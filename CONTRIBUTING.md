# Contributing to Breadcrumbs

New features, integrations, practical workflows, bug fixes, accessibility,
documentation, and ideas that make everyday work easier are welcome. Describe
the problem you are solving in an issue or a focused pull request.

1. Fork the repository and create a focused branch.
2. Install development dependencies with `python -m pip install -e ".[dev]"`.
3. Run `python -m pytest -q` before opening a pull request.
4. Keep Breadcrumbs offline-first. New network behavior must be explicit and optional.
5. Do not add copyrighted sprites, audio, translations, or other assets without
   a compatible license and attribution.

Bug reports should include the operating system, terminal, Python version,
Breadcrumbs version (`breadcrumbs --version`), and minimal reproduction steps.

For browser changes, run the extension tests in [TESTING.md](docs/TESTING.md).
Keep the timer usable without integrations. Label inferred context honestly,
retain pause/privacy gates, and include a regression test for a behavior fix.
