"""pixelkit.puppet - GPT 拆件图 → 像素木偶（剪纸 / 绑骨动画）。

思路：GPT 负责「长什么样」（拆件图：头、躯干、手臂、腿…分开画在纯品红底上），代码负责「怎么动」。
  1. 读图抠底：key_out(img)            纯品红 #FF00FF（容差 + 去品红溢色）
  2. 分件：     split_parts(rgba)       连通域 → 每个部件一张 RGBA；preview() 出带编号的检查图，人工给编号起名
  3. 像素化：   pixelize_all(parts, s)  所有部件同一个缩放倍数 + 同一套调色板（一个网格、一套颜色）+ 统一 1px 描边
  4. 绑骨：     Puppet({name: Part(...)}) 每个部件一个转轴 pivot、挂在父部件的 joint 点上
  5. 每帧：     puppet.render(angles, offsets) → (rgba, E)；旋转用 perform.rotsprite（小角度剪切 / 大角度 EPX），
                位置按像素取整，所以全身始终在同一个像素网格上，不会出现半像素和糊边。

动作节奏（预备 → 动作 → 过冲 → 回稳、一拍二、呼吸、眨眼）用 anim / perform / acting 里现成的工具驱动角度。
"""
import math
import numpy as np
import cv2
from .perform import rotsprite

KEY = (255, 0, 255)


def load_rgba(path):
    img = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_UNCHANGED)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    elif img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    return img[..., [2, 1, 0, 3]].copy()  # -> RGBA


def save_rgba(path, rgba):
    cv2.imencode('.png', rgba[..., [2, 1, 0, 3]])[1].tofile(str(path))


def key_out(rgba, key=KEY, tol=110, spill=40):
    """抠掉纯色底。tol = 与底色的 RGB 距离阈值；spill = 「偏品红」程度（min(R,B) - G）超过它的边缘像素也去掉。"""
    a = rgba.copy()
    c = a[..., :3].astype(np.int32)
    d = np.sqrt(((c - np.array(key)) ** 2).sum(-1))
    mag = np.minimum(c[..., 0], c[..., 2]) - c[..., 1]
    bg = d < tol
    near = cv2.dilate(bg.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    bg |= near & (mag > spill)
    a[bg, 3] = 0
    return a


def split_parts(rgba, min_area=300, join=4):
    """连通域分件（先把 alpha 膨胀 join 像素，让细天线和顶端星芒算同一件）。按从上到下、从左到右排序。"""
    m = (rgba[..., 3] > 0).astype(np.uint8)
    g = cv2.dilate(m, np.ones((2 * join + 1, 2 * join + 1), np.uint8)) if join else m
    n, lab, st, _ = cv2.connectedComponentsWithStats(g, 8)
    parts = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if area < min_area:
            continue
        crop = rgba[y:y + h, x:x + w].copy()
        crop[(lab[y:y + h, x:x + w] != i) | (m[y:y + h, x:x + w] == 0), 3] = 0
        parts.append(dict(rgba=crop, box=(int(x), int(y), int(w), int(h))))
    parts.sort(key=lambda p: (p['box'][1] // 80, p['box'][0]))
    return parts


def preview(rgba, parts, path):
    """原图上画出每个部件的框和编号，给人工起名用。"""
    img = rgba[..., :3].copy()[..., ::-1]
    img = np.ascontiguousarray(img)
    for i, p in enumerate(parts):
        x, y, w, h = p['box']
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(img, str(i), (x + 4, y + 28), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    cv2.imencode('.png', img)[1].tofile(str(path))


def _down(rgba, s):
    """面积平均降采样（预乘 alpha），alpha 二值化。"""
    h, w = rgba.shape[:2]
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    f = rgba.astype(np.float32) / 255.0
    pre = f[..., :3] * f[..., 3:4]
    pre = cv2.resize(pre, (nw, nh), interpolation=cv2.INTER_AREA)
    al = cv2.resize(f[..., 3], (nw, nh), interpolation=cv2.INTER_AREA)
    col = pre / np.maximum(al[..., None], 1e-4)
    out = np.zeros((nh, nw, 4), np.uint8)
    out[..., :3] = np.clip(col * 255, 0, 255).astype(np.uint8)
    out[..., 3] = np.where(al > 0.5, 255, 0)
    return out


def build_palette(rgbas, n=24, seed=0):
    px = np.concatenate([r[r[..., 3] > 0][:, :3] for r in rgbas]).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    cv2.setRNGSeed(seed)
    _, _, cent = cv2.kmeans(px, min(n, len(px)), None, crit, 3, cv2.KMEANS_PP_CENTERS)
    return np.clip(cent, 0, 255).astype(np.uint8)


def quantize(rgba, pal):
    out = rgba.copy()
    m = out[..., 3] > 0
    c = out[m][:, :3].astype(np.int32)
    d = ((c[:, None, :] - pal[None].astype(np.int32)) ** 2).sum(-1)
    out[m, :3] = pal[d.argmin(1)]
    return out


def add_outline(rgba, col):
    """在部件外面补 1px 描边（只补在透明像素上，4 邻域）。"""
    a = rgba[..., 3] > 0
    p = np.pad(a, 1)
    ring = (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]) & ~a
    out = np.pad(rgba, ((1, 1), (1, 1), (0, 0)))
    r2 = np.pad(ring, 1)
    out[r2, :3] = col
    out[r2, 3] = 255
    return out


def clean_orphans(rgba):
    """去掉只有 1 个像素、四周都透明的孤点（降采样残渣）。"""
    a = rgba[..., 3] > 0
    p = np.pad(a, 1)
    nb = p[:-2, 1:-1].astype(int) + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
    out = rgba.copy()
    out[a & (nb == 0), 3] = 0
    return out


def pixelize_all(rgbas, scale, ncolors=24, outline=(52, 40, 58), palette=None):
    """所有部件同一个缩放倍数、同一套调色板。outline=None 不补描边。返回 (parts, palette)。"""
    small = [clean_orphans(_down(r, scale)) for r in rgbas]
    pal = palette if palette is not None else build_palette(small, ncolors)
    out = [quantize(s, pal) for s in small]
    if outline is not None:
        out = [add_outline(o, outline) for o in out]
    return out, pal


class Part:
    """rgba: 像素化后的部件；pivot: 部件自己的转轴（部件内坐标）；parent: 父部件名；
    joint: 转轴挂在父部件的哪个点（父部件内坐标，未旋转时）；z: 前后顺序（大的在前）。"""

    def __init__(self, rgba, pivot, parent=None, joint=(0, 0), z=0, E=None):
        self.rgba, self.pivot, self.parent, self.joint, self.z = rgba, pivot, parent, joint, z
        self.E = E if E is not None else np.zeros(rgba.shape[:2], np.float32)


def _rot(v, deg):
    a = math.radians(deg)
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


class Puppet:
    def __init__(self, parts, root, size=(160, 160), root_at=(80, 120)):
        self.parts, self.root, self.size, self.root_at = parts, root, size, root_at

    def world(self, angles, offsets):
        """正向运动学：每个部件的世界角度和转轴的世界位置。angles 为相对父部件的角度（度，顺时针为正）。"""
        W = {}

        def solve(name):
            if name in W:
                return W[name]
            p = self.parts[name]
            own = angles.get(name, 0.0)
            off = offsets.get(name, (0, 0))
            if p.parent is None:
                pos = (self.root_at[0] + off[0], self.root_at[1] + off[1])
                W[name] = (own, pos)
            else:
                pa, ppos = solve(p.parent)
                pp = self.parts[p.parent]
                v = _rot((p.joint[0] - pp.pivot[0], p.joint[1] - pp.pivot[1]), pa)
                pos = (ppos[0] + v[0] + off[0], ppos[1] + v[1] + off[1])
                W[name] = (pa + own, pos)
            return W[name]

        for n in self.parts:
            solve(n)
        return W

    def render(self, angles=None, offsets=None, swap=None, method='epx'):
        """→ (rgba, E) 大小 self.size。swap={name: rgba} 本帧临时替换某个部件的图（换表情 / 换手型）。"""
        angles, offsets, swap = angles or {}, offsets or {}, swap or {}
        W = self.world(angles, offsets)
        H_, W_ = self.size[1], self.size[0]
        out = np.zeros((H_, W_, 4), np.uint8)
        oE = np.zeros((H_, W_), np.float32)
        for name in sorted(self.parts, key=lambda n: self.parts[n].z):
            p = self.parts[name]
            img = swap.get(name, p.rgba)
            E = p.E if img is p.rgba else np.zeros(img.shape[:2], np.float32)
            ang, pos = W[name]
            h, w = img.shape[:2]
            pad = int(math.ceil(math.hypot(h, w))) + 2
            A = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.uint8)
            A[pad:pad + h, pad:pad + w] = img
            Ee = np.zeros(A.shape[:2], np.float32)
            Ee[pad:pad + h, pad:pad + w] = E
            pv = (p.pivot[0] + pad, p.pivot[1] + pad)
            angq = round(ang)  # 1 度一档，避免相邻帧细碎抖动
            if angq:
                A, Ee = rotsprite(A, Ee, angq, pv, method=method)  # 实测：大块刚体（CRT 头）用剪切法会被拉碎，EPX 干净
            x0, y0 = int(round(pos[0] - pv[0])), int(round(pos[1] - pv[1]))
            # 贴到输出（裁边）
            sx0, sy0 = max(0, -x0), max(0, -y0)
            dx0, dy0 = max(0, x0), max(0, y0)
            ww = min(A.shape[1] - sx0, W_ - dx0)
            hh = min(A.shape[0] - sy0, H_ - dy0)
            if ww <= 0 or hh <= 0:
                continue
            src = A[sy0:sy0 + hh, sx0:sx0 + ww]
            m = src[..., 3] > 0
            out[dy0:dy0 + hh, dx0:dx0 + ww][m] = src[m]
            oE[dy0:dy0 + hh, dx0:dx0 + ww][m] = Ee[sy0:sy0 + hh, sx0:sx0 + ww][m]
        return out, oE
