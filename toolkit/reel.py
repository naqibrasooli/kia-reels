"""KIA Reel engine: renders a 1080x1920 animated Reel from a JSON content spec.

Usage:
    python3 reel.py <spec.json> <out.mp4>                 # full video with audio
    python3 reel.py <spec.json> <out_prefix> 3,8,20      # preview stills at given seconds

Rules baked in (KIA brand + Afghanistan context):
- Text, icons and animated objects only. Never photos or drawings of people or animals.
- Dari/Pashto main text (right-to-left), English subtitle under every scene.
- Brand orange from the KIA logo; logo on every scene and large on the final card.
- Original synthesized soft background music (no copyrighted audio) + light sound effects.

Spec format: see specs/*.json in this repo.
"""
import json
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cartoon  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
W, H, FPS = 1080, 1920, 30

ORANGE = (255, 83, 15)
ORANGE_D = (214, 62, 6)
ORANGE_L = (255, 232, 214)
CREAM = (255, 248, 241)
INK = (30, 30, 38)
GREY = (110, 110, 122)
WHITE = (255, 255, 255)
GREEN = (46, 160, 90)


def F(weight, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"Vazirmatn-{weight}.ttf"), size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def is_rtl(text):
    return any("؀" <= ch <= "ۿ" for ch in text)


# ---------------------------------------------------------------- drawing helpers
class Layer:
    def __init__(self, img, x, y, t_in, slide=40):
        self.img, self.t_in, self.slide = img, t_in, slide
        self.x, self.y = int(x - img.size[0] / 2), int(y)


def text_img(text, font, color, rtl=None, pad=6):
    rtl = is_rtl(text) if rtl is None else rtl
    d, lang = ("rtl", "fa") if rtl else ("ltr", "en")
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    l, t, r, b = probe.textbbox((0, 0), text, font=font, direction=d, language=lang)
    img = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((pad - l, pad - t), text, font=font, fill=color, direction=d, language=lang)
    return img


def fit_text(text, weight, size, color, max_w, rtl=None):
    while size > 20:
        img = text_img(text, F(weight, size), color, rtl)
        if img.size[0] <= max_w:
            return img
        size -= 4
    return img


def lines_img(lines, weight, size, color, gap=14, max_w=940):
    imgs = [fit_text(s, weight, size, color, max_w) for s in lines]
    w = max(i.size[0] for i in imgs)
    h = sum(i.size[1] for i in imgs) + gap * (len(imgs) - 1)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for i in imgs:
        out.alpha_composite(i, ((w - i.size[0]) // 2, y))
        y += i.size[1] + gap
    return out


def rounded(w, h, r, fill, shadow=True):
    pad = 30 if shadow else 0
    img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 8, pad + w, pad + h + 8), r, fill=(120, 60, 20, 45))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(img).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=fill)
    return img


def subtitle(lines):
    t = lines_img(lines, "SemiBold", 44, WHITE, gap=8, max_w=900)
    w, h = t.size[0] + 70, t.size[1] + 44
    box = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle((0, 0, w, h), 28, fill=(25, 25, 32, 225))
    box.alpha_composite(t, ((w - t.size[0]) // 2, (h - t.size[1]) // 2))
    return box


# ---------------------------------------------------------------- icons (objects only, white on orange)
def _canvas(s):
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def icon_shield(s=300):
    img, d = _canvas(s)
    d.polygon([(s*.5, s*.04), (s*.9, s*.18), (s*.86, s*.56), (s*.5, s*.96), (s*.14, s*.56), (s*.1, s*.18)], fill=ORANGE)
    d.polygon([(s*.5, s*.13), (s*.8, s*.24), (s*.77, s*.54), (s*.5, s*.86), (s*.23, s*.54), (s*.2, s*.24)], fill=ORANGE_D)
    d.line([(s*.33, s*.5), (s*.45, s*.63), (s*.69, s*.37)], fill=WHITE, width=int(s*.075), joint="curve")
    return img


def icon_bacteria(s=120):
    img, d = _canvas(s)
    d.ellipse((6, 6, s-6, s-6), outline=WHITE, width=8)
    for cx, cy, r in [(.38, .4, .07), (.62, .36, .05), (.55, .62, .08), (.33, .63, .045), (.7, .58, .04)]:
        d.ellipse((s*(cx-r), s*(cy-r), s*(cx+r), s*(cy+r)), fill=WHITE)
    return img


def icon_flask(s=120):
    img, d = _canvas(s)
    d.rectangle((s*.4, s*.08, s*.6, s*.4), fill=WHITE)
    d.polygon([(s*.4, s*.38), (s*.6, s*.38), (s*.88, s*.88), (s*.12, s*.88)], fill=WHITE)
    d.polygon([(s*.3, s*.6), (s*.7, s*.6), (s*.82, s*.82), (s*.18, s*.82)], fill=ORANGE_L)
    d.rectangle((s*.34, s*.05, s*.66, s*.12), fill=WHITE)
    return img


def icon_nut(s=120):
    img, d = _canvas(s)
    cx, cy, r = s/2, s/2, s*.4
    d.polygon([(cx + r*math.cos(math.radians(a)), cy + r*math.sin(math.radians(a))) for a in range(0, 360, 60)], fill=WHITE)
    d.ellipse((cx - r*.45, cy - r*.45, cx + r*.45, cy + r*.45), fill=ORANGE)
    return img


def icon_factory(s=120):
    img, d = _canvas(s)
    d.polygon([(s*.08, s*.9), (s*.08, s*.45), (s*.32, s*.6), (s*.32, s*.45), (s*.56, s*.6), (s*.56, s*.45),
               (s*.8, s*.6), (s*.8, s*.12), (s*.92, s*.12), (s*.92, s*.9)], fill=WHITE)
    for x in (.18, .42, .66):
        d.rectangle((s*x, s*.7, s*(x+.1), s*.8), fill=ORANGE)
    return img


def icon_box(s=120):
    img, d = _canvas(s)
    d.polygon([(s*.5, s*.1), (s*.9, s*.3), (s*.5, s*.5), (s*.1, s*.3)], fill=WHITE)
    d.polygon([(s*.1, s*.36), (s*.47, s*.55), (s*.47, s*.92), (s*.1, s*.72)], fill=WHITE)
    d.polygon([(s*.53, s*.55), (s*.9, s*.36), (s*.9, s*.72), (s*.53, s*.92)], fill=ORANGE_L)
    return img


def icon_globe(s=120):
    img, d = _canvas(s)
    d.ellipse((s*.1, s*.1, s*.9, s*.9), outline=WHITE, width=8)
    d.ellipse((s*.33, s*.1, s*.67, s*.9), outline=WHITE, width=6)
    d.line([(s*.1, s*.5), (s*.9, s*.5)], fill=WHITE, width=6)
    d.line([(s*.18, s*.3), (s*.82, s*.3)], fill=WHITE, width=5)
    d.line([(s*.18, s*.7), (s*.82, s*.7)], fill=WHITE, width=5)
    return img


def icon_doc(s=120):
    img, d = _canvas(s)
    d.rounded_rectangle((s*.2, s*.08, s*.8, s*.92), 10, fill=WHITE)
    for i, y in enumerate((.28, .44, .6)):
        d.rectangle((s*.32, s*y, s*(.68 if i < 2 else .55), s*(y+.06)), fill=ORANGE)
    d.ellipse((s*.55, s*.66, s*.75, s*.86), fill=ORANGE)
    return img


def icon_cart(s=120):
    img, d = _canvas(s)
    d.line([(s*.06, s*.18), (s*.2, s*.18), (s*.32, s*.66), (s*.82, s*.66)], fill=WHITE, width=8, joint="curve")
    d.polygon([(s*.24, s*.28), (s*.92, s*.28), (s*.82, s*.56), (s*.3, s*.56)], fill=WHITE)
    for x in (.38, .76):
        d.ellipse((s*(x-.07), s*.74, s*(x+.07), s*.88), fill=WHITE)
    return img


def icon_cap(s=120):
    img, d = _canvas(s)
    d.polygon([(s*.5, s*.18), (s*.95, s*.38), (s*.5, s*.58), (s*.05, s*.38)], fill=WHITE)
    d.polygon([(s*.25, s*.5), (s*.75, s*.5), (s*.75, s*.75), (s*.5, s*.85), (s*.25, s*.75)], fill=WHITE)
    d.line([(s*.85, s*.42), (s*.85, s*.72)], fill=WHITE, width=5)
    return img


def icon_pot(s=120):
    img, d = _canvas(s)
    d.rounded_rectangle((s*.14, s*.42, s*.86, s*.86), 14, fill=WHITE)
    d.rectangle((s*.04, s*.48, s*.16, s*.56), fill=WHITE)
    d.rectangle((s*.84, s*.48, s*.96, s*.56), fill=WHITE)
    d.rounded_rectangle((s*.1, s*.32, s*.9, s*.42), 6, fill=WHITE)
    d.rounded_rectangle((s*.42, s*.22, s*.58, s*.32), 4, fill=WHITE)
    for x in (.34, .5, .66):
        d.arc((s*(x-.05), s*.04, s*(x+.05), s*.2), 200, 340, fill=WHITE, width=5)
    return img


ICONS = {"pot": icon_pot, "bacteria": icon_bacteria, "flask": icon_flask, "nut": icon_nut, "factory": icon_factory,
         "box": icon_box, "globe": icon_globe, "doc": icon_doc, "cart": icon_cart, "cap": icon_cap,
         "shield": lambda s=120: icon_shield(s)}


def icon_check(s=70, color=ORANGE):
    img, d = _canvas(s)
    d.ellipse((0, 0, s, s), fill=color)
    d.line([(s*.27, s*.52), (s*.44, s*.68), (s*.74, s*.34)], fill=WHITE, width=int(s*.11), joint="curve")
    return img


def num_badge(n, s=72):
    img, d = _canvas(s)
    d.ellipse((0, 0, s, s), fill=ORANGE)
    t = text_img(n, F("Bold", 40), WHITE, rtl=True)
    img.alpha_composite(t, ((s - t.size[0]) // 2, (s - t.size[1]) // 2 - 2))
    return img


FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


def fa_num(i):
    return "".join(FA_DIGITS[int(c)] for c in str(i))


# ---------------------------------------------------------------- brand frame
LOGO = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA")


def logo_scaled(w):
    return LOGO.resize((w, round(LOGO.size[1] * w / LOGO.size[0])), Image.LANCZOS)


def base_frame():
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(img)
    d.ellipse((-260, -260, 420, 420), fill=(255, 236, 220))
    d.ellipse((760, 1500, 1400, 2140), fill=(255, 236, 220))
    logo = logo_scaled(280)
    img.alpha_composite(logo, ((W - logo.size[0]) // 2, 90))
    return img


# ---------------------------------------------------------------- scene builders
def build_scenes(spec):
    """Scenes come from spec["scenes"] (ordered list of {"type": ...}) or, for older specs,
    from the fixed keys hook, define, cards, hygiene, steps, benefits, cta."""
    scenes = []  # dicts: s, e, kind, layers, sub
    t = 0.0

    def add(kind, dur, layers_fn, sub):
        nonlocal t
        s, e = t, t + dur
        scenes.append({"s": s, "e": e, "kind": kind, "layers": layers_fn(s), "sub": subtitle(sub)})
        t = e

    def do_hook(h):
        add("hook", 4.2, lambda s: [
            Layer(fit_text(h["big"], "Black", 230, ORANGE, 960), W/2, 450, s + .1, slide=60),
            Layer(fit_text(h["line"], "Black", 150, INK, 960), W/2, 720, s + .5),
            Layer(rounded(560, 110, 55, ORANGE, shadow=False), W/2, 960, s + .9, slide=20),
            Layer(fit_text(h.get("pill", "در ۳۰ ثانیه"), "Bold", 64, WHITE, 500), W/2, 977, s + 1.0, slide=20),
        ], h["sub"])

    def do_define(d):
        add("define", d.get("dur", 5.0), lambda s: [
            (Layer(cartoon.art_factory(560), W/2, 270, s + .1) if d.get("art") == "factory"
             else Layer(icon_shield(300), W/2, 330, s + .1)),
            Layer(lines_img(d["title"], "Black", 96, INK, gap=10), W/2, 690, s + .4),
            Layer(lines_img(d["body"], "Medium", 56, GREY, gap=14), W/2, 950, s + 1.0),
        ], d["sub"])

    def do_cards(c):
        def cards_layers(s):
            L = [Layer(fit_text(c["title"], "Black", 92, INK, 960), W/2, 330, s + .1)]
            for i, (t1, t2, en, ic) in enumerate(c["items"][:3]):
                card = rounded(900, 230, 40, WHITE)
                cw = card.size[0]
                tile = Image.new("RGBA", (170, 170), (0, 0, 0, 0))
                ImageDraw.Draw(tile).rounded_rectangle((0, 0, 170, 170), 34, fill=ORANGE)
                tile.alpha_composite(ICONS.get(ic, icon_doc)(120), (25, 25))
                card.alpha_composite(tile, (cw - 60 - 170, 60))
                right = cw - 60 - 170 - 40
                a = fit_text(t1, "Black", 64, INK, 400)
                b = fit_text(t2, "Medium", 42, GREY, 400)
                e_ = fit_text(en, "SemiBold", 34, ORANGE, 190, rtl=False)
                card.alpha_composite(a, (right - a.size[0], 66))
                card.alpha_composite(b, (right - b.size[0], 66 + a.size[1]))
                card.alpha_composite(e_, (70, 145 - e_.size[1] // 2))
                L.append(Layer(card, W/2, 490 + i * 270, s + .6 + i * .45, slide=60))
            return L
        add("cards", c.get("dur", 6.0), cards_layers, c["sub"])

    def do_hygiene(hy):
        def hyg_layers(s):
            L = [Layer(fit_text(hy["title"], "Black", 84, INK, 980), W/2, 300, s + .1)]
            for i, (fa, en) in enumerate(hy["items"][:5]):
                row = Image.new("RGBA", (500, 128), (0, 0, 0, 0))
                ImageDraw.Draw(row).rounded_rectangle((0, 0, 500, 128), 34, fill=WHITE)
                row.alpha_composite(icon_check(64, GREEN), (500 - 22 - 64, 32))
                a = fit_text(fa, "Bold", 46, INK, 370)
                e_ = fit_text(en, "Medium", 28, GREY, 370, rtl=False)
                row.alpha_composite(a, (500 - 22 - 64 - 18 - a.size[0], 14))
                row.alpha_composite(e_, (500 - 22 - 64 - 18 - e_.size[0], 14 + a.size[1] - 4))
                L.append(Layer(row, 780, 470 + i * 150, s + .8 + i * .6, slide=40))
            return L
        add("hygiene", max(6.0, 2.4 + 0.65 * len(hy["items"])), hyg_layers, hy["sub"])

    def do_steps(st):
        n = len(st["items"])

        def steps_layers(s):
            L = [Layer(fit_text(st["title"], "Black", 92, INK, 960), W/2, 300, s + .1)]
            y0 = 440 + (7 - n) * 118 // 2
            for i, item in enumerate(st["items"]):
                fa, en = item[0], item[1]
                muted = len(item) > 2 and item[2]
                row = Image.new("RGBA", (900, 112), (0, 0, 0, 0))
                ImageDraw.Draw(row).rounded_rectangle((0, 4, 900, 108), 30, fill=(240, 236, 232) if muted else WHITE)
                badge = num_badge(fa_num(i + 1), 72)
                if muted:
                    badge = Image.merge("RGBA", (*badge.convert("LA").convert("RGB").split(), badge.getchannel("A")))
                row.alpha_composite(badge, (900 - 20 - 72, 20))
                a = fit_text(fa, "Bold", 46, GREY if muted else INK, 520)
                row.alpha_composite(a, (900 - 20 - 72 - 24 - a.size[0], 56 - a.size[1] // 2))
                e_ = fit_text(en, "Medium", 28, GREY, 180, rtl=False)
                row.alpha_composite(e_, (28, 56 - e_.size[1] // 2))
                L.append(Layer(row, W/2, y0 + i * 118, s + .5 + i * .55, slide=40))
            return L
        add("steps", max(5.5, 2.2 + 0.75 * n), steps_layers, st["sub"])

    def do_benefits(b):
        def ben_layers(s):
            L = [Layer(fit_text(b["title"], "Black", 100, INK, 960), W/2, 360, s + .1)]
            for i, bt in enumerate(b["items"][:3]):
                row = Image.new("RGBA", (900, 150), (0, 0, 0, 0))
                ImageDraw.Draw(row).rounded_rectangle((0, 0, 900, 150), 40, fill=ORANGE_L)
                row.alpha_composite(icon_check(84), (900 - 34 - 84, 33))
                a = fit_text(bt, "Bold", 56, INK, 700)
                row.alpha_composite(a, (900 - 34 - 84 - 30 - a.size[0], 75 - a.size[1] // 2))
                L.append(Layer(row, W/2, 600 + i * 190, s + .6 + i * .5, slide=50))
            return L
        add("benefits", b.get("dur", 5.0), ben_layers, b["sub"])

    def do_cta(ct):
        def cta_layers(s):
            card = rounded(900, 450, 44, WHITE)
            cw = card.size[0]
            big = logo_scaled(360)
            a = text_img("شرکت تحقیقاتی و انکشافی کیا", F("Black", 56), INK)
            c2 = text_img("+93 799 000 579  ·  kia-rd.com", F("Bold", 44), ORANGE, rtl=False)
            y = 58
            card.alpha_composite(big, ((cw - big.size[0]) // 2, y)); y += big.size[1] + 14
            card.alpha_composite(a, ((cw - a.size[0]) // 2, y)); y += a.size[1] + 10
            card.alpha_composite(c2, ((cw - c2.size[0]) // 2, y))
            return [Layer(lines_img(ct["title"], "Black", 104, INK, gap=6), W/2, 300, s + .1),
                    Layer(lines_img(ct["body"], "Medium", 60, GREY, gap=10), W/2, 590, s + .6),
                    Layer(card, W/2, 780, s + 1.2, slide=60)]
        add("cta", 5.8, cta_layers, ct["sub"])

    DO = {"hook": do_hook, "define": do_define, "cards": do_cards, "hygiene": do_hygiene,
          "steps": do_steps, "benefits": do_benefits, "cta": do_cta}
    if "scenes" in spec:
        for sc in spec["scenes"]:
            DO[sc["type"]](sc)
    else:
        for key in ("hook", "define", "cards", "hygiene", "steps", "benefits", "cta"):
            if key in spec:
                DO[key](spec[key])
    return scenes


# ---------------------------------------------------------------- animations
_rng = random.Random(7)
PARTS = [(_rng.uniform(0, W), _rng.uniform(0, H), _rng.uniform(5, 16), _rng.uniform(25, 60),
          _rng.uniform(0, 6.28), _rng.randint(25, 60)) for _ in range(22)]
SPEED, GAP, X0 = 150.0, 180, W + 60
CX = W // 2
BELT_Y = 1262


def draw_particles(ov, t):
    d = ImageDraw.Draw(ov)
    for (x, y, r, v, ph, a) in PARTS:
        yy = (y - v * t) % (H + 80) - 40
        xx = x + 18 * math.sin(t * 0.8 + ph)
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=ORANGE + (a,))


def draw_conveyor(ov, t, a, product="jar"):
    d = ImageDraw.Draw(ov)
    A = lambda c, k=1.0: c + (int(255 * a * k),)
    d.rounded_rectangle((60, BELT_Y, W - 60, BELT_Y + 14), 7, fill=A((70, 70, 80)))
    for i in range(14):
        rx = 80 + ((i * 70 - t * SPEED) % (W - 160))
        d.ellipse((rx - 5, BELT_Y + 2, rx + 5, BELT_Y + 12), fill=A((150, 150, 160)))
    for k in range(-2, 30):
        x = X0 + k * GAP - SPEED * t
        if x < 30 or x > W - 30:
            continue
        top = BELT_Y - 72
        if product == "box":
            d.rectangle((x - 34, top + 14, x + 34, BELT_Y), fill=A((222, 180, 130)))
            d.rectangle((x - 34, top + 14, x + 34, top + 24), fill=A((200, 155, 105)))
            d.rectangle((x - 6, top + 14, x + 6, BELT_Y), fill=A(ORANGE))
        else:
            d.rounded_rectangle((x - 28, top + 12, x + 28, BELT_Y), 10, fill=A(WHITE))
            d.rounded_rectangle((x - 28, top + 12, x + 28, BELT_Y), 10, outline=A((225, 205, 190)), width=3)
            d.rounded_rectangle((x - 22, top, x + 22, top + 16), 5, fill=A(ORANGE))
            d.rectangle((x - 28, top + 34, x + 28, top + 52), fill=A(ORANGE_L))
        if x < CX - 10:
            p = ease((CX - 10 - x) / 40)
            r, cy = 18 * p, top - 30
            d.ellipse((x - r, cy - r, x + r, cy + r), fill=A(GREEN, p))
            if p > .6:
                d.line([(x - 8, cy), (x - 2, cy + 7), (x + 9, cy - 6)], fill=A(WHITE), width=4, joint="curve")
    d.rectangle((CX - 52, BELT_Y - 108, CX - 42, BELT_Y), fill=A(ORANGE_D))
    d.rectangle((CX + 42, BELT_Y - 108, CX + 52, BELT_Y), fill=A(ORANGE_D))
    d.rounded_rectangle((CX - 60, BELT_Y - 120, CX + 60, BELT_Y - 100), 8, fill=A(ORANGE))
    beam = 0.35 + 0.25 * math.sin(t * 9)
    d.rectangle((CX - 40, BELT_Y - 100, CX + 40, BELT_Y), fill=ORANGE + (int(70 * beam * a),))


def draw_ring(ov, t, a, cx, cy, r=180):
    d = ImageDraw.Draw(ov)
    for i in range(28):
        ang = math.radians(i * (360 / 28) + t * 40)
        p1 = (cx + r * math.cos(ang - .07), cy + r * math.sin(ang - .07))
        p2 = (cx + r * math.cos(ang + .07), cy + r * math.sin(ang + .07))
        d.line([p1, p2], fill=ORANGE + (int(170 * a),), width=8)


def draw_growth(ov, tl, a):
    d = ImageDraw.Draw(ov)
    base, n, bw = 1282, 6, 70
    x0 = CX - (n * bw + (n - 1) * 26) // 2
    for i in range(n):
        h = (30 + i * 18) * ease((tl - 1.6 - i * 0.18) / 0.6)
        if h > 0:
            x = x0 + i * (bw + 26)
            d.rounded_rectangle((x, base - h, x + bw, base), 12, fill=(ORANGE if i == n - 1 else ORANGE_L) + (int(255 * a),))
    p = ease((tl - 3.0) / 0.6)
    if p > 0:
        xs, ys = x0 + 20, base - 50
        xe, ye = x0 + (n - 1) * (bw + 26) + bw, base - 125
        xm, ym = xs + (xe - xs) * p, ys + (ye - ys) * p
        d.line([(xs, ys), (xm, ym)], fill=INK + (int(220 * a),), width=7)
        d.polygon([(xm, ym - 20), (xm + 22, ym + 6), (xm - 6, ym + 18)], fill=INK + (int(220 * a),))


def scene_alpha(t, sc):
    s, e = sc["s"], sc["e"]
    if not (s - 0.01 <= t < e + 0.35):
        return 0.0
    return 1.0 if t < e else max(0.0, 1 - (t - e) / 0.35)


def alpha_mul(img, a):
    if a >= 1:
        return img
    r, g, b, al = img.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))


class Reel:
    def __init__(self, spec):
        self.spec = spec
        self.scenes = build_scenes(spec)
        self.total = self.scenes[-1]["e"]
        self.base = base_frame()
        self.product = spec.get("conveyor", "jar")

    def render(self, t):
        frame = self.base.copy()
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_particles(ov, t)
        sc = self.scenes
        k = {s["kind"]: s for s in sc}
        a = max(scene_alpha(t, k["hook"]), scene_alpha(t, k["define"]))
        if a > 0:
            draw_conveyor(ov, t, a * ease(t / 0.6), self.product)
        art = next((x.get("art") for x in self.spec.get("scenes", []) if x["type"] == "define"),
                   self.spec.get("define", {}).get("art"))
        if art != "factory":
            a = scene_alpha(t, k["define"]) * ease((t - k["define"]["s"] - .1) / .5)
            if a > 0:
                draw_ring(ov, t, a, CX, 480)
        if "hygiene" in k:
            a = scene_alpha(t, k["hygiene"]) * ease((t - k["hygiene"]["s"] - .2) / .5)
            if a > 0:
                ov.alpha_composite(alpha_mul(cartoon.worker_scene(t, 480), a), (24, 430 + int((1 - a) * 40)))
        a = scene_alpha(t, k["benefits"])
        if a > 0:
            draw_growth(ov, t - k["benefits"]["s"], a)
        frame.alpha_composite(ov)
        for s in sc:
            out_a = scene_alpha(t, s)
            if out_a <= 0:
                continue
            for ly in s["layers"]:
                p = ease((t - ly.t_in) / 0.45)
                if p > 0:
                    frame.alpha_composite(alpha_mul(ly.img, p * out_a), (ly.x, ly.y + int((1 - p) * ly.slide)))
            p = ease((t - s["s"] - 0.15) / 0.35) * out_a
            if p > 0:
                frame.alpha_composite(alpha_mul(s["sub"], p), ((W - s["sub"].size[0]) // 2, 1390))
        d = ImageDraw.Draw(frame)
        d.rounded_rectangle((80, 1300, W - 80, 1310), 5, fill=(240, 220, 205))
        x = int((W - 160) * min(1, t / self.total))
        d.rounded_rectangle((W - 80 - x, 1300, W - 80, 1310), 5, fill=ORANGE)
        return frame.convert("RGB")

    # ------------------------------------------------------------ audio
    def build_audio(self, path, sr=44100):
        n = int(self.total * sr) + sr
        sfx = np.zeros(n)
        rng = np.random.default_rng(3)

        def add(buf, sig, t, vol):
            i = int(t * sr)
            j = min(n, i + len(sig))
            if 0 <= i < n:
                buf[i:j] += vol * sig[: j - i]

        tt = lambda dur: np.arange(int(dur * sr)) / sr

        def pop():
            x = tt(.09)
            return np.sin(2 * np.pi * np.cumsum(950 - 4000 * x) / sr) * np.exp(-x * 45)

        def whoosh(dur=.55):
            m = int(dur * sr)
            k = np.linspace(0, 1, m)
            spec_ = np.fft.rfft(rng.standard_normal(m))
            f = np.fft.rfftfreq(m, 1 / sr)
            y = np.fft.irfft(spec_ * np.exp(-f / 1800), m)
            return y / (np.abs(y).max() + 1e-9) * np.sin(np.pi * k) ** 2

        def tick():
            x = tt(.03)
            return np.sin(2 * np.pi * 2300 * x) * np.exp(-x * 160)

        def ding(fq):
            x = tt(1.4)
            return (np.sin(2 * np.pi * fq * x) + .35 * np.sin(2 * np.pi * 2.01 * fq * x)) * np.exp(-x * 3.2)

        for i, s in enumerate(self.scenes):
            if i:
                add(sfx, whoosh(), s["s"] - .25, .26)
            for ly in s["layers"]:
                add(sfx, pop(), ly.t_in + .05, .16)
        e2 = self.scenes[1]["e"]
        for k in range(-2, 30):
            tc = (X0 + k * GAP - CX) / SPEED
            if 0.4 < tc < e2:
                add(sfx, tick(), tc, .07)
        s6 = self.scenes[-1]["s"]
        add(sfx, ding(784), s6 + 1.25, .14)
        add(sfx, ding(1046), s6 + 1.40, .10)

        out = sfx
        if self.spec.get("music", True):
            out = out + 0.55 * soft_music(n, sr, seed=self.spec.get("music_seed", 1))
        out = out / max(1.0, np.abs(out).max() / 0.85)
        pcm = (out * 32767).astype(np.int16)
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())


def soft_music(n, sr, seed=1):
    """Original, calm background music: warm pad + gentle piano-like arpeggio + soft bass.
    Chord loop vi-IV-I-V (Am-F-C-G) at 76 BPM. Fully synthesized, no samples."""
    rng = np.random.default_rng(seed)
    bpm = 76
    beat = 60 / bpm
    bar = 4 * beat
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)
    progs = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
    shift = [0, 2, -3, 5][seed % 4]
    out = np.zeros(n)
    t_all = np.arange(n) / sr

    def env(m, a, r):
        e = np.ones(m)
        ai, ri = min(int(a * sr), m // 2), min(int(r * sr), m // 2)
        e[:ai] = np.linspace(0, 1, ai)
        if ri:
            e[-ri:] *= np.linspace(1, 0, ri)
        return e

    nbars = int(n / sr / bar) + 1
    for b in range(nbars):
        chord = [m + shift for m in progs[b % 4]]
        i0 = int(b * bar * sr)
        m = min(int(bar * 1.15 * sr), n - i0)
        if m <= 0:
            break
        x = np.arange(m) / sr
        pad = np.zeros(m)
        for k, note in enumerate(chord):
            f = midi(note)
            for det in (-0.12, 0.12):
                pad += np.sin(2 * np.pi * f * (1 + det / 100) * x + k) * 0.5
            pad += 0.25 * np.sin(2 * np.pi * f * 2 * x)
        pad *= env(m, 0.9, 0.9) * 0.05
        bass = np.sin(2 * np.pi * midi(chord[0] - 12) * x) * env(m, 0.05, 0.6) * np.exp(-x * 0.6) * 0.10
        out[i0:i0 + m] += pad + bass
        # arpeggio: 8 eighth notes per bar
        arp = [chord[0] + 12, chord[1] + 12, chord[2] + 12, chord[1] + 12] * 2
        for j, note in enumerate(arp):
            st = i0 + int(j * beat / 2 * sr)
            L = min(int(1.6 * sr), n - st)
            if L <= 0:
                continue
            x2 = np.arange(L) / sr
            f = midi(note)
            tone = (np.sin(2 * np.pi * f * x2) + 0.3 * np.sin(2 * np.pi * 2 * f * x2) + 0.1 * np.sin(2 * np.pi * 3 * f * x2))
            vel = 0.045 * (1.0 if j % 4 == 0 else 0.7) * rng.uniform(0.85, 1.0)
            out[st:st + L] += tone * np.exp(-x2 * 3.2) * np.minimum(1, x2 * 200) * vel
    # gentle fade in/out
    fade = np.minimum(1, t_all / 1.5) * np.minimum(1, (t_all[-1] - t_all) / 2.5)
    out *= fade
    # soft low-pass for warmth
    spec_ = np.fft.rfft(out)
    f = np.fft.rfftfreq(n, 1 / sr)
    out = np.fft.irfft(spec_ / (1 + (f / 3500) ** 4), n)
    return out / (np.abs(out).max() + 1e-9) * 0.6


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    reel = Reel(spec)
    if len(sys.argv) > 3:
        for ts in sys.argv[3].split(","):
            reel.render(float(ts)).save(f"{out}_{ts}.png")
        return
    wav = out + ".wav"
    reel.build_audio(wav)
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(int(reel.total * FPS)):
        proc.stdin.write(reel.render(i / FPS).tobytes())
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    print(f"done {out} ({reel.total:.1f}s)")


if __name__ == "__main__":
    main()
