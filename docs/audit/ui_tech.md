# RimDeck UI technology evaluation

Date: 2026-10-23. Baseline: `main` @ `18e52bcb` (v1.17.3 released 2026-10-21), PySide6 6.12.0, Python 3.14, Nuitka.

Goal: pick the UI technology for a redesign that reaches "Linear / Raycast / new Steam client" polish, and say whether a rewrite (web or Rust) is justified.

---

## 1. What the codebase tells us before any framework comparison

These facts weigh more than any framework benchmark, so they come first.

| Fact | Evidence | Why it matters |
| --- | --- | --- |
| The mod lists put a full `QWidget` in every row. | `ModListWidget(QListWidget)` in [`app/views/mods_panel.py:1161`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/views/mods_panel.py#L1161) calls `setItemWidget(item, ModListItemInner(...))` per row (`:2975-2992`). It lazy-loads widgets to cope, and `setUniformItemSizes(True)` is commented out (`:1246`). | This is the main cause of the list performance and look-and-feel problems, and Qt's own docs warn against it. Qt's model/view stack (`QAbstractListModel` + `QListView` + `QStyledItemDelegate`) paints 3000 rows without creating 3000 widgets. **This is a design fault, not a toolkit limit.** |
| Buttons resize when pressed. | [`themes/RimPy/style.qss:265`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/themes/RimPy/style.qss#L265): `QPushButton:pressed { border-style: inset; }` while the normal state has `border-width: 0px`, plus 38 inline `setStyleSheet(...)` calls in `app/`. | This is a QSS bug. Five themes × ~1,200 lines of hand-written QSS with no shared tokens produce the inconsistent spacing. Again a design-system problem, not a toolkit one. |
| The UI is most of the code. | 57 files / ~43k of ~64k Python lines import `QtWidgets`. `app/views` is 19.6k lines and `app/windows` 6.7k. | Any non-Qt option means rewriting about two-thirds of the codebase's surface area. |
| Qt reaches into the "core". | `EventBus(QObject)` ([`app/utils/event_bus.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/event_bus.py)), [`mod_sorting.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/mod_sorting.py) (`QObject`/`Signal`), [`metadata_mediator.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/metadata/metadata_mediator.py) (`QThread`/`QThreadPool`/`QMutex`), [`settings.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/models/settings.py) (`QApplication`), and [`topo_sort.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/sort/topo_sort.py) (`QCoreApplication.translate`). 28 of 49 `app/utils` modules import PySide6. | A Python sidecar for Tauri or Electron is not "keep the core as is". The core first has to be untangled from Qt threading, signals and translation. That is a large refactor before the first web pixel. |
| The download is already huge. | v1.17.3 assets: Windows MSI 166 MB, Windows zip 202 MB, AppImage 230 MB, Linux tar 257 MB, macOS 312–323 MB (latest release of the original project). | Most of this is QtWebEngine (Chromium), which serves only the Workshop browser. QtWebEngineCore alone is ~130–200 MB on Windows/Linux and 460–645 MB on macOS ([Flathub](https://discourse.flathub.org/t/qt-webengine-takes-200mb-of-installed-size/10292), [Qt forum](https://forum.qt.io/topic/162586/size-of-qtwebengine), [Staffroom #12](https://github.com/ColePoppleton/Staffroom/issues/12)). |
| Startup is dominated by Python imports. | `docs/audit/evidence/importtime.txt`: `app.controllers.app_controller` takes ~1.86 s cumulative import time (`metadata_controller` alone ~0.94 s). | A new UI toolkit will not fix startup. Lazy imports and less eager work will. A web shell starting in 300 ms would still wait on a Python sidecar to import the same modules. |
| Self-update is custom. | [`app/utils/update_utils.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/update_utils.py) downloads a GitHub release archive and runs [`update.sh`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/update.sh)/[`update.bat`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/update.bat). | Any option needs a signed, atomic updater. Tauri and Electron ship one; Qt does not, so it stays custom or uses Sparkle/WinSparkle. |
| i18n is Qt-native. | 11 locales (`locales/*.ts` + `.qm`), ~270 `translate(` call sites. | Free in A and B (QML uses the same `.ts`/`.qm` via `qsTr`). Options C, D and E need a converted catalog and a new extraction workflow. |

**Consequence:** the visible problems (nested boxes, uneven spacing, resizing buttons, plain tabs, list jank) all have known fixes inside Qt Widgets. The toolkit sets the *ceiling*, mostly for animation, blur/translucency and fancy transitions. RimDeck is nowhere near that ceiling today.

---

## 2. Is the embedded Steam Workshop browser needed?

What it does today ([`app/utils/steam/steambrowser/browser.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/utils/steam/steambrowser/browser.py)): browse steamcommunity.com inside QtWebEngine, inject JS ([`setup_web_channel_script.js`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/setup_web_channel_script.js), [`setup_steam_recovery_script.js`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/setup_steam_recovery_script.js)) to show "add to list" badges, scrape collection HTML, and queue items for SteamCMD download or Steam subscribe.

Options:

1. **Drop it (recommended).** Open Workshop pages in the system browser or the Steam client (`steam://url/CommunityFilePage/<id>`). Add a first-class "Add by URL / ID / collection link" box, plus an optional clipboard watcher that recognizes Workshop URLs. Item and collection details come from the key-less `ISteamRemoteStorage/GetPublishedFileDetails` / `GetCollectionDetails` web endpoints. Full Workshop **search** in-app through `IPublishedFileService/QueryFiles` needs a Web API key ([Steamworks docs](https://partner.steamgames.com/doc/webapi/IPublishedFileService)). So in-app search would need a user-supplied key, a proxy, or `ISteamUGC` queries through the running Steam client (SteamworksPy already loads `steam_api`). This saves roughly 130–600 MB per platform and removes Chromium security patching from the release process.
2. **Keep it, but out of process and on demand.** Use the OS webview (WebView2 / WKWebView / WebKitGTK) in a helper process, e.g. `pywebview`. It costs a few MB instead of 150+ MB, but WebKitGTK quality on Linux is a known weak spot (see §3C).
3. **Keep QtWebEngine as an optional add-on download.** It is possible but adds packaging complexity for little gain.

This decision is independent of the UI toolkit and is the **single largest download-size win available.** It also removes one of the main arguments for a web stack ("we already need a browser").

---

## 3. Options

Scores are relative (★ = poor, ★★★★★ = best) and reflect RimDeck's situation, not the framework in general.

### A. Keep Qt Widgets and rebuild the UI layer on a real design system

**What it means:** one token source (colors, radii, spacing scale, type scale, elevation), a `QProxyStyle` that paints buttons, tabs, inputs, scrollbars and focus rings from those tokens, and a single small generated QSS for the leftovers (light and dark generated from the same tokens; the five hand-written themes become token presets). Lists move to `QAbstractListModel` + `QListView` + custom `QStyledItemDelegate` (icons, badges, two-line rows, hover and selection states painted in one `paint()`). A small set of in-house components covers what QSS cannot do well: a segmented/pill tab bar, toolbar icon buttons, a toast, an empty state, a command palette (`Ctrl+K`), and a split detail panel.

- **Visual ceiling and effort:** high for a desktop tool and enough for a Linear-like flat, dense, keyboard-first look. Polished custom-painted Qt Widgets apps exist (Telegram Desktop is the canonical example). Animations are possible (`QPropertyAnimation`, `QVariantAnimation` in delegates) but hand-rolled, and blur/vibrancy and fluid layout transitions are hard. Effort is moderate and front-loaded into the style and delegate layer, then each screen is mostly re-layout. Third-party kits such as QFluentWidgets are GPLv3-for-non-commercial plus a paid commercial license ([about](https://qfluentwidgets.github.io/pages/about/)). This project is GPL-3.0, so it is usable, but it imposes a Windows-11 look and a dependency; borrowing ideas is better than adopting it.
- **3000 rows with DnD:** ★★★★★. `QListView` with uniform item sizes and a delegate handles 10k+ rows easily. Internal-move DnD, multi-select (extended selection) and filtering (`QSortFilterProxyModel`) are built in. Qt 6.12's `QRangeModel` adds built-in sorting and drag-and-drop action controls ([Qt 6.12](https://www.qt.io/blog/qt-6.12-released)).
- **Size and startup:** same runtime as today. Dropping QtWebEngine (§2) should bring downloads from 166–323 MB to an estimated 50–90 MB compressed. This is an estimate to verify with a Nuitka build; [PythonGUIs](https://www.pythonguis.com/faq/packaged-installer-file-sizes/) gives typical PySide6 bundle sizes. Startup is unchanged by the toolkit; fix it with import hygiene (§1).
- **Auto-update:** stays custom. Harden the existing updater (signature check with minisign/ed25519, atomic swap) or adopt Sparkle (macOS) / WinSparkle (Windows) and AppImageUpdate (Linux).
- **SteamworksPy / pygit2 / watchdog / SQLite:** zero integration cost.
- **i18n:** zero migration. New strings go through the existing `just i18n-update` flow.
- **Accessibility:** best of all options. Widgets expose an accessibility tree automatically; custom delegates need `QAccessible` roles and text for rows ([Qt accessibility](https://doc.qt.io/qt-6/accessible.html)).
- **Team fit:** ★★★★★ (Python + Qt is what the codebase is).
- **Migration path:** fully incremental, screen by screen, with each release shippable.
- **Risk:** low. The main risk is ending with a "better but still Qt-looking" result if the design system is half-applied. Mitigate by making tokens and `QProxyStyle` the first deliverable and banning new inline `setStyleSheet`.
- **Future option:** Qt 6.12 adds the **StyleKit** module (Labs) for styling Widgets and Qt Quick from one QML-based styling API ([Qt 6.12 blog](https://www.qt.io/blog/qt-6.12-released), [Phoronix](https://www.phoronix.com/news/Qt-6.12-LTS-Released)). It is experimental today, but it is the official path to the token-based styling this plan builds by hand. Keep the token source format-neutral (JSON) so it can feed StyleKit later.

### B. Qt Quick / QML with PySide6 (keep the Python core)

- **Visual ceiling and effort:** ★★★★☆. GPU scene graph, smooth animations, states and transitions, and shaders give a ceiling close to web. Qt 6.10 added `FlexboxLayout` (tech preview), a `SearchField` control, and QML `SortFilterProxyModel`/`TreeModel` ([Qt 6.10](https://www.qt.io/blog/qt-6.10-released), [FlexboxLayout docs](https://doc.qt.io/qt-6/qml-qtquick-layouts-flexboxlayout.html)). Qt 6.12 LTS adds built-in QML hot reload and a `QtQuick.Controls.Native` style. PySide6 6.12 adds the `QtQmlFeatures` tech preview with reactive property decorators (`@computed`, `@watch`) that cut QObject boilerplate ([PySide 6.12](https://www.qt.io/blog/qt-for-python-release-6.12-is-here)). But Qt Quick Controls' desktop-grade widgets (tables, tree views, complex forms, log viewers with 100k lines) are still less complete than Widgets, so you build more yourself.
- **3000 rows with DnD:** ★★★★☆. `ListView` only instantiates visible delegates. Reorder DnD is a known but hand-built pattern (`DelegateModel` + `Drag`/`DropArea`, commit one `move()` on drop) ([Qt tutorial](https://doc.qt.io/qt-6/qtquick-tutorials-dynamicview-dynamicview3-example.html), [QRangeModelAdapter example](https://github.com/keithel/dragreorder-listview-qrangemodeladapter-example)). Multi-select drag between two lists is custom work. Python-side models must be `QAbstractListModel` subclasses; per-row Python `data()` calls are fine at this scale.
- **Size and startup:** adds QtQuick, QtQml, QuickControls2 and shader modules, roughly 20–40 MB more than Widgets-only (estimate). QML compile cost at startup can be cached with `qmlcachegen`. Nuitka has a PySide6 QML plugin, but bundling QML plugins can drag in QtWebEngine accidentally ([pyside6-deploy docs](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html)).
- **Auto-update:** same as A.
- **Native libraries:** zero cost.
- **i18n:** `qsTr()` uses the same `.ts`/`.qm` pipeline; `lupdate` scans `.qml`. Low cost.
- **Accessibility:** weaker by default. Quick controls need explicit `Accessible.*` properties, and real migrations report missing states and keyboard activation ([Qt accessibility](https://doc.qt.io/qt-6/accessible.html), [audio-forge PR #109](https://github.com/FueledByRedBull/audio-forge/pull/109)).
- **Team fit:** ★★★☆☆. QML is a third language (declarative JS-ish) that the team does not know; debugging the Python↔QML boundary (property notifications, ownership, GC) is a recurring cost. Qt Bridges, Qt's simplified Python-to-QML layer announced in 2025, is only in early code access/beta ([Qt Bridges](https://www.qt.io/qt-bridges), [forum](https://forum.qt.io/topic/164093/welcome-to-qt-bridges)).
- **Migration path:** possible incrementally via `QQuickWidget` (embed a QML view inside the Widgets window), but a mixed app has two styling systems and focus/DnD edge cases at the seams. In practice it becomes a rewrite of the main window.
- **Risk:** medium. The core still has to move off QWidget-era patterns, and the visual gain over a well-done A is mostly motion and transitions.

### C. Tauri 2 (Rust shell + web frontend), Python core as sidecar, or core ported to Rust

- **Visual ceiling and effort:** ★★★★★. Highest ceiling and the best component ecosystem (Radix/shadcn, Tailwind, Framer Motion). This is the stack Linear-class UIs are built with. Effort is a full UI rewrite (~26k lines of views and windows).
- **3000 rows with DnD:** ★★★★☆ in Chromium/WebView2/WKWebView. TanStack Virtual handles 100k rows ([TanStack Virtual](https://tanstack.com/virtual/latest)), but dnd-kit's sortable cannot target rows that are not mounted. Virtualized reorder with multi-select needs custom collision logic ([react-virtual-dnd-table](https://github.com/Utumno1984/react-virtual-dnd-table)). It is solvable, but it is the same custom work as in QML.
- **Linux is the problem.** Tauri uses the system webview: WebKitGTK on Linux, whose performance and stability a Tauri maintainer called "unusable" in 2024, with ongoing user reports into 2025–2026 of low scroll FPS and regressions after WebKitGTK updates ([discussion #8524](https://github.com/orgs/tauri-apps/discussions/8524), [wry #1315](https://github.com/tauri-apps/wry/issues/1315), [tauri #7021](https://github.com/tauri-apps/tauri/issues/7021)). RimWorld has a large Linux and Steam Deck audience, and a smooth-scrolling 3000-row DnD list is exactly the workload that suffers. The Chromium (CEF) runtime that fixes this exists only in **Tauri 3.0 alpha**, adds "hundreds of megabytes", and one project already backed out of it (187–455 MB Linux packages) ([Tauri CEF docs](https://v3.tauri.app/develop/cef/), [athas PR #767](https://github.com/athasdev/athas/pull/767)).
- **Size and startup:** the shell is a few MB, but the Python sidecar (Nuitka/PyInstaller onedir with pygit2, SQLAlchemy, lxml/xml deps, SteamworksPy) is plausibly 40–80 MB. Net size is similar to option A without WebEngine. The window appears fast, but data waits for the sidecar's Python imports (§1).
- **Auto-update:** ★★★★★. Built-in, mandatory ed25519 signatures, static `latest.json` on GitHub Releases, and `tauri-action` generates everything ([updater plugin](https://v2.tauri.app/plugin/updater/)). The sidecar must be signed and updated with the app.
- **Sidecar cost:** documented via `externalBin` and `shell().sidecar()` with stdin/stdout ([sidecar docs](https://v2.tauri.app/develop/sidecar/)). Lifecycle is on you: PyInstaller onefile orphans children, and health checks and restart are not built in (plugins-workspace #3062). Nuitka sidecar examples are rare ([tauri-python-sidecar](https://github.com/matshoppenbrouwers/tauri-python-sidecar), [PyInstaller example](https://github.com/dieharders/example-tauri-v2-python-server-sidecar)). [PyTauri](https://github.com/pytauri/pytauri) (PyO3, embeds CPython in-process, v0.8) is an interesting alternative but third-party and pre-1.0. Before any of this, the core needs untangling from `QObject`/`QThread`/`EventBus` and an RPC API (JSON-RPC or similar) designed for every operation the UI performs.
- **Port the core to Rust instead:** `steamworks-rs` 0.13 covers UGC/Workshop ([repo](https://github.com/Noxime/steamworks-rs), [UGC docs](https://docs.rs/steamworks/latest/steamworks/struct.UGC.html)), `git2`/`gitoxide` replace pygit2, `notify` replaces watchdog, `rusqlite`/`sqlx` replace SQLAlchemy, and `petgraph` covers topological sort. Everything is technically available, but it means rewriting ~64k lines including years of RimWorld edge cases (About.xml quirks, load-order rules, community rules DB). That is a multi-quarter project for a small team with "some Rust".
- **i18n:** convert `.ts` to PO/JSON (`ts2po` → `po2json` in translate-toolkit ([docs](http://docs.translatehouse.org/projects/translate-toolkit/en/latest/commands/ts2po.html))) and move translators to a new workflow (e.g. Weblate or Crowdin with i18next/FormatJS). Context strings carry over, but placeholders (`%s`/`{0}`) must be rewritten to ICU.
- **Accessibility:** good; web ARIA semantics map well to platform accessibility APIs, if the team does the work.
- **Team fit:** ★★★★☆ for TypeScript, ★★☆☆☆ for owning a Rust shell, a Python sidecar and the IPC between them.
- **Migration path:** not incremental inside the shipping app. It is a parallel new app that reaches parity before replacing the old one.
- **Risk:** high (Linux webview quality, sidecar ops, parity gap, translator churn).

### D. Electron + web frontend + Python sidecar

- Same frontend story as C, but with **bundled Chromium**, so rendering is identical on Windows, macOS and Linux. That removes C's biggest technical risk.
- **Size and startup:** ~85–150 MB installers and ~1–1.5 s cold start for Electron itself ([Digital Applied 2026](https://www.digitalapplied.com/blog/desktop-apps-web-stack-tauri-electron-deno-wails-2026); comparisons are mostly vendor-written, so treat them as estimates). Adding the Python sidecar gives roughly 130–220 MB, which is **about what the app ships today**, but far worse than option A without WebEngine. Idle RAM is ~150–300 MB.
- **Auto-update:** mature (`electron-updater` with GitHub Releases, code signing).
- **Steam and git:** sidecar unchanged; Node also has `steamworks.js` if ever needed.
- **i18n, accessibility, team fit, migration, risk:** as in C, minus the WebKitGTK risk and plus the size and RAM cost. If the team ever goes web, Electron is the safer web choice for this app's Linux audience, which is an uncomfortable conclusion given the "small download" goal.

### E. Native Rust GUI with a full Rust rewrite

- **Slint 1.17/1.18:** declarative `.slint` markup, good-looking Fluent/Cupertino/Material styles, and live preview. License is GPLv3, royalty-free (attribution) or commercial; this project's GPL-3.0 is compatible ([LICENSE](https://github.com/slint-ui/slint/blob/master/LICENSE.md), [FAQ](https://github.com/slint-ui/slint/blob/master/FAQ.md)). Drag and drop (`DragArea`/`DropArea`) only left experimental in 1.17 (June 2026), cross-app drops are still landing, and there is **no built-in ListView reorder**; you compose it per delegate ([1.17 release](https://slint.dev/blog/slint-1.17-released), [DnD guide](https://docs.slint.dev/latest/docs/slint/guide/development/drag-and-drop/), [discussion #6717](https://github.com/slint-ui/slint/discussions/6717)). Slint has AccessKit. It is young for a dense desktop tool with tables and log viewers.
- **egui:** fast and immediate-mode, with AccessKit accessibility on by default ([egui a11y](https://github.com/emilk/egui/blob/main/docs/accessibility.md)), but its look is "developer tool". Reaching Linear-like polish fights the paradigm, and text layout and i18n (CJK, RTL) are weaker.
- **iced 0.14** (Dec 2025): Elm architecture, still no screen-reader support in mainline ([HN thread](https://news.ycombinator.com/item?id=46185323)).
- **Dioxus 0.7:** desktop is wry/webview (same WebKitGTK issue as Tauri); the native Blitz renderer is experimental ([0.7 release](https://dioxuslabs.com/blog/release-070/)).
- **Size and startup:** best of all (10–30 MB, sub-200 ms). Auto-update is DIY (e.g. `self_update`, Velopack).
- **Native libraries:** `steamworks-rs`, `git2`, and so on, as in C.
- **i18n:** Slint has gettext-based `@tr()`, so convert `.ts` to `.po` (translate-toolkit). Others vary.
- **Team fit:** ★★☆☆☆. **Migration:** big-bang rewrite. **Risk:** very high, with the most effort for a visual result no better than A or C.

### F. Others, briefly

- **Flet 1.0** (Sept 2026; Python + Flutter rendering) ([blog](https://flet.dev/blog/flet-1-0/)): pure Python and attractive Material/Cupertino out of the box, but the UI runs in a separate Flutter process over MessagePack, desktop list DnD/multi-select at 3000 rows is unproven, the Qt `.ts` workflow is lost, and native-lib and Nuitka packaging are replaced by Flet's own build. It is not a fit for a dense power-user tool today.
- **Avalonia 12** (Apr 2026; 12.1.4 Oct 2026; .NET): mature, good Linux story (native Wayland, AT-SPI2 accessibility, open-source WebView) ([Avalonia 12](https://avaloniaui.net/blog/avalonia-12)), but a full C# rewrite with no team skill fit.
- **PyTauri** ([repo](https://github.com/pytauri/pytauri)): Tauri with CPython in-process, which removes the sidecar. It is worth watching as a future C variant, but it is pre-1.0, third-party, and inherits WebKitGTK.
- **Qt Bridges** ([qt.io](https://www.qt.io/qt-bridges)): official simplified Python↔QML layer, in beta/early access. It could lower option B's cost in 2027 and is a reason to keep B open as a later step.

---

## 4. Summary matrix

| | A. Qt Widgets + design system | B. QML + PySide6 | C. Tauri + Py sidecar | D. Electron + Py sidecar | E. Rust native rewrite |
| --- | --- | --- | --- | --- | --- |
| Visual ceiling | ★★★★ | ★★★★½ | ★★★★★ (★★★ on Linux WebKitGTK) | ★★★★★ | ★★★–★★★★ |
| Effort to look modern | Medium | High | Very high | Very high | Extreme |
| 3000-row DnD lists | ★★★★★ built in | ★★★★ custom DnD | ★★★★ custom virtual DnD; Linux scroll risk | ★★★★ custom virtual DnD | ★★★ custom (Slint) |
| Download (est.) | ~50–90 MB without WebEngine | ~70–120 MB | ~45–90 MB | ~130–220 MB | ~10–30 MB |
| Startup | Python-import bound (fixable) | Same + QML load | Fast shell; data waits on sidecar | ~1–1.5 s + sidecar | Fastest |
| Auto-update | Custom (harden) | Custom | Built-in, signed | Mature | DIY |
| SteamworksPy / pygit2 | Free | Free | Free (sidecar) or port | Free (sidecar) | Port everything |
| Core decoupling needed | No | Partial | Yes (Qt out of core + RPC) | Yes | n/a (rewrite) |
| i18n migration | None | None (`qsTr`) | `.ts` → JSON/ICU | `.ts` → JSON/ICU | `.ts` → PO |
| Accessibility | Best by default | Manual | Good (ARIA) | Good (ARIA) | Varies (egui/Slint OK) |
| Team fit | High | Medium | Medium | Medium-high | Low |
| Incremental migration | Yes, per screen | Partly (`QQuickWidget`) | No (parallel app) | No (parallel app) | No |
| Risk | Low | Medium | High | Medium-high | Very high |

---

## 5. Recommendation

**Stay on PySide6 Qt Widgets (option A) and rebuild the UI layer on a token-based design system: model/view lists with custom delegates, a `QProxyStyle`, and one generated stylesheet. Drop the embedded QtWebEngine Workshop browser in the same program.** Do not rewrite in Tauri, Electron or Rust.

Why:

1. **The current ugliness and jank are self-inflicted, not toolkit limits.** One `QWidget` per list row, ~6k lines of untokenized QSS across five themes, and 38 inline `setStyleSheet` calls (including a `:pressed` rule that changes the border) are fixable inside Qt. A delegate-painted `QListView` is the fastest 3000-row DnD list of any option here, with multi-select and filtering built in.
2. **A rewrite buys ceiling RimDeck does not need, at a cost it cannot afford.** About two-thirds of the code is UI, and Qt threading, signals and translation run through the "core". C and D first need a Qt-free core and an RPC layer, then a full UI rewrite, translator migration, and (for Tauri) a gamble on WebKitGTK for the Linux and Steam Deck audience, all while the existing app is frozen. Option A ships improvements every release.
3. **The size and startup goals are met better by removing things than by changing toolkits.** Dropping QtWebEngine cuts most of today's 166–323 MB. Startup is bound by ~1.9 s of Python imports, which no UI framework fixes.

**Revisit triggers.** Re-evaluate B (QML via `QQuickWidget` or Qt Bridges) for showcase surfaces if, after phase 3, motion and transitions are still the gap, *and* Qt Bridges/StyleKit are stable. Re-evaluate a web front-end only if a Qt-free core and RPC API exist for other reasons (e.g. a CLI or headless mode) and Tauri's CEF runtime is stable.

---

## 6. Phased migration plan (incremental, every phase shippable)

**Phase 0: Foundations (2–3 weeks)**

- Design tokens in one JSON file (color roles for light and dark, a 4/8 px spacing scale, radii, type scale, elevation, motion durations) and a small Python module that turns tokens into a `QPalette` + generated QSS.
- `RimDeckStyle(QProxyStyle)` that paints push and tool buttons (fixed metrics across states, so nothing resizes), tabs (underline or pill), line edits, combo boxes, scrollbars (thin overlay), and focus rings from tokens.
- Existing themes become token presets. Add a lint guard (like [`check_deferred_imports.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/check_deferred_imports.py)) that fails on new inline `setStyleSheet`.
- A screenshot test harness (pytest-qt + `QWidget.grab()`) for key screens in light and dark, to catch regressions.

**Phase 1: Mod lists (3–5 weeks; highest user impact)**

- Replace `ModListWidget(QListWidget)` + `ModListItemInner` with `ModListModel(QAbstractListModel)` + `QListView` + `ModRowDelegate`. One painted row shows icon, name, author/version in a secondary line, and badges (source, warnings, errors, update available, color tag). Use uniform row heights, hover and selection states, and paint inline actions on hover.
- `QSortFilterProxyModel` for search and filter chips. Internal-move and cross-list DnD via `mimeData`/`dropMimeData`, multi-select with extended selection, keyboard reordering (`Alt+↑/↓`), and `QAccessible` text for rows.
- Keep the public signals the controllers use so the rest of the app does not change. Benchmark 3000 rows (scroll FPS, DnD latency, filter latency) in tests.

**Phase 2: App shell and layout (3–4 weeks)**

- Flatten the nested group boxes into a three-pane layout: sidebar or toolbar, inactive and active lists, and a collapsible detail panel. Use a consistent page header and toolbar component, a new tab bar, a status bar replaced by toasts and a task drawer, and a `Ctrl+K` command palette that exposes existing actions.
- Mod detail panel: large preview image with a rounded mask, metadata chips, and a description rendered through a BBCode→HTML converter into `QTextBrowser` (or `QTextDocument` markdown). Lazy image loading via `QThreadPool`.

**Phase 3: Secondary surfaces (4–6 weeks, parallelizable)**

- Settings becomes a sidebar-nav settings page with grouped form rows. Log viewers use `QPlainTextEdit` or a model-backed `QListView` with level coloring and filtering. Tables (`app/windows/*`) get one shared `DataTable` (model + header delegate + empty state). Dialogs share a common frame (title, body, button row, fixed metrics).
- Every new string goes through `translate()` and `just i18n-update` / `i18n-compile`.

**Phase 4: Steam Workshop without QtWebEngine (2–3 weeks, can run in parallel with phase 2)**

- "Add from Workshop" panel: paste URL, ID or collection link, a clipboard watcher (opt-in), details via the key-less `GetPublishedFileDetails`/`GetCollectionDetails`, then queue to SteamCMD or subscribe via SteamworksPy. "Open in Steam / browser" buttons cover browsing.
- Optional: in-app search via `ISteamUGC` query through SteamworksPy when Steam is running, or with a user-supplied Web API key.
- Remove `PySide6-WebEngine`/`QtWebEngine` from deps and from the Nuitka config ([`app/__main__.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/__main__.py), [`distribute.py`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/distribute.py), which need owner sign-off per [`AGENTS.md`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/AGENTS.md)). Measure the new artifact sizes.

**Phase 5: Startup, update and polish (2–3 weeks)**

- Startup: profile with `-X importtime` (baseline in `docs/audit/evidence/importtime.txt`), defer `metadata_controller` work, show the main window with skeleton rows before metadata finishes loading, and target first paint under 1 s.
- Updater: sign release artifacts (ed25519/minisign), verify before applying, use atomic swap and rollback, and consider Sparkle/WinSparkle on macOS and Windows.
- Motion: subtle `QPropertyAnimation` for panel collapse, toasts and row insert/remove. Run an accessibility pass (keyboard-only walkthrough, NVDA/VoiceOver/Orca smoke test).

**Phase 6 (optional, 2027+): Re-evaluate**

- If StyleKit leaves Labs, port the token→QSS generator to StyleKit. If Qt Bridges for Python is stable and motion-heavy surfaces remain the gap, prototype one `QQuickWidget` surface (e.g. the mod detail panel) behind a flag before committing to anything broader.

Rough total: 4–6 months of part-time work for a small team, with visible improvements from phase 1 onward. A Tauri or Electron rewrite would plausibly take 9–18 months before reaching parity, and nothing would ship to users in the meantime.
