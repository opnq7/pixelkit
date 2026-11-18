"""pixelkit.characters.person - slender townsfolk (v2 extras), ~3 heads tall.

Why a second human generator: characters.human is the desk chibi (huge 30x27 head, stubby body) - fine
behind a desk, but walking on a street next to Claude it reads as squat and toy-like.  Townsfolk are
taller and leaner than Claude (head 22x21, total ~64 px vs Claude's 58) without going realistic:
still a big friendly head, dot eyes with a highlight, rosy cheeks, 1px dark-warm outlines (sel-out).

View: 3/4, body toward camera, head turned toward the walking direction (+x; flip=True for -x).
Light from the upper left (the street's low morning sun) -> lit left edges, shaded right edges.

    from pixelkit.characters import person as P
    L = P.Look(hair='bun', hair_col='#4a3226', top='cardigan', top_col='#c88a6a', inner='#f4e8d0')
    s = P.draw(L, pose='walk', phase=0.25, arms='coffee', face='normal')   # -> SimpleNamespace
    layer.put(s.rgba, x - s.ax, foot - s.fy, Z, E=s.E)                       # (ax, fy) = feet centre / ground row

poses : stand | walk (phase 0..1, one full stride cycle) | sit (on a seat at s.seat_y)
arms  : down swing coffee phone bag leash type wave point hold wipe cross chin
faces : normal blink closed smile happy talk surprised shock sad cry tired down focus soft
hair  : short messy side long bun bald bob ponytail cap      (+ Look.hat='straw': wide-brim straw hat over any hair)
top   : tee cardigan hoodie shirt jacket suit dress
"""
import math
from dataclasses import dataclass, field
from types import SimpleNamespace
import numpy as np
from ..core import C, mix
from ..palette import ramp

SW, SH = 48, 86
AX = 24                         # body centre column
HW, HH = 24, 22
HX, HY = AX - HW // 2, 18       # head box (top row 18)
SHOULDER_Y = HY + HH + 1        # 41
TORSO_H = 16
HIP_Y = SHOULDER_Y + TORSO_H    # 57
THIGH, SHIN = 10, 9
GROUND = HIP_Y - 1 + THIGH + SHIN + 2     # first row BELOW the shoes when standing (77)
INK = C('#2b1c22'); WH = C('#fff8ee'); OUTL = C('#2e1a22')


@dataclass
class Look:
    hair: str = 'short'
    hair_col: str = '#2b2630'
    skin: str = '#f1c7a0'
    glasses: str = None             # None | 'round' | 'square'
    glasses_col: str = '#2a2a33'
    stubble: bool = False
    beard: bool = False
    bags: bool = False
    top: str = 'tee'
    top_col: str = '#7c8594'
    inner: str = '#f4f0e8'          # inner shirt / tie / print colour
    tie: str = None                 # None | hex (shirt / suit)
    bottom: str = 'pants'           # pants | shorts | skirt
    bottom_col: str = '#3a4258'
    shoes: str = '#3a2a2a'
    hat_col: str = '#c84a3a'        # for hair='cap'
    hat: str = None                 # None | 'straw' (wide-brim straw hat over any hair)
    straw_col: str = '#d8b46a'
    band_col: str = '#6a2e26'
    blush: bool = True
    flower: bool = False            # boutonniere (wedding)
    wrinkles: bool = False          # crow's feet + a forehead line (older faces)
    seed: int = 0


def _rp(h, n=6, **kw): return [tuple(int(v) for v in c) for c in ramp(h, n, **kw)]

def _edge(m):
    p = np.pad(m, 1)
    inner = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m & ~inner

def _yx():
    return np.mgrid[0:SH, 0:SW].astype(np.float32)
YY, XX = _yx()

def capsule(p0, p1, w):
    """bool mask of a thick segment (limb)."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy + 1e-6
    t = np.clip(((XX - x0) * dx + (YY - y0) * dy) / L2, 0, 1)
    px, py = x0 + t * dx, y0 + t * dy
    return (XX - px) ** 2 + (YY - py) ** 2 <= (w / 2.0) ** 2

def shade_part(a, m, base, light_edge=True, out=True, hi=True, shade_frac=0.30, bottom=0, rp=None):
    """cel-shade a mask: base, right-side shade, lit 1px left edge, dark sel-out outline."""
    if not m.any(): return
    r = rp or _rp(base, 6)
    a[m] = r[3]
    ys, xs = np.nonzero(m)
    rows = {}
    for y, x in zip(ys, xs):
        lo, hi_ = rows.get(y, (x, x)); rows[y] = (min(lo, x), max(hi_, x))
    for y, x in zip(ys, xs):
        lo, hi_ = rows[y]; w = hi_ - lo + 1
        s = (x - lo) / max(1, w - 1)
        if w >= 4 and s > 1 - shade_frac: a[y, x] = r[2]
        if hi and light_edge and w >= 4 and x == lo + 1: a[y, x] = r[4]
    if bottom:
        yb = ys.max()
        for y, x in zip(ys, xs):
            if y > yb - bottom: a[y, x] = r[2]
    if out:
        e = _edge(m)
        a[e] = mix(r[0], OUTL, 0.45)
        # lit sel-out: top/left outline a bit lighter
        up = np.roll(m, 1, 0); lf = np.roll(m, 1, 1)
        lit = e & (~lf) & up & (YY < HIP_Y + 30)
        a[lit] = r[1]

# ---------------------------------------------------------------- legs
def leg_angles(pose, phase, side):
    """(thigh, shin) angles in degrees from straight down; + = forward (toward +x)."""
    if pose == 'sit':
        return 82.0, -6.0
    if pose != 'walk':
        return (2.0, 0.0) if side else (-2.0, 0.0)
    p = (phase + (0.5 if side else 0.0)) % 1.0
    th = 24.0 * math.sin(2 * math.pi * p)
    bend = 42.0 * max(0.0, math.cos(2 * math.pi * p)) ** 1.3       # knee folds while the leg swings forward
    return th, th - bend

def _pt(p, ang, ln):
    a = math.radians(ang)
    return (p[0] + math.sin(a) * ln, p[1] + math.cos(a) * ln)

def legs_geom(pose, phase, hip_y=HIP_Y):
    out = []
    for side in (0, 1):                                       # 0 = back leg (drawn first, darker)
        th, sh = leg_angles(pose, phase, side)
        if pose == 'walk': hx = AX + (2 if th > 0 else -2)       # the leading leg hangs from the front hip (no X-crossing)
        else: hx = AX - 2 + (4 if side else 0)
        hip = (hx, hip_y - 1)
        knee = _pt(hip, th, THIGH); ank = _pt(knee, sh, SHIN)
        out.append((hip, knee, ank, th, sh))
    return out

def draw_legs(a, L, pose, phase, hip_y):
    g = legs_geom(pose, phase, hip_y)
    pr = _rp(L.bottom_col, 6); shr = _rp(L.shoes, 6, dark=0.12, light=0.7)
    sk = _rp(L.skin, 6, dark=0.42, light=0.95)
    for i, (hip, knee, ank, th, sh) in enumerate(g):
        thigh = capsule(hip, knee, 5.8); shin = capsule(knee, ank, 5.0)
        m = thigh | shin
        if L.bottom == 'shorts':
            mid = ((hip[0] + knee[0]) / 2 + 0.5, (hip[1] + knee[1]) / 2 + 1.5)
            pm = capsule(hip, mid, 5.6); skm = m & ~pm
            shade_part(a, skm, None, rp=[mix(c, OUTL, 0.15 * (1 - i)) for c in sk])
            shade_part(a, pm, None, rp=[mix(c, OUTL, 0.18 * (1 - i)) for c in pr])
        elif L.bottom == 'skirt':
            shade_part(a, m, None, rp=[mix(c, OUTL, 0.15 * (1 - i)) for c in sk], hi=False)
            if i == 1:
                km = np.zeros((SH, SW), bool)
                for k in range(11):
                    w = 15 + (k * 5) // 10
                    km[hip_y - 2 + k, AX - w // 2:AX - w // 2 + w] = True
                shade_part(a, km, None, rp=pr, shade_frac=0.3)
                a[hip_y + 8, AX - 9:AX + 9][km[hip_y + 8, AX - 9:AX + 9]] = pr[1]
        else:
            shade_part(a, m, None, rp=[mix(c, OUTL, 0.22 * (1 - i)) for c in pr])
        # shoe: 7x3 pointing forward, sole flat on the shin direction's end
        fx, fy = ank
        sm = np.zeros((SH, SW), bool)
        x0 = int(round(fx - 2.5)); y0 = int(round(fy - 1))
        sm[y0:y0 + 3, x0:x0 + 7] = True
        sm[y0, x0 + 5:x0 + 7] = False                              # rounded toe
        if pose == 'walk' and sh > 15:                             # toe-off: tilt (lift the heel)
            sm[y0 + 2, x0:x0 + 2] = False
        shade_part(a, sm, None, rp=[mix(c, OUTL, 0.2 * (1 - i)) for c in shr], hi=False, shade_frac=0.2)
        a[y0 + 2, x0 + 1:x0 + 6][sm[y0 + 2, x0 + 1:x0 + 6]] = mix(shr[0], OUTL, 0.3)    # sole line
    return g

# ---------------------------------------------------------------- torso
TW = [10, 14, 15, 16, 16, 16, 16, 15, 15, 14, 14, 14, 15, 15, 15, 15]
def torso_mask(top, y0=SHOULDER_Y, h=TORSO_H):
    m = np.zeros((SH, SW), bool)
    widths = TW[:h]
    for i, w in enumerate(widths):
        x0 = AX - w // 2
        m[y0 + i, x0:x0 + w] = True
    if top == 'dress':                                  # A-line skirt to the knee
        for i in range(10):
            w = 14 + i
            x0 = AX - w // 2
            m[y0 + h + i, x0:x0 + w] = True
    if top == 'hoodie':                                 # hood bulge around the neck
        m[y0 - 1, AX - 6:AX + 6] = True
    return m

def draw_torso(a, E, L, y0):
    m = torso_mask(L.top, y0)
    cr = _rp(L.top_col, 6)
    shade_part(a, m, None, rp=cr, shade_frac=0.32)
    ir = _rp(L.inner, 6)
    t = L.top
    if t in ('cardigan', 'jacket', 'suit'):
        # open front: inner shirt wedge, lapels
        for i in range(1, TORSO_H - 1):
            w = 2 if i < 3 else (3 if i < 10 else 2)
            if t == 'suit': w = 3 if i < 8 else 2
            a[y0 + i, AX - w // 2 - 1:AX - w // 2 - 1 + w] = ir[4 if i < 3 else 3]
        a[y0 + 1:y0 + TORSO_H - 1, AX - 3] = cr[1]                     # placket line
        if t == 'cardigan':
            for i in (4, 8, 12): a[y0 + i, AX - 4] = ir[2]   # buttons
        if t in ('jacket', 'suit'):
            for i in range(1, 7): a[y0 + i, AX - 4 - (i // 3)] = cr[1]; a[y0 + i, AX + 1 + (i // 3)] = cr[1]  # lapels
    elif t == 'shirt':
        a[y0 + 1, AX - 3:AX + 2] = ir[4]; a[y0 + 2, AX - 2] = cr[1]; a[y0 + 2, AX] = cr[1]   # collar
        for i in (5, 8, 11): a[y0 + i, AX - 1] = cr[1]
    elif t == 'hoodie':
        a[y0 - 1, AX - 5:AX + 5] = cr[2]; a[y0 - 1, AX - 6] = cr[0]; a[y0 - 1, AX + 5] = cr[0]
        a[y0 + 2:y0 + 6, AX - 3] = ir[4]; a[y0 + 2:y0 + 5, AX + 1] = ir[4]          # strings
        a[y0 + 10, AX - 5:AX + 4] = cr[1]; a[y0 + 11:y0 + 14, AX - 5] = cr[1]; a[y0 + 11:y0 + 14, AX + 3] = cr[1]  # pocket
    elif t == 'tee':
        a[y0, AX - 3:AX + 2] = _rp(L.skin, 6, dark=0.42, light=0.95)[2]                # neckline
        if L.inner and L.inner.lower() not in ('#f4f0e8',):
            a[y0 + 6:y0 + 8, AX - 6:AX + 6] = ir[3]                                    # stripe print
    elif t == 'dress':
        a[y0 + 1, AX - 2:AX + 1] = _rp(L.skin, 6, dark=0.42, light=0.95)[3]
        a[y0 + 9, AX - 7:AX + 7] = ir[3]                                                # waist ribbon
    if L.tie and t in ('shirt', 'suit'):
        tr = _rp(L.tie, 5)
        a[y0 + 1, AX - 2:AX] = tr[2]
        for i in range(2, 9): a[y0 + i, AX - 2:AX] = tr[3 if i < 8 else 2]
        a[y0 + 2:y0 + 8, AX - 1] = tr[2]
    if L.flower:
        a[y0 + 4, AX + 3:AX + 5] = C('#f4f0f4'); a[y0 + 3, AX + 4] = C('#ffffff'); a[y0 + 5, AX + 4] = C('#7ab05a')
    # belt / hem shadow
    if t not in ('dress', 'hoodie'):
        a[y0 + TORSO_H - 1, AX - 8:AX + 8][m[y0 + TORSO_H - 1, AX - 8:AX + 8]] = cr[1]
    return m

# ---------------------------------------------------------------- arms
def arm_pose(arms, phase, side, pose):
    """-> (upper angle, fore angle) in degrees from straight down (+ = forward/+x), for side 0 (left/back) / 1 (right/front)."""
    sw = 15.0 * math.sin(2 * math.pi * (phase + (0.0 if side else 0.5))) if pose == 'walk' else 0.0
    base = {'down': (4 - 8 * (1 - side), 2 - 6 * (1 - side))}
    if arms in ('down',) or (arms == 'swing' and pose != 'walk'):
        return (-4.0, -1.0) if side == 0 else (4.0, 2.0)
    if arms == 'swing':
        return (-sw - 4 if side == 0 else -sw + 4, -sw * 0.6 + (8 if -sw > 0 else 0) + (-4 if side == 0 else 4))
    spec = {
        'coffee': {1: (8, 95)},
        'phone':  {1: (6, -150), 0: (-4, 2)},
        'bag':    {0: (-10, -10)},
        'leash':  {1: (30, 40)},
        'type':   {0: (35, 95), 1: (40, 100)},
        'wave':   {1: (150, 175)},
        'point':  {1: (150, 160)},
        'hold':   {0: (-2, 110), 1: (12, 120)},
        'wipe':   {1: (20, 165)},
        'cross':  {0: (14, 105), 1: (-6, 95)},
        'chin':   {1: (16, 160)},
        'give':   {0: (-2, 110), 1: (80, 94)},      # front arm straight out (handing something over)
        'offer':  {0: (-2, 110), 1: (50, 110)},     # front hand held out low in front of him (palm up)
        'catch':  {0: (-2, 110), 1: (38, 150)},     # front hand up at the chest (holding a small thing)
        'flick':  {0: (-2, 110), 1: (70, 160)},     # front hand raised, a little dismissive flick
        'reel':   {0: (24, 140), 1: (30, 118)},     # both hands up at the rod butt / reel
    }.get(arms, {})
    if side in spec: return spec[side]
    if pose == 'walk': return (-sw - 4 if side == 0 else -sw + 4, -sw * 0.6 + (-4 if side == 0 else 4))
    return (-6.0, -2.0) if side == 0 else (6.0, 4.0)

def draw_arm(a, L, side, ua, fa, y0):
    cr = _rp(L.top_col if L.top != 'dress' else L.top_col, 6); sk = _rp(L.skin, 6, dark=0.42, light=0.95)
    sx = AX - 7 + (13 if side else 0)
    sh = (sx + 0.5, y0 + 2.5)
    el = _pt(sh, ua, 7.0); hd = _pt(el, fa, 6.0)
    m = capsule(sh, el, 4.6) | capsule(el, hd, 3.8)
    sleeve = cr
    if L.top in ('tee', 'dress'):                            # short sleeves: forearm is skin
        up = capsule(sh, el, 4.8)
        shade_part(a, m & ~up, None, rp=sk, hi=False)
        shade_part(a, up, None, rp=sleeve)
    else:
        shade_part(a, m, None, rp=sleeve)
    hm = capsule(hd, hd, 4.6)
    shade_part(a, hm, None, rp=sk, hi=False, shade_frac=0.4)
    return (int(round(hd[0])), int(round(hd[1])))

# ---------------------------------------------------------------- head
def _head_mask(y0):
    m = np.zeros((SH, SW), bool)
    a_, b_, n = HW / 2.0, HH / 2.0, 2.3
    cx, cy = HX + HW / 2.0 - 0.5, y0 + HH / 2.0 - 0.5
    dx = np.abs(XX - cx) / a_; dy = np.abs(YY - cy) / b_
    dy = np.where(YY > cy, np.abs(YY - cy) / (b_ * 0.97), dy)
    m = dx ** n + dy ** n <= 1.0
    return m

def _hair(style, y0, seed=0, eo=0):
    """hair mask for a head turned right (face on the right, back of the skull on the left)."""
    H = _head_mask(y0)
    m = np.zeros((SH, SW), bool)
    if style == 'bald':
        # horseshoe of hair round the back + sides, shiny dome
        band = H & (YY >= y0 + 6) & (YY <= y0 + 12) & ((XX <= HX + 4) | (XX >= HX + HW - 3))
        return band
    fr = {}
    for x in range(HX - 1, HX + HW + 1):
        u = (x - HX) / HW
        if style == 'side':   f = y0 + 4 + int(round(5 * u))
        elif style == 'messy': f = y0 + 6 + [0, 1, -1, 1, 0, 2, 0, 1][(x + seed) % 8]
        elif style in ('long', 'bun', 'ponytail', 'bob'): f = y0 + 6 + (1 if (x // 3) % 2 else 0) - (1 if u > 0.75 else 0)
        elif style == 'cap':  f = y0 + 6
        else:                 f = y0 + 5 + (1 if (x // 4) % 2 else 0)
        fr[x] = f
    for x, f in fr.items():
        col = H[:, x] if 0 <= x < SW else None
        if col is None: continue
        m[:f, x] |= H[:f, x]
    # 1px puff outside the skull (volume)
    grow = np.zeros_like(m)
    grow[1:, :] |= m[:-1, :] & False
    pm = np.pad(m, 1)
    grow = (pm[:-2, 1:-1] | pm[1:-1, :-2] | pm[1:-1, 2:]) & ~H & (YY < y0 + 10)
    m |= grow
    # back of the head (left) - hair comes down over the ear zone
    back = {'long': y0 + HH + 4, 'bob': y0 + 17, 'bun': y0 + 12, 'ponytail': y0 + 12, 'messy': y0 + 13,
            'side': y0 + 12, 'short': y0 + 11, 'cap': y0 + 12}.get(style, y0 + 11)
    m |= H & (XX <= HX + 3 + eo) & (YY < back + eo // 2)
    if eo >= 4: m |= H & (XX <= HX + 1 + eo // 2) & (YY < back + eo)        # profile: the back of the skull
    m |= H & (XX >= HX + HW - 2) & (YY < y0 + (13 if style in ('long', 'bob') else 9))      # sideburn on the face side
    if style == 'long':
        m |= (XX >= HX - 1) & (XX <= HX + 4) & (YY >= y0 + 4) & (YY < y0 + HH + 5)
        m |= (XX >= HX + HW - 3) & (XX <= HX + HW) & (YY >= y0 + 5) & (YY < y0 + HH + 1)
    if style == 'bob':
        m |= (XX >= HX - 1) & (XX <= HX + 3) & (YY >= y0 + 4) & (YY < y0 + 18)
        m |= (XX >= HX + HW - 3) & (XX <= HX + HW) & (YY >= y0 + 5) & (YY < y0 + 16)
    if style == 'bun':
        cx_, cy_ = AX - 3, y0 - 2
        m |= ((XX - cx_) / 5.0) ** 2 + ((YY - cy_) / 4.2) ** 2 <= 1.0
    if style == 'ponytail':
        m |= capsule((HX + 1, y0 + 8), (HX - 3, y0 + 20), 4.5)
        m |= capsule((HX + 2, y0 + 6), (HX - 1, y0 + 9), 4.0)
    if style == 'messy':
        for (dx, h, lean) in ((-7, 3, -1), (-2, 4, 0), (3, 3, 1), (7, 2, 1)):
            for i in range(h):
                xx = AX + dx + int(round(lean * i / max(1, h - 1))); yy = y0 - i
                m[yy, xx:xx + (2 if i < h - 1 else 1)] = True
    if style == 'short':
        m[y0 - 1, AX - 2:AX + 2] = True; m[y0 - 2, AX - 1:AX + 1] = True
    return m

def draw_head(a, E, L, face, y0, tilt=0, glint=0.0, turn=1.0):
    """turn (v0.7): 0 = facing the camera, 1 = the usual 3/4 view (face toward +x), 1.6 = full profile toward +x."""
    sk = _rp(L.skin, 6, dark=0.42, light=0.95); hr = _rp(L.hair_col, 6, dark=0.12, light=0.66)
    H = _head_mask(y0)
    turn = max(0.0, min(1.6, turn))
    prof = turn >= 1.45
    eo = int(round(max(0.0, turn - 1.0) * 10))          # the ear / sideburn travel back->centre as the head turns away
    # ear on the back side
    em = np.zeros((SH, SW), bool)
    if turn >= 0.45: em[y0 + 10:y0 + 15, HX + 3 + eo:HX + 6 + eo] = True
    # head
    a[H] = sk[3]
    ys, xs = np.nonzero(H)
    for y, x in zip(ys, xs):
        u = (x - (HX + HW / 2)) / (HW / 2); v = (y - y0) / HH
        if u > 0.70 or v > 0.90: a[y, x] = sk[2]
        elif u < -0.55 and 0.35 < v < 0.8: a[y, x] = sk[4]
    if prof:                                            # profile: nape / jaw corner behind the ear in shade
        a[H & (XX < HX + 9) & (YY > y0 + 13)] = sk[2]
    a[_edge(H)] = mix(sk[0], OUTL, 0.5)
    fx = AX + int(round(3 * min(turn, 1.0) + 4 * max(0.0, turn - 1.0)))    # face centre (turned right)
    if turn < 0.45: fx = AX - 1
    ey = y0 + 11 + tilt
    exl, exr = fx - 5, fx + 3
    if prof: exl, exr = -99, AX + 7
    # brows
    BR = hr[1]
    bro = {'sad': ((1, 0), (0, 1)), 'cry': ((1, 0), (0, 1)), 'surprised': ((-1, -1), (-1, -1)), 'shock': ((-2, -1), (-1, -2)),
           'tired': ((0, 1), (1, 0)), 'focus': ((1, 0), (0, 1))}.get(face, ((0, 0), (0, 0)))
    if face != 'down':
        for ex, (p, q) in ((exl, bro[0]), (exr, bro[1])):
            if ex < 0: continue
            a[ey - 3 + p, ex - 1] = BR; a[ey - 3 + (p + q) // 2, ex] = BR; a[ey - 3 + q, ex + 1] = BR
    # eyes
    for k, ex in enumerate((exl, exr)):
        w = 2
        if ex < 0: continue
        if face in ('blink', 'closed'):
            a[ey + 1, ex - (1 if face == 'closed' else 0):ex + 2] = INK
        elif face in ('smile', 'happy', 'soft'):
            a[ey + 1, ex - 1] = INK; a[ey, ex:ex + 2] = INK; a[ey + 1, ex + 2] = INK
        elif face == 'down':
            a[ey + 2, ex - 1:ex + 2] = INK
        elif face == 'tired':
            a[ey, ex - 1:ex + 3] = INK; a[ey + 1, ex:ex + 2] = INK
        elif face in ('surprised', 'shock'):
            a[ey - 1:ey + 3, ex:ex + 2] = INK; a[ey - 1, ex + 1] = WH
            if face == 'shock': a[ey - 1:ey + 3, ex - 1] = INK
        elif face == 'focus':
            a[ey, ex - 1:ex + 3] = INK; a[ey + 1:ey + 3, ex:ex + 2] = INK
        else:
            a[ey:ey + 3, ex:ex + 2] = INK; a[ey, ex + 1] = WH
        if face in ('sad', 'cry') and face not in ('blink',):
            pass
    if L.bags:
        for ex in (exl, exr):
            if ex >= 0: a[ey + 4, ex - 1:ex + 2] = sk[2]
    # nose (on the turned side) + mouth
    if prof:                                       # profile: the nose breaks the silhouette, the mouth sits forward
        nx_ = HX + HW - 1
        a[ey + 2:ey + 5, nx_] = sk[3]; a[ey + 3:ey + 5, nx_ + 1] = sk[3]; a[ey + 5, nx_] = sk[1]
        a[ey + 2, nx_ + 1] = mix(sk[0], OUTL, 0.5); a[ey + 3:ey + 5, nx_ + 2] = mix(sk[0], OUTL, 0.5); a[ey + 5, nx_ + 1] = mix(sk[0], OUTL, 0.5)
        fx = AX + 7
    else:
        a[ey + 4, fx + 1] = sk[1]
    my = ey + 7
    MO = C('#8a3a3a'); TONG = C('#e07a6e')
    if face in ('smile', 'happy'):
        a[my - 1, fx - 2] = INK; a[my, fx - 1:fx + 2] = INK; a[my - 1, fx + 2] = INK
        if face == 'happy': a[my + 1, fx - 1:fx + 1] = MO
    elif face == 'soft':
        a[my, fx - 1:fx + 1] = INK; a[my - 1, fx - 2] = INK
    elif face == 'talk':
        a[my - 1, fx - 1:fx + 2] = INK; a[my, fx - 1:fx + 2] = MO; a[my + 1, fx - 1:fx + 2] = INK
    elif face in ('surprised',):
        a[my - 1:my + 1, fx - 1:fx + 1] = INK
    elif face == 'shock':
        a[my - 2:my + 2, fx - 2:fx + 2] = INK; a[my, fx - 1:fx + 1] = TONG
    elif face in ('sad', 'cry', 'tired'):
        a[my, fx - 1:fx + 2] = INK; a[my + 1, fx - 2] = INK; a[my + 1, fx + 2] = INK
    elif face == 'down':
        a[my + 1, fx - 1:fx + 1] = INK
    else:
        a[my, fx - 1:fx + 1] = INK
    if face == 'cry':
        TE = C('#8ad0ff')
        for ex in (exl, exr):
            if ex >= 0: a[ey + 3:ey + 6, ex] = TE; E[ey + 3:ey + 6, ex] = 0.25
    if L.blush and face not in ('shock', 'down'):
        BL = mix(sk[3], C('#f07a7a'), 0.55)
        if exl >= 0: a[ey + 4, exl - 2:exl] = BL
        if prof: a[ey + 4, exr - 3:exr - 1] = BL
        else: a[ey + 4, exr + 2:exr + 4] = BL
    if L.stubble:
        st = mix(sk[3], C(L.hair_col), 0.30)
        jaw = H & (YY >= y0 + HH - 4) & ~_edge(H) & (XX > HX + 5) & ((XX * 3 + YY * 5) % 3 == 0)
        jaw &= ~((YY == my) & (np.abs(XX - fx) < 2))
        a[jaw] = st
    if L.beard:            # short full beard: textured, a jagged lower edge, the mouth left open, a moustache over it
        bc = _rp(L.hair_col, 6, dark=0.25, light=0.85)
        jaw = H & (YY >= my - 2) & (XX > HX + 5 + eo)
        jaw |= H & (YY >= y0 + 12) & (XX > HX + 5 + eo) & (XX < HX + 9 + eo)           # sideburn toward the ear
        jaw &= ~((YY == my) & (np.abs(XX - fx) < 2))
        ys, xs = np.nonzero(jaw)
        # v0.7: calmer texture (the old checker read as pixel noise in close-ups): a flat mid tone, a soft
        # light band under the moustache, sparse vertical strands, a shade row along the lower edge
        low = {}
        for y, x in zip(ys, xs): low[x] = max(low.get(x, -1), y)
        for y, x in zip(ys, xs):
            c = bc[3]
            if y == my - 2 or y == my - 1: c = bc[4]
            if (x * 5 + L.seed) % 4 == 0 and y >= my + 1 and (y - my) % 3 != 0: c = bc[2]
            if y == low[x]: c = bc[2]
            a[y, x] = c
        a[my - 1, fx - 2:fx + 3] = bc[1]; a[my - 1, fx - 3] = bc[2]; a[my - 1, fx + 3] = bc[2]     # moustache
        a[my, fx - 1:fx + 1] = INK if face not in ('talk',) else a[my, fx - 1:fx + 1]
        cy_ = y0 + HH
        for x in range(HX + 7 + eo, HX + HW - 2):                                       # chin tufts below the jaw line
            if (x + L.seed) % 3 == 0 and H[cy_ - 1, x]: a[cy_, x] = bc[2]
    if L.wrinkles:
        WR = sk[1]
        for ex in (exl, exr):
            if ex >= 0: a[ey + 3, ex + 2] = WR
        if prof: a[ey - 1, exr - 2] = WR; a[ey + 1, exr - 3] = WR
        else: a[ey - 1, exr + 3] = WR; a[ey + 1, exr + 4] = WR                           # crow's feet
        a[ey - 5, fx - 4:fx] = mix(sk[3], WR, 0.5)                                       # forehead line
    # glasses
    if L.glasses:
        G = C(L.glasses_col); LENS = mix(sk[3], C('#cfeaff'), 0.35)
        gy = ey - 2
        for ex in (exl, exr):
            x0, w, h = ex - 2, 6, 6
            if L.glasses == 'round':
                a[gy, x0 + 1:x0 + w - 1] = G; a[gy + h - 1, x0 + 1:x0 + w - 1] = G
                a[gy + 1:gy + h - 1, x0] = G; a[gy + 1:gy + h - 1, x0 + w - 1] = G
            else:
                a[gy, x0:x0 + w] = G; a[gy + h - 1, x0:x0 + w] = G
                a[gy:gy + h, x0] = G; a[gy:gy + h, x0 + w - 1] = G
        a[gy + 2, exl + 4:exr - 2] = G
        a[gy + 2, HX + 4:exl - 2] = G                                 # temple arm to the ear
        a[gy + 1, exr + 2] = mix(G, WH, 0.7); a[gy + 1, exl + 2] = mix(G, WH, 0.5)    # lens glint
        if glint > 0:
            for ex in (exl, exr): E[gy + 1:gy + 5, ex - 1:ex + 3] = np.maximum(E[gy + 1:gy + 5, ex - 1:ex + 3], 0.4 * glint)
    # hair over the head
    hm = _hair(L.hair, y0, L.seed, eo)
    if L.hair == 'cap':
        hm &= YY >= y0 + 4
    a[hm] = hr[3]
    ys, xs = np.nonzero(hm)
    for y, x in zip(ys, xs):
        u = (x - (HX + HW / 2)) / (HW / 2)
        if u > 0.45 or (y > y0 + 6 and x < HX + 4): a[y, x] = hr[2]
        if -0.55 < u < 0.15 and y == y0 + 2 + int(round(3 * (u + 0.2) ** 2)): a[y, x] = hr[4]      # sheen arc
    e = _edge(hm)
    a[e] = mix(hr[0], OUTL, 0.4)
    # ear in front of the back hair
    if em.any():
        shade_part(a, em, None, rp=sk, hi=False)
        a[y0 + 12, HX + 4 + eo] = sk[2]
    if L.hair == 'bald':
        a[y0 + 3, AX - 4:AX - 1] = sk[5]; a[y0 + 4, AX - 5] = sk[5]                             # dome shine
    if L.hair == 'cap':
        cr = _rp(L.hat_col, 6)
        cm = _head_mask(y0) & (YY < y0 + 7)
        cm |= (np.abs(XX - AX) <= 9) & (YY == y0 - 1)
        cm |= (np.abs(XX - AX) <= 6) & (YY == y0 - 2)
        shade_part(a, cm, None, rp=cr)
        a[y0 + 6, AX + 4:AX + 15] = cr[1]; a[y0 + 7, AX + 6:AX + 14] = cr[0]                    # brim (toward the face)
        a[y0 + 1, AX - 1:AX + 1] = cr[4]
    if L.hat == 'straw':
        draw_straw_hat(a, L, y0)
    return H

def draw_straw_hat(a, L, y0):
    """wide-brim straw hat, 3/4 view turned right: crown with a diagonal weave + dark band, a brim that dips toward
    the face side, frayed edge; casts a shadow band across the forehead."""
    st = _rp(L.straw_col, 6, dark=0.30, light=0.92)
    sk = _rp(L.skin, 6, dark=0.42, light=0.95)
    H = _head_mask(y0)
    # brim shadow on the forehead / upper face
    shm = H & (YY >= y0 + 5) & (YY <= y0 + 8)
    a[shm] = [mix(tuple(int(v) for v in c), sk[1], 0.45) for c in a[shm]] if shm.any() else a[shm]
    cx = AX + 1.0
    by = y0 + 5.0 + (XX - cx) * 0.06                                      # brim centre line, dipping toward the face
    brim = (((XX - cx) / 18.5) ** 2 + ((YY - by) / 2.6) ** 2) <= 1.0
    crown = (np.abs(XX - (cx - 0.5)) <= 9.5 - np.clip(y0 + 1 - YY, 0, 9) * 0.12) & (YY >= y0 - 6) & (YY <= y0 + 4)
    crown &= ~((YY == y0 - 6) & (np.abs(XX - cx) > 7.5))                  # rounded top corners
    a[crown] = st[3]
    ys, xs = np.nonzero(crown)
    for y, x in zip(ys, xs):
        if (x + y) % 3 == 0: a[y, x] = st[2]
        elif (x - y) % 4 == 0: a[y, x] = st[4]
        if x - cx > 6: a[y, x] = st[2]                                   # shade side of the crown
    a[(YY == y0 - 6) & (np.abs(XX - cx) <= 3)] = st[2]                   # crown dent
    band = crown & (YY >= y0 + 1) & (YY <= y0 + 3)
    a[band] = C(L.band_col); a[band & (YY == y0 + 3)] = mix(C(L.band_col), OUTL, 0.4)
    a[brim] = st[3]
    ys, xs = np.nonzero(brim)
    for y, x in zip(ys, xs):
        if y > by[y, x] + 0.6: a[y, x] = st[2]                           # underside
        elif (x - y) % 3 == 0: a[y, x] = st[4]
    rng = np.random.default_rng(L.seed + 17)
    e = _edge(brim)
    ys, xs = np.nonzero(e & (YY > by))
    for y, x in zip(ys, xs):
        if rng.random() < 0.3 and y + 1 < SH: a[y + 1, x] = st[1]          # frayed straw ends
    m = crown | brim
    a[_edge(m)] = mix(st[0], OUTL, 0.5)

# ---------------------------------------------------------------- props
def draw_prop(a, E, prop, hand, side_hands):
    if prop == 'coffee':
        x, y = side_hands.get(1, hand)
        a[y - 6:y + 1, x - 2:x + 3] = C('#3a2420'); a[y - 5:y, x - 1:x + 2] = C('#f4f0e8')
        a[y - 3:y - 1, x - 1:x + 2] = C('#a8703e'); a[y - 7, x - 2:x + 3] = C('#6a4a3a'); a[y - 6, x - 1:x + 2] = C('#f8f4ee')
    elif prop == 'phone':
        x, y = side_hands.get(1, hand)
        a[y - 4:y + 1, x - 2:x + 2] = C('#1a1a22'); a[y - 3:y, x - 1:x + 1] = C('#bfe4ff'); E[y - 3:y, x - 1:x + 1] = 0.8
    elif prop == 'bag':
        x, y = side_hands.get(0, hand)
        a[y:y + 11, x - 4:x + 5] = C('#4a3226'); a[y + 1:y + 10, x - 3:x + 4] = C('#d8b47a'); a[y + 1, x - 3:x + 4] = C('#f0d09a')
        a[y + 2:y + 10, x + 3] = C('#b08a5a')
        for i in range(7):
            a[y + 1 - i, x - 1 + i // 2] = C('#e8b46a'); a[y + 1 - i, x + i // 2] = C('#c8843e')                  # baguette
        a[y - 6, x + 2] = C('#f4d494')
    elif prop == 'paper':
        x, y = side_hands.get(1, hand)
        a[y - 7:y + 1, x - 3:x + 3] = C('#5a4a48'); a[y - 6:y, x - 2:x + 2] = C('#fbf7ee')
        for k in range(y - 5, y - 1, 2): a[k, x - 1:x + 2] = C('#a8a0a0')
    elif prop == 'tissue':
        x, y = side_hands.get(1, hand)
        a[y - 3:y + 1, x - 2:x + 2] = C('#fbfbff')

# ---------------------------------------------------------------- compose
def head_dir(v):
    """screen-space head direction -> draw() kwargs.  v: -1.6 profile left, -1 3/4 left, 0 front, 1 3/4 right,
    1.6 profile right.  Animate v (on 2s) for a head turn; the body keeps its own flip.
    RULE (1 unit ~ 45 deg): keep |v_head - v_body| <= 2 (~90 deg).  A body at 3/4 right (flip=False, v_body=+1, e.g.
    facing the water) may look anywhere from 3/4 left (-1, via the front in-between 0) to profile right (+1.6) - Act 4
    v2's approved old-man turn.  Never 3/4 body + opposite PROFILE (|diff| 2.6, ~135 deg): an owl twist, creepy."""
    return dict(head_flip=(v < 0), turn=abs(v))

def draw(L, pose='stand', phase=0.0, arms='down', face='normal', prop=None, tilt=0, glint=0.0, flip=False, hop=0,
         turn=1.0, head_flip=None, arm_ang=None):
    """one frame -> SimpleNamespace(rgba, E, ax, fy, seat_y, hands).  (ax, fy) = feet centre / ground row:
    put at (x - ax, ground - fy).  For pose='sit', put at (x - ax, seat - seat_y).
    v0.7 performance:
      arms      a name or (arms_a, arms_b, k): the joint angles are interpolated (k may overshoot a little)
      arm_ang   {side: (upper_deg, fore_deg)} explicit angles (reel crank cycles, pats ...) - overrides arms per side
      turn      head turn: 0 front, 1 = 3/4 (default), 1.6 = profile          head_flip: the head faces the other way
                (True/False, None = same as the body).  Use head_dir(v); see its twist rule."""
    names = arms if isinstance(arms, tuple) else (arms, arms, 0.0)
    arms = names[1] if names[2] >= 0.5 else names[0]
    a = np.zeros((SH, SW, 4), np.uint8); E = np.zeros((SH, SW), np.float32)
    # body offset: stance foot on the ground (natural bob)
    if pose == 'walk':
        g = legs_geom(pose, phase)
        low = max(g[0][2][1], g[1][2][1])
        dy = int(round(GROUND - 2 - low))
    else:
        dy = 0
    dy -= int(round(hop))
    hip_y = HIP_Y + dy; y0 = SHOULDER_Y + dy; hy = HY + dy
    lay_legs = np.zeros_like(a); lay_body = np.zeros_like(a); lay_arm0 = np.zeros_like(a); lay_arm1 = np.zeros_like(a)
    if L.top != 'dress' or pose == 'walk' or True:
        draw_legs(lay_legs, L, pose, phase, hip_y)
    hands = {}
    for side, lay in ((0, lay_arm0), (1, lay_arm1)):
        ua, fa = arm_pose(names[0], phase, side, pose)
        if names[2] > 0:
            ub, fb = arm_pose(names[1], phase, side, pose); k_ = names[2]
            ua, fa = ua + (ub - ua) * k_, fa + (fb - fa) * k_
        if arm_ang and side in arm_ang: ua, fa = arm_ang[side]
        if side == 0: ua, fa = -ua if arms in ('down', 'swing') or (arms not in ('type', 'hold', 'cross', 'phone', 'bag')) and False else ua, fa
        hands[side] = draw_arm(lay, L, side, ua, fa, y0)
    draw_torso(lay_body, E, L, y0)
    if pose == 'sit':                                     # lap: thighs read in front of the torso hem
        pass
    hf = flip if head_flip is None else head_flip
    if hf == flip:
        Hm = draw_head(lay_body, E, L, face, hy, tilt, glint, turn)
    else:                         # head turned the other way: own layer, mirrored (the head is symmetric about AX-0.5)
        lay_head = np.zeros_like(a); Eh = np.zeros_like(E)
        Hm = draw_head(lay_head, Eh, L, face, hy, tilt, glint, turn)
        lay_head = lay_head[:, ::-1]; Eh = Eh[:, ::-1]; Hm = Hm[:, ::-1]
        mh = lay_head[..., 3] > 0
        lay_body[mh] = lay_head[mh]; E[mh] = np.maximum(E[mh], Eh[mh])
    # neck
    sk = _rp(L.skin, 6, dark=0.42, light=0.95)
    nk = np.zeros((SH, SW), bool); nk[hy + HH - 1:y0 + 1, AX - 2:AX + 2] = True
    nk &= ~Hm & (lay_body[..., 3] == 0)
    lay_body[nk] = sk[2]
    # back arm behind the torso, front arm in front (arms crossing the chest come in front)
    order = [lay_arm0, lay_legs, lay_body, lay_arm1] if pose != 'sit' else [lay_arm0, lay_body, lay_legs, lay_arm1]
    if arms in ('type', 'hold', 'cross', 'phone', 'wipe', 'chin', 'give', 'offer', 'catch', 'flick', 'reel'):
        order = [lay_legs if pose != 'sit' else lay_body, lay_body if pose != 'sit' else lay_legs, lay_arm0, lay_arm1]
    for lay in order:
        m = lay[..., 3] > 0
        a[m] = lay[m]
    draw_prop(a, E, prop, hands.get(1), hands)
    if flip:
        a = a[:, ::-1].copy(); E = E[:, ::-1].copy()
        hands = {k: (SW - 1 - v[0], v[1]) for k, v in hands.items()}
    return SimpleNamespace(rgba=a, E=E, ax=AX if not flip else SW - 1 - AX, fy=GROUND, seat_y=HIP_Y + 1, hands=hands, dy=dy)

def background(rgba, k=0.20, tint='#a8b0d0', lift=0.03, contrast=0.94):
    """depth treatment for extras: a little desaturated / cooler / flatter than the lead - not washed out."""
    a = rgba.copy()
    m = a[..., 3] > 0
    rgb = a[..., :3].astype(np.float32)
    g = rgb.mean(-1, keepdims=True)
    t = np.asarray(C(tint)[:3], np.float32)
    rgb = rgb * (1 - k) + (g * 0.6 + t * 0.4) * k
    mu = rgb[m].mean(0) if m.any() else 128
    rgb = mu + (rgb - mu) * contrast
    rgb = rgb + (255 - rgb) * lift
    a[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    return a

# ---------------------------------------------------------------- cast
CAST = {
    'bun_cardigan': Look(hair='bun', hair_col='#4a3226', skin='#f2cfae', top='cardigan', top_col='#c88a6a', inner='#f4e8d0',
                         bottom='skirt', bottom_col='#6a5a7a', shoes='#6a3a3a', seed=2),
    'glasses_tee':  Look(hair='short', hair_col='#2a2630', skin='#e8bc94', glasses='round', top='tee', top_col='#6a8ab0',
                         inner='#f4f0e8', bottom_col='#4a4a5a', shoes='#f0ece4', seed=3),
    'uncle':        Look(hair='bald', hair_col='#7a6a62', skin='#e8c09c', glasses='square', stubble=True, top='cardigan',
                         top_col='#8a8a6a', inner='#d8c8a0', bottom_col='#5a4a40', shoes='#3a2a26', seed=6),
    'hoodie_long':  Look(hair='long', hair_col='#2a2228', skin='#f4d4b8', top='hoodie', top_col='#9ab07a', inner='#f4f0e8',
                         bottom_col='#3a4258', shoes='#e8e4dc', seed=4),
    'side_shirt':   Look(hair='side', hair_col='#6a5040', skin='#dcae86', top='shirt', top_col='#e8ecf2', inner='#ffffff',
                         tie='#4a6ab0', bottom_col='#2e3448', shoes='#2a2226', seed=5),
    'cap_runner':   Look(hair='cap', hair_col='#2a2226', skin='#d8a47e', top='tee', top_col='#e8e0d0', inner='#e0603e',
                         bottom='shorts', bottom_col='#3a4a6a', shoes='#f0f0f0', hat_col='#3a6ab0', seed=7),
    'bob_dress':    Look(hair='bob', hair_col='#3a2a2a', skin='#f6dcc4', top='dress', top_col='#e8a0a0', inner='#f8f0e8',
                         bottom='skirt', bottom_col='#e8a0a0', shoes='#8a4a4a', seed=8),
    'old_fisher':   Look(hair='short', hair_col='#a39a92', skin='#d9a682', beard=True, top='cardigan', top_col='#7a6c4a',
                         inner='#d8d0c0', bottom_col='#4a4642', shoes='#2a2224', hat='straw', blush=False, wrinkles=True, seed=11),
    'pony_jacket':  Look(hair='ponytail', hair_col='#5a3a2a', skin='#f0c8a4', top='jacket', top_col='#5a6a8a', inner='#f4f0e8',
                         bottom_col='#3a3a48', shoes='#2a2a30', seed=9),
}

def sheet(path, looks=None, scale=4):
    """contact sheet: every look x a few poses (for review)."""
    from PIL import Image
    looks = looks or list(CAST.values())
    rows = []
    poses = [dict(pose='stand'), dict(pose='walk', phase=0.0, arms='swing'), dict(pose='walk', phase=0.25, arms='swing'),
             dict(pose='walk', phase=0.5, arms='swing'), dict(pose='walk', phase=0.75, arms='swing'),
             dict(pose='stand', face='smile'), dict(pose='sit', arms='type', face='focus'), dict(pose='stand', arms='phone', face='down', prop='phone')]
    W = SW * len(poses); Hh = SH * len(looks)
    img = np.zeros((Hh, W, 4), np.uint8); img[..., :3] = (236, 222, 200); img[..., 3] = 255
    for i, L in enumerate(looks):
        for j, kw in enumerate(poses):
            s = draw(L, **kw)
            m = s.rgba[..., 3] > 0
            blk = img[i * SH:(i + 1) * SH, j * SW:(j + 1) * SW]
            blk[m] = s.rgba[m]
            blk[GROUND, :, :3] = (180, 150, 130)
    Image.fromarray(img).resize((W * scale, Hh * scale), Image.NEAREST).save(path)
    return path
