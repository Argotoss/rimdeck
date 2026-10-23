"""Compare the two live missing-dependency checks on the same active list."""
from pathlib import Path
from types import SimpleNamespace

from loguru import logger

logger.remove()
from app.models.metadata.metadata_structure import (
    AboutXmlMod, BaseRules, CaseInsensitiveStr, DependencyMod,
)
from app.services.dependency_resolver import build_dependencies_dialog_context
from app.utils.constants import KNOWN_MOD_REPLACEMENTS


def mk(pid, deps=()):
    m = AboutXmlMod(name=pid)
    m.package_id = CaseInsensitiveStr(pid)
    m.about_rules = BaseRules()
    for d in deps:
        dm = DependencyMod(); dm.package_id = CaseInsensitiveStr(d)
        m.about_rules.dependencies[CaseInsensitiveStr(d)] = dm
    m.mod_path = Path(f"/mods/{pid}")
    return m


mods = [mk("zetrith.prepatcher"), mk("some.mod", deps=("brrainz.harmony",))]
meta = {str(m.mod_path): m for m in mods}
mc = SimpleNamespace(
    mods_metadata=meta, steam_db=None, game_version="1.6",
    settings=SimpleNamespace(use_alternative_package_ids_as_satisfying_dependencies=True, prefer_versioned_about_tags=True),
)
_, missing, _ = build_dependencies_dialog_context(mc, set(meta))
print("Sort pre-check dialog (dependency_resolver):", missing or "nothing missing")
active = {"zetrith.prepatcher", "some.mod"}
listed = any(r in active for r in KNOWN_MOD_REPLACEMENTS.get("brrainz.harmony", set()))
print("Mod list error icon (mods_panel._check_missing_dependencies + _has_replacement):",
      "Harmony counted as satisfied by Prepatcher" if listed else "missing")
