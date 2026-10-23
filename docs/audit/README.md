# Fork audit, October 2026

Audit of the fork at commit `18e52bcb` covering interface, logic and performance, libraries and packaging, and UI technology.

## Start here

1. [Milestones](milestones.md): the work plan. Eight milestones, 67 checklist items, done in order. Tick items off as they land.
2. [Findings](findings.md): every must-fix item with a description, permalinks to the exact code lines, evidence and screenshots.

## Detailed reports

- [Interface](ui.md): criteria, design-system measurements, every screen scored. Screenshots in [screens/](screens/).
- [Logic and performance](logic.md): sorting correctness experiments, metadata pipeline, validation, benchmarks at 600 and 2000 mods, how to separate the core from Qt.
- [Libraries, packaging, architecture, fork identity](platform.md): every dependency, the updater, packaging, architecture hotspots, and the full rebrand checklist.
- [UI technology options](ui_tech.md): Qt Widgets vs QML vs Tauri vs Electron vs native Rust, with sources.

Raw outputs of every experiment and benchmark are in [evidence/](evidence/). The scripts that produced them are in [tools/](tools/): a synthetic RimWorld install generator, the screenshot harness that drives the app and grabs every window, and the sorting, git and benchmark experiments. Run them from the repository root with `uv run python docs/audit/tools/<script>.py`; each script's docstring gives its arguments.

## How the audit was run

No RimWorld install was available, so a synthetic one was generated: 600 local mods with 307 active, and 2000 with 800 active for benchmarks, with realistic About.xml files, dependencies, load rules, preview images and some missing dependencies. The app ran in dev mode and was driven by a script. Steam Workshop, SteamCMD and real Steam client flows were not exercised.

Code references in the findings are permalinks to commit `18e52bcb`, so they keep pointing at the code that was audited after the files change.

## Verdict

Do not rewrite. Keep Python and Qt, keep the core logic, rebuild the interface and the orchestration layer around it.

- The sorting core is small, correct and fast: the topological sort takes about 2 ms for 807 active mods and had zero rule violations across 200 randomized cases. It is 80 to 96% covered by tests.
- About 80% of the 64k lines are in modules that import Qt, and much business logic lives inside view classes. That, not the toolkit, is why the app looks and behaves the way it does.
- A Rust, Tauri or Electron rewrite would freeze the product for months to reach parity on Steam, SteamCMD, git and instance handling, and would not fix the real slow paths: database writes per mod, re-parsing every About.xml on refresh, and a leaking panel.
- Qt Widgets with painted list rows, a token-based design system and fewer modals reaches a modern look and handles 3000+ rows with drag and drop. QML is the fallback if animation becomes the gap.

## Scorecard

| Area | Verdict |
| --- | --- |
| Visual design, layout, theming | Rebuild |
| Mod lists, one widget per row | Rebuild as painted model and delegate |
| Main screen, settings, rule editor, secondary tabs | Rebuild screen by screen |
| Popups as the main feedback channel, 355 call sites | Replace with inline status, notifications, first-run setup |
| Topological sort, About.xml parsing, rule model, external databases | Keep |
| Sort orchestration inside the view | Rebuild in a Qt-free core |
| Validation, three disagreeing implementations | Rebuild as one function |
| Metadata controller, aux database access | Refactor: cache parses, batch writes |
| Git mod handling | Rebuild |
| Alphabetical sort | Remove |
| Auto-updater | Rebuild with signed manifest before the first fork release |
| Embedded Workshop browser, about 225 MB of the download | Remove or make optional |
| Runtime dependencies | Trim |
| Packaging, CI, uv, ruff, mypy, pyright, pytest | Keep; centralize branding, add signing, make Nix optional |

## Open decisions

1. Diverge from upstream fully, or keep pulling upstream fixes into the core for a while. The milestones assume divergence after M4.
2. The new name, which M1 bakes into the app id and data folder.
3. Whether to keep the Workshop browser as an optional download or drop it.
