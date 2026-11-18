"""第 3 关 v2 · 1964 264 小时不睡：一个问题 → 硬撑 11 天 → 幻觉/断片/微睡眠 → 一个答案 → 回到存档点（+20%）。Level3().frame(t)。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s3_awake'))
import numpy as np
import timeline as TL
from common import (subs_layer, lerp, smooth, FPS, put_human, nightcap, ghost_dive, hud2, revive_curve, Anchor, keyed)
from pixelkit import ui, gameui as G, acting as A
from pixelkit.core import C, scale_nearest
from pixelkit.edit import Edit
from pixelkit.scene import ui_over
from pixelkit.pixstage import Stage, cam as pcam, GRADE_NIGHT
from pixelkit.sets.home1964 import GRADE_RETRO
from pixelkit.sets.hub_doors import HubDoors
from pixelkit.plates import Plate
from pixelkit.characters.cast_sleep import GARDNER
from pixelkit.characters import human, sleep_head as SH
from pixelkit.anim import back_out, clamp01

PL = (_PROJ + '/assets/plates/')
def eo3(u): u = clamp01(u); return 1 - (1 - u) ** 3
def logz(a, b, k): return math.exp(math.log(a) + (math.log(b) - math.log(a)) * k)

FOOTBALL = human.Look(hair='short', hair_col='#8a5a30', skin='#f2c8a0', cloth='tshirt', cloth_col='#d8402a', accent='#ffffff', seed=5)
GX, GY = 128, 146                 # Gardner on the rug
BED_HEAD = (284, 83)              # the pillow
KEY_ROOM = (150, 130)

class Level3:
    def __init__(self):
        self.pA, self.pB, self.pS = Plate(PL + 'L3-A.png'), Plate(PL + 'L3-B.png'), Plate(PL + 'L3.png')
        self.hub = HubDoors(); self.anchor = Anchor()
        e = self.ed = Edit()
        e.add('home', TL.S_HOME, self.f_home)
        e.add('box', TL.S_BOX, self.f_box, 'dissolve', 0.3)
        e.add('warp', TL.S_WARP, self.f_warp, 'cut')
        e.add('stad', TL.S_STAD, self.f_stad, 'dissolve', 0.3)
        e.add('board', TL.S_BOARD, self.f_board, 'whip', 0.3, dir=1)
        e.add('micro', TL.S_MICRO, self.f_micro, 'cut')
        e.add('road', TL.S_ROAD, self.f_road, 'dissolve', 0.35)
        e.add('crash', TL.S_CRASH, self.f_crash, 'cut')
        e.add('revive', TL.S_REVIVE, self.f_revive, 'cut')
        e.add('slap', TL.S_SLAP, self.f_revive, 'cut')
        e.add('anchor', TL.S_ANCHOR, self.f_anchor, 'dissolve', 0.6)
        e.add('hub', TL.S_HUB, self.f_hub, 'dissolve', 0.5)
        e.end(TL.END)
        self.act_in = A.Act(face='normal', float_amp=1.6, look=(-2, 0))
        self.act_back = A.Act(face='sad', float_amp=1.8, look=(0, 3)).hold(TL.T_REVIVE, 99, face='happy').beat(TL.T_REVIVE + 0.05, 'cheer', dur=0.9)
        self.act_hub = A.Act(face='happy', float_amp=2.0).beat(TL.T_NEXT, 'ask', dur=0.7)

    def fi(self, t): return int(round(t * FPS))
    def compose(self, img, cv): return ui_over(img, cv.a, scale=4)

    def san(self, t):
        if t < TL.T_DAY2: return 100
        if t < TL.T_DAY4: return lerp(100, 82, eo3((t - TL.T_DAY2) / 0.4))
        if t < TL.T_DAY11: return lerp(82, 51, eo3((t - TL.T_DAY4) / 0.4))
        if t < TL.T_PICK: return lerp(51, 9, eo3((t - TL.T_DAY11) / 0.4))
        if t < TL.T_FREEZE: return lerp(9, 100, eo3((t - TL.T_PICK - 0.1) / 0.4))
        return 100

    def hud(self, t, loc=True, san=True, pips=False):
        pct, fl = revive_curve(t, TL.T_REVIVE, 40, 60)
        cv = hud2(t, pct, 3 if t > TL.T_REVIVE + 0.6 else 2, fl, '1964' if loc else None, '圣地亚哥 · 加德纳家',
                  t_enter=TL.T_TAG, t_out=TL.S_ANCHOR - 0.4, k=1.0 if pips else 0.0)
        if t < TL.S_ANCHOR + 0.7: G.question_card(cv, t, TL.T_Q, '人最多能撑多久不睡？', TL.T_ANS, '撑到 264 小时，但幻觉、断片全来了', hold=4.0, y=34)
        if san and TL.T_SAN <= t < TL.S_ANCHOR - 0.3:
            G.sanity_bar(cv, 352, 76, self.san(t), t=t, k=clamp01((t - TL.T_SAN) / 0.35))
            for tt, v0, v1 in ((TL.T_DAY2, 100, 82), (TL.T_DAY4, 82, 51), (TL.T_DAY11, 51, 9)):
                d = t - tt
                if 0 < d < 0.8: cv.text(432, 106 + int(10 * d), f'-{v0 - v1}', (255, 90, 80, int(255 * (1 - d / 0.8))), 'silkb')
        return cv

    def ghost(self, fr, t, act, x, y, scale=1.0):
        p = act.at(t); rgba, E, ax, ay = A.ghost_sprite(p, t)
        if abs(scale - 1) > 0.02: rgba = scale_nearest(rgba, scale); E = scale_nearest(E, scale)
        fr.sprite(rgba, x + p['dx'] - ax * scale, y + p['dy'] - ay * scale, E=E)
        return p, (x + p['dx'], y + p['dy'] - 24 * scale)

    def day_badge(self, cv, t, t0, s):
        d = t - t0
        if d < 0 or d > 1.6: return
        q = back_out(clamp01(d / 0.25), 2.2) * (1 - clamp01((d - 1.3) / 0.3))
        if q > 0.04:
            w = G.text_width(s, 'zh12') * 2 * 3 // 2
            G.big_zh(cv, s, 240 - w // 3, 36, 2, C('#ffffff'), min(1, q))

    def warp_img(self, img, w, t):
        """the room melts: rows slide in a slow sine, the colour channels split."""
        if w <= 0: return img
        H = img.shape[0]; out = img.copy()
        sh = (np.sin(np.arange(H) / 55.0 + t * 3.0) * 26 * w).astype(int)
        for y in range(0, H, 4):
            if sh[y]: out[y:y + 4] = np.roll(out[y:y + 4], sh[y], 1)
        d = int(8 * w)
        if d: out[..., 0] = np.roll(out[..., 0], d, 1); out[..., 2] = np.roll(out[..., 2], -d, 1)
        return out

    # ------------------------------------------------------------------ 1. the room + possession
    def f_home(self, t):
        P = self.pA; fr = P.frame()
        hit = t >= TL.T_HIT; white = max(0.0, 1 - (t - TL.T_HIT) / 0.12) if hit else 0.0
        top = put_human(fr, GARDNER, GX, GY, face='smile' if not hit else ('surprised' if t < TL.T_HIT + 0.7 else 'smile'),
                        arms='rest', white=white)
        if hit and t > TL.T_HIT + 0.15: nightcap(fr, GX, top[1] + 2, t)
        p = None; head = None
        if t < TL.T_POSSESS:
            gx = lerp(340, 196, eo3((t - 0.6) / 1.8)); p, head = self.ghost(fr, t, self.act_in, gx, 64 + 3 * math.sin(t * 2.4))
        else:
            ghost_dive(fr, t, TL.T_POSSESS, (196, 64), (GX, top[1] + 14), 0.45, look=(-2, 0))
        L = P.light(fr, key=KEY_ROOM)
        if hit: L = L + fr.band(GX, top[1] + 14, 30, 30, (0.7, 0.9, 1.0), [(1.0, 0.5 * white), (0.5, white)])
        k = smooth((t - TL.T_HIT) / 1.5)
        c = pcam(logz(1.0, 1.75, k), lerp(160, GX + 12, k), lerp(92, 108, k), sx=10 * white * math.sin(t * 90))
        img = fr.render(c, L, GRADE_RETRO, frame=self.fi(t))
        img = img + (1 - img) * (1 - smooth(t / 0.5))
        cv = self.hud(t)
        if p is not None: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if hit and t < TL.T_HIT + 0.5:
            ux, uy = c.w2ui(GX, top[1] + 14, 4); d = t - TL.T_HIT
            G.burst_lines(cv, ux, uy, 20 + 160 * d, 34 + 200 * d, 16, C('#bfe8ff'), 1 - d / 0.5)
        G.char_card(cv, t, TL.T_CARD, '加德纳', 'LV.17', '硬撑', '1964 · 高中生 · 科学展参赛者', x=12, y=150, life=3.6)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 2. day 2: the mystery box
    def f_box(self, t):
        P = self.pA; fr = P.frame()
        top = put_human(fr, GARDNER, GX, GY, face='tired', arms='hold')
        nightcap(fr, GX, top[1] + 2, t)
        bx, by = GX + 2, GY - 22
        box = fr.rect(bx - 14, by, 28, 16, '#c88a4a'); fr.rect(bx - 14, by, 28, 3, '#e8a860'); fr.outline(box, '#2a1408')
        fr.text(bx - 6, by + 5, '?', '#2a1408', 'p2p')
        if t >= TL.T_APPLE:
            u = eo3((t - TL.T_APPLE) / 0.3); ay = by - 4 - 10 * u
            fr.ell(bx + 2, ay, 5, 5, '#d8302a'); fr.px(bx + 1, ay - 2, '#ff9a8a'); fr.rect(bx + 2, ay - 7, 1, 3, '#5a3a1a'); fr.px(bx + 3, ay - 7, '#4a9a3a')
        L = P.light(fr, key=KEY_ROOM)
        c = pcam(2.0, GX + 14, top[1] + 26)
        img = fr.render(c, L, GRADE_RETRO, frame=self.fi(t))
        cv = self.hud(t)
        self.day_badge(cv, t, TL.T_DAY2, '第 2 天')
        if t >= TL.T_SHOE:
            ux, uy = c.w2ui(GX + 18, by - 26, 4)
            ui.speech_bubble(cv, ux, uy + 8, '这是……鞋？', t - TL.T_SHOE, life=TL.S_WARP - TL.T_SHOE, side=1, with_coin=False, t=t)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 3. day 4: the room starts to melt
    def f_warp(self, t):
        w = smooth((t - TL.T_DAY4 - 0.3) / 1.4)
        P = self.pA; fr = P.frame()
        top = put_human(fr, GARDNER, GX, GY, face='surprised', arms='rest', look_dir=((-2, 0) if int(t * 3) % 2 else (2, 0)))
        nightcap(fr, GX, top[1] + 2, t)
        L = P.light(fr, key=KEY_ROOM)
        img = fr.render(pcam(1.5, 150, 104), L, GRADE_RETRO, frame=self.fi(t), tint=(1.0 + 0.3 * w, 1.0 - 0.1 * w, 1.0 + 0.4 * w))
        img = self.warp_img(img, w, t)
        cv = self.hud(t)
        self.day_badge(cv, t, TL.T_DAY4, '第 4 天')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 4. hallucination: the stadium
    def f_stad(self, t):
        P = self.pS; s = P.frame()
        u = smooth((t - TL.S_STAD) / (TL.S_BOARD - TL.S_STAD))
        rng = np.random.default_rng(4)
        stands = (s.yy > 62) & (s.yy < 100) & ~((s.xx > 150) & (s.xx < 172) & (s.yy > 78))
        for i in range(1400):
            x, y = int(rng.integers(0, 320)), int(rng.integers(62, 100))
            if stands[y, x] and (i + int(t * 6)) % 5:
                s.px(x, y - int(abs(math.sin(t * 9 + i)) > 0.8), ['#e05a7a', '#f0e0d0', '#6a8ae8', '#ffd84a', '#c86aff'][i % 5], 0.35)
        for i in range(8):
            if (int(t * 14) + i * 5) % 9 == 0: s.ell(int(rng.integers(10, 310)), int(rng.integers(64, 98)), 1.5, 1.5, '#ffffff', 1.0)
        y = lerp(118, 178, u); x = 160 + 6 * math.sin(t * 3)
        s.mul(s.M_ell(x, y, 12, 3), 0.55)
        top = put_human(s, FOOTBALL, x, y, face='smile', arms='hold', phase=int(t * 8) % 2)
        nightcap(s, x, top[1] + 2, t)
        s.ell(x + 13, y - 14, 5, 3.5, '#8a4a20'); s.line(x + 10, y - 14, x + 16, y - 14, '#ffffff')
        L = P.light(s) * P.flicker(s, t, seed=3, amp=0.18)[..., None]
        A_ = s.cone((28, 14), (-40, 180), (150, 180), (1.0, 0.95, 0.8), 0.04) + s.cone((292, 14), (170, 180), (360, 180), (1.0, 0.95, 0.8), 0.04)
        c = pcam(lerp(1.0, 1.55, u), 160, lerp(96, 130, u), sx=3 * math.sin(t * 30))
        img = s.render(c, L, GRADE_NIGHT, frame=self.fi(t), air=A_, tint=(1.12, 0.95, 1.15))
        sh = (np.sin(np.arange(1080) / 70.0 + t * 5) * 10 * (0.5 + 0.5 * u)).astype(int)
        for yy in range(0, 1080, 6):
            if sh[yy]: img[yy:yy + 6] = np.roll(img[yy:yy + 6], sh[yy], 1)
        cv = self.hud(t)
        G.danmaku(cv, t, TL.S_STAD + 0.2, '全场都在喊你的名字！', y=108, speed=150, col=C('#ffd84a'))
        a = clamp01((t - TL.S_STAD - 0.4) / 0.2)
        G._panel(cv, 360, 200, 108, 22, a, accent=C('#ff82dc')); cv.text(370, 204, '状态：幻觉', (255, 130, 220, int(255 * a)), 'zh10')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 5. day 11: 100 - 7 - 7 ... 65 ... ?   (written on the science-fair board)
    def f_board(self, t):
        P = self.pA; fr = P.frame()
        nums = ['100', '93', '86', '79', '72', '65']
        n = int(clamp01((t - TL.T_DAY11 - 1.2) / 2.6) * len(nums) + 0.999) if t > TL.T_DAY11 + 1.2 else 0
        for i in range(n):
            col, row = divmod(i, 3)
            fr.text(160 + col * 22, 42 + row * 10, nums[i], '#2a2a40', 'silkb')
        stuck = n >= len(nums) and t > TL.L.e('C5') - 1.4
        if stuck: fr.text(182 + 3, 62, '?', '#d83a2a', 'zh12')
        top = put_human(fr, GARDNER, 150, 150, face='tired' if not stuck else 'o', arms='up' if not stuck else 'rest', look_dir=(1, -1))
        nightcap(fr, 150, top[1] + 2, t)
        L = P.light(fr, key=KEY_ROOM) + fr.band(182, 56, 40, 30, (1.0, 0.95, 0.85), [(1.0, 0.12)])
        c = pcam(1.9, 172, 86)
        img = fr.render(c, L, GRADE_RETRO, frame=self.fi(t))
        cv = self.hud(t)
        self.day_badge(cv, t, TL.T_DAY11, '第 11 天')
        if n > 0 and not stuck:
            G._panel(cv, 18, 150, 118, 22, 1.0); cv.text(26, 154, '100 - 7 - 7 ...', (255, 236, 200, 255), 'zh10')
        if stuck:
            q = back_out(clamp01((t - TL.L.e('C5') + 1.4) / 0.3), 2)
            G.big_zh(cv, '?', 380, 120, 5, C('#ffe27a'), min(1, q))
        if self.san(t) < 25 and int(t * 6) % 2 == 0:
            cv.rect(0, 0, 480, 3, (255, 40, 40, 150)); cv.rect(0, 267, 480, 3, (255, 40, 40, 150))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 6. microsleep: eyes open, signal lost
    def f_micro(self, t):
        P = self.pA; fr = P.frame()
        sx, sy = 150, 152
        top = put_human(fr, GARDNER, sx, sy, face='normal', arms='rest')
        nightcap(fr, sx, top[1] + 2, t)
        L = P.light(fr, key=KEY_ROOM)
        img = fr.render(pcam(2.8, sx, top[1] + 22), L, GRADE_RETRO, frame=self.fi(t))
        cv = self.hud(t)
        if TL.T_BLACK0 <= t < TL.T_BLACK1:
            img = img * 0
            G.signal_lost(cv, 1.0, '信号中断', t)
            cv.text(200, 160, f'{(t - TL.T_BLACK0):.1f}s', (120, 120, 130, 255), 'silkb')
        elif TL.T_BLACK1 < t < TL.T_BLACK1 + 1.2:
            ui.speech_bubble(cv, 270, 100, '刚才怎么了？', t - TL.T_BLACK1, life=1.2, side=1, with_coin=False, t=t)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 7. the night road: the same few seconds, behind the wheel
    def f_road(self, t):
        P = self.pB; fr = P.frame()
        L = P.light(fr)
        u = smooth((t - TL.S_ROAD) / (TL.T_ROADBLACK - TL.S_ROAD))
        drift = smooth((t - TL.T_ROADBLACK - 0.6) / 0.5)
        c = pcam(lerp(1.0, 1.22, u), lerp(160, 150, u) + 24 * drift, lerp(92, 88, u), sx=2.0 * math.sin(t * 60) * (1 + 3 * drift))
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t))
        # heavy eyelids: two drooping blinks, then shut
        droop = 0.0
        ph = (t - TL.S_ROAD)
        if t < TL.T_ROADBLACK: droop = 0.16 * max(0.0, math.sin(ph * 1.9)) ** 2 + 0.10 * u
        if TL.T_ROADBLACK <= t < TL.T_ROADBLACK + 1.0: droop = 0.5 + 0.0
        if droop > 0:
            H = 1080; yy = np.arange(H)[:, None]
            lid_t = droop * H * (1 + 0.08 * np.sin(np.arange(1920) / 300.0))[None, :]
            m = (yy < lid_t) | (yy > H - lid_t)
            img = img.copy(); img[m] = 0.0
        cv = self.hud(t)
        if TL.T_ROADBLACK <= t < TL.T_ROADBLACK + 1.0:
            G.signal_lost(cv, 1.0, '信号中断', t)
        if TL.T_HORN <= t < TL.T_HORN + 0.4:
            G.onomatopoeia(cv, '嘀——！', 360, 90, t - TL.T_HORN, 3, C('#ffe27a'), life=0.4)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 8. fall onto the bed -> 14 hours -> quiz
    def f_crash(self, t):
        P = self.pA; fr = P.frame()
        if t < TL.T_FALL:
            top = put_human(fr, GARDNER, 238, 146, face='tired', arms='rest', tilt=-6 * smooth((t - TL.S_CRASH) / 0.4)); nightcap(fr, 238, top[1] + 2, t)
        else:
            SH.draw(fr, BED_HEAD[0], BED_HEAD[1], t, s=0.85, cap=True, face='sleep', facing=-1)
        L = P.light(fr, key=KEY_ROOM)
        sh = 12 * max(0.0, 1 - (t - TL.T_FALL) / 0.3) if t >= TL.T_FALL else 0
        c = pcam(2.1, 262, 84, sy=sh * math.sin(t * 80))
        img = fr.render(c, L, GRADE_RETRO, frame=self.fi(t))
        cv = self.hud(t)
        if TL.T_FALL <= t < TL.T_FALL + 0.45: G.onomatopoeia(cv, '咚！', 280, 90, t - TL.T_FALL, 3, C('#ffe27a'), life=0.45)
        if t < TL.T_FALL + 0.8:
            G.big_zh(cv, '264.4 小时', 18, 186, 2, C('#ffd34a'), 1.0)
        else:
            ui.zzz(cv, 340, 120, t, TL.T_FALL + 0.4, TL.S_REVIVE)
            h = min(14.0, (t - TL.T_FALL - 0.8) * 5)
            G.big_zh(cv, f'睡了 {h:.0f} 小时', 18, 186, 2, C('#a8d8ff'), 1.0)
        G.choice_panel(cv, t, TL.T_QUIZ, '醒来以后？', ('满血复活', '彻底废了'), pick=0, t_pick=TL.T_PICK,
                       countdown=max(1, 3 - int((t - TL.T_QUIZ) / 0.5)), y=76)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 9. revive! -> freeze -> the comment gets smashed
    def f_revive(self, t):
        P = self.pA; fr = P.frame()
        frozen = t >= TL.T_FREEZE
        y = 146 - 14 * math.sin(math.pi * clamp01((t - TL.T_PICK) / 0.5))
        top = put_human(fr, GARDNER, 232, y, face='smile', arms='up')
        nightcap(fr, 232, top[1] + 2, t if not frozen else TL.T_FREEZE)
        L = P.light(fr, key=KEY_ROOM)
        img = fr.render(pcam(1.6, 214, 106), L, GRADE_RETRO, frame=self.fi(t), desat=0.7 if frozen else 0)
        cv = self.hud(t)
        if not frozen:
            G.big_zh(cv, '满血复活！', 240 - G.text_width('满血复活！', 'zh12') * 3 // 2, 90, 3, C('#7fffa0'), 1.0)
        dm = '懂了，熬完补觉就行'
        if t >= TL.T_DANMAKU:
            tw = G.text_width(dm, 'zh12')
            if t < TL.T_SLAP:
                age = min(t, TL.T_FREEZE) - TL.T_DANMAKU
                x = 500 - age * 140
                cv.text(int(x), 130, dm, (255, 255, 255, 255), 'zh12', outline=(20, 10, 20, 255))
            else:
                d = t - TL.T_SLAP
                x = 500 - (TL.T_FREEZE - TL.T_DANMAKU) * 140
                for i, ch in enumerate(dm):                          # the comment shatters into characters
                    vx = (i - 4) * 30; vy = -60 + i * 9
                    px = x + i * 13 + vx * d; py = 130 + vy * d + 300 * d * d
                    if py < 280: cv.text(int(px), int(py), ch, (255, 255, 255, int(255 * max(0, 1 - d))), 'zh12', outline=(20, 10, 20, 255))
                if d < 0.5:
                    G.onomatopoeia(cv, '啪！', int(x + tw / 2), 120, d, 4, C('#ffffff'), life=0.5)
                    G.burst_lines(cv, int(x + tw / 2), 134, 30 + 220 * d, 50 + 280 * d, 14, C('#ffffff'), 1 - d / 0.5)
                if d >= 0.2: ui.rubber_stamp(cv, 110, 160, '打脸', d - 0.2, fname='zh12', scale=3, angle=-8)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 10. back at the 03:56 save point: +20%
    def f_anchor(self, t):
        u = smooth((t - TL.S_ANCHOR) / 1.0)
        gy = lerp(58, 90, u)
        color_k = 0.55 + 0.2 * smooth((t - TL.T_REVIVE) / 0.8)
        img, c, p, head = self.anchor.render(t, color_k, z=lerp(1.5, 1.7, smooth((t - TL.S_ANCHOR) / 3.0)), cx=184, cy=96, ghost_xy=(150, gy - 6),
                                             ghost_act=self.act_back, frame_i=self.fi(t))
        img = np.clip((np.clip(img, 0, 1) ** 0.8) * 1.35 + 0.02, 0, 1)
        cv = self.hud(t, loc=False, san=False, pips=True)
        if p is not None: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if TL.T_REVIVE - 0.1 <= t < TL.T_REVIVE + 1.4:
            q = t - TL.T_REVIVE + 0.1
            k = back_out(clamp01(q / 0.3), 1.6) * (1 - clamp01((q - 1.1) / 0.3))
            if k > 0.05: G.big_zh(cv, '复活 +20%', 240 - int(G.text_width('复活 +20%', 'zh12')), int(196 - 6 * k), 2, C('#7fe0ff'), min(1, k))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 11. hub: the next door
    def f_hub(self, t):
        st = ['cleared', 'cleared', 'cleared' if t >= TL.T_CLEAR else 'active', 'active' if t >= TL.T_NEXT else 'locked', 'locked']
        op = [0.55, 0.55, 0.55 * smooth((t - TL.T_CLEAR) / 0.5), eo3((t - TL.T_GO - 0.5) / 0.6), 0]
        fr = self.hub.frame(t, st, (1,) * 5, op)
        d3 = self.hub.D[3]
        k = smooth((t - TL.T_GO) / 1.0)
        gx = lerp(160, d3['x'], k); gy = lerp(140, d3['yb'] - 18, k)
        p, head = self.ghost(fr, t, self.act_hub, gx, gy, scale=lerp(1, 0.85, k))
        L = self.hub.light(fr, st, (1,) * 5, op) + fr.band(gx, gy, 30, 22, (0.55, 0.75, 1.0), [(1.0, 0.15), (0.5, 0.3)])
        z = logz(1.0, 2.6, smooth((t - TL.T_GO - 0.2) / 1.1)); cx = lerp(160, d3['x'], smooth((t - TL.T_GO) / 1.1)); cy = lerp(98, d3['yb'] - 28, smooth((t - TL.T_GO) / 1.1))
        c = pcam(z, cx, cy)
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t), air=self.hub.air(fr, st, (1,) * 5, op))
        img = img + (1 - img) * smooth((t - TL.END + 0.4) / 0.4)
        cv = self.hud(t, loc=False, san=False, pips=True)
        A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if TL.T_BTN <= t < TL.T_GO + 0.2:
            G.item_card(cv, t, TL.T_BTN, 176, 50, None, '极限纪录', '264.4 小时不睡', price='已获得', price_t=TL.T_BTN + 0.5,
                        rarity=C('#ffd34a'), w=130, life=TL.T_GO + 0.2 - TL.T_BTN)
        return self.compose(img, cv)

    def frame(self, t):
        img = self.ed.frame(min(t, TL.END - 1e-3))
        return ui_over(img, subs_layer(t, TL.L, TL.HL).a, scale=5)

def make(**kw): return Level3(**kw)
