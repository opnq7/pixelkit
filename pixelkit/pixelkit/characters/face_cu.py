"""pixelkit.characters.face_cu - 熬夜脸大特写（v0.13，vec.Painter 原生绘制，320x180 舞台尺度，头宽约 120 美术像素）。

视角 = 手机前置摄像头看你：平躺、脸朝上、头发散在枕头上、屏幕的冷光从上方打下来。
所有参数连续，可直接做表演曲线：

    from pixelkit.characters import face_cu as FC
    spr = FC.sleeper_face(lid=0.35, look=(0, -2), red=0.6, mouth='flat', tilt=0, reflect=feed_rgb)
    st.sprite(spr.cv.a, x - spr.ax, y - spr.ay, E=spr.E)

lid    0 = 睁眼，1 = 闭眼，<0 = 吓醒瞪大（-0.3）
look   (dx, dy) 眼珠偏移（美术像素）
pupil  瞳孔大小倍率（惊醒时 0.6）
red    0..1 血丝
bags   0..1 黑眼圈
mouth  'flat' | 'o' | 'open' | 'drool' | 'smile' | 'grit'
dead   True -> X 眼
reflect  None 或 (h, w, 3) uint8 小图：眼珠里的屏幕倒影（会跟着刷视频变化）
"""
import math
import numpy as np
from ..core import C
from ..vec import Painter, rrect, ellipse, circle, seg, arc, poly_stroke, union, sub

SKIN = [C('#7a4a3a'), C('#b06e52'), C('#d8946c'), C('#eeb48a'), C('#f8cfa8'), C('#fde4c8')]
HAIR = [C('#0c0a14'), C('#171424'), C('#221e34'), C('#302a46'), C('#463e62')]
INK = C('#2a1218')
BAG = C('#7a4a7a')

def sleeper_face(lid=0.0, look=(0, 0), pupil=1.0, red=0.0, bags=0.8, mouth='flat', dead=False, tilt=0.0, dy=0.0,
                 squash=0.0, reflect=None, sweat=0.0, brow=0.0, seed=4, light=(0.0, -0.6, 0.8)):
    W, H = 170, 150
    p = Painter(W, H)
    cx, cy = W / 2, 78 + dy
    rx, ry = 58.0, 52.0 * (1 - squash)
    with p.frame(rot=tilt, cx=cx, cy=cy + 30):
        u, v = p.uv()
        rng = np.random.RandomState(seed)
        # ---- hair spread on the pillow (behind the head): radiating locks
        locks = np.zeros((H, W), bool)
        for i in range(15):
            a = math.radians(-170 + i * (160 / 14) + rng.uniform(-5, 5))
            L = rng.uniform(16, 26)
            bx, by = cx + math.cos(a) * rx * 0.86, cy + math.sin(a) * ry * 0.86
            tip = (bx + math.cos(a) * L, by + math.sin(a) * L)
            pa = a + math.pi / 2
            locks |= p.poly([(bx + math.cos(pa) * 9, by + math.sin(pa) * 9), (bx - math.cos(pa) * 9, by - math.sin(pa) * 9), tip])
        p.part(locks, HAIR, bevel=4, light=light, amb=0.15, ink=C('#05040a'), bias=-0.05)
        # ---- ears
        for sgn in (-1, 1):
            ed = ellipse(u, v, cx + sgn * (rx - 2), cy + 8, 7, 10)
            p.part(ed, SKIN, bevel=3, light=light, amb=0.25, ink=INK, bias=-0.08)
            p.fill(ellipse(u, v, cx + sgn * (rx - 1), cy + 9, 3, 5), SKIN[1])
        # ---- face
        fd = ellipse(u, v, cx, cy + 4, rx, ry)
        fm = p.part(fd, SKIN, bevel=14, light=light, amb=0.30, ink=INK)
        # ---- hair cap + fringe (front)
        cap = p.mask(ellipse(u, v, cx, cy - 22, rx + 3, 34))
        fr = np.zeros_like(cap)
        hl = cy - 12
        for i in range(11):
            x0 = cx - rx + i * (2 * rx / 11); x1 = x0 + 2 * rx / 11
            L = rng.uniform(5, 13); lean = rng.uniform(-3, 3)
            fr |= p.poly([(x0 - 1, hl - 3), (x1 + 1, hl - 3), ((x0 + x1) / 2 + lean, hl + L)])
        hm = (cap & (v < hl)) | fr
        p.part(hm, HAIR, bevel=6, light=light, amb=0.12, ink=C('#05040a'), bias=-0.04, dither=0.3)
        sheen = hm & p.mask(arc(u, v, cx - 8, cy + 6, 44, 230, 300, th=2.2))
        p.tint(sheen & (p.bayer < 0.2), HAIR[4], 0.9)
        # forehead shadow under the fringe
        p.tint(fm & ~hm & (v < hl + 9) & (v > hl - 4), SKIN[1], 0.35)
        # ---- features
        lx, ly = look
        ey = cy + 12
        exs = (cx - 25, cx + 25)
        # eye bags
        if bags > 0:
            for ex in exs:
                p.tint(fm & p.mask(arc(u, v, ex, ey + 1, 13, 25, 155, th=2.2)), BAG, 0.45 * bags)
                p.tint(fm & p.mask(arc(u, v, ex, ey + 5, 12, 40, 140, th=1.2)), BAG, 0.3 * bags)
        # brows (brow > 0 = raised / worried, < 0 = frown)
        for i, ex in enumerate(exs):
            sgn = -1 if i == 0 else 1
            yb = ey - 15 - 3 * max(0, -lid) - 2 * brow
            inner = yb - 2 * brow + (1.5 if lid > 0.4 else 0)
            p.fill(poly_stroke(u, v, [(ex - sgn * 11, inner), (ex, yb - 1), (ex + sgn * 11, yb + 1.5)], th=2.6), HAIR[1], where=~fr)
        # eyes
        for i, ex in enumerate(exs):
            sgn = -1 if i == 0 else 1
            erx, ery = 11.5, 8.5 * (1 + 0.25 * max(0, -lid))
            if dead:
                for d in (-1, 1):
                    p.fill(seg(u, v, ex - 7, ey - 6 * d, ex + 7, ey + 6 * d, th=2.4), INK)
                continue
            k = max(0.0, min(1.0, lid))
            if k >= 0.97:
                p.fill(arc(u, v, ex, ey - 7, 12, 30, 150, th=2.0), INK)
                p.fill(seg(u, v, ex - 9, ey + 3, ex - 6, ey + 1, th=1.0), INK)
                continue
            top = ey - ery + 2 * ery * k                          # lid line height
            eye = p.mask(ellipse(u, v, ex, ey, erx, ery)) & (v > top)
            p.fill(eye, C('#eef0f8'))
            p.tint(eye & (v < top + 2.5), C('#9aa0c0'), 0.6)       # lid shadow on the white
            if red > 0:
                for j in range(5):
                    a0 = (j / 5) * math.pi + rng.uniform(-0.3, 0.3)
                    side = -1 if j % 2 else 1
                    x0 = ex + side * erx * 0.95; y0 = ey + rng.uniform(-3, 4)
                    x1 = ex + side * erx * rng.uniform(0.35, 0.6); y1 = y0 + rng.uniform(-3, 3)
                    p.fill(seg(u, v, x0, y0, x1, y1, th=0.55 + 0.4 * red), C('#e04050'), where=eye & (p.bayer < 0.3 + 0.7 * red))
            ir = 6.2 * pupil
            ix, iy = ex + lx, ey + ly + 0.5
            iris = p.mask(circle(u, v, ix, iy, ir)) & eye
            p.part(iris, [C('#1a0e0a'), C('#3a2216'), C('#5a3a22'), C('#7a5230')], bevel=3, light=(0, 0.6, 0.8), amb=0.3, outline=None)
            p.fill(p.mask(circle(u, v, ix, iy, ir * 0.48)) & eye, C('#08060a'))
            # screen reflection (a tiny phone in each eye)
            rw, rh = 4, 5
            rx0, ry0 = int(round(ix - 3)), int(round(iy - 4))
            refl = p.mask(rrect(u, v, ix - 3.5, iy - 4.5, rw, rh, 0.6)) & eye
            if reflect is not None:
                ys, xs = np.nonzero(refl)
                if len(ys):
                    y0r, x0r = ys.min(), xs.min()
                    sh = reflect.shape
                    for yy, xx in zip(ys, xs):
                        c = reflect[min(sh[0] - 1, int((yy - y0r) * sh[0] / rh)), min(sh[1] - 1, int((xx - x0r) * sh[1] / rw))]
                        p.rgb[yy, xx] = c / 255.0 * 0.7 + 0.3
                    p.E[refl] = 0.9
            else:
                p.fill(refl, C('#d8f0ff'), E=0.9)
            p.fill(circle(u, v, ix + 3, iy + 3, 1.0), C('#ffffff'), where=eye, E=0.6)
            # upper lid: thick line + lashes, lower lid hint
            lidm = p.mask(ellipse(u, v, ex, ey, erx + 1, ery + 1)) & ~p.mask(ellipse(u, v, ex, ey, erx - 0.5, ery - 0.5))
            p.fill(lidm & (v < ey - ery * 0.2) & (v <= top + 1.5), INK)
            p.fill(seg(u, v, ex - erx, top, ex + erx, top, th=1.6), INK, where=p.mask(ellipse(u, v, ex, ey, erx + 1.5, ery + 2)))
            p.fill(seg(u, v, ex + sgn * erx, top + 1, ex + sgn * (erx + 3), top - 2, th=1.2), INK)
            p.tint(fm & p.mask(arc(u, v, ex, ey - 1, erx + 1, 30, 150, th=1.0)), SKIN[1], 0.5)
        # nose
        p.tint(fm & p.mask(ellipse(u, v, cx + 2, cy + 27, 3.5, 2.2)), SKIN[1], 0.55)
        p.fill(circle(u, v, cx - 1, cy + 25, 1.2), SKIN[5])
        # cheeks
        for ex in exs:
            p.tint(fm & p.mask(ellipse(u, v, ex + (-3 if ex < cx else 3), ey + 16, 7, 3)) & (p.bayer < 0.35), C('#e8806e'), 0.5)
        # mouth
        mx, my = cx, cy + 38
        if mouth == 'o':
            p.fill(ellipse(u, v, mx, my, 4, 4.5), C('#4a1a22')); p.fill(ellipse(u, v, mx, my + 2, 2.5, 1.5), C('#b0505a'))
        elif mouth == 'open':
            p.fill(ellipse(u, v, mx, my + 1, 7, 5), C('#4a1a22')); p.fill(ellipse(u, v, mx, my + 3.5, 4, 2), C('#c05a62'))
            p.fill(rrect(u, v, mx - 5, my - 3.5, 10, 2, 1), C('#f4f0ec'))
        elif mouth == 'drool':
            p.fill(arc(u, v, mx, my - 5, 6, 60, 120, th=1.4), INK)
            p.fill(poly_stroke(u, v, [(mx + 4, my), (mx + 6, my + 4), (mx + 6, my + 9)], th=1.6), C('#bfe6ff'), E=0.3)
            p.fill(circle(u, v, mx + 6, my + 10, 1.8), C('#dff4ff'), E=0.4)
        elif mouth == 'smile':
            p.fill(arc(u, v, mx, my - 8, 8, 55, 125, th=1.6), INK)
        elif mouth == 'grit':
            p.fill(rrect(u, v, mx - 7, my - 2.5, 14, 5, 1.5), C('#f4f0ec')); p.fill(seg(u, v, mx - 6, my, mx + 6, my, th=0.6), C('#9a8a8a'))
            p.edge(p.mask(rrect(u, v, mx - 7, my - 2.5, 14, 5, 1.5)), ink=INK)
        else:
            p.fill(seg(u, v, mx - 5, my, mx + 4, my + 0.6, th=1.5), C('#6a2a2a'))
        # sweat drop
        if sweat > 0:
            sx, sy = cx + rx - 12, cy - 8 + 6 * sweat
            d = union(circle(u, v, sx, sy + 3, 3.4), p.mask(np.zeros_like(u)) * 0 + 1e9)
            p.part(p.poly([(sx, sy - 6), (sx - 3.4, sy + 2), (sx + 3.4, sy + 2)]) | p.mask(circle(u, v, sx, sy + 3, 3.4)),
                   [C('#5a9ad8'), C('#9ad0f8'), C('#e8f8ff')], bevel=2, light=(-0.5, -0.6, 0.6), amb=0.5, ink=C('#1a3a6a'), E=0.2)
    s = p.sprite()
    s.ax, s.ay = int(cx), int(78)
    return s
