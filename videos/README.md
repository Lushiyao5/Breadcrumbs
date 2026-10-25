# Breadcrumbs videos

Two editable HyperFrames projects using real Breadcrumbs TUI captures with
synthetic demo data. No personal browsing history or pairing tokens are shown.

- `setup-guide`: 88-second continuous walkthrough with a macOS-style terminal
  frame, smooth camera zooms, cursor movement, click presses and ripples.
  Installation instructions target Windows / PowerShell, followed by the real
  app: intentions, a checklist, start/pause/resume, the persistent activity
  sidebar, Config and the browser pairing screen.
- `launch`: 28-second kinetic app film about one intention, simple timing,
  visible detours and finding a way back. No subscription or AI service is needed.

Open either directory and run `npm run dev`, or use
`npx hyperframes preview --background`. Both projects pin HyperFrames 0.8.193.
The HTML scene and media can be edited directly in the preview.

Render with `npm run render -- --quality delivery --low-memory-mode`.
Delivery files live in each project's `renders/` folder and are intentionally
excluded from Git. Node.js 22+ and FFmpeg are needed for the video tooling;
Breadcrumbs itself needs only Python 3.11+.

To regenerate the real app interaction frames from the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.capture_video
npm install --prefix .build-check --no-save --package-lock=false @resvg/resvg-js
node videos/rasterize.cjs
.\.venv\Scripts\python.exe videos/build_motion.py
```

The capture runner uses an isolated temporary database. The installation
terminal shows the exact documented command as instructional text, without
inventing installer output. App interaction is captured from the actual UI;
fixture observations are labelled as a demonstration in the tutorial.

Sound uses HyperFrames' bundled offline click, typing and whoosh assets.
There is no narration or music bed. Keep `assets/CREDITS.md` with the editable
sources and preserve the product's bundled icon license notices.
