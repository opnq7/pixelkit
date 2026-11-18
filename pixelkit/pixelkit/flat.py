"""pixelkit.flat - 平面像素合成器：GPT 背景板 + 像素精灵 + 像素字，全部落在同一个 320x180 网格上（1080p 下 6 px 一格）。

和 pixstage（HD-2D 光照舞台）的区别：这里没有法线和点光，只有「一张图一张图往上叠」。适合第一人称的手、道具特写、
小票 / 价签这类平面 UI 属于画面世界本身的片子（002《好看，到底值多少钱？》起用）。

    from pixelkit import flat as F
    fr = F.plate('plates/bg.png').copy()            # 320x180 float RGB
    F.blit(fr, F.load('px/bag.png'), 100, 46)       # RGBA 精灵
    F.text(fr, '¥9.00', 160, 20, F.hexc('#1c2a2a'), 'zh12', anchor='c')
    img = F.cam(fr, z=1.06, cx=160, cy=90)          # 最近邻放大到 1080p（亚像素平移，像素边保持锐利）
    img = FIN.apply(img, frame_index, bloom=0.35, vig=0.4, grain=0.014)

规则：世界画布里的坐标一律取整；镜头放大 ≤ 1.15；一个画面只有一个像素网格（字和图同一格）。
"""
import os, functools, hashlib
import numpy as np, cv2
from . import core as _core, post as _post, plates as _plates

W, H, S = 320, 180, 6


def hexc(h, a=None):
    h = h.lstrip('#'); c = tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return c if a is None else c + (a,)


# ---------------------------------------------------------------- 缓动
def clamp(u, a=0.0, b=1.0): return a if u < a else b if u > b else u
def smooth(u): u = clamp(u); return u * u * (3 - 2 * u)
def ramp(t, a, b): return smooth((t - a) / (b - a)) if b > a else float(t >= a)
def lin(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)
def lerp(a, b, k): return a + (b - a) * k
def out_cubic(u): u = clamp(u); return 1 - (1 - u) ** 3
def out_quart(u): u = clamp(u); return 1 - (1 - u) ** 4
def in_cubic(u): u = clamp(u); return u ** 3
def out_back(u, s=1.7): u = clamp(u); return 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2
def out_elastic(u, p=0.35):
    u = clamp(u)
    return 1.0 if u in (0.0, 1.0) and u == 1.0 else (0.0 if u == 0 else 2 ** (-10 * u) * np.sin((u - p / 4) * 2 * np.pi / p) + 1)
def out_bounce(u):
    u = clamp(u)
    if u < 1 / 2.75: return 7.5625 * u * u
    if u < 2 / 2.75: u -= 1.5 / 2.75; return 7.5625 * u * u + 0.75
    if u < 2.5 / 2.75: u -= 2.25 / 2.75; return 7.5625 * u * u + 0.9375
    u -= 2.625 / 2.75; return 7.5625 * u * u + 0.984375
def step12(t, fps=12.0): return np.floor(t * fps) / fps          # 一拍二：动作按 12 fps 走，镜头仍按 30 fps
def hash01(*k):
    return int(hashlib.md5(repr(k).encode()).hexdigest()[:8], 16) / 0xffffffff


# ---------------------------------------------------------------- 素材
@functools.lru_cache(maxsize=256)
def load(path):
    """RGBA 像素精灵 → float32 (h, w, 4) 0..1。返回的是缓存，别原地改。"""
    a = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_UNCHANGED)
    if a is None: raise FileNotFoundError(path)
    if a.ndim == 2: a = cv2.cvtColor(a, cv2.COLOR_GRAY2BGRA)
    elif a.shape[2] == 3: a = cv2.cvtColor(a, cv2.COLOR_BGR2BGRA)
    a = a[..., [2, 1, 0, 3]].astype(np.float32) / 255.0
    a.setflags(write=False)
    return a


@functools.lru_cache(maxsize=64)
def plate(path, w=W, h=H, colors=40, sharpen=0.5, dither=0.3, crop=None):
    """GPT 背景板 → w x h 的真像素图（float RGB）。结果缓存在原图旁边的 _px 目录。crop = (x0, y0, x1, y1) 取原图的一部分（0..1）。"""
    path = str(path)
    key = f'{os.path.basename(path)}_{w}x{h}_{colors}_{sharpen}_{dither}_{crop}'
    cdir = os.path.join(os.path.dirname(path), '_px'); os.makedirs(cdir, exist_ok=True)
    cp = os.path.join(cdir, hashlib.md5(key.encode()).hexdigest()[:10] + '_' + os.path.splitext(os.path.basename(path))[0] + '.png')
    if os.path.exists(cp) and os.path.getmtime(cp) >= os.path.getmtime(path):
        rgb = cv2.imdecode(np.fromfile(cp, np.uint8), cv2.IMREAD_COLOR)[..., ::-1]
    else:
        bgr = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
        if crop:
            hh, ww = bgr.shape[:2]
            bgr = bgr[int(crop[1] * hh):int(crop[3] * hh), int(crop[0] * ww):int(crop[2] * ww)]
        rgb, _ = _plates.pixelize(bgr, w, h, colors=colors, sharpen=sharpen, dither=dither)
        cv2.imencode('.png', rgb[..., ::-1])[1].tofile(cp)
    out = rgb.astype(np.float32) / 255.0
    out.setflags(write=False)
    return out


def canvas(col=(0, 0, 0), w=W, h=H):
    fr = np.empty((h, w, 3), np.float32); fr[:] = col
    return fr


# ---------------------------------------------------------------- 精灵变换（全部最近邻）
def scaled(spr, sx, sy=None):
    """最近邻缩放。sx < 0 = 水平翻转。用来做翻面（sx 从 1 → 0 → -1）、挤压拉伸。"""
    sy = sx if sy is None else sy
    h, w = spr.shape[:2]
    nw, nh = max(1, int(round(w * abs(sx)))), max(1, int(round(h * abs(sy))))
    out = cv2.resize(spr, (nw, nh), interpolation=cv2.INTER_NEAREST)
    if sx < 0: out = out[:, ::-1]
    if sy < 0: out = out[::-1]
    return out


def rot(spr, deg):
    """最近邻旋转（小角度摆动用）。画布按对角线放大，返回 (精灵, 偏移 dx, dy)：贴图时 x - dx, y - dy。"""
    h, w = spr.shape[:2]
    d = int(np.ceil(np.hypot(w, h))); px, py = (d - w) // 2, (d - h) // 2
    big = np.zeros((d, d, spr.shape[2]), np.float32); big[py:py + h, px:px + w] = spr
    M = cv2.getRotationMatrix2D((d / 2 - 0.5, d / 2 - 0.5), deg, 1.0)
    return cv2.warpAffine(big, M, (d, d), flags=cv2.INTER_NEAREST), px, py


def tinted(spr, mul=(1, 1, 1), add=(0, 0, 0), desat=0.0):
    out = spr.copy()
    rgb = out[..., :3]
    if desat:
        g = (rgb @ np.array([0.3, 0.59, 0.11], np.float32))[..., None]
        rgb = rgb * (1 - desat) + g * desat
    out[..., :3] = np.clip(rgb * np.asarray(mul, np.float32) + np.asarray(add, np.float32), 0, 1)
    return out


def silhouette(spr, col):
    out = spr.copy(); out[..., :3] = col
    return out


def outline(spr, col, alpha=1.0):
    """给精灵加 1 px 外描边（返回大 2 px 的新精灵，贴图时 x-1, y-1）。"""
    h, w = spr.shape[:2]
    a = np.zeros((h + 2, w + 2), np.float32); a[1:-1, 1:-1] = (spr[..., 3] > 0.5)
    m = np.zeros_like(a)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        m = np.maximum(m, np.roll(a, (dy, dx), (0, 1)))
    out = np.zeros((h + 2, w + 2, 4), np.float32)
    out[..., :3] = col; out[..., 3] = m * alpha
    out[1:-1, 1:-1] = np.where(spr[..., 3:4] > 0.5, spr, out[1:-1, 1:-1])
    return out


# ---------------------------------------------------------------- 往画布上画
def _clip(dst, x, y, w, h):
    x, y = int(round(x)), int(round(y))
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0: return None
    return x0, y0, x1, y1, x0 - x, y0 - y


def blit(dst, spr, x, y, alpha=1.0, add=False, clip=None):
    """把 RGBA 精灵贴到 RGB 画布。clip = (x0, y0, x1, y1) 只在这个矩形里画（打印机出纸口、瞳孔遮罩之类）。"""
    r = _clip(dst, x, y, spr.shape[1], spr.shape[0])
    if r is None or alpha <= 0: return
    x0, y0, x1, y1, sx, sy = r
    if clip:
        cx0, cy0, cx1, cy1 = [int(v) for v in clip]
        nx0, ny0 = max(x0, cx0), max(y0, cy0); x1, y1 = min(x1, cx1), min(y1, cy1)
        sx += nx0 - x0; sy += ny0 - y0; x0, y0 = nx0, ny0
        if x1 <= x0 or y1 <= y0: return
    s = spr[sy:sy + y1 - y0, sx:sx + x1 - x0]
    a = s[..., 3:4] * alpha if s.shape[2] == 4 else alpha
    reg = dst[y0:y1, x0:x1]
    if add: reg += s[..., :3] * a
    else: reg += (s[..., :3] - reg) * a


def rect(dst, x, y, w, h, col, alpha=1.0, add=False):
    r = _clip(dst, x, y, int(round(w)), int(round(h)))
    if r is None or alpha <= 0: return
    x0, y0, x1, y1, _, _ = r
    reg = dst[y0:y1, x0:x1]
    if add: reg += np.asarray(col[:3], np.float32) * alpha
    else: reg += (np.asarray(col[:3], np.float32) - reg) * alpha


def frame_rect(dst, x, y, w, h, col, alpha=1.0, t=1):
    rect(dst, x, y, w, t, col, alpha); rect(dst, x, y + h - t, w, t, col, alpha)
    rect(dst, x, y + t, t, h - 2 * t, col, alpha); rect(dst, x + w - t, y + t, t, h - 2 * t, col, alpha)


def line(dst, x0, y0, x1, y1, col, alpha=1.0):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n):
        k = i / max(1, n - 1)
        rect(dst, round(x0 + (x1 - x0) * k), round(y0 + (y1 - y0) * k), 1, 1, col, alpha)


def dim(dst, k, col=(0, 0, 0)):
    """整张画布压暗到 col（k = 0 不变，1 全黑）。"""
    dst += (np.asarray(col, np.float32) - dst) * k


def mask_blit(dst, mask, x, y, col, alpha=1.0, add=False):
    r = _clip(dst, x, y, mask.shape[1], mask.shape[0])
    if r is None or alpha <= 0: return
    x0, y0, x1, y1, sx, sy = r
    m = mask[sy:sy + y1 - y0, sx:sx + x1 - x0].astype(np.float32)[..., None] * alpha
    reg = dst[y0:y1, x0:x1]
    if add: reg += np.asarray(col[:3], np.float32) * m
    else: reg += (np.asarray(col[:3], np.float32) - reg) * m


# ---------------------------------------------------------------- 像素字
@functools.lru_cache(maxsize=4096)
def _tmask(s, font, scale):
    m = _core.text_mask(s, font)
    ys = np.where(m.any(1))[0]; xs = np.where(m.any(0))[0]
    if not len(xs): return np.zeros((1, 1), bool), 0
    m = m[:, :xs[-1] + 1]
    if scale != 1: m = np.kron(m, np.ones((scale, scale), bool))
    return m, int(ys[0]) * scale


def text_w(s, font='zh12', scale=1):
    return _tmask(s, font, scale)[0].shape[1] if s else 0


def text(dst, s, x, y, col, font='zh12', alpha=1.0, outline=None, shadow=None, scale=1, anchor='l', add=False):
    """像素字。y = 字格顶边。anchor: l / c / r。outline = 描边色（8 向 1 格），shadow = 右下 1 格的投影色。返回字宽。"""
    if not s or alpha <= 0: return 0
    m, _ = _tmask(s, font, scale)
    w = m.shape[1]
    x = int(round(x - (w / 2 if anchor == 'c' else w if anchor == 'r' else 0))); y = int(round(y))
    if outline is not None:
        o = np.zeros((m.shape[0] + 2 * scale, w + 2 * scale), bool)
        for dy in (0, scale, 2 * scale):
            for dx in (0, scale, 2 * scale):
                o[dy:dy + m.shape[0], dx:dx + w] |= m
        mask_blit(dst, o, x - scale, y - scale, outline, alpha)
    if shadow is not None:
        mask_blit(dst, m, x + scale, y + scale, shadow, alpha)
    mask_blit(dst, m, x, y, col, alpha, add=add)
    return w


def text_sprite(s, col, font='zh12', scale=1, outline=None):
    """把一行字做成 RGBA 精灵（要旋转、挤压、飞出去的字用）。"""
    m, _ = _tmask(s, font, scale)
    pad = scale if outline is not None else 0
    out = np.zeros((m.shape[0] + 2 * pad, m.shape[1] + 2 * pad, 4), np.float32)
    if outline is not None:
        o = np.zeros(out.shape[:2], bool)
        for dy in (0, scale, 2 * scale):
            for dx in (0, scale, 2 * scale):
                o[dy:dy + m.shape[0], dx:dx + m.shape[1]] |= m
        out[o, :3] = outline[:3]; out[o, 3] = 1
    out[pad:pad + m.shape[0], pad:pad + m.shape[1]][m] = tuple(col[:3]) + (1.0,)
    return out


def rich(dst, segs, x, y, font='zh12', alpha=1.0, outline=None, shadow=None, scale=1, anchor='c'):
    """一行里有多种颜色：segs = [(字, 颜色), ...]。"""
    tw = sum(text_w(s, font, scale) + scale for s, _ in segs) - scale
    xx = x - (tw / 2 if anchor == 'c' else tw if anchor == 'r' else 0)
    for s, c in segs:
        text(dst, s, xx, y, c, font, alpha, outline, shadow, scale)
        xx += text_w(s, font, scale) + scale
    return tw


# ---------------------------------------------------------------- 镜头 + 成片处理
def cam(fr, z=1.0, cx=None, cy=None, dx=0.0, dy=0.0, OW=1920, OH=1080, rot_deg=0.0):
    """世界画布 → 输出尺寸，最近邻。z = 放大倍数（≤ 1.15），(cx, cy) = 画面中心对准的世界坐标，dx / dy = 输出像素级的抖动。"""
    h, w = fr.shape[:2]
    cx = w / 2 if cx is None else cx; cy = h / 2 if cy is None else cy
    s = OW / W * z                       # 画布可以比 320 宽（横移用的长条），放大倍数始终按 320 算
    M = cv2.getRotationMatrix2D((cx, cy), rot_deg, s)
    M[0, 2] += OW / 2 - cx + dx; M[1, 2] += OH / 2 - cy + dy
    return cv2.warpAffine(fr, M, (OW, OH), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)


class Finish:
    """1080p 上的最后一步：辉光（只有亮处和金色会发光）、暗角、胶片颗粒。"""
    def __init__(self, OW=1920, OH=1080, seed=5):
        self.fin = _post.Finisher(OW, OH, seed=seed); self.OW, self.OH = OW, OH

    def apply(self, img, frame=0, bloom=0.3, thr=0.78, tint=(0.92, 1.0, 0.96), vig=0.38, grain=0.014, glow=None, glow_k=1.0):
        if bloom > 0 or glow is not None:
            img = _post.bloom(img, thr=thr, knee=0.2, strength=max(bloom, 1e-3), tint=tint, extra=None if glow is None else glow * glow_k)
        if vig > 0: img = self.fin.vignette(img, strength=vig, tint=(0.9, 0.97, 0.95))
        if grain > 0: img = self.fin.add_grain(img, frame, grain)
        return np.clip(img, 0, 1)


def shake(t, t_hit, amp=10.0, dur=0.25, seed=0):
    """t_hit 时刻的一次震屏 → (dx, dy) 输出像素。"""
    u = (t - t_hit) / dur
    if u < 0 or u > 1: return 0.0, 0.0
    k = (1 - u) ** 2 * amp
    f = int(t * 30)
    return k * (hash01(seed, f, 'x') * 2 - 1), k * (hash01(seed, f, 'y') * 2 - 1)


def drift(t, amp=1.2, seed=0):
    """手持感：很慢的小幅漂移（输出像素）。"""
    return (amp * (np.sin(t * 0.61 + seed) + 0.5 * np.sin(t * 1.37 + seed * 2.1)),
            amp * (np.cos(t * 0.53 + seed * 1.7) + 0.5 * np.sin(t * 1.13 + seed)))
