"""pixelkit.sets.street - sunny morning shopping street (side-view diorama, 960x270 native, ACT III).  v2

    st = Street()                     # paints everything once (albedo, emissive, sun visibility, AO, haze)
    bg = st.bg                        # dict for outdoor.OutdoorScene; bg['front'] = LIST of canopy-sway variants
    st.front_index(t)                 # which front variant to show at time t (gentle 1-px rustle of the leaves)
    st.A['exit_door']                 # (x, y, w, h) of the 安全出口 doorway on the office tower (left end)
    st.A['trees']                     # [(x, foot), ...] tree positions (falling leaves spawn from the canopies)
    st.door_sprite(open_k)            # the steel door leaf, swung open toward the camera (draw into mid)

Layout (native px):  sky 0..~120 | far skyline | facades down to y = GROUND (184) | sidewalk 184..226 (with a
yellow tactile strip) | curb 226..231 | road 231..270.  Claude walks with feet at ~200, passers-by at 186-192.
Sun = morning, low from the left: shadows fall right and slightly back (outdoor_state shadow_sx>0, shadow_sy<0).
Buildings (left -> right): office tower + 安全出口 (0-150) | bakery 面包房 (150-300) | alley | flower shop 花店
(330-500) | convenience store 便利店 (500-660) | apartments + bookshop 书店 + garage (660-960).

Texture rules (v2, after the reference review):  no large flat fills - every wall gets sparse short dark dashes,
chips, rising damp and drip streaks under sills; every object gets a 1 px dark warm outline on its shadow side;
shop windows show a lit interior behind a partial sky reflection; the sidewalk tiles vary tile by tile; the trees
are clusters of 6-tone leaf masses lit from the upper left with dithered transitions, broken edges, stray leaves
and branches showing through gaps.  The light itself is quantised by outdoor.py (light.dither_light).
"""
import math, functools
import numpy as np, cv2
from ..core import Canvas, C, mix, text_width, BAYER4
from ..palette import ramp
from .. import materials as M
from ..scene import Sprite
from ..outdoor import haze_map

W, H = 960, 270
GROUND, CURB, ROAD = 184, 226, 231
WALK_Y = 206
OUTL = C('#2b1a24')                      # the dark warm outline colour of the whole set

@functools.lru_cache(maxsize=256)
def R(base, n=6, **kw): return tuple(ramp(base, n, **kw))

def dk(c, k=0.5): return mix(c, OUTL, k)

def _yx(h, w): return np.mgrid[0:h, 0:w]


class Street:
    def __init__(self, seed=0, w=W, sway_frames=12):
        self.W, self.H, self.seed = w, H, seed
        self.cv = Canvas(w, H)
        self.E = np.zeros((H, w), np.float32)
        self.T = np.ones((H, w), np.float32)          # sun visibility
        self.ao = np.ones((H, w), np.float32)
        self.front = Canvas(w, H)                      # static occluders in front of the walking line
        self.frontE = np.zeros((H, w), np.float32)
        self.A = {'trees': []}
        self.rng = np.random.default_rng(seed + 1234)
        self.sky(); self.skyline(); self.cables()
        self.office(0, 150); self.bakery(150, 300); self.alley(300, 330); self.flower_shop(330, 500)
        self.konbini(500, 660); self.apartments(660, w)
        self.vertical_signs()
        self.sidewalk(); self.road()
        self.street_props()
        self.canopies = []
        for i, x in enumerate((316, 646, 870)): self.tree(x, seed=101 + i)
        self.fronts = self.build_fronts(sway_frames)
        self.lighting()
        self.bg = dict(rgba=self.cv.a, E=self.E, T=self.T, ao=self.ao, ground=self.ground,
                       haze=haze_map(w, H, 2, sun_xy=(-90, -70), rays=12, ray_k=0.45, glow_k=0.55, glow_r=260.0,
                                     horizon=120, horizon_k=0.10),
                       front=self.fronts, frontE=self.frontE)

    SWAY_PERIOD = 3.6
    def front_index(self, t, period=None):
        """canopy variant for time t.  The sway frames are one seamless wind cycle (a ripple travelling
        through the leaf masses, crown tips moving up to 2 px), looped every `period` seconds."""
        n = len(self.fronts)
        if n == 1: return 0
        return int(t / (period or self.SWAY_PERIOD) * n) % n

    # ================================================================== small painting helpers
    def darken(self, x, y, k=0.85):
        if 0 <= x < self.W and 0 <= y < H:
            self.cv.a[y, x, :3] = (self.cv.a[y, x, :3].astype(np.float32) * k).astype(np.uint8)

    def outline_box(self, x, y, w, h, col=None):
        c = OUTL if col is None else col
        self.cv.rect(x - 1, y - 1, w + 2, 1, c); self.cv.rect(x - 1, y + h, w + 2, 1, c)
        self.cv.rect(x - 1, y, 1, h, c); self.cv.rect(x + w, y, 1, h, c)

    def soft_shadow(self, x, y, w, h, k=0.3, fade=3, ao=None):
        """sun shadow on a facade with a short graded penumbra at the bottom / right (dithered later by the light)."""
        x0, y0, x1, y1 = max(0, x), max(0, y), min(self.W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0: return
        yy, xx = np.mgrid[y0:y1, x0:x1]
        fy = np.clip((y + h - 0.5 - yy) / fade, 0, 1); fx = np.clip((x + w - 0.5 - xx) / fade, 0, 1)
        m = np.minimum(fy, fx)
        self.T[y0:y1, x0:x1] *= 1 - (1 - k) * m
        if ao: self.ao[y0:y1, x0:x1] *= 1 - (1 - ao) * m

    def weather(self, x0, x1, top, bot, rp, seed, dash=1.0, bricks=0.5, damp=True, cracks=2):
        """sparse texture on a painted wall: short dark dashes (worn brick courses showing through), chips with a
        lit lip, a few hairline cracks, rising damp at the base and grime under the top edge."""
        cv = self.cv; rng = np.random.default_rng(seed + 500)
        area = (x1 - x0) * (bot - top)
        for _ in range(int(area / 70 * dash)):
            x = int(rng.integers(x0 + 2, max(x0 + 3, x1 - 6))); y = int(rng.integers(top + 2, max(top + 3, bot - 2)))
            L = int(rng.integers(2, 6)); c = rp[1] if rng.random() < 0.55 else rp[2]
            cv.hline(x, y, L, c)
            if rng.random() < 0.35: cv.hline(x + 1, y + 1, max(1, L - 2), rp[4])
        for _ in range(int(area / 900 * bricks)):          # little exposed brick patches (2-3 courses)
            x = int(rng.integers(x0 + 3, max(x0 + 4, x1 - 12))); y = int(rng.integers(top + 4, max(top + 5, bot - 10)))
            for r in range(int(rng.integers(2, 4))):
                off = 0 if r % 2 == 0 else 3
                for k in range(int(rng.integers(1, 3))):
                    cv.hline(x + off + k * 6, y + r * 3, 4, rp[1]); cv.hline(x + off + k * 6, y + r * 3 + 1, 4, rp[2])
        for _ in range(cracks):
            x = int(rng.integers(x0 + 6, max(x0 + 7, x1 - 6))); y = int(rng.integers(top + 6, max(top + 7, bot - 20)))
            for i in range(int(rng.integers(5, 12))):
                cv.px(x, y, rp[1]); y += 1; x += int(rng.integers(-1, 2))
        if damp:
            yy, xx = np.mgrid[bot - 16:bot, x0:x1]
            n = M.fbm(xx.astype(float), yy.astype(float), 9.0, 3, seed + 7)
            v = n * 0.9 + (yy - (bot - 16)) / 16.0 * 0.8 + (BAYER4[yy % 4, xx % 4] - 0.5) * 0.25
            m = v > 1.0
            reg = cv.a[bot - 16:bot, x0:x1]
            reg[m, :3] = (reg[m, :3].astype(np.float32) * 0.86 + np.array(OUTL[:3]) * 0.04).astype(np.uint8)
        # grime streaks under the top edge
        for _ in range(int((x1 - x0) / 14)):
            x = int(rng.integers(x0 + 1, x1 - 1)); L = int(rng.integers(2, 9))
            for i in range(L):
                if i < L - 2 or (i + x) % 2 == 0: self.darken(x, top + 1 + i, 0.9)

    def drips(self, x, y, w, rng, k=0.86):
        """water streaks below a sill: 1 px dark runs with a dithered tail."""
        for xx in range(x, x + w):
            if rng.random() < 0.35:
                L = int(rng.integers(2, 9))
                for i in range(L):
                    if i < L - 3 or (i + xx) % 2 == 0: self.darken(xx, y + i, k)

    # ================================================================== sky + far city
    def sky(self):
        w = self.W
        yy, xx = _yx(H, w)
        t = np.clip(yy / 150.0, 0, 1)
        c0 = np.array(C('#9ab4ec')[:3], np.float32); c1 = np.array(C('#f6d2d6')[:3], np.float32); c2 = np.array(C('#ffe8bc')[:3], np.float32)
        col = np.where(t[..., None] < 0.55, c0 + (c1 - c0) * (t[..., None] / 0.55), c1 + (c2 - c1) * ((t[..., None] - 0.55) / 0.45))
        col = col + (np.clip(1 - xx / 500.0, 0, 1) * 18)[..., None] * np.array([1.0, 0.55, 0.0])
        th = BAYER4[yy % 4, xx % 4]
        q = np.floor(col / 9.0 + th[..., None]) * 9.0            # chunkier sky bands (visible dither, like the ref)
        self.cv.a[..., :3] = np.clip(q, 0, 255).astype(np.uint8); self.cv.a[..., 3] = 255
        self.E[:] = 1.0
        u, v = xx.astype(np.float64), yy.astype(np.float64)
        n = M.fbm(u * 0.5, v * 1.1, 46.0, 4, self.seed + 21)
        band = np.exp(-((yy - 38) / 26.0) ** 2) + 0.8 * np.exp(-((yy - 92) / 14.0) ** 2)
        d = n * band
        cloud = d > 0.42
        n2 = M.fbm(u * 0.5, (v - 3) * 1.1, 46.0, 4, self.seed + 21) * (np.exp(-((yy - 41) / 26.0) ** 2) + 0.8 * np.exp(-((yy - 95) / 14.0) ** 2))
        belly = cloud & (n2 <= 0.42)
        CL, CL2, CB, CB2 = C('#fff6e6'), C('#ffe9d2'), C('#e2c8dc'), C('#cdb4d6')
        self.cv.a[cloud] = CL2
        hi = cloud & (d > 0.50) & ~((BAYER4[yy % 4, xx % 4] > 0.5) & (d < 0.53))
        self.cv.a[hi] = CL
        self.cv.a[belly] = CB
        self.cv.a[belly & ~np.roll(belly, -1, 0)] = CB2
        self.sky_mask = np.ones((H, w), bool)

    def skyline(self):
        rng = np.random.default_rng(self.seed + 5)
        x = -10
        cols = [R('#b8a3cf', 5), R('#c7b0d4', 5), R('#a995c6', 5)]
        while x < self.W:
            bw = int(rng.integers(26, 60)); top = int(rng.integers(48, 104))
            rp = cols[int(rng.integers(0, 3))]
            self.cv.rect(x, top, bw, GROUND - top, rp[2]); self.cv.vline(x, top, GROUND - top, rp[3])
            self.cv.vline(x + bw - 1, top, GROUND - top, rp[1])
            self.cv.hline(x, top, bw, rp[3])
            for wy in range(top + 5, GROUND, 6):
                for wx in range(x + 3, x + bw - 3, 5):
                    if rng.random() < 0.55: self.cv.rect(wx, wy, 2, 2, rp[1] if rng.random() < 0.8 else C('#fff0c8'))
            if rng.random() < 0.3:
                self.cv.vline(x + bw // 2, top - 8, 8, rp[1]); self.cv.px(x + bw // 2, top - 9, C('#ff8a70'))
            if rng.random() < 0.35:   # rooftop water tank
                tx = x + int(rng.integers(3, max(4, bw - 10)))
                self.cv.rect(tx, top - 5, 7, 5, rp[1]); self.cv.hline(tx, top - 5, 7, rp[3])
            self.E[top - 9:GROUND, x:x + bw] = np.where(self.cv.a[top - 9:GROUND, x:x + bw, 3] > 0, self.E[top - 9:GROUND, x:x + bw], 0)
            self.E[top:GROUND, x:x + bw] = 0.0
            x += bw + int(rng.integers(-6, 6))
        # the far city is dimmer / hazier than the street
        self.far = (self.E == 0)

    def cables(self):
        """sagging overhead cables across the sky gaps, with two sparrows (drawn now, buildings paint over ends)."""
        cv = self.cv
        def sag(x0, y0, x1, y1, s, col):
            for x in range(x0, x1 + 1):
                u = (x - x0) / max(1, x1 - x0)
                y = y0 + (y1 - y0) * u + s * 4 * u * (1 - u)
                cv.px(x, int(round(y)), col)
                self.E[int(round(y)), x] = 0.0
        sag(140, 4, 340, 2, 12, C('#4a3e4c')); sag(140, 8, 340, 7, 15, C('#5a4c5a'))
        sag(490, 6, 670, 4, 13, C('#4a3e4c'))
        for bx, by in ((228, 15), (236, 15)):
            u = (bx - 140) / 200; y = int(round(4 + -2 * u + 12 * 4 * u * (1 - u)))
            cv.rect(bx, y - 3, 3, 2, C('#6a5040')); cv.px(bx + 3, y - 3, C('#4a3a30')); cv.px(bx - 1, y - 2, C('#8a6a50'))
            self.E[y - 3:y, bx - 1:bx + 4] = 0.0

    # ================================================================== walls / windows / awnings
    def wall(self, x0, x1, top, base, mat='plaster', seed=0, weather=True, **kw):
        x0c, x1c = max(0, x0), min(self.W, x1)
        yy, xx = np.mgrid[top:GROUND, x0c:x1c]
        u, v = xx.astype(np.float64), yy.astype(np.float64)
        rp = R(base, 6)
        if mat == 'brick':
            bw, bh = kw.get('bw', 10.0), kw.get('bh', 4.0)
            r, i, j = M.cell_rand(u, v, bw, bh, seed, stagger=0.5)
            mort = (np.mod(v, bh) < 1) | (np.mod(u + (np.floor(v / bh) % 2) * bw / 2, bw) < 1)
            t = 3.0 + (r - 0.5) * 1.1 + (M.fbm(u, v, 14, 2, seed) - 0.5) * 0.6
            t = np.where(r > 0.93, 1.6, t); t = np.where(r < 0.05, 4.2, t)       # odd dark / pale bricks
            t = np.where(mort, 4.0, t)
        elif mat == 'tiles':
            tw, th = kw.get('tw', 6.0), kw.get('th', 6.0)
            r, i, j = M.cell_rand(u, v, tw, th, seed)
            grout = (np.mod(u, tw) < 1) | (np.mod(v, th) < 1)
            t = np.where(grout, 2.0, 3.1 + (r - 0.5) * 0.9 + (M.fbm(u, v, 22, 2, seed) - 0.5) * 0.5)
            t = np.where(~grout & (np.mod(u, tw) < 2) & (np.mod(v, th) < 2), t + 0.6, t)   # glaze glint per tile
        elif mat == 'siding':
            t = 3.0 + (np.mod(v, 5) < 1) * -1.2 + (np.mod(v, 5) == 1) * 0.5 + (M.fbm(u, v, 30, 2, seed) - 0.5) * 0.6
        else:
            t = M.plaster(u, v, 3.0, seed, kw.get('mottle', 0.5), kw.get('speck', 0.02))
        img = M.apply_ramp(t, rp, xx, yy, True, band=2.4)
        self.cv.a[top:GROUND, x0c:x1c] = img
        self.E[top:GROUND, x0c:x1c] = 0.0
        if weather:
            dash = kw.get('dash', 1.0 if mat in ('plaster', 'siding') else 0.35)
            self.weather(x0c, x1c, top, GROUND, rp, seed, dash=dash, bricks=0.8 if mat == 'plaster' else 0.0)
        # building seams: 1 px dark outline + a lit edge on the sun side
        self.cv.vline(x0c, top, GROUND - top, dk(rp[1], 0.5)); self.cv.vline(x1c - 1, top, GROUND - top, dk(rp[1], 0.6))
        if x0c + 1 < x1c: self.cv.vline(x0c + 1, top, GROUND - top, rp[4])
        if top > 0: self.cv.hline(x0c, top - 1, x1c - x0c, OUTL)
        return rp

    def cornice(self, x0, x1, y, rp, h=4):
        self.cv.rect(x0 - 2, y, x1 - x0 + 4, h, rp[4]); self.cv.hline(x0 - 2, y, x1 - x0 + 4, rp[5])
        self.cv.hline(x0 - 2, y + h - 1, x1 - x0 + 4, rp[1]); self.cv.hline(x0 - 1, y + h, x1 - x0 + 2, OUTL)
        for k in range(x0, x1, 6): self.cv.px(k, y + h - 2, rp[2])        # dentils
        self.cv.px(x0 - 2, y, OUTL); self.cv.px(x1 + 1, y, OUTL)
        self.ao[y + h:y + h + 4, x0:x1] *= np.linspace(0.72, 1.0, 4)[:, None]
        self.soft_shadow(x0 + 2, y + h, x1 - x0 + 1, 3, 0.25, fade=2)

    def glass(self, gx, gy, gw, gh, top='#ffe4c4', bot='#7f86c4', glints=2, k0=0.25):
        """sky-reflecting glass, quantised to a 4-tone dithered ramp + diagonal glints."""
        if gw <= 0 or gh <= 0: return
        yy, xx = np.mgrid[gy:gy + gh, gx:gx + gw]
        rp = [mix(C(top), C(bot), k0 + 0.75 * i / 3) for i in range(4)]
        t = (yy - gy) / max(1, gh - 1) * 3.0
        self.cv.a[gy:gy + gh, gx:gx + gw] = M.apply_ramp(t, rp, xx, yy, True, band=1.6)
        for g in range(glints):
            off = gw - 3 - g * max(4, gw // 3)
            wdt = 2 if g == 0 else 1
            for i in range(gh):
                xx_ = gx + off - i
                for k in range(wdt):
                    if gx <= xx_ + k < gx + gw: self.cv.px(xx_ + k, gy + i, C('#fff8ec'))

    def window(self, x, y, w, h, frame='#f2ece2', curtain=None, box=None, sill=True, panes=2, lit=0.0, rng=None,
               blind=None, ac=False):
        cv = self.cv
        rng = rng or np.random.default_rng(x * 7 + y)
        fr = R(frame, 5)
        cv.rect(x - 2, y - 2, w + 4, h + 4, dk(fr[1], 0.55))
        cv.rect(x - 1, y - 1, w + 2, h + 2, fr[1]); cv.rect(x, y, w, h, fr[3]); cv.hline(x - 1, y - 1, w + 2, fr[4])
        gx, gy, gw, gh = x + 1, y + 1, w - 2, h - 2
        self.glass(gx, gy, gw, gh)
        if curtain:
            cr = R(curtain, 5)
            cw = max(2, gw // 3)
            for side in (0, 1):
                xs = gx if side == 0 else gx + gw - cw
                cv.rect(xs, gy, cw, gh, cr[3])
                for k in range(xs + 1, xs + cw, 2): cv.vline(k, gy + 1, gh - 1, cr[2])         # folds
                cv.vline(xs + (cw - 1 if side == 0 else 0), gy, gh, cr[1])
                cv.hline(xs, gy, cw, cr[4])
        if blind:      # half-lowered roller blind
            br = R(blind, 5); bh = int(gh * 0.38)
            cv.rect(gx, gy, gw, bh, br[3]); cv.hline(gx, gy + bh - 1, gw, br[1])
            for k in range(gy + 2, gy + bh - 1, 3): cv.hline(gx, k, gw, br[2])
        if panes == 2: cv.vline(x + w // 2, y, h, fr[3]); cv.vline(x + w // 2 + 1, y, h, fr[1])
        if panes >= 3:
            for k in (w // 3, 2 * w // 3): cv.vline(x + k, y, h, fr[3]); cv.vline(x + k + 1, y, h, fr[1])
        cv.hline(x, y + h // 3, w, fr[3]); cv.hline(x, y + h // 3 + 1, w, fr[1])
        if lit > 0: self.E[gy:gy + gh, gx:gx + gw] = lit
        self.soft_shadow(gx, gy, gw, 3, 0.3, fade=2); self.soft_shadow(gx, gy, 2, gh, 0.3, fade=1)
        if sill:
            cv.rect(x - 3, y + h + 1, w + 6, 2, fr[4]); cv.hline(x - 3, y + h + 2, w + 6, fr[2]); cv.hline(x - 3, y + h + 3, w + 6, OUTL)
            self.soft_shadow(x - 1, y + h + 4, w + 6, 3, 0.35, fade=2)
            self.drips(x - 1, y + h + 4, w + 3, rng)
        if box:
            bx, by = x - 1, y + h - 3
            cv.rect(bx, by, w + 2, 4, C('#8a5a3a')); cv.hline(bx, by, w + 2, C('#a8724a')); cv.hline(bx, by + 4, w + 2, OUTL)
            for i in range(w + 2):
                hh = int(rng.integers(2, 6))
                cv.vline(bx + i, by - hh, hh, C('#3f7a44') if rng.random() < 0.5 else C('#5f9e4f'))
                cv.px(bx + i, by - 1, C('#2c5236'))
                if rng.random() < 0.3: cv.px(bx + i, by - hh - 1, C(box if rng.random() < 0.7 else '#fff2c8'))
        if ac:          # air-conditioner box under the window, with a drip hose and a damp spot
            ax, ay = x + w // 2 - 9, y + h + 7
            cv.rect(ax - 1, ay - 1, 20, 12, OUTL); cv.rect(ax, ay, 18, 10, C('#e4e2dc')); cv.hline(ax, ay, 18, C('#f8f6f0'))
            cv.rect(ax + 2, ay + 2, 10, 6, C('#a8aaae'))
            for k in range(ay + 3, ay + 8, 2): cv.hline(ax + 2, k, 10, C('#7a7c82'))
            cv.ellipse(ax + 14.5, ay + 5, 2.2, 2.2, C('#8a8c92'))
            cv.vline(ax + 17, ay + 10, 6, C('#d8d4cc'))
            self.soft_shadow(ax + 2, ay + 10, 20, 4, 0.3, fade=3, ao=0.8)
            self.drips(ax + 16, ay + 16, 3, rng, 0.82)

    def awning(self, x, y, w, depth=12, cols=('#d65a4a', '#f4eadc'), stripe=5, scallop=True):
        cv = self.cv
        a, b = R(cols[0], 5), R(cols[1], 5)
        for yy in range(depth):
            for xx in range(w):
                c = a if ((xx // stripe) % 2 == 0) else b
                k = 4 if yy < 2 else (3 if yy < depth - 4 else 2)
                if yy == depth - 5 and (xx + yy) % 2: k = 2           # dithered fold where the canvas bends
                cv.px(x + xx, y + yy, c[k])
        for xx in range(0, w, stripe * 2): cv.vline(x + xx, y + 2, depth - 2, a[1])
        if scallop:
            for xx in range(0, w, stripe):
                c = a if ((xx // stripe) % 2 == 0) else b
                cv.rect(x + xx + 1, y + depth, stripe - 2, 2, c[2]); cv.hline(x + xx + 2, y + depth + 2, stripe - 4, OUTL)
                cv.px(x + xx + 1, y + depth + 1, OUTL); cv.px(x + xx + stripe - 2, y + depth + 1, OUTL)
        cv.hline(x, y - 1, w, OUTL); cv.hline(x, y, w, C('#6a4038')); cv.hline(x - 1, y + depth - 1, w + 2, C('#5a3830'))
        cv.vline(x - 1, y, depth, OUTL); cv.vline(x + w, y, depth, OUTL)
        self.E[y - 1:y + depth + 3, x - 1:x + w + 1] = 0.0
        self.soft_shadow(x + 4, y + depth + 2, w + 6, 14, 0.22, fade=5, ao=0.8)

    def sign(self, x, y, text, bg='#3b5a4a', fg='#fff3d6', fname='zh8', pad=3, lit=0.0, border='#e8c070'):
        cv = self.cv
        tw = text_width(text, fname); w = tw + pad * 2; h = 10 if fname == 'zh8' else 13
        cv.rect(x - 2, y - 2, w + 4, h + 4, OUTL)
        cv.rect(x - 1, y - 1, w + 2, h + 2, C(border)); cv.rect(x, y, w, h, C(bg))
        cv.hline(x, y, w, mix(C(bg), C('#ffffff'), 0.25)); cv.hline(x, y + h - 1, w, mix(C(bg), C('#000000'), 0.2))
        cv.text(x + pad, y + (0 if fname == 'zh8' else -1), text, C(fg), fname)
        if lit > 0:
            m = np.all(cv.a[y:y + h, x:x + w, :3] == np.array(C(fg)[:3]), -1)
            self.E[y:y + h, x:x + w][m] = lit
        self.soft_shadow(x + 2, y + h + 2, w + 2, 3, 0.35, fade=2)
        return w

    def door(self, x, y, w, h, col='#6a4a3a', glass=True, plaque=None):
        cv = self.cv; rp = R(col, 5)
        cv.rect(x - 2, y - 2, w + 4, h + 2, OUTL)
        cv.rect(x - 1, y - 1, w + 2, h + 1, rp[0]); cv.rect(x, y, w, h, rp[2]); cv.vline(x, y, h, rp[3]); cv.vline(x + 1, y, h, rp[3])
        cv.vline(x + w - 1, y, h, rp[1])
        if glass:
            gx, gy, gw, gh = x + 3, y + 3, w - 6, h // 2
            cv.rect(gx - 1, gy - 1, gw + 2, gh + 2, rp[0])
            self.glass(gx, gy, gw, gh, '#f4dcc8', '#6a6aa8', glints=1, k0=0.35)
        else:
            for py in (y + 4, y + h // 2 + 2):
                cv.rect(x + 3, py, w - 6, h // 2 - 8, rp[1]); cv.rect(x + 4, py + 1, w - 8, h // 2 - 10, rp[2])
        cv.rect(x + 3, y + h // 2 + 6, w - 6, 1, rp[1])
        cv.rect(x + w - 5, y + h // 2 + 2, 2, 4, C('#e8c070')); cv.px(x + w - 5, y + h // 2 + 5, C('#8a6a30'))
        cv.rect(x, y + h - 3, w, 3, rp[1])                                   # kick plate
        if plaque:
            pc, pt = plaque
            cv.rect(x + 3, y + 5, w - 6, 6, C(pc)); cv.text(x + 4, y + 3, pt, C('#fff4e0'), 'zh8') if False else None
        self.soft_shadow(x, y, w, 4, 0.4, fade=3, ao=0.85); self.soft_shadow(x, y, 3, h, 0.4, fade=2)
        self.ao[y:y + h, x:x + w] *= 0.88

    def shop_window(self, x, y, w, h, frame, kind, lamp_col='#ffe6b0', mull=3):
        """a shop window = a lit interior (back wall, shelves, goods, pendant lamps) seen through glass that
        reflects the sky in two diagonal bands.  kind: 'bakery' | 'flowers' | 'books' | 'konbini' | 'cafe'."""
        cv = self.cv; rng = np.random.default_rng(x * 13 + y)
        fr = R(frame, 5)
        cv.rect(x - 2, y - 2, w + 4, h + 4, OUTL); cv.rect(x - 1, y - 1, w + 2, h + 2, fr[1]); cv.hline(x - 1, y - 1, w + 2, fr[3])
        back = {'bakery': '#8a5a44', 'flowers': '#46685a', 'books': '#5a4038', 'konbini': '#e8eef0', 'cafe': '#6a4636'}[kind]
        br = R(back, 5)
        yy, xx = np.mgrid[y:y + h, x:x + w]
        tt = 2.6 - (yy - y) / h * 1.2 + (M.fbm(xx.astype(float), yy.astype(float), 10, 2, x) - 0.5) * 0.5
        cv.a[y:y + h, x:x + w] = M.apply_ramp(tt, br, xx, yy, True, band=2.0)
        E = {'konbini': 0.42, 'cafe': 0.26}.get(kind, 0.22)
        self.E[y:y + h, x:x + w] = E
        # interior floor / counter line
        cv.rect(x, y + h - 6, w, 6, br[1]); cv.hline(x, y + h - 6, w, br[3])
        if kind == 'bakery':
            for sy in (y + 18, y + 32):
                cv.hline(x + 1, sy + 6, w - 2, C('#5a3424')); cv.hline(x + 1, sy + 7, w - 2, C('#3a2018'))
                for bx in range(x + 3, x + w - 8, 9):
                    kindb = (bx // 9) % 3
                    if kindb == 0:   # round loaf
                        cv.ellipse(bx + 3.5, sy + 3, 4, 3, C('#b8702e')); cv.hline(bx + 1, sy + 1, 5, C('#e8b46a'))
                        cv.px(bx + 2, sy + 2, C('#7a4418')); cv.px(bx + 5, sy + 2, C('#7a4418')); cv.hline(bx + 1, sy + 5, 6, C('#6a3a18'))
                    elif kindb == 1:  # croissant
                        cv.rect(bx + 1, sy + 2, 6, 3, C('#d08a3e')); cv.px(bx, sy + 4, C('#d08a3e')); cv.px(bx + 7, sy + 4, C('#d08a3e'))
                        cv.vline(bx + 3, sy + 2, 3, C('#8a5020')); cv.vline(bx + 5, sy + 2, 3, C('#8a5020')); cv.hline(bx + 2, sy + 2, 4, C('#f0c070'))
                    else:            # baguettes in a basket
                        cv.rect(bx + 1, sy + 2, 6, 4, C('#8a6034')); cv.line(bx + 2, sy + 2, bx + 4, sy - 4, C('#e0a050')); cv.line(bx + 4, sy + 2, bx + 6, sy - 3, C('#c8843e'))
            # cake stand on the counter
            cx = x + w - 14
            cv.rect(cx, y + h - 13, 10, 6, C('#f4e8f0')); cv.hline(cx, y + h - 13, 10, C('#ff9ab0')); cv.px(cx + 5, y + h - 15, C('#e83a4a'))
            cv.hline(cx - 1, y + h - 7, 12, C('#d8d0d8'))
        elif kind == 'flowers':
            for k in range(x + 2, x + w - 4, 7):          # potted plants on a stepped stand + hanging pots
                ph = int(rng.integers(8, 16)); py = y + h - 6
                cv.rect(k, py - 5, 5, 5, C('#b0603e')); cv.hline(k, py - 5, 5, C('#d0805a'))
                for j in range(ph):
                    cv.px(k + 2 + int(round(math.sin(j * 0.9 + k) * 1.5)), py - 6 - j, C('#3f7a44'))
                    if j % 3 == 0: cv.px(k + 1, py - 6 - j, C('#5f9e4f')); cv.px(k + 3, py - 7 - j, C('#2f5a3a'))
                if rng.random() < 0.6: cv.px(k + 2, py - 6 - ph, C(['#ff6a8a', '#ffd04a', '#c88aff', '#ffffff'][int(rng.integers(0, 4))]))
            for k in range(x + 8, x + w - 6, 22):
                cv.vline(k + 2, y, 8, C('#3a2a24')); cv.rect(k, y + 8, 5, 4, C('#d8c8b0'))
                for j in range(6): cv.px(k + (j % 3) * 2 - 1, y + 12 + j, C('#4f8a4a'))
        elif kind == 'books':
            for sy in (y + 10, y + 24, y + 38):
                if sy + 8 > y + h - 6: break
                cv.hline(x + 1, sy + 8, w - 2, C('#3a2418')); cv.hline(x + 1, sy + 9, w - 2, C('#24140e'))
                k = x + 2
                while k < x + w - 3:
                    bw = int(rng.integers(2, 4)); bh = int(rng.integers(5, 9))
                    col = C(['#c84a3a', '#3a6ac8', '#e0b040', '#4a9a5a', '#8a5ab0', '#e8dcc0', '#2a5a7a'][int(rng.integers(0, 7))])
                    cv.rect(k, sy + 8 - bh, bw, bh, col); cv.vline(k, sy + 8 - bh, bh, dk(col, 0.35))
                    if bw > 2: cv.px(k + 1, sy + 9 - bh + 1, mix(col, C('#ffffff'), 0.5))
                    k += bw + (1 if rng.random() < 0.15 else 0)
            # the bookshop cat asleep in the window (curled loaf, ginger)
            cx, cy = x + 10, y + h - 6
            cv.ellipse(cx + 5, cy - 3, 6, 3.2, C('#e08a3e')); cv.ellipse(cx + 1, cy - 4, 3, 2.6, C('#e08a3e'))
            cv.px(cx - 1, cy - 7, C('#e08a3e')); cv.px(cx + 2, cy - 7, C('#e08a3e'))
            cv.hline(cx + 2, cy - 1, 8, C('#a85a24')); cv.hline(cx, cy - 4, 2, C('#5a3018'))
            for k in (cx + 4, cx + 7): cv.vline(k, cy - 5, 2, C('#c06a2a'))
            cv.hline(cx + 9, cy - 1, 3, C('#f0a860'))
            self.A['cat'] = (cx + 1, cy - 8)
        elif kind == 'cafe':
            # chalk menu board (left), cup shelf, counter with an espresso machine + grinder, a plant (right)
            mx, my = x + 4, y + 10
            cv.rect(mx - 1, my - 1, 22, 20, C('#5a3a28')); cv.rect(mx, my, 20, 18, C('#24342e'))
            cv.text(mx + 2, my - 1, '菜单', C('#f4ecd8'), 'zh8')
            for k in range(3):
                cv.hline(mx + 2, my + 10 + k * 3, 10 + (k * 5) % 6, C('#c8d0c4')); cv.hline(mx + 15, my + 10 + k * 3, 3, C('#f0c070'))
            sy = y + 14
            cv.hline(x + 28, sy + 6, w - 32, C('#4a2c1e')); cv.hline(x + 28, sy + 7, w - 32, C('#2e1a12'))
            for k in range(x + 30, x + w - 6, 6):
                c_ = C(['#f4f0e8', '#e8a87a', '#f4f0e8', '#7aa8c8'][(k // 6) % 4])
                cv.rect(k, sy + 2, 4, 4, c_); cv.vline(k + 3, sy + 2, 4, dk(c_, 0.3)); cv.px(k + 4, sy + 3, dk(c_, 0.25))
            cy_ = y + h - 6
            cv.rect(x + 1, cy_ - 7, w - 2, 7, C('#8a5a3a')); cv.hline(x + 1, cy_ - 7, w - 2, C('#c08a5a')); cv.hline(x + 1, cy_ - 6, w - 2, C('#a06a44'))
            ex = x + w // 2 - 6
            cv.rect(ex - 1, cy_ - 20, 18, 13, OUTL); cv.rect(ex, cy_ - 19, 16, 12, C('#c8ccd4')); cv.hline(ex, cy_ - 19, 16, C('#eef0f4'))
            cv.rect(ex + 2, cy_ - 15, 12, 3, C('#5a5e66')); cv.px(ex + 3, cy_ - 18, C('#ff5a3a')); cv.px(ex + 6, cy_ - 18, C('#5aff8a'))
            self.E[cy_ - 18, ex + 3] = 1.0; self.E[cy_ - 18, ex + 6] = 1.0
            cv.vline(ex + 4, cy_ - 12, 3, C('#3a3a40')); cv.vline(ex + 11, cy_ - 12, 3, C('#3a3a40'))
            cv.rect(ex + 3, cy_ - 10, 3, 3, C('#f4f0e8')); cv.rect(ex + 10, cy_ - 10, 3, 3, C('#f4f0e8'))
            gx_ = ex + 20
            cv.rect(gx_, cy_ - 16, 6, 9, C('#3a3036')); cv.rect(gx_ + 1, cy_ - 21, 4, 5, C('#c8a070')); cv.hline(gx_ + 1, cy_ - 21, 4, C('#e8c890'))
            px_ = x + w - 9
            cv.rect(px_, cy_ - 12, 6, 5, C('#c86a4a')); cv.hline(px_, cy_ - 12, 6, C('#e88a6a'))
            for j in range(9):
                cv.px(px_ + 2 + int(round(math.sin(j * 1.3) * 2)), cy_ - 13 - j, C('#3f7a44'))
                cv.px(px_ + 3 + int(round(math.cos(j * 1.1) * 2)), cy_ - 13 - j, C('#5f9e4f'))
        elif kind == 'konbini':
            for sy in range(y + 12, y + h - 4, 13):
                cv.hline(x, sy, w, C('#9aa4ac')); cv.hline(x, sy + 1, w, C('#6a747c'))
                for k in range(x + 1, x + w - 2, 3):
                    col = C(['#e85a4a', '#4ab0e0', '#f4c040', '#6ac06a', '#f08ab0', '#ffffff'][(k // 3 * 7 + sy) % 6])
                    hh = 4 + (k * 5 + sy) % 4
                    cv.rect(k, sy - hh, 2, hh, col); cv.px(k, sy - hh, mix(col, C('#ffffff'), 0.5))
            for k in range(x + 20, x + w, 34):   # ceiling fluorescent tubes
                cv.rect(k, y + 1, 14, 2, C('#ffffff')); self.E[y + 1:y + 3, k:k + 14] = 1.0
            # posters on the glass
            cv.rect(x + 6, y + h - 26, 14, 18, C('#ff8a3a')); cv.rect(x + 7, y + h - 25, 12, 8, C('#fff4dc'))
            cv.text(x + 7, y + h - 18, '冰', C('#ffffff'), 'zh8'); self.outline_box(x + 6, y + h - 26, 14, 18, C('#8a3a1a'))
            cv.rect(x + 24, y + h - 22, 12, 14, C('#3a8ad0')); cv.rect(x + 25, y + h - 21, 10, 5, C('#bfe4ff'))
            cv.hline(x + 26, y + h - 13, 8, C('#ffffff')); cv.hline(x + 26, y + h - 11, 6, C('#ffffff'))
        if kind != 'konbini':        # warm pendant lamps
            for k in range(x + w // 4, x + w, w // 2):
                cv.vline(k, y, 6, C('#2a2020')); cv.rect(k - 3, y + 6, 7, 3, C('#3a3030')); cv.hline(k - 2, y + 9, 5, C(lamp_col))
                self.E[y + 9, k - 2:k + 3] = 1.0
                yy2, xx2 = np.mgrid[y + 9:min(y + h, y + 34), max(x, k - 18):min(x + w, k + 19)]
                g = np.exp(-(((xx2 - k) / 14.0) ** 2 + ((yy2 - y - 10) / 16.0) ** 2) * 1.2) * 0.35
                self.E[yy2, xx2] = np.maximum(self.E[yy2, xx2], E + g)
        # glass reflection: two sky bands (the shop is dim against the sunny street)
        for (o, wd, kk) in ((0.30, 7, 0.42), (0.52, 3, 0.30)):
            for i in range(h):
                xc = x + int(o * w) + (h - i) // 2
                for j in range(wd):
                    xx_ = xc + j
                    if x <= xx_ < x + w and ((j > 0 and j < wd - 1) or (i + j) % 2 == 0):
                        cv.a[y + i, xx_, :3] = mix(tuple(int(v) for v in cv.a[y + i, xx_]), C('#fff0dc'), kk)[:3]
        # mullions + transom
        for k in range(1, mull):
            mx = x + k * w // mull
            cv.vline(mx - 1, y, h, OUTL); cv.vline(mx, y, h, fr[3]); cv.vline(mx + 1, y, h, fr[1])
        cv.hline(x, y + h, w, fr[4]); cv.hline(x, y + h + 1, w, OUTL)
        self.soft_shadow(x, y, w, 6, 0.35, fade=4)

    def shopfront(self, x0, x1, frame, door_col, awn, sign_txt, sign_bg, sign_fg, kind, sign_border='#e8c070', door_at='right'):
        cv = self.cv
        fr = R(frame, 5)
        yy, xx = np.mgrid[114:GROUND, x0 + 5:x1 - 5]
        t = 2.4 + (M.fbm(xx.astype(float), yy.astype(float), 8, 2, x0) - 0.5) * 0.6 + (np.mod(yy, 9) == 0) * -0.6
        cv.a[114:GROUND, x0 + 5:x1 - 5] = M.apply_ramp(t, fr, xx, yy, True, band=2.0)       # painted wood fascia
        cv.vline(x0 + 5, 114, GROUND - 114, OUTL); cv.vline(x1 - 6, 114, GROUND - 114, OUTL)
        cv.vline(x0 + 6, 114, GROUND - 114, fr[3])
        dw = 26
        dxp = x1 - 12 - dw if door_at == 'right' else x0 + 12
        wx0 = x0 + 12 if door_at == 'right' else x0 + 12 + dw + 8
        wx1 = dxp - 8 if door_at == 'right' else x1 - 12
        self.shop_window(wx0, 128, wx1 - wx0, 44, frame, kind)
        # stall riser below the window
        cv.rect(wx0 - 1, 175, wx1 - wx0 + 2, GROUND - 175, fr[1]); cv.hline(wx0 - 1, 175, wx1 - wx0 + 2, fr[3])
        for k in range(wx0 + 4, wx1 - 2, 12): cv.rect(k, 178, 8, 4, fr[2])
        self.door(dxp, 120, dw, GROUND - 120, door_col)
        self.awning(x0 + 3, 100, x1 - x0 - 6, 13, awn)
        tw = text_width(sign_txt, 'zh8') + 6
        self.sign((wx0 + wx1) // 2 - tw // 2, 116, sign_txt, bg=sign_bg, fg=sign_fg, border=sign_border)
        # step + base AO
        cv.rect(dxp - 3, GROUND - 2, dw + 6, 2, C('#b8b0a4')); cv.hline(dxp - 3, GROUND - 2, dw + 6, C('#e0d8cc'))
        self.ao[GROUND - 8:GROUND, x0:x1] *= np.linspace(1.0, 0.78, 8)[:, None]
        return wx0, wx1, dxp

    # ================================================================== buildings
    def office(self, x0, x1):
        rp = self.wall(x0, x1, 0, '#8f97a8', 'tiles', seed=31, tw=8.0, th=5.0)
        cv = self.cv
        for y in (2, 34, 66):          # glass curtain-wall bands
            cv.rect(x0 + 5, y - 1, x1 - x0 - 14, 24, OUTL)
            self.glass(x0 + 6, y, x1 - x0 - 16, 22, '#ffd9b4', '#4a5a8a', glints=0, k0=0.0)
            for mx in range(x0 + 6, x1 - 10, 16): cv.vline(mx, y, 22, C('#2c3550')); cv.vline(mx + 1, y, 22, C('#6a7aa0'))
            for i in range(20):
                xx = x0 + 44 + i * 2
                cv.px(xx, y + 21 - i, C('#fff6e8')); cv.px(xx + 1, y + 21 - i, C('#fff6e8'))
            # one office blind half down, one plant on a sill (somebody works weekends...)
            cv.rect(x0 + 72, y, 14, 9, C('#d8d4cc')); cv.hline(x0 + 72, y + 8, 14, C('#9a968e'))
            cv.hline(x0 + 6, y + 22, x1 - x0 - 16, rp[5]); cv.hline(x0 + 6, y + 23, x1 - x0 - 16, OUTL)
            self.soft_shadow(x0 + 6, y, x1 - x0 - 16, 3, 0.5, fade=2)
        cv.rect(x0, 92, x1 - x0, 6, rp[1]); cv.hline(x0, 92, x1 - x0, rp[4]); cv.hline(x0, 98, x1 - x0, OUTL)
        cv.text(x0 + 30, 97, '云端大厦  CLOUD TOWER', C('#e9ecf2'), 'zh8')
        dx, dy, dw, dh = 80, 122, 36, 62
        self.A['exit_door'] = (dx, dy, dw, dh)
        cv.rect(dx - 4, dy - 4, dw + 8, dh + 4, OUTL)
        cv.rect(dx - 3, dy - 3, dw + 6, dh + 3, C('#4a505c')); cv.hline(dx - 3, dy - 3, dw + 6, C('#9aa2b2'))
        for yy in range(dh):
            cv.hline(dx, dy + yy, dw, mix(C('#2a2e3a'), C('#14161e'), yy / dh))
        cv.rect(dx + 4, dy + 36, dw - 8, 1, C('#3a4a44')); cv.rect(dx + 7, dy + 24, 1, 12, C('#3a4a44'))
        self.E[dy:dy + dh, dx:dx + dw] = 0.0
        self.T[dy - 3:GROUND, dx - 3:dx + dw + 3] *= 0.15
        self.ao[dy:GROUND, dx:dx + dw] *= 0.35
        sx, sy, sw, sh = dx - 6, dy - 15, 48, 12
        cv.rect(sx - 1, sy - 1, sw + 2, sh + 2, OUTL)
        cv.rect(sx, sy, sw, sh, C('#1e5a36')); cv.rect(sx + 1, sy + 1, sw - 2, sh - 2, C('#2fd07a'))
        man = ["..##.", ".###.", "#.##.", "..#.#", ".#.#.", "#...#"]
        for j, row in enumerate(man):
            for i, ch in enumerate(row):
                if ch == '#': cv.px(sx + 3 + i, sy + 3 + j, C('#f0fff4'))
        cv.text(sx + 11, sy, '安全出口', C('#f0fff4'), 'zh8')
        self.E[sy:sy + sh, sx:sx + sw] = 1.0
        self.A['exit_sign'] = (sx, sy, sw, sh)
        cv.rect(dx - 6, GROUND - 3, dw + 12, 3, C('#a8a49c')); cv.hline(dx - 6, GROUND - 3, dw + 12, C('#d8d2c6')); cv.hline(dx - 6, GROUND - 4, dw + 12, OUTL)
        # drain pipe with brackets
        cv.rect(x0 + 13, 98, 5, GROUND - 98, OUTL); cv.rect(x0 + 14, 98, 3, GROUND - 98, C('#6a7080')); cv.vline(x0 + 14, 98, GROUND - 98, C('#a0a8b8'))
        for by in range(108, GROUND, 22): cv.rect(x0 + 12, by, 7, 2, C('#4a505c'))
        self.soft_shadow(x0 + 18, 98, 3, GROUND - 98, 0.4, fade=2)
        # AC unit + hose
        cv.rect(x0 + 123, 125, 22, 16, OUTL)
        cv.rect(x0 + 124, 126, 20, 14, C('#d8dade')); cv.rect(x0 + 126, 128, 12, 10, C('#9aa0a8')); cv.hline(x0 + 124, 126, 20, C('#f4f4f6'))
        for yy in range(129, 138, 2): cv.hline(x0 + 126, yy, 12, C('#7a8088'))
        cv.ellipse(x0 + 141, 133, 2, 3, C('#7a8088'))
        self.soft_shadow(x0 + 127, 140, 20, 6, 0.3, fade=4, ao=0.8)
        cv.vline(x0 + 140, 140, 10, C('#e8e4dc')); self.drips(x0 + 139, 150, 3, np.random.default_rng(3), 0.8)
        # electric box + meter + taped notices
        cv.rect(x0 + 33, 159, 18, 26, OUTL)
        cv.rect(x0 + 34, 160, 16, 24, C('#3f6a52')); cv.hline(x0 + 33, 160, 18, C('#5e8f72')); cv.rect(x0 + 39, 166, 6, 4, C('#2a4a38'))
        cv.rect(x0 + 37, 174, 3, 2, C('#e8c040')); cv.vline(x0 + 35, 161, 22, C('#4f7a62'))
        self.soft_shadow(x0 + 50, 162, 6, GROUND - 162, 0.3, fade=3)
        cv.rect(x0 + 56, 150, 9, 12, C('#f4f0e4')); cv.hline(x0 + 57, 153, 7, C('#9a9488')); cv.hline(x0 + 57, 155, 5, C('#9a9488'))
        cv.hline(x0 + 56, 150, 3, C('#e8d890')); self.darken(x0 + 64, 162, 0.8)
        cv.rect(x0 + 122, 152, 12, 16, C('#e86a4a')); cv.rect(x0 + 123, 153, 10, 6, C('#fff0d8'))
        cv.hline(x0 + 124, 161, 8, C('#fff0d8')); cv.hline(x0 + 124, 163, 6, C('#fff0d8')); self.outline_box(x0 + 122, 152, 12, 16, C('#8a2a1a'))
        # a bike-share dock sign / bollard by the door, cigarette-butt bin
        cv.rect(x0 + 60, 172, 6, 12, C('#5a5e66')); cv.rect(x0 + 59, 170, 8, 3, C('#7a7e86')); cv.hline(x0 + 59, 170, 8, C('#c8ccd4'))
        self.outline_box(x0 + 59, 170, 8, 14)
        self.ao[GROUND - 8:GROUND, x0:x1] *= np.linspace(1.0, 0.75, 8)[:, None]

    def bakery(self, x0, x1):
        top = 18
        self.wall(x0, x1, top, '#f0d6b0', 'plaster', seed=41, mottle=0.45)
        self.cornice(x0, x1, top, R('#e6c49c', 6), 5)
        cv = self.cv
        # rooftop: water tank + vent stack peeking over the parapet
        cv.rect(x0 + 96, 6, 18, 12, OUTL); cv.rect(x0 + 97, 7, 16, 11, C('#c8b8a4')); cv.hline(x0 + 97, 7, 16, C('#e8dccc'))
        for k in range(x0 + 99, x0 + 112, 4): cv.vline(k, 8, 9, C('#a89884'))
        cv.rect(x0 + 120, 10, 4, 8, C('#8a8a90')); cv.hline(x0 + 119, 10, 6, C('#b8b8c0')); self.outline_box(x0 + 120, 10, 4, 8)
        self.E[5:18, x0 + 95:x0 + 126] = np.where(self.cv.a[5:18, x0 + 95:x0 + 126, 2] < 240, 0.0, self.E[5:18, x0 + 95:x0 + 126])
        self.E[6:18, x0 + 96:x0 + 114] = 0.0; self.E[9:18, x0 + 119:x0 + 125] = 0.0
        rng = np.random.default_rng(41)
        for i, wx in enumerate((x0 + 14, x0 + 60, x0 + 106)):
            self.window(wx, top + 22, 28, 38, curtain='#e8a0a0', box='#ff7aa0', rng=rng, ac=(i == 1))
        self.cornice(x0, x1, 92, R('#d8b088', 6), 4)
        wx0, wx1, dxp = self.shopfront(x0, x1, '#7a4a36', '#8a4a32', ('#d65a4a', '#f6ecdc'), '面包房 BAKERY', '#5a3424', '#ffe6b0', 'bakery')
        # OPEN sign on the door
        cv.rect(dxp + 6, 146, 14, 6, C('#fff4dc')); cv.text(dxp + 6, 144, 'OPEN', C('#c8402a'), 'px5') if False else None
        cv.hline(dxp + 8, 148, 10, C('#c8402a')); cv.hline(dxp + 8, 150, 8, C('#c8402a')); self.outline_box(dxp + 6, 146, 14, 6, C('#5a3424'))
        cv.line(dxp + 9, 145, dxp + 13, 141, C('#3a2a24')); cv.line(dxp + 17, 145, dxp + 13, 141, C('#3a2a24'))
        # A-board menu on the sidewalk + a potted bay tree by the door
        bx = x0 + 130
        cv.line(bx, 184, bx + 4, 161, OUTL); cv.line(bx + 15, 184, bx + 11, 161, OUTL)
        cv.poly([(bx + 1, 184), (bx + 4, 162), (bx + 11, 162), (bx + 14, 184)], C('#7a5030'))
        cv.poly([(bx + 3, 180), (bx + 5, 165), (bx + 10, 165), (bx + 12, 180)], C('#2c3a34'))
        for k, yy in enumerate((168, 171, 174, 177)): cv.hline(bx + 6 - (k > 1), yy, 4 + k % 2, C('#e8e4d4' if k != 1 else '#f0c070'))
        cv.hline(bx + 4, 162, 8, C('#a07040'))
        self.soft_shadow(bx + 14, 168, 8, 16, 0.4, fade=4)
        px = x0 + 112
        cv.rect(px - 1, 172, 11, 12, OUTL); cv.rect(px, 173, 9, 11, C('#b0603e')); cv.hline(px, 173, 9, C('#d8885a')); cv.vline(px + 7, 174, 9, C('#8a4428'))
        cv.vline(px + 4, 160, 13, C('#5a3a24'))
        yy, xx = np.mgrid[146:166, px - 6:px + 16]
        d = ((xx - px - 4.5) / 9.0) ** 2 + ((yy - 155) / 8.5) ** 2
        n = M.fbm(xx.astype(float), yy.astype(float), 3, 2, 77)
        m = d + (n - 0.5) * 0.6 < 1
        t = np.clip(3.2 - ((xx - px + 1) / 9.0) * 0.8 - ((yy - 148) / 9.0) * 1.0 + (n - 0.5) * 1.6, 0, 4)
        G = [C('#1f3b33'), C('#2d5a3f'), C('#467a42'), C('#6e9e45'), C('#a6c25a')]
        img = M.apply_ramp(t, G, xx, yy, True, band=2.0)
        cv.a[146:166, px - 6:px + 16][m] = img[m]
        self.E[146:166, px - 6:px + 16][m] = 0.0
        self.soft_shadow(px + 8, 160, 12, 24, 0.45, fade=5)

    def alley(self, x0, x1):
        cv = self.cv
        top = 56
        yy, xx = np.mgrid[top:GROUND, x0:x1]
        t = 3.2 - (yy - top) / (GROUND - top) * 2.4 + (M.fbm(xx.astype(float), yy.astype(float), 7, 2, 9) - 0.5) * 0.5
        cv.a[top:GROUND, x0:x1] = M.apply_ramp(t, R('#5e5276', 5), xx, yy, True, band=1.4)
        cv.rect(x0 + 5, 119, 12, 66, OUTL); cv.rect(x0 + 6, 120, 10, 64, C('#4a4058')); cv.hline(x0 + 6, 120, 10, C('#6a6080'))
        cv.rect(x0 + 18, 150, 8, 34, C('#544a64'))
        for yy_ in range(80, 180, 11): cv.hline(x0 + 2, yy_, x1 - x0 - 4, C('#2e2838'))
        cv.rect(x0 + 8, 168, 10, 16, C('#3a5a6a')); cv.hline(x0 + 8, 168, 10, C('#5a8a9a')); self.outline_box(x0 + 8, 168, 10, 16)   # bin
        cv.rect(x0 + 19, 176, 7, 8, C('#8a7050')); cv.hline(x0 + 19, 176, 7, C('#a88a60'))                                          # box
        cv.vline(x0 + 27, top, GROUND - top, C('#3a3448')); cv.vline(x0 + 2, top, GROUND - top, C('#2e2838'))
        self.E[top:GROUND, x0:x1] = 0.0
        self.T[top:GROUND, x0:x1] *= 0.0
        self.ao[top:GROUND, x0:x1] *= 0.55
        self.T[GROUND - 10:GROUND, x0:x0 + 10] = 0.7
        self.soft_shadow(x0, GROUND - 10, 12, 10, 0.7, fade=4)

    def flower_shop(self, x0, x1):
        top = 0
        self.wall(x0, x1, top, '#7fb3a8', 'tiles', seed=51, tw=6.0, th=6.0)
        rng = np.random.default_rng(51)
        cv = self.cv
        for row, wy in enumerate((4, 46)):
            for k, wx in enumerate((x0 + 14, x0 + 58, x0 + 102, x0 + 140)):
                if wx + 24 > x1 - 4: continue
                self.window(wx, wy, 22, 30, curtain=['#f2e6c8', '#c8d8f0', None, '#f0c8a0'][(k + row) % 4], box='#ffb050' if row else None,
                            rng=rng, blind='#e8dcc0' if (k + row) % 4 == 2 else None)
        cv.rect(x0 + 49, 85, 86, 5, OUTL); cv.rect(x0 + 50, 86, 84, 3, C('#e8e0d0')); cv.hline(x0 + 50, 86, 84, C('#fffaf0'))
        for bx in range(x0 + 50, x0 + 134, 4): cv.vline(bx, 76, 10, C('#4a5a5a'))
        cv.hline(x0 + 50, 76, 84, C('#6a7a7a')); cv.hline(x0 + 50, 75, 84, OUTL)
        for k in range(x0 + 54, x0 + 132, 9):          # balcony plants + a hanging towel
            cv.rect(k, 81, 5, 4, C('#b0603e')); cv.ellipse(k + 2.5, 79, 3, 2.4, C('#4f8a4a')); cv.px(k + 1, 78, C('#7ab65a'))
        cv.rect(x0 + 100, 76, 9, 12, C('#ffd8a0')); cv.vline(x0 + 108, 76, 12, C('#e8b070'))
        self.soft_shadow(x0 + 54, 90, 86, 6, 0.3, fade=4)
        self.cornice(x0, x1, 92, R('#e8e0d0', 6), 4)
        self.shopfront(x0, x1, '#2f5a4a', '#3f6a5a', ('#4f9a6a', '#f2eedc'), '花店 FLOWERS', '#f4eedc', '#2f5a4a', 'flowers', '#2f5a4a')
        # tiered wooden stand with buckets, hanging baskets from the awning, a watering can
        sx0, sx1 = x0 + 12, x0 + 108
        cv.rect(sx0 - 1, 175, sx1 - sx0 + 2, 9, OUTL); cv.rect(sx0, 176, sx1 - sx0, 8, C('#9a6a44')); cv.hline(sx0, 176, sx1 - sx0, C('#c08a5a'))
        for k in range(sx0 + 2, sx1, 10): cv.vline(k, 177, 7, C('#6a4428'))
        for i, bx in enumerate(range(sx0 + 2, sx1 - 8, 12)):
            cv.rect(bx - 1, 165, 11, 11, OUTL); cv.rect(bx, 166, 9, 10, C('#9aa4b0')); cv.hline(bx, 166, 9, C('#d0d8e0')); cv.vline(bx + 7, 167, 9, C('#6a7480'))
            colr = ['#ff6a8a', '#ffd04a', '#ff9a4a', '#c88aff', '#ffffff', '#ff5a5a', '#ffb0c8'][i % 7]
            cr = R(colr, 5)
            for k in range(-1, 10):
                fx = bx + k; fy = 156 + int(rng.integers(0, 5))
                cv.vline(fx, fy + 2, 166 - fy - 2, C('#3f7a44') if k % 2 else C('#2f5a3a'))
                if rng.random() < 0.75:
                    cv.px(fx, fy, cr[3]); cv.px(fx, fy + 1, cr[1])
                    if rng.random() < 0.4: cv.px(fx, fy - 1, cr[4])
            self.E[150:176, bx - 2:bx + 12] = 0.0
        self.soft_shadow(sx0 + 4, 166, sx1 - sx0 + 4, 18, 0.45, fade=5)
        for hx in (x0 + 16, x0 + 126):
            cv.vline(hx, 115, 6, C('#3a2a24')); cv.ellipse(hx, 123, 5, 3, C('#a8805a')); cv.hline(hx - 4, 121, 9, C('#c8a07a'))
            for j in range(8): cv.px(hx - 4 + j, 125 + (j * 3) % 4, C('#4f8a4a')); cv.px(hx - 3 + j, 126 + (j * 5) % 5, C('#3f7a44'))
            cv.px(hx - 2, 124, C('#ff8ab0')); cv.px(hx + 2, 124, C('#ffd04a'))
        wc = x0 + 112
        cv.rect(wc, 177, 8, 7, C('#5a9a8a')); cv.hline(wc, 177, 8, C('#8acaba')); cv.line(wc + 8, 179, wc + 12, 175, C('#5a9a8a'))
        cv.line(wc + 1, 177, wc + 4, 174, C('#3a6a5a')); cv.line(wc + 4, 174, wc + 7, 177, C('#3a6a5a')); self.outline_box(wc, 177, 8, 7)

    def konbini(self, x0, x1):
        top = 24
        self.wall(x0, x1, top, '#c87a5a', 'brick', seed=61, bw=10.0, bh=4.0)
        self.cornice(x0, x1, top, R('#e0d0c0', 6), 4)
        cv = self.cv
        # rooftop clutter: AC condensers + antenna
        for k, ax in enumerate((x0 + 20, x0 + 44)):
            cv.rect(ax - 1, 11, 18, 13, OUTL); cv.rect(ax, 12, 16, 12, C('#d4d4d0')); cv.hline(ax, 12, 16, C('#f4f4f0'))
            cv.ellipse(ax + 8, 18, 4, 4, C('#8a8a90')); cv.ellipse(ax + 8, 18, 2, 2, C('#5a5a60'))
            self.E[11:24, ax - 1:ax + 17] = 0.0
        cv.vline(x0 + 130, 2, 22, C('#4a4a54')); cv.hline(x0 + 124, 6, 13, C('#4a4a54')); cv.hline(x0 + 126, 10, 9, C('#4a4a54'))
        self.E[2:24, x0 + 130] = 0.0; self.E[6, x0 + 124:x0 + 137] = 0.0; self.E[10, x0 + 126:x0 + 135] = 0.0
        rng = np.random.default_rng(61)
        for i, wx in enumerate((x0 + 14, x0 + 62, x0 + 110)):
            self.window(wx, top + 16, 28, 34, frame='#efe8dc', curtain='#f4e8c0' if i % 2 == 0 else None, rng=rng, ac=True,
                        blind='#d8e4f0' if i == 1 else None)
        cv.rect(x0 + 3, 95, x1 - x0 - 6, 18, OUTL)
        cv.rect(x0 + 4, 96, x1 - x0 - 8, 16, C('#f4f4f0'))
        cv.rect(x0 + 4, 96, x1 - x0 - 8, 3, C('#3a8ad0')); cv.rect(x0 + 4, 109, x1 - x0 - 8, 3, C('#ff8a3a'))
        cv.text(x0 + 16, 99, '便利店  24H', C('#2a4a8a'), 'zh8')
        self.E[96:112, x0 + 4:x1 - 4] = 0.55
        cv.rect(x0 + 4, 112, x1 - x0 - 8, GROUND - 112, C('#5a5e66')); cv.vline(x0 + 4, 112, GROUND - 112, OUTL); cv.vline(x1 - 5, 112, GROUND - 112, OUTL)
        gx0, gx1 = x0 + 8, x1 - 38
        self.shop_window(gx0, 118, gx1 - gx0, GROUND - 124, '#5a5e66', 'konbini', mull=4)
        self.door(x1 - 34, 120, 26, GROUND - 120, '#5a5e66')
        # outside: vending machine-ish freezer, umbrella stand, newspaper rack is the bins (front of the riser)
        fx = gx0 + 46
        cv.rect(fx - 1, 167, 30, 17, OUTL); cv.rect(fx, 168, 28, 16, C('#f4f4f6')); cv.rect(fx + 2, 169, 24, 5, C('#bfe4ff'))
        cv.hline(fx + 2, 169, 24, C('#ffffff')); cv.text(fx + 3, 173, 'ICE', C('#3a8ad0'), 'zh8') if False else None
        cv.rect(fx + 3, 176, 22, 2, C('#3a8ad0')); self.E[169:174, fx + 2:fx + 26] = 0.6
        self.soft_shadow(fx + 28, 170, 6, 14, 0.4, fade=3)
        self.ao[GROUND - 6:GROUND, x0:x1] *= np.linspace(1.0, 0.8, 6)[:, None]

    def apartments(self, x0, x1):
        self.wall(x0, x1, 0, '#e8d2c0', 'siding', seed=71)
        rng = np.random.default_rng(71)
        cv = self.cv
        for row, wy in enumerate((2, 48)):
            for k, wx in enumerate(range(x0 + 14, x1 - 30, 58)):
                self.window(wx, wy, 26, 30, frame='#f4ece0', curtain=['#a8c8e8', '#f0c8c8', '#f4e4b0', None][(k + row) % 4], rng=rng,
                            sill=False)
                by = wy + 38
                cv.rect(wx - 7, by - 1, 42, 5, OUTL)
                cv.rect(wx - 6, by, 40, 3, C('#d8ccc0')); cv.hline(wx - 6, by, 40, C('#f4ece4'))
                cv.rect(wx - 6, by - 10, 40, 1, C('#7a6a64')); cv.hline(wx - 6, by - 11, 40, OUTL)
                for bx in range(wx - 6, wx + 34, 3): cv.vline(bx, by - 10, 10, C('#8a7a74'))
                self.soft_shadow(wx - 2, by + 4, 42, 7, 0.3, fade=4, ao=0.85)
                self.drips(wx - 4, by + 4, 38, rng, 0.9)
                if (k + row) % 2 == 0:
                    cv.hline(wx - 6, by - 19, 40, C('#6a5a54'))
                    for j in range(5):
                        cc = ['#ff8a8a', '#8ab4ff', '#ffe08a', '#ffffff', '#9ae0a0'][(j + k) % 5]
                        cv.rect(wx - 2 + j * 7, by - 18, 5, 7, C(cc)); cv.vline(wx - 2 + j * 7 + 4, by - 18, 7, R(cc, 5)[2])
                        cv.hline(wx - 2 + j * 7, by - 12, 5, R(cc, 5)[1]); cv.px(wx - 1 + j * 7, by - 19, C('#e8e0d8'))
                else:
                    for j in range(4):
                        px = wx - 3 + j * 10
                        cv.rect(px, by - 6, 6, 5, C('#b0603e')); cv.hline(px, by - 6, 6, C('#d8885a'))
                        cv.ellipse(px + 3, by - 9, 4, 3, C('#4f8a4a')); cv.px(px + 2, by - 11, C('#ff7a90')); cv.px(px + 1, by - 10, C('#7ab65a'))
        self.cornice(x0, x1, 92, R('#c8b4a4', 6), 4)
        wx0, wx1, dxp = self.shopfront(x0, x0 + 150, '#6a4a3a', '#5a3a2a', ('#3a5a9a', '#f0e8d8'), '书店 BOOKS', '#3a2a24', '#f4e0b0', 'books', door_at='right')
        # book cart outside
        bx = wx0 + 60
        cv.rect(bx - 1, 170, 30, 9, OUTL); cv.rect(bx, 171, 28, 7, C('#8a5a3a')); cv.hline(bx, 171, 28, C('#b07a50'))
        for k in range(bx + 1, bx + 27, 3):
            cv.rect(k, 165 + (k % 3), 2, 6 - (k % 3), C(['#c84a3a', '#3a6ac8', '#e0b040', '#4a9a5a', '#e8dcc0'][(k // 3) % 5]))
        cv.vline(bx + 2, 178, 6, OUTL); cv.vline(bx + 25, 178, 6, OUTL)
        self.soft_shadow(bx + 6, 179, 28, 5, 0.4, fade=3)
        # garage with a rolled shutter, stickers and a parked scooter
        sx0 = x0 + 160
        if sx0 + 40 < x1:
            ww = min(130, x1 - sx0 - 8)
            cv.rect(sx0 - 1, 111, ww + 2, GROUND - 111, OUTL)
            cv.rect(sx0, 112, ww, GROUND - 112, C('#8a7064'))
            yy, xx = np.mgrid[120:GROUND, sx0 + 4:sx0 + ww - 4]
            t = 2.8 + (np.mod(yy, 3) == 0) * -1.0 + (np.mod(yy, 3) == 1) * 0.4 + (M.fbm(xx.astype(float), yy.astype(float), 12, 2, 5) - 0.5) * 0.7
            cv.a[120:GROUND, sx0 + 4:sx0 + ww - 4] = M.apply_ramp(t, R('#a0a4ae', 5), xx, yy, True, band=2.0)
            cv.rect(sx0 + 4, 118, ww - 8, 3, C('#5a5e66'))
            cv.rect(sx0 + 18, 140, 10, 12, C('#f4e4b0')); cv.hline(sx0 + 19, 143, 8, C('#c84a3a')); cv.hline(sx0 + 19, 146, 6, C('#5a5e66'))
            cv.rect(sx0 + 34, 148, 6, 6, C('#5ab0e0')); cv.rect(sx0 + 92, 136, 14, 6, C('#ffffff')); cv.hline(sx0 + 93, 138, 12, C('#e84a3a'))
            self.soft_shadow(sx0, 112, ww, 8, 0.4, fade=5)
            # scooter
            kx = sx0 + 60
            for wx in (kx, kx + 26):
                cv.ellipse(wx, 179, 5, 5, OUTL); cv.ellipse(wx, 179, 3.6, 3.6, C('#3a3a44')); cv.px(wx, 179, C('#c8c8d0'))
            cv.poly([(kx - 3, 172), (kx + 6, 166), (kx + 14, 166), (kx + 26, 170), (kx + 30, 176), (kx + 4, 176)], C('#e85a4a'))
            cv.hline(kx + 6, 166, 9, C('#ff8a7a')); cv.rect(kx + 8, 162, 10, 4, C('#3a3036')); cv.line(kx - 2, 172, kx + 1, 158, C('#5a5a64'))
            cv.hline(kx - 1, 157, 6, C('#3a3036')); cv.rect(kx + 1, 160, 3, 2, C('#fff4c8'))
            self.soft_shadow(kx + 4, 176, 30, 8, 0.4, fade=4)
        # drain pipe on the seam
        cv.rect(x0 + 152, 0, 5, GROUND, OUTL); cv.rect(x0 + 153, 0, 3, GROUND, C('#b8a898')); cv.vline(x0 + 153, 0, GROUND, C('#e0d4c4'))
        for by in range(12, GROUND, 24): cv.rect(x0 + 151, by, 7, 2, C('#8a7a6a'))

    def vertical_signs(self):
        """two projecting vertical signboards (Chinese street flavour): 休闲足浴 / 牙科."""
        cv = self.cv
        for (x, y, txt, bg, fg, lit) in ((500, 28, '休闲足浴', '#c83a3a', '#fff0c8', 0.0), (664, 104 - 54, '牙科', '#2a6ab0', '#ffffff', 0.0)):
            h = len(txt) * 9 + 6
            cv.rect(x - 4, y + 4, 4, 2, C('#3a3a44')); cv.rect(x - 4, y + h - 8, 4, 2, C('#3a3a44'))
            cv.rect(x - 1, y - 1, 14, h + 2, OUTL); cv.rect(x, y, 12, h, C(bg)); cv.vline(x, y, h, mix(C(bg), C('#ffffff'), 0.3))
            cv.vline(x + 11, y, h, mix(C(bg), C('#000000'), 0.25))
            for i, ch in enumerate(txt): cv.text(x + 2, y + 2 + i * 9, ch, C(fg), 'zh8')
            self.E[y - 1:y + h + 1, x - 4:x + 13] = 0.0
            self.soft_shadow(x + 13, y + 3, 6, h, 0.3, fade=3)

    # ================================================================== ground
    def sidewalk(self):
        w = self.W; cv = self.cv
        yy, xx = np.mgrid[GROUND:CURB, 0:w]
        u, v = xx.astype(np.float64), yy.astype(np.float64)
        rows = [GROUND, 190, 197, 205, 212, 219, CURB]
        t = np.full(u.shape, 3.0)
        tact = np.zeros(u.shape, bool)
        for i, (a, b) in enumerate(zip(rows[:-1], rows[1:])):
            m = (v >= a) & (v < b)
            pw = 12 + i * 2
            off = (i % 2) * pw / 2 + i * 3
            r, ci, _ = M.cell_rand(u + off, np.full_like(v, i), pw, 1, 81 + i)
            base = 3.0 + (r - 0.5) * 0.9 + (M.fbm(u, v, 16, 2, 9) - 0.5) * 0.5
            base = np.where(r > 0.95, 2.0, base)                       # a replaced darker slab here and there
            t = np.where(m, base, t)
            t = np.where(m & (np.mod(u + off, pw) < 1), 1.3, t)          # dark joints
            t = np.where(m & (np.mod(u + off, pw) >= 1) & (np.mod(u + off, pw) < 2), base + 0.6, t)   # lit slab edge
            t = np.where(v == a, 1.5, t)
            t = np.where(v == a + 1, t + 0.5, t)
            if i == 4: tact |= m
        img = M.apply_ramp(t, R('#d8c8b4', 6), xx, yy, True, band=2.2)
        # yellow tactile strip (盲道) with raised bars
        tt = 3.0 + (M.fbm(u, v, 12, 2, 4) - 0.5) * 0.5
        bars = (np.mod(u, 6) >= 1) & (np.mod(u, 6) < 5) & ((v == 214) | (v == 217))
        tt = np.where(bars, 4.2, tt); tt = np.where(bars & np.roll(bars, 1, 0) == False, tt, tt)
        tt = np.where(((v == 215) | (v == 218)) & (np.mod(u, 6) >= 1) & (np.mod(u, 6) < 5), 1.8, tt)
        tt = np.where(np.mod(u, 12) < 1, 1.3, tt); tt = np.where(v == 212, 1.4, tt)
        timg = M.apply_ramp(tt, R('#e0b040', 6), xx, yy, True, band=2.0)
        img[tact] = timg[tact]
        cv.a[GROUND:CURB] = img; self.E[GROUND:CURB] = 0.0
        # cracks, gum spots, stains
        rng = np.random.default_rng(88)
        for _ in range(26):
            x = int(rng.integers(4, w - 4)); y = int(rng.integers(GROUND + 3, CURB - 2))
            if 212 <= y < 219: continue
            for i in range(int(rng.integers(3, 9))):
                self.darken(x, y, 0.78); x += 1; y += int(rng.integers(-1, 2)); y = min(max(y, GROUND + 2), CURB - 1)
        for _ in range(40):
            x = int(rng.integers(4, w - 4)); y = int(rng.integers(GROUND + 3, CURB - 2))
            self.darken(x, y, 0.82); self.darken(x + 1, y, 0.88)
        self.ao[GROUND:GROUND + 6] *= np.linspace(0.55, 1.0, 6)[:, None]

    def road(self):
        w = self.W; cv = self.cv
        yy, xx = np.mgrid[CURB:ROAD, 0:w]
        t = 3.0 + (M.fbm(xx.astype(float), yy.astype(float), 6, 2, 31) - 0.5) * 0.6
        t = np.where(np.mod(xx + 7, 24) < 1, 1.6, t); t = np.where(yy == CURB, 4.6, t); t = np.where(yy == ROAD - 1, 1.0, t)
        cv.a[CURB:ROAD] = M.apply_ramp(t, R('#c0b8ac', 6), xx, yy, True, band=2.0)
        cv.hline(0, ROAD, w, OUTL)
        yy, xx = np.mgrid[ROAD:H, 0:w]
        u, v = xx.astype(float), yy.astype(float)
        t = 2.5 + (M.fbm(u, v, 5, 2, 91) - 0.5) * 1.0 + (M.fbm(u, v, 40, 2, 92) - 0.5) * 0.6
        rng = np.random.default_rng(93)
        for _ in range(7):                    # asphalt repair patches (slightly darker, crisp edges)
            px, py = int(rng.integers(0, w - 40)), int(rng.integers(ROAD + 3, H - 8))
            pw, ph = int(rng.integers(14, 46)), int(rng.integers(5, 12))
            m = (u >= px) & (u < px + pw) & (v >= py) & (v < py + ph)
            t = np.where(m, t - 0.7, t)
            t = np.where(m & ((u == px) | (v == py)), t - 0.5, t)
        img = M.apply_ramp(t, R('#5a5866', 6), xx, yy, True, band=1.6)
        cv.a[ROAD:H] = img
        for x in range(10, w, 46):            # worn lane dashes
            for k in range(24):
                for r in (252, 253):
                    if rng.random() < 0.86: cv.px(x + k, r, C('#e8e4dc') if r == 252 else C('#c8c4bc'))
        for _ in range(18):                   # cracks
            x = int(rng.integers(0, w)); y = int(rng.integers(ROAD + 2, H - 2))
            for i in range(int(rng.integers(4, 14))):
                self.darken(x, y, 0.7); x += int(rng.integers(0, 2)) * (1 if i % 2 else -1) + 1; y += int(rng.integers(-1, 2)); y = min(max(y, ROAD + 1), H - 1)
        for mx in (180, 520, 840):            # manholes
            cv.ellipse(mx, 243, 9, 3.2, OUTL); cv.ellipse(mx, 243, 8, 2.5, C('#4a4652'))
            for k in range(-6, 7, 3): cv.px(mx + k, 243, C('#6a6672'))
            cv.hline(mx - 7, 242, 14, C('#5e5a66'))
        for gx in (60, 390, 700):             # curb drain grates
            cv.rect(gx, ROAD - 1, 14, 3, OUTL)
            for k in range(gx + 1, gx + 13, 2): cv.vline(k, ROAD - 1, 3, C('#3a3640'))
        self.E[CURB:H] = 0.0
        self.ao[ROAD:ROAD + 3] *= np.linspace(0.65, 1.0, 3)[:, None]

    # ================================================================== props
    def street_props(self):
        cv = self.cv
        self.front_base = Canvas(self.W, H)
        for x in (236, 470, 760): self.lamp(x)
        # bench against the flower shop
        bx = 410
        for (yy, c) in ((186, '#a86a3e'), (192, '#a86a3e')):
            cv.rect(bx - 1, yy - 1, 36, 5, OUTL); cv.rect(bx, yy, 34, 3, C(c)); cv.hline(bx, yy, 34, C('#d08a54'))
            for k in range(bx + 4, bx + 34, 8): cv.px(k, yy + 1, C('#8a5030'))
        cv.rect(bx + 2, 195, 2, 6, C('#3a3a44')); cv.rect(bx + 30, 195, 2, 6, C('#3a3a44'))
        cv.rect(bx + 1, 185, 2, 10, C('#3a3a44')); cv.rect(bx + 31, 185, 2, 10, C('#3a3a44'))
        self.soft_shadow(bx + 6, 196, 36, 6, 0.35, fade=3)
        # hydrant
        hx = 540
        cv.rect(hx - 3, 203, 12, 16, OUTL)
        cv.rect(hx, 206, 6, 12, C('#d6372d')); cv.rect(hx - 1, 204, 8, 3, C('#e85a4a')); cv.rect(hx - 2, 210, 10, 2, C('#a82a22'))
        cv.vline(hx, 206, 12, C('#f07a6a')); cv.rect(hx + 2, 202, 2, 2, C('#e85a4a'))
        self.soft_shadow(hx + 5, 214, 12, 5, 0.4, fade=3)
        # parked bicycle
        bk = 700
        for wx in (bk, bk + 18):
            cv.ellipse(wx, 214, 6.5, 6.5, OUTL); cv.ellipse(wx, 214, 5.5, 5.5, C('#2a2a33')); cv.ellipse(wx, 214, 4.4, 4.4, C('#d8c8b4'))
            cv.px(wx, 214, C('#8a8a96'))
            for a in range(0, 360, 45):
                cv.px(wx + int(round(3 * math.cos(math.radians(a)))), 214 + int(round(3 * math.sin(math.radians(a)))), C('#a8a8b4'))
        for (a, b) in (((bk, 214), (bk + 8, 205)), ((bk + 8, 205), (bk + 18, 214)), ((bk + 8, 205), (bk + 16, 205)), ((bk + 16, 205), (bk + 18, 214)), ((bk + 8, 205), (bk + 10, 214))):
            cv.line(*a, *b, C('#3a8ac8'))
        cv.hline(bk + 6, 203, 4, C('#2a2a33')); cv.line(bk + 16, 205, bk + 17, 201, C('#2a2a33')); cv.hline(bk + 15, 200, 4, C('#2a2a33'))
        cv.rect(bk + 15, 202, 5, 3, C('#c8a060'))           # front basket
        self.soft_shadow(bk + 4, 216, 26, 4, 0.45, fade=2)
        # trash + recycling bins by the konbini, a planter by the apartments, stacked crates by the bakery
        for k, (tx, col) in enumerate(((622, '#3a7a5a'), (634, '#3a6ab0'))):
            cv.rect(tx - 1, 171, 12, 15, OUTL); cv.rect(tx, 172, 10, 14, C(col)); cv.rect(tx - 1, 170, 12, 3, R(col, 5)[3]); cv.hline(tx - 1, 170, 12, R(col, 5)[4])
            cv.rect(tx + 3, 175, 4, 2, OUTL); cv.vline(tx + 8, 173, 12, R(col, 5)[1])
        self.soft_shadow(624, 176, 26, 10, 0.4, fade=4)
        for (px, py) in ((812, 172), (264, 174)):
            cv.rect(px - 1, py - 1, 22, GROUND - py + 1, OUTL); cv.rect(px, py, 20, GROUND - py, C('#9a9488')); cv.hline(px, py, 20, C('#c8c2b4'))
            cv.vline(px + 18, py + 1, GROUND - py - 1, C('#7a7468'))
            for j in range(20):
                hh = 4 + int(3 * abs(math.sin(j * 1.7 + px)))
                cv.vline(px + j, py - hh, hh, C('#3f7a44') if j % 3 else C('#5f9e4f')); cv.px(px + j, py - hh, C('#7ab65a'))
                if j % 5 == 2: cv.px(px + j, py - hh - 1, C('#ffe070' if px > 500 else '#ff8ab0'))
            self.soft_shadow(px + 6, py, 22, GROUND - py, 0.45, fade=5)
        cx = 274 - 4
        for (yy, k) in ((176, 0), (168, 1)):
            cv.rect(cx - 1 + k * 2, yy - 1, 16, 9, OUTL); cv.rect(cx + k * 2, yy, 14, 7, C('#b08050')); cv.hline(cx + k * 2, yy, 14, C('#d0a070'))
            cv.hline(cx + k * 2, yy + 3, 14, C('#8a6038'))
        cv.ellipse(cx + 8, 167, 3, 1.5, C('#e0a050')); cv.ellipse(cx + 5, 167, 2, 1.5, C('#c8843e'))
        self.soft_shadow(cx + 14, 168, 6, 16, 0.4, fade=3)
        # fallen leaves scattered on the sidewalk under / right of each tree
        rng = np.random.default_rng(66)
        for tx in (316, 646, 870):
            for _ in range(36):
                lx = int(tx + rng.normal(30, 34)); ly = int(rng.uniform(GROUND + 4, CURB - 1))
                if not (0 <= lx < self.W - 2): continue
                col = C(['#c8a040', '#a8803a', '#7a9a44', '#d8b860', '#9a6a34'][int(rng.integers(0, 5))])
                cv.px(lx, ly, col)
                if rng.random() < 0.6: cv.px(lx + 1, ly, dk(col, 0.25))
        # bollards at the curb (front layer, in front of the walkers' feet)
        f = self.front_base
        for bx in (40, 200, 380, 660):
            f.rect(bx - 1, 211, 6, 15, OUTL); f.rect(bx, 212, 4, 14, C('#5a5e6a')); f.vline(bx, 212, 14, C('#8a909e'))
            f.rect(bx, 215, 4, 2, C('#e8c040'))

    def lamp(self, x, foot=226):
        f = self.front_base if hasattr(self, 'front_base') else self.front
        f.rect(x - 3, foot - 6, 7, 6, OUTL); f.rect(x - 2, foot - 5, 5, 5, C('#3a3a44')); f.hline(x - 2, foot - 5, 5, C('#6a6a7a'))
        f.rect(x - 2, foot - 93, 4, 88, OUTL)
        f.rect(x - 1, foot - 92, 2, 87, C('#4a4a56')); f.vline(x - 1, foot - 92, 87, C('#8a8a9a'))
        f.line(x, foot - 92, x + 12, foot - 98, C('#4a4a56')); f.line(x, foot - 93, x + 12, foot - 99, OUTL)
        f.rect(x + 8, foot - 99, 10, 5, OUTL); f.rect(x + 9, foot - 98, 8, 4, C('#3a3a44'))
        f.rect(x + 10, foot - 94, 6, 2, C('#f4ecd0'))
        f.rect(x + 1, foot - 81, 10, 20, OUTL); f.rect(x + 2, foot - 80, 8, 18, C('#d65a4a')); f.vline(x + 9, foot - 80, 18, C('#a8403a'))
        f.vline(x + 2, foot - 80, 18, C('#f07a6a'))
        f.px(x + 5, foot - 74, C('#ffe6b0')); f.px(x + 6, foot - 72, C('#ffe6b0')); f.px(x + 4, foot - 70, C('#ffe6b0'))
        f.hline(x + 3, foot - 66, 6, C('#ffe6b0'))
        for hh in range(0, 98):
            gx, gy = int(round(x + 0.55 * hh)), int(round(foot - 0.2 * hh))
            if GROUND <= gy < H and 0 <= gx < self.W: self.T[gy, gx:gx + 2] *= 0.35

    # ================================================================== trees (front layer, swaying)
    def tree(self, x, foot=224, seed=0):
        """a street tree: bark-textured trunk with forks + 12-16 leaf masses.  The canopy is stored as cluster
        data and rasterised per sway frame in build_fronts(); trunk / branches / pit and the dappled ground
        shadow are painted once."""
        rng = np.random.default_rng(seed)
        cv = self.cv
        self.A['trees'].append((x, foot))
        # tree pit with an iron grate (bg, on the sidewalk)
        cv.rect(x - 12, foot - 3, 24, 5, OUTL); cv.rect(x - 11, foot - 2, 22, 4, C('#5a4434'))
        for k in range(x - 10, x + 11, 3): cv.vline(k, foot - 2, 4, C('#3a3a40'))
        cv.hline(x - 11, foot - 2, 22, C('#7a7a84'))
        for k in range(-9, 10, 4): cv.px(x + k, foot - 3, C('#5f9e4f'))
        # trunk (front layer)
        crown_y = foot - 60
        bark = [C('#2e1e1c'), C('#4a3028'), C('#6a4632'), C('#8a603e'), C('#b08454')]
        tr = Canvas(self.W, H); tr.a[:] = 0
        for yy in range(crown_y - 8, foot - 1):
            u = (foot - yy) / (foot - crown_y)
            half = 4.2 - 1.4 * u + (1.6 if yy > foot - 6 else 0) + (0.8 if yy > foot - 12 else 0)
            for xx in range(int(math.floor(x - half)), int(math.ceil(x + half)) + 1):
                s = (xx - (x - half)) / (2 * half + 1e-3)           # 0 left (sun) .. 1 right
                n = M.value_noise(np.array([xx * 3.0]), np.array([yy * 0.35]), 1.0, seed)[0]
                lv = 3.4 - s * 2.6 + (n - 0.5) * 1.4
                if (xx * 7 + yy // 3) % 5 == 0: lv -= 1.0          # vertical bark fissures
                lv = int(np.clip(round(lv + (BAYER4[yy % 4, xx % 4] - 0.5) * 0.6), 0, 4))
                tr.px(xx, yy, bark[lv])
        tm = tr.a[..., 3] > 0
        edge = tm & ~(np.roll(tm, 1, 1) & np.roll(tm, -1, 1))
        tr.a[edge] = OUTL
        tr.px(x - 1, foot - 30, bark[0]); tr.px(x, foot - 29, bark[0]); tr.px(x - 1, foot - 28, bark[1])       # a knot
        # forks into the crown (visible through canopy gaps)
        br = []
        for ang, ln, th in ((-62, 30, 2), (-115, 28, 2), (-88, 34, 2), (-40, 22, 1), (-140, 20, 1)):
            a = math.radians(ang + rng.uniform(-8, 8))
            x1, y1 = x + math.cos(a) * ln, crown_y - 4 + math.sin(a) * ln
            br.append((x, crown_y - 4, x1, y1, th))
            for k in range(int(ln)):
                bx_, by_ = x + math.cos(a) * k, crown_y - 4 + math.sin(a) * k
                w_ = th if k < ln * 0.6 else 1
                for dx in range(w_):
                    tr.px(int(round(bx_)) + dx, int(round(by_)), bark[2] if dx == 0 else bark[1])
                tr.px(int(round(bx_)) + w_, int(round(by_)), OUTL)
        self.front_base.a[tr.a[..., 3] > 0] = tr.a[tr.a[..., 3] > 0]
        # canopy clusters: a dome of leaf masses
        cl = []
        cx, cy, rx, ry = x + rng.uniform(-3, 3), crown_y - 30, 50, 33
        for i in range(20):
            a = rng.uniform(0, 2 * math.pi); rr = math.sqrt(rng.uniform(0, 1))
            px_ = cx + math.cos(a) * rr * rx * 0.85; py_ = cy + math.sin(a) * rr * ry * 0.75
            r = rng.uniform(11, 17) * (1.0 - 0.25 * rr)
            cl.append([px_, py_, r, rng.uniform(0, 2 * math.pi)])
        cl += [[cx - rx * 0.6, cy + ry * 0.4, 13, 0.3], [cx + rx * 0.62, cy + ry * 0.3, 14, 1.1], [cx - 6, cy - ry * 0.75, 15, 2.0],
               [cx + rx * 0.25, cy + ry * 0.6, 14, 2.6], [cx - rx * 0.2, cy + ry * 0.62, 13, 0.9]]
        cl.sort(key=lambda c: (-(c[1] - cy) * 0.0 + c[2] * 0.0, c[1] + (c[0] - cx) * 0.25))   # back (top) first
        self.canopies.append(dict(x=x, foot=foot, cx=cx, cy=cy, rx=rx, ry=ry, cl=cl, seed=seed))
        # ground shadow: project the (rest pose) canopy mask along the sun onto the sidewalk -> dappled flecks
        m, _ = self.canopy_raster(self.canopies[-1], None)
        ys, xs = np.nonzero(m)
        hgt = foot - ys
        gx = np.round(xs + 0.55 * hgt).astype(int); gy = np.round(foot - 0.20 * hgt).astype(int)
        sh = np.zeros((H, self.W), np.float32)
        ok = (gx >= 0) & (gx < self.W) & (gy >= GROUND) & (gy < H)
        sh[gy[ok], gx[ok]] = 1.0
        sh = cv2.morphologyEx(sh, cv2.MORPH_CLOSE, np.ones((2, 3), np.uint8))
        sh = cv2.dilate(sh, np.ones((1, 2), np.uint8))
        for hh in range(0, foot - crown_y):                        # trunk shadow
            gx_, gy_ = int(round(x + 0.55 * hh)), int(round(foot - 0.2 * hh))
            if GROUND <= gy_ < H: sh[gy_, gx_:gx_ + 3] = 1.0
        yy, xx = np.mgrid[0:H, 0:self.W]
        fleck = M.value_noise(xx * 1.0, yy * 2.2, 3.0, seed + 17) > 0.74         # sun coins through the leaves
        sh = np.where(fleck & (sh > 0), 0.15, sh)
        self.T *= (1 - 0.80 * sh)

    def canopy_raster(self, c, sway):
        """returns (mask, rgba) full-canvas arrays of one canopy at wind phase `sway` (radians; None = rest).
        Each leaf mass moves rigidly (its noise is sampled in local coordinates) by a ripple that travels
        through the crown: upper / outer masses move more, the whole crown leans a little."""
        x, foot, cx, cy, rx, ry = c['x'], c['foot'], c['cx'], c['cy'], c['rx'], c['ry']
        x0, x1 = int(cx - rx - 26), int(cx + rx + 26); y0, y1 = int(cy - ry - 24), int(cy + ry + 24)
        x0, x1 = max(0, x0), min(self.W, x1); y0, y1 = max(0, y0), min(H, y1)
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
        lev = np.full(yy.shape, -1.0); own = np.full(yy.shape, -1, int)
        G = [C('#1b3434'), C('#24493d'), C('#356640'), C('#4f8640'), C('#7aa848'), C('#b4cc62'), C('#e6dc8c')]
        for i, (px_, py_, r, ph) in enumerate(c['cl']):
            hfac = float(np.clip((foot - py_ - 52) / 60.0, 0, 1))      # higher masses sway more
            if sway is None: ox = oy = 0
            else:
                outer = min(1.0, abs(px_ - cx) / rx)
                ox = round((0.55 + 1.25 * hfac + 0.3 * outer) * math.sin(sway + ph * 0.9) + 0.5 * hfac * math.sin(sway))
                oy = round(0.7 * hfac * math.cos(sway * 1.0 + ph * 0.9 + 0.6)) if hfac > 0.45 else 0
            qx, qy = px_ + ox, py_ + oy
            dx, dy = (xx - qx) / r, (yy - qy) / (r * 0.82)
            lx_, ly_ = xx - ox, yy - oy                                     # mass-local coordinates (rigid move)
            n = M.value_noise(lx_, ly_, 3.0, c['seed'] * 31 + i)
            d = dx * dx + dy * dy + (n - 0.5) * 0.55
            m = d < 1.0
            # sphere shading lit from the upper left + the crown's own shadow (low / right masses darker)
            nz = np.sqrt(np.clip(1 - dx * dx - dy * dy, 0, 1))
            lam = np.clip(-0.55 * dx - 0.62 * dy + 0.55 * nz, -1, 1)
            crown = -0.9 * (qy - cy) / ry - 0.45 * (qx - cx) / rx
            leaf = (M.value_noise(lx_, ly_, 1.6, c['seed'] * 7 + i) - 0.5) * 1.5                # leaf clumps
            v = 2.5 + 2.1 * lam + 1.4 * crown + leaf
            v = np.where(d > 0.80, v - 0.9, v)                            # darker rim on each mass
            lev = np.where(m, v, lev); own = np.where(m, i, own)
        mask = lev >= 0
        # gaps: a few see-through holes inside the crown where masses meet
        hole = (M.value_noise(xx, yy, 4.0, c['seed'] + 99) > 0.80) & mask
        er = cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        hole &= er & (lev < 2.6)
        mask &= ~hole
        img = M.apply_ramp(np.clip(lev, 0, 6), G, xx.astype(int), yy.astype(int), True, band=2.2)
        # silhouette: dark outline on the shadow side (bottom / right), lit sel-out on top / left
        up = np.roll(mask, 1, 0); dn = np.roll(mask, -1, 0); lf = np.roll(mask, 1, 1); rt = np.roll(mask, -1, 1)
        edge = mask & ~(up & dn & lf & rt)
        lit_e = edge & (~up | ~lf)
        img[edge] = G[0]
        img[lit_e] = np.array(G[3], np.uint8)
        # boundaries between masses: thin dark seam where a front mass overlaps a back one (lower side only)
        seam = mask & (own != np.roll(own, -1, 0)) & np.roll(mask, -1, 0) & (lev < 3.2)
        img[seam] = G[1]
        # stray leaves just outside the silhouette (only some edge pixels spawn one)
        rnd = M.value_noise(xx * 3.1, yy * 3.1, 1.0, c['seed'] + 5)
        ring = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~mask & ~hole
        stray = ring & (rnd > 0.72)
        img[stray] = np.array(G[2], np.uint8); mask = mask | stray
        bite = edge & (rnd < 0.16)                                          # notches in the outline
        mask &= ~bite
        M_full = np.zeros((H, self.W), bool); I_full = np.zeros((H, self.W, 4), np.uint8)
        M_full[y0:y1, x0:x1] = mask; I_full[y0:y1, x0:x1] = img; I_full[..., 3] = M_full * 255
        return M_full, I_full

    def build_fronts(self, n):
        sw = [None] if n <= 1 else [2 * math.pi * k / n for k in range(n)]
        out = []
        for s in sw:
            f = self.front_base.a.copy()
            for c in self.canopies:
                m, img = self.canopy_raster(c, s)
                f[m] = img[m]
            out.append(f)
        return out

    def lighting(self):
        yy = WALK_Y - 4
        self.ground = np.clip(self.T[yy - 3:yy + 3].mean(0), 0, 1).astype(np.float32)

    # ================================================================== dynamic pieces
    def door_sprite(self, open_k):
        """steel door leaf (hinge on the left) swung open toward the camera: projected width = w*cos(angle)."""
        dx, dy, dw, dh = self.A['exit_door']
        ang = open_k * math.radians(100)
        pw = int(round(dw * abs(math.cos(ang))))
        th = 3
        ww = max(pw, 1) + (th if open_k > 0.02 else 0)
        s = Sprite(ww + 2, dh)
        cv = s.cv
        base = R('#7a8494', 5)
        if math.cos(ang) >= 0:
            cv.rect(0, 0, max(pw, 1), dh, base[2]); cv.vline(0, 0, dh, base[3]); cv.rect(0, 0, max(pw, 1), 1, base[4])
            if pw > 8:
                cv.rect(int(pw * 0.62), dh // 2 - 1, max(2, int(pw * 0.28)), 2, C('#c8ccd4'))
                cv.rect(3, 6, pw - 6, 1, base[1]); cv.rect(3, dh - 8, pw - 6, 1, base[1])
            if open_k > 0.02: cv.rect(pw, 0, th, dh, base[1])
            if pw > 2: cv.vline(max(pw, 1) - 1, 0, dh, OUTL)
        else:
            cv.rect(0, 0, max(pw, 1), dh, base[1]); cv.rect(pw, 0, th, dh, base[0])
        return s, dx, dy
