"""pixelkit.characters.claude - Claude, the office robot (reference-faithful design).

White rounded CRT-like head, dark screen face with two big warm-cream LED eyes (emissive),
tiny antenna with an orange spark, call-centre headset, coral body, round white hands, blue
lanyard + badge, and a status LED on the chin (online / away / busy / off).

    from pixelkit.characters import claude
    parts = claude.draw(face='happy', arms='type', phase=1, led='online')
    layer.put(parts.body.rgba, x - parts.ax, y - parts.ay, Z=345, E=parts.body.E)   # behind the desk
    ...draw desk...
    layer.put(parts.hands.rgba, x - parts.ax, y - parts.ay, Z=330, E=parts.hands.E) # in front of it
(x, y) = the world position of the head's top-centre.
"""
import math
from types import SimpleNamespace
import numpy as np
from ..core import Canvas, C, mix, scale_nearest
from ..scene import Sprite

SW, SH = 72, 74                 # sprite size
HX, HY, HW, HH = 19, 12, 34, 28  # head box inside the sprite
AX, AY = HX + HW // 2, HY        # anchor = head top-centre

OUT = C('#3b3042'); SH2 = C('#a59cb4'); SH1 = C('#cbc3d0'); BASE = C('#ebe5dd'); HI = C('#faf6ef'); HI2 = C('#ffffff')
SCR = C('#1d1a2a'); SCR2 = C('#29243b'); SCR3 = C('#3a3350'); BEZ = C('#d3cbc8')
EYE = C('#ffe2b8'); EYE_HI = C('#fff7ea'); EYE_LO = C('#f1c08c'); EYE_DIM = C('#b88a6a')
TC_HI = C('#f2a296'); TC = C('#d8776e'); TC_SH = C('#b0555a'); TC_DK = C('#843a48'); TC_OUT = C('#48223a')
HAND = C('#f4f0ea'); HAND_SH = C('#c9c1cc'); HAND_OUT = C('#4a3a48')
HS = C('#34313f'); HS_HI = C('#5c5869'); HS_MIC = C('#e0603e')
LAN = C('#3d6fd8'); LAN_SH = C('#2a4f9e'); CARD = C('#ffffff'); CARD_SH = C('#cfd6e0')
METAL = C('#bdb5ab'); SPARK = C('#ff9a52'); SPARK_HI = C('#ffe4c4')
LED = {'online': C('#5dff8f'), 'away': C('#ffc04a'), 'busy': C('#ff5a4a'), 'off': C('#3a4a40')}

# eye glyphs: '#' = eye, 'h' = hot highlight, 'l' = lower (darker) row
EYES = {
    'normal': [".hh##.", "#hh###", "#h####", "######", "######", "######", "llllll", ".llll."],
    'wide':   [".hh###.", "#hh####", "#h#####", "#######", "#######", "#######", "#######", "lllllll", ".lllll."],
    'blink':  ["......", "......", "......", "......", "......", ".####.", "llllll", "......"],
    'half':   ["......", "......", "......", "######", "#h####", "######", "llllll", ".llll."],
    'closed': ["......", "......", "......", "......", "......", "#....#", ".####.", "......"],
    'happy':  ["......", "......", ".####.", "######", "##..##", "#....#", "......", "......"],
    'focus':  ["......", "......", "######", "#h####", "######", "######", "llllll", "......"],
    'sadL':   ["......", "###...", "#h###.", "######", "######", "######", "llllll", ".llll."],
    'dizzyL': ["#.....", "##....", ".###..", "...###", ".###..", "##....", "#.....", "......"],
    'heart':  [".#..#.", "######", "######", ".####.", "..##..", "......", "......", "......"],
}
QMARK = [".####.", "##..##", "....##", "...##.", "..##..", "......", "..##..", "......"]
EYE_POS = (6, 5)     # left eye top-left inside the screen; right eye mirrored
SCREEN = (4, 4, 26, 18)

def _glyph(cv, E, g, x, y, mirror=False, glow=1.0):
    cols = {'#': EYE, 'h': EYE_HI, 'l': EYE_LO}
    for j, row in enumerate(g):
        r = row[::-1] if mirror else row
        for i, ch in enumerate(r):
            if ch in cols:
                cv.px(x + i, y + j, cols[ch] if glow > 0.5 else EYE_DIM)
                if 0 <= y + j < E.shape[0] and 0 <= x + i < E.shape[1]: E[y + j, x + i] = glow

def draw_face(cv, E, face='normal', look=(0, 0), glow=1.0):
    sx, sy, sw, sh = SCREEN
    ox, oy = HX + sx, HY + sy
    lx, ly = look
    if face == 'off': return
    if face == 'q':
        _glyph(cv, E, QMARK, ox + 10 + lx, oy + 5 + ly, glow=glow); return
    if face == 'dizzy':
        _glyph(cv, E, EYES['dizzyL'], ox + EYE_POS[0] + lx, oy + EYE_POS[1] + ly, glow=glow)
        _glyph(cv, E, EYES['dizzyL'], ox + sw - EYE_POS[0] - 6 + lx, oy + EYE_POS[1] + ly, mirror=True, glow=glow); return
    if face == 'sad':
        _glyph(cv, E, EYES['sadL'], ox + EYE_POS[0] + lx, oy + EYE_POS[1] + ly, mirror=True, glow=glow)
        _glyph(cv, E, EYES['sadL'], ox + sw - EYE_POS[0] - 6 + lx, oy + EYE_POS[1] + ly, glow=glow); return
    g = EYES.get(face, EYES['normal'])
    w = len(g[0]); dx = (6 - w) // 2 if w <= 6 else -(w - 6 + 1) // 2
    dy = -1 if face == 'wide' else 0
    _glyph(cv, E, g, ox + EYE_POS[0] + dx + lx, oy + EYE_POS[1] + dy + ly, glow=glow)
    _glyph(cv, E, g, ox + sw - EYE_POS[0] - 6 + (6 - w - dx) + lx, oy + EYE_POS[1] + dy + ly, mirror=True, glow=glow)

def draw_head(cv, E, face='normal', look=(0, 0), led='online', led_k=1.0, glow=1.0, spark_k=1.0, headset=True):
    x, y, w, h = HX, HY, HW, HH
    ax = x + w // 2
    # antenna + spark
    cv.vline(ax, y - 4, 4, METAL); cv.px(ax - 1, y - 1, METAL); cv.px(ax + 1, y - 1, METAL)
    for (dx, dy, c) in [(0, -7, SPARK), (-1, -6, SPARK), (1, -6, SPARK), (0, -6, SPARK_HI), (0, -5, SPARK), (-2, -6, SPARK), (2, -6, SPARK), (0, -8, SPARK)]:
        cv.px(ax + dx, y + dy, c); E[y + dy, ax + dx] = 0.85 * spark_k
    # headset band (behind the shell top)
    if headset:
        cv.hline(x + 5, y - 2, w - 10, HS); cv.hline(x + 7, y - 2, 5, HS_HI)
        cv.px(x + 4, y - 1, HS); cv.px(x + w - 5, y - 1, HS); cv.px(x + 3, y, HS); cv.px(x + w - 4, y, HS)
    # shell
    cv.rrect(x, y, w, h, OUT, 6)
    cv.rrect(x + 1, y + 1, w - 2, h - 2, BASE, 5)
    # form shading: lower/right in lavender shade, top-left highlight
    cv.rect(x + w - 4, y + 4, 2, h - 8, SH1); cv.vline(x + w - 2, y + 5, h - 10, SH2)
    cv.rect(x + 4, y + h - 4, w - 8, 2, SH1); cv.hline(x + 5, y + h - 2, w - 10, SH2)
    cv.px(x + w - 3, y + h - 3, SH2); cv.px(x + w - 4, y + h - 3, SH1); cv.px(x + w - 3, y + h - 4, SH1)
    cv.hline(x + 5, y + 1, w - 12, HI2); cv.hline(x + 3, y + 2, w - 9, HI); cv.vline(x + 1, y + 5, h - 12, HI); cv.vline(x + 2, y + 3, 3, HI)
    # screen bezel + screen
    sx, sy, sw, sh = SCREEN
    cv.rrect(x + sx - 1, y + sy - 1, sw + 2, sh + 2, BEZ, 4)
    cv.rrect(x + sx, y + sy, sw, sh, SCR, 3)
    cv.hline(x + sx + 3, y + sy, sw - 6, SCR3); cv.hline(x + sx + 2, y + sy + 1, sw - 4, SCR2); cv.hline(x + sx + 1, y + sy + 2, sw - 2, SCR2)
    # glass glint
    cv.px(x + sx + sw - 4, y + sy + 2, SCR3); cv.px(x + sx + sw - 3, y + sy + 3, SCR3); cv.px(x + sx + sw - 3, y + sy + 4, SCR2)
    draw_face(cv, E, face, look, glow)
    # status LED (chin, right) + vents (left)
    lc = LED.get(led, LED['off'])
    if led != 'off':
        lc2 = mix(LED['off'], lc, max(0.0, min(1.0, led_k)))
        cv.rect(x + w - 8, y + h - 5, 2, 2, lc2); E[y + h - 5:y + h - 3, x + w - 8:x + w - 6] = led_k
    else:
        cv.rect(x + w - 8, y + h - 5, 2, 2, lc)
    for k in range(3): cv.hline(x + 5, y + h - 6 + k * 0 + (k - 1) * 0, 0, SH1)
    cv.hline(x + 6, y + h - 5, 4, SH1); cv.hline(x + 6, y + h - 4, 4, HI)
    # headset cups + mic
    if headset:
        for ex in (x - 3, x + w - 1):
            cv.rrect(ex, y + 8, 4, 12, OUT, 1); cv.rect(ex + 1, y + 9, 2, 10, HS); cv.vline(ex + 1, y + 10, 4, HS_HI)
        cv.px(x - 1, y + 20, HS); cv.px(x - 1, y + 21, HS); cv.px(x, y + 22, HS); cv.px(x + 1, y + 23, HS); cv.hline(x + 2, y + 24, 3, HS)
        cv.rect(x + 5, y + 23, 3, 2, HS_MIC); cv.px(x + 5, y + 23, C('#ff9a7a'))

def draw_torso(cv, E, badge=True):
    x, y = HX + 4, HY + HH - 1
    w, h = HW - 8, 26
    cv.rrect(x, y, w, h, TC_OUT, 5)
    cv.rrect(x + 1, y + 1, w - 2, h - 1, TC, 4)
    cv.rect(x + w - 5, y + 4, 3, h - 5, TC_SH); cv.vline(x + w - 2, y + 5, h - 6, TC_DK)
    cv.hline(x + 5, y + 1, w - 10, TC_HI); cv.vline(x + 1, y + 5, 8, TC_HI); cv.vline(x + 2, y + 3, 2, TC_HI)
    cv.rect(x + 7, y, w - 14, 2, TC_DK)                  # neck shadow
    if badge:
        cx = x + w // 2
        cv.line(x + 6, y + 1, cx - 1, y + 9, LAN); cv.line(x + w - 7, y + 1, cx + 1, y + 9, LAN)
        cv.line(x + 7, y + 1, cx, y + 8, LAN_SH)
        cv.rect(cx - 4, y + 9, 9, 11, TC_OUT); cv.rect(cx - 3, y + 10, 7, 9, CARD)
        cv.rect(cx - 3, y + 10, 7, 2, TC); cv.rect(cx - 2, y + 13, 3, 3, SH1); cv.hline(cx - 2, y + 17, 5, CARD_SH); cv.hline(cx + 2, y + 14, 2, CARD_SH)

def _hand(cv, x, y, big=False):
    w, h = (7, 6) if big else (6, 5)
    cv.rrect(x, y, w, h, HAND_OUT, 2); cv.rrect(x + 1, y + 1, w - 2, h - 2, HAND, 1)
    cv.hline(x + 2, y + h - 2, w - 3, HAND_SH); cv.px(x + 1, y + 1, HI2)

def _sleeve(cv, pts, width=4):
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(n + 1):
            xx = x0 + (x1 - x0) * i / n; yy = y0 + (y1 - y0) * i / n
            cv.rect(int(round(xx - width / 2)), int(round(yy - width / 2)), width, width, TC_OUT)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(n + 1):
            xx = x0 + (x1 - x0) * i / n; yy = y0 + (y1 - y0) * i / n
            cv.rect(int(round(xx - width / 2 + 1)), int(round(yy - width / 2 + 1)), width - 2, width - 2, TC_SH)

def draw_arms(cv, E, arms='rest', phase=0, desk_y=None):
    """arms + hands. desk_y: sprite y of the desk top (hands rest just below it)."""
    bx, by = HX + 4, HY + HH - 1
    bw = HW - 8
    dy = (desk_y if desk_y is not None else by + 24)
    L, Rr = bx + 1, bx + bw - 2
    if arms in ('rest', 'type'):
        up = (phase % 2) if arms == 'type' else 0
        upR = ((phase + 1) % 2) if arms == 'type' else 0
        inset = 3 if arms == 'type' else 0
        _sleeve(cv, [(L, by + 6), (L - 3, by + 14), (L + inset - 1, dy + 1 - up)], 5)
        _sleeve(cv, [(Rr, by + 6), (Rr + 3, by + 14), (Rr - inset + 1, dy + 1 - upR)], 5)
        _hand(cv, L + inset - 4, dy - up); _hand(cv, Rr - inset - 2, dy - upR)
    elif arms == 'up':
        _sleeve(cv, [(L, by + 5), (L - 6, by - 2), (L - 8, by - 9)], 5)
        _sleeve(cv, [(Rr, by + 5), (Rr + 6, by - 2), (Rr + 8, by - 9)], 5)
        _hand(cv, L - 11, by - 15, True); _hand(cv, Rr + 5, by - 15, True)
    elif arms == 'shrug':
        _sleeve(cv, [(L, by + 6), (L - 6, by + 9), (L - 9, by + 4)], 5)
        _sleeve(cv, [(Rr, by + 6), (Rr + 6, by + 9), (Rr + 9, by + 4)], 5)
        _hand(cv, L - 12, by, True); _hand(cv, Rr + 6, by, True)
    elif arms == 'wave':
        _sleeve(cv, [(L, by + 6), (L - 3, by + 14), (L - 1, dy + 1)], 5)
        _hand(cv, L - 4, dy)
        a = 0.35 * math.sin(phase * 1.3)
        _sleeve(cv, [(Rr, by + 5), (Rr + 6, by - 1), (Rr + 8 + int(round(a * 4)), by - 9)], 5)
        _hand(cv, Rr + 5 + int(round(a * 4)), by - 15, True)
    elif arms == 'hold':
        _sleeve(cv, [(L, by + 6), (L - 2, by + 13), (L + 6, by + 16)], 5)
        _sleeve(cv, [(Rr, by + 6), (Rr + 2, by + 13), (Rr - 6, by + 16)], 5)
        _hand(cv, L + 4, by + 13); _hand(cv, Rr - 9, by + 13)
    elif arms == 'down':
        _sleeve(cv, [(L, by + 6), (L - 3, by + 20)], 5); _sleeve(cv, [(Rr, by + 6), (Rr + 3, by + 20)], 5)
        _hand(cv, L - 6, by + 20); _hand(cv, Rr, by + 20)

def draw(face='normal', arms='rest', phase=0, led='online', led_k=1.0, look=(0, 0), glow=1.0, desk_y=None,
         squash=0.0, spark_k=1.0, headset=True, badge=True):
    """returns SimpleNamespace(body=Sprite, hands=Sprite, ax, ay) - sprites share coordinates."""
    body = Sprite(SW, SH); hands = Sprite(SW, SH)
    draw_torso(body.cv, body.E, badge)
    draw_head(body.cv, body.E, face, look, led, led_k, glow, spark_k, headset)
    draw_arms(hands.cv, hands.E, arms, phase, desk_y)
    ax, ay = AX, AY
    if abs(squash) > 1e-3:
        sx = 1.0 + squash * 0.6; sy = 1.0 - squash
        for sp in (body, hands):
            rgba = scale_nearest(sp.cv.a, sx, sy); E = scale_nearest(sp.E, sx, sy)
            sp.cv = Canvas(rgba.shape[1], rgba.shape[0]); sp.cv.a = rgba; sp.E = E
        nh, nw = body.cv.a.shape[:2]
        # keep the bottom-centre fixed
        ax = AX * sx; ay = SH - (SH - AY) * sy
        ax = AX * nw / SW; ay = nh - (SH - AY) * nh / SH
    return SimpleNamespace(body=body, hands=hands, ax=ax, ay=ay)

def sheet(path, faces=('normal', 'blink', 'closed', 'wide', 'happy', 'dizzy', 'q', 'sad', 'half', 'focus', 'heart'),
          scale=4, bg=(70, 62, 86)):
    """expression sheet for review."""
    import cv2
    tiles = []
    for i, f in enumerate(faces):
        p = draw(face=f, arms=['rest', 'type', 'up', 'shrug', 'wave', 'hold'][i % 6], phase=i)
        a = p.body.cv.a.copy(); h = p.hands.cv.a; m = h[..., 3] > 0; a[m] = h[m]
        img = np.zeros((SH, SW, 3), np.uint8) + np.array(bg, np.uint8)
        al = a[..., 3:4] / 255.0
        img = (img * (1 - al) + a[..., :3] * al).astype(np.uint8)
        tiles.append(cv2.resize(img, (SW * scale, SH * scale), interpolation=cv2.INTER_NEAREST))
    rows = [np.concatenate(tiles[i:i + 6] + [np.zeros_like(tiles[0])] * (6 - len(tiles[i:i + 6])), 1) for i in range(0, len(tiles), 6)]
    cv2.imwrite(path, np.concatenate(rows, 0)[..., ::-1])
