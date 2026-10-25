"""Record the current, music-backed delivery rather than obsolete silent edits."""
from pathlib import Path
import json

base=Path(__file__).resolve().parent
for kind,length in [('launch',35),('setup-guide',222)]:
    p=base/kind
    report=p/'delivery-report.json'
    measured=json.loads(report.read_text()) if report.exists() else None
    notes='''# Final music-backed review

Direction: follow the supplied 33-second reference's rapid word changes, action-led reframing and clean brand close. Preserve the user's exact logo and use real app proof. The launch gives the branch trail 13 seconds; the full guide covers 39 feature entries. Native SVG app captures stay sharp at 1920×1080 through camera moves. No personal browsing data is shown.

Selected story: one goal → one timer → a visible trail → a way back. Alternative subscription-critique and long developer-day narratives were not used; the user asked for a snappy product film and an actual feature guide.

Checked: all 991 reference frames were measured, and its one-second overview and transition contact sheets were inspected. Actual compositions passed lint/runtime/layout checks with no errors and nonzero samples. Inspected scene/phone sheets, close-ups, extension controls, changing sidebar context, reading cards, recovery and the exact supplied logo. Both previews loaded with HTTP 200.

Kept warnings: guide screenshot/overlay tracks are intentionally dense to preserve a continuous app demonstration; 3–7-second instruction holds let first-time users read. Large app crops and the logo image's CSS framing are intentional. No overlap errors remain. Source installation text uses the released wheel route while PyPI authentication is pending.

Sound: the supplied product-launch track enters its full groove at 8.727s. A 110 BPM edit grid drives the launch. Music continues across the whole guide; clicks, typing, pops, whooshes and one impact are tied to visible actions. Final mastering targets −15 LUFS / at most −1 dBTP. Sound is measured, not heard.

Weakest portion: installation demonstrates the exact command but does not record a network download; no installer output is invented. Reading holds make the guide slower than the launch by design. The full feature timestamps are in FEATURE_COVERAGE.md.
'''
    if measured:
        notes+='\nDelivery verified: '+str(measured['duration'])+' seconds, 1920×1080 / 30fps H.264 + AAC, complete FFmpeg decode passed. Integrated '+measured['loudness']['input_i']+' LUFS; true peak '+measured['loudness']['input_tp']+' dBTP.\n'
    (p/'REVIEW.md').write_text(notes,encoding='utf-8')
    (p/'assets/CREDITS.md').write_text('''Breadcrumbs logo: exact artwork supplied by the project owner, with CSS framing only. TUI bread marks are generated terminal colour cells from the same artwork.
Product footage: real Textual/extension captures with isolated synthetic example sessions and observations.
Music: owner-supplied monume-product-product-launch-603962.mp3. The original and local prepared music are not redistributed in Git. The delivered videos use the requested soundtrack.
Effects: HyperFrames offline click, typing, whoosh, pop and bass impact assets; retrieved, not generated. App icons retain the notices in breadcrumbs/assets/brands/NOTICE.md.
Reference video: analyzed locally for pacing and audio levels; no reference footage or soundtrack is included in the delivered film.\n''',encoding='utf-8')
    (p/'STORYLINES.md').write_text('''# Current creative choice
1. SELECTED: one goal, one timer, your trail. Actual product proof builds toward a return to scope; the user's logo and launch command finish it. Supplied 110 BPM music, crisp action effects and beat-led camera motion.
2. Cost of complexity: a subscription/agent critique through kinetic type. Not selected because actual branch proof gives the product a clearer reason to exist.
3. Developer afternoon: a longer narrative about a bug fix. Not selected for the launch; the full guide instead uses that concrete task to explain every feature.\n''',encoding='utf-8')
print('Updated music-backed review notes and asset credits')
