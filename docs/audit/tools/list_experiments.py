"""Experiments on MetadataController.get_mods_from_list (ModsConfig -> active list)."""
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from loguru import logger

logger.remove()
from app.controllers.metadata_controller import MetadataController
from app.models.metadata.metadata_structure import AboutXmlMod, CaseInsensitiveStr, ModType


def mk(pid, path, mtype):
    m = AboutXmlMod(name=pid)
    m.package_id = CaseInsensitiveStr(pid)
    m.mod_path = Path(path)
    m.mod_type = mtype
    return m


def run(mods, ids):
    fake = SimpleNamespace(mods_metadata={str(m.mod_path): m for m in mods}, game_version="1.6")
    return MetadataController.get_mods_from_list(fake, ids)


mods = [
    mk("author.my_steamworks", "/local/steamworks", ModType.LOCAL),
    mk("author.my_steamworks", "/workshop/111", ModType.STEAM_WORKSHOP),
    mk("plain.mod", "/local/plain", ModType.LOCAL),
    mk("plain.mod", "/workshop/222", ModType.STEAM_WORKSHOP),
]
a, i, d, m = run(mods, ["author.my_steamworks", "plain.mod"])
print("ids: author.my_steamworks, plain.mod (both duplicated local+workshop)")
print("active:", a)
print("missing:", m)
a, i, d, m = run(mods, ["plain.mod", "plain.mod"])
print("\nids: plain.mod listed twice in ModsConfig")
print("active:", a)
