"""Flat cartoon illustrations for KIA Reels (no photos).
- art_factory(): a clean, well-kept food factory with a food-safety check badge.
- worker_scene(t): a male food worker in full hygiene gear washing hands (animated).
Workers are always shown in correct hygiene practice: hairnet, mask, white uniform, gloves.
"""
import math
from PIL import Image, ImageDraw

ORANGE = (255, 83, 15)
ORANGE_L = (255, 232, 214)
SKIN = (205, 150, 110)
SKIN_D = (180, 125, 90)
NET = (196, 224, 245)
MASK = (160, 205, 240)
GLOVE = (70, 140, 230)
COAT = (255, 255, 255)
LINE = (205, 212, 224)
STEEL = (196, 203, 212)
STEEL_D = (150, 158, 170)
WATER = (90, 170, 240)
INK = (40, 40, 50)
GREEN = (46, 160, 90)
WALL = (232, 242, 247)


def art_factory(w=560):
    s = w / 560
    img = Image.new("RGBA", (w, int(380 * s)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    S = lambda *v: [x * s for x in v]
    d.rounded_rectangle(S(10, 330, 550, 350), int(10 * s), fill=(214, 234, 214))       # lawn
    d.rectangle(S(60, 150, 500, 335), fill=(246, 248, 251), outline=LINE, width=int(5 * s))
    for i in range(4):                                                                  # saw-tooth roof
        x = 60 + i * 110
        d.polygon(S(x, 150, x + 110, 150, x + 110, 80), fill=ORANGE)
        d.polygon(S(x + 70, 108, x + 108, 86, x + 108, 150, x + 70, 150), fill=(255, 140, 90))
    d.rectangle(S(60, 190, 500, 204), fill=ORANGE)                                      # brand stripe
    for x in (90, 170, 330, 410):                                                       # windows
        d.rounded_rectangle(S(x, 225, x + 60, 275), int(6 * s), fill=(190, 222, 245), outline=LINE, width=int(3 * s))
        d.line(S(x + 30, 225, x + 30, 275), fill=LINE, width=int(3 * s))
    d.rounded_rectangle(S(245, 230, 315, 335), int(6 * s), fill=(150, 160, 175))        # door
    d.rectangle(S(278, 230, 282, 335), fill=(120, 130, 145))
    d.ellipse(S(455, 30, 545, 120), fill=GREEN)                                          # safety badge
    d.line(S(476, 76, 494, 94, 524, 58), fill=(255, 255, 255), width=int(12 * s), joint="curve")
    for x in (20, 520):                                                                  # trees
        d.rectangle(S(x + 14, 280, x + 22, 335), fill=(140, 100, 70))
        d.ellipse(S(x - 6, 230, x + 42, 292), fill=(120, 190, 120))
    return img


def worker_scene(t, w=440):
    s = w / 440
    img = Image.new("RGBA", (w, int(760 * s)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    S = lambda *v: [x * s for x in v]
    lw = lambda v: max(1, int(v * s))
    # tiled hygienic wall
    d.rounded_rectangle(S(0, 40, 440, 600), lw(40), fill=WALL)
    for y in range(80, 600, 60):
        d.line(S(20, y, 420, y), fill=(218, 232, 240), width=lw(2))
    for x in range(60, 440, 60):
        d.line(S(x, 50, x, 590), fill=(218, 232, 240), width=lw(2))
    # hand-wash sign + soap dispenser
    d.rounded_rectangle(S(28, 70, 118, 160), lw(14), fill=(255, 255, 255), outline=WATER, width=lw(5))
    d.polygon(S(73, 88, 92, 120, 73, 140, 54, 120), fill=WATER)
    d.ellipse(S(54, 104, 92, 142), fill=WATER)
    d.rounded_rectangle(S(352, 300, 402, 380), lw(10), fill=(255, 255, 255), outline=LINE, width=lw(4))
    d.rectangle(S(366, 380, 388, 394), fill=STEEL_D)
    # legs + boots
    d.rectangle(S(160, 560, 212, 690), fill=(90, 100, 122))
    d.rectangle(S(228, 560, 280, 690), fill=(90, 100, 122))
    d.rounded_rectangle(S(150, 680, 218, 712), lw(12), fill=(250, 250, 250), outline=LINE, width=lw(3))
    d.rounded_rectangle(S(222, 680, 290, 712), lw(12), fill=(250, 250, 250), outline=LINE, width=lw(3))
    # coat
    d.rounded_rectangle(S(118, 250, 322, 590), lw(60), fill=COAT, outline=LINE, width=lw(5))
    d.polygon(S(186, 252, 220, 310, 254, 252), fill=(232, 238, 244))
    for y in (340, 390, 440):
        d.ellipse(S(214, y, 226, y + 12), fill=STEEL_D)
    d.rounded_rectangle(S(250, 330, 296, 372), lw(8), outline=LINE, width=lw(4))
    d.line(S(262, 320, 262, 350), fill=ORANGE, width=lw(5))                             # pen in pocket
    # neck + head
    d.rectangle(S(204, 222, 236, 256), fill=SKIN_D)
    d.ellipse(S(152, 160, 176, 196), fill=SKIN)
    d.ellipse(S(264, 160, 288, 196), fill=SKIN)
    d.ellipse(S(158, 98, 282, 238), fill=SKIN)
    # hairnet
    d.chord(S(150, 82, 290, 222), 180, 360, fill=NET)
    d.line(S(154, 152, 286, 152), fill=(160, 200, 232), width=lw(6))
    for i in range(9):
        for j in range(3):
            x, y = 172 + i * 13 + (j % 2) * 6, 104 + j * 15
            if (x - 220) ** 2 / 70 ** 2 + (y - 152) ** 2 / 70 ** 2 < 0.95:
                d.ellipse(S(x - 2, y - 2, x + 2, y + 2), fill=(160, 200, 232))
    # eyes + brows (friendly)
    blink = (t % 3.2) < 0.12
    for ex in (196, 244):
        if blink:
            d.line(S(ex - 8, 172, ex + 8, 172), fill=INK, width=lw(4))
        else:
            d.ellipse(S(ex - 7, 165, ex + 7, 180), fill=INK)
            d.ellipse(S(ex - 2, 167, ex + 2, 171), fill=(255, 255, 255))
        d.arc(S(ex - 12, 150, ex + 12, 166), 200, 340, fill=(90, 60, 40), width=lw(4))
    # face mask
    d.rounded_rectangle(S(176, 186, 264, 236), lw(16), fill=MASK)
    for y in (200, 212, 224):
        d.line(S(184, y, 256, y), fill=(135, 185, 228), width=lw(3))
    d.line(S(176, 196, 160, 180), fill=(135, 185, 228), width=lw(3))
    d.line(S(264, 196, 280, 180), fill=(135, 185, 228), width=lw(3))
    # sink (stainless) + faucet
    d.rounded_rectangle(S(60, 486, 380, 566), lw(18), fill=STEEL, outline=STEEL_D, width=lw(4))
    d.rounded_rectangle(S(100, 486, 340, 512), lw(10), fill=STEEL_D)
    d.rectangle(S(300, 400, 314, 488), fill=STEEL_D)
    d.rounded_rectangle(S(220, 396, 314, 412), lw(8), fill=STEEL_D)
    # running water
    for k in range(6):
        y = 414 + ((t * 260 + k * 14) % 80)
        d.line(S(230, y, 230, y + 10), fill=WATER, width=lw(6))
    # arms + gloved hands rubbing under the tap
    ph = math.sin(t * 9)
    hands = [(205 + 16 * ph, 462 + 4 * math.cos(t * 9)), (238 - 16 * ph, 466 - 4 * math.cos(t * 9))]
    for (sx, sy), (hx, hy) in zip([(140, 300), (300, 300)], hands):
        d.line(S(sx, sy, hx, hy - 6), fill=LINE, width=lw(46))
        d.line(S(sx, sy, hx, hy - 6), fill=COAT, width=lw(38))
        d.ellipse(S(hx - 24, hy - 24, hx + 24, hy + 24), fill=GLOVE)
    # soap bubbles
    for k in range(7):
        ph2 = (t * 0.9 + k * 0.37) % 1.0
        bx = 222 + 60 * math.sin(k * 2.1 + t * 1.3)
        by = 470 - ph2 * 120
        r = 6 + (k % 3) * 3
        a = int(255 * (1 - ph2))
        d.ellipse(S(bx - r, by - r, bx + r, by + r), outline=(120, 180, 235, a), width=lw(3), fill=(255, 255, 255, a // 2))
    return img
