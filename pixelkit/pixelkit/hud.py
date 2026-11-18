"""pixelkit.hud - 「微光 HUD」高质感游戏界面（001《深度工作》沉淀，可复用）。

全部画在 480x270 UI 画布（×4 输出）；每个组件同时往一张「辉光画布」gv 上画发光部分，合成时 compose() 把 gv 模糊后加到画面上，
UI 才有真正的光晕（这是旧 UI「平」的主要原因）。

    cv, gv = UICanvas(), UICanvas()
    cast_bar_pro(cv, gv, x, y, w, k, t, icon='rune', name='读条')    读条 Pro：技能插槽 + 双线金框 + 玻璃槽 + 流动能量 + 前沿辉光
    cast_shatter_pro(cv, gv, x, y, w, k, age, ...)                     被打断：玻璃裂纹 → 碎片飞散 → 红闪 → 空槽
    dmg_number(cv, gv, '99999', cx, cy, age, scale=3)                   伤害数字：逐位弹出 + 渐变 + 描边 + 投影 + 辉光 + 星芒
    roll_number(cv, gv, value, x, y, ...)                               老虎机滚动数字（每一位竖向翻滚，带动态模糊行）
    speed_lines(cv, t, cx, cy, k)                                       冲击速度线（放射，逐帧闪烁）
    slam_stamp(cv, gv, '免费', cx, cy, age)                              盖章：从 2× 砸下 + 冲击环 + 碎屑
    panel(cv, gv, x, y, w, h, k, title=...)                             黑金面板：双线金边、角菱形、标题条、斜向扫光
    name_tag(cv, gv, text, x, y, k, ramp)                               带引线的名牌
    compose(img, cv, gv, strength=1.0)                                  合成：辉光（两层模糊）+ UI 清晰层
"""
import math
import numpy as np
import cv2
from .core import C, text_width, text_mask, Canvas
from .ui import _a, UICanvas
from .castbar import BLUE, GOLD, RED, GREY, FRAME

INK = C('#0b0a16'); INK2 = C('#151227'); GLASS = C('#0a1226'); GLASS2 = C('#14203f')
G_DK = C('#6a4614'); G_MD = C('#b8862c'); G_HI = C('#f2cf72'); G_TOP = C('#fff1c2')
WHITE = C('#ffffff')


def _hline(cv, x, y, w, c): cv.rect(int(x), int(y), int(w), 1, c)
def _vline(cv, x, y, h, c): cv.rect(int(x), int(y), 1, int(h), c)


def _diamond(cv, cx, cy, r, c, c2=None):
    for dy in range(-r, r + 1):
        w = r - abs(dy)
        cv.rect(int(cx - w), int(cy + dy), 2 * w + 1, 1, c)
    if c2 is not None and r >= 2: cv.px(int(cx), int(cy - r + 1), c2)


# ------------------------------------------------------------------ cast bar pro
ICONS = {
    'rune': ['..#####..', '.#.....#.', '#..#.#..#', '#...#...#', '#.#####.#', '#...#...#', '#..#.#..#', '.#.....#.', '..#####..'],
    'eye':  ['.........', '..#####..', '.#.....#.', '#..###..#', '#..#.#..#', '#..###..#', '.#.....#.', '..#####..', '.........'],
    'sword': ['.......##', '......###', '.....###.', '#...###..', '.#.###...', '..###....', '.##.#....', '##...#...', '#........'],
    'mp':   ['....#....', '...###...', '..#####..', '.#######.', '#########', '#########', '.#######.', '..#####..', '.........'],
}


def _icon(cv, gv, cx, cy, kind, ramp, alpha, glow):
    g = ICONS.get(kind, ICONS['rune'])
    h = len(g); w = len(g[0])
    for yy, row in enumerate(g):
        for xx, ch in enumerate(row):
            if ch == '#':
                cv.px(cx - w // 2 + xx, cy - h // 2 + yy, _a(ramp['top'], alpha))
                if gv is not None and glow > 0: gv.px(cx - w // 2 + xx, cy - h // 2 + yy, _a(ramp['hi'], alpha * glow))


def _socket(cv, gv, cx, cy, r, t, ramp, alpha, icon, glow=0.0, ring_flash=0.0):
    """round gold socket with a rune inside."""
    for dy in range(-r - 2, r + 3):
        for dx in range(-r - 2, r + 3):
            d = math.hypot(dx + 0.5 - 0.5, dy)
            x, y = cx + dx, cy + dy
            if d <= r - 1.5:
                v = 1 - d / r
                c = GLASS2 if (dx + dy) < -r * 0.3 else GLASS
                cv.px(x, y, _a(c, alpha))
            elif d <= r - 0.5: cv.px(x, y, _a(FRAME, alpha))
            elif d <= r + 0.6:
                c = G_HI if (dx + dy) < 0 else G_MD
                cv.px(x, y, _a(c, alpha))
            elif d <= r + 1.6: cv.px(x, y, _a(G_DK if (dx + dy) > 0 else G_MD, alpha))
            elif d <= r + 2.5: cv.px(x, y, _a(FRAME, alpha))
    _icon(cv, gv, cx, cy, icon, ramp, alpha * (0.55 + 0.45 * glow), 0.6 + glow)
    if ring_flash > 0 and gv is not None:
        rr = r + 3 + (1 - ring_flash) * 10
        for a in range(0, 360, 6):
            x = cx + math.cos(math.radians(a)) * rr; y = cy + math.sin(math.radians(a)) * rr
            gv.px(int(x), int(y), _a(ramp['top'], ring_flash)); cv.px(int(x), int(y), _a(ramp['top'], ring_flash))


def cast_bar_pro(cv, gv, x, y, w, k, t, h=8, ramp=BLUE, icon='rune', name=None, alpha=1.0, flash=0.0, stall=0.0,
                 show_time=None, socket=True, ticks=True, energy=True, shake=(0, 0)):
    """高质感读条。(x, y) = 槽体左上角；socket 画在槽体左侧（半径 h-1）。k 0..1；flash 满格白闪；stall 卡住颤动。"""
    if alpha <= 0: return
    x, y = int(round(x + shake[0])), int(round(y + shake[1])); w = int(w)
    k = max(0.0, min(1.0, k))
    # --- frame: outer ink, gold double line, glass track
    cv.rect(x - 3, y - 3, w + 7, h + 6, _a(FRAME, alpha * 0.92))
    _hline(cv, x - 2, y - 2, w + 4, _a(G_HI, alpha)); _hline(cv, x - 2, y + h + 1, w + 4, _a(G_DK, alpha))
    _vline(cv, x - 2, y - 2, h + 4, _a(G_MD, alpha)); _vline(cv, x + w + 1, y - 2, h + 4, _a(G_DK, alpha))
    cv.rect(x, y, w, h, _a(GLASS, alpha)); _hline(cv, x, y, w, _a(GLASS2, alpha))
    _diamond(cv, x + w + 4, y + h // 2, 3, _a(G_HI, alpha), _a(G_TOP, alpha))
    # --- fill
    wf = int(round(w * k))
    if stall > 0 and 0 < wf < w: wf = max(1, wf + int(round(math.sin(t * 43) * 1.2 * stall)))
    if wf > 0:
        rows = [ramp['top'], ramp['hi']] + [ramp['mid']] * max(0, h - 4) + [ramp['dark'], ramp['dark']]
        for r in range(h):
            c = rows[min(r, len(rows) - 1)]
            if flash > 0: c = tuple(int(c[i] + (255 - c[i]) * flash) for i in range(3)) + (255,)
            cv.rect(x, y + r, wf, 1, _a(c, alpha))
        if energy and flash < 0.9:
            # flowing energy: soft brightness waves travelling right (Bayer-dithered between mid and hi) + sparkles
            B4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
            for xx in range(0, max(0, wf - 3)):
                wv = 0.5 + 0.5 * math.sin((xx - t * 42) / 5.5) * math.sin((xx + t * 17) / 13.0)
                for r in range(2, h - 2):
                    if wv * 16 > B4[r % 4][xx % 4] + 4: cv.px(x + xx, y + r, _a(ramp['hi'], alpha))
            rng = np.random.default_rng(int(t * 30) % 997)
            for _ in range(max(1, wf // 10)):
                sx = rng.integers(0, max(1, wf - 2)); sy = rng.integers(1, h - 1)
                cv.px(x + sx, y + sy, _a(WHITE, alpha * 0.8))
        # leading edge
        cv.rect(x + wf - 2, y, 2, h, _a(WHITE, alpha)); cv.rect(x + wf - 3, y + 1, 1, h - 2, _a(ramp['top'], alpha))
        if gv is not None:
            gv.rect(x, y + 1, wf, h - 2, _a(ramp['hi'], alpha * (0.55 + 0.45 * flash)))
            gv.rect(x + wf - 4, y - 2, 6, h + 4, _a(ramp['top'], alpha))
        # sparks converging to the edge
        if k < 0.999:
            ex, ey = x + wf, y + h / 2
            for i in range(10):
                ph = ((t * (1.4 if stall < 0.5 else 0.12)) + i / 10.0) % 1.0
                ang = i * 2.39996 + 0.5
                rad = (1 - ph) ** 1.3 * (14 + 6 * ((i * 37) % 5) / 5)
                px_, py_ = ex + math.cos(ang) * rad * 1.5, ey + math.sin(ang) * rad
                cv.px(int(px_), int(py_), _a(ramp['top'] if i % 2 else WHITE, alpha * (0.25 + 0.75 * ph)))
                if gv is not None: gv.px(int(px_), int(py_), _a(ramp['hi'], alpha * ph))
    if ticks:
        for i in range(1, 10):
            tx = x + int(w * i / 10)
            cv.px(tx, y + h - 1, _a(FRAME, alpha * 0.8)); cv.px(tx, y, _a(FRAME, alpha * 0.5))
    if flash > 0 and gv is not None:
        gv.rect(x - 6, y - 6, w + 14, h + 12, _a(ramp['top'], alpha * flash))
    # --- socket + name + time
    if socket:
        r = h + 2
        _socket(cv, gv, x - r - 4, y + h // 2, r, t, ramp, alpha, icon, glow=k if k < 1 else 1.0, ring_flash=flash)
    if name:
        nx = x + 2; ny = y - 17
        tw = text_width(name, 'zh10')
        cv.rect(nx - 2, ny + 2, tw + 8, 12, _a(INK, alpha * 0.85))
        _hline(cv, nx - 2, ny + 14, tw + 8, _a(G_MD, alpha))
        cv.text(nx + 2, ny, name, _a(G_TOP, alpha), 'zh10')
    if show_time is not None:
        s = f'{show_time:.1f}s'
        cv.text(x + w + 9, y - 4, s, _a(ramp['top'], alpha), 'zh10', outline=_a(FRAME, alpha))


def cast_shatter_pro(cv, gv, x, y, w, k, age, h=8, ramp=BLUE, alpha=1.0, seed=5, floor=None, icon='rune', socket=True):
    """被打断：0–0.06 裂纹（白）→ 0.06+ 填充与玻璃碎成方块飞散、红闪、框体抖动 → 空槽留下暗红余辉。"""
    if age < 0 or alpha <= 0: return
    shake = (0, 0)
    if age < 0.3: shake = (int(round(math.sin(age * 90) * 3 * (1 - age / 0.3))), int(round(math.cos(age * 70) * 2 * (1 - age / 0.3))))
    wf = int(round(w * k))
    if age < 0.06:
        cast_bar_pro(cv, gv, x, y, w, k, 0.0, h, ramp, icon, None, alpha, flash=0.4, energy=False, socket=socket, shake=shake)
        rng = np.random.default_rng(seed)
        for _ in range(5):                                    # crack lines
            cx = x + rng.integers(2, max(3, wf)); cy = y + h // 2
            for s in range(12):
                cx += rng.integers(-1, 3); cy += rng.integers(-2, 3)
                cv.px(int(cx), int(min(y + h - 1, max(y, cy))), _a(WHITE, alpha))
        return
    cast_bar_pro(cv, gv, x, y, w, 0.0, 0.0, h, ramp, icon, None, alpha, socket=socket, shake=shake)
    rk = max(0.0, 1 - (age - 0.06) / 0.5)
    if rk > 0:
        cv.rect(int(x + shake[0]), int(y + shake[1]), w, h, _a(RED['mid'], alpha * rk * 0.7))
        if gv is not None: gv.rect(x - 4, y - 4, w + 8, h + 8, _a(RED['hi'], alpha * rk))
    rng = np.random.default_rng(seed)
    a = age - 0.06
    for bx in range(0, max(1, wf), 3):
        for by in range(0, h, 3):
            vx = rng.uniform(-60, 60) + (bx - wf * 0.4) * 0.6
            vy = rng.uniform(-110, -30)
            spin = rng.uniform(0, 1)
            px_ = x + bx + vx * a; py_ = y + by + vy * a + 300 * a * a
            if floor is not None and py_ > floor: py_ = floor
            life = 0.7 + spin * 0.5
            fa = alpha * max(0.0, 1 - a / life)
            if fa <= 0: continue
            col = WHITE if spin > 0.85 else (ramp['top'] if by == 0 else (ramp['hi'] if spin > 0.45 else ramp['mid']))
            s = 3 if spin < 0.5 else 2
            if a > 0.3 and spin > 0.6: s = 1
            cv.rect(int(px_), int(py_), s, s, _a(col, fa))
            if gv is not None and spin > 0.6: gv.rect(int(px_), int(py_), s, s, _a(ramp['hi'], fa))


# ------------------------------------------------------------------ numbers
_GLYPH_CACHE = {}
def _glyph(s, fname='zh12'):
    key = (s, fname)
    if key not in _GLYPH_CACHE: _GLYPH_CACHE[key] = text_mask(s, fname)
    return _GLYPH_CACHE[key]


def big_text(cv, gv, s, x, y, scale=3, ramp=GOLD, alpha=1.0, fname='zh12', glow=0.8, outline=True, shadow=True):
    """渐变大字（逐行：top→hi→mid→dark）+ 1 px 描边 + 投影 + 辉光；(x, y) 左上角。返回宽度。"""
    m = _glyph(s, fname)
    if scale != 1: m = cv2.resize(m.astype(np.uint8), (m.shape[1] * scale, m.shape[0] * scale), interpolation=cv2.INTER_NEAREST) > 0
    H, W = m.shape
    ys = np.nonzero(m.any(1))[0]
    if len(ys) == 0: return W
    y0, y1 = ys.min(), ys.max()
    x, y = int(x), int(y)
    if shadow:
        sh = np.zeros((H, W), bool); sh[2:, 2:] = m[:-2, :-2]
        cv._mask(sh, x, y, _a(C('#000000'), alpha * 0.55))
    if outline:
        o = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        cv._mask(o & ~m, x, y, _a(FRAME, alpha))
    stops = [ramp['top'], ramp['top'], ramp['hi'], ramp['hi'], ramp['mid'], ramp['dark']]
    for r in range(y0, y1 + 1):
        u = (r - y0) / max(1, y1 - y0)
        c = stops[min(len(stops) - 1, int(u * len(stops)))]
        row = np.zeros_like(m); row[r] = m[r]
        cv._mask(row, x, y, _a(c, alpha))
    if gv is not None and glow > 0: gv._mask(m, x, y, _a(ramp['hi'], alpha * glow))
    return W


def dmg_number(cv, gv, s, cx, cy, age, scale=3, ramp=GOLD, life=1.4, stagger=0.035, rise=10, alpha=1.0, stars=True):
    """伤害数字：每一位依次从 1.8 倍砸下（过冲回弹）、整体上浮淡出，周围四角星芒。(cx, cy) = 中心。"""
    if age < 0 or age > life: return
    fade = 1.0 if age < life - 0.3 else max(0.0, (life - age) / 0.3)
    widths = [text_width(ch, 'zh12') * scale for ch in s]
    tot = sum(widths)
    x = cx - tot / 2
    yb = cy - 9 * scale - rise * min(1.0, age / life)
    for i, ch in enumerate(s):
        a = age - i * stagger
        if a < 0: x += widths[i]; continue
        u = min(1.0, a / 0.14)
        sc = scale + (1 - u) * scale * 0.8 - (math.sin(min(1, a / 0.22) * math.pi) * 0.25 if u >= 1 else 0)
        si = max(1, int(round(sc)))
        dy = -(1 - u) * 14
        big_text(cv, gv, ch, x + (widths[i] - text_width(ch, 'zh12') * si) / 2, yb + dy - (si - scale) * 9, si, ramp, alpha * fade)
        x += widths[i]
    if stars:
        for j in range(6):
            ph = (age * 1.2 + j / 6) % 1
            ang = j * 1.05 + 0.3
            r = tot * 0.45 + 18 * ph
            sx = cx + math.cos(ang) * r; sy = cy - 6 * scale + math.sin(ang) * r * 0.5
            a2 = alpha * fade * (1 - ph)
            _star(cv, gv, sx, sy, 2 if j % 2 else 3, ramp['top'], a2)


def _star(cv, gv, x, y, r, c, a):
    x, y = int(x), int(y)
    for d in range(-r, r + 1):
        cv.px(x + d, y, _a(c, a)); cv.px(x, y + d, _a(c, a))
    cv.px(x, y, _a(WHITE, a))
    if gv is not None: gv.rect(x - 1, y - 1, 3, 3, _a(c, a))


def roll_number(cv, gv, value, x, y, digits=None, prefix='', scale=1, ramp=GOLD, alpha=1.0, fname='zh12', commas=True, glow=0.5):
    """老虎机式滚动数字：value 是浮点数，每一位按小数部分竖向滚动（上一位滚出、下一位滚入），带一行动态模糊残影。"""
    v = max(0.0, value)
    iv = int(v); frac = v - iv
    s = str(iv)
    if digits: s = s.rjust(digits, '0')
    n = len(s)
    cw = text_width('0', fname) * scale; ch = 16 * scale
    xx = int(x)
    if prefix:
        xx += big_text(cv, gv, prefix, xx, y, scale, ramp, alpha, fname, glow) - 2 * scale
    for i, d in enumerate(s):
        place = n - 1 - i
        # the last digit rolls continuously; higher digits roll only while the lower ones wrap from 9 to 0
        if place == 0: f = frac
        else:
            lower = v / (10 ** place) - int(v / (10 ** place))
            f = max(0.0, (lower - (1 - 1 / (10 ** place))) * (10 ** place)) if lower > 1 - 1 / (10 ** place) else 0.0
        cur = int(d); nxt_ = (cur + 1) % 10
        off = int(round(f * ch))
        sub = Canvas(cw + 4, ch + 4)
        big_text(sub, None, str(cur), 1, 1 - off, scale, ramp, 1.0, fname, 0)
        if off > 0: big_text(sub, None, str(nxt_), 1, 1 - off + ch, scale, ramp, 1.0, fname, 0)
        cv.blit(sub.a, xx - 1, y - 1, alpha)
        if gv is not None and glow > 0: gv.blit(sub.a, xx - 1, y - 1, alpha * glow * 0.6)
        xx += cw
        if commas and place > 0 and place % 3 == 0:
            cv.rect(xx, y + ch - 6, 2 * scale, 3 * scale, _a(ramp['mid'], alpha)); xx += 4 * scale
    return xx - int(x)


# ------------------------------------------------------------------ impact helpers
def speed_lines(cv, t, cx, cy, k=1.0, n=46, r0=70, col=WHITE, seed=3):
    """冲击速度线：从 r0 往外放射到画面边缘，每 2 帧换一组（30 fps 下 15 Hz 闪烁）。"""
    if k <= 0: return
    rng = np.random.default_rng(seed + int(t * 15))
    for i in range(n):
        ang = rng.uniform(0, 2 * math.pi)
        rr = r0 * rng.uniform(0.85, 1.4)
        L = rng.uniform(80, 260)
        w = 1 if rng.uniform() < 0.7 else 2
        for s in range(int(L)):
            r = rr + s
            x = cx + math.cos(ang) * r; y = cy + math.sin(ang) * r * 0.62
            if not (0 <= x < cv.w and 0 <= y < cv.h): break
            a = k * (0.35 + 0.65 * (s / L)) * 0.8
            cv.rect(int(x), int(y), w, 1, _a(col, a))


def slam_stamp(cv, gv, text, cx, cy, age, ramp=RED, scale=2, angle_seed=0, alpha=1.0):
    """盖章：0–0.08 s 从 2.2 倍砸下 → 冲击环 + 碎屑 → 停住（轻微墨色不均）。"""
    if age < 0: return
    u = min(1.0, age / 0.08)
    sc = max(1, int(round(scale * (2.2 - 1.2 * u))))
    m = _glyph(text, 'zh12')
    tw, th = m.shape[1] * sc, m.shape[0] * sc
    pad = 4 * sc
    x0, y0 = int(cx - tw / 2 - pad), int(cy - th / 2 - pad)
    w, h = tw + 2 * pad, th + 2 * pad
    a = alpha * (0.4 + 0.6 * u)
    for i in range(2):
        cv.rect(x0 + i * 2, y0 + i * 2, w - i * 4, 1, _a(ramp['hi'], a)); cv.rect(x0 + i * 2, y0 + h - 1 - i * 2, w - i * 4, 1, _a(ramp['hi'], a))
        cv.rect(x0 + i * 2, y0 + i * 2, 1, h - i * 4, _a(ramp['hi'], a)); cv.rect(x0 + w - 1 - i * 2, y0 + i * 2, 1, h - i * 4, _a(ramp['hi'], a))
    mm = cv2.resize(m.astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST) > 0
    rng = np.random.default_rng(7)
    wear = rng.uniform(0, 1, mm.shape) < 0.08
    cv._mask(mm & ~wear, x0 + pad, y0 + pad, _a(ramp['hi'], a))
    if gv is not None: gv._mask(mm, x0 + pad, y0 + pad, _a(ramp['mid'], a * 0.7))
    if age >= 0.08 and age < 0.5:                                    # impact ring + debris
        v = (age - 0.08) / 0.42
        rr = max(w, h) * (0.6 + 0.9 * v)
        for d in range(0, 360, 5):
            x = cx + math.cos(math.radians(d)) * rr; y = cy + math.sin(math.radians(d)) * rr * 0.6
            cv.px(int(x), int(y), _a(ramp['top'], alpha * (1 - v)))
        for j in range(10):
            ang = j * 0.63 + 0.2
            r = max(w, h) * 0.5 + 40 * v
            cv.rect(int(cx + math.cos(ang) * r), int(cy + math.sin(ang) * r * 0.6), 2, 2, _a(ramp['hi'], alpha * (1 - v)))


# ------------------------------------------------------------------ panels / tags
def panel(cv, gv, x, y, w, h, k=1.0, title=None, title_ramp=GOLD, alpha=1.0, sweep=None, accent=None):
    """黑金面板：k 0..1 从左展开；sweep = 斜向扫光进度 0..1（None 不扫）。"""
    if k <= 0 or alpha <= 0: return
    ww = max(4, int(w * (1 - (1 - k) ** 3)))
    x, y = int(x), int(y)
    cv.rect(x, y, ww, h, _a(INK, alpha * 0.9))
    cv.rect(x + 1, y + 1, ww - 2, 1, _a(INK2, alpha))
    _hline(cv, x, y, ww, _a(G_HI, alpha)); _hline(cv, x, y + h - 1, ww, _a(G_DK, alpha))
    _vline(cv, x, y, h, _a(G_MD, alpha)); _vline(cv, x + ww - 1, y, h, _a(G_DK, alpha))
    _hline(cv, x + 3, y + 3, ww - 6, _a(G_DK, alpha * 0.8)); _hline(cv, x + 3, y + h - 4, ww - 6, _a(G_DK, alpha * 0.8))
    for (dx, dy) in ((0, 0), (ww - 1, 0), (0, h - 1), (ww - 1, h - 1)):
        _diamond(cv, x + dx, y + dy, 3, _a(G_HI, alpha), _a(G_TOP, alpha))
    if accent is not None: cv.rect(x + 1, y + 4, 2, h - 8, _a(accent, alpha))
    if title and k > 0.7:
        a2 = alpha * min(1.0, (k - 0.7) / 0.3)
        big_text(cv, gv, title, x + 10, y + 6, 2, title_ramp, a2, glow=0.35)
    if sweep is not None and 0 <= sweep < 1:
        sx = x + int(sweep * (ww + h)) - h
        for i in range(h):
            for d in range(4):
                xx = sx + i // 2 + d
                if x < xx < x + ww - 1: cv.px(xx, y + i, _a(WHITE, alpha * 0.18 * (1 - abs(d - 1.5) / 2)))


def name_tag(cv, gv, text, ax, ay, k, ramp=BLUE, side=1, alpha=1.0, fname='zh12'):
    """从世界点 (ax, ay) 拉一条引线到名牌；k 0..1 引线先长、牌子后弹出。"""
    if k <= 0: return
    tw = text_width(text, fname) + 12
    bx = int(ax + side * 26) if side > 0 else int(ax - 26 - tw)
    by = int(ay - 30)
    lk = min(1.0, k / 0.4)
    ex = ax + (bx + (0 if side > 0 else tw) - ax) * lk; ey = ay + (by + 9 - ay) * lk
    cv.line(int(ax), int(ay), int(ex), int(ey), _a(ramp['hi'], alpha))
    if gv is not None: gv.line(int(ax), int(ay), int(ex), int(ey), _a(ramp['hi'], alpha * 0.6))
    cv.rect(int(ax) - 1, int(ay) - 1, 3, 3, _a(ramp['top'], alpha))
    if k > 0.4:
        u = min(1.0, (k - 0.4) / 0.3)
        a2 = alpha * u
        cv.rect(bx, by, tw, 19, _a(INK, a2 * 0.92))
        _hline(cv, bx, by, tw, _a(ramp['hi'], a2)); _hline(cv, bx, by + 18, tw, _a(ramp['dark'], a2))
        cv.rect(bx, by, 2, 19, _a(ramp['hi'], a2))
        cv.text(bx + 7, by + 0, text, _a(ramp['top'], a2), fname)
        if gv is not None: gv.rect(bx, by, 2, 19, _a(ramp['hi'], a2))


# ------------------------------------------------------------------ compose
def compose(img, cv, gv=None, strength=1.0, scale=4):
    """img: (H, W, 3) float 0..1 output frame. glow = gv blurred at two radii (tight + wide), added; then the UI on top."""
    from .scene import ui_over
    if gv is not None and gv.a[..., 3].any():
        g = gv.a.astype(np.float32) / 255.0
        g = g[..., :3] * g[..., 3:4]
        H, W = img.shape[:2]
        g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
        g1 = cv2.GaussianBlur(g, (0, 0), 6 * W / 1920)
        g2 = cv2.GaussianBlur(cv2.resize(g, (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), 7 * W / 1920)
        g2 = cv2.resize(g2, (W, H), interpolation=cv2.INTER_LINEAR)
        img = img + strength * (0.9 * g1 + 1.1 * g2)
        img = np.clip(img, 0, 1.2)
    return ui_over(img, cv.a, scale=scale)
