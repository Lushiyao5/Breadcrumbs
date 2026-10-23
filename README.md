# Tlock

Tlock is an offline-first terminal focus companion: Pomodoro and custom timers,
an animated pixel mascot, optional Qur'an verses during breaks, completion
melodies, goals, reflections, and a queryable SQLite history.

## Install once on Windows

From a cloned checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
tlock
```

After the first public GitHub Release, new users can install the latest release
without cloning:

```powershell
irm https://raw.githubusercontent.com/SaroashDS/Tlock/main/bootstrap.ps1 | iex
```

After that, open any PowerShell window and type `tlock`. The installer keeps
Tlock in its own private runtime and adds a lightweight launcher to the standard
Windows command path. To remove the app later, run `.\uninstall.ps1`; your
activity database is deliberately preserved.

## Install with pip (macOS, Linux, or development)

```bash
python -m pip install .
tlock
```

Keyboard shortcuts: `Space` starts or pauses, `R` resets, `M` pets the mascot,
`N` spawns a random new companion, `C` opens configuration, `1` selects focus,
`2` short break, `3` long break, and `Q` quits.

The intention editor is multiline and scrollable. Press `Ctrl+B` to add a
checklist task and `F2` to tick or untick the task under the cursor. Checklist
changes made during a running session are saved to SQLite immediately.

The config screen controls every duration, Pomodoro cycle length, auto-start,
Qur'an break cards, three visual themes, sound on/off, and three synthesized
chiptune sound packs. No audio files or external services are required.

Data is stored locally in `~/.tlock/tlock.db`; preferences are stored in
`~/.tlock/config.json`. Override the directory with `TLOCK_HOME`.

## Agent-friendly export

```powershell
tlock export
tlock export --limit 20
tlock export --output activity.json
```

The export contains structured session timestamps, planned goals, actual work,
ratings, timer type, and completion status. Nothing leaves the machine.

## Updates

Updates are explicit and use published GitHub Releases; launching the timer does
not make a network request.

```powershell
tlock update --check
tlock update
tlock update --status
```

The installer can always be rerun to repair or upgrade an installation.

## Publishing on GitHub

This repository is prepared for public development with an MIT license,
cross-platform CI, contribution and security guidance, and tag-driven releases.

1. Change every `SaroashDS/Tlock` reference if your final GitHub owner or
   repository name differs.
2. Create a public repository and push the `main` branch.
3. Confirm the **CI** workflow passes in the Actions tab.
4. Bump the version in both `pyproject.toml` and `tlock/__init__.py`.
5. Commit, tag, and push: `git tag v0.4.0; git push origin main --tags`.
6. The release workflow builds the wheel and source distribution and creates a
   GitHub Release. That release immediately becomes visible to `tlock update`.

Optional PyPI publishing uses trusted publishing. Create a PyPI project and a
trusted publisher for this repository's `release.yml` workflow and `pypi`
environment, then add the GitHub repository variable `PUBLISH_TO_PYPI=true`.
No PyPI API token is stored in GitHub.

The pet-framework investigation and suggested experiments are documented in
[`docs/PET_ENGINE_RESEARCH.md`](docs/PET_ENGINE_RESEARCH.md).

## Development

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```
