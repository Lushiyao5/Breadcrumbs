# Testing focus branches

Install the development dependencies and run the Python suite:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
node --test breadcrumbs/assets/browser-extension/tests/worker.test.mjs breadcrumbs/assets/browser-extension/tests/ui.test.mjs
```

CI runs Python tests on Windows and Ubuntu with Python 3.11 and 3.14. The
extension's dependency-free Node tests run in their own CI job. They cover
scope classification, consent, title redaction, freshness, pairing, inventory,
navigation hashes, pause, late reports, recovery, and helper cleanup.

A separate `macos-wheel` job builds and installs the wheel into a fresh virtual
environment on `macos-latest` with Python 3.11. Outside the checkout, it checks
all CLI aliases, help, bundled branding/extension resources, and a headless
timer start/pause/resume/quit/recovery lifecycle using temporary local data.
It does not test native foreground capture, desktop permissions, audio or a
real macOS browser; native macOS capture remains unsupported. The same check
can be run with `python -I /path/to/scripts/smoke_installed_package.py` from
outside the checkout using an environment where the wheel is installed.

The Windows suite also creates a new hidden fixture console, applies a real
terminal-agent marker through the authenticated bridge, and verifies title
restoration. It does not attach to the user's existing consoles.

## Real Chromium + TUI integration

The optional integration test uses Playwright only as a development tool.
It launches an isolated browser profile and temporary Breadcrumbs database. It does
not load the user's browser profile, history, cookies, or saved sessions.

From the repository on Windows:

```powershell
npm.cmd install --prefix .build-check --no-save --package-lock=false playwright @resvg/resvg-js
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.build-check\browsers'
.\.build-check\node_modules\.bin\playwright.cmd install chromium
node scripts/test_browser_e2e.cjs
```

This drives the actual Textual Start/scope/save flow and extension pairing UI.
The real extension sends events to the real loopback bridge. The actual TUI
poller writes the resulting intervals to its SQLite database. Fixture web
pages represent documentation and two YouTube video URLs; page responses are
intercepted, so no real account or video is opened.

Checks include selecting an exact URL, leaving and returning to it, different
query parameters, full TUI shutdown/recovery, and retaining the scope afterward.
The actual extension UI starts, pauses, resumes, and finishes blocks, including
cancelled and confirmed Finish actions. Sharing Stop/Disconnect and title
redaction are checked separately. A controlled desktop source supplies the other-app
departure; this test does not establish foreground-window behavior in the
user's normal desktop or terminal tabs.

## First real session

Install the checkout with `install.ps1`, then open `breadcrumbs`. Start a short focus
block, choose apps/agents and a documentation page, and save the scope. Switch
to another app or a different page, then return. B should show departures and
returns; the bottom status line should describe the active context. Pause
must stop capture. Quit and resume the saved name to check the trail remains
split across running spans.

Some terminal applications pin tab titles or suppress title updates. When a
selected agent cannot be verified, Breadcrumbs keeps host-window context rather
than guessing. Wayland/macOS native foreground capture remains unavailable;
see [support and limits](ACTIVITY.md).
