"""Generate one WAV per script line in the cloned voice.  python gen_vo.py [--only 3,7] [--seed N]"""
import os, sys, json, time, argparse
os.environ.setdefault("HF_HOME", r"D:\VoiceClone\hf_cache")
import torch, torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

HERE = os.path.dirname(os.path.abspath(__file__))
EXAG = {"reel": 0.65, "clear": 0.45, "outro": 0.55, "calm": 0.45}
p = argparse.ArgumentParser(); p.add_argument("--only", default=""); p.add_argument("--seed", type=int, default=1)
a = p.parse_args()
only = {int(x) for x in a.only.split(",") if x}
d = json.load(open(os.path.join(HERE, "script.json"), encoding="utf-8"))
os.makedirs(os.path.join(HERE, "lines"), exist_ok=True)
m = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
n = 0
for sc in d["scenes"]:
    for roman, dev in sc["lines"]:
        n += 1
        if only and n not in only: continue
        torch.manual_seed(a.seed * 1000 + n)
        t = time.time()
        w = m.generate(dev, language_id="hi", audio_prompt_path=rf"D:\VoiceClone\refs\{sc['style']}.wav",
                       exaggeration=EXAG[sc["style"]], cfg_weight=0.5, temperature=0.75)
        ta.save(os.path.join(HERE, "lines", f"{n:02d}.wav"), w.cpu(), m.sr)
        print(f"{n:02d} {sc['id']:8s} {w.shape[-1] / m.sr:5.1f}s ({time.time() - t:.0f}s) {roman[:50]}", flush=True)
