"""Sort re-entrancy: click Sort twice while the Dependency Manager is open.

Usage: uv run python docs/audit/tools/repro_sort_reentrancy.py <bench_dir>
"""
import os
import sys
import time
from pathlib import Path

BENCH = Path(sys.argv[1]).resolve()
os.environ.update(RIMDECK_DEV="1", RIMDECK_DEV_DIR=str(BENCH), RIMDECK_DISABLE_UPDATER="1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.modules["__main__"].__file__ = str(Path(__file__).resolve().parents[3] / "app" / "__main__.py")
sys.argv = [sys.argv[0], "--dev"]
from loguru import logger

logger.remove()
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

QDialog.exec = lambda self: 0
QMessageBox.exec = lambda self: QMessageBox.StandardButton.No
from app.controllers.app_controller import AppController
import app.windows.missing_dependencies_dialog as mdd

CREATED: list = []
_orig_init = mdd.MissingDependenciesDialog.__init__


def _rec_init(self, *a, **k):
    _orig_init(self, *a, **k)
    CREATED.append(self)


mdd.MissingDependenciesDialog.__init__ = _rec_init

ctrl = AppController()
mw = ctrl.main_window
mw.show()
mw.initialize_content(is_initial=True)
for w in QApplication.topLevelWidgets():
    if w.isVisible() and w is not mw:
        w.close()
btn = [b for b in ctrl.main_window_controller.buttons if "sort" in b.text().lower()][0]
T0 = time.perf_counter()
returns: list[float] = []
OUTER_DONE: list[bool] = []


def dialogs():
    return [w for w in QApplication.topLevelWidgets() if type(w).__name__ == "MissingDependenciesDialog" and w.isVisible()]


def second_click():
    print(f"[{time.perf_counter() - T0:4.1f}s] dialogs open={len(dialogs())}; main window enabled={mw.isEnabled()} -> clicking Sort again", flush=True)
    btn.click()
    returns.append(time.perf_counter() - T0)
    print(f"[{time.perf_counter() - T0:4.1f}s] inner Sort returned", flush=True)


def close_first():
    print(f"[{time.perf_counter() - T0:4.1f}s] dialogs open={len(dialogs())}; user closes the FIRST (outer Sort's) dialog", flush=True)
    CREATED[0].reject()
    QTimer.singleShot(100, lambda: print(f"[{time.perf_counter() - T0:4.1f}s] after closing it: outer Sort returned? {'no' if not OUTER_DONE else 'yes'}; dialogs open={len(dialogs())}", flush=True))


def close_rest():
    ds = dialogs()
    print(f"[{time.perf_counter() - T0:4.1f}s] outer Sort still waiting (returned={bool(returns)}); dialogs open={len(ds)}; closing remaining", flush=True)
    for d in ds:
        d.reject()


QTimer.singleShot(2000, second_click)
QTimer.singleShot(4000, close_first)
QTimer.singleShot(8000, close_rest)
btn.click()
OUTER_DONE.append(True)
print(f"[{time.perf_counter() - T0:4.1f}s] outer Sort returned", flush=True)
os._exit(0)
