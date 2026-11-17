#!/usr/bin/env python3
"""Render penuh video simulasi (32-bit gaya game) per segmen, streaming ke ffmpeg.
Pakai: python3 render_full.py --list | --segment s01 | --all
Tiap segmen -> segments/<nama>.mp4 (1280x720, 30fps, tanpa audio; audio digabung di rakit akhir)."""
import argparse, json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world import (World, score_at, load_font, text_outline, grade, draw_hud,
                   draw_banner, W, H, GW, GH)
from assets import draw_kevin, draw_mulyadi, draw_sari, ujang_frames, PUMP, TREE
from v2_effects import (CameraController, get_active_mode, get_active_markers,
                        get_active_chips, draw_markers, draw_stamps,
                        draw_migrant_counter, render_showcase,
                        render_split_fields, render_chart)
from v3_effects import get_moment, render_v3_frame

PROJ = os.path.dirname(os.path.abspath(__file__))
SEGDIR = os.path.join(PROJ, "segments")
os.makedirs(SEGDIR, exist_ok=True)
FPS = 30
TOTAL_T = 746.52

FONT_HUD = load_font(16); FONT_LBL = load_font(14); FONT_END = load_font(20)
FONT_BANNER = load_font(24); FONT_POP = load_font(14)
FONT_TITLE = load_font(32); FONT_SUB = load_font(16); FONT_CARD = load_font(13)
FONT_CARD_T = load_font(16); FONT_BIG = load_font(28); FONT_Q = load_font(20)
FONT_BUB = None  # diisi di dialog (ukuran grid)
V2_FONTS = {"hud": FONT_HUD, "lbl": FONT_LBL, "end": FONT_END, "banner": FONT_BANNER,
            "pop": FONT_POP, "title": FONT_TITLE, "sub": FONT_SUB, "card": FONT_CARD,
            "card_t": FONT_CARD_T, "big": FONT_BIG, "q": FONT_Q}

# ---------------- segmen ----------------
# kind: map | dialog | grid | split | counter | closing
SEGMENTS = [
    dict(name="s01_coldopen", t0=0.0, t1=53.43, kind="map", y0=1, y1=1,
         title=(0.0, 6.0), bet=(34.28, 47.88, "Siapa yang lebih maju? Tulis tebakanmu di komentar!")),
    dict(name="s02_aturan", t0=53.43, t1=131.86, kind="map", y0=1, y1=1,
         cards=[(73.12, "1. TEKNOLOGI", "Kevin: pompa, bibit, penggilingan", "Mulyadi: melarang ketiganya"),
                (84.14, "2. RENCANA", "Kevin: rencana 10 tahun tertulis", "Mulyadi: ikut musim"),
                (97.1, "3. BELAJAR", "Kevin: pelatihan, akui kesalahan", "Mulyadi: anti kritik")]),
    dict(name="s03_tahun12", t0=131.86, t1=191.52, kind="map", y0=1, y1=2),
    dict(name="s04_tahun34", t0=191.52, t1=244.16, kind="map", y0=3, y1=4),
    dict(name="s05_tahun56", t0=244.16, t1=293.8, kind="map", y0=5, y1=6),
    dict(name="s06_tahun7", t0=293.8, t1=307.38, kind="map", y0=7, y1=7),
    dict(name="s07_dialog1", t0=307.38, t1=324.65, kind="dialog", left="mulyadi", right="sari",
         lines=[("mulyadi", 307.38, 309.78, "Sari! Apa yang kau lakukan di sini?"),
                ("sari", 310.18, 314.64, "Belajar, Pak. Satu pompa bisa mengairi sepuluh sawah dalam sehari."),
                ("mulyadi", 314.88, 321.94, "Kita tidak butuh itu! Sawah kita hidup dari hujan, seperti zaman bapakmu! Jangan ajari aku cara bertani!"),
                ("sari", 322.18, 324.24, "Tapi Pak, kalau hujannya tidak datang?")]),
    dict(name="s08_jembatan1", t0=324.65, t1=330.24, kind="map", y0=8, y1=8),
    dict(name="s09_tahun910", t0=330.24, t1=367.66, kind="map", y0=9, y1=10,
         banners=[(330.24, "KEMARAU PANJANG!", 4.0)]),
    dict(name="s10_taruhan_twist", t0=367.66, t1=415.44, kind="map", y0=10, y1=12,
         bet=(370.92, 375.88, "Bisa nyalip enggak? Tebak sekarang!"),
         banners=[(375.88, "EKSODUS BESAR!", 4.0)]),
    dict(name="s11_dialog2", t0=415.44, t1=434.46, kind="dialog", left="mulyadi", right="sari",
         lines=[("sari", 415.44, 422.24, "Pak, tinggal kita yang bertahan. Ayolah, izinkan satu pompa saja. Satu."),
                ("mulyadi", 422.84, 426.76, "Kalau aku mengizinkan, berarti 30 tahun aku salah."),
                ("sari", 427.2, 433.86, "Tidak, Pak. Berarti 30 tahun Bapak menjaga desa ini. Dan sekarang giliran Bapak belajar satu hal baru.")]),
    dict(name="s12_tahun1314", t0=434.46, t1=472.5, kind="map", y0=13, y1=14,
         banners=[(435.06, "POMPA RAHASIA", 4.0)]),
    dict(name="s13_tahun1517", t0=472.5, t1=513.8, kind="map", y0=15, y1=17,
         banners=[(490.0, "PASAR BERSAMA", 4.0)]),
    dict(name="s14_tahun18", t0=513.8, t1=524.68, kind="map", y0=18, y1=18),
    dict(name="s15_dialog3", t0=524.68, t1=537.92, kind="dialog", left="mulyadi", right="sari",
         hug_from=531.56,
         lines=[("mulyadi", 524.68, 527.58, "Aku salah. Bukan teknologinya yang jahat."),
                ("mulyadi", 527.58, 531.56, "Akunya yang takut. Aku takut dunia berubah, dan aku tidak ikut berubah.")]),
    dict(name="s16_tahun19", t0=537.92, t1=545.74, kind="map", y0=19, y1=19),
    dict(name="s17_tahun20", t0=545.74, t1=575.76, kind="map", y0=20, y1=20, endcard=6.0),
    dict(name="s18_ujang", t0=575.76, t1=601.84, kind="split"),
    dict(name="s19_eksperimen", t0=601.84, t1=647.3, kind="counter"),
    dict(name="s20_seratus", t0=647.3, t1=695.58, kind="grid"),
    dict(name="s21_penutup", t0=695.58, t1=746.52, kind="closing"),
]

# ---------------- ffmpeg ----------------
def open_encoder(out_path):
    return subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
         out_path],
        stdin=subprocess.PIPE)

def wrap_text(d, text, font, max_w):
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

# ---------------- peta ----------------
def render_map(seg, enc, nframes):
    world = World(seed=23, start_year=int(seg["y0"]))
    cam = CameraController()
    prev_scores = None
    popup_until = -1
    popup_ds = popup_dt = 0
    for f in range(nframes):
        t_abs = seg["t0"] + f / FPS
        frac = f / max(1, nframes - 1)
        yf = seg["y0"] + (seg["y1"] - seg["y0"]) * frac
        sl, sr = score_at(yf)
        if prev_scores is not None and (sl, sr) != prev_scores:
            popup_ds, popup_dt = sl - prev_scores[0], sr - prev_scores[1]
            popup_until = f + 18
        prev_scores = (sl, sr)

        moment = get_moment(t_abs)
        if moment:
            if moment["kind"] == "mg":
                grid_img = world.render_grid(f, yf)
                cam.update(t_abs, world, seg, [])
                bg_full, _ = world.apply_camera(grid_img, 320.0, 180.0, 1.0)
                bg_full = grade(bg_full)
                full = render_v3_frame(moment, t_abs, bg_img=bg_full)
            else:
                world.step_only(f, yf)
                cam.update(t_abs, world, seg, [])
                full = render_v3_frame(moment, t_abs)
            fd = ImageDraw.Draw(full)
            draw_hud(fd, max(1, min(20, round(yf))), sl, sr, FONT_HUD, FONT_LBL, show_side_labels=False)
            enc.stdin.write(full.tobytes())
            continue

        mode = get_active_mode(t_abs)
        active_markers = get_active_markers(t_abs)
        active_chips = get_active_chips(t_abs)

        if mode and mode["kind"] in ("showcase", "chart"):
            fade_a = max(0.0, min(1.0, (t_abs - mode["t0"]) / 0.4, (mode["t1"] - t_abs) / 0.4))
            if fade_a >= 0.999:
                world.step_only(f, yf)
                full = (render_showcase(f, mode["who"], V2_FONTS)
                        if mode["kind"] == "showcase" else render_chart(t_abs, V2_FONTS))
                enc.stdin.write(full.tobytes())
                continue
            grid_img = world.render_grid(f, yf)
            cx, cy, zm = cam.update(t_abs, world, seg, [])
            map_full, _ = world.apply_camera(grid_img, cx, cy, zm)
            map_full = grade(map_full)
            md = ImageDraw.Draw(map_full)
            draw_hud(md, max(1, min(20, round(yf))), sl, sr, FONT_HUD, FONT_LBL)
            mode_full = (render_showcase(f, mode["who"], V2_FONTS)
                         if mode["kind"] == "showcase" else render_chart(t_abs, V2_FONTS))
            full = Image.blend(map_full, mode_full, fade_a)
            enc.stdin.write(full.tobytes())
            continue

        grid_img = world.render_grid(f, yf)
        if mode and mode["kind"] == "split_fields":
            full = render_split_fields(grid_img, V2_FONTS)
        else:
            cx, cy, zm = cam.update(t_abs, world, seg, active_markers)
            full, crop_box = world.apply_camera(grid_img, cx, cy, zm)
            full = grade(full)
            full = draw_markers(full, world, t_abs, crop_box, active_markers,
                                active_chips, V2_FONTS, seg["name"])

        fd = ImageDraw.Draw(full)
        is_split_fields = bool(mode and mode["kind"] == "split_fields")
        draw_hud(fd, max(1, min(20, round(yf))), sl, sr, FONT_HUD, FONT_LBL,
                 show_side_labels=not is_split_fields)
        if f < popup_until:
            yy = 60 + (f - (popup_until - 18))
            if popup_ds:
                text_outline(fd, (200, yy), f"+{popup_ds}", FONT_POP, (255, 220, 120))
            if popup_dt:
                text_outline(fd, (W - 260, yy), f"+{popup_dt}" if popup_dt > 0 else f"{popup_dt}",
                             FONT_POP, (140, 230, 140) if popup_dt > 0 else (240, 120, 100))
        # counter migran (di bawah HUD kiri atas)
        full = draw_migrant_counter(full, t_abs, FONT_POP)
        fd = ImageDraw.Draw(full)
        # spanduk kejadian
        for (bt, btext, bdur) in seg.get("banners", []):
            dt = t_abs - bt
            if 0 <= dt < bdur:
                alpha = 255 if dt < bdur - 1 else int(255 * (bdur - dt))
                full = draw_banner(full, btext, FONT_BANNER, alpha)
                fd = ImageDraw.Draw(full)
        # stempel v2
        full = draw_stamps(full, t_abs, FONT_BANNER)
        fd = ImageDraw.Draw(full)
        # kartu aturan
        cards = seg.get("cards", [])
        active = None
        for (ct, ctitle, c1, c2) in cards:
            if t_abs >= ct:
                active = (ctitle, c1, c2)
        if active:
            ctitle, c1, c2 = active
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.rounded_rectangle([340, 490, 940, 616], radius=12, fill=(20, 18, 16, 225),
                                 outline=(255, 220, 120, 255), width=3)
            od.text((364, 504), ctitle, font=FONT_CARD_T, fill=(255, 220, 120, 255))
            od.text((364, 538), "> " + c1, font=FONT_CARD, fill=(255, 255, 255, 255))
            od.text((364, 570), "X " + c2, font=FONT_CARD, fill=(240, 160, 150, 255))
            full = Image.alpha_composite(full.convert("RGBA"), ov).convert("RGB")
            fd = ImageDraw.Draw(full)
        # kartu judul (cold open)
        if "title" in seg:
            t_start, t_end = seg["title"]
            if t_start <= t_abs < t_end:
                alpha = 255 if t_abs < t_end - 1 else int(255 * (t_end - t_abs))
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(ov)
                od.rectangle([0, 0, W, H], fill=(10, 8, 6, int(alpha * 0.55)))
                t1, t2 = "SIMULASI 20 TAHUN!", "Desa Dipimpin Anak Muda vs Orang Tua"
                w1 = od.textlength(t1, font=FONT_TITLE)
                w2 = od.textlength(t2, font=FONT_SUB)
                od.text(((W - w1) / 2, 300), t1, font=FONT_TITLE, fill=(255, 220, 120, alpha))
                od.text(((W - w2) / 2, 368), t2, font=FONT_SUB, fill=(255, 255, 255, alpha))
                full = Image.alpha_composite(full.convert("RGBA"), ov).convert("RGB")
                fd = ImageDraw.Draw(full)
        # overlay taruhan
        if "bet" in seg:
            b0, b1, btext = seg["bet"]
            if b0 <= t_abs < b1:
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(ov)
                bw = int(od.textlength(btext, font=FONT_SUB)) + 48
                bx, by = (W - bw) // 2, H - 96
                od.rounded_rectangle([bx, by, bx + bw, by + 52], radius=12,
                                     fill=(20, 18, 16, 225), outline=(255, 220, 120, 255), width=3)
                od.text((bx + 24, by + 10), btext, font=FONT_SUB, fill=(255, 240, 200, 255))
                full = Image.alpha_composite(full.convert("RGBA"), ov).convert("RGB")
                fd = ImageDraw.Draw(full)
        # kartu akhir
        if "endcard" in seg and t_abs >= seg["t1"] - seg["endcard"]:
            s = "SIMULASI SELESAI — SINARBARU MENANG 88 vs 56"
            tw = fd.textlength(s, font=FONT_END)
            fd.rectangle([(W - tw) / 2 - 16, H - 80, (W + tw) / 2 + 16, H - 30], fill=(20, 18, 16))
            text_outline(fd, ((W - tw) / 2, H - 74), s, FONT_END, (255, 220, 120))
        enc.stdin.write(full.tobytes())

# ---------------- dialog ----------------
PORTRAITS = {"kevin": draw_kevin, "mulyadi": draw_mulyadi, "sari": draw_sari}
NAMES = {"kevin": "KEVIN", "mulyadi": "PAK MULYADI", "sari": "SARI"}

def sunset_bg(f):
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
    # matahari + sinar (di tengah, tidak menabrak kepala tokoh)
    d.ellipse([290, 110, 370, 190], fill=(255, 226, 150))
    d.ellipse([298, 118, 362, 182], fill=(255, 240, 190))
    for (cx, cy, s) in [(120 + (f // 3) % 40, 60, 1), (300 + (f // 4) % 30, 40, 1)]:
        d.ellipse([cx, cy, cx + 44, cy + 12], fill=(255, 220, 200))
        d.ellipse([cx + 10, cy - 6, cx + 34, cy + 8], fill=(255, 230, 210))
    # tanah + siluet
    d.rectangle([0, 240, GW, GH], fill=(74, 96, 52))
    d.rectangle([0, 240, GW, 248], fill=(92, 116, 62))
    for (hx, hy) in [(60, 200), (560, 205)]:
        d.rectangle([hx, hy, hx + 34, hy + 40], fill=(52, 40, 34))
        d.polygon([(hx - 4, hy), (hx + 17, hy - 16), (hx + 38, hy)], fill=(40, 30, 26))
    for (tx, ty) in [(150, 190), (420, 195)]:
        d.rectangle([tx + 6, ty + 18, tx + 9, ty + 50], fill=(40, 30, 26))
        d.ellipse([tx, ty, tx + 26, ty + 26], fill=(44, 66, 36))
    return img, d

def render_dialog(seg, enc, nframes):
    font_bub = load_font(16)  # bubble: font pixel 16px, baris 28px
    left_fn, right_fn = PORTRAITS[seg["left"]], PORTRAITS[seg["right"]]
    for f in range(nframes):
        t_abs = seg["t0"] + f / FPS
        img, d = sunset_bg(f)
        # baris aktif
        active = None
        for (sp, s0, s1, txt) in seg["lines"]:
            if s0 <= t_abs < s1 + 0.4:
                active = (sp, s0, s1, txt)
        # posisi: pelukan menggeser Sari mendekat
        lx, rx = 110, 470
        hug = seg.get("hug_from") and t_abs >= seg["hug_from"]
        if hug:
            rx = 400
        bob_l = 1 if (f // 15) % 2 == 0 else 0
        bob_r = 1 if (f // 15) % 2 == 1 else 0
        blink = (f % 100) < 5
        # pendengar digambar dulu (akan diredupkan), pembicara belakangan
        spk = active[0] if active else None
        def draw_char(side):
            fn = left_fn if side == "left" else right_fn
            who = seg["left"] if side == "left" else seg["right"]
            speaking = (spk == who)
            mouth = "open" if (speaking and (f // 5) % 2 == 0) else "closed"
            expr = "stern" if who == "mulyadi" else "neutral"
            if hug and who == "sari":
                expr = "happy"
            fn(d, lx if side == "left" else rx, 340, mouth=mouth,
               blink=blink, expr=expr, bob=bob_l if side == "left" else bob_r)
        # gambar keduanya, lalu redupkan pendengar via overlay
        draw_char("left")
        draw_char("right")
        if spk:
            # redupkan pendengar dengan masker membulat yang di-blur (tepi lembut)
            dim = Image.new("RGBA", (GW, GH), (0, 0, 0, 0))
            dd = ImageDraw.Draw(dim)
            if spk == seg["left"]:
                dd.rounded_rectangle([rx - 14, 200, rx + 60, 345], radius=18, fill=(20, 10, 40, 110))
            else:
                dd.rounded_rectangle([lx - 14, 200, lx + 60, 345], radius=18, fill=(20, 10, 40, 110))
            dim = dim.filter(ImageFilter.GaussianBlur(10))
            img = Image.alpha_composite(img.convert("RGBA"), dim).convert("RGB")
        # zoom pelan + upscale
        zw, zh = GW - 12, GH - 7
        full = img.crop(((GW - zw) // 2, (GH - zh) // 2, (GW + zw) // 2, (GH + zh) // 2))
        full = full.resize((W, H), Image.NEAREST)
        full = grade(full)
        fd = ImageDraw.Draw(full)
        # nama (papan nama di tanah, di depan kaki)
        text_outline(fd, (lx * 2 - 10, 676), NAMES[seg["left"]], FONT_LBL, (255, 240, 200))
        text_outline(fd, (rx * 2 - 10, 676), NAMES[seg["right"]], FONT_LBL, (255, 240, 200))
        # bubble (ukuran dari teks LENGKAP supaya stabil selama typewriter)
        if active and not hug:
            sp, s0, s1, txt = active
            chars = int(len(txt) * min(1.0, (t_abs - s0) / max(0.1, (s1 - s0))))
            shown = txt[:max(1, chars)]
            max_w = 620
            full_lines = wrap_text(fd, txt, font_bub, max_w)
            bw = max(fd.textlength(ln, font=font_bub) for ln in full_lines) + 40
            lines = wrap_text(fd, shown, font_bub, max_w)
            bh = len(full_lines) * 28 + 28
            if sp == seg["left"]:
                bx, by = 60, 90
                tail = [(200, by + bh), (230, by + bh), (190, by + bh + 26)]
            else:
                bx, by = W - 60 - bw, 90
                tail = [(W - 230, by + bh), (W - 200, by + bh), (W - 190, by + bh + 26)]
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.polygon(tail, fill=(255, 252, 245, 255))
            od.rounded_rectangle([bx, by, bx + bw, by + bh], radius=16,
                                 fill=(255, 252, 245, 255), outline=(30, 24, 20, 255), width=4)
            full = Image.alpha_composite(full.convert("RGBA"), ov).convert("RGB")
            fd = ImageDraw.Draw(full)
            for i, ln in enumerate(lines):
                fd.text((bx + 20, by + 14 + i * 28), ln, font=font_bub, fill=(30, 24, 20))
            # tag nama di bubble
            tag = NAMES[sp]
            tw = fd.textlength(tag, font=FONT_POP)
            fd.rounded_rectangle([bx + 12, by - 16, bx + 24 + tw, by + 10], radius=8,
                                 fill=(20, 18, 16))
            fd.text((bx + 18, by - 13), tag, font=FONT_POP, fill=(255, 220, 120))
        enc.stdin.write(full.tobytes())

# ---------------- grid 100x ----------------
def render_grid(seg, enc, nframes):
    fill_end = 663.56
    layers = ["POMPA", "BIBIT", "PELATIHAN", "PENGGILINGAN", "JALAN DAGANG"]
    layer_t0 = 668.22
    for f in range(nframes):
        t_abs = seg["t0"] + f / FPS
        img = Image.new("RGB", (W, H), (24, 22, 30))
        d = ImageDraw.Draw(img)
        title = "SIMULASI DIULANG 100 KALI"
        tw = d.textlength(title, font=FONT_BIG)
        text_outline(d, ((W - tw) / 2, 30), title, FONT_BIG, (255, 220, 120))
        # grid 10x10
        cell, gap, x0, y0 = 52, 8, (W - (10 * 52 + 9 * 8)) // 2, 110
        filled = int(min(100, max(0, (t_abs - 648.0) / (fill_end - 648.0) * 100)))
        for i in range(100):
            r, c = divmod(i, 10)
            x, y = x0 + c * (cell + gap), y0 + r * (cell + gap)
            if i < filled:
                pop = 1.0
                if i == filled - 1:
                    pop = 1.15
                s = int(cell * pop)
                dx = (s - cell) // 2
                d.rounded_rectangle([x - dx, y - dx, x - dx + s, y - dx + s], radius=8,
                                    fill=(92, 160, 222), outline=(180, 220, 255), width=2)
            else:
                d.rounded_rectangle([x, y, x + cell, y + cell], radius=8,
                                    outline=(90, 86, 100), width=2)
        # penghitung
        text_outline(d, (x0, 640), f"VISIONER: {filled}/100", FONT_Q, (140, 200, 255))
        _rt = "TRADISIONAL: 0/100"
        text_outline(d, (x0 + 592 - d.textlength(_rt, font=FONT_Q), 640), _rt, FONT_Q, (240, 130, 110))
        # lima lapis
        if t_abs >= layer_t0:
            shown_layers = min(5, int((t_abs - layer_t0) / 4.0) + 1)
            lx = (W - (5 * 190 + 4 * 12)) // 2
            for i in range(shown_layers):
                x = lx + i * 202
                d.rounded_rectangle([x, 690 - 44, x + 190, 690], radius=10,
                                    fill=(255, 220, 120), outline=(255, 240, 180), width=2)
                tw2 = d.textlength(layers[i], font=FONT_POP)
                d.text((x + (190 - tw2) / 2, 690 - 34), layers[i], font=FONT_POP, fill=(30, 24, 20))
        moment = get_moment(t_abs)
        if moment:
            img = render_v3_frame(moment, t_abs, bg_img=img)
        enc.stdin.write(img.tobytes())

# ---------------- Ujang dua kali ----------------
def render_split(seg, enc, nframes):
    for f in range(nframes):
        t_abs = seg["t0"] + f / FPS
        moment = get_moment(min(t_abs, seg["t1"] - 1e-4))
        full = render_v3_frame(moment, t_abs)
        fd = ImageDraw.Draw(full)
        draw_hud(fd, 20, 88, 56, FONT_HUD, FONT_LBL, show_side_labels=False)
        enc.stdin.write(full.tobytes())

# ---------------- eksperimen balik ----------------
def render_counter(seg, enc, nframes):
    world = World(seed=23, start_year=20)
    cam = CameraController()
    for f in range(nframes):
        t_abs = seg["t0"] + f / FPS
        frac = f / max(1, nframes - 1)
        sl = round(74 + (90 - 74) * frac)
        sr = round(38 + (74 - 38) * frac)
        grid_img = world.render_grid(f, 20, counterfactual=True)
        moment = get_moment(t_abs)
        if moment:
            cam.update(t_abs, world, seg, [])
            bg_full, _ = world.apply_camera(grid_img, 320.0, 180.0, 1.0)
            bg_full = grade(bg_full)
            full = render_v3_frame(moment, t_abs, bg_img=bg_full)
        else:
            active_markers = get_active_markers(t_abs)
            cx, cy, zm = cam.update(t_abs, world, seg, active_markers)
            full, crop_box = world.apply_camera(grid_img, cx, cy, zm)
            full = grade(full)
            full = draw_markers(full, world, t_abs, crop_box, active_markers, [], V2_FONTS, seg["name"])
        fd = ImageDraw.Draw(full)
        fd.rectangle([0, 0, W, 40], fill=(20, 18, 16))
        text_outline(fd, (24, 7), f"SINARBARU  {sl}", FONT_HUD, (255, 220, 120))
        text_outline(fd, (W - 300, 7), f"TANJUNGSARI  {sr}", FONT_HUD, (140, 230, 140))
        t = "TAHUN 20 — KALAU POMPA DITERIMA TAHUN PERTAMA"
        tw = fd.textlength(t, font=FONT_LBL)
        text_outline(fd, ((W - tw) / 2, 9), t, FONT_LBL, (255, 255, 255))
        fd.rectangle([24, 44, 24 + sl * 3, 50], fill=(255, 220, 120))
        fd.rectangle([W - 24 - sr * 3, 44, W - 24, 50], fill=(140, 230, 140))
        if not moment and t_abs >= 617.98:
            full = draw_banner(full, "TANPA EKSODUS - SELISIH 32 JADI 16 POIN", FONT_BANNER)
        enc.stdin.write(full.tobytes())

# ---------------- penutup ----------------
def render_closing(seg, enc, nframes):
    for f in range(nframes):
        t_abs = seg["t0"] + f / FPS
        img = Image.new("RGB", (GW, GH), (30, 26, 40))
        d = ImageDraw.Draw(img)
        for y in range(GH):
            t = y / GH
            c = tuple(int(30 + (70 - 30) * t) if i == 0 else int(26 + (50 - 26) * t) if i == 1 else int(40 + (70 - 40) * t) for i in range(3))
            d.line([(0, y), (GW, y)], fill=c)
        d.rectangle([0, 300, GW, GH], fill=(52, 60, 44))
        draw_kevin(d, 90, 330, blink=(f % 100) < 5, expr="happy", bob=1 if (f // 15) % 2 == 0 else 0)
        draw_mulyadi(d, 470, 330, blink=(f % 100) < 5, expr="neutral", bob=1 if (f // 15) % 2 == 1 else 0)
        full = img.resize((W, H), Image.NEAREST)
        full = grade(full)
        fd = ImageDraw.Draw(full)
        if t_abs < 710.96:
            # fase jawaban: 26 vs 70
            text_outline(fd, (150, 90), "26 TAHUN", FONT_BIG, (140, 200, 255))
            text_outline(fd, (W - 330, 90), "70 TAHUN", FONT_BIG, (240, 180, 130))
            fd.ellipse([W // 2 - 46, 300, W // 2 + 46, 392], fill=(200, 60, 50),
                       outline=(255, 240, 200), width=4)
            vs = "VS"
            tw = fd.textlength(vs, font=FONT_BIG)
            fd.text(((W - tw) / 2, 318), vs, font=FONT_BIG, fill=(255, 255, 255))
            if t_abs >= 702.92:
                s = "BEDA 44 TAHUN — CARA PIKIRNYA KELIHATAN"
                tw = fd.textlength(s, font=FONT_SUB)
                text_outline(fd, ((W - tw) / 2, 560), s, FONT_SUB, (255, 220, 120))
        elif t_abs < 715.96:
            # kartu JAWABAN TARUHAN (tampil 5 dtk setelah 710.96, sebelum pertanyaan)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            alpha = 255 if t_abs < 715.56 else max(0, int(255 * (715.96 - t_abs) / 0.4))
            od.rounded_rectangle([180, 90, W - 180, 286], radius=16,
                                 fill=(20, 18, 16, int(alpha * 0.92)),
                                 outline=(255, 220, 120, alpha), width=3)
            hdr = "JAWABAN TARUHAN"
            hw = od.textlength(hdr, font=FONT_Q)
            od.text(((W - hw) / 2, 114), hdr, font=FONT_Q, fill=(255, 220, 120, alpha))
            l1 = "> DESA ANAK MUDA — BENAR DI DUNIA INI"
            l2 = "> DESA ORANG TUA — MEMIMPIN DI TAHUN 2"
            od.text((220, 174), l1, font=FONT_SUB, fill=(255, 220, 120, alpha))
            od.text((220, 222), l2, font=FONT_SUB, fill=(140, 230, 140, alpha))
            full = Image.alpha_composite(full.convert("RGBA"), ov).convert("RGB")
        else:
            qs = [(715.96, "Pemimpin yang lebih baik itu yang mana?"),
                  (717.16, "Yang pengalamannya 30 tahun,"),
                  (721.16, "atau yang visinya 10 tahun ke depan?"),
                  (725.16, "Kalau kamu jadi warga Tanjungsari,"),
                  (729.16, "di tahun ke berapa kamu pindah?"),
                  (733.16, "Tulis jawabanmu di komentar."),
                  (737.16, "SUBSCRIBE untuk simulasi seperti ini!")]
            yy = 36
            for (qt, qtxt) in qs:
                if t_abs >= qt:
                    big = qt >= 737.16
                    font = FONT_BIG if big else FONT_Q
                    col = (255, 220, 120) if big else (255, 255, 255)
                    tw = fd.textlength(qtxt, font=font)
                    text_outline(fd, ((W - tw) / 2, yy), qtxt, font, col)
                    yy += 56 if big else 46
        enc.stdin.write(full.tobytes())

# ---------------- driver ----------------
RENDERERS = {"map": render_map, "dialog": render_dialog, "grid": render_grid,
             "split": render_split, "counter": render_counter, "closing": render_closing}

def render_segment(seg):
    out = os.path.join(SEGDIR, seg["name"] + ".mp4")
    nframes = int(round((seg["t1"] - seg["t0"]) * FPS))
    print(f"{seg['name']}: {seg['t0']:.2f}-{seg['t1']:.2f} ({nframes} frame, {seg['kind']})", flush=True)
    enc = open_encoder(out)
    try:
        RENDERERS[seg["kind"]](seg, enc, nframes)
    finally:
        enc.stdin.close()
        enc.wait()
    print(f"selesai {out}", flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--segment", default="")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.list:
        for s in SEGMENTS:
            print(s["name"], s["t0"], s["t1"], s["kind"])
        return
    if args.segment:
        seg = next(s for s in SEGMENTS if s["name"] == args.segment)
        render_segment(seg)
        return
    if args.all:
        for seg in SEGMENTS:
            out = os.path.join(SEGDIR, seg["name"] + ".mp4")
            if os.path.exists(out) and os.path.getsize(out) > 10000:
                print(f"skip {seg['name']} (sudah ada)")
                continue
            render_segment(seg)

if __name__ == "__main__":
    main()
