# Focus branches

Breadcrumbs v0.4.0 includes the integrated tracker and bundled browser extension.

## Start a block

Press Start or Space. Choose **Choose scope and start**, **Use previous scope**
when available, or **Continue without tracking**. Cancel leaves the timer ready
and creates no session. Breaks do not capture activity.

Select apps and recognized running Claude Code/Codex CLI processes with Space.
Add app names or domains if needed. For individual pages, connect the bundled
browser extension, wait for its tab inventory, then select pages. Ctrl+S saves
the scope and starts the block.

During a block, B → **Scope / source** edits its scope. The change starts a new
running span with its own scope snapshot; earlier observations stay intact.
Saved scope becomes the default for later blocks. An untracked start does not
erase that default. Recovery opens paused and restores that block's scope.

## Browser setup

Run `breadcrumbs browser setup`, or open **Config (C) → Browser connection**.
Load the bundled folder as an unpacked extension in Chrome or Edge, then pair
it with the address and token shown in Breadcrumbs. Installation is manual once.
No ActivityWatch installation, separate tracker service, or account is needed.

The bridge binds only to 127.0.0.1 and requires a local pairing token. Breadcrumbs owns
its lifetime. Outside a running tracked block, the extension sends no active
tab metadata. Opening the scope picker temporarily permits an inventory of
normal web tabs, held in memory to let you select them.

The small trail beside intentions shows recent recorded nodes without app
names. The live node pulses during running capture and freezes on pause.
Click it or press B to inspect the full trail.

Page rules use hashes of canonical URLs, including their query parameters.
Different YouTube videos become different contexts. Raw URLs never leave the
extension. Domains are readable; optional titles may contain document names.
Hashes identify pages; they are not a guarantee of anonymization.

See [extension installation and protocol](BROWSER_EXTENSION.md).

## Scope rules

- App names match executable/application names.
- Selecting Chrome alone allows all Chrome visits.
- Adding domains or pages narrows browser matches, even if Chrome is selected.
- A domain permits its subdomains, using a domain boundary.
- An individual page permits that page hash. Navigation can leave the scope.
- A selected terminal agent requires a live process identity and its marker in
  the foreground terminal title. A background process alone never counts.

Other active apps still appear in the trail. An out-of-scope visit is
**Deviation**: it left your chosen scope. A tutorial might still help your task;
use S to mark it supporting. Returning to a selected app or page automatically
joins the main lane, marked **Back in scope**.

Selecting an exact page keeps its full URL identity, including query parameters.
The same visible page title with a different URL remains outside scope. Browser
app selection does not bypass selected page/domain rules.

## Desktop and terminal support

Windows reads the foreground window and executable; visible windows supply app
choices. Three minutes without input reports away. Linux/X11 uses `xprop`;
`wmctrl`, when installed, improves app choices. X11 has no native idle signal.

Wayland and macOS native foreground capture are unavailable in this preview.
A paired browser can report browser focus when desktop context is unavailable,
with reduced precision explicitly shown. It cannot claim complete app coverage.

Fresh browser events and native window title hashes provide tab detail without
storing the title when titles are disabled. A different native foreground app
wins over a browser heartbeat. Ambiguous profiles, stale data, or unavailable
sources fall back to window precision or unknown context.

With exact page/domain rules, window-only capture is **Unknown**, not a
deviation: a window title cannot establish which URL is active. The status
bar says when tab verification is missing or the URL differs from the selected
pages. Reopen Scope to see saved URLs that are no longer present in open tabs.
Selected terminal agents that cannot be verified likewise show Unknown, with
their marker error available in Scope. Historical window-only records keep
their original labels; visit details explain their limited precision.

Selected terminal agents use a temporary title marker managed by a Breadcrumbs
helper. It verifies process birth identity to avoid PID reuse and removes its
marker on pause or exit. Windows console attachment and supported Linux terminal
title handling are best effort. Fixed tab titles, terminal multiplexers, and
editor-integrated terminals can prevent pane attribution; those remain host
context. Select GUI Claude/Codex apps as apps, separately from CLI candidates.

Private and internal browser tabs are excluded by the extension. Without a
paired extension, app-only capture cannot reliably detect private browsing.
Disable titles if you do not want window names retained.

## Read the trail

B shows timestamped visits. Main-lane nodes match the scope; side lanes show
departures and returns. Up/Down selects a visit, including its logo and source
precision. A marks in scope, S supporting, V deviation (U also works). These annotations
remain separate from the source observation. Away, excluded, and unknown
observations retain their labels.

The bar above the persistent command keys shows the latest sampled context.
Capture runs only during running focus/custom blocks. Pause, breaks, decision
dialogs, and exit stop it. Late results from earlier spans are discarded.
Sampling estimates transition times; it does not record every click.

Browser updates are event-driven, with a ten-second heartbeat while awake and
a thirty-second alarm fallback. MV3 worker suspension can delay reports. Records
expire after 45 seconds rather than remaining live indefinitely.

## Persistence and export

Intervals, annotations, and running spans share the local SQLite database.
Recovery closes the old span at its last durable boundary and resumes in a new
span; closed-app time is not joined into the trail. Exited agent process
identities must be reselected.

Ordinary exports remain session-only. Include context explicitly:

```powershell
breadcrumbs export --activity --output activity-with-branches.json
```

This adds activity_intervals, running_spans, focus_scope, and
activity_schema_version. Timestamps are Unix seconds. Pairing tokens and
unselected tab inventories are never exported.

## Long-break progress

The timer says how many full focus blocks remain until a long break. Only a
Focus timer that reaches zero advances that progress. Custom timers, early
finishes, ended blocks, and short breaks do not. Completing a full long break
resets the round. Progress survives restarts.

Daily totals also include useful time from custom and early-finished blocks.
