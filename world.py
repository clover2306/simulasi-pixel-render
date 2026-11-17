#!/usr/bin/env python3
"""Mesin dunia 32-bit gaya game untuk render penuh simulasi Kevin vs Mulyadi.
Dipakai render_full.py. Grid 640x360 -> 1280x720 NEAREST, streaming ke ffmpeg.
Perbaikan dari demo: warga menghindari bangunan (obstacle), status dunia
(pompa/pasar/migrasi) diturunkan dari tahun awal segmen supaya kontinu."""
import math, os, random, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assets import (kevin_frames, mulyadi_frames, sari_frames, ujang_frames,
                    villager_frames, HOUSE_THATCH, HOUSE_TILE, HOUSE_ABAND,
                    TREE, PUMP, MILL, STALL_RED, STALL_BLUE, make_tree)

GW, GH, SCALE = 640, 360, 2
W, H = GW * SCALE, GH * SCALE
GRASS = (96, 168, 76); GRASS_D = (82, 150, 62); GRASS_L = (112, 184, 92)
FIELD = (110, 178, 82); FIELD_BRIGHT = (142, 206, 92); FIELD_DRY = (188, 160, 100)
RIVER = (56, 138, 220); RIVER_L = (126, 192, 242); RIVER_D = (44, 116, 200)
BANK = (222, 196, 138); PATH = (214, 186, 130)

CHECK = {0: (20, 20), 2: (28, 34), 4: (46, 40), 6: (60, 44),
         10: (74, 38), 14: (80, 46), 20: (88, 56)}
def score_at(y):
    ks = sorted(CHECK)
    for i in range(len(ks) - 1):
        a, b = ks[i], ks[i + 1]
        if a <= y <= b:
            t = (y - a) / (b - a)
            sa, ta = CHECK[a]; sb, tb = CHECK[b]
            return (round(sa + (sb - sa) * t), round(ta + (tb - ta) * t))
    return CHECK[20]

def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)

def soft_shadowed(sprite, blur=2):
    w, h = sprite.size
    out = Image.new("RGBA", (w + 6, h + 4), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w + 6, h + 4), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.ellipse([3, h - 4, w + 2, h + 2], fill=(0, 0, 0, 100))
    out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(blur)))
    out.alpha_composite(sprite, (3, 0))
    return out

HOUSE_THATCH_S = soft_shadowed(HOUSE_THATCH)
HOUSE_TILE_S = soft_shadowed(HOUSE_TILE)
HOUSE_ABAND_S = soft_shadowed(HOUSE_ABAND)
TREE_S = soft_shadowed(TREE)
TREE_FRUIT_S = soft_shadowed(make_tree(fruit=True))
MILL_S = soft_shadowed(MILL)
STALL_RED_S = soft_shadowed(STALL_RED)
STALL_BLUE_S = soft_shadowed(STALL_BLUE)
PUMP_S = soft_shadowed(PUMP)

HOUSES_L = [(60, 120), (170, 120), (90, 270), (200, 270)]
HOUSES_R = [(390, 120), (500, 120), (420, 270), (530, 270)]
EXTRA_L = [(230, 130), (30, 140)]
TREES = [(20, 20), (260, 30), (20, 300), (270, 300), (120, 140)]
PUMPS_L = [(125, 105), (235, 215)]
STALLS_L = [(100, 165), (180, 165)]
PLOTS_L = [(30, 60, 90, 55), (140, 50, 90, 55), (40, 200, 90, 55), (150, 230, 90, 55)]
PLOTS_R = [(410, 60, 90, 55), (520, 50, 90, 55), (400, 200, 90, 55), (510, 230, 90, 55)]

# obstacle: rumah/penggilingan/warung/pompa (warga tidak boleh masuk)
OBSTACLES = []
for (hx, hy) in HOUSES_L + HOUSES_R + EXTRA_L:
    OBSTACLES.append((hx - 4, hy - 4, hx + 40, hy + 34))
OBSTACLES.append((246, 236, 292, 274))   # penggilingan
for (sx, sy) in STALLS_L:
    OBSTACLES.append((sx - 4, sy - 4, sx + 36, sy + 28))
OBSTACLES += [(266, 161, 306, 193), (346, 161, 386, 193)]  # warung pasar bersama
for (px_, py_) in PUMPS_L:
    OBSTACLES.append((px_ - 2, py_ - 2, px_ + 22, py_ + 22))
OBSTACLES.append((493, 183, 515, 205))  # pompa rahasia
OBSTACLES.append((236, 286, 262, 310))  # tumpukan jerami kiri
OBSTACLES.append((596, 296, 622, 320))  # tumpukan jerami kanan
OBSTACLES.append((281, 284, 311, 305))  # gerobak dekat penggilingan

def inside_obstacle(x, y):
    return any(x0 <= x <= x1 and y0 <= y <= y1 for (x0, y0, x1, y1) in OBSTACLES)

def river_cx(y):
    return 320 + int(6 * math.sin(y / 40.0))

class World:
    def __init__(self, seed=23, start_year=1):
        self.rng = random.Random(seed)
        rng = self.rng
        # terrain: rumput dasar + bercak tanah + jalan + plaza + tanaman
        base = Image.new("RGB", (GW, GH))
        px = base.load()
        for y in range(GH):
            for x in range(GW):
                r = rng.random()
                px[x, y] = GRASS if r > 0.3 else (GRASS_D if r > 0.15 else GRASS_L)
        bd = ImageDraw.Draw(base)
        for _ in range(40):
            x, y = rng.randint(10, 620), rng.randint(10, 340)
            bd.ellipse([x, y, x + rng.randint(14, 34), y + rng.randint(8, 18)],
                       fill=GRASS_D if rng.random() > 0.5 else GRASS_L)
        # bercak tanah kering
        for _ in range(20):
            x, y = rng.randint(10, 600), rng.randint(10, 330)
            bd.ellipse([x, y, x + rng.randint(14, 30), y + rng.randint(8, 16)],
                       fill=(150, 142, 96))
            bd.ellipse([x + 3, y + 2, x + rng.randint(10, 22), y + rng.randint(6, 12)],
                       fill=(168, 158, 110))
        # plaza tanah di depan warung (kiri-kanan jalan)
        for (ex0, ex1) in [(60, 240), (400, 580)]:
            bd.ellipse([ex0, 148, ex1, 196], fill=(178, 160, 116))
            bd.ellipse([ex0 + 8, 154, ex1 - 8, 190], fill=(188, 170, 126))
        # jalan utama + cabang ke rumah (dipanggang supaya tidak berkedip)
        for x in range(20, 620):
            if 305 <= x <= 335:
                continue  # jembatan menutup bagian sungai
            bd.point((x, 159), fill=PATH); bd.point((x, 160), fill=PATH); bd.point((x, 161), fill=PATH)
            if x % 3 == 0:
                bd.point((x, 158), fill=(196, 168, 112))
                bd.point((x, 162), fill=(196, 168, 112))
            if rng.random() > 0.85:
                bd.point((x, 160), fill=(180, 152, 100))
        for (hx, hy) in HOUSES_L + HOUSES_R + EXTRA_L:
            cx = hx + 17
            y0, y1 = min(160, hy + 30), max(160, hy + 30)
            for y in range(y0, y1 + 1):
                bd.point((cx, y), fill=PATH); bd.point((cx + 1, y), fill=PATH)
        for y in range(160, 241):
            bd.point((267, y), fill=PATH); bd.point((268, y), fill=PATH)
        self.flowers = []
        for _ in range(110):
            x, y = rng.randint(8, 632), rng.randint(8, 352)
            bd.point((x, y), fill=rng.choice([(240, 120, 160), (250, 240, 120), (240, 240, 240)]))
            self.flowers.append((x, y))
        for _ in range(600):
            x, y = rng.randint(8, 632), rng.randint(8, 352)
            bd.point((x, y), fill=(70, 134, 54))
        for _ in range(50):
            x, y = rng.randint(8, 632), rng.randint(8, 352)
            bd.ellipse([x, y, x + 3, y + 2], fill=(170, 164, 150))
        # rumpun rumput + rumpun bunga + semak + batu + jamur (hindari sungai & sawah)
        plot_rects = PLOTS_L + PLOTS_R
        def clear_spot(x, y):
            if 300 <= x <= 340:
                return False
            return not any(px0 - 2 <= x <= px0 + pw + 2 and py0 - 2 <= y <= py0 + ph + 2
                           for (px0, py0, pw, ph) in plot_rects)
        for _ in range(250):
            x, y = rng.randint(8, 632), rng.randint(8, 352)
            if not clear_spot(x, y):
                continue
            col = (70, 134, 54) if rng.random() > 0.5 else (126, 196, 104)
            bd.line([(x, y), (x, y - 3)], fill=col)
            bd.line([(x - 2, y), (x - 3, y - 2)], fill=col)
            bd.line([(x + 2, y), (x + 3, y - 2)], fill=col)
        for _ in range(40):
            x, y = rng.randint(8, 624), rng.randint(8, 344)
            if not clear_spot(x, y):
                continue
            col = rng.choice([(240, 120, 160), (250, 240, 120), (240, 240, 240), (200, 140, 240)])
            for (dx, dy) in [(0, 0), (3, 1), (1, 3), (4, 3), (2, -2)]:
                bd.point((x + dx, y + dy), fill=col)
            bd.point((x + 2, y + 1), fill=(250, 220, 60))
        for (bx, by) in [(15, 175), (290, 315), (250, 165), (355, 315), (605, 175), (370, 60),
                         (40, 330), (600, 330)]:
            bd.ellipse([bx, by, bx + 12, by + 8], fill=(62, 118, 48))
            bd.ellipse([bx + 2, by, bx + 9, by + 4], fill=(86, 148, 66))
        for _ in range(30):
            x, y = rng.randint(8, 628), rng.randint(8, 348)
            if not clear_spot(x, y):
                continue
            bd.ellipse([x, y, x + 3, y + 2], fill=(150, 148, 142))
            bd.point((x + 1, y), fill=(190, 188, 182))
        for _ in range(8):
            x, y = rng.randint(8, 628), rng.randint(8, 348)
            if not clear_spot(x, y):
                continue
            bd.rectangle([x + 1, y, x + 2, y + 2], fill=(240, 230, 210))
            bd.ellipse([x, y - 2, x + 3, y + 1], fill=(220, 70, 60))
            bd.point((x + 1, y - 1), fill=(255, 255, 255))
        # bayangan awan (sprite blur, digeser per frame)
        self.cloud_blobs = []
        for (bw_, bh_) in [(130, 52), (100, 42), (150, 58)]:
            blob = Image.new("RGBA", (bw_, bh_), (0, 0, 0, 0))
            bdd = ImageDraw.Draw(blob)
            bdd.ellipse([0, 0, bw_, bh_], fill=(20, 30, 20, 30))
            self.cloud_blobs.append(blob.filter(ImageFilter.GaussianBlur(10)))
        self.base_normal = base.copy()
        self._bake_river(self.base_normal, drought=False)
        self.base_drought = base.copy()
        self._bake_river(self.base_drought, drought=True)
        self.crop_dots = []
        for (x, y, w, h) in PLOTS_L + PLOTS_R:
            for yy in range(y + 5, y + h, 7):
                for xx in range(x + 4, x + w, 7):
                    self.crop_dots.append((xx, yy))
        # orang
        VILS = [villager_frames((30, 24, 20), (220, 60, 50)),
                villager_frames((96, 60, 32), (60, 120, 220)),
                villager_frames((180, 180, 180), (240, 200, 60)),
                villager_frames((150, 60, 40), (90, 190, 90))]
        self.people = []
        for i in range(8):
            self.people.append(Person(self, VILS[i % 4], rng.randint(30, 290),
                                      rng.randint(40, 330), 25, 295))
        self.migrants = []
        for i in range(8):
            x0, x1 = (340, 450) if i % 2 == 0 else (515, 615)
            p = Person(self, VILS[(i + 1) % 4], rng.randint(x0, x1),
                       rng.randint(40, 330), x0, x1)
            self.people.append(p)
            if i < 4:
                self.migrants.append(p)
        self.kevin = Person(self, kevin_frames(), 150, 150, 60, 280, 100, 260)
        self.mulyadi = Person(self, mulyadi_frames(), 470, 150, 430, 520, 110, 200)
        self.sari = Person(self, sari_frames(), 500, 160, 400, 580, 100, 260)
        self.ujang = Person(self, ujang_frames(), 470, 200, 400, 580, 100, 280)
        # status awal dari tahun segmen
        self.ujang_crossed = start_year >= 6
        self.migrants_crossed = start_year >= 11
        if self.ujang_crossed:
            self.ujang.x, self.ujang.y = 200, 200
            self.ujang.x0, self.ujang.x1 = 60, 300
        if self.migrants_crossed:
            for j, m in enumerate(self.migrants):
                m.x, m.y = 240 - j * 15, 200 + j * 10
                m.x0, m.x1 = 25, 295
        self.butterflies = [{"x": fx, "y": fy, "tx": fx, "ty": fy,
                             "c": rng.choice([(240, 130, 200), (250, 220, 90), (150, 200, 250)])}
                            for fx, fy in rng.sample(self.flowers, 6)]
        self.leaves = [(rng.randint(30, 300), rng.randint(20, 200), rng.randint(0, 60))
                       for _ in range(8)]
        self.dust = [(rng.randint(340, 620), rng.randint(60, 320), rng.randint(0, 60))
                     for _ in range(10)]
        self.prev_year = start_year

    def _bake_river(self, img, drought):
        pxb = img.load()
        half = 4 if drought else 7
        for y in range(GH):
            cx = river_cx(y)
            for dx in range(-half - 2, half + 3):
                if abs(dx) >= half:
                    pxb[cx + dx, y] = BANK
                else:
                    pxb[cx + dx, y] = RIVER_D if abs(dx) >= half - 2 else RIVER
        d = ImageDraw.Draw(img)
        # alang-alang + eceng di tepian (posisi tetap, di kedua varian)
        for ry in (30, 70, 120, 210, 260, 310):
            cx = river_cx(ry)
            for side in (-1, 1):
                bx = cx + side * 10
                d.line([(bx, ry), (bx, ry - 7)], fill=(74, 140, 62))
                d.line([(bx + 2, ry), (bx + 2, ry - 5)], fill=(94, 160, 78))
                d.rectangle([bx - 1, ry - 9, bx + 1, ry - 6], fill=(120, 82, 44))
        # daun teratai di atas air
        for ly in (50, 140, 230, 300):
            cx = river_cx(ly)
            d.ellipse([cx - 3, ly, cx + 3, ly + 2], fill=(62, 150, 70))
            d.point((cx + 1, ly), fill=(90, 180, 96))
        # batu pijakan dekat jembatan
        for (sx, sy) in [(-5, 150), (0, 156), (5, 162)]:
            cx = river_cx(sy)
            d.ellipse([cx + sx - 2, sy, cx + sx + 2, sy + 2], fill=(170, 164, 150))

    def draw_plots(self, d, year, f):
        bright = year >= 4
        drought = year in (9, 10)
        for (x, y, w, h) in PLOTS_L:
            d.rectangle([x, y, x + w, y + h], fill=FIELD_BRIGHT if bright else FIELD)
            d.rectangle([x, y, x + w, y + h], outline=shade(FIELD, 0.8))
        for (x, y, w, h) in PLOTS_R:
            col = FIELD_DRY if drought else FIELD
            d.rectangle([x, y, x + w, y + h], fill=col)
            d.rectangle([x, y, x + w, y + h], outline=shade(col, 0.8))
            if drought:
                for _ in range(6):
                    cx, cy = x + self.rng.randint(6, w - 10), y + self.rng.randint(6, h - 8)
                    d.line([(cx, cy), (cx + 5, cy + 2), (cx + 3, cy + 6)], fill=(150, 122, 78))
        # alur baris tanam + pagar kayu sekeliling petak
        for (x, y, w, h) in PLOTS_L + PLOTS_R:
            for yy in range(y + 7, y + h, 7):
                d.line([(x + 2, yy), (x + w - 2, yy)], fill=shade(FIELD, 0.88))
            for fx in range(x, x + w + 1, 14):
                d.rectangle([fx, y - 3, fx + 1, y], fill=(120, 86, 50))
                d.rectangle([fx, y + h, fx + 1, y + h + 3], fill=(120, 86, 50))
            for fy in range(y, y + h + 1, 14):
                d.rectangle([x - 3, fy, x, fy + 1], fill=(120, 86, 50))
                d.rectangle([x + w, fy, x + w + 3, fy + 1], fill=(120, 86, 50))
            d.line([(x, y - 2), (x + w, y - 2)], fill=(140, 100, 60))
            d.line([(x, y + h + 2), (x + w, y + h + 2)], fill=(140, 100, 60))
        for i, (xx, yy) in enumerate(self.crop_dots):
            right = xx > 320
            if drought and right:
                continue
            sway = int(1.2 * math.sin((f + i * 3) / 10.0))
            col = shade(FIELD_BRIGHT if (bright and not right) else FIELD, 1.18)
            d.point((xx + sway, yy), fill=col)

    def draw_river_fx(self, d, year, f):
        half = 4 if year in (9, 10) else 7
        for k in range(24):
            yy = (f * 2 + k * 47) % GH
            cx = river_cx(yy)
            d.line([(cx - 2, yy), (cx - 2, yy + 6)], fill=RIVER_L)
            d.point((cx + 3, yy + 3), fill=RIVER_L)
        for k in range(14):
            yy = (k * 53 + f) % GH
            cx = river_cx(yy)
            d.point((cx - half - 1, yy), fill=(240, 248, 255))
            d.point((cx + half + 1, (yy + 27) % GH), fill=(240, 248, 255))

    def draw_bridge(self, d, year):
        for bx in range(306, 336, 6):
            d.rectangle([bx, 178, bx + 5, 190], fill=(140, 96, 54))
            d.rectangle([bx, 178, bx + 5, 180], fill=(170, 122, 70))
        if year >= 16:
            d.rectangle([306, 176, 335, 178], fill=(120, 82, 44))
            d.rectangle([306, 190, 335, 192], fill=(120, 82, 44))

    def step_only(self, f, year_float):
        """Majukan status simulasi satu frame tanpa menggambar piksel (untuk mode full-screen)."""
        if year_float >= 5.45 and not self.ujang_crossed:
            self.ujang.path = [(470, 200), (420, 184), (370, 184), (330, 184),
                               (300, 184), (270, 190), (250, 200)]
            self.ujang.x0, self.ujang.x1 = 60, 300
            self.ujang_crossed = True
        if year_float >= 10.4 and not self.migrants_crossed:
            for j, m in enumerate(self.migrants):
                m.path = [(m.x, m.y), (420, 184), (330, 184), (260, 184),
                          (240 - j * 15, 200 + j * 10)]
                m.x0, m.x1 = 25, 295
            self.migrants_crossed = True
        for p in self.people + [self.kevin, self.mulyadi, self.sari, self.ujang]:
            p.step()

    def render_grid(self, f, year_float, counterfactual=False):
        """Majukan simulasi dan gambar satu frame peta 640x360 (level grid, sebelum kamera)."""
        year = max(1, min(20, int(round(year_float))))
        drought = year in (9, 10) and not counterfactual
        img = (self.base_drought if drought else self.base_normal).copy()
        d = ImageDraw.Draw(img)
        # peristiwa: penyeberangan dipicu saat tahun berjalan melewati ambang
        if year_float >= 5.45 and not self.ujang_crossed:
            self.ujang.path = [(470, 200), (420, 184), (370, 184), (330, 184),
                               (300, 184), (270, 190), (250, 200)]
            self.ujang.x0, self.ujang.x1 = 60, 300
            self.ujang_crossed = True
        if year_float >= 10.4 and not self.migrants_crossed:
            for j, m in enumerate(self.migrants):
                m.path = [(m.x, m.y), (420, 184), (330, 184), (260, 184),
                          (240 - j * 15, 200 + j * 10)]
                m.x0, m.x1 = 25, 295
            self.migrants_crossed = True
        self.draw_plots(d, year if not counterfactual else 20, f)
        if counterfactual:
            for (x, y, w, h) in PLOTS_R:
                d.rectangle([x, y, x + w, y + h], fill=FIELD_BRIGHT)
                d.rectangle([x, y, x + w, y + h], outline=shade(FIELD, 0.8))
        self.draw_river_fx(d, year, f)
        # saluran irigasi dari sungai ke sawah kiri (pompa bekerja)
        for (cy, cx1) in [(88, 232), (228, 242)]:
            cx0 = river_cx(cy) - 8
            d.line([(cx0, cy), (cx1, cy)], fill=RIVER_L)
            d.line([(cx0, cy + 1), (cx1, cy + 1)], fill=RIVER)
        self.draw_bridge(d, year)
        # pohon (satu pohon buah per sisi)
        for (x, y) in TREES:
            spr = TREE_FRUIT_S if (x, y) == (260, 30) else TREE_S
            img.paste(spr, (x - 3, y), spr)
            spr2 = TREE_FRUIT_S if (x, y) == (260, 30) else TREE_S
            img.paste(spr2, (620 - x - 20 - 3, y), spr2)
        chimneys = []
        for (hx, hy) in HOUSES_L:
            spr = HOUSE_TILE_S if year >= 5 else HOUSE_THATCH_S
            img.paste(spr, (hx - 3, hy), spr)
            chimneys.append((hx + 25, hy + 2))
        for i, (hx, hy) in enumerate(HOUSES_R):
            abandoned = year >= 12 and i in (1, 3) and not counterfactual
            spr = HOUSE_ABAND_S if abandoned else HOUSE_THATCH_S
            img.paste(spr, (hx - 3, hy), spr)
            if not abandoned:
                chimneys.append((hx + 25, hy + 2))
        if year >= 5:
            img.paste(HOUSE_TILE_S, (230 - 3, 130), HOUSE_TILE_S)
            img.paste(HOUSE_TILE_S, (30 - 3, 140), HOUSE_TILE_S)
            chimneys += [(255, 132), (55, 142)]
        for (chx, chy) in chimneys:
            for k in range(3):
                ph = (f // 2 + k * 12) % 36
                d.ellipse([chx + k - 1, chy - ph - 1, chx + k + 2, chy - ph + 2],
                          fill=(210, 210, 210))
        for (px_, py_) in PUMPS_L:
            img.paste(PUMP_S, (px_ - 3, py_), PUMP_S)
            d.rectangle([px_ + 8, py_ + 4 - (f // 6) % 2, px_ + 10, py_ + 8], fill=(90, 90, 96))
        if year >= 13 or counterfactual:
            img.paste(PUMP_S, (495 - 3, 185), PUMP_S)
        if year >= 5:
            img.paste(MILL_S, (250 - 3, 240), MILL_S)
        if year >= 6:
            for (sx, sy) in STALLS_L:
                spr = STALL_RED_S if sx < 150 else STALL_BLUE_S
                img.paste(spr, (sx - 3, sy), spr)
        if year >= 16:
            img.paste(STALL_RED_S, (270 - 3, 165), STALL_RED_S)
            img.paste(STALL_BLUE_S, (350 - 3, 165), STALL_BLUE_S)
        # tumpukan jerami + gerobak + lentera jalan + orang-orangan sawah
        for (hx, hy) in [(249, 308), (609, 318)]:
            d.polygon([(hx - 12, hy), (hx, hy - 18), (hx + 12, hy)], fill=(222, 188, 92))
            d.line([(hx - 6, hy - 8), (hx + 6, hy - 8)], fill=(196, 162, 72))
            d.line([(hx - 3, hy - 13), (hx + 3, hy - 13)], fill=(196, 162, 72))
        d.rectangle([285, 290, 307, 298], fill=(140, 96, 54))
        d.rectangle([285, 290, 307, 292], fill=(170, 122, 70))
        d.ellipse([288, 297, 294, 303], fill=(90, 70, 50))
        d.ellipse([299, 297, 305, 303], fill=(90, 70, 50))
        d.line([(307, 292), (313, 288)], fill=(120, 86, 50))
        for (lx, ly) in [(140, 150), (240, 150), (400, 150), (500, 150)]:
            d.line([(lx, ly), (lx, ly - 12)], fill=(90, 70, 50))
            d.rectangle([lx - 2, ly - 16, lx + 2, ly - 11], fill=(250, 220, 120))
            d.point((lx, ly - 13), fill=(255, 240, 180))
        for (sx, sy) in [(75, 88), (455, 88)]:
            d.line([(sx, sy), (sx, sy - 14)], fill=(120, 86, 50))
            d.line([(sx - 6, sy - 10), (sx + 6, sy - 10)], fill=(120, 86, 50))
            d.ellipse([sx - 3, sy - 18, sx + 3, sy - 12], fill=(222, 188, 92))
            d.rectangle([sx - 5, sy - 16, sx + 5, sy - 14], fill=(240, 210, 120))
        for (fx, fy) in [(60, 120), (390, 120)]:
            d.line([(fx + 17, fy - 8), (fx + 17, fy + 4)], fill=(90, 70, 50))
            wave = int(2 * math.sin(f / 5.0))
            d.polygon([(fx + 17, fy - 8), (fx + 27, fy - 6 + wave), (fx + 17, fy - 4)],
                      fill=(220, 60, 50))
        for i, (lx, ly, off) in enumerate(self.leaves):
            dy = (f + off) % 60
            d.point((lx + int(4 * math.sin((f + off) / 9.0)), ly + dy), fill=(120, 170, 70))
        for b in self.butterflies:
            if abs(b["x"] - b["tx"]) < 2 and abs(b["y"] - b["ty"]) < 2:
                b["tx"] = max(10, min(630, b["x"] + self.rng.randint(-30, 30)))
                b["ty"] = max(10, min(350, b["y"] + self.rng.randint(-30, 30)))
            b["x"] += (1 if b["tx"] > b["x"] else -1 if b["tx"] < b["x"] else 0)
            b["y"] += (1 if b["ty"] > b["y"] else -1 if b["ty"] < b["y"] else 0)
            w = 2 if (f // 3) % 2 == 0 else 1
            d.point((b["x"] - w, b["y"]), fill=b["c"])
            d.point((b["x"] + w, b["y"]), fill=b["c"])
        for i, by in enumerate((30, 55, 80)):
            bx = (f * 2 + i * 220) % (GW + 60) - 30
            flap = 2 if (f // 4 + i) % 2 == 0 else 0
            d.line([(bx - 4, by - flap), (bx, by), (bx + 4, by - flap)], fill=(40, 36, 32))
        if drought:
            for (dx, dy, off) in self.dust:
                d.point((dx + int(8 * math.sin((f + off) / 14.0)), dy), fill=(222, 196, 150))
        for p in self.people + [self.kevin, self.mulyadi, self.sari, self.ujang]:
            p.step()
            frame_idx = (f // 6 + p.phase) % 4
            bob = 1 if frame_idx in (1, 3) else 0
            spr = p.sprites[frame_idx]
            img.paste(spr, (p.x - 8, p.y - 24 - bob), spr)
        if drought:
            haze = Image.new("RGB", (GW, GH), (232, 200, 140))
            img = Image.blend(img, haze, 0.12)
            d = ImageDraw.Draw(img)
        # bayangan awan bergerak perlahan di atas peta
        for i, blob in enumerate(self.cloud_blobs):
            bw_, bh_ = blob.size
            bx = int((f * (0.5 + i * 0.2) + i * 260) % (GW + bw_ * 2) - bw_)
            by = 50 + i * 110
            img.paste(blob, (bx, by), blob)
        # capung di sekitar sungai
        for i, (ccx, ccy) in enumerate([(300, 100), (345, 260)]):
            dx = ccx + int(18 * math.sin((f + i * 40) / 16.0))
            dy = ccy + int(10 * math.cos((f + i * 40) / 12.0))
            d.point((dx, dy), fill=(40, 180, 180))
            d.point((dx + 1, dy), fill=(40, 160, 160))
            w = 2 if (f // 2) % 2 == 0 else 1
            d.point((dx - w, dy - 1), fill=(220, 240, 240))
            d.point((dx + 1 + w, dy - 1), fill=(220, 240, 240))
        # ikan melompat sesekali
        cyc = f % 200
        if cyc < 14:
            fy = 100 + ((f // 200) * 37 % 180)
            fx = river_cx(fy)
            arc = int(6 * math.sin(cyc / 14 * math.pi))
            d.point((fx, fy - arc), fill=(200, 210, 220))
            d.point((fx + 1, fy - arc), fill=(180, 190, 200))
            if cyc < 3 or cyc > 11:
                d.point((fx - 2, fy), fill=(240, 248, 255))
                d.point((fx + 2, fy), fill=(240, 248, 255))
        # kilau air
        for i, sy in enumerate((40, 90, 170, 220, 290, 330)):
            if math.sin(f / 6.0 + i * 1.7) > 0.6:
                d.point((river_cx(sy) + (i % 3) - 1, sy), fill=(255, 255, 255))
        return img

    def apply_camera(self, grid_img, cx=320.0, cy=180.0, zoom=1.0):
        """Crop grid_img sesuai (cx, cy, zoom) lalu upscale NEAREST ke 1280x720.
        Mengembalikan (full_1280x720, (x0, y0, cw, ch))."""
        z = max(1.0, min(2.5, float(zoom)))
        cw = max(int(round(GW / 2.5)), min(GW, int(round(GW / z))))
        ch = max(int(round(GH / 2.5)), min(GH, int(round(cw * GH / GW))))
        x0 = max(0, min(GW - cw, int(round(cx - cw / 2.0))))
        y0 = max(0, min(GH - ch, int(round(cy - ch / 2.0))))
        full = grid_img.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.NEAREST)
        return full, (x0, y0, cw, ch)

    def draw(self, f, year_float, zoom=0.0, counterfactual=False):
        """Satu frame peta 1280x720 (kompatibel v1; tanpa HUD)."""
        img = self.render_grid(f, year_float, counterfactual=counterfactual)
        # kamera: zoom pelan sesuai progres absolut
        zw = GW - int(20 * zoom)
        zh = GH - int(11 * zoom)
        cx0, cy0 = (GW - zw) // 2, (GH - zh) // 2
        full = img.crop((cx0, cy0, cx0 + zw, cy0 + zh)).resize((W, H), Image.NEAREST)
        return full

class Person:
    def __init__(self, world, sprites, x, y, x0, x1, y0=40, y1=330):
        self.world = world
        self.sprites = sprites; self.x, self.y = x, y
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.tx, self.ty = x, y; self.phase = world.rng.randint(0, 3)
        self.path = None; self.path_i = 0
    def _pick_target(self):
        rng = self.world.rng
        for _ in range(12):
            tx, ty = rng.randint(self.x0, self.x1), rng.randint(self.y0, self.y1)
            if not inside_obstacle(tx, ty):
                self.tx, self.ty = tx, ty
                return
        self.tx, self.ty = self.x, self.y
    def step(self):
        if self.path is not None:
            if self.path_i < len(self.path):
                self.tx, self.ty = self.path[self.path_i]
            else:
                self.path = None
        if abs(self.x - self.tx) < 2 and abs(self.y - self.ty) < 2:
            if self.path is not None:
                self.path_i += 1
                if self.path_i < len(self.path):
                    self.tx, self.ty = self.path[self.path_i]
                else:
                    self.path = None
            if self.path is None:
                self._pick_target()
        nx = self.x + (1 if self.tx > self.x else -1 if self.tx < self.x else 0)
        ny = self.y + (1 if self.ty > self.y else -1 if self.ty < self.y else 0)
        if self.path is None and inside_obstacle(nx, ny):
            self._pick_target()
            return
        self.x, self.y = nx, ny

# ---------- util tampilan (dipakai render_full.py) ----------
PIXEL_FONT = os.path.expanduser("~/workspace/fonts/PressStart2P-Regular.ttf")

def load_font(size):
    if os.path.exists(PIXEL_FONT):
        return ImageFont.truetype(PIXEL_FONT, size)
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def text_outline(d, xy, s, font, fill, outline=(0, 0, 0), w=2):
    x, y = xy
    for dx in range(-w, w + 1):
        for dy in range(-w, w + 1):
            if dx or dy:
                d.text((x + dx, y + dy), s, font=font, fill=outline)
    d.text((x, y), s, font=font, fill=fill)

def make_vignette():
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([-90, -70, W + 90, H + 70], fill=255)
    return mask.filter(ImageFilter.GaussianBlur(70))

VIGNETTE = make_vignette()
WARM = Image.new("RGB", (W, H), (255, 240, 210))

def grade(full):
    full = Image.blend(full, WARM, 0.05)
    dark = ImageEnhance.Brightness(full).enhance(0.4)
    return Image.composite(full, dark, VIGNETTE)

def draw_hud(fd, year_disp, sl, sr, font_hud, font_lbl, show_side_labels=True):
    fd.rectangle([0, 0, W, 40], fill=(20, 18, 16))
    text_outline(fd, (24, 7), f"SINARBARU  {sl}", font_hud, (255, 220, 120))
    text_outline(fd, (W - 300, 7), f"TANJUNGSARI  {sr}", font_hud, (140, 230, 140))
    t = f"TAHUN {year_disp}"
    tw = fd.textlength(t, font=font_hud)
    fd.rectangle([0, 44, W, 46], fill=(0, 0, 0))
    fd.rectangle([24, 44, 24 + sl * 3, 50], fill=(255, 220, 120))
    fd.rectangle([24, 44, 24 + sl * 3, 46], fill=(255, 240, 180))
    fd.rectangle([W - 24 - sr * 3, 44, W - 24, 50], fill=(140, 230, 140))
    fd.rectangle([W - 24 - sr * 3, 44, W - 24, 46], fill=(200, 250, 200))
    text_outline(fd, ((W - tw) / 2, 7), t, font_hud, (255, 255, 255))
    if show_side_labels:
        text_outline(fd, (60, 90), "SINARBARU", font_lbl, (255, 240, 200))
        text_outline(fd, (W - 280, 90), "TANJUNGSARI", font_lbl, (220, 255, 220))

def draw_banner(full, text, font_banner, alpha=255):
    fd = ImageDraw.Draw(full)
    bw = int(fd.textlength(text, font=font_banner)) + 48
    bx, by = (W - bw) // 2, 90
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rounded_rectangle([bx, by, bx + bw, by + 58], radius=14,
                         fill=(20, 18, 16, int(alpha * 0.9)))
    od.rounded_rectangle([bx, by, bx + bw, by + 58], radius=14,
                         outline=(255, 220, 120, alpha), width=3)
    od.text((bx + 24, by + 8), text, font=font_banner, fill=(255, 240, 200, alpha))
    return Image.alpha_composite(full.convert("RGBA"), ov).convert("RGB")
