"""pixelkit.sets.lab1953 - 50 年代深夜睡眠实验室（320x180 一点透视，v0.13《熬夜副本》第 2 关）。

绿罩台灯（唯一暖光，硬边光池）、整面墙的仪器表盘（指针可动）、老式脑电仪（纸带 + 记录笔，内容动态）、
小铁床（孩子睡在上面，头上电极线连到仪器）、窗外夜色。
    lab = Lab1953()
    fr = lab.frame(t, needles=0..1, pens=fn(t, ch)->dy, smoke=0..1)
    L  = lab.light(fr, lamp=1.0)
锚点 A：lamp, bed_head（孩子头的中心）, chair（研究员脚底）, eeg（纸带区域 x, y, w, h）, dials（表盘中心列表）
"""
import math
import numpy as np
from ..pixstage import Stage
from .. import post

GRADE_LAB = dict(post.GRADES['golden_hd2d'])
GRADE_LAB.update(grain=0.014, vignette=0.46, sat=1.06, contrast=1.14, black=0.02,
                 bloom=dict(thr=0.74, knee=0.22, strength=0.55, tint=(1.0, 0.86, 0.66), halation=0.2))

class Lab1953:
    W, H = 320, 180
    BW = (64, 18, 256, 120)

    def __init__(self):
        self.A = dict(lamp=(118, 92), bed_head=(214, 116), chair=(150, 156), eeg=(28, 96, 40, 30),
                      dials=[(84 + i * 18, 40 + (i % 2) * 14) for i in range(6)])
        self.st = Stage(self.W, self.H); self._paint(self.st); self.base = self.st.snapshot()

    def _paint(self, s):
        W, H = self.W, self.H; x0, y0, x1, y1 = self.BW; yy = s.yy
        s.rect(0, 0, W, H, '#0b0a0c')
        s.poly([(0, 0), (W, 0), (x1, y0), (x0, y0)], '#121012')
        s.poly([(0, 0), (x0, y0), (x0, y1), (0, H)], '#1a1714')
        s.poly([(W, 0), (x1, y0), (x1, y1), (W, H)], '#171412')
        s.rect(x0, y0, x1 - x0, y1 - y0, '#2a2620')
        s.rect(x0, 84, x1 - x0, 36, '#22362e'); s.rect(x0, 84, x1 - x0, 1, '#4a6a5a')            # green tile wainscot
        for x in range(x0, x1, 8): s.rect(x, 85, 1, 35, '#1c2c26')
        for y in range(92, 120, 8): s.rect(x0, y, x1 - x0, 1, '#1c2c26')
        fl = s.poly([(0, H), (x0, y1), (x1, y1), (W, H)], '#1c1a18')
        for k in range(17):
            s.line(x0 + (x1 - x0) * k / 16, y1, -120 + 560 * k / 16, H, '#161412', mask=fl)
        for yb in (126, 136, 150, 170): s.fill(fl & (yy == yb), '#161412')
        # instrument wall: rack with round dials
        rack = s.rect(74, 26, 112, 44, '#3a3a34'); s.outline(rack, '#0a0a08'); s.rect(74, 26, 112, 2, '#5a5a50')
        for (dx, dy) in self.A['dials']:
            m = s.ell(dx, dy, 6, 6, '#e8e0c8'); s.outline(m, '#0a0a08'); s.ell(dx, dy, 5, 5, '#d8d0b4')
            s.rect(dx - 4, dy + 2, 8, 1, '#a8a088')
        for i in range(10): s.rect(80 + i * 10, 64, 3, 2, ['#c83a2a', '#3ac84a', '#e8b030'][i % 3], 0.6)
        # window on the right part of the back wall
        wx, wy, ww, wh = 202, 30, 40, 40
        s.rect(wx - 2, wy - 2, ww + 4, wh + 4, '#5a4a38'); win = s.rect(wx, wy, ww, wh, '#0d1638', 0.7)
        for (sx, sy) in ((208, 36), (230, 42), (216, 52), (236, 34)): s.px(sx, sy, '#fff4d0', 1.0)
        s.rect(wx + ww // 2 - 1, wy, 2, wh, '#5a4a38'); s.rect(wx, wy + wh // 2 - 1, ww, 2, '#5a4a38')
        # EEG machine (left, perspective cabinet) with paper strip window
        cab = s.poly([(8, 84), (60, 78), (66, 150), (4, 160)], '#4a4a40'); s.outline(cab, '#0a0a08')
        s.poly([(8, 84), (60, 78), (62, 82), (8, 88)], '#6a6a5a')
        ex, ey, ew, eh = self.A['eeg']
        s.rect(ex - 2, ey - 2, ew + 4, eh + 4, '#2a2a24'); s.rect(ex, ey, ew, eh, '#f2ead6')
        for k in range(4): s.rect(ex, ey + 4 + k * 7, ew, 1, '#d8c8a8')
        for k in range(3): s.ell(16 + k * 12, 140, 3, 3, '#1a1a16'); s.px(16 + k * 12, 139, '#8a8a7a')
        # cables from the machine to the bed
        for k in range(3):
            pts = [(62, 100 + k * 3), (120, 150 + k * 2), (180, 138 + k), (206, 112 + k * 2)]
            for (a, b) in zip(pts, pts[1:]): s.line(a[0], a[1], b[0], b[1], ['#c83a2a', '#3a6ac8', '#e8e0c8'][k])
        # desk with the green lamp (centre-left)
        dk = s.poly([(84, 112), (150, 110), (156, 120), (80, 122)], '#5a3a26'); s.outline(dk, '#0a0604')
        s.poly([(80, 122), (156, 120), (156, 124), (80, 126)], '#3a2418')
        for lx in (84, 152): s.rect(lx, 124, 2, 30, '#2a1a12')
        s.rect(96, 106, 14, 5, '#e8e0cc'); s.rect(97, 107, 12, 1, '#a89878')     # logbook
        s.rect(134, 104, 6, 7, '#7a5a3a'); s.rect(135, 103, 4, 1, '#e8e0cc')    # coffee cup
        # iron bed (right) + pillow
        frm = s.poly([(178, 124), (262, 120), (284, 158), (176, 164)], '#3a3a44')
        s.poly([(180, 118), (262, 114), (262, 122), (180, 126)], '#d8d4dc')
        for x in range(254, 272, 4): s.line(x, 92, x + 6, 128, '#6a6a7a')
        s.line(254, 92, 272, 92, '#8a8a9a'); s.line(254, 92, 254, 118, '#8a8a9a')
        s.ell(216, 118, 16, 5, '#ece8f2')
        s.outline(frm, '#08080a')
        # chair for the researcher
        s.poly([(132, 132), (160, 130), (162, 140), (130, 142)], '#4a2e20'); s.rect(132, 120, 3, 14, '#3a2418'); s.rect(158, 118, 3, 14, '#3a2418')

    def blanket(self, s):
        m = s.poly([(186, 124), (258, 120), (276, 152), (182, 158)], '#7a8ab8')
        s.fill(m & s.M_poly([(200, 124), (240, 122), (252, 152), (204, 156)]), '#8a9ac8')
        s.rect(186, 122, 72, 2, '#f0ece0'); s.outline(m, '#08080a')

    def frame(self, t=0.0, needles=0.1, pen_fn=None, lamp=1.0, smoke=0.0):
        s = self.st.from_snapshot(self.base)
        for i, (dx, dy) in enumerate(self.A['dials']):
            a = -2.4 + (0.6 + 1.6 * needles) * (0.6 + 0.4 * math.sin(t * (3 + i) * (0.5 + 2 * needles) + i))
            s.line(dx, dy, dx + 4.5 * math.cos(a), dy + 4.5 * math.sin(a), '#c8302a')
        ex, ey, ew, eh = self.A['eeg']
        if pen_fn is not None:
            for ch in range(4):
                base = ey + 4 + ch * 7
                prev = None
                for x in range(ex, ex + ew):
                    dy = pen_fn(t - (ex + ew - x) * 0.03, ch)
                    y = base + dy
                    if prev is not None: s.line(x - 1, prev, x, y, '#2a2a3a')
                    prev = y
        # lamp
        lx, ly = self.A['lamp']
        s.poly([(lx - 10, ly), (lx + 10, ly), (lx + 6, ly - 8), (lx - 6, ly - 8)], '#2f7a5a')
        s.poly([(lx - 10, ly), (lx + 10, ly), (lx + 9, ly - 2), (lx - 9, ly - 2)], '#4aa07a')
        s.rect(lx - 8, ly, 16, 1, '#fff2c0', lamp); s.rect(lx - 1, ly - 10, 2, 2, '#c8a040')
        s.rect(lx, ly - 8, 1, 18, '#c8a040'); s.rect(lx - 4, ly + 10, 9, 2, '#c8a040')
        if smoke > 0:
            for k in range(6):
                a = k * 1.3 + t * 2
                r = 3 + 8 * smoke + k
                s.ell(34 + r * 0.6 * math.cos(a), 80 - 10 * smoke - k * 3, 2 + k * 0.6, 2 + k * 0.6, '#1a1a1e')
        return s

    def light(self, s, lamp=1.0, room=1.0):
        L = s.light_base((0.55, 0.55, 0.72), 0.62 * room)
        lx, ly = self.A['lamp']
        L = L + s.cone((lx, ly - 2), (lx - 60, 180), (lx + 70, 180), (1.0, 0.86, 0.6), 0.28 * lamp)
        L = L + s.band(lx, ly + 22, 90, 48, (1.0, 0.85, 0.58), [(1.0, 0.2 * lamp), (0.62, 0.42 * lamp), (0.32, 0.7 * lamp)])
        L = L + s.band(222, 50, 30, 30, (0.5, 0.6, 1.0), [(1.0, 0.12), (0.5, 0.2)])
        return L

    def air(self, s, lamp=1.0):
        lx, ly = self.A['lamp']
        return s.cone((lx, ly), (lx - 40, 180), (lx + 46, 180), (1.0, 0.88, 0.62), 0.05 * lamp)
