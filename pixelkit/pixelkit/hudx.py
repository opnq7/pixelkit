"""pixelkit.hudx - 「微光 HUD」扩展件（001《深度工作》正片沉淀）。和 hud.py 同一套外观：黑底、金色双线、玻璃槽、辉光层 gv。
全部画在 480x270 UI 画布，纯 t / age 函数（age = 距离这个事件开始的秒数）。

    chapter_card(cv, gv, age, i, names)            章节卡：顶部全片读条放大落到画面中央 → 当前段充能点亮 + 章名砸下 → 缩回顶部。返回背景压暗量
    skill_hotbar(cv, gv, x, y, t, slots)           技能栏：锁 → 解锁（锁碎、光环、图标弹出）→ 常亮
    choice_panel(cv, gv, x, y, w, t, q, opts, ...)  选择题面板：选项逐行滑入、光标跳动、打叉、选中发光
    icon(cv, gv, name, cx, cy, ramp, alpha, scale)  像素图标（msg / meet / form / note / doc / book / portal / split / drop / bag /
                                                    cert / people / lock / key / check / cross / gift / hourglass / coin）
    item_card(cv, gv, x, y, name, icon, ramp, age)  道具卡（灰 = 普攻，金 = 大招），从下方弹起
    check_mark / cross_mark(cv, gv, cx, cy, s, k)  对勾 / 叉的笔画动画（k 0..1）
    stroke_x(cv, gv, cx, cy, size, k, ramp)        马克笔画叉（两笔、笔刷粗细变化、末端飞溅）
    quest_list(cv, gv, x, y, w, title, rows, t)    任务卡：rows = [(text, done_at or None)]，勾选动画
    time_axis / time_block                          一天的时间轴 + 时间块（金块带流光、灰块安静）
    clock_ring(cv, gv, cx, cy, r, eaten, t)        24 段圆环，被一口一口啃掉（缺口带牙印）
    clock_face(cv, gv, cx, cy, r, t, hand, sectors) 钟面 + 扇区
    density_meter(cv, gv, x, y, h, k, t)           竖向「信息密度」表：分格、绿→黄→红、顶格闪
    error_bar(cv, gv, cx, cy, text, age)           红黑警示条 + 故障偏移
    book_says(cv, gv, age, portrait, out_age)      「书里说」角标：头像插槽 + 引号 + 小字
    status_flip(cv, gv, x, y, a, b, age, ra, rb)   状态牌翻牌（在线 → 专注中）
    input_card(cv, gv, x, y, w, label, val, t)     评论区输入框（光标闪）
    boss_bar(cv, gv, x, y, w, name, lv, hp, t, age) Boss 血条：砸下、名字、等级、血量、伤害残影
    hp_tag(cv, gv, cx, cy, text, ramp, age)        头顶小标签（Lv.1 / 意志力差？）
"""
import math
import numpy as np
import cv2
from .core import C, text_width, text_mask, Canvas
from .ui import _a
from .castbar import BLUE, GOLD, RED, GREY, FRAME
from . import hud as H
from .hud import INK, INK2, GLASS, GLASS2, G_DK, G_MD, G_HI, G_TOP, WHITE, _hline, _vline, _diamond, big_text, _star

GREEN = dict(dark=C('#1d4a2a'), mid=C('#2f9a4c'), hi=C('#6fdc7c'), top=C('#c8ffd0'), edge=C('#ffffff'))
AMBER = dict(dark=C('#6a3a08'), mid=C('#d07a16'), hi=C('#ffb340'), top=C('#ffe2a8'), edge=C('#ffffff'))


def ease_out(u): u = max(0.0, min(1.0, u)); return 1 - (1 - u) ** 3
def ease_io(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def back_out(u, s=1.7):
    u = max(0.0, min(1.0, u)); u -= 1; return u * u * ((s + 1) * u + s) + 1
def _mix(c, w, k): return tuple(int(c[i] + (w[i] - c[i]) * k) for i in range(3)) + (255,)


# ------------------------------------------------------------------ icons (11x11 ascii, letters = ramp steps)
ICONS = {
    'msg': ["..#######..", ".#aaaaaaa#.", "#abbbbbbbc#", "#bwbbwbbwc#", "#bbbbbbbbc#", ".#ccccccc#.", "..##c####..", "...#c#.....", "...##......"],
    'meet': [".##.....##.", "#aa#...#aa#", "#bb#.#.#bb#", ".##.#a#.##.", ".#a##b##a#.", "#ab#bbb#bc#", "#bb#cbc#bc#", "#cc#ccc#cc#", ".#########."],
    'form': ["#########..", "#wwwwwww##.", "#w#####w#w#", "#wwwwwwwww#", "#w###w###w#", "#wwwwwwwww#", "#w###w###w#", "#wwwwwwwww#", "#w###w###w#", "#wwwwwwwww#", "###########"],
    'note': [".#########.", "#aawaaaaaa#", "#a#######a#", "#aaaaaaaaa#", "#a#####aaa#", "#aaaaaaaaa#", "#a######aa#", "#aaaaaaaaa#", "#a####aaaa#", "#bbbbbbbbb#", ".#########."],
    'doc': ["#######....", "#wwwww##...", "#w###w#w#..", "#wwwww####.", "#w#######w#", "#wwwwwwwww#", "#w####b##w#", "#wwwwwbbww#", "#w##bbbbbw#", "#wwwwbbbww#", "###########"],
    'book': ["...........", "##.......##", "#a##...##c#", "#aaa#.#ccc#", "#a#a#.#c#c#", "#aaa#.#ccc#", "#a#a#.#c#c#", "#aaa#.#ccc#", "#aaab#bccc#", "##bbb#bbb##", "..##b#b##..", "....###...."],
    'puzzle': ["...###.....", "..#aaa#....", ".#ab#ba#...", "....#ba#...", "...#bb#....", "...#b#.....", "...#b#.....", "....#......", "...#w#.....", "....#......"],
    'star': ["....#....", "...#a#...", "...#a#...", "####b####", "#abbbbbc#", ".#bbbbc#.", "..#bbb#..", ".#bc#cb#.", ".#c#.#c#.", ".##...##."],
    'portal': ["...#####...", "..#aaaaa#..", ".#ab###ba#.", "#ab#ccc#ba#", "#a#cdddc#a#", "#a#cdwdc#a#", "#a#cdddc#a#", "#ab#ccc#ba#", ".#ab###ba#.", "..#aaaaa#..", "...#####..."],
    'split': ["###########", "#aaaaa#ggg#", "#abbba#ghg#", "#abwba#ggg#", "#abbba#ghg#", "#abbba#ggg#", "#abbba#ghg#", "#aaaaa#ggg#", "###########"],
    'drop': ["....##.....", "...#aa#....", "..#abba#...", "..#abba#...", ".#abbbba#..", "#abwbbbbc#.", "#abwbbbbc#.", "#abbbbbbc#.", ".#cbbbbc#..", "..#cccc#...", "...####...."],
    'bag': ["...#####...", "..#.....#..", ".#########.", "#ggggggggg#", "#ghhhhhhhg#", "#ghhwhhhhg#", "#ghhhhhhhg#", "#ggggggggg#", ".#########."],
    'cert': ["##########.", "#wwwwwwww#.", "#w######w#.", "#wwwwwwww#.", "#w####www#.", "#wwwww#a#..", "#wwww#aba#.", "######aba#.", ".....#b#b#.", ".....##.##."],
    'people': ["..##...##..", ".#gg#.#gg#.", ".#gg#.#gg#.", "..##...##..", ".#gg#.#gg#.", "#gggg#gggg#", "#gggg#gggg#", "###########"],
    'lock': ["...####....", "..#....#...", "..#....#...", ".########..", ".#aaaaaa#..", ".#ab##ba#..", ".#aab#aa#..", ".#cccccc#..", ".########.."],
    'key': ["..###......", ".#aaa#.....", "#aw.ab#####", "#a..ab#aaa#", ".#aaa#.#.#.", "..###......"],
    'gift': ["..#.#.#....", "...###.....", "#########..", "#aaa#raaa#.", "#########..", ".#bb#r#bb#.", ".#bb#r#bb#.", ".#cc#r#cc#.", ".#########."],
    'coin': ["..#####..", ".#aaaaa#.", "#aabbbaa#", "#ab#b#ba#", "#abb#bba#", "#ab#b#ba#", "#aabbbaa#", ".#ccccc#.", "..#####.."],
    'hourglass': ["#########", ".#wwwww#.", "..#bbb#..", "...#b#...", "...#w#...", "..#www#..", ".#bbbbb#.", "#########"],
}


def icon(cv, gv, name, cx, cy, ramp=GOLD, alpha=1.0, scale=1, glow=0.5):
    g = ICONS[name]
    h = len(g); w = max(len(r) for r in g)
    x0 = int(round(cx - w * scale / 2)); y0 = int(round(cy - h * scale / 2))
    pal = {'#': FRAME, 'a': ramp['top'], 'b': ramp['hi'], 'c': ramp['mid'], 'd': ramp['dark'], 'w': C('#f4f0ff'),
           'g': GREY['hi'], 'h': GREY['mid'], 'r': RED['hi']}
    for yy, row in enumerate(g):
        for xx, ch in enumerate(row):
            if ch == '.': continue
            c = pal.get(ch)
            if c is None: continue
            cv.rect(x0 + xx * scale, y0 + yy * scale, scale, scale, _a(c, alpha))
            if gv is not None and glow > 0 and ch in 'ab':
                gv.rect(x0 + xx * scale, y0 + yy * scale, scale, scale, _a(ramp['hi'], alpha * glow))


# ------------------------------------------------------------------ strokes
def _brush(cv, gv, pts, k, col, glow_col, alpha, width=3, glow=0.6):
    """draw polyline pts (list of (x, y)) up to fraction k with a tapered square brush."""
    if k <= 0: return None
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    L = sum(seg); target = L * min(1.0, k); acc = 0.0; last = pts[0]
    for i, s in enumerate(seg):
        n = max(1, int(s * 2))
        for j in range(n + 1):
            d = acc + s * j / n
            if d > target: return last
            u = d / max(1e-6, L)
            wv = max(1, int(round(width * (0.65 + 0.35 * math.sin(math.pi * u)))))
            x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * j / n; y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * j / n
            cv.rect(int(x - wv / 2), int(y - wv / 2), wv, wv, _a(col, alpha))
            if gv is not None: gv.rect(int(x - wv / 2), int(y - wv / 2), wv, wv, _a(glow_col, alpha * glow))
            last = (x, y)
        acc += s
    return last


def check_mark(cv, gv, cx, cy, s, k, ramp=GOLD, alpha=1.0, width=2):
    pts = [(cx - s * 0.5, cy), (cx - s * 0.12, cy + s * 0.38), (cx + s * 0.55, cy - s * 0.45)]
    _brush(cv, gv, pts, k, ramp['top'], ramp['hi'], alpha, width)


def cross_mark(cv, gv, cx, cy, s, k, ramp=RED, alpha=1.0, width=3):
    a = [(cx - s / 2, cy - s / 2), (cx + s / 2, cy + s / 2)]; b = [(cx + s / 2, cy - s / 2), (cx - s / 2, cy + s / 2)]
    _brush(cv, gv, a, min(1.0, k * 2), ramp['hi'], ramp['mid'], alpha, width)
    if k > 0.5: _brush(cv, gv, b, (k - 0.5) * 2, ramp['hi'], ramp['mid'], alpha, width)


def stroke_x(cv, gv, cx, cy, size, k, ramp=GOLD, alpha=1.0, width=4, seed=3):
    """马克笔画叉：第一笔 0–0.45，第二笔 0.5–0.95，最后一笔落下时溅几个点。"""
    s = size / 2
    a = [(cx - s, cy - s * 0.9), (cx - s * 0.2, cy - s * 0.05), (cx + s * 0.95, cy + s)]
    b = [(cx + s * 0.9, cy - s), (cx + s * 0.1, cy - s * 0.1), (cx - s, cy + s * 0.95)]
    _brush(cv, gv, a, min(1.0, k / 0.45), ramp['hi'], ramp['top'], alpha, width, 0.7)
    end = None
    if k > 0.5: end = _brush(cv, gv, b, min(1.0, (k - 0.5) / 0.45), ramp['hi'], ramp['top'], alpha, width, 0.7)
    for p in (a, b):                                                       # highlight line on each stroke
        if k > (0.45 if p is a else 0.95):
            _brush(cv, None, [(x - 1, y - 1) for x, y in p], 1.0, ramp['top'], ramp['top'], alpha * 0.8, 1)
    if k >= 0.95:
        rng = np.random.default_rng(seed)
        for _ in range(6):
            ang = rng.uniform(0, 6.28); r = rng.uniform(3, 9)
            cv.rect(int(cx - s + math.cos(ang) * r), int(cy + s + math.sin(ang) * r * 0.6), 1 + int(rng.uniform() > 0.6), 1, _a(ramp['hi'], alpha))


# ------------------------------------------------------------------ chapter card
def _rail_geom(u):
    """u 0 = top thin rail, 1 = centre big rail."""
    A = (120, 6, 240, 3); B = (60, 150, 360, 10)
    return tuple(A[i] + (B[i] - A[i]) * u for i in range(4))


def chapter_card(cv, gv, age, i, names, dur=1.45, gift_last=True):
    """章节卡（约 1.45 s）：0–0.32 顶部读条放大落到中央；0.3–0.75 第 i 段充能点亮（之前的段已满）；0.42 章名砸下；
    1.05–1.45 整条缩回顶部。返回背景压暗量 0..1（给场景乘暗用）。"""
    if age < 0 or age > dur: return 0.0
    n = len(names)
    if age < 0.32: u = ease_out(age / 0.32)
    elif age < dur - 0.4: u = 1.0
    else: u = 1 - ease_io((age - (dur - 0.4)) / 0.4)
    x, y, w, h = _rail_geom(u)
    x, y, w, h = int(x), int(y), int(w), max(2, int(round(h)))
    dim = 0.78 * min(1.0, age / 0.2) * (1.0 if age < dur - 0.35 else max(0.0, (dur - age) / 0.35))
    sw = (w - (n - 1) * 3) / n
    fill = ease_io((age - 0.3) / 0.45)
    for j in range(n):
        sx = int(round(x + j * (sw + 3))); ex = int(round(x + j * (sw + 3) + sw)); ww = ex - sx
        cv.rect(sx - 1, y - 1, ww + 2, h + 2, _a(FRAME, 0.95))
        cv.rect(sx, y, ww, h, _a(GLASS, 1.0)); _hline(cv, sx, y, ww, _a(GLASS2, 1.0))
        f = 1.0 if j < i else (fill if j == i else 0.0)
        ramp = GOLD if j == i else BLUE
        if f > 0:
            fw = max(1, int(round(ww * f)))
            rows = [ramp['top'], ramp['hi']] + [ramp['mid']] * max(0, h - 3) + [ramp['dark']]
            for r in range(h): cv.rect(sx, y + r, fw, 1, _a(rows[min(r, len(rows) - 1)], 1.0 if j == i else 0.75))
            if j == i and f < 1: cv.rect(sx + fw - 2, y - 1, 2, h + 2, _a(WHITE, 1.0)); gv.rect(sx + fw - 5, y - 4, 7, h + 8, _a(ramp['top'], 1.0))
            gv.rect(sx, y, fw, h, _a(ramp['hi'], 0.7 if j == i else 0.25))
        if u > 0.6 and h >= 6:                                             # little index under each segment
            a2 = min(1.0, (u - 0.6) / 0.4) * (1.0 if age < dur - 0.4 else max(0.0, 1 - (age - (dur - 0.4)) / 0.2))
            nm = names[j]; tw = text_width(nm, 'zh10')
            col = G_TOP if j == i else (BLUE['hi'] if j < i else C('#6c6c86'))
            cv.text(int((sx + ex) / 2 - tw / 2), y + h + 3, nm, _a(col, a2), 'zh10', outline=_a(FRAME, a2))
    if gift_last:
        gx = x + w + 4 + (3 if u > 0.5 else 0)
        icon(cv, gv, 'gift', gx + 4, y + h // 2, GOLD, 1.0, 1 if u < 0.5 else 2, glow=0.3)
    # big chapter name
    na = age - 0.42
    if na >= 0 and age < dur - 0.3:
        al = min(1.0, na / 0.06) * (1.0 if age < dur - 0.42 else max(0.0, (dur - 0.3 - age) / 0.12))
        k = min(1.0, na / 0.1)
        sc = 4 if k >= 1 else 5
        nm = names[i]
        tw = text_width(nm, 'zh12') * sc
        yy = int(150 - 22 - 18 * sc + 8 * (1 - k))
        big_text(cv, gv, nm, int(240 - tw / 2), yy, sc, GOLD, al, glow=0.9)
        lab = f'第 {i + 1} 段 / {n}'
        lw = text_width(lab, 'zh10')
        cv.text(int(240 - lw / 2), yy - 16, lab, _a(G_HI, al * 0.9), 'zh10', outline=_a(FRAME, al))
        if na < 0.3:                                                       # impact ring
            v = na / 0.3
            for d in range(0, 360, 4):
                rx = 240 + math.cos(math.radians(d)) * (tw * 0.55 + 70 * v); ry = yy + 9 * sc + math.sin(math.radians(d)) * (30 + 30 * v)
                cv.px(int(rx), int(ry), _a(G_TOP, 1 - v)); gv.px(int(rx), int(ry), _a(G_HI, 1 - v))
    return dim


# ------------------------------------------------------------------ skill hotbar
def _slot_frame(cv, gv, x, y, s, alpha, ramp=None, glow=0.0):
    cv.rect(x - 2, y - 2, s + 4, s + 4, _a(FRAME, alpha * 0.95))
    _hline(cv, x - 1, y - 1, s + 2, _a(G_HI, alpha)); _hline(cv, x - 1, y + s, s + 2, _a(G_DK, alpha))
    _vline(cv, x - 1, y - 1, s + 2, _a(G_MD, alpha)); _vline(cv, x + s, y - 1, s + 2, _a(G_DK, alpha))
    cv.rect(x, y, s, s, _a(GLASS, alpha)); cv.rect(x, y, s, s // 2, _a(GLASS2, alpha * 0.6))
    for (dx, dy) in ((-1, -1), (s, -1), (-1, s), (s, s)): cv.px(x + dx, y + dy, _a(G_TOP, alpha))
    if ramp is not None and glow > 0:
        gv.rect(x - 3, y - 3, s + 6, s + 6, _a(ramp['hi'], alpha * glow * 0.5))
        cv.rect(x, y + s - 2, s, 2, _a(ramp['mid'], alpha * glow))


def skill_hotbar(cv, gv, x, y, t, slots, s=30, gap=10, alpha=1.0, labels=True):
    """slots = [dict(icon='portal', ramp=BLUE, label='开副本', unlock=t_unlock or None, key='1'), ...]。
    解锁：0–0.18 锁抖动 → 0.18 锁碎（碎片 + 光环）→ 图标从 0 弹到 1（回弹）→ 之后呼吸辉光。"""
    if alpha <= 0: return
    n = len(slots)
    for j, sl in enumerate(slots):
        sx = int(x + j * (s + gap)); sy = int(y)
        ua = None if sl.get('unlock') is None else t - sl['unlock']
        ramp = sl.get('ramp', BLUE)
        on = ua is not None and ua >= 0.18
        br = 0.6 + 0.4 * math.sin(t * 2.6 + j) if on else 0.0
        _slot_frame(cv, gv, sx, sy, s, alpha, ramp if on else None, br)
        cv.text(sx + 2, sy - 1, sl.get('key', str(j + 1)), _a(G_TOP if on else C('#7a7a90'), alpha), 'zh10', outline=_a(FRAME, alpha))
        cx, cy = sx + s // 2, sy + s // 2 + 1
        if not on:
            shake = int(round(math.sin(ua * 90) * 2)) if (ua is not None and ua >= 0) else 0
            icon(cv, None, 'lock', cx + shake + 1, cy + 1, GREY, alpha * 0.9, 2, glow=0)
        else:
            a = ua - 0.18
            sc = back_out(a / 0.3)
            if sc > 0.05:
                sub = Canvas(40, 40); sg = Canvas(40, 40)
                icon(sub, sg, sl['icon'], 20, 20, ramp, 1.0, 2, glow=0.8)
                k = max(0.1, sc)
                m = cv2.resize(sub.a, (int(40 * k), int(40 * k)), interpolation=cv2.INTER_NEAREST)
                cv.blit(m, int(cx - m.shape[1] / 2), int(cy - m.shape[0] / 2), alpha)
                mg = cv2.resize(sg.a, (int(40 * k), int(40 * k)), interpolation=cv2.INTER_NEAREST)
                gv.blit(mg, int(cx - mg.shape[1] / 2), int(cy - mg.shape[0] / 2), alpha * (0.6 + 0.4 * br))
            if a < 0.5:                                                     # lock shards + ring
                v = a / 0.5
                rng = np.random.default_rng(j + 3)
                for q in range(10):
                    ang = rng.uniform(0, 6.28); sp = rng.uniform(20, 46)
                    px_ = cx + math.cos(ang) * sp * v; py_ = cy + math.sin(ang) * sp * v + 40 * v * v
                    cv.rect(int(px_), int(py_), 2, 2, _a(GREY['hi'] if q % 2 else G_HI, alpha * (1 - v)))
                rr = s * 0.6 + 26 * v
                for d in range(0, 360, 6):
                    px_ = cx + math.cos(math.radians(d)) * rr; py_ = cy + math.sin(math.radians(d)) * rr
                    cv.px(int(px_), int(py_), _a(ramp['top'], alpha * (1 - v))); gv.px(int(px_), int(py_), _a(ramp['hi'], alpha * (1 - v)))
                if a < 0.08: gv.rect(sx - 4, sy - 4, s + 8, s + 8, _a(WHITE, alpha))
        if labels and sl.get('label'):
            la = alpha * (min(1.0, (ua - 0.25) / 0.2) if on and ua < 0.45 else (1.0 if on else 0.0))
            if la > 0:
                tw = text_width(sl['label'], 'zh10')
                cv.text(int(sx + s / 2 - tw / 2), sy + s + 3, sl['label'], _a(ramp['top'], la), 'zh10', outline=_a(FRAME, la))


# ------------------------------------------------------------------ choice panel
def _cursor(cv, x, y, alpha=1.0):
    g = ["#.....", "##....", "#w#...", "#ww#..", "#www#.", "#wwww#", "#ww###", "#w#...", "##....", "#....."]
    for yy, row in enumerate(g):
        for xx, ch in enumerate(row):
            if ch == '#': cv.px(x + xx, y + yy, _a(FRAME, alpha))
            elif ch == 'w': cv.px(x + xx, y + yy, _a(WHITE, alpha))


def choice_panel(cv, gv, x, y, w, t, q, opts, age, cursor=0, cursor_from=None, cursor_move=None, crossed=(), cross_age=None,
                 pick=None, pick_age=None, alpha=1.0):
    """q = 题目；opts = ['10 秒', ...]；age = 面板出现后的秒数。cursor 停在第几项（cursor_from + cursor_move = 移动开始的 age）。
    crossed = 被打叉的项（cross_age 开始画叉）；pick = 被选中亮起的项（pick_age 开始，金色）。"""
    if age < 0 or alpha <= 0: return
    rh = 26; hh = 30 + rh * len(opts) + 6
    k = ease_out(age / 0.25)
    H.panel(cv, gv, x, y, w, hh, k=k, alpha=alpha)
    if k < 0.8: return
    big_text(cv, gv, q, x + 12, y + 7, 1, GOLD, alpha, glow=0.4)
    keys = 'ABCD'
    rows_y = []
    for j, o in enumerate(opts):
        ra = alpha * ease_out((age - 0.15 - j * 0.08) / 0.18)
        if ra <= 0: rows_y.append(None); continue
        ry = y + 28 + j * rh; rows_y.append(ry)
        off = int(10 * (1 - ra))
        bx = x + 12 + off
        picked = pick == j and pick_age is not None and pick_age >= 0
        crossed_j = j in crossed and cross_age is not None and cross_age >= 0
        rb = GOLD if picked else (GREY if crossed_j else BLUE)
        cv.rect(bx, ry, w - 24, rh - 5, _a(INK2, ra * 0.95))
        _hline(cv, bx, ry, w - 24, _a(rb['mid'], ra)); _hline(cv, bx, ry + rh - 6, w - 24, _a(FRAME, ra))
        cv.rect(bx, ry, 18, rh - 5, _a(rb['dark'], ra)); cv.text(bx + 5, ry + 1, keys[j], _a(rb['top'], ra), 'zh12')
        tc = GREY['mid'] if crossed_j else (G_TOP if picked else C('#eae6ff'))
        cv.text(bx + 26, ry + 1, o, _a(tc, ra), 'zh12', outline=_a(FRAME, ra))
        if picked:
            pa = min(1.0, pick_age / 0.15)
            gv.rect(bx - 2, ry - 2, w - 20, rh - 1, _a(GOLD['hi'], ra * pa * (0.5 + 0.2 * math.sin(t * 8))))
            for e in range(2): cv.rect(bx - 1 - e, ry - 1 - e, w - 22 + 2 * e, 1, _a(GOLD['top'], ra * pa))
        if crossed_j:
            ck = min(1.0, cross_age / 0.25)
            tw = text_width(o, 'zh12')
            _brush(cv, gv, [(bx + 22, ry + 10), (bx + 30 + tw, ry + 9)], ck, RED['hi'], RED['mid'], ra, 2)
            cross_mark(cv, gv, bx + w - 40, ry + 10, 12, ck, RED, ra)
    # cursor
    if rows_y and all(r is not None for r in rows_y):
        cy_to = rows_y[cursor] + 6
        if cursor_from is not None and cursor_move is not None:
            mv = ease_io((age - cursor_move) / 0.35)
            cy = rows_y[cursor_from] + 6 + (cy_to - rows_y[cursor_from] - 6) * mv
        else: cy = cy_to
        bob = int(round(math.sin(t * 7) * 1.5))
        _cursor(cv, x + w - 22 + bob, int(cy), alpha)


# ------------------------------------------------------------------ cards / tags
def item_card(cv, gv, x, y, name, icon_name, ramp, age, w=66, h=66, alpha=1.0, stamp=None, stamp_age=None, sparkle=False, t=0.0):
    """道具卡：从下方 10 px 弹起；灰卡暗、金卡带辉光边。stamp = 盖在卡上的小章文字。"""
    if age < 0 or alpha <= 0: return
    k = back_out(age / 0.22)
    yy = int(y + 10 * (1 - min(1.0, k))); a = alpha * min(1.0, age / 0.1)
    x = int(x)
    cv.rect(x - 1, yy - 1, w + 2, h + 2, _a(FRAME, a))
    cv.rect(x, yy, w, h, _a(INK2, a)); cv.rect(x, yy, w, 14, _a(ramp['dark'], a * 0.8))
    _hline(cv, x, yy, w, _a(ramp['hi'], a)); _hline(cv, x, yy + h - 1, w, _a(ramp['dark'], a))
    _vline(cv, x, yy, h, _a(ramp['mid'], a)); _vline(cv, x + w - 1, yy, h, _a(ramp['dark'], a))
    if ramp is GOLD: gv.rect(x - 2, yy - 2, w + 4, h + 4, _a(GOLD['hi'], a * 0.35))
    icon(cv, gv, icon_name, x + w // 2, yy + 27, ramp, a, 3 if w >= 60 else 2, glow=0.4 if ramp is GOLD else 0.0)
    tw = text_width(name, 'zh10')
    cv.text(int(x + w / 2 - tw / 2), yy + h - 15, name, _a(ramp['top'], a), 'zh10', outline=_a(FRAME, a))
    if sparkle:
        for j in range(4):
            ph = (t * 1.1 + j * 0.25) % 1.0
            if ph < 0.4: _star(cv, gv, x + 8 + (j * 37) % (w - 12), yy + 6 + (j * 23) % 30, 2, G_TOP, a * (1 - ph / 0.4))
    if stamp and stamp_age is not None and stamp_age >= 0:
        H.slam_stamp(cv, gv, stamp, x + w // 2, yy + h // 2 - 2, stamp_age, RED, scale=1)


def hp_tag(cv, gv, cx, cy, text, ramp, age, alpha=1.0, strike=None):
    """头顶小标签（Lv.1 / 意志力差？）；strike = 划掉的进度 0..1。"""
    if age < 0: return
    k = back_out(age / 0.2); a = alpha * min(1.0, age / 0.08)
    tw = text_width(text, 'zh10'); w = tw + 10
    x = int(cx - w / 2); y = int(cy - 8 * k)
    cv.rect(x, y, w, 14, _a(INK, a * 0.9)); _hline(cv, x, y, w, _a(ramp['hi'], a)); _hline(cv, x, y + 13, w, _a(ramp['dark'], a))
    cv.text(x + 5, y - 1, text, _a(ramp['top'], a), 'zh10')
    gv.rect(x, y, w, 2, _a(ramp['hi'], a * 0.5))
    if strike is not None and strike > 0:
        _brush(cv, gv, [(x - 3, y + 8), (x + w + 3, y + 5)], strike, RED['hi'], RED['mid'], a, 2)


def error_bar(cv, gv, cx, cy, text, age, alpha=1.0, w=None):
    """红黑斜纹警示条 + 文字；前 0.25 s 故障横移。"""
    if age < 0: return
    tw = text_width(text, 'zh12'); w = w or tw + 44
    k = ease_out(age / 0.12); a = alpha * min(1.0, age / 0.05)
    x = int(cx - w / 2); y = int(cy - 11)
    gl = int(round(math.sin(age * 120) * 6)) if age < 0.25 else 0
    ww = int(w * k)
    cv.rect(x + gl, y, ww, 22, _a(C('#1a0408'), a))
    for i in range(0, ww, 8):
        for r in range(3):
            cv.rect(x + gl + i + r, y + r, 3, 1, _a(RED['mid'], a)); cv.rect(x + gl + i + r, y + 21 - r, 3, 1, _a(RED['mid'], a))
    _hline(cv, x + gl, y + 3, ww, _a(RED['hi'], a)); _hline(cv, x + gl, y + 18, ww, _a(RED['hi'], a))
    if k > 0.9:
        cv.text(x + gl + 24, y + 2, text, _a(RED['top'], a), 'zh12', outline=_a(FRAME, a))
        _tri_warn(cv, x + gl + 8, y + 5, a)
    gv.rect(x + gl, y, ww, 22, _a(RED['hi'], a * 0.35))


def _tri_warn(cv, x, y, a):
    for r in range(11):
        hw = r // 2
        cv.rect(x + 5 - hw, y + r, 2 * hw + 1, 1, _a(AMBER['hi'], a))
    cv.rect(x + 5, y + 3, 1, 4, _a(FRAME, a)); cv.px(x + 5, y + 8, _a(FRAME, a))


def status_flip(cv, gv, x, y, a_text, b_text, age, ra=GREY, rb=BLUE, alpha=1.0, dot=True):
    """状态牌：age<0 显示 a；0–0.22 竖向翻转（压扁 → 展开）；之后显示 b。"""
    use_b = age >= 0.11
    sq = 1.0 if age < 0 or age > 0.22 else abs(math.cos(age / 0.22 * math.pi))
    txt = b_text if use_b else a_text; rp = rb if use_b else ra
    tw = text_width(txt, 'zh12'); w = tw + (22 if dot else 12); h = 20
    hh = max(1, int(h * sq)); yy = int(y + (h - hh) / 2)
    cv.rect(x - 1, yy - 1, w + 2, hh + 2, _a(FRAME, alpha))
    cv.rect(x, yy, w, hh, _a(INK2, alpha)); _hline(cv, x, yy, w, _a(rp['hi'], alpha))
    if sq > 0.7:
        if dot:
            cv.rect(x + 6, y + 7, 6, 6, _a(rp['hi'], alpha)); cv.px(x + 7, y + 8, _a(WHITE, alpha))
            gv.rect(x + 5, y + 6, 8, 8, _a(rp['hi'], alpha))
        cv.text(x + (18 if dot else 6), y + 1, txt, _a(rp['top'], alpha), 'zh12')
    if use_b and age < 0.5:
        gv.rect(x - 3, y - 3, w + 6, h + 6, _a(rb['hi'], alpha * (1 - age / 0.5)))


def book_says(cv, gv, age, portrait=None, out_age=None, alpha=1.0, x=12, y=200, label='书里说'):
    """「书里说」角标：左下角滑入 0.25 s；out_age 起滑出。portrait = RGBA (≈22x22) 猫头鹰头像。"""
    if age < 0: return
    k = ease_out(age / 0.25)
    if out_age is not None and out_age >= 0: k *= 1 - ease_io(out_age / 0.25)
    if k <= 0: return
    xx = int(x - 90 * (1 - k)); a = alpha * k
    r = 13
    cx, cy = xx + r + 2, y + r + 2
    for dy in range(-r - 2, r + 3):
        for dx in range(-r - 2, r + 3):
            d = math.hypot(dx, dy)
            if d <= r: cv.px(cx + dx, cy + dy, _a(GLASS2 if dx + dy < 0 else GLASS, a))
            elif d <= r + 1: cv.px(cx + dx, cy + dy, _a(G_HI if dx + dy < 0 else G_MD, a))
            elif d <= r + 2: cv.px(cx + dx, cy + dy, _a(FRAME, a))
    if portrait is not None:
        ph, pw = portrait.shape[:2]
        sub = portrait.copy()
        yy_, xx_ = np.mgrid[0:ph, 0:pw]
        sub[((xx_ - pw / 2 + 0.5) ** 2 + (yy_ - ph / 2 + 0.5) ** 2) > (r - 0.5) ** 2] = 0
        cv.blit(sub, cx - pw // 2, cy - ph // 2, a)
    tw = text_width(label, 'zh12')
    bx = cx + r + 4
    cv.rect(bx, cy - 10, tw + 22, 20, _a(INK, a * 0.92)); _hline(cv, bx, cy - 10, tw + 22, _a(G_HI, a)); _hline(cv, bx, cy + 9, tw + 22, _a(G_DK, a))
    for q in range(2):                                                      # quote marks “
        cv.rect(bx + 4 + q * 4, cy - 6, 3, 3, _a(G_TOP, a)); cv.px(bx + 5 + q * 4, cy - 3, _a(G_TOP, a))
    cv.text(bx + 14, cy - 9, label, _a(G_TOP, a), 'zh12')
    gv.rect(cx - r, cy - r, 2 * r, 2 * r, _a(G_HI, a * 0.25))


def input_card(cv, gv, x, y, w, label, value, t, unit='分钟', alpha=1.0, age=1.0):
    if age < 0: return
    k = ease_out(age / 0.25); a = alpha * k
    H.panel(cv, gv, x, y, w, 52, k=k, alpha=alpha)
    if k < 0.8: return
    cv.text(x + 12, y + 6, label, _a(G_TOP, a), 'zh12', outline=_a(FRAME, a))
    fx, fy, fw = x + 12, y + 26, w - 24 - text_width(unit, 'zh12') - 8
    cv.rect(fx, fy, fw, 18, _a(C('#05040c'), a)); _hline(cv, fx, fy + 17, fw, _a(BLUE['hi'], a)); gv.rect(fx, fy + 16, fw, 2, _a(BLUE['hi'], a * 0.6))
    xx = fx + 6
    if value:
        big_text(cv, gv, value, xx, fy + 1, 1, GOLD, a, glow=0.5); xx += text_width(value, 'zh12')
    if int(t * 2.4) % 2 == 0: cv.rect(xx + 1, fy + 3, 2, 12, _a(WHITE, a))
    cv.text(fx + fw + 6, fy + 1, unit, _a(C('#d8d4ee'), a), 'zh12')


def boss_bar(cv, gv, x, y, w, name, lv, hp, t, age, alpha=1.0, ramp=RED):
    """Boss 血条：0–0.15 从上方砸下；名字 + Lv；血量 hp 0..1。"""
    if age < 0: return
    k = back_out(age / 0.18); a = alpha * min(1.0, age / 0.08)
    yy = int(y - 30 * (1 - min(1.0, k)))
    x = int(x)
    cv.rect(x - 4, yy - 18, w + 8, 34, _a(FRAME, a * 0.92))
    _hline(cv, x - 3, yy - 17, w + 6, _a(ramp['mid'], a)); _hline(cv, x - 3, yy + 15, w + 6, _a(ramp['dark'], a))
    nm = f'{name}'
    cv.text(x, yy - 18, nm, _a(ramp['top'], a), 'zh12', outline=_a(FRAME, a))
    lvs = f'Lv.{lv}'
    big_text(cv, gv, lvs, x + w - text_width(lvs, 'zh12') * 1, yy - 18, 1, ramp, a, glow=0.6)
    cv.rect(x, yy + 2, w, 9, _a(C('#22060c'), a))
    wf = int(w * max(0.0, min(1.0, hp)))
    rows = [ramp['top'], ramp['hi'], ramp['mid'], ramp['mid'], ramp['mid'], ramp['mid'], ramp['dark'], ramp['dark'], ramp['dark']]
    for r in range(9): cv.rect(x, yy + 2 + r, wf, 1, _a(rows[r], a))
    for i in range(1, 20): cv.rect(x + int(w * i / 20), yy + 2, 1, 9, _a(FRAME, a * 0.6))
    gv.rect(x, yy + 3, wf, 7, _a(ramp['hi'], a * 0.6))
    if age < 0.2: gv.rect(x - 6, yy - 20, w + 12, 38, _a(ramp['top'], a * (1 - age / 0.2)))


# ------------------------------------------------------------------ time
def time_axis(cv, gv, x, y, w, h0=7, h1=22, alpha=1.0, labels=(7, 12, 18, 22)):
    cv.rect(x, y, w, 1, _a(C('#8a86a8'), alpha))
    for hr in range(h0, h1 + 1):
        tx = x + int(w * (hr - h0) / (h1 - h0))
        cv.rect(tx, y - (2 if hr in labels else 1), 1, 3 if hr in labels else 2, _a(C('#8a86a8'), alpha))
        if hr in labels:
            s = f'{hr:02d}:00'; tw = text_width(s, 'zh10')
            cv.text(tx - tw // 2, y + 2, s, _a(C('#b8b4d8'), alpha), 'zh10', outline=_a(FRAME, alpha))


def time_block(cv, gv, x, y, w, h, kind, t, alpha=1.0, seed=0):
    """kind 'gold'（大招，带流光、辉光）/ 'grey'（普攻）/ 'blue'。"""
    if w < 1 or alpha <= 0: return
    x, y, w = int(round(x)), int(round(y)), int(round(w))
    ramp = GOLD if kind == 'gold' else (BLUE if kind == 'blue' else GREY)
    cv.rect(x, y, w, h, _a(FRAME, alpha))
    if w > 2:
        rows = [ramp['top'], ramp['hi']] + [ramp['mid']] * max(0, h - 4) + [ramp['dark']]
        for r in range(1, h - 1): cv.rect(x + 1, y + r, w - 2, 1, _a(rows[min(r - 1, len(rows) - 1)], alpha))
    if kind != 'grey' and w > 4:
        span = w + 30; pos = (t * 40 + seed * 17) % span - 15
        for r in range(1, h - 1):
            for d in range(4):
                xx = int(pos + d - r * 0.5)
                if 1 <= xx < w - 1: cv.px(x + xx, y + r, _a(ramp['top'], alpha * (0.35 if d in (0, 3) else 0.7)))
        rng = np.random.default_rng(seed * 31 + int(t * 8))
        for _ in range(max(1, w // 18)):
            cv.px(x + int(rng.integers(1, w - 1)), y + int(rng.integers(2, h - 2)), _a(WHITE, alpha * 0.8))
        gv.rect(x, y, w, h, _a(ramp['hi'], alpha * 0.45))


def clock_ring(cv, gv, cx, cy, r, eaten, t, n=24, ramp=BLUE, alpha=1.0, label=None, bite_age=None, th=7):
    """24 段圆环（实心像素环，段间 1 px 缝）：eaten 0..n（小数 = 正在被咬的那段按比例缺）；被吃掉的段只剩暗槽，缺口边缘红色牙印。
    bite_age = 最近一口的年龄（白 / 红闪）。"""
    cx, cy = int(cx), int(cy)
    R0, R1 = r - th / 2, r + th / 2
    for dy in range(-int(R1) - 2, int(R1) + 3):
        for dx in range(-int(R1) - 2, int(R1) + 3):
            d = math.hypot(dx + 0.5, dy + 0.5)
            if d < R0 - 1 or d > R1 + 1: continue
            ang = (math.atan2(dx + 0.5, -(dy + 0.5))) % (2 * math.pi)
            f = ang / (2 * math.pi) * n; i = int(f); fr = f - i
            x, y = cx + dx, cy + dy
            if d < R0 or d > R1:
                cv.px(x, y, _a(FRAME, alpha)); continue
            if fr < 0.06:
                cv.px(x, y, _a(FRAME, alpha)); continue
            gone = i < int(eaten) or (i == int(eaten) and fr > 1 - (eaten - int(eaten)))
            if gone:
                edge = (i == int(eaten) - 1 and fr > 0.8) or (i == int(eaten) and abs(fr - (1 - (eaten - int(eaten)))) < 0.12)
                cv.px(x, y, _a(RED['mid'] if edge and (dx + dy) % 2 == 0 else C('#171931'), alpha))
            else:
                u = (d - R0) / max(1, R1 - R0)
                c = ramp['top'] if u > 0.8 else (ramp['hi'] if u > 0.5 else (ramp['mid'] if u > 0.2 else ramp['dark']))
                cv.px(x, y, _a(c, alpha))
                if 0.3 < u < 0.7: gv.px(x, y, _a(ramp['hi'], alpha * 0.7))
    if bite_age is not None and bite_age < 0.3 and eaten > 0:
        am = (int(math.ceil(eaten)) - 0.5) / n * 2 * math.pi
        bx, by = cx + math.sin(am) * r, cy - math.cos(am) * r
        k = 1 - bite_age / 0.3
        gv.rect(int(bx) - 5, int(by) - 5, 11, 11, _a(RED['top'], alpha * k)); cv.rect(int(bx) - 1, int(by) - 1, 3, 3, _a(WHITE, alpha * k))
    if label:
        tw = text_width(label, 'zh12') * 2
        big_text(cv, gv, label, int(cx - tw / 2), int(cy - 17), 2, ramp if eaten < n else RED, alpha, glow=0.5)


def clock_face(cv, gv, cx, cy, r, hand_ang, sectors=(), alpha=1.0, t=0.0):
    """钟面：sectors = [(a0, a1, ramp, k)] 角度（弧度，0 = 12 点方向顺时针）。hand_ang 同一约定。"""
    for dy in range(-r - 3, r + 4):
        for dx in range(-r - 3, r + 4):
            d = math.hypot(dx, dy)
            x, y = int(cx + dx), int(cy + dy)
            if d <= r:
                ang = (math.atan2(dx, -dy)) % (2 * math.pi)
                col = C('#0d0f22')
                for a0, a1, rp, k in sectors:
                    if a0 <= ang <= a1 and d <= r - 2:
                        col = _mix(C('#0d0f22'), rp['mid'] if d < r * 0.7 else rp['hi'], k); gv.px(x, y, _a(rp['hi'], alpha * k * 0.5))
                cv.px(x, y, _a(col, alpha))
            elif d <= r + 1.2: cv.px(x, y, _a(G_HI if dx + dy < 0 else G_MD, alpha))
            elif d <= r + 2.5: cv.px(x, y, _a(FRAME, alpha))
    for i in range(12):
        a = i / 12 * 2 * math.pi
        L = 4 if i % 3 == 0 else 2
        for s in range(L):
            cv.px(int(cx + math.sin(a) * (r - 2 - s)), int(cy - math.cos(a) * (r - 2 - s)), _a(G_TOP if i % 3 == 0 else C('#8a86a8'), alpha))
    for s in range(int(r * 0.8)):
        cv.rect(int(cx + math.sin(hand_ang) * s), int(cy - math.cos(hand_ang) * s), 2, 2, _a(WHITE, alpha))
    cv.rect(int(cx) - 1, int(cy) - 1, 3, 3, _a(G_TOP, alpha))


def density_meter(cv, gv, x, y, h, k, t, alpha=1.0, label='信息密度', cells=14, w=14):
    """竖向表：k 0..1；格子绿 → 黄 → 红；顶格时红闪。"""
    x, y = int(x), int(y)
    ch = (h - 4) / cells
    cv.rect(x - 3, y - 3, w + 6, h + 6, _a(FRAME, alpha * 0.92))
    _vline(cv, x - 2, y - 2, h + 4, _a(G_MD, alpha)); _vline(cv, x + w + 1, y - 2, h + 4, _a(G_DK, alpha))
    _hline(cv, x - 2, y - 2, w + 4, _a(G_HI, alpha)); _hline(cv, x - 2, y + h + 1, w + 4, _a(G_DK, alpha))
    lit = k * cells
    hot = k > 0.95 and int(t * 10) % 2 == 0
    for i in range(cells):
        u = i / (cells - 1)
        rp = GREEN if u < 0.45 else (AMBER if u < 0.75 else RED)
        cy = int(y + h - 2 - (i + 1) * ch)
        on = i < lit
        cv.rect(x + 1, cy + 1, w - 2, max(1, int(ch) - 1), _a(rp['mid'] if on else C('#14162a'), alpha))
        if on:
            cv.rect(x + 1, cy + 1, w - 2, 1, _a(rp['top'] if not hot else WHITE, alpha))
            gv.rect(x, cy, w, int(ch), _a(rp['hi'], alpha * (0.6 if hot else 0.35)))
    if label:
        for j, chr_ in enumerate(label):                                      # vertical label
            cv.text(x + w + 6, y + j * 14, chr_, _a(C('#d8d4ee'), alpha), 'zh10', outline=_a(FRAME, alpha))


def quest_list(cv, gv, x, y, w, title, rows, t, age=1.0, alpha=1.0, ramp=GOLD):
    """任务卡：rows = [(text, done_at)]；done_at 之后画勾 + 文字变亮 + 闪一下。"""
    if age < 0: return
    rh = 22; hh = 30 + rh * len(rows) + 4
    k = ease_out(age / 0.3)
    H.panel(cv, gv, x, y, w, hh, k=k, alpha=alpha)
    if k < 0.85: return
    big_text(cv, gv, title, x + 12, y + 6, 1, ramp, alpha, glow=0.5)
    icon(cv, gv, 'gift', x + w - 18, y + 13, GOLD, alpha, 1)
    for j, (txt, done) in enumerate(rows):
        ra = alpha * ease_out((age - 0.25 - j * 0.1) / 0.2)
        if ra <= 0: continue
        ry = y + 30 + j * rh
        bx = x + 14
        cv.rect(bx, ry + 2, 14, 14, _a(FRAME, ra)); cv.rect(bx + 1, ry + 3, 12, 12, _a(GLASS, ra)); _hline(cv, bx + 1, ry + 3, 12, _a(GLASS2, ra))
        da = None if done is None else t - done
        col = C('#c8c4e0')
        if da is not None and da >= 0:
            check_mark(cv, gv, bx + 7, ry + 9, 12, min(1.0, da / 0.2), ramp, ra, 2)
            col = ramp['top']
            if da < 0.3: gv.rect(bx - 4, ry - 2, w - 24, rh, _a(ramp['hi'], ra * (1 - da / 0.3)))
        cv.text(bx + 22, ry, txt, _a(col, ra), 'zh12', outline=_a(FRAME, ra))


def calendar(cv, gv, x, y, cols, rows, cell, t, marks=None, bars=None, today=None, alpha=1.0, head=True, start_dow=0):
    """月历格：marks = {day_index: k}（金叉进度 0..1）；bars = {day_index: (len 0..1, k)} 格子底部的小读条。"""
    x, y = int(x), int(y)
    W, Hh = cols * cell, rows * cell
    if head:
        cv.rect(x - 2, y - 16, W + 4, 15, _a(C('#3a1820'), alpha)); _hline(cv, x - 2, y - 16, W + 4, _a(RED['mid'], alpha))
        for j, d in enumerate('一二三四五六日'[:cols]):
            cv.text(x + j * cell + cell // 2 - 5, y - 17, d, _a(C('#f0e6ee'), alpha), 'zh10')
    cv.rect(x - 2, y - 1, W + 4, Hh + 3, _a(C('#efe6d4'), alpha))
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            cx, cy = x + c * cell, y + r * cell
            cv.rect(cx, cy, cell - 1, cell - 1, _a(C('#fbf4e4') if (i + r) % 2 else C('#f6eedc'), alpha))
            cv.text(cx + 2, cy - 1, str(i + 1), _a(C('#8a7a6a'), alpha), 'zh10')
            if today == i:
                for e in range(2): cv.rect(cx - e, cy - e, cell - 1 + 2 * e, 1, _a(BLUE['mid'], alpha)); cv.rect(cx - e, cy + cell - 2 + e, cell - 1 + 2 * e, 1, _a(BLUE['mid'], alpha))
            if bars and i in bars:
                ln, k = bars[i]
                bw = int((cell - 6) * ln * k)
                cv.rect(cx + 3, cy + cell - 6, cell - 6, 3, _a(C('#2a2c44'), alpha))
                if bw > 0: cv.rect(cx + 3, cy + cell - 6, bw, 3, _a(BLUE['hi'], alpha)); gv.rect(cx + 3, cy + cell - 6, bw, 3, _a(BLUE['hi'], alpha * 0.6))
            if marks and i in marks and marks[i] > 0:
                stroke_x(cv, gv, cx + cell / 2, cy + cell / 2 - 2, cell * 0.62, marks[i], GOLD, alpha, width=max(2, cell // 9), seed=i)
