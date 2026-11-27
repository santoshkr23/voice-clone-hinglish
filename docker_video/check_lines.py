"""Transcribe every generated line and score it against the script (needs GPU free)."""
import os, json, glob, difflib, re
os.add_dll_directory(r'D:\VoiceClone\.venv\Lib\site-packages\torch\lib')
os.environ['PATH'] = r'D:\VoiceClone\.venv\Lib\site-packages\torch\lib;' + os.environ['PATH']
import soundfile as sf, numpy as np, subprocess
from faster_whisper import WhisperModel
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, 'script.json'), encoding='utf-8'))
lines = [l for sc in d['scenes'] for l in sc['lines']]
m = WhisperModel('medium', device='cuda', compute_type='int8_float16')
norm = lambda s: re.sub(r'[^\w\s]', '', s).replace('़', '').replace('ं', '').replace('ँ', '').split()
res = []
for i, (roman, dev) in enumerate(lines, 1):
    f = os.path.join(HERE, 'lines', f'{i:02d}.wav')
    if not os.path.exists(f): continue
    a = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-ar', '16000', '-ac', '1', '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(a, np.float32)
    segs, _ = m.transcribe(x, language='hi', beam_size=5, vad_filter=False, condition_on_previous_text=False)
    got = ' '.join(s.text.strip() for s in segs)
    r = difflib.SequenceMatcher(None, ''.join(norm(dev)), ''.join(norm(got))).ratio()
    dur = len(x) / 16000; wps = len(roman.split()) / dur
    res.append({'n': i, 'ratio': round(r, 2), 'dur': round(dur, 1), 'wps': round(wps, 2), 'got': got})
    print(f"{i:02d} {r:.2f} {dur:5.1f}s {wps:.1f}w/s | {got}", flush=True)
json.dump(res, open(os.path.join(HERE, 'check.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
