"""ACT IV v2 renderer: make() -> object with .frame(t) -> float RGB (1080, 1920, 3).   Shots + timing: timeline.py

Geometry of the 'side' shots (SIDE2 / SIDE_H / the singles): a low camera behind and to the side of the pair, looking
out toward the sunset, both turned toward each other - Claude (left, faces right) sits on the pier end, the old man
(right, faces left) on his folding stool; the sun sits between them.  Characters are crisp sprites placed in front of
the (blurred) pier world; a sharp deck strip carries them.  The singles are the same axis, closer (shot / reverse shot)."""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math, importlib.util
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/act4'))
import numpy as np, cv2
import timeline as TL
from pixelkit.core import Canvas, C, mix, scale_nearest, text_width
from pixelkit.anim import ramp, ease_io, ease_out3, clamp01, blink_at, hop, squash_curve
from pixelkit.camera import Cam
from pixelkit.scene import GLayer, ui_over, FlatScene
from pixelkit.outdoor import OutdoorScene, outdoor_state, dof, pixel_soft
from pixelkit import perform as PF
BG_MODE = 'pixel'          # v2: 'pixel' (pixel_soft, default) | 'dof' (v1 photographic) | 'crisp'
from pixelkit.sets import river_pier as RP
from pixelkit.characters import backs, claude as CL, person as P
from pixelkit import ui, edit
from pixelkit.particles import PixelSwarm

# ---- paint_v2 (the oil-paint shot) lives in its own project with its own `timeline` module: load it under other names
def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m; sp.loader.exec_module(m); return m
_act4_tl = sys.modules['timeline']
PTL = _load('pv2_timeline', (_PROJ + '/paint_v2/timeline.py'))
PTL.BOXES[0]['lines'][0]['zh'] = '那天傍晚，我第一次不知道过了多久。'
PTL.BOXES[0]['lines'][0]['en'] = 'That evening, for the first time, I lost track of time.'
from pixelkit.anim import boxes_prep as _bp; _bp(PTL.BOXES)
sys.modules['timeline'] = PTL
PV = _load('pv2_scene', (_PROJ + '/paint_v2/scene.py'))
sys.modules['timeline'] = _act4_tl

def bob_far_water():
    """the far bobber cut at the waterline (rows 5-6 are under water)."""
    a, E = RP.bobber_far(); a = a.copy(); a[5:] = 0
    return a, E
PV.bobber_sprite = bob_far_water            # paint_v2 uses the same far float as every pixel wide

OM_X, OM_Y = RP.OLD_SEAT
ROD_TIP = PV.ROD_TIP
OLD = P.CAST['old_fisher']
UIS = 4                                              # UI scale (480x270 grid -> 1080p)


def bake_rim(rgba, E, sun_side=1, k=0.75, col=(255, 200, 150), width=1):
    a = rgba.copy(); e = E.copy()
    backs._rim(a, e, sun_side, col=col, k=k, width=width, top=True)
    return a, e

def merge(body, hands):
    a = body.cv.a.copy(); e = body.E.copy()
    m = hands.cv.a[..., 3] > 0
    a[m] = hands.cv.a[m]; e[m] = hands.E[m]
    return a, e

def shift_rows(a, e, row, dy):
    """move everything above sprite row `row` down by dy px (head sinks into the shoulders / nods)."""
    if dy == 0: return a, e
    a = a.copy(); e = e.copy()
    if dy > 0:
        top_a, top_e = a[:row].copy(), e[:row].copy()
        m = top_a[..., 3] > 0
        a[:row][m] = 0
        sa = np.zeros_like(top_a); se = np.zeros_like(top_e)
        sa[dy:], se[dy:] = top_a[:-dy], top_e[:-dy]
        reg_a, reg_e = a[:row + dy], e[:row + dy]
        mm = np.zeros(reg_a.shape[:2], bool); mm[:row] = sa[..., 3] > 0
        ext_a = np.zeros_like(reg_a); ext_a[:row] = sa; ext_e = np.zeros_like(reg_e); ext_e[:row] = se
        # rows that crossed into the torso
        ext_a[row:row + dy] = top_a[row - dy:row]; ext_e[row:row + dy] = top_e[row - dy:row]
        mm[row:row + dy] = top_a[row - dy:row, :, 3] > 0
        reg_a[mm] = ext_a[mm]; reg_e[mm] = ext_e[mm]
    else:
        d = -dy
        a[:row - d] = a[d:row].copy(); e[:row - d] = e[d:row].copy()
    return a, e

def lean_rows(a, e, lean, row0, row1):
    """lean the upper body: rows < row0 shift by `lean` px, rows row0..row1 interpolate to 0 (the seat stays)."""
    L = int(round(lean))
    if L == 0: return a, e
    out = np.zeros_like(a); oe = np.zeros_like(e)
    for y in range(a.shape[0]):
        s = L if y < row0 else int(round(L * (row1 - y) / max(1, row1 - row0))) if y < row1 else 0
        if s >= 0: out[y, s:], oe[y, s:] = a[y, :a.shape[1] - s], e[y, :a.shape[1] - s]
        else: out[y, :s], oe[y, :s] = a[y, -s:], e[y, -s:]
    return out, oe


def blue_hour(img, k=0.32):
    """after the paint montage: later light - pull the warm close shots toward the violet-blue of the dusk wide."""
    lum = img[..., :1] * 0.30 + img[..., 1:2] * 0.55 + img[..., 2:3] * 0.15
    tint = lum * np.array([0.62, 0.62, 1.05], np.float32)
    return (img * (1 - k) + tint * k).astype(np.float32)


class Pier:
    """the pier world in pixels: backgrounds (dusk 0 / 1), the old man's back + rod + line + bobber, birds."""
    def __init__(self, OW=1920, OH=1080):
        self.OW, self.OH = OW, OH
        self.rv0, self.rv1 = RP.RiverPier(0.0), RP.RiverPier(1.0)
        self.sc0 = OutdoorScene(self.rv0.bg, OW=OW, OH=OH)
        self.sc1 = OutdoorScene(self.rv1.bg, OW=OW, OH=OH)
        self.om = backs.old_fisher_back()
        self.bob, self.bobE = bob_far_water()
        self.fine, self.fineE = RP.bobber_fine()
        self.far, self.farE = RP.bobber_far()

    def bobber_xy(self, t, extra=0.0):
        bx, by = RP.BOBBER
        d = 0.6 * math.sin(2 * math.pi * t / 2.3) + extra
        return int(bx - 1), int(round(by - 5 + d))

    def rod_and_line(self, t, bobber=True, birds=True, bob_extra=0.0, line_to=None, dusk=0.0):
        cv = Canvas(480, 270); E = np.zeros((270, 480), np.float32)
        hx, hy = OM_X - self.om.ax + self.om.hand[0], OM_Y - self.om.ay + self.om.hand[1]
        tx, ty = ROD_TIP
        sway = 0.5 * math.sin(2 * math.pi * t / 3.1)
        lit = C('#f0b88a') if dusk < 0.5 else C('#b08aa0')
        n = 80
        for i in range(n + 1):
            u = i / n
            x = hx + (tx - hx) * u; y = hy + (ty - hy) * u + 7 * u * (1 - u) + sway * u * u
            cv.px(int(round(x)), int(round(y)), C('#2a1c22') if u < 0.75 else lit)
            if u < 0.3: cv.px(int(round(x)), int(round(y)) + 1, C('#2a1c22'))
            if u >= 0.75: E[int(round(y)), int(round(x))] = 0.6 * (1 - 0.5 * dusk)
        bx, by = self.bobber_xy(t, bob_extra)
        ex, ey = (bx + 1, by) if line_to is None else line_to
        x0, y0 = tx, ty + sway
        for i in range(61):
            u = i / 60
            x = x0 + (ex - x0) * u; y = y0 + (ey - y0) * u + 3 * u * (1 - u)
            if i % 2 == 0:
                cv.px(int(round(x)), int(round(y)), C('#f8e0c8')); E[int(round(y)), int(round(x))] = 0.5 * (1 - 0.4 * dusk)
        if bobber and line_to is None:
            h, w = self.bob.shape[:2]
            m = self.bob[..., 3] > 127
            cv.a[by:by + h, bx:bx + w][m] = self.bob[m]; E[by:by + h, bx:bx + w][m] = self.bobE[m]
        if birds: RP.draw_birds(cv, self.rv0.birds(t), C('#3a2a4a'))
        return cv, E

    def state(self, dusk=0.0, **over):
        st = outdoor_state('sunset', **RP.RP_STATE)
        lx, ly = RP.LANTERN
        st['points'] = [dict(x=lx, y=ly - 5, r=22.0, col=(1.0, 0.62, 0.30), k=(0.10 + 0.35 * dusk) * PF.flicker(self.t_now, 3, amp=0.10 * dusk), power=1.4)]
        st.update(over)
        return st

    t_now = 0.0
    def render(self, t, cam, mid, dusk=0.0, st=None, casters=(), bg_fx=None):
        rv, sc = (self.rv0, self.sc0) if dusk < 0.5 else (self.rv1, self.sc1)
        self.t_now = t
        st = st or self.state(dusk)
        g = rv.glitter(t)
        return sc.render(cam, st, mid, list(casters), frame=int(round(t * TL.FPS)), bg_patches=[(g[0], g[2], g[3], g[1])],
                         front_i=rv.front_index(t), bg_fx=bg_fx)


# ====================================================================== W / TWO / END (pixel, from behind)
class BackShot:
    def __init__(self, pier):
        self.p = pier

    def claude_sprite(self, t):
        """-> (rgba, E, x, y) top-left in world px, plus the foot y (for the caster).
        v2: W = walks in and STOPS two planks behind the old man (standing); END = seated, closer (CL_X_END)."""
        if t >= TL.T_END:
            s = backs.claude_back()
            return s.rgba, s.E, TL.CL_X_END - s.ax, TL.CL_SEAT - s.ay, TL.CL_SEAT
        q = PF.on_twos(t) if t >= TL.T_ARRIVE else t
        x, y, sc = TL.walk_pos(q)
        b = backs.claude_back_walk(TL.walk_phase(t), sit=0.0)
        a, e = b.rgba, b.E
        hdx = int(round(TL.w_head_dx(t)))
        if hdx: a, e = lean_rows(a, e, hdx, 45, 45)                  # the head turns a little toward the ping
        if t >= TL.T_ARRIVE and PF.breath_px(t, 3.4): a, e = shift_rows(a, e, 46, 1)
        if abs(sc - 1.0) > 1e-3:
            a = scale_nearest(a, sc); e = scale_nearest(e, sc)
            ax, ay = b.ax * sc, b.ay * sc
        else:
            ax, ay = b.ax, b.ay
        return a, e, int(round(x - ax)), int(round(y - ay)), y

    def raise_arm(self, mid, t, x, y, a):
        """END: Claude's right arm comes up beside his head holding the bobber against the evening sky."""
        k = ease_out3(ramp(t, TL.T_RAISE0, TL.T_RAISE1))
        if k <= 0: return
        h, w = a.shape[:2]
        sx, sy = x + w - 14, y + h - 12                        # shoulder: the top right corner of the torso
        ex, ey = sx + 4 + 2 * k, sy - 1 - 8 * k                 # hand: a short chibi arm (about as long as the standing one)
        cv = Canvas(480, 270)
        n = 10
        pts = [(sx + (ex - sx) * i / n, sy + (ey - sy) * i / n) for i in range(n + 1)]
        for (px_, py_) in pts: cv.rect(int(round(px_)) - 2, int(round(py_)) - 2, 5, 5, CL.TC_OUT)
        for (px_, py_) in pts: cv.rect(int(round(px_)) - 1, int(round(py_)) - 1, 3, 3, CL.TC_SH)
        hx, hy = int(round(ex)), int(round(ey))
        cv.rrect(hx - 3, hy - 3, 7, 6, CL.HAND_OUT, 2); cv.rect(hx - 2, hy - 2, 5, 4, CL.HAND_SH)
        f, fE = self.p.fine, self.p.fineE
        fh, fw = f.shape[:2]
        mid.put(f, hx - fw // 2, hy - fh + 3, 0, E=fE * 1.2)
        mid.put(cv.a, 0, 0, 0)

    def mid(self, t, dusk=0.0, bobber=True):
        mid = GLayer(480, 270)
        om = self.p.om
        mid.put(om.rgba, int(OM_X - om.ax), int(OM_Y - om.ay), 0, E=om.E)
        a, e, x, y, foot = self.claude_sprite(t)
        if t >= TL.T_RAISE0:          # the right hand leaves the deck: it is the one holding up the bobber
            a = a.copy(); a[50:, 41:] = 0
        mid.put(a, x, y, 0, E=e)
        if t >= TL.T_END: self.raise_arm(mid, t, x, y, a)
        if t >= TL.T_END:     # the bobber is in Claude's hand now: the line just hangs from the rod tip
            cv, E = self.p.rod_and_line(t, bobber=False, line_to=(ROD_TIP[0] + 2, ROD_TIP[1] + 14), dusk=dusk)
        else:
            cv, E = self.p.rod_and_line(t, bobber=bobber, dusk=dusk)
        mid.put(cv.a, 0, 0, 0, E=E)
        casters = [(a[..., 3] > 127, x, y, foot, 0.8)] if t < TL.T_END else []
        return mid, casters

    def frame(self, t, cam, dusk=0.0):
        mid, casters = self.mid(t, dusk)
        return self.p.render(t, cam, mid, dusk=dusk, casters=casters)


# ====================================================================== the side shots
SX_C, SX_O = 281, 346                     # Claude (seated, v2: a polite gap; +TL.SCOOT after the hand-over) / the old man
DECK_Y = 192                              # Claude's seat row = the pier's far edge
STOOL_Y = 174                             # the old man's seat (folding stool)
C_HEAD = (SX_C, DECK_Y - (CL.SIT_Y - CL.AY))      # Claude's head-top anchor
ROD_S_TIP = (432.0, 132.0)                # side shots: the rod tip (top right, just out of frame)
BOB_S = (382, 178)                        # side shots: the far bobber in the water, right of the old man
BUCKET_X, BUCKET_Y = TL.BUCKET_X, DECK_Y + 3        # the zinc bucket on the deck between them (bottom-left)

SIDE_CAM = (2.5, 289.0, 172.0)
CU_C_CAM = (3.5, 291.0, 175.5)
CU_O_CAM = (4.0, 342.0, 155.0)
INS_CAM = (5.0, 334.0, 184.0)

def side_state(pier, dusk=0.0, **over):
    st = pier.state(dusk, facing=0.30 + 0.08 * dusk, mid_amb=1.04 - 0.1 * dusk, shadow_k=0.0)
    if dusk > 0.5:     # the lantern stands on the deck to Claude's left (off-screen); v2: it flickers
        st['points'] = [dict(x=238.0, y=186.0, r=46.0, col=(1.0, 0.62, 0.30), k=0.55 * PF.flicker(pier.t_now, 5, amp=0.09), power=1.25)]
    st.update(over); return st


class Side:
    def __init__(self, pier):
        self.p = pier
        self.deck = {d: self.make_deck(d) for d in (0.0, 1.0)}
        self.stool = self.make_stool()
        self.bucket = RP.bucket_side()
        self.midges = PixelSwarm(center=(246, 152), spread=(12, 7), n=8, seed=4)
        self.midges2 = PixelSwarm(center=(404, 160), spread=(9, 6), n=6, seed=9)
        self.flies = PixelSwarm(center=(262, 166), spread=(60, 18), n=7, seed=12, kind='firefly')
        # occasional distant fish-jump rings (t, x, y): far water, never behind a face
        self.jumps = [(15.2, 214, 168), (27.9, 410, 172), (44.0, 404, 176), (58.6, 246, 174), (66.3, 228, 170), (73.1, 398, 174),
                      (97.0, 214, 172), (103.9, 412, 170), (108.8, 236, 168)]

    # ---------------------------------------------------------------- set pieces
    def make_deck(self, dusk):
        """the pier end, seen low from behind: planks converge toward the horizon, the far edge catches the sun."""
        cv = Canvas(480, 270); E = np.zeros((270, 480), np.float32)
        y0 = DECK_Y - 1
        vx, vy = 300.0, float(RP.HORIZON)
        base = [C('#7a4e48'), C('#6e4642'), C('#80544a')]
        gap, hi, lip = C('#2e1c26'), C('#c48660'), C('#f0b07a')
        if dusk > 0.5:
            base = [mix(c, C('#3c2a44'), 0.55) for c in base]
            gap, hi, lip = C('#1c1220'), mix(C('#c48660'), C('#5e3e5a'), 0.6), C('#b8786a')
        fb = (270 - vy)
        for y in range(y0, 270):
            f = (y - vy) / fb
            for x in range(160, 480):
                xb = vx + (x - vx) / f                     # x at the bottom row
                j = int(math.floor(xb / 30.0))
                fr = xb / 30.0 - j
                col = base[j % 3]
                if fr < 0.06 * (1 + (y - y0) / 60): col = gap
                elif y - y0 < 3: col = hi if y - y0 > 0 else lip
                elif fr > 0.85 and (y + j) % 9 == 0: col = mix(col, gap, 0.4)          # wood grain / nail rows
                cv.px(x, y, col)
            if y - y0 < 2: E[y, 160:] = 0.35 * (1 - 0.6 * dusk)
        # v2 detail: nail pairs where the planks cross the beams, a few knots, grain streaks, a worn path
        rng = np.random.default_rng(3)
        for yb in (y0 + 6, y0 + 19, y0 + 41, y0 + 72):
            f = (yb - vy) / fb
            for j in range(-6, 22):
                for dxn in (0.25, 0.7):
                    xb = (j + dxn) * 30.0
                    x = int(round(vx + (xb - vx) * f))
                    if 160 <= x < 480 and yb < 270:
                        cv.px(x, yb, C('#2a1a22') if dusk < 0.5 else C('#140c16'))
                        if yb + 1 < 270: cv.px(x, yb - 1, mix(cv.a[yb - 1, x], C('#d8a07a'), 0.35) if dusk < 0.5 else cv.a[yb - 1, x])
        for (x, y) in ((258, 197), (321, 200), (372, 196), (226, 214), (402, 230)):
            cv.px(x, y, C('#3a2630')); cv.px(x + 1, y, C('#4a3038'))
        for _ in range(70):                                    # grain: short darker dashes along the plank direction
            yb = int(rng.uniform(y0 + 3, 268)); xb = rng.uniform(-60, 520)
            f = (yb - vy) / fb
            ln = int(2 + 4 * f)
            for i in range(ln):
                yy = yb + i; xx = int(round(vx + (xb - vx) * ((yy - vy) / fb)))
                if 160 <= xx < 480 and yy < 270: cv.a[yy, xx, :3] = (cv.a[yy, xx, :3] * 0.9).astype(np.uint8)
        yy, xx = np.mgrid[0:270, 0:480]
        wear = (np.exp(-((xx - 300.0) / 70.0) ** 2 - ((yy - (y0 + 10.0)) / 14.0) ** 2) * 0.10)
        wear[:y0] = 0; wear[:, :160] = 0
        cv.a[..., :3] = np.clip(cv.a[..., :3] * (1 + wear[..., None]), 0, 255).astype(np.uint8)
        return cv.a, E

    def make_stool(self):
        cv = Canvas(24, 24)
        wood, wood_d, can, can_d = C('#5a3a2c'), C('#3a2420'), C('#5e6a52'), C('#46503e')
        cv.line(3, 3, 19, 22, wood_d); cv.line(4, 3, 20, 22, wood)
        cv.line(20, 3, 4, 22, wood_d); cv.line(19, 3, 3, 22, wood)
        cv.rect(0, 0, 24, 3, can); cv.hline(0, 2, 24, can_d); cv.hline(1, 0, 22, C('#76826a'))
        # v2: the canvas sags between the rails (folds), a hem flap hangs below the front rail
        for x in (6, 11, 17): cv.px(x, 1, can_d)
        cv.hline(3, 3, 18, can_d); cv.hline(6, 4, 12, C('#3c4434'))
        cv.px(2, 3, can); cv.px(21, 3, can)
        cv.rect(0, 0, 1, 3, C('#2e2420')); cv.rect(23, 0, 1, 3, C('#2e2420'))
        return cv.a

    # ---------------------------------------------------------------- characters
    def claude_sprite(self, d, sun_side=1, rim_k=0.75):
        """d: face arms look glow drop bob nod lean dx  + v2 performance keys: pose ('sit'|'stand') phase tilt hdy ant
        kick squash spark y (extra px, e.g. a hop)."""
        pose = d.get('pose', 'sit')
        pr = CL.draw(face=d.get('face', 'normal'), arms=d.get('arms', 'down'), look=d.get('look', (0, 0)),
                     glow=d.get('glow', 1.0), legs=True, pose=pose, led='off', phase=d.get('phase', 0),
                     tilt=d.get('tilt', 0.0), head_dy=d.get('hdy', 0), ant=d.get('ant', (0, 0)), leg_kick=d.get('kick', 0),
                     spark_k=d.get('spark', 1.0))
        a, e = merge(pr.body, pr.hands)
        drop = d.get('drop', 0) - d.get('bob', 0) + d.get('nod', 0)
        a, e = shift_rows(a, e, CL.torso_box()[1] + 1, drop)
        if d.get('lean', 0): a, e = lean_rows(a, e, d['lean'], 50, CL.SIT_Y - 2)
        ox = oy = 0
        if abs(d.get('squash', 0.0)) > 1e-3:
            a, e, ox, oy = PF.squash_about(a, e, d['squash'], CL.AX, CL.SIT_Y if pose == 'sit' else CL.FOOT_Y - 1)
        a, e = bake_rim(a, e, sun_side, k=rim_k)
        bl = d.get('bounce', (255, 168, 112, 0.13))
        if bl: a = PF.bounce_light(a, bl[:3], bl[3], rows=34)
        yoff = (CL.SIT_Y - CL.FOOT_Y + 1) if pose == 'stand' else 0
        return a, e, int(C_HEAD[0] - pr.ax) + ox, int(C_HEAD[1] - pr.ay) + oy + yoff + int(round(d.get('y', 0)))

    def old_face(self, t):
        face = 'normal'
        for ln in TL.OLD_LINES:
            if ln['t0'] <= t < ln['t_end']:
                n = sum(1 for tc in ln['times'] if t >= tc)
                ch = ln['zh'][max(0, n - 1)]
                face = 'talk' if (int((t - ln['t0']) * 7) % 2 == 0 and ch not in '，。…？！、') else ('soft' if ln['face'] == 'soft' else 'normal')
                return face
            if ln['t_end'] <= t < ln['t_end'] + 2.2:
                face = {'smile': 'smile', 'soft': 'soft', 'down': 'normal'}.get(ln['face'], 'normal')
        if TL.T_SMILE_O <= t < TL.T_CU_H: face = 'smile'
        if TL.T_LOOK_BADGE <= t < TL.T_BADGE + 0.2: face = 'down'
        if TL.L_REST['t0'] - 0.3 <= t < TL.T_CU_C2: face = 'soft' if face == 'normal' else face
        if face in ('normal', 'soft') and blink_at(t, TL.BLINKS_O, 0.14): face = 'blink'
        return face

    def old_sprite(self, t, arms='hold', lean=0.0, rim_k=0.7, breathe=True, od=None):
        """od (v2 performance): body ('claude' = 3/4 toward Claude, v1 default | 'water' = 3/4 toward the water / rod),
        v = screen head direction (person.head_dir; keep within ~90 deg of the body), face (override),
        shake (px, laughing shoulders), breath ('v2' = perform.breath_px)."""
        od = od or {}
        flip = od.get('body', 'claude') == 'claude'
        hd = P.head_dir(od['v']) if 'v' in od else {}
        s = P.draw(OLD, pose='sit', arms=arms, face=od.get('face') or self.old_face(t), flip=flip, arm_ang=od.get('arm_ang'), **hd)
        a, e = s.rgba, s.E
        if lean: a, e = lean_rows(a, e, lean, 46, s.seat_y - 1)
        if od.get('shake'): a, e = PF.shake_rows(a, e, 0, s.seat_y - 4, int(od['shake']))
        a, e = bake_rim(a, e, -1, k=rim_k)
        bl = od.get('bounce', (255, 168, 112, 0.12))
        if bl: a = PF.bounce_light(a, bl[:3], bl[3], rows=40)
        if od.get('breath') == 'v2': b = PF.breath_px(t, 4.3, 0.3) if breathe else 0
        else: b = 1 if breathe and (t % 4.3) > 3.6 else 0
        x, y = SX_O - s.ax, STOOL_Y - s.seat_y + b
        hands = {k: (x + hx + (lean if hy < s.seat_y - 8 else 0), y + hy) for k, (hx, hy) in s.hands.items()}
        return a, e, x, y, hands

    # ---------------------------------------------------------------- rod, line, far bobber, hook
    def rod(self, cv, E, hand, t, dusk):
        hx, hy = hand
        tx, ty = ROD_S_TIP
        sway = 0.6 * math.sin(2 * math.pi * t / 3.3)
        dark, lit = C('#22161c'), (C('#f0b88a') if dusk < 0.5 else C('#9a7a94'))
        bx, by = hx - 7, hy + 8                                    # butt end on his lap
        n = 120
        for i in range(n + 1):
            u = i / n
            x = bx + (tx - bx) * u; y = by + (ty - by) * u + 5 * u * (1 - u) + sway * u * u
            cv.px(int(round(x)), int(round(y)), dark if u < 0.8 else lit)
            if u < 0.35: cv.px(int(round(x)) + 1, int(round(y)), dark)
            if u >= 0.8 and 0 <= int(round(y)) < 270 and 0 <= int(round(x)) < 480: E[int(round(y)), int(round(x))] = 0.5 * (1 - 0.5 * dusk)
        return tx, ty + sway

    def line(self, cv, E, p0, p1, sag=4.0, dusk=0.0):
        (x0, y0), (x1, y1) = p0, p1
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        col = C('#f8e0c8') if dusk < 0.5 else C('#c8b0c8')
        for i in range(0, n + 1):
            u = i / n
            x = x0 + (x1 - x0) * u; y = y0 + (y1 - y0) * u + sag * 4 * u * (1 - u)
            if i % 2 == 0 and 0 <= int(round(y)) < 270 and 0 <= int(round(x)) < 480:
                cv.px(int(round(x)), int(round(y)), col); E[int(round(y)), int(round(x))] = 0.45 * (1 - 0.4 * dusk)

    def far_bobber(self, cv, E, x, y, under=True):
        a, e = self.p.far, self.p.farE
        rows = 5 if under else 7
        for j in range(rows):
            for i in range(3):
                if a[j, i, 3] > 0:
                    cv.px(x - 1 + i, y - 5 + j, tuple(int(v) for v in a[j, i])); E[y - 5 + j, x - 1 + i] = e[j, i]
        if under: cv.hline(x - 2, y, 5, C('#f8d8b8'))

    def hook(self, cv, x, y):
        """an empty hook dangling below (x, y): a short line, a bent silver hook."""
        cv.vline(x, y, 4, C('#e8d8d0'))
        for (dx, dy) in ((0, 4), (0, 5), (1, 6), (2, 5), (2, 4)):
            cv.px(x + dx, y + dy, C('#d8d8e0'))

    # ---------------------------------------------------------------- atmosphere
    def jump_rings(self, cv, E, t, dusk):
        """a fish jumps somewhere far off: a 2-frame splash pixel, then two widening flat rings (1.4 s)."""
        col = C('#ffe0c0') if dusk < 0.5 else C('#b8a8d8')
        for (tj, x, y) in self.jumps:
            u = t - tj
            if not 0 <= u < 1.4: continue
            if u < 0.12: cv.px(x, y - 2, col); cv.px(x, y - 1, col); E[y - 2, x] = 0.5
            for (d, sp) in ((0.0, 9.0), (0.25, 7.0)):
                v = u - d
                if v <= 0: continue
                r = 1.5 + sp * v; al = 1 - v / (1.4 - d)
                if al <= 0.05: continue
                n = int(2 * math.pi * r) + 2
                for i in range(n):
                    if (i + int(v * 30)) % 3 == 0: continue
                    ang = 2 * math.pi * i / n
                    xx, yy = int(round(x + r * math.cos(ang))), int(round(y + 0.3 * r * math.sin(ang)))
                    if 0 <= yy < DECK_Y - 1 and 0 <= xx < 480:
                        cv.a[yy, xx] = (*col[:3], int(200 * al)); E[yy, xx] = max(E[yy, xx], 0.3 * al)

    def jump_rings_bg(self, im, cam, t, dusk):
        """the rings drawn INTO the background (output res, world-pixel blocks) so pixel_soft softens them with the
        water - crisp rings on a soft river read as garbage in the close-ups."""
        cv = Canvas(480, 270); E = np.zeros((270, 480), np.float32)
        self.jump_rings(cv, E, t, dusk)
        ys, xs = np.nonzero(cv.a[..., 3])
        if not len(ys): return im
        im = im.copy(); s = cam.zoom * 4.0
        for (y, x) in zip(ys, xs):
            X0, Y0 = cam.w2o(x, y)
            X0, Y0 = int(round(X0)), int(round(Y0))
            if -s < X0 < im.shape[1] and -s < Y0 < im.shape[0]:
                al = cv.a[y, x, 3] / 255.0 * 0.8
                sl = im[max(0, Y0):max(0, Y0 + int(s)), max(0, X0):max(0, X0 + int(s))]
                sl[:] = sl * (1 - al) + np.array(cv.a[y, x, :3], np.float32) / 255.0 * 1.15 * al
        return im

    def contact(self, mid, a, x, y, floor=DECK_Y - 2, col=(40, 22, 30), alpha=190):
        """1 px contact shadow under a sprite's lowest pixels (only where they reach the deck)."""
        sh = PF.contact_shadow(a, col=col, alpha=alpha)
        if sh is None: return
        patch, dx, dy = sh
        if y + dy >= floor: mid.put(patch, x + dx, y + dy, 0)

    # ---------------------------------------------------------------- the shot
    def frame(self, t, cam_def, dusk=0.0, cd=None, od=None, who=('c', 'o'), blur=6.0, extra=None, under=None, atmo=True,
              bucket=True, shake=(0.0, 0.0)):
        """cd / od: Claude / old-man dicts (face, arms, look, lean ...).  extra(mid_cv, E, info) draws props on top.
        v2: the bucket + contact shadows by default, midges (day) / fireflies (dusk), far fish-jump rings, camera hits."""
        z, cx, cy = cam_def
        cam = Cam(z, cx + shake[0], cy + shake[1], W=480, H=270)
        self.p.t_now = t
        mid = GLayer(480, 270)
        dk, dE = self.deck[1.0 if dusk > 0.5 else 0.0]
        props = Canvas(480, 270); pE = np.zeros((270, 480), np.float32)
        info = {}
        if 'o' in who:
            od = od or {}
            a, e, x, y, hands = self.old_sprite(t, od.get('arms', 'hold'), od.get('lean', 0.0), od=od)
            info['old_hands'] = hands
            rh = hands[0]
            if od.get('body', 'claude') == 'water' and od.get('arm_ang') and 0 in od['arm_ang']:
                rh = (hands[1][0] - 14, hands[1][1] + 1)          # the near hand is busy: the rod stays in the other one
            tip = self.rod(props, pE, rh, t, dusk)
            info['tip'] = tip
            if od.get('line', 'water') == 'water':
                bx, by = BOB_S[0], int(round(BOB_S[1] + 0.6 * math.sin(2 * math.pi * t / 2.3)))
                self.line(props, pE, tip, (bx, by - 5), sag=6, dusk=dusk)
                self.far_bobber(props, pE, bx, by)
            elif od.get('line') == 'to':
                p1 = od['line_to']
                self.line(props, pE, tip, p1, sag=od.get('sag', 3), dusk=dusk)
            elif od.get('line') == 'hang':
                self.line(props, pE, tip, (tip[0] - 3, tip[1] + 30), sag=1, dusk=dusk)
        if 'c' in who:
            cd = cd or {}
            if 'bounce' not in cd and dusk > 0.5: cd = dict(cd, bounce=(150, 120, 210, 0.08))
            ca, ce, cx_, cy_ = self.claude_sprite(cd, rim_k=0.75 if dusk < 0.5 else 0.3)
            cx_ += int(round(cd.get('dx', 0)))
            info['claude_xy'] = (cx_ - int(round(cd.get('dx', 0))), cy_)
        mid.put(dk, 0, 0, 0, E=dE)
        if bucket:
            ba, be = self.bucket
            bxp = BUCKET_X if not callable(bucket) else bucket(t)
            sh = np.zeros((1, ba.shape[1] + 2, 4), np.uint8); sh[..., :3] = (46, 26, 32); sh[..., 3] = 255
            mid.put(sh, bxp - 1, BUCKET_Y, 0)
            mid.put(ba if dusk < 0.5 else (ba * np.array([0.80, 0.76, 0.88, 1.0])).astype(np.uint8), bxp, BUCKET_Y - ba.shape[0], 0, E=be)
        if under is not None: under(mid, info)
        if 'o' in who:
            self.contact(mid, self.stool, SX_O - 13, STOOL_Y)
            mid.put(self.stool, SX_O - 13, STOOL_Y, 0)
            mid.put(a, x, y, 0, E=e)
        if 'c' in who:
            self.contact(mid, ca, cx_, cy_)
            mid.put(ca, cx_, cy_, 0, E=ce)
        if extra is not None: extra(props, pE, info)
        if atmo:
            if dusk < 0.5: self.midges.draw(props, pE, t); self.midges2.draw(props, pE, t + 3.0, 0.8)
            else: self.flies.draw(props, pE, t)
        mid.put(props.a, 0, 0, 0, E=pE)
        st = side_state(self.p, dusk)
        cell = max(4, int(round(4 * z)))
        fx = {'dof': lambda im: dof(im, blur), 'crisp': None,
              'pixel': lambda im: pixel_soft(im, cell, sigma=blur / cell * 1.6)}[BG_MODE]
        if atmo and fx is not None:
            fx0 = fx; fx = lambda im: fx0(self.jump_rings_bg(im, cam, t, dusk))
        img = self.p.render(t, cam, mid, dusk=dusk, st=st, bg_fx=fx)
        if dusk > 0.5: img = blue_hour(img)
        return img, cam, info


# ====================================================================== flat inserts (bucket POV, badge)
class Flat:
    def __init__(self, pier, OW=1920, OH=1080):
        self.p = pier
        self.fs = FlatScene(OW=OW, OH=OH)
        self.bucket = self.make_bucket()
        self.badge = self.make_badge()

    def make_bucket(self):
        H, W = 270, 480
        cv = Canvas(W, H); E = np.zeros((H, W), np.float32)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        # planks (seen from above, running up-right) + gaps
        u = (xx * 0.94 + yy * 0.34) / 34.0
        j = np.floor(u).astype(int); fr = u - j
        pal = np.array([C('#7a4e48')[:3], C('#6c4440')[:3], C('#845850')[:3]], np.float32)
        col = pal[j % 3]
        grain = (np.sin(xx * 0.31 + j * 1.7) * np.sin(yy * 0.05 + j) > 0.82)
        col[grain] = col[grain] * 0.86
        col[fr < 0.07] = np.array(C('#2e1c26')[:3], np.float32)
        a = cv.a; a[..., :3] = col.astype(np.uint8); a[..., 3] = 255
        cx, cy, rx, ry = 236.0, 140.0, 124.0, 82.0
        def ell(rx_, ry_, dy=0.0): return ((xx - cx) / rx_) ** 2 + ((yy - cy - dy) / ry_) ** 2
        # the bucket's outer wall below the rim (a darker zinc band), its shadow on the planks to the lower left
        sh = (((xx - cx + 14) / (rx + 6)) ** 2 + ((yy - cy - 24) / (ry + 8)) ** 2) <= 1
        a[sh, :3] = (a[sh, :3] * 0.55).astype(np.uint8)
        wall = (((xx - cx) / rx) ** 2 + ((yy - cy - 14) / ry) ** 2 <= 1) & (yy > cy)
        a[wall] = C('#6a707c'); a[wall & (xx > cx + 40)] = C('#7e8592')
        rim = ell(rx, ry) <= 1
        a[rim] = C('#aab0ba')
        inner = ell(rx - 7, ry - 5) <= 1
        a[rim & ~inner & (yy < cy - ry * 0.55)] = C('#d8dce2')               # rim highlight, far side
        a[rim & ~inner & (xx > cx + rx * 0.7)] = C('#e8c0a0')                # sun on the right rim
        # inner wall (far half visible) then the water surface
        a[inner] = C('#4e5462')
        a[inner & (yy > cy)] = C('#5c6270')
        water = ell(rx - 14, ry - 14, dy=8) <= 1
        k = np.clip((yy - (cy - ry + 20)) / (2 * ry - 28), 0, 1)
        wc = (np.array(C('#f0a07a')[:3]) * (1 - k[..., None]) + np.array(C('#7a5070')[:3]) * k[..., None])
        a[water, :3] = wc[water].astype(np.uint8)
        E[water] = 0.45 * (1 - k[water])
        # sky reflection: a cloud streak + the sun's glint, a few ripple arcs, one floating leaf
        st = water & (np.abs((yy - cy + 18) + (xx - cx) * 0.12) < 3) & (np.abs(xx - cx + 10) < 70)
        a[st] = C('#ffc89a'); E[st] = 0.6
        gl = water & (((xx - cx - 46) / 9.0) ** 2 + ((yy - cy + 26) / 4.0) ** 2 <= 1)
        a[gl] = C('#fff2d0'); E[gl] = 1.0
        for r in (22.0, 34.0):
            ring = water & (np.abs(np.sqrt(((xx - cx + 30) / 1.6) ** 2 + (yy - cy - 18) ** 2) - r) < 0.6) & ((xx + yy).astype(int) % 3 != 0)
            a[ring] = C('#d89a86')
        leaf = [(0, 0), (1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (2, 1), (3, 1), (0, 2), (1, 2), (2, 2)]
        for (dx, dy) in leaf:
            cv.px(int(cx) - 40 + dx, int(cy) + 22 + dy, C('#c88a3a'))
        cv.px(int(cx) - 37, int(cy) + 21, C('#8a5a2a'))
        # wire handle lying over the rim on the left
        for i in range(60):
            uu = i / 59; ang = math.pi * (0.55 + 0.6 * uu)
            hx_, hy_ = cx + (rx + 6) * math.cos(ang), cy + (ry + 18) * math.sin(ang) + 4
            cv.px(int(hx_), int(hy_), C('#3a3a44')); cv.px(int(hx_), int(hy_) - 1, C('#c8ccd4'))
        return a, E, (cx, cy, rx, ry)

    def make_badge(self):
        H, W = 270, 480
        cv = Canvas(W, H); E = np.zeros((H, W), np.float32)
        yy, xx = np.mgrid[0:H, 0:W]
        knit = ((xx // 3 + yy // 4) % 2 == 0)
        a = cv.a; a[..., 3] = 255
        a[..., :3] = np.array(CL.TC[:3], np.uint8); a[knit, :3] = np.array(mix(CL.TC, CL.TC_SH, 0.35)[:3], np.uint8)
        a[(yy % 8 == 0), :3] = (a[(yy % 8 == 0), :3] * 0.92).astype(np.uint8)
        # the lanyard: two blue straps from the top meeting at the clip
        for side in (-1, 1):
            for y in range(0, 92):
                x0 = 240 + side * (110 - y * 1.05)
                cv.rect(int(x0) - 7, y, 14, 1, CL.LAN_SH); cv.rect(int(x0) - 5, y, 10, 1, CL.LAN)
                if y % 6 < 2: cv.px(int(x0), y, C('#6a96f0'))
        cv.rect(228, 84, 24, 16, C('#9a6a2a')); cv.rect(230, 86, 20, 12, CL.METAL); cv.hline(231, 87, 18, C('#ffe0a0'))
        # the card
        x0, y0, w, h = 150, 98, 180, 116
        cv.rrect(x0 + 4, y0 + 5, w, h, (60, 24, 30, 255), 8)
        cv.rrect(x0, y0, w, h, C('#3b3042'), 8); cv.rrect(x0 + 2, y0 + 2, w - 4, h - 4, C('#ffffff'), 7)
        cv.rect(x0 + 2, y0 + 10, w - 4, 20, C('#d97757')); cv.rect(x0 + 2, y0 + 28, w - 4, 2, C('#b5583c'))
        cv.rect(x0 + 80, y0 + 6, 20, 5, C('#3b3042'))                     # punched slot
        cv.text(x0 + 10, y0 + 13, 'STAFF  ·  员工证', C('#fff4ea'), 'zh10')
        # logo (scaled 4x) on the left
        lg = Canvas(13, 13); lE = np.zeros((13, 13), np.float32)
        CL.draw_logo(lg, lE, 6, 6, 1.0)
        big = scale_nearest(lg.a, 4.0)
        m = big[..., 3] > 0
        a[y0 + 40:y0 + 40 + big.shape[0], x0 + 12:x0 + 12 + big.shape[1]][m] = big[m]
        E[y0 + 40:y0 + 40 + big.shape[0], x0 + 12:x0 + 12 + big.shape[1]][m] = 0.5
        # name (zh12 at 2x) + role
        tm = Canvas(80, 16); tm.text(0, 0, 'Claude', C('#3b3042'), 'zh12')
        t2 = scale_nearest(tm.a, 2.0); m2 = t2[..., 3] > 0
        a[y0 + 42:y0 + 42 + t2.shape[0], x0 + 74:x0 + 74 + t2.shape[1]][m2] = t2[m2]
        cv.text(x0 + 75, y0 + 74, 'AI 助手  ASSISTANT', C('#8a7a88'), 'zh10')
        for i in range(24):                                              # a little barcode
            if (i * 7) % 5 < 3: cv.vline(x0 + 75 + i * 3, y0 + 92, 12, C('#3b3042'))
        return a, E

    def render(self, t, which, cam, dusk):
        st = self.p.state(dusk)
        fs = self.fs
        if which == 'bucket':
            alb, E, _ = self.bucket
            L = fs.ambient((0.95, 0.72, 0.66), 0.82, top=1.05, bottom=0.85) + fs.pool(400, 40, 260, 170, (1.0, 0.72, 0.45), 0.45)
        else:
            alb, E = self.badge
            L = fs.ambient((0.62, 0.50, 0.70), 0.62, top=0.9, bottom=0.75) + fs.pool(60, 220, 260, 190, (1.0, 0.62, 0.30), 0.75)
        return fs.render(cam, alb, L, st['grade'], E=E, frame=int(round(t * TL.FPS)))


# ====================================================================== ECHO: the bobber held up to the last light
class Echo:
    """close, low: Claude's hand (from the lower left, backlit) holds the fine bobber up against the afterglow; the
    little sun dot painted on its white band sits right beside the last sliver of the real sun on the far hills."""
    CAM = (6.0, 314.0, 136.0)
    DOT = (310, 139)                       # where the painted sun dot sits (world)
    SUN = (322.0, 141.0)                   # the last sliver (top of the set sun, just above the hill line)

    def __init__(self, pier):
        self.p = pier
        self.flies = PixelSwarm(center=(296, 150), spread=(26, 8), n=4, seed=21, kind='firefly')

    def sliver(self, img, cam, t):
        X, Y = cam.w2o(*self.SUN)
        s = cam.zoom * 4.0
        yy, xx = np.ogrid[0:img.shape[0], 0:img.shape[1]]
        k = 0.92 + 0.08 * math.sin(t * 1.7)
        disc = (((xx - X) / (4.5 * s)) ** 2 + ((yy - Y - 0.5 * s) / (2.6 * s)) ** 2 <= 1) & (yy < Y)
        img = img * (1 - 0.18 * np.exp(-(((xx - X) / (30 * s)) ** 2 + ((yy - Y + 4 * s) / (8 * s)) ** 2)))[..., None]
        img[disc] = np.array([1.5, 1.2, 0.75], np.float32) * k
        g = np.exp(-(((xx - X) / (10 * s)) ** 2 + ((yy - Y) / (3 * s)) ** 2)) * 0.25 * k
        return img + g[..., None] * np.array([1.0, 0.7, 0.4], np.float32)

    def frame(self, t):
        q = PF.on_twos(t)
        u = ease_io(ramp(t, TL.T_ECHO, TL.DUR))
        z, cx, cy = self.CAM
        cam = Cam(z * (1 + 0.04 * u), cx, cy - 0.6 * u, W=480, H=270)
        mid = GLayer(480, 270)
        cv = Canvas(480, 270); E = np.zeros((270, 480), np.float32)
        a, e = self.p.fine, self.p.fineE
        h, w = a.shape[:2]
        sway = int(round(0.5 * math.sin(2 * math.pi * q / 3.0)))
        X, Y = self.DOT[0] - 4, self.DOT[1] - 8 + (1 if PF.breath_px(q, 3.8) else 0)
        # the arm + mitten, backlit (dark, a warm rim on the top edge)
        dark = mix(CL.TC_SH, C('#2a1830'), 0.55); dout = mix(CL.TC_OUT, C('#140a18'), 0.5)
        hx, hy = X + 4 + sway, Y + h - 2
        sx, sy = hx - 30, hy + 26
        n = 24
        for i_ in range(n + 1):
            v = i_ / n; px_, py_ = sx + (hx - sx) * v, sy + (hy - sy) * v
            cv.rect(int(round(px_)) - 3, int(round(py_)) - 3, 7, 7, dout)
        for i_ in range(n + 1):
            v = i_ / n; px_, py_ = sx + (hx - sx) * v, sy + (hy - sy) * v
            cv.rect(int(round(px_)) - 2, int(round(py_)) - 2, 5, 5, dark)
            cv.px(int(round(px_)) + 1, int(round(py_)) - 2, mix(dark, C('#ff9a6a'), 0.55))
        m = a[..., 3] > 0
        cv.a[Y:Y + h, X + sway:X + sway + w][m] = a[m]; E[Y:Y + h, X + sway:X + sway + w][m] = e[m] * 0.35
        hand_d, hand_o = mix(CL.HAND_SH, C('#3a2a44'), 0.5), mix(CL.HAND_OUT, C('#140a18'), 0.4)
        cv.rrect(hx - 4, hy - 2, 9, 7, hand_o, 3); cv.rrect(hx - 3, hy - 1, 7, 5, hand_d, 2)
        cv.hline(hx - 2, hy - 1, 5, mix(hand_d, C('#ffc8a0'), 0.6))                 # the rim of light on the knuckles
        mid.put(cv.a, 0, 0, 0, E=E)
        st = self.p.state(1.0, haze_k=0.12)
        cell = max(4, int(round(4 * cam.zoom)))
        fx = lambda im: pixel_soft(im, cell, sigma=14.0 / cell * 1.6)
        img = self.p.render(t, cam, mid, dusk=1.0, st=st, bg_fx=fx)
        img = blue_hour(img, 0.18)
        # the last sliver of the sun on the hill line: world-pixel blocks, softened a touch, added after the grade
        sl = np.zeros(img.shape[:2], np.float32)
        s = cam.zoom * 4.0
        for (dx, dy, k) in ((-3, -1, 0.7), (-2, -1, 1), (-1, -1, 1), (0, -1, 1), (1, -1, 1), (2, -1, 1), (3, -1, 0.7),
                            (-4, 0, 0.8), (-3, 0, 1), (-2, 0, 1), (-1, 0, 1), (0, 0, 1), (1, 0, 1), (2, 0, 1), (3, 0, 1), (4, 0, 0.8),
                            (-1, -2, 0.55), (0, -2, 0.7), (1, -2, 0.55)):
            X0, Y0 = cam.w2o(self.SUN[0] + dx, self.SUN[1] - 1 + dy)
            X0, Y0 = int(round(X0)), int(round(Y0))
            sl[max(0, Y0):max(0, Y0 + int(round(s))), max(0, X0):max(0, X0 + int(round(s)))] = k
        sl = cv2.GaussianBlur(sl, (0, 0), s * 0.35)
        Xs, Ys = cam.w2o(self.SUN[0] + 0.5, self.SUN[1] - 1.0)
        yy, xx = np.ogrid[0:img.shape[0], 0:img.shape[1]]
        r2 = (xx - Xs) ** 2 + ((yy - Ys) * 1.6) ** 2
        glow = (np.exp(-r2 / (2 * (s * 4.5) ** 2)) * 0.8).astype(np.float32)
        near = np.exp(-r2 / (2 * (s * 14.0) ** 2)).astype(np.float32)
        kf = 0.95 + 0.05 * math.sin(t * 1.7)
        img = img * (0.80 + 0.20 * near[..., None])                     # the sky dims away from the last light
        img = img * (1 - 0.9 * sl[..., None]) + sl[..., None] * np.array([1.3, 0.92, 0.48], np.float32) * kf
        return img + glow[..., None] * np.array([0.9, 0.55, 0.28], np.float32) * 0.9


# ====================================================================== ACT IV
class Act4:
    def __init__(self, OW=1920, OH=1080, only=None):
        mk = lambda n: only is None or n in only
        self.OW, self.OH = OW, OH
        self.pier = Pier(OW, OH)
        self.back = BackShot(self.pier)
        self.side = Side(self.pier)
        self.flat = Flat(self.pier, OW, OH)
        self.pv = PV.PaintV2(OW, OH, toggle_ui=False, t_click=-10.0, fade_out=False) if mk('PAINT') else None
        self.card_cache = {}
        self.echo = Echo(self.pier)
        E = edit.Edit()
        E.add('W', 0.0, self.f_w)
        E.add('SO', TL.T_SO, self.f_so)
        E.add('BKT', TL.T_BKT, self.f_bkt)
        E.add('SIDE2', TL.T_SIDE2, self.f_side2)
        E.add('CU_OR', TL.T_CU_OR0, self.f_cu_or)
        E.add('SIDE2B', TL.T_CU_OR1, self.f_side2)
        E.add('CU_C1', TL.T_CU_C1, self.f_cu_c1)
        E.add('CU_O', TL.T_CU_O, self.f_cu_o)
        E.add('CU_CR', TL.T_CU_CR, self.f_cu_cr)
        E.add('CU_OB', TL.T_CU_OB, self.f_cu_ob)
        E.add('INS', TL.T_INS, self.f_ins)
        E.add('CU_C3', TL.T_CU_C3, self.f_cu_c3)
        E.add('INS2', TL.T_INS2, self.f_ins2)
        E.add('CU_O2', TL.T_CU_O2, self.f_cu_o2)
        E.add('CU_C2', TL.T_CU_C2, self.f_cu_c2)
        E.add('PAINT', TL.T_PAINT, self.f_paint)
        E.add('INS_D', TL.T_INS_D, self.f_ins_d, kind='dissolve', d=TL.D_INS_D_DISS)
        E.add('SIDE_H', TL.T_SIDE_H, self.f_side_h)
        E.add('BADGE', TL.T_BADGE, self.f_badge)
        E.add('SIDE_H2', TL.T_SIDE_H2, self.f_side_h)
        E.add('CU_H', TL.T_CU_H, self.f_cu_h)
        E.add('END', TL.T_END, self.f_end, kind='dissolve', d=TL.D_END_DISS)
        E.add('ECHO', TL.T_ECHO, self.f_echo)
        E.end(TL.DUR)
        self.edit = E

    # ---------------------------------------------------------------- UI
    def ui_common(self, cv, t):
        a = TL.hud_alpha(t)
        if a > 0:
            s, tt = TL.clock(t)
            flash = max(0.0, 1 - (t - tt) / 0.35) if tt > 0 else 0.0
            if t >= TL.T_CLOCK_STOP: flash = max(flash, 1 - (t - TL.T_CLOCK_STOP) / 0.3)
            ui.hud_time(cv, 8, 8, s, day='周六', day_en='SAT', alpha=a, flash=flash)
        k, al, which = TL.note_k(t)
        if which:
            ui.hud_notify(cv, 8, 40, '工作群', '3 条新消息' if which == 1 else '新消息', k=k, alpha=al * max(a, 0.0))
        if t < TL.T_PAINT or t >= TL.T_INS_D:
            ui.narration(cv, t, TL.BOXES)

    def card(self, t):
        crack = ramp(t, TL.T_CRACK, TL.T_SHATTER)
        return ui.optimizer_card(t, TL.card_rows(t), rate_k=ramp(t, TL.T_RATE, TL.T_RATE + 0.3), crack=crack)

    def ui_card(self, cv, t):
        if t < TL.T_CARD_IN: return
        if t < TL.T_SHATTER:
            k = TL.card_in(t)
            a = self.card(t)
            if k < 1:
                ui.blit_scaled(cv, a, TL.CARD_X + a.shape[1] // 2, TL.CARD_Y + a.shape[0] // 2, 0.6 + 0.4 * k, alpha=k)
            else:
                jx = int(round(2 * math.sin(t * 90))) if TL.T_CRACK <= t else 0      # the hit shakes it
                cv.blit(a, TL.CARD_X + jx, TL.CARD_Y)
            return
        a = self.card(TL.T_SHATTER)
        age = t - TL.T_SHATTER
        ui.shatter(cv, a, TL.CARD_X, TL.CARD_Y, age, TL.CARD_FLOOR, seed=3)
        for (th, xh) in self.hits():
            u = age - th
            if 0 <= u < 0.5:
                w = int(1 + 6 * u); al = 1 - u / 0.5
                cv.hline(int(xh) - w, TL.CARD_FLOOR + 1, 2 * w + 1, (255, 240, 210, int(170 * al)))

    def hits(self):
        if 'hits' not in self.card_cache:
            hs = ui.shatter_hits(self.card(TL.T_SHATTER), TL.CARD_X, TL.CARD_Y, TL.CARD_FLOOR, seed=3)
            self.card_cache['hits'] = hs[::6]
        return self.card_cache['hits']

    def ui_scan(self, cv, t):
        cx, cy, rx, ry = self.flat.bucket[2]
        x0, y0, x1, y1 = int(cx - rx - 8), int(cy - ry - 8), int(cx + rx + 8), int(cy + ry + 24)
        k = ease_out3(ramp(t, TL.T_BKT + 0.25, TL.T_BKT + 0.55))
        if k <= 0: return
        org = (255, 154, 82)
        L = int(14 * k)
        for (xx, yy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            cv.hline(min(xx, xx + sx * L), yy, L, org + (230,)); cv.hline(min(xx, xx + sx * L), yy + sy, L, org + (230,))
            cv.vline(xx, min(yy, yy + sy * L), L, org + (230,)); cv.vline(xx + sx, min(yy, yy + sy * L), L, org + (230,))
        u = TL.scan_u(t)
        if 0 < u < 1:
            sy_ = int(y0 + (y1 - y0) * ease_io(u))
            cv.rect(x0 + 3, sy_, x1 - x0 - 6, 2, (255, 210, 160, 220))
            for i in range(1, 12):
                yy = sy_ - i * 2
                if yy > y0: cv.hline(x0 + 3, yy, x1 - x0 - 6, (255, 170, 110, int(70 * (1 - i / 12))))
        lab = 'SCANNING' + '.' * (int(t * 4) % 4) if t < TL.T_RESULT else 'SCAN COMPLETE'
        cv.text(x0, y0 - 14, lab, org + (255,), 'zh10', shadow=(40, 20, 20, 160))
        r = ease_out3(ramp(t, TL.T_RESULT, TL.T_RESULT + 0.3))
        if r > 0:
            tag = Canvas(96, 40)
            tag.rrect(0, 0, 96, 40, (30, 22, 34, 235), 4); tag.rrect(1, 1, 94, 38, (52, 40, 58, 235), 3)
            tag.rect(0, 0, 4, 40, org + (255,))
            tag.text(10, 5, '鱼获：0', (255, 240, 220, 255), 'zh12')
            tag.text(10, 23, 'FISH CAUGHT: 0', (220, 180, 160, 255), 'zh10')
            ui.blit_scaled(cv, tag.a, x1 - 30 + 48, int(cy) - 10, 0.7 + 0.3 * r, alpha=r)

    def ui_toggle(self, cv, t, cam):
        if not (TL.T_TOG_IN <= t < TL.T_TOG_OUT + 0.3): return
        k = ease_out3(ramp(t, TL.T_TOG_IN, TL.T_TOG_IN + 0.25))
        alpha = 1.0 - ramp(t, TL.T_TOG_OUT, TL.T_TOG_OUT + 0.3)
        press = math.sin(math.pi * ramp(t, TL.T_CLICK - 0.06, TL.T_CLICK + 0.12))
        X, Y = cam.w2ui(C_HEAD[0] + 40, C_HEAD[1] + 2, UIS)
        X = min(X, 400)
        ui.toggle(cv, X, Y, TL.switch_k(t), '消息提醒', alpha=alpha, k=k, press=press)

    def ui_sigh(self, cv, t, cam):
        """three soft puffs from the vent on the side of his head, drifting up and fading."""
        for i in range(4):
            u = (t - TL.T_SIGH - 0.10 * i) / 1.0
            if not 0 <= u < 1: continue
            X, Y = cam.w2ui(C_HEAD[0] - 23 - 4 * u - 1.5 * i, C_HEAD[1] + 14 - 10 * u - 2.5 * i, UIS)
            r = 6 + 9 * u
            al = int(200 * (1 - u) * min(1.0, u * 6))
            yy, xx = np.mgrid[-16:17, -16:17]
            m = (xx ** 2 + yy ** 2) <= r * r
            for (dy, dx) in zip(*np.where(m)):
                cv.px(int(X) + dx - 16, int(Y) + dy - 16, (250, 244, 240, al))

    def ui_flick(self, cv, t, cam, info):
        """a quick swish arc off the old man's near hand toward the card (after the 0.12 s wind-up)."""
        u = (t - TL.T_FLICK0 - 0.12) / 0.3
        if not 0 <= u < 1: return
        hx, hy = info['old_hands'][0]
        X, Y = cam.w2ui(hx, hy, UIS)
        for i in range(14):
            v = i / 13
            if v > u * 1.4: break
            ang = math.pi * (1.05 + 0.55 * v)
            r = 22 + 10 * v
            px_, py_ = X + r * math.cos(ang) + 16, Y + r * math.sin(ang) + 10
            al = int(200 * (1 - u) * (1 - abs(v - u) * 0.8))
            if al > 0: cv.rect(int(px_), int(py_), 2, 2, (255, 246, 230, al))

    def ui_calc(self, cv, t, cam, info):
        pass

    def comp(self, img, t, extra=None):
        cv = ui.UICanvas()
        if extra is not None: extra(cv)
        self.ui_common(cv, t)
        return ui_over(img, cv.a, scale=UIS)

    # ---------------------------------------------------------------- shots
    def f_w(self, t):
        img = self.back.frame(t, Cam(*TL.cam_w(t), W=480, H=270))
        img = img * ease_io(ramp(t, 0.0, 0.5))
        return self.comp(img, t)

    def f_so(self, t):
        z = 2.5 + 0.06 * ease_io(ramp(t, TL.T_SO, TL.T_BKT))
        img, cam, info = self.side.frame(t, (z, 290.0, 171.0), 0.0, cd=TL.claude_so(t), od=TL.old_so(t))
        return self.comp(img, t)

    def f_bkt(self, t):
        u = ease_io(ramp(t, TL.T_BKT, TL.T_SIDE2))
        cam = Cam(1.0 + 0.04 * u, 240.0, 136.0, W=480, H=270)
        img = self.flat.render(t, 'bucket', cam, 0.0)
        return self.comp(img, t, lambda cv: self.ui_scan(cv, t))

    def side_cam(self, t, t0, t1, z0=2.5, z1=2.58, base=SIDE_CAM):
        u = ease_io(ramp(t, t0, t1))
        z = z0 + (z1 - z0) * u
        return (z, base[1], base[2] - 1.5 * u)

    def f_side2(self, t):
        img, cam, info = self.side.frame(t, self.side_cam(t, TL.T_SIDE2, TL.T_CU_C1), 0.0, cd=TL.claude_side2(t),
                                         od=TL.old_side2(t), shake=TL.shake_side2(t))
        def ex(cv):
            self.ui_card(cv, t); self.ui_flick(cv, t, cam, info)
        return self.comp(img, t, ex)

    def f_cu_or(self, t):
        """reaction: the old man holding back a laugh while the card fills (the card stays up)."""
        z, cx, cy = CU_O_CAM
        p = 0.02 * ease_io(ramp(t, TL.T_CU_OR0, TL.T_CU_OR1))
        img, cam, _ = self.side.frame(t, (z * (1 + p), cx, cy), 0.0, od=TL.old_or(t), who=('o',), blur=10.0)
        return self.comp(img, t, lambda cv: self.ui_card(cv, t))

    def f_cu_c1(self, t):
        img, cam, _ = self.side.frame(t, CU_C_CAM, 0.0, cd=TL.claude_c1(t), who=('c',), blur=10.0)
        return self.comp(img, t)

    def f_cu_o(self, t):
        z, cx, cy = CU_O_CAM
        p = TL.punch_o(t)
        img, cam, _ = self.side.frame(t, (z * (1 + p), cx, cy - 6 * p), 0.0, od=TL.old_cu(t), who=('o',), blur=10.0)
        return self.comp(img, t)

    def f_cu_cr(self, t):
        z, cx, cy = CU_C_CAM
        img, cam, _ = self.side.frame(t, (z * 1.06, cx, cy - 1.0), 0.0, cd=TL.claude_cr(t), who=('c',), blur=10.0)
        return self.comp(img, t)

    def f_cu_ob(self, t, t0=None, t1=None, p0=0.0, p1=0.04):
        t0 = TL.T_CU_OB if t0 is None else t0; t1 = TL.T_INS if t1 is None else t1
        z, cx, cy = CU_O_CAM
        p = p0 + (p1 - p0) * ease_io(ramp(t, t0, t1))
        img, cam, _ = self.side.frame(t, (z * (1 + p), cx, cy), 0.0, od=TL.old_cu(t), who=('o',), blur=10.0)
        return self.comp(img, t)

    def f_cu_o2(self, t):
        return self.f_cu_ob(t, TL.T_CU_O2, TL.T_CU_C2, 0.03, 0.08)

    def insert_frame(self, t, dusk, t0, t1):
        """the fine bobber at the waterline in the pier world (crisp; the part under water tinted by the river)."""
        z, cx, cy = INS_CAM
        u = ease_io(ramp(t, t0, t1))
        cam = Cam(z * (1 + 0.05 * u), cx, cy, W=480, H=270)
        mid = GLayer(480, 270)
        bx, by = int(RP.BOBBER[0]), int(RP.BOBBER[1])
        d = 0.6 * math.sin(2 * math.pi * t / 2.3)
        lift = 0.0
        if dusk > 0.5:
            if TL.T_TWITCH <= t < TL.T_TWITCH + 0.25: d += 1.5
            lift = 34.0 * ease_io(ramp(t, TL.T_LIFT0, TL.T_LIFT1)) ** 1.6
        wl = int(round(by + d - lift))                     # sprite row 10 sits on the waterline
        fine, fE = self.pier.fine, self.pier.fineE
        top = wl - 10
        a = fine.copy(); e = fE.copy()
        if lift < 9:
            wc = np.array(C('#c87a6a')[:3] if dusk < 0.5 else C('#5a4a78')[:3], np.float32)
            under = slice(11, None)
            a[under, :, :3] = (a[under, :, :3] * 0.45 + wc * 0.55).astype(np.uint8); e[under] *= 0.3
        cv, E = self.pier.rod_and_line(t, bobber=False, birds=False, line_to=(bx + 3, top + 1), dusk=dusk)
        mid.put(cv.a, 0, 0, 0, E=E)
        mid.put(a, bx - 1, top, 0, E=e)
        # waterline: ring highlight + ripples (on the twitch / when it lifts out)
        rp = Canvas(480, 270); rE = np.zeros((270, 480), np.float32)
        col = C('#ffe8c8') if dusk < 0.5 else C('#c8b8e8')
        if lift < 9: rp.hline(bx - 3, by, 15, col); rE[by, bx - 3:bx + 12] = 0.7
        for (tr, sp) in ((TL.T_TWITCH, 7.0), (TL.T_LIFT0 + 0.2, 10.0)):
            if dusk > 0.5 and tr <= t < tr + 1.6:
                r = 4 + sp * (t - tr)
                for i in range(int(2 * math.pi * r)):
                    ang = i / r
                    x_, y_ = bx + 3.5 + r * math.cos(ang), by + 0.35 * r * math.sin(ang)
                    if i % 2 == 0 and 0 <= int(y_) < 270: rp.px(int(x_), int(y_), col)
        if lift >= 9:
            self.side.hook(rp, bx + 3, top + 19)
            for k_ in range(3):                             # drips falling back
                dy_ = (t - TL.T_LIFT0 - 0.3 * k_) * 60
                if 0 < dy_ < by - top - 18: rp.px(bx + 2 + k_, int(top + 20 + dy_), col)
        mid.put(rp.a, 0, 0, 0, E=rE)
        st = self.pier.state(dusk)
        img = self.pier.render(t, cam, mid, dusk=dusk, st=st)
        if dusk < 0.5:
            k = math.sin(math.pi * clamp01((t - TL.T_INS_GLINT) / 0.9))
            if k > 0:
                X, Y = cam.w2o(bx + 3.5, top + 1.5)
                yy, xx = np.ogrid[0:img.shape[0], 0:img.shape[1]]
                r2 = (xx - X) ** 2 + (yy - Y) ** 2
                g = np.exp(-r2 / (2 * 30.0 ** 2)) * 0.9 + np.exp(-r2 / (2 * 90.0 ** 2)) * 0.25
                star = (np.exp(-((xx - X) / 160.0) ** 2 - ((yy - Y) / 4.0) ** 2) + np.exp(-((xx - X) / 4.0) ** 2 - ((yy - Y) / 110.0) ** 2)) * 0.6
                img = img + ((g + star) * k)[..., None] * np.array([1.0, 0.85, 0.6], np.float32)
        return img

    def f_ins(self, t):
        return self.comp(self.insert_frame(t, 0.0, TL.T_INS, TL.T_INS + 4.0), t)

    def f_ins2(self, t):
        """the pause after 一个周末都没好好过过: nothing but the float riding the swell."""
        return self.comp(self.insert_frame(t, 0.0, TL.T_INS2 - 1.2, TL.T_CU_O2 + 1.0), t)

    def f_cu_c3(self, t):
        z, cx, cy = CU_C_CAM
        u = ease_io(ramp(t, TL.T_CU_C3, TL.T_INS2))
        img, cam, _ = self.side.frame(t, (z * (1.03 + 0.04 * u), cx + 1, cy - 1), 0.0, cd=TL.claude_c3(t), who=('c',), blur=10.0)
        return self.comp(img, t)

    def f_cu_c2(self, t):
        img, cam, _ = self.side.frame(t, CU_C_CAM, 0.0, cd=TL.claude_c2(t), who=('c',), blur=10.0)
        def ex(cv):
            self.ui_sigh(cv, t, cam); self.ui_toggle(cv, t, cam)
        return self.comp(img, t, ex)

    def f_paint(self, t):
        return self.pv.frame(TL.paint_local(t))

    def f_ins_d(self, t):
        return self.comp(self.insert_frame(t, 1.0, TL.T_INS_D, TL.T_SIDE_H), t)

    # ---- the hand-over (dusk two-shot)
    def handover(self, t):
        """-> (claude dict, old dict, extra fn) for SIDE_H / SIDE_H2.
        SIDE_H: body to the water - the reel crank (4 drawings), the catch, a look at the empty hook, a smile, a glance
        at the badge.  SIDE_H2 (after the badge insert hides the turn): body to Claude - 拿着。 the give (blended arm),
        Claude reaches, takes it (wide eyes -> ^ ^), scoots closer; 下周末……"""
        side = self.side
        q = PF.on_twos(t)
        rk = TL.reach_k(q); sk = TL.scoot_k(q); gk = TL.give_k(q)
        # ---------------- Claude
        cd = dict(face='normal', arms='knees', look=(3, 0), pose='sit', hdy=PF.breath_px(q, 3.6))
        if q < TL.T_CATCH: cd['look'] = (3, -1) if q < TL.T_REEL0 + 0.6 else (3, 0)
        elif q < TL.T_SIDE_H2: cd['look'] = (3, 0)
        cd['face'] = PF.blink_face(q, [96.3, 98.0, 99.9, 104.2])
        if TL.T_CATCH + 0.1 <= q < TL.T_BADGE: cd['tilt_t'] = 3.0
        if q >= TL.T_REACH0:
            cd['arms'] = ('knees', 'lift', rk) if q < TL.T_WITH0 else ('lift', 'hold', ease_io(ramp(q, TL.T_WITH0, TL.T_WITH1)))
        if q >= TL.T_DROP: cd['face'] = 'wide2' if q < TL.T_HAPPY_H else 'happy'; cd['look'] = (1, 1)
        if q >= TL.T_HAPPY_H + 1.1: cd['face'] = PF.blink_face(q, [104.2], 'normal'); cd['look'] = (3, 0)
        cd['dx'] = 4 * rk * (1 - sk) + TL.SCOOT * sk
        cd['y'] = hop(q, TL.T_SCOOT0, 3.0, TL.T_SCOOT1 - TL.T_SCOOT0)
        cd['squash'] = squash_curve(q, TL.T_SCOOT1, 0.08, 0.1) + squash_curve(q, TL.T_DROP, -0.05, 0.1)
        tgt = lambda x: (3.0 if TL.T_CATCH + 0.1 <= x < TL.T_BADGE else 0.0) + (4.0 if TL.T_HAPPY_H <= x < TL.T_HAPPY_H + 1.1 else 0.0)
        cd['tilt'] = PF.spring_follow(tgt, q, freq=2.4, zeta=0.55, window=1.0, dt=1 / 120)
        hp = lambda x: (4 * TL.reach_k(x) * (1 - TL.scoot_k(x)) + TL.SCOOT * TL.scoot_k(x) + 0.5 * tgt(x), hop(x, TL.T_SCOOT0, 3.0, TL.T_SCOOT1 - TL.T_SCOOT0))
        lx, ly = PF.lag(hp, t, freq=3.2, zeta=0.22, window=1.4, dt=1 / 120)
        lx += PF.wobbles(t, [(TL.T_DROP, 1.8), (TL.T_HAPPY_H, 1.6)], freq=3.6, decay=3.0)
        cd['ant'] = (lx * 1.4, ly * 0.6)
        cd.pop('tilt_t', None)
        # ---------------- the old man
        if q < TL.T_SIDE_H2:
            od = dict(body='water', breath='v2', v=PF.turn_track(q, TL.H_TURN))
            if q < TL.T_REEL1:
                od['arms'] = 'reel'
                if q >= TL.T_REEL0: od['arm_ang'] = {1: TL.REEL_CRANK[TL.reel_phase(q)]}
            else:
                od['arms'] = 'catch'
            if TL.T_LOOK_HOOK <= q < TL.T_SMILE_O: od['face'] = 'down'
            if TL.T_SMILE_O <= q < TL.T_LOOK_BADGE: od['face'] = 'smile'
            if q >= TL.T_LOOK_BADGE: od['face'] = 'down'
        else:
            od = dict(body='claude', breath='v2', arms=('catch', 'give', gk) if q < TL.T_WITH1 else 'hold', lean=-12 * gk)
            if q >= TL.T_WITH0: od['arms'] = ('give', 'hold', ease_io(ramp(q, TL.T_WITH0, TL.T_WITH1)))
            if q >= TL.T_WITH1: od['arms'] = 'hold'
            od['v'] = -1.0
        state = {}

        def bob_pos(info):
            hands = info['old_hands']
            if t < TL.T_CATCH:
                u = ease_io(ramp(t, TL.T_REEL0 + 0.25, TL.T_CATCH))
                x0, y0 = BOB_S; x1, y1 = hands[1][0] - 1, hands[1][1] + 2
                x = x0 + (x1 - x0) * u; y = y0 + (y1 - y0) * u - 10 * math.sin(math.pi * u)
                return x, y + 0.8 * math.sin(t * 11) * (1 - u)
            if t < TL.T_GIVE0 or (t < TL.T_SIDE_H2):
                return hands[1][0] - 1, hands[1][1] + 2
            if t < TL.T_DROP:
                k = ease_io(ramp(t, TL.T_GIVE0, TL.T_GIVE0 + 0.3))
                return hands[1][0], hands[1][1] + 2 + 12 * k
            cx_, cy_ = info['claude_xy']
            cx_ += cd.get('dx', 0)
            lift = (cx_ + 53, cy_ + 46)
            hold = (cx_ + CL.torso_box()[0] + 12, cy_ + CL.torso_box()[1] + 13 + 2)
            k = ease_io(ramp(t, TL.T_WITH0, TL.T_WITH1))
            v = clamp01((t - TL.T_DROP) / 0.12)
            bounce = -1 if 0.12 <= t - TL.T_DROP < 0.22 else 0
            x = lift[0] + (hold[0] - lift[0]) * k; y = lift[1] + 2 * v + bounce + (hold[1] - lift[1] - 2) * k
            return x, y + cd.get('y', 0)

        def extra(cv, E, info):
            if t < TL.T_REEL0 + 0.25: return
            x, y = bob_pos(info)
            a, e = self.pier.fine, self.pier.fineE
            h, w = a.shape[:2]
            hooked = t < TL.T_BADGE
            X, Y = int(round(x - w // 2)), int(round(y - h + 4))
            m = a[..., 3] > 0
            reg = cv.a[Y:Y + h, X:X + w]; regE = E[Y:Y + h, X:X + w]
            reg[m] = a[m]; regE[m] = e[m]
            if t >= TL.T_WITH1:
                pr = CL.draw(arms='hold', pose='sit', legs=True, led='off')
                ha = pr.hands.cv.a; hm = ha[..., 3] > 0; hm[:CL.torso_box()[1] + 7] = False
                ys, xs = np.nonzero(hm); cx_, cy_ = info['claude_xy']
                cv.a[cy_ + int(round(cd.get('y', 0))) + ys, cx_ + int(round(cd.get('dx', 0))) + xs] = ha[ys, xs]
            if hooked:
                side.line(cv, E, info['tip'], (X + w // 2, Y), sag=1.5 if t >= TL.T_CATCH else 2.5, dusk=1.0)
                side.hook(cv, X + w // 2, Y + h - 1)
        if t < TL.T_REEL0 + 0.25: od['line'] = 'water'
        elif t < TL.T_BADGE: od['line'] = 'none'
        else: od['line'] = 'hang'
        return cd, od, extra

    def f_side_h(self, t):
        cd, od, extra = self.handover(t)
        if t < TL.T_BADGE: cam_def = self.side_cam(t, TL.T_SIDE_H, TL.T_BADGE, 2.5, 2.54)
        else: cam_def = self.side_cam(t, TL.T_SIDE_H2, TL.T_CU_H, 2.54, 2.62)
        cam_def = (cam_def[0], cam_def[1] + 2 * TL.scoot_k(t), cam_def[2])
        img, cam, info = self.side.frame(t, cam_def, 1.0, cd=cd, od=od, extra=extra)
        return self.comp(img, t)

    def f_badge(self, t):
        u = ease_io(ramp(t, TL.T_BADGE, TL.T_SIDE_H2))
        cam = Cam(1.0 + 0.06 * u, 240.0, 150.0 - 4 * u, W=480, H=270)
        return self.comp(blue_hour(self.flat.render(t, 'badge', cam, 1.0), 0.22), t)

    def f_cu_h(self, t):
        """Claude holding the bobber; the invitation still on screen: — — ... 嗯。 ^ ^ + a head-tilt nod, antenna boing."""
        q = PF.on_twos(t)
        d = dict(face='calm', arms='hold', look=(0, 2), glow=0.55, pose='sit', dx=TL.SCOOT, hdy=PF.breath_px(q, 3.8))
        if q < TL.T_CU_H + 1.2: d['face'] = PF.blink_face(q, [TL.T_CU_H + 0.7], 'normal'); d['look'] = (2, 0)
        if q >= TL.T_YES - 0.1: d['face'] = 'happy'
        d['nod'] = int(round(2 * TL.nod(q)))
        d['tilt'] = PF.spring_follow(lambda x: 5.0 if x >= TL.T_NOD0 else 0.0, q, freq=2.2, zeta=0.5, window=1.2, dt=1 / 120)
        d['ant'] = (PF.wobble(t, TL.T_NOD0 + 0.1, 2.4, freq=3.4, decay=2.6) + 1.2 * PF.wobble(t, TL.T_NOD0, 1.0, freq=1.7, decay=2.0),
                    PF.wobble(t, TL.T_NOD0 + 0.1, 1.2, freq=3.4, decay=2.6))
        u = ease_io(ramp(t, TL.T_CU_H, TL.T_END + 1.0))
        z, cx, cy = CU_C_CAM
        cam_def = (z * (1 + 0.05 * u), cx + TL.SCOOT - 2 * u, cy - 4 * u)
        def extra(cv, E, info):
            x, y = info['claude_xy']
            x += TL.SCOOT; y += d['nod'] * 0
            a, e = self.pier.fine, self.pier.fineE
            h, w = a.shape[:2]
            bx_, by_ = CL.torso_box()[0], CL.torso_box()[1]
            X, Y = x + bx_ + 12 - w // 2, y + by_ + 15 - h + 2
            m = a[..., 3] > 0
            cv.a[Y:Y + h, X:X + w][m] = a[m]; E[Y:Y + h, X:X + w][m] = e[m]
            pr = CL.draw(arms='hold', pose='sit', legs=True, led='off')
            ha = pr.hands.cv.a
            hm = ha[..., 3] > 0
            hm[:by_ + 7] = False
            ys, xs = np.nonzero(hm)
            cv.a[y + ys, x + xs] = ha[ys, xs]
        img, cam, _ = self.side.frame(t, cam_def, 1.0, cd=d, who=('c',), blur=12.0, extra=extra)
        return self.comp(img, t)

    def f_end(self, t):
        u = ease_io(ramp(t, TL.T_END, TL.T_ECHO + 0.5))
        img = self.back.frame(t, Cam(1.0 + 0.04 * u, 240.0, 135.0 + 2 * u, W=480, H=270), dusk=1.0)
        return self.comp(img, t)

    def f_echo(self, t):
        return self.comp(self.echo.frame(t), t)

    def frame(self, t):
        img = self.edit.frame(t)
        if t >= TL.T_FADE0: img = img * (1 - ease_io(ramp(t, TL.T_FADE0, TL.DUR - 0.05)))
        return img

def make(**kw): return Act4(**kw)
