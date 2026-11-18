"""pixelkit.bookreveal - 书本出场 v2：真 3D 透视的像素书（001《深度工作》沉淀；每期换封面复用）。v1 在 bookreveal_v1.py。

    from pixelkit.bookreveal import BookReveal
    BR = BookReveal(cover_px, t_out=...)            # cover_px：像素化封面 RGB(A)（UI 网格大小，例 81x118）
    img = BR.frame(img, u, cv, gv)                  # u = t - t0；叠在任何画面上（cv / gv = 本帧 UI / 辉光画布，hud.compose 合成）
    BR.dock(cv, gv, u)                              # 收起后停靠在左上角的「本期书目」
    BR.sfx(bus, t0)                                 # 配套音效

时间（u，秒）：
    0.00–0.35  压暗 + 暗角；pixelfx holy/holy-pillar：顶上开出一轮光、光束汇聚到落点、地面法阵亮起
    0.30–1.40  书带着 58° 偏转、轻微俯仰从光里降下，减速落定（透视翻正）
    1.40       落定：书轻弹、碎光
    1.65–2.35  封面向左打开（绕书脊转到 165°），书页透出暖光
    2.05–2.75  三页纸快速翻过
    2.2–3.6    金色光粒从书页升起
    close_at   封面合上（默认 3.7）
    t_out      缩小飞到左上角停靠（0.55 s）
所有部件都是贴图四边形 + 透视投影（cv2.warpPerspective 最近邻），像素保持方块，3D 感来自透视与分面明暗。
"""
import math
import numpy as np
import cv2

WARM = np.array((1.0, 0.88, 0.62), np.float32)


def _sm(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def _o3(u): u = max(0.0, min(1.0, u)); return 1 - (1 - u) ** 3
def _io(u): u = max(0.0, min(1.0, u)); return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def _page_tex(w, h, seed=0):
    rng = np.random.default_rng(seed)
    t = np.zeros((h, w, 4), np.uint8); t[..., 3] = 255
    t[..., :3] = (238, 228, 204)
    t[:, :2, :3] = (214, 200, 172)
    for y in range(10, h - 8, 6):
        t[y, 6:w - 5, :3] = (206, 212, 226)
        x = 7
        for _ in range(int(rng.integers(2, 5))):
            L = int(rng.integers(6, 18))
            if x + L > w - 6: break
            t[y - 2, x:x + L, :3] = (120, 112, 120); x += L + int(rng.integers(2, 5))
    t[0, :, :3] = t[-1, :, :3] = (180, 166, 140); t[:, -1, :3] = (190, 176, 150)
    return t


def _inner_cover(w, h):
    t = np.zeros((h, w, 4), np.uint8); t[..., 3] = 255
    t[..., :3] = (34, 40, 78)
    for y in range(0, h, 4):
        for x in range((y // 4) % 2 * 2, w, 4): t[y, x, :3] = (52, 60, 104)
    t[2:-2, 2, :3] = t[2:-2, -3, :3] = (190, 150, 80); t[2, 2:-2, :3] = t[-3, 2:-2, :3] = (190, 150, 80)
    return t


def make_back(w, h):
    b = np.zeros((h, w, 4), np.uint8); b[..., 3] = 255; b[..., :3] = (30, 34, 66)
    for i, c in ((3, (214, 172, 90)), (5, (150, 112, 50))):
        b[i, i:w - i, :3] = c; b[h - 1 - i, i:w - i, :3] = c; b[i:h - i, i, :3] = c; b[i:h - i, w - 1 - i, :3] = c
    cx, cy = w // 2, h // 2
    for dy in range(-6, 7):
        ww = 6 - abs(dy); b[cy + dy, cx - ww:cx + ww + 1, :3] = (230, 190, 100)
    for dy in range(-3, 4):
        ww = 3 - abs(dy); b[cy + dy, cx - ww:cx + ww + 1, :3] = (30, 34, 66)
    return b


class BookReveal:
    def __init__(self, cover, OW=1920, OH=1080, ui_scale=4, bx=0.5, by=0.46, t_out=None, close_at=3.7,
                 dock=(26, 22), dock_scale=0.25, seed=3, open_book=True, pillar=True, **_):
        c = cover if cover.shape[2] == 4 else np.dstack([cover, np.full(cover.shape[:2], 255, np.uint8)])
        self.cover = c
        self.h, self.w = c.shape[:2]
        self.back = make_back(self.w, self.h)
        self.inner = _inner_cover(self.w, self.h)
        self.pages = [_page_tex(self.w - 2, self.h - 4, s) for s in range(5)]
        self.OW, self.OH, self.U = OW, OH, ui_scale
        self.cx, self.cy = OW * bx, OH * by
        self.t_out, self.close_at = t_out, close_at
        self.dock_xy, self.dock_s = dock, dock_scale
        self.open_book, self.pillar = open_book, pillar
        rng = np.random.default_rng(seed)
        self.motes = [(rng.uniform(-1, 1), rng.uniform(0, 1), rng.uniform(0.5, 1.3), rng.uniform(0, 6.28), int(rng.integers(0, 4))) for _ in range(46)]
        self.dust = [(rng.uniform(0, 2 * math.pi), rng.uniform(60, 220), rng.uniform(0.5, 1.0)) for _ in range(34)]
        self._fx = None; self._vig = None; self._xy = None

    def _proj(self, P, S, yaw, pitch, cx, cy):
        x, y, z = P[..., 0] * S, P[..., 1] * S, P[..., 2] * S
        cyw, syw = math.cos(yaw), math.sin(yaw); cp, sp = math.cos(pitch), math.sin(pitch)
        x2 = x * cyw + z * syw; z2 = -x * syw + z * cyw
        y3 = y * cp - z2 * sp; z3 = y * sp + z2 * cp
        k = 1250.0 / (1250.0 + z3)
        return np.stack([cx + x2 * k, cy + y3 * k], -1)

    def _quad(self, img, tex, Q, shade=1.0, alpha=1.0):
        h, w = tex.shape[:2]
        x0, y0 = np.floor(Q.min(0)).astype(int); x1, y1 = np.ceil(Q.max(0)).astype(int)
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(self.OW, x1 + 1), min(self.OH, y1 + 1)
        if x1 - x0 < 2 or y1 - y0 < 2: return
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        M = cv2.getPerspectiveTransform(src, np.float32(Q - [x0, y0]))
        wp = cv2.warpPerspective(tex, M, (x1 - x0, y1 - y0), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        a = (wp[..., 3:4] / 255.0 * alpha).astype(np.float32)
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + wp[..., :3].astype(np.float32) / 255.0 * shade * a

    def pose(self, u):
        if u < 0.3: return None
        out_k = _sm((u - self.t_out) / 0.55) if self.t_out is not None and u >= self.t_out else 0.0
        v = _o3((u - 0.3) / 1.1)
        cy = self.cy - (1 - v) * self.OH * 0.62
        yaw = (1 - v) * math.radians(58)
        pitch = math.radians(14) * (1 - v) + math.radians(6)
        S = self.U * (0.7 + 0.3 * v)
        if u >= 1.4:
            lu = u - 1.4
            S *= 1 + 0.035 * math.exp(-lu * 8) * math.cos(lu * 26)
            S *= 1 + 0.07 * _sm(lu / 3.5)
            yaw = math.radians(5) * math.sin(lu * 0.9)
            cy += 3 * math.sin(lu * 2.1)
        op = _io((u - 1.65) / 0.7) * (1 - _io((u - self.close_at) / 0.5)) if self.open_book else 0.0
        pitch += math.radians(34) * op
        cx_shift = self.w * self.U * 0.42 * op
        flips = [_io((u - (2.05 + i * 0.22)) / 0.45) * (1 - _io((u - self.close_at + 0.1) / 0.4)) for i in range(3)] if self.open_book else []
        cx = self.cx + cx_shift
        if out_k > 0:
            S *= 1 - out_k * (1 - self.dock_s)
            cx = cx + (self.dock_xy[0] * self.U + 20 - cx) * out_k
            cy = cy + (self.dock_xy[1] * self.U + 34 - cy) * out_k
            op *= (1 - out_k)
        return dict(S=S, yaw=yaw, pitch=pitch, cx=cx, cy=cy, open=op, flips=flips, out=out_k)

    def _draw_book(self, img, p):
        w, h, T = self.w, self.h, 7.0
        S, yaw, pitch, cx, cy = p['S'], p['yaw'], p['pitch'], p['cx'], p['cy']
        X0, X1, Y0, Y1 = -w / 2, w / 2, -h / 2, h / 2
        zf, zb = -T / 2, T / 2
        Q = lambda pts: self._proj(np.array(pts, np.float32), S, yaw, pitch, cx, cy)
        self._quad(img, self.back, Q([[X0, Y0, zb], [X1, Y0, zb], [X1, Y1, zb], [X0, Y1, zb]]), 0.55)
        edge = np.zeros((h, 6, 4), np.uint8); edge[..., 3] = 255; edge[..., :3] = (226, 214, 190); edge[::2, :, :3] = (204, 190, 164)
        if math.sin(yaw) > -0.05:
            self._quad(img, edge, Q([[X1 - 1, Y0 + 1, zf], [X1 - 1, Y0 + 1, zb], [X1 - 1, Y1 - 1, zb], [X1 - 1, Y1 - 1, zf]]), 0.9)
        bot = np.zeros((6, w, 4), np.uint8); bot[..., 3] = 255; bot[..., :3] = (210, 198, 172); bot[:, ::2, :3] = (190, 176, 150)
        self._quad(img, bot, Q([[X0 + 1, Y1 - 1, zf], [X1 - 1, Y1 - 1, zf], [X1 - 1, Y1 - 1, zb], [X0 + 1, Y1 - 1, zb]]), 0.7)
        op = p['open']
        if op > 0.02:
            self._quad(img, self.pages[0], Q([[X0 + 1, Y0 + 2, zf + 0.6], [X1 - 1, Y0 + 2, zf + 0.6], [X1 - 1, Y1 - 2, zf + 0.6], [X0 + 1, Y1 - 2, zf + 0.6]]), 0.95 + 0.1 * op)
            for i, fk in enumerate(p['flips']):
                if fk <= 0.01 or fk >= 0.99: continue
                th = fk * math.pi
                pts = [[X0 + (xx - X0) * math.cos(th), yy, zf + 0.5 - (xx - X0) * math.sin(th) * 0.45]
                       for (xx, yy) in ((X0, Y0 + 2), (X1 - 1, Y0 + 2), (X1 - 1, Y1 - 2), (X0, Y1 - 2))]
                tex = self.pages[1 + i] if th < math.pi / 2 else self.pages[1 + i][:, ::-1]
                self._quad(img, tex, Q(pts), 0.85 + 0.3 * abs(math.cos(th)))
        th = op * math.radians(165)
        pts = [[X0 + (xx - X0) * math.cos(th), yy, zf - (xx - X0) * math.sin(th)] for (xx, yy) in ((X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1))]
        front = th < math.pi / 2
        shade = (0.6 + 0.4 * abs(math.cos(th))) if front else (0.55 + 0.35 * abs(math.cos(th)))
        self._quad(img, self.cover if front else self.inner[:, ::-1], Q(pts), shade)
        return Q([[X0, Y0, zf], [X1, Y0, zf], [X1, Y1, zf], [X0, Y1, zf]])

    def frame(self, img, u, cv=None, gv=None):
        if u < 0: return img
        OW, OH = self.OW, self.OH
        out_k = _sm((u - self.t_out) / 0.55) if self.t_out is not None and u >= self.t_out else 0.0
        dk = _sm(u / 0.35) * (1 - out_k)
        if dk > 0:
            if self._vig is None:
                yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
                d = np.sqrt(((xx - self.cx) / (OW * 0.5)) ** 2 + ((yy - self.cy) / (OH * 0.62)) ** 2)
                self._vig = np.clip(1.1 - d, 0.12, 1.0)[..., None].astype(np.float32)
            img = img * (1 - dk * (1 - 0.3 * self._vig))
        if self.pillar and cv is not None and out_k < 1:
            if self._fx is None:
                from . import pfx
                self._fx = pfx.FX('holy/holy-pillar')
            lx, ly = self.cx / self.U, (self.cy + self.h * self.U * 0.5 + 8) / self.U
            if u < self._fx.duration:
                self._fx.draw(cv, u, lx, ly, alpha=1 - out_k)
                if gv is not None: self._fx.draw(gv, u, lx, ly, alpha=0.6 * (1 - out_k))
        p = self.pose(u)
        if p is None: return img
        op = p['open']
        if op > 0.02:
            if self._xy is None: self._xy = np.mgrid[0:OH, 0:OW].astype(np.float32)
            yy, xx = self._xy
            g = np.exp(-(((xx - p['cx']) / (OW * 0.16)) ** 2 + ((yy - p['cy'] + OH * 0.05) / (OH * 0.26)) ** 2))[..., None] * WARM
            img = img + g * 0.22 * op
        quad = self._draw_book(img, p)
        if op > 0.02 and gv is not None:
            bx0, by0 = (quad.min(0) / self.U).astype(int); bx1, by1 = (quad.max(0) / self.U).astype(int)
            gv.rect(int(bx0) + 4, int(by0) + 4, max(1, int(bx1 - bx0) - 8), max(1, int(by1 - by0) - 8), (255, 214, 140, int(40 * op)))
        if cv is not None and u > 2.2 and out_k < 1:
            for dx, ph, spd, wob, kind in self.motes:
                a0 = 2.2 + ph * 1.2
                if u < a0: continue
                life = (u - a0) * 0.45 * spd
                if life > 1: continue
                x = (p['cx'] + dx * self.w * self.U * 0.45 + 18 * math.sin(u * 1.6 + wob)) / self.U
                y = (p['cy'] - life * OH * 0.42) / self.U
                a = (1 - life) * (1 - out_k) * min(1.0, op * 2 + 0.2)
                col = (255, 226, 150, int(255 * a))
                cv.px(int(x), int(y), col)
                if kind == 0:
                    for ddx, ddy in ((-1, 0), (1, 0), (0, -1), (0, 1)): cv.px(int(x) + ddx, int(y) + ddy, col)
                if gv is not None: gv.rect(int(x) - 1, int(y) - 1, 3, 3, col)
        lu = u - 1.4
        if 0 <= lu < 1.0 and cv is not None:
            ly = (self.cy + self.h * self.U * 0.5) / self.U
            for ang, spd, life in self.dust:
                if lu > life: continue
                d = spd * lu * (1 - lu / (2 * life)) / self.U
                x = self.cx / self.U + math.cos(ang) * d; y = ly + math.sin(ang) * d * 0.25 - 20 * lu
                a = 1 - lu / life
                cv.px(int(x), int(y), (255, 236, 190, int(220 * a)))
                if gv is not None: gv.px(int(x), int(y), (255, 210, 130, int(200 * a)))
        return img

    def dock(self, cv, gv, u, label=None):
        if self.t_out is None or u < self.t_out + 0.55: return
        k = _sm((u - self.t_out - 0.55) / 0.2)
        h = 30; w = int(self.w * h / self.h)
        small = cv2.resize(self.cover, (w, h), interpolation=cv2.INTER_AREA)
        x, y = self.dock_xy[0] + 4 - w // 2, self.dock_xy[1] - h // 2 + 6
        cv.rect(x - 1, y - 1, w + 2, h + 2, (20, 16, 30, int(255 * k)))
        cv.blit(small, x, y, k)
        if gv is not None: gv.rect(x - 2, y - 2, w + 4, h + 4, (255, 210, 120, int(50 * k)))

    def sfx(self, bus, t0):
        from .audio import synth as Z, cues as Q
        Q.riser(bus, t0 + 0.1, t0 + 1.35, gain=0.045, f0=300, f1=4500)
        Q.shimmer(bus, t0 + 0.25, 1.2, 0.35)
        bus.add(Z.whoosh(1.0, 2400, 500, 0.8, 11), t0 + 0.35, 0.04)
        bus.add(Z.thud(0.8, True, 8, 100, 42), t0 + 1.4, 0.14)
        Q.sparkle(bus, t0 + 1.42, 0.6, 0.02)
        if self.open_book:
            Q.paper_flip(bus, t0 + 1.7, 0.6)
            for i in range(3): Q.paper_flip(bus, t0 + 2.1 + i * 0.22, 0.35)
            Q.shimmer(bus, t0 + 1.8, 1.6, 0.4)
            Q.paper_flip(bus, t0 + self.close_at + 0.25, 0.5)
            bus.add(Z.thud(0.4, False, 9, 160, 80), t0 + self.close_at + 0.45, 0.06)
