"""Launch RimDeck in dev mode, run scripted UI steps, grab every visible window.

Usage: uv run python docs/audit/tools/shoot.py <outdir> <steps_module>
A steps module defines STEPS: list[tuple[str, float, Callable[[AppController], None]]].
"""
import importlib.util
import os
import sys
import time
import traceback
from pathlib import Path

os.environ["RIMDECK_DEV"] = "1"
sys.modules["__main__"].__file__ = str(Path(__file__).resolve().parents[3] / "app" / "__main__.py")
os.environ["RIMDECK_DISABLE_UPDATER"] = "1"
sys.argv = [sys.argv[0], "--dev"] + sys.argv[1:]
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location("steps", sys.argv[3])
steps_mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(steps_mod)

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

T0 = time.perf_counter()
from app.controllers.app_controller import AppController

ctrl = AppController()
print(f"TIMING construct={time.perf_counter()-T0:.2f}s", flush=True)

def grab_all(tag: str) -> None:
    for i, w in enumerate(QApplication.topLevelWidgets()):
        if w.isVisible() and w.width() > 50:
            w.grab().save(str(OUT / f"{tag}_{i}_{type(w).__name__}.png"))

queue = list(steps_mod.STEPS)
def run_next() -> None:
    if not queue:
        QApplication.quit(); os._exit(0)
    tag, delay, fn = queue.pop(0)
    try:
        fn(ctrl)
    except Exception:
        traceback.print_exc()
    def shoot() -> None:
        grab_all(tag); print(f"SHOT {tag} t={time.perf_counter()-T0:.2f}s", flush=True); run_next()
    QTimer.singleShot(int(delay * 1000), shoot)

QTimer.singleShot(500, run_next)
ctrl.run()
