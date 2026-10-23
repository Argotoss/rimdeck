# RimDeck audit: logic and performance

Branch `audit` (separate worktree), tree at `18e52bcb`. macOS, Python 3.14.6 with the GIL on, PySide6 offscreen.
I did not modify anything under `app/` or `tests/`. The harness scripts are in `docs/audit/tools/` and the raw outputs are in `docs/audit/evidence/`.

| Script | Purpose |
| --- | --- |
| `bench_core.py <dev_dir> [--profile]` | Headless timings of the non-UI logic (metadata, ModsConfig resolution, compile, sort, dependency checks, aux DB). Output: `bench_*/results.txt` |
| `bench_app.py <dev_dir> [--profile]` | Real `AppController`, offscreen: startup, search, Sort, Refresh. Env vars: `PROFILE_ONLY`, `REFRESH_N`, `CLOSE_WINDOWS`. Output: `bench_*/results_app.txt` |
| [`repro_sort_hang.py`](tools/repro_sort_hang.py), [`repro_sort_reentrancy.py`](tools/repro_sort_reentrancy.py) | Reproduce the reported Sort "hang" |
| [`sort_experiments.py`](tools/sort_experiments.py) | Black-box experiments on the sorter. Output: [`sort_experiments.txt`](evidence/sort_experiments.txt) |
| [`list_experiments.py`](tools/list_experiments.py), [`deps_divergence.py`](tools/deps_divergence.py), [`git_repair_experiment.py`](tools/git_repair_experiment.py), [`parse_microbench.py`](tools/parse_microbench.py) | Targeted experiments, one output `.txt` each |

Fixtures:

- `dev/fakegame`: 606 mods, 307 active.
- `dev/fakegame_big`: 2006 mods, 807 active. Generated with `make_fake_game.py dev/fakegame_big 2000 800`.
- Each bench run uses its own `RIMDECK_DEV_DIR`: `docs/audit/evidence/bench_small` and `docs/audit/evidence/bench_big`. Both use the real downloaded databases through file paths: steamDB has 57,679 entries and Community Rules has 631 rules.

Caveat: the app's startup routine still calls `check_internet_connection()`, which sends HEAD requests to steamcommunity.com and github.com. The bench runs did this because the app does it on startup. No databases were downloaded.

## TL;DR

- **Sort algorithm: keep.** The topological sort and its tier model (`CompiledDependencyData.build` + `Sorter` + `do_topo_sort`) are correct on random DAGs (0 violations in 200 cases) and fast: about 2 ms for 807 active mods.
- **Everything around it is the problem.** At 2000 mods, a Sort click freezes the UI for 2–3 s, and over 99.9 % of that time is outside the algorithm. A Refresh can take minutes. The validation logic is duplicated three ways and lives in a 5,861-line widget. Several user-visible behaviours are wrong:
  - mods are silently dropped from the active list;
  - the order is non-deterministic;
  - dividers are wiped;
  - the "missing PublishedFileId" nag is wrong by construction;
  - a git "repair" deletes `.git`.
- **Recommendation:** keep the domain core (parsing, rule merge, compiled graph, topo sort), rebuild the orchestration and validation layer as a Qt-free service, and fix the aux-DB access pattern. A full rewrite is not justified by the logic.

## Measurements

All timings are wall clock, without the profiler, median of the runs shown. Columns: S = 606 mods / 307 active, B = 2006 mods / 807 active.

| Operation (thread) | S | B | Notes |
| --- | ---: | ---: | --- |
| Import app modules | 0.88 s | 0.90 s | |
| `AppController()` | 0.32 s | 0.32 s | |
| `show()` + `initialize_content(is_initial=True)` (UI thread, with a nested loop for the scan) | 3.52 s | 6.28 s | |
| **Time to usable window** | **4.7 s** | **7.5 s** | |
| `refresh_metadata` cold / warm (worker thread at startup; UI thread from `do_metadata_refresh_cache` and panel deletes) | 0.58 / 0.49 s | 1.50 / 1.06 s | no parse cache |
| `get_mods_from_list(ModsConfig.xml)` | 19 ms | 153 ms | O(list × mods), 1.6 M `isinstance` calls |
| `compile()` (graph build) | 3 ms | 14 ms | |
| `Sorter(Topological).sort()` | 0.7 ms | 1.9 ms | the algorithm itself |
| `Sorter(Alphabetical).sort()` | 1.4 ms | 6.5 ms | |
| `build_dependencies_dialog_context` (Sort pre-check, UI thread) | 248 ms | 987 ms | re-parses About.xml 25,824 times at B |
| `sort_paths(inactive, MOD_TAGS)` (UI thread) | 68 ms | 272 ms | 2 SQL queries per mod |
| Per-item aux DB work of `recreate_mod_list`, active + inactive (UI thread) | 0.50 s | 1.63 s | ~6 SELECTs + 1 COMMIT per mod |
| **Sort button**, `_do_sort(check_deps=False)` (UI thread) | 0.67 s | 1.98 s | 99.9 % list rebuild |
| Sort button with the deps check (dialog stubbed) | 0.89 s | 3.10 s | |
| Sort when already sorted | 0.65 s | 2.13 s | never short-circuits (finding H5) |
| Search keystroke, inactive list | 4–42 ms | 8–42 ms | no debounce, but fine |
| `recalculate_list_errors_warnings('Active')` | 24 ms | 25 ms | fine |
| **Refresh button** (`_do_refresh`), startup "Missing Properties" panel still open | **17.4 s** | **166 s** | finding C1 |
| Refresh ×5 at S, user closes the panel each time | 3.8 → 4.1 → 4.2 → 4.3 → 4.7 s | | one leaked panel per Refresh |
| Refresh ×4 at S, panel left open | 3.7 → 18.1 → 34.0 → 46.8 s | | |

Profiled hot spots (cProfile, `docs/audit/evidence/bench_big/results*.txt`):

1. **Aux DB access per list item, on the UI thread.**
   - Startup issues 16,182 `AuxMetadataController.get` calls ([`metadata_db_controller.py:152`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/metadata_db_controller.py#L152)); a Sort issues 12,172.
   - Callers: `ModListWidget.recreate_mod_list` ([`views/mods_panel.py:3989-4016`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L3989-L4016)) → `CustomListWidgetItemMetadata.__init__` ([`utils/custom_list_widget_item_metadata.py:77-131`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/custom_list_widget_item_metadata.py#L77-L131)).
   - Each item makes separate queries for `warning_toggled`, `color`, `tags`, `user_notes` and the `updated` timestamp.
   - Each item also runs `AuxMetadataController.update(..., outdated=False)`, which COMMITs per mod ([`metadata_db_controller.py:143`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/metadata_db_controller.py#L143)).
   - This is a mark-and-sweep pattern that costs N commits: `do_set_all_entries_in_aux_db_as_outdated` → per-item un-mark → `do_delete_outdated_entries_in_aux_db` ([`views/main_window.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_window.py), `initialize_content`).
2. **`QStandardItemModel.appendRow` in `BaseModsPanel._add_row` ([`windows/base_mods_panel.py:331`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/windows/base_mods_panel.py#L331)).**
   - Costs 12 ms per row when the table is visible, because the vertical header is `ResizeToContents` and sorting is enabled ([`base_mods_panel.py:179, 207`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/windows/base_mods_panel.py#L179)). Populating is therefore O(n²).
   - In the Refresh profile at S: 1,200 rows took 13.9 s of 18.7 s.
3. **`dependency_resolver._resolve_from_about_xml` ([`services/dependency_resolver.py:54-113`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/services/dependency_resolver.py#L54-L113)).**
   - For every missing dependency, it parses the About.xml of every active mod from disk again.
   - At B that is 32 × 807 = 25,824 `ET.parse` calls. On top of that comes a linear scan of the 57k-entry steamDB per dependency (`:122-132`, 3.7 M `str.lower` calls).
4. **`pygit2.discover_repository`, called per local mod in `_set_mod_type` ([`models/metadata/metadata_factory.py:420`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_factory.py#L420)).**
   - It is 31 % of single-thread parse time (0.53 s of 1.69 s at B).
   - A plain `(mod_path / ".git").exists()` gives the same answer for the case the code checks (`Path(repo).parent == mod.mod_path`).
5. **`MetadataController.get_mods_from_list` ([`controllers/metadata_controller.py:542-600`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/metadata_controller.py#L542-L600)).** It loops over every mod for every ModsConfig entry, and uses `path not in active_mod_paths` on a list. Quadratic: 153 ms at B, about 1 s at 5k/2k.
6. **Parsing threads don't help.**
   - Parsing all 2006 About.xml on a single thread takes 1.00 s ([`parse_microbench.txt`](evidence/parse_microbench.txt)).
   - The `QThreadPool` fan-out in `MetadataMediator.refresh_metadata` takes 0.97 s for the same work, so the GIL removes the benefit.
   - There is no parse cache, so every Refresh, rule edit and DB change re-parses everything.

## The reported Sort "hang" (600 mods, `dev/fakegame`)

The report was that clicking Sort logged `Starting sorting mods` ([`main_content_panel.py:1068`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L1068)), and then nothing happened for more than 4 minutes.

**Verdict: this is neither a hang nor a slowdown. Sort is parked in a nested event loop, waiting for input from a parentless, non-modal "Dependency Manager" window.** The sort itself finished in about 0.9 s once the window was dismissed.

Evidence ([`docs/audit/tools/repro_sort_hang.py`](tools/repro_sort_hang.py); stacks in [`docs/audit/evidence/bench_small/sort_hang_stacks.txt`](evidence/bench_small/sort_hang_stacks.txt)):

- I closed the startup windows (as a user would), then clicked the real Sort button. A sampler thread dumped the main-thread stack every 3 s:

  ```
  --- main thread @ 3.0s cpu=4.14s
  --- main thread @ 6.0s cpu=4.14s
  --- main thread @ 9.0s cpu=4.14s
    File "app/views/main_content_panel.py", line 1091, in _do_sort
      selected_deps = dialog.show_dialog(
    File "app/windows/missing_dependencies_dialog.py", line 148, in show_dialog
      loop.exec()
  ```

- Process CPU time stays flat at 4.14 s, so the process is idle and waiting.
- At t+10 s the only extra visible window is `MissingDependenciesDialog title='Dependency Manager' modal=False`, with `parent=None` and `main.isEnabled=True`.
- After that window was closed, `_do_sort` returned. The next log line is the expected `Created sorter instance…`.

Why a user experiences it as a hang:

- The dialog is created without a parent ([`main_content_panel.py:1086`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L1086)) and shown non-modal with its own `QEventLoop` ([`missing_dependencies_dialog.py:142-148`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/windows/missing_dependencies_dialog.py#L142-L148)).
- On a desktop it can open behind the main window. The main window stays enabled, so nothing signals that Sort is waiting.
- `show_dialog` ignores the `ApplicationModal` "Mods with Missing Properties" panel (C1/H4). Any such panel still open blocks input to the Dependency Manager as well.
- **Re-entrancy makes it worse** ([`docs/audit/tools/repro_sort_reentrancy.py`](tools/repro_sort_reentrancy.py), output in [`docs/audit/evidence/sort_reentrancy.txt`](evidence/sort_reentrancy.txt)):
  1. Clicking Sort again while the first dialog is open starts a second `_do_sort` and a second nested loop.
  2. Closing the first dialog then does **not** finish the first Sort, because nested loops unwind last-in-first-out:

  ```
  [ 1.9s] dialogs open=1; main window enabled=True -> clicking Sort again
  [ 3.8s] dialogs open=2; user closes the FIRST (outer Sort's) dialog
  [ 3.9s] after closing it: outer Sort returned? no; dialogs open=1
  [ 8.8s] inner Sort returned
  [10.2s] outer Sort returned
  ```

  The same pattern exists in `do_threaded_loading_animation` ([`main_content_panel.py:905-909`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L905-L909)) and in the `_do_refresh` wait on the settings dialog (`:996-998`).

If the coordinator's GUI run showed a spinning beachball with high CPU, that would be something else. In that case take a `py-spy dump`. Headlessly, all the evidence points to an idle wait on a hidden window.

Fix: give the dialog a parent and make it window-modal with `exec()`, or make Sort continuation-based (`finished` → continue). Disable the Sort and Refresh actions while a sort is pending.

## Findings, ranked

### Critical

**C1. Each Refresh leaks a "Mods with Missing Properties" panel that repopulates on every later refresh. Refresh time grows without bound and becomes minutes once a panel is visible.**

- `__check_and_warn_missing_mod_properties` ([`views/main_content_panel.py:747-797`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L747-L797)) runs on every refresh. It builds a new `MissingModPropertiesPanel`, shows it `ApplicationModal`, and registers it with `window_manager.register()`.
- `register()` appends to a list that is never pruned ([`services/window_manager.py:26-28`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/services/window_manager.py#L26-L28)).
- Every panel subscribes to `metadata_refreshed` ([`windows/base_mods_panel.py:114`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/windows/base_mods_panel.py#L114)), so all old panels repopulate their tables on each refresh. When a panel is visible, that population is O(n²) (hot spot 2).
- Measured:
  - 17.4 s (S) and 166 s (B) for a single Refresh with the startup panel still open;
  - 3.7 → 18 → 34 → 47 s over consecutive refreshes at S;
  - +5–8 % per refresh even when the user closes the panel each time.
- The content of the panel is wrong anyway (H4).

### High

**H1. Sort, Refresh and list rebuilds are UI-thread orchestration inside view classes. The cost is all overhead.**

- `_do_sort` lives in `MainContent` ([`views/main_content_panel.py:1061-1207`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L1061-L1207)). It compiles twice (`:1078`, `:1113`), runs the deps pre-check (hot spot 3), sorts (2 ms), then rebuilds both list widgets with per-item SQL (hot spot 1).
- Sort costs 2.0 s at B without the deps check and 3.1 s with it, of which the algorithm is 0.002 s.
- Startup takes 7.5 s, of which 3.3 s is `_insert_data_into_lists`.
- Every Sort, Clear, Import, Restore and Refresh rebuilds both lists from scratch.

**H2. Sort waits on a parentless non-modal dialog via a nested event loop, and can re-enter itself.** Details and evidence are in the "Sort hang" section above.

**H3. Git "corruption repair" deletes the repository's `.git` and reports success.**

- `_handle_git_error` ([`utils/git_utils.py:275-345`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/git_utils.py#L275-L345)) matches error text such as "object not found" and calls `_attempt_repository_repair(repo.path, …)` (`:191-272`).
- `pygit2.Repository.path` is the `.git/` directory, so the repair:
  1. recursively deletes `.git/`, losing local commits, branches and stashes;
  2. re-clones *into* `.git/` if a URL is known;
  3. otherwise returns `True`, which `git_pull` maps to `GitPullResult.UP_TO_DATE` (`:986`, `:1118`).
- The same handler runs from the passive `git_check_updates` (`:898-906`).
- An error with that text appears in normal situations, for example with shallow clones or after an upstream force-push.
- Experiment ([`git_repair_experiment.txt`](evidence/git_repair_experiment.txt)):

  ```
  before: .git exists = True commits = 1
  handler returned repaired = True (git_pull maps this to GitPullResult.UP_TO_DATE)
  after: .git exists = False | working tree files kept = ['About.xml']
  ```

**H4. The "Mods with Missing Properties" check is wrong by construction (the known issue, explained).**

- `WindowManager.get_missing_publishfieldid_paths` ([`services/window_manager.py:70-83`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/services/window_manager.py#L70-L83)) flags every mod whose `published_file_id` is `None`. It only skips Ludeon IDs and the user's ignore list. It never looks at `mod_type`.
- `ListedMod.published_file_id` ([`models/metadata/metadata_structure.py:365-397`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_structure.py#L365-L397)) reads `About/PublishedFileId.txt`, and if that is missing it **falls back to the folder name when the name is numeric**.
- Steam Workshop and SteamCMD mods live in numeric folders, so they can never be flagged. The only mods that can be flagged are local, git and scenario mods, which by definition have no Workshop ID.
- On a first launch with only local mods, every mod is listed (600 rows at S). The panel is `ApplicationModal`, shows on every refresh with no setting to disable it, and costs C1.
- The companion check `get_missing_packageid_paths` (`:54-68`) flags every non-`AboutXmlMod`, including `.rsc` scenarios, which have no package ID by design.
- The UI label says "Publish Field ID" (it should be PublishedFileId).
- Fix:
  - only consider mods whose type implies a Workshop origin and whose identity cannot be derived from the folder;
  - or drop the check entirely, since the Workshop ID is never actually missing for Workshop mods.

**H5. Sort silently removes mods from the active list, ignores the current order, and wipes the user's dividers.**

- **Duplicate package IDs.** `do_topo_sort` builds `packageid_to_path` with last-write-wins ([`sort/topo_sort.py:38-46`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/topo_sort.py#L38-L46)). If two copies with the same package ID are active, one vanishes. After `_insert_data_into_lists` it ends up in the inactive list (experiment E3: 3 in, 2 out). [`tests/sort/test_sort_integration.py:207-221`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/tests/sort/test_sort_integration.py#L207-L221) pins this as "may be a bug worth fixing".
- **Non-About entries.** Invalid folders and scenarios are dropped the same way (E4: 3 in, 2 out).
- **No-change check never fires.** `new_order != current_order` compares a `list` to a `set` ([`main_content_panel.py:1134`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L1134), `:1173`), so it is always `True`. Every Sort rebuilds both lists (2.1 s at B when already sorted).
- **Dividers.** Every Sort moves all dividers to the bottom and uncollapses them (`:1179-1185`), even when the order did not change.
- **Order is ignored.** Tier → topological level → name. The user's existing order of unconstrained mods is discarded (E8: user order C, A, B with B after C → A, C, B). A minimal-change topological sort, keeping the current order as the tie-breaker, would preserve manual curation, keep diffs small and make sorting idempotent.

**H6. Three divergent "missing dependency" implementations.**

1. List icons: `ModListWidget._check_missing_dependencies` ([`views/mods_panel.py:3407-3434`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L3407-L3434)). Honours `alternativePackageIds` **and** `KNOWN_MOD_REPLACEMENTS`.
2. Sort pre-check dialog: `build_dependencies_dialog_context` ([`services/dependency_resolver.py:154-235`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/services/dependency_resolver.py#L154-L235)). Honours alternatives only.
3. `MetadataController.get_missing_dependencies` ([`controllers/metadata_controller.py:425-449`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/metadata_controller.py#L425-L449)). Honours neither, and has no callers.

Experiment ([`deps_divergence.txt`](evidence/deps_divergence.txt)), with Prepatcher active and a mod depending on Harmony: the list shows no error, while the Sort dialog reports `{'some.mod': {'brrainz.harmony'}}`. Harmony is the most common dependency on the Workshop. Load-order violations, incompatibilities and version mismatch exist only in the view ([`mods_panel.py:3436-3813`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L3436-L3813)), so neither export, the CLI nor the sorter can reuse them.

### Medium

**M1. `modDependencies` are not ordering constraints by default.**

- The setting `use_moddependencies_as_loadTheseBefore` defaults to `False` ([`models/settings.py:117`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L117)).
- E5: a dependent sorts before its dependency (`['AA Uses Library', 'ZZ Library']`); with the flag on, the order is correct.
- RimWorld also doesn't infer an order from dependencies. But in practice a dependency nearly always has to load first, and many authors don't repeat it in `loadAfter`.
- The flag does handle conflicts well: explicit rules win and dropped inferred edges are logged ([`metadata_structure.py:625-664`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_structure.py#L625-L664)). It should be on by default, and the dropped edges should be shown to the user, not only logged.

**M2. Sort output is non-deterministic across launches.**

- Ties within a topological level are broken by display name only. Equal names keep `set` iteration order, which depends on `PYTHONHASHSEED`.
- E9: four same-named "Compat Patch" mods gave **6 different orders over 6 seeds** for Topological; Alphabetical also varies.
- Same-named mods (translations, patches) are common, so this shows up as spurious "unsaved changes" and noisy ModsConfig diffs.
- Fix: tie-break by `(name, package_id, path)`, or better, by current position (H5).

**M3. Cycle handling is all-or-nothing, and the cycle listing can blow up.**

- Any cycle aborts the whole sort (`(False, [])`), including unrelated mods (E1). There is no partial result. There is also no precedence among rule sources (About.xml vs community vs user) to break the weakest edge.
- The report enumerates **every** simple cycle with `nx.simple_cycles` and puts them in a `QMessageBox` ([`sort/topo_sort.py:71-95`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/topo_sort.py#L71-L95)).
- E2, dense strongly connected components: 6 nodes → 409 cycles; 8 → 16,064 cycles (625 KB of text); 9 → 125,664 cycles (5.7 MB). This is exponential.
- Fix: report SCCs (Tarjan) with one shortest cycle each, and name the rule source of each edge.
- The sort module also calls a Qt dialog directly ([`topo_sort.py:9, 85`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/topo_sort.py#L9)).

**M4. Tier contradictions are resolved silently.**

- E7: a `loadBottom` mod Z, with X `loadAfter` Z and HugsLib (tier 1) `loadAfter` X. Z and X are pulled into tier 1, and the "load last" mod is placed **first**. No warning is shown.
- Otherwise the tier model is coherent. Dependencies are pulled into tiers 0 and 1, and reverse dependencies into tier 3, so no `loadBefore`/`loadAfter` edge is lost across tiers (0 violations in E6).

**M5. Metadata pipeline: no parse cache, ineffective threading, duplicated state.**

- No cache keyed on About.xml mtime, so every Refresh, rule save ([`rule_editor_panel.py:1106-1119`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/windows/rule_editor_panel.py#L1106-L1119) → full `_do_refresh`) and DB update re-parses everything.
- `QThreadPool` gives no speedup (hot spot 6).
- Every About.xml is opened 3 times to sniff gzip and zstd, which only matters for save files ([`utils/xml.py:247-290`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/xml.py#L247-L290)).
- The incremental watchdog path `_parse_single_mod` ([`metadata_controller.py:609-642`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/metadata_controller.py#L609-L642)) differs from the full refresh: it passes `game_path` instead of `layout.content_root` and omits `case_insensitive_about_xml`. The same mod can therefore parse differently depending on how it was loaded.
- `steam_db` is passed to every parser worker but never used ([`metadata_mediator.py:319-427`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_mediator.py#L319-L427)).
- `AboutXmlMod.overall_rules` is a `cached_property` with a `clear_cache()` that nothing calls. That is harmless today only because every rule change triggers a full re-parse.
- State is duplicated:
  - `mods_metadata` (keyed by path), the widget `.paths` lists, the per-item `CustomListWidgetItemMetadata` and the aux SQLite DB all mirror the same facts;
  - `settings.active_mods_dividers` mirrors the widget's dividers;
  - "uuid" and "path" are the same string under two names, with bridging dictionaries rebuilt on each sort ([`main_content_panel.py:1126-1166`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L1126-L1166)).

**M6. Global singletons and hidden coupling.**

- Singletons: `MetadataController.instance()`, `AuxMetadataController.get_or_create_cached_instance`, `SteamcmdInterface.instance`, `MainContent.instance`, `app_globals.SETTINGS`, `EventBus()`.
- Model objects such as `CustomListWidgetItemMetadata` and `mod_sorting.get_mod_metadata` reach into `MetadataController.instance()`.
- Settings and schema modules import view dialogs ([`models/settings.py:32`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L32), [`utils/schema.py:7`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/schema.py#L7)).
- A Qt-free domain model, [`app/models/mod_list.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/mod_list.py) (413 lines: `ModEntry`, `ModList`, `ModListDiff`, `_steam` resolution), exists but is used only by its tests. It is a half-finished refactor; see also `TODO(debt)` in [`controllers/sort_controller.py:43`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/sort_controller.py#L43).

**M7. Startup and network behaviour.**

- `_update_databases_on_startup_if_enabled_silent` ([`controllers/main_content_controller.py:739-806`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/main_content_controller.py#L739-L806)) calls `check_internet_connection()` synchronously on the UI thread: 2 HEAD requests with a 10 s timeout each.
- It runs even when every database uses a local file path.
- Databases downloaded at startup are not applied until the next manual refresh, because `_notify_http_result_silent` only logs (`:915-926`). So a first-ever session sorts without community rules.

**M8. Rule data is silently dropped or unused.**

- Community-rules `incompatibleWith` entries (5 in the current DB) are dropped by the msgspec schema: `ExternalRule` has no such field ([`metadata_structure.py:679-683`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_structure.py#L679-L683)).
- SteamDB "required items" (`SteamDbEntry.dependencies`, 57k entries) are not used for dependency checks or sorting. They are used only for translations and the missing-mods panel ([`views/mods_panel.py:5685`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L5685), [`windows/missing_mods_panel.py:201`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/windows/missing_mods_panel.py#L201)).

### Low

- **L1.** The `_steam` suffix test is a substring match ([`metadata_controller.py:544-551`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/metadata_controller.py#L544-L551)). E.g. `author.my_steamworks` with a local and a Workshop copy activates **both** copies ([`list_experiments.txt`](evidence/list_experiments.txt)).
- **L2.** `get_mods_from_list` is quadratic (hot spot 5), while a `packageid_to_paths` cache sits unused next to it ([`metadata_controller.py:238-247`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/metadata_controller.py#L238-L247)).
- **L3.** Sorting the inactive list by tags issues 2 queries per mod ([`sort/mod_sorting.py:186-206`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/mod_sorting.py#L186-L206)): 272 ms at B, on the UI thread.
- **L4.** `ModsConfig.xml` is written non-atomically with `open(path, "w")` ([`utils/xml.py:146`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/xml.py#L146)). A crash mid-write corrupts the game's config. Write to a temp file and `os.replace` instead.
- **L5.** The watchdog doesn't handle moves or renames, so a renamed mod folder leaves a stale entry. It also spawns one `threading.Timer` per path ([`utils/watchdog.py:176-206`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/watchdog.py#L176-L206)).
- **L6.** The Alphabetical sort is deprecated (only a log warning) but still selectable, and it is wrong: E6 found 145 `loadBefore`/`loadAfter` violations over 200 random DAGs. It also never detects cycles.
- **L7.** About.xml has a lenient BeautifulSoup fallback ([`utils/xml.py:103-115`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/xml.py#L103-L115)), so mods that RimWorld rejects can show as valid.
- **L8.** Latent O(n²) in `recalculate_internal_errors_warnings`: `self.paths.index(...)` per mod and per rule ([`mods_panel.py:3577, 3480-3491`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L3577)). It measures 25 ms at 807 today.
- **L9.** `uuid not in set(new_order)` rebuilds the set for every element ([`main_content_panel.py:1194`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L1194)): 21 ms vs 0.04 ms with the set built once.
- **L10.** File search is over-engineered: three "algorithms" that differ only by extension filter, and two copies of `_read_file_with_fallback` ([`controllers/file_search_controller.py:145`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/file_search_controller.py#L145), [`utils/file_search.py:268`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/file_search.py#L268)).

## What a good RimWorld sorter should do, and how RimDeck compares

| Expectation | RimDeck |
| --- | --- |
| Honour `loadBefore`/`loadAfter`/`forceLoad*` with `*ByVersion` replacing (not adding to) the base list, case-insensitively | Yes ([`metadata_factory.py:572-614`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_factory.py#L572-L614)). Well done. |
| `modDependencies` (with `alternativePackageIds`) imply load-after | Off by default (M1) |
| Community and user rules: `loadTop`/`loadBottom` | Yes, via tiers; contradictions are silent (M4) |
| Deterministic and stable: same input gives the same output, minimal changes from the current order | No (M2, H5) |
| Never drop or reorder entries the user cannot see | Drops duplicates and non-About entries; wipes dividers (H5) |
| Cycles: explain them precisely, sort the rest, suggest which rule to drop | Aborts everything, exponential report (M3) |
| One validation engine shared by list icons, the Sort pre-check and export | Three engines (H6) |
| Off the UI thread | Algorithm yes in principle; everything around it no (H1) |

## Tests

- Subset `tests/sort tests/models tests/controllers`: **628 passed, 2 skipped, 7.7 s.**
- Full suite: **1660 passed, 31 skipped, 26.8 s** (`dev/audit/pytest_*.txt`). The slowest tests are privatebin crypto at about 1–2 s each and a large steamDB read at 2.5 s.

Assessment:

- **Sort (160 tests).** Good coverage of happy paths, tiers and cycles, but every test is a hand-written example.
  - Known bugs are pinned rather than fixed (`test_duplicate_package_ids_last_path_wins`).
  - There is no property-based check. A 200-case random-DAG property test immediately exposed the Alphabetical sort's 145 violations (E6).
  - There is no determinism test (M2).
- **Models and controllers.** Good on parsing details: ByVersion, case-insensitive About.xml lookup, the msgspec DBs.
- **The orchestration and validation layer, where most of the findings live, is barely tested.**
  - `_do_sort` is only asserted as "called" ([`tests/controllers/test_main_window_controller.py:98`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/tests/controllers/test_main_window_controller.py#L98)).
  - `recalculate_internal_errors_warnings` is covered only through [`tests/views/test_mods_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/tests/views/test_mods_panel.py).
  - There is no test for the missing-properties logic or for git repair.
  - There are no performance or regression tests. C1 and the per-item SQL pattern would be caught by a simple "Refresh twice at 2000 mods, under N seconds" test using the fixture generator.
- Overall, the suite is a decent safety net for the parts worth keeping and close to useless for the parts that need rebuilding.

## Separating the logic from the Qt UI

Lines in modules that import PySide6 (computed over `app/`):

| Package | Lines | In Qt-importing modules |
| --- | ---: | ---: |
| views | 19,646 | 100 % |
| windows | 6,687 | 97 % |
| controllers | 9,342 | 92 % |
| utils (incl. steam, github, …) | 20,125 | ~66 % |
| models | 3,890 | 35 % |
| services | 3,364 | 35 % |
| sort | 833 | 81 % (through `topo_sort` → `views.dialogue`) |
| **Total** | **64,401** | **80 %** |

- **Already Qt-free and reusable as-is (about 3.8k lines):** [`metadata_structure.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_structure.py), [`metadata_factory.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_factory.py), [`alphabetical_sort.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/alphabetical_sort.py), [`dependencies.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/dependencies.py), [`sort_controller.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/sort_controller.py) (apart from a transitive import), [`mod_list.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/mod_list.py), [`import_export_service.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/services/import_export_service.py), [`modlist_history_service.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/services/modlist_history_service.py), [`file_search.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/file_search.py), and the Steamworks wrapper.
- **Qt for no good reason (cheap fixes):**
  - `MetadataMediator` uses `QThreadPool`/`QMutex`; replace with `concurrent.futures` or remove.
  - `MetadataController` is a `QObject` only for 6 signals; use a plain observer.
  - `topo_sort.find_circular_dependencies` shows a dialog; return the data instead.
  - [`models/settings.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py) and [`utils/schema.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/schema.py) import `views.dialogue`.
  - `dependency_resolver` imports the Qt `MetadataController` type.
- **Business logic embedded in widgets, the real cost:**
  - [`views/main_content_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py) (3,359 lines, 52 `_do_*` actions): sort, refresh, import, export, save, restore and download orchestration.
  - [`views/mods_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py) (5,861 lines): all validation, the list identity model (`.paths`), filtering and search, aux-DB writes, plus a 1,050-line `eventFilter` context menu.
  - [`windows/base_mods_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/windows/base_mods_panel.py).
  - `SteamcmdInterface`, which stores batch state as private attributes on the `RunnerPanel` view ([`steamcmd/wrapper.py:386-417`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/steam/steamcmd/wrapper.py#L386-L417)).
  - `InstanceService`, which calls `QInputDialog` and `BinaryChoiceDialog` mid-operation ([`instance_service.py:520-560`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/services/instance_service.py#L520-L560)).
  - Git, troubleshooting and file-search controllers, with 30 dialog calls in the troubleshooting controller alone.
- **Estimate.**
  - A Qt-free core package (metadata, rules, compiled graph, sort, validation, ModsConfig and modlist I/O, aux DB repository) that a web frontend or different toolkit could drive needs:
    - about 1.5–2k lines moved or rewritten out of [`main_content_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py), [`mods_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py) and [`metadata_controller.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/metadata_controller.py);
    - about 300 lines of de-Qt-ing.
  - Roughly 2–3 engineer-weeks, starting from [`mod_list.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/mod_list.py) as the list model.
  - Steam, SteamCMD, git and instance flows would each need their UI prompts turned into callbacks or results: another 2–3 weeks.
  - The views would then be mostly replaced rather than ported.

## Verdict per area

| Area | Verdict | Why |
| --- | --- | --- |
| About.xml parsing and rule model (`metadata_factory`, `metadata_structure`) | **Keep** | Correct handling of ByVersion, forceLoad, `alternativePackageIds`, case-insensitive IDs and DLC defaults; Qt-free; well tested. Fix mod-type detection cost and the dropped `incompatibleWith`. |
| Compiled graph + tiered topological sort (`CompiledDependencyData`, `Sorter`, `do_topo_sort`) | **Keep, refactor edges** | Correct (0 violations) and fast. Add a deterministic, order-preserving tie-break; keep duplicates and non-About entries; SCC-based cycle reporting with partial sort; warn on tier contradictions; default deps-as-order on. |
| Alphabetical sort | **Remove** | Deprecated and demonstrably wrong (E6). |
| Sort driver (`_do_sort` in the view) | **Rebuild** | Lives in a widget, blocks the UI for 2–3 s, waits in a nested loop and can re-enter, wipes dividers, list≠set bug. Make it a pure service returning `(order, issues)`. |
| Validation and warnings (deps, incompatibilities, order, version) | **Rebuild** | Three divergent implementations, embedded in a 5.8k-line widget. One pure `validate(list, metadata, settings)` used by icons, the Sort dialog, export and CLI. |
| Missing-properties check | **Rebuild or delete** | Wrong by construction (H4), modal on every refresh, leaks panels (C1). |
| MetadataController / Mediator | **Refactor** | Sound responsibilities but singleton + `QObject`; quadratic list resolution; no parse cache; useless thread pool; incremental and full parse paths diverge. |
| Aux DB (`AuxMetadataController`, `aux_db_utils`) | **Refactor (access pattern)** | SQLite is fine. Load all rows for the instance into a dict once per rebuild and batch writes in one transaction. Removes about 1.6 s per list rebuild at 2000 mods. Drop the outdated mark-and-sweep. |
| External DBs (steamDB, community rules, Use This Instead, No Version Warning) | **Keep, refactor** | msgspec loading is fast and robust. Index steamDB by packageId once (O(1) lookups), apply startup downloads immediately, move the connectivity check off the UI thread. |
| Watchdog | **Keep** | Small, debounced. Handle moves and unify with the full parse path. |
| Instance management (`InstanceService`) | **Refactor** | Logic is reasonable (copy, clone, archive) but interleaved with modal prompts; separate the decisions from the file operations. |
| SteamCMD integration | **Refactor** | Script generation and batching are fine; state stashed on the `RunnerPanel` view and 28 dialog calls in the wrapper. |
| Steamworks (SteamworksPy in subprocesses) | **Keep** | Process isolation of steam_api is the right call; polling with fixed sleeps could be tightened. |
| Steam WebAPI / workshop browser | **Keep, refactor** (light audit) | Not deeply reviewed; same pattern of dialogs inside wrappers. |
| Git mod handling (`git_utils`, `git_worker`) | **Rebuild, shrink** | A 1.9k-line general git client (push, stash, commit) is scope creep for a mod manager, and the auto-"repair" destroys `.git` (H3). Keep clone and pull-fast-forward and status only, with no destructive auto-repair. |
| Troubleshooting | **Keep, refactor** | Useful destructive tools, correctly behind confirmations; 30 dialog calls in a controller should move to the view. |
| File search | **Rebuild (small)** | Over-engineered "algorithms" and duplicated readers; a simple background grep over mod paths is enough. |
| Save / restore / import / export / history (`import_export_service`, `modlist_history_service`, `mod_list_parser`) | **Keep** | Qt-free, sane `_steam` handling on export, Core/DLC preflight before save. Make ModsConfig writes atomic and fix the `_steam` substring bug (L1). |
| Test suite | **Keep, extend** | Good for the keepers; add property-based sort tests, determinism tests, and 2000-mod performance tests using [`make_fake_game.py`](tools/make_fake_game.py). |

**Overall:** keep and harden the domain core, rebuild the orchestration and validation layer as a Qt-free service with its own tests, and fix C1, H3 and H4 immediately, since they are cheap to fix and user-visible. A full rewrite of the logic is not warranted. A UI-toolkit change would mostly mean rewriting `views/` and `windows/`, which is where most of the problems live anyway.
