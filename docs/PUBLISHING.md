# Publish Breadcrumbs to PyPI

The package and command are both `breadcrumbs`. On 25 October 2026 the public
PyPI JSON endpoint for that name returned 404. The final availability check is
the first successful upload: a missing public project does not reserve a name
or rule out a prohibited/deleted name.

## Current status

GitHub release wheels are published and support pipx/uvx installation now.
The source distribution includes the application, tests and package metadata;
local video renders, supplied music and authoring caches are excluded.
PyPI publication is not yet configured: no local PyPI token, `.pypirc`, or
enabled repository publishing configuration was available during this update.
The README therefore uses the real released wheel URL rather than claiming a
bare package-name install already works.

## One-time owner setup

Sign in to your own PyPI account and add a
[pending trusted publisher](https://pypi.org/manage/account/publishing/):

| Field | Value |
| --- | --- |
| PyPI project name | `breadcrumbs` |
| GitHub owner | `SaroashDS` |
| Repository | `Breadcrumbs` |
| Workflow filename | `release.yml` |
| Environment | `pypi` |

Then run the **Release** workflow on the released tag with
**Publish to PyPI** enabled, or set the GitHub repository variable
`PUBLISH_TO_PYPI=true` for future tagged releases. The workflow requests a
short-lived OIDC token and never needs a long-lived token in the repository.
Do not paste an account token into an issue, source file or chat.

The pending publisher creates the PyPI project on first use. It does not
reserve the name beforehand. If PyPI rejects the name, select an available
distribution name, update `project.name` and the installation docs together,
and retain the `breadcrumbs` console command.

Official instructions: [create a project through OIDC](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
and [publish with a trusted publisher](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

## Verify before advertising PyPI installs

1. Confirm the wheel and sdist passed the release build and `twine check`.
2. Confirm the upload succeeded and `https://pypi.org/pypi/breadcrumbs/json`
   reports this repository and the intended version.
3. In a clean environment, run both commands below and verify the version,
   `breadcrumbs browser path`, and a headless timer/session smoke check.
4. Replace the README's wheel URL with the short PyPI commands only then.

```sh
pipx install breadcrumbs
uvx breadcrumbs
```

For local build checks:

```sh
python -m pip install build twine
python -m build
python -m twine check dist/*
```

Existing tags/releases are immutable. Current work targets v0.4.4; do not
recreate the historical v0.4.0 release to retry publishing.
