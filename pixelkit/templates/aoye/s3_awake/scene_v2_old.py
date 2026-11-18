"""第 3 关 · 1964 264 小时不睡：Level3().frame(t)。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s3_awake'))
import numpy as np
import timeline as TL
from common import (subs_layer, ramp, lerp, smooth, FPS, put_human, nightcap, lying_head, put_ghost, ghost_dive, hud_layer)
from pixelkit import ui, gameui as G
from pixelkit.core import C
from pixelkit.edit import Edit
from pixelkit.scene import ui_over
from pixelkit.pixstage import Stage, cam as pcam, GRADE_NIGHT
from pixelkit.sets.home1964 import Home1964, GRADE_RETRO
from pixelkit.sets.hub_doors import HubDoors
from pixelkit.sets import symbols as SY
from pixelkit.characters.cast_sleep import GARDNER
from pixelkit.characters import human
from pixelkit.anim import back_out, clamp01

def eo3(u): u = clamp01(u); return 1 - (1 - u) ** 3
def logz(a, b, k): return math.exp(math.log(a) + (math.log(b) - math.log(a)) * k)

FOOTBALL = human.Look(hair='short', hair_col='#8a5a30', skin='#f2c8a0', cloth='tshirt', cloth_col='#d8402a', accent='#ffffff', seed=5)

class Level3:
    def __init__(self):
        self.home = Home1964(); self.hub = HubDoors()
        e = self.ed = Edit()
        e.add('home', TL.S_HOME, self.f_home)
        e.add('box', TL.S_BOX, self.f_box, 'cut')
        e.add('warp', TL.S_WARP, self.f_warp, 'cut')
        e.add('stad', TL.S_STAD, self.f_stad, 'flash', 0.25)
        e.add('board', TL.S_BOARD, self.f_board, 'cut')
        e.add('micro', TL.S_MICRO, self.f_micro, 'cut')
        e.add('road', TL.S_ROAD, self.f_road, 'cut')
        e.add('crash', TL.S_CRASH, self.f_crash, 'cut')
        e.add('revive', TL.S_REVIVE, self.f_revive, 'cut')
        e.add('slap', TL.S_SLAP, self.f_revive, 'cut')
        e.add('hub', TL.S_HUB, self.f_hub, 'flash', 0.36)
        e.end(TL.END)

    def fi(self, t): return int(round(t * FPS))

    def san(self, t):
        if t < TL.T_DAY2: return 100
        if t < TL.T_DAY4: return lerp(100, 82, eo3((t - TL.T_DAY2) / 0.4))
        if t < TL.T_DAY11: return lerp(82, 51, eo3((t - TL.T_DAY4) / 0.4))
        if t < TL.T_PICK: return lerp(51, 9, eo3((t - TL.T_DAY11) / 0.4))
        if t < TL.T_FREEZE: return lerp(9, 100, eo3((t - TL.T_PICK - 0.1) / 0.4))
        return 100

    def hud(self, t, year=True, san=True):
        pct = 40 + 20 * eo3((t - TL.T_ACH - 1.0) / 0.6)
        fl = max(0.0, 1 - abs(t - TL.T_ACH - 1.3) / 0.3) if t > TL.T_ACH + 1.0 else 0.0
        stage = 3 if t > TL.T_ACH + 1.3 else 2
        yk = clamp01((t - TL.T_TAG) / 0.35) * (1 - clamp01((t - TL.S_HUB) / 0.2))
        cv = hud_layer(t, pct, stage, fl, 1.0, '1964' if year else None, '美国 · 圣地亚哥 · 加德纳家', yk)
        if san and t >= TL.T_SAN and t < TL.S_HUB:
            G.sanity_bar(cv, 352, 40, self.san(t), t=t, k=clamp01((t - TL.T_SAN) / 0.35))
            for tt, v0, v1 in ((TL.T_DAY2, 100, 82), (TL.T_DAY4, 82, 51), (TL.T_DAY11, 51, 9)):
                d = t - tt
                if 0 < d < 0.8:
                    cv.text(400, 70 + int(10 * d), f'-{v0 - v1}', (255, 90, 80, int(255 * (1 - d / 0.8))), 'silkb')
        return cv

    def compose(self, img, cv): return ui_over(img, cv.a, scale=4)

    def day_of(self, t):
        if t < TL.T_DAY2: return 1
        if t < TL.T_DAY4: return 2
        if t < TL.T_DAY11: return 4
        return 11

    # ------------------------------------------------------------------ 1. home + possession
    def f_home(self, t):
        fr = self.home.frame(t, day=1)
        sx, sy = self.home.A['stand']
        hit = t >= TL.T_HIT; white = max(0.0, 1 - (t - TL.T_HIT) / 0.12) if hit else 0.0
        top = put_human(fr, GARDNER, sx, sy, face='smile' if not hit else ('surprised' if t < TL.T_HIT + 0.7 else 'smile'),
                        arms='rest' if not hit else ('up' if t > TL.T_HIT + 0.7 else 'rest'), white=white)
        if hit and t > TL.T_HIT + 0.15: nightcap(fr, sx, top[1] + 2, t)
        if t < TL.T_POSSESS:
            gx = lerp(340, 196, eo3((t - 0.6) / 1.8)); put_ghost(fr, t, gx, 64 + 3 * math.sin(t * 2.4), face='normal', look=(-2, 0))
        else:
            ghost_dive(fr, t, TL.T_POSSESS, (196, 64), (sx, top[1] + 14), 0.45, look=(-2, 0))
        L = self.home.light(fr)
        if hit: L = L + fr.band(sx, top[1] + 14, 30, 30, (0.7, 0.9, 1.0), [(1.0, 0.5 * white), (0.5, white)])
        k = smooth((t - TL.T_HIT) / 1.5)
        c = pcam(logz(1.05, 1.7, k), lerp(160, 150, k), lerp(92, 108, k), sx=12 * white * math.sin(t * 90))
        img = fr.render(c, L, GRADE_RETRO, frame=self.fi(t), air=self.home.air(fr))
        img = img + (1 - img) * (1 - smooth(t / 0.5))
        cv = self.hud(t)
        if hit and t < TL.T_HIT + 0.5:
            ux, uy = c.w2ui(sx, top[1] + 14, 4); d = t - TL.T_HIT
            G.burst_lines(cv, ux, uy, 20 + 160 * d, 34 + 200 * d, 16, C('#bfe8ff'), 1 - d / 0.5)
        G.char_card(cv, t, TL.T_CARD, '加德纳', 'LV.17', '硬撑', '1964 · 高中生 · 科学展参赛者', x=12, y=150, life=3.6)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 2. day 2: the mystery box
    def f_box(self, t):
        fr = self.home.frame(t, day=2)
        sx, sy = self.home.A['stand']
        top = put_human(fr, GARDNER, sx, sy, face='tired', arms='hold')
        nightcap(fr, sx, top[1] + 2, t)
        bx, by = sx + 2, sy - 22
        box = fr.rect(bx - 14, by, 28, 16, '#c88a4a'); fr.rect(bx - 14, by, 28, 3, '#e8a860'); fr.outline(box, '#2a1408')
        fr.text(bx - 6, by + 5, '?', '#2a1408', 'p2p')
        if t >= TL.T_APPLE:
            u = eo3((t - TL.T_APPLE) / 0.3)
            ay = by - 4 - 10 * u
            fr.ell(bx + 2, ay, 5, 5, '#d8302a'); fr.px(bx + 1, ay - 2, '#ff9a8a'); fr.rect(bx + 2, ay - 7, 1, 3, '#5a3a1a'); fr.px(bx + 3, ay - 7, '#4a9a3a')
        L = self.home.light(fr)
        c = pcam(2.0, sx + 10, top[1] + 26)
        img = fr.render(c, L, GRADE_RETRO, frame=self.fi(t), air=self.home.air(fr))
        cv = self.hud(t)
        self.day_badge(cv, t, TL.T_DAY2, '第 2 天')
        if t >= TL.T_SHOE:
            q = back_out(clamp01((t - TL.T_SHOE) / 0.25), 2)
            ux, uy = c.w2ui(sx + 16, by - 26, 4)
            cv.rrect(int(ux) - 4, int(uy) - 4, 92, 22, (255, 255, 255, int(255 * min(1, q))), 6)
            cv.text(int(ux), int(uy), '这是……鞋？', (40, 30, 30, int(255 * min(1, q))), 'zh12')
        return self.compose(img, cv)

    def day_badge(self, cv, t, t0, s):
        d = t - t0
        if d < 0 or d > 1.6: return
        q = back_out(clamp01(d / 0.25), 2.2) * (1 - clamp01((d - 1.3) / 0.3))
        G.big_text(cv, s, 110, 70, 3, C('#ffffff'), alpha=min(1, q))

    # ------------------------------------------------------------------ 3. day 4: the room starts to melt
    def f_warp(self, t):
        w = smooth((t - TL.T_DAY4 - 0.3) / 1.4)
        fr = self.home.frame(t, day=4, warp=w)
        sx, sy = self.home.A['stand']
        top = put_human(fr, GARDNER, sx, sy, face='surprised', arms='rest', look_dir=((-2, 0) if int(t * 3) % 2 else (2, 0)))
        nightcap(fr, sx, top[1] + 2, t)
        L = self.home.light(fr)
        img = fr.render(pcam(1.5, 160, 104), L, GRADE_RETRO, frame=self.fi(t), tint=(1.0 + 0.3 * w, 1.0 - 0.1 * w, 1.0 + 0.4 * w))
        cv = self.hud(t)
        self.day_badge(cv, t, TL.T_DAY4, '第 4 天')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 4. hallucination: the stadium
    def f_stad(self, t):
        if not hasattr(self, 'pStad'):
            from pixelkit.plates import Plate
            self.pStad = Plate((_PROJ + '/assets/plates/L3.png'))
        P = self.pStad; s = P.frame()
        u = smooth((t - TL.S_STAD) / (TL.S_BOARD - TL.S_STAD))
        # a hallucinated crowd fills the empty stands (flickering, slightly translucent-looking colours)
        rng = np.random.default_rng(4)
        stands = (s.yy > 62) & (s.yy < 100) & ~((s.xx > 150) & (s.xx < 172) & (s.yy > 78))
        for i in range(1400):
            x, y = int(rng.integers(0, 320)), int(rng.integers(62, 100))
            if stands[y, x] and (i + int(t * 6)) % 5:
                s.px(x, y - int(abs(math.sin(t * 9 + i)) > 0.8), ['#e05a7a', '#f0e0d0', '#6a8ae8', '#ffd84a', '#c86aff'][i % 5], 0.35)
        for i in range(8):
            if (int(t * 14) + i * 5) % 9 == 0: s.ell(int(rng.integers(10, 310)), int(rng.integers(64, 98)), 1.5, 1.5, '#ffffff', 1.0)
        # the "star player" charging at the camera
        y = lerp(118, 178, u); x = 160 + 6 * math.sin(t * 3)
        s.mul(s.M_ell(x, y, 12, 3), 0.55)
        top = put_human(s, FOOTBALL, x, y, face='smile', arms='hold', phase=int(t * 8) % 2)
        nightcap(s, x, top[1] + 2, t)
        s.ell(x + 13, y - 14, 5, 3.5, '#8a4a20'); s.line(x + 10, y - 14, x + 16, y - 14, '#ffffff')
        L = P.light(s) * P.flicker(s, t, seed=3, amp=0.18)[..., None]
        A_ = s.cone((28, 14), (-40, 180), (150, 180), (1.0, 0.95, 0.8), 0.04) + s.cone((292, 14), (170, 180), (360, 180), (1.0, 0.95, 0.8), 0.04)
        c = pcam(lerp(1.0, 1.55, u), 160, lerp(96, 130, u), sx=3 * math.sin(t * 30))
        img = s.render(c, L, GRADE_NIGHT, frame=self.fi(t), air=A_, tint=(1.12, 0.95, 1.15))
        # hallucination wobble: rows slide in a slow sine, colours breathe
        sh = (np.sin(np.arange(1080) / 70.0 + t * 5) * 10 * (0.5 + 0.5 * u)).astype(int)
        for yy in range(0, 1080, 6):
            if sh[yy]: img[yy:yy + 6] = np.roll(img[yy:yy + 6], sh[yy], 1)
        cv = self.hud(t)
        ux, uy = c.w2ui(x, top[1], 4)
        G.danmaku(cv, t, TL.S_STAD + 0.2, '全场都在喊你的名字！', y=104, speed=150, col=C('#ffd84a'))
        a = clamp01((t - TL.S_STAD - 0.4) / 0.2)
        G._panel(cv, 370, 196, 92, 18, a); cv.text(376, 198, '状态：幻觉', (255, 130, 220, int(255 * a)), 'zh10')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 5. day 11: 100 - 7 - 7 ... 65 ... ?
    def f_board(self, t):
        nums = ['100', '93', '86', '79', '72', '65']
        n = int(clamp01((t - TL.T_DAY11 - 1.2) / 2.6) * len(nums) + 0.999) if t > TL.T_DAY11 + 1.2 else 0
        fr = self.home.frame(t, day=11, board_lines=nums[:n])
        sx, sy = 132, 158
        stuck = n >= len(nums) and t > TL.L.e('C5') - 1.4
        top = put_human(fr, GARDNER, sx, sy, face='tired' if not stuck else 'o', arms='up' if not stuck else 'rest', look_dir=(-1, -1))
        nightcap(fr, sx, top[1] + 2, t)
        L = self.home.light(fr)
        c = pcam(2.3, 128, 64)
        img = fr.render(c, L, GRADE_RETRO, frame=self.fi(t), air=self.home.air(fr))
        cv = self.hud(t)
        self.day_badge(cv, t, TL.T_DAY11, '第 11 天')
        if stuck:
            q = back_out(clamp01((t - TL.L.e('C5') + 1.4) / 0.3), 2)
            G.big_text(cv, '?', 390, 120, 5, C('#ffe27a'), alpha=min(1, q))
        if self.san(t) < 25 and int(t * 6) % 2 == 0:
            cv.rect(0, 0, 480, 3, (255, 40, 40, 150)); cv.rect(0, 267, 480, 3, (255, 40, 40, 150))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 6. microsleep: eyes open, signal lost
    def f_micro(self, t):
        fr = self.home.frame(t, day=11)
        sx, sy = 150, 156
        top = put_human(fr, GARDNER, sx, sy, face='normal', arms='rest')
        nightcap(fr, sx, top[1] + 2, t)
        L = self.home.light(fr)
        img = fr.render(pcam(2.8, sx, top[1] + 22), L, GRADE_RETRO, frame=self.fi(t))
        cv = self.hud(t)
        if TL.T_BLACK0 <= t < TL.T_BLACK1:
            img = img * 0
            G.signal_lost(cv, 1.0, '信号中断', t)
            cv.text(200, 160, f'{(t - TL.T_BLACK0):.1f}s', (120, 120, 130, 255), 'silkb')
        elif t > TL.T_BLACK1 and t < TL.T_BLACK1 + 1.2:
            cv.text(300, 80, '……刚才怎么了？', (230, 230, 240, 255), 'zh10', outline=(0, 0, 0, 255))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 7. night road: the same few seconds
    def f_road(self, t):
        s = Stage(320, 180); s.img[..., :3] = (4, 5, 12); s.E[:] = 0
        road = s.poly([(-60, 180), (150, 92), (170, 92), (380, 180)], '#1a1a22')
        for k in range(8):
            ph = ((t * 1.6 + k / 8) % 1.0)
            y0 = 92 + 88 * ph ** 2; y1 = 92 + 88 * min(1, ph + 0.05) ** 2
            s.poly([(160 - 2 - 8 * ph, y0), (160 + 2 + 8 * ph, y0), (160 + 2 + 8 * (ph + 0.05), y1), (160 - 2 - 8 * (ph + 0.05), y1)], '#e8d860', 0.3)
        s.rect(0, 140, 320, 40, '#0a0a10')                    # dashboard
        s.ell(110, 150, 18, 10, '#14141c'); s.ell(110, 150, 14, 7, '#2a3a2a', 0.3)
        s.ell(160, 176, 36, 20, '#1a1a20'); s.fill(s.ring(s.M_ell(160, 176, 36, 20)), '#3a3a44')
        L = s.light_base((0.5, 0.5, 0.7), 0.8) + s.cone((160, 140), (40, 92), (280, 92), (1.0, 0.95, 0.8), 0.5)
        A = s.cone((160, 150), (110, 92), (210, 92), (1.0, 0.95, 0.8), 0.06)
        img = s.render(pcam(1.0), L, GRADE_NIGHT, frame=self.fi(t), air=A)
        cv = self.hud(t)
        if TL.T_ROADBLACK <= t < TL.T_ROADBLACK + 1.0:
            img = img * 0; G.signal_lost(cv, 1.0, '信号中断', t)
        if TL.T_HORN <= t < TL.T_HORN + 0.25:
            img = img + (1 - img) * 0.5
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 8. crash onto the bed -> 14 hours -> quiz
    def f_crash(self, t):
        fr = self.home.frame(t, day=11, tv=0.4)
        bx, by = self.home.A['bed']
        fall = eo3((t - TL.T_FALL) / 0.35)
        if t < TL.T_FALL:
            top = put_human(fr, GARDNER, 190, 150, face='tired', arms='rest'); nightcap(fr, 190, top[1] + 2, t)
        else:
            lying_head(fr, GARDNER, 222, 120 - 0 * fall, face='closed', blanket_col=('#5a3a6a', '#6a4a7a'), w=26, cap_t=t)
        L = self.home.light(fr, lamp=0.6)
        sh = 14 * max(0.0, 1 - (t - TL.T_FALL - 0.35) / 0.3) if t > TL.T_FALL + 0.35 else 0
        img = fr.render(pcam(1.9, 214, 120, sy=sh * math.sin(t * 80)), L, GRADE_RETRO, frame=self.fi(t))
        cv = self.hud(t)
        # 264.4 h counter then 14 h sleep clock
        if t < TL.T_FALL + 0.8:
            G.big_text(cv, '264.4 小时', 240, 54, 3, C('#ffd34a'))
        else:
            ui.zzz(cv, 330, 120, t, TL.T_FALL + 0.4, TL.S_REVIVE)
            h = min(14.0, (t - TL.T_FALL - 0.8) * 5)
            G.big_text(cv, f'睡了 {h:.0f} 小时', 240, 54, 2, C('#a8d8ff'))
        G.choice_panel(cv, t, TL.T_QUIZ, '醒来以后？', ('满血复活', '彻底废了'), pick=0, t_pick=TL.T_PICK,
                       countdown=max(1, 3 - int((t - TL.T_QUIZ) / 0.5)), y=76)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 9. revive! -> freeze -> slap the danmaku
    def f_revive(self, t):
        fr = self.home.frame(t, day=12, tv=1.0)
        frozen = t >= TL.T_FREEZE
        jump = eo3((t - TL.T_PICK) / 0.3)
        y = 156 - 14 * math.sin(math.pi * clamp01((t - TL.T_PICK) / 0.5))
        top = put_human(fr, GARDNER, 176, y, face='smile', arms='up')
        nightcap(fr, 176, top[1] + 2, t if not frozen else TL.T_FREEZE)
        L = self.home.light(fr)
        img = fr.render(pcam(1.6, 170, 110), L, GRADE_RETRO, frame=self.fi(t), desat=0.7 if frozen else 0)
        cv = self.hud(t)
        if not frozen:
            G.big_text(cv, '满血复活！', 240, 60, 3, C('#7fffa0'))
        # the danmaku
        dm = '懂了，熬完补觉就行'
        if t >= TL.T_DANMAKU:
            if t < TL.T_SLAP:
                age = min(t, TL.T_FREEZE) - TL.T_DANMAKU
                x = 500 - age * 140
                cv.text(int(x), 140, dm, (255, 255, 255, 255), 'zh12', outline=(20, 10, 20, 255))
            else:
                d = t - TL.T_SLAP
                x = 500 - (TL.T_FREEZE - TL.T_DANMAKU) * 140
                # shards
                for i, ch in enumerate(dm):
                    vx = (i - 4) * 30; vy = -60 + i * 9
                    px = x + i * 13 + vx * d; py = 140 + vy * d + 300 * d * d
                    if py < 280: cv.text(int(px), int(py), ch, (255, 255, 255, int(255 * max(0, 1 - d))), 'zh12', outline=(20, 10, 20, 255))
                if d < 0.35:
                    # giant pixel hand (simple flat palm)
                    hx, hy = x + 50, 120 + 30 * (1 - min(1, d / 0.08))
                    cv.rect(int(hx), int(hy), 70, 40, (240, 196, 160, 255)); cv.rect(int(hx), int(hy), 70, 2, (255, 225, 200, 255))
                    for f in range(4): cv.rect(int(hx) + 4 + f * 16, int(hy) - 18, 12, 20, (240, 196, 160, 255))
                    cv.rect(int(hx) - 14, int(hy) + 10, 16, 10, (240, 196, 160, 255))
                    G.burst_lines(cv, int(hx) + 35, int(hy) + 20, 30 + 200 * d, 50 + 260 * d, 14, C('#ffffff'), 1 - d / 0.35)
        ui.achievement(cv, t, TL.T_ACH, '极限纪录', '264.4 小时', life=2.6, y=44)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 10. hub
    def f_hub(self, t):
        st = ['cleared', 'cleared', 'cleared' if t >= TL.T_CLEAR else 'active', 'active' if t >= TL.T_NEXT else 'locked', 'locked']
        op = [0.55, 0.55, 0.55 * smooth((t - TL.T_CLEAR) / 0.5), eo3((t - TL.T_GO - 0.6) / 0.6), 0]
        fr = self.hub.frame(t, st, (1,) * 5, op)
        d3 = self.hub.D[3]
        k = smooth((t - TL.T_GO) / 1.0)
        gx = lerp(160, d3['x'], k); gy = lerp(140, d3['yb'] - 18, k) + 2 * math.sin(t * 2.4)
        put_ghost(fr, t, gx, gy, face='determined' if t > TL.T_NEXT else 'happy', look=(2, 0) if t > TL.T_NEXT else (0, 0), scale=lerp(1, 0.85, k))
        L = self.hub.light(fr, st, (1,) * 5, op) + fr.band(gx, gy, 30, 22, (0.55, 0.75, 1.0), [(1.0, 0.15), (0.5, 0.3)])
        z = logz(1.0, 2.6, smooth((t - TL.T_GO - 0.2) / 1.1)); cx = lerp(160, d3['x'], smooth((t - TL.T_GO) / 1.1)); cy = lerp(98, d3['yb'] - 28, smooth((t - TL.T_GO) / 1.1))
        img = fr.render(pcam(z, cx, cy), L, GRADE_NIGHT, frame=self.fi(t), air=self.hub.air(fr, st, (1,) * 5, op))
        img = img + (1 - img) * smooth((t - TL.END + 0.4) / 0.4)
        return self.compose(img, self.hud(t, year=False, san=False))

    def frame(self, t):
        img = self.ed.frame(min(t, TL.END - 1e-3))
        return ui_over(img, subs_layer(t, TL.L, TL.HL).a, scale=5)

def make(**kw): return Level3(**kw)
