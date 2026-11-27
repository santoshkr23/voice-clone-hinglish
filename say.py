"""Generate speech in your cloned voice.

  .venv\\Scripts\\python say.py "आज मैं आपको बाली ले चलता हूँ।" -o output\\test.mp3
  .venv\\Scripts\\python say.py -f script.txt --style reel -o output\\reel1.mp3
Styles: calm, reel, question, excited, soft, clear (tech/education), english, outro.

Hindi works best written in Devanagari. English lines can stay in English (use --lang en for all-English text).
Long text is split by sentence (। . ? !) and joined with short pauses.
"""
import argparse, os, re, subprocess, sys, time
os.environ.setdefault("HF_HOME", os.path.join(os.path.dirname(os.path.abspath(__file__)), "hf_cache"))
import torch, torchaudio as ta

HERE = os.path.dirname(os.path.abspath(__file__))
p = argparse.ArgumentParser()
p.add_argument("text", nargs="?", help="text to speak")
p.add_argument("-f", "--file", help="UTF-8 text file to speak")
p.add_argument("-o", "--out", default=os.path.join(HERE, "output", "out.mp3"))
STYLES = {  # style -> default emotion (exaggeration)
    "calm": 0.45, "reel": 0.7, "question": 0.55, "excited": 0.8, "soft": 0.35,
    "clear": 0.4, "english": 0.5, "outro": 0.6}
p.add_argument("-s", "--style", default="calm", choices=sorted(STYLES),
               help="calm=travel story, reel=hooks, clear=tech/education, soft=emotional, english, ...")
p.add_argument("--ref", help="custom voice reference clip (5-15 s); overrides --style")
p.add_argument("--lang", default="hi")
p.add_argument("--exaggeration", type=float, help="emotion 0.25 (flat) .. 1.0 (very expressive); default per style")
p.add_argument("--cfg", type=float, default=0.5, help="lower (0.3) = slower, more deliberate pacing")
p.add_argument("--temp", type=float, default=0.8)
p.add_argument("--gap", type=float, default=0.35, help="pause between sentences, seconds")
p.add_argument("--seed", type=int, default=0)
p.add_argument("--cpu", action="store_true")
a = p.parse_args()
a.ref = a.ref or os.path.join(HERE, "refs", f"{a.style}.wav")
if a.exaggeration is None: a.exaggeration = STYLES[a.style]
if a.style == "english" and a.lang == "hi": a.lang = "en"

text = open(a.file, encoding="utf-8").read() if a.file else a.text
if not text: sys.exit("give text or -f file")
parts = [s.strip() for s in re.split(r"(?<=[।.?!])\s+|\n+", text) if s.strip()]

dev = "cuda" if torch.cuda.is_available() and not a.cpu else "cpu"
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
t0 = time.time()
model = ChatterboxMultilingualTTS.from_pretrained(device=dev)
print(f"model on {dev} ({time.time() - t0:.0f}s)", flush=True)
if a.seed: torch.manual_seed(a.seed)

chunks = []
for i, s in enumerate(parts, 1):
    t1 = time.time()
    w = model.generate(s, language_id=a.lang, audio_prompt_path=a.ref, exaggeration=a.exaggeration,
                       cfg_weight=a.cfg, temperature=a.temp)
    chunks += [w.cpu(), torch.zeros(1, int(model.sr * a.gap))]
    print(f"[{i}/{len(parts)}] {w.shape[-1] / model.sr:.1f}s audio in {time.time() - t1:.0f}s: {s[:60]}", flush=True)

wav = torch.cat(chunks[:-1], dim=-1)
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
tmp = os.path.splitext(a.out)[0] + "_raw.wav"
ta.save(tmp, wav, model.sr)
# match the VO polish: level to -16 LUFS, light de-ess, then encode
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                "highpass=f=70,deesser=i=0.3,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000",
                "-c:a", "libmp3lame", "-b:a", "192k", a.out], check=True)
os.remove(tmp)
print("saved", a.out)
