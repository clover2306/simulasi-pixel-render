#!/usr/bin/env python3
"""Lapisan visual v3 di atas v2:
1. MG Penjelas + Blur Map (M1-M8)
2. Vignette Tampil Samping gaya panggung pixel (V1-V9, termasuk V9 panggung ganda)
3. Gating & routing helper untuk render_full.py dan v2_effects.py.
"""
import json
import math
import os
from PIL import Image, ImageDraw, ImageEnhance
from world import (W, H, GW, GH, FIELD, FIELD_BRIGHT, FIELD_DRY,
                   RIVER, RIVER_L, RIVER_D, BANK, PATH, load_font, text_outline)
from assets import SKIN, SKIN_L, SKIN_D, SKIN_OLD, EYE, BLUSH, BOOT, DARK, shade

PROJ = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(PROJ, "moments-v3.json"), encoding="utf-8") as _fh:
    _MOMENTS_DATA = json.load(_fh)

MOMENTS = _MOMENTS_DATA["moments"]

# Grid vignette 320x180 -> 4x NEAREST ke 1280x720 (karakter ~88px grid = 352px layar)
VG_W, VG_H, VG_SCALE = 320, 180, 4
STAGE_TOP = 50      # di bawah HUD (y=0..50)
STAGE_BOT = 650     # di atas zona caption (y=650..720)
RIVER_Y0 = 149      # grid y: 149*4 = 596..644 (tepat di atas zona caption)
RIVER_Y1 = 161

# Palet v2 + aksen panggung
COL_GOLD = (255, 220, 120)
COL_GREEN = (140, 230, 140)
COL_RED = (235, 92, 82)
COL_CREAM = (255, 244, 214)
COL_WHITE = (248, 246, 240)
COL_DARK = (22, 20, 24)
COL_NAVY = (26, 36, 52)
COL_OUTLINE = (26, 20, 18)
COL_CURTAIN = (58, 34, 22)
COL_CURTAIN_L = (80, 48, 32)
COL_CURTAIN_D = (36, 20, 14)

_FONT_CACHE = {}


def _font(sz):
    if sz not in _FONT_CACHE:
        _FONT_CACHE[sz] = load_font(sz)
    return _FONT_CACHE[sz]


def get_moment(t_abs):
    """Kembalikan dict momen v3 yang aktif pada waktu absolut t_abs, atau None."""
    for m in MOMENTS:
        if m["t0"] <= t_abs < m["t1"]:
            return m
    return None


def v3_active(t_abs):
    """True bila jendela momen v3 aktif (untuk gating lapis v2)."""
    return get_moment(t_abs) is not None


def _clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _ease(t):
    t = _clamp01(t)
    return t * t * (3.0 - 2.0 * t)


def _wrap_lines(d, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if d.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


# =====================================================================
# PRIMITIF UI (1280x720): BLUR, CHIP, KARTU, PELAT, PAPAN, BUBBLE, TIRAI
# =====================================================================

def pixel_blur(img, factor=8, darken=0.48):
    """Downscale 8x BILINEAR -> upscale NEAREST + gelapkan sedikit agar tetap pixel-art."""
    small = img.resize((max(1, W // factor), max(1, H // factor)), Image.BILINEAR)
    px = small.resize((W, H), Image.NEAREST)
    return ImageEnhance.Brightness(px).enhance(darken)


def draw_chip(d, cx, cy, text, sz=14, border=COL_GOLD, bg=COL_DARK, fg=COL_CREAM,
              pad_x=16, pad_y=8, anchor="center"):
    """Gambar chip teks berbingkai. Semua teks MG/vignette berada dalam wadah."""
    f = _font(sz)
    tw = int(d.textlength(text, font=f))
    bw = tw + pad_x * 2
    bh = sz + pad_y * 2
    if anchor == "center":
        x0 = int(cx - bw // 2)
    elif anchor == "right":
        x0 = int(cx - bw)
    else:
        x0 = int(cx)
    y0 = int(cy)
    d.rectangle([x0 - 2, y0 - 2, x0 + bw + 2, y0 + bh + 2], fill=COL_OUTLINE)
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=bg, outline=border, width=3)
    d.text((x0 + pad_x, y0 + pad_y + 1), text, font=f, fill=fg)
    return (x0, y0, x0 + bw, y0 + bh)


def draw_card_panel(d, x0, y0, x1, y1, border=COL_GOLD, bg=(26, 28, 38)):
    """Panel kartu MG bergaya pixel bertingkat."""
    d.rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], fill=(12, 10, 14))
    d.rectangle([x0, y0, x1, y1], fill=bg, outline=border, width=4)
    d.rectangle([x0 + 8, y0 + 8, x1 - 8, y1 - 8], outline=(48, 52, 70), width=2)


def draw_nameplate(d, x, y, name, status, accent=COL_GREEN, align="left"):
    """Pelat NAMA / STATUS dua baris gaya tangkapan layar Mrfy (maks ~14 char/baris)."""
    f_name = _font(18)
    f_stat = _font(11)
    w1 = int(d.textlength(name, font=f_name))
    w2 = int(d.textlength(status, font=f_stat))
    bw = max(w1, w2) + 34
    bh = 60
    if align == "right":
        x0 = x - bw
    elif align == "center":
        x0 = x - bw // 2
    else:
        x0 = x
    y0 = y
    d.rectangle([x0 + 4, y0 + 4, x0 + bw + 4, y0 + bh + 4], fill=(10, 12, 16))
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=COL_NAVY, outline=accent, width=3)
    d.rectangle([x0 + 3, y0 + 3, x0 + 9, y0 + bh - 3], fill=accent)
    d.text((x0 + 18, y0 + 10), name, font=f_name, fill=accent)
    d.text((x0 + 18, y0 + 38), status, font=f_stat, fill=COL_WHITE)
    return (x0, y0, x0 + bw, y0 + bh)


def draw_signboard(d, cx, y_bottom, lines, sz=11, style="tan", post_h=24):
    """Papan nama properti di atas tiang kayu."""
    f = _font(sz)
    if isinstance(lines, str):
        lines = [lines]
    mw = max(int(d.textlength(ln, font=f)) for ln in lines)
    bw = mw + 22
    lh = sz + 7
    bh = len(lines) * lh + 12
    x0 = int(cx - bw // 2)
    y0 = int(y_bottom - post_h - bh)
    # tiang kayu
    d.rectangle([cx - 5, y0 + bh - 2, cx + 5, y_bottom], fill=(96, 62, 34), outline=COL_OUTLINE, width=2)
    if style == "blue":
        bg, brd, fg = (38, 62, 92), (160, 114, 66), COL_WHITE
    elif style == "warn":
        bg, brd, fg = (224, 196, 140), (140, 50, 42), (160, 36, 30)
    else:
        bg, brd, fg = (214, 184, 132), (126, 86, 48), (44, 30, 20)
    d.rectangle([x0 - 3, y0 - 3, x0 + bw + 3, y0 + bh + 3], fill=COL_OUTLINE)
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=bg, outline=brd, width=3)
    for i, ln in enumerate(lines):
        lw = int(d.textlength(ln, font=f))
        d.text((cx - lw // 2, y0 + 8 + i * lh), ln, font=f, fill=fg)


def draw_bubble(d, cx, y_bot, text, kind="speech", max_w=380, sz=12, tail_dir="down",
                icon_fn=None):
    """Speech bubble atau thought bubble berbingkai pixel."""
    f = _font(sz)
    lines = _wrap_lines(d, text, f, max_w)
    tw = max(int(d.textlength(ln, font=f)) for ln in lines) if lines else 40
    icon_w = 34 if icon_fn else 0
    bw = tw + 28 + icon_w
    lh = sz + 8
    bh = max(40, len(lines) * lh + 20)
    x0 = max(24, min(W - bw - 24, int(cx - bw // 2)))
    y0 = max(STAGE_TOP + 12, int(y_bot - bh - 18))

    if kind == "thought":
        # awan pixel + dua bulatan kecil
        d.rounded_rectangle([x0 - 3, y0 - 3, x0 + bw + 3, y0 + bh + 3], radius=16, fill=COL_OUTLINE)
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=14,
                            fill=(248, 248, 255), outline=(90, 100, 120), width=3)
        tx = max(x0 + 20, min(x0 + bw - 20, cx))
        d.ellipse([tx - 7, y0 + bh + 3, tx + 7, y0 + bh + 15], fill=(248, 248, 255), outline=COL_OUTLINE, width=2)
        d.ellipse([tx - 4, y0 + bh + 17, tx + 4, y0 + bh + 25], fill=(248, 248, 255), outline=COL_OUTLINE, width=2)
    else:
        d.rectangle([x0 - 3, y0 - 3, x0 + bw + 3, y0 + bh + 3], fill=COL_OUTLINE)
        d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=(255, 252, 242), outline=COL_OUTLINE, width=2)
        if tail_dir == "down":
            tx = max(x0 + 20, min(x0 + bw - 20, cx))
            d.polygon([(tx - 10, y0 + bh), (tx + 10, y0 + bh), (tx, y0 + bh + 16)],
                      fill=(255, 252, 242), outline=COL_OUTLINE)
            d.line([(tx - 8, y0 + bh), (tx + 8, y0 + bh)], fill=(255, 252, 242), width=3)

    if icon_fn:
        icon_fn(d, x0 + 12, y0 + bh // 2 - 12)
    for i, ln in enumerate(lines):
        d.text((x0 + 14 + icon_w, y0 + 11 + i * lh), ln, font=f, fill=(30, 24, 20))


def draw_curtains(d, t_abs, t0, t1, dur=0.45):
    """Tirai panggung pixel cokelat tua membuka di awal dan menutup di akhir.
    Menutupi y=50..652 (di bawah HUD, di atas zona caption). Saat terbuka penuh: 0px."""
    dt_in = t_abs - t0
    dt_out = t1 - t_abs
    closed = 0.0
    if dt_in < dur:
        closed = max(closed, 1.0 - _ease(dt_in / dur))
    if dt_out < dur:
        closed = max(closed, 1.0 - _ease(dt_out / dur))
    if closed <= 0.005:
        return
    half_w = int(round((W // 2) * closed))
    # gambar lipatan tirai kiri & kanan
    for side in ("left", "right"):
        if side == "left":
            rx0, rx1 = 0, half_w
        else:
            rx0, rx1 = W - half_w, W
        if rx1 <= rx0:
            continue
        d.rectangle([rx0, STAGE_TOP, rx1, STAGE_BOT], fill=COL_CURTAIN)
        # lipatan vertikal bergaya pixel
        stripe = 32
        for sx in range(rx0, rx1, stripe):
            sx_e = min(rx1, sx + 12)
            d.rectangle([sx, STAGE_TOP, sx_e, STAGE_BOT], fill=COL_CURTAIN_L)
            sx_d0 = min(rx1, sx + 18)
            sx_d1 = min(rx1, sx + 28)
            if sx_d1 > sx_d0:
                d.rectangle([sx_d0, STAGE_TOP, sx_d1, STAGE_BOT], fill=COL_CURTAIN_D)
        # lis emas di tepi dalam tirai
        edge_x = rx1 - 8 if side == "left" else rx0
        d.rectangle([edge_x, STAGE_TOP, edge_x + 8, STAGE_BOT], fill=(196, 152, 66))
        d.rectangle([edge_x + (6 if side == "left" else 0), STAGE_TOP,
                     edge_x + (8 if side == "left" else 2), STAGE_BOT], fill=COL_OUTLINE)


# =====================================================================
# ASET & TOKOH VIGNETTE (GRID 320x180 -> 4x NEAREST = 1280x720)
# =====================================================================

def _px_rect(d, x0, y0, x1, y1, fill, out=COL_OUTLINE):
    if out:
        d.rectangle([x0 - 1, y0 - 1, x1 + 1, y1 + 1], fill=out)
    d.rectangle([x0, y0, x1, y1], fill=fill)


def _draw_mini_face(d, cx, cy, who="kevin"):
    """Wajah ikon mini (untuk panel M1)."""
    s = 28
    x0, y0 = cx - s, cy - s
    hair = (30, 26, 22) if who == "kevin" else (182, 182, 178)
    skin = SKIN if who == "kevin" else SKIN_OLD
    d.rectangle([x0 - 3, y0 - 3, x0 + s * 2 + 3, y0 + s * 2 + 3], fill=COL_OUTLINE)
    d.rectangle([x0, y0, x0 + s * 2, y0 + s * 2], fill=skin)
    d.rectangle([x0, y0, x0 + s * 2, y0 + 16], fill=hair)
    if who == "mulyadi":
        d.rectangle([x0 + 14, y0 + 2, x0 + 42, y0 + 10], fill=(208, 208, 204))
        d.rectangle([x0 + 12, y0 + 38, x0 + 44, y0 + 43], fill=(150, 150, 146))
    for ex in (x0 + 14, x0 + 36):
        d.rectangle([ex, y0 + 22, ex + 6, y0 + 30], fill=COL_OUTLINE)
    d.rectangle([x0 + 18, y0 + 44, x0 + 38, y0 + 48], fill=COL_OUTLINE)


def _draw_stage_bg(img, mood="day", left_dry=False, right_dry=False, f=0):
    """Latar belakang panggung 320x180: langit ber-dither, bukit, sawah kiri/kanan, jalan, apron caption."""
    d = ImageDraw.Draw(img)
    if mood == "drought":
        sky_top, sky_mid, sky_bot = (130, 150, 182), (218, 176, 108), (242, 206, 134)
        hill1, hill2 = (146, 134, 96), (168, 150, 104)
    elif mood == "dusk":
        sky_top, sky_mid, sky_bot = (44, 52, 82), (88, 96, 126), (138, 126, 132)
        hill1, hill2 = (56, 70, 68), (70, 84, 74)
    elif mood == "night":
        sky_top, sky_mid, sky_bot = (14, 18, 38), (24, 32, 62), (38, 48, 82)
        hill1, hill2 = (22, 34, 42), (30, 46, 44)
    elif mood == "warm_eve":
        sky_top, sky_mid, sky_bot = (66, 48, 88), (192, 108, 66), (244, 176, 98)
        hill1, hill2 = (82, 92, 62), (102, 114, 70)
    else:  # day
        sky_top, sky_mid, sky_bot = (92, 156, 224), (136, 192, 240), (176, 218, 246)
        hill1, hill2 = (92, 148, 84), (112, 170, 92)

    # langit dengan pita dither horizontal gaya Mrfy
    for y in range(13, 106):
        t = (y - 13) / 93.0
        if t < 0.5:
            u = t * 2
            c = tuple(int(sky_top[i] + (sky_mid[i] - sky_top[i]) * u) for i in range(3))
        else:
            u = (t - 0.5) * 2
            c = tuple(int(sky_mid[i] + (sky_bot[i] - sky_mid[i]) * u) for i in range(3))
        d.line([(0, y), (VG_W, y)], fill=c)

    if mood == "night":
        for (sx, sy) in [(26, 22), (72, 34), (165, 20), (198, 28), (235, 19), (288, 36), (55, 58), (222, 52)]:
            d.point((sx, sy), fill=(250, 244, 200))
        d.ellipse([112, 20, 130, 38], fill=(248, 236, 180))
        d.ellipse([117, 18, 134, 35], fill=sky_top)
    elif mood == "drought":
        d.ellipse([246, 22, 276, 52], fill=(255, 226, 120))
        d.ellipse([251, 27, 271, 47], fill=(255, 248, 190))
    elif mood == "dusk":
        d.ellipse([36, 72, 68, 104], fill=(216, 134, 88))
    elif mood == "warm_eve":
        d.ellipse([142, 62, 178, 98], fill=(255, 224, 146))
    else:
        # awan pixel
        for (cx, cy) in [(48 + (f // 8) % 20, 30), (190 + (f // 10) % 16, 36)]:
            d.rectangle([cx, cy, cx + 26, cy + 7], fill=(242, 248, 255))
            d.rectangle([cx + 6, cy - 4, cx + 20, cy], fill=(242, 248, 255))

    # bukit jauh
    for x in range(VG_W):
        h1 = int(92 + 9 * math.sin(x / 38.0))
        h2 = int(99 + 7 * math.cos(x / 27.0 + 1.1))
        d.line([(x, h1), (x, 114)], fill=hill1)
        d.line([(x, h2), (x, 114)], fill=hill2)

    # latar sawah kiri (Sinarbaru = hijau terang) & kanan (Tanjungsari = hijau biasa / kering)
    col_l = FIELD_DRY if left_dry else FIELD_BRIGHT
    col_r = FIELD_DRY if right_dry else FIELD
    if mood == "night":
        col_l = shade(col_l, 0.45)
        col_r = shade(col_r, 0.45)
    elif mood == "dusk":
        col_l = shade(col_l, 0.72)
        col_r = shade(col_r, 0.68)

    d.rectangle([0, 108, VG_W // 2, 132], fill=col_l)
    d.rectangle([VG_W // 2, 108, VG_W, 132], fill=col_r)
    # garis alur sawah
    for ry in (114, 120, 126):
        d.line([(0, ry), (VG_W // 2 - 1, ry)], fill=shade(col_l, 0.86))
        d.line([(VG_W // 2, ry), (VG_W, ry)], fill=shade(col_r, 0.86))
    # retakan bila kering
    for side_dry, x_start in ((left_dry, 12), (right_dry, VG_W // 2 + 12)):
        if side_dry:
            for k in range(5):
                rx = x_start + k * 28
                ry = 113 + (k % 2) * 8
                d.line([(rx, ry), (rx + 6, ry + 3), (rx + 3, ry + 7)], fill=shade(FIELD_DRY, 0.62))

    # jalan panggung tanah (tempat tokoh berpijak)
    road_c = (182, 148, 100) if mood != "night" else (82, 68, 52)
    road_t = (202, 168, 118) if mood != "night" else (96, 80, 62)
    d.rectangle([0, 132, VG_W, 149], fill=road_c)
    d.line([(0, 132), (VG_W, 132)], fill=road_t)
    for k in range(28):
        px_ = (k * 37 + 11) % VG_W
        py_ = 136 + (k * 13) % 10
        d.point((px_, py_), fill=shade(road_c, 0.76))

    # apron gelap di bawah y=162 (zona caption 648..720 bersih)
    d.rectangle([0, RIVER_Y1, VG_W, VG_H], fill=(22, 24, 20))
    d.line([(0, RIVER_Y1 + 1), (VG_W, RIVER_Y1 + 1)], fill=(44, 52, 38))


def _draw_river_strip(img, state="normal", f=0, x0=0, x1=VG_W, dim=False):
    """Strip sungai melintang di bagian bawah panggung (y=149..161, tepat di atas zona caption).
    Tanpa angka, tanpa skala, tanpa garis ukur."""
    d = ImageDraw.Draw(img)
    bank_c = BANK if not dim else (140, 134, 124)
    water_c = RIVER if not dim else (82, 102, 122)
    water_d = RIVER_D if not dim else (64, 82, 100)
    water_l = RIVER_L if not dim else (120, 140, 158)

    d.rectangle([x0, RIVER_Y0, x1, RIVER_Y1], fill=bank_c)
    d.line([(x0, RIVER_Y0), (x1, RIVER_Y0)], fill=(54, 96, 46) if not dim else (66, 74, 66))

    if state == "drought":
        # surut: tepi pasir/lumpur lebar, aliran sempit di tengah
        d.rectangle([x0, RIVER_Y0 + 5, x1, RIVER_Y0 + 8], fill=water_d)
        d.line([(x0, RIVER_Y0 + 6), (x1, RIVER_Y0 + 6)], fill=water_c)
        for k in range(x0 + 8, x1 - 8, 22):
            d.point((k + (f // 12) % 4, RIVER_Y0 + 6), fill=water_l)
            d.line([(k, RIVER_Y0 + 2), (k + 4, RIVER_Y0 + 3)], fill=shade(bank_c, 0.75))
    elif state == "clear":
        d.rectangle([x0, RIVER_Y0 + 2, x1, RIVER_Y1 - 2], fill=water_c)
        d.line([(x0, RIVER_Y0 + 2), (x1, RIVER_Y0 + 2)], fill=water_d)
        for k in range(x0 + 6, x1 - 6, 18):
            rx = x0 + ((k - x0 + f // 2) % max(1, (x1 - x0 - 6)))
            d.line([(rx, RIVER_Y0 + 4), (rx + 5, RIVER_Y0 + 4)], fill=water_l)
            d.point((rx + 2, RIVER_Y0 + 7), fill=(242, 250, 255))
    else:  # normal
        d.rectangle([x0, RIVER_Y0 + 2, x1, RIVER_Y1 - 2], fill=water_c)
        d.line([(x0, RIVER_Y0 + 2), (x1, RIVER_Y0 + 2)], fill=water_d)
        for k in range(x0 + 8, x1 - 8, 20):
            rx = x0 + ((k - x0 + f // 3) % max(1, (x1 - x0 - 6)))
            d.line([(rx, RIVER_Y0 + 5), (rx + 4, RIVER_Y0 + 5)], fill=water_l)


def _draw_house_bg(d, x, gy, abandoned=False, lit=True, dim=False):
    """Rumah desa latar ukuran sedang di grid 320x180."""
    wall = (164, 114, 68) if not abandoned else (112, 102, 94)
    roof = (196, 134, 72) if not abandoned else (106, 76, 66)
    win = (250, 222, 128) if (lit and not abandoned) else (44, 42, 48)
    if dim:
        wall, roof = shade(wall, 0.6), shade(roof, 0.6)
        win = (74, 72, 70)
    _px_rect(d, x, gy - 22, x + 26, gy, wall)
    d.polygon([(x - 3, gy - 22), (x + 13, gy - 35), (x + 29, gy - 22)],
              fill=roof, outline=COL_OUTLINE)
    d.rectangle([x + 4, gy - 16, x + 10, gy - 10], fill=win, outline=COL_OUTLINE)
    d.rectangle([x + 15, gy - 15, x + 22, gy], fill=(66, 46, 30), outline=COL_OUTLINE)


def _draw_pump_vig(d, cx, gy, working=True, broken=False, f=0, scale=1.0):
    """Pompa air besar untuk panggung vignette (grid 320x180)."""
    s = scale
    x0 = int(cx - 14 * s)
    y0 = int(gy - 28 * s)
    # alas
    _px_rect(d, x0, gy - int(5 * s), x0 + int(28 * s), gy, (86, 86, 92))
    # badan pompa merah
    shake = ((f // 2) % 3 - 1) if broken else (0 if not working else (f // 6) % 2)
    _px_rect(d, x0 + int(4 * s), y0 + int(6 * s) + shake,
             x0 + int(20 * s), gy - int(4 * s), (190, 58, 48))
    d.rectangle([x0 + int(5 * s), y0 + int(7 * s) + shake,
                 x0 + int(19 * s), y0 + int(10 * s) + shake], fill=(224, 92, 80))
    # roda flywheel
    rx0, ry0 = x0 + int(19 * s), y0 + int(8 * s) + shake
    d.ellipse([rx0, ry0, rx0 + int(10 * s), ry0 + int(10 * s)],
              fill=(70, 72, 80), outline=COL_OUTLINE)
    d.ellipse([rx0 + int(3 * s), ry0 + int(3 * s), rx0 + int(7 * s), ry0 + int(7 * s)],
              fill=(190, 194, 200))
    # pipa keluar ke kanan/kiri
    _px_rect(d, x0 - int(8 * s), y0 + int(10 * s), x0 + int(4 * s), y0 + int(14 * s), (110, 114, 122))
    if working and not broken:
        # semburan air biru
        for k in range(3):
            wy = y0 + int(15 * s) + ((f + k * 4) % 10)
            d.rectangle([x0 - int(7 * s), wy, x0 - int(4 * s), wy + 3], fill=RIVER_L)
    if broken:
        # asap hitam/abu mengepul
        for k in range(3):
            sy = y0 - 4 - ((f // 2 + k * 7) % 18)
            sx = cx + int(4 * math.sin((f + k * 5) / 5.0))
            r = 3 + k
            d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(120, 120, 126), outline=(60, 60, 66))


# ---------------- Tokoh Besar Vignette (~86px di grid 320x180 = 344px layar) ----------------

def _draw_big_head(d, cx, hy, skin, hair, hair_style="kevin", expr="neutral",
                   look="right", blink=False, moustache=False, headband=False, wrinkles=False):
    """Gambar kepala ekspresif besar (~28x28 grid px) dengan outline tebal & shading."""
    # kepala bulat-kotak khas Mrfy
    _px_rect(d, cx - 13, hy, cx + 13, hy + 26, skin)
    d.rectangle([cx - 12, hy + 1, cx - 9, hy + 25], fill=shade(skin, 1.07))
    d.rectangle([cx + 9, hy + 1, cx + 12, hy + 25], fill=shade(skin, 0.88))

    # rambut
    if hair_style == "kevin":
        _px_rect(d, cx - 14, hy - 5, cx + 14, hy + 6, hair)
        d.rectangle([cx - 11, hy - 3, cx + 4, hy], fill=shade(hair, 1.5))
        d.rectangle([cx - 14, hy + 4, cx - 10, hy + 13], fill=hair)
        d.rectangle([cx + 10, hy + 4, cx + 14, hy + 11], fill=hair)
    elif hair_style == "mulyadi":
        _px_rect(d, cx - 14, hy - 4, cx + 14, hy + 3, hair)
        d.rectangle([cx - 5, hy - 3, cx + 5, hy + 2], fill=skin)  # menipis di tengah
        d.rectangle([cx - 14, hy + 2, cx - 10, hy + 13], fill=hair)
        d.rectangle([cx + 10, hy + 2, cx + 14, hy + 13], fill=hair)
    elif hair_style == "ujang":
        _px_rect(d, cx - 14, hy - 5, cx + 14, hy + 5, hair)
        if headband:
            _px_rect(d, cx - 14, hy + 3, cx + 14, hy + 7, (220, 56, 46))
            # simpul ikat kepala di sisi belakang
            kx = cx - 17 if look == "right" else cx + 14
            d.rectangle([kx, hy + 3, kx + 3, hy + 8], fill=(196, 44, 36), outline=COL_OUTLINE)
    elif hair_style == "sari":
        _px_rect(d, cx - 15, hy - 5, cx + 15, hy + 5, hair)
        _px_rect(d, cx - 15, hy + 3, cx - 10, hy + 34, hair)
        _px_rect(d, cx + 10, hy + 3, cx + 15, hy + 34, hair)

    if wrinkles:
        d.line([(cx - 8, hy + 6), (cx + 8, hy + 6)], fill=shade(skin, 0.8))

    # arah pandangan offset mata
    dx = 3 if look == "right" else (-3 if look == "left" else 0)
    ex1, ex2 = cx - 7 + dx, cx + 3 + dx
    ey = hy + 12

    # mata
    if blink:
        d.line([(ex1, ey + 2), (ex1 + 4, ey + 2)], fill=COL_OUTLINE)
        d.line([(ex2, ey + 2), (ex2 + 4, ey + 2)], fill=COL_OUTLINE)
    else:
        for ex in (ex1, ex2):
            d.rectangle([ex, ey, ex + 4, ey + 5], fill=(252, 250, 244))
            d.rectangle([ex + (2 if look == "right" else 1), ey + 1,
                         ex + (4 if look == "right" else 3), ey + 4], fill=COL_OUTLINE)
            d.point((ex + 1, ey + 1), fill=(255, 255, 255))

    # alis ekspresif
    if expr in ("confused", "shocked"):
        d.line([(ex1 - 1, ey - 4), (ex1 + 4, ey - 6)], fill=COL_OUTLINE, width=2)
        d.line([(ex2, ey - 6), (ex2 + 5, ey - 4)], fill=COL_OUTLINE, width=2)
    elif expr in ("stern", "stubborn"):
        d.line([(ex1 - 1, ey - 4), (ex1 + 5, ey - 2)], fill=COL_OUTLINE, width=2)
        d.line([(ex2 - 1, ey - 2), (ex2 + 5, ey - 4)], fill=COL_OUTLINE, width=2)
    elif expr in ("sad", "wavering"):
        d.line([(ex1 - 1, ey - 2), (ex1 + 4, ey - 4)], fill=COL_OUTLINE, width=2)
        d.line([(ex2, ey - 4), (ex2 + 5, ey - 2)], fill=COL_OUTLINE, width=2)
    else:
        d.line([(ex1, ey - 3), (ex1 + 4, ey - 3)], fill=COL_OUTLINE, width=2)
        d.line([(ex2, ey - 3), (ex2 + 4, ey - 3)], fill=COL_OUTLINE, width=2)

    # kumis Pak Mulyadi
    if moustache:
        d.rectangle([cx - 7 + dx, hy + 18, cx + 7 + dx, hy + 20], fill=(164, 164, 160), outline=COL_OUTLINE)

    # mulut
    my = hy + 21 + (1 if moustache else 0)
    if expr in ("shocked", "confused"):
        d.ellipse([cx - 3 + dx, my - 1, cx + 3 + dx, my + 3], fill=(120, 42, 38), outline=COL_OUTLINE)
    elif expr == "happy":
        d.line([(cx - 4 + dx, my), (cx + dx, my + 2), (cx + 4 + dx, my)], fill=COL_OUTLINE, width=2)
    elif expr in ("sad", "stubborn", "stern"):
        d.line([(cx - 4 + dx, my + 2), (cx + dx, my), (cx + 4 + dx, my + 2)], fill=COL_OUTLINE, width=2)
    else:
        d.line([(cx - 3 + dx, my + 1), (cx + 3 + dx, my + 1)], fill=COL_OUTLINE, width=2)


def draw_kevin_vig(d, cx, gy, look="right", expr="neutral", pose="idle", bob=0, blink=False):
    """Kevin besar (~86px tinggi) di grid 320x180."""
    y = gy - bob
    # bayangan pijakan
    d.ellipse([cx - 18, gy - 3, cx + 18, gy + 3], fill=(0, 0, 0))
    # kaki & sepatu
    _px_rect(d, cx - 10, y - 30, cx - 2, y - 7, (52, 58, 96))
    _px_rect(d, cx + 2, y - 30, cx + 10, y - 7, (52, 58, 96))
    _px_rect(d, cx - 11, y - 7, cx - 1, y, BOOT)
    _px_rect(d, cx + 1, y - 7, cx + 11, y, BOOT)
    # badan kemeja biru
    lean = 2 if pose == "listen" else 0
    _px_rect(d, cx - 13 + lean, y - 60, cx + 13 + lean, y - 30, (92, 160, 222))
    d.rectangle([cx + 7 + lean, y - 59, cx + 12 + lean, y - 31], fill=(66, 128, 184))
    # kerah putih
    d.polygon([(cx - 5 + lean, y - 60), (cx + lean, y - 53), (cx + 5 + lean, y - 60)], fill=(244, 244, 240))
    # lengan & prop
    if pose == "pull_lever":
        _px_rect(d, cx + 8, y - 56, cx + 22, y - 48, (66, 128, 184))
        _px_rect(d, cx + 20, y - 54, cx + 25, y - 47, SKIN)
    elif pose == "notebook":
        _px_rect(d, cx + 8 + lean, y - 54, cx + 19 + lean, y - 45, (66, 128, 184))
        _px_rect(d, cx + 15 + lean, y - 50, cx + 25 + lean, y - 40, (240, 232, 204))
    elif pose == "sit":
        pass
    else:
        _px_rect(d, cx - 17, y - 56, cx - 12, y - 34, (66, 128, 184))
        _px_rect(d, cx + 12, y - 56, cx + 17, y - 34, (66, 128, 184))
        # gulungan rencana di tangan
        _px_rect(d, cx - 20, y - 42, cx - 12, y - 32, (242, 234, 206))

    _draw_big_head(d, cx + lean, y - 86, SKIN, (30, 26, 22), "kevin", expr=expr, look=look, blink=blink)


def draw_mulyadi_vig(d, cx, gy, look="left", expr="stern", pose="idle", bob=0, blink=False):
    """Pak Mulyadi besar (~86px tinggi) di grid 320x180."""
    y = gy - bob
    d.ellipse([cx - 18, gy - 3, cx + 18, gy + 3], fill=(0, 0, 0))
    # kaki & sarung
    _px_rect(d, cx - 11, y - 32, cx + 11, y - 7, (96, 70, 50))
    for sy in range(y - 28, y - 8, 6):
        d.line([(cx - 10, sy), (cx + 10, sy)], fill=(130, 95, 65))
    _px_rect(d, cx - 10, y - 7, cx - 2, y, BOOT)
    _px_rect(d, cx + 2, y - 7, cx + 10, y, BOOT)
    # baju cokelat
    lean = -2 if pose == "lean" else 0
    _px_rect(d, cx - 13 + lean, y - 60, cx + 13 + lean, y - 32, (150, 100, 60))
    d.rectangle([cx + 7 + lean, y - 59, cx + 12 + lean, y - 33], fill=(118, 78, 46))
    # tongkat
    sx = cx - 18 if look == "left" else cx + 17
    tap_y = -2 if pose == "tap" else 0
    _px_rect(d, sx, y - 52 + tap_y, sx + 2, y + tap_y, (124, 88, 52))
    _px_rect(d, sx - 2, y - 55 + tap_y, sx + 4, y - 52 + tap_y, (158, 118, 70))

    if pose == "crossed":
        _px_rect(d, cx - 11, y - 48, cx + 11, y - 41, (118, 78, 46))
    elif pose == "shush":
        _px_rect(d, cx - 8, y - 62, cx - 2, y - 48, SKIN_OLD)
    elif pose == "block":
        _px_rect(d, cx - 22, y - 52, cx - 10, y - 45, (118, 78, 46))
    else:
        _px_rect(d, cx - 17 + lean, y - 55, cx - 12 + lean, y - 35, (118, 78, 46))
        _px_rect(d, cx + 12 + lean, y - 55, cx + 17 + lean, y - 35, (118, 78, 46))

    _draw_big_head(d, cx + lean, y - 86, SKIN_OLD, (176, 176, 172), "mulyadi",
                   expr=expr, look=look, blink=blink, moustache=True, wrinkles=True)


def draw_ujang_vig(d, cx, gy, look="left", expr="neutral", prop="hoe", pose="idle",
                   bob=0, blink=False, ghost=False):
    """Ujang besar (~84px tinggi). Mendukung mode ghost=True (bayangan putus-putus V9)."""
    if ghost:
        # Gambar ke buffer transparan lalu beri warna bayangan + kontur putus-putus
        buf = Image.new("RGBA", (VG_W, VG_H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(buf)
        draw_ujang_vig(bd, cx, gy, look=look, expr="sad", prop=prop, pose=pose, bob=bob, ghost=False)
        px = buf.load()
        for yy in range(max(0, gy - 95), min(VG_H, gy + 5)):
            for xx in range(max(0, cx - 34), min(VG_W, cx + 34)):
                r, g, b, a = px[xx, yy]
                if a == 0:
                    continue
                lum = int(0.3 * r + 0.59 * g + 0.11 * b)
                # efek bayangan putus-putus: outline hanya pada pola checker, isi semi-transparan
                is_dark = (r < 40 and g < 40 and b < 40)
                if is_dark:
                    if (xx + yy) % 2 == 0:
                        px[xx, yy] = (180, 196, 210, 190)
                    else:
                        px[xx, yy] = (0, 0, 0, 0)
                else:
                    px[xx, yy] = (min(255, lum + 20), min(255, lum + 30), min(255, lum + 45), 115)
        d._image.paste(buf, (0, 0), buf)
        return

    crouch = 12 if pose == "crouch" else 0
    y = gy - bob
    d.ellipse([cx - 17, gy - 3, cx + 17, gy + 3], fill=(0, 0, 0))
    # kaki
    step = 3 if pose == "walk" else 0
    _px_rect(d, cx - 10 - step, y - 28 + crouch // 2, cx - 2 - step, y - 7, (70, 70, 82))
    _px_rect(d, cx + 2 + step, y - 28 + crouch // 2, cx + 10 + step, y - 7, (70, 70, 82))
    _px_rect(d, cx - 11 - step, y - 7, cx - 1 - step, y, BOOT)
    _px_rect(d, cx + 1 + step, y - 7, cx + 11 + step, y, BOOT)
    # baju oranye
    _px_rect(d, cx - 12, y - 58 + crouch, cx + 12, y - 28 + crouch // 2, (226, 110, 60))
    d.rectangle([cx + 7, y - 57 + crouch, cx + 11, y - 29 + crouch // 2], fill=(188, 84, 44))
    # lengan + prop
    if prop == "hoe":
        # cangkul di bahu
        _px_rect(d, cx - 16, y - 54 + crouch, cx - 11, y - 34 + crouch, SKIN)
        d.line([(cx - 14, y - 52 + crouch), (cx + 16, y - 78 + crouch)], fill=(128, 88, 48), width=3)
        _px_rect(d, cx + 13, y - 82 + crouch, cx + 21, y - 73 + crouch, (170, 174, 182))
    elif prop == "wrench":
        ax = cx - 22 if look == "left" else cx + 12
        _px_rect(d, ax, y - 48 + crouch, ax + 10, y - 42 + crouch, SKIN)
        # kunci pas perak dengan rahang C jelas
        wx = ax - 6 if look == "left" else ax + 6
        _px_rect(d, wx, y - 56 + crouch, wx + 4, y - 36 + crouch, (196, 208, 224))
        _px_rect(d, wx - 2, y - 61 + crouch, wx + 6, y - 55 + crouch, (224, 232, 244))
        d.rectangle([wx + 1, y - 61 + crouch, wx + 3, y - 58 + crouch], fill=COL_OUTLINE)
    if pose == "throw":
        _px_rect(d, cx + 12, y - 62, cx + 22, y - 54, SKIN)

    _draw_big_head(d, cx, y - 84 + crouch, SKIN, (30, 26, 22), "ujang",
                   expr=expr, look=look, blink=blink, headband=True)


def draw_sari_vig(d, cx, gy, look="left", expr="neutral", lantern=False, bob=0, blink=False):
    """Sari (kebaya ungu, rambut hitam panjang) di panggung vignette."""
    y = gy - bob
    d.ellipse([cx - 15, gy - 3, cx + 15, gy + 3], fill=(0, 0, 0))
    _px_rect(d, cx - 10, y - 30, cx + 10, y - 4, (90, 60, 110))
    _px_rect(d, cx - 9, y - 4, cx + 9, y, BOOT)
    _px_rect(d, cx - 11, y - 56, cx + 11, y - 30, (168, 90, 190))
    if lantern:
        _px_rect(d, cx - 18, y - 48, cx - 10, y - 42, SKIN)
        _px_rect(d, cx - 21, y - 42, cx - 14, y - 32, (255, 224, 110))
        d.ellipse([cx - 26, y - 46, cx - 9, y - 28], outline=(255, 210, 90))
    _draw_big_head(d, cx, y - 82, SKIN, (24, 20, 18), "sari", expr=expr, look=look, blink=blink)


def draw_villager_vig(d, cx, gy, shirt=(180, 70, 60), hat="none", pose="idle",
                      look="left", scale=1.0, bob=0, prop=None, silhouette=False):
    """Warga generik untuk pemeran pendukung (3-4 variasi topi/pakaian)."""
    y = gy - bob
    h_tot = int(76 * scale)
    w_half = int(10 * scale)
    if silhouette:
        shirt = (52, 58, 72)
        skin_c = (68, 74, 88)
        pant_c = (40, 44, 56)
    else:
        skin_c = SKIN
        pant_c = (58, 62, 82)
    d.ellipse([cx - w_half - 3, gy - 2, cx + w_half + 3, gy + 2], fill=(0, 0, 0))
    _px_rect(d, cx - w_half + 2, y - int(26 * scale), cx - 1, y - 4, pant_c)
    _px_rect(d, cx + 1, y - int(26 * scale), cx + w_half - 2, y - 4, pant_c)
    _px_rect(d, cx - w_half, y - int(52 * scale), cx + w_half, y - int(26 * scale), shirt)
    if pose == "crossed":
        _px_rect(d, cx - w_half + 1, y - int(44 * scale), cx + w_half - 1, y - int(38 * scale), shade(shirt, 0.8))
    elif pose == "point":
        px_e = cx - int(20 * scale) if look == "left" else cx + int(20 * scale)
        d.line([(cx, y - int(46 * scale)), (px_e, y - int(50 * scale))], fill=skin_c, width=max(2, int(4 * scale)))
    elif pose == "bundle":
        _px_rect(d, cx + w_half - 2, y - int(54 * scale), cx + w_half + int(10 * scale), y - int(34 * scale), (168, 128, 78))
    if prop == "wrench":
        wx = cx - w_half - 4
        _px_rect(d, wx, y - int(50 * scale), wx + 3, y - int(36 * scale), (190, 200, 214))
    elif prop == "hoe":
        d.line([(cx + 4, y - int(42 * scale)), (cx + 14, y - int(68 * scale))], fill=(120, 86, 50), width=2)
        _px_rect(d, cx + 11, y - int(71 * scale), cx + 18, y - int(65 * scale), (180, 186, 196))
    elif prop == "lantern":
        _px_rect(d, cx - w_half - 6, y - int(42 * scale), cx - w_half - 1, y - int(34 * scale), (255, 224, 120))
    # kepala
    hy = y - h_tot
    hr = int(10 * scale)
    _px_rect(d, cx - hr, hy, cx + hr, hy + int(20 * scale), skin_c)
    if hat == "caping":
        d.polygon([(cx - int(18 * scale), hy + 4), (cx, hy - int(10 * scale)), (cx + int(18 * scale), hy + 4)],
                  fill=(206, 178, 108) if not silhouette else (64, 68, 82), outline=COL_OUTLINE)
    elif hat == "kain":
        _px_rect(d, cx - hr - 1, hy - 3, cx + hr + 1, hy + 5, (210, 202, 184) if not silhouette else (62, 66, 80))
    else:
        _px_rect(d, cx - hr - 1, hy - 3, cx + hr + 1, hy + 4, (36, 30, 26))
    if not silhouette:
        dx = -2 if look == "left" else 2
        d.point((cx - 4 + dx, hy + 9), fill=COL_OUTLINE)
        d.point((cx + 4 + dx, hy + 9), fill=COL_OUTLINE)


# =====================================================================
# RENDERER MG PENJELAS + BLUR (M1 - M8)
# =====================================================================

def _draw_padlock(d, cx, cy, locked=True):
    """Ikon gembok pixel di koordinat layar 1280x720."""
    # lengkung shackle
    sy = cy - 38 if locked else cy - 50
    d.arc([cx - 22, sy, cx + 22, sy + 44], 180, 360, fill=(200, 206, 216), width=8)
    _px_rect(d, cx - 28, cy - 12, cx + 28, cy + 36, (226, 178, 66))
    d.ellipse([cx - 6, cy + 2, cx + 6, cy + 14], fill=COL_OUTLINE)
    d.rectangle([cx - 3, cy + 10, cx + 3, cy + 24], fill=COL_OUTLINE)


def _draw_sack(d, cx, cy, scale=1.0, label=None):
    w, h = int(34 * scale), int(40 * scale)
    _px_rect(d, cx - w, cy - h, cx + w, cy + h, (198, 158, 96))
    d.polygon([(cx - w // 2, cy - h), (cx, cy - h - 14), (cx + w // 2, cy - h)],
              fill=(176, 136, 78), outline=COL_OUTLINE)
    d.line([(cx - w // 2, cy - h + 2), (cx + w // 2, cy - h + 2)], fill=(120, 74, 40), width=4)
    if label:
        draw_chip(d, cx, cy - 12, label, sz=11, border=(120, 84, 48), bg=(236, 214, 168), fg=(40, 26, 18))


def _draw_coin(d, cx, cy, r, col=(255, 216, 76)):
    d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=COL_OUTLINE)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col, outline=(180, 132, 32), width=3)
    d.rectangle([cx - max(2, r // 6), cy - r // 2, cx + max(2, r // 6), cy + r // 2], fill=(255, 244, 180))


def _render_mg_m1(d, p, t_abs):
    """M1 [A] GEMBOK DAN TIGA TUAS."""
    locks = ["WARGA", "LAHAN", "SUNGAI", "LUMBUNG", "CUACA"]
    # Ketukan 1: 5 gembok besar, lalu mengecil ke strip atas di ketukan 2-3
    compact = p >= 0.30
    ly = 192 if compact else 320
    for i, lbl in enumerate(locks):
        lx = 220 + i * 210
        if compact:
            d.arc([lx - 14, ly - 32, lx + 14, ly - 4], 180, 360, fill=(200, 206, 216), width=5)
            _px_rect(d, lx - 18, ly - 10, lx + 18, ly + 18, (226, 178, 66))
            d.ellipse([lx - 4, ly - 1, lx + 4, ly + 7], fill=COL_OUTLINE)
            draw_chip(d, lx, ly + 26, lbl, sz=11, border=(170, 176, 190))
        else:
            bounce = int(12 * max(0.0, 1.0 - abs(p * 10 - i * 0.6) * 2)) if p < 0.25 else 0
            _draw_padlock(d, lx, ly - bounce, locked=True)
            draw_chip(d, lx, ly + 54, lbl, sz=13, border=(200, 206, 216))
    if not compact:
        draw_chip(d, W // 2, 160, "SEMUA VARIABEL DIKUNCI SAMA", sz=16, border=COL_GOLD)
        return

    # Ketukan 2 & 3: Panel 3 tuas, baris wajah Kevin vs Mulyadi, tuas tarik ON (hijau) vs OFF (merah)
    d.rectangle([160, 272, 1120, 606], fill=(20, 22, 32), outline=(74, 80, 102), width=3)
    draw_chip(d, W // 2, 286, "PEMIMPIN MENGUBAH TIGA HAL", sz=14, border=COL_GOLD)

    levers = ["TEKNOLOGI", "RENCANA", "BELAJAR"]
    # sorot bertahap selama ketukan 2, lalu ON/OFF terkunci di ketukan 3
    pull = _ease((p - 0.56) / 0.20) if p >= 0.56 else 0.0

    # Baris Kevin & Mulyadi
    _draw_mini_face(d, 236, 395, "kevin")
    draw_chip(d, 236, 434, "KEVIN", sz=11, border=COL_GOLD)
    _draw_mini_face(d, 236, 525, "mulyadi")
    draw_chip(d, 236, 564, "MULYADI", sz=11, border=COL_GREEN)

    for j, lv in enumerate(levers):
        cx = 470 + j * 240
        hl = (p < 0.65 and int((p - 0.30) / 0.11) == j)
        draw_chip(d, cx, 326, lv, sz=13, border=COL_GOLD if hl or pull > 0.5 else (110, 116, 136))

        # Tuas Kevin (ON -> hijau)
        slot_k = (cx - 40, 384, cx + 40, 412)
        _px_rect(d, *slot_k, (36, 40, 54))
        kx = int(cx - 24 + 48 * pull)
        k_col = (80, 210, 110) if pull > 0.5 else (150, 156, 170)
        _px_rect(d, kx - 12, 378, kx + 12, 418, k_col)
        if pull > 0.7:
            d.text((cx + 52, 391), "ON", font=_font(12), fill=COL_GREEN)

        # Tuas Mulyadi (OFF -> merah)
        slot_m = (cx - 40, 514, cx + 40, 542)
        _px_rect(d, *slot_m, (36, 40, 54))
        mx = int(cx + 24 - 48 * pull)
        m_col = (220, 74, 68) if pull > 0.5 else (150, 156, 170)
        _px_rect(d, mx - 12, 508, mx + 12, 548, m_col)
        if pull > 0.7:
            d.text((cx + 52, 521), "OFF", font=_font(12), fill=COL_RED)


def _draw_lumbung(d, cx, y_bot, fill_frac, name, accent):
    """Lumbung padi pixel berpotongan isi."""
    _px_rect(d, cx - 95, y_bot - 170, cx + 95, y_bot, (150, 102, 56))
    d.polygon([(cx - 115, y_bot - 170), (cx, y_bot - 240), (cx + 115, y_bot - 170)],
              fill=(186, 128, 60), outline=COL_OUTLINE)
    # jendela isi padi
    wx0, wy0, wx1, wy1 = cx - 64, y_bot - 146, cx + 64, y_bot - 18
    _px_rect(d, wx0, wy0, wx1, wy1, (38, 30, 24))
    fill_h = int((wy1 - wy0 - 6) * _clamp01(fill_frac))
    if fill_h > 0:
        d.rectangle([wx0 + 4, wy1 - fill_h - 2, wx1 - 4, wy1 - 2], fill=(238, 198, 74))
        d.rectangle([wx0 + 4, wy1 - fill_h - 2, wx1 - 4, wy1 - fill_h + 6], fill=(252, 224, 118))
    draw_chip(d, cx, y_bot + 16, name, sz=14, border=accent)


def _render_mg_m2(d, p, t_abs):
    """M2 [A] LUMBUNG TERKURAS JADI MODAL."""
    drain = _ease((p - 0.30) / 0.40) if p >= 0.30 else 0.0
    left_fill = 0.92 - 0.42 * drain  # turun hampir separuh
    _draw_lumbung(d, 360, 520, left_fill, "SINARBARU", COL_GOLD)
    _draw_lumbung(d, 920, 520, 0.92, "TANJUNGSARI", COL_GREEN)

    if p >= 0.32:
        items = ["POMPA", "BIBIT", "PELATIHAN"]
        prog = _ease((p - 0.32) / 0.35)
        for i, lbl in enumerate(items):
            iy = int(340 - 150 * prog + i * 74)
            ix = int(495 + 110 * prog)
            draw_chip(d, ix, iy, lbl, sz=13, border=COL_GOLD, bg=(42, 48, 68), anchor="left")
            d.line([(455, 400), (ix - 6, iy + 14)], fill=COL_GOLD, width=3)

    if p >= 0.67:
        draw_chip(d, 360, 150, "MODAL DI MUKA", sz=13, border=COL_GOLD)
        draw_chip(d, 920, 150, "TETAP PENUH", sz=13, border=COL_GREEN)


def _draw_rice_stalk(d, cx, y_bot, rich=True, scale=1.0):
    """Gambar tangkai padi detail (biasa vs unggul)."""
    h = int(200 * scale)
    bend = 42 if rich else 18
    pts = [(cx, y_bot), (cx + 8, y_bot - h // 2), (cx + bend, y_bot - h)]
    d.line(pts, fill=(130, 184, 68) if rich else (140, 170, 88), width=int(6 * scale))
    # daun
    d.line([(cx + 4, y_bot - h // 3), (cx - 48, y_bot - h // 2)], fill=(96, 164, 64), width=int(5 * scale))
    d.line([(cx + 6, y_bot - h // 2), (cx + 56, y_bot - h // 2 - 20)], fill=(96, 164, 64), width=int(5 * scale))
    # bulir padi
    count = 12 if rich else 5
    gr_r = int((9 if rich else 6) * scale)
    for k in range(count):
        t = k / max(1, count - 1)
        gx = cx + 10 + (bend + 32) * t
        gy = y_bot - h * (0.55 + 0.45 * t) + 28 * (t ** 2)
        side = -1 if k % 2 == 0 else 1
        col = (246, 206, 72) if rich else (206, 184, 114)
        d.ellipse([gx + side * 8 - gr_r, gy - gr_r // 2, gx + side * 8 + gr_r, gy + gr_r // 2],
                  fill=col, outline=COL_OUTLINE, width=2)


def _render_mg_m3(d, p, t_abs):
    """M3 [A] SATU TANGKAI, DUA KARUNG (chip 'x2' resmi)."""
    # pembagi tengah
    d.line([(W // 2, 140), (W // 2, 610)], fill=(66, 72, 92), width=3)
    draw_chip(d, 380, 144, "BIBIT BIASA", sz=14, border=(180, 186, 196))
    draw_chip(d, 900, 144, "BIBIT UNGGUL", sz=14, border=COL_GOLD)

    if p < 0.33:
        # Ketukan 1: dua petak sama luas
        for cx, col in [(380, FIELD), (900, FIELD_BRIGHT)]:
            _px_rect(d, cx - 150, 320, cx + 150, 490, col)
            for dx in range(-120, 121, 40):
                d.line([(cx + dx, 420), (cx + dx, 360)], fill=shade(col, 1.3), width=5)
    else:
        # Ketukan 2 & 3: zoom detail tangkai padi + hasil karung + chip x2
        _draw_rice_stalk(d, 340, 500, rich=False, scale=1.0)
        _draw_rice_stalk(d, 830, 500, rich=True, scale=1.15)
        if p >= 0.67:
            _draw_sack(d, 460, 490, scale=0.95)
            _draw_sack(d, 960, 490, scale=0.95)
            _draw_sack(d, 1045, 490, scale=0.95)
            draw_chip(d, 900, 210, "x2", sz=22, border=COL_GOLD, bg=(180, 60, 44), fg=COL_WHITE)


def _render_mg_m4(d, p, t_abs):
    """M4 [A] DUA JALUR GABAH (tanpa angka; ukuran koin membedakan)."""
    # Jalur atas: lama
    d.rectangle([168, 160, 1112, 340], fill=(32, 30, 38), outline=(120, 96, 86), width=2)
    draw_chip(d, 200, 174, "JALUR LAMA", sz=12, border=(200, 140, 120), anchor="left")
    _draw_sack(d, 250, 275, scale=0.75, label="GABAH")
    d.line([(310, 275), (620, 275)], fill=(150, 140, 120), width=5)
    draw_chip(d, 670, 252, "TENGKULAK", sz=13, border=(200, 140, 120))
    if p >= 0.20:
        # gabah bergerak ke tengkulak, koin kecil pulang
        t1 = _clamp01(p / 0.35)
        _draw_coin(d, int(620 - 240 * t1), 275, 13, col=(216, 172, 84))
    if p >= 0.67:
        _draw_coin(d, 800, 275, 13, col=(216, 172, 84))
        draw_chip(d, 960, 252, "UNTUNG KECIL", sz=12, border=(200, 140, 120))

    # Jalur bawah: baru
    lit = p >= 0.33
    d.rectangle([168, 370, 1112, 596], fill=(28, 36, 40) if lit else (22, 24, 30),
                outline=COL_GOLD if lit else (60, 64, 78), width=3)
    draw_chip(d, 200, 386, "JALUR BARU", sz=12, border=COL_GOLD if lit else (80, 84, 98), anchor="left")
    if not lit:
        return

    _draw_sack(d, 240, 505, scale=0.75, label="GABAH")
    d.line([(295, 505), (410, 505)], fill=COL_GOLD, width=5)
    # penggilingan pixel
    _px_rect(d, 415, 455, 525, 535, (170, 120, 70))
    d.polygon([(405, 455), (470, 420), (535, 455)], fill=(156, 62, 52), outline=COL_OUTLINE)
    draw_chip(d, 470, 544, "PENGGILINGAN", sz=10, border=COL_GOLD)

    d.line([(535, 505), (725, 505)], fill=COL_GREEN, width=5)
    draw_chip(d, 630, 458, "JALAN KE KOTA", sz=10, border=COL_GREEN)
    draw_chip(d, 740, 488, "WARUNG & PEDAGANG", sz=11, border=COL_GOLD, anchor="left")

    if p >= 0.67:
        _draw_coin(d, 1020, 495, 36, col=(255, 220, 72))
        draw_chip(d, 1020, 544, "UNTUNG BESAR", sz=12, border=COL_GOLD)


def _render_mg_m5(d, p, t_abs):
    """M5 [A] AIR TURUN, SIAPA MASIH PUNYA SUMBER (tanpa angka/skala berlabel)."""
    # Potongan melintang sungai di tengah (x=540..740), sawah kiri & kanan
    drop = _ease(p / 0.33)
    water_top = int(340 + 70 * drop)  # turun ke setengah tanda (tanpa angka!)

    # Tanah kiri & kanan
    _px_rect(d, 160, 330, 540, 540, (92, 68, 44))
    _px_rect(d, 740, 330, 1120, 540, (112, 88, 56))
    # Palung sungai
    d.rectangle([540, 330, 740, 540], fill=(74, 58, 44))
    d.rectangle([540, water_top, 740, 540], fill=RIVER)
    d.line([(540, water_top), (740, water_top)], fill=RIVER_L, width=4)
    # Tanda batas air visual polos (tanpa angka, tanpa teks skala)
    d.line([(544, 340), (558, 340)], fill=COL_WHITE, width=3)
    d.line([(544, 410), (558, 410)], fill=COL_GOLD, width=3)

    # Sisi kiri: sawah hijau + pipa pompa terendam
    sawah_l = FIELD_BRIGHT if p >= 0.33 else FIELD
    _px_rect(d, 160, 308, 540, 332, sawah_l)
    # pipa dari sungai ke pompa kiri
    _px_rect(d, 460, 290, 590, 302, (110, 118, 128))
    _px_rect(d, 578, 290, 592, 470, (110, 118, 128))
    _px_rect(d, 420, 260, 470, 308, (190, 58, 48))
    if p >= 0.33:
        # animasi aliran air naik dari pipa ke parit sawah
        off = int((t_abs * 18) % 24)
        for ky in range(440 - off, 305, -24):
            d.rectangle([582, ky, 588, ky + 10], fill=RIVER_L)
        d.line([(200, 304), (420, 304)], fill=RIVER_L, width=6)

    # Sisi kanan: awan kosong + sawah retak
    _px_rect(d, 740, 308, 1120, 332, FIELD_DRY if p >= 0.33 else FIELD)
    # awan kosong di kanan atas
    d.ellipse([860, 186, 980, 232], fill=(164, 168, 178), outline=COL_OUTLINE, width=3)
    d.ellipse([895, 166, 955, 210], fill=(176, 180, 190), outline=COL_OUTLINE, width=3)
    if p >= 0.33:
        for rx in (790, 860, 940, 1020):
            d.line([(rx, 314), (rx + 18, 324), (rx + 8, 332)], fill=(96, 70, 42), width=3)

    if p >= 0.67:
        draw_chip(d, 350, 558, "SINARBARU: HUJAN + SUNGAI", sz=11, border=COL_GOLD)
        draw_chip(d, 930, 558, "TANJUNGSARI: HUJAN SAJA", sz=11, border=COL_RED)


def _render_mg_m6(d, p, t_abs):
    """M6 [A] CARA KERJA POMPA (tinggi air sama dengan M5; chip resmi '1 POMPA = 10 ORANG')."""
    # Kiri: potongan pompa + pipa ke sungai (tinggi air sama dengan M5!)
    d.rectangle([168, 160, 620, 540], fill=(24, 32, 42), outline=(74, 84, 104), width=2)
    _px_rect(d, 180, 330, 450, 520, (92, 68, 44))
    _px_rect(d, 180, 306, 450, 330, FIELD_BRIGHT)
    d.rectangle([450, 330, 610, 520], fill=(74, 58, 44))
    # tinggi air setengah (sama dengan M5: y=410)
    d.rectangle([450, 410, 610, 520], fill=RIVER)
    d.line([(450, 410), (610, 410)], fill=RIVER_L, width=4)
    # pipa & pompa berdenyut
    pulse = int(3 * math.sin(t_abs * 14.0))
    _px_rect(d, 515, 290, 529, 470, (110, 118, 128))
    _px_rect(d, 350, 290, 529, 304, (110, 118, 128))
    _px_rect(d, 310, 250 + pulse, 365, 306 + pulse, (190, 58, 48))
    off = int((t_abs * 24) % 24)
    for ky in range(440 - off, 305, -24):
        d.rectangle([519, ky, 525, ky + 10], fill=RIVER_L)
    d.line([(195, 302), (310, 302)], fill=RIVER_L, width=6)
    draw_chip(d, 394, 174, "MESIN POMPA", sz=12, border=COL_GOLD)

    # Kanan: 10 siluet orang menimba dengan ember (Ketukan 2+)
    if p >= 0.33:
        d.rectangle([650, 160, 1112, 440], fill=(24, 30, 40), outline=(74, 84, 104), width=2)
        draw_chip(d, 881, 174, "MENIMBA SEHARIAN", sz=12, border=COL_GREEN)
        for i in range(10):
            r, c = divmod(i, 5)
            ox = 700 + c * 86
            oy = 266 + r * 86
            bob = int(4 * math.sin(t_abs * 7.0 + i))
            # siluet kepala + badan + ember
            d.ellipse([ox - 9, oy - 36 + bob, ox + 9, oy - 18 + bob], fill=(160, 180, 200))
            d.rectangle([ox - 11, oy - 16 + bob, ox + 11, oy + 14], fill=(130, 150, 172))
            _px_rect(d, ox + 12, oy - 6 + bob, ox + 24, oy + 10 + bob, (110, 140, 180))
            # tetes keringat
            if (int(t_abs * 4) + i) % 3 == 0:
                d.ellipse([ox + 12, oy - 34, ox + 16, oy - 28], fill=RIVER_L)

    # Ketukan 3: timbangan seimbang & chip resmi "1 POMPA = 10 ORANG"
    if p >= 0.67:
        d.line([(720, 486), (1042, 486)], fill=COL_GOLD, width=6)
        d.polygon([(881, 486), (866, 520), (896, 520)], fill=COL_GOLD)
        draw_chip(d, W // 2, 550, "1 POMPA = 10 ORANG", sz=18, border=COL_GOLD, bg=(160, 48, 40), fg=COL_WHITE)


def _render_mg_m7(d, p, t_abs):
    """M7 [B] SATU PERSIMPANGAN, DUA DUNIA (tanpa angka selisih/grafik)."""
    # Ketukan 1: Garis waktu bercabang
    _px_rect(d, 168, 368, 320, 380, COL_GOLD)
    d.ellipse([308, 356, 336, 384], fill=COL_WHITE, outline=COL_OUTLINE, width=3)
    draw_chip(d, 240, 316, "TAHUN PERTAMA", sz=11, border=COL_GOLD)

    if p < 0.25:
        return

    # Cabang atas: POMPA DITOLAK LAMA
    d.line([(330, 366), (440, 240), (1080, 240)], fill=COL_RED, width=5)
    draw_chip(d, 440, 166, "POMPA DITOLAK LAMA", sz=12, border=COL_RED, anchor="left")
    dark_count = min(5, int(_clamp01((p - 0.25) / 0.40) * 6))
    for i in range(5):
        hx = 480 + i * 116
        lit = i >= dark_count
        _px_rect(d, hx - 22, 262, hx + 22, 306, (140, 100, 62) if lit else (76, 72, 70))
        d.polygon([(hx - 28, 262), (hx, 238), (hx + 28, 262)],
                  fill=(180, 120, 62) if lit else (66, 54, 52), outline=COL_OUTLINE)
        d.rectangle([hx - 8, 274, hx + 8, 288], fill=(252, 224, 120) if lit else (34, 34, 38))

    # Cabang bawah: POMPA DITERIMA DI AWAL
    d.line([(330, 376), (440, 468), (1080, 468)], fill=COL_GREEN, width=5)
    draw_chip(d, 440, 404, "POMPA DITERIMA DI AWAL", sz=12, border=COL_GREEN, anchor="left")
    for i in range(5):
        hx = 480 + i * 116
        _px_rect(d, hx - 22, 488, hx + 22, 532, (164, 114, 68))
        d.polygon([(hx - 28, 488), (hx, 464), (hx + 28, 488)], fill=(200, 134, 68), outline=COL_OUTLINE)
        d.rectangle([hx - 8, 500, hx + 8, 514], fill=(252, 224, 120))

    # Ketukan 3: penjelas visual "masih kalah" (1 ikon vs 5 ikon, tanpa angka)
    if p >= 0.68:
        d.rectangle([168, 550, 1112, 620], fill=(20, 22, 30), outline=COL_GOLD, width=2)
        draw_chip(d, 190, 566, "TANJUNGSARI: POMPA", sz=10, border=COL_GREEN, anchor="left")
        draw_chip(d, 490, 566, "SINARBARU: LIMA LAPIS", sz=10, border=COL_GOLD, anchor="left")
        draw_chip(d, 1094, 566, "MASIH KALAH", sz=11, border=COL_GOLD, bg=(140, 48, 42), anchor="right")


def _render_mg_m8(d, p, t_abs):
    """M8 [B] TEMBOK LIMA LAPIS VS KEBERUNTUNGAN (jangan tampilkan '100' atau 'nol')."""
    bricks = ["JALAN DAGANG", "PENGGILINGAN", "PELATIHAN", "BIBIT", "POMPA"]
    shown = min(5, int(_clamp01(p / 0.30) * 5) + 1)
    for i in range(shown):
        by = 504 - i * 68
        _px_rect(d, 210, by, 540, by + 56, (176, 86, 62))
        d.rectangle([214, by + 4, 536, by + 11], fill=(206, 112, 84))
        draw_chip(d, 375, by + 11, bricks[i], sz=13, border=COL_GOLD, bg=(42, 28, 24))

    # Ketukan 2: dadu, awan hujan, dan koin "hoki" melenting dari tembok
    if p >= 0.33:
        bounce_t = ((t_abs * 1.4) % 1.0)
        # sebelum kena x=540 lalu melenting ke kanan
        tri = 1.0 - abs(bounce_t * 2.0 - 1.0)
        hx = int(980 - 410 * tri)
        # dadu
        _px_rect(d, hx - 22, 210, hx + 22, 254, COL_WHITE)
        d.ellipse([hx - 6, 226, hx + 6, 238], fill=COL_OUTLINE)
        draw_chip(d, hx, 264, "DADU", sz=10, border=(180, 186, 196))
        # awan hujan
        d.ellipse([hx - 34, 326, hx + 34, 364], fill=(120, 134, 154), outline=COL_OUTLINE, width=3)
        draw_chip(d, hx, 372, "CUACA", sz=10, border=(140, 180, 220))
        # koin hoki
        _draw_coin(d, hx, 452, 24)
        draw_chip(d, hx, 484, "HOKI", sz=10, border=COL_GOLD)

    if p >= 0.67:
        draw_chip(d, W // 2, 580, "BUKAN HOKI, TAPI STRUKTUR", sz=16, border=COL_GOLD, bg=(156, 48, 42), fg=COL_WHITE)


MG_RENDERERS = {
    "M1": _render_mg_m1,
    "M2": _render_mg_m2,
    "M3": _render_mg_m3,
    "M4": _render_mg_m4,
    "M5": _render_mg_m5,
    "M6": _render_mg_m6,
    "M7": _render_mg_m7,
    "M8": _render_mg_m8,
}


def render_mg(moment, bg_img, t_abs):
    """Render frame MG Penjelas + Blur Map 1280x720."""
    base = pixel_blur(bg_img, factor=8, darken=0.45)
    d = ImageDraw.Draw(base)
    p = _clamp01((t_abs - moment["t0"]) / max(0.01, moment["t1"] - moment["t0"]))

    # Chip judul di atas kartu, kartu di tengah, aman dari HUD (y<56) dan caption (y>640)
    draw_chip(d, W // 2, 64, moment["title"], sz=15, border=COL_GOLD, bg=COL_NAVY, fg=COL_GOLD)
    draw_card_panel(d, 130, 114, 1150, 636, border=COL_GOLD)
    MG_RENDERERS[moment["id"]](d, p, t_abs)
    return base


# =====================================================================
# RENDERER VIGNETTE TAMPIL SAMPING (V1 - V9)
# =====================================================================

def _icon_house(d, x, y):
    d.rectangle([x + 2, y + 10, x + 22, y + 24], fill=(164, 114, 68), outline=COL_OUTLINE)
    d.polygon([(x, y + 10), (x + 12, y), (x + 24, y + 10)], fill=(196, 134, 72), outline=COL_OUTLINE)


def _render_v1(p, t_abs, f):
    """V1 [A] KEVIN DAN POMPA MOGOK."""
    img = Image.new("RGB", (VG_W, VG_H))
    _draw_stage_bg(img, mood="day", f=f)
    _draw_river_strip(img, state="normal", f=f)
    d = ImageDraw.Draw(img)

    # petak bibit baru aneh di belakang kiri
    _px_rect(d, 14, 108, 72, 130, (124, 166, 78))
    for bx in range(20, 68, 10):
        d.line([(bx, 126), (bx + 3, 114), (bx - 2, 110)], fill=(176, 198, 92), width=2)

    # pompa mogok + ember kosong
    _draw_pump_vig(d, 138, 142, working=False, broken=(p >= 0.25), f=f, scale=1.2)
    _px_rect(d, 112, 130, 124, 142, (132, 92, 54))  # ember kosong

    # Kevin menarik tuas -> bingung/malu
    expr = "confused" if p >= 0.33 else "neutral"
    pose = "pull_lever" if p < 0.67 else "idle"
    draw_kevin_vig(d, 90, 142, look="right", expr=expr, pose=pose,
                   bob=(f // 12) % 2, blink=(f % 90) < 4)

    # 3 warga bersedekap di kanan
    v_specs = [(216, (210, 70, 60), "caping"), (252, (70, 130, 210), "kain"), (286, (210, 170, 60), "none")]
    for idx, (vx, col, hat) in enumerate(v_specs):
        shake_bob = ((f // 6 + idx) % 2) if p >= 0.67 else 0
        draw_villager_vig(d, vx, 142, shirt=col, hat=hat, pose="crossed", look="left", bob=shake_bob)

    full = img.resize((W, H), Image.NEAREST)
    fd = ImageDraw.Draw(full)
    draw_signboard(fd, 43 * VG_SCALE, 130 * VG_SCALE, ["BIBIT", "BARU"], sz=10, post_h=16)
    draw_signboard(fd, 168 * VG_SCALE, 142 * VG_SCALE, ["POMPA AIR"], sz=10, style="blue", post_h=20)
    draw_nameplate(fd, 44, 64, "KEVIN", "POMPA MOGOK!", accent=COL_GOLD, align="left")
    if p >= 0.65:
        draw_bubble(fd, 250 * VG_SCALE, 62 * VG_SCALE, '"PINTAR DI SEKOLAH, TAPI DI SAWAH?"',
                    kind="speech", max_w=340, sz=11)
    return full


def _render_v2(p, t_abs, f):
    """V2 [B] KEVIN MENDENGARKAN."""
    img = Image.new("RGB", (VG_W, VG_H))
    _draw_stage_bg(img, mood="day", f=f)
    _draw_river_strip(img, state="normal", f=f)
    d = ImageDraw.Draw(img)

    _draw_pump_vig(d, 44, 138, working=False, broken=False, f=f, scale=0.95)
    # 5 siluet anak muda membawa kunci pas berjalan menuju pompa di ketukan 3
    if p >= 0.67:
        prog = _ease((p - 0.67) / 0.30)
        for i in range(5):
            ux = int(288 - prog * 170 + i * 14)
            if ux <= 312:
                draw_villager_vig(d, ux, 130, hat="none", look="left", scale=0.62,
                                  bob=((f // 5 + i) % 2), prop="wrench", silhouette=True)

    draw_kevin_vig(d, 118, 143, look="right", expr="neutral", pose="notebook",
                   bob=(f // 15) % 2, blink=(f % 95) < 4)
    draw_villager_vig(d, 192, 143, shirt=(210, 74, 64), hat="caping", pose="point", look="left",
                      bob=((f // 7) % 2) if p < 0.67 else 0)

    full = img.resize((W, H), Image.NEAREST)
    fd = ImageDraw.Draw(full)
    draw_signboard(fd, 44 * VG_SCALE, 140 * VG_SCALE, ["POMPA AIR"], sz=10, style="blue", post_h=18)
    draw_nameplate(fd, 44, 64, "KEVIN", "MENDENGARKAN!", accent=COL_GOLD, align="left")
    draw_chip(fd, 44, 134, "TIDAK MEMBELA DIRI", sz=11, border=COL_GOLD, anchor="left")
    if p < 0.67:
        # bubble keluhan bergelombang visual
        bx0, by0 = 740, 140
        fd.rectangle([bx0 - 3, by0 - 3, bx0 + 183, by0 + 57], fill=COL_OUTLINE)
        fd.rectangle([bx0, by0, bx0 + 180, by0 + 54], fill=(255, 252, 242), outline=COL_OUTLINE, width=2)
        fd.polygon([(830, by0 + 54), (848, by0 + 54), (838, by0 + 70)], fill=(255, 252, 242), outline=COL_OUTLINE)
        for wy in (by0 + 18, by0 + 36):
            pts = [(bx0 + 18 + k * 14, wy + (4 if (k + f // 5) % 2 == 0 else -4)) for k in range(11)]
            fd.line(pts, fill=(180, 56, 48), width=4)
    return full


def _render_v3(p, t_abs, f):
    """V3 [B] MULYADI MENANCAPKAN LARANGAN."""
    img = Image.new("RGB", (VG_W, VG_H))
    _draw_stage_bg(img, mood="day", f=f)
    _draw_river_strip(img, state="normal", f=f)
    d = ImageDraw.Draw(img)

    back_step = int(28 * _ease((p - 0.67) / 0.28)) if p >= 0.67 else 0
    vx = int(76 + 34 * _ease(min(1.0, p / 0.33))) - back_step
    draw_villager_vig(d, vx, 143, shirt=(72, 138, 206), hat="caping", look="right", prop="hoe",
                      bob=((f // 6) % 2) if p < 0.67 else 0)

    pose = "tap" if 0.33 <= p < 0.67 else ("block" if p < 0.33 else "idle")
    draw_mulyadi_vig(d, 224, 143, look="left", expr="stern", pose=pose, blink=(f % 100) < 4)

    full = img.resize((W, H), Image.NEAREST)
    fd = ImageDraw.Draw(full)
    draw_nameplate(fd, 44, 64, "PAK MULYADI", "MELARANG!", accent=COL_GREEN, align="left")
    if p >= 0.33:
        draw_signboard(fd, 165 * VG_SCALE, 143 * VG_SCALE, ["DILARANG BELI", "ALAT DARI SINARBARU"],
                       sz=10, style="warn", post_h=34)
    if 0.25 <= p < 0.85:
        draw_bubble(fd, 214 * VG_SCALE, 45 * VG_SCALE,
                    '"TIDAK BUTUH BANTUAN ANAK KEMARIN SORE"', kind="speech", max_w=340, sz=10)
    return full


def _render_v4(p, t_abs, f):
    """V4 [A] UJANG MENYEBERANG — SATU Ujang saja, cangkul bergeser menjadi kunci pas."""
    img = Image.new("RGB", (VG_W, VG_H))
    _draw_stage_bg(img, mood="day", f=f)
    # sungai mengalir vertikal di tengah panggung menuju strip sungai di bawah
    d = ImageDraw.Draw(img)
    d.rectangle([126, 108, 194, 150], fill=BANK)
    d.rectangle([134, 108, 186, 150], fill=RIVER)
    for ry in range(114, 148, 8):
        d.line([(142 + (f // 4 + ry) % 10, ry), (154 + (f // 4 + ry) % 10, ry)], fill=RIVER_L)
    # batu titian di tengah sungai
    for sx in (182, 160, 138):
        _px_rect(d, sx - 9, 139, sx + 9, 145, (164, 158, 146))

    # kiri: pompa Sinarbaru; kanan: rumah berasap Tanjungsari
    _draw_pump_vig(d, 44, 140, working=True, f=f, scale=1.0)
    _draw_house_bg(d, 256, 138, abandoned=False, lit=True)

    _draw_river_strip(img, state="normal", f=f)
    d = ImageDraw.Draw(img)

    # SATU Ujang bergerak dari kanan ke titian tengah, menoleh, lalu melangkah ke kiri
    if p < 0.35:
        ux = int(196 - 36 * _ease(p / 0.35))
        look, pose, prop = "left", "walk", "hoe"
    elif p < 0.67:
        ux = 160
        look = "right" if p < 0.56 else "left"  # menoleh sekali ke belakang
        pose, prop = "idle", "hoe"
    else:
        u = _ease((p - 0.67) / 0.33)
        ux = int(160 - 66 * u)
        look, pose = "left", "walk"
        prop = "wrench" if p >= 0.72 else "hoe"

    draw_ujang_vig(d, ux, 140, look=look, expr="neutral", prop=prop, pose=pose,
                   bob=(f // 6) % 2 if pose == "walk" else 0, blink=(f % 95) < 4)

    full = img.resize((W, H), Image.NEAREST)
    fd = ImageDraw.Draw(full)
    draw_signboard(fd, 72 * VG_SCALE, 136 * VG_SCALE, ["SINARBARU"], sz=10, style="blue", post_h=18)
    draw_signboard(fd, 240 * VG_SCALE, 136 * VG_SCALE, ["TANJUNGSARI"], sz=10, post_h=18)
    draw_nameplate(fd, 44, 64, "UJANG", "MENYEBERANG!", accent=COL_GOLD, align="left")
    if p < 0.72:
        draw_bubble(fd, ux * VG_SCALE, 43 * VG_SCALE, "BUKAN KARENA BENCI",
                    kind="thought", max_w=240, sz=11, icon_fn=_icon_house)
    return full


def _render_v5(p, t_abs, f):
    """V5 [A] MENOLAK DI TENGAH KEMARAU."""
    img = Image.new("RGB", (VG_W, VG_H))
    _draw_stage_bg(img, mood="drought", left_dry=False, right_dry=True, f=f)
    _draw_river_strip(img, state="drought", f=f)
    d = ImageDraw.Draw(img)

    # retak di tanah pijakan bawah Mulyadi
    extra_crack = p >= 0.67
    for cx_r in (190, 224, 258, 286):
        d.line([(cx_r, 136), (cx_r + 8, 141), (cx_r + 4, 147)], fill=(116, 86, 48), width=2 if extra_crack else 1)

    # Utusan Sinarbaru (berompi biru muda) mengulurkan pompa -> pulang di ketukan 3
    if p < 0.33:
        ex = int(52 + 46 * _ease(p / 0.33))
        elook = "right"
    elif p < 0.67:
        ex = 98
        elook = "right"
    else:
        ex = int(98 - 62 * _ease((p - 0.67) / 0.33))
        elook = "left"

    draw_villager_vig(d, ex, 143, shirt=(120, 186, 238), hat="caping", look=elook,
                      bob=(f // 6) % 2 if elook == "left" or p < 0.33 else 0)
    px_pump = ex + (24 if elook == "right" else -22)
    _draw_pump_vig(d, px_pump, 134, working=False, f=f, scale=0.72)

    # Mulyadi memalingkan wajah (look="right" menghadap pergi dari utusan) & mengetuk tongkat
    mlook = "right" if p >= 0.33 else "left"
    mpose = "tap" if 0.35 <= p < 0.55 else "crossed"
    draw_mulyadi_vig(d, 238, 143, look=mlook, expr="stubborn", pose=mpose, blink=(f % 100) < 4)

    full = img.resize((W, H), Image.NEAREST)
    fd = ImageDraw.Draw(full)
    draw_signboard(fd, px_pump * VG_SCALE, 142 * VG_SCALE, ["POMPA", "PINJAMAN"], sz=9, style="blue", post_h=12)
    draw_nameplate(fd, W - 44, 64, "PAK MULYADI", "MENOLAK!", accent=COL_GREEN, align="right")
    if p >= 0.33:
        draw_bubble(fd, 224 * VG_SCALE, 45 * VG_SCALE, "TERIMA = AKUI SALAH",
                    kind="thought", max_w=260, sz=11)
    return full


def _render_v6(p, t_abs, f):
    """V6 [A] EKSODUS, MULYADI DITINGGAL (palet dingin, ruang diam sebelum tirai tutup)."""
    img = Image.new("RGB", (VG_W, VG_H))
    _draw_stage_bg(img, mood="dusk", left_dry=False, right_dry=True, f=f)
    _draw_river_strip(img, state="drought", f=f)
    d = ImageDraw.Draw(img)

    # rumah-rumah di latar padam satu per satu
    lit_count = 3 - min(3, int(p * 4))
    for i, hx in enumerate((130, 174, 218)):
        _draw_house_bg(d, hx, 132, abandoned=(i >= lit_count), lit=(i < lit_count))

    # gerbang desa Tanjungsari (kiri dari Mulyadi agar tidak menutupi tokoh)
    _px_rect(d, 210, 98, 215, 134, (112, 82, 52))
    _px_rect(d, 242, 100, 247, 134, (112, 82, 52))
    d.line([(212, 98), (245, 103)], fill=(128, 92, 58), width=3)

    # keluarga-keluarga membawa bundel berjalan ke kiri (ruang diam di p >= 0.72)
    if p < 0.74:
        families = [(0.0, 0.42, (200, 80, 70), "caping"),
                    (0.22, 0.62, (80, 140, 200), "kain"),
                    (0.40, 0.74, (200, 170, 80), "none")]
        for (s0, s1, col, hat) in families:
            if s0 <= p <= s1:
                u = (p - s0) / (s1 - s0)
                fx = int(224 - u * 204)
                draw_villager_vig(d, fx, 143, shirt=col, hat=hat, pose="bundle", look="left",
                                  scale=0.88, bob=(f // 6) % 2)
                draw_villager_vig(d, fx + 18, 143, shirt=shade(col, 0.8), hat="none", pose="bundle",
                                  look="left", scale=0.72, bob=((f // 6) + 1) % 2)

    # Mulyadi sendirian di pojok kanan bersandar tongkat, menoleh ke arah mereka
    draw_mulyadi_vig(d, 280, 143, look="left", expr="sad", pose="lean", blink=(f % 110) < 4)

    full = img.resize((W, H), Image.NEAREST)
    fd = ImageDraw.Draw(full)
    draw_signboard(fd, 228 * VG_SCALE, 102 * VG_SCALE, ["TANJUNGSARI"], sz=10, post_h=12)
    draw_nameplate(fd, W - 44, 64, "PAK MULYADI", "DITINGGAL!", accent=COL_GREEN, align="right")
    return full


def _render_v7(p, t_abs, f):
    """V7 [A] POMPA DIAM-DIAM (malam, lentera, hijau menjalar, sungai pulih jernih)."""
    img = Image.new("RGB", (VG_W, VG_H))
    green_spread = _ease((p - 0.35) / 0.45) if p >= 0.35 else 0.0
    _draw_stage_bg(img, mood="night", left_dry=False, right_dry=(green_spread < 0.7), f=f)
    # sungai mulai surut lalu pulih jernih saat pompa menyala di ketukan 3
    _draw_river_strip(img, state="clear" if p >= 0.65 else "drought", f=f)
    d = ImageDraw.Draw(img)

    # petak sawah kanan perlahan berubah hijau dari parit kiri ke kanan
    gx_end = int(160 + 150 * green_spread)
    if green_spread > 0.01:
        d.rectangle([160, 109, gx_end, 131], fill=shade(FIELD_BRIGHT, 0.55))
        d.line([(130, 128), (gx_end, 128)], fill=RIVER_L, width=2)

    pump_on = p >= 0.35
    _draw_pump_vig(d, 118, 142, working=pump_on, f=f, scale=1.05)

    # Ujang berjongkok dengan kunci pas, Sari pegang lentera, Mulyadi jari di bibir melirik kiri-kanan
    draw_ujang_vig(d, 152, 143, look="left", expr="neutral", prop="wrench", pose="crouch")
    draw_sari_vig(d, 198, 143, look="left", expr="neutral", lantern=True, blink=(f % 95) < 4)
    mlook = "left" if (f // 45) % 2 == 0 else "right"
    draw_mulyadi_vig(d, 256, 143, look=mlook, expr="neutral", pose="shush", blink=(f % 100) < 4)

    full = img.resize((W, H), Image.NEAREST)
    fd = ImageDraw.Draw(full)
    draw_signboard(fd, 90 * VG_SCALE, 142 * VG_SCALE, ["POMPA", "SATU-SATUNYA"], sz=9, style="blue", post_h=16)
    draw_nameplate(fd, W - 44, 64, "PAK MULYADI", "DIAM-DIAM!", accent=COL_GREEN, align="right")
    draw_chip(fd, W - 44, 134, "JANGAN BILANG SIAPA-SIAPA", sz=10, border=COL_GOLD, anchor="right")
    return full


def _icon_weather(d, x, y):
    d.ellipse([x + 10, y + 2, x + 22, y + 14], fill=(252, 212, 74))
    d.ellipse([x + 2, y + 10, x + 20, y + 22], fill=(180, 196, 216), outline=COL_OUTLINE)


def _render_v8(p, t_abs, f):
    """V8 [B] PASAR BERSAMA, SEMEJA."""
    img = Image.new("RGB", (VG_W, VG_H))
    _draw_stage_bg(img, mood="warm_eve", f=f)
    _draw_river_strip(img, state="clear", f=f)
    d = ImageDraw.Draw(img)

    # lapak latar + Ujang atur pompa + Sari atur dagangan
    for sx, aw in ((22, (200, 60, 50)), (258, (60, 120, 200))):
        _px_rect(d, sx, 108, sx + 36, 134, (140, 96, 54))
        _px_rect(d, sx - 2, 100, sx + 38, 108, aw)
    _draw_pump_vig(d, 72, 136, working=True, f=f, scale=0.65)
    draw_ujang_vig(d, 90, 136, look="left", prop="wrench", bob=(f // 12) % 2)
    draw_sari_vig(d, 232, 136, look="right", expr="happy", bob=(f // 14) % 2)

    # Kevin kiri, Mulyadi kanan, meja kecil di tengah dengan dua cangkir kopi berasap
    draw_kevin_vig(d, 132, 144, look="right", expr="happy", pose="idle", blink=(f % 95) < 4)
    draw_mulyadi_vig(d, 192, 144, look="left", expr="neutral", pose="idle", blink=(f % 100) < 4)
    _px_rect(d, 146, 122, 178, 128, (136, 92, 50))
    _px_rect(d, 160, 128, 164, 144, (104, 68, 36))
    # cangkir kopi + uap
    for cx_c in (152, 170):
        _px_rect(d, cx_c - 3, 117, cx_c + 3, 122, (240, 236, 228))
        sy = 114 - ((f // 4) % 5)
        d.point((cx_c, sy), fill=(250, 248, 244))
    if p < 0.35:
        # teko kopi menuang ke cangkir Kevin
        _px_rect(d, 162, 106, 172, 114, (160, 164, 172))
        d.line([(162, 110), (153, 118)], fill=(96, 56, 30), width=2)

    full = img.resize((W, H), Image.NEAREST)
    fd = ImageDraw.Draw(full)
    draw_signboard(fd, 276 * VG_SCALE, 108 * VG_SCALE, ["PASAR BERSAMA"], sz=10, style="blue", post_h=12)
    draw_nameplate(fd, 44, 64, "KEVIN & MULYADI", "SEMEJA!", accent=COL_GOLD, align="left")
    if 0.33 <= p < 0.78:
        draw_bubble(fd, 162 * VG_SCALE, 52 * VG_SCALE, "CUACA CERAH", kind="speech",
                    max_w=240, sz=11, icon_fn=_icon_weather)
    return full


def _render_v9(p, t_abs, f):
    """V9 [A] HIDUP UJANG DUA KALI — menggantikan render_split s18 sepenuhnya.
    Kiri: YANG TERJADI (warna penuh, kunci pas + kirim amplop ke rumah IBU).
    Kanan: SEANDAINYA (desaturasi, scanline, bingkai putus-putus, Ujang BAYANGAN)."""
    # Kiri (0..160 di grid 320x180)
    left_g = Image.new("RGB", (VG_W, VG_H))
    _draw_stage_bg(left_g, mood="day", f=f)
    _draw_river_strip(left_g, state="clear", f=f, x0=0, x1=VG_W // 2)
    ld = ImageDraw.Draw(left_g)
    _draw_pump_vig(ld, 40, 142, working=True, f=f, scale=0.95)
    _draw_house_bg(ld, 122, 138, abandoned=False, lit=True)
    draw_ujang_vig(ld, 74, 142, look="right", expr="happy", prop="wrench",
                   pose="throw" if p < 0.7 else "idle", bob=(f // 12) % 2)
    # amplop/koin melayang ke rumah ibu
    env_t = (t_abs * 0.7) % 1.0
    ex = int(84 + 44 * env_t)
    ey = int(102 - 22 * math.sin(env_t * math.pi))
    _px_rect(ld, ex - 4, ey - 3, ex + 4, ey + 3, COL_GOLD)

    # Kanan (160..320 di grid 320x180)
    right_g = Image.new("RGB", (VG_W, VG_H))
    _draw_stage_bg(right_g, mood="dusk", left_dry=True, right_dry=True, f=f)
    _draw_river_strip(right_g, state="drought", f=f, x0=VG_W // 2, x1=VG_W, dim=True)
    rd = ImageDraw.Draw(right_g)
    _draw_house_bg(rd, 274, 138, abandoned=False, lit=True, dim=True)
    # siluet ibu menunggu dengan lentera di depan rumah
    draw_villager_vig(rd, 266, 141, hat="none", look="left", scale=0.72, prop="lantern", silhouette=True)
    # satu karung kecil
    _px_rect(rd, 224, 132, 234, 142, (148, 126, 86))
    # Ujang BAYANGAN (bukan tokoh kedua berwarna penuh)
    draw_ujang_vig(rd, 206, 142, look="right", prop="hoe", bob=(f // 16) % 2, ghost=True)

    # Desaturasi + scanline untuk sisi kanan SEANDAINYA
    right_gray = right_g.convert("L").convert("RGB")
    right_g = Image.blend(right_g, right_gray, 0.75)

    # Ketukan pencahayaan (Ketukan 1 kiri terang, 2 kanan terang, 3 keduanya)
    if p < 0.35:
        right_g = ImageEnhance.Brightness(right_g).enhance(0.45)
    elif p < 0.70:
        left_g = ImageEnhance.Brightness(left_g).enhance(0.50)

    # Gabungkan kiri (0..640) dan kanan (640..1280)
    full_l = left_g.resize((W, H), Image.NEAREST).crop((0, 0, W // 2, H))
    full_r = right_g.resize((W, H), Image.NEAREST).crop((W // 2, 0, W, H))
    full = Image.new("RGB", (W, H))
    full.paste(full_l, (0, 0))
    full.paste(full_r, (W // 2, 0))

    fd = ImageDraw.Draw(full)
    # scanline halus di sisi SEANDAINYA
    for sy in range(STAGE_TOP, STAGE_BOT, 8):
        fd.line([(W // 2 + 4, sy), (W - 4, sy)], fill=(24, 28, 34), width=1)
    # bingkai putus-putus di sisi SEANDAINYA
    for x in range(W // 2 + 10, W - 12, 24):
        fd.line([(x, STAGE_TOP + 6), (min(W - 8, x + 12), STAGE_TOP + 6)], fill=(190, 200, 214), width=3)
        fd.line([(x, STAGE_BOT - 6), (min(W - 8, x + 12), STAGE_BOT - 6)], fill=(190, 200, 214), width=3)
    for y in range(STAGE_TOP + 6, STAGE_BOT - 6, 24):
        fd.line([(W // 2 + 6, y), (W // 2 + 6, min(STAGE_BOT - 6, y + 12))], fill=(190, 200, 214), width=3)
        fd.line([(W - 6, y), (W - 6, min(STAGE_BOT - 6, y + 12))], fill=(190, 200, 214), width=3)
    # pembatas tengah
    fd.rectangle([W // 2 - 4, STAGE_TOP, W // 2 + 4, STAGE_BOT], fill=COL_DARK)

    # Papan properti & chip sisi
    draw_signboard(fd, 536, 134 * VG_SCALE, ["IBU"], sz=10, post_h=14)
    draw_signboard(fd, 1144, 134 * VG_SCALE, ["IBU"], sz=10, post_h=14)
    draw_signboard(fd, 756, 144 * VG_SCALE, ["SAWAH DI", "TANJUNGSARI"], sz=9, post_h=12)

    draw_chip(fd, 40, 70, "YANG TERJADI", sz=12, border=COL_GOLD, anchor="left")
    draw_chip(fd, W - 40, 70, "SEANDAINYA", sz=12, border=(170, 180, 196), anchor="right")

    # SATU pelat UJANG di tengah-atas yang menghubungkan keduanya (tanpa umur!)
    draw_nameplate(fd, W // 2, 62, "UJANG", "HIDUP DUA KALI", accent=COL_GOLD, align="center")

    if p >= 0.70:
        draw_chip(fd, W // 2, 144, "ORANGNYA SAMA. PEMIMPINNYA BEDA.", sz=14,
                  border=COL_GOLD, bg=(140, 44, 38), fg=COL_WHITE)
    return full


VIG_RENDERERS = {
    "V1": _render_v1,
    "V2": _render_v2,
    "V3": _render_v3,
    "V4": _render_v4,
    "V5": _render_v5,
    "V6": _render_v6,
    "V7": _render_v7,
    "V8": _render_v8,
    "V9": _render_v9,
}


def render_vignette(moment, t_abs):
    """Render panggung vignette + tirai pixel cokelat tua membuka/menutup."""
    p = _clamp01((t_abs - moment["t0"]) / max(0.01, moment["t1"] - moment["t0"]))
    f = int(round((t_abs - moment["t0"]) * 30))
    full = VIG_RENDERERS[moment["id"]](p, t_abs, f)
    fd = ImageDraw.Draw(full)
    draw_curtains(fd, t_abs, moment["t0"], moment["t1"], dur=0.45)
    return full


def render_v3_frame(moment, t_abs, bg_img=None):
    """Titik masuk utama renderer v3 (MG atau Vignette)."""
    if moment["kind"] == "mg":
        if bg_img is None:
            bg_img = Image.new("RGB", (W, H), (24, 24, 30))
        return render_mg(moment, bg_img, t_abs)
    return render_vignette(moment, t_abs)
