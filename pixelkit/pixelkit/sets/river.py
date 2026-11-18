"""pixelkit.sets.river - riverbank at sunset (side-view diorama, 480x270 native, ACT IV).  Backlit: the low sun sits
over the far bank, its reflection makes a glittering gold column on the water, the near bank and the figures are
dark silhouettes with warm rim light.

    rv = River(dusk=0.0)              # dusk 0 = sun just above the far bank, 1 = sun gone, violet sky, town lights on
    bg = rv.bg                        # dict for outdoor.OutdoorScene (front = list of reed-sway variants)
    rv.front_index(t)                 # reed sway variant at time t
    rv.glitter(t)                     # (rgba, E, x, y) bg patch: animated sun glitter on the water (bg_patches)
    rv.ripple_rings(t, t0, x, y)      # pixel ripple rings around a point on the water (mid sprite list)
    RIVER_STATE                       # outdoor_state overrides for the backlit look

Layout (native px): sky 0..HORIZON (138) | far bank tree line + bridge (left) + town (right) | water 140..bank edge
(~214) | near grass bank down to 270.  Figures sit with their seat at SEAT_Y (~234).  Sun at SUN_X (332).
"""
import math, functools
import numpy as np, cv2
from ..core import Canvas, C, mix, BAYER4
from ..palette import ramp
from .. import materials as M
from ..outdoor import haze_map

W, H = 480, 270
HORIZON = 138
SUN_X = 332
SEAT_Y = 234
OUTL = C('#24182a')

RIVER_STATE = dict(sun_k=0.35, amb_k=0.72, haze_k=0.30, rim=0.0, facing=0.10, mid_amb=1.0, shadow_k=0.25,
                   shadow_sx=-0.2, shadow_sy=0.25, light_dither=0.0)

def _lerp(a, b, k): return np.asarray(a, np.float32) + (np.asarray(b, np.float32) - np.asarray(a, np.float32)) * k
def _hx(h): return np.array(C(h)[:3], np.float32)

SKY0 = [(0, '#46407e'), (48, '#94568c'), (96, '#ec8668'), (124, '#ffbe6c'), (138, '#ffe0a0')]
SKY1 = [(0, '#24264e'), (48, '#4c3a6e'), (96, '#a45478'), (124, '#da7a5e'), (138, '#ee9e6c')]

def sky_col(y, dusk):
    """(N,) y -> (N, 3) sky colour for a dusk level."""
    y = np.asarray(y, np.float32)
    out = []
    for stops in (SKY0, SKY1):
        ys = np.array([s[0] for s in stops], np.float32); cs = np.stack([_hx(s[1]) for s in stops])
        out.append(np.stack([np.interp(y, ys, cs[:, i]) for i in range(3)], -1))
    return out[0] + (out[1] - out[0]) * dusk


class River:
    SWAY_PERIOD = 4.2

    def __init__(self, dusk=0.0, seed=0, sway_frames=12):
        self.W, self.H, self.dusk, self.seed = W, H, float(dusk), seed
        self.cv = Canvas(W, H)
        self.E = np.zeros((H, W), np.float32)
        self.T = np.ones((H, W), np.float32) * 0.15
        self.ao = np.ones((H, W), np.float32)
        self.rng = np.random.default_rng(seed + 77)
        self.yy, self.xx = np.mgrid[0:H, 0:W]
        self.sun_y = 121 + 26 * self.dusk
        self.sky(); self.far_bank(); self.water(); self.near_bank(); self.props()
        self.fronts = self.build_fronts(sway_frames)
        self.ground = np.full(W, 0.12, np.float32)
        self.bg = dict(rgba=self.cv.a, E=self.E, T=self.T, ao=self.ao, ground=self.ground,
                       haze=haze_map(W, H, 2, sun_xy=(SUN_X, self.sun_y), rays=9, ray_k=0.35 * (1 - self.dusk),
                                     glow_k=0.9 * (1 - 0.6 * self.dusk), glow_r=120.0, horizon=HORIZON, horizon_k=0.25,
                                     angle_spread=1.4),
                       front=self.fronts, frontE=np.zeros((H, W), np.float32))

    # ---------------------------------------------------------------- helpers
    def dither(self, col, step=8.0, y=None, x=None):
        yy, xx = (self.yy, self.xx) if y is None else (y, x)
        th = BAYER4[yy % 4, xx % 4]
        return np.clip(np.floor(col / step + th[..., None]) * step, 0, 255)

    def front_index(self, t, period=None):
        n = len(self.fronts); p = period or self.SWAY_PERIOD
        return int(math.floor((t % p) / p * n)) % n

    # ---------------------------------------------------------------- sky
    def sky(self):
        yy, xx = self.yy, self.xx
        col = sky_col(yy.ravel(), self.dusk).reshape(H, W, 3)
        d = np.sqrt((xx - SUN_X) ** 2 + ((yy - self.sun_y) * 1.6) ** 2)
        warm = np.exp(-d / 90.0)[..., None] * _lerp([60, 34, -10], [30, 6, -6], self.dusk)
        col = col + warm
        u, v = xx.astype(np.float64), yy.astype(np.float64)
        n = M.fbm(u * 0.22, v * 1.6, 40.0, 4, self.seed + 3)
        band = np.exp(-((yy - 62) / 9.0) ** 2) + 0.9 * np.exp(-((yy - 88) / 6.0) ** 2) + 0.7 * np.exp(-((yy - 108) / 4.0) ** 2)
        cl = n * band
        cloud = cl > 0.40
        under = cloud & ~(np.roll(cl, 2, 0) > 0.40)                  # lower edge lit by the sun below
        top_c = _lerp(_hx('#a0608e'), _hx('#563e70'), self.dusk); lit_c = _lerp(_hx('#ffc888'), _hx('#e8806a'), self.dusk)
        col[cloud] = col[cloud] * 0.35 + top_c * 0.65
        col[under] = lit_c
        col = self.dither(col, 7.0)
        self.cv.a[..., :3] = col.astype(np.uint8); self.cv.a[..., 3] = 255
        self.E[:] = 1.0
        # the sun disc (clipped by the far bank later)
        if self.sun_y < HORIZON + 12:
            disc = (xx - SUN_X) ** 2 + (yy - self.sun_y) ** 2 <= 11.5 ** 2
            rim = disc & ((xx - SUN_X) ** 2 + (yy - self.sun_y) ** 2 > 9.5 ** 2)
            self.cv.a[disc] = C('#fff2c8'); self.cv.a[rim] = C('#ffd890')
            for k in range(3):                                         # thin cloud strands across the disc
                yb = int(self.sun_y) - 3 + k * 4
                m = disc & (yy == yb) & (((xx * 7 + k * 5) % 11) < 8)
                self.cv.a[m] = C('#ffc070')
        if self.dusk > 0.5:                                            # first star
            self.cv.a[34, 118] = C('#fff6e0'); self.cv.a[33, 118] = C('#c8b8d8'); self.cv.a[35, 118] = C('#c8b8d8')

    # ---------------------------------------------------------------- far bank: trees, bridge, town
    def far_bank(self):
        yy, xx = self.yy, self.xx
        x = np.arange(W, dtype=np.float64)
        top = 131 - 6 * M.fbm(x, np.zeros_like(x), 18.0, 3, self.seed + 5) - 3 * M.fbm(x, np.ones_like(x) * 9, 5.0, 2, self.seed + 6)
        for px_, h_ in ((214, 13), (226, 10), (420, 12), (60, 9)):       # poplars
            top = np.minimum(top, 131 - h_ * np.exp(-((x - px_) / 3.2) ** 2) - 2)
        top = np.round(top).astype(int)
        tree = (yy >= top[None, :]) & (yy <= HORIZON + 1)
        haze = np.exp(-np.abs(xx - SUN_X) / 70.0) * (1 - 0.5 * self.dusk)
        base = _lerp(_hx('#4c3462'), _hx('#2e2444'), self.dusk)
        hz = _lerp(_hx('#c2707c'), _hx('#7a4a6e'), self.dusk)
        col = base[None, None] + (hz - base)[None, None] * haze[..., None] * 0.75
        ntex = M.fbm(xx * 1.0, yy * 1.0, 3.0, 2, self.seed + 8)
        col = col * (0.9 + 0.18 * ntex[..., None])
        edge = tree & ~np.roll(tree, 1, 0)
        a = self.cv.a
        a[..., :3][tree] = self.dither(col)[tree].astype(np.uint8)
        rimc = _lerp(_hx('#ffb078'), _hx('#c06a6a'), self.dusk)
        lit_edge = edge & (np.abs(xx - SUN_X) < 110)
        a[..., :3][lit_edge] = (rimc * 0.6 + col[lit_edge] * 0.4).astype(np.uint8)
        self.E[tree] = 0.30 + 0.35 * haze[tree]; self.E[lit_edge] = 0.8
        self.T[tree] = 0.0
        # iron bridge on the left (deck 112..116, piers, arches, railing)
        bc = _lerp(_hx('#3a2a4e'), _hx('#262036'), self.dusk); bci = tuple(int(v) for v in bc) + (255,)
        cv = self.cv
        cv.rect(0, 112, 170, 4, bci); cv.rect(0, 109, 170, 1, bci)
        for xr in range(0, 170, 4): cv.rect(xr, 109, 1, 3, bci)
        for p in (8, 62, 116, 168):
            cv.rect(p - 2, 116, 5, HORIZON - 116 + 1, bci)
        for p0, p1 in ((8, 62), (62, 116), (116, 168)):
            for xi in range(p0, p1 + 1):
                u = (xi - p0) / (p1 - p0)
                yv = 131 - int(round(13 * (1 - (2 * u - 1) ** 2)))     # arch soffit
                cv.px(xi, yv, bci); cv.px(xi, yv + 1, bci)
        a[116:118, 0:170, :3] = np.clip(a[116:118, 0:170, :3].astype(np.int16) - 10, 0, 255).astype(np.uint8)
        self.E[108:HORIZON + 1, 0:172][np.all(a[108:HORIZON + 1, 0:172, :3] == np.array(bci[:3], np.uint8), -1)] = 0.18
        cv.rect(0, 108, 170, 1, tuple(int(v) for v in rimc * 0.55 + bc * 0.45) + (255,))   # lit top rail
        self.E[108, 0:170] = 0.5
        # little town on the right bank: roofs + windows
        rng = np.random.default_rng(self.seed + 31)
        xh = 372
        while xh < W:
            w_ = int(rng.integers(12, 22)); h_ = int(rng.integers(8, 15)); y0 = HORIZON - h_
            hc = tuple(int(v) for v in base * (0.85 + 0.1 * rng.random())) + (255,)
            cv.rect(xh, y0, w_, h_ + 1, hc)
            for k in range(w_ // 2 + 1):                                 # pitched roof
                cv.rect(xh + k, y0 - min(k, w_ - k) // 2, 1, min(k, w_ - k) // 2 + 1, hc)
            for wx in range(xh + 2, xh + w_ - 2, 5):
                if rng.random() < 0.35 + 0.5 * self.dusk:
                    cv.rect(wx, y0 + 3, 2, 2, C('#ffd88a')); self.E[y0 + 3:y0 + 5, wx:wx + 2] = 0.9
            xh += w_ + int(rng.integers(1, 5))

    # ---------------------------------------------------------------- water
    def water(self):
        self.bank_y = self._bank_edge()
        yy, xx = self.yy, self.xx
        wm = (yy > HORIZON) & (yy < self.bank_y[None, :] + 2)
        self.water_mask = wm
        dy = np.clip(yy - HORIZON, 0, None).astype(np.float32)
        ym = np.clip(HORIZON - dy * 1.5, 0, HORIZON)
        col = sky_col(ym.ravel(), self.dusk).reshape(H, W, 3) * 0.78 + _hx('#20203a') * 0.22
        u, v = xx.astype(np.float64), yy.astype(np.float64)
        persp = 0.25 + dy / 80.0
        n = M.value_noise(u / (2.0 + 6 * persp), v * 1.0, 1.0, self.seed + 11)
        light = (n > 0.72) & wm; dark = (n < 0.22) & wm
        col[light] = col[light] * 1.12 + 8; col[dark] = col[dark] * 0.82
        # reflection of the far bank: dark band just under the horizon with a wavy lower edge
        rb = (dy >= 0) & (dy < 6 + 2 * np.sin(xx / 7.0 + yy) + 3 * M.fbm(u, v, 6.0, 2, self.seed + 12))
        col[rb & wm] = col[rb & wm] * 0.55 + _hx('#3a2a50') * 0.45
        # sun column
        prof, col_k = self._column(dy, xx)
        dash = M.value_noise(u / (1.5 + 5 * persp), v, 1.0, self.seed + 13)
        sunlit = wm & (dash > 1.0 - prof * 0.85)
        gold = _lerp(_hx('#ffe6a8'), _hx('#ffb07a'), self.dusk)
        col[wm] = col[wm] + (gold - col[wm]) * (prof[wm, None] * 0.35)
        col[sunlit] = gold * (0.85 + 0.15 * prof[sunlit, None])
        col = self.dither(col, 7.0)
        a = self.cv.a
        a[..., :3][wm] = col[wm].astype(np.uint8)
        self.E[wm] = 0.62 + 0.3 * prof[wm]
        self.E[sunlit] = 1.0
        self.T[wm] = 0.2

    def _column(self, dy, xx):
        hw = 5 + dy * 0.42
        prof = np.clip(1 - np.abs(xx - SUN_X) / np.maximum(hw, 1), 0, 1) ** 1.3
        prof = prof * np.clip(1.0 - dy / 110.0, 0.25, 1) * (1 - 0.55 * self.dusk)
        return prof, hw

    def _bank_edge(self):
        x = np.arange(W, dtype=np.float64)
        y = 216 + 3 * np.sin(x / 31.0) + 2.5 * M.fbm(x, np.zeros_like(x), 12.0, 2, self.seed + 21) - 9 * np.exp(-(x / 70.0) ** 2) \
            - 6 * np.exp(-((W - x) / 60.0) ** 2)
        return np.round(y).astype(int)

    # ---------------------------------------------------------------- near bank (backlit grass slope)
    def near_bank(self):
        yy, xx = self.yy, self.xx
        top = self.bank_y
        m = yy >= top[None, :]
        u, v = xx.astype(np.float64), yy.astype(np.float64)
        dyb = (yy - top[None, :]).astype(np.float32)
        c0 = _lerp(_hx('#5a5038'), _hx('#36302e'), self.dusk); c1 = _lerp(_hx('#3a2e40'), _hx('#221c2c'), self.dusk)
        k = np.clip(dyb / 50.0, 0, 1)[..., None]
        col = c0 + (c1 - c0) * k
        n = M.fbm(u * 1.0, v * 2.2, 5.0, 2, self.seed + 22)
        col = col * (0.86 + 0.28 * n[..., None])
        tuft = (M.value_noise(u, v * 0.35, 1.0, self.seed + 23) > 0.86) & (dyb > 3)
        col[tuft] = col[tuft] * 0.75
        col = self.dither(col, 6.0)
        a = self.cv.a
        a[..., :3][m] = col[m].astype(np.uint8)
        self.E[m] = 0.0; self.T[m] = 0.12
        # grass blades on the edge, rim-lit by the sun
        rim = _lerp(_hx('#ffb46a'), _hx('#d4785e'), self.dusk)
        rng = np.random.default_rng(self.seed + 24)
        for x in range(W):
            n_bl = 1 if rng.random() < 0.55 else 0
            for _ in range(n_bl):
                h_ = int(rng.integers(1, 5)); y0 = top[x] - h_
                dc = tuple(int(v) for v in c0 * 0.9) + (255,)
                self.cv.rect(x, y0, 1, h_ + 1, dc)
                near = math.exp(-abs(x - SUN_X) / 160.0)
                self.cv.px(x, y0, tuple(int(v) for v in (rim * near + c0 * (1 - near))) + (255,))
                self.E[y0, x] = 0.55 * near
            # wet edge line at the waterline
            self.cv.px(x, top[x] + 1, tuple(int(v) for v in c1 * 0.8) + (255,))
        # stones at the waterline
        for sx in (150, 171, 308, 352, 365):
            sy = top[sx] + 1
            self.cv.ellipse(sx, sy, 4, 2, C('#4a3e52')); self.cv.rect(sx - 3, sy - 2, 6, 1, C('#b0806a'))
            self.E[sy - 2, sx - 3:sx + 3] = 0.45

    # ---------------------------------------------------------------- props baked into the set: bucket, tackle box
    def props(self):
        cv = self.cv
        bx, by = 228, SEAT_Y                       # empty bucket (galvanised, backlit)
        for j in range(11):
            w_ = 10 + j // 4
            cv.rect(bx - w_ // 2, by - 11 + j, w_, 1, C('#5a6474') if j % 3 else C('#4a5262'))
        cv.rect(bx - 6, by - 12, 13, 1, C('#d8b090')); self.E[by - 12, bx - 6:bx + 7] = 0.6          # lit rim
        cv.rect(bx + 5, by - 11, 1, 10, C('#c89a7a')); self.E[by - 11:by - 1, bx + 5] = 0.35          # sun-side edge
        for i in range(9):                                                                           # handle
            ang = math.pi * i / 8
            cv.px(int(round(bx + 6 * math.cos(ang))), int(round(by - 12 - 4 * math.sin(ang))), C('#7a7f8a'))
        cv.ellipse(bx, by, 7, 1, C('#141018'))
        tx, ty = 162, SEAT_Y + 4                   # tackle box on the old man's left
        cv.rect(tx, ty - 6, 14, 6, C('#5a3a3a')); cv.rect(tx, ty - 7, 14, 1, C('#c88a6a')); cv.rect(tx + 5, ty - 9, 4, 2, C('#3a2a2a'))
        self.E[ty - 7, tx:tx + 14] = 0.4
        cv.ellipse(tx + 7, ty, 8, 1, C('#141018'))

    # ---------------------------------------------------------------- reeds (front layer, sway variants)
    def build_fronts(self, n):
        rng = np.random.default_rng(self.seed + 41)
        stalks = []
        for (x0, x1, cnt, side) in ((0, 64, 15, 1), (430, 480, 12, -1)):
            for i in range(cnt):
                x = float(rng.uniform(x0, x1)); top = float(rng.uniform(96, 175)) if x0 == 0 else float(rng.uniform(110, 185))
                stalks.append(dict(x=x, top=top, lean=float(rng.uniform(-0.12, 0.12)) + 0.08 * side, ph=float(rng.uniform(0, 6.28)),
                                   cat=rng.random() < 0.35, side=side, leaves=int(rng.integers(1, 3)), seed=int(rng.integers(1e6))))
        rim = _lerp(_hx('#ffa860'), _hx('#c8705e'), self.dusk)
        dark = _lerp(_hx('#2a1e2c'), _hx('#1a1420'), self.dusk); mid_ = _lerp(_hx('#3c2c34'), _hx('#261c28'), self.dusk)
        out = []
        for f in range(n):
            ph = 2 * math.pi * f / n
            cv = Canvas(W, H)
            for s in stalks:
                L = H - s['top']
                sway = 2.2 * math.sin(ph + s['ph'])
                pts = []
                for k in range(int(L) + 1):
                    u = k / L
                    pts.append((s['x'] + s['lean'] * k + sway * u * u, H - k))
                col_d = tuple(int(v) for v in dark) + (255,); col_m = tuple(int(v) for v in mid_) + (255,)
                for (px_, py_) in pts:
                    cv.px(int(round(px_)), int(round(py_)), col_d)
                    if s['side'] > 0 and py_ < 200: cv.px(int(round(px_)) + 1, int(round(py_)), tuple(int(v) for v in (rim * 0.7 + mid_ * 0.3)) + (255,))
                    if s['side'] < 0 and py_ < 200: cv.px(int(round(px_)) - 1, int(round(py_)), tuple(int(v) for v in (rim * 0.7 + mid_ * 0.3)) + (255,))
                r2 = np.random.default_rng(s['seed'])
                for li in range(s['leaves']):                                # long curved blades
                    k0 = int(r2.uniform(0.1, 0.5) * L); dirn = 1 if r2.random() < 0.5 else -1
                    bx_, by_ = pts[k0]; ln = r2.uniform(18, 34)
                    for k in range(int(ln)):
                        u = k / ln
                        x_ = bx_ + dirn * (k * 0.55) + sway * 0.6 * u
                        y_ = by_ - k * (1.0 - 0.9 * u * u)
                        cv.px(int(round(x_)), int(round(y_)), col_m)
                if s['cat']:                                                 # cattail head
                    tx, ty = pts[-1]
                    tx, ty = int(round(tx)), int(round(ty))
                    cv.rect(tx - 1, ty + 2, 3, 8, C('#4a2e26')); cv.px(tx, ty, col_d); cv.px(tx, ty + 1, col_d)
                    rx = tx + 1 if s['side'] > 0 else tx - 1
                    cv.rect(rx, ty + 3, 1, 6, tuple(int(v) for v in (rim * 0.8 + _hx('#4a2e26') * 0.2)) + (255,))
            out.append(cv.a.copy())
        return out

    # ---------------------------------------------------------------- dynamic water pieces
    def glitter(self, t, x0=290, x1=376):
        """animated sun glitter on the water: (rgba, E, x0, y0) for OutdoorScene bg_patches."""
        y0, y1 = HORIZON + 1, int(self.bank_y[x0:x1].min()) - 1
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dy = (yy - HORIZON).astype(np.float32)
        prof, _ = self._column(dy, xx)
        persp = 0.25 + dy / 80.0
        drift = t * (1.2 + 2.0 * persp)
        n = M.value_noise((xx + drift * 3) / (1.2 + 4 * persp), yy * 1.0 + np.floor(t * 6) * 0.37, 1.0, self.seed + 51)
        on = (n > 1.0 - prof * 0.55) & (prof > 0.05)
        rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        rgba[on] = C('#fff6d8')
        E = np.zeros(rgba.shape[:2], np.float32); E[on] = 1.0
        return rgba, E, x0, y0

    def ripple_rings(self, t, t0, cx, cy, n=3, speed=16.0, gap=0.45, life=2.6):
        """pixel ripple rings (flattened ellipses) around (cx, cy): list of (x, y, alpha 0..1)."""
        pts = []
        for i in range(n):
            age = t - t0 - i * gap
            if age <= 0 or age > life: continue
            r = 2 + age * speed * (1 - 0.15 * i)
            a = (1 - age / life) ** 1.4
            m = max(8, int(r * 2.2))
            for k in range(m):
                ang = 2 * math.pi * k / m
                x = cx + r * math.cos(ang); y = cy + 0.32 * r * math.sin(ang)
                if self.water_mask[int(min(max(y, 0), H - 1)), int(min(max(x, 0), W - 1))]:
                    pts.append((int(round(x)), int(round(y)), a))
        return pts
