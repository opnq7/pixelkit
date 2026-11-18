"""pixelkit.particles - stateless particles (pure functions of t -> parallel-render safe).

DustField: motes floating in a BoxRoom volume.  They are only visible where they sit inside a
sun shaft (brightness = sun transmission at the mote's 3D position) -> the reference's
"glittering dust in the light beams" look.  Rendered into an additive glow buffer at f x native.
"""
import math
import numpy as np, cv2
from .light import sun_T
from .core import C

class DustField:
    def __init__(self, room, n=420, seed=7, z_near=None, z_far=None, speed=1.0, size=(0.5, 1.0)):
        self.room = room
        r = np.random.default_rng(seed)
        zn = z_near or room.D * 0.45; zf = z_far or room.D * 0.99
        self.p0 = np.stack([r.uniform(room.Xl, room.Xr, n), r.uniform(room.Yc, room.Yf, n), r.uniform(zn, zf, n)], 1)
        self.zr = (zn, zf)
        self.v = np.stack([r.normal(0.6, 0.8, n), r.normal(0.9, 0.5, n), r.normal(0, 0.6, n)], 1) * speed  # world u/s
        self.wob = r.uniform(1.0, 4.0, (n, 3)); self.wf = r.uniform(0.08, 0.35, (n, 3)); self.wp = r.uniform(0, 6.28, (n, 3))
        self.tw = r.uniform(0.5, 2.5, n); self.tp = r.uniform(0, 6.28, n)
        self.sz = r.uniform(size[0], size[1], n)
        self.warm = r.uniform(0, 1, n)

    def positions(self, t):
        rm = self.room
        P = self.p0 + self.v * t + self.wob * np.sin(2 * np.pi * self.wf * t + self.wp)
        lo = np.array([rm.Xl, rm.Yc, self.zr[0]]); hi = np.array([rm.Xr, rm.Yf, self.zr[1]])
        return lo + np.mod(P - lo, hi - lo)

    def render(self, t, sun, windows, f=2, gain=1.0, color=(1.0, 0.86, 0.62), min_T=0.04, base=0.0):
        """additive glow buffer (H*f, W*f, 3) float32."""
        rm = self.room
        H, W = int(rm.H * f), int(rm.W * f)
        out = np.zeros((H, W, 3), np.float32)
        if gain <= 0: return out
        P = self.positions(t)
        T = sun_T(rm, sun, windows, P[:, 0], P[:, 1], P[:, 2])
        tw = 0.55 + 0.45 * np.sin(2 * np.pi * self.tw * t + self.tp)
        b = (T * 1.0 + base) * tw * gain
        x, y = rm.project(P[:, 0], P[:, 1], P[:, 2])
        col_w = np.asarray(color, np.float32); col_c = np.array([0.9, 0.95, 1.0], np.float32)
        for i in np.nonzero(b > min_T)[0]:
            s = self.sz[i] * rm.D / P[i, 2]                  # native px
            xs, ys = int(x[i] * f), int(y[i] * f)
            n = max(1, int(round(s * f)))
            if 0 <= xs < W - n and 0 <= ys < H - n:
                c = col_w * self.warm[i] + col_c * (1 - self.warm[i])
                out[ys:ys + n, xs:xs + n] += c * b[i]
        return out

    # ------------------------------------------------------------ output-resolution (preferred)
    _ker = {}
    @classmethod
    def _kernel(cls, r):
        rq = max(0.6, round(r * 4) / 4)
        if rq not in cls._ker:
            n = int(math.ceil(rq * 3)) * 2 + 1
            yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) - n // 2
            k = np.exp(-(xx * xx + yy * yy) / (2 * rq * rq))
            cls._ker[rq] = k.astype(np.float32)
        return cls._ker[rq]

    def render_out(self, t, sun, windows, cam, gain=1.0, px=1.6, color=(1.0, 0.88, 0.68), min_T=0.04,
                   occluder=None, glint_frac=0.10, base=0.0):
        """soft glowing motes drawn at OUTPUT resolution (HD-2D: particles are hi-res, art is pixel).
        occluder: (alpha_native bool, Z_native float) - motes behind opaque mid-layer pixels are hidden.
        Returns (OH, OW, 3) float32 additive buffer."""
        OH, OW = cam.OH, cam.OW
        out = np.zeros((OH, OW, 3), np.float32)
        if gain <= 0: return out
        rm = self.room
        P = self.positions(t)
        T = sun_T(rm, sun, windows, P[:, 0], P[:, 1], P[:, 2])
        tw = 0.55 + 0.45 * np.sin(2 * np.pi * self.tw * t + self.tp)
        b = (T + base) * tw * gain
        x, y = rm.project(P[:, 0], P[:, 1], P[:, 2])
        X, Y = cam.w2o(x, y)
        zs = math.sqrt(max(cam.zoom, 0.2))
        col_w = np.asarray(color, np.float32); col_c = np.array([0.92, 0.95, 1.0], np.float32)
        for i in np.nonzero(b > min_T)[0]:
            if occluder is not None:
                xi, yi = int(x[i]), int(y[i])
                al, Zn = occluder
                if 0 <= xi < al.shape[1] and 0 <= yi < al.shape[0] and al[yi, xi] and not (Zn[yi, xi] > P[i, 2]):
                    continue
            r = px * self.sz[i] * (rm.D / P[i, 2]) * zs
            k = self._kernel(r); n = k.shape[0]; h = n // 2
            xs, ys = int(round(X[i])) - h, int(round(Y[i])) - h
            if xs < 0 or ys < 0 or xs + n > OW or ys + n > OH: continue
            c = (col_w * self.warm[i] + col_c * (1 - self.warm[i])) * b[i]
            out[ys:ys + n, xs:xs + n] += k[..., None] * c
            if (i % 997) / 997.0 < glint_frac and b[i] > 0.5 * gain:      # a few motes flash a 4-point glint
                L = int(r * 4 + 2)
                cx_, cy_ = xs + h, ys + h
                if L < cx_ < OW - L and L < cy_ < OH - L:
                    fall = np.exp(-np.abs(np.arange(-L, L + 1)) / (L * 0.35)).astype(np.float32)[:, None]
                    out[cy_, cx_ - L:cx_ + L + 1] += fall * c * 0.8
                    out[cy_ - L:cy_ + L + 1, cx_] += fall * c * 0.8
        return out

def sparkle_pattern(k):
    """tiny star glyph (k: 0..3 size) as bool mask."""
    pats = {
        0: ["#"],
        1: [".#.", "###", ".#."],
        2: ["..#..", "..#..", "#####", "..#..", "..#.."],
        3: ["...#...", "...#...", "..###..", "#######", "..###..", "...#...", "...#..."],
    }
    p = pats[max(0, min(3, int(k)))]
    return np.array([[c == '#' for c in r] for r in p])

def sparkles(t, spots, f=2, H=270, W=480, color=(1.0, 0.92, 0.7)):
    """spots: list of (x, y, t0, life, size) -> additive buffer.  Stateless twinkles."""
    out = np.zeros((int(H * f), int(W * f), 3), np.float32)
    for (x, y, t0, life, size) in spots:
        u = (t - t0) / life
        if not 0 <= u < 1: continue
        k = math.sin(u * math.pi)
        m = sparkle_pattern(round(size * k))
        h, w = m.shape
        xs, ys = int(x * f) - w // 2, int(y * f) - h // 2
        if xs < 0 or ys < 0 or xs + w > out.shape[1] or ys + h > out.shape[0]: continue
        out[ys:ys + h, xs:xs + w][m] += np.asarray(color, np.float32) * (0.6 + 0.6 * k)
    return out


# ====================================================================== outdoor (side-view sets, native px space)
class Motes2D:
    """pollen / dust drifting in the sunny air of a side-view set (no room volume needed).
    Stateless: positions are pure functions of t.  Visible where `vis` (native (H, W) 0..1, e.g. sun visibility
    or a haze map) is bright, twinkling; drawn as soft hi-res glows at OUTPUT resolution like DustField."""
    def __init__(self, W, H, n=180, seed=11, y_range=(30, 222), wind=(5.0, -1.5), size=(0.6, 1.3)):
        r = np.random.default_rng(seed)
        self.W, self.H = W, H
        self.y0, self.y1 = y_range
        self.p0 = np.stack([r.uniform(0, W, n), r.uniform(self.y0, self.y1, n)], 1)
        self.v = np.stack([r.normal(wind[0], 2.0, n), r.normal(wind[1], 1.2, n)], 1)
        self.wob = r.uniform(1.0, 5.0, (n, 2)); self.wf = r.uniform(0.08, 0.4, (n, 2)); self.wp = r.uniform(0, 6.28, (n, 2))
        self.tw = r.uniform(0.4, 2.0, n); self.tp = r.uniform(0, 6.28, n)
        self.sz = r.uniform(size[0], size[1], n); self.warm = r.uniform(0.3, 1.0, n)

    def positions(self, t):
        P = self.p0 + self.v * t + self.wob * np.sin(2 * np.pi * self.wf * t + self.wp)
        P[:, 0] = np.mod(P[:, 0], self.W)
        P[:, 1] = self.y0 + np.mod(P[:, 1] - self.y0, self.y1 - self.y0)
        return P

    def render_out(self, t, cam, vis=None, gain=1.0, px=1.5, color=(1.0, 0.92, 0.72), glint_frac=0.08):
        OH, OW = cam.OH, cam.OW
        out = np.zeros((OH, OW, 3), np.float32)
        if gain <= 0: return out
        P = self.positions(t)
        X, Y = cam.w2o(P[:, 0], P[:, 1])
        tw = 0.5 + 0.5 * np.sin(2 * np.pi * self.tw * t + self.tp)
        if vis is not None:
            xi = np.clip(P[:, 0].astype(int), 0, vis.shape[1] - 1); yi = np.clip(P[:, 1].astype(int), 0, vis.shape[0] - 1)
            b = vis[yi, xi] * tw * gain
        else:
            b = tw * gain
        zs = math.sqrt(max(cam.zoom, 0.2))
        col_w = np.asarray(color, np.float32); col_c = np.array([0.95, 0.97, 1.0], np.float32)
        for i in np.nonzero(b > 0.03)[0]:
            r = px * self.sz[i] * zs
            k = DustField._kernel(r); n = k.shape[0]; h = n // 2
            xs, ys = int(round(X[i])) - h, int(round(Y[i])) - h
            if xs < 0 or ys < 0 or xs + n > OW or ys + n > OH: continue
            c = (col_w * self.warm[i] + col_c * (1 - self.warm[i])) * b[i]
            out[ys:ys + n, xs:xs + n] += k[..., None] * c
            if (i * 7919 % 1000) / 1000.0 < glint_frac and tw[i] > 0.85:
                L = int(r * 3 + 2); cx_, cy_ = xs + h, ys + h
                if L < cx_ < OW - L and L < cy_ < OH - L:
                    fall = np.exp(-np.abs(np.arange(-L, L + 1)) / (L * 0.35)).astype(np.float32)[:, None]
                    out[cy_, cx_ - L:cx_ + L + 1] += fall * c * 0.7
                    out[cy_ - L:cy_ + L + 1, cx_] += fall * c * 0.7
        return out


LEAF_SHAPES = [np.array([[1, 1]]), np.array([[1], [1]]), np.array([[1, 0], [0, 1]]), np.array([[1, 1], [1, 0]]), np.array([[1]])]

class FallingLeaves:
    """a few leaves let go of the canopies and flutter down to the sidewalk (native-pixel sprites for the mid
    layer, so the scene lights them).  Each leaf loops with its own period; it rests on the ground for a moment,
    then the next fall starts from the canopy again.
        leaves = FallingLeaves([(x, top_y, bottom_y_of_canopy, half_width), ...], ground=(196, 224))
        for rgba, x, y in leaves.sprites(t): mid.put(rgba, x, y, 0)"""
    COLS = [(200, 160, 64), (168, 128, 58), (122, 154, 68), (216, 184, 96), (154, 106, 52)]
    def __init__(self, canopies, ground=(196, 224), per_tree=3, seed=5, wind=6.0):
        r = np.random.default_rng(seed)
        self.L = []
        for (cx, cy0, cy1, hw) in canopies:
            for k in range(per_tree):
                self.L.append(dict(x0=cx + r.uniform(-hw, hw), y0=r.uniform(cy0, cy1), gy=r.uniform(*ground),
                                   vy=r.uniform(9, 15), amp=r.uniform(3, 7), fq=r.uniform(0.35, 0.7), ph=r.uniform(0, 6.28),
                                   per=r.uniform(7, 12), off=r.uniform(0, 12), wind=wind * r.uniform(0.6, 1.3),
                                   col=self.COLS[int(r.integers(0, len(self.COLS)))]))

    def sprites(self, t):
        out = []
        for l in self.L:
            u = (t + l['off']) % l['per']
            fall_t = (l['gy'] - l['y0']) / l['vy']
            if u < fall_t:
                y = l['y0'] + l['vy'] * u
                x = l['x0'] + l['wind'] * u + l['amp'] * math.sin(2 * math.pi * l['fq'] * u + l['ph'])
                shp = LEAF_SHAPES[int(u * 6 + l['ph']) % 4]
            elif u < fall_t + 2.5:
                y = l['gy']; x = l['x0'] + l['wind'] * fall_t + l['amp'] * math.sin(2 * math.pi * l['fq'] * fall_t + l['ph'])
                shp = LEAF_SHAPES[0]
            else:
                continue
            h, w = shp.shape
            a = np.zeros((h, w, 4), np.uint8); a[shp > 0] = (*l['col'], 255)
            out.append((a, int(round(x)), int(round(y))))
        return out


class PixelSwarm:
    """v0.7 midges / fireflies / embers drawn as SINGLE NATIVE PIXELS with emission (so they stay pixel art and the
    bloom gives the glow).  Pure function of t.
        kind='midge'   : a tight swarm dancing in the sun (fast small figure-8 jitter), warm gold.  Place it in front of
                         something darker (far shore), against the bright sky it disappears.
        kind='firefly' : slow drifters that blink on for ~0.7 s every few seconds, yellow-green
    swarm = PixelSwarm(center=(262, 157), spread=(12, 7), n=8);  swarm.draw(cv, E, t, k=1.0)"""
    def __init__(self, center, spread=(14, 9), n=9, seed=5, kind='midge', col=None, e=0.9):
        r = np.random.default_rng(seed)
        self.c = np.asarray(center, np.float32); self.s = np.asarray(spread, np.float32); self.n = n; self.kind = kind
        self.f = r.uniform(0.35, 1.2, (n, 2)) * (1.0 if kind == 'midge' else 0.12)
        self.p = r.uniform(0, 6.28, (n, 2)); self.f2 = r.uniform(1.5, 3.5, (n, 2)) * (1.0 if kind == 'midge' else 0.2)
        self.home = r.uniform(-1, 1, (n, 2)) * 0.6
        self.blink = r.uniform(2.5, 5.5, n); self.bp = r.uniform(0, 5, n)
        self.col = C(col) if col else (C('#ffe2a0') if kind == 'midge' else C('#e8ff8a'))
        self.e = e

    def positions(self, t):
        u = self.home + 0.6 * np.sin(2 * np.pi * self.f * t + self.p) + 0.25 * np.sin(2 * np.pi * self.f2 * t + 2 * self.p)
        return self.c + u * self.s

    def draw(self, cv, E, t, k=1.0):
        if k <= 0: return
        P = self.positions(t)
        H, W = E.shape
        for i, (x, y) in enumerate(P):
            if self.kind == 'firefly':
                ph = (t + self.bp[i]) % self.blink[i]
                b = math.sin(math.pi * min(1.0, ph / 0.7)) if ph < 0.7 else 0.0
            else:
                b = 0.65 + 0.35 * math.sin(2 * math.pi * 3.1 * t + i * 1.7)
            b *= k
            if b < 0.08: continue
            xi, yi = int(round(x)), int(round(y))
            if 0 <= xi < W and 0 <= yi < H:
                cv.px(xi, yi, self.col); E[yi, xi] = max(E[yi, xi], self.e * b)


# ====================================================================== v0.8: soft steam (coffee / tea / noodles)
class SteamWisps:
    """soft rising steam drawn at output resolution as an additive glow buffer (pixel-art steam sprites read as grey
    squiggles under the light rig; real steam is a faint glow).

        sw = SteamWisps((x, y))                       # native px of the cup's mouth
        glow = sw.render_out(t, cam, gain=1.0)        # (OH, OW, 3) -> World.render(glow_out=...)
    """
    def __init__(self, src, rate=5.0, life=1.9, rise=15.0, seed=3, col=(1.0, 0.97, 0.92)):
        self.x, self.y = src; self.rate, self.life, self.rise = rate, life, rise
        self.rng = np.random.default_rng(seed); self.col = np.asarray(col, np.float32)
        n = int(rate * 200)
        self.ph = self.rng.uniform(0, 6.28, n); self.dx = self.rng.normal(0, 0.8, n); self.sz = self.rng.uniform(0.8, 1.3, n)

    def render_out(self, t, cam, gain=1.0):
        OH, OW = cam.OH, cam.OW
        f = 4
        buf = np.zeros((OH // f, OW // f), np.float32)
        s = cam.s / f
        i1 = int(t * self.rate); i0 = max(0, i1 - int(self.life * self.rate) - 1)
        for i in range(i0, i1 + 1):
            if i >= len(self.ph): break
            age = t - i / self.rate
            if not 0 <= age < self.life: continue
            u = age / self.life
            wx = self.x + self.dx[i] * u * 3 + 1.6 * math.sin(self.ph[i] + age * 2.4) * u
            wy = self.y - self.rise * (u ** 0.8)
            X, Y = cam.w2o(wx, wy)
            r = (0.8 + 2.6 * u) * self.sz[i] * s
            a = math.sin(math.pi * min(1.0, u * 1.4)) * (1 - u) * 0.9
            cv2.circle(buf, (int(X / f), int(Y / f)), max(1, int(r)), float(a), -1, lineType=cv2.LINE_AA)
        if buf.max() <= 0: return np.zeros((OH, OW, 3), np.float32)
        buf = cv2.GaussianBlur(buf, (0, 0), max(1.0, 0.9 * s))
        up = cv2.resize(buf, (OW, OH), interpolation=cv2.INTER_LINEAR)
        return up[..., None] * self.col * (0.16 * gain)
