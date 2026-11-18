"""BRIDGE III -> IV · 走向河边 - the Act III street (pixelkit.sets.street) as afternoon turns to gold."""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, importlib.util
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/bridge34'))
import numpy as np
from pixelkit.camera import Cam
from pixelkit.scene import GLayer
from pixelkit.outdoor import OutdoorScene, outdoor_state, OTOD
from pixelkit.characters import walker as WK
from pixelkit import ui
import timeline as TL

def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m; sp.loader.exec_module(m); return m

_mine = sys.modules['timeline']
A3TL = _load('a3_timeline', (_PROJ + '/act3/timeline.py'))
sys.modules['timeline'] = A3TL
A3 = _load('a3_scene', (_PROJ + '/act3/scene.py'))
sys.modules['timeline'] = _mine


def lerp(a, b, k):
    if isinstance(a, tuple): return tuple(x + (y - x) * k for x, y in zip(a, b))
    return a + (b - a) * k


class Bridge34:
    def __init__(self, OW=1920, OH=1080, **kw):
        self.ss = A3.StreetShot(OW, OH)
        self.st, self.sc = self.ss.st, self.ss.sc
        self.OW, self.OH = OW, OH
        self.extras = [WK.Walker(li, x0, v, foot, prop, 0.0, seed=i + 3) for i, (li, x0, v, foot, prop) in enumerate(TL.EXTRAS)]

    def state(self, t):
        g, gl = TL.gold(t), TL.glare(t)
        st = outdoor_state('morning', **A3.LOOK)
        st['grade'].update(sat=1.22, contrast=1.20, black=0.045)
        a, b = OTOD['noon'], OTOD['sunset']
        st['sun'] = lerp(a['sun'], b['sun'], g); st['amb'] = lerp(a['amb'], b['amb'], g); st['haze'] = lerp(a['haze'], b['haze'], g)
        st['sun_k'] = A3.LOOK['sun_k'] * (1.0 + 0.25 * g)
        st['amb_k'] = A3.LOOK['amb_k'] * (1.0 - 0.15 * g)
        st['haze_k'] = A3.LOOK['haze_k'] + 0.20 * g + 0.25 * gl
        st['shadow_k'] = 0.62 + 0.25 * g
        st['shadow_sx'] = 0.55 - 3.0 * g                     # the sun swings low ahead (right): shadows stretch out behind
        st['shadow_sy'] = -0.20 - 0.08 * g
        st['rim'] = 0.55 + 0.6 * g
        A3.warm_grade(st['grade'], 0.9 * g)
        st['grade']['exposure'] = st['grade'].get('exposure', 1.0) * (1.0 + 0.30 * gl)
        return st

    def ui(self, t):
        cv = ui.UICanvas()
        a = TL.hud_alpha(t)                   # v1.1: only the badge fades - the clock carries across the cut (Act IV has it)
        hh = TL.clock(t)
        fl = 0.6 * (1 - ramp01((t - TL.T_ROLL1) / 0.35)) if t >= TL.T_ROLL1 else 0.0
        ui.hud_time(cv, 8, 8, hh, day='周六', day_en='SAT', alpha=1.0, flash=fl)
        if a > 0: ui.status_badge(cv, 472, 8, 'off', alpha=a)
        return cv.a

    def frame(self, t):
        z, cx, cy = TL.cam(t)
        cam = Cam(z, cx, cy, W=480, H=270, OW=self.OW, OH=self.OH)
        hw, hh = 240 / z, 135 / z
        cam.cx = min(max(cam.cx, hw), self.st.W - hw); cam.cy = min(max(cam.cy, hh), 270 - hh)
        st = self.state(t)
        mid = GLayer(self.st.W, self.st.H)
        casters = []
        for wk in self.extras:
            for (rgba, X, Y, E, al, foot) in wk.sprites(t):
                if X > self.st.W or X + rgba.shape[1] < 0: continue
                mid.put(rgba, X, Y, 0, E=E)
                if foot is not None: casters.append((al, X, Y, foot, 0.55))
        for (rgba, X, Y) in self.ss.leaves.sprites(t): mid.put(rgba, X, Y, 0)
        d = TL.claude(t)
        p, X, Y, al = A3.claude_sprite(d)
        mid.put(p.body.rgba, X, Y, 0, E=p.body.E); mid.put(p.hands.rgba, X, Y, 0, E=p.hands.E)
        casters.append((al, X, Y, d['foot'], 1.0))
        leaf, lx, ly = self.st.door_sprite(0.0)
        motes = self.ss.motes.render_out(t, cam, self.ss.mote_vis, gain=0.45 + 0.5 * TL.gold(t))
        img = self.sc.render(cam, st, mid, casters, ui=self.ui(t), frame=int(round(t * TL.FPS)), bg_patches=[(leaf.rgba, lx, ly)],
                             front_i=self.st.front_index(t), add_out=motes)
        gl = TL.glare(t)
        if gl > 0:                                            # the low sun over the river, off frame right
            H, W = img.shape[:2]
            xs = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
            ys = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
            m = np.clip((xs - 0.35) / 0.65, 0, 1) ** 2.2 * (0.75 + 0.25 * (1 - np.abs(ys - 0.55) * 1.6))
            img = img + m * gl * 0.55 * np.float32([1.0, 0.72, 0.42])
        f = TL.fade(t)
        return img * f if f < 1 else img


def ramp01(u): return 0.0 if u <= 0 else (1.0 if u >= 1 else u)

def make(**kw): return Bridge34(**kw)
