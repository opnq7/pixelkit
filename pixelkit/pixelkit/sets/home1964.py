"""pixelkit.sets.home1964 - 60 年代美国家里的书房 / 卧室（320x180 一点透视，v0.13《熬夜副本》第 3 关）。

木墙板 + 橙色落地灯（暖主光）、显像管电视（彩条发光）、单人床、科学展三折展板「不睡觉大挑战」、
墙上撕页日历（大号「第 N 天」可翻）、小黑板（减 7 算式用）、地毯。
    h = Home1964()
    fr = h.frame(t, day=1, board_lines=['100', '93'], tv=1.0, warp=0.0)
    L = h.light(fr, lamp=1.0, tv=1.0)
锚点 A：lamp, tv, bed（床面中心）, stand（人物脚底）, cal（日历 x, y, w, h）, board（黑板 x, y, w, h）, trifold
"""
import math
import numpy as np
from ..pixstage import Stage
from ..core import text_width
from .. import post

GRADE_RETRO = dict(post.GRADES['golden_hd2d'])
GRADE_RETRO.update(grain=0.016, vignette=0.42, sat=1.1, contrast=1.12, black=0.025,
                   bloom=dict(thr=0.74, knee=0.22, strength=0.55, tint=(1.0, 0.84, 0.62), halation=0.22))

class Home1964:
    W, H = 320, 180
    BW = (62, 20, 258, 118)

    def __init__(self):
        self.A = dict(lamp=(84, 70), tv=(236, 96), bed=(214, 140), stand=(150, 156), cal=(174, 34, 28, 34),
                      board=(96, 36, 64, 40), trifold=(108, 110))
        self.st = Stage(self.W, self.H); self._paint(self.st); self.base = self.st.snapshot()

    def _paint(self, s):
        W, H = self.W, self.H; x0, y0, x1, y1 = self.BW; yy = s.yy
        s.rect(0, 0, W, H, '#140c0a')
        s.poly([(0, 0), (W, 0), (x1, y0), (x0, y0)], '#1c1410')
        lw = s.poly([(0, 0), (x0, y0), (x0, y1), (0, H)], '#3a2418')
        rw = s.poly([(W, 0), (x1, y0), (x1, y1), (W, H)], '#32200f' if False else '#34200f')
        s.rect(x0, y0, x1 - x0, y1 - y0, '#4a2e1c')
        for x in range(x0 + 4, x1, 9): s.rect(x, y0, 1, y1 - y0, '#3e2616')         # wood paneling grooves
        for k in range(8):
            s.line(x0 * k / 8, y0 * k / 8 + 0, x0 * k / 8, H - (H - y1) * k / 8, '#30200f', mask=lw)
        s.rect(x0, 98, x1 - x0, 2, '#6a4428')
        fl = s.poly([(0, H), (x0, y1), (x1, y1), (W, H)], '#5a3a2a')
        rug = s.poly([(70, 176), (250, 176), (226, 124), (94, 124)], '#7a3a2a')
        s.fill(rug & s.M_poly([(80, 170), (240, 170), (220, 128), (100, 128)]), '#8a4a30')
        for k in range(6): s.line(94 + k * 26, 124, 70 + k * 36, 176, '#6a3020', mask=rug)
        # floor lamp (left)
        lx, ly = self.A['lamp']
        s.rect(lx - 1, ly, 2, 70, '#c8a050'); s.rect(lx - 6, ly + 68, 12, 3, '#8a6a30')
        s.poly([(lx - 12, ly), (lx + 12, ly), (lx + 7, ly - 14), (lx - 7, ly - 14)], '#e8a050')
        s.poly([(lx - 12, ly), (lx + 12, ly), (lx + 11, ly - 2), (lx - 11, ly - 2)], '#ffd090', 0.5)
        # TV (right, boxy) with cabinet
        tx, ty = self.A['tv']
        cab = s.rect(tx - 22, ty - 6, 44, 38, '#6a4428'); s.outline(cab, '#120a06')
        s.rect(tx - 18, ty - 2, 30, 22, '#1a1a1a')
        for k in range(3): s.rect(tx + 14, ty + 2 + k * 6, 4, 3, '#c8a050')
        s.rect(tx - 20, ty + 32, 3, 6, '#3a2418'); s.rect(tx + 17, ty + 32, 3, 6, '#3a2418')
        s.line(tx - 6, ty - 6, tx - 14, ty - 20, '#a8a8b0'); s.line(tx + 2, ty - 6, tx + 10, ty - 22, '#a8a8b0')
        # bed (back right corner)
        bf = s.poly([(176, 122), (252, 118), (266, 160), (170, 166)], '#5a3a6a'); s.outline(bf, '#0a0610')
        s.poly([(176, 118), (252, 114), (252, 122), (176, 126)], '#e8e0e8')
        s.ell(236, 118, 14, 5, '#f4f0f4')
        s.fill(bf & s.M_poly([(176, 126), (252, 122), (262, 156), (172, 160)]) & ((s.xx // 8 + s.yy // 8) % 2 == 0), '#6a4a7a')
        # calendar (big tear-off)
        cx, cy, cw, ch = self.A['cal']
        s.rect(cx, cy, cw, ch, '#f2ece0'); s.rect(cx, cy, cw, 8, '#c8302a'); s.outline(s.M_rect(cx, cy, cw, ch), '#1a0a06')
        # blackboard
        bx, by, bw, bh = self.A['board']
        s.rect(bx - 3, by - 3, bw + 6, bh + 6, '#8a6a40'); s.rect(bx, by, bw, bh, '#1e3a2e')
        s.rect(bx + 4, by + bh - 2, 12, 2, '#e8e4dc')
        # science-fair trifold on a stand
        fx, fy = self.A['trifold']
        s.poly([(fx - 30, fy - 30), (fx - 18, fy - 34), (fx - 18, fy + 6), (fx - 30, fy + 8)], '#e8d8a0')
        s.rect(fx - 18, fy - 34, 36, 40, '#f4e8b8')
        s.poly([(fx + 18, fy - 34), (fx + 30, fy - 30), (fx + 30, fy + 8), (fx + 18, fy + 6)], '#e8d8a0')
        s.outline(s.M_poly([(fx - 30, fy - 30), (fx - 18, fy - 34), (fx + 18, fy - 34), (fx + 30, fy - 30), (fx + 30, fy + 8), (fx - 30, fy + 8)]), '#2a1a0a')
        s.text(fx - 16, fy - 31, '不睡觉', '#c8302a', 'zh10'); s.text(fx - 16, fy - 19, '大挑战', '#2a4a8a', 'zh10')
        s.rect(fx - 14, fy - 6, 10, 8, '#8ac8e8'); s.rect(fx + 2, fy - 6, 12, 8, '#e8a0a0')
        s.rect(fx - 2, fy + 8, 3, 24, '#3a2418')

    def frame(self, t=0.0, day=None, board_lines=(), tv=1.0, warp=0.0, board_q=0.0):
        s = self.st.from_snapshot(self.base)
        tx, ty = self.A['tv']
        if tv > 0:
            bars = ['#e8e8e8', '#e8e030', '#30e0e8', '#30e030', '#e030e0', '#e03030', '#3030e8']
            for i, c in enumerate(bars): s.rect(tx - 18 + i * 30 / 7, ty - 2, 30 / 7 + 1, 15, c, 0.8 * tv)
            s.rect(tx - 18, ty + 13, 30, 7, '#1a1a40', 0.5 * tv)
            if int(t * 9) % 4 == 0: s.rect(tx - 18, ty - 2 + int(t * 37) % 20, 30, 1, '#ffffff', 0.6 * tv)
        if day is not None:
            cx, cy, cw, ch = self.A['cal']
            s.rect(cx + 2, cy + 10, cw - 4, ch - 12, '#f2ece0')
            sd = str(day); tw = text_width(sd, 'p2p')
            s.text(cx + cw // 2 - tw // 2, cy + 13, sd, '#1a1a1a', 'p2p')
            s.text(cx + 4, cy + 24, '第  天', '#5a4a3a', 'zh8')
        bx, by, bw, bh = self.A['board']
        for i, ln in enumerate(board_lines):
            s.text(bx + 4 + (i // 4) * 30, by + 3 + (i % 4) * 9, ln, '#e8e4dc', 'zh8')
        if warp > 0:      # hallucination: rows slide sideways in a sine
            img = s.img.copy(); E = s.E.copy()
            for y in range(self.H):
                dx = int(round(warp * 6 * math.sin(y * 0.12 + t * 5)))
                s.img[y] = np.roll(img[y], dx, 0); s.E[y] = np.roll(E[y], dx, 0)
        return s

    def light(self, s, lamp=1.0, tv=1.0, room=1.0):
        lx, ly = self.A['lamp']; tx, ty = self.A['tv']
        L = s.light_base((0.55, 0.5, 0.7), 0.6 * room)
        L = L + s.band(lx, ly + 30, 120, 90, (1.0, 0.72, 0.42), [(1.0, 0.22 * lamp), (0.62, 0.42 * lamp), (0.32, 0.7 * lamp)])
        L = L + s.band(tx, ty + 20, 60, 40, (0.6, 0.8, 1.0), [(1.0, 0.15 * tv), (0.5, 0.3 * tv)])
        return L

    def air(self, s, lamp=1.0):
        lx, ly = self.A['lamp']
        return s.cone((lx, ly - 2), (lx - 44, 180), (lx + 50, 180), (1.0, 0.8, 0.5), 0.04 * lamp)
