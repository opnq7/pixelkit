"""pixelkit.bookreveal - 书本出场动画（001《深度工作》沉淀；每期换封面即可复用）。

    from pixelkit.bookreveal import BookReveal
    BR = BookReveal(cover_rgba, title='深度工作', sub='Deep Work', small='卡尔·纽波特  著')   # cover_rgba：UI 网格上的像素书（含书页厚度）
    img = BR.frame(img, t - t0, cv=cv, gv=gv)     # 叠在任何画面上；cv / gv = 本帧的 UI 画布 / 辉光画布（hud.compose 合成）
    BR.dock(cv, gv, t - t0)                        # 收起后停靠在左上角的「本期书目」小书（之后每帧都画）
    BR.sfx(bus, t0)                                # 配套音效（pixelkit.audio）

时间（相对 t0，秒）：
    0.00–0.30  画面压暗 + 暗角收紧
    0.08–0.50  一道光柱从顶上落下，金尘往上飘
    0.25–1.35  书在光柱里旋转下落（1.5 圈，减速），远小近大
    1.35       落定：冲击光环 + 金色碎光 + 白闪 + 轻震
    1.35–      悬浮轻摆、背后光芒慢转、推镜 1.00→1.10
    1.65       封面斜向扫光；标题（金色衬线字）在右侧揭晓
    out        BR.t_out 开始收起：书缩小飞到左上角停靠、标题淡出、暗场恢复（0.55 s）
布局：书在画面 38% 处，标题块在 70% 处（让出底部字幕区）。
"""
import math
import numpy as np
import cv2
from .core import C
from .ui import _a

GOLD_A = np.array((1.0, 0.82, 0.45), np.float32)
WHITE_A = np.array((1.0, 0.97, 0.9), np.float32)


def _smooth(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def _out3(u): u = max(0.0, min(1.0, u)); return 1 - (1 - u) ** 3


def make_back(cover):
    """book back cover in the same size: deep navy, gold double frame, a small gold emblem."""
    h, w = cover.shape[:2]
    b = np.zeros_like(cover)
    m = cover[..., 3] > 0
    b[m] = (30, 34, 66, 255)
    ys, xs = np.nonzero(m); y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    b[y0:y1 + 1, x0] = b[y0:y1 + 1, x1] = (20, 16, 30, 255); b[y0, x0:x1 + 1] = b[y1, x0:x1 + 1] = (20, 16, 30, 255)
    for i, c in ((3, (214, 172, 90, 255)), (5, (150, 112, 50, 255))):
        b[y0 + i, x0 + i:x1 - i] = c; b[y1 - i, x0 + i:x1 - i] = c; b[y0 + i:y1 - i, x0 + i] = c; b[y0 + i:y1 - i, x1 - i] = c
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    for dy in range(-6, 7):
        ww = 6 - abs(dy)
        b[cy + dy, cx - ww:cx + ww + 1] = (230, 190, 100, 255)
    for dy in range(-3, 4):
        ww = 3 - abs(dy)
        b[cy + dy, cx - ww:cx + ww + 1] = (30, 34, 66, 255)
    return b


class BookReveal:
    def __init__(self, cover, title='', sub='', small='', OW=1920, OH=1080, ui_scale=4, bx=0.38, by=0.45, title_x=0.70,
                 t_out=None, dock=(26, 22), dock_scale=0.28, seed=3, title_at=1.6):
        self.cover = cover; self.back = make_back(cover)
        self.OW, self.OH, self.U = OW, OH, ui_scale
        self.bx, self.by = bx, by
        self.title_x = title_x
        self.t_out = t_out
        self.title_at = title_at
        self.dock_xy, self.dock_s = dock, dock_scale
        self.title = None
        if title:
            from .titles import TitleCard
            self.TW = int(OW * 0.52)
            self.title = TitleCard(title, sub, small, OW=self.TW, OH=OH, title_px=150, sub_px=50, small_px=30, y=by - 0.02, seed=seed)
        rng = np.random.default_rng(seed)
        self.dust = [(rng.uniform(-1, 1), rng.uniform(0, 1), rng.uniform(0.6, 1.4), rng.uniform(0, 6.28)) for _ in range(70)]
        self.sparks = [(rng.uniform(0, 2 * math.pi), rng.uniform(140, 420), rng.uniform(0.5, 1.0)) for _ in range(40)]

    # ------------------------------------------------------------ state
    def state(self, u):
        """u = t - t0 -> dict(y, angle, scale, alive)."""
        cy = self.by * self.OH
        if u < 0.25: return None
        if u < 1.35:
            v = _out3((u - 0.25) / 1.1)
            y = -self.OH * 0.35 + (cy + self.OH * 0.35) * v
            ang = (1 - v) * 3 * math.pi
            sc = 0.55 + 0.45 * v
            return dict(y=y, ang=ang, sc=sc)
        bob = 4 * math.sin((u - 1.35) * 2.2) * min(1.0, (u - 1.35) / 0.4)
        push = 1.0 + 0.10 * _smooth((u - 1.35) / 3.0)
        land = 1.0 - 0.06 * math.exp(-(u - 1.35) * 10) * math.cos((u - 1.35) * 32)
        return dict(y=cy + bob, ang=0.0, sc=push * land)

    # ------------------------------------------------------------ draw
    def _book_img(self, ang, sc):
        c = math.cos(ang)
        src = self.cover if c >= 0 else self.back
        h, w = src.shape[:2]
        S = self.U * sc
        H2, W2 = max(2, int(round(h * S))), max(2, int(round(w * S)))
        big = cv2.resize(src, (W2, H2), interpolation=cv2.INTER_NEAREST)
        cw = max(1, int(round(W2 * abs(c))))
        sq = cv2.resize(big, (cw, H2), interpolation=cv2.INTER_NEAREST)
        shade = 0.55 + 0.45 * abs(c)
        sq = sq.astype(np.float32); sq[..., :3] *= shade
        if abs(c) < 0.22:                                           # spine
            sw = max(2, int(round(7 * S * (1 - abs(c) / 0.22) + 2)))
            sp = np.zeros((H2, sw, 4), np.float32); sp[..., 3] = 255
            sp[..., :3] = (36, 40, 78)
            for yy in range(int(H2 * 0.15), int(H2 * 0.85), max(2, int(S * 6))): sp[yy:yy + max(1, int(S)), :, :3] = (214, 172, 90)
            sq = sp if cw < sw else np.concatenate([sp, sq], 1)
        return sq

    def frame(self, img, u, cv=None, gv=None):
        OW, OH = self.OW, self.OH
        if u < 0: return img
        out_k = 0.0
        if self.t_out is not None and u >= self.t_out: out_k = _smooth((u - self.t_out) / 0.55)
        # dim + vignette
        dk = _smooth(u / 0.3) * (1 - out_k)
        if dk > 0:
            yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32) if not hasattr(self, '_vig') else (None, None)
            if not hasattr(self, '_vig'):
                d = np.sqrt(((xx - OW * self.bx) / (OW * 0.55)) ** 2 + ((yy - OH * self.by) / (OH * 0.7)) ** 2)
                self._vig = np.clip(1.15 - d, 0.15, 1.0)[..., None].astype(np.float32)
            img = img * (1 - dk * (1 - 0.32 * self._vig))
        cx = OW * self.bx
        # light pillar
        pk = _smooth((u - 0.08) / 0.4) * (1 - 0.6 * _smooth((u - 1.6) / 1.2)) * (1 - out_k)
        if pk > 0:
            if not hasattr(self, '_pillar'):
                xs = np.arange(OW, dtype=np.float32)
                prof = np.exp(-((xs - cx) / (OW * 0.075)) ** 2)[None, :]
                ys = np.arange(OH, dtype=np.float32)[:, None]
                vert = np.clip(1.15 - ys / (OH * self.by + OH * 0.25), 0, 1)
                self._pillar = (prof * vert)[..., None] * GOLD_A
            img = img + self._pillar * 0.55 * pk
        st = self.state(u)
        if st is not None and out_k < 1:
            # rays behind (after landing)
            rk = _smooth((u - 1.3) / 0.5) * (1 - out_k)
            if rk > 0: img = img + self._rays(u, cx, st['y']) * rk
            # shockwave + flash
            lu = u - 1.35
            if 0 <= lu < 0.6 and cv is not None:
                r = 30 + 160 * _out3(lu / 0.6)
                a = 1 - lu / 0.6
                ucx, ucy = cx / self.U, st['y'] / self.U + 30
                for d in range(0, 360, 3):
                    x = ucx + math.cos(math.radians(d)) * r / 2; y = ucy + math.sin(math.radians(d)) * r * 0.16
                    cv.px(int(x), int(y), (255, 236, 180, int(255 * a)))
                    if gv is not None: gv.px(int(x), int(y), (255, 210, 120, int(255 * a)))
            if 0 <= lu < 0.14:                                       # flash: warm, radial around the book
                if not hasattr(self, '_flashm'):
                    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
                    self._flashm = np.exp(-(((xx - cx) / (OW * 0.22)) ** 2 + ((yy - OH * self.by) / (OH * 0.3)) ** 2))[..., None] * WHITE_A
                img = img + self._flashm * 0.75 * (1 - lu / 0.14)
            # sparks burst
            if 0 <= lu < 1.0 and cv is not None:
                for ang, spd, life in self.sparks:
                    if lu > life: continue
                    d = spd * lu * (1 - lu / (2 * life))
                    x = (cx + math.cos(ang) * d) / self.U; y = (st['y'] + math.sin(ang) * d * 0.7 + 260 * lu * lu) / self.U
                    a = 1 - lu / life
                    cv.rect(int(x), int(y), 1, 1, (255, 226, 140, int(255 * a)))
                    if gv is not None: gv.rect(int(x) - 1, int(y) - 1, 3, 3, (255, 200, 100, int(255 * a)))
            # the book (flying to the dock on the way out)
            bimg = self._book_img(st['ang'], st['sc'] * (1 - out_k * (1 - self.dock_s)))
            bx = cx + (self.dock_xy[0] * self.U + 30 - cx) * out_k
            by_ = st['y'] + (self.dock_xy[1] * self.U + 40 - st['y']) * out_k
            img = self._paste(img, bimg, bx, by_)
            # cover shine
            su = (u - self.title_at - 0.05) / 0.55
            if 0 <= su < 1 and abs(st['ang']) < 0.01 and out_k == 0:
                h, w = bimg.shape[:2]
                x0 = int(bx - w / 2); y0 = int(by_ - h / 2)
                band = np.zeros((h, w), np.float32)
                yy, xx = np.mgrid[0:h, 0:w]
                pos = su * (w + h) - h
                band = np.clip(1 - np.abs(xx - yy * 0.45 - pos) / 26, 0, 1) * (bimg[..., 3] > 0)
                sub = img[max(0, y0):y0 + h, max(0, x0):x0 + w]
                bb = band[max(0, -y0):max(0, -y0) + sub.shape[0], max(0, -x0):max(0, -x0) + sub.shape[1]]
                sub += bb[..., None] * 0.45
        # dust motes rising in the pillar
        if pk > 0.05 and cv is not None:
            for dx, ph, spd, wob in self.dust:
                yv = (ph - u * 0.12 * spd) % 1.0
                x = (cx + dx * OW * 0.07 + 6 * math.sin(u * 1.3 + wob)) / self.U
                y = (OH * (0.1 + 0.85 * yv)) / self.U
                a = pk * (0.4 + 0.6 * math.sin(yv * math.pi))
                cv.px(int(x), int(y), (255, 230, 170, int(200 * a)))
                if gv is not None: gv.px(int(x), int(y), (255, 210, 120, int(160 * a)))
        # title
        if self.title is not None and u >= self.title_at:
            tt = u - self.title_at
            f = self.title.frame(tt, dur=99, fade_out=0.25)
            k = (1 - out_k) ** 2
            x0 = int(OW * self.title_x - self.TW / 2)
            reg = img[:, x0:x0 + self.TW]
            ff = np.clip(f[:, :reg.shape[1]], 0, 1) * k
            al = np.clip(ff.max(-1, keepdims=True) * 2.2, 0, 1) * k
            img[:, x0:x0 + self.TW] = reg * (1 - al) + ff
        return img

    def _rays(self, u, cx, cy):
        if not hasattr(self, '_rayc'):
            self._rayc = {}
        key = int(u * 15)
        if key in self._rayc: return self._rayc[key]
        q = 4
        W, H = self.OW // q, self.OH // q
        r = np.zeros((H, W), np.float32)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        a = np.arctan2(yy - cy / q, xx - cx / q)
        d = np.sqrt((xx - cx / q) ** 2 + (yy - cy / q) ** 2)
        rot = key / 15 * 0.18
        r = (0.5 + 0.5 * np.cos(a * 14 + rot * 14)) ** 6 * np.exp(-d / (W * 0.28)) * (d > 18)
        r = cv2.GaussianBlur(r, (0, 0), 1.5)
        r = cv2.resize(r, (self.OW, self.OH), interpolation=cv2.INTER_LINEAR)[..., None] * GOLD_A * 0.42
        if len(self._rayc) > 64: self._rayc.clear()
        self._rayc[key] = r
        return r

    def _paste(self, img, spr, cx, cy):
        h, w = spr.shape[:2]
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
        X0, Y0 = max(0, x0), max(0, y0); X1, Y1 = min(self.OW, x0 + w), min(self.OH, y0 + h)
        if X1 <= X0 or Y1 <= Y0: return img
        s = spr[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
        a = (s[..., 3:4] / 255.0).astype(np.float32)
        # soft drop shadow
        sh = np.zeros_like(img[..., :1])
        img[Y0:Y1, X0:X1] = img[Y0:Y1, X0:X1] * (1 - a) + (s[..., :3] / 255.0) * a
        return img

    def dock(self, cv, gv, u, label='本期书目'):
        """small docked book (top-left) after the outro."""
        if self.t_out is None or u < self.t_out + 0.55: return
        k = _smooth((u - self.t_out - 0.55) / 0.2)
        h = 30; w = int(self.cover.shape[1] * h / self.cover.shape[0])
        small = cv2.resize(self.cover, (w, h), interpolation=cv2.INTER_AREA)
        x, y = self.dock_xy[0] + 4 - w // 2, self.dock_xy[1] - h // 2 + 6
        cv.blit(small, x, y, k)
        if gv is not None: gv.rect(x - 1, y - 1, w + 2, h + 2, (255, 210, 120, int(60 * k)))

    def sfx(self, bus, t0):
        from .audio import synth as Z, cues as Q
        Q.riser(bus, t0 + 0.05, t0 + 1.3, gain=0.05, f0=300, f1=5000)
        bus.add(Z.whoosh(1.0, 2600, 500, 1.0, 11), t0 + 0.3, 0.05)
        bus.add(Z.thud(1.0, True, 8, 100, 40), t0 + 1.35, 0.2)
        Q.crash(bus, t0 + 1.35, 0.05, d=1.8)
        Q.shimmer(bus, t0 + 1.4, 1.6, 0.4)
        Q.title_sting(bus, t0 + 1.62, 0.45, chord=('C3', 'G3', 'C4', 'E4', 'G4'))
        Q.sparkle(bus, t0 + 1.65, 0.6, 0.02)
