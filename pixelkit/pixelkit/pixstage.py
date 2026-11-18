"""pixelkit.pixstage - 大像素 + 硬边画光舞台（v0.13，《熬夜副本》画风标准）。

参考片对比后的结论（docs/STYLE_GUIDE 6p）：
  - 美术分辨率 320x180（1 美术像素 = 1080p 的 6x6），形状大块干净，少噪点纹理；
  - 一点透视房间（地板 / 地毯 / 家具往灭点收）；
  - 光是「画出来的硬边色阶」：光池 2-3 圈分明的带、光柱是清晰多边形，暗部接近纯黑；
  - 一个暖色主光 + 金色点缀；每个镜头一个主角物件放在中心。

    st = Stage(320, 180)
    st.poly([...], '#1a1218'); st.rect(x, y, w, h, '#c8902e'); st.ell(cx, cy, rx, ry, col); st.outline(mask)
    base = st.snapshot()                          # 缓存静态布景
    fr = st.from_snapshot(base)                   # 每帧：拷贝 → 画动态物件
    L = fr.light_base((0.78, 0.80, 1.0))          # 环境光
    L += fr.band(cx, cy, rx, ry, col, [(1.0, .3), (.6, .6), (.3, 1.0)])   # 硬边光池
    img = fr.render(cam, L, grade, frame=i, ui=ui_rgba)                  # -> 1080p float RGB
"""
import math
import numpy as np, cv2
from .core import C, poly_mask
from .camera import Cam, warp_crisp
from . import post
from .scene import ui_over

def col(c): return C(c) if isinstance(c, str) else (tuple(c) if len(c) == 4 else tuple(c) + (255,))

class Stage:
    def __init__(self, W=320, H=180, OW=1920, OH=1080):
        self.W, self.H, self.OW, self.OH = W, H, OW, OH
        self.img = np.zeros((H, W, 4), np.uint8); self.img[..., 3] = 255
        self.E = np.zeros((H, W), np.float32)
        self.yy, self.xx = np.mgrid[0:H, 0:W]
        self._fin = None

    # ------------------------------------------------------------ masks
    def M_rect(self, x, y, w, h):
        m = np.zeros((self.H, self.W), bool)
        x0, y0, x1, y1 = max(0, int(round(x))), max(0, int(round(y))), min(self.W, int(round(x + w))), min(self.H, int(round(y + h)))
        if x1 > x0 and y1 > y0: m[y0:y1, x0:x1] = True
        return m
    def M_poly(self, pts): return poly_mask(self.W, self.H, pts)
    def M_ell(self, cx, cy, rx, ry): return ((self.xx + .5 - cx) / rx) ** 2 + ((self.yy + .5 - cy) / ry) ** 2 <= 1
    def ring(self, m):
        p = np.pad(m, 1); return (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]) & ~m

    # ------------------------------------------------------------ paint
    def fill(self, m, c, E=None):
        self.img[m] = col(c)
        if E is not None: self.E[m] = E
        return m
    def rect(self, x, y, w, h, c, E=None): return self.fill(self.M_rect(x, y, w, h), c, E)
    def poly(self, pts, c, E=None): return self.fill(self.M_poly(pts), c, E)
    def ell(self, cx, cy, rx, ry, c, E=None): return self.fill(self.M_ell(cx, cy, rx, ry), c, E)
    def px(self, x, y, c, E=None):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.W and 0 <= y < self.H:
            self.img[y, x] = col(c)
            if E is not None: self.E[y, x] = E
    def line(self, x0, y0, x1, y1, c, E=None, mask=None):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            u = i / n; x, y = int(round(x0 + (x1 - x0) * u)), int(round(y0 + (y1 - y0) * u))
            if mask is None or (0 <= x < self.W and 0 <= y < self.H and mask[y, x]): self.px(x, y, c, E)
    def outline(self, m, c='#07060e'): return self.fill(self.ring(m), c)
    def add(self, m, rgb):
        """additive tint inside mask (painted light on the albedo, e.g. a moonbeam)."""
        v = self.img[m, :3].astype(np.int16) + np.array(rgb, np.int16)
        self.img[m, :3] = np.clip(v, 0, 255).astype(np.uint8)
    def mul(self, m, k):
        self.img[m, :3] = np.clip(self.img[m, :3].astype(np.float32) * k, 0, 255).astype(np.uint8)
    def sprite(self, rgba, x, y, E=None, alpha_min=1):
        x, y = int(round(x)), int(round(y)); h, w = rgba.shape[:2]
        x0, y0, x1, y1 = max(0, x), max(0, y), min(self.W, x + w), min(self.H, y + h)
        if x1 <= x0 or y1 <= y0: return
        s = rgba[y0 - y:y1 - y, x0 - x:x1 - x]; m = s[..., 3] >= alpha_min
        a = s[..., 3:4].astype(np.float32) / 255
        reg = self.img[y0:y1, x0:x1]
        mixd = (reg[..., :3] * (1 - a) + s[..., :3] * a).astype(np.uint8)
        reg[..., :3] = np.where(m[..., None], mixd, reg[..., :3])
        if E is not None:
            e = E[y0 - y:y1 - y, x0 - x:x1 - x] if isinstance(E, np.ndarray) else np.full(m.shape, E, np.float32)
            self.E[y0:y1, x0:x1] = np.where(m, np.maximum(e * a[..., 0], 0), self.E[y0:y1, x0:x1])
        else:
            self.E[y0:y1, x0:x1][m] = 0
    def text(self, x, y, s, c, fname='zh8', E=None):
        from .core import text_mask
        m = text_mask(s, fname); h, w = m.shape
        sub = np.zeros((self.H, self.W), bool)
        x0, y0 = int(x), int(y)
        xs0, ys0 = max(0, x0), max(0, y0); xs1, ys1 = min(self.W, x0 + w), min(self.H, y0 + h)
        if xs1 > xs0 and ys1 > ys0: sub[ys0:ys1, xs0:xs1] = m[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
        return self.fill(sub, c, E)

    def part(self, m, ramp, bevel=3.0, light=(-0.45, -0.6, 0.66), amb=0.3, dither=0.4, outline=0.55, ink=None,
             bias=0.0, E=None, normal=(0, 0, 1), profile='round'):
        """shaded volume on the stage (v0.13): the vec.Painter bevel/lambert/ramp/Bayer shading applied to a stage
        mask.  ramp = colours dark -> light (hex or tuples).  Use for hero props (blanket folds, lamp shade, cat ...)."""
        from .vec import Painter
        if not m.any(): return m
        p = getattr(self, '_pp', None)
        if p is None or p.W != self.W:
            p = Painter(self.W, self.H); self._pp = p
        p.rgb[:] = self.img[..., :3].astype(np.float32) / 255.0
        p.E[:] = self.E
        R = [col(c) for c in ramp]
        p.part(m, R, bevel=bevel, light=light, amb=amb, dither=dither, outline=outline, ink=(col(ink) if isinstance(ink, str) else ink),
               bias=bias, E=E, normal=normal, profile=profile)
        self.img[..., :3] = np.clip(p.rgb * 255 + 0.5, 0, 255).astype(np.uint8)
        self.E[:] = p.E
        return m

    def dither(self, m, c, k=0.5, E=None):
        """fill a Bayer-dithered fraction k of mask m with colour c (painted gradients / texture)."""
        from .core import BAYER4
        b = np.tile(BAYER4, (self.H // 4 + 1, self.W // 4 + 1))[:self.H, :self.W]
        return self.fill(m & (b < k), c, E)

    def grad(self, m, c0, c1, y0, y1, steps=4):
        """vertical banded gradient c0 (at y0) -> c1 (at y1) inside m, hard steps with dithered seams."""
        a, b = np.array(col(c0)[:3], np.float32), np.array(col(c1)[:3], np.float32)
        for i in range(steps):
            k = i / max(1, steps - 1)
            c = tuple(int(v) for v in (a + (b - a) * k))
            ya = y0 + (y1 - y0) * i / steps
            band = m & (self.yy >= ya)
            if i == 0: self.fill(m, c)
            else:
                self.dither(band & (self.yy < ya + 2), c, 0.5); self.fill(band & (self.yy >= ya + 2), c)
        return m

    # ------------------------------------------------------------ actors (v0.13e: characters that belong to the set)
    def actor(self, rgba, x, y, E=None, foot=None, shadow=0.45, shadow_w=None):
        """draw a character sprite and remember its pixels (self.act) so the light pass can relight it with the set's
        light (Plate.light / relight_actors) + rim; foot=(fx, fy) adds a soft 2-ring contact shadow under it first."""
        if foot is not None and shadow > 0:
            fx, fy = foot; w = shadow_w or max(5.0, rgba.shape[1] * 0.32)
            self.mul(self.M_ell(fx, fy, w, max(1.5, w * 0.26)), 1 - shadow * 0.6)
            self.mul(self.M_ell(fx, fy, w * 0.66, max(1.2, w * 0.18)), 1 - shadow * 0.5)
        self.sprite(rgba, x, y, E=E)
        if getattr(self, 'act', None) is None: self.act = np.zeros((self.H, self.W), bool)
        x, y = int(round(x)), int(round(y)); h, w = rgba.shape[:2]
        x0, y0, x1, y1 = max(0, x), max(0, y), min(self.W, x + w), min(self.H, y + h)
        if x1 > x0 and y1 > y0: self.act[y0:y1, x0:x1] |= rgba[y0 - y:y1 - y, x0 - x:x1 - x, 3] > 0
        return self

    def actor_light(self, L, lmap, key=None, rim_col=(1.0, 0.8, 0.55), rim_k=0.55, k=1.0):
        """replace L on actor pixels by the set's local light (lmap, HxWx3) and add a 1-px rim on the side facing key."""
        a = getattr(self, 'act', None)
        if a is None or not a.any(): return L
        L = L.copy(); L[a] = lmap[a] * k
        if key is not None:
            cy, cx = np.nonzero(a); mx, my = cx.mean(), cy.mean()
            dx, dy = np.sign(key[0] - mx), np.sign(key[1] - my)
            sh = np.zeros_like(a)
            ys0, ys1 = max(0, int(dy)), self.H + min(0, int(dy)); xs0, xs1 = max(0, int(dx)), self.W + min(0, int(dx))
            sh[ys0 - int(dy):ys1 - int(dy), xs0 - int(dx):xs1 - int(dx)] = a[ys0:ys1, xs0:xs1]
            rim = a & ~sh
            L[rim] = L[rim] + np.array(rim_col, np.float32) * rim_k
        return L

    # ------------------------------------------------------------ snapshots
    def snapshot(self): return (self.img.copy(), self.E.copy())
    def from_snapshot(self, snap):
        s = Stage.__new__(Stage)
        s.W, s.H, s.OW, s.OH = self.W, self.H, self.OW, self.OH
        s.img, s.E = snap[0].copy(), snap[1].copy(); s.yy, s.xx = self.yy, self.xx; s._fin = self._fin; s.act = None
        return s

    # ------------------------------------------------------------ painted light
    def light_base(self, rgb=(0.8, 0.8, 1.0), k=1.0):
        return np.ones((self.H, self.W, 3), np.float32) * (np.array(rgb, np.float32) * k)
    def band(self, cx, cy, rx, ry, rgb, ks, mask=None):
        """hard-edged light pool: ks = [(radius_fraction, strength)...] outer -> inner (strength is ADDED)."""
        d = np.sqrt(((self.xx + .5 - cx) / rx) ** 2 + ((self.yy + .5 - cy) / ry) ** 2)
        out = np.zeros((self.H, self.W), np.float32)
        for r, k in ks: out = np.where(d <= r, np.maximum(out, k), out)
        if mask is not None: out = out * mask
        return out[..., None] * np.array(rgb, np.float32)
    def cone(self, apex, left, right, rgb, k=0.5, soft_rows=0, mask=None):
        """hard spotlight cone polygon (apex, left foot, right foot) + inner core."""
        m = self.M_poly([apex, left, right]).astype(np.float32)
        lx, ly = left; rx_, ry_ = right; ax, ay = apex
        core = self.M_poly([apex, (lx + (rx_ - lx) * 0.25, ly), (lx + (rx_ - lx) * 0.75, ry_)]).astype(np.float32)
        out = m * k + core * k * 0.6
        if mask is not None: out *= mask
        return out[..., None] * np.array(rgb, np.float32)

    # ------------------------------------------------------------ render
    def render(self, cam, L, grade, frame=0, ui=None, fade=1.0, desat=0.0, tint=None, emis_gain=1.15, flash=0.0,
               post_ui=None, pre_grade=None, air=None):
        """air: native (H, W, 3) additive light IN THE AIR (spotlight beams, haze) added after lighting."""
        if self._fin is None: self._fin = post.Finisher(self.OW, self.OH)
        alb = self.img[..., :3].astype(np.float32) / 255
        lit = alb * L
        e = self.E[..., None]
        lit = lit * (1 - e) + alb * e * emis_gain * (1 + 0.6 * e)
        if desat > 0:
            g = lit.mean(-1, keepdims=True); lit = lit + (g - lit) * desat
        if tint is not None: lit = lit * np.array(tint, np.float32)
        if air is not None: lit = lit + air
        img = warp_crisp(np.ascontiguousarray(lit.astype(np.float32)), cam)
        glow = warp_crisp(np.ascontiguousarray((alb * e).astype(np.float32)), cam)
        if pre_grade is not None: img = pre_grade(img)
        out = post.apply_grade(img, grade, self._fin, frame, bloom_extra=glow * 0.5)
        if flash > 0: out = out + (1.0 - out) * flash
        if fade < 1.0: out = out * fade
        if post_ui is not None: out = post_ui(out)
        if ui is not None: out = ui_over(out, ui, scale=max(1, self.OW // ui.shape[1]))
        return out

def cam(zoom=1.0, cx=None, cy=None, sx=0.0, sy=0.0, W=320, H=180):
    return Cam(zoom, cx, cy, sx, sy, W=W, H=H).clamp()

GRADE_NIGHT = dict(post.GRADES['night_hd2d'])
GRADE_NIGHT.update(bloom=dict(thr=0.78, knee=0.2, strength=0.6, tint=(0.9, 0.95, 1.0), halation=0.18), grain=0.012,
                   vignette=0.42, sat=1.1, contrast=1.12)
GRADE_WARM = dict(post.GRADES['golden_hd2d'])
GRADE_WARM.update(grain=0.012, vignette=0.40)

def pixelate(img_out, cell=6):
    """re-grid an output-res float image to big pixels (for inserts drawn at a finer resolution)."""
    H, W = img_out.shape[:2]
    sm = cv2.resize(img_out, (W // cell, H // cell), interpolation=cv2.INTER_AREA)
    return cv2.resize(sm, (W, H), interpolation=cv2.INTER_NEAREST)
