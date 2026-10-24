# Screenshot used in the README

The image shows the actual Breadcrumbs TUI with synthetic data. The capture runs the
application headlessly in a 132 × 39 terminal, uses an isolated temporary
database, and leaves the user's activity and settings untouched.

It demonstrates the current development screen, including the small branch
trail beside intentions. Its tasks, history, and activity are isolated fixtures.

From the repository, after installing development dependencies:

```powershell
python -m scripts.capture_screenshot
```

This produces `docs/assets/breadcrumbs-focus.svg`. Color is enabled for the capture
even if the surrounding shell uses `NO_COLOR`; the prior environment is
restored afterward.

The PNG in the README is a rasterization of that SVG, not a generated mockup.
To regenerate it with the optional documentation-only Node renderer:

```powershell
npm install --prefix .build-check --no-save --package-lock=false @resvg/resvg-js
node scripts/render_screenshot.cjs
```

The renderer dependency goes in the ignored `.build-check` directory. Breadcrumbs's
runtime dependencies do not change. Installed fonts can slightly affect glyph
shapes; the SVG records the same terminal cells and layout.

## Focus branches

Capture the branch view with isolated documentation-only fixtures:

```powershell
python -m scripts.capture_branches
node scripts/render_screenshot.cjs focus-branches
node scripts/render_screenshot.cjs active-context
```

These show the features in Breadcrumbs v0.4.0. The capture
never invokes a desktop collector. Real logo shapes are rendered by Breadcrumbs's
bundled brand masks, with attribution in [BRANDS.md](BRANDS.md).

## Session start and scope

`python -m scripts.capture_scope` captures `start-scope.svg` and
`select-scope.svg`. Render each with the same Node renderer. These show the
actual start gate and scrollable scope picker using synthetic app choices;
no real desktop/process inventory is read and pairing tokens are not shown.

## Feature tour

`python -m scripts.capture_onboarding` captures the actual first-launch tour
at 100 × 34 and a scrollable feature page at 80 × 24. Render `onboarding` and
`onboarding-small` with the Node renderer. The capture uses a temporary data
directory and does not enumerate desktop windows or browser tabs.
