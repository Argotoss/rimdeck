"""Reproduce the 'Sort blocks the main thread' report headlessly.

Starts RimDeck (dev mode, offscreen), then clicks Sort through the real code path
(_do_sort with check_deps=True and the real MissingDependenciesDialog). A sampler
thread dumps all Python stacks every few seconds; a QTimer inside the nested
event loop reports which top-level windows are visible, then closes them.

Usage: uv run python docs/audit/tools/repro_sort_hang.py <bench_dir>
"""

import faulthandler
import os
import sys
import threading
import time
import traceback
from pathlib import Path

BENCH = Path(sys.argv[1]).resolve()
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
logger.add(sys.stderr, level="INFO", filter=lambda r: "sort" in r["message"].lower())

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

QDialog.exec = lambda self: 0  # type: ignore[method-assign]
QMessageBox.exec = lambda self: QMessageBox.StandardButton.No  # type: ignore[method-assign]

from app.controllers.app_controller import AppController  # noqa: E402

ctrl = AppController()
mw = ctrl.main_window
mw.show()
mw.initialize_content(is_initial=True)
mcp = mw.main_content_panel
print("startup done", flush=True)
for w in QApplication.topLevelWidgets():
    if w.isVisible() and w is not mw:
        print(f"closing startup window {type(w).__name__} modality={w.windowModality()}", flush=True)
        w.close()
QApplication.processEvents()
print(f"activeModalWidget before Sort: {QApplication.activeModalWidget()}", flush=True)

stack_log = (BENCH / "sort_hang_stacks.txt").open("w")
main_ident = threading.main_thread().ident
stop = threading.Event()


def sampler() -> None:
    t0 = time.perf_counter()
    while not stop.wait(3.0):
        frame = sys._current_frames().get(main_ident)
        stack_log.write(
            f"\n--- main thread @ {time.perf_counter() - t0:.1f}s cpu={time.process_time():.2f}s\n"
        )
        stack_log.write("".join(traceback.format_stack(frame)[-14:]))
        stack_log.flush()


def report_and_close() -> None:
    vis = [
        f"{type(w).__name__} title={w.windowTitle()!r} modal={w.isModal()}"
        for w in QApplication.topLevelWidgets()
        if w.isVisible() and w is not mw
    ]
    print(f"[t+10s] visible top-level windows besides main: {vis}", flush=True)
    dlg = [w for w in QApplication.topLevelWidgets() if type(w).__name__ == "MissingDependenciesDialog"]
    for d in dlg:
        print(f"[t+10s] dialog parent={d.parent()} isActiveWindow={d.isActiveWindow()} main.isEnabled={mw.isEnabled()} activeModal={QApplication.activeModalWidget()}", flush=True)
    for w in QApplication.topLevelWidgets():
        if w.isVisible() and w is not mw:
            w.close()
    print("[t+10s] closed them", flush=True)


threading.Thread(target=sampler, daemon=True).start()
QTimer.singleShot(10_000, report_and_close)
t = time.perf_counter()
sort_btn = [b for b in ctrl.main_window_controller.buttons if "sort" in b.text().lower()][0]
print(f"clicking button {sort_btn.text()!r}", flush=True)
sort_btn.click()
print(f"_do_sort returned after {time.perf_counter() - t:.1f}s", flush=True)
stop.set()
faulthandler.dump_traceback(file=stack_log)
os._exit(0)
