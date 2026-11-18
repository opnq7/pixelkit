"""pixelkit.blocks - chat-message bricks that fall, bounce, pile up and get bonked off heads.

Deterministic fixed-step simulation (precomputed once, then sampled per frame => safe for parallel
rendering).  Bricks live in depth "lanes" (desk top, floor rows ...) with a heightmap each.

    lanes = {'desk': Lane(Z=334, y=168, x0=166, x1=334), 'floor': Lane(Z=300, y=222)}
    sim = Sim(lanes, g=900)
    b = sim.add(t=3.6, brick=brick(['周报'], 0), x=290, lane='desk', y0=-30)
    sim.add(t=4.6, brick=..., x=236, lane='desk', bonk=dict(y=113, vx=80, vy=-240, to='floor'))
    sim.run(t_end=12)
    for b, x, y, sq in sim.at(tau): ...     # tau = simulation time (apply freezes via time warp)
    sim.events -> [(t, 'land'|'bonk', dict)]  (drive SFX + reactions)
"""
import numpy as np, math
from .core import Canvas, C, mix, text_width
from .scene import Sprite

COLS = [  # fill, light, dark, outline
    ('#2f9fc4', '#6fd0ea', '#1f7193', '#163e52'),   # 0 cyan
    ('#4f7fe0', '#86a9f2', '#3558aa', '#1f2d5c'),   # 1 blue
    ('#ee8a3e', '#f9b878', '#bb5f22', '#5e2c10'),   # 2 orange
    ('#d9a124', '#f2cc5e', '#a8740f', '#4f3606'),   # 3 amber
    ('#46b26a', '#7fd897', '#2f8048', '#173d22'),   # 4 green
    ('#9763d6', '#bf97ef', '#6c40a6', '#33204f'),   # 5 purple
    ('#e0544c', '#f48a80', '#ac3530', '#521614'),   # 6 red
    ('#e86a8a', '#f7a3b8', '#b8476a', '#4f1a2c'),   # 7 pink
]
WHITE = C('#ffffff')
LINE_H = {'zh8': 9, 'zh10': 11, 'zh12': 13, 'silkb': 9, 'p2p': 9}

GOLD_HI = C('#ffd75e')

def brick(lines, col=0, fname='zh10', tail=True, padx=5, pady=3, text_E=0.35, icon=None, hi=None, hi_col=GOLD_HI, hi_E=1.0,
          body_E=0.0):
    """a message brick sprite (Sprite with E map: text slightly emissive so it stays readable in shade).
    hi: substring drawn in hi_col with emissive hi_E (e.g. a glowing gold '周末');  body_E: whole brick glows a little
    (keeps it visible / colourful at night)."""
    if isinstance(lines, str): lines = [lines]
    fill, light, dark, out = [C(c) for c in COLS[col % len(COLS)]]
    lh = LINE_H.get(fname, 11)
    tw = max(text_width(l, fname) for l in lines) + (9 if icon else 0)
    w = tw + padx * 2; h = len(lines) * lh + pady * 2 + 1
    th = 3 if tail else 0
    s = Sprite(w + 2, h + th + 2); cv = s.cv
    ox, oy = 1, 1
    cv.rrect(ox, oy, w, h, out, 2)
    cv.rrect(ox + 1, oy + 1, w - 2, h - 2, fill, 1)
    cv.hline(ox + 2, oy + 1, w - 4, light); cv.vline(ox + 1, oy + 2, h - 5, light)
    cv.rect(ox + 2, oy + h - 3, w - 4, 2, dark); cv.vline(ox + w - 2, oy + 2, h - 4, dark)
    cv.checker(ox + 3, oy + 2, w - 6, 1, mix(fill, light, 0.5))
    if tail:
        tx = ox + 5
        for i in range(3):
            cv.hline(tx, oy + h - 1 + i, 4 - i, out)
            if i < 2: cv.hline(tx + 1, oy + h - 1 + i, 2 - i, dark)
    before = cv.a[..., 3].copy(); col_before = cv.a[..., :3].copy()
    body = cv.a[..., 3] > 0
    ty = oy + (h - len(lines) * lh) // 2
    hi_boxes = []
    for l in lines:
        lw = text_width(l, fname) + (9 if icon else 0)
        lx = ox + (w - lw) // 2
        if icon:
            icon(cv, lx, ty + 1); lx += 9
        cv.text(lx, ty - (1 if fname != 'zh8' else 0), l, WHITE, fname, shadow=dark)
        if hi and hi in l:
            k = l.index(hi); x0 = lx + (text_width(l[:k], fname) if k else 0)
            hi_boxes.append((x0, x0 + text_width(hi, fname) + 1, ty - 1, ty + lh))
        ty += lh
    txt = np.any(cv.a[..., :3] != col_before, axis=2) & (cv.a[..., 0] > 200) & (cv.a[..., 1] > 200)
    if body_E > 0: s.E[body] = body_E
    s.E[txt] = max(text_E, body_E)
    for (x0, x1, y0, y1) in hi_boxes:
        m = np.zeros_like(txt); m[max(0, y0):y1, max(0, x0):x1] = True; m &= txt
        cv.a[m, :3] = hi_col[:3]; s.E[m] = hi_E
    s.w, s.h = w + 2, h + th + 2
    return s

class Lane:
    def __init__(self, Z, y, x0=0, x1=480, W=480):
        self.Z, self.y, self.x0, self.x1 = Z, y, x0, x1
        self.surf = np.full(W, np.inf); self.surf[max(0, int(x0)):min(W, int(x1))] = y

class Body:
    _id = 0
    def __init__(self, t, spr, x, lane, y0=-40.0, vy0=0.0, vx0=0.0, bonk=None, name='', gk=1.0, vmax=None, sway=0.0,
                 sway_f=0.9, soft=False, tf=None, tag=None):
        """gk: gravity scale (0.3 = floaty), vmax: terminal fall speed (px/s), sway: horizontal swing amplitude (px)
        that dies out at the landing (needs tf = expected fall time; add_landing fills it), soft: no bounce / small squash."""
        Body._id += 1; self.id = Body._id
        self.t0, self.spr, self.lane0, self.y0, self.vy0, self.vx0 = t, spr, lane, y0, vy0, vx0
        self.x0 = x; self.bonk = bonk; self.name = name
        self.gk, self.vmax, self.sway, self.sway_f, self.soft, self.tf, self.tag = gk, vmax, sway, sway_f, soft, tf, tag
        self.w, self.h = spr.w, spr.h
        self.track = None      # (n, 4) array: x, y, state(0 hidden 1 fall 2 rest), lane index

class Sim:
    def __init__(self, lanes, g=900.0, dt=1 / 240.0, restitution=0.22, W=480):
        self.lanes = lanes; self.lane_names = list(lanes)
        self.g, self.dt, self.rest, self.W = g, dt, restitution, W
        self.bodies = []; self.events = []

    def add(self, t, brick, x, lane, **kw):
        b = Body(t, brick, x, lane, **kw); self.bodies.append(b); return b

    def fall_time(self, h, lane, y0=-40.0, surf_y=None, bonk=None, gk=1.0, vmax=None):
        """seconds a brick of height h needs from y0 to its first contact (free fall, vy0 = 0)."""
        target = (bonk['y'] if bonk else (self.lanes[lane].y if surf_y is None else surf_y)) - h
        dist = max(1.0, target - y0); g = self.g * gk
        if vmax:
            t_acc = vmax / g; d_acc = 0.5 * g * t_acc ** 2
            if dist > d_acc: return t_acc + (dist - d_acc) / vmax
        return math.sqrt(2 * dist / g)

    def add_landing(self, t_land, brick, x, lane, y0=-40.0, surf_y=None, **kw):
        """add a brick timed so that its first contact (landing or bonk) happens at t_land.
        surf_y: expected surface height if it lands on a pile (default: the lane floor)."""
        tf = self.fall_time(brick.h, lane, y0, surf_y, kw.get('bonk'), kw.get('gk', 1.0), kw.get('vmax'))
        kw.setdefault('tf', tf)
        return self.add(t_land - tf, brick, x, lane, y0=y0, **kw)

    def run(self, t_end):
        n = int(t_end / self.dt) + 2
        for b in self.bodies: b.track = np.zeros((n, 4), np.float32); b.track[:, 2] = 0
        st = {b.id: None for b in self.bodies}
        for i in range(n):
            t = i * self.dt
            for b in self.bodies:
                s = st[b.id]
                if s is None:
                    if t >= b.t0:
                        s = st[b.id] = dict(x=float(b.x0), y=float(b.y0), vx=float(b.vx0), vy=float(b.vy0),
                                            lane=b.lane0, state=1, bounced=False, bonked=False, t_land=None)
                        self.events.append((t, 'spawn', dict(id=b.id, name=b.name)))
                    else:
                        continue
                if s['state'] == 1:
                    s['vy'] += self.g * b.gk * self.dt
                    if b.vmax and s['vy'] > b.vmax: s['vy'] = b.vmax
                    nx = s['x'] + s['vx'] * self.dt; ny = s['y'] + s['vy'] * self.dt
                    if b.sway and b.tf:
                        sw = lambda tt: b.sway * math.sin(2 * math.pi * b.sway_f * (tt - b.t0)) * max(0.0, 1 - (tt - b.t0) / b.tf)
                        nx += sw(t) - sw(t - self.dt)
                    bk = b.bonk
                    if bk and not s['bonked'] and s['vy'] > 0 and ny + b.h >= bk['y']:
                        s['bonked'] = True; ny = bk['y'] - b.h
                        self.events.append((t, 'bonk', dict(id=b.id, name=b.name, v=s['vy'], x=nx + b.w / 2, y=bk['y'])))
                        s['vy'] = bk.get('vy', -220.0); s['vx'] = bk.get('vx', 80.0)
                        if bk.get('to'): s['lane'] = bk['to']
                    else:
                        L = self.lanes[s['lane']]
                        x0, x1 = int(max(0, nx + 1)), int(min(self.W, nx + b.w - 1))
                        surf = L.surf[x0:x1].min() if x1 > x0 else np.inf
                        if not np.isfinite(surf):
                            # off the lane (e.g. slid off the desk) -> fall to the next lane listed in 'fallback'
                            fb = getattr(L, 'fallback', None)
                            if fb: s['lane'] = fb
                        elif s['vy'] > 0 and ny + b.h >= surf:
                            ny = surf - b.h
                            if not s['bounced'] and s['vy'] > 260 and not b.soft:
                                self.events.append((t, 'land', dict(id=b.id, name=b.name, v=s['vy'], x=nx + b.w / 2, y=surf, lane=s['lane'])))
                                s['vy'] = -s['vy'] * self.rest; s['vx'] *= 0.5; s['bounced'] = True
                            else:
                                if not s['bounced']:
                                    self.events.append((t, 'land', dict(id=b.id, name=b.name, v=s['vy'], x=nx + b.w / 2, y=surf, lane=s['lane'])))
                                s['state'] = 2; s['vy'] = 0; s['vx'] = 0; s['t_land'] = t
                                L.surf[x0:x1] = np.minimum(L.surf[x0:x1], ny + 1)
                    s['x'], s['y'] = nx, ny
                b.track[i] = (s['x'], s['y'], s['state'], self.lane_names.index(s['lane']))
        self.events.sort(key=lambda e: e[0])
        self.n = n
        return self

    def at(self, tau):
        """list of (body, x, y, lane_name, squash) visible at simulation time tau."""
        i = int(round(min(max(tau, 0), (self.n - 1) * self.dt) / self.dt))
        out = []
        for b in self.bodies:
            x, y, s, li = b.track[i]
            if s == 0: continue
            # landing squash: find the first rest index (cheap: scan back a little)
            sq = 0.0
            if s == 2:
                j = i
                while j > 0 and b.track[j - 1, 2] == 2 and i - j < 60: j -= 1
                age = (i - j) * self.dt
                if age < 0.18: sq = math.sin(age / 0.18 * math.pi) * (1 - age / 0.18) * (0.35 if b.soft else 0.9)
            out.append((b, float(x), float(y), self.lane_names[int(li)], sq))
        return out

def put_bodies(mid, sim, tau, Zof=lambda lane: 330.0, flat_squash=True, only=None, flash_fn=None, hide_fn=None):
    """draw all visible bricks into a GLayer (far lanes first). only: optional set of lane names.
    flash_fn(body) -> 0..1 white flash (line clears), hide_fn(body) -> True to skip (cleared bricks)."""
    items = sim.at(tau)
    if only is not None: items = [it for it in items if it[3] in only]
    if hide_fn is not None: items = [it for it in items if not hide_fn(it[0])]
    items.sort(key=lambda it: -Zof(it[3]))
    for b, x, y, lane, sq in items:
        spr, E = b.spr.rgba, b.spr.E
        fl = flash_fn(b) if flash_fn is not None else 0.0
        if fl > 0.01:
            spr = spr.copy(); m = spr[..., 3] > 0
            spr[m, :3] = (spr[m, :3].astype(np.float32) * (1 - fl) + 255 * fl).astype(np.uint8)
            E = np.where(m, np.maximum(E, fl), E).astype(np.float32)
        if sq > 0.02 and flat_squash:
            h, w = spr.shape[:2]
            nh = max(2, int(round(h * (1 - 0.18 * sq)))); nw = int(round(w * (1 + 0.10 * sq)))
            import cv2
            spr = cv2.resize(spr, (nw, nh), interpolation=cv2.INTER_NEAREST)
            E = cv2.resize(E, (nw, nh), interpolation=cv2.INTER_NEAREST)
            x = x - (nw - w) / 2; y = y + (h - nh)
        mid.put(spr, x, y, Zof(lane), E=E)
    return items


# ------------------------------------------------------------------ line-clear 'poof' particles
class Poof:
    """Tetris-style line clear: every brick bursts into its own coloured pixels (+ white sparks) at t0.
        pf = Poof(items, t0)            # items = sim.at(tau_clear) (body, x, y, lane, sq) or [(spr_rgba, x, y, Z)]
        pf.draw(mid, t)                 # writes emissive pixels into the GLayer (they glow and fade)"""
    def __init__(self, items, t0, Zof=lambda lane: 330.0, per=10, seed=0, g=520.0, life=(0.45, 0.85), speed=(60, 170),
                 sparks=0.35, stagger=None):
        rng = np.random.default_rng(seed)
        P = []
        for k, it in enumerate(items):
            if hasattr(it[0], 'spr'):
                b, x, y, lane, sq = it; rgba = b.spr.rgba; Z = Zof(lane)
            else:
                rgba, x, y, Z = it
            ys, xs = np.nonzero(rgba[..., 3] > 127)
            if len(xs) == 0: continue
            n = max(3, int(per * (len(xs) / 400.0) ** 0.5 * 2))
            pick = rng.integers(0, len(xs), n)
            dt0 = 0.0 if stagger is None else stagger(x, y)
            for j in pick:
                px, py = x + xs[j], y + ys[j]
                cx, cy = x + rgba.shape[1] / 2, y + rgba.shape[0] / 2
                a = math.atan2(py - cy - 4, px - cx) + rng.normal(0, 0.5)
                sp = rng.uniform(*speed)
                col = rgba[ys[j], xs[j], :3]
                if rng.uniform() < sparks: col = np.array([255, 250, 225], np.uint8)
                P.append((px, py, math.cos(a) * sp, math.sin(a) * sp - rng.uniform(40, 120), col, Z - 2,
                          rng.uniform(*life), int(rng.integers(1, 3)), dt0))
        self.t0, self.g = t0, g
        if P:
            self.x0, self.y0, self.vx, self.vy = [np.array([p[i] for p in P], np.float32) for i in range(4)]
            self.col = np.array([p[4] for p in P], np.uint8); self.Z = np.array([p[5] for p in P], np.float32)
            self.life = np.array([p[6] for p in P], np.float32); self.size = np.array([p[7] for p in P], np.int32)
            self.dt0 = np.array([p[8] for p in P], np.float32)
        else:
            self.x0 = np.zeros(0, np.float32)

    def draw(self, mid, t, E=1.0):
        if len(self.x0) == 0: return
        age = t - self.t0 - self.dt0
        ok = (age >= 0) & (age < self.life)
        if not ok.any(): return
        a = age[ok]; u = a / self.life[ok]
        x = self.x0[ok] + self.vx[ok] * a; y = self.y0[ok] + self.vy[ok] * a + 0.5 * self.g * a * a
        col = self.col[ok]; Z = self.Z[ok]; sz = self.size[ok] * (u < 0.6) + 1 * (u >= 0.6)
        e = (E * (1 - u) ** 0.7).astype(np.float32)
        H, W = mid.H, mid.W
        for dx in (0, 1):
            for dy in (0, 1):
                sel = (sz > 1) | ((dx == 0) & (dy == 0))
                xi = np.round(x[sel]).astype(int) + dx; yi = np.round(y[sel]).astype(int) + dy
                m = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
                xi, yi = xi[m], yi[m]
                mid.cv.a[yi, xi, :3] = col[sel][m]; mid.cv.a[yi, xi, 3] = 255
                mid.E[yi, xi] = e[sel][m]; mid.Z[yi, xi] = Z[sel][m]; mid.N[yi, xi] = 0
