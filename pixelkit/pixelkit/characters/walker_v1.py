"""pixelkit.characters.walker - background passers-by (chibi humans that WALK), built on characters.human.

They are extras: they must make a street feel alive without stealing the eye from the lead.  So:
  * they walk on a back lane (feet ~186-192 on the 960x270 street; the lead walks at 200), in profile-ish
    3/4 view (look turned toward the walking direction), never stopping in front of the lead;
  * `background()` pushes them back in depth: desaturated, cooler, lower contrast, slightly lighter
    (aerial perspective) - the lead keeps the saturated colours and the hard outline;
  * small props tell little stories (coffee, a baguette bag, a phone, a dog on a leash).

    from pixelkit.characters import walker
    W = walker.Walker(look=walker.LOOKS[0], x0=300, v=-22, foot=190, prop='coffee', t0=0)
    for spr, x, y, alpha in W.sprites(t): mid.put(spr, x, y, 0)      # (+ casters for their shadows)
"""
import math
from types import SimpleNamespace
import numpy as np
from ..core import Canvas, C, mix
from ..palette import ramp
from ..scene import Sprite
from . import human as HU

LEGS = [((3, 0), (-2, 0)), ((0, 2), (0, 0)), ((-2, 0), (3, 0)), ((0, 0), (0, 2))]     # (dx, lift) per leg
BOB = [0, -1, 0, -1]
ARMS = [(-2, 2), (0, 0), (2, -2), (0, 0)]                                            # hand dx (left, right)
FOOT_Y = 55                    # feet line inside the 56 x 62 sprite (head top = HU.HY = 7)

def _rp(h, n=6, **kw): return [tuple(c) for c in ramp(h, n, **kw)]

def draw_legs(cv, L, phase, pants='#3a4258', shoes='#2a2226'):
    x, y, w, h = HU.torso_box()
    pr = _rp(pants, 6)
    lo = LEGS[phase % 4]
    for (lx0, (dx, lift)) in zip((x + 4, x + w - 10), lo):
        lx = lx0 + dx; top = y + h - 3
        cv.rrect(lx, top, 6, 9 - lift, pr[0], 2); cv.rect(lx + 1, top + 1, 4, 7 - lift, pr[2]); cv.vline(lx + 1, top + 1, 6 - lift, pr[3])
        fy = top + 7 - lift
        cv.rrect(lx - 1, fy, 8, 4, C(shoes), 2); cv.rect(lx, fy + 1, 6, 1, mix(C(shoes), C('#ffffff'), 0.25))

def draw_walk_arms(cv, L, phase, prop=None):
    """swinging arms (or a carried prop).  Returns hand positions."""
    bx, by, bw, bh = HU.torso_box()
    cr = _rp(L.cloth_col if L.cloth != 'shirt_tie' else '#eef0f4', 6); sk = _rp(L.skin, 6, dark=0.42, light=0.95)
    Lx, Rx, sy = bx + 2, bx + bw - 3, by + 4
    dl, dr = ARMS[phase % 4]
    hands = {}
    # left arm swings unless it carries the bag / leash
    if prop in ('bag', 'dog'):
        HU._sleeve(cv, [(Lx, sy), (Lx - 4, sy + 9)], cr); HU._hand(cv, Lx - 7, sy + 8, sk); hands['L'] = (Lx - 5, sy + 11)
    else:
        HU._sleeve(cv, [(Lx, sy), (Lx - 3 + dl, sy + 9)], cr); HU._hand(cv, Lx - 6 + dl, sy + 8, sk); hands['L'] = (Lx - 4 + dl, sy + 10)
    if prop in ('coffee', 'phone'):
        HU._sleeve(cv, [(Rx, sy), (Rx + 3, sy + 7), (Rx - 3, sy + 8)], cr); HU._hand(cv, Rx - 6, sy + 6, sk); hands['R'] = (Rx - 4, sy + 6)
    else:
        HU._sleeve(cv, [(Rx, sy), (Rx + 3 + dr, sy + 9)], cr); HU._hand(cv, Rx + dr, sy + 8, sk); hands['R'] = (Rx + 2 + dr, sy + 10)
    return hands

def draw_prop(cv, E, prop, hands):
    if prop == 'coffee':
        x, y = hands['R']
        cv.rect(x - 2, y - 6, 5, 7, C('#2a1a20')); cv.rect(x - 1, y - 5, 3, 5, C('#f4f0e8')); cv.rect(x - 1, y - 3, 3, 2, C('#a8703e'))
        cv.hline(x - 2, y - 7, 5, C('#5a3a2a'))
    elif prop == 'phone':
        x, y = hands['R']
        cv.rect(x - 2, y - 5, 4, 6, C('#1a1a22')); cv.rect(x - 1, y - 4, 2, 4, C('#bfe4ff')); E[y - 4:y, x - 1:x + 1] = 0.8
    elif prop == 'bag':
        x, y = hands['L']
        cv.rect(x - 4, y, 9, 10, C('#2a1a20')); cv.rect(x - 3, y + 1, 7, 8, C('#d8b47a')); cv.hline(x - 3, y + 1, 7, C('#f0d09a'))
        cv.line(x - 1, y + 1, x + 2, y - 5, C('#e8b46a')); cv.line(x + 1, y + 1, x + 4, y - 4, C('#c8843e'))        # baguette
        cv.vline(x + 3, y + 2, 7, C('#b08a5a'))

def background(rgba, k=0.36, tint='#a8b0d0', lift=0.04, contrast=0.86):
    """depth treatment for extras: desaturate toward a cool grey-lilac, flatten contrast, lift slightly."""
    a = rgba.copy()
    m = a[..., 3] > 0
    rgb = a[..., :3].astype(np.float32)
    g = rgb.mean(-1, keepdims=True)
    t = np.asarray(C(tint)[:3], np.float32)
    rgb = rgb * (1 - k) + (g * 0.55 + t * 0.45) * k
    mu = rgb[m].mean(0) if m.any() else 128
    rgb = mu + (rgb - mu) * contrast
    rgb = rgb + (255 - rgb) * lift
    a[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    return a

def draw(L, phase=0, face='normal', look=(2, 0), prop=None, pants='#3a4258', flip=False):
    """one frame -> SimpleNamespace(rgba, E, ax, ay, bob).  (ax, ay) = head top centre (like human.draw)."""
    s = Sprite(HU.SW, HU.SH)
    cv, E = s.cv, s.E
    draw_legs(cv, L, phase, pants)
    body = Sprite(HU.SW, HU.SH)
    HU.draw_torso(body.cv, body.E, L, legs=False)
    HU.draw_head(body.cv, body.E, L, face, look)
    arms = Sprite(HU.SW, HU.SH)
    hands = draw_walk_arms(arms.cv, L, phase, prop)
    draw_prop(arms.cv, arms.E, prop, hands)
    bob = BOB[phase % 4]
    hip = HU.torso_box()[1] + HU.torso_box()[3] - 3
    for layer in (body, arms):
        a = layer.cv.a; e = layer.E
        if bob:
            a2 = a.copy(); e2 = e.copy()
            a2[:hip + bob] = a[-bob:hip]; e2[:hip + bob] = e[-bob:hip]
            a, e = a2, e2
        m = a[..., 3] > 0
        cv.a[m] = a[m]; E[m] = e[m]
    rgba, Em = cv.a, E
    if flip: rgba, Em = rgba[:, ::-1].copy(), Em[:, ::-1].copy()
    return SimpleNamespace(rgba=rgba, E=Em, ax=HU.AX, ay=HU.AY, bob=bob)

def dog_sprite(phase, col='#e8c896', flip=False):
    """tiny shiba-ish dog, 16 x 11, trotting (2-frame legs)."""
    s = Sprite(16, 11); cv = s.cv
    O = C('#2a1a20'); c = _rp(col, 5)
    cv.rrect(3, 3, 10, 5, O, 2); cv.rect(4, 4, 8, 3, c[3]); cv.hline(4, 6, 8, c[2])
    cv.rrect(10, 0, 6, 6, O, 2); cv.rect(11, 1, 4, 4, c[3]); cv.px(11, 0, O); cv.px(14, 0, O)
    cv.px(14, 2, O); cv.px(15, 3, O); cv.rect(11, 4, 3, 1, C('#fff4e8'))
    cv.rect(1, 2, 3, 2, c[3]); cv.px(1, 1, O); cv.px(0, 2, O)                                    # curled tail
    lg = [(4, 8), (6, 8), (10, 8), (12, 8)] if phase % 2 == 0 else [(5, 8), (7, 8), (9, 8), (11, 8)]
    for (x, y) in lg: cv.vline(x, y, 3, O)
    if flip: s.cv.a = s.cv.a[:, ::-1].copy(); s.E = s.E[:, ::-1].copy()
    return s

LOOKS = [
    HU.Look(hair='bun', hair_col='#4a3226', skin='#f2cfae', cloth='cardigan', cloth_col='#c88a6a', accent='#f4e8d0', seed=2),
    HU.Look(hair='short', hair_col='#2a2630', skin='#e8bc94', glasses='round', cloth='tshirt', cloth_col='#6a8ab0', seed=3),
    HU.Look(hair='long', hair_col='#2a2228', skin='#f4d4b8', cloth='hoodie', cloth_col='#9ab07a', seed=4),
    HU.Look(hair='side', hair_col='#6a5040', skin='#dcae86', cloth='shirt_tie', cloth_col='#eef0f4', accent='#4a6ab0', seed=5),
    HU.Look(hair='bald', hair_col='#8a7a70', skin='#e8c09c', glasses='square', stubble=True, cloth='cardigan', cloth_col='#8a8a70', accent='#d8c8a0', seed=6),
]
PANTS = ['#4a4a5a', '#3a4258', '#5a4a40', '#2e3448', '#6a6458']


class Walker:
    """a passer-by crossing the set at constant speed.
    x0: x at t0, v: px/s (negative = walking left), foot: feet line, fps: steps per second (cadence)."""
    def __init__(self, look, x0, v, foot=190, prop=None, t0=0.0, fps=None, pants=None, depth=0.36, face='normal', seed=0):
        self.L, self.x0, self.v, self.foot, self.prop, self.t0 = look, x0, v, foot, prop, t0
        self.fps = fps or (5.0 + abs(v) / 10.0)
        self.pants = pants or PANTS[seed % len(PANTS)]
        self.depth, self.face, self.seed = depth, face, seed
        self._cache = {}

    def x(self, t): return self.x0 + self.v * (t - self.t0)

    def frame(self, t):
        ph = int((t - self.t0) * self.fps + self.seed) % 4
        blink = ((t + self.seed * 0.7) % 3.1) < 0.12
        key = (ph, blink)
        if key not in self._cache:
            flip = self.v < 0
            p = draw(self.L, ph, 'blink' if blink else self.face, (2, 0), self.prop, self.pants, flip=flip)
            rgba = background(p.rgba, self.depth) if self.depth > 0 else p.rgba
            self._cache[key] = (rgba, p.E * (0.6 if self.depth else 1.0), p.bob)
        return self._cache[key]

    def sprites(self, t):
        """[(rgba, X, Y, E, alpha_bool, foot)] in set coordinates."""
        rgba, E, bob = self.frame(t)
        x = self.x(t)
        ax = HU.AX if self.v >= 0 else HU.SW - 1 - HU.AX
        X = int(round(x - ax)); Y = int(round(self.foot - FOOT_Y))
        out = [(rgba, X, Y, E, rgba[..., 3] > 127, self.foot)]
        if self.prop == 'dog':
            ph = int((t - self.t0) * self.fps * 2) % 2
            d = dog_sprite(ph, flip=self.v < 0)
            da = background(d.cv.a, self.depth) if self.depth > 0 else d.cv.a
            lead = 22 if self.v >= 0 else -22 - 16
            dx, dy = int(round(x + lead)), int(round(self.foot - 10))
            out.append((da, dx, dy, d.E, da[..., 3] > 127, self.foot))
            # leash: from the left hand to the dog's collar
            hx = X + (HU.torso_box()[0] - 3 if self.v >= 0 else HU.SW - 1 - (HU.torso_box()[0] - 3))
            hy = Y + HU.torso_box()[1] + 15
            cx = dx + (11 if self.v >= 0 else 4); cy = dy + 3
            n = max(abs(cx - hx), 1)
            leash = np.zeros((max(hy, cy) - min(hy, cy) + 6, n + 2, 4), np.uint8)
            x0_, y0_ = min(hx, cx), min(hy, cy) - 2
            for i in range(n + 1):
                u = i / n
                xx = hx + (cx - hx) * u; yy = hy + (cy - hy) * u + 3 * 4 * u * (1 - u)
                lx, ly = int(round(xx - x0_)), int(round(yy - y0_))
                if 0 <= ly < leash.shape[0] and 0 <= lx < leash.shape[1]: leash[ly, lx] = (150, 70, 60, 255)
            out.append((leash, x0_, y0_, np.zeros(leash.shape[:2], np.float32), leash[..., 3] > 127, None))
        return out
