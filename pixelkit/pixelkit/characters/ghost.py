"""pixelkit.characters.ghost - 小魂：戴睡帽的小幽灵（《熬夜副本》主角，v0.13）。

原创角色：薄荷白身体 + 淡紫阴影、半透明微发光；深蓝星星睡帽（金色绒球）；竖椭圆眼；
头顶金色加载圈（= 死了但没完全死 / 正在复活）。世界像素尺寸约 30 x 40（含帽子），夜景里自带辉光。

    from pixelkit.characters import ghost
    g = ghost.draw(face='normal', arms='rest', t=t, look=(0, 0))
    layer.put(g.rgba, x - g.ax, y - g.ay, Z=0, E=g.E)          # (x, y) = 身体中心
    ghost.ring(cv, cx, cy, t)                                   # 加载圈画在 UI 或世界层

faces: normal blink happy wow sad squint sleepy dizzy determined smug closed
arms : rest up wave point stretch hold fist
extra: squash(+压扁 / -拉长)、tilt（度）、cap=False、alpha（0..1，整体半透明）、tail（漂浮下摆相位）
"""
import math
from types import SimpleNamespace
import numpy as np
from ..core import Canvas, C, mix
from ..scene import Sprite

W, H = 40, 48                 # sprite canvas
CX, CY = 20, 28               # body centre inside the canvas
OUT = C('#3a2a4c')            # outline (dark plum)
BODY = [C('#ffffff'), C('#f1fbf8'), C('#dcefee'), C('#c3d4e8'), C('#a7add8'), C('#8a84bd')]   # light -> shadow
EYE = C('#2b1d3a'); EYE_HI = C('#ffffff'); BLUSH = C('#ff9fb4'); MOUTH = C('#5a2f4a')
CAP = [C('#4c63c9'), C('#3a4ca8'), C('#2b3880'), C('#1f2860')]
CAP_BAND = C('#f5ead2'); CAP_BAND_D = C('#cdbf9f'); STAR = C('#ffd85a'); POM = C('#ffd85a'); POM_D = C('#d39a2a')
RING = C('#ffd85a')

def _body_mask(t=0.0, squash=0.0):
    """bool (H, W): rounded top + skirt with 3 swaying scallops."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sx = 1.0 + 0.55 * squash; sy = 1.0 - squash
    rx, ry = 11.5 * sx, 12.5 * sy
    top_cy = CY - 2 * sy
    m = ((xx + 0.5 - CX) / rx) ** 2 + ((yy + 0.5 - top_cy) / ry) ** 2 <= 1.0
    bot = CY + 7 * sy
    m |= (np.abs(xx + 0.5 - CX) <= rx - 0.2) & (yy + 0.5 >= top_cy) & (yy + 0.5 <= bot)
    # slight waist: taper the skirt a touch
    for i in range(3):
        bx = CX - rx + rx * 2 * (i + 0.5) / 3
        off = 1.6 * math.sin(t * 7.0 + i * 2.1)
        m |= ((xx + 0.5 - bx) / (rx / 3 + 0.6)) ** 2 + ((yy + 0.5 - (bot + off)) / 3.2) ** 2 <= 1.0
    return m

def _edge(m):
    p = np.pad(m, 1)
    nb = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m & ~nb

def _shade_body(cv, m, squash):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # light from upper-left: value by (x + y) distance from the lit corner, then bayer-free banding
    u = ((xx - (CX - 7)) * 0.55 + (yy - (CY - 10)) * 0.75) / 22.0
    u = np.clip(u, 0, 1)
    idx = np.clip((u * 4.2).astype(int) + 1, 1, 5)
    # rim of reflected light along the lower-right edge (keeps it from going muddy)
    for k in range(1, 6):
        sel = m & (idx == k)
        cv.a[sel, :3] = BODY[k][:3]; cv.a[sel, 3] = 255
    hl = m & (((xx + 0.5 - (CX - 5)) / 3.2) ** 2 + ((yy + 0.5 - (CY - 9)) / 2.2) ** 2 <= 1.0)
    cv.a[hl, :3] = BODY[0][:3]

def _cap(cv, t, squash, tilt_flop=0.0):
    """navy night-cap flopping to the right with a pompom."""
    sy = 1.0 - squash
    top = int(round(CY - 2 * sy - 12.5 * sy))         # head top
    base_y = top + 2
    # band
    for x in range(CX - 9, CX + 10):
        dy = int(round((x - CX) ** 2 * 0.025))
        cv.a[base_y + dy - 1:base_y + dy + 1, x, :3] = CAP_BAND[:3]; cv.a[base_y + dy - 1:base_y + dy + 1, x, 3] = 255
        cv.a[base_y + dy, x, :3] = CAP_BAND_D[:3]
    # cone: from band up and over to the right
    sway = 1.5 * math.sin(t * 2.3) + tilt_flop
    tip = (CX + 13 + sway, top - 2 + 1.0 * math.sin(t * 2.3 + 0.6))
    pts = [(CX - 9, base_y - 1), (CX - 5, top - 5), (CX + 1, top - 8), (CX + 7, top - 7), (tip[0], tip[1]), (CX + 7, top - 2), (CX + 9, base_y - 1)]
    from ..core import poly_mask
    pm = poly_mask(W, H, pts) > 0 if poly_mask(W, H, pts).dtype != bool else poly_mask(W, H, pts)
    pm &= ~(cv.a[..., 3] > 0) | (np.arange(H)[:, None] < base_y - 1)
    yy, xx = np.mgrid[0:H, 0:W]
    shade = np.clip(((xx - CX) * 0.08 + (yy - top) * 0.10 + 1.2).astype(int), 0, 3)
    for k in range(4):
        sel = pm & (shade == k)
        cv.a[sel, :3] = CAP[k][:3]; cv.a[sel, 3] = 255
    for sx_, sy_ in [(CX - 4, top - 3), (CX + 3, top - 6), (CX + 8, top - 4)]:
        if 0 <= sy_ < H and pm[sy_, sx_]: cv.a[sy_, sx_, :3] = STAR[:3]
    # pompom
    px, py = int(round(tip[0])), int(round(tip[1]))
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if dx * dx + dy * dy <= 5:
                x, y = px + dx, py + dy
                if 0 <= x < W and 0 <= y < H:
                    cv.a[y, x, :3] = (POM_D if dx + dy > 1 else POM)[:3]; cv.a[y, x, 3] = 255
    return pm

EYES = {
    'normal':  [(0, 0, 2, 4)], 'determined': [(0, 1, 2, 3)], 'smug': [(0, 2, 2, 2)],
}

def _eyes(cv, face, look, squash):
    lx, ly = look
    ey = int(round(CY - 4 - 2 * squash)) + ly
    exs = (CX - 5 + lx, CX + 3 + lx)
    def px(x, y, col):
        if 0 <= x < W and 0 <= y < H: cv.a[y, x, :3] = col[:3]; cv.a[y, x, 3] = 255
    for i, ex in enumerate(exs):
        if face in ('blink', 'closed', 'sleepy'):
            for dx in range(3): px(ex + dx - (0 if face != 'sleepy' else 0), ey + 2, EYE)
            if face == 'sleepy': px(ex + (0 if i == 0 else 2), ey + 1, EYE)
        elif face == 'happy':
            px(ex, ey + 2, EYE); px(ex + 1, ey + 1, EYE); px(ex + 2, ey + 2, EYE)
        elif face == 'squint':
            for dx in range(3): px(ex + dx, ey + 2, EYE)
            px(ex + (2 if i == 0 else 0), ey + 1, EYE)
        elif face == 'dizzy':
            px(ex, ey, EYE); px(ex + 2, ey, EYE); px(ex + 1, ey + 1, EYE); px(ex, ey + 2, EYE); px(ex + 2, ey + 2, EYE)
        elif face == 'sad':
            for dy in range(3): px(ex, ey + 1 + dy, EYE); px(ex + 1, ey + 1 + dy, EYE)
            px(ex + (1 if i == 0 else 0), ey + 1, EYE_HI)
            px(ex + (2 if i == 0 else -1), ey, EYE)
        else:
            h = 5 if face == 'wow' else 4
            top = ey - (1 if face == 'wow' else 0)
            for dy in range(h):
                for dx in range(2): px(ex + dx, top + dy, EYE)
            if face == 'wow':
                px(ex - 1, top + 1, EYE); px(ex + 2, top + 1, EYE); px(ex - 1, top + 2, EYE); px(ex + 2, top + 2, EYE)
            px(ex, top, EYE_HI)
            if face == 'determined':
                px(ex + (1 if i == 0 else 0), top - 1, EYE); px(ex + (0 if i == 0 else 1), top - 2, EYE)
    # blush + mouth
    by = ey + 4
    for x in (CX - 8, CX - 7, CX + 6, CX + 7): px(x + lx // 2, by, BLUSH)
    mx = CX - 1 + lx
    if face in ('wow',):
        px(mx, by + 1, MOUTH); px(mx + 1, by + 1, MOUTH); px(mx, by + 2, MOUTH); px(mx + 1, by + 2, MOUTH)
    elif face in ('happy', 'smug'):
        px(mx - 1, by, MOUTH); px(mx, by + 1, MOUTH); px(mx + 1, by + 1, MOUTH); px(mx + 2, by, MOUTH)
    elif face == 'sad':
        px(mx - 1, by + 2, MOUTH); px(mx, by + 1, MOUTH); px(mx + 1, by + 1, MOUTH); px(mx + 2, by + 2, MOUTH)
    elif face == 'dizzy':
        px(mx - 1, by + 1, MOUTH); px(mx, by + 2, MOUTH); px(mx + 1, by + 1, MOUTH); px(mx + 2, by + 2, MOUTH)
    else:
        px(mx, by + 1, MOUTH); px(mx + 1, by + 1, MOUTH)

ARMS = {  # (dx, dy) of each little arm nub tip relative to the body side, per pose: (left, right)
    'rest': ((-1, 3), (1, 3)), 'up': ((-3, -7), (3, -7)), 'wave': ((-1, 3), (3, -7)), 'point': ((-1, 3), (5, -1)),
    'stretch': ((-4, -9), (4, -9)), 'hold': ((2, 4), (-2, 4)), 'fist': ((-1, 3), (2, -4)),
}

def _arms(cv, arms, t, squash):
    L, R = ARMS.get(arms, ARMS['rest'])
    if arms == 'wave': R = (3 + int(round(1.5 * math.sin(t * 16))), -7)
    sx = 1.0 + 0.55 * squash
    ay = int(round(CY + 1))
    for side, (dx, dy) in ((-1, L), (1, R)):
        bx = int(round(CX + side * (11.5 * sx - 0.5)))
        x1, y1 = bx + dx + side * 2, ay + dy
        n = max(abs(x1 - bx), abs(y1 - ay), 1)
        for i in range(n + 1):
            x = int(round(bx + (x1 - bx) * i / n)); y = int(round(ay + (y1 - ay) * i / n))
            for ddx in (0, side):
                for ddy in (0, 1):
                    xx, yy = x + ddx, y + ddy
                    if 0 <= xx < W and 0 <= yy < H:
                        cv.a[yy, xx, :3] = BODY[2 if ddy == 0 else 3][:3]; cv.a[yy, xx, 3] = 255

def draw(face='normal', arms='rest', t=0.0, look=(0, 0), squash=0.0, cap=True, alpha=1.0, glow=0.30, tilt=0.0):
    """returns SimpleNamespace(rgba, E, ax, ay, w, h): ax/ay = body centre inside the sprite."""
    cv = Canvas(W, H)
    m = _body_mask(t, squash)
    _shade_body(cv, m, squash)
    _arms(cv, arms, t, squash)
    if cap: _cap(cv, t, squash)
    _eyes(cv, face, look, squash)
    a = cv.a[..., 3] > 0
    e = _edge(a)
    # dark outline outside the silhouette
    p = np.pad(a, 1)
    ring = (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]) & ~a
    cv.a[ring, :3] = OUT[:3]; cv.a[ring, 3] = 255
    rgba = cv.a.copy()
    E = np.zeros((H, W), np.float32)
    E[m] = glow
    E[ring] = glow * 0.4
    if abs(tilt) >= 0.5:
        from ..perform import rotsprite
        rgba, E = rotsprite(rgba, E, tilt, (CX, CY + 8))
    if alpha < 0.999:
        rgba = rgba.copy(); rgba[..., 3] = (rgba[..., 3] * alpha).astype(np.uint8)
        E = E * alpha
    return SimpleNamespace(rgba=rgba, E=E, ax=CX, ay=CY, w=W, h=H)

def ring(cv, cx, cy, t, r=5.0, n=8, col=RING, alpha=1.0, speed=9.0, size=1):
    """golden loading ring (UI or world Canvas): head dot bright, tail fading."""
    for i in range(n):
        ang = -t * speed - i * 0.62
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang) * 0.75
        a = int(255 * alpha * (1 - i / n) ** 1.2)
        if a < 10: continue
        cv.rect(int(round(x)), int(round(y)), size + (1 if i == 0 else 0), size + (1 if i == 0 else 0), (col[0], col[1], col[2], a))

def sheet(path, scale=6, bg=(40, 36, 64)):
    import cv2
    faces = ['normal', 'blink', 'happy', 'wow', 'sad', 'squint', 'sleepy', 'dizzy', 'determined', 'smug']
    arms = ['rest', 'up', 'wave', 'point', 'stretch', 'hold', 'fist', 'rest', 'rest', 'rest']
    tiles = []
    for i, (f, a) in enumerate(zip(faces, arms)):
        g = draw(face=f, arms=a, t=i * 0.3, squash=(0.18 if i == 7 else (-0.15 if i == 8 else 0.0)))
        img = np.zeros((H, W, 3), np.uint8) + np.array(bg, np.uint8)
        al = g.rgba[..., 3:4] / 255.0
        img = (img * (1 - al) + g.rgba[..., :3] * al).astype(np.uint8)
        tiles.append(cv2.resize(img, (W * scale, H * scale), interpolation=cv2.INTER_NEAREST))
    cv2.imwrite(path, np.concatenate(tiles, 1)[..., ::-1])
