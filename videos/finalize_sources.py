"""Keep only the authored motion sources and document the final creative choice."""
from pathlib import Path
import json

base=Path(__file__).resolve().parent
for kind in ('launch','setup-guide'):
    p=base/kind
    for unused in (p/'assets').glob('*.png'):
        unused.unlink()
    old=p/'assets/transition.mp3'
    if old.exists(): old.unlink()
    (p/'STORYLINES.md').write_text('''# Final storyline choice
1. SELECTED — Real app in motion. One continuous terminal window, cursor-led close-ups and smooth returns to the full view. The tutorial follows installation instructions through a real first session; the launch accelerates the same workflow into intention → timer → detour → return.
2. Cost of complexity. A typographic critique of subscriptions and unnecessary agents; not built because the user explicitly rejected slide-based storytelling.
3. Developer afternoon. A longer narrative about fixing one bug; not built because the user requested a direct tutorial and a snappy launch film.
Sound: bundled offline click, typing and whoosh accents. No music provider or narration.\n''',encoding='utf-8')
    data=json.loads((base/'recording/timeline.json').read_text())
    if kind=='setup-guide':
        beats=[(0,'PowerShell installation instructions'),(10,'Open the actual app'),(14,'Type the intention'),(18,'Type a checklist item'),(25,'Click Start'),(29,'Continue without tracking'),(36,'Pause'),(39,'Resume'),(45,'Open branch trail with fixture observations'),(49,'Inspect Chrome'),(52,'Inspect useful tutorial'),(55,'Inspect a deviation'),(58,'Back in scope'),(65,'Config'),(73,'Browser pairing'),(80,'Back to work')]
    else:
        beats=[(0,'One thing to do; real app behind the hook'),(2,'Type an intention'),(5,'Click Start'),(7,'Timer close-up'),(10,'Pause and resume'),(12,'Branch trail'),(15,'Useful detour details'),(17,'Return to scope'),(18.5,'Find your way back'),(21,'Breadcrumbs wordmark and repository')]
    (p/'STORYBOARD.md').write_text('\n'.join(f'- {t}s / frame {round(t*30)}: {label}.' for t,label in beats)+'\n',encoding='utf-8')
    (p/'REVIEW.md').write_text('''# Review
Creative call: rebuilt after the user rejected the initial slide deck. The final film uses real app interaction frames, a continuous macOS-style window, cursor presses, click rings and animated camera close-ups. The launch compresses the workflow into 28 seconds; the tutorial keeps 88 seconds for instruction reading.
Checked: HyperFrames lint/runtime/layout/contrast sampled the final composition with no errors. Inspected key camera positions, typing, Start dialog, pause/resume, actual changing branch details, browser pairing and end card. The preview returned HTTP 200 and loaded both full timelines.
Warnings retained: dense screenshot/overlay tracks are intentional for a continuous recorded interaction. Tutorial holds of 3–6 seconds allow reading; its 22px PowerShell window title is decorative chrome, not instructional copy. Tutorial reading overlays are 29px; terminal commands are 32px. Source screenshots use real app text at native resolution and are zoomed for the feature being demonstrated.
Weakest section: installation shows the documented command being typed and does not record a network download. It avoids invented installer output. Pairing is shown only through the local setup screen; no real browser data or token is revealed.
Sound: click, typing and whoosh assets only. No music bed or narration. Audio can be measured after rendering but has not been heard.\n''',encoding='utf-8')
    (p/'assets/CREDITS.md').write_text('''Product: Breadcrumbs actual app captures, synthetic local demo data, no personal activity. Capture code and product source are in this repository.
Sound: HyperFrames bundled offline click (0.4s), typing (1.5s), and whoosh (0.6s) assets resolved with media-use; no external stock track.
Camera reference: HyperFrames registry cursor-zoom-follow; adapted cursor presses, ripple behavior and focus-led camera treatment. No built-in dashboard appears in the film.
App logos retain their original Simple Icons / Microsoft Codicons license notices in breadcrumbs/assets/brands/NOTICE.md.\n''',encoding='utf-8')
old=base/'build_projects.py'
if old.exists(): old.unlink()
unused=base/'setup-guide/compositions/components/cursor-zoom-follow.html'
if unused.exists(): unused.unlink()
print('Final motion sources and review notes ready')
