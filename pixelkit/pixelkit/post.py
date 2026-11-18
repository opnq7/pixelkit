"""pixelkit.post - output-resolution post FX tuned to the reference look.

Order used by scene.Renderer:   lit image -> + god rays -> bloom/halation -> grade -> vignette
-> grain -> (UI on top, un-graded).  All functions take/return float32 RGB in 0..1+ (display
referred), shape (OH, OW, 3).
"""
import numpy as np, cv2

def lum(img):
    return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722

def _down(img, w, h):
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)

def bloom(img, thr=0.72, knee=0.25, strength=0.6, tint=(1.0, 0.86, 0.70), radii=(3, 9, 24), weights=(0.5, 0.7, 0.8),
          halation=0.0, hal_tint=(1.0, 0.35, 0.15), extra=None):
    """multi-scale bloom (soft knee threshold) + optional red-orange halation.
    extra: optional float map (same size as img) of additional glow sources (e.g. emissive)."""
    OH, OW = img.shape[:2]
    w0, h0 = OW // 4, OH // 4
    small = _down(img, w0, h0)
    if extra is not None: small = small + _down(extra, w0, h0)
    l = small.max(axis=2, keepdims=True)
    # soft knee
    x = l - thr
    soft = np.clip(x + knee, 0, 2 * knee) ** 2 / (4 * knee + 1e-6)
    contrib = np.maximum(soft, x) / np.maximum(l, 1e-4)
    bright = small * np.clip(contrib, 0, 8)
    acc = np.zeros_like(bright)
    for r, wgt in zip(radii, weights):
        sc = max(1, int(r // 6))
        b = _down(bright, max(8, w0 // sc), max(8, h0 // sc)) if sc > 1 else bright
        b = cv2.GaussianBlur(b, (0, 0), r / sc)
        if sc > 1: b = cv2.resize(b, (w0, h0), interpolation=cv2.INTER_LINEAR)
        acc += b * wgt
    acc *= np.asarray(tint, np.float32)
    if halation > 0:
        hb = cv2.GaussianBlur(_down(bright, w0 // 2, h0 // 2), (0, 0), 6)
        acc += cv2.resize(hb, (w0, h0), interpolation=cv2.INTER_LINEAR) * np.asarray(hal_tint, np.float32) * halation
    up = cv2.resize(acc, (OW, OH), interpolation=cv2.INTER_LINEAR)
    return img + up * strength

def _soft(x, k):
    over = np.maximum(x - k, 0)
    return np.where(x > k, k + (1 - k) * (1 - np.exp(-over / (1 - k))), x)

def tonemap(img, shoulder=0.80, bleach=0.5):
    """soft-clip highlights above `shoulder`.
    bleach 0 = hue-preserving (scale by max channel); 1 = per-channel film roll-off (hot highlights
    bleach toward warm white like the reference's sun spots and lamp glow)."""
    m = img.max(axis=2, keepdims=True)
    hp = img * (_soft(m, shoulder) / np.maximum(m, 1e-6))
    if bleach <= 0: return hp
    pc = _soft(img, shoulder)
    return hp * (1 - bleach) + pc * bleach

def split_tone(img, shadow=(0.10, 0.00, 0.16), highlight=(0.10, 0.05, -0.06), pivot=0.42, width=0.30, amount=1.0):
    """add colour to shadows / highlights (offsets in RGB, scaled by luminance masks)."""
    L = lum(img)[..., None]
    ws = np.clip(1 - L / pivot, 0, 1) ** 1.5
    wh = np.clip((L - pivot) / max(1e-6, 1 - pivot), 0, 1) ** 1.2
    return img + amount * (ws * np.asarray(shadow, np.float32) * 0.5 + wh * np.asarray(highlight, np.float32) * 0.5)

def saturation(img, sat=1.2, vib=0.0):
    L = lum(img)[..., None]
    d = img - L
    if vib:
        c = np.abs(d).max(axis=2, keepdims=True)
        sat = sat * (1 + vib * (1 - np.clip(c * 3, 0, 1)))
    return L + d * sat

def contrast(img, c=1.1, pivot=0.40, black=0.0, white=1.0, gamma=1.0):
    out = (img - pivot) * c + pivot
    out = (out - black) / max(1e-6, white - black)
    if gamma != 1.0: out = np.sign(out) * np.abs(out) ** gamma
    return out

def lift_gamma_gain(img, lift=(0, 0, 0), gamma=(1, 1, 1), gain=(1, 1, 1)):
    x = np.clip(img, 0, None) * np.asarray(gain, np.float32)
    x = x + np.asarray(lift, np.float32) * (1 - np.clip(x, 0, 1))
    g = np.asarray(gamma, np.float32)
    return np.power(np.clip(x, 0, None), 1 / g)

class Finisher:
    """vignette + grain cache for a given output size."""
    def __init__(self, OW=1920, OH=1080, seed=5, n_grain=12):
        yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
        self.r = np.sqrt(((xx - OW / 2) / (OW / 2)) ** 2 * 0.80 + ((yy - OH / 2) / (OH / 2)) ** 2)
        rng = np.random.default_rng(seed)
        self.grain = []
        for i in range(n_grain):
            g = rng.normal(0, 1, (OH // 2, OW // 2)).astype(np.float32)
            g = cv2.GaussianBlur(g, (0, 0), 0.7)
            self.grain.append(cv2.resize(g, (OW, OH), interpolation=cv2.INTER_LINEAR))
        self._vig = {}

    def vignette(self, img, strength=0.35, power=2.2, tint=(0.95, 0.85, 1.0)):
        key = (round(strength, 3), power)
        if key not in self._vig:
            v = 1.0 - strength * np.clip(self.r, 0, 1.7) ** power
            self._vig[key] = np.clip(v, 0, 1)[..., None].astype(np.float32)
        v = self._vig[key]
        # tinted vignette: darkening leans purple instead of grey
        return img * (v + (1 - v) * (1 - np.asarray(tint, np.float32)) * 0.0) * (1 - (1 - v) * (1 - np.asarray(tint, np.float32)))

    def add_grain(self, img, frame, amount=0.018):
        if amount <= 0: return img
        g = self.grain[frame % len(self.grain)][..., None]
        L = lum(np.clip(img, 0, 1))[..., None]
        return img + g * amount * (0.35 + 0.65 * (1 - np.abs(L - 0.45) * 1.6).clip(0, 1))

# ---------------------------------------------------------------- presets
GRADES = {
    # matched to the reference interiors (see docs/STYLE_GUIDE.md "measured targets")
    'golden_hd2d': dict(exposure=1.0, shoulder=0.82, bleach=0.7, shadow=(0.16, -0.02, 0.22), highlight=(0.10, 0.04, -0.10),
                        pivot=0.40, sat=1.12, vib=0.25, contrast=1.16, cpivot=0.36, black=0.03, gamma=1.0,
                        vignette=0.34, grain=0.016,
                        bloom=dict(thr=0.70, knee=0.25, strength=0.55, tint=(1.0, 0.84, 0.66), halation=0.25)),
    'morning_hd2d': dict(exposure=1.0, shoulder=0.82, bleach=0.6, shadow=(0.08, 0.02, 0.22), highlight=(0.10, 0.06, -0.06),
                        pivot=0.40, sat=1.10, vib=0.25, contrast=1.14, cpivot=0.36, black=0.03, gamma=1.0,
                        vignette=0.32, grain=0.016,
                        bloom=dict(thr=0.70, knee=0.25, strength=0.55, tint=(1.0, 0.90, 0.74), halation=0.22)),
    'night_hd2d': dict(exposure=1.0, shoulder=0.85, bleach=0.5, shadow=(0.04, 0.02, 0.20), highlight=(0.06, 0.05, -0.04),
                       pivot=0.35, sat=1.15, vib=0.2, contrast=1.08, cpivot=0.30, black=0.015, gamma=1.0,
                       vignette=0.40, grain=0.02,
                       bloom=dict(thr=0.55, knee=0.25, strength=0.7, tint=(0.85, 0.9, 1.0), halation=0.15)),
    'neutral': dict(exposure=1.0, shoulder=0.9, bleach=0.0, shadow=(0, 0, 0), highlight=(0, 0, 0), pivot=0.4, sat=1.0, vib=0,
                    contrast=1.0, cpivot=0.4, black=0.0, gamma=1.0, vignette=0.0, grain=0.0,
                    bloom=dict(thr=0.9, knee=0.2, strength=0.0)),
}

def lerp_grade(a, b, k):
    A, B = GRADES[a] if isinstance(a, str) else a, GRADES[b] if isinstance(b, str) else b
    out = {}
    for key in A:
        va, vb = A[key], B[key]
        if isinstance(va, dict): out[key] = lerp_grade(va, vb, k)
        elif isinstance(va, tuple): out[key] = tuple(x + (y - x) * k for x, y in zip(va, vb))
        else: out[key] = va + (vb - va) * k
    return out

def apply_grade(img, g, finisher=None, frame=0, bloom_extra=None):
    img = img * g.get('exposure', 1.0)
    b = g.get('bloom')
    if b and b.get('strength', 0) > 0:
        img = bloom(img, extra=bloom_extra, **b)
    img = tonemap(img, g['shoulder'], g.get('bleach', 0.5))
    img = split_tone(img, g['shadow'], g['highlight'], g['pivot'])
    img = saturation(img, g['sat'], g.get('vib', 0))
    img = contrast(img, g['contrast'], g['cpivot'], g['black'], 1.0, g.get('gamma', 1.0))
    if finisher is not None:
        if g.get('vignette', 0) > 0: img = finisher.vignette(img, g['vignette'])
        img = finisher.add_grain(img, frame, g.get('grain', 0))
    return img

def to_u8(img):
    return np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)
