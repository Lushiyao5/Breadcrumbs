# Security policy

Please do not publish suspected vulnerabilities in a public issue. Use GitHub's
private vulnerability reporting feature under **Security → Advisories → New
draft advisory**.

Breadcrumbs' updater connects when the user runs `breadcrumbs update`. It reads the
latest published GitHub Release and installs that release's source archive.
Normal timer use remains offline.

Only the latest release receives security fixes.

Contributions are reviewed before execution and merge. See the
[maintainer PR review procedure](docs/PR_REVIEW.md). Do not include personal
session exports or pairing tokens in reports. New dependencies, network access,
build steps and third-party assets must be disclosed in the PR.
