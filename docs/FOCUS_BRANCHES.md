# Focus branches

Status: design notes and feasibility research, 24 October 2026.
Breadcrumbs v0.4.0 implements scope selection, durable running spans,
Windows/X11 desktop capture, an integrated browser bridge, a Git-style
trail, annotations, a live status line, and per-app colors.
See [setup and exact limits](ACTIVITY.md).
The bundled Chrome/Edge extension and explicit terminal-agent markers are now
implemented in this checkout. Editor/project identity is still future work.
The research below records earlier options; the current implementation owns
its collector and bridge rather than requiring a separate ActivityWatch service.

## The idea

At the start of a focus block, choose the tools and pages you intend to use:
VS Code in a project, a terminal with a coding agent, and a few documentation
tabs, for example. While the block runs, an optional activity source records
which context is foreground. Review the resulting trail alongside intentions
and the end-of-block reflection.

A running process is a candidate for the scope picker, not evidence that work
is happening in it. A new tab is not a detour until it becomes active. A
YouTube visit can be a tutorial, a break, or unrelated browsing; the domain
alone does not tell us which.

Use neutral labels:

- **Planned:** matches a rule selected for this block.
- **Supporting:** the user identifies a useful detour.
- **Deviation:** outside the selected scope; this does not imply wasted time.
- **Away:** an idle signal; kept separate from a judgment about productivity.
- **Unknown:** the collector could not determine the active context.

The trail records order and duration. It does not claim that switching from
an editor to a tab proves the tab was opened because of the code.

An optional **opened** marker could record a new tab or app without assigning
it attention time. Foreground visits, not process lifetime or background tab
creation, determine the duration shown in the trail.

## Proposed interaction

Keep the current timer and intentions layout. Put scope selection and branch
review in separate screens so this feature does not crowd the focus screen.

1. Opt into context tracking for a block.
2. Select a reusable scope: applications, windows/projects, and optionally
   domains or specific pages. Explain the precision available for each choice.
3. Start the timer. A small status indicates recording, paused, unavailable,
   or partially supported. Tracking follows the timer's running spans.
4. Open a separate trail screen to inspect transitions. It can render visits
   as branches or a chronological list, with repeat visits pointing back to
   the same context. Do not silently merge noncontiguous visits into one span.
5. During reflection, label useful detours, correct a classification, or delete
   a captured interval. Keep raw observation separate from user interpretation.

Illustrative trail, not collected data:

```text
implement-session-recovery
├─ 00:00  VS Code · workspace              planned
├─ 08:20  Chrome · documentation           planned
├─ 13:10  Chrome · video tutorial          deviation → supporting
└─ 19:40  VS Code · workspace              return
```

This is a route through a session. A tree is one presentation of that route;
it is not an inferred task-dependency tree.

### Scope precision

Selecting the whole Chrome application would make every Chrome visit match
that app-level rule. To distinguish documentation from YouTube, select domains
or individual pages with browser integration. Show that distinction in the
picker instead of suggesting that a process selection can inspect tabs.

Similarly, a VS Code executable is an app-level rule. A project-specific rule
requires editor context. A terminal wrapper can say an agent is running, but
needs pane/focus integration before it can say that agent has the user's
attention. Unknown precision should remain explicit.

## How ActivityWatch does it

ActivityWatch separates collection from storage and presentation. Small
watchers report to a local server; the UI reads the recorded data. Watcher
streams are grouped in buckets, commonly by watcher and host. See its
[architecture](https://docs.activitywatch.net/en/latest/architecture.html).

Events have timestamps, durations, and structured data. Consecutive matching
heartbeats can merge within a configured pulse window, reducing storage churn.
Window, browser, editor, and idle streams provide different observations. This
is described in the [data model](https://docs.activitywatch.net/en/latest/buckets-and-events.html).

The official [watcher catalog](https://docs.activitywatch.net/en/latest/watchers.html)
includes a window watcher, an idle watcher, browser extensions, and editor
integrations. Those streams still need to be interpreted together. In
particular, a selected browser tab can remain selected while another desktop
application is foreground. Its [accuracy notes](https://docs.activitywatch.net/en/latest/faq.html#how-accurate-is-activitywatch)
also make clear that these signals are estimates of activity.

## Platform feasibility

| Context | Approach | Boundary |
| --- | --- | --- |
| Windows app/window | Native foreground-window handle, window owner PID, and optional title | A foreground terminal host does not identify its active child pane or agent |
| Linux X11 | EWMH active-window properties, application identity, optional title | Requires an accessible graphical X11 session, not just a Linux process list |
| Linux Wayland | A tested compositor-specific integration or compatible existing watcher | No promise of one generic backend working on every compositor |
| Chrome / Chromium | Browser extension reports active tab and browser-window focus | Title/URL access needs permission; selected tab is not necessarily foreground |
| VS Code project | Editor integration reports workspace/project identity | `Code.exe` alone cannot distinguish two projects in the same app |
| Claude Code / Codex CLI | Explicit terminal/agent integration plus foreground context | A process existing, or an agent generating in the background, is not active attention |
| SSH / headless Linux | Explicit session markers or remote-specific integration | It cannot observe the local desktop from an unrelated remote shell |

Windows exposes the current foreground window through
[GetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getforegroundwindow)
and its owner through
[GetWindowThreadProcessId](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowthreadprocessid).
Use these as a native starting point, with correctly sized handles and graceful
handling of missing windows or exited processes. A PID must be qualified by
process start identity; it can be reused after a restart.

X11's [_NET_ACTIVE_WINDOW](https://specifications.freedesktop.org/wm/1.5/ar01s03.html)
is a defined window-manager property. Wayland needs a different support plan.
The [ActivityWatch Wayland watcher](https://github.com/ActivityWatch/aw-watcher-window-wayland)
documents a limited compositor compatibility matrix. Detect the actual backend
and expose unsupported collection as unknown, rather than making up app time.

For Chrome, the [Tabs API](https://developer.chrome.com/docs/extensions/reference/api/tabs)
provides tab metadata with suitable permissions. Its temporary `activeTab`
permission is granted through user interaction and is not a general solution
for continuously inspecting every tab. The
[Windows API](https://developer.chrome.com/docs/extensions/reference/api/windows)
provides browser-window focus state. A tab selection event alone is insufficient
to assign desktop foreground time.

## Recommended first implementation

Earlier option, superseded by the integrated collector and bundled extension:
build an **optional ActivityWatch adapter** first. It lets us test the focus
scope, interval model, and review screen without maintaining every OS watcher
at once. Breadcrumbs remains usable without ActivityWatch. This is a recommendation,
not a requirement added to the current package.

The adapter should use bounded, read-only requests to the user's local
[ActivityWatch API](https://docs.activitywatch.net/en/latest/api/rest.html),
discover relevant buckets, and import only intervals overlapping an opted-in
block's running spans. Do not assume a fixed bucket ID, machine name, or browser.
Support API authentication when enabled; do not expose the server to a network.

ActivityWatch may itself be recording outside Breadcrumbs sessions. Limiting what
Breadcrumbs imports does not stop that separate application from collecting data.
The setup screen must distinguish those two controls.

After the trail proves useful, evaluate a small native Windows backend and an
optional X11 backend. Add Wayland support compositor by compositor with actual
capability tests. A small browser extension or editor integration can improve
precision later; none should be bundled into the core timer by default.

## Session timing must come first

Today the database stores a block's start/end, elapsed total, and latest
checkpoint. It does not record every pause/resume boundary. Those fields alone
cannot determine which historical browser events happened while the timer was
running.

Add durable running spans before importing activity:

- Open a span when the timer starts or resumes.
- Close it when pausing, entering a switch decision, finishing, or quitting.
- Persist the last confirmed boundary at checkpoints.
- After a crash, close the old span at its last checkpoint, leaving the gap
  until recovery untracked. Resume starts a new span.
- Keep UTC boundaries for joins and monotonic timing for live duration. Flag
  clock discontinuities instead of silently extending an interval.

Intersect activity with those spans and idle signals. Browser detail should
refine an already foreground browser interval, not create a second overlapping
foreground interval. Never extend stale events across missing watcher data,
sleep, reboot, or disconnection. Unknown and idle time should remain visible.

## Proposed local data model

| Record | Purpose |
| --- | --- |
| `focus_scopes` / `focus_scope_rules` | Reusable app, project, domain, or page rules, versioned with a per-block snapshot |
| `session_spans` | Exact running intervals inside an existing named session |
| `activity_intervals` | Source identity, time range, normalized context, precision, and confidence/availability |
| `activity_annotations` | User labels and notes, separate from the source observation |
| `activity_sources` / import cursor | Backend capability and deduplication state |

Use stable source event identities where available and bounded overlap reads
to handle heartbeat events whose durations are still growing. Imports must be
idempotent and isolated by host/browser instance. Tab IDs and PIDs are not
permanent identities. Store event order and capture gaps so a later review can
be rebuilt without guessing a causal relationship.

## Data defaults

Capture is explicit and optional. Default to application identity and browser
domain; full titles and paths require a separate choice. Strip query strings
and fragments before storage, and consider path segments sensitive too. If a
full URL is temporarily needed for matching, evaluate it locally and persist
only the allowed normalized result.

Exclude private browsing from the proposed browser integration. No page-body
capture, screenshots, keystroke contents, or clipboard capture is needed.
Provide collection pause, exclusions, retention, per-session deletion, and
export. Do not write titles or URLs into diagnostic logs. Aggregate agent
exports should be a separate opt-in view, not an automatic raw-history feed.

An ActivityWatch adapter cannot undo data that ActivityWatch already collected;
offer only the guarantees enforced by our own import and storage boundary.

## What would make a first version shippable?

- Scope selection reports the actual precision of every source.
- Windows and Linux/X11 adapter paths are exercised with real watcher data;
  Wayland reports only tested capability.
- Background tabs do not count as foreground use.
- Pause, restart, recovery, idle, watcher loss, and duplicate imports preserve
  correct boundaries without double-counting.
- Multiple browser windows/profiles and reused process identities are handled.
- Helpful detours can be labeled without changing the original observation.
- The timer keeps working when the optional collector is missing or fails.
- A visible trail can explain every counted interval and every unknown gap.

The initial slice above is now implemented with synthetic fixtures and adapter
tests. Next, validate real watcher behavior across supported desktops, improve
browser/profile correlation, and add editor/agent integrations where useful.
