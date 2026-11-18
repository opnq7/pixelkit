"""pixelkit.ui - screen-space UI drawn on a 480x270 grid (x4 = 1080p).

Same pixel grain as the world at zoom 1 (STYLE_GUIDE: "one pixel size on screen").  Draw into a
UI canvas each frame, then composite with scene.ui_over(img, ui.a, scale=4).

    ui = UICanvas()
    chat_bubble(ui, x, y, ['在吗？'], avatar='#7aa7ff', k=pop_k(age))
    speech_bubble(ui, ax, ay, '好的！', age)            # Claude's reply with a coin
    hud_time(ui, 8, 8, '16:30');  hud_counter(ui, 472, 8, 9999)
World anchors: x, y = cam.w2ui(wx, wy, 4)
"""
import numpy as np, math, functools
from .core import Canvas, C, mix, text_width, text_mask, sprite, outline_sprite
from .anim import back_out

UW, UH, US = 480, 270, 4
INK = C('#3b2620'); INK2 = C('#a0583c'); CREAM = C('#fff3df')
TC = C('#c8654a'); TC_L = C('#e88e6e'); TC_D = C('#8f3f2b'); TC_DD = C('#7a3424'); OUTL = C('#2a1715')
NAVY = C('#1b1830'); NAVY2 = C('#2e2a4c'); GOLD = C('#f2c94c'); GOLD_D = C('#9a6a20')

def UICanvas():
    return Canvas(UW, UH)

def ease_out(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3

def pop_k(age, life=1e9, t_in=0.16, t_out=0.12):
    """scale factor for a pop-in (overshoot) / pop-out bubble."""
    if age < 0: return 0.0
    if age < t_in * 0.45: return 0.35 + (1.14 - 0.35) * (age / (t_in * 0.45))
    if age < t_in: return 1.14 - 0.14 * ((age - t_in * 0.45) / (t_in * 0.55))
    if age > life - t_out: return max(0.0, (life - age) / t_out)
    return 1.0

def _a(col, alpha):
    a = 0.0 if alpha < 0 else (1.0 if alpha > 1 else alpha)      # overshoot easings (back_out) must never wrap uint8
    return (col[0], col[1], col[2], int(col[3] * a))

def big_text(cv, x, y, s, col, fname='zh12', scale=2, shadow=None, alpha=1.0):
    m = text_mask(s, fname)
    m2 = np.repeat(np.repeat(m, scale, 0), scale, 1)
    if shadow is not None: cv._mask(m2, x + scale, y + scale, _a(shadow, alpha))
    cv._mask(m2, x, y, _a(col, alpha))
    cols = np.where(m.any(axis=0))[0]
    return (int(cols[-1] + 1) if len(cols) else 0) * scale

# ------------------------------------------------------------------ coins
COIN_ROWS = [
    ["..ooo..", ".oyyyo.", "oyYyyyo", "oyYyyyo", "oyYyyyo", ".oyyyo.", "..ooo.."],
    ["..oo...", ".oyyo..", ".oYyo..", ".oYyo..", ".oYyo..", ".oyyo..", "..oo..."],
    ["..o....", "..o....", "..o....", "..o....", "..o....", "..o....", "..o...."],
    ["...oo..", "..oyyo.", "..oyYo.", "..oyYo.", "..oyYo.", "..oyyo.", "...oo.."],
]
_CP = {'o': C('#8a4a10'), 'y': C('#ffc93c'), 'Y': C('#fff4b0')}
COIN = [sprite(r, _CP) for r in COIN_ROWS]

def coin(cv, x, y, t=0.0, alpha=1.0, spin=8.0):
    """spinning coin centred at x, y."""
    f = int(t * spin) % 4
    cv.blit(COIN[f], int(round(x)) - 3, int(round(y)) - 3, alpha_mul=alpha)

# ------------------------------------------------------------------ bubbles
def chat_bubble(cv, x, y, lines, avatar='#7aa7ff', k=1.0, name=None, fname='zh10', alpha=1.0, max_w=None,
                fill=C('#ffffff'), ink=C('#20232c'), face='smile'):
    """incoming chat message: round avatar + white bubble.  lines: str or list of str. (x, y) = top-left."""
    if k <= 0.01: return (0, 0)
    if isinstance(lines, str): lines = [lines]
    lh = 12 if fname == 'zh10' else (14 if fname == 'zh12' else 10)
    tw = max(text_width(l, fname) for l in lines)
    if name: tw = max(tw, text_width(name, 'zh8'))          # v0.10: short replies never clip the sender's name
    bw0, bh0 = tw + 14, len(lines) * lh + 8 + (9 if name else 0)
    bw, bh = max(6, int(bw0 * k)), max(6, int(bh0 * k))
    # avatar
    ac = C(avatar); ax, ay = x + 7, y + 7
    cv.ellipse(ax, ay, 7.5, 7.5, _a(OUTL, alpha)); cv.ellipse(ax, ay, 6.5, 6.5, _a(ac, alpha))
    cv.ellipse(ax - 1.5, ay - 2.5, 3, 2, _a(mix(ac, C('#ffffff'), 0.4), alpha))
    cv.px(ax - 3, ay, _a(OUTL, alpha)); cv.px(ax + 2, ay, _a(OUTL, alpha))
    if face == 'smile': cv.hline(ax - 2, ay + 3, 4, _a(OUTL, alpha))
    else: cv.hline(ax - 2, ay + 3, 4, _a(OUTL, alpha)); cv.px(ax - 3, ay + 2, _a(OUTL, alpha))
    bx, by = x + 18, y
    cv.rrect(bx + 1, by + 2, bw, bh, (20, 10, 30, int(80 * alpha)), 3)
    cv.rrect(bx, by, bw, bh, _a(OUTL, alpha), 3)
    cv.rrect(bx + 1, by + 1, bw - 2, bh - 2, _a(fill, alpha), 3)
    cv.hline(bx + 3, by + bh - 2, bw - 6, _a(C('#dcdfe6'), alpha))
    for i in range(3):            # little tail towards the avatar
        cv.vline(bx - 3 + i, by + 5 + i // 2, 3 - i, _a(OUTL if i == 0 else fill, alpha))
    if k > 0.92:
        ty = by + 4
        if name:
            cv.text(bx + 7, ty - 1, name, _a(C('#8a8fa0'), alpha), 'zh8'); ty += 9
        for l in lines:
            cv.text(bx + 7, ty, l, _a(ink, alpha), fname); ty += lh
    return (bw + 18, bh)

def speech_bubble(cv, ax, ay, text, age, life=0.95, side=1, col=INK, with_coin=True, fill=C('#ffffff'),
                  fname='zh12', rise=3, scale=1, alpha=1.0, t=None):
    """Claude's reply bubble (tail points to (ax, ay)).  scale=2 for a big shout, 0.6.. for a tiny one."""
    k = pop_k(age, life)
    if k <= 0.01: return
    tw = text_width(text, fname)
    iw = 10 if with_coin else 0
    bw0, bh0 = tw + 12 + iw, (17 if fname == 'zh12' else 15)
    bw, bh = max(6, int(round(bw0 * k))), max(5, int(round(bh0 * k)))
    lift = int(min(age, 0.6) / 0.6 * rise)
    bx = int(ax + side * 4) if side > 0 else int(ax - 4 - bw)
    by = int(ay - 6 - bh - lift)
    cv.rrect(bx + 1, by + 2, bw, bh, (30, 10, 10, int(90 * alpha)), 2)
    cv.rrect(bx, by, bw, bh, _a(OUTL, alpha), 2)
    cv.rrect(bx + 1, by + 1, bw - 2, bh - 2, _a(fill, alpha), 2)
    cv.hline(bx + 3, by + bh - 2, bw - 6, _a(mix(fill, C('#d9cbb5'), 0.6), alpha))
    tx = bx + (4 if side > 0 else bw - 8)
    for i in range(4):
        xx = tx - i if side > 0 else tx + i
        cv.hline(xx, by + bh - 1 + i, 4, _a(OUTL, alpha))
        if i < 3: cv.hline(xx + 1, by + bh - 1 + i, 2, _a(fill, alpha))
    if k > 0.78:
        x0 = bx + (bw - (tw + iw)) // 2
        if with_coin:
            f = int(((t if t is not None else age) * 8)) % 4
            cv.blit(COIN[f], x0, by + (bh - 7) // 2, alpha_mul=alpha)
        cv.text(x0 + iw, by + (bh - (12 if fname == 'zh12' else 10)) // 2 - 1, text, _a(col, alpha), fname)

def tiny_bubble(cv, ax, ay, text, age, life=1.0, alpha=1.0):
    """very small reply (e.g. the whispered '好的！' during the freeze)."""
    speech_bubble(cv, ax, ay, text, age, life, fname='zh8', with_coin=False, rise=1, alpha=alpha)

# ------------------------------------------------------------------ HUD
def _hud_panel(cv, x, y, w, h, alpha=1.0):
    cv.rrect(x + 1, y + 2, w, h, (0, 0, 0, int(90 * alpha)), 2)
    cv.rrect(x, y, w, h, _a(GOLD_D, alpha), 2)
    cv.rrect(x + 1, y + 1, w - 2, h - 2, (NAVY[0], NAVY[1], NAVY[2], int(230 * alpha)), 2)
    cv.hline(x + 3, y + 1, w - 6, _a(NAVY2, alpha))

def hud_time(cv, x, y, hhmm, day='周五', day_en='FRI', alpha=1.0, flash=0.0):
    if alpha <= 0: return
    w, h = 64, 28
    _hud_panel(cv, x, y, w, h, alpha)
    cv.text(x + 5, y + 2, day, _a(CREAM, alpha), 'zh10')
    cv.text(x + 28, y + 4, day_en, _a(GOLD, alpha), 'silkb')
    tc = mix(GOLD, C('#ffffff'), flash)
    cv.text(x + 5, y + 16, hhmm, _a(tc, alpha), 'p2p', shadow=(0, 0, 0, int(255 * alpha)))
    cx, cy = x + w - 9, y + 8
    cv.ellipse(cx, cy, 4, 4, _a(GOLD, alpha)); cv.ellipse(cx, cy, 3, 3, _a(NAVY, alpha))
    cv.vline(int(cx), int(cy) - 2, 2, _a(CREAM, alpha)); cv.hline(int(cx), int(cy), 2, _a(CREAM, alpha))

def fmt_int(v): return f"{int(v):,}"

def hud_counter(cv, x_right, y, value, alpha=1.0, bump=0.0, t=0.0, label='今日已处理', tag='DONE'):
    """returns the coin slot position (where flying coins should land)."""
    if alpha <= 0: return (x_right - 60, y + 18)
    s = fmt_int(value)
    tw = text_width(s, 'p2p')
    w = max(106, tw + 24); h = 28
    x = x_right - w
    yy = y - int(round(bump * 2))
    _hud_panel(cv, x, yy, w, h, alpha)
    cv.text(x + 5, yy + 2, label, _a(CREAM, alpha), 'zh10')
    cv.text(x + 60, yy + 4, tag, _a(GOLD, alpha), 'silkb')
    vc = mix(GOLD, C('#ffffff'), min(1, bump))
    cv.text(x + w - 5 - tw, yy + 16, s, _a(vc, alpha), 'p2p', shadow=(0, 0, 0, int(255 * alpha)))
    cv.blit(COIN[int(t * 6) % 4 if int(t * 6) % 4 != 2 else 1], x + 5, yy + 16, alpha_mul=alpha)
    return (x + 8, yy + 19)

def fly_coin(cv, p0, p1, u, t=0.0, arc=26):
    """coin flying from p0 to p1 (UI coords), u 0..1."""
    if not 0 <= u <= 1: return
    e = u * u * (3 - 2 * u)
    x = p0[0] + (p1[0] - p0[0]) * e
    y = p0[1] + (p1[1] - p0[1]) * e - arc * math.sin(math.pi * u)
    coin(cv, x, y, t + u)

# ------------------------------------------------------------------ JRPG dialog box (reference style)
@functools.lru_cache(maxsize=16)
def _box_bg(w, h):
    cv = Canvas(w, h)
    cv.rrect(0, 0, w, h, OUTL, 3); cv.rrect(1, 1, w - 2, h - 2, TC, 3)
    cv.hline(3, 1, w - 6, TC_L); cv.hline(3, 2, w - 6, mix(TC, TC_L, 0.5)); cv.hline(3, h - 2, w - 6, TC_D)
    cv.rrect(3, 3, w - 6, h - 6, TC_DD, 2); cv.rrect(4, 4, w - 8, h - 8, C('#f6c9a8'), 1)
    ix, iy, iw, ih = 5, 5, w - 10, h - 10
    cv.dither_v(ix, iy, iw, ih, C('#fbf5e9'), C('#efe2c9'))
    for (cx, cy) in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]: cv.px(cx, cy, C('#f2b79a'))
    return cv.a

DOT_ON = C('#fbefd6'); DOT_WARM = C('#f4a874'); DOT_OFF = C('#29212f'); DOT_GLOW = C('#4b2c2b'); SCREEN = C('#1b1520')
EYES = {
    'normal': [".###.", "#####", "#####", "#####", ".###."],
    'wide':   [".###.", "##.##", "#####", "#####", ".###."],
    'happy':  [".....", ".###.", "#...#", ".....", "....."],
    'closed': [".....", ".....", "#...#", ".###.", "....."],
    'blink':  [".....", ".....", "#####", ".....", "....."],
    'half':   [".....", ".....", "#####", "#####", ".###."],
    'q':      [".###.", "#...#", "..##.", ".....", "..#.."],
    'sad':    ["...##", "..###", ".####", "#####", ".###."],      # left eye; the right eye is mirrored
    'tired':  [".....", ".....", ".....", "#####", ".###."],
    'up':     [".###.", "##.##", "#####", ".###.", "....."],      # looking up
}
MIRRORED = {'sad'}
MOUTHS = {'smile': [(7, 4), (7, 8), (8, 5), (8, 6), (8, 7)], 'flat': [(8, 5), (8, 6), (8, 7)],
          'o': [(7, 6), (8, 5), (8, 7), (9, 6)], 'frown': [(8, 4), (8, 8), (7, 5), (7, 6), (7, 7)],
          'wavy': [(8, 4), (7, 5), (8, 6), (7, 7), (8, 8)], 'none': []}

def portrait(cv, x, y, face='normal', mouth='smile', W=44, H=42):
    cv.rrect(x, y, W, H, OUTL, 3); cv.rrect(x + 1, y + 1, W - 2, H - 2, C('#efe5d2'), 3)
    cv.hline(x + 3, y + 1, W - 6, C('#fffaf0')); cv.rect(x + 3, y + H - 3, W - 6, 1, C('#d4c6ae'))
    sx, sy, sw, sh = x + 4, y + 4, W - 8, H - 10
    cv.rrect(sx, sy, sw, sh, SCREEN, 2)
    pitch = 3; cols = sw // pitch; rows = sh // pitch
    gx = sx + (sw - cols * pitch) // 2 + 1; gy = sy + (sh - rows * pitch) // 2 + 1
    on = {}
    g = EYES.get(face, EYES['normal'])
    if face == 'q':
        for r, row in enumerate(g):
            for c, ch in enumerate(row):
                if ch == '#': on[(r + 1, c + 4)] = DOT_ON
    else:
        for c0 in (0, 7):
            gg = [row[::-1] for row in g] if (face in MIRRORED and c0 == 7) else g
            for r, row in enumerate(gg):
                for c, ch in enumerate(row):
                    if ch == '#': on[(r + 1, c + c0)] = DOT_WARM if (r >= 3 and face in ('normal', 'wide')) else DOT_ON
        for (r, c) in MOUTHS.get(mouth, []): on[(r, c)] = DOT_ON
    for (r, c), col in on.items():
        cv.rect(gx + c * pitch - 1, gy + r * pitch - 1, 4, 4, DOT_GLOW)
    for r in range(rows):
        for c in range(cols):
            px_, py_ = gx + c * pitch, gy + r * pitch
            if (r, c) in on: cv.rect(px_, py_, 2, 2, on[(r, c)])
            else: cv.px(px_, py_, DOT_OFF)
    cv.rect(x + W - 10, y + H - 5, 3, 1, C('#7ee08a'))

def name_tab(cv, x, y, name='CLAUDE', icon='spark', col=None):
    """icon: 'spark' (Claude) | 'fish' (the old fisherman) | None.  col: (base, light, dark, shadow) or None = terracotta."""
    base, lt, dk, dd = col or (TC, TC_L, TC_D, TC_DD)
    tw = text_width(name, 'silkb'); w = tw + (16 if icon else 9); h = 11
    cv.rrect(x, y, w, h, OUTL, 2); cv.rrect(x + 1, y + 1, w - 2, h - 2, base, 1)
    cv.hline(x + 2, y + 1, w - 4, lt); cv.hline(x + 2, y + h - 2, w - 4, dk)
    sx, sy = x + 5, y + 5
    if icon == 'spark':
        for (dx, dy) in [(0, -2), (0, 2), (-2, 0), (2, 0), (0, -1), (0, 1), (-1, 0), (1, 0), (0, 0)]:
            cv.px(sx + dx, sy + dy, CREAM)
    elif icon == 'fish':
        for (dx, dy) in [(-1, -1), (0, -1), (1, -1), (-2, 0), (-1, 0), (0, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (-3, -1), (-3, 1), (-4, -2), (-4, 2)]:
            cv.px(sx + dx + 1, sy + dy, CREAM)
    cv.text(x + (10 if icon else 4), y + 1, name, CREAM, 'silkb', shadow=dd)

OLD_TAB = (C('#7a6c4a'), C('#9a8a5e'), C('#5e5238'), C('#3e3424'))      # olive cardigan name tab

@functools.lru_cache(maxsize=16)
def _old_face(face):
    from .characters import person as P
    s = P.draw(P.CAST['old_fisher'], pose='sit', arms='hold', face=face)
    return np.ascontiguousarray(s.rgba[9:41, 5:41])                       # hat + head + collar, 36 x 32

def old_portrait(cv, x, y, face='normal', W=44, H=42):
    """the old fisherman's portrait for claude_box(who='old'): a warm sunset backdrop + his pixel head (1:1)."""
    cv.rrect(x, y, W, H, OUTL, 3); cv.rrect(x + 1, y + 1, W - 2, H - 2, C('#efe5d2'), 3)
    cv.hline(x + 3, y + 1, W - 6, C('#fffaf0')); cv.rect(x + 3, y + H - 3, W - 6, 1, C('#d4c6ae'))
    sx, sy, sw, sh = x + 4, y + 4, W - 8, H - 10
    cv.rrect(sx, sy, sw, sh, C('#f2a070'), 2)
    for j in range(sh):                                                    # sky -> sun glow -> water stripes
        u = j / (sh - 1)
        col = mix(C('#c8607a'), C('#ffc47c'), min(1.0, u * 1.6)) if u < 0.62 else (C('#e88a5a') if j % 2 else C('#b8566a'))
        cv.hline(sx + 1, sy + j, sw - 2, col)
    cv.ellipse(sx + sw - 9, sy + sh * 0.55, 4, 4, C('#fff0c0'))
    f = _old_face(face)
    cv.blit(f, sx + (sw - f.shape[1]) // 2, sy + sh - f.shape[0])
    cv.rect(x + W - 10, y + H - 5, 3, 1, C('#7ee08a'))

WANG_TAB = (C('#6f7888'), C('#8e98a8'), C('#545c6c'), C('#363c4a'))      # v0.11: grey hoodie name tab (王工)

@functools.lru_cache(maxsize=32)
def _human_face(look_name, face, look=(0, 0)):
    """head-and-shoulders crop of a characters.human sitter (1:1 pixels) for a dialog portrait."""
    from .characters import human as H
    L = getattr(H, look_name)
    s = H.draw(L, face=face, arms='rest', look=look)
    a = s.body.rgba
    return np.ascontiguousarray(a[H.HY - 4:H.HY + H.HH + 6, H.HX - 4:H.HX + H.HW + 4])

def person_portrait(cv, x, y, look_name='WANG', face='normal', backdrop='night', W=44, H=42, look=(0, 0)):
    """v0.11: portrait for claude_box(who='wang' / 'wang_dusk'): a backdrop + the human head (1:1).
    backdrop: 'night' (dark office, cool laptop glow from below) | 'sunset' (same as the old man's)."""
    cv.rrect(x, y, W, H, OUTL, 3); cv.rrect(x + 1, y + 1, W - 2, H - 2, C('#efe5d2'), 3)
    cv.hline(x + 3, y + 1, W - 6, C('#fffaf0')); cv.rect(x + 3, y + H - 3, W - 6, 1, C('#d4c6ae'))
    sx, sy, sw, sh = x + 4, y + 4, W - 8, H - 10
    cv.rrect(sx, sy, sw, sh, C('#1c2340'), 2)
    for j in range(sh):
        u = j / (sh - 1)
        if backdrop == 'sunset':
            col = mix(C('#c8607a'), C('#ffc47c'), min(1.0, u * 1.6)) if u < 0.62 else (C('#e88a5a') if j % 2 else C('#b8566a'))
        else:
            col = mix(C('#141a33'), C('#2c4a7a'), u ** 1.6)
            if j % 4 == 0 and u < 0.5: col = mix(col, C('#232c4e'), 0.6)
        cv.hline(sx + 1, sy + j, sw - 2, col)
    if backdrop == 'sunset': cv.ellipse(sx + sw - 9, sy + sh * 0.55, 4, 4, C('#fff0c0'))
    else:
        for (wx, wy) in ((sx + 4, sy + 4), (sx + 8, sy + 3), (sx + sw - 7, sy + 5)): cv.px(wx, wy, C('#ffd27a'))   # far windows
    f = _human_face(look_name, face, look)
    fw, fh = f.shape[1], f.shape[0]
    cv.blit(f[:min(fh, sh)], sx + (sw - fw) // 2, sy + max(0, sh - fh) + 2)
    if backdrop != 'sunset':                                              # laptop glow on the chin
        cv.rect(sx + 1, sy + sh - 2, sw - 2, 2, (120, 180, 255, 70))
    cv.rect(x + W - 10, y + H - 5, 3, 1, C('#7ee08a'))

def _wrap2(s, avail):
    """split s at a space so the first part fits avail px (zh10) -> (line1 incl. trailing space, line2)."""
    words = s.split(' '); best = len(words) // 2
    for i in range(1, len(words)):
        if text_width(' '.join(words[:i]), 'zh10') <= avail: best = i
    return ' '.join(words[:best]) + ' ', ' '.join(words[best:])

def claude_box(cv, zh='', en='', face='normal', mouth='smile', open_t=1.0, zh_n=None, en_n=None,
               t=0.0, show_next=False, x=20, y=200, w=440, h=62, name=None, who='claude'):
    """reference-style dialog box: portrait (dot-matrix face) + name tab + typewriter text.
    who='old': the old fisherman (pixel portrait, olive OLD MAN tab; face = person face, his mouth flaps while typing).
    v0.11 who='wang' / 'wang_dusk': 王工 (human portrait on a night-office / sunset backdrop, grey WANG tab)."""
    if open_t <= 0: return
    k = ease_out(open_t)
    hh = max(6, int(round(h * k)))
    yy = y + (h - hh) // 2 + int(round((1 - k) * 6))
    cv.rrect(x + 2, yy + 3, w, hh, (20, 8, 8, 110), 3)
    bg = _box_bg(w, h)
    if hh < h:
        top = bg[:hh // 2]; bot = bg[h - (hh - hh // 2):]
        cv.blit(np.concatenate([top, bot], 0), x, yy); return
    cv.blit(bg, x, yy)
    if who in ('wang', 'wang_dusk'):
        typing = zh_n is not None and 0 < zh_n < len(zh)
        f = 'o' if typing and int(zh_n) % 2 == 1 and zh[max(0, int(zh_n) - 1)] not in '，。……？！、' else face
        person_portrait(cv, x + 7, yy + 6, 'WANG', f, 'sunset' if who == 'wang_dusk' else 'night')
        name_tab(cv, x + 9, yy + h - 8, name or 'WANG', icon=None, col=WANG_TAB)
    elif who == 'old':
        typing = zh_n is not None and 0 < zh_n < len(zh)
        f = 'talk' if typing and int(zh_n) % 2 == 1 and zh[max(0, int(zh_n) - 1)] not in '，。……？！、' else face
        old_portrait(cv, x + 7, yy + 6, f)
        name_tab(cv, x + 9, yy + h - 8, name or 'OLD MAN', icon='fish', col=OLD_TAB)
    else:
        portrait(cv, x + 7, yy + 6, face, mouth)
        name_tab(cv, x + 9, yy + h - 8, name or 'CLAUDE')
    tx = x + 60
    zs = zh if zh_n is None else zh[:max(0, int(zh_n))]
    es = en if en_n is None else en[:max(0, int(en_n))]
    if zs: cv.text(tx, yy + 12, zs, INK, 'zh12', shadow=C('#e3d2b4'))
    if es:
        # v0.7: English that does not fit wraps onto two lines (wrap decided on the FULL line so typing never re-flows)
        avail = w - (tx - x) - 10
        if text_width(en, 'zh10') <= avail:
            cv.text(tx + 1, yy + 34, es, INK2, 'zh10')
        else:
            l1, l2 = _wrap2(en, avail)
            cv.text(tx + 1, yy + 30, es[:len(l1)], INK2, 'zh10')
            if len(es) > len(l1): cv.text(tx + 1, yy + 42, es[len(l1):].lstrip(), INK2, 'zh10')
    if show_next:
        bob = 1 if (t * 3) % 1 < 0.5 else 0
        ax_, ay_ = x + w - 16, yy + h - 12 + bob
        for i in range(3): cv.hline(ax_ + i, ay_ + i, 5 - 2 * i, TC)

# ------------------------------------------------------------------ Win95
W95 = dict(face=C('#c3c3c3'), hi=C('#ffffff'), lt=C('#dfdfdf'), sh=C('#808080'), dk=C('#0a0a0a'),
           t0=C('#000080'), t1=C('#1084d0'), ti=C('#808080'), ti1=C('#b5b5b5'))

def w95_bevel(cv, x, y, w, h, raised=True):
    if raised:
        cv.hline(x, y, w - 1, W95['lt']); cv.vline(x, y, h - 1, W95['lt'])
        cv.hline(x + 1, y + 1, w - 3, W95['hi']); cv.vline(x + 1, y + 1, h - 3, W95['hi'])
        cv.hline(x, y + h - 1, w, W95['dk']); cv.vline(x + w - 1, y, h, W95['dk'])
        cv.hline(x + 1, y + h - 2, w - 2, W95['sh']); cv.vline(x + w - 2, y + 1, h - 2, W95['sh'])
    else:
        cv.hline(x, y, w - 1, W95['sh']); cv.vline(x, y, h - 1, W95['sh'])
        cv.hline(x + 1, y + 1, w - 3, W95['dk']); cv.vline(x + 1, y + 1, h - 3, W95['dk'])
        cv.hline(x, y + h - 1, w, W95['hi']); cv.vline(x + w - 1, y, h, W95['hi'])
        cv.hline(x + 1, y + h - 2, w - 2, W95['lt']); cv.vline(x + w - 2, y + 1, h - 2, W95['lt'])

def w95_button(cv, x, y, w, h, label='', pressed=False, fname='zh10'):
    cv.rect(x, y, w, h, W95['face']); w95_bevel(cv, x, y, w, h, raised=not pressed)
    if label:
        tw = text_width(label, fname); off = 1 if pressed else 0
        cv.text(x + (w - tw) // 2 + off, y + (h - 11) // 2 + off, label, W95['dk'], fname)

def w95_window(cv, x, y, w, h, title, active=True, icon=None):
    """Win95 window frame; icon: optional callable(cv, x, y) drawing a 10x10 title icon. returns the client rect."""
    cv.rect(x + 2, y + 2, w, h, (0, 0, 0, 80)); cv.rect(x, y, w, h, W95['face']); w95_bevel(cv, x, y, w, h, True)
    tx, ty, tw_, th = x + 3, y + 3, w - 6, 14
    c0, c1 = (W95['t0'], W95['t1']) if active else (W95['ti'], W95['ti1'])
    for i in range(tw_): cv.vline(tx + i, ty, th, mix(c0, c1, i / max(1, tw_ - 1)))
    if icon is not None: icon(cv, tx + 2, ty + 2); tx += 12
    cv.text(tx + 3, ty + 1, title, C('#ffffff'), 'zh10')
    bx = x + w - 5 - 11 * 3 + 2
    for i, g in enumerate(['min', 'max', 'close']):
        bxx = bx + i * 11 + (1 if g == 'close' else 0)
        w95_button(cv, bxx, ty + 3, 10, 9)
        gx, gy = bxx + 2, ty + 5; k = W95['dk']
        if g == 'min': cv.hline(gx + 1, gy + 4, 4, k)
        elif g == 'max': cv.rect(gx, gy, 6, 5, k); cv.rect(gx + 1, gy + 2, 4, 2, W95['face'])
        else:
            for d in range(5): cv.px(gx + d, gy + d, k); cv.px(gx + 4 - d, gy + d, k)
    return (x + 4, y + 19, w - 8, h - 23)

# ------------------------------------------------------------------ cartoon FX
_STAR = ["..#..", ".###.", "#####", ".###.", "#.#.#"]
def star(cv, x, y, col=GOLD, alpha=1.0, small=False):
    rows = [".#.", "###", ".#."] if small else _STAR
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == '#': cv.px(int(x) + i - len(r) // 2, int(y) + j - len(rows) // 2, _a(col, alpha))

def dizzy_stars(cv, cx, cy, t, n=3, rx=16, ry=4, speed=2.2, alpha=1.0):
    """stars orbiting a point (UI coords) - e.g. after a bonk on the head."""
    for i in range(n):
        a = 2 * math.pi * (t * speed + i / n)
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        front = math.sin(a) > 0
        star(cv, x, y, GOLD if front else GOLD_D, alpha, small=not front)

def burst_lines(cv, cx, cy, r0, r1, n=10, col=CREAM, alpha=1.0, rot=0.0):
    """comic impact lines radiating from (cx, cy)."""
    for i in range(n):
        a = rot + 2 * math.pi * i / n
        cv.line(int(cx + r0 * math.cos(a)), int(cy + r0 * math.sin(a)), int(cx + r1 * math.cos(a)), int(cy + r1 * math.sin(a)), _a(col, alpha))


# ------------------------------------------------------------------ generic helpers
def blit_scaled(cv, rgba, cx, cy, s=1.0, alpha=1.0):
    """paste an RGBA sprite scaled (nearest) around its centre (pop-ins, fly-to-HUD shrink ...)."""
    import cv2
    if s <= 0.01 or alpha <= 0: return
    h, w = rgba.shape[:2]
    if abs(s - 1) > 1e-3:
        nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
        rgba = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_NEAREST)
    h, w = rgba.shape[:2]
    cv.blit(rgba, int(round(cx - w / 2)), int(round(cy - h / 2)), alpha_mul=alpha)

def hud_popup(label, value, sub=None, w=None):
    """big centred HUD panel (e.g. '今日已处理' + 3,000,000,000) as an RGBA sprite -> blit_scaled() it."""
    vs = value if isinstance(value, str) else fmt_int(value)
    vw = text_width(vs, 'p2p') * 2
    W_ = w or max(200, vw + 44); H_ = 54 if sub is None else 64
    cv = Canvas(W_ + 3, H_ + 3)
    cv.rrect(2, 3, W_, H_, (0, 0, 0, 110), 3)
    cv.rrect(0, 0, W_, H_, GOLD_D, 3); cv.rrect(1, 1, W_ - 2, H_ - 2, GOLD, 3)
    cv.rrect(3, 3, W_ - 6, H_ - 6, NAVY, 2); cv.hline(5, 4, W_ - 10, NAVY2)
    lw = text_width(label, 'zh12')
    cv.text((W_ - lw) // 2 + 6, 7, label, CREAM, 'zh12', shadow=(0, 0, 0, 255))
    cv.blit(COIN[0], (W_ - lw) // 2 - 8, 10)
    big_text(cv, (W_ - vw) // 2, 25, vs, GOLD, 'p2p', 2, shadow=(0, 0, 0, 255))
    if sub:
        sw = text_width(sub, 'silkb'); cv.text((W_ - sw) // 2, H_ - 13, sub, C('#ffe9a8'), 'silkb')
    return cv.a

# ------------------------------------------------------------------ Win95 extras
CURSOR_ROWS = [
    "#.......", "##......", "#o#.....", "#oo#....", "#ooo#...", "#oooo#..", "#ooooo#.", "#oooooo#",
    "#ooo####", "#o#oo#..", "##.#oo#.", "#...#o#.", "....#oo#", ".....##.",
]
_CUR = None
def cursor(cv, x, y, pressed=False, age_press=None):
    """Win95 arrow cursor with its hot-spot at (x, y). age_press: seconds since a click -> small click ring."""
    global _CUR
    if _CUR is None: _CUR = sprite(CURSOR_ROWS, {'#': C('#0a0a0a'), 'o': C('#ffffff')})
    xi, yi = int(round(x)), int(round(y)) + (1 if pressed else 0)
    if age_press is not None and 0 <= age_press < 0.22:
        r = 2 + age_press / 0.22 * 9; a = 1 - age_press / 0.22
        for k in range(16):
            an = k / 16 * 2 * math.pi
            cv.px(int(round(x + r * math.cos(an))), int(round(y + r * math.sin(an))), (255, 255, 255, int(220 * a)))
    cv.blit(_CUR, xi, yi)

def w95_panel(cv, x, y, w, h, fill=None):
    """sunken white panel (list views, result boxes)."""
    cv.rect(x, y, w, h, fill or C('#ffffff')); w95_bevel(cv, x, y, w, h, raised=False)

def w95_field(cv, x, y, w, h, text='', caret=False, fname='zh12', col=None):
    """sunken text field; returns the caret x."""
    w95_panel(cv, x, y, w, h)
    tx = x + 4; ty = y + (h - (13 if fname == 'zh12' else 11)) // 2 + 1
    if text: cv.text(tx, ty, text, col or W95['dk'], fname)
    cx = tx + (text_width(text, fname) + 1 if text else 0)
    if caret: cv.vline(cx, y + 3, h - 6, W95['dk'])
    return cx

def highlight(cv, x, y, w, h, u=1.0, col=C('#ffd23f'), alpha=0.85, seed=0):
    """highlighter-marker sweep (draw it BEFORE the text it marks). u: 0..1 progress left -> right."""
    if u <= 0: return
    ww = int(round(w * min(1.0, u)))
    rng = np.random.default_rng(seed)
    jt = rng.integers(0, 2, ww + 2); jb = rng.integers(0, 2, ww + 2)
    for i in range(ww):
        cv.blend_rect(x + i, y + int(jt[i]), x + i + 1, y + h - int(jb[i]), (col[0], col[1], col[2], int(255 * alpha)))

def w95_open_fx(cv, src, dst, k, n=3, col=(30, 30, 30, 210)):
    """Win95 'zoom rectangles' window-open animation from rect src to rect dst, k 0..1 (+ trailing copies)."""
    for j in range(n):
        kk = max(0.0, min(1.0, k * (1 + 0.15 * (n - 1)) - j * 0.15))
        if kk <= 0: continue
        r = [src[i] + (dst[i] - src[i]) * kk for i in range(4)]
        x, y, w, h = [int(round(v)) for v in r]
        for xx in range(x, x + w, 2): cv.px(xx, y, col); cv.px(xx, y + h - 1, col)
        for yy in range(y, y + h, 2): cv.px(x, yy, col); cv.px(x + w - 1, yy, col)

# ------------------------------------------------------------------ rubber stamp
STAMP_RED = C('#d6372d')

@functools.lru_cache(maxsize=64)
def stamp_sprite(text, fname='zh8', scale=1, col=STAMP_RED, angle=0.0, seed=0, border=1, padx=3, pady=2, wear=0.10, rings=2,
                 ink=235, bold=False):
    """red ink rubber stamp: double rounded border + text, worn ink (deterministic), rotated (nearest)."""
    import cv2
    m = text_mask(text, fname)
    if bold:                                   # pixel faux-bold: thicken strokes by one native px (right + down)
        m = np.pad(m, ((0, 1), (0, 1))); mb = m.copy(); mb[:, 1:] |= m[:, :-1]; mb[1:, :] |= m[:-1, :]; m = mb
    if scale > 1: m = np.repeat(np.repeat(m, scale, 0), scale, 1)
    th, tw = m.shape
    bw = ((2 + border) if rings == 2 else border) * scale
    W_ = tw + 2 * (padx * scale + bw); H_ = th + 2 * (pady * scale + bw)
    def rr(i, r):
        t = Canvas(W_, H_); o = i * scale
        t.rrect(o, o, W_ - 2 * o, H_ - 2 * o, (255, 255, 255, 255), r); return t.a[..., 3] > 0
    ring = rr(0, 2 * scale) & ~rr(border, 2 * scale)
    if rings == 2: ring |= rr(border + 1, scale) & ~rr(border + 2, scale)
    cv = Canvas(W_, H_)
    cv.a[ring] = col
    cv._mask(m, (W_ - tw) // 2, (H_ - th) // 2, col)
    a = cv.a
    rng = np.random.default_rng(seed + 991)
    if wear > 0:      # worn ink: speckle dropouts + lighter blotches
        hole = rng.random(a.shape[:2]) < wear
        blob = cv2.GaussianBlur(rng.random(a.shape[:2]).astype(np.float32), (0, 0), 1.6 * scale) > 0.56
        a[hole & (a[..., 3] > 0), 3] = 0
        lt = blob & (a[..., 3] > 0)
        a[lt, :3] = (a[lt, :3].astype(np.float32) * 0.8 + 255 * 0.2).astype(np.uint8)
        a[lt, 3] = 200
    a[a[..., 3] == 255, 3] = ink
    if abs(angle) > 1e-3:
        d = int(np.ceil(np.hypot(W_, H_))) + 2
        big = np.zeros((d, d, 4), np.uint8); ox, oy = (d - W_) // 2, (d - H_) // 2
        big[oy:oy + H_, ox:ox + W_] = a
        M = cv2.getRotationMatrix2D((d / 2, d / 2), angle, 1.0)
        a = cv2.warpAffine(big, M, (d, d), flags=cv2.INTER_NEAREST, borderValue=(0, 0, 0, 0))
        ys, xs = np.nonzero(a[..., 3])
        a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy()
    return a

def rubber_stamp(cv, cx, cy, text, age, fname='zh8', scale=1, col=STAMP_RED, angle=0.0, seed=0, slam=0.07, from_s=1.8,
                 alpha=1.0, splat=False, rings=2, wear=0.10, padx=3, pady=2, bold=False):
    """stamp slammed down at age 0 (centre cx, cy): drops in scaled from_s -> 1 during `slam` seconds, then sticks.
    returns impact strength 0..1 (1 at the moment of contact) to drive shakes / SFX.
    LEGIBILITY (CJK): keep |angle| <= 5 and bold=False, wear<=0.04; zh10 at scale 3 reads best. Bigger angles
    (nearest-neighbour rotation) and bold shred pixel glyphs into noise."""
    if age < -slam: return 0.0
    spr = stamp_sprite(text, fname, scale, col, float(round(angle, 2)), seed, padx=padx, pady=pady, wear=wear, rings=rings,
                       bold=bold)
    if age < 0:
        u = 1 + age / slam                      # 0 -> 1 as it comes down
        s = from_s + (1 - from_s) * u * u
        blit_scaled(cv, spr, cx, cy - 2 * (1 - u), s, alpha * (0.25 + 0.35 * u))
        return 0.0
    s = 1.0 + 0.06 * max(0.0, 1 - age / 0.05)
    blit_scaled(cv, spr, cx, cy, s, alpha)
    if splat and age < 0.12:
        r = 0.55 * max(spr.shape[:2]) + 40 * age; a = 1 - age / 0.12
        for k in range(12):
            an = k / 12 * 2 * math.pi + seed
            cv.px(int(cx + math.cos(an) * r), int(cy + math.sin(an) * r * 0.7), (col[0], col[1], col[2], int(255 * a)))
    return max(0.0, 1 - age / 0.12)

# ------------------------------------------------------------------ calendar month grid
WEEK_ZH = '一二三四五六日'
def month_info(year, month):
    """(weekday of the 1st, Monday = 0, number of days)."""
    import calendar
    return calendar.monthrange(year, month)

def cal_cells(x, y, year, month, cw, ch, gap=1, header_h=12):
    """{day: (x, y, w, h)} for a Monday-first month grid whose header row starts at (x, y)."""
    wd0, nd = month_info(year, month)
    out = {}
    for d in range(1, nd + 1):
        i = wd0 + d - 1; r, c = divmod(i, 7)
        out[d] = (x + c * (cw + gap), y + header_h + r * (ch + gap), cw, ch)
    return out

def cal_grid(cv, x, y, year, month, cw=38, ch=21, gap=1, header_h=12, fill=C('#ffffff'), weekend_fill=C('#fff0ec'),
             ink=C('#1a1a1a'), red=C('#c8352c'), grid=C('#c9c9c9'), fname='p2p', today=None):
    """Monday-first month grid: weekday header (一 … 日, 六/日 red) + numbered cells.  returns cal_cells(...)."""
    cells = cal_cells(x, y, year, month, cw, ch, gap, header_h)
    for c, d in enumerate(WEEK_ZH):
        tw = text_width(d, 'zh10')
        cv.text(x + c * (cw + gap) + (cw - tw) // 2, y, d, red if c >= 5 else ink, 'zh10')
    rows = max((v[1] - y - header_h) // (ch + gap) for v in cells.values()) + 1
    cv.rect(x - gap, y + header_h - gap, 7 * (cw + gap) + gap, rows * (ch + gap) + gap, grid)
    wd0, nd = month_info(year, month)
    for r in range(rows):
        for c in range(7):
            cv.rect(x + c * (cw + gap), y + header_h + r * (ch + gap), cw, ch, weekend_fill if c >= 5 else C('#f4f4f4'))
    for d, (cx, cy, w, h) in cells.items():
        c = (wd0 + d - 1) % 7
        cv.rect(cx, cy, w, h, weekend_fill if c >= 5 else fill)
        if today == d: cv.rect(cx, cy, w, h, C('#dfe8ff'))
        cv.text(cx + 2, cy + 2, str(d), red if c >= 5 else ink, fname)
    return cells


# ---------------------------------------------------------------- chat feed / fast-forward badge (from ACT I)
def chat_msg_h(m):
    """height of one chat message dict (lines + optional name row)."""
    return len(m['lines']) * 12 + 8 + (9 if m.get('name') else 0)


def chat_feed(cv, t, msgs, x, fast_lift=0.12, slow_lift=0.22, alpha_mul=1.0, gap=4, out_dur=0.25):
    """Scrolling chat feed.  msgs: list of dicts
         t_in, t_out, lines(list[str]), avatar('#hex'), name(str|None), group(any), bot(y of bubble bottom), fast(bool)
       Each message is lifted by the *later messages of its own group* (so several feeds can share one list),
       fades + drifts up 10px over out_dur after t_out."""
    from .anim import ease_out3, ramp
    for m in msgs:
        age = t - m['t_in']
        if age < 0: continue
        alpha = (1.0 - ramp(t, m['t_out'], m['t_out'] + out_dur)) * alpha_mul
        if alpha <= 0.01: continue
        lift = 0.0
        for n in msgs:
            if n is m or n.get('group') != m.get('group') or n['t_in'] <= m['t_in'] or t <= n['t_in']: continue
            lt = fast_lift if n.get('fast') else slow_lift
            lift += ease_out3((t - n['t_in']) / lt) * (chat_msg_h(n) + gap)
        lift += 10 * ramp(t, m['t_out'], m['t_out'] + out_dur)
        y = m['bot'] - chat_msg_h(m) - lift
        if y < -40: continue
        k = pop_k(age, 1e9, t_in=0.10 if m.get('fast') else 0.16)
        chat_bubble(cv, x, int(round(y)), m['lines'], avatar=m['avatar'], k=k, name=m.get('name'), alpha=alpha)


def ff_badge(cv, x, y, t, alpha=1.0, label='x 180'):
    """fast-forward ▶▶ HUD badge for time-lapses (60x16, blinking gold arrows)."""
    if alpha <= 0: return
    _hud_panel(cv, x, y, 60, 16, alpha)
    col = _a(GOLD if (t * 4) % 1 < 0.6 else C('#fff3df'), alpha)
    for k in range(2):
        bx = x + 6 + k * 7
        for i in range(5):
            hh = 9 - 2 * i
            if hh > 0: cv.vline(bx + i, y + 4 + i, hh, col)
    cv.text(x + 24, y + 5, label, _a(C('#fff3df'), alpha), 'silkb')


def narration(cv, t, boxes):
    """draw the active claude_box from prepared narration boxes (see anim.boxes_prep / box_at).
       Audio side: for each line call cues.voice_line(times=ln['times'], ...)."""
    from .anim import box_at
    r = box_at(t, boxes)
    if r is None: return
    bx, ln, k, zn, en_n = r
    if k <= 0: return
    claude_box(cv, ln['zh'], ln['en'], ln['face'], ln.get('mouth', 'flat'), open_t=k, zh_n=zn, en_n=en_n, t=t,
               show_next=t > ln['t_end'] + 0.35, who=ln.get('who', 'claude'))


# ------------------------------------------------------------------ ACT II widgets (forms, system UI, cards)
def w95_checkbox(cv, x, y, checked=False, label='', fname='zh10', hover=False, check_k=1.0):
    """9x9 sunken Win95 checkbox + label; check_k 0..1 draws the tick stroke progressively. returns label end x."""
    cv.rect(x, y, 9, 9, C('#ffffff') if not hover else C('#fff7d0')); w95_bevel(cv, x, y, 9, 9, raised=False)
    if checked and check_k > 0:
        pts = [(2, 4), (3, 5), (4, 6), (5, 5), (6, 4), (7, 3)]
        n = max(1, int(round(len(pts) * min(1.0, check_k))))
        for (px, py) in pts[:n]:
            cv.px(x + px, y + py - 1, W95['dk']); cv.px(x + px, y + py, W95['dk'])
    if label:
        cv.text(x + 12, y - 2, label, W95['dk'], fname)
        return x + 12 + text_width(label, fname)
    return x + 9

def w95_progress(cv, x, y, w, h, u, seg=6, gap=2, col=C('#000080'), marquee=None):
    """classic segmented progress bar in a sunken trough. u 0..1.  marquee=t -> bouncing 'busy' blocks."""
    w95_panel(cv, x, y, w, h, fill=W95['face'])
    ix, iy, iw, ih = x + 2, y + 2, w - 4, h - 4
    if marquee is not None:
        n = 4; span = iw - n * (seg + gap)
        p = (math.sin(marquee * 2.6) * 0.5 + 0.5) * span
        for i in range(n): cv.rect(int(ix + p + i * (seg + gap)), iy, seg, ih, col)
        return
    fill_w = int(round(iw * max(0.0, min(1.0, u))))
    xx = ix
    while xx + seg <= ix + fill_w:
        cv.rect(xx, iy, seg, ih, col); xx += seg + gap
    if xx < ix + fill_w: cv.rect(xx, iy, ix + fill_w - xx, ih, col)

def tooltip(cv, x, y, text, alpha=1.0, fname='zh10'):
    """Win95 yellow tooltip, top-left at (x, y)."""
    if alpha <= 0: return
    tw = text_width(text, fname); w, h = tw + 8, 14
    cv.rect(x + 1, y + 1, w, h, (0, 0, 0, int(70 * alpha)))
    cv.rect(x, y, w, h, _a(C('#0a0a0a'), alpha)); cv.rect(x + 1, y + 1, w - 2, h - 2, _a(C('#ffffe1'), alpha))
    cv.text(x + 4, y + 1, text, _a(C('#0a0a0a'), alpha), fname)

def toast(cv, x_right, y_bottom, title, body, k=1.0, icon_col=C('#d97757'), w=None, alpha=1.0):
    """system notification sliding up from the bottom-right; k 0..1 slide (use pop/ramp)."""
    if k <= 0 or alpha <= 0: return
    tw = max(text_width(title, 'zh8'), text_width(body, 'zh10'))
    w = w or tw + 34; h = 30
    x = x_right - w; y = int(round(y_bottom - h * min(1.0, k) - 4))
    cv.rrect(x + 2, y + 2, w, h, (0, 0, 0, int(90 * alpha)), 3)
    cv.rrect(x, y, w, h, _a(C('#14131c'), alpha), 3); cv.rrect(x + 1, y + 1, w - 2, h - 2, _a(C('#2a2838'), alpha), 3)
    cv.hline(x + 3, y + 1, w - 6, _a(C('#45425a'), alpha))
    ic = C(icon_col) if isinstance(icon_col, str) else icon_col
    cv.rrect(x + 6, y + 7, 16, 16, _a(ic, alpha), 4)
    W_ = _a(C('#fff4ea'), alpha); cxx, cyy = x + 13, y + 14
    cv.vline(cxx, cyy - 4, 9, W_); cv.hline(cxx - 4, cyy, 9, W_)
    for d in (-2, 2):
        cv.px(cxx + d, cyy - 2, W_); cv.px(cxx + d, cyy + 2, W_)
    cv.text(x + 27, y + 3, title, _a(C('#a9a6c0'), alpha), 'zh8')
    cv.text(x + 27, y + 14, body, _a(C('#ffffff'), alpha), 'zh10')

def hud_notify(cv, x, y, title='工作群', body='3 条新消息', k=1.0, alpha=1.0, icon_col=C('#d97757'), dot=True):
    """v0.7: a small notification chip that drops in just under the HUD clock (top-left); k 0..1 = drop-in (use
    ease_out of a 0.25 s ramp), alpha = fade.  '工作群 · 3 条新消息' style: coral chat icon, grey title, white body."""
    if k <= 0 or alpha <= 0: return
    a = alpha * min(1.0, k * 1.5)
    s = title + ' · ' + body
    w = text_width(s, 'zh10') + 26; h = 17
    yy = int(round(y - 6 * (1 - ease_out(k))))
    cv.rrect(x + 1, yy + 2, w, h, (0, 0, 0, int(90 * a)), 3)
    cv.rrect(x, yy, w, h, _a(C('#14131c'), a), 3); cv.rrect(x + 1, yy + 1, w - 2, h - 2, _a(C('#2a2838'), a), 3)
    cv.hline(x + 3, yy + 1, w - 6, _a(C('#45425a'), a))
    ic = C(icon_col) if isinstance(icon_col, str) else icon_col
    cv.rrect(x + 4, yy + 3, 13, 10, _a(ic, a), 3); cv.px(x + 6, yy + 13, _a(ic, a)); cv.px(x + 5, yy + 14, _a(ic, a))
    W_ = _a(C('#fff4ea'), a)
    for d in (7, 10, 13): cv.px(x + d, yy + 8, W_)
    if dot: cv.rect(x + 15, yy + 1, 3, 3, _a(C('#ff5a4a'), a))
    tw = text_width(title + ' · ', 'zh10')
    cv.text(x + 21, yy + 3, title + ' · ', _a(C('#a9a6c0'), a), 'zh10')
    cv.text(x + 21 + tw, yy + 3, body, _a(C('#ffffff'), a), 'zh10')

STATUS = {'online': ('#4fe07a', '在线'), 'away': ('#ffc04a', '离开'), 'busy': ('#ff5a4a', '忙碌'),
          'off': ('#8a8aa0', '休假中'), 'offline': ('#6a6a7a', '离线')}
def status_badge(cv, x_right, y, state='online', label=None, alpha=1.0, pulse=0.0, flip=1.0):
    """HUD-style status pill '● 在线' (right-aligned).  flip 0..1 squashes vertically for a state change."""
    if alpha <= 0: return
    col, lab = STATUS.get(state, STATUS['online']); label = label or lab
    tw = text_width(label, 'zh10'); w, h = tw + 20, 15
    x = x_right - w
    hh = max(1, int(round(h * flip))); yy = y + (h - hh) // 2
    cv.rrect(x + 1, yy + 2, w, hh, (0, 0, 0, int(90 * alpha)), 2)
    cv.rrect(x, yy, w, hh, _a(GOLD_D, alpha), 2); cv.rrect(x + 1, yy + 1, w - 2, max(1, hh - 2), _a(NAVY, alpha * 0.92), 2)
    if flip > 0.7:
        c = C(col)
        if pulse > 0: cv.ellipse(x + 8, y + 7, 4.5 + pulse, 4.5 + pulse, (c[0], c[1], c[2], int(90 * alpha * pulse)))
        for j, row in enumerate(('.###.', '#####', '#####', '#####', '.###.')):
            for i, ch in enumerate(row):
                if ch == '#': cv.px(x + 6 + i, y + 5 + j, _a(mix(c, C('#ffffff'), 0.45) if (i, j) == (1, 1) else c, alpha))
        cv.text(x + 14, y + 2, label, _a(CREAM, alpha), 'zh10')

def name_card(cv, x, y, name, role='', sub='', k=1.0, alpha=1.0, accent=GOLD):
    """lower-third character card sliding in from the left (k 0..1)."""
    if k <= 0 or alpha <= 0: return
    w1 = text_width(name, 'zh12'); w2 = text_width(role, 'zh10') if role else 0; w3 = text_width(sub, 'zh8') if sub else 0
    w = max(w1 + w2 + 22, w3 + 16, 90); h = 34 if sub else 22
    xx = int(round(x - (w + 20) * (1 - min(1.0, k))))
    cv.rect(xx + 2, y + 2, w, h, (0, 0, 0, int(100 * alpha)))
    cv.rect(xx, y, w, h, _a(NAVY, alpha * 0.94)); cv.rect(xx, y, 3, h, _a(accent, alpha))
    cv.hline(xx + 3, y, w - 3, _a(NAVY2, alpha)); cv.hline(xx + 3, y + h - 1, w - 3, _a(GOLD_D, alpha))
    cv.text(xx + 9, y + 3, name, _a(CREAM, alpha), 'zh12', shadow=_a(C('#000000'), alpha))
    if role: cv.text(xx + 15 + w1, y + 5, role, _a(GOLD, alpha), 'zh10')
    if sub: cv.text(xx + 9, y + 21, sub, _a(C('#ffb59a'), alpha), 'zh8')

def chapter_banner(cv, t, zh, en, t0, t1, y=96, w=300):
    """chapter ribbon: unrolls from the centre at t0, holds, folds away by t1.  zh drawn x2 in gold."""
    if not (t0 <= t < t1): return
    u_in = ease_out((t - t0) / 0.38); u_out = max(0.0, min(1.0, (t - (t1 - 0.32)) / 0.32))
    k = u_in * (1 - u_out ** 2)
    if k <= 0.01: return
    ww = int(round(w * k)); cx = UW // 2; x = cx - ww // 2; h = 46
    a = 1.0 - u_out
    cv.rect(x + 3, y + 3, ww, h, (0, 0, 0, int(110 * a)))
    cv.rect(x, y, ww, h, _a(NAVY, 0.95 * a)); cv.hline(x, y + 2, ww, _a(GOLD_D, a)); cv.hline(x, y + h - 3, ww, _a(GOLD_D, a))
    cv.hline(x, y, ww, _a(GOLD, a)); cv.hline(x, y + h - 1, ww, _a(GOLD, a))
    for sx in (x - 6, x + ww):            # swallow-tail ends
        for i in range(6):
            d = i if sx < cx else 5 - i
            cv.vline(sx + i, y + 4 + d, h - 8 - 2 * d, _a(TC_D, a))
    if k > 0.85:
        tk = min(1.0, (t - t0 - 0.30) / 0.25)
        if tk > 0:
            m = text_mask(zh, 'zh12'); tw = m.shape[1] * 2
            big_text(cv, cx - tw // 2, y + 5, zh, GOLD, 'zh12', 2, shadow=C('#3b2620'), alpha=a * tk)
            ew = text_width(en, 'silkb')
            cv.text(cx - ew // 2, y + 33, en, _a(CREAM, a * tk), 'silkb')
        # sparkle sweep across the ribbon
        sx = x + int((t - t0 - 0.4) / 0.6 * ww)
        if x < sx < x + ww:
            for i in range(h - 6):
                cv.px(sx - i // 3, y + 3 + i, (255, 240, 200, int(90 * a)))


# ------------------------------------------------------------------ RPG quest tracker (ACT III)
QUEST_RED = C('#e0483c'); QUEST_GREEN = C('#5fd07a')

def _quest_icon(cv, x, y, col, alpha=1.0, mark='!'):
    """9x11 gold diamond badge with a '!' (or '✓' / 'x')."""
    rows = ['....#....', '...###...', '..#####..', '.#######.', '#########', '#########', '#########', '.#######.',
            '..#####..', '...###...', '....#....']
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == '#':
                edge = i in (0, 8) or j in (0, 10) or r[max(0, i - 1)] == '.' or r[min(8, i + 1)] == '.'
                cv.px(x + i, y + j, _a(GOLD_D if edge else col, alpha))
    ink = _a(NAVY, alpha)
    if mark == '!':
        cv.vline(x + 4, y + 2, 5, ink); cv.px(x + 4, y + 8, ink)
    elif mark == 'v':
        for (i, j) in ((2, 5), (3, 6), (4, 7), (5, 6), (6, 5), (7, 4)): cv.px(x + i, y + j, ink)
    else:
        for d in range(5): cv.px(x + 2 + d, y + 3 + d, ink); cv.px(x + 6 - d, y + 3 + d, ink)

def quest_bar(cv, t, t0, title='学会休息', progress=(0, 1), kind='主线任务', kind_en='MAIN QUEST', state='active',
              t_state=None, y=6, x_center=None, alpha=1.0, slide=0.42, new_tag=True):
    """RPG quest tracker panel, centred at the top of the 480x270 UI canvas.
         [◆!]  主线任务 MAIN QUEST
               学会休息            0/1
    - slides down from above at t0 (back_out), a gold sparkle sweeps across and a '新任务' tag blinks for ~1.4 s.
    - state 'active' | 'fail' (red flash + shake at t_state, title struck through, '失败') | 'done' (green ✓, 1/1).
    returns the panel rect (x, y, w, h) (e.g. to anchor achievements under it)."""
    if t < t0 or alpha <= 0: return None
    u = (t - t0) / slide
    k = back_out(min(1.0, u), 1.4) if u < 1 else 1.0
    tw = text_width(title, 'zh12'); kw = text_width(kind, 'zh8') + 4 + text_width(kind_en, 'silkb')
    ptxt = f'{progress[0]}/{progress[1]}'; pw = text_width(ptxt, 'p2p')
    w = max(tw + pw + 44, kw + 30, 150); h = 34
    xc = UW // 2 if x_center is None else x_center
    x = int(round(xc - w / 2)); yy = int(round(y - (h + y + 4) * (1 - k)))
    age_s = (t - t_state) if (t_state is not None and t >= t_state) else None
    st = state if age_s is not None or t_state is None else 'active'
    if st == 'fail' and age_s is not None and age_s < 0.45:          # hit shake
        x += int(round(math.sin(age_s * 70) * 3 * (1 - age_s / 0.45)))
    _hud_panel(cv, x, yy, w, h, alpha)
    accent = GOLD if st == 'active' else (QUEST_RED if st == 'fail' else QUEST_GREEN)
    cv.rect(x + 1, yy + 1, 2, h - 2, _a(accent, alpha))                 # left accent stripe
    _quest_icon(cv, x + 7, yy + 6, accent if st != 'active' else GOLD, alpha,
                {'active': '!', 'fail': 'x', 'done': 'v'}[st])
    cv.text(x + 21, yy + 1, kind, _a(accent if st != 'active' else GOLD, alpha), 'zh8')
    cv.text(x + 21 + text_width(kind, 'zh8') + 4, yy + 3, kind_en, _a(C('#c8b88a'), alpha), 'silkb')
    tcol = CREAM if st != 'fail' else C('#b8aab0')
    cv.text(x + 21, yy + 14, title, _a(tcol, alpha), 'zh12', shadow=_a(C('#000000'), alpha))
    if st == 'fail':
        sk = min(1.0, age_s / 0.2) if age_s is not None else 1.0
        cv.hline(x + 20, yy + 23, int((tw + 2) * sk), _a(QUEST_RED, alpha))
    pc = GOLD if st == 'active' else (QUEST_RED if st == 'fail' else QUEST_GREEN)
    cv.text(x + w - 7 - pw, yy + 20, ptxt, _a(pc, alpha), 'p2p', shadow=_a(C('#000000'), alpha))
    # progress pips under the counter
    n = max(1, progress[1]); pipw = max(3, min(10, (pw + 2) // n - 1))
    for i in range(n):
        px_ = x + w - 7 - pw + i * (pipw + 1)
        cv.rect(px_, yy + 29, pipw, 2, _a(pc if i < progress[0] else NAVY2, alpha))
    # entrance flourish: sparkle sweep + blinking 新任务 tag
    a_in = t - t0 - slide * 0.7
    if 0 < a_in < 0.6:
        sx = x + int(a_in / 0.6 * (w + 20)) - 10
        for i in range(h - 4):
            xx = sx - i // 3
            if x + 2 < xx < x + w - 2: cv.px(xx, yy + 2 + i, (255, 240, 200, int(110 * alpha)))
    if new_tag and st == 'active' and 0 < t - t0 - slide * 0.5 < 1.6 and int((t - t0) * 5) % 2 == 0:
        lab = '新任务'; lw = text_width(lab, 'zh8') + 6
        tx, ty = x + w - lw + 4, yy - 5
        cv.rect(tx, ty, lw, 11, _a(QUEST_RED, alpha)); cv.hline(tx, ty, lw, _a(C('#ff8a7a'), alpha))
        cv.text(tx + 3, ty - 1, lab, _a(CREAM, alpha), 'zh8')
    if st == 'fail' and age_s is not None:
        a = min(1.0, age_s / 0.12)
        if age_s < 0.2:
            cv.rect(x, yy, w, h, (224, 72, 60, int(120 * (1 - age_s / 0.2) * alpha)))
        lab = '失败'; lw = text_width(lab, 'zh10') + 8
        cv.rect(x + w - lw - 36, yy + 15, lw, 14, _a(QUEST_RED, alpha * a))
        cv.text(x + w - lw - 32, yy + 15, lab, _a(CREAM, alpha * a), 'zh10')
    return (x, yy, w, h)


# ------------------------------------------------------------------ achievement toast / HUD banner (ACT III)
TROPHY_ROWS = ["#########", "#ooooooo#", ".#ooooo#.", ".#oo+oo#.", "..#ooo#..", "...#o#...", "...#o#...", "..#####..",
               ".#######."]

def trophy(cv, x, y, alpha=1.0, col=GOLD):
    """9x9 gold cup."""
    for j, r in enumerate(TROPHY_ROWS):
        for i, ch in enumerate(r):
            if ch == '#': cv.px(x + i, y + j, _a(GOLD_D, alpha))
            elif ch == 'o': cv.px(x + i, y + j, _a(col if i < 5 else mix(col, GOLD_D, 0.35), alpha))
            elif ch == '+': cv.px(x + i, y + j, _a(C('#fff6d0'), alpha))
    for (i, j) in ((-1, 1), (-2, 2), (-1, 3), (9, 1), (10, 2), (9, 3)): cv.px(x + i, y + j, _a(GOLD_D, alpha))

def achievement(cv, t, t0, title, sub='', label='成就解锁', label_en='ACHIEVEMENT UNLOCKED', life=2.6, y=200,
                x_center=None, alpha=1.0):
    """console-style achievement toast: a round trophy badge pops in, the pill unrolls to the right,
    gold shimmer sweep; folds back at t0 + life.  Returns the rect or None."""
    age = t - t0
    if age < 0 or age > life or alpha <= 0: return None
    tw = max(text_width(title, 'zh12'), text_width(label, 'zh8') + 4 + text_width(label_en, 'silkb'),
             text_width(sub, 'zh8') if sub else 0)
    W_, H_ = tw + 44, (40 if sub else 34)
    xc = UW // 2 if x_center is None else x_center
    x0 = int(round(xc - W_ / 2))
    kb = back_out(min(1.0, age / 0.22), 2.2)                          # badge pop
    ku = ease_out((age - 0.18) / 0.32)                               # pill unroll
    kout = max(0.0, min(1.0, (age - (life - 0.3)) / 0.3))
    ku *= 1 - kout; kb *= 1 - max(0.0, (age - (life - 0.12)) / 0.12)
    ww = int(round(17 + (W_ - 17) * ku))
    if ww > 18:
        cv.rrect(x0 + 2, y + 3, ww, H_, (0, 0, 0, int(110 * alpha)), 16)
        cv.rrect(x0, y, ww, H_, _a(GOLD_D, alpha), 16)
        cv.rrect(x0 + 1, y + 1, ww - 2, H_ - 2, (NAVY[0], NAVY[1], NAVY[2], int(240 * alpha)), 16)
        cv.hline(x0 + 14, y + 2, ww - 28, _a(NAVY2, alpha))
        if ku > 0.9:
            a2 = alpha * min(1.0, (age - 0.45) / 0.15) if age > 0.45 else 0.0
            if a2 > 0:
                cv.text(x0 + 34, y + 3, label, _a(GOLD, a2), 'zh8')
                cv.text(x0 + 38 + text_width(label, 'zh8'), y + 5, label_en, _a(C('#c8b88a'), a2), 'silkb')
                cv.text(x0 + 34, y + (14 if not sub else 13), title, _a(CREAM, a2), 'zh12', shadow=_a(C('#000000'), a2))
                if sub: cv.text(x0 + 34, y + 28, sub, _a(C('#ffd9a0'), a2), 'zh8')
            sx = x0 + int((age - 0.5) / 0.5 * (ww + 30)) - 15            # shimmer
            for i in range(H_ - 4):
                xx = sx - i // 2
                if x0 + 8 < xx < x0 + ww - 8: cv.px(xx, y + 2 + i, (255, 240, 200, int(120 * alpha)))
    if kb > 0.02:                                                    # round badge on the left
        r = 15 * kb; cx_, cy_ = x0 + 17, y + H_ // 2
        cv.ellipse(cx_, cy_, r + 1, r + 1, _a(GOLD_D, alpha)); cv.ellipse(cx_, cy_, r, r, _a(GOLD, alpha))
        cv.ellipse(cx_, cy_, r * 0.8, r * 0.8, _a(NAVY, alpha))
        if kb > 0.8: trophy(cv, cx_ - 4, cy_ - 5, alpha)
        if age < 0.5:
            burst_lines(cv, cx_, cy_, 17 + age * 30, 21 + age * 40, n=10, col=GOLD, alpha=alpha * (1 - age / 0.5))
    return (x0, y, W_, H_)

HOLO_C = C('#6ad8ff'); HOLO_L = C('#bff4ff'); OK_G = C('#5fd07a')

def hud_banner(cv, t, t0, text, sub=None, progress=None, state='run', t_state=None, t1=None, y=10, x_center=None,
               alpha=1.0, accent=HOLO_C, fname='zh12'):
    """thin sci-fi / system banner at the top: '◇ 路线规划中...' with a marquee or progress bar.
    state 'run' (spinner + animated dots) -> 'ok' at t_state (green flash + check).  t1: slides away."""
    if t < t0 or alpha <= 0: return None
    if t1 is not None and t > t1 + 0.3: return None
    k = ease_out((t - t0) / 0.25)
    if t1 is not None and t > t1: k *= 1 - ease_out((t - t1) / 0.3)
    ok = t_state is not None and t >= t_state and state == 'ok'
    acc = OK_G if ok else accent
    dots = '' if ok else '.' * (int((t - t0) * 4) % 4)
    tw = text_width(text + '...', fname); sw = text_width(sub, 'silkb') if sub else 0
    W_ = max(tw, sw) + 34; H_ = 22 if not sub else 30
    if progress is not None: H_ += 5
    xc = UW // 2 if x_center is None else x_center
    ww = int(round(W_ * k)); x0 = int(round(xc - ww / 2))
    if ww < 6: return None
    cv.rect(x0 + 2, y + 2, ww, H_, (0, 0, 0, int(90 * alpha)))
    cv.rect(x0, y, ww, H_, (10, 24, 40, int(220 * alpha)))
    cv.hline(x0, y, ww, _a(acc, alpha)); cv.hline(x0, y + H_ - 1, ww, _a(mix(acc, C('#000000'), 0.4), alpha))
    for (cx_, sgn) in ((x0, 1), (x0 + ww - 1, -1)):                  # corner brackets
        cv.vline(cx_, y, 5, _a(acc, alpha)); cv.vline(cx_, y + H_ - 5, 5, _a(acc, alpha))
    if k < 0.95: return (x0, y, ww, H_)
    ix, iy = x0 + 8, y + 6
    if ok:
        age = t - t_state
        if age < 0.25: cv.rect(x0, y, ww, H_, (95, 208, 122, int(110 * (1 - age / 0.25) * alpha)))
        for (i, j) in ((0, 4), (1, 5), (2, 6), (3, 5), (4, 4), (5, 3), (6, 2), (7, 1)):
            cv.px(ix + i, iy + j, _a(OK_G, alpha)); cv.px(ix + i, iy + j + 1, _a(OK_G, alpha))
    else:                                                            # spinner: 8 dots, one bright
        ph = int((t - t0) * 12) % 8
        for n in range(8):
            a_ = n * math.pi / 4
            px_, py_ = ix + 3 + round(3 * math.cos(a_)), iy + 4 + round(3 * math.sin(a_))
            cv.px(px_, py_, _a(HOLO_L if n == ph else mix(acc, C('#000000'), 0.5), alpha))
    cv.text(x0 + 21, y + 4, text + dots, _a(HOLO_L if not ok else C('#e8ffe8'), alpha), fname)
    if sub: cv.text(x0 + 21, y + 17, sub, _a(mix(acc, C('#ffffff'), 0.3), alpha), 'silkb')
    if progress is not None:
        py_ = y + H_ - 5; pw = ww - 16
        cv.rect(x0 + 8, py_, pw, 2, (40, 60, 80, int(220 * alpha)))
        cv.rect(x0 + 8, py_, int(pw * max(0.0, min(1.0, progress))), 2, _a(acc, alpha))
    return (x0, y, ww, H_)



# ------------------------------------------------------------------ ACT III v2: quest list / zzz / dust / auto-reply / thought bubble
def quest_list(cv, t, t0, items, y=44, x_center=None, w=150, alpha=1.0, stagger=0.14):
    """sub-quest checklist that unrolls under quest_bar():
         ▸ 睡个懒觉        (state 'active': gold arrow + gold text)
         □ 散个步          ('todo': hollow box, dim)
         ✗ 随便逛逛        ('fail': red cross, struck through) / ✓ ('done': green)
    items: [(title, state) | (title, state, t_state)] - the state applies from t_state on (else 'todo')."""
    if t < t0 or alpha <= 0: return None
    n = len(items); rh = 12; H_ = 6 + n * rh
    k = ease_out((t - t0) / 0.30)
    hh = int(round(H_ * k))
    if hh < 3: return None
    xc = UW // 2 if x_center is None else x_center
    x = int(round(xc - w / 2))
    _hud_panel(cv, x, y, w, hh, alpha * 0.92)
    cv.rect(x + 1, y + 1, 2, hh - 2, _a(GOLD_D, alpha))
    for i, it in enumerate(items):
        title, st = it[0], it[1]
        if len(it) > 2 and t < it[2]: st = 'todo'
        ry = y + 3 + i * rh
        a = alpha * min(1.0, max(0.0, (t - t0 - 0.12 - i * stagger) / 0.15))
        if a <= 0 or ry + rh > y + hh + 2: continue
        bx = x + 9; by = ry + 3
        if st == 'active':
            for j in range(4): cv.vline(bx + j, by + j, 7 - 2 * j, _a(GOLD, a))
            col = GOLD
        elif st == 'fail':
            for j in range(6): cv.px(bx + j, by + j, _a(QUEST_RED, a)); cv.px(bx + 5 - j, by + j, _a(QUEST_RED, a))
            col = C('#b8aab0')
        elif st == 'done':
            for (dx, dy) in ((0, 3), (1, 4), (2, 5), (3, 4), (4, 3), (5, 2), (6, 1)): cv.px(bx + dx, by + dy, _a(QUEST_GREEN, a))
            col = CREAM
        else:
            cv.rect(bx, by, 6, 6, _a(C('#8a86a8'), a)); cv.rect(bx + 1, by + 1, 4, 4, _a(NAVY, a))
            col = C('#c8c4e0')
        cv.text(x + 20, ry, title, _a(col, a), 'zh10', shadow=_a(C('#000000'), a))
        if st == 'fail':
            cv.hline(x + 19, ry + 7, text_width(title, 'zh10') + 2, _a(QUEST_RED, a))
    return (x, y, w, hh)


def zzz(cv, x, y, t, t0, t1, col=CREAM, period=0.55):
    """sleepy 'z Z Z' rising and drifting right from (x, y) between t0 and t1 (UI px)."""
    if t < t0 or t >= t1 + period * 2: return
    k = 0
    while True:
        ts = t0 + k * period
        if ts > t1 or ts > t: break
        age = (t - ts) / (period * 2.4)
        if age < 1.0:
            s = 1 + (1 if age > 0.45 else 0)
            a = min(1.0, age / 0.15) * (1 - max(0.0, (age - 0.7) / 0.3))
            zx = int(x + 10 * age + 2 * math.sin(age * 6 + k)); zy = int(y - 22 * age)
            big_text(cv, zx, zy, 'z', col, 'p2p', s, shadow=C('#3b3042'), alpha=a)
        k += 1


def dust_puff(cv, x, y, age, life=0.45, n=6, col=CREAM, spread=14):
    """little landing / hop puff on the ground line (UI px)."""
    if age < 0 or age > life: return
    u = age / life
    for i in range(n):
        ang = math.pi * (i + 0.5) / n
        dx = math.cos(ang) * spread * (0.4 + u); dy = -math.sin(ang) * 4 * u
        r = 1.6 + 2.4 * u * (1 - 0.3 * (i % 2))
        a = (1 - u) ** 1.3
        cv.ellipse(x + dx, y + dy, r, r * 0.8, _a(col, 0.85 * a))


AUTO_FILL = C('#2a2838'); AUTO_INK = C('#c8c4e0')

def auto_bubble(cv, ax, ay, age, life=1.6, text='自动回复：Claude 休假中', side=1, fname='zh8', alpha=1.0):
    """the dark 'auto-reply' bubble (same look as the city-wide replies in ACT III), with a tiny coral Claude tile."""
    k = pop_k(age, life)
    if k <= 0.01: return
    tw = text_width(text, fname)
    bw0, bh0 = tw + 21, 15
    bw, bh = max(6, int(round(bw0 * k))), max(5, int(round(bh0 * k)))
    lift = int(min(age, 0.6) / 0.6 * 2)
    bx = int(ax + side * 4) if side > 0 else int(ax - 4 - bw)
    by = int(ay - 6 - bh - lift)
    cv.rrect(bx + 1, by + 2, bw, bh, (0, 0, 0, int(100 * alpha)), 2)
    cv.rrect(bx - 1, by - 1, bw + 2, bh + 2, _a(C('#14121e'), alpha), 3)
    cv.rrect(bx, by, bw, bh, _a(AUTO_FILL, alpha), 2)
    tx = int(ax + side * 1) if side > 0 else int(ax - 2)
    for j in range(4): cv.hline(tx - (j if side > 0 else 0), by + bh + j, max(1, 4 - j), _a(AUTO_FILL, alpha))
    if k > 0.9:
        cv.rect(bx + 4, by + 4, 7, 7, _a(C('#d97757'), alpha)); cv.px(bx + 6, by + 6, _a(CREAM, alpha)); cv.px(bx + 8, by + 6, _a(CREAM, alpha))
        cv.text(bx + 14, by + 1, text, _a(AUTO_INK, alpha), fname)


class ThoughtBubble:
    """cloud-shaped thought bubble with an animated interior (dream / memory / plan).
       tb = ThoughtBubble(W, H); tb.draw(cv, t, t0, head_xy, tl_xy, interior(t)->rgba(H, W), t_out=None)
       - three dots rise from the head (t0 .. t0+0.3), the cloud pops in (back_out), pops out at t_out.
       tint_rim: rim brightening; edge colour = outline."""
    def __init__(self, W=156, H=92, edge=C('#2a1715'), rim_k=0.4, rim_col=(255, 255, 255)):
        import cv2
        self.W, self.H = W, H
        yy, xx = np.mgrid[0:H, 0:W]
        m = np.zeros((H, W), bool)
        sx, sy = W / 156.0, H / 92.0
        for (cx, cy, rx, ry) in ((78, 46, 70, 36), (40, 26, 30, 20), (80, 18, 34, 16), (120, 26, 30, 20),
                                 (34, 64, 28, 20), (78, 74, 36, 16), (122, 64, 28, 20), (16, 46, 14, 16), (140, 46, 14, 16)):
            m |= ((xx - cx * sx) / (rx * sx)) ** 2 + ((yy - cy * sy) / (ry * sy)) ** 2 < 1.0
        self.m = m
        k = np.ones((3, 3), np.uint8)
        self.edge = cv2.dilate(m.astype(np.uint8), k).astype(bool) & ~m
        self.rim = m & ~cv2.erode(m.astype(np.uint8), k).astype(bool)
        self.edge_col, self.rim_k, self.rim_col = edge, rim_k, np.array(rim_col, np.float32)

    def compose(self, interior):
        out = np.zeros((self.H + 4, self.W + 4, 4), np.uint8)
        a = interior.copy(); a[~self.m] = 0
        a[self.rim, :3] = (a[self.rim, :3] * (1 - self.rim_k) + self.rim_col * self.rim_k).astype(np.uint8)
        out[2:-2, 2:-2][self.m] = a[self.m]
        out[2:-2, 2:-2][self.edge] = self.edge_col
        return out

    def draw(self, cv, t, t0, head_xy, tl_xy, interior_fn, t_out=None, dot_col=C('#ffffff'), alpha=1.0):
        if t < t0: return
        if t_out is not None and t >= t_out + 0.3: return
        hx, hy = head_xy; bx, by = tl_xy
        fade = 1.0 if (t_out is None or t < t_out) else max(0.0, 1 - (t - t_out) / 0.3)
        n = 3
        for i in range(n):                                         # dots towards the bubble
            u = (i + 1) / (n + 1)
            dx, dy = hx + (bx + self.W * 0.25 - hx) * u * 0.8, hy + (by + self.H - hy) * u * 0.9
            r = 2.0 + 1.2 * i
            age = t - t0 - 0.1 * i
            if age <= 0: continue
            kk = back_out(min(1.0, age / 0.15), 2.0) * fade
            cv.ellipse(dx, dy, r * kk + 1, r * kk + 1, _a(self.edge_col, alpha)); cv.ellipse(dx, dy, r * kk, r * kk, _a(dot_col, alpha))
        age = t - t0 - 0.3
        if age < 0: return
        k = back_out(min(1.0, age / 0.3), 1.5)
        spr = self.compose(interior_fn(t))
        blit_scaled(cv, spr, bx + self.W // 2, by + self.H // 2, k, alpha * fade)


# ------------------------------------------------------------------ ACT IV widgets
def toggle(cv, cx, y, on_k=1.0, label='消息提醒', alpha=1.0, k=1.0, press=0.0):
    """small settings panel with an iOS-style switch, centred at cx.  on_k 1 = 开 (green, knob right) -> 0 = 关
    (grey, knob left; animate it over ~0.15 s).  k = pop-in 0..1 (rises 4 px), press = 0..1 knob squash."""
    if alpha <= 0 or k <= 0: return
    a = alpha * min(1.0, k)
    tw = text_width(label, 'zh10')
    w = tw + 50; h = 19
    x = int(round(cx - w / 2)); y = int(round(y + 4 * (1 - ease_out(k))))
    cv.rrect(x + 2, y + 2, w, h, (0, 0, 0, int(80 * a)), 4)
    cv.rrect(x, y, w, h, _a(C('#14131c'), a), 4); cv.rrect(x + 1, y + 1, w - 2, h - 2, _a(C('#2a2838'), a), 4)
    cv.hline(x + 4, y + 1, w - 8, _a(C('#45425a'), a))
    # bell icon (crossed out once off)
    bx, by = x + 6, y + 5
    B = _a(C('#e8e4f4'), a)
    cv.rect(bx + 2, by, 3, 1, B); cv.rect(bx + 1, by + 1, 5, 4, B); cv.rect(bx, by + 5, 7, 1, B); cv.px(bx + 3, by + 7, B)
    if on_k < 0.5:
        R_ = _a(C('#ff6a5a'), a)
        for i in range(8): cv.px(bx - 1 + i, by - 1 + i, R_)
    cv.text(x + 16, y + 4, label, _a(C('#ffffff'), a), 'zh10')
    # the switch
    sx, sy, sw, sh = x + w - 30, y + 5, 18, 9
    on = mix(C('#6a6a7a'), C('#4fe07a'), max(0.0, min(1.0, on_k)))
    cv.rrect(sx, sy, sw, sh, _a(on, a), 4)
    cv.hline(sx + 3, sy + 1, sw - 6, _a(mix(on, C('#ffffff'), 0.25), a))
    kx = sx + 1 + (sw - 9) * max(0.0, min(1.0, on_k))
    kw = 7 + int(round(2 * press))
    cv.rrect(int(round(kx - press)), sy + 1, kw, 7, _a(C('#ffffff'), a), 3)
    cv.text(x + w - 10, y + 5, '开' if on_k >= 0.5 else '关', _a(C('#a9a6c0'), a), 'zh8')


# ------------------------------------------------------------------ ACT IV: the optimizer card + its shatter
CYAN = C('#7fe0ff'); CYAN_D = C('#2c6a8a'); HUD_BG = (16, 20, 38, 228)

def _row_label(cv, x, y, zh, alpha):
    cv.text(x, y, zh, _a(CREAM, alpha), 'zh8')

def optimizer_card(t, rows_k, title='钓鱼方案', title_en='OPTIMIZER', w=140, best='12.4m', wind='东南 2.1m/s',
                   temp='18.6°C', rate='+83%', rate_k=0.0, seed=0, crack=0.0):
    """dark HUD card 'Claude computes the perfect fishing plan' -> RGBA (h, w, 4) uint8.
    rows_k: reveal 0..1 for [sonar (best spot), fish density bars, wind, water temp] (each row slides in + fades up);
    rate_k: 0..1 the big success-rate number pops in at the bottom; crack 0..1 white fracture lines (just before shatter).
    t drives the sonar sweep / bar wiggle / title spinner."""
    rows_k = list(rows_k) + [0.0] * (4 - len(rows_k))
    RH = 18
    h = 25 + 4 * RH + (34 if rate_k > 0 else 0) + 2
    cv = Canvas(w, h)
    cv.rrect(0, 0, w, h, CYAN_D, 3); cv.rrect(1, 1, w - 2, h - 2, HUD_BG, 3)
    for yy in range(3, h - 3, 3): cv.hline(3, yy, w - 6, (40, 60, 90, 60))                 # scanlines
    cv.text(6, 3, title, CREAM, 'zh10')
    cv.text(6 + text_width(title, 'zh10') + 4, 6, title_en, CYAN, 'silkb')
    sp = int(t * 10) % 8
    for i in range(8):
        a_ = 2 * math.pi * i / 8
        cv.px(int(round(w - 10 + 3 * math.cos(a_))), int(round(9 + 3 * math.sin(a_))), CYAN if (sp - i) % 8 < 3 else CYAN_D)
    cv.hline(4, 20, w - 8, CYAN_D)
    y = 24
    VX = 62                                                         # column where the visual / value starts
    for i, k in enumerate(rows_k):
        if k <= 0: y += RH; continue
        al = min(1.0, k * 2.5)
        x0 = 6 - int(round(8 * (1 - ease_out(min(1.0, k * 2.0)))))
        if i == 0:     # best spot: a mini sonar (arcs + sweep + ping) + distance
            _row_label(cv, x0, y + 1, '最佳下钩点', al)
            sx, sy = VX + 12, y + 15
            for r in (4, 8, 12):
                for d in range(-60, 61, 6):
                    a_ = math.radians(d - 90)
                    cv.px(int(round(sx + r * math.cos(a_))), int(round(sy + r * math.sin(a_))), _a(CYAN_D, al))
            sw_ = math.radians(-90 + 60 * math.sin(t * 3.0))
            for r in range(1, 12): cv.px(int(round(sx + r * math.cos(sw_))), int(round(sy + r * math.sin(sw_))), _a(CYAN, al))
            pk = 0.5 + 0.5 * math.sin(t * 9)
            cv.rect(sx + 5, sy - 9, 2, 2, _a(mix(C('#ff7a5a'), C('#ffe0c0'), pk), al))
            cv.text(VX + 30, y + 1, best, _a(CYAN, al * min(1.0, k * 1.5)), 'zh8')
        elif i == 1:   # fish density: 7 bars
            _row_label(cv, x0, y + 1, '鱼群密度', al)
            for b in range(7):
                hb = int(round((3 + 9 * abs(math.sin(b * 1.7 + seed))) * min(1.0, k * 1.6) * (0.85 + 0.15 * math.sin(t * 6 + b))))
                cv.rect(VX + b * 6, y + 14 - hb, 4, hb, _a(CYAN if b in (3, 4) else CYAN_D, al))
            cv.text(VX + 46, y + 1, '高', _a(CYAN, al), 'zh8')
        elif i == 2:   # wind: arrow + value
            _row_label(cv, x0, y + 1, '风向', al)
            ax_, ay_ = VX, y + 10
            for jj in range(9): cv.px(ax_ + jj, ay_ - jj // 2, _a(CYAN, al))
            cv.px(ax_ + 7, ay_ - 5, _a(CYAN, al)); cv.px(ax_ + 8, ay_ - 2, _a(CYAN, al)); cv.px(ax_ + 6, ay_ - 4, _a(CYAN, al))
            cv.text(ax_ + 12, y + 1, wind, _a(CYAN, al), 'zh8')
        elif i == 3:   # water temperature
            _row_label(cv, x0, y + 1, '水温', al)
            tx_ = VX + 2
            cv.rect(tx_, y + 2, 3, 9, _a(CYAN_D, al)); cv.rect(tx_ + 1, y + 6, 1, 5, _a(C('#ff7a5a'), al)); cv.rect(tx_ - 1, y + 10, 5, 3, _a(C('#ff7a5a'), al))
            cv.text(tx_ + 10, y + 1, temp, _a(CYAN, al), 'zh8')
        y += RH
    if rate_k > 0:
        cv.hline(4, y + 1, w - 8, CYAN_D)
        cv.text(6, y + 11, '成功率', CREAM, 'zh10')
        k = back_out(min(1.0, rate_k), 2.2)
        m = text_mask(rate, 'p2p')
        rows = np.nonzero(m.any(1))[0]; m = m[rows[0]:rows[-1] + 1]
        s = 2
        big = np.repeat(np.repeat(m, s, 0), s, 1)
        bw = big.shape[1]
        g = Canvas(bw + 2, big.shape[0] + 2)
        g._mask(big, 2, 2, (0, 0, 0, 255)); g._mask(big, 0, 0, GOLD)
        blit_scaled(cv, g.a, w - 10 - bw // 2, y + 18, k)
    if crack > 0:                                                   # fracture lines spreading from the big number
        rng = np.random.default_rng(seed + 5)
        cx_, cy_ = w * 0.7, h - 18
        for n in range(7):
            ang = rng.uniform(0, 2 * math.pi); L_ = (25 + 60 * rng.random()) * crack
            x_, y_ = cx_, cy_
            for st in range(int(L_)):
                ang += rng.uniform(-0.35, 0.35)
                x_ += math.cos(ang); y_ += math.sin(ang)
                if 0 <= x_ < w and 0 <= y_ < h: cv.px(int(x_), int(y_), CREAM)
    return cv.a


def shatter(cv, rgba, x, y, age, floor_y, seed=0, block=5, g=420.0, alpha=1.0):
    """break a UI sprite into pixel blocks that fall (gravity, a little spin-off sideways) and vanish at floor_y
    (e.g. the water line).  age = seconds since the break.  The blocks near the top-left go first.
    Returns the number of blocks that hit the floor during this frame-age (for splash cues use shatter_hits)."""
    h, w = rgba.shape[:2]
    rng = np.random.default_rng(seed)
    for by in range(0, h, block):
        for bx in range(0, w, block):
            tile = rgba[by:by + block, bx:bx + block]
            vx = rng.uniform(-26, 26); vy = rng.uniform(-60, -10); d = 0.10 * (bx + by) / (w + h) + rng.uniform(0, 0.05)
            if not (tile[..., 3] > 0).any(): continue
            u = age - d
            if u < 0:
                cv.blit(tile, x + bx, y + by, alpha_mul=alpha); continue
            px_ = x + bx + vx * u; py_ = y + by + vy * u + 0.5 * g * u * u
            if py_ >= floor_y: continue
            fade = max(0.0, 1.0 - u / 1.6)
            cv.blit(tile, int(round(px_)), int(round(py_)), alpha_mul=alpha * fade)

def shatter_hits(rgba, x, y, floor_y, seed=0, block=5, g=420.0):
    """sorted [(t, x)]: time after the break + UI x at which each shatter() block reaches floor_y (plinks / splashes)."""
    h, w = rgba.shape[:2]
    rng = np.random.default_rng(seed); out = []
    for by in range(0, h, block):
        for bx in range(0, w, block):
            vx = rng.uniform(-26, 26); vy = rng.uniform(-60, -10); d = 0.10 * (bx + by) / (w + h) + rng.uniform(0, 0.05)
            if not (rgba[by:by + block, bx:bx + block, 3] > 0).any(): continue
            dy = floor_y - (y + by)
            u = (-vy + math.sqrt(vy * vy + 2 * g * max(dy, 0))) / g
            if u < 1.6: out.append((d + u, x + bx + block / 2 + vx * u))
    return sorted(out)


# ------------------------------------------------------------------ v0.8: a refined Win95 word processor (ACT V 周报)
DOC = dict(ink=C('#1f1f2a'), navy=C('#1b2a78'), grey=C('#8a8a96'), page=C('#fffdf8'), desk=C('#6f7480'),
           rule=C('#c9cbe0'), sel=C('#1b2a78'), claude=C('#d97757'), warm=C('#b8452f'), green=C('#2f8a4a'))

def soft_shadow(cv, x, y, w, h, n=5, a0=70, dx=3, dy=4):
    """layered drop shadow (reads as soft at 4x) - replaces the hard 1-step w95 shadow."""
    for i in range(n, 0, -1):
        cv.rrect(x + dx - i + 2, y + dy - i + 2, w + 2 * i - 4, h + 2 * i - 4, (10, 6, 20, int(a0 / n * (n - i + 1) * 0.55)), 3)

def _icon(cv, x, y, kind, col=None):
    """10x10 toolbar glyphs."""
    k = W95['dk']; w_ = C('#ffffff'); g = C('#808080')
    if kind == 'new':
        cv.rect(x + 2, y + 1, 6, 8, w_); cv.rect(x + 2, y + 1, 6, 1, k); cv.vline(x + 2, y + 1, 8, k); cv.vline(x + 7, y + 3, 6, k)
        cv.hline(x + 2, y + 8, 6, k); cv.px(x + 6, y + 2, k); cv.px(x + 6, y + 1, W95['face']); cv.px(x + 7, y + 2, k)
    elif kind == 'open':
        cv.rect(x + 1, y + 3, 8, 6, C('#e8c860')); cv.hline(x + 1, y + 3, 4, C('#b08a20')); cv.rect(x + 1, y + 8, 8, 1, C('#8a6a10'))
        cv.hline(x + 3, y + 5, 7, C('#f8e090'))
    elif kind == 'save':
        cv.rect(x + 1, y + 1, 8, 8, C('#2a3a8a')); cv.rect(x + 3, y + 1, 4, 3, C('#dcdcdc')); cv.rect(x + 3, y + 6, 4, 3, w_)
    elif kind in ('B', 'I', 'U'):
        cv.text(x + 2, y - 1, kind, k, 'silkb')
        if kind == 'U': cv.hline(x + 2, y + 8, 6, k)
    elif kind == 'align':
        for i, L in enumerate((7, 5, 7, 4)): cv.hline(x + 1, y + 2 + i * 2, L, k)
    elif kind == 'list':
        for i in range(3): cv.px(x + 1, y + 2 + i * 3, k); cv.hline(x + 3, y + 2 + i * 3, 6, k)
    elif kind == 'book':          # dictionary: red cover + pages
        cv.rect(x + 1, y + 1, 8, 8, C('#b8302a')); cv.vline(x + 2, y + 1, 8, C('#7a1a16')); cv.rect(x + 4, y + 3, 4, 2, C('#ffd9a0'))
        cv.hline(x + 2, y + 9, 7, C('#ffffff'))
    elif kind == 'cal':           # calendar: red header + grid
        cv.rect(x + 1, y + 1, 8, 8, w_); cv.rect(x + 1, y + 1, 8, 3, C('#c8352c')); cv.px(x + 3, y, k); cv.px(x + 6, y, k)
        for i in range(3):
            for j in range(2): cv.px(x + 2 + i * 2, y + 5 + j * 2, g)
        cv.px(x + 7, y + 7, C('#c8352c'))
    elif kind == 'search':        # magnifier
        c = col or k
        cv.rect(x + 1, y + 1, 5, 5, C('#bfe4ff')); cv.hline(x + 2, y, 3, c); cv.hline(x + 2, y + 6, 3, c); cv.vline(x, y + 2, 3, c)
        cv.vline(x + 6, y + 2, 3, c); cv.px(x + 2, y + 2, w_)
        for i in range(3): cv.rect(x + 6 + i, y + 6 + i, 2, 2, c)
    elif kind == 'star':
        for j, r in enumerate(["....#....", "...###...", "#########", ".#######.", "..#####..", ".###.###.", ".#.....#."]):
            for i, ch_ in enumerate(r):
                if ch_ == '#': cv.px(x + i, y + 1 + j, col or GOLD)
    elif kind == 'speaker':
        c = col or k
        cv.rect(x + 1, y + 3, 2, 4, c); cv.vline(x + 3, y + 2, 6, c); cv.vline(x + 4, y + 1, 8, c)
        cv.vline(x + 6, y + 3, 4, c); cv.px(x + 7, y + 2, c); cv.px(x + 7, y + 7, c); cv.vline(x + 8, y + 3, 4, c)
    elif kind == 'send':          # paper plane
        c = col or C('#1b2a78')
        for i in range(7): cv.hline(x + 1 + i // 2, y + 2 + i // 2 + (1 if i > 4 else 0), 8 - i, c)
        cv.line(x + 1, y + 2, x + 9, y + 4, c); cv.line(x + 9, y + 4, x + 4, y + 9, c); cv.px(x + 4, y + 6, C('#ffffff'))
    elif kind == 'form':          # v0.8.1 form: page with two tick rows + a pencil
        cv.rect(x + 1, y, 7, 10, w_); cv.vline(x + 1, y, 10, g); cv.hline(x + 1, y + 9, 7, g)
        for j in (2, 5): cv.rect(x + 2, y + j, 2, 2, C('#1f4fbf')); cv.hline(x + 5, y + j + 1, 2, g)
        cv.line(x + 6, y + 9, x + 9, y + 6, C('#e0a030')); cv.px(x + 6, y + 9, k)
    elif kind == 'seal':          # v0.8.1 approval centre: red square seal
        cv.rect(x + 1, y + 1, 8, 8, C('#c8352c')); cv.rect(x + 2, y + 2, 6, 6, C('#f6e9e0'))
        cv.rect(x + 3, y + 3, 4, 4, C('#c8352c')); cv.px(x + 4, y + 4, C('#f6e9e0'))
    elif kind == 'power':         # v0.8.1 shutdown: power symbol
        c = col or C('#1a7a2a')
        cv.vline(x + 4, y, 5, c); cv.vline(x + 5, y, 5, c)
        for (px_, py_) in ((2, 2), (1, 3), (1, 4), (1, 5), (1, 6), (2, 7), (3, 8), (4, 8), (5, 8), (6, 8), (7, 7), (8, 6),
                           (8, 5), (8, 4), (8, 3), (7, 2)): cv.px(x + px_, y + py_, c)
    elif kind == 'hourglass':     # v0.8.1 waiting
        c = col or k
        cv.hline(x + 1, y, 8, c); cv.hline(x + 1, y + 9, 8, c)
        for i in range(4): cv.hline(x + 2 + i, y + 1 + i, 6 - 2 * i, C('#e8c070') if i > 1 else w_); cv.hline(x + 2 + i, y + 8 - i, 6 - 2 * i, C('#e8c070'))

def tool_button(cv, x, y, w, h, hover=False, pressed=False):
    if pressed: w95_bevel(cv, x, y, w, h, raised=False)
    elif hover:
        cv.hline(x, y, w - 1, W95['hi']); cv.vline(x, y, h - 1, W95['hi']); cv.hline(x, y + h - 1, w, W95['sh']); cv.vline(x + w - 1, y, h, W95['sh'])

def spinner_dots(cv, x, y, t, col):
    for i in range(3):
        k = 0.5 + 0.5 * math.sin(t * 9 - i * 0.9)
        cv.rect(x + i * 3, y + (0 if k > 0.75 else 1), 2, 2, _a(col, 0.4 + 0.6 * k))

def w95_menubar(cv, cx, cy, cw, items=('文件', '编辑', '视图', '帮助'), hot=None):
    """menu bar inside a client rect; hot = index of an open/hovered menu. returns the y below its separator."""
    mx = cx + 4
    for i, m in enumerate(items):
        tw = text_width(m, 'zh8')
        if i == hot: cv.rect(mx - 3, cy, tw + 6, 11, W95['t0']); cv.text(mx, cy + 1, m, C('#ffffff'), 'zh8')
        else: cv.text(mx, cy + 1, m, W95['dk'], 'zh8')
        mx += tw + 9
    yy = cy + 12
    cv.hline(cx, yy, cw, W95['sh']); cv.hline(cx, yy + 1, cw, W95['hi'])
    return yy + 2

def w95_statusbar(cv, cx, y, cw, segs, t=0.0):
    """segmented sunken status bar (13 px tall).  segs: list of dict(text, w=None (auto; the last seg takes the rest),
    col=None, busy=False (spinner dots), right='' (right-aligned grey text))."""
    xx = cx + 1
    for i, sg in enumerate(segs):
        txt = sg.get('text', '')
        ww = cw - (xx - cx) - 1 if i == len(segs) - 1 else (sg.get('w') or text_width(txt, 'zh8') + 9)
        w95_panel(cv, xx, y, ww, 13, W95['face'])
        c = sg.get('col') or W95['dk']
        if txt: cv.text(xx + 4, y + 2, txt, c, 'zh8')
        if sg.get('busy'): spinner_dots(cv, xx + 6 + text_width(txt, 'zh8'), y + 6, t, c)
        if sg.get('right'): cv.text(xx + ww - 4 - text_width(sg['right'], 'zh8'), y + 2, sg['right'], W95['sh'], 'zh8')
        xx += ww + 2

def default_button(cv, x, y, w, h, label, state='idle', icon=None, fname='zh10'):
    """a dialog's default button (black ring): state idle|hover|pressed; icon: _icon kind drawn left of the label."""
    cv.rect(x - 1, y - 1, w + 2, h + 2, W95['dk'])
    cv.rect(x, y, w, h, C('#d8e4f8') if state == 'hover' else W95['face'])
    w95_bevel(cv, x, y, w, h, raised=state != 'pressed')
    off = 1 if state == 'pressed' else 0
    tw = text_width(label, fname) + (14 if icon else 0); lx = x + (w - tw) // 2 + off; ly = y + (h - 11) // 2 + off
    if icon: _icon(cv, lx, ly + 1, icon); lx += 14
    cv.text(lx, ly, label, W95['dk'], fname)
    return (x + w / 2, y + h / 2)

def w95_doc(cv, x, y, w, h, title, blocks, t=0.0, status='', status_r='', status_col=None, send=None, scroll=0,
            word_count=None):
    """a Win95 word processor: menu bar, toolbar (with a default 发送 button), ruler, grey desk with a paper page,
    scrollbar, segmented status bar.  blocks (page content, top to bottom):
        dict(kind='h1'|'meta'|'li'|'p'|'sep'|'gap', text, n=None (visible chars), col=None, num=None (li),
             gen=False (streaming: fresh glyph tail fades in + an orange block caret), caret=False,
             sel=None (a, b) selected char range (navy highlight), tail_icon=None callable(cv, x, y))
    send: None | dict(state='idle'|'hover'|'pressed'|'sent') draws the 发送 button at the toolbar's right end.
    Returns dict(send=(cx, cy) centre of the send button, caret=(x, y) of the last caret)."""
    out = {}
    soft_shadow(cv, x, y, w, h)
    cx, cy, cw, ch = w95_window(cv, x, y, w, h, title, icon=lambda c, ix, iy: (_icon(c, ix, iy - 1, 'new')))
    # menu bar
    yy = w95_menubar(cv, cx, cy, cw, ('文件', '编辑', '视图', '插入', '格式', '工具', '帮助')) - 2
    # toolbar
    ty = yy + 3; bx = cx + 3
    for kind in ('new', 'open', 'save', '|', 'B', 'I', 'U', '|', 'align', 'list'):
        if kind == '|':
            cv.vline(bx + 1, ty + 1, 11, W95['sh']); cv.vline(bx + 2, ty + 1, 11, W95['hi']); bx += 6; continue
        _icon(cv, bx + 2, ty + 2, kind); bx += 14
    w95_field(cv, bx + 2, ty, 46, 14, '宋体', fname='zh8'); w95_button(cv, bx + 37, ty + 2, 9, 10)
    for i in range(3): cv.hline(bx + 39 + i, ty + 6 + i, 5 - 2 * i, W95['dk'])
    w95_field(cv, bx + 50, ty, 24, 14, '10.5', fname='zh8')
    if send is not None:
        st = send.get('state', 'idle')
        sw_, sh_ = 52, 15; sx_, sy_ = cx + cw - sw_ - 3, ty - 1
        cv.rect(sx_ - 1, sy_ - 1, sw_ + 2, sh_ + 2, W95['dk'])                       # default-button ring
        cv.rect(sx_, sy_, sw_, sh_, C('#d8e4f8') if st == 'hover' else W95['face'])
        w95_bevel(cv, sx_, sy_, sw_, sh_, raised=st != 'pressed')
        off = 1 if st == 'pressed' else 0
        if st == 'sent':
            for i_, (dx, dy) in enumerate(((0, 3), (1, 4), (2, 5), (3, 4), (4, 3), (5, 2), (6, 1))):
                cv.rect(sx_ + 8 + dx, sy_ + 4 + dy, 1, 2, DOC['green'])
            cv.text(sx_ + 18, sy_ + 2, '已发送', DOC['green'], 'zh10')
        else:
            _icon(cv, sx_ + 5 + off, sy_ + 2 + off, 'send')
            cv.text(sx_ + 20 + off, sy_ + 2 + off, '发送', W95['dk'], 'zh10')
        out['send'] = (sx_ + sw_ / 2, sy_ + sh_ / 2)
    yy = ty + 17
    cv.hline(cx, yy, cw, W95['sh']); cv.hline(cx, yy + 1, cw, W95['hi'])
    # ruler
    ry = yy + 3
    sb_w = 11
    desk_x, desk_w = cx + 1, cw - 2 - sb_w
    px0, pw = desk_x + 12, desk_w - 24
    cv.rect(desk_x, ry, desk_w, 8, W95['face']); cv.rect(px0, ry + 1, pw, 6, C('#ffffff'))
    for i in range(0, pw, 4):
        cv.vline(px0 + i, ry + (4 if i % 16 else 2), 2 if i % 16 else 4, W95['sh'])
    for mx_ in (px0 + 10, px0 + pw - 10):
        cv.px(mx_ - 1, ry, W95['dk']); cv.hline(mx_ - 2, ry + 1, 3, W95['dk'])
    # status bar
    sb_y = y + h - 4 - 13
    # desk + page
    dy0 = ry + 10; dh = sb_y - 2 - dy0
    cv.rect(desk_x, dy0, desk_w + sb_w, dh, DOC['desk']); w95_bevel(cv, desk_x - 1, dy0 - 1, desk_w + sb_w + 2, dh + 2, raised=False)
    # scrollbar
    sbx = desk_x + desk_w
    cv.rect(sbx, dy0, sb_w, dh, C('#e0e0e0'))
    for k_ in range(0, dh, 2): cv.hline(sbx, dy0 + k_, sb_w, C('#d0d0d0'))
    w95_button(cv, sbx, dy0, sb_w, 10); w95_button(cv, sbx, dy0 + dh - 10, sb_w, 10)
    cv.px(sbx + 5, dy0 + 4, W95['dk']); cv.hline(sbx + 4, dy0 + 5, 3, W95['dk'])
    cv.hline(sbx + 4, dy0 + dh - 6, 3, W95['dk']); cv.px(sbx + 5, dy0 + dh - 5, W95['dk'])
    thumb_h = max(14, int(dh * 0.55)); thumb_y = dy0 + 10 + int((dh - 20 - thumb_h) * min(1.0, scroll / 40.0))
    w95_button(cv, sbx, thumb_y, sb_w, thumb_h)
    # the page (clipped to the desk)
    page = Canvas(desk_w, dh)
    pg = page
    pxl, pyl = 12, 5 - int(scroll)
    pg.rect(pxl + 2, pyl + 2, pw, 400, (20, 20, 30, 90)); pg.rect(pxl, pyl, pw, 400, DOC['page'])
    lx = pxl + 14; ly = pyl + 8; maxw = pw - 28
    for b in blocks:
        kind = b.get('kind', 'p'); s = b.get('text', ''); n = b.get('n'); n = len(s) if n is None else max(0, min(len(s), n))
        if kind == 'gap': ly += b.get('h', 6); continue
        if kind == 'sep':
            for i in range(0, maxw, 3): pg.px(lx + i, ly + 3, DOC['rule'])
            ly += 9; continue
        fname = 'zh12' if kind == 'h1' else ('zh8' if kind == 'meta' else 'zh10')
        col = b.get('col') or (DOC['navy'] if kind == 'h1' else DOC['grey'] if kind == 'meta' else DOC['ink'])
        tx = lx
        if kind == 'li':
            num = str(b.get('num', '·')); pg.rect(tx, ly + 1, 9, 9, DOC['navy'])
            pg.text(tx + 5 - text_width(num, 'silk') // 2, ly + 2, num, C('#ffffff'), 'silk')
            tx += 12
        vis = s[:n]
        sel = b.get('sel')
        if sel and n > 0:
            a_, b_ = max(0, sel[0]), min(n, sel[1])
            if b_ > a_:
                xa = tx + text_width(vis[:a_], fname); xb = tx + text_width(vis[:b_], fname)
                pg.rect(xa, ly, xb - xa + 1, 12 if fname != 'zh12' else 14, DOC['sel'])
        if vis:
            if sel and n > 0 and sel[1] > sel[0]:
                a_, b_ = max(0, sel[0]), min(n, sel[1])
                pg.text(tx, ly, vis[:a_], col, fname)
                pg.text(tx + text_width(vis[:a_], fname), ly, vis[a_:b_], C('#ffffff'), fname)
                pg.text(tx + text_width(vis[:b_], fname), ly, vis[b_:], col, fname)
            else:
                pg.text(tx, ly, vis, col, fname)
            if kind == 'h1': pg.text(tx + 1, ly, vis, col, fname)                       # faux bold
            if b.get('gen') and n < len(s):                                             # fresh tail fades in
                k0 = max(0, n - 3)
                for j in range(k0, n):
                    xj = tx + text_width(vis[:j], fname)
                    a = 0.35 + 0.65 * (j - k0 + 1) / 4
                    pg.rect(xj, ly, text_width(vis[j], fname), 12, (*DOC['page'][:3], int(255 * (1 - a) * 0.8)))
        ex = tx + text_width(vis, fname) if vis else tx
        if b.get('gen') and n < len(s):
            pg.rect(ex + 1, ly + 2, 5, 9, DOC['claude'])
        if b.get('caret') and (t * 2.2) % 1 < 0.6:
            pg.vline(ex + 1, ly, 12, DOC['ink']); out['caret'] = (desk_x + ex + 1, dy0 + ly)
        if b.get('tail_icon') is not None and n >= len(s):
            b['tail_icon'](pg, ex + 3, ly)
        if kind == 'h1':
            ly += 15
            pg.hline(lx, ly, maxw, DOC['navy']); pg.hline(lx, ly + 1, maxw, DOC['rule']); ly += 5
        else:
            ly += 11 if kind == 'meta' else b.get('lh', 13)
    cv.blit(pg.a, desk_x, dy0)
    # status bar segments
    s1 = '第 1 页，共 1 页'; w1 = text_width(s1, 'zh8') + 9
    w95_panel(cv, cx + 1, sb_y, w1, 13, W95['face']); cv.text(cx + 5, sb_y + 2, s1, W95['dk'], 'zh8')
    s2 = f'字数 {word_count}' if word_count is not None else ''; w2 = text_width('字数 000', 'zh8') + 9
    w95_panel(cv, cx + w1 + 3, sb_y, w2, 13, W95['face']); cv.text(cx + w1 + 7, sb_y + 2, s2, W95['dk'], 'zh8')
    rx_ = cx + w1 + w2 + 5; rw_ = cw - (w1 + w2 + 6)
    w95_panel(cv, rx_, sb_y, rw_, 13, W95['face'])
    if status:
        sc = status_col or W95['dk']
        cv.text(rx_ + 4, sb_y + 2, status, sc, 'zh8')
        if status.endswith('…') or status_r == 'busy':
            spinner_dots(cv, rx_ + 6 + text_width(status, 'zh8'), sb_y + 6, t, sc)
    if status_r and status_r != 'busy':
        cv.text(rx_ + rw_ - 4 - text_width(status_r, 'zh8'), sb_y + 2, status_r, W95['sh'], 'zh8')
    return out
