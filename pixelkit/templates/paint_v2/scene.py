"""油画转场小样 v2 renderer: make() -> object with .frame(t) -> float RGB (1080, 1920, 3).  Timing: timeline.py"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/paint_v2'))
import numpy as np, cv2
from pixelkit.core import Canvas, C
from pixelkit.anim import ramp, ease_io, ease_out3
from pixelkit.camera import Cam
from pixelkit.scene import GLayer, ui_over
from pixelkit.outdoor import OutdoorScene, outdoor_state, lerp_otod
from pixelkit.sets import river_pier as RP
from pixelkit.characters import backs
from pixelkit import painterly as PT, ui
import timeline as TL

CL_X, CL_Y = 220, RP.CLAUDE_SEAT[1]
OM_X, OM_Y = RP.OLD_SEAT
ROD_TIP = (360.0, 134.0)
BG_LAYERS = PT.Painter.LAYERS[:2] + (dict(r=4.0, length=(2.5, 4.5), density=0.65, thr=0.022, curve=0.8),
                                     dict(r=2.3, length=(2.2, 4.0), density=0.7, thr=0.03, curve=0.8))
FIG_LAYERS = (dict(r=4.5, length=(2.0, 3.5), density=1.0, thr=None, curve=0.5, focus_only=True),
              dict(r=3.0, length=(1.8, 3.0), density=1.0, thr=None, curve=0.5, focus_only=True))

def bobber_sprite():
    a = np.zeros((7, 3, 4), np.uint8)
    for y, col in ((0, '#ffd2b4'), (1, '#ff6a4a'), (2, '#e04a3a'), (3, '#fff4ea'), (4, '#3a2a3a')):
        a[y, :] = C(col)
    a[0, 0] = a[0, 2] = 0
    a[5:, :] = 0
    E = np.zeros((7, 3), np.float32); E[0:3] = 0.55; E[3] = 0.4
    return a, E


class PaintV2:
    def __init__(self, OW=1920, OH=1080, only=None, mode='full', toggle_ui=True, t_click=None, fade_out=True):
        """mode: 'full' | 'pixel' | 'soft' | 'paint' (comparison stills).
        Embedding in ACT IV: toggle_ui=False (the switch was already flipped in the close-up), t_click = when Claude's
        logo dims (default TL.T_CLICK; use a large negative value = already dim), fade_out=False (the edit dissolves)."""
        self.OW, self.OH, self.mode = OW, OH, mode
        self.toggle_ui, self.fade_out = toggle_ui, fade_out
        self.t_click = TL.T_CLICK if t_click is None else t_click
        self.rv0, self.rv1 = RP.RiverPier(0.0), RP.RiverPier(1.0)
        self.sc0, self.sc1 = OutdoorScene(self.rv0.bg, OW=OW, OH=OH), OutdoorScene(self.rv1.bg, OW=OW, OH=OH)
        self.om = backs.old_fisher_back()
        self.cam = Cam(1.0, W=480, H=270, OW=OW, OH=OH)
        self.bob, self.bobE = bobber_sprite()
        f = OW // 480; self.f = f
        ref = self.source(3.0)
        mid = GLayer(480, 270); self.figures(mid, 3.0)
        fa = np.repeat(np.repeat((mid.alpha() > 0.5).astype(np.float32), f, 0), f, 1)
        dm = np.repeat(np.repeat((self.rv0.detail_mask | self.rv1.detail_mask).astype(np.float32), f, 0), f, 1)
        self.fig_m = np.maximum(cv2.GaussianBlur(fa, (0, 0), 1.2), 0.8 * cv2.GaussianBlur(dm, (0, 0), 2.0))   # crisp-ish layer: figures + small props
        foc = cv2.GaussianBlur(cv2.dilate(fa, np.ones((9, 9), np.uint8)), (0, 0), 6.0)
        yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
        sx, sy = self.cam.w2o(RP.SUN_X, self.rv0.sun_y)
        foc = np.maximum(foc, np.exp(-((xx - sx) ** 2 + (yy - sy) ** 2) / (2 * (12.0 * f) ** 2)))
        pm = np.repeat(np.repeat(self.rv0.pier_mask.astype(np.float32), f, 0), f, 1)
        foc = np.maximum(foc, 0.7 * cv2.GaussianBlur(pm, (0, 0), 4.0 * f))           # keep the pier's planks / edges
        hy = self.cam.w2o(0, RP.HORIZON)[1]; by = self.cam.w2o(0, RP.PIER_END)[1]
        band = lambda a_, b_, c_: cv2.GaussianBlur(np.where(yy < hy, a_, np.where(yy < by, b_, c_)).astype(np.float32), (0, 0), 3.0 * f)
        hz = np.exp(-((yy - hy - 2 * f) / (16.0 * f)) ** 2)                               # town / hills / reflections on the horizon
        foc = np.maximum(foc, 0.55 * hz)
        self.P = PT.Painter(ref, focus=foc, length_map=band(2.1, 1.1, 0.9), width_map=band(0.6, 0.5, 0.7), focus_mix=0.25, layers=BG_LAYERS,
                            jitter_map=band(0.38, 0.8, 0.9), break_map=band(0.045, 0.07, 0.085))
        self.Pf = PT.Painter(ref, focus=cv2.dilate(np.maximum(fa, dm), np.ones((5, 5), np.uint8)), layers=FIG_LAYERS, focus_mix=0.0, seed=11, jitter=0.35)

    # ------------------------------------------------------------------ world
    def figures(self, mid, t):
        om = self.om
        mid.put(om.rgba, int(OM_X - om.ax), int(OM_Y - om.ay), 0, E=om.E)
        glow = 1.0 - 0.45 * ease_io(ramp(t, self.t_click, self.t_click + 0.4))
        cl = backs.claude_back(glow=glow)
        mid.put(cl.rgba, int(CL_X - cl.ax), int(CL_Y - cl.ay), 0, E=cl.E)

    def bobber_xy(self, t):
        bx, by = TL.BOBBER
        d = 0.6 * math.sin(2 * math.pi * t / 2.3)
        dip = t - TL.T_DIP
        if 0 <= dip < 0.45: d += 2.0 * math.sin(math.pi * dip / 0.45)
        return int(bx - 1), int(round(by - 5 + d))

    def rod_and_line(self, t, bobber=True):
        cv = Canvas(480, 270); E = np.zeros((270, 480), np.float32)
        hx, hy = OM_X - self.om.ax + self.om.hand[0], OM_Y - self.om.ay + self.om.hand[1]
        tx, ty = ROD_TIP
        sway = 0.5 * math.sin(2 * math.pi * t / 3.1)
        n = 80
        for i in range(n + 1):
            u = i / n
            x = hx + (tx - hx) * u; y = hy + (ty - hy) * u + 7 * u * (1 - u) + sway * u * u
            cv.px(int(round(x)), int(round(y)), C('#2a1c22') if u < 0.75 else C('#f0b88a'))
            if u < 0.3: cv.px(int(round(x)), int(round(y)) + 1, C('#2a1c22'))       # thicker butt
            if u >= 0.75: E[int(round(y)), int(round(x))] = 0.6
        bx, by = self.bobber_xy(t)
        x0, y0 = tx, ty + sway
        for i in range(61):
            u = i / 60
            x = x0 + (bx + 1 - x0) * u; y = y0 + (by - y0) * u + 3 * u * (1 - u)
            if i % 2 == 0:
                cv.px(int(round(x)), int(round(y)), C('#f8e0c8')); E[int(round(y)), int(round(x))] = 0.5
        if bobber:
            h, w = self.bob.shape[:2]
            m = self.bob[..., 3] > 127
            cv.a[by:by + h, bx:bx + w][m] = self.bob[m]; E[by:by + h, bx:bx + w][m] = self.bobE[m]
        for (x, y, a) in self.rv0.ripple_rings(t, TL.T_DIP + 0.1, TL.BOBBER[0], TL.BOBBER[1], n=4, speed=22.0, gap=0.35, life=2.4):
            if a > 0.15: cv.px(x, y, C('#fff0d0')); E[y, x] = 0.6 * a + 0.3
        RP.draw_birds(cv, self.rv0.birds(t), C('#3a2a4a'))
        return cv, E

    def source(self, t, bobber=True):
        k = TL.dusk(t)
        mid = GLayer(480, 270)
        self.figures(mid, t)
        cv, E = self.rod_and_line(t, bobber)
        mid.put(cv.a, 0, 0, 0, E=E)
        out = None
        lx, ly = RP.LANTERN
        for w, rv, sc in ((1 - k, self.rv0, self.sc0), (k, self.rv1, self.sc1)):
            if w <= 1e-3: continue
            st = outdoor_state('sunset', **RP.RP_STATE)
            st['points'] = [dict(x=lx, y=ly - 5, r=22.0, col=(1.0, 0.62, 0.30), k=0.10 + 0.35 * k, power=1.4)]
            g = rv.glitter(t)
            img = sc.render(self.cam, st, mid, [], frame=int(round(t * TL.FPS)), bg_patches=[(g[0], g[2], g[3], g[1])],
                            front_i=rv.front_index(t))
            out = img * w if out is None else out + img * w
        return out

    # ------------------------------------------------------------------ UI
    def ui(self, t):
        cv = ui.UICanvas()
        if self.toggle_ui and TL.T_UI_IN <= t < TL.T_UI_OUT + 0.3:
            k = ease_out3(ramp(t, TL.T_UI_IN, TL.T_UI_IN + 0.25))
            alpha = 1.0 - ramp(t, TL.T_UI_OUT, TL.T_UI_OUT + 0.3)
            press = math.sin(math.pi * ramp(t, TL.T_CLICK - 0.06, TL.T_CLICK + 0.12))
            X, Y = self.cam.w2ui(CL_X, CL_Y - 62, 4)
            ui.toggle(cv, X, Y - 10, TL.switch_k(t), '消息提醒', alpha=alpha, k=k, press=press)
        if TL.T_NAR - 0.3 <= t < TL.T_NAR_CLOSE + 0.6:
            ui.narration(cv, t, TL.BOXES)
        return cv.a

    # ------------------------------------------------------------------ frame
    def bobber_mask(self, t):
        bx, by = self.bobber_xy(t); f = self.f
        m = np.zeros((self.OH, self.OW), np.float32)
        a = (self.bob[..., 3] > 127).astype(np.float32); h, w = a.shape
        m[by * f:(by + h) * f, bx * f:(bx + w) * f] = np.repeat(np.repeat(a, f, 0), f, 1)
        return m

    def painted(self, src, t):
        bg = self.P.paint(src, t, streaks=0.02)
        fg = self.Pf.paint(src, t, streaks=0.0, impasto=0.03, weave=0.02)
        fg = 0.5 * fg + 0.5 * PT.paint_grade(cv2.GaussianBlur(src, (0, 0), 1.6))      # painted, but clean shapes
        fm = self.fig_m[..., None]
        return self.rod_paint(bg * (1 - fm) + fg * fm, t)

    def rod_paint(self, img, t):
        """the rod + line as deliberate thin brush strokes over the painting (a 1-px pixel line would smear away)."""
        f = self.f; img = np.ascontiguousarray(img)
        hx, hy = OM_X - self.om.ax + self.om.hand[0], OM_Y - self.om.ay + self.om.hand[1]
        tx, ty = ROD_TIP; sway = 0.5 * math.sin(2 * math.pi * t / 3.1)
        k = TL.dusk(t)
        pts = []
        for i in range(41):
            u = i / 40
            pts.append(((hx + (tx - hx) * u + 0.5) * f, (hy + (ty - hy) * u + 7 * u * (1 - u) + sway * u * u + 0.5) * f))
        dark = np.array([0.24, 0.15, 0.17], np.float32); lit = np.array([1.0, 0.74, 0.52], np.float32) * (1 - 0.3 * k)
        S = 4
        for i in range(40):
            u = i / 40
            w = 4.0 - 2.6 * u
            col = dark if u < 0.6 else dark + (lit - dark) * min(1.0, (u - 0.6) / 0.3)
            p0 = (int(pts[i][0] * S), int(pts[i][1] * S)); p1 = (int(pts[i + 1][0] * S), int(pts[i + 1][1] * S))
            cv2.line(img, p0, p1, tuple(float(c) for c in col), max(1, int(round(w))), cv2.LINE_AA, shift=2)
        # line: rod tip -> bobber, thin and light, partly lost against the bright water
        bx, by = self.bobber_xy(t)
        x0, y0 = tx + 0.5, ty + sway + 0.5
        lay = np.zeros_like(img[..., 0])
        q = [(((x0 + (bx + 1.5 - x0) * u) * f) * S, ((y0 + (by + 0.5 - y0) * u + 3 * u * (1 - u)) * f) * S) for u in np.linspace(0, 1, 30)]
        cv2.polylines(lay, [np.int32(q)], False, 1.0, 1, cv2.LINE_AA, shift=2)
        lay = cv2.GaussianBlur(lay, (0, 0), 0.6) * 1.3
        img = img + (np.array([0.97, 0.88, 0.78], np.float32) - img) * np.clip(0.4 * lay, 0, 0.5)[..., None]
        return img

    def frame(self, t):
        src = self.source(t)
        mode = self.mode
        if mode == 'pixel' or (mode == 'full' and t < TL.T_RIP):
            out = src
        else:
            if mode == 'soft':
                out = PT.soften(src)
            elif mode == 'paint' or t >= TL.T_FULL:
                out = self.painted(src, t)
            else:
                paint = self.painted(src, t)
                r = TL.ripple_r(t)
                ms = PT.ripple_mask(self.cam, r, TL.BOBBER, OW=self.OW, OH=self.OH)[..., None]
                mp = PT.ripple_mask(self.cam, r - TL.SOFT_BAND, TL.BOBBER, OW=self.OW, OH=self.OH)[..., None]
                soft = PT.soften(src)
                out = src * (1 - ms) + soft * (ms - mp) + paint * mp
                ring = PT.ring_glow(self.cam, r, TL.BOBBER, width=3.5, OW=self.OW, OH=self.OH)
                out = out + ring[..., None] * np.array([1.0, 0.80, 0.55], np.float32) * 0.22
            bm = self.bobber_mask(t)[..., None]
            halo = cv2.GaussianBlur(bm[..., 0], (0, 0), 14.0)[..., None]
            out = out + halo * np.array([1.0, 0.55, 0.35], np.float32) * 0.9 * min(1.0, ramp(t, TL.T_RIP, TL.T_RIP + 0.6))
            out = out * (1 - bm) + src * bm
            if mode == 'full' and t >= TL.T_STAR:
                sx, sy = self.cam.w2o(118, 30)
                yy, xx = np.ogrid[0:self.OH, 0:self.OW]
                st_ = np.exp(-((xx - sx) ** 2 + (yy - sy) ** 2) / (2 * 5.0 ** 2)).astype(np.float32)
                out = out + st_[..., None] * np.array([1.0, 0.95, 0.85], np.float32) * 0.8 * ramp(t, TL.T_STAR, TL.T_STAR + 1.5)
        if mode == 'full' and t >= TL.T_PUSH0:
            z = TL.push(t)
            cx, cy = self.cam.w2o(262, 196)
            bm = self.bobber_mask(t)
            sharp = out * bm[..., None]
            out = PT.zoom_view(out * (1 - bm[..., None]) + cv2.GaussianBlur(out, (0, 0), 2) * bm[..., None], z, cx, cy)
            Mz = PT.zoom_matrix(z, cx, cy)
            bz = cv2.warpAffine(bm, Mz, (self.OW, self.OH), flags=cv2.INTER_NEAREST)[..., None]
            sz = cv2.warpAffine(sharp, Mz, (self.OW, self.OH), flags=cv2.INTER_NEAREST)
            out = out * (1 - bz) + sz
        if mode == 'full' and self.fade_out:
            out = out * (1 - ramp(t, TL.T_FADE0, TL.DUR - 0.05))
        u = self.ui(t) if mode == 'full' else None
        if u is not None and u[..., 3].any():
            out = ui_over(out, u, scale=self.OW // 480)
        return out

def make(**kw): return PaintV2(**kw)
