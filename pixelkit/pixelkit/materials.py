"""pixelkit.materials - procedural pixel textures.

Textures are functions of world-space texture coordinates (u, v) (see persp.BoxRoom.uv) that
return a *ramp index field* t (float, 0..n-1).  apply_ramp() turns it into pixels using ordered
dithering only between ADJACENT ramp shades (subtle, like the reference - never the harsh
two-colour halftone look).
"""
import numpy as np
from .core import BAYER4

def _hash2(i, j, seed=0):
    h = (i * 374761393 + j * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0

def value_noise(u, v, scale=16.0, seed=0):
    """smooth value noise in [0,1]"""
    x = np.asarray(u, np.float64) / scale; y = np.asarray(v, np.float64) / scale
    xi = np.floor(x).astype(np.int64); yi = np.floor(y).astype(np.int64)
    fx = x - xi; fy = y - yi
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = _hash2(xi, yi, seed); b = _hash2(xi + 1, yi, seed)
    c = _hash2(xi, yi + 1, seed); d = _hash2(xi + 1, yi + 1, seed)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

def fbm(u, v, scale=24.0, octaves=3, seed=0):
    t = 0; amp = 1; norm = 0
    for o in range(octaves):
        t = t + amp * value_noise(u, v, scale / (2 ** o), seed + 17 * o); norm += amp; amp *= 0.5
    return t / norm

def cell_rand(u, v, cw, ch, seed=0, stagger=0.0):
    """random value per rectangular cell (bricks / tiles / planks)."""
    j = np.floor(np.asarray(v) / ch).astype(np.int64)
    off = (j % 2) * stagger * cw
    i = np.floor((np.asarray(u) + off) / cw).astype(np.int64)
    return _hash2(i, j, seed), i, j

def apply_ramp(t, ramp, x=None, y=None, dither=True, band=2.2):
    """t: float ramp index field (any shape 2D). returns uint8 RGBA array.
    band > 1 narrows the dithered zone to the transition between two shades (pixel-art style:
    mostly solid clusters, short dithered bands). band = 1 -> plain ordered dither."""
    n = len(ramp)
    t = np.clip(np.asarray(t, np.float64), 0, n - 1)
    lo = np.floor(t).astype(np.int64); fr = t - lo
    if band != 1.0:
        fr = np.clip((fr - 0.5) * band + 0.5, 0, 1)
    hi = np.minimum(lo + 1, n - 1)
    if dither:
        if x is None:
            h, w = t.shape; yy, xx = np.mgrid[0:h, 0:w]
        else:
            xx, yy = np.asarray(x).astype(np.int64), np.asarray(y).astype(np.int64)
        th = BAYER4[yy % 4, xx % 4]
        idx = np.where(fr > th, hi, lo)
    else:
        idx = np.where(fr > 0.5, hi, lo)
    pal = np.array(ramp, np.uint8)
    return pal[idx]

# ---------------------------------------------------------------- texture fields (ramp index)
def plaster(u, v, base=3.0, seed=1, mottle=0.55, speck=0.0):
    """mottled painted wall (large soft blotches + rare specks)."""
    t = base + (fbm(u, v, 40.0, 3, seed) - 0.5) * 2 * mottle
    sp = _hash2(np.floor(u).astype(np.int64), np.floor(v).astype(np.int64), seed + 99)
    t = t - (sp > 1 - speck * 0.5) * 0.55 + (sp < speck * 0.3) * 0.45
    return t

def carpet_tiles(u, v, base=2.5, tile=36.0, seed=3):
    r, i, j = cell_rand(u, v, tile, tile, seed)
    t = base + (r - 0.5) * 0.7
    # pile direction stripes alternate per tile (quarter-turn layout)
    alt = ((i + j) % 2) == 0
    q = np.where(alt, np.asarray(u), np.asarray(v))
    t = t + (np.floor(q / 2.0) % 2) * 0.35 - 0.17
    # seams
    fu = np.mod(u, tile); fv = np.mod(v, tile)
    seam = (fu < 1.0) | (fv < 1.0)
    t = t - seam * 0.9
    t = t + (fbm(u, v, 60.0, 2, seed + 5) - 0.5) * 0.8      # wear / soft variation
    return t

def planks(u, v, base=3.0, pw=10.0, pl=64.0, seed=5, along='u'):
    """wood planks. along='u': planks run along u (rows stacked in v)."""
    a, b = (u, v) if along == 'u' else (v, u)
    r, i, j = cell_rand(a, b, pl, pw, seed, stagger=0.37)
    t = base + (r - 0.5) * 0.8
    g = value_noise(np.asarray(a) * 0.15, np.asarray(b) * 2.2, 3.0, seed + 7)  # long grain streaks
    t = t + (g - 0.5) * 0.6
    fb = np.mod(b, pw); fa = np.mod(np.asarray(a) + (j % 2) * 0.37 * pl, pl)
    t = t - (fb < 1.0) * 1.6 - (fa < 1.0) * 1.2      # gaps / joints darker
    t = t + ((fb >= 1.0) & (fb < 2.0)) * 0.5        # top edge catches light
    return t

def ceiling_tiles(u, v, base=3.5, tile=30.0, seed=9):
    fu = np.mod(u, tile); fv = np.mod(v, tile)
    grid = (fu < 1.2) | (fv < 1.2)
    sp = _hash2(np.floor(u * 1.0).astype(np.int64), np.floor(v * 1.0).astype(np.int64), seed)
    t = base + (sp > 0.93) * -0.7 + (fbm(u, v, 50, 2, seed) - 0.5) * 0.5
    return np.where(grid, base - 1.4, t)

def fabric(u, v, base=3.0, seed=11):
    """woven partition fabric: tight 2px weave + soft mottling"""
    ui = np.floor(u).astype(np.int64); vi = np.floor(v).astype(np.int64)
    weave = ((ui + vi) % 2) * 0.32
    return base + weave - 0.16 + (fbm(u, v, 30, 2, seed) - 0.5) * 0.6

def brick(u, v, base=3.0, bw=16.0, bh=6.0, seed=13):
    r, i, j = cell_rand(u, v, bw, bh, seed, stagger=0.5)
    fb = np.mod(v, bh); fa = np.mod(np.asarray(u) + (j % 2) * 0.5 * bw, bw)
    mortar = (fb < 1.0) | (fa < 1.0)
    return np.where(mortar, base + 1.2, base + (r - 0.5) * 1.3)

def vgrad(y, y0, y1, t0, t1):
    k = np.clip((np.asarray(y, np.float64) - y0) / max(1e-6, y1 - y0), 0, 1)
    return t0 + (t1 - t0) * k
