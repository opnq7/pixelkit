"""pixelkit.vec - a tiny SDF / mask "vector pixel painter" for natively drawn LARGE sprites (close-ups).

Close-ups used to be the room scene zoomed 2.5-3.5x, so a close-up character was a 30 px head blown up into
14 px blocks.  vec draws big sprites directly on the native pixel grid instead: every shape is a signed-distance
field (or a polygon) sampled at pixel centres, so a 130 px head stays crisp pixel art at any tilt (rotate the
coordinate frame, not the raster), and every part is shaded as a soft volume:

    depth = distance-to-edge / bevel  ->  rounded profile  ->  normal  ->  lambert(key) + fill + ambient
          ->  quantised onto a hand-picked colour ramp with 4x4 Bayer dither at the band edges
          ->  1 px selective outline (a darker version of the part's own edge colour, or a fixed ink)

    from pixelkit.vec import Painter, rrect, ellipse, seg, arc
    p = Painter(160, 140)
    with p.frame(rot=4, cx=80, cy=70):                     # everything inside is drawn tilted 4 deg about (80, 70)
        u, v = p.uv()
        m = p.part(rrect(u, v, 20, 30, 120, 90, 18), ramp=SHELL, bevel=7, light=(-0.5, -0.6, 0.65))
        p.fill(ellipse(u, v, 60, 70, 9, 12), EYE, E=0.9)     # flat fill + emissive
    spr = p.sprite()                                        # -> pixelkit.scene.Sprite (rgba uint8 + E)

Shapes return signed distances (<0 inside) in pixels of the local frame.  Parts drawn later sit on top.
"""
import math
from contextlib import contextmanager
import numpy as np, cv2
from .core import BAYER4

# ------------------------------------------------------------------ SDF primitives (local coords u, v)
def rrect(u, v, x, y, w, h, r=0.0):
    cx, cy = x + w / 2.0, y + h / 2.0
    qx = np.abs(u - cx) - (w / 2.0 - r); qy = np.abs(v - cy) - (h / 2.0 - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r

def ellipse(u, v, cx, cy, rx, ry):
    k = np.hypot((u - cx) / rx, (v - cy) / ry)
    return (k - 1.0) * min(rx, ry)

def circle(u, v, cx, cy, r): return np.hypot(u - cx, v - cy) - r

def seg(u, v, x0, y0, x1, y1, th=1.0):
    """capsule stroke from (x0, y0) to (x1, y1), thickness th."""
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    t = np.clip(((u - x0) * dx + (v - y0) * dy) / L2, 0, 1) if L2 > 0 else 0.0
    return np.hypot(u - x0 - t * dx, v - y0 - t * dy) - th / 2.0

def poly_stroke(u, v, pts, th=1.0):
    d = None
    for (a, b) in zip(pts[:-1], pts[1:]):
        s = seg(u, v, a[0], a[1], b[0], b[1], th)
        d = s if d is None else np.minimum(d, s)
    return d

def arc(u, v, cx, cy, R, a0, a1, th=1.0):
    """stroke along the circle (cx, cy, R) from angle a0 to a1 (degrees, 0 = +x, 90 = +y = DOWN, counter-clockwise
    in maths = clockwise on screen).  Round caps."""
    ang = np.degrees(np.arctan2(v - cy, u - cx))
    lo, hi = min(a0, a1), max(a0, a1)
    a = (ang - lo) % 360.0
    inside = a <= (hi - lo)
    d_ring = np.abs(np.hypot(u - cx, v - cy) - R) - th / 2.0
    p0 = (cx + R * math.cos(math.radians(lo)), cy + R * math.sin(math.radians(lo)))
    p1 = (cx + R * math.cos(math.radians(hi)), cy + R * math.sin(math.radians(hi)))
    d_cap = np.minimum(np.hypot(u - p0[0], v - p0[1]), np.hypot(u - p1[0], v - p1[1])) - th / 2.0
    return np.where(inside, d_ring, d_cap)

def union(*ds):
    out = ds[0]
    for d in ds[1:]: out = np.minimum(out, d)
    return out

def inter(a, b): return np.maximum(a, b)
def sub(a, b): return np.maximum(a, -b)
def smooth_union(a, b, k=4.0):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def _norm(v):
    v = np.asarray(v, np.float32); n = float(np.linalg.norm(v)); return v / (n if n > 0 else 1.0)

def _col(c): return np.asarray(c[:3], np.float32)


class Painter:
    """native-res canvas for big sprites.  All shapes are evaluated in the current local frame (see frame())."""
    def __init__(self, W, H):
        self.W, self.H = int(W), int(H)
        self.rgb = np.zeros((self.H, self.W, 3), np.float32)
        self.a = np.zeros((self.H, self.W), bool)
        self.E = np.zeros((self.H, self.W), np.float32)
        yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        self.X, self.Y = xx + 0.5, yy + 0.5
        self._M = [np.eye(3, dtype=np.float32)]          # local -> screen
        self.bayer = np.tile(BAYER4, (self.H // 4 + 1, self.W // 4 + 1))[:self.H, :self.W] - 0.5

    # ---------------------------------------------------------------- frames
    @contextmanager
    def frame(self, rot=0.0, cx=0.0, cy=0.0, dx=0.0, dy=0.0, sx=1.0, sy=1.0):
        """nested local frame: scale (sx, sy) and rotate by rot degrees about (cx, cy), then translate by (dx, dy)."""
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        T1 = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]], np.float32)
        R = np.array([[c * sx, -s * sy, 0], [s * sx, c * sy, 0], [0, 0, 1]], np.float32)
        T2 = np.array([[1, 0, cx + dx], [0, 1, cy + dy], [0, 0, 1]], np.float32)
        self._M.append(self._M[-1] @ (T2 @ R @ T1))
        try: yield self
        finally: self._M.pop()

    def uv(self):
        Mi = np.linalg.inv(self._M[-1])
        u = Mi[0, 0] * self.X + Mi[0, 1] * self.Y + Mi[0, 2]
        v = Mi[1, 0] * self.X + Mi[1, 1] * self.Y + Mi[1, 2]
        return u, v

    def to_screen(self, x, y):
        M = self._M[-1]
        return M[0, 0] * x + M[0, 1] * y + M[0, 2], M[1, 0] * x + M[1, 1] * y + M[1, 2]

    def poly(self, pts):
        """filled polygon (local coords) -> boolean mask (screen)."""
        sp = np.array([self.to_screen(x, y) for (x, y) in pts], np.float32)
        m = np.zeros((self.H, self.W), np.uint8)
        cv2.fillPoly(m, [np.round(sp * 8).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=3)
        return m.astype(bool)

    # ---------------------------------------------------------------- painting
    @staticmethod
    def mask(d):
        return d <= 0 if not (isinstance(d, np.ndarray) and d.dtype == bool) else d

    def fill(self, d, col, E=None, where=None, alpha=1.0):
        m = self.mask(d)
        if where is not None: m = m & where
        if alpha >= 1.0: self.rgb[m] = _col(col) / 255.0
        else: self.rgb[m] = self.rgb[m] * (1 - alpha) + (_col(col) / 255.0) * alpha
        self.a |= m
        if E is not None: self.E[m] = E
        return m

    def part(self, d, ramp, bevel=4.0, light=(-0.45, -0.6, 0.66), amb=0.30, fill=None, normal=(0, 0, 1),
             dither=0.4, outline=0.55, ink=None, where=None, E=None, bias=0.0, profile='round', clip=None):
        """shaded volume.  ramp: list of colours dark -> light.  fill: (dir, strength) second light.  normal: base
        normal of the flat area (e.g. (-0.7, 0, 0.7) for a side panel turned left).  outline: darken factor for the
        1 px edge (None = no outline), ink: fixed outline colour instead.  bias: shifts the lit value (+ = lighter).
        clip: boolean mask the part is clipped to (drawn only there; the outline follows the clipped shape)."""
        m = self.mask(d)
        if where is not None: m = m & where
        if clip is not None: m = m & clip
        if not m.any(): return m
        dist = cv2.distanceTransform(np.pad(m, 1, mode='edge').astype(np.uint8), cv2.DIST_L2, 5)[1:-1, 1:-1]
        dep = np.clip(dist / max(bevel, 1e-3), 0, 1)
        h = np.sqrt(np.clip(1 - (1 - dep) ** 2, 0, 1)) if profile == 'round' else dep
        h = cv2.GaussianBlur(h.astype(np.float32), (0, 0), 0.7) * bevel
        gy, gx = np.gradient(h)
        n0 = _norm(normal)
        nx, ny, nz = n0[0] - gx, n0[1] - gy, n0[2] + 0 * gx
        ln = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
        L = _norm(light)
        lam = np.clip((nx * L[0] + ny * L[1] + nz * L[2]) / ln, 0, 1)
        val = amb + (1 - amb) * lam
        if fill is not None:
            F = _norm(fill[0]); val = val + fill[1] * np.clip((nx * F[0] + ny * F[1] + nz * F[2]) / ln, 0, 1)
        val = np.clip(val + bias, 0, 1)
        n = len(ramp)
        idx = np.clip(np.floor(val * (n - 1) + 0.5 + self.bayer * dither), 0, n - 1).astype(np.int32)
        R = np.array([_col(c) for c in ramp], np.float32) / 255.0
        self.rgb[m] = R[idx[m]]
        self.a |= m
        if E is not None: self.E[m] = E
        if outline is not None or ink is not None:
            self.edge(m, outline if outline is not None else 0.55, ink)
        return m

    def edge(self, m, factor=0.55, ink=None, sides='all'):
        pad = np.pad(m, 1, mode='edge')
        e = m & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        if ink is not None: self.rgb[e] = _col(ink) / 255.0
        else: self.rgb[e] = self.rgb[e] * factor
        return e

    def rim(self, m, direction=(1, 0), col=(255, 255, 255), width=1, alpha=1.0, E=None):
        """light the pixels of mask m whose neighbour `width` px towards `direction` is outside m (a rim light)."""
        dx, dy = direction
        sh = np.zeros_like(m)
        H, W = m.shape
        for k in range(1, width + 1):
            ox, oy = int(round(dx * k)), int(round(dy * k))
            s = np.zeros_like(m)
            ys0, ys1 = max(0, -oy), min(H, H - oy); xs0, xs1 = max(0, -ox), min(W, W - ox)
            s[ys0:ys1, xs0:xs1] = m[ys0 + oy:ys1 + oy, xs0 + ox:xs1 + ox]
            sh |= ~s
        r = m & sh
        c = _col(col) / 255.0
        self.rgb[r] = self.rgb[r] * (1 - alpha) + c * alpha
        if E is not None: self.E[r] = np.maximum(self.E[r], E)
        return r

    def tint(self, m, col, k):
        self.rgb[m] = self.rgb[m] * (1 - k) + (_col(col) / 255.0) * k

    def sprite(self):
        from .scene import Sprite
        s = Sprite(self.W, self.H)
        s.cv.a[..., :3] = np.clip(self.rgb * 255 + 0.5, 0, 255).astype(np.uint8)
        s.cv.a[..., 3] = np.where(self.a, 255, 0).astype(np.uint8)
        s.E[:] = self.E
        return s
