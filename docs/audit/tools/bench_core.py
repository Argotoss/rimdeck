"""Headless benchmark of RimDeck's non-UI logic against a synthetic install.

Usage: uv run python docs/audit/tools/bench_core.py <bench_dir> [--profile]
<bench_dir> is a RIMDECK_DEV_DIR whose data/settings.json points at a fake game.
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
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from loguru import logger  # noqa: E402

logger.remove()
logger.add(sys.stderr, level="ERROR")

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])

import app.utils.globals as app_globals  # noqa: E402
from app.controllers.metadata_controller import MetadataController  # noqa: E402
from app.controllers.metadata_db_controller import AuxMetadataController  # noqa: E402
from app.controllers.sort_controller import Sorter  # noqa: E402
from app.models.metadata.metadata_structure import AboutXmlMod  # noqa: E402
from app.models.settings import Settings  # noqa: E402
from app.services.dependency_resolver import (  # noqa: E402
    build_dependencies_dialog_context,
)
from app.sort.mod_sorting import ModsPanelSortKey, sort_paths  # noqa: E402
from app.utils.constants import SortMethod  # noqa: E402
from app.utils.steam.steamcmd.wrapper import SteamcmdInterface  # noqa: E402

settings = Settings()
settings.load()
app_globals.SETTINGS = settings
inst = settings.instances[settings.current_instance]
SteamcmdInterface.instance(inst.steamcmd_install_path, False)
aux = AuxMetadataController.get_or_create_cached_instance(settings.aux_db_path)
mc = MetadataController.instance(
    settings=settings, get_active_instance=lambda: inst, metadata_db_controller=aux
)

RESULTS: list[tuple[str, float]] = []
PROFILES: dict[str, str] = {}


def timed(label: str, fn, *a, profile: bool = PROFILE, **kw):
    pr = cProfile.Profile() if profile else None
    t = time.perf_counter()
    if pr:
        pr.enable()
    out = fn(*a, **kw)
    if pr:
        pr.disable()
    dt = time.perf_counter() - t
    RESULTS.append((label, dt))
    print(f"{label:<60} {dt * 1000:9.1f} ms", flush=True)
    if pr:
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(18)
        PROFILES[label] = s.getvalue()
    return out


timed("refresh_metadata (cold: parse + aux db + acf)", mc.refresh_metadata)
timed("refresh_metadata (warm, 2nd run)", mc.refresh_metadata)
mods = mc.mods_metadata
print(f"  mods parsed: {len(mods)}")

cfg = str(Path(inst.config_folder) / "ModsConfig.xml")
active, inactive, dups, missing = timed(
    "get_mods_from_list(ModsConfig.xml)", mc.get_mods_from_list, cfg
)
print(f"  active={len(active)} inactive={len(inactive)} missing={len(missing)}")

compiled = timed("compile() (CompiledDependencyData.build)", mc.compile)
compiled_deps = timed(
    "compile(use_moddependencies_as_loadTheseBefore=True)",
    mc.compile,
    use_moddependencies_as_loadTheseBefore=True,
    use_alternative_package_ids=True,
)
active_set = set(active)
for method in (SortMethod.TOPOLOGICAL, SortMethod.ALPHABETICAL):
    sorter = Sorter(method, compiled, mods, active_set)
    ok, order = timed(f"Sorter({method.value}).sort()", sorter.sort)
    print(f"  ok={ok} n={len(order)}")

timed("get_missing_dependencies(active)", mc.get_missing_dependencies, active_set)
summary, missing_deps, resolve = timed(
    "build_dependencies_dialog_context(active) [sort pre-check]",
    build_dependencies_dialog_context,
    mc,
    active_set,
)
print(f"  mods with missing deps={len(missing_deps)} resolved={len(resolve)}")

timed(
    "is_version_mismatch() x all mods",
    lambda: [mc.is_version_mismatch(p) for p in mods],
)
timed(
    "has_alternative_mod() x all mods",
    lambda: [mc.has_alternative_mod(p) for p in mods],
)

for key in (
    ModsPanelSortKey.MODNAME,
    ModsPanelSortKey.FILESYSTEM_MODIFIED_TIME,
    ModsPanelSortKey.MOD_TAGS,
):
    timed(
        f"sort_paths(inactive, {key.name})",
        sort_paths,
        list(inactive),
        key,
        settings=settings,
    )


def per_item_db_pattern(paths: list[str]) -> None:
    """Replicates ModListWidget.recreate_mod_list's per-item aux DB work."""
    from app.utils.custom_list_widget_item_metadata import (
        CustomListWidgetItemMetadata,
    )

    for p in paths:
        with aux.Session() as s:
            aux.get_or_create(s, p)
            aux.update(s, p, outdated=False)
            CustomListWidgetItemMetadata(
                path=p,
                list_type="Active",
                aux_metadata_controller=aux,
                aux_metadata_session=s,
                settings=settings,
            )


timed("recreate_mod_list item-metadata pattern (active)", per_item_db_pattern, active)
timed(
    "recreate_mod_list item-metadata pattern (inactive)", per_item_db_pattern, inactive
)


def search_like(term: str) -> int:
    hits = 0
    for p in active + inactive:
        m = mods.get(p)
        if m is None:
            continue
        hay = m.name.lower()
        if isinstance(m, AboutXmlMod):
            hay += " " + " ".join(m.authors).lower() + " " + str(m.package_id)
        if term in hay:
            hits += 1
    return hits


timed("baseline: pure-python substring search over all mods", search_like, "vanilla")

out = BENCH / "results.txt"
with out.open("w") as f:
    for label, dt in RESULTS:
        f.write(f"{label:<60} {dt * 1000:9.1f} ms\n")
    for label, prof in PROFILES.items():
        f.write(f"\n===== PROFILE: {label}\n{prof}")
print(f"wrote {out}")
os._exit(0)
