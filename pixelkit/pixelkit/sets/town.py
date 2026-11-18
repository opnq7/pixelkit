"""pixelkit.sets.town - the weekend town block (side-view diorama, 900x270 native, ACT III part 2).

    tw = Town()                       # subclass of sets.street.Street: same sky / skyline / sidewalk / road / tree code
    tw.bg                             # dict for outdoor.OutdoorScene (front = list of canopy-sway variants)
    tw.A['benches']                   # [(x0, x1, seat_y)]  seat top row (people: put pose='sit' at seat - seat_y)
    tw.A['quilt_win']                 # (x, y, w, h) glass area of the 2nd-floor bedroom window (draw quilt_patch there)
    tw.A['tables']                    # [(x, foot)] cafe terrace tables (draw table_sprite in the mid layer, after the sitter)
    tw.A['column']                    # (x, foot) the porch column the best man hides behind -> column_sprite() in mid
    tw.quilt_patch(curtain, quilt, phone, sun)   # dynamic bedroom interior (rgba, E) for bg_patches
    tw.table_sprite(lid=1.0, glow=1.0)           # bistro table + laptop (lid 1 open .. 0 shut), (rgba, E, ox, oy)
    tw.column_sprite()                           # (rgba, X, Y)

Layout (native px, left -> right):
  0-330    pocket park 口袋公园: hazy background trees, trimmed hedge + iron railing, gravel path with a grass
           edge, two benches (A 116-182 for Claude, B 228-276 for the uncle), front trees at 64 / 300
  330-520  cafe 咖啡 CAFE: cream siding, flower boxes, green shopfront, bistro chairs on the terrace
  520-690  pastel apartment block: 3 floors, the bedroom window (quilt) on the 2nd floor, entrance + mailboxes
  690-900  wedding hall 幸福礼堂: white pediment facade, arched windows, flower arch over the door, balloons,
           porch columns, red carpet across the sidewalk
Ground rows as in street.py: facades end at GROUND 184, sidewalk 184..226, curb, road.  Lead walks at 200.
"""
import math
import numpy as np, cv2
from ..core import Canvas, C, mix, text_width, BAYER4
from .. import materials as M
from ..outdoor import haze_map
from .street import Street, R, dk, OUTL, GROUND, CURB, ROAD, WALK_Y, H

W = 900
GREENS = [C('#1b3434'), C('#24493d'), C('#356640'), C('#4f8640'), C('#7aa848'), C('#b4cc62'), C('#e6dc8c')]
BENCH_A, BENCH_B = (116, 182), (228, 276)
SEAT_Y = 189


def clusters(cx, cy, rx, ry, rng, n=20):
    cl = []
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi); rr = math.sqrt(rng.uniform(0, 1))
        px_ = cx + math.cos(a) * rr * rx * 0.85; py_ = cy + math.sin(a) * rr * ry * 0.75
        r = rng.uniform(11, 17) * (1.0 - 0.25 * rr) * (rx / 50.0) ** 0.5
        cl.append([px_, py_, r, rng.uniform(0, 2 * math.pi)])
    cl.sort(key=lambda c: c[1] + (c[0] - cx) * 0.25)
    return cl


class Town(Street):
    def __init__(self, seed=0, w=W, sway_frames=12):
        self.W, self.H, self.seed = w, H, seed
        self.cv = Canvas(w, H)
        self.E = np.zeros((H, w), np.float32)
        self.T = np.ones((H, w), np.float32)
        self.ao = np.ones((H, w), np.float32)
        self.front = Canvas(w, H)
        self.frontE = np.zeros((H, w), np.float32)
        self.A = {'trees': [], 'benches': [], 'tables': []}
        self.rng = np.random.default_rng(seed + 4321)
        self.front_base = Canvas(w, H)
        self.canopies = []
        self.sky(); self.skyline()
        self.park_back(0, 330)
        self.cafe(330, 520)
        self.flat(520, 690)
        self.wedding(690, w)
        self.sidewalk(); self.road()
        self.park_ground(0, 330)
        self.wedding_ground()
        self.cafe_terrace()
        self.town_props()
        for i, x in enumerate((64, 300)): self.tree(x, seed=201 + i)
        self.fronts = self.build_fronts(sway_frames)
        self.lighting()
        self.bg = dict(rgba=self.cv.a, E=self.E, T=self.T, ao=self.ao, ground=self.ground,
                       haze=haze_map(w, H, 2, sun_xy=(-90, -70), rays=12, ray_k=0.45, glow_k=0.55, glow_r=260.0,
                                     horizon=120, horizon_k=0.10),
                       front=self.fronts, frontE=self.frontE)

    # ================================================================== park
    def bg_tree(self, x, cy, rx, ry, seed, haze=0.22):
        """a big background tree (static canopy, hazier / cooler than the street trees) with its trunk to GROUND."""
        cv = self.cv; rng = np.random.default_rng(seed)
        bark = [C('#3a2c30'), C('#56403a'), C('#6e5446')]
        for yy in range(int(cy), GROUND):
            half = 3.0 + (GROUND - yy) / (GROUND - cy) * -0.6 + (1.5 if yy > GROUND - 6 else 0)
            for xx in range(int(x - half), int(x + half) + 1):
                s = (xx - (x - half)) / (2 * half + 1e-3)
                cv.px(xx, yy, bark[2] if s < 0.35 else (bark[1] if s < 0.8 else bark[0]))
        c = dict(x=x, foot=GROUND, cx=x, cy=cy, rx=rx, ry=ry, cl=clusters(x, cy, rx, ry, rng, 22), seed=seed)
        m, img = self.canopy_raster(c, None)
        hz = np.asarray(C('#b4b2d2')[:3], np.float32)
        col = img[..., :3].astype(np.float32) * (1 - haze) + hz * haze
        cv.a[m, :3] = col[m].astype(np.uint8); cv.a[m, 3] = 255
        self.E[m] = 0.0
        return m

    def park_back(self, x0, x1):
        cv = self.cv
        for (x, cy, rx, ry, sd) in ((22, 112, 52, 40, 311), (128, 98, 62, 46, 312), (232, 108, 58, 42, 313), (318, 120, 40, 32, 314)):
            self.bg_tree(x, cy, rx, ry, sd)
        # trimmed hedge 148..184 (irregular top, leaf clumps, lit from the upper left)
        yy, xx = np.mgrid[136:GROUND, x0:x1]
        u, v = xx.astype(float), yy.astype(float)
        top = 149 + 2.2 * np.sin(u / 23.0) + (M.fbm(u, np.zeros_like(u), 9.0, 2, 41) - 0.5) * 5
        m = v >= top
        n = M.fbm(u, v, 4.0, 3, 42)
        t = 4.6 - (v - top) / 36.0 * 2.6 + (n - 0.5) * 2.0 - (u - x0) / (x1 - x0) * 0.3
        t = np.where(v < top + 1.5, t + 0.8, t)
        img = M.apply_ramp(np.clip(t, 0, 6), GREENS, xx, yy, True, band=2.0)
        reg = cv.a[136:GROUND, x0:x1]
        reg[m] = img[m]
        edge = m & ~np.roll(m, 1, 0)
        reg[edge] = np.array(GREENS[5], np.uint8)
        reg[np.roll(edge, -1, 0) & ~m] = np.array(GREENS[1], np.uint8)
        self.E[136:GROUND, x0:x1][m] = 0.0
        # flowers along the hedge foot
        rng = np.random.default_rng(43)
        for _ in range(70):
            fx = int(rng.integers(x0 + 2, x1 - 2)); fy = int(rng.integers(176, 183))
            cv.px(fx, fy, C(['#ff8ab0', '#fff2c8', '#ffd04a', '#c88aff', '#ff6a6a'][int(rng.integers(0, 5))]))
        # iron railing 158..184 with spear tips, posts every 44 px
        IR, IR_H = C('#2c3834'), C('#5c6e66')
        for x in range(x0 + 2, x1, 4):
            cv.vline(x, 160, GROUND - 160, IR); cv.px(x, 159, IR_H); cv.px(x, 158, IR)
        for yr in (163, 180):
            cv.hline(x0, yr, x1 - x0, IR); cv.hline(x0, yr - 1, x1 - x0, IR_H)
        for x in range(x0 + 10, x1, 44):
            cv.rect(x - 1, 154, 4, GROUND - 154, OUTL); cv.rect(x, 155, 2, GROUND - 155, IR); cv.vline(x, 155, GROUND - 155, IR_H)
            cv.rect(x - 2, 152, 6, 3, IR); cv.hline(x - 2, 152, 6, IR_H)
        self.E[152:GROUND, x0:x1][np.all(cv.a[152:GROUND, x0:x1, :3] == np.array(IR[:3]), -1)] = 0.0
        # park sign 口袋公园 on two posts
        sx = 150
        for px_ in (sx + 4, sx + 52):
            cv.rect(px_ - 1, 140, 4, GROUND - 140, OUTL); cv.rect(px_, 140, 2, GROUND - 140, C('#6a4a34'))
        self.sign(sx, 128, '口袋公园 PARK', bg='#3a5a3a', fg='#fff3d6', border='#c8a060')
        # stone gate pier at the park end (towards the cafe)
        gx = x1 - 12
        cv.rect(gx - 1, 128, 14, GROUND - 128, OUTL)
        self.wall(gx, gx + 12, 129, '#c8bca8', 'brick', seed=44, weather=False, bw=6.0, bh=4.0)
        cv.rect(gx - 2, 125, 16, 4, C('#e0d6c4')); cv.hline(gx - 2, 125, 16, C('#f4ecdc')); cv.hline(gx - 2, 129, 16, OUTL)
        self.soft_shadow(gx + 12, 130, 5, GROUND - 130, 0.35, fade=3)
        self.ao[170:GROUND, x0:x1] *= np.linspace(1.0, 0.8, GROUND - 170)[:, None]

    def bench(self, x0, x1):
        """park bench seen from the front: iron ends, 3 back slats, seat surface 186..188, seat edge 189..191."""
        cv = self.cv
        WD = R('#b07a4a', 5); IR = C('#2c3a34'); IRH = C('#5a6e64')
        for y0 in (169, 174, 179):                                          # back slats
            cv.rect(x0 - 1, y0 - 1, x1 - x0 + 2, 5, OUTL)
            cv.rect(x0, y0, x1 - x0, 3, WD[2]); cv.hline(x0, y0, x1 - x0, WD[4]); cv.hline(x0, y0 + 2, x1 - x0, WD[1])
            for k in range(x0 + 5, x1 - 2, 11): cv.px(k, y0 + 1, WD[1])
        for xe in (x0 + 2, x1 - 5):                                          # cast-iron ends
            cv.rect(xe - 1, 166, 5, 34, OUTL); cv.rect(xe, 167, 3, 32, IR); cv.vline(xe, 167, 32, IRH)
            cv.rect(xe - 3, 183, 9, 3, OUTL); cv.rect(xe - 2, 183, 7, 2, IR); cv.hline(xe - 2, 183, 7, IRH)    # armrest
            cv.rect(xe - 2, 197, 7, 2, IR)
        cv.rect(x0 - 2, 185, x1 - x0 + 4, 8, OUTL)
        cv.rect(x0 - 1, 186, x1 - x0 + 2, 3, WD[3]); cv.hline(x0 - 1, 186, x1 - x0 + 2, WD[4])
        cv.rect(x0 - 1, 189, x1 - x0 + 2, 3, WD[2]); cv.hline(x0 - 1, 191, x1 - x0 + 2, WD[1])
        for k in range(x0 + 3, x1 - 2, 9): cv.px(k, 190, WD[1])
        self.soft_shadow(x0 + 4, 193, x1 - x0 + 4, 7, 0.45, fade=3, ao=0.8)
        self.ao[186:199, x0 - 2:x1 + 4] *= 0.92
        self.A['benches'].append((x0, x1, SEAT_Y))

    def park_ground(self, x0, x1):
        cv = self.cv
        yy, xx = np.mgrid[GROUND:CURB, x0:x1]
        u, v = xx.astype(float), yy.astype(float)
        t = 3.0 + (M.fbm(u, v * 1.6, 3.0, 2, 51) - 0.5) * 1.3 + (M.fbm(u, v, 22.0, 2, 52) - 0.5) * 0.7
        r = M.value_noise(u * 1.0, v * 1.0, 1.0, 53)
        t = np.where(r > 0.86, t + 1.0, t); t = np.where(r < 0.10, t - 1.0, t)
        t = t - np.clip((v - (CURB - 6)) / 6.0, 0, 1) * 0.6
        img = M.apply_ramp(np.clip(t, 0, 5), R('#d6c4a2', 6), xx, yy, True, band=2.0)
        cv.a[GROUND:CURB, x0:x1] = img
        # grass edge along the hedge (184..189) with tufts, and a grass verge by the curb (219..224)
        rng = np.random.default_rng(54)
        for (ya, yb) in ((GROUND, GROUND + 5), (CURB - 7, CURB - 2)):
            yy, xx = np.mgrid[ya:yb, x0:x1]
            tg = 3.4 + (M.fbm(xx.astype(float), yy.astype(float), 3.0, 2, 55 + ya) - 0.5) * 1.6 - (yy - ya) * 0.15
            cv.a[ya:yb, x0:x1] = M.apply_ramp(np.clip(tg, 0, 6), GREENS, xx, yy, True, band=2.0)
            for x in range(x0, x1):
                if rng.random() < 0.45:
                    hh = int(rng.integers(1, 3)); cv.vline(x, yb - 1, hh, GREENS[3] if rng.random() < 0.6 else GREENS[2])
                if rng.random() < 0.03: cv.px(x, int(rng.integers(ya, yb)), C(['#fff2c8', '#ffd04a', '#ff8ab0'][int(rng.integers(0, 3))]))
        cv.hline(x0, CURB - 2, x1 - x0, C('#b8ac98')); cv.hline(x0, CURB - 1, x1 - x0, C('#8a806e'))
        # pebbles / footprints
        for _ in range(90):
            px_, py_ = int(rng.integers(x0 + 2, x1 - 2)), int(rng.integers(GROUND + 6, CURB - 8))
            cv.px(px_, py_, C('#a89878') if rng.random() < 0.6 else C('#f0e4c8'))
        self.E[GROUND:CURB, x0:x1] = 0.0
        self.ao[GROUND:GROUND + 6, x0:x1] *= np.linspace(0.6, 1.0, 6)[:, None]
        self.bench(*BENCH_A); self.bench(*BENCH_B)
        # bin + drinking fountain
        bx = 204
        cv.rect(bx - 1, 182, 12, 18, OUTL); cv.rect(bx, 183, 10, 16, C('#3a6a5a')); cv.vline(bx, 183, 16, C('#5a8a7a'))
        cv.rect(bx - 1, 181, 12, 3, C('#2a4a40')); cv.hline(bx + 2, 188, 6, C('#2a4a40'))
        self.soft_shadow(bx + 4, 199, 12, 4, 0.45, fade=2)

    # ================================================================== cafe
    def cafe(self, x0, x1):
        cv = self.cv
        rp = self.wall(x0, x1, 22, '#efe0c4', 'siding', seed=81)
        self.cornice(x0, x1, 20, R('#d8c4a4', 6), 4)
        rng = np.random.default_rng(81)
        for k, wx in enumerate(range(x0 + 20, x1 - 30, 58)):
            self.window(wx, 40, 26, 34, frame='#2f5a4a', curtain=['#f4e4b0', '#f0c8c8', '#a8c8e8'][k % 3], box='#ff8ab0', rng=rng)
        self.cornice(x0, x1, 92, R('#c8b49a', 6), 4)
        self.shopfront(x0, x1, '#2f5a4a', '#3a2a24', ('#2f5a4a', '#f4eadc'), '咖啡 CAFE', '#2a2420', '#f4e0b0', 'cafe', door_at='left')
        # hanging cup sign
        hx = x1 - 22
        cv.rect(hx - 1, 104, 3, 2, C('#3a3a44')); cv.vline(hx, 106, 4, C('#3a3a44'))
        cv.ellipse(hx, 116, 7, 6, OUTL); cv.ellipse(hx, 116, 6, 5, C('#f4e8d0'))
        cv.rect(hx - 3, 113, 6, 6, C('#8a5a3a')); cv.hline(hx - 3, 113, 6, C('#c08a5a')); cv.px(hx + 3, 115, C('#8a5a3a'))
        self.E[104:123, hx - 8:hx + 8] = 0.0

    def cafe_terrace(self):
        """bistro chairs on the terrace (bg); the tables are mid sprites so they sit in front of the sitters."""
        cv = self.cv
        for (tx, foot) in ((372, 196), (438, 196), (494, 196)):
            self.A['tables'].append((tx, foot))
            cx = tx - 10                                                       # chair under the sitter (left of the table)
            cv.rect(cx - 6, foot - 22, 2, 22, OUTL); cv.vline(cx - 5, foot - 21, 21, C('#4a5a52'))
            cv.rect(cx - 6, foot - 11, 12, 2, C('#4a5a52')); cv.hline(cx - 6, foot - 12, 12, OUTL)
            cv.vline(cx + 4, foot - 9, 9, C('#4a5a52'))
            self.soft_shadow(tx - 12, foot, 30, 4, 0.5, fade=2, ao=0.85)
        # chalk A-board by the door
        bx = 336
        cv.poly([(bx, 198), (bx + 4, 176), (bx + 12, 176), (bx + 16, 198)], OUTL)
        cv.poly([(bx + 1, 197), (bx + 5, 177), (bx + 11, 177), (bx + 15, 197)], C('#2a3a34'))
        cup = ["......", ".####.", ".#..##", ".#..#.", ".###..", "######"]          # chalk coffee cup
        for j, r in enumerate(cup):
            for i, ch in enumerate(r):
                if ch == '#': cv.px(bx + 5 + i, 180 + j, C('#f4ecd8'))
        cv.px(bx + 7, 178, C('#c8d0c4')); cv.px(bx + 8, 177, C('#c8d0c4'))
        cv.hline(bx + 5, 190, 6, C('#f0c070')); cv.hline(bx + 5, 193, 5, C('#c8d0c4'))
        self.soft_shadow(bx + 6, 198, 16, 3, 0.5, fade=2)

    def table_sprite(self, lid=1.0, glow=1.0):
        """round bistro table + a laptop seen from its back (glowing logo).  lid: 1 open .. 0 shut.
        returns (rgba, E, ox, oy): put at (table_x - ox, foot - oy)."""
        Wd, Hd = 30, 30
        cv = Canvas(Wd, Hd); E = np.zeros((Hd, Wd), np.float32)
        ox, oy = 15, Hd - 1
        top = Hd - 20
        cv.rect(14, top + 2, 3, Hd - top - 4, OUTL); cv.vline(15, top + 2, Hd - top - 4, C('#5a6a62'))
        cv.rect(9, Hd - 3, 13, 2, OUTL); cv.hline(10, Hd - 3, 11, C('#5a6a62'))
        cv.ellipse(15, top, 12, 2.6, OUTL); cv.ellipse(15, top, 11, 1.8, C('#f0ece4')); cv.hline(5, top - 1, 20, C('#ffffff'))
        cv.hline(4, top + 2, 23, C('#a8a49c'))
        # coffee cup on the right edge
        cv.rect(22, top - 4, 4, 4, C('#f4f0e8')); cv.vline(25, top - 4, 4, C('#c8c0b4')); cv.px(26, top - 3, C('#f4f0e8'))
        cv.hline(22, top - 4, 4, C('#6a3a20'))
        # laptop: base on the table, lid hinged at its far (right) edge, seen from the back
        cv.rect(4, top - 2, 14, 2, OUTL); cv.hline(5, top - 2, 12, C('#c8ccd4'))
        lh = max(1, int(round(11 * lid)))
        lw = 10 if lid > 0.15 else 13
        lx = 6
        cv.rect(lx - 1, top - 2 - lh - 1, lw + 2, lh + 2, OUTL)
        cv.rect(lx, top - 2 - lh, lw, lh, C('#b8bcc6')); cv.vline(lx, top - 2 - lh, lh, C('#dfe2e8')); cv.vline(lx + lw - 1, top - 2 - lh, lh, C('#8a8e98'))
        if lid > 0.35:
            gx, gy = lx + lw // 2, top - 2 - lh // 2 - 1
            for (dx_, dy_) in ((0, 0), (-1, 0), (0, -1), (-1, -1), (0, 1), (1, 0)):
                cv.px(gx + dx_, gy + dy_, C('#eaf6ff')); E[gy + dy_, gx + dx_] = 0.9 * glow
            # screen light spilling over the top edge toward the sitter
            cv.hline(lx + 1, top - 3 - lh, lw - 2, C('#cfe6ff')); E[top - 3 - lh, lx + 1:lx + lw - 1] = 0.6 * glow
        return cv.a, E, ox, oy

    # ================================================================== apartment block
    def flat(self, x0, x1):
        cv = self.cv
        rp = self.wall(x0, x1, 4, '#bcc8dc', 'plaster', seed=91, mottle=0.45)
        self.cornice(x0, x1, 2, R('#a8b4c8', 6), 4)
        rng = np.random.default_rng(91)
        cols = [x0 + 18, x0 + 70, x0 + 124]
        for wx in cols:                                                 # 3rd floor
            self.window(wx, 14, 26, 28, frame='#f4ece0', curtain='#f0c8c8' if wx != cols[1] else '#f4e4b0', rng=rng, ac=(wx == cols[2]))
        # 2nd floor: two windows + the bedroom (quilt) window in the middle, a narrow balcony
        for wx in (cols[0], cols[2]):
            self.window(wx, 58, 26, 28, frame='#f4ece0', curtain='#a8c8e8', rng=rng, box='#ffd04a' if wx == cols[0] else None)
        qx, qy, qw, qh = x0 + 64, 54, 40, 34
        self.window(qx, qy, qw, qh, frame='#f4ece0', curtain=None, sill=True, panes=1, rng=rng)
        self.A['quilt_win'] = (qx + 1, qy + 1, qw - 2, qh - 2)
        by = qy + qh + 4
        cv.rect(qx - 7, by - 1, qw + 14, 5, OUTL); cv.rect(qx - 6, by, qw + 12, 3, C('#d8d4cc')); cv.hline(qx - 6, by, qw + 12, C('#f4f0e8'))
        cv.hline(qx - 6, by - 12, qw + 12, OUTL); cv.hline(qx - 6, by - 11, qw + 12, C('#6a6a74'))
        for bx in range(qx - 6, qx + qw + 6, 3): cv.vline(bx, by - 11, 11, C('#7a7a84'))
        self.soft_shadow(qx - 2, by + 4, qw + 14, 6, 0.3, fade=4, ao=0.85)
        self.cornice(x0, x1, 96, R('#a8b4c8', 6), 3)
        # ground floor: entrance with a little canopy, mailboxes, a window, potted plants
        dx = x0 + 72
        self.door(dx, 128, 26, GROUND - 128, '#4a6a8a')
        cv.rect(dx - 8, 118, 42, 4, OUTL); cv.rect(dx - 7, 118, 40, 3, C('#e8e4dc')); cv.hline(dx - 7, 118, 40, C('#ffffff'))
        self.soft_shadow(dx - 4, 122, 42, 6, 0.3, fade=4)
        cv.rect(dx + 30, 112, 14, 6, C('#3a4a6a')); cv.text(dx + 31, 110, '12', C('#ffffff'), 'p2p') if False else None
        cv.rect(dx + 31, 113, 12, 4, C('#f4f0e8')); cv.text(dx + 33, 111, '12', C('#3a4a6a'), 'zh8')
        mx = x0 + 14
        cv.rect(mx - 1, 142, 30, 20, OUTL)
        for i in range(3):
            for j in range(2):
                cv.rect(mx + i * 10, 143 + j * 10, 9, 9, C('#c8ccd4')); cv.hline(mx + i * 10, 143 + j * 10, 9, C('#eef0f4'))
                cv.hline(mx + i * 10 + 2, 146 + j * 10, 5, C('#5a5e66'))
        self.window(x0 + 124, 128, 30, 30, frame='#f4ece0', curtain='#f4e4b0', rng=rng, box='#ff6a8a')
        for px_ in (dx - 14, dx + 32):
            cv.rect(px_, 172, 10, 12, OUTL); cv.rect(px_ + 1, 173, 8, 11, C('#c86a4a')); cv.hline(px_ + 1, 173, 8, C('#e88a6a'))
            cv.ellipse(px_ + 5, 167, 6, 6, GREENS[2]); cv.ellipse(px_ + 4, 165, 4, 4, GREENS[3]); cv.px(px_ + 3, 163, GREENS[5])
            self.soft_shadow(px_ + 4, 184, 12, 3, 0.4, fade=2)
        # drain pipe on the right seam
        cv.rect(x1 - 6, 0, 5, GROUND, OUTL); cv.rect(x1 - 5, 0, 3, GROUND, C('#c8ccd4')); cv.vline(x1 - 5, 0, GROUND, C('#eef0f4'))
        for by_ in range(16, GROUND, 26): cv.rect(x1 - 7, by_, 7, 2, C('#8a8e98'))

    def quilt_patch(self, curtain=0.0, quilt='bulge', phone=1.0, sun=0.0, sleeper=None):
        """bedroom interior for the 2nd-floor window.  curtain 0 drawn .. 1 open; quilt 'bulge' (somebody under it
        with a phone - blue glow leaking out) | 'off' (thrown back); sun 0..1 morning light in the room.
        sleeper: optional rgba bust of the person sitting up (for quilt='off').  -> (rgba, E, x, y)."""
        x, y, w, h = self.A['quilt_win']
        cv = Canvas(w, h); E = np.zeros((h, w), np.float32)
        k = 0.45 + 0.55 * sun
        wall = mix(C('#5a5068'), C('#f0dcc0'), sun); wall2 = mix(C('#4a4258'), C('#e0c8ac'), sun)
        cv.rect(0, 0, w, h, wall)
        for yy in range(0, h, 2): cv.hline(0, yy, w, wall2) if yy % 4 == 0 else None
        # a poster + headboard
        cv.rect(4, 4, 8, 10, mix(C('#3a4a6a'), C('#6a8ac8'), sun)); cv.rect(5, 5, 6, 4, mix(C('#8a6a5a'), C('#ffd08a'), sun))
        bed_y = h - 12
        cv.rect(2, bed_y - 9, w - 4, 9, mix(C('#5a3a30'), C('#a8724a'), sun)); cv.hline(2, bed_y - 9, w - 4, mix(C('#7a5040'), C('#d09a6a'), sun))
        cv.rect(0, bed_y, w, h - bed_y, mix(C('#3a3448'), C('#c8b4a0'), sun))
        q0, q1 = mix(C('#3a4a7a'), C('#7aa0e0'), sun), mix(C('#2a3460'), C('#5a7ac0'), sun)
        if quilt == 'bulge':
            yy, xx = np.mgrid[0:h, 0:w]
            hump = (((xx - w * 0.5) / (w * 0.42)) ** 2 + ((yy - bed_y - 1) / 10.0) ** 2) < 1.0
            hump &= yy < h
            stripe = ((xx + yy // 2) // 4) % 2 == 0
            cv.a[hump & stripe] = q0; cv.a[hump & ~stripe] = q1
            top_edge = hump & ~np.roll(hump, 1, 0)
            cv.a[top_edge] = mix(q0, C('#ffffff'), 0.35)
            if phone > 0:     # glow leaking from under the quilt edge (left, where the head is)
                gx0, gx1 = int(w * 0.14), int(w * 0.32)
                for gx in range(gx0, gx1):
                    gy = bed_y + 4 + (gx - gx0) // 4
                    cv.px(gx, gy, C('#cfe8ff')); E[gy, gx] = 0.9 * phone
                    cv.px(gx, gy + 1, C('#8ab8f0')); E[gy + 1, gx] = 0.5 * phone
                g = np.exp(-(((xx - w * 0.22) / 7.0) ** 2 + ((yy - bed_y - 3) / 5.0) ** 2))
                E = np.maximum(E, (g * 0.35 * phone).astype(np.float32) * hump)
        else:
            cv.rect(0, bed_y + 1, w, 3, mix(C('#f4f0e8'), C('#ffffff'), sun))                      # sheet
            yy, xx = np.mgrid[0:h, 0:w]
            heap = (((xx - w * 0.82) / (w * 0.22)) ** 2 + ((yy - bed_y - 3) / 7.0) ** 2) < 1.0
            stripe = ((xx + yy // 2) // 4) % 2 == 0
            cv.a[heap & stripe] = q0; cv.a[heap & ~stripe] = q1
            if sleeper is not None:
                sh_, sw_ = sleeper.shape[:2]
                cv.blit(sleeper, int(w * 0.40 - sw_ / 2), bed_y + 4 - sh_)
        # sun patch on the wall
        if sun > 0:
            yy, xx = np.mgrid[0:h, 0:w]
            band = ((xx - yy * 0.6) > w * 0.15) & ((xx - yy * 0.6) < w * 0.15 + 12) & (yy < bed_y)
            cv.a[band, :3] = np.clip(cv.a[band, :3].astype(np.float32) * (1 + 0.25 * sun), 0, 255).astype(np.uint8)
        # curtains (slide to the sides as they open)
        cr = R('#c88a9a', 5)
        cwid = int(round((w / 2) * (1 - 0.72 * curtain)))
        for side in (0, 1):
            xs = 0 if side == 0 else w - cwid
            cv.rect(xs, 0, cwid, h, cr[3])
            for kk in range(xs + 1, xs + cwid, 2): cv.vline(kk, 1, h - 1, cr[2])
            cv.vline(xs + (cwid - 1 if side == 0 else 0), 0, h, cr[1]); cv.hline(xs, 0, cwid, cr[4])
        cv.hline(0, 0, w, C('#8a7a70'))
        # dim the room vs the bright facade, then the glass reflection on top
        a = cv.a.astype(np.float32); a[..., :3] *= (0.62 + 0.38 * sun); cv.a = np.clip(a, 0, 255).astype(np.uint8)
        for (o, wd, kk) in ((0.62, 5, 0.40), (0.80, 2, 0.28)):
            for i in range(h):
                xc = int(o * w) + (h - i) // 2 - h // 2
                for j in range(wd):
                    xx_ = xc + j
                    if 0 <= xx_ < w and ((0 < j < wd - 1) or (i + j) % 2 == 0):
                        cv.a[i, xx_, :3] = mix(tuple(int(v) for v in cv.a[i, xx_]), C('#fff0dc'), kk * (1 - 0.5 * curtain))[:3]
        cv.a[..., 3] = 255
        return cv.a, E, x, y

    # ================================================================== wedding hall
    COLS = (752, 838)
    def column_paint(self, cv, x, top, foot):
        """a round white porch column (fluted shaft, simple capital and base), centred on x."""
        rp = R('#f4eee6', 6)
        cv.rect(x - 7, top - 1, 15, foot - top + 1, OUTL)
        for yy in range(top + 4, foot - 4):
            for i, xx in enumerate(range(x - 5, x + 6)):
                s = i / 10.0
                lv = 4 if s < 0.25 else (3 if s < 0.55 else (2 if s < 0.85 else 1))
                if i in (2, 5, 8) and lv > 1: lv -= 1                         # flutes
                cv.px(xx, yy, rp[lv])
        cv.rect(x - 7, top, 15, 4, rp[4]); cv.hline(x - 7, top, 15, rp[5]); cv.hline(x - 7, top + 3, 15, rp[2])
        cv.rect(x - 7, foot - 4, 15, 4, rp[3]); cv.hline(x - 7, foot - 4, 15, rp[4]); cv.hline(x - 7, foot - 1, 15, rp[1])
        # ribbon + flower garland on the column
        cv.hline(x - 6, top + 20, 13, C('#ff8ab0')); cv.hline(x - 6, top + 21, 13, C('#e86a90'))
        for (dx_, col) in ((-4, '#ffffff'), (0, '#ffd0e0'), (4, '#ffffff')): cv.px(x + dx_, top + 19, C(col))

    def column_sprite(self):
        x, foot = self.A['column']; top = 104
        cv = Canvas(18, foot - top + 2)
        self.column_paint(cv, 8, 1, foot - top + 1)
        return cv.a, x - 8, top - 1

    def wedding(self, x0, x1):
        cv = self.cv
        rp = self.wall(x0, x1, 26, '#f4eee6', 'plaster', seed=101, mottle=0.35, dash=0.4)
        cxp = (x0 + x1) // 2
        # pediment
        for yy in range(6, 26):
            half = int((yy - 6) / 20.0 * ((x1 - x0) / 2 + 2))
            cv.hline(cxp - half, yy, 2 * half, rp[3] if yy > 8 else rp[4])
            cv.px(cxp - half - 1, yy, OUTL); cv.px(cxp + half, yy, OUTL)
            self.E[yy, max(0, cxp - half - 1):min(self.W, cxp + half + 1)] = 0.0
        cv.ellipse(cxp, 18, 5, 5, OUTL); cv.ellipse(cxp, 18, 4, 4, C('#e8c070')); cv.text(cxp - 4, 13, '囍', C('#c8302a'), 'zh8')
        self.E[12:24, cxp - 6:cxp + 7] = 0.0
        self.cornice(x0, x1, 26, R('#e0d6c8', 6), 4)
        # pilasters
        for px_ in (x0 + 8, x1 - 14):
            cv.rect(px_, 30, 7, GROUND - 30, rp[4]); cv.vline(px_, 30, GROUND - 30, rp[5]); cv.vline(px_ + 6, 30, GROUND - 30, rp[2])
            self.soft_shadow(px_ + 7, 30, 3, GROUND - 30, 0.4, fade=2)
        # arched windows (upper floor)
        for wx in (x0 + 28, cxp - 13, x1 - 54):
            self.window(wx, 46, 26, 34, frame='#f8f4ee', curtain='#fff0f4', rng=np.random.default_rng(wx), panes=2)
            for i in range(14):                                          # arch head
                a = math.pi * i / 13
                ax_, ay_ = wx + 13 - math.cos(a) * 14, 45 - math.sin(a) * 8
                cv.px(int(round(ax_)), int(round(ay_)), OUTL); cv.px(int(round(ax_)), int(round(ay_)) + 1, rp[5])
            cv.rect(wx + 1, 39, 24, 6, rp[3])
            for i in range(12):
                a = math.pi * (i + 0.5) / 12
                cv.px(int(round(wx + 13 - math.cos(a) * 11)), int(round(44 - math.sin(a) * 5)), C('#ffe8f0'))
        # gold sign band
        tw = text_width('幸福礼堂 WEDDING', 'zh8') + 6
        self.sign(cxp - tw // 2, 90, '幸福礼堂 WEDDING', bg='#fbf6ee', fg='#b8822a', border='#e8c070')
        # porch: entablature on two columns, arched double door, flower arch, balloons
        cv.rect(self.COLS[0] - 9, 100, self.COLS[1] - self.COLS[0] + 18, 5, OUTL)
        cv.rect(self.COLS[0] - 8, 101, self.COLS[1] - self.COLS[0] + 16, 3, rp[4]); cv.hline(self.COLS[0] - 8, 101, self.COLS[1] - self.COLS[0] + 16, rp[5])
        self.soft_shadow(self.COLS[0] - 4, 105, self.COLS[1] - self.COLS[0] + 12, 10, 0.3, fade=6, ao=0.75)
        dx, dw = cxp - 18, 36
        cv.rect(dx - 3, 120, dw + 6, GROUND - 120, OUTL)
        self.door(dx, 124, dw // 2, GROUND - 124, '#f0e4d4'); self.door(dx + dw // 2, 124, dw // 2, GROUND - 124, '#f0e4d4')
        rng = np.random.default_rng(103)
        for i in range(60):                                               # flower arch
            a = math.pi * i / 59
            r0 = 27 + rng.uniform(-1.5, 1.5)
            fx, fy = cxp - math.cos(a) * r0, 150 - math.sin(a) * (r0 * 1.25)
            for (ox_, oy_) in ((0, 0), (1, 0), (0, 1)):
                cv.px(int(round(fx)) + ox_, int(round(fy)) + oy_, GREENS[3] if rng.random() < 0.4 else C(['#ffffff', '#ffc0d4', '#ff8ab0', '#fff2c8'][int(rng.integers(0, 4))]))
            if rng.random() < 0.5: cv.px(int(round(fx)) - 1, int(round(fy)) + 1, GREENS[2])
        for side in (-1, 1):
            ax_ = cxp + side * 27
            for yy in range(150, GROUND):
                cv.px(ax_ + int(rng.integers(-1, 2)), yy, GREENS[int(rng.integers(2, 5))])
                if rng.random() < 0.3: cv.px(ax_ + int(rng.integers(-2, 3)), yy, C(['#ffffff', '#ffc0d4', '#ff8ab0'][int(rng.integers(0, 3))]))
        for bx_ in (x0 + 26, x1 - 26):                                     # balloon bunches
            cols = ['#ff8ab0', '#ffffff', '#f2c94c', '#ffb0c8', '#ffffff']
            pos = [(-5, -6), (4, -8), (0, -14), (-7, -15), (6, -17)]
            for k, ((ox_, oy_), cc) in enumerate(zip(pos, cols)):
                bxk, byk = bx_ + ox_, 132 + oy_
                cv.line(bxk, byk + 5, bx_, 170, C('#a89a90'))
                cv.ellipse(bxk, byk, 5, 6, OUTL); cv.ellipse(bxk, byk, 4, 5, C(cc)); cv.px(bxk - 2, byk - 3, C('#ffffff'))
                cv.ellipse(bxk + 1, byk + 2, 2, 2, R(cc, 5)[2]) if cc != '#ffffff' else cv.px(bxk + 2, byk + 3, C('#e0dcd8'))
                cv.px(bxk, byk + 6, R(cc, 5)[1])
            cv.rect(bx_ - 3, 170, 7, 14, OUTL); cv.rect(bx_ - 2, 171, 5, 13, C('#e8c070'))
            self.E[100:184, bx_ - 14:bx_ + 14] = np.where(cv.a[100:184, bx_ - 14:bx_ + 14, 3] > 0, 0.0, self.E[100:184, bx_ - 14:bx_ + 14])
        # columns (the right one is ALSO a mid sprite: the best man hides behind it)
        for x in self.COLS: self.column_paint(cv, x, 104, 190)
        self.A['column'] = (self.COLS[1], 190)
        self.A['hall_door'] = (cxp, GROUND)
        for x in self.COLS: self.soft_shadow(x + 7, 112, 8, 76, 0.35, fade=4)

    def wedding_ground(self):
        cv = self.cv
        cxp, _ = self.A['hall_door']
        for yy in range(GROUND, CURB):                                     # red carpet, widening toward the camera
            u = (yy - GROUND) / (CURB - GROUND)
            half = 15 + 9 * u
            x0, x1 = int(cxp - half), int(cxp + half)
            cv.hline(x0, yy, x1 - x0, C('#c8323a') if (yy % 7) else C('#b02a32'))
            cv.px(x0, yy, C('#f2c94c')); cv.px(x1 - 1, yy, C('#f2c94c')); cv.px(x0 - 1, yy, OUTL); cv.px(x1, yy, OUTL)
        for x in self.COLS:                                                 # column plinths on the sidewalk
            cv.rect(x - 9, 188, 19, 4, OUTL); cv.rect(x - 8, 188, 17, 3, C('#e8e2d8')); cv.hline(x - 8, 188, 17, C('#ffffff'))
            self.soft_shadow(x + 6, 191, 16, 4, 0.4, fade=3)
        # welcome easel
        ex = 712
        cv.line(ex, 200, ex + 6, 170, OUTL); cv.line(ex + 14, 200, ex + 8, 170, OUTL)
        cv.rect(ex - 1, 168, 16, 20, OUTL); cv.rect(ex, 169, 14, 18, C('#fbf6ee'))
        for j, r in enumerate([".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."]):    # heart
            for i, ch in enumerate(r):
                if ch == '#': cv.px(ex + 4 + i, 172 + j, C('#ffb0b0') if (i, j) == (1, 1) else C('#d8403a'))
        cv.hline(ex + 2, 181, 10, C('#c8a060')); cv.hline(ex + 3, 184, 8, C('#d8c8b0'))
        self.soft_shadow(ex + 4, 200, 16, 3, 0.4, fade=2)

    # ================================================================== street furniture
    def town_props(self):
        for x in (212, 526, 686): self.lamp(x)
        f = self.front_base
        for bx in (346, 610, 880):
            f.rect(bx - 1, 211, 6, 15, OUTL); f.rect(bx, 212, 4, 14, C('#5a5e6a')); f.vline(bx, 212, 14, C('#8a909e'))
            f.rect(bx, 215, 4, 2, C('#e8c040'))
        cv = self.cv
        # bicycle by the flats
        bk = 640
        for wx in (bk, bk + 18):
            cv.ellipse(wx, 196, 6.5, 6.5, OUTL); cv.ellipse(wx, 196, 5.5, 5.5, C('#2a2a33')); cv.ellipse(wx, 196, 4.4, 4.4, C('#d8c8b4'))
            cv.px(wx, 196, C('#8a8a96'))
        for (a, b) in (((bk, 196), (bk + 8, 187)), ((bk + 8, 187), (bk + 18, 196)), ((bk + 8, 187), (bk + 16, 187)), ((bk + 16, 187), (bk + 18, 196))):
            cv.line(*a, *b, C('#e86a5a'))
        cv.hline(bk + 6, 185, 4, C('#2a2a33')); cv.line(bk + 16, 187, bk + 17, 183, C('#2a2a33')); cv.hline(bk + 15, 182, 4, C('#2a2a33'))
        self.soft_shadow(bk + 4, 198, 26, 4, 0.45, fade=2)
        # fallen leaves under the park trees
        rng = np.random.default_rng(67)
        for tx in (64, 300):
            for _ in range(30):
                lx = int(tx + rng.normal(30, 30)); ly = int(rng.uniform(GROUND + 6, CURB - 3))
                if not (0 <= lx < self.W - 2): continue
                col = C(['#c8a040', '#a8803a', '#7a9a44', '#d8b860', '#9a6a34'][int(rng.integers(0, 5))])
                cv.px(lx, ly, col)
