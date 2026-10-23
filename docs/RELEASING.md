# Releasing Tlock

Tlock uses two GitHub Actions workflows:

- **CI** runs the test suite and compilation checks on Windows and Ubuntu for
  every push to `main` and every pull request.
- **Release** runs when a tag beginning with `v` is pushed. It checks that the
  tag matches the package version, builds the wheel and source archive, checks
  both packages, and creates a GitHub release with those files attached.

## Publish a release

Start from an up-to-date, clean `main` branch:

```powershell
git switch main
git pull --ff-only
git status
```

Update the version in both `pyproject.toml` and `tlock/__init__.py`, then run the
same checks expected by CI and the release workflow:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q tlock tests
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

Commit and push the version change:

```powershell
git add pyproject.toml tlock/__init__.py
git commit -m "release: v0.5.0"
git push origin main
```

Wait for CI to pass. Then create and push an annotated tag whose value exactly
matches the package version:

```powershell
git tag -a v0.5.0 -m "Tlock v0.5.0"
git push origin v0.5.0
```

That tag push starts the Release workflow. Follow it in the repository's
**Actions** tab. When it finishes, verify the generated release and its wheel
and source archive under **Releases**. `tlock update --check` discovers the
latest published release.

For the initial `0.4.0` release, use `v0.4.0` in the two tag commands; no
version edit is needed if both package files already contain `0.4.0`.

## How GitHub Actions fits together

A workflow is a YAML file in `.github/workflows`. Its `on` section defines the
event that starts it. A workflow contains jobs, each job receives a temporary
runner, and each step either runs a command or invokes a reusable action.

The release runner receives a short-lived `GITHUB_TOKEN` automatically. The
workflow uses it only to create the GitHub release. Optional PyPI publication
is disabled unless the repository variable `PUBLISH_TO_PYPI` is set to `true`.
It uses PyPI trusted publishing rather than a stored API token.
