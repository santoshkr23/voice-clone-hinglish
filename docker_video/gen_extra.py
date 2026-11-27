import os, json, sys
os.environ.setdefault("HF_HOME", r"D:\VoiceClone\hf_cache")
import torch, torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
HERE = os.path.dirname(os.path.abspath(__file__))
X = json.load(open(os.path.join(HERE, "extra.json"), encoding="utf-8"))
keys = sys.argv[1:] or list(X); seed = int(os.environ.get("SEED", "3"))
m = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
for k in keys:
    torch.manual_seed(seed)
    w = m.generate(X[k]["dev"], language_id="hi", audio_prompt_path=rf"D:\VoiceClone\refs\{X[k]['style']}.wav", exaggeration=0.65, cfg_weight=0.5, temperature=0.75)
    ta.save(os.path.join(HERE, "lines", f"{k}.wav"), w.cpu(), m.sr); print(k, round(w.shape[-1] / m.sr, 1), flush=True)
