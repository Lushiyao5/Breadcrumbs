# Breadcrumbs v0.4.2 QA

## Live diagnosis

Chrome's extension registration referenced the old Tlock runtime folder.
That directory held extension 0.2.0 with a ten-second heartbeat; the installed
Breadcrumbs directory held extension 0.4.1 with a two-second heartbeat.
The running TUI was v0.4.1 and published an active Focus timer. Read-only
activity summaries showed alternating verified tab and Unknown window records.
No browser history, cookies, pairing tokens, or real tab titles were printed.
The user's running session was not stopped or modified.

## Checks

- Old known extension folders are refreshed in place; a repeat is a no-op.
  Newer copies are not downgraded, missing installs are not created, unrelated
  extension names are untouched, and history bytes remain unchanged.
- The worker reports its loaded extension version. Popup mismatch messaging
  leaves a healthy timer controllable. The app exposes version diagnostics.
- Diagnostic messages survive activity persistence, including reason changes
  within otherwise identical Unknown contexts. Old observations are not relabeled.
- Artwork attribution is absent from rendered activity details; notices and
  artwork credits remain bundled.
- Click/Enter expands inline sidebar details, Escape collapses them, and
  Ctrl+Enter retains the full-view option. Older selection, latest-follow,
  labels, and scrolling remain covered.
- Real screenshots are inspected at 140×42 and 80×24; compact mode keeps
  the selected visit and useful details visible together.
- Full Python/Node suites, compilation, real isolated Chromium integration,
  package build/metadata, installed-wheel smoke, and GitHub CI gate publication.

Chrome/Edge still needs an unpacked-extension reload to activate replaced
files. No test asserts that every Unknown record is erroneous: private/internal
pages, missing reports, or ambiguous foreground evidence can remain unverified.
