"""pixelkit.palette - hue-shifted colour ramps.

Pixel-art rule (matches the reference): shadows are NOT just darker, they shift toward
cool purple/blue; highlights shift toward warm yellow.  ramp() builds such ramps in OKLab.
"""
import numpy as np

def hex2rgb(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64) / 255.0

def rgb2hex(c):
    c = np.clip(np.round(np.asarray(c) * 255), 0, 255).astype(int); return '#%02x%02x%02x' % tuple(c)

def _lin(c): c = np.asarray(c, np.float64); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def _gam(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

def srgb_to_oklab(c):
    r, g, b = _lin(c)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.array([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s])

def oklab_to_srgb(lab):
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return _gam(np.array([r, g, bb]))

def _lch(c):
    L, a, b = srgb_to_oklab(c); return L, np.hypot(a, b), np.degrees(np.arctan2(b, a)) % 360

def _from_lch(L, C, H):
    h = np.radians(H); return oklab_to_srgb(np.array([L, C * np.cos(h), C * np.sin(h)]))

def _hue_toward(h, target, amt):
    d = ((target - h + 180) % 360) - 180
    return (h + d * amt) % 360

SHADOW_HUE = 290.0     # purple-blue
LIGHT_HUE = 85.0       # warm yellow

def ramp(base, n=6, dark=0.30, light=0.93, hue_dark=0.30, hue_light=0.25, chroma_dark=0.85,
         chroma_light=0.55, base_index=None):
    """Hue-shifted ramp from a base hex colour. Returns list of RGBA tuples (dark -> light).
    The base colour sits at base_index (default: n//2)."""
    L0, C0, H0 = _lch(hex2rgb(base))
    bi = n // 2 if base_index is None else base_index
    out = []
    for i in range(n):
        if i < bi:
            k = (bi - i) / max(1, bi)
            L = L0 + (dark - L0) * k
            C = C0 * (1 + (chroma_dark - 1) * k)
            H = _hue_toward(H0, SHADOW_HUE, hue_dark * k)
        elif i > bi:
            k = (i - bi) / max(1, n - 1 - bi)
            L = L0 + (light - L0) * k
            C = C0 * (1 + (chroma_light - 1) * k)
            H = _hue_toward(H0, LIGHT_HUE, hue_light * k)
        else:
            L, C, H = L0, C0, H0
        c = _from_lch(L, C, H)
        out.append(tuple(int(round(v * 255)) for v in c) + (255,))
    return out

def mixc(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3)) + (255,)

def swatch(ramps, path, cell=24):
    """save a swatch image of named ramps {name: ramp} for review."""
    import cv2
    names = list(ramps)
    n = max(len(r) for r in ramps.values())
    img = np.zeros((len(names) * cell, n * cell + 120, 3), np.uint8) + 30
    for j, k in enumerate(names):
        for i, c in enumerate(ramps[k]):
            img[j * cell:(j + 1) * cell, 120 + i * cell:120 + (i + 1) * cell] = c[2::-1][:3] if False else (c[2], c[1], c[0])
        cv2.putText(img, k[:14], (4, j * cell + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1)
    cv2.imwrite(path, img)
