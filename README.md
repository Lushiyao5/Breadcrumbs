# Tlock

Tlock is a terminal timer for focused work. It combines Pomodoro and custom
timers with a checklist, end-of-session reflection, and local history. The main
screen keeps the timer and intentions in view; history opens separately.
An optional pixel companion and Qur'an verse cards can be enabled in Settings.

Session history and intention drafts are stored on your machine in SQLite;
preferences use a local JSON file. Starting Tlock does not require an account
or a network connection.

[Latest release](https://github.com/SaroashDS/Tlock/releases/latest) ·
[What's new in v0.2.0](docs/releases/v0.2.0.md)

## Features

- Focus, short-break, long-break, and custom timers
- Scrollable, multiline intentions with checkable tasks
- A reflection prompt after completed focus sessions
- An optional pixel companion, hidden by default
- Saved intention drafts and unfinished tasks carried into the next block
- Three 8-bit themes and three synthesized completion sounds
- Optional Qur'an verse cards during breaks
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

## Controls

The command bar remains visible while the main timer screen is open.

| Key | Action |
| --- | --- |
| `Space` | Start or pause |
| `R` | Reset the current timer |
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
