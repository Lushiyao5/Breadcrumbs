"""Music-led native-vector product films. Real UI, exact supplied artwork."""
from pathlib import Path
import json
import shutil
import html

BASE=Path(__file__).resolve().parent
CAP=BASE/'feature-recording'
BEAT=60/110
CSS='''
*{margin:0;box-sizing:border-box}#root{position:absolute;inset:0;overflow:hidden;background:#fffdf8;color:#102436;font-family:Inter}
.paper{position:absolute;inset:0;background:#fffdf8}.camera{position:absolute;inset:0;transform-origin:960px 540px}
.app{position:absolute;left:220px;top:40px;width:1480px;height:976px;border-radius:14px;overflow:hidden;box-shadow:0 24px 54px #10243628;background:#090b12}
.shot{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}.cursor{position:absolute;width:42px;height:50px;z-index:70;transform-origin:3px 3px}.cursor svg{width:100%;height:100%}.ring{position:absolute;left:0;top:0;width:66px;height:66px;border:3px solid #ffb21a;border-radius:50%;opacity:0;z-index:69}
.caption{position:absolute;left:160px;right:160px;bottom:15px;display:flex;justify-content:center;z-index:100;pointer-events:none}.caption span{font-size:32px;font-weight:700;line-height:1.3;background:#fffdf8;padding:12px 26px;border:1px solid #eadfc8;border-radius:11px;color:#102436}.caption b{color:#b86a00}
.word{position:absolute;left:160px;right:160px;top:385px;text-align:center;font-size:144px;line-height:1.08;font-weight:700;letter-spacing:-7px}.word b{color:#e69a00}.word.small{font-size:110px}.bar{position:absolute;left:620px;top:655px;width:680px;height:10px;background:#ffb21a;transform-origin:left}
.label{position:absolute;left:160px;top:150px;font-size:30px;letter-spacing:4px;text-transform:uppercase;color:#8b6830}
.brand-art{position:absolute;left:480px;top:55px;width:960px;height:700px;overflow:hidden}.brand-art img{position:absolute;width:1192px;height:1192px;left:-114px;top:-247px}
.cta{position:absolute;left:160px;right:160px;top:815px;text-align:center;font-size:42px;font-weight:700}.cta code{font-family:'IBM Plex Mono';background:#102436;color:#fff4dc;padding:14px 30px;border-radius:12px}.repo{position:absolute;left:160px;right:160px;top:934px;text-align:center;font-family:'IBM Plex Mono';font-size:28px;color:#102436}
.terminal{position:absolute;inset:0;background:#090b12;color:#edf2f7}.chrome{height:42px;background:#292929;color:#ddd;font:28px 'IBM Plex Mono';text-align:center}.shell{position:absolute;left:45px;right:45px;top:115px;font-family:'IBM Plex Mono';font-size:30px;line-height:1.7;white-space:pre-wrap;overflow-wrap:anywhere}.prompt{color:#70e1c1}.caret{display:inline-block;width:16px;height:30px;background:#ffb21a;vertical-align:middle}
.popup{position:absolute;left:585px;top:65px;width:750px;height:870px;object-fit:contain}.popup-wrap{position:absolute;inset:0;background:#fffdf8}
'''
CSS=CSS.replace('color:#e69a00','color:#ad7000')

def clip(id,start,end,content,track=0):
    return f'<div id="{id}" class="clip" data-start="{start:.4f}" data-duration="{end-start:.4f}" data-track-index="{track}">{content}</div>'

def caption(id,start,end,text):
    return clip(id,start,end,f'<div class="caption"><span>{text}</span></div>',2)

def prepare(kind):
    p=BASE/kind
    (p/'assets/screens').mkdir(parents=True,exist_ok=True)
    for source in CAP.glob('*.svg'):shutil.copy2(source,p/'assets/screens'/source.name)
    for source in CAP.glob('extension-*.png'):shutil.copy2(source,p/'assets/screens'/source.name)
    shutil.copy2(BASE.parent/'breadcrumbs/assets/branding/logo.png',p/'assets/logo.png')
    return p

def scene(p,id,duration,frames=(),poses=(),cues=(),notes=(),extra='',script='',background=True):
    images=[]
    for i,(at,name) in enumerate(frames):
        end=frames[i+1][0] if i+1<len(frames) else duration
        images.append(f'<img id="{id}-screen-{i}" class="clip shot" data-start="{at:.4f}" data-duration="{end-at:.4f}" data-track-index="0" src="assets/screens/{name}.svg" alt="Actual Breadcrumbs: {name}"/>')
    pointer=f'<div id="{id}-cursor" class="cursor" data-layout-ignore><svg viewBox="0 0 30 38"><path d="M3 2 L3 30 L10 24 L16 36 L22 33 L16 21 L27 20 Z" fill="white" stroke="#102436" stroke-width="2" stroke-linejoin="round"/></svg></div>'
    rings=''.join(f'<div id="{id}-ring-{i}" class="ring" data-layout-ignore></div>' for i,c in enumerate(cues) if c[3])
    moves=f"tl.set('#{id}-cursor',{{x:1460,y:900}},0);" if background else ''
    for at,z,fx,fy,travel in poses:
        moves+=f"tl.to('#{id}-camera',{{scale:{z},x:{(960-fx)*z},y:{(540-fy)*z},duration:{travel},ease:'power3.inOut'}},{at});"
    for i,(at,x,y,clicking) in enumerate(cues):
        moves+=f"tl.to('#{id}-cursor',{{x:{x},y:{y},duration:.38,ease:'power3.inOut'}},{max(0,at-.5)});"
        if clicking:
            moves+=f"tl.to('#{id}-cursor',{{scale:.77,duration:.07}},{at});tl.to('#{id}-cursor',{{scale:1,duration:.16}},{at+.07});tl.fromTo('#{id}-ring-{i}',{{x:{x-33},y:{y-33},opacity:.75,scale:.25}},{{opacity:0,scale:1.4,duration:.4,immediateRender:false,ease:'power2.out'}},{at});"
    overlays=''.join(caption(f'{id}-note-{i}',a,b,t) for i,(a,b,t) in enumerate(notes))
    body=f'<div class="paper"></div><div id="{id}-camera" class="camera" data-layout-allow-overflow><div class="app" data-layout-allow-overlap>{"".join(images)}</div>{rings}{pointer}</div>' if background else '<div class="paper"></div>'
    scene_css=CSS.replace('font-size:32px','font-size:42px' if p.name=='launch' else 'font-size:36px')
    (p/'compositions'/f'{id}.html').write_text(f'''<template><style>{scene_css}</style><div id="root" data-composition-id="{id}" data-width="1920" data-height="1080">{body}{overlays}{extra}</div><script>const tl=gsap.timeline({{paused:true}});{moves}{script}window.__timelines['{id}']=tl;</script></template>''',encoding='utf-8')

def project(p,duration,hosts,effects):
    source=''.join(f'<div id="{id}" class="clip" data-composition-id="{id}" data-composition-src="compositions/{id}.html" data-start="{start}" data-duration="{length}" data-width="1920" data-height="1080" data-track-kind="graphics" data-track-index="0"></div>' for id,start,length in hosts)
    audio='';bar32=128*BEAT;at=0;i=0
    while at<duration:
        length=min(bar32,duration-at)
        audio+=f'<audio id="music-{i}" class="clip" src="assets/user-music.wav" data-start="{at:.5f}" data-duration="{length:.5f}" data-volume="0.86" data-fade-in="0.012" data-fade-out="{1.1 if at+length>=duration else .012}" data-timeline-role="music" data-track-index="7"></audio>'
        at+=length;i+=1
    for i,(at,name,gain) in enumerate(effects):
        lengths={'click':.4,'typing':1.5,'whoosh':.6,'pop':.7,'impact':2.1}
        audio+=f'<audio id="effect-{i}" class="clip" src="assets/{name}.wav" data-start="{at:.4f}" data-duration="{min(lengths[name],duration-at):.4f}" data-volume="{gain}" data-track-index="{8+list(lengths).index(name)}"></audio>'
    (p/'index.html').write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>*{{margin:0;box-sizing:border-box}}html,body{{width:1920px;height:1080px;overflow:hidden;background:#fffdf8}}#root,.clip{{position:absolute;inset:0}}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="{duration}" data-fps="30" data-width="1920" data-height="1080">{source}{audio}</div><script>window.__timelines=window.__timelines||{{}};window.__timelines.main=gsap.timeline({{paused:true}});</script></body></html>''',encoding='utf-8')
    used={h[0]+'.html' for h in hosts}
    for path in (p/'compositions').glob('*.html'):
        if path.name not in used:path.unlink()

launch=prepare('launch')
hook=''
for i,(a,b,text) in enumerate([(0,BEAT*2,'One <b>goal.</b>'),(BEAT*2,BEAT*4,'One <b>timer.</b>'),(BEAT*4,BEAT*6,'Your <b>trail.</b>')]):
    hook+=clip(f'hook-word-{i}',a,b,f'<div class="word" id="hook-type-{i}">{text}</div>')
hook+='<div class="bar" id="hook-bar"></div>'
hs=''.join(f"tl.fromTo('#hook-type-{i}',{{y:38,opacity:{1 if i==0 else 0}}},{{y:0,opacity:1,duration:.24,ease:'power4.out'}},{i*BEAT*2});" for i in range(3))+"tl.fromTo('#hook-bar',{scaleX:.1},{scaleX:1,duration:3.2,ease:'power2.out'},0);"
scene(launch,'hook',6*BEAT,extra=hook,script=hs,background=False)
focuslen=10*BEAT
scene(launch,'focus',focuslen,[(0,'home'),(.4,'type-03'),(.65,'type-09'),(.9,'intention'),(1.3,'checklist'),(1.65,'checked'),(2.2,'start-choices'),(2.8,'running'),(4.4,'paused'),(4.9,'resumed')],
    [(0,1.15,960,540,0),(.15,1.75,1260,400,.5),(2,1.22,960,520,.45),(2.7,1.8,550,330,.5),(4,1.65,520,700,.38)],
    [(1.65,1300,360,False),(2.2,390,685,True),(2.8,960,565,True),(4.4,390,685,True),(4.9,390,685,True)],
    [(0,2.2,'Set your intention.'),(2.8,focuslen,'Start. Pause. Pick up where you left off.')])
traillen=24*BEAT
scene(launch,'trail',traillen,[(0,'branches'),(2*BEAT,'branch-docs'),(6*BEAT,'branch-supporting'),(10*BEAT,'branch-deviation'),(14*BEAT,'branch-annotated'),(18*BEAT,'branch-return'),(21*BEAT,'branch-terminal')],
    [(0,1.18,960,520,0),(.2,1.55,760,520,.45),(3*BEAT,1.8,1320,700,.5),(7*BEAT,1.55,760,540,.4),(11*BEAT,1.85,1320,710,.5),(16*BEAT,1.5,750,540,.45),(20*BEAT,1.25,960,530,.5)],
    [(2*BEAT,750,440,False),(6*BEAT,750,475,False),(10*BEAT,750,510,False),(14*BEAT,750,510,False),(18*BEAT,750,550,False)],
    [(0,5*BEAT,'See where your attention goes.'),(5*BEAT,10*BEAT,'Useful detours belong in the story.'),(10*BEAT,16*BEAT,'Notice the drift. Label the context.'),(16*BEAT,traillen,'Follow the branch back to your goal.')])
prooflen=12*BEAT
scene(launch,'proof',prooflen,[(0,'gameboy'),(2*BEAT,'sunset'),(4*BEAT,'midnight-companion'),(6*BEAT,'reading-card'),(8*BEAT,'reflection-written'),(10*BEAT,'history')],
    [(0,1.12,960,540,0),(.3,1.5,1250,720,.45),(3*BEAT,1.35,960,540,.4),(7*BEAT,1.35,960,550,.4),(10*BEAT,1.45,960,520,.4)],
    notes=[(0,6*BEAT,'Make it feel like yours.'),(6*BEAT,prooflen,'Reflect on the work. Keep the lesson.')])
scene(launch,'return',4*BEAT,extra='<div class="word small" id="return-copy">Find your<br><b>way back.</b></div>',script="tl.fromTo('#return-copy',{y:80,scale:.94},{y:0,scale:1,duration:.38,ease:'power4.out'},0);",background=False)
brandstart=56*BEAT
brand='<div class="brand-art" id="real-logo"><img src="assets/logo.png" alt="Supplied Breadcrumbs logo" /></div><div class="cta" id="brand-cta"><code>&gt; breadcrumbs</code></div><div class="repo" id="brand-repo">github.com/SaroashDS/Breadcrumbs</div>'
scene(launch,'brand',35-brandstart,extra=brand,script="tl.fromTo('#real-logo',{y:95,scale:.9,opacity:0},{y:0,scale:1,opacity:1,duration:.5,ease:'back.out(1.25)'},0);tl.fromTo('#brand-cta',{y:30,opacity:0},{y:0,opacity:1,duration:.3},.48);tl.fromTo('#brand-repo',{opacity:0},{opacity:1,duration:.3},.7);",background=False)
hosts=[('hook',0,6*BEAT),('focus',6*BEAT,10*BEAT),('trail',16*BEAT,24*BEAT),('proof',40*BEAT,12*BEAT),('return',52*BEAT,4*BEAT),('brand',56*BEAT,35-56*BEAT)]
effects=[(6*BEAT+.03,'whoosh',.5),(16*BEAT+.03,'whoosh',.6),(26*BEAT+.03,'pop',.4),(34*BEAT+.03,'pop',.4),(40*BEAT+.03,'whoosh',.45),(56*BEAT+.03,'impact',.5),
    (6*BEAT+2.23,'click',.55),(6*BEAT+2.83,'click',.55),(6*BEAT+4.43,'click',.55),(6*BEAT+4.93,'click',.55),(6*BEAT+.5,'typing',.3)]
project(launch,35,hosts,effects)

# Complete guide: one continuous terminal surface; every feature has a timed entry.
guide=prepare('setup-guide');DURATION=222
timeline=[(12,'tour'),(15,'tour-next'),(18,'home'),(19,'type-00'),(19.3,'type-03'),(19.6,'type-06'),(19.9,'type-09'),(20.2,'type-12'),(20.5,'type-15'),(20.8,'type-18'),(21.1,'intention'),(24,'checklist'),(27,'checked'),
    (30,'home'),(34,'presets'),(37,'extended'),(40,'custom'),(43,'focus-preset'),(46,'start-choices'),(50,'scope-apps'),(55,'scope-agents'),(60,'scope-pages'),(65,'scope-domains'),(70,'browser-pairing'),
    (89,'running'),(93,'paused'),(96,'resumed'),(100,'branches'),(103,'branch-docs'),(106,'branch-supporting'),(110,'branch-deviation'),(113,'branch-annotated'),(117,'branch-return'),(120,'branch-terminal'),(123,'branch-latest'),
    (127,'finish-decision'),(131,'reflection'),(135,'reflection-written'),(140,'history'),(145,'short-break-ready'),(148,'short-break-running'),(152,'break-in-trail'),(156,'long-break'),
    (160,'checkpoint'),(164,'recovery'),(167,'recovered-paused'),(171,'explicit-new-session'),(175,'gameboy'),(178,'sunset'),(181,'midnight-companion'),(184,'pet'),(186,'new-pet'),
    (189,'sound-settings'),(192,'sound-pack'),(195,'reading-settings'),(198,'reading-card'),(201,'automation-settings'),(204,'tour-replay')]
poses=[(0,1,960,540,0),(2,1.15,960,280,.6),(11,1,960,540,.6),(18,1.7,1260,405,.6),(29,1.5,1250,245,.5),(33,1.3,960,500,.5),(39,1.8,550,600,.5),(45,1.2,960,540,.5),
    (51,1.4,960,530,.5),(60,1.4,960,570,.5),(69,1.3,960,530,.5),(89,1.8,550,330,.6),(92,1.8,470,700,.5),(99,1.2,960,530,.5),(104,1.65,1310,690,.5),(109,1.55,750,520,.5),(115,1.65,1310,690,.5),(121,1.25,960,540,.5),
    (126,1.2,960,520,.5),(132,1.4,960,500,.5),(140,1.25,960,520,.5),(145,1.7,550,330,.5),(151,1.2,960,530,.5),(159,1.05,960,540,.5),(164,1.3,960,530,.5),(173,1,960,540,.5),(180,1.65,1260,690,.5),(188,1.3,960,540,.5),(194,1.25,960,540,.5),(198,1.7,1260,710,.5),(201,1.25,960,540,.5)]
notes=[(0,12,'Install on Windows · Python 3.11+ · use the command shown'),(12,18,'The first-run tour · arrows to browse · Escape to skip'),(18,24,'E: write an intention you can act on'),(24,30,'Ctrl+B: add a task · F2: check it off'),(30,34,'Keep or edit your session name'),(34,40,'P: choose 25/5, 50/10 or 60/10 rhythms'),(40,46,'Set custom minutes · 1/2/3 choose work or breaks'),(46,50,'Start with a scope, reuse one, or run untracked'),
    (50,55,'Choose planned apps · Space selects · Ctrl+S saves'),(55,60,'Select a live Codex or Claude terminal · verify active context'),(60,65,'Pair the browser to select an exact page'),(65,70,'Domain rules and optional titles · private tabs stay excluded'),(70,77,'Config → Browser connection · load unpacked and pair locally'),(77,83,'The extension finds your timer · Pause / Resume'),(83,89,'Sharing is separate · Finish requires confirmation'),
    (89,93,'Space or Start: begin your focus block'),(93,100,'Pause without ending · Resume when ready'),(100,106,'B: the branch trail shows visits and durations'),(106,113,'Supporting, deviation and unknown are different observations'),(113,117,'A / S / V: annotate the selected activity'),(117,123,'Return in scope · the sidebar follows your selection'),(123,127,'End / Latest returns to the newest visit'),(127,131,'Finish early, end the session, or keep working'),(131,140,'Write a reflection · optional 1–5 rating · Ctrl+S saves'),(140,145,'H: review intentions, elapsed time and reflections'),(145,152,'Take a short or long break in the same session'),(152,160,'Breaks appear in branches · capture stays off during breaks'),(160,164,'Q saves checkpoints · closed-app time is not counted'),(164,171,'Reopen and recover paused · breadcrumbs --resume NAME'),(171,175,'Ctrl+N explicitly starts a different session'),(175,181,'C: Midnight Arcade, Game Boy and Sunset Drive'),(181,189,'Optional companion · M to pet · N changes it'),(189,195,'Preview Arcade, Victory or Gentle completion sounds'),(195,201,'Optional Quotes / Qur’an · every block or breaks only'),(201,205,'Set card rotation, animation and automatic block starts'),(205,213,'Export locally · add --activity only when wanted'),(213,218,'Check updates · breadcrumbs update --check'),(218,222,'One intention. A simple timer. A trail back.')]
command='pipx install https://github.com/SaroashDS/Breadcrumbs/releases/download/v0.4.4/breadcrumbs-0.4.4-py3-none-any.whl'
terminal=clip('guide-install',0,12,'<div class="camera"><div class="app"><div class="terminal"><div class="chrome">PowerShell</div><div class="shell"><span class="prompt">PS &gt; </span><span id="install-command"></span><span class="caret"></span><br><br><span id="open-command"></span></div></div></div></div>')
script=f"const clock={{n:0}};tl.to(clock,{{n:{len(command)},duration:3.7,ease:'none',onUpdate:()=>document.getElementById('install-command').textContent={json.dumps(command)}.slice(0,Math.floor(clock.n))}},.5);tl.set('#open-command',{{textContent:'PS > breadcrumbs'}},8);"
popups=''
for i,(a,b,name) in enumerate([(77,80,'extension-running'),(80,83,'extension-paused'),(83,86,'extension-finish-confirm'),(86,89,'extension-next-block')]):
    popups+=clip(f'guide-popup-{i}',a,b,f'<div class="popup-wrap"><img class="popup" src="assets/screens/{name}.png" alt="Real paired extension controls"/></div>',1)
cli=json.loads((CAP/'cli.json').read_text())
exporttext='PS > breadcrumbs sessions\n'+cli['sessions']['output']+'\nPS > breadcrumbs export --output sessions.json\n'+cli['export']['output'].replace('<local-folder>\\','')+'\nPS > breadcrumbs export --activity --output activity.json\n'+cli['activity-export']['output'].replace('<local-folder>\\','')
terminal+=clip('guide-cli',205,218,'<div class="camera"><div class="app"><div class="terminal"><div class="chrome">PowerShell · local records</div><pre class="shell">'+html.escape(exporttext)+'\nPS > breadcrumbs update --check\n</pre></div></div></div>',1)
notes[0]=(0,12,'pipx + Python 3.11+ · Native app capture: Windows / Linux X11')
notes=[(a,b,'macOS / Wayland: timer + paired browser; native app capture unavailable' if a==89 else t) for a,b,t in notes]
notes=[(a,b,t.replace('Ctrl+N explicitly starts a different session','Ctrl+N: confirm when you want a different session')) for a,b,t in notes]
guidecues=[(46,390,685,True),(89,390,685,True),(93,390,685,True),(96,390,685,True),(103,700,440,False),(106,700,475,False),(110,700,510,False),(117,700,550,False),(127,960,640,False),(131,960,560,True)]
scene(guide,'walkthrough',DURATION,timeline,poses,cues=guidecues,notes=notes,extra=terminal+popups,script=script)
guidefx=[(.6,'typing',.28),(19.1,'typing',.28),(24.1,'typing',.28),(27.033,'pop',.45),(46.033,'click',.55),(77.033,'whoosh',.4),(80.033,'click',.55),(83.033,'click',.55),(89.033,'whoosh',.45),(93.033,'click',.55),(96.033,'click',.55),(100.033,'whoosh',.5),(113.033,'pop',.45),(127.033,'click',.55),(140.033,'whoosh',.4),(175.033,'pop',.4),(178.033,'pop',.4),(181.033,'pop',.4),(205.033,'whoosh',.4)]
project(guide,DURATION,[('walkthrough',0,DURATION)],guidefx)

coverage=['Windows install / Python requirement','first-run tour and replay','session name','intentions','checklist and checking tasks','presets','custom timer','focus / short / long breaks','start / reuse / untracked','planned apps','verified terminal agents','exact browser pages','domain rules','optional titles and privacy','load unpacked / pairing','extension active session / pause / resume','sharing independent of timer','confirmed remote finish / next block','local pause / resume','branches / durations / sidebar','supporting / deviation / unknown','A/S/V annotations','End / Latest','finish / end / keep decision','reflection / rating','history','same session across breaks','break capture exclusion','checkpoint / quit / recover','CLI sessions / resume','explicit new session','three visual themes','companion / pet / new pet','three sound packs / preview','Quotes / Qur’an / reading scope','card interval / animation','auto-start work / breaks','JSON export / optional activity','update check']
(BASE/'setup-guide/FEATURE_COVERAGE.md').write_text('# Complete feature guide\n\n222 seconds · 1920×1080 native vector captures · music throughout.\n\n'+'\n'.join(f'- [x] {x}' for x in coverage)+'\n\nNative foreground capture: Windows and Linux/X11. On macOS and Wayland, use the timer and paired browser; native app capture is unavailable.\n',encoding='utf-8')
for kind,duration in [('launch',35),('setup-guide',222)]:
    p=BASE/kind
    (p/'SPEC.md').write_text(f'''# Music-led {kind}
1920×1080 native, 30fps, {duration}s. Real Textual exports are SVG, preserving sharpness through 1–1.85× camera moves. No stretched PNG app capture. Source reference: 991 frames measured, 33.088s / 120 BPM, see ../REFERENCE_ANALYSIS.md.
User music: monume-product-product-launch-603962.mp3, enter at 8.727s, 110 BPM. 32-bar local groove segments, normalize final mix to −15 LUFS / −1 dBTP. Retrieved click, typing, whoosh, pop and one impact; no synthesized sounds. Logo is the untouched supplied PNG, framed with CSS.
Cream/navy/amber match the artwork. Inter 700/900; IBM Plex Mono commands. 160px title-safe horizontal margin, 32px guide overlays. Motion 0.38–0.6s, holds land on the beat. Launch: hook → timer → 13s branch proof → personalization/reflection → return → logo. Guide: one continuous terminal surface, 39 feature entries.
BANNED: silent music bed, muddy upscaled product PNG, fake dashboards, stock logos, paragraph slides, logo-only first frame, invented completion statistics, guessed browser context.
QA: all-frame reference metrics; check runtime/layout/contrast with nonzero samples; scene + phone + transition snapshots; native video probe; full decode; final music loudness / peak / clipping measurement.
''',encoding='utf-8')
print('Built 35s music-led launch and 222s complete feature guide')
