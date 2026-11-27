"""Animated Docker explainer, synced to lines/NN.wav.  python render.py [--preview SEC] [--only SCENE]
Timeline: 0.6 s lead, lines back to back with GAP, SCENE_GAP between scenes."""
import os, sys, json, math, subprocess, argparse
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 25
LEAD, GAP, SCENE_GAP, TAIL = 0.6, 0.30, 0.9, 2.0
F = "C:/Windows/Fonts/"
_fc = {}
def font(size, kind="b"):
    k = (size, kind)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(F + {"b": "segoeuib.ttf", "r": "segoeui.ttf", "m": "consola.ttf", "mb": "consolab.ttf",
                                         "h": "seguibl.ttf"}[kind], size)
    return _fc[k]

BG = (13, 20, 38); PANEL = (24, 34, 58); PANEL2 = (32, 45, 76); LINE = (60, 78, 118)
BLUE = (36, 150, 237); BLUE_D = (20, 98, 170); GREEN = (34, 197, 94); RED = (239, 68, 68)
YEL = (250, 204, 21); WHITE = (240, 244, 252); GREY = (148, 163, 184); ORANGE = (249, 115, 22); PURPLE = (168, 85, 247)

# ---------------------------------------------------------------- timeline
_script = json.load(open(os.path.join(HERE, "script.json"), encoding="utf-8"))
_extra = json.load(open(os.path.join(HERE, "extra.json"), encoding="utf-8"))
LINES, _n, SCENE_LINES = {}, 0, {}
for sc in _script["scenes"]:
    SCENE_LINES[sc["id"]] = []
    for roman, dev in sc["lines"]:
        _n += 1; k = f"{_n:02d}"; LINES[k] = roman; SCENE_LINES[sc["id"]].append(k)
for k, v in _extra.items(): LINES[k] = v["roman"]
# cuts: list of (scene_id, [line keys]); scene functions address lines by position k in that list
PLANS = {
    "full": [(s, SCENE_LINES[s]) for s in SCENE_LINES],
    "reel1": [("hook", SCENE_LINES["hook"]), ("what", SCENE_LINES["what"]), ("p1", SCENE_LINES["p1"]), ("p2", SCENE_LINES["p2"]),
              ("next1", ["x1"]), ("yt", ["x3"]), ("notes", ["45"])],
    "reel2": [("intro2", ["x2"]), ("p3", SCENE_LINES["p3"]), ("concepts", SCENE_LINES["concepts"]), ("commands", SCENE_LINES["commands"]),
              ("recap", SCENE_LINES["recap"][:4]), ("yt", ["x3"]), ("notes", ["45"])],
}
def line_dur(k):
    f = os.path.join(HERE, "lines", f"{k}.wav")
    return sf.info(f).duration if os.path.exists(f) else max(1.6, len(LINES[k].split()) / 2.4)

def build(plan_name):
    global d, T, TOTAL, PLAN
    PLAN = plan_name
    scenes, T, t = [], [], LEAD
    for sid, keys in PLANS[plan_name]:
        sc = {"id": sid, "t0": t, "starts": [], "keys": keys}
        for k in keys:
            dur = line_dur(k); sc["starts"].append(t)
            T.append({"key": k, "scene": sid, "t": t, "dur": dur, "text": LINES[k]}); t += dur + GAP
        t += SCENE_GAP - GAP; sc["t1"] = t; scenes.append(sc)
    d = {"scenes": scenes}; TOTAL = t + TAIL
build("full")

# ---------------------------------------------------------------- drawing helpers
def ease(p): p = min(1, max(0, p)); return 1 - (1 - p) ** 3

class Ctx:
    """Per-frame context. at(k) = seconds since line k of the scene started (negative = not yet)."""
    def __init__(self, img, sc, t):
        self.img, self.sc, self.t = img, sc, t
    def at(self, k, delay=0.0):
        if k >= len(self.sc["starts"]): return -999.0   # line not in this cut
        return self.t - self.sc["starts"][k] - delay
    def vis(self, k, delay=0.0, until=None, dur=0.45):
        """visibility 0..1 for an element that appears at line k (+delay) and optionally fades at line `until`."""
        a = ease(self.at(k, delay) / dur)
        if until is not None: a *= 1 - ease(self.at(until) / 0.35)
        return a

def layer(ctx, alpha, fn, dy=0):
    """draw fn(draw, dy) on a transparent layer and composite with alpha (slide up by (1-alpha)*24 px)."""
    if alpha <= 0.003: return
    off = int((1 - alpha) * 24) + dy
    if alpha >= 0.997:
        fn(ImageDraw.Draw(ctx.img), off); return
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fn(ImageDraw.Draw(L), off)
    if alpha < 1:
        a = L.getchannel("A").point(lambda v: int(v * alpha)); L.putalpha(a)
    ctx.img.alpha_composite(L)

def rr(dr, box, r, fill=None, outline=None, w=0): dr.rounded_rectangle(box, r, fill=fill, outline=outline, width=w)
def txt(dr, xy, s, size=40, col=WHITE, kind="b", anchor="mm"): dr.text(xy, s, font=font(size, kind), fill=col, anchor=anchor)

def badge(dr, cx, cy, s, col, size=34):
    f = font(size); tw = dr.textlength(s, font=f)
    rr(dr, (cx - tw / 2 - 26, cy - size * 0.85, cx + tw / 2 + 26, cy + size * 0.85), int(size * 0.85), fill=col)
    dr.text((cx, cy), s, font=f, fill=WHITE, anchor="mm")

def check(dr, cx, cy, r=34, col=GREEN):
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    dr.line([(cx - r * .45, cy + r * .02), (cx - r * .1, cy + r * .38), (cx + r * .5, cy - r * .35)], fill=WHITE, width=max(4, r // 5), joint="curve")

def cross(dr, cx, cy, r=34, col=RED):
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col); k = r * .42
    dr.line([(cx - k, cy - k), (cx + k, cy + k)], fill=WHITE, width=max(4, r // 5))
    dr.line([(cx - k, cy + k), (cx + k, cy - k)], fill=WHITE, width=max(4, r // 5))

def arrow(dr, x0, y0, x1, y1, col=GREY, w=8, head=22):
    dr.line([(x0, y0), (x1, y1)], fill=col, width=w)
    ang = math.atan2(y1 - y0, x1 - x0)
    pts = [(x1, y1), (x1 - head * math.cos(ang - .45), y1 - head * math.sin(ang - .45)),
           (x1 - head * math.cos(ang + .45), y1 - head * math.sin(ang + .45))]
    dr.polygon(pts, fill=col)

def laptop(dr, cx, cy, s=1.0, label=None, col=BLUE):
    w, h = 300 * s, 190 * s
    rr(dr, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), int(14 * s), fill=PANEL2, outline=col, w=int(6 * s))
    rr(dr, (cx - w / 2 + 16 * s, cy - h / 2 + 16 * s, cx + w / 2 - 16 * s, cy + h / 2 - 14 * s), int(6 * s), fill=(18, 28, 50))
    dr.polygon([(cx - w / 2 - 34 * s, cy + h / 2 + 30 * s), (cx + w / 2 + 34 * s, cy + h / 2 + 30 * s),
                (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)], fill=col)
    if label: txt(dr, (cx, cy + h / 2 + 62 * s), label, int(34 * s), WHITE)

def server(dr, cx, cy, s=1.0, label=None, col=GREY):
    w, h = 230 * s, 70 * s
    for i in range(3):
        y = cy - 1.5 * h + i * (h + 10 * s)
        rr(dr, (cx - w / 2, y, cx + w / 2, y + h), int(10 * s), fill=PANEL2, outline=col, w=int(5 * s))
        for j in range(3): dr.ellipse((cx - w / 2 + (22 + j * 24) * s, y + h / 2 - 7 * s, cx - w / 2 + (36 + j * 24) * s, y + h / 2 + 7 * s), fill=GREEN if j == 0 else LINE)
        dr.line([(cx + 10 * s, y + h / 2), (cx + w / 2 - 24 * s, y + h / 2)], fill=LINE, width=int(6 * s))
    if label: txt(dr, (cx, cy + 1.5 * h + 60 * s), label, int(34 * s), WHITE)

def container(dr, x0, y0, x1, y1, col=BLUE, label=None, size=34, ribs=True):
    rr(dr, (x0, y0, x1, y1), 12, fill=col)
    if ribs:
        step = 26
        for x in range(int(x0) + 18, int(x1) - 10, step): dr.line([(x, y0 + 12), (x, y1 - 12)], fill=tuple(int(c * .78) for c in col), width=6)
    rr(dr, (x0, y0, x1, y1), 12, outline=WHITE, w=4)
    if label:
        f = font(size); tw = dr.textlength(label, font=f)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rr(dr, (cx - tw / 2 - 14, cy - size * .75, cx + tw / 2 + 14, cy + size * .75), 10, fill=(10, 20, 40))
        dr.text((cx, cy), label, font=f, fill=WHITE, anchor="mm")

def chip(dr, cx, cy, s, col=PANEL2, tcol=WHITE, size=30, border=None):
    f = font(size); tw = dr.textlength(s, font=f)
    rr(dr, (cx - tw / 2 - 22, cy - size * .8, cx + tw / 2 + 22, cy + size * .8), 14, fill=col, outline=border, w=3 if border else 0)
    dr.text((cx, cy), s, font=f, fill=tcol, anchor="mm")

def header(dr, ctx, tag, tagcol, title):
    badge(dr, 960, 120, tag, tagcol, 30); txt(dr, (960, 205), title, 58, WHITE, "h")

def terminal(dr, x0, y0, x1, y1, title="Terminal"):
    rr(dr, (x0, y0, x1, y1), 18, fill=(8, 12, 22), outline=LINE, w=3)
    rr(dr, (x0, y0, x1, y0 + 56), 18, fill=PANEL2); dr.rectangle((x0, y0 + 36, x1, y0 + 56), fill=PANEL2)
    for i, c in enumerate([RED, YEL, GREEN]): dr.ellipse((x0 + 24 + i * 34, y0 + 18, x0 + 44 + i * 34, y0 + 38), fill=c)
    txt(dr, ((x0 + x1) / 2, y0 + 28), title, 26, GREY, "r")

def typed(ctx, k, s, delay=0.15, cps=22):
    n = int(max(0, ctx.at(k, delay)) * cps); return s[:n] + ("▌" if n < len(s) and int(ctx.t * 3) % 2 == 0 else "")

def truck(dr, cx, cy, col):
    rr(dr, (cx - 150, cy - 60, cx + 60, cy + 40), 8, fill=col, outline=WHITE, w=3)
    rr(dr, (cx + 66, cy - 30, cx + 140, cy + 40), 10, fill=GREY)
    for x in (cx - 110, cx + 20, cx + 108): dr.ellipse((x - 20, cy + 30, x + 20, cy + 70), fill=(30, 30, 30), outline=GREY, width=4)
def ship(dr, cx, cy, col):
    dr.polygon([(cx - 170, cy), (cx + 170, cy), (cx + 130, cy + 60), (cx - 130, cy + 60)], fill=(70, 90, 130))
    for i, c in enumerate([col, ORANGE, GREEN]): rr(dr, (cx - 130 + i * 88, cy - 56, cx - 50 + i * 88, cy - 4), 5, fill=c, outline=WHITE, w=2)
def train(dr, cx, cy, col):
    for i, c in enumerate([GREY, col, ORANGE]):
        x = cx - 170 + i * 115; rr(dr, (x, cy - 50, x + 105, cy + 30), 8, fill=c, outline=WHITE, w=3)
        for wx in (x + 25, x + 80): dr.ellipse((wx - 14, cy + 22, wx + 14, cy + 50), fill=(30, 30, 30))
    dr.line([(cx - 190, cy + 52), (cx + 190, cy + 52)], fill=GREY, width=4)

def person(dr, cx, cy, col=YEL):
    dr.ellipse((cx - 40, cy - 120, cx + 40, cy - 40), fill=col)
    dr.pieslice((cx - 80, cy - 30, cx + 80, cy + 130), 180, 360, fill=col)

# ---------------------------------------------------------------- scenes
def s_hook(c):
    dr = None
    layer(c, c.vis(0, until=2), lambda d, o: (laptop(d, 520, 470 + o, 1.25, "Developer ka laptop", BLUE), check(d, 690, 330 + o, 40),
                                              rr(d, (300, 160 + o, 900, 250 + o), 26, fill=WHITE), txt(d, (600, 205 + o), "\"Mere laptop pe toh chal raha tha!\"", 34, BG)))
    layer(c, c.vis(1, until=2), lambda d, o: (arrow(d, 780, 470, 1150, 470, GREY, 10, 30), server(d, 1400, 470 + o, 1.2, "Server", RED),
                                              cross(d, 1560, 330 + o, 44), txt(d, (1400, 210 + o), "CRASH!", 80, RED, "h")))
    def title(d, o):
        container(d, 560, 250 + o, 1360, 560 + o, BLUE)
        txt(d, (960, 405 + o), "DOCKER", 170, WHITE, "h")
        txt(d, (960, 640 + o), "5 minute mein, aasaan bhasha mein", 48, YEL)
    layer(c, c.vis(2, until=3), title)
    for i, (s, col) in enumerate([("1  \"Works on my machine\"", RED), ("2  Setup ka sir dard", ORANGE), ("3  Bhaari, slow VMs", PURPLE)]):
        layer(c, c.vis(3, i * 0.6), lambda d, o, s=s, col=col, i=i: (rr(d, (460, 250 + i * 170 + o, 1460, 380 + i * 170 + o), 30, fill=PANEL, outline=col, w=5),
                                                                    txt(d, (960, 315 + i * 170 + o), s, 56, WHITE)))
    layer(c, c.vis(3), lambda d, o: txt(d, (960, 160 + o), "Docker in 3 problems ko kaise solve karta hai?", 46, YEL))

def s_what(c):
    layer(c, c.vis(0), lambda d, o: txt(d, (960, 130 + o), "Docker kya hai?", 76, WHITE, "h"))
    p = ease(c.at(1, 0.6) / 1.0)  # app box flies into container
    layer(c, c.vis(1, until=3), lambda d, o: container(d, 700, 260 + o, 1220, 640 + o, BLUE, None))
    layer(c, c.vis(1, until=3) * (1 - ease(c.at(2) / 0.3)), lambda d, o: (
        rr(d, (300 + p * 560 - 100, 400 - 70, 300 + p * 560 + 100, 400 + 70), 20, fill=PURPLE, outline=WHITE, w=4),
        txt(d, (300 + p * 560, 400), "</> App", 40)))
    for i, s in enumerate(["Code", "Libraries", "Settings", "Runtime"]):
        x, y = 830 + (i % 2) * 260, 370 + (i // 2) * 150
        layer(c, c.vis(2, i * 0.45, until=3), lambda d, o, s=s, x=x, y=y: chip(d, x, y + o, s, (10, 20, 40), WHITE, 40))
    layer(c, c.vis(2, 2.0, until=3), lambda d, o: txt(d, (960, 720 + o), "Sab kuch ek saath, ek box mein", 46, YEL))
    for i, (s, col) in enumerate([("Python app", BLUE), ("Node app", GREEN), ("Java app", ORANGE)]):
        layer(c, c.vis(3, i * 0.4), lambda d, o, s=s, col=col, i=i: container(d, 250 + i * 500, 280 + o, 650 + i * 500, 480 + o, col, s, 36))
    layer(c, c.vis(3, 1.4), lambda d, o: txt(d, (960, 560 + o), "Andar kuch bhi ho, bahar se sab ek jaise", 46, YEL))
    for i, fn in enumerate([ship, truck, train]):
        layer(c, c.vis(4, i * 0.4), lambda d, o, fn=fn, i=i: (fn(d, 450 + i * 510, 740 + o, BLUE),
                                                              txt(d, (450 + i * 510, 850 + o), ["Jahaz", "Truck", "Train"][i], 36, GREY)))

def s_p1(c):
    layer(c, c.vis(0), lambda d, o: header(d, c, "PROBLEM 1", RED, "\"Mere machine pe toh chal raha tha!\""))
    def lap(d, o):
        rr(d, (220, 300 + o, 860, 760 + o), 30, fill=PANEL, outline=BLUE, w=4); laptop(d, 540, 440 + o, 0.9, None, BLUE)
        chip(d, 540, 620 + o, "Python 3.12", BLUE_D, size=34); chip(d, 540, 700 + o, "library v2", BLUE_D, size=34)
        txt(d, (540, 800 + o), "Aapka laptop", 38, WHITE); check(d, 820, 330 + o, 38)
    def srv(d, o):
        rr(d, (1060, 300 + o, 1700, 760 + o), 30, fill=PANEL, outline=GREY, w=4); server(d, 1380, 450 + o, 0.85)
        chip(d, 1380, 620 + o, "Python 3.8", (90, 60, 30), size=34); chip(d, 1380, 700 + o, "library v1", (90, 60, 30), size=34)
        txt(d, (1380, 800 + o), "Server", 38, WHITE)
    layer(c, c.vis(1, until=4), lap); layer(c, c.vis(2, until=4), srv)
    shake = int(math.sin(c.t * 60) * 8) if 0 < c.at(3) < 0.6 else 0
    layer(c, c.vis(3, until=4), lambda d, o: (cross(d, 1680 + shake, 330 + o, 44), rr(d, (1230 + shake, 400 + o, 1530 + shake, 500 + o), 20, fill=RED), txt(d, (1380 + shake, 450 + o), "CRASH!", 60, WHITE, "h"),
                                              rr(d, (560, 880 + o, 1360, 960 + o), 22, fill=(60, 20, 26)),
                                              txt(d, (960, 920 + o), "Code same, environment alag", 40, WHITE)))
    layer(c, c.vis(4), lambda d, o: badge(d, 960, 300 + o, "DOCKER KA SOLUTION", GREEN, 30))
    def box(d, o):
        container(d, 640, 360 + o, 1280, 560 + o, BLUE)
        for i, s in enumerate(["App", "Python 3.12", "library v2"]): chip(d, 760 + i * 200 if i else 735, 460 + o, s, (10, 20, 40), size=30)
    layer(c, c.vis(4, until=5), box)
    for i, s in enumerate(["Laptop", "Testing server", "Production"]):
        x = 400 + i * 560
        def tgt(d, o, x=x, s=s):
            rr(d, (x - 220, 380 + o, x + 220, 720 + o), 26, fill=PANEL, outline=LINE, w=3)
            container(d, x - 150, 430 + o, x + 150, 560 + o, BLUE, "Same container", 26)
            txt(d, (x, 640 + o), s, 38); check(d, x + 190, 400 + o, 32)
        layer(c, c.vis(5, i * 0.5), tgt)
    layer(c, c.vis(6), lambda d, o: (rr(d, (420, 800 + o, 1500, 920 + o), 40, fill=GREEN),
                                     txt(d, (960, 860 + o), "Ek baar banao, kahin bhi chalao", 54, WHITE, "h")))

def s_p2(c):
    layer(c, c.vis(0), lambda d, o: header(d, c, "PROBLEM 2", ORANGE, "Setup ka sir dard"))
    layer(c, c.vis(1, until=3), lambda d, o: (person(d, 380, 560 + o), txt(d, (380, 720 + o), "Naya developer", 38)))
    items = ["PostgreSQL", "Redis cache", "Node 18", "Python 3.11", "Env variables", "SSL certs", "Queue", "Nginx", "DB migrations", "...aur bhi"]
    def lst(d, o):
        rr(d, (620, 300 + o, 1220, 860 + o), 24, fill=PANEL, outline=LINE, w=3); txt(d, (920, 340 + o), "Install karo:", 36, GREY)
        k = int(min(len(items), max(0, c.at(1, 0.3)) * 3.2))
        for i, s in enumerate(items[:k]):
            y = 395 + i * 46 + o; d.rectangle((660, y - 14, 688, y + 14), outline=GREY, width=3); txt(d, (710, y), s, 32, WHITE, "r", "lm")
    layer(c, c.vis(1, until=3), lst)
    layer(c, c.vis(2, 1.0, until=3), lambda d, o: (d.ellipse((1330, 380 + o, 1590, 640 + o), outline=RED, width=10),
                                                  d.line([(1460, 510 + o), (1460, 420 + o)], fill=RED, width=10), d.line([(1460, 510 + o), (1530, 550 + o)], fill=RED, width=10),
                                                  txt(d, (1460, 700 + o), "2 din!", 64, RED, "h")))
    layer(c, c.vis(3, until=4), lambda d, o: (
        rr(d, (300, 340 + o, 860, 640 + o), 26, fill=PANEL, outline=BLUE, w=4), txt(d, (580, 420 + o), "Project A", 44), chip(d, 580, 530 + o, "Node 16", BLUE_D, size=38),
        rr(d, (1060, 340 + o, 1620, 640 + o), 26, fill=PANEL, outline=GREEN, w=4), txt(d, (1340, 420 + o), "Project B", 44), chip(d, 1340, 530 + o, "Node 20", (20, 110, 60), size=38),
        d.polygon([(960, 380 + o), (920, 500 + o), (965, 500 + o), (935, 610 + o), (1010, 470 + o), (962, 470 + o), (1000, 380 + o)], fill=YEL),
        rr(d, (300, 700 + o, 1620, 800 + o), 22, fill=(60, 20, 26)), txt(d, (960, 750 + o), "Ek hi machine pe versions takra gaye", 42, WHITE)))
    layer(c, c.vis(4), lambda d, o: badge(d, 960, 300 + o, "DOCKER KA SOLUTION", GREEN, 30))
    for i, (s, col) in enumerate([("App", BLUE), ("Database", PURPLE), ("Cache", ORANGE)]):
        layer(c, c.vis(4, 0.3 + i * 0.4), lambda d, o, s=s, col=col, i=i: (rr(d, (230 + i * 500 - 10, 370 + o, 690 + i * 500 + 10, 560 + o), 18, outline=WHITE, w=3),
                                                                           container(d, 240 + i * 500, 380 + o, 680 + i * 500, 550 + o, col, s, 38)))
    layer(c, c.vis(4, 1.6), lambda d, o: txt(d, (960, 610 + o), "Har service apne isolated container mein", 40, YEL))
    def term(d, o):
        terminal(d, 460, 640 + o, 1460, 900 + o, "docker-compose.yml")
        d.text((500, 712 + o), "$ " + typed(c, 5, "docker compose up"), font=font(40, "mb"), fill=GREEN)
        for i, s in enumerate(["Container app       Started", "Container database  Started", "Container cache     Started"]):
            if c.at(5, 1.6 + i * 0.4) > 0: d.text((500, 768 + i * 40 + o), "[+] " + s, font=font(32, "m"), fill=WHITE)
    layer(c, c.vis(5), term)
    layer(c, c.vis(6), lambda d, o: (rr(d, (1500, 640 + o, 1860, 900 + o), 26, fill=GREEN), txt(d, (1680, 710 + o), "2 din", 50, WHITE, "h"),
                                     d.line([(1590, 712 + o), (1770, 712 + o)], fill=RED, width=8), txt(d, (1680, 820 + o), "5 min", 72, WHITE, "h")))

def s_p3(c):
    layer(c, c.vis(0), lambda d, o: header(d, c, "PROBLEM 3", PURPLE, "Virtual machines: bhaari aur slow"))
    def vm(d, o):
        x0, x1 = 150, 900; txt(d, (525, 300 + o), "Virtual Machines", 42, WHITE)
        for i in range(3):
            x = x0 + i * 255
            rr(d, (x, 340 + o, x + 235, 600 + o), 14, fill=PANEL, outline=RED, w=3)
            chip(d, x + 117, 390 + o, "App", BLUE_D, size=28); rr(d, (x + 15, 440 + o, x + 220, 585 + o), 10, fill=(90, 35, 40))
            txt(d, (x + 117, 512 + o), "Poora OS", 30, WHITE)
        for j, s in enumerate(["Hypervisor", "Host OS", "Hardware"]): rr(d, (x0, 615 + j * 62 + o, x1 - 15, 667 + j * 62 + o), 10, fill=PANEL2); txt(d, (525, 641 + j * 62 + o), s, 28, GREY)
    def ct(d, o):
        x0 = 1020; txt(d, (1395, 300 + o), "Containers", 42, WHITE)
        for i in range(3):
            x = x0 + i * 255; container(d, x, 470 + o, x + 235, 600 + o, BLUE, "App", 28)
        for j, s in enumerate(["Docker Engine", "Host OS (shared kernel)", "Hardware"]):
            rr(d, (x0, 615 + j * 62 + o, x0 + 750, 667 + j * 62 + o), 10, fill=BLUE_D if j == 0 else PANEL2); txt(d, (1395, 641 + j * 62 + o), s, 28, WHITE if j == 0 else GREY)
    layer(c, c.vis(1, until=5), vm)
    layer(c, c.vis(2, until=5), lambda d, o: (chip(d, 330, 880 + o, "GBs memory", (90, 30, 34), RED, 36), chip(d, 720, 880 + o, "Minutes to start", (90, 30, 34), RED, 36)))
    layer(c, c.vis(3, until=5), ct)
    layer(c, c.vis(3, 1.2, until=5), lambda d, o: chip(d, 1200, 880 + o, "Sirf MBs", (16, 80, 45), GREEN, 36))
    layer(c, c.vis(4, until=5), lambda d, o: chip(d, 1590, 880 + o, "Seconds mein start", (16, 80, 45), GREEN, 36))
    def graph(d, o):
        gx0, gy0, gx1, gy1 = 200, 330, 900, 820
        rr(d, (gx0 - 40, gy0 - 40, gx1 + 40, gy1 + 60), 24, fill=PANEL); txt(d, (550, gy0), "Website traffic", 38, WHITE)
        d.line([(gx0, gy1), (gx1, gy1)], fill=GREY, width=3); d.line([(gx0, gy0 + 40), (gx0, gy1)], fill=GREY, width=3)
        p = ease(c.at(5, 0.2) / 2.0); pts = []
        for i in range(41):
            x = i / 40; y = 0.12 + 0.03 * math.sin(i) + (0.8 * ease((x - 0.6) / 0.25) if x > 0.6 else 0)
            if x <= p: pts.append((gx0 + x * (gx1 - gx0), gy1 - y * (gy1 - gy0 - 60)))
        if len(pts) > 1: d.line(pts, fill=RED, width=8, joint="curve")
        if p > 0.9: txt(d, (560, 420 + o), "10x traffic!", 64, RED, "h")
    layer(c, c.vis(5), graph)
    k = 1 + int(min(9, max(0, c.at(6, 0.4)) * 4))
    def grid(d, o):
        rr(d, (1000, 290, 1760, 900), 24, fill=PANEL); txt(d, (1380, 340 + o), f"{k} container{'s' if k > 1 else ''}", 44, GREEN if k == 10 else WHITE, "h")
        for i in range(k):
            x, y = 1050 + (i % 5) * 140, 420 + (i // 5) * 200
            container(d, x, y + o, x + 120, y + 150 + o, BLUE, None, ribs=True)
        if k == 10: txt(d, (1380, 850 + o), "Kuch hi seconds mein", 40, YEL)
    layer(c, c.vis(5), lambda d, o: None)
    layer(c, c.vis(6), grid)

def s_concepts(c):
    layer(c, c.vis(0), lambda d, o: txt(d, (960, 130 + o), "3 words yaad rakho", 70, WHITE, "h"))
    cur = max([i for i, k in enumerate((1, 2, 3)) if c.at(k) >= 0], default=-1) if c.at(4) < 0 else -1
    names = [("Dockerfile", "Recipe", ORANGE), ("Image", "Packed tiffin (read-only)", PURPLE), ("Container", "Chalta hua app", BLUE)]
    for i, (a, b, col) in enumerate(names):
        x = 340 + i * 620
        def box(d, o, x=x, a=a, b=b, col=col, i=i):
            sel = (i == cur)
            rr(d, (x - 230, 260 + o, x + 230, 470 + o), 26, fill=col if sel else PANEL, outline=col, w=6)
            txt(d, (x, 335 + o), a, 56, WHITE, "h"); txt(d, (x, 415 + o), b, 32, WHITE if sel else GREY)
            if i < 2: arrow(d, x + 245, 365 + o, x + 375, 365 + o, GREY, 8, 24)
        layer(c, c.vis(0, 0.5 + i * 0.5), box)
    def code(d, o):
        terminal(d, 260, 540 + o, 1060, 900 + o, "Dockerfile")
        for i, s in enumerate(["FROM python:3.12", "COPY . /app", "RUN pip install -r requirements.txt", "CMD [\"python\", \"app.py\"]"]):
            d.text((300, 620 + i * 62 + o), s, font=font(36, "m"), fill=[ORANGE, WHITE, WHITE, GREEN][i])
    layer(c, c.vis(1, until=2), code)
    layer(c, c.vis(2, until=4), lambda d, o: (rr(d, (560, 560 + o, 1360, 880 + o), 26, fill=PANEL, outline=PURPLE, w=4),
        rr(d, (820, 600 + o, 1100, 760 + o), 20, fill=PURPLE, outline=WHITE, w=4), txt(d, (960, 680 + o), "myapp:1.0", 40),
        txt(d, (960, 820 + o), "Ek baar bana, kabhi badalta nahi", 38, YEL)))
    layer(c, c.vis(4), lambda d, o: (rr(d, (820, 560 + o, 1100, 680 + o), 20, fill=PURPLE, outline=WHITE, w=4), txt(d, (960, 620 + o), "myapp:1.0", 40)))
    for i in range(3):
        layer(c, c.vis(4, 0.4 + i * 0.4), lambda d, o, i=i: (arrow(d, 960, 690, 560 + i * 400, 790, GREY, 6, 20),
                                                       container(d, 440 + i * 400, 800 + o, 680 + i * 400, 900 + o, BLUE, f"container {i + 1}", 28)))
    layer(c, c.vis(3, until=4), lambda d, o: (container(d, 1440, 600 + o, 1800, 780 + o, BLUE, "Running", 36),
                                              txt(d, (1620, 840 + o), "localhost:8080", 36, GREEN, "m")))

def s_commands(c):
    layer(c, c.vis(0), lambda d, o: txt(d, (960, 130 + o), "Sirf 2 commands", 76, WHITE, "h"))
    def term(d, o):
        terminal(d, 260, 230 + o, 1660, 900 + o, "Terminal")
        y = 320
        rows = [(1, "docker build -t myapp .", ["Successfully built image: myapp"]),
                (2, "docker run -p 8080:80 myapp", ["Container running on localhost:8080"]),
                (3, "docker ps", ["CONTAINER ID   IMAGE   STATUS        PORTS", "a1b2c3d4e5f6   myapp   Up 5 seconds  0.0.0.0:8080->80"])]
        for k, cmd, outs in rows:
            if c.at(k) < 0: break
            d.text((310, y + o), "$ " + typed(c, k, cmd), font=font(44, "mb"), fill=GREEN); y += 66
            for j, s in enumerate(outs):
                if c.at(k, 1.6 + j * 0.3) > 0: d.text((310, y + o), s, font=font(32, "m"), fill=WHITE if j or k < 3 else GREY)
                y += 50
            y += 30
    layer(c, c.vis(0, 0.8), term)
    for k, (s, col, x) in {1: ("IMAGE banti hai", PURPLE, 1450), 2: ("CONTAINER start", BLUE, 1450), 3: ("Running list", GREEN, 1450)}.items():
        layer(c, c.vis(k, 1.2, until=k + 1 if k < 3 else None), lambda d, o, s=s, col=col: badge(d, 1450, 180 + o, s, col, 32))

def s_recap(c):
    layer(c, c.vis(0), lambda d, o: txt(d, (960, 120 + o), "RECAP", 90, WHITE, "h"))
    rows = [("\"Works on my machine\"", "Same container, har jagah", RED), ("Setup ka sir dard", "docker compose up", ORANGE), ("Bhaari, slow VMs", "Halke, fast containers", PURPLE)]
    for i, (a, b, col) in enumerate(rows):
        y = 260 + i * 150
        layer(c, c.vis(1, i * 0.8, until=3), lambda d, o, a=a, b=b, col=col, y=y: (
            rr(d, (200, y + o, 860, y + 110 + o), 24, fill=PANEL, outline=col, w=4), txt(d, (530, y + 55 + o), a, 38),
            arrow(d, 890, y + 55 + o, 1010, y + 55 + o, GREY, 8, 22),
            rr(d, (1040, y + o, 1720, y + 110 + o), 24, fill=(16, 70, 42), outline=GREEN, w=4), txt(d, (1380, y + 55 + o), b, 38), check(d, 1720, y + o, 26)))
    layer(c, c.vis(2, until=3), lambda d, o: (rr(d, (420, 760 + o, 1500, 880 + o), 40, fill=BLUE), txt(d, (960, 820 + o), "Build once, run anywhere", 58, WHITE, "h")))
    layer(c, c.vis(3), lambda d, o: (rr(d, (460, 300 + o, 1460, 560 + o), 30, fill=PANEL, outline=BLUE, w=5), badge(d, 960, 300 + o, "NEXT VIDEO", BLUE, 30),
                                     txt(d, (960, 440 + o), "Apni pehli app Docker mein chalao", 52, WHITE, "h")))
    for i, (s, col) in enumerate([("LIKE", BLUE_D), ("SHARE", GREEN), ("SUBSCRIBE", RED)]):
        layer(c, c.vis(4, i * 0.5), lambda d, o, s=s, col=col, i=i: (rr(d, (300 + i * 470, 660 + o, 680 + i * 470, 780 + o), 60, fill=col), txt(d, (490 + i * 470, 720 + o), s, 52, WHITE, "h")))

def s_notes(c):
    def notes(d, o):
        # stacked notebook pages, slightly rotated look via offsets
        for i, col in enumerate([(200, 190, 160), (225, 215, 185), (250, 244, 225)]):
            rr(d, (300 + i * 18, 230 + i * 14 + o, 860 + i * 18, 860 + i * 14 + o), 18, fill=col, outline=(120, 110, 90), w=2)
        x0, y0 = 336, 258 + o
        for j in range(11): d.line([(x0 + 20, y0 + 120 + j * 44), (x0 + 520, y0 + 120 + j * 44)], fill=(170, 190, 220), width=2)
        d.line([(x0 + 70, y0 + 20), (x0 + 70, y0 + 590)], fill=(230, 120, 120), width=3)
        d.text((x0 + 95, y0 + 40), "Docker Notes", font=font(54, "h"), fill=(30, 50, 110))
        for j, s in enumerate(["Dockerfile = recipe", "Image = packed tiffin", "Container = running app", "docker build / run / ps", "docker compose up"]):
            d.text((x0 + 95, y0 + 140 + j * 88), s, font=font(36, "b"), fill=(40, 60, 120))
        badge(d, 800, 250 + o, "FREE", GREEN, 40)
    layer(c, c.vis(0), notes)
    def comment(d, o):
        rr(d, (1000, 330 + o, 1680, 600 + o), 26, fill=PANEL, outline=LINE, w=3)
        d.ellipse((1040, 370 + o, 1110, 440 + o), fill=BLUE); txt(d, (1075, 405 + o), "U", 34)
        txt(d, (1140, 405 + o), "Comment karo:", 34, GREY, "r", "lm")
        rr(d, (1040, 470 + o, 1640, 560 + o), 18, fill=(8, 12, 22), outline=BLUE, w=3)
        d.text((1070, 515 + o), typed(c, 0, "DOCKER", 0.8, 6), font=font(48, "mb"), fill=YEL, anchor="lm")
    layer(c, c.vis(0, 0.6), comment)
    layer(c, c.vis(0, 2.5), lambda d, o: (arrow(d, 1340, 630, 1340, 720, GREY, 8, 24),
                                          rr(d, (1040, 740 + o, 1640, 840 + o), 50, fill=GREEN),
                                          txt(d, (1340, 790 + o), "Notes aapke message mein!", 38, WHITE, "h")))

def s_next1(c):
    layer(c, c.vis(0), lambda d, o: (badge(d, 960, 230 + o, "COMING NEXT", BLUE, 34), txt(d, (960, 360 + o), "PART 2 mein", 110, WHITE, "h")))
    for i, (s, col) in enumerate([("Problem 3: Bhaari VMs", PURPLE), ("Dockerfile, Image, Container", ORANGE), ("Docker commands", GREEN)]):
        layer(c, c.vis(0, 0.8 + i * 0.6), lambda d, o, s=s, col=col, i=i: (rr(d, (510, 480 + i * 130 + o, 1410, 590 + i * 130 + o), 28, fill=PANEL, outline=col, w=5),
                                                                           txt(d, (960, 535 + i * 130 + o), s, 46)))
    layer(c, c.vis(0, 3.5), lambda d, o: (rr(d, (700, 880 + o, 1220, 960 + o), 40, fill=RED), txt(d, (960, 920 + o), "FOLLOW karo!", 44, WHITE, "h")))


def s_intro2(c):
    layer(c, c.vis(0), lambda d, o: (container(d, 640, 150 + o, 1280, 330 + o, BLUE), txt(d, (960, 240 + o), "PART 2", 110, WHITE, "h")))
    rows = [('1  "Works on my machine"', True), ("2  Setup ka sir dard", True), ("3  Bhaari, slow VMs", False)]
    for i, (s, done) in enumerate(rows):
        layer(c, c.vis(0, 1.0 + i * 0.7), lambda d, o, s=s, done=done, i=i: (
            rr(d, (460, 420 + i * 150 + o, 1460, 540 + i * 150 + o), 28, fill=PANEL if done else (70, 55, 10), outline=GREEN if done else YEL, w=5),
            txt(d, (920, 480 + i * 150 + o), s, 50),
            check(d, 1400, 480 + i * 150 + o, 30) if done else txt(d, (1395, 480 + i * 150 + o), "NOW", 36, YEL, "h")))


def s_yt(c):
    def card(d, o):
        rr(d, (460, 200 + o, 1460, 760 + o), 40, fill=PANEL, outline=RED, w=6)
        rr(d, (820, 270 + o, 1100, 460 + o), 50, fill=RED)
        d.polygon([(925, 315 + o), (925, 415 + o), (1010, 365 + o)], fill=WHITE)
        txt(d, (960, 540 + o), "Pura video YouTube pe", 64, WHITE, "h")
        txt(d, (960, 640 + o), "Docker in 5 Min · Full explainer", 40, GREY)
    layer(c, c.vis(0), card)
    bob = int(math.sin(c.t * 6) * 10)
    layer(c, c.vis(0, 1.8), lambda d, o: (arrow(d, 960, 960 + bob, 960, 830 + bob, YEL, 14, 44),
                                          rr(d, (700, 860 + o, 1220, 940 + o), 40, fill=YEL), txt(d, (960, 900 + o), "Link bio mein", 48, BG, "h")))


SCENES = {"notes": s_notes, "hook": s_hook, "what": s_what, "p1": s_p1, "p2": s_p2, "p3": s_p3, "concepts": s_concepts, "commands": s_commands,
          "recap": s_recap, "next1": s_next1, "intro2": s_intro2, "yt": s_yt}

# ---------------------------------------------------------------- frame
def cur_text(t):
    cur = [x for x in T if x["t"] - 0.05 <= t < x["t"] + x["dur"] + GAP]
    return cur[-1]["text"] if cur else None


def wrap(dr, s, f, maxw):
    lines, ln = [], ""
    for w_ in s.split():
        if dr.textlength(ln + " " + w_, font=f) > maxw and ln: lines.append(ln); ln = w_
        else: ln = (ln + " " + w_).strip()
    return lines + [ln]


def caption(dr, t):
    s = cur_text(t)
    if not s: return
    f = font(40, "b"); lines = wrap(dr, s, f, 1500)
    y0 = 1040 - len(lines) * 54
    for i, l in enumerate(lines):
        tw = dr.textlength(l, font=f)
        rr(dr, (960 - tw / 2 - 22, y0 + i * 54 - 6, 960 + tw / 2 + 22, y0 + i * 54 + 50), 12, fill=(6, 10, 20))
        dr.text((960, y0 + i * 54 + 22), l, font=f, fill=WHITE, anchor="mm")


def stage(t):
    img = Image.new("RGBA", (W, H), BG + (255,))
    dr = ImageDraw.Draw(img)
    for x in range(0, W, 80): dr.line([(x, 0), (x, H)], fill=(18, 27, 48))
    for y in range(0, H, 80): dr.line([(0, y), (W, y)], fill=(18, 27, 48))
    last = d["scenes"][-1]
    for sc in d["scenes"]:
        if sc["t0"] - 0.05 <= t < sc["t1"] or (sc is last and t >= sc["t0"]):
            c = Ctx(img, sc, t)
            fade = min(1, (t - sc["t0"] + 0.3) / 0.3, (sc["t1"] - t) / 0.35) if sc is not last else min(1, (t - sc["t0"] + 0.3) / 0.3)
            if fade < 1:
                L = Image.new("RGBA", (W, H), BG + (255,)); c.img = L; SCENES[sc["id"]](c)
                img = Image.blend(img, L, max(0, fade))
            else:
                SCENES[sc["id"]](c)
    return img


def frame(t):
    img = stage(t); dr = ImageDraw.Draw(img)
    dr.text((40, 36), "DOCKER in 5 MIN", font=font(28, "h"), fill=BLUE)
    dr.rectangle((0, H - 8, W * min(1, t / TOTAL), H), fill=BLUE)
    caption(dr, t)
    return img.convert("RGB")


VW, VH = 1080, 1920


def vframe(t, part):
    v = Image.new("RGB", (VW, VH), BG); dr = ImageDraw.Draw(v)
    for x in range(0, VW, 60): dr.line([(x, 0), (x, VH)], fill=(18, 27, 48))
    for y in range(0, VH, 60): dr.line([(0, y), (VW, y)], fill=(18, 27, 48))
    dr.text((540, 250), "DOCKER in 5 MIN", font=font(84, "h"), fill=WHITE, anchor="mm")
    badge(dr, 540, 370, f"PART {part} / 2", BLUE, 40)
    st = stage(t).convert("RGB").resize((1040, 585), Image.BILINEAR)
    rr(dr, (14, 456, 1066, 1053), 26, fill=LINE)
    m = Image.new("L", (1040, 585), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, 1039, 584), 22, fill=255)
    v.paste(st, (20, 462), m)
    dr.rectangle((20, 1070, 20 + 1040 * min(1, t / TOTAL), 1080), fill=BLUE)
    s = cur_text(t)
    if s:
        f = font(58, "b"); lines = wrap(dr, s, f, 940)[:5]
        y0 = 1150
        for i, l in enumerate(lines):
            tw = dr.textlength(l, font=f)
            rr(dr, (540 - tw / 2 - 20, y0 + i * 80 - 8, 540 + tw / 2 + 20, y0 + i * 80 + 66), 14, fill=(6, 10, 20))
            dr.text((540, y0 + i * 80 + 29), l, font=f, fill=WHITE, anchor="mm")
    return v


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--plan", default="full"); ap.add_argument("--preview", type=float, nargs="*")
    a = ap.parse_args(); build(a.plan)
    vert = a.plan != "full"; part = a.plan[-1] if vert else None
    fr = (lambda t: vframe(t, part)) if vert else frame
    if a.preview is not None:
        os.makedirs(os.path.join(HERE, "prev"), exist_ok=True)
        for s in a.preview: fr(s).save(os.path.join(HERE, "prev", f"{a.plan}_{s:06.1f}.jpg"), quality=85)
        sys.exit()
    out = os.path.join(HERE, f"video_{a.plan}.mp4"); w, h = (VW, VH) if vert else (W, H)
    print(f"{a.plan}: total {TOTAL:.1f}s, {int(TOTAL * FPS)} frames", flush=True)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-tune", "animation", out], stdin=subprocess.PIPE)
    for i in range(int(TOTAL * FPS)):
        ff.stdin.write(fr(i / FPS).tobytes())
        if i % 1000 == 0: print(f"frame {i}", flush=True)
    ff.stdin.close(); ff.wait()
    json.dump({"T": T, "TOTAL": TOTAL, "scenes": [{k: s[k] for k in ("id", "t0", "t1", "starts", "keys")} for s in d["scenes"]]},
              open(os.path.join(HERE, f"timeline_{a.plan}.json"), "w"), indent=1)
    print("done", out)
