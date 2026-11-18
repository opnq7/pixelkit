"""pixelkit.characters.juzi - 小橘：「微光」频道主角（奶油橘白小猫，001《深度工作》起）。

做法（用户定的流程，2026-11-09）：GPT 以设定图 A 为参考出各个姿势 → 统一头宽 48 px、同一套 40 色调色板量化成真像素
（工具包/素材库/角色/小橘/px/*.png）→ 代码在上面加表演层：
  · 眼睛：normal（原图）/ blink / closed / happy（^ ^）/ half / focus / dilated（瞳孔放大，盯红点）/ shock / sad / blank
          look=(dx, dy) 整只眼睛在眼眶里平移 1 px
  · 口鼻：统一重画（降采样后原图的嘴是糊的）：w（ω，默认）/ o / smile / flat / frown
  · 尾巴：tail_k 让尾巴尖轻摆（剪切旋转），breath 1 px 呼吸
  · 一切都是 t 的纯函数，可多进程乱序渲染

    s = draw('desk', face='focus', t=t, look=(1, 0), mouth='w')
    s.rgba, s.E, s.ax, s.ay（锚点：全身 = 两脚之间地面；半身 = 底边中点）, s.head_top, s.eyes（世界坐标要自己加偏移）

姿势：stand（全身正面）desk（桌后写字）phone（捧手机，困）mage（法师 + 法杖）back（坐着背影）
      student（校服桌后写字）office（衬衫 + 耳机桌后打字）back_stand（站立背影）pocket（手插兜站立）
      …更多姿势按需加：在素材库放 png，POSES 里加一行。
"""
import os, math
from types import SimpleNamespace
import numpy as np
import cv2

ASSETS = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '素材库', '角色', '小橘', 'px'))

OUT = (58, 36, 30, 255)
EYE_D = (58, 30, 26, 255); EYE_M = (96, 52, 38, 255); SHINE = (255, 255, 255, 255)
NOSE = (240, 150, 160, 255); NOSE_D = (205, 110, 125, 255); MOUTH = (96, 52, 44, 255); TONGUE = (232, 120, 135, 255)

# eyes = [(x, y, w, h) left, right] in sprite px (auto-detected, checked by eye); half = half-body sprite (anchor = bottom centre)
POSES = {
    'stand':      dict(file='A_cream_ginger.png', eyes=[(9, 24, 10, 7), (31, 24, 11, 8)], half=False, tail=(41, 34, 52, 60)),
    'desk':       dict(file='P1_desk_write.png', eyes=[(9, 26, 10, 8), (32, 26, 10, 8)], half=True, tail=(43, 36, 53, 56)),
    'phone':      dict(file='P2_phone.png', eyes=[(9, 29, 10, 4), (31, 29, 10, 5)], half=True, sleepy=True, tail=(43, 36, 53, 56)),
    'mage':       dict(file='P3_mage.png', eyes=[(16, 38, 10, 7), (39, 38, 10, 7)], half=False, tail=None),
    'back':       dict(file='P4_back.png', eyes=None, half=True, tail=(42, 34, 52, 56)),
    'student':    dict(file='P5_student.png', eyes=None, half=True, tail=None),
    'office':     dict(file='P6_office.png', eyes=None, half=True, tail=None, face_box=(0.2, 0.3, 0.8, 0.7)),
    'back_stand': dict(file='P9_back_stand.png', eyes=None, half=False, tail=None),
    'pocket':     dict(file='P11_pocket.png', eyes=None, half=False, tail=None),
    'desk_nb':    dict(file='P1b_desk_notebook.png', eyes=None, half=True, tail=None, face_box=(0.15, 0.2, 0.85, 0.6)),
    'chin_nb':    dict(file='P12b_chin_notebook.png', eyes=None, half=True, tail=None, face_box=(0.15, 0.2, 0.85, 0.6)),
    'cup':        dict(file='P16_cup.png', eyes=None, half=True, tail=None, face_box=(0.15, 0.15, 0.85, 0.55)),
    'reach':      dict(file='P17a_reach.png', eyes=None, half=True, tail=None, face_box=(0.15, 0.15, 0.75, 0.55)),
    'hold':       dict(file='P17b_hold.png', eyes=None, half=True, tail=None, face_box=(0.15, 0.15, 0.85, 0.55)),
    'scratch':    dict(file='P19_scratch.png', eyes=None, half=True, tail=None, face_box=(0.25, 0.2, 0.8, 0.55)),
    'peek':       dict(file='P20_peek.png', eyes=None, half=True, tail=None, face_box=(0.0, 0.2, 0.75, 0.6)),
    'busy':       dict(file='P6n_busy.png', eyes=None, half=True, tail=None, face_box=(0.15, 0.3, 0.85, 0.7)),
}

_CACHE = {}


def _load(pose):
    if pose in _CACHE: return _CACHE[pose]
    p = POSES[pose]
    path = os.path.join(ASSETS, p['file'])
    a = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_UNCHANGED)
    a = cv2.cvtColor(a, cv2.COLOR_BGRA2RGBA)
    if p.get('eyes') is None and pose not in ('back', 'back_stand'):
        p['eyes'] = detect_eyes(a, p.get('face_box'))
    # face colour = most common light pixel in the upper-middle of the head
    m = a[..., 3] > 0
    H, W = a.shape[:2]
    reg = a[int(H * 0.25):int(H * 0.55), int(W * 0.3):int(W * 0.7)]
    px = reg[reg[..., 3] > 0][:, :3]
    lum = px.astype(int).mean(1)
    light = px[lum >= np.percentile(lum, 70)]
    vals, cnt = np.unique(light, axis=0, return_counts=True)
    face = tuple(int(v) for v in vals[cnt.argmax()]) + (255,)
    _CACHE[pose] = (a, face)
    return _CACHE[pose]


def detect_eyes(a, box=None):
    """two largest compact dark blobs in the upper 70 % (inside the silhouette); box=(x0,y0,x1,y1) fractions limits the search."""
    from scipy import ndimage
    m = a[..., 3] > 0; lum = a[..., :3].astype(int).mean(-1)
    H, W = a.shape[:2]
    inner = ndimage.binary_erosion(m, iterations=2)
    dark = (lum < 95) & inner; dark[int(H * 0.7):] = False
    if box is not None:
        lim = np.zeros_like(dark); lim[int(H * box[1]):int(H * box[3]), int(W * box[0]):int(W * box[2])] = True; dark &= lim
    lab, n = ndimage.label(dark); objs = ndimage.find_objects(lab)
    comps = sorted([(int((lab == i + 1).sum()), o) for i, o in enumerate(objs)], key=lambda c: -c[0])[:2]
    eyes = [(o[1].start, o[0].start, o[1].stop - o[1].start, o[0].stop - o[0].start) for _, o in comps]
    return sorted(eyes)


def _rect(a, x, y, w, h, c):
    x0, y0 = max(0, int(x)), max(0, int(y)); x1, y1 = min(a.shape[1], int(x + w)), min(a.shape[0], int(y + h))
    if x1 > x0 and y1 > y0: a[y0:y1, x0:x1] = c


def _px(a, x, y, c):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < a.shape[1] and 0 <= y < a.shape[0]: a[y, x] = c


def _eye(a, face_col, box, f, look, side, orig):
    x, y, w, h = box
    cx = x + w / 2 - 0.5; cy = y + h / 2 - 0.5
    if f == 'normal' and look == (0, 0): return
    region = orig[y:y + h, x:x + w].copy()
    _rect(a, x - 1, y - 1, w + 2, h + 2, face_col)
    if f in ('normal', 'half', 'focus', 'sad', 'dilated'):
        dx, dy = look
        if f == 'dilated':                                    # bigger dark pupil + big sparkles
            W2, H2 = w + 1, h + 2
            for yy in range(H2):
                for xx in range(W2):
                    nx = (xx + 0.5 - W2 / 2) / (W2 / 2); ny = (yy + 0.5 - H2 / 2) / (H2 / 2)
                    if nx * nx + ny * ny <= 1.05: a[min(a.shape[0] - 1, y - 1 + yy + dy), min(a.shape[1] - 1, x + xx + dx - (1 if side == 0 else 0))] = EYE_D
            for ox, oy in ((1, 1), (2, 1), (1, 2), (2, 2), (3, 1), (1, 3)): _px(a, x + ox + dx, y + oy + dy, SHINE)
            _px(a, x + w - 3 + dx, y + h - 2 + dy, SHINE); _px(a, x + w - 2 + dx, y + h - 3 + dy, SHINE)
            return
        a[y + dy:y + dy + h, x + dx:x + dx + w][region[..., 3] > 0] = region[region[..., 3] > 0]
        if f in ('half', 'focus', 'sad'):
            k = {'half': 0.5, 'focus': 0.16, 'sad': 0.35}[f]
            lid = int(round(h * k))
            for xx in range(w):
                yy = y + lid - 1 + dy
                if f == 'sad': yy += (1 if (xx < w / 2) == (side == 0) else 0) - 0
                _rect(a, x + xx + dx, y - 1 + dy, 1, yy - (y - 1 + dy) + 1, face_col)
                _px(a, x + xx + dx, yy + 1, OUT)
            if f == 'focus':                                   # determined brow above the inner corner
                inner = x + w - 1 if side == 0 else x
                d = -1 if side == 0 else 1
                for i in range(4): _px(a, inner + d * i * 1.0 + dx, y - 3 + (i // 2 if True else 0) + dy, OUT)
            if f == 'sad':
                outer = x if side == 0 else x + w - 1
                d = 1 if side == 0 else -1
                for i in range(4): _px(a, outer + d * i + dx, y - 2 - (i // 2) + dy, OUT)
    elif f in ('blink', 'closed'):
        base = int(y + h // 2)
        prof = [0, 1, 1, 2, 2, 2, 2, 1, 1, 0, 0]
        for xx in range(w):
            a[base + prof[min(xx, len(prof) - 1)] - 1, x + xx] = EYE_D
        _px(a, x - 1, cy + 1, EYE_D) if side == 0 else _px(a, x + w, cy + 1, EYE_D)
    elif f == 'happy':
        base = int(y + h // 2 + 1)
        prof = [2, 1, 0, 0, 0, 0, 0, 0, 1, 2] if w >= 10 else [2, 1, 0, 0, 0, 0, 1, 2][:w]
        for xx in range(w):
            yy = base - 2 + prof[min(xx, len(prof) - 1)] if xx < len(prof) else base
            a[yy, x + xx] = EYE_D; a[yy + 1, x + xx] = EYE_D
    elif f == 'shock':
        ex, ey = int(x + w // 2), int(y + h // 2)
        for yy in range(-4, 4):
            for xx in range(-4, 4):
                d = ((xx + 0.5) / 4.0) ** 2 + ((yy + 0.5) / 4.0) ** 2
                if d <= 1: a[ey + yy, ex + xx] = SHINE if d < 0.6 else OUT
        _rect(a, ex - 1 + look[0], ey - 1 + look[1], 2, 2, EYE_D)
    elif f == 'blank':
        _rect(a, cx - 0.5, cy - 1, 2, 3, EYE_D)


def _mouth(a, face_col, eyes, kind, sleepy=False):
    (lx, ly, lw, lh), (rx, ry, rw, rh) = eyes
    mx = (lx + lw + rx) / 2 - 0.5                               # between the eyes
    ny = max(ly + lh, ry + rh) - (2 if not sleepy else 0) - 1
    _rect(a, mx - 4, ny - 1, 10, 7, face_col)
    _px(a, mx, ny, NOSE); _px(a, mx + 1, ny, NOSE); _px(a, mx + 0.5, ny + 1, NOSE_D)
    y = ny + 2
    if kind == 'w':
        for x_, y_ in ((-2, 0), (-1, 1), (0, 0.5), (1, 0.5), (2, 1), (3, 0)): _px(a, mx + x_, y + y_, MOUTH)
    elif kind == 'smile':
        for x_, y_ in ((-2, 0), (-1, 1), (0, 1), (1, 1), (2, 1), (3, 0)): _px(a, mx + x_, y + y_, MOUTH)
        _px(a, mx, y + 2, TONGUE); _px(a, mx + 1, y + 2, TONGUE)
    elif kind == 'o':
        for x_, y_ in ((0, 0), (1, 0), (-1, 1), (2, 1), (-1, 2), (2, 2), (0, 3), (1, 3)): _px(a, mx + x_, y + y_, MOUTH)
        for x_, y_ in ((0, 1), (1, 1), (0, 2), (1, 2)): _px(a, mx + x_, y + y_, TONGUE)
    elif kind == 'flat':
        for x_ in range(-1, 3): _px(a, mx + x_, y + 1, MOUTH)
    elif kind == 'frown':
        for x_, y_ in ((-1, 1), (0, 0), (1, 0), (2, 1)): _px(a, mx + x_, y + y_, MOUTH)


def _tail(a, box, k):
    """sway the tail: rows of the tail box shifted horizontally, more toward the tip (top)."""
    if box is None or abs(k) < 0.05: return a
    x0, y0, x1, y1 = box
    x1, y1 = min(x1, a.shape[1]), min(y1, a.shape[0])
    out = a.copy()
    sub = a[y0:y1, x0:x1].copy()
    out[y0:y1, x0:x1] = 0
    out[y0:y1, x0:x1][..., 3] = 0
    for r in range(y1 - y0):
        u = 1 - r / max(1, (y1 - y0 - 1))                           # 1 at the top (tip), 0 at the base
        sh = int(round(k * 2.4 * u * u))
        row = sub[r]
        for c in range(x1 - x0):
            if row[c, 3] == 0: continue
            nx = x0 + c + sh
            if 0 <= nx < a.shape[1]: out[y0 + r, nx] = row[c]
    # restore body pixels the tail box may have erased (left part overlapping the body)
    keep = (a[y0:y1, x0:x1, 3] > 0) & (out[y0:y1, x0:x1, 3] == 0)
    o2 = out[y0:y1, x0:x1]; o2[keep] = a[y0:y1, x0:x1][keep]
    return out


def draw(pose='stand', face='normal', t=0.0, look=(0, 0), mouth=None, tail_k=None, breath=True, blink=True, flip=False):
    a0, face_col = _load(pose)
    p = POSES[pose]
    a = a0.copy()
    f = face
    # automatic blinking (normal / focus faces): ~every 3.1 s, 0.13 s
    if blink and f in ('normal', 'focus', 'dilated'):
        ph = (t * 0.32 + 0.37 * (hash(pose) % 7)) % 1.0
        if ph < 0.042: f = 'closed' if ph > 0.014 and ph < 0.028 else 'half'
    if p.get('eyes') and f != 'normal' or (p.get('eyes') and look != (0, 0)):
        if p.get('sleepy') and f == 'normal': pass
        else:
            for side, box in enumerate(p['eyes']):
                _eye(a, face_col, box, f, look, side, a0)
    if p.get('eyes'):
        mk = mouth or ('o' if f in ('shock',) else ('smile' if f == 'happy' else 'w'))
        _mouth(a, face_col, p['eyes'], mk, p.get('sleepy', False))
    if tail_k is None: tail_k = math.sin(t * 1.7)
    a = _tail(a, p.get('tail'), tail_k)
    if breath:                                                     # 1 px rise of everything above the waist line
        b = (math.sin(t * 2.0) > 0.35)
        if b:
            H = a.shape[0]; cut = int(H * (0.62 if not p['half'] else 0.8))
            a2 = a.copy(); a2[:cut - 1] = a[1:cut]; a2[cut - 1] = a[cut - 1]; a = a2
    E = np.zeros(a.shape[:2], np.float32)
    if pose == 'mage':                                             # the staff crystal glows
        hsv = cv2.cvtColor(np.ascontiguousarray(a[..., :3]), cv2.COLOR_RGB2HSV)
        E[(hsv[..., 0] > 85) & (hsv[..., 0] < 110) & (hsv[..., 1] > 60) & (a[..., 3] > 0)] = 0.85
    if flip: a = a[:, ::-1].copy(); E = E[:, ::-1].copy()
    H, W = a.shape[:2]
    if p['half']: ax, ay = W // 2, H - 1
    else:
        m = a[..., 3] > 0; ys = np.nonzero(m.any(1))[0]; ay = int(ys.max())
        ax = W // 2
    ys = np.nonzero((a[..., 3] > 0).any(1))[0]
    return SimpleNamespace(rgba=a, E=E, ax=ax, ay=ay, head_top=(W // 2, int(ys.min())), W=W, H=H,
                           eyes=p.get('eyes'), half=p['half'])


def sheet(path, scale=6, bg=(44, 38, 62)):
    rows = [[('desk', f) for f in ('normal', 'blink', 'happy', 'half', 'focus', 'dilated', 'shock', 'sad', 'blank')],
            [('stand', 'normal'), ('phone', 'normal'), ('phone', 'dilated'), ('mage', 'focus'), ('mage', 'blank'), ('back', 'normal')]]
    tiles = []
    for row in rows:
        ts = []
        for pose, f in row:
            s = draw(pose, f, t=0.9, breath=False, blink=False)
            Hm = 92
            img = np.zeros((Hm, s.W + 6, 3), np.uint8) + np.array(bg, np.uint8)
            al = s.rgba[..., 3:4] / 255.0
            y0 = Hm - s.H
            img[y0:, 3:3 + s.W] = (img[y0:, 3:3 + s.W] * (1 - al) + s.rgba[..., :3] * al).astype(np.uint8)
            ts.append(img)
        r = np.hstack(ts)
        tiles.append(r)
    Wm = max(r.shape[1] for r in tiles)
    tiles = [np.pad(r, ((0, 0), (0, Wm - r.shape[1]), (0, 0)), constant_values=40) for r in tiles]
    out = np.vstack(tiles)
    cv2.imwrite(path, cv2.cvtColor(cv2.resize(out, (out.shape[1] * scale, out.shape[0] * scale), interpolation=cv2.INTER_NEAREST), cv2.COLOR_RGB2BGR))
