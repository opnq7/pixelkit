"""pixelkit.plates - 外部生成的背景板（GPT / 手绘 / 照片）→ 320x180 大像素舞台（v0.13c）。

AI 出的「像素风」图其实不是真像素网格（同色连续像素中位数 = 1，渐变是平滑的）。直接缩小会糊，
所以按真像素画的规矩重建一遍：
    1. 面积缩小到美术分辨率（默认 320x180）
    2. 反锐化（找回缩小时丢的边）
    3. k-means 提取有限调色板（默认 40 色，按亮度排序）
    4. 4x4 Bayer 有序抖动量化到调色板（渐变变成规整的像素色阶，不是噪点）
    5. 孤立像素清理（一个像素和四邻都不同 → 改成四邻多数色）
    6. 自发光掩码 E：亮 + 暖/饱和的像素（灯、窗、屏幕、发光液体）→ 渲染时走 bloom、可以闪烁

    from pixelkit.plates import Plate
    P = Plate('L2-B.png', colors=40)            # 结果缓存在同目录 .plate_<name>_<W>x<H>_<colors>.npz
    fr = P.frame()                              # -> pixstage.Stage（可继续画角色 / 道具 / 文字）
    L = P.light(fr, k=1.0) + fr.band(...)        # 底图本身已含光：L 以 1.0 为中性，额外的光叠在上面
    img = fr.render(cam, L, GRADE, air=P.air(fr, ...))
    P.lamps                                     # 自动找到的发光块 [(cx, cy, area, rgb)]，可以给它们加光池 / 闪烁
"""
import os
import numpy as np, cv2
from .pixstage import Stage
from .core import BAYER4

def _kmeans_palette(img, k, seed=3):
    Z = img.reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    cv2.setRNGSeed(seed)
    _, lab, cen = cv2.kmeans(Z, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    lum = cen @ np.array([0.11, 0.59, 0.3], np.float32)          # BGR luminance
    order = np.argsort(lum)
    return cen[order]

def pixelize(bgr, W=320, H=180, colors=40, sharpen=0.6, dither=0.35, despeckle=True):
    """any image (BGR uint8) -> (rgb uint8 HxWx3 on a small palette, palette)."""
    small = cv2.resize(bgr, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32)
    if sharpen > 0:
        bl = cv2.GaussianBlur(small, (0, 0), 1.0)
        small = np.clip(small + sharpen * (small - bl), 0, 255)
    pal = _kmeans_palette(small, colors)
    # ordered dither: nudge each pixel by a Bayer offset scaled to the local palette spacing, then nearest colour
    b = np.tile(BAYER4, (H // 4 + 1, W // 4 + 1))[:H, :W] - 0.5
    pert = small + (b[..., None] * dither * 24.0)
    d = ((pert[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(-1)
    idx = d.argmin(-1)
    if despeckle:
        for _ in range(2):
            p = np.pad(idx, 1, mode='edge')
            n4 = np.stack([p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]], -1)
            lone = (n4 != idx[..., None]).all(-1)
            same = (n4[..., 0] == n4[..., 1]) | (n4[..., 0] == n4[..., 2]) | (n4[..., 0] == n4[..., 3])
            fix = lone & same
            idx = np.where(fix, n4[..., 0], idx)
    out = pal[idx].astype(np.uint8)
    return out[..., ::-1].copy(), pal[:, ::-1].astype(np.uint8)      # -> RGB

def emissive_mask(rgb, thr=0.72, sat_min=0.25):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32) / 255.0
    v, s = hsv[..., 2], hsv[..., 1]
    E = np.clip((v - thr) / (1 - thr), 0, 1) * np.clip((s - sat_min * 0.5) / sat_min, 0.35, 1)
    return E.astype(np.float32)

class Plate:
    def __init__(self, path, W=320, H=180, colors=40, sharpen=0.6, dither=0.35, e_thr=0.72, cache=True, crop=None):
        self.path, self.W, self.H = path, W, H
        d, n = os.path.split(path)
        cp = os.path.join(d, f'.plate_{os.path.splitext(n)[0]}_{W}x{H}_{colors}.npz')
        if cache and os.path.exists(cp) and os.path.getmtime(cp) > os.path.getmtime(path):
            z = np.load(cp); rgb, pal = z['rgb'], z['pal']
        else:
            bgr = cv2.imread(path)
            if crop: x, y, w, h = crop; bgr = bgr[y:y + h, x:x + w]
            th = int(round(bgr.shape[1] * H / W))                     # force 16:9
            if abs(th - bgr.shape[0]) > 2:
                y0 = max(0, (bgr.shape[0] - th) // 2); bgr = bgr[y0:y0 + th]
            rgb, pal = pixelize(bgr, W, H, colors, sharpen, dither)
            if cache:                                              # atomic: parallel renders may read it while another process writes
                tmp = cp[:-4] + f'.{os.getpid()}.tmp.npz'
                np.savez_compressed(tmp, rgb=rgb, pal=pal)
                try: os.replace(tmp, cp)
                except OSError: pass
        self.rgb, self.pal = rgb, pal
        self.E = emissive_mask(rgb, e_thr)
        self.st = Stage(W, H)
        self.st.img[..., :3] = rgb; self.st.E[:] = self.E
        self.base = self.st.snapshot()
        self.lamps = self._find_lamps()
        # local light of the set (for relighting actors): blurred colour -> brightness + tint
        c = cv2.GaussianBlur(rgb.astype(np.float32) / 255.0, (0, 0), 9)
        lum = c.mean(-1, keepdims=True)
        tint = np.clip(c / (lum + 1e-3), 0.6, 1.6) ** 0.55
        self.lmap = np.clip((0.45 + 1.35 * lum) * tint, 0.38, 1.5).astype(np.float32)

    def _find_lamps(self, min_area=3):
        m = (self.E > 0.35).astype(np.uint8)
        n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
        out = []
        for i in range(1, n):
            a = stats[i, cv2.CC_STAT_AREA]
            if a >= min_area:
                ys, xs = np.nonzero(lab == i)
                out.append((float(cent[i][0]), float(cent[i][1]), int(a), tuple(int(v) for v in self.rgb[ys, xs].mean(0))))
        return sorted(out, key=lambda r: -r[2])

    def frame(self): return self.st.from_snapshot(self.base)

    def light(self, s, k=1.0, tint=(1.0, 1.0, 1.0), key=None, rim_col=(1.0, 0.8, 0.55), rim_k=0.55, actor_k=1.0):
        """neutral light for the plate (its lighting is painted in) + the plate's LOCAL light on actor pixels
        (Stage.actor) so characters sit in the set: dark corners darken them, lamp pools warm them, plus a rim
        toward key=(x, y)."""
        L = s.light_base(tint, k)
        return s.actor_light(L, self.lmap * np.array(tint, np.float32), key=key, rim_col=rim_col, rim_k=rim_k, k=actor_k)

    def flicker(self, s, t, seed=0, amp=0.15, region=None):
        """lamps breathe: scale E (and the lit pixels' brightness) per lamp blob with a slow pseudo-random flicker."""
        rng = np.random.default_rng(seed)
        out = np.ones((self.H, self.W), np.float32)
        for i, (cx, cy, a, rgb) in enumerate(self.lamps[:12]):
            ph, fr = rng.uniform(0, 6.3), rng.uniform(1.5, 4.0)
            f = 1 + amp * (0.6 * np.sin(t * fr + ph) + 0.4 * np.sin(t * fr * 2.7 + ph * 2))
            r = max(6, np.sqrt(a) * 3)
            out *= 1 + (f - 1) * s.M_ell(cx, cy, r, r)
        return out
