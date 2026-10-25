"""Continuous Screen Studio-style walkthrough and kinetic product launch."""
from pathlib import Path
import json
import shutil
import html

BASE=Path(__file__).resolve().parent
recording=json.loads((BASE/'recording/timeline.json').read_text())

STYLE='''
*{box-sizing:border-box;margin:0}#root{position:absolute;inset:0;overflow:hidden;background:#172235;font-family:Inter;color:#fff}
.backdrop{position:absolute;inset:0;background:linear-gradient(130deg,#263c54 0%,#303248 52%,#504340 100%)}
.camera{position:absolute;inset:0;transform-origin:960px 540px}
.window{position:absolute;left:180px;top:70px;width:1560px;height:930px;border-radius:15px;overflow:hidden;background:#090b12;box-shadow:0 32px 85px #0009;border:1px solid #ffffff35}
.image{position:absolute;inset:0;width:100%;height:100%;object-fit:fill}.terminal{position:absolute;inset:0;background:#090b12}.chrome{height:42px;background:#292929;display:flex;align-items:center;justify-content:center;font:22px 'IBM Plex Mono';color:#ccc}.dots{position:absolute;left:20px;top:14px;display:flex;gap:10px}.dots i{display:block;width:14px;height:14px;border-radius:50%;background:#ff6058}.dots i:nth-child(2){background:#ffbd2e}.dots i:nth-child(3){background:#28c840}
.shell{position:absolute;left:40px;right:40px;top:100px;font:32px/1.7 'IBM Plex Mono';white-space:pre-wrap;overflow-wrap:anywhere;color:#e7eef5}.prompt{color:#70e1c1}.caret{display:inline-block;width:18px;height:34px;background:#70e1c1;vertical-align:middle}
.cursor{position:absolute;left:0;top:0;width:36px;height:45px;z-index:90;transform-origin:3px 3px}.cursor svg{width:100%;height:100%}.ripple{position:absolute;left:0;top:0;width:62px;height:62px;border:3px solid #a9fce5;border-radius:50%;opacity:0;z-index:89;transform-origin:center}
.overlay{position:absolute;inset:0;pointer-events:none;z-index:100}.hint{position:absolute;left:160px;right:160px;bottom:32px;display:flex;justify-content:center;gap:18px;align-items:center}.hint span{font-size:29px;font-weight:700;background:#101722ed;border:1px solid #ffffff28;border-radius:13px;padding:13px 24px;box-shadow:0 8px 20px #0004}.hint b{color:#70e1c1}.tiny{font:24px 'IBM Plex Mono';color:#b5c3d4}.intro{position:absolute;left:220px;top:200px;font-size:115px;line-height:1.02;letter-spacing:-5px;font-weight:900;max-width:1450px}.intro b{color:#70e1c1}.shade{position:absolute;inset:0;background:#090b12d9}.punch{position:absolute;left:160px;right:160px;top:360px;font-size:130px;line-height:1.02;font-weight:900;letter-spacing:-6px;color:#fff}.punch b{color:#70e1c1}.brand{position:absolute;left:160px;top:245px;font-size:170px;font-weight:900;letter-spacing:-8px;color:#70e1c1}.tag{position:absolute;left:168px;top:485px;font-size:46px;line-height:1.45}.link{position:absolute;left:168px;top:730px;font:33px 'IBM Plex Mono';color:#70e1c1}
'''
STYLE += ".shell,.chrome,.link,.tiny{font-family:'IBM Plex Mono'}"

def timed_wrap(id,start,end,inside,kind='graphics'):
    return f'<div id="{id}" class="clip overlay" data-start="{start}" data-duration="{end-start}" data-track-index="2" data-track-kind="{kind}">{inside}</div>'

def hint(id,start,end,text):
    return timed_wrap(id,start,end,f'<div class="hint"><span>{text}</span></div>')

def write_project(kind,duration,frames,camera,cues,overlays,sounds,extra='',script=''):
    p=BASE/kind
    source=p/'compositions'/'motion.html'
    (p/'assets'/'recording').mkdir(parents=True,exist_ok=True)
    for f in {f['file'] for f in frames}:
        shutil.copy2(BASE/'recording'/f,p/'assets'/'recording'/f)
    for filename,origin in [('click.mp3',BASE/'setup-guide/.media/audio/sfx/sfx_001.mp3'),('typing.mp3',BASE/'setup-guide/.media/audio/sfx/sfx_002.mp3'),('whoosh.mp3',BASE/'launch/.media/audio/sfx/sfx_001.mp3')]:
        if origin.exists(): shutil.copy2(origin,p/'assets'/filename)
    images=[]
    for i,f in enumerate(frames):
        end=frames[i+1]['at'] if i+1<len(frames) else duration
        images.append(f'<img id="capture-{i}" class="clip image" src="assets/recording/{f["file"]}" data-start="{f["at"]}" data-duration="{round(end-f["at"],4)}" data-track-index="0" alt="Actual Breadcrumbs app: {html.escape(f["label"])}" />')
    pointer='<div id="pointer" class="cursor" data-layout-ignore><svg viewBox="0 0 30 38"><path d="M3 2 L3 30 L10 24 L16 36 L22 33 L16 21 L27 20 Z" fill="white" stroke="#111" stroke-width="2" stroke-linejoin="round"/></svg></div>'
    rings=''.join(f'<div id="ring-{i}" class="ripple" data-layout-ignore></div>' for i,c in enumerate(cues) if c.get('click'))
    moves=''
    for at,scale,x,y,ease,travel in camera:
        moves+=f"tl.to('#camera',{{scale:{scale},x:{x},y:{y},duration:{travel},ease:'{ease}'}},{at});\n"
    moves+="tl.set('#pointer',{x:1460,y:900},0);\n"
    for i,c in enumerate(cues):
        x=180+1560*c['x'];y=70+930*(.045+.955*c['y'])
        moves+=f"tl.to('#pointer',{{x:{x},y:{y},duration:.65,ease:'power3.inOut'}},{max(0,c['at']-.85)});\n"
        if c.get('click'):
            moves+=f"tl.to('#pointer',{{scale:.78,duration:.08,ease:'power2.out'}},{c['at']-.02});tl.to('#pointer',{{scale:1,duration:.17,ease:'power2.out'}},{c['at']+.06});\n"
            moves+=f"tl.fromTo('#ring-{i}',{{x:{x-31},y:{y-31},scale:.3,opacity:.8}},{{scale:1.65,opacity:0,duration:.48,immediateRender:false,ease:'power2.out'}},{c['at']});\n"
    markup=f'<div class="backdrop"></div><div id="camera" class="camera" data-layout-allow-overflow><div class="window" data-layout-allow-overlap>{extra}{"".join(images)}</div>{rings}{pointer}</div>{overlays}'
    source.write_text(f'''<template><style>{STYLE}</style><div id="root" data-composition-id="motion" data-width="1920" data-height="1080">{markup}</div><script>const tl=gsap.timeline({{paused:true}});{moves}{script}window.__timelines.motion=tl;</script></template>''',encoding='utf-8')
    audio=''
    for i,(at,name,length,gain) in enumerate(sounds):
        audio+=f'<audio id="sound-{i}" class="clip" src="assets/{name}.mp3" data-start="{at}" data-duration="{length}" data-volume="{gain}" data-track-index="{3 if name=="click" else 4 if name=="typing" else 5}"></audio>'
    (p/'index.html').write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>*{{margin:0;box-sizing:border-box}}html,body{{width:1920px;height:1080px;overflow:hidden;background:#172235}}.clip{{position:absolute;inset:0}}#root{{position:absolute;inset:0}}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="{duration}" data-fps="30" data-width="1920" data-height="1080"><div id="motion" class="clip" data-composition-id="motion" data-composition-src="compositions/motion.html" data-start="0" data-duration="{duration}" data-track-kind="graphics" data-track-index="0" data-width="1920" data-height="1080"></div>{audio}</div><script>window.__timelines=window.__timelines||{{}};window.__timelines.main=gsap.timeline({{paused:true}});</script></body></html>''',encoding='utf-8')
    # Remove only this generator's superseded slide scenes, within the project.
    for old in (p/'compositions').glob('*.html'):
        if old.name!='motion.html': old.unlink()

frames=recording['frames']
cues=recording['cues']
camera=[(0,1,0,0,'none',0),(1,1.1,20,100,'power3.inOut',1.2),
        (8,1,0,0,'power3.inOut',.9),(12,1.8,-490,330,'power3.inOut',1),
        (20.5,1.75,-440,250,'power3.inOut',1),(23,1,0,0,'power3.inOut',1),
        (24,1.7,700,-230,'power3.inOut',.9),(25.1,1.3,0,40,'power3.inOut',.8),
        (30,1.65,700,140,'power3.inOut',1),(34.5,1.8,760,-255,'power3.inOut',1),
        (40.5,1,0,0,'power3.inOut',1),(45.5,1.2,100,50,'power3.inOut',1),
        (49,1.8,-500,55,'power3.inOut',1),(54,1.9,-520,10,'power3.inOut',1.1),
        (59.5,1,0,0,'power3.inOut',1),(64,1.6,280,-110,'power3.inOut',.9),
        (66,1.18,0,0,'power3.inOut',1),(72,1.45,0,140,'power3.inOut',1),
        (79,1,0,0,'power3.inOut',1.1),(84,1.05,0,0,'power2.inOut',3)]
notes=[(0,8,'Windows · Python 3.11+ · Run this in PowerShell'),(8,12,'Launch with <b>breadcrumbs</b>'),
       (12,22,'<b>E</b> Write your intention · <b>Ctrl+B</b> Add a task'),
       (23,30,'Click Start · Choose a scope, or continue without tracking'),
       (30,35,'One intention. One focused block.'),(35,43,'Click to pause. Click again to resume.'),
       (44,49,'<b>B</b> Open your trail · demo observations'),
       (49,61,'Select another visit → the sidebar follows. No extra popup.'),
       (62,72,'<b>C</b> Config · themes, sounds, reading cards and more'),
       (73,80,'Browser connection · load the shown folder and pair locally'),
       (80,88,'Ready for your own session · github.com/SaroashDS/Breadcrumbs')]
overlays=''.join(hint(f'guide-note-{i}',a,b,t) for i,(a,b,t) in enumerate(notes))
command="irm https://raw.githubusercontent.com/SaroashDS/Breadcrumbs/main/bootstrap.ps1 | iex"
terminal=timed_wrap('install-terminal',0,10,'<div class="terminal"><div class="chrome"><div class="dots"><i></i><i></i><i></i></div>PowerShell</div><div class="shell"><span class="prompt">PS &gt; </span><span id="command"></span><span class="caret"></span><br><br><span id="launch-command"></span></div></div>')
terminal=terminal.replace('class="clip overlay"','class="clip"')
script=f'''const typing={{n:0}};tl.to(typing,{{n:{len(command)},duration:3.9,ease:'none',onUpdate:()=>{{document.getElementById('command').textContent={json.dumps(command)}.slice(0,Math.floor(typing.n));}}}},.8);tl.set('#launch-command',{{textContent:'PS > breadcrumbs'}},8);'''
sounds=[(c['at']+.033,'click',.4,.45) for c in cues if c.get('click')]
sounds += [(14.02,'typing',1.5,.18),(18.02,'typing',1.5,.18),(12,'whoosh',.6,.12),(45,'whoosh',.6,.12)]
write_project('setup-guide',88,frames,camera,cues,overlays,sounds,terminal,script)

# Launch: same real workflow, accelerated into a kinetic 28-second product film.
def frame_at(t): return max((f for f in frames if f['at']<=t),key=lambda f:f['at'])
launch_events=[(0,10),(2,14.5),(2.3,15),(2.6,15.5),(2.9,16),(3.2,17),(3.5,18.4),(3.8,19.2),(4.1,20),
               (5,25),(6.4,29),(8,32),(10,36),(11,39),(12,45),(14,49),(15,52),(16,55),(17,58),(19,62),(21,83)]
launch_frames=[dict(frame_at(t),at=at) for at,t in launch_events]
launch_camera=[(0,1.1,0,0,'none',0),(1.5,1.9,-500,330,'power4.inOut',.65),
               (4.6,1.8,720,-250,'power4.inOut',.55),(5.7,1.25,0,0,'power4.inOut',.55),
               (7,2.05,940,290,'power4.inOut',.7),(9,1.4,350,-100,'power3.inOut',.6),
               (11.5,1.1,0,0,'power4.inOut',.6),(13,1.7,420,40,'power3.inOut',.55),
               (14.5,2.1,-650,20,'power4.inOut',.7),(17,1.7,-430,0,'power3.inOut',.65),
               (18.5,1,0,0,'power4.inOut',.8),(21,0.92,0,0,'power3.inOut',.7),
               (23,1.2,0,0,'power3.inOut',4.5)]
launch_cues=[dict(at=5,x=.1,y=.645,click=True),dict(at=6.4,x=.5,y=.54,click=True),dict(at=10,x=.1,y=.645,click=True),dict(at=11,x=.1,y=.645,click=True),dict(at=15,x=.25,y=.4,click=False)]
launch_overlays=timed_wrap('launch-hook',0,1.8,'<div class="shade"></div><div class="intro">One thing<br>to <b>do.</b></div>')
launch_overlays+=hint('launch-plan',1.8,5,'Start with <b>one intention.</b>')
launch_overlays+=hint('launch-timer',5,9,'A timer that stays <b>simple.</b>')
launch_overlays+=hint('launch-control',9,12,'Pause. Breathe. Resume.')
launch_overlays+=hint('launch-trail',12,18.5,'See where you <b>trail off.</b>')
launch_overlays+=timed_wrap('launch-return',18.5,21,'<div class="shade"></div><div class="punch">Find your<br><b>way back.</b></div>')
launch_overlays+=timed_wrap('launch-mark',21,28,'<div class="shade"></div><div class="brand">Breadcrumbs</div><div class="tag">A terminal-first productivity timer.<br><span style="color:#aab4c8">No subscription. No AI service required.</span></div><div class="link">github.com/SaroashDS/Breadcrumbs</div>')
ls="tl.fromTo('#launch-hook .intro',{y:0,scale:1},{y:-15,scale:1.04,duration:1.7,ease:'power2.out'},0);tl.fromTo('#launch-return .punch',{x:100,opacity:0},{x:0,opacity:1,duration:.32,ease:'power4.out'},18.5);tl.fromTo('#launch-mark .brand',{y:70,opacity:0},{y:0,opacity:1,duration:.48,immediateRender:false,ease:'power4.out'},21);tl.fromTo('#launch-mark .tag',{y:30,opacity:0},{y:0,opacity:1,duration:.4,ease:'power3.out'},21.25);tl.fromTo('#launch-mark .link',{opacity:0},{opacity:1,duration:.3},21.6);"
launch_sounds=[(c['at']+.033,'click',.4,.4) for c in launch_cues if c.get('click')]+[(t+.033,'whoosh',.6,.25) for t in [1.8,7,12,18.5,21]]+[(2.05,'typing',1.5,.16)]
write_project('launch',28,launch_frames,launch_camera,launch_cues,launch_overlays,launch_sounds,script=ls)

for kind,length in [('launch',28),('setup-guide',88)]:
    p=BASE/kind
    (p/'SPEC.md').write_text(f'''# {kind} — revised motion treatment
User correction: continuous macOS / Screen Studio style, smooth zooms and click effects; launch must be snappy.
1920×1080, 30fps, {length}s. Actual pilot-driven app captures; isolated synthetic session and visit records. Same window throughout; no slide deck. Tutorial installation terminal is instructional text, not a claimed recording of a download. App begins at 10s.
Camera: 0.55–1.2s power3/power4 moves, 1–2.1× scales; cursor 0.65s travel, 80ms press, 480ms ring. Launch changes UI/camera on 1–3s beats. Sound: bundled offline click/typing/whoosh; no music provider signed in. Never synthesize a music substitute.
Palette: real Midnight app, blue/slate desktop framing, mint accents. Actual mac-style terminal chrome is part of the exported app capture. 29px guide callouts; 115–170px launch typography. Intentional app crop during zooms; all tutorial reading text remains in the lower overlay.
BANNED: slide cards, static title sequence tutorial, fabricated app UI, screenshot collage, generic diagram, guessed private tabs, fabricated install logs, popup activity details.
QA: check actual timeline samples, snapshots at key camera positions and clicks, 360px sheet, render/decode/ffprobe. Review sound levels numerically, not by listening.
''',encoding='utf-8')
print('Rebuilt: continuous 88s tutorial + 28s kinetic launch')
