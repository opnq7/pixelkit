"""ACT III renderer: make() -> object with .frame(t) -> float RGB (1080, 1920, 3).   Shots: see timeline.py"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/act3'))
import numpy as np, cv2
from pixelkit.core import C, Canvas, mix, poly_mask
from pixelkit.anim import clamp01, ramp, ease_out3, ease_io
from pixelkit.camera import Cam
from pixelkit.scene import GLayer, FlatScene
from pixelkit.outdoor import OutdoorScene, outdoor_state
from pixelkit.sets.street import Street
from pixelkit.characters import claude as CL
from pixelkit.characters import walker as WK
from pixelkit.particles import Motes2D, FallingLeaves
from pixelkit import ui, edit, post
from pixelkit import materials as M
import timeline as TL

LOOK = dict(sun_k=0.75, amb_k=0.50, haze_k=0.12, shadow_sy=-0.20)          # tuned outdoor morning (brightest act of the film)

def claude_sprite(d, flip=False):
    p = CL.draw(face=d['face'], arms=d['arms'], pose=d['pose'], phase=d['phase'], look=d['look'], led='off', flip=flip)
    hy = d['foot'] - (CL.FOOT_Y - CL.AY) + p.bob + d.get('hop', 0.0)
    X, Y = int(round(d['x'] - p.ax)), int(round(hy - p.ay))
    al = (p.body.cv.a[..., 3] > 127) | (p.hands.cv.a[..., 3] > 127)
    return p, X, Y, al


# ====================================================================== IN : the corridor (480 x 270 painted insert)
class InShot:
    DX, DY, DW, DH = 214, 138, 52, 78          # doorway (as seen from inside)
    FLOOR = 216
    def __init__(self, OW=1920, OH=1080):
        self.fs = FlatScene(OW=OW, OH=OH)
        W, H = 480, 270
        cv = Canvas(W, H, (10, 10, 14, 255))
        yy, xx = np.mgrid[0:H, 0:W].astype(float)
        n = M.fbm(xx, yy, 18.0, 3, 7)
        dx, dy, dw, dh, fl = self.DX, self.DY, self.DW, self.DH, self.FLOOR
        bx0, bx1, by0 = 150, 330, 70                       # back wall
        wall = np.array(C('#3a3e4c')[:3], float); flo = np.array(C('#44424a')[:3], float)
        img = np.zeros((H, W, 3))
        img[:] = wall * 0.70                                # ceiling / side walls (darker)
        back = (xx >= bx0) & (xx < bx1) & (yy >= by0) & (yy < fl)
        img[back] = wall * (0.92 + 0.10 * n[back, None])
        side = ((xx < bx0) & (yy > by0 - (bx0 - xx) * 0.47) & (yy < fl + (bx0 - xx) * 0.37)) | \
               ((xx >= bx1) & (yy > by0 - (xx - bx1) * 0.47) & (yy < fl + (xx - bx1) * 0.37))
        img[side] = wall * (0.78 + 0.10 * n[side, None])
        floor = yy >= fl + np.abs(np.clip(xx, bx0, bx1) - xx) * 0.37
        floor &= ~side
        img[floor] = flo * (0.85 + 0.12 * n[floor, None])
        # floor seams converging to the door
        for k in range(-6, 7):
            x_b = 240 + k * 70
            for y in range(fl, H):
                u = (y - fl) / (H - fl); x = int(round(240 + (x_b - 240) * u * 1.0 + k * 14 * (1 - u)))
                if 0 <= x < W and floor[y, x]: img[y, x] *= 0.82
        for y in (fl + 8, fl + 20, fl + 38):
            img[y, :][floor[y, :]] *= 0.85
        # skirting + pipe + fire box on the left wall
        img[fl - 4:fl, bx0:bx1] = wall * 0.6
        img[by0 + 8:by0 + 11, bx0:bx1] = np.array(C('#5a5e6a')[:3]) * 0.9
        img[118:150, 168:184] = np.array(C('#b8392e')[:3]); img[120:148, 170:182] = np.array(C('#d44a3a')[:3])
        img[126:140, 172:180] = np.array(C('#f0e6d8')[:3]) * 0.8
        # door frame + steel leaf (closed); the leaf is redrawn per frame
        img[dy - 3:fl, dx - 3:dx + dw + 3] = np.array(C('#4a505c')[:3])
        self.base = np.dstack([np.clip(img, 0, 255).astype(np.uint8), np.full((H, W), 255, np.uint8)])
        # exit sign above the door
        self.sign = (216, 121, 48, 12)
        self.side = side; self.floor = floor

    def paint(self, t):
        img = self.base.copy(); E = np.zeros(img.shape[:2], np.float32)
        cv = Canvas(480, 270); cv.a = img
        dx, dy, dw, dh, fl = self.DX, self.DY, self.DW, self.DH, self.FLOOR
        o = TL.door_in(t)
        # outdoors seen through the opening: blinding warm white with a hint of street
        pw = int(round(dw * math.cos(o * math.radians(95)))) if o < 0.99 else 0
        open_w = dw - max(0, pw)
        if open_w > 0:
            x0 = dx + max(pw, 0)
            for yy in range(dy, fl):
                c = mix(C('#fff4dc'), C('#ffd9a0'), (yy - dy) / (fl - dy))
                cv.rect(x0, yy, dx + dw - x0, 1, c)
            E[dy:fl, x0:dx + dw] = 1.0
        # the leaf (inside face), swinging away: hinge on the left
        if pw > 0:
            shade = mix(C('#5a6272'), C('#3a404c'), o)
            cv.rect(dx, dy, pw, fl - dy, shade); cv.vline(dx + pw - 1, dy, fl - dy, C('#7a8494'))
            if pw > 10:
                cv.rect(dx + 4, dy + 30, pw - 8, 3, C('#9aa2b2')); cv.rect(dx + 4, dy + 30, pw - 8, 1, C('#c8ccd4'))   # push bar
            if o > 0.005:     # light leaking round the crack
                cv.vline(dx + pw, dy, fl - dy, C('#fff0d0')); E[dy:fl, dx + pw] = 1.0
                cv.hline(dx, fl - 1, pw, C('#ffe6b8')); E[fl - 1, dx:dx + pw] = 0.8
        # exit sign
        sx, sy, sw, sh = self.sign; on = TL.sign_on(t)
        cv.rect(sx, sy, sw, sh, C('#1e3a2a')); cv.rect(sx + 1, sy + 1, sw - 2, sh - 2, C('#2fd07a') if on else C('#2a4a38'))
        if on:
            cv.text(sx + 11, sy, '安全出口', C('#f0fff4'), 'zh8')
            man = ["..##.", ".###.", "#.##.", "..#.#", ".#.#.", "#...#"]
            for j, row in enumerate(man):
                for i, ch in enumerate(row):
                    if ch == '#': cv.px(sx + 3 + i, sy + 3 + j, C('#f0fff4'))
            E[sy:sy + sh, sx:sx + sw] = 1.0
        # Claude from behind = silhouette (+ glowing spark on the antenna), rim-lit by the doorway
        d = dict(x=240.0, foot=fl + 14, pose='stand', arms='down', face='off', phase=0, look=(0, 0), hop=0.0)
        if t > TL.T_OPEN0 + 0.25:    # starts walking into the light
            d['pose'] = 'walk'; d['phase'] = int((t - TL.T_OPEN0 - 0.25) * 6) % 4
        p, X, Y, al = claude_sprite(d)
        h, w = al.shape
        sil = C('#100e16')
        spark = p.body.E > 0.3
        reg = cv.a[Y:Y + h, X:X + w]
        reg[al] = sil
        ys = np.arange(h)[:, None] < (CL.AY - 1)
        reg[spark & ys & al] = p.body.cv.a[spark & ys & al]
        E[Y:Y + h, X:X + w][spark & ys & al] = 0.8 * on
        light = clamp01(open_w / dw) if open_w > 0 else 0.0
        if light > 0:
            er = cv2.erode(al.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            rim = al & ~er
            bright = np.zeros_like(al)
            bright[:, :] = (np.arange(X, X + w)[None, :] >= dx + max(pw, 0) - 3) & (np.arange(Y, Y + h)[:, None] >= dy)
            rim &= bright | (light > 0.6)
            reg[rim] = C('#ffe2b0'); E[Y:Y + h, X:X + w][rim] = 0.9 * light
        return cv.a, E, light, (X, Y, al)

    def frame(self, t):
        alb, E, light, (X, Y, al) = self.paint(t)
        fs = self.fs; on = TL.sign_on(t)
        L = fs.ambient((0.40, 0.42, 0.62), 0.07 + 0.16 * on)
        L = L + fs.pool(240, 138, 120, 70, (0.30, 1.0, 0.55), 0.55 * on)
        if light > 0:
            dx, dy, dw, fl = self.DX, self.DY, self.DW, self.FLOOR
            L = L + fs.pool(240, 190, 140 + 160 * light, 90 + 60 * light, (1.0, 0.86, 0.66), 1.6 * light ** 0.8)
            # light shaft spilling across the floor toward the camera
            x0 = dx + dw * (1 - light)
            pts = [(x0, fl), (dx + dw, fl), (dx + dw + (dx + dw - 240) * 1.8 + 60, 270), (240 + (x0 - 240) * 2.6 - 40, 270)]
            m = poly_mask(480 * 2, 270 * 2, [(px * 2, py * 2) for px, py in pts]).astype(np.float32)
            m = cv2.GaussianBlur(m, (0, 0), 4)
            L = L + m[..., None] * np.asarray((1.0, 0.85, 0.62), np.float32) * 2.2 * light
            L = fs.shadow(L, np.pad(al, ((0, 0), (0, 0)))[:0] if False else self._mask(al, X, Y), 0, 10, k=0.7 * light, soft=3)
        g = dict(post.GRADES['golden_hd2d']); g['exposure'] = TL.exposure_in(t)
        g['vignette'] = 0.5
        z = 1.95 + 0.25 * ease_io(ramp(t, 0.0, TL.T_OUT))
        cam = Cam(z, 240, 182 - 4 * ease_io(ramp(t, 0, TL.T_OUT)))
        return fs.render(cam, alb, L.astype(np.float32), g, E=E, frame=int(round(t * TL.FPS)), emis_bloom=0.8)

    def _mask(self, al, X, Y):
        m = np.zeros((270, 480), bool); h, w = al.shape
        m[Y:Y + h, X:X + w] = al; return m


# ====================================================================== OUT / MED : the street
class StreetShot:
    def __init__(self, OW=1920, OH=1080):
        self.st = Street()
        self.sc = OutdoorScene(self.st.bg, OW=OW, OH=OH)
        self.OW, self.OH = OW, OH
        self.walkers = [WK.Walker(li, x0, v, foot, prop, t0, seed=sd) for (li, x0, v, foot, prop, t0, sd) in TL.WALKERS]
        cans = [(c['cx'], c['cy'] - c['ry'] * 0.4, c['cy'] + c['ry'] * 0.6, c['rx'] * 0.7) for c in self.st.canopies]
        self.leaves = FallingLeaves(cans, ground=(194, 224), per_tree=3, seed=8)
        self.motes = Motes2D(self.st.W, self.st.H, n=220, seed=12)
        self.mote_vis = np.clip(self.st.T, 0, 1) * 0.6 + 0.25

    def state(self, t):
        st = outdoor_state('morning', **LOOK)
        st['grade']['exposure'] = TL.exposure_out(t)
        st['grade'].update(sat=1.22, contrast=1.20, black=0.045)
        st['haze_gain'] = 1.0 + 3.0 * (1 - ease_out3(ramp(t, TL.T_OUT, TL.T_EXP1)))
        return st

    def hud(self, cv, t):
        a = ramp(t, TL.T_HUD, TL.T_HUD + 0.4)
        ui.hud_time(cv, 8, 8, '08:00', day='周六', day_en='SAT', alpha=a)
        ui.status_badge(cv, 472, 8, 'off', alpha=a)

    def ui(self, t):
        cv = ui.UICanvas()
        self.hud(cv, t)
        if t >= TL.T_QUEST:
            ui.quest_bar(cv, t, TL.T_QUEST, '学会休息', (0, 1), y=8)
        if t >= TL.T_QLIST:
            ui.quest_list(cv, t, TL.T_QLIST, [('睡个懒觉', 'active'), ('散个步', 'todo'), ('随便逛逛', 'todo')], y=44)
        return cv.a

    def frame(self, t, cam=None, ui_on=True):
        if cam is None:
            if t < TL.T_MED: z, cx, cy = TL.cam_out(t)
            else: z, cx, cy = TL.cam_med(t)
            cam = Cam(z, cx, cy, W=480, H=270, OW=self.OW, OH=self.OH)
        z = cam.zoom
        hw, hh = 240 / z, 135 / z
        if z >= 1.0: cam.cx = min(max(cam.cx, hw), self.st.W - hw); cam.cy = min(max(cam.cy, hh), 270 - hh)
        st = self.state(t)
        mid = GLayer(self.st.W, self.st.H)
        casters = []
        for wk in self.walkers:                       # extras first (behind the lead)
            for (rgba, X, Y, E, al, foot) in wk.sprites(t):
                if X > self.st.W or X + rgba.shape[1] < 0: continue
                mid.put(rgba, X, Y, 0, E=E)
                if foot is not None: casters.append((al, X, Y, foot, 0.55))
        for (rgba, X, Y) in self.leaves.sprites(t): mid.put(rgba, X, Y, 0)
        d = TL.claude(t)
        p, X, Y, al = claude_sprite(d)
        mid.put(p.body.rgba, X, Y, 0, E=p.body.E); mid.put(p.hands.rgba, X, Y, 0, E=p.hands.E)
        casters.append((al, X, Y, d['foot'], 1.0 if d['hop'] > -1.5 else 0.7))
        leaf, lx, ly = self.st.door_sprite(TL.door_out(t))
        patches = [(leaf.rgba, lx, ly)]
        motes = self.motes.render_out(t, cam, self.mote_vis, gain=0.45)
        return self.sc.render(cam, st, mid, casters, ui=self.ui(t) if ui_on else None, frame=int(round(t * TL.FPS)), bg_patches=patches,
                              front_i=self.st.front_index(t), add_out=motes)


# ====================================================================== shared helpers (town shots)
from pixelkit.sets.town import Town
from pixelkit.sets.maps import ParkMap, CityAerial, claude_mini
from pixelkit.characters import person as P
from pixelkit.core import Canvas as _Cv, text_width
from pixelkit.anim import blink_at, back_out

U4 = 4
INK_D = C('#2b1c22')

def blit_np(img, E, rgba, e, x, y, alpha=1.0):
    """alpha-blit an RGBA sprite (+ emission) into a uint8 RGBA image array in place."""
    h, w = rgba.shape[:2]; H, W = img.shape[:2]
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    s = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = (s[..., 3:4].astype(np.float32) / 255.0) * alpha
    d = img[y0:y1, x0:x1, :3].astype(np.float32)
    img[y0:y1, x0:x1, :3] = (d * (1 - a) + s[..., :3] * a).astype(np.uint8)
    if E is not None and e is not None:
        E[y0:y1, x0:x1] = np.maximum(E[y0:y1, x0:x1] * (1 - a[..., 0]), e[y0 - y:y1 - y, x0 - x:x1 - x] * a[..., 0])

SUIT = P.Look(hair='side', hair_col='#2a2226', skin='#f0c8a4', top='suit', top_col='#3a3e52', inner='#ffffff', tie='#c8302a',
              bottom_col='#2e3044', shoes='#1e1a1e', seed=21)
GROOM = P.Look(hair='short', hair_col='#2a2228', skin='#eebf98', top='suit', top_col='#f4f0e8', inner='#ffffff', tie='#2a2a33',
               bottom_col='#e8e4dc', shoes='#3a2a26', flower=True, seed=22)
BRIDE = P.Look(hair='bun', hair_col='#3a2a26', skin='#f6dcc4', top='dress', top_col='#fbf8f4', inner='#ffffff', bottom='skirt',
               bottom_col='#fbf8f4', shoes='#f0e8e0', flower=True, seed=23)
FRIEND = P.CAST['bun_cardigan']

class People:
    """cached person sprites keyed by (look name, pose, phase, arms, face, flip)."""
    LOOKS = dict(P.CAST, suit=SUIT, groom=GROOM, bride=BRIDE)
    def __init__(self): self.c = {}
    def get(self, name, pose='stand', phase=0.0, arms='down', face='normal', flip=False, prop=None, bgk=0.10):
        k = (name, pose, round(phase, 3), arms, face, flip, prop)
        if k not in self.c:
            s = P.draw(self.LOOKS[name], pose=pose, phase=phase, arms=arms, face=face, flip=flip, prop=prop)
            s.rgba = P.background(s.rgba, k=bgk) if bgk > 0 else s.rgba
            s.al = s.rgba[..., 3] > 127
            self.c[k] = s
        return self.c[k]

def warm_grade(g, w):
    g['highlight'] = (g['highlight'][0] + 0.35 * w, g['highlight'][1] + 0.15 * w, g['highlight'][2] - 0.30 * w)
    g['shadow'] = (g['shadow'][0] + 0.10 * w, g['shadow'][1] + 0.03 * w, g['shadow'][2] - 0.15 * w)
    g['sat'] = g['sat'] + 0.15 * w
    return g

def kite_sprite(t):
    cv = _Cv(13, 26); E = np.zeros((26, 13), np.float32)
    pts = [(6, 0), (12, 6), (6, 15), (0, 6)]
    cv.poly(pts, OUTL_K)
    cv.poly([(6, 1), (11, 6), (6, 6)], C('#ff6a5a')); cv.poly([(6, 1), (1, 6), (6, 6)], C('#ffd23f'))
    cv.poly([(1, 6), (6, 6), (6, 14)], C('#5ab0ff')); cv.poly([(11, 6), (6, 6), (6, 14)], C('#6ad08a'))
    cv.vline(6, 1, 13, C('#fff4e0')); cv.hline(1, 6, 11, C('#fff4e0'))
    for k in range(5):                                                   # tail with bows, waving
        x = int(round(6 + 2.2 * math.sin(t * 6 + k * 1.1))); y = 15 + 2 * k
        cv.px(x, y, C('#2a1715'))
        if k % 2 == 1: cv.px(x - 1, y, C('#ff6a5a')); cv.px(x + 1, y, C('#ff6a5a'))
    return cv.a, E
OUTL_K = C('#2a1715')

def kite_xy(t):
    """F1: a runaway kite drifts in from the upper left, sinks towards the uncle, then climbs once he holds it."""
    u = ease_out3(ramp(t, TL.T_KITE_IN, TL.T_U_STAND))
    kx = 92 + (196 - 92) * u + 10 * math.sin(t * 0.9) * u + 3 * math.sin(t * 2.3)
    ky = 30 + (62 - 30) * u + 5 * math.sin(t * 1.3)
    if t >= TL.T_U_STAND: ky -= 10 * ease_io(ramp(t, TL.T_U_STAND, TL.T_U_STAND + 1.2))
    return kx, ky

def kite_free_end(t):
    """the trailing end of the string: dangles under the kite, floats down to the uncle's raised hand height."""
    kx, ky = kite_xy(t)
    u = ease_io(ramp(t, TL.T_KITE_IN + 0.4, TL.T_U_STAND))
    x0, y0 = kx - 4 + 3 * math.sin(t * 3.1), ky + 52
    x1, y1 = 262.0, 150.0
    return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u

def line_sprite(x0, y0, x1, y1, col, sag=0.0):
    """thin string as a sprite (with a little sag) -> (rgba, X, Y)."""
    X, Y = int(min(x0, x1)) - 2, int(min(y0, y1)) - 2
    w, h = int(abs(x1 - x0)) + 5, int(abs(y1 - y0) + abs(sag)) + 6
    cv = _Cv(w, h)
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n + 1):
        u = i / n
        x = x0 + (x1 - x0) * u; y = y0 + (y1 - y0) * u + sag * 4 * u * (1 - u)
        cv.px(int(round(x - X)), int(round(y - Y)), col)
    return cv.a, X, Y

def chair_sprite(flip=False):
    cv = _Cv(14, 24)
    cv.rect(10, 0, 2, 22, OUTL_K); cv.vline(11, 1, 21, C('#4a5a52'))
    cv.rect(0, 11, 12, 2, C('#4a5a52')); cv.hline(0, 10, 12, OUTL_K); cv.vline(1, 13, 9, C('#4a5a52'))
    a = cv.a if not flip else cv.a[:, ::-1].copy()
    return a          # foot row 22

def mic_sprite():
    cv = _Cv(9, 44); E = np.zeros((44, 9), np.float32)
    cv.rect(1, 42, 7, 2, OUTL_K); cv.vline(4, 6, 37, OUTL_K); cv.vline(5, 6, 37, C('#8a8e98'))
    cv.line(4, 6, 1, 2, OUTL_K)
    cv.rect(0, 0, 3, 4, OUTL_K); cv.rect(0, 0, 2, 3, C('#5a5e6a'))
    return cv.a, E

def sleeper_bust(stretch=0.0, face_open=True):
    """tiny bedroom-window sleeper (fits the 38x32 window): 14 x 16 sprite, arms up when stretch > .5"""
    cv = _Cv(16, 16)
    sk, hr, pj = C('#f1c7a0'), C('#4a3226'), C('#8ab0e0')
    cv.rect(3, 9, 10, 7, OUTL_K); cv.rect(4, 10, 8, 6, pj); cv.hline(4, 10, 8, C('#b8d4f4'))
    cv.rect(4, 1, 8, 8, OUTL_K); cv.rect(5, 2, 6, 7, sk)
    cv.rect(4, 1, 8, 3, hr); cv.px(3, 2, hr); cv.px(12, 1, hr); cv.px(11, 0, hr); cv.px(6, 0, hr)
    if face_open: cv.px(6, 5, INK_D); cv.px(9, 5, INK_D); cv.hline(7, 7, 2, C('#c86a5a'))
    else: cv.hline(6, 5, 2, INK_D); cv.hline(9, 5, 2, INK_D); cv.rect(7, 7, 2, 1, C('#c86a5a'))
    cv.px(5, 6, C('#f0a090')); cv.px(10, 6, C('#f0a090'))
    if stretch > 0.5:
        for xs in (2, 13):
            cv.rect(xs, 1, 2, 9, OUTL_K); cv.vline(xs, 2, 7, pj); cv.px(xs, 1, sk)
    return cv.a


# ---------------------------------------------------------------------- the dream bubble (PARK)
def sheep_sprite(ph=0, dizzy=False):
    cv = _Cv(17, 13)
    lg = C('#3a3036')
    offs = [(0, 0, 0, 0), (1, -1, -1, 1)][ph % 2]
    for i, lx in enumerate((4, 6, 10, 12)): cv.rect(lx + offs[i] * 0, 8, 1, 3 + (offs[i] if offs[i] > 0 else 0), lg)
    for (ex, ey, r) in ((5, 5, 4.0), (9, 4, 4.4), (12, 6, 3.4), (7, 7, 3.6), (10, 7, 3.4)):
        cv.ellipse(ex, ey, r + 1, r + 1, OUTL_K)
    for (ex, ey, r) in ((5, 5, 4.0), (9, 4, 4.4), (12, 6, 3.4), (7, 7, 3.6), (10, 7, 3.4)):
        cv.ellipse(ex, ey, r, r, C('#fbf6ec'))
    for (ex, ey) in ((7, 2), (10, 2), (4, 4)): cv.px(ex, ey, C('#ffffff'))
    cv.hline(4, 9, 9, C('#d8cfc0'))
    cv.rect(13, 3, 4, 5, OUTL_K); cv.rect(14, 4, 3, 3, lg); cv.px(16, 4, C('#ffffff')); cv.px(13, 3, lg)
    return cv.a

SHEEP_SPR = [sheep_sprite(0), sheep_sprite(1)]

def sheep_counter(cv, t):
    """HUD panel at the top centre: [sheep] x 1,234 只羊 (runs away, lands gold)."""
    n = TL.sheep_count(t); txt = ui.fmt_int(n)
    a = ramp(t, TL.T_SHEEP0, TL.T_SHEEP0 + 0.2) * (1 - ramp(t, TL.T_EYES + 0.3, TL.T_EYES + 0.6))
    if a <= 0: return
    tw = text_width(txt, 'p2p') * 2
    w = tw + 66; h = 26; x = 240 - w // 2; y = 8
    bump = 1 - (t - TL.T_DONE) / 0.3 if TL.T_DONE <= t < TL.T_DONE + 0.3 else 0.0
    if TL.T_RUSH0 <= t < TL.T_DONE: x += int(round(math.sin(t * 80) * 1.5))
    ui._hud_panel(cv, x, y - int(2 * bump), w, h, a)
    cv.blit(SHEEP_SPR[int(t * 6) % 2], x + 6, y + 6, alpha_mul=a)
    col = C('#ffd23f') if t >= TL.T_DONE else C('#ffffff')
    ui.big_text(cv, x + 26, y + 6 - int(2 * bump), txt, col, 'p2p', 2, shadow=OUTL_K, alpha=a)
    cv.text(x + 30 + tw, y + 7, '只', (255, 243, 223, int(255 * a)), 'zh12')

class DreamBubble:
    W, H = 156, 92
    def __init__(self):
        W, H = self.W, self.H
        yy, xx = np.mgrid[0:H, 0:W]
        m = np.zeros((H, W), bool)
        for (cx, cy, rx, ry) in ((78, 46, 70, 36), (40, 26, 30, 20), (80, 18, 34, 16), (120, 26, 30, 20),
                                 (34, 64, 28, 20), (78, 74, 36, 16), (122, 64, 28, 20), (16, 46, 14, 16), (140, 46, 14, 16)):
            m |= ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 < 1.0
        self.m = m
        k = np.ones((3, 3), np.uint8)
        self.edge = cv2.dilate(m.astype(np.uint8), k).astype(bool) & ~m
        self.edge2 = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~m & ~self.edge
        inner = cv2.erode(m.astype(np.uint8), k).astype(bool)
        self.rim = m & ~inner
        # interior scene (static part)
        bg = np.zeros((H, W, 4), np.uint8)
        for y in range(H):
            bg[y, :, :3] = mix(C('#a8d8ff'), C('#eaf6ff'), min(1.0, y / 58))[:3]
        hill = yy > 52 + 6 * np.sin(xx / 23.0) + 3 * np.sin(xx / 9.0 + 1)
        bg[hill, :3] = C('#9ad07a')[:3]
        ground = yy > 64
        bg[ground, :3] = C('#7ac060')[:3]
        g2 = ground & ((xx + yy * 3) % 11 == 0)
        bg[g2, :3] = C('#5aa048')[:3]
        for (cx, cy) in ((30, 16), (120, 22)):                                # clouds
            c = (((xx - cx) / 12.0) ** 2 + ((yy - cy) / 4.0) ** 2 < 1) | (((xx - cx - 6) / 7.0) ** 2 + ((yy - cy + 3) / 4.0) ** 2 < 1)
            bg[c, :3] = (255, 255, 255)
        bg[..., 3] = 255
        cv = _Cv(W, H); cv.a = bg
        fx = 78                                                               # the fence
        for px_ in (fx - 7, fx + 5):
            cv.rect(px_ - 1, 49, 4, 18, OUTL_K); cv.rect(px_, 50, 2, 16, C('#c89a6a')); cv.px(px_, 50, C('#e8c08a'))
        for ry_ in (54, 60):
            cv.rect(fx - 12, ry_ - 1, 24, 4, OUTL_K); cv.rect(fx - 11, ry_, 22, 2, C('#d8aa78')); cv.hline(fx - 11, ry_, 22, C('#f0c890'))
        self.bg = cv.a
        self.FX, self.GY = fx, 66

    def sheep_xy(self, u):
        x = -18 + (self.W + 20) * u
        d = (x + 8 - self.FX) / 30.0
        y = self.GY - 12 - 22 * max(0.0, 1 - d * d)
        return x, y

    def render(self, t):
        cv = _Cv(self.W, self.H); cv.a = self.bg.copy()
        if t < TL.T_RUSH0:
            for i, s0 in enumerate(TL.SHEEP):
                u = (t - s0) / TL.sheep_dur(i)
                if 0 <= u <= 1:
                    x, y = self.sheep_xy(u)
                    cv.blit(SHEEP_SPR[int(t * 8) % 2 if abs(x + 8 - self.FX) > 24 else 1], int(x), int(y))
        elif t < TL.T_DONE:                                                    # the stream runs away
            u = (t - TL.T_RUSH0) / (TL.T_DONE - TL.T_RUSH0)
            s = 160 * (t - TL.T_RUSH0) + 900 * (t - TL.T_RUSH0) ** 2.2
            gap = 26 - 12 * u
            n = int((self.W + 40) / gap) + 2
            for k in range(n):
                x = (s + k * gap) % (self.W + 40) - 20
                uu = (x + 18) / (self.W + 20)
                _, y = self.sheep_xy(uu)
                for g in range(3 if u > 0.3 else 1):                            # speed ghosts
                    cv.blit(SHEEP_SPR[k % 2], int(x - g * (6 + 10 * u)), int(y), alpha_mul=[1.0, 0.45, 0.2][g])
                if u > 0.35:
                    for j in range(3): cv.hline(int(x - 18 - 30 * u), int(y + 3 + j * 3), int(14 + 20 * u), (255, 255, 255, 160))
        else:                                                                  # done: one dizzy sheep left
            cv.blit(SHEEP_SPR[0], 112, self.GY - 12)
            if t > TL.T_DONE + 0.2:
                for k in range(3):
                    a_ = t * 5 + k * 2.1
                    cv.px(int(121 + 6 * math.cos(a_)), int(self.GY - 15 + 2 * math.sin(a_)), C('#ffd23f'))
        if t >= TL.T_DONE2:
            a = min(1.0, (t - TL.T_DONE2) / 0.15)
            s_ = '数完了。'; w_ = text_width(s_, 'zh12')
            cv.text((self.W - w_) // 2, 72, s_, (255, 255, 255, int(255 * a)), 'zh12', outline=OUTL_K)
        out = np.zeros((self.H + 4, self.W + 4, 4), np.uint8)
        a = cv.a; a[~self.m] = 0
        a[self.rim, :3] = (a[self.rim, :3] * 0.6 + 255 * 0.4).astype(np.uint8)
        out[2:-2, 2:-2][self.m] = a[self.m]
        out[2:-2, 2:-2][self.edge] = OUTL_K
        return out

    def draw(self, cv, t, head_xy, tl_xy):
        """thought dots from the head, then the bubble at tl_xy (UI px)."""
        hx, hy = head_xy; bx, by = tl_xy
        if t < TL.T_BUB0 or t >= TL.T_EYES + 0.2: return
        dots = [(hx + 10, hy - 8, 2.5), (hx + 18, hy - 18, 3.5), (hx + 28, hy - 30, 4.5)]
        for k, (dx, dy, r) in enumerate(dots):
            age = t - TL.T_BUB0 - 0.1 * k
            if age <= 0: continue
            kk = back_out(min(1.0, age / 0.15), 2.0)
            if t >= TL.T_EYES: kk *= max(0.0, 1 - (t - TL.T_EYES) / 0.1)
            if kk <= 0: continue
            cv.ellipse(dx, dy, r * kk + 1, r * kk + 1, OUTL_K); cv.ellipse(dx, dy, r * kk, r * kk, C('#ffffff'))
        age = t - TL.T_BUB1
        if age < 0: return
        k = back_out(min(1.0, age / 0.25), 1.6)
        alpha = 1.0
        if t >= TL.T_EYES:                       # pop!
            u = (t - TL.T_EYES) / 0.12
            k = 1.0 + 0.25 * min(1.0, u); alpha = max(0.0, 1 - u)
            ui.burst_lines(cv, bx + self.W // 2, by + self.H // 2, 60 + 40 * u, 80 + 60 * u, n=14, col=C('#ffffff'),
                           alpha=max(0.0, 1 - (t - TL.T_EYES) / 0.2))
        if alpha <= 0: return
        spr = self.render(t)
        ui.blit_scaled(cv, spr, bx + self.W // 2, by + self.H // 2, k, alpha)


# ====================================================================== TOWN : park / track / four / ask (900 x 270)
BENCH_B_X, SEAT_B = 252, 186
CAFE_A, CAFE_B, CAFE_C = 428, 362, 484          # sitters (left of tables 438 / 372 / 494)
CAFE_SEAT = 185
FRIEND_X = 452                                  # friend opposite the PPT guy (own chair)
BM_X0, BM_FOOT = 826, 189                       # best man behind the column
BM_X1 = 822                                     # ... at the mic (FOUR)
GROOM_X, BRIDE_X, MIC_X = 794, 778, 810
KITE_HAND = None
# speech-bubble anchors from the head tops
ANCH = {'uncle': (256, 143), 'cafe': (432, 142), 'quilt': (604, 62), 'bestman': (818, 128),
        'cafeB': (366, 142), 'cafeC': (488, 142)}

# ---------------------------------------------------------------- the best man's memory (warm, nostalgic thought bubble)
MEM_W, MEM_H = 168, 96                 # bubble size (UI px); the interior is painted at half res and doubled (chunky pixels)
MEM_TL = (306, 0)
AUTO_LIFE = [1.0, 1.15, 1.35, 1.5]
LIE_X_PUFF = 149.0
_MW, _MH = MEM_W // 2, MEM_H // 2

def _mem_static():
    W, H = _MW, _MH
    a = np.zeros((H, W, 4), np.float32)
    top, mid_, low = np.array(C('#b86a7e')[:3], np.float32), np.array(C('#f29a5a')[:3], np.float32), np.array(C('#ffd890')[:3], np.float32)
    for y in range(H):                                              # sunset sky in flat bands
        u = round(min(1.0, y / 30.0) * 7) / 7
        a[y, :, :3] = (top + (mid_ - top) * u * 2) if u < 0.5 else (mid_ + (low - mid_) * (u - 0.5) * 2)
    a[..., 3] = 255
    cv = _Cv(W, H); cv.a = a.astype(np.uint8)
    cv.ellipse(41.5, 27.5, 13, 13, C('#ffe7a8')); cv.ellipse(41.5, 27.5, 11, 11, C('#fff4cc'))                 # sun setting between the two kids
    cv.hline(26, 17, 14, C('#f6b07a')); cv.hline(50, 20, 12, C('#f6b07a')); cv.hline(60, 14, 9, C('#e89a7a'))   # thin clouds
    rng = np.random.default_rng(3); x = 0
    while x < W:                                                                                    # far roofs
        w_ = int(rng.integers(5, 10)); h_ = int(rng.integers(2, 5))
        cv.rect(x, 31 - h_, w_, h_ + 1, C('#b0605a')); x += w_
    cv.rect(9, 20, 4, 11, C('#a85856')); cv.rect(8, 19, 6, 2, C('#a85856')); cv.px(10, 23, C('#ffd2a0')); cv.px(11, 23, C('#ffd2a0'))
    cv.hline(0, 31, W, C('#ffc8a0')); cv.hline(0, 32, W, C('#e09a7a'))                               # wall coping
    cv.rect(0, 33, W, 9, C('#9c4e40'))
    for r in range(3):
        y0 = 33 + r * 3
        cv.hline(0, y0 + 2, W, C('#7a3a32'))
        for x0 in range((r % 2) * 3, W, 6): cv.vline(x0, y0, 2, C('#7a3a32'))
    cv.rect(0, 42, W, H - 42, C('#5a2e2e'))
    for (bx, col, col2) in ((17, C('#3a5a8a'), C('#5a7aaa')), (62, C('#b84a3a'), C('#d86a50'))):     # school bags on the wall
        cv.rect(bx - 1, 24, 8, 8, C('#2a1715')); cv.rect(bx, 25, 6, 6, col); cv.rect(bx, 25, 6, 2, col2)
        cv.px(bx + 3, 27, C('#ffd23f')); cv.hline(bx + 1, 22, 4, C('#2a1715')); cv.px(bx + 1, 23, C('#2a1715')); cv.px(bx + 4, 23, C('#2a1715'))
    return cv.a

def _kid(cv, x, y, nod=0):
    """a kid sitting on the wall, seen from behind, backlit by the sun (rim light on the right)."""
    SH, SH2, NV, RIM, HAIR = C('#efe2d0'), C('#cdbba8'), C('#2a3050'), C('#ffb070'), C('#3a2228')
    cv.rect(x - 5, y - 8, 11, 9, C('#2a1715')); cv.rect(x - 4, y - 9, 9, 1, C('#2a1715')); cv.rect(x - 4, y - 8, 9, 8, SH)   # white shirt
    cv.vline(x - 4, y - 8, 8, SH2)
    cv.rect(x - 4, y - 8, 9, 2, NV); cv.px(x, y - 6, NV)                                              # sailor collar
    cv.rect(x - 4, y - 1, 9, 1, NV)
    cv.vline(x + 4, y - 7, 6, RIM)
    hy = y - 13 + nod
    cv.rect(x - 1, hy + 3, 3, 3, C('#6a3a38'))                                                       # neck (backlit)
    cv.ellipse(x + 0.5, hy + 0.5, 5.2, 5.2, C('#2a1715')); cv.ellipse(x + 0.5, hy + 0.5, 4.2, 4.2, HAIR)   # head from behind
    cv.px(x + 3, hy - 2, RIM); cv.px(x + 4, hy - 1, RIM); cv.px(x + 4, hy, RIM)
    cv.px(x - 4, hy + 1, C('#e8b090'))                                                                # an ear

def mem_painter():
    base = _mem_static()
    yy, xx = np.mgrid[0:_MH, 0:_MW]
    glow0 = np.exp(-(((xx - 41) / 22.0) ** 2 + ((yy - 26) / 15.0) ** 2))
    vig = 1 - 0.30 * (((xx - _MW / 2) / (_MW / 2)) ** 2 + ((yy - _MH / 2) / (_MH / 2)) ** 2)
    def paint(t):
        cv = _Cv(_MW, _MH); cv.a = base.copy()
        age = t - TL.T_MEM0
        for i in range(3):                                                    # birds crossing the sun
            bx = int((age * 5 + i * 8) % (_MW + 12)) - 6; by = 12 + i * 3 + int(round(math.sin(age * 3 + i)))
            f = int(age * 5 + i) % 2
            for (dx, dy) in ((0, 0), (-1, -1 + f), (1, -1 + f)): cv.px(bx + dx, by + dy, C('#7a3a40'))
        _kid(cv, 35, 31, nod=1 if 1.0 < age < 1.3 else 0)
        _kid(cv, 47, 31)
        k = ease_io(ramp(age, 1.7, 2.2))                                      # ... and puts his arm round his friend
        if k > 0:
            pts = []
            for j in range(13):
                u = j / 12 * k
                pts.append((43 - 11 * u, 24 - 2.5 * math.sin(math.pi * min(1.0, u / max(k, 1e-3)) * 0.9) * k))
            for (px_, py_) in pts: cv.rect(int(round(px_)) - 1, int(round(py_)) - 1, 3, 3, C('#2a1715'))
            for (px_, py_) in pts: cv.px(int(round(px_)), int(round(py_)), C('#efe2d0'))
            hx_, hy_ = pts[-1]; cv.px(int(round(hx_)), int(round(hy_)), C('#e8b090'))
        a = cv.a[..., :3].astype(np.float32)
        a = a + (glow0 * (0.20 + 0.04 * math.sin(age * 2.2)))[..., None] * np.array([255, 200, 120], np.float32)
        a = (a * np.array([1.04, 0.97, 0.86], np.float32) + 14) * vig[..., None]
        a = a + np.random.default_rng(int(t * 12)).integers(-5, 6, (_MH, _MW, 1)).astype(np.float32)
        out = np.empty((_MH, _MW, 4), np.uint8); out[..., :3] = np.clip(a, 0, 255).astype(np.uint8); out[..., 3] = 255
        return np.repeat(np.repeat(out, 2, 0), 2, 1)
    return paint

def cam_four(t):
    if t < TL.T_F2:   # kite: wide on the park, sky
        u = ease_io(ramp(t, TL.T_F1, TL.T_F2)); return 1.75 + 0.08 * u, 214.0 + 6 * u, 118.0 - 4 * u
    if t < TL.T_F3:   # cafe
        u = ease_io(ramp(t, TL.T_F2, TL.T_F3)); return 2.6 + 0.12 * u, 444.0, 160.0
    if t < TL.T_F4:   # window
        u = ease_io(ramp(t, TL.T_F3, TL.T_F4)); return 3.4 + 0.15 * u, 604.0, 72.0
    u = ease_io(ramp(t, TL.T_F4, TL.T_ASK)); return 2.15 + 0.10 * u, 800.0, 150.0
def cam_ask(t):
    u = ease_io(ramp(t, TL.T_ASK, TL.DUR))
    return 2.7 + 0.25 * u, ASK_X + 14 - 2 * u, 166.0
ASK_X = 738.0

class TownShot:
    def __init__(self, OW=1920, OH=1080):
        self.tw = Town()
        self.sc = OutdoorScene(self.tw.bg, OW=OW, OH=OH)
        self.OW, self.OH = OW, OH
        self.pp = People()
        self.col = self.tw.column_sprite()
        cans = [(c['cx'], c['cy'] - c['ry'] * 0.4, c['cy'] + c['ry'] * 0.6, c['rx'] * 0.7) for c in self.tw.canopies]
        self.leaves = FallingLeaves(cans, ground=(194, 224), per_tree=3, seed=9)
        self.motes = Motes2D(self.tw.W, self.tw.H, n=300, seed=14)
        self.mote_vis = np.clip(self.tw.T, 0, 1) * 0.6 + 0.25
        self.walkers = [WK.Walker(li, x0, v, foot, prop, t0, seed=sd) for (li, x0, v, foot, prop, t0, sd) in (
            ('cap_runner', 760.0, -40.0, 190, None, TL.T_TRACK, 11), ('hoodie_long', 300.0, 14.0, 188, 'bag', TL.T_TRACK, 12))]
        self.chair = chair_sprite(flip=True)
        self.mic = mic_sprite()
        self.dream = DreamBubble()
        self.memory = ui.ThoughtBubble(MEM_W, MEM_H, edge=OUTL_K, rim_k=0.35, rim_col=(255, 236, 200))
        self.mem_interior = mem_painter()
        self.tables = {}

    # ------------------------------------------------------------------ state
    def state(self, t, warm=0.0):
        st = outdoor_state('morning', **LOOK)
        st['grade'].update(sat=1.22, contrast=1.20, black=0.045)
        if warm > 0: warm_grade(st['grade'], warm)
        return st

    def put_person(self, mid, casters, s, x, ground=None, seat=None, k_sh=0.5):
        if seat is not None: X, Y = int(round(x - s.ax)), int(round(seat - s.seat_y))
        else: X, Y = int(round(x - s.ax)), int(round(ground - s.fy))
        mid.put(s.rgba, X, Y, 0, E=s.E)
        casters.append((s.al, X, Y, (ground if ground is not None else seat + 12), k_sh))
        return X, Y

    def table(self, lid):
        k = round(lid, 2)
        if k not in self.tables: self.tables[k] = self.tw.table_sprite(lid=k)
        return self.tables[k]

    # ------------------------------------------------------------------ who does what, when
    def extras(self, t, mode, mid, casters):
        pp = self.pp
        four = mode == 'FOUR'
        if mode == 'TRACK':
            for wk in self.walkers:
                for (rgba, X, Y, E, al, foot) in wk.sprites(t):
                    if X > self.tw.W or X + rgba.shape[1] < 0: continue
                    mid.put(rgba, X, Y, 0, E=E)
                    if foot is not None: casters.append((al, X, Y, foot, 0.5))
        # --- the uncle on bench B (weekly report on the phone) / F1: sighs, phone down, catches a runaway kite
        f1 = four and t < TL.T_F2
        if f1 and t >= TL.T_U_STAND:
            s = pp.get('uncle', 'stand', 0, 'point', 'blink' if blink_at(t, [TL.T_U_STAND + 1.1]) else 'happy')
            X, Y = self.put_person(mid, casters, s, BENCH_B_X + 4, ground=192)
            hx, hy = X + s.hands[1][0], Y + s.hands[1][1]
            kx, ky = kite_xy(t)
            ln, lx, ly = line_sprite(hx, hy, kx + 6, ky + 14, C('#f4ecdc'), sag=6 * (1 - 0.5 * ramp(t, TL.T_U_STAND, TL.T_U_STAND + 0.6)))
            mid.put(ln, lx, ly, 0)
            ks, ke = kite_sprite(t); mid.put(ks, int(kx), int(ky), 0, E=ke)
        else:
            face, arms = 'down', 'phone'
            if mode == 'TRACK' and TL.STATIONS[0][1] <= t < TL.STATIONS[0][1] + 1.6: face = 'talk' if int(t * 8) % 2 else 'down'
            if f1:
                if t >= TL.T_F1 + TL.POP_AUTO + 0.45: face = 'surprised'
                if t >= TL.T_U_SIGH: face = 'tired'
                if t >= TL.T_U_DOWN: arms, face = 'down', 'closed'
                if t >= TL.T_U_LOOK: face = 'surprised'
            s = pp.get('uncle', 'sit', 0, arms, face)
            self.put_person(mid, casters, s, BENCH_B_X, seat=SEAT_B, k_sh=0.4)
            if f1 and t >= TL.T_KITE_IN:                      # the runaway kite drifts over, its string trailing down
                kx, ky = kite_xy(t)
                ex, ey = kite_free_end(t)
                ln, lx, ly = line_sprite(kx + 6, ky + 14, ex, ey, C('#f4ecdc'), sag=4)
                mid.put(ln, lx, ly, 0)
                ks, ke = kite_sprite(t); mid.put(ks, int(kx), int(ky), 0, E=ke)
        if f1 and t >= TL.T_U_DOWN:                           # the phone left face-down on the bench
            ph = np.zeros((2, 6, 4), np.uint8); ph[...] = (40, 40, 52, 255); mid.put(ph, BENCH_B_X - 14, SEAT_B - 2, 0)
        # --- cafe terrace: sitters, the friend's chair, then the tables in front
        f2 = four and TL.T_F2 <= t < TL.T_F3
        lid = 1.0
        if four and t >= TL.T_F2:
            lid = 1.0 - ease_io(ramp(t, TL.T_LID0, TL.T_LID1))
        mid.put(self.chair, FRIEND_X - 4, 196 - 22, 0)
        fface, farms = 'down', 'phone'
        if f2:
            if t >= TL.T_C_ASK - 0.35: fface, farms = 'normal', 'down'
            if TL.T_C_ASK <= t < TL.T_C_ASK + 1.4: fface = 'talk' if int(t * 7) % 2 else 'normal'
            elif t >= TL.T_C_ASK + 1.4: fface = 'happy'
        elif four and TL.T_F3 <= t < TL.T_F4: fface, farms = 'happy', 'down'
        s = pp.get('bun_cardigan', 'sit', 0, farms, fface, flip=True)
        self.put_person(mid, casters, s, FRIEND_X, seat=CAFE_SEAT, k_sh=0.35)
        for (nm, x, arms) in (('pony_jacket', CAFE_B, 'type'), ('side_shirt', CAFE_A, 'type'), ('bob_dress', CAFE_C, 'type')):
            face = 'focus'
            a_ = arms
            if nm == 'side_shirt':
                if mode == 'TRACK' and TL.STATIONS[1][1] <= t < TL.STATIONS[1][1] + 1.4: face = 'talk' if int(t * 8) % 2 else 'focus'
                if f2:
                    if t >= TL.T_C_STOP: a_ = 'down'; face = 'surprised'
                    if t >= TL.T_C_STOP + 0.55: face = 'tired'
                    if t >= TL.T_C_ASK + 0.6: face = 'normal'
                    if t >= TL.T_LID0: face = 'soft'
                    if t >= TL.T_TURN: face = 'talk' if (t < TL.T_TURN + 0.6 and int(t * 7) % 2) else 'happy'
                elif four and TL.T_F3 <= t < TL.T_F4: a_, face = 'down', 'happy'
            if blink_at(t, [TL.T_TRACK + 1.9 + (x % 7) * 0.3, TL.T_TRACK + 7.2 + (x % 5) * 0.4, TL.T_TURN + 0.9]) and face in ('focus', 'normal', 'happy'): face = 'blink'
            s = pp.get(nm, 'sit', 0, a_, face)
            self.put_person(mid, casters, s, x, seat=CAFE_SEAT, k_sh=0.35)
        for (tx, foot) in self.tw.A['tables']:
            rgba, E, ox, oy = self.table(lid if tx == 438 else 1.0)
            mid.put(rgba, tx - ox, foot - oy, 0, E=E)
        # --- wedding: best man (behind the column) / at the mic; the couple appears in FOUR / ASK
        wed = (four and t >= TL.T_F4) or mode == 'ASK'
        if wed:
            gface, garms = 'happy', 'down'
            if t >= TL.T_BM3: gface = 'soft'
            if t >= TL.T_CRY: gface, garms = 'cry', 'wipe'
            s = pp.get('bride', 'stand', 0, 'down', 'happy' if t < TL.T_CRY + 0.5 else 'soft')
            self.put_person(mid, casters, s, BRIDE_X, ground=191)
            s = pp.get('groom', 'stand', 0, garms, gface)
            self.put_person(mid, casters, s, GROOM_X, ground=191)
            mid.put(self.col[0], self.col[1], self.col[2], 0)
            mid.put(self.mic[0], MIC_X - 4, 190 - 43, 0)
            bface = 'tired'
            if t >= TL.T_BM1: bface = 'sad'
            if t >= TL.T_BM2: bface = 'soft'
            for (tb, txt) in TL.BM_LINES:
                if tb <= t < tb + min(1.3, 0.12 * len(txt)) and int(t * 7) % 2: bface = 'talk'
            if mode == 'ASK': bface = 'happy'
            s = pp.get('suit', 'stand', 0, 'hold', bface, flip=True)
            self.put_person(mid, casters, s, BM_X1, ground=192)
        else:
            face = 'focus'
            if mode == 'TRACK':
                td = TL.STATIONS[3][1]
                if td <= t < td + 2.0: face = 'shock' if t < td + 0.6 else 'talk' if int(t * 8) % 2 else 'focus'
            s = pp.get('suit', 'stand', 0, 'phone', face, flip=True)
            self.put_person(mid, casters, s, BM_X0, ground=BM_FOOT)
            mid.put(self.col[0], self.col[1], self.col[2], 0)

    def claude(self, t, mode):
        if mode == 'PARK': return TL.claude_park(t)
        if mode == 'FAIL': return TL.claude_fail(t)
        if mode == 'TRACK': return TL.claude_track(t)
        if mode == 'ASK':
            d = dict(x=ASK_X, foot=TL.FOOT, pose='stand', arms='down', face='q', phase=0, look=(1, -1), hop=0.0)
            if t < TL.T_TILT: d['face'] = 'normal'; d['look'] = (2, 0)
            if blink_at(t, [TL.T_ASK + 3.0, TL.T_ASK + 5.4]): d['face'] = 'blink'
            return d
        return None

    # ------------------------------------------------------------------ UI
    def side_quest(self, cv, t, t0, title, state='active', t_state=None, alpha=1.0, new_tag=True):
        return ui.quest_bar(cv, t, t0, title, (0, 1), kind='支线任务', kind_en='SIDE QUEST', state=state, t_state=t_state,
                            y=8, alpha=alpha, new_tag=new_tag)

    def ui(self, t, mode, cam):
        cv = ui.UICanvas()
        if mode in ('PARK', 'FAIL', 'TRACK'):
            a = 1.0 if mode != 'PARK' else 1.0 - ramp(t, TL.T_PUSH0, TL.T_PUSH0 + 0.4)
            hh = {'PARK': '09:40', 'FAIL': '10:05', 'TRACK': '10:20'}[mode]
            if a > 0:
                ui.hud_time(cv, 8, 8, hh, day='周六', day_en='SAT', alpha=a)
                ui.status_badge(cv, 472, 8, 'off', alpha=a)
        if mode == 'PARK':
            # side quests: 睡个懒觉 (pops when he sees the bench, makes room for the sheep counter, comes back to fail)
            a1 = 1.0 - ramp(t, TL.T_BUB0 - 0.4, TL.T_BUB0)
            if TL.T_SQ1 <= t < TL.T_BUB0:
                self.side_quest(cv, t, TL.T_SQ1, '睡个懒觉', alpha=a1)
            a1b = 1.0 - ramp(t, TL.T_SQ2 - 0.35, TL.T_SQ2 - 0.05)
            if TL.T_SQ1_BACK <= t and a1b > 0:
                self.side_quest(cv, t, TL.T_SQ1_BACK, '睡个懒觉', state='fail', t_state=TL.T_SQ1_FAIL, alpha=a1b, new_tag=False)
            a2 = 1.0 - ramp(t, TL.T_PUSH0, TL.T_PUSH0 + 0.35)
            if t >= TL.T_SQ2 and a2 > 0:
                self.side_quest(cv, t, TL.T_SQ2, '散个步', alpha=a2)
            # landing puffs
            if TL.T_LIE - 0.05 <= t < TL.T_LIE + 0.5:
                px_, py_ = cam.w2ui(LIE_X_PUFF, 179, U4); ui.dust_puff(cv, px_, py_, t - TL.T_LIE + 0.05, spread=22)
            if TL.T_HOPOFF + 0.28 <= t < TL.T_HOPOFF + 0.8:
                px_, py_ = cam.w2ui(TL.STAND_X + 4, TL.FOOT, U4); ui.dust_puff(cv, px_, py_, t - TL.T_HOPOFF - 0.28)
            # try #1: zzz -> eyes pop -> 数羊试试
            hx, hy = cam.w2ui(134, 150, U4)
            ui.zzz(cv, hx, hy - 6, t, TL.T_Z0, TL.T_EYES0 - 0.5)
            if TL.T_EYES0 <= t < TL.T_EYES0 + 0.45:
                ex, ey = cam.w2ui(120, 158, U4)
                ui.burst_lines(cv, ex, ey, 10, 18, n=7, col=C('#fff3df'), alpha=1 - (t - TL.T_EYES0) / 0.45)
            if TL.T_SHEEP0 <= t < TL.T_EYES + 0.6:
                sheep_counter(cv, t)
            hx, hy = cam.w2ui(124, 166, U4)
            self.dream.draw(cv, t, (hx, hy), (hx + 34, hy - 128))
            if TL.T_EYES <= t < TL.T_EYES + 0.5:
                ex, ey = cam.w2ui(120, 158, U4)
                ui.burst_lines(cv, ex, ey, 10, 18, n=7, col=C('#fff3df'), alpha=1 - (t - TL.T_EYES) / 0.5)
            if TL.T_MAPFACE <= t < TL.T_MAPFACE + 0.35:                  # the map icon lights up on his face
                fx, fy = cam.w2ui(*TL.claude_face_xy(TL.claude_park(t)), U4)
                u = (t - TL.T_MAPFACE) / 0.35
                ui.burst_lines(cv, fx, fy, 14 + 30 * u, 22 + 44 * u, n=10, col=C('#9fe8ff'), alpha=1 - u)
        if mode == 'FAIL':
            qa = 1.0 - ramp(t, TL.T_SQ3 - 0.35, TL.T_SQ3 - 0.05)
            if t >= TL.T_UNMAP and qa > 0:
                self.side_quest(cv, t, TL.T_UNMAP, '散个步', state='fail', t_state=TL.T_QFAIL, alpha=qa, new_tag=False)
        if mode in ('FAIL', 'TRACK') and t >= TL.T_SQ3:
            qa = 1.0 - ramp(t, TL.T_TRACK + 1.5, TL.T_TRACK + 1.9)
            if qa > 0: self.side_quest(cv, t, TL.T_SQ3, '随便逛逛', alpha=qa)
        if mode == 'TRACK':
            for (who, td, txt, anc, side) in TL.STATIONS:
                ax, ay = cam.w2ui(*ANCH[who], U4)
                age = t - td
                life = TL.STATION_LIFE_BM if who == 'bestman' else TL.STATION_LIFE
                if 0 <= age < life:
                    if age < 0.35:
                        ui.burst_lines(cv, ax, ay - 8, 6 + age * 30, 10 + age * 40, n=8, col=ui.GOLD, alpha=1 - age / 0.35)
                    ui.speech_bubble(cv, ax, ay, txt, age, life=life, side=side, with_coin=False, fname='zh10')
            for (td, txt, anc, side) in TL.CAFE_EXTRA:
                key = 'cafeB' if side < 0 else 'cafeC'
                ax, ay = cam.w2ui(*ANCH[key], U4)
                age = t - td
                if 0 <= age < TL.STATION_LIFE - 0.4:
                    ui.speech_bubble(cv, ax, ay, txt, age, life=TL.STATION_LIFE - 0.4, side=side, with_coin=False, fname='zh8', rise=2)
        if mode == 'FOUR':
            i = TL.four_i(t); t0 = (TL.T_F1, TL.T_F2, TL.T_F3, TL.T_F4)[i]
            anc = (ANCH['uncle'], ANCH['cafe'], ANCH['quilt'], (BM_X1 - 4, 128))[i]
            ax, ay = cam.w2ui(*anc, U4)
            ui.auto_bubble(cv, ax, ay, t - t0 - TL.POP_AUTO, life=AUTO_LIFE[i], side=1)
            if i == 0 and TL.T_U_SIGH <= t < TL.T_U_SIGH + 0.9:                     # 唉……
                ui.speech_bubble(cv, ax, ay, '唉……', t - TL.T_U_SIGH, life=0.9, side=-1, with_coin=False, fname='zh10', rise=2)
            if i == 1:
                if t >= TL.T_C_ASK:
                    bx, by = cam.w2ui(FRIEND_X - 2, 142, U4)
                    ui.speech_bubble(cv, bx, by, '连 Claude 都放假了，咱也歇会儿？', t - TL.T_C_ASK, life=TL.T_TURN + 0.15 - TL.T_C_ASK,
                                     side=1, with_coin=False, fname='zh10')
                if t >= TL.T_TURN + 0.05:
                    ui.speech_bubble(cv, ax, ay, '走！', t - TL.T_TURN - 0.05, life=TL.T_F3 - TL.T_TURN, side=-1, with_coin=False, fname='zh12')
            if i == 3:
                for j, (tl_, txt) in enumerate(TL.BM_LINES):
                    end = TL.BM_LINES[j + 1][0] if j + 1 < len(TL.BM_LINES) else TL.T_CRY + 1.4
                    if tl_ <= t < end:
                        ui.speech_bubble(cv, ax, ay, txt, t - tl_, life=end - tl_, side=-1, with_coin=False, fname='zh10')
                hx, hy = cam.w2ui(BM_X1 - 2, 124, U4)
                self.memory.draw(cv, t, TL.T_MEM0, (hx + 6, hy - 6), MEM_TL, self.mem_interior, t_out=TL.T_CRY + 0.6,
                                 dot_col=C('#fff3df'))
        if mode == 'ASK' and t >= TL.T_Q:
            qx, qy = cam.w2ui(ASK_X + 10, 134, U4)
            k = back_out(min(1.0, (t - TL.T_Q) / 0.2), 2.0)
            if k > 0.05:
                ui.big_text(cv, int(qx), int(qy - 20 * k), '?', C('#ffd23f'), 'p2p', 2, shadow=OUTL_K)
        ui.narration(cv, t, TL.BOXES)
        return cv.a

    # ------------------------------------------------------------------ frame
    def cam(self, t, mode):
        if mode == 'PARK': z, cx, cy = TL.cam_park(t)
        elif mode == 'FAIL': z, cx, cy = TL.cam_fail(t)
        elif mode == 'TRACK': z, cx, cy = TL.cam_track(t)
        elif mode == 'FOUR': z, cx, cy = cam_four(t)
        else: z, cx, cy = cam_ask(t)
        cam = Cam(z, cx, cy, W=480, H=270, OW=self.OW, OH=self.OH)
        hw, hh = 240 / z, 135 / z
        cam.cx = min(max(cam.cx, hw), self.tw.W - hw); cam.cy = min(max(cam.cy, hh), 270 - hh)
        return cam

    def face_rect(self, t, mode):
        """output-px rect of Claude's face screen (where the map opens / folds back)."""
        d = self.claude(t, mode); cam = self.cam(t, mode)
        hop = d.get('hop', 0.0)
        X0, Y0 = cam.w2o(d['x'] - 10, d['foot'] - 46 + hop); X1, Y1 = cam.w2o(d['x'] + 18, d['foot'] - 25 + hop)
        return float(X0), float(Y0), float(X1), float(Y1)

    def frame(self, t, mode):
        cam = self.cam(t, mode)
        warm = 0.0
        if mode == 'FOUR': warm = TL.WARM[TL.four_i(t)]
        if mode == 'ASK': warm = TL.WARM[3]
        st = self.state(t, warm)
        mid = GLayer(self.tw.W, self.tw.H); casters = []
        self.extras(t, mode, mid, casters)
        for (rgba, X, Y) in self.leaves.sprites(t): mid.put(rgba, X, Y, 0)
        d = self.claude(t, mode)
        if d is not None:
            if d['pose'] == 'lie':
                p = CL.draw(face=d['face'], arms='pillow', pose='lie', led='off')
                X, Y = int(round(d['x'] - 35)), int(round(188 - 60 + d.get('hop', 0.0)))
                mid.put(p.body.rgba, X, Y, 0, E=p.body.E)
                casters.append((p.body.cv.a[..., 3] > 127, X, Y, 197, 0.5))
            else:
                p, X, Y, al = claude_sprite(d)
                mid.put(p.body.rgba, X, Y, 0, E=p.body.E); mid.put(p.hands.rgba, X, Y, 0, E=p.hands.E)
                casters.append((al, X, Y, d['foot'], 1.0 if d.get('hop', 0.0) > -6 else 0.7))
        # bedroom window: phone glow under the quilt -> goes dark -> a crack of sun -> curtains open -> quilt off, stretch
        if mode == 'FOUR' and TL.T_F3 <= t:
            phone = 1.0 - ramp(t, TL.T_GLOW_OFF, TL.T_GLOW_OFF + 0.15)
            cur = 0.12 * ease_out3(ramp(t, TL.T_CRACK, TL.T_CRACK + 0.35)) + 0.88 * ease_io(ramp(t, TL.T_CURT0, TL.T_CURT1))
            sun = 0.3 * ease_io(ramp(t, TL.T_CRACK, TL.T_CRACK + 0.5)) + 0.7 * ease_io(ramp(t, TL.T_CURT0 + 0.2, TL.T_CURT1 + 0.4))
            if t < TL.T_QUILT: qp = self.tw.quilt_patch(cur, 'bulge', phone, sun)
            else:
                sl = sleeper_bust(stretch=1.0 if t > TL.T_QUILT + 0.5 else 0.0, face_open=t > TL.T_QUILT + 0.25)
                qp = self.tw.quilt_patch(cur, 'off', 0.0, sun, sleeper=sl)
        else:
            qp = self.tw.quilt_patch(0.0, 'bulge', 1.0, 0.0)
        patches = [(qp[0], qp[2], qp[3], qp[1])]
        motes = self.motes.render_out(t, cam, self.mote_vis, gain=0.45 + 0.4 * warm)
        return self.sc.render(cam, st, mid, casters, ui=self.ui(t, mode, cam), frame=int(round(t * TL.FPS)), bg_patches=patches,
                              front_i=self.tw.front_index(t), add_out=motes)


# ====================================================================== PATH : top-down park map + BFS (15.5 - 24.5)
def mini2(direction, phase):
    """claude_mini at x2 (RPG overworld sprites read bigger than the tiles)."""
    a, e = claude_mini(direction, phase)
    return np.repeat(np.repeat(a, 2, 0), 2, 1), np.repeat(np.repeat(e, 2, 0), 2, 1)

class PathShot:
    def __init__(self, OW=1920, OH=1080):
        self.pm = pm = ParkMap()
        self.fs = FlatScene(OW=OW, OH=OH)
        self.d, _ = pm.bfs(pm.S)
        self.maxd = int(self.d.max())
        self.route = pm.route([pm.S, *pm.CHECK, pm.S])
        self.pts = [pm.cell_c(c) for c in self.route]
        seg = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(self.pts[:-1], self.pts[1:])]
        self.cum = np.concatenate([[0], np.cumsum(seg)])
        ci, k = [], 0
        for n, c in enumerate(self.route):
            if k < 3 and c == pm.CHECK[k]: ci.append(n); k += 1
        self.check_i = ci
        self.L = self.fs.ambient((1.0, 0.97, 0.90), 1.05, top=1.04, bottom=0.94)
        self.g = dict(post.GRADES['golden_hd2d']); self.g.update(vignette=0.28, bloom=dict(self.g['bloom'], strength=0.7))

    def run_u(self, t):
        u = clamp01((t - TL.T_RUN0) / (TL.T_RUN1 - TL.T_RUN0))
        return u * u * (3 - 2 * u) * 0.25 + u * 0.75
    def pos(self, u):
        s = u * self.cum[-1]
        i = int(np.searchsorted(self.cum, s, side='right') - 1); i = min(max(i, 0), len(self.pts) - 2)
        a, b = self.pts[i], self.pts[i + 1]
        f = (s - self.cum[i]) / max(1e-6, self.cum[i + 1] - self.cum[i])
        x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        dx, dy = b[0] - a[0], b[1] - a[1]
        dirn = ('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else ('down' if dy > 0 else 'up')
        return x, y, dirn, i

    def frame(self, t):
        pm = self.pm
        img = pm.cv.a.copy(); E = pm.E.copy()
        plan = ramp(t, TL.T_GRID0, TL.T_GRID0 + 0.3) * (1 - ramp(t, TL.T_RUN0 - 0.2, TL.T_RUN0 + 0.3))
        if plan > 0: img[..., :3] = (img[..., :3].astype(np.float32) * (1 - 0.30 * plan) + np.array([10, 30, 60]) * 0.30 * plan).astype(np.uint8)
        gk = ease_io(ramp(t, TL.T_GRID0, TL.T_GRID1))
        if t < TL.T_RUN0: pm.draw_grid(img, E, gk)
        if TL.T_BFS0 <= t < TL.T_RUN0:
            wave = (self.maxd + 2) * ramp(t, TL.T_BFS0, TL.T_BFS1)
            pm.draw_bfs(img, E, self.d, wave)
        ur = ease_io(ramp(t, TL.T_ROUTE0, TL.T_ROUTE1))
        done = set()
        if t >= TL.T_RUN0:
            _, _, _, i = self.pos(self.run_u(t))
            done = {n for n, ci in enumerate(self.check_i) if i >= ci}
        if ur > 0:
            # the route fades while it is being walked (consumed behind Claude)
            if t < TL.T_RUN0: pm.draw_route(img, E, self.route, ur, t=t)
            else:
                _, _, _, i = self.pos(self.run_u(t))
                if t < TL.T_RUN1: pm.draw_route(img, E, self.route[i:], 1.0, t=t)
        if t >= TL.T_GRID1: pm.draw_flags(img, E, ramp(t, TL.T_GRID1, TL.T_GRID1 + 0.6) * 1.2, t, done)
        # Claude
        if t < TL.T_RUN0:
            x, y = self.pts[0]; dirn = 'right'; ph = 0
            bob = int(t * 2) % 2
            spr, e = mini2(dirn, 0)
            blit_np(img, E, spr, e, int(x - 12), int(y - 24 - bob))
        else:
            u = self.run_u(t)
            x, y, dirn, i = self.pos(u)
            running = t < TL.T_RUN1
            if running:
                for g in range(1, 6):                                          # after-images
                    xg, yg, dg, _ = self.pos(max(0.0, u - g * 0.012))
                    spr, e = mini2(dg, g)
                    blit_np(img, E, spr, e * 0.3, int(xg - 12), int(yg - 24), alpha=0.5 * (1 - g / 6))
                xs, ys, _, _ = self.pos(max(0.0, u - 0.08))
                for k in range(14):                                          # speed line / dust
                    xx = int(xs + (x - xs) * k / 14); yy = int(ys + (y - ys) * k / 14) + 2
                    if 0 <= xx < 480 and 0 <= yy < 270: img[yy, xx, :3] = (255, 236, 160); E[yy, xx] = 0.6 * k / 14
            else:
                dirn = 'down'
            spr, e = mini2(dirn, int(t * 16) if running else 0)
            blit_np(img, E, spr, e, int(x - 12), int(y - 24 - (0 if running else int(t * 3) % 2)))
        z = 1.0 + 0.05 * ease_io(ramp(t, TL.T_PATH, TL.T_FAIL))
        cam = Cam(z, 240, 135)
        return self.fs.render(cam, img, self.L, self.g, E=E, frame=int(round(t * TL.FPS)), ui=self.ui(t), emis_bloom=0.7)

    def ui(self, t):
        cv = ui.UICanvas()
        if t < TL.T_PLAN_OK:
            if t >= TL.T_GRID0:
                if t < TL.T_BFS0: txt, sub, pr = '扫描地形', 'GRID 32 x 18', ramp(t, TL.T_GRID0, TL.T_GRID1)
                else: txt, sub, pr = '路线规划中', f'BFS  {int(412 * ramp(t, TL.T_BFS0, TL.T_BFS1))}/412 CELLS', ramp(t, TL.T_BFS0, TL.T_ROUTE1)
                ui.hud_banner(cv, t, TL.T_GRID0, txt, sub=sub, progress=pr, y=8)
        elif t < TL.T_ACH - 0.1:
            ui.hud_banner(cv, t, TL.T_GRID0, '最优路线规划完成', sub=f'{len(self.route) - 1} STEPS  ETA 1.8 s', state='ok', t_state=TL.T_PLAN_OK,
                          t1=TL.T_ACH - 0.4, y=8)
        if t >= TL.T_RUN0:                                                    # stopwatch
            el = min(t, TL.T_RUN1) - TL.T_RUN0
            s_ = f'{el:05.2f}s'
            w = text_width(s_, 'p2p') + 34
            ui._hud_panel(cv, 472 - w, 8, w, 20)
            col = ui.GOLD if t < TL.T_RUN1 or int(t * 6) % 2 == 0 else C('#ffffff')
            cv.text(472 - w + 6, 12, '用时', ui.CREAM, 'zh10')
            cv.text(472 - w + 30, 14, s_, col, 'p2p')
            if t < TL.T_RUN1:
                n_done = sum(1 for ci in self.check_i if self.pos(self.run_u(t))[3] >= ci)
                cv.text(472 - w + 6, 32, f'检查点 {n_done}/3', ui.CREAM, 'zh8', outline=OUTL_K)
        if t >= TL.T_ACH:
            ui.achievement(cv, t, TL.T_ACH, '散步完成！', sub='用时 1.8 秒 · 效率 100%', life=TL.T_FAIL - TL.T_ACH + 0.4, y=196)
        return cv.a


# ====================================================================== AERIAL : the whole town at work (44 - 57)
REQ = ['周报！', 'PPT 改一下', 'Claude 在吗', '方案呢？', '表格！', '翻译一下', '写个文案', '回下邮件', '总结一下', '周一要！',
       '帮我看看', '会议纪要', '急！！', '报价单', '改简历', '写个总结', '做个图', 'Claude？', '在吗在吗', '数据呢']
SCREAMS = ['啊？！', '什么？！', '啊——', '休假？！', '诶？！']

class AerialShot:
    def __init__(self, OW=1920, OH=1080):
        self.ca = ca = CityAerial()
        self.fs = FlatScene(OW=OW, OH=OH)
        self.L = self.fs.ambient((1.0, 0.96, 0.88), 1.08, top=1.06, bottom=0.94)
        self.g = dict(post.GRADES['golden_hd2d']); self.g.update(vignette=0.36)
        self.claude_xy = (290, 210)
        rng = np.random.default_rng(5)
        cand = list(ca.windows) + list(ca.people)
        order = rng.permutation(len(cand))
        picks = []
        for i in order:
            x, y = cand[i]
            if all((x - a) ** 2 + (y - b) ** 2 > 16 ** 2 for (a, b) in picks) or len(picks) > 70:
                picks.append((x, y))
            if len(picks) >= 150: break
        N = len(picks)
        self.bub = []
        for k, (x, y) in enumerate(picks):
            tk = TL.T_BUBBLES0 + (TL.T_BUBBLES1 - TL.T_BUBBLES0) * (k / N) ** 0.55
            dist = math.hypot(x - self.claude_xy[0], y - self.claude_xy[1]) / 330.0
            tr = TL.T_REPLIES0 + (TL.T_REPLIES1 - TL.T_REPLIES0) * min(1.0, dist)
            self.bub.append(dict(x=x, y=y, t=tk, tr=tr, txt=REQ[int(rng.integers(len(REQ)))], side=1 if rng.random() < 0.6 else -1,
                                 scream=SCREAMS[int(rng.integers(len(SCREAMS)))] if rng.random() < 0.35 else None,
                                 ts=TL.T_SCREAM + rng.uniform(0, 0.35)))

    def cam(self, t):
        z, cx, cy = TL.cam_aerial(t)
        if t >= TL.T_SCREAM:
            a = max(0.0, 1 - (t - TL.T_SCREAM) / 0.7)
            cx += 3.0 * a * math.sin(t * 61); cy += 2.0 * a * math.sin(t * 47 + 1)
        hw, hh = 240 / z, 135 / z
        cx = min(max(cx, hw), 480 - hw); cy = min(max(cy, hh), 270 - hh)
        return Cam(z, cx, cy)

    def frame(self, t, cam=None):
        img = self.ca.cv.a.copy(); E = self.ca.E.copy()
        x, y = self.claude_xy
        spr, e = claude_mini('down', 0)
        blit_np(img, E, spr, e, x - 6, y - 12)
        cam = cam or self.cam(t)
        return self.fs.render(cam, img, self.L, self.g, E=E, frame=int(round(t * TL.FPS)), ui=self.ui(t, cam), emis_bloom=0.6)

    def ui(self, t, cam):
        cv = ui.UICanvas()
        cx, cy = cam.w2ui(*self.claude_xy, U4)
        # Claude pin (bobbing)
        if t < TL.T_BUBBLES0 + 2.0 or t >= TL.T_CITY_DING - 0.3:
            pa = 1.0 if t < TL.T_BUBBLES0 + 1.6 or t >= TL.T_CITY_DING - 0.3 else max(0.0, 1 - (t - TL.T_BUBBLES0 - 1.6) / 0.4)
            by = int(cy - 26 - 2 * math.sin(t * 5))
            if pa > 0:
                cv.rrect(int(cx - 18), by - 8, 36, 12, (27, 24, 48, int(220 * pa)), 3)
                cv.text(int(cx - 15), by - 7, 'CLAUDE', (255, 210, 63, int(255 * pa)), 'silkb')
                for j in range(4): cv.hline(int(cx - 3 + j), by + 4 + j, 6 - 2 * j, (27, 24, 48, int(220 * pa)))
        # requests piling up
        for b in self.bub:
            if t < b['t']: continue
            ax, ay = cam.w2ui(b['x'], b['y'], U4)
            if not (-30 < ax < 510 and -10 < ay < 290): continue
            if t < b['tr'] or t < TL.T_CITY_DING:
                ui.speech_bubble(cv, ax, ay, b['txt'], t - b['t'], life=99, side=b['side'], with_coin=False, fname='zh8', rise=1)
            elif b['scream'] is not None and t >= b['ts']:
                ui.speech_bubble(cv, ax, ay, b['scream'], t - b['ts'], life=99, side=b['side'], with_coin=False, fname='zh10', rise=2,
                                 fill=C('#fff0e8'), col=C('#c8302a'))
            else:
                age = t - b['tr']
                ui.speech_bubble(cv, ax, ay, '自动回复', age, life=99, side=b['side'], with_coin=False, fname='zh8', rise=1,
                                 fill=C('#2a2838'), col=C('#c8c4e0'))
        # the city-wide ding: a ring from Claude
        if TL.T_CITY_DING <= t < TL.T_CITY_DING + 0.9:
            u = (t - TL.T_CITY_DING) / 0.9; r = 20 + 560 * ease_out3(u)
            a = int(200 * (1 - u))
            for k in range(int(r * 6.3 / 2)):
                ang = k * 2 / r
                for dr in (0, 1, 2):
                    px_, py_ = int(cx + (r - dr) * math.cos(ang)), int(cy + (r - dr) * math.sin(ang) * 0.8)
                    if 0 <= px_ < 480 and 0 <= py_ < 270: cv.px(px_, py_, (255, 230, 160, a))
        # the auto-reply card
        if TL.T_CITY_DING + 0.1 <= t < TL.T_SCREAM + 0.1:
            k = back_out(min(1.0, (t - TL.T_CITY_DING - 0.1) / 0.2), 1.6)
            if t > TL.T_SCREAM - 0.1: k *= max(0.0, 1 - (t - TL.T_SCREAM + 0.1) / 0.2)
            cv.rect(0, 0, 480, 270, (12, 10, 24, int(120 * min(1.0, k))))
            card = _Cv(272, 66)
            card.rrect(2, 3, 268, 62, (0, 0, 0, 120), 5); card.rrect(0, 0, 268, 62, OUTL_K, 5)
            card.rrect(1, 1, 266, 60, C('#2a2838'), 5); card.hline(5, 2, 258, C('#45425a'))
            card.rrect(8, 10, 40, 40, C('#d97757'), 7)
            sp, _ = mini2('down', 0); card.blit(sp, 16, 16)
            card.text(58, 5, 'Claude · 自动回复', C('#a9a6c0'), 'zh10')
            card.text(58, 21, '您好，Claude 休假中。', C('#ffffff'), 'zh12')
            card.text(58, 39, '急事请自己想办法。', C('#ffd9a0'), 'zh12')
            ui.blit_scaled(cv, card.a, 240, 118, k)
        if t >= TL.T_SCREAM:
            age = t - TL.T_SCREAM
            k = back_out(min(1.0, age / 0.18), 2.4)
            s_ = '啊——？！'; w_ = text_width(s_, 'zh12') * 4
            jx = int(2 * math.sin(t * 70)) if age < 0.8 else 0
            ka = min(1.0, k)
            cv.rect(0, 92, 480, 64, (12, 10, 24, int(150 * ka)))
            ui.big_text(cv, 240 - w_ // 2 + jx + 3, int(100 - 10 * (1 - k)) + 3, s_, C('#c8302a'), 'zh12', 4, alpha=ka)
            ui.big_text(cv, 240 - w_ // 2 + jx, int(100 - 10 * (1 - k)), s_, C('#fff3df'), 'zh12', 4, shadow=OUTL_K, alpha=ka)
            if age < 0.4: ui.burst_lines(cv, 240, 122, 70 + age * 200, 100 + age * 260, n=18, col=C('#fff3df'), alpha=1 - age / 0.4)
        ui.narration(cv, t, TL.BOXES)
        return cv.a

    # ------------------------------------------------------------------ AFTER: the city calms down
    def after_setup(self):
        rng = np.random.default_rng(77)
        for b in self.bub:
            start = b['ts'] if (b['scream'] is not None and TL.T_FREEZE >= b['ts']) else b['tr']
            b['start'] = start
            b['tp'] = TL.T_AFTER + 0.2 + 1.7 * rng.random() ** 0.8
        self.birds = [(rng.uniform(-40, 0), rng.uniform(-14, 14), rng.uniform(0.9, 1.1), rng.uniform(0, 6)) for _ in range(9)]
        self.cam0 = self.cam(TL.T_FREEZE - 0.05)

    def cam_after(self, t):
        c0 = self.cam0
        u = ease_io(ramp(t, TL.T_AFTER, TL.T_F1 + 0.8))
        z = c0.zoom * 1.025 * (1 + 0.10 * u)
        cx = c0.cx + (self.claude_xy[0] - c0.cx) * 0.30 * u; cy = c0.cy + (self.claude_xy[1] - c0.cy) * 0.30 * u
        hw, hh = 240 / z, 135 / z
        cx = min(max(cx, hw), 480 - hw); cy = min(max(cy, hh), 270 - hh)
        return Cam(z, cx, cy)

    def frame_after(self, t):
        if not hasattr(self, 'cam0'): self.after_setup()
        img = self.ca.cv.a.copy(); E = self.ca.E.copy()
        x, y = self.claude_xy
        spr, e = claude_mini('down', 0)
        blit_np(img, E, spr, e, x - 6, y - 12)
        cam = self.cam_after(t)
        out = self.fs.render(cam, img, self.L, self.g, E=E, frame=int(round(t * TL.FPS)), ui=self.ui_after(t, cam), emis_bloom=0.6)
        out = out.astype(np.float32)
        s = 0.35 * (1 - ease_io(ramp(t, TL.T_AFTER + 0.5, TL.T_F1 - 0.2)))       # colour comes back
        w = ease_io(ramp(t, TL.T_AFTER + 0.8, TL.T_F1))                            # ... a touch warmer than before
        g = out.mean(-1, keepdims=True)
        out = out * (1 - s) + g * s
        out = out * np.array([1 + 0.035 * w, 1 + 0.01 * w, 1 - 0.04 * w], np.float32)
        return out

    def ui_after(self, t, cam):
        cv = ui.UICanvas()
        cx, cy = cam.w2ui(*self.claude_xy, U4)
        by = int(cy - 26 - 2 * math.sin(t * 5))
        cv.rrect(int(cx - 18), by - 8, 36, 12, (27, 24, 48, 220), 3)
        cv.text(int(cx - 15), by - 7, 'CLAUDE', (255, 210, 63, 255), 'silkb')
        for j in range(4): cv.hline(int(cx - 3 + j), by + 4 + j, 6 - 2 * j, (27, 24, 48, 220))
        for b in self.bub:
            ax, ay = cam.w2ui(b['x'], b['y'], U4)
            if not (-30 < ax < 510 and -10 < ay < 290): continue
            if t < b['tp']:
                age, life = t - b['start'], b['tp'] - b['start']
                if b['start'] == b['ts'] and b['scream'] is not None:
                    ui.speech_bubble(cv, ax, ay, b['scream'], age, life=life, side=b['side'], with_coin=False, fname='zh10', rise=2,
                                     fill=C('#fff0e8'), col=C('#c8302a'))
                else:
                    ui.speech_bubble(cv, ax, ay, '自动回复', age, life=life, side=b['side'], with_coin=False, fname='zh8', rise=1,
                                     fill=C('#2a2838'), col=C('#c8c4e0'))
            elif t < b['tp'] + 0.8:                                                 # the phone screen goes dark
                a = 1 - (t - b['tp']) / 0.8
                ix, iy = int(ax), int(ay)
                cv.rect(ix - 2, iy - 2, 4, 4, (160, 210, 255, int(70 * a)))
                cv.rect(ix - 1, iy - 1, 2, 2, (215, 238, 255, int(230 * a)))
        if t < TL.T_AFTER + 0.5:                                                    # the scream fades
            ka = 1 - ramp(t, TL.T_AFTER, TL.T_AFTER + 0.5)
            s_ = '啊——？！'; w_ = text_width(s_, 'zh12') * 4
            cv.rect(0, 92, 480, 64, (12, 10, 24, int(150 * ka)))
            ui.big_text(cv, 240 - w_ // 2 + 3, 103, s_, C('#c8302a'), 'zh12', 4, alpha=ka)
            ui.big_text(cv, 240 - w_ // 2, 100, s_, C('#fff3df'), 'zh12', 4, shadow=OUTL_K, alpha=ka)
        # a flock of birds crosses the quiet town
        u0 = (t - TL.T_AFTER - 0.6) / 2.6
        if 0 <= u0 < 1.2:
            for (ox, oy, sp, ph) in self.birds:
                bx = -30 + ox + 560 * u0 * sp; byy = 70 + oy - 18 * u0 + 3 * math.sin(u0 * 9 + ph)
                if not (-6 < bx < 486): continue
                f = int(t * 10 + ph) % 2
                bx, byy = int(bx), int(byy)
                col = (58, 46, 60, 235)
                for (dx, dy) in ((0, 0), (-2, -2 + 2 * f), (2, -2 + 2 * f), (-4, -2 + 4 * f), (4, -2 + 4 * f)):
                    cv.rect(bx + dx, byy + dy, 2, 2, col)
        return cv.a


class FreezeShot:
    """hold the last AERIAL frame (desaturating, very slow push) - wind only."""
    def __init__(self, aerial):
        self.a = aerial; self.img = None
    def frame(self, t):
        if self.img is None: self.img = self.a.frame(TL.T_FREEZE - 0.05).astype(np.float32)
        u = ease_io(ramp(t, TL.T_FREEZE, TL.T_AFTER))
        img = self.img
        g = img.mean(-1, keepdims=True)
        img = img * (1 - 0.35 * u) + g * 0.35 * u
        s = 1.0 + 0.025 * u
        H, W = img.shape[:2]
        M_ = np.float32([[s, 0, (1 - s) * W / 2], [0, s, (1 - s) * H / 2]])
        return cv2.warpAffine(img, M_, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


class Act3:
    def __init__(self, OW=1920, OH=1080, only=None):
        mk = lambda n: only is None or n in only
        self.ins = InShot(OW, OH) if mk('IN') else None
        self.street = StreetShot(OW, OH) if (mk('OUT') or mk('MED')) else None
        self.town = TownShot(OW, OH) if any(mk(n) for n in ('PARK', 'FAIL', 'TRACK', 'FOUR', 'F1', 'F2', 'F3', 'F4', 'ASK')) else None
        self.path = PathShot(OW, OH) if any(mk(n) for n in ('PARK', 'PATH', 'FAIL')) else None
        self.aerial = AerialShot(OW, OH) if any(mk(n) for n in ('AERIAL', 'FREEZE', 'AFTER')) else None
        self.freeze = FreezeShot(self.aerial) if self.aerial is not None else None
        E = edit.Edit()
        E.add('IN', 0.0, lambda t: self.ins.frame(t))
        E.add('OUT', TL.T_OUT, lambda t: self.street.frame(t))
        E.add('MED', TL.T_MED, lambda t: self.street.frame(t))
        E.add('PARK', TL.T_PARK, self.park, kind='fade', d=0.7)
        E.add('PATH', TL.T_PATH, lambda t: self.path.frame(t))
        E.add('FAIL', TL.T_FAIL, self.fail)
        E.add('TRACK', TL.T_TRACK, lambda t: self.town.frame(t, 'TRACK'))
        E.add('AERIAL', TL.T_AERIAL, lambda t: self.aerial.frame(t), kind='dissolve', d=0.7)
        E.add('FREEZE', TL.T_FREEZE, lambda t: self.freeze.frame(t))
        E.add('AFTER', TL.T_AFTER, lambda t: self.aerial.frame_after(t), kind='dissolve', d=0.6)
        E.add('F1', TL.T_F1, lambda t: self.town.frame(t, 'FOUR'), kind='dissolve', d=0.8)
        E.add('F2', TL.T_F2, lambda t: self.town.frame(t, 'FOUR'), kind='dissolve', d=0.4)
        E.add('F3', TL.T_F3, lambda t: self.town.frame(t, 'FOUR'), kind='dissolve', d=0.4)
        E.add('F4', TL.T_F4, lambda t: self.town.frame(t, 'FOUR'), kind='dissolve', d=0.4)
        E.add('ASK', TL.T_ASK, lambda t: self.town.frame(t, 'ASK'))
        E.end(TL.DUR)
        self.edit = E
    # the walk is planned ON his face screen: the map opens out of it (PARK) and folds back into it (FAIL)
    def park(self, t):
        img = self.town.frame(t, 'PARK')
        if t < TL.T_MAP0: return img
        k = ramp(t, TL.T_MAP0, TL.T_MAP1)
        return edit.screen_zoom(np.asarray(img, np.float32), np.asarray(self.path.frame(TL.T_PATH), np.float32),
                                self.town.face_rect(t, 'PARK'), k, t=t)
    def fail(self, t):
        img = self.town.frame(t, 'FAIL')
        if t >= TL.T_UNMAP: return img
        k = 1 - ramp(t, TL.T_FAIL, TL.T_UNMAP)
        return edit.screen_zoom(np.asarray(img, np.float32), np.asarray(self.path.frame(TL.T_FAIL - 1.0 / TL.FPS), np.float32),
                                self.town.face_rect(t, 'FAIL'), k, t=t)
    def frame(self, t):
        img = self.edit.frame(t)
        if t >= TL.T_FADE0: img = img * (1 - ease_io(ramp(t, TL.T_FADE0, TL.DUR - 0.05)))
        return img

def make(**kw): return Act3(**kw)
