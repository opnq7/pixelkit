"""开场 v2 · 再刷十分钟：Opening().frame(t) -> float RGB (1080, 1920, 3)。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s0_open'))
import numpy as np, cv2
import timeline as TL
from common import subs_layer, ramp, lerp, smooth, FPS
from pixelkit import ui, gameui as G
from pixelkit.core import C
from pixelkit.edit import Edit
from pixelkit.scene import ui_over
from pixelkit.pixstage import Stage, cam as pcam
from pixelkit.sets.bedroom_night import BedroomNight, GRADE_BED
from pixelkit.sets.bedroom320 import SLEEPER
from pixelkit.sets.phone_feed import PhoneFeed, CLIPS
from pixelkit.sets.hub_doors import HubDoors
from pixelkit.characters import ghost, human, face_cu as FC
from pixelkit.anim import back_out, clamp01
from pixelkit import perform as P

def eo3(u): u = clamp01(u); return 1 - (1 - u) ** 3
def ei2(u): u = clamp01(u); return u * u
def logz(a, b, k): return math.exp(math.log(a) + (math.log(b) - math.log(a)) * k)
def UI(): return ui.UICanvas()

class Opening:
    def __init__(self):
        self.b = BedroomNight(); self.pf = PhoneFeed(); self.hub = HubDoors()
        self.face_st = self._face_set()
        self.ed = Edit()
        self.ed.add('feed1', TL.S_FEED1, self.f_feed)
        self.ed.add('face1', TL.S_FACE1, self.f_face, 'cut')
        self.ed.add('wide', TL.S_WIDE, self.f_wide, 'cut')
        self.ed.add('feed2', TL.S_FEED2, self.f_feed, 'cut')
        self.ed.add('face2', TL.S_FACE2, self.f_face, 'cut')
        self.ed.add('feed3', TL.S_FEED3, self.f_feed, 'cut')
        self.ed.add('face3', TL.S_FACE3, self.f_face, 'cut')
        self.ed.add('smack', TL.S_SMACK, self.f_smack, 'cut')
        self.ed.add('over', TL.S_OVER, self.f_over, 'cut')
        self.ed.add('ghost', TL.S_GHOST, self.f_ghost, 'fade', 0.35)
        self.ed.add('quest', TL.S_QUEST, self.f_quest, 'cut')
        self.ed.add('hub', TL.S_HUB, self.f_hub, 'flash', 0.36)
        self.ed.end(TL.END)
        self._over_bg = None
        self.portraits = {f: human.draw(SLEEPER, face=f).body.cv.a[2:36, 9:47].copy() for f in ('tired', 'closed', 'surprised', 'smile')}

    def fi(self, t): return int(round(t * FPS))

    # ================================================================ shared HUD layer (status bar + quest tracker)
    def hud(self, cv, t, show=True):
        if not show or t < TL.T_HUD or t >= TL.S_OVER: return
        k = clamp01((t - TL.T_HUD) / 0.35)
        dead = t >= TL.T_FLAT
        face = 'tired'
        if TL.S_FACE2 + 0.2 < t < TL.T_JERK or t > TL.S_FACE3: face = 'closed'
        if TL.T_JERK <= t < TL.T_JERK + 0.4: face = 'surprised'
        if TL.T_SMIRK0 <= t < TL.T_SMIRK1: face = 'smile'
        bpm = 74 if t < TL.S_WIDE else (96 if t < TL.S_FEED2 else (124 if t < TL.S_FACE3 else 150))
        hit = max(0.0, 1 - (t - TL.T_HIT) / 0.5) if t >= TL.T_HIT else 0.0
        G.player_hud(cv, 8, 8, t, hp=TL.hp(t), bpm=bpm, beats=TL.BEATS, flat_t=TL.T_FLAT, portrait=self.portraits[face],
                     name='你', lv='LV.25', title='夜猫子', k=k, hit=hit, dead=dead)
        if t >= TL.T_TASK:
            kt = clamp01((t - TL.T_TASK) / 0.35)
            failed = clamp01((t - TL.T_FAIL) / 0.25) if t >= TL.T_FAIL else 0.0
            G.task_tracker(cv, 472, 8, t, '再刷 10 分钟就睡', TL.remain(t), 600, k=kt, failed=failed)
            if TL.T_TASK <= t < TL.T_TASK + 0.4:
                d = t - TL.T_TASK
                G.burst_lines(cv, 400, 28, 40 + 80 * d, 50 + 110 * d, 12, C('#ffe27a'), 1 - d / 0.4)
            # videos watched counter (escalates)
            if t >= TL.S_WIDE:
                n = int(round(137 * (600 - TL.remain(t)) / 548)); n = max(1, min(137, n))
                s = f'已刷 {n} 条'
                bump = any(0 <= t - ts < 0.12 for ts in TL.SWIPES)
                w = G.text_width(s, 'zh10') + 12
                G._panel(cv, 472 - w, 54, w, 16, 1.0)
                cv.text(472 - w + 6, 56 - (1 if bump else 0), s, (255, 226, 120, 255) if bump else (240, 232, 214, 255), 'zh10')

    # ================================================================ phone feed POV
    def f_feed(self, t):
        sh = self.ed.shot_at(t)
        tilt = 0.0; sx = sy = 0.0; z = 1.0; dim = 0.0
        if sh == 'feed1':
            z = lerp(1.0, 1.05, smooth(t / 1.7))
        elif sh == 'feed2':
            z = 1.04
            for ts in TL.SWIPES:
                if 0 <= t - ts < 0.12: sx = 3 * math.sin((t - ts) * 80)
        elif sh == 'feed3':
            u = clamp01((t - TL.T_LOOSE) / (TL.S_FACE3 - TL.T_LOOSE))
            z = 1.04 + 0.06 * u; sx = 10 * ei2(u); sy = 16 * ei2(u); dim = 0.25 * u
        fr = self.pf.frame(t, TL.SWIPES, CLIPS, clock=TL.clock(t)[:2] + ':' + TL.clock(t)[2:], battery=100, tilt=tilt, dim=dim)
        L = self.pf.light(fr)
        c = pcam(z, 160 - sx / z, 90 - sy / z)
        img = fr.render(c, L, GRADE_BED, frame=self.fi(t))
        if sh == 'feed3':          # the grip loosens: the phone view rolls a few degrees
            ang = 7 * ei2(clamp01((t - TL.T_LOOSE) / (TL.S_FACE3 - TL.T_LOOSE)))
            M = cv2.getRotationMatrix2D((960, 540), ang, 1.0)
            img = cv2.warpAffine(img, M, (1920, 1080), flags=cv2.INTER_NEAREST, borderValue=(0, 0, 0))
        cv = UI()
        if sh == 'feed1' and t >= TL.T_CLOCK_POP:
            a = t - TL.T_CLOCK_POP
            sc = 5 + int(round(2 * max(0, 1 - a / 0.10)))
            G.pixel_word(cv, '03:47', 90, 92, sc - 1, C('#ffd34a'), C('#6a3a0a'), C('#fff2b0'), alpha=min(1, a / 0.05), depth=3)
            if a > 0.12:
                al = min(1, (a - 0.12) / 0.1)
                cv.text(58, 116, '凌晨', (220, 210, 240, int(255 * al)), 'zh12', outline=(10, 6, 20, int(255 * al)))
                cv.text(88, 119, 'AM', (160, 150, 190, int(255 * al)), 'silkb')
        self.hud(cv, t)
        return ui_over(img, cv.a, scale=4)

    # ================================================================ face CU (front-camera POV)
    def _face_set(self):
        s = Stage(320, 180)
        s.rect(0, 0, 320, 180, '#5a5678')
        pil = s.M_ell(160, 92, 168, 76)
        s.part(pil, ['#3a3656', '#5a5678', '#7a7698', '#a8a4c4', '#c8c4dc'], bevel=26, light=(0.1, -0.7, 0.7), amb=0.35, outline=None)
        for (a, b) in (((20, 60), (70, 76)), ((250, 70), (300, 54)), ((40, 130), (90, 120)), ((240, 124), (296, 136))):
            s.line(a[0], a[1], b[0], b[1], '#4a4668', mask=pil)
        # blanket + hoodie collar along the bottom
        bl = s.M_poly([(0, 160), (90, 150), (160, 156), (230, 150), (320, 158), (320, 180), (0, 180)])
        s.part(bl, ['#141a3a', '#1e2a5a', '#2a3a7a', '#3a4e98'], bevel=5, amb=0.4, ink='#07060e')
        col = s.M_ell(160, 168, 46, 14)
        s.part(col, ['#22305a', '#33457a', '#4a5e9a', '#6a7eb8'], bevel=5, amb=0.35, ink='#07060e')
        return s.snapshot()

    def face_params(self, t):
        sh = self.ed.shot_at(t)
        p = dict(lid=0.32, look=(0, 0), pupil=1.0, red=0.35, bags=0.75, mouth='flat', tilt=0.0, dy=0.0, sweat=0.0, brow=0.0)
        # eyes follow each new video up, then settle
        for ts in TL.SWIPES:
            d = t - ts
            if 0 <= d < 0.35: p['look'] = (0, -3 * (1 - d / 0.35))
        p['look'] = (p['look'][0] + 0.6 * math.sin(t * 1.7), p['look'][1])
        if sh == 'face1':
            if TL.T_SMIRK0 <= t < TL.T_SMIRK1:
                k = min(clamp01((t - TL.T_SMIRK0) / 0.12), 1 - clamp01((t - TL.T_SMIRK1 + 0.15) / 0.15))
                p.update(mouth='smile' if k > 0.5 else 'flat', lid=lerp(0.32, 0.5, k), brow=-0.6 * k, tilt=-4 * k)
            for bt in (2.35, 4.05):
                if 0 <= t - bt < 0.16: p['lid'] = 1.0 if t - bt < 0.08 else 0.7
        elif sh == 'face2':
            p.update(red=0.8, bags=1.0)
            if t < TL.T_JERK:
                k = smooth((t - TL.S_FACE2) / (TL.T_JERK - TL.S_FACE2))
                p.update(lid=lerp(0.55, 0.97, k), dy=6 * k, tilt=5 * k, mouth='flat')
            elif t < TL.T_JERK + 0.40:
                d = t - TL.T_JERK
                p.update(lid=-0.3, pupil=0.6, brow=1.0, sweat=clamp01(d / 0.15), mouth='o', dy=-2 + P.wobble(t, TL.T_JERK, 2.5, 6, 6))
            else:
                k = smooth((t - TL.T_JERK - 0.40) / (TL.S_FEED3 - TL.T_JERK - 0.40))
                p.update(lid=lerp(0.45, 0.8, k), dy=2 * k, sweat=1 - k, brow=0.5 * (1 - k))
        elif sh == 'face3':
            p.update(lid=1.0, mouth='drool', tilt=7, dy=5, red=0.8, bags=1.0)
        return p

    def f_face(self, t):
        sh = self.ed.shot_at(t)
        fp = self.face_params(t)
        name = CLIPS[int(math.floor(self.pf.scroll(t, TL.SWIPES))) % len(CLIPS)]
        spr = FC.sleeper_face(reflect=self.pf.clip_thumb(name), **fp)
        s = self.b.st.from_snapshot(self.face_st)
        s.sprite(spr.cv.a, 160 - spr.ax, 88 - spr.ay, E=spr.E)
        scol = np.array(self.pf.screen_color(t, TL.SWIPES), np.float32) / 255.0
        scol = 0.45 * scol + 0.55 * np.array([0.55, 0.78, 1.0], np.float32)
        dim = 0.0
        if sh == 'face3': dim = clamp01((t - TL.S_FACE3) / 0.5) * 0.3
        k = 1.0 - dim
        L = s.light_base((0.55, 0.52, 0.8), 0.32)
        L = L + s.band(160, 40, 190, 150, tuple(scol), [(1.0, 0.16 * k), (0.66, 0.36 * k), (0.40, 0.62 * k), (0.22, 0.8 * k)])
        L = L + s.band(330, 110, 90, 90, (1.0, 0.6, 0.3), [(1.0, 0.12), (0.5, 0.2)])         # bedside lamp from the right
        z, cx, cy, sx, sy = 1.18, 160, 92, 0.0, 0.0
        sx = 1.2 * math.sin(t * 2.1); sy = 1.0 * math.sin(t * 1.6 + 1)        # handheld
        for ts in TL.SWIPES:
            if 0 <= t - ts < 0.1: sy += 2 * math.sin((t - ts) * 60)
        if sh == 'face2' and TL.T_JERK <= t < TL.T_JERK + 0.3:
            sx += 6 * math.sin((t - TL.T_JERK) * 70) * (1 - (t - TL.T_JERK) / 0.3)
        if sh == 'face1': z = lerp(1.15, 1.24, smooth((t - TL.S_FACE1) / 2.8))
        if sh == 'face3':
            u = clamp01((t - TL.T_SLIP) / (TL.S_SMACK - TL.T_SLIP))
            z = logz(1.22, 4.0, ei2(u)); cy = lerp(92, 100, u); sx += 8 * ei2(u)
        img = s.render(pcam(z, cx + sx, cy + sy), L, GRADE_BED, frame=self.fi(t))
        if sh == 'face3':
            u = clamp01((t - TL.T_SLIP) / (TL.S_SMACK - TL.T_SLIP))
            img = img * (1 - 0.85 * u ** 3)
        cv = UI()
        if sh == 'face2' and TL.T_JERK <= t < TL.T_JERK + 0.5:
            G.onomatopoeia(cv, '!', 330, 70, t - TL.T_JERK, 3, C('#ffffff'), life=0.5)
        if sh == 'face2' and t < TL.T_JERK:
            u = (t - TL.S_FACE2) / (TL.T_JERK - TL.S_FACE2)
            if u > 0.35:
                for i in range(2):
                    zt = (t * 1.2 + i * 0.5) % 1
                    cv.text(int(330 + 20 * zt), int(90 - 40 * zt), 'z', (200, 210, 255, int(255 * (1 - zt))), 'p2p')
        self.hud(cv, t)
        return ui_over(img, cv.a, scale=4)

    # ================================================================ wide: the room (time-lapse)
    def room_light(self, fr, t, phone_k=1.0, room=1.0, lamp=1.0, phone_xy=None):
        scol = np.array(self.pf.screen_color(t, TL.SWIPES), np.float32) / 255.0
        scol = tuple(0.5 * scol + 0.5 * np.array([0.5, 0.78, 1.0]))
        return self.b.light(fr, phone_k=phone_k, lamp_k=lamp, room_k=room, screen_col=scol, phone_xy=phone_xy)

    def f_wide(self, t):
        u = (t - TL.S_WIDE)
        jit = 0.0
        for ts in TL.SWIPES:
            if 0 <= t - ts < 0.12: jit = -1.0
        px, py = self.b.A['phone']
        scr = tuple(int(v) for v in self.pf.screen_color(t, TL.SWIPES))
        fr = self.b.frame(t, face='tired', look=(0, -2), phone='up', phone_xy=(px, py + jit), clock=TL.clock(t),
                          colon=(int(t * 4) % 2 == 0), cat='curl', screen=scr)
        L = self.room_light(fr, t, phone_xy=(180, 96))
        z = logz(1.0, 1.10, smooth(u / 1.75)); cx = lerp(160, 172, smooth(u / 1.75)); cy = lerp(90, 92, smooth(u / 1.75))
        if u < 0.12: z = z * (1.0 + 0.08 * (1 - u / 0.12))
        img = fr.render(pcam(z, cx, cy), L, GRADE_BED, frame=self.fi(t), air=self.b.air(fr, phone_xy=(px, py)))
        cv = UI()
        if TL.T_FF0 <= t < TL.T_FF1:
            ui.ff_badge(cv, 210, 64, t, alpha=clamp01((t - TL.T_FF0) / 0.15), label='x 32')
        self.hud(cv, t)
        return ui_over(img, cv.a, scale=4)

    # ================================================================ the smack
    def smack_frame(self, t):
        cat = 'curl'
        if t >= TL.T_HIT + 0.05: cat = 'puff' if t < TL.T_HIT + 1.3 else 'up'
        fr = self.b.frame(t, face='closed', phone='smack', clock=TL.clock(t), colon=True, cat=cat, cat_look=(-3, -2),
                          screen=(170, 230, 255), chest=0.0)
        L = self.room_light(fr, t, phone_k=0.55, phone_xy=(182, 104))
        return fr, L

    def f_smack(self, t):
        u = t - TL.S_SMACK
        fr, L = self.smack_frame(t)
        sh = 0.0
        if u < 0.45: sh = 9 * (1 - u / 0.45) * math.sin(u * 75)
        z = lerp(2.15, 2.0, eo3(u / 0.3)) if u < 0.3 else lerp(2.0, 2.25, smooth((u - 0.3) / 2.6))
        desat = 0.75 * smooth((t - TL.T_DESAT0) / (TL.T_DESAT1 - TL.T_DESAT0))
        flash = 1.0 if u < 0.05 else (0.5 if u < 0.09 else 0.0)
        img = fr.render(pcam(z, 186, 104, sx=sh, sy=0), L, GRADE_BED, frame=self.fi(t), desat=desat, flash=flash,
                        tint=(1.0 + 0.12 * desat, 0.9, 0.9), air=self.b.air(fr, phone_k=0.0))
        cv = UI()
        G.onomatopoeia(cv, '啪！', 300, 72, u - 0.04, 5, C('#ffe24a'), life=1.2)
        self.hud(cv, t)
        if t >= TL.T_FLAT and int(t * 6) % 2 == 0:
            cv.rect(0, 0, 480, 2, (255, 40, 40, 150)); cv.rect(0, 268, 480, 2, (255, 40, 40, 150))
        return ui_over(img, cv.a, scale=4)

    # ================================================================ GAME OVER + 本局结算
    def f_over(self, t):
        if self._over_bg is None:
            fr, L = self.smack_frame(TL.S_OVER - 0.01)
            self._over_bg = fr.render(pcam(2.25, 186, 104), L, GRADE_BED, frame=0, desat=0.85, tint=(1.1, 0.85, 0.85))
        u = t - TL.S_OVER
        img = self._over_bg.copy()
        # slow push + darken + red floor glow
        s = 1.0 + 0.03 * smooth(u / 7)
        if s > 1.001:
            M = cv2.getRotationMatrix2D((960, 600), 0, s); img = cv2.warpAffine(img, M, (1920, 1080), flags=cv2.INTER_NEAREST)
        dk = lerp(1.0, 0.32, eo3(u / 0.35))
        img = img * dk
        yy = np.linspace(0, 1, 1080, dtype=np.float32)[:, None, None]
        img = img + (0.10 * yy ** 2) * np.array([1.0, 0.1, 0.12], np.float32) * (0.85 + 0.15 * math.sin(t * 4))
        cv = UI()
        rng = np.random.default_rng(3)
        for i in range(60):                                     # embers
            x0, y0, sp, ph = rng.uniform(0, 480), rng.uniform(0, 1), rng.uniform(14, 40), rng.uniform(0, 6)
            y = 270 - ((y0 * 270 + u * sp) % 270); x = x0 + 3 * math.sin(u * 2 + ph)
            b = 0.5 + 0.5 * math.sin(u * 9 + ph)
            cv.rect(int(x), int(y), 1 + (i % 3 == 0), 1, (255, int(110 + 120 * b), 50, int(200 * b)))
        # GAME OVER slam (one line)
        d = t - TL.T_GAME
        if d >= -0.08:
            if d < 0: sc, sy = 7, 1.0
            else: sc, sy = 4, 1 - 0.3 * math.sin(math.pi * clamp01(d / 0.14))
            G.pixel_word(cv, 'GAME OVER', 240, 36, sc, C('#ff3b3b'), C('#5a0812'), C('#ffb0a0'), sy=sy, depth=3)
            if 0 <= d < 0.3: G.burst_lines(cv, 240, 36, 150 + 120 * d, 170 + 200 * d, 16, C('#ffd0c0'), 1 - d / 0.3)
        rows = [('kv', '死因', '熬夜', C('#ff4a3c'), True),
                ('kv', '附加伤害', '手机砸脸', C('#ffd9a0')),
                ('count', '本局刷视频', 137, '条', C('#ffffff')),
                ('count', '本月说“就十分钟”', 23, '次', C('#ffd34a'), '第 '),
                ('battery', '手机电量', 100, '你的电量', 0)]
        if t >= TL.T_PANEL:
            G.result_panel(cv, t, TL.T_ROWS, rows, y=64, w=316, gap=TL.ROW_GAP)
            if TL.T_PANEL <= t < TL.T_ROWS:      # panel frame appears with the line, rows follow on "熬夜"
                pass
        # rating stamp
        if t >= TL.T_STAMP - 0.08:
            a = t - TL.T_STAMP
            cx, cy = 352, 150
            sc = 1.0 if a >= 0 else 1.8
            r = int(26 * sc)
            col = (230, 48, 48, 255)
            for rr in (r, r - 1, r - 4):
                for k in range(80):
                    an = k / 80 * 6.283
                    cv.px(int(cx + rr * math.cos(an)), int(cy + rr * math.sin(an)), col)
            G.pixel_word(cv, 'F', cx, cy - 2, int(round(4 * sc)), C('#ff4040'), C('#5a0812'), C('#ffb0a0'), depth=2)
            cv.text(cx - 10, cy + 14, '评级', col, 'zh8')
            if 0 <= a < 0.15: G.burst_lines(cv, cx, cy, 30 + 60 * a, 40 + 90 * a, 12, C('#ffd0c0'), 1 - a / 0.15)
        return ui_over(img, cv.a, scale=4)

    # ================================================================ ghost
    def ghost_state(self, t):
        """(x, y, face, arms, look, squash, alpha) in room coords."""
        bx, by = 182, 100
        if t < TL.T_POP: return None
        def target(tt):
            return (bx, by - 34 if tt >= TL.T_POP + 0.05 else by)
        y = P.spring_follow(lambda tt: target(tt)[1], t, freq=2.6, zeta=0.38, window=1.5)
        x = bx
        u = t - TL.T_POP
        squash = -0.35 * math.exp(-u * 6) if u < 0.5 else 0.0
        if 0.25 < u < 0.7: squash += 0.18 * math.sin((u - 0.25) / 0.45 * math.pi)
        face, arms, look = 'normal', 'rest', (0, 0)
        if TL.T_DIZZY0 <= t < TL.T_DIZZY1: face = 'dizzy'
        elif TL.T_HANDS <= t < TL.T_BODY: face, arms, look = 'normal', 'hold', (0, 3)
        elif TL.T_BODY <= t < TL.T_BACK: face, look = 'normal', (-1, 4)
        elif TL.T_BACK <= t < TL.T_TAKE: face, look = ('blink' if t < TL.T_BACK + 0.08 else 'normal'), (0, 0)
        elif TL.T_TAKE <= t < TL.T_PANIC1:
            face, arms = 'wow', ('up' if t >= TL.T_PANIC0 else 'rest')
            look = (-1, 4)
            y = y - 7 * eo3((t - TL.T_TAKE) / 0.1) + P.wobble(t, TL.T_TAKE + 0.1, 3, 5, 4)
            if t >= TL.T_PANIC0: x = x + 2 * math.sin(t * 60)
        elif t >= TL.T_PANIC1:
            face, arms, look = ('sad', 'rest', (3, 2)) if t < TL.T_CATSEE + 0.5 else ('happy', 'wave', (3, 2))
            y = y - 7 + 7 * smooth((t - TL.T_PANIC1) / 0.5)
        y = y + 1.5 * math.sin(t * 2.4) * clamp01(u / 1.0)
        return x, y, face, arms, look, squash, clamp01(u / 0.12)

    def put_ghost(self, fr, t, x, y, face='normal', arms='rest', look=(0, 0), alpha=1.0, scale=1.0, squash=0.0):
        g = ghost.draw(face=face, arms=arms, t=t, look=look, alpha=alpha, glow=0.22, squash=squash)
        from pixelkit.core import scale_nearest
        rgba, E = g.rgba, g.E
        if abs(scale - 1) > 0.02: rgba = scale_nearest(rgba, scale); E = scale_nearest(E, scale)
        fr.sprite(rgba, x - g.ax * scale, y - g.ay * scale, E=E)

    def ghost_room(self, t, gx=None, gy=None, **gk):
        cat = 'curl'
        if t >= TL.T_CAT_PUFF: cat = 'puff' if t < TL.T_CATSEE + 0.6 else 'up'
        fr = self.b.frame(t, face='closed', phone='smack', clock=TL.clock(TL.S_SMACK), colon=(int(t * 2) % 2 == 0), cat=cat,
                          cat_look=(-4, -3), screen=(150, 210, 240), chest=0.0)
        return fr

    def f_ghost(self, t):
        st = self.ghost_state(t)
        fr = self.ghost_room(t)
        if st:
            x, y, face, arms, look, squash, a = st
            if t < TL.T_POP + 0.35:        # trail while rising
                for k_, al in ((0.12, 0.25), (0.06, 0.45)):
                    s2 = self.ghost_state(t - k_)
                    if s2: self.put_ghost(fr, t, s2[0], s2[1], s2[2], s2[3], s2[4], al * a, squash=s2[5])
            self.put_ghost(fr, t, x, y, face, arms, look, a, squash=squash)
        L = self.room_light(fr, t, phone_k=0.5, phone_xy=(182, 104), lamp=0.9)
        if st: L = L + fr.band(st[0], st[1] - 14, 34, 28, (0.55, 0.75, 1.0), [(1.0, 0.18), (0.5, 0.32)])
        u = t - TL.S_GHOST
        z = lerp(1.75, 1.85, smooth(u / 3.6)); cx = lerp(188, 194, smooth(u / 3.6)); cy = lerp(100, 98, smooth(u / 3.6))
        c = pcam(z, cx, cy)
        img = fr.render(c, L, GRADE_BED, frame=self.fi(t), desat=0.35, tint=(0.9, 0.94, 1.08))
        cv = UI()
        if st:
            x, y = st[0], st[1]
            ux, uy = c.w2ui(x, y - 24, 4)
            ghost.ring(cv, ux, uy - 6, t, r=7, alpha=st[6], size=2)
            if TL.T_DIZZY0 <= t < TL.T_DIZZY1: ui.dizzy_stars(cv, ux, uy + 2, t, n=3, rx=22, ry=5)
            if TL.T_TAKE <= t < TL.T_PANIC1:
                G.onomatopoeia(cv, '！！', ux + 46, uy + 4, t - TL.T_TAKE, 2, C('#ffe24a'), life=0.8)
                for i in range(3):          # sweat drops flying off
                    d = (t - TL.T_PANIC0 + i * 0.13) % 0.4
                    if t >= TL.T_PANIC0:
                        cv.rect(int(ux - 30 - 30 * d - i * 6), int(uy + 10 - 40 * d + 120 * d * d), 3, 4, (130, 210, 255, 255))
            if t >= TL.T_CATSEE and t < TL.S_QUEST:
                cxu, cyu = c.w2ui(self.b.A['cat'][0] - 8, self.b.A['cat'][1] - 24, 4)
                a = clamp01((t - TL.T_CATSEE) / 0.1)
                if t < TL.T_CATSEE + 0.6: cv.text(int(cxu) - 4, int(cyu) - 18, '嘶！', (255, 140, 120, int(255 * a)), 'zh10', outline=(20, 8, 10, 255))
        return ui_over(img, cv.a, scale=4)

    # ================================================================ quest + the gag
    def f_quest(self, t):
        fr = self.ghost_room(t)
        z = 1.9; pz = smooth((t - TL.S_QUEST) / 0.6); cx = lerp(188, 228, pz); cy = lerp(88, 80, pz)
        c = pcam(z, cx, cy)
        # where the buttons sit (UI), and the world x that puts the ghost's hand on them
        px, py, pw, ph = 196, 40, 262, 158
        by = py + ph - 34
        bad_ui = (212, by + 11); ok_ui = (382, by + 11)
        def world_x_for(ux): return cx + (ux - 240) * 4 / (6 * z)
        def world_y_for(uy): return cy + (uy - 135) * 4 / (6 * z)
        home = (186, 56)
        hx_bad = world_x_for(bad_ui[0]) - 15; hy_bad = world_y_for(bad_ui[1]) + 4
        hx_ok = world_x_for(ok_ui[0]) - 14; hy_ok = world_y_for(ok_ui[1]) + 2
        gx, gy = home; face, arms, look, squash = 'normal', 'rest', (2, 0), 0.0
        if TL.T_PANEL_Q + 0.3 <= t < TL.T_REACH0: face, look = 'happy', (3, 0)
        if TL.T_REACH0 <= t < TL.T_FREEZE:
            k = smooth((t - TL.T_REACH0) / (TL.T_FREEZE - TL.T_REACH0))
            gx, gy = lerp(home[0], hx_bad, k), lerp(home[1], hy_bad, k); face, arms, look = 'smug', 'point', (3, 1)
        elif TL.T_FREEZE <= t < TL.T_RETRACT0:
            k = 1.0
            gx, gy = lerp(home[0], hx_bad, k), lerp(home[1], hy_bad, k)
            gx += P.wobble(t, TL.T_FREEZE, 2.0, 7, 5); face, arms, look = 'wow', 'point', (3, 1)
            if t >= TL.T_SKULL: face = 'sad'
        elif TL.T_RETRACT0 <= t < TL.T_CLICK - 0.12:
            k0 = 1.0
            sx0, sy0 = lerp(home[0], hx_bad, k0), lerp(home[1], hy_bad, k0)
            k = smooth((t - TL.T_RETRACT0) / (TL.T_RETRACT1 - TL.T_RETRACT0))
            gx, gy = lerp(sx0, home[0], k), lerp(sy0, home[1], k)
            face, arms, look = ('squint', 'rest', (-2, -1)) if t < TL.T_WHISTLE1 else ('determined', 'fist', (3, 1))
        elif t >= TL.T_CLICK - 0.12:
            k = eo3((t - TL.T_CLICK + 0.12) / 0.12)
            gx, gy = lerp(home[0], hx_ok, k), lerp(home[1], hy_ok, k); face, arms, look = 'happy', 'point', (3, 1)
            if t >= TL.T_CLICK + 0.2:
                k2 = smooth((t - TL.T_CLICK - 0.2) / 0.4); gx, gy = lerp(hx_ok, home[0], k2), lerp(hy_ok, home[1], k2)
                face, arms = 'happy', 'up'
        gy += 1.6 * math.sin(t * 2.4)
        L = self.room_light(fr, t, phone_k=0.5, phone_xy=(182, 104), lamp=0.9)
        L = L + fr.band(gx, gy - 14, 34, 28, (0.55, 0.75, 1.0), [(1.0, 0.18), (0.5, 0.32)])
        img = fr.render(c, L, GRADE_BED, frame=self.fi(t), desat=0.4, tint=(0.88, 0.92, 1.08))
        cv = UI()
        ux, uy = c.w2ui(gx, gy - 24, 4)
        if t >= TL.T_REVIVE: G.revive_hud(cv, 0, 0, 5, k=clamp01((t - TL.T_REVIVE) / 0.35))
        # panel + buttons
        kin = clamp01((t - TL.T_PANEL_Q) / 0.45); kout = clamp01((t - TL.T_PANEL_OUT) / 0.22)
        if kin > 0 and kout < 1:
            al = 1 - kout
            G.quest_panel(cv, px, py, pw, ph, kin, '复活任务', 'QUEST', [(C('#ffd34a'), '目标：', '通关 5 个副本'),
                          (C('#7fe0ff'), '条件：', '查明睡眠的真相'), (C('#5fd07a'), '奖励：', '复活 ×1')], alpha=al)
            oy = int(round((1 - back_out(kin, 1.7)) * -120))
            byy = by + oy
            st_ok = 'pressed' if TL.T_CLICK <= t < TL.T_CLICK + 0.14 else ('hover' if TL.T_CLICK - 0.1 <= t < TL.T_CLICK + 0.3 else 'idle')
            G.game_button(cv, 372, byy, 70, 22, '接受', st_ok, C('#3a9a5c'), al, 'zh12')
            # the tempting button
            label, state, col, sy = '我还能再熬会儿', 'idle', C('#b04050'), 1.0
            bob = 0
            if TL.T_REACH0 - 0.3 <= t < TL.T_FREEZE:
                state = 'hover'; bob = int(round(1.5 * math.sin(t * 9)))
            if TL.T_SKULL <= t < TL.T_RETRACT1 + 0.2:
                flick = int((t - TL.T_SKULL) * 10) % 3 != 2
                label = 'GAME OVER' if flick else label
                col = C('#6a1018') if flick else col
            G.game_button(cv, 210, byy + bob, 150, 22, label, state, col, al, 'zh12', sy=sy)
            if TL.T_REACH0 - 0.3 <= t < TL.T_FREEZE:          # it sparkles at you
                for i in range(4):
                    a_ = (t * 3 + i / 4) % 1
                    ui.star(cv, 218 + (i * 37) % 140, byy - 6 + int(30 * a_) % 30, C('#ffe27a'), 1 - a_, small=(i % 2 == 0))
            if TL.T_SKULL <= t < TL.T_RETRACT1 + 0.2:
                G.onomatopoeia(cv, '☠', 366, byy - 8, t - TL.T_SKULL, 2, C('#ff6a6a'), life=TL.T_RETRACT1 + 0.2 - TL.T_SKULL)
            if TL.T_CLICK <= t < TL.T_CLICK + 0.45:
                d = t - TL.T_CLICK
                G.burst_lines(cv, 407, byy + 11, 30 + 120 * d, 44 + 160 * d, 14, C('#ffe27a'), 1 - d / 0.45)
        # the ghost lives on the UI layer here so it can float over the panel to the buttons
        g = ghost.draw(face=face, arms=arms, t=t, look=look, glow=0.22, squash=squash)
        gu = c.w2ui(gx, gy, 4); h_, w_ = g.rgba.shape[:2]; S3 = 2.85
        ui.blit_scaled(cv, g.rgba, gu[0] + (w_ / 2 - g.ax) * S3, gu[1] + (h_ / 2 - g.ay) * S3, S3)
        ghost.ring(cv, ux, uy - 6, t, r=7, size=2)
        # whistle notes
        if TL.T_WHISTLE0 <= t < TL.T_WHISTLE1:
            for i in range(3):
                d = (t - TL.T_WHISTLE0 - i * 0.22)
                if 0 <= d < 0.7:
                    cv.text(int(ux - 34 - 10 * d), int(uy + 4 - 40 * d), '♪', (255, 236, 150, int(255 * (1 - d / 0.7))), 'zh12',
                            outline=(20, 12, 4, int(255 * (1 - d / 0.7))))
        return ui_over(img, cv.a, scale=4)

    # ================================================================ hub of doors
    def f_hub(self, t):
        states = ['locked'] * 5
        if t >= TL.T_ACTIVE: states[0] = 'active'
        appear = [clamp01((t - td) / 0.28) for td in TL.T_DOORS]
        op = [eo3((t - TL.T_OPEN0) / (TL.T_OPEN1 - TL.T_OPEN0)), 0, 0, 0, 0]
        fr = self.hub.frame(t, states, appear, op, circle_k=clamp01((t - TL.S_HUB) / 0.4))
        k = smooth((t - TL.T_FLOAT0) / (TL.T_FLOAT1 - TL.T_FLOAT0))
        d0 = self.hub.D[0]
        gx = lerp(160, d0['x'], k); gy = lerp(138, d0['yb'] - 16, k) + 2 * math.sin(t * 2.4) - 10 * math.sin(math.pi * k)
        sc = lerp(1.0, 0.72, k)
        face = 'happy' if t < TL.T_ACTIVE + 0.1 else ('wow' if t < TL.T_FLOAT0 else 'determined')
        look = (0, 0) if t < TL.T_ACTIVE else (-2, 0)
        self.put_ghost(fr, t, gx, gy, face=face, arms=('wave' if t < TL.T_ACTIVE else 'rest'), look=look, scale=sc)
        L = self.hub.light(fr, states, appear, op)
        L = L + fr.band(gx, gy, 30, 22, (0.55, 0.75, 1.0), [(1.0, 0.15), (0.5, 0.3)])
        z = logz(1.0, 2.6, smooth((t - TL.T_FLOAT0 - 0.3) / 1.6)); cx = lerp(160, d0['x'] + 4, smooth((t - TL.T_FLOAT0) / 1.8))
        cy = lerp(98, d0['yb'] - 26, smooth((t - TL.T_FLOAT0) / 1.8))
        c = pcam(z, cx, cy)
        from pixelkit.pixstage import GRADE_NIGHT
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t), air=self.hub.air(fr, states, appear, op))
        w = smooth((t - TL.T_WHITE) / (TL.END - TL.T_WHITE))
        img = img + (1 - img) * w
        cv = UI()
        G.revive_hud(cv, 0, 0, 5)
        if TL.S_HUB + 0.3 < t < TL.T_FLOAT0:
            a = clamp01((t - TL.S_HUB - 0.3) / 0.3) * (1 - clamp01((t - TL.T_FLOAT0 + 0.3) / 0.3))
            tw = G.text_width('选择副本', 'zh12')
            cv.text(240 - tw // 2, 22, '选择副本', (255, 230, 160, int(255 * a)), 'zh12', outline=(20, 10, 4, int(255 * a)))
        ux, uy = c.w2ui(gx, gy - 24 * sc, 4)
        ghost.ring(cv, ux, uy - 6, t, r=7, size=2)
        return ui_over(img, cv.a, scale=4)

    def frame(self, t):
        img = self.ed.frame(min(t, TL.END - 1e-3))
        return ui_over(img, subs_layer(t, TL.L, TL.HL).a, scale=5)

def make(**kw): return Opening(**kw)
