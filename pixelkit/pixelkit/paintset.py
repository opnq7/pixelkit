"""pixelkit.paintset - 手绘布景画板（v0.13）：给 OutdoorScene 用的「画出来的光」布景。

OutdoorScene 不只用于外景：任何正面/侧面构图的布景（夜晚卧室、洞穴、实验室、细胞工厂……）都可以
画成 albedo + E（自发光）+ T（主光可见度：月光 / 窗光 / 光柱）+ ao（环境光遮蔽）四张图，
动态的东西放 mid 层，灯用 st['points']。PaintSet 把这四张图和常用画法打包：

    ps = PaintSet(480, 270)
    ps.tex_rect(0, 0, 480, 200, R('#3d3f6a'), mat.plaster, base=3.0)       # 有纹理的墙
    ps.rect(..., col, E=0.9)                                              # 自发光块（屏幕 / 灯）
    ps.light_poly([(x, y), ...], k=1.0, soft=2)                           # 画在 T 上的光斑（月光落地）
    ps.ao_rect(x, y, w, h, k=0.5, soft=6)                                 # 家具下 / 角落的接触阴影
    ps.put(sprite_rgba, x, y, E=None)                                     # 道具精灵
    bg = ps.bg()                                                          # -> OutdoorScene(bg)

坐标全部是布景原生像素（480 x 270 = 1080p 的 1/4）。
"""
import numpy as np, cv2
from .core import Canvas, C, poly_mask
from .palette import ramp
from . import materials as mat

def R(base, n=6, **kw):
    """hue-shifted ramp dark -> light (RGBA tuples)."""
    return [tuple(c) for c in ramp(base, n, **kw)]

class PaintSet:
    def __init__(self, W=480, H=270):
        self.W, self.H = W, H
        self.cv = Canvas(W, H)
        self.E = np.zeros((H, W), np.float32)
        self.T = np.zeros((H, W), np.float32)
        self.ao = np.ones((H, W), np.float32)
        self.yy, self.xx = np.mgrid[0:H, 0:W]

    # ------------------------------------------------------------ albedo
    def mask_rect(self, x, y, w, h):
        m = np.zeros((self.H, self.W), bool)
        x0, y0, x1, y1 = max(0, int(x)), max(0, int(y)), min(self.W, int(x + w)), min(self.H, int(y + h))
        if x1 > x0 and y1 > y0: m[y0:y1, x0:x1] = True
        return m

    def mask_poly(self, pts):
        return poly_mask(self.W, self.H, pts)

    def mask_ellipse(self, cx, cy, rx, ry):
        return ((self.xx + 0.5 - cx) / rx) ** 2 + ((self.yy + 0.5 - cy) / ry) ** 2 <= 1.0

    def fill(self, m, col, E=None):
        self.cv.a[m] = col if len(col) == 4 else tuple(col) + (255,)
        if E is not None: self.E[m] = E

    def tex(self, m, rp, field=None, base=None, band=2.2, E=None, **kw):
        """fill mask m with ramp rp driven by a materials texture field (u = x, v = y) or a constant base."""
        if field is None:
            t = np.full((self.H, self.W), (len(rp) - 1) / 2 if base is None else base, np.float64)
        else:
            t = field(self.xx.astype(np.float64), self.yy.astype(np.float64), **({'base': base} if base is not None else {}), **kw)
        img = mat.apply_ramp(t, rp, band=band)
        self.cv.a[m] = img[m]
        if E is not None: self.E[m] = E
        return m

    def tex_rect(self, x, y, w, h, rp, field=None, base=None, **kw):
        return self.tex(self.mask_rect(x, y, w, h), rp, field, base, **kw)

    def rect(self, x, y, w, h, col, E=None):
        m = self.mask_rect(x, y, w, h); self.fill(m, col, E); return m

    def vgrad(self, m, rp, y0, y1, t0, t1, band=1.6, E=None):
        """vertical ramp gradient inside mask (dithered between adjacent shades)."""
        t = t0 + (t1 - t0) * np.clip((self.yy - y0) / max(1, y1 - y0), 0, 1)
        img = mat.apply_ramp(t, rp, band=band)
        self.cv.a[m] = img[m]
        if E is not None:
            self.E[m] = E if np.isscalar(E) else E[m]

    def put(self, rgba, x, y, E=None, alpha_min=128):
        x, y = int(round(x)), int(round(y)); h, w = rgba.shape[:2]
        x0, y0, x1, y1 = max(0, x), max(0, y), min(self.W, x + w), min(self.H, y + h)
        if x1 <= x0 or y1 <= y0: return
        s = rgba[y0 - y:y1 - y, x0 - x:x1 - x]; m = s[..., 3] >= alpha_min
        self.cv.a[y0:y1, x0:x1][m] = s[m]; self.cv.a[y0:y1, x0:x1, 3][m] = 255
        if E is not None:
            e = E[y0 - y:y1 - y, x0 - x:x1 - x] if isinstance(E, np.ndarray) else np.full(m.shape, E, np.float32)
            self.E[y0:y1, x0:x1][m] = e[m]
        else:
            self.E[y0:y1, x0:x1][m] = 0

    def px(self, x, y, col, E=None):
        if 0 <= x < self.W and 0 <= y < self.H:
            self.cv.a[int(y), int(x)] = col if len(col) == 4 else tuple(col) + (255,)
            if E is not None: self.E[int(y), int(x)] = E

    def line(self, x0, y0, x1, y1, col, E=None):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            u = i / max(1, n)
            self.px(int(round(x0 + (x1 - x0) * u)), int(round(y0 + (y1 - y0) * u)), col, E)

    def text(self, x, y, s, col, fname='zh8', E=None):
        before = self.cv.a[..., 3].copy(); rgb = self.cv.a[..., :3].copy()
        self.cv.text(x, y, s, col, fname)
        if E is not None:
            ch = (self.cv.a[..., :3] != rgb).any(-1)
            self.E[ch] = E

    def outline(self, m, col):
        """1px outline OUTSIDE mask m."""
        p = np.pad(m, 1)
        ring = (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]) & ~m
        self.fill(ring, col); return ring

    # ------------------------------------------------------------ light maps
    def _soft(self, a, soft):
        return cv2.GaussianBlur(a.astype(np.float32), (0, 0), soft) if soft > 0 else a.astype(np.float32)

    def light_poly(self, pts, k=1.0, soft=1.5):
        self.T = np.maximum(self.T, self._soft(self.mask_poly(pts), soft) * k)

    def light_mask(self, m, k=1.0, soft=1.0):
        self.T = np.maximum(self.T, self._soft(m, soft) * k)

    def ao_rect(self, x, y, w, h, k=0.5, soft=6.0):
        a = self._soft(self.mask_rect(x, y, w, h), soft)
        self.ao *= (1 - k * np.clip(a, 0, 1))

    def ao_mask(self, m, k=0.5, soft=6.0):
        self.ao *= (1 - k * np.clip(self._soft(m, soft), 0, 1))

    def ao_vignette(self, k=0.35, power=2.0):
        """darken the set toward its edges/corners (rooms read deeper)."""
        u = (self.xx / self.W - 0.5) * 2; v = (self.yy / self.H - 0.5) * 2
        self.ao *= (1 - k * np.clip(np.sqrt(u * u * 0.8 + v * v) / 1.3, 0, 1) ** power).astype(np.float32)

    def bg(self, **extra):
        d = dict(rgba=self.cv.a.copy(), E=self.E.copy(), T=self.T.copy(), ao=self.ao.copy())
        d.update(extra); return d


# ---------------------------------------------------------------- tiny prop painters (shared by the sets)
def star_px(ps, x, y, col=(255, 240, 200, 255), E=1.0, big=False):
    ps.px(x, y, col, E)
    if big:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ps.px(x + dx, y + dy, tuple(int(c * 0.6) for c in col[:3]) + (255,), E * 0.6)

def string_lights(ps, pts, n, cols=('#ffcf6a', '#ff8f6a', '#9fe0ff', '#ffe9a8'), wire='#2a2238', E=1.0, sag=6.0):
    """fairy lights hanging between points; returns bulb positions [(x, y, col)] for point lights."""
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        m = max(2, int(abs(x1 - x0)))
        for i in range(m + 1):
            u = i / m
            x = x0 + (x1 - x0) * u; y = y0 + (y1 - y0) * u + sag * 4 * u * (1 - u)
            ps.px(int(round(x)), int(round(y)), C(wire))
    tot = n
    seg = list(zip(pts, pts[1:]))
    for k in range(tot):
        u_all = (k + 0.5) / tot * len(seg); si = min(len(seg) - 1, int(u_all)); u = u_all - si
        (x0, y0), (x1, y1) = seg[si]
        x = x0 + (x1 - x0) * u; y = y0 + (y1 - y0) * u + sag * 4 * u * (1 - u) + 1
        c = C(cols[k % len(cols)])
        ps.px(int(round(x)), int(round(y)), c, E); ps.px(int(round(x)), int(round(y)) + 1, tuple(int(v * 0.7) for v in c[:3]) + (255,), E * 0.7)
        out.append((x, y + 1, c))
    return out
