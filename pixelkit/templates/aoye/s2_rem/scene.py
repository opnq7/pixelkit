"""第 2 关 · 1953 快速眼动 + 大脑夜班大楼：Level2().frame(t)。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s2_rem'))
import numpy as np
import timeline as TL
from common import (subs_layer, ramp, lerp, smooth, FPS, put_human, nightcap, lying_head, put_ghost, ghost_dive, hud2, revive_curve, Anchor, keyed)
from pixelkit import ui, gameui as G
from pixelkit.core import C
from pixelkit.edit import Edit
from pixelkit.scene import ui_over
from pixelkit.pixstage import Stage, cam as pcam, GRADE_NIGHT
from pixelkit.sets.lab1953 import Lab1953, GRADE_LAB
from pixelkit.sets.brain_tower import BrainTower
from pixelkit.sets.hub_doors import HubDoors
from pixelkit.sets import symbols as SY
from pixelkit.characters.cast_sleep import ASERINSKY, KID
from pixelkit.characters import sleep_head as SH
from pixelkit.anim import back_out, clamp01
import cv2
from pixelkit.core import scale_nearest
from pixelkit.plates import Plate
from pixelkit.characters import worker as W
from pixelkit import acting as A
PL = (_PROJ + '/assets/plates/')
KEY_LAB = (150, 130)
KID_HEAD = (274, 67)
ASX, ASY = 196, 142

def eo3(u): u = clamp01(u); return 1 - (1 - u) ** 3
def logz(a, b, k): return math.exp(math.log(a) + (math.log(b) - math.log(a)) * k)

class Level2:
    def __init__(self):
        self.lab = Lab1953(); self.bt = BrainTower(); self.hub = HubDoors(); self.anchor = Anchor(); self.pL = Plate(PL + 'L2-L.png')
        self.pA, self.pB, self.pC = Plate(PL + 'L2-A.png'), Plate(PL + 'L2-B.png'), Plate(PL + 'L2-C.png')
        self.pD1, self.pD2 = Plate(PL + 'L2-D1.png'), Plate(PL + 'L2-D2.png')
        self.act_tower = A.Act(face='determined', float_amp=0.0)
        self.act_arch = A.Act(face='normal', float_amp=1.5, look=(2, 0)).beat(TL.S_ARCH + 0.2, 'ask')
        self.act_arch.hold(TL.T_CARD_UP, TL.T_CARD_STAMP, face='wow', look=(2, 1)).beat(TL.T_CARD_STAMP + 0.05, 'sigh', dur=0.9)
        self.act_emo = A.Act(face='normal', float_amp=1.5, look=(3, 0)).beat(TL.S_EMO + 0.3, 'peek', dir=1, dist=5)
        self.act_emo.beat(TL.T_POP, 'startle', dur=0.5).beat(TL.T_TOWEL + 0.2, 'nodyes', dur=0.8)
        self.act_base = A.Act(face='normal', float_amp=1.5, look=(0, 1))
        self.act_base.beat(TL.T_VALVE + 0.1, 'startle', dur=0.6).beat(TL.T_WAVE - 0.35, 'take', look=(0, 4), dur=0.5)
        self.act_base.beat(TL.T_SWEPT, 'tumble', dur=1.2, turns=2.0, dir=-1).hold(TL.T_SWEPT + 1.6, 99, face='sad')
        self.act_base.beat(TL.T_SWEPT + 1.95, 'shiver', dur=1.6)
        self.act_back = A.Act(face='sad', float_amp=1.8, look=(0, 3)).hold(TL.T_REVIVE, 99, face='happy').beat(TL.T_REVIVE + 0.05, 'cheer', dur=0.9)
        self.act_in = A.Act(face='normal', float_amp=1.6, look=(2, 0))
        e = self.ed = Edit()
        e.add('lab', TL.S_LAB, self.f_lab)
        e.add('lean', TL.S_LEAN, self.f_lean, 'cut')
        e.add('off', TL.S_OFF, self.f_off, 'dissolve', 0.3)
        e.add('eye', TL.S_EYE, self.f_eye, 'dissolve', 0.25)
        e.add('eeg', TL.S_EEG, self.f_eeg, 'dissolve', 0.25)
        e.add('disc', TL.S_DISC, self.f_disc, 'cut')
        e.add('into', TL.S_INTO, self.f_into, 'cut')
        e.add('arch', TL.S_ARCH, self.f_arch, 'cut')
        e.add('emo', TL.S_EMO, self.f_emo, 'cut')
        e.add('base', TL.S_BASE, self.f_base, 'cut')
        e.add('ext2', TL.S_EXT2, self.f_ext2, 'dissolve', 0.4)
        e.add('sched', TL.S_SCHED, self.f_sched, 'dissolve', 0.3)
        e.add('anchor', TL.S_ANCHOR, self.f_anchor, 'dissolve', 0.6)
        e.add('hub', TL.S_HUB, self.f_hub, 'dissolve', 0.5)
        e.end(TL.END)

    def fi(self, t): return int(round(t * FPS))

    def hud(self, t, loc=True, pips=False):
        pct, fl = revive_curve(t, TL.T_REVIVE, 20, 40)
        cv = hud2(t, pct, 2 if t > TL.T_REVIVE + 0.6 else 1, fl, '1953' if loc else None, '芝加哥 · 深夜实验室',
                  t_enter=TL.T_TAG, t_out=TL.S_ARCH - 0.4, k=1.0 if pips else 0.0)
        if t < TL.S_ANCHOR + 0.7: G.question_card(cv, t, TL.T_Q, '睡着以后，大脑在忙什么？', TL.T_ANS, '睡觉不是关机，是系统维护', hold=4.0, y=34)
        return cv

    def compose(self, img, cv): return ui_over(img, cv.a, scale=4)

    def pens(self, wild):
        def f(t, ch):
            a = 0.8 + 4.2 * wild
            return int(round(a * math.sin(t * (3 + 9 * wild) + ch * 1.7) * (0.6 + 0.4 * math.sin(t * 13 * wild + ch))))
        return f

    # ------------------------------------------------------------------ plate helpers
    def kid(self, fr, t):
        SH.draw(fr, KID_HEAD[0], KID_HEAD[1], t, s=0.72, cap=False, face='sleep', facing=-1)

    def eeg(self, fr, t, wild=0.0):
        """pens scribbling on the paper roll of the EEG machine (plate coordinates)."""
        x0, x1, y0, y1 = 33, 65, 64, 87
        yc = (y0 + y1) / 2; prev = None
        for x in range(x0, x1):
            ph = (x - x0) * 0.5 - t * (6 + 20 * wild)
            amp = 2.0 + 9.0 * wild
            y = yc + amp * math.sin(ph) * (0.6 + 0.4 * math.sin(ph * 2.3 + t * 5)) + (2.5 * wild * math.sin(ph * 5.1))
            y = max(y0, min(y1, y))
            if prev: fr.line(prev[0], prev[1], x, y, '#241a14', 0.9)
            prev = (x, y)
        fr.rect(x1, int(prev[1]) - 1, 2, 2, '#c83a2a')

    # ------------------------------------------------------------------ 1. lab + possession
    def f_lab(self, t):
        P = self.pL; fr = P.frame()
        self.kid(fr, t); self.eeg(fr, t, 0.0)
        hit = t >= TL.T_HIT; white = max(0.0, 1 - (t - TL.T_HIT) / 0.12) if hit else 0.0
        top = put_human(fr, ASERINSKY, ASX, ASY, face='focus' if not hit else ('surprised' if t < TL.T_HIT + 0.8 else 'normal'), look_dir=(2, 0), white=white)
        if hit and t > TL.T_HIT + 0.15: nightcap(fr, ASX, top[1] + 2, t)
        p = None; head = None
        if t < TL.T_POSSESS:
            gx = lerp(-20, 130, eo3((t - 0.6) / 1.8))
            p, head = self.ghost_at(fr, t, self.act_in, gx, 64 + 3 * math.sin(t * 2.4))
        else:
            ghost_dive(fr, t, TL.T_POSSESS, (130, 64), (ASX, top[1] + 14), 0.45, look=(2, 0))
        L = P.light(fr, key=KEY_LAB)
        if hit: L = L + fr.band(ASX, top[1] + 14, 30, 30, (0.7, 0.9, 1.0), [(1.0, 0.5 * white), (0.5, white)])
        k = smooth((t - TL.T_HIT) / 1.6)
        c = pcam(logz(1.0, 1.7, k), lerp(160, ASX - 6, k), lerp(90, 108, k), sx=10 * white * math.sin(t * 90))
        img = fr.render(c, L, GRADE_LAB, frame=self.fi(t))
        img = img + (1 - img) * (1 - smooth(t / 0.5))
        cv = self.hud(t)
        if p is not None: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if hit and t < TL.T_HIT + 0.5:
            ux, uy = c.w2ui(ASX, top[1] + 14, 4); d = t - TL.T_HIT
            G.burst_lines(cv, ux, uy, 20 + 160 * d, 34 + 200 * d, 16, C('#bfe8ff'), 1 - d / 0.5)
        G.char_card(cv, t, TL.T_CARD, '阿瑟林斯基', 'LV.31', '半夜盯梢', '1953 · 芝加哥大学 · 穷研究生', x=12, y=146, life=3.6)
        if TL.T_CARD + 0.7 < t < TL.T_CARD + 3.6:
            a = clamp01((t - TL.T_CARD - 0.7) / 0.2)
            G._panel(cv, 12, 204, 200, 20, a); cv.text(18, 207, '装备：二手脑电仪（耐久 3%）', (255, 200, 140, int(255 * a)), 'zh10')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 2. leaning in ... "this is science" freeze
    def f_lean(self, t):
        P = self.pL; fr = P.frame()
        self.kid(fr, t)
        u = smooth((t - TL.S_LEAN) / 1.0)
        x = lerp(214, 232, u)
        top = put_human(fr, ASERINSKY, x, 142, face='focus', look_dir=(2, 1), tilt=-10 * u)
        nightcap(fr, x, top[1] + 2, t)
        frozen = t >= TL.T_FREEZE
        L = P.light(fr, key=KEY_LAB) + fr.band(x + 10, top[1] + 30, 26, 18, (1.0, 0.85, 0.6), [(1.0, 0.2), (0.5, 0.35)])
        c = pcam(2.5, 258, 96)
        img = fr.render(c, L, GRADE_LAB, frame=self.fi(t), desat=(0.6 if frozen else 0))
        cv = self.hud(t)
        if frozen: ui.rubber_stamp(cv, 150, 110, '科研', t - TL.T_FREEZE, fname='zh12', scale=2, angle=-8)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 3. "the brain switches off"?  a power icon over the sleeping head
    def f_off(self, t):
        P = self.pL; fr = P.frame()
        self.kid(fr, t)
        k = back_out(clamp01((t - TL.S_OFF - 0.3) / 0.3), 1.8)
        if k > 0:
            cx, cy, r = KID_HEAD[0] - 4, KID_HEAD[1] - 17, 9 * k
            ring = fr.M_ell(cx, cy, r, r) & ~fr.M_ell(cx, cy, r - 2, r - 2) & ~fr.M_rect(cx - 2, cy - r - 1, 4, r)
            off = t >= TL.T_OFF
            col = '#ff5a4a' if off else '#9ab0d8'
            fr.fill(ring, col, 0.9); fr.rect(cx - 1, cy - r - 1, 2, r, col, 0.9)
        L = P.light(fr, key=KEY_LAB)
        if k > 0 and t >= TL.T_OFF: L = L + fr.band(KID_HEAD[0] - 4, KID_HEAD[1] - 17, 22, 18, (1.0, 0.3, 0.25), [(1.0, 0.2)])
        c = pcam(2.9, 266, 66)
        img = fr.render(c, L, GRADE_LAB, frame=self.fi(t))
        cv = self.hud(t)
        if t >= TL.T_OFF:
            a = clamp01((t - TL.T_OFF) / 0.2)
            G._panel(cv, 150, 150, 180, 28, a, accent=C('#ff5a4a'))
            cv.text(162, 154, '大脑：已关机？', (255, 208, 200, int(255 * a)), 'zh12')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 4. eyelid ECU: the eyeball darts underneath
    def f_eye(self, t):
        s = Stage(320, 180)
        sk = ['#7a4a3a', '#a8684e', '#c88a6a', '#e0a888', '#f0c4a4']
        s.img[..., :3] = (232, 180, 148)
        s.fill(s.M_ell(160, 100, 200, 100), sk[3])
        lid = s.M_ell(160, 96, 110, 40)
        s.fill(lid, sk[4])
        # the eyeball bulge under the lid
        rem = t >= TL.T_SCAN0
        bx = 160 + (55 * math.sin((t - TL.T_SCAN0) * 14) * min(1, (t - TL.T_SCAN0) * 2) if rem else 0)
        s.fill(lid & s.M_ell(bx, 92, 36, 26), '#ffd8bc'); s.fill(lid & s.M_ell(bx - 8, 84, 14, 8), '#fff0dc')
        s.fill(lid & ~s.M_ell(160, 92, 104, 34), sk[2])
        # lash line + lashes (closed)
        for x in range(56, 266):
            y = 128 + 10 * math.sin(math.pi * (x - 56) / 210) - 10
            s.px(x, y, '#3a1e18'); s.px(x, y + 1, '#3a1e18')
            if x % 6 == 0: s.line(x, y + 1, x - 2 + (x - 160) * 0.03, y + 9, '#2a1410')
        s.fill(s.M_ell(160, 150, 120, 14) & ~s.M_ell(160, 142, 124, 14), sk[2])
        if rem:
            for k in range(3):
                d = 1 if math.cos((t - TL.T_SCAN0) * 14) > 0 else -1
                s.line(bx - d * (44 + k * 8), 70 + k * 12, bx - d * (60 + k * 8), 70 + k * 12, '#ffffff', 0.6)
        L = s.light_base((0.62, 0.6, 0.8), 0.95) + s.band(160, 100, 160, 90, (1.0, 0.82, 0.6), [(1.0, 0.18), (0.5, 0.3)])
        img = s.render(pcam(1.0 + 0.05 * smooth((t - TL.S_EYE) / 2.5)), L, GRADE_LAB, frame=self.fi(t))
        return self.compose(img, self.hud(t))

    # ------------------------------------------------------------------ 5. the EEG paper goes wild
    def f_eeg(self, t):
        P = self.pL; fr = P.frame()
        wild = smooth((t - TL.T_WILD) / 0.25)
        self.eeg(fr, t, wild)
        L = P.light(fr, key=KEY_LAB) + fr.band(48, 76, 30, 22, (1.0, 0.95, 0.85), [(1.0, 0.25), (0.5, 0.4)])
        sh = 5 * wild * math.sin(t * 70)
        far = t >= TL.T_WILD + 1.2
        c = pcam(lerp(3.4, 2.0, smooth((t - TL.T_WILD - 1.2) / 0.5)) if far else 3.4, lerp(50, 70, smooth((t - TL.T_WILD - 1.2) / 0.5)) if far else 50, 76, sx=sh)
        img = fr.render(c, L, GRADE_LAB, frame=self.fi(t))
        cv = self.hud(t)
        if wild > 0.5 and int(t * 8) % 2 == 0: G.big_zh(cv, '!!', 400, 90, 3, C('#ff5a4a'))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 6. "broken?" tap + smoke -> hidden level discovered
    def f_disc(self, t):
        P = self.pL; fr = P.frame()
        self.kid(fr, t); self.eeg(fr, t, 1.0 if t < TL.T_BANNER else 0.4)
        smoke = clamp01((t - TL.T_SMOKE) / 0.8) * (1 - clamp01((t - TL.T_BANNER) / 0.6))
        if smoke > 0:
            for i in range(7):
                ph = (t * 0.7 + i / 7) % 1
                fr.ell(30 + 8 * math.sin(t * 2 + i) + i * 2, 40 - ph * 34, 3 + 4 * ph, 3 + 4 * ph, (150, 150, 160), 0.0)
        tap = TL.T_TAP <= t < TL.T_TAP + 0.5 and int((t - TL.T_TAP) * 8) % 2 == 0
        face = 'surprised' if t < TL.T_BANNER else 'smile'
        top = put_human(fr, ASERINSKY, 96, 144, face=face, arms='up' if tap else 'rest', look_dir=(-2, 0) if t < TL.T_BANNER else (0, 0))
        nightcap(fr, 96, top[1] + 2, t)
        frozen = t >= TL.T_BANNER
        L = P.light(fr, key=KEY_LAB)
        c = pcam(1.7, 92, 100, sx=(7 * math.sin(t * 80) if tap else 0))
        img = fr.render(c, L, GRADE_LAB, frame=self.fi(t), desat=0.35 if frozen else 0)
        cv = self.hud(t)
        if TL.T_TAP <= t < TL.T_BANNER:
            a = clamp01((t - TL.T_TAP) / 0.2)
            ux, uy = c.w2ui(96, top[1], 4)
            ui.speech_bubble(cv, ux + 20, uy + 6, '坏了？', t - TL.T_TAP, life=TL.T_BANNER - TL.T_TAP, side=1, with_coin=False, t=t)
        ui.chapter_banner(cv, t, '发现隐藏关卡', 'HIDDEN LEVEL · REM', TL.T_BANNER, TL.T_BANNER + 2.6, y=24, w=300)
        if frozen and TL.T_BANNER < t < TL.T_BANNER + 0.5:
            d = t - TL.T_BANNER; G.burst_lines(cv, 240, 48, 60 + 300 * d, 80 + 360 * d, 18, C('#ffe27a'), 1 - d / 0.5)
        if frozen and t >= TL.T_BANNER + 0.6:
            a = clamp01((t - TL.T_BANNER - 0.6) / 0.25)
            G._panel(cv, 150, 92, 180, 26, a, accent=C('#c8a0ff'))
            cv.text(162, 97, '快速眼动期 REM', (230, 210, 255, int(255 * a)), 'zh12')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 7. into the kid's ear -> the tower (GPT plate)
    def ghost_at(self, fr, t, act, x, y, scale=1.0, alpha=1.0):
        p = act.at(t)
        rgba, E, ax, ay = A.ghost_sprite(p, t, alpha=alpha)
        if abs(scale - 1) > 0.02: rgba = scale_nearest(rgba, scale); E = scale_nearest(E, scale)
        gx, gy = x + p['dx'] * scale, y + p['dy'] * scale
        fr.sprite(rgba, gx - ax * scale, gy - ay * scale, E=E)
        return p, (gx, gy - 24 * scale)

    def shadow(self, fr, x, y, w):
        fr.mul(fr.M_ell(x, y, w, max(1.2, w * 0.28)), 0.5)

    def tower(self, t, sign='夜班中', glow_t=None, sleep=0.0):
        P = self.pA; fr = P.frame()
        fr.rect(145, 75, 34, 11, '#1a0a1a')
        tw = G.text_width(sign, 'zh10')
        blink = 1.0 if int(t * 7) % 9 else 0.4
        fr.text(162 - tw // 2, 73, sign, '#ff8ac0', 'zh10', 1.0 * blink)
        L = P.light(fr) * P.flicker(fr, t, seed=2, amp=0.12)[..., None]
        win = (P.E > 0.3) & (fr.yy > 30) & (fr.yy < 140) & (fr.xx > 80) & (fr.xx < 240)
        k = np.ones((180, 320), np.float32)
        if glow_t is not None:
            sweep = 140 - 130 * smooth((t - glow_t) / 0.7)
            k = np.where(win & (fr.yy < sweep), 0.35, 1.0).astype(np.float32)
        if sleep > 0:
            rng = np.random.default_rng(5); off = rng.random((180, 320)) < 0.75
            k = np.where(win & off, 1 - 0.65 * sleep, k).astype(np.float32)
        dome = (fr.yy < 40) & (fr.xx > 112) & (fr.xx < 208)
        k = np.where(dome, k * (1 + (0.22 if sleep == 0 else 0.1) * math.sin(t * (3.2 if sleep == 0 else 1.2))), k)
        return fr, L * k[..., None]

    def f_into(self, t):
        if t < TL.T_TOWER:
            P = self.pL; fr = P.frame()
            self.kid(fr, t); self.eeg(fr, t, 0.5)
            k = smooth((t - TL.T_EXIT_GHOST) / (TL.T_EAR - TL.T_EXIT_GHOST))
            gx, gy = lerp(200, KID_HEAD[0] + 2, k), lerp(70, KID_HEAD[1] + 2, k) - 14 * math.sin(math.pi * k)
            put_ghost(fr, t, gx, gy, face='determined', look=(2, 1), scale=lerp(0.9, 0.22, k))
            L = P.light(fr, key=KEY_LAB)
            kk = smooth((t - TL.S_INTO) / 1.5)
            c = pcam(logz(1.6, 4.2, kk), lerp(230, KID_HEAD[0], kk), lerp(90, KID_HEAD[1] + 4, kk))
            img = fr.render(c, L, GRADE_LAB, frame=self.fi(t))
            img = img * (1 - smooth((t - TL.T_EAR) / 0.4))
            return self.compose(img, self.hud(t))
        fr, L = self.tower(t, '夜班中', glow_t=TL.T_GLOW)
        # the ghost, tiny, flies down to the front door
        u = smooth((t - TL.T_TOWER - 0.3) / 2.4)
        gx, gy = lerp(120, 159, u), lerp(40, 122, u) - 10 * math.sin(math.pi * u)
        if t < TL.S_ARCH - 0.25:
            p, _ = self.ghost_at(fr, t, self.act_tower, gx, gy, scale=lerp(0.7, 0.35, u))
        k = eo3((t - TL.T_TOWER) / 1.8)
        c = pcam(logz(3.0, 1.04, k), lerp(160, 160, k), lerp(28, 92, k))
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t))
        img = img + (1 - img) * smooth((t - TL.S_ARCH + 0.25) / 0.25) * 0.9      # into the door: white
        cv = self.hud(t)
        if t >= TL.T_GLOW:
            d = t - TL.T_GLOW
            if d < 0.5: G.burst_lines(cv, 240, 60, 60 + 200 * d, 80 + 260 * d, 18, C('#ffe27a'), 1 - d / 0.5)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 8. archive: memories get filed (and one is PERMANENT)
    def f_arch(self, t):
        P = self.pB; fr = P.frame()
        u = (t - TL.S_ARCH) / (TL.S_EMO - TL.S_ARCH)
        L = P.light(fr) * P.flicker(fr, t, seed=4, amp=0.1)[..., None]
        # cards flying from the cart into the drawers
        wx = lerp(176, 150, smooth(u)); wy = lerp(122, 168, smooth(u)); ws = lerp(0.7, 1.7, smooth(u))
        rng = np.random.default_rng(7)
        drawers = [(30, 40), (52, 72), (18, 98), (60, 30), (290, 40), (300, 70), (282, 100), (40, 60), (305, 20)]
        for i in range(14):
            t0 = TL.S_ARCH + 0.15 + i * 0.22
            a = (t - t0) / 0.55
            if 0 <= a < 1:
                dx, dy = drawers[i % len(drawers)]
                sx, sy = wx + 8 * ws, wy - 12 * ws
                x = lerp(sx, dx, a); y = lerp(sy, dy, a) - 30 * math.sin(math.pi * a)
                fr.rect(x - 1, y - 1, 3, 2, (255, 230, 150), 1.0)
            if 1 <= a < 1.35:                                          # the drawer flashes as it takes the card
                dx, dy = drawers[i % len(drawers)]
                fr.fill(fr.M_rect(dx - 4, dy - 2, 9, 5), (255, 220, 140), 0.9)
        self.shadow(fr, wx, wy, 9 * ws)
        W.draw(fr, wx, wy, t, prop='cart', walk=True, scale=ws, face='happy', dir=1)
        # a clerk on the ladder, filing
        lad = int((t * 3) % 2)
        self.shadow(fr, 98, 128, 6)
        W.draw(fr, 100, 84 + lad, t, prop='card' if lad else None, scale=0.9, face='happy', dir=-1)
        p, head = self.ghost_at(fr, t, self.act_arch, 62, 74, scale=0.95)
        z = lerp(1.22, 1.38, smooth(u)); c = pcam(z, 166, 104)
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t)
        A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        # the embarrassing memory card
        if t >= TL.T_CARD_UP:
            d = t - TL.T_CARD_UP
            out = clamp01((t - TL.T_CARD_STAMP - 0.55) / 0.3)
            k = back_out(clamp01(d / 0.25), 1.6)
            sc = (1 - out)
            cxu, cyu = lerp(240, 60, out), lerp(118, 60, out)
            w, h = int(150 * k * max(sc, 0.15)), int(64 * k * max(sc, 0.15))
            if w > 6:
                x0, y0 = int(cxu - w / 2), int(cyu - h / 2)
                cv.rect(x0 + 2, y0 + 3, w, h, (0, 0, 0, 110)); cv.rect(x0, y0, w, h, (246, 238, 214, 255)); cv.rect(x0, y0, w, 3, (232, 170, 60, 255))
                if sc > 0.8 and k > 0.9:
                    cv.text(x0 + 8, y0 + 8, '今日记忆 #0347', (120, 100, 80, 255), 'zh8')
                    cv.text(x0 + 8, y0 + 22, '开会时把老板叫成了妈', (40, 30, 30, 255), 'zh10')
                    cv.text(x0 + 8, y0 + 40, '尴尬指数 ★★★★★', (200, 80, 60, 255), 'zh8')
                    if t >= TL.T_CARD_STAMP:
                        ui.rubber_stamp(cv, x0 + w - 34, y0 + h - 18, '永久保存', t - TL.T_CARD_STAMP, fname='zh10', scale=1, angle=-6)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 9. emotion dept: the anxiety goes in the dryer, comes out folded
    def f_emo(self, t):
        P = self.pC; fr = P.frame()
        cxd, cyd, rxd, ryd = 281, 72, 22, 29
        drum = fr.M_ell(cxd, cyd, rxd, ryd)
        popped = t >= TL.T_POP
        if not popped:                                    # tumbling storm
            ang = (t - TL.S_EMO) * 140
            M = cv2.getRotationMatrix2D((cxd, cyd), ang, 1.0)
            rot = cv2.warpAffine(P.rgb, M, (320, 180), flags=cv2.INTER_NEAREST)
            fr.img[drum, :3] = rot[drum]
            if int(t * 10) % 7 == 0:
                fr.fill(drum & fr.M_poly([(cxd - 4, cyd - 20), (cxd + 3, cyd - 2), (cxd - 2, cyd - 1), (cxd + 5, cyd + 18), (cxd - 6, cyd + 2), (cxd, cyd + 1)]), (240, 220, 255), 1.0)
        else:                                             # empty drum, just a warm glow
            fr.fill(drum, (40, 34, 44)); fr.fill(drum & fr.M_ell(cxd, cyd + 12, rxd - 4, 10), (70, 60, 70))
        L = P.light(fr) * P.flicker(fr, t, seed=9, amp=0.08)[..., None]
        if not popped:
            L = L + fr.band(cxd, cyd, 40, 44, (0.55, 0.35, 0.9), [(1.0, 0.10 + 0.1 * (int(t * 10) % 7 == 0))])
        # the clerk
        wx, wy = 236, 140
        self.shadow(fr, wx, wy, 11)
        hop = 3 * abs(math.sin((t - TL.T_TOWEL) * 9)) if TL.T_TOWEL <= t < TL.T_TOWEL + 0.7 else 0
        face = 'sweat' if t < TL.T_POP else ('wow' if t < TL.T_TOWEL else 'happy')
        W.draw(fr, wx, wy - hop, t, prop='towel' if t >= TL.T_TOWEL else None, scale=1.5, face=face, dir=1)
        # the storm cloud escapes, shrinks, is caught as a folded towel
        if TL.T_POP <= t < TL.T_TOWEL:
            a = (t - TL.T_POP) / (TL.T_TOWEL - TL.T_POP)
            cx_, cy_ = lerp(cxd, wx + 4, a), lerp(cyd, wy - 22, a) - 16 * math.sin(math.pi * a)
            r = lerp(14, 4, a)
            m = fr.M_ell(cx_, cy_, r, r * 0.7) | fr.M_ell(cx_ - r * 0.7, cy_ + 2, r * 0.6, r * 0.5) | fr.M_ell(cx_ + r * 0.7, cy_ + 2, r * 0.6, r * 0.5)
            fr.part(m, ['#2a1a4a', '#4a2a7a', '#6a4aa8', '#9a7ad8'], bevel=2, amb=0.5, ink='#120a20')
        p, head = self.ghost_at(fr, t, self.act_emo, 172, 86, scale=1.0)
        z = 1.42; c = pcam(z, 226, 92)
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t)
        A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if TL.T_POP <= t < TL.T_POP + 0.5: G.onomatopoeia(cv, '叮！', 420, 70, t - TL.T_POP, 2, C('#ffe27a'), life=0.5)
        if t >= TL.T_TOWEL + 0.15:
            a = clamp01((t - TL.T_TOWEL - 0.15) / 0.2)
            ux, uy = c.w2ui(wx, wy - 40, 4)
            s_ = '焦虑（已烘干·叠好）'
            tw = G.text_width(s_, 'zh10')
            G._panel(cv, int(ux - tw / 2 - 6), int(uy - 20), tw + 12, 16, a)
            cv.text(int(ux - tw / 2), int(uy - 18), s_, (255, 236, 200, int(255 * a)), 'zh10')
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 10. basement: the cleaning crew opens the gate
    def f_base(self, t):
        D1, D2 = self.pD1, self.pD2
        fr = D2.frame() if t >= TL.T_GATE else D1.frame()
        lift = smooth((t - TL.T_GATE) / (TL.T_WAVE - TL.T_GATE + 0.3))
        if t >= TL.T_GATE and lift < 1:                 # the D1 gate slides up, revealing D2's open gate
            off = int(round(lift * 100))
            patch = D1.base[0][22:118, 110:215].copy()
            y0 = 22 - off
            ys = max(22, y0); ye = y0 + 96
            if ye > ys:
                fr.img[ys:ye, 110:215] = patch[ys - y0:ye - y0]
        front = 118 + 64 * smooth((t - TL.T_WAVE + 0.2) / 0.7)     # the wave front rolls toward the camera
        if t < TL.T_WAVE - 0.2:
            fr.img[118:, :] = D1.base[0][118:, :]
        else:
            fy = int(front)
            fr.img[fy:, :] = D1.base[0][fy:, :]
            if fy < 172:
                rng = np.random.default_rng(int(t * 30))
                foam = fr.M_rect(0, fy - 2, 320, 3) & (fr.xx > 60) & (fr.xx < 262) & (rng.random((180, 320)) < 0.6)
                fr.fill(foam, (220, 255, 255), 0.9)
        # moving water (D2 water rows shimmer sideways)
        if t >= TL.T_WAVE - 0.2:
            img = fr.img
            cyan = (img[..., 2].astype(int) > img[..., 0].astype(int) + 40) & (fr.yy > 60)
            for y in range(60, 180, 2):
                sh = int(round(1.5 * math.sin(y * 0.45 + t * 9)))
                if sh:
                    row = img[y].copy(); rolled = np.roll(row, sh, 0)
                    m = cyan[y]
                    img[y][m] = rolled[m]
        # grime (washed away by the wave)
        gr = [(66, 121), (252, 119), (150, 128), (196, 132)]
        for i, (x, y) in enumerate(gr):
            if not (t >= TL.T_WAVE and y < front + 4):
                fr.fill(fr.M_ell(x, y, 4, 2) | fr.M_ell(x + 3, y - 1, 2.5, 1.6), '#4a3a1a'); fr.px(x - 1, y - 1, '#7a6a2a')
        # lever on the left ledge
        lx, ly = 58, 112
        fr.rect(lx - 3, ly - 2, 7, 4, '#3a3a44')
        la = -0.7 if t < TL.T_VALVE else lerp(-0.7, 0.7, smooth((t - TL.T_VALVE) / 0.25))
        fr.line(lx, ly - 1, lx + 12 * math.sin(la), ly - 1 - 12 * math.cos(la), '#c8c8d0'); fr.ell(lx + 12 * math.sin(la), ly - 1 - 12 * math.cos(la), 1.8, 1.8, '#e04030')
        # valve wheels spin while the gate lifts
        if TL.T_GATE <= t < TL.T_WAVE + 0.4:
            for (vx, vy, r) in ((40, 70, 12), (293, 73, 12)):
                m = fr.M_ell(vx, vy, r, r)
                M = cv2.getRotationMatrix2D((vx, vy), (t - TL.T_GATE) * 400, 1.0)
                rot = cv2.warpAffine(np.ascontiguousarray(fr.img[..., :3]), M, (320, 180), flags=cv2.INTER_NEAREST)
                fr.img[m, :3] = rot[m]
        # the cleaning crew
        wx, wy = 74, 118
        hop = 4 * abs(math.sin((t - TL.T_SALUTE) * 10)) if TL.T_SALUTE <= t < TL.T_SALUTE + 0.35 else 0
        if t >= TL.T_CHEER: hop = 5 * abs(math.sin((t - TL.T_CHEER) * 7))
        prop = 'lever' if TL.T_VALVE - 0.1 <= t < TL.T_VALVE + 0.5 else 'mop'
        face = 'happy' if t < TL.T_WAVE or t >= TL.T_CHEER else 'wow'
        self.shadow(fr, wx, wy, 9)
        W.draw(fr, wx - (8 if prop == 'lever' else 0), wy - hop, t, kind='blue', hat='#ff8a2a', prop=prop, scale=1.3, face=face, dir=-1 if prop == 'lever' else 1)
        # the ghost: curious -> startled by the alarm -> double take at the wave -> swept away -> pops back up soaked
        L = D2.light(fr)
        if TL.T_VALVE <= t < TL.T_WAVE + 1.0 and int(t * 4) % 2 == 0:
            L = L + fr.band(162, 18, 70, 30, (1.0, 0.2, 0.15), [(1.0, 0.25), (0.5, 0.4)])
        gx, gy, gs, ga = 168, 86, 1.0, 1.0
        if t >= TL.T_SWEPT:
            a = clamp01((t - TL.T_SWEPT) / 0.9)
            gx, gy, gs = lerp(168, 40, a), lerp(86, 200, a * a), lerp(1.0, 1.9, a)
            if t >= TL.T_SWEPT + 1.6:                        # back up, soaked
                b = clamp01((t - TL.T_SWEPT - 1.6) / 0.4)
                gx, gy, gs = 236, lerp(200, 140, eo3(b)), 1.25
        p = None
        if gy < 215:
            p, head = self.ghost_at(fr, t, self.act_base, gx, gy, scale=gs)
        sh = 0.0
        if TL.T_WAVE - 0.1 <= t < TL.T_SWEPT + 0.9: sh = 3.5 * math.sin(t * 55) * (1 - clamp01((t - TL.T_SWEPT) / 0.9))
        c = pcam(lerp(1.14, 1.06, smooth((t - TL.S_BASE) / 2.5)), 160, 92, sx=sh, sy=sh * 0.5)
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t)
        if p is not None: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if TL.T_GRIME <= t < TL.T_WAVE:
            a = clamp01((t - TL.T_GRIME) / 0.2) * (1 - clamp01((t - TL.T_WAVE + 0.3) / 0.3))
            ux, uy = c.w2ui(150, 128, 4)
            cv.line(int(ux), int(uy - 4), int(ux + 18), int(uy - 30), (255, 220, 140, int(255 * a)))
            G._panel(cv, int(ux + 16), int(uy - 46), 108, 16, a)
            cv.text(int(ux + 22), int(uy - 44), '白天攒下的代谢垃圾', (255, 220, 140, int(255 * a)), 'zh10')
        if TL.T_SWEPT <= t < TL.T_SWEPT + 0.9:
            G.onomatopoeia(cv, '哇啊——', 160, 60, t - TL.T_SWEPT, 3, C('#bfffff'), life=0.9)
        if TL.T_SWEPT + 1.6 <= t:
            ux, uy = c.w2ui(236, 120, 4)
            for i in range(5):                                  # dripping
                d = (t * 1.6 + i * 0.2) % 1
                cv.rect(int(ux - 30 + i * 14), int(uy + 30 + 30 * d), 2, 3, (140, 240, 255, int(255 * (1 - d))))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 11. tower: maintenance mode
    def f_ext2(self, t):
        sign = '维护中' if t >= TL.T_SIGN else '夜班中'
        sl = smooth((t - TL.T_SIGN) / 1.2)
        fr, L = self.tower(t, sign, sleep=sl)
        img = fr.render(pcam(lerp(1.02, 1.22, smooth((t - TL.S_EXT2) / 4.0)), 160, 88), L, GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t)
        if t >= TL.T_SIGN + 0.3:
            a = clamp01((t - TL.T_SIGN - 0.3) / 0.2)
            cv.text(240 - G.text_width('请勿打扰', 'zh10') // 2, 150, '请勿打扰', (160, 230, 255, int(255 * a)), 'zh10', outline=(0, 10, 20, int(255 * a)))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 12. tonight's shift schedule: REM sits in the second half
    def f_sched(self, t):
        s = Stage(320, 180); s.img[..., :3] = (10, 9, 16); s.E[:] = 0
        board = s.rect(14, 22, 292, 120, '#1c1a2c'); s.outline(board, '#c8902e'); s.rect(14, 22, 292, 2, '#e8b04a')
        x0, x1, base = 28, 296, 124
        s.line(x0, base, x1, base, '#8a88a8')
        hours = ['23', '00', '01', '02', '03', '04', '05', '06', '07']
        for i, h in enumerate(hours):
            x = x0 + (x1 - x0) * i / 8; s.line(x, base, x, base + 3, '#8a88a8')
        cyc = (x1 - x0) / 5.3
        strike_x = x0 + (x1 - x0) * 6 / 8
        fall_k = clamp01((t - TL.T_FALL) / 0.8)
        grow = smooth((t - TL.T_SCHED) / 1.8)
        for i in range(5):
            cx0 = x0 + i * cyc
            deep_h = (62 - i * 12) * grow; deep_w = cyc * (0.5 - i * 0.07)
            rem_h = (16 + i * 13) * grow; rem_w = cyc * (0.15 + i * 0.09)
            s.rect(cx0 + 2, base - deep_h, deep_w, deep_h, '#3a5ab8'); s.rect(cx0 + 2, base - deep_h, deep_w, 1, '#7a9ae8')
            rx = cx0 + 4 + deep_w; ry = base - rem_h
            if rx + rem_w > strike_x and fall_k > 0:
                ry += fall_k * fall_k * 80; s.rect(rx, ry, rem_w, rem_h, '#8a4ac8', 0.3)
            else:
                s.rect(rx, ry, rem_w, rem_h, '#b06ae8', 0.4); s.rect(rx, ry, rem_w, 1, '#e0b0ff', 0.6)
        if t >= TL.T_STRIKE:
            k = smooth((t - TL.T_STRIKE) / 0.4)
            s.fill(s.M_rect(strike_x, 30, (x1 - strike_x) * k, 96) & ((s.xx + s.yy) % 4 == 0), '#ff3a3a', 0.4)
            s.line(strike_x, 30, strike_x + (x1 - strike_x) * k, 124 * k + 30 * (1 - k), '#ff4a3a', 0.8)
            s.line(strike_x, 124, strike_x + (x1 - strike_x) * k, 124 - 94 * k, '#ff4a3a', 0.8)
        L = s.light_base((0.85, 0.85, 0.95), 1.0)
        img = s.render(pcam(1.0), L, GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        cv.text(36, 74, '今晚排班表', (255, 226, 160, 255), 'zh12', outline=(20, 10, 0, 255))
        for i, h in enumerate(hours):
            x = (x0 + (x1 - x0) * i / 8) * 1.5
            cv.text(int(x) - 6, 192, h, (180, 176, 210, 255), 'silk')
        cv.text(36, 214, '■ 深睡：清洁队', (122, 154, 232, 255), 'zh10', outline=(0, 0, 0, 255))
        cv.text(170, 214, '■ 快速眼动：整理 + 消化', (200, 150, 255, 255), 'zh10', outline=(0, 0, 0, 255))
        if t >= TL.T_STRIKE:
            cv.text(int(strike_x * 1.5) + 8, 52, '熬夜砍掉', (255, 120, 100, 255), 'zh12', outline=(20, 0, 0, 255))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 12b. back at the 03:56 save point: +20%
    def f_anchor(self, t):
        u = smooth((t - TL.S_ANCHOR) / 1.0)
        gy = lerp(58, 90, u)
        color_k = 0.3 + 0.25 * smooth((t - TL.T_REVIVE) / 0.8)
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

    # ------------------------------------------------------------------ 13. hub: the button peeks out of 1964
    def f_hub(self, t):
        st = ['cleared', 'cleared' if t >= TL.T_CLEAR else 'active', 'active' if t >= TL.T_NEXT else 'locked', 'locked', 'locked']
        op = [0.55, 0.55 * smooth((t - TL.T_CLEAR) / 0.5), eo3((t - TL.T_GO - 0.6) / 0.6), 0, 0]
        fr = self.hub.frame(t, st, (1,) * 5, op)
        d2 = self.hub.D[2]
        k = smooth((t - TL.T_GO) / 1.0)
        gx = lerp(160, d2['x'], k); gy = lerp(140, d2['yb'] - 18, k) + 2 * math.sin(t * 2.4)
        face = 'happy' if t < TL.T_BTN else ('wow' if t < TL.T_BTN + 0.5 else 'determined')
        put_ghost(fr, t, gx, gy, face=face, look=(0, -1) if t > TL.T_BTN else (0, 0), scale=lerp(1, 0.85, k))
        L = self.hub.light(fr, st, (1,) * 5, op) + fr.band(gx, gy, 30, 22, (0.55, 0.75, 1.0), [(1.0, 0.15), (0.5, 0.3)])
        z = logz(1.0, 2.6, smooth((t - TL.T_GO - 0.2) / 1.2)); cx = lerp(160, d2['x'], smooth((t - TL.T_GO) / 1.2)); cy = lerp(98, d2['yb'] - 28, smooth((t - TL.T_GO) / 1.2))
        c = pcam(z, cx, cy)
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t), air=self.hub.air(fr, st, (1,) * 5, op))
        img = img + (1 - img) * smooth((t - TL.END + 0.4) / 0.4)
        cv = self.hud(t, loc=False, pips=True)
        if TL.T_BTN <= t < TL.T_GO + 0.3:
            q = back_out(clamp01((t - TL.T_BTN) / 0.25), 2.2)
            bx, by = c.w2ui(d2['x'] + d2['w'] * 0.5, d2['yb'] - d2['h'] * 0.6, 4)
            G.game_button(cv, int(bx + 4 - 20 * (1 - q)), int(by), 116, 20, '我还能再熬会儿', 'hover', C('#b04050'), min(1, q), 'zh10',
                          sweat=False)
            cv.text(int(bx + 124), int(by - 10), '嘿嘿', (255, 200, 200, int(255 * min(1, q))), 'zh10', outline=(20, 0, 0, 255))
        return self.compose(img, cv)

    def frame(self, t):
        img = self.ed.frame(min(t, TL.END - 1e-3))
        return ui_over(img, subs_layer(t, TL.L, TL.HL).a, scale=5)

def make(**kw): return Level2(**kw)
