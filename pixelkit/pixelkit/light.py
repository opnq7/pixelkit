"""pixelkit.light - a 2.5D light rig for pixel-art rooms (HD-2D look).

Light is computed as smooth float RGB maps at f x canvas resolution and multiplied onto the
crisp pixel albedo (soft light over crisp pixels - the key to the reference look).

  * Sun through windows (with venetian blinds / mullions): every receiver point is traced back
    along the sun direction to the window plane -> exact striped light pools on walls, floor
    and on mid-ground objects (at their own depth, so stripes shift across them).
  * Cast shadows of a mid-ground layer (characters, desks) onto the room (remap lookup).
  * Volumetric god rays (ray-marched at low res) + bounce light + corner AO + point lights.
"""
import numpy as np, cv2
from .persp import BACK, FLOOR, CEIL, LEFT, RIGHT, NONE

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

class Window:
    """Rectangular opening on a room wall.
    wall LEFT/RIGHT: a = Z range, b = Y range.   wall BACK: a = X range, b = Y range.
    blinds: dict(period, open (0..1 fraction open), top, bottom, soft) - horizontal slats between
            Y=top and Y=bottom; below 'bottom' the window is unobstructed.
    mullions: list of a-positions of vertical bars, bar width in world units = mull_w."""
    def __init__(self, wall, a0, a1, b0, b1, blinds=None, mullions=(), mull_w=2.0, frame=1.5):
        self.wall, self.a0, self.a1, self.b0, self.b1 = wall, a0, a1, b0, b1
        self.blinds, self.mullions, self.mull_w, self.frame = blinds, mullions, mull_w, frame

    def transmission(self, a, b):
        fr = self.frame
        T = smoothstep(self.a0 + fr - 0.5, self.a0 + fr + 0.5, a) * smoothstep(-(self.a1 - fr) - 0.5, -(self.a1 - fr) + 0.5, -a)
        T = T * smoothstep(self.b0 + fr - 0.5, self.b0 + fr + 0.5, b) * smoothstep(-(self.b1 - fr) - 0.5, -(self.b1 - fr) + 0.5, -b)
        for m in self.mullions:
            T = T * (1 - (1 - smoothstep(self.mull_w / 2 - 0.4, self.mull_w / 2 + 0.4, np.abs(a - m))))
        bl = self.blinds
        if bl:
            p = bl.get('period', 5.0); o = bl.get('open', 0.5); sft = bl.get('soft', 0.12)
            top, bot = bl.get('top', self.b0), bl.get('bottom', self.b1)
            ph = np.mod((b - top) / p, 1.0)
            slat = smoothstep(o - sft, o + sft, ph)      # 1 where slat blocks
            inreg = (b >= top) & (b <= bot)
            T = T * np.where(inreg, 1 - slat * bl.get('opacity', 0.92), 1.0)
        return T

class Sun:
    def __init__(self, direction=(1.0, 0.42, 0.32), color=(1.0, 0.70, 0.40), intensity=1.25):
        d = np.asarray(direction, np.float64); self.d = d / np.linalg.norm(d)
        self.color = np.asarray(color, np.float32); self.intensity = float(intensity)

def sun_T(room, sun, windows, X, Y, Z):
    """transmission (0..1) of sunlight reaching world points (X,Y,Z) through any window."""
    d = sun.d
    T = np.zeros(np.shape(X), np.float64)
    for w in windows:
        if w.wall in (LEFT, RIGHT):
            Xw = room.Xl if w.wall == LEFT else room.Xr
            if abs(d[0]) < 1e-6: continue
            t = (X - Xw) / d[0]                 # P - t*d lies on the window plane
            a = Z - t * d[2]; b = Y - t * d[1]
        else:  # BACK window: plane Z = D
            if abs(d[2]) < 1e-6: continue
            t = (Z - room.D) / d[2]
            a = X - t * d[0]; b = Y - t * d[1]
        ok = t > 0
        T = np.maximum(T, np.where(ok, w.transmission(a, b), 0.0))
    return T

def _normals_factor(sid, sun, amb_floor=0.25):
    """Lambert factor per surface id for the sun (towards-light = -d)."""
    L = -sun.d
    nd = {BACK: (0, 0, -1), FLOOR: (0, -1, 0), CEIL: (0, 1, 0), LEFT: (1, 0, 0), RIGHT: (-1, 0, 0)}
    out = np.zeros(sid.shape, np.float32)
    for k, n in nd.items():
        out[sid == k] = max(0.0, float(np.dot(n, L)))
    return out

class LightRig:
    def __init__(self, room, f=2):
        self.room, self.f = room, f
        self.S = room.surfaces(f)
        self.h, self.w = self.S['id'].shape
        self._pt = {}

    # ---------------- sun -----------------------------------------------------------------
    def sun_room(self, sun, windows):
        S = self.S
        T = sun_T(self.room, sun, windows, S['X'], S['Y'], S['Z'])
        ndl = _normals_factor(S['id'], sun)
        mx = max(1e-6, ndl.max())
        return (T * (0.35 + 0.65 * ndl / mx)).astype(np.float32), T.astype(np.float32)

    def sun_plane(self, sun, windows, Z, facing=0.75):
        """sun on a vertical camera-facing plane at depth Z (mid-ground sprites)."""
        S = self.S
        X, Y, ZZ = self.room.unproject_on_Z(S['x'], S['y'], Z)
        T = sun_T(self.room, sun, windows, X, Y, ZZ)
        return (T * facing).astype(np.float32)

    def shadow_from_plane(self, alpha, Zc, sun, receiver_Z=None, soft=1.2, f_alpha=1):
        """Occlusion (0..1) cast by a mid-ground layer living on plane Z=Zc onto the room
        surfaces (receiver_Z None) or onto a plane at receiver_Z.  alpha: (H*f_alpha, W*f_alpha)
        float/bool coverage of the caster layer."""
        S = self.S; d = sun.d
        if receiver_Z is None:
            X, Y, Z = S['X'], S['Y'], S['Z']
        else:
            X, Y, Z = self.room.unproject_on_Z(S['x'], S['y'], receiver_Z)
        if abs(d[2]) < 1e-6: return np.zeros((self.h, self.w), np.float32)
        t = (Z - Zc) / d[2]
        valid = t > 0
        qx, qy = self.room.project(X - t * d[0], Y - t * d[1], np.full_like(X, Zc))
        mx = (qx * f_alpha - 0.5).astype(np.float32); my = (qy * f_alpha - 0.5).astype(np.float32)
        a = alpha.astype(np.float32)
        if soft > 0: a = cv2.GaussianBlur(a, (0, 0), soft * f_alpha)
        occ = cv2.remap(a, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        return np.where(valid, occ, 0).astype(np.float32)

    # ---------------- volumetrics ---------------------------------------------------------
    def god_rays(self, sun, windows, scale=0.25, steps=40, z_near=None, density=1.0):
        """screen-space accumulated in-scattering of sun shafts (h*scale/f .. ) float map."""
        r = self.room
        h, w = int(r.H * scale * 2), int(r.W * scale * 2)
        S = r.surfaces(scale * 2)
        x, y = S['x'], S['y']
        z_far = S['Z']
        z_near = z_near or r.D / 2.2
        acc = np.zeros((h, w))
        zs = np.linspace(0, 1, steps)
        for k in zs:
            Z = z_near + (z_far - z_near) * k
            X, Y, ZZ = r.unproject_on_Z(x, y, 1.0)
            X = (x - r.vx) * Z / r.D; Y = (y - r.vy) * Z / r.D
            inside = (X > r.Xl) & (X < r.Xr) & (Y > r.Yc) & (Y < r.Yf)
            T = sun_T(r, sun, windows, X, Y, Z) * inside
            acc += T * (z_far - z_near) / steps
        acc = acc / r.D * density
        return cv2.GaussianBlur(acc.astype(np.float32), (0, 0), 0.8)

    # ---------------- misc ----------------------------------------------------------------
    def corner_ao(self, strength=0.35, radius=14.0):
        S = self.S; r = self.room; sid = S['id']; X, Y, Z = S['X'], S['Y'], S['Z']
        d = np.full(sid.shape, 1e9)
        dz_back = (r.D - Z)
        m = sid == BACK; d[m] = np.minimum.reduce([(r.Yf - Y)[m], (X - r.Xl)[m], (r.Xr - X)[m], (Y - r.Yc)[m]])
        m = sid == FLOOR; d[m] = np.minimum.reduce([dz_back[m], (X - r.Xl)[m], (r.Xr - X)[m]])
        m = sid == CEIL; d[m] = np.minimum.reduce([dz_back[m], (X - r.Xl)[m], (r.Xr - X)[m]])
        m = np.isin(sid, (LEFT, RIGHT)); d[m] = np.minimum.reduce([dz_back[m], (r.Yf - Y)[m], (Y - r.Yc)[m]])
        return (1 - strength * np.exp(-np.maximum(d, 0) / radius)).astype(np.float32)

    def point(self, x, y, radius, power=1.6):
        """smooth point-light falloff map (canvas coords) - cached."""
        key = (round(x, 1), round(y, 1), round(radius, 1), power)
        if key not in self._pt:
            f = self.f
            yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
            rr = np.hypot((xx + 0.5) / f - x, (yy + 0.5) / f - y) / radius
            self._pt[key] = (1.0 / (1.0 + rr * rr) ** power).astype(np.float32)
        return self._pt[key]

def bounce(sun_map, color, strength=0.22, sigma=40.0, f=2):
    b = cv2.resize(sun_map, (sun_map.shape[1] // 4, sun_map.shape[0] // 4), interpolation=cv2.INTER_AREA)
    b = cv2.GaussianBlur(b, (0, 0), sigma * f / 4)
    b = cv2.resize(b, (sun_map.shape[1], sun_map.shape[0]), interpolation=cv2.INTER_LINEAR)
    return b[..., None] * (np.asarray(color, np.float32) * strength)

# ---------------------------------------------------------------- time-of-day presets
TOD = {
    # sun travel direction, sun colour, intensity, ambient colour, ambient level, god-ray strength
    # tuned against the reference (qa.REF_TARGETS) in the office set: warm pink-peach sun, lilac ambient
    'morning': dict(sun=((1.0, 0.52, 0.15), (1.0, 0.88, 0.70), 2.00), amb=((0.78, 0.78, 0.96), 0.86), rays=2.3),
    'golden': dict(sun=((1.0, 0.35, 0.15), (1.0, 0.76, 0.62), 2.10), amb=((0.84, 0.70, 0.90), 0.80), rays=2.0),
    'late':   dict(sun=((1.0, 0.28, 0.15), (1.0, 0.64, 0.50), 2.00), amb=((0.80, 0.64, 0.88), 0.72), rays=2.2),
    'sunset': dict(sun=((1.0, 0.18, 0.15), (1.0, 0.50, 0.42), 1.70), amb=((0.72, 0.56, 0.86), 0.62), rays=2.0),
    'dusk':   dict(sun=((1.0, 0.12, 0.15), (0.8, 0.40, 0.45), 0.0), amb=((0.46, 0.44, 0.78), 0.50), rays=0.0),
    'night':  dict(sun=((1.0, 0.12, 0.15), (0.5, 0.6, 1.0), 0.0), amb=((0.30, 0.34, 0.70), 0.34), rays=0.0),
}

def lerp_tod(a, b, k):
    A, B = TOD[a], TOD[b]
    L = lambda u, v: tuple(np.asarray(u, np.float64) * (1 - k) + np.asarray(v, np.float64) * k)
    return dict(sun=(L(A['sun'][0], B['sun'][0]), L(A['sun'][1], B['sun'][1]), A['sun'][2] * (1 - k) + B['sun'][2] * k),
                amb=(L(A['amb'][0], B['amb'][0]), A['amb'][1] * (1 - k) + B['amb'][1] * k),
                rays=A['rays'] * (1 - k) + B['rays'] * k)


# ====================================================================== pixel-art light quantisation
def dither_light(L, f=2, step=0.20, k=1.0, floor=0.02, phase=(0, 0)):
    """Quantise a smooth light map to crisp per-native-pixel levels with a BAYER4 ordered dither.

    This is the single biggest "texture" trick of the reference look: light gradients (lamp glow on a wall,
    shadow penumbrae, falloff across a facade) do not ramp smoothly - they step in a few levels and the
    transitions between levels are a checkerboard of native pixels.

    L:     (H*f, W*f, 3) or (H*f, W*f) float light (any range, 1 = albedo as painted)
    step:  level spacing in log2 units (0.20 ~ 15 % brightness steps; 0.3 = chunkier bands)
    k:     blend between the smooth map (0) and the quantised map (1)
    phase: offset of the Bayer matrix (keep it fixed in SET space so the pattern never swims under a moving camera)
    Returns an array shaped like L (crisp blocks of f x f)."""
    import cv2 as _cv2
    from .core import BAYER4
    Hf, Wf = L.shape[:2]; H, W = Hf // f, Wf // f
    Ln = _cv2.resize(L.astype(np.float32), (W, H), interpolation=_cv2.INTER_AREA) if f > 1 else L.astype(np.float32)
    lum = Ln.mean(-1) if Ln.ndim == 3 else Ln
    lum = np.maximum(lum, floor)
    yy, xx = np.mgrid[0:H, 0:W]
    th = BAYER4[(yy + phase[1]) % 4, (xx + phase[0]) % 4] - 0.5
    lg = np.log2(lum) / step
    q = np.floor(lg + 0.5 + th) * step
    s = np.power(2.0, q) / lum
    Lq = Ln * (s[..., None] if Ln.ndim == 3 else s)
    Lq = np.repeat(np.repeat(Lq, f, 0), f, 1) if f > 1 else Lq
    return (L + (Lq - L) * k).astype(np.float32) if k < 1 else Lq.astype(np.float32)
