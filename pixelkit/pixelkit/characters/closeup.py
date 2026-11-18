"""pixelkit.characters.closeup - close-up versions of the cast, drawn NATIVELY at S x the room-sprite size
(pixelkit.vec), so a close-up keeps the same 4-screen-px pixel grid as the wide shots instead of blowing a 30 px
sprite up into 14 px blocks.  Same design / palette as characters.claude and characters.human, more detail:
soft bevel shading + dither, bezel and screen gloss, eye glow halos, a proper logo spark, lanyard stitching,
hair strands, glasses with lens reflections, stubble ...

    from pixelkit.characters import closeup as CU
    s = CU.claude_bust(S=3, face='happy', look=(2, 0), tilt=5, ant=(1.5, 0))    # Sprite (rgba + E), anchor .ax/.ay
    s = CU.wang_bust(S=3, face='soft', look=(2, 2), tilt=-3, mouth='o')

Faces (claude): normal blink wide happy q focus closed half        look = (dx, dy) in ROOM pixels (x S on screen)
Faces (wang):   normal blink tired closed soft smile down          mouth = 'flat' | 'o' | 'smile'
"""
import math
import numpy as np, cv2
from ..core import C
from ..vec import Painter, rrect, ellipse, circle, seg, arc, poly_stroke, union, sub, inter
from . import claude as CL

# ------------------------------------------------------------------ palettes (ramps dark -> light)
SHELL = [C('#6f6584'), C('#a59cb4'), C('#cbc3d0'), C('#e2dbd6'), C('#f1ece5'), C('#fbf8f2')]
SIDE = [C('#6f6584'), C('#8f8496'), C('#b5a9b2'), C('#cfc5c4'), C('#e0d8d2')]
BEZ = [C('#7e7488'), C('#a99fa8'), C('#c7bebc'), C('#dcd4d0')]
CORAL = [C('#5a2640'), C('#843a48'), C('#b0555a'), C('#d8776e'), C('#ec9284'), C('#f6b0a0')]
LANY = [C('#1f3a78'), C('#2a4f9e'), C('#3d6fd8'), C('#5e8ef0')]
HANDR = [C('#8d8299'), C('#c9c1cc'), C('#e8e3e2'), C('#f8f5f0')]
METALR = [C('#6a5a72'), C('#8f8496'), C('#c9c0c8'), C('#ece6ea')]
OUT = C('#2e2436')
KEY = (-0.50, -0.58, 0.64)          # default key: lamp, upper-left-front


def _eye(p, u, v, face, cx, cy, S, mirror, glow):
    """one Claude eye at centre (cx, cy) (screen units already x S).  Returns nothing; paints p."""
    EYE, EYE_HI, EYE_LO, HALO = CL.EYE, CL.EYE_HI, CL.EYE_LO, CL.HALO
    rx, ry = 3.0 * S, 4.0 * S
    hi_x = -1 if not mirror else 1
    E = 0.95 * glow
    if face in ('normal', 'wide', 'focus', 'half'):
        if face == 'wide': ry *= 1.14; cy -= 0.4 * S
        d = ellipse(u, v, cx, cy, rx, ry)
        if face == 'focus': d = np.maximum(d, (cy - 1.2 * S) - v)            # lid: flat top
        if face == 'half': d = np.maximum(d, (cy - 0.2 * S) - v)
        p.fill(d - 1.5 * S, mix_c(CL.SCR2, HALO, 0.45), E=0.10 * glow, where=~p.mask(d))
        p.fill(d - 0.75 * S, mix_c(CL.SCR3, HALO, 0.7), E=0.16 * glow, where=~p.mask(d))
        p.fill(d, EYE, E=E)
        p.fill(np.maximum(d, (cy + 1.4 * S) - v), EYE_LO, E=E * 0.9)        # peach lower third
        p.fill(np.maximum(d, (cy + 2.6 * S) - v), mix_c(EYE_LO, (226, 140, 110, 255), 0.5), E=E * 0.8)
        if face not in ('focus', 'half'):
            p.fill(ellipse(u, v, cx + hi_x * 1.2 * S, cy - 1.8 * S, 0.95 * S, 1.25 * S), EYE_HI, E=1.0 * glow)
            p.fill(circle(u, v, cx + hi_x * -1.0 * S, cy - 2.4 * S, 0.45 * S), EYE_HI, E=1.0 * glow)
        else:
            p.fill(ellipse(u, v, cx + hi_x * 1.2 * S, cy - 0.2 * S, 0.9 * S, 0.7 * S), EYE_HI, E=1.0 * glow)
    elif face == 'blink':
        d = rrect(u, v, cx - rx, cy + 1.2 * S, 2 * rx, 1.3 * S, 0.6 * S)
        p.fill(d - 0.9 * S, mix_c(CL.SCR3, HALO, 0.6), E=0.1 * glow, where=~p.mask(d)); p.fill(d, EYE, E=E)
    elif face == 'happy':                                   # ^ ^
        d = arc(u, v, cx, cy + 1.6 * S, 2.5 * S, 200, 340, th=1.55 * S)
        p.fill(d - 0.9 * S, mix_c(CL.SCR3, HALO, 0.6), E=0.1 * glow, where=~p.mask(d)); p.fill(d, EYE, E=E)
        p.fill(np.maximum(d, (cy - 0.2 * S) - v), EYE_HI, E=1.0 * glow)
    elif face == 'closed':                                  # u u
        d = arc(u, v, cx, cy - 0.4 * S, 2.6 * S, 20, 160, th=1.3 * S)
        p.fill(d - 0.9 * S, mix_c(CL.SCR3, HALO, 0.6), E=0.1 * glow, where=~p.mask(d)); p.fill(d, EYE, E=E)


def mix_c(a, b, k): return tuple(int(round(a[i] + (b[i] - a[i]) * k)) for i in range(3)) + (255,)


def _qmark(p, u, v, cx, cy, S, glow):
    E = 0.95 * glow
    d = union(arc(u, v, cx, cy - 2.2 * S, 2.4 * S, 180, 405, th=1.6 * S),
              seg(u, v, cx + 0.2 * S, cy + 0.2 * S, cx, cy + 1.6 * S, th=1.6 * S),
              circle(u, v, cx, cy + 4.0 * S, 0.95 * S))
    p.fill(d - 0.9 * S, mix_c(CL.SCR3, CL.HALO, 0.6), E=0.1 * glow, where=~p.mask(d)); p.fill(d, CL.EYE, E=E)


def _logo(p, u, v, cx, cy, S, k=1.0):
    """the Claude spark, redrawn as tapered rays (same silhouette as claude.LOGO)."""
    rays = [(-90, 5.2), (90, 5.2), (180, 5.2), (0, 5.2), (-135, 4.6), (-55, 4.0), (125, 4.0), (45, 4.8)]
    d = circle(u, v, cx, cy, 1.5 * S)
    for (a, L) in rays:
        ex, ey = cx + L * S * math.cos(math.radians(a)), cy + L * S * math.sin(math.radians(a))
        d = np.minimum(d, seg(u, v, cx, cy, ex, ey, th=1.05 * S) + 0.18 * np.hypot(u - cx, v - cy) / max(L * S, 1) * S)
    p.fill(d - 0.9 * S, CL.LOGO_D, E=0.25 * k, where=~p.mask(d))
    p.fill(d, CL.LOGO_O, E=0.6 * k)
    p.fill(np.maximum(d, circle(u, v, cx, cy, 3.0 * S)), CL.LOGO_C, E=0.85 * k)
    p.fill(circle(u, v, cx, cy, 1.1 * S), CL.LOGO_H, E=1.0 * k)


def claude_bust(S=3, face='normal', look=(0, 0), tilt=0.0, ant=(0.0, 0.0), led='online', led_k=1.0, glow=1.0,
                head_dy=0.0, spark_k=1.0, hands=None, light=KEY, screen_flash=0.0, badge=True, extra_h=0):
    """Claude from the chest up, drawn at S x the room sprite.  Sprite size (78 S, (76 S + extra_h)), anchor
    (.ax, .ay) = head top-centre like claude.draw().  hands: None | list of (x, y) hand centres in ROOM units
    relative to the sprite (e.g. typing).  screen_flash 0..1 lights the face screen (submit flash)."""
    W, H = int(78 * S), int(76 * S + extra_h)
    p = Painter(W, H)
    HX, HY, HW, HH = [k * S for k in (CL.HX, CL.HY, CL.HW, CL.HH)]
    SD = CL.SIDE * S
    AXp = (CL.AX) * S
    # ---------------------------------------------------------------- torso (behind the head)
    tx, ty, tw, th = [k * S for k in CL.torso_box()]
    th = th + 10 * S
    u, v = p.uv()
    for sgn in (-1, 1):                                                  # arm stubs hanging at the sides
        ax0 = tx + tw / 2 + sgn * (tw / 2 - 1.5 * S)
        p.part(seg(u, v, ax0, ty + 4 * S, ax0 + sgn * 3.0 * S, ty + 16 * S, th=6.0 * S), CORAL, bevel=2.6 * S, light=light, amb=0.22, ink=OUT)
    tm = p.part(rrect(u, v, tx, ty, tw, th, 6 * S), CORAL, bevel=6.0 * S, light=light, amb=0.22, ink=OUT)
    p.fill(inter(rrect(u, v, tx + 3 * S, ty, tw - 6 * S, 2.2 * S, 1.0 * S), tm.astype(np.float32) * -1 + 0.5), CL.TC_DK)
    if badge:
        cx = tx + tw / 2
        for sgn in (-1, 1):
            x0 = cx + sgn * (tw / 2 - 6 * S)
            d = seg(u, v, x0, ty + 0.5 * S, cx + sgn * 1.2 * S, ty + 6.4 * S, th=1.5 * S)
            p.part(d, LANY, bevel=0.8 * S, light=light, amb=0.4, outline=None)
            st = seg(u, v, x0, ty + 0.5 * S, cx + sgn * 1.2 * S, ty + 6.4 * S, th=0.35 * S)
            p.fill(st, LANY[3], where=((np.floor(u) + np.floor(v)) % 3 == 0))
        bm = p.part(rrect(u, v, cx - 3.6 * S, ty + 6 * S, 7.2 * S, 8.4 * S, 1.0 * S), [C('#9aa6b8'), C('#cfd6e0'), C('#f2f5f8'), C('#ffffff')],
                    bevel=1.0 * S, light=light, amb=0.5, ink=OUT)
        p.fill(rrect(u, v, cx - 2.8 * S, ty + 6.8 * S, 5.6 * S, 1.4 * S, 0.3 * S), CL.LAN_SH)
        p.fill(rrect(u, v, cx - 2.6 * S, ty + 9.0 * S, 2.4 * S, 2.6 * S, 0.4 * S), CL.TC)
        p.fill(rrect(u, v, cx + 0.2 * S, ty + 9.3 * S, 2.4 * S, 0.6 * S, 0.2 * S), C('#9aa6b8'))
        p.fill(rrect(u, v, cx + 0.2 * S, ty + 10.6 * S, 1.8 * S, 0.6 * S, 0.2 * S), C('#9aa6b8'))
        p.fill(rrect(u, v, cx - 2.6 * S, ty + 12.4 * S, 5.2 * S, 0.6 * S, 0.2 * S), C('#cfd6e0'))
    # ---------------------------------------------------------------- head (tilted about the neck)
    with p.frame(rot=tilt, cx=AXp, cy=HY + HH, dy=head_dy):
        u, v = p.uv()
        # antenna + logo
        sx, sy, sw, sh = [k * S for k in CL.SCREEN]
        ax = HX + sx + sw / 2
        tdx, tdy = ant[0] * S, ant[1] * S
        nx, ny = ax + tdx * 0.5, HY - 6 * S + tdy * 0.5
        stick = poly_stroke(u, v, [(ax, HY + 0.5 * S), (ax + tdx * 0.12, HY - 2 * S), (nx, ny)], th=1.25 * S)
        p.part(stick, METALR, bevel=0.6 * S, light=light, amb=0.45, ink=OUT)
        p.part(rrect(u, v, nx - 1.6 * S, ny - 1.1 * S, 3.2 * S, 2.2 * S, 0.9 * S), METALR, bevel=0.9 * S, light=light, amb=0.4, ink=OUT)
        p.part(rrect(u, v, ax - 2.4 * S, HY - 1.4 * S, 4.8 * S, 2.2 * S, 0.8 * S), METALR, bevel=0.8 * S, light=light, amb=0.35, ink=OUT)
        _logo(p, u, v, ax + tdx, HY - 7.5 * S - 5.5 * S + tdy, S, spark_k)
        # shell
        hd = rrect(u, v, HX, HY, HW, HH, 6.5 * S)
        hm = p.part(hd, SHELL, bevel=3.4 * S, light=light, amb=0.26, ink=OUT)
        side = hm & p.mask(u - (HX + SD))
        p.part(side, SIDE, bevel=2.6 * S, light=light, amb=0.30, normal=(-0.72, 0.0, 0.69), outline=None)
        p.edge(hm, ink=OUT)
        p.fill(inter(seg(u, v, HX + SD, HY + 4 * S, HX + SD, HY + HH - 4 * S, th=0.9 * S), hd), SHELL[2])
        p.fill(inter(seg(u, v, HX + SD + 0.8 * S, HY + 4 * S, HX + SD + 0.8 * S, HY + HH - 4 * S, th=0.5 * S), hd), SHELL[5])
        # panel screws + vent slits on the side panel
        for yy in (HY + 6 * S, HY + HH - 6 * S):
            p.part(circle(u, v, HX + 3.4 * S, yy, 0.75 * S), SIDE[:4], bevel=0.5 * S, light=light, amb=0.3, ink=SIDE[0])
        # ear hub (coral) with rings
        ex, ey = HX + 4.4 * S, HY + 16.5 * S
        p.part(ellipse(u, v, ex, ey, 3.7 * S, 4.4 * S), CORAL, bevel=1.6 * S, light=light, amb=0.3, normal=(-0.6, 0, 0.8), ink=OUT)
        p.fill(sub(ellipse(u, v, ex, ey, 2.5 * S, 3.1 * S), ellipse(u, v, ex, ey, 2.0 * S, 2.6 * S)), CL.TC_SH)
        p.part(ellipse(u, v, ex + 0.2 * S, ey, 1.3 * S, 1.6 * S), CORAL[:4], bevel=0.8 * S, light=light, amb=0.2, ink=CL.TC_OUT)
        p.fill(ellipse(u, v, ex - 1.4 * S, ey - 2.3 * S, 0.7 * S, 0.5 * S), CL.TC_HI)
        # bezel + screen
        bx, by = HX + sx, HY + sy
        p.part(rrect(u, v, bx - 1.2 * S, by - 1.2 * S, sw + 2.4 * S, sh + 2.4 * S, 3.6 * S), BEZ, bevel=1.1 * S,
               light=(0.3, 0.6, 0.75), amb=0.4, ink=SHELL[1])
        sd = rrect(u, v, bx, by, sw, sh, 3.0 * S)
        sm = p.fill(sd, CL.SCR)
        gy = np.clip((v - by) / sh, 0, 1)
        scr = np.stack([np.interp(gy, [0, 0.25, 1], [c0, c1, c2]) for c0, c1, c2 in
                        zip(CL.SCR3[:3], CL.SCR2[:3], CL.SCR[:3])], -1) / 255.0
        p.rgb[sm] = scr[sm]
        p.rgb[sm & (np.floor(v) % 2 == 0)] *= 0.93                                     # scanlines
        gl = sm & (np.abs((u - bx) + 0.55 * (v - by) - sw * 0.78) < 1.6 * S)          # gloss streak
        p.rgb[gl] = p.rgb[gl] * 0.8 + 0.2 * np.array([0.55, 0.55, 0.7])
        gl2 = sm & (np.abs((u - bx) + 0.55 * (v - by) - sw * 0.86) < 0.5 * S)
        p.rgb[gl2] = p.rgb[gl2] * 0.85 + 0.15 * np.array([0.6, 0.6, 0.75])
        if screen_flash > 0:
            p.rgb[sm] = p.rgb[sm] * (1 - 0.45 * screen_flash) + 0.45 * screen_flash * np.array([0.55, 0.95, 0.65])
            p.E[sm] = np.maximum(p.E[sm], 0.35 * screen_flash)
        # face
        lx, ly = look[0] * S, look[1] * S
        ecy = by + (CL.EYE_POS[1] + 4) * S + ly
        exl = bx + (CL.EYE_POS[0] + 3) * S + lx
        exr = bx + sw - (CL.EYE_POS[0] + 3) * S + lx
        if face == 'q':
            _qmark(p, u, v, bx + sw / 2 + lx, by + sh / 2 + ly - 0.5 * S, S, glow)
        elif face != 'off':
            _eye(p, u, v, face, exl, ecy, S, False, glow)
            _eye(p, u, v, face, exr, ecy, S, True, glow)
        p.rgb[sm] = np.minimum(p.rgb[sm], 1.0)
        # chin LED + chin seam
        lc = CL.LED.get(led, CL.LED['off'])
        ld = rrect(u, v, HX + HW - 9.5 * S, HY + HH - 4.4 * S, 2.6 * S, 1.3 * S, 0.6 * S)
        if led != 'off':
            p.fill(ld - 0.8 * S, mix_c(SHELL[3], lc, 0.35 * led_k), where=hm & ~p.mask(ld))
            p.fill(ld, mix_c(CL.LED['off'], lc, led_k), E=led_k)
        else:
            p.fill(ld, lc)
    # ---------------------------------------------------------------- hands (in front)
    if hands:
        for (hx, hy) in hands:
            u, v = p.uv()
            p.part(circle(u, v, hx * S, hy * S, 3.6 * S), HANDR, bevel=1.8 * S, light=light, amb=0.3, ink=CL.HAND_OUT)
    s = p.sprite()
    s.ax, s.ay = int(round(AXp)), int(round(HY))
    s.S = S
    return s


# ====================================================================== Wang Gong (human.WANG) close-up
SKIN = [C('#8a5446'), C('#b27560'), C('#d39878'), C('#e8b590'), C('#f3cba5'), C('#fbdcbc')]
HAIR = [C('#0e0c12'), C('#17141d'), C('#211d29'), C('#2d2937'), C('#3d394b'), C('#565269')]
HOOD = [C('#2c313d'), C('#434a59'), C('#596171'), C('#6c7584'), C('#808999'), C('#97a0ae')]
FRAME_C = C('#17141c')
INK_W = C('#3a2228')


def _spikes(cx, top, w, n, seed, up=True, base_y=None):
    rng = np.random.RandomState(seed)
    pts = []
    for i in range(n):
        x = cx - w / 2 + (i + 0.5) * w / n + rng.uniform(-0.15, 0.15) * w / n
        yield x, rng


def wang_bust(S=3, face='normal', look=(0, 0), tilt=0.0, mouth='flat', glint=1.0, head_dy=0.0, nod=0.0,
              hand=None, light=(-0.25, -0.35, 0.90), seed=3, shoulders_dy=0.0, pad_r=0):
    """Wang Gong from the chest up at S x the room sprite (head 30 x 27 -> 30S x 27S).  Sprite (70 S, 66 S),
    anchor (.ax, .ay) = head top-centre.  face: normal blink tired closed soft smile down.  mouth: flat | o | smile.
    nod 0..1 = looking down (features drop, hair covers more of the forehead).  hand: None | ('glasses', k) push-up
    | ('reach', k) towards the lower right (touching a frame on the desk), k 0..1."""
    W, H = int(70 * S) + int(pad_r), int(66 * S)
    p = Painter(W, H)
    cx = (W - int(pad_r)) / 2.0
    HY = 8.0 * S
    hw, hh = 30.0 * S, 27.0 * S
    hcy = HY + hh / 2
    neck_y = HY + hh - 2 * S
    u, v = p.uv()
    # ---------------------------------------------------------------- shoulders / hoodie
    sy = neck_y + 4 * S + shoulders_dy
    tor = union(rrect(u, v, cx - 25 * S, sy + 4 * S, 50 * S, H, 12 * S),
                ellipse(u, v, cx, sy + 10 * S, 22 * S, 9 * S))
    tm = p.part(tor, HOOD, bevel=7 * S, light=light, amb=0.25, ink=OUT)
    # folds
    for (x0, y0, x1, y1) in ((-15, 12, -11, 30), (16, 13, 12, 30), (-6, 24, -3, 36)):
        p.fill(inter(seg(u, v, cx + x0 * S, sy + y0 * S, cx + x1 * S, sy + y1 * S, th=0.7 * S), tor), HOOD[2], where=p.bayer < 0.3)
    # neck
    p.part(rrect(u, v, cx - 5.5 * S, neck_y - 3 * S, 11 * S, 10 * S, 3 * S), SKIN[:4], bevel=2 * S, light=light, amb=0.2, ink=INK_W)
    # hood rolled around the neck (a thick ring, open at the front)
    ring = sub(ellipse(u, v, cx, sy + 3.5 * S, 15 * S, 6.8 * S), ellipse(u, v, cx, sy + 2.2 * S, 7.5 * S, 3.8 * S))
    ring = sub(ring, rrect(u, v, cx - 3.2 * S, sy + 2 * S, 6.4 * S, 12 * S, 2 * S))
    p.part(ring, HOOD, bevel=3.0 * S, light=light, amb=0.3, ink=OUT, bias=0.06)
    # drawstrings + aglets
    for sgn in (-1, 1):
        x0 = cx + sgn * 3.8 * S
        d = poly_stroke(u, v, [(x0, sy + 6 * S), (x0 + sgn * 0.6 * S, sy + 12 * S), (x0 + sgn * 0.3 * S, sy + 17 * S)], th=1.1 * S)
        p.part(d, [C('#8f97a3'), C('#c9ced6'), C('#eef0f3')], bevel=0.5 * S, light=light, amb=0.4, ink=HOOD[0])
        p.part(rrect(u, v, x0 + sgn * 0.3 * S - 0.8 * S, sy + 16.5 * S, 1.6 * S, 2.6 * S, 0.5 * S), METALR, bevel=0.4 * S, light=light, amb=0.4, ink=OUT)
    # ---------------------------------------------------------------- head
    lx, ly = look[0] * S * 0.7, look[1] * S * 0.7
    fy = nod * 2.6 * S                                       # features drop when he looks down
    with p.frame(rot=tilt, cx=cx, cy=neck_y + 2 * S, dy=head_dy):
        u, v = p.uv()
        # ears
        for sgn in (-1, 1):
            exx = cx + sgn * (hw / 2 - 0.3 * S)
            ed = ellipse(u, v, exx, hcy + 1.5 * S + fy * 0.4, 2.6 * S, 3.6 * S)
            p.part(ed, SKIN, bevel=1.4 * S, light=light, amb=0.2, ink=INK_W, bias=-0.05)
            p.fill(ellipse(u, v, exx + sgn * 0.3 * S, hcy + 1.8 * S + fy * 0.4, 1.0 * S, 1.9 * S), SKIN[1])
        # skull / face
        hd = union(rrect(u, v, cx - hw / 2, HY, hw, hh, 11.5 * S), ellipse(u, v, cx, hcy + 3.5 * S, hw / 2 - 1.2 * S, hh / 2 - 1.0 * S))
        fm = p.part(hd, SKIN, bevel=5.5 * S, light=light, amb=0.30, ink=INK_W)
        # stubble (jaw) - ordered dots, denser at the chin
        jaw = fm & ~p.mask(ellipse(u, v, cx + lx * 0.5, hcy - 3.5 * S + fy, hw / 2 - 2.5 * S, hh / 2 - 1.5 * S))
        dots = jaw & (p.bayer < -0.18) & ~p.mask(rrect(u, v, cx - hw / 2, HY, hw, hh, 11.5 * S) + 1.0)
        p.tint(dots, C('#6a4a48'), 0.42)
        # cheeks
        if face in ('smile', 'soft'):
            for sgn in (-1, 1):
                ch = ellipse(u, v, cx + sgn * 8.8 * S + lx, hcy + 6.4 * S + fy + ly * 0.4, 2.8 * S, 1.4 * S)
                p.tint(fm & p.mask(ch) & (p.bayer < 0.2), C('#e8806e'), 0.45 if face == 'smile' else 0.3)
        # hair: cap + fringe + crown spikes  (polygon union, shaded as one volume)
        rng = np.random.RandomState(seed)
        cap = p.mask(ellipse(u, v, cx, HY + 8.0 * S, hw / 2 + 1.2 * S, 10.5 * S)) | p.mask(rrect(u, v, cx - hw / 2 - 1.0 * S, HY + 4 * S, hw + 2.0 * S, 7 * S + fy * 0.6, 3 * S))
        hairline = HY + 9.0 * S + fy * 0.8
        fr = np.zeros_like(cap)
        n = 9
        for i in range(n):
            x0 = cx - hw / 2 - 0.5 * S + i * (hw + 1 * S) / n
            x1 = x0 + (hw + 1 * S) / n
            L = (2.2 + rng.uniform(0, 2.4)) * S
            lean = rng.uniform(-1.2, 1.2) * S
            fr |= p.poly([(x0 - 0.4 * S, hairline - 1 * S), (x1 + 0.4 * S, hairline - 1 * S), ((x0 + x1) / 2 + lean, hairline + L)])
        for sgn in (-1, 1):                                  # side burns down past the ear top
            sx0 = cx + sgn * (hw / 2 + 0.6 * S)
            fr |= p.poly([(sx0, HY + 7 * S), (sx0 - sgn * 3.2 * S, HY + 7 * S), (sx0 - sgn * 1.6 * S, hcy + 0.5 * S + fy * 0.4), (sx0 - sgn * 0.2 * S, hcy - 1 * S)])
        cr = np.zeros_like(cap)
        tops = [(-11, 4.2, -34), (-6.0, 5.6, -14), (-1.0, 6.2, 2), (4.0, 5.8, 18), (9.0, 4.8, 34), (12.8, 3.2, 52), (-14, 2.8, -56)]
        for (dx, L, ang) in tops:
            bx = cx + dx * S
            by = HY + 2.5 * S + abs(dx) * 0.12 * S
            a = math.radians(ang - 90)
            tip = (bx + L * S * math.cos(a), by + L * S * math.sin(a))
            perp = (math.cos(a + math.pi / 2) * 3.4 * S, math.sin(a + math.pi / 2) * 3.4 * S)
            cr |= p.poly([(bx - perp[0], by - perp[1] + 2 * S), (bx + perp[0], by + perp[1] + 2 * S), tip])
        hm = cap | fr | cr
        hm &= ~(p.mask(rrect(u, v, cx - hw / 2 + 2.2 * S, hairline + 2.2 * S, hw - 4.4 * S, hh, 4 * S)) & ~fr)
        p.part(hm, HAIR, bevel=4.0 * S, light=light, amb=0.10, ink=OUT, bias=-0.16, dither=0.25)
        # sheen arc + strands
        sheen = hm & p.mask(arc(u, v, cx - 2 * S, HY + 14 * S, 11.5 * S, 215, 300, th=1.6 * S))
        p.tint(sheen & (p.bayer < 0.25), HAIR[4], 0.8)
        for (a0, a1, R) in ((215, 245, 9.5), (262, 292, 8.5), (238, 268, 12.5)):
            st = hm & p.mask(arc(u, v, cx, HY + 15 * S, R * S, a0, a1, th=0.45 * S)) & (p.bayer < 0.2)
            p.tint(st, HAIR[0], 0.6)
        # forehead shadow under the fringe
        fsh = fm & ~hm & p.mask(np.minimum(v - hairline - 3.2 * S, 0) * 0 + (v - (hairline + 3.0 * S)))
        p.tint(fsh & (v > hairline - 1 * S), SKIN[1], 0.35)
        # ---------------------------------------------------------------- face features
        ey = hcy + 3.4 * S + fy + ly
        exs = [cx - 6.6 * S + lx, cx + 6.6 * S + lx]
        # eyebrows
        for i, ex in enumerate(exs):
            sgn = -1 if i == 0 else 1
            # (inner end, middle, outer end) heights above the eye: inner higher = soft / sad, lower = cross
            hi_, mid_, lo_ = {'tired': (5.3, 5.0, 4.2), 'soft': (5.6, 5.4, 4.6), 'down': (5.6, 5.4, 4.6),
                              'smile': (5.4, 5.9, 5.0), 'closed': (5.0, 5.2, 4.6)}.get(face, (5.0, 5.5, 5.0))
            pts = [(ex - sgn * 3.4 * S, ey - hi_ * S), (ex, ey - mid_ * S), (ex + sgn * 3.2 * S, ey - lo_ * S)]
            p.fill(poly_stroke(u, v, pts, th=1.25 * S), HAIR[1], where=~hm | fr)
        # eyes (behind the lenses)
        for i, ex in enumerate(exs):
            sgn = -1 if i == 0 else 1
            if face in ('normal', 'tired', 'soft', 'down'):
                pdy = {'normal': 0.0, 'tired': 0.4, 'soft': 1.0, 'down': 1.3}[face] * S
                lid = {'normal': -1.9, 'tired': -0.6, 'soft': 0.0, 'down': 0.4}[face] * S
                p.fill(ellipse(u, v, ex, ey + 0.2 * S, 2.6 * S, 1.9 * S), C('#f4efe8'), where=v > ey + lid)
                pu = ellipse(u, v, ex + lx * 0.25 + 0.2 * S * (look[0] > 0) - 0.2 * S * (look[0] < 0), ey + 0.3 * S + pdy * 0.4, 1.35 * S, 1.75 * S)
                p.fill(pu, C('#2a1d1c'), where=(v > ey + lid) & p.mask(ellipse(u, v, ex, ey + 0.2 * S, 2.7 * S, 2.0 * S)))
                p.fill(circle(u, v, ex + lx * 0.25 - 0.45 * S, ey - 0.35 * S + pdy * 0.4, 0.45 * S), C('#ffffff'), where=v > ey + lid)
                p.fill(seg(u, v, ex - 2.8 * S, ey + lid, ex + 2.8 * S, ey + lid - 0.2 * S, th=0.95 * S), INK_W)   # upper lid line
                if face in ('tired',):
                    p.tint(fm & p.mask(arc(u, v, ex, ey + 0.6 * S, 2.9 * S, 30, 150, th=0.8 * S)), C('#8a5a6a'), 0.45)
                if face in ('soft', 'down'):
                    p.fill(seg(u, v, ex - 2.2 * S, ey + 1.9 * S, ex + 2.2 * S, ey + 1.9 * S, th=0.5 * S), SKIN[2])
            elif face == 'blink':
                p.fill(arc(u, v, ex, ey - 1.2 * S, 2.8 * S, 40, 140, th=0.9 * S), INK_W)
            elif face == 'closed':
                p.fill(arc(u, v, ex, ey - 1.6 * S, 2.8 * S, 30, 150, th=1.0 * S), INK_W)
                p.tint(fm & p.mask(arc(u, v, ex, ey + 0.8 * S, 3.0 * S, 30, 150, th=0.8 * S)), C('#8a5a6a'), 0.4)
            elif face == 'smile':
                p.fill(arc(u, v, ex, ey + 1.6 * S, 2.6 * S, 205, 335, th=1.0 * S), INK_W)
        # nose
        nx_, ny_ = cx + lx * 1.1, hcy + 7.0 * S + fy + ly * 0.8
        p.tint(fm & p.mask(ellipse(u, v, nx_ + 0.9 * S, ny_ + 0.6 * S, 1.0 * S, 0.6 * S)), SKIN[1], 0.45)
        p.fill(circle(u, v, nx_ - 0.4 * S, ny_ - 0.4 * S, 0.45 * S), SKIN[5])
        # mouth
        my = hcy + 9.8 * S + fy * 0.9 + ly * 0.6
        mx = cx + lx * 0.9
        if mouth == 'o':
            p.fill(ellipse(u, v, mx, my, 1.3 * S, 1.1 * S), C('#5a2a2c')); p.fill(ellipse(u, v, mx, my + 0.6 * S, 0.8 * S, 0.4 * S), C('#b0565a'))
        elif mouth == 'smile' or face == 'smile':
            p.fill(arc(u, v, mx, my - 2.2 * S, 2.8 * S, 55, 125, th=0.9 * S), INK_W)
        else:
            p.fill(seg(u, v, mx - 1.6 * S, my, mx + 1.4 * S, my + 0.15 * S, th=0.8 * S), C('#6a3a38'))
        # glasses: thick square frames, lenses catch the laptop light
        gw, gh = 9.4 * S, 6.8 * S
        gy0 = ey - gh / 2 + 0.2 * S
        for i, ex in enumerate(exs):
            outer = rrect(u, v, ex - gw / 2, gy0, gw, gh, 1.6 * S)
            inner = rrect(u, v, ex - gw / 2 + 1.15 * S, gy0 + 1.15 * S, gw - 2.3 * S, gh - 2.3 * S, 0.9 * S)
            lens = p.mask(inner)
            p.tint(lens, C('#cfe4ff'), 0.10)
            dd = (u - ex) + 0.9 * (v - gy0)
            g = lens & (np.abs(dd - 4.6 * S) < 0.5 * S) & (v < gy0 + 3.4 * S)
            g |= lens & (np.abs(dd - 6.2 * S) < 0.28 * S) & (v < gy0 + 3.0 * S)
            if glint > 0:
                p.rgb[g] = p.rgb[g] * (1 - 0.6 * glint) + 0.6 * glint * np.array([0.82, 0.92, 1.0])
                p.E[g] = np.maximum(p.E[g], 0.35 * glint)
            fmask = p.mask(outer) & ~lens
            p.fill(fmask, FRAME_C)
            p.fill(fmask & p.mask(v - (gy0 + 0.5 * S)) & ~p.mask(v - (gy0 - 0.2 * S)) , C('#3a3644'))
        p.fill(seg(u, v, exs[0] + gw / 2 - 0.2 * S, gy0 + 1.6 * S, exs[1] - gw / 2 + 0.2 * S, gy0 + 1.6 * S, th=1.0 * S), FRAME_C)
        for sgn in (-1, 1):                                   # temples to the ears
            ex = exs[0] if sgn < 0 else exs[1]
            p.fill(seg(u, v, ex + sgn * gw / 2, gy0 + 1.4 * S, cx + sgn * (hw / 2 - 0.5 * S), gy0 + 2.4 * S, th=0.9 * S), FRAME_C, where=~hm)
    # ---------------------------------------------------------------- hand
    if hand is not None:
        kind, k = hand[0], hand[1]
        u, v = p.uv()
        if kind == 'glasses':
            hx0, hy0 = cx + 9 * S, H + 6 * S
            hx1, hy1 = cx + 1.2 * S + look[0] * S * 0.7, HY + 13 * S + look[1] * S * 0.7
        else:
            hx0, hy0 = cx + 22 * S, H + 4 * S
            hx1, hy1 = hand[2] if len(hand) > 2 else (cx + 30 * S, H - 6 * S)
        hx, hy = hx0 + (hx1 - hx0) * k, hy0 + (hy1 - hy0) * k
        if kind == 'glasses':
            p.part(seg(u, v, hx0 + 3 * S, H + 14 * S, hx + 1.0 * S, hy + 5.0 * S, th=8.0 * S), HOOD, bevel=3.5 * S, light=light, amb=0.25, ink=OUT)
            p.part(rrect(u, v, hx - 2.4 * S, hy - 1.6 * S, 5.0 * S, 6.0 * S, 2.2 * S), SKIN, bevel=1.8 * S, light=light, amb=0.3, ink=INK_W)
            p.part(rrect(u, v, hx - 0.6 * S, hy - 4.6 * S, 1.8 * S, 4.6 * S, 0.9 * S), SKIN, bevel=0.8 * S, light=light, amb=0.3, ink=INK_W)
        else:                                   # fingertips resting on the frame's edge (hand points right)
            p.part(seg(u, v, hx - 9 * S, H + 10 * S, hx - 3.0 * S, hy + 1.5 * S, th=7.5 * S), HOOD, bevel=3.2 * S, light=light, amb=0.25, ink=OUT)
            p.part(rrect(u, v, hx - 5.5 * S, hy - 0.8 * S, 4.6 * S, 4.6 * S, 1.6 * S), HOOD[1:], bevel=1.2 * S, light=light, amb=0.3, ink=OUT)
            hand_d = union(rrect(u, v, hx - 2.2 * S, hy - 1.4 * S, 6.2 * S, 4.2 * S, 1.8 * S),
                           rrect(u, v, hx - 1.4 * S, hy - 3.0 * S, 2.0 * S, 3.0 * S, 0.9 * S))
            p.part(hand_d, SKIN, bevel=1.4 * S, light=light, amb=0.3, ink=INK_W)
            for j in range(3):
                p.fill(seg(u, v, hx + 1.4 * S, hy - 0.2 * S + j * 1.1 * S, hx + 3.6 * S, hy - 0.2 * S + j * 1.1 * S, th=0.35 * S), SKIN[1])
    s = p.sprite()
    s.ax, s.ay = int(round(cx)), int(round(HY))
    s.S = S
    return s
