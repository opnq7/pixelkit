"""结尾 v2 · 外挂商店 → 回到存档点（时间重新走动）→ 天亮 → 评论区：Ending().frame(t)。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math, os
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s6_end'))
import numpy as np
import timeline as TL
from common import subs_layer, lerp, smooth, FPS, hud2, Anchor, keyed
from pixelkit import ui, gameui as G, acting as A
from pixelkit.core import C, scale_nearest
from pixelkit.edit import Edit
from pixelkit.scene import ui_over
from pixelkit.pixstage import cam as pcam, GRADE_WARM
from pixelkit.plates import Plate
from pixelkit.anim import back_out, clamp01

PL = (_PROJ + '/assets/plates/')
def eo3(u): u = clamp01(u); return 1 - (1 - u) ** 3

# name, plate position of the item, rarity colour, effect line
ITEMS = [('电灯', (124, 40), C('#ffd34a'), '删除黑夜', TL.T_BULB), ('咖啡', (163, 42), C('#d89a5a'), '屏蔽困意', TL.T_COFFEE),
         ('手机', (199, 42), C('#7fd0ff'), '伪造白天', TL.T_PHONE)]
TIMES = ['02:30', '04:10', '通宵', '01:00 算早吗', '六点刚躺下', '00:30 乖宝宝', '03:56（同款）', '看完这条就睡']
SHOP_KEYS = [(0.0, 1.22, 160, 82), (TL.T_BULB - 0.55, 1.5, 150, 76),
             (TL.T_BULB - 0.1, 2.5, 148, 52), (TL.T_COFFEE - 0.35, 2.5, 148, 52),
             (TL.T_COFFEE, 2.5, 187, 54), (TL.T_PHONE - 0.35, 2.5, 187, 54),
             (TL.T_PHONE, 2.5, 223, 54), (TL.T_ROW - 0.45, 2.5, 223, 54),
             (TL.T_ROW + 0.3, 1.3, 160, 80), (TL.S_SKIP, 1.4, 160, 80)]

class Ending:
    def __init__(self):
        self.pF, self.pC = Plate(PL + 'F.png'), Plate(PL + 'F-C.png')
        self.anchor = Anchor()
        rgb = self.pF.rgb
        self.icons = []
        for _, (ix, iy), *_ in ITEMS:
            crop = rgb[iy - 12:iy + 12, ix - 12:ix + 12]
            self.icons.append(np.dstack([crop, np.full(crop.shape[:2], 255, np.uint8)]))
        e = self.ed = Edit()
        e.add('shop', TL.S_SHOP, self.f_shop)
        e.add('skip', TL.S_SKIP, self.f_skip, 'whip', 0.3, dir=1)
        e.add('wake', TL.S_WAKE, self.f_wake, 'dissolve', 0.6)
        e.add('rank', TL.S_RANK, self.f_rank, 'dissolve', 0.5)
        e.end(TL.END)
        self.act = A.Act(face='happy', float_amp=1.6, look=(0, -1))
        self.act.hold(TL.T_BULB, TL.T_ROW, face='wow', look=(0, -2)).beat(TL.T_COIN + 0.1, 'sigh', dur=0.9)
        self.act.beat(TL.T_CASE + 0.2, 'ask', dur=0.9).beat(TL.T_BTN + 0.25, 'take', look=(3, 1), dur=0.8)
        self.act.hold(TL.T_BTN + 1.05, TL.T_PUSH, face='squint', look=(3, 1)).beat(TL.T_PUSH, 'point', dir=1, dur=0.5)
        self.act.beat(TL.T_PUSH + 0.5, 'nodyes', dur=0.6)
        self.act_back = A.Act(face='happy', float_amp=1.8, look=(1, 1)).beat(TL.T_REVIVE + 0.05, 'cheer', dur=0.9)

    def fi(self, t): return int(round(t * FPS))
    def compose(self, img, cv): return ui_over(img, cv.a, scale=4)

    def hud(self, t, loc=True):
        cv = hud2(t, 100, 5, 0.0, 'SHOP' if loc else None, '外挂商店', t_enter=0.4, t_out=TL.S_SKIP - 0.3, k=1.0)
        G.question_card(cv, t, TL.T_Q, '人类有没有睡眠外挂？', TL.T_ANS, '没有：每个价签上写的，都是睡眠', hold=4.0, y=34)
        return cv

    def ghost(self, fr, t, x, y, scale=1.0):
        p = self.act.at(t); rgba, E, ax, ay = A.ghost_sprite(p, t)
        if abs(scale - 1) > 0.02: rgba = scale_nearest(rgba, scale); E = scale_nearest(E, scale)
        fr.sprite(rgba, x + p['dx'] - ax * scale, y + p['dy'] - ay * scale, E=E)
        return p, (x + p['dx'], y + p['dy'] - 24 * scale)

    @staticmethod
    def path(t, pts):
        if t <= pts[0][0]: return pts[0][1], pts[0][2]
        for (t0, x0, y0), (t1, x1, y1) in zip(pts, pts[1:]):
            if t < t1:
                u = smooth((t - t0) / max(1e-3, t1 - t0)); return lerp(x0, x1, u), lerp(y0, y1, u)
        return pts[-1][1], pts[-1][2]

    # ------------------------------------------------------------------ 1. the cheat shop: one item at a time, then the same price tag on all three
    def f_shop(self, t):
        P = self.pF; fr = P.frame()
        pts = [(0.0, 30, 112), (3.2, 96, 106), (TL.T_BULB - 0.1, 92, 74), (TL.T_COFFEE - 0.1, 130, 76), (TL.T_PHONE - 0.1, 166, 76),
               (TL.T_ROW - 0.2, 184, 76), (TL.T_ROW + 0.7, 150, 108), (99, 150, 108)]
        gx, gy = self.path(t, pts)
        z_ = keyed(t, SHOP_KEYS)[0]
        p, head = self.ghost(fr, t, gx, gy, scale=0.85 if z_ < 1.8 else 0.5)
        L = P.light(fr) * P.flicker(fr, t, seed=3, amp=0.1)[..., None]
        cur = None
        for i, (name, (ix, iy), col, eff, t0) in enumerate(ITEMS):
            t1 = ITEMS[i + 1][4] if i < 2 else TL.T_ROW - 0.3
            if t0 <= t < t1 + 0.1: cur = i
            if t0 <= t < TL.T_ROW + 3.5:                                             # the lit item keeps its warm pool, with a glint
                L = L + fr.band(ix, iy, 20, 16, (1.0, 0.9, 0.6), [(1.0, 0.22), (0.5, 0.4)])
                ph = (t * 1.7 + i * 0.4) % 1.0
                if ph < 0.35: fr.px(ix + 9 - 4 * ph, iy - 9 + 4 * ph, '#ffffff', 0.9)
        z, cx, cy = keyed(t, SHOP_KEYS)
        c = pcam(z, cx, cy)
        img = fr.render(c, L, GRADE_WARM, frame=self.fi(t))
        img = img + (1 - img) * (1 - smooth(t / 0.6))
        cv = self.hud(t)
        A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if t < TL.T_ROW - 0.2:
            for i, (name, _, col, eff, t0) in enumerate(ITEMS):
                t1 = ITEMS[i + 1][4] - 0.12 if i < 2 else TL.T_ROW - 0.3
                if t0 <= t < t1:
                    G.item_card(cv, t, t0 + 0.1, 262, 74, self.icons[i], name, eff, price='睡眠', price_t=99, rarity=col, w=150, life=t1 - t0 - 0.1)
        else:                                                                            # the three cards line up; every price tag flips to the same coin
            for i, (name, _, col, eff, _) in enumerate(ITEMS):
                G.item_card(cv, t, TL.T_ROW + i * 0.14, 64 + i * 120, 88, self.icons[i], name, eff, price='睡眠', price_t=TL.T_PRICE + i * 0.14,
                            rarity=col, w=112, life=TL.S_SKIP + 0.1 - TL.T_ROW - i * 0.14)
            if t >= TL.T_COIN:
                a = clamp01((t - TL.T_COIN) / 0.2)
                G._panel(cv, 8, 40, 116, 22, a)
                cv.ellipse(22, 51, 6, 6, (200, 200, 255, int(255 * a))); cv.ellipse(24, 49, 5, 5, (30, 30, 50, int(255 * a)))
                cv.text(34, 44, '睡眠币 × 0', (255, 236, 200, int(255 * a)), 'zh10')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 2. "free skip sleep": not found. the familiar button, pushed away
    def f_skip(self, t):
        P = self.pF; fr = P.frame()
        cx, cy = 172, 90
        # glass dome on a pedestal: empty, cobwebs, a lonely '?'
        fr.rect(cx - 17, cy, 34, 5, '#6a4420'); fr.rect(cx - 17, cy, 34, 1, '#a8743a'); fr.rect(cx - 15, cy + 5, 30, 2, '#3a2410')
        dome = fr.M_ell(cx, cy, 15, 20) & (fr.yy < cy)
        fr.add(dome, (16, 22, 30))
        fr.fill(fr.ring(dome) & (fr.yy < cy), (210, 228, 245), 0.3)
        for k in range(4): fr.px(cx - 10, cy - 24 + k * 1.2 + (k > 1), '#ffffff', 0.8)
        for a_, b_ in (((cx - 12, cy - 16), (cx - 3, cy - 8)), ((cx - 3, cy - 8), (cx + 9, cy - 15)), ((cx + 9, cy - 15), (cx + 12, cy - 6))):
            fr.line(a_[0], a_[1], b_[0], b_[1], '#cfcfd8', 0.35)
        fr.text(cx - 3, cy - 18, '?', '#ffe6a0', 'zh12', 0.8)
        # the familiar red button: drops in, gets shoved off the counter
        bx, by = 214, 87
        if t >= TL.T_BTN:
            q = clamp01((t - TL.T_BTN) / 0.35); by = 87 - 40 * (1 - back_out(q, 1.6))
            if t >= TL.T_PUSH:
                u = t - TL.T_PUSH; bx = 214 + 70 * u * 1.4 + 20 * u * u; by = 87 + (0 if bx < 236 else 60 * (bx - 236) ** 2 / 900)
            fr.part(fr.M_ell(bx, by + 3, 14, 5), ['#161018', '#2a2230', '#4a4258'], bevel=1, amb=0.4, ink='#08060a')
            fr.part(fr.M_ell(bx, by - 3, 10.5, 7) & (fr.yy < by + 3), ['#4a0610', '#9a1220', '#d82a38', '#ff6a60'], bevel=2.5, amb=0.3, ink='#1a0206', E=0.2)
            fr.px(bx - 4, by - 7, '#ffd0c8'); fr.px(bx - 3, by - 7, '#ffd0c8')
        pts = [(TL.S_SKIP, 118, 104), (TL.T_BTN, 118, 104), (TL.T_PUSH - 0.2, 192, 104), (TL.T_PUSH + 0.5, 192, 104), (TL.S_WAKE, 150, 100)]
        gx, gy = self.path(t, pts)
        p, head = self.ghost(fr, t, gx, gy, scale=0.85)
        L = self.pF.light(fr) * self.pF.flicker(fr, t, seed=3, amp=0.1)[..., None] + fr.band(cx, cy - 10, 22, 22, (1.0, 0.92, 0.7), [(1.0, 0.2), (0.5, 0.3)])
        if t >= TL.T_BTN: L = L + fr.band(bx, by, 18, 12, (1.0, 0.4, 0.35), [(1.0, 0.2)])
        k = smooth((t - TL.S_SKIP) / 6.0)
        c = pcam(lerp(2.0, 2.12, k), 172, 80)
        img = fr.render(c, L, GRADE_WARM, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        a = clamp01((t - TL.T_CASE) / 0.25)
        x0, y0, w = 20, 74, 176
        G._panel(cv, x0, y0, w, 62, a, accent=C('#ff8a6a'))
        cv.text(x0 + 10, y0 + 5, '免费跳过睡眠', (255, 236, 200, int(255 * a)), 'zh12')
        if t >= TL.T_SEARCH:
            prog = min(0.99, 0.99 * eo3((t - TL.T_SEARCH) / 1.0))
            cv.rect(x0 + 10, y0 + 26, 104, 8, (20, 18, 30, int(255 * a))); cv.rect(x0 + 10, y0 + 26, int(104 * prog), 8, (255, 200, 90, int(255 * a)))
            cv.text(x0 + 122, y0 + 24, f'{int(prog * 100)}%', (255, 200, 90, int(255 * a)), 'p2p')
            cv.text(x0 + 10, y0 + 40, '搜索 1938 → 至今', (210, 200, 190, int(255 * a)), 'zh10')
            if t >= TL.T_SEARCH + 1.1: ui.rubber_stamp(cv, x0 + 126, y0 + 62, '未找到', t - TL.T_SEARCH - 1.1, fname='zh12', angle=-6)
        if TL.T_BTN <= t < TL.T_PUSH + 0.6:
            b = clamp01((t - TL.T_BTN - 0.25) / 0.2) * (1 - clamp01((t - TL.T_PUSH - 0.3) / 0.3))
            G._panel(cv, 306, 74, 140, 50, b, accent=C('#c84050'))
            cv.text(316, 79, '我还能再熬会儿', (255, 226, 210, int(255 * b)), 'zh12')
            cv.text(316, 99, '价格：睡眠 × 无限', (255, 120, 110, int(255 * b)), 'zh10')
            if t >= TL.T_PUSH + 0.3: ui.rubber_stamp(cv, 380, 112, '不要了', t - TL.T_PUSH - 0.3, fname='zh12', scale=2, angle=-8)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 3. back at the 03:56 save point: revive, the ghost dives in, time resumes, dawn
    def f_wake(self, t):
        woke = t >= TL.T_WAKE
        floating = t < TL.T_DIVE
        diving = TL.T_DIVE <= t < TL.T_DIVE + 0.5
        face = 'closed' if not woke else ('surprised' if t < TL.T_WAKE + 0.7 else 'soft')
        k_clock = smooth((t - TL.T_CLOCK) / 1.5)
        mins = int(lerp(3 * 60 + 56, 7 * 60 + 12, k_clock)); clock = f'{mins // 60:02d}{mins % 60:02d}'
        dawn = smooth((t - TL.T_WAKE) / 2.0)
        screen = (150, 210, 240) if t < TL.T_FACEDOWN else (20, 20, 26)
        img, c, p, head = self.anchor.render(
            t, 0.9 + 0.1 * smooth((t - TL.S_WAKE) / 0.6), z=lerp(1.55, 1.3, smooth((t - TL.S_WAKE) / 4.5)), cx=186, cy=100, frame_i=self.fi(t),
            ghost_xy=(150, 84) if floating else None, ghost_act=self.act_back if floating else None,
            dive=(TL.T_DIVE, (150, 84), (180, 98)) if diving else None,
            clock=clock, face=face, phone='drop' if woke else 'smack', screen=screen, dawn=dawn, cat='curl' if t < TL.T_REVIVE + 1.5 else 'up')
        lift = 0.2 + 0.15 * smooth((t - TL.T_WAKE) / 2.0)
        img = np.clip((np.clip(img, 0, 1) ** 0.8) * (1.3 + lift) + 0.02, 0, 1)
        cv = self.hud(t, loc=False)
        if p is not None: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if TL.T_REVIVE <= t < TL.T_REVIVE + 1.4:
            d = t - TL.T_REVIVE; k = back_out(clamp01(d / 0.3), 1.6) * (1 - clamp01((d - 1.1) / 0.3))
            if k > 0.04:
                G.big_zh(cv, '复活成功', 240 - G.text_width('复活成功', 'zh12') * 3 // 2, 100, 3, C('#7fe0ff'), min(1, k))
                if d < 0.5: G.burst_lines(cv, 240, 118, 80 + 200 * d, 100 + 240 * d, 18, C('#bff4ff'), 1 - d / 0.5)
        if t >= TL.T_TIP:
            a = clamp01((t - TL.T_TIP) / 0.25)
            G.quest_panel(cv, 14, 150, 168, 58, a, '新手提示', 'TIP', (), 1.0)
            cv.text(26, 178, '今晚，别再来了。', (255, 240, 210, int(255 * a)), 'zh12')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 4. the room in the morning: leaderboard + comment prompt + title
    def f_rank(self, t):
        P = self.pC; fr = P.frame()
        L = P.light(fr)
        k = smooth((t - TL.S_RANK) / 6.0)
        c = pcam(lerp(1.0, 1.08, k), 160, 92)
        img = fr.render(c, L, GRADE_WARM, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        a = clamp01((t - TL.T_BOARD) / 0.3)
        x0, y0, w = 128, 34, 224
        G.quest_panel(cv, x0, y0, w, 150, a, '本服夜猫子排行榜', 'RANK', (), 1.0, head_col=C('#2a3a8a'))
        rows = [('1', '？？？', '05:12'), ('2', '？？？', '04:47'), ('3', '你（已复活）', '03:56')]
        for i, (n, who, tm) in enumerate(rows):
            yy = y0 + 28 + i * 22
            b = clamp01((t - TL.T_BOARD - 0.3 - i * 0.25) / 0.2)
            col = (255, 226, 120) if i == 0 else (230, 225, 240)
            cv.text(x0 + 12, yy, n, col + (int(255 * b),), 'p2p'); cv.text(x0 + 34, yy, who, col + (int(255 * b),), 'zh10')
            cv.text(x0 + w - 12 - G.text_width(tm, 'p2p'), yy, tm, col + (int(255 * b),), 'p2p')
        b = clamp01((t - TL.T_BOARD - 1.2) / 0.2)
        yy = y0 + 100
        cv.rect(x0 + 10, yy - 2, w - 20, 22, (14, 16, 34, int(255 * b)))
        caret = '_' if int(t * 3) % 2 else ' '
        cv.text(x0 + 16, yy + 2, '你：__:__ ' + caret, (127, 224, 255, int(255 * b)), 'zh12')
        cv.text(x0 + 16, yy + 26, '↓ 评论区报个时间', (255, 210, 150, int(255 * b)), 'zh10')
        for i, s_ in enumerate(TIMES[:7]):
            G.danmaku(cv, t, TL.T_BOARD + 1.0 + i * 0.55, s_, y=[196, 212][i % 2], speed=130, col=C('#ffffff') if i % 3 else C('#ffd84a'))
        if t >= TL.T_LOGO:
            kk = clamp01((t - TL.T_LOGO) / 0.4)
            cv.rect(0, 0, 480, 270, (0, 0, 0, int(232 * kk)))
            G.big_zh(cv, '熬夜副本', 240 - G.text_width('熬夜副本', 'zh12') * 2, 110, 4, C('#ffd34a'), kk)
        return self.compose(img, cv)

    def frame(self, t):
        img = self.ed.frame(min(t, TL.END - 1e-3))
        return ui_over(img, subs_layer(t, TL.L, TL.HL).a, scale=5)

def make(**kw): return Ending(**kw)
