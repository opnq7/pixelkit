"""pixelkit.perform - the PERFORMANCE layer (v0.7, 表演层): small, reusable acting helpers that make sprites feel alive.

Everything is a pure function of t (parallel render safe).  Built for Act 4 v2 after comparing with a pro pixel short:
the difference was not the drawing, it was the acting - nothing in a good shot is ever perfectly still.

  timing     on_twos(t)                 quantise character motion to 12 fps ("animate on 2s"), keep water/breath at 30
  springs    spring_follow(fn, t)       a damped follower of any 1-D/2-D trajectory (antenna lag, hair, rod tip ...)
             wobble(t, t0, amp)         damped sine kicked at t0 (antenna boing, hat bounce, card shake)
             lag(fn, t) = follower - target  -> use as the antenna tip offset
  poses      PoseTrack([(t, 'rest'), (t, 'clasp', 0.3, 'back'), ...])  -> (a, b, k) for blended arm poses
             Keys(...) numeric keyframes with ease names (= anim.Track, re-exported)
  life       breath_px(t)               0/1 px idle breathing offset (period ~3.6 s, the exhale holds a little)
             blink_face(t, times, base) blink with in-betweens: half -> blink -> half (reads as a real blink, not a pop)
             glance(t, keys)            eye look offsets with quick saccades + slight overshoot
  sprites    rotsprite(rgba, E, deg, pivot)   pixel-art rotation: method='shear' (default, 3 integer shears, clean up to
                                        ~10 deg) or 'epx' (EPX x3 upscale -> rotate -> centre-sample, for big angles)
             squash_about(a, e, k, px, py)    squash / stretch about a fixed point (seat contact, feet)
             shake_rows / shift_rows / lean_rows / merge

Acting rules of thumb (see STYLE_GUIDE 5c):
  * every move = anticipation (small opposite move, 2-4 frames) -> action (eased, on 2s) -> overshoot -> settle
  * secondary motion lags the primary by 2-4 frames (antenna after the head, feet after the hop)
  * holds are never dead: breathing + blinks + a 1px look shift every 2-3 s
  * one idea per beat; the eyes lead (look first, then the head turns, then the body)
  * never twist a head more than ~90 deg away from its body (turn the body instead)
"""
import math
import numpy as np
from .anim import EASE, Track as Keys, clamp01, ramp, lerp, auto_blinks

# ------------------------------------------------------------------ timing
def on_twos(t, fps=30, n=2):
    """quantise t to every n-th frame (n=2 at 30 fps -> 15 drawings / s).  Use for character poses, not water/light."""
    f = math.floor(t * fps + 1e-6)
    return (f - f % n) / fps

# ------------------------------------------------------------------ springs
def spring_follow(fn, t, freq=3.0, zeta=0.32, window=2.5, dt=1 / 240.0):
    """position of a damped spring that chases fn(t) (scalar or tuple).  Simulated from t-window, so it is a pure
    function of t.  freq in Hz, zeta = damping ratio (0.2 bouncy .. 1 no overshoot)."""
    w = 2 * math.pi * freq
    t0 = max(0.0, t - window)
    x = np.asarray(fn(t0), np.float64); v = np.zeros_like(x)
    n = max(1, int((t - t0) / dt))
    h = (t - t0) / n
    tt = t0
    for _ in range(n):
        tt += h
        target = np.asarray(fn(tt), np.float64)
        acc = w * w * (target - x) - 2 * zeta * w * v
        v = v + acc * h; x = x + v * h
    return x if x.shape else float(x)

def lag(fn, t, **kw):
    """follower - target: how far a loosely attached part trails behind (e.g. antenna tip offset)."""
    return np.asarray(spring_follow(fn, t, **kw)) - np.asarray(fn(t), np.float64)

def wobble(t, t0, amp=2.0, freq=4.0, decay=3.5):
    """damped sine kicked at t0 (0 before): amp * e^(-decay u) * sin(2 pi freq u)."""
    u = t - t0
    if u < 0: return 0.0
    return amp * math.exp(-decay * u) * math.sin(2 * math.pi * freq * u)

def wobbles(t, events, **kw):
    """sum of wobble() for a list of (t0, amp) events."""
    return sum(wobble(t, t0, amp, **kw) for t0, amp in events)

# ------------------------------------------------------------------ poses
def back_soft(u, s=1.2):
    """ease with a small overshoot (~6%) - for arms arriving at a pose."""
    u = clamp01(u) - 1
    return u * u * ((s + 1) * u + s) + 1

class PoseTrack:
    """discrete named poses with eased blends.  keys: (t, pose[, blend_dur=0.25[, ease='io']]) - the blend INTO the
    pose starts at t.  __call__(t) -> (pose_a, pose_b, k) where k may exceed 1 a little with ease='back'
    (overshoot).  Pass the tuple straight to claude.draw(arms=...) / person.draw(arms=...)."""
    def __init__(self, keys):
        self.keys = [(k[0], k[1], k[2] if len(k) > 2 else 0.25, k[3] if len(k) > 3 else 'io') for k in sorted(keys, key=lambda k: k[0])]

    def __call__(self, t):
        ks = self.keys
        if t < ks[0][0]: return (ks[0][1], ks[0][1], 0.0)
        i = max(j for j in range(len(ks)) if ks[j][0] <= t)
        t0, p, d, e = ks[i]
        prev = ks[i - 1][1] if i > 0 else p
        if d <= 0 or t >= t0 + d: return (p, p, 0.0)
        u = (t - t0) / d
        k = EASE[e](u) if e != 'back' else back_soft(u)
        return (prev, p, k)

    def name(self, t):
        a, b, k = self(t)
        return b if k >= 0.5 else a

def anticipate(u, a=0.12, split=0.25):
    """0..1 progress with a small pull-back first (dips to -a during the first `split`), then eases to 1 with a soft
    overshoot.  Use for any 'big' move (flick, hop, reach)."""
    u = clamp01(u)
    if u < split: return -a * math.sin(math.pi * u / split * 0.5) ** 2
    v = (u - split) / (1 - split)
    return -a + (1 + a) * back_soft(v)

# ------------------------------------------------------------------ life
def breath_px(t, period=3.6, phase=0.0, amp=1):
    """0 or amp px: the body sinks 1 px on the exhale (held ~40% of the cycle) - reads as calm breathing."""
    u = ((t / period) + phase) % 1.0
    return amp if 0.45 <= u < 0.85 else 0

def blink_face(t, times, base='normal', dur=0.17):
    """'half' -> 'blink' -> 'half' around each blink start."""
    for b in times:
        u = t - b
        if 0 <= u < dur:
            return 'half' if (u < dur * 0.22 or u > dur * 0.72) else 'blink'
    return base

def glance(t, keys, overshoot=0.35, dur=0.09):
    """eye look offsets (lx, ly): keys = [(t, (lx, ly)), ...].  Saccade = very fast move (dur) + a small overshoot;
    holds between keys are still (real eyes jump, they do not drift)."""
    ks = sorted(keys, key=lambda k: k[0])
    if t < ks[0][0]: return ks[0][1]
    i = max(j for j in range(len(ks)) if ks[j][0] <= t)
    t0, p = ks[i]; prev = ks[i - 1][1] if i > 0 else p
    u = (t - t0) / dur
    if u >= 3: return p
    k = back_soft(min(1.0, u), s=1.2 + 2 * overshoot)
    return (int(round(lerp(prev[0], p[0], k))), int(round(lerp(prev[1], p[1], k))))

# ------------------------------------------------------------------ sprite ops
def shear_rotate(rgba, E, deg, pivot):
    """small-angle pixel-art rotation by three integer shears (Paeth): bijective, so no holes, no doubled pixels and
    the outline stays one continuous line (it just gains clean 1px steps).  Best choice up to ~10 degrees.
    positive deg = clockwise on screen (the top moves right)."""
    if abs(deg) < 1e-3: return rgba, E
    a = math.radians(deg)
    t_ = -math.tan(a / 2); s_ = math.sin(a)
    px, py = pivot
    h, w = rgba.shape[:2]
    pad = int(math.ceil(max(h, w) * abs(math.tan(a)))) + 2
    A = np.zeros((h + 2 * pad, w + 2 * pad, 4), rgba.dtype); A[pad:pad + h, pad:pad + w] = rgba
    Ee = np.zeros((h + 2 * pad, w + 2 * pad), np.float32); Ee[pad:pad + h, pad:pad + w] = E
    cx, cy = px + pad, py + pad
    def shx(A, Ee, k):
        oA = np.zeros_like(A); oE = np.zeros_like(Ee)
        for y in range(A.shape[0]):
            d = int(round(k * (y + 0.5 - cy)))
            if d > 0: oA[y, d:] = A[y, :-d]; oE[y, d:] = Ee[y, :-d]
            elif d < 0: oA[y, :d] = A[y, -d:]; oE[y, :d] = Ee[y, -d:]
            else: oA[y] = A[y]; oE[y] = Ee[y]
        return oA, oE
    def shy(A, Ee, k):
        oA = np.zeros_like(A); oE = np.zeros_like(Ee)
        for x in range(A.shape[1]):
            d = int(round(k * (x + 0.5 - cx)))
            if d > 0: oA[d:, x] = A[:-d, x]; oE[d:, x] = Ee[:-d, x]
            elif d < 0: oA[:d, x] = A[-d:, x]; oE[:d, x] = Ee[-d:, x]
            else: oA[:, x] = A[:, x]; oE[:, x] = Ee[:, x]
        return oA, oE
    A, Ee = shx(A, Ee, t_); A, Ee = shy(A, Ee, s_); A, Ee = shx(A, Ee, t_)
    return A[pad:pad + h, pad:pad + w].copy(), Ee[pad:pad + h, pad:pad + w].copy()

def _epx(ids):
    """Scale2x / EPX on an integer id image (equal-colour logic), returns 2x."""
    p = np.pad(ids, 1, mode='edge')
    P_ = p[1:-1, 1:-1]; A = p[:-2, 1:-1]; B = p[1:-1, 2:]; Cc = p[1:-1, :-2]; D = p[2:, 1:-1]
    e0 = np.where((Cc == A) & (Cc != D) & (A != B), A, P_)
    e1 = np.where((A == B) & (A != Cc) & (B != D), B, P_)
    e2 = np.where((D == Cc) & (D != B) & (Cc != A), Cc, P_)
    e3 = np.where((B == D) & (B != A) & (D != Cc), D, P_)
    h, w = ids.shape
    out = np.empty((h * 2, w * 2), ids.dtype)
    out[0::2, 0::2] = e0; out[0::2, 1::2] = e1; out[1::2, 0::2] = e2; out[1::2, 1::2] = e3
    return out

def rotsprite(rgba, E, deg, pivot, steps=3, method='shear'):
    """rotate a pixel sprite about pivot (x, y).  method='shear' (default, see shear_rotate) or 'epx'
    (EPX-upscale 2^steps, rotate nearest, sample block centres - for large angles).  -> (rgba, E) same size."""
    if abs(deg) < 1e-3: return rgba, E
    if method == 'shear': return shear_rotate(rgba, E, deg, pivot)
    h, w = rgba.shape[:2]
    q = np.clip(np.round(E * 63), 0, 63).astype(np.uint32)
    key = (rgba[..., 0].astype(np.uint64) << 32) | (rgba[..., 1].astype(np.uint64) << 24) | (rgba[..., 2].astype(np.uint64) << 16) \
        | (rgba[..., 3].astype(np.uint64) << 8) | q.astype(np.uint64)
    key = np.where(rgba[..., 3] == 0, 0, key)
    uniq, ids = np.unique(key, return_inverse=True)
    ids = ids.reshape(h, w).astype(np.int32)
    for _ in range(steps): ids = _epx(ids)
    f = 2 ** steps
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float64)
    a = math.radians(deg); ca, sa = math.cos(a), math.sin(a)
    px, py = pivot
    dx, dy = xs + 0.5 - px, ys + 0.5 - py
    sx = ca * dx + sa * dy + px; sy = -sa * dx + ca * dy + py
    ix = np.floor(sx * f).astype(np.int64); iy = np.floor(sy * f).astype(np.int64)
    ok = (ix >= 0) & (iy >= 0) & (ix < w * f) & (iy < h * f)
    out_ids = np.zeros((h, w), np.int32)
    out_ids[ok] = ids[iy[ok], ix[ok]]
    k = np.where(ok, uniq[out_ids], 0)
    o = np.zeros_like(rgba)
    o[..., 0] = (k >> 32) & 255; o[..., 1] = (k >> 24) & 255; o[..., 2] = (k >> 16) & 255; o[..., 3] = (k >> 8) & 255
    oE = ((k & 255).astype(np.float32) / 63.0) * (o[..., 3] > 0)
    return o, oE.astype(np.float32)

def shake_rows(a, e, r0, r1, dx):
    """shift rows r0..r1-1 of a sprite sideways by dx px (laugh / shiver).  Returns copies."""
    if not dx: return a, e
    a = a.copy(); e = e.copy()
    a[r0:r1] = np.roll(a[r0:r1], dx, axis=1); e[r0:r1] = np.roll(e[r0:r1], dx, axis=1)
    return a, e

def squash_about(a, e, k, px, py):
    """squash (k>0: wider + shorter) / stretch (k<0) a sprite about the point (px, py) - e.g. the seat contact or the
    feet - so that point stays put.  -> (a, e, ox, oy): add (ox, oy) to the sprite's top-left."""
    if abs(k) < 1e-3: return a, e, 0, 0
    import cv2
    sx, sy = 1.0 + 0.6 * k, 1.0 - k
    h, w = a.shape[:2]
    nw, nh = max(1, int(round(w * sx))), max(1, int(round(h * sy)))
    na = cv2.resize(a, (nw, nh), interpolation=cv2.INTER_NEAREST); ne = cv2.resize(e, (nw, nh), interpolation=cv2.INTER_NEAREST)
    return na, ne, int(round(px - px * nw / w)), int(round(py - py * nh / h))

def merge(body, hands):
    """flatten a claude.draw() result (body + hands sprites) into one (rgba, E)."""
    a = body.cv.a.copy(); e = body.E.copy()
    m = hands.cv.a[..., 3] > 0
    a[m] = hands.cv.a[m]; e[m] = hands.E[m]
    return a, e

def shift_rows(a, e, row, dy):
    """move everything above sprite row `row` down by dy px (head sinks into the shoulders / nods)."""
    if dy == 0: return a, e
    a = a.copy(); e = e.copy()
    if dy > 0:
        top_a, top_e = a[:row].copy(), e[:row].copy()
        m = top_a[..., 3] > 0
        a[:row][m] = 0
        sa = np.zeros_like(top_a); se = np.zeros_like(top_e)
        sa[dy:], se[dy:] = top_a[:-dy], top_e[:-dy]
        reg_a, reg_e = a[:row + dy], e[:row + dy]
        mm = np.zeros(reg_a.shape[:2], bool); mm[:row] = sa[..., 3] > 0
        ext_a = np.zeros_like(reg_a); ext_a[:row] = sa; ext_e = np.zeros_like(reg_e); ext_e[:row] = se
        # rows that crossed into the torso
        ext_a[row:row + dy] = top_a[row - dy:row]; ext_e[row:row + dy] = top_e[row - dy:row]
        mm[row:row + dy] = top_a[row - dy:row, :, 3] > 0
        reg_a[mm] = ext_a[mm]; reg_e[mm] = ext_e[mm]
    else:
        d = -dy
        a[:row - d] = a[d:row].copy(); e[:row - d] = e[d:row].copy()
    return a, e

def lean_rows(a, e, lean, row0, row1):
    """lean the upper body: rows < row0 shift by `lean` px, rows row0..row1 interpolate to 0 (the seat stays)."""
    L = int(round(lean))
    if L == 0: return a, e
    out = np.zeros_like(a); oe = np.zeros_like(e)
    for y in range(a.shape[0]):
        s = L if y < row0 else int(round(L * (row1 - y) / max(1, row1 - row0))) if y < row1 else 0
        if s >= 0: out[y, s:], oe[y, s:] = a[y, :a.shape[1] - s], e[y, :a.shape[1] - s]
        else: out[y, :s], oe[y, :s] = a[y, -s:], e[y, -s:]
    return out, oe


# ------------------------------------------------------------------ light
def bounce_light(a, col=(255, 168, 110), k=0.16, rows=22, bottom=None):
    """warm light bounced up from water / a lit floor: tint the lowest `rows` opaque rows of a sprite toward col,
    strongest at the bottom (k), fading to 0 upward.  bottom = sprite row the gradient starts from (default: last
    opaque row).  Returns a new array (E untouched)."""
    a = a.copy()
    op = a[..., 3] > 0
    ys = np.nonzero(op.any(1))[0]
    if not len(ys): return a
    b = ys[-1] if bottom is None else bottom
    y0 = max(0, b - rows)
    w = np.clip((np.arange(a.shape[0]) - y0) / max(1, b - y0), 0, 1) ** 1.5 * k
    w = w[:, None] * op
    c = np.array(col, np.float32)
    a[..., :3] = (a[..., :3] * (1 - w[..., None]) + c * w[..., None]).astype(np.uint8)
    return a

def flicker(t, seed=0, base=1.0, amp=0.12):
    """lantern / candle flicker multiplier: two incommensurate sines + a fast hash jitter, pure function of t."""
    j = math.sin(t * 13.7 + seed) * 0.5 + math.sin(t * 7.3 + 2.1 * seed) * 0.35 + math.sin(t * 31.0 + seed * 0.7) * 0.15
    return base + amp * j

def turn_track(t, keys, snap=True):
    """head-turn value v (person.head_dir) from keys [(t, v), ...] eased between keys.  snap: show only the drawable
    in-betweens (|v| < 0.5 -> 0 front, < 0.95 -> 0.6) - reads as a quick turn through real drawings, not a smear."""
    ks = sorted(keys, key=lambda k: k[0])
    v = ks[0][1] if t < ks[0][0] else ks[-1][1]
    for (t0, v0), (t1, v1) in zip(ks[:-1], ks[1:]):
        if t0 <= t < t1:
            v = v0 + (v1 - v0) * (EASE['io']((t - t0) / (t1 - t0)) if t1 > t0 else 1.0); break
    if snap and abs(v) < 0.95 and abs(v) not in (0.6,):
        v = 0.0 if abs(v) < 0.5 else math.copysign(0.6, v)
    return v

def contact_shadow(a, col=(40, 22, 30), alpha=190, spread=1):
    """-> (rgba patch, dx, dy) or None: a 1 px dark strip just under the lowest opaque pixel of each column of sprite
    `a` (widened by `spread` px each side) - put it at (x + dx, y + dy) BEFORE the sprite.  Grounds sitting / standing
    characters, stools and props on a floor (a sprite with no contact shadow floats)."""
    op = a[..., 3] > 0
    cols = np.nonzero(op.any(0))[0]
    if not len(cols): return None
    low = np.full(a.shape[1], -1)
    for x in cols: low[x] = np.nonzero(op[:, x])[0][-1]
    ymax = low.max()
    feet = cols[low[cols] >= ymax - 1]                  # only columns that reach the floor line
    if not len(feet): return None
    x0, x1 = feet.min() - spread, feet.max() + spread
    patch = np.zeros((1, x1 - x0 + 1, 4), np.uint8)
    for x in feet:
        patch[0, max(0, x - spread - x0):x + spread - x0 + 1] = (*col, alpha)
    return patch, x0, ymax + 1
