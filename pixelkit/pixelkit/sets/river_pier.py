"""pixelkit.sets.river_pier - the 'poster' riverbank at sunset: a weathered wooden pier running out into the river,
the two figures sitting at its end against the bright water (ACT IV hold frame / the oil-paint transition).

    rv = RiverPier(dusk=0.0)          # dusk 0 = sun a disc above the hills, 1 = half set, violet sky, lights on
    bg = rv.bg                        # dict for outdoor.OutdoorScene (front = reed sway variants)
    rv.front_index(t); rv.glitter(t); rv.birds(t); rv.ripple_rings(t, t0, x, y)
    RP_STATE                          # outdoor_state overrides (backlit)

Layout (native 480x270): sky 0..HORIZON (152, ~56 %) with layered clouds lit from below | far hills, poplars,
a little town + steeple (right) | water: mirrored sky + long sun column, a rowboat far left, lily pads lower left |
the pier: a perspective trapezoid from the bottom edge (x 138..358) to its end (x 196..300 at PIER_END 208),
planks, gaps, stringers, posts + their reflections | props on the deck: lantern, bucket, tackle box, thermos, rope |
front reeds in the two bottom corners (sway variants).
Seats: CLAUDE_SEAT (226, 216) on the deck, OLD_SEAT (272, 218) on a stool.  Bobber in the sun column at BOBBER.
"""
import math
import numpy as np, cv2
from ..core import Canvas, C, BAYER4
from .. import materials as M
from ..outdoor import haze_map

W, H = 480, 270
HORIZON = 152
SUN_X = 322
PIER_END = 208
VP = (248.0, float(HORIZON))
PIER_X_END = (196.0, 300.0)
CLAUDE_SEAT = (226, 216)
OLD_SEAT = (272, 218)
BOBBER = (338.0, 190.0)
LANTERN = (188, 227)

RP_STATE = dict(sun_k=0.35, amb_k=0.74, haze_k=0.30, rim=0.0, facing=0.10, mid_amb=1.0, shadow_k=0.25,
                shadow_sx=-0.2, shadow_sy=0.25, light_dither=0.0)

def _hx(h): return np.array(C(h)[:3], np.float32)
def _arr(a): return _hx(a) if isinstance(a, str) else np.asarray(a, np.float32)
def _lerp(a, b, k): a, b = _arr(a), _arr(b); return a + (b - a) * k
def _c(v): return tuple(int(max(0, min(255, x))) for x in v) + (255,)

SKY0 = [(0, '#2e3c74'), (26, '#4c4686'), (62, '#8c5290'), (98, '#d26e7c'), (124, '#f8986a'), (142, '#ffc47c'), (152, '#ffe2a4')]
SKY1 = [(0, '#181c40'), (26, '#2a2a5e'), (62, '#523a72'), (98, '#94507a'), (124, '#cc6e66'), (142, '#e89470'), (152, '#f2ac7a')]

def sky_col(y, dusk):
    y = np.asarray(y, np.float32); out = []
    for stops in (SKY0, SKY1):
        ys = np.array([s[0] for s in stops], np.float32); cs = np.stack([_hx(s[1]) for s in stops])
        out.append(np.stack([np.interp(y, ys, cs[:, i]) for i in range(3)], -1))
    return out[0] + (out[1] - out[0]) * dusk

def pier_x(y):
    """(left, right) x of the pier deck at screen row y (perspective toward VP)."""
    k = (y - VP[1]) / (PIER_END - VP[1])
    return VP[0] + (PIER_X_END[0] - VP[0]) * k, VP[0] + (PIER_X_END[1] - VP[0]) * k


class RiverPier:
    SWAY_PERIOD = 4.2

    def __init__(self, dusk=0.0, seed=0, sway_frames=12, sway_amp=2.0):
        self.sway_amp = float(sway_amp)                                # v0.11: reed sway (px at the tip)
        self.W, self.H, self.dusk, self.seed = W, H, float(dusk), seed
        self.cv = Canvas(W, H)
        self.E = np.zeros((H, W), np.float32)
        self.T = np.ones((H, W), np.float32) * 0.15
        self.ao = np.ones((H, W), np.float32)
        self.yy, self.xx = np.mgrid[0:H, 0:W]
        self.sun_y = 138 + 22 * self.dusk
        self.sky(); s0 = self.cv.a.copy(); self.far_bank(); s1 = self.cv.a.copy(); self.water()
        a0 = self.cv.a.copy(); self.boat(); self.lilies(); a1 = self.cv.a.copy(); self.pier(); a2 = self.cv.a.copy(); self.props()
        self.fronts = self.build_fronts(sway_frames)
        # small, readable things a painter would pick out with a fine brush (used by the painterly pass)
        ch = lambda a, b: np.abs(a.astype(np.int16) - b.astype(np.int16)).sum(-1) > 0
        town = cv2.dilate((ch(s0, s1) & (self.yy <= HORIZON + 1)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        posts = ch(a1, a2) & ~self.pier_mask
        fr = np.zeros((H, W), bool)
        for f_ in self.fronts: fr |= f_[..., 3] > 0
        self.detail_mask = ch(a0, a1) | ch(a2, self.cv.a) | town | posts | fr
        self.ground = np.full(W, 0.12, np.float32)
        self.bg = dict(rgba=self.cv.a, E=self.E, T=self.T, ao=self.ao, ground=self.ground,
                       haze=haze_map(W, H, 2, sun_xy=(SUN_X, self.sun_y), rays=9, ray_k=0.30 * (1 - self.dusk),
                                     glow_k=0.85 * (1 - 0.6 * self.dusk), glow_r=130.0, horizon=HORIZON, horizon_k=0.25,
                                     angle_spread=1.4),
                       front=self.fronts, frontE=np.zeros((H, W), np.float32))

    def dither(self, col, step=7.0, y=None, x=None):
        yy, xx = (self.yy, self.xx) if y is None else (y, x)
        th = BAYER4[yy % 4, xx % 4]
        return np.clip(np.floor(col / step + th[..., None]) * step, 0, 255)

    def front_index(self, t, period=None):
        n = len(self.fronts); p = period or self.SWAY_PERIOD
        return int(math.floor((t % p) / p * n)) % n

    # ================================================================ sky + clouds
    def sky(self):
        yy, xx = self.yy, self.xx
        col = sky_col(yy.ravel(), self.dusk).reshape(H, W, 3)
        col = col + (np.exp(-((xx - 40) ** 2 + yy ** 2) / (2 * 160.0 ** 2)) * np.clip(1 - yy / 60.0, 0, 1))[..., None] * \
            _lerp([-14, 8, 18], [-8, 4, 10], self.dusk)                                          # a cooler teal top-left
        d = np.sqrt((xx - SUN_X) ** 2 + ((yy - self.sun_y) * 1.5) ** 2)
        col = col + np.exp(-d / 85.0)[..., None] * _lerp([62, 38, -6], [34, 10, -4], self.dusk)
        u, v = xx.astype(np.float64), yy.astype(np.float64)
        # cloud envelopes: a big bank upper left, a bank right, thin strands above the sun, high cirrus
        env = (1.00 * np.exp(-((xx - 140) / 200.0) ** 2 - ((yy - 74) / 13.0) ** 2)
               + 0.95 * np.exp(-((xx - 420) / 120.0) ** 2 - ((yy - 52) / 10.0) ** 2)
               + 0.80 * np.exp(-((xx - 250) / 170.0) ** 2 - ((yy - 104) / 6.0) ** 2)
               + 0.75 * np.exp(-((xx - 330) / 120.0) ** 2 - ((yy - 126) / 3.0) ** 2)
               + 0.55 * np.exp(-((yy - 22) / 7.0) ** 2)
               + 0.85 * np.exp(-((xx - 40) / 90.0) ** 2 - ((yy - 112) / 8.0) ** 2))
        n = M.fbm(u * 0.30, v * 1.25, 34.0, 4, self.seed + 3)
        n2 = M.fbm(u * 0.9, v * 3.0, 9.0, 2, self.seed + 4)
        dens = np.clip((n * env + 0.16 * (n2 - 0.5) * env - 0.21) / 0.20, 0, 1)
        dens[yy > HORIZON - 4] = 0
        below = np.roll(dens, -2, 0); below[-2:] = 0
        under = np.clip(dens - below, 0, 1)                                    # lower edges (lit from the sun below)
        above = np.roll(dens, 2, 0); above[:2] = 0
        top = np.clip(dens - above, 0, 1)
        near = np.exp(-np.abs(xx - SUN_X) / 150.0)
        shade = _lerp(_lerp('#6c4a86', '#3c3466', self.dusk), _lerp('#5a3e7a', '#2e2a58', self.dusk), (yy < 60)[..., None] * 1.0)
        body = _lerp(_lerp('#b0648a', '#6a4274', self.dusk), _lerp('#ea8a78', '#b0606c', self.dusk), (near ** 1.5)[..., None])
        lit = _lerp(_lerp('#ff9a7c', '#d86c64', self.dusk), _lerp('#ffe0a0', '#ffac78', self.dusk), near[..., None])
        cc = shade + (body - shade) * np.clip(1 - top * 1.5, 0, 1)[..., None] * 0.0
        cc = _lerp(shade, body, np.clip(0.35 + 0.65 * (1 - dens) + 0.5 * under, 0, 1)[..., None])
        cc = _lerp(cc, lit, np.clip(under * 2.2, 0, 1)[..., None])
        a_ = np.clip(dens * 1.6, 0, 1)[..., None]
        col = col * (1 - a_) + cc * a_
        col = self.dither(col, 6.0)
        self.cv.a[..., :3] = col.astype(np.uint8); self.cv.a[..., 3] = 255
        self.E[:] = 1.0
        self.cloud = dens
        # sun disc (clipped by the hills later) + two cloud strands across it
        r2 = (xx - SUN_X) ** 2 + (yy - self.sun_y) ** 2
        disc = r2 <= 12.5 ** 2
        self.cv.a[disc] = C('#fff4d0'); self.cv.a[disc & (r2 > 10.5 ** 2)] = C('#ffdc96')
        m = disc & (yy == int(self.sun_y) + 3) & (np.abs(xx - SUN_X) < 9)
        self.cv.a[m] = C('#ffd08a')

    # ================================================================ far bank
    def far_bank(self):
        yy, xx = self.yy, self.xx
        x = np.arange(W, dtype=np.float64)
        a = self.cv.a
        hz_sun = np.exp(-np.abs(xx - SUN_X) / 90.0)
        # far hills (atmospheric, pinkish)
        top1 = np.round(HORIZON - 10 - 9 * M.fbm(x, np.zeros_like(x), 70.0, 3, self.seed + 5)
                        + 6 * np.exp(-((x - SUN_X) / 60.0) ** 2)).astype(int)
        m1 = (yy >= top1[None, :]) & (yy <= HORIZON)
        c1 = _lerp(_lerp('#b26a86', '#6c4470', self.dusk), _lerp('#f0a08a', '#b06672', self.dusk), (hz_sun * 0.9)[..., None])
        a[..., :3][m1] = self.dither(c1, 6.0)[m1].astype(np.uint8)
        self.E[m1] = 0.55 + 0.3 * hz_sun[m1]; self.T[m1] = 0.0
        # nearer tree line with poplars
        top2 = HORIZON - 3 - 3 * M.fbm(x, np.ones_like(x) * 3, 14.0, 3, self.seed + 6) - 2 * M.fbm(x, np.ones_like(x) * 9, 4.0, 2, self.seed + 7)
        for px_, h_ in ((22, 12), (30, 9), (176, 14), (186, 10), (232, 8), (452, 11)):
            top2 = np.minimum(top2, HORIZON - 3 - h_ * np.exp(-((x - px_) / 2.6) ** 2))
        top2 = np.round(top2).astype(int)
        m2 = (yy >= top2[None, :]) & (yy <= HORIZON + 1)
        base = _lerp('#55375e', '#2e2442', self.dusk); hz = _lerp('#c8707a', '#7a4a6e', self.dusk)
        col = base + (hz - base) * (hz_sun * 0.7)[..., None]
        col = col * (0.9 + 0.18 * M.fbm(xx * 1.0, yy * 1.0, 3.0, 2, self.seed + 8))[..., None]
        a[..., :3][m2] = self.dither(col)[m2].astype(np.uint8)
        edge = m2 & ~np.roll(m2, 1, 0)
        rimc = _lerp('#ffb078', '#c06a6a', self.dusk)
        le = edge & (np.abs(xx - SUN_X) < 120)
        a[..., :3][le] = (rimc * 0.6 + col[le] * 0.4).astype(np.uint8)
        self.E[m2] = 0.30 + 0.35 * hz_sun[m2]; self.E[le] = 0.8; self.T[m2] = 0.0
        # little town on the right: roofs, a steeple, windows lighting up
        cv = self.cv; rng = np.random.default_rng(self.seed + 31)
        hc0 = base * 0.92
        xh = 384
        while xh < W:
            w_ = int(rng.integers(10, 19)); h_ = int(rng.integers(6, 12)); y0 = HORIZON - h_
            hc = _c(hc0 * (0.9 + 0.1 * rng.random()))
            cv.rect(xh, y0, w_, h_ + 1, hc)
            for k in range(w_ // 2 + 1):
                cv.rect(xh + k, y0 - min(k, w_ - k) // 2, 1, min(k, w_ - k) // 2 + 1, hc)
            for wx in range(xh + 2, min(xh + w_ - 2, W - 1), 4):
                if rng.random() < 0.25 + 0.6 * self.dusk:
                    cv.rect(wx, y0 + 3, 1, 2, C('#ffd88a')); self.E[y0 + 3:y0 + 5, wx] = 0.9
            xh += w_ + int(rng.integers(1, 4))
        sx = 426                                                               # steeple
        cv.rect(sx - 3, HORIZON - 16, 7, 17, _c(hc0)); 
        for k in range(9): cv.rect(sx - 3 + k // 3, HORIZON - 16 - k, 7 - 2 * (k // 3), 1, _c(hc0))
        cv.rect(sx, HORIZON - 30, 1, 5, _c(hc0)); cv.rect(sx - 1, HORIZON - 28, 3, 1, _c(hc0))
        cv.rect(sx - 1, HORIZON - 12, 3, 3, C('#ffcf80') if self.dusk > 0.25 else _c(hc0 * 1.3))
        self.horizon_top = np.minimum(top1, top2)

    # ================================================================ water: mirrored sky + sun column
    def water(self):
        yy, xx = self.yy, self.xx
        wm = yy > HORIZON
        self.water_mask = wm
        dy = np.clip(yy - HORIZON, 0, None).astype(np.float32)
        persp = 0.2 + dy / 60.0
        rows = np.arange(H); pr_ = 0.2 + np.clip(rows - HORIZON, 0, None) / 60.0
        # per-row horizontal wobble (pixel-art water: whole strips shift)
        wob = np.round(2.2 * pr_ * np.sin(rows * 1.7 + 0.8 * np.sin(rows * 0.37)) + 1.4 * pr_ * np.sin(rows * 0.61)).astype(int)
        ym = np.clip(HORIZON - (dy * 0.95).astype(int) - 1, 0, HORIZON)
        xm = np.clip(xx + wob[:, None], 0, W - 1)
        src = self.cv.a[..., :3].astype(np.float32)
        refl = src[ym, xm]
        deep = _lerp('#3e2a5c', '#221a3c', self.dusk)
        k = np.clip(0.10 + dy / 190.0, 0, 0.55)[..., None]
        col = refl * (1 - k) * 0.90 + deep * k
        col = col + (_hx('#d07a9a') - col) * np.clip(dy / 260.0, 0, 0.18)[..., None]
        u, v = xx.astype(np.float64), yy.astype(np.float64)
        n = M.value_noise(u / (2.0 + 7 * persp), v * 1.0, 1.0, self.seed + 11)
        lightr = (n > 0.74) & wm; darkr = (n < 0.24) & wm
        col[lightr] = col[lightr] * 1.10 + 10; col[darkr] = col[darkr] * 0.80
        # sun column
        prof = self._column(dy, xx)
        dash = M.value_noise(u / (1.5 + 5 * persp), v, 1.0, self.seed + 13)
        sunlit = wm & (dash > 1.0 - prof * 0.85)
        gold = _lerp('#ffe6a8', '#ffb07a', self.dusk)
        col = col + (gold - col) * (prof * 0.35)[..., None]
        col[sunlit] = gold * (0.85 + 0.15 * prof[sunlit, None])
        col = self.dither(col, 6.0)
        a = self.cv.a
        a[..., :3][wm] = col[wm].astype(np.uint8)
        self.E[wm] = 0.58 + 0.32 * prof[wm]; self.E[sunlit] = 1.0
        self.T[wm] = 0.2

    def _column(self, dy, xx):
        hw = 5 + dy * 0.36
        prof = np.clip(1 - np.abs(xx - SUN_X) / np.maximum(hw, 1), 0, 1) ** 1.3
        return prof * np.clip(1.0 - dy / 120.0, 0.2, 1) * (1 - 0.5 * self.dusk)

    # ================================================================ rowboat far left, lily pads lower left
    def boat(self):
        cv = self.cv
        bx, by = 92, HORIZON + 7
        dk = _c(_lerp('#3a2a48', '#241c34', self.dusk)); rim = _c(_lerp('#f0a080', '#b0646a', self.dusk))
        for j in range(3): cv.rect(bx - 9 + j, by + j, 19 - 2 * j, 1, dk)
        cv.rect(bx - 10, by - 1, 21, 1, rim)
        cv.rect(bx + 1, by - 6, 3, 5, dk); cv.rect(bx + 1, by - 8, 3, 2, dk)          # seated figure
        cv.line(bx + 4, by - 5, bx + 13, by - 13, dk)                                 # rod
        for j in range(2): cv.rect(bx - 8 + j, by + 4 + j, 17 - 2 * j, 1, _c(_lerp('#6a4a6a', '#3a2c48', self.dusk)))   # reflection
        self.E[by - 8:by + 6, bx - 10:bx + 14] = 0.35

    def lilies(self):
        cv = self.cv; rng = np.random.default_rng(self.seed + 71)
        pad = _lerp('#3a4a40', '#26302e', self.dusk); pad_l = _lerp('#c88a70', '#9a5a5e', self.dusk)
        for (x, y, r) in ((40, 238, 12), (76, 252, 14), (20, 260, 11), (108, 242, 9), (96, 264, 12), (56, 225, 8), (122, 230, 6), (412, 252, 11), (440, 238, 8), (392, 262, 9)):
            ry = max(2, int(r * 0.36))
            cv.ellipse(x, y, r, ry, _c(pad))
            cv.rect(x - r + 2, y - ry, 2 * r - 4, 1, _c(pad_l))                       # sky-lit far rim
            cut = int(rng.integers(-r // 2, r // 2)); cv.line(x, y, x + cut, y + ry, _c(pad * 0.6))
            self.E[y - ry, x - r + 2:x + r - 2] = 0.5
        for (x, y) in ((44, 235), (74, 249), (424, 247)):                            # little pink flowers
            cv.rect(x - 1, y - 2, 3, 2, C('#f0a0b4')); cv.px(x, y - 3, C('#ffd2dc')); cv.px(x, y - 1, C('#ffe080'))
            self.E[y - 3:y, x - 1:x + 2] = 0.7

    # ================================================================ the pier
    def pier(self):
        cv, a = self.cv, self.cv.a
        dusk = self.dusk
        wood = _lerp('#8a6658', '#544050', dusk); wood_l = _lerp('#d09a84', '#946068', dusk)
        wood_d = _lerp('#3e2c38', '#261c2a', dusk); gap = _lerp('#1e1620', '#140e18', dusk)
        sheen = _lerp('#ffcc98', '#d8866e', dusk)
        # posts under the deck (into the water) + reflections, drawn before the deck
        for yp in (PIER_END, 226, 248):
            xl, xr = pier_x(yp)
            for xp in (xl + 1, xr - 2):
                xp = int(round(xp)); h_ = 10 + (yp - PIER_END) // 6
                cv.rect(xp - 1, yp + 2, 3, h_, _c(wood_d))
                for j in range(h_):
                    if j % 2 == 0: cv.px(xp - 1 + (j // 2) % 2, yp + 2 + h_ + j, _c(wood_d * 0.9 + _hx('#3a2a48') * 0.1))
        # deck front face at the end
        xl, xr = pier_x(PIER_END)
        cv.rect(int(xl), PIER_END, int(xr - xl) + 1, 4, _c(wood_d))
        cv.rect(int(xl), PIER_END + 4, int(xr - xl) + 1, 1, _c(gap))
        # planks: boards at equal depth steps
        z_end = 1.0 / (PIER_END - VP[1]); z_bot = 1.0 / (H - VP[1])
        nb = 15
        edges = [VP[1] + 1.0 / (z_end + (z_bot - z_end) * i / nb) for i in range(nb + 1)]
        rng = np.random.default_rng(self.seed + 61)
        for i in range(nb):
            y0, y1 = int(round(edges[i])), int(round(edges[i + 1]))
            tone = 0.9 + 0.2 * rng.random()
            for y in range(y0, y1):
                xl, xr = pier_x(y); xl, xr = int(math.ceil(xl)), int(math.floor(xr))
                if y >= H: break
                xs = np.arange(xl, xr + 1)
                base = wood * tone
                # sky sheen on the far boards + warm sheen toward the sun side
                fk = np.clip(1 - (y - PIER_END) / 40.0, 0, 1)
                sk = np.exp(-np.abs(xs - (SUN_X - 30)) / 60.0) * fk
                c = base[None] + (wood_l - base)[None] * (0.25 * fk + 0.40 * sk)[:, None]
                c = c * (1 - 0.38 * (y - PIER_END) / (H - PIER_END))
                grain = M.value_noise(xs * 0.25 + i * 13.0, np.full(xs.shape, y * 1.0), 1.0, self.seed + 62 + i)
                c = c * (0.9 + 0.16 * grain)[:, None]
                yy_ = np.full(xs.shape, y); c = self.dither(c, 6.0, yy_, xs)
                a[y, xl:xr + 1, :3] = c.astype(np.uint8); a[y, xl:xr + 1, 3] = 255
                self.E[y, xl:xr + 1] = 0.25 * fk + 0.5 * sk
                self.T[y, xl:xr + 1] = 0.3
            # gap line at the near edge of the board + a lit lip on the far edge
            yg = min(y1, H - 1)
            xl, xr = pier_x(yg)
            cv.rect(int(math.ceil(xl)), yg - (1 if y1 - y0 > 6 else 0), int(xr - xl), 1, _c(gap))
            xl0, xr0 = pier_x(y0)
            xs = np.arange(int(math.ceil(xl0)), int(xr0))
            if len(xs):
                sk = np.exp(-np.abs(xs - (SUN_X - 30)) / 50.0)
                for x, s in zip(xs, sk):
                    if s > 0.5 and y0 < 240: cv.px(int(x), y0, _c(sheen * s * 0.7 + wood * (1 - 0.7 * s))); self.E[y0, int(x)] = 0.5 * s
            # nails
            for xn in (xl0 + 3, xr0 - 4):
                if y1 - y0 > 3: cv.px(int(xn), y0 + 1, _c(wood_d))
            # a few split boards
            if rng.random() < 0.4:
                xs_ = int(rng.uniform(xl0 + 10, xr0 - 10)); cv.rect(xs_, y0 + 1, 1, max(1, y1 - y0 - 1), _c(wood_d))
        # stringers (side beams) + rim light on the sun side
        for y in range(PIER_END, H):
            xl, xr = pier_x(y)
            th = 2 + (y - PIER_END) // 22
            cv.rect(int(xl) - th, y, th, 1, _c(wood_d)); cv.rect(int(xr) + 1, y, th, 1, _c(wood_d))
            cv.px(int(xr) + th, y, _c(sheen * 0.55 + wood_d * 0.45)); self.E[y, int(xr) + th] = 0.5
        # short posts sticking up at the sides (mooring posts) near the camera
        for (yp, side) in ((236, -1), (236, 1)):
            xl, xr = pier_x(yp); xp = int(xl) - 4 if side < 0 else int(xr) + 2
            cv.rect(xp, yp - 18, 4, 20, _c(wood_d)); cv.rect(xp, yp - 19, 4, 1, _c(wood))
            cv.rect(xp + 3, yp - 18, 1, 20, _c(sheen * 0.5 + wood_d * 0.5)); self.E[yp - 18:yp + 2, xp + 3] = 0.5
            if side < 0:                                                    # rope coil on the left post
                for k in range(3): cv.rect(xp - 1, yp - 12 + 2 * k, 6, 1, C('#b89a72') if k % 2 == 0 else C('#8a7052'))
        pl, pr = pier_x(self.yy.astype(np.float32))
        self.pier_mask = (self.yy >= PIER_END) & (self.xx >= pl - 4) & (self.xx <= pr + 4)

    # ================================================================ deck props
    def props(self):
        cv = self.cv
        dk = C('#141018')
        # lantern (left of Claude) - the flame grows with dusk
        lx, ly = LANTERN
        cv.ellipse(lx, ly + 1, 5, 1, dk)
        cv.rect(lx - 3, ly - 1, 7, 2, C('#3a2e2e')); cv.rect(lx - 3, ly - 9, 7, 1, C('#3a2e2e'))
        cv.rect(lx - 2, ly - 8, 5, 7, C('#e8c08a') if self.dusk > 0.05 else C('#a07a6a'))
        cv.rect(lx - 3, ly - 8, 1, 7, C('#3a2e2e')); cv.rect(lx + 3, ly - 8, 1, 7, C('#3a2e2e'))
        cv.px(lx, ly - 5, C('#fff4c8')); cv.px(lx, ly - 4, C('#ffc060'))
        for i in range(5): cv.px(lx - 2 + i, ly - 11 + (0 if i in (0, 4) else -1 if i == 2 else 0), C('#3a2e2e'))
        self.E[ly - 8:ly - 1, lx - 2:lx + 3] = 0.55 + 0.45 * self.dusk
        # galvanised bucket between them (empty)
        bx, by = 250, 228
        for j in range(10):
            w_ = 9 + j // 4
            cv.rect(bx - w_ // 2, by - 10 + j, w_, 1, C('#5e6878') if j % 3 else C('#4a5262'))
        cv.rect(bx - 5, by - 11, 11, 1, C('#e0b896')); self.E[by - 11, bx - 5:bx + 6] = 0.6
        cv.rect(bx + 5, by - 10, 1, 9, C('#c89a7a')); self.E[by - 10:by - 1, bx + 5] = 0.35
        for i in range(9):
            ang = math.pi * i / 8
            cv.px(int(round(bx + 5 * math.cos(ang))), int(round(by - 11 - 4 * math.sin(ang))), C('#7a7f8a'))
        cv.ellipse(bx, by, 6, 1, dk)
        # tackle box (left, near) + thermos (old man's right)
        tx, ty = 176, 236
        cv.ellipse(tx + 8, ty + 1, 10, 1, dk)
        cv.rect(tx, ty - 7, 16, 7, C('#6a3a36')); cv.rect(tx, ty - 8, 16, 1, C('#d08a6a')); cv.rect(tx + 6, ty - 10, 4, 2, C('#3a2a2a'))
        cv.rect(tx, ty - 4, 16, 1, C('#4a2a2a')); cv.px(tx + 8, ty - 4, C('#c8a060'))
        self.E[ty - 8, tx:tx + 16] = 0.4
        hx, hy = 298, 222
        cv.ellipse(hx, hy + 1, 3, 1, dk)
        cv.rect(hx - 2, hy - 9, 5, 10, C('#3a5a6a')); cv.rect(hx - 2, hy - 11, 5, 2, C('#c8c0b0')); cv.rect(hx + 2, hy - 9, 1, 10, C('#9ab8c0'))
        self.E[hy - 11:hy + 1, hx + 2] = 0.5

    # ================================================================ reeds (front layer, sway variants)
    def build_fronts(self, n):
        rng = np.random.default_rng(self.seed + 41)
        stalks = []
        for (x0, x1, cnt, side, t0, t1) in ((0, 58, 14, 1, 118, 200), (446, 480, 7, -1, 168, 222)):
            for i in range(cnt):
                x = float(rng.uniform(x0, x1)); top = float(rng.uniform(t0, t1))
                stalks.append(dict(x=x, top=top, lean=float(rng.uniform(-0.10, 0.10)) + 0.07 * side, ph=float(rng.uniform(0, 6.28)),
                                   cat=rng.random() < 0.4, side=side, leaves=int(rng.integers(1, 3)), seed=int(rng.integers(1e6))))
        rim = _lerp('#ffa860', '#c8705e', self.dusk)
        dark = _lerp('#2a1e2c', '#1a1420', self.dusk); mid_ = _lerp('#3c2c34', '#261c28', self.dusk)
        out = []
        for f in range(n):
            ph = 2 * math.pi * f / n
            cv = Canvas(W, H)
            for s in stalks:
                L = H - s['top']; sway = self.sway_amp * math.sin(ph + s['ph'])
                pts = [(s['x'] + s['lean'] * k + sway * (k / L) ** 2, H - k) for k in range(int(L) + 1)]
                cd, cm = _c(dark), _c(mid_); cr = _c(rim * 0.7 + mid_ * 0.3)
                for (px_, py_) in pts:
                    cv.px(int(round(px_)), int(round(py_)), cd)
                    if py_ < 236: cv.px(int(round(px_)) + s['side'], int(round(py_)), cr)
                r2 = np.random.default_rng(s['seed'])
                for li in range(s['leaves']):
                    k0 = int(r2.uniform(0.1, 0.5) * L); dirn = 1 if r2.random() < 0.5 else -1
                    bx_, by_ = pts[k0]; ln = r2.uniform(16, 30)
                    for k in range(int(ln)):
                        u = k / ln
                        cv.px(int(round(bx_ + dirn * k * 0.55 + sway * 0.6 * u)), int(round(by_ - k * (1.0 - 0.9 * u * u))), cm)
                if s['cat']:
                    tx, ty = (int(round(v)) for v in pts[-1])
                    cv.rect(tx - 1, ty + 2, 3, 8, C('#4a2e26')); cv.px(tx, ty, cd); cv.px(tx, ty + 1, cd)
                    cv.rect(tx + s['side'], ty + 3, 1, 6, _c(rim * 0.8 + _hx('#4a2e26') * 0.2))
            out.append(cv.a.copy())
        return out

    # ================================================================ dynamic pieces
    def glitter(self, t, x0=290, x1=372):
        y0, y1 = HORIZON + 1, PIER_END + 26
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dy = (yy - HORIZON).astype(np.float32)
        prof = self._column(dy, xx)
        persp = 0.25 + dy / 70.0
        drift = t * (1.2 + 2.0 * persp)
        n = M.value_noise((xx + drift * 3) / (1.2 + 4 * persp), yy * 1.0 + np.floor(t * 6) * 0.37, 1.0, self.seed + 51)
        on = (n > 1.0 - prof * 0.55) & (prof > 0.05)
        pl, pr = pier_x(yy.astype(np.float32))
        on &= ~((yy >= PIER_END) & (xx >= pl - 4) & (xx <= pr + 4))
        rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8); rgba[on] = C('#fff6d8')
        E = np.zeros(rgba.shape[:2], np.float32); E[on] = 1.0
        return rgba, E, x0, y0

    def birds(self, t, x0=150.0, y0=58.0, speed=3.0):
        """a small flock crossing the sky slowly: list of (x, y, frame 0/1) in native px."""
        out = []
        for i, (dx, dy_) in enumerate(((0, 0), (-7, -3), (-6, 4), (-14, -5), (-13, 7), (-21, 2))):
            ph = t * 2.6 + i * 1.3
            out.append((x0 + dx + speed * t, y0 + dy_ + 0.6 * math.sin(t * 0.8 + i), int(ph) % 2))
        return out

    def ripple_rings(self, t, t0, cx, cy, n=3, speed=16.0, gap=0.45, life=2.6):
        pts = []
        for i in range(n):
            age = t - t0 - i * gap
            if age <= 0 or age > life: continue
            r = 2 + age * speed * (1 - 0.15 * i); a = (1 - age / life) ** 1.4
            m = max(8, int(r * 2.2))
            for k in range(m):
                ang = 2 * math.pi * k / m
                x = cx + r * math.cos(ang); y = cy + 0.30 * r * math.sin(ang)
                xi, yi = int(round(x)), int(round(y))
                if 0 <= xi < W and HORIZON < yi < H:
                    pl, pr = pier_x(yi)
                    if not (yi >= PIER_END - 1 and pl - 4 <= xi <= pr + 4): pts.append((xi, yi, a))
        return pts


def draw_birds(cv, pts, col):
    for p in pts:
        if len(p) > 3 and p[3]: _big_bird(cv, p, col); continue
        x, y, f = p[:3]
        x, y = int(round(x)), int(round(y))
        if f == 0: cv.px(x - 2, y - 1, col); cv.px(x - 1, y, col); cv.px(x, y, col); cv.px(x + 1, y, col); cv.px(x + 2, y - 1, col)
        else: cv.px(x - 2, y + 1, col); cv.px(x - 1, y, col); cv.px(x, y, col); cv.px(x + 1, y, col); cv.px(x + 2, y + 1, col)


# ================================================================ the bobber (v0.7): the old man's hand-made float
# Same design at two scales so it reads as one object: bobber_far() floats in the sun column (wide / insert / paint),
# bobber_fine() is the hero prop at character scale (the hand-over, ACT V on top of the 'weekend' blocks).
BOB_COLS = {'h': '#fff2c8', 'r': '#ff6a3a', 'R': '#d8433a', 'q': '#ff9a7a', 'Q': '#a32e2c',
            'G': '#e8b860', 'g': '#a8783a', 'W': '#fff6ec', 'w': '#d8cec8', 'B': '#c8843e', 'b': '#e8b070',
            'k': '#8a5228', 's': '#f07a4a', 'D': '#3a2a3a', 'o': '#d9a64e'}
BOB_FINE = ["...h...",
            "...r...",
            "...r...",
            "...R...",
            "..qRQ..",
            "..GGg..",
            ".WWWWw.",
            ".WWsWw.",
            ".bBBBk.",
            ".bBBBk.",
            ".bBGBk.",
            ".bBBBk.",
            "..BBk..",
            "..GGg..",
            "...D...",
            "...D...",
            "...o..."]
BOB_E = {'h': 0.95, 'r': 0.6, 'R': 0.25, 'q': 0.35, 'G': 0.3, 'W': 0.2, 's': 0.3}

def bobber_fine(outline=True):
    """-> (rgba, E) 9x19 with a dark outline: fluorescent tip, red cap, gold ring, white band with a tiny
    hand-painted sun dot, varnished honey-wood body with a gold inlay, gold ring, dark stem, brass eyelet."""
    h, w = len(BOB_FINE), len(BOB_FINE[0])
    a = np.zeros((h + 2, w + 2, 4), np.uint8); E = np.zeros((h + 2, w + 2), np.float32)
    for y, row in enumerate(BOB_FINE):
        for x, ch in enumerate(row):
            if ch == '.': continue
            a[y + 1, x + 1] = C(BOB_COLS[ch]); E[y + 1, x + 1] = BOB_E.get(ch, 0.0)
    if outline:
        m = a[..., 3] > 0
        nb = np.zeros_like(m)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb |= np.roll(np.roll(m, dy, 0), dx, 1)
        o = nb & ~m
        a[o] = C('#2e1a22')
        a[0, :] = np.where(m[0, :, None], a[0, :], 0) if False else a[0, :]
    return a, E

def bobber_far():
    """-> (rgba, E) 3x7 (bottom two rows below the waterline): the same float far away - tip, red, gold, white."""
    a = np.zeros((7, 3, 4), np.uint8)
    for y, col in ((0, '#fff2c8'), (1, '#ff6a3a'), (2, '#d8433a'), (3, '#e8b860'), (4, '#fff6ec')):
        a[y, :] = C(col)
    a[0, 0] = a[0, 2] = 0; a[1, 0] = a[1, 2] = 0
    E = np.zeros((7, 3), np.float32); E[0:2] = 0.7; E[2] = 0.45; E[3:5] = 0.35
    return a, E


BUCKET_SIDE = ["...hhhhhhhhh...",
               "..hoooooooooh..",
               ".hoWwwwwwwwwoh.",
               ".hoooooooooooh.",
               "..LmmmmmmmmmSk.",
               "..LmmmmmmmmSSk.",
               "..BBBBBBBBBBBk.",
               "..LmmmmdmmmSSk.",
               "...LmmmmmmmSk..",
               "...LmmmmmmSSk..",
               "...BBBBBBBBBk..",
               "...LmmmmmmmSk..",
               "....kkkkkkkk..."]
BUCKET_COLS = {'h': '#e8eef2', 'o': '#7a8790', 'W': '#3a5a68', 'w': '#5f8fa0', 'L': '#d6dde2', 'm': '#a9b4bb',
               'S': '#7d8890', 'k': '#3a3440', 'B': '#8f9aa2', 'd': '#8d979e'}

def bucket_side(handle=True):
    """-> (rgba, E) side view of the old man's zinc bucket (15x13 + handle): rolled rim, a sliver of water inside with
    a glint, two pressed bands, a dent, lit from the left.  Give it a 1px contact shadow when placed."""
    h, w = len(BUCKET_SIDE), len(BUCKET_SIDE[0])
    top = 4 if handle else 0
    a = np.zeros((h + top, w, 4), np.uint8); E = np.zeros((h + top, w), np.float32)
    for y, row in enumerate(BUCKET_SIDE):
        for x, ch in enumerate(row):
            if ch in '. ': continue
            a[y + top, x] = C(BUCKET_COLS[ch])
    a[2 + top, 5] = C('#cfe8f0'); E[2 + top, 5] = 0.35                       # glint on the water
    if handle:                                                              # wire handle arc
        HC = C('#5a5560')
        for x, y in ((1, 3), (2, 2), (3, 1), (4, 1), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 1), (11, 1), (12, 2), (13, 3)):
            a[y, x] = HC
        a[0, 6] = C('#9a95a0')
    return a, E



# ================================================================ v0.11: river details (egg) - flock, sparkles, motes, sinking sun
def _big_bird(cv, p, col):
    """a nearer bird: 9 px wingspan, 3 wing frames (0 up, 1 level, 2 down)."""
    x, y, f = int(round(p[0])), int(round(p[1])), p[2] % 3
    cv.px(x, y, col); cv.px(x + 1, y, col); cv.px(x - 1, y, col); cv.px(x + 2, y - 1, col)    # body + head
    wing = {0: [(-2, -1), (-3, -2), (-4, -3), (2, -2), (3, -3), (4, -4)],
            1: [(-2, 0), (-3, 0), (-4, -1), (2, 0), (3, 0), (4, -1)],
            2: [(-2, 1), (-3, 1), (-4, 2), (2, 1), (3, 2), (4, 2)]}[f]
    for dx, dy in wing: cv.px(x + dx, y + dy, col)


def flock(t, t0, p0, vel, n=4, flap=3.4, big=True, seed=0):
    """a flock crossing the frame from p0 at t0 with velocity vel (px/s), V formation; [] before t0.
    returns draw_birds() points (x, y, frame, big)."""
    if t < t0: return []
    a = t - t0; rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        side = -1 if i % 2 else 1; rank = (i + 1) // 2
        dx, dy = -9 * rank, side * 5 * rank + float(rng.uniform(-1, 1))
        ph = a * flap + float(rng.uniform(0, 3))
        x = p0[0] + vel[0] * a + dx; y = p0[1] + vel[1] * a + dy + 0.8 * math.sin(a * 1.7 + i)
        if -10 < x < W + 10 and -10 < y < H: out.append((x, y, int(ph) % 3 if big else int(ph) % 2, big))
    return out


def sparkles(t, n=9, life=0.55, seed=5, y0=None, y1=None, spread=0.9):
    """star glints in the sun column: list of (x, y, a) - each slot pops up at a new place every cycle."""
    y0 = HORIZON + 3 if y0 is None else y0; y1 = PIER_END + 24 if y1 is None else y1
    out = []
    for i in range(n):
        per = life * (1.6 + 0.37 * (i % 3))
        c = int(math.floor((t + i * 0.29) / per)); u = ((t + i * 0.29) - c * per) / life
        if u >= 1: continue
        r = np.random.default_rng(seed * 1000 + i * 97 + c)
        y = float(r.uniform(y0, y1)); hw = 4 + (y - HORIZON) * 0.30
        x = SUN_X + float(r.normal(0, spread)) * hw
        pl, pr = pier_x(y)
        if y >= PIER_END - 2 and pl - 5 <= x <= pr + 5: continue
        out.append((x, y, math.sin(math.pi * u)))
    return out


def draw_sparkles(rgba, E, pts, ox=0, oy=0, col='#fffbe8'):
    """4-point stars (arm 1-2 px by brightness) into an RGBA patch at offset (ox, oy)."""
    c = C(col); h, w = rgba.shape[:2]
    for (x, y, a) in pts:
        xi, yi = int(round(x)) - ox, int(round(y)) - oy
        arm = 2 if a > 0.75 else (1 if a > 0.3 else 0)
        cells = [(0, 0)] + [(d * k, 0) for k in range(1, arm + 1) for d in (-1, 1)] + [(0, d * k) for k in range(1, arm) for d in (-1, 1)]
        for dx, dy in cells:
            X, Y = xi + dx, yi + dy
            if 0 <= X < w and 0 <= Y < h: rgba[Y, X] = c; E[Y, X] = max(E[Y, X], a)


def sun_motes(t, n=40, box=(190, 96, 440, 230), seed=9, rise=2.2):
    """drifting light dust in the low sun: list of (x, y, a); they rise slowly, wander, and twinkle."""
    r = np.random.default_rng(seed)
    x0, y0, x1, y1 = box; bw, bh = x1 - x0, y1 - y0
    px, py = r.uniform(0, bw, n), r.uniform(0, bh, n)
    sp, ph, tw = r.uniform(0.5, 1.5, n), r.uniform(0, 6.28, n), r.uniform(0.6, 1.6, n)
    out = []
    for i in range(n):
        x = x0 + (px[i] + 1.2 * t + 3.0 * math.sin(t * 0.5 * sp[i] + ph[i])) % bw
        y = y0 + (py[i] - rise * sp[i] * t) % bh
        a = 0.5 + 0.5 * math.sin(t * 2.2 * tw[i] + ph[i])
        near = math.exp(-abs(x - SUN_X) / 110.0)                  # brighter in the sun's path
        if a * (0.4 + 0.6 * near) > 0.35: out.append((x, y, a * (0.4 + 0.6 * near)))
    return out


class DuskDrift:
    """the sun keeps sinking: pre-built skies at 1-px sun steps, swapped into an OutdoorScene per frame.
    DuskDrift(sc, dusk_max).apply(k) with k 0..1 (sun_y += 22*dusk_max*k, sky / clouds / glow toward SKY1)."""
    def __init__(self, sc, dusk_max=0.32, seed=0):
        self.sc = sc
        n = max(1, int(round(22 * dusk_max)))
        self.steps = []
        for i in range(n + 1):
            bg = RiverPier(dusk_max * i / n, seed=seed, sway_frames=1).bg
            self.steps.append((bg['rgba'][..., :3].astype(np.float32), bg['haze']))
        self.k = None

    def apply(self, k):
        k = min(1.0, max(0.0, float(k)))
        if k == self.k: return
        self.k = k
        x = k * (len(self.steps) - 1); i = min(int(x), len(self.steps) - 2) if len(self.steps) > 1 else 0
        f = x - i
        (r0, h0), (r1, h1) = self.steps[i], self.steps[min(i + 1, len(self.steps) - 1)]
        self.sc.rgb = np.ascontiguousarray(np.clip(r0 + (r1 - r0) * f + 0.5, 0, 255).astype(np.uint8))
        self.sc.haze2 = (h0 + (h1 - h0) * f).astype(np.float32) if h0 is not None else None
        self.sc._hazeq = {}
