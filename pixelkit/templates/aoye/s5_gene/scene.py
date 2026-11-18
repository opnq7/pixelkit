"""第 5 关 v2 · 这只钟藏在哪：实验室（显微镜 → 黑板 → 试管）→ period → 离开 / 诺奖 → 工厂机制 → 每个细胞 → 存档点 100%。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math, os
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s5_gene'))
import numpy as np, cv2
import timeline as TL
from common import subs_layer, lerp, smooth, FPS, put_human, nightcap, ghost_dive, hud2, revive_curve, Anchor
from pixelkit import ui, gameui as G, acting as A
from pixelkit.core import C, scale_nearest
from pixelkit.edit import Edit
from pixelkit.scene import ui_over
from pixelkit.pixstage import Stage, cam as pcam, GRADE_NIGHT, GRADE_WARM
from pixelkit.plates import Plate
from pixelkit.characters.cast_sleep import KONOPKA, LAUREATES
from pixelkit.characters import fly as FLY, worker as W
from pixelkit.sets.clock_factory import per_machine, loop_badge
from pixelkit.sets.cells import cells_stage
from pixelkit.anim import back_out, clamp01

PL = (_PROJ + '/assets/plates/')
def eo3(u): u = clamp01(u); return 1 - (1 - u) ** 3
def logz(a, b, k): return math.exp(math.log(a) + (math.log(b) - math.log(a)) * k)
CHALK = (232, 228, 214)
KEY = (275, 62)                      # desk lamp over the microscope
MAN = (204, 150)
SCOPE = (262, 92)
VIALS = [(238 + i * 11, 90) for i in range(7)]          # vials on the right bench (feet of each vial)
WEIRD = (2, 4, 6)                                        # which vials hold the odd flies
MACH = (178, 150)                                        # the PER machine on the factory floor

class Level5:
    def __init__(self):
        self.pA, self.pB, self.pC = Plate(PL + 'L5-A.png'), Plate(PL + 'L5-B.png'), Plate(PL + 'L5-C.png')
        self.anchor = Anchor()
        e = self.ed = Edit()
        e.add('lab', TL.S_LAB, self.f_lab)
        e.add('scope', TL.S_SCOPE, self.f_scope, 'cut')
        e.add('board', TL.S_BOARD, self.f_board, 'dissolve', 0.3)
        e.add('bench', TL.S_BENCH, self.f_bench, 'cut')
        e.add('weird', TL.S_WEIRD, self.f_bench, 'cut')
        e.add('gene', TL.S_GENE, self.f_board, 'cut')
        e.add('leave', TL.S_LEAVE, self.f_leave, 'dissolve', 0.4)
        e.add('nobel', TL.S_NOBEL, self.f_nobel, 'dissolve', 0.6)
        e.add('fac', TL.S_FAC, self.f_fac, 'dissolve', 0.5)
        e.add('cells', TL.S_CELLS, self.f_cells, 'dissolve', 0.5)
        e.add('anchor', TL.S_ANCHOR, self.f_anchor, 'dissolve', 0.5)
        e.end(TL.END)
        self.act_in = A.Act(face='normal', float_amp=1.5, look=(2, 1)).beat(1.3, 'ask', dur=0.7)
        self.act_bye = A.Act(face='sad', arms='wave', float_amp=1.4, look=(-2, 0))
        self.act_fac = A.Act(face='normal', float_amp=1.4, look=(2, 1)).beat(TL.S_FAC + 0.4, 'ask', dur=0.8)
        self.act_fac.beat(TL.T_PILE + 0.3, 'take', look=(2, 3), dur=0.8).beat(TL.T_HANDS + 0.1, 'cheer', dur=0.8)
        self.act_fac.beat(TL.T_PULL + 0.05, 'startle', dur=0.5).beat(TL.T_ON + 0.1, 'nodyes', dur=0.7)
        self.act_end = A.Act(face='sad', float_amp=1.8, look=(0, 3)).hold(TL.T_FULL, 99, face='happy').beat(TL.T_FULL + 0.05, 'cheer', dur=1.2)

    def fi(self, t): return int(round(t * FPS))
    def compose(self, img, cv): return ui_over(img, cv.a, scale=4)

    def hud(self, t, loc=True, pips=False):
        pct, fl = revive_curve(t, TL.T_FULL, 80, 100)
        cv = hud2(t, pct, 5 if t > TL.T_FULL + 0.6 else 4, fl, '1971' if loc else None, '加州理工 · 果蝇实验室',
                  t_enter=TL.T_TAG, t_out=TL.S_SCOPE - 0.3, k=1.0 if pips else 0.0)
        G.question_card(cv, t, TL.T_Q, '逼你睡觉的那只钟，藏在哪？', TL.T_ANS, '在每个细胞里：PER 攒够了，就关掉自己', hold=4.0, y=34)
        return cv

    def ghost(self, fr, t, act, x, y, scale=1.0):
        p = act.at(t); rgba, E, ax, ay = A.ghost_sprite(p, t)
        if abs(scale - 1) > 0.02: rgba = scale_nearest(rgba, scale); E = scale_nearest(E, scale)
        fr.sprite(rgba, x + p['dx'] - ax * scale, y + p['dy'] - ay * scale, E=E)
        return p, (x + p['dx'], y + p['dy'] - 24 * scale)

    def lab(self, t, face='focus', arms='rest', look=(2, 0), x=None, cap=True, chalk=None):
        P = self.pA; fr = P.frame()
        if chalk: self.chalk(fr, t, *chalk)
        for i in range(4):                                          # flies buzzing over the vials
            FLY.draw(fr, 268 + 16 * math.sin(t * 2.1 + i * 1.7), 74 + 5 * math.sin(t * 3.3 + i), t + i, scale=0.45, dir=1 if i % 2 else -1)
        mx = MAN[0] if x is None else x
        top = None
        if mx > -20:
            top = put_human(fr, KONOPKA, mx, MAN[1], face=face, arms=arms, look_dir=look, phase=int(t * 6) % 2)
            if cap: nightcap(fr, mx, top[1] + 2, t)
        return fr, top

    def chalk(self, fr, t, t0, kind):
        """kind 'hunch': clock -> DNA?   'gene': DNA with 'period' glowing."""
        k = clamp01((t - t0) / 0.8)
        if k <= 0: return
        cx, cy = 150, 46
        n = int(40 * k)
        for i in range(n):
            a = i / 40 * 2 * math.pi
            fr.px(cx + 12 * math.cos(a), cy + 12 * math.sin(a), CHALK)
        if k > 0.4: fr.line(cx, cy, cx, cy - 8, CHALK); fr.line(cx, cy, cx + 5, cy + 2, CHALK)
        if k > 0.6: fr.line(cx + 17, cy, cx + 30, cy, CHALK); fr.line(cx + 26, cy - 3, cx + 30, cy, CHALK); fr.line(cx + 26, cy + 3, cx + 30, cy, CHALK)
        k2 = clamp01((t - t0 - 0.5) / 0.8)
        for i in range(int(32 * k2)):
            x = cx + 36 + i * 1.2
            fr.px(x, cy + 9 * math.sin(i * 0.38), CHALK); fr.px(x, cy - 9 * math.sin(i * 0.38), CHALK)
            if i % 4 == 0: fr.line(x, cy + 9 * math.sin(i * 0.38), x, cy - 9 * math.sin(i * 0.38), (190, 186, 172))
        if kind == 'hunch' and k2 > 0.9: fr.text(cx + 76, cy - 14, '?', CHALK, 'zh12')
        if kind == 'gene':
            fr.fill(fr.M_rect(cx + 50, cy - 10, 12, 20) & (fr.img[..., 0] > 170), (255, 220, 120), 0.95)

    # ------------------------------------------------------------------ 1. lab + possession
    def f_lab(self, t):
        hit = t >= TL.T_HIT; white = max(0.0, 1 - (t - TL.T_HIT) / 0.12) if hit else 0.0
        face = 'focus' if not hit else ('surprised' if t < TL.T_HIT + 0.7 else 'normal')
        fr, top = self.lab(t, face=face, look=(3, 0) if not hit else (-1, 0), cap=t > TL.T_HIT + 0.15)
        p = None
        if t < TL.T_POSSESS:
            u = smooth((t - TL.T_GHOST_IN) / 1.4)
            p, head = self.ghost(fr, t, self.act_in, lerp(60, 170, u), lerp(100, 96, u))
        elif t < TL.T_POSSESS + 0.5:
            ghost_dive(fr, t, TL.T_POSSESS, (170, 96), (MAN[0], MAN[1] - 41), 0.45, look=(2, 1))
        L = self.pA.light(fr, key=KEY)
        if hit: L = L + fr.band(MAN[0], MAN[1] - 41, 30, 30, (0.7, 0.9, 1.0), [(1.0, 0.5 * white), (0.5, white)])
        k = smooth((t - TL.T_HIT) / 1.2)
        c = pcam(logz(1.04, 1.6, k), lerp(160, 222, k), lerp(92, 108, k), sx=10 * white * math.sin(t * 90))
        img = fr.render(c, L, GRADE_WARM, frame=self.fi(t))
        img = img + (1 - img) * (1 - smooth(t / 0.5))
        cv = self.hud(t)
        if p is not None: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if hit and t < TL.T_HIT + 0.5:
            ux, uy = c.w2ui(MAN[0], MAN[1] - 41, 4); d = t - TL.T_HIT
            G.burst_lines(cv, ux, uy, 20 + 160 * d, 34 + 200 * d, 16, C('#bfe8ff'), 1 - d / 0.5)
        ui.name_card(cv, 12, 200, '科诺普卡', 'LV.24', '', k=clamp01((t - TL.T_CARD) / 0.3) * (1 - clamp01((t - TL.S_SCOPE + 0.4) / 0.3)))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 2. into the microscope: a fly sleeping in a nightcap
    def scope_view(self, t):
        s = Stage(320, 180); s.img[..., :3] = (232, 214, 170); s.E[:] = 0
        s.grad(s.M_rect(0, 0, 320, 180), '#f0e2b8', '#c8a870', 0, 180, 5)
        s.fill(s.M_rect(0, 128, 320, 52), '#b07a3a'); s.fill(s.M_rect(0, 128, 320, 2), '#d8a85a')     # food layer
        FLY.draw(s, 160, 112, t, scale=6.0, mood='sleep', cap=True, dir=1)
        L = s.light_base((1.0, 0.95, 0.85), 1.0)
        return s.render(pcam(1.0), L, GRADE_WARM, frame=self.fi(t))

    def f_scope(self, t):
        fr, top = self.lab(t, face='focus', look=(3, 0))
        u = smooth((t - TL.S_SCOPE) / 0.6)
        c = pcam(logz(1.6, 5.0, u), lerp(222, SCOPE[0], u), lerp(108, SCOPE[1] - 6, u))
        base = fr.render(c, self.pA.light(fr, key=KEY), GRADE_WARM, frame=self.fi(t))
        view = self.scope_view(t)
        k = smooth((t - TL.S_SCOPE - 0.35) / 0.5)
        R = 40 + 520 * k
        yy, xx = np.ogrid[:1080, :1920]
        d2 = (xx - 960) ** 2 + (yy - 540) ** 2
        m = d2 <= R * R
        img = base.copy(); img[m] = view[m]
        img[(d2 > R * R) & (d2 <= (R + 30) ** 2)] *= 0.15                              # eyepiece rim
        img[d2 > (R + 30) ** 2] *= (1 - 0.85 * k)
        cv = self.hud(t, loc=False)
        if k > 0.9:
            for i in range(2):
                zt = (t * 0.9 + i * 0.5) % 1
                cv.text(int(300 + 16 * zt), int(84 - 30 * zt), 'z', (90, 60, 30, int(255 * (1 - zt))), 'p2p')
            a = clamp01((t - TL.S_SCOPE - 0.9) / 0.25)
            G._panel(cv, 24, 196, 150, 22, a); cv.text(32, 199, '任务：盯着果蝇睡觉', (255, 236, 200, int(255 * a)), 'zh12')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 3/6. the blackboard (hunch -> period)
    def f_board(self, t):
        gene = self.ed.shot_at(t) == 'gene'
        writing = (TL.T_CHALK <= t < TL.T_CHALK + 1.3) and not gene
        fr, top = self.lab(t, face='focus' if not gene else ('smile' if t > TL.T_ITEM else 'focus'), arms='up' if writing else 'rest',
                           look=(-2, -2), x=208, chalk=(TL.T_CHALK, 'hunch') if not gene else (-10, 'gene'))
        c = pcam(1.9, 172, 62)
        img = fr.render(c, self.pA.light(fr, key=KEY), GRADE_WARM, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        if gene:
            for i, vi in enumerate(()):
                u = smooth((t - TL.T_LINES - i * 0.18) / 0.7)
                if u <= 0: continue
                vx, vy = c.w2ui(*VIALS[vi], 4); gx, gy = c.w2ui(206, 46, 4)
                ex, ey = lerp(vx, gx, u), lerp(min(vy, 270), gy, u)
                cv.line(int(vx), int(min(vy, 268)), int(ex), int(ey), (255, 226, 140, 255))
            if t >= TL.T_NAME:
                d = t - TL.T_NAME; n = min(6, int(d / 0.09) + 1)
                G.pixel_word(cv, 'period'[:n], 240, 186, 4, C('#ffd34a'), C('#6a3a0a'), C('#fff2b0'), depth=2)
                if d < 0.6: G.burst_lines(cv, 240, 186, 80 + 160 * d, 100 + 200 * d, 16, C('#ffe27a'), 1 - d / 0.6)
            if t >= TL.T_ITEM:
                G.item_card(cv, t, TL.T_ITEM, 20, 120, None, '周期基因', '控制一天多长', price='', rarity=C('#ffd34a'), w=124,
                            life=TL.S_LEAVE - TL.T_ITEM + 0.2)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 4/5. the vial rack: a census, then three odd flies
    def f_bench(self, t):
        weird = self.ed.shot_at(t) == 'weird'
        fr, top = self.lab(t, face='focus', look=(3, 0), x=-99)
        c = pcam(2.6, 268, 86)
        L = self.pA.light(fr, key=KEY)
        if weird:                                                 # spotlight the three odd vials, dim the rest
            L = L * 0.45
            for j, vi in enumerate(WEIRD):
                if t >= TL.T_W[j]:
                    vx, vy = VIALS[vi]; L = L + fr.band(vx, vy - 8, 8, 18, (1.0, 0.9, 0.7), [(1.0, 0.6), (0.6, 0.9)])
        img = fr.render(c, L, GRADE_WARM, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        if not weird:
            a = clamp01((t - TL.T_VIALS) / 0.25)
            n = int(2000 * eo3((t - TL.T_VIALS) / 3.6))
            G._panel(cv, 24, 196, 150, 22, a); cv.text(32, 199, f'已记录 {n} 只', (255, 236, 200, int(255 * a)), 'zh12')
            for i, (vx, vy) in enumerate(VIALS):                  # a tiny sleep/wake strip appears over each vial
                k = clamp01((t - TL.T_VIALS - i * 0.15) / 0.4)
                if k <= 0: continue
                ux, uy = c.w2ui(vx, vy - 22, 4)
                for d in range(int(18 * k)):
                    on = math.sin((d / 18) * 2 * math.pi * 2 + i) > 0
                    cv.rect(int(ux - 9 + d), int(uy - (6 if on else 2)), 1, 6 if on else 2, (255, 210, 110, 255) if on else (130, 130, 170, 255))
        else:
            labels = [('19 小时', 3.2), ('29 小时', 0.6), ('没规律', None)]
            for j, vi in enumerate(WEIRD):
                if t < TL.T_W[j]: continue
                vx, vy = VIALS[vi]; ux, uy = c.w2ui(vx, vy - 30, 4)
                k = back_out(clamp01((t - TL.T_W[j]) / 0.3), 2.0)
                r = 14 * k
                cv.ellipse(ux, uy, r + 2, r + 2, (40, 24, 12, 255)); cv.ellipse(ux, uy, r, r, (246, 236, 210, 255))
                sp = labels[j][1]
                ang = (t * sp if sp is not None else 3 * math.sin(t * 5.3) + 2 * math.sin(t * 2.1)) - math.pi / 2
                if k > 0.8:
                    cv.line(int(ux), int(uy), int(ux + 10 * math.cos(ang)), int(uy + 10 * math.sin(ang)), (180, 40, 30, 255))
                    for q in range(12):
                        a_ = q / 12 * 2 * math.pi
                        cv.px(int(ux + 12 * math.cos(a_)), int(uy + 12 * math.sin(a_)), (90, 70, 50, 255))
                    tw = G.text_width(labels[j][0], 'zh12')
                    G._panel(cv, int(ux - tw / 2 - 6), int(uy + 18), tw + 12, 18, 1.0, accent=C('#ffd34a'))
                    cv.text(int(ux - tw / 2), int(uy + 20), labels[j][0], (255, 236, 180, 255), 'zh12')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 7. nobody cared; he leaves; the notebook stays
    def f_leave(self, t):
        walk = t >= TL.T_WALK
        x = MAN[0] if not walk else lerp(MAN[0], -30, smooth((t - TL.T_WALK) / 2.4))
        fr, top = self.lab(t, face='sad' if not walk else 'normal', look=(-2, 1), x=x, cap=t < TL.T_UNPOSSESS, chalk=(-10, 'gene'))
        nb = fr.M_rect(224, 96, 14, 9)
        fr.part(nb, ['#4a1a10', '#7a2a1c', '#a84a34', '#c86a50'], bevel=1.5, amb=0.5, ink='#1a0604')
        fr.text(226, 96, 'per', '#ffe0a0', 'silk', 0.7 if t > TL.T_LIGHT_OFF else 0.3)
        p = None
        if t >= TL.T_UNPOSSESS:
            u = eo3((t - TL.T_UNPOSSESS) / 0.5)
            p, head = self.ghost(fr, t, self.act_bye, lerp(MAN[0], 180, u), lerp(110, 88, u))
        k = smooth((t - TL.S_LEAVE) / 1.2)
        L = self.pA.light(fr, key=KEY) * np.array([lerp(1, 0.8, k), lerp(1, 0.82, k), lerp(1, 1.1, k)], np.float32)
        if t >= TL.T_LIGHT_OFF:
            o = smooth((t - TL.T_LIGHT_OFF) / 0.4)
            L = L * (1 - 0.6 * o) + fr.band(231, 100, 30, 20, (1.0, 0.85, 0.55), [(1.0, 0.25 * o), (0.5, 0.45 * o)])
        c = pcam(lerp(1.3, 1.6, smooth((t - TL.T_LIGHT_OFF) / 2.5)), lerp(190, 222, smooth((t - TL.T_LIGHT_OFF) / 2.5)), 100)
        img = fr.render(c, L, GRADE_WARM, frame=self.fi(t), desat=0.25 * k)
        cv = self.hud(t, loc=False)
        if p is not None: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if t >= TL.T_LIGHT_OFF:
            a = clamp01((t - TL.T_LIGHT_OFF - 0.3) / 0.4)
            G.big_zh(cv, '1971 — 2015', 240 - G.text_width('1971 — 2015', 'zh12'), 60, 2, C('#e8dccb'), a)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 8. 2017: the prize, and his notebook on the podium
    def f_nobel(self, t):
        P = self.pC; fr = P.frame()
        xs = (120, 200, 228)
        for i, x in enumerate(xs):
            top = put_human(fr, LAUREATES[i], x, 106, face='smile' if t >= TL.T_MEDAL else 'normal',
                            arms='wave' if (t >= TL.T_MEDAL and i == 0) else 'rest')
            if t >= TL.T_MEDAL: fr.ell(x, top[1] + 42, 2.5, 2.5, '#ffd23a', 0.9)
        nb = fr.M_rect(152, 72, 16, 5)                             # notebook on the podium
        fr.part(nb, ['#4a1a10', '#7a2a1c', '#a84a34', '#c86a50'], bevel=1.5, amb=0.5, ink='#1a0604')
        rng = np.random.default_rng(5)
        if t >= TL.T_MEDAL:
            for i in range(50):
                x0 = rng.uniform(0, 320); sp = rng.uniform(20, 50); ph = rng.uniform(0, 10)
                y = (t - TL.T_MEDAL) * sp - 10 + rng.uniform(-60, 0)
                if 0 < y < 120: fr.rect(x0 + 4 * math.sin(t * 3 + ph), y, 2, 1, ['#ffd23a', '#ff6a6a', '#7ae0ff', '#ffffff'][i % 4])
        L = P.light(fr, key=(160, 10))
        nk = clamp01((t - TL.T_NOTE) / 0.5)
        L = L + fr.band(160, 74, 18, 10, (1.0, 0.85, 0.55), [(1.0, 0.3 * nk), (0.5, 0.6 * nk)])
        u = smooth((t - TL.S_NOBEL) / 5)
        c = pcam(lerp(1.15, 1.25, u), 160, 84)
        if t > TL.T_NOTE: c = pcam(lerp(1.25, 2.0, smooth((t - TL.T_NOTE) / (TL.S_FAC - TL.T_NOTE))), 160, lerp(84, 78, smooth((t - TL.T_NOTE) / 1.2)))
        img = fr.render(c, L, GRADE_WARM, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        ui.chapter_banner(cv, t, '2017 诺贝尔奖', 'NOBEL PRIZE · 2017', TL.T_BANNER, TL.T_BANNER + 2.6, y=10, w=250)
        if t >= TL.T_NOTE:
            a = clamp01((t - TL.T_NOTE) / 0.3)
            ux, uy = c.w2ui(160, 66, 4)
            ui.speech_bubble(cv, ux, uy, '起点：1971 · 科诺普卡', t - TL.T_NOTE, life=TL.S_FAC - TL.T_NOTE + 0.4, side=1, with_coin=False, t=t)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 9. the clock factory: PER piles up, holds hands with TIM, switches the machine off
    def fac_frame(self, t):
        P = self.pB; fr = P.frame()
        off = TL.T_PULL <= t < TL.T_ON
        night = t < TL.T_SUN
        lever = 0.0
        if TL.T_PULL - 0.15 <= t < TL.T_ON: lever = smooth((t - TL.T_PULL + 0.15) / 0.3)
        if t >= TL.T_ON: lever = 1 - smooth((t - TL.T_ON) / 0.3)
        n = TL.per_count(t)
        anc = per_machine(fr, MACH[0], MACH[1], t, on=0.0 if off else 1.0, gauge=min(1.0, n / 9.0), lever=lever)
        ox, oy = anc['out']
        # PER pile in front of the chute
        for i in range(int(math.ceil(n))):
            px = ox + 6 + (i % 3) * 11; py = 160 - (i // 3) * 8
            sq = 0.0
            if not night: sq = clamp01(n - i) and (1 - clamp01(n - i))
            fade = clamp01(n - i)
            if fade <= 0.05: continue
            W.draw(fr, px, py, t, kind='mint', hat=None, badge='P', face='happy' if night else 'sleepy', scale=0.8 * (0.4 + 0.6 * fade), phase=i)
        # TIM walks in from the left, two PERs join hands with it and the trio walks to the lever
        lx, ly = anc['lever']
        if TL.T_TIM <= t < TL.T_ON + 0.4:
            u = smooth((t - TL.T_TIM) / 0.7)
            tx = lerp(-12, 92, u); ty = 160
            if t >= TL.T_HANDS:
                v = smooth((t - TL.T_HANDS - 0.2) / max(0.1, TL.T_PULL - TL.T_HANDS - 0.4))
                tx = lerp(92, lx - 10, v); ty = lerp(160, 132, v)
            W.draw(fr, tx, ty, t, kind='lilac', hat=None, badge='T', face='happy', walk=True, scale=1.15, dir=1,
                   hand=(tx + 10, ty - 9) if t >= TL.T_HANDS else None)
            if t >= TL.T_HANDS:
                W.draw(fr, tx + 15, ty, t, kind='mint', hat=None, badge='P', face='happy', walk=True, scale=1.15, dir=-1, phase=0.3)
                if TL.T_HANDS <= t < TL.T_HANDS + 0.5: fr.ell(tx + 8, ty - 22, 2.5, 2.5, '#ff6a8a', 1.0)
        L = P.light(fr) * P.flicker(fr, t, seed=8, amp=0.06)[..., None]
        if off: L = L * 0.72
        if not night: L = L * np.array([1.08, 1.04, 0.95], np.float32)
        return fr, L, anc

    def f_fac(self, t):
        fr, L, anc = self.fac_frame(t)
        p, head = self.ghost(fr, t, self.act_fac, 246, 84, scale=0.9)
        u = smooth((t - TL.S_FAC) / 2.0)
        c = pcam(logz(3.0, 1.45, u), lerp(160, 176, u), lerp(70, 112, u))
        img = fr.render(c, L, GRADE_WARM, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        if u > 0.6: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        night = t < TL.T_SUN
        a = clamp01((t - TL.S_FAC - 1.2) / 0.3)
        G._panel(cv, 18, 34, 112, 24, a)
        cv.text(26, 38, ('夜里' if night else '白天'), (255, 230, 170, int(255 * a)) if night else (255, 240, 150, int(255 * a)), 'zh12')
        cv.text(62, 41, f'PER {int(round(TL.per_count(t)))}', (130, 240, 200, int(255 * a)), 'p2p')
        if TL.T_PULL <= t < TL.T_PULL + 0.7: G.onomatopoeia(cv, '关！', 96, 84, t - TL.T_PULL, 3, C('#ff8a8a'), life=0.7)
        if TL.T_ON <= t < TL.T_ON + 0.7: G.onomatopoeia(cv, '开！', 96, 84, t - TL.T_ON, 3, C('#8aff9a'), life=0.7)
        if TL.T_PULL <= t < TL.T_ON:
            a2 = clamp01((t - TL.T_PULL - 0.3) / 0.2)
            ux, uy = c.w2ui(MACH[0], MACH[1] - 70, 4)
            G._panel(cv, int(ux - 56), int(uy - 22), 112, 20, a2, accent=C('#ff6a5a'))
            cv.text(int(ux - 48), int(uy - 20), '生产线：暂停', (255, 160, 140, int(255 * a2)), 'zh12')
        if t >= TL.T_LOOP: loop_badge(cv, t, TL.T_LOOP, 112, 146, r=30)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 10. every cell has one — and your phone scrambles them all
    def f_cells(self, t):
        chaos = smooth((t - TL.T_CHAOS) / 0.6)
        beat = max(0.0, math.sin(t * 2 * math.pi * 1.1)) ** 4
        s = cells_stage(t, beat=beat, chaos=chaos)
        L = s.light_base((1.0, 0.9, 0.9), 1.0)
        if chaos > 0: L = L + s.band(330, 90, 160, 140, (0.4, 0.7, 1.2), [(1.0, 0.18 * chaos), (0.6, 0.35 * chaos), (0.3, 0.5 * chaos)])
        u = eo3((t - TL.S_CELLS) / 1.8)
        c = pcam(logz(6.0, 1.0, u), lerp(165, 160, u), lerp(84, 90, u), sx=(2 * math.sin(t * 40) * chaos))
        img = s.render(c, L, GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        if chaos > 0.3:
            G.big_zh(cv, '节拍：乱了', 240 - G.text_width('节拍：乱了', 'zh12'), 100, 2, C('#ff7a6a'), chaos)
            G._panel(cv, 330, 168, 132, 20, chaos); cv.text(338, 170, '光源：手机屏幕', (150, 210, 255, int(255 * chaos)), 'zh12')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 11. the save point: 100%
    def f_anchor(self, t):
        u = smooth((t - TL.S_ANCHOR) / 1.0)
        color_k = 0.6 + 0.4 * smooth((t - TL.T_FULL) / 1.2)
        img, c, p, head = self.anchor.render(t, color_k, z=1.6, cx=184, cy=96, ghost_xy=(150, lerp(52, 84, u)), ghost_act=self.act_end,
                                             frame_i=self.fi(t))
        img = np.clip((np.clip(img, 0, 1) ** 0.8) * 1.35 + 0.02, 0, 1)
        img = img + (1 - img) * smooth((t - TL.END + 0.9) / 0.9)
        cv = self.hud(t, loc=False, pips=True)
        if p is not None: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if t >= TL.T_FULL + 0.4:
            k = back_out(clamp01((t - TL.T_FULL - 0.4) / 0.3), 1.6)
            G.big_zh(cv, '复活 100%', 240 - G.text_width('复活 100%', 'zh12'), int(196 - 6 * k), 2, C('#7fe0ff'), min(1, k))
        return self.compose(img, cv)

    def frame(self, t):
        img = self.ed.frame(min(t, TL.END - 1e-3))
        return ui_over(img, subs_layer(t, TL.L, TL.HL).a, scale=5)

def make(**kw): return Level5(**kw)
