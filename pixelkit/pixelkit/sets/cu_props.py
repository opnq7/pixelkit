"""pixelkit.sets.cu_props - natively drawn LARGE props for close-ups (pixelkit.vec), matched to the room props:

    bobber_on_stand(S)        the Act IV keepsake float on its turned-wood base (= river_pier.BOB_FINE design)
    crt(w, h, content)        Claude's beige CRT, 3/4 front, curved glossy glass; content = RGBA drawn on the glass
    form_screen(w, h, u, ok)  the screen content: 王工's 请假单 being filled (u 0..1) -> green ✓ (ok 0..1)
    keyboard(w, h, press)     beige keyboard, top view at a slant; press = set of key indices pushed down
    photo_frame(pr, w, h)     walnut desk frame + mat + the print (RGB array) + glass sheen, on its stand
    laptop_back(w, h)         the back of Wang's laptop lid (coral spark sticker), screen glow spilling round the edges
Each returns a Sprite (rgba + E) with .ax, .ay = bottom-centre (where it stands on the desk)."""
import math
import numpy as np, cv2
from ..core import C
from ..vec import Painter, rrect, ellipse, circle, seg, arc, poly_stroke, union, sub, inter
from ..characters import claude as CL

KEY = (-0.5, -0.55, 0.67)
WOOD = [C('#3a2018'), C('#5a3424'), C('#7a4a30'), C('#9a6440'), C('#b8804e'), C('#d29a62')]
HONEY = [C('#6a3a1c'), C('#8a5228'), C('#c8843e'), C('#e0a058'), C('#f0bc78'), C('#fad6a0')]
GOLD = [C('#6a4a1a'), C('#a8783a'), C('#d9a64e'), C('#e8b860'), C('#f8dc90')]
REDR = [C('#5a1820'), C('#a32e2c'), C('#d8433a'), C('#ff6a3a'), C('#ff9a7a')]
WHITE = [C('#8a8088'), C('#d8cec8'), C('#f0e8e0'), C('#fff6ec')]
BEIGE = [C('#5e5446'), C('#857a66'), C('#aea38c'), C('#cfc5ac'), C('#e4dcc4'), C('#f2ecd8')]
INK = C('#2a1e22')


def _spr(p, ax, ay):
    s = p.sprite(); s.ax, s.ay = int(round(ax)), int(round(ay)); return s


def bobber_on_stand(S=4, light=KEY, glow=1.0):
    """float ~ 7S x 17S standing on a 13S x 5S wooden base.  Sprite anchor = base bottom-centre."""
    W, H = int(16 * S), int(25 * S)
    p = Painter(W, H)
    u, v = p.uv()
    cx = W / 2
    by = H - 5.2 * S
    # base (turned wood): top ellipse + body
    p.part(union(rrect(u, v, cx - 6.5 * S, by + 1.2 * S, 13 * S, 3.6 * S, 1.0 * S), ellipse(u, v, cx, by + 1.2 * S, 6.5 * S, 1.6 * S)),
           WOOD, bevel=1.6 * S, light=light, amb=0.3, ink=INK)
    p.part(ellipse(u, v, cx, by + 1.0 * S, 5.6 * S, 1.2 * S), WOOD[2:], bevel=1.0 * S, light=(0, -1, 0.4), amb=0.5, ink=WOOD[1])
    p.fill(rrect(u, v, cx - 2.2 * S, by + 2.6 * S, 4.4 * S, 1.2 * S, 0.3 * S), GOLD[3]); p.fill(rrect(u, v, cx - 2.2 * S, by + 2.6 * S, 1.2 * S, 0.5 * S, 0.2 * S), GOLD[4])
    # float (bottom -> top): eyelet, stem, ring, body, ring, white band, ring, red cap, tip
    p.part(seg(u, v, cx, by + 0.6 * S, cx, by - 3.0 * S, th=0.9 * S), [C('#1e161e'), C('#3a2a3a'), C('#5a4a5a')], bevel=0.4 * S, light=light, amb=0.4, ink=INK)
    y = by - 3.0 * S
    body = ellipse(u, v, cx, y - 4.4 * S, 2.6 * S, 4.6 * S)
    p.part(body, HONEY, bevel=2.0 * S, light=light, amb=0.28, ink=INK)
    p.fill(inter(body, rrect(u, v, cx - 3 * S, y - 4.6 * S, 6 * S, 0.7 * S, 0)), GOLD[3])
    p.part(rrect(u, v, cx - 2.0 * S, y - 1.2 * S, 4.0 * S, 1.1 * S, 0.4 * S), GOLD, bevel=0.5 * S, light=light, amb=0.35, ink=INK)
    yb = y - 8.6 * S
    p.part(rrect(u, v, cx - 2.6 * S, yb - 2.4 * S, 5.2 * S, 2.8 * S, 0.8 * S), WHITE, bevel=1.0 * S, light=light, amb=0.4, ink=INK, E=0.08 * glow)
    p.fill(circle(u, v, cx - 0.2 * S, yb - 1.0 * S, 0.65 * S), C('#f07a4a'), E=0.3 * glow)
    p.part(rrect(u, v, cx - 2.0 * S, yb - 3.4 * S, 4.0 * S, 1.1 * S, 0.4 * S), GOLD, bevel=0.5 * S, light=light, amb=0.35, ink=INK)
    cap = union(ellipse(u, v, cx, yb - 4.2 * S, 1.8 * S, 1.2 * S), seg(u, v, cx, yb - 4.6 * S, cx, yb - 7.4 * S, th=1.3 * S))
    p.part(cap, REDR, bevel=0.8 * S, light=light, amb=0.4, ink=INK, E=0.3 * glow)
    p.fill(circle(u, v, cx, yb - 7.9 * S, 0.75 * S), C('#fff2c8'), E=0.95 * glow)
    p.fill(seg(u, v, cx - 0.9 * S, y - 7.0 * S, cx - 1.3 * S, y - 3.0 * S, th=0.5 * S), HONEY[5])       # varnish highlight
    return _spr(p, cx, H)


def form_screen(w, h, u_fill=1.0, ok=0.0, t=0.0, mode='form'):
    """the monitor content (RGBA, w x h): 'doc' = Claude's own doc being typed, 'form' = the 请假单 filling in,
    then ok 0..1 draws the green ✓ badge popping in."""
    p = Painter(w, h)
    U, V = p.uv()
    p.fill(rrect(U, V, 0, 0, w, h, 0), C('#eceae2'), E=0.55)
    tb = max(4, int(h * 0.13))
    p.fill(rrect(U, V, 0, 0, w, tb, 0), C('#a03a2a') if mode == 'form' else C('#000080'), E=0.6)
    for i in range(3):
        p.fill(rrect(U, V, w - (i + 1) * (tb - 1) - 1, 1, tb - 2, tb - 2, 0), C('#c8c4bc'), E=0.55)
    p.fill(rrect(U, V, 3, tb * 0.3, w * 0.35, tb * 0.4, 0), C('#ffffff'), E=0.7)
    rows = 5
    y0 = tb + h * 0.08
    dy = (h - y0 - h * 0.12) / rows
    for i in range(rows):
        yy = y0 + i * dy
        if mode == 'form':
            p.fill(rrect(U, V, w * 0.06, yy + dy * 0.25, w * 0.2, dy * 0.32, 1), C('#8a8a9a'), E=0.5)
            p.fill(rrect(U, V, w * 0.30, yy + dy * 0.1, w * 0.64, dy * 0.62, 1), C('#ffffff'), E=0.6)
            k = float(np.clip(u_fill * rows - i, 0, 1))
            if k > 0: p.fill(rrect(U, V, w * 0.33, yy + dy * 0.25, w * 0.56 * k, dy * 0.32, 1), C('#1f4fbf'), E=0.55)
        else:
            k = float(np.clip(u_fill * rows - i, 0, 1))
            if k > 0: p.fill(rrect(U, V, w * 0.06, yy + dy * 0.3, w * (0.86 if i % 3 != 2 else 0.5) * k, dy * 0.3, 1), C('#6a6a7a'), E=0.5)
    if mode == 'doc' and (t * 2.2) % 1 < 0.6:
        i = min(rows - 1, int(u_fill * rows)); yy = y0 + i * dy
        xx = w * 0.06 + w * (0.86 if i % 3 != 2 else 0.5) * float(np.clip(u_fill * rows - i, 0, 1))
        p.fill(rrect(U, V, xx, yy + dy * 0.1, max(1, w * 0.02), dy * 0.6, 0), C('#1a1a1a'), E=0.5)
    if ok > 0:
        s = 0.6 + 0.4 * min(1.0, ok * 1.6) + 0.12 * math.sin(min(1.0, ok) * math.pi)
        cx, cy, r = w / 2, h * 0.56, min(w, h) * 0.26 * s
        p.fill(circle(U, V, cx, cy, r + 1.2), C('#1e6a2c'), E=0.6)
        p.fill(circle(U, V, cx, cy, r), C('#3aaa4a'), E=0.8)
        p.fill(poly_stroke(U, V, [(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.36), (cx + r * 0.5, cy - r * 0.34)], th=max(1.5, r * 0.22)),
               C('#ffffff'), E=1.0)
    s = p.sprite(); return s


def crt(w=120, h=104, content=None, light=KEY, glow=1.0, turn=1):
    """beige CRT, 3/4 view (turn=+1: screen faces right, we see its left flank).  content: Sprite / RGBA for the
    glass (resized to fit).  Anchor = bottom-centre of the foot."""
    p = Painter(w, h)
    u, v = p.uv()
    fw = int(w * 0.16)                  # visible flank
    bx0 = fw if turn > 0 else 0
    bw = w - fw
    bh = h * 0.80
    # foot
    p.part(rrect(u, v, w * 0.30, h * 0.86, w * 0.46, h * 0.12, 3), BEIGE, bevel=3, light=light, amb=0.3, ink=INK)
    p.part(rrect(u, v, w * 0.40, h * 0.78, w * 0.26, h * 0.12, 2), BEIGE[:5], bevel=2, light=light, amb=0.25, ink=INK)
    # flank (the deep CRT body seen from the side)
    if turn > 0:
        fl = p.poly([(bx0 + 2, 3), (0, h * 0.08), (0, bh * 0.92), (bx0 + 2, bh - 1)])
    else:
        fl = p.poly([(w - fw - 2, 3), (w, h * 0.08), (w, bh * 0.92), (w - fw - 2, bh - 1)])
    p.part(fl, BEIGE, bevel=4, light=light, amb=0.25, normal=(-0.75 * turn, 0, 0.66), ink=INK)
    for i in range(5):                   # vents on the flank
        yy = h * 0.2 + i * h * 0.1
        p.fill(seg(u, v, 3 if turn > 0 else w - 3, yy + 2, fw - 3 if turn > 0 else w - fw + 3, yy, th=1.2), BEIGE[1], where=fl)
    # front bezel
    fm = p.part(rrect(u, v, bx0, 0, bw, bh, 7), BEIGE, bevel=5, light=light, amb=0.30, ink=INK)
    gx0, gy0, gw, gh = bx0 + bw * 0.10, bh * 0.09, bw * 0.80, bh * 0.70
    p.part(rrect(u, v, gx0 - 3, gy0 - 3, gw + 6, gh + 6, 7), BEIGE[:5], bevel=3, light=(0.4, 0.6, 0.7), amb=0.35, ink=BEIGE[1])
    gm = p.fill(rrect(u, v, gx0, gy0, gw, gh, 6), C('#10161c'))
    if content is not None:
        a = content.rgba if hasattr(content, 'rgba') else content
        E = content.E if hasattr(content, 'E') else np.zeros(a.shape[:2], np.float32)
        cw, ch = int(gw - 4), int(gh - 4)
        a2 = cv2.resize(a, (cw, ch), interpolation=cv2.INTER_AREA)
        E2 = cv2.resize(E, (cw, ch), interpolation=cv2.INTER_AREA)
        x0, y0 = int(round(gx0 + 2)), int(round(gy0 + 2))
        sub_m = gm[y0:y0 + ch, x0:x0 + cw] & (a2[..., 3] > 127)
        reg = p.rgb[y0:y0 + ch, x0:x0 + cw]
        reg[sub_m] = a2[..., :3][sub_m] / 255.0
        p.E[y0:y0 + ch, x0:x0 + cw][sub_m] = E2[sub_m] * glow
    # glass curvature: darker corners, scan lines, sheen
    cxg, cyg = gx0 + gw / 2, gy0 + gh / 2
    r = np.hypot((u - cxg) / (gw / 2), (v - cyg) / (gh / 2))
    p.rgb[gm] *= np.clip(1.08 - 0.22 * r[gm] ** 2, 0.6, 1.0)[..., None]
    p.rgb[gm & (np.floor(v) % 2 == 0)] *= 0.94
    sh = gm & (np.abs((u - gx0) + 0.7 * (v - gy0) - gw * 0.22) < 2.2)
    p.rgb[sh] = p.rgb[sh] * 0.8 + 0.2
    # badge + power LED
    p.fill(rrect(u, v, bx0 + bw * 0.12, bh * 0.86, bw * 0.18, bh * 0.05, 1), BEIGE[2])
    p.fill(rrect(u, v, bx0 + bw * 0.80, bh * 0.865, 3, 2, 0.5), C('#5dff8f'), E=0.9 * glow)
    s = p.sprite(); s.ax, s.ay = w // 2 + (fw // 2) * turn, h
    s.glass = (gx0, gy0, gw, gh)
    return s


def keyboard(w=110, h=26, press=(), light=KEY):
    p = Painter(w, h)
    u, v = p.uv()
    body = p.poly([(6, 0), (w - 6, 0), (w, h - 2), (0, h - 2)])
    p.part(body, BEIGE, bevel=3, light=light, amb=0.3, ink=INK)
    rows = 4
    for r in range(rows):
        y0 = 3 + r * (h - 8) / rows
        inset = 6 * (1 - r / rows) + 2
        n = 14 - (r == 3) * 4
        kw = (w - 2 * inset) / n
        for i in range(n):
            if r == 3 and i == 4: kw2 = kw * 4
            else: kw2 = kw
            if r == 3 and 4 < i < 8: continue
            x0 = inset + i * kw + 0.5
            down = (r * 16 + i) in press
            d = rrect(u, v, x0, y0 + (1 if down else 0), kw2 - 1.2, (h - 8) / rows - 1.0, 1.0)
            p.part(d, BEIGE[1:] if not down else BEIGE[:5], bevel=1.2, light=light, amb=0.35, ink=BEIGE[0], outline=None)
            p.edge(p.mask(d), 0.7)
    s = p.sprite(); s.ax, s.ay = w // 2, h
    return s


def photo_frame(pr, w=64, h=50, light=KEY, wood=None, mat='#e9dfc8', sheen=0.0, warmth=0.0):
    """walnut frame (w x h) standing on the desk, slightly turned; pr = the print RGB(A) uint8 array."""
    W, H = w + 6, h + 6
    p = Painter(W, H)
    u, v = p.uv()
    wd = wood or [C('#2a160e'), C('#40241a'), C('#5a3424'), C('#7a5034'), C('#9a6a48'), C('#b88660')]
    p.fill(p.poly([(W * 0.62, H - 1), (W * 0.82, H - 1), (W * 0.70, h * 0.45)]), C('#2a160e'))   # the stand behind
    fr = rrect(u, v, 2, 1, w, h, 2)
    p.part(fr, wd, bevel=3.2, light=light, amb=0.3, ink=INK)
    bw = max(4, int(w * 0.09))
    p.part(rrect(u, v, 2 + bw, 1 + bw, w - 2 * bw, h - 2 * bw, 0), wd[1:4], bevel=1.0, light=(0.4, 0.5, 0.75), amb=0.3, outline=None)
    mx0, my0, mw, mh = 2 + bw + 1, 1 + bw + 1, w - 2 * bw - 2, h - 2 * bw - 2
    p.fill(rrect(u, v, mx0, my0, mw, mh, 0), C(mat))
    pw, ph = int(mw - 6), int(mh - 6)
    img = cv2.resize(pr[..., :3], (pw, ph), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    x0, y0 = int(round(mx0 + 3)), int(round(my0 + 3))
    p.rgb[y0:y0 + ph, x0:x0 + pw] = img
    p.a[y0:y0 + ph, x0:x0 + pw] = True
    if warmth > 0: p.E[y0:y0 + ph, x0:x0 + pw] = 0.35 * warmth
    p.rgb[y0 - 1, x0:x0 + pw] *= 0.8; p.rgb[y0:y0 + ph, x0 - 1] *= 0.85
    gl = (rrect(u, v, 2 + bw, 1 + bw, w - 2 * bw, h - 2 * bw, 0) <= 0)
    band = gl & (np.abs(u + 0.9 * v - (W * 0.35 + W * 1.2 * sheen)) < 3.0)
    p.rgb[band] = p.rgb[band] * 0.75 + 0.25
    p.rgb[gl & (np.abs(u + 0.9 * v - (W * 0.35 + W * 1.2 * sheen) - 6) < 1.0)] *= 1.12
    s = p.sprite(); s.ax, s.ay = W // 2, H - 1
    s.print_box = (x0, y0, pw, ph)
    return s


def laptop_back(w=120, h=60, light=KEY, glow=1.0, sticker=True):
    """the back of the lid, seen from behind (towards the camera); the screen glow spills round the edges."""
    W, H = w + 8, h + 6
    p = Painter(W, H)
    u, v = p.uv()
    halo = rrect(u, v, 0, 0, W, H - 2, 8)
    p.fill(halo, C('#7fa8e8'), E=0.22 * glow, where=~p.mask(rrect(u, v, 2, 2, W - 4, H - 4, 7)), alpha=0.6)
    lid = rrect(u, v, 4, 3, w, h, 5)
    p.part(lid, [C('#14141c'), C('#22222c'), C('#30303c'), C('#3e3e4c'), C('#4e4e5e')], bevel=4, light=(0, 0.2, 0.98), amb=0.35, ink=C('#0c0c12'))
    p.rim(p.mask(lid), (0, -1), C('#bcd8ff'), 1, 0.85, E=0.5 * glow)
    p.rim(p.mask(lid), (-1, 0), C('#8fb0e8'), 1, 0.5, E=0.3 * glow)
    p.rim(p.mask(lid), (1, 0), C('#8fb0e8'), 1, 0.5, E=0.3 * glow)
    if sticker:
        sx, sy = W * 0.66, H * 0.42
        rays = [(-90, 7), (90, 7), (180, 7), (0, 7), (-135, 6), (-50, 5.5), (130, 5.5), (40, 6.5)]
        d = circle(u, v, sx, sy, 2.2)
        for a, L in rays:
            d = np.minimum(d, seg(u, v, sx, sy, sx + L * math.cos(math.radians(a)), sy + L * math.sin(math.radians(a)), th=1.8))
        p.fill(d - 1.0, C('#f6eee6')); p.fill(d, C('#d97757'), E=0.05)
        p.fill(rrect(u, v, W * 0.18, H * 0.62, 16, 10, 2) - 0.8, C('#f6eee6'))
        p.fill(rrect(u, v, W * 0.18, H * 0.62, 16, 10, 2), C('#3d6fd8'))
        p.fill(seg(u, v, W * 0.18 + 3, H * 0.62 + 5, W * 0.18 + 13, H * 0.62 + 5, th=1.2), C('#ffffff'))
    s = p.sprite(); s.ax, s.ay = W // 2, H
    return s


def desk(w=480, h=80, wood=None, light=KEY, edge=10, seed=4):
    """a desk top seen at a grazing angle across the bottom of a close-up: planks with grain + a front lip."""
    p = Painter(w, h)
    u, v = p.uv()
    wd = wood or [C('#2a1810'), C('#3e2416'), C('#56341f'), C('#6e4429'), C('#865634'), C('#9c6a40')]
    top = p.mask(v - (h - edge))
    p.part(top, wd, bevel=6, light=(0, -0.3, 0.95), amb=0.55, outline=None, dither=0.3)
    rng = np.random.RandomState(seed)
    for i in range(10):                                   # soft grain streaks (dithered, close to the base tone)
        yy = rng.uniform(2, h - edge - 2)
        x0 = rng.uniform(-60, w); L = rng.uniform(60, 200) * (0.5 + yy / h)
        p.tint(p.mask(seg(u, v, x0, yy, x0 + L, yy + rng.uniform(-0.8, 0.8), th=1.0 + yy / h)) & top & (p.bayer < 0.1), wd[1], 0.35)
    p.fill(seg(u, v, 0, 0.5, w, 0.5, th=1.0), wd[4], where=top)
    lip = ~top & (v < h)
    p.part(lip, wd, bevel=3, light=(0, -0.8, 0.6), amb=0.25, outline=None)
    p.fill(seg(u, v, 0, h - edge + 0.5, w, h - edge + 0.5, th=1.0), wd[5])
    s = p.sprite(); s.ax, s.ay = 0, 0
    return s
