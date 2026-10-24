# Changelog

## 0.4.3 — Persistent sidebar and safer Windows updates · 2026-10-25

- Keep activity details visible beside the branch list. Arrow keys or a click
  immediately update the sidebar. Enter stays inline; Escape closes branches.
  Remove the Ctrl+Enter activity popup.
- Wait for running Windows launchers to close before pip changes packages. If
  they remain open, stop safely with an actionable status and leave the app intact.
- Back up the importable Breadcrumbs package and its metadata before updating,
  restoring them if pip fails after uninstalling. Avoid forcibly reinstalling
  every dependency on an application update.
- Update the README and real UI captures to match the persistent sidebar.
- Add regression coverage for a busy launcher and recovery after pip failure.


## 0.4.2 — Current browser build, cleaner branch details · 2026-10-25

- Fix the legacy unpacked-extension path left behind by the runtime rename:
  installers, future updater helpers, and installed app startup refresh known
  old extension folders. Pairing storage and Chrome preferences stay untouched.
  A Chrome/Edge extension reload is still required to activate new files.
- Add `breadcrumbs browser repair`, loaded extension version reporting,
  app/extension version display, and an old-build notice in Config.
- Preserve capture diagnostic messages in activity records so new Unknown
  visits can explain missing reports or an old extension instead of only
  saying that the window was captured.
- Remove artwork attribution strings from activity details. Attribution remains
  in the bundled notices and documentation.
- Open clicked/Enter-selected activity in a sidebar, with a smaller bounded
  branch card. Escape collapses details; Ctrl+Enter keeps the full-screen option.
  Compact details remain readable at 80×24.

## 0.4.1 — Keep the session, follow the trail · 2026-10-25

### Fixed

- Branches opens at the latest activity and keeps following new visits and
  duration updates without rebuilding the list. Inspecting an older visit
  preserves selection; End or Latest returns to the newest activity.
- A session keeps its name across work blocks, breaks, and app restarts.
  Ctrl+N or an explicitly edited name starts a different session. Block
  checkpoints, reflections, and elapsed times remain separate.
- The timer bridge starts for untracked running blocks too, so the paired
  extension can detect/control the current block without enabling capture.
  Port conflicts retry after another app instance closes.
- Browser title matching handles alternate dash glyphs and browser/profile
  suffixes, while ambiguous profiles still remain unverified.

### Added

- Click/Enter opens a full, scrollable activity detail screen with logo,
  timestamps, title/domain, capture precision, and annotation keys at all sizes.
- Short/long breaks appear in the session's branch timeline as timer spans.
  Paused/offline gaps are excluded; app/browser capture stays off during breaks.
- Explicit terminal-title program hints and bundled logos for Claude Code,
  Codex, Python, Node.js, Git, and Neovim. Hints affect presentation only;
  process-verified agent attribution and scope classification stay separate.
- The extension shows its actual last reported tab/domain. Disabled title
  sharing immediately redacts its preview; stopped, stale, private/internal,
  or unfocused context clears the preview. Awake heartbeats run every two seconds.
- Clearer browser verification notices, contributor guidance, updated project
  positioning, and practical launch-channel suggestions in `docs/SHARING.md`.

### Data and updating

- Existing blocks/history are retained. New blocks store a persistent session
  root and export its readable session name. Older unrelated blocks are not
  retroactively joined into a guessed session.
- Reload the unpacked extension after updating so Chrome/Edge loads v0.4.1.
  Re-pair if its saved address/token no longer matches Config → Browser connection.

## 0.4.0 — Breadcrumbs · 2026-10-25

### Renamed

- Tlock is now Breadcrumbs. The app, Python package, primary command, browser
  extension, installer, updater, and repository use the new name.
- `breadcrumbs` is the primary command. `tlock` remains a compatibility entry.
- Existing Tlock data, saved sessions, preferences, and environment overrides
  remain supported. No history is moved or deleted.

### Added

- A 12-page first-launch feature tour with Back/Next, keyboard navigation,
  scrolling, Skip, and replay using `?` from the ready or paused timer.
  Tour dismissal is remembered. Saved-session recovery takes priority;
  the tour never starts capture or a timer and blocks underlying app shortcuts.
- A hands-on onboarding guide and a README organized around practical tasks,
  with feature explanations, examples, settings, and a keyboard reference.
- Opt-in app/browser/terminal-agent scope before starting a block, with reuse
  and untracked options. Scope can also change within an existing session.
- Durable running spans and a Git-style activity trail with colored app nodes,
  departures, returns, source precision, and user annotations.
- A small animated, nameless trail beside intentions and a live context bar.
- Bundled Chrome/Edge extension with local pairing, exact URL selection,
  current-session pickup, theme matching, and Start/Pause/Resume/Finish controls.
- Browser connection setup in Config, separate from scope selection.
- Verified CLI agent markers for supported terminals; background processes do
  not count as foreground agent activity.
- Explicit activity export, including per-span scope snapshots.
- Local-date work totals and clear long-break round progress, alongside named
  recovery, intentions, task carryover, reflections, and configurable reading.

### Fixed

- Missing tab/agent verification reports Unknown rather than a false deviation.
- Scope survives recovery, including edits made while paused. Offline time is
  not joined into activity spans; late results from old spans are discarded.
- Long-break progress counts only full Focus completions and resets after a
  full long break. The UI states the remaining focus blocks directly.
- Extension status is independent of tab capture and stale browser requests.
  A stalled response body is bounded, older replies cannot replace newer state,
  and stale/double-clicked timer commands cannot target a changed session.
- Unverified browser fallback discards window titles, including potential
  private-browser titles. IPv6 domain literals are validated and normalized.
- Empty trail selections clear the previous visit's logo and details.
- Historical visit explanations use that running span's scope snapshot,
  rather than the session's most recently edited scope.

### Browser reliability and privacy

- Authenticated loopback bridge with bounded extension origins and payloads.
- Exact-page hashes retain query identity without transmitting raw URL paths
  or queries. Titles are separately configurable; private/internal tabs are
  excluded by the extension. Hashes are not anonymous identifiers.
- Stopping sharing does not disable timer status or controls. Reopening the
  popup discovers an already-running TUI session without waiting for tab reads.
- Timer commands bind to session identity/revision. Duplicate Finish commands,
  stale popups, pre-restart revisions, and changed-session replies cannot
  silently retarget a block. Busy dialogs temporarily disable remote controls.
- Slow response bodies time out, older results cannot replace newer status,
  and failed tab reads do not discard a healthy countdown.

### Validation

- Windows Python regression suite, dependency-free extension tests, and a
  real isolated Chromium/extension/TUI/SQLite integration scenario.
- Installer/reinstall, paths with spaces, legacy-data recovery, installed-wheel
  commands/resources, and package metadata checks.
- CI covers Windows/Ubuntu on Python 3.11/3.14, browser integration, extension
  tests, and package installation. See `docs/QA-v0.4.0.md` for audit scope.

### Upgrade notes

- Close Tlock before upgrading. Use `breadcrumbs` afterward; old command aliases
  remain available for transition.
- Load the extension from the new path printed by `breadcrumbs browser path`
  and pair it through Config. The old unpacked extension points to the old folder.
- Windows and Linux/X11 app capture are supported. Wayland/macOS native app
  capture and general editor-integrated terminal attribution remain limitations.

## 0.3.0 — Tlock

- Recoverable named sessions, scope-change decisions, rotating reading cards,
  sound previews, saved intentions, and session reflections.

## 0.2.0 — Tlock

- A cleaner timer workflow, simplified companion, task carryover, and local export.

## 0.1.0 — Tlock

- Initial public release.
