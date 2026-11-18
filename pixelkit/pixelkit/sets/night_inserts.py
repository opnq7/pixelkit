"""pixelkit.sets.night_inserts - 深夜特写插入镜头（v0.13，《熬夜副本》）。配合 scene.FlatScene 渲染。

    PhoneInsert().frame(t, episode=37, press=0.0, thumb=(x, y), countdown=3, video_t=t)
        手持手机 POV：短视频（仓鼠跑轮，暗讽“停不下来”）+「第 N 集」+ 自动连播倒计时 +「再看一集 ▶」大红按钮 + 拇指
    EyeInsert().frame(t, veins=0..1, pupil=0..1, droop=0..1, dead=0..1, gaze=(dx, dy), reflect=1.0)
        眼睛大特写：屏幕冷光从下往上打，血丝生长、瞳孔里手机倒影；dead → 瞳孔放大、倒影变暗、去饱和
返回 (albedo RGBA uint8 480x270, E float 480x270, L light map (H*f, W*f, 3))。
"""
import math
import numpy as np, cv2
from ..core import C, Canvas, text_width
from ..paintset import PaintSet, R
from .. import materials as mat
from ..scene import FlatScene

class PhoneInsert:
    W, H = 480, 270
    SCR = (186, 22, 116, 222)          # screen rect x, y, w, h

    def __init__(self, fs=None):
        self.fs = fs or FlatScene()
        ps = PaintSet(self.W, self.H)
        # bedding background: dark quilt folds + out-of-focus fairy-light bokeh (blocky)
        q = R('#3a4277', 7)
        t = 2.4 + 1.2 * np.sin((ps.xx * 0.6 + ps.yy * 1.3) * 0.045) + (mat.fbm(ps.xx * 1.0, ps.yy * 1.0, 30, 3, 5) - 0.5) * 1.4
        ps.cv.a[:] = mat.apply_ramp(t, q, band=1.6)
        rng = np.random.default_rng(7)
        for i in range(18):
            x, y = int(rng.integers(0, self.W)), int(rng.integers(0, 120))
            if 150 < x < 340: continue
            col = C(['#ffcf6a', '#ff8f6a', '#9fe0ff', '#ffe9a8'][i % 4]); r = int(rng.integers(5, 10))
            m = ps.mask_rect(x - r, y - r, 2 * r, 2 * r) & ps.mask_ellipse(x, y, r, r)
            ps.cv.a[m, :3] = (ps.cv.a[m, :3] * 0.5 + np.array(col[:3]) * 0.5).astype(np.uint8); ps.E[m] = 0.35
        # phone body
        x, y, w, h = self.SCR
        body = ps.mask_rect(x - 8, y - 14, w + 16, h + 26)
        rr = ps.mask_ellipse(x - 1, y - 7, 8, 8) | ps.mask_ellipse(x + w + 1, y - 7, 8, 8) | ps.mask_ellipse(x - 1, y + h + 5, 8, 8) | ps.mask_ellipse(x + w + 1, y + h + 5, 8, 8)
        corner_cut = (ps.mask_rect(x - 8, y - 14, 8, 8) | ps.mask_rect(x + w, y - 14, 9, 8) | ps.mask_rect(x - 8, y + h + 5, 8, 8) | ps.mask_rect(x + w, y + h + 5, 9, 8)) & ~rr
        body &= ~corner_cut
        ps.fill(body, C('#16151d')); ps.outline(body, C('#07060a'))
        ps.fill(ps.mask_rect(x - 8, y - 14, 2, h + 26) & body, C('#2e2c3a'))
        ps.rect(x + w // 2 - 10, y - 9, 20, 3, C('#08080c'))                      # notch
        self.base = ps
        self.mask_body = body

    def frame(self, t, episode=37, press=0.0, thumb=(318, 236), countdown=3, video_t=None, flash=0.0, glow=1.0):
        ps = PaintSet(self.W, self.H)
        ps.cv.a[:] = self.base.cv.a; ps.E[:] = self.base.E
        x, y, w, h = self.SCR
        vt = t if video_t is None else video_t
        # ---- video area: hamster in a wheel (the joke: can't stop running)
        vh = 92
        m = ps.mask_rect(x, y, w, vh)
        ps.vgrad(m, R('#ffb37a', 6), y, y + vh, 4.2, 1.4, E=1.0)
        ps.rect(x, y + vh - 14, w, 14, C('#7a4a3a'), 1.0)
        cx, cy, r = x + w // 2, y + 50, 30
        ring = ps.mask_ellipse(cx, cy, r, r) & ~ps.mask_ellipse(cx, cy, r - 3, r - 3)
        ps.fill(ring, C('#d8d8e8'), 1.0)
        for k in range(8):
            a = vt * 9.0 + k * math.pi / 4
            ps.line(cx, cy, cx + (r - 2) * math.cos(a), cy + (r - 2) * math.sin(a), C('#a8a8c0'), 1.0)
        ps.fill(ps.mask_ellipse(cx, cy, 3, 3), C('#8888a0'), 1.0)
        ps.rect(cx - 2, cy, 4, r + 12, C('#8888a0'), 1.0)
        hx, hy = cx, cy + r - 9 + int(round(1.5 * math.sin(vt * 30)))           # hamster running at the bottom
        ps.fill(ps.mask_ellipse(hx, hy, 9, 6), C('#e8a860'), 1.0); ps.fill(ps.mask_ellipse(hx + 2, hy + 1, 6, 4), C('#fff0d8'), 1.0)
        ps.px(hx - 6, hy - 2, C('#1a1010'), 1.0); ps.fill(ps.mask_ellipse(hx - 4, hy - 6, 2, 2), C('#f0a0a0'), 1.0)
        for k in range(2):
            lx = hx - 3 + 6 * k + int(round(2 * math.sin(vt * 30 + k * 3)))
            ps.rect(lx, hy + 5, 2, 2, C('#c07040'), 1.0)
        # progress bar (full) + UI
        ps.rect(x, y + vh, w, 3, C('#3a3a48'), 1.0); ps.rect(x, y + vh, w, 3, C('#ff3d5a'), 1.0)
        ps.rect(x, y + vh + 3, w, h - vh - 3, C('#14131c'), 1.0)
        s = f'第 {episode} 集'
        ps.text(x + w // 2 - text_width(s, 'zh12') // 2, y + vh + 12, s, C('#ffffff'), 'zh12', E=1.0)
        s2 = '自动连播中'
        ps.text(x + w // 2 - text_width(s2, 'zh8') // 2, y + vh + 30, s2, C('#8a88a0'), 'zh8', E=1.0)
        cd = str(countdown)
        ps.text(x + w // 2 - text_width(cd, 'p2p') * 2 // 2, y + vh + 46, cd, C('#ffd34a'), 'p2p', E=1.0)
        # big red button
        bx, by, bw, bh = x + 10, y + h - 46, w - 20, 26
        pr = press
        col = C('#ff3d5a') if pr < 0.5 else C('#b02040')
        ps.rect(bx, by + 3, bw, bh, C('#6a1020'), 1.0)
        ps.rect(bx, by + int(round(2 * pr)), bw, bh, col, 1.0)
        ps.rect(bx + 2, by + 1 + int(round(2 * pr)), bw - 4, 1, C('#ff8a9a'), 1.0)
        s3 = '再看一集 ▶'
        ps.text(bx + bw // 2 - text_width(s3, 'zh12') // 2, by + 6 + int(round(2 * pr)), s3, C('#ffffff'), 'zh12', E=1.0)
        if flash > 0:
            m = ps.mask_rect(x, y, w, h); ps.cv.a[m, :3] = (ps.cv.a[m, :3] * (1 - flash) + 255 * flash).astype(np.uint8)
        # ---- thumb (comes from bottom-right, nail toward the button)
        tx, ty = thumb
        sk = R('#e8b48e', 6)
        th = ps.mask_ellipse(tx, ty, 17, 24) | ps.mask_poly([(tx - 10, ty + 10), (tx + 16, ty - 2), (tx + 80, ty + 70), (tx + 30, ty + 90)])
        t_ = 3.0 - np.clip((ps.xx - tx + 6) / 26.0, 0, 1) * 1.6 + np.clip((ty - ps.yy) / 30.0, 0, 1) * 0.6
        img = mat.apply_ramp(t_, sk, band=2.0); ps.cv.a[th] = img[th]; ps.E[th] = 0
        ps.outline(th, C('#5a2a2a'))
        nail = ps.mask_ellipse(tx - 2, ty - 12, 9, 10) & th
        ps.fill(nail, C('#f6d8cc')); ps.fill(ps.mask_ellipse(tx - 5, ty - 15, 3, 3) & nail, C('#ffffff'))
        ps.line(tx - 10, ty - 3, tx + 6, ty - 2, C('#c08a70'))
        # light: dim room + the screen as an area light (thumb + bedding near the phone)
        fs = self.fs
        L = fs.ambient((0.40, 0.38, 0.70), 0.42)
        L = L + fs.pool(x + w / 2, y + h / 2, 130, 150, (0.55, 0.78, 1.0), 0.95 * glow, 1.6)
        L = L + fs.pool(tx - 6, ty - 10, 34, 34, (0.65, 0.85, 1.0), 0.30 * glow, 2.0)
        return ps.cv.a, ps.E, L

class EyeInsert:
    W, H = 480, 270
    CX, CY = 240, 140

    def __init__(self, fs=None, seed=11):
        self.fs = fs or FlatScene()
        rng = np.random.default_rng(seed)
        self.veins = []
        for i in range(18):
            side = i % 2
            x = self.CX - 112 if side == 0 else self.CX + 112; y = self.CY + rng.integers(-16, 16); pts = [(x, y)]
            for j in range(int(rng.integers(6, 11))):
                x += (rng.integers(4, 9) if side == 0 else -rng.integers(4, 9)); y += rng.integers(-4, 5); pts.append((x, y))
            self.veins.append(pts)
        ps = PaintSet(self.W, self.H)
        sk = R('#d9a184', 8)
        t = 4.2 + (mat.fbm(ps.xx * 1.0, ps.yy * 1.0, 26, 3, 3) - 0.5) * 0.9
        ps.cv.a[:] = mat.apply_ramp(t, sk, band=1.8)
        # pores / skin speckle
        sp = rng.random((self.H, self.W)) < 0.012
        ps.cv.a[sp, :3] = sk[3][:3]
        # socket shade + dark circles (purple) below the eye
        ps.ao_mask(ps.mask_ellipse(self.CX, self.CY, 150, 64), 0.30, 18)
        bags = ps.mask_ellipse(self.CX + 6, self.CY + 52, 120, 20) & ~ps.mask_ellipse(self.CX + 6, self.CY + 36, 124, 22)
        ps.cv.a[bags, :3] = (ps.cv.a[bags, :3] * 0.6 + np.array(C('#7a4e86')[:3]) * 0.4).astype(np.uint8)
        for k, dy in enumerate((44, 54, 63)):
            m = ps.mask_ellipse(self.CX + 6, self.CY + dy - 14, 110 - k * 12, 16) & ~ps.mask_ellipse(self.CX + 6, self.CY + dy - 16, 110 - k * 12, 16)
            ps.cv.a[m, :3] = R('#8a5470', 6)[2][:3]
        # eyebrow: hair strokes
        # eyebrow: a tapered band (thick at the inner end) with hair texture
        up = [(self.CX - 150 + 300 * u, self.CY - 86 - 20 * math.sin(math.pi * (0.1 + 0.8 * u)) + 4 * u) for u in np.linspace(0, 1, 40)]
        lo = [(x, y + 12 - 9 * (i / 39)) for i, (x, y) in enumerate(up)][::-1]
        bm = ps.mask_poly(up + lo)
        br = R('#3a2622', 6)
        tb = 2.0 + (mat.value_noise(ps.xx * 3.0, ps.yy * 0.6, 3.0, 4) - 0.5) * 2.2
        img = mat.apply_ramp(tb, br, band=1.4); ps.cv.a[bm] = img[bm]
        for i in range(40):
            x, y = up[int(rng.integers(0, 40))]
            ps.line(x, y + rng.integers(0, 4), x + rng.integers(4, 9), y - rng.integers(1, 4), br[1])
        self.base = ps

    def lids(self, droop=0.0, twitch=0):
        top = [(self.CX - 122 + i * 5, self.CY - (56 - 30 * droop) * math.sin(math.pi * i / 48.8) + 6) for i in range(50)]
        bot = [(self.CX + 122 - i * 5, self.CY + 46 * math.sin(math.pi * i / 48.8) + 4 + twitch) for i in range(50)]
        return top, bot

    def frame(self, t, veins=0.3, pupil=0.0, droop=0.0, dead=0.0, gaze=(0, 0), reflect=1.0, twitch=0, screen=(205, 236, 255)):
        ps = PaintSet(self.W, self.H)
        ps.cv.a[:] = self.base.cv.a; ps.ao[:] = self.base.ao
        top, bot = self.lids(droop, twitch)
        em = ps.mask_poly(top + bot)
        # sclera with soft shading toward the corners
        scl = R('#ece4df', 6)
        tt = 4.2 - np.clip(np.abs(ps.xx - self.CX) / 120.0, 0, 1) * 1.6 - np.clip((self.CY - 20 - ps.yy) / 40.0, 0, 1) * 1.4
        img = mat.apply_ramp(tt, scl, band=2.0); ps.cv.a[em] = img[em]
        nv = int(len(self.veins) * min(1.0, veins))
        for v in self.veins[:nv]:
            for (x0, y0), (x1, y1) in zip(v, v[1:]): ps.line(x0, y0, x1, y1, C('#d0504a'))
        gx, gy = self.CX + gaze[0], self.CY + 2 + gaze[1]
        iris = ps.mask_ellipse(gx, gy, 44, 44) & em
        ir = R('#6a3e26', 7)
        rr = np.sqrt((ps.xx - gx) ** 2 + (ps.yy - gy) ** 2); ang = np.arctan2(ps.yy - gy, ps.xx - gx)
        ti = 2.2 + np.clip(rr / 44.0, 0, 1) * 1.8 + 0.6 * np.sin(ang * 23) * (rr > 18) - (rr > 40) * 2.0
        img = mat.apply_ramp(ti, ir, band=1.8); ps.cv.a[iris] = img[iris]
        pr = 15 + 15 * pupil
        pm = ps.mask_ellipse(gx, gy, pr, pr) & em
        ps.fill(pm, C('#09070a'))
        # screen reflection (emissive) + catchlights
        rk = reflect * (1 - 0.6 * dead)
        if rk > 0.02:
            rc = tuple(int(c * rk) for c in screen) + (255,)
            m = ps.mask_rect(gx + 12, gy - 22, 12, 17) & em
            ps.fill(m, rc, 0.9 * rk); ps.fill(ps.mask_rect(gx + 14, gy - 20, 8, 6) & em, tuple(int(c * 0.6 * rk) for c in screen) + (255,), 0.9 * rk)
            ps.fill(ps.mask_rect(gx - 22, gy - 12, 4, 4) & em, (255, 255, 255, 255), 0.8 * rk)
        # lid lines, crease, lashes
        for (x0, y0), (x1, y1) in zip(top, top[1:]):
            for d in range(4): ps.line(x0, y0 - d, x1, y1 - d, R('#3a2020', 6)[1 + (d > 1)])
        for i in range(8, 49, 2):
            x0, y0 = top[i]; u = i / 49
            ln = 4 + 9 * u
            ps.line(x0, y0 - 3, x0 + 2 + 7 * u, y0 - 3 - ln, C('#24120f'))
            ps.line(x0 + 1, y0 - 3, x0 + 3 + 7 * u, y0 - 3 - ln, C('#24120f'))
        for (x0, y0), (x1, y1) in zip(top[6:44], top[7:45]): ps.line(x0, y0 - 16, x1, y1 - 16, R('#b8806a', 6)[2])
        for (x0, y0), (x1, y1) in zip(bot, bot[1:]):
            ps.line(x0, y0, x1, y1, R('#a8706a', 6)[2]); ps.line(x0, y0 + 1, x1, y1 + 1, R('#e8b0a0', 6)[3])
        ps.fill(ps.mask_ellipse(self.CX - 118, self.CY + 6, 7, 6) & ~em, C('#d88a8a'))          # inner corner
        fs = self.fs
        L = fs.ambient((0.45, 0.36, 0.55), 0.55)
        L = L + fs.pool(self.CX, self.H + 40, 260, 170, (0.50, 0.75, 1.0), 1.25, 1.4)            # phone light from below
        L = L * (ps.ao if False else 1.0)
        L = L * cv2.resize(ps.ao, (self.W * fs.f, self.H * fs.f), interpolation=cv2.INTER_LINEAR)[..., None]
        if dead > 0:
            g = ps.cv.a[..., :3].astype(np.float32).mean(-1, keepdims=True)
            ps.cv.a[..., :3] = (ps.cv.a[..., :3] * (1 - 0.8 * dead) + g * 0.8 * dead).astype(np.uint8)
        return ps.cv.a, ps.E, L
