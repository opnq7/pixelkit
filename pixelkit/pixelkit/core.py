"""pixelkit.core - pixel-art canvas + drawing primitives (numpy RGBA uint8).

All world art is drawn on small native-resolution canvases (e.g. 480x270) and later
upscaled by the camera with crisp (nearest) pixels."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import functools, os

FONT_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts')
FONT_FILES = {
    'zh12': '12px-proportional/fusion-pixel-12px-proportional-zh_hans.ttf',
    'zh10': '10px-proportional/fusion-pixel-10px-proportional-zh_hans.ttf',
    'zh8': '8px-proportional/fusion-pixel-8px-proportional-zh_hans.ttf',
    'silk': 'Silkscreen.ttf', 'silkb': 'SilkscreenBold.ttf', 'p2p': 'PressStart2P.ttf',
}
FONT_SIZE = {'zh12': 12, 'zh10': 10, 'zh8': 8, 'silk': 8, 'silkb': 8, 'p2p': 8}

def C(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) / 16.0 + 1/32

def mix(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(4))

@functools.lru_cache(maxsize=64)
def font(name, size=None):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONT_FILES[name]), size or FONT_SIZE[name])

@functools.lru_cache(maxsize=4096)
def text_mask(s, fname, size=None):
    f = font(fname, size)
    l, t, r, b = f.getbbox(s)
    w = max(1, r) + 2; h = (size or FONT_SIZE[fname]) + 6
    im = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(im); d.fontmode = '1'
    d.text((0, 0), s, font=f, fill=255)
    m = np.array(im) > 127
    return m

def text_width(s, fname, size=None):
    m = text_mask(s, fname, size)
    cols = np.where(m.any(axis=0))[0]
    return int(cols[-1] + 1) if len(cols) else 0

def _over(dst, src_rgb, a_s):
    """Straight-alpha 'over'. dst float (...,4) 0..255; src_rgb (...,3) or (3,); a_s scalar or (...,1)."""
    a_d = dst[..., 3:4] / 255.0
    a_s = np.asarray(a_s, np.float32)
    if a_s.ndim == 0: a_s = np.full(a_d.shape, float(a_s), np.float32)
    out_a = a_s + a_d * (1 - a_s)
    rgb = (src_rgb * a_s + dst[..., :3] * a_d * (1 - a_s)) / np.maximum(out_a, 1e-6)
    out = np.concatenate([rgb, out_a * 255.0], axis=-1)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)

class Canvas:
    def __init__(self, w, h, fill=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.a = np.zeros((h, w, 4), dtype=np.uint8)
        if fill[3] or any(fill[:3]):
            self.a[:] = fill

    def copy(self):
        c = Canvas(self.w, self.h); c.a = self.a.copy(); return c

    def _clip(self, x0, y0, x1, y1):
        return max(0, x0), max(0, y0), min(self.w, x1), min(self.h, y1)

    def rect(self, x, y, w, h, col):
        x0, y0, x1, y1 = self._clip(int(x), int(y), int(x + w), int(y + h))
        if x1 > x0 and y1 > y0:
            if col[3] == 255:
                self.a[y0:y1, x0:x1] = col
            else:
                self.blend_rect(x0, y0, x1, y1, col)

    def blend_rect(self, x0, y0, x1, y1, col):
        reg = self.a[y0:y1, x0:x1].astype(np.float32)
        self.a[y0:y1, x0:x1] = _over(reg, np.array(col[:3], np.float32), col[3] / 255.0)

    def px(self, x, y, col):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = col

    def hline(self, x, y, w, col): self.rect(x, y, w, 1, col)
    def vline(self, x, y, h, col): self.rect(x, y, 1, h, col)

    def line(self, x0, y0, x1, y1, col):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.px(x0, y0, col)
            if x0 == x1 and y0 == y1: break
            e2 = 2 * err
            if e2 >= dy: err += dy; x0 += sx
            if e2 <= dx: err += dx; y0 += sy

    def rrect(self, x, y, w, h, col, r=1):
        """Filled rect with pixel-rounded corners (r = 1 or 2 or 3)."""
        x, y, w, h = int(x), int(y), int(w), int(h)
        if r <= 0:
            self.rect(x, y, w, h, col); return
        insets = {1: [1], 2: [2, 1], 3: [3, 1, 1], 4: [4, 2, 1, 1], 5: [5, 3, 2, 1, 1], 6: [6, 4, 3, 2, 1, 1]}[min(r, 6)]
        n = len(insets)
        self.rect(x, y + n, w, h - 2 * n, col)
        for i, ins in enumerate(insets):
            self.rect(x + ins, y + i, w - 2 * ins, 1, col)
            self.rect(x + ins, y + h - 1 - i, w - 2 * ins, 1, col)

    def outline_rrect(self, x, y, w, h, fill, outline, r=1):
        self.rrect(x, y, w, h, outline, r)
        self.rrect(x + 1, y + 1, w - 2, h - 2, fill, max(0, r - 1))

    def ellipse(self, cx, cy, rx, ry, col):
        y0, y1 = int(np.floor(cy - ry)), int(np.ceil(cy + ry))
        for yy in range(y0, y1 + 1):
            dy = (yy + 0.5 - cy) / max(ry, 1e-6)
            if abs(dy) > 1: continue
            hw = rx * np.sqrt(1 - dy * dy)
            xa, xb = int(round(cx - hw)), int(round(cx + hw))
            if xb > xa: self.rect(xa, yy, xb - xa, 1, col)

    def dither_v(self, x, y, w, h, c_top, c_bot, steps=None, ox=0, oy=0):
        """Vertical gradient using ordered dithering between two colors."""
        x0, y0, x1, y1 = self._clip(int(x), int(y), int(x + w), int(y + h))
        if x1 <= x0 or y1 <= y0: return
        ys = np.arange(y0, y1)
        t = (ys - y) / max(1, h - 1)
        t = t[:, None]
        xs = np.arange(x0, x1)
        th = BAYER4[(ys[:, None] + oy) % 4, (xs[None, :] + ox) % 4]
        m = t > th
        a = np.where(m[..., None], np.array(c_bot, np.uint8), np.array(c_top, np.uint8))
        self.a[y0:y1, x0:x1] = a

    def dither_field(self, x, y, w, h, c0, c1, tfield):
        """tfield: (h,w) float 0..1 -> dithered between c0 and c1."""
        x, y = int(x), int(y)
        ys = np.arange(y, y + h); xs = np.arange(x, x + w)
        th = BAYER4[ys[:, None] % 4, xs[None, :] % 4]
        m = tfield > th
        a = np.where(m[..., None], np.array(c1, np.uint8), np.array(c0, np.uint8))
        x0, y0, x1, y1 = self._clip(x, y, x + w, y + h)
        if x1 > x0 and y1 > y0:
            self.a[y0:y1, x0:x1] = a[y0 - y:y1 - y, x0 - x:x1 - x]

    def checker(self, x, y, w, h, col, phase=0):
        x0, y0, x1, y1 = self._clip(int(x), int(y), int(x + w), int(y + h))
        if x1 <= x0 or y1 <= y0: return
        ys = np.arange(y0, y1)[:, None]; xs = np.arange(x0, x1)[None, :]
        m = ((xs + ys + phase) % 2) == 0
        reg = self.a[y0:y1, x0:x1]
        reg[m] = col

    def blit(self, spr, x, y, alpha_mul=1.0):
        """Blit an RGBA uint8 array with binary alpha (or blended if alpha_mul<1)."""
        x, y = int(round(x)), int(round(y))
        sh, sw = spr.shape[:2]
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + sw), min(self.h, y + sh)
        if x1 <= x0 or y1 <= y0: return
        s = spr[y0 - y:y1 - y, x0 - x:x1 - x]
        d = self.a[y0:y1, x0:x1]
        if alpha_mul >= 0.999:
            m = s[..., 3] > 127
            d[m] = s[m]
            d[m, 3] = 255
        else:
            a = (s[..., 3:4].astype(np.float32) / 255.0) * alpha_mul
            d[:] = _over(d.astype(np.float32), s[..., :3].astype(np.float32), a)

    def text(self, x, y, s, col, fname='zh12', size=None, shadow=None, outline=None):
        m = text_mask(s, fname, size)
        if outline is not None:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                self._mask(m, x + dx, y + dy, outline)
        if shadow is not None:
            self._mask(m, x + 1, y + 1, shadow)
        self._mask(m, x, y, col)
        return m.shape[1]

    def _mask(self, m, x, y, col):
        x, y = int(x), int(y)
        mh, mw = m.shape
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + mw), min(self.h, y + mh)
        if x1 <= x0 or y1 <= y0: return
        mm = m[y0 - y:y1 - y, x0 - x:x1 - x]
        reg = self.a[y0:y1, x0:x1]
        if col[3] == 255:
            reg[mm] = col
        else:
            sub = reg[mm].astype(np.float32)
            reg[mm] = _over(sub, np.array(col[:3], np.float32), col[3] / 255.0)

def sprite(rows, pal):
    h = len(rows); w = max(len(r) for r in rows)
    a = np.zeros((h, w, 4), np.uint8)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in pal and pal[ch] is not None:
                a[y, x] = pal[ch]
    return a

def flip(spr):
    return spr[:, ::-1].copy()

def outline_sprite(spr, col):
    """Add 1px outline around opaque pixels (grows sprite by 1 on each side)."""
    h, w = spr.shape[:2]
    out = np.zeros((h + 2, w + 2, 4), np.uint8)
    m = spr[..., 3] > 127
    mm = np.zeros((h + 2, w + 2), bool)
    for dx, dy in [(0, 1), (2, 1), (1, 0), (1, 2)]:
        mm[dy:dy + h, dx:dx + w] |= m
    out[mm] = col
    inner = out[1:h + 1, 1:w + 1]
    inner[m] = spr[m]
    return out

def recolor(spr, mapping):
    s = spr.copy()
    for src, dst in mapping.items():
        m = np.all(spr[..., :3] == np.array(src[:3], np.uint8), axis=-1) & (spr[..., 3] > 0)
        s[m] = dst
    return s

# ----------------------------------------------------------------------------------------
# additions for pixelkit
# ----------------------------------------------------------------------------------------
import cv2

def rgb(col):
    """RGBA tuple -> float32 rgb 0..1"""
    return np.array(col[:3], np.float32) / 255.0

def shade(col, f, a=None):
    """multiply colour brightness (keeps alpha)."""
    return tuple(int(max(0, min(255, round(c * f)))) for c in col[:3]) + ((col[3] if a is None else a),)

def poly_mask(w, h, pts, f=1):
    """Filled polygon mask (h*f, w*f) bool. pts in canvas pixel coords (floats ok)."""
    m = np.zeros((int(h * f), int(w * f)), np.uint8)
    p = np.round(np.asarray(pts, np.float64) * f * 16).astype(np.int32)
    cv2.fillPoly(m, [p], 1, lineType=cv2.LINE_8, shift=4)
    return m.astype(bool)

def _cv_fill(self, mask, col):
    """fill bool mask (same size as canvas) with colour."""
    if col[3] == 255:
        self.a[mask] = col
    else:
        sub = self.a[mask].astype(np.float32)
        self.a[mask] = _over(sub, np.array(col[:3], np.float32), col[3] / 255.0)
Canvas.fill_mask = _cv_fill

def _cv_poly(self, pts, col):
    self.fill_mask(poly_mask(self.w, self.h, pts), col)
Canvas.poly = _cv_poly

def _cv_paste(self, img, x, y, mask=None):
    """paste an RGBA/RGB array honoring its alpha (binary)."""
    if img.shape[2] == 3:
        img = np.concatenate([img, np.full(img.shape[:2] + (1,), 255, np.uint8)], 2)
    if mask is not None:
        img = img.copy(); img[..., 3] = np.where(mask, img[..., 3], 0)
    self.blit(img, x, y)
Canvas.paste = _cv_paste

def scale_nearest(spr, sx, sy=None):
    sy = sx if sy is None else sy
    h, w = spr.shape[:2]
    nw, nh = max(1, int(round(w * sx))), max(1, int(round(h * sy)))
    return cv2.resize(spr, (nw, nh), interpolation=cv2.INTER_NEAREST)

def squash(spr, k, anchor='bottom'):
    """squash & stretch. k>0 squash (wider, shorter), k<0 stretch. returns (sprite, dx, dy)
    offsets to keep the anchor fixed."""
    h, w = spr.shape[:2]
    sy = 1.0 - k; sx = 1.0 + k * 0.6
    out = scale_nearest(spr, sx, sy)
    nh, nw = out.shape[:2]
    dx = (w - nw) / 2.0
    dy = (h - nh) if anchor == 'bottom' else (h - nh) / 2.0
    return out, dx, dy

def sel_out(spr, factor=0.55, outer=None):
    """'selective outline': every opaque border pixel (touching transparency) is recoloured as a
    darker version of its own colour (instead of flat black). outer: optional fixed colour."""
    a = spr[..., 3] > 127
    pad = np.pad(a, 1)
    edge = a & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    out = spr.copy()
    if outer is not None:
        out[edge] = outer
    else:
        out[edge, :3] = (spr[edge, :3].astype(np.float32) * factor).astype(np.uint8)
    return out

def alpha_of(spr):
    return (spr[..., 3] > 127)

def layer_new(w, h):
    """an RGBA canvas + float emissive map (0..1, same size) - the unit pixelkit layers work with."""
    return Canvas(w, h), np.zeros((h, w), np.float32)


def missing_glyphs(text, fname='zh12'):
    """characters of `text` the pixel font cannot draw (they would render as tofu boxes).  v0.13 lint:
    run it over every on-screen string (≈ 👍 and most emoji are missing in fusion-pixel)."""
    tofu = text_mask('\U000F0000', fname)
    out = []
    for ch in set(text):
        if ch.isspace(): continue
        m = text_mask(ch, fname)
        if m is None or not m.any() or (tofu is not None and m.shape == tofu.shape and (m == tofu).all()):
            out.append(ch)
    return sorted(out)
