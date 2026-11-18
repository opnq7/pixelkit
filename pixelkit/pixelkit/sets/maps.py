"""pixelkit.sets.maps - painted 480x270 'map' inserts for FlatScene (ACT III).

ParkMap   top-down RPG-overworld view of the pocket park on a 15 px tile grid (32 x 18 cells):
          lawn with mowing stripes, hedge ring with gates, gravel loop, pond, fountain, flower beds, trees,
          benches.  Pathfinding helpers (walkable grid, BFS distance field, shortest path) and holographic
          overlays drawn as emissive pixels (grid sweep, BFS ripple, route arrows) + a tiny top-down Claude.

    pm = ParkMap()
    d = pm.bfs(pm.S)                      # distance field (cells), -1 = blocked / unreached
    route = pm.route([pm.S, *pm.CHECK, pm.S])   # list of cells
    img, E = pm.base.copy(), pm.E.copy(); pm.draw_grid(img, E, k); pm.draw_bfs(img, E, d, wave); ...

CityAerial  oblique 3/4 bird's-eye view of the whole town (roofs + south facades, streets, the park, the
          wedding hall with its red carpet).  .windows = [(x, y)] facade window anchors for speech bubbles.
"""
import math
from collections import deque
import numpy as np, cv2
from ..core import Canvas, C, mix, BAYER4
from .. import materials as M
from .street import R, dk, OUTL

GREENS = [C('#1b3434'), C('#24493d'), C('#356640'), C('#4f8640'), C('#7aa848'), C('#b4cc62'), C('#e6dc8c')]
HOLO = C('#6ad8ff'); HOLO2 = C('#bff4ff'); HOLO_D = C('#2a7ab8'); ROUTE = C('#ffd23f')


def _ramp_img(t, rp, x0, y0, w, h, band=2.0):
    yy, xx = np.mgrid[y0:y0 + h, x0:x0 + w]
    return M.apply_ramp(np.clip(t, 0, len(rp) - 1), rp, xx, yy, True, band=band)


class ParkMap:
    CS, NX, NY = 15, 32, 18
    W, H = 480, 270

    def __init__(self, seed=3):
        self.rng = np.random.default_rng(seed)
        self.cv = Canvas(self.W, self.H, (0, 0, 0, 255))
        self.E = np.zeros((self.H, self.W), np.float32)
        self.block = np.zeros((self.H, self.W), bool)          # obstacle pixels (pathfinding)
        self.shadow = np.zeros((self.H, self.W), np.float32)
        self.paint()
        self.grid = self.walk_grid()

    # ------------------------------------------------------------ painting
    def cell_c(self, c):
        i, j = c
        return i * self.CS + self.CS / 2, j * self.CS + self.CS / 2

    def paint(self):
        cv, W, H = self.cv, self.W, self.H
        yy, xx = np.mgrid[0:H, 0:W]
        u, v = xx.astype(float), yy.astype(float)
        stripe = (((u + v * 0.35) // 22) % 2) * 0.45
        t = 3.3 + stripe + (M.fbm(u, v, 5.0, 2, 1) - 0.5) * 1.2 + (M.fbm(u, v, 40.0, 2, 2) - 0.5) * 0.6
        cv.a[:] = M.apply_ramp(np.clip(t, 0, 6), GREENS, xx, yy, True, band=2.0)
        # gravel loop (rounded rect ring) + a cross path, painted as a mask
        path = np.zeros((H, W), bool)
        def ring(x0, y0, x1, y1, r, wd):
            out = np.zeros((H, W), bool)
            for (a, b, c_, d) in ((x0, y0, x1, y1),):
                cx = np.clip(u, a + r, c_ - r); cy = np.clip(v, b + r, d - r)
                dist = np.hypot(u - cx, v - cy)
                out |= (dist <= r) & (dist >= r - wd) | False
                inner = (u > a + wd) & (u < c_ - wd) & (v > b + wd) & (v < d - wd)
                edge = (u >= a) & (u <= c_) & (v >= b) & (v <= d) & ~inner
                out = edge & (np.hypot(u - cx, v - cy) <= r)
            return out
        path |= ring(52, 40, 430, 236, 34, 14)
        path |= (np.abs(v - 138) < 7) & (u > 52) & (u < 430)                  # east-west cross path
        path |= (np.abs(u - 300) < 7) & (v > 40) & (v < 236)
        path |= (np.abs(v - 138) < 7) & ((u < 60) | (u > 420))                 # out to the two gates
        path |= (np.abs(u - 240) < 7) & (v > 226)                               # south gate (street side)
        g = 3.0 + (M.fbm(u, v, 2.0, 2, 4) - 0.5) * 1.6
        g = np.where(M.value_noise(u, v, 1.0, 5) > 0.85, g + 1.0, g)
        gimg = M.apply_ramp(np.clip(g, 0, 5), R('#d6c4a2', 6), xx, yy, True, band=2.0)
        cv.a[path] = gimg[path]
        er = cv2.erode(path.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        cv.a[path & ~er] = np.array(R('#d6c4a2', 6)[1], np.uint8)
        self.path_mask = path
        # hedge ring (with gaps for the gates)
        hedge = (u < 16) | (u > W - 17) | (v < 14) | (v > H - 16)
        hedge &= ~((np.abs(v - 138) < 9) & ((u < 16) | (u > W - 17)))
        hedge &= ~((np.abs(u - 240) < 9) & (v > H - 16))
        th = 3.6 + (M.fbm(u, v, 3.0, 3, 7) - 0.5) * 2.4
        th = th - np.minimum(np.minimum(u, W - 1 - u), np.minimum(v, H - 1 - v)) * 0.0
        himg = M.apply_ramp(np.clip(th, 0, 6), GREENS, xx, yy, True, band=2.0)
        cv.a[hedge] = himg[hedge]
        he = hedge & ~cv2.erode(hedge.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        cv.a[he & ((u > 15) & (u < W - 16) & (v > 13) & (v < H - 15))] = np.array(GREENS[1], np.uint8)
        self.block |= hedge
        # pond
        pc = (150, 92, 58, 30)
        d = ((u - pc[0]) / pc[2]) ** 2 + ((v - pc[1]) / pc[3]) ** 2 + (M.fbm(u, v, 9, 2, 8) - 0.5) * 0.25
        pond = d < 1.0
        tw = 2.0 + (1 - d) * 1.4 + ((((u * 0.4 + v) // 3) % 5 == 0) * 0.8)
        pimg = M.apply_ramp(np.clip(tw, 0, 4), [C('#2a4a7a'), C('#3a6aa8'), C('#5a8ec8'), C('#8ac0e8'), C('#d8f0ff')], xx, yy, True, 2.0)
        cv.a[pond] = pimg[pond]
        pe = pond & ~cv2.erode(pond.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        cv.a[pe] = np.array(C('#b8a888'), np.uint8)
        self.block |= cv2.dilate(pond.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        for (lx, ly) in ((128, 84), (170, 100), (146, 104)):                    # lily pads
            cv.ellipse(lx, ly, 3, 2, C('#4f8640')); cv.px(lx + 1, ly - 1, C('#ff9ab0'))
        for k in range(14):                                                     # reeds
            a = self.rng.uniform(0, 2 * math.pi)
            rx, ry = pc[0] + math.cos(a) * pc[2] * 0.98, pc[1] + math.sin(a) * pc[3] * 0.98
            for j in range(3): cv.px(int(rx) + j - 1, int(ry) - (j % 2), GREENS[2 + j % 2])
        # fountain (centre of the cross)
        fx, fy = 300, 138
        cv.ellipse(fx, fy + 2, 17, 12, (0, 0, 0, 0)) if False else None
        cv.ellipse(fx, fy, 16, 12, OUTL); cv.ellipse(fx, fy, 15, 11, C('#d8d0c4')); cv.ellipse(fx, fy, 12, 8.5, C('#5a8ec8'))
        cv.ellipse(fx, fy - 1, 4, 3, C('#e8e4dc')); cv.ellipse(fx, fy - 2, 2, 1.5, C('#ffffff'))
        for k in range(8):
            a = k * math.pi / 4
            cv.px(int(fx + math.cos(a) * 8), int(fy + math.sin(a) * 6), C('#d8f0ff'))
        self.block |= (((u - fx) / 18) ** 2 + ((v - fy) / 14) ** 2) < 1
        self.fountain = (fx, fy)
        # flower beds
        self.beds = [(386, 78, 22, 14), (96, 196, 30, 13), (210, 186, 18, 12)]
        for (bx, by, rx, ry) in self.beds:
            m = (((u - bx) / rx) ** 2 + ((v - by) / ry) ** 2) < 1
            cv.a[m] = np.array(C('#6a4a34'), np.uint8)
            fl = m & (M.value_noise(u, v, 1.0, bx) > 0.45)
            cols = np.array([C(c)[:4] for c in ('#ff8ab0', '#ffd04a', '#ffffff', '#c88aff', '#ff6a6a')], np.uint8)
            idx = (M.value_noise(u * 3.0, v * 3.0, 1.0, by) * 4.99).astype(int)
            cv.a[fl] = cols[idx[fl]]
            ring_ = m & ~cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            cv.a[ring_] = np.array(C('#e8e0d0'), np.uint8)
            self.block |= m
        # benches (top-down: slats), A = where Claude lay
        self.benches = [(90, 222, 'h'), (200, 222, 'h'), (360, 222, 'h'), (448, 100, 'v')]
        for (bx, by, o) in self.benches:
            if o == 'h':
                cv.rect(bx - 12, by - 4, 24, 8, OUTL); cv.rect(bx - 11, by - 3, 22, 6, C('#b07a4a'))
                for k in (by - 2, by, by + 2): cv.hline(bx - 11, k, 22, C('#d09a64') if k != by + 2 else C('#8a5a34'))
            else:
                cv.rect(bx - 4, by - 12, 8, 24, OUTL); cv.rect(bx - 3, by - 11, 6, 22, C('#b07a4a'))
                for k in (bx - 2, bx, bx + 2): cv.vline(k, by - 11, 22, C('#d09a64'))
        # trees (canopy + offset shadow), trunks block
        trees = [(70, 52, 17), (112, 150, 15), (40, 238, 13), (232, 60, 16), (262, 214, 14), (350, 54, 15), (410, 196, 16),
                 (446, 236, 12), (196, 120, 13), (372, 132, 12), (448, 40, 13), (30, 100, 12), (330, 236, 11)]
        self.trees = trees
        sh = np.zeros((H, W), np.float32)
        for (tx, ty, r) in trees:
            sh = np.maximum(sh, ((((u - tx - r * 0.5) / (r * 1.05)) ** 2 + ((v - ty - r * 0.45) / (r * 0.9)) ** 2) < 1) * 1.0)
        self.shadow = sh
        a = cv.a.astype(np.float32); a[..., :3] *= (1 - 0.38 * sh[..., None]); cv.a = np.clip(a, 0, 255).astype(np.uint8)
        for (tx, ty, r) in sorted(trees, key=lambda q: q[1]):
            n = M.fbm(u, v, 3.5, 2, tx)
            d = ((u - tx) / r) ** 2 + ((v - ty) / r) ** 2 + (n - 0.5) * 0.5
            m = d < 1
            lam = np.clip(-0.6 * (u - tx) / r - 0.7 * (v - ty) / r + 0.6 * np.sqrt(np.clip(1 - d, 0, 1)), -1, 1)
            tv = 3.0 + 2.2 * lam + (M.value_noise(u, v, 2.0, ty) - 0.5) * 1.4
            img = M.apply_ramp(np.clip(tv, 0, 6), GREENS, xx, yy, True, band=2.0)
            cv.a[m] = img[m]
            e = m & ~cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            cv.a[e] = np.array(GREENS[0], np.uint8)
            self.block |= (((u - tx) / (r * 0.75)) ** 2 + ((v - ty) / (r * 0.75)) ** 2) < 1
        # lamp posts (tiny) + checkpoints
        self.S = self.cell_of(90, 214)
        self.CHECK = [self.cell_of(150, 128), self.cell_of(386, 98), self.cell_of(300, 162)]
        self.CHECK_NAMES = ['池塘', '花坛', '喷泉']

    def cell_of(self, x, y): return (int(x // self.CS), int(y // self.CS))

    # ------------------------------------------------------------ pathfinding
    def walk_grid(self):
        g = np.zeros((self.NX, self.NY), bool)
        for i in range(self.NX):
            for j in range(self.NY):
                x0, y0 = i * self.CS, j * self.CS
                sub = self.block[y0 + 3:y0 + self.CS - 3, x0 + 3:x0 + self.CS - 3]
                g[i, j] = sub.mean() < 0.25
        return g

    def bfs(self, start):
        d = -np.ones((self.NX, self.NY), int); par = {}
        q = deque([start]); d[start] = 0
        while q:
            c = q.popleft()
            for (di, dj) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + di, c[1] + dj)
                if 0 <= n[0] < self.NX and 0 <= n[1] < self.NY and self.grid[n] and d[n] < 0:
                    d[n] = d[c] + 1; par[n] = c; q.append(n)
        return d, par

    def path(self, a, b):
        d, par = self.bfs(a)
        if d[b] < 0: return [a]
        out = [b]
        while out[-1] != a: out.append(par[out[-1]])
        return out[::-1]

    def route(self, pts):
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]): out += self.path(a, b)[1:]
        return out

    # ------------------------------------------------------------ overlays (emissive)
    def draw_grid(self, img, E, k, col=HOLO):
        """grid lines sweeping in from the left: k 0..1"""
        if k <= 0: return
        xm = k * (self.W + 60)
        for i in range(self.NX + 1):
            x = i * self.CS
            if x > xm: break
            img[:, min(x, self.W - 1), :3] = mix(tuple(int(c) for c in img[0, min(x, self.W - 1)]), col, 0.0)[:3] if False else img[:, min(x, self.W - 1), :3]
            col_ = np.array(col[:3], np.float32)
            xs = min(x, self.W - 1)
            ys = np.arange(0, self.H)
            on = (ys % 3 != 2)
            img[ys[on], xs, :3] = (img[ys[on], xs, :3] * 0.45 + col_ * 0.55).astype(np.uint8)
            E[ys[on], xs] = np.maximum(E[ys[on], xs], 0.45)
        for j in range(self.NY + 1):
            y = min(j * self.CS, self.H - 1)
            xs = np.arange(0, int(min(xm, self.W)))
            on = (xs % 3 != 2)
            col_ = np.array(col[:3], np.float32)
            img[y, xs[on], :3] = (img[y, xs[on], :3] * 0.45 + col_ * 0.55).astype(np.uint8)
            E[y, xs[on]] = np.maximum(E[y, xs[on]], 0.45)
        # blocked cells get a faint red cross-hatch once the grid has passed
        for i in range(self.NX):
            if (i + 1) * self.CS > xm: break
            for j in range(self.NY):
                if not self.grid[i, j]:
                    x0, y0 = i * self.CS, j * self.CS
                    for q in range(2, self.CS - 2, 3):
                        img[y0 + q, x0 + q, :3] = (img[y0 + q, x0 + q, :3] * 0.5 + np.array([255, 110, 110]) * 0.5).astype(np.uint8)

    def draw_bfs(self, img, E, d, wave, front_w=1.6):
        """BFS ripple: cells with distance <= wave fill pale blue, the wave front glows."""
        if wave <= 0: return
        for i in range(self.NX):
            for j in range(self.NY):
                dd = d[i, j]
                if dd < 0 or dd > wave: continue
                x0, y0 = i * self.CS + 1, j * self.CS + 1
                age = wave - dd
                k = 0.85 if age < front_w else 0.30
                col = np.array(HOLO2[:3] if age < front_w else HOLO[:3], np.float32)
                reg = img[y0:y0 + self.CS - 1, x0:x0 + self.CS - 1, :3].astype(np.float32)
                yy, xx = np.mgrid[0:self.CS - 1, 0:self.CS - 1]
                dith = (BAYER4[yy % 4, xx % 4] < (0.5 if age >= front_w else 0.9))
                reg[dith] = reg[dith] * (1 - k) + col * k
                img[y0:y0 + self.CS - 1, x0:x0 + self.CS - 1, :3] = reg.astype(np.uint8)
                E[y0:y0 + self.CS - 1, x0:x0 + self.CS - 1][dith] = np.maximum(E[y0:y0 + self.CS - 1, x0:x0 + self.CS - 1][dith], 0.55 if age < front_w else 0.22)

    def draw_route(self, img, E, cells, u, col=ROUTE, t=0.0):
        """route as a thick dashed golden line with chevrons, drawn up to fraction u (0..1); dashes crawl with t."""
        if u <= 0 or len(cells) < 2: return
        pts = [self.cell_c(c) for c in cells]
        seg = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts[:-1], pts[1:])]
        L = sum(seg); lim = L * min(1.0, u); acc = 0.0
        cv = Canvas(self.W, self.H); cv.a = img
        for (a, b), s in zip(zip(pts[:-1], pts[1:]), seg):
            if acc > lim: break
            n = int(s)
            for k in range(n):
                if acc + k > lim: break
                p = (acc + k + t * 30) % 10
                if p < 6:
                    x = a[0] + (b[0] - a[0]) * k / s; y = a[1] + (b[1] - a[1]) * k / s
                    for (ox, oy) in ((0, 0), (1, 0), (0, 1), (1, 1)):
                        xi, yi = int(x) + ox - 1, int(y) + oy - 1
                        if 0 <= xi < self.W and 0 <= yi < self.H:
                            img[yi, xi, :3] = col[:3]; E[yi, xi] = 0.9
            acc += s

    def draw_flags(self, img, E, k=1.0, t=0.0, done=()):
        cv = Canvas(self.W, self.H); cv.a = img
        for n, (c, name) in enumerate(zip(self.CHECK, self.CHECK_NAMES)):
            if k <= n * 0.2: continue
            x, y = self.cell_c(c)
            x, y = int(x), int(y)
            cv.vline(x, y - 12, 12, OUTL)
            col = C('#5aff8a') if n in done else C('#ff5a4a')
            wav = int(t * 6 + n) % 2
            cv.rect(x + 1, y - 12, 6, 4, col); cv.px(x + 7, y - 11 + wav, col)
            E[y - 12:y - 8, x + 1:x + 8] = 0.6
            cv.ellipse(x, y, 3, 1.5, (0, 0, 0, 120))
            cv.text(x - 7, y + 1, name, C('#ffffff'), 'zh8', outline=OUTL)


def claude_mini(direction='right', phase=0, glow=1.0):
    """tiny top-down / overworld Claude (12 x 14): cream head box with the dark screen + orange eyes, coral body."""
    cv = Canvas(12, 14); E = np.zeros((14, 12), np.float32)
    cv.rect(2, 9, 8, 4, C('#b0555a')); cv.rect(3, 9, 6, 3, C('#d8776e')); cv.hline(3, 9, 6, C('#f2a296'))
    leg = phase % 2
    cv.rect(3, 12 + leg, 2, 2 - leg, C('#843a48')); cv.rect(7, 13 - leg, 2, 1 + leg, C('#843a48'))
    cv.rect(0, 0, 12, 10, C('#3b3042')); cv.rect(1, 1, 10, 8, C('#ebe5dd')); cv.hline(1, 1, 10, C('#faf6ef'))
    ex = {'right': 1, 'left': -1, 'up': 0, 'down': 0}[direction]
    if direction != 'up':
        cv.rect(2, 3, 8, 5, C('#1a1726'))
        for x in (4, 7):
            cv.rect(x + ex, 4, 1, 2, C('#ffe6c4')); E[4:6, x + ex] = 1.0 * glow
    else:
        cv.rect(2, 2, 8, 6, C('#cbc3d0'))
    cv.px(6, 0, C('#d9a64e')); cv.px(6, -1 + 1, C('#d9a64e'))
    return cv.a, E


class CityAerial:
    """oblique bird's-eye view of the town (480 x 270).  Painted once; .windows = facade window anchors."""
    W, H = 480, 270

    P = 24                                    # painting margin (blocks bleed off the frame), cropped afterwards

    def __init__(self, seed=11):
        self.rng = np.random.default_rng(seed)
        P = self.P
        self.cv = Canvas(self.W + 2 * P, self.H + 2 * P, (0, 0, 0, 255))
        self.E = np.zeros((self.H + 2 * P, self.W + 2 * P), np.float32)
        self.windows = []
        self.people = []
        self.paint()
        self.cv.a = np.ascontiguousarray(self.cv.a[P:P + self.H, P:P + self.W]); self.E = np.ascontiguousarray(self.E[P:P + self.H, P:P + self.W])
        self.windows = [(x - P, y - P) for (x, y) in self.windows if P + 4 <= x < P + self.W - 4 and P + 8 <= y < P + self.H - 2]
        self.people = [(x - P, y - P) for (x, y) in self.people if P <= x < P + self.W and P <= y < P + self.H]
        self.bench_anchor = (self.bench_anchor[0] - P, self.bench_anchor[1] - P)

    def paint(self):
        cv, rng, P = self.cv, self.rng, self.P
        W, H = self.W + 2 * P, self.H + 2 * P
        yy, xx = np.mgrid[0:H, 0:W]
        u, v = xx.astype(float), yy.astype(float)
        t = 3.0 + (M.fbm(u, v, 4, 2, 21) - 0.5) * 0.8
        cv.a[:] = M.apply_ramp(t, R('#8a8494', 6), xx, yy, True, 2.0)            # asphalt everywhere first
        # sidewalks: lighter bands along every block edge are painted with the blocks
        rows = [(y0 + P, y1 + P) for (y0, y1) in ((-14, 50), (62, 128), (142, 206), (220, 290))]   # block rows
        cols = [(x0 + P, x1 + P) for (x0, x1) in ((-20, 96), (108, 226), (238, 352), (364, 500))]
        for bi, (y0, y1) in enumerate(rows):
            for bj, (x0, x1) in enumerate(cols):
                cv.rect(x0 - 3, y0 - 3, x1 - x0 + 6, y1 - y0 + 6, C('#cfc4b4'))
                cv.hline(x0 - 3, y1 + 3, x1 - x0 + 6, C('#a89c8c'))
                if (bi, bj) == (2, 1): self.park(x0, y0, x1, y1)
                else: self.block(x0, y0, x1, y1, seed=bi * 10 + bj, hall=(bi, bj) == (2, 2))
        # lane dashes + crossings
        for y in (56 + P, 135 + P, 213 + P):
            for x in range(0, W, 14): cv.hline(x, y, 7, C('#e8e2d4'))
        for x in (102 + P, 232 + P, 358 + P):
            for y in range(0, H, 14): cv.vline(x, y, 7, C('#e8e2d4'))
        # far haze at the top
        hz = np.clip(1 - (v - P) / 70.0, 0, 1) ** 1.5 * 0.45
        a = cv.a.astype(np.float32); a[..., :3] = a[..., :3] * (1 - hz[..., None]) + np.array([232, 214, 228]) * hz[..., None]
        cv.a = a.astype(np.uint8)
        # street trees along the sidewalks
        for (y0, y1) in rows:
            for x in range(8, W - 8, 23):
                ty = y1 + 4
                if any(a - 2 <= x <= b + 2 for (a, b) in ((102 + P - 6, 102 + P + 6), (232 + P - 6, 232 + P + 6), (358 + P - 6, 358 + P + 6))): continue
                cv.ellipse(x + 2, ty + 1, 4, 2.5, (40, 40, 50, 255))
                cv.ellipse(x, ty - 1, 4, 3.4, GREENS[2]); cv.ellipse(x - 1, ty - 2, 2.5, 2, GREENS[4]); cv.px(x - 2, ty - 3, GREENS[5])
        # tiny people on the sidewalks
        for _ in range(70):
            x, y = int(rng.integers(4, W - 4)), int(rng.choice([58, 60, 131, 139, 209, 217])) + P
            c = C(['#3a4258', '#c84a3a', '#e8e0d0', '#5a6a8a', '#e8a0a0'][int(rng.integers(0, 5))])
            cv.px(x, y - 1, C('#f1c7a0')); cv.px(x, y, c); self.people.append((x, y - 2))

    def building(self, x, base, w, h, d, wall, roof, seed=0, kind=None):
        """roof (top face, depth d) above a south facade of height h; base = sidewalk row."""
        cv, rng = self.cv, np.random.default_rng(abs(seed))
        rp, rr = R(wall, 6), R(roof, 6)
        fy0 = base - h
        # cast shadow to the right on whatever is behind / beside
        sh_w = max(3, h // 3)
        reg = cv.a[max(0, fy0 - d + 2):base, x + w:min(cv.a.shape[1], x + w + sh_w), :3]
        reg[:] = (reg.astype(np.float32) * 0.72).astype(np.uint8)
        cv.rect(x - 1, fy0 - d - 1, w + 2, h + d + 2, OUTL)
        # roof
        t = 3.4 + (M.fbm(np.arange(w)[None, :] + x + 0.0, np.arange(d)[:, None] + fy0 + 0.0, 6, 2, seed) - 0.5) * 0.8
        cv.a[fy0 - d:fy0, x:x + w] = _ramp_img(t, rr, x, fy0 - d, w, d)
        cv.hline(x, fy0 - d, w, rr[5]); cv.hline(x, fy0 - 1, w, rr[2])
        if kind == 'tiles':
            for k in range(fy0 - d + 2, fy0 - 1, 3): cv.hline(x + 1, k, w - 2, rr[2])
        else:
            for _ in range(max(1, w * d // 260)):                                     # roof clutter
                kx, ky = int(rng.integers(x + 2, max(x + 3, x + w - 8))), int(rng.integers(fy0 - d + 2, max(fy0 - d + 3, fy0 - 6)))
                kind_ = rng.integers(0, 4)
                if kind_ == 0:   # water tank
                    cv.rect(kx, ky, 6, 5, OUTL); cv.rect(kx + 1, ky + 1, 4, 3, C('#d8d0c4')); cv.hline(kx + 1, ky + 1, 4, C('#f4ecdc'))
                elif kind_ == 1:  # AC units
                    cv.rect(kx, ky, 5, 3, C('#e8e4dc')); cv.px(kx + 3, ky + 1, C('#8a8a96'))
                elif kind_ == 2:  # solar panel
                    cv.rect(kx, ky, 7, 4, C('#2a3a6a')); cv.hline(kx, ky, 7, C('#5a7ab8')); cv.vline(kx + 3, ky, 4, C('#5a7ab8'))
                else:            # rooftop garden
                    for q in range(3): cv.px(kx + q * 2, ky + 1, GREENS[3 + q % 2]); cv.px(kx + q * 2 + 1, ky, GREENS[4])
        # facade
        t = 3.0 + (M.fbm(np.arange(w)[None, :] + x + 0.0, np.arange(h)[:, None] + fy0 + 0.0, 8, 2, seed + 1) - 0.5) * 0.6
        cv.a[fy0:base, x:x + w] = _ramp_img(t - 0.6, rp, x, fy0, w, h)
        cv.vline(x, fy0, h, rp[4]); cv.vline(x + w - 1, fy0, h, rp[1])
        floors = max(1, (h - 3) // 6)
        for f in range(floors):
            wy = fy0 + 2 + f * 6
            if wy + 3 > base - 1: break
            for wx in range(x + 2, x + w - 3, 5):
                lit = rng.random() < 0.12
                col = C('#ffe6a8') if lit else (C('#6a7aa8') if rng.random() < 0.7 else C('#f4e4c8'))
                cv.rect(wx, wy, 3, 3, col); cv.hline(wx, wy, 3, mix(col, C('#ffffff'), 0.35))
                if lit: self.E[wy:wy + 3, wx:wx + 3] = 0.6
                self.windows.append((wx + 1, wy))
        cv.hline(x, base - 1, w, rp[1])
        if kind == 'awning':
            for k in range(w): cv.vline(x + k, base - 6, 3, C('#2f5a4a') if (k // 3) % 2 == 0 else C('#f4eadc'))

    def block(self, x0, y0, x1, y1, seed=0, hall=False):
        rng = np.random.default_rng(seed + 50)
        walls = ['#efe0c4', '#bcc8dc', '#e8d2c0', '#c87a5a', '#8fb8a0', '#e8c8a0', '#f0d8d0', '#a8b4c8']
        roofs = ['#a85a44', '#7a8494', '#5a7a6a', '#c8a070', '#8a6a8a', '#b8b0a0']
        # two rows of buildings per block: back row (taller) and the front row on the block's south edge
        for row, (base, hmin, hmax) in enumerate(((y0 + (y1 - y0) // 2 - 2, 9, 15), (y1, 8, 13))):
            x = x0
            while x < x1 - 8:
                w = int(rng.integers(18, 34)); w = min(w, x1 - x)
                h = int(rng.integers(hmin, hmax)); d = int(rng.integers(14, 22)) if row == 0 else int(rng.integers(12, 18))
                if rng.random() < 0.12: h += int(rng.integers(6, 12))                     # the odd taller block
                if base - h - d < y0 - 4 and row == 0: d = max(5, base - h - (y0 - 4))
                kind = 'awning' if (row == 1 and rng.random() < 0.3) else ('tiles' if rng.random() < 0.35 else None)
                self.building(x, base, w, h, d, walls[int(rng.integers(0, len(walls)))], roofs[int(rng.integers(0, len(roofs)))],
                              seed=seed * 100 + x, kind=kind)
                x += w + int(rng.integers(0, 3))
        if hall:   # the wedding hall: white, red carpet, gold dot - front row centre
            cx = (x0 + x1) // 2
            self.building(cx - 18, y1, 36, 18, 12, '#f4eee6', '#e8dcd0', seed=999)
            cv = self.cv
            cv.rect(cx - 3, y1, 6, 4, C('#c8323a')); cv.px(cx, y1 - 18 - 6, C('#e8c070'))
            for (bx, col) in ((cx - 14, '#ff8ab0'), (cx + 13, '#ffffff'), (cx - 12, '#f2c94c')):
                cv.px(bx, y1 - 4, C(col)); cv.px(bx, y1 - 5, C(col))

    def park(self, x0, y0, x1, y1):
        cv = self.cv
        yy, xx = np.mgrid[y0:y1, x0:x1]
        t = 3.4 + ((((xx + yy * 0.35) // 9) % 2) * 0.4) + (M.fbm(xx.astype(float), yy.astype(float), 4, 2, 31) - 0.5)
        cv.a[y0:y1, x0:x1] = M.apply_ramp(np.clip(t, 0, 6), GREENS, xx, yy, True, 2.0)
        cv.ellipse((x0 + x1) // 2 - 22, (y0 + y1) // 2 - 6, 18, 9, C('#3a6aa8')); cv.ellipse((x0 + x1) // 2 - 24, (y0 + y1) // 2 - 8, 8, 3, C('#8ac0e8'))
        for k in range(x0 + 6, x1 - 4, 3): cv.px(k, y1 - 10, C('#d6c4a2')); cv.px(k, y1 - 9, C('#d6c4a2'))
        rng = np.random.default_rng(32)
        for _ in range(16):
            tx, ty, r = int(rng.integers(x0 + 6, x1 - 6)), int(rng.integers(y0 + 6, y1 - 6)), int(rng.integers(5, 9))
            cv.ellipse(tx + 2, ty + 2, r, r * 0.8, (20, 40, 30, 255))
            cv.ellipse(tx, ty, r, r * 0.85, GREENS[3]); cv.ellipse(tx - 1, ty - 1, r * 0.6, r * 0.5, GREENS[4]); cv.px(tx - 2, ty - 2, GREENS[5])
        bx, by = x0 + 30, y1 - 14
        cv.rect(bx, by, 8, 2, C('#b07a4a')); self.bench_anchor = (bx + 4, by - 1)
        for k in range(4): self.people.append((x0 + 20 + k * 22, y1 - 12))
