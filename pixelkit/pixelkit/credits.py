"""pixelkit.credits - end credits where the character runs its own credits (v0.9, 第五幕片尾「Claude 制作」).

Picture model: a dark theatre void + one dithered pixel spotlight (480x270 grid, nearest x4), the pixel character and
pixel props/UI are lit by the spot; the credit TYPE is smooth serif at output resolution (like titles.TitleCard and the
reference end card), so the film's credits read as 'the film' and the pixel UI reads as 'Claude's own UI'.

    st = Stage()                                  # cx / floor_y / spot radius
    base = st.base(t, spot_k)                     # float RGB (270, 480, 3) void + spot + dust
    img  = st.compose(base, sprites, ui_rgba)     # sprites: [(rgba u8, E, x, y)] lit by the spot -> (1080, 1920, 3)
    Type(img).line('制作', 'sans', 26, 960, 330, alpha=a, tracking=0.5)
    rows(img, t, [(t_in, '导演', 'Claude')], y0, step)   # two-column credit rows with pop-in / shine
    head props: clapper(open) / pencil() / beret() / note() / steam_puffs(cv, ...); stats_card(...)
"""
import math, functools
import numpy as np, cv2
from .titles import text_mask, gold_fill, SERIF_CJK, SANS_SC
from .core import Canvas, C, text_width
from .anim import clamp01, ramp, ease_out3, ease_io, back_out
from . import ui

FONTS = {
    'serif': ('/usr/share/fonts/google-noto-cjk/NotoSerifCJK-Medium.ttc', 2),
    'serifb': SERIF_CJK,
    'it': ('/usr/share/fonts/msttcore/georgiai.ttf', 0),
    'itb': ('/usr/share/fonts/msttcore/georgiaz.ttf', 0),
    'sans': SANS_SC,
    'sansl': ('/usr/share/fonts/google-noto-cjk/NotoSansSC-Light.otf', 0),
}
CREAM_F = np.array([0.93, 0.89, 0.82], np.float32)
GREY_F = np.array([0.58, 0.54, 0.52], np.float32)
WARM_GLOW = np.array([0.95, 0.62, 0.30], np.float32)

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16.0


# ====================================================================== stage
class Stage:
    """black-box stage with one pixel spotlight (all in 480x270 world px)."""
    W, H = 480, 270

    def __init__(self, OW=1920, OH=1080, cx=240, floor_y=236, rx=78, ry=12, top_w=22, seed=3,
                 col=(1.0, 0.86, 0.64), void=('#0b0810', '#140d16')):
        self.OW, self.OH, self.cx, self.floor_y, self.rx, self.ry = OW, OH, cx, floor_y, rx, ry
        self.col = np.array(col, np.float32)
        H, W = self.H, self.W
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        top, bot = np.array(C(void[0])[:3], np.float32) / 255, np.array(C(void[1])[:3], np.float32) / 255
        v = (ys / H)[..., None]
        self.void = top * (1 - v) + bot * v
        vig = ((xs - W / 2) / (W * 0.62)) ** 2 + ((ys - H * 0.55) / (H * 0.75)) ** 2
        self.void *= np.clip(1.15 - 0.55 * vig, 0.45, 1.0)[..., None]
        # cone: from a narrow top to the floor ellipse
        u = np.clip(ys / floor_y, 0, 1)
        hw = top_w + (rx - top_w) * u
        edge = np.clip((hw - np.abs(xs - cx)) / 10.0, 0, 1)
        edge = edge * edge * (3 - 2 * edge)
        cone = edge * (0.28 + 0.72 * u ** 1.4) * (ys <= floor_y + 2)
        # floor pool
        d = ((xs - cx) / rx) ** 2 + ((ys - floor_y) / ry) ** 2
        pool = np.clip(1 - d, 0, 1) ** 0.65
        rim = np.exp(-((np.sqrt(d) - 1.0) / 0.08) ** 2) * (ys > floor_y - ry)
        self.cone, self.pool, self.rim = cone, pool, rim
        # stepped (dithered) light levels -> pixel bands, never smooth gradients
        def q(L, step):
            return np.floor(L / step + BAYER4[ys.astype(int) % 4, xs.astype(int) % 4]) * step
        self.Lcone = q(cone * 0.085, 0.017)
        self.Lpool = q(pool * 0.40 + rim * 0.06, 0.04)
        rng = np.random.default_rng(seed)
        n = 90
        self.dust = dict(x=rng.uniform(cx - rx, cx + rx, n), y=rng.uniform(10, floor_y - 4, n), ph=rng.uniform(0, 6.28, n),
                         w=rng.uniform(0.6, 1.6, n), vx=rng.uniform(-1.6, 1.6, n), vy=rng.uniform(-1.2, 0.6, n),
                         b=rng.uniform(0.35, 1.0, n))

    def spot_at(self, x, y=None):
        """0..1 how much of the spot a sprite standing at world x receives."""
        d = abs(x - self.cx) / self.rx
        return float(np.clip(1.25 - d, 0, 1) ** 1.5)

    def base(self, t, spot_k=1.0, dust_k=1.0):
        img = self.void.copy()
        if spot_k > 0:
            img += (self.Lcone * spot_k)[..., None] * self.col
            img += (self.Lpool * spot_k)[..., None] * self.col * np.array([1.0, 0.93, 0.85], np.float32)
        if dust_k * spot_k > 0.01:
            D = self.dust
            span = 2 * self.rx
            x = (D['x'] - (self.cx - self.rx) + D['vx'] * t) % span + self.cx - self.rx + 1.5 * np.sin(t * 0.4 + D['ph'])
            y = (D['y'] + D['vy'] * t + 2.0 * np.sin(t * 0.3 * D['w'] + D['ph']))
            y = (y - 10) % (self.floor_y - 14) + 10
            tw = 0.5 + 0.5 * np.sin(t * 2.2 * D['w'] + D['ph'])
            for i in range(len(x)):
                xi, yi = int(x[i]), int(y[i])
                if 0 <= xi < self.W and 0 <= yi < self.H:
                    c = self.cone[yi, xi]
                    if c > 0.05: img[yi, xi] += self.col * (0.18 * c * tw[i] * D['b'][i] * spot_k * dust_k)
        return img

    def contact_shadow(self, img, x, w=30, k=1.0):
        """soft dark ellipse on the floor under a character at world x (pixel stepped)."""
        y = self.floor_y
        for j in range(-2, 4):
            hw = int(round(w / 2 * math.sqrt(max(0.0, 1 - ((j - 0.5) / 3.6) ** 2))))
            a = 0.42 * k * (1 - abs(j - 0.5) / 4.0)
            x0, x1 = max(0, int(x - hw)), min(self.W, int(x + hw))
            if 0 <= y + j < self.H and x1 > x0: img[y + j, x0:x1] *= (1 - a)

    def compose(self, base, sprites=(), ui_rgba=None, spot_k=1.0, glow=0.55, shake=(0, 0), fg=None, emis0=None):
        """sprites: [(rgba u8, E float|None, x, y[, alpha])] in world px, lit by the spot (ambient 0.30 + spot) with a
        warm top light; fg: float RGBA (270, 480, 4) drawn over the sprites (e.g. the audience); ui_rgba: (270, 480, 4)
        u8 drawn unlit on top; emis0: extra float RGB emission for the glow (lamps).  -> float RGB (OH, OW, 3)."""
        img = base.copy()
        emis = np.zeros((self.H, self.W, 3), np.float32) if emis0 is None else emis0.copy()
        for spr in sprites:
            a8, E, x, y = spr[:4]; al = spr[4] if len(spr) > 4 else 1.0
            h, w = a8.shape[:2]
            x, y = int(round(x)), int(round(y))
            x0, y0, x1, y1 = max(0, x), max(0, y), min(self.W, x + w), min(self.H, y + h)
            if x1 <= x0 or y1 <= y0: continue
            s = a8[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32) / 255.0
            rgb, a = s[..., :3], s[..., 3:] * al
            L = 0.30 + 0.80 * spot_k * self.spot_at(x + w / 2)
            rows = np.linspace(1.08, 0.86, h, dtype=np.float32)[y0 - y:y1 - y, None, None]
            lit = rgb * L * rows * np.array([1.0, 0.96, 0.9], np.float32)
            if E is not None:
                e = E[y0 - y:y1 - y, x0 - x:x1 - x, None].astype(np.float32)
                lit = lit * (1 - e) + rgb * e * 1.05
                emis[y0:y1, x0:x1] += rgb * e * a
            img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + lit * a
        if fg is not None:
            img = img * (1 - fg[..., 3:]) + fg[..., :3] * fg[..., 3:]
            emis = emis * (1 - fg[..., 3:])                          # silhouettes block the glow behind them
        if ui_rgba is not None:
            u = ui_rgba.astype(np.float32) / 255.0
            img = img * (1 - u[..., 3:]) + u[..., :3] * u[..., 3:]
        big = cv2.resize(img, (self.OW, self.OH), interpolation=cv2.INTER_NEAREST)
        if glow > 0 and emis.max() > 0:
            eb = cv2.resize(emis, (self.OW // 4, self.OH // 4), interpolation=cv2.INTER_AREA)
            g = cv2.GaussianBlur(eb, (0, 0), 2.0) * 0.6 + cv2.GaussianBlur(eb, (0, 0), 6.0) * 0.5
            big += cv2.resize(g, (self.OW, self.OH), interpolation=cv2.INTER_LINEAR) * glow
        if shake != (0, 0):
            M = np.float32([[1, 0, shake[0]], [0, 1, shake[1]]])
            big = cv2.warpAffine(big, M, (self.OW, self.OH), borderMode=cv2.BORDER_REPLICATE)
        return big


# ====================================================================== v0.10: a warm little theatre
def _hexf(h): return np.array(C(h)[:3], np.float32) / 255.0

def _dq(L, levels, ys, xs):
    """pixel-art banding: quantize a 0..1 map to `levels` steps with a Bayer 4x4 dither."""
    return np.floor(np.clip(L, 0, 1) * levels + BAYER4[ys.astype(int) % 4, xs.astype(int) % 4]) / levels


class Theatre(Stage):
    """the Stage spotlight inside a warm little theatre (v0.10, 第五幕片尾 v3 - 'pure black was too cold'):
    red velvet back curtain (dithered folds), a scalloped valance with gold fringe, gathered side drapes with gold
    tie-backs, a wooden stage floor (perspective planks) with a gold lip, a row of footlights.
    Lighting = albedo x (house ambient + footlights + spot spill/pool) + the visible spot cone + dust.

        th = Theatre(floor_y=236)
        base = th.base(t, spot_k, house_k=1.0, foot_k=1.0)
        img = th.compose(base, sprites, ui, spot_k=sk, fg=th.audience(t, cues), emis0=th.foot_emis(foot_k))
    """

    def __init__(self, OW=1920, OH=1080, cx=240, floor_y=236, back_y=204, lip_y=249, seed=3, **kw):
        super().__init__(OW, OH, cx=cx, floor_y=floor_y, seed=seed, **kw)
        H, W = self.H, self.W
        self.back_y, self.lip_y = back_y, lip_y
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        rng = np.random.default_rng(seed + 11)
        alb = np.zeros((H, W, 3), np.float32)
        vel_d, vel_m, vel_l = _hexf('#120709'), _hexf('#3a1317'), _hexf('#6e2c2e')
        def velvet(f):                       # 0..1 fold light -> velvet colour (dark crease -> sheen)
            f = f[..., None]
            return np.where(f < 0.6, vel_d + (vel_m - vel_d) * (f / 0.6), vel_m + (vel_l - vel_m) * ((f - 0.6) / 0.4))
        # ---- back curtain: soft vertical folds (period ~15 px, wandering), darker toward the top
        ph = xs * (2 * math.pi / 31.0) + 1.3 * np.sin(xs / 61.0) + 0.5 * np.sin(xs / 23.0 + 1.3)
        f = 0.42 + 0.58 * (0.5 + 0.5 * np.sin(ph)) ** 1.6
        f = f * (0.42 + 0.58 * np.clip(ys / back_y, 0, 1) ** 1.1)
        # the credit type lives in the upper middle: keep the velvet quiet there (fewer, softer folds)
        quiet = np.exp(-((xs - cx) / 150.0) ** 2) * np.clip(1.0 - (ys - 40) / 150.0, 0, 1) * (ys > 20)
        f = f * (1.0 - 0.30 * quiet) + 0.12 * quiet * (0.5 - f)
        back = velvet(_dq(f, 6, ys, xs))
        hem = back_y - 1 + np.round(np.sin(xs / 7.0)).astype(np.float32)
        is_back = ys < hem
        alb[is_back] = back[is_back]
        # ---- floor: perspective planks, darker at the back (under the curtain), a gold lip, the dark apron
        fl = (ys >= hem) & (ys < lip_y)
        v = np.clip((ys - back_y) / (lip_y - back_y), 0, 1)
        pw = 11.0 + 5.0 * v                                           # plank width grows toward us
        pk = (xs - cx) / pw
        pid = np.floor(pk).astype(int)
        tone = (np.sin(pid * 12.9898) * 43758.5453) % 1.0             # per-plank tone
        wood = _hexf('#4a2c1c') * (1 - tone[..., None] * 0.25) + _hexf('#6e4630') * (tone[..., None] * 0.25)
        wood = wood * (0.55 + 0.45 * v[..., None])
        seam = (pk - pid) < (1.0 / pw)
        wood[seam] *= 0.55
        ends = ((np.floor(ys / 7.0 + tone * 3) % 4) == 0) & (((ys + 0) % 7) == 0)      # staggered plank ends
        wood[ends] *= 0.7
        alb[fl] = wood[fl]
        lip = (ys >= lip_y) & (ys < lip_y + 2)
        alb[lip] = np.where((ys[lip] == lip_y)[..., None], _hexf('#f0c870'), _hexf('#a8772e'))
        apron = ys >= lip_y + 2
        ap = _hexf('#2a1410') * (1.0 - 0.25 * ((xs % 40) < 1)[..., None])
        alb[apron] = ap[apron]
        # ---- side drapes (gathered at a gold tie-back), in front of everything behind the lip
        self.drape = np.zeros((H, W), bool)
        tie_y = 150
        for side in (-1, 1):
            def edge(y):                                               # drape width from the frame edge
                if y < tie_y: return 48 - 24 * math.sin(0.5 * math.pi * y / tie_y) ** 1.3
                return 24 + 22 * ((y - tie_y) / (lip_y - tie_y)) ** 0.8
            for y in range(0, lip_y):
                e = int(round(edge(y)))
                x0, x1 = (0, e) if side < 0 else (W - e, W)
                xx = np.arange(x0, x1, dtype=np.float32)
                d = (xx - x0) if side < 0 else (x1 - 1 - xx)           # distance from the frame edge
                ff = 0.5 + 0.5 * np.sin(d / max(e, 1) * 2 * math.pi * 3.2 + (0.6 if side > 0 else 0.0))
                ff = ff ** 1.3 * (0.55 + 0.45 * (d / max(e, 1)))      # inner edge catches the stage light
                q = np.floor(ff * 6 + BAYER4[y % 4, xx.astype(int) % 4]) / 6
                alb[y, x0:x1] = velvet(q[None, :])[0] * 1.08
                self.drape[y, x0:x1] = True
                if tie_y - 2 <= y <= tie_y + 1:                        # gold tie-back rope
                    alb[y, x0:x1] = _hexf('#e0b050') if y < tie_y else _hexf('#9a6a28')
            tx = (int(edge(tie_y)) - 3) if side < 0 else (W - int(edge(tie_y)) + 2)
            for k in range(8):                                         # tassel
                w_ = 1 if k < 3 else 2
                alb[tie_y + 2 + k, tx - w_ // 2: tx + w_ // 2 + 1] = _hexf('#d8a848') if k % 2 == 0 else _hexf('#b8862e')
        # ---- valance: five scalloped swags + gold fringe + a dark rod
        frac = (xs % 96) / 96.0
        vb = 12 + 9 * np.sin(math.pi * frac)
        val = ys < vb
        sw = 0.5 + 0.5 * np.cos(2 * math.pi * (ys / np.maximum(vb, 1)) * 2.0 + 0.4)
        sw = (sw ** 1.2) * (0.55 + 0.45 * np.sin(math.pi * frac))
        vcol = velvet(_dq(sw, 6, ys, xs)) * 1.12
        alb[val] = vcol[val]
        fr = (ys >= vb) & (ys < vb + 3)
        frc = np.where(((xs.astype(int) + (ys.astype(int))) % 2 == 0)[..., None], _hexf('#e8b85a'), _hexf('#8a5a20'))
        frc = np.where((ys < vb + 1)[..., None], _hexf('#f2cc70'), frc)
        alb[fr & ((ys < vb + 1) | (xs.astype(int) % 2 == 0))] = frc[fr & ((ys < vb + 1) | (xs.astype(int) % 2 == 0))]
        alb[0:2] = _hexf('#2a1a12'); alb[1, :] = _hexf('#6a4a26')
        self.alb = alb
        self.val_mask = val | fr
        # ---- light maps (quantized)
        dl = lip_y - ys
        foot = np.where(fl, np.exp(-np.clip(dl, 0, None) / 13.0), 0.0)
        foot = foot + np.where(is_back | self.drape, 0.55 * np.exp(-np.clip(back_y - ys, 0, None) / 55.0), 0.0)
        foot = foot + np.where(lip | apron, 0.25, 0.0)
        self.Lfoot = _dq(foot * 0.85, 8, ys, xs)
        sp = np.exp(-(((xs - cx) / 92.0) ** 2 + ((ys - (floor_y - 40)) / 70.0) ** 2) * 1.6) * (is_back | fl)
        self.Lspill = _dq(sp * 0.95, 8, ys, xs)
        self.Lpool_f = _dq(self.pool * 1.0 + self.rim * 0.12, 8, ys, xs) * fl
        self.vgrad = (0.80 + 0.20 * (ys / H))
        # footlight lamps (x positions) + their emission map
        self.lamps = [int(x) for x in np.arange(60, W - 50, 30)]
        self.lamp_emis = np.zeros((H, W, 3), np.float32)
        for x in self.lamps:
            self.lamp_emis[lip_y - 2, x - 1:x + 2] = _hexf('#ffd890') * 1.4
            self.lamp_emis[lip_y - 3, x] = _hexf('#fff0c0')
        self._fg_cache = {}

    def lamp_k(self, x, foot_k, t_on=None, t=None):
        return foot_k

    def base(self, t, spot_k=1.0, dust_k=1.0, house_k=1.0, foot_k=1.0, lamp_ks=None):
        warm = np.array([1.0, 0.78, 0.52], np.float32)
        L = (0.30 * house_k * self.vgrad)[..., None] * np.array([1.0, 0.9, 0.85], np.float32)
        L = L + (self.Lfoot * foot_k * 0.95)[..., None] * warm
        L = L + ((self.Lspill * 0.75 + self.Lpool_f * 1.5) * spot_k)[..., None] * self.col
        img = self.alb * L
        img += (self.Lcone * spot_k * 0.8)[..., None] * self.col * (~self.val_mask)[..., None]
        # footlight hoods + bulbs
        for i, x in enumerate(self.lamps):
            lk = foot_k if lamp_ks is None else lamp_ks[i]
            img[self.lip_y - 1, x - 3:x + 4] = _hexf('#1a1210')
            img[self.lip_y - 2, x - 2:x + 3] = _hexf('#2a2018')
            img[self.lip_y - 2, x - 1:x + 2] = _hexf('#ffd890') * (0.12 + 1.0 * lk)
        if dust_k * spot_k > 0.01:
            D = self.dust
            span = 2 * self.rx
            x = (D['x'] - (self.cx - self.rx) + D['vx'] * t) % span + self.cx - self.rx + 1.5 * np.sin(t * 0.4 + D['ph'])
            y = (D['y'] + D['vy'] * t + 2.0 * np.sin(t * 0.3 * D['w'] + D['ph']))
            y = (y - 10) % (self.floor_y - 14) + 10
            tw = 0.5 + 0.5 * np.sin(t * 2.2 * D['w'] + D['ph'])
            for i in range(len(x)):
                xi, yi = int(x[i]), int(y[i])
                if 0 <= xi < self.W and 0 <= yi < self.H:
                    c = self.cone[yi, xi]
                    if c > 0.05: img[yi, xi] += self.col * (0.22 * c * tw[i] * D['b'][i] * spot_k * dust_k)
        return img

    def foot_emis(self, foot_k, lamp_ks=None):
        return self.lamp_emis * foot_k

    def contact_shadow(self, img, x, w=30, k=1.0):
        super().contact_shadow(img, x, w, k * 1.15)

    # ------------------------------------------------------------------ the front row (backlit silhouettes)
    def audience(self, t, people, light=1.0, seat_y=252, pitch=46, x0=34, sc=1.9, base_y=266):
        """float RGBA (H, W, 4) foreground: a row of velvet seat backs + people seen from behind as silhouettes with a
        warm rim from the stage.  people: [dict(kind='hat'|'messy'|'card', x, dx, dy, clap=None|phase, clap_dx, clap_dy,
        card='鱼')]   (dx/dy move the head only; clap_dx/clap_dy place the hands relative to the head, in sc units)
        sc scales the people (they sit close to the camera); the seat backs hide everything below seat_y."""
        H, W = self.H, self.W
        cvp = Canvas(W, H)
        WH = (255, 255, 255, 255)
        def ell(cx, cy, rx, ry): cvp.ellipse(int(round(cx)), int(round(cy)), max(1, int(round(rx))), max(1, int(round(ry))), WH)
        def rect(x, y, w, h): cvp.rect(int(round(x)), int(round(y)), max(1, int(round(w))), max(1, int(round(h))), WH)
        self._heads = []
        for p in people:
            if p['kind'] not in ('hat', 'messy'): continue
            x, dx, dy = p['x'], p.get('dx', 0), p.get('dy', 0)
            hx, hy = x + dx, base_y - 36 * sc + dy                     # head centre
            ell(x, hy + 23.5 * sc, 20 * sc, 12.5 * sc)                    # shoulders (the seat back hides the rest)
            rect(hx - 4 * sc, hy + 4 * sc, 8 * sc, 10 * sc)              # neck
            ell(hx, hy, 8 * sc, 9.2 * sc)                                # head
            ell(hx - 8.2 * sc, hy + 0.5 * sc, 1.4 * sc, 2.4 * sc); ell(hx + 8.2 * sc, hy + 0.5 * sc, 1.4 * sc, 2.4 * sc)  # ears
            if p['kind'] == 'hat':
                ell(hx, hy - 5.5 * sc, 16.5 * sc, 2.6 * sc)              # wide straw brim
                cw0, cw1 = 7.2 * sc, 6.0 * sc                            # crown, slightly tapered, dented top
                for i in range(int(round(9 * sc))):
                    w_ = cw0 + (cw1 - cw0) * i / (9 * sc)
                    yy_ = hy - 6.5 * sc - i
                    rect(hx - w_, yy_, 2 * w_ + 1, 1)
                ytop = hy - 6.5 * sc - 9 * sc
                rect(hx - 2.2 * sc, ytop - 0.5, 4.4 * sc, 1)             # (overwritten below to make the dent)
            else:                                                        # messy hair: a full mop + uneven pointed locks
                ell(hx, hy - 1.6 * sc, 9.0 * sc, 8.6 * sc)
                for (deg, ln, wd) in ((-170, 2.0, 6), (-148, 3.0, 7), (-122, 2.2, 7), (-100, 3.6, 6), (-80, 1.6, 6),
                                      (-60, 2.8, 7), (-36, 3.2, 6), (-12, 1.8, 6), (10, 1.2, 5)):
                    th_ = math.radians(deg); n_ = (math.cos(th_), math.sin(th_)); tg = (-n_[1], n_[0])
                    r0 = 8.2
                    bx_, by_ = hx + n_[0] * r0 * sc, hy - 1.6 * sc + n_[1] * r0 * sc
                    bend = 0.6 * ln                                     # locks curl slightly clockwise
                    tip = (bx_ + (n_[0] * ln + tg[0] * bend) * sc, by_ + (n_[1] * ln + tg[1] * bend) * sc)
                    cvp.poly([(bx_ - tg[0] * wd / 2 * sc, by_ - tg[1] * wd / 2 * sc), tip,
                              (bx_ + tg[0] * wd / 2 * sc, by_ + tg[1] * wd / 2 * sc)], WH)
            if p.get('clap') is not None:                                # hands up, clapping
                c = p['clap']; sep = (1.2 + 3.2 * abs(math.sin(c * math.pi))) * sc
                cxh = hx + p.get('clap_dx', 0) * sc; cyh = hy + p.get('clap_dy', -12) * sc
                for sgn in (-1, 1):
                    ell(cxh + sgn * sep, cyh, 2.8 * sc, 3.6 * sc)
                    rect(cxh + sgn * sep - 1.3 * sc, cyh + 2 * sc, 2.6 * sc, 9 * sc)   # forearms
            self._heads.append((p, hx, hy))
        if any(p['kind'] == 'hat' for p in people):                      # carve the crown's dent
            for (p, hx, hy) in self._heads:
                if p['kind'] == 'hat':
                    yt = int(round(hy - 6.5 * sc - 9 * sc)) + 1
                    cvp.a[yt - 1:yt + 1, int(round(hx - 2 * sc)):int(round(hx + 2 * sc)) + 1, 3] = 0
        a_people = cvp.a[..., 3].astype(np.float32) / 255.0
        # seats
        cvs = Canvas(W, H)
        for i in range(-1, int((W - x0) / pitch) + 2):
            sx = x0 + i * pitch
            cvs.rrect(int(sx - pitch / 2 + 3), seat_y, int(pitch - 6), H - seat_y + 6, WH, r=8)
        a_seats = cvs.a[..., 3].astype(np.float32) / 255.0
        out = np.zeros((H, W, 4), np.float32)
        warm = np.array([1.0, 0.80, 0.55], np.float32)
        yy = np.mgrid[0:H, 0:W][0]
        # people first: near-black warm silhouettes, a 1-px rim on the top edges + the head's sides
        sil = _hexf('#0d070a')
        pm = cvp.a[..., 3] > 127
        out[pm, :3] = sil; out[pm, 3] = 1.0
        up = pm & ~np.roll(pm, 1, 0)
        side = pm & (~np.roll(pm, 1, 1) | ~np.roll(pm, -1, 1))
        neck_y = base_y - 36 * sc + 4 * sc
        xx_ = np.mgrid[0:H, 0:W][1]
        near_head = np.zeros((H, W), bool)
        for (p, hx, hy) in self._heads:
            near_head |= np.abs(xx_ - hx) < 11 * sc
        rim = up | (side & (yy < neck_y) & near_head)
        out[rim, :3] = warm * (0.22 + 0.50 * light)
        hot = up & np.roll(up, 1, 1) & np.roll(up, -1, 1)
        out[hot, :3] = warm * (0.34 + 0.70 * light)
        for (p, hx, hy) in self._heads:
            hx_, hy_ = int(round(hx)), int(round(hy))
            if p['kind'] == 'messy':                                     # glasses temples catch the light over the ears
                for sgn in (-1, 1):
                    xe = hx_ + sgn * int(round(8.2 * sc))
                    xa, xb = (xe - 1, xe + 2) if sgn > 0 else (xe - 1, xe + 2)
                    out[hy_ - 1, xa:xb, :3] = _hexf('#e0d8cc') * (0.45 + 0.55 * light)
                    out[hy_, (xb - 1 if sgn > 0 else xa), :3] = _hexf('#a09890') * (0.45 + 0.55 * light)
            if p['kind'] == 'hat':                                       # straw: lit brim + crown edges, dark hat band
                ybr = int(round(hy - 5.5 * sc - 2.6 * sc))
                for yb in (ybr, ybr + 1):
                    row = pm[yb, :] & ~pm[yb - 1, :]
                    out[yb, row, :3] = _hexf('#e8c47a') * (0.35 + 0.65 * light)
                yband = int(round(hy - 7.6 * sc))
                bw = int(round(7.0 * sc))
                out[yband:yband + 2, hx_ - bw + 1:hx_ + bw, :3] = _hexf('#4a1c14') * (0.6 + 0.5 * light)
                # a few straw-weave glints on the brim
                for gx in range(-14, 15, 4):
                    xg = hx_ + int(round(gx * sc * 0.95))
                    if pm[ybr + 2, xg]: out[ybr + 2, xg, :3] = _hexf('#b08a4a') * (0.3 + 0.6 * light)
        # seat backs in FRONT of the people (we sit one row behind them)
        seat_col = _hexf('#2a0a10') * (0.55 + 0.6 * light)
        sm = a_seats > 0.5
        out[sm, :3] = seat_col; out[sm, 3] = 1.0
        top = sm & ~np.roll(sm, 1, 0)
        top2 = sm & ~np.roll(sm, 2, 0) & ~top
        out[top, :3] = _hexf('#a8424a') * (0.45 + 0.6 * light); out[top2, :3] = _hexf('#5a1a20') * (0.55 + 0.6 * light)
        # thin dark gap between seat backs and the people behind (contact shade)
        sh = (~sm) & np.roll(sm, -1, 0) & pm
        out[sh, :3] *= 0.6
        # reserved-seat cards
        for p in people:
            if p['kind'] != 'card': continue
            x = p['x']; cw, ch = 16, 14
            cvc = Canvas(cw, ch)
            cvc.rect(0, 0, cw, ch, C('#efe6d4')); cvc.hline(0, ch - 1, cw, C('#b8ab94')); cvc.vline(cw - 1, 0, ch, C('#cfc2aa'))
            cvc.text(3, 1, p.get('card', '鱼'), C('#3a2a2a'), 'zh10')
            c = cvc.a.astype(np.float32) / 255.0
            k = 0.40 + 0.6 * light
            y0, x0_ = seat_y + 3, x - cw // 2
            out[y0:y0 + ch, x0_:x0_ + cw, :3] = c[..., :3] * k
            out[y0:y0 + ch, x0_:x0_ + cw, 3] = 1.0
        return out


# ====================================================================== smooth credit type
@functools.lru_cache(maxsize=256)
def _mask(text, font, px, tracking=0.0):
    return text_mask(text, FONTS[font], px, tracking)

@functools.lru_cache(maxsize=256)
def _gold(text, font, px, tracking=0.0):
    return gold_fill(_mask(text, font, px, tracking))

def text_w(text, font, px, tracking=0.0):
    return _mask(text, font, px, tracking).shape[1] - 8

def _over(img, rgb, a, x, y):
    H, W = img.shape[:2]; h, w = a.shape
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    aa = a[y0 - y:y1 - y, x0 - x:x1 - x, None]
    src = rgb[y0 - y:y1 - y, x0 - x:x1 - x] if rgb.ndim == 3 and rgb.shape[0] == h else rgb
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - aa) + src * aa

def line(img, text, font, px, x, y, align='c', col=CREAM_F, alpha=1.0, gold=False, glow=0.0, tracking=0.0,
         shine=None, outline=0.0):
    """one smooth text line at output px; (x, y) = anchor (align 'c' centre / 'l' left edge / 'r' right edge), y = top.
    shine: 0..1 a diagonal light sweep across the line (gold names on pop-in)."""
    if alpha <= 0.003 or not text: return 0
    m = _mask(text, font, px, tracking)
    h, w = m.shape
    xx = int(round(x - w / 2)) if align == 'c' else (int(round(x)) - 4 if align == 'l' else int(round(x - w)) + 4)
    yy = int(round(y)) - 4
    a = m * alpha
    if glow > 0:
        P = int(px * 0.6) + 4
        ap = cv2.copyMakeBorder(a, P, P, P, P, cv2.BORDER_CONSTANT, value=0)
        g = cv2.GaussianBlur(ap, (0, 0), max(2.0, px * 0.18)) * glow
        H, W = img.shape[:2]; gx, gy = xx - P, yy - P; gh, gw = g.shape
        x0, y0, x1, y1 = max(0, gx), max(0, gy), min(W, gx + gw), min(H, gy + gh)
        if x1 > x0 and y1 > y0: img[y0:y1, x0:x1] += g[y0 - gy:y1 - gy, x0 - gx:x1 - gx, None] * WARM_GLOW * 0.5
    if outline > 0:
        k = max(1, int(px * 0.06))
        o = cv2.GaussianBlur(cv2.dilate(m, np.ones((2 * k + 1, 2 * k + 1), np.uint8)), (0, 0), 1.0) * alpha * outline
        _over(img, np.zeros((h, w, 3), np.float32) + np.array([0.08, 0.05, 0.03], np.float32), o, xx, yy)
    if gold:
        rgb = _gold(text, font, px, tracking).copy()
        if shine is not None and 0 <= shine <= 1:
            xs = np.arange(w, dtype=np.float32)[None, :]; ys = np.arange(h, dtype=np.float32)[:, None]
            c = shine * (w + h) - h
            band = np.exp(-((xs + ys * 0.5 - c) / max(8.0, px * 0.45)) ** 2)
            rgb = np.minimum(1.0, rgb + band[..., None] * np.array([0.6, 0.55, 0.4], np.float32))
    else:
        rgb = np.broadcast_to(np.asarray(col, np.float32), (h, w, 3))
    _over(img, rgb, a, xx, yy)
    return w - 8


def pop(t, t0, t1=None, d_in=0.38, d_out=0.35, rise=14, sink=10):
    """(alpha, dy) for a credit element: rises into place (ease out) at t0, floats up + fades at t1."""
    if t < t0: return 0.0, rise
    u = clamp01((t - t0) / d_in)
    a, dy = ease_io(u), rise * (1 - ease_out3(u))
    if t1 is not None and t > t1:
        v = clamp01((t - t1) / d_out)
        a *= 1 - ease_io(v); dy -= sink * ease_io(v)
    return a, dy


def credit_row(img, t, t0, role, name, y, t1=None, cx=960, gap=34, role_px=34, name_px=40, role_font='serif',
               name_font='it', name_gold=True, dots=True, name_col=CREAM_F):
    """two-column row 'role  ·  name' centred on the gutter cx; name in gold italic with a shine on pop-in."""
    a, dy = pop(t, t0, t1)
    if a <= 0: return
    line(img, role, role_font, role_px, cx - gap, y + dy + (name_px - role_px) * 0.55, 'r', col=CREAM_F * 0.92, alpha=a)
    if dots:
        for i in range(3):
            xx, yy = int(cx - 9 + i * 9), int(y + dy + name_px * 0.62)
            img[yy:yy + 3, xx:xx + 3] = img[yy:yy + 3, xx:xx + 3] * (1 - 0.6 * a) + GREY_F * 0.6 * a
    sh = (t - t0 - 0.12) / 0.55
    line(img, name, name_font, name_px, cx + gap, y + dy, 'l', col=name_col, alpha=a, gold=name_gold, glow=0.35 * a if name_gold else 0,
         shine=sh if 0 <= sh <= 1 else None)


# ====================================================================== pixel props (world px, drawn with Canvas)
def clapper(open_k=0.0):
    """film slate 21x19: dark board with chalk lines + a striped clap stick hinged at the left,
    open_k 0 (shut) .. 1 (open ~28 deg)."""
    cv = Canvas(22, 20)
    INK, WH, GR, BD = C('#1c1a24'), C('#f2efe8'), C('#8a8896'), C('#34323e')
    cv.rect(1, 7, 20, 12, INK); cv.rect(2, 8, 18, 10, BD)
    cv.hline(4, 11, 7, WH); cv.hline(4, 14, 12, GR); cv.hline(4, 16, 9, GR); cv.px(14, 11, GR); cv.px(16, 11, GR)
    ang = math.radians(-28 * open_k)
    for i in range(21):
        for j in range(4):
            x = 1 + i * math.cos(ang) - (j - 3) * math.sin(ang); y = 6 + i * math.sin(ang) + (j - 3) * math.cos(ang)
            stripe = ((i // 4) % 2 == 0)
            cv.px(int(round(x)), int(round(y)), WH if stripe and 0 < j < 3 else INK)
    return cv.a

def pencil():
    """yellow pencil 13x5 lying at ~-20 deg: pink eraser + metal ferrule on the left, sharpened tip on the right."""
    cv = Canvas(14, 6)
    cols = [C('#f0a0b0'), C('#f0a0b0'), C('#c8c8d0'), C('#ffd040'), C('#ffd040'), C('#ffd040'), C('#ffd040'), C('#ffd040'),
            C('#ffd040'), C('#f2d2a0'), C('#f2d2a0'), C('#3a3040')]
    for i, c in enumerate(cols):
        y = 4 - int(i * 0.36)
        cv.px(i + 1, y, c); cv.px(i + 1, y - 1, c if i < 9 else (C('#e8c890') if i < 11 else c))
        if 3 <= i < 9: cv.px(i + 1, y, C('#d8a020'))
    return cv.a

def beret():
    """artist's beret 22x9 (deep red, soft highlight, the little stalk on top), tilted to the right."""
    cv = Canvas(24, 10)
    R0, R1, R2, OUT = C('#7a1f2e'), C('#b8323a'), C('#e05a5a'), C('#3a1420')
    cv.ellipse(12, 6, 11, 3.6, OUT); cv.ellipse(12, 5.6, 10, 3.0, R1)
    cv.ellipse(10, 4.6, 6, 1.6, R2); cv.hline(3, 8, 18, R0)
    cv.rect(13, 1, 2, 2, OUT); cv.px(13, 1, R1)
    return cv.a

NOTE = ["..##", "..#.", "..#.", "###.", "###."]
def note(col='#ffe6a8'):
    cv = Canvas(5, 6)
    for y, r in enumerate(NOTE):
        for x, ch in enumerate(r):
            if ch == '#': cv.px(x, y, C(col))
    return cv.a

def steam_puffs(cv, x, y, t, t0, t1, rate=7.0, col=(236, 230, 222), life=0.9, seed=0):
    """little pixel steam puffs rising from (x, y) between t0 and t1 (an overheating head)."""
    if t < t0: return
    n = int((min(t, t1) - t0) * rate) + 1
    rng = np.random.default_rng(seed)
    offs = rng.uniform(-10, 10, 200); drift = rng.uniform(-6, 6, 200)
    for k in range(min(n, 200)):
        ts = t0 + k / rate
        age = (t - ts) / life
        if 0 <= age < 1:
            r = 1.2 + 2.6 * age
            a = int(200 * (1 - age) ** 1.2)
            cv.ellipse(x + offs[k] + drift[k] * age, y - 16 * age, r, r * 0.85, (col[0], col[1], col[2], a))

def combo(cv, x, y, n, age, label='COMBO', col=None, alpha=1.0):
    """game-style 'COMBO xN' badge (right-aligned at x), bumps on every increment (age = since the last one)."""
    if alpha <= 0: return
    col = col or ui.GOLD
    s = 2 if age < 0.12 else 1
    txt = f'x{n}'
    ui.big_text(cv, int(x - text_width(txt, 'p2p') * s), int(y - (s - 1) * 4), txt, col, 'p2p', s, shadow=C('#3b3042'), alpha=alpha)
    cv.text(int(x - text_width(txt, 'p2p') * s - text_width(label, 'silkb') - 3), int(y + 1), label, ui._a(ui.CREAM, 0.85 * alpha), 'silkb')


# ====================================================================== the 'film stats' card (same look as ui.optimizer_card)
def stats_card(t, rows, rows_k, big='+83%', big_label='效率可提高', big_k=0.0, title='本片数据', title_en='STATS', w=156,
               crack=0.0, seed=0):
    """dark HUD card listing [(label, value)] rows (each slides in by rows_k) + an optional big gold number."""
    RH = 15
    h = 25 + len(rows) * RH + (32 if big_k > 0 else 0) + 3
    cv = Canvas(w, h)
    cv.rrect(0, 0, w, h, ui.CYAN_D, 3); cv.rrect(1, 1, w - 2, h - 2, ui.HUD_BG, 3)
    for yy in range(3, h - 3, 3): cv.hline(3, yy, w - 6, (40, 60, 90, 60))
    cv.text(6, 3, title, ui.CREAM, 'zh10')
    cv.text(6 + text_width(title, 'zh10') + 4, 6, title_en, ui.CYAN, 'silkb')
    sp = int(t * 10) % 8
    for i in range(8):
        a_ = 2 * math.pi * i / 8
        cv.px(int(round(w - 10 + 3 * math.cos(a_))), int(round(9 + 3 * math.sin(a_))), ui.CYAN if (sp - i) % 8 < 3 else ui.CYAN_D)
    cv.hline(4, 20, w - 8, ui.CYAN_D)
    y = 24
    for (lab, val), k in zip(rows, list(rows_k) + [0] * len(rows)):
        if k > 0:
            al = min(1.0, k * 2.5); x0 = 6 - int(round(8 * (1 - ui.ease_out(min(1.0, k * 2.0)))))
            cv.text(x0, y + 1, lab, ui._a(ui.CREAM, al), 'zh8')
            n = int(round(len(val) * min(1.0, k * 1.4)))
            cv.text(52, y + 1, val[:n], ui._a(ui.CYAN, al), 'zh8')
        y += RH
    if big_k > 0:
        cv.hline(4, y + 1, w - 8, ui.CYAN_D)
        cv.text(6, y + 10, big_label, ui.CREAM, 'zh10')
        k = back_out(min(1.0, big_k), 2.2)
        m = text_mask_px(big)
        s = 2
        bg_ = np.repeat(np.repeat(m, s, 0), s, 1)
        g = Canvas(bg_.shape[1] + 2, bg_.shape[0] + 2)
        g._mask(bg_, 2, 2, (0, 0, 0, 255)); g._mask(bg_, 0, 0, ui.GOLD)
        ui.blit_scaled(cv, g.a, w - 10 - bg_.shape[1] // 2, y + 17, k)
    if crack > 0:
        rng = np.random.default_rng(seed + 5)
        cx_, cy_ = w * 0.72, h - 16
        for n_ in range(7):
            ang = rng.uniform(0, 2 * math.pi); L_ = (25 + 60 * rng.random()) * crack
            x_, y_ = cx_, cy_
            for st in range(int(L_)):
                ang += rng.uniform(-0.35, 0.35); x_ += math.cos(ang); y_ += math.sin(ang)
                if 0 <= x_ < w and 0 <= y_ < h: cv.px(int(x_), int(y_), ui.CREAM)
    return cv.a

def text_mask_px(s, fname='p2p'):
    from .core import text_mask as tm
    m = tm(s, fname)
    rows = np.nonzero(m.any(1))[0]
    return m[rows[0]:rows[-1] + 1]


# ====================================================================== v0.9 little extras for the credits performance
def twinkles(cv, x, y, t, t0, n=5, life=0.55, spread=16, col=None, seed=0):
    """a small burst of 4-point pixel twinkles around (x, y) at t0 (star eyes, heart eyes, a proud moment)."""
    age = t - t0
    if age < 0 or age > life + 0.25: return
    col = col or ui.GOLD
    rng = np.random.default_rng(seed)
    for i in range(n):
        d = rng.uniform(0, 0.22); u = (age - d) / life
        if not 0 <= u < 1: continue
        ang = rng.uniform(0, 2 * math.pi); r = spread * (0.45 + 0.55 * rng.random()) * (0.4 + 0.6 * ease_out3(u))
        px, py = int(round(x + r * math.cos(ang))), int(round(y + r * math.sin(ang) * 0.8 - 3 * u))
        s = 2 if u < 0.5 else 1
        a = 1 - u
        c = ui._a(col, a)
        cv.px(px, py, ui._a(ui.CREAM, a))
        for k in range(1, s + 1):
            cv.px(px - k, py, c); cv.px(px + k, py, c); cv.px(px, py - k, c); cv.px(px, py + k, c)

def headset_spr():
    """the headset on its own (14x9) - for when it flies off."""
    cv = Canvas(15, 10)
    from .characters.claude import HS, HS_HI, HS_MIC
    for i in range(13):
        ang = math.pi * (1 - i / 12)
        x, y = 7 + 6 * math.cos(ang), 6 - 5 * math.sin(ang)
        cv.px(int(round(x)), int(round(y)), HS); cv.px(int(round(x)), int(round(y)) + 1, HS)
    cv.rect(0, 5, 3, 4, HS); cv.rect(12, 5, 3, 4, HS); cv.px(1, 6, HS_HI); cv.px(13, 6, HS_HI)
    cv.px(3, 9, HS_MIC); cv.px(4, 9, HS_MIC)
    return cv.a

def mini_card(text, fname='zh10', col=None, w=None):
    """small dark HUD tag (e.g. '鱼获：0') as an RGBA sprite."""
    tw = text_width(text, fname); W_ = w or tw + 14; H_ = 17
    cv = Canvas(W_ + 2, H_ + 2)
    cv.rrect(1, 2, W_, H_, (0, 0, 0, 110), 3)
    cv.rrect(0, 0, W_, H_, ui.CYAN_D, 3); cv.rrect(1, 1, W_ - 2, H_ - 2, ui.HUD_BG, 3)
    cv.text(7, 2, text, col or ui.CREAM, fname)
    return cv.a
