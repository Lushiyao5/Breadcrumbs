"""Create the explicitly requested, nonduplicate contributor starter tickets."""
import json
import subprocess
import tempfile
from pathlib import Path

REPO='SaroashDS/Breadcrumbs'
ISSUES=[
('Add an optional macOS foreground-app capture backend',['enhancement','help wanted'],'''The timer and paired browser work on macOS, but `breadcrumbs/activity.py` currently has no native macOS foreground-app adapter. macOS users should be able to opt into app-level scope without installing an unrelated tracking service.

Scope: implement one documented native foreground-app adapter behind the existing source interface. Keep permissions and any platform dependency optional. Return Unknown when access is unavailable; never infer focus from a background process.

Acceptance criteria:
- Capture the active application with monotonic, testable observation boundaries.
- Pause, breaks, quit and denied permissions stop or prevent capture.
- Browser page matching continues to rely on the extension and existing privacy gates.
- Document the required macOS permissions and supported OS versions.
- Add mocked unit tests and a reproducible manual macOS smoke check.

Start with `breadcrumbs/activity.py`, `docs/ACTIVITY.md` and `tests/test_activity.py`. This is a platform integration task, not a promise that macOS native capture already works.'''),
('Support one Wayland compositor with explicit capability detection',['enhancement','help wanted'],'''Native app capture currently supports Linux/X11. A generic Wayland implementation is not available, and compositor-specific support should be advertised only after it is tested.

Scope: choose one compositor, document its foreground-app API, and add an optional adapter using the existing activity-source interface. Keep unsupported compositors on the usable timer/browser path.

Acceptance criteria:
- Detect the tested compositor and required tools without prompting for unrelated privileges.
- Produce foreground-app observations only from actual compositor evidence.
- Show a clear unsupported/unavailable reason on other Wayland desktops.
- Preserve pause/break/exclusion behavior and browser identity rules.
- Add fixture-based tests and a manual test matrix for the chosen compositor.

Start with `breadcrumbs/activity.py`, `docs/ACTIVITY.md` and the support table in `docs/FOCUS_BRANCHES.md`. Please name the compositor you can test before beginning.'''),
('Add a local weekly review command for completed work and detours',['enhancement','help wanted'],'''History reviews individual blocks, but there is no weekly summary. Add a small read-only CLI workflow that helps users reflect without turning Breadcrumbs into a dashboard service.

Scope: `breadcrumbs review --week YYYY-MM-DD` (or a comparably small CLI) prints local-week work totals, completed/early-finished blocks and optional activity-label totals. Use the existing SQLite records; no network or AI dependency.

Acceptance criteria:
- Define week boundaries using the user's local timezone and document the choice.
- Exclude breaks from work totals and preserve recorded partial/early-finished work semantics.
- Keep activity omitted unless explicitly requested; do not guess missing context.
- Work with an empty database and sessions that span midnight.
- Add deterministic boundary tests, including a DST transition and repeated focus/break blocks in one named session.

Start with `breadcrumbs/db.py`, `breadcrumbs/__main__.py`, `tests/test_sessions.py` and `docs/USAGE.md`. Keep the first iteration textual and offline.'''),
('Design an opt-in VS Code workspace context integration',['enhancement','help wanted'],'''The foreground app name cannot distinguish two VS Code workspaces. The roadmap calls for editor/project context, but the current app must continue to label this limitation honestly.

Scope: propose and implement a minimal opt-in workspace report using the authenticated local bridge. Start with workspace identity, not source file contents or keystrokes. Explain the payload and lifecycle before adding a larger extension.

Acceptance criteria:
- Explicit user opt-in and per-workspace selection.
- No source contents, file paths or project names stored by default without a documented choice.
- Authenticate local reports, expire stale context and distinguish foreground evidence from a merely open workspace.
- Retain the timer and ordinary app-level scope without the integration installed.
- Document the protocol and include positive, stale-report, unauthorized and paused-capture tests.

Start with `breadcrumbs/bridge.py`, `breadcrumbs/activity.py`, `docs/ACTIVITY.md` and `docs/FOCUS_BRANCHES.md`. A short protocol proposal is a useful first contribution.'''),
('Add CSV export for session summaries',['enhancement','good first issue'],'''Breadcrumbs currently exports JSON. A CSV option would make personal reviews easier in a spreadsheet without adding a service or account.

Scope: add a `--format csv` option to the existing export command for session summary fields. Keep JSON as the default and defer nested activity CSV to a separate design.

Acceptance criteria:
- Include stable column names for session/block identity, timestamps, kind, elapsed work, completion status, intentions, reflection and rating.
- Use Python's CSV writer so commas, quotes, newlines and Unicode round-trip correctly.
- Preserve `--limit` and stdout/`--output` behavior.
- Omit activity/context unless a separately documented explicit option exists; never flatten it silently.
- Test an empty export, multiline intentions, non-ASCII reflection and early-finished blocks.

Start with `breadcrumbs/__main__.py`, `breadcrumbs/db.py`, `tests/test_db.py` and `docs/USAGE.md`. No new runtime dependency is needed.'''),
('Show actionable CLI errors when an export file cannot be written',['bug','good first issue'],'''`breadcrumbs export --output PATH` calls `Path.write_text()` directly. An unwritable location, missing parent directory or directory-valued path currently raises a Python traceback.

Scope: catch expected filesystem errors at the CLI boundary and print a short actionable message with a nonzero exit status. Preserve the original database and avoid printing session payloads on failure.

Acceptance criteria:
- Cover permission denied, nonexistent parent and output pointing at a directory.
- Keep success output accurate: distinguish session export from export that includes activity.
- Leave existing files and database records unchanged if writing fails.
- Add CLI regression tests using isolated data directories and mocked permission errors where necessary.
- Update the export documentation with one clear failure example.

Start with the `export` branch in `breadcrumbs/__main__.py` and `tests/test_cli.py` (or the existing CLI test module). This is a small, self-contained first fix.'''),
('Add macOS CI smoke coverage for the timer and installed wheel',['enhancement','good first issue'],'''CI currently tests Ubuntu and Windows on Python 3.11/3.14. The timer and paired browser are advertised on macOS even though native foreground capture is explicitly unsupported there.

Scope: add a macOS job for the portable timer/session tests and an installed-wheel CLI/resource smoke check. Do not claim or require native app capture.

Acceptance criteria:
- Build/install the wheel into an isolated environment on a macOS runner.
- Verify `breadcrumbs --version`, browser-extension resource availability and a headless timer/session lifecycle.
- Keep platform-dependent capture tests appropriately gated, with reasons rather than silent skips.
- Avoid GUI permission prompts, real browser profiles and network calls in unit tests.
- Document exactly which macOS behavior CI covers.

Start with `.github/workflows/ci.yml`, `tests/test_app.py`, `tests/test_sessions.py` and `docs/TESTING.md`. Prefer one focused job before expanding the matrix.'''),
('Add a privacy-safe doctor command for capture and browser diagnostics',['enhancement','help wanted'],'''Users need a quick way to explain why context is Unknown or why the extension cannot see a timer. Config exposes some connection information, but there is no shareable CLI diagnostic report.

Scope: add `breadcrumbs doctor` with version, Python/OS, supported capture backend, bridge reachability, extension version compatibility and actionable setup hints. Default output must be safe to paste into an issue.

Acceptance criteria:
- Never print pairing tokens, page titles, URLs, project paths, process command lines or stored session content.
- Distinguish unsupported platform, disabled capture, disconnected extension and stale extension build.
- Use bounded timeouts and do not start tracking or mutate session state.
- Offer JSON output with a documented stable schema if feasible.
- Add fixture-based tests for Windows, Linux/X11, Wayland and macOS plus connected/disconnected/outdated extension cases.

Start with `breadcrumbs/bridge.py`, `breadcrumbs/browser_install.py`, `breadcrumbs/__main__.py` and `docs/BROWSER_EXTENSION.md`. Keep every diagnostic a measured capability, not a guessed explanation.''')]

def gh(*args):return subprocess.check_output(['gh',*args],text=True,encoding='utf-8').strip()

def main():
    existing={row['title']:row['url'] for row in json.loads(gh('issue','list','--repo',REPO,'--state','all','--limit','100','--json','title,url'))}
    results=[]
    for title,labels,body in ISSUES:
        if title in existing:url=existing[title]
        else:
            with tempfile.TemporaryDirectory(prefix='breadcrumbs-issue-') as work:
                file=Path(work)/'body.md';file.write_text(body,encoding='utf-8')
                args=['issue','create','--repo',REPO,'--title',title,'--body-file',str(file)]
                for label in labels:args.extend(['--label',label])
                url=gh(*args)
        results.append(dict(title=title,url=url,labels=labels))
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
