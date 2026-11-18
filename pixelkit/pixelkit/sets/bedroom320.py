"""pixelkit.sets.bedroom320 - 深夜卧室（320x180 大像素一点透视版，v0.13《熬夜副本》开场 / 结尾）。

    b = Bedroom320()
    fr = b.frame(t, face='tired', phone='hold'|'drop'|None, screen=(160,230,255), clock='0347', bulbs=1.0)
    L  = b.light(fr, phone_k=1.0, moon_k=1.0, room_k=1.0, clock_k=1.0)
    img = fr.render(cam, L, GRADE_NIGHT, frame=i, ui=...)
锚点 b.A：head（人物头顶中心）、face（脸中心）、phone、clock、bed（床面中心）、window、door_wall。
"""
import math
import numpy as np
from ..core import C
from ..pixstage import Stage
from ..characters import human

DIG = {'0': ['###', '#.#', '#.#', '#.#', '###'], '1': ['.#.', '##.', '.#.', '.#.', '###'], '2': ['###', '..#', '###', '#..', '###'],
       '3': ['###', '..#', '.##', '..#', '###'], '4': ['#.#', '#.#', '###', '..#', '..#'], '5': ['###', '#..', '###', '..#', '###'],
       '6': ['###', '#..', '###', '#.#', '###'], '7': ['###', '..#', '..#', '.#.', '.#.'], '8': ['###', '#.#', '###', '#.#', '###'],
       '9': ['###', '#.#', '###', '..#', '###'], ':': ['...', '.#.', '...', '.#.', '...']}

def digits(st, x, y, s, c, E=1.0):
    cx = x
    for ch in s:
        rows = DIG.get(ch)
        if rows is None: cx += 2; continue
        for r, row in enumerate(rows):
            for k, v in enumerate(row):
                if v == '#': st.px(cx + k, y + r, c, E)
        cx += 4 if ch != ':' else 2
    return cx

SLEEPER = human.Look(hair='messy', hair_col='#22202c', skin='#f0c49e', glasses=None, bags=True, cloth='hoodie', cloth_col='#5d6f9a')

class Bedroom320:
    W, H = 320, 180
    VX, VY = 160, 66
    BW = (72, 22, 248, 118)

    def __init__(self):
        self.A = dict(head=(186, 92), face=(186, 102), phone=(205, 104), clock=(250, 95), bed=(191, 140),
                      window=(86, 32, 46, 52), moon=(118, 46))
        self.st = Stage(self.W, self.H)
        self._paint(self.st)
        self.base = self.st.snapshot()

    # ---------------------------------------------------------------- static set
    def _paint(self, s):
        W, H = self.W, self.H; x0, y0, x1, y1 = self.BW; yy, xx = s.yy, s.xx
        s.rect(0, 0, W, H, '#08080f')
        s.poly([(0, 0), (W, 0), (x1, y0), (x0, y0)], '#0b0b17')
        lw = s.poly([(0, 0), (x0, y0), (x0, y1), (0, H)], '#11121f')
        rw = s.poly([(W, 0), (x1, y0), (x1, y1), (W, H)], '#0f101c')
        s.rect(x0, y0, x1 - x0, y1 - y0, '#171829')
        s.rect(x0, 98, x1 - x0, 20, '#131424'); s.rect(x0, 97, x1 - x0, 1, '#262842')
        s.fill(s.M_poly([(0, 150), (x0, 98), (x0, y1), (0, H)]) & lw, '#0e0f1b')
        s.fill(s.M_poly([(W, 150), (x1, 98), (x1, y1), (W, H)]) & rw, '#0d0e19')
        s.line(0, 149, x0, 97, '#20223a', mask=lw); s.line(W - 1, 149, x1, 97, '#1e2036', mask=rw)
        for x in range(x0 + 10, x1, 22): s.rect(x, 24, 1, 72, '#141526')
        fl = s.poly([(0, H), (x0, y1), (x1, y1), (W, H)], '#1a1218')
        for k in range(25):
            xa = x0 + (x1 - x0) * k / 24; xb = -150 + 620 * k / 24
            s.line(xa, y1, xb, H, '#140d13', mask=fl)
        for yb in (124, 133, 146, 163):
            s.fill(fl & (yy == yb), '#170f15')
        self.floor = fl
        # window + curtains
        wx, wy, ww, wh = self.A['window']
        s.rect(wx - 3, wy - 3, ww + 6, wh + 6, '#c8902e'); s.rect(wx - 2, wy - 2, ww + 4, wh + 4, '#f2c35a'); s.rect(wx - 1, wy - 1, ww + 2, wh + 2, '#6a4a1e')
        sky = s.rect(wx, wy, ww, wh, '#0f1a44', 0.85); s.fill(sky & (yy > wy + 30), '#14225a', 0.85)
        # distant skyline in the lower panes
        rng = np.random.default_rng(4)
        bx = wx
        while bx < wx + ww:
            bw_ = int(rng.integers(4, 8)); bh = int(rng.integers(6, 18))
            m = s.M_rect(bx, wy + wh - bh, bw_, bh) & sky; s.fill(m, '#0a0f2a', 0.0)
            for wy_ in range(wy + wh - bh + 2, wy + wh - 1, 3):
                for wx_ in range(bx + 1, bx + bw_ - 1, 2):
                    if rng.random() < 0.3: s.px(wx_, wy_, ['#ffcf7a', '#9fd2ff'][int(rng.integers(0, 2))], 0.9)
            bx += bw_ + 1
        for (sx, sy) in [(92, 38), (100, 50), (124, 40), (107, 36), (95, 44), (128, 52)]: s.px(sx, sy, '#fff4d0', 1.0)
        mx, my = self.A['moon']
        s.ell(mx, my, 6, 6, '#fff0c4', 1.0); s.fill(s.M_ell(mx + 2, my - 2, 5, 5) & s.M_ell(mx, my, 6, 6), '#ffe6a8', 1.0)
        s.px(mx - 2, my + 1, '#e8d090', 1.0); s.px(mx + 1, my + 3, '#e8d090', 1.0)
        s.rect(wx + ww // 2 - 1, wy, 2, wh, '#f2c35a'); s.rect(wx, wy + wh // 2 - 1, ww, 2, '#f2c35a')
        s.rect(wx - 6, wy + wh + 3, ww + 12, 3, '#f2c35a'); s.rect(wx - 6, wy + wh + 6, ww + 12, 1, '#8a5e20')
        for cxx in (wx - 13, wx + ww + 3):
            s.rect(cxx, wy - 8, 10, wh + 22, '#4a1830'); s.rect(cxx + 2, wy - 8, 2, wh + 22, '#6a2440'); s.rect(cxx + 6, wy - 8, 1, wh + 22, '#3a1024')
        s.rect(wx - 16, wy - 10, ww + 32, 2, '#c8902e')
        # moonbeam (hard, two bands) on the wall below the sill + the floor
        beam = s.M_poly([(wx, wy + wh + 7), (wx + ww, wy + wh + 7), (150, H), (40, H)]) & (yy > wy + wh + 6)
        s.add(beam, (22, 26, 48))
        core = s.M_poly([(wx + 8, wy + wh + 7), (wx + ww - 8, wy + wh + 7), (128, H), (62, H)]) & beam & (yy > y1 + 8)
        s.add(core, (14, 16, 30))
        self.beam = beam
        # left-foreground desk (perspective) with dark monitor, cans, noodle cup
        dtop = s.poly([(0, 128), (34, 112), (60, 116), (30, 136)], '#4a2a22'); s.fill(dtop & (yy <= 116), '#5e3628')
        s.poly([(0, 136), (30, 136), (30, 180), (0, 180)], '#2a1612'); s.poly([(30, 136), (60, 116), (60, 150), (30, 180)], '#22120e')
        s.line(0, 128, 34, 112, '#c8902e'); s.line(34, 112, 60, 116, '#8a5e20')
        mon = s.poly([(14, 98), (40, 88), (40, 108), (14, 118)], '#15141c'); s.outline(mon)
        s.poly([(16, 99), (38, 90), (38, 106), (16, 115)], '#0a0a12')
        s.px(37, 107, '#ffb347', 1.0)
        for i, (cx_, c) in enumerate([(44, '#3aa860'), (48, '#3aa860'), (52, '#e0503a')]):
            m = s.rect(cx_, 106 + i, 3, 7, c); s.px(cx_, 106 + i, '#d8dce6'); s.outline(m, '#08060a')
        nd = s.rect(20, 118, 6, 6, '#e8e0d0'); s.rect(20, 118, 6, 1, '#c84a3a'); s.outline(nd, '#08060a')
        # poster on the left wall (perspective parallelogram)
        pm = s.poly([(26, 46), (52, 40), (52, 76), (26, 86)], '#2d2458'); s.outline(pm, '#c8902e')
        s.ell(39, 58, 6, 6, '#ff8a5a'); s.ell(39, 58, 4, 4, '#ffc070')
        s.text(29, 70, 'LV.99', '#ffd85a', 'silk')
        # rug
        s.poly([(96, 172), (264, 172), (232, 124), (130, 124)], '#4a1a2e')
        inner = s.poly([(102, 168), (258, 168), (228, 128), (134, 128)], '#5e2238'); s.outline(inner, '#c8902e')
        for k in range(5): s.ell(150 + k * 15, 150, 2, 1, '#c8902e')
        # bed
        hb = s.rect(150, 74, 82, 44, '#4a2420'); s.rect(152, 76, 78, 40, '#5e2e28'); s.rect(150, 74, 82, 2, '#e8b04a'); s.outline(hb)
        for px_ in (156, 190, 224): s.rect(px_, 80, 2, 2, '#e8b04a')
        s.poly([(146, 118), (236, 118), (262, 168), (120, 168)], '#3a1c1a')
        s.poly([(120, 168), (262, 168), (262, 176), (120, 176)], '#2a1210'); s.rect(120, 168, 142, 1, '#e8b04a')
        s.poly([(148, 112), (234, 112), (258, 160), (124, 160)], '#c8c2dc')
        pil = s.ell(191, 108, 26, 7, '#e8e4f4'); s.fill(s.M_ell(191, 110, 24, 4) & pil, '#cfc8e4')
        # nightstand + clock body + cans
        ns = s.poly([(238, 100), (262, 100), (268, 132), (236, 132)], '#3a1c1a'); s.poly([(238, 100), (262, 100), (263, 104), (237, 104)], '#5a2e28'); s.outline(ns)
        s.rect(245, 114, 10, 1, '#c8902e')
        ck = s.rect(240, 90, 20, 10, '#0e0c12'); s.outline(ck)
        for i, c in enumerate(('#3aa860', '#e0503a')):
            m = s.rect(252 + i * 5, 96 - 0, 3, 5, c); s.px(252 + i * 5, 96, '#d8dce6')
        # bookshelf (right wall, perspective)
        sh = s.poly([(276, 40), (306, 22), (306, 150), (276, 132)], '#2a1614'); s.outline(sh)
        for k in range(4):
            yb = 52 + k * 24
            s.poly([(277, yb), (305, yb - 15), (305, yb - 13), (277, yb + 2)], '#c8902e')
            for j in range(5):
                cx_ = 279 + j * 5; top = yb - 12 - j * 2.7
                c = ['#7a2a2a', '#2a4a7a', '#7a6a2a', '#2a6a4a', '#5a2a6a'][(j + k) % 5]
                s.poly([(cx_, top), (cx_ + 4, top - 2.5), (cx_ + 4, yb - 2.4 * (j + 1) + 1), (cx_, yb - 2.4 * j + 1)], c)
        # fairy-light wire
        self.bulbs = []
        for i in range(14):
            u = i / 13; self.bulbs.append((x0 + 6 + (x1 - x0 - 12) * u, y0 + 6 + 5 * math.sin(math.pi * (u * 3 % 1))))
        for (a, b) in zip(self.bulbs, self.bulbs[1:]): s.line(a[0], a[1], b[0], b[1], '#05040a')

    # ---------------------------------------------------------------- dynamic
    def blanket(self, s):
        yy = s.yy
        bl = s.M_poly([(140, 116), (242, 116), (264, 162), (118, 162)]) | s.M_ell(191, 118, 52, 6)
        s.fill(bl, '#26346e'); s.fill(bl & s.M_poly([(160, 116), (222, 116), (236, 162), (146, 162)]), '#2c3c80')
        s.fill(bl & s.M_ell(160, 140, 18, 10), '#22306a'); s.fill(bl & s.M_ell(225, 145, 16, 9), '#22306a')
        s.fill(bl & s.M_poly([(170, 116), (214, 116), (224, 132), (164, 132)]), '#33448c')
        for (a, b) in [((150, 130), (138, 158)), ((176, 128), (170, 160)), ((210, 128), (222, 160)), ((232, 130), (248, 156))]:
            s.line(a[0], a[1], b[0], b[1], '#1c2858', mask=bl)
        s.fill(bl & (yy >= 112) & (yy <= 114), '#e8e0c8'); s.outline(bl)
        return bl

    def frame(self, t=0.0, face='tired', look=(2, 0), phone='hold', screen=(191, 244, 255), clock='0347', colon=True,
              bulbs=1.0, person=True, head_dy=0):
        s = self.st.from_snapshot(self.base)
        if person:
            p = human.draw(SLEEPER, face=face, arms='rest', look=look, head_dy=head_dy)
            hs = p.body.cv.a[:30, :]; hx, hy = self.A['head']
            s.sprite(hs, hx - p.ax, hy - p.ay)
        self.blanket(s)
        if phone == 'hold':
            ph = s.poly([(206, 96), (216, 98), (214, 116), (204, 114)], '#15141c'); s.outline(ph)
            s.poly([(204, 97), (206, 96), (204, 114), (202, 113)], tuple(screen), 1.0)
            hm = s.ell(210, 117, 4, 3, '#f0c49e'); s.outline(hm)
        elif phone == 'drop':
            ph = s.poly([(214, 126), (230, 124), (232, 132), (216, 134)], tuple(screen), 1.0); s.outline(ph)
            s.ell(205, 128, 4, 3, '#f0c49e')
        # clock
        if clock:
            c = '#ff3a2e'
            s.rect(241, 92, 18, 6, '#0e0c12')
            digits(s, 242, 92, clock[:2], c); digits(s, 251, 92, clock[2:], c)
            if colon: s.px(250, 93, c, 1.0); s.px(250, 95, c, 1.0)
        # bulbs
        for i, (x, y) in enumerate(self.bulbs):
            k = bulbs * (0.75 + 0.25 * math.sin(t * 2.2 + i * 1.9))
            if k > 0.05: s.rect(int(x), int(y) + 1, 1, 2, ['#ffcf6a', '#ff8a5a', '#ffe9a8'][i % 3], k)
        return s

    def light(self, s, phone_k=1.0, moon_k=1.0, room_k=1.0, clock_k=1.0, phone_col=(0.55, 0.85, 1.0), phone_xy=None):
        L = s.light_base((0.78, 0.80, 1.0), room_k)
        if phone_k > 0:
            px, py = phone_xy or (200, 100)
            L = L + s.band(px, py, 44, 26, phone_col, [(1.0, 0.18 * phone_k), (0.62, 0.32 * phone_k), (0.30, 0.44 * phone_k)])
        if clock_k > 0:
            L = L + s.band(250, 95, 18, 12, (1.0, 0.25, 0.2), [(1.0, 0.25 * clock_k), (0.5, 0.5 * clock_k)])
        return L
