# Breadcrumbs videos

Two editable HyperFrames projects using real Breadcrumbs TUI captures with
synthetic demo data. No personal browsing history or pairing tokens are shown.

- `setup-guide`: 222-second complete walkthrough with a macOS-style terminal
  frame, smooth camera zooms, cursor movement, click presses and ripples.
  Installation instructions target Windows / PowerShell, followed by the real
  app: intentions, a checklist, start/pause/resume, the persistent activity
  sidebar, Config and the browser pairing screen.
- `launch`: 35-second kinetic app film about one intention, simple timing,
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
.\.venv\Scripts\python.exe -m scripts.capture_feature_tour
.\.venv\Scripts\python.exe videos/prepare_audio.py
.\.venv\Scripts\python.exe videos/build_v3.py
```

The capture runner uses an isolated temporary database. The installation
terminal shows the exact documented command as instructional text, without
inventing installer output. App interaction is captured from the actual UI;
fixture observations are labelled as a demonstration in the tutorial.

Music uses the project owner's supplied product-launch track, cut to its
110 BPM groove. Click, typing, whoosh, pop and impact effects come from the
HyperFrames offline library. The provided music stays local and is excluded
from Git; `prepare_audio.py` expects the supplied MP3 in Downloads. Render
to `renders/breadcrumbs-launch-music-raw.mp4` or
`renders/breadcrumbs-complete-guide-raw.mp4`, then run
`python videos/deliver_v3.py launch` or `python videos/deliver_v3.py setup-guide`
from the repository root to master the mix to −15 LUFS and verify the file.
The launch delivery also creates the 13-second README GIF.

There is no narration. Keep `assets/CREDITS.md` with the editable
sources and preserve the product's bundled icon license notices.
