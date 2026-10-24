# Breadcrumbs v0.4.1 action-point QA

Audit: 25 October 2026. Synthetic databases, an isolated Chromium profile, and
headless TUI tests were used. Live diagnostics only confirmed the running
bridge's timer status and capture precision; pairing tokens and real titles
were not printed. The user's running session was not stopped or modified.

| Action point | Validation |
| --- | --- |
| Branches stays at latest | 60-visit small-terminal fixture checks initial scroll end, live duration changes, new rows, older selection retention, End, and mouse/Enter details |
| Expanded activity view | Real click/Enter handlers, annotations persisted in SQLite, full logo/details, visual inspection at 140×42 and 80×24 |
| Terminal programs/logos | Explicit-title positive/negative cases, browser/editor exclusions, no verified agent ID from hints, unchanged scope classification, live context label/logo, bundled SVG/mask hashes |
| Session continuity | Focus → break → Focus, recovery by the same name, restart after completion, same session root/export name, explicit Ctrl+N creates a different session |
| Breaks in timeline | Short/long break spans, separate pause/resume spans, measured durations exclude pause/offline gaps, no app activity rows during breaks |
| Extension session pickup | Untracked block publishes running/paused timer without capture, port-conflict retry, already-running popup pickup, restart, stopped-sharing controls, stale/duplicate command checks |
| Accurate tab names | Real Chromium tab title/domain changes reach SQLite and extension preview; alternate browser dashes/profile suffixes; ambiguous profiles remain unverified |
| Privacy | Immediate title-preview redaction, stale/private/internal/unfocused/stop clear preview; origin/token, pause, exact-URL, and metadata-consent regression coverage |
| README/description | Updated motivation and description, contributor welcome, removed Tlock upgrade section, actual detail screenshot, all relative documentation links resolve |

The full Python suite, extension suite, real Chromium integration, compilation,
wheel/source build, metadata validation, and GitHub CI are checked for release.
Physical Linux foreground capture and every possible terminal/browser-profile
configuration remain outside this audit. Terminal-title hints are inferences;
they do not establish process or pane identity.
