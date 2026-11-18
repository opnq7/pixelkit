"""pixelkit.cushot - close-up compositor: a blurred room plate + natively drawn big sprites, lit and graded the
same way as World, so a close-up keeps the 4-screen-px pixel grid of the wide shots (no 3x zoom blocks).

    cu = CUShot(world)                                   # the room's World (for the plate, finisher, grade path)
    plate = cu.plate(cam, st, frame=i, bg_patches=..., dof=1.4)          # room background only, native, linear
    out = cu.compose(plate, [
            Layer(spr_desk, 0, 180),                                      # crisp native layers, back -> front
            Layer(spr_claude, 120, 20, light=LightRig(...)),
            Layer(spr_fg, -20, 120, soft=2.5, offset=(dx, dy)),           # soft = blurred foreground (output res)
         ], st, frame=i, ui=ui_rgba)

LightRig(amb_col, amb, points=[dict(x, y, r, col, k, power)]) in NATIVE screen coords (480 x 270) - the same
falloff as light.Rig.point:  1 / (1 + (d / r)^2)^power.  Emissive pixels (Sprite.E) ignore the light and feed bloom.
"""
import numpy as np, cv2
from . import post

NW, NH = 480, 270


class LightRig:
    def __init__(self, amb_col=(0.55, 0.6, 0.85), amb=0.5, points=(), eg=1.15):
        self.amb_col, self.amb, self.points, self.eg = amb_col, amb, list(points), eg
        self._cache = {}

    def map(self):
        key = 'full'
        if key not in self._cache:
            yy, xx = np.mgrid[0:NH, 0:NW].astype(np.float32) + 0.5
            L = np.zeros((NH, NW, 3), np.float32) + np.asarray(self.amb_col, np.float32) * self.amb
            for p in self.points:
                rr = np.hypot(xx - p['x'], yy - p['y']) / p['r']
                L += (1.0 / (1.0 + rr * rr) ** p.get('power', 1.6))[..., None] * (np.asarray(p['col'], np.float32) * p.get('k', 1.0))
            self._cache[key] = L
        return self._cache[key]


class Layer:
    def __init__(self, spr, x, y, light=None, soft=0.0, offset=(0.0, 0.0), alpha=1.0, E_k=1.0, tint=None):
        """spr: Sprite (rgba + E) or (rgba, E).  (x, y) = native top-left.  light: LightRig (None = the shot's
        default).  soft: blur sigma in NATIVE px -> composited at output res with a float `offset` (native px)."""
        if hasattr(spr, 'rgba'): self.rgba, self.E = spr.rgba, spr.E
        else: self.rgba, self.E = spr
        self.x, self.y = int(round(x)), int(round(y))
        self.light, self.soft, self.offset, self.alpha, self.E_k, self.tint = light, soft, offset, alpha, E_k, tint


class CUShot:
    def __init__(self, world=None, OW=1920, OH=1080, finisher=None):
        self.w = world
        self.OW, self.OH = OW, OH
        self.f = OW // NW
        self.finisher = finisher if finisher is not None else (world.finisher if world is not None else post.Finisher(OW, OH))

    # ---------------------------------------------------------------- plate
    def plate(self, cam, st, frame=0, bg_patches=None, dof=1.4, gain=1.0, mid=None):
        """render the room (background only unless mid is given) through World, capture the LINEAR image before
        grading, downsample to the native grid and blur (depth of field)."""
        cap = {}
        def grab(img):
            cap['img'] = img; return img
        self.w.render(cam, st, mid=mid, fg=None, frame=frame, pre_grade=grab, bg_patches=bg_patches)
        img = cv2.resize(cap['img'], (NW, NH), interpolation=cv2.INTER_AREA)
        if dof > 0: img = cv2.GaussianBlur(img, (0, 0), dof)
        return img * gain

    # ---------------------------------------------------------------- compose
    def _lit(self, L, rig):
        a = L.rgba.astype(np.float32) / 255.0
        h, w = a.shape[:2]
        x0, y0 = L.x, L.y
        X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(NW, x0 + w), min(NH, y0 + h)
        if X1 <= X0 or Y1 <= Y0: return None
        sa = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
        E = L.E[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0][..., None] * L.E_k
        Lm = rig.map()[Y0:Y1, X0:X1]
        Lm = Lm * (1 - np.clip(E, 0, 1)) + E * rig.eg
        alb = sa[..., :3]
        if L.tint is not None: alb = alb * np.asarray(L.tint, np.float32)
        col = alb * Lm
        glow = alb * E
        al = sa[..., 3:4] * L.alpha
        return (X0, Y0, X1, Y1), col, al, glow

    def compose(self, plate, layers, st, frame=0, ui=None, rig=None, emis_bloom=1.0, grade=None, post_native=None,
                pre_grade=None):
        rig = rig or LightRig()
        img = plate.astype(np.float32).copy()
        glow = np.zeros_like(img)
        soft = []
        for L in layers:
            if L.soft > 0: soft.append(L); continue
            r = self._lit(L, L.light or rig)
            if r is None: continue
            (X0, Y0, X1, Y1), col, al, gl = r
            img[Y0:Y1, X0:X1] = img[Y0:Y1, X0:X1] * (1 - al) + col * al
            glow[Y0:Y1, X0:X1] = glow[Y0:Y1, X0:X1] * (1 - al) + gl * al
        if post_native is not None: img, glow = post_native(img, glow)
        f = self.f
        up = cv2.resize(img, (self.OW, self.OH), interpolation=cv2.INTER_NEAREST)
        gup = cv2.resize(glow, (self.OW, self.OH), interpolation=cv2.INTER_LINEAR)
        for L in soft:                                   # blurred foreground at output res, float offset
            full = np.zeros((NH, NW, 3), np.float32); fa = np.zeros((NH, NW, 1), np.float32)
            r = self._lit(L, L.light or rig)
            if r is None: continue
            (X0, Y0, X1, Y1), col, al, gl = r
            full[Y0:Y1, X0:X1] = col; fa[Y0:Y1, X0:X1] = al
            M = np.float32([[f, 0, L.offset[0] * f], [0, f, L.offset[1] * f]])
            c2 = cv2.warpAffine(full * fa, M, (self.OW, self.OH), flags=cv2.INTER_LINEAR)
            a2 = cv2.warpAffine(fa, M, (self.OW, self.OH), flags=cv2.INTER_LINEAR)
            s = L.soft * f
            c2 = cv2.resize(cv2.GaussianBlur(cv2.resize(c2, (self.OW // 4, self.OH // 4), interpolation=cv2.INTER_AREA), (0, 0), max(0.5, s / 4)), (self.OW, self.OH))
            a2 = cv2.resize(cv2.GaussianBlur(cv2.resize(a2, (self.OW // 4, self.OH // 4), interpolation=cv2.INTER_AREA), (0, 0), max(0.5, s / 4)), (self.OW, self.OH))[..., None]
            up = up * (1 - a2) + c2
        if pre_grade is not None: up = pre_grade(up)
        g = grade or st['grade']
        out = post.apply_grade(up, g, self.finisher, frame, bloom_extra=gup * emis_bloom)
        if st.get('fade', 1.0) < 1.0: out = out * st['fade']
        if ui is not None:
            from .scene import ui_over
            out = ui_over(out, ui, scale=max(1, self.OW // ui.shape[1]))
        return out
