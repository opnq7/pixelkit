"""pixelkit.characters.backs - BACK views of seated figures, for backlit shots (sunset river bank, looking out).

From behind and against the light, a figure reads by its silhouette + a warm rim on the sun side, so these sprites
are painted as mid-dark shapes with a baked emissive rim (E) on the edges that face the sun.  Use with
outdoor_state(..., rim=0, facing~0.1) so the renderer does not add its own (upper-left) rim.

    s = claude_back(sun_side=1)            # Claude sitting on the grass: head shell + back vents + coral ear hubs + logo antenna
    s = person_back(L, hat='straw')        # townsperson / the old fisherman on a folding stool (L = characters.person.Look)
    layer.put(s.rgba, x - s.ax, seat_y - s.ay, 0, E=s.E)      # (ax, ay) = bottom-centre (the seat)
    s.hand = (hx, hy)                      # where a held rod leaves the silhouette (sprite coords)
sun_side: +1 = sun to the right of the figure (rim on the right / top-right edges), -1 = left.
"""
import math
from types import SimpleNamespace
import numpy as np
from ..core import Canvas, C, mix
from ..palette import ramp
from . import claude as CL

def _edge(m):
    p = np.pad(m, 1)
    inner = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m & ~inner

def _rim(a, E, sun_side=1, col=(255, 196, 140), k=0.85, width=1, top=True):
    """bake a warm rim: pixels whose neighbour toward the sun (or above) is empty."""
    m = a[..., 3] > 127
    side = np.zeros_like(m)
    for w in range(1, width + 1):
        nb = np.roll(m, -sun_side * w, 1)
        if sun_side > 0: nb[:, -w:] = False
        else: nb[:, :w] = False
        side |= m & ~nb
        if top:
            up = np.roll(m, w, 0); up[:w] = False
            side |= m & ~up & (np.arange(m.shape[1])[None, :] * sun_side > (m.shape[1] * (0.35 if sun_side > 0 else -0.65)))
    c = np.array(col, np.float32)
    a[..., :3][side] = (a[..., :3][side].astype(np.float32) * 0.25 + c * 0.75).astype(np.uint8)
    E[side] = np.maximum(E[side], k)
    return side

def _outline(a, col):
    m = a[..., 3] > 127
    e = _edge(m)
    a[e] = mix(tuple(int(v) for v in a[e].mean(0)[:3]) + (255,), col, 0.6) if e.any() else a[e]
    return e


def _claude_back_head(cv, E, hx, hy, glow=1.0):
    """the head shell seen from behind (44 x 32 at hx, hy) + antenna / logo."""
    hw, hh = 44, 32
    cv.rrect(hx, hy, hw, hh, CL.SH1, r=7)
    cv.rrect(hx + 1, hy + 1, hw - 2, hh - 6, CL.BASE, r=6)
    cv.rect(hx + 3, hy + hh - 6, hw - 6, 4, CL.SH2)                 # lower shell in shadow
    cv.rrect(hx + 10, hy + 6, hw - 20, hh - 13, CL.SIDE1, r=3)      # back service panel
    cv.outline_rrect(hx + 10, hy + 6, hw - 20, hh - 13, CL.SIDE1, CL.SIDE2, r=3)
    for k in range(3): cv.rect(hx + 16, hy + 11 + k * 3, hw - 32, 1, CL.SH2)  # vents
    cv.px(hx + hw // 2, hy + 9, CL.LOGO_O)                            # tiny spark sticker
    for ex in (hx - 2, hx + hw - 2):                                  # coral ear hubs
        cv.rrect(ex, hy + 11, 4, 9, CL.TC, r=1); cv.rect(ex + 1, hy + 12, 2, 7, CL.TC_HI if ex > hx else CL.TC_SH)
    ax_ = hx + hw // 2
    cv.rect(ax_, hy - 6, 1, 6, CL.METAL); cv.rect(ax_ + 1, hy - 5, 1, 5, CL.METAL_D)
    CL.draw_logo(cv, E, ax_, hy - 8, k=glow)


def claude_back(sun_side=1, glow=1.0):
    """Claude seen from behind, sitting on the ground (legs out of sight in front).  56 x 60, anchor bottom-centre."""
    cv = Canvas(56, 60); E = np.zeros((60, 56), np.float32)
    hx, hy, hw, hh = 6, 13, 44, 32
    _claude_back_head(cv, E, hx, hy, glow)
    # torso + hands on the grass
    cv.rrect(hx + 10, hy + hh, 24, 14, CL.TC_SH, r=3)
    cv.rect(hx + 12, hy + hh, 20, 3, CL.TC_DK)                       # neck shadow under the head
    cv.rect(hx + 11, hy + hh + 4, 22, 1, CL.TC)
    for hxp in (hx + 4, hx + 36):
        cv.ellipse(hxp + 2, hy + hh + 10, 3, 3, CL.HAND_SH); cv.px(hxp + 2, hy + hh + 8, CL.HAND)
    a = cv.a
    _outline(a, CL.OUT)
    _rim(a, E, sun_side, col=(255, 206, 150), k=0.9)
    E[a[..., 3] < 128] = 0
    return SimpleNamespace(rgba=a, E=E, ax=28, ay=hy + hh + 14, w=56, h=60, hand=None)


BACK_WALK_LEGS = ((0, 2), (0, 0), (2, 0), (0, 0))      # (left lift, right lift) per walk phase 0..3
BACK_WALK_BOB = (0, -1, 0, -1)

def claude_back_walk(phase=0, sit=0.0, sun_side=1, glow=1.0):
    """Claude seen from behind, STANDING / walking away from the camera (phase 0..3 leg cycle).
    sit 0..1 = sitting down (knees bend, body sinks 6 px, hands go to the ground) -> at 1 switch to claude_back().
    56 x 67, anchor (ax, ay) = bottom-centre between the feet.  At sit=1 the head is where claude_back() has it
    when both share the same anchor y (the seat)."""
    W_, H_ = 56, 67
    cv = Canvas(W_, H_); E = np.zeros((H_, W_), np.float32)
    foot = 65
    sink = int(round(6 * sit))
    bob = BACK_WALK_BOB[phase % 4] if sit <= 0 else 0
    hx, hw, hh = 6, 44, 32
    hy = 13 + sink + bob
    ty = hy + hh                                                     # torso top
    lift = BACK_WALK_LEGS[phase % 4] if sit <= 0 else (0, 0)
    leg_h = max(2, foot - (ty + 13) - 0)
    # legs (behind the torso hem) + soles
    for i, (lx, lf) in enumerate(((hx + 13, lift[0]), (hx + 25, lift[1]))):
        if sit > 0.5: break
        y0 = ty + 12; y1 = foot - 2 - lf
        cv.rect(lx, y0, 6, max(1, y1 - y0), CL.TC_SH)
        cv.rect(lx, y1, 6, 2, CL.FOOT if lf == 0 else CL.TC_DK)
    # torso
    cv.rrect(hx + 10, ty, 24, 14, CL.TC_SH, r=3)
    cv.rect(hx + 12, ty, 20, 3, CL.TC_DK)
    cv.rect(hx + 11, ty + 4, 22, 1, CL.TC)
    # arms swinging (hands at the sides), or reaching for the ground while sitting down
    sw = (1, 0, -1, 0)[phase % 4] if sit <= 0 else 0
    for side, hxp in ((-1, hx + 6), (1, hx + 34)):
        if sit > 0:
            yh = ty + 10 + int(round(3 * sit)); xh = hxp + side * int(round(-2 + 2 * sit))
        else:
            yh = ty + 9 + side * sw; xh = hxp
        cv.rect(xh - 1 + (2 if side < 0 else -1), ty + 2, 3, max(1, yh - ty - 2), CL.TC_SH)
        cv.ellipse(xh + 2, yh, 3, 3, CL.HAND_SH); cv.px(xh + 2, yh - 2, CL.HAND)
    _claude_back_head(cv, E, hx, hy, glow)
    a = cv.a
    _outline(a, CL.OUT)
    _rim(a, E, sun_side, col=(255, 206, 150), k=0.9)
    E[a[..., 3] < 128] = 0
    return SimpleNamespace(rgba=a, E=E, ax=28, ay=foot, w=W_, h=H_, hand=None)


def person_back(L, hat=None, hat_col='#d6b06a', band_col='#7a3a2e', seat='stool', sun_side=1, hunch=1):
    """a townsperson seen from behind, seated.  hat: None | 'straw' (wide brim) | 'cap'.  44 x 62, anchor bottom-centre."""
    W_, H_ = 44, 62
    cv = Canvas(W_, H_); E = np.zeros((H_, W_), np.float32)
    hr = ramp(L.hair_col, 6); tr = ramp(L.top_col, 6); sk = ramp(L.skin, 6); br = ramp(L.bottom_col, 6)
    cx = 22
    # stool / seat
    if seat == 'stool':
        wood = C('#6a4a32'); wood_d = C('#3e2a22')
        cv.rect(cx - 11, 48, 22, 2, wood); cv.rect(cx - 11, 50, 22, 1, wood_d)
        for i in range(10):
            cv.px(cx - 9 + i * 2, 51 + i, wood_d); cv.px(cx + 9 - i * 2, 51 + i, wood_d)
    # trousers showing either side of the seat (knees forward)
    cv.rect(cx - 13, 44, 4, 6, br[2]); cv.rect(cx + 9, 44, 4, 6, br[2])
    # torso (cardigan), slightly hunched forward over the rod
    y0 = 28 + hunch
    for j in range(22):
        u = j / 21.0
        half = int(round(12 + 2.0 * min(u * 4, 1) - 1.5 * u))
        cv.rect(cx - half, y0 + j, 2 * half, 1, tr[3])
    for j in range(22):                                            # knit texture + shadow toward the bottom
        for i in range(-14, 15):
            x, y = cx + i, y0 + j
            if cv.a[y, x, 3] and (i + j) % 3 == 0: cv.px(x, y, tr[2])
    cv.rect(cx - 13, y0 + 16, 26, 6, tr[2])
    cv.rect(cx - 1, y0 + 2, 1, 19, tr[2])                           # back seam
    # sleeves / elbows reaching forward
    cv.rect(cx - 15, y0 + 5, 3, 12, tr[2]); cv.rect(cx + 12, y0 + 5, 3, 12, tr[2])
    # neck + head (back)
    cv.rect(cx - 3, y0 - 3, 6, 4, sk[2])
    cv.ellipse(cx, y0 - 10, 10, 9, hr[3])
    for j in range(-9, 10, 3): cv.px(cx + j, y0 - 10 + abs(j) // 2, hr[2])          # hair strands
    cv.rect(cx - 11, y0 - 11, 2, 4, sk[3]); cv.rect(cx + 9, y0 - 11, 2, 4, sk[3])   # ears
    if hat == 'straw':
        hc = ramp(hat_col, 6)
        cv.ellipse(cx, y0 - 15, 20, 5, hc[2]); cv.ellipse(cx, y0 - 16, 19, 4, hc[3])
        for i in range(-18, 19, 2): cv.px(cx + i, y0 - 16 + (1 if i % 4 else 0), hc[4])   # weave
        cv.rrect(cx - 9, y0 - 26, 18, 11, hc[3], r=4)
        for j in range(y0 - 25, y0 - 16):
            for i in range(cx - 8, cx + 9):
                if (i + j) % 2 == 0: cv.px(i, j, hc[4])
        cv.rect(cx - 9, y0 - 19, 18, 2, C(band_col))
    elif hat == 'cap':
        cv.ellipse(cx, y0 - 13, 9, 6, C(L.hat_col))
    a = cv.a
    _outline(a, C('#24182a'))
    _rim(a, E, sun_side, col=(255, 200, 140), k=0.8)
    E[a[..., 3] < 128] = 0
    return SimpleNamespace(rgba=a, E=E, ax=cx, ay=48, w=W_, h=H_, hand=(cx + 13, y0 + 12))


def old_fisher_back(sun_side=1, rod_side=1, seed=3, young=False, turn=0):
    """the old fisherman (ACT IV), detailed back view on a canvas folding stool.  52 x 70, anchor = seat centre.
    Straw hat with a frayed, sun-rimmed brim and a dark band; grey hair at the nape; backlit ears glow red;
    shirt collar over an olive knit cardigan (rib texture, elbow patches); hunched; the rod hand on rod_side.
    v0.11 turn=-1/+1: head turned toward that side - head + crown shift 2 px / 1 px, that ear tucks in,
    a sliver of cheek + the nose tip peek out past the hair."""
    W_, H_ = 52, 70
    cv = Canvas(W_, H_); E = np.zeros((H_, W_), np.float32)
    rng = np.random.default_rng(seed)
    cx, seat = 26, 52
    # ---- folding stool: canvas seat + X legs
    leg = C('#5a4a40'); leg_d = C('#36282a'); canvas_ = C('#6a5a48'); canvas_d = C('#4a3c34')
    cv.rect(cx - 12, seat - 1, 24, 3, canvas_); cv.rect(cx - 12, seat + 2, 24, 1, canvas_d)
    # ---- trousers + heels peeking out either side
    tr = C('#4a4642'); tr_d = C('#34302e')
    cv.rect(cx - 15, seat - 6, 5, 8, tr); cv.rect(cx + 10, seat - 6, 5, 8, tr)
    cv.rect(cx - 15, seat + 1, 5, 1, tr_d); cv.rect(cx + 10, seat + 1, 5, 1, tr_d)
    cv.rect(cx - 15, seat + 14, 4, 2, C('#2a2224')); cv.rect(cx + 11, seat + 14, 4, 2, C('#2a2224'))   # heels on the deck
    # ---- cardigan torso: hunched, rounded upper back
    knit, knit_d, knit_l, knit_dd = C('#7a6c4a'), C('#5e5238'), C('#9a8a5e'), C('#463c2c')
    if young:                                                      # v0.11: 30 years earlier - a faded blue sweater
        knit, knit_d, knit_l, knit_dd = C('#5a7090'), C('#465a78'), C('#7a92b0'), C('#34425a')
    y0 = 27
    for j in range(25):
        u = j / 24.0
        half = 9 + 5.5 * math.sqrt(min(j / 7.0, 1.0)) - 1.2 * u
        cv.rect(int(round(cx - half)), y0 + j, int(round(2 * half)), 1, knit)
    for j in range(25):                                            # rib texture: vertical knit columns
        for i in range(-15, 16):
            x, y = cx + i, y0 + j
            if not cv.a[y, x, 3]: continue
            if i % 3 == 0 and (y % 4 != 0): cv.px(x, y, knit_d)
    for j in range(25):                                            # form shading: darker toward the lower back + shadow side
        for i in range(-15, 16):
            x, y = cx + i, y0 + j
            if cv.a[y, x, 3] and (i * sun_side < -10 or (j > 19 and (i + j) % 2 == 0)): cv.px(x, y, knit_dd)
            elif cv.a[y, x, 3] and i * sun_side > 9 and j < 18 and i % 3: cv.px(x, y, knit_l)
    cv.rect(cx - 13, y0 + 21, 26, 3, knit_d); cv.rect(cx - 12, y0 + 24, 24, 1, knit_dd)              # hem band
    # sleeves + elbow patches; the rod arm reaches forward on rod_side
    for side in (-1, 1):
        ex = cx + side * 14
        cv.rect(ex - 2, y0 + 6, 4, 13, knit_d)
        cv.rrect(ex - 2, y0 + 11, 4, 5, knit_dd if young else C('#5a3e2e'), r=1)
        if side == rod_side:
            cv.rect(ex + side * 2 - (1 if side < 0 else 0), y0 + 13, 3, 4, knit_d)
            cv.rect(ex + side * 4 - (1 if side < 0 else 0), y0 + 14, 3, 3, C('#c08a6a'))                # hand
    # ---- shirt collar + neck (sunk a little into the shoulders)
    cv.rect(cx - 6, y0 - 1, 12, 3, C('#d8d0c0')); cv.rect(cx - 6, y0 + 1, 12, 1, C('#a8a090'))
    cv.rect(cx - 4, y0 - 4, 8, 3, C('#b07a5a'))
    for k in range(3): cv.rect(cx - 3, y0 - 4 + k, 6, 1, C('#9a6a4e') if k == 1 else C('#b07a5a'))   # neck creases
    # ---- head (back): grey hair, nape tufts, ears glowing in the backlight
    hair, hair_d, hair_l = C('#8e8580'), C('#6a625e'), C('#c8bcb0')
    if young: hair, hair_d, hair_l = C('#2e2628'), C('#1e181c'), C('#5a4c4c')     # v0.11: black hair (young=True)
    hx = cx + 2 * turn
    cv.rrect(hx - 10, y0 - 16, 20, 14, hair, r=3)                          # back of the head (rounded at the nape)
    for k in range(-8, 9):
        if k % 2 == 0: cv.px(hx + k, y0 - 13 + (k * k) // 40, hair_l)       # combed strands catching the sky light
        if k % 3 == 0: cv.px(hx + k, y0 - 9, hair_d)
    for k in (-6, -3, 0, 3, 6): cv.px(hx + k, y0 - 3, hair)                  # stray tufts over the collar
    cv.rect(hx - 10, y0 - 13, 1, 9, hair_d); cv.rect(hx + 9, y0 - 13, 1, 9, hair_d)
    for side in (-1, 1):
        if side == turn: continue
        ex = hx + side * 10 - (1 if side < 0 else 0)
        cv.rrect(ex - 1, y0 - 12, 3, 6, C('#d0705a'), r=1); cv.px(ex, y0 - 10, C('#f09070'))
        if side == sun_side: cv.rect(ex + side, y0 - 11, 1, 4, C('#ffb48a')); E[y0 - 11:y0 - 7, ex + side] = 0.9
        E[y0 - 12:y0 - 6, ex - 1:ex + 2] = np.maximum(E[y0 - 12:y0 - 6, ex - 1:ex + 2], 0.45)
    if turn:                                                        # cheek + nose tip past the hair line
        sk, sk_d = C('#c08a6a'), C('#9a6a4e')
        fx = hx + turn * 10 - (1 if turn < 0 else 0)
        cv.rect(fx - (2 if turn < 0 else 0), y0 - 12, 3, 8, sk); cv.rect(fx + 2 * turn, y0 - 11, 1, 4, sk)
        cv.px(fx + 3 * turn, y0 - 9, sk); cv.rect(fx - (2 if turn < 0 else 0), y0 - 5, 3, 1, sk_d)
        cv.px(fx - turn, y0 - 11, C('#d0705a'))                          # the ear's edge, tucked behind the cheek
    hx2 = cx + turn
    # ---- straw hat: crown with diagonal weave, dark band, wide frayed brim
    st, st_d, st_l, st_dd = C('#d8b46a'), C('#a8844a'), C('#f0d490'), C('#7a5a34')
    hy = y0 - 15
    cv.ellipse(hx2, hy + 1, 21, 5, st_d)                                 # brim underside (shadow)
    cv.ellipse(hx2, hy, 21, 4, st)
    for i in range(-21, 22):
        for j in range(-4, 5):
            x, y = cx + i, hy + j
            if 0 <= x < W_ and cv.a[y, x, 3] and (i - j) % 3 == 0: cv.px(x, y, st_d)
    for i in range(-21, 22, 1):                                          # frayed edge
        if rng.random() < 0.25:
            x = hx2 + i; y = hy + int(round(4.4 * math.sqrt(max(0.0, 1 - (i / 21.5) ** 2)))) + 1
            if 0 <= x < W_: cv.px(x, y, st_d)
    cv.rrect(hx2 - 9, hy - 11, 18, 11, st, r=5)                          # crown
    for j in range(hy - 10, hy):
        for i in range(hx2 - 8, hx2 + 9):
            if cv.a[j, i, 3] and (i + j) % 3 == 0: cv.px(i, j, st_d)
            elif cv.a[j, i, 3] and (i - j) % 4 == 0: cv.px(i, j, st_l)
    cv.rect(hx2 - 7, hy - 11, 14, 1, st_dd); cv.rect(hx2 - 2, hy - 11, 4, 1, st_d)                   # crown dent
    cv.rect(hx2 - 9, hy - 3, 18, 2, C('#6a2e26')); cv.rect(hx2 - 9, hy - 2, 18, 1, C('#4a2220'))    # band
    a = cv.a
    _outline(a, C('#24182a'))
    _rim(a, E, sun_side, col=(255, 206, 150), k=0.85)
    # brim rim on the sun side + crown top highlight
    for i in range(0, 22):
        x = cx + sun_side * i
        y = hy - int(round(4 * math.sqrt(max(0.0, 1 - (i / 21.5) ** 2))))
        if 0 <= x < W_ and a[y, x, 3] and i > 6: a[y, x, :3] = (255, 224, 160); E[y, x] = 0.95
    E[a[..., 3] < 128] = 0
    lg = Canvas(W_, H_)                                                   # stool legs (drawn after the rim, behind)
    lg.line(cx - 11, seat + 3, cx + 10, seat + 16, leg_d); lg.line(cx + 10, seat + 3, cx - 11, seat + 16, leg_d)
    lg.line(cx - 10, seat + 3, cx + 11, seat + 16, leg_d); lg.line(cx + 11, seat + 3, cx - 10, seat + 16, C('#7a6250'))
    lg.rect(cx - 12, seat + 16, 4, 1, leg_d); lg.rect(cx + 8, seat + 16, 4, 1, leg_d)
    m = (lg.a[..., 3] > 127) & (a[..., 3] < 128); a[m] = lg.a[m]
    hand = (cx + rod_side * 16, y0 + 15)
    return SimpleNamespace(rgba=a, E=E, ax=cx, ay=seat, w=W_, h=H_, hand=hand)


# ====================================================================== v0.11: 王工 + his childhood self (EGG)
def _messy_hair(cv, cx, cy, rx, ry, hr, rng, spikes=7, whorl=True, spike_len=2):
    """the back of a messy head: dark mass, spiky crown, ragged nape, a cowlick whorl, strands catching the light.
    hr = 6-step ramp (dark -> light)."""
    cv.ellipse(cx, cy, rx, ry, hr[1])
    cv.ellipse(cx - 0.5, cy - 0.8, rx - 1.2, ry - 1.4, hr[2])
    for k in range(spikes):                                         # crown spikes: tapered tufts leaning outward
        a = -math.pi / 2 + (k - (spikes - 1) / 2) * (2.4 / max(1, spikes - 1))
        bx, by = cx + math.cos(a) * (rx - 2.5), cy + math.sin(a) * (ry - 2.5)
        L = spike_len + (k * 7 + 3) % 3
        lean = 0.35 if k % 2 else -0.25
        for i in range(L + 3):
            w = max(1, int(round(3.4 * (1 - i / (L + 3)))))
            x = bx + (math.cos(a) + lean * math.sin(a)) * i; y = by + math.sin(a) * i
            cv.rect(int(round(x - w / 2)), int(round(y)), w, 1, hr[1] if i < L + 1 else hr[0])
    for i in range(-int(rx) + 2, int(rx) - 1, 2):                   # ragged nape: uneven tips
        cv.px(cx + i, int(cy + ry - 1 + (i * 5 % 3 == 0)), hr[1])
    for side in (-1, 1):                                            # tufts over the ears (attached, 2 px)
        cv.rect(int(cx + side * (rx + 0.5)) - (1 if side < 0 else 0), int(cy - 2), 2, 2, hr[1])
    if whorl:                                                       # cowlick: a little spiral at the crown
        wx, wy = int(cx + 2), int(cy - ry * 0.45)
        for (dx, dy) in ((0, 0), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1), (2, -1)):
            cv.px(wx + dx, wy + dy, hr[0] if (dx + dy) % 2 else hr[3])
    for k in range(int(rx * 2)):                                    # strands (light) - sparse, combed down/out
        x = int(cx - rx + 1 + k)
        if rng.random() < 0.45:
            y = int(cy - ry * 0.2 + rng.integers(-2, 4))
            cv.px(x, y, hr[3]); cv.px(x, y + 1, hr[2])


def wang_back(sun_side=1, cloth='#7a8392', hair='#25212b', skin='#efc49c', seed=5, turn=0):
    """王工 seen from behind, sitting on the pier deck (legs over the edge, out of sight), hands on the planks.
    Messy black hair with a cowlick, glasses' temple arms over backlit ears, grey hoodie with the hood bunched at
    the nape, jeans at the seat.  52 x 62, anchor (ax, ay) = bottom-centre on the deck.
    turn: -1/+1 = head turned a little toward that side (ear on that side tucks in, glasses' frame edge peeks out)."""
    W_, H_ = 52, 62
    cv = Canvas(W_, H_); E = np.zeros((H_, W_), np.float32)
    rng = np.random.default_rng(seed)
    cx, deck = 26, 60
    cr = ramp(cloth, 6); hr = ramp(hair, 6, dark=0.10, light=0.72); sk = ramp(skin, 6)
    jean, jean_d = C('#3c4a66'), C('#2a3448')
    # ---- v0.11 seated pose: rounded shoulders, slight taper, hoodie hem flaring over the hips, the seat of the jeans
    #      on the planks.  Upper arms hang at the sides to the elbow, forearms go forward to the knees (out of sight).
    y0 = 31
    def half_at(j):                       # silhouette half-width incl. the upper arms tucked at the sides
        if j < 4: return 8.0 + 4.4 * math.sqrt(j / 4.0)
        if j < 15: return 12.4 + 0.06 * (j - 4)
        if j < 18: return 13.0 - 0.2 * (j - 15)
        if j < 21: return 12.4 - 0.65 * (j - 17)                     # under the elbows the forearms go forward
        return 10.5 + 1.1 * min(1.0, (j - 21) / 4.0)
    rows = deck - y0
    for j in range(rows):
        h = half_at(j)
        xl, xr = int(round(cx - h)), int(round(cx + h))
        cv.rect(xl, y0 + j, xr - xl, 1, cr[3])
    AXR = 9                                                         # arm / back crease (x offset from the spine)
    for j in range(rows - 5):                                       # form shading
        for i in range(-14, 15):
            x, y = cx + i, y0 + j
            if not cv.a[y, x, 3]: continue
            v = i * sun_side; hh = half_at(j)
            arm = abs(i) > AXR and 3 <= j < 19
            if arm:
                if v < 0: cv.px(x, y, cr[2] if (j % 2 == 0 or abs(i) > AXR + 2) else cr[3])
                elif j < 10 and abs(i) < AXR + 3: cv.px(x, y, cr[4])
                if j >= 16: cv.px(x, y, cr[2])
            else:
                if v < -(AXR - 3) and (i + j) % 2 == 0: cv.px(x, y, cr[2])
                elif j > 15: cv.px(x, y, cr[2] if (i + j) % 2 == 0 or j > 19 else cr[3])
                elif v > AXR - 5 and j < 7 and v + j > 6: cv.px(x, y, cr[4])
    for side in (-1, 1):
        for j in range(4, 19):                                      # the crease where the arm meets the back
            cv.px(cx + side * AXR, y0 + j, cr[1] if j % 3 else cr[2])
        cv.hline(cx + side * AXR + (1 if side > 0 else -3), y0 + 18, 3, cr[1])   # elbow underside
    cv.vline(cx, y0 + 7, 10, cr[2])                                 # spine crease under the hoodie
    for k in range(2):                                              # soft slump folds
        yy = y0 + 14 + k * 3
        for i in range(-5 + k, 6 - k):
            if (i + k) % 3: cv.px(cx + i, yy + (abs(i) // 3), cr[2])
    hb = deck - 9                                                   # ribbed hem band over the hips
    for j in range(3):
        h = half_at(hb - y0 + j)
        cv.rect(int(round(cx - h)), hb + j, int(round(2 * h)), 1, cr[2])
    cv.hline(int(round(cx - half_at(hb - y0))), hb, int(round(2 * half_at(hb - y0))), cr[1])
    for i in range(-10, 11, 2): cv.vline(cx + i, hb + 1, 2, cr[1])
    js = deck - 6                                                   # the seat: jeans on the planks, a soft rounded top
    for j in range(6):
        h = 11.6 + (0.4 if j > 1 else 0.0)
        xl, xr = int(round(cx - h)), int(round(cx + h))
        cv.rect(xl, js + j, xr - xl, 1, jean if j < 4 else jean_d)
    cv.vline(cx, js, 5, jean_d)                                     # centre seam
    cv.hline(cx - 9, js, 7, mix(jean, C('#8090b0'), 0.35)); cv.hline(cx + 3, js, 7, mix(jean, C('#8090b0'), 0.25))
    for side in (-1, 1):                                            # back pockets (just a line + a stitch)
        px0 = cx + (2 if side > 0 else -8)
        cv.hline(px0, js + 2, 6, jean_d)
    # ---- hood bunched at the nape: a soft lump with a lit top fold and a dark opening
    cv.rrect(cx - 10, y0 - 6, 20, 11, cr[3], r=4)
    cv.hline(cx - 7, y0 - 6, 14, cr[3]); cv.hline(cx - 5 + 2 * sun_side, y0 - 5, 8, cr[4])
    cv.rrect(cx - 5, y0 - 3, 10, 4, cr[2], r=2)
    for i in range(-4, 5): cv.px(cx + i, y0 + 1 - (abs(i) > 2), cr[1])
    cv.hline(cx - 9, y0 + 4, 18, cr[2])
    # ---- neck + head
    cv.rect(cx - 3, y0 - 10, 6, 5, sk[2]); cv.hline(cx - 3, y0 - 6, 6, sk[1])
    hcx, hcy = cx + turn, y0 - 17
    for side in (-1, 1):                                            # ears (backlit: warm red glow)
        if side == turn: continue
        ex = hcx + side * 10 - (1 if side < 0 else 0)
        cv.rrect(ex - 1, hcy - 1, 3, 6, C('#c86a58'), r=1); cv.px(ex, hcy + 1, C('#f0a080')); cv.px(ex, hcy + 2, C('#f0a080'))
        E[hcy - 1:hcy + 5, ex - 1:ex + 2] = np.maximum(E[hcy - 1:hcy + 5, ex - 1:ex + 2], 0.45)
        if side == sun_side: cv.rect(ex + side, hcy, 1, 4, C('#ffb48a')); E[hcy:hcy + 4, ex + side] = 0.9
    _messy_hair(cv, hcx, hcy, 10.0, 9.5, hr, rng, spikes=5, spike_len=1)
    for side in (-1, 1):                                            # glasses' temple arms resting on the ears
        if side == turn: continue
        tx = hcx + side * 10 - (1 if side < 0 else 0)
        cv.hline(tx - (1 if side > 0 else 0), hcy - 2, 3, C('#14141c'))
        cv.px(tx + side, hcy - 1, C('#14141c'))
        if side == sun_side: cv.px(tx + side, hcy - 2, C('#c8c8d8')); E[hcy - 2, tx + side] = 0.8
    if turn:                                                        # head turned: the frame's edge + cheek peek out
        fx = hcx + turn * 10
        cv.rect(fx - (1 if turn < 0 else 0), hcy - 1, 2, 5, sk[3]); cv.vline(fx + (1 if turn > 0 else -1), hcy - 2, 4, C('#14141c'))
    a = cv.a
    m = a[..., 3] > 127                                             # despeckle: no floating 1-px hair tips
    nb = sum(np.roll(np.roll(m, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
    a[m & (nb < 2)] = 0
    _outline(a, C('#22182a'))
    _rim(a, E, sun_side, col=(255, 200, 146), k=0.85)
    E[a[..., 3] < 128] = 0
    for i in range(-13, 14):                                        # contact shadow on the planks
        if a[deck, cx + i, 3] < 128: a[deck, cx + i] = (24, 14, 22, 130 if abs(i) < 11 else 70)
    return SimpleNamespace(rgba=a, E=E, ax=cx, ay=deck, w=W_, h=H_, hand=None)


def kid_back(sun_side=1, shirt=('#d8463a', '#f4ecdc'), hair='#25212b', skin='#f3c9a2', seed=8, rod=False):
    """a small boy from behind (王工 as a child, EGG photo): sitting on the pier edge, the same messy hair + cowlick,
    a red / cream striped T-shirt, sun-browned arms, hands on the deck.  30 x 38, anchor = bottom-centre on the deck."""
    W_, H_ = 30, 38
    cv = Canvas(W_, H_); E = np.zeros((H_, W_), np.float32)
    rng = np.random.default_rng(seed)
    cx, deck = 15, 36
    hr = ramp(hair, 6, dark=0.08, light=0.55); sk = ramp(skin, 6)
    s1, s2 = ramp(shirt[0], 6), ramp(shirt[1], 6)
    cv.rect(cx - 7, deck - 4, 14, 4, C('#3a5a8a')); cv.rect(cx - 7, deck - 1, 14, 1, C('#283e60'))   # shorts
    y0 = 17
    for j in range(deck - 4 - y0):
        half = 5.5 + 2.2 * math.sqrt(min(j / 4.0, 1.0))
        for i in range(int(round(-half)), int(round(half))):
            band = ((j + 1) // 2) % 2
            c = (s1 if band else s2)[3 if i * sun_side > -4 else 2]
            cv.px(cx + i, y0 + j, c)
    for side in (-1, 1):                                            # short sleeves + thin arms to the deck
        ax0 = cx + side * 8
        cv.rect(ax0 - 1 - (1 if side < 0 else 0), y0 + 2, 3, 4, s1[2])
        cv.rect(ax0 - (1 if side < 0 else 0), y0 + 6, 2, deck - y0 - 8, sk[2])
        cv.rect(ax0 - (1 if side < 0 else 0) + side, deck - 2, 2, 2, sk[3])
    cv.rect(cx - 2, y0 - 2, 4, 2, sk[2])                            # neck
    hcx, hcy = cx, y0 - 8
    for side in (-1, 1):
        ex = hcx + side * 7 - (1 if side < 0 else 0)
        cv.rrect(ex - 1, hcy - 1, 3, 5, C('#e08a70'), r=1)
        E[hcy - 1:hcy + 4, ex - 1:ex + 2] = 0.35
    _messy_hair(cv, hcx, hcy, 7.2, 7.0, hr, rng, spikes=5)
    if rod:                                                         # a little bamboo rod held up on the right
        for k in range(14): cv.px(cx + 9 + k // 2, y0 + 6 - k, C('#c8a060'))
    a = cv.a
    _outline(a, C('#22182a'))
    _rim(a, E, sun_side, col=(255, 206, 150), k=0.85)
    E[a[..., 3] < 128] = 0
    return SimpleNamespace(rgba=a, E=E, ax=cx, ay=deck, w=W_, h=H_, hand=None)
