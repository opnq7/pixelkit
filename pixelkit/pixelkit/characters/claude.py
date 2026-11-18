"""pixelkit.characters.claude - Claude, the office robot (chibi v2, matched to the reference).

Proportions: WIDE head (44x32, ~1.4:1, 3/4 view with a side panel + coral ear hub) on a SHORT body
(24x15 torso + stubby legs), head ~ 60% of the height.  Dark screen face with two big oval cream eyes
(peach lower third, dark warm halo), gold antenna topped with the pixel Claude logo (LOGO / draw_logo), coral body, big round white
hands, blue lanyard + badge, status LED on the chin.  Old lanky design: characters/claude_v1.py.

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

SW, SH = 78, 76                 # sprite size
HX, HY, HW, HH = 17, 18, 44, 32  # head box inside the sprite (chibi v2: wide head, short body)
AX, AY = HX + HW // 2, HY        # anchor = head top-centre
SIDE = 9                         # 3/4 view: left side panel width (the head's thickness)

OUT = C('#3b3042'); SH2 = C('#a59cb4'); SH1 = C('#cbc3d0'); BASE = C('#ebe5dd'); HI = C('#faf6ef'); HI2 = C('#ffffff')
SIDE1 = C('#ddd4cf'); SIDE2 = C('#bfb3b8')
SCR = C('#1a1726'); SCR2 = C('#262236'); SCR3 = C('#38324c'); BEZ = C('#d3cbc8')
EYE = C('#ffe6c4'); EYE_HI = C('#fff8ee'); EYE_LO = C('#f4b48c'); EYE_DIM = C('#b88a6a'); HALO = C('#5f3c3e')
TC_HI = C('#f2a296'); TC = C('#d8776e'); TC_SH = C('#b0555a'); TC_DK = C('#843a48'); TC_OUT = C('#48223a')
FOOT = C('#f0a08e')
HAND = C('#f6f2ec'); HAND_SH = C('#c9c1cc'); HAND_OUT = C('#4a3a48')
HS = C('#34313f'); HS_HI = C('#5c5869'); HS_MIC = C('#e0603e')
LAN = C('#3d6fd8'); LAN_SH = C('#2a4f9e'); CARD = C('#ffffff'); CARD_SH = C('#cfd6e0')
METAL = C('#d9a64e'); METAL_D = C('#9a6a2a'); SPARK = C('#ff9a52'); SPARK_HI = C('#ffe4c4')
LED = {'online': C('#5dff8f'), 'away': C('#ffc04a'), 'busy': C('#ff5a4a'), 'off': C('#3a4a40')}

# eye glyphs (6 wide): '#' = eye, 'h' = hot highlight, 'l' = lower peach.  Every lit pixel gets a dark warm halo.
EYES = {
    'normal': [".####.", "#hh###", "#h####", "######", "######", "######", "llllll", ".llll."],
    'wide':   [".####.", "#hh###", "#h####", "######", "######", "######", "######", "llllll", ".llll."],
    'blink':  ["......", "......", "......", "......", "......", ".####.", "llllll", "......"],
    'half':   ["......", "......", "......", "######", "#h####", "######", "llllll", ".llll."],
    'closed': ["......", "......", "......", "......", "......", "#....#", ".####.", "......"],
    'happy':  ["......", "......", ".####.", "######", "##..##", "#....#", "......", "......"],
    'focus':  ["......", "......", ".####.", "#h####", "######", "######", ".llll.", "......"],
    'sadL':   ["......", "###...", "#h###.", "######", "######", "######", "llllll", ".llll."],
    'dizzyL': ["#.....", "##....", ".###..", "...###", ".###..", "##....", "#.....", "......"],
    'heart':  [".#..#.", "######", "######", ".####.", "..##..", "......", "......", "......"],
    # v0.7 performance eyes
    'blink1': ["......", "......", "......", "......", "......", "######", "llllll", ".llll."],   # lid 3/4 down (blink in-between)
    'sparkle':[".####.", "#hh###", "#hh#h#", "####hh", "#####h", "######", "llllll", ".llll."],   # excited, extra glints
    'star':   ["..##..", "..##..", "######", ".####.", ".#hh#.", "##..##", "#....#", "......"],   # star eyes (big idea!)
    'squint': ["......", "......", "......", ".####.", "######", "#....#", "......", "......"],   # warm squint smile
    'droopL': ["......", "......", "......", "###...", "#h###.", "######", "llllll", ".llll."],   # tired / let down (outer lid low)
    'wideL':  ["..##..", ".####.", "#hh###", "#h####", "######", "######", "######", "llllll", ".llll."],  # surprised, taller
}
QMARK = [".####.", "##..##", "....##", "...##.", "..##..", "......", "..##..", "......"]
SCREEN = (12, 6, 28, 21)    # x, y, w, h inside the head box (front plate, right of the side panel)
EYE_POS = (6, 6)            # left eye top-left inside the screen; right eye mirrored

# Claude logo (pixel spark) used as the antenna topper.  'h' hot centre, 'o' main, 'd' darker tips.
LOGO = [".....d.....",
        ".d...o.....",
        "..o..o..d..",
        "...o.o.o...",
        "....ooo....",
        "doooohooood",
        "....ooo....",
        "...o.o.o...",
        "..d..o..o..",
        ".....o...d.",
        ".....d....."]
LOGO_O = C('#d97757'); LOGO_H = C('#ffd2b4'); LOGO_D = C('#b5583c'); LOGO_C = C('#f0956c')

def draw_logo(cv, E, cx, cy, k=1.0, glyph=None):
    """pixel Claude spark centred at (cx, cy); k = glow (emissive) strength."""
    g = glyph or LOGO
    n = len(g); r = n // 2
    for j, row in enumerate(g):
        for i, ch in enumerate(row):
            if ch == '.': continue
            x, y = cx - r + i, cy - r + j
            near = abs(i - r) <= 1 and abs(j - r) <= 1
            col = {'h': LOGO_H, 'o': LOGO_C if near else LOGO_O, 'd': LOGO_D}[ch]
            cv.px(x, y, col)
            if 0 <= y < E.shape[0] and 0 <= x < E.shape[1]:
                E[y, x] = k * (1.0 if ch == 'h' else 0.8 if near else 0.55 if ch == 'o' else 0.35)

def _glyph(cv, E, g, x, y, mirror=False, glow=1.0, halo=True):
    cols = {'#': EYE, 'h': EYE_HI, 'l': EYE_LO}
    pts = []
    for j, row in enumerate(g):
        r = row[::-1] if mirror else row
        for i, ch in enumerate(r):
            if ch in cols: pts.append((x + i, y + j, cols[ch]))
    if halo and glow > 0.5:
        lit = {(px, py) for px, py, _ in pts}
        for px, py, _ in pts:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (px + dx, py + dy)
                if q not in lit:
                    cv.px(q[0], q[1], HALO)
                    if 0 <= q[1] < E.shape[0] and 0 <= q[0] < E.shape[1]: E[q[1], q[0]] = max(E[q[1], q[0]], 0.12 * glow)
    for px, py, c in pts:
        cv.px(px, py, c if glow > 0.5 else EYE_DIM)
        if 0 <= py < E.shape[0] and 0 <= px < E.shape[1]: E[py, px] = glow

MAP_D = C('#1f5470'); MAP_M = C('#3f9fc8'); MAP_L = C('#9fe8ff'); MAP_W = C('#eafcff'); MAP_PIN = C('#ff6a5a')

def _map_icon(cv, E, x, y, glow=1.0):
    """'planning mode' face: a glowing folded 3-panel map with a dotted route and a red pin (17 x 13)."""
    for p in range(3):                                   # panels, the middle one dips 1px (fold)
        px_, py_ = x + p * 6, y + (1 if p == 1 else 0)
        cv.rect(px_, py_, 6, 11, MAP_L); cv.rect(px_ + 1, py_ + 1, 4, 9, MAP_D if p != 1 else MAP_M)
        for yy in range(py_ + 1, py_ + 10):
            for xx in range(px_, px_ + 6): E[yy, xx] = max(E[yy, xx], 0.35 * glow)
    route = [(2, 8), (3, 7), (4, 6), (6, 6), (7, 5), (8, 4), (10, 5), (11, 6), (12, 5), (13, 4)]
    for i, (dx, dy) in enumerate(route):
        if i % 2 == 0: cv.px(x + dx, y + dy, MAP_W); E[y + dy, x + dx] = glow
    cv.rect(x + 13, y + 1, 3, 3, MAP_PIN); cv.px(x + 14, y + 4, MAP_PIN); cv.px(x + 14, y + 2, MAP_W)
    E[y + 1:y + 5, x + 13:x + 16] = glow

# v0.7: tiny 3x5 pixel font for text on the face screen (face='txt:40×52/=2080', '/' = new line, max ~6 chars a line)
DIG35 = {'0': ['###', '#.#', '#.#', '#.#', '###'], '1': ['.#.', '##.', '.#.', '.#.', '###'], '2': ['###', '..#', '###', '#..', '###'],
         '3': ['###', '..#', '.##', '..#', '###'], '4': ['#.#', '#.#', '###', '..#', '..#'], '5': ['###', '#..', '###', '..#', '###'],
         '6': ['###', '#..', '###', '#.#', '###'], '7': ['###', '..#', '.#.', '.#.', '.#.'], '8': ['###', '#.#', '###', '#.#', '###'],
         '9': ['###', '#.#', '###', '..#', '###'], '×': ['...', '#.#', '.#.', '#.#', '...'], 'x': ['...', '#.#', '.#.', '#.#', '...'],
         '=': ['...', '###', '...', '###', '...'], '+': ['...', '.#.', '###', '.#.', '...'], '-': ['...', '...', '###', '...', '...'],
         '%': ['#.#', '..#', '.#.', '#..', '#.#'], ':': ['...', '.#.', '...', '.#.', '...'], '.': ['...', '...', '...', '...', '.#.'],
         '?': ['###', '..#', '.##', '...', '.#.'], '!': ['.#.', '.#.', '.#.', '...', '.#.'], ' ': ['...'] * 5}

def face_text(cv, E, text, x0, y0, w, h, glow=1.0, col=None):
    """centre lines of DIG35 text in the screen box (x0, y0, w, h)."""
    lines = text.split('/')
    col = col or EYE
    lh = 6; top = y0 + (h - (len(lines) * lh - 1)) // 2
    for i, ln in enumerate(lines):
        lw = 4 * len(ln) - 1
        x = x0 + (w - lw) // 2; y = top + i * lh
        for ch in ln:
            g = DIG35.get(ch, DIG35[' '])
            for yy, row in enumerate(g):
                for xx, c in enumerate(row):
                    if c == '#':
                        cv.px(x + xx, y + yy, col); E[y + yy, x + xx] = 0.85 * glow
            x += 4

TEAR = C('#a8e4ff'); TEAR_HI = C('#f0fbff'); TEAR_TR = C('#3f6d8c')

def draw_tear(cv, E, k, look=(0, 0), side=1, glow=1.0):
    """v0.8.1: one small glowing tear on the face screen (restrained, deadpan-friendly), cool cyan vs the warm eyes.
    k 0..1 progress: 0-0.3 wells up at the eye's outer corner (1 px -> 2x2), 0.3-0.75 a 2x3 drop slides down
    with gravity leaving a dim 1 px trail, 0.75-1 lands on the screen's bottom edge, splats flat and fades.
    side 1 = right eye (default), -1 = left."""
    if k <= 0 or k >= 1 or glow <= 0: return
    sx, sy, sw, sh = SCREEN
    ox, oy = HX + sx, HY + sy
    lx, ly = look
    if side > 0: tx = ox + sw - EYE_POS[0] + lx - 1          # just outside the right eye's outer edge
    else:        tx = ox + EYE_POS[0] + lx - 2
    y0 = oy + EYE_POS[1] + ly + 5                            # outer corner, lower half of the eye
    ybot = oy + sh - 3                                       # last row the drop's bottom can reach
    def put(x, y, col, e):
        if oy + 1 <= y <= oy + sh - 2 and ox + 1 <= x <= ox + sw - 2:
            cv.px(x, y, col); E[y, x] = max(E[y, x], e * glow)
    if k < 0.3:                                              # well up
        u = k / 0.3
        put(tx, y0, TEAR_HI if u > 0.5 else TEAR, 0.5 + 0.4 * u)
        if u > 0.45: put(tx + 1, y0, TEAR, 0.7); put(tx, y0 + 1, TEAR, 0.7)
        if u > 0.75: put(tx + 1, y0 + 1, TEAR, 0.75)
        return
    if k < 0.75:                                             # slide (ease-in = gravity)
        u = (k - 0.3) / 0.45
        top = int(round(y0 + (ybot - 2 - y0) * u * u))       # drop rows: top (tip), top+1, top+2
        for yy in range(y0, top): put(tx, yy, TEAR_TR, 0.30)
        put(tx, top, TEAR, 0.8)
        put(tx, top + 1, TEAR_HI, 0.95); put(tx + 1, top + 1, TEAR, 0.85)
        put(tx, top + 2, TEAR, 0.85); put(tx + 1, top + 2, TEAR, 0.8)
        return
    u = (k - 0.75) / 0.25                                    # land: splat flat, then fade
    a = 1 - u
    if u < 0.35:
        for yy in range(y0 + int(u * 10), ybot - 1): put(tx, yy, TEAR_TR, 0.25)
    if u < 0.15:
        put(tx, ybot - 1, TEAR_HI, 0.9); put(tx + 1, ybot - 1, TEAR, 0.8)
        put(tx - 1, ybot, TEAR, 0.8); put(tx, ybot, TEAR, 0.85); put(tx + 1, ybot, TEAR, 0.8); put(tx + 2, ybot, TEAR, 0.7)
    else:
        c = TEAR if a > 0.45 else TEAR_TR
        for dx in (-1, 0, 1, 2): put(tx + dx, ybot, c, 0.8 * a)

def draw_face(cv, E, face='normal', look=(0, 0), glow=1.0, tear=0.0, tear_side=1):
    _draw_face(cv, E, face, look, glow)
    if tear > 0: draw_tear(cv, E, tear, look, tear_side, glow)

def _draw_face(cv, E, face='normal', look=(0, 0), glow=1.0):
    sx, sy, sw, sh = SCREEN
    ox, oy = HX + sx, HY + sy
    lx, ly = look
    if face == 'off': return
    if face.startswith('txt:'):          # v0.7: pixel text on the screen (numbers, a quick sum)
        face_text(cv, E, face[4:], ox + 1, oy + 1, sw - 2, sh - 2, glow, col=EYE if glow > 0.6 else EYE_DIM); return
    if face == 'map':
        _map_icon(cv, E, ox + (sw - 17) // 2 + lx, oy + 4 + ly, glow); return
    if face == 'q':
        _glyph(cv, E, QMARK, ox + (sw - 6) // 2 + lx, oy + 6 + ly, glow=glow); return
    if face.startswith('load'):          # loading spinner: 'load0'..'load7' = which of the 8 dots is the head
        k = int(face[4:] or 0) % 8
        ccx, ccy = ox + sw // 2 + lx, oy + sh // 2 + ly
        for i in range(8):
            a = 2 * math.pi * i / 8 - math.pi / 2
            px_, py_ = int(round(ccx + 6 * math.cos(a))) - 1, int(round(ccy + 6 * math.sin(a))) - 1
            d = (k - i) % 8
            col, e = ((EYE_HI, 1.0) if d == 0 else (EYE, 0.8) if d == 1 else (EYE_LO, 0.55) if d == 2 else (SCR3, 0.0))
            cv.rect(px_, py_, 2, 2, col)
            if e: E[py_:py_ + 2, px_:px_ + 2] = e * glow
        return
    if face == 'calm':                   # eyes closed, at peace:  - -
        for ex in (ox + EYE_POS[0] + lx, ox + sw - EYE_POS[0] - 6 + lx):
            y_ = oy + EYE_POS[1] + 5 + ly
            cv.hline(ex, y_, 6, EYE); cv.hline(ex + 1, y_ + 1, 4, HALO)
            E[y_, ex:ex + 6] = 0.85 * glow
        return
    if face == 'dizzy':
        _glyph(cv, E, EYES['dizzyL'], ox + EYE_POS[0] + lx, oy + EYE_POS[1] + ly, glow=glow, halo=False)
        _glyph(cv, E, EYES['dizzyL'], ox + sw - EYE_POS[0] - 6 + lx, oy + EYE_POS[1] + ly, mirror=True, glow=glow, halo=False); return
    if face == 'droop':
        _glyph(cv, E, EYES['droopL'], ox + EYE_POS[0] + lx, oy + EYE_POS[1] + ly, mirror=True, glow=glow)
        _glyph(cv, E, EYES['droopL'], ox + sw - EYE_POS[0] - 6 + lx, oy + EYE_POS[1] + ly, glow=glow); return
    if face == 'dots':                   # two loading dots that light up then die (about to do something... no)
        ccx, ccy = ox + sw // 2 + lx, oy + sh // 2 + ly
        for dx_ in (-4, 2):
            cv.rect(ccx + dx_, ccy, 2, 2, EYE); E[ccy:ccy + 2, ccx + dx_:ccx + dx_ + 2] = 0.8 * glow
        return
    if face == 'dots1':
        ccx, ccy = ox + sw // 2 + lx, oy + sh // 2 + ly
        cv.rect(ccx - 4, ccy, 2, 2, EYE); E[ccy:ccy + 2, ccx - 4:ccx - 2] = 0.8 * glow
        return
    if face == 'ellipsis':               # '...' (lost for words)
        ccx, ccy = ox + sw // 2 + lx, oy + sh // 2 + 2 + ly
        for dx_ in (-7, -1, 5):
            cv.rect(ccx + dx_, ccy, 2, 2, EYE); E[ccy:ccy + 2, ccx + dx_:ccx + dx_ + 2] = 0.8 * glow
        return
    if face in ('peek', 'wink'):         # v0.9: one eye open (peek = left closed / right open; wink = the reverse)
        sh_ = face == 'wink'
        gl, gr = (EYES['normal'], EYES['closed']) if sh_ else (EYES['closed'], EYES['normal'])
        _glyph(cv, E, gl, ox + EYE_POS[0] + lx, oy + EYE_POS[1] + ly, glow=glow, halo=gl is EYES['normal'])
        _glyph(cv, E, gr, ox + sw - EYE_POS[0] - 6 + lx, oy + EYE_POS[1] + ly, mirror=True, glow=glow, halo=gr is EYES['normal'])
        return
    if face == 'sad':
        _glyph(cv, E, EYES['sadL'], ox + EYE_POS[0] + lx, oy + EYE_POS[1] + ly, mirror=True, glow=glow)
        _glyph(cv, E, EYES['sadL'], ox + sw - EYE_POS[0] - 6 + lx, oy + EYE_POS[1] + ly, glow=glow); return
    g = EYES.get(face, EYES['normal'])
    if face == 'wide2': g = EYES['wideL']
    dy = -1 if face == 'wide' else (-2 if face == 'wide2' else 0)
    halo = face not in ('closed', 'happy', 'blink', 'squint')
    _glyph(cv, E, g, ox + EYE_POS[0] + lx, oy + EYE_POS[1] + dy + ly, glow=glow, halo=halo)
    _glyph(cv, E, g, ox + sw - EYE_POS[0] - 6 + lx, oy + EYE_POS[1] + dy + ly, mirror=True, glow=glow, halo=halo)

def draw_head(cv, E, face='normal', look=(0, 0), led='online', led_k=1.0, glow=1.0, spark_k=1.0, headset=False, ant=(0, 0),
              tear=0.0, tear_side=1):
    x, y, w, h = HX, HY, HW, HH
    sx, sy, sw, sh = SCREEN
    ax = x + sx + sw // 2                          # antenna sits on the front plate (3/4 view)
    # antenna: short silver stick + node, the Claude spark floats just above it (1px gap)
    ST = C('#d8d0d8'); ST_D = C('#8f8496')
    cv.rect(ax - 1, y - 1, 3, 2, ST_D); cv.px(ax, y - 1, ST)
    tdx, tdy = ant                                  # v0.7: spring offset of the antenna tip (perform.lag / wobble)
    tdx = int(round(max(-4, min(4, tdx)))); tdy = int(round(max(-2, min(2, tdy))))
    if tdx == 0 and tdy == 0:
        cv.vline(ax, y - 4, 3, ST); cv.vline(ax + 1, y - 4, 3, ST_D)
        cv.rect(ax - 1, y - 6, 3, 2, ST_D); cv.hline(ax - 1, y - 6, 2, HI2)
    else:                                           # bent stick: base fixed, node moves half, the logo the full offset
        nx, ny = ax + int(round(tdx * 0.5)), y - 6 + int(round(tdy * 0.5))
        for i in range(4):
            u = (i + 1) / 4.0
            px_ = ax + int(round((nx - ax) * u * u)); py_ = y - 2 - i
            cv.px(px_, py_, ST); cv.px(px_ + 1, py_, ST_D)
        cv.rect(nx - 1, ny, 3, 2, ST_D); cv.hline(nx - 1, ny, 2, HI2)
    draw_logo(cv, E, ax + tdx, y - 13 + tdy, k=spark_k)
    if headset:
        cv.hline(x + 8, y - 2, w - 16, HS); cv.hline(x + 10, y - 2, 5, HS_HI)
    # shell
    cv.rrect(x, y, w, h, OUT, 6)
    cv.rrect(x + 1, y + 1, w - 2, h - 2, BASE, 5)
    # side panel (left, slightly darker) + seam
    for yy in range(y + 2, y + h - 2):
        u = (yy - y) / h
        col = SIDE1 if u < 0.62 else SIDE2
        x0 = x + 1 if 4 < yy - y < h - 5 else x + 3
        cv.hline(x0, yy, x + SIDE - x0, col)
    cv.vline(x + SIDE, y + 4, h - 7, SH1); cv.vline(x + 2, y + 6, h - 16, HI)
    # top face highlight
    cv.hline(x + 6, y + 1, w - 12, HI2); cv.hline(x + 3, y + 2, w - 7, HI); cv.hline(x + SIDE + 1, y + 3, w - SIDE - 4, HI)
    # ear hub (on the side panel)
    ex, ey = x + 4, y + 16
    cv.ellipse(ex + 0.5, ey + 0.5, 3.6, 4.2, TC_OUT); cv.ellipse(ex + 0.5, ey + 0.5, 2.6, 3.2, TC)
    cv.px(ex - 1, ey - 2, TC_HI); cv.px(ex, ey - 2, TC_HI); cv.vline(ex + 2, ey - 1, 3, TC_SH); cv.px(ex, ey, TC_DK); cv.px(ex, ey + 1, TC_DK)
    # front-plate form shading: right edge + chin
    cv.rect(x + w - 4, y + 5, 2, h - 10, SH1); cv.vline(x + w - 2, y + 6, h - 12, SH2)
    cv.rect(x + SIDE + 2, y + h - 4, w - SIDE - 5, 2, SH1); cv.hline(x + 5, y + h - 2, w - 10, SH2)
    cv.hline(x + 3, y + h - 3, SIDE - 2, SH2)
    # screen bezel + screen
    cv.rrect(x + sx - 1, y + sy - 1, sw + 2, sh + 2, BEZ, 3)
    cv.rrect(x + sx, y + sy, sw, sh, SCR, 3)
    cv.hline(x + sx + 3, y + sy, sw - 6, SCR3); cv.hline(x + sx + 2, y + sy + 1, sw - 4, SCR2); cv.hline(x + sx + 1, y + sy + 2, sw - 2, SCR2)
    cv.px(x + sx + sw - 4, y + sy + 2, SCR3); cv.px(x + sx + sw - 3, y + sy + 3, SCR3); cv.px(x + sx + sw - 3, y + sy + 4, SCR2)
    draw_face(cv, E, face, look, glow, tear, tear_side)
    # status LED (chin, right)
    lc = LED.get(led, LED['off'])
    lx, ly = x + w - 9, y + h - 4
    if led != 'off':
        lc2 = mix(LED['off'], lc, max(0.0, min(1.0, led_k)))
        cv.rect(lx, ly, 2, 1, lc2); E[ly:ly + 1, lx:lx + 2] = led_k
    else:
        cv.rect(lx, ly, 2, 1, lc)
    cv.hline(x + SIDE + 4, y + h - 4, 4, SH2)

def torso_box():
    tw, th = 24, 15
    return AX - tw // 2 + 1, HY + HH - 2, tw, th

# walk cycle (4 phases): per-leg (dx, lift) for (left, right) + body bob.  Used by draw(pose='walk').
WALK_LEGS = [((3, 0), (-2, 0)), ((0, 2), (0, 0)), ((-2, 0), (3, 0)), ((0, 0), (0, 2))]
WALK_BOB = [0, -1, 0, -1]

def _leg(cv, lx, y, h, dx=0, lift=0):
    lx = lx + dx
    ll = 8 - lift
    cv.rrect(lx, y + h - 3, 6, ll, TC_OUT, 2); cv.rect(lx + 1, y + h - 2, 4, ll - 2, TC_SH); cv.vline(lx + 1, y + h - 2, ll - 3, TC)
    fy = y + h + 3 - lift
    cv.rrect(lx - 1, fy, 8, 4, TC_OUT, 2); cv.rect(lx, fy + 1, 6, 2, FOOT); cv.hline(lx + 1, fy + 1, 3, C('#ffd0c0'))

SIT_Y = 63                       # sprite row of the seat contact for pose='sit' (bottom of the body)

def _leg_sit(cv, x, y):
    """v0.7 'plush toy' sit: a stubby leg stretched toward the camera, its round coral sole facing us.
    (x, y) = top-left of the stub; the sole hangs a little below the seat row (the feet rest on the floor in front)."""
    cv.rrect(x, y, 8, 6, TC_OUT, 2); cv.rect(x + 1, y + 1, 6, 4, TC); cv.hline(x + 2, y + 1, 4, TC_HI); cv.hline(x + 1, y + 4, 6, TC_SH)
    sx, sy = x - 1, y + 3
    cv.rrect(sx, sy, 10, 8, TC_OUT, 3); cv.rrect(sx + 1, sy + 1, 8, 6, FOOT, 2)
    cv.hline(sx + 3, sy + 1, 4, C('#ffd0c0')); cv.px(sx + 2, sy + 2, C('#ffd0c0'))
    cv.hline(sx + 2, sy + 6, 6, mix(FOOT, TC_SH, 0.45)); cv.px(sx + 8, sy + 5, mix(FOOT, TC_SH, 0.45))

def draw_torso(cv, E, badge=True, legs=True, leg_off=((0, 0), (0, 0)), sit=False, kick=0):
    x, y, w, h = torso_box()
    if legs and sit:
        pass
    elif legs:
        # the back leg (right, further from camera in 3/4 view) first
        _leg(cv, x + w - 10, y, h, *leg_off[1]); _leg(cv, x + 4, y, h, *leg_off[0])
    cv.rrect(x, y, w, h, TC_OUT, 5)
    cv.rrect(x + 1, y + 1, w - 2, h - 2, TC, 4)
    cv.rect(x + w - 5, y + 3, 3, h - 5, TC_SH); cv.vline(x + w - 2, y + 4, h - 7, TC_DK)
    cv.hline(x + 4, y + h - 2, w - 8, TC_SH)
    cv.hline(x + 5, y + 2, w - 12, TC_HI); cv.vline(x + 2, y + 4, 5, TC_HI)
    cv.rect(x + 5, y, w - 10, 2, TC_DK)                  # neck shadow under the head
    if legs and sit:
        _leg_sit(cv, x + 3, y + h - 6 - (1 if kick & 1 else 0)); _leg_sit(cv, x + 14, y + h - 6 - (1 if kick & 2 else 0))
    if badge:
        cx = x + w // 2
        cv.line(x + 6, y + 1, cx - 1, y + 6, LAN); cv.line(x + w - 7, y + 1, cx + 1, y + 6, LAN)
        cv.rect(cx - 3, y + 6, 7, 7, TC_OUT); cv.rect(cx - 2, y + 7, 5, 5, CARD)
        cv.hline(cx - 2, y + 7, 5, LAN_SH); cv.px(cx - 1, y + 9, SH1); cv.hline(cx - 1, y + 10, 3, CARD_SH)

def _hand(cv, x, y, big=False):
    w, h = (9, 8) if big else (8, 7)
    cv.rrect(x, y, w, h, HAND_OUT, 3); cv.rrect(x + 1, y + 1, w - 2, h - 2, HAND, 2)
    cv.hline(x + 2, y + h - 2, w - 4, HAND_SH); cv.px(x + w - 2, y + h - 3, HAND_SH)
    cv.px(x + 2, y + 1, HI2); cv.px(x + 1, y + 2, HI2)

def _sleeve(cv, pts, width=6):
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(n + 1):
            xx = x0 + (x1 - x0) * i / n; yy = y0 + (y1 - y0) * i / n
            cv.rect(int(round(xx - width / 2)), int(round(yy - width / 2)), width, width, TC_OUT)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(n + 1):
            xx = x0 + (x1 - x0) * i / n; yy = y0 + (y1 - y0) * i / n
            cv.rect(int(round(xx - width / 2 + 1)), int(round(yy - width / 2 + 1)), width - 2, width - 2, TC)
            cv.px(int(round(xx + width / 2 - 2)), int(round(yy)), TC_SH)

def arm_spec(arms='rest', phase=0, desk_y=None):
    """arm pose as DATA: {'L': (sleeve_pts, (hand_x, hand_y), big), 'R': (...)} in sprite px.  Data (not drawing code)
    so poses can be blended: draw(arms=('rest', 'clasp', 0.4)) lerps the sleeves (resampled) and the hands."""
    bx, by, bw, bh = torso_box()
    dy = (desk_y if desk_y is not None else by + bh + 2)
    L, R = bx + 2, bx + bw - 3
    sy = by + 4
    if arms in ('rest', 'type'):
        up = (phase % 2) if arms == 'type' else 0
        upR = ((phase + 1) % 2) if arms == 'type' else 0
        inset = 3 if arms == 'type' else 0
        return {'L': ([(L, sy), (L - 3, sy + 5), (L + inset - 1, dy - 1 - up)], (L + inset - 6, dy - 3 - up), False),
                'R': ([(R, sy), (R + 3, sy + 5), (R - inset + 1, dy - 1 - upR)], (R - inset - 2, dy - 3 - upR), False)}
    if arms == 'up':
        return {'L': ([(L, sy), (L - 6, sy - 6), (L - 8, sy - 12)], (L - 13, sy - 19), True),
                'R': ([(R, sy), (R + 6, sy - 6), (R + 8, sy - 12)], (R + 4, sy - 19), True)}
    if arms == 'shrug':
        return {'L': ([(L, sy), (L - 6, sy + 3), (L - 9, sy - 1)], (L - 15, sy - 5), True),
                'R': ([(R, sy), (R + 6, sy + 3), (R + 9, sy - 1)], (R + 6, sy - 5), True)}
    if arms == 'wave':
        a = int(round(0.35 * math.sin(phase * 1.3) * 4))
        return {'L': ([(L, sy), (L - 3, sy + 5), (L - 1, dy - 1)], (L - 6, dy - 3), False),
                'R': ([(R, sy), (R + 6, sy - 5), (R + 8 + a, sy - 12)], (R + 4 + a, sy - 19), True)}
    if arms == 'hold':
        return {'L': ([(L, sy), (L - 2, sy + 5), (L + 5, sy + 8)], (L + 2, sy + 4), False),
                'R': ([(R, sy), (R + 2, sy + 5), (R - 5, sy + 8)], (R - 9, sy + 4), False)}
    if arms == 'receive':        # both hands reach forward (+x) and cup together, palms up (taking something)
        return {'L': ([(L, sy), (L + 4, sy + 7), (R + 1, sy + 6)], (R - 2, sy + 3), False),
                'R': ([(R, sy), (R + 5, sy + 4)], (R + 4, sy + 1), False)}
    if arms == 'lift':           # cupped hands raised in front of the chest (showing what it holds)
        return {'L': ([(L, sy), (L + 4, sy + 2), (R, sy - 2)], (R - 3, sy - 5), False),
                'R': ([(R, sy), (R + 4, sy - 3)], (R + 3, sy - 6), False)}
    if arms == 'present':        # right hand up and open beside the head (here's the plan!), left at rest
        return {'L': ([(L, sy), (L - 3, sy + 9)], (L - 7, sy + 8), False),
                'R': ([(R, sy), (R + 7, sy - 2), (R + 10, sy - 8)], (R + 6, sy - 15), True)}
    if arms == 'down':
        return {'L': ([(L, sy), (L - 3, sy + 9)], (L - 7, sy + 8), False),
                'R': ([(R, sy), (R + 3, sy + 9)], (R - 1, sy + 8), False)}
    if arms == 'swing':          # walking: hands swing opposite to the legs (phase 0..3)
        s_ = (2, 0, -2, 0)[phase % 4]
        return {'R': ([(R, sy), (R + 3 - s_ // 2, sy + 9)], (R - 1 - s_, sy + 8), False),
                'L': ([(L, sy), (L - 3 + s_ // 2, sy + 9)], (L - 7 + s_, sy + 8), False)}
    if arms == 'shade':          # right hand up as a visor on the brow (blinded by the sun)
        return {'L': ([(L, sy), (L - 3, sy + 9)], (L - 7, sy + 8), False),
                'R': ([(R, sy), (R + 10, sy - 8), (R + 9, sy - 22)], (R - 3, sy - 31), True)}
    if arms == 'ear':            # left hand up on the coral ear hub (pressing a 'button'), right arm resting
        return {'R': ([(R, sy), (R + 3, sy + 5), (R + 1, dy - 1)], (R - 2, dy - 3), False),
                'L': ([(L, sy), (L - 6, sy - 1), (HX + 1, HY + 21)], (HX - 2, HY + 12), True)}
    if arms == 'stretch':        # big morning stretch: stubby arms up beside the head (v0.10: shortened ~35% - chibi
        # arms only reach the upper head corners; the long v0.6 V read as 'too long')
        return {'L': ([(L, sy), (L - 7, sy - 5), (L - 9, sy - 14)], (L - 14, sy - 22), True),
                'R': ([(R, sy), (R + 7, sy - 5), (R + 9, sy - 14)], (R + 5, sy - 22), True)}
    if arms == 'pillow':         # hands behind the head (lying down)
        return {'L': ([(L, sy), (L - 6, sy - 4), (L - 2, sy - 12)], (L - 6, sy - 18), False),
                'R': ([(R, sy), (R + 6, sy - 4), (R + 2, sy - 12)], (R - 2, sy - 18), False)}
    # ---- v0.7 performance poses
    if arms == 'clasp':          # polite: both hands together in front of the belly (asking, waiting)
        return {'L': ([(L, sy), (L - 1, sy + 6), (L + 5, sy + 8)], (L + 3, sy + 4), False),
                'R': ([(R, sy), (R + 1, sy + 6), (R - 5, sy + 8)], (R - 9, sy + 4), False)}
    if arms == 'knees':          # seated: hands resting on the leg stubs; phase taps the fingers (L / R alternately)
        tl = 1 if phase % 4 == 1 else 0; tr = 1 if phase % 4 == 3 else 0
        return {'L': ([(L, sy), (L - 2, sy + 6), (L + 2, sy + 9)], (L - 1, sy + 5 - tl), False),
                'R': ([(R, sy), (R + 2, sy + 6), (R - 2, sy + 9)], (R - 6, sy + 5 - tr), False)}
    if arms == 'reach':          # v0.8: right arm stretched out to the right edge of the sprite (one finger steadies
        # something standing on the desk just right of the sprite: hand spans sprite x 68..76, y sy-16..sy-9)
        return {'L': ([(L, sy), (L - 3, sy + 5), (L - 1, dy - 1)], (L - 6, dy - 3), False),
                'R': ([(R, sy), (R + 9, sy - 3), (R + 18, sy - 10)], (R + 19, sy - 16), False)}
    if arms == 'point':          # right hand reaching forward-up (following / pointing at something on the right)
        return {'L': ([(L, sy), (L - 3, sy + 9)], (L - 7, sy + 8), False),
                'R': ([(R, sy), (R + 6, sy + 1), (R + 11, sy - 3)], (R + 9, sy - 8), False)}
    if arms == 'hips':           # v0.9: hands on hips (proud / ta-da), elbows out
        return {'L': ([(L, sy), (L - 7, sy + 3), (L - 3, sy + 8)], (L - 7, sy + 6), False),
                'R': ([(R, sy), (R + 7, sy + 3), (R + 3, sy + 8)], (R - 1, sy + 6), False)}
    if arms == 'bow':            # v0.9: polite bow, both hands together low in front
        return {'L': ([(L, sy), (L + 1, sy + 7), (L + 6, sy + 10)], (L + 4, sy + 7), False),
                'R': ([(R, sy), (R - 1, sy + 7), (R - 6, sy + 10)], (R - 10, sy + 7), False)}
    return arm_spec('rest', phase, desk_y)

def _resample(pts, n=6):
    """polyline -> n points evenly spaced by arc length (for pose blending)."""
    pts = [(float(x), float(y)) for x, y in pts]
    if len(pts) == 1: return pts * n
    seg = [math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:])]
    tot = sum(seg) or 1.0
    out = []
    for i in range(n):
        d = tot * i / (n - 1); j = 0
        while j < len(seg) - 1 and d > seg[j]: d -= seg[j]; j += 1
        u = d / seg[j] if seg[j] else 0.0
        (x0, y0), (x1, y1) = pts[j], pts[j + 1]
        out.append((x0 + (x1 - x0) * u, y0 + (y1 - y0) * u))
    return out

def blend_spec(a, b, k):
    if k <= 0: return a
    if k == 1: return b
    out = {}
    for side in ('L', 'R'):
        pa, ha, ba = a[side]; pb, hb, bb = b[side]
        ra, rb = _resample(pa), _resample(pb)
        pts = [(x0 + (x1 - x0) * k, y0 + (y1 - y0) * k) for (x0, y0), (x1, y1) in zip(ra, rb)]
        hx = ha[0] + (hb[0] - ha[0]) * k; hy = ha[1] + (hb[1] - ha[1]) * k
        out[side] = (pts, (int(round(hx)), int(round(hy))), bb if k >= 0.5 else ba)
    out['_order'] = list(b.keys()) if k >= 0.5 else list(a.keys())
    return out

def draw_arms(cv, E, arms='rest', phase=0, desk_y=None):
    """stubby arms + big round hands. desk_y: sprite y of the desk top (hands rest on it).
    arms: a pose name, or (pose_a, pose_b, k) to blend (perform.PoseTrack returns exactly that)."""
    if isinstance(arms, tuple):
        a_, b_, k = arms
        spec = blend_spec(arm_spec(a_, phase, desk_y), arm_spec(b_, phase, desk_y), k)
    else:
        spec = arm_spec(arms, phase, desk_y)
    order = [s for s in spec.get('_order', list(spec.keys())) if not s.startswith('_')]
    pairs = arms in ('wave', 'swing', 'ear', 'present', 'down', 'shade') if isinstance(arms, str) else False
    if pairs:                     # sleeve + hand per side (the original drawing order of these poses)
        for s_ in order:
            pts, (hx, hy), big = spec[s_]; _sleeve(cv, [(int(round(x)), int(round(y))) for x, y in pts]); _hand(cv, hx, hy, big)
    else:
        for s_ in order: _sleeve(cv, [(int(round(x)), int(round(y))) for x, y in spec[s_][0]])
        for s_ in order: _hand(cv, spec[s_][1][0], spec[s_][1][1], spec[s_][2])

FOOT_Y = 70                      # sprite row just below the feet (stand / walk): world foot line = y_head_top + FOOT_Y - AY

def draw(face='normal', arms='rest', phase=0, led='online', led_k=1.0, look=(0, 0), glow=1.0, desk_y=None,
         squash=0.0, spark_k=1.0, headset=False, badge=True, legs=True, pose='stand', flip=False,
         tilt=0.0, head_dy=0, head_dx=0, ant=(0, 0), leg_kick=0, tear=0.0, tear_side=1):
    """returns SimpleNamespace(body=Sprite, hands=Sprite, ax, ay, bob) - sprites share coordinates.
    pose: 'stand' (default, also used behind desks) | 'walk' (phase 0..3 leg cycle, use arms='swing';
          .bob = body bob in px, add it to y) | 'lie' (rotated 90 deg, head to the left, hands merged into body).
    flip: mirror (facing left; the 3/4 side panel moves to the right).
    v0.7 performance (see pixelkit.perform):
      arms     a name or (pose_a, pose_b, k) blend      tilt   head roll in degrees (+ = clockwise), pixel shear rotation
      head_dy  head offset vs the torso (breath / nod / sink), head_dx sideways
      ant      (dx, dy) antenna-tip spring offset        leg_kick  pose='sit': soles lift (1 left / 2 right / 3 both)
    v0.8.1: tear 0..1 = progress of one small glowing tear on the face screen (draw_tear), tear_side 1 right / -1 left"""
    body = Sprite(SW, SH); hands = Sprite(SW, SH)
    leg_off = WALK_LEGS[phase % 4] if pose == 'walk' else ((0, 0), (0, 0))
    bob = WALK_BOB[phase % 4] if pose == 'walk' else 0
    draw_torso(body.cv, body.E, badge, legs, leg_off, sit=(pose == 'sit'), kick=leg_kick)
    if abs(tilt) < 0.5 and not head_dy and not head_dx:
        draw_head(body.cv, body.E, face, look, led, led_k, glow, spark_k, headset, ant, tear, tear_side)
    else:                       # head on its own layer: roll about the neck, offset, then over the torso
        from ..perform import rotsprite
        hd = Sprite(SW, SH)
        draw_head(hd.cv, hd.E, face, look, led, led_k, glow, spark_k, headset, ant, tear, tear_side)
        ha, he = rotsprite(hd.cv.a, hd.E, tilt, (AX, HY + HH - 1)) if abs(tilt) >= 0.5 else (hd.cv.a, hd.E)
        if head_dy or head_dx:
            ha = np.roll(np.roll(ha, head_dy, 0), head_dx, 1); he = np.roll(np.roll(he, head_dy, 0), head_dx, 1)
        m = ha[..., 3] > 0
        body.cv.a[m] = ha[m]; body.E[m] = he[m]
    draw_arms(hands.cv, hands.E, arms, phase, desk_y)
    if bob:     # legs stay planted: shift everything above the hips
        hip = torso_box()[1] + torso_box()[3] - 3
        for sp in (body, hands):
            a = sp.cv.a; e = sp.E
            a[:hip + bob] = a[-bob:hip].copy()
            e[:hip + bob] = e[-bob:hip].copy()
    ax, ay = AX, AY
    if pose == 'lie':
        m = hands.cv.a[..., 3] > 0
        body.cv.a[m] = hands.cv.a[m]; body.E[m] = hands.E[m]
        ra = np.ascontiguousarray(np.rot90(body.cv.a, 1)); re = np.ascontiguousarray(np.rot90(body.E, 1))
        body = Sprite(ra.shape[1], ra.shape[0]); body.cv.a = ra; body.E = re
        hands = Sprite(ra.shape[1], ra.shape[0])
        ax, ay = AY, SW - 1 - AX
    if flip:
        for sp in (body, hands):
            sp.cv.a = np.ascontiguousarray(sp.cv.a[:, ::-1]); sp.E = np.ascontiguousarray(sp.E[:, ::-1])
        ax = body.cv.a.shape[1] - 1 - ax
    if abs(squash) > 1e-3:
        sx = 1.0 + squash * 0.6; sy = 1.0 - squash
        for sp in (body, hands):
            rgba = scale_nearest(sp.cv.a, sx, sy); E = scale_nearest(sp.E, sx, sy)
            sp.cv = Canvas(rgba.shape[1], rgba.shape[0]); sp.cv.a = rgba; sp.E = E
        nh, nw = body.cv.a.shape[:2]
        # keep the bottom-centre fixed
        ax = AX * sx; ay = SH - (SH - AY) * sy
        ax = AX * nw / SW; ay = nh - (SH - AY) * nh / SH
    return SimpleNamespace(body=body, hands=hands, ax=ax, ay=ay, bob=bob)

def crt_off(cv, E, k):
    """old-TV power-off on the face screen of a drawn sprite (body canvas + E): k 0..1
    0-0.45 picture collapses to a bright horizontal line, 0.45-0.8 the line shrinks to a dot, 0.8-1 dot fades."""
    if k <= 0: return
    sx, sy, sw, sh = SCREEN; x0, y0 = HX + sx, HY + sy
    W_ = C('#f4fbff'); cyc = y0 + sh // 2
    a = cv.a; dark = np.array(SCR, np.uint8)
    reg = a[y0:y0 + sh, x0:x0 + sw]; m = reg[..., 3] > 0
    reg[m] = dark; E[y0:y0 + sh, x0:x0 + sw][m] = 0.0
    if k < 0.45:
        u = k / 0.45; hh = max(1, int(round(sh * (1 - u) ** 2)))
        ww = sw - 4
        for yy in range(cyc - hh // 2, cyc - hh // 2 + hh):
            col = mix(SCR3, W_, min(1.0, 0.35 + u))
            cv.hline(x0 + 2, yy, ww, col); E[yy, x0 + 2:x0 + 2 + ww] = 0.5 + 0.5 * u
    elif k < 0.8:
        u = (k - 0.45) / 0.35; ww = max(1, int(round((sw - 4) * (1 - u) ** 1.5)))
        cv.hline(x0 + sw // 2 - ww // 2, cyc, ww, W_); E[cyc, x0 + sw // 2 - ww // 2:x0 + sw // 2 - ww // 2 + ww] = 1.0
    else:
        u = (k - 0.8) / 0.2
        if u < 1:
            cv.px(x0 + sw // 2, cyc, mix(W_, SCR, u)); E[cyc, x0 + sw // 2] = 1.0 - u

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
