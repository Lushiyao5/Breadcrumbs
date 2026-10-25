"""Measure every reference frame and its soundtrack; never touch source files."""
from pathlib import Path
import subprocess
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.build-check/reference-analysis'
OUT.mkdir(parents=True,exist_ok=True)
BIN=Path('C:/Users/User/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin')
FF=str(BIN/'ffmpeg.exe')
REF=Path('C:/Users/User/Downloads/Best-SaaS-Product-SnapYT.App.mp4')
MUSIC=Path('C:/Users/User/Downloads/monume-product-product-launch-603962.mp3')

probe=json.loads(subprocess.check_output([str(BIN/'ffprobe.exe'),'-v','error','-show_streams','-show_format','-of','json',str(REF)]))
video=next(s for s in probe['streams'] if s['codec_type']=='video')
w,h=video['width'],video['height']; fps=30
proc=subprocess.Popen([FF,'-v','error','-i',str(REF),'-an','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
metrics=[];previous=None;thumbs=[];idx=0
while True:
    raw=proc.stdout.read(w*h*3)
    if len(raw)!=w*h*3:break
    arr=np.frombuffer(raw,dtype=np.uint8).reshape(h,w,3)
    sample=arr[::6,::6].astype(np.float32)
    diff=0 if previous is None else float(np.abs(sample-previous).mean())
    metrics.append(dict(frame=idx,time=round(idx/fps,4),change=round(diff,4),luminance=round(float(sample.mean()),3),edge=round(float(np.abs(np.diff(sample,axis=1)).mean()),3)))
    previous=sample
    thumb=Image.fromarray(arr).resize((192,108))
    thumbs.append(thumb)
    if idx%30==0:Image.fromarray(arr).save(OUT/f'second-{idx//30:02d}.png')
    idx+=1
proc.wait()
for page,start in enumerate(range(0,len(thumbs),84)):
    sheet=Image.new('RGB',(192*12,132*7),'#171c24');draw=ImageDraw.Draw(sheet)
    for j,thumb in enumerate(thumbs[start:start+84]):
        x=j%12*192;y=j//12*132;sheet.paste(thumb,(x,y));draw.text((x+4,y+110),f'f{start+j:04d} {(start+j)/fps:.2f}s',fill='white')
    sheet.save(OUT/f'all-frames-{page+1:02d}.jpg',quality=92)
summary=Image.new('RGB',(640*4,390*9),'#171c24');draw=ImageDraw.Draw(summary)
for i,path in enumerate(sorted(OUT.glob('second-*.png'))):
    x=i%4*640;y=i//4*390;summary.paste(Image.open(path),(x,y));draw.text((x+8,y+365),path.stem,fill='white')
summary.save(OUT/'overview.jpg',quality=92)

def sound(path,name):
    wav=OUT/f'{name}.wav'
    subprocess.run([FF,'-v','error','-y','-i',str(path),'-vn','-ac','1','-ar','22050',str(wav)],check=True)
    raw=subprocess.check_output([FF,'-v','error','-i',str(wav),'-f','f32le','-'])
    samples=np.frombuffer(raw,dtype='<f4');hop=256;win=1024
    windows=np.lib.stride_tricks.sliding_window_view(samples,win)[::hop]
    spec=np.abs(np.fft.rfft(windows*np.hanning(win),axis=1))
    flux=np.maximum(0,np.diff(np.log1p(spec),axis=0)).mean(axis=1)
    env=flux-flux.mean();corr=np.correlate(env,env,mode='full')[len(env)-1:]
    laglo=int(60*22050/(170*hop));laghi=int(60*22050/(75*hop))
    lag=laglo+int(np.argmax(corr[laglo:laghi]));bpm=60*22050/(hop*lag)
    peaks=[]
    for i in np.argsort(flux)[::-1]:
        t=float(i*hop/22050)
        if all(abs(t-p['time'])>.15 for p in peaks):peaks.append(dict(time=round(t,3),strength=round(float(flux[i]),5)))
        if len(peaks)==120:break
    loud=subprocess.run([FF,'-hide_banner','-i',str(path),'-vn','-af','loudnorm=I=-16:TP=-1:LRA=11:print_format=json','-f','null','NUL'],capture_output=True,text=True)
    text=loud.stderr;text=text[text.rfind('{'):];loudness=json.JSONDecoder().raw_decode(text)[0] if text.startswith('{') else {}
    return dict(duration=round(len(samples)/22050,3),estimated_bpm=round(bpm,2),period=round(lag*hop/22050,5),onsets=sorted(peaks,key=lambda p:p['time']),loudness=loudness)

result=dict(reference=dict(frames=len(metrics),fps=fps,width=w,height=h,duration=probe['format']['duration'],strong_changes=sorted(metrics,key=lambda r:r['change'],reverse=True)[:60]),soundtrack=sound(REF,'reference-mixed-soundtrack'),music=sound(MUSIC,'provided-music'))
(OUT/'frame-metrics.json').write_text(json.dumps(metrics),encoding='utf-8')
(OUT/'analysis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:({a:b for a,b in v.items() if a not in ('strong_changes','onsets')} if isinstance(v,dict) else v) for k,v in result.items()},indent=2))
