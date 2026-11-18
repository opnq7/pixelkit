"""pixelkit.gameui - 「副本 / 游戏化叙事」UI 组件（v0.13，《熬夜副本》沉淀）。

全部画在 480x270 的 UI 画布上（ui.UICanvas()，输出时整倍 x4），像素字体。

    subtitle(cv, text, hl=('熬夜',), alpha)          底部字幕，关键词金色高亮，深色描边 + 投影
    sub_chunks(text, t0, t1)                       把一句旁白按标点切成短句，按字数分配时长
    revive_hud(cv, pct, stage, total, k, flash)    右上角：复活进度条 + 副本 n/total
    year_tag(cv, year, place, k, flash)            左上角：年份 + 地点（翻页闪光）
    pixel_word(cv, s, cx, cy, scale, col, ...)     像素大字（Press Start 2P 放大），砸下 / 挤压
    cause_panel(cv, t, t0, rows)                   「死因：熬夜」逐字结算面板
    quest_panel(cv, x, y, k, title, rows)          金边 JRPG 任务面板（返回按钮区）
    game_button(cv, x, y, w, h, label, ...)        游戏按钮（idle / hover / pressed / grey）
    ecg_strip(cv, x, y, w, h, t, beats, flat_t)    心电监护条（逐拍、拉直线）
    char_card(cv, t, t0, name, lv, skill, ...)     角色登场卡（名字 + Lv + 技能），魂穿后弹出
    sanity_bar(cv, x, y, v, label)                 理智值血条（绿 → 黄 → 红，低血量闪）
    choice_panel(cv, t, t0, q, opts, pick, ...)    选择题弹窗（A / B + 倒计时 + 选中高亮）
    danmaku(cv, t, t0, text, y, speed)             横飘弹幕
    signal_lost(cv, k)                             「信号中断」黑屏小字
    big_stamp_text(...)                            大号描边字（关卡名、发现）
"""
import math
import numpy as np
from .core import C, mix, text_width, text_mask
from .ui import (_a, NAVY, NAVY2, GOLD, GOLD_D, CREAM, OUTL, ease_out, burst_lines, star, UICanvas)
from .anim import back_out, clamp01

UW, UH = 480, 270
HL = C('#ffd34a'); SUB_INK = C('#fff6e6'); SUB_OUT = C('#120c1c'); RED = C('#ff4a3c'); GREEN = C('#5fd07a')

# ---------------------------------------------------------------- subtitles
_PUNCT = '，。：；？！、…—'

def sub_chunks(text, t0, t1, max_len=19):
    """split a narration line at punctuation into display chunks with times ∝ characters."""
    parts, cur = [], ''
    for ch in text:
        cur += ch
        if ch in '，。：；？！' and len(cur.strip()) >= 4:
            parts.append(cur); cur = ''
    if cur.strip(): parts.append(cur)
    merged = []
    for p in parts:
        if merged and len(merged[-1]) + len(p) <= max_len and len(p) < 7: merged[-1] += p
        else: merged.append(p)
    out = []
    n = sum(len(p) for p in merged); acc = 0
    for p in merged:
        a = t0 + (t1 - t0) * acc / n; acc += len(p); b = t0 + (t1 - t0) * acc / n
        s = p.strip().rstrip('，。；、')
        out.append((a, b, s))
    return out

def subtitle(cv, text, hl=(), alpha=1.0, y=232, fname='zh12', pop=1.0, W=UW):
    """centred bottom subtitle; words in hl drawn in gold.  pop 0..1 = tiny rise-in."""
    if not text or alpha <= 0: return
    # segment into (string, colour)
    segs = [(text, SUB_INK)]
    for w in sorted(hl, key=len, reverse=True):
        nxt = []
        for s, c in segs:
            if c is not SUB_INK or w not in s: nxt.append((s, c)); continue
            parts = s.split(w)
            for i, p in enumerate(parts):
                if p: nxt.append((p, SUB_INK))
                if i < len(parts) - 1: nxt.append((w, HL))
        segs = nxt
    tw = sum(text_width(s, fname) for s, _ in segs)
    x = int(round(W / 2 - tw / 2)); yy = int(round(y + 3 * (1 - pop)))
    a = alpha * min(1.0, pop * 1.6)
    for s, c in segs:
        # soft drop shadow, then 1px outline, then fill
        cv.text(x + 1, yy + 2, s, (0, 0, 0, int(120 * a)), fname)
        cv.text(x, yy, s, _a(c, a), fname, outline=_a(SUB_OUT, a))
        x += text_width(s, fname)

# ---------------------------------------------------------------- HUDs
def _panel(cv, x, y, w, h, alpha=1.0, accent=GOLD_D):
    cv.rect(x + 1, y + 2, w, h, (0, 0, 0, int(90 * alpha)))
    cv.rect(x, y, w, h, (NAVY[0], NAVY[1], NAVY[2], int(225 * alpha)))
    cv.hline(x, y, w, _a(NAVY2, alpha)); cv.hline(x, y + h - 1, w, _a(accent, alpha))
    cv.vline(x, y, h, _a(NAVY2, alpha)); cv.vline(x + w - 1, y, h, _a(accent, alpha))

def revive_hud(cv, pct, stage=0, total=5, k=1.0, flash=0.0, x_right=472, y=8, alpha=1.0):
    """复活进度 bar (pct 0..100) + 副本 n/total.  k: slide-in 0..1; flash: gold flash on gain."""
    if k <= 0 or alpha <= 0: return
    w, h = 118, 26
    x = int(round(x_right - w + (1 - back_out(clamp01(k), 1.6)) * (w + 16)))
    _panel(cv, x, y, w, h, alpha)
    cv.text(x + 5, y + 3, '复活进度', _a(CREAM, alpha), 'zh8')
    cv.text(x + 44, y + 4, f'{int(round(pct))}%', _a(mix(C('#7fe0ff'), C('#ffffff'), flash), alpha), 'silkb')
    st = f'副本 {stage}/{total}'
    cv.text(x + w - 5 - text_width(st, 'zh8'), y + 3, st, _a(GOLD, alpha), 'zh8')
    bx, by, bw, bh = x + 5, y + 15, w - 10, 6
    cv.rect(bx, by, bw, bh, _a(C('#0b0a16'), alpha))
    fw = int(round((bw - 2) * clamp01(pct / 100.0)))
    if fw > 0:
        col = mix(C('#7fe0ff'), C('#ffffff'), flash)
        cv.rect(bx + 1, by + 1, fw, bh - 2, _a(col, alpha))
        cv.hline(bx + 1, by + 1, fw, _a(C('#d8f8ff'), alpha))
    for i in range(1, total):                                    # stage ticks
        tx = bx + 1 + int((bw - 2) * i / total)
        cv.vline(tx, by + 1, bh - 2, _a(NAVY2, alpha))
    cv.text(bx + bw - 22, by - 1 if False else y + 3, '', CREAM)
    if flash > 0:
        burst_lines(cv, bx + 1 + fw, by + 3, 4 + 8 * flash, 8 + 12 * flash, 8, GOLD, alpha * flash)

def year_tag(cv, year, place='', k=1.0, flash=0.0, x=8, y=8, alpha=1.0):
    """big year + small place, slides in from the left."""
    if k <= 0 or alpha <= 0: return
    w = max(70, text_width(place, 'zh8') + 16) if place else 70
    xx = int(round(x - (1 - back_out(clamp01(k), 1.6)) * (w + 16)))
    _panel(cv, xx, y, w, 30 if place else 22, alpha)
    col = mix(GOLD, C('#ffffff'), flash)
    cv.text(xx + 6, y + 5, str(year), _a(col, alpha), 'p2p', shadow=(0, 0, 0, int(255 * alpha)))
    if place: cv.text(xx + 6, y + 18, place, _a(CREAM, alpha), 'zh8')

def pixel_word(cv, s, cx, cy, scale=4, col=C('#ff3b3b'), shade=C('#7a0a1a'), hi=C('#ffb0a0'), sy=1.0, alpha=1.0,
               fname='p2p', depth=2):
    """chunky title from a pixel font scaled up (nearest): face colour + top highlight row + extruded shade."""
    m = text_mask(s, fname)
    if m is None or not m.any(): return
    ys, xs = np.nonzero(m); m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = m.shape
    sx_ = scale; sy_ = max(1, int(round(scale * sy)))
    big = np.repeat(np.repeat(m, sy_, 0), sx_, 1)
    H, W = big.shape
    x0, y0 = int(round(cx - W / 2)), int(round(cy - H / 2))
    rows_hi = np.zeros_like(big); rows_hi[:sy_ * 1] = True
    for d in range(depth, 0, -1):
        _blit_mask(cv, big, x0 + d, y0 + d, _a(shade, alpha))
    _blit_mask(cv, big, x0, y0, _a(col, alpha))
    top = big & ~np.roll(big, sy_, 0)
    _blit_mask(cv, top, x0, y0, _a(hi, alpha))

def _blit_mask(cv, m, x, y, col):
    H, W = m.shape
    x0, y0, x1, y1 = max(0, x), max(0, y), min(cv.a.shape[1], x + W), min(cv.a.shape[0], y + H)
    if x1 <= x0 or y1 <= y0: return
    sub = m[y0 - y:y1 - y, x0 - x:x1 - x]
    reg = cv.a[y0:y1, x0:x1]
    a = col[3] / 255.0
    if a >= 0.999: reg[sub] = col
    else:
        reg[sub, :3] = (reg[sub, :3] * (1 - a) + np.array(col[:3]) * a).astype(np.uint8)
        reg[sub, 3] = np.maximum(reg[sub, 3], col[3])

def cause_panel(cv, t, t0, rows, x=None, y=150, cps=14.0, alpha=1.0):
    """settlement rows typed in: rows = [(label, value, value_col, big)]; returns end time of typing."""
    tt = t - t0
    if tt < 0 or alpha <= 0: return
    yy = y
    acc = 0.0
    for label, value, vcol, big in rows:
        n_l, n_v = len(label), len(value)
        k_l = clamp01((tt - acc) * cps / max(1, n_l)); acc += n_l / cps
        k_v = clamp01((tt - acc) * cps / max(1, n_v)); acc += n_v / cps + 0.25
        fnv = 'zh12' if big else 'zh10'
        wl = text_width(label, 'zh10'); wv = text_width(value, fnv)
        xx = int(UW / 2 - (wl + wv) / 2) if x is None else x
        sl = label[:int(round(k_l * n_l))]; sv = value[:int(round(k_v * n_v))]
        if sl: cv.text(xx, yy + (2 if big else 0), sl, _a(C('#cfc6dc'), alpha), 'zh10', outline=_a(SUB_OUT, alpha))
        if sv:
            if big:
                pixel_word_zh(cv, sv, xx + wl, yy - 3, 2, vcol, alpha)
            else:
                cv.text(xx + wl, yy, sv, _a(vcol, alpha), fnv, outline=_a(SUB_OUT, alpha))
        yy += 24 if big else 15

def pixel_word_zh(cv, s, x, y, scale, col, alpha=1.0, fname='zh12'):
    m = text_mask(s, fname)
    if m is None: return
    big = np.repeat(np.repeat(m, scale, 0), scale, 1)
    _blit_mask(cv, big, x + scale, y + scale, _a(SUB_OUT, alpha))          # extruded shade (no inner outline:
    _blit_mask(cv, big, x, y, _a(col, alpha))                              #  dense CJK glyphs stay readable)

# ---------------------------------------------------------------- panels & buttons
def quest_panel(cv, x, y, w, h, k=1.0, title='复活任务', title_en='QUEST', rows=(), alpha=1.0, head_col=None, body_col=(24, 26, 58)):
    """gold-framed JRPG panel, drops in with k (0..1).  rows: [(icon_col, label, value)] -> returns (x, y, w, h)."""
    if k <= 0: return None
    oy = int(round((1 - back_out(clamp01(k), 1.7)) * -120))
    y = y + oy
    cv.rect(x + 3, y + 4, w, h, (0, 0, 0, int(110 * alpha)))
    cv.rect(x - 1, y - 1, w + 2, h + 2, _a(OUTL, alpha))
    cv.rect(x, y, w, h, _a(GOLD, alpha)); cv.rect(x + 1, y + 1, w - 2, h - 2, _a(GOLD_D, alpha))
    cv.rect(x + 2, y + 2, w - 4, h - 4, tuple(body_col) + (int(246 * alpha),))
    tex = tuple(min(255, c + 10) for c in body_col[:3]) + (int(255 * alpha),)
    for yy in range(y + 3, y + h - 3, 2):                         # faint woven texture
        for xx in range(x + 3 + (yy // 2) % 2 * 2, x + w - 3, 4): cv.px(xx, yy, tex)
    cv.rect(x + 2, y + 2, w - 4, 18, _a(head_col or C('#8e2b48'), alpha)); cv.hline(x + 2, y + 20, w - 4, _a(GOLD, alpha))
    for cx_, cy_ in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        cv.rect(cx_ - 2, cy_ - 2, 5, 5, _a(C('#ffe27a'), alpha)); cv.px(cx_, cy_, _a(OUTL, alpha))
    tw = text_width(title, 'zh12')
    cv.text(x + w // 2 - tw // 2 - 14, y + 4, title, _a(C('#ffe9a0'), alpha), 'zh12', shadow=_a(C('#3a0a1a'), alpha))
    cv.text(x + w // 2 + tw // 2 - 10, y + 7, title_en, _a(C('#f5c0a0'), alpha), 'silkb')
    yy = y + 27
    for icol, label, value in rows:
        cv.rect(x + 10, yy + 4, 4, 4, _a(icol, alpha)); cv.px(x + 11, yy + 4, _a(C('#ffffff'), alpha))
        cv.text(x + 18, yy + 2, label, _a(C('#c9b8ff'), alpha), 'zh10')
        cv.text(x + 18 + text_width(label, 'zh10') + 2, yy, value, _a(CREAM, alpha), 'zh12', shadow=_a(C('#000000'), alpha))
        yy += 17
    return (x, y, w, h)

def game_button(cv, x, y, w, h, label, state='idle', col=C('#3a9a5c'), alpha=1.0, fname='zh10', sy=1.0, sweat=False, t=0.0):
    """state: idle | hover | pressed | grey.  sy squash (bottom fixed)."""
    hh = max(4, int(round(h * sy))); y = y + (h - hh)
    if state == 'grey': col = C('#5a5a68')
    base = mix(col, C('#ffffff'), 0.18) if state == 'hover' else col
    dark = tuple(int(c * 0.5) for c in base[:3]) + (255,)
    py = 2 if state == 'pressed' else 0
    if state != 'pressed': cv.rect(x, y + 3, w, hh, _a(dark, alpha))
    cv.rect(x - 1, y + py - 1, w + 2, hh + 2, _a(OUTL, alpha))
    cv.rect(x, y + py, w, hh, _a(base, alpha))
    cv.hline(x + 1, y + py + 1, w - 2, _a(mix(base, C('#ffffff'), 0.35), alpha))
    tw = text_width(label, fname)
    tc = C('#a8a8b4') if state == 'grey' else CREAM
    cv.text(x + w // 2 - tw // 2, y + py + hh // 2 - (6 if fname == 'zh12' else 5), label, _a(tc, alpha), fname,
            shadow=_a(C('#000000'), alpha * 0.6))
    if state == 'grey':
        cv.hline(x + 4, y + py + hh // 2, w - 8, _a(C('#2a2a34'), alpha * 0.8))
    if sweat:
        sx, sy_ = x + w + 2, y - 4 + int(2 * math.sin(t * 20))
        cv.rect(sx, sy_, 3, 4, _a(C('#7fd0ff'), alpha)); cv.px(sx + 1, sy_ - 1, _a(C('#7fd0ff'), alpha)); cv.px(sx, sy_, _a(C('#e8f8ff'), alpha))

# ---------------------------------------------------------------- monitors
def ecg_val(t, beats):
    v = 0.0
    for b in beats:
        x = t - b
        if -0.05 < x < 0.25:
            v += (-0.22 * math.exp(-((x + 0.02) / 0.01) ** 2) + 1.0 * math.exp(-(x / 0.011) ** 2)
                  - 0.35 * math.exp(-((x - 0.028) / 0.011) ** 2) + 0.16 * math.exp(-((x - 0.14) / 0.03) ** 2))
    return v

def ecg_strip(cv, x, y, w, h, t, beats, flat_t=None, window=1.6, bpm=None, label='心率', alpha=1.0):
    dead = flat_t is not None and t >= flat_t
    col = RED if dead else C('#6dff9a')
    _panel(cv, x, y, w, h, alpha, accent=C('#2a5a40'))
    cv.text(x + 5, y + 3, label, _a(col, alpha), 'zh8')
    cv.text(x + 26, y + 4, 'BPM', _a(C('#7a8a90'), alpha), 'silk')
    val = '0' if dead else (str(bpm) if bpm is not None else '')
    if val: cv.text(x + w - 6 - text_width(val, 'p2p'), y + 3, val, _a(col, alpha), 'p2p')
    base = y + h - 8
    prev = None
    for i in range(w - 8):
        tt = t - (w - 8 - i) / (w - 8) * window
        v = ecg_val(tt, [b for b in beats if flat_t is None or b < flat_t])
        py = int(round(base - v * (h - 16)))
        px_ = x + 4 + i
        if prev is not None:
            a, b = sorted((prev, py))
            for yy in range(a, b + 1): cv.px(px_, yy, _a(col, alpha))
        cv.px(px_, py, _a(col, alpha))
        prev = py
    # sweep dot
    cv.rect(x + w - 5, prev - 1, 2, 2, _a(C('#ffffff'), alpha))

def sanity_bar(cv, x, y, v, label='理智值', w=120, alpha=1.0, t=0.0, k=1.0):
    if k <= 0: return
    xx = int(round(x + (1 - back_out(clamp01(k), 1.6)) * (w + 20)))
    _panel(cv, xx, y, w, 24, alpha)
    cv.text(xx + 5, y + 2, label, _a(CREAM, alpha), 'zh8'); cv.text(xx + 40, y + 3, 'SAN', _a(GOLD, alpha), 'silkb')
    vv = int(round(v)); s = str(vv)
    col = GREEN if v > 60 else (C('#ffd34a') if v > 25 else RED)
    blink = v <= 25 and (int(t * 6) % 2 == 0)
    cv.text(xx + w - 6 - text_width(s, 'silkb'), y + 3, s, _a(C('#ffffff') if blink else col, alpha), 'silkb')
    bx, by, bw = xx + 5, y + 14, w - 10
    cv.rect(bx, by, bw, 6, _a(C('#0b0a16'), alpha))
    fw = int(round((bw - 2) * clamp01(v / 100)))
    if fw > 0:
        cv.rect(bx + 1, by + 1, fw, 4, _a(col, alpha)); cv.hline(bx + 1, by + 1, fw, _a(mix(col, C('#ffffff'), 0.4), alpha))

def char_card(cv, t, t0, name, lv='', skill='', role='', x=12, y=186, life=3.4, alpha=1.0, accent=GOLD):
    """character card after a possession: slides in from the left, name + Lv chip + skill line, folds away."""
    age = t - t0
    if age < 0 or age > life: return
    k = back_out(clamp01(age / 0.30), 1.6) * (1 - clamp01((age - life + 0.25) / 0.25))
    w = max(text_width(name, 'zh12') + text_width(lv, 'silkb') + 30, text_width(skill, 'zh10') + 52, text_width(role, 'zh8') + 20, 120)
    h = 44
    xx = int(round(x - (1 - k) * (w + 24)))
    _panel(cv, xx, y, w, h, alpha, accent=accent)
    cv.rect(xx, y, 3, h, _a(accent, alpha))
    cv.text(xx + 9, y + 4, name, _a(CREAM, alpha), 'zh12', shadow=_a(C('#000000'), alpha))
    if lv:
        lx = xx + 13 + text_width(name, 'zh12')
        cv.rect(lx, y + 6, text_width(lv, 'silkb') + 6, 11, _a(accent, alpha))
        cv.text(lx + 3, y + 7, lv, _a(NAVY, alpha), 'silkb')
    if role: cv.text(xx + 9, y + 19, role, _a(C('#bfb2e8'), alpha), 'zh8')
    if skill:
        cv.text(xx + 9, y + 30, '技能', _a(GOLD, alpha), 'zh10')
        cv.text(xx + 34, y + 30, skill, _a(C('#ffd0b0'), alpha), 'zh10')
    if age < 0.5:
        sx = xx + int(age / 0.5 * (w + 20)) - 10
        for i in range(h):
            if xx < sx - i // 3 < xx + w: cv.px(sx - i // 3, y + i, (255, 245, 210, int(110 * alpha)))

def choice_panel(cv, t, t0, q, opts=('满血复活', '彻底废了'), pick=None, t_pick=None, countdown=None, y=72, alpha=1.0):
    age = t - t0
    if age < 0: return
    k = back_out(clamp01(age / 0.28), 1.8)
    w, h = 250, 96
    x = UW // 2 - w // 2
    yy = int(round(y + (1 - k) * 30)); a = alpha * clamp01(age / 0.15)
    quest_panel(cv, x, yy, w, h, 1.0, '选择题', 'QUIZ', (), a)
    tw = text_width(q, 'zh12')
    cv.text(UW // 2 - tw // 2, yy + 26, q, _a(CREAM, a), 'zh12', shadow=_a(C('#000000'), a))
    for i, o in enumerate(opts):
        bx = x + 14 + i * 116; by = yy + 50
        st = 'idle'
        if pick is not None and t_pick is not None and t >= t_pick:
            st = 'hover' if i == pick else 'grey'
        col = C('#3a9a5c') if i == 0 else C('#b04050')
        game_button(cv, bx, by, 106, 22, ('A  ' if i == 0 else 'B  ') + o, st, col, a, 'zh10')
        if st == 'hover' and t - t_pick < 0.4:
            burst_lines(cv, bx + 53, by + 11, 30 + 60 * (t - t_pick), 40 + 80 * (t - t_pick), 12, GOLD, a * (1 - (t - t_pick) / 0.4))
    if countdown is not None and (pick is None or t < t_pick):
        s = str(countdown)
        cv.text(x + w - 22, yy + 78, s, _a(GOLD, a), 'p2p')

def danmaku(cv, t, t0, text, y=60, speed=95.0, col=C('#ffffff'), alpha=1.0, fname='zh12'):
    age = t - t0
    if age < 0: return
    w = text_width(text, fname)
    x = int(round(UW + 4 - age * speed))
    if x + w < 0: return
    cv.text(x + 1, y + 1, text, (0, 0, 0, int(140 * alpha)), fname)
    cv.text(x, y, text, _a(col, alpha), fname, outline=_a(C('#1a1020'), alpha * 0.8))

def signal_lost(cv, k=1.0, text='信号中断', t=0.0):
    if k <= 0: return
    cv.rect(0, 0, UW, UH, (0, 0, 0, int(255 * k)))
    tw = text_width(text, 'zh10')
    if int(t * 3) % 2 == 0:
        cv.text(UW // 2 - tw // 2, UH // 2 - 5, text, (150, 150, 160, int(255 * k)), 'zh10')
    cv.text(UW // 2 - 18, UH // 2 + 8, 'NO SIGNAL', (90, 90, 100, int(255 * k)), 'silk')

def big_text(cv, s, cx, cy, scale=2, col=C('#ffe27a'), alpha=1.0, fname='zh12'):
    tw = text_width(s, fname) * scale
    pixel_word_zh(cv, s, int(round(cx - tw / 2)), int(round(cy - 6 * scale)), scale, col, alpha, fname)


# ================================================================ v0.13b · 开场「玩家状态 / 任务 / 结算」组件
def battery_icon(cv, x, y, pct, w=22, h=10, charging=False, alpha=1.0, t=0.0, blink_low=True):
    """battery glyph: body + nub + fill (green > 50, yellow > 20, red), bolt when charging, empty one blinks."""
    col = GREEN if pct > 50 else (C('#ffd34a') if pct > 20 else RED)
    cv.rect(x - 1, y - 1, w + 2, h + 2, _a(OUTL, alpha))
    cv.rect(x, y, w, h, _a(C('#e8e4f0'), alpha)); cv.rect(x + 1, y + 1, w - 2, h - 2, _a(C('#14121e'), alpha))
    cv.rect(x + w + 1, y + h // 2 - 2, 2, 4, _a(C('#e8e4f0'), alpha))
    fw = int(round((w - 4) * clamp01(pct / 100)))
    if fw > 0:
        cv.rect(x + 2, y + 2, fw, h - 4, _a(col, alpha)); cv.hline(x + 2, y + 2, fw, _a(mix(col, C('#ffffff'), 0.45), alpha))
    elif blink_low and int(t * 4) % 2 == 0:
        cv.rect(x + 1, y + 1, w - 2, h - 2, _a(C('#5a0a12'), alpha))
    if charging:
        bx, by = x + w // 2, y + 1
        for (dx, dy) in ((1, 0), (0, 1), (-1, 2), (0, 3), (1, 3), (2, 3), (1, 4), (0, 5), (-1, 6)):
            cv.px(bx + dx, by + dy, _a(C('#ffe24a'), alpha))

def player_hud(cv, x, y, t, hp=1.0, bpm=72, beats=(), flat_t=None, portrait=None, name='你', lv='LV.25', title='夜猫子',
               k=1.0, alpha=1.0, hit=0.0, dead=False):
    """game status bar (top-left): portrait + name/Lv + 精力 segmented bar + heart rate with a live mini-ECG.
    portrait: rgba (<=36x36) drawn in the frame.  hit 0..1 = red damage flash.  dead -> portrait X, bars empty, ECG flat."""
    if k <= 0 or alpha <= 0: return
    w, h = 176, 46
    xx = int(round(x - (1 - back_out(clamp01(k), 1.6)) * (w + 20)))
    _panel(cv, xx, y, w, h, alpha, accent=GOLD_D)
    cv.rect(xx, y, 3, h, _a(RED if dead else GOLD, alpha))
    # portrait frame
    px, py = xx + 6, y + 4
    cv.rect(px - 1, py - 1, 40, 40, _a(GOLD, alpha)); cv.rect(px, py, 38, 38, _a(C('#1a1830'), alpha))
    if portrait is not None:
        ph, pw = portrait.shape[:2]
        ox, oy = px + 19 - pw // 2, py + 38 - ph
        sub = portrait[max(0, py - oy):, :]
        oy = max(oy, py)
        hh = min(sub.shape[0], py + 38 - oy)
        reg = cv.a[oy:oy + hh, ox:ox + pw]
        s2 = sub[:hh, :reg.shape[1]]
        m = s2[..., 3] > 0
        reg[m] = s2[m] if not dead else (np.array(s2[m], np.float32) * [0.5, 0.5, 0.55, 1]).astype(np.uint8)
    if dead:
        for d in range(-8, 9):
            for (cx_, cy_) in ((px + 13, py + 17), (px + 25, py + 17)):
                pass
        cv.line(px + 6, py + 6, px + 32, py + 32, _a(RED, alpha)); cv.line(px + 32, py + 6, px + 6, py + 32, _a(RED, alpha))
        cv.line(px + 7, py + 6, px + 33, py + 32, _a(RED, alpha)); cv.line(px + 33, py + 6, px + 7, py + 32, _a(RED, alpha))
    if hit > 0:
        cv.rect(px, py, 38, 38, (255, 40, 40, int(150 * hit * alpha)))
    # name + level chip + title
    tx = xx + 50
    cv.text(tx, y + 3, name, _a(CREAM, alpha), 'zh10', shadow=_a(C('#000000'), alpha))
    lx = tx + text_width(name, 'zh10') + 4
    cv.rect(lx, y + 4, text_width(lv, 'silk') + 6, 11, _a(GOLD, alpha)); cv.text(lx + 3, y + 5, lv, _a(C('#2a1406'), alpha), 'silk')
    cv.text(lx + text_width(lv, 'silk') + 10, y + 4, title, _a(C('#bfb2e8'), alpha), 'zh8')
    # 精力 bar (10 segments)
    by = y + 18
    cv.text(tx, by - 1, '精力', _a(GOLD, alpha), 'zh8')
    col = GREEN if hp > 0.5 else (C('#ffd34a') if hp > 0.22 else RED)
    blink = hp <= 0.22 and int(t * 7) % 2 == 0
    segs = 10
    for i in range(segs):
        sx = tx + 22 + i * 10
        cv.rect(sx, by + 1, 8, 7, _a(C('#0b0a16'), alpha))
        f = clamp01(hp * segs - i)
        if f > 0:
            fw = max(1, int(round(8 * f)))
            c = C('#ffffff') if blink else col
            cv.rect(sx, by + 1, fw, 7, _a(c, alpha)); cv.hline(sx, by + 1, fw, _a(mix(c, C('#ffffff'), 0.45), alpha))
    # heart + bpm + mini ecg
    hy = y + 31
    beat = 0.0
    for b in beats:
        if 0 <= t - b < 0.15 and (flat_t is None or b < flat_t): beat = 1 - (t - b) / 0.15
    HEART = ['.##.##.', '#######', '#######', '.#####.', '..###..', '...#...']
    hc = C('#5a5a68') if dead else (C('#ff8a8a') if beat > 0.4 else RED)
    for r_, row in enumerate(HEART):
        for c_, ch in enumerate(row):
            if ch == '#': cv.px(tx + c_, hy + 1 + r_, _a(hc, alpha))
    if beat > 0.4 and not dead:
        for (dx, dy) in ((-1, 2), (7, 2), (3, -1)): cv.px(tx + dx, hy + 1 + dy, _a(C('#ffb0b0'), alpha))
    sb = '0' if dead else str(int(bpm))
    cv.text(tx + 10, hy, sb, _a(RED if (bpm > 120 or dead) else CREAM, alpha), 'silkb')
    cv.text(tx + 12 + text_width(sb, 'silkb'), hy + 1, 'BPM', _a(C('#7a8a90'), alpha), 'silk')
    ex0, ew = tx + 52, w - (tx - xx) - 58
    base = hy + 6
    prev = None
    ecol = RED if dead else C('#6dff9a')
    for i in range(ew):
        tt = t - (ew - i) / ew * 1.2
        v = 0.0 if dead else ecg_val(tt, [b for b in beats if flat_t is None or b < flat_t])
        pyy = int(round(base - v * 7))
        if prev is not None:
            a_, b_ = sorted((prev, pyy))
            for yy_ in range(a_, b_ + 1): cv.px(ex0 + i, yy_, _a(ecol, alpha))
        prev = pyy

def task_tracker(cv, x_right, y, t, title, remain, total=600.0, k=1.0, alpha=1.0, failed=0.0, label='当前任务'):
    """quest tracker (top-right): ◆ 当前任务 / title / big mm:ss countdown + draining bar.
    failed 0..1: freezes grey, a red 「失败」 tag slams on."""
    if k <= 0 or alpha <= 0: return
    w, h = 150, 42
    x = int(round(x_right - w + (1 - back_out(clamp01(k), 1.6)) * (w + 20)))
    _panel(cv, x, y, w, h, alpha)
    cv.rect(x + 5, y + 5, 4, 4, _a(GOLD, alpha)); cv.px(x + 6, y + 5, _a(C('#ffffff'), alpha))
    cv.text(x + 12, y + 2, label, _a(GOLD, alpha), 'zh8')
    grey = failed > 0
    cv.text(x + 6, y + 13, title, _a(C('#8a8a96') if grey else CREAM, alpha), 'zh10', shadow=_a(C('#000000'), alpha))
    r = max(0, int(remain)); mm, ss = r // 60, r % 60
    ts = f'{mm:02d}:{ss:02d}'
    warn = remain < 90 and not grey and int(t * 5) % 2 == 0
    cv.text(x + w - 6 - text_width(ts, 'p2p'), y + 2, ts, _a(C('#8a8a96') if grey else (RED if warn else C('#7fe0ff')), alpha), 'p2p')
    bx, by, bw = x + 6, y + 30, w - 12
    cv.rect(bx, by, bw, 5, _a(C('#0b0a16'), alpha))
    fw = int(round((bw - 2) * clamp01(remain / total)))
    if fw > 0: cv.rect(bx + 1, by + 1, fw, 3, _a(C('#5a5a68') if grey else C('#7fe0ff'), alpha))
    if grey:
        a2 = alpha * clamp01(failed)
        sc = 1 + 0.8 * max(0.0, 1 - failed / 0.25)
        lab = '失败'
        tw = text_width(lab, 'zh10')
        cx, cy = x + w - 34, y + 22
        cv.rect(int(cx - (tw / 2 + 4) * sc), int(cy - 7 * sc), int((tw + 8) * sc), int(14 * sc), _a(RED, a2))
        cv.text(int(cx - tw / 2), int(cy - 6), lab, _a(C('#ffffff'), a2), 'zh10')

def onomatopoeia(cv, s, cx, cy, age, scale=4, col=C('#ffe24a'), life=0.9, alpha=1.0, rot_seed=0):
    """comic sound-effect word: pops in big (overshoot), jitters, fades.  returns k."""
    if age < 0 or age > life: return 0.0
    u = age / 0.12
    sc = scale * (1.5 - 0.5 * min(1.0, u)) if u < 1 else scale * (1 + 0.08 * math.sin((age - 0.12) * 40) * math.exp(-(age - 0.12) * 8))
    sc = max(1, int(round(sc)))
    a = alpha * (1 - clamp01((age - life + 0.2) / 0.2))
    jx = int(round(2 * math.sin(age * 70 + rot_seed))) if age < 0.3 else 0
    tw = text_width(s, 'zh12') * sc
    m = text_mask(s, 'zh12')
    big = np.repeat(np.repeat(m, sc, 0), sc, 1)
    x0, y0 = int(cx - tw / 2) + jx, int(cy - 6 * sc)
    for d in range(1, 3):
        for (dx, dy) in ((-d, 0), (d, 0), (0, -d), (0, d), (d, d), (-d, -d), (d, -d), (-d, d)):
            _blit_mask(cv, big, x0 + dx, y0 + dy, _a(SUB_OUT, a))
    _blit_mask(cv, big, x0 + sc, y0 + sc, _a(C('#c8302a'), a))
    _blit_mask(cv, big, x0, y0, _a(col, a))
    if age < 0.25: burst_lines(cv, cx, cy, tw * 0.55, tw * 0.55 + 40 * age / 0.25 + 10, 12, col, a * (1 - age / 0.25))
    return a

def result_panel(cv, t, t0, rows, x=None, y=64, w=300, title='本局结算', title_en='RESULT', gap=0.55, alpha=1.0, head_col=None):
    """death/clear settlement card: gold frame, rows reveal one by one (slide + flash), numbers count up.
    rows: ('kv', label, value, col[, big]) | ('count', label, n, suffix, col[, prefix]) | ('battery', l_lab, l_pct, r_lab, r_pct)
    returns the list of row reveal times (for SFX)."""
    age = t - t0
    times = [t0 + 0.30 + i * gap for i in range(len(rows))]
    if age < 0 or alpha <= 0: return times
    row_h = [30 if (r[0] == 'kv' and len(r) > 4 and r[4]) else (26 if r[0] == 'battery' else 19) for r in rows]
    h = 30 + sum(row_h) + 8
    x = UW // 2 - w // 2 if x is None else x
    k = clamp01(age / 0.25)
    quest_panel(cv, x, y, w, h, k, title, title_en, (), alpha, head_col=head_col or C('#7a1a2a'), body_col=(30, 18, 34))
    if k < 1: return times
    yy = y + 27
    for i, (r, rh) in enumerate(zip(rows, row_h)):
        ra = t - times[i]
        if ra < 0: yy += rh; continue
        sl = int(round((1 - back_out(clamp01(ra / 0.18), 1.4)) * -26))
        a = alpha * clamp01(ra / 0.08)
        lx = x + 14 + sl
        if ra < 0.14: cv.rect(x + 4, yy - 1, w - 8, rh - 2, (255, 240, 200, int(70 * (1 - ra / 0.14) * alpha)))
        kind = r[0]
        if kind in ('kv', 'count'):
            label = r[1]
            cv.rect(lx - 6, yy + 5, 3, 3, _a(GOLD, a))
            cv.text(lx, yy + (5 if (kind == 'kv' and len(r) > 4 and r[4]) else 1), label, _a(C('#cfc0e0'), a), 'zh10')
            vx = x + 112 + sl
            if kind == 'kv':
                val, col = r[2], r[3]; big = len(r) > 4 and r[4]
                if big: big_zh(cv, val, vx, yy - 4, 2, col, a)
                else: cv.text(vx, yy, val, _a(col, a), 'zh12', shadow=_a(C('#000000'), a))
            else:
                n, suf, col = r[2], r[3], r[4]; pre = r[5] if len(r) > 5 else ''
                cu = clamp01((ra - 0.08) / 0.55)
                v = int(round(n * (1 - (1 - cu) ** 2)))
                sv = f'{pre}{v}'
                bump = 1 if (cu >= 1 and ra < 0.75) else 0
                cv.text(vx, yy - bump, sv, _a(col, a), 'zh12', shadow=_a(C('#000000'), a))
                cv.text(vx + text_width(sv, 'zh12') + 3, yy + 1, suf, _a(CREAM, a), 'zh10')
        elif kind == 'battery':
            _, ll, lp, rl, rp = r
            cv.text(lx, yy + 5, ll, _a(C('#cfc0e0'), a), 'zh10')
            bx = lx + text_width(ll, 'zh10') + 6
            battery_icon(cv, bx, yy + 5, lp, charging=True, alpha=a, t=t)
            cv.text(bx + 28, yy + 4, f'{lp}%', _a(GREEN, a), 'silkb')
            cv.text(x + w // 2 - 4 + sl, yy + 4, 'VS', _a(GOLD, a), 'silkb')
            rx = x + w // 2 + 16 + sl
            cv.text(rx, yy + 5, rl, _a(C('#cfc0e0'), a), 'zh10')
            bx2 = rx + text_width(rl, 'zh10') + 6
            battery_icon(cv, bx2, yy + 5, rp, alpha=a, t=t)
            cv.text(bx2 + 28, yy + 4, f'{rp}%', _a(RED, a), 'silkb')
        yy += rh
    return times


def big_zh(cv, s, x, y, scale=2, col=C('#ff4a3c'), alpha=1.0, fname='zh12', out=SUB_OUT, drop=C('#000000')):
    """big CJK word that stays legible: glyph scaled (nearest), 1-step outline ring + drop shadow, no inner shade."""
    m = text_mask(s, fname)
    if m is None: return 0
    big = np.repeat(np.repeat(m, scale, 0), scale, 1)
    _blit_mask(cv, big, x + scale, y + scale, _a(drop, alpha * 0.85))
    _blit_mask(cv, big, x, y, _a(col, alpha))
    return big.shape[1]


# ================================================================ v0.13e · HUD skin v2（更大、更清楚、有进出场）
def loc_tag(cv, t, t0, year, place='', hold=3.6, t_out=None, x=8, y=8, alpha=1.0):
    """location tag: slides in at t0 as [年份 | 地点]; after `hold` s the place folds away leaving a compact year chip;
    slides out at t_out.  Year in p2p (32 px at 1080p), place in zh12 - no 8 px CJK."""
    if t < t0 or alpha <= 0: return
    k = back_out(clamp01((t - t0) / 0.35), 1.5)
    if t_out is not None and t > t_out: k *= 1 - ease_out((t - t_out) / 0.3)
    if k <= 0.01: return
    yw = text_width(str(year), 'p2p') + 14
    pw = text_width(place, 'zh12') + 14 if place else 0
    fold = clamp01((t - t0 - hold) / 0.35)
    pw_now = int(round(pw * (1 - ease_out(fold))))
    w = yw + pw_now; h = 22
    xx = int(round(x - (1 - k) * (w + 16)))
    cv.rect(xx + 2, y + 3, w, h, (0, 0, 0, int(100 * alpha)))
    cv.rect(xx, y, yw, h, _a(GOLD, alpha)); cv.hline(xx, y, yw, _a(C('#fff0b0'), alpha)); cv.hline(xx, y + h - 1, yw, _a(GOLD_D, alpha))
    cv.text(xx + 7, y + 7, str(year), _a(C('#2a1406'), alpha), 'p2p')
    if pw_now > 6:
        cv.rect(xx + yw, y, pw_now, h, _a(NAVY, alpha * 0.95)); cv.hline(xx + yw, y + h - 1, pw_now, _a(GOLD_D, alpha))
        if fold < 0.4:
            a2 = alpha * (1 - fold / 0.4) * clamp01((t - t0 - 0.25) / 0.2)
            cv.text(xx + yw + 7, y + 4, place, _a(CREAM, a2), 'zh12', shadow=_a(C('#000000'), a2))

def _door_pip(cv, x, y, state, alpha, pulse=0.0):
    """12x15 arched door: state 'done' (gold, check), 'now' (outlined, pulsing), 'locked' (dim)."""
    rows = ['..######..', '.########.', '##########', '##########', '##########', '##########', '##########',
            '##########', '##########', '##########', '##########', '##########']
    col = {'done': GOLD, 'now': mix(NAVY2, GOLD, 0.35 + 0.35 * pulse), 'locked': C('#2a2840')}[state]
    edge = {'done': GOLD_D, 'now': GOLD, 'locked': C('#3a3858')}[state]
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch != '#': continue
            e = j == 0 or i in (0, 9) or r[i - 1] == '.' or (i < 9 and r[i + 1] == '.') or j == len(rows) - 1
            cv.px(x + i, y + j, _a(edge if e else col, alpha))
    if state == 'done':
        for (dx, dy) in ((2, 6), (3, 7), (4, 8), (5, 7), (6, 6), (7, 5)): cv.px(x + dx, y + dy, _a(C('#2a1406'), alpha))
    elif state == 'now':
        cv.px(x + 7, y + 7, _a(GOLD, alpha))

def revive_pips(cv, t, pct, stage, total=5, flash=0.0, k=1.0, x_right=472, y=8, alpha=1.0):
    """revive HUD v2: 「复活」 + one door pip per level (cleared = gold ✓, current pulses) + big %."""
    if k <= 0 or alpha <= 0: return
    pw = total * 13 + 4
    ps = f'{int(round(pct))}%'
    w = 40 + pw + text_width(ps, 'p2p') + 10; h = 22
    x = int(round(x_right - w + (1 - back_out(clamp01(k), 1.5)) * (w + 16)))
    cv.rect(x + 2, y + 3, w, h, (0, 0, 0, int(100 * alpha)))
    cv.rect(x, y, w, h, _a(NAVY, 0.95 * alpha)); cv.hline(x, y + h - 1, w, _a(GOLD_D, alpha)); cv.hline(x, y, w, _a(NAVY2, alpha))
    cv.text(x + 6, y + 4, '复活', _a(GOLD, alpha), 'zh12')
    pulse = 0.5 + 0.5 * math.sin(t * 5)
    for i in range(total):
        st = 'done' if i < stage else ('now' if i == stage else 'locked')
        _door_pip(cv, x + 36 + i * 13, y + 4, st, alpha, pulse)
    col = mix(C('#7fe0ff'), C('#ffffff'), flash)
    cv.text(x + 36 + pw + 2, y + 7, ps, _a(col, alpha), 'p2p')
    if flash > 0:
        burst_lines(cv, x + 36 + (stage - 1) * 13 + 5, y + 11, 6 + 10 * flash, 10 + 16 * flash, 10, GOLD, alpha * flash)

def question_card(cv, t, t_in, question, t_answer=None, answer='', hold=4.2, y=6):
    """the level's question as an RPG quest bar (top centre), tucks away after `hold`; at t_answer it drops back
    in as 'done' with the answer (green ✓).  Built on ui.quest_bar."""
    from . import ui as _ui
    if t_answer is not None and t >= t_answer:
        if t > t_answer + 3.6:
            k = 1 - ease_out((t - t_answer - 3.6) / 0.3)
            if k <= 0: return
            y = int(y - (1 - k) * 44)
        return _ui.quest_bar(cv, t, t_answer, answer, (1, 1), kind='本关答案', kind_en='ANSWER', state='done', t_state=t_answer,
                             y=y, new_tag=False)
    if t < t_in or t > t_in + hold + 0.3: return
    yy = y
    if t > t_in + hold: yy = int(y - ease_out((t - t_in - hold) / 0.3) * 44)
    return _ui.quest_bar(cv, t, t_in, question, (0, 1), kind='本关问题', kind_en='QUESTION', y=yy, new_tag=False)

def stat_meter(cv, t, t0, x, y, label, v, col, w=150, life=None, side=1, alpha=1.0, blink=False, fill_in=True):
    """one labelled meter that slides in from the screen edge (side=+1 right / -1 left), fills with an ease."""
    if t < t0: return
    k = back_out(clamp01((t - t0) / 0.3), 1.4)
    if life is not None and t > t0 + life: k *= 1 - ease_out((t - t0 - life) / 0.25)
    if k <= 0.01: return
    h = 22
    xx = int(round(x + side * (1 - k) * (w + 30)))
    cv.rect(xx + 2, y + 3, w, h, (0, 0, 0, int(100 * alpha)))
    cv.rect(xx, y, w, h, _a(NAVY, 0.95 * alpha)); cv.rect(xx, y, 3, h, _a(col, alpha)); cv.hline(xx, y + h - 1, w, _a(GOLD_D, alpha))
    cv.text(xx + 8, y + 4, label, _a(CREAM, alpha), 'zh12')
    bx = xx + 14 + text_width(label, 'zh12'); bw = w - (bx - xx) - 40
    fill = v * ease_out(clamp01((t - t0 - 0.2) / 0.6)) if fill_in else v
    cv.rect(bx, y + 7, bw, 8, _a(C('#0b0a16'), alpha))
    c2 = C('#ffffff') if (blink and int(t * 6) % 2) else col
    cv.rect(bx, y + 7, int(bw * fill), 8, _a(c2, alpha)); cv.hline(bx, y + 7, int(bw * fill), _a(mix(c2, C('#ffffff'), 0.4), alpha))
    s = f'{int(round(fill * 100))}%'
    cv.text(xx + w - 6 - text_width(s, 'p2p'), y + 8, s, _a(c2, alpha), 'p2p')

PARCH = [C('#5a3a1a'), C('#c8a870'), C('#e8d4a4'), C('#f6e8c4')]

def item_card(cv, t, t0, x, y, icon_rgba, name, effect, price='', price_t=None, rarity=C('#7fd0ff'), w=104, life=None, alpha=1.0):
    """RPG shop item card (parchment + gold frame): icon, name in rarity colour, one effect line; the price tag
    flips over at price_t ('???' -> price).  Pops in with ui.pop_k."""
    from . import ui as _ui
    if t < t0: return
    k = _ui.pop_k(t - t0, life if life is not None else 1e9)
    if k <= 0.02: return
    h = 70
    ww, hh = int(w * k), int(h * k)
    x0, y0 = int(x + (w - ww) / 2), int(y + (h - hh) / 2)
    cv.rect(x0 + 3, y0 + 4, ww, hh, (0, 0, 0, int(110 * alpha)))
    cv.rect(x0 - 1, y0 - 1, ww + 2, hh + 2, _a(C('#2a1406'), alpha)); cv.rect(x0, y0, ww, hh, _a(GOLD, alpha))
    cv.rect(x0 + 2, y0 + 2, ww - 4, hh - 4, _a(PARCH[2], alpha))
    for yy in range(y0 + 3, y0 + hh - 3, 3): cv.hline(x0 + 3, yy, ww - 6, _a(PARCH[3], alpha * 0.5))
    if k < 0.95: return
    if icon_rgba is not None:
        ih, iw = icon_rgba.shape[:2]
        cv.rect(x0 + 6, y0 + 6, 28, 28, _a(C('#3a2410'), alpha)); cv.rect(x0 + 7, y0 + 7, 26, 26, _a(C('#6a4420'), alpha))
        _ui.blit_scaled(cv, icon_rgba, x0 + 20, y0 + 20, min(24 / iw, 24 / ih), alpha)
    cv.text(x0 + 40, y0 + 6, name, _a(mix(rarity, C('#000000'), 0.35), alpha), 'zh12')
    cv.text(x0 + 40, y0 + 22, effect, _a(C('#3a2410'), alpha), 'zh10')
    # price tag (flips)
    if price_t is not None:
        f = clamp01((t - price_t) / 0.25)
        sx = abs(math.cos(math.pi * f))
        txt = '???' if f < 0.5 else price
        tw = text_width(txt, 'zh10') + 10
        tw2 = max(2, int(tw * sx))
        px = x0 + ww - 8 - tw; py = y0 + hh - 22
        cv.rect(px + (tw - tw2) // 2, py, tw2, 15, _a(C('#a8302a') if f >= 0.5 else C('#6a5a40'), alpha))
        if sx > 0.6: cv.text(px + 5, py + 2, txt, _a(C('#fff0d0'), alpha), 'zh10')


# ================================================================ v0.13f · boss bar v2 + top-slot rule
def boss_bar(cv, t, t0, name, sub, hp, hp_max, hp_lag=None, portrait=None, k_out=0.0, y=10, w=300, hit=0.0, alpha=1.0):
    """action-game boss bar (top centre): portrait frame on the left, dark-red nameplate with gold rim, segmented
    HP bar with a white 'damage trail' (hp_lag) and big numbers; slides down at t0 (+ shake on hit), up with k_out."""
    if t < t0 or alpha <= 0: return None
    k = back_out(clamp01((t - t0) / 0.4), 1.4) * (1 - ease_out(k_out))
    if k <= 0.01: return None
    x = UW // 2 - w // 2 + int(round(3 * math.sin(t * 70) * hit))
    yy = int(round(y - (1 - k) * 60))
    ph = 38
    cv.rect(x + 3, yy + 4, w, ph, (0, 0, 0, int(110 * alpha)))
    # portrait
    cv.rect(x - 1, yy - 1, ph + 2, ph + 2, _a(C('#1a0606'), alpha)); cv.rect(x, yy, ph, ph, _a(GOLD, alpha))
    cv.rect(x + 2, yy + 2, ph - 4, ph - 4, _a(C('#3a0c10'), alpha))
    if portrait is not None:
        from . import ui as _ui
        ph_, pw_ = portrait.shape[:2]
        _ui.blit_scaled(cv, portrait, x + ph // 2, yy + ph // 2 + 2, min((ph - 6) / pw_, (ph - 6) / ph_), alpha)
    if hit > 0: cv.rect(x + 2, yy + 2, ph - 4, ph - 4, (255, 255, 255, int(160 * hit * alpha)))
    # plate
    px, pw = x + ph + 2, w - ph - 2
    cv.rect(px, yy + 2, pw, ph - 4, _a(C('#2a0a0e'), 0.96 * alpha)); cv.hline(px, yy + 2, pw, _a(GOLD, alpha))
    cv.hline(px, yy + ph - 3, pw, _a(GOLD_D, alpha))
    for sx in (px + pw - 1,):
        for i in range(5): cv.vline(sx + i, yy + 4 + i, ph - 8 - 2 * i, _a(C('#5a1018'), alpha))
    cv.text(px + 6, yy + 5, 'BOSS', _a(C('#ff6a5a'), alpha), 'silkb')
    cv.text(px + 38, yy + 2, name, _a(CREAM, alpha), 'zh12', shadow=_a(C('#000000'), alpha))
    if sub: cv.text(px + 46 + text_width(name, 'zh12'), yy + 4, sub, _a(C('#ffb090'), alpha), 'zh10')
    hs = f'{int(round(hp))}h'
    cv.text(px + pw - 10 - text_width(hs, 'p2p'), yy + 6, hs, _a(C('#ff8a70'), alpha), 'p2p')
    # segmented HP bar
    bx, by, bw, bh = px + 6, yy + 21, pw - 16, 9
    cv.rect(bx - 1, by - 1, bw + 2, bh + 2, _a(C('#0a0204'), alpha))
    f = clamp01(hp / hp_max); fl = clamp01((hp_lag if hp_lag is not None else hp) / hp_max)
    if fl > f: cv.rect(bx, by, int(bw * fl), bh, _a(C('#fff0e0'), alpha))
    cv.rect(bx, by, int(bw * f), bh, _a(C('#d8302a'), alpha))
    cv.hline(bx, by, int(bw * f), _a(C('#ff8a70'), alpha)); cv.hline(bx, by + bh - 1, int(bw * f), _a(C('#8a1010'), alpha))
    for i in range(1, 10): cv.vline(bx + bw * i // 10, by, bh, _a(C('#2a0a0e'), alpha))
    return (x, yy, w, ph)

class TopSlot:
    """one element at a time in the top-centre slot.  Register (name, t_in, t_out) for every top-centre widget;
    check() returns the overlapping pairs (call it in the timeline's self-test)."""
    def __init__(self): self.items = []
    def add(self, name, t_in, t_out): self.items.append((name, t_in, t_out)); return self
    def check(self, gap=0.15):
        bad = []
        it = sorted(self.items, key=lambda r: r[1])
        for a, b in zip(it, it[1:]):
            if b[1] < a[2] + gap: bad.append((a[0], b[0], round(a[2] - b[1], 2)))
        return bad


# ================================================================ v0.13h · shop row
def item_row(cv, t, t0, items, y=88, w=112, gap=8, price='睡眠', t_price=None, stagger=0.14, life=None):
    """a row of item_cards that pop in one after another; with t_price every price tag flips to the same coin.
    items = [(icon_rgba|None, name, effect, rarity_colour), ...]  (the 'same currency' joke of the film's ending)."""
    n = len(items); x0 = (UW - (n * w + (n - 1) * gap)) // 2
    for i, (icon, name, eff, col) in enumerate(items):
        item_card(cv, t, t0 + i * stagger, x0 + i * (w + gap), y, icon, name, eff, price=price,
                  price_t=(t_price + i * stagger) if t_price is not None else 1e9, rarity=col, w=w,
                  life=None if life is None else life - i * stagger)
