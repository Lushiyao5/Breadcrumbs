# Changelog

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
