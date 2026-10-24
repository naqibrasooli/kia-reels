"""Render KIA sample Reel: 'What is HACCP in 30 seconds?' (Dari + English subtitles).
Text-and-icon only: no people, no animals, no music.
"""
import math
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
FONT_DIR = sys.argv[1]
OUT = sys.argv[2]

ORANGE = (255, 83, 15)
ORANGE_D = (214, 62, 6)
ORANGE_L = (255, 232, 214)
CREAM = (255, 248, 241)
INK = (30, 30, 38)
GREY = (110, 110, 122)
WHITE = (255, 255, 255)


def F(weight, size):
    return ImageFont.truetype(f"{FONT_DIR}/Vazirmatn-{weight}.ttf", size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


# ---------- layer helpers ----------
class Layer:
    def __init__(self, img, x, y, t_in, t_out=None, slide=40, anchor="center"):
        self.img, self.t_in, self.t_out, self.slide = img, t_in, t_out, slide
        w, h = img.size
        if anchor == "center":
            self.x, self.y = int(x - w / 2), int(y)
        elif anchor == "right":
            self.x, self.y = int(x - w), int(y)
        else:
            self.x, self.y = int(x), int(y)


def text_img(text, font, color, rtl=True, pad=6):
    d = "rtl" if rtl else "ltr"
    lang = "fa" if rtl else "en"
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    l, t, r, b = probe.textbbox((0, 0), text, font=font, direction=d, language=lang)
    img = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((pad - l, pad - t), text, font=font, fill=color,
                             direction=d, language=lang)
    return img


def lines_img(lines, font, color, rtl=True, gap=18, align="center"):
    imgs = [text_img(s, font, color, rtl) for s in lines]
    w = max(i.size[0] for i in imgs)
    h = sum(i.size[1] for i in imgs) + gap * (len(imgs) - 1)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for i in imgs:
        if align == "center":
            x = (w - i.size[0]) // 2
        elif align == "right":
            x = w - i.size[0]
        else:
            x = 0
        out.alpha_composite(i, (x, y))
        y += i.size[1] + gap
    return out


def rounded(w, h, r, fill, shadow=True):
    pad = 30 if shadow else 0
    img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 8, pad + w, pad + h + 8), r,
                                             fill=(120, 60, 20, 45))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(img).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=fill)
    return img


def subtitle(text_lines):
    """English subtitle box (white text on dark pill)."""
    font = F("SemiBold", 44)
    t = lines_img(text_lines, font, WHITE, rtl=False, gap=8)
    w, h = t.size[0] + 70, t.size[1] + 44
    box = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle((0, 0, w, h), 28, fill=(25, 25, 32, 225))
    box.alpha_composite(t, ((w - t.size[0]) // 2, (h - t.size[1]) // 2))
    return box


# ---------- icons (objects only) ----------
def icon_shield(size=300):
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(s * .5, s * .04), (s * .9, s * .18), (s * .86, s * .56),
           (s * .5, s * .96), (s * .14, s * .56), (s * .1, s * .18)]
    d.polygon(pts, fill=ORANGE)
    inner = [(s * .5, s * .13), (s * .8, s * .24), (s * .77, s * .54),
             (s * .5, s * .86), (s * .23, s * .54), (s * .2, s * .24)]
    d.polygon(inner, fill=ORANGE_D)
    d.line([(s * .33, s * .5), (s * .45, s * .63), (s * .69, s * .37)], fill=WHITE,
           width=int(s * .075), joint="curve")
    return img


def icon_dish(s=120):
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 6, s - 6, s - 6), outline=WHITE, width=8)
    for cx, cy, r in [(.38, .4, .07), (.62, .36, .05), (.55, .62, .08), (.33, .63, .045), (.7, .58, .04)]:
        d.ellipse((s * (cx - r), s * (cy - r), s * (cx + r), s * (cy + r)), fill=WHITE)
    return img


def icon_flask(s=120):
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((s * .4, s * .08, s * .6, s * .4), fill=WHITE)
    d.polygon([(s * .4, s * .38), (s * .6, s * .38), (s * .88, s * .88), (s * .12, s * .88)], fill=WHITE)
    d.polygon([(s * .3, s * .6), (s * .7, s * .6), (s * .82, s * .82), (s * .18, s * .82)], fill=ORANGE_L)
    d.rectangle((s * .34, s * .05, s * .66, s * .12), fill=WHITE)
    return img


def icon_bolt(s=120):
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy, r = s / 2, s / 2, s * .4
    hexp = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(0, 360, 60)]
    d.polygon(hexp, fill=WHITE)
    d.ellipse((cx - r * .45, cy - r * .45, cx + r * .45, cy + r * .45), fill=ORANGE)
    return img


def icon_check(s=70, color=ORANGE):
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, s, s), fill=color)
    d.line([(s * .27, s * .52), (s * .44, s * .68), (s * .74, s * .34)], fill=WHITE, width=int(s * .11), joint="curve")
    return img


def num_badge(n, s=72):
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((0, 0, s, s), fill=ORANGE)
    t = text_img(n, F("Bold", 40), WHITE, rtl=True)
    img.alpha_composite(t, ((s - t.size[0]) // 2, (s - t.size[1]) // 2 - 2))
    return img


# ---------- static frame chrome ----------
LOGO = Image.open(__import__("os").path.join(__import__("os").path.dirname(__file__), "logo.png")).convert("RGBA")


def logo_scaled(w):
    return LOGO.resize((w, round(LOGO.size[1] * w / LOGO.size[0])), Image.LANCZOS)


def base_frame():
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(img)
    # soft decorative circles
    d.ellipse((-260, -260, 420, 420), fill=(255, 236, 220))
    d.ellipse((760, 1500, 1400, 2140), fill=(255, 236, 220))
    # brand pill (top-right, RTL)
    logo = logo_scaled(280)
    img.alpha_composite(logo, ((W - logo.size[0]) // 2, 90))
    return img


BASE = base_frame()

# ---------- scenes ----------
scenes = []  # (start, end, [layers], subtitle_img)


def scene(start, end, layers, sub_lines):
    scenes.append((start, end, layers, subtitle(sub_lines)))


# S1 Hook 0-4
s, e = 0.0, 4.2
scene(s, e, [
    Layer(text_img("HACCP", F("Black", 230), ORANGE, rtl=False), W / 2, 450, s + .1, slide=60),
    Layer(text_img("چیست؟", F("Black", 150), INK), W / 2, 720, s + .5),
    Layer(rounded(520, 110, 55, ORANGE, shadow=False), W / 2, 960, s + .9, slide=20),
    Layer(text_img("در ۳۰ ثانیه", F("Bold", 64), WHITE), W / 2, 977, s + 1.0, slide=20),
], ["What is HACCP?", "Explained in 30 seconds"])

# S2 Definition 4.2-9
s, e = 4.2, 9.2
scene(s, e, [
    Layer(icon_shield(300), W / 2, 330, s + .1),
    Layer(lines_img(["HACCP یک سیستم", "ایمنی غذایی است"], F("Black", 96), INK, gap=10), W / 2, 690, s + .4),
    Layer(lines_img(["که خطرات را پیش از رسیدن غذا", "به مشتری شناسایی و کنترل می‌کند."], F("Medium", 56), GREY, gap=14), W / 2, 950, s + 1.0),
], ["A food safety system that finds and controls", "hazards before food reaches your customer."])

# S3 Three hazards 9.2-15.2
s, e = 9.2, 15.2
title = text_img("۳ نوع خطر در غذا", F("Black", 92), INK)
L = [Layer(title, W / 2, 330, s + .1)]
cards = [
    ("بیولوژیکی", "باکتری و ویروس", "Biological", icon_dish),
    ("کیمیاوی", "مواد پاک‌کاری و آفت‌کش", "Chemical", icon_flask),
    ("فزیکی", "شیشه، فلز و سنگ", "Physical", icon_bolt),
]
for i, (t1, t2, en, ic) in enumerate(cards):
    y = 520 + i * 270
    card = rounded(900, 230, 40, WHITE)
    cw = card.size[0]
    # orange icon tile on right side (RTL)
    tile = Image.new("RGBA", (170, 170), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, 170, 170), 34, fill=ORANGE)
    tile.alpha_composite(ic(120), (25, 25))
    card.alpha_composite(tile, (cw - 30 - 30 - 170, 30 + 30))
    a = text_img(t1, F("Black", 64), INK)
    b = text_img(t2, F("Medium", 42), GREY)
    c = text_img(en, F("SemiBold", 34), ORANGE, rtl=False)
    right = cw - 30 - 30 - 170 - 40
    card.alpha_composite(a, (right - a.size[0], 30 + 36))
    card.alpha_composite(b, (right - b.size[0], 30 + 36 + a.size[1]))
    card.alpha_composite(c, (30 + 50, 30 + 115 - c.size[1] // 2))
    L.append(Layer(card, W / 2, y - 30, s + .6 + i * .45, slide=60))
scene(s, e, L, ["3 types of food hazards:", "biological, chemical, physical"])

# S4 Seven principles 15.2-22.7
s, e = 15.2, 22.7
L = [Layer(text_img("۷ اصل HACCP", F("Black", 92), INK), W / 2, 300, s + .1)]
items = [
    ("۱", "تحلیل خطرات", "Hazard analysis"),
    ("۲", "تعیین نقاط کنترل بحرانی (CCP)", "CCPs"),
    ("۳", "تعیین حدود بحرانی", "Critical limits"),
    ("۴", "نظارت", "Monitoring"),
    ("۵", "اقدامات اصلاحی", "Corrective actions"),
    ("۶", "تصدیق سیستم", "Verification"),
    ("۷", "ثبت اسناد و ریکارد", "Records"),
]
for i, (n, fa, en) in enumerate(items):
    row = Image.new("RGBA", (900, 112), (0, 0, 0, 0))
    ImageDraw.Draw(row).rounded_rectangle((0, 4, 900, 108), 30, fill=WHITE)
    row.alpha_composite(num_badge(n, 72), (900 - 20 - 72, 20))
    a = text_img(fa, F("Bold", 46), INK)
    row.alpha_composite(a, (900 - 20 - 72 - 24 - a.size[0], 56 - a.size[1] // 2))
    c = text_img(en, F("Medium", 28), GREY, rtl=False)
    row.alpha_composite(c, (28, 56 - c.size[1] // 2))
    L.append(Layer(row, W / 2, 440 + i * 118, s + .5 + i * .55, slide=40))
scene(s, e, L, ["The 7 principles of HACCP"])

# S5 Why it matters 22.7-27.7
s, e = 22.7, 27.7
L = [Layer(text_img("چرا مهم است؟", F("Black", 100), INK), W / 2, 360, s + .1)]
benefits = ["اعتماد بیشتر مشتریان", "دسترسی به بازارهای صادراتی", "رعایت مقررات ایمنی غذا"]
for i, bt in enumerate(benefits):
    row = Image.new("RGBA", (900, 150), (0, 0, 0, 0))
    ImageDraw.Draw(row).rounded_rectangle((0, 0, 900, 150), 40, fill=ORANGE_L)
    row.alpha_composite(icon_check(84), (900 - 34 - 84, 33))
    a = text_img(bt, F("Bold", 56), INK)
    row.alpha_composite(a, (900 - 34 - 84 - 30 - a.size[0], 75 - a.size[1] // 2))
    L.append(Layer(row, W / 2, 600 + i * 190, s + .6 + i * .5, slide=50))
scene(s, e, L, ["Why it matters: customer trust,", "export markets and compliance"])

# S6 CTA 27.7-33.5
s, e = 27.7, 33.5
L = []
L.append(Layer(lines_img(["کلمه «HACCP» را", "کامنت کنید"], F("Black", 104), INK, gap=6), W / 2, 300, s + .1))
L.append(Layer(lines_img(["تا چک‌لیست رایگان", "را برایتان بفرستیم"], F("Medium", 60), GREY, gap=10), W / 2, 590, s + .6))
card = rounded(900, 450, 44, WHITE)
big = logo_scaled(360)
cw = card.size[0]
a = text_img("شرکت تحقیقاتی و انکشافی کیا", F("Black", 56), INK)
b = None
c = text_img("+93 799 000 579  ·  kia-rd.com", F("Bold", 44), ORANGE, rtl=False)
y0 = 30 + 28
card.alpha_composite(big, ((cw - big.size[0]) // 2, y0))
y0 += big.size[1] + 14
card.alpha_composite(a, ((cw - a.size[0]) // 2, y0))
y0 += a.size[1] + 10
card.alpha_composite(c, ((cw - c.size[0]) // 2, y0))
L.append(Layer(card, W / 2, 780, s + 1.2, slide=60))
scene(s, e, L, ["Comment HACCP and we'll send you", "a free checklist"])

TOTAL = scenes[-1][1]
SUB_Y = 1390


# ---------- animations (objects only) ----------
import random
_rng = random.Random(7)
PARTS = [(_rng.uniform(0, W), _rng.uniform(0, H), _rng.uniform(5, 16), _rng.uniform(25, 60),
          _rng.uniform(0, 6.28), _rng.randint(25, 60)) for _ in range(22)]
SPEED, GAP, X0 = 150.0, 180, W + 60
CX = W // 2
BELT_Y = 1262


def jar_x(k, t):
    return X0 + k * GAP - SPEED * t


def draw_particles(ov, t):
    d = ImageDraw.Draw(ov)
    for (x, y, r, v, ph, a) in PARTS:
        yy = (y - v * t) % (H + 80) - 40
        xx = x + 18 * math.sin(t * 0.8 + ph)
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=ORANGE + (a,))


def draw_conveyor(ov, t, a):
    d = ImageDraw.Draw(ov)
    A = lambda c, k=1.0: c + (int(255 * a * k),)
    # belt + rollers
    d.rounded_rectangle((60, BELT_Y, W - 60, BELT_Y + 14), 7, fill=A((70, 70, 80)))
    for i in range(14):
        rx = 80 + ((i * 70 - t * SPEED) % (W - 160))
        d.ellipse((rx - 5, BELT_Y + 2, rx + 5, BELT_Y + 12), fill=A((150, 150, 160)))
    # jars
    for k in range(-2, 30):
        x = jar_x(k, t)
        if x < 30 or x > W - 30:
            continue
        top = BELT_Y - 72
        d.rounded_rectangle((x - 28, top + 12, x + 28, BELT_Y), 10, fill=A(WHITE))
        d.rounded_rectangle((x - 28, top + 12, x + 28, BELT_Y), 10, outline=A((225, 205, 190)), width=3)
        d.rounded_rectangle((x - 22, top, x + 22, top + 16), 5, fill=A(ORANGE))
        d.rectangle((x - 28, top + 34, x + 28, top + 52), fill=A(ORANGE_L))
        if x < CX - 10:  # passed inspection -> green tick
            p = ease((CX - 10 - x) / 40)
            r = 18 * p
            cy = top - 30
            d.ellipse((x - r, cy - r, x + r, cy + r), fill=A((46, 160, 90), p))
            if p > .6:
                d.line([(x - 8, cy), (x - 2, cy + 7), (x + 9, cy - 6)], fill=A(WHITE), width=4, joint="curve")
    # scanner arch + beam
    d.rectangle((CX - 52, BELT_Y - 108, CX - 42, BELT_Y), fill=A(ORANGE_D))
    d.rectangle((CX + 42, BELT_Y - 108, CX + 52, BELT_Y), fill=A(ORANGE_D))
    d.rounded_rectangle((CX - 60, BELT_Y - 120, CX + 60, BELT_Y - 100), 8, fill=A(ORANGE))
    beam = 0.35 + 0.25 * math.sin(t * 9)
    d.rectangle((CX - 40, BELT_Y - 100, CX + 40, BELT_Y), fill=ORANGE + (int(70 * beam * a),))


def draw_ring(ov, t, a, cx, cy, r=180):
    d = ImageDraw.Draw(ov)
    for i in range(28):
        ang = math.radians(i * (360 / 28) + t * 40)
        a1 = ang - 0.07
        p1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
        p2 = (cx + r * math.cos(ang + 0.07), cy + r * math.sin(ang + 0.07))
        d.line([p1, p2], fill=ORANGE + (int(170 * a),), width=8)


def draw_growth(ov, tl, a):
    d = ImageDraw.Draw(ov)
    base, n, bw = 1282, 6, 70
    x0 = CX - (n * bw + (n - 1) * 26) // 2
    for i in range(n):
        h = (30 + i * 18) * ease((tl - 1.6 - i * 0.18) / 0.6)
        if h <= 0:
            continue
        x = x0 + i * (bw + 26)
        d.rounded_rectangle((x, base - h, x + bw, base), 12, fill=(ORANGE if i == n - 1 else ORANGE_L) + (int(255 * a),))
    p = ease((tl - 3.0) / 0.6)
    if p > 0:
        xs, ys = x0 + 20, base - 50
        xe, ye = x0 + (n - 1) * (bw + 26) + bw, base - 125
        xm, ym = xs + (xe - xs) * p, ys + (ye - ys) * p
        d.line([(xs, ys), (xm, ym)], fill=INK + (int(220 * a),), width=7)
        d.polygon([(xm, ym - 20), (xm + 22, ym + 6), (xm - 6, ym + 18)], fill=INK + (int(220 * a),))


def scene_alpha(t, s, e):
    if not (s - 0.01 <= t < e + 0.35):
        return 0.0
    return 1.0 if t < e else max(0.0, 1 - (t - e) / 0.35)


def draw_anims(frame, t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_particles(ov, t)
    a = max(scene_alpha(t, scenes[0][0], scenes[0][1]), scene_alpha(t, scenes[1][0], scenes[1][1]))
    if a > 0:
        draw_conveyor(ov, t, a * ease(t / 0.6))
    s2, e2 = scenes[1][0], scenes[1][1]
    a = scene_alpha(t, s2, e2) * ease((t - s2 - .1) / .5)
    if a > 0:
        draw_ring(ov, t, a, CX, 330 + 150)
    s5, e5 = scenes[4][0], scenes[4][1]
    a = scene_alpha(t, s5, e5)
    if a > 0:
        draw_growth(ov, t - s5, a)
    frame.alpha_composite(ov)


# ---------- sound effects (no music) ----------
def build_audio(path, sr=44100):
    import numpy as np, wave
    n = int(TOTAL * sr) + sr
    out = np.zeros(n)
    rng = np.random.default_rng(3)

    def add(sig, t, vol):
        i = int(t * sr)
        j = min(n, i + len(sig))
        if i < n:
            out[i:j] += vol * sig[: j - i]

    def pop():
        tt = np.arange(int(.09 * sr)) / sr
        f = 950 - 4000 * tt
        return np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt * 45)

    def whoosh(dur=.55):
        m = int(dur * sr)
        x = rng.standard_normal(m)
        k = np.linspace(0, 1, m)
        env = np.sin(np.pi * k) ** 2
        # moving one-pole lowpass for a sweep
        y = np.zeros(m); acc = 0
        for i in range(m):
            c = 0.02 + 0.25 * k[i]
            acc += c * (x[i] - acc); y[i] = acc
        return y / (np.abs(y).max() + 1e-9) * env

    def tick():
        tt = np.arange(int(.03 * sr)) / sr
        return np.sin(2 * np.pi * 2300 * tt) * np.exp(-tt * 160)

    def ding(f):
        tt = np.arange(int(1.4 * sr)) / sr
        return (np.sin(2 * np.pi * f * tt) + .35 * np.sin(2 * np.pi * 2.01 * f * tt)) * np.exp(-tt * 3.2)

    for i, (s, e, layers, sub) in enumerate(scenes):
        if i:
            add(whoosh(), s - .25, .30)
        for ly in layers:
            add(pop(), ly.t_in + .05, .20)
    e2 = scenes[1][1]
    for k in range(-2, 30):
        tc = (X0 + k * GAP - CX) / SPEED
        if 0.4 < tc < e2:
            add(tick(), tc, .10)
    s6 = scenes[-1][0]
    add(ding(784), s6 + 1.25, .16)
    add(ding(1046), s6 + 1.40, .12)
    out = out / max(1.0, np.abs(out).max() / 0.85)
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())


def alpha_mul(img, a):
    if a >= 1:
        return img
    r, g, b, al = img.split()
    al = al.point(lambda v: int(v * a))
    return Image.merge("RGBA", (r, g, b, al))


def render(t):
    frame = BASE.copy()
    draw_anims(frame, t)
    for (s, e, layers, sub) in scenes:
        if not (s - 0.01 <= t < e + 0.35):
            continue
        out_a = 1.0 if t < e else max(0.0, 1 - (t - e) / 0.35)
        for ly in layers:
            p = ease((t - ly.t_in) / 0.45)
            if p <= 0:
                continue
            dy = int((1 - p) * ly.slide)
            frame.alpha_composite(alpha_mul(ly.img, p * out_a), (ly.x, ly.y + dy))
        p = ease((t - s - 0.15) / 0.35) * out_a
        if p > 0:
            frame.alpha_composite(alpha_mul(sub, p), ((W - sub.size[0]) // 2, SUB_Y))
    # progress bar
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((80, 1300, W - 80, 1310), 5, fill=(240, 220, 205))
    x = 80 + int((W - 160) * min(1, t / TOTAL))
    d.rounded_rectangle((W - 80 - (x - 80), 1300, W - 80, 1310), 5, fill=ORANGE)  # fills right-to-left
    return frame.convert("RGB")


if __name__ == "__main__":
    if len(sys.argv) > 3:  # preview stills
        for ts in sys.argv[3].split(","):
            render(float(ts)).save(f"{OUT}_{ts}.png")
        sys.exit()
    n = int(TOTAL * FPS)
    wav = OUT + ".wav"
    build_audio(wav)
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest",
        "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(render(i / FPS).tobytes())
    proc.stdin.close()
    proc.wait()
    print("done", n, "frames")
