"""pixelkit.sets.hub_doors - 关卡大厅：黑暗空间里一排带年份牌的门 + 硬边追光（v0.13《熬夜副本》）。

    hub = HubDoors(years=('1938', '1953', '1964', '2003', '1971'))
    fr = hub.frame(t, states=[...]*5, appear=[0..1]*5, open_k=[0..1]*5, circle_k=1.0)
    L  = hub.light(fr, states, appear, open_k)
    img = fr.render(cam, L, GRADE_NIGHT, ...)
state: 'hidden' | 'locked'（暗、金框暗）| 'active'（下一关：边缘漏光、追光、年份牌发亮）| 'cleared'（绿勾、门半开）
hub.D[i] = dict(x, yb, w, h) 每扇门（x 中心、yb 门底）；hub.door_center(i) -> (x, y)。
"""
import math
import numpy as np
from ..pixstage import Stage

YEARS = ('1938', '1953', '1964', '2003', '1971')

class HubDoors:
    W, H = 320, 180
    VX, VY = 160, 58

    def __init__(self, years=YEARS):
        self.years = years
        # an arc of doors: centre biggest/closest, outer smaller/further
        xs = (44, 100, 160, 220, 276); sc = (0.70, 0.86, 1.0, 0.86, 0.70)
        self.D = []
        for x, s in zip(xs, sc):
            w, h = int(round(30 * s)), int(round(52 * s))
            yb = int(round(120 + 18 * (s - 0.7) / 0.3))
            self.D.append(dict(x=x, yb=yb, w=w, h=h, s=s))
        self.st = Stage(self.W, self.H)
        self._paint(self.st)
        self.base = self.st.snapshot()

    def door_center(self, i):
        d = self.D[i]; return (d['x'], d['yb'] - d['h'] * 0.5)

    def _paint(self, s):
        W, H = self.W, self.H; yy, xx = s.yy, s.xx
        s.rect(0, 0, W, H, '#06060c')
        # far haze band + faint stars (void)
        s.rect(0, 70, W, 40, '#0a0a16')
        rng = np.random.default_rng(9)
        for i in range(40):
            s.px(int(rng.integers(0, W)), int(rng.integers(0, 70)), ['#3a3a5a', '#5a5a80', '#8a88b0'][i % 3], 0.6)
        # floor: perspective stone tiles
        fl = s.poly([(0, H), (0, 112), (W, 112), (W, H)], '#100e18')
        for k in range(-10, 11):
            xb = 160 + k * 46
            s.line(160 + k * 12, 112, xb, H, '#0a0912', mask=fl)
        for yb in (116, 122, 131, 144, 162):
            s.fill(fl & (yy == yb), '#0b0a13')
        # summoning circle (gold inlay) in front of the doors
        c1 = s.M_ell(160, 152, 70, 16) & ~s.M_ell(160, 152, 68, 15)
        c2 = s.M_ell(160, 152, 54, 12) & ~s.M_ell(160, 152, 53, 11)
        s.fill(c1, '#5a4220'); s.fill(c2, '#4a3418')
        for k in range(12):
            a = k / 12 * 2 * math.pi
            s.px(160 + 61 * math.cos(a), 152 + 13.5 * math.sin(a), '#8a6a2a')
        self.circle = (c1, c2)

    def _door(self, s, i, state, appear, open_k, t):
        if state == 'hidden' or appear <= 0: return
        d = self.D[i]; x, yb, w, h = d['x'], d['yb'], d['w'], d['h']
        # materialise: rises from the floor line with a scanline reveal
        hh = int(round(h * min(1.0, appear)))
        top = yb - hh
        x0 = int(round(x - w / 2))
        reveal = s.M_rect(x0 - 4, top - 14, w + 8, hh + 15)
        active = state == 'active'; cleared = state == 'cleared'; locked = state == 'locked'
        gold = '#f2c35a' if not locked else '#7a5a24'
        gold_d = '#c8902e' if not locked else '#4a3416'
        # frame (arched)
        r = w / 2
        arch_o = (s.M_rect(x0 - 3, yb - h + r, w + 6, h - r + 1) | s.M_ell(x, yb - h + r, r + 3, r + 3)) & (s.yy <= yb)
        arch_i = (s.M_rect(x0, yb - h + r, w, h - r) | s.M_ell(x, yb - h + r, r, r)) & (s.yy < yb)
        s.fill(arch_o & reveal, gold_d); s.fill((arch_o & ~s.M_ell(x, yb - h + r, r + 2, r + 2) & ~s.M_rect(x0 - 2, yb - h + r, w + 4, h)) & reveal, gold)
        s.fill(s.ring(arch_o) & reveal, '#050408')
        # opening: light behind the door (warm white), leaf swings open by open_k
        glow = '#fff2d0' if not locked else '#2a2430'
        s.fill(arch_i & reveal, glow, 1.0 if not locked else 0.0)
        leaf_w = w * (1 - 0.85 * open_k)
        leaf = arch_i & (s.xx < x0 + leaf_w) & reveal
        wood = '#5a2e22' if not locked else '#2a1814'
        s.fill(leaf, wood)
        s.fill(leaf & ((s.xx - x0) % 6 == 0), '#4a241a' if not locked else '#20120e')
        if leaf_w > 4:
            s.fill(leaf & (s.xx >= x0 + leaf_w - 1), '#3a1a12')
            kx = int(x0 + leaf_w - 4); ky = int(yb - h * 0.45)
            s.rect(kx, ky, 2, 2, gold)
        # light leaking around a closed active door
        if active and open_k < 0.05:
            s.fill(s.ring(arch_i) & arch_o & reveal, '#ffe9b0', 1.0)
            s.fill((s.yy == yb - 1) & (s.xx >= x0) & (s.xx < x0 + w), '#fff6d8', 1.0)
        # year plaque above the arch
        py = int(yb - h - 10)
        pw = 20
        s.rect(x - pw // 2, py, pw, 9, gold_d); s.rect(x - pw // 2 + 1, py + 1, pw - 2, 7, '#1a1020')
        from .bedroom320 import digits
        digits(s, x - 7, py + 2, self.years[i], '#ffd85a' if active else ('#8af0a0' if cleared else '#8a7a50'),
               1.0 if active else (0.8 if cleared else 0.0))
        if cleared:
            cx_, cy_ = x + w // 2 + 2, yb - h + 2
            s.ell(cx_, cy_, 4, 4, '#2a8a4a'); s.line(cx_ - 2, cy_, cx_ - 1, cy_ + 2, '#d8ffe0', 1.0); s.line(cx_ - 1, cy_ + 2, cx_ + 2, cy_ - 2, '#d8ffe0', 1.0)
        if locked:
            s.rect(x - 2, yb - h * 0.5, 4, 4, '#4a4458'); s.px(x, yb - h * 0.5 + 1, '#08060a')

    def frame(self, t=0.0, states=('active', 'locked', 'locked', 'locked', 'locked'), appear=(1,) * 5, open_k=(0,) * 5,
              circle_k=1.0):
        s = self.st.from_snapshot(self.base)
        if circle_k > 0:
            c1, c2 = self.circle
            k = circle_k * (0.7 + 0.3 * math.sin(t * 3))
            s.fill(c1, '#c8902e', 0.6 * k); s.fill(c2, '#a8781e', 0.4 * k)
        order = sorted(range(5), key=lambda i: self.D[i]['s'])          # far doors first
        for i in order: self._door(s, i, states[i], appear[i], open_k[i], t)
        return s

    def air(self, s, states, appear=(1,) * 5, open_k=(0,) * 5, k=1.0):
        """visible spotlight beams in the dark air (hard, two bands)."""
        A = np.zeros((self.H, self.W, 3), np.float32)
        for i, (st, a, o) in enumerate(zip(states, appear, open_k)):
            if st == 'hidden' or a <= 0: continue
            d = self.D[i]; x, yb, w = d['x'], d['yb'], d['w']
            kk = (0.10 if st == 'active' else (0.05 if st == 'cleared' else 0.025)) * min(1.0, a) * k
            col = (1.0, 0.86, 0.6) if st != 'cleared' else (0.6, 1.0, 0.75)
            A += s.cone((x, -10), (x - w * 0.95, yb + 6), (x + w * 0.95, yb + 6), col, kk)
        return A

    def light(self, s, states, appear=(1,) * 5, open_k=(0,) * 5, room_k=1.0):
        L = s.light_base((0.62, 0.62, 0.90), room_k)
        for i, (st, a, o) in enumerate(zip(states, appear, open_k)):
            if st == 'hidden' or a <= 0: continue
            d = self.D[i]; x, yb, w, h = d['x'], d['yb'], d['w'], d['h']
            k = (0.55 if st == 'active' else (0.30 if st == 'cleared' else 0.12)) * min(1.0, a)
            col = (1.0, 0.86, 0.6) if st != 'cleared' else (0.6, 1.0, 0.75)
            L = L + s.cone((x, -10), (x - w * 0.95, yb + 6), (x + w * 0.95, yb + 6), col, k)
            L = L + s.band(x, yb + 3, w * 0.9, 5, col, [(1.0, k * 0.8), (0.6, k * 1.4)])
            if o > 0:
                L = L + s.cone((x, yb - h * 0.5), (x - w * (1.2 + 2.5 * o), 182), (x + w * (1.2 + 2.5 * o), 182), (1.0, 0.92, 0.75), 0.5 * o)
        return L
