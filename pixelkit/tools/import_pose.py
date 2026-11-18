"""GPT 角色姿势 → 真像素精灵（和已有姿势同一尺度、同一调色板）。

尺度靠「两眼间距」对齐：小橘所有姿势两眼中心间距 ≈ 22.5 px（头宽 48 px）。GPT 每张图画得大小不一，按眼距缩放最稳。
    python tools/import_pose.py <src.png> <dst.png> [--pal palette.npy] [--eye 22.5] [--eyes-box x0,y0,x1,y1] [--scale S]
--scale 直接给缩放比（没有眼睛的图，例如背影、道具）。打印检测到的眼距和输出尺寸，方便核对。
"""
import argparse, sys, os
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pixelkit import puppet as PU


def crop(a, pad=4):
    ys, xs = np.nonzero(a[..., 3] > 0)
    return a[max(0, ys.min() - pad):ys.max() + pad + 1, max(0, xs.min() - pad):xs.max() + pad + 1]


def eye_distance(a, box=None):
    """two largest compact dark blobs in the upper 60 % of the figure -> centre distance (source px)."""
    m = a[..., 3] > 0; lum = a[..., :3].astype(int).mean(-1)
    H, W = a.shape[:2]
    inner = ndimage.binary_erosion(m, iterations=4)
    dark = (lum < 80) & inner
    lim = np.zeros_like(dark)
    if box: lim[int(H * box[1]):int(H * box[3]), int(W * box[0]):int(W * box[2])] = True
    else: lim[:int(H * 0.6)] = True
    dark &= lim
    lab, n = ndimage.label(dark)
    comps = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(ys) < 200: continue
        h, w = np.ptp(ys) + 1, np.ptp(xs) + 1
        if not (0.5 < h / w < 2.2): continue
        comps.append((len(ys), xs.mean(), ys.mean()))
    comps.sort(key=lambda c: -c[0])
    if len(comps) < 2: return None
    (_, x1, y1), (_, x2, y2) = comps[:2]
    return float(np.hypot(x2 - x1, y2 - y1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--pal', default=None); ap.add_argument('--eye', type=float, default=22.5)
    ap.add_argument('--eyes-box', default=None); ap.add_argument('--scale', type=float, default=None)
    ap.add_argument('--colors', type=int, default=24); ap.add_argument('--outline', default='58,36,30')
    a = ap.parse_args()
    src = crop(PU.key_out(PU.load_rgba(a.src)))
    if a.scale: s = a.scale
    else:
        box = [float(v) for v in a.eyes_box.split(',')] if a.eyes_box else None
        d = eye_distance(src, box)
        if d is None: sys.exit('no eyes found; pass --scale or --eyes-box')
        s = a.eye / d
        print(f'eye distance {d:.0f}px -> scale {s:.4f}')
    small = PU.clean_orphans(PU._down(src, s))
    pal = np.load(a.pal) if a.pal else PU.build_palette([small], a.colors)
    out = PU.add_outline(PU.quantize(small, pal), tuple(int(v) for v in a.outline.split(',')))
    PU.save_rgba(a.dst, out)
    print(os.path.basename(a.dst), out.shape[:2])


if __name__ == '__main__':
    main()
