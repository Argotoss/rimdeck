"""Black-box experiments against RimDeck's load-order sorter.

Usage: uv run python docs/audit/tools/sort_experiments.py
Each experiment prints its verdict; nothing touches disk or real settings.
"""

import os
import random
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from loguru import logger

logger.remove()

from PySide6.QtWidgets import QApplication

app = QApplication([])

import app.sort.topo_sort as topo_mod
from app.controllers.sort_controller import Sorter
from app.models.metadata.metadata_structure import (
    AboutXmlMod,
    BaseRules,
    CaseInsensitiveSet,
    CaseInsensitiveStr,
    CompiledDependencyData,
    DependencyMod,
    ListedMod,
    Rules,
)
from app.utils.constants import SortMethod

WARNINGS: list[str] = []
topo_mod.show_warning = lambda **kw: WARNINGS.append(kw.get("details", ""))  # type: ignore[assignment]


def mk(
    pid: str,
    name: str | None = None,
    after: tuple[str, ...] = (),
    before: tuple[str, ...] = (),
    deps: tuple[str, ...] = (),
    first: bool = False,
    last: bool = False,
    path: str | None = None,
) -> AboutXmlMod:
    m = AboutXmlMod(name=name or pid)
    m.package_id = CaseInsensitiveStr(pid)
    m.about_rules = BaseRules(
        load_after=CaseInsensitiveSet(after),
        load_before=CaseInsensitiveSet(before),
    )
    for d in deps:
        dm = DependencyMod()
        dm.package_id = CaseInsensitiveStr(d)
        m.about_rules.dependencies[CaseInsensitiveStr(d)] = dm
    m.community_rules = Rules(load_first=first, load_last=last)
    m.mod_path = Path(path or f"/mods/{pid}")
    return m


def run(mods: list[ListedMod], method=SortMethod.TOPOLOGICAL, deps_as_order=False):
    meta = {str(m.mod_path): m for m in mods}
    compiled = CompiledDependencyData.build(meta, deps_as_order, True)
    ok, order = Sorter(method, compiled, meta, set(meta)).sort()
    names = [meta[p].name for p in order]
    return ok, names, meta, order


def violations(meta, order) -> list[str]:
    pos = {str(meta[p].package_id): i for i, p in enumerate(order)}
    bad = []
    for p in order:
        m = meta[p]
        pid = str(m.package_id)
        r = m.overall_rules
        for a in r.load_after:
            if str(a) in pos and pos[str(a)] > pos[pid]:
                bad.append(f"{pid} should load after {a}")
        for b in r.load_before:
            if str(b) in pos and pos[str(b)] < pos[pid]:
                bad.append(f"{pid} should load before {b}")
    return bad


def header(t: str) -> None:
    print(f"\n### {t}")


if os.environ.get("SORT_EXP_ONLY") == "E9":
    mods = [
        mk("lib.core", name="Library"),
        mk("author1.patch", name="Compat Patch", after=("lib.core",)),
        mk("author2.patch", name="Compat Patch", after=("lib.core",)),
        mk("author3.patch", name="Compat Patch", after=("lib.core",)),
    ]
    for method in (SortMethod.TOPOLOGICAL, SortMethod.ALPHABETICAL):
        ok, names, meta, order = run(mods, method)
        print(method.value, [str(meta[p].package_id) for p in order])
    sys.exit(0)

header("E1 simple 2-cycle (A after B, B after A)")
WARNINGS.clear()
ok, names, *_ = run([mk("a", after=("b",)), mk("b", after=("a",)), mk("c")])
print(f"ok={ok} result={names} warning_details={WARNINGS!r}")
print("-> whole sort aborted; unrelated mod 'c' is not sorted either; no partial result")

header("E2 cycle enumeration blow-up (dense SCC, as from a bad community rule set)")
for n in (6, 7, 8, 9):
    pids = [f"m{i}" for i in range(n)]
    mods = [mk(p, after=tuple(q for q in pids if q != p)) for p in pids]
    WARNINGS.clear()
    t = time.perf_counter()
    run(mods)
    dt = time.perf_counter() - t
    print(
        f"n={n}: {dt * 1000:8.1f} ms, cycles listed in dialog={WARNINGS[0].count(chr(10) + chr(10)) + 1}, details chars={len(WARNINGS[0])}"
    )

header("E3 duplicate packageId active twice (local copy + workshop copy)")
ok, names, meta, order = run(
    [
        mk("dup.mod", name="Dup (local)", path="/local/dup"),
        mk("dup.mod", name="Dup (workshop)", path="/workshop/123"),
        mk("other"),
    ]
)
print(f"active in=3 sorted out={len(order)} -> {names}")

header("E4 non-About mods (scenario / invalid folder) in the active list")
inv = ListedMod(name="Broken folder", valid=False)
inv.mod_path = Path("/mods/broken")
ok, names, meta, order = run([mk("a"), mk("b"), inv])
print(f"active in=3 sorted out={len(order)} -> {names}")

header("E5 modDependencies without loadAfter (default setting deps_as_order=False)")
ok, names, meta, order = run(
    [mk("zz.lib", name="ZZ Library"), mk("aa.user", name="AA Uses Library", deps=("zz.lib",))]
)
print(f"default: {names}  (dependent before its dependency)")
ok, names, meta, order = run(
    [mk("zz.lib", name="ZZ Library"), mk("aa.user", name="AA Uses Library", deps=("zz.lib",))],
    deps_as_order=True,
)
print(f"use_moddependencies_as_loadTheseBefore=True: {names}")

header("E6 random DAGs: constraint satisfaction, topo vs alphabetical")
random.seed(7)
tot = {SortMethod.TOPOLOGICAL: 0, SortMethod.ALPHABETICAL: 0}
cases = 200
for _ in range(cases):
    n = random.randint(20, 120)
    pids = [f"p{i:03d}" for i in range(n)]
    mods = []
    for i, p in enumerate(pids):
        earlier = pids[:i]
        after = tuple(random.sample(earlier, k=min(len(earlier), random.choice([0, 0, 1, 2, 3]))))
        later = pids[i + 1 :]
        before = tuple(random.sample(later, k=min(len(later), random.choice([0, 0, 0, 1]))))
        nm = "".join(random.choice("abcdefghij") for _ in range(6))
        mods.append(
            mk(p, name=nm, after=after, before=before, first=random.random() < 0.03, last=random.random() < 0.03)
        )
    for method in tot:
        ok, names, meta, order = run(mods, method)
        tot[method] += len(violations(meta, order)) if ok else 10**6
for method, v in tot.items():
    print(f"{method.value}: total loadBefore/loadAfter violations over {cases} random DAGs = {v}")

header("E7 tier contradictions are resolved silently")
ok, names, meta, order = run(
    [
        mk("z.last", name="Z Load Last", last=True),
        mk("x.mid", name="X", after=("z.last",)),
        mk("unlimitedhugs.hugslib", name="HugsLib", after=("x.mid",)),
    ]
)
print(f"ok={ok} {names} violations={violations(meta, order)}")

header("E8 the current order is ignored (unconstrained mods are re-alphabetised)")
mods = [mk("c", name="C"), mk("a", name="A"), mk("b", name="B", after=("c",))]
ok, names, *_ = run(mods)
print(f"user order C, A, B (B after C) -> sorted {names}")

header("E9 determinism across PYTHONHASHSEED (two mods share a display name)")
seeds = {}
for seed in ("1", "2", "3", "4", "5", "6"):
    env = dict(os.environ, PYTHONHASHSEED=seed, SORT_EXP_ONLY="E9")
    out = subprocess.run(
        [sys.executable, __file__], env=env, capture_output=True, text=True
    ).stdout.strip()
    seeds[seed] = " | ".join(out.splitlines()[-2:]) if out else "?"
print("\n".join(f"seed {k}: {v}" for k, v in seeds.items()))
print(f"distinct orders: {len(set(seeds.values()))}")
