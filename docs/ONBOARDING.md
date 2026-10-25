# Your first week with Breadcrumbs

You do not need to turn on every feature at once. This guide walks through all
of them in short exercises. The app's first-launch tour introduces the same
features; replay it with `?` while the timer is ready or paused.

## 1. Finish one small task

Launch `breadcrumbs`. Read or skip the tour. Press `E`, use `Ctrl+B` to add
a task, and write something small: “Read the failing test.” Press `Escape`.
Keep the generated session name or enter a unique name.

Enter **2** in custom minutes, choose **Set timer**, then press `Space`.
Choose **Continue without tracking**. Use `E` and `F2` to check the task when
done, then `Escape` to return. When the countdown ends, describe the result,
optionally rate your focus, and save with `Ctrl+S` or skip with `Escape`.

Open `H`. Your name, intentions, elapsed work, and reflection should be there.
Unchecked tasks and notes carry forward; checked tasks stay in that block.

## 2. Learn the timer and recovery controls

Press `P` to try a 25/5, 50/10, or 60/10 rhythm. `1`, `2`, and `3` select Focus,
Short break, and Long break. `C` changes durations and full Focus blocks per
long break. Only a full Focus countdown advances the round; a full long break
resets it. Custom and early-finished work still contribute to work totals.

Start another short block. Pause with `Space`, then resume. Press `Q` to save
and quit. Run `breadcrumbs sessions`, then `breadcrumbs --resume NAME` using
the saved name. Recovery opens paused; press `Space` when ready. Time while
the app was closed is excluded. Activity spans stay separate across pauses
and recovery. Checkpoints save about every second.

Press `F`. Try **Keep working** first. When ready, **Finish early** records
elapsed work and opens reflection; **End session** keeps partial work without
marking it complete. Reset and timer changes offer the same choices.

## 3. Add app scope and inspect a real trail

Start a Focus/custom block and choose **Choose scope and start**. Select your
editor with `Space`; add an app name manually if needed. Choose whether to
store titles, then `Ctrl+S` to save. Capture starts with the block.

Switch to another app, then return. The small trail should pulse and show
changes. Click it or press `B` to inspect visits, timestamps, durations, logos,
and the capture source/precision. The bottom status line describes context.

- **In scope:** matches your choices.
- **Deviation:** outside scope; it can still be useful work.
- **Supporting:** your annotation for a useful detour.
- **Unknown:** evidence was unavailable; it is not a scope judgment.
- **Away / Excluded:** idle or excluded context, kept separate.

Select a visit and use `A`, `S`, or `V` to mark In scope, Supporting, or
Deviation. Unknown/Away/Excluded observations keep their labels. Use the
block selector to inspect older trails. **Scope / source** edits the current
block's scope. Earlier spans keep their original scope snapshot.

Pause: capture stops and the small trail freezes. Breaks also stop capture.
Next time, try **Use previous scope**. **Continue without tracking** keeps
your remembered scope available for a later block.

## 4. Pair your browser and select a page

Open **C → Browser connection**. In Chrome or Edge:

1. Open `chrome://extensions` or `edge://extensions`.
2. Enable **Developer mode** and choose **Load unpacked**.
3. Select the extension folder shown by Breadcrumbs.
4. Open the extension popup, paste the local address/token, and pair it.

Keep the token on your computer. Return to the scope picker, wait for tabs,
and select an individual documentation page. Alternatively enter a domain
such as `docs.python.org`; that also matches subdomains.

Switch to a different URL and return. Exact page identity includes query
parameters. Different URLs with similar titles remain different pages.
Selecting the browser app does not override page/domain restrictions.
Unverified browser context is Unknown when page rules are selected.

Open the popup during an existing block: it should find the countdown and
match the terminal theme. Try Pause, Resume, and Finish. Cancel Finish once,
then confirm when ready. The reflection appears in the terminal. Start can
begin the next ready block using remembered scope; choose new scope in the TUI.

Stop sharing and try Pause/Resume again. Timer controls remain available;
sharing controls only govern tab reports. Disconnect removes saved pairing.
See the [browser guide](BROWSER_EXTENSION.md) for setup details.

## 5. Try a supported terminal agent

Open Claude Code or Codex CLI, then reopen **B → Scope / source**. Choose a
detected process. Breadcrumbs verifies its identity and an active terminal
title marker; a background process alone is not evidence of focus. Temporary
markers are removed when tracking stops.

Pinned tab titles, terminal multiplexers, and editor-integrated panes can
prevent verification. Expect Unknown rather than a guess. Select the terminal
app for broader host-level scope when that fits your plan. Native foreground
capture supports Windows and Linux/X11; see [support limits](ACTIVITY.md).

## 6. Personalize the experience

Open `C`. Try Midnight Arcade, Game Boy, or Sunset Drive. Select Arcade,
Victory, or Gentle sound and choose **Preview**; this works even if completion
sound is disabled and does not save changes. Windows uses note sequences;
other platforms use the terminal bell.

Enable the optional companion and try `M` to pet it and `N` to change it.
Choose reading cards: Off, Qur'an, or Quotes. Show them in every block or
breaks only, rotate every 1–60 minutes, and toggle the book animation.
Content is bundled locally; [reading sources](READING.md) describe it.

Choose whether breaks/focus start automatically. `Ctrl+S` saves Config;
`Escape` discards unsaved changes. Theme changes also appear in the extension.

## 7. Review and keep a copy

Use `H` for intentions, reflections, and completion status. The header shows
today's work minutes and completed work blocks using your computer's local
date; breaks are excluded. The long-break round is a separate counter.

```powershell
breadcrumbs export --output sessions.json
breadcrumbs export --activity --output activity.json
breadcrumbs export --limit 20 --output recent.json
breadcrumbs update --check
breadcrumbs update
```

Normal export omits activity. `--activity` adds observations, annotations,
scope, and running spans. New data lives in `~/.breadcrumbs`; set
`BREADCRUMBS_HOME` to choose another directory. Existing data and compatibility
commands remain usable in place.

Tracking is opt-in. Domains and URL hashes leave the extension, not raw URL
paths/queries; hashes are not anonymous. Titles are optional. The extension
excludes private/internal tabs; app-only capture cannot reliably identify
private windows. Pause, breaks, and exit stop capture.

After updating, reload the unpacked extension. `breadcrumbs browser repair`
refreshes a previously installed extension folder if needed. See the
[user guide](USAGE.md) for the full keyboard reference.
