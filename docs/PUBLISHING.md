# Publish Breadcrumbs to PyPI

The distribution is `breadcrumbst`; the product and main command
remain `breadcrumbs`. PyPI rejected `breadcrumbs` as a disallowed project name
despite its public API returning 404. The owner has selected the accepted
`breadcrumbst` name in the trusted-publisher form.

## Current status

`breadcrumbst` v0.4.6 is published on PyPI. Public-registry pipx and uvx installs
were verified against that version. The main console command is `breadcrumbs`.
GitHub release wheels remain available as an alternative.
The source distribution includes the application, tests and package metadata;
local video renders, supplied music and authoring caches are excluded.
The `pypi` environment and trusted publisher are configured. Tagged releases
publish automatically with `PUBLISH_TO_PYPI=true`; no local account token is needed.

## One-time owner setup

Sign in to your own PyPI account and add a
[pending trusted publisher](https://pypi.org/manage/account/publishing/):

| Field | Value |
| --- | --- |
| PyPI project name | `breadcrumbst` |
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
2. Confirm the upload succeeded and `https://pypi.org/pypi/breadcrumbst/json`
   reports this repository and the intended version.
3. In a clean environment, run both commands below and verify the version,
   `breadcrumbs browser path`, and a headless timer/session smoke check.
4. Replace the README's wheel URL with the short PyPI commands only then.

```sh
pipx install breadcrumbst
uvx breadcrumbst
```

For local build checks:

```sh
python -m pip install build twine
python -m build
python -m twine check dist/*
```

Both installs expose the usual `breadcrumbs` command; `breadcrumbst` is
also an entry point so uvx can infer the command from the distribution name.

Existing tags/releases are immutable. Current work targets v0.4.6; do not
recreate the historical v0.4.0 release to retry publishing.
