"""pixelkit.sets.cave320 - 地下洞穴营地（320x180 一点透视，v0.13《熬夜副本》第 1 关 1938）。

隧道往灭点收进黑暗；木板平台上两张行军床、中间实验桌 + 马灯（唯一暖光）；石笋 / 钟乳石剪影；
洞壁右侧一块平整岩面给「粉笔 28 格钟 / 体温曲线」用（self.A['chalk'] 区域）。

    cv = Cave320()
    fr = cv.frame(t, lamp=1.0, chalk_k=0..1, graph_k=0..1)
    L  = cv.light(fr, lamp=1.0, flicker=t)
    img = fr.render(cam, L, GRADE_WARM_DARK, air=cv.air(fr, t))
锚点 A: lamp, table, bed_l, bed_r, stand_l（左侧人物站位脚底）, stand_r, chalk (x, y, w, h), mouth（隧道口）
"""
import math
import numpy as np
from ..pixstage import Stage, GRADE_NIGHT
from .. import post

GRADE_CAVE = dict(post.GRADES['golden_hd2d'])
GRADE_CAVE.update(grain=0.014, vignette=0.48, sat=1.08, contrast=1.14, black=0.02,
                  bloom=dict(thr=0.74, knee=0.22, strength=0.55, tint=(1.0, 0.82, 0.62), halation=0.22))

class Cave320:
    W, H = 320, 180
    VX, VY = 168, 72

    def __init__(self, seed=5):
        self.rng = np.random.default_rng(seed)
        self.A = dict(lamp=(150, 104), table=(150, 122), bed_l=(70, 134), bed_r=(232, 136), stand_l=(104, 150), stand_r=(196, 150),
                      chalk=(236, 34, 66, 56), mouth=(168, 72))
        self.st = Stage(self.W, self.H)
        self._paint(self.st)
        self.base = self.st.snapshot()

    def _rock(self, s, m, tones, seed=0, scale=7):
        """fill a mask with chunky 3-tone rock facets (no fine noise)."""
        rng = np.random.default_rng(seed)
        yy, xx = s.yy, s.xx
        cell = (xx // scale + (yy // scale) * 977 + seed * 31) % 9973
        v = (np.sin(cell * 12.9898) * 43758.5453) % 1.0
        idx = np.clip((v * len(tones)).astype(int), 0, len(tones) - 1)
        for i, c in enumerate(tones):
            s.fill(m & (idx == i), c)

    def _paint(self, s):
        W, H, VX, VY = self.W, self.H, self.VX, self.VY; yy, xx = s.yy, s.xx
        s.rect(0, 0, W, H, '#050407')
        # tunnel rings receding into the dark (one-point perspective)
        for k, (sc, c, rim) in enumerate([(1.0, '#2a1c17', '#5a3e2c'), (0.74, '#21160f', '#4a3224'), (0.54, '#180f0b', '#3a261a'),
                                           (0.38, '#100a08', '#2a1a12'), (0.25, '#0a0606', '#1c120c')]):
            rx, ry = 190 * sc, 112 * sc
            pts = []
            for i in range(48):
                a = math.pi + i / 47 * math.pi
                j = 1 + 0.07 * math.sin(i * 2.7 + k) + 0.05 * math.sin(i * 5.3 + 2 * k)
                pts.append((VX + rx * j * math.cos(a), VY + 8 * sc + ry * j * math.sin(a)))
            pts += [(VX + rx * 1.1, VY + 8 * sc + 60 * sc), (VX - rx * 1.1, VY + 8 * sc + 60 * sc)]
            m = s.M_poly(pts)
            s.fill(m, c)
            s.fill(s.ring(m) & (yy < VY + 8 * sc + 40 * sc), rim)
        # the far dark hole
        s.ell(VX, VY + 2, 20, 14, '#020203')
        # left + right rock walls (big faceted planes)
        lw = s.M_poly([(0, 0), (92, 0), (118, 40), (112, 112), (80, 128), (0, 150)])
        rw = s.M_poly([(W, 0), (236, 0), (224, 30), (228, 104), (262, 124), (W, 146)])
        self._rock(s, lw, ['#33221c', '#382620', '#2e1f1a', '#3c2a22'], 1, 12)
        self._rock(s, rw, ['#33221c', '#382620', '#2e1f1a', '#3c2a22'], 2, 12)
        s.fill(s.ring(lw) & ~lw.copy() if False else s.ring(~lw) & lw, '#6a4a34')
        s.fill(s.ring(~rw) & rw, '#5a3e2c')
        # flat slab on the right wall for chalk drawings
        cx, cy, cw, ch = self.A['chalk']
        slab = s.M_poly([(cx - 4, cy - 2), (cx + cw + 6, cy - 6), (cx + cw + 8, cy + ch + 6), (cx - 2, cy + ch + 4)])
        s.fill(slab, '#2e2420'); s.fill(s.ring(slab), '#1a1210')
        # ceiling with stalactites
        ceil = s.M_poly([(0, 0), (W, 0), (W, 12), (0, 16)])
        s.fill(ceil, '#120c0b')
        for i in range(26):
            x = self.rng.uniform(0, W); L = self.rng.uniform(8, 34) * (1 - abs(x - VX) / 260); w = self.rng.uniform(3, 8)
            s.poly([(x - w, 0), (x + w, 0), (x + w * 0.2, L)], '#1a1210' if i % 3 else '#241814')
            s.px(x + w * 0.2, L, '#5a4a40')
        # floor: rock + plank platform (perspective)
        fl = s.M_poly([(0, 150), (80, 128), (112, 112), (224, 104), (262, 124), (W, 146), (W, H), (0, H)])
        self._rock(s, fl, ['#1e1512', '#241a16', '#1a1210'], 3, 8)
        plat = s.M_poly([(20, H), (92, 122), (246, 120), (304, H)])
        s.fill(plat, '#4a3022')
        for k in range(14):
            xa = 92 + (246 - 92) * k / 13; xb = 20 + (304 - 20) * k / 13
            s.line(xa, 122, xb, H, '#36221a', mask=plat)
        s.fill(plat & ((yy == 121) | (yy == 122)), '#6a4630')
        # camp beds (left/right, perspective boxes)
        for (x0, x1, yb, flip) in ((44, 110, 150, 0), (196, 266, 152, 1)):
            frame = s.poly([(x0, yb - 14), (x1, yb - 18), (x1 + 4, yb - 6), (x0 - 4, yb - 2)], '#5a5040')
            s.poly([(x0, yb - 20), (x1, yb - 24), (x1, yb - 18), (x0, yb - 14)], '#8a8270')         # canvas top
            s.poly([(x0 + 2, yb - 20), (x1 - 18, yb - 23), (x1 - 18, yb - 19), (x0 + 2, yb - 15)], '#6a6a7a')   # grey blanket
            pil = (x1 - 14, yb - 24) if not flip else (x0 + 2, yb - 21)
            s.rect(pil[0], pil[1] - 2, 12, 5, '#d8d0c0')
            for lx in (x0, x1): s.rect(lx, yb - 14, 2, 12, '#2a2418')
            s.outline(frame, '#0a0606')
        # table centre + instruments
        tb = s.poly([(118, 116), (184, 114), (190, 124), (112, 126)], '#6a4630'); s.outline(tb, '#120a06')
        s.poly([(112, 126), (190, 124), (190, 127), (112, 129)], '#4a3022')
        for lx in (116, 186): s.rect(lx, 127, 2, 16, '#3a2418')
        s.rect(160, 110, 12, 6, '#e8e0cc'); s.rect(161, 111, 10, 1, '#a89878')     # notebook
        s.rect(128, 108, 3, 8, '#c8d0d8'); s.rect(129, 109, 1, 6, '#e05040')        # thermometer
        s.rect(136, 112, 8, 4, '#3a3a42'); s.px(140, 112, '#a0a8b0')                # instrument box
        # crates + rope ladder
        for (bx, by, bw, bh) in ((14, 128, 22, 16), (24, 116, 16, 12), (272, 132, 26, 18)):
            m = s.rect(bx, by, bw, bh, '#5a3a24'); s.rect(bx, by, bw, 2, '#7a5236'); s.line(bx, by, bx + bw - 1, by + bh - 1, '#3a2418', mask=m); s.outline(m, '#0a0604')
        for y in range(0, 100, 6):
            s.rect(96, y, 6, 1, '#7a6040'); s.px(95, y, '#5a4428'); s.px(102, y, '#5a4428')
        s.line(95, 0, 95, 100, '#5a4428'); s.line(102, 0, 102, 100, '#5a4428')
        # water puddle near the front (reflects the lamp later)
        s.ell(206, 168, 22, 4, '#0e0c10')

    # ---------------------------------------------------------------- dynamic
    def frame(self, t=0.0, lamp=1.0, drips=True):
        s = self.st.from_snapshot(self.base)
        lx, ly = self.A['lamp']
        # lantern: brass frame + glass + flame
        s.rect(lx - 4, ly - 2, 9, 12, '#8a6a2a'); s.rect(lx - 3, ly - 1, 7, 9, '#ffcf70' if lamp > 0 else '#3a3020', lamp)
        fl = 0.85 + 0.15 * math.sin(t * 13) * math.sin(t * 7.1)
        if lamp > 0: s.rect(lx - 1, ly + 2, 3, 4, '#fff4d0', min(1, lamp * fl)); s.px(lx, ly + 1, '#fff8e0', lamp)
        s.rect(lx - 2, ly - 4, 5, 2, '#5a4418'); s.px(lx, ly - 6, '#5a4418'); s.rect(lx - 4, ly + 10, 9, 2, '#5a4418')
        if drips:
            for i, x in enumerate((60, 214, 258)):
                ph = (t * 0.7 + i * 0.37) % 1.0
                y = 18 + ph * 110
                if ph < 0.9: s.px(x, y, '#a8c8e8', 0.5)
        # puddle glints
        s.px(200 + int(4 * math.sin(t * 2)), 168, '#ffcf70', 0.6 * lamp)
        return s

    def light(self, s, lamp=1.0, t=0.0, extra=None):
        L = s.light_base((0.50, 0.46, 0.70), 0.78)
        fl = 0.92 + 0.08 * math.sin(t * 13) * math.sin(t * 7.1)
        lx, ly = self.A['lamp']
        k = lamp * fl
        L = L + s.band(lx, ly + 4, 150, 96, (1.0, 0.72, 0.42), [(1.0, 0.30 * k), (0.66, 0.55 * k), (0.40, 0.85 * k), (0.20, 1.10 * k)])
        return L

    def air(self, s, lamp=1.0, t=0.0):
        lx, ly = self.A['lamp']
        return s.band(lx, ly + 3, 26, 22, (1.0, 0.75, 0.45), [(1.0, 0.05 * lamp), (0.55, 0.10 * lamp)])
