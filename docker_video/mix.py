"""Voice + Essential SFX + music -> final MP4.  python mix.py <plan>   (full | reel1 | reel2)
SFX rules (Editing Skool pack guide): whoosh on movement/transitions (panned with motion), riser drop exactly on the
reveal, hits only on big statements, foley where the action happens on screen, drone low under the hook."""
import os, sys, json, subprocess, numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = r"D:\VoiceClone\sfx\lib"
SR = 48000
INFO = json.load(open(os.path.join(LIB, "info.json")))
MUSIC = r"E:/PROJECT BC/Ai Video Editor/Brand Kit/ES_Informer - Wendel Scherer.mp3"

# (scene, line k, delay s, sfx, gain dB, align: peak|start, extra)
CUES = [
    ("hook", 1, 0.30, "l2r", -13, "peak", {}),                # arrow laptop -> server (moves left to right)
    ("hook", 1, 0.45, "glass", -11, "peak", {}),              # CRASH!
    ("hook", 2, 0.00, "riser3", -15, "peak", {}),             # riser drops exactly on the DOCKER title
    ("hook", 2, 0.02, "hit2", -9, "peak", {}),
    *[("hook", 3, i * 0.6, "mclick", -17, "peak", {}) for i in range(3)],
    ("what", 1, 1.00, "l2r", -15, "peak", {}),                # app flies into the container
    *[("what", 2, i * 0.45, "click", -19, "peak", {}) for i in range(4)],
    ("what", 3, 0.40, "swish", -16, "peak", {}),
    ("what", 4, 0.40, "swish", -18, "peak", {}),
    ("p1", 1, 0.00, "swish", -18, "peak", {}), ("p1", 2, 0.00, "swish", -18, "peak", {}),
    ("p1", 3, 0.05, "metal", -12, "peak", {}),                # server crash (shake)
    ("p1", 4, 0.00, "riser4", -16, "peak", {}),               # -> DOCKER KA SOLUTION
    *[("p1", 5, i * 0.5, "click", -19, "peak", {}) for i in range(3)],
    ("p1", 6, 0.05, "hit2", -10, "peak", {}),                 # "Ek baar banao, kahin bhi chalao"
    ("p2", 1, 0.30, "kbslow", -21, "start", {"len": 3.1}),    # checklist filling up
    ("p2", 2, 1.00, "hit2", -14, "peak", {}),                 # "2 din!"
    ("p2", 3, 0.10, "glass", -15, "peak", {}),                # versions clash (lightning)
    ("p2", 4, 0.00, "riser2", -17, "peak", {}),               # -> DOCKER KA SOLUTION
    *[("p2", 4, 0.3 + i * 0.4, "click", -19, "peak", {}) for i in range(3)],
    ("p2", 5, 0.15, "kbfast", -19, "start", {"len": 0.85}),   # typing "docker compose up"
    *[("p2", 5, 1.6 + i * 0.4, "mclick", -20, "peak", {}) for i in range(3)],
    ("p2", 6, 0.05, "hit2", -10, "peak", {}),                 # 2 din -> 5 min
    ("p3", 1, 0.00, "swish", -18, "peak", {}), ("p3", 3, 0.00, "swish", -18, "peak", {}),
    ("p3", 2, 0.00, "click", -19, "peak", {}), ("p3", 3, 1.20, "click", -19, "peak", {}), ("p3", 4, 0.00, "click", -19, "peak", {}),
    ("p3", 5, 1.60, "riser3", -15, "peak", {}),               # traffic spike
    ("p3", 5, 2.00, "hit1", -11, "peak", {}),                 # "10x traffic!"
    *[("p3", 6, 0.4 + i * 0.25, "click", -21, "peak", {}) for i in range(9)],  # containers multiply
    *[("concepts", 0, 0.5 + i * 0.5, "swish", -18, "peak", {}) for i in range(3)],
    ("concepts", 1, 0.00, "paper", -18, "start", {"len": 1.4}),
    ("concepts", 2, 0.00, "click", -18, "peak", {}),
    ("concepts", 3, 0.00, "notif", -17, "peak", {}),          # "Running"
    *[("concepts", 4, 0.4 + i * 0.4, "click", -19, "peak", {}) for i in range(3)],
    ("commands", 0, 0.80, "swish", -17, "peak", {}),
    ("commands", 1, 0.15, "kbfast", -19, "start", {"len": 1.05}), ("commands", 1, 1.60, "mclick", -19, "peak", {}),
    ("commands", 2, 0.15, "kbfast", -19, "start", {"len": 1.25}), ("commands", 2, 1.60, "notif", -17, "peak", {}),
    ("commands", 3, 0.15, "kbfast", -19, "start", {"len": 0.45}), ("commands", 3, 1.60, "mclick", -19, "peak", {}),
    ("recap", 0, 0.00, "hit2", -12, "peak", {}),
    *[("recap", 1, i * 0.8, "click", -18, "peak", {}) for i in range(3)],
    ("recap", 2, 0.05, "hit2", -11, "peak", {}),
    ("recap", 3, 0.00, "swish", -17, "peak", {}),
    *[("recap", 4, i * 0.5, "mclick", -17, "peak", {}) for i in range(3)],
    ("next1", 0, 0.00, "riser4", -16, "peak", {}),
    *[("next1", 0, 0.8 + i * 0.6, "click", -18, "peak", {}) for i in range(3)],
    ("next1", 0, 3.50, "hit2", -12, "peak", {}),
    ("intro2", 0, 0.00, "hit2", -10, "peak", {}),
    *[("intro2", 0, 1.0 + i * 0.7, "click", -18, "peak", {}) for i in range(3)],
    ("yt", 0, 0.00, "notif", -15, "peak", {}),
    ("yt", 0, 1.80, "swish", -16, "peak", {}),
    ("notes", 0, 0.00, "paper", -16, "start", {"len": 1.3}),
    ("notes", 0, 0.80, "kbfast", -19, "start", {"len": 1.0}),  # typing DOCKER
    ("notes", 0, 2.50, "msg", -14, "peak", {}),
]

_cache = {}
def sfx(name):
    if name not in _cache: _cache[name] = sf.read(os.path.join(LIB, name + ".wav"), dtype="float32")[0]
    return _cache[name]

def place(buf, x, t, gain_db, fade_out=0.08):
    i = int(t * SR); x = x * (10 ** (gain_db / 20))
    if fade_out and len(x) > int(fade_out * SR): x = x.copy(); n = int(fade_out * SR); x[-n:] *= np.linspace(1, 0, n)[:, None]
    if i < 0: x = x[-i:]; i = 0
    n = min(len(x), len(buf) - i)
    if n > 0: buf[i:i + n] += x[:n]

def main(plan):
    tl = json.load(open(os.path.join(HERE, f"timeline_{plan}.json")))
    T = tl["TOTAL"]; N = int(T * SR)
    sc = {s["id"]: s for s in tl["scenes"]}
    # voice
    vo = np.zeros(N, np.float32)
    for x in tl["T"]:
        a = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(HERE, "lines", f"{x['key']}.wav"), "-ar", str(SR), "-ac", "1",
                                          "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
        i = int(x["t"] * SR); vo[i:i + len(a)] += a[:N - i]
    sf.write(os.path.join(HERE, f"_vo_{plan}.wav"), vo, SR, subtype="FLOAT")
    # sfx
    fx = np.zeros((N, 2), np.float32); used = 0
    for k, s in enumerate(tl["scenes"][1:]):           # scene transitions: alternating whoosh, peak just after the cut
        place(fx, sfx("woosh1" if k % 2 == 0 else "woosh2"), s["t0"] + 0.05 - INFO["woosh1" if k % 2 == 0 else "woosh2"]["peak"], -17)
    for sid, k, delay, name, g, align, ex in CUES:
        if sid not in sc or k >= len(sc[sid]["starts"]): continue
        t = sc[sid]["starts"][k] + delay
        x = sfx(name)
        if "len" in ex: x = x[:int(ex["len"] * SR)]
        place(fx, x, t - (INFO[name]["peak"] if align == "peak" else 0), g); used += 1
    first = tl["scenes"][0]                              # drone: curiosity under the opening scene only
    dr = sfx("drone2")[:int((first["t1"] + 1.5) * SR)].copy()
    env = np.minimum(1, np.minimum(np.arange(len(dr)) / (1.0 * SR), (len(dr) - np.arange(len(dr))) / (1.5 * SR)))[:, None]
    place(fx, dr * env, 0, -27, 0)
    sf.write(os.path.join(HERE, f"_fx_{plan}.wav"), fx, SR, subtype="FLOAT")
    print(f"{plan}: {used} sfx cues + {len(tl['scenes']) - 1} transitions + drone")
    fc = (f"[0:a]highpass=f=70,deesser=i=0.3,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2dB,loudnorm=I=-16:TP=-1.5:LRA=7,"
          f"aresample={SR},asplit=3[vo][k1][k2];"
          f"[1:a]aresample={SR}[fx0];[fx0][k1]sidechaincompress=threshold=0.05:ratio=2.5:attack=10:release=250[fx];"
          f"[2:a]aresample={SR},aloop=loop=-1:size=2e9,atrim=0:{T:.2f},volume=-25dB,afade=t=in:d=2,afade=t=out:st={T - 3:.2f}:d=3[mu];"
          f"[mu][k2]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=500[mud];"
          f"[vo]pan=stereo|c0=c0|c1=c0[vos];[vos][fx][mud]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.89:level=disabled[m]")
    name = {"full": "Docker_in_5_Min_Hinglish_FULL.mp4", "reel1": "Docker_Reel_Part1.mp4", "reel2": "Docker_Reel_Part2.mp4"}[plan]
    out = os.path.join(HERE, name)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(HERE, f"_vo_{plan}.wav"), "-i", os.path.join(HERE, f"_fx_{plan}.wav"), "-i", MUSIC,
                    "-i", os.path.join(HERE, f"video_{plan}.mp4"), "-filter_complex", fc, "-map", "3:v", "-map", "[m]", "-dn", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    print("done", out)

if __name__ == "__main__":
    main(sys.argv[1])
