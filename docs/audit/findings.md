# Findings

Every must-fix finding from the audit, with code references pinned to commit `audit-ba` so line numbers stay valid as the code changes. Status is tracked in [milestones.md](milestones.md); this file is the reference.

## Release safety and fork identity

### F01

**Updater checks upstream releases.** The release check was hardcoded to the original project's repository and runs at startup by default, so a build would have offered the original project's releases and installed them over this app. Fixed in the initial commit: it now checks this repository.

Milestone: [M1](milestones.md#m1-fork-identity-and-safe-updates)

- [`app/utils/update_utils.py:44`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L44)
- [`app/models/settings.py:57`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L57)
- [`app/views/main_content_panel.py:856-880`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L856-L880)
- [Platform report, C1](platform.md#critical)

### F02

**Windows installer shares upstream's product ID.** The MSI UpgradeCode and component GUIDs were the original project's, so Windows would treat both as one product and each installer would replace the other. Fixed in the initial commit with new GUIDs.

Milestone: [M1](milestones.md#m1-fork-identity-and-safe-updates)

- [`packaging/msi/RimDeck.wxs:10`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/packaging/msi/RimDeck.wxs#L10)
- [`packaging/msi/RimDeck.wxs:99`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/packaging/msi/RimDeck.wxs#L99)
- [`packaging/msi/RimDeck.wxs:113`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/packaging/msi/RimDeck.wxs#L113)
- [Platform report, C1](platform.md#critical)

### F03

**Copy existing data from the original app on first launch.** The data folder and single-instance lock are now named after this app, so it no longer shares settings with the original app. Still missing: on first launch, copy the original app's settings, databases, mod lists and instances into the new folder once, leaving the originals untouched.

Milestone: [M1](milestones.md#m1-fork-identity-and-safe-updates)

- [`app/utils/app_info.py:90`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/app_info.py#L90)
- [`app/utils/app_info.py:117`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/app_info.py#L117)
- [`app/__main__.py:240`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/__main__.py#L240)
- [Platform report, C1](platform.md#critical)

### F04

**Updater verifies nothing but file size.** Downloads are only checked for being non-empty, then install scripts run with admin rights. The checksum in the shell updater is read from inside the downloaded archive. CI produces build attestations that the app never checks. Needs a signed manifest with per-file SHA-256, verified against a key built into the app.

Milestone: [M1](milestones.md#m1-fork-identity-and-safe-updates)

- [`app/utils/update_utils.py:1467-1482`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L1467-L1482)
- [`update.sh`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/update.sh)
- [`.github/workflows/build.yml:246-311`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/build.yml#L246-L311)
- [`app/utils/update_utils.py:301-335`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L301-L335)
- [Platform report, C2](platform.md#critical)

### F05

**Predictable update temp folder used with root rights on Linux.** The staging folder name is derived from the timestamp and reused if it exists, then handed to a sudo rsync. Another local user can pre-create it. Use a private temp directory.

Milestone: [M1](milestones.md#m1-fork-identity-and-safe-updates)

- [`app/utils/update_utils.py:1530-1535`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L1530-L1535)
- [Platform report, M4](platform.md#medium)

### F06

**Updater holds the whole download in memory twice.** The download grows a byte array and then copies it, about 650 MB at peak for the macOS archive. Stream to a temp file instead.

Milestone: [M1](milestones.md#m1-fork-identity-and-safe-updates)

- [`app/utils/update_utils.py:1409-1465`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L1409-L1465)
- [Platform report, M3](platform.md#medium)

### F07

**Edge builds are always offered a downgrade.** The commit suffix is sliced from an XML element instead of its text, producing `+[]`, and `-edge` versions don't parse, so Edge builds count as 0.0.0.

Milestone: [M1](milestones.md#m1-fork-identity-and-safe-updates)

- [`app/utils/app_info.py:101`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/app_info.py#L101)
- [`app/utils/update_utils.py:796-798`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L796-L798)
- [`.github/workflows/get_version_info.yml:75`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/get_version_info.yml#L75)
- [Platform report, H2](platform.md#high)

### F08

**Builds without a version accept any update.** Builds missing version metadata ask "update anyway?" and then treat themselves as 0.0.0.

Milestone: [M1](milestones.md#m1-fork-identity-and-safe-updates)

- [`app/utils/update_utils.py:776-789`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L776-L789)
- [Platform report, C1](platform.md#critical)

### F09

**Two Linux downloads match the updater's filter.** The Ubuntu 22.04 and 24.04 archives both match, and match order decides which is installed.

Milestone: [M1](milestones.md#m1-fork-identity-and-safe-updates)

- [`app/utils/update_utils.py:1047`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L1047)
- [Platform report, L5](platform.md#low)

### F10

**No code signing or notarization.** No OS signs its builds. macOS users have to bypass Gatekeeper, Windows shows SmartScreen, and the macOS bundle ID falls back to the bare executable name with version 1.0.

Milestone: [M8](milestones.md#m8-distribution-polish)

- [`app/__main__.py:1-26`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/__main__.py#L1-L26)
- [`.github/workflows/build.yml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/build.yml)
- [Platform report, H1](platform.md#high)

### F11

**Unverified build inputs.** The build downloads the latest texture optimizer release with no checksum, the AppImage tool is pinned but not hash-checked, and Steamworks binaries are committed by hand.

Milestone: [M8](milestones.md#m8-distribution-polish)

- [`distribute.py:361-420`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/distribute.py#L361-L420)
- [`packaging/linux/build-appimage.sh:107`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/packaging/linux/build-appimage.sh#L107)
- [Platform report, M5](platform.md#medium)

### F12

**Tokens stored in plain text.** The GitHub token and Steam API key are written to the settings file. Use the OS keychain.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`app/models/settings.py:154`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L154)
- [`app/models/settings.py:232`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L232)
- [Platform report, M7](platform.md#medium)

### F13

**Rebrand everything that pointed at the original project.** App name, data folder, single-instance lock, environment variables, about 160 user-facing strings in every translation, help links, export images, Linux desktop IDs, installer IDs, Nix cache and workflow names. Done in the initial commit; the inherited logo and the externally hosted sources are tracked as their own items.

Milestone: [M1](milestones.md#m1-fork-identity-and-safe-updates)

- [Platform report, rebrand status](platform.md#rebrand-status)

## Crashes and data loss

### F14

**Missing theme folder crashes the app.** The fallback warning's translated format string contains `{self.default_theme}`, which raises KeyError, so a missing or misplaced theme folder crashes startup instead of falling back.

Milestone: [M1](milestones.md#m1-fork-identity-and-safe-updates)

- [`app/controllers/theme_controller.py:166-179`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/theme_controller.py#L166-L179)
- [UI report, item 3](ui.md#critical)

### F15

**Git repair deletes the repository history.** On an "object not found" error the repair deletes `.git`, then reports the mod as up to date. The same handler runs from the passive update check. Reproduced.

Milestone: [M2](milestones.md#m2-data-safety-and-blocking-bugs)

- [`app/utils/git_utils.py:191-272`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/git_utils.py#L191-L272)
- [`app/utils/git_utils.py:275-345`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/git_utils.py#L275-L345)
- [`git_repair_experiment.txt`](evidence/git_repair_experiment.txt)
- [Logic report, H3](logic.md#high)

### F16

**Game mod list written in place.** ModsConfig.xml is opened for writing directly, so a crash mid-save corrupts the game's config. Write to a temp file and replace atomically.

Milestone: [M2](milestones.md#m2-data-safety-and-blocking-bugs)

- [`app/utils/xml.py:146`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/xml.py#L146)
- [Logic report, L4](logic.md#low)

### F17

**Sort drops duplicate and invalid entries.** Package IDs are mapped last-write-wins, so active duplicates and invalid entries vanish from the active list on sort. An existing test pins this as a possible bug.

Milestone: [M2](milestones.md#m2-data-safety-and-blocking-bugs)

- [`app/sort/topo_sort.py:38-46`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/topo_sort.py#L38-L46)
- [`tests/sort/test_sort_integration.py:207-221`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/tests/sort/test_sort_integration.py#L207-L221)
- [`sort_experiments.txt`](evidence/sort_experiments.txt)
- [Logic report, H5](logic.md#high)

### F18

**IDs containing "_steam" activate both copies.** The Workshop suffix check is a substring match, so a mod like `author.my_steamworks` with a local and Workshop copy activates both.

Milestone: [M2](milestones.md#m2-data-safety-and-blocking-bugs)

- [`app/controllers/metadata_controller.py:544-551`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/metadata_controller.py#L544-L551)
- [`list_experiments.txt`](evidence/list_experiments.txt)
- [Logic report, L1](logic.md#low)

### F19

**Moved or renamed mod folders leave stale entries.** The file watcher doesn't handle moves and spawns one timer per path.

Milestone: [M2](milestones.md#m2-data-safety-and-blocking-bugs)

- [`app/utils/watchdog.py:176-206`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/watchdog.py#L176-L206)
- [Logic report, L5](logic.md#low)

## Sorting correctness

### F20

**Sort discards the user's order.** Ties are broken by tier, topological level, then name, so the order of unconstrained mods is thrown away. Use the current position as the tie-breaker so sorting is minimal-change and repeatable.

Milestone: [M3](milestones.md#m3-correct-sorting)

- [`app/views/main_content_panel.py:1061-1207`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L1061-L1207)
- [`sort_experiments.txt`](evidence/sort_experiments.txt)
- [Logic report, H5](logic.md#high)

### F21

**Sort is not deterministic.** Same-named mods keep set iteration order, which changes per launch: 6 different orders over 6 runs. Shows up as false "unsaved changes".

Milestone: [M3](milestones.md#m3-correct-sorting)

- [`sort_experiments.txt`](evidence/sort_experiments.txt)
- [Logic report, M2](logic.md#medium)

### F22

**Every sort moves dividers to the bottom.** Dividers are moved and expanded on every sort, and the no-change check compares a list to a set so it never fires.

Milestone: [M3](milestones.md#m3-correct-sorting)

- [`app/views/main_content_panel.py:1134`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L1134)
- [`app/views/main_content_panel.py:1179-1185`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L1179-L1185)
- [Logic report, H5](logic.md#high)

### F23

**Dependencies don't affect load order by default.** "Use dependency rules for sorting" defaults to off, so a mod can sort above the library it needs. Turn it on and show dropped inferred edges to the user.

Milestone: [M3](milestones.md#m3-correct-sorting)

- [`app/models/settings.py:117`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L117)
- [`app/models/metadata/metadata_structure.py:625-664`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_structure.py#L625-L664)
- [Logic report, M1](logic.md#medium)

### F24

**Any cycle aborts the whole sort.** There is no partial result, and the report enumerates every simple cycle into a popup, which grows exponentially. Report strongly connected components with one shortest cycle each and the rule source of each edge.

Milestone: [M3](milestones.md#m3-correct-sorting)

- [`app/sort/topo_sort.py:71-95`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/topo_sort.py#L71-L95)
- [`sort_experiments.txt`](evidence/sort_experiments.txt)
- [Logic report, M3](logic.md#medium)

### F25

**Tier contradictions resolved silently.** A load-last mod can be pulled to the top by other rules with no warning.

Milestone: [M3](milestones.md#m3-correct-sorting)

- [`sort_experiments.txt`](evidence/sort_experiments.txt)
- [Logic report, M4](logic.md#medium)

### F26

**Three dependency checks that disagree.** List icons, the sort pre-check and the metadata controller each implement missing-dependency logic differently. Example: with Prepatcher active, the list shows no error while the sort dialog reports Harmony missing. Merge into one Qt-free function.

Milestone: [M3](milestones.md#m3-correct-sorting)

- [`app/views/mods_panel.py:3407-3434`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L3407-L3434)
- [`app/services/dependency_resolver.py:154-235`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/services/dependency_resolver.py#L154-L235)
- [`app/controllers/metadata_controller.py:425-449`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/metadata_controller.py#L425-L449)
- [`deps_divergence.txt`](evidence/deps_divergence.txt)
- [Logic report, H6](logic.md#high)

### F27

**Rule data dropped or unused.** Community-rules incompatibility entries are dropped by the schema, and Steam's required-items data is not used for dependency checks or sorting.

Milestone: [M3](milestones.md#m3-correct-sorting)

- [`app/models/metadata/metadata_structure.py:679-683`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_structure.py#L679-L683)
- [`app/views/mods_panel.py:5685`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L5685)
- [Logic report, M8](logic.md#medium)

### F28

**Remove alphabetical sort.** It breaks load rules, 145 violations in 200 random cases, never detects cycles, and is still selectable.

Milestone: [M3](milestones.md#m3-correct-sorting)

- [`app/sort/alphabetical_sort.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/alphabetical_sort.py)
- [`sort_experiments.txt`](evidence/sort_experiments.txt)
- [Logic report, L6](logic.md#low)

### F29

**Lenient XML fallback accepts broken mods.** A BeautifulSoup fallback parses About.xml files that RimWorld would reject, so broken mods show as valid.

Milestone: [M3](milestones.md#m3-correct-sorting)

- [`app/utils/xml.py:103-115`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/xml.py#L103-L115)
- [Logic report, L7](logic.md#low)

### F30

**File-watcher reload parses differently from full refresh.** The incremental path passes a different root and omits the case-insensitive lookup setting.

Milestone: [M3](milestones.md#m3-correct-sorting)

- [`app/controllers/metadata_controller.py:609-642`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/metadata_controller.py#L609-L642)
- [Logic report, M5](logic.md#medium)

## Performance and freezes

### F31

**Refresh leaks a panel and gets slower every time.** Every refresh opens a new missing-properties panel that is never released and reloads on each later refresh. Consecutive refreshes at 600 mods: 3.7, 18, 34, 47 seconds; 166 seconds for one refresh at 2000 mods with the panel open.

Milestone: [M2](milestones.md#m2-data-safety-and-blocking-bugs)

- [`app/views/main_content_panel.py:747-797`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L747-L797)
- [`app/services/window_manager.py:26-28`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/services/window_manager.py#L26-L28)
- [`app/windows/base_mods_panel.py:114`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/windows/base_mods_panel.py#L114)
- [`bench_small/results_app.txt`](evidence/bench_small/results_app.txt)
- [`bench_big/results_app.txt`](evidence/bench_big/results_app.txt)
- [Logic report, C1](logic.md#critical)

### F32

**Sort waits on a hidden window.** Sort waits in a nested event loop on a parentless, non-modal Dependency Manager that can open behind the main window. Clicking Sort again nests a second wait.

Milestone: [M2](milestones.md#m2-data-safety-and-blocking-bugs)

- [`app/windows/missing_dependencies_dialog.py:148`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/windows/missing_dependencies_dialog.py#L148)
- [`bench_small/sort_hang_stacks.txt`](evidence/bench_small/sort_hang_stacks.txt)
- [`sort_reentrancy.txt`](evidence/sort_reentrancy.txt)
- [Logic report, H2](logic.md#high)

### F33

**List rebuilds hit the database per mod on the UI thread.** Sort, Refresh, Clear, Import and Restore rebuild both lists with about six queries and a commit per mod: 2 to 3 second freezes at 2000 mods and a 7.5 second startup. The sort algorithm itself takes 2 ms.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`app/views/mods_panel.py:3989-4016`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L3989-L4016)
- [`app/utils/custom_list_widget_item_metadata.py:77-131`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/custom_list_widget_item_metadata.py#L77-L131)
- [`bench_big/results.txt`](evidence/bench_big/results.txt)
- [Logic report, H1](logic.md#high)

### F34

**No parse cache.** Every refresh re-parses every About.xml, the dependency pre-check re-reads about 26,000 files, each About.xml is opened three times, and the parsing threads give no speedup.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`app/services/dependency_resolver.py:54-113`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/services/dependency_resolver.py#L54-L113)
- [`app/utils/xml.py:247-290`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/xml.py#L247-L290)
- [`parse_microbench.txt`](evidence/parse_microbench.txt)
- [Logic report, M5](logic.md#medium)

### F35

**Blocking network checks at startup.** Two HEAD requests with 10 second timeouts run on the UI thread, even with local databases, and downloaded databases aren't applied until the next refresh.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`app/controllers/main_content_controller.py:739-806`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/main_content_controller.py#L739-L806)
- [`app/controllers/main_content_controller.py:915-926`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/main_content_controller.py#L915-L926)
- [Logic report, M7](logic.md#medium)

### F36

**Heavy imports at startup.** About 0.9 of 1.86 seconds of import time is sqlalchemy, networkx, PyGithub and steam. Lazy-load or drop them.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [Platform report, M2](platform.md#medium)

### F37

**Downloads are 166 to 323 MB.** Most of it is the Chromium engine behind the embedded Workshop browser. Replace with open-in-browser, paste a link and steam:// links, or ship it as an optional component.

Milestone: [M8](milestones.md#m8-distribution-polish)

- [`app/utils/steam/steambrowser/browser.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/steam/steambrowser/browser.py)
- [`distribute.py:47`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/distribute.py#L47)
- [Platform report, H3](platform.md#high)

## Interface

### F38

**Three blocking popups on first launch.** SteamCMD setup, missing properties and Steam integration appear in sequence before the app is usable. Replace with a first-run setup flow.

Milestone: [M6](milestones.md#m6-main-screen-rebuild)

- [screenshot](screens/first-run-steamcmd.png)
- [screenshot](screens/first-run-missing-properties.png)
- [screenshot](screens/first-run-steam-integration.png)
- [UI report, item 1](ui.md#critical)

### F39

**Remove the missing-properties check.** It flags mods without a Workshop ID, but Workshop mods fall back to their folder name, so only local mods, which never have one, can be flagged. The package-ID half flags scenarios, which have none by design.

Milestone: [M2](milestones.md#m2-data-safety-and-blocking-bugs)

- [`app/services/window_manager.py:54-83`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/services/window_manager.py#L54-L83)
- [`app/models/metadata/metadata_structure.py:365-397`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_structure.py#L365-L397)
- [screenshot](screens/first-run-missing-properties.png)
- [Logic report, H4](logic.md#high)

### F40

**Popups as the main feedback channel.** 355 call sites open a blocking dialog. Replace with inline status and non-blocking notifications; keep modals for real decisions.

Milestone: [M5](milestones.md#m5-design-system)

- [`app/views/dialogue.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/dialogue.py)
- [UI report, design-system debt](ui.md#measured-design-system-debt)

### F41

**No design system.** Five themes of about 1,200 lines each recolor one layout. The default uses 32 colors, 5 font sizes, 14 spacing values, and 38 inline style overrides bypass it.

Milestone: [M5](milestones.md#m5-design-system)

- [`themes/RimPy/style.qss`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/themes/RimPy/style.qss)
- [screenshot](screens/themes.png)
- [UI report, design-system debt](ui.md#measured-design-system-debt)

### F42

**Boxes inside boxes.** 17 group boxes and 10 frames nest content, with large outer padding and a stray divider in the main panel.

Milestone: [M5](milestones.md#m5-design-system)

- [screenshot](screens/main.png)
- [UI report, item 15](ui.md#medium)

### F43

**Mod list rows are full widgets.** Each row is a widget inserted per item, which is heavy at scale and hard to style. Rebuild with a model and painted delegate.

Milestone: [M6](milestones.md#m6-main-screen-rebuild)

- [`app/views/mods_panel.py:1161`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L1161)
- [UI report, design-system debt](ui.md#measured-design-system-debt)

### F44

**Selection barely visible or unreadable.** Default theme: slightly lighter gray behind red text. SunSet and Wood: red text on orange.

Milestone: [M6](milestones.md#m6-main-screen-rebuild)

- [screenshot](screens/main.png)
- [screenshot](screens/themes.png)
- [UI report, item 5](ui.md#high)

### F45

**Noisy rows.** Folder and XML icons on every row, a NEW badge on every mod on first launch, problem reasons only on hover, warnings on inactive mods.

Milestone: [M6](milestones.md#m6-main-screen-rebuild)

- [screenshot](screens/main.png)
- [UI report, item 4](ui.md#high)

### F46

**No primary action.** Refresh, Clear, Restore, Sort, Save and Run are six identical buttons, with the destructive Clear beside Sort and Save.

Milestone: [M6](milestones.md#m6-main-screen-rebuild)

- [`app/views/main_window.py:137-142`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_window.py#L137-L142)
- [screenshot](screens/main.png)
- [UI report, item 6](ui.md#high)

### F47

**Jargon on main buttons.** "Check 'Use This Instead' Database" and "Check Dependencies" as full-width buttons.

Milestone: [M6](milestones.md#m6-main-screen-rebuild)

- [screenshot](screens/main.png)
- [UI report, item 6](ui.md#high)

### F48

**Mod detail panel layout.** Label and value columns misalign, notes and description sit in separate bordered scroll boxes, empty fields like "Unknown" take space, large empty area when nothing is selected.

Milestone: [M6](milestones.md#m6-main-screen-rebuild)

- [`app/views/mod_info_panel.py:121`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mod_info_panel.py#L121)
- [screenshot](screens/main.png)
- [UI report, item 7](ui.md#high)

### F49

**Seven search controls per list.** Search field, field picker, magnifier, Tags, eye toggle, sort-field picker and Desc toggle, several unlabeled.

Milestone: [M6](milestones.md#m6-main-screen-rebuild)

- [`app/views/mods_panel.py:4419-4423`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L4419-L4423)
- [screenshot](screens/main.png)
- [UI report, item 8](ui.md#high)

### F50

**Tabs and buttons shift on state change.** Unselected tabs get a 2 px top margin so the bar jumps on switch; pressed buttons switch to an inset border.

Milestone: [M5](milestones.md#m5-design-system)

- [`themes/RimPy/style.qss:310`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/themes/RimPy/style.qss#L310)
- [`themes/RimPy/style.qss:265-268`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/themes/RimPy/style.qss#L265-L268)
- [UI report, item 11](ui.md#medium)

### F51

**Tools at the same level as the mod manager.** Log readers, file search and troubleshooting are top-level tabs beside the main screen.

Milestone: [M7](milestones.md#m7-secondary-screens)

- [`app/views/main_window.py:100-200`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_window.py#L100-L200)
- [UI report, item 11](ui.md#medium)

### F52

**Secondary screens unfinished.** "Do nothing and exit" inside the ACF reader tab, neon colors and raw names like "Mod_issue" in Player Log, an unlabeled "▼" and plain-text Stop in File Search, no empty states.

Milestone: [M7](milestones.md#m7-secondary-screens)

- [screenshot](screens/acf-reader.png)
- [screenshot](screens/player-log.png)
- [screenshot](screens/file-search.png)
- [UI report, item 12](ui.md#medium)

### F53

**Destructive troubleshooting actions in plain view.** "Clear All Mods", which deletes every mod, and "Apply Recovery" are prominent buttons in a normal tab.

Milestone: [M7](milestones.md#m7-secondary-screens)

- [screenshot](screens/troubleshooting.png)
- [UI report, item 13](ui.md#medium)

### F54

**Rule editor needs prior knowledge.** Raw XML tag names as labels, clipped button text, unexplained "C" and "U" buttons, eight empty boxes with no guidance.

Milestone: [M7](milestones.md#m7-secondary-screens)

- [`app/windows/rule_editor_panel.py:108`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/windows/rule_editor_panel.py#L108)
- [screenshot](screens/rule-editor.png)
- [UI report, item 9](ui.md#high)

### F55

**Settings dialog.** Nine overflowing tabs, clipped text, mixed alignment, Windows path hints on macOS, developer jargon, dependency rules off by default.

Milestone: [M7](milestones.md#m7-secondary-screens)

- [`app/views/settings_dialog.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/settings_dialog.py)
- [screenshot](screens/settings-locations.png)
- [screenshot](screens/settings-sorting.png)
- [screenshot](screens/settings-advanced.png)
- [UI report, item 10](ui.md#high)

### F56

**No responsive layout.** Names truncate at 1280x760 and everything stretches on large screens.

Milestone: [M6](milestones.md#m6-main-screen-rebuild)

- [screenshot](screens/themes.png)
- [UI report, item 14](ui.md#medium)

### F57

**Inconsistent naming.** PackageID, Package ID and PackageId on different screens, and the wrong term "Publish Field ID".

Milestone: [M5](milestones.md#m5-design-system)

- [UI report, item 17](ui.md#low)

### F58

**Missing basics.** No light theme, no visible keyboard shortcuts, a status bar that only shows the game version.

Milestone: [M5](milestones.md#m5-design-system)

- [UI report, items 15, 16, 18](ui.md#low)

## Code structure

### F59

**Business logic inside screens.** One 3,400-line view singleton runs sorting, SteamCMD, Steamworks, git, uploads and game launch; one 1,048-line event filter builds the mod context menu; 34 functions exceed 150 lines.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`app/views/main_content_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py)
- [`app/views/mods_panel.py:1720`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L1720)
- [`app/controllers/main_content_controller.py:1573`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/main_content_controller.py#L1573)
- [Platform report, H4](platform.md#high)

### F60

**Core cannot run without Qt widgets.** The settings model imports dialogs and the sorter opens a dialog itself, so even the model meant to be Qt-free pulls in widgets. Cutting three import edges frees most of the domain layer.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`app/models/settings.py:13`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L13)
- [`app/models/settings.py:32`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L32)
- [`app/sort/topo_sort.py:8`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/topo_sort.py#L8)
- [Platform report, H4](platform.md#high)

### F61

**Unused Qt-free mod list model.** A domain model for mod lists, diffs and ModsConfig exists but only its tests use it. Adopt it.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`app/models/mod_list.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/mod_list.py)
- [`app/controllers/sort_controller.py:43`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/sort_controller.py#L43)
- [Logic report, M6](logic.md#medium)

### F62

**Nested event loops and mixed threading.** Nine nested event loops let other slots run mid-operation; QThread, QThreadPool, raw threads, executors and QProcess are mixed.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`app/views/main_content_panel.py:905-909`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L905-L909)
- [`app/utils/update_utils.py:1257`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L1257)
- [Platform report, M8](platform.md#medium)

### F63

**Same data stored in four places.** Metadata dict, widget path lists, per-row data and the aux database mirror each other; dividers are stored twice; uuid and path are the same string under two names.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`app/views/main_content_panel.py:1126-1166`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L1126-L1166)
- [Logic report, M5](logic.md#medium)

### F64

**Global event bus and singletons.** A 90-signal global bus and nine singletons make control flow implicit; orchestration files have 11 to 40% test coverage.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`app/utils/event_bus.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/event_bus.py)
- [Platform report, M9](platform.md#medium)

### F65

**Dead and duplicated code.** About 89 unreferenced functions or classes, a dead duplicate release check, stale comments, and git logic split across three subsystems.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`app/views/main_content_panel.py:856`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L856)
- [`app/utils/update_utils.py:78`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L78)
- [Platform report, M6](platform.md#medium)

### F66

**Library cleanup.** aiohttp is unused at runtime; steam is abandoned since 2022 and silently supplies two undeclared imports; steamfiles is abandoned since 2020 and pulls protobuf; toposort and networkx, zstandard, and BeautifulSoup can be replaced by the standard library or lxml.

Milestone: [M4](milestones.md#m4-qt-free-core-and-speed)

- [`pyproject.toml:8-34`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/pyproject.toml#L8-L34)
- [Platform report, M1](platform.md#medium)

### F67

**Steamworks binaries from an abandoned fork.** Mirror SteamworksPy under the fork and build the native libraries in CI from a pinned SDK.

Milestone: [M8](milestones.md#m8-distribution-polish)

- [`.gitmodules`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.gitmodules)
- [Platform report, M1](platform.md#medium)

## Identity leftovers

### F68

**Replace the inherited logo and icons.** The app icon, window icon and animated logo are still the original project's artwork under new file names.

Milestone: [M5](milestones.md#m5-design-system)

- [`themes/default-icons/RimDeck_Icon_64x64.svg`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/themes/default-icons/RimDeck_Icon_64x64.svg)
- [`themes/default-icons/AppIcon_a.png`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/themes/default-icons/AppIcon_a.png)
- [`app/utils/gui_info.py:62`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/gui_info.py#L62)

### F69

**Externally hosted sources still owned by the original project.** The default Steam Workshop and community rules databases, the steamfiles git dependency and the SteamworksPy submodule are downloaded from the original project's GitHub organization. Mirror them, replace them, or keep them deliberately.

Milestone: [M8](milestones.md#m8-distribution-polish)

- [`app/models/settings.py:65-76`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L65-L76)
- [`pyproject.toml:37`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/pyproject.toml#L37)
- [`.gitmodules`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.gitmodules)
- [Platform report, M1](platform.md#medium)
