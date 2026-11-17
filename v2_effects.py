#!/usr/bin/env python3
"""Fitur visual v2: sistem kamera, marker, stempel, mode showcase/split_fields/chart,
counter migran, dan chip."""
import json
import math
import os
from PIL import Image, ImageDraw
from world import CHECK, GW, GH, W, H, grade
from assets import draw_kevin, draw_mulyadi

PROJ = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(PROJ, "cues-v2.json"), encoding="utf-8") as _fh:
    CUES = json.load(_fh)

MARKERS = CUES.get("markers", [])
STAMPS = CUES.get("stamps", [])
MODES = CUES.get("modes", [])
COUNTERS = CUES.get("counters", [])
CHIPS = CUES.get("chips", [])

COL_GOLD = (255, 220, 120)
COL_GREEN = (140, 230, 140)
COL_WHITE = (245, 245, 245)
COL_DARK = (20, 18, 16)
COL_CREAM = (255, 240, 200)
COL_RED = (240, 140, 120)

PROPERTY_POS = {
    "pompa": (136, 115),          # pusat visual pompa kiri (125, 105, 22x20)
    "pompa_rahasia": (506, 195),  # pusat visual pompa kanan (495, 185, 22x20)
    "penggilingan": (273, 260),   # pusat visual penggilingan (250, 240, 46x40)
    "pasar": (310, 175),          # titik tengah pasar bersama (310, 165)
    "jembatan": (320, 184),
    "sungai": (320, 180),
    "bibit": (85, 87),
}

MARKER_LABELS = {
    "kevin": "KEVIN",
    "mulyadi": "PAK MULYADI",
    "sari": "SARI",
    "ujang": "UJANG",
    "pompa": "POMPA",
    "pompa_rahasia": "POMPA RAHASIA",
    "penggilingan": "PENGGILINGAN",
    "pasar": "PASAR",
    "jembatan": "JEMBATAN",
    "sungai": "SUNGAI",
    "bibit": "BIBIT UNGGUL",
}

SUBJECT_RADIUS = {
    "kevin": 16,
    "mulyadi": 16,
    "sari": 16,
    "ujang": 16,
    "pompa": 16,
    "pompa_rahasia": 16,
    "penggilingan": 26,
    "pasar": 24,
    "jembatan": 20,
    "sungai": 20,
    "bibit": 20,
}

def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def get_subject_pos(world, subject, seg_name=None, t_abs=None):
    if subject == "kevin":
        return (world.kevin.x, world.kevin.y - 12)
    if subject == "mulyadi":
        return (world.mulyadi.x, world.mulyadi.y - 12)
    if subject == "sari":
        return (world.sari.x, world.sari.y - 12)
    if subject == "ujang":
        return (world.ujang.x, world.ujang.y - 12)
    if subject == "pompa" and seg_name == "s19_eksperimen":
        return PROPERTY_POS["pompa_rahasia"]
    return PROPERTY_POS[subject]

def get_subject_color(world, subject, seg_name=None):
    if subject in ("kevin", "pompa", "penggilingan", "pasar", "bibit"):
        if subject == "pompa" and seg_name == "s19_eksperimen":
            return COL_GREEN
        return COL_GOLD
    if subject in ("mulyadi", "sari", "pompa_rahasia"):
        return COL_GREEN
    if subject == "ujang":
        return COL_GOLD if world.ujang.x <= 320 else COL_GREEN
    return COL_WHITE

def get_active_mode(t_abs):
    for m in MODES:
        if m["t0"] <= t_abs < m["t1"]:
            return m
    return None

def get_active_markers(t_abs):
    return [m for m in MARKERS if m["t"] <= t_abs < m["t"] + 4.0]

def get_active_chips(t_abs):
    return [c for c in CHIPS if c["t"] <= t_abs < c["t"] + c.get("dur", 4.0)]

class CameraController:
    """Kamera grid 640x360 dengan transisi smoothstep ~1.0 dtk."""
    def __init__(self, trans_dur=1.0):
        self.trans_dur = trans_dur
        self.cur_cx = 320.0
        self.cur_cy = 180.0
        self.cur_zoom = 1.0
        self.from_cx = 320.0
        self.from_cy = 180.0
        self.from_zoom = 1.0
        self.trans_t0 = None
        self.last_key = None

    def _compute_target(self, t_abs, world, seg, active_markers):
        name = seg["name"]
        # Direktif khusus s19 (counterfactual)
        if name == "s19_eksperimen":
            if 605.66 <= t_abs <= 612.66:
                return (("dir", "s19_a"), 495.0, 185.0, 1.6)
            if 625.8 <= t_abs <= 632.8:
                return (("dir", "s19_b"), 495.0, 185.0, 1.6)
            return (("wide",), 320.0, 180.0, 1.0)

        # Aturan default: ikuti marker aktif
        if active_markers:
            key = ("markers", tuple(m["subject"] for m in active_markers))
            pts = [get_subject_pos(world, m["subject"], name, t_abs) for m in active_markers]
            if len(pts) == 1:
                return (key, float(pts[0][0]), float(pts[0][1]), 2.0)
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            cx = (min(xs) + max(xs)) / 2.0
            cy = (min(ys) + max(ys)) / 2.0
            need_w = (max(xs) - min(xs)) + 160.0
            need_h = (max(ys) - min(ys)) + 120.0
            fit_z = min(GW / max(1.0, need_w), GH / max(1.0, need_h))
            z = max(1.0, min(1.5, fit_z))
            return (key, cx, cy, z)

        # Direktif segmen (saat tidak ada marker)
        if name == "s08_jembatan1":
            p = smoothstep((t_abs - 324.65) / 5.59)
            return (("dir", "s08"), 320.0, 184.0, 1.0 + 0.8 * p)
        if name == "s09_tahun910":
            for (bt, _btxt, bdur) in seg.get("banners", []):
                if bt <= t_abs < bt + bdur:
                    return (("dir", "s09_drought"), 500.0, 150.0, 1.6)
        if name == "s10_taruhan_twist":
            for c in COUNTERS:
                if c["t0"] <= t_abs <= c["t1"]:
                    return (("dir", "s10_bridge"), 320.0, 184.0, 1.5)
        if name == "s13_tahun1517":
            return (("dir", "s13_pasar"), 310.0, 165.0, 1.5)
        if name == "s16_tahun19":
            p = smoothstep((t_abs - 537.92) / 7.82)
            return (("dir", "s16"), 320.0, 180.0, 1.0 + 0.3 * p)

        return (("wide",), 320.0, 180.0, 1.0)

    def update(self, t_abs, world, seg, active_markers):
        key, tcx, tcy, tz = self._compute_target(t_abs, world, seg, active_markers)
        if self.last_key is None:
            self.last_key = key
            self.trans_t0 = t_abs - self.trans_dur
            self.from_cx, self.from_cy, self.from_zoom = 320.0, 180.0, 1.0
        elif key != self.last_key:
            self.from_cx = self.cur_cx
            self.from_cy = self.cur_cy
            self.from_zoom = self.cur_zoom
            self.trans_t0 = t_abs
            self.last_key = key

        u = smoothstep((t_abs - self.trans_t0) / self.trans_dur)
        self.cur_cx = self.from_cx + (tcx - self.from_cx) * u
        self.cur_cy = self.from_cy + (tcy - self.from_cy) * u
        self.cur_zoom = max(1.0, min(2.5, self.from_zoom + (tz - self.from_zoom) * u))
        return self.cur_cx, self.cur_cy, self.cur_zoom


def draw_markers(full, world, t_abs, crop_box, active_markers, active_chips, fonts, seg_name=None):
    """Gambar marker (cincin berdenyut + segitiga + chip nama) & chip terpasang di koordinat layar."""
    if not active_markers:
        return full
    x0, y0, cw, ch = crop_box
    sx_scale = W / cw
    sy_scale = H / ch
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    font_pop = fonts["pop"]
    placed_boxes = []

    for m in active_markers:
        dt = t_abs - m["t"]
        alpha = max(0.0, min(1.0, dt / 0.3, (4.0 - dt) / 0.3))
        if alpha <= 0.01:
            continue
        subj = m["subject"]
        gx, gy = get_subject_pos(world, subj, seg_name, t_abs)
        sx = (gx - x0) * sx_scale
        sy = (gy - y0) * sy_scale
        if sx < -60 or sx > W + 60 or sy < -60 or sy > H + 60:
            continue

        col = get_subject_color(world, subj, seg_name)
        base_r = SUBJECT_RADIUS.get(subj, 16) * sx_scale * 0.9
        # Pada zoom tinggi, jaga agar cincin tetap proporsional
        base_r = min(base_r, 95.0)
        r = base_r + 3.5 * math.sin(t_abs * 6.5)

        a_ring = int(240 * alpha)
        a_out = int(210 * alpha)
        a_bg = int(230 * alpha)
        a_txt = int(255 * alpha)

        # Cincin berdenyut
        od.ellipse([sx - r, sy - r, sx + r, sy + r], outline=(10, 10, 10, a_out), width=6)
        od.ellipse([sx - r, sy - r, sx + r, sy + r], outline=col + (a_ring,), width=3)

        # Segitiga kecil di atas cincin
        tip_y = max(72.0, sy - r - 4)
        tri = [(sx, tip_y), (sx - 8, tip_y - 11), (sx + 8, tip_y - 11)]
        od.polygon(tri, fill=col + (a_ring,), outline=(10, 10, 10, a_out))

        # Chip nama di atas segitiga
        lbl = MARKER_LABELS.get(subj, subj.upper())
        tw = od.textlength(lbl, font=font_pop)
        chip_w = int(tw) + 20
        chip_h = 26
        cx0 = max(8, min(W - chip_w - 8, int(round(sx - chip_w / 2))))
        cy0 = max(56, min(H - 102, int(round(tip_y - 14 - chip_h))))

        # Hindari tumpang tindih antar chip marker
        for _ in range(4):
            hit = False
            for (bx0, by0, bx1, by1) in placed_boxes:
                if not (cx0 + chip_w + 4 <= bx0 or cx0 >= bx1 + 4 or cy0 + chip_h + 4 <= by0 or cy0 >= by1 + 4):
                    if cy0 - (chip_h + 6) >= 56:
                        cy0 -= (chip_h + 6)
                    else:
                        cy0 = min(H - 102, by1 + 6)
                    hit = True
                    break
            if not hit:
                break
        placed_boxes.append((cx0, cy0, cx0 + chip_w, cy0 + chip_h))

        od.rounded_rectangle([cx0, cy0, cx0 + chip_w, cy0 + chip_h], radius=6,
                             fill=COL_DARK + (a_bg,), outline=col + (a_txt,), width=2)
        od.text((cx0 + 10, cy0 + 6), lbl, font=font_pop, fill=(255, 250, 235, a_txt))

        # Chip tambahan terpasang (mis. "88 TAHUN" di samping Mulyadi)
        for chp in active_chips:
            if chp.get("attach") == subj:
                cdt = t_abs - chp["t"]
                cdur = chp.get("dur", 4.0)
                ca = max(0.0, min(1.0, cdt / 0.3, (cdur - cdt) / 0.3))
                if ca <= 0.01:
                    continue
                ctext = chp["text"]
                ctw = od.textlength(ctext, font=font_pop)
                cw_ = int(ctw) + 20
                ax0 = cx0 + chip_w + 8
                if ax0 + cw_ > W - 8:
                    ax0 = max(8, cx0 - cw_ - 8)
                od.rounded_rectangle([ax0, cy0, ax0 + cw_, cy0 + chip_h], radius=6,
                                     fill=COL_DARK + (int(235 * ca),),
                                     outline=COL_GOLD + (int(255 * ca),), width=2)
                od.text((ax0 + 10, cy0 + 6), ctext, font=font_pop,
                        fill=COL_GOLD + (int(255 * ca),))
                placed_boxes.append((ax0, cy0, ax0 + cw_, cy0 + chip_h))

    return Image.alpha_composite(full.convert("RGBA"), ov).convert("RGB")


def _draw_stamp_badge(full, text, dt, dur, font_banner, y_top=90):
    alpha = 1.0 if dt < dur else max(0.0, (dur + 0.4 - dt) / 0.4)
    if alpha <= 0.01:
        return full
    scale = 1.15 - 0.15 * (dt / 0.2) if dt < 0.2 else 1.0
    tmp_d = ImageDraw.Draw(full)
    bw = int(tmp_d.textlength(text, font=font_banner)) + 48
    bh = 58
    badge = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    a_bg = int(235 * alpha)
    a_fg = int(255 * alpha)
    bd.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=14,
                         fill=COL_DARK + (a_bg,), outline=COL_GOLD + (a_fg,), width=3)
    bd.text((24, 15), text, font=font_banner, fill=COL_CREAM + (a_fg,))
    if scale != 1.0:
        sw, sh = max(1, int(round(bw * scale))), max(1, int(round(bh * scale)))
        badge = badge.resize((sw, sh), Image.BILINEAR)
    else:
        sw, sh = bw, bh
    px = (W - sw) // 2
    py = int(round(y_top + (bh - sh) / 2))
    base = full.convert("RGBA")
    base.alpha_composite(badge, (px, py))
    return base.convert("RGB")


def draw_stamps(full, t_abs, font_banner):
    for s in STAMPS:
        dt = t_abs - s["t"]
        dur = s["dur"]
        if 0.0 <= dt < dur + 0.4:
            txt = f'"{s["text"]}"' if s["text"] == "KEBERUNTUNGAN SEMUSIM" else s["text"]
            full = _draw_stamp_badge(full, txt, dt, dur, font_banner, y_top=90)
    return full


def draw_migrant_counter(full, t_abs, font_pop):
    for c in COUNTERS:
        if c["t0"] <= t_abs <= c["t1"]:
            p = (t_abs - c["t0"]) / max(0.01, c["t1"] - c["t0"])
            val = round(c["from"] + (c["to"] - c["from"]) * max(0.0, min(1.0, p)))
            txt = f"{c['label']}: {val}"
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            tw = od.textlength(txt, font=font_pop)
            bw = int(tw) + 24
            od.rounded_rectangle([24, 56, 24 + bw, 84], radius=8,
                                 fill=COL_DARK + (230,), outline=COL_GOLD + (255,), width=2)
            od.text((36, 63), txt, font=font_pop, fill=COL_CREAM + (255,))
            return Image.alpha_composite(full.convert("RGBA"), ov).convert("RGB")
    return full


# ---------------- SHOWCASE (s01) ----------------
def _build_sunset_base():
    img = Image.new("RGB", (GW, GH))
    px = img.load()
    top, mid, bot = (42, 26, 74), (180, 89, 42), (242, 165, 74)
    for y in range(GH):
        if y < 150:
            t = y / 150
            c = tuple(int(top[i] + (mid[i] - top[i]) * t) for i in range(3))
        else:
            t = (y - 150) / 90
            c = tuple(int(mid[i] + (bot[i] - mid[i]) * min(1, t)) for i in range(3))
        for x in range(GW):
            px[x, y] = c
    d = ImageDraw.Draw(img)
    d.ellipse([290, 110, 370, 190], fill=(255, 226, 150))
    d.ellipse([298, 118, 362, 182], fill=(255, 240, 190))
    d.rectangle([0, 240, GW, GH], fill=(74, 96, 52))
    d.rectangle([0, 240, GW, 248], fill=(92, 116, 62))
    for (hx, hy) in [(60, 200), (560, 205)]:
        d.rectangle([hx, hy, hx + 34, hy + 40], fill=(52, 40, 34))
        d.polygon([(hx - 4, hy), (hx + 17, hy - 16), (hx + 38, hy)], fill=(40, 30, 26))
    for (tx, ty) in [(430, 195), (90, 195)]:
        d.rectangle([tx + 6, ty + 18, tx + 9, ty + 50], fill=(40, 30, 26))
        d.ellipse([tx, ty, tx + 26, ty + 26], fill=(44, 66, 36))
    return img

_SUNSET_BASE = _build_sunset_base()

def render_showcase(f, who, fonts):
    """Close-up 2D tokoh bergaya sunset + kartu nama + 3 chip sifat + label anotasi."""
    img = _SUNSET_BASE.copy()
    d = ImageDraw.Draw(img)
    for (cx, cy) in [(120 + (f // 3) % 40, 100), (300 + (f // 4) % 30, 92)]:
        d.ellipse([cx, cy, cx + 44, cy + 12], fill=(255, 220, 200))
        d.ellipse([cx + 10, cy - 6, cx + 34, cy + 8], fill=(255, 230, 210))

    blink = (f % 100) < 5
    bob = 1 if (f // 15) % 2 == 0 else 0
    x0, gy = 155, 300
    if who == "kevin":
        draw_kevin(d, x0, gy, mouth="closed", blink=blink, expr="happy", bob=bob)
    else:
        draw_mulyadi(d, x0, gy, mouth="closed", blink=blink, expr="stern", bob=bob)

    # Crop [40, 83, 520, 353] (480x270) -> upscale NEAREST 1280x720 (skala 8/3)
    cx0, cy0, cw, ch = 40, 83, 480, 270
    full = img.crop((cx0, cy0, cx0 + cw, cy0 + ch)).resize((W, H), Image.NEAREST)
    full = grade(full)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)

    sx_s, sy_s = W / cw, H / ch
    def to_scr(gx, gy_):
        return (int(round((gx - cx0) * sx_s)), int(round((gy_ - cy0) * sy_s)))

    is_kevin = (who == "kevin")
    accent = COL_GOLD if is_kevin else COL_GREEN
    font_pop = fonts["pop"]
    font_big = fonts["big"]
    font_sub = fonts["sub"]

    # Anotasi menunjuk ciri tokoh
    if is_kevin:
        annots = [
            ("RAMBUT RAPI", (40, 175), to_scr(x0 + 18, gy - bob - 114)),
            ("GULUNGAN RENCANA", (24, 465), to_scr(x0 + 2, gy - bob - 55)),
        ]
    else:
        annots = [
            ("RAMBUT PUTIH", (40, 175), to_scr(x0 + 18, gy - bob - 114)),
            ("TONGKAT", (442, 470), to_scr(x0 + 44, gy - bob - 45)),
        ]
    for label, (ax, ay), (tx, ty) in annots:
        tw = od.textlength(label, font=font_pop)
        aw, ah = int(tw) + 20, 28
        # Garis penunjuk dari tepi chip ke titik ciri
        lx = ax + aw if ax + aw < tx else ax
        ly = ay + ah // 2
        od.line([(lx, ly), (tx, ty)], fill=accent + (240,), width=3)
        od.ellipse([tx - 5, ty - 5, tx + 5, ty + 5], fill=accent + (255,), outline=COL_DARK + (255,), width=2)
        od.rounded_rectangle([ax, ay, ax + aw, ay + ah], radius=6,
                             fill=COL_DARK + (235,), outline=accent + (255,), width=2)
        od.text((ax + 10, ay + 7), label, font=font_pop, fill=COL_CREAM + (255,))

    # Kartu nama + 3 chip sifat di kanan
    rx0, rx1 = 580, 1220
    od.rounded_rectangle([rx0, 120, rx1, 240], radius=14,
                         fill=COL_DARK + (235,), outline=accent + (255,), width=3)
    if is_kevin:
        name_txt, age_txt = "KEVIN", "26 TAHUN"
        age_col = (140, 200, 255)
        traits = ["> VISIONER", "> MAU MENDENGAR", "> BELAJAR DARI KESALAHAN"]
        trait_col = COL_CREAM
    else:
        name_txt, age_txt = "PAK MULYADI", "70 TAHUN"
        age_col = (240, 180, 130)
        traits = ["X KERAS KEPALA", "X ANTI KRITIK", "X TIDAK BERPIKIR MAJU"]
        trait_col = (255, 200, 190)

    od.text((rx0 + 28, 140), name_txt, font=font_big, fill=accent + (255,))
    od.text((rx0 + 28, 190), age_txt, font=font_sub, fill=age_col + (255,))

    for i, tr in enumerate(traits):
        ty0 = 268 + i * 74
        od.rounded_rectangle([rx0, ty0, rx1, ty0 + 54], radius=10,
                             fill=COL_DARK + (225,), outline=accent + (220,), width=2)
        od.text((rx0 + 24, ty0 + 18), tr, font=font_sub, fill=trait_col + (255,))

    return Image.alpha_composite(full.convert("RGBA"), ov).convert("RGB")


# ---------------- SPLIT FIELDS (s04) ----------------
def render_split_fields(grid_img, fonts):
    """Belah dua satu frame grid: sawah Sinarbaru (kiri) vs Tanjungsari (kanan)."""
    left = grid_img.crop((18, 45, 238, 293)).resize((W // 2, H), Image.NEAREST)
    right = grid_img.crop((395, 45, 615, 293)).resize((W // 2, H), Image.NEAREST)
    out = Image.new("RGB", (W, H))
    out.paste(left, (0, 0))
    out.paste(right, (W // 2, 0))
    out = grade(out)

    d = ImageDraw.Draw(out)
    # Bingkai warna sisi + garis tengah (di bawah HUD y=50)
    d.rectangle([0, 50, W // 2 - 3, H - 1], outline=COL_GOLD, width=4)
    d.rectangle([W // 2 + 3, 50, W - 1, H - 1], outline=COL_GREEN, width=4)
    d.rectangle([W // 2 - 3, 50, W // 2 + 3, H - 1], fill=COL_DARK)

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    font_sub = fonts["sub"]
    font_pop = fonts["pop"]

    for (bx, txt, col) in [(24, "SINARBARU", COL_GOLD), (W // 2 + 24, "TANJUNGSARI", COL_GREEN)]:
        tw = od.textlength(txt, font=font_sub)
        od.rounded_rectangle([bx, 72, bx + int(tw) + 28, 108], radius=8,
                             fill=COL_DARK + (235,), outline=col + (255,), width=2)
        od.text((bx + 14, 81), txt, font=font_sub, fill=col + (255,))

    chip = "LIHAT SAJA SAWAHNYA"
    cw_ = int(od.textlength(chip, font=font_pop)) + 32
    cx0 = (W - cw_) // 2
    od.rounded_rectangle([cx0, 122, cx0 + cw_, 154], radius=10,
                         fill=COL_DARK + (235,), outline=COL_GOLD + (255,), width=2)
    od.text((cx0 + 16, 130), chip, font=font_pop, fill=COL_CREAM + (255,))

    return Image.alpha_composite(out.convert("RGBA"), ov).convert("RGB")


# ---------------- CHART (s17) ----------------
_CHART_BG = None
_CHART_BOX = (150, 155, 1130, 585)  # x0, y0, x1, y1
_CHART_PTS = sorted((yr, s_val, t_val) for yr, (s_val, t_val) in CHECK.items())

def _get_chart_bg(fonts):
    global _CHART_BG
    if _CHART_BG is not None:
        return _CHART_BG
    bg = Image.new("RGB", (W, H), (20, 22, 30))
    d = ImageDraw.Draw(bg)
    x0, y0, x1, y1 = _CHART_BOX
    font_banner = fonts["banner"]
    font_pop = fonts["pop"]
    font_card = fonts["card"]

    # Grid & sumbu skor 0..100
    for sc in range(0, 101, 20):
        yy = int(round(y1 - (y1 - y0) * (sc / 100.0)))
        d.line([(x0, yy), (x1, yy)], fill=(42, 46, 60), width=1)
        lbl = str(sc)
        lw = d.textlength(lbl, font=font_card)
        d.text((x0 - lw - 14, yy - 7), lbl, font=font_card, fill=(170, 176, 194))

    # Grid & sumbu tahun 0..20
    for yr in (0, 2, 4, 6, 10, 14, 20):
        xx = int(round(x0 + (x1 - x0) * (yr / 20.0)))
        d.line([(xx, y0), (xx, y1)], fill=(42, 46, 60), width=1)
        lbl = f"TH {yr}"
        lw = d.textlength(lbl, font=font_card)
        d.text((xx - lw / 2, y1 + 14), lbl, font=font_card, fill=(170, 176, 194))

    d.line([(x0, y0), (x0, y1), (x1, y1)], fill=(210, 214, 226), width=3)

    # Judul + legenda
    title = "INDEKS KEMAKMURAN"
    tw = d.textlength(title, font=font_banner)
    d.text(((W - tw) / 2, 30), title, font=font_banner, fill=COL_GOLD)

    lx = 390
    d.rectangle([lx, 76, lx + 26, 90], fill=COL_GOLD)
    d.text((lx + 36, 76), "SINARBARU", font=font_pop, fill=COL_GOLD)
    rx = 690
    d.rectangle([rx, 76, rx + 26, 90], fill=COL_GREEN)
    d.text((rx + 36, 76), "TANJUNGSARI", font=font_pop, fill=COL_GREEN)

    _CHART_BG = bg
    return bg


def render_chart(t_abs, fonts):
    """Layar penuh grafik garis animasi INDEKS KEMAKMURAN (548.96 - 566.96)."""
    img = _get_chart_bg(fonts).copy()
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = _CHART_BOX
    font_pop = fonts["pop"]
    font_sub = fonts["sub"]

    p = max(0.0, min(1.0, (t_abs - 548.96) / 18.0))
    cur_year = 20.0 * p

    def to_xy(yr, val):
        xx = x0 + (x1 - x0) * (yr / 20.0)
        yy = y1 - (y1 - y0) * (val / 100.0)
        return (xx, yy)

    pts_s, pts_t = [], []
    passed = []
    for i, (yr, sv, tv) in enumerate(_CHART_PTS):
        if yr <= cur_year + 1e-6:
            pts_s.append(to_xy(yr, sv))
            pts_t.append(to_xy(yr, tv))
            passed.append((yr, sv, tv))
        else:
            prev_yr, prev_s, prev_t = _CHART_PTS[i - 1]
            frac = (cur_year - prev_yr) / max(1e-6, yr - prev_yr)
            pts_s.append(to_xy(cur_year, prev_s + (sv - prev_s) * frac))
            pts_t.append(to_xy(cur_year, prev_t + (tv - prev_t) * frac))
            break

    if len(pts_s) >= 2:
        d.line(pts_s, fill=COL_GOLD, width=6)
        d.line(pts_t, fill=COL_GREEN, width=6)

    for (yr, sv, tv) in passed:
        sx, sy = to_xy(yr, sv)
        tx, ty = to_xy(yr, tv)
        d.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], fill=COL_GOLD, outline=COL_DARK, width=2)
        d.ellipse([tx - 6, ty - 6, tx + 6, ty + 6], fill=COL_GREEN, outline=COL_DARK, width=2)
        if yr == 20:
            # Label akhir 88 & 56
            d.rounded_rectangle([sx + 12, sy - 16, sx + 64, sy + 16], radius=6,
                                fill=COL_DARK, outline=COL_GOLD, width=2)
            d.text((sx + 20, sy - 9), str(sv), font=font_sub, fill=COL_GOLD)
            d.rounded_rectangle([tx + 12, ty - 16, tx + 64, ty + 16], radius=6,
                                fill=COL_DARK, outline=COL_GREEN, width=2)
            d.text((tx + 20, ty - 9), str(tv), font=font_sub, fill=COL_GREEN)
        elif yr > 0:
            s_dy = -24 if sv >= tv else 12
            t_dy = 12 if sv >= tv else -24
            d.text((sx - 12, sy + s_dy), str(sv), font=font_pop, fill=COL_GOLD)
            d.text((tx - 12, ty + t_dy), str(tv), font=font_pop, fill=COL_GREEN)

    # Stempel "SINARBARU MENANG" di 2 detik terakhir mode (564.96 - 566.96)
    if t_abs >= 564.96:
        img = _draw_stamp_badge(img, "SINARBARU MENANG", t_abs - 564.96, 2.0, fonts["banner"], y_top=105)

    return img
