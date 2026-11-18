"""EGG renderer: make() -> object with .frame(t) -> float RGB (1080, 1920, 3).   Shots + timing: timeline.py

Office shots = the Act V desk (bobber on its wooden base, desk calendar) at night with Wang Gong drawn live at his
desk (Act II), lit only by Claude's lamp + monitor and Wang's laptop.  The insert is the photo on Wang's desk
(pixelkit.sets.inserts.PhotoFrameInsert); the print itself is RENDERED from the Act IV pier world (a young father in
the same straw hat + a small boy sitting where Claude sat) and film-graded (inserts.film_print), so the hard cut to
the river can land exactly on the photo's framing before pulling back to the Act IV wide."""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math, importlib.util
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/egg'))
import numpy as np, cv2

def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m; sp.loader.exec_module(m); return m

TL = _load('egg_timeline', (_PROJ + '/egg/timeline.py'))
_A4TL = _load('a4_timeline', (_PROJ + '/act4/timeline.py'))
sys.modules['timeline'] = _A4TL
A4 = _load('a4_scene', (_PROJ + '/act4/scene.py'))      # Pier (the river world) + rod / line / bobber
sys.modules['timeline'] = TL

from pixelkit.sets.office import Office
from pixelkit.sets import props as P, dressing as DR, river_pier as RP, inserts as INS
from pixelkit.scene import World, GLayer, make_state
from pixelkit.camera import Cam
from pixelkit.characters import claude, human, backs
from pixelkit.core import C, Canvas, scale_nearest, sel_out, text_width
from pixelkit.anim import clamp01, ramp, ease_io, ease_out3
from pixelkit import ui, edit, perform as PF
from pixelkit.light import Sun
from pixelkit.outdoor import OutdoorScene
from pixelkit.particles import DustField
from pixelkit.cushot import CUShot, Layer, LightRig
from pixelkit.characters import closeup as CUC
from pixelkit.sets import cu_props as CP

U4 = 4
OM_X, OM_Y = RP.OLD_SEAT
SEAT_X, SEAT_Y = A4.TL.CL_X_END, A4.TL.CL_SEAT


# ====================================================================== the river (pixel world of Act IV, golden hour)
class River:
    def __init__(self, OW=1920, OH=1080):
        self.p = A4.Pier(OW, OH)
        rv = RP.RiverPier(0.0, sway_frames=24, sway_amp=2.6)                 # P3: smoother, livelier reeds
        self.p.rv0, self.p.sc0 = rv, OutdoorScene(rv.bg, OW=OW, OH=OH)
        self.drift = RP.DuskDrift(self.p.sc0, dusk_max=TL.DUSK_MAX)          # P3: the sun keeps sinking
        self.om_turn = backs.old_fisher_back(turn=-1)                          # P3: a readable head turn
        self.wang = {0: backs.wang_back(), 1: backs.wang_back(turn=1)}
        self.young = backs.old_fisher_back(young=True)
        self.kid = backs.kid_back()

    def mid(self, t, photo=False):
        mid = GLayer(480, 270)
        om = self.young if photo else self.p.om
        a, e = om.rgba, om.E
        if not photo:
            k = ease_io(ramp(t, TL.T_OLD_TURN0, TL.T_OLD_TURN0 + 0.3)) * (1 - ease_io(ramp(t, TL.T_OLD_TURN1, TL.T_OLD_TURN1 + 0.3)))
            if k > 0.5:                                                    # his head turns toward his son
                a, e = self.om_turn.rgba, self.om_turn.E
                a, e = PF.lean_rows(a, e, -1, 24, 30)
            if PF.breath_px(PF.on_twos(t), 4.6, 1.3): a, e = PF.shift_rows(a, e, 27, 1)
        mid.put(a, int(OM_X - om.ax), int(OM_Y - om.ay), 0, E=e)
        if photo: s = self.kid
        else:
            turn = 1 if TL.T_W_TURN0 <= t < TL.T_W_TURN1 else 0
            s = self.wang[turn]
        a, e = s.rgba, s.E
        if not photo and PF.breath_px(PF.on_twos(t), 4.0): a, e = PF.shift_rows(a, e, 34, 1)
        mid.put(a, int(SEAT_X - s.ax), int(SEAT_Y - s.ay), 0, E=e)
        cv, E = self.p.rod_and_line(t, bobber=True, birds=not photo, dusk=0.0)
        if not photo:
            RP.draw_birds(cv, RP.flock(t, TL.T_FLOCK, (236, 128), (17.0, -3.5), n=4, seed=3), C('#2e1e32'))
            mc = C('#ffe6b0')
            for (x, y, al) in RP.sun_motes(t, n=48, box=(200, 120, 430, 236)):
                xi, yi = int(round(x)), int(round(y))
                if 0 <= xi < 480 and 0 <= yi < 270 and cv.a[yi, xi, 3] == 0:
                    cv.px(xi, yi, mc[:3] + (int(170 + 85 * al),)); E[yi, xi] = 0.6 + 0.4 * al
        mid.put(cv.a, 0, 0, 0, E=E)
        return mid

    def world(self, t, cam, mid, photo=False):
        """Pier.render + P3: sinking sun (DuskDrift), star glints in the sun column, a violet drift."""
        p = self.p; p.t_now = t
        k = 0.0 if photo else TL.dusk_k(t)
        self.drift.apply(k)
        g = p.rv0.glitter(t)
        rgba, E = g[0].copy(), g[1].copy()
        if not photo: RP.draw_sparkles(rgba, E, RP.sparkles(t), g[2], g[3])
        img = p.sc0.render(cam, p.state(0.0), mid, [], frame=int(round(t * TL.FPS)), bg_patches=[(rgba, g[2], g[3], E)],
                           front_i=p.rv0.front_index(t))
        if k > 0:
            lum = img[..., :1] * 0.30 + img[..., 1:2] * 0.55 + img[..., 2:3] * 0.15
            img = img * (1 - 0.20 * k) + lum * np.array([0.95, 0.66, 1.10], np.float32) * (0.20 * k)
        return img

    def frame(self, t, cam, photo=False, ui_rgba=None, film_k=0.0, frame=0, age=None):
        """age (0..1, optional): the match dissolve inside the photo - 0 = the print's world (boy + young father),
        1 = today (Wang + the old man); in between both worlds are rendered and crossfaded."""
        if age is None: age = 0.0 if photo else 1.0
        if age <= 0.0: img = self.world(t, cam, self.mid(t, True), True)
        elif age >= 1.0: img = self.world(t, cam, self.mid(t, False), False)
        else:
            a = self.world(t, cam, self.mid(t, True), True)
            img = a + (self.world(t, cam, self.mid(t, False), False) - a) * age
        if film_k > 0: img = INS.film_grade(img, film_k, date="'97 8 16", frame=frame)   # still the photo, for a beat
        if ui_rgba is not None: img = A4.ui_over(img, ui_rgba, scale=U4)
        return img

    def photo_print(self, w=204, h=136):
        z, cx, cy = TL.PHOTO_CAM
        img = self.world(3.0, Cam(z, cx, cy, W=480, H=270), self.mid(3.0, photo=True), photo=True)
        return INS.film_print(img, w, h, date="'97 8 16")


# ====================================================================== the office at night (Act V desk + Wang live)
MOON = ((1.0, 0.42, 0.20), (0.52, 0.64, 1.0), 0.60)     # direction, colour, intensity of the light through the blinds
NIGHT_AMB = 0.82                                          # a darker room than v0 ...
LAMP_K = 1.25                                             # ... so the lamp / screens carry the shot

def night_points(lamp=1.0, wang=1.0):
    return [dict(x=197, y=138, r=46, col=(0.34, 0.66, 1.0), k=0.85, power=1.5, layers=('mid',)),
            dict(x=197, y=138, r=90, col=(0.20, 0.42, 0.85), k=0.38, power=1.5, layers=('bg',)),
            dict(x=180, y=152, r=40, col=(1.0, 0.72, 0.42), k=0.85 * lamp, power=1.6, layers=('mid',)),
            dict(x=180, y=152, r=70, col=(1.0, 0.62, 0.36), k=0.40 * lamp, power=1.7, layers=('bg',)),
            dict(x=393, y=34, r=30, col=(0.30, 1.0, 0.50), k=0.30, power=1.6, layers=('bg',)),
            dict(x=259.5, y=137, r=6, col=(0.35, 1.0, 0.55), k=0.5, power=1.4, layers=('mid',)),
            dict(x=370, y=150, r=30, col=(0.50, 0.78, 1.0), k=0.46 * wang, power=1.5, layers=('mid',)),
            dict(x=370, y=150, r=60, col=(0.25, 0.50, 0.85), k=0.32 * wang, power=1.6, layers=('bg',))]

class NightOffice:
    def __init__(self, OW=1920, OH=1080, mini_photo=None):
        self.OW, self.OH = OW, OH
        o = self.o = Office()
        self.bg = o.background(clock=None, lights_on=0.0, exit_on=1.0, tod='night', wang_live=True, dressing=True)
        self.sun = Sun(*MOON)                                   # cold street-light / moon through the blinds
        self.w = World(o.room, o.windows, OW=OW, OH=OH)
        self.w.set_background(self.bg, self.sun)
        self.rays = self.w.rig.god_rays(self.sun, o.windows, scale=0.25, steps=40)
        self.dust = DustField(o.room, n=1000, size=(0.6, 1.4), seed=77)
        self.chair = o.chair_sprite()
        self.fg = (o.foreground(), 1.18, 0.8, (0.10, 0.11, 0.20))
        self.stand = sel_out(DR.bobber_stand().rgba, 0.7)
        self.cal = sel_out(DR.desk_calendar().rgba, 0.6)
        self.bob = RP.bobber_fine()
        self.mug = sel_out(P.mug().rgba, 0.7)
        self.pen = sel_out(DR.pen_cup('#3f6fb0').rgba, 0.7)
        self.note = P.sticky('#f6d860', w=7, h=7, lines=2, seed=9).rgba
        o.draw_wang_desk(GLayer(), None, 1.0, 0.0)                     # builds the desk cache ...
        if mini_photo is not None: o._wang_cache['photo'] = mini_photo  # ... then the desk photo = the real print

    def state(self, t, shot=None):
        st = make_state('night', grade='night_hd2d')
        st.update(sun=self.sun, sun_color=self.sun.color, sun_int=MOON[2], sun_k=1.0, cast_shadows=True, shadow_k=0.7,
                  rays=0.55, rays_map=(self.rays, 0.5), emis_bloom=1.1, rim=0.25)
        st['amb'] *= NIGHT_AMB
        st['points'] = night_points(lamp=LAMP_K)
        if shot:                                   # close-ups: soften the room (pixel cells) + key / rim on the actor
            st['bg_soft'] = dict(sigma=0.9 if shot != 'm' else 0.7, bokeh_k=0.35)
            st['dust_k'] = 0.6
            if shot in ('c', 'm'):
                st['points'] = st['points'] + [
                    dict(x=226, y=110, r=34, col=(1.0, 0.74, 0.46), k=0.42, power=1.4, layers=('mid',)),   # lamp key, upper left
                    dict(x=282, y=118, r=22, col=(0.45, 0.62, 1.0), k=0.30, power=1.6, layers=('mid',))]   # cold rim, right
                fl = clamp01(1 - (t - TL.T_SUBMIT) / 0.6) if t >= TL.T_SUBMIT else 0.0
                if fl > 0:                           # 已提交: the monitor flashes green across the desk and Claude
                    st['points'] = st['points'] + [dict(x=200, y=136, r=48, col=(0.40, 1.0, 0.55), k=0.9 * fl, power=1.4, layers=('mid', 'bg'))]
            else:
                st['points'] = st['points'] + [
                    dict(x=372, y=152, r=26, col=(0.55, 0.80, 1.0), k=0.55, power=1.5, layers=('mid',)),   # laptop from below
                    dict(x=330, y=118, r=36, col=(1.0, 0.72, 0.45), k=0.22, power=1.5, layers=('mid',)),   # Claude's lamp, far left
                    dict(x=404, y=160, r=14, col=(1.0, 0.70, 0.45), k=0.25, power=1.6, layers=('mid',))]   # the photo's warmth
        return st

    def screen(self, t):
        """Claude's monitor: his own document -> 王工's 请假单 being filled -> 已提交 ✓"""
        cv = Canvas(30, 22)
        cv.rect(0, 0, 30, 22, C('#f2f2ee')); cv.rect(0, 0, 30, 4, C('#000080'))
        if t < TL.T_C_MED:
            n = int(clamp01(t / 3.0) * 7) + 3
            for i in range(min(n, 7)): cv.hline(2, 6 + i * 2, 24 if i % 3 != 2 else 15, C('#6a6a7a'))
            if (t * 2.2) % 1 < 0.6: cv.vline(2 + (15 if n % 3 == 2 else 24), 5 + min(n, 7) * 2 - 1, 2, C('#1a1a1a'))
            return cv.a
        cv.rect(0, 0, 30, 4, C('#a03a2a'))
        u = clamp01((t - TL.T_C_MED) / (TL.T_SUBMIT - TL.T_C_MED))
        for i in range(4):
            cv.hline(2, 7 + i * 3, 6, C('#8a8a9a'))
            cv.hline(10, 7 + i * 3, int(round(16 * clamp01(u * 4 - i))), C('#1f4fbf'))
        if t >= TL.T_SUBMIT:
            cv.rect(8, 6, 14, 11, C('#2a8a3a')); cv.rect(9, 7, 12, 9, C('#3aaa4a'))
            for (x, y) in ((11, 11), (12, 12), (13, 13), (14, 12), (15, 11), (16, 10), (17, 9)): cv.px(x, y, C('#ffffff'))
        return cv.a

    def desk_objects(self, t):
        a, e = self.bob
        ox, oy = TL.BOB_XY; sx_, sy_ = TL.STAND_XY; cx_, cy_ = TL.CAL_XY; mx, my = TL.MUG_XY
        return [(self.cal, cx_, cy_, 0.6, None), (self.stand, sx_, sy_, 0.3, None), (a, ox, oy, 0.4, e * 0.55),
                (self.mug, mx, my, 0.0, None), (self.pen, 219, 155, 0.2, None), (self.note, 212, 121, 1.0, None)]

    def claude_parts(self, d):
        hx, hy = TL.HEAD
        p0 = claude.draw()
        dy_sprite = int(round(TL.DESK_Y - (hy - p0.ay) - d['dy']))
        p = claude.draw(face=d['face'], arms=d['arms'], phase=d['phase'], led=d['led'], led_k=d['led_k'], look=d['look'],
                        glow=d['glow'], desk_y=dy_sprite, tilt=d['tilt'], head_dy=int(d['hdy']), spark_k=d.get('spark_k', 1.0),
                        ant=(int(round(d['ant'][0])), int(round(d['ant'][1]))))
        x0, y0 = hx - p.ax, hy - p.ay - d['dy']
        return (p.body.cv.a, p.body.E), (p.hands.cv.a, p.hands.E), int(round(x0)), int(round(y0))

    def mid(self, t):
        o = self.o
        mid = GLayer()
        mid.put(self.chair.rgba, 232, 128, o.Z['chair'])
        d = TL.claude_state(t)
        (ba, be), (ha, he), x0, y0 = self.claude_parts(d)
        mid.put(ba, x0, y0, o.Z['claude'], E=be)
        o.draw_desk(mid, monitor_on=1.0, content=self.screen(t), lamp_on=1.0, skip={'mug', 'paper', 'cactus'},
                    extra=self.desk_objects(t))
        mid.put(ha, x0, y0, o.Z['desk'], E=he)
        w = TL.wang_state(PF.on_twos(t))
        hx, hy = o.WANG_HEAD
        p = human.draw(human.WANG, face=w['face'], arms=w['arms'], phase=w['phase'], look=w['look'], glint=w['glint'],
                       desk_y=o.WANG_DESK_Y - (hy - human.AY), head_dy=w['hdy'], tilt=w['tilt'],
                       reach=(TL.PHOTO_EDGE[0] - (hx - human.AX), TL.PHOTO_EDGE[1] - (hy - human.AY), w['reach']))
        o.draw_wang_desk(mid, p, 1.0, t)
        return mid, d

    def render(self, t, cam, ui_fn=None, shot=None):
        mid, d = self.mid(t)
        uia = ui_fn(cam, d) if ui_fn else None
        ss = (13.0 + t) % 60
        st = self.state(t, shot)
        dust = self.dust.render_out(t, self.sun, self.o.windows, cam, gain=1.3 * st.get('dust_k', 1.0), px=1.3 * self.OW / 1920,
                                    color=(0.70, 0.82, 1.0), occluder=(mid.alpha(), mid.Z), glint_frac=0.05)
        return self.w.render(cam, st, mid=mid, fg=self.fg, ui=uia, frame=int(round(t * TL.FPS)), glow_out=dust,
                             bg_patches=[self.o.clock_patch(22, 47, int(ss))])


def mini_photo(pr):
    """Wang's desk photo for the wide shots: 14 x 12, a 1 px walnut frame around the real print, downsampled."""
    s = np.zeros((12, 14, 4), np.uint8); s[..., :3] = C('#4a3020')[:3]; s[..., 3] = 255
    s[0, :, :3] = C('#6b4a30')[:3]
    s[1:11, 1:13] = cv2.resize(pr, (12, 10), interpolation=cv2.INTER_AREA)
    s[1:11, 1:13, 3] = 255
    return s


# ====================================================================== close-ups (native big sprites, v2)
N2UI = 4.0 / 3.0            # native 480x270 -> UI canvas 640x360

class CloseUps:
    """C_CU / W_CU / C_MED: a blurred room plate + natively drawn Claude / Wang / props (no zoomed blocks)."""
    def __init__(self, office, pr):
        self.o = office
        self.cu = CUShot(office.w, office.OW, office.OH)
        self.pr = pr
        self.desk = CP.desk(480, 84)
        self.bob = CP.bobber_on_stand(4)
        self.kb = CP.keyboard(136, 28)
        self.lap = CP.laptop_back(156, 74)
        self._plates = {}
        self.rig_mon = LightRig((0.40, 0.46, 0.78), 0.30, [dict(x=140, y=0, r=200, col=(1.0, 0.7, 0.42), k=0.45)])
        warm, cool = (1.0, 0.70, 0.42), (0.42, 0.62, 1.0)
        self.rig_c = LightRig((0.40, 0.46, 0.78), 0.34, [
            dict(x=70, y=10, r=170, col=warm, k=1.25, power=1.3),          # Claude's desk lamp (upper left)
            dict(x=150, y=140, r=110, col=cool, k=0.55, power=1.4),        # its monitor (left, facing it)
            dict(x=470, y=120, r=160, col=(0.35, 0.45, 0.9), k=0.25)])     # faint blue room fill
        self.rig_w = LightRig((0.36, 0.42, 0.74), 0.30, [
            dict(x=205, y=200, r=95, col=(0.62, 0.80, 1.0), k=1.0, power=1.4),     # laptop, from below
            dict(x=-40, y=60, r=220, col=warm, k=0.35, power=1.4),                 # Claude's lamp, far left
            dict(x=470, y=40, r=120, col=(0.3, 0.9, 0.5), k=0.12)])               # exit sign, far right

    def plate(self, key, t, z, cx, cy, dof=1.5, drift=(0.0, 0.0)):
        if key not in self._plates:
            cam = Cam(z, cx, cy, OW=self.o.OW, OH=self.o.OH).clamp()
            self._plates[key] = self.cu.plate(cam, self.o.state(t), frame=0, dof=dof,
                                              bg_patches=[self.o.o.clock_patch(22, 47, 30)])
        P0 = self._plates[key]
        if drift == (0.0, 0.0): return P0
        M = np.float32([[1, 0, drift[0]], [0, 1, drift[1]]])
        return cv2.warpAffine(P0, M, (P0.shape[1], P0.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    @staticmethod
    def drift(t, t0, amp=1.2, seed=0):
        u = t - t0
        return (amp * math.sin(0.9 * u + seed) + 0.4 * amp * math.sin(2.3 * u + 1.7 * seed),
                0.6 * amp * math.sin(0.7 * u + 2.1 + seed))

    # ---------------------------------------------------------------- Claude close (C_CU)
    def c_cu(self, t, ui_fn):
        d = TL.claude_state(t)
        P = self.plate('c_cu', t, 2.4, 246, 104, 1.6, self.drift(t, TL.T_C_CU, 1.0, 0.3))
        doc = CP.form_screen(84, 60, u_fill=0.75, t=t, mode='doc')
        mon = CP.crt(176, 152, doc)
        S = 3
        spr = CUC.claude_bust(S=S, face=d['face'], look=d['look'], tilt=d['tilt'], ant=d['ant'], head_dy=d['hdy'] * 2,
                              led=d['led'], led_k=d['led_k'])
        hx, hy = 236, 62 - d['dy'] * S
        L = [Layer(mon, -96, 206 - 152, light=self.rig_mon),
             Layer(spr, hx - spr.ax, hy - spr.ay),
             Layer(self.desk, 0, 270 - 84 + 12)]
        uia = ui_fn(dict(head=(hx, hy), S=S))
        return self.cu.compose(P, L, self.o.state(t), frame=int(round(t * TL.FPS)), ui=uia, rig=self.rig_c)

    # ---------------------------------------------------------------- Claude medium (C_MED): monitor / keyboard / bobber
    def c_med(self, t, ui_fn):
        d = TL.claude_state(t)
        P = self.plate('c_med', t, 2.0, 262, 108, 1.4, self.drift(t, TL.T_C_MED, 0.9, 1.1))
        if t < TL.T_SUBMIT:
            u = clamp01((t - TL.T_C_MED + 0.4) / (TL.T_SUBMIT - TL.T_C_MED + 0.4))
            scr = CP.form_screen(84, 60, u_fill=u, ok=0.0, t=t)
        else:
            scr = CP.form_screen(84, 60, u_fill=1.0, ok=clamp01((t - TL.T_SUBMIT) / 0.25), t=t)
        mon = CP.crt(150, 130, scr)
        S = 2.4
        hx, hy = 262, 66 - d['dy'] * S
        hands = None
        x0 = hx - CUC.CL.AX * S; y0 = hy - CUC.CL.HY * S
        kbx, kby = 200, 196
        if d['arms'] == 'type':
            ph = d['phase'] % 4
            pts = [(kbx + 40 + (6 if ph in (1, 2) else 0), kby + 6 - (2 if ph == 1 else 0)), (kbx + 92 - (6 if ph in (2, 3) else 0), kby + 6 - (2 if ph == 3 else 0))]
        else:
            pts = [(kbx + 34, kby + 16), (kbx + 100, kby + 16)]
        hands = [((px - x0) / S, (py - y0) / S) for (px, py) in pts]
        flash = clamp01(1 - (t - TL.T_SUBMIT) / 0.6) if t >= TL.T_SUBMIT else 0.0
        spr = CUC.claude_bust(S=S, face=d['face'], look=d['look'], tilt=d['tilt'], ant=d['ant'], head_dy=d['hdy'] * 2,
                              led=d['led'], led_k=d['led_k'], hands=hands, screen_flash=0.0, spark_k=1.0 + 0.8 * flash)
        rig = self.rig_c
        if flash > 0:
            rig = LightRig(self.rig_c.amb_col, self.rig_c.amb, self.rig_c.points + [dict(x=70, y=115, r=150, col=(0.4, 1.0, 0.5), k=0.8 * flash, power=1.5)])
        L = [Layer(spr, x0, y0),
             Layer(self.desk, 0, 270 - 84 + 18),
             Layer(mon, 6, 214 - 130, light=self.rig_mon),
             Layer(self.kb, kbx, kby),
             Layer(self.bob, 372, 214 - self.bob.rgba.shape[0])]
        # hands go in front of the keyboard: redraw them on top
        if hands:
            hp = CUC.claude_bust(S=S, face=d['face'], hands=hands, badge=False)
        L.append(Layer(self._hands_only(hands, S, x0, y0), 0, 0))
        uia = ui_fn(dict(head=(hx, hy), S=S))
        return self.cu.compose(P, L, self.o.state(t), frame=int(round(t * TL.FPS)), ui=uia, rig=rig)

    def _hands_only(self, hands, S, x0, y0):
        from pixelkit.vec import Painter, circle
        p = Painter(480, 270)
        u, v = p.uv()
        for (hx, hy) in hands:
            p.part(circle(u, v, x0 + hx * S, y0 + hy * S, 3.6 * S), CUC.HANDR, bevel=1.8 * S, light=CUC.KEY, amb=0.3, ink=CUC.CL.HAND_OUT)
        return p.sprite()

    # ---------------------------------------------------------------- Wang close (W_CU)
    def w_cu(self, t, ui_fn, warmth=0.0):
        w = TL.wang_cu(t)
        P = self.plate('w_cu', t, 2.4, 380, 108, 1.6, self.drift(t, TL.T_W_CU, 1.0, 2.0))
        S = 3
        hx, hy = 196, 40
        x0 = hx - 35 * S; y0 = hy - 8 * S
        fr = CP.photo_frame(self.pr, 70, 54)
        fx, fy = 322, 196 - fr.rgba.shape[0]
        tgt = (fx + 4 - x0, fy + fr.rgba.shape[0] * 0.42 - y0)
        spr = CUC.wang_bust(S=S, face=w['face'], look=w['look'], tilt=w['tilt'], mouth=w['mouth'], nod=w['nod'],
                            head_dy=w['hdy'], shoulders_dy=w['sh'] * 1.0, light=(-0.1, 0.25, 0.96),
                            hand=('reach', w['reach'], tgt) if w['reach'] > 0.02 else None, pad_r=60 * S)
        L = [Layer(spr, x0, y0),
             Layer(self.desk, 0, 196 - 6),
             Layer(fr, fx, fy),
             Layer(self.lap, hx - self.lap.rgba.shape[1] // 2, 252 - self.lap.rgba.shape[0])]
        if w['reach'] > 0.02:      # the hand is in front of the frame: draw the arm layer again, clipped to the hand
            L.append(Layer(self._hand_only(spr, x0, y0, fx, fy, fr), 0, 0))
        uia = ui_fn(dict(head=(hx, hy), S=S))
        return self.cu.compose(P, L, self.o.state(t), frame=int(round(t * TL.FPS)), ui=uia, rig=self.rig_w)

    def _hand_only(self, spr, x0, y0, fx, fy, fr):
        a = np.zeros((270, 480, 4), np.uint8); E = np.zeros((270, 480), np.float32)
        h, w = spr.rgba.shape[:2]
        X0, Y0 = int(x0), int(y0)
        sub = spr.rgba[max(0, -Y0):min(h, 270 - Y0), max(0, -X0):min(w, 480 - X0)]
        a[max(0, Y0):max(0, Y0) + sub.shape[0], max(0, X0):max(0, X0) + sub.shape[1]] = sub
        keep = np.zeros((270, 480), bool)
        keep[fy - 4:fy + fr.rgba.shape[0] + 4, fx - 12:fx + fr.rgba.shape[1]] = True
        a[~keep] = 0
        return (a, E)


# ====================================================================== the film
class Egg:
    def __init__(self, OW=1920, OH=1080, only=None):
        self.OW, self.OH = OW, OH
        self.river = River(OW, OH)
        self.pr, self.prE = self.river.photo_print()
        self.office = NightOffice(OW, OH, mini_photo(self.pr))
        self.ins = INS.PhotoFrameInsert(self.pr, self.prE, OW=OW, OH=OH)
        E = edit.Edit()
        E.add('WIDE', 0.0, self.f_wide)
        E.add('C_CU', TL.T_C_CU, self.f_c_cu)
        E.add('W_CU', TL.T_W_CU, self.f_w_cu)
        E.add('C_MED', TL.T_C_MED, self.f_c_med)
        E.add('INS', TL.T_INS, self.f_ins)
        E.add('RIVER', TL.T_RIVER, self.f_river, 'dissolve', TL.D_IN)   # into the print, not a hard cut
        E.end(TL.DUR)
        self.edit = E

    # ---------------------------------------------------------------- UI
    def ui_common(self, cv, t):
        a = TL.hud_alpha(t)
        if a > 0:
            hh, d, de = TL.hud_clock(t)
            if t < TL.T_INS:
                k = ease_out3(ramp(t, TL.T_HUD_IN, TL.T_HUD_IN + 0.4))
                ui.hud_time(cv, 8 - int(round(60 * (1 - k))), 8, hh, day=d, day_en=de, alpha=a)
            else:
                ui.hud_time(cv, 8, 8, hh, day=d, day_en=de, alpha=a)
        ui.narration(cv, t, TL.BOXES)

    def office_ui(self, t, extra=None):
        def fn(cam, d):
            cv = ui.UICanvas()
            if extra: extra(cv, cam, d)
            if t < TL.T_C_CU or t >= TL.T_RIVER: self.ui_common(cv, t)
            else: ui.narration(cv, t, TL.BOXES)
            return cv.a
        return fn

    def mk_cam(self, z, cx, cy):
        return Cam(z, cx, cy, OW=self.OW, OH=self.OH).clamp()

    # ---------------------------------------------------------------- shots
    def f_wide(self, t):
        cam = self.mk_cam(TL.ZOOM_WIDE(t), *TL.CENTER_WIDE(t))
        return self.office.render(t, cam, self.office_ui(t))

    # close-ups = the SAME pixel world, zoomed (as in Acts I-V); pixel_soft background + close-up key / rim lights
    def f_c_cu(self, t):
        cam = self.mk_cam(*TL.cam_c_cu(t))
        def bubble(cv, cam, d):
            age = t - TL.T_OK
            if 0 <= age < 0.95:
                hx, hy = TL.HEAD
                ax, ay = cam.w2ui(hx + 15, hy + 3 - d['dy'], U4)
                ui.speech_bubble(cv, float(ax), float(ay), '好的！', age, 0.95, side=1, with_coin=True, t=t)
        return self.office.render(t, cam, self.office_ui(t, bubble), shot='c')

    def f_w_cu(self, t):
        return self.office.render(t, self.mk_cam(*TL.cam_w_cu(t)), self.office_ui(t), shot='w')

    def f_c_med(self, t):
        return self.office.render(t, self.mk_cam(*TL.cam_c_med(t)), self.office_ui(t), shot='m')

    def f_ins(self, t):
        z, cx, cy = TL.cam_ins(t)
        cam = Cam(z, cx, cy, OW=self.OW, OH=self.OH)
        cv = ui.UICanvas()
        if t >= TL.T_BADGE_IN:
            al = ease_out3(ramp(t, TL.T_BADGE_IN, TL.T_BADGE_IN + 0.3))
            fl = t - TL.T_FLIP
            al *= 1 - ease_io(ramp(t, TL.T_BADGE_OUT, TL.T_PUSH1 - 0.05))   # leaves before the dissolve
            if fl < 0: ui.status_badge(cv, 470, 10, 'online', '王工 · 在线', alpha=al)
            else:
                flip = abs(math.cos(math.pi * clamp01(fl / 0.24)))
                st = 'online' if fl < 0.12 else 'off'
                ui.status_badge(cv, 470, 10, st, '王工 · 在线' if st == 'online' else '王工 · 休假中', alpha=al, flip=max(0.05, flip),
                                pulse=max(0.0, 1 - (fl - 0.24) / 0.5) if fl > 0.24 else 0.0)
        u = (t - TL.T_GLINT0) / (TL.T_GLINT1 - TL.T_GLINT0)
        warm = ease_io(ramp(t, TL.T_WARM0, TL.T_WARM1))
        return self.ins.frame(cam, frame=int(round(t * TL.FPS)), glint=u if 0 <= u <= 1 else None, warmth=warm,
                              cool=1.0 - 0.35 * warm, ui=cv.a, t=t)

    def f_river(self, t):
        cam = Cam(*TL.cam_river(t), W=480, H=270)
        cv = ui.UICanvas(); self.ui_common(cv, t)
        fk = 1.0 - ease_io(ramp(t, TL.T_RIVER + TL.FILM_HOLD, TL.T_RIVER + TL.FILM_HOLD + TL.FILM_FADE))
        age = ease_io(ramp(t, TL.T_AGE0, TL.T_AGE1))
        return self.river.frame(t, cam, ui_rgba=cv.a, film_k=fk, frame=int(round(t * TL.FPS)), age=age)

    def frame(self, t):
        img = self.edit.frame(t)
        f = TL.fade(t)
        return img * f if f < 1 else img

def make(**kw): return Egg(**kw)
