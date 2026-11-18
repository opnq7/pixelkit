"""pixelkit.sets.inserts - close-up insert shots (flat, 480x270 native), rendered with scene.FlatScene so
they share the camera warp / grade / grain of the room shots and can be match-cut into them.

    ck = ClockInsert(tod='sunset')                     # the office wall clock, filling the frame
    cam = Cam(1.06, 240, 135)
    img = ck.frame(cam, hh=17, mm=59, ss=57.0, frame=i, ui=ui_rgba)

Second-hand ticks: ClockInsert.tick_angle(ss_float) gives a quartz tick with a tiny overshoot.
"""
import math, functools
import numpy as np, cv2
from ..core import Canvas, C, mix, text_width, BAYER4
from ..materials import plaster, apply_ramp, fbm
from ..palette import ramp
from ..scene import FlatScene
from ..light import TOD
from .. import post
from ..ui import big_text

INK = C('#2a2433'); INK_HI = C('#4a4258'); RED = C('#d8453a'); RED_D = C('#8f2a24')


def _poly(cv, pts, col):
    m = np.zeros((cv.h, cv.w), np.uint8)
    cv2.fillPoly(m, [np.round(np.array(pts)).astype(np.int32)], 1, lineType=cv2.LINE_8)
    cv.a[m > 0] = col
    return m > 0


def hand(cv, cx, cy, ang, length, width, col, tail=0.0):
    """tapered clock hand polygon (angle 0 = 12 o'clock, clockwise)."""
    ux, uy = math.sin(ang), -math.cos(ang); vx, vy = -uy, ux; hw = width / 2
    p = [(cx - ux * tail + vx * hw, cy - uy * tail + vy * hw), (cx + ux * length + vx * hw * 0.55, cy + uy * length + vy * hw * 0.55),
         (cx + ux * (length + hw), cy + uy * (length + hw)),
         (cx + ux * length - vx * hw * 0.55, cy + uy * length - vy * hw * 0.55), (cx - ux * tail - vx * hw, cy - uy * tail - vy * hw)]
    return _poly(cv, p, col)


class ClockInsert:
    CX, CY, R = 240, 134, 100

    def __init__(self, tod='sunset', wall='#dcc1a6', brand='ALWAYS ON', OW=1920, OH=1080, seed=3):
        self.tod, self.wall, self.brand, self.seed = tod, wall, brand, seed
        self.fs = FlatScene(OW=OW, OH=OH)
        self.static, self.face_mask, self.body_mask = self._static()
        self.L = self._light()
        self.grade = dict(post.GRADES['golden_hd2d'])

    # ------------------------------------------------------------------ art
    def _static(self):
        W, H = 480, 270
        cv = Canvas(W, H)
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
        rp = ramp(self.wall, 6)
        t = plaster(xs * 0.75, ys * 0.75, base=3.0, seed=self.seed, mottle=0.3)
        cv.a[..., :3] = apply_ramp(t, rp, xs.astype(int), ys.astype(int))[..., :3]
        cv.a[..., 3] = 255
        for x in (36, 444):                                      # wall panel seams
            cv.vline(x, 0, H, mix(rp[2], rp[3], 0.5)); cv.vline(x + 1, 0, H, mix(rp[3], rp[4], 0.6))
        cx, cy, R = self.CX, self.CY, self.R
        # rim (dark bezel with a lit top-left edge) + face
        cv.ellipse(cx, cy, R + 9, R + 9, C('#1f1a28'))
        cv.ellipse(cx - 1, cy - 1, R + 7.5, R + 7.5, C('#6a6078'))
        cv.ellipse(cx + 1, cy + 1, R + 7.0, R + 7.0, C('#3a3346'))
        cv.ellipse(cx, cy, R + 2.5, R + 2.5, C('#1f1a28'))
        face, face_d, face_l = C('#f5f0e6'), C('#e4dac8'), C('#fffaf2')
        cv.ellipse(cx, cy, R, R, face)
        r = np.sqrt((xs + 0.5 - cx) ** 2 + (ys + 0.5 - cy) ** 2) / R
        th = BAYER4[ys.astype(int) % 4, xs.astype(int) % 4]
        tf = np.clip((r - 0.70) / 0.30, 0, 1)
        cv.a[(tf > th) & (r < 1.0)] = face_d
        hl = np.sqrt((xs + 0.5 - (cx - R * 0.3)) ** 2 + (ys + 0.5 - (cy - R * 0.3)) ** 2) / (R * 0.55)
        cv.a[(hl < 1) & (np.clip(1 - hl, 0, 1) * 0.9 > th) & (r < 0.95)] = face_l
        face_mask = r < 1.0
        for k in range(60):                                      # minute + hour ticks
            a = k / 60 * 2 * math.pi
            if k % 5 == 0:
                hand(cv, cx + math.sin(a) * (R - 15), cy - math.cos(a) * (R - 15), a, 9, 4.5, INK)
            else:
                x = cx + math.sin(a) * (R - 8); y = cy - math.cos(a) * (R - 8)
                cv.rect(int(round(x - 1)), int(round(y - 1)), 2, 2, INK)
        for n in range(1, 13):                                   # numerals
            a = n / 12 * 2 * math.pi; s = str(n)
            tw = text_width(s, 'p2p') * 2
            x = cx + math.sin(a) * (R - 33) - tw / 2; y = cy - math.cos(a) * (R - 33) - 8
            big_text(cv, int(round(x)), int(round(y)), s, INK, 'p2p', 2)
        # brand split either side of the hub (hands never hide it for long)
        words = self.brand.split(' ', 1) if ' ' in self.brand else [self.brand, '']
        lw = text_width(words[0], 'silkb')
        cv.text(cx - 14 - lw, cy - 4, words[0], C('#a0968a'), 'silkb')
        if words[1]:
            cv.text(cx + 15, cy - 4, words[1], C('#a0968a'), 'silkb')
        body = np.sqrt((xs + 0.5 - cx) ** 2 + (ys + 0.5 - cy) ** 2) < R + 9
        return cv.a.copy(), face_mask, body

    def _light(self):
        fs = self.fs; t = TOD[self.tod]
        sun_col = np.asarray(t['sun'][1], np.float32) * t['sun'][2] * 0.75
        amb_col = np.asarray(t['amb'][0], np.float32) * t['amb'][1] * 1.25
        L = fs.ambient(amb_col, 1.0, top=1.05, bottom=0.8)
        if t['sun'][2] > 0:
            L = L + fs.blinds(sun_col, 1.0, angle=-0.30, period=21.0, open_=0.58, soft=0.10, x0=0, y0=8,
                              region=(170, 120, 330, 210), fade_x=(40, 520))
            L = L + fs.pool(110, 70, 260, 170, sun_col, 0.22)
        L = fs.shadow(L, self.body_mask, 9, 12, k=0.55, soft=4.0)
        # corners darker (vignette is in the grade; this is the wall's own falloff)
        return L.astype(np.float32)

    # ------------------------------------------------------------------ animation helpers
    @staticmethod
    def tick_angle(ss, tick_dur=0.09, overshoot=0.35):
        """second-hand angle (radians) for a quartz tick at every whole second (ss float seconds)."""
        whole = math.floor(ss); u = ss - whole
        if u < tick_dur:
            k = u / tick_dur; s = 1.70158 * overshoot * 3
            k = 1 + (s + 1) * (k - 1) ** 3 + s * (k - 1) ** 2      # back-out
            pos = whole - 1 + k
        else:
            pos = whole
        return pos / 60 * 2 * math.pi

    def hands(self, cv, hh, mm, ss_angle, min_angle=None):
        cx, cy, R = self.CX, self.CY, self.R
        ah = ((hh % 12) + mm / 60) / 12 * 2 * math.pi
        am = (mm / 60) * 2 * math.pi if min_angle is None else min_angle
        sh = C('#cbbfaa')
        hand(cv, cx + 3, cy + 4, ah, R * 0.50, 9, sh, tail=10)
        hand(cv, cx + 3, cy + 4, am, R * 0.78, 7, sh, tail=12)
        hand(cv, cx + 4, cy + 5, ss_angle, R * 0.86, 3, sh, tail=26)
        hand(cv, cx, cy, ah, R * 0.50, 9, INK, tail=10)
        hand(cv, cx, cy, am, R * 0.78, 7, INK, tail=12)
        hand(cv, cx - 0.6, cy - 0.6, am, R * 0.74, 2, INK_HI, tail=8)
        hand(cv, cx, cy, ss_angle, R * 0.86, 3, RED, tail=26)
        ux, uy = math.sin(ss_angle), -math.cos(ss_angle)
        cv.ellipse(cx - ux * 22, cy - uy * 22, 5, 5, RED)
        cv.ellipse(cx - ux * 22 - 1, cy - uy * 22 - 1, 2, 2, C('#f07a6a'))
        cv.ellipse(cx, cy, 7, 7, INK); cv.ellipse(cx, cy, 3.5, 3.5, RED); cv.px(cx - 1, cy - 1, C('#f8a090'))

    def glare(self, cv):
        cx, cy, R = self.CX, self.CY, self.R
        for k in range(30):
            a = math.radians(-160 + k * 2.6)
            x = cx + math.cos(a) * (R - 16); y = cy + math.sin(a) * (R - 16)
            cv.blend_rect(int(x), int(y), int(x) + 3, int(y) + 2, (255, 255, 255, 64))
        for k in range(10):
            a = math.radians(-140 + k * 3.0)
            x = cx + math.cos(a) * (R - 24); y = cy + math.sin(a) * (R - 24)
            cv.blend_rect(int(x), int(y), int(x) + 2, int(y) + 1, (255, 255, 255, 40))

    # ------------------------------------------------------------------ frame
    def albedo(self, hh, mm, ss, min_angle=None):
        cv = Canvas(480, 270); cv.a[:] = self.static
        self.hands(cv, hh, mm, self.tick_angle(ss), min_angle)
        self.glare(cv)
        return cv.a

    def frame(self, cam, hh, mm, ss, frame=0, ui=None, fade=1.0, glow_out=None, min_angle=None, light_k=1.0, grade=None,
              pre_grade=None):
        a = self.albedo(hh, mm, ss, min_angle)
        return self.fs.render(cam, a, self.L * light_k, grade or self.grade, frame=frame, ui=ui, fade=fade, glow_out=glow_out,
                              pre_grade=pre_grade)


# ====================================================================== v0.11: film photo print + framed photo insert
DIGITS_3x5 = {'0': '###,#.#,#.#,#.#,###', '1': '.#.,##.,.#.,.#.,###', '2': '###,..#,###,#..,###', '3': '###,..#,.##,..#,###',
              '4': '#.#,#.#,###,..#,..#', '5': '###,#..,###,..#,###', '6': '###,#..,###,#.#,###', '7': '###,..#,.#.,.#.,.#.',
              '8': '###,#.#,###,#.#,###', '9': '###,#.#,###,..#,###', "'": '#..,#..,...,...,...', ' ': '...,...,...,...,...'}

def _film_tone(im, k, hal_sigma=2.0):
    """the colour side of the old-print look (float RGB 0..1): softer saturation, milky blacks,
    cyan shadows / yellowed highlights, a little warm halation."""
    lum = im @ np.float32([0.3, 0.59, 0.11])
    im = im * (1 - 0.18 * k) + lum[..., None] * 0.18 * k
    im = 0.075 * k + im * (1 - 0.13 * k)
    sh = (1 - lum)[..., None] ** 2
    im = im + k * (sh * np.float32([-0.02, 0.015, 0.03]) + (1 - sh) * np.float32([0.035, 0.012, -0.05]))
    hal = cv2.GaussianBlur(np.clip(lum - 0.7, 0, 1), (0, 0), hal_sigma)[..., None] * np.float32([0.25, 0.08, 0.02])
    return im + hal * k


def film_grade(img, k, date="'97 8 16", frame=0, aspect=1.5, grain_px=4, seed=4):
    """the film_print look applied to a full graded frame (float RGB, output res) with strength k (0..1) -
    for match cuts INTO a photo world: open on the print's colours, grain and date stamp, then fade k -> 0.
    The print = the centre crop of the given aspect (as film_print crops it); the date stamp sits at the
    same place on it and the vignette follows it.  Grain: native-px blocks (grain_px), re-rolled every frame."""
    if k <= 0.001: return img
    H, W = img.shape[:2]
    im = _film_tone(np.clip(img, 0, 1).astype(np.float32), k, hal_sigma=2.0 * W / 204)
    cw = min(W, int(round(H * aspect))); ch = int(round(cw / aspect)); x0, y0 = (W - cw) // 2, (H - ch) // 2
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xs - x0 + 0.5) / cw - 0.5) ** 2 * 1.2 + ((ys - y0 + 0.5) / ch - 0.5) ** 2)
    im = im * (1 - 0.32 * k * np.clip((r - 0.30) / 0.35, 0, 1) ** 1.5)[..., None]
    rng = np.random.default_rng(seed * 7919 + frame)
    gh, gw = -(-H // grain_px), -(-W // grain_px)
    gr = np.repeat(np.repeat(rng.random((gh, gw, 1)).astype(np.float32) - 0.5, grain_px, 0), grain_px, 1)[:H, :W]
    im = im + gr * 0.045 * k
    if date:
        B = cw / 204.0                                            # one print pixel (film_print's default width) in output px
        px0 = x0 + (204 - 4 - 4 * len(date) + 1) * B; py0 = y0 + (136 - 8) * B
        col = np.float32([1.0, 0.59, 0.24]) * 1.25
        for ci, chh in enumerate(date):
            g = DIGITS_3x5.get(chh, DIGITS_3x5[' ']).split(',')
            for j, row in enumerate(g):
                for i, c in enumerate(row):
                    if c == '#':
                        xa, ya = int(round(px0 + (ci * 4 + i) * B)), int(round(py0 + j * B))
                        xb, yb = int(round(px0 + (ci * 4 + i + 1) * B)), int(round(py0 + (j + 1) * B))
                        im[ya:yb, xa:xb] = im[ya:yb, xa:xb] * (1 - k) + col * k
    return im


def film_print(rgb, w=168, h=112, date="'97 8 16", seed=4, fade=1.0):
    """an old colour film print (native px) from any rendered frame (float RGB 0..1, output res):
    centre crop to w:h, area downsample, lifted milky blacks, warm/yellowed highlights + cyan-ish shadows,
    softened saturation, corner fall-off, a little halation and grain, and the orange date stamp (3x5 digits).
    -> (rgba uint8 (h, w, 4), E float32 (h, w)) - E = the date stamp's glow."""
    H0, W0 = rgb.shape[:2]
    ar = w / h
    cw = min(W0, int(round(H0 * ar))); ch = int(round(cw / ar))
    x0, y0 = (W0 - cw) // 2, (H0 - ch) // 2
    im = cv2.resize(np.ascontiguousarray(rgb[y0:y0 + ch, x0:x0 + cw]).astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
    im = np.clip(im, 0, 1)
    k = fade
    im = _film_tone(im, k, hal_sigma=2.0)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xs + 0.5) / w - 0.5) ** 2 * 1.2 + ((ys + 0.5) / h - 0.5) ** 2)
    im = im * (1 - 0.32 * k * np.clip((r - 0.30) / 0.35, 0, 1) ** 1.5)[..., None]
    rng = np.random.default_rng(seed)
    im = im + (rng.random((h, w, 1)).astype(np.float32) - 0.5) * 0.045 * k
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = np.clip(im * 255, 0, 255).astype(np.uint8); out[..., 3] = 255
    E = np.zeros((h, w), np.float32)
    if date:
        x = w - 4 - 4 * len(date) + 1; y = h - 8
        for chh in date:
            g = DIGITS_3x5.get(chh, DIGITS_3x5[' ']).split(',')
            for j, row in enumerate(g):
                for i, c in enumerate(row):
                    if c == '#':
                        out[y + j, x + i, :3] = (255, 150, 60); E[y + j, x + i] = 0.9
                        if y + j + 1 < h: out[y + j + 1, x + i, :3] = np.minimum(out[y + j + 1, x + i, :3], (150, 70, 40))
            x += 4
    return out, E


class PhotoFrameInsert:
    """a framed photo standing on a desk at night, filling the frame (480x270 native, FlatScene):
    walnut moulding + cream mat + the print + glass (soft laptop reflection, a two-stripe glint that can sweep),
    the dark office behind (a partition + a beige CRT out of focus), lit by a cool laptop glow from the left;
    warmth 0..1 lets the photo glow on its own (it 'comes alive' before a match cut into it).

        pi = PhotoFrameInsert(print_rgba, print_E)
        img = pi.frame(cam, frame=i, glint=u (None | 0..1 sweep), warmth=w, cool=1.0, ui=ui_rgba, motes_t=t)"""
    def __init__(self, print_rgba, print_E=None, OW=1920, OH=1080, seed=6, mat='#e9dfc8', wood='#7a5034', style=2):
        self.fs = FlatScene(OW=OW, OH=OH)
        self.pr = print_rgba; self.prE = print_E if print_E is not None else np.zeros(print_rgba.shape[:2], np.float32)
        ph, pw = print_rgba.shape[:2]
        self.pw, self.ph = pw, ph
        m, b = 8, 10                                              # mat, moulding
        self.fw, self.fh = pw + 2 * (m + b), ph + 2 * (m + b)
        self.fx, self.fy = 240 - self.fw // 2, 214 - self.fh       # frame top-left; its foot on the desk at y 214
        self.px, self.py = self.fx + m + b, self.fy + m + b
        self.m, self.b, self.seed, self.mat, self.wood, self.style = m, b, seed, mat, wood, style
        self.static, self.glass = self._static()
        self.grade = dict(post.GRADES['night_hd2d'])
        rng = np.random.default_rng(seed + 1)
        self.motes = [(float(rng.uniform(10, 200)), float(rng.uniform(20, 250)), float(rng.uniform(0, 6.28)), float(rng.uniform(0.5, 1.4)))
                      for _ in range(9)]

    def fill_cam(self, margin=1.004):
        """(zoom, cx, cy) where the print's height fills the 16:9 frame - exactly the centre 1.5 crop that
        film_print / film_grade use, so an edit 'dissolve' into the photo's world (rendered with film_grade k=1 at
        the print's camera) lines up pixel for pixel: the recipe 'into the photo' (see STYLE_GUIDE 6n)."""
        return 270.0 / self.ph * margin, self.px + self.pw / 2.0, self.py + self.ph / 2.0

    def _static(self):
        W, H = 480, 270
        cv = Canvas(W, H)
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
        self.E_static = np.zeros((H, W), np.float32)
        if self.style >= 2:
            self._bg_v2(cv, xs, ys)
        else:
            # partition fabric (out of focus: low contrast weave) above the desk
            fr = ramp('#4a6478', 6)
            t = 2.8 + fbm(xs * 0.6, ys * 0.6, 30.0, 2, self.seed) * 0.8 - 0.4 + ((xs.astype(int) % 3) == 0) * -0.3
            cv.a[..., :3] = apply_ramp(t, fr, xs.astype(int), ys.astype(int), True, band=3.5)[..., :3]; cv.a[..., 3] = 255
            cv.rect(0, 0, W, 6, ramp('#c2c8cc', 6)[2]); cv.hline(0, 6, W, fr[0])                         # partition rail (top)
            # the CRT monitor behind (right): soft beige casing, dark screen corner
            cr = ramp('#c9c0ac', 6)
            cv.rrect(300, 30, 200, 190, cr[2], 10); cv.rrect(304, 34, 192, 182, cr[3], 9)
            cv.rrect(330, 52, 160, 120, C('#1a2226'), 6); cv.rrect(334, 56, 152, 112, C('#232e33'), 5)
            for k in range(6): cv.hline(318 + k * 4, 200, 2, cr[1])                                        # vents
            cv.rect(96, 6, 3, 204, ramp('#c2c8cc', 6)[1])                                                  # partition post
        # the noodle cup (left, soft) + its lid fold
        nr = ramp('#e8e0d0', 6)
        cv.rrect(40, 150, 46, 62, nr[2], 4); cv.rect(44, 160, 38, 18, C('#c0392b')); cv.rect(44, 162, 38, 2, C('#e8c04a'))
        cv.rect(38, 146, 50, 6, nr[3]); cv.rect(60, 136, 22, 12, nr[3])
        # desk top (wood, receding) + front edge
        wr = ramp('#9a6440', 6)
        tt = 3.0 + np.sin(xs * 0.05 + np.sin(ys * 0.3) * 2.0) * 0.5 + (fbm(xs, ys * 4, 16.0, 2, self.seed + 3) - 0.5) * 0.8
        desk = apply_ramp(tt, wr, xs.astype(int), ys.astype(int), True)[..., :3]
        m = ys >= 210
        cv.a[m, :3] = desk[m]
        cv.hline(0, 210, W, wr[4]); cv.hline(0, 211, W, wr[3])
        cv.rect(0, 262, W, 8, wr[1]); cv.hline(0, 262, W, wr[2])
        # contact shadow under the frame
        for k in range(5):
            cv.rect(self.fx - 4 + k, 214 + k, self.fw + 12 - 2 * k, 1, (30, 20, 26, 150 - 25 * k))
        if self.style >= 2: self._keyboard_corner(cv)
        # the frame: walnut moulding with a bevel (lit top-left, dark bottom-right), a mitre line at each corner
        wd = ramp(self.wood, 6)
        fx, fy, fw, fh, b, mm = self.fx, self.fy, self.fw, self.fh, self.b, self.m
        cv.rect(fx, fy, fw, fh, wd[2])
        rng = np.random.default_rng(self.seed)
        for j in range(fh):                                        # wood grain along each side
            for i in range(fw):
                if i < b or i >= fw - b or j < b or j >= fh - b:
                    if rng.random() < 0.18: cv.px(fx + i, fy + j, wd[1] if rng.random() < 0.6 else wd[3])
        for k in range(b):
            lt = wd[4] if k < 2 else wd[3]
            cv.hline(fx + k, fy + k, fw - 2 * k, lt if k in (0, 1, 4) else wd[2]); cv.vline(fx + k, fy + k, fh - 2 * k, lt if k in (0, 1, 4) else wd[2])
            dk = wd[0] if k < 2 else wd[1]
            cv.hline(fx + k, fy + fh - 1 - k, fw - 2 * k, dk if k in (0, 1, 4) else wd[2]); cv.vline(fx + fw - 1 - k, fy + k, fh - 2 * k, dk if k in (0, 1, 4) else wd[2])
        for k in range(b):                                         # mitres
            for (cx_, cy_, sx, sy) in ((fx, fy, 1, 1), (fx + fw - 1, fy, -1, 1), (fx, fy + fh - 1, 1, -1), (fx + fw - 1, fy + fh - 1, -1, -1)):
                cv.px(cx_ + sx * k, cy_ + sy * k, wd[1])
        cv.hline(fx + 2, fy, fw - 4, wd[5])                        # top edge catches the light
        # cream mat with an inner bevel
        mr = ramp(self.mat, 6)
        cv.rect(fx + b, fy + b, fw - 2 * b, fh - 2 * b, mr[3])
        for j in range(fh - 2 * b):
            for i in range(fw - 2 * b):
                if rng.random() < 0.05: cv.px(fx + b + i, fy + b + j, mr[2])
        cv.rect(fx + b, fy + b, fw - 2 * b, 1, mr[1]); cv.rect(fx + b, fy + b, 1, fh - 2 * b, mr[1])   # shadow of the moulding
        cv.rect(self.px - 1, self.py - 1, self.pw + 2, self.ph + 2, mr[4])                          # bevel cut
        cv.hline(self.px - 1, self.py + self.ph, self.pw + 2, mr[5])
        cv.blit(self.pr, self.px, self.py)
        glass = np.zeros((H, W), bool); glass[fy + b:fy + fh - b, fx + b:fx + fw - b] = True
        return cv.a.copy(), glass


    # ------------------------------------------------------------ style 2 (v0.11): bokeh office, keyboard corner, reflection
    BOKEH = (  # x, y, r, colour, emissive  - the out-of-focus night office behind the frame
        (28, 40, 15, (255, 196, 120), 0.75), (70, 18, 9, (255, 214, 150), 0.55), (6, 96, 11, (255, 170, 100), 0.5),   # Claude's lamp, far left
        (112, 70, 7, (140, 190, 255), 0.45), (150, 22, 6, (120, 170, 250), 0.35),                                    # monitors across the room
        (392, 46, 10, (120, 170, 255), 0.5), (420, 120, 14, (110, 160, 250), 0.45), (452, 30, 7, (150, 200, 255), 0.4),  # Wang's CRT glow
        (468, 8, 6, (90, 235, 140), 0.6), (442, 12, 4, (90, 235, 140), 0.45),                                         # the exit sign
        (205, 14, 4, (255, 226, 170), 0.35), (226, 26, 3, (255, 226, 170), 0.3), (258, 10, 5, (255, 220, 160), 0.3),   # city windows
        (330, 22, 4, (255, 226, 170), 0.3), (300, 6, 3, (200, 220, 255), 0.3))

    def _bg_v2(self, cv, xs, ys):
        W, H = 480, 270
        rng = np.random.default_rng(self.seed + 11)
        top, bot = np.float32([16, 20, 40]), np.float32([40, 50, 80])
        g = np.clip(ys / 210.0, 0, 1)[..., None]
        bg = top * (1 - g) + bot * g
        def box(x0, y0, x1, y1, col, k=1.0):
            bg[y0:y1, x0:x1] = bg[y0:y1, x0:x1] * (1 - k) + np.float32(col) * k
        box(0, 0, W, 210, (44, 58, 86), 0.55)                        # partition fabric
        box(0, 0, W, 7, (110, 118, 140), 0.8)                        # its rail
        box(96, 0, 100, 210, (88, 96, 120), 0.7)                     # a post
        box(300, 30, 500, 220, (120, 112, 100), 0.85)                # Wang's CRT casing (dim beige) ...
        box(330, 52, 490, 172, (26, 38, 62), 1.0)                    # ... its screen, a cold glow
        box(150, 150, 300, 210, (30, 38, 62), 0.6)                   # shadowy clutter behind the frame
        bg = cv2.GaussianBlur(bg, (0, 0), 4.0)                       # deep focus fall-off (native px -> still blocks)
        bg = np.round(bg / 6.0) * 6.0                                # posterise: banded pixel-art steps, not a photo gradient
        bg = bg + (rng.random((H, W, 1)).astype(np.float32) - 0.5) * 4.0
        E = self.E_static
        for (x, y, r, col, e) in self.BOKEH:                         # soft discs, slightly brighter rim (lens cat-eye)
            d = np.sqrt((xs - x) ** 2 + (ys - y) ** 2) / r
            m = (d < 1.0).astype(np.float32)                         # hard-edged pixel discs (no smooth falloff)
            rim = ((d > 0.78) & (d < 1.0)).astype(np.float32) * 0.3   # 1-2 px brighter ring
            a = (m * (0.55 + rim))[..., None]
            bg = bg * (1 - a * 0.7) + np.float32(col) * a
            E[:] = np.maximum(E, (m * e).astype(np.float32))
        cv.a[..., :3] = np.clip(bg, 0, 255).astype(np.uint8); cv.a[..., 3] = 255

    def _keyboard_corner(self, cv):
        """the corner of Wang's keyboard in the foreground (bottom left), slightly out of focus."""
        W, H = 480, 270
        k = np.zeros((H, W, 4), np.float32)
        def r(x0, y0, w, h, col, a=1.0):
            x0, y0 = max(0, x0), max(0, y0)
            k[y0:y0 + h, x0:x0 + w, :3] = col; k[y0:y0 + h, x0:x0 + w, 3] = a
        r(0, 228, 128, 42, (46, 48, 58)); r(0, 228, 126, 2, (92, 96, 112))       # body + lit top edge
        for row in range(3):
            y = 233 + row * 12
            off = (row * 5) % 12
            for i in range(9):
                x = -6 + off + i * 14
                if x + 12 > 122: continue
                r(x, y, 12, 10, (70, 74, 88)); r(x, y, 12, 2, (118, 124, 142)); r(x + 1, y + 9, 11, 1, (34, 34, 44))
        k[..., :3] = k[..., :3] * 0.8 + 10                           # out of focus = lower contrast, still crisp pixels
        a = np.clip(k[..., 3:4], 0, 1)
        rgb = k[..., :3] / np.maximum(a, 1e-4)
        cv.a[..., :3] = np.clip(cv.a[..., :3] * (1 - a) + rgb * a, 0, 255).astype(np.uint8)

    def _reflection(self, a, xs, ys, k):
        """Wang's faint reflection in the glass: head + shoulders lit by his laptop, two small screen glints in his glasses."""
        if k <= 0.01: return
        g = self.glass
        hx, hy = self.fx + self.fw * 0.27, self.fy + self.fh * 0.36
        head = ((xs - hx) / 21.0) ** 2 + ((ys - hy) / 25.0) ** 2 < 1
        hair = (((xs - hx) / 23.0) ** 2 + ((ys - hy + 6) / 24.0) ** 2 < 1) & (ys < hy - 8)
        sh = (((xs - hx) / 64.0) ** 2 + ((ys - (hy + 66)) / 40.0) ** 2 < 1) & (ys > hy + 20)
        neck = (np.abs(xs - hx) < 9) & (ys > hy + 14) & (ys < hy + 34)
        body = (head | sh | neck) & g
        m = body.astype(np.float32) * 0.17 - (hair & g) * 0.09
        lens = g & (np.abs(ys - (hy + 2)) < 3) & ((np.abs(xs - (hx - 8)) < 5) | (np.abs(xs - (hx + 8)) < 5))
        m = np.where(lens, 0.38, m) * k
        sel = m > 0.005
        mm = m[sel][:, None]
        a[sel, :3] = (a[sel, :3].astype(np.float32) * (1 - mm) + np.float32([150, 180, 235]) * mm).astype(np.uint8)

    def light(self, cool=1.0, warmth=0.0):
        fs = self.fs
        L = fs.ambient((0.20, 0.24, 0.42), 0.55, top=0.8, bottom=1.0)
        L = L + fs.pool(-30, 150, 230, 160, (0.50, 0.70, 1.05), 0.95 * cool, power=1.4)         # the laptop, off left
        L = L + fs.pool(240, 300, 260, 70, (0.35, 0.50, 0.85), 0.25 * cool, power=1.6)          # its spill on the desk
        if warmth > 0:
            L = L + fs.pool(self.px + self.pw / 2, self.py + self.ph / 2, self.pw * 0.9, self.ph * 0.9, (1.0, 0.70, 0.45), 0.35 * warmth, power=1.6)
            if self.style >= 2:      # the glow spills onto the moulding and the desk in front
                L = L + fs.pool(self.px + self.pw / 2, self.py + self.ph / 2, self.fw * 0.75, self.fh * 0.75, (1.0, 0.66, 0.40), 0.45 * warmth, power=1.3)
                L = L + fs.pool(240, 226, 190, 26, (1.0, 0.62, 0.36), 0.55 * warmth, power=1.5)
        return L

    def albedo(self, glint=None, t=0.0, reflect=1.0):
        a = self.static.copy()
        E = self.E_static.copy()
        E[self.py:self.py + self.ph, self.px:self.px + self.pw] = self.prE
        ys, xs = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        g = self.glass
        # the laptop's reflection: a soft pale-blue panel on the left of the glass
        rk = np.clip(1 - (xs - self.fx) / (self.fw * 0.55), 0, 1) ** 1.5 * np.clip((ys - self.fy) / (self.fh * 0.5), 0, 1)
        rk = (rk * 0.16)[g][:, None]
        a[g, :3] = (a[g, :3].astype(np.float32) * (1 - rk) + np.float32([150, 190, 240]) * rk).astype(np.uint8)
        if self.style >= 2: self._reflection(a, xs, ys, reflect)
        if glint is not None and -0.05 < glint < 1.05:
            u = xs + (ys - self.fy) * 0.55                          # diagonal stripes travelling left -> right
            c0 = self.fx - 40 + (self.fw + 120) * glint
            for (off, wdt, k) in ((0, 12, 0.32), (18, 3, 0.45)):
                s = g & (np.abs(u - (c0 + off)) < wdt / 2)
                a[s, :3] = (a[s, :3].astype(np.float32) * (1 - k) + 255 * k).astype(np.uint8); E[s] = np.maximum(E[s], 0.45 * k / 0.45)
        for (x, y, ph, sp) in self.motes:                           # dust motes drifting in the laptop light
            mx = int((x + 6 * math.sin(t * 0.3 * sp + ph)) % 480); my = int((y - t * 4 * sp) % 270)
            if mx < 150 and not self.glass[my, mx] and my < 205:
                a[my, mx, :3] = np.maximum(a[my, mx, :3], (170, 195, 230)); E[my, mx] = 0.35
        return a, E

    def frame(self, cam, frame=0, glint=None, warmth=0.0, cool=1.0, ui=None, t=0.0, fade=1.0):
        a, E = self.albedo(glint, t, reflect=1.0 - 0.8 * warmth)
        if warmth > 0:
            E[self.py:self.py + self.ph, self.px:self.px + self.pw] = np.maximum(E[self.py:self.py + self.ph, self.px:self.px + self.pw], 0.55 * warmth)
        return self.fs.render(cam, a, self.light(cool, warmth), self.grade, E=E, frame=frame, ui=ui, fade=fade)
