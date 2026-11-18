"""pixelkit.scene - G-buffer layers + the HD-2D frame renderer.

A frame is built from native-resolution layers (GLayer) that carry, per pixel:
    albedo RGBA  (crisp pixel art, painted with only a hint of form shading)
    E            emissive 0..1 (screens, LEDs, eyes: shown at full colour, feed the bloom)
    Z            depth in BoxRoom world units (nan = empty / use the room surface)
    N            surface orientation id (persp.BACK = camera facing, FLOOR = up facing ...)

World.render() then:
  1. lights every layer with smooth float light maps at f x native (sun through windows with
     blinds, cast shadows from the mid layer, ambient + corner/contact AO, bounce, point lights,
     sun-side rim light on sprites)
  2. warps albedo crisply and light smoothly to the output, multiplies (soft light over crisp
     pixels), composites bg (+DOF) / mid / fg (parallax + blur), adds god rays + dust glow
  3. grades (bloom/halation, split tone, saturation, contrast, vignette, grain)
"""
import numpy as np, cv2
from .core import Canvas
from .persp import BACK, FLOOR, CEIL, LEFT, RIGHT, NONE
from .light import sun_T, _normals_factor, LightRig, Sun
from .camera import warp_crisp, warp_smooth
from . import post

class GLayer:
    def __init__(self, W=480, H=270):
        self.W, self.H = W, H
        self.cv = Canvas(W, H)
        self.E = np.zeros((H, W), np.float32)
        self.Z = np.full((H, W), np.nan, np.float32)
        self.N = np.full((H, W), NONE, np.uint8)
        self.flat = np.zeros((H, W), bool)       # wall-mounted flat items (no contact AO halo)

    @property
    def a(self): return self.cv.a

    def alpha(self): return self.cv.a[..., 3] > 127

    def copy(self):
        g = GLayer(self.W, self.H); g.cv = self.cv.copy(); g.E = self.E.copy(); g.Z = self.Z.copy(); g.N = self.N.copy()
        g.flat = self.flat.copy(); return g

    def _region(self, x, y, w, h):
        x0, y0, x1, y1 = max(0, x), max(0, y), min(self.W, x + w), min(self.H, y + h)
        return x0, y0, x1, y1

    def put(self, spr, x, y, Z, N=BACK, E=None, alpha_mul=1.0, flat=False):
        """blit an RGBA sprite; writes Z (scalar or array like spr), N and E (scalar / array / None)."""
        x, y = int(round(x)), int(round(y))
        h, w = spr.shape[:2]
        x0, y0, x1, y1 = self._region(x, y, w, h)
        if x1 <= x0 or y1 <= y0: return
        s = spr[y0 - y:y1 - y, x0 - x:x1 - x]
        m = s[..., 3] > 127
        if alpha_mul < 0.999:
            self.cv.blit(spr, x, y, alpha_mul); return
        self.cv.a[y0:y1, x0:x1][m] = s[m]
        self.cv.a[y0:y1, x0:x1, 3][m] = 255
        zz = Z[y0 - y:y1 - y, x0 - x:x1 - x] if isinstance(Z, np.ndarray) else Z
        self.Z[y0:y1, x0:x1][m] = zz[m] if isinstance(zz, np.ndarray) else zz
        nn = N[y0 - y:y1 - y, x0 - x:x1 - x] if isinstance(N, np.ndarray) else N
        self.N[y0:y1, x0:x1][m] = nn[m] if isinstance(nn, np.ndarray) else nn
        self.flat[y0:y1, x0:x1][m] = flat
        if E is None: self.E[y0:y1, x0:x1][m] = 0
        elif isinstance(E, np.ndarray): self.E[y0:y1, x0:x1][m] = E[y0 - y:y1 - y, x0 - x:x1 - x][m]
        else: self.E[y0:y1, x0:x1][m] = E

    def put_layer(self, other, mask=None):
        m = other.alpha() if mask is None else mask
        self.cv.a[m] = other.cv.a[m]; self.E[m] = other.E[m]; self.Z[m] = other.Z[m]; self.N[m] = other.N[m]

    def fill(self, mask, col, Z, N=BACK, E=0.0, flat=False):
        self.cv.fill_mask(mask, col)
        self.flat[mask] = flat
        self.Z[mask] = Z[mask] if isinstance(Z, np.ndarray) else Z
        self.N[mask] = N
        self.E[mask] = E[mask] if isinstance(E, np.ndarray) else E

class Sprite:
    """a small RGBA sprite + emissive map, e.g. a character frame.  Draw with GLayer.put(s.rgba, x, y, Z, E=s.E)."""
    def __init__(self, w, h):
        self.cv = Canvas(w, h); self.E = np.zeros((h, w), np.float32)
    @property
    def rgba(self): return self.cv.a

def up_nearest(a, f):
    if f == 1: return a
    return np.repeat(np.repeat(a, f, 0), f, 1)

def edge_rim(alpha, dx=-1, dy=-1):
    """pixels of a sprite layer whose neighbour towards the light (dx, dy) is empty."""
    a = alpha
    p = np.pad(a, 1)
    H, W = a.shape
    nb_x = p[1:H + 1, 1 + dx:W + 1 + dx] if dx else np.ones_like(a)
    nb_y = p[1 + dy:H + 1 + dy, 1:W + 1] if dy else np.ones_like(a)
    return (a & ~nb_x).astype(np.float32), (a & ~nb_y).astype(np.float32)

class World:
    """one room + lights; renders frames from layers."""
    def __init__(self, room, windows, f=2, OW=1920, OH=1080):
        self.room, self.windows, self.f = room, windows, f
        self.OW, self.OH = OW, OH
        self.rig = LightRig(room, f)
        S = room.surfaces(f)
        self.x2, self.y2 = S['x'].astype(np.float32), S['y'].astype(np.float32)
        self.ao_room = self.rig.corner_ao(0.38, 16.0)
        self.finisher = post.Finisher(OW, OH)
        self._bg = None; self._sun_cache = {}

    # ------------------------------------------------------------ geometry
    def xyz(self, Z2):
        D = self.room.D
        X = (self.x2 - self.room.vx) * Z2 / D; Y = (self.y2 - self.room.vy) * Z2 / D
        return X, Y, Z2

    def gbuf2(self, layer, fill_room=False):
        f = self.f
        Z2 = up_nearest(layer.Z, f).astype(np.float32); N2 = up_nearest(layer.N, f)
        if fill_room:
            S = self.room.surfaces(f)
            m = np.isnan(Z2)
            Z2 = np.where(m, S['Z'], Z2).astype(np.float32); N2 = np.where(m, S['id'], N2).astype(np.uint8)
        return Z2, N2

    # ------------------------------------------------------------ sun
    def sun_map(self, sun, Z2, N2, facing=None):
        """T * lambert for every pixel; facing: override lambert for camera-facing sprites."""
        X, Y, Z = self.xyz(np.nan_to_num(Z2, nan=self.room.D))
        T = sun_T(self.room, sun, self.windows, X, Y, Z).astype(np.float32)
        nd = _normals_factor(N2, sun)
        mx = max(1e-6, float(nd.max()))
        lam = 0.35 + 0.65 * nd / mx
        if facing is not None:
            lam = np.where(N2 == BACK, facing, lam)
        return T * lam, T

    def shadow(self, caster_alpha, Zc, sun, Z2, soft=1.0):
        """occlusion of the sun on receivers (per-pixel depth Z2) by a caster layer on plane Zc."""
        d = sun.d; r = self.room
        X, Y, Z = self.xyz(np.nan_to_num(Z2, nan=r.D))
        t = (Z - Zc) / d[2]
        valid = t > 0.5
        qx, qy = r.project(X - t * d[0], Y - t * d[1], np.full_like(X, Zc))
        a = caster_alpha.astype(np.float32)
        if soft > 0: a = cv2.GaussianBlur(a, (0, 0), soft)
        occ = cv2.remap(a, (qx - 0.5).astype(np.float32), (qy - 0.5).astype(np.float32), cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        return np.where(valid, occ, 0).astype(np.float32)

    # ------------------------------------------------------------ background (static) cache
    def set_background(self, bg, sun, ao_obj=0.40, bounce=0.30, bounce_sigma=34.0):
        f = self.f
        Z2, N2 = self.gbuf2(bg, fill_room=True)
        objm = ~np.isnan(up_nearest(bg.Z, f)) & ~up_nearest(bg.flat, f)
        S, T = self.sun_map(sun, Z2, N2)
        alb2 = up_nearest(bg.cv.a[..., :3], f).astype(np.float32) / 255.0
        # contact AO: room pixels near (mostly below) objects get darker
        om = objm.astype(np.float32)
        k = cv2.GaussianBlur(om, (0, 0), 5 * f / 2)
        k = np.maximum(k, np.roll(cv2.GaussianBlur(om, (0, 0), 3 * f / 2), 3 * f // 2, axis=0))
        ao = self.ao_room * (1 - ao_obj * np.clip(k * 1.6, 0, 1) * (~objm))
        # bounce = blurred sunlit albedo
        sm = cv2.resize(S[..., None] * alb2, (self.rig.w // 4, self.rig.h // 4), interpolation=cv2.INTER_AREA)
        sm = cv2.GaussianBlur(sm, (0, 0), bounce_sigma * f / 4)
        B = cv2.resize(sm, (self.rig.w, self.rig.h), interpolation=cv2.INTER_LINEAR) * bounce
        self._bg = dict(layer=bg, Z2=Z2, N2=N2, S=S, T=T, ao=ao.astype(np.float32), B=B.astype(np.float32),
                        rgb=bg.cv.a[..., :3].copy(), E2=up_nearest(bg.E, f), sun=sun)
        return self._bg

    # ------------------------------------------------------------ light assembly
    def light(self, which, st, Z2=None, N2=None, alpha=None, shadow=None, E2=None):
        """returns L (H2, W2, 3) for 'bg' (cached geometry) or 'mid' (given Z2/N2/alpha native)."""
        sun_col = np.asarray(st['sun_color'], np.float32) * st['sun_k'] * st.get('sun_int', 1.25)
        amb = np.asarray(st['amb_color'], np.float32) * st['amb']
        if which == 'bg':
            g = self._bg
            S = g['S'] if shadow is None else g['S'] * (1 - shadow)
            L = g['ao'][..., None] * amb + S[..., None] * sun_col + g['B'] * (st['sun_k'] * st.get('bounce_k', 1.0))
            L = L * (1 + 0 * S[..., None])
            pts_scope = 'bg'
        else:
            S, T = self.sun_map(st['sun'], Z2, N2, facing=st.get('sprite_facing', 0.80))
            if shadow is not None: S = S * (1 - shadow)
            L = amb * st.get('mid_amb', 1.0) + S[..., None] * sun_col
            if alpha is not None and st.get('rim', 0) > 0:
                rx, ry = edge_rim(alpha, -1, -1)
                rim = (rx * 1.0 + ry * 0.6)
                rim2 = up_nearest(rim, self.f) * T
                L = L + rim2[..., None] * sun_col * st['rim']
            pts_scope = 'mid'
        for p in st.get('points', ()):
            if p.get('k', 1) <= 0 or pts_scope not in p.get('layers', ('bg', 'mid')): continue
            fall = self.rig.point(p['x'], p['y'], p['r'], p.get('power', 1.6))
            L = L + fall[..., None] * (np.asarray(p['col'], np.float32) * p.get('k', 1.0))
        if E2 is not None:
            eg = st.get('emis_gain', 1.15)
            L = L * (1 - E2[..., None]) + E2[..., None] * eg
        return L.astype(np.float32)

    # ------------------------------------------------------------ frame
    def patched_bg(self, patches):
        """albedo + emissive of the cached background with dynamic flat sprites pasted on top
        (wall clock hands, TV / sign content ...).  patches: [(rgba, x, y) or (rgba, x, y, E)].
        The patched pixels keep the background's light (they are flat on their wall)."""
        g = self._bg; f = self.f
        rgb = g['rgb'].copy(); E2 = None
        for p in patches:
            spr, x, y = p[0], int(round(p[1])), int(round(p[2])); E = p[3] if len(p) > 3 else None
            h, w = spr.shape[:2]
            x0, y0, x1, y1 = max(0, x), max(0, y), min(rgb.shape[1], x + w), min(rgb.shape[0], y + h)
            if x1 <= x0 or y1 <= y0: continue
            s = spr[y0 - y:y1 - y, x0 - x:x1 - x]; m = s[..., 3] > 127
            rgb[y0:y1, x0:x1][m] = s[..., :3][m]
            if E is not None:
                if E2 is None: E2 = g['E2'].copy()
                e = np.where(m, E[y0 - y:y1 - y, x0 - x:x1 - x], g['layer'].E[y0:y1, x0:x1])
                E2[y0 * f:y1 * f, x0 * f:x1 * f] = up_nearest(e.astype(np.float32), f)
        return rgb, E2

    def render(self, cam, st, mid=None, fg=None, frame=0, extra_glow=None, ui=None, mid_Z=340.0, glow_out=None, pre_grade=None,
               bg_patches=None, post_ui=None):
        """st: light/grade state dict.  mid: GLayer (dynamic).  fg: (rgba native, parallax, blur_px, light_k)
        extra_glow: additive (H2, W2, 3) buffer at f (dust/sparkles).  ui: RGBA uint8 (OH/3, OW/3) drawn on top.
        bg_patches: dynamic flat sprites on the background (see patched_bg).
        post_ui: callable(img) -> img applied after grading, before the UI (e.g. dim / blur behind a window)."""
        f = self.f; g = self._bg
        bg_rgb_src, E2_patch = (g['rgb'], None) if not bg_patches else self.patched_bg(bg_patches)
        sun = st['sun']
        mid_alpha = mid.alpha() if mid is not None else None
        # --- shadows of the mid layer on the background
        sh = None
        if mid is not None and st['sun_k'] > 0 and st.get('cast_shadows', True):
            sh = self.shadow(mid_alpha, mid_Z, sun, g['Z2'], soft=st.get('shadow_soft', 1.0)) * st.get('shadow_k', 0.85)
        E2src = g['E2'] if E2_patch is None else E2_patch
        E2bg = E2src if st.get('bg_emis_k', 1.0) >= 0.999 else E2src * max(0.0, st.get('bg_emis_k', 1.0))
        Lbg = self.light('bg', st, shadow=sh, E2=E2bg)
        bg_rgb = warp_crisp(bg_rgb_src, cam).astype(np.float32) * (1 / 255.0)
        img = bg_rgb * warp_smooth(Lbg, cam, f)
        dof = st.get('dof', 0.0) * cam.s           # native px -> output px
        if dof > 0.6:
            sm = cv2.resize(img, (self.OW // 2, self.OH // 2), interpolation=cv2.INTER_AREA)
            sm = cv2.GaussianBlur(sm, (0, 0), dof / 2)
            img = cv2.resize(sm, (self.OW, self.OH), interpolation=cv2.INTER_LINEAR)
        bs = st.get('bg_soft')                     # v0.11: pixel-preserving background softening (close-ups)
        if bs:
            from .outdoor import pixel_soft
            cell = bs.get('cell') or max(2, int(round(cam.s)))
            img = pixel_soft(img, cell, sigma=bs.get('sigma', 1.0), bokeh_k=bs.get('bokeh_k', 0.3), dim=bs.get('dim', 0.96),
                             desat=bs.get('desat', 0.10))
        glow_src = None
        # --- god rays (behind the mid layer is fine: rays are mostly in the air in front of walls)
        if st.get('rays', 0) > 0 and st['sun_k'] > 0 and 'rays_map' in st:
            rm, rf = st['rays_map']
            img = img + warp_smooth(rm[..., None] * np.asarray(st['sun_color'], np.float32), cam, rf) * (st['rays'] * st['sun_k'])
        # --- mid layer
        if mid is not None:
            Z2, N2 = self.gbuf2(mid)
            E2m = up_nearest(mid.E, f)
            Lm = self.light('mid', st, Z2=Z2, N2=N2, alpha=mid_alpha, E2=E2m, shadow=st.get('mid_shadow'))
            rgba = warp_crisp(mid.cv.a, cam)
            a = rgba[..., 3:4].astype(np.float32) * (1 / 255.0)
            lit = rgba[..., :3].astype(np.float32) * (1 / 255.0) * warp_smooth(Lm, cam, f)
            img = img * (1 - a) + lit * a
            if st.get('emis_bloom', 0) > 0:
                eg = up_nearest(mid.E, 1)[..., None] * (mid.cv.a[..., :3].astype(np.float32) / 255.0)
                glow_src = warp_smooth(cv2.resize(eg, (eg.shape[1] * f, eg.shape[0] * f), interpolation=cv2.INTER_NEAREST), cam, f) * st['emis_bloom']
        # --- additive glow (dust etc.) - crisp native-res buffer, or soft output-res buffer
        if extra_glow is not None:
            img = img + warp_crisp(extra_glow, cam, f)
        if glow_out is not None:
            img = img + glow_out
        # --- foreground (parallax, blurred, mostly silhouette)
        if fg is not None:
            frgba, par, blur, lk = fg
            c2 = cam.layer(par)
            o = warp_crisp(frgba, c2)
            a = o[..., 3:4].astype(np.float32) / 255.0
            col = o[..., :3].astype(np.float32) / 255.0 * np.asarray(lk, np.float32)
            if blur > 0:
                bpx = blur * c2.s
                sm = lambda z: cv2.resize(cv2.GaussianBlur(cv2.resize(z, (self.OW // 4, self.OH // 4), interpolation=cv2.INTER_AREA), (0, 0), max(0.5, bpx / 4)), (self.OW, self.OH), interpolation=cv2.INTER_LINEAR)
                a = sm(a); a = a[..., None] if a.ndim == 2 else a
                col = sm(col * a) / np.maximum(a, 1e-4)
            img = img * (1 - a) + col * a
        if pre_grade is not None:           # hook: callable(img) -> img  (e.g. screen-space FX before grading)
            img = pre_grade(img)
        # --- grade
        out = post.apply_grade(img, st['grade'], self.finisher, frame, bloom_extra=glow_src)
        if st.get('fade', 1.0) < 1.0:
            out = out * st['fade']
        if post_ui is not None:
            out = post_ui(out)
        if ui is not None:
            out = ui_over(out, ui, scale=max(1, self.OW // ui.shape[1]))
        return out

def ui_over(img, ui_rgba, scale=3, alpha=1.0):
    """composite a small RGBA UI canvas (e.g. 640x360) crisply over the output."""
    a = ui_rgba[..., 3]
    if not a.any(): return img
    ys, xs = np.nonzero(a)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = ui_rgba[y0:y1, x0:x1]
    up = cv2.resize(sub, ((x1 - x0) * scale, (y1 - y0) * scale), interpolation=cv2.INTER_NEAREST).astype(np.float32) / 255.0
    al = up[..., 3:4] * alpha
    reg = img[y0 * scale:y1 * scale, x0 * scale:x1 * scale]
    img[y0 * scale:y1 * scale, x0 * scale:x1 * scale] = reg * (1 - al) + up[..., :3] * al
    return img

def make_state(tod='golden', grade='golden_hd2d', **over):
    """light/grade state dict for World.render with the tuned reference-look defaults.
    Any key can be overridden, e.g. make_state('golden', rays=1.2, amb=0.9)."""
    from .light import TOD, Sun
    t = TOD[tod]
    sun = Sun(*t['sun'])
    st = dict(sun=sun, sun_color=sun.color, sun_k=1.0, sun_int=t['sun'][2], amb_color=t['amb'][0], amb=t['amb'][1],
              rim=0.5, sprite_facing=0.35, mid_amb=1.12, emis_bloom=0.4, emis_gain=1.15, rays=t['rays'],
              grade=dict(post.GRADES[grade]), shadow_k=0.85, fade=1.0, points=[])
    st.update(over)
    return st


# ====================================================================== flat inserts
class FlatScene:
    """light-weight renderer for flat close-up inserts (a clock on a wall, a calendar page ...):
    native albedo x a painted light map (+ emissive) -> the same crisp/smooth camera warp, grade and UI
    path as World, so inserts cut seamlessly with the room shots.

        fs = FlatScene()
        L = fs.ambient((0.62, 0.52, 0.70), 0.75) + fs.blinds(...) + fs.pool(...)
        img = fs.render(cam, albedo_rgba, L, post.GRADES['golden_hd2d'], E=emissive, frame=i, ui=ui_rgba)
    """
    def __init__(self, W=480, H=270, f=2, OW=1920, OH=1080):
        self.W, self.H, self.f, self.OW, self.OH = W, H, f, OW, OH
        self.finisher = post.Finisher(OW, OH)
        ys, xs = np.mgrid[0:H * f, 0:W * f].astype(np.float32)
        self.X, self.Y = (xs + 0.5) / f, (ys + 0.5) / f            # native-px coordinates of the light grid

    # ------------------------------------------------------------ painted light
    def ambient(self, col, k=1.0, top=1.0, bottom=1.0):
        g = top + (bottom - top) * (self.Y / self.H)
        return (g[..., None] * np.asarray(col, np.float32) * k).astype(np.float32)

    def pool(self, cx, cy, rx, ry, col, k=1.0, power=2.0):
        d = ((self.X - cx) / rx) ** 2 + ((self.Y - cy) / ry) ** 2
        return (np.exp(-d * power / 2)[..., None] * np.asarray(col, np.float32) * k).astype(np.float32)

    def blinds(self, col, k=1.0, angle=-0.42, period=18.0, open_=0.55, soft=0.12, region=None, x0=0.0, y0=0.0,
               fade_x=None):
        """slanted sun stripes through venetian blinds. region: (cx, cy, rx, ry) soft elliptical window patch.
        fade_x: (x_a, x_b) stripes fade out from x_a to x_b (light falls off away from the window)."""
        u = (self.Y - y0) + (self.X - x0) * angle
        ph = np.mod(u / period, 1.0)
        s = np.clip((open_ - ph) / soft + 0.5, 0, 1) * np.clip((ph - 0.0) / soft + 0.5, 0, 1)
        if region is not None:
            cx, cy, rx, ry = region
            d = ((self.X - cx) / rx) ** 2 + ((self.Y - cy) / ry) ** 2
            s = s * np.clip(1.6 - d, 0, 1)
        if fade_x is not None:
            a, b = fade_x
            s = s * np.clip((self.X - b) / (a - b), 0, 1)
        return (s[..., None] * np.asarray(col, np.float32) * k).astype(np.float32)

    def shadow(self, L, alpha, dx, dy, k=0.6, soft=3.0):
        """darken L where a sprite mask (native alpha bool, H x W) casts a soft offset shadow."""
        a = cv2.resize(alpha.astype(np.float32), (self.W * self.f, self.H * self.f), interpolation=cv2.INTER_NEAREST)
        M = np.float32([[1, 0, dx * self.f], [0, 1, dy * self.f]])
        a = cv2.warpAffine(a, M, (a.shape[1], a.shape[0]))
        a = cv2.GaussianBlur(a, (0, 0), soft * self.f)
        return (L * (1 - k * a[..., None])).astype(np.float32)

    # ------------------------------------------------------------ frame
    def render(self, cam, albedo, L, grade, E=None, frame=0, ui=None, glow_out=None, fade=1.0, post_ui=None,
               emis_gain=1.15, emis_bloom=0.5, pre_grade=None):
        f = self.f
        rgb = albedo[..., :3] if albedo.shape[2] == 4 else albedo
        Lw = L
        if E is not None:
            E2 = up_nearest(E.astype(np.float32), f)[..., None]
            Lw = L * (1 - E2) + E2 * emis_gain
        img = warp_crisp(np.ascontiguousarray(rgb), cam).astype(np.float32) * (1 / 255.0) * warp_smooth(Lw, cam, f)
        glow_src = None
        if E is not None and emis_bloom > 0:
            eg = E.astype(np.float32)[..., None] * (rgb.astype(np.float32) / 255.0)
            glow_src = warp_smooth(cv2.resize(eg, (self.W * f, self.H * f), interpolation=cv2.INTER_NEAREST), cam, f) * emis_bloom
        if glow_out is not None: img = img + glow_out
        if pre_grade is not None: img = pre_grade(img)
        out = post.apply_grade(img, grade, self.finisher, frame, bloom_extra=glow_src)
        if fade < 1.0: out = out * fade
        if post_ui is not None: out = post_ui(out)
        if ui is not None: out = ui_over(out, ui, scale=max(1, self.OW // ui.shape[1]))
        return out


def dim_blur(img, k=0.5, blur_px=0.0, tint=(1.0, 1.0, 1.0)):
    """post_ui helper: darken (k = 0..1 amount) and optionally blur the graded frame behind a UI window."""
    if k <= 0 and blur_px <= 0: return img
    out = img
    if blur_px > 0.5:
        H, W = img.shape[:2]
        sm = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        sm = cv2.GaussianBlur(sm, (0, 0), blur_px / 4)
        out = cv2.resize(sm, (W, H), interpolation=cv2.INTER_LINEAR)
    return out * (1 - k) * np.asarray(tint, np.float32) ** k
