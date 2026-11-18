"""pixelkit.characters.reddot - 红点怪（001《深度工作》沉淀）：「未读消息红点」变成的小怪，代表一切打断。

一个红色圆团，脸正中是白色数字（就是通知角标上那个数字），两边一对眼睛，下面一张嘴；小短手、小脚。
世界层精灵（320x180 网格），自带微弱自发光（红点在暗处是亮的）。

    s = draw(face='grin', arms='poke', num='1', phase=0, look=(0, 0), squash=0.0, flip=False)
    s.rgba, s.E, s.ax, s.ay          # 锚点 = 两脚之间的地面点
    s.finger                         # arms='poke' 时指尖在精灵里的坐标（给「戳读条」对位）

face：idle（圆眼）/ grin（眯眼坏笑）/ cute（大眼无辜）/ oops（x x 被弹开）/ shock（瞪眼 o 嘴）/ sleep（— —）
arms：rest / poke（右手伸出一根指头）/ up（双手举起）/ wave（右手挥，phase 动）/ hold（双手举在头顶上方，举牌用）/ push
num：'1'..'99'，或 '99+' → 画成 '99'（字太多就只取前两位）
"""
import math
from types import SimpleNamespace
import numpy as np
from ..core import C
from .claude import DIG35

OUT = C('#3a0712'); DARK = C('#9e1428'); MID = C('#e3283c'); HI = C('#ff6670'); TOP = C('#ffc1c6')
WHITE = C('#fff7f2'); EYE = C('#1a0710'); MOUTH = C('#5a0a18'); TOOTH = C('#ffffff'); FOOT = C('#4a0c18')

SW, SH = 27, 24
CX, CY, R = 13, 11, 7.2          # body circle
AX, AY = 13, 22                  # ground anchor


def _put(a, x, y, c):
    x, y = int(x), int(y)
    if 0 <= x < SW and 0 <= y < SH: a[y, x] = c


def draw(face='idle', arms='rest', num='1', phase=0, look=(0, 0), squash=0.0, flip=False, glow=0.28, blink=False):
    a = np.zeros((SH, SW, 4), np.uint8); E = np.zeros((SH, SW), np.float32)
    yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
    # squash: + = flatter/wider (landing), - = taller (jump)
    rx, ry = R * (1 + 0.18 * squash), R * (1 - 0.18 * squash)
    cy = CY + (R - ry)
    dx, dy = (xx + 0.5 - (CX + 0.5)) / rx, (yy + 0.5 - (cy + 0.5)) / ry
    d = np.sqrt(dx * dx + dy * dy)
    body = d <= 1.0
    # feet first (behind body)
    st = math.sin(phase * math.pi / 2) if arms != 'hold' else 0
    for fx, fo in ((CX - 3, st), (CX + 3, -st)):
        fy = int(round(cy + ry + 0.2 - max(0, fo)))
        for ox in (-1, 0, 1):
            _put(a, fx + ox, fy, FOOT); _put(a, fx + ox, fy + 1 if ox == 0 else fy, FOOT)
    # shaded body: light from upper-left
    sh = -(dx * 0.55 + dy * 0.75)
    for m, c in ((body, DARK), (body & (sh > -0.35), MID), (body & (sh > 0.35) & (d < 0.92), HI), (body & (sh > 0.75) & (d < 0.8), TOP)):
        a[m] = c
    ring = body & ~((np.abs(dx) * 1.0) ** 2 + 0 <= -1)
    edge = body & (d > 1.0 - 1.0 / min(rx, ry))
    a[edge] = OUT
    E[body] = glow
    # arms: short round nubs (2x2) on the sides; poke = a short arm + 1 px finger
    lx, rx_ = int(round(CX - rx)) - 1, int(round(CX + rx)) + 1
    ay0 = int(round(cy + 2))
    def nub(x, y, out_dir):
        for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1)): _put(a, x + ox, y + oy, MID if oy == 0 else DARK)
        _put(a, x + (2 if out_dir > 0 else -1), y, OUT); _put(a, x + (2 if out_dir > 0 else -1), y + 1, OUT)
        _put(a, x, y + 2, OUT); _put(a, x + 1, y + 2, OUT); _put(a, x, y - 1, OUT); _put(a, x + 1, y - 1, OUT)
    finger = None
    if arms == 'rest':
        nub(lx - 1, ay0, -1); nub(rx_ - 1, ay0, 1)
    elif arms == 'poke':
        nub(lx - 1, ay0, -1)
        for i in range(3): _put(a, rx_ - 1 + i, ay0 - 1, MID); _put(a, rx_ - 1 + i, ay0, DARK); _put(a, rx_ - 1 + i, ay0 - 2, OUT); _put(a, rx_ - 1 + i, ay0 + 1, OUT)
        _put(a, rx_ + 2, ay0 - 1, TOP); _put(a, rx_ + 3, ay0 - 1, TOP); _put(a, rx_ + 4, ay0 - 1, OUT)
        finger = (rx_ + 3, ay0 - 1)
    elif arms == 'push':
        nub(lx - 2, ay0 - 1, -1); nub(rx_, ay0 - 1, 1)
    elif arms == 'up':
        nub(lx, ay0 - 4, -1); nub(rx_ - 2, ay0 - 4, 1)
    elif arms == 'hold':
        nub(lx + 1, int(cy - ry) - 1, -1); nub(rx_ - 3, int(cy - ry) - 1, 1)
    elif arms == 'wave':
        w = math.sin(phase * 1.9) > 0
        nub(lx - 1, ay0, -1); nub(rx_ - (0 if w else 1), ay0 - (5 if w else 3), 1)
    # face: number in the centre (the notification count), eyes either side, mouth below
    s = str(num).replace('+', '')[:2]
    gl = [DIG35.get(ch, DIG35['1']) for ch in s]
    nw = 4 * len(gl) - 1
    nx = CX - nw // 2 + (1 if len(gl) == 1 else 0) - 1; ny = int(round(cy - 3))
    for i, g in enumerate(gl):
        for r_, row in enumerate(g):
            for c_, ch in enumerate(row):
                if ch == '#': _put(a, nx + i * 4 + c_, ny + r_, WHITE); E[min(SH - 1, ny + r_), min(SW - 1, nx + i * 4 + c_)] = 0.6
    sp = 4 if len(gl) == 1 else 3
    ex0 = nx - sp + int(look[0]); ex1 = nx + nw + sp - 3 + int(look[0]); ey = ny + 1 + int(look[1])
    f = 'sleep' if blink else face
    if f in ('idle', 'cute', 'shock'):
        for ex in (ex0, ex1):
            for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1)): _put(a, ex + ox, ey + oy, EYE)
            if f == 'cute': _put(a, ex, ey - 1, EYE); _put(a, ex + 1, ey - 1, EYE)
            _put(a, ex, ey if f != 'cute' else ey - 1, WHITE)
    elif f == 'grin':
        for ex, s_ in ((ex0, 1), (ex1, -1)):                     # narrowed, slanted eyes  \ /
            _put(a, ex + (0 if s_ > 0 else 1), ey, EYE); _put(a, ex + (1 if s_ > 0 else 0), ey + 1, EYE)
            _put(a, ex + (1 if s_ > 0 else 0), ey, EYE)
    elif f == 'oops':
        for ex in (ex0, ex1):
            _put(a, ex - 1 + 1, ey - 1, EYE); _put(a, ex + 1 + 1, ey - 1, EYE); _put(a, ex + 1, ey, EYE); _put(a, ex, ey + 1, EYE); _put(a, ex + 2, ey + 1, EYE)
    elif f == 'sleep':
        for ex in (ex0, ex1): _put(a, ex, ey + 1, EYE); _put(a, ex + 1, ey + 1, EYE)
    my = ny + 6
    if len(gl) > 1: my = ny + 6
    if f == 'grin':
        for x_ in range(nx - 1, nx + nw + 1): _put(a, x_, my, MOUTH)
        for x_ in range(nx, nx + nw): _put(a, x_, my + 1, MOUTH)
        _put(a, nx, my, TOOTH); _put(a, nx - 2, my - 1, MOUTH); _put(a, nx + nw + 1, my - 1, MOUTH)
    elif f == 'shock':
        _put(a, CX, my, MOUTH); _put(a, CX, my + 1, MOUTH); _put(a, CX - 1, my, MOUTH); _put(a, CX - 1, my + 1, MOUTH)
    elif f == 'cute':
        _put(a, CX - 2, my, MOUTH); _put(a, CX - 1, my + 1, MOUTH); _put(a, CX, my, MOUTH); _put(a, CX + 1, my + 1, MOUTH)
    elif f in ('idle', 'sleep'):
        _put(a, CX - 1, my, MOUTH); _put(a, CX, my, MOUTH)
    elif f == 'oops':
        for x_ in range(CX - 2, CX + 2): _put(a, x_, my + (x_ % 2), MOUTH)
    if flip:
        a = a[:, ::-1].copy(); E = E[:, ::-1].copy()
        if finger: finger = (SW - 1 - finger[0], finger[1])
    return SimpleNamespace(rgba=a, E=E, ax=AX if not flip else SW - 1 - AX, ay=AY, finger=finger)


def sheet(path, scale=8, bg=(40, 34, 60)):
    """review sheet of faces x arms."""
    import cv2
    combos = [('idle', 'rest', '1'), ('grin', 'poke', '1'), ('cute', 'hold', '3'), ('oops', 'up', '1'), ('shock', 'rest', '7'),
              ('grin', 'wave', '99'), ('sleep', 'rest', '2'), ('cute', 'push', '12')]
    tiles = []
    for i, (f, ar, n) in enumerate(combos):
        s = draw(f, ar, n, phase=i)
        img = np.zeros((SH, SW, 3), np.uint8) + np.array(bg, np.uint8)
        al = s.rgba[..., 3:4] / 255.0
        img = (img * (1 - al) + s.rgba[..., :3] * al).astype(np.uint8)
        tiles.append(cv2.resize(img, (SW * scale, SH * scale), interpolation=cv2.INTER_NEAREST))
    out = np.hstack(tiles)
    cv2.imwrite(path, cv2.cvtColor(out, cv2.COLOR_RGB2BGR))


# ------------------------------------------------------------------ v2: GPT-designed sprite (用户 2026-11-09 评旧版「质感不行」)
import os as _os
_ASSETS = _os.path.normpath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..', '素材库', '角色', '红点怪', 'px'))
_SPR = {}


def _load(pose):
    if pose not in _SPR:
        import cv2
        a = cv2.imdecode(np.fromfile(_os.path.join(_ASSETS, pose + '.png'), np.uint8), cv2.IMREAD_UNCHANGED)
        _SPR[pose] = cv2.cvtColor(a, cv2.COLOR_BGRA2RGBA)
    return _SPR[pose]


def sprite(pose='grin', t=0.0, squash=0.0, flip=False, glow=0.22, bob=True):
    """红点怪 v2（GPT 设计稿量化）：pose grin（坏笑）/ poke（戳）/ jump（起跳，双手举起）/ peek（装无辜）。
    squash +压扁（落地）/ -拉长（起跳）；返回 SimpleNamespace(rgba, E, ax, ay)，锚点 = 脚底中点。"""
    import cv2
    a = _load(pose).copy()
    h, w = a.shape[:2]
    if abs(squash) > 0.02:
        nh = max(4, int(round(h * (1 - 0.22 * squash)))); nw = max(4, int(round(w * (1 + 0.18 * squash))))
        a = cv2.resize(a, (nw, nh), interpolation=cv2.INTER_NEAREST)
    elif bob and math.sin(t * 6.0) > 0.6:                     # tiny breathing squash
        a = np.concatenate([np.zeros((1, w, 4), np.uint8), cv2.resize(a, (w, h - 1), interpolation=cv2.INTER_NEAREST)], 0)
    if flip: a = a[:, ::-1].copy()
    E = np.zeros(a.shape[:2], np.float32)
    m = a[..., 3] > 0
    r, g = a[..., 0].astype(int), a[..., 1].astype(int)
    E[m & (r > 150) & (g < 120)] = glow
    E[m & (r > 230) & (g > 200)] = 0.5                         # the white "1"
    return SimpleNamespace(rgba=a, E=E, ax=a.shape[1] // 2, ay=a.shape[0] - 1)
