"""pixelkit.sets.dressing - 'lived-in' set dressing (v0.8): the small clutter that makes a room feel inhabited
(the reference look: shelves full of things, paper balls on the floor, cork boards, cables, plants, pigeons).

Every function returns a scene.Sprite (rgba + emissive E) in the props.py conventions (light from the upper-left,
mid-range albedo, sel_out outlines).  Office.dress(bg) places a curated set of them in the office;
OfficeLife (bottom) animates the ambient life: coffee steam, a pigeon on the window ledge, drifting clouds.
"""
import math
import numpy as np
from ..core import C, mix, sel_out, text_width
from ..scene import Sprite
from .props import R, box

def _sp(w, h): return Sprite(w, h)

# ---------------------------------------------------------------- floor clutter
def paper_ball(seed=0, r=2.6):
    """crumpled paper ball (~6x5): random facets, lit from the upper-left."""
    rng = np.random.default_rng(seed)
    n = int(math.ceil(r * 2)) + 2
    s = _sp(n, n - 1); cv = s.cv
    cx, cy = n / 2 - 0.5, (n - 1) / 2 - 0.3
    cols = [C('#fbf8f0'), C('#e9e3d6'), C('#cfc6b6'), C('#a79c8c')]
    for y in range(n - 1):
        for x in range(n):
            d = ((x - cx) / r) ** 2 + ((y - cy) / (r * 0.86)) ** 2
            if d > 1.0 + rng.uniform(-0.25, 0.1): continue
            lit = -(x - cx) * 0.5 - (y - cy) * 0.7 + rng.normal(0, 0.8)
            k = 0 if lit > 0.9 else 1 if lit > -0.2 else 2 if lit > -1.2 else 3
            cv.px(x, y, cols[k])
    for _ in range(2):          # crease lines
        x, y = int(rng.integers(1, n - 2)), int(rng.integers(1, n - 2))
        if s.cv.a[y, x, 3]: cv.px(x, y, cols[3])
    return s

def trash_bin(w=13, h=15, balls=3, seed=1):
    """wire-mesh office bin, overflowing with paper balls."""
    s = _sp(w + 2, h + 5); cv = s.cv
    mr = R('#5a5e6a', 6)
    oy = 5
    for y in range(h):
        inset = int(round(1.5 * y / h))
        x0, x1 = 1 + inset, w + 1 - inset
        for x in range(x0, x1):
            on = ((x + y) % 3 == 0) or ((x - y) % 3 == 0)
            cv.px(x, oy + y, mr[3] if on else mr[1])
        cv.px(x0, oy + y, mr[4]); cv.px(x1 - 1, oy + y, mr[0])
    cv.rect(0, oy, w + 2, 2, mr[4]); cv.hline(0, oy, w + 2, mr[5]); cv.rect(2, oy + h - 1, w - 2, 1, mr[0])
    rng = np.random.default_rng(seed)
    for k in range(balls):
        b = paper_ball(seed * 10 + k, r=2.4)
        bx = int(1 + k * (w - 4) / max(1, balls - 1) + rng.integers(-1, 2)); by = int(oy - 4 + rng.integers(0, 3))
        cv.blit(b.rgba, bx, by)
    return s

def file_box(w=26, h=16, label='资料'):
    """cardboard box with folders sticking out."""
    s = _sp(w, h + 6); cv = s.cv
    br = R('#b88a55', 6)
    for i, col in enumerate(('#d8c27a', '#7aa7d8', '#e08a7a', '#f2efe6')):
        cv.rect(3 + i * 5, 1 + (i % 2) * 2, 6, 8, R(col, 6)[3]); cv.hline(3 + i * 5, 1 + (i % 2) * 2, 6, R(col, 6)[5])
    box(cv, 0, 6, w, h, br)
    cv.rect(w // 2 - 4, 6, 8, 2, br[1])
    cv.rect(w // 2 - 7, 11, 14, 8, C('#f4efe2'))
    cv.text(w // 2 - 6, 11, label, C('#4a3a30'), 'zh8')
    return s

def floor_cable(cv_w, pts, col='#2c2a33'):
    """polyline cable sprite through pts (list of (x, y) in a cv_w-wide local canvas) -> Sprite."""
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    s = _sp(cv_w, max(ys) + 2); cv = s.cv
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(int(x0), int(y0), int(x1), int(y1), C(col))
        cv.line(int(x0), int(y0) - 1, int(x1), int(y1) - 1, C('#4a4752'))
    return s

def coat_stand(h=62, coat='#5a6b8c', umbrella='#c8463c'):
    s = _sp(22, h + 2); cv = s.cv
    wr = R('#6b4a33', 6)
    cv.rect(10, 4, 2, h - 6, wr[2]); cv.vline(10, 4, h - 6, wr[4])
    for dx in (-6, 0, 6):
        cv.line(11, h - 3, 11 + dx, h, wr[1])
    cv.hline(5, h, 13, wr[0])
    cv.rect(6, 3, 10, 2, wr[3]); cv.rect(9, 1, 4, 2, wr[4])
    cr = R(coat, 6)
    cv.poly([(5, 6), (16, 6), (18, 30), (3, 30)], cr[3]); cv.vline(10, 8, 22, cr[1]); cv.vline(5, 7, 22, cr[4])
    cv.rect(8, 6, 6, 3, cr[2])
    ur = R(umbrella, 6)
    cv.poly([(15, 34), (19, 34), (18, h - 4), (16, h - 4)], ur[3]); cv.vline(16, 34, h - 38, ur[4])
    cv.rect(16, 31, 2, 3, C('#3a2a24'))
    return s

def floor_plant(h=58, pot='#e8e0d0', seed=2):
    """tall monstera-ish plant in a ceramic pot (corner dressing)."""
    rng = np.random.default_rng(seed)
    w = 34
    s = _sp(w, h); cv = s.cv
    gr = R('#4f9a5a', 7)
    for k in range(9):
        a = -math.pi / 2 + rng.uniform(-1.1, 1.1)
        L = rng.uniform(h * 0.35, h * 0.72)
        x0, y0 = w / 2, h - 14
        x1, y1 = x0 + math.cos(a) * L * 0.55, y0 + math.sin(a) * L
        cv.line(int(x0), int(y0), int(x1), int(y1), gr[1])
        rx, ry = rng.uniform(4, 6.5), rng.uniform(2.4, 3.6)
        cv.ellipse(x1, y1, rx, ry, gr[2]); cv.ellipse(x1 - 0.8, y1 - 0.8, rx - 1.4, ry - 1.0, gr[4])
        cv.px(int(x1 - rx * 0.4), int(y1 - 1), gr[6]); cv.line(int(x1 - rx + 1), int(y1), int(x1 + rx - 1), int(y1), gr[1])
    pr = R(pot, 6)
    cv.poly([(w / 2 - 8, h - 15), (w / 2 + 8, h - 15), (w / 2 + 6, h - 1), (w / 2 - 6, h - 1)], pr[3])
    cv.vline(int(w / 2 - 7), h - 14, 12, pr[5]); cv.vline(int(w / 2 + 5), h - 14, 13, pr[1]); cv.hline(int(w / 2 - 8), h - 15, 17, pr[5])
    cv.hline(int(w / 2 - 6), h - 1, 12, pr[0])
    return s

# ---------------------------------------------------------------- wall dressing
BOOK_COLS = ['#c8503c', '#3f6fb0', '#e0b04a', '#5b9a6a', '#8a5aa8', '#e07a4a', '#2f8a8a', '#d8d0c0']

def wall_shelf(w=64, seed=3, items=('books', 'jar', 'ivy', 'robot', 'photo')):
    """floating wall shelf (plank + two brackets) with things on it; the ivy trails over the edge.
    Returns Sprite (h = 34): plank top at y = 24."""
    rng = np.random.default_rng(seed)
    H = 40; top = 24
    s = _sp(w, H); cv = s.cv
    wr = R('#9a6a44', 7)
    x = 2
    for it in items:
        if it == 'books':
            n = int(rng.integers(5, 8))
            for k in range(n):
                bw = int(rng.integers(2, 4)); bh = int(rng.integers(10, 16))
                col = R(BOOK_COLS[int(rng.integers(0, len(BOOK_COLS)))], 6)
                if k == n - 1:                                    # last one leans
                    for j in range(bh):
                        xx = x + int(j * 0.35)
                        cv.hline(xx, top - j - 1, bw + 1, col[3]); cv.px(xx, top - j - 1, col[4])
                    x += bw + 6; continue
                cv.rect(x, top - bh, bw, bh, col[3]); cv.vline(x, top - bh, bh, col[4]); cv.hline(x, top - bh, bw, col[5])
                cv.hline(x, top - bh + 3, bw, col[1]); cv.hline(x, top - 4, bw, col[2])
                x += bw
            x += 2
        elif it == 'jar':
            jr = R('#a8d0d8', 6)
            cv.rect(x, top - 9, 7, 9, jr[2]); cv.rect(x + 1, top - 8, 5, 7, jr[4]); cv.vline(x + 1, top - 8, 7, jr[5])
            cv.rect(x, top - 10, 7, 2, C('#c8a060'))
            for k, c in enumerate(('#d8453a', '#3f6fb0', '#2a2a2a')):
                cv.vline(x + 2 + k, top - 15 + k, 6, C(c))
            s.E[top - 8:top - 1, x + 1:x + 2] = 0.15
            x += 10
        elif it == 'ivy':
            pr = R('#d07a52', 6); gr = R('#5aa05e', 7)
            cv.rect(x, top - 7, 8, 7, pr[3]); cv.hline(x, top - 7, 8, pr[5]); cv.vline(x + 7, top - 6, 6, pr[1])
            for k in range(5):
                cv.px(x + 1 + int(rng.integers(0, 6)), top - 8 - int(rng.integers(0, 3)), gr[4 + k % 2])
            for v in range(3):                                   # trailing vines over the edge
                vx = x + 1 + v * 3; L = int(rng.integers(6, 15))
                for j in range(L):
                    xx = vx + int(round(1.2 * math.sin(j * 0.7 + v)))
                    cv.px(xx, top + 2 + j, gr[2] if j % 3 else gr[5])
                    if j % 3 == 1: cv.px(xx + (1 if v % 2 else -1), top + 2 + j, gr[4])
            x += 12
        elif it == 'robot':                                      # tiny vintage tin robot toy
            rr = R('#c8c0b8', 6)
            cv.rect(x + 1, top - 12, 6, 5, rr[3]); cv.rect(x + 2, top - 11, 4, 2, C('#2a2a3a'))
            cv.px(x + 2, top - 11, C('#ffd27a')); cv.px(x + 5, top - 11, C('#ffd27a'))
            cv.vline(x + 4, top - 14, 2, rr[1]); cv.px(x + 4, top - 15, C('#ff7a5a'))
            cv.rect(x, top - 7, 8, 5, R('#d97757', 6)[3]); cv.rect(x + 1, top - 2, 2, 2, rr[1]); cv.rect(x + 5, top - 2, 2, 2, rr[1])
            s.E[top - 11, x + 2] = s.E[top - 11, x + 5] = 0.5
            x += 10
        elif it == 'photo':
            fr = R('#e8dcc4', 6)
            cv.rect(x, top - 11, 10, 11, fr[1]); cv.rect(x + 1, top - 10, 8, 9, fr[4])
            cv.rect(x + 2, top - 9, 6, 7, C('#9fc3ef')); cv.rect(x + 2, top - 5, 6, 3, C('#6fae6a'))
            cv.px(x + 4, top - 6, C('#d97757')); cv.px(x + 5, top - 6, C('#d97757'))
            x += 12
        elif it == 'globe':
            cv.ellipse(x + 4, top - 6, 3.6, 3.6, C('#5a9ad8')); cv.px(x + 3, top - 8, C('#7ac07a')); cv.px(x + 5, top - 5, C('#7ac07a'))
            cv.rect(x + 2, top - 2, 5, 2, C('#c8a060'))
            x += 10
    # plank + brackets
    cv.rect(0, top, w, 3, wr[3]); cv.hline(0, top, w, wr[5]); cv.hline(0, top + 2, w, wr[1])
    for bx in (6, w - 8):
        cv.rect(bx, top + 3, 2, 6, C('#3a3438')); cv.line(bx + 2, top + 3, bx + 2, top + 8, C('#3a3438'))
    return s

def cork_board(w=44, h=30, seed=5, river=True):
    """framed cork board: pinned notes, a polaroid, a to-do list, a string between two pins."""
    rng = np.random.default_rng(seed)
    s = _sp(w, h); cv = s.cv
    fr = R('#8a6040', 6); kr = R('#c99a64', 6)
    cv.rect(0, 0, w, h, fr[2]); cv.hline(0, 0, w, fr[4]); cv.vline(0, 0, h, fr[4]); cv.hline(0, h - 1, w, fr[0])
    for y in range(2, h - 2):
        for x in range(2, w - 2):
            v = rng.random()
            cv.px(x, y, kr[2] if v < 0.18 else kr[4] if v > 0.85 else kr[3])
    notes = [(3, 4, 10, 9, '#f6d860'), (15, 3, 12, 14, '#fbf8f0'), (30, 5, 10, 8, '#9fe39a'), (4, 16, 9, 9, '#8fd3f5'),
             (30, 16, 11, 10, '#f59bb8')]
    for (x, y, ww, hh, col) in notes:
        rp = R(col, 6)
        cv.rect(x, y, ww, hh, rp[3]); cv.hline(x, y, ww, rp[4]); cv.vline(x + ww - 1, y + 1, hh - 1, rp[2])
        for k in range(1, hh // 2 - 1):
            cv.hline(x + 2, y + 1 + k * 2, int(rng.integers(3, max(4, ww - 2))), rp[1])
        cv.rect(x + ww // 2 - 1, y - 1, 2, 2, C(['#d8453a', '#3f6fb0', '#e0b04a'][int(rng.integers(0, 3))]))
    # polaroid with the river (foreshadow / callback)
    px_, py_ = 16, 18
    cv.rect(px_, py_, 11, 10, C('#f4f0e8')); cv.rect(px_ + 1, py_ + 1, 9, 6, C('#9fc3ef'))
    if river: cv.rect(px_ + 1, py_ + 4, 9, 3, C('#5aa0d8')); cv.hline(px_ + 1, py_ + 4, 9, C('#6fae6a'))
    cv.line(9, 5, 33, 6, C('#c83a3a'))
    return s

def whiteboard(w=46, h=28, lines=('本周', 'OKR'), seed=6):
    rng = np.random.default_rng(seed)
    s = _sp(w, h + 3); cv = s.cv
    fr = R('#b8bcc4', 6)
    cv.rect(0, 0, w, h, fr[2]); cv.rect(1, 1, w - 2, h - 2, C('#f6f7f4')); cv.hline(1, 1, w - 2, C('#ffffff'))
    cv.text(3, 2, lines[0], C('#2f5fb8'), 'zh8')
    for k in range(4):
        y = 13 + k * 3
        cv.px(4, y, C('#2a2a2a')); cv.hline(6, y, int(rng.integers(10, w - 14)), C('#7a8090'))
    cv.ellipse(w - 10, 10, 6, 4, C('#d8453a')); cv.ellipse(w - 10, 10, 5, 3, C('#f6f7f4'))
    cv.rect(4, h, w - 8, 2, fr[1]); cv.rect(8, h - 1, 5, 2, C('#d8453a')); cv.rect(15, h - 1, 5, 2, C('#2f5fb8'))
    return s

def framed_art(w=22, h=18, kind='sun'):
    s = _sp(w, h); cv = s.cv
    fr = R('#6b4a33', 6)
    cv.rect(0, 0, w, h, fr[2]); cv.hline(0, 0, w, fr[4]); cv.rect(2, 2, w - 4, h - 4, C('#f2ead8'))
    ix, iy, iw, ih = 3, 3, w - 6, h - 6
    for yy in range(ih):
        cv.hline(ix, iy + yy, iw, mix(C('#8fb8e8'), C('#ffe0b8'), yy / ih))
    cv.poly([(ix, iy + ih), (ix + iw * 0.35, iy + ih * 0.45), (ix + iw * 0.6, iy + ih), ], C('#6a8a9a'))
    cv.poly([(ix + iw * 0.4, iy + ih), (ix + iw * 0.7, iy + ih * 0.3), (ix + iw, iy + ih)], C('#7a9aa8'))
    cv.ellipse(ix + iw * 0.75, iy + ih * 0.25, 2, 2, C('#ffcf7a'))
    return s

# ---------------------------------------------------------------- desk clutter
def pen_cup(col='#3f6fb0'):
    s = _sp(7, 11); cv = s.cv
    cr = R(col, 6)
    cv.rect(0, 4, 6, 7, cr[3]); cv.vline(0, 4, 7, cr[4]); cv.vline(5, 4, 7, cr[1]); cv.hline(0, 4, 6, cr[5])
    for k, (c, hh) in enumerate((('#e0b04a', 4), ('#d8453a', 3), ('#2a2a2a', 5), ('#5b9a6a', 2))):
        cv.vline(1 + k, 4 - hh, hh, C(c))
    return s

def sticky_pad(col='#f6d860'):
    s = _sp(8, 5); cv = s.cv
    rp = R(col, 6)
    cv.rect(0, 1, 8, 4, rp[1]); cv.rect(0, 0, 8, 3, rp[3]); cv.hline(0, 0, 8, rp[4])
    return s

def snack(kind='cookie'):
    s = _sp(7, 4); cv = s.cv
    cv.rect(0, 1, 7, 3, C('#e8c070')); cv.hline(0, 1, 7, C('#f8dc98'))
    for x in (1, 3, 5): cv.px(x, 2, C('#6a3a20'))
    return s

def pigeon(frame=0):
    """city pigeon (8x6) for a window ledge: frame 0 stand, 1 peck, 2 look back."""
    s = _sp(9, 7); cv = s.cv
    g1, g2, g3 = C('#8a8ea0'), C('#b8bccb'), C('#5a5e70')
    if frame == 1:
        cv.rect(1, 2, 5, 3, g2); cv.rect(0, 3, 2, 1, g3); cv.rect(5, 4, 2, 2, g1); cv.px(7, 5, C('#e0a050'))
        cv.px(6, 4, C('#5a9a8a'))
    else:
        cv.rect(1, 3, 5, 3, g2); cv.rect(0, 4, 2, 1, g3); cv.hline(2, 3, 3, g1)
        hx = 5 if frame == 0 else 4
        cv.rect(hx, 1, 2, 2, g1); cv.px(hx + 1, 2, C('#5a9a8a')); cv.px(hx + (2 if frame == 0 else -1), 1, C('#e0a050'))
        cv.px(hx + 1, 1, C('#1a1a1a'))
    cv.px(3, 6, C('#d0706a')); cv.px(4, 6, C('#d0706a'))
    return s


# ---------------------------------------------------------------- the office, lived-in
def floor_y(room, Z):
    return room.vy + room.Yf * room.D / Z

PAPER_BALLS = [   # (x, Z, seed) - around the bin and in front of the desk (drafts that didn't make it)
    (352, 334, 1), (330, 318, 2), (300, 286, 3), (205, 300, 4), (150, 262, 5), (372, 300, 6), (262, 248, 7), (95, 320, 8),
    (410, 270, 9)]

def dress_office(o, bg, shelf=True, cork=True, art=True, plant=True, coat=True, bin=True, balls=PAPER_BALLS, box_=True,
                 rug=(-92, 92, 236, 314)):
    """bakes the lived-in dressing into the office background GLayer (see Office.background(dressing=True))."""
    room = o.room; Zw = o.Z['wall']
    if rug:
        rg, m = floor_rug(room, *rug); bg.cv.a[m] = rg[m]
    put = lambda spr, x, y, Z, k=0.7, E=None: bg.put(sel_out(spr.rgba, k), int(x), int(y), Z, E=E if E is not None else spr.E)
    if shelf:
        sh = wall_shelf(64, seed=3); put(sh, 152, 80 - 24, Zw - 2, 0.75); o.A['shelf'] = (152, 80)
    if cork:
        cb = cork_board(44, 30, seed=5); bg.put(cb.rgba, 268, 60, Zw - 1, flat=True); o.A['cork'] = (268, 60)
    if art:
        fa = framed_art(22, 18); bg.put(fa.rgba, 346, 70, Zw - 1, flat=True)
    if plant:
        fp = floor_plant(58, seed=2); Z = 384.0; put(fp, 44, floor_y(room, Z) - fp.rgba.shape[0] + 1, Z)
    if box_:
        fb = file_box(26, 16); Z = 362.0; put(fb, 121, floor_y(room, Z) - fb.rgba.shape[0] + 1, Z)
    if coat:
        cs = coat_stand(62); Z = 352.0; put(cs, 421, floor_y(room, Z) - cs.rgba.shape[0] + 1, Z)
    if bin:
        tb = trash_bin(); Z = 336.0; put(tb, 337, floor_y(room, Z) - tb.rgba.shape[0] + 1, Z); o.A['bin'] = (337, Z)
    for (x, Z, sd) in (balls or ()):
        pb = paper_ball(sd, r=3.0 + (sd % 3) * 0.4)
        put(pb, x, floor_y(room, Z) - pb.rgba.shape[0] + 1, Z, 0.8)
    return bg


def floor_rug(room, X0, X1, Z0, Z1, tex=(56, 26), seed=4,
              cols=('#7a2e2e', '#b84a3a', '#e8c88a', '#2f6f6f', '#d98a3a', '#f4e6c8')):
    """perspective-correct kilim rug on the floor plane (X0..X1 world, Z0..Z1 depth).
    tex = pattern resolution in rug texels (u across, v in depth) - nearest sampled, so it stays pixel art.
    -> (rgba (H, W, 4) canvas space, mask)."""
    S = room.surfaces(1)
    from ..persp import FLOOR
    m = (S['id'] == FLOOR) & (S['X'] >= X0) & (S['X'] <= X1) & (S['Z'] >= Z0) & (S['Z'] <= Z1)
    tu, tv = tex
    u = np.clip(((S['X'] - X0) / (X1 - X0) * tu).astype(int), 0, tu - 1)
    v = np.clip(((S['Z'] - Z0) / (Z1 - Z0) * tv).astype(int), 0, tv - 1)
    dk, rd, cr, tl, gd, lt = [np.array(C(c)) for c in cols]
    # pattern in texel space
    P = np.zeros((tv, tu, 4), np.uint8)
    rng = np.random.default_rng(seed)
    for j in range(tv):
        for i in range(tu):
            e = min(i, tu - 1 - i, j, tv - 1 - j)              # distance to the edge (texels)
            if e == 0: c = cr
            elif e == 1: c = dk
            elif e in (2, 3): c = tl if (i + j) % 4 < 2 else gd
            elif e == 4: c = cr
            else:
                cx, cy = (i - (tu - 1) / 2) / (tu / 2), (j - (tv - 1) / 2) / (tv / 2)
                d = abs(cx) * 1.0 + abs(cy) * 1.6
                if d < 0.22: c = gd
                elif d < 0.34: c = cr
                elif d < 0.50: c = tl
                elif d < 0.58: c = cr
                else:
                    c = rd if (abs(cx * 9) + abs(cy * 5)) % 2 < 1.5 else dk
                    for sx in (-0.72, 0.72):                      # small side diamonds
                        if abs(cx - sx) * 1.0 + abs(cy) * 1.6 < 0.16: c = gd
            n = rng.normal(0, 6)
            P[j, i, :3] = np.clip(c.astype(float)[:3] + n, 0, 255); P[j, i, 3] = 255
    rgba = np.zeros((room.H, room.W, 4), np.uint8)
    rgba[m] = P[v[m], u[m]]
    # fringe: a pale row just beyond the near / far edges
    fr = (S['id'] == FLOOR) & (S['X'] >= X0 + 2) & (S['X'] <= X1 - 2) & (((S['Z'] > Z0 - 3) & (S['Z'] < Z0)))
    fr &= (((S['X'] - X0) / (X1 - X0) * tu * 2).astype(int) % 2 == 0)
    rgba[fr] = np.array(C(cols[5])); m = m | fr
    return rgba, m


# ---------------------------------------------------------------- v0.10 desk keepsakes (第五幕 v3)
_DIG35 = {'0': ('111', '101', '101', '101', '111'), '1': ('010', '110', '010', '010', '111'),
          '2': ('111', '001', '111', '100', '111'), '5': ('111', '100', '111', '001', '111')}

def _digits(cv, x, y, s, col):
    for ch in s:
        g = _DIG35.get(ch)
        if g:
            for j, row in enumerate(g):
                for i, b in enumerate(row):
                    if b == '1': cv.px(x + i, y + j, col)
        x += 4

def desk_calendar(month='10', first_col=2, n_days=31, today=27, past=True, ticked=(25,), circled=(32,), fish=True):
    """small tent desk calendar (29 x 29), Monday-first month grid as tiny date dashes.
    today: outlined cell; ticked: little coral check marks (days that happened); circled: hand-drawn red ring + a blue
    fish doodle (a date to keep).  Day numbers > n_days spill into next month (greyed), e.g. 32 = the 1st of next month.
    -> Sprite (rgba/E); bottom row = the stand's foot on the desk."""
    W_, H_ = 29, 29
    s = _sp(W_, H_); cv = s.cv
    paper, paper_d, paper_dd = C('#f4efe4'), C('#ded6c6'), C('#c4baa8')
    ink, ink_l, red, red_d = C('#6a6470'), C('#b4aca4'), C('#e0483a'), C('#a8322a')
    head = R('#d8574a', 6)
    # stand (dark tent edges peeking out at the bottom + shadow foot)
    cv.rect(1, 27, 27, 2, C('#3a3440')); cv.hline(2, 28, 25, C('#26222c'))
    # page
    cv.rect(0, 2, 29, 26, paper); cv.vline(28, 3, 25, paper_d); cv.hline(1, 27, 28, paper_dd)
    cv.vline(0, 3, 24, C('#fbf8f0'))
    # header band + month digits + a tiny 'year' dash
    cv.rect(0, 3, 29, 6, head[3]); cv.hline(0, 3, 29, head[4]); cv.hline(0, 8, 29, head[2])
    _digits(cv, 2, 3, month, C('#fff6ea'))
    cv.hline(21, 5, 5, head[5]); cv.hline(23, 6, 3, head[5])
    # binder: a dark bar + silver rings
    cv.hline(1, 2, 27, C('#4a4652'))
    for x in range(3, 27, 4):
        cv.vline(x, 0, 3, C('#c8ccd8')); cv.px(x, 0, C('#eef0f6')); cv.px(x + 1, 1, C('#7a7e8c'))
    # weekday marks (Sat / Sun in coral)
    for c in range(7):
        cv.hline(2 + 4 * c, 10, 2, red if c >= 5 else ink_l)
    cv.hline(1, 11, 27, paper_d)
    # date grid
    cells = {}
    d, col, row = 1, first_col, 0
    while row < 5:
        cells[d] = (2 + 4 * col, 13 + 3 * row)
        d += 1; col += 1
        if col == 7: col = 0; row += 1
    for dd in ticked:                                              # a soft highlighter swipe behind a day that happened
        if dd in cells:
            x, y = cells[dd]; cv.rect(x - 1, y - 1, 4, 3, C('#f6d860'))
    for dd, (x, y) in cells.items():
        if dd in circled: continue
        nxt = dd > n_days
        c = paper_dd if nxt else (ink_l if (past and dd < today) else ink)
        if (dd - 1 + first_col) % 7 >= 5 and not nxt and not (past and dd < today): c = red_d
        if dd in ticked: c = C('#b08a3a')
        cv.hline(x, y, 2, c)
    if today in cells:                                             # today: a little blue box
        x, y = cells[today]
        b = C('#3f6fb0')
        cv.hline(x - 1, y - 1, 4, b); cv.hline(x - 1, y + 1, 4, b); cv.px(x - 1, y, b); cv.px(x + 2, y, b)
    for dd in circled:                                             # a tiny blue fish in a hand-drawn red ring
        if dd in cells:
            x, y = cells[dd]; cx, cy = x + 0.5, y
            if fish:
                fb = C('#3f7fc8')
                cv.hline(x - 1, y, 3, fb); cv.px(x, y - 1, fb); cv.px(x + 2, y - 1, fb); cv.px(x + 2, y + 1, fb)
            for k in range(26):
                a = -0.5 + 2 * math.pi * 1.06 * k / 25
                px, py = cx + 3.3 * math.cos(a), cy + 2.1 * math.sin(a)
                cv.px(int(round(px)), int(round(py)), red)
    return s

def bobber_stand():
    """a little turned-wood display base (11 x 4) a keepsake bobber stands on; a brass pin in the middle."""
    s = _sp(11, 4); cv = s.cv
    w = R('#8a5a3a', 6)
    cv.rect(1, 0, 9, 1, w[4]); cv.rect(0, 1, 11, 2, w[3]); cv.hline(0, 3, 11, w[1])
    cv.hline(1, 1, 3, w[5]); cv.px(10, 1, w[2]); cv.px(10, 2, w[1])
    cv.hline(4, 2, 3, C('#d8b050')); cv.px(4, 2, C('#f4d878'))           # brass plate
    return s
