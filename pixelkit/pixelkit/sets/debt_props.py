"""pixelkit.sets.debt_props - 「睡眠债」实物道具（v0.13f，第 4 关）。全部直接画在 pixstage.Stage 上（320x180 美术像素）。

    sevenseg(st, x, y, text, s=1, on='#ff3a2a', off='#3a0c0a')      7 段数码管（发光段 + 暗段），text 可含 0-9 - 空格 L A P S E
    bill_monster(st, x, y_foot, t, size=1.0, face='grin', hit=0.0)  欠条怪：一沓沓账单堆成的怪物（会呼吸、晃、被打时压扁发白）
    pvt_box(st, cx, cy, t, ms=None, label='', press=0.0, lapse=False) 手持反应盒（PVT）：红色数码管 + 大按钮 + 双手 + 拇指
    printout(st, x, y, t, k=1.0, curves=...)                         打印机吐出实验记录纸，两条曲线 + 红笔圈
    iou_jar(st, x, y_base, n, t, overflow=False)                     「欠条」玻璃罐：n 张纸条堆在里面，满了会溢出
    alarm_clock(st, x, y, t, ring=0.0, hhmm='0600')                  闹钟（响铃时抖 + 震动线）
    cup_stack(st, x, y, n)                                           桌上的空咖啡杯（n 个，第 6 个起叠高 / 倒在一边）
"""
import math
import numpy as np

# ---------------------------------------------------------------- 7-segment display
SEG = {'0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', '6': 'afgedc', '7': 'abc', '8': 'abcdefg',
       '9': 'abcdfg', '-': 'g', ' ': '', 'L': 'fed', 'A': 'abcefg', 'P': 'abefg', 'S': 'afgcd', 'E': 'afged', 'H': 'fbgec', 'O': 'abcdef'}

def sevenseg(st, x, y, text, s=1, on='#ff3a2a', off='#3a0c0a', glow=1.0):
    """digits 5s wide x 9s tall, 1s gap.  Lit segments are emissive (E=glow)."""
    w, h = 5 * s, 9 * s
    for i, ch in enumerate(text):
        ox = x + i * (w + 2 * s)
        segs = {'a': (ox + s, y, 3 * s, s), 'g': (ox + s, y + 4 * s, 3 * s, s), 'd': (ox + s, y + 8 * s, 3 * s, s),
                'f': (ox, y + s, s, 3 * s), 'b': (ox + 4 * s, y + s, s, 3 * s), 'e': (ox, y + 5 * s, s, 3 * s), 'c': (ox + 4 * s, y + 5 * s, s, 3 * s)}
        lit = SEG.get(ch, '')
        for k, (sx, sy, sw, sh) in segs.items():
            if k in lit: st.rect(sx, sy, sw, sh, on, glow)
            else: st.rect(sx, sy, sw, sh, off)
    return len(text) * (w + 2 * s)

# ---------------------------------------------------------------- the bill monster
PAPER = ['#4a4030', '#7a6c52', '#a89a7c', '#c2b698', '#dccfb2']

def bill_monster(st, x, y, t, size=1.0, face='grin', hit=0.0, seed=3):
    """a monster made of stacked IOUs.  (x, y) = bottom centre; size scales it (it grows as the debt grows).
    face: grin | hurt | smug.  hit 0..1: squash + flash white (pillow impact)."""
    rng = np.random.default_rng(seed)
    s = size
    br = math.sin(t * 2.2) * 1.2 * s
    sq = 0.25 * hit
    H = 70 * s * (1 - sq) + br; W = 44 * s * (1 + sq * 0.6)
    # body = a leaning tower of sheets (rows of slightly offset rectangles)
    rows = int(max(6, H / 4))
    body = np.zeros((st.H, st.W), bool)
    for r in range(rows):
        u = r / rows
        sway = math.sin(t * 1.6 + u * 2.4) * 3 * s * u
        ww = W * (1.0 - 0.35 * u) + rng.uniform(-3, 3) * s
        yy = y - (r + 1) * H / rows
        xx = x - ww / 2 + sway + rng.uniform(-1.5, 1.5) * s
        m = st.M_rect(xx, yy, ww, H / rows + 1)
        body |= m
        col = PAPER[3] if r % 2 else PAPER[2]
        st.fill(m, col)
        st.line(xx, yy, xx + ww, yy, PAPER[1])
        if rng.random() < 0.5: st.rect(xx + rng.uniform(2, ww - 8), yy + 1, 5 * s, 1, '#c8302a')       # red debt marks
    st.outline(body, '#2a2014')
    # arms = paper scrolls
    for sg in (-1, 1):
        ax0, ay0 = x + sg * W * 0.45, y - H * 0.55
        wav = math.sin(t * 3 + sg) * 6 * s
        ax1, ay1 = ax0 + sg * 16 * s, ay0 - 10 * s + wav
        for w_ in range(-1, 2): st.line(ax0, ay0 + w_, ax1, ay1 + w_, PAPER[3])
        st.ell(ax1, ay1, 3.5 * s, 3.5 * s, PAPER[4]); st.outline(st.M_ell(ax1, ay1, 3.5 * s, 3.5 * s), '#2a2014')
    # face
    fx, fy = x, y - H * 0.62
    for sg in (-1, 1):
        ex = fx + sg * 8 * s
        if face == 'hurt':
            st.line(ex - 3 * s, fy - 2 * s, ex + 3 * s, fy + 2 * s, '#1a0a08'); st.line(ex - 3 * s, fy + 2 * s, ex + 3 * s, fy - 2 * s, '#1a0a08')
        else:
            st.ell(ex, fy, 4 * s, 4.5 * s, '#ffffff'); st.ell(ex + 1 * s, fy + 0.5 * s, 2 * s, 2.5 * s, '#c8302a', 0.6)
            st.px(ex + 1 * s, fy + 0.5 * s, '#1a0a08')
            st.line(ex - 4 * s, fy - 6 * s, ex + 4 * s, fy - 4 * s + (2 * s if face == 'smug' else 0), '#1a0a08')
    my = fy + 10 * s
    if face == 'hurt':
        st.ell(fx, my, 4 * s, 3 * s, '#3a0a0a')
    else:
        m = st.M_ell(fx, my - 2 * s, 11 * s, 6 * s) & (st.yy > my - 2 * s)
        st.fill(m, '#3a0a0a')
        for k in range(-3, 4): st.rect(fx + k * 3 * s - s, my - 2 * s, 2 * s, 2 * s, '#fffaf0')
    # the 欠 stamp on the belly
    st.ell(fx, y - H * 0.28, 7 * s, 7 * s, '#c8302a', 0.3)
    st.text(fx - 5, y - H * 0.28 - 6, '欠', '#fff0e0', 'zh10', 0.4)
    if hit > 0:                       # brief pale flash (blend, never solid white)
        st.img[body, :3] = (st.img[body, :3] * (1 - 0.45 * hit) + 255 * 0.45 * hit).astype(np.uint8)
    return (fx, y - H)

# ---------------------------------------------------------------- PVT handheld box
def pvt_box(st, cx, cy, t, ms=None, text=None, press=0.0, lapse=False, sleepy=0.0):
    """close-up of the handheld reaction-time box held in two hands.  ms = counter value (None = blank),
    text overrides the digits (e.g. 'LAPSE').  press 0..1 = thumb pushes the button."""
    W, H = 150, 84
    x0, y0 = cx - W / 2, cy - H / 2
    desk = st.M_rect(0, y0 + H - 10, st.W, st.H)
    st.part(desk, ['#2a180e', '#4a2e1a', '#6a4426', '#8a5a34'], bevel=3, light=(0, -1, 0.4), amb=0.5, outline=None)
    st.rect(0, y0 + H - 10, st.W, 1, '#a8784a')
    st.mul(st.M_ell(cx, y0 + H, W * 0.6, 6), 0.55)
    case = st.M_rect(x0, y0, W, H) & ~(st.M_rect(x0, y0, 4, 4) | st.M_rect(x0 + W - 4, y0, 4, 4))
    st.part(case, ['#14141c', '#26262f', '#3a3a46', '#56566a', '#7a7a90'], bevel=6, light=(-0.4, -0.7, 0.6), amb=0.35, ink='#05050a')
    # display window
    dx0, dy0, dw, dh = cx - 56, y0 + 10, 112, 34
    st.rect(dx0 - 2, dy0 - 2, dw + 4, dh + 4, '#08080c'); st.rect(dx0, dy0, dw, dh, '#1a0604')
    s_txt = text if text is not None else ('' if ms is None else f'{int(ms):4d}'.replace(' ', ' '))
    s_txt = s_txt[-5:].rjust(4)
    on = '#ff4a30' if not lapse else ('#ff4a30' if int(t * 6) % 2 else '#ff9a70')
    sevenseg(st, dx0 + 8, dy0 + 6, s_txt, s=2 if len(s_txt) <= 4 else 2, on=on, off='#2a0806', glow=0.95)
    st.text(dx0 + dw - 18, dy0 + dh - 11, 'ms', '#8a3a2a', 'silk')
    # glass reflection
    st.line(dx0 + 4, dy0 + 2, dx0 + 20, dy0 + 2, '#5a2a24'); st.line(dx0 + 2, dy0 + 4, dx0 + 10, dy0 + 4, '#4a2018')
    for (sx, sy) in ((x0 + 5, y0 + 5), (x0 + W - 6, y0 + 5), (x0 + 5, y0 + H - 6), (x0 + W - 6, y0 + H - 6)):
        st.ell(sx, sy, 1.5, 1.5, '#6a6a7a'); st.px(sx, sy, '#2a2a34')
    st.rect(x0 + 10, y0 + H - 26, 60, 12, '#1a1a22'); st.text(x0 + 14, y0 + H - 25, 'PVT-192', '#a8a8c0', 'silkb')
    st.rect(dx0, dy0 + dh + 3, dw, 1, '#5a1a14')                                  # LED spill on the case
    # label + button
    bx, by = cx + 34, y0 + H - 18
    br = st.M_ell(bx, by + 2 * press, 13, 9)
    st.part(br, ['#5a0a0a', '#9a1a1a', '#d83a2a', '#ff7a5a'], bevel=4, light=(-0.4, -0.7, 0.6), amb=0.4, ink='#1a0404')
    # chibi mitten hand (matches the cast's round hands): sleeve from the right, a round mitt resting on the
    # button, a stubby thumb nub on top. press squashes the mitt down; sleepy makes it slide off the button.
    SK = ['#7a4434', '#b06a4c', '#d8906a', '#f0b48a', '#fcd2aa']
    HD = ['#141c34', '#22305a', '#33457a', '#4a5e9a']
    hx = bx + 8 + 14 * sleepy; hy = by - 4 + 3 * press + 6 * sleepy
    sl = st.M_poly([(st.W + 4, hy + 4), (st.W + 4, hy + 30), (hx + 18, hy + 22), (hx + 12, hy + 4)])
    st.part(sl, HD, bevel=5, light=(-0.4, -0.7, 0.6), amb=0.3, ink='#05060e')
    st.part(st.M_rect(hx + 8, hy - 2, 7, 24) & sl | (st.M_ell(hx + 12, hy + 10, 4, 11) & ~st.M_ell(hx + 4, hy + 10, 9, 13)),
            ['#b8b4c8', '#d8d4e4', '#f0eef8'], bevel=1.5, amb=0.5, ink='#3a3650')           # cuff
    mitt = st.M_ell(hx, hy + 8, 11, 9 - 1.5 * press)
    st.part(mitt, SK, bevel=4, light=(-0.5, -0.7, 0.5), amb=0.35, ink='#3a1a10')
    thumb = st.M_ell(hx - 7, hy + 1 + 2 * press, 4.5, 4)
    st.part(thumb, SK, bevel=2, light=(-0.5, -0.7, 0.5), amb=0.38, ink='#3a1a10')
    st.line(hx - 5, hy + 10, hx + 3, hy + 12, SK[1])                                       # finger crease
    return (dx0, dy0, dw, dh)

# ---------------------------------------------------------------- printout
def printout(st, x, y, t, k=1.0, label_a='每晚 6h × 14 天', label_b='通宵 1 夜', circle=0.0):
    """a dot-matrix printer at the top, paper scrolls down by k (0..1); two curves drawn as k reveals them."""
    W, Hmax = 150, 120
    h = int(Hmax * k)
    st.rect(x - 10, y - 14, W + 20, 16, '#c8c0b0'); st.rect(x - 10, y - 14, W + 20, 3, '#e8e2d4'); st.rect(x - 6, y - 2, W + 12, 3, '#2a2a2a')
    st.rect(x + W - 12, y - 10, 6, 3, '#3ad86a', 0.9)
    if h <= 2: return
    paper = st.M_rect(x, y, W, h)
    st.fill(paper, '#f6f2e6')
    for yy in range(y + 6, y + h, 8): st.line(x + 4, yy, x + W - 4, yy, '#dcd6c4')
    for yy in range(y + 4, y + h, 6): st.px(x + 2, yy, '#b8b0a0'); st.px(x + W - 3, yy, '#b8b0a0')
    st.text(x + 8, y + 4, '注意力测试记录', '#3a3020', 'zh10')
    # axes + curves (rise = more lapses over 14 days)
    ox, oy = x + 14, y + 100
    if h > 100:
        st.line(ox, y + 24, ox, oy, '#5a5040'); st.line(ox, oy, x + W - 10, oy, '#5a5040')
        for d in range(0, 120):
            u = d / 120
            ya = oy - 62 * (1 - math.exp(-u * 2.2)) - 2 * math.sin(d * 0.7)
            yb = oy - 60 + 2 * math.sin(d * 0.5)
            st.px(ox + 2 + d, ya, '#2a5ab8'); st.px(ox + 2 + d, ya + 1, '#2a5ab8')
            if d > 90: st.px(ox + 2 + d, yb, '#d8402a'); st.px(ox + 2 + d, yb + 1, '#d8402a')
        st.text(ox + 40, oy - 14, label_a, '#2a5ab8', 'zh8')
        st.text(ox + 60, y + 22, label_b, '#d8402a', 'zh8')
    if circle > 0:
        cx_, cy_ = ox + 108, oy - 60
        n = int(60 * circle)
        for i in range(n):
            a = i / 60 * 2 * math.pi
            st.px(cx_ + 16 * math.cos(a), cy_ + 9 * math.sin(a), '#e0302a'); st.px(cx_ + 16 * math.cos(a) + 1, cy_ + 9 * math.sin(a), '#e0302a')

# ---------------------------------------------------------------- IOU jar, alarm clock, cups
def iou_jar(st, x, y, n, t, overflow=False, label=True):
    """small rounded glass jar (base at y, ~16x20) with n paper slips; overflow pushes slips over the rim."""
    W, H = 16, 20
    body = st.M_ell(x, y - H * 0.45, W / 2, H * 0.5) | st.M_rect(x - W / 2 + 1, y - H * 0.6, W - 2, H * 0.6 - 1)
    st.fill(body, (70, 96, 116)); st.fill(body & ~st.M_ell(x, y - H * 0.45, W / 2 - 1.5, H * 0.5 - 1.5), (150, 190, 210))
    rng = np.random.default_rng(7)
    for i in range(min(n, 14)):
        sx = x - W / 2 + 3 + rng.uniform(0, W - 8); sy = y - 3 - (i // 3) * 3 - rng.uniform(0, 1)
        if sy < y - H + 3 and not overflow: continue
        st.rect(sx, sy, 4, 2, ['#f6f2e6', '#ffe8a0', '#f2d8d0'][i % 3]); st.px(sx + 1, sy, '#c8302a')
    if overflow:
        for i in range(3):
            st.rect(x - 6 + i * 4, y - H - 2 - (i % 2) * 2, 4, 2, '#ffe8a0'); st.px(x - 5 + i * 4, y - H - 2 - (i % 2) * 2, '#c8302a')
    st.fill(st.M_rect(x - W / 2 + 2, y - H * 0.8, 1, H * 0.55), (230, 244, 255))       # glass glint
    st.rect(x - W / 2 + 1, y - H - 1, W - 2, 3, '#8a6a40'); st.rect(x - W / 2 + 1, y - H - 1, W - 2, 1, '#b8945a')
    if label:
        st.rect(x - 4, y - H * 0.45 - 3, 8, 7, '#f6f2e6'); st.text(x - 4, y - H * 0.45 - 6, '欠', '#c8302a', 'zh8')

def alarm_clock(st, x, y, t, ring=0.0, hhmm='0600'):
    sh = (2 * math.sin(t * 60) * ring)
    x = x + sh
    body = st.M_ell(x, y, 10, 9)
    st.part(body, ['#5a0a0a', '#9a1a1a', '#d83a2a', '#ff7a5a'], bevel=3, amb=0.4, ink='#1a0404')
    st.ell(x, y, 7, 6, '#f2ead6')
    st.line(x, y, x, y - 4, '#1a1a1a'); st.line(x, y, x + 3, y + 1, '#1a1a1a')
    for sg in (-1, 1):
        st.ell(x + sg * 7, y - 9, 3.5, 2.5, '#c8a040'); st.line(x + sg * 6, y + 8, x + sg * 8, y + 11, '#3a3a3a')
    if ring > 0:
        for k in range(3):
            r = 13 + k * 4
            for sg in (-1, 1):
                st.line(x + sg * r, y - 6, x + sg * (r + 2), y - 10, '#ffe27a', 0.9)

def cup_stack(st, x, y, n, s=1.0):
    """paper coffee cups; the first 4 stand in a row, the rest pile on top / one lies tipped over."""
    w, h = 7 * s, 9 * s
    for i in range(n):
        if i < 4: cx, cy = x + i * (w + 2), y
        elif i < 7: cx, cy = x + w * 0.5 + (i - 4) * (w + 2), y - h
        else: cx, cy = x + w + (i - 7) * (w + 2), y - 2 * h
        m = st.M_poly([(cx, cy - h), (cx + w, cy - h), (cx + w - s, cy), (cx + s, cy)])
        st.part(m, ['#6a6058', '#a8a090', '#e8e0d0', '#fffaf0'], bevel=1.5, amb=0.45, ink='#2a2420')
        st.rect(cx, cy - h, w, max(1, s), '#3a2014')
        st.rect(cx + s, cy - h * 0.55, w - 2 * s, 2.5 * s, '#a85a2a')            # sleeve band
    if n >= 6:                                                                     # one tipped over on the floor
        tx, ty = x - 10 * s, y
        m = st.M_poly([(tx, ty - w), (tx + h, ty - w + s), (tx + h, ty), (tx, ty)])
        st.part(m, ['#6a6058', '#a8a090', '#e8e0d0', '#fffaf0'], bevel=1.5, amb=0.45, ink='#2a2420')
        st.fill(st.M_ell(tx - 3 * s, ty - 1, 4 * s, 1.5 * s), '#4a2a14')
