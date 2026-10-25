# Install Breadcrumbs

Requires Python 3.11 or newer. The timer and paired Chrome/Edge extension work
on Windows, Linux and macOS. Native foreground-app capture currently supports
Windows and Linux/X11; macOS and Wayland native capture are unavailable.

## Install with pipx

Install [pipx](https://pipx.pypa.io/stable/installation/) once, then:

```sh
pipx install https://github.com/SaroashDS/Breadcrumbs/releases/download/v0.4.4/breadcrumbs-0.4.4-py3-none-any.whl
breadcrumbs
```

This uses an isolated Python environment and the released wheel. It requires
neither Git nor a piped shell script. Add pipx's application directory to PATH
if prompted (`pipx ensurepath`), then reopen your terminal.

PyPI publication is pending. The public PyPI project API returned 404 for
`breadcrumbs` on 25 October 2026; that is not a reservation or a guarantee that
PyPI will accept the first upload. We do not advertise `pipx install breadcrumbs`
until that distribution is actually published. [Maintainer setup](PUBLISHING.md)

To update this wheel-based install, use the current wheel from the
[latest GitHub release](https://github.com/SaroashDS/Breadcrumbs/releases/latest):

```sh
pipx install --force https://github.com/SaroashDS/Breadcrumbs/releases/download/v0.4.4/breadcrumbs-0.4.4-py3-none-any.whl
```

Replace the version in the URL when a newer release is available.

## Run with uvx

With [uv installed](https://docs.astral.sh/uv/getting-started/installation/):

```sh
uvx --from https://github.com/SaroashDS/Breadcrumbs/releases/download/v0.4.4/breadcrumbs-0.4.4-py3-none-any.whl breadcrumbs
```

uvx manages an isolated cached tool environment. Use the newer wheel URL to
run a new release. Keep using uv/uvx to manage that environment rather than
the app's pip-based background updater.

## Ordinary Python virtual environment

No application manager is required:

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .\.venv\Scripts\Activate.ps1
python -m pip install https://github.com/SaroashDS/Breadcrumbs/releases/download/v0.4.4/breadcrumbs-0.4.4-py3-none-any.whl
breadcrumbs
```

Use `python3` if that is your Python 3.11+ executable.

## Optional Windows private-runtime installer

If you prefer Breadcrumbs to create its own runtime and launcher, download
and inspect [bootstrap.ps1](../bootstrap.ps1), then run the downloaded file:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap.ps1
```

It downloads the latest release, installs into `%LOCALAPPDATA%\Breadcrumbs`,
and creates a launcher in WindowsApps. The familiar PowerShell one-liner
remains an optional route:

```powershell
irm https://raw.githubusercontent.com/SaroashDS/Breadcrumbs/main/bootstrap.ps1 | iex
```

For that runtime, `breadcrumbs update --check` checks GitHub and
`breadcrumbs update` starts the background update. Close other Breadcrumbs
windows when updating; `breadcrumbs update --status` reports the result.

## Develop from source

```sh
git clone https://github.com/SaroashDS/Breadcrumbs.git
cd Breadcrumbs
python -m venv .venv
# Activate the environment as above.
python -m pip install -e ".[dev]"
breadcrumbs
```

Git cloning is a development option, not a requirement for Linux/macOS users.

## Browser extension and first session

Run `breadcrumbs browser setup` for the bundled Chrome/Edge extension folder.
In the TUI, open **C → Browser connection** for the local address and pairing
token. The timer is usable without pairing or capture.

After an update, reload the unpacked extension in your browser. Use
`breadcrumbs browser repair` if a previously installed extension folder needs
refreshing. [Browser guide](BROWSER_EXTENSION.md) · [First session](ONBOARDING.md)
