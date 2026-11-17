#!/usr/bin/env python3
"""Pustaka aset 'Simulasi Pemimpin Muda vs Tua' — gaya 32-bit (grid 640x360).
Sprite peta 16x26 (4 frame jalan), bangunan, dan potret close-up.
Tokoh: KEVIN (26, visioner), MULYADI (70, keras kepala), SARI (anak Mulyadi),
UJANG (22, petani muda, cangkul di pundak)."""
import math
from PIL import Image, ImageDraw

SKIN = (238, 190, 146); SKIN_L = (246, 206, 164); SKIN_D = (214, 164, 120)
SKIN_OLD = (228, 178, 134); EYE = (30, 24, 20); BLUSH = (240, 150, 130)
BOOT = (96, 66, 40)

def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)

# ---------------- sprite peta 16x26 ----------------
BASE_BODY = [
    "....hhhhhhhh....",
    "...hhhhhhhhhh...",
    "...hhHHhhhhhh...",
    "...hffffffffh...",
    "...hffffffffh...",
    "...hfeffffefh...",
    "...hffffffffh...",
    "...hfBffffBfh...",
    "....ffffffff....",
    "....ffffffff....",
    "...ssssssssss...",
    "..ssssssssssss..",
    "..sSssssssssSs..",
    "..sSssssssssSs..",
    "..sSssssssssSs..",
    "...ssssssssss...",
    "...ssssssssss...",
    "....pppppppp....",
    "....pppppppp....",
    "....pppppppp....",
]
LEGS_WALK = [
    ["....ppp..ppp....", "....ppp..ppp....", "....OOO..OOO....", "....OOO..OOO...."],
    [".....pppppp.....", ".....pppppp.....", ".....OOOOOO.....", ".....OOOOOO....."],
    [".....ppp..ppp...", ".....ppp..ppp...", ".....OOO..OOO...", ".....OOO..OOO..."],
    [".....pppppp.....", ".....pppppp.....", ".....OOOOOO.....", ".....OOOOOO....."],
]
LEGS_SARONG = [
    ["....cccccccc....", "....cccccccc....", "....cccccccc....", "....OOO..OOO...."],
    ["....cccccccc....", "....cccccccc....", "....cccccccc....", "....OOO..OOO...."],
    ["....cccccccc....", "....cccccccc....", "....cccccccc....", "....OOO..OOO...."],
    ["....cccccccc....", "....cccccccc....", "....cccccccc....", "....OOO..OOO...."],
]
LEGS_SKIRT = [
    ["....kkkkkkkk....", "....kkkkkkkk....", "....kkkkkkkk....", "....OOO..OOO...."],
    ["....kkkkkkkk....", "...kkkkkkkkkk...", "....kkkkkkkk....", "....OOO..OOO...."],
    ["....kkkkkkkk....", "....kkkkkkkk....", "....kkkkkkkk....", "....OOO..OOO...."],
    ["....kkkkkkkk....", "...kkkkkkkkkk...", "....kkkkkkkk....", "....OOO..OOO...."],
]

def _build(body, legs, pal, extra=None):
    frames = []
    for li, leg in enumerate(legs):
        im = Image.new("RGBA", (16, 26), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([2, 23, 14, 25], fill=(0, 0, 0, 70))
        for j, row in enumerate(body + leg):
            for i, ch in enumerate(row):
                if ch != "." and ch in pal:
                    d.point((i, j), fill=pal[ch] + (255,))
        if extra:
            extra(d, li)
        frames.append(im)
    return frames

def kevin_frames():
    body = list(BASE_BODY)
    body[10] = "...sswwssssss..."  # kerah putih
    pal = {"h": (30, 26, 22), "H": (52, 46, 40), "f": SKIN, "e": EYE, "B": BLUSH,
           "s": (92, 160, 222), "S": (66, 128, 184), "w": (244, 244, 240),
           "p": (52, 58, 96), "O": BOOT}
    return _build(body, LEGS_WALK, pal)

def mulyadi_frames():
    body = list(BASE_BODY)
    body[0] = ".....hhhhhh....."
    body[2] = "...hhHHhhhff...."  # rambut menipis di depan
    body[7] = "...hfmmmmmmfh..."  # kumis abu-abu
    body[8] = "....fmmmmmmf...."  # janggut tipis
    body[17] = "....cccccccc...."
    body[18] = "....cCcCcCcC...."
    body[19] = "....cccccccc...."
    pal = {"h": (172, 172, 168), "H": (200, 200, 196), "f": SKIN_OLD, "e": EYE, "B": BLUSH,
           "m": (150, 150, 146), "s": (150, 100, 60), "S": (118, 78, 46),
           "c": (96, 70, 50), "C": (130, 95, 65), "p": (96, 70, 50), "O": BOOT}
    def stick(d, li):
        for y in range(10, 24):
            d.point((1, y), fill=(120, 86, 50, 255))
        d.point((1, 9), fill=(150, 112, 66, 255))
    return _build(body, LEGS_SARONG, pal, extra=stick)

def sari_frames():
    body = list(BASE_BODY)
    body[3] = "..hhffffffffhh.."
    body[4] = "..hhffffffffhh.."
    body[5] = "..hhfeffffefhh.."
    body[6] = "..hhffffffffhh.."
    body[7] = "..hhfBffffBfhh.."
    body[8] = "..hhffffffffhh.."
    body[9] = "..hhffffffffhh.."
    body[10] = "..hhsssssssshh.."
    body[11] = "..hssssssssssh.."
    body[17] = "....kkkkkkkk...."
    body[18] = "....kkkkkkkk...."
    body[19] = "....kkkkkkkk...."
    pal = {"h": (24, 20, 18), "H": (44, 38, 34), "f": SKIN, "e": EYE, "B": BLUSH,
           "s": (168, 90, 190), "S": (132, 66, 152),
           "k": (90, 60, 110), "p": (90, 60, 110), "O": BOOT}
    return _build(body, LEGS_SKIRT, pal)

def ujang_frames():
    body = list(BASE_BODY)
    body[3] = "...hrrrrrrrrh..."  # ikat kepala merah
    body[12] = "..fSssssssssSf.."
    body[13] = "..fSssssssssSf.."
    body[14] = "..fSssssssssSf.."
    pal = {"h": (30, 26, 22), "H": (52, 46, 40), "f": SKIN, "e": EYE, "B": BLUSH,
           "r": (220, 60, 50), "s": (226, 110, 60), "S": (188, 84, 44),
           "p": (70, 70, 80), "O": BOOT}
    def hoe(d, li):
        for (x, y) in ((3, 5), (4, 7), (5, 9)):
            d.point((x, y), fill=(120, 86, 50, 255))
        d.rectangle([1, 2, 2, 4], fill=(150, 150, 150, 255))
        d.point((1, 2), fill=(200, 200, 200, 255))
    return _build(body, LEGS_WALK, pal, extra=hoe)

def villager_frames(hair, shirt):
    pal = {"h": hair, "H": shade(hair, 1.35), "f": SKIN, "e": EYE, "B": BLUSH,
           "s": shirt, "S": shade(shirt, 0.7), "p": (52, 58, 96), "O": BOOT}
    return _build(BASE_BODY, LEGS_WALK, pal)

# ---------------- bangunan ----------------
def make_house(roof_c, wall_c, abandoned=False):
    im = Image.new("RGBA", (34, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([1, 28, 33, 31], fill=(0, 0, 0, 70))
    wall, wall_m, wall_d = wall_c, shade(wall_c, 0.88), shade(wall_c, 0.74)
    roof = [roof_c, shade(roof_c, 0.88), shade(roof_c, 0.76), shade(roof_c, 0.64)]
    if abandoned:
        wall, wall_m, wall_d = (116, 106, 96), (102, 92, 84), (88, 80, 72)
        roof = [(110, 76, 68)] * 4
    d.rectangle([4, 12, 29, 19], fill=wall)
    d.rectangle([4, 20, 29, 24], fill=wall_m)
    d.rectangle([4, 25, 29, 28], fill=wall_d)
    d.rectangle([27, 12, 29, 28], fill=wall_d)
    for k, rc in enumerate(roof):
        d.rectangle([4 + k * 2, 4 + k * 2, 29 - k * 2, 5 + k * 2], fill=rc)
    d.rectangle([14, 2, 19, 3], fill=roof[0])
    win = (250, 222, 132) if not abandoned else (60, 56, 50)
    d.rectangle([7, 15, 11, 19], fill=win)
    d.rectangle([9, 15, 9, 19], fill=wall_d)
    d.point((8, 16), fill=(255, 255, 255))
    d.rectangle([19, 15, 23, 28], fill=(58, 42, 28))
    d.point((22, 21), fill=(200, 180, 120))
    d.rectangle([25, 2, 27, 8], fill=(150, 90, 70))
    return im

def make_tree(fruit=False):
    im = Image.new("RGBA", (20, 26), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([2, 23, 18, 25], fill=(0, 0, 0, 70))
    d.rectangle([9, 14, 11, 24], fill=(112, 74, 42))
    d.rectangle([11, 14, 11, 24], fill=(88, 56, 32))
    d.ellipse([1, 4, 19, 18], fill=(38, 104, 44))
    d.ellipse([2, 2, 18, 16], fill=(52, 134, 58))
    d.ellipse([3, 1, 15, 12], fill=(74, 164, 74))
    d.ellipse([4, 2, 9, 7], fill=(96, 190, 96))
    if fruit:
        for fx, fy in ((4, 10), (14, 12), (9, 14), (15, 8)):
            d.point((fx, fy), fill=(244, 204, 64))
    return im

def make_pump():
    """Pompa air: mesin kecil + pipa + roda."""
    im = Image.new("RGBA", (22, 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([1, 17, 21, 19], fill=(0, 0, 0, 70))
    d.rectangle([3, 8, 14, 17], fill=(180, 60, 50))
    d.rectangle([3, 8, 14, 10], fill=(208, 84, 72))
    d.rectangle([12, 8, 14, 17], fill=(140, 44, 38))
    d.rectangle([5, 4, 10, 8], fill=(90, 90, 96))
    d.rectangle([15, 10, 20, 13], fill=(120, 120, 128))
    d.ellipse([16, 6, 21, 11], fill=(60, 60, 66))
    d.ellipse([18, 8, 19, 9], fill=(200, 200, 200))
    d.rectangle([1, 13, 3, 17], fill=(70, 70, 76))
    return im

def make_mill():
    """Penggilingan padi: bangunan besar + cerobong."""
    im = Image.new("RGBA", (46, 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([2, 36, 44, 39], fill=(0, 0, 0, 70))
    d.rectangle([4, 14, 41, 36], fill=(170, 120, 70))
    d.rectangle([4, 14, 41, 20], fill=(186, 134, 80))
    d.rectangle([38, 14, 41, 36], fill=(140, 96, 54))
    d.polygon([(2, 14), (23, 2), (44, 14)], fill=(150, 60, 50))
    d.polygon([(23, 2), (44, 14), (23, 14)], fill=(130, 50, 42))
    d.rectangle([36, 0, 40, 12], fill=(120, 80, 60))
    d.rectangle([18, 24, 28, 36], fill=(70, 48, 30))
    d.rectangle([8, 22, 13, 27], fill=(250, 222, 132))
    d.rectangle([32, 22, 37, 27], fill=(250, 222, 132))
    d.rectangle([6, 30, 16, 32], fill=(120, 84, 48))
    d.point((8, 29), fill=(240, 210, 110)); d.point((12, 29), fill=(240, 210, 110))
    return im

def make_stall(awning):
    """Warung pasar: tiang + tenda garis + meja dagangan."""
    im = Image.new("RGBA", (30, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([1, 21, 29, 23], fill=(0, 0, 0, 70))
    d.rectangle([2, 8, 4, 22], fill=(110, 74, 44))
    d.rectangle([25, 8, 27, 22], fill=(110, 74, 44))
    for i, x in enumerate(range(0, 30, 6)):
        d.rectangle([x, 2, x + 5, 8], fill=awning if i % 2 == 0 else (244, 240, 228))
    d.rectangle([0, 2, 29, 3], fill=shade(awning, 1.2))
    d.rectangle([3, 15, 26, 18], fill=(140, 96, 54))
    for fx, fc in ((6, (230, 60, 50)), (11, (240, 200, 60)), (16, (90, 180, 80)), (21, (230, 120, 40))):
        d.ellipse([fx, 12, fx + 3, 15], fill=fc)
    return im

HOUSE_THATCH = make_house((196, 150, 80), (156, 104, 58))
HOUSE_TILE = make_house((208, 94, 76), (170, 120, 70))
HOUSE_ABAND = make_house((196, 150, 80), (156, 104, 58), abandoned=True)
TREE = make_tree()
PUMP = make_pump()
MILL = make_mill()
STALL_RED = make_stall((200, 60, 50))
STALL_BLUE = make_stall((60, 120, 200))

# ---------------- potret close-up (grid 640x360) ----------------
DARK = (30, 24, 20)
SHADOW = (168, 138, 86)

def _face_base(d, x0, y0, skin=SKIN, skin_l=SKIN_L, skin_d=SKIN_D):
    d.rectangle([x0 + 6, y0 - 112, x0 + 36, y0 - 84], fill=skin)
    d.rectangle([x0 + 6, y0 - 112, x0 + 10, y0 - 84], fill=skin_l)
    d.rectangle([x0 + 32, y0 - 112, x0 + 36, y0 - 84], fill=skin_d)
    d.rectangle([x0 + 4, y0 - 100, x0 + 6, y0 - 92], fill=skin_d)
    d.rectangle([x0 + 36, y0 - 100, x0 + 38, y0 - 92], fill=skin_d)
    d.rectangle([x0 + 20, y0 - 98, x0 + 22, y0 - 94], fill=skin_d)

def _eyes(d, x0, y0, blink, lash=False):
    if not blink:
        for ex in (x0 + 12, x0 + 26):
            d.rectangle([ex, y0 - 100, ex + 4, y0 - 95], fill=(250, 248, 244))
            d.rectangle([ex + 1, y0 - 100, ex + 3, y0 - 95], fill=DARK)
            d.point((ex + 1, y0 - 99), fill=(255, 255, 255))
            if lash:
                d.point((ex + 4, y0 - 100), fill=DARK)
    else:
        d.rectangle([x0 + 12, y0 - 97, x0 + 16, y0 - 96], fill=DARK)
        d.rectangle([x0 + 26, y0 - 97, x0 + 30, y0 - 96], fill=DARK)

def _mouth(d, x0, y0, mouth, expr):
    if mouth == "open":
        d.ellipse([x0 + 16, y0 - 90, x0 + 26, y0 - 83], fill=(110, 36, 32))
        d.ellipse([x0 + 18, y0 - 86, x0 + 24, y0 - 83], fill=(200, 90, 80))
    elif expr == "happy":
        d.line([(x0 + 15, y0 - 89), (x0 + 21, y0 - 84), (x0 + 27, y0 - 89)], fill=DARK, width=2)
    elif expr == "sad":
        d.line([(x0 + 16, y0 - 85), (x0 + 21, y0 - 89), (x0 + 26, y0 - 85)], fill=DARK, width=2)
    else:
        d.rectangle([x0 + 17, y0 - 88, x0 + 25, y0 - 87], fill=DARK)

def draw_kevin(d, x0, gy, mouth="closed", blink=False, expr="neutral", bob=0):
    """Kevin 26: rambut rapi belah pinggir, kemeja biru muda, gulungan rencana."""
    y0 = gy - bob
    SHIRT, SHIRT_D, SHIRT_L = (92, 160, 222), (66, 128, 184), (130, 190, 240)
    d.ellipse([x0 - 2, gy - 2, x0 + 42, gy + 3], fill=SHADOW)
    d.rectangle([x0 + 8, y0 - 46, x0 + 34, y0 - 14], fill=(52, 58, 96))
    d.rectangle([x0 + 30, y0 - 46, x0 + 34, y0 - 14], fill=(40, 46, 78))
    d.rectangle([x0 + 6, y0 - 14, x0 + 17, y0], fill=BOOT)
    d.rectangle([x0 + 25, y0 - 14, x0 + 36, y0], fill=BOOT)
    d.rectangle([x0 + 4, y0 - 84, x0 + 38, y0 - 46], fill=SHIRT)
    d.rectangle([x0 + 34, y0 - 84, x0 + 38, y0 - 46], fill=SHIRT_D)
    d.rectangle([x0 + 4, y0 - 84, x0 + 8, y0 - 46], fill=SHIRT_L)
    d.polygon([(x0 + 17, y0 - 84), (x0 + 21, y0 - 78), (x0 + 17, y0 - 74)], fill=SHIRT_D)
    d.polygon([(x0 + 25, y0 - 84), (x0 + 21, y0 - 78), (x0 + 25, y0 - 74)], fill=SHIRT_D)
    for by in (y0 - 70, y0 - 62, y0 - 54):
        d.point((x0 + 21, by), fill=(240, 240, 240))
    # lengan kiri memegang gulungan rencana
    d.rectangle([x0, y0 - 82, x0 + 5, y0 - 54], fill=SHIRT_D)
    d.rectangle([x0 - 2, y0 - 58, x0 + 6, y0 - 52], fill=(244, 240, 228))
    d.rectangle([x0 - 2, y0 - 58, x0, y0 - 52], fill=(200, 190, 170))
    d.rectangle([x0 + 37, y0 - 82, x0 + 42, y0 - 54], fill=SHIRT_D)
    d.rectangle([x0 + 37, y0 - 54, x0 + 42, y0 - 47], fill=SKIN)
    _face_base(d, x0, y0)
    # rambut rapi belah pinggir
    d.rectangle([x0 + 5, y0 - 118, x0 + 37, y0 - 108], fill=(30, 26, 22))
    d.rectangle([x0 + 5, y0 - 108, x0 + 9, y0 - 100], fill=(30, 26, 22))
    d.rectangle([x0 + 33, y0 - 108, x0 + 37, y0 - 100], fill=(30, 26, 22))
    d.rectangle([x0 + 8, y0 - 117, x0 + 20, y0 - 115], fill=(56, 48, 42))
    d.rectangle([x0 + 11, y0 - 105, x0 + 17, y0 - 103], fill=DARK)
    d.rectangle([x0 + 25, y0 - 105, x0 + 31, y0 - 103], fill=DARK)
    _eyes(d, x0, y0, blink)
    _mouth(d, x0, y0, mouth, expr)

def draw_mulyadi(d, x0, gy, mouth="closed", blink=False, expr="stern", bob=0):
    """Mulyadi 70: rambut abu-abu menipis, keriput, kumis, baju cokelat, sarung, tongkat."""
    y0 = gy - bob
    SHIRT, SHIRT_D = (150, 100, 60), (118, 78, 46)
    d.ellipse([x0 - 2, gy - 2, x0 + 42, gy + 3], fill=SHADOW)
    # tongkat
    d.rectangle([x0 + 43, y0 - 70, x0 + 45, y0], fill=(120, 86, 50))
    d.rectangle([x0 + 42, y0 - 74, x0 + 46, y0 - 70], fill=(150, 112, 66))
    # sarung
    d.rectangle([x0 + 8, y0 - 46, x0 + 34, y0 - 12], fill=(96, 70, 50))
    for sy in range(y0 - 42, y0 - 14, 8):
        d.line([(x0 + 9, sy), (x0 + 33, sy)], fill=(130, 95, 65))
    d.rectangle([x0 + 30, y0 - 46, x0 + 34, y0 - 12], fill=(78, 56, 40))
    d.rectangle([x0 + 6, y0 - 12, x0 + 17, y0], fill=BOOT)
    d.rectangle([x0 + 25, y0 - 12, x0 + 36, y0], fill=BOOT)
    # badan
    d.rectangle([x0 + 4, y0 - 84, x0 + 38, y0 - 46], fill=SHIRT)
    d.rectangle([x0 + 34, y0 - 84, x0 + 38, y0 - 46], fill=SHIRT_D)
    for by in (y0 - 70, y0 - 62, y0 - 54):
        d.point((x0 + 21, by), fill=(220, 200, 160))
    d.rectangle([x0, y0 - 82, x0 + 5, y0 - 54], fill=SHIRT_D)
    d.rectangle([x0, y0 - 54, x0 + 5, y0 - 47], fill=SKIN_OLD)
    d.rectangle([x0 + 37, y0 - 82, x0 + 42, y0 - 60], fill=SHIRT_D)
    d.rectangle([x0 + 37, y0 - 60, x0 + 44, y0 - 54], fill=SKIN_OLD)
    _face_base(d, x0, y0, skin=SKIN_OLD, skin_l=(238, 192, 150), skin_d=(200, 150, 108))
    # keriput dahi + kantung mata
    d.line([(x0 + 10, y0 - 107), (x0 + 32, y0 - 107)], fill=(200, 150, 108))
    d.line([(x0 + 12, y0 - 104), (x0 + 30, y0 - 104)], fill=(200, 150, 108))
    d.line([(x0 + 12, y0 - 93), (x0 + 16, y0 - 93)], fill=(200, 150, 108))
    d.line([(x0 + 26, y0 - 93), (x0 + 30, y0 - 93)], fill=(200, 150, 108))
    # rambut abu-abu menipis
    d.rectangle([x0 + 8, y0 - 117, x0 + 34, y0 - 111], fill=(172, 172, 168))
    d.rectangle([x0 + 5, y0 - 111, x0 + 9, y0 - 102], fill=(172, 172, 168))
    d.rectangle([x0 + 33, y0 - 111, x0 + 37, y0 - 102], fill=(172, 172, 168))
    d.rectangle([x0 + 10, y0 - 116, x0 + 22, y0 - 114], fill=(200, 200, 196))
    # alis: stern = miring ke dalam
    if expr == "stern":
        d.line([(x0 + 11, y0 - 106), (x0 + 17, y0 - 103)], fill=DARK, width=2)
        d.line([(x0 + 31, y0 - 106), (x0 + 25, y0 - 103)], fill=DARK, width=2)
    elif expr == "sad":
        d.line([(x0 + 11, y0 - 103), (x0 + 17, y0 - 106)], fill=DARK, width=2)
        d.line([(x0 + 31, y0 - 103), (x0 + 25, y0 - 106)], fill=DARK, width=2)
    else:
        d.rectangle([x0 + 11, y0 - 105, x0 + 17, y0 - 103], fill=DARK)
        d.rectangle([x0 + 25, y0 - 105, x0 + 31, y0 - 103], fill=DARK)
    _eyes(d, x0, y0, blink)
    # kumis + janggut abu-abu
    d.rectangle([x0 + 14, y0 - 92, x0 + 28, y0 - 90], fill=(150, 150, 146))
    d.rectangle([x0 + 17, y0 - 84, x0 + 25, y0 - 83], fill=(150, 150, 146))
    _mouth(d, x0, y0, mouth, expr)

def draw_sari(d, x0, gy, mouth="closed", blink=False, expr="neutral", bob=0):
    """Sari: rambut panjang hitam, kebaya ungu, rok batik."""
    y0 = gy - bob
    KEB, KEB_D, KEB_L = (168, 90, 190), (132, 66, 152), (196, 130, 214)
    d.ellipse([x0 - 2, gy - 2, x0 + 42, gy + 3], fill=SHADOW)
    # rambut belakang
    d.rectangle([x0 + 2, y0 - 118, x0 + 40, y0 - 60], fill=(24, 20, 18))
    d.rectangle([x0 + 2, y0 - 118, x0 + 8, y0 - 60], fill=(44, 38, 34))
    # rok batik
    d.rectangle([x0 + 6, y0 - 46, x0 + 36, y0 - 10], fill=(90, 60, 110))
    for bx in range(x0 + 10, x0 + 34, 8):
        d.point((bx, y0 - 20), fill=(140, 110, 160))
        d.point((bx + 3, y0 - 16), fill=(140, 110, 160))
    d.rectangle([x0 + 4, y0 - 10, x0 + 38, y0], fill=(70, 46, 88))
    # kebaya
    d.rectangle([x0 + 4, y0 - 84, x0 + 38, y0 - 46], fill=KEB)
    d.rectangle([x0 + 34, y0 - 84, x0 + 38, y0 - 46], fill=KEB_D)
    d.rectangle([x0 + 4, y0 - 84, x0 + 8, y0 - 46], fill=KEB_L)
    d.line([(x0 + 21, y0 - 84), (x0 + 21, y0 - 46)], fill=KEB_D)
    d.point((x0 + 21, y0 - 72), fill=(244, 204, 64))
    d.rectangle([x0, y0 - 82, x0 + 5, y0 - 54], fill=KEB_D)
    d.rectangle([x0, y0 - 54, x0 + 5, y0 - 47], fill=SKIN)
    d.rectangle([x0 + 37, y0 - 82, x0 + 42, y0 - 54], fill=KEB_D)
    d.rectangle([x0 + 37, y0 - 54, x0 + 42, y0 - 47], fill=SKIN)
    # rambut depan membingkai wajah
    _face_base(d, x0, y0)
    d.rectangle([x0 + 5, y0 - 118, x0 + 37, y0 - 108], fill=(24, 20, 18))
    d.rectangle([x0 + 5, y0 - 108, x0 + 10, y0 - 84], fill=(24, 20, 18))
    d.rectangle([x0 + 32, y0 - 108, x0 + 37, y0 - 84], fill=(24, 20, 18))
    d.rectangle([x0 + 8, y0 - 117, x0 + 18, y0 - 115], fill=(52, 44, 40))
    # anting
    d.point((x0 + 5, y0 - 94), fill=(244, 204, 64))
    d.point((x0 + 37, y0 - 94), fill=(244, 204, 64))
    d.rectangle([x0 + 11, y0 - 105, x0 + 17, y0 - 103], fill=DARK)
    d.rectangle([x0 + 25, y0 - 105, x0 + 31, y0 - 103], fill=DARK)
    _eyes(d, x0, y0, blink, lash=True)
    d.ellipse([x0 + 12, y0 - 94, x0 + 15, y0 - 92], fill=BLUSH)
    d.ellipse([x0 + 27, y0 - 94, x0 + 30, y0 - 92], fill=BLUSH)
    _mouth(d, x0, y0, mouth, expr)
