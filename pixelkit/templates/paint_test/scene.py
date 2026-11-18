"""油画转场小样 renderer: make() -> object with .frame(t) -> float RGB (1080, 1920, 3).  Timing: timeline.py"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/paint_test'))
import numpy as np, cv2
from pixelkit.core import Canvas, C
from pixelkit.anim import ramp, ease_io, ease_out3
from pixelkit.camera import Cam
from pixelkit.scene import GLayer, ui_over
from pixelkit.outdoor import OutdoorScene, outdoor_state, lerp_otod
from pixelkit.sets.river import River, RIVER_STATE, SEAT_Y, HORIZON
from pixelkit.characters import backs, person as P
from pixelkit import painterly as PT, ui
import timeline as TL

OLD = P.Look(hair='short', hair_col='#c8c2bc', skin='#e8b48e', top='cardigan', top_col='#7e6e52', bottom_col='#4a4438')
OM_X, CL_X = 196, 262
ROD_TIP = (297.0, 150.0)

def bobber_sprite():
    a = np.zeros((7, 3, 4), np.uint8)
    for y, col in ((0, '#ffd2b4'), (1, '#ff6a4a'), (2, '#e04a3a'), (3, '#fff4ea'), (4, '#3a2a3a')):
        a[y, :] = C(col)
    a[0, 0] = a[0, 2] = 0
    a[5:, :] = 0
    E = np.zeros((7, 3), np.float32); E[0:3] = 0.55; E[3] = 0.4
    return a, E


class PaintTest:
    def __init__(self, OW=1920, OH=1080, only=None, mode='full'):
        """mode: 'full' (the sample) | 'pixel' | 'soft' | 'paint' (for the A/B comparison stills)."""
        self.OW, self.OH, self.mode = OW, OH, mode
        self.rv0, self.rv1 = River(0.0), River(1.0)
        self.sc0, self.sc1 = OutdoorScene(self.rv0.bg, OW=OW, OH=OH), OutdoorScene(self.rv1.bg, OW=OW, OH=OH)
        self.om = backs.person_back(OLD, hat='straw')
        self.cam = Cam(1.0, W=480, H=270, OW=OW, OH=OH)
        self.bob, self.bobE = bobber_sprite()
        ref = self.source(3.0, bobber=True)
        # focus = the two figures (+ a margin) and the sun: smaller strokes, silhouettes stay readable
        mid = GLayer(480, 270); self.figures(mid, 3.0)
        f = OW // 480
        a = np.repeat(np.repeat(mid.alpha().astype(np.float32), f, 0), f, 1)
        foc = cv2.GaussianBlur(cv2.dilate(a, np.ones((9, 9), np.uint8)), (0, 0), 6.0)
        yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
        sx, sy = self.cam.w2o(332, self.rv0.sun_y)
        foc = np.maximum(foc, np.exp(-((xx - sx) ** 2 + (yy - sy) ** 2) / (2 * (10.0 * f) ** 2)))
        hy = self.cam.w2o(0, HORIZON)[1]; by = self.cam.w2o(0, 214)[1]
        band = lambda a_, b_, c_: cv2.GaussianBlur(np.where(yy < hy, a_, np.where(yy < by, b_, c_)).astype(np.float32), (0, 0), 3.0 * f)
        self.P = PT.Painter(ref, focus=foc, length_map=band(1.5, 1.0, 0.9), width_map=band(0.85, 0.5, 0.8))

    # ------------------------------------------------------------------ world
    def figures(self, mid, t):
        om = self.om
        mid.put(om.rgba, int(OM_X - om.ax), int(SEAT_Y - om.ay), 0, E=om.E)
        glow = 1.0 - 0.45 * ease_io(ramp(t, TL.T_CLICK, TL.T_CLICK + 0.4))
        cl = backs.claude_back(glow=glow)
        mid.put(cl.rgba, int(CL_X - cl.ax), int(SEAT_Y - cl.ay), 0, E=cl.E)
        return om

    def bobber_xy(self, t):
        bx, by = TL.BOBBER
        d = 0.6 * math.sin(2 * math.pi * t / 2.3)
        dip = t - TL.T_DIP
        if 0 <= dip < 0.45: d += 2.0 * math.sin(math.pi * dip / 0.45)
        return int(bx - 1), int(round(by - 5 + d))

    def rod_and_line(self, t, bobber=True):
        cv = Canvas(480, 270); E = np.zeros((270, 480), np.float32)
        hx, hy = OM_X - self.om.ax + self.om.hand[0], SEAT_Y - self.om.ay + self.om.hand[1]
        tx, ty = ROD_TIP
        sway = 0.5 * math.sin(2 * math.pi * t / 3.1)
        n = 60
        for i in range(n + 1):
            u = i / n
            x = hx + (tx - hx) * u; y = hy + (ty - hy) * u + 6 * u * (1 - u) + sway * u * u
            cv.px(int(round(x)), int(round(y)), C('#2a1c22') if u < 0.8 else C('#e8b088'))
            if u >= 0.8: E[int(round(y)), int(round(x))] = 0.5
        bx, by = self.bobber_xy(t)
        x0, y0 = tx, ty + sway
        for i in range(41):
            u = i / 40
            x = x0 + (bx + 1 - x0) * u; y = y0 + (by - y0) * u + 3 * u * (1 - u)
            if i % 2 == 0:
                cv.px(int(round(x)), int(round(y)), C('#f4d8c0')); E[int(round(y)), int(round(x))] = 0.35
        if bobber:
            h, w = self.bob.shape[:2]
            m = self.bob[..., 3] > 127
            cv.a[by:by + h, bx:bx + w][m] = self.bob[m]; E[by:by + h, bx:bx + w][m] = self.bobE[m]
        # pixel ripple rings
        for (x, y, a) in self.rv0.ripple_rings(t, TL.T_DIP + 0.1, TL.BOBBER[0], TL.BOBBER[1], n=4, speed=22.0, gap=0.35, life=2.4):
            if a > 0.15 and 0 <= x < 480 and 0 <= y < 270:
                cv.px(x, y, C('#ffe8c8')); E[y, x] = 0.6 * a + 0.3
        return cv, E

    def source(self, t, bobber=True):
        """the pixel-art frame at t (reference framing, dusk blend), no UI."""
        k = TL.dusk(t)
        mid = GLayer(480, 270)
        self.figures(mid, t)
        cv, E = self.rod_and_line(t, bobber)
        mid.put(cv.a, 0, 0, 0, E=E)
        out = None
        for w, rv, sc, tod_k in ((1 - k, self.rv0, self.sc0, 0.0), (k, self.rv1, self.sc1, 1.0)):
            if w <= 1e-3: continue
            st = outdoor_state(lerp_otod('sunset', 'dusk', 0.45 * tod_k * k / max(k, 1e-6) if tod_k else 0.0), **RIVER_STATE)
            g = rv.glitter(t)
            img = sc.render(self.cam, st, mid, [], frame=int(round(t * TL.FPS)), bg_patches=[(g[0], g[2], g[3], g[1])],
                            front_i=rv.front_index(t))
            out = img * w if out is None else out + img * w
        return out

    # ------------------------------------------------------------------ UI
    def ui(self, t):
        cv = ui.UICanvas()
        if TL.T_UI_IN <= t < TL.T_UI_OUT + 0.3:
            k = ease_out3(ramp(t, TL.T_UI_IN, TL.T_UI_IN + 0.25))
            alpha = 1.0 - ramp(t, TL.T_UI_OUT, TL.T_UI_OUT + 0.3)
            press = math.sin(math.pi * ramp(t, TL.T_CLICK - 0.06, TL.T_CLICK + 0.12))
            X, Y = self.cam.w2ui(CL_X, SEAT_Y - 62, 4)
            ui.toggle(cv, X, Y - 10, TL.switch_k(t), '消息提醒', alpha=alpha, k=k, press=press)
        if t >= TL.T_NAR - 0.3:
            ui.narration(cv, t, TL.BOXES)
        return cv.a

    # ------------------------------------------------------------------ frame
    def bobber_patch(self, src, t):
        """mask (OH, OW) of the bobber's crisp pixels in the reference framing."""
        bx, by = self.bobber_xy(t)
        f = self.OW // 480
        m = np.zeros((self.OH, self.OW), np.float32)
        a = (self.bob[..., 3] > 127).astype(np.float32)
        h, w = a.shape
        m[by * f:(by + h) * f, bx * f:(bx + w) * f] = np.repeat(np.repeat(a, f, 0), f, 1)
        return m

    def frame(self, t):
        src = self.source(t)
        mode = self.mode
        if mode == 'pixel' or (mode == 'full' and t < TL.T_RIP):
            out = src
        else:
            paint = self.P.paint(src, t)
            if mode == 'soft':
                out = PT.soften(src)
            elif mode == 'paint' or t >= TL.T_FULL:
                out = paint
            else:
                r = TL.ripple_r(t)
                ms = PT.ripple_mask(self.cam, r, TL.BOBBER, OW=self.OW, OH=self.OH)[..., None]
                mp = PT.ripple_mask(self.cam, r - TL.SOFT_BAND, TL.BOBBER, OW=self.OW, OH=self.OH)[..., None]
                soft = PT.soften(src)
                out = src * (1 - ms) + soft * (ms - mp) + paint * mp
                ring = PT.ring_glow(self.cam, r, TL.BOBBER, width=3.5, OW=self.OW, OH=self.OH)
                out = out + ring[..., None] * np.array([1.0, 0.80, 0.55], np.float32) * 0.22
            # the bobber stays a crisp pixel object (+ a faint warm halo once it sits in the painting)
            bm = self.bobber_patch(src, t)[..., None]
            halo = cv2.GaussianBlur(bm[..., 0], (0, 0), 14.0)[..., None]
            out = out + halo * np.array([1.0, 0.55, 0.35], np.float32) * 0.9 * min(1.0, ramp(t, TL.T_RIP, TL.T_RIP + 0.6))
            out = out * (1 - bm) + src * bm
            if mode == 'full' and t >= TL.T_STAR:            # first star: a single soft dab
                sx, sy = self.cam.w2o(118, 34)
                yy, xx = np.ogrid[0:self.OH, 0:self.OW]
                st_ = np.exp(-((xx - sx) ** 2 + (yy - sy) ** 2) / (2 * 5.0 ** 2)).astype(np.float32)
                out = out + st_[..., None] * np.array([1.0, 0.95, 0.85], np.float32) * 0.8 * ramp(t, TL.T_STAR, TL.T_STAR + 1.2)
        if mode == 'full' and t >= TL.T_PUSH0:
            z = TL.push(t)
            cx, cy = self.cam.w2o(232, 196)
            bm = self.bobber_patch(src, t)
            sharp = out * bm[..., None]
            out = PT.zoom_view(out * (1 - bm[..., None]) + cv2.GaussianBlur(out, (0, 0), 2) * bm[..., None], z, cx, cy)
            Mz = PT.zoom_matrix(z, cx, cy)
            bz = cv2.warpAffine(bm, Mz, (self.OW, self.OH), flags=cv2.INTER_NEAREST)[..., None]
            sz = cv2.warpAffine(sharp, Mz, (self.OW, self.OH), flags=cv2.INTER_NEAREST)
            out = out * (1 - bz) + sz
        if mode == 'full':
            out = out * (1 - ramp(t, TL.T_FADE0, TL.DUR - 0.05))
        u = self.ui(t) if mode == 'full' else None
        if u is not None and u[..., 3].any():
            out = ui_over(out, u, scale=self.OW // 480)
        return out

def make(**kw): return PaintTest(**kw)
