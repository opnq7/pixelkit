"""pixelkit.fx - 整帧后期小特效（v0.13h；作用在 render() 返回的 1080p float 图上）。

    melt(img, w, t)                 房间融化：行按正弦滑动 + 红蓝通道错位（幻觉 / 熬夜第 4 天）
    eyelids(img, droop)             沉重眼皮：droop 0..0.5（0.5 = 全闭），上下两片黑幕；微睡眠 / 疲劳驾驶
    silhouette(fr, look, x, y, s)   把人物缩小染成逆光剪影画到 Stage 上（走向光里的背影）
    cheek? 无。      全部无闪烁：不做整帧亮度翻转。
"""
import numpy as np
from .core import scale_nearest


def melt(img, w, t, amp=26, band=4):
    if w <= 0: return img
    H = img.shape[0]; out = img.copy()
    sh = (np.sin(np.arange(H) / 55.0 + t * 3.0) * amp * w).astype(int)
    for y in range(0, H, band):
        if sh[y]: out[y:y + band] = np.roll(out[y:y + band], sh[y], 1)
    d = int(8 * w)
    if d: out[..., 0] = np.roll(out[..., 0], d, 1); out[..., 2] = np.roll(out[..., 2], -d, 1)
    return out


def eyelids(img, droop):
    if droop <= 0: return img
    H, W = img.shape[:2]; yy = np.arange(H)[:, None]
    lid = droop * H * (1 + 0.08 * np.sin(np.arange(W) / 300.0))[None, :]
    m = (yy < lid) | (yy > H - lid)
    out = img.copy(); out[m] = 0.0
    return out


def silhouette(fr, look, x, y, s, phase=0, warm=(46, 30, 14)):
    from .characters import human
    p = human.draw(look, face='normal', arms='rest', phase=phase)
    a = p.body.cv.a.copy()
    a[..., :3] = np.clip(a[..., :3].astype(np.float32) * 0.16 + np.array(warm), 0, 255).astype(np.uint8)
    a = scale_nearest(a, s); h, w = a.shape[:2]
    fr.sprite(a, x - w / 2, y - h)
