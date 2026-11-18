"""pixelkit.bookreveal - 书本出场 v4（001《深度工作》沉淀；每期换封面复用）。v1/v2 留在 bookreveal_v1.py / bookreveal_v2.py。

用户定的方向（2026-11-09）：v1 的「光柱 → 旋转降落 → 落地冲击 → 光芒 → 扫光」流程更好；不要翻页；书要有质感的精装边框；
结束时直接消失（不停靠角落）。

    from pixelkit.bookreveal import BookReveal
    BR = BookReveal(cover_px, t_out=4.2)            # cover_px：像素化封面 RGB(A)（UI 网格，例 81x118）
    img = BR.frame(img, u, cv, gv)                  # u = t - t0；cv / gv = 本帧 UI / 辉光画布（hud.compose 合成）
    BR.sfx(bus, t0)

时间（u，秒）：
    0.00–0.30  压暗 + 暗角收紧
    0.08–0.50  柔光光柱从顶上落下，金尘上浮
    0.25–1.35  精装书在光里旋转下落（1.25 圈 3D 透视，可见书脊和书页厚度，带淡残影），减速落定
    1.35       落地：像素冲击环 + 暖色光爆 + 金色碎光 + 轻弹
    1.35–      背后光芒慢转、光晕呼吸、星芒环绕；推镜 1.00→1.08；悬浮轻摆
    1.65       封面斜向扫光（之后每 2.2 s 一次）
    t_out      消散：书从上到下化成金色光粒飞走（0.7 s），暗场恢复
精装书：封面图嵌在深蓝布面板里，外圈双线金色压纹边框 + 四角包金 + 书脊金带；侧面是书页（细线），背面布面 + 金色徽记。
"""
import math
import numpy as np
import cv2

GOLD_A = np.array((1.0, 0.82, 0.45), np.float32)
WHITE_A = np.array((1.0, 0.97, 0.9), np.float32)


def _sm(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def _o3(u): u = max(0.0, min(1.0, u)); return 1 - (1 - u) ** 3


G_HI, G_MD, G_DK, G_TOP = (242, 207, 114), (184, 134, 44), (106, 70, 20), (255, 241, 194)
CLOTH, CLOTH2, CLOTH3 = (30, 36, 70), (40, 48, 90), (20, 24, 48)


def hardcover(cover, m=6):
    """cover art (h, w, 3|4) -> hardcover front texture with a cloth board, embossed gold double frame and gold corners."""
    c = cover[..., :3]
    h, w = c.shape[:2]
    H, W = h + 2 * m, w + 2 * m
    t = np.zeros((H, W, 4), np.uint8); t[..., 3] = 255
    yy, xx = np.mgrid[0:H, 0:W]
    t[..., :3] = CLOTH
    t[((xx + yy) % 3 == 0)] = (*CLOTH2, 255)                          # cloth weave
    t[((xx * 2 + yy) % 7 == 0)] = (*CLOTH3, 255)
    # art inset with a dark bevel + light top-left lip
    t[m:m + h, m:m + w, :3] = c
    t[m - 1, m - 1:m + w + 1, :3] = (10, 10, 20); t[m + h, m - 1:m + w + 1, :3] = (70, 76, 120)
    t[m - 1:m + h + 1, m - 1, :3] = (10, 10, 20); t[m - 1:m + h + 1, m + w, :3] = (70, 76, 120)
    # embossed gold double frame in the board margin
    for i, col in ((1, G_DK), (2, G_HI), (4, G_MD)):
        t[i, i:W - i, :3] = col; t[H - 1 - i, i:W - i, :3] = col; t[i:H - i, i, :3] = col; t[i:H - i, W - 1 - i, :3] = col
    t[2, 2:W - 2, :3] = G_TOP                                         # light catches the top edge
    # gold corner caps (triangles) with a highlight
    for (cx, cy, sx, sy) in ((0, 0, 1, 1), (W - 1, 0, -1, 1), (0, H - 1, 1, -1), (W - 1, H - 1, -1, -1)):
        for d in range(9):
            for e in range(9 - d):
                x, y = cx + sx * e, cy + sy * d
                t[y, x, :3] = G_HI if (d + e) < 3 else (G_MD if (d + e) < 7 else G_DK)
        t[cy + sy * 1, cx + sx * 1, :3] = G_TOP
    # spine hinge groove on the left
    t[3:H - 3, 3, :3] = (12, 14, 28)
    return t


def back_cover(W, H):
    t = np.zeros((H, W, 4), np.uint8); t[..., 3] = 255
    yy, xx = np.mgrid[0:H, 0:W]
    t[..., :3] = CLOTH; t[((xx + yy) % 3 == 0)] = (*CLOTH2, 255)
    for i, col in ((2, G_HI), (4, G_MD)):
        t[i, i:W - i, :3] = col; t[H - 1 - i, i:W - i, :3] = col; t[i:H - i, i, :3] = col; t[i:H - i, W - 1 - i, :3] = col
    cx, cy = W // 2, H // 2
    for dy in range(-7, 8):
        ww = 7 - abs(dy); t[cy + dy, cx - ww:cx + ww + 1, :3] = G_HI
    for dy in range(-4, 5):
        ww = 4 - abs(dy); t[cy + dy, cx - ww:cx + ww + 1, :3] = CLOTH
    t[cy, cx, :3] = G_TOP
    return t


def spine_tex(T, H):
    t = np.zeros((H, T, 4), np.uint8); t[..., 3] = 255; t[..., :3] = CLOTH3
    t[:, 1:-1, :3] = CLOTH
    for y in (6, 9, H - 10, H - 7): t[y, :, :3] = G_HI
    for y in range(H // 2 - 14, H // 2 + 14, 4): t[y, 2:-2, :3] = G_MD
    return t


def pages_tex(T, H):
    t = np.zeros((H, T, 4), np.uint8); t[..., 3] = 255; t[..., :3] = (232, 222, 196)
    t[:, ::2, :3] = (208, 196, 168)
    t[0, :, :3] = t[-1, :, :3] = G_MD
    return t


class BookReveal:
    def __init__(self, cover, OW=1920, OH=1080, ui_scale=4, bx=0.5, by=0.45, t_out=None, seed=3, thick=9, **_):
        c = cover if cover.shape[2] == 4 else np.dstack([cover, np.full(cover.shape[:2], 255, np.uint8)])
        self.front = hardcover(c)
        f = self.front[..., :3].astype(np.float32)                     # the cover is the brightest thing on screen: lift + saturate
        g = f.mean(-1, keepdims=True); f = np.clip((g + (f - g) * 1.18) * 1.1 + 6, 0, 255)
        self.front[..., :3] = f.astype(np.uint8)
        self.h, self.w = self.front.shape[:2]
        self.T = thick
        self.back = back_cover(self.w, self.h)
        self.spine = spine_tex(thick, self.h)
        self.pages = pages_tex(thick, self.h - 4)
        self.top = pages_tex(thick, self.w - 4).transpose(1, 0, 2).copy()
        self.OW, self.OH, self.U = OW, OH, ui_scale
        self.cx, self.cy = OW * bx, OH * by
        self.t_out = t_out
        rng = np.random.default_rng(seed)
        self.dust = [(rng.uniform(-1, 1), rng.uniform(0, 1), rng.uniform(0.6, 1.4), rng.uniform(0, 6.28)) for _ in range(70)]
        self.sparks = [(rng.uniform(0, 2 * math.pi), rng.uniform(160, 460), rng.uniform(0.5, 1.0)) for _ in range(44)]
        self.orbit = [(rng.uniform(0, 2 * math.pi), rng.uniform(0.7, 1.3), rng.uniform(0.85, 1.15)) for _ in range(10)]
        self.grains = None
        self._c = {}

    # ---------------------------------------------------------------- 3D
    def _proj(self, P, S, yaw, pitch, roll, cx, cy):
        x, y, z = P[..., 0] * S, P[..., 1] * S, P[..., 2] * S
        cr, sr = math.cos(roll), math.sin(roll)
        x, y = x * cr - y * sr, x * sr + y * cr
        cyw, syw = math.cos(yaw), math.sin(yaw); cp, sp = math.cos(pitch), math.sin(pitch)
        x2 = x * cyw + z * syw; z2 = -x * syw + z * cyw
        y3 = y * cp - z2 * sp; z3 = y * sp + z2 * cp
        k = 1500.0 / (1500.0 + z3)
        return np.stack([cx + x2 * k, cy + y3 * k], -1), z3

    def _quad(self, img, tex, Q, shade=1.0, alpha=1.0):
        h, w = tex.shape[:2]
        x0, y0 = np.floor(Q.min(0)).astype(int); x1, y1 = np.ceil(Q.max(0)).astype(int)
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(self.OW, x1 + 1), min(self.OH, y1 + 1)
        if x1 - x0 < 2 or y1 - y0 < 2: return
        M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(Q - [x0, y0]))
        wp = cv2.warpPerspective(tex, M, (x1 - x0, y1 - y0), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        a = (wp[..., 3:4] / 255.0 * alpha).astype(np.float32)
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + wp[..., :3].astype(np.float32) / 255.0 * shade * a

    def pose(self, u):
        if u < 0.25: return None
        v = _o3((u - 0.25) / 1.1)
        cy = self.cy - (1 - v) * self.OH * 0.75
        yaw = (1 - v) * 2.5 * math.pi                                   # 1.25 turns, decelerating
        pitch = math.radians(10) * (1 - v)
        roll = math.radians(-8) * (1 - v)
        S = self.U * (0.62 + 0.38 * v)
        if u >= 1.35:
            lu = u - 1.35
            S *= 1 - 0.05 * math.exp(-lu * 9) * math.cos(lu * 30)
            S *= 1 + 0.08 * _sm(lu / 3.0)
            yaw = math.radians(3) * math.sin(lu * 1.1)
            cy += 4 * math.sin(lu * 2.0)
        return dict(S=S, yaw=yaw, pitch=pitch, roll=roll, cx=self.cx, cy=cy)

    def _draw_book(self, img, p, alpha=1.0):
        w, h, T = self.w, self.h, self.T
        X0, X1, Y0, Y1 = -w / 2, w / 2, -h / 2, h / 2
        zf, zb = -T / 2, T / 2
        S, yaw, pitch, roll, cx, cy = p['S'], p['yaw'], p['pitch'], p['roll'], p['cx'], p['cy']
        def Q(pts):
            q, z = self._proj(np.array(pts, np.float32), S, yaw, pitch, roll, cx, cy); return q, float(z.mean())
        L = np.array([-0.5, -0.6, -0.62]); L /= np.linalg.norm(L)
        def shade(n):
            # rotate the face normal by yaw (approx) and light it
            ny = n; nx = (n[0] * math.cos(yaw) + n[2] * math.sin(yaw), n[1], -n[0] * math.sin(yaw) + n[2] * math.cos(yaw))
            return 0.55 + 0.6 * max(0.0, -(nx[0] * L[0] + nx[1] * L[1] + nx[2] * L[2]))
        faces = [
            (self.front, [[X0, Y0, zf], [X1, Y0, zf], [X1, Y1, zf], [X0, Y1, zf]], (0, 0, -1)),
            (self.back[:, ::-1], [[X1, Y0, zb], [X0, Y0, zb], [X0, Y1, zb], [X1, Y1, zb]], (0, 0, 1)),
            (self.spine, [[X0, Y0, zb], [X0, Y0, zf], [X0, Y1, zf], [X0, Y1, zb]], (-1, 0, 0)),
            (self.pages, [[X1 - 1, Y0 + 2, zf + 1], [X1 - 1, Y0 + 2, zb - 1], [X1 - 1, Y1 - 2, zb - 1], [X1 - 1, Y1 - 2, zf + 1]], (1, 0, 0)),
        ]
        drawn = []
        for tex, pts, n in faces:
            q, z = Q(pts)
            # back-face cull with the projected winding (keeps perspective correct)
            area = 0.5 * sum(q[i][0] * q[(i + 1) % 4][1] - q[(i + 1) % 4][0] * q[i][1] for i in range(4))
            if area <= 2: continue
            drawn.append((z, tex, q, shade(n)))
        for z, tex, q, sh in sorted(drawn, key=lambda d: -d[0]):
            if tex is self.front: sh = max(sh, 1.0)
            self._quad(img, tex, q, sh, alpha)
        qf, _ = Q([[X0, Y0, zf], [X1, Y0, zf], [X1, Y1, zf], [X0, Y1, zf]])
        return qf

    # ---------------------------------------------------------------- frame
    def _cache(self, key, fn):
        if key not in self._c: self._c[key] = fn()
        return self._c[key]

    def frame(self, img, u, cv=None, gv=None):
        if u < 0: return img
        OW, OH = self.OW, self.OH
        out = _sm((u - self.t_out) / 0.7) if self.t_out is not None and u >= self.t_out else 0.0
        if out >= 1: return img
        dk = _sm(u / 0.45) * (1 - out)
        lit = _sm((u - 0.35) / 1.25)                                  # light slowly comes up after the dark beat
        if dk > 0:
            def vig():
                yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
                d = np.sqrt(((xx - self.cx) / (OW * 0.5)) ** 2 + ((yy - self.cy) / (OH * 0.62)) ** 2)
                return np.clip(1.12 - d, 0.12, 1.0)[..., None].astype(np.float32)
            img = img * (1 - dk * (1 - 0.16 * self._cache('vig', vig)))
        # soft pillar
        pk = lit * (1 - 0.6 * _sm((u - 1.8) / 1.4)) * (1 - out)
        if pk > 0:
            def pil():
                xs = np.arange(OW, dtype=np.float32); ys = np.arange(OH, dtype=np.float32)[:, None]
                prof = np.exp(-((xs - self.cx) / (OW * 0.07)) ** 2)[None, :] + 0.35 * np.exp(-((xs - self.cx) / (OW * 0.16)) ** 2)[None, :]
                vert = np.clip(1.2 - ys / (self.cy + OH * 0.3), 0, 1)
                return (prof * vert)[..., None] * GOLD_A
            img = img + self._cache('pil', pil) * 0.5 * pk * (0.35 + 0.65 * lit)
        p = self.pose(u)
        if p is not None:
            lu = u - 1.35
            # rays + halo behind (after landing)
            rk = _sm((u - 1.3) / 1.0) * (1 - out)
            if rk > 0:
                img = img + self._rays(u, p['cx'], p['cy']) * rk
                def halo():
                    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
                    return np.exp(-(((xx - self.cx) / (OW * 0.13)) ** 2 + ((yy - self.cy) / (OH * 0.26)) ** 2))[..., None] * GOLD_A
                img = img + self._cache('halo', halo) * (0.22 + 0.06 * math.sin(u * 2.4)) * rk
            # motion afterimages while spinning down
            if 0.9 < u < 1.3:
                for k, dt in ((0.18, 0.05), (0.1, 0.1)):
                    pp = self.pose(u - dt)
                    if pp is not None: self._draw_book(img, pp, alpha=k)
            if 0 <= lu < 1.1:
                def fm():
                    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
                    return np.exp(-(((xx - self.cx) / (OW * 0.2)) ** 2 + ((yy - self.cy) / (OH * 0.3)) ** 2))[..., None] * WHITE_A
                bloom = _sm(lu / 0.35) * (1 - _sm((lu - 0.35) / 0.75))
                img = img + self._cache('flash', fm) * 0.32 * bloom
            if out <= 0:
                bl = 0.12 + 0.88 * _sm((u - 0.5) / 0.95)
                if bl < 0.999:
                    tmp = img.copy(); quad = self._draw_book(tmp, p)
                    img = self._relight(img, tmp, quad, bl)
                else:
                    quad = self._draw_book(img, p)
            else:
                img, quad = self._dissolve(img, p, out, cv, gv)
            if gv is not None and out == 0 and u > 1.2:
                x0, y0 = (quad.min(0) / self.U).astype(int); x1, y1 = (quad.max(0) / self.U).astype(int)
                rk2 = _sm((u - 1.2) / 0.6)
                gv.rect(int(x0) - 2, int(y0) - 2, int(x1 - x0) + 4, 2, (255, 236, 190, int(150 * rk2)))
                gv.rect(int(x0) - 2, int(y1), int(x1 - x0) + 4, 2, (255, 236, 190, int(110 * rk2)))
                gv.rect(int(x0) - 2, int(y0), 2, int(y1 - y0), (255, 236, 190, int(130 * rk2)))
                gv.rect(int(x1), int(y0), 2, int(y1 - y0), (255, 236, 190, int(130 * rk2)))
            # shine sweep on the cover
            for s0 in (1.65, 3.85, 6.05):
                su = (u - s0) / 0.55
                if 0 <= su < 1 and out == 0:
                    x0, y0 = quad.min(0).astype(int); x1, y1 = quad.max(0).astype(int)
                    yy, xx = np.mgrid[y0:y1, x0:x1]
                    pos = x0 + su * ((x1 - x0) + (y1 - y0)) - (y1 - y0)
                    band = np.clip(1 - np.abs(xx - x0 - (yy - y0) * 0.45 - (pos - x0)) / 22, 0, 1)
                    m = cv2.fillConvexPoly(np.zeros((y1 - y0, x1 - x0), np.uint8), (quad - [x0, y0]).astype(np.int32), 1).astype(np.float32)
                    img[y0:y1, x0:x1] += (band * m)[..., None] * 0.35
            if cv is not None:
                # landing ring (pixel) + sparks
                if 0 <= lu < 0.6:
                    r = 40 + 190 * _o3(lu / 0.6); a = 1 - lu / 0.6
                    ucx, ucy = self.cx / self.U, (self.cy + self.h * self.U * 0.5) / self.U
                    for d in range(0, 360, 3):
                        x = ucx + math.cos(math.radians(d)) * r / 2; y = ucy + math.sin(math.radians(d)) * r * 0.14
                        cv.px(int(x), int(y), (255, 236, 180, int(255 * a)))
                        if gv is not None: gv.px(int(x), int(y), (255, 210, 120, int(255 * a)))
                if 0 <= lu < 1.0:
                    for ang, spd, life in self.sparks:
                        if lu > life: continue
                        d = spd * lu * (1 - lu / (2 * life))
                        by_ = self.cy + self.h * self.U * 0.5
                        x = (self.cx + math.cos(ang) * d) / self.U; y = (by_ - abs(math.sin(ang)) * d * 0.55 + 280 * lu * lu) / self.U
                        a = 1 - lu / life
                        cv.px(int(x), int(y), (255, 226, 140, int(255 * a)))
                        if gv is not None: gv.rect(int(x) - 1, int(y) - 1, 3, 3, (255, 200, 100, int(255 * a)))
                # glints orbiting the book after landing
                if lu > 0.2 and out < 1:
                    for ph, spd, rr in self.orbit:
                        a = ph + (u - 1.55) * 0.9 * spd
                        x = (self.cx + math.cos(a) * self.w * self.U * 0.85 * rr) / self.U
                        y = (p['cy'] + math.sin(a) * self.h * self.U * 0.42 * rr) / self.U
                        tw = 0.5 + 0.5 * math.sin(u * 5 + ph * 3)
                        col = (255, 236, 180, int(230 * tw * (1 - out) * min(1.0, (lu - 0.2) / 0.3)))
                        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)): cv.px(int(x) + dx, int(y) + dy, col)
                        if gv is not None: gv.rect(int(x) - 1, int(y) - 1, 3, 3, col)
        # dust in the pillar
        if pk > 0.05 and cv is not None:
            for dx, ph, spd, wob in self.dust:
                yv = (ph - u * 0.12 * spd) % 1.0
                x = (self.cx + dx * OW * 0.08 + 6 * math.sin(u * 1.3 + wob)) / self.U
                y = (OH * (0.05 + 0.9 * yv)) / self.U
                a = pk * (0.4 + 0.6 * math.sin(yv * math.pi))
                cv.px(int(x), int(y), (255, 230, 170, int(200 * a)))
                if gv is not None: gv.px(int(x), int(y), (255, 210, 120, int(150 * a)))
        return img

    def _relight(self, img, tmp, quad, k):
        """darken the freshly drawn book (its quad) by k (0 = black silhouette, 1 = fully lit)."""
        m = cv2.fillConvexPoly(np.zeros(img.shape[:2], np.uint8), quad.astype(np.int32), 1).astype(bool)
        out = img.copy(); out[m] = tmp[m] * k
        return out

    def _dissolve(self, img, p, k, cv, gv):
        """the book breaks into gold motes from the top down and drifts away."""
        tmp = np.zeros_like(img); m = np.zeros(img.shape[:2], np.float32)
        q = self._draw_book(tmp, p)
        x0, y0 = q.min(0).astype(int); x1, y1 = q.max(0).astype(int)
        cut = y0 + (y1 - y0) * (k * 1.25 - 0.1)                       # rows above `cut` are gone
        H = img.shape[0]
        rows = np.arange(H)[:, None]
        cell = self.U
        noise = self._cache('dn', lambda: np.random.default_rng(5).uniform(0, 1, (H // cell + 1, img.shape[1] // cell + 1)))
        nz = cv2.resize(noise, (img.shape[1], H), interpolation=cv2.INTER_NEAREST)
        keep = (rows > cut + (nz - 0.5) * 40).astype(np.float32)
        a = (tmp.sum(-1) > 0).astype(np.float32) * keep
        img = img * (1 - a[..., None]) + tmp * a[..., None]
        if cv is not None:
            rng = np.random.default_rng(int(k * 40))
            for _ in range(120):
                x = rng.uniform(x0, x1); y = cut + rng.uniform(-20, 10)
                life = rng.uniform(0, 1)
                yy = y - life * 120 * k; xx = x + math.sin(life * 6 + x) * 10
                aa = (1 - life) * (1 - k * 0.6)
                cv.px(int(xx / self.U), int(yy / self.U), (255, 226, 150, int(255 * aa)))
                if gv is not None: gv.rect(int(xx / self.U) - 1, int(yy / self.U) - 1, 3, 3, (255, 210, 120, int(200 * aa)))
        return img, q

    def _rays(self, u, cx, cy):
        key = int(u * 15)
        rc = self._c.setdefault('rays', {})
        if key in rc: return rc[key]
        q = 4; W, H = self.OW // q, self.OH // q
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        a = np.arctan2(yy - cy / q, xx - cx / q); d = np.sqrt((xx - cx / q) ** 2 + (yy - cy / q) ** 2)
        rot = key / 15 * 0.16
        r = ((0.5 + 0.5 * np.cos(a * 12 + rot * 12)) ** 8 + 0.5 * (0.5 + 0.5 * np.cos(a * 7 - rot * 9)) ** 10) * np.exp(-d / (W * 0.3)) * (d > 16)
        r = cv2.GaussianBlur(r, (0, 0), 1.6)
        r = cv2.resize(r, (self.OW, self.OH), interpolation=cv2.INTER_LINEAR)[..., None] * GOLD_A * 0.3
        if len(rc) > 64: rc.clear()
        rc[key] = r
        return r

    def sfx(self, bus, t0):
        from .audio import synth as Z, cues as Q
        Q.riser(bus, t0 + 0.4, t0 + 1.33, gain=0.05, f0=300, f1=5000)
        bus.add(Z.whoosh(1.0, 2600, 500, 1.0, 11), t0 + 0.3, 0.05)
        bus.add(Z.thud(1.0, True, 8, 100, 40), t0 + 1.35, 0.2)
        Q.crash(bus, t0 + 1.35, 0.04, d=1.8)
        Q.shimmer(bus, t0 + 1.4, 1.6, 0.4)
        Q.sparkle(bus, t0 + 1.65, 0.6, 0.02)
        if self.t_out is not None:
            Q.shimmer(bus, t0 + self.t_out, 1.0, 0.35)
            bus.add(Z.whoosh(0.7, 800, 4000, 0.7, 12), t0 + self.t_out, 0.03)
