"""pixelkit.sets.bedroom_night - 凌晨的卧室 v2（320x180 一点透视，v0.13《熬夜副本》开场）。

比 bedroom320 更「有人住」：每件杂物都在说「这人天天熬夜」——
  左墙书桌：待机的显示器（屏保 zZ 在弹）、外卖盒、能量饮料罐金字塔、泡面杯；
  后墙：窗（月光 + 城市）、床头灯照亮的软木板「早睡打卡」（7 天全是红叉）+ 便签「7:00 必须起!!」、彩灯串；
  床头柜：暖色小台灯、红色数字闹钟、水杯、插座 → 充电线一路拉到手机（绷直）；
  床：人平躺、双手举着手机（屏幕朝下照脸）；床尾蜷着一只橘猫；
  右前景：堆满衣服的「衣服椅」；地上：拖鞋（一只翻了）、袜子、纸团、手柄、一本扣着的《早睡指南》躺在月光里。

    b = BedroomNight()
    fr = b.frame(t, face='tired', phone='up'|'smack'|'none', head_dy=0, cat='curl'|'up'|'puff', clock='0347',
                 screen=(150, 220, 255), arms_k=1.0, monitor=1.0)
    L = b.light(fr, phone_k=1.0, lamp_k=1.0, moon_k=1.0, room_k=1.0, screen_col=(0.5, 0.8, 1.0))
    img = fr.render(cam, L, GRADE_NIGHT, frame=i, air=b.air(fr))
锚点 b.A：head（头顶中心）、face（脸中心）、phone（举着时手机中心）、cat、clock、lamp、cork（软木板 x,y,w,h）、book、monitor。
"""
import math
import numpy as np
from ..pixstage import Stage
from ..characters import human, cat as CAT
from .bedroom320 import digits, SLEEPER

WALL = ['#120c12', '#1a121a', '#221822', '#2c1f2a']
WOOD = ['#1a0e0c', '#2a1812', '#3a2216', '#4e2e1c', '#66402a']
from .. import post
GRADE_BED = dict(post.GRADES['night_hd2d'])
GRADE_BED.update(shadow=(0.05, 0.015, 0.11), highlight=(0.08, 0.04, -0.06), grain=0.012, vignette=0.42, sat=1.12, contrast=1.12,
                 bloom=dict(thr=0.72, knee=0.22, strength=0.6, tint=(1.0, 0.9, 0.8), halation=0.2))
GOLD = ['#5a3a12', '#8a5e20', '#c8902e', '#f2c35a', '#fff0b0']
BLANK = ['#141a3a', '#1e2a5a', '#2a3a7a', '#3a4e98', '#5a6cb8']
SHEET = ['#6a6688', '#9a96b8', '#c8c4dc', '#e8e4f4']
SHADE = ['#7a3a10', '#c86a1a', '#f2a03a', '#ffd27a', '#fff2c8']

class BedroomNight:
    W, H = 320, 180
    BW = (58, 20, 262, 120)            # back wall rect
    VP = (160, 68)

    def __init__(self):
        self.A = dict(head=(180, 92), face=(180, 104), phone=(184, 87), cat=(224, 142), clock=(250, 92), lamp=(236, 84),
                      cork=(222, 34, 34, 28), book=(92, 166), monitor=(24, 96), window=(68, 30, 44, 46), socket=(258, 108))
        self.st = Stage(self.W, self.H)
        self._paint(self.st)
        self.base = self.st.snapshot()

    # ================================================================ static set
    def _paint(self, s):
        W, H = self.W, self.H; x0, y0, x1, y1 = self.BW; yy, xx = s.yy, s.xx
        s.rect(0, 0, W, H, '#07050a')
        # ceiling
        ce = s.poly([(0, 0), (W, 0), (x1, y0), (x0, y0)], '#0c080e')
        s.dither(ce & (yy > 12), '#110b12', 0.5)
        # walls
        lw = s.poly([(0, 0), (x0, y0), (x0, y1), (0, H)], '#140d14')
        rw = s.poly([(W, 0), (x1, y0), (x1, y1), (W, H)], '#120b12')
        bw = s.rect(x0, y0, x1 - x0, y1 - y0, WALL[1])
        # wallpaper: faint diamond pattern on the back wall
        pat = bw & (((xx + yy) % 12 == 0) | ((xx - yy) % 12 == 0))
        s.dither(pat, WALL[2], 0.5)
        for k in range(1, 6):        # side wall stripes in perspective
            u = k / 6
            s.line(x0 * u, y0 * u, x0 * u, H - (H - y1) * u, '#170f17', mask=lw)
            s.line(W - (W - x1) * u, y0 * u, W - (W - x1) * u, H - (H - y1) * u, '#150e15', mask=rw)
        # skirting board + chair rail (gold thin line)
        s.rect(x0, y1 - 5, x1 - x0, 5, '#1e1218'); s.rect(x0, y1 - 6, x1 - x0, 1, GOLD[1])
        s.poly([(0, H - 8), (x0, y1 - 5), (x0, y1), (0, H)], '#1a0f15')
        s.poly([(W, H - 8), (x1, y1 - 5), (x1, y1), (W, H)], '#180e14')
        # floor: warm planks converging to the vanishing point
        fl = s.poly([(0, H), (x0, y1), (x1, y1), (W, H)], WOOD[1])
        for k in range(17):
            xa = x0 + (x1 - x0) * k / 16; xb = -170 + 660 * k / 16
            s.line(xa, y1, xb, H, WOOD[0], mask=fl)
        for i, yb in enumerate((123, 128, 135, 145, 159, 176)):
            s.fill(fl & (yy == yb), '#1e110d')
        s.dither(fl & (yy > 150), WOOD[2], 0.18)
        self.floor = fl
        self._window(s)
        self._moonbeam(s)
        self._desk(s)
        self._back_props(s)
        self._rug_bed(s)
        self._nightstand(s)
        self._floor_clutter(s)
        self._chair(s)

    def _window(self, s):
        wx, wy, ww, wh = self.A['window']; yy = s.yy
        s.rect(wx - 3, wy - 3, ww + 6, wh + 6, GOLD[1]); s.rect(wx - 2, wy - 2, ww + 4, wh + 4, GOLD[2])
        sky = s.rect(wx, wy, ww, wh, '#0c1440', 0.85)
        s.fill(sky & (yy > wy + 16), '#101a50', 0.85); s.fill(sky & (yy > wy + 32), '#18205a', 0.85)
        s.dither(sky & (yy > wy + 14) & (yy < wy + 18), '#101a50', 0.5, 0.85)
        rng = np.random.default_rng(7); bx = wx
        while bx < wx + ww:
            bw_ = int(rng.integers(4, 9)); bh = int(rng.integers(6, 20))
            m = s.M_rect(bx, wy + wh - bh, bw_, bh) & sky; s.fill(m, '#080c24', 0.0)
            for wy_ in range(wy + wh - bh + 2, wy + wh - 1, 3):
                for wx_ in range(bx + 1, bx + bw_ - 1, 2):
                    if rng.random() < 0.28: s.px(wx_, wy_, ['#ffcf7a', '#9fd2ff', '#ff9a7a'][int(rng.integers(0, 3))], 0.95)
            bx += bw_ + 1
        for (sx, sy) in [(73, 36), (80, 46), (104, 34), (88, 33), (99, 44)]: s.px(sx, sy, '#fff4d0', 1.0)
        mx, my = wx + 32, wy + 12
        s.ell(mx, my, 6, 6, '#fff0c4', 1.0); s.fill(s.M_ell(mx + 3, my - 2, 5, 5) & s.M_ell(mx, my, 6, 6), '#0c1440', 0.85)
        s.rect(wx + ww // 2 - 1, wy, 2, wh, GOLD[2]); s.rect(wx, wy + wh // 2 - 1, ww, 2, GOLD[2])
        s.rect(wx - 6, wy + wh + 3, ww + 12, 3, GOLD[2]); s.rect(wx - 6, wy + wh + 6, ww + 12, 1, GOLD[0])
        # sill clutter: a small cactus + an empty bottle
        s.rect(wx + 2, wy + wh, 5, 3, '#a85a3a'); s.rect(wx + 3, wy + wh - 5, 3, 5, '#3a8a4a'); s.px(wx + 4, wy + wh - 6, '#ff8aa0')
        s.rect(wx + ww - 6, wy + wh - 6, 3, 9, '#5a8a6a', 0.0); s.rect(wx + ww - 5, wy + wh - 8, 1, 2, '#5a8a6a')
        # curtains (half drawn, folds shaded)
        for cx0, w in ((wx - 14, 12), (wx + ww + 2, 12)):
            m = s.M_rect(cx0, wy - 8, w, wh + 24)
            s.part(m, ['#2a0c1c', '#4a1630', '#6a2242', '#8a3456'], bevel=3, light=(-0.5, -0.3, 0.8), amb=0.4, outline=0.6)
            for k in range(1, w, 4): s.line(cx0 + k, wy - 8, cx0 + k, wy + wh + 15, '#2a0c1c')
            s.rect(cx0, wy + wh + 2, w, 3, GOLD[1])         # tie-back
        s.rect(wx - 18, wy - 10, ww + 36, 2, GOLD[2]); s.px(wx - 19, wy - 10, GOLD[3]); s.px(wx + ww + 18, wy - 10, GOLD[3])

    def _moonbeam(self, s):
        wx, wy, ww, wh = self.A['window']; yy = s.yy; H = self.H
        beam = s.M_poly([(wx, wy + wh + 8), (wx + ww, wy + wh + 8), (140, H), (30, H)]) & (yy > self.BW[3] - 1)
        s.add(beam, (8, 10, 24))
        core = s.M_poly([(wx + 8, wy + wh + 8), (wx + ww - 8, wy + wh + 8), (122, H), (50, H)]) & beam & (yy > self.BW[3] + 6)
        s.add(core, (8, 10, 22))
        # window-cross shadow inside the beam
        s.mul(beam & (np.abs(s.xx - (wx + ww / 2 - (yy - 120) * 0.62)) < 1.5), 0.6)
        self.beam = beam

    def _desk(self, s):
        yy = s.yy
        top = s.poly([(0, 126), (40, 106), (58, 108), (22, 132)], WOOD[3])
        s.fill(top & (s.M_poly([(0, 124), (40, 104), (44, 106), (2, 127)])), WOOD[4])
        s.poly([(0, 132), (22, 132), (22, 180), (0, 180)], WOOD[1]); s.poly([(22, 132), (58, 108), (58, 140), (22, 172)], WOOD[0])
        s.line(0, 126, 40, 106, GOLD[1])
        # monitor (standby): bezel + screen; the zZ screensaver is drawn per frame
        mon = s.poly([(8, 82), (40, 70), (40, 98), (8, 112)], '#100e16'); s.outline(mon)
        self.mon_screen = s.poly([(10, 84), (38, 73), (38, 96), (10, 109)], '#06060c')
        s.rect(22, 106, 4, 8, '#100e16'); s.poly([(16, 114), (32, 108), (34, 110), (18, 116)], '#18161e')
        s.px(37, 97, '#ffb347', 1.0)
        # takeout boxes (stacked), chopsticks
        for i, (bx, by) in enumerate(((42, 100), (44, 94))):
            m = s.poly([(bx, by), (bx + 10, by - 3), (bx + 12, by + 3), (bx + 2, by + 6)], '#e8e2d4')
            s.part(m, ['#8a8478', '#c8c0b0', '#ece6d8'], bevel=2, amb=0.5)
            s.rect(bx + 4, by + 1, 3, 2, '#c8302a')
        s.line(46, 92, 54, 86, '#c8a060'); s.line(47, 92, 55, 87, '#a88040')
        # energy can pyramid (3-2-1)
        cans = [(4, 114), (8, 112), (12, 110), (6, 107), (10, 105), (8, 100)]
        for i, (cx, cy) in enumerate(cans):
            m = s.rect(cx, cy, 3, 6, ['#3ab86a', '#e8402a'][i % 2]); s.px(cx, cy, '#e8ecf4'); s.px(cx + 2, cy + 2, '#ffffff'); s.outline(m, '#050308')
        # noodle cup with a fork
        m = s.poly([(28, 112), (36, 109), (35, 117), (29, 119)], '#f2ece0'); s.part(m, ['#9a9080', '#d8d0c0', '#f6f0e4'], bevel=2)
        s.poly([(28, 112), (36, 109), (36, 111), (28, 114)], '#c8302a'); s.line(33, 104, 32, 111, '#d8dce6')

    def _back_props(self, s):
        # cork board (lit by the bedside lamp): "早睡打卡" with 7 red X + a sticky note
        cx, cy, cw, ch = self.A['cork']
        s.rect(cx - 2, cy - 2, cw + 4, ch + 4, GOLD[1])
        cb = s.rect(cx, cy, cw, ch, '#8a5a32'); s.dither(cb, '#a06a3c', 0.3); s.dither(cb, '#6a4224', 0.15)
        s.rect(cx + 2, cy + 2, 21, 23, '#f2ece0')
        s.text(cx + 2, cy - 1, '早睡', '#2a1a1a', 'zh10')
        s.text(cx + 13, cy + 3, '打卡', '#6a5a50', 'silk') if False else None
        for i in range(7):
            gx, gy = cx + 3 + (i % 4) * 5, cy + 12 + (i // 4) * 6
            s.rect(gx, gy, 4, 4, '#e8e0d0'); s.line(gx, gy, gx + 3, gy + 3, '#e0302a'); s.line(gx + 3, gy, gx, gy + 3, '#e0302a')
        s.px(cx + 12, cy + 1, '#e0302a')                                  # pin
        sn = s.rect(cx + 23, cy + 9, 10, 10, '#f6d85a')                   # sticky note "7:00 !!"
        s.rect(cx + 23, cy + 9, 10, 2, '#e8c040')
        digits(s, cx + 24, cy + 12, '7', '#2a1a1a'); s.px(cx + 28, cy + 13, '#2a1a1a'); s.px(cx + 28, cy + 15, '#2a1a1a')
        s.px(cx + 30, cy + 12, '#e0302a'); s.px(cx + 30, cy + 13, '#e0302a'); s.px(cx + 30, cy + 15, '#e0302a')
        s.px(cx + 31, cy + 12, '#e0302a'); s.px(cx + 31, cy + 13, '#e0302a'); s.px(cx + 31, cy + 15, '#e0302a')
        s.px(cx + 27, cy + 9, '#3a8ae0')
        # polaroid
        s.rect(cx + 24, cy + 21, 8, 6, '#f2ece0'); s.rect(cx + 25, cy + 22, 6, 3, '#4a6a9a')
        # framed game poster (left of headboard)
        pm = s.rect(122, 34, 22, 30, GOLD[2]); s.rect(123, 35, 20, 28, '#241a4a')
        s.ell(133, 46, 5, 5, '#ff8a5a'); s.ell(133, 46, 3, 3, '#ffd27a')
        s.rect(125, 53, 16, 1, '#ffd85a'); s.text(126, 54, 'LV99', '#ffd85a', 'silk')
        # string lights wire (bulbs drawn per frame)
        self.bulbs = []
        for i in range(16):
            u = i / 15; xb = 118 + 104 * u
            self.bulbs.append((xb, 26 + 6 * abs(math.sin(math.pi * (u * 3)))))
        for (a, b) in zip(self.bulbs, self.bulbs[1:]): s.line(a[0], a[1], b[0], b[1], '#05040a')
        # wall socket + plug
        sx, sy = self.A['socket']
        s.rect(sx - 2, sy - 2, 6, 6, '#c8c4bc'); s.rect(sx - 1, sy - 1, 4, 4, '#1a1a1a'); s.rect(sx, sy, 2, 3, '#e8e8e8')

    def _rug_bed(self, s):
        yy = s.yy
        rug = s.poly([(92, 178), (272, 178), (240, 126), (122, 126)], '#3a1426')
        inner = s.poly([(100, 172), (264, 172), (236, 130), (128, 130)], '#4a1a30'); s.outline(inner, GOLD[1])
        for k in range(7): s.ell(140 + k * 14, 166, 2, 1, GOLD[1])
        # headboard (tufted, gold trim)
        hb = s.rect(140, 70, 80, 50, '#3a1a1c')
        s.part(s.M_rect(142, 72, 76, 46), ['#2a1014', '#44201e', '#5a2c26', '#6e3a30'], bevel=4, amb=0.35, outline=None)
        for r in range(3):
            for c in range(5):
                bx, by = 150 + c * 15 + (7 if r % 2 else 0), 80 + r * 10
                if bx < 214: s.px(bx, by, GOLD[2]); s.px(bx, by + 1, '#24100e')
        s.rect(140, 69, 80, 2, GOLD[2]); s.rect(140, 69, 80, 1, GOLD[3]); s.outline(hb)
        # bed frame + mattress
        s.poly([(132, 118), (228, 118), (252, 170), (108, 170)], '#2a1214')
        s.poly([(108, 170), (252, 170), (252, 178), (108, 178)], '#1e0c0e'); s.rect(108, 170, 144, 1, GOLD[2])
        s.poly([(136, 112), (224, 112), (246, 162), (114, 162)], SHEET[2])
        # pillow
        pil = s.M_ell(180, 104, 30, 8)
        s.part(pil, SHEET, bevel=4, light=(-0.2, -0.8, 0.6), amb=0.45, ink='#2a2440')

    def _nightstand(self, s):
        ns = s.poly([(226, 98), (256, 98), (262, 128), (222, 128)], WOOD[2])
        s.part(ns, WOOD, bevel=3, light=(0.5, -0.6, 0.6), amb=0.35, ink='#07050a')
        s.poly([(226, 98), (256, 98), (257, 101), (225, 101)], WOOD[4])
        s.rect(236, 112, 10, 2, GOLD[2]); s.rect(226, 107, 34, 1, '#120a08')
        # lamp: base + shade (emissive inside rim)
        lx, ly = self.A['lamp']
        s.rect(lx - 1, ly + 2, 2, 10, GOLD[2]); s.ell(lx, ly + 12, 4, 1.5, GOLD[1])
        shade = s.M_poly([(lx - 8, ly + 2), (lx + 8, ly + 2), (lx + 5, ly - 8), (lx - 5, ly - 8)])
        s.part(shade, SHADE, bevel=3, light=(0.0, 0.2, 1.0), amb=0.6, ink='#5a2a08', E=0.75)
        s.rect(lx - 7, ly + 2, 14, 1, '#fff6d8', 1.0)
        # water glass
        g = s.rect(228, 92, 4, 6, '#9ab8d8'); s.rect(228, 95, 4, 3, '#6a8ab8'); s.px(228, 92, '#e8f4ff'); s.outline(g, '#0a0a14')
        # clock body
        ck = s.rect(244, 89, 16, 9, '#0e0c12'); s.outline(ck); s.rect(245, 98, 2, 1, '#2a2a2a'); s.rect(257, 98, 2, 1, '#2a2a2a')

    def _floor_clutter(self, s):
        # slippers (one flipped), socks, paper balls, controller, the book in the moonbeam
        for (x, y, flip) in ((104, 150, False), (116, 156, True)):
            m = s.M_ell(x, y, 6, 2.6)
            s.part(m, ['#3a4a6a', '#5a6a8a', '#8a9ab8'] if not flip else ['#1a1a24', '#2a2a36', '#3a3a48'], bevel=2, amb=0.4, ink='#07050a')
            if not flip: s.rect(x - 3, y - 2, 4, 2, '#e8e4f0')
        s.poly([(268, 150), (276, 148), (278, 152), (270, 154)], '#d8d4e8'); s.rect(268, 150, 2, 4, '#d8d4e8')
        for (x, y) in ((70, 142), (82, 136), (282, 132)):
            s.part(s.M_ell(x, y, 2.6, 2.2), ['#8a8478', '#c8c0b0', '#f2ece0'], bevel=1.5, amb=0.5, ink='#2a2420')
        # controller with a cable
        cm = s.M_ell(150, 174, 7, 3) | s.M_ell(144, 175, 3, 3) | s.M_ell(156, 175, 3, 3)
        s.part(cm, ['#1a1a24', '#2a2a3a', '#46465a'], bevel=2, amb=0.4, ink='#050308')
        s.px(147, 173, '#e0402a', 0.9); s.px(153, 173, '#3a9ae0', 0.9)
        for k in range(18): s.px(157 + k, 176 - 2 * math.sin(k / 4), '#0a0a12')
        # the book: 《早睡指南》 face down, in the moonbeam
        bx, by = self.A['book']
        bk = s.poly([(bx - 12, by), (bx + 8, by - 4), (bx + 13, by + 4), (bx - 7, by + 8)], '#c8402a')
        s.part(bk, ['#5a1410', '#9a2a1c', '#c8402a', '#e86a4a'], bevel=2, amb=0.45, ink='#1a0606')
        s.poly([(bx - 7, by + 8), (bx + 13, by + 4), (bx + 13, by + 5), (bx - 7, by + 9)], '#f2ece0')
        s.text(bx - 7, by - 4, '早睡', '#ffe6a0', 'zh10')

    def _chair(self, s):
        # the clothes chair (right foreground): legs, back, a heap of hoodies / jeans / a towel
        s.rect(282, 138, 3, 42, '#1a0e0c'); s.rect(312, 140, 3, 40, '#140a08')
        s.rect(292, 70, 4, 70, '#2a1812'); s.rect(316, 66, 4, 74, '#24140e')
        s.rect(290, 70, 32, 4, '#3a2216')
        heap = s.M_poly([(274, 140), (282, 112), (296, 100), (312, 96), (322, 104), (322, 146), (300, 150)])
        s.part(heap, ['#1a1a2a', '#2a2e44', '#3e4462', '#566088'], bevel=5, light=(-0.6, -0.5, 0.6), amb=0.3, ink='#05040a')
        jeans = s.M_poly([(290, 108), (308, 104), (306, 150), (298, 152), (294, 124)])
        s.part(jeans, ['#16243e', '#22365a', '#304a78', '#40609a'], bevel=3, light=(-0.6, -0.5, 0.6), amb=0.3, ink='#05040a')
        sleeve = s.M_poly([(278, 118), (286, 116), (284, 160), (278, 162)])
        s.part(sleeve, ['#3a1a24', '#5a2a36', '#7a3a48'], bevel=2, amb=0.35, ink='#05040a')
        s.rect(278, 158, 6, 3, '#e8e4f0')
        towel = s.M_poly([(300, 96), (322, 92), (322, 104), (304, 106)])
        s.part(towel, ['#3a6a5a', '#5a9a82', '#8acab0'], bevel=2, amb=0.4, ink='#05040a')

    # ================================================================ dynamic
    def blanket(self, s, chest=0.0):
        yy = s.yy
        top = 113 - chest
        bl = s.M_poly([(134, top + 2), (226, top + 2), (248, 166), (112, 166)]) | s.M_ell(180, top + 4, 46, 5)
        s.part(bl, BLANK, bevel=2.5, light=(-0.2, -0.8, 0.55), amb=0.45, ink='#07060e')
        torso = s.M_ell(182, top + 14, 30, 12) & bl
        legs = (s.M_ell(170, 146, 14, 14) | s.M_ell(196, 148, 14, 13)) & bl
        s.part(torso | legs, BLANK, bevel=7, light=(-0.3, -0.85, 0.45), amb=0.3, outline=None, bias=0.05)
        for (a, b) in [((146, 128), (134, 162)), ((222, 128), (236, 160)), ((183, 140), (183, 162))]:
            s.line(a[0], a[1], b[0], b[1], BLANK[1], mask=bl)
        s.fill(bl & (yy >= top + 1) & (yy <= top + 3) & (np.abs(s.xx - 180) < 44), SHEET[3])
        s.fill(bl & (yy == top + 4) & (np.abs(s.xx - 180) < 44), SHEET[1])
        return bl

    def phone_shape(self, s, px, py, tilt=0.0, screen=(150, 220, 255), on=1.0, w=22, h=7):
        """phone held screen-down above the face: we see its back + bottom edge, screen light leaks below."""
        c, sn = math.cos(tilt), math.sin(tilt)
        def P(x, y): return (px + x * c - y * sn, py + x * sn + y * c)
        back = s.M_poly([P(-w / 2, -h / 2), P(w / 2, -h / 2), P(w / 2, h / 2 - 1), P(-w / 2, h / 2 - 1)])
        s.part(back, ['#241a30', '#3a2c4a', '#5a4a72', '#7a6a98'], bevel=2, light=(-0.3, -0.8, 0.5), amb=0.45, ink='#04030a')
        edge = s.M_poly([P(-w / 2, h / 2 - 1), P(w / 2, h / 2 - 1), P(w / 2, h / 2), P(-w / 2, h / 2)])
        s.fill(edge, tuple(int(v) for v in screen), 0.95 * on)
        cam = P(-w / 2 + 2, -h / 2 + 1); s.rect(cam[0], cam[1], 4, 3, '#0a0a10'); s.px(cam[0] + 1, cam[1] + 1, '#6a6a8a')
        st_ = P(4, -1); s.ell(st_[0], st_[1], 2, 1.6, '#ffd24a'); s.px(st_[0], st_[1], '#e0402a')      # a sticker
        return back | edge

    def frame(self, t=0.0, face='tired', look=(0, 2), phone='up', phone_xy=None, phone_tilt=0.0, head_dy=0, tilt=0.0,
              cat='curl', cat_look=(0, 0), cat_blink=False, clock='0347', colon=True, screen=(150, 220, 255), bulbs=1.0,
              monitor=1.0, arms_k=1.0, person=True, chest=None):
        s = self.st.from_snapshot(self.base)
        # monitor screensaver: a bouncing "zZ"
        if monitor > 0:
            s.fill(self.mon_screen, '#0c0a1e', 0.3 * monitor)
            u = (t * 9) % 40; v = (t * 6) % 24
            zx = 12 + (u if u < 20 else 40 - u); zy = 88 + (v if v < 12 else 24 - v) - (zx - 12) * 0.35
            s.text(zx, zy, 'zZ', '#7a6aff', 'silk', 0.9 * monitor)
        if person:
            ch = (0.6 + 0.6 * math.sin(t * 2 * math.pi / 3.6)) if chest is None else chest
            p = human.draw(SLEEPER, face=face, arms='rest', look=look, head_dy=head_dy, tilt=tilt)
            hs = p.body.cv.a[:31, :].copy(); he = p.body.E[:31, :]
            hx, hy = self.A['head']
            s.sprite(hs, hx - p.ax, hy - p.ay, E=he)
            self.blanket(s, chest=ch)
            # one arm raised to the phone (hoodie sleeve: shoulder -> elbow -> hand), the other under the blanket
            if phone == 'up' and arms_k > 0:
                px, py = phone_xy or self.A['phone']
                sh_, el, hd = (202, 118), (210, 104), (px + 10, py + 2)
                for (a, b) in ((sh_, el), (el, hd)):
                    m = np.zeros((self.H, self.W), bool)
                    n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) + 1
                    for i in range(n + 1):
                        u = i / n; m |= s.M_ell(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, 3.2, 3.2)
                    s.part(m, ['#22305a', '#33457a', '#4a5e9a', '#6a7eb8'], bevel=2.5, light=(-0.3, -0.8, 0.5), amb=0.35, ink='#07060e')
                self._arm_hand = hd
            elif phone in ('smack', 'drop', 'none'):
                for sgn in (-1, 1):       # arms flopped on the blanket
                    s.part(s.M_ell(180 + sgn * 30, 122, 8, 3), ['#2a3a62', '#3a4a72', '#4a5a86'], bevel=2, amb=0.4, ink='#07060e')
                    s.ell(180 + sgn * 38, 122, 2.5, 2, SLEEPER.skin)
        else:
            self.blanket(s, chest=0)
        # charger cable: socket -> nightstand side -> over the blanket -> phone
        sx, sy = self.A['socket']
        if phone == 'up':
            tx, ty = (phone_xy or self.A['phone'])[0] + 9, (phone_xy or self.A['phone'])[1] + 2
            pts = [(sx + 1, sy + 3), (sx - 6, sy + 10), (232, 112), (212, 104), (tx, ty)]
        elif phone == 'smack':
            pts = [(sx + 1, sy + 3), (sx - 6, sy + 10), (232, 112), (212, 108), (194, 104)]
        else:
            pts = [(sx + 1, sy + 3), (sx - 6, sy + 12), (238, 130), (220, 128), (204, 122)]
        for (a, b) in zip(pts, pts[1:]): s.line(a[0], a[1], b[0], b[1], '#e8e4f0')
        # phone
        if person and phone == 'up':
            px, py = phone_xy or self.A['phone']
            self.phone_shape(s, px, py, phone_tilt, screen)
            hx_, hy_ = px + 9, py + 3
            hm = s.M_ell(hx_, hy_, 3.4, 3.4) | s.M_ell(hx_ - 4, hy_ - 2, 2.2, 1.6)
            s.part(hm, ['#b0705a', '#e0a07a', '#f6c8a0'], bevel=1.5, amb=0.5, ink='#3a1a14')
            th = getattr(self, 'thumb', 0.0)
        elif person and phone == 'smack':
            fx, fy = self.A['face']
            self.phone_shape(s, fx + 3, fy - 1, -0.32, screen, on=0.5, w=26, h=16)
        elif phone == 'drop':
            m = s.poly([(196, 120), (214, 117), (216, 124), (198, 127)], tuple(int(v) for v in screen), 0.95); s.outline(m)
        # cat at the foot of the bed
        cx, cy = self.A['cat']
        CAT.draw(s, cx, cy, pose=cat, t=t, look=cat_look, blink=cat_blink)
        # clock digits
        if clock:
            c = '#ff3a2e'
            digits(s, 245, 91, clock[:2], c); digits(s, 253, 91, clock[2:], c)
            if colon: s.px(252, 92, c, 1.0); s.px(252, 94, c, 1.0)
        # fairy bulbs
        for i, (x, y) in enumerate(self.bulbs):
            k = bulbs * (0.7 + 0.3 * math.sin(t * 2.2 + i * 1.9))
            if k > 0.05: s.rect(int(x), int(y) + 1, 1, 2, ['#ffcf6a', '#ff8a5a', '#ffe9a8', '#9ad8ff'][i % 4], k)
        return s

    def light(self, s, phone_k=1.0, lamp_k=1.0, moon_k=1.0, room_k=1.0, screen_col=(0.5, 0.8, 1.0), phone_xy=None, bulbs=1.0):
        L = s.light_base((0.62, 0.56, 0.78), 0.30 * room_k)
        if phone_k > 0:
            px, py = phone_xy or (180, 96)
            L = L + s.band(px, py + 8, 52, 30, screen_col, [(1.0, 0.16 * phone_k), (0.62, 0.34 * phone_k), (0.32, 0.62 * phone_k)])
        if lamp_k > 0:
            lx, ly = self.A['lamp']
            L = L + s.band(lx, ly + 8, 96, 70, (1.0, 0.62, 0.32), [(1.0, 0.14 * lamp_k), (0.62, 0.32 * lamp_k), (0.34, 0.62 * lamp_k), (0.16, 0.9 * lamp_k)])
        if moon_k > 0:
            L = L + (self.beam[..., None] * np.array([0.16, 0.2, 0.42], np.float32) * moon_k)
            wx, wy, ww, wh = self.A['window']
            L = L + s.band(wx + ww / 2, wy + wh / 2, 46, 40, (0.4, 0.5, 0.9), [(1.0, 0.10 * moon_k), (0.6, 0.2 * moon_k)])
        L = L + s.band(24, 96, 30, 24, (0.5, 0.45, 1.0), [(1.0, 0.10 * room_k)])          # monitor standby
        L = L + s.band(170, 30, 70, 14, (1.0, 0.7, 0.4), [(1.0, 0.10 * bulbs), (0.5, 0.18 * bulbs)])
        return L

    def air(self, s, moon_k=1.0, lamp_k=1.0, phone_k=1.0, phone_xy=None):
        wx, wy, ww, wh = self.A['window']
        a = s.cone((wx + ww / 2, wy + 10), (wx - 30, 180), (wx + ww + 60, 180), (0.35, 0.45, 0.9), 0.03 * moon_k)
        if phone_k > 0:
            px, py = phone_xy or self.A['phone']
            a = a + s.cone((px, py + 3), (px - 20, py + 26), (px + 18, py + 26), (0.45, 0.75, 1.0), 0.06 * phone_k)
        return a
