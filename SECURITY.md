# Security policy

Please do not publish suspected vulnerabilities in a public issue. Use GitHub's
private vulnerability reporting feature under **Security → Advisories → New
draft advisory**.

Tlock's updater connects only when the user runs `tlock update`. It reads the
latest published GitHub Release and installs that release's source archive.
Normal timer use remains offline.

Only the latest release receives security fixes.
