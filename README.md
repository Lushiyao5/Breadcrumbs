<p align="center">
  <img src="https://raw.githubusercontent.com/SaroashDS/Breadcrumbs/main/docs/assets/breadcrumbs-mark-transparent.png" width="220" alt="Breadcrumbs bread-and-trail mark" />
</p>

<h1 align="center">Breadcrumbs</h1>

<p align="center">
  <strong>A terminal-first productivity timer that helps you understand where you trail off.</strong><br />
  Set an intention, stay with your goal, and leave yourself a trail back.
</p>

```sh
pipx install https://github.com/SaroashDS/Breadcrumbs/releases/download/v0.4.6/breadcrumbst-0.4.6-py3-none-any.whl
```

Then run `breadcrumbs`. **Python 3.11+** and [pipx](https://pipx.pypa.io/stable/installation/) are required.
This installs the released wheel in an isolated environment; no shell script or Git clone.
The wheel installs directly from the GitHub release. [Other install options](docs/INSTALL.md)

<p align="center">
  <img src="https://raw.githubusercontent.com/SaroashDS/Breadcrumbs/main/docs/assets/breadcrumbs-demo.gif" width="900" alt="Set an intention, start, and see the branch trail" />
</p>

**Platform support:** timer + paired Chrome/Edge work on Windows, Linux and macOS.
Native foreground-app capture supports **Windows and Linux/X11 only**.
macOS and Wayland native capture are not implemented. [Details](docs/ACTIVITY.md)

[Installation options](docs/INSTALL.md) · [First session](docs/ONBOARDING.md) ·
[Full guide + keys](docs/USAGE.md) · [Browser extension](docs/BROWSER_EXTENSION.md) ·
[Latest release](https://github.com/SaroashDS/Breadcrumbs/releases/latest)

## Try one block

1. Press `E` and write one small intention. `Ctrl+B` adds a task; `F2` checks it off.
2. Press `Escape`, choose a duration, then `Space` to start.
3. Choose your working scope, reuse it, or continue without tracking.
4. Switch between your work and other apps. Press `B` to inspect the trail.
5. Finish the block, save a reflection, and review it with `H`.

The feature tour opens on first launch. Replay it with `?` while ready or paused.
It never enables capture or starts the timer. [Hands-on onboarding](docs/ONBOARDING.md)

## What it does

| Need | Breadcrumbs feature |
| --- | --- |
| Keep the next step in view | Intentions and a persistent Markdown checklist |
| Work to your own rhythm | Focus/short/long presets, custom timers, pause and resume |
| Understand a detour | App/browser scope, Git-style branches, useful-detour annotations |
| Inspect what happened | Activity details stay beside the trail and follow selection |
| Stop and return later | Named sessions, checkpoints and paused recovery |
| Learn from a block | Reflections, optional focus rating, history and JSON export |
| Stay in the browser | Optional extension countdown, Start/Pause/Resume and confirmed Finish |

Sessions keep their name across work blocks, breaks and restarts. `Ctrl+N`
explicitly starts a new session. Breaks appear in the same trail without capture.
`End` or **Latest** follows the newest activity; selecting an older visit preserves it.

**In scope** matches your choices. **Supporting** marks a useful detour.
**Deviation** is outside scope and can still be useful work. **Unknown** means
the context was not verified. `A`, `S`, and `V` annotate a selected visit.

Optional preferences include three themes, sound previews, a companion and
reading cards. They stay out of the core timer workflow. [Every setting](docs/USAGE.md#settings)

## Browser and terminal context

Open **Config (`C`) → Browser connection** for the extension folder and local
pairing token. Load the unpacked extension in Chrome/Edge, pair, then select
apps, domains or exact pages in scope. Page matching includes query parameters.
Sharing tab context and controlling the timer are separate controls.

Selected Claude Code/Codex CLI activity uses a verified foreground terminal
marker. A running background process alone does not count as focus. Pinned
titles, multiplexers and editor panes may prevent verification; unsupported
context stays Unknown. [Setup and limitations](docs/ACTIVITY.md)

## Install, update and recover

Prefer a one-off run with [uv](https://docs.astral.sh/uv/getting-started/installation/)?

```sh
uvx --from https://github.com/SaroashDS/Breadcrumbs/releases/download/v0.4.5/breadcrumbs-0.4.5-py3-none-any.whl breadcrumbs
```

[All installation options](docs/INSTALL.md) cover pipx, uvx, ordinary virtual
environments, the optional Windows installer and source development.
Use the latest released wheel URL when updating a wheel-based installation.

```sh
breadcrumbs sessions
breadcrumbs --resume my-session
breadcrumbs export --output sessions.json
breadcrumbs export --activity --output activity.json
```

Recovery opens paused. Time while the app was closed is excluded. `Q` saves and
quits; `F` offers Keep working, Finish early or End session.
[Full keyboard reference](docs/USAGE.md#keyboard-reference)

## Why build this?

Too many productivity tools turn a simple need into another subscription, an
unnecessary AI agent, or a system that takes more work to manage than it saves.

Sometimes you just want a timer, goals you can keep in view, and an understanding
of where your attention trails off. Breadcrumbs is for developers moving between
editors, terminals and documentation, and anyone who wants a simpler way to work.

Write what you intend to do. Notice useful detours. Find your way back.

## Your data

Sessions and preferences stay locally in `~/.breadcrumbs`. `BREADCRUMBS_HOME`
chooses another folder. Existing Tlock data and its compatibility command remain usable in place.

Tracking is optional and runs only during running focus/custom blocks. Pauses,
breaks and quitting stop it. Normal export omits activity; `--activity` adds it.
The extension sends domains and URL hashes, not raw paths or queries. Titles
are optional. Hashes identify pages and are not anonymous. Private/internal
tabs are excluded by the extension; app-only capture cannot reliably identify
private windows. [Privacy and capture details](docs/ACTIVITY.md)

## Contributors welcome

Help make everyday work easier: small features, integrations, useful workflows,
bug fixes and clearer docs are welcome. Keep the timer useful on its own and
integrations optional.

Start with a concrete [good first issue](https://github.com/SaroashDS/Breadcrumbs/issues?q=is%3Aissue%20is%3Aopen%20label%3A%22good%20first%20issue%22)
or a [help wanted task](https://github.com/SaroashDS/Breadcrumbs/issues?q=is%3Aissue%20is%3Aopen%20label%3A%22help%20wanted%22).
The [roadmap tickets](docs/CONTRIBUTOR_TASKS.md) cover weekly review, CSV export,
editor context and broader desktop support. See [CONTRIBUTING.md](CONTRIBUTING.md).

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
```

[Changelog](CHANGELOG.md) · [QA](docs/TESTING.md) ·
[Architecture](docs/FOCUS_BRANCHES.md) · [Brand credits](docs/BRANDS.md) ·
[Publishing setup](docs/PUBLISHING.md)

MIT licensed. Brand marks belong to their respective owners.
