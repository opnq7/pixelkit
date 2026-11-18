"""pixelkit.titles - reference-style title cards (smooth gold serif on a dark brush band, over black).

    tc = TitleCard('Claude 想请一天假', 'Claude Wants a Day Off', '第一幕 · 没有周末    ACT I · NO WEEKENDS')
    img = tc.frame(t, dur=4.2)           # t = seconds since the card started; float RGB (1080, 1920, 3)

Timing (seconds from the card start): brush band wipes in 0-0.55, title wipe-reveal with gold glints 0.25-1.25,
subtitle 1.05-1.65, small line 1.45-2.0, a shine sweep ~1.7, then the letters dissolve into gold dust
left -> right during the last `out` seconds (like the reference 'CLAUDE DREAMING' card).
Unlike the pixel UI, title cards are drawn smooth at output resolution (as in the reference).
"""
import math, functools
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

SERIF_CJK = ('/usr/share/fonts/google-noto-cjk/NotoSerifCJK-Bold.ttc', 2)      # index 2 = SC
SERIF_IT = ('/usr/share/fonts/msttcore/georgiaz.ttf', 0)                       # Georgia Bold Italic
SANS_SC = ('/usr/share/fonts/google-noto-cjk/NotoSansSC-Medium.otf', 0)

def _font(spec, size):
    from . import fonts          # cross-platform: bundled -> Linux path -> Windows fonts
    return fonts.truetype(spec, size)

def text_mask(text, spec, size, tracking=0.0):
    """anti-aliased float mask (h, w) of a single text line; tracking in em."""
    f = _font(spec, size)
    if tracking == 0:
        l, t, r, b = f.getbbox(text)
        im = Image.new('L', (r - l + 8, b - t + 8), 0)
        ImageDraw.Draw(im).text((4 - l, 4 - t), text, font=f, fill=255)
        return np.asarray(im, np.float32) / 255.0
    parts = [text_mask(ch, spec, size) if ch != ' ' else np.zeros((4, int(size * 0.3)), np.float32) for ch in text]
    asc = f.getbbox('Hg国')
    H = asc[3] - asc[1] + 10
    W = sum(p.shape[1] for p in parts) + int(size * tracking) * (len(parts) - 1) + 8
    out = np.zeros((H, W), np.float32); x = 4
    for ch, p in zip(text, parts):
        if ch != ' ':
            l, t, r, b = f.getbbox(ch)
            y = max(0, t - asc[1] + 1)
            h = min(p.shape[0], H - y); out[y:y + h, x:x + p.shape[1]] = np.maximum(out[y:y + h, x:x + p.shape[1]], p[:h])
        x += p.shape[1] + int(size * tracking)
    return out

def _noise1d(n, scale, seed, octaves=3):
    rng = np.random.default_rng(seed); out = np.zeros(n, np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        k = max(2, int(n / scale) + 2)
        v = rng.uniform(-1, 1, k).astype(np.float32)
        out += amp * np.interp(np.linspace(0, k - 1, n), np.arange(k), v); tot += amp
        scale /= 2.2; amp *= 0.5
    return out / tot

@functools.lru_cache(maxsize=4)
def brush_band(w, h, seed=1, col=(0.115, 0.085, 0.105), streak=(0.255, 0.19, 0.215)):
    """dark dry-brush stroke (RGBA float, (h + pad, w + pad)) with ragged bristle ends and horizontal streaks."""
    pad = 40; H, W = h + 2 * pad, w + 2 * pad
    ys = np.arange(H, dtype=np.float32)[:, None]; xs = np.arange(W, dtype=np.float32)[None, :]
    top = pad + h * 0.06 * _noise1d(W, 260, seed)[None, :] + 6 * _noise1d(W, 40, seed + 1)[None, :]
    bot = pad + h + h * 0.07 * _noise1d(W, 300, seed + 2)[None, :] + 6 * _noise1d(W, 50, seed + 3)[None, :]
    # bristle ends: every row ends at its own x
    l_end = pad + 30 + 34 * _noise1d(H, 6, seed + 4)[:, None] + 26 * np.abs(_noise1d(H, 30, seed + 5))[:, None]
    r_end = W - pad - 30 - 40 * _noise1d(H, 5, seed + 6)[:, None] - 30 * np.abs(_noise1d(H, 24, seed + 7))[:, None]
    ss = lambda e0, e1, x: np.clip((x - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((x - e0) / (e1 - e0), 0, 1))
    m = ss(top - 3, top + 5, ys) * (1 - ss(bot - 5, bot + 3, ys)) * ss(l_end - 14, l_end + 10, xs) * (1 - ss(r_end - 10, r_end + 14, xs))
    rng = np.random.default_rng(seed + 9)
    rows = rng.uniform(0, 1, H).astype(np.float32)
    rows = cv2.GaussianBlur(rows[:, None], (0, 0), 1.2)[:, 0]
    tex = np.zeros((H, W), np.float32)
    for o, sc in enumerate((900, 300, 90)):
        k = int(W / sc) + 3
        g = rng.uniform(0, 1, (H, k)).astype(np.float32)
        g = cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)
        tex += g * (0.5 ** o)
    tex = tex / 1.75
    tex = cv2.GaussianBlur(tex, (0, 0), sigmaX=6, sigmaY=0.6)
    s = np.clip(0.55 * tex + 0.45 * rows[:, None], 0, 1)
    gaps = (cv2.GaussianBlur(rng.uniform(0, 1, (H, W // 8)).astype(np.float32), (0, 0), sigmaX=0.1, sigmaY=1.0))
    gaps = cv2.resize(gaps, (W, H), interpolation=cv2.INTER_LINEAR)
    m = m * np.clip(1.25 - 0.6 * (gaps > 0.72) * (1 - ss(top + 14, top + 30, ys) * (1 - ss(bot - 30, bot - 14, ys))), 0, 1)
    c0, c1 = np.array(col, np.float32), np.array(streak, np.float32)
    rgb = c0[None, None, :] * (1 - s[..., None]) + c1[None, None, :] * s[..., None]
    a = np.clip(m * (0.82 + 0.25 * s), 0, 1)
    return np.dstack([rgb, a]).astype(np.float32)

GOLD_TOP, GOLD_MID, GOLD_BOT = np.array([1.0, 0.94, 0.74]), np.array([0.93, 0.78, 0.47]), np.array([0.73, 0.53, 0.25])

def gold_fill(mask):
    """vertical gold gradient (+ a darker lower lip) for a text mask -> RGB."""
    h = mask.shape[0]
    rows = np.where(mask.max(axis=1) > 0.2)[0]
    y0, y1 = (rows[0], rows[-1]) if len(rows) else (0, h - 1)
    u = np.clip((np.arange(h, dtype=np.float32) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    top = GOLD_TOP * (1 - np.clip(u / 0.45, 0, 1)) + GOLD_MID * np.clip(u / 0.45, 0, 1)
    bot = GOLD_MID * (1 - np.clip((u - 0.45) / 0.55, 0, 1)) + GOLD_BOT * np.clip((u - 0.45) / 0.55, 0, 1)
    g = np.where(u < 0.45, top, bot).astype(np.float32)
    return np.broadcast_to(g, mask.shape + (3,)).copy()

class TitleCard:
    def __init__(self, title, sub='', small='', OW=1920, OH=1080, title_px=118, sub_px=46, small_px=27, y=0.43, seed=1,
                 band_w=None, band_h=None):
        self.OW, self.OH, self.seed = OW, OH, seed
        s = OW / 1920
        self.tm = text_mask(title, SERIF_CJK, int(title_px * s))
        self.sm = text_mask(sub, SERIF_IT, int(sub_px * s)) if sub else None
        self.km = text_mask(small, SANS_SC, int(small_px * s), tracking=0.18) if small else None
        th, tw = self.tm.shape
        self.tx, self.ty = (OW - tw) // 2, int(OH * y - th / 2)
        bw = band_w or int(tw + 300 * s); bh = band_h or int(th * 1.55)
        self.band = brush_band(bw, bh, seed)
        self.bx, self.by = (OW - self.band.shape[1]) // 2, int(OH * y - self.band.shape[0] / 2 + 4 * s)
        self.trgb = gold_fill(self.tm)
        k = max(1, int(3 * s))
        dil = cv2.dilate(self.tm, np.ones((2 * k + 1, 2 * k + 1), np.uint8))
        self.tout = cv2.GaussianBlur(dil, (0, 0), 1.2 * s)
        self.sy = self.by + self.band.shape[0] - int(22 * s)
        if self.sm is not None: self.sx = (OW - self.sm.shape[1]) // 2; self.srgb = gold_fill(self.sm) * 0.98
        if self.km is not None:
            self.kx = (OW - self.km.shape[1]) // 2
            self.ky = self.sy + (self.sm.shape[0] if self.sm is not None else 0) + int(26 * s)
        rng = np.random.default_rng(seed + 5)
        ys, xs = np.nonzero(self.tm > 0.5)
        pick = rng.choice(len(xs), min(len(xs), 2600), replace=False)
        self.px, self.py = xs[pick].astype(np.float32) + self.tx, ys[pick].astype(np.float32) + self.ty
        n = len(pick)
        self.pv = np.stack([rng.uniform(40, 190, n), -rng.uniform(25, 140, n)], 1).astype(np.float32) * s
        self.plife = rng.uniform(0.55, 1.1, n).astype(np.float32); self.psz = rng.uniform(1.2, 3.2, n).astype(np.float32) * s
        self.ppink = rng.uniform(0, 1, n).astype(np.float32); self.pph = rng.uniform(0, 6.28, n).astype(np.float32)
        self.glints = [(float(rng.uniform(0, 1)), float(rng.uniform(0.1, 0.9)), float(rng.uniform(0.6, 1.0))) for _ in range(18)]

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _over(img, rgb, a, x, y):
        H, W = img.shape[:2]; h, w = a.shape
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0: return
        aa = a[y0 - y:y1 - y, x0 - x:x1 - x, None]
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - aa) + rgb[y0 - y:y1 - y, x0 - x:x1 - x] * aa

    @staticmethod
    def _wipe(w, front, soft):
        """per-column visibility 1 left of the front, soft edge (front in px)."""
        xs = np.arange(w, dtype=np.float32)
        return np.clip((front - xs) / max(1.0, soft), 0, 1)

    def _glint(self, img, x, y, r, k):
        if k <= 0: return
        s = self.OW / 1920; r = int(max(3, r * s))
        x, y = int(x), int(y)
        H, W = img.shape[:2]
        for dx in range(-r, r + 1):
            f = (1 - abs(dx) / (r + 1)) ** 2 * k
            for (xx, yy) in ((x + dx, y), (x, y + dx)):
                if 0 <= xx < W and 0 <= yy < H: img[yy, xx] = np.minimum(1.0, img[yy, xx] + np.array([1.0, 0.92, 0.7]) * f)

    # ------------------------------------------------------------------ frame
    def frame(self, t, dur=4.2, out=1.0, fade_out=0.25):
        OW, OH = self.OW, self.OH; s = OW / 1920
        img = np.zeros((OH, OW, 3), np.float32)
        # band: wipe in from the left
        bh, bw = self.band.shape[:2]
        u = np.clip(t / 0.55, 0, 1); ue = 1 - (1 - u) ** 3
        bvis = self._wipe(bw, ue * bw * 1.15, 160 * s)[None, :]
        t_d = dur - out                                        # dissolve start
        bfade = 1.0 - np.clip((t - (dur - 0.6)) / 0.5, 0, 1)
        self._over(img, self.band[..., :3], self.band[..., 3] * bvis * bfade, self.bx, self.by)
        # title: wipe reveal, later dissolve
        th, tw = self.tm.shape
        rv = np.clip((t - 0.25) / 1.0, 0, 1); rv = rv * rv * (3 - 2 * rv)
        front = rv * (tw + 120 * s) - 60 * s
        vis = self._wipe(tw, front, 60 * s)[None, :]
        dfront = None
        if t >= t_d:
            dk = np.clip((t - t_d) / (out * 0.85), 0, 1)
            dfront = -40 * s + dk * (tw + 80 * s)
            xs = np.arange(tw, dtype=np.float32)
            jitter = (np.sin(np.arange(th)[:, None] * 0.37 + xs[None, :] * 0.05) * 18 * s)
            vis = vis * np.clip((xs[None, :] + jitter - dfront) / (26 * s), 0, 1)
        a = self.tm * vis
        # warm glow + dark outline + gold fill + shine
        glow = cv2.GaussianBlur(a, (0, 0), 9 * s) * 0.55
        img[self.ty:self.ty + th, self.tx:self.tx + tw] += glow[..., None] * np.array([0.95, 0.62, 0.30], np.float32) * 0.6
        self._over(img, np.zeros((th, tw, 3), np.float32) + np.array([0.10, 0.06, 0.03], np.float32), self.tout * vis * 0.85,
                   self.tx, self.ty)
        rgb = self.trgb.copy()
        sh = (t - 1.75) / 0.8
        if 0 <= sh <= 1:
            xs = np.arange(tw, dtype=np.float32)[None, :]; ys = np.arange(th, dtype=np.float32)[:, None]
            c = sh * (tw + th) - th
            band = np.exp(-((xs + ys * 0.5 - c) / (38 * s)) ** 2)
            rgb = np.minimum(1.0, rgb + band[..., None] * np.array([0.55, 0.5, 0.35], np.float32))
        self._over(img, rgb, a, self.tx, self.ty)
        # reveal glints along the wipe front
        if 0.25 < t < 1.45:
            for (gx, gy, gk) in self.glints:
                xg = self.tx + front - 30 * s + gx * 60 * s; yg = self.ty + th * gy
                ph = math.sin((t * 9 + gx * 17) % 6.283)
                self._glint(img, xg, yg, 9 + 9 * gk, max(0.0, ph) * gk * (1 - np.clip((t - 1.2) / 0.25, 0, 1)))
        # subtitle + small line
        for (m, rgb_, x, y, t0, d) in ([(self.sm, self.srgb, self.sx, self.sy, 1.05, 0.6)] if self.sm is not None else []) + \
                                       ([(self.km, None, self.kx, self.ky, 1.45, 0.55)] if self.km is not None else []):
            k = np.clip((t - t0) / d, 0, 1); k = k * k * (3 - 2 * k)
            k *= 1.0 - np.clip((t - (t_d + 0.15)) / 0.45, 0, 1)
            if k <= 0: continue
            col = rgb_ if rgb_ is not None else np.zeros(m.shape + (3,), np.float32) + np.array([0.80, 0.70, 0.52], np.float32)
            self._over(img, col, m * k * (0.92 if rgb_ is None else 1.0), x, y + int(round(8 * s * (1 - k))))
        # dissolve dust
        if dfront is not None:
            act = self.px - self.tx < dfront + 30 * s
            if act.any():
                tx0 = t_d + np.clip((self.px[act] - self.tx + 40 * s) / (tw + 80 * s), 0, 1) * out * 0.85
                age = t - tx0; ok = (age >= 0) & (age < self.plife[act])
                idx = np.nonzero(act)[0][ok]; ag = age[ok]
                if len(idx):
                    uu = ag / self.plife[idx]
                    x = self.px[idx] + self.pv[idx, 0] * ag + 14 * s * np.sin(ag * 5 + self.pph[idx])
                    y = self.py[idx] + self.pv[idx, 1] * ag - 30 * s * ag * ag
                    col = (np.array([1.0, 0.86, 0.55])[None, :] * (1 - self.ppink[idx, None]) +
                           np.array([1.0, 0.62, 0.62])[None, :] * self.ppink[idx, None]) * ((1 - uu) ** 1.3)[:, None]
                    acc = np.zeros((OH, OW, 3), np.float32)
                    xi = np.clip(np.round(x).astype(int), 0, OW - 1); yi = np.clip(np.round(y).astype(int), 0, OH - 1)
                    np.add.at(acc, (yi, xi), col * 2.2)
                    acc = cv2.GaussianBlur(acc, (0, 0), 1.6 * s) * 6.0 + cv2.GaussianBlur(acc, (0, 0), 6 * s) * 2.5
                    img += acc
        g = np.clip(1.0 - np.clip((t - (dur - fade_out)) / fade_out, 0, 1), 0, 1)
        img *= g
        rng = np.random.default_rng(int(t * 30) + 7)
        img += (rng.standard_normal((OH // 2, OW // 2)).astype(np.float32) * 0.012).repeat(2, 0).repeat(2, 1)[..., None]
        return np.clip(img, 0, 1)
