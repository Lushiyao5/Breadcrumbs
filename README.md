# Tlock

Tlock is a terminal timer for focused work. It combines Pomodoro and custom
timers with a checklist, end-of-session reflection, local history, an animated
pixel pet, and optional Qur'an verses during breaks.

Everything is stored on your machine in SQLite. Starting Tlock does not require
an account or a network connection.

## Features

- Focus, short-break, long-break, and custom timers
- Scrollable, multiline intentions with checkable tasks
- A reflection prompt after completed focus sessions
- Randomized pixel pets that react to timer state and interaction
- Three 8-bit themes and three synthesized completion sounds
- Optional Qur'an verse cards during breaks
- Local session history and JSON export
- Explicit, release-based updates through GitHub

## Install on Windows

Tlock requires Python 3.11 or newer.

Clone the repository, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
tlock
```

The extension matters: the installer is `install.ps1`, not `install.ps`.

After the first GitHub release is published, the latest version can also be
installed without cloning:

```powershell
irm https://raw.githubusercontent.com/SaroashDS/Tlock/main/bootstrap.ps1 | iex
```

The installer creates a private runtime under `%LOCALAPPDATA%\Tlock` and adds a
small `tlock` launcher to the standard Windows command path. Run
`.\uninstall.ps1` from a checkout to remove the application. Uninstalling keeps
your activity history.

## Install from source

On macOS, Linux, or in a development environment:

```bash
python -m pip install .
tlock
```

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
| `Q` | Quit |

Inside the intention editor:

| Key | Action |
| --- | --- |
| `Ctrl+B` | Add a checklist item |
| `F2` | Tick or untick the item under the cursor |
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
