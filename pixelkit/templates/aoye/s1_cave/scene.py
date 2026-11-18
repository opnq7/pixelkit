"""第 1 关 v2 · 1938 没有太阳的洞穴：一个问题 → 洞穴实验 → 一个答案 → 回到存档点（+20%）。Level1().frame(t)。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s1_cave'))
import numpy as np
import timeline as TL
from common import (subs_layer, lerp, smooth, FPS, put_human, nightcap, ghost_dive, hud2, revive_curve, Anchor, keyed)
from pixelkit import ui, gameui as G, acting as A
from pixelkit.core import C, scale_nearest
from pixelkit.edit import Edit
from pixelkit.scene import ui_over
from pixelkit.pixstage import Stage, cam as pcam, GRADE_NIGHT
from pixelkit.plates import Plate
from pixelkit.sets.cave320 import GRADE_CAVE
from pixelkit.sets.hub_doors import HubDoors
from pixelkit.sets.bedroom320 import Bedroom320
from pixelkit.sets import symbols as SY
from pixelkit.characters import human
from pixelkit.characters.cast_sleep import KLEITMAN, STUDENT, SUBJECT
from pixelkit.anim import back_out, clamp01

PL = (_PROJ + '/assets/plates/')
def eo3(u): u = clamp01(u); return 1 - (1 - u) ** 3
def logz(a, b, k): return math.exp(math.log(a) + (math.log(b) - math.log(a)) * k)

KEY_CAMP = (70, 126); KEY_WALL = (22, 96)
KX, KY = 104, 136                 # Kleitman's spot in the lamp pool (camp plate)
SX_, SY_ = 150, 142               # the student

class Level1:
    def __init__(self):
        self.pA, self.pB, self.pC = Plate(PL + 'L1-A.png'), Plate(PL + 'L1-B.png'), Plate(PL + 'L1-C.png')
        self.hub = HubDoors(); self.bed = Bedroom320(); self.anchor = Anchor()
        e = self.ed = Edit()
        e.add('desc', TL.S_DESC, self.f_desc)
        e.add('camp', TL.S_CAMP, self.f_camp, 'dissolve', 0.3)
        e.add('vs', TL.S_VS, self.f_vs, 'dissolve', 0.4)
        e.add('dark', TL.S_DARK, self.f_vs, 'cut')
        e.add('chalk', TL.S_CHALK, self.f_chalk, 'cut')
        e.add('split', TL.S_SPLIT, self.f_split, 'dissolve', 0.4)
        e.add('nod', TL.S_NOD, self.f_nod, 'cut')
        e.add('thermo', TL.S_THERMO, self.f_thermo, 'dissolve', 0.4)
        e.add('graph', TL.S_GRAPH, self.f_graph, 'cut')
        e.add('exit', TL.S_EXIT, self.f_exit, 'dissolve', 0.5)
        e.add('trip', TL.S_TRIP, self.f_trip, 'cut')
        e.add('anchor', TL.S_ANCHOR, self.f_anchor, 'dissolve', 0.6)
        e.add('hub', TL.S_HUB, self.f_hub, 'dissolve', 0.5)
        e.end(TL.END)
        self.act_in = A.Act(face='wow', float_amp=1.6, look=(2, 0)).beat(TL.T_GHOST_IN1 + 0.1, 'ask', dur=0.8)
        self.act_back = A.Act(face='sad', float_amp=1.8, look=(0, 3)).hold(TL.T_REVIVE, 99, face='happy').beat(TL.T_REVIVE + 0.05, 'cheer', dur=0.9)
        self.act_hub = A.Act(face='happy', float_amp=2.0).beat(TL.T_NEXT, 'ask', dur=0.7)
        self.gear_icon = self._gear_icon()

    def fi(self, t): return int(round(t * FPS))
    def compose(self, img, cv): return ui_over(img, cv.a, scale=4)

    def _gear_icon(self):
        s = Stage(40, 40); s.img[..., 3] = 0
        SY.gear_clock(s, 20, 20, 15, 0.0, 24, hand=3, glow=0.8, spin=0.3)
        a = s.img.copy(); a[..., 3] = np.where(a[..., :3].sum(-1) > 30, 255, 0)
        return a

    # ------------------------------------------------------------------ HUD: one thing at a time
    def hud(self, t, loc=True, pips=False):
        pct, fl = revive_curve(t, TL.T_REVIVE, 0, 20)
        cv = hud2(t, pct, 1 if t > TL.T_REVIVE + 0.6 else 0, fl, '1938' if loc else None, '美国 · 猛犸洞穴 · 地下 40 米',
                  t_enter=TL.T_TAG, t_out=TL.S_TRIP, k=1.0 if pips else 0.0)
        if t < TL.S_ANCHOR + 0.7: G.question_card(cv, t, TL.T_Q, '人按点犯困，是谁在指挥？', TL.T_ANS, '体内有只钟，没有太阳也照样走', hold=4.0, y=34)
        return cv

    def ghost(self, fr, t, act, x, y, scale=1.0):
        p = act.at(t); rgba, E, ax, ay = A.ghost_sprite(p, t)
        if abs(scale - 1) > 0.02: rgba = scale_nearest(rgba, scale); E = scale_nearest(E, scale)
        fr.sprite(rgba, x + p['dx'] - ax * scale, y + p['dy'] - ay * scale, E=E)
        return p, (x + p['dx'], y + p['dy'] - 24 * scale)

    # ------------------------------------------------------------------ 1. descent down the ladder (camera follows it down the plate)
    def f_desc(self, t):
        P = self.pA; fr = P.frame()
        L = P.light(fr)
        z, cx, cy = keyed(t, [(0.0, 2.6, 236, 40), (3.5, 1.1, 160, 92)])
        img = fr.render(pcam(z, cx, cy), L, GRADE_CAVE, frame=self.fi(t))
        img = img + (1 - img) * (1 - smooth(t / 0.55))
        cv = self.hud(t)
        d = int(round(40 * smooth((t - 0.4) / 3.0)))
        a = clamp01((t - 0.3) / 0.3) * (1 - clamp01((t - 3.6) / 0.3))
        if a > 0:
            G._panel(cv, 430, 70, 40, 130, a)
            cv.rect(447, 80, 6, 100, (12, 10, 20, int(255 * a)))
            cv.rect(448, 81, 4, int(98 * d / 40), (255, 200, 90, int(255 * a)))
            s = f'-{d}m'; cv.text(450 - G.text_width(s, 'silkb') // 2, 186, s, (255, 220, 120, int(255 * a)), 'silkb')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 2. camp: the ghost arrives, possesses Kleitman
    def f_camp(self, t):
        P = self.pA; fr = P.frame()
        hit = t >= TL.T_HIT
        white = max(0.0, 1 - (t - TL.T_HIT) / 0.12) if hit else 0.0
        kface = 'focus' if not hit else ('surprised' if t < TL.T_HIT + 0.9 else 'normal')
        put_human(fr, STUDENT, SX_ + 60, SY_, face='normal', arms='hold', look_dir=(-1, 0) if t < TL.T_HIT else (-2, 0))
        top = put_human(fr, KLEITMAN, KX, KY, face=kface, arms='rest', look_dir=(1, 0), white=white)
        if hit and t > TL.T_HIT + 0.15: nightcap(fr, KX, top[1] + 2, t)
        gx = lerp(-20, 150, eo3((t - TL.T_GHOST_IN0) / (TL.T_GHOST_IN1 - TL.T_GHOST_IN0))); gy = 70 + 3 * math.sin(t * 2.4)
        p = None; head = None
        if t < TL.T_POSSESS:
            if t > TL.T_GHOST_IN0: p, head = self.ghost(fr, t, self.act_in, gx, gy)
        else:
            ghost_dive(fr, t, TL.T_POSSESS, (150, 70), (KX, top[1] + 14), 0.45, look=(2, 0))
        L = P.light(fr, key=KEY_CAMP)
        if TL.T_GHOST_IN0 < t < TL.T_HIT: L = L + fr.band(gx, gy, 26, 20, (0.6, 0.8, 1.0), [(1.0, 0.12), (0.5, 0.25)])
        if hit: L = L + fr.band(KX, top[1] + 14, 30, 30, (0.7, 0.9, 1.0), [(1.0, 0.5 * white), (0.5, white)])
        k = smooth((t - TL.T_HIT - 0.1) / 1.3)
        c = pcam(logz(1.15, 2.0, k), lerp(160, KX + 16, k), lerp(94, top[1] + 30, k), sx=(10 * white * math.sin(t * 90)))
        img = fr.render(c, L, GRADE_CAVE, frame=self.fi(t))
        cv = self.hud(t)
        if p is not None: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if hit and t < TL.T_HIT + 0.5:
            ux, uy = c.w2ui(KX, top[1] + 14, 4); d = t - TL.T_HIT
            G.burst_lines(cv, ux, uy, 20 + 160 * d, 34 + 200 * d, 16, C('#bfe8ff'), 1 - d / 0.5)
        G.char_card(cv, t, TL.T_CARD, '克莱特曼', 'LV.43', '拿自己做实验', '1938 · 芝加哥大学 · 生理学家', x=12, y=150, life=4.6)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 3-4. the cave wall: sun or a clock inside?  then the boulder shuts the sun out
    def f_vs(self, t):
        P = self.pB; fr = P.frame()
        dark = t >= TL.S_DARK
        ks = back_out(clamp01((t - TL.T_SUN) / 0.35), 1.6)
        kg = back_out(clamp01((t - TL.T_GEAR) / 0.35), 1.6)
        sun_k = 1.0 - (smooth((t - TL.T_ROLL1 + 0.15) / 0.3) if dark else 0)
        if ks > 0: SY.sun(fr, 96, 66, 24 * ks, t, max(0.05, sun_k))
        if kg > 0: SY.gear_clock(fr, 224, 66, 24 * kg, t, 24, hand=(t * 2) % 24, glow=0.9, spin=t * 0.4)
        if dark:
            u = smooth((t - TL.T_ROLL0) / (TL.T_ROLL1 - TL.T_ROLL0))
            SY.boulder(fr, lerp(-40, 96, u), lerp(80, 74, u), 34, -u * 6)
        if t >= TL.T_VS and not dark:
            d = t - TL.T_VS; sc = 4 if d > 0.08 else 7
            SY.vs_mark(fr, 160, 64, sc)
        top = put_human(fr, KLEITMAN, 160, 170, face='normal' if not dark else 'surprised', arms='chin', look_dir=((-2, 0) if (t % 2) < 1 else (2, 0)))
        nightcap(fr, 160, top[1] + 2, t)
        L = P.light(fr, key=KEY_WALL)
        if ks > 0: L = L + fr.band(96, 66, 90, 70, (1.0, 0.75, 0.4), [(1.0, 0.22 * sun_k), (0.5, 0.4 * sun_k)])
        if kg > 0: L = L + fr.band(224, 66, 90, 70, (0.45, 0.8, 1.0), [(1.0, 0.18), (0.5, 0.36)])
        z = 1.0 if not dark else logz(1.0, 1.7, smooth((t - TL.T_ROLL1) / 1.2))
        cx = 160 if not dark else lerp(160, 224, smooth((t - TL.T_ROLL1) / 1.2))
        sh = 0
        if TL.T_VS <= t < TL.T_VS + 0.25 and not dark: sh = 12 * (1 - (t - TL.T_VS) / 0.25)
        if dark and TL.T_ROLL1 <= t < TL.T_ROLL1 + 0.3: sh = 16 * (1 - (t - TL.T_ROLL1) / 0.3)
        c = pcam(z, cx, 84, sx=sh * math.sin(t * 95))
        img = fr.render(c, L, GRADE_CAVE, frame=self.fi(t))
        cv = self.hud(t)
        if ks > 0.5 and not dark: cv.text(144 - G.text_width('太阳？', 'zh12') // 2, 150, '太阳？', (255, 214, 120, 255), 'zh12', outline=(20, 10, 0, 255))
        if kg > 0.5 and not dark: cv.text(336 - G.text_width('体内的钟？', 'zh12') // 2, 150, '体内的钟？', (160, 230, 255, 255), 'zh12', outline=(0, 10, 20, 255))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 5. the 28-hour clock, chalked on the wall
    def f_chalk(self, t):
        P = self.pB; fr = P.frame()
        ccx, ccy = 176, 74
        k = smooth((t - TL.T_CHALK0) / (TL.T_CHALK1 - TL.T_CHALK0))
        SY.chalk_clock(fr, ccx, ccy, 36, 28, k, segs=[(0, 9, '#7fb8ff'), (9, 19, '#ffb060'), (19, 28, '#8fe0a0')])
        top = put_human(fr, KLEITMAN, 292, 150, face='focus', arms='up', look_dir=(-2, 0), phase=int(t * 6) % 2)
        nightcap(fr, 292, top[1] + 2, t)
        L = P.light(fr, key=KEY_WALL) + fr.band(ccx, ccy, 60, 52, (1.0, 0.8, 0.55), [(1.0, 0.14), (0.6, 0.28)])
        c = pcam(1.75, 188, 84)
        img = fr.render(c, L, GRADE_CAVE, frame=self.fi(t))
        cv = self.hud(t)
        if t >= TL.T_28:
            q = back_out(clamp01((t - TL.T_28) / 0.25), 2.2)
            G.big_zh(cv, '一天 28 小时', 22, 78, 2, C('#ffe27a'), min(1, q))
        for i, (lab, col, tt) in enumerate((('睡 9', (127, 184, 255), 0.25), ('工作 10', (255, 176, 96), 0.5), ('自由 9', (143, 224, 160), 0.75))):
            if k > tt:
                x0, y0 = 22, 130 + i * 20
                cv.rect(x0, y0, 7, 14, col + (255,)); cv.rect(x0 + 7, y0, 70, 14, (14, 12, 26, 235))
                cv.text(x0 + 13, y0 + 1, lab, (255, 240, 220, 255), 'zh10')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 6. the student sleeps standing up; you stare at the ceiling
    def f_split(self, t):
        P = self.pA; fr = P.frame()
        sway = int(round(2 * math.sin(t * 2.2)))
        put_human(fr, STUDENT, SX_ + 12, SY_, face='closed', arms='rest', tilt=-5 + 2 * math.sin(t * 2.2))
        top = put_human(fr, KLEITMAN, KX, KY, face='surprised', arms='rest', look_dir=(2, -1) if (t % 2.4) < 1.2 else (-1, -2))
        nightcap(fr, KX, top[1] + 2, t)
        L = P.light(fr, key=KEY_CAMP)
        c = pcam(1.7, 128, 100)
        img = fr.render(c, L, GRADE_CAVE, frame=self.fi(t))
        cv = self.hud(t)
        ux, uy = c.w2ui(SX_ + 12, SY_ - 54, 4)
        ui.zzz(cv, ux, uy, t, TL.S_SPLIT, TL.S_NOD)
        kx_, ky_ = c.w2ui(KX, top[1], 4)
        A.draw_fx(cv, [('sweat', t - TL.S_SPLIT, 1)], kx_, ky_ + 10, t)
        cv.text(ux + 40, uy + 70, '学生：秒睡', (255, 220, 160, 255), 'zh12', outline=(20, 10, 0, 255))
        cv.text(kx_ - 50, ky_ - 30, '你：睡不着', (180, 210, 255, 255), 'zh12', outline=(0, 6, 20, 255))
        if int(t * 2) % 2 == 0: cv.text(396, 56, '03:00', (255, 80, 60, 255), 'p2p')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 7. nodding off at work -> bonk
    def f_nod(self, t):
        P = self.pA; fr = P.frame()
        pre = t < TL.T_BONK
        dy = int(round(4 * smooth((t - TL.S_NOD) / (TL.T_BONK - TL.S_NOD)) * (1 + 0.3 * math.sin(t * 6)))) if pre else 6
        top = put_human(fr, KLEITMAN, KX, KY, face='tired' if pre else 'closed', arms='rest', head_dy=dy, tilt=(-5 * smooth((t - TL.S_NOD) / 2.0) if pre else -9))
        nightcap(fr, KX, top[1] + 2 + dy, t)
        L = P.light(fr, key=KEY_CAMP)
        sh = 14 * max(0.0, 1 - (t - TL.T_BONK) / 0.3) if not pre else 0
        c = pcam(2.3, KX + 20, 108, sy=sh * math.sin(t * 90))
        img = fr.render(c, L, GRADE_CAVE, frame=self.fi(t))
        cv = self.hud(t)
        ux, uy = c.w2ui(KX, top[1] + dy, 4)
        if pre: A.draw_fx(cv, [('zz', 0, 1)], ux, uy, t)
        else:
            d = t - TL.T_BONK
            if d < 0.4: G.onomatopoeia(cv, '咚！', ux + 60, uy - 10, d, 3, C('#ffe27a'), life=0.4)
            ui.dizzy_stars(cv, ux, uy - 4, t, 3, 26, 6, 2.6)
        G._panel(cv, 380, 30, 88, 36, 1.0)
        cv.text(388, 33, '工作时间', (255, 230, 180, 255), 'zh10'); cv.text(388, 47, '10:00', (255, 200, 90, 255), 'p2p')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 8. the giant thermometer: day high, night low
    def f_thermo(self, t):
        P = self.pB; fr = P.frame()
        day = t < TL.T_NIGHT - 0.2
        target = 0.82 if day else 0.25
        prev = 0.5 if t < TL.T_DAY else 0.82
        u = smooth((t - (TL.T_DAY if day else TL.T_NIGHT - 0.2)) / 0.6)
        lev = lerp(prev if day else 0.82, target, u) + 0.02 * math.sin(t * 6)
        SY.thermometer(fr, 160, 26, 108, lev, t, w=14)
        SY.sun(fr, 84, 66, 14, t, 1.0 if day else 0.15)
        moon = fr.ell(236, 66, 13, 13, '#f2e6c0', 0.15 if day else 1.0); fr.fill(fr.M_ell(242, 61, 11, 11) & moon, '#06050a' if not day else '#0a0910')
        L = P.light(fr, key=KEY_WALL) + fr.band(160, 90, 80, 100, (1.0, 0.45, 0.4), [(1.0, 0.14), (0.6, 0.28)])
        img = fr.render(pcam(lerp(1.0, 1.08, (t - TL.S_THERMO) / 4), 160, 90), L, GRADE_CAVE, frame=self.fi(t))
        cv = self.hud(t)
        cv.text(80, 150, '白天 高', (255, 210, 120, 255 if day else 90), 'zh12', outline=(10, 6, 0, 255))
        cv.text(326, 150, '夜里 低', (170, 200, 255, 90 if day else 255), 'zh12', outline=(0, 6, 20, 255))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 9. the chalk graph: 28 h schedule vs 24 h temperature -> the gear clicks back
    def f_graph(self, t):
        P = self.pB; fr = P.frame()
        x0, x1, yb, yt = 56, 270, 120, 40
        fr.line(x0, yb, x1, yb, '#d8d4cc'); fr.line(x0, yt, x0, yb, '#d8d4cc')
        k = smooth((t - TL.S_GRAPH - 0.2) / 2.6)
        xmax = x0 + (x1 - x0) * k; sc = 1.35
        for d in range(0, 6):
            a = x0 + d * 28 * sc; b = a + 9 * sc
            if a < xmax: fr.rect(a, 104, min(b, xmax) - a, 10, '#6a82c8', 0.9); fr.rect(a, 104, min(b, xmax) - a, 1, '#b8c8f0')
        prev = None
        for x in range(int(x0), int(xmax)):
            h = (x - x0) / sc
            y = 76 - 20 * math.sin(2 * math.pi * (h - 6) / 24)
            if prev: fr.line(prev[0], prev[1], x, y, '#ff6a58', 0.9)
            prev = (x, y)
        gk = smooth((t - TL.T_GEAR_CLICK + 0.6) / 0.4)
        if gk > 0:
            fr.mul(fr.M_rect(0, 0, 320, 180), 1 - 0.6 * gk)
            ang = 28 if t < TL.T_GEAR_CLICK else lerp(28, 24, eo3((t - TL.T_GEAR_CLICK) / 0.15))
            SY.gear_clock(fr, 160, 76, 34 * back_out(gk, 1.6), t, 28, hand=ang, glow=1.0, spin=(0 if t < TL.T_GEAR_CLICK else -0.3))
        L = P.light(fr, key=KEY_WALL)
        sh = 10 * max(0.0, 1 - (t - TL.T_GEAR_CLICK) / 0.25) if t >= TL.T_GEAR_CLICK else 0
        img = fr.render(pcam(1.0, 160, 90, sx=sh * math.sin(t * 90)), L, GRADE_CAVE, frame=self.fi(t))
        cv = self.hud(t)
        if t < TL.T_GEAR_CLICK - 0.6:
            cv.text(50, 196, '■ 新规矩：28 小时作息', (168, 184, 232, 255), 'zh10', outline=(0, 0, 0, 255))
            cv.text(260, 196, '— 体温：24 小时起落', (255, 130, 110, 255), 'zh10', outline=(0, 0, 0, 255))
        if t >= TL.T_GEAR_CLICK:
            q = back_out(clamp01((t - TL.T_GEAR_CLICK) / 0.2), 2)
            G.pixel_word(cv, '24h', 240, 196, int(2 + 2 * q), C('#7fe0ff'), C('#0a2a3a'), C('#e0f8ff'))
            if t - TL.T_GEAR_CLICK < 0.4: G.onomatopoeia(cv, '咔哒', 336, 80, t - TL.T_GEAR_CLICK, 2, C('#ffffff'), life=0.4)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 10. day 32: two silhouettes walk out into daylight
    def silhouette(self, fr, look, x, y, s, phase):
        p = human.draw(look, face='normal', arms='rest', phase=phase)
        a = p.body.cv.a.copy(); a[..., :3] = np.clip(a[..., :3].astype(np.float32) * 0.16 + np.array([46, 30, 14]), 0, 255).astype(np.uint8)
        a = scale_nearest(a, s); h, w = a.shape[:2]
        fr.sprite(a, x - w / 2, y - h)

    def f_exit(self, t):
        P = self.pC; fr = P.frame()
        u = smooth((t - TL.S_EXIT) / 5.5)
        for i, off in enumerate((-9, 9)):
            x = 158 + off * (1 - 0.6 * u); y = lerp(168, 128, u); s = lerp(0.9, 0.42, u)
            self.silhouette(fr, KLEITMAN if i == 0 else STUDENT, x, y + (1 if int(t * 5 + i) % 2 else 0), s, int(t * 4 + i) % 2)
        L = P.light(fr) * P.flicker(fr, t, seed=2, amp=0.05)[..., None]
        img = fr.render(pcam(lerp(1.12, 1.0, u), 160, 92), L, GRADE_CAVE, frame=self.fi(t))
        cv = self.hud(t)
        a = clamp01((t - TL.S_EXIT - 0.2) / 0.3)
        G._panel(cv, 12, 40, 92, 22, a)
        cv.text(22, 44, '第 32 天', (255, 240, 200, int(255 * a)), 'zh12')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 11. triptych: why it matters to you
    def panel(self, kind, t):
        s = Stage(320, 180)
        if kind == 0:
            img, *_ = self.anchor.render(t, 0.45, z=2.0, cx=188, cy=100, face='tired', phone='smack', clock='0347', frame_i=self.fi(t))
            return img
        if kind == 1:
            s.img[..., :3] = (10, 10, 14); s.rect(0, 120, 320, 60, '#1a1a22')
            for i in range(6): s.rect(40 + i * 44, 128, 30, 8, '#4a4a58'); s.rect(40 + i * 44, 126, 30, 2, '#8a8a98')
            s.rect(0, 136, 320, 4, '#2a2a34')
            s.line(160, 0, 160, 40, '#3a3a44'); s.poly([(146, 40), (174, 40), (168, 48), (152, 48)], '#4a4a58', None)
            s.rect(152, 48, 16, 2, '#fff2c0', 1.0)
            put_human(s, SUBJECT, 160, 132, face='tired', arms='hold')
            L = s.light_base((0.4, 0.42, 0.6), 0.7) + s.cone((160, 48), (100, 182), (220, 182), (1.0, 0.9, 0.6), 0.5)
            return s.render(pcam(1.6, 160, 100), L, GRADE_NIGHT, frame=self.fi(t), air=s.cone((160, 48), (110, 182), (210, 182), (1.0, 0.9, 0.6), 0.06))
        s.img[..., :3] = (30, 30, 40)
        win = s.M_ell(150, 76, 34, 46); s.fill(win, '#0a0e2a', 0.6)
        for i in range(10): s.px(124 + i * 6, 46 + (i * 13) % 44, '#fff4d0', 1.0)
        s.fill(win & (s.yy > 104), '#1a1430', 0.3)
        s.fill(s.ring(win), '#9a9aaa'); s.fill(s.ring(s.M_ell(150, 76, 35, 47)), '#5a5a6a')
        s.rect(0, 140, 320, 40, '#2a2a36')
        put_human(s, SUBJECT, 168, 150, face='closed', arms='rest', tilt=-10)
        L = s.light_base((0.55, 0.55, 0.8), 0.95) + s.band(160, 90, 60, 50, (0.6, 0.7, 1.0), [(1.0, 0.2), (0.5, 0.35)])
        return s.render(pcam(1.5, 164, 100), L, GRADE_NIGHT, frame=self.fi(t))

    def f_trip(self, t):
        img = np.zeros((1080, 1920, 3), np.float32)
        for i, tt in enumerate((TL.T_P1, TL.T_P2, TL.T_P3)):
            k = eo3((t - tt + 0.15) / 0.3)
            if k <= 0: continue
            p = self.panel(i, t)
            x0 = i * 640; sl = p[:, 640:1280]
            dy = int(round((1 - k) * 1080))
            if dy < 1080: img[dy:, x0:x0 + 640] = sl[:1080 - dy]
        img[:, 636:644] = (0.9, 0.7, 0.3); img[:, 1276:1284] = (0.9, 0.7, 0.3)
        cv = self.hud(t, loc=False)
        labels = ('熬夜', '倒班', '倒时差')
        jam = t >= TL.T_JAM
        for i, tt in enumerate((TL.T_P1, TL.T_P2, TL.T_P3)):
            if t < tt: continue
            cx = 80 + i * 160
            G._panel(cv, cx - 34, 10, 68, 22, 1.0)
            cv.text(cx - G.text_width(labels[i], 'zh12') // 2, 14, labels[i], (255, 230, 170, 255), 'zh12')
            r = 13; gx, gy = cx + 52, 62
            spin = t * 3 if not jam else 0
            jit = (1.5 * math.sin(t * 60) if not jam else 2.5 * math.sin(t * 80))
            for k in range(10):
                a = k / 10 * 6.283 + spin
                cv.rect(int(gx + jit + (r + 2) * math.cos(a)) - 1, int(gy + (r + 2) * math.sin(a)) - 1, 3, 3, (90, 150, 190, 255))
            cv.ellipse(gx + jit, gy, r, r, (60, 110, 150, 255)); cv.ellipse(gx + jit, gy, r - 4, r - 4, (14, 32, 52, 255))
            if not jam and int(t * 20) % 3 == 0:
                for q in range(3): cv.px(int(gx + r + 3 + q * 2), int(gy - 4 + q * 3), (255, 220, 120, 255))
            if jam:
                cv.line(int(gx - 9), int(gy - 9), int(gx + 9), int(gy + 9), (255, 60, 50, 255)); cv.line(int(gx + 9), int(gy - 9), int(gx - 9), int(gy + 9), (255, 60, 50, 255))
                cv.line(int(gx - 9), int(gy - 8), int(gx + 9), int(gy + 10), (255, 60, 50, 255)); cv.line(int(gx + 9), int(gy - 8), int(gx - 9), int(gy + 10), (255, 60, 50, 255))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 12. back at the 03:56 save point: +20%
    def f_anchor(self, t):
        u = smooth((t - TL.S_ANCHOR) / 1.0)
        gy = lerp(58, 90, u)
        color_k = 0.05 + 0.25 * smooth((t - TL.T_REVIVE) / 0.8)
        img, c, p, head = self.anchor.render(t, color_k, z=lerp(1.5, 1.7, smooth((t - TL.S_ANCHOR) / 3.0)), cx=184, cy=96, ghost_xy=(150, gy - 6),
                                             ghost_act=self.act_back, frame_i=self.fi(t))
        img = np.clip((np.clip(img, 0, 1) ** 0.8) * 1.35 + 0.02, 0, 1)
        cv = self.hud(t, loc=False, pips=True)
        if p is not None: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if TL.T_REVIVE - 0.1 <= t < TL.T_REVIVE + 1.4:
            q = t - TL.T_REVIVE + 0.1
            k = back_out(clamp01(q / 0.3), 1.6) * (1 - clamp01((q - 1.1) / 0.3))
            if k > 0.05: G.big_zh(cv, '复活 +20%', 240 - int(G.text_width('复活 +20%', 'zh12')), int(196 - 6 * k), 2, C('#7fe0ff'), min(1, k))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 13. hub: the first door is cleared, the next one glows
    def f_hub(self, t):
        st = ['cleared' if t >= TL.T_CLEAR else 'active', 'active' if t >= TL.T_NEXT else 'locked', 'locked', 'locked', 'locked']
        op = [0.55 * smooth((t - TL.T_CLEAR) / 0.5), eo3((t - TL.T_GO - 0.5) / 0.6), 0, 0, 0]
        fr = self.hub.frame(t, st, (1,) * 5, op)
        d1 = self.hub.D[1]
        k = smooth((t - TL.T_GO) / 1.0)
        gx = lerp(160, d1['x'], k); gy = lerp(140, d1['yb'] - 18, k)
        p, head = self.ghost(fr, t, self.act_hub, gx, gy, scale=lerp(1, 0.8, k))
        L = self.hub.light(fr, st, (1,) * 5, op) + fr.band(gx, gy, 30, 22, (0.55, 0.75, 1.0), [(1.0, 0.15), (0.5, 0.3)])
        z = logz(1.0, 2.4, smooth((t - TL.T_GO - 0.1) / 1.0)); cx = lerp(160, d1['x'], smooth((t - TL.T_GO) / 1.1)); cy = lerp(98, d1['yb'] - 26, smooth((t - TL.T_GO) / 1.1))
        c = pcam(z, cx, cy)
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t), air=self.hub.air(fr, st, (1,) * 5, op))
        img = img + (1 - img) * smooth((t - TL.END + 0.4) / 0.4)
        cv = self.hud(t, loc=False, pips=True)
        A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if TL.T_BTN <= t < TL.T_GO + 0.1:
            G.item_card(cv, t, TL.T_BTN, 176, 50, self.gear_icon, '体内时钟', '没有太阳也照样走', price='已获得', price_t=TL.T_BTN + 0.5,
                        rarity=C('#7fd0ff'), w=130, life=TL.T_GO + 0.1 - TL.T_BTN)
        return self.compose(img, cv)

    def frame(self, t):
        img = self.ed.frame(min(t, TL.END - 1e-3))
        return ui_over(img, subs_layer(t, TL.L, TL.HL).a, scale=5)

def make(**kw): return Level1(**kw)
