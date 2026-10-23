"""Single-threaded About.xml parse cost, and the cost of the mod_path setter's hasattr()."""
import sys
import time
from pathlib import Path

from loguru import logger

logger.remove()
from app.models.metadata import metadata_structure as ms
from app.models.metadata.metadata_factory import create_listed_mod_from_path

game = Path(sys.argv[1]).resolve()
paths = [p for p in (game / "Mods").iterdir() if p.is_dir()] + [p for p in (game / "Data").iterdir() if p.is_dir()]


def parse_all() -> float:
    t = time.perf_counter()
    for p in paths:
        create_listed_mod_from_path(p, "1.6.4633", game / "Mods", game, None)
    return time.perf_counter() - t


base = min(parse_all() for _ in range(3))
orig = ms.ListedMod.mod_path.fset


def setter_without_hasattr(self, path):
    if self._mod_path:
        raise ValueError("Mod path already set. Cannot override.")
    self._mod_path = path
    self.__dict__.pop("published_file_id", None)


ms.ListedMod.mod_path = ms.ListedMod.mod_path.setter(setter_without_hasattr)
patched = min(parse_all() for _ in range(3))
print(f"mods={len(paths)} single-thread parse: {base * 1000:.0f} ms; with setter using __dict__.pop instead of hasattr: {patched * 1000:.0f} ms")
