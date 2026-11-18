"""pixelkit.sets.bedroom - 深夜卧室（v0.13，《熬夜副本》开场 / 结尾 / 关卡大厅）。

正面构图 480x270：左边窗（月光 + 远处城市灯窗）、书桌（关着的显示器 + 待机灯、泡面、能量饮料罐）、
床头柜（红色数字闹钟）、右边床（被子隆起，枕头上的人由 mid 层画）、床头墙上一串小彩灯。
光：月光 = OutdoorScene 的 sun（T 图画好的窗光斑）；手机 / 闹钟 / 彩灯 / 待机灯 = points。

    b = Bedroom(); bg = b.bg(clock='0347')        # dict -> OutdoorScene(bg)
    b.A['head'], b.A['phone'], b.A['clock'] ...    # 锚点
    b.points(t, phone=1.0)                         # 点光列表（手机闪烁随内容变）
"""
import math
import numpy as np
from ..core import C
from ..paintset import PaintSet, R, string_lights, star_px
from .. import materials as mat

SEG = {0: 'abcdef', 1: 'bc', 2: 'abged', 3: 'abgcd', 4: 'fgbc', 5: 'afgcd', 6: 'afgedc', 7: 'abc', 8: 'abcdefg', 9: 'abcdfg'}

def seg7(ps, x, y, n, col, E=1.0, w=5, h=9):
    m = h // 2
    P = {'a': (x + 1, y, w - 2, 1), 'b': (x + w - 1, y + 1, 1, m - 1), 'c': (x + w - 1, y + m + 1, 1, h - m - 2),
         'd': (x + 1, y + h - 1, w - 2, 1), 'e': (x, y + m + 1, 1, h - m - 2), 'f': (x, y + 1, 1, m - 1), 'g': (x + 1, y + m, w - 2, 1)}
    for s in SEG[int(n)]:
        ps.rect(*P[s], col, E)

class Bedroom:
    W, H = 480, 270
    FLOOR = 206

    def __init__(self, seed=3):
        self.seed = seed
        self.A = dict(head=(424, 166), face=(414, 170), phone=(398, 158), clock=(254, 166), window=(36, 34, 104, 112),
                      bed=(258, 168, 470, 212), monitor=(186, 118), led=(219, 147), hub_wall=(60, 20, 380, 170))
        self._base = None

    # ---------------------------------------------------------------- painting
    def _paint(self):
        ps = PaintSet(self.W, self.H); F = self.FLOOR
        wall = R('#4a4878', 7)
        ps.tex_rect(0, 0, self.W, F, wall, mat.plaster, base=3.2, mottle=0.5)
        # wallpaper: faint vertical pinstripe
        for x in range(6, self.W, 12):
            m = ps.mask_rect(x, 14, 1, F - 40); ps.cv.a[m & (ps.yy % 3 != 0), :3] = wall[2][:3]
        ps.tex_rect(0, 0, self.W, 12, R('#3a3762', 6), base=1.6)                          # ceiling strip
        ps.rect(0, 12, self.W, 1, wall[1])
        ps.tex_rect(0, F - 26, self.W, 26, R('#3d3a5e', 6), base=2.6)                      # wainscot
        ps.rect(0, F - 27, self.W, 1, wall[5]); ps.rect(0, F - 26, self.W, 1, wall[1])
        ps.rect(0, F - 2, self.W, 2, R('#2c2840', 6)[1])                                  # skirting
        # floor: warm planks
        fl = R('#6b4a46', 7)
        ps.tex_rect(0, F, self.W, self.H - F, fl, mat.planks, base=3.2, pw=7.0, pl=58.0)
        # rug under the bed / desk
        rug = R('#5b3e6e', 6)
        m = ps.mask_poly([(150, 252), (460, 252), (446, 222), (166, 222)])
        ps.tex(m, rug, mat.fabric, base=3.0)
        for yy in (226, 247):
            ps.cv.a[m & (ps.yy == yy), :3] = R('#e0b26a', 6)[3][:3]
        # ----- window + curtains
        x0, y0, w, h = self.A['window']
        ps.rect(x0 - 3, y0 - 3, w + 6, h + 6, R('#2a2540', 6)[2])
        sky = R('#1b2250', 7)
        mw = ps.mask_rect(x0, y0, w, h)
        ps.vgrad(mw, sky, y0, y0 + h, 0.6, 3.6, E=0.85)
        rng = np.random.default_rng(self.seed)
        for i in range(24):
            sx, sy = x0 + rng.integers(2, w - 2), y0 + rng.integers(2, h // 2)
            star_px(ps, sx, sy, (255, 244, 214, 255), 1.0, big=(i % 9 == 0))
        # moon
        mm = ps.mask_ellipse(x0 + 72, y0 + 20, 8.5, 8.5); ps.fill(mm, C('#fff2cf'), 1.0)
        ps.fill(ps.mask_ellipse(x0 + 75, y0 + 18, 7.5, 7.5) & mm, C('#f1dfae'), 1.0)
        ps.fill(ps.mask_ellipse(x0 + 69, y0 + 23, 1.6, 1.2), C('#e2cc98'), 1.0)
        # skyline with lit windows
        bx = x0
        while bx < x0 + w:
            bw = int(rng.integers(9, 18)); bh = int(rng.integers(18, 52))
            m = ps.mask_rect(bx, y0 + h - bh, bw, bh) & mw
            ps.fill(m, C('#141632'), 0.0)
            for wy in range(y0 + h - bh + 3, y0 + h - 2, 4):
                for wx in range(bx + 2, bx + bw - 2, 3):
                    if rng.random() < 0.28: ps.px(wx, wy, C(['#ffcf7a', '#ffe7a8', '#9fd2ff'][int(rng.integers(0, 3))]), 0.9)
            bx += bw + int(rng.integers(0, 3))
        # mullions
        ps.rect(x0 + w // 2, y0, 2, h, R('#2a2540', 6)[3]); ps.rect(x0, y0 + h // 2, w, 2, R('#2a2540', 6)[3])
        ps.rect(x0 - 6, y0 + h + 2, w + 12, 4, R('#7c6a8c', 6)[3]); ps.rect(x0 - 6, y0 + h + 5, w + 12, 1, R('#7c6a8c', 6)[1])
        # curtains
        cu = R('#7a3a5c', 7)
        for cx0, cw in ((x0 - 16, 20), (x0 + w - 4, 20)):
            m = ps.mask_rect(cx0, y0 - 8, cw, h + 26)
            t = 3.0 + 1.3 * np.sin((ps.xx - cx0) * 0.9) + (mat.fbm(ps.xx * 1.0, ps.yy * 1.0, 20, 2, 4) - 0.5)
            img = mat.apply_ramp(t, cu, band=1.8); ps.cv.a[m] = img[m]
        ps.rect(x0 - 20, y0 - 10, w + 40, 3, R('#3a2a2a', 6)[2])
        # ----- desk (left-centre) with a sleeping monitor
        dk = R('#7a5038', 6)
        ps.tex_rect(146, 150, 92, 6, dk, base=4.0)                              # top
        ps.rect(146, 156, 92, 1, dk[1])
        ps.tex_rect(150, 157, 6, F - 157, dk, base=2.2); ps.tex_rect(228, 157, 6, F - 157, dk, base=2.2)
        ps.tex_rect(196, 157, 32, 20, dk, base=2.8); ps.rect(209, 166, 6, 1, dk[5])   # drawer
        ps.ao_rect(150, 157, 84, F - 157, k=0.45, soft=4)
        mo = R('#2b2a3a', 6)
        ps.rect(170, 104, 50, 34, mo[1]); ps.rect(172, 106, 46, 30, C('#0d0f1a'))
        ps.rect(173, 107, 20, 1, C('#262a44'))                                   # glass sheen
        ps.rect(191, 138, 8, 8, mo[2]); ps.rect(184, 146, 22, 4, mo[3])
        ps.rect(*self.A['led'], 2, 1, C('#ffb347'), 1.0)
        # lamp (off), noodle cup, cans, keyboard
        lp = R('#2f6f6a', 6)
        ps.rect(156, 145, 10, 5, lp[2]); ps.rect(160, 120, 2, 25, lp[1]); ps.rect(154, 114, 14, 7, lp[3]); ps.rect(155, 120, 12, 1, lp[1])
        ps.rect(180, 147, 30, 3, R('#c9c0ad', 6)[3]); ps.rect(181, 147, 28, 1, R('#c9c0ad', 6)[5])
        nd = R('#e9e2d2', 6)
        ps.rect(222, 139, 10, 11, nd[3]); ps.rect(222, 139, 10, 2, C('#c84a3a')); ps.rect(221, 138, 12, 1, nd[5])
        can_cols = ('#46b36a', '#46b36a', '#e0563c', '#46b36a')
        for i, cc in enumerate(can_cols):
            cx = 236 - 0 + i * 0  # placed on the nightstand below instead
        # ----- nightstand + alarm clock
        ns = R('#6a4a3a', 6)
        ps.tex_rect(240, 176, 34, 30, ns, base=3.0); ps.rect(240, 176, 34, 2, ns[5]); ps.rect(243, 190, 28, 1, ns[1])
        ps.rect(255, 183, 4, 1, ns[5])
        ps.ao_rect(240, 176, 34, 30, k=0.35, soft=4)
        ps.rect(244, 162, 30, 14, C('#1c1a24')); ps.rect(246, 164, 26, 10, C('#07060a'))
        for i, cc in enumerate(('#46b36a', '#46b36a', '#e0563c')):
            cx = 242 + i * 0
        # cans on the desk top (3) + one crushed on the floor
        for i, cc in enumerate(('#46b36a', '#46b36a', '#e0563c')):
            r = R(cc, 6); x = 200 + i * 6 if False else 132 + i * 0
        cans = [(205, 141, '#46b36a'), (211, 141, '#46b36a'), (217, 143, '#e0563c')]
        for (x, y, cc) in cans:
            r = R(cc, 6); hh = 150 - y
            ps.rect(x, y, 5, hh, r[3]); ps.rect(x, y, 1, hh, r[5]); ps.rect(x + 4, y, 1, hh, r[1])
            ps.rect(x, y, 5, 1, C('#c8ccd6')); ps.rect(x + 1, y + 3, 3, 1, C('#f2f2f2'))
        r = R('#46b36a', 6); ps.rect(118, 236, 8, 4, r[3]); ps.rect(118, 236, 2, 4, C('#c8ccd6')); ps.ao_rect(117, 239, 10, 2, 0.5, 1.5)
        # clothes pile + sneakers on the floor
        cl = R('#5d6f9a', 6)
        m = ps.mask_ellipse(118, 218, 18, 7) | ps.mask_ellipse(130, 214, 10, 6)
        ps.tex(m, cl, mat.fabric, base=3.0); ps.ao_mask(m, 0.35, 3)
        for sx in (84, 96):
            ps.rect(sx, 226, 10, 4, C('#e8e6f0')); ps.rect(sx, 229, 10, 1, C('#8a86a0')); ps.rect(sx + 1, 226, 4, 1, C('#d8584a'))
        # ----- bed (right): frame, mattress, blanket mound, pillow, headboard
        bf = R('#5a3e52', 6)
        ps.tex_rect(452, 120, 18, 88, bf, base=3.0); ps.rect(452, 120, 18, 2, bf[5]); ps.rect(455, 126, 12, 1, bf[1])
        ps.tex_rect(266, 188, 190, 18, bf, base=2.6); ps.rect(266, 188, 190, 1, bf[4])
        ps.rect(268, 206, 6, 4, bf[1]); ps.rect(446, 206, 6, 4, bf[1])
        ps.ao_rect(262, 204, 196, 6, k=0.6, soft=3)
        ms = R('#d9d2e6', 6); ps.tex_rect(266, 178, 186, 11, ms, base=3.0)
        pl = R('#e9e4f2', 6)
        m = ps.mask_ellipse(430, 168, 22, 9); ps.tex(m, pl, base=3.4); ps.outline(m, pl[1])
        bl = R('#4a5590', 7)
        m = (ps.mask_ellipse(300, 176, 40, 13) | ps.mask_ellipse(352, 170, 44, 16) | ps.mask_ellipse(398, 174, 26, 12)
             | ps.mask_rect(262, 176, 152, 16))
        t = 3.2 + (mat.fbm(ps.xx * 1.0, ps.yy * 1.0, 18, 2, 9) - 0.5) * 1.2 - np.clip((ps.yy - 160) / 30.0, 0, 1) * 0.8
        img = mat.apply_ramp(t, bl, band=2.0); ps.cv.a[m] = img[m]
        for yy in range(160, 194, 6):                            # quilt stitching
            ps.cv.a[m & (ps.yy == yy) & (ps.xx % 3 != 0), :3] = bl[2][:3]
        for xx in range(276, 410, 16):
            ps.cv.a[m & (ps.xx == xx) & (ps.yy % 3 != 0), :3] = bl[2][:3]
        ps.outline(m, bl[0])
        # ----- wall dressing: poster, shelf, fairy lights, small frame
        pp = R('#2a1f3a', 6)
        ps.rect(300, 54, 46, 62, C('#e8dcc0')); ps.rect(302, 56, 42, 58, C('#2d2458'))
        m = ps.mask_ellipse(323, 80, 13, 13); ps.fill(m, C('#ff8a5a'), 0.0)
        ps.fill(ps.mask_ellipse(323, 80, 9, 9), C('#ffc070'))
        for i, yy in enumerate(range(98, 112, 3)): ps.rect(306, yy, 34 - i * 6, 1, C('#7a6fd0'))
        ps.text(306, 57, 'LEVEL UP', C('#ffd85a'), 'silk')
        ps.tex_rect(372, 92, 64, 4, R('#7a5038', 6), base=3.6); ps.rect(372, 96, 64, 1, R('#7a5038', 6)[1])
        for i, (bx, bh, cc) in enumerate([(376, 14, '#c84a3a'), (381, 12, '#3f7ab0'), (385, 15, '#d8b04a'), (390, 11, '#5aa070')]):
            ps.rect(bx, 92 - bh, 4, bh, R(cc, 6)[3]); ps.rect(bx, 92 - bh, 1, bh, R(cc, 6)[5])
        ps.rect(404, 84, 10, 8, C('#d8d0e8')); ps.rect(405, 85, 8, 6, C('#7aa0d8'))          # little photo
        ps.rect(420, 82, 9, 10, R('#7aa06a', 6)[3]); ps.rect(421, 78, 3, 5, R('#7aa06a', 6)[4]); ps.rect(425, 77, 3, 6, R('#7aa06a', 6)[2])
        self.bulbs = string_lights(ps, [(262, 30), (330, 40), (400, 28), (468, 40)], 13, sag=7)
        # ----- room depth / AO
        ps.ao_rect(0, 0, self.W, 14, 0.45, 6)
        ps.ao_rect(0, F - 4, self.W, 8, 0.25, 4)
        ps.ao_vignette(0.42, 1.8)
        # moonlight: window glass is fully lit; a slanted patch on the floor + wall below the sill
        x0, y0, w, h = self.A['window']
        ps.light_mask(ps.mask_rect(x0 - 6, y0 + h + 2, w + 12, 5), 0.8, 0.8)
        ps.light_poly([(x0 + 4, y0 + h + 8), (x0 + w - 4, y0 + h + 8), (x0 + w + 30, F), (x0 + 30, F)], 0.18, 4.0)
        ps.light_poly([(x0 + 30, F), (x0 + w + 30, F), (x0 + w + 80, 258), (x0 + 64, 258)], 0.32, 3.5)
        # lava lamp on the shelf: warm emissive blob (point light in points())
        ps.rect(437, 84, 6, 8, C('#2a2238')); ps.rect(438, 70, 4, 14, C('#ff9a4a'), 0.9)
        ps.rect(439, 73, 2, 3, C('#ffd27a'), 1.0); ps.rect(438, 79, 2, 2, C('#ffd27a'), 1.0); ps.rect(437, 68, 6, 2, C('#2a2238'))
        return ps

    def bg(self, clock='0347', colon=True, monitor_led=True):
        if self._base is None: self._base = self._paint()
        ps = PaintSet(self.W, self.H)
        ps.cv.a[:] = self._base.cv.a; ps.E[:] = self._base.E; ps.T[:] = self._base.T; ps.ao[:] = self._base.ao
        red = C('#ff3a2e')
        for i, ch in enumerate(clock):
            seg7(ps, 247 + i * 6 + (2 if i > 1 else 0), 165, ch, red, 1.0, w=5, h=8)
        if colon:
            ps.px(258, 167, red, 1.0); ps.px(258, 170, red, 1.0)
        if not monitor_led: ps.rect(*self.A['led'], 2, 1, C('#3a2a1a'), 0.0)
        return ps.bg()

    def points(self, t, phone=1.0, phone_col=(0.55, 0.80, 1.0), clock=1.0, bulbs=1.0, flick=0.0):
        pts = []
        if phone > 0:
            px, py = self.A['phone']
            pts.append(dict(x=px, y=py + 2, r=26, col=phone_col, k=1.15 * phone * (1 + flick), power=1.3))
            pts.append(dict(x=px + 6, y=py - 30, r=70, col=tuple(c * 0.5 for c in phone_col), k=0.35 * phone, power=1.6, layers=('bg',)))
        if clock > 0:
            cx, cy = self.A['clock']
            pts.append(dict(x=cx + 6, y=cy + 2, r=14, col=(1.0, 0.25, 0.18), k=0.55 * clock, power=1.5))
        pts.append(dict(x=440, y=78, r=30, col=(1.0, 0.55, 0.28), k=0.55, power=1.5))
        if bulbs > 0:
            for i, (x, y, c) in enumerate(self.bulbs):
                fl = 0.85 + 0.15 * math.sin(t * 2.0 + i * 1.7)
                pts.append(dict(x=x, y=y + 3, r=15, col=tuple(v / 255 for v in c[:3]), k=0.45 * bulbs * fl, power=1.4, layers=('bg',)))
        return pts
