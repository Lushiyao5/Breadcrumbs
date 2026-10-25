"""Master the rendered music mix, verify streams, and make the README demo."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE=Path(__file__).resolve().parent
fallback=Path(os.environ.get('LOCALAPPDATA',''))/'Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin'
FF=shutil.which('ffmpeg') or str(fallback/'ffmpeg.exe')
PROBE=shutil.which('ffprobe') or str(fallback/'ffprobe.exe')
kind=sys.argv[1]
names={'launch':('breadcrumbs-launch-music-raw.mp4','breadcrumbs-launch-music.mp4',35),
       'setup-guide':('breadcrumbs-complete-guide-raw.mp4','breadcrumbs-complete-guide.mp4',222)}
raw,final,duration=names[kind];p=BASE/kind
source=p/'renders'/raw;dest=p/'renders'/final
subprocess.run([FF,'-v','error','-y','-i',str(source),'-map','0:v:0','-map','0:a:0','-c:v','copy',
    '-af','loudnorm=I=-15:TP=-1.5:LRA=7','-ar','48000','-c:a','aac','-b:a','256k','-movflags','+faststart',str(dest)],check=True)
probe=json.loads(subprocess.check_output([PROBE,'-v','error','-show_streams','-show_format','-of','json',str(dest)]))
video=next(s for s in probe['streams'] if s['codec_type']=='video')
assert (video['width'],video['height'])==(1920,1080)
assert video['r_frame_rate']=='30/1'
assert abs(float(probe['format']['duration'])-duration)<.1
assert any(s['codec_type']=='audio' for s in probe['streams'])
subprocess.run([FF,'-v','error','-i',str(dest),'-f','null','NUL' if os.name=='nt' else '/dev/null'],check=True)
measure=subprocess.run([FF,'-hide_banner','-i',str(dest),'-vn','-af','loudnorm=I=-15:TP=-1.5:LRA=7:print_format=json','-f','null','NUL' if os.name=='nt' else '/dev/null'],capture_output=True,text=True,check=True)
text=measure.stderr[measure.stderr.rfind('{'):];stats=json.JSONDecoder().raw_decode(text)[0]
assert -16.0<float(stats['input_i'])<-14.0,stats
assert float(stats['input_tp'])<=-1.0,stats
report=dict(file=final,width=1920,height=1080,fps=30,duration=duration,bytes=dest.stat().st_size,loudness=stats,decode='pass',auditory_review='not performed; measured only')
(p/'delivery-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if kind=='launch':
    gif=BASE.parent/'docs/assets/breadcrumbs-demo.gif'
    # The real intention/start/trail sequence, compressed to a 13s looping demo.
    subprocess.run([FF,'-v','error','-y','-ss','3.273','-i',str(dest),'-t','18.545','-an',
        '-filter_complex','[0:v]trim=duration=18.545,setpts=0.70*(PTS-STARTPTS),fps=12,scale=900:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3',
        '-loop','0',str(gif)],check=True)
print(json.dumps(report,indent=2))
