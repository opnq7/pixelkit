"""pixelkit.castbar - 「读条」一套组件（001《深度工作》沉淀）。全部画在 480x270 UI 画布上，纯 t 函数。

    cast_bar(cv, x, y, w, k, t, ...)        读条：深色槽 + 分层填充（高光行 / 主色 / 暗行）+ 斜向流光 + 前沿亮线
                                           + 向前沿汇聚的光点；label 名牌（「读条」「专注」）、pct 百分比、
                                           flash 满条白闪、stall 卡住时前沿原地颤
    cast_shatter(cv, x, y, w, k, age, ...)  被打断：填充部分碎成像素块（重力 + 旋飞）、槽体红闪、裂缝
    mp_bar(cv, x, y, n, lit, t, ...)        分格蓝条（MP）：亮格呼吸，新点亮的格子白闪 + 上浮 +1
    film_rail(cv, t, segs, ...)             顶部「全片读条」：分段细条，按段名提示当前章节，满格时金闪
    orb_sprite(r, t, dim)                   注意力光核（世界层精灵 RGBA + 自发光 E）：分层球体、旋转内纹、外圈抖动光晕
    ramps：BLUE（专注）/ GOLD（大招）/ RED（打断）/ GREY（普攻）—— 颜色有固定含义，见 001 策划。
"""
import math
import numpy as np
from .core import C, text_width
from .ui import _a

def _ramp(dark, mid, hi, top, edge='#ffffff'):
    return dict(dark=C(dark), mid=C(mid), hi=C(hi), top=C(top), edge=C(edge))

BLUE = _ramp('#123d73', '#2b84d6', '#5cc8ff', '#c4f0ff')
GOLD = _ramp('#7a4708', '#d98c16', '#ffd36a', '#fff3c4')
RED = _ramp('#5c0c1a', '#c42438', '#ff4a5a', '#ffc0c5')
GREY = _ramp('#3a3a48', '#6c6c7c', '#9a9aaa', '#d0d0da', '#e8e8ee')
FRAME = C('#0a0916'); TRACK = C('#191c36'); TRACK2 = C('#23284a'); RIM = C('#56628f')


def _frame(cv, x, y, w, h, alpha, track=True):
    cv.rect(x - 1, y - 2, w + 2, 1, _a(FRAME, alpha)); cv.rect(x - 1, y + h + 1, w + 2, 1, _a(FRAME, alpha))
    cv.rect(x - 2, y - 1, 1, h + 2, _a(FRAME, alpha)); cv.rect(x + w + 1, y - 1, 1, h + 2, _a(FRAME, alpha))
    cv.rect(x - 1, y - 1, w + 2, 1, _a(RIM, alpha * 0.9))                       # light top rim
    cv.rect(x - 1, y, 1, h + 1, _a(RIM, alpha * 0.6)); cv.rect(x + w, y, 1, h + 1, _a(FRAME, alpha))
    cv.rect(x - 1, y + h, w + 2, 1, _a(FRAME, alpha))
    if track:
        cv.rect(x, y, w, h, _a(TRACK, alpha)); cv.rect(x, y, w, 1, _a(TRACK2, alpha))
        for i in range(4, w, 8): cv.rect(x + i, y + h - 1, 1, 1, _a(TRACK2, alpha))   # tick marks


def _fill_rows(cv, x, y, wf, h, ramp, alpha, mix_white=0.0):
    rows = [ramp['top'], ramp['hi']] + [ramp['mid']] * max(0, h - 3) + [ramp['dark']]
    for r in range(h):
        c = rows[min(r, len(rows) - 1)]
        if mix_white > 0: c = tuple(int(c[i] + (255 - c[i]) * mix_white) for i in range(3)) + (255,)
        cv.rect(x, y + r, wf, 1, _a(c, alpha))


def cast_bar(cv, x, y, w, k, t=0.0, h=5, ramp=BLUE, label=None, label_k=1.0, pct=False, alpha=1.0, flash=0.0,
             stall=0.0, shimmer=True, sparks=True, label_font='zh10', label_side='left'):
    """读条。k 0..1 填充；flash 0..1 满条白闪；stall 0..1 卡住（前沿 ±1 px 颤动、光点停止汇聚）。"""
    if alpha <= 0: return
    x, y = int(round(x)), int(round(y)); w = int(w)
    _frame(cv, x, y, w, h, alpha)
    k = max(0.0, min(1.0, k))
    wf = int(round(w * k))
    if stall > 0 and 0 < wf < w: wf = max(1, wf + int(round(math.sin(t * 47) * stall)))
    if wf > 0:
        _fill_rows(cv, x, y, wf, h, ramp, alpha, mix_white=flash)
        if shimmer and flash < 0.9:
            span = wf + 24; pos = (t * 46.0) % span - 12                      # diagonal sheen sweeping right
            for r in range(h):
                for d in range(3):
                    px = int(pos + d - r)
                    if 0 <= px < wf: cv.px(x + px, y + r, _a(ramp['top'], alpha * (0.55 if d != 1 else 0.85)))
        cv.rect(x + wf - 1, y, 1, h, _a(ramp['edge'], alpha))                     # bright leading edge
        if wf > 1: cv.rect(x + wf - 2, y + 1, 1, h - 2, _a(ramp['top'], alpha))
        if sparks and k < 0.999:
            ex, ey = x + wf, y + h / 2
            for i in range(7):
                ph = ((t * (1.3 if stall < 0.5 else 0.15)) + i / 7.0) % 1.0
                ang = i * 2.39996 + 0.7
                rad = (1 - ph) * (9 + 4 * ((i * 37) % 5) / 5)
                px, py = ex + math.cos(ang) * rad * 1.4, ey + math.sin(ang) * rad
                cv.px(int(px), int(py), _a(ramp['top'] if i % 2 else ramp['hi'], alpha * (0.3 + 0.7 * ph)))
    if flash > 0:                                                                 # outer glow ring
        g = _a(ramp['top'], alpha * flash * 0.6)
        cv.rect(x - 2, y - 3, w + 4, 1, g); cv.rect(x - 2, y + h + 2, w + 4, 1, g)
    if label and label_k > 0:
        lw = text_width(label, label_font) + 6
        lx = x - 2 if label_side == 'left' else x + w + 2 - lw
        ly = y - 2 - 15
        a2 = alpha * min(1.0, label_k)
        cv.rect(lx, ly, lw, 14, _a(FRAME, a2)); cv.rect(lx + 1, ly + 1, lw - 2, 12, _a(ramp['dark'], a2))
        cv.rect(lx + 1, ly + 1, lw - 2, 1, _a(ramp['mid'], a2))
        cv.text(lx + 3, ly - 1, label, _a(ramp['top'], a2), label_font)
    if pct:
        s = f'{int(round(k * 100))}%'
        cv.text(x + w + 4, y - 5, s, _a(ramp['top'], alpha), 'zh10', outline=_a(FRAME, alpha))


def cast_shatter(cv, x, y, w, k, age, h=5, ramp=BLUE, alpha=1.0, seed=3, floor=None, show_frame=True):
    """被打断：age 秒（0 = 被碰的那一帧）。0–0.08 白闪 → 填充碎成 2–3 px 方块飞散下落 → 槽体红闪后恢复空槽。
    floor = 碎片落地的 UI y（None = 一直掉出画面）。"""
    if alpha <= 0 or age < 0: return
    x, y = int(round(x)), int(round(y))
    if show_frame:
        _frame(cv, x, y, w, h, alpha)
        rk = max(0.0, 1 - age / 0.45)
        if rk > 0: cv.rect(x, y, w, h, _a(RED['mid'], alpha * rk * 0.85))
    wf = int(round(w * max(0.0, min(1.0, k))))
    if age < 0.07:
        _fill_rows(cv, x, y, wf, h, ramp, alpha, mix_white=0.8)
        return
    rng = np.random.default_rng(seed)
    a = age - 0.07
    for bx in range(0, wf, 3):
        for by in range(0, h, 3):
            vx = rng.uniform(-38, 38) + (bx - wf * 0.5) * 0.35
            vy = rng.uniform(-75, -25)
            spin = rng.uniform(0, 1)
            px = x + bx + vx * a; py = y + by + vy * a + 210 * a * a
            if floor is not None and py > floor: py = floor
            life = 0.75 + spin * 0.35
            fa = alpha * max(0.0, 1 - a / life)
            if fa <= 0: continue
            col = ramp['top'] if by == 0 else (ramp['hi'] if spin > 0.5 else ramp['mid'])
            s = 3 if spin < 0.6 else 2
            if a > 0.25 and spin > 0.7: s = 1
            cv.rect(int(px), int(py), s, min(s, h - by), _a(col, fa))


def mp_bar(cv, x, y, n, lit, t=0.0, cell=5, gap=1, h=4, ramp=BLUE, new_age=None, alpha=1.0, label=None):
    """分格蓝条：n 格，lit 可以是小数（最后一格按比例亮）。new_age = 刚点亮那格的年龄（秒），白闪 + 上浮「+1」。"""
    if alpha <= 0: return
    x, y = int(round(x)), int(round(y))
    W = n * (cell + gap) - gap
    _frame(cv, x, y, W, h, alpha, track=False)
    cv.rect(x, y, W, h, _a(TRACK, alpha))
    for i in range(n):
        cx = x + i * (cell + gap)
        f = max(0.0, min(1.0, lit - i))
        if f <= 0:
            cv.rect(cx, y, cell, h, _a(TRACK2, alpha)); continue
        breathe = 0.12 * (0.5 + 0.5 * math.sin(t * 3.1 + i * 0.6))
        fw = max(1, int(round(cell * f)))
        _fill_rows(cv, cx, y, fw, h, ramp, alpha, mix_white=breathe)
        if gap: cv.rect(cx + cell, y, gap, h, _a(FRAME, alpha))
    if new_age is not None and 0 <= new_age < 0.9 and lit >= 1:
        i = int(math.ceil(lit)) - 1; cx = x + i * (cell + gap)
        fl = max(0.0, 1 - new_age / 0.25)
        if fl > 0: cv.rect(cx - 1, y - 1, cell + 2, h + 2, _a(C('#ffffff'), alpha * fl))
        rise = new_age / 0.9
        cv.text(cx - 2, int(y - 12 - 8 * rise), '+1', _a(ramp['top'], alpha * (1 - rise)), 'zh10', outline=_a(FRAME, alpha * (1 - rise)))
    if label:
        cv.text(x - text_width(label, 'zh10') - 4, y - 5, label, _a(ramp['top'], alpha), 'zh10', outline=_a(FRAME, alpha))


def film_rail(cv, t, segs, x=150, y=5, w=180, h=2, alpha=1.0, gift_last=True, done_flash=0.0, show_label=(0.0, 3.0)):
    """顶部全片读条。segs = [(name, t0, t1), ...]（各章节在成片里的起止秒）。
    当前章节开始后 show_label 秒内在条下方显示章节名（滑入 → 停 → 收起），之后只留细条。"""
    if alpha <= 0 or not segs: return
    T0, T1 = segs[0][1], segs[-1][2]
    n = len(segs); sw = (w - (n - 1)) / n
    for i, (name, a, b) in enumerate(segs):
        sx = x + int(round(i * (sw + 1))); ex = x + int(round(i * (sw + 1) + sw))
        cv.rect(sx, y, ex - sx, h, _a(TRACK2, alpha * 0.9))
        f = 0.0 if t <= a else (1.0 if t >= b else (t - a) / (b - a))
        if f > 0:
            fw = max(1, int(round((ex - sx) * f)))
            ramp = GOLD if done_flash > 0 else BLUE
            cv.rect(sx, y, fw, 1, _a(ramp['top'], alpha)); cv.rect(sx, y + 1, fw, h - 1, _a(ramp['hi'], alpha))
            if f < 1: cv.rect(sx + fw - 1, y - 1, 1, h + 2, _a(C('#ffffff'), alpha * 0.9))
        if i == n - 1 and gift_last:                                              # gift icon after the last segment
            gx, gy = ex + 3, y - 3
            cv.rect(gx, gy + 2, 7, 5, _a(GOLD['mid'], alpha)); cv.rect(gx, gy + 2, 7, 1, _a(GOLD['top'], alpha))
            cv.rect(gx + 3, gy + 1, 1, 6, _a(RED['hi'], alpha)); cv.rect(gx - 1, gy + 1, 9, 1, _a(GOLD['hi'], alpha))
            cv.px(gx + 2, gy, _a(RED['hi'], alpha)); cv.px(gx + 4, gy, _a(RED['hi'], alpha))
        # chapter label
        if a <= t < b:
            u = t - a
            lo, hi_ = show_label
            if lo <= u < hi_ + 0.4:
                k = min(1.0, (u - lo) / 0.25) * (1.0 if u < hi_ else max(0.0, 1 - (u - hi_) / 0.4))
                tw = text_width(name, 'zh10')
                lx = int((sx + ex) / 2 - tw / 2); ly = y + h + 2 + int(3 * (1 - k))
                cv.text(lx, ly, name, _a(BLUE['top'], alpha * k), 'zh10', outline=_a(FRAME, alpha * k))
    if done_flash > 0:
        cv.rect(x - 2, y - 2, w + 4, h + 4, _a(GOLD['top'], alpha * done_flash * 0.5))


def orb_sprite(r=7, t=0.0, dim=0.0, ramp=BLUE, halo=True):
    """注意力光核：返回 (rgba uint8, E float32)，中心在 (R, R)，R = r + 3（含光晕）。dim 0..1 变暗（被吸走）。
    同心色带（光从左上）+ 一道绕球心慢转的亮弧 + 2 px 高光 + 1 px 光晕环（外面一圈稀疏抖动，呼吸）。"""
    R = r + 3; S = 2 * R + 1
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    dx, dy = xx + 0.5 - (R + 0.5), yy + 0.5 - (R + 0.5)
    d = np.sqrt(dx * dx + dy * dy)
    rgba = np.zeros((S, S, 4), np.uint8); E = np.zeros((S, S), np.float32)
    lum = 1.0 - 0.5 * dim
    def cc(c): return (int(c[0] * lum), int(c[1] * lum), int(c[2] * lum), 255)
    body = d <= r
    lx, ly = -r * 0.38, -r * 0.42                                   # light point
    dl = np.sqrt((dx - lx) ** 2 + (dy - ly) ** 2) / (r * 1.45)
    band = np.clip((dl * 4).astype(int), 0, 3)                       # 0 brightest
    for i, c in enumerate((ramp['top'], ramp['hi'], ramp['mid'], ramp['dark'])):
        m = body & (band == i); rgba[m] = cc(c)
    ang = (np.arctan2(dy, dx) - t * 2.2) % (2 * np.pi)
    arc = body & (d > r - 2.2) & (d <= r - 0.8) & (ang < 1.1)       # rotating bright arc on the rim
    rgba[arc] = cc(ramp['hi'])
    rim = body & (d > r - 0.8)
    rgba[rim & ~arc] = cc(ramp['dark'])
    sx, sy = int(round(R + lx * 0.8)), int(round(R + ly * 0.8))
    for ox, oy in ((0, 0), (1, 0), (0, 1)): rgba[sy + oy, sx + ox] = (255, 255, 255, 255)
    E[body] = (0.5 + 0.4 * (3 - band[body]) / 3) * lum
    if halo:
        pulse = 0.5 + 0.5 * math.sin(t * 3.0)
        ring1 = (d > r) & (d <= r + 1.0)
        rgba[ring1] = (*ramp['hi'][:3], int(200 * lum)); E[ring1] = 0.45 * lum
        ring2 = (d > r + 1.0) & (d <= r + 2.4)
        chk = ((xx.astype(int) + yy.astype(int)) % 2 == 0) & (((xx.astype(int) // 2 + yy.astype(int) // 2 + int(t * 6)) % 3) != 0)
        m2 = ring2 & chk & (pulse * (1 - dim) > 0.25)
        rgba[m2] = (*ramp['top'][:3], int(150 * lum)); E[m2] = 0.35 * lum
    return rgba, E
