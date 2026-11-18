"""第 1 关 · 1938 没有太阳的洞穴：Level1().frame(t)。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s1_cave'))
import numpy as np
import timeline as TL
from common import (subs_layer, ramp, lerp, smooth, FPS, put_human, nightcap, lying_head, put_ghost, ghost_dive, hud_layer)
from pixelkit import ui, gameui as G
from pixelkit.core import C
from pixelkit.edit import Edit
from pixelkit.scene import ui_over
from pixelkit.pixstage import Stage, cam as pcam, GRADE_NIGHT
from pixelkit.sets.cave320 import Cave320, GRADE_CAVE
from pixelkit.sets.hub_doors import HubDoors
from pixelkit.sets.bedroom320 import Bedroom320
from pixelkit.sets import symbols as SY
from pixelkit.characters import ghost
from pixelkit.characters.cast_sleep import KLEITMAN, STUDENT, SUBJECT
from pixelkit.anim import back_out, clamp01

def eo3(u): u = clamp01(u); return 1 - (1 - u) ** 3
def logz(a, b, k): return math.exp(math.log(a) + (math.log(b) - math.log(a)) * k)

class Level1:
    def __init__(self):
        self.cave = Cave320(); self.hub = HubDoors(); self.bed = Bedroom320()
        self.blank = Stage(320, 180)
        e = self.ed = Edit()
        e.add('desc', TL.S_DESC, self.f_desc)
        e.add('camp', TL.S_CAMP, self.f_camp, 'cut')
        e.add('vs', TL.S_VS, self.f_vs, 'flash', 0.3)
        e.add('dark', TL.S_DARK, self.f_vs, 'cut')
        e.add('chalk', TL.S_CHALK, self.f_chalk, 'cut')
        e.add('split', TL.S_SPLIT, self.f_split, 'cut')
        e.add('nod', TL.S_NOD, self.f_nod, 'cut')
        e.add('thermo', TL.S_THERMO, self.f_thermo, 'flash', 0.3)
        e.add('graph', TL.S_GRAPH, self.f_graph, 'cut')
        e.add('exit', TL.S_EXIT, self.f_exit, 'dissolve', 0.5)
        e.add('trip', TL.S_TRIP, self.f_trip, 'cut')
        e.add('hub', TL.S_HUB, self.f_hub, 'flash', 0.36)
        e.end(TL.END)

    def fi(self, t): return int(round(t * FPS))

    # HUD: revive % jumps to 20 at the achievement
    def hud(self, t, year=True):
        pct = 20 * eo3((t - TL.T_ACH - 1.2) / 0.6)
        fl = max(0.0, 1 - abs(t - TL.T_ACH - 1.5) / 0.3) if t > TL.T_ACH + 1.2 else 0.0
        stage = 1 if t > TL.T_ACH + 1.5 else 0
        yk = clamp01((t - TL.T_TAG) / 0.35) * (1 - clamp01((t - TL.S_HUB) / 0.2))
        return hud_layer(t, pct, stage, fl, 1.0, '1938' if year else None, '美国 · 猛犸洞穴 · 地下 40 米', yk)

    def compose(self, img, cv): return ui_over(img, cv.a, scale=4)

    # ------------------------------------------------------------------ 1. descent down the ladder
    def f_desc(self, t):
        fr = self.cave.frame(t)
        fr.rect(94, 0, 10, 3, '#fff6d8', 1.0); fr.rect(96, 3, 6, 2, '#ffe9b0', 0.8)       # daylight hole far above
        k = smooth((t - 0.25) / 3.3)
        z = logz(2.8, 1.0, k); cx = lerp(99, 160, k); cy = lerp if False else lerp(30, 92, k)
        L = self.cave.light(fr, t=t)
        L = L + fr.band(99, 0, 30, 40, (1.0, 0.95, 0.8), [(1.0, 0.25), (0.5, 0.5)])
        img = fr.render(pcam(z, cx, cy), L, GRADE_CAVE, frame=self.fi(t), air=self.cave.air(fr, t=t))
        img = img + (1 - img) * (1 - smooth(t / 0.55))
        cv = self.hud(t)
        # depth meter
        d = int(round(40 * smooth((t - 0.4) / 3.0)))
        a = clamp01((t - 0.3) / 0.3) * (1 - clamp01((t - 3.6) / 0.3))
        if a > 0:
            G._panel(cv, 430, 70, 40, 130, a)
            cv.rect(447, 80, 6, 100, (12, 10, 20, int(255 * a)))
            cv.rect(448, 81, 4, int(98 * d / 40), (255, 200, 90, int(255 * a)))
            s = f'-{d}m'; cv.text(450 - G.text_width(s, 'silkb') // 2, 186, s, (255, 220, 120, int(255 * a)), 'silkb')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 2. camp: ghost arrives, possesses Kleitman
    def f_camp(self, t):
        fr = self.cave.frame(t)
        kx, ky = self.cave.A['stand_r']; sx_, sy_ = self.cave.A['stand_l']
        hit = t >= TL.T_HIT
        white = max(0.0, 1 - (t - TL.T_HIT) / 0.12) if hit else 0.0
        kface = 'focus' if not hit else ('surprised' if t < TL.T_HIT + 0.9 else 'normal')
        put_human(fr, STUDENT, sx_, sy_, face='normal', arms='hold', look_dir=(1, 0) if t < TL.T_HIT else (2, 0))
        top = put_human(fr, KLEITMAN, kx, sy_ + 2, face=kface, arms='type' if not hit else 'rest', phase=int(t * 8) % 2, white=white)
        if hit and t > TL.T_HIT + 0.15: nightcap(fr, kx, top[1] + 2, t)
        # ghost
        gx = lerp(-20, 128, eo3((t - TL.T_GHOST_IN0) / (TL.T_GHOST_IN1 - TL.T_GHOST_IN0))); gy = 70 + 3 * math.sin(t * 2.4)
        look = (2, 0) if int(t * 0.9) % 2 == 0 else (-2, 0)
        if t < TL.T_POSSESS:
            if t > TL.T_GHOST_IN0: put_ghost(fr, t, gx, gy, face='wow' if t < TL.T_GHOST_IN1 else 'normal', look=look)
        else:
            ghost_dive(fr, t, TL.T_POSSESS, (128, 70), (kx, top[1] + 14), 0.45, look=(2, 0))
        L = self.cave.light(fr, t=t)
        if TL.T_GHOST_IN0 < t < TL.T_HIT: L = L + fr.band(gx, gy, 26, 20, (0.6, 0.8, 1.0), [(1.0, 0.12), (0.5, 0.25)])
        if hit: L = L + fr.band(kx, top[1] + 14, 30, 30, (0.7, 0.9, 1.0), [(1.0, 0.5 * white), (0.5, white)])
        k = smooth((t - TL.T_HIT - 0.1) / 1.3)
        z = logz(1.08, 2.1, k); cx = lerp(160, kx, k); cy = lerp(98, top[1] + 26, k)
        img = fr.render(pcam(z, cx, cy, sx=(14 * white * math.sin(t * 90))), L, GRADE_CAVE, frame=self.fi(t), air=self.cave.air(fr, t=t))
        cv = self.hud(t)
        c = pcam(z, cx, cy)
        if hit and t < TL.T_HIT + 0.5:
            ux, uy = c.w2ui(kx, top[1] + 14, 4); d = t - TL.T_HIT
            G.burst_lines(cv, ux, uy, 20 + 160 * d, 34 + 200 * d, 16, C('#bfe8ff'), 1 - d / 0.5)
        G.char_card(cv, t, TL.T_CARD, '克莱特曼', 'LV.43', '拿自己做实验', '1938 · 芝加哥大学 · 生理学家', x=12, y=150, life=4.6)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 3-4. VS: the sun or a clock inside? then the boulder
    def stage_base(self, fr, y=126):
        fr.img[..., :3] = (6, 5, 10); fr.E[:] = 0
        SY.stage_floor(fr, y)

    def f_vs(self, t):
        fr = Stage(320, 180); self.stage_base(fr)
        dark = t >= TL.S_DARK
        ks = back_out(clamp01((t - TL.T_SUN) / 0.35), 1.6)
        kg = back_out(clamp01((t - TL.T_GEAR) / 0.35), 1.6)
        sun_k = 1.0 - (smooth((t - TL.T_ROLL1 + 0.15) / 0.3) if dark else 0)
        if ks > 0: SY.sun(fr, 86, 66, 24 * ks, t, max(0.05, sun_k))
        if kg > 0: SY.gear_clock(fr, 234, 66, 24 * kg, t, 24, hand=(t * 2) % 24, glow=0.9, spin=t * 0.4)
        if dark:
            u = smooth((t - TL.T_ROLL0) / (TL.T_ROLL1 - TL.T_ROLL0))
            SY.boulder(fr, lerp(-40, 86, u), lerp(76, 70, u), 34, -u * 6)
        if t >= TL.T_VS and not dark:
            d = t - TL.T_VS; sc = 4 if d > 0.08 else 7
            SY.vs_mark(fr, 160, 64, sc)
        # Kleitman (possessed) thinking at the front
        top = put_human(fr, KLEITMAN, 160, 168, face='normal' if not dark else 'surprised', arms='chin', look_dir=((-2, 0) if (t % 2) < 1 else (2, 0)))
        nightcap(fr, 160, top[1] + 2, t)
        L = fr.light_base((0.55, 0.55, 0.8), 0.9)
        if ks > 0: L = L + fr.band(86, 66, 120, 90, (1.0, 0.75, 0.4), [(1.0, 0.25 * sun_k), (0.5, 0.45 * sun_k)])
        if kg > 0: L = L + fr.band(234, 66, 110, 90, (0.45, 0.8, 1.0), [(1.0, 0.2), (0.5, 0.4)])
        z = 1.0 if not dark else logz(1.0, 1.9, smooth((t - TL.T_ROLL1) / 1.2))
        cx = 160 if not dark else lerp(160, 234, smooth((t - TL.T_ROLL1) / 1.2))
        sh = 0
        if TL.T_VS <= t < TL.T_VS + 0.25 and not dark: sh = 16 * (1 - (t - TL.T_VS) / 0.25)
        if dark and TL.T_ROLL1 <= t < TL.T_ROLL1 + 0.3: sh = 20 * (1 - (t - TL.T_ROLL1) / 0.3)
        img = fr.render(pcam(z, cx, 80, sx=sh * math.sin(t * 95)), L, GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t)
        if ks > 0.5 and not dark: cv.text(118 - G.text_width('太阳？', 'zh12') // 2, 154, '太阳？', (255, 214, 120, 255), 'zh12', outline=(20, 10, 0, 255))
        if kg > 0.5 and not dark: cv.text(352 - G.text_width('体内的钟？', 'zh12') // 2, 154, '体内的钟？', (160, 230, 255, 255), 'zh12', outline=(0, 10, 20, 255))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 5. chalk 28-hour clock on the wall
    def f_chalk(self, t):
        fr = self.cave.frame(t)
        cx_, cy_, cw, ch = self.cave.A['chalk']
        ccx, ccy = cx_ + cw / 2 + 1, cy_ + ch / 2
        k = smooth((t - TL.T_CHALK0) / (TL.T_CHALK1 - TL.T_CHALK0))
        SY.chalk_clock(fr, ccx, ccy, 24, 28, k, segs=[(0, 9, '#7fb8ff'), (9, 19, '#ffb060'), (19, 28, '#8fe0a0')])
        # Kleitman at the right edge, arm up drawing
        top = put_human(fr, KLEITMAN, 304, 150, face='focus', arms='up', look_dir=(-2, 0), phase=int(t * 6) % 2)
        nightcap(fr, 304, top[1] + 2, t)
        L = self.cave.light(fr, t=t) + fr.band(ccx, ccy, 50, 46, (1.0, 0.8, 0.55), [(1.0, 0.15), (0.6, 0.3)])
        z = 2.35; c = pcam(z, ccx + 8, ccy + 6)
        img = fr.render(c, L, GRADE_CAVE, frame=self.fi(t), air=self.cave.air(fr, t=t))
        cv = self.hud(t)
        if t >= TL.T_28:
            q = back_out(clamp01((t - TL.T_28) / 0.25), 2.2)
            G.pixel_word(cv, '28h', 92, 70, int(round(3 + 2 * q)), C('#ffe27a'), C('#5a3a0a'), C('#fff6c0'), alpha=min(1, q))
            G.big_text(cv, '一天', 92, 112, 2, C('#ffffff'), alpha=min(1, q))
        for i, (lab, col, tt) in enumerate((('睡 9', (127, 184, 255), 0.25), ('工作 10', (255, 176, 96), 0.5), ('自由 9', (143, 224, 160), 0.75))):
            if k > tt:
                cv.text(30, 150 + i * 16, lab, col + (255,), 'zh12', outline=(10, 6, 4, 255))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 6. split: student sleeps / you stare
    def f_split(self, t):
        A = Stage(320, 180); A.img[..., :3] = (10, 7, 8)
        A.rect(0, 120, 320, 60, '#2a1a14')
        lying_head(A, STUDENT, 160, 92, face='closed', blanket_col=('#5a5a6e', '#6a6a80'))
        LA = A.light_base((0.75, 0.68, 0.85), 1.05) + A.band(160, 96, 120, 70, (1.0, 0.72, 0.42), [(1.0, 0.3), (0.5, 0.55)])
        B = Stage(320, 180); B.img[..., :3] = (4, 4, 8)
        B.rect(0, 120, 320, 60, '#120c0c')
        lying_head(B, KLEITMAN, 160, 92, face='surprised', blanket_col=('#3a3a48', '#44445a'), cap_t=t)
        LB = B.light_base((0.45, 0.50, 0.85), 0.85) + B.band(160, 88, 60, 40, (0.6, 0.75, 1.0), [(1.0, 0.25), (0.5, 0.45)])
        ia = A.render(pcam(3.3, 160, 93), LA, GRADE_CAVE, frame=self.fi(t))
        ib = B.render(pcam(3.3, 160, 93), LB, GRADE_NIGHT, frame=self.fi(t))
        ia = np.roll(ia, -480, 1); ib = np.roll(ib, 480, 1)
        img = ia.copy(); img[:, 960:] = ib[:, 960:]
        img[:, 954:966] = np.array([0.9, 0.7, 0.3])
        cv = self.hud(t)
        ui.zzz(cv, 150, 70, t, TL.S_SPLIT, TL.S_NOD)
        cv.text(60, 40, '学生：秒睡', (255, 220, 160, 255), 'zh12', outline=(20, 10, 0, 255))
        cv.text(300, 40, '你：睡不着', (180, 210, 255, 255), 'zh12', outline=(0, 6, 20, 255))
        if int(t * 2) % 2 == 0: cv.text(420, 70, '03:00', (255, 80, 60, 255), 'silkb')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 7. nodding off at the table -> bonk
    def f_nod(self, t):
        fr = self.cave.frame(t)
        kx = 150; ky = 152
        pre = t < TL.T_BONK
        dy = int(round(4 * smooth((t - TL.S_NOD) / (TL.T_BONK - TL.S_NOD)) * (1 + 0.3 * math.sin(t * 6)))) if pre else 6
        top = put_human(fr, KLEITMAN, kx, ky, face='tired' if pre else 'closed', arms='type' if pre else 'rest', head_dy=dy, tilt=(0 if pre else 8))
        nightcap(fr, kx, top[1] + 2 + dy, t)
        L = self.cave.light(fr, t=t)
        sh = 18 * max(0.0, 1 - (t - TL.T_BONK) / 0.3) if not pre else 0
        img = fr.render(pcam(2.4, kx + 8, 118, sy=sh * math.sin(t * 90)), L, GRADE_CAVE, frame=self.fi(t), air=self.cave.air(fr, t=t))
        cv = self.hud(t)
        c = pcam(2.4, kx + 8, 118)
        ux, uy = c.w2ui(kx, top[1] + dy, 4)
        if not pre:
            d = t - TL.T_BONK
            if d < 0.35: G.big_text(cv, '咚！', ux + 60, uy - 10 - 20 * d, 3, C('#ffe27a'), alpha=1 - d / 0.35)
            ui.dizzy_stars(cv, ux, uy - 4, t, 3, 26, 6, 2.6)
        if int(t * 2) % 2 == 0: cv.text(400, 60, '10:00', (255, 200, 90, 255), 'silkb')
        cv.text(380, 46, '工作时间', (255, 230, 180, 255), 'zh10', outline=(10, 6, 0, 255))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 8. the giant thermometer
    def f_thermo(self, t):
        fr = Stage(320, 180); self.stage_base(fr, 140)
        day = t < TL.T_NIGHT - 0.2
        target = 0.82 if day else 0.25
        # mercury follows like a pendulum
        prev = 0.5 if t < TL.T_DAY else 0.82
        u = smooth((t - (TL.T_DAY if day else TL.T_NIGHT - 0.2)) / 0.6)
        lev = lerp(prev if day else 0.82, target, u)
        lev += 0.02 * math.sin(t * 6)
        SY.thermometer(fr, 160, 22, 108, lev, t, w=14)
        SY.sun(fr, 74, 62, 14, t, 1.0 if day else 0.15)
        moon = fr.ell(246, 62, 13, 13, '#f2e6c0', 0.15 if day else 1.0); fr.fill(fr.M_ell(252, 57, 11, 11) & moon, '#06050a' if not day else '#0a0910')
        L = fr.light_base((0.6, 0.6, 0.85), 0.95) + fr.band(160, 90, 90, 110, (1.0, 0.45, 0.4), [(1.0, 0.15), (0.6, 0.3)])
        img = fr.render(pcam(lerp(1.0, 1.08, (t - TL.S_THERMO) / 4)), L, GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t)
        cv.text(80, 150, '白天 高', (255, 210, 120, 255 if day else 90), 'zh12', outline=(10, 6, 0, 255))
        cv.text(326, 150, '夜里 低', (170, 200, 255, 90 if day else 255), 'zh12', outline=(0, 6, 20, 255))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 9. the graph: 28 h schedule vs 24 h temperature -> gear clicks back
    def f_graph(self, t):
        fr = Stage(320, 180); fr.img[..., :3] = (22, 17, 16); fr.E[:] = 0
        # slate board
        fr.rect(20, 20, 280, 120, '#2a2420'); fr.outline(fr.M_rect(20, 20, 280, 120), '#7a5a3a')
        fr.line(30, 118, 290, 118, '#d8d4cc'); fr.line(30, 30, 30, 118, '#d8d4cc')
        k = smooth((t - TL.S_GRAPH - 0.2) / 2.6)
        xmax = 30 + 260 * k
        # schedule: sleep blocks every 28 'hours' (white)
        for d in range(0, 6):
            x0 = 30 + d * 28 * 1.55 + 0; x1 = x0 + 9 * 1.55
            if x0 < xmax: fr.rect(x0, 98, min(x1, xmax) - x0, 12, '#5a6a9a'); fr.rect(x0, 98, min(x1, xmax) - x0, 1, '#a8b8e8')
        # body temperature: 24 h sine (red)
        prev = None
        for x in range(30, int(xmax)):
            h = (x - 30) / 1.55
            y = 66 - 22 * math.sin(2 * math.pi * (h - 6) / 24)
            if prev: fr.line(prev[0], prev[1], x, y, '#ff5a4a', 0.6)
            prev = (x, y)
        gk = smooth((t - TL.T_GEAR_CLICK + 0.6) / 0.4)
        if gk > 0:
            fr.rect(0, 0, 320, 180, '#000000') if False else None
            fr.mul(fr.M_rect(0, 0, 320, 180), 1 - 0.6 * gk)
            ang = 28 if t < TL.T_GEAR_CLICK else lerp(28, 24, eo3((t - TL.T_GEAR_CLICK) / 0.15))
            SY.gear_clock(fr, 160, 70, 34 * back_out(gk, 1.6), t, 28, hand=ang, glow=1.0, spin=(0 if t < TL.T_GEAR_CLICK else -0.3))
        L = fr.light_base((0.85, 0.82, 0.9), 1.0)
        sh = 12 * max(0.0, 1 - (t - TL.T_GEAR_CLICK) / 0.25) if t >= TL.T_GEAR_CLICK else 0
        img = fr.render(pcam(1.0, 160, 90, sx=sh * math.sin(t * 90)), L, GRADE_CAVE, frame=self.fi(t))
        cv = self.hud(t)
        if t < TL.T_GEAR_CLICK - 0.6: cv.text(50, 214, '■ 新规矩：28 小时作息', (168, 184, 232, 255), 'zh10', outline=(0, 0, 0, 255))
        if t < TL.T_GEAR_CLICK - 0.6: cv.text(250, 214, '— 体温：24 小时起落', (255, 110, 90, 255), 'zh10', outline=(0, 0, 0, 255))
        if t >= TL.T_GEAR_CLICK:
            q = back_out(clamp01((t - TL.T_GEAR_CLICK) / 0.2), 2)
            G.pixel_word(cv, '24h', 240, 196, int(2 + 2 * q), C('#7fe0ff'), C('#0a2a3a'), C('#e0f8ff'))
            if t - TL.T_GEAR_CLICK < 0.4: G.big_text(cv, '咔哒', 330, 70, 2, C('#ffffff'), alpha=1 - (t - TL.T_GEAR_CLICK) / 0.4)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 10. out of the cave into daylight
    def f_exit(self, t):
        fr = Stage(320, 180); fr.img[..., :3] = (14, 9, 8); fr.E[:] = 0
        mouth = fr.M_poly([(110, 150), (118, 70), (140, 40), (178, 34), (206, 52), (216, 96), (222, 150)])
        fr.vgrad if False else None
        fr.fill(mouth, '#fff4dc', 1.0); fr.fill(mouth & (fr.yy > 110), '#d8f0c8', 1.0)
        fr.fill(mouth & (fr.yy > 128), '#a8d890', 1.0)
        fr.fill(fr.ring(mouth), '#3a2a20')
        rock = ~mouth
        cave = Cave320()._rock
        cave(fr, rock & (fr.yy < 150), ['#2a1c18', '#30201a', '#261814'], 7, 12)
        fl = fr.M_poly([(0, 180), (0, 150), (320, 150), (320, 180)]); fr.fill(fl, '#2a1e16')
        # two bearded silhouettes walking out (shrink toward the light)
        u = smooth((t - TL.S_EXIT) / 5.5)
        for i, off in enumerate((-12, 12)):
            x = 166 + off * (1 - 0.5 * u); y = lerp(176, 152, u); sc = lerp(1.4, 0.7, u)
            hh = 44 * sc
            m = fr.M_ell(x, y - hh, 6 * sc, 6 * sc) | fr.M_rect(x - 6 * sc, y - hh + 4 * sc, 12 * sc, hh - 4 * sc)
            m |= fr.M_ell(x, y - hh + 6 * sc, 5 * sc, 5 * sc)
            fr.fill(m, '#120c0a')
        L = fr.light_base((0.75, 0.7, 0.75), 0.9)
        L = L + fr.cone((166, 70), (60, 182), (290, 182), (1.0, 0.92, 0.7), 0.45)
        air = fr.cone((166, 60), (40, 182), (300, 182), (1.0, 0.9, 0.65), 0.10) * (fr.yy[..., None] > 60)
        img = fr.render(pcam(lerp(1.15, 1.0, u), 166, 96), L, GRADE_CAVE, frame=self.fi(t), air=air)
        cv = self.hud(t)
        G.danmaku(cv, t, TL.S_EXIT + 0.8, '32 天后……', 40, 0) if False else None
        cv.text(196, 30, '第 32 天', (255, 240, 200, int(255 * clamp01((t - TL.S_EXIT - 0.2) / 0.3))), 'zh12', outline=(20, 10, 0, 255))
        ui.achievement(cv, t, TL.T_ACH, '体内时钟', '没有太阳，它也照样走', life=3.0, y=44)
        # gear item flies to the HUD
        u2 = clamp01((t - TL.T_ACH - 0.9) / 0.5)
        if 0 < u2 < 1:
            x = lerp(240, 420, u2); y = lerp(210, 20, u2) - 40 * math.sin(math.pi * u2)
            cv.ellipse(x, y, 6, 6, (127, 216, 255, 255)); cv.ellipse(x, y, 3, 3, (14, 32, 52, 255))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 11. triptych: why it matters to you
    def panel(self, kind, t):
        s = Stage(320, 180)
        if kind == 0:
            fr = self.bed.frame(t, face='tired', phone='hold')
            L = self.bed.light(fr, phone_k=1.0, room_k=0.55)
            return fr.render(pcam(2.6, 196, 100), L, GRADE_NIGHT, frame=self.fi(t))
        if kind == 1:
            s.img[..., :3] = (10, 10, 14); s.rect(0, 120, 320, 60, '#1a1a22')
            for i in range(6): s.rect(40 + i * 44, 128, 30, 8, '#4a4a58'); s.rect(40 + i * 44, 126, 30, 2, '#8a8a98')
            s.rect(0, 136, 320, 4, '#2a2a34')
            s.line(160, 0, 160, 40, '#3a3a44'); s.poly([(146, 40), (174, 40), (168, 48), (152, 48)], '#4a4a58', None)
            s.rect(152, 48, 16, 2, '#fff2c0', 1.0)
            top = put_human(s, SUBJECT, 160, 132, face='tired', arms='hold')
            L = s.light_base((0.4, 0.42, 0.6), 0.7) + s.cone((160, 48), (100, 182), (220, 182), (1.0, 0.9, 0.6), 0.5)
            return s.render(pcam(1.6, 160, 100), L, GRADE_NIGHT, frame=self.fi(t), air=s.cone((160, 48), (110, 182), (210, 182), (1.0, 0.9, 0.6), 0.06))
        s.img[..., :3] = (30, 30, 40)
        win = s.M_ell(150, 76, 34, 46); s.fill(win, '#0a0e2a', 0.6)
        for i in range(10): s.px(124 + i * 6, 46 + (i * 13) % 44, '#fff4d0', 1.0)
        s.fill(win & (s.yy > 104), '#1a1430', 0.3)
        s.fill(s.ring(win), '#9a9aaa'); s.fill(s.ring(s.M_ell(150, 76, 35, 47)), '#5a5a6a')
        s.rect(0, 140, 320, 40, '#2a2a36')
        top = put_human(s, SUBJECT, 168, 150, face='closed', arms='rest', tilt=-10)
        L = s.light_base((0.55, 0.55, 0.8), 0.95) + s.band(160, 90, 60, 50, (0.6, 0.7, 1.0), [(1.0, 0.2), (0.5, 0.35)])
        return s.render(pcam(1.5, 164, 100), L, GRADE_NIGHT, frame=self.fi(t))

    def f_trip(self, t):
        img = np.zeros((1080, 1920, 3), np.float32)
        for i, tt in enumerate((TL.T_P1, TL.T_P2, TL.T_P3)):
            k = eo3((t - tt + 0.15) / 0.3)
            if k <= 0: continue
            p = self.panel(i, t)
            x0 = i * 640; sl = p[:, 640:1280] if i != 0 else p[:, 640:1280]
            dy = int(round((1 - k) * 1080))
            if dy < 1080: img[dy:, x0:x0 + 640] = sl[:1080 - dy]
        img[:, 636:644] = (0.9, 0.7, 0.3); img[:, 1276:1284] = (0.9, 0.7, 0.3)
        cv = self.hud(t)
        labels = ('熬夜', '倒班', '倒时差')
        jam = t >= TL.T_JAM
        for i, tt in enumerate((TL.T_P1, TL.T_P2, TL.T_P3)):
            if t < tt: continue
            cx = 80 + i * 160
            cv.text(cx - G.text_width(labels[i], 'zh12') // 2, 16, labels[i], (255, 230, 170, 255), 'zh12', outline=(20, 10, 0, 255))
            # grinding gear badge
            r = 13; gx, gy = cx + 52, 52
            spin = t * 3 if not jam else 0
            jit = (1.5 * math.sin(t * 60) if not jam else 2.5 * math.sin(t * 80))
            for k in range(10):
                a = k / 10 * 6.283 + spin
                cv.rect(int(gx + jit + (r + 2) * math.cos(a)) - 1, int(gy + (r + 2) * math.sin(a)) - 1, 3, 3, (90, 150, 190, 255))
            cv.ellipse(gx + jit, gy, r, r, (60, 110, 150, 255)); cv.ellipse(gx + jit, gy, r - 4, r - 4, (14, 32, 52, 255))
            if not jam and int(t * 20) % 3 == 0:
                for q in range(3): cv.px(int(gx + r + 3 + q * 2), int(gy - 4 + q * 3), (255, 220, 120, 255))
            if jam:
                d = t - TL.T_JAM
                cv.line(int(gx - 9), int(gy - 9), int(gx + 9), int(gy + 9), (255, 60, 50, 255)); cv.line(int(gx + 9), int(gy - 9), int(gx - 9), int(gy + 9), (255, 60, 50, 255))
                cv.line(int(gx - 9), int(gy - 8), int(gx + 9), int(gy + 10), (255, 60, 50, 255)); cv.line(int(gx + 9), int(gy - 8), int(gx - 9), int(gy + 10), (255, 60, 50, 255))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 12. back to the hub: cleared -> next door
    def f_hub(self, t):
        st = ['cleared' if t >= TL.T_CLEAR else 'active', 'active' if t >= TL.T_NEXT else 'locked', 'locked', 'locked', 'locked']
        op = [0.55 * smooth((t - TL.T_CLEAR) / 0.5), eo3((t - TL.T_GO - 0.7) / 0.6), 0, 0, 0]
        fr = self.hub.frame(t, st, (1,) * 5, op)
        d1 = self.hub.D[1]
        k = smooth((t - TL.T_GO) / 1.0)
        gx = lerp(160, d1['x'], k); gy = lerp(138, d1['yb'] - 18, k) + 2 * math.sin(t * 2.4) - 8 * math.sin(math.pi * k)
        face = 'happy' if t < TL.T_NEXT else ('wow' if t < TL.T_NEXT + 0.6 else 'determined')
        put_ghost(fr, t, gx, gy, face=face, arms='up' if TL.T_CLEAR < t < TL.T_NEXT else 'rest', look=(-1, 0) if t > TL.T_NEXT else (0, 0), scale=lerp(1, 0.8, k))
        L = self.hub.light(fr, st, (1,) * 5, op) + fr.band(gx, gy, 30, 22, (0.55, 0.75, 1.0), [(1.0, 0.15), (0.5, 0.3)])
        z = logz(1.0, 2.4, smooth((t - TL.T_GO - 0.3) / 1.2)); cx = lerp(160, d1['x'], smooth((t - TL.T_GO) / 1.3)); cy = lerp(98, d1['yb'] - 26, smooth((t - TL.T_GO) / 1.3))
        c = pcam(z, cx, cy)
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t), air=self.hub.air(fr, st, (1,) * 5, op))
        img = img + (1 - img) * smooth((t - TL.END + 0.4) / 0.4)
        cv = self.hud(t, year=False)
        ux, uy = c.w2ui(gx, gy - 24, 4)
        if TL.T_NEXT + 0.3 < t < TL.T_GO:
            q = back_out(clamp01((t - TL.T_NEXT - 0.3) / 0.2), 2)
            G.big_text(cv, '?', ux + 30, uy, 2, C('#ffe27a'), alpha=q)
        return self.compose(img, cv)

    def frame(self, t):
        img = self.ed.frame(min(t, TL.END - 1e-3))
        return ui_over(img, subs_layer(t, TL.L, TL.HL).a, scale=5)

def make(**kw): return Level1(**kw)
