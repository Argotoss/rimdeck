"""Time a full headless RimDeck startup plus common UI-thread operations.

Usage: uv run python docs/audit/tools/bench_app.py <bench_dir> [--profile]
"""

import cProfile
import io
import os
import pstats
import sys
import time
from pathlib import Path

BENCH = Path(sys.argv[1]).resolve()
PROFILE = "--profile" in sys.argv
os.environ["RIMDECK_DEV"] = "1"
os.environ["RIMDECK_DEV_DIR"] = str(BENCH)
os.environ["RIMDECK_DISABLE_UPDATER"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.modules["__main__"].__file__ = str(
    Path(__file__).resolve().parents[3] / "app" / "__main__.py"
)
sys.argv = [sys.argv[0], "--dev"]

from loguru import logger  # noqa: E402

logger.remove()
logger.add(sys.stderr, level="ERROR")

from PySide6.QtWidgets import QDialog, QMessageBox  # noqa: E402

QDialog.exec = lambda self: 0  # type: ignore[method-assign]
QMessageBox.exec = lambda self: QMessageBox.StandardButton.No  # type: ignore[method-assign]

import app.windows.missing_dependencies_dialog as mdd  # noqa: E402

mdd.MissingDependenciesDialog.show_dialog = lambda self, *a, **k: set()  # type: ignore[method-assign]

RESULTS: list[tuple[str, float]] = []
PROFILES: dict[str, str] = {}


ONLY = os.environ.get("PROFILE_ONLY", "")


def timed(label, fn, *a, **kw):
    pr = cProfile.Profile() if PROFILE and ONLY in label else None
    t = time.perf_counter()
    if pr:
        pr.enable()
    out = fn(*a, **kw)
    if pr:
        pr.disable()
    dt = time.perf_counter() - t
    RESULTS.append((label, dt))
    print(f"{label:<62} {dt * 1000:9.1f} ms", flush=True)
    if pr:
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(30)
        PROFILES[label] = s.getvalue()
    return out


import faulthandler  # noqa: E402

_stackf = open(BENCH / "stacks.txt", "w")  # noqa: SIM115
if os.environ.get("STACKS"):
    faulthandler.dump_traceback_later(float(os.environ["STACKS"]), repeat=True, file=_stackf)

T0 = time.perf_counter()
from app.controllers.app_controller import AppController  # noqa: E402

print(f"{'import app modules':<62} {(time.perf_counter() - T0) * 1000:9.1f} ms")
ctrl = timed("AppController() construct", AppController)
mw = ctrl.main_window


def startup() -> None:
    mw.show()
    mw.initialize_content(is_initial=True)


timed("main_window.show() + initialize_content(is_initial=True)", startup)
mcp = mw.main_content_panel
mp = mcp.mods_panel
if os.environ.get("CLOSE_WINDOWS"):
    from PySide6.QtWidgets import QApplication

    for w in QApplication.topLevelWidgets():
        if w.isVisible() and w is not mw:
            print(f"  closing {type(w).__name__}")
            w.close()
    QApplication.processEvents()
print(
    f"  active={mp.active_mods_list.count()} inactive={mp.inactive_mods_list.count()}"
)
print(f"{'TOTAL to usable window':<62} {(time.perf_counter() - T0) * 1000:9.1f} ms")

timed("recalculate_list_errors_warnings('Active')", mp.recalculate_list_errors_warnings, "Active")
timed("recalculate_list_errors_warnings('Inactive')", mp.recalculate_list_errors_warnings, "Inactive")

for term in ("v", "va", "van", "vani", "vanil", "vanill", "vanilla"):
    timed(f"inactive search keystroke '{term}'", mp.on_inactive_mods_search, term)
timed("inactive search clear", mp.on_inactive_mods_search_clear)
timed("active search 'vanilla'", mp.on_active_mods_search, "vanilla")
timed("active search clear", mp.on_active_mods_search_clear)

timed("_do_sort(check_deps=False)", mcp._do_sort, check_deps=False)
timed("_do_sort(check_deps=True) [dialog stubbed]", mcp._do_sort, check_deps=True)
timed("_do_sort again (already sorted)", mcp._do_sort, check_deps=False)

def live_panels() -> str:
    from PySide6.QtWidgets import QApplication

    names = [type(w).__name__ for w in QApplication.topLevelWidgets()]
    return f"MissingModPropertiesPanel alive={names.count('MissingModPropertiesPanel')} visible={sum(1 for w in QApplication.topLevelWidgets() if type(w).__name__ == 'MissingModPropertiesPanel' and w.isVisible())}"


for i in range(int(os.environ.get("REFRESH_N", "1"))):
    if os.environ.get("CLOSE_WINDOWS"):
        from PySide6.QtWidgets import QApplication

        for w in QApplication.topLevelWidgets():
            if w.isVisible() and w is not mw:
                w.close()
        QApplication.processEvents()
    print("  before refresh:", live_panels())
    timed(f"_do_refresh(is_initial=False) [Refresh button] #{i + 1}", mcp._do_refresh, is_initial=False)

out = BENCH / "results_app.txt"
with out.open("w") as f:
    for label, dt in RESULTS:
        f.write(f"{label:<62} {dt * 1000:9.1f} ms\n")
    for label, prof in PROFILES.items():
        f.write(f"\n===== PROFILE: {label}\n{prof}")
print(f"wrote {out}")
os._exit(0)
