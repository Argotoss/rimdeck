# RimDeck platform audit: libraries, packaging, architecture, fork identity

Scope: worktree `rimdeck` (branch `audit`, base `18e52bcb`), audited 2026-10-23.
Nothing was built. The commands that were run were the test suite, the type checkers,
ruff, import-time profiling, a coverage run and read-only GitHub/PyPI API queries.
Raw logs are in `docs/audit/evidence/` (`pytest.log`, `cov.log`, `mypy.log`, `pyright.log`,
`ruff.log`, `importtime.txt`).

## Key numbers

| Metric | Value |
| --- | --- |
| App source | 64,401 lines in 236 files: views 19.6k, utils 20.1k, controllers 9.3k, windows 6.7k, models 3.9k, services 3.4k, sort 0.8k, cli 0.2k |
| Tests | 114 test files, 26.6k lines. **1660 passed, 31 skipped, 32.4 s** (34.4 s wall). Coverage 45% overall |
| Coverage of hotspots | [`main_content_controller.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/main_content_controller.py) 11%, [`update_utils.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py) 28%, [`steambrowser/browser.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/steam/steambrowser/browser.py) 28%, [`git_utils.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/git_utils.py) 30%, [`mods_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py) 37%, [`main_content_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py) 40%. By contrast `sort/*` is 82-96% and [`metadata_factory.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_factory.py) 81% |
| Static checks | mypy 8.2 s, pyright 8.8 s, ruff 0.9 s, all clean on `app/` and `tests/`. The only errors were in untracked files under `dev/`, because the checkers scan `.` |
| Startup imports | `import app.controllers.app_controller` takes **1.86 s** (warm). The biggest contributors are sqlalchemy 298 ms, networkx 284 ms, PyGithub 231 ms, requests 101 ms, steam.webapi 98 ms and bs4 49 ms |
| Upstream v1.17.3 artifacts | macOS arm64 tar.gz 312 MB, macOS x86_64 323 MB, Ubuntu tar.gz 257 MB, AppImage 230 MB, Windows zip 202 MB, MSI 166 MB |
| Upstream CI build times | Windows 12 min, macOS arm64 5 min, macOS Intel 11 min, Ubuntu 22.04 29 min, Ubuntu 24.04 6 min |

---

## Ranked findings

### CRITICAL

**C1. A fork build would offer to update its users back to the original project, and its Windows installer was the same product as the original's.**

- The release endpoint is hardcoded at [`app/utils/update_utils.py:44`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L44): `GITHUB_API_URL` pointing at the original project's releases. A second, dead copy is at [`app/views/main_content_panel.py:858`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L858).
- The update check runs at startup by default ([`app/models/settings.py:57`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L57), `check_for_update_startup: bool = True`).
- Versions come from `PaulHatch/semantic-version` over the fork's own tags ([`build.yml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/build.yml)). If the fork's version is ever below upstream's (for example after restarting at v0.x or v2-less numbering), every launch shows "An update has been released". Accepting it downloads the upstream artifact, which [`update.sh`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/update.sh) (rsync into the bundle) or [`update.bat`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/update.bat) (robocopy) then installs over the fork.
- Builds without `version.xml` report "Unknown version". `_parse_current_version` ([`update_utils.py:776-789`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L776-L789)) asks "update anyway?", and answering yes treats the build as 0.0.0, so it installs upstream.
- MSI `UpgradeCode="d4f7c3b9-8a5e-4e52-bb9f-3c2d1f7a9e24"` ([`packaging/msi/RimDeck.wxs:10`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/packaging/msi/RimDeck.wxs#L10)) and component GUIDs (`:99`, `:113`) are shared with upstream. Windows will treat the fork MSI and upstream MSI as versions of one product, and each will uninstall or replace the other.
- The data folder is shared. `PlatformDirs(appname="RimDeck")` ([`app/utils/app_info.py:117`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/app_info.py#L117), name set at `:90`) gives the same `settings.json`, `dbs/`, instances, browser profile and `rimdeck.lock` single-instance lock ([`app/__main__.py:240`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/__main__.py#L240)). The fork and upstream therefore cannot run side by side, and they will overwrite each other's settings.

**C2. The updater does no integrity checks: it downloads, extracts and runs code, sometimes elevated, trusting only TLS and the GitHub account.**

- The only content check is size: empty or under 1 KB (`_validate_download`, [`update_utils.py:1467-1482`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L1467-L1482)). There is no hash, signature or attestation check.
- [`update.sh`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/update.sh) has a `verify_checksum` that reads `checksum.sha256` from inside the downloaded archive itself, so it protects nothing. No workflow produces that file, and a missing file is a warning, not a failure.
- CI generates GitHub build-provenance attestations ([`build.yml:246-311`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/build.yml#L246-L311)), but the client never verifies them.
- Elevation paths:
  - macOS: `sudo` inside `osascript ... do script` ([`update_utils.py:308-314`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L308-L314)).
  - Linux: `sudo` in a terminal (`:231-232`, `:261-277`).
  - Windows: `powershell ... Start-Process cmd -Verb RunAs` (`:331-335`) or `msiexec` (`:2468-2480`).
  - All launched with `shell=True` (`:2277-2318`, `:2383-2418`).
- Because the download goes through `requests`, the files never get `com.apple.quarantine`. The self-updater therefore installs unsigned, un-notarized code with no Gatekeeper evaluation.
- Consequence for a fork: anyone who compromises the fork owner's GitHub account (or a release-capable workflow token) gets code execution, sometimes as admin, on every user who clicks "Yes". Before shipping, add a signed manifest (ed25519/minisign) with per-asset SHA-256, verified in-app against a pinned public key.

### HIGH

**H1. No code signing or notarization on any OS.**

[`build.yml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/build.yml) and [`release.yml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/release.yml) contain no `codesign`, `notarytool` or `signtool` step. The original README sent macOS users to "special instructions" to get around Gatekeeper, and Windows users will see SmartScreen warnings. The macOS bundle's `CFBundleIdentifier` ends up as the bare executable name: Nuitka falls back to the output filename when `--macos-signed-app-name` is unset (`nuitka/freezer/MacOSApp.py:68-82`). `CFBundleShortVersionString` defaults to `1.0`. A fork that wants trust needs an Apple Developer ID plus notarization, and a Windows Authenticode certificate (or Azure Trusted Signing).

**H2. Edge builds can never compare versions, so the updater always offers to "update" them to the latest stable.**

- [`app/utils/app_info.py:101`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/app_info.py#L101) does `f"+{commit[:7]}"` on an lxml objectify element. That yields a list, so the version string becomes `v1.2.3-edge4+[]`. I reproduced this with the same lxml.
- `-edge4` is not valid PEP 440 either way. `version.parse` raises, and `_parse_current_version` returns `0.0.0` ([`update_utils.py:796-798`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L796-L798)).
- Result: every Edge user is offered the latest stable release, which is effectively a downgrade, on every startup.

**H3. The embedded QtWebEngine browser is most of the app's size, for one convenience feature.**

- What it does: [`app/utils/steam/steambrowser/browser.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/steam/steambrowser/browser.py) (1,233 lines) plus [`setup_web_channel_script.js`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/setup_web_channel_script.js) (761 lines) and [`setup_steam_recovery_script.js`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/setup_steam_recovery_script.js) (22 lines). It shows the Steam Workshop in a persistent Chromium profile, injects JS badges and "add" buttons, uses a QWebChannel bridge ([`js_bridge.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/steam/steambrowser/js_bridge.py)) to queue mods, scrapes collection HTML with regex (`:622-645`), and feeds the queue to SteamCMD or Steamworks subscribe.
- Size: `QtWebEngineCore` alone is 225 MB thinned to arm64 (81 MB gzipped, measured). Add `qtwebengine_locales` (44 MB, copied whole by [`distribute.py:47`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/distribute.py#L47)), ICU data (10 MB) and the `QtWebEngineProcess` helper. QtCore+QtGui+QtWidgets thinned is about 20 MB. Most of the 166-323 MB release artifacts is therefore Chromium.
- Startup: the module is imported eagerly ([`main_content_panel.py:77`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L77)), costing about 29 ms of `QtWebEngineCore` import. The real cost is memory (a multi-process Chromium) when the browser is opened, plus a large CVE surface that has to follow Qt releases.
- Other issues: the user agent is spoofed as Chrome 131 and hardcoded ([`browser.py:57-60`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/steam/steambrowser/browser.py#L57-L60)). The JS bridge is registered into `MainWorld` (`:325`, `:332`), so any page reached through the URL bar can call `add_mod_from_js` (low impact).
- Alternatives:
  - (a) Remove it. Open the Workshop in the system browser, and add mods by pasted URL/ID (already exists: `_show_add_mods_by_id_dialog`, `:401`) or by `steam://` links.
  - (b) A native Qt "Workshop search" list backed by `IPublishedFileService/QueryFiles` and `GetDetails`, which the WebAPI wrapper already partly calls.
  - (c) If it has to stay, make it an optional lazily-imported component and ship a "lite" build without WebEngine. That likely cuts artifacts by 60-70% (estimate from the sizes above; not built).

**H4. There is no separable UI-agnostic core today; domain code depends on Qt Widgets.**

- 57 of 118 non-view/non-window modules import PySide6 directly, and 44 import `QtWidgets` or `app.views`/`app.windows`.
- The root edge is [`app/models/settings.py:13,32`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L13): the settings model imports `QApplication` and dialogs (`BinaryChoiceDialog` at `:494`, `InformationBox` at `:511`).
- Through `metadata_structure → utils.files → models.settings → views.dialogue`, even [`app/models/mod_list.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/mod_list.py) pulls in `PySide6.QtWidgets`, though its docstring says "No Qt dependency" (verified in a fresh interpreter). The same holds for `metadata_structure`, `metadata_factory`, `sort/mod_sorting`, `services/mod_list_parser` and `dependency_resolver`.
- [`app/sort/topo_sort.py:8`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/topo_sort.py#L8) imports `show_warning` from `app.views.dialogue`, so the sorting algorithm opens a dialog itself.
- The god objects:
  - [`views/mods_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py): 5,861 lines, 149 defs. `ModListWidget.eventFilter` alone is **1,048 lines** (`:1720`) and builds the whole context menu plus git/steamcmd/acf actions inline. `recalculate_internal_errors_warnings` is 310 lines (`:3504`).
  - [`views/main_content_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py): `MainContent`, a 3,359-line, 104-method `QObject` **singleton** inside `views/`. It runs SteamCMD, Steamworks, todds, git, Rentry/PrivateBin, zip import and game launch.
  - [`controllers/main_content_controller.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/main_content_controller.py): 2,134 lines, 11% covered, with a 418-line `_perform_git_upload_operations` (`:1573`).
- 34 functions are over 150 lines and 110 are over 80.
- Upside: [`app/utils/xml.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/xml.py), [`acf_utils.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/acf_utils.py) and [`app_info.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/app_info.py) import cleanly without Qt. The sort/metadata logic is the best-tested code (80-96%). Cutting about three import edges (settings→dialogue, files→settings, topo_sort→dialogue) would free most of the domain layer.

### MEDIUM

**M1. Dead, unmaintained, redundant or undeclared runtime dependencies.** Usage was found by grepping imports under `app/`. PyPI dates are the latest upload.

| Dependency | Used for (evidence) | Health | Verdict |
| --- | --- | --- | --- |
| aiohttp 3.14.5 | **Nothing in `app/`.** Only [`translation_helper.py:87`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/translation_helper.py#L87), a dev script | Active | **Move to dev group** (adds 7 transitive packages to the runtime lock) |
| steam 1.4.4 | Five `WebAPI.call` uses in [`utils/steam/webapi/wrapper.py:17,388-397`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/steam/webapi/wrapper.py#L17) | **Last release 2022-12** | **Replace** with plain `requests` against `api.steampowered.com`. It silently provides `Cryptodome` (pycryptodomex, 9 MB, imported directly by [`utils/privatebin.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/privatebin.py)) and `vdf` ([`utils/generic.py:19`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/generic.py#L19)), both undeclared, so declare them first |
| steamfiles (git dependency **and** submodule) | ACF load/dump only ([`utils/steam/steamfiles/wrapper.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/steam/steamfiles/wrapper.py), 23 lines) | Submodule last commit 2020-10. Pulls `protobuf` and `protobuf3-to-dict` (2017, legacy setuptools build) | **Drop**. ACF is VDF, so use `vdf`. Removes the submodule, the externally hosted `steamfiles` git source, protobuf, and the setuptools workarounds in [`pyproject.toml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/pyproject.toml) |
| toposort 1.10 + networkx 3.7 | [`sort/topo_sort.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/topo_sort.py): `toposort()` plus `nx.simple_cycles` **only on the error path** | toposort 2023; networkx active but 8 MB and **284 ms at startup** | **Replace** with stdlib `graphlib.TopologicalSorter` (`prepare()` raises `CycleError` with a cycle) and a short DFS for listing all cycles |
| zstandard 0.25 | One `zstd.open` for compressed saves ([`utils/xml.py:290`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/xml.py#L290)) | OK | **Replace** with stdlib `compression.zstd` (Python 3.14, PEP 784) |
| beautifulsoup4 + lxml | bs4 is only a fallback XML parser ([`utils/xml.py:111`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/xml.py#L111), `"lxml-xml"`). lxml is also used for `version.xml` ([`app_info.py:93`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/app_info.py#L93)) | Active; lxml is 21 MB | **Drop bs4**. Use `lxml.etree.XMLParser(recover=True)` directly. Keep lxml, which tolerates broken mod XML |
| rapidfuzz | One `fuzz.partial_ratio` in notes search ([`views/mods_panel.py:5196`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L5196)) | Active, 4.3 MB | Low priority. `difflib` or substring matching would do |
| PyGithub 2.10 | [`utils/github/provider.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/github/provider.py) (git-mod update checks) and the DB-upload PR flow in [`main_content_controller.py:10`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/main_content_controller.py#L10) | Active. Pulls pyjwt[crypto] (cryptography 24 MB) and pynacl. 231 ms import | Keep short-term with a lazy import. Its use is small enough to replace with REST calls via `requests` later |
| SQLAlchemy 2.1 | Aux metadata DB and GitHub-mod cache (13 files, [`utils/aux_db_utils.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/aux_db_utils.py), [`utils/github/models.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/github/models.py)) | Active. 298 ms import, 10 MB | Keep but lazy-import. A stdlib `sqlite3` rewrite is optional and not urgent |
| pygit2 | Git-mod clone/pull, wrapped in [`utils/pygit2_loader.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/pygit2_loader.py) | Active | Keep. It removes the need for a system git |
| requests | The single HTTP client ([`utils/http.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/http.py), with retry and backoff) | Active | Keep. There is no second runtime HTTP client once aiohttp moves to dev |
| msgspec, natsort, platformdirs, psutil, watchdog, loguru, click, charset-normalizer, packaging, certifi, base58 | Settings/metadata structs, sort, dirs, process info, file watching, logging, `cli/build_db`, file search, updater version compare, pygit2 CA, PrivateBin | Mostly active. natsort is from 2023 and loguru from 2024-12 but both are stable | Keep. click could become argparse since it backs only 238 lines of CLI |
| PySide6 6.12 (meta-package) | GUI | Active | Keep, but depend on `pyside6-essentials` (+ `pyside6-addons` only if needed) instead of the meta-package. The meta-package also installs `pyside6-webengine` and `pyside6-pdf`, about 1.2 GB in the venv (Nuitka bundles only imported modules) |
| `submodules/SteamworksPy` + prebuilt `libs/*` (10 binaries, about 2.6 MB) | Steamworks subscribe/unsubscribe/launch/app-dependencies via `multiprocessing` ([`utils/steam/steamworks/wrapper.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/steam/steamworks/wrapper.py)) | Fork of a dead upstream. Last commit 2024-11 (a `<cstdint>` include). Binaries are committed by hand (last updated 2026-08-24); CI never rebuilds them | Keep (no alternative for in-client subscribe). Mirror it under the fork's org and build the `.so`/`.dylib`/`.dll` in CI from the pinned SDK so their provenance can be checked |

**M2. Startup cost comes from eager imports of heavy libraries, not from Qt.** See the key numbers table: about 0.9 s of the 1.86 s import time is networkx, sqlalchemy, PyGithub and steam. Lazy imports plus dropping networkx and steam would roughly halve cold Python import time. This is an estimate from `-X importtime`, not an end-to-end launch measurement.

**M3. The updater buffers the whole artifact in RAM twice.** `bytearray()` grows to the full size and is then copied by `bytes(content)` ([`update_utils.py:1409-1465`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L1409-L1465)), then kept in `self._update_content`. For a 323 MB macOS tarball that is about 650 MB peak. Stream to a temp file instead.

**M4. The update temp directory is predictable, and later steps may run elevated.** `Path(gettempdir()) / f"RimDeck_update_{%Y%m%d_%H%M%S}"` is created with `mkdir(exist_ok=True)` ([`update_utils.py:1530-1535`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L1530-L1535)). On Linux `/tmp` is shared, so another local user can pre-create it. That staging directory is then fed to `sudo update.sh`, which runs `rsync` as root. This is a local privilege-escalation pattern; use `tempfile.mkdtemp()`. Shell strings are built by hand for `cmd`, PowerShell and osascript (`:301-335`). The paths are quoted, but `osascript ... do script "<script_cmd>"` embeds `shlex`-quoted paths inside an AppleScript string literal, which is fragile for paths containing `"`.

**M5. The build supply chain has unpinned or unchecked inputs.**

- [`distribute.py:361-420`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/distribute.py#L361-L420) downloads the **latest** `joseasoler/todds` release with no checksum and bundles it as an executable.
- [`packaging/linux/build-appimage.sh:107`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/packaging/linux/build-appimage.sh#L107) pins `appimagetool` 1.9.1 but does not verify a hash.
- The Steamworks binaries are committed by hand (M1).
- The Actions themselves are mostly pinned by tag rather than SHA; only `ncipollo/release-action` and the nix-cache actions use SHAs.

**M6. Dead code, duplication, and a parallel model that is not wired in.**

- `MainContent.__do_get_github_release_info` ([`main_content_panel.py:856`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L856)) is name-mangled and never called.
- [`app/models/mod_list.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/mod_list.py) (`ModList`, `ModListDiff`, `to_mods_config`/`from_mods_config`) is a UI-agnostic domain model referenced **only by tests**. It looks like a refactor that was started and never adopted.
- 59 `jscpd:ignore-start` blocks exist to satisfy the 0%-duplication gate ([`.jscpd.json`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.jscpd.json) threshold 0).
- A heuristic scan found 89 defined-but-unreferenced functions or classes. Some are Qt slots and false positives. Examples: `instance_controller.get_local_mods_path/get_workshop_mods_path/get_config_folder_path`, `file_search_controller.update_results/get_search_text`, `main_content_panel._do_configure_steam_db_file_path/_do_set_database_expiry/_do_edit_steam_webapi_key`, `UpdateNetworkError`, `PlatformPatterns`.
- [`update_utils.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py) still carries the comment "TEMP_DIR_DARWIN and TEMP_DIR_DEFAULT are unused and can be removed" (`:78`).
- The git functionality is split three ways: [`utils/git_utils.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/git_utils.py) (1,865 lines), [`utils/git_worker.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/git_worker.py) (582) and `utils/github/` (925, PyGithub + SQLAlchemy). The main thing duplicated is error and notification plumbing.

**M7. Secrets are stored in plaintext.** `github_token` ([`settings.py:232`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py#L232)) and `steam_apikey` (`:154`) are written to `settings.json` in the data folder. The OS keychain would be better (a `keyring` dependency or the Qt keychain).

**M8. The threading model is mixed and re-entrant.** It combines 40 `QThread` references, 6 `QRunnable`/`QThreadPool`, 4 raw `threading.Thread`, 3 `ThreadPoolExecutor`, `multiprocessing` for Steamworks (needed, because Steamworks binds per process), 17 `QProcess`, and **9 nested `QEventLoop().exec()`** used to "wait without blocking" ([`main_content_panel.py:905-909`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py#L905-L909) and `update_utils.py:1222/1257`, among others). Nested event loops allow re-entrancy, so other slots can run mid-operation. They are a common source of hard-to-reproduce bugs.

**M9. EventBus is a 90-signal global QObject singleton** ([`utils/event_bus.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/event_bus.py), 164 lines, which also imports `QPushButton`/`QWidget`). It is referenced 211 times across 29 files, with 84 emits and 88 connects. Combined with nine singletons (`AppInfo`, `EventBus`, `MetadataController`, `MetadataDbController`, `MainContent`, `SteamcmdInterface`, `GUIInfo`, `SystemInfo`, `db_builder`), control flow is implicit and hard to test. That explains the low coverage on the orchestration files. [`AGENTS.md`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/AGENTS.md) documents the GC-of-subscriber trap that broke instance actions for v1.6–v1.16.

### LOW

- **L1.** Dependabot runs **daily** for `uv`, submodules and actions ([`.github/dependabot.yml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/dependabot.yml)). The last five commits on `main` are all bumps. For a small fork, switch to weekly grouped updates.
- **L2.** The pre-commit hook (`.githooks/pre-commit`) refuses to run unless `pwsh` is installed, even on macOS/Linux. On Unix, `just check` runs `nix flake check`, which also builds the packaged app. That is slow for a commit hook.
- **L3.** `just typecheck` and `just pyright` scan `.` and pick up untracked scratch files under `dev/`. Scope them to `app tests`.
- **L4.** [`pyproject.toml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/pyproject.toml) has `version = "0.0.0"`, with the real version injected through `version.xml` at build time. Builds made outside CI have no version (feeds into C1/H2).
- **L5.** Two Linux tarballs (Ubuntu 22.04 and 24.04) both match the updater's "Ubuntu/Linux" asset patterns. Which one is picked depends on match order (`update_utils.py:1047+`).

---

## Packaging and distribution summary (read only, not built)

- **Pipeline:** [`auto_build.yml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/auto_build.yml) (push to main → Edge prerelease) and [`release.yml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/release.yml) (manual Stable/Edge) both call [`build.yml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/build.yml). That workflow runs on a matrix of macos-15-intel, macos-latest (arm64), ubuntu-22.04, ubuntu-24.04 and windows-latest, with these steps:
  1. `semantic-version` produces `version.xml`.
  2. `uv sync --no-dev --group build` installs dependencies.
  3. `pyside6-lrelease` compiles translations.
  4. `distribute.py --skip-build` fetches todds and copies the Steamworks libs.
  5. `Nuitka/Nuitka-Action@v1.5` builds with Nuitka 4.3.1 (`--mode=app` on macOS, `standalone` elsewhere, `static-libpython: auto`). Further options come from [`rimdeck.nuitka-package.config.yml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/rimdeck.nuitka-package.config.yml) and the `# nuitka-project:` header in [`app/__main__.py:1-26`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/__main__.py#L1-L26).
  6. macOS: [`packaging/optimize_macos_bundle.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/packaging/optimize_macos_bundle.py) thins fat binaries.
  7. Windows: WiX 7 builds the MSI.
  8. Ubuntu 22.04: `build-appimage.sh` builds the AppImage.
  9. `attest-build-provenance` signs the artifacts.
  10. [`test_builds.yml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/test_builds.yml) launches each binary for 10 s as a smoke test.
- **Release assets:** [`release.yml`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/.github/workflows/release.yml) packs Windows `.zip`, `.msi`, `.AppImage`, and `.tar.gz` for macOS/Linux.
- **Signing:** none (H1). Attestations are produced but never consumed (C2).
- **Size:** 166-323 MB per artifact, dominated by QtWebEngine (H3).
- **Startup:** Nuitka standalone (not onefile), so there is no unpack cost. The cost is Python-level imports (M2) plus Qt initialization.
- **Assessment:** the Nuitka + Actions pipeline works, is reasonably fast with Nuitka caching, and is worth keeping. What is missing is identity parameterization, signing, and update-manifest generation.

## Auto-update flow (per OS)

1. Trigger: at startup (default on) or from the menu. Skipped if `RIMDECK_DISABLE_UPDATER` is set or the app runs from source (`__compiled__` absent, [`update_utils.py:695-711`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py#L695-L711)).
2. `GET https://api.github.com/repos/Argotoss/rimdeck/releases/latest`, sending the user's GitHub token if one is configured (`:863-867`). Drafts and prereleases are excluded by GitHub. The tag is parsed with `packaging.version`.
3. Pick an asset by filename pattern (OS/arch/extension). Windows prefers `.msi` when the install is in a protected path, otherwise `.zip`. Linux uses `.AppImage` when running as an AppImage, otherwise `.tar.gz`. macOS uses `.tar.gz`.
4. Download into memory (M3), with only a size check (C2). Extract: zip with a zip-slip guard ([`zip_extractor.py:86-90`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/zip_extractor.py#L86-L90)), tar with `filter="data"` (`:388`), which is good.
5. Optionally zip-backup the install, then hand off to the platform installer:
   - Windows: [`update.bat`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/update.bat) copied to the data folder (`taskkill /im <app>.exe` + robocopy), or `msiexec /i /passive` with UAC.
   - macOS: `osascript` → Terminal → [`update.sh`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/update.sh), which runs `killall RimDeck`, `rm -rf` on the old bundle, `rsync` and `open`; prefixed with `sudo` when the bundle is not writable.
   - Linux: [`update.sh`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/update.sh) through bash or a detected terminal, with `sudo` if needed; for AppImages it renames to `.bak` and swaps the file.
6. Then `sys.exit(0)`.

Trust model: HTTPS to `api.github.com` and the asset CDN, plus whoever can publish releases on `Argotoss/rimdeck`. There is nothing else.

---

## Rebrand status

The rename was done in the initial commit of this repository: app name, data folder and lock file, environment variables, user-facing strings in every translation, help and issue links, export images, the Linux desktop and AppStream IDs, the MSI UpgradeCode and component GUIDs, Nuitka and workflow names, the Nix package and the removed Nix cache. Upstream documentation, community files and issue templates were removed.

Still open, tracked in [findings.md](findings.md):

- One-time copy of the original app's data into the new data folder on first launch (F03).
- The inherited logo and icons (F68).
- Sources still hosted by the original project's GitHub organization: the default Steam Workshop and community rules databases, the steamfiles git dependency and the SteamworksPy submodule (F69).
- The GPL-3.0 notice: keep the license, ship source with every binary release, and state modifications. The license file carries the single attribution line.

---

## Dev tooling verdict

The core tooling is fast and helps a small team:

- 1,660 tests run in about 32 s.
- mypy and pyright take about 9 s each and are clean, with strict-ish mypy (`disallow_untyped_defs`, `disallow_any_generics`).
- ruff runs in about 1 s.
- `uv` keeps installs reproducible.
- The two custom guards ([`check_deferred_imports.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/check_deferred_imports.py), [`check_eventbus_subscribers.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/check_eventbus_subscribers.py)) encode real past bugs.

The burden for a small fork comes from these:

- A Nix flake (830 lines of `nix/`) that `just check` runs on Unix, including a full package build.
- 12 workflows.
- Daily dependabot.
- A 0%-duplication jscpd gate, which has led to 59 ignore blocks.
- markdownlint, shfmt and checkov.
- A pre-commit hook that requires `pwsh`.
- Mandatory i18n regeneration across 11 locales.

Recommendation:

- Keep uv, ruff, mypy, pyright, pytest, just and the two guards.
- Make Nix opt-in.
- Relax jscpd to a small non-zero threshold.
- Move dependabot to weekly grouped updates.
- Drop the `pwsh` requirement from the hook.

---

## Verdict per area

| Area | Verdict | Why / what |
| --- | --- | --- |
| Runtime libraries | **Refactor (trim)** | Move aiohttp to dev. Replace steam (declare pycryptodomex and vdf first), steamfiles, toposort+networkx, zstandard and bs4 with stdlib or already-present libraries. Lazy-import sqlalchemy and PyGithub. Depend on `pyside6-essentials`. Low risk, quick, and cuts lock size and startup |
| SteamworksPy + `libs/` | **Keep, re-host** | No real alternative for in-client subscribe. Mirror it to the fork's org and build the binaries in CI from a pinned SDK |
| Embedded Steam browser (QtWebEngine) | **Rebuild / replace** | Over half the artifact for a convenience UI. Replace with system browser + paste/`steam://` + a native WebAPI search list, or at least make it an optional lazily-loaded module and ship a lite build |
| Packaging (Nuitka, Actions, MSI, AppImage) | **Keep, refactor** | The pipeline works and builds in 5-29 min. Centralize branding, add signing and notarization, pin and hash todds and appimagetool, set the macOS bundle id and version |
| Auto-updater ([`update_utils.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py) 2,737 lines + [`update.sh`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/update.sh)/[`update.bat`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/update.bat)) | **Rebuild** | Hardcoded upstream, no integrity check, elevated `shell=True` scripts, predictable temp directory, whole-file RAM buffering, broken Edge version handling, 28% coverage. Replace with a signed manifest (ed25519) verified in-app, streamed downloads, and a small install step per OS. Alternatively evaluate Sparkle/WinSparkle, AppImageUpdate or Velopack. Must land before the first fork release |
| Architecture: domain core (sort, metadata, mod list, ACF/XML) | **Refactor (extract)** | Well tested (80-96%) and full of domain knowledge, so rewriting it would be wasteful. Cut the model→view import edges ([`models/settings.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py), [`utils/files.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/files.py), [`sort/topo_sort.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/topo_sort.py)), adopt the unused [`models/mod_list.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/mod_list.py), and enforce "no PySide6 in core" with a guard like the existing deferred-imports check |
| Architecture: views/controllers ([`mods_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py), [`main_content_panel.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/main_content_panel.py), [`main_content_controller.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/main_content_controller.py)) | **Rebuild incrementally (strangler)** | God objects: a 1,048-line `eventFilter`, a 3.4k-line view-singleton that does business logic, 11-40% coverage, nested event loops, a 90-signal global bus. For a redesign, build new screens on top of the extracted core and retire these piece by piece; don't refactor in place |
| Dev tooling and CI | **Keep core, trim extras** | See Dev tooling verdict above |
