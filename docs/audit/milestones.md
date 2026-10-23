# Milestones

Work through these in order; each milestone ships on its own. Tick an item by changing `- [ ]` to `- [x]` in the commit that fixes it. Item IDs link to the full finding with code references.

| Milestone | Items |
| --- | --- |
| [M1. Fork identity and safe updates](#m1-fork-identity-and-safe-updates) | 11 |
| [M2. Data safety and blocking bugs](#m2-data-safety-and-blocking-bugs) | 8 |
| [M3. Correct sorting](#m3-correct-sorting) | 11 |
| [M4. Qt-free core and speed](#m4-qt-free-core-and-speed) | 13 |
| [M5. Design system](#m5-design-system) | 7 |
| [M6. Main screen rebuild](#m6-main-screen-rebuild) | 9 |
| [M7. Secondary screens](#m7-secondary-screens) | 5 |
| [M8. Distribution polish](#m8-distribution-polish) | 5 |

## M1. Fork identity and safe updates

Before any fork build reaches a user. Installed builds can't be fixed afterwards, so the updater has to be right first.

Done when: a fork build only sees fork releases, refuses unsigned updates, installs and runs side by side with the original app, imports its data once, and Edge builds compare versions correctly.

- [x] [F01](findings.md#f01) Updater checks upstream releases
- [x] [F02](findings.md#f02) Windows installer shares upstream's product ID
- [x] [F03](findings.md#f03) Copy existing data from the original app on first launch
- [x] [F04](findings.md#f04) Updater verifies nothing but file size
- [x] [F05](findings.md#f05) Predictable update temp folder used with root rights on Linux
- [x] [F06](findings.md#f06) Updater holds the whole download in memory twice
- [x] [F07](findings.md#f07) Edge builds are always offered a downgrade
- [x] [F08](findings.md#f08) Builds without a version accept any update
- [x] [F09](findings.md#f09) Two Linux downloads match the updater's filter
- [x] [F13](findings.md#f13) Rebrand everything that pointed at the original project
- [x] [F14](findings.md#f14) Missing theme folder crashes the app

## M2. Data safety and blocking bugs

Stops the app from destroying data or appearing frozen.

Done when: no feature deletes or corrupts user data, Refresh time is flat across repeated runs, and Sort never waits on an invisible window.

- [x] [F15](findings.md#f15) Git repair deletes the repository history
- [x] [F16](findings.md#f16) Game mod list written in place
- [x] [F17](findings.md#f17) Sort drops duplicate and invalid entries
- [x] [F18](findings.md#f18) IDs containing "_steam" activate both copies
- [x] [F19](findings.md#f19) Moved or renamed mod folders leave stale entries
- [ ] [F31](findings.md#f31) Refresh leaks a panel and gets slower every time
- [ ] [F32](findings.md#f32) Sort waits on a hidden window
- [ ] [F39](findings.md#f39) Remove the missing-properties check

## M3. Correct sorting

Sorting is the product. It must be correct, repeatable and respectful of the user's list before anything is redesigned on top of it.

Done when: sorting an already sorted list changes nothing, results are identical across launches, dependencies order correctly by default, cycles produce a partial result with a readable report, and list icons and the sort dialog agree.

- [ ] [F20](findings.md#f20) Sort discards the user's order
- [ ] [F21](findings.md#f21) Sort is not deterministic
- [ ] [F22](findings.md#f22) Every sort moves dividers to the bottom
- [ ] [F23](findings.md#f23) Dependencies don't affect load order by default
- [ ] [F24](findings.md#f24) Any cycle aborts the whole sort
- [ ] [F25](findings.md#f25) Tier contradictions resolved silently
- [ ] [F26](findings.md#f26) Three dependency checks that disagree
- [ ] [F27](findings.md#f27) Rule data dropped or unused
- [ ] [F28](findings.md#f28) Remove alphabetical sort
- [ ] [F29](findings.md#f29) Lenient XML fallback accepts broken mods
- [ ] [F30](findings.md#f30) File-watcher reload parses differently from full refresh

## M4. Qt-free core and speed

The redesign needs a core it can call without dragging widgets along, and the freezes come from orchestration, not the algorithm.

Done when: sort, validation and mod list state live in a tested module with no PySide6 import, Sort at 2000 mods returns in under 300 ms, Refresh re-parses only changed mods, startup does no blocking network work, and unused libraries are gone.

- [ ] [F33](findings.md#f33) List rebuilds hit the database per mod on the UI thread
- [ ] [F34](findings.md#f34) No parse cache
- [ ] [F35](findings.md#f35) Blocking network checks at startup
- [ ] [F36](findings.md#f36) Heavy imports at startup
- [ ] [F59](findings.md#f59) Business logic inside screens
- [ ] [F60](findings.md#f60) Core cannot run without Qt widgets
- [ ] [F61](findings.md#f61) Unused Qt-free mod list model
- [ ] [F62](findings.md#f62) Nested event loops and mixed threading
- [ ] [F63](findings.md#f63) Same data stored in four places
- [ ] [F64](findings.md#f64) Global event bus and singletons
- [ ] [F65](findings.md#f65) Dead and duplicated code
- [ ] [F66](findings.md#f66) Library cleanup
- [ ] [F12](findings.md#f12) Tokens stored in plain text

## M5. Design system

One set of tokens and components replaces five hand-written themes, so every later screen is built from the same parts.

Done when: color, type, spacing and radius come from tokens; one generated stylesheet serves dark and light; buttons, inputs, list rows and panels have stable sizes across states; non-blocking notifications replace most popups.

- [ ] [F40](findings.md#f40) Popups as the main feedback channel
- [ ] [F41](findings.md#f41) No design system
- [ ] [F42](findings.md#f42) Boxes inside boxes
- [ ] [F50](findings.md#f50) Tabs and buttons shift on state change
- [ ] [F57](findings.md#f57) Inconsistent naming
- [ ] [F58](findings.md#f58) Missing basics
- [ ] [F68](findings.md#f68) Replace the inherited logo and icons

## M6. Main screen rebuild

The screen users spend all their time on.

Done when: painted list rows with clear status, readable selection, one primary action, a flat detail panel, a first-run setup flow, and a layout that works from 1280x760 up.

- [ ] [F38](findings.md#f38) Three blocking popups on first launch
- [ ] [F43](findings.md#f43) Mod list rows are full widgets
- [ ] [F44](findings.md#f44) Selection barely visible or unreadable
- [ ] [F45](findings.md#f45) Noisy rows
- [ ] [F46](findings.md#f46) No primary action
- [ ] [F47](findings.md#f47) Jargon on main buttons
- [ ] [F48](findings.md#f48) Mod detail panel layout
- [ ] [F49](findings.md#f49) Seven search controls per list
- [ ] [F56](findings.md#f56) No responsive layout

## M7. Secondary screens

Everything else, rebuilt from the same components.

Done when: settings grouped by task, a plain-language rule editor, tools moved out of the main tab bar with empty states, destructive actions behind confirmation.

- [ ] [F51](findings.md#f51) Tools at the same level as the mod manager
- [ ] [F52](findings.md#f52) Secondary screens unfinished
- [ ] [F53](findings.md#f53) Destructive troubleshooting actions in plain view
- [ ] [F54](findings.md#f54) Rule editor needs prior knowledge
- [ ] [F55](findings.md#f55) Settings dialog

## M8. Distribution polish

Trust and download size.

Done when: signed and notarized builds on all OSes, verified build inputs, Steamworks built in CI, and a download without the embedded Chromium.

- [ ] [F10](findings.md#f10) No code signing or notarization
- [ ] [F11](findings.md#f11) Unverified build inputs
- [ ] [F37](findings.md#f37) Downloads are 166 to 323 MB
- [ ] [F67](findings.md#f67) Steamworks binaries from an abandoned fork
- [ ] [F69](findings.md#f69) Externally hosted sources still owned by the original project
