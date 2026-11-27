"""Place each voice line at its timeline time, polish, add a ducked music bed, mux with the rendered video."""
import os, json, subprocess, numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
tl = json.load(open(os.path.join(HERE, 'timeline.json')))
N = int(tl['TOTAL'] * SR) + SR
vo = np.zeros(N, np.float32)
for x in tl['T']:
    a = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(HERE, 'lines', f"{x['n']:02d}.wav"), '-ar', str(SR), '-ac', '1', '-f', 'f32le', '-'], capture_output=True).stdout
    a = np.frombuffer(a, np.float32); i = int(x['t'] * SR); vo[i:i + len(a)] += a[:N - i]
sf.write(os.path.join(HERE, 'vo_raw.wav'), vo[:int(tl['TOTAL'] * SR)], SR, subtype='FLOAT')
MUSIC = r"E:/PROJECT BC/Ai Video Editor/Brand Kit/ES_Informer - Wendel Scherer.mp3"
T = tl['TOTAL']
fc = (f"[0:a]highpass=f=70,deesser=i=0.3,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2dB,loudnorm=I=-16:TP=-1.5:LRA=7,aresample={SR},asplit=2[vo][key];"
      f"[1:a]aresample={SR},aloop=loop=-1:size=2e9,atrim=0:{T:.2f},volume=-24dB,afade=t=in:d=2,afade=t=out:st={T-3:.2f}:d=3[mu];"
      f"[mu][key]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=500[mud];"
      f"[vo]pan=stereo|c0=c0|c1=c0[vos];[vos][mud]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89:level=disabled[m]")
out = os.path.join(HERE, 'Docker_in_5_Min_Hinglish.mp4')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(HERE, 'vo_raw.wav'), '-i', MUSIC, '-i', os.path.join(HERE, 'video_noaudio.mp4'),
                '-filter_complex', fc, '-map', '2:v', '-map', '[m]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], check=True)
print('done', out)
