"""pixelkit.edit - several shots on ONE global timeline + transitions (the film's edit decision list).

    ed = Edit()
    ed.add('office', 0.0,  office.frame)                       # shot runs until the next shot starts
    ed.add('clock', 21.0,  clock.frame, 'zoomcut')             # hard cut (named for readability)
    ed.add('night', 37.0,  night.frame, 'dissolve', 0.8)       # crossfade centred on 37.0
    ed.add('title', 41.4,  title.frame, 'fade', 0.6)           # out to black 0.3 s, in 0.3 s
    ed.end(45.6)
    img = ed.frame(t)              # float RGB (OH, OW, 3)
    ed.shot_at(t) -> name          # e.g. for audio routing / debugging

Shots are called with the GLOBAL time t (timeline.py stays the single source of truth).  The transition
belongs to the incoming shot:
    'cut' | 'zoomcut'       hard cut
    'dissolve', d           crossfade over [t0 - d/2, t0 + d/2] (both shots rendered there)
    'fade', d               A fades to black over [t0 - d/2, t0), B fades in over [t0, t0 + d/2)
    'flash', d              hard cut hidden in a white flash peaking at t0 (d = total flash length)
    'whip', d, dir          whip pan: A smears out in direction dir (+1 = content moves left), B smears in
"""
import math
import numpy as np, cv2


def _ss(u):
    u = min(max(u, 0.0), 1.0); return u * u * (3 - 2 * u)


class Shot:
    def __init__(self, name, t0, fn, kind='cut', d=0.0, **opt):
        self.name, self.t0, self.fn, self.kind, self.d, self.opt = name, float(t0), fn, kind, float(d), opt
        self.t1 = None

    @property
    def pre(self):           # how long before t0 the transition starts
        return self.d / 2 if self.kind in ('dissolve', 'fade', 'flash', 'whip') else 0.0

    @property
    def post(self):
        return self.d / 2 if self.kind in ('dissolve', 'fade', 'flash', 'whip') else 0.0


class Edit:
    def __init__(self):
        self.shots = []; self.t_end = None

    def add(self, name, t0, fn, kind='cut', d=0.0, **opt):
        s = Shot(name, t0, fn, kind, d, **opt)
        if self.shots: self.shots[-1].t1 = s.t0
        self.shots.append(s); return s

    def end(self, t_end):
        self.t_end = float(t_end); self.shots[-1].t1 = self.t_end; return self

    def index_at(self, t):
        i = 0
        for k, s in enumerate(self.shots):
            if t >= s.t0: i = k
        return i

    def shot_at(self, t): return self.shots[self.index_at(t)].name

    def cuts(self): return [(s.name, s.t0, s.kind, s.d) for s in self.shots]

    # ------------------------------------------------------------------ frame
    def frame(self, t):
        i = self.index_at(t)
        cur = self.shots[i]
        nxt = self.shots[i + 1] if i + 1 < len(self.shots) else None
        # inside the incoming half of the NEXT shot's transition?
        if nxt is not None and t >= nxt.t0 - nxt.pre:
            return self._trans(self.shots[i], nxt, t)
        # inside the outgoing half of the CURRENT shot's transition?
        if i > 0 and t < cur.t0 + cur.post:
            return self._trans(self.shots[i - 1], cur, t)
        return cur.fn(t)

    def _trans(self, A, B, t):
        k, d, t0 = B.kind, max(B.d, 1e-6), B.t0
        if k == 'dissolve':
            u = _ss((t - (t0 - d / 2)) / d)
            if u <= 0.0: return A.fn(t)
            if u >= 1.0: return B.fn(t)
            return A.fn(t) * (1 - u) + B.fn(t) * u
        if k == 'fade':
            if t < t0: return A.fn(t) * (1 - _ss((t - (t0 - d / 2)) / (d / 2)))
            return B.fn(t) * _ss((t - t0) / (d / 2))
        if k == 'flash':
            img = A.fn(t) if t < t0 else B.fn(t)
            w = max(0.0, 1 - abs(t - t0) / (d / 2)) ** B.opt.get('power', 1.5) * B.opt.get('peak', 1.0)
            col = np.asarray(B.opt.get('color', (1.0, 0.97, 0.9)), np.float32)
            return img * (1 - w) + col * w
        if k == 'whip':
            dirn = B.opt.get('dir', 1)
            if t < t0:
                u = (t - (t0 - d / 2)) / (d / 2); img = A.fn(t); s = (u ** 2) * dirn
            else:
                u = 1 - (t - t0) / (d / 2); img = B.fn(t); s = -(u ** 2) * dirn
            return whip(img, s)
        return A.fn(t) if t < t0 else B.fn(t)


def whip(img, s, max_blur=0.22, max_shift=0.35):
    """horizontal whip-pan smear: s in -1..1 (sign = direction, |s| = strength)."""
    H, W = img.shape[:2]
    a = abs(s)
    if a < 1e-3: return img
    k = int(max(1, a * max_blur * W)) | 1
    out = cv2.blur(img, (k, 1), borderType=cv2.BORDER_REFLECT)
    shift = -s * max_shift * W
    M = np.float32([[1, 0, shift], [0, 1, 0]])
    out = cv2.warpAffine(out, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out * (1 - 0.15 * a) + out.mean(axis=(0, 1), keepdims=True) * 0.15 * a


def zoom_blur(img, k, cx=0.5, cy=0.5, n=6):
    """radial zoom blur (crash zoom), k = strength 0..~0.15 (scale spread of the samples)."""
    if k < 1e-3: return img
    H, W = img.shape[:2]
    acc = img.astype(np.float32).copy(); wsum = 1.0
    for i in range(1, n + 1):
        s = 1 + k * i / n
        M = np.float32([[s, 0, (1 - s) * cx * W], [0, s, (1 - s) * cy * H]])
        acc += cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        wsum += 1
    return acc / wsum


# ---------------------------------------------------------------------- screen zoom (ACT III v2)
HOLO = (0.42, 0.85, 1.0)

def screen_zoom(base, inset, rect, k, border=HOLO, bw=4, scan=True, t=0.0):
    """open a full-frame 'inset' shot OUT OF a small rectangle of 'base' (a character's face screen, a phone, a monitor)
    or fold it back (run k 1 -> 0).
      base, inset : float RGB frames (H, W, 3) of the same size
      rect        : (x0, y0, x1, y1) of the start rectangle in output px
      k           : 0 = inset hidden inside rect .. 1 = inset fills the frame
    The rect is interpolated to the full frame with an ease, the inset is area-resized into it (no pixel shimmer),
    a glowing border (bw px) + faint scanlines sell 'it is a screen' and fade out as the rect fills the frame."""
    import cv2
    H, W = base.shape[:2]
    if k <= 0: return base
    if k >= 1: return inset
    e = k * k * (3 - 2 * k)
    x0, y0, x1, y1 = rect
    X0 = x0 * (1 - e); Y0 = y0 * (1 - e); X1 = x1 + (W - x1) * e; Y1 = y1 + (H - y1) * e
    X0, Y0, X1, Y1 = int(round(X0)), int(round(Y0)), int(round(X1)), int(round(Y1))
    w, h = max(2, X1 - X0), max(2, Y1 - Y0)
    out = base.copy()
    small = cv2.resize(inset, (w, h), interpolation=cv2.INTER_AREA)
    a_in = min(1.0, k / 0.18)                                     # fade the picture in on the screen first
    xa, ya, xb, yb = max(0, X0), max(0, Y0), min(W, X0 + w), min(H, Y0 + h)
    reg = small[ya - Y0:yb - Y0, xa - X0:xb - X0]
    if scan and k < 0.85:
        s = np.ones((reg.shape[0], 1, 1), np.float32)
        s[(np.arange(reg.shape[0]) + int(t * 120)) % 4 == 0] = 1.0 - 0.18 * (1 - k / 0.85)
        reg = reg * s
    out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - a_in) + reg * a_in
    ba = max(0.0, 1 - max(0.0, k - 0.55) / 0.4)                   # border fades as it fills the frame
    if ba > 0:
        col = np.array(border, np.float32) * 1.25
        for (p, q, r, s_) in ((X0 - bw, Y0 - bw, X1 + bw, Y0), (X0 - bw, Y1, X1 + bw, Y1 + bw),
                              (X0 - bw, Y0, X0, Y1), (X1, Y0, X1 + bw, Y1)):
            p, q, r, s_ = max(0, p), max(0, q), min(W, r), min(H, s_)
            if r > p and s_ > q: out[q:s_, p:r] = out[q:s_, p:r] * (1 - ba) + col * ba
        glow = np.zeros((H, W), np.float32)
        cv2.rectangle(glow, (X0 - bw, Y0 - bw), (X1 + bw, Y1 + bw), 1.0, bw * 2)
        glow = cv2.GaussianBlur(glow, (0, 0), 6 + 10 * e)
        out = out + glow[..., None] * np.array(border, np.float32) * 0.45 * ba
    return out
