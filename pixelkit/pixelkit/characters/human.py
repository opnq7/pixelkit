"""pixelkit.characters.human - chibi human generator matched to Claude v2 proportions.

Big round head (30x27, ~55% of the height) on a short body (22x15 torso + stubby legs), front view
with a `look` turn.  Everything is a parameter so one module casts the whole office:

    from pixelkit.characters import human
    WANG = human.Look(hair='messy', hair_col='#24212c', skin='#f1c7a0', glasses='square', stubble=True,
                      bags=True, cloth='hoodie', cloth_col='#7c8594')
    p = human.draw(WANG, face='tired', arms='type', phase=1, look=(0, 0), glint=1.0, desk_y=...)
    layer.put(p.body.rgba, x - p.ax, y - p.ay, Z, E=p.body.E)    # behind the desk
    ...desk / laptop...
    layer.put(p.hands.rgba, x - p.ax, y - p.ay, Zdesk, E=p.hands.E)
(x, y) = world position of the head's top-centre (hair tufts may poke above it).

hair:    'messy' | 'short' | 'side' | 'long' | 'bun' | 'bald'
glasses: None | 'square' | 'round'          (glint = emissive screen reflection on the lenses)
cloth:   'hoodie' | 'shirt_tie' | 'suit' | 'cardigan' | 'tshirt'
faces:   normal blink closed tired surprised smile soft sad focus o
arms:    rest type chin mouse up wave down hold
"""
import math
from dataclasses import dataclass
from types import SimpleNamespace
import numpy as np
from ..core import Canvas, C, mix
from ..palette import ramp
from ..scene import Sprite

SW, SH = 56, 62
HW, HH = 30, 27
HX, HY = (SW - HW) // 2, 7
AX, AY = HX + HW // 2, HY
TW, TH = 22, 15


@dataclass
class Look:
    hair: str = 'short'
    hair_col: str = '#2b2630'
    skin: str = '#f1c7a0'
    glasses: str = None
    glasses_col: str = '#2a2a33'
    stubble: bool = False
    bags: bool = False
    cloth: str = 'hoodie'
    cloth_col: str = '#7c8594'
    accent: str = '#c8453a'          # tie / inner shirt / cardigan buttons
    blush: bool = True
    seed: int = 0


def _rp(h, n=6, **kw): return [tuple(c) for c in ramp(h, n, **kw)]

def _head_mask():
    m = np.zeros((SH, SW), bool)
    a, b, n = HW / 2.0, HH / 2.0, 2.35
    cx, cy = HX + HW / 2.0 - 0.5, HY + HH / 2.0 - 0.5
    for y in range(HY, HY + HH):
        for x in range(HX, HX + HW):
            dx = abs(x - cx) / a; dy = abs(y - cy) / b
            if y > cy: dy = abs(y - cy) / (b * 0.98)
            if dx ** n + dy ** n <= 1.0: m[y, x] = True
    return m
HEAD_M = _head_mask()

def _edge(m):
    e = np.zeros_like(m)
    e[1:-1, 1:-1] = m[1:-1, 1:-1] & ~(m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:])
    return e

def _paint(cv, m, col):
    cv.a[m] = col

def _hair_mask(style, seed=0):
    """hair silhouette (incl. tufts above / beside the skull) + fringe line."""
    m = np.zeros((SH, SW), bool)
    H = HEAD_M
    fr = HY + 9                                     # fringe base line
    if style == 'bald':
        return m
    rows = {}
    for x in range(HX - 2, HX + HW + 2):
        u = (x - HX) / HW
        if style == 'messy':
            jag = [0, 2, 1, 3, 1, 0, 2, 3, 1, 2, 0, 1, 3, 2, 1, 0, 2, 1, 3, 1, 2, 0, 1, 2, 3, 1, 0, 2, 1, 2, 0, 1, 2, 1]
            rows[x] = fr - 1 + jag[(x - HX + 2 + seed) % len(jag)]
        elif style == 'side':
            rows[x] = int(round(HY + 5 + 6 * u))     # swept fringe, high on the left
        elif style in ('long', 'bun'):
            rows[x] = fr - 1 + (1 if (x // 3) % 2 else 0)
        else:  # short
            rows[x] = fr - 2 + (1 if (x // 4) % 2 else 0)
    for y in range(SH):
        for x in range(SW):
            if not (HX - 2 <= x < HX + HW + 2): continue
            inside = H[y, x] or (H[min(SH - 1, y + 1), x] and y < HY + 3)
            if not inside:
                # 1px puff outside the skull above the ears
                if y < HY + 14 and (H[y, min(SW - 1, x + 1)] or H[y, max(0, x - 1)]):
                    inside = True
                else:
                    continue
            if y < rows[x]: m[y, x] = True
            side = min(x - HX, HX + HW - 1 - x)
            lim = {'long': HY + 25, 'bun': HY + 13, 'messy': HY + 15, 'side': HY + 14, 'short': HY + 13}.get(style, HY + 13)
            if side <= 2 and y < lim: m[y, x] = True          # sideburns / side hair
            if style == 'long' and side <= 4 and y < HY + 24: m[y, x] = True
    if style == 'messy':          # tufts poking above the head
        for (dx, h, lean) in ((-9, 4, -1), (-4, 6, 0), (1, 5, 1), (6, 4, 1), (10, 3, 2), (-12, 2, -1)):
            x0 = AX + dx
            for i in range(h):
                xx = x0 + int(round(lean * i / max(1, h - 1)))
                yy = HY + 1 - i
                if 0 <= yy < SH:
                    w = 3 if i < h - 2 else (2 if i < h - 1 else 1)
                    m[yy, xx:xx + w] = True
        pass
    if style == 'bun':
        for y in range(HY - 7, HY + 1):
            for x in range(AX - 5, AX + 5):
                if (x - AX + 0.5) ** 2 / 25 + (y - HY + 3.5) ** 2 / 16 <= 1: m[y, x] = True
    if style == 'short':
        for (dx, h) in ((-3, 2), (2, 3), (5, 1)):
            m[HY - h + 1:HY + 1, AX + dx:AX + dx + 2] = True
    return m

def draw_head(cv, E, L, face='normal', look=(0, 0), glint=0.0):
    sk = _rp(L.skin, 6, dark=0.42, light=0.95); hr = _rp(L.hair_col, 6, dark=0.10, light=0.62)
    OUT = mix(sk[0], C('#2a1a20'), 0.5)
    lx = int(round(max(-2, min(2, look[0])))); ly = int(round(max(-1, min(1, look[1]))))
    # ears (behind the face); the one on the turn side tucks in
    for side in (-1, 1):
        ex = HX - 2 if side < 0 else HX + HW - 1
        ex += lx if (side < 0) == (lx > 0) else 0
        if side * lx < -1: continue
        cv.rrect(ex, HY + 13, 3, 6, OUT, 1); cv.rect(ex + 1, HY + 14, 1, 4, sk[3])
    H = HEAD_M
    cv.a[H] = sk[3]
    # form shading: right/lower side shadow, cheek light on the left
    ys, xs = np.nonzero(H)
    cx = HX + HW / 2.0
    for y, x in zip(ys, xs):
        u = (x - cx) / (HW / 2); v = (y - HY) / HH
        if u > 0.62 or (v > 0.86 and abs(u) < 0.7): cv.a[y, x] = sk[2]
        elif u < -0.55 and 0.35 < v < 0.8: cv.a[y, x] = sk[4]
    cv.a[_edge(H)] = OUT
    # neck shadow strip under the chin is drawn by the torso; chin highlight
    cv.hline(AX - 3 + lx, HY + HH - 2, 6, sk[2])
    # ---- face features
    fx = AX + lx; fy = HY + ly
    ex_l, ex_r, ey = fx - 7, fx + 5, fy + 15            # eye boxes (2 wide)
    INK = C('#2b1c22'); WH = C('#fff8ee')
    if L.bags:
        for ex in (ex_l, ex_r):
            cv.hline(ex - 1, ey + 4, 4, sk[2]); cv.px(ex, ey + 5, mix(sk[2], C('#8a6a9a'), 0.35))
    if L.stubble:
        st = mix(sk[3], C(L.hair_col), 0.26); EH = _edge(H)
        for y in range(fy + 21, HY + HH - 1):
            for x in range(HX + 4, HX + HW - 4):
                if not H[y, x] or EH[y, x]: continue
                jaw = y >= HY + HH - 4 or (abs(x - fx) > 6 and y >= fy + 23)
                if jaw and (x * 3 + y * 5) % 4 == 0 and not (abs(x - fx + 0.5) < 3 and y <= fy + 23):
                    cv.a[y, x] = st
        cv.px(fx - 4, fy + 23, st); cv.px(fx + 3, fy + 23, st)
    # brows
    BR = hr[1]
    brow = {'tired': ((0, 1), (1, 0)), 'surprised': ((-1, -1), (-1, -1)), 'sad': ((1, 0), (0, 1)), 'focus': ((1, 0), (0, 1)),
            'smile': ((0, 0), (0, 0)), 'soft': ((0, 0), (0, 0))}.get(face, ((0, 0), (0, 0)))
    if face == 'focus': brow = ((0, 1), (1, 0))
    for (ex, (a, b)) in ((ex_l, brow[0]), (ex_r, brow[1])):
        cv.px(ex - 1, ey - 3 + a, BR); cv.px(ex, ey - 3 + (a + b) // 2, BR); cv.px(ex + 1, ey - 3 + (a + b) // 2, BR); cv.px(ex + 2, ey - 3 + b, BR)
    # eyes
    px_, py_ = (1 if look[0] > 0.5 else (-1 if look[0] < -0.5 else 0)), 0
    for ex in (ex_l, ex_r):
        if face in ('blink', 'closed'):
            cv.hline(ex - (1 if face == 'closed' else 0), ey + 1, 3 if face == 'closed' else 2, INK)
        elif face == 'smile':
            cv.px(ex - 1, ey + 1, INK); cv.hline(ex, ey, 2, INK); cv.px(ex + 2, ey + 1, INK)
        elif face == 'tired':
            cv.hline(ex - 1, ey, 4, INK)                       # heavy lid
            cv.rect(ex + max(0, px_), ey + 1, 2, 1, INK); cv.px(ex + max(0, px_) + 1, ey + 1, mix(INK, WH, 0.35))
        elif face == 'surprised':
            cv.rect(ex, ey - 1, 2, 4, INK); cv.px(ex + 1, ey - 1, WH)
        elif face == 'focus':
            cv.hline(ex - 1, ey, 4, INK); cv.rect(ex + px_, ey + 1, 2, 2, INK)
        else:
            cv.rect(ex + px_, ey, 2, 3, INK); cv.px(ex + px_ + 1, ey, WH)
            if face == 'sad': cv.px(ex - 1 if ex == ex_l else ex + 2, ey - 1, INK)
    # nose
    cv.px(fx + 1 if lx >= 0 else fx - 1, fy + 19, sk[2]); cv.px(fx + (1 if lx >= 0 else -1), fy + 20, sk[1])
    # mouth
    mx, my = fx - 1, fy + 22
    MO = C('#8a3a3a')
    if face in ('smile', 'soft'):
        if face == 'smile':
            cv.px(mx - 2, my - 1, INK); cv.hline(mx - 1, my, 4, INK); cv.px(mx + 3, my - 1, INK); cv.hline(mx, my + 1, 2, MO)
        else:
            cv.px(mx - 1, my - 1, INK); cv.hline(mx, my, 2, INK); cv.px(mx + 2, my - 1, INK)
        if L.blush:
            for bx in (ex_l - 2, ex_r + 1):
                cv.hline(bx, ey + 4, 2, C('#f08e8a'))
    elif face in ('surprised', 'o'):
        cv.rect(mx, my - 1, 2, 2, INK)
    elif face in ('sad', 'tired'):
        cv.hline(mx - 1, my, 4, INK); cv.px(mx - 2, my + 1, INK) if face == 'sad' else None
        if face == 'sad': cv.px(mx + 3, my + 1, INK)
    else:
        cv.hline(mx, my, 3, INK)
    # glasses (frames + tinted lenses + emissive screen glint)
    if L.glasses:
        G = C(L.glasses_col); LENS = mix(sk[3], C('#cfeaff'), 0.30)
        gy = ey - 2
        for ex in (ex_l, ex_r):
            x0 = ex - 3; w, h = 8, 7
            if L.glasses == 'round':
                cv.rrect(x0, gy, w, h, G, 3); cv.rrect(x0 + 1, gy + 1, w - 2, h - 2, LENS, 2)
            else:
                cv.rect(x0, gy, w, h, G); cv.rect(x0 + 1, gy + 1, w - 2, h - 2, LENS)
            # re-stamp the eye inside the lens (it was overwritten)
            sub = cv.a  # eyes drawn again below
        cv.hline(ex_l + 5, gy + 2, ex_r - ex_l - 8, G)                     # bridge
        cv.hline(HX, gy + 2, ex_l - 3 - HX, G); cv.hline(ex_r + 5, gy + 2, HX + HW - ex_r - 5, G)   # temples
        # redraw eyes + brows over the lenses
        for ex in (ex_l, ex_r):
            if face in ('blink', 'closed'):
                cv.hline(ex - (1 if face == 'closed' else 0), ey + 1, 3 if face == 'closed' else 2, INK)
            elif face == 'smile':
                cv.px(ex - 1, ey + 1, INK); cv.hline(ex, ey, 2, INK); cv.px(ex + 2, ey + 1, INK)
            elif face == 'tired':
                cv.hline(ex - 1, ey, 4, INK); cv.rect(ex + max(0, px_), ey + 1, 2, 1, INK)
            elif face == 'surprised':
                cv.rect(ex, ey - 1, 2, 4, INK); cv.px(ex + 1, ey - 1, WH)
            elif face == 'focus':
                cv.hline(ex - 1, ey, 4, INK); cv.rect(ex + px_, ey + 1, 2, 2, INK)
            else:
                cv.rect(ex + px_, ey, 2, 3, INK); cv.px(ex + px_ + 1, ey, WH)
        if glint > 0:
            GL = C('#e8fbff')
            for ex in (ex_l, ex_r):
                x0 = ex - 2
                E[gy + 1:gy + 6, x0:x0 + 6] = np.maximum(E[gy + 1:gy + 6, x0:x0 + 6], 0.15 * glint)
                for (gx, gyy, k) in ((ex + 3, gy + 1, 1.0), (ex + 2, gy + 1, 0.8), (ex + 3, gy + 2, 0.7), (ex - 2, gy + 5, 0.5)):
                    cv.px(gx, gyy, mix(LENS, GL, glint * k)); E[gyy, gx] = 0.9 * glint * k
    # hair over everything on the head
    hm = _hair_mask(L.hair, L.seed)
    cv.a[hm] = hr[3]
    ys, xs = np.nonzero(hm)
    for y, x in zip(ys, xs):
        u = (x - (HX + HW / 2)) / (HW / 2)
        if u > 0.45 or not hm[min(SH - 1, y + 1), x]: cv.a[y, x] = hr[2]
        if -0.62 < u < 0.05 and (y - HY) == int(round(3 + 2.2 * (u + 0.3) ** 2 * 4)) : cv.a[y, x] = hr[4]   # sheen arc
        elif -0.5 < u < -0.1 and (y - HY) == int(round(4 + 2.2 * (u + 0.3) ** 2 * 4)): cv.a[y, x] = hr[3 if L.hair == 'bald' else 4]
    e = _edge(np.pad(hm, 1)[1:-1, 1:-1]) | (hm & ~np.roll(hm, 1, 0)) | (hm & ~np.roll(hm, -1, 1)) | (hm & ~np.roll(hm, 1, 1))
    cv.a[e & hm] = hr[0]

def torso_box():
    return AX - TW // 2, HY + HH - 3, TW, TH

def draw_torso(cv, E, L, legs=True):
    x, y, w, h = torso_box()
    cr = _rp(L.cloth_col, 6); sk = _rp(L.skin, 6, dark=0.42, light=0.95)
    OUT = cr[0]
    if legs:
        pr = _rp('#3a4258', 6)
        for lx in (x + 4, x + w - 10):
            cv.rrect(lx, y + h - 3, 6, 8, pr[0], 2); cv.rect(lx + 1, y + h - 2, 4, 6, pr[2]); cv.vline(lx + 1, y + h - 2, 5, pr[3])
            cv.rrect(lx - 1, y + h + 3, 8, 4, C('#2a2226'), 2); cv.rect(lx, y + h + 4, 6, 2, C('#5a4a4a'))
    cv.rect(AX - 3, y - 1, 6, 3, sk[1])                          # neck
    cv.rrect(x, y, w, h, OUT, 5); cv.rrect(x + 1, y + 1, w - 2, h - 2, cr[3], 4)
    cv.rect(x + w - 5, y + 3, 3, h - 5, cr[2]); cv.hline(x + 4, y + h - 2, w - 8, cr[2])
    cv.hline(x + 5, y + 2, w - 12, cr[4]); cv.vline(x + 2, y + 4, 5, cr[4])
    cx = AX
    if L.cloth == 'hoodie':
        cv.rrect(cx - 8, y - 1, 16, 5, OUT, 2); cv.rrect(cx - 7, y, 14, 3, cr[2], 1)        # hood rim behind neck
        cv.rect(cx - 3, y, 6, 2, sk[1])
        for sx in (cx - 3, cx + 2):
            cv.vline(sx, y + 3, 5, C('#e8e4dc')); cv.px(sx, y + 8, C('#b8b2a8'))
        cv.rrect(cx - 7, y + 9, 14, 5, cr[2], 2); cv.hline(cx - 6, y + 9, 12, cr[1])        # kangaroo pocket
    elif L.cloth in ('shirt_tie', 'suit'):
        sh = _rp('#eef0f4', 6)
        if L.cloth == 'suit':
            cv.poly([(cx - 5, y), (cx + 5, y), (cx + 2, y + 10), (cx - 2, y + 10)], sh[4])
            cv.line(cx - 5, y, cx - 1, y + 9, OUT); cv.line(cx + 5, y, cx + 1, y + 9, OUT)
        else:
            cv.a[y:y + h - 1, x + 1:x + w - 1][cv.a[y:y + h - 1, x + 1:x + w - 1, 3] > 0] = sh[4]
            cv.rrect(x, y, w, h, sh[0], 5); cv.rrect(x + 1, y + 1, w - 2, h - 2, sh[4], 4); cv.rect(x + w - 5, y + 3, 3, h - 5, sh[3])
            cv.line(cx - 5, y, cx - 1, y + 2, sh[2]); cv.line(cx + 5, y, cx + 1, y + 2, sh[2])
        tr = _rp(L.accent, 5)
        cv.rect(cx - 1, y + 1, 3, 2, tr[2]); cv.poly([(cx - 1, y + 3), (cx + 1, y + 3), (cx + 2, y + 9), (cx, y + 11), (cx - 2, y + 9)], tr[2])
        cv.vline(cx + 1, y + 4, 5, tr[1])
    elif L.cloth == 'cardigan':
        cv.rect(cx - 2, y, 5, h - 1, _rp(L.accent, 5)[3])
        cv.vline(cx - 3, y, h - 1, OUT); cv.vline(cx + 3, y, h - 1, OUT)
        for by in (y + 4, y + 8, y + 12): cv.px(cx + 4, by, C('#f2e2b8'))
    elif L.cloth == 'tshirt':
        cv.rect(cx - 3, y, 6, 2, sk[1]); cv.hline(cx - 4, y + 2, 8, cr[1])

def _sleeve(cv, pts, cr, width=5):
    for col, pad in ((cr[0], 0), (cr[3], 1)):
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            n = max(abs(x1 - x0), abs(y1 - y0), 1)
            for i in range(n + 1):
                xx = x0 + (x1 - x0) * i / n; yy = y0 + (y1 - y0) * i / n
                cv.rect(int(round(xx - width / 2 + pad)), int(round(yy - width / 2 + pad)), width - 2 * pad, width - 2 * pad, col)
                if pad: cv.px(int(round(xx + width / 2 - 2)), int(round(yy)), cr[2])

HAND_ROWS = ['.ooo.', 'o###o', 'o####', 'o###o', '.ooo.']
HAND_BIG = ['.oooo.', 'o####o', 'o#####', 'o####o', 'o####o', '.oooo.']
def _hand(cv, x, y, sk, big=False):
    """v0.13f: a round chibi mitt (soft skin-tone outline, no near-black box) with a highlight and a 1-px thumb nub."""
    rows = HAND_BIG if big else HAND_ROWS
    OUT = mix(sk[1], C('#3a2028'), 0.35)
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == 'o': cv.px(x + i, y + j, OUT)
            elif ch == '#': cv.px(x + i, y + j, sk[3] if j < len(rows) - 2 else sk[2])
    cv.px(x + 1, y + 1, sk[4]); cv.px(x + 2, y + 1, sk[4])

def draw_arms(cv, E, L, arms='rest', phase=0, desk_y=None, right=True):
    bx, by, bw, bh = torso_box()
    cr = _rp(L.cloth_col if L.cloth not in ('shirt_tie',) else '#eef0f4', 6); sk = _rp(L.skin, 6, dark=0.42, light=0.95)
    dy = desk_y if desk_y is not None else by + bh + 2
    Lx, Rx, sy = bx + 2, bx + bw - 3, by + 4
    if arms == 'rest' and desk_y is None:          # v0.13f standing: arms hang at the sides, mitts at the hips
        hy = by + bh - 4
        _sleeve(cv, [(Lx, sy), (Lx - 3, sy + 5), (Lx - 2, hy)], cr); _hand(cv, Lx - 5, hy - 1, sk)
        if right:
            _sleeve(cv, [(Rx, sy), (Rx + 3, sy + 5), (Rx + 2, hy)], cr); _hand(cv, Rx, hy - 1, sk)
    elif arms in ('rest', 'type', 'mouse'):
        up = (phase % 2) if arms == 'type' else 0
        upR = ((phase + 1) % 2) if arms == 'type' else 0
        ins = 3 if arms == 'type' else 0
        _sleeve(cv, [(Lx, sy), (Lx - 3, sy + 5), (Lx + ins - 1, dy - 1 - up)], cr)
        _hand(cv, Lx + ins - 5, dy - 3 - up, sk)
        if arms == 'mouse':
            mx = Rx + 9 + (phase % 3) - 1
            _sleeve(cv, [(Rx, sy), (Rx + 4, sy + 5), (mx - 1, dy - 1)], cr); _hand(cv, mx - 3, dy - 3, sk)
        elif right:
            _sleeve(cv, [(Rx, sy), (Rx + 3, sy + 5), (Rx - ins + 1, dy - 1 - upR)], cr)
            _hand(cv, Rx - ins - 1, dy - 3 - upR, sk)
    elif arms == 'chin':        # right elbow on the desk, hand under the chin
        _sleeve(cv, [(Lx, sy), (Lx - 3, sy + 5), (Lx - 1, dy - 1)], cr); _hand(cv, Lx - 5, dy - 3, sk)
        ex = Rx + 1
        _sleeve(cv, [(Rx, sy), (Rx + 3, sy + 5), (ex, dy - 1), (AX + 4, HY + HH + 1)], cr)
        _hand(cv, AX + 1, HY + HH - 3, sk, True)
    elif arms == 'up':
        _sleeve(cv, [(Lx, sy), (Lx - 5, sy - 6), (Lx - 7, sy - 12)], cr)
        _sleeve(cv, [(Rx, sy), (Rx + 5, sy - 6), (Rx + 7, sy - 12)], cr)
        _hand(cv, Lx - 11, sy - 17, sk, True); _hand(cv, Rx + 3, sy - 17, sk, True)
    elif arms == 'wave':
        if desk_y is None:
            hy = by + bh - 4; _sleeve(cv, [(Lx, sy), (Lx - 3, sy + 5), (Lx - 2, hy)], cr); _hand(cv, Lx - 5, hy - 1, sk)
        else:
            _sleeve(cv, [(Lx, sy), (Lx - 3, sy + 5), (Lx - 1, dy - 1)], cr); _hand(cv, Lx - 5, dy - 3, sk)
        a = int(round(1.6 * math.sin(phase * 1.3)))
        _sleeve(cv, [(Rx, sy), (Rx + 5, sy - 4), (Rx + 7 + a, sy - 11)], cr)
        _hand(cv, Rx + 4 + a, sy - 16, sk, True)
    elif arms == 'hold':
        _sleeve(cv, [(Lx, sy), (Lx - 2, sy + 5), (Lx + 4, sy + 8)], cr)
        _sleeve(cv, [(Rx, sy), (Rx + 2, sy + 5), (Rx - 4, sy + 8)], cr)
        _hand(cv, Lx + 2, sy + 5, sk); _hand(cv, Rx - 8, sy + 5, sk)
    elif arms == 'down':
        _sleeve(cv, [(Lx, sy), (Lx - 3, sy + 9)], cr); _sleeve(cv, [(Rx, sy), (Rx + 3, sy + 9)], cr)
        _hand(cv, Lx - 6, sy + 8, sk); _hand(cv, Rx, sy + 8, sk)

def reach_arm(L, tx, ty, k=1.0, desk_y=None, pad=40):
    """v0.11: the RIGHT arm reaching from its rest pose toward (tx, ty) (sprite coords, may lie outside the
    56 px sprite) - e.g. fingertips on a photo frame on the desk.  k 0..1 blends rest -> target.
    Returns a Sprite (SW + pad wide, same origin) to be drawn IN FRONT of the props it touches."""
    sp = Sprite(SW + pad, SH)
    bx, by, bw, bh = torso_box()
    cr = _rp(L.cloth_col if L.cloth not in ('shirt_tie',) else '#eef0f4', 6); sk = _rp(L.skin, 6, dark=0.42, light=0.95)
    dy = desk_y if desk_y is not None else by + bh + 2
    Rx, sy = bx + bw - 3, by + 4
    r_el, r_h = (Rx + 3, sy + 5), (Rx + 1, dy - 1)
    t_el = (Rx + 4 + (tx - Rx) * 0.35, max(sy + 3, min(ty, dy - 2)))
    lerp = lambda a, b: (int(round(a[0] + (b[0] - a[0]) * k)), int(round(a[1] + (b[1] - a[1]) * k)))
    el, hd = lerp(r_el, t_el), lerp(r_h, (tx - 3, ty))
    _sleeve(sp.cv, [(Rx, sy), el, hd], cr)
    _hand(sp.cv, hd[0] - 1, hd[1] - 2, sk)
    if k > 0.6:                                   # fingertips over the frame edge: two lighter knuckle pixels
        sp.cv.px(hd[0] + 4, hd[1] - 1, sk[4]); sp.cv.px(hd[0] + 4, hd[1] + 1, sk[3])
    return sp

def draw(L, face='normal', arms='rest', phase=0, look=(0, 0), glint=0.0, desk_y=None, legs=True, head_dy=0, tilt=0.0,
         reach=None):
    """returns SimpleNamespace(body=Sprite, hands=Sprite, ax, ay[, reach=Sprite]) - sprites share coordinates.
    v0.8.1 performance: head_dy = head offset vs the torso (breath / nod), tilt = head roll in degrees (+ clockwise).
    v0.11 reach=(tx, ty, k): the right arm leaves its rest pose for (tx, ty) -> .reach sprite (draw it in front)."""
    body = Sprite(SW, SH); hands = Sprite(SW, SH)
    draw_torso(body.cv, body.E, L, legs)
    if abs(tilt) < 0.5 and not head_dy:
        draw_head(body.cv, body.E, L, face, look, glint)
    else:
        from ..perform import rotsprite
        import numpy as np
        hd = Sprite(SW, SH)
        draw_head(hd.cv, hd.E, L, face, look, glint)
        ha, he = rotsprite(hd.cv.a, hd.E, tilt, (AX, HY + HH - 1)) if abs(tilt) >= 0.5 else (hd.cv.a, hd.E)
        if head_dy: ha = np.roll(ha, head_dy, 0); he = np.roll(he, head_dy, 0)
        m = ha[..., 3] > 0
        body.cv.a[m] = ha[m]; body.E[m] = he[m]
    rk = reach is not None and reach[2] > 0.02
    draw_arms(hands.cv, hands.E, L, arms, phase, desk_y, right=not rk)
    ns = SimpleNamespace(body=body, hands=hands, ax=AX, ay=AY, reach=None)
    if rk: ns.reach = reach_arm(L, reach[0], reach[1], reach[2], desk_y)
    return ns

def sheet(path, looks, faces=('normal', 'blink', 'tired', 'surprised', 'smile', 'soft', 'sad', 'focus', 'o', 'closed'),
          arms=('rest', 'type', 'chin', 'mouse', 'up', 'wave', 'hold', 'down'), scale=5, bg=(70, 62, 86), glint=0.0):
    """review sheet: one row per Look (cycling faces/arms) - looks: list of Look."""
    import cv2
    rows = []
    for li, L in enumerate(looks):
        tiles = []
        for i, f in enumerate(faces):
            p = draw(L, face=f, arms=arms[i % len(arms)], phase=i, look=((-2, 0), (0, 0), (2, 0))[i % 3] if i >= 7 else (0, 0), glint=glint)
            a = p.body.cv.a.copy(); h = p.hands.cv.a; m = h[..., 3] > 0; a[m] = h[m]
            img = np.zeros((SH, SW, 3), np.uint8) + np.array(bg, np.uint8)
            al = a[..., 3:4] / 255.0
            img = (img * (1 - al) + a[..., :3] * al).astype(np.uint8)
            tiles.append(cv2.resize(img, (SW * scale, SH * scale), interpolation=cv2.INTER_NEAREST))
        rows.append(np.concatenate(tiles, 1))
    cv2.imwrite(path, np.concatenate(rows, 0)[..., ::-1])

WANG = Look(hair='messy', hair_col='#25212b', skin='#efc49c', glasses='square', stubble=True, bags=True,
            cloth='hoodie', cloth_col='#7a8392', seed=1)
