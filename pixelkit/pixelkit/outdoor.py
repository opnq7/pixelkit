"""pixelkit.outdoor - HD-2D renderer for OUTDOOR side-view sets (streets, parks, river banks).

The office World is a perspective box lit through windows.  Outdoors there is no box: the set is a
painted side-view diorama (any width, e.g. 960 px for tracking shots) and the light is painted too:

    bg = dict(rgba=(H, W, 4) uint8 albedo,
              E=(H, W) emissive (sky = 1, lit signs, windows ...),
              T=(H, W) sun visibility 0..1 (painted shadows of awnings / trees / buildings),
              ao=(H, W) ambient occlusion 0..1 (1 = open sky),
              ground=(W,) float: sun visibility at the walking line, per column (lights sprites walking
                     through tree / building shadows; optional))
    sc = OutdoorScene(bg)                                 # caches the light-independent parts
    st = outdoor_state('morning', exposure=1.0)           # light + grade dict (any key overridable)
    mid = GLayer(W, H); mid.put(claude.rgba, x, y, Z=0, E=...)    # dynamic sprites (Z unused)
    casters = [(alpha_bool_sprite, x, y, foot_y), ...]    # ground shadows of the sprites
    img = sc.render(cam, st, mid, casters, fg=..., ui=..., frame=i)

Light model (per pixel, at f x native, smooth over crisp pixels like World):
    L_bg  = amb * ao + sun * T * (1 - mid shadows) + E
    L_mid = amb * mid_amb + sun * facing * ground(x) + rim (sun-side sprite edges) + E
Ground shadows of sprites: sheared, flattened copies of their silhouettes (shear sx, flatten sy),
blurred by `shadow_soft`; plus a small contact-AO blob under each caster.
Haze / god rays are painted (`haze_map`) and added before grading.  Exposure (st['grade']['exposure'])
drives "stepping out into the sun" white-outs.
"""
import numpy as np, cv2
from .scene import GLayer, up_nearest, edge_rim, ui_over
from .camera import warp_crisp, warp_smooth
from . import post
from .light import dither_light

# sun colour, sun strength, ambient colour, ambient strength, haze colour, haze strength
OTOD = {
    'morning': dict(sun=(1.00, 0.80, 0.60), sun_k=1.55, amb=(0.70, 0.66, 0.92), amb_k=0.78, haze=(1.0, 0.86, 0.66), haze_k=0.30),
    'noon':    dict(sun=(1.00, 0.93, 0.80), sun_k=1.45, amb=(0.72, 0.76, 0.95), amb_k=0.85, haze=(1.0, 0.95, 0.85), haze_k=0.18),
    'warm':    dict(sun=(1.00, 0.74, 0.52), sun_k=1.60, amb=(0.80, 0.66, 0.86), amb_k=0.80, haze=(1.0, 0.80, 0.58), haze_k=0.34),
    'sunset':  dict(sun=(1.00, 0.56, 0.40), sun_k=1.50, amb=(0.66, 0.52, 0.84), amb_k=0.66, haze=(1.0, 0.62, 0.44), haze_k=0.42),
    'dusk':    dict(sun=(0.80, 0.42, 0.45), sun_k=0.35, amb=(0.46, 0.44, 0.78), amb_k=0.55, haze=(0.7, 0.5, 0.7), haze_k=0.15),
    'grey':    dict(sun=(0.85, 0.86, 0.90), sun_k=0.55, amb=(0.66, 0.68, 0.78), amb_k=0.85, haze=(0.8, 0.82, 0.88), haze_k=0.10),
}

def lerp_otod(a, b, k):
    A = OTOD[a] if isinstance(a, str) else a; B = OTOD[b] if isinstance(b, str) else b
    out = {}
    for key in A:
        va, vb = A[key], B[key]
        out[key] = tuple(x + (y - x) * k for x, y in zip(va, vb)) if isinstance(va, tuple) else va + (vb - va) * k
    return out

def outdoor_state(tod='morning', grade='golden_hd2d', **over):
    t = dict(OTOD[tod]) if isinstance(tod, str) else dict(tod)
    st = dict(t, mid_amb=1.10, facing=0.82, rim=0.55, emis_gain=1.15, emis_bloom=0.45, shadow_k=0.62,
              shadow_sx=0.55, shadow_sy=-0.20, shadow_soft=1.2, contact_k=0.45, bg_emis_k=1.0, haze_gain=1.0,
              grade=dict(post.GRADES[grade]), fade=1.0, points=[], warm=0.0,
              light_dither=0.20, light_dither_k=1.0, haze_dither=0.20, sun_grad=(0.0, 0.0))
    st.update(over)
    return st

def set_tod(st, tod):
    """overwrite the light keys of a state with another (possibly lerped) time of day."""
    st.update(OTOD[tod] if isinstance(tod, str) else tod); return st


class OutdoorScene:
    def __init__(self, bg, f=2, OW=1920, OH=1080):
        self.f, self.OW, self.OH = f, OW, OH
        self.bg = bg
        H, W = bg['rgba'].shape[:2]
        self.W, self.H = W, H
        self.rgb = np.ascontiguousarray(bg['rgba'][..., :3])
        self.E2 = up_nearest(bg.get('E', np.zeros((H, W), np.float32)).astype(np.float32), f)
        self.T2 = self._smooth(bg.get('T', np.ones((H, W), np.float32)), 0.6)
        self.ao2 = self._smooth(bg.get('ao', np.ones((H, W), np.float32)), 1.2)
        self.ground = np.asarray(bg.get('ground', np.ones(W, np.float32)), np.float32)
        self.haze2 = bg.get('haze')               # optional (H*f, W*f) painted haze / god rays
        # optional RGBA layer drawn over the mid layer (trees / lamp posts at the curb).  May be a list of
        # variants (e.g. canopy sway frames) - pick one per frame with render(front_i=...).
        fr = bg.get('front')
        self.fronts = None if fr is None else (list(fr) if isinstance(fr, (list, tuple)) else [fr])
        self.front = None if fr is None else self.fronts[0]
        self._front_rim = {}
        self.frontE2 = None
        if self.front is not None:
            self.frontE2 = up_nearest(bg.get('frontE', np.zeros((H, W), np.float32)).astype(np.float32), f)
        self.finisher = post.Finisher(OW, OH)
        ys, xs = np.mgrid[0:H * f, 0:W * f].astype(np.float32)
        self.X, self.Y = (xs + 0.5) / f, (ys + 0.5) / f
        self._hazeq = {}

    def front_rim(self, i):
        if i not in self._front_rim:
            fa = self.fronts[i][..., 3] > 127
            rx, ry = edge_rim(fa, -1, -1)
            self._front_rim[i] = up_nearest(rx * 1.0 + ry * 0.6, self.f).astype(np.float32)
        return self._front_rim[i]

    def haze_q(self, step):
        """painted haze quantised once (crisp dithered bands instead of a smooth airbrush)."""
        if step <= 0 or self.haze2 is None: return self.haze2
        if step not in self._hazeq:
            h = self.haze2
            from .core import BAYER4
            f = self.f; H, W = self.H, self.W
            hn = cv2.resize(h, (W, H), interpolation=cv2.INTER_AREA)
            yy, xx = np.mgrid[0:H, 0:W]
            th = BAYER4[yy % 4, xx % 4]
            lv = step * 0.5
            q = np.floor(hn / lv + th) * lv
            self._hazeq[step] = np.repeat(np.repeat(q.astype(np.float32), f, 0), f, 1)
        return self._hazeq[step]

    def _smooth(self, a, s):
        a = cv2.resize(a.astype(np.float32), (self.W * self.f, self.H * self.f), interpolation=cv2.INTER_LINEAR)
        return cv2.GaussianBlur(a, (0, 0), s * self.f) if s > 0 else a

    # ------------------------------------------------------------ shadows
    def ground_shadows(self, casters, st):
        """native (H, W) float occlusion map from [(alpha bool (h, w), x, y, foot_y[, k]), ...]."""
        H, W = self.H, self.W
        acc = np.zeros((H, W), np.float32)
        sx, sy = st['shadow_sx'], st['shadow_sy']
        yy, xx = np.mgrid[0:H, 0:W]
        for c in casters:
            a, x, y, foot = c[:4]; k = c[4] if len(c) > 4 else 1.0
            a = a.astype(np.float32)
            # sprite (u, v) -> ground: X = x + u + sx * (foot - y - v),  Y = foot + sy * (foot - y - v)
            M = np.float32([[1, -sx, x + sx * (foot - y)], [0, -sy, foot + sy * (foot - y)]])
            sh = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
            acc = np.maximum(acc, sh * k)
            # contact blob under the feet
            cols = np.nonzero(a.max(0) > 0.5)[0]
            if len(cols):
                cx = x + (cols[0] + cols[-1]) / 2; rx = (cols[-1] - cols[0]) / 2 + 2
                blob = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - foot) / 2.2) ** 2) * 1.6) * st['contact_k'] * k
                acc = np.maximum(acc, blob.astype(np.float32))
        return acc

    # ------------------------------------------------------------ frame
    def render(self, cam, st, mid=None, casters=(), fg=None, ui=None, frame=0, glow_out=None, post_ui=None,
               pre_grade=None, bg_patches=None, extra_shadow=None, mid_T=None, front_i=0, mid_extra=None, add_out=None,
               bg_fx=None):
        """mid: GLayer (W x H of the set).  fg: (rgba, parallax, blur_px, light_mul) like World.render.
        bg_patches: [(rgba, x, y[, E])] dynamic flat sprites baked into the background (signs, a door ...).
        extra_shadow: native (H, W) occlusion added to the sprite shadows (e.g. a passing cloud).
        mid_T: native (H, W) sun visibility for the mid layer (default: per-column `ground`).
        bg_fx: fn(img) -> img applied to the lit background (output res) BEFORE the mid layer is composited,
               e.g. lambda im: dof(im, 14) for close-ups: soft background, pixel-sharp characters."""
        f = self.f
        sun = np.asarray(st['sun'], np.float32) * st['sun_k']
        amb = np.asarray(st['amb'], np.float32) * st['amb_k']
        rgb, E2 = self.rgb, self.E2
        if bg_patches:
            rgb = rgb.copy(); E2 = E2.copy()
            for p in bg_patches:
                spr, x, y = p[0], int(round(p[1])), int(round(p[2])); E = p[3] if len(p) > 3 else None
                h, w = spr.shape[:2]
                x0, y0, x1, y1 = max(0, x), max(0, y), min(self.W, x + w), min(self.H, y + h)
                if x1 <= x0 or y1 <= y0: continue
                s = spr[y0 - y:y1 - y, x0 - x:x1 - x]; m = s[..., 3] > 127
                rgb[y0:y1, x0:x1][m] = s[..., :3][m]
                e = np.zeros((y1 - y0, x1 - x0), np.float32) if E is None else E[y0 - y:y1 - y, x0 - x:x1 - x]
                cur = E2[y0 * f:y1 * f, x0 * f:x1 * f]
                E2[y0 * f:y1 * f, x0 * f:x1 * f] = np.where(up_nearest(m, f), up_nearest(e.astype(np.float32), f), cur)
        # --- background light
        occ = None
        if casters:
            occ = self.ground_shadows(casters, st)
        if extra_shadow is not None:
            occ = extra_shadow if occ is None else np.maximum(occ, extra_shadow)
        T2 = self.T2
        if occ is not None:
            o2 = cv2.resize(occ, (self.W * f, self.H * f), interpolation=cv2.INTER_LINEAR)
            o2 = cv2.GaussianBlur(o2, (0, 0), st['shadow_soft'] * f)
            T2 = T2 * (1 - st['shadow_k'] * np.clip(o2, 0, 1))
        L = self.ao2[..., None] * amb + T2[..., None] * sun
        for p in st.get('points', ()):
            d = ((self.X - p['x']) ** 2 + (self.Y - p['y']) ** 2) / (p['r'] ** 2)
            L = L + (np.exp(-d * p.get('power', 1.6)) * p.get('k', 1.0))[..., None] * np.asarray(p['col'], np.float32)
        gx, gy = st.get('sun_grad', (0.0, 0.0))
        if gx or gy:      # broad falloff of the low sun across the set (brighter toward the sun / the sky)
            g = 1.0 + gx * (0.5 - self.X / self.W) + gy * (0.5 - self.Y / self.H)
            L = L * g[..., None]
        if st.get('light_dither', 0) > 0:
            L = dither_light(L, f, st['light_dither'], st.get('light_dither_k', 1.0))
        Eb = E2 * st.get('bg_emis_k', 1.0)
        eg = st['emis_gain']
        L = L * (1 - Eb[..., None]) + Eb[..., None] * eg
        wl = warp_crisp if st.get('light_dither', 0) > 0 else warp_smooth     # quantised light stays pixel-crisp
        img = warp_crisp(rgb, cam).astype(np.float32) * (1 / 255.0) * wl(L.astype(np.float32), cam, f)
        if bg_fx is not None: img = bg_fx(img)
        glow_src = None
        # --- mid layer
        if mid is not None and mid.alpha().any():
            alpha = mid.alpha()
            if mid_T is None:
                Tm = np.broadcast_to(self.ground[None, :], (self.H, self.W)).astype(np.float32)
            else:
                Tm = mid_T.astype(np.float32)
            Tm2 = cv2.resize(Tm, (self.W * f, self.H * f), interpolation=cv2.INTER_LINEAR)
            Lm = amb * st['mid_amb'] + (Tm2 * st['facing'])[..., None] * sun
            if st.get('rim', 0) > 0:
                rx, ry = edge_rim(alpha, -1, -1)
                rim2 = up_nearest(rx * 1.0 + ry * 0.6, f) * Tm2
                Lm = Lm + rim2[..., None] * sun * st['rim']
            for p in st.get('points', ()):
                if 'mid' not in p.get('layers', ('bg', 'mid')): continue
                d = ((self.X - p['x']) ** 2 + (self.Y - p['y']) ** 2) / (p['r'] ** 2)
                Lm = Lm + (np.exp(-d * p.get('power', 1.6)) * p.get('k', 1.0))[..., None] * np.asarray(p['col'], np.float32)
            Em = up_nearest(mid.E, f)[..., None]
            Lm = Lm * (1 - Em) + Em * eg
            rgba = warp_crisp(mid.cv.a, cam)
            a = rgba[..., 3:4].astype(np.float32) * (1 / 255.0)
            lit = rgba[..., :3].astype(np.float32) * (1 / 255.0) * warp_smooth(Lm.astype(np.float32), cam, f)
            img = img * (1 - a) + lit * a
            if st.get('emis_bloom', 0) > 0:
                e = mid.E[..., None] * (mid.cv.a[..., :3].astype(np.float32) / 255.0)
                glow_src = warp_smooth(cv2.resize(e, (self.W * f, self.H * f), interpolation=cv2.INTER_NEAREST), cam, f) * st['emis_bloom']
        # --- static front layer (trees / lamp posts at the curb, in front of the walkers)
        if mid_extra is not None: img = mid_extra(img)
        if self.front is not None and st.get('front_k', 1.0) > 0:
            fi = front_i % len(self.fronts)
            frgba = warp_crisp(self.fronts[fi], cam)
            a = frgba[..., 3:4].astype(np.float32) * (1 / 255.0)
            if a.any():
                Lf = amb * st['mid_amb'] + sun * st.get('front_sun', 0.9)
                Lf = Lf + self.front_rim(fi)[..., None] * sun * st['rim']
                Lf = Lf * (1 - self.frontE2[..., None]) + self.frontE2[..., None] * eg
                img = img * (1 - a) + frgba[..., :3].astype(np.float32) * (1 / 255.0) * warp_smooth(Lf.astype(np.float32), cam, f) * a
        # --- haze / rays
        if self.haze2 is not None and st.get('haze_k', 0) > 0:
            hz = self.haze_q(st.get('haze_dither', 0))
            img = img + warp_smooth(hz[..., None] * np.asarray(st['haze'], np.float32), cam, f) * (st['haze_k'] * st['haze_gain'])
        if add_out is not None: img = img + add_out
        if glow_out is not None: img = img + glow_out
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
        if pre_grade is not None: img = pre_grade(img)
        out = post.apply_grade(img, st['grade'], self.finisher, frame, bloom_extra=glow_src)
        if st.get('fade', 1.0) < 1.0: out = out * st['fade']
        if post_ui is not None: out = post_ui(out)
        if ui is not None: out = ui_over(out, ui, scale=max(1, self.OW // ui.shape[1]))
        return out


def dof(img, sigma=14.0, bokeh_k=0.6, thr=0.85, down=4):
    """depth-of-field blur for close-up backgrounds (output res float RGB): a cheap downsampled gaussian plus
    soft 'bokeh' discs grown from the brightest pixels (sun glitter, lanterns)."""
    H, W = img.shape[:2]
    sm = cv2.resize(img, (W // down, H // down), interpolation=cv2.INTER_AREA)
    bl = cv2.GaussianBlur(sm, (0, 0), sigma / down)
    if bokeh_k > 0:
        lum = sm.max(-1)
        hi = np.clip((lum - thr) / (1 - thr + 1e-6), 0, 1)[..., None] * sm
        r = max(2, int(round(sigma * 0.55 / down)))
        disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)).astype(np.float32)
        disc /= disc.sum() * 0.35
        bk = cv2.filter2D(hi, -1, disc)
        bl = bl + bokeh_k * cv2.GaussianBlur(bk, (0, 0), 0.8)
    return cv2.resize(bl, (W, H), interpolation=cv2.INTER_LINEAR)


# ====================================================================== painting helpers
def haze_map(W, H, f=2, sun_xy=(-60, -40), rays=10, ray_k=0.55, glow_k=0.6, glow_r=220.0, seed=3, horizon=None,
             horizon_k=0.0, angle_spread=0.55):
    """painted morning haze: soft glow around an off-screen sun + fanned god-ray streaks + optional horizon band.
    returns (H*f, W*f) float32 (multiplied by st['haze'] * st['haze_k'] at render)."""
    ys, xs = np.mgrid[0:H * f, 0:W * f].astype(np.float32)
    X, Y = (xs + 0.5) / f, (ys + 0.5) / f
    dx, dy = X - sun_xy[0], Y - sun_xy[1]
    r = np.sqrt(dx * dx + dy * dy) + 1e-3
    out = glow_k * np.exp(-r / glow_r)
    if rays:
        ang = np.arctan2(dy, dx)
        rng = np.random.default_rng(seed)
        a0 = float(np.arctan2(H / 2 - sun_xy[1], W / 2 - sun_xy[0]))
        streak = np.zeros_like(X)
        for i in range(rays):
            ac = a0 + (rng.random() - 0.5) * angle_spread * 2
            wdt = 0.010 + rng.random() * 0.03
            streak += np.exp(-((ang - ac) / wdt) ** 2) * (0.4 + 0.6 * rng.random())
        out = out + ray_k * streak * np.exp(-r / (glow_r * 2.2)) * np.clip(r / 60.0, 0, 1)
    if horizon is not None and horizon_k > 0:
        out = out + horizon_k * np.exp(-((Y - horizon) / 18.0) ** 2)
    return out.astype(np.float32)


def pixel_soft(img, cell=12, sigma=1.3, bokeh_k=0.3, thr=0.88, dim=0.96, desat=0.10, bokeh_r=1.0):
    """v0.7 PIXEL-PRESERVING background softening (replaces the photographic `dof` in pixel shots):
    average the lit background onto a coarse screen grid of `cell` output px (use cell = round(4 * cam zoom) so one
    cell = one world pixel), gaussian-blur THAT grid (sigma in cells), grow blocky bokeh from the brightest cells,
    dim / desaturate a touch (depth), and upscale with NEAREST - the background stays made of crisp square pixels,
    just softer, so it never looks like a photo behind a pixel character.  img: output-res float RGB."""
    H, W = img.shape[:2]
    cell = max(2, int(cell))
    gw, gh = -(-W // cell), -(-H // cell)
    pw, ph = gw * cell - W, gh * cell - H
    src = np.pad(img, ((0, ph), (0, pw), (0, 0)), mode='edge') if (pw or ph) else img
    sm = cv2.resize(src, (gw, gh), interpolation=cv2.INTER_AREA)
    bl = cv2.GaussianBlur(sm, (0, 0), max(0.3, sigma))
    if bokeh_k > 0:
        lum = sm.max(-1)
        hi = np.clip((lum - thr) / (1 - thr + 1e-6), 0, 1)[..., None] * sm
        r = max(1, int(round(bokeh_r)))
        disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)).astype(np.float32)
        disc /= disc.sum() * 0.35
        bl = bl + bokeh_k * cv2.filter2D(hi, -1, disc)
    if desat > 0:
        g = bl.mean(-1, keepdims=True); bl = bl + (g - bl) * desat
    bl = bl * dim
    up = np.repeat(np.repeat(bl, cell, 0), cell, 1)[:H, :W]
    return np.ascontiguousarray(up.astype(img.dtype))
