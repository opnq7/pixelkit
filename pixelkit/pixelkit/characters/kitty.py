"""pixelkit.characters.kitty - 小猫主角（001《深度工作》起，「微光」频道固定主角）。

Q 版两头身灰白小猫：灰色虎斑头 + 白口鼻 / 白胸 / 白爪，穿卫衣。世界层精灵（320x180 网格），56x66，锚点 = 两脚之间地面。
表演件：眼睛（大眼双高光 / 瞳孔放大 / 眯眼 …）、耳朵（立 / 塌 / 抖）、尾巴（摆 / 炸毛 / 垂）、爪子（多种姿势）。

    k = draw(face='normal', arms='rest', ears='up', tail=0.0, look=(0, 0), outfit='hoodie', legs=True,
             phase=0, tail_mode='swish', desk_y=None, prop=None, blush=True)
    k.body / k.front : Sprite（front = 画在桌子 / 道具前面的爪子层）; k.ax, k.ay 锚点; k.head_top (x, y)；k.paw_r / k.paw_l 爪子中心

face : normal blink half closed focus happy surprised dilated（红点出现：瞳孔放大）blank tired sad smug wink
arms : rest wave up cheer point hold（双爪捧手机）write（桌面写字，phase 动笔）chin（托腮）scratch（挠头）reach（右爪伸向前方）
       pocket（手插兜）push（向前推）
ears : up perk droop back（飞机耳）twitch（用 phase 抖一下左耳）
tail_mode : swish（慢摆，phase 控制）puff（炸毛）down（垂）still
outfit : hoodie（默认鼠尾草绿卫衣）uniform（学生：白衬衫 + 藏青领结）shirt（打工人：浅蓝灰衬衫 + 领带）robe（法师袍）
prop : None / 'pen' / 'phone' / 'staff'（法杖，蓝宝石杖头）/ 'headphones'
"""
import math
from types import SimpleNamespace
import numpy as np
from ..core import C

SW, SH = 60, 68
HAT_PAD = 14
AX, AY = 30, 65            # ground point between the feet
HX, HY = 30, 22            # head centre (face)

OUT = C('#2a1f30')
FUR = dict(L=C('#d6d2dc'), M=C('#aaa5b4'), D=C('#7d778c'), S=C('#625c72'))          # grey tabby
WHT = dict(L=C('#fffaf6'), M=C('#efe8ea'), D=C('#cfc6cf'))
PINK = C('#f4a2b2'); PINK_D = C('#d97890'); NOSE = C('#e98a9e')
EYE = C('#1d1828'); IRIS = C('#4e7a6a'); SHINE = C('#ffffff')
BLUSH = C('#f6a8b6')
OUTFITS = {
    'hoodie': dict(L=C('#a9c3a8'), M=C('#82a086'), D=C('#5f7a66'), trim=C('#efe6d2'), pants=(C('#454b66'), C('#33384f'))),
    'uniform': dict(L=C('#ffffff'), M=C('#e6e8f0'), D=C('#b9bdcc'), trim=C('#2f3a66'), pants=(C('#3b4466'), C('#2b3150'))),
    'shirt': dict(L=C('#d9e2ea'), M=C('#b4c2cf'), D=C('#8696a8'), trim=C('#6a4c5c'), pants=(C('#3e3f4c'), C('#2c2d38'))),
    'robe': dict(L=C('#6f6aa8'), M=C('#4f4a88'), D=C('#36326a'), trim=C('#d9cfa6'), pants=(C('#36326a'), C('#26234e'))),
}


class Sprite:
    def __init__(self, w=SW, h=SH):
        self.a = np.zeros((h, w, 4), np.uint8); self.E = np.zeros((h, w), np.float32)


_yy, _xx = np.mgrid[0:SH, 0:SW].astype(np.float32)


def _ell(cx, cy, rx, ry, n=2.0):
    return (np.abs((_xx + 0.5 - cx) / rx) ** n + np.abs((_yy + 0.5 - cy) / ry) ** n) <= 1.0


def _tri(p0, p1, p2):
    x, y = _xx + 0.5, _yy + 0.5
    def side(a, b): return (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
    s0, s1, s2 = side(p0, p1), side(p1, p2), side(p2, p0)
    return ((s0 >= 0) & (s1 >= 0) & (s2 >= 0)) | ((s0 <= 0) & (s1 <= 0) & (s2 <= 0))


def _outline(m):
    o = np.zeros_like(m)
    o[1:] |= m[:-1]; o[:-1] |= m[1:]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
    return o & ~m


def _px(a, x, y, c):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < a.shape[1] and 0 <= y < a.shape[0]: a[y, x] = c


def _paint(a, m, c): a[m] = c


def _shade(a, m, cx, cy, rx, ry, ramp, k_hi=0.42, k_lo=-0.25, rim=None):
    """3-tone shading on mask m (light from the upper-left).  rim=(d_hi, d_lo): only light/darken near the edge
    (rounder, softer volume than a straight diagonal split)."""
    nx = (_xx + 0.5 - cx) / rx; ny = (_yy + 0.5 - cy) / ry
    v = -(nx * 0.6 + ny * 0.8)
    a[m] = ramp['M']
    if rim is None:
        a[m & (v > k_hi)] = ramp['L']
        a[m & (v < k_lo)] = ramp['D']
    else:
        d = np.sqrt(nx * nx + ny * ny)
        a[m & (v > 0.15) & (d > rim[0])] = ramp['L']
        a[m & (v < -0.2) & (d > rim[1])] = ramp['D']


def _line(a, x0, y0, x1, y1, c, w=1):
    n = int(max(abs(x1 - x0), abs(y1 - y0), 1) * 2)
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n; y = y0 + (y1 - y0) * i / n
        for ox in range(w):
            for oy in range(w): _px(a, x + ox - (w - 1) / 2, y + oy - (w - 1) / 2, c)


# ---------------------------------------------------------------- tail (behind everything)
def _tail(a, mode, phase):
    if mode == 'down':
        pts = [(39, 56), (44, 60), (49, 61), (53, 59)]
    else:
        sw = math.sin(phase * 0.9) if mode == 'swish' else 0.0
        pts = [(38, 54), (45, 52), (49 + 1.5 * sw, 45), (48 + 3.5 * sw, 38), (45 + 5.5 * sw, 34)]
    w = 6 if mode == 'puff' else 4
    m = np.zeros((SH, SW), bool)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = 12
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n; y = y0 + (y1 - y0) * i / n
            m |= _ell(x, y, w / 2 + 0.3, w / 2 + 0.3)
    a[_outline(m)] = OUT
    a[m] = FUR['M']
    # stripes + white tip
    for i, (x, y) in enumerate(pts[2:-1]):
        a[m & _ell(x, y, w / 2 + 0.5, 0.8)] = FUR['S']
    a[m & (_xx > np.array([p[0] for p in pts]).mean() + 1)] = FUR['D']
    for i, (x, y) in enumerate(pts[2:-1]):
        a[m & _ell(x, y, w / 2 + 0.5, 0.8)] = FUR['S']
    tx, ty = pts[-1]
    a[m & _ell(tx, ty, w / 2 + 0.6, w / 2 + 0.6)] = WHT['M']
    if mode == 'puff':
        for (x, y) in pts[1:]:
            for ang in (0.6, 2.2, 3.8, 5.3): _px(a, x + math.cos(ang + x) * (w / 2 + 1), y + math.sin(ang + y) * (w / 2 + 1), OUT)


# ---------------------------------------------------------------- body
def _body(a, outfit, legs, arms, phase):
    o = OUTFITS[outfit]
    torso = _ell(30, 46, 11.5, 10.5, 2.6) & (_yy >= 35)
    if outfit == 'robe':
        torso = _tri((30, 33), (16, 60), (44, 60)) | (_ell(30, 46, 11.5, 10.5, 2.6) & (_yy >= 35))
    leg_m = np.zeros((SH, SW), bool)
    if legs and outfit != 'robe':
        st = math.sin(phase * math.pi / 2) if arms == 'walk' else 0.0
        for lx, d in ((25, st), (35, -st)):
            leg_m |= _ell(lx + d * 1.5, 57, 3.6, 4.5) & (_yy >= 53)
    feet = np.zeros((SH, SW), bool)
    if legs:
        st = math.sin(phase * math.pi / 2) if arms == 'walk' else 0.0
        for fx, d in ((24.5, st), (35.5, -st)):
            feet |= _ell(fx + d * 2.0, 62.5 - max(0, d) * 1.5, 4.0, 2.6)
    full = torso | leg_m | feet
    a[_outline(full)] = OUT
    if legs and outfit != 'robe':
        a[leg_m] = o['pants'][0]; a[leg_m & (_xx > 31)] = o['pants'][1]
    _shade(a, torso, 30, 44, 12, 12, o)
    # hood rim behind the neck + drawstrings / collar
    if outfit == 'hoodie':
        rim = _ell(30, 36, 10, 3.2) & (_yy >= 34) & torso
        a[rim] = o['D']
        for sx in (27, 33):
            _line(a, sx, 37, sx, 42, o['trim']); _px(a, sx, 43, o['trim'])
        pocket = (_yy >= 49) & (_yy <= 53) & (np.abs(_xx + 0.5 - 30) <= 7 - (_yy - 49) * 0.2) & torso
        a[pocket & ((_yy == 49) | (np.abs(_xx + 0.5 - 30) > 6.2 - (_yy - 49) * 0.2))] = o['D']
    elif outfit == 'uniform':
        _px(a, 29, 36, o['trim']); _px(a, 31, 36, o['trim']); _px(a, 30, 37, o['trim']); _px(a, 28, 37, o['trim']); _px(a, 32, 37, o['trim'])
        a[(_yy >= 36) & (np.abs(_xx + 0.5 - 30.5) < 0.6) & torso] = o['D']
    elif outfit == 'shirt':
        _line(a, 30, 36, 30, 47, o['trim'], 2); _px(a, 30, 48, o['trim']); _px(a, 29, 48, o['trim'])
        _px(a, 27, 35, o['L']); _px(a, 33, 35, o['L'])
    elif outfit == 'robe':
        _line(a, 30, 35, 30, 60, o['trim']); a[torso & (_yy >= 58)] = o['trim']
    if legs:
        a[feet] = WHT['M']; a[feet & (_yy < 62)] = WHT['L']
        for fx in (24.5, 35.5):
            _px(a, fx - 1, 63, WHT['D']); _px(a, fx + 1, 63, WHT['D'])
    # white chest tuft peeking at the neckline
    chest = _ell(30, 35, 4.5, 2.4) & (_yy >= 34)
    a[chest] = WHT['L']


# ---------------------------------------------------------------- head
EARS = {'up': ((14, 2), (40, 2)), 'perk': ((13, 0), (41, 0)), 'droop': ((8, 10), (46, 10)), 'back': ((9, 6), (45, 6))}


def _head(a, E, face, ears, look, blush, phase):
    ex, ey = look
    lt, rt = EARS.get(ears if ears in EARS else 'up')
    if ears == 'twitch' and math.sin(phase * 7) > 0.3: lt = (12, 4)
    earL = _tri(lt, (11.5, 15), (24, 9))
    earR = _tri(rt, (36, 9), (48.5, 15))
    head = _ell(HX, HY + 2, 18.5, 14.5, 2.35)
    cheeks = _ell(HX - 15.5, HY + 7, 4.2, 3.6) | _ell(HX + 15.5, HY + 7, 4.2, 3.6)
    m = head | earL | earR | cheeks
    a[_outline(m)] = OUT
    _shade(a, m, HX - 1, HY + 1, 19, 15.5, FUR, rim=(0.62, 0.66))
    # inner ears
    def inner(apex, b0, b1):
        cx = (apex[0] + b0[0] + b1[0]) / 3; cy = (apex[1] + b0[1] + b1[1]) / 3
        sh = lambda p: (cx + (p[0] - cx) * 0.55, cy + (p[1] - cy) * 0.55 + 1)
        return _tri(sh(apex), sh(b0), sh(b1))
    a[inner(lt, (11.5, 15), (24, 9)) & m] = PINK
    a[inner(rt, (36, 9), (48.5, 15)) & m] = PINK
    # cheek fluff notches
    for sx in (-1, 1):
        _px(a, HX + sx * 19.5, HY + 6, OUT); _px(a, HX + sx * 20.3, HY + 8, FUR['M'] if sx < 0 else FUR['D'])
    # tabby stripes on the forehead
    for dx_, ln in ((-4, 4), (0, 5), (4, 4)):
        _line(a, HX + dx_, HY - 11, HX + dx_ * 0.9, HY - 11 + ln, FUR['S'])
    _line(a, HX - 18, HY + 1, HX - 15, HY + 1, FUR['S']); _line(a, HX + 15, HY + 1, HX + 18, HY + 1, FUR['S'])
    # white muzzle (two puffs) + chin
    muz = (_ell(HX - 3.6, HY + 8.5, 6.2, 4.6) | _ell(HX + 3.6, HY + 8.5, 6.2, 4.6) | _ell(HX, HY + 11.5, 6, 3)) & head
    a[muz] = WHT['L']; a[muz & (_yy >= HY + 12)] = WHT['M']
    a[_ell(HX, HY + 2.5, 1.8, 4) & head & (_yy >= HY - 1)] = WHT['M']                      # blaze between the eyes
    # whiskers
    for sy in (HY + 8, HY + 10):
        _line(a, HX - 21, sy - (sy - HY - 9), HX - 17, sy, WHT['D']); _line(a, HX + 17, sy, HX + 21, sy - (sy - HY - 9), WHT['D'])
    if blush and face not in ('blank', 'sad', 'tired'):
        for bx in (HX - 12, HX + 11):
            _px(a, bx, HY + 7, BLUSH); _px(a, bx + 1, HY + 7, BLUSH)
    # eyes
    exL, exR, eyy = HX - 8 + ex, HX + 7 + ex, HY + 1 + ey
    _eyes(a, E, face, exL, exR, eyy, phase)
    # nose + mouth
    nx, ny = HX, HY + 6
    _px(a, nx - 1, ny, NOSE); _px(a, nx, ny, NOSE); _px(a, nx - 0.5, ny + 1, PINK_D)
    if face in ('happy', 'smug', 'wink'):
        for p in ((nx - 3, ny + 2), (nx - 2, ny + 3), (nx - 1, ny + 2), (nx, ny + 3), (nx + 1, ny + 2)): _px(a, *p, OUT)
        if face == 'happy':
            for p in ((nx - 2, ny + 4), (nx - 1, ny + 4), (nx, ny + 4)): _px(a, *p, PINK_D)
    elif face in ('surprised', 'dilated'):
        for p in ((nx - 1, ny + 3), (nx, ny + 3), (nx - 2, ny + 4), (nx + 1, ny + 4), (nx - 1, ny + 5), (nx, ny + 5)): _px(a, *p, OUT)
        _px(a, nx - 1, ny + 4, PINK_D); _px(a, nx, ny + 4, PINK_D)
    elif face in ('sad', 'tired'):
        for p in ((nx - 2, ny + 4), (nx - 1, ny + 3), (nx, ny + 3), (nx + 1, ny + 4)): _px(a, *p, OUT)
    elif face == 'blank':
        _px(a, nx - 1, ny + 3, OUT); _px(a, nx, ny + 3, OUT)
    else:                                                                                  # small ω
        for p in ((nx - 2, ny + 2), (nx - 1, ny + 3), (nx - 0.5, ny + 2), (nx, ny + 3), (nx + 1, ny + 2)): _px(a, *p, OUT)


def _eyes(a, E, face, xl, xr, y, phase):
    for i, x in enumerate((xl, xr)):
        x = int(round(x)); y = int(round(y))
        f = face
        if f == 'wink' and i == 1: f = 'happy'
        elif f == 'wink': f = 'normal'
        if f in ('normal', 'focus', 'surprised', 'dilated', 'smug', 'sad', 'tired', 'half'):
            h = {'focus': 5, 'smug': 4, 'tired': 4, 'half': 4}.get(f, 7)
            w = 5
            top = y - 4 + (7 - h)
            for yy in range(top, y + 3):
                for xx in range(x - 2, x + 3):
                    corner = (yy in (top, y + 2)) and xx in (x - 2, x + 2)
                    if not corner: _px(a, xx, yy, EYE)
            if f not in ('dilated', 'surprised'):
                for xx in range(x - 1, x + 2): _px(a, xx, y + 1, IRIS)                   # iris glint row
            # highlights
            if f == 'dilated':
                _px(a, x - 1, y - 2, SHINE); _px(a, x - 2, y - 2, SHINE); _px(a, x - 1, y - 1, SHINE); _px(a, x - 2, y - 1, SHINE)
                _px(a, x + 1, y + 1, SHINE); _px(a, x + 2, y, SHINE)
            elif f == 'surprised':
                _px(a, x - 1, y - 2, SHINE); _px(a, x - 1, y - 1, SHINE)
                for xx in range(x - 2, x + 3): _px(a, xx, y - 5, OUT)
            else:
                _px(a, x - 1, top + (1 if h >= 6 else 0), SHINE); _px(a, x, top + (1 if h >= 6 else 0), SHINE)
                if h >= 6: _px(a, x - 1, top + 2, SHINE); _px(a, x, top + 2, SHINE)
                _px(a, x + 1, y + 1, SHINE)
            if f == 'focus':                                                                # determined brows
                d = 1 if i == 0 else -1
                _line(a, x - 2, y - 3 + (0 if d > 0 else 1), x + 2, y - 3 + (1 if d > 0 else 0), OUT)
            if f == 'sad':
                d = 1 if i == 0 else -1
                _line(a, x - 2, y - 4 + (1 if d > 0 else 0), x + 2, y - 4 + (0 if d > 0 else 1), OUT)
            if f == 'tired':
                for xx in range(x - 2, x + 3): _px(a, xx, top - 1, FUR['D'])
        elif f in ('blink', 'closed'):
            for xx in range(x - 2, x + 3): _px(a, xx, y + 1, EYE)
            _px(a, x - 3, y, EYE) if i == 0 else _px(a, x + 3, y, EYE)
        elif f == 'happy':
            for xx, yy in ((x - 2, y + 1), (x - 1, y), (x, y - 1), (x + 1, y), (x + 2, y + 1)): _px(a, xx, yy, EYE)
        elif f == 'blank':
            _px(a, x, y, EYE); _px(a, x, y + 1, EYE)


# ---------------------------------------------------------------- arms / paws
def _paw(a, x, y, r=2.6):
    m = _ell(x, y, r, r * 0.9)
    a[_outline(m)] = OUT; a[m] = WHT['M']; a[m & (_yy + 0.5 < y)] = WHT['L']
    return (x, y)


def _sleeve(a, x0, y0, x1, y1, o, w=4):
    m = np.zeros((SH, SW), bool)
    n = 16
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n; y = y0 + (y1 - y0) * i / n
        m |= _ell(x, y, w / 2, w / 2)
    a[_outline(m) & (a[..., 3] == 0)] = OUT
    a[_outline(m) & ~(np.all(a[..., :3] == np.array(OUT[:3]), -1))] = OUT
    a[m] = o['M']; a[m & (_yy + 0.5 < (y0 + y1) / 2 - 1)] = o['L']


ARMS = {   # (shoulder->paw) for left and right, sprite coords; None = arm hidden
    'rest': ((20, 39, 17, 49), (40, 39, 43, 49)),
    'wave': ((20, 39, 17, 49), (40, 38, 47, 28)),
    'up': ((20, 38, 13, 27), (40, 38, 47, 27)),
    'cheer': ((20, 38, 16, 24), (40, 38, 44, 24)),
    'point': ((20, 39, 17, 49), (40, 39, 51, 37)),
    'hold': ((21, 39, 26, 45), (39, 39, 34, 45)),
    'write': ((21, 39, 23, 46), (39, 39, 36, 46)),
    'chin': ((21, 39, 25, 31), (39, 39, 35, 46)),
    'scratch': ((20, 39, 17, 49), (40, 37, 42, 12)),
    'reach': ((21, 39, 23, 46), (40, 39, 52, 44)),
    'pocket': ((20, 39, 23, 48), (40, 39, 37, 48)),
    'push': ((21, 39, 21, 42), (40, 39, 50, 41)),
    'walk': ((20, 39, 17, 49), (40, 39, 43, 49)),
    'staff': ((20, 39, 17, 49), (40, 38, 44, 42)),
}


def _arms(front, o, arms, phase, desk_y):
    l, r = ARMS.get(arms, ARMS['rest'])
    l, r = list(l), list(r)
    if arms == 'walk':
        s = math.sin(phase * math.pi / 2)
        l[2] += 2 * s; r[2] -= 2 * s
    if arms == 'wave':
        r[2] += 2 * math.sin(phase * 2.2)
    if arms == 'write':
        r[2] += 1.2 * math.sin(phase * 3.1); r[3] += 0.8 * math.cos(phase * 4.7)
    if arms == 'scratch':
        r[2] += 1.0 * math.sin(phase * 9)
    if desk_y is not None and arms in ('write', 'hold', 'reach', 'chin'):
        if arms != 'chin': l[3] = desk_y - 1
        if arms in ('write', 'hold', 'chin'): r[3] = desk_y - 1
    paws = []
    for (x0, y0, x1, y1) in (l, r):
        _sleeve(front.a, x0, y0, x1, y1, o)
        paws.append(_paw(front.a, x1, y1))
    return paws


# ---------------------------------------------------------------- props
def _prop(front, prop, paws, arms, phase):
    a = front.a
    pl, pr = paws
    if prop == 'pen':
        x, y = pr
        _line(a, x + 1, y - 1, x + 4, y - 7, C('#3b3550'), 1); _px(a, x + 4, y - 8, C('#e8e0f0'))
    elif prop == 'phone':
        x = (pl[0] + pr[0]) / 2; y = (pl[1] + pr[1]) / 2 - 3
        m = (np.abs(_xx + 0.5 - x) <= 3.5) & (_yy + 0.5 >= y - 5) & (_yy + 0.5 <= y + 3)
        a[_outline(m)] = OUT; a[m] = C('#2a2a3a')
        scr = (np.abs(_xx + 0.5 - x) <= 2.5) & (_yy + 0.5 >= y - 4) & (_yy + 0.5 <= y + 2)
        a[scr] = C('#e9e6ff'); front.E[scr] = 0.9
        _paw(a, *pl); _paw(a, *pr)
    elif prop == 'staff':
        x, y = pr
        _line(a, x, y + 14, x + 1, y - 18, C('#5a3a2a'), 2); _line(a, x - 0.5, y + 14, x + 0.5, y - 18, C('#8a5e3e'), 1)
        gm = _ell(x + 1, y - 21, 3.2, 3.6)
        a[_outline(gm)] = OUT; a[gm] = C('#2b84d6'); a[gm & (_yy + 0.5 < y - 21)] = C('#5cc8ff')
        _px(a, x, y - 23, C('#ffffff')); front.E[gm] = 0.9
        _paw(a, *pr)
    elif prop == 'headphones':
        pass   # drawn on the head layer by draw()


def _hat(a, E):
    """wizard hat (robe outfit).  a is the TALL canvas (HAT_PAD rows above the normal sprite)."""
    P = HAT_PAD
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float32)
    def tri(p0, p1, p2):
        x, y = xx + 0.5, yy + 0.5
        def side(a_, b_): return (b_[0] - a_[0]) * (y - a_[1]) - (b_[1] - a_[1]) * (x - a_[0])
        s0, s1, s2 = side(p0, p1), side(p1, p2), side(p2, p0)
        return ((s0 >= 0) & (s1 >= 0) & (s2 >= 0)) | ((s0 <= 0) & (s1 <= 0) & (s2 <= 0))
    m = tri((40, P - 13), (15, P + 9), (45, P + 9)) | ((((xx + 0.5 - 30) / 19) ** 2 + ((yy + 0.5 - (P + 9)) / 2.8) ** 2) <= 1)
    o = np.zeros_like(m); o[1:] |= m[:-1]; o[:-1] |= m[1:]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]; o &= ~m
    a[o] = OUT
    a[m] = C('#4f4a88'); a[m & (xx + 0.5 < 33 - (yy - P - 9) * 0.35)] = C('#6f6aa8')
    a[m & (yy >= P + 5) & (yy <= P + 6)] = C('#d9cfa6')
    for sx, sy in ((27, P + 1), (35, P - 4), (31, P - 7)):
        a[int(sy), int(sx)] = C('#d9cfa6')
    return
    hat = None
    m = None
    a[_outline(m) & (_yy >= 0)] = OUT
    a[m] = C('#4f4a88'); a[m & (_xx + 0.5 < 30 - (_yy - 10) * 0.2)] = C('#6f6aa8')
    band = m & (_yy >= 7) & (_yy <= 8)
    a[band] = C('#d9cfa6')
    for sx, sy in ((26, 3), (33, 1)):
        _px(a, sx, sy, C('#d9cfa6'))


def _headphones(a):
    band = _ell(HX, HY - 2, 20, 15, 2.0) & ~_ell(HX, HY - 2, 18, 13, 2.0) & (_yy < HY - 4)
    a[band] = C('#3a3550')
    for sx in (-19, 19):
        m = _ell(HX + sx, HY + 2, 3.2, 4.5)
        a[_outline(m)] = OUT; a[m] = C('#4a4566'); a[m & (_yy + 0.5 < HY + 1)] = C('#6a6488')


def draw(face='normal', arms='rest', ears='up', tail=0.0, look=(0, 0), outfit='hoodie', legs=True, phase=0,
         tail_mode='swish', desk_y=None, prop=None, blush=True, hat=None):
    body = Sprite(); front = Sprite()
    o = OUTFITS[outfit]
    if tail_mode != 'none': _tail(body.a, tail_mode, phase + tail)
    _body(body.a, outfit, legs, arms, phase)
    _head(body.a, body.E, face, ears, look, blush, phase)
    if prop == 'headphones': _headphones(body.a)
    paws = _arms(front, o, arms, phase, desk_y)
    if prop: _prop(front, prop, paws, arms, phase)
    ay = AY; ht = (HX, 2)
    if hat or (hat is None and outfit == 'robe'):                  # taller canvas so the hat tip fits
        for sp in (body, front):
            a2 = np.zeros((SH + HAT_PAD, SW, 4), np.uint8); a2[HAT_PAD:] = sp.a
            e2 = np.zeros((SH + HAT_PAD, SW), np.float32); e2[HAT_PAD:] = sp.E
            sp.a, sp.E = a2, e2
        _hat(body.a, body.E)
        ay = AY + HAT_PAD; ht = (HX, 0); paws = [(p[0], p[1] + HAT_PAD) for p in paws]
    return SimpleNamespace(body=body, front=front, ax=AX, ay=ay, head_top=ht, paw_l=paws[0], paw_r=paws[1])


def flat(k):
    """merge body + front into one RGBA (for previews / simple use)."""
    a = k.body.a.copy(); f = k.front.a; m = f[..., 3] > 0; a[m] = f[m]
    E = k.body.E.copy(); E[m] = k.front.E[m]
    return a, E


def sheet(path, scale=6, bg=(58, 50, 76)):
    import cv2
    rows = [
        [dict(face=f) for f in ('normal', 'blink', 'focus', 'happy', 'surprised', 'dilated', 'blank', 'tired', 'sad', 'smug')],
        [dict(arms=a_, face=f, ears=e, prop=p) for a_, f, e, p in (('wave', 'happy', 'up', None), ('cheer', 'happy', 'perk', None),
         ('point', 'smug', 'up', None), ('hold', 'dilated', 'perk', 'phone'), ('write', 'focus', 'up', 'pen'), ('chin', 'tired', 'droop', None),
         ('scratch', 'blank', 'back', None), ('reach', 'surprised', 'perk', None), ('pocket', 'normal', 'up', None), ('rest', 'sad', 'droop', None))],
        [dict(outfit='uniform', face='normal'), dict(outfit='uniform', face='tired', ears='droop', tail_mode='down'),
         dict(outfit='shirt', face='normal', prop='headphones'), dict(outfit='shirt', face='tired', ears='back'),
         dict(outfit='robe', arms='staff', prop='staff', face='focus'), dict(outfit='robe', arms='up', face='happy'),
         dict(face='surprised', tail_mode='puff', ears='back', arms='up'), dict(arms='walk', phase=1), dict(arms='walk', phase=3),
         dict(face='closed', tail_mode='down')],
    ]
    tiles = []
    for row in rows:
        ts = []
        for kw in row:
            k = draw(**kw); a, _ = flat(k)
            if a.shape[0] < SH + HAT_PAD:
                a = np.concatenate([np.zeros((SH + HAT_PAD - a.shape[0], SW, 4), np.uint8), a], 0)
            img = np.zeros((SH + HAT_PAD, SW, 3), np.uint8) + np.array(bg, np.uint8)
            al = a[..., 3:4] / 255.0
            img = (img * (1 - al) + a[..., :3] * al).astype(np.uint8)
            ts.append(cv2.resize(img, (SW * scale, (SH + HAT_PAD) * scale), interpolation=cv2.INTER_NEAREST))
        tiles.append(np.hstack(ts))
    cv2.imwrite(path, cv2.cvtColor(np.vstack(tiles), cv2.COLOR_RGB2BGR))
