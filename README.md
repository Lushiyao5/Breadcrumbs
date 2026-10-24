# Tlock

Tlock is a terminal timer for focused work. It combines Pomodoro and custom
timers with a checklist, end-of-session reflection, and local history. The main
screen keeps the timer and intentions in view; history opens separately.
An optional pixel companion and Qur'an verse cards can be enabled in Settings.

Session history and intention drafts are stored on your machine in SQLite;
preferences use a local JSON file. Starting Tlock does not require an account
or a network connection.

[Latest release](https://github.com/SaroashDS/Tlock/releases/latest) ·
[What's new in v0.3.0](docs/releases/v0.3.0.md)

## Features

- Focus, short-break, long-break, and custom timers
- Scrollable, multiline intentions with checkable tasks
- A reflection prompt after completed focus sessions
- An optional pixel companion, hidden by default
- Saved intention drafts and unfinished tasks carried into the next block
- Named session checkpoints that survive application and machine restarts
- Finish early, end, or keep working before resetting or switching presets
- Quick focus rhythms (25/5, 50/10, and 60/10) and a daily focus summary
- Three 8-bit themes and three synthesized completion sounds
- Rotating Qur'an or quote cards with an optional book animation
- Local session history and JSON export
- Explicit, release-based updates through GitHub

## Install on Windows

Tlock requires Python 3.11 or newer.

Install the latest release from PowerShell:

```powershell
irm https://raw.githubusercontent.com/SaroashDS/Tlock/main/bootstrap.ps1 | iex
tlock
```

If you already have a checkout, install that copy instead:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

The installer creates a private runtime under `%LOCALAPPDATA%\Tlock` and adds a
small `tlock` launcher to the standard Windows command path. Run
`.\uninstall.ps1` from a checkout to remove the application. Uninstalling keeps
your activity history.

## Install from source

On macOS, Linux, or in a development environment:

```bash
git clone https://github.com/SaroashDS/Tlock.git
cd Tlock
python -m pip install .
tlock
```

## A focus block

1. Press `E` and write your intentions. Drafts save automatically, even before
   the timer starts. Press `Escape` when you're ready.
2. Choose Focus, Short, Long, or a custom duration, then start the timer.
3. Tick tasks with `F2` as you finish them. After the block, record what you
   accomplished and optionally rate your focus.
4. Unchecked tasks and notes carry forward. Completed tasks remain in that
   session's history, which you can read with `H`.

The companion is hidden by default. Enable **Show companion** in Settings if
you want it on screen. Small terminals use a scrolling layout.

## Named sessions and recovery

Each block gets a name such as `calm-otter-a3f2` from a built-in word library.
Edit the **Session name** field before starting, or keep the generated name.
Names are unique and use letters, numbers, and hyphens.

Tlock saves the timer, intentions, and session identity every second and when
you pause or quit. After a restart, choose a saved block or start a new one.
Starting a new block keeps the other saved blocks available.

```powershell
tlock sessions
tlock --resume calm-otter-a3f2
tlock --name my-reading-block
```

`--session NAME` is an alias for `--resume NAME`. Resumed blocks open paused at
their last checkpoint; press `Space` to continue. Time spent outside Tlock does
not count as work. A sudden shutdown may lose roughly the last second of timer
progress. Normal exits save immediately and print the resume command.

Press `P` for a focus rhythm. Switching timers or resetting an active block
opens a choice: **Keep working**, **Finish early**, or **End session**. Finishing
early records the time actually worked and opens a reflection. Ending records
the partial time without marking the block completed. Press `F` to open this
choice directly. Custom countdowns stay standalone after completion.

The header summarizes focus time and completed blocks for sessions started
today, using your machine's local date. Breaks are excluded.

## Reading cards

In Settings, choose **Off**, **Qur'an**, or **Quotes**. Cards can appear during
every block or only during breaks, and rotate every 1–60 minutes (two minutes
by default). Immediate repeats are avoided. The brief book animation runs when
a new card appears and can be disabled independently.

Verses cover effort, knowledge, patience, trust, and hope. Cards show Arabic,
an English meaning, and a verse reference; partial verses are labeled as
excerpts. Quotes are original Tlock reminders about effort, rest, and starting
again. All content is bundled locally. See [reading sources](docs/READING.md).

## Controls

The command bar remains visible while the main timer screen is open.

| Key | Action |
| --- | --- |
| `Space` | Start or pause |
| `R` | Reset the current timer |
| `F` | Finish early / end / keep working |
| `P` | Choose a focus rhythm |
| `1` / `2` / `3` | Focus / short break / long break |
| `M` | Pet the companion |
| `N` | Spawn a random companion |
| `C` | Open configuration |
| `E` | Edit intentions |
| `H` | Open recent history and reflections |
| `Q` | Quit |

Inside the intention editor:

| Key | Action |
| --- | --- |
| `Enter` | Continue a checklist with a new task |
| `Ctrl+B` | Add a checklist item |
| `F2` | Tick or untick the item under the cursor |
| `Escape` | Return to timer controls |
| Mouse wheel / arrow keys | Scroll and move through longer plans |

Configuration covers durations, cycle length, auto-start behavior, themes,
sound, and break verses. Use `Ctrl+S` to save a configuration or reflection
dialog and `Escape` to close it without saving.

Use **Preview** beside the sound pack selector to hear the current selection
before saving. Preview works even when completion sounds are switched off.

## Local data

By default, Tlock writes two files:

- `~/.tlock/tlock.db` — sessions, intentions, and reflections
- `~/.tlock/config.json` — application preferences

Set `TLOCK_HOME` to use a different directory. No activity data leaves the
machine unless you export or copy it yourself.

Export structured history for scripts or local agents:

```powershell
tlock export
tlock export --limit 20
tlock export --output activity.json
```

## Updates

Updates are opt-in and come from published releases in this repository. Normal
timer use makes no network requests.

```powershell
tlock update --check
tlock update
tlock update --status
```

The updater runs in the background. Check its status and reopen Tlock after it
finishes. Your session database and preferences are kept.

## Development

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and
[docs/RELEASING.md](docs/RELEASING.md) for the release process. Notes from the
terminal pet framework research are in
[docs/PET_ENGINE_RESEARCH.md](docs/PET_ENGINE_RESEARCH.md).

Security issues should follow [SECURITY.md](SECURITY.md).

Tlock is available under the [MIT License](LICENSE).
