"""pixelkit.painterly - pixel art -> oil painting (stroke-based, temporally stable) + the ripple transition.

Why strokes and not a filter: a Kuwahara / "oil paint" filter re-decides every brush mark every frame (it shimmers)
and looks like a photo app.  Here the brush marks are generated ONCE from a reference frame and stored in WORLD
coordinates; every frame only their colours are re-sampled from the live pixel render.  So the sun can keep sinking,
the camera can pull out, the water can glitter - and the strokes stay put (they only 'breathe' by a pixel or two).

    P = Painter(ref_img, ref_cam, focus=[(x0, y0, x1, y1), ...])     # once (≈2-4 s at 1080p); focus = world boxes
    img = P.paint(src_img, cam, t)                                   # per frame (≈0.4 s at 1080p)
    soft = soften(src_img)                                           # the halfway state: pixels melted, not yet paint
    M = ripple_mask(cam, r, origin=(x, y), ...)                      # 0..1 per output pixel, blocky dissolve front
    out = blend3(pixel, soft, paint, M_soft, M_paint)

Layers (coarse -> fine, Hertzmann-style): big horizontal sky / water strokes, mid strokes following the image
structure, small strokes only where detail is (edges, faces) or inside `focus` boxes so the characters stay readable.
Each stroke = a main band + two thinner bristle tracks of slightly different value + an impasto height that is
embossed under a light from the upper left; a faint linen weave sits on top.
"""
import math
import numpy as np, cv2

# ------------------------------------------------------------------ colour treatment of the paint
def paint_grade(img, warm=0.03, lift=0.025, sat=1.06, contrast=0.97):
    """oil paint never goes pitch black: lift shadows toward violet, warm the lights, a bit more chroma."""
    l = img.mean(-1, keepdims=True)
    out = l + (img - l) * sat
    out = 0.42 + (out - 0.42) * contrast
    out = out + lift * (1 - np.clip(l * 2.2, 0, 1)) * np.array([0.8, 0.55, 1.0], np.float32)
    out = out + warm * np.clip(l * 1.5 - 0.3, 0, 1) * np.array([1.0, 0.45, -0.35], np.float32)
    return np.clip(out, 0, 1.5).astype(np.float32)

def _blur_small(img, sigma, f=4):
    """gaussian blur at 1/f resolution, back to full size (cheap wide blurs)."""
    H, W = img.shape[:2]
    s = cv2.resize(img, (W // f, H // f), interpolation=cv2.INTER_AREA)
    if sigma / f > 0.3: s = cv2.GaussianBlur(s, (0, 0), sigma / f)
    return cv2.resize(s, (W, H), interpolation=cv2.INTER_LINEAR)

def soften(img, sigma=5.0, glow=0.35):
    """the melted halfway look: pixel edges gone, light blooms, colours run together."""
    b = cv2.GaussianBlur(img, (0, 0), sigma)
    g = _blur_small(np.clip(img - 0.65, 0, None), 30.0)
    return np.clip(b + g * glow, 0, 1.6).astype(np.float32)


class Painter:
    """stroke-based oil paint, built once from a reference frame (all geometry lives in the reference framing).

    Brush marks are tapered, slightly curved flat strokes that follow the image structure (horizontal in sky and
    water), laid coarse -> fine; fine strokes only where there is detail or inside `focus` boxes (characters).
    Geometry, the impasto height map and the bristle streaks are computed ONCE; per frame only the stroke colours
    are re-sampled from the live pixel render -> the painting can change (sunset, glitter) without crawling."""
    LAYERS = (  # r = half width (px at the reference framing), length in r, density (strokes per r^2 area), detail thr
        dict(r=13.0, length=(4.0, 8.0), density=1.0, thr=None, curve=0.35),
        dict(r=7.5, length=(3.0, 6.0), density=0.8, thr=0.020, curve=0.6),
        dict(r=4.0, length=(2.5, 4.5), density=0.65, thr=0.030, curve=0.8),
    )

    def __init__(self, ref, focus=None, seed=7, layers=None, flat_wobble=0.10, jitter=1.0, length_map=None, width_map=None, focus_mix=0.5,
                 jitter_map=None, break_map=None):
        """focus: (H, W) float mask (e.g. the characters' alpha, dilated) -> smaller strokes + some of the soft source
        shows through so silhouettes stay readable.  length_map: (H, W) stroke-length multiplier (sky long, water short)."""
        H, W = ref.shape[:2]
        self.H, self.W = H, W
        self.layers = layers or self.LAYERS
        rng = np.random.default_rng(seed)
        ref = paint_grade(ref)
        lum = ref @ np.array([0.3, 0.55, 0.15], np.float32)
        from .materials import fbm
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        wob = ((fbm(xx, yy, 160.0, 3, seed + 1) - 0.5) * 2 * flat_wobble).astype(np.float32)
        self.focus = np.zeros((H, W), np.float32) if focus is None else focus.astype(np.float32)
        self.focus_mix = focus_mix
        lmap = np.ones((H, W), np.float32) if length_map is None else length_map
        wmap = np.ones((H, W), np.float32) if width_map is None else width_map
        jmap = np.ones((H, W), np.float32) if jitter_map is None else jitter_map.astype(np.float32)
        bmap = np.full((H, W), 0.085, np.float32) if break_map is None else break_map.astype(np.float32)
        hmap = np.zeros((H, W), np.float32)
        self.L = []
        prev = None
        for Ly in self.layers:
            R = Ly['r']
            B = cv2.GaussianBlur(ref, (0, 0), max(0.8, R * 0.45))
            Bs = cv2.GaussianBlur(ref, (0, 0), R * 1.1)
            Lb = cv2.GaussianBlur(lum, (0, 0), max(1.0, R * 0.6))
            gx = cv2.Sobel(Lb, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Lb, cv2.CV_32F, 0, 1, ksize=3)
            sig = R * 1.5
            Jxx = cv2.GaussianBlur(gx * gx, (0, 0), sig); Jyy = cv2.GaussianBlur(gy * gy, (0, 0), sig); Jxy = cv2.GaussianBlur(gx * gy, (0, 0), sig)
            ang = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy) + np.pi / 2
            lam = np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2)
            coh = np.clip(lam / (Jxx + Jyy + 1e-7), 0, 1) * np.clip(np.sqrt(Jxx + Jyy) * 80, 0, 1)
            n = int(H * W / (R * R) * Ly['density'] / 4)
            xs = rng.uniform(0, W, n); ys = rng.uniform(0, H, n)
            xi, yi = xs.astype(int), ys.astype(int)
            if Ly.get('focus_only'):
                keep = rng.random(n) < self.focus[yi, xi] * 1.3
            elif Ly['thr'] is not None and prev is not None:
                err = np.abs(B - prev).mean(-1)
                err = cv2.blur(err, (int(R * 2) | 1, int(R * 2) | 1))
                keep = (err[yi, xi] > Ly['thr']) | (rng.random(n) < self.focus[yi, xi])
            else:
                keep = np.ones(n, bool)
            xs, ys = xs[keep], ys[keep]
            polys, cxs, cys, jms = [], [], [], []
            for x, y in zip(xs, ys):
                ix, iy = int(x), int(y)
                c0 = Bs[iy, ix]; brk = bmap[iy, ix]
                ln = rng.uniform(*Ly['length']) * R * (1 - 0.5 * self.focus[iy, ix]) * lmap[iy, ix]
                step = max(1.5, R * 0.7); nseg = max(1, int(ln / step / 2))
                pts = {1: [], -1: []}
                for d in (1, -1):
                    px, py, pa = x, y, None
                    for k in range(nseg):
                        jy, jx = int(min(max(py, 0), H - 1)), int(min(max(px, 0), W - 1))
                        a = ang[jy, jx]; ch = coh[jy, jx] ** 0.7 * Ly['curve']
                        dx_, dy_ = math.cos(a), math.sin(a)
                        if dx_ < 0: dx_, dy_ = -dx_, -dy_
                        hw_ = wob[jy, jx]
                        dx_, dy_ = dx_ * ch + math.cos(hw_) * (1 - ch), dy_ * ch + math.sin(hw_) * (1 - ch)
                        nn = math.hypot(dx_, dy_) + 1e-6; dx_, dy_ = dx_ / nn, dy_ / nn
                        if pa is not None and dx_ * pa[0] + dy_ * pa[1] < 0: dx_, dy_ = -dx_, -dy_
                        nx, ny = px + d * dx_ * step, py + d * dy_ * step
                        if not (0 <= nx < W and 0 <= ny < H): break
                        if np.abs(Bs[int(ny), int(nx)] - c0).mean() > brk: break
                        pts[d].append((nx, ny)); px, py, pa = nx, ny, (dx_, dy_)
                cl = pts[-1][::-1] + [(x, y)] + pts[1]
                if len(cl) < 2:
                    a = ang[iy, ix]; cl = [(x - math.cos(a) * R * 0.8, y - math.sin(a) * R * 0.8), (x + math.cos(a) * R * 0.8, y + math.sin(a) * R * 0.8)]
                P = np.array(cl, np.float32)
                # tapered flat brush: full width in the middle, pointed-ish ends, a little uneven
                m = len(P)
                tang = np.gradient(P, axis=0); tang /= (np.linalg.norm(tang, axis=1, keepdims=True) + 1e-6)
                nrm = np.stack([-tang[:, 1], tang[:, 0]], -1)
                u = np.linspace(0, 1, m)
                wprof = R * wmap[iy, ix] * (0.45 + 0.55 * np.sin(np.pi * np.clip(u * 0.85 + 0.075, 0, 1)) ** 0.6) * rng.uniform(0.8, 1.15)
                head = P[0] - tang[0] * R * 0.9; tail = P[-1] + tang[-1] * R * 1.3
                left = P + nrm * wprof[:, None]; right = P - nrm * wprof[:, None] * rng.uniform(0.85, 1.0)
                poly = np.concatenate([[head], left, [tail], right[::-1]], 0)
                polys.append(np.round(poly * 4).astype(np.int32))
                cxs.append(x); cys.append(y); jms.append(jmap[iy, ix])
                cv2.fillPoly(hmap, [polys[-1]], float(rng.uniform(0.2, 1.0)), cv2.LINE_AA, shift=2)
            nS = len(polys); jm = np.array(jms, np.float32).reshape(-1, 1) if nS else np.zeros((0, 1), np.float32)
            self.L.append(dict(r=R, polys=polys, cx=np.clip(np.array(cxs), 0, W - 1).astype(int), cy=np.clip(np.array(cys), 0, H - 1).astype(int),
                               jit=((rng.normal(0, 1, (nS, 3)) * np.array([0.035, 0.030, 0.040]) * jitter + rng.normal(0, 0.045 * jitter, (nS, 1))) * jm).astype(np.float32),
                               ph=rng.uniform(0, 2 * np.pi, nS).astype(np.float32)))
            prev = B
        self.count = sum(len(l['polys']) for l in self.L)
        # bristle streaks: fine grain smeared along the (coarse) flow
        self.fx, self.fy = np.cos(ang).astype(np.float32), np.sin(ang).astype(np.float32)
        grain = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.9)
        st = self._lic(grain, 10.0, 6); self.streak = st / (st.std() + 1e-6)
        hgt = cv2.GaussianBlur(hmap, (0, 0), 1.6) + 0.12 * self.streak
        gxh = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3); gyh = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3)
        self.shade = np.clip(-(gxh * 0.6 + gyh * 0.8), -2.0, 2.0).astype(np.float32)
        self.weave = self._weave()

    def _lic(self, tex, length, steps):
        H, W = tex.shape
        Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
        fx = np.where(self.fx < 0, -self.fx, self.fx); fy = np.where(self.fx < 0, -self.fy, self.fy)
        acc = tex.copy(); ws = 1.0; st = length / steps
        for d in (1, -1):
            px, py = X.copy(), Y.copy()
            for k in range(steps):
                px += d * cv2.remap(fx, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) * st
                py += d * cv2.remap(fy, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) * st
                w = 1.0 - (k + 1) / (steps + 1)
                acc += w * cv2.remap(tex, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT); ws += w
        return acc / ws

    def _weave(self):
        H, W = self.H, self.W
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        p = 3.2
        w = 0.5 * np.sin(xx * 2 * np.pi / p) * np.sin(yy * 2 * np.pi / p * 1.07)
        n = np.random.default_rng(3).normal(0, 1, (H // 2 + 1, W // 2 + 1)).astype(np.float32)
        n = cv2.resize(cv2.GaussianBlur(n, (0, 0), 0.8), (W, H))[:H, :W]
        return (w * 0.6 + n * 0.4).astype(np.float32)

    def paint(self, src, t=0.0, impasto=0.07, streaks=0.035, weave=0.03, breathe=0.25, grade=True):
        """src: float RGB frame in the reference framing.  returns the painted frame (same size)."""
        if grade: src = paint_grade(src)
        canvas = np.ascontiguousarray(_blur_small(src, self.L[0]['r'] * 1.2))
        for Ly in self.L:
            B = _blur_small(src, Ly['r'] * 0.45, f=2 if Ly['r'] < 6 else 4) if Ly['r'] > 3 else cv2.GaussianBlur(src, (0, 0), 1.2)
            k = 1 + breathe * np.sin(t * 0.9 + Ly['ph'])[:, None]
            col = B[Ly['cy'], Ly['cx']] * (1 + Ly['jit'] * k) + Ly['jit'] * k * 0.12
            for poly, c in zip(Ly['polys'], col):
                cv2.fillPoly(canvas, [poly], (float(c[0]), float(c[1]), float(c[2])), cv2.LINE_AA, shift=2)
        img = canvas
        if self.focus.any():
            fo = self.focus[..., None] * self.focus_mix
            img = img * (1 - fo) + cv2.GaussianBlur(src, (0, 0), 2.2) * fo
        calm = (1 - 0.85 * np.clip(self.focus, 0, 1))[..., None]      # no bristle/impasto rings on the characters' faces
        img = img * (1 + streaks * self.streak[..., None] * calm)
        img = img * (1 + impasto * self.shade[..., None] * calm) + np.clip(self.shade, 0, None)[..., None] * impasto * 0.08
        img = img * (1 + weave * self.weave[..., None])
        return np.clip(img, 0, 1.6).astype(np.float32)


def zoom_matrix(z, cx, cy):
    """2x3 affine of a zoom by z that keeps output point (cx, cy) in place."""
    return np.float32([[z, 0, cx - cx * z], [0, z, cy - cy * z]])

def zoom_view(img, z, cx, cy):
    """digital push-in on an already rendered (painted) frame: zoom z >= 1 with output point (cx, cy) held fixed."""
    H, W = img.shape[:2]
    M = zoom_matrix(z, cx, cy)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ------------------------------------------------------------------ the ripple transition
def ripple_mask(cam, r, origin, aspect=0.42, band=10.0, block=2, wobble=10.0, seed=5, OW=1920, OH=1080, f_native=4):
    """-> (OH, OW) float 0..1: 1 inside the ripple front (painted), 0 outside (pixels).  The front is a flattened
    ellipse of radius r (world px) around `origin`, wobbled by noise and resolved BLOCK BY BLOCK (block = world px)
    with an ordered dither inside `band`, so the pixels flip one by one instead of a soft wipe."""
    x0, y0, x1, y1 = cam.view()
    bw = block
    nx = int(math.ceil((x1 - x0) / bw)) + 2; ny = int(math.ceil((y1 - y0) / bw)) + 2
    gx0 = math.floor(x0 / bw) * bw; gy0 = math.floor(y0 / bw) * bw
    X = gx0 + (np.arange(nx) + 0.5) * bw; Y = gy0 + (np.arange(ny) + 0.5) * bw
    XX, YY = np.meshgrid(X, Y)
    from .materials import fbm
    from .core import BAYER4
    d = np.sqrt((XX - origin[0]) ** 2 + ((YY - origin[1]) / aspect) ** 2)
    d = d + wobble * (fbm(XX, YY, 26.0, 3, seed) - 0.5) * 2
    u = np.clip((r - d) / band, 0, 1)
    ii = (np.floor(XX / bw).astype(int)) % 4; jj = (np.floor(YY / bw).astype(int)) % 4
    m = (u > BAYER4[jj, ii]).astype(np.float32)
    # block grid -> output pixels (nearest: crisp blocks)
    s = cam.s
    M = np.float32([[s * bw, 0, (gx0 - cam.cx) * s + OW / 2 + cam.sx], [0, s * bw, (gy0 - cam.cy) * s + OH / 2 + cam.sy]])
    out = cv2.warpAffine(m, M, (OW, OH), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
    return out

def ring_glow(cam, r, origin, aspect=0.42, width=2.5, wobble=10.0, seed=5, OW=1920, OH=1080):
    """soft bright ring riding on the ripple front (add to the frame, x colour)."""
    from .materials import fbm
    ys, xs = np.mgrid[0:OH // 4, 0:OW // 4].astype(np.float32)
    WX, WY = cam.o2w(xs * 4 + 2, ys * 4 + 2)
    d = np.sqrt((WX - origin[0]) ** 2 + ((WY - origin[1]) / aspect) ** 2)
    d = d + wobble * (fbm(WX, WY, 26.0, 3, seed) - 0.5) * 2
    g = np.exp(-((d - r) / width) ** 2).astype(np.float32)
    return cv2.resize(g, (OW, OH), interpolation=cv2.INTER_LINEAR)
