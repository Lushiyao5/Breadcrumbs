"""Prepare the user's actual music and retrieved effects for both films."""
from pathlib import Path
import subprocess
import shutil

ROOT=Path(__file__).resolve().parents[1]
BIN=Path('C:/Users/User/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin')
FF=str(BIN/'ffmpeg.exe')
out=ROOT/'.build-check/audio';out.mkdir(parents=True,exist_ok=True)
source=Path('C:/Users/User/Downloads/monume-product-product-launch-603962.mp3')
# Enter on the full groove after the quiet 8-bar opening. 32 bars at 110 BPM.
music=out/'user-music.wav'
subprocess.run([FF,'-v','error','-y','-ss',str(16*60/110),'-i',str(source),'-t',str(128*60/110),
    '-af','loudnorm=I=-16:TP=-1:LRA=7','-ar','48000','-ac','2',str(music)],check=True)
sounds={'click':ROOT/'videos/setup-guide/assets/click.mp3',
        'whoosh':ROOT/'videos/launch/assets/whoosh.mp3',
        'typing':ROOT/'videos/launch/assets/typing.mp3',
        'impact':ROOT/'videos/launch/.media/audio/sfx/sfx_002.mp3',
        'pop':ROOT/'videos/launch/.media/audio/sfx/sfx_003.mp3'}
for name,path in sounds.items():
    subprocess.run([FF,'-v','error','-y','-i',str(path),'-af','loudnorm=I=-16:TP=-1:LRA=7','-ar','48000','-ac','2',str(out/f'{name}.wav')],check=True)
for kind in ('launch','setup-guide'):
    assets=ROOT/'videos'/kind/'assets'
    shutil.copy2(music,assets/'user-music.wav')
    for name in sounds:shutil.copy2(out/f'{name}.wav',assets/f'{name}.wav')
print('Prepared the supplied 110 BPM groove and five distinct effects')
