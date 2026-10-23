# Interface audit

Method: the app was launched in dev mode against a synthetic install (600 local mods, 307 active, [`docs/audit/tools/make_fake_game.py`](tools/make_fake_game.py)) and driven by a script ([`docs/audit/tools/shoot.py`](tools/shoot.py) + `steps_*.py`) that grabs every window after each step. Screens are in `docs/audit/screens/` (full set in the gitignored `dev/shots*`). Each screen was scored against the criteria below.

## Criteria

1. Layout: one grid, consistent alignment, no nested frames without purpose.
2. Spacing: a small fixed spacing scale (e.g. 4/8/12/16/24).
3. Typography: a few sizes and weights forming a hierarchy.
4. Color: semantic tokens (surface, text, muted, accent, success, warning, danger) with WCAG AA contrast.
5. Controls: one button system (primary, secondary, ghost, danger), stable dimensions across states.
6. Feedback: inline status, non-blocking notifications, empty/loading states; modals only for decisions.
7. Information architecture: frequent actions prominent, rare or dangerous actions tucked away; user language over internal jargon.
8. Responsiveness: usable at 1280x760, no clipped text.

## Measured design-system debt

- 5 themes x ~1,200 lines of QSS each, 6,073 lines total; every theme is the same layout recolored.
- Default theme alone uses 32 distinct hex colors, 5 font sizes, 14 distinct padding/margin values (0-25px).
- 38 inline `setStyleSheet` calls and 32 hardcoded colors in Python bypass the theme.
- 17 group boxes and 10 frames create the "boxes in boxes" look.
- 355 call sites open a modal popup (warnings, info, yes/no). The app talks to the user almost exclusively through blocking dialogs.
- Mod list rows are full widgets inserted per row (`setItemWidget`) instead of a painted delegate: heavy, hard to style, slow at scale.

## Findings, ranked

### Critical

1. **First launch is a wall of popups.** Three blocking dialogs appear in sequence before the user sees anything usable: "set up SteamCMD?", a "Mods with Missing Properties" table, and "enable Steam Client Integration?". The missing-properties table flags every local mod as lacking a Steam Workshop ID, which is meaningless for local mods. Screens: `01_main_*`, `03_mod_selected_60_BinaryChoiceDialog.png`.
2. **Sort looks frozen.** Clicking Sort with missing dependencies opens a parentless, non-modal "Dependency Manager" window that can land behind the main window, while the sort waits in a nested event loop. In the scripted run nothing visibly happened for over 4 minutes. Clicking Sort again stacks a second wait inside the first. Details in `logic.md`.
3. **A missing theme folder crashes the app instead of falling back.** The fallback warning's format string contains `{self.default_theme}`, which raises `KeyError` ([`app/controllers/theme_controller.py:174`](https://github.com/Argotoss/rimdeck/blob/audit-baseline/app/controllers/theme_controller.py#L174)). Any user whose theme files are missing or whose working directory differs gets a crash on startup.

### High

4. **Mod lists carry too much noise and too little meaning.** Every row shows a folder icon and an "XML" icon that rarely differ; every mod shows a "NEW" badge on first launch (307 badges); problem mods are signaled by red text plus a yellow or red icon, but the reason only appears on hover. Inactive mods also show warnings that don't matter until they are activated.
5. **Selection is nearly invisible and sometimes unreadable.** The selected row in the default theme is a slightly lighter gray behind red text; in SunSet and Wood the selection is orange behind red text. Screens: `05_mod_selected_err`, `themes_sheet.png`.
6. **Primary actions have no hierarchy.** Refresh, Clear, Restore, Sort, Save, Run are six identical gray buttons in a row; "Clear" (destructive) sits next to "Sort" and "Save". Two full-width buttons above them ("Check 'Use This Instead' Database", "Check Dependencies") use internal jargon.
7. **Mod detail panel layout is broken.** Label/value columns don't align (long labels like "Supported Version:" and "Filesystem Modified:" push the value column); the preview image floats with no frame logic; the notes field and the description are separate bordered boxes with their own scrollbars; the description repeats inside a fixed-height scroller; "Mod Version: Unknown", "Tags: None", "Workshop Times: Not available" waste space. Large empty area above the "Welcome to RimDeck!" box when nothing is selected.
8. **Search controls are confusing.** Each list has "Search by..." field, a "Name" dropdown that picks the field to search, a magnifier button, "Tags" button, an eye button, and on the inactive side a sort-field dropdown and "Desc" toggle. Seven controls per list, unlabeled icons, tiny targets.
9. **Rule editor is unusable without prior knowledge.** Eight empty boxes labeled with raw XML tag names (`About.xml (loadAfter)`, `Community Rules (incompatibilitiesWith)`), bottom-right buttons with clipped text ("de About.xml rul", "k Community Ru"), and two unexplained single-letter buttons "C" and "U". Screen: `26_rule_editor_208_RuleEditor.png`.
10. **Settings dialog has 9 tabs that overflow** behind scroll arrows; Advanced tab mixes centered and left-aligned headings, clips text off the right edge ("Enable editin"), places spin boxes inconsistently, shows a Windows path hint ("C:\Program Files (x86)\...") on macOS, and exposes developer concepts ("watchdog file monitor daemon", "Auxiliary Metadata DB deletion time limit in seconds (Delete instantly 0, Never Delete -1)"). "Use dependency rules for sorting" is off by default.

### Medium

11. **Tabs jump.** Unselected tabs get `margin-top: 2px`, so the selected tab is taller and the bar shifts on every switch (`themes/*/style.qss`, `QTabBar::tab:!selected`). Pressed buttons switch to `border-style: inset`; with themes that have a border width this changes the drawn size. The tab bar itself is centered, top-of-window, browser-style, and holds unrelated tools (log readers, file search, troubleshooting) at the same level as the main mod manager.
12. **Secondary tabs reuse dialogs inappropriately.** ACF Log Reader shows a "Do nothing and exit" button inside a tab; Player Log uses neon green/yellow/red label text, raw enum names ("Mod_issue"), and a grid of "<" ">" buttons; File Search has an unlabeled "▼" button and a "Stop" rendered as plain text next to a green "Search". None of them has an empty state.
13. **Troubleshooting puts destructive actions in plain view.** "Clear All Mods" (deletes every mod) and "Apply Recovery" sit as prominent red buttons in a normal tab, with warnings in red body text; four different button styles on one screen.
14. **No responsive behavior.** At 1280x760 mod names truncate in the active list, the info panel squeezes, nothing reflows. At 2940px everything stretches; huge outer padding and a stray vertical divider in the middle of the main panel.
15. **Five themes, zero design.** Themes only swap colors; layout, spacing and hierarchy problems are identical in all of them. No light theme. "Themes off" falls back to stock Fusion, which looks better aligned than the themed versions.

### Low

16. Status line "RimWorld version 1.6.4633 rev1261" is the only status bar content; no indication of instance, mod counts, or background tasks.
17. Inconsistent capitalization ("PackageID", "Package ID", "PackageId", "Published File Id", "Publish Field ID") across screens.
18. No keyboard-first affordances visible (no command palette, shortcuts not shown on buttons).

## Verdict

Rebuild the interface layer. Keep the toolkit decision separate (see `ui_tech.md`); nothing here is fixable by recoloring, and the problems come from structure (nested boxes, per-row widgets, popups as the main feedback channel, flat information architecture), not from Qt itself.
