# Breadcrumbs 0.4.0 QA

Local release audit: 24 October 2026. Tests used temporary databases and an
isolated Chromium profile. No private browser profile was inspected or changed.

## Passed locally

| Area | Evidence |
| --- | --- |
| Python | 120 tests passed on Windows / Python 3.14 |
| Extension | 39 Node worker/UI tests passed |
| Installer | Fresh and repeat PowerShell install, runtime paths with spaces, canonical command, old launcher redirect |
| Installed runtime | Package import, bundled extension/brand assets, headless TUI, legacy SQLite recovery, JSON export |
| Browser integration | Real Chromium extension, authenticated loopback bridge, actual Textual UI and SQLite poller |
| Recovery | Exact URL selection, deviation/return, full TUI restart, saved scope retained |
| Remote controls | Start, Pause, Resume, confirmed/cancelled Finish, blocked conflicting dialogs, stopped sharing |
| Terminal helper | Real isolated hidden Windows console marker and exact title restoration |

## Adversarial checks

- Hostile browser origins are rejected even with a valid token. Extension CORS
  is bounded to the permitted origin.
- Concurrent duplicate Finish requests accept one command. Stale identities,
  changed sessions, and pre-restart control revisions cannot retarget a block.
- Old worker results cannot replace new status or browser capture results.
- Slow status bodies have a bounded timeout. Tab failures do not erase a
  healthy timer; stale status disables extrapolation and controls.
- Pause and span changes discard late activity. Restart gaps stay separate.
- Exact URL queries participate in page identity. Returning to the same URL
  rejoins scope; a different query does not.
- Unverified browser fallback drops plaintext titles. Private/internal tabs are
  excluded by the extension. IPv6 literals are normalized without accepting URLs
  in domain fields.
- Existing `tlock.db`, preferences, recovery names, and legacy environment
  overrides remain usable; data is not copied or moved during upgrade.

## Continuous checks

[GitHub Actions](https://github.com/SaroashDS/Breadcrumbs/actions) runs Windows
and Ubuntu with Python 3.11/3.14, extension worker/UI checks, a real browser
integration job, and installed-wheel command/resource checks. Release creation
also validates that the tag matches the package version and checks wheel/sdist
metadata. Release tags are pushed only after the main-branch checks succeed.

## Limits of this audit

The browser integration uses controlled foreground-window fixtures for app
departures. It proves extension/TUI/storage behavior, not every user's desktop
permissions or terminal title propagation. X11 capture is not exercised on a
physical Linux desktop. Wayland/macOS app capture is not implemented. Pinned tab
titles, multiplexers, and editor-integrated terminals may prevent agent
verification and are reported as Unknown.

## Follow-up deep QA: 25 October 2026

- Re-ran the Python suite (126 tests), all 39 extension worker/UI tests, and
  the real isolated Chromium/TUI integration covering URL scope, recovery,
  timer controls, and sharing/privacy gates.
- Reproduced and fixed two trail-inspector bugs with regression tests:
  switching to an empty block retained the previous visit's details/logo;
  older visits used the latest session scope for verification explanations.
  Visit explanations now use the scope snapshot saved with their running span.
- Added first-launch onboarding tests at 120 × 42 and 80 × 24 covering all
  pages, navigation, Skip, replay, persisted dismissal, recovery priority,
  unchanged paused blocks, and blocked underlying timer/settings shortcuts.
  Visually inspected screenshots of the welcome page and a scrollable small
  terminal feature page. The tour does not start a timer or enable capture.
- Windows/Python 3.11 CI exposed test-driver timing assumptions: a scope
  dialog was clicked before layout settled, and repeated tour clicks raced
  Textual's button active effect. The tests now wait for layout/button state;
  no timer or capture behavior was changed to accommodate the tests.
- Built wheel/source packages and passed Twine metadata checks. This follow-up
  did not repeat the installer audit or physical Linux desktop checks above.
