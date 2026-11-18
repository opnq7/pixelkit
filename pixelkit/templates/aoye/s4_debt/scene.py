"""第 4 关 v4 · 2003 睡眠债：一个问题 → 三个晚上 → 反应盒 → 记录纸 → 「我挺好的」→ 欠条怪 → 答案 → 存档点。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s4_debt'))
import numpy as np, cv2
import timeline as TL
from common import subs_layer, lerp, smooth, FPS, put_human, nightcap, ghost_dive, hud2, revive_curve, Anchor
from pixelkit import ui, gameui as G, acting as A
from pixelkit.core import C, scale_nearest
from pixelkit.edit import Edit
from pixelkit.scene import ui_over
from pixelkit.pixstage import Stage, cam as pcam, GRADE_NIGHT
from pixelkit.plates import Plate
from pixelkit.sets.hub_doors import HubDoors
from pixelkit.sets import debt_props as D
from pixelkit.characters import human
from pixelkit.characters.cast_sleep import SUBJECT
from pixelkit.anim import back_out, clamp01

PL = (_PROJ + '/assets/plates/')
def eo3(u): u = clamp01(u); return 1 - (1 - u) ** 3
def logz(a, b, k): return math.exp(math.log(a) + (math.log(b) - math.log(a)) * k)

KEY_LAB = (300, 58); KEY_VAULT = (160, 20)
DESK = (250, 143)
DANMAKU = ['我', '+1', '本人', '六小时都算奢侈', '我是五小时', '别骂了别骂了', '看这条的我：凌晨一点', '已经在还了', '破防了', '原来我是负债人']
DM_ROWS = (58, 76)

class Level4:
    def __init__(self):
        self.pA, self.pB = Plate(PL + 'L4-A.png'), Plate(PL + 'L4-B.png')
        self.pPVT, self.pBED = Plate(PL + 'L4-PVT.png'), Plate(PL + 'L4-BED.png')
        self.hub = HubDoors(); self.anchor = Anchor()
        e = self.ed = Edit()
        e.add('lab', TL.S_LAB, self.f_lab)
        e.add('bed', TL.S_BED, self.f_bed, 'dissolve', 0.4)
        e.add('pvt', TL.S_PVT, self.f_pvt, 'dissolve', 0.3)
        e.add('nod', TL.S_NOD, self.f_nod, 'cut')
        e.add('print', TL.S_PRINT, self.f_print, 'cut')
        e.add('fine', TL.S_FINE, self.f_fine, 'dissolve', 0.3)
        e.add('debt', TL.S_DEBT, self.f_vault, 'whip', 0.36, dir=1)
        e.add('crowd', TL.S_CROWD, self.f_vault, 'cut')
        e.add('anchor', TL.S_ANCHOR, self.f_anchor, 'dissolve', 0.6)
        e.add('hub', TL.S_HUB, self.f_hub, 'dissolve', 0.5)
        e.end(TL.END)
        self.act_in = A.Act(face='normal', float_amp=1.5, look=(2, 0)).beat(1.3, 'ask', dur=0.7)
        self.act_back = A.Act(face='sad', float_amp=1.8, look=(0, 3)).hold(TL.T_REVIVE, 99, face='happy').beat(TL.T_REVIVE + 0.05, 'cheer', dur=0.9)
        self.act_hub = A.Act(face='happy', float_amp=2.0).beat(TL.T_BTN + 0.35, 'take', look=(-2, 1), dur=0.7)
        self.act_hub.beat(TL.T_BTN + 1.15, 'shake', dur=0.6, face='squint')
        self.monster_por = self._monster_portrait()

    def fi(self, t): return int(round(t * FPS))
    def compose(self, img, cv): return ui_over(img, cv.a, scale=4)

    def _monster_portrait(self):
        s = Stage(60, 90); s.img[..., 3] = 0
        D.bill_monster(s, 30, 88, 0.4, size=1.1, face='grin')
        a = s.img.copy(); a[..., 3] = np.where(a[..., :3].sum(-1) > 0, 255, 0)
        return a[4:56]

    # ------------------------------------------------------------------ HUD: one thing at a time
    def hud(self, t, loc=True, pips=False):
        pct, fl = revive_curve(t, TL.T_REVIVE, 60, 80)
        cv = hud2(t, pct, 4 if t > TL.T_REVIVE + 0.6 else 3, fl, '2003' if loc else None, '宾夕法尼亚大学 · 睡眠实验室',
                  t_enter=TL.T_TAG, t_out=TL.S_BED - 0.4, k=1.0 if pips else 0.0)
        if t < TL.S_ANCHOR + 0.7: G.question_card(cv, t, TL.T_Q, '每天少睡一点，会怎样？', TL.T_ANS, '睡眠债：每天欠一点，周末还不清', hold=4.0, y=34)
        return cv

    def ghost(self, fr, t, act, x, y, scale=1.0):
        p = act.at(t); rgba, E, ax, ay = A.ghost_sprite(p, t)
        if abs(scale - 1) > 0.02: rgba = scale_nearest(rgba, scale); E = scale_nearest(E, scale)
        fr.sprite(rgba, x + p['dx'] - ax * scale, y + p['dy'] - ay * scale, E=E)
        return p, (x + p['dx'], y + p['dy'] - 24 * scale)

    # ------------------------------------------------------------------ 1. lab: possession + the 1964 record + a yawn
    def f_lab(self, t):
        P = self.pA; fr = P.frame()
        hit = t >= TL.T_HIT; white = max(0.0, 1 - (t - TL.T_HIT) / 0.12) if hit else 0.0
        face = 'tired'
        if hit and t < TL.T_HIT + 0.7: face = 'surprised'
        if TL.T_YAWN <= t < TL.T_YAWN + 0.9: face = 'o'
        top = put_human(fr, SUBJECT, DESK[0], DESK[1], face=face, look_dir=(2, -1) if not hit else (-1, 0), white=white,
                        arms='up' if TL.T_YAWN <= t < TL.T_YAWN + 0.9 else 'rest')
        if t > TL.T_HIT + 0.15: nightcap(fr, DESK[0], top[1] + 2, t)
        p = None
        if t < TL.T_POSSESS:
            u = smooth((t - TL.T_GHOST_IN) / 1.3)
            p, head = self.ghost(fr, t, self.act_in, lerp(40, 196, u), 78 + 6 * math.sin(math.pi * u))
        elif t < TL.T_POSSESS + 0.5:
            ghost_dive(fr, t, TL.T_POSSESS, (196, 78), (DESK[0], DESK[1] - 41), 0.45, look=(2, 1))
        L = P.light(fr, key=KEY_LAB)
        if hit: L = L + fr.band(DESK[0], DESK[1] - 41, 30, 30, (0.7, 0.9, 1.0), [(1.0, 0.5 * white), (0.5, white)])
        k1 = smooth((t - TL.T_HIT) / 1.0)
        c = pcam(logz(1.05, 1.7, k1), lerp(170, 232, k1), lerp(92, 106, k1), sx=10 * white * math.sin(t * 90))
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t))
        img = img + (1 - img) * (1 - smooth(t / 0.5))
        cv = self.hud(t)
        if p is not None: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if hit and t < TL.T_HIT + 0.5:
            ux, uy = c.w2ui(DESK[0], DESK[1] - 41, 4); d = t - TL.T_HIT
            G.burst_lines(cv, ux, uy, 20 + 160 * d, 34 + 200 * d, 16, C('#bfe8ff'), 1 - d / 0.5)
        ui.name_card(cv, 12, 200, '受试者 17 号', 'LV.22', '', k=clamp01((t - TL.T_CARD) / 0.3) * (1 - clamp01((t - TL.T_EXTREME + 0.5) / 0.3)))
        if TL.T_EXTREME - 0.3 <= t < TL.S_BED:                 # the 1964 record, on its own
            k = ui.pop_k(t - TL.T_EXTREME + 0.3, TL.S_BED - TL.T_EXTREME)
            if k > 0.05:
                x0, y0, w, h = 24, 120, 150, 44
                ww = int(w * k)
                cv.rect(x0 + 3, y0 + 4, ww, h, (0, 0, 0, 110)); cv.rect(x0, y0, ww, h, (26, 22, 48, 245)); cv.rect(x0, y0, 3, h, (255, 211, 74, 255))
                if k > 0.9:
                    cv.text(x0 + 10, y0 + 5, '上一关 · 1964', (200, 190, 230, 255), 'zh10')
                    cv.text(x0 + 10, y0 + 20, '连熬 11 天', (255, 236, 200, 255), 'zh12')
                    if t >= TL.T_EXTREME: ui.rubber_stamp(cv, x0 + 112, y0 + 24, '太极端', t - TL.T_EXTREME, fname='zh10', scale=1, angle=-5)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 2. three nights at the bed (same frame, the room keeps score)
    def bed_frame(self, t, idx, u):
        """idx 0/1/2 = night 1/7/14, u = 0..1 inside the beat."""
        P = self.pBED; fr = P.frame(); base = fr.img.copy()
        night = TL.NIGHTS[idx]
        ring = u > 0.5
        face = 'closed'
        if ring: face = ('normal', 'tired', 'closed')[idx] if u > 0.62 else 'surprised' if idx < 2 else 'closed'
        p = human.draw(SUBJECT, face=face)
        hy = 64 - (2 if (ring and idx < 2 and u > 0.62) else 0)
        fr.sprite(p.body.cv.a[:34], 163 - p.ax, hy - 20)
        nightcap(fr, 163, hy - 18, t, 24)
        chin = fr.M_poly([(118, 71), (208, 71), (232, 110), (96, 110)])
        fr.img[chin] = base[chin]
        fr.fill(fr.M_rect(126, 70, 74, 1), '#b8b8d0')
        br = 0.5 + 0.5 * math.sin(t * 2 * math.pi / 3.6)
        fr.mul(fr.M_ell(163, 92 - br, 34, 12) & chin & (fr.yy > 96), 0.86)
        D.alarm_clock(fr, 68, 58, t, ring=1.0 if ring else 0.0)
        D.iou_jar(fr, 90, 67, (0, 7, 14)[idx] + (2 if u > 0.75 else 0), t, overflow=idx == 2 and u > 0.75)
        D.cup_stack(fr, 236, 152, (1, 4, 9)[idx], s=1.3)
        if idx == 2:                                            # night 14: sticky notes + a dropped phone on the floor
            for k in range(3): fr.rect(52 + k * 7, 56 - k, 6, 6, ['#ffe87a', '#ff9aa0', '#9ae0ff'][k])
        L = P.light(fr)
        L = L + fr.band(68, 58, 26, 20, (1.0, 0.85, 0.6), [(1.0, 0.12 if ring else 0.0)])
        return fr, L

    def f_bed(self, t):
        idx, t0 = TL.night_at(t)
        u = (t - t0) / TL.NIGHT_LEN
        fr, L = self.bed_frame(t, idx, u)
        sh = 1.5 * math.sin(t * 50) if (u > 0.5 and u < 0.62) else 0.0
        c = pcam(1.25 + 0.03 * idx, 160, 84, sx=sh)
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t))
        # page flip into the next night (a paper sheet wipes down from the top; no flashing)
        if idx > 0 and t - t0 < TL.FLIP:
            pfr, pL = self.bed_frame(t, idx - 1, 1.0)
            prev = pfr.render(c, pL, GRADE_NIGHT, frame=self.fi(t))
            k = smooth((t - t0) / TL.FLIP); edge = int(1080 * k)
            img = img.copy(); img[edge:] = prev[edge:]
            img[max(0, edge - 10):edge] = (0.95, 0.92, 0.84)
        cv = self.hud(t, loc=False)
        # night label + the 8-slot sleep bar (6 filled, 2 slip into the jar)
        a = clamp01((t - t0) / 0.2)
        x0, y0 = 322, 30
        cv.rect(x0 + 3, y0 + 4, 136, 40, (0, 0, 0, int(110 * a))); cv.rect(x0, y0, 136, 40, (24, 22, 46, int(240 * a)))
        cv.rect(x0, y0, 3, 40, (127, 224, 255, int(255 * a)))
        cv.text(x0 + 10, y0 + 4, f'第 {TL.NIGHTS[idx]} 晚', (255, 236, 200, int(255 * a)), 'zh12')
        cv.text(x0 + 66, y0 + 6, '睡 6 小时', (170, 200, 255, int(255 * a)), 'zh10')
        for i in range(8):
            fill = i < 6
            cv.rect(x0 + 10 + i * 15, y0 + 24, 13, 9, ((110, 160, 255) if fill else (52, 48, 80)) + (int(255 * a),))
        if 0.3 < u < 0.75:                                       # the 2 missing hours fly into the jar
            jx, jy = c.w2ui(90, 50, 4)
            q = smooth((u - 0.3) / 0.45)
            for i in range(2):
                sx, sy = x0 + 10 + (6 + i) * 15, y0 + 24
                x = lerp(sx, jx - 4 + 6 * i, q); y = lerp(sy, jy, q) - 30 * math.sin(math.pi * q)
                cv.rect(int(x), int(y), 12, 8, (255, 120, 100, 255)); cv.text(int(x) + 2, int(y) - 2, '欠', (255, 240, 220, 255), 'zh8')
        if u > 0.5:
            ux, uy = c.w2ui(68, 46, 4)
            G.onomatopoeia(cv, '铃——', ux + 6, uy - 34, t - t0 - 0.5 * TL.NIGHT_LEN, 2, C('#ffe27a'), life=0.55)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 3. the reaction box (no hands: the button + the counter tell it)
    def pvt_state(self, t):
        for i, (t0, rt) in enumerate(TL.TRIALS):
            nxt = TL.TRIALS[i + 1][0] if i + 1 < len(TL.TRIALS) else 99
            if t0 <= t < nxt:
                a = t - t0
                if rt is not None:
                    if a < rt: return f'{int(a * 1000):d}', False, False
                    return f'{int(rt * 1000):d}', a < rt + 0.12, False
                if a < 0.55: return f'{int(a * 1000):d}', False, False
                return 'LAPSE', False, True
        return '', False, False

    def f_pvt(self, t):
        P = self.pPVT; fr = P.frame()
        txt, press, lapse = self.pvt_state(t)
        x0, y0, w, h = 82, 103, 108, 25
        fr.rect(x0, y0, w, h, '#1a0402')
        on = '#ff4a30' if not lapse or int(t * 3) % 2 == 0 else '#c83020'
        if txt: D.sevenseg(fr, x0 + w - 10 - len(txt) * 14, y0 + 4, txt, s=2, on=on, off='#2e0806', glow=0.95)
        bx, by = 217, 118
        if press:
            fr.mul(fr.M_ell(bx, by, 12, 12), 0.72); fr.fill(fr.M_ell(bx, by + 1, 9, 9) & (fr.yy < by - 4), '#ff7a5a')
        L = P.light(fr) + fr.band(136, 140, 90, 22, (1.0, 0.3, 0.2), [(1.0, 0.10), (0.5, 0.18)])
        u = smooth((t - TL.S_PVT) / (TL.S_NOD - TL.S_PVT))
        c = pcam(lerp(1.02, 1.18, u), lerp(160, 150, u), lerp(92, 112, u))
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        a = clamp01((t - TL.S_PVT - 0.1) / 0.25)
        G._panel(cv, 22, 30, 150, 22, a)
        cv.text(30, 33, 'PVT 反应测试 · 第 14 天', (255, 236, 200, int(255 * a)), 'zh10')
        for i, (t0, rt) in enumerate(TL.TRIALS):
            if t >= t0 + (rt or 0.55) + 0.05:
                s = f'{int(rt * 1000)} ms' if rt else '漏！'
                col = (110, 255, 150, 255) if rt else (255, 90, 80, 255)
                cv.text(30 + i * 52, 58, s, col, 'zh10', outline=(0, 0, 0, 255))
        if press:
            ux, uy = c.w2ui(217, 106, 4); G.onomatopoeia(cv, '咔', ux, uy - 10, 0.05, 2, C('#ffffff'), life=0.2)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 3b. he nods off over the box, jerks awake
    def f_nod(self, t):
        P = self.pA; fr = P.frame()
        jerk = t >= TL.T_JERK
        u = smooth((t - TL.S_NOD) / (TL.T_JERK - TL.S_NOD))
        hd = 0 if jerk else int(round(5 * u))
        top = put_human(fr, SUBJECT, DESK[0], DESK[1], face='surprised' if jerk else 'closed', head_dy=hd, tilt=0 if jerk else -7 * u)
        nightcap(fr, DESK[0], top[1] + 2 + hd, t)
        c = pcam(2.1, 236, 100, sx=(3 * math.sin(t * 70) if jerk and t < TL.T_JERK + 0.2 else 0))
        img = fr.render(c, P.light(fr, key=KEY_LAB), GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        ux, uy = c.w2ui(DESK[0], top[1], 4)
        if not jerk: A.draw_fx(cv, [('zz', 0, 1)], ux, uy, t)
        else: A.draw_fx(cv, [('!', t - TL.T_JERK, 1), ('sweat', t - TL.T_JERK, 1)], ux, uy, t)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 3c. the printout: two weeks of 6 h ≈ one sleepless night
    def f_print(self, t):
        s = Stage(320, 180)
        bg = cv2.GaussianBlur(self.pA.rgb, (0, 0), 3)
        s.img[..., :3] = (bg * 0.45).astype(np.uint8); s.E[:] = 0
        k = smooth((t - TL.S_PRINT) / 1.4)
        D.printout(s, 86, 30, t, k=k, circle=clamp01((t - TL.T_CIRCLE) / 0.5))
        L = s.light_base((1.0, 0.92, 0.8), 0.95)
        img = s.render(pcam(lerp(1.0, 1.12, smooth((t - TL.S_PRINT) / 2.6)), 160, 84), L, GRADE_NIGHT, frame=self.fi(t))
        return self.compose(img, self.hud(t, loc=False))

    # ------------------------------------------------------------------ 4. "I'm fine." - the self-assessment vs reality
    def f_fine(self, t):
        P = self.pA; fr = P.frame()
        micro = TL.T_MICRO <= t < TL.T_MICRO + 0.4
        jerk = TL.T_MICRO + 0.4 <= t < TL.T_MICRO + 0.65
        face = 'closed' if micro else ('surprised' if jerk else 'smile')
        hd = 5 if micro else (-1 if jerk else 0)
        top = put_human(fr, SUBJECT, DESK[0], DESK[1], face=face, arms='rest' if micro else 'wave', head_dy=hd, tilt=-6 if micro else 0)
        nightcap(fr, DESK[0], top[1] + 2 + hd, t)
        c = pcam(1.9, 226, 100, sx=(3 * math.sin(t * 60) if jerk else 0))
        img = fr.render(c, P.light(fr, key=KEY_LAB), GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        ux, uy = c.w2ui(DESK[0], top[1], 4)
        ui.speech_bubble(cv, ux - 22, uy + 14, '我挺好的……' if micro else '我挺好的啊！', t - TL.T_THUMB, life=TL.S_DEBT - TL.T_THUMB,
                         side=-1, with_coin=False, t=t)
        if micro: A.draw_fx(cv, [('zz', 0, 1)], ux, uy, t)
        G.stat_meter(cv, t, TL.T_METERS, 18, 112, '自我感觉', 1.0, C('#5fd07a'), w=160, side=-1, fill_in=False)
        drop = 1.0 - 0.54 * smooth((t - TL.T_DROP) / 0.5)
        G.stat_meter(cv, t, TL.T_METERS + 0.15, 18, 140, '实际表现', drop, C('#ff5a4a'), w=160, side=-1, blink=t > TL.T_DROP + 0.5, fill_in=False)
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 5. the debt bank: the bill monster
    def f_vault(self, t):
        P = self.pB; fr = P.frame()
        sh = self.ed.shot_at(t)
        d = TL.debt(t)
        rise = eo3((t - TL.T_RISE) / 0.9)
        size = (0.5 + 0.8 * rise * (0.75 + 0.25 * d / 40)) * (0.85 if sh == 'crowd' else 1.0)
        hit = max(0.0, 1 - (t - TL.T_HIT_BOSS) / 0.25) if TL.T_HIT_BOSS <= t < TL.T_HIT_BOSS + 0.25 else 0.0
        mface = 'hurt' if TL.T_HIT_BOSS <= t < TL.T_HIT_BOSS + 0.6 else ('smug' if t > TL.T_BROKE else 'grin')
        if rise > 0.02:
            D.bill_monster(fr, 160, 132 + 30 * (1 - rise), t, size=size, face=mface, hit=hit * 0.25)
        sx, sy = 112, 160
        face, arms = 'normal', 'hold'
        if TL.T_PILLOW <= t < TL.T_HIT_BOSS: arms, face = 'up', 'focus'
        elif TL.T_HIT_BOSS <= t < TL.T_BROKE: face, arms = 'smile', 'rest'
        elif t >= TL.T_BROKE: face, arms = 'sad', 'rest'
        if sh == 'crowd': face, arms = 'o', 'rest'
        top = put_human(fr, SUBJECT, sx, sy, face=face, arms=arms, look_dir=(2, -2))
        nightcap(fr, sx, top[1] + 2, t)
        if t < TL.T_PILLOW:
            fr.part(fr.M_ell(sx, sy - 22, 9, 5), ['#8a86a8', '#c8c4dc', '#f0eef8'], bevel=2, amb=0.5, ink='#3a3650')
        elif t < TL.T_HIT_BOSS:
            a = (t - TL.T_PILLOW) / (TL.T_HIT_BOSS - TL.T_PILLOW)
            px, py = lerp(sx, 156, a), lerp(sy - 34, 92, a) - 26 * math.sin(math.pi * a)
            fr.part(fr.M_ell(px, py, 8, 5), ['#8a86a8', '#c8c4dc', '#f0eef8'], bevel=2, amb=0.5, ink='#3a3650')
        L = P.light(fr, key=KEY_VAULT) * P.flicker(fr, t, seed=6, amp=0.06)[..., None]
        shake = 3 * math.sin(t * 60) * hit
        if sh == 'debt': c = pcam(lerp(1.12, 1.24, smooth((t - TL.S_DEBT) / 5)), 150, 100, sx=shake)
        else: c = pcam(lerp(1.24, 1.06, smooth((t - TL.S_CROWD) / 3)), 158, 94)
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t))
        cv = self.hud(t, loc=False)
        ui.chapter_banner(cv, t, '睡眠债银行', 'SLEEP DEBT BANK', TL.T_BANNER0, TL.T_BANNER1, y=10, w=240)
        kout = clamp01((t - TL.T_BOSS_OUT) / 0.3)
        G.boss_bar(cv, t, TL.T_BOSS, '睡眠债', '每晚 +2h', d, 40, hp_lag=TL.debt_lag(t), portrait=self.monster_por, k_out=kout, y=10, w=310, hit=hit)
        if TL.T_HIT_BOSS <= t < TL.T_HIT_BOSS + 0.9:
            q = t - TL.T_HIT_BOSS
            ux, uy = c.w2ui(160, 70, 4)
            G.big_zh(cv, '-2', int(ux + 30), int(uy - 20 * q), 2, C('#ffe27a'), 1 - q / 0.9)
        if TL.T_HIT_BOSS + 0.9 <= t < TL.T_HIT_BOSS + 1.8:
            q = t - TL.T_HIT_BOSS - 0.9
            ux, uy = c.w2ui(160, 70, 4)
            G.big_zh(cv, '+2', int(ux + 30), int(uy - 20 * q), 2, C('#ff6a5a'), 1 - q / 0.9)
        if TL.T_PILLOW - 0.15 <= t < TL.T_HIT_BOSS + 0.4:
            ux, uy = c.w2ui(sx, top[1], 4)
            ui.speech_bubble(cv, ux - 18, uy + 8, '周末懒觉！', t - TL.T_PILLOW + 0.15, life=0.95, side=-1, with_coin=False, t=t)
        if t >= TL.T_BROKE and sh == 'debt':
            ui.rubber_stamp(cv, 392, 150, '余额不足', t - TL.T_BROKE, fname='zh12', scale=2, angle=-5)
        if sh == 'crowd':
            for i, s_ in enumerate(DANMAKU[:8]):
                G.danmaku(cv, t, TL.T_DANMAKU + i * 0.42, s_, y=DM_ROWS[i % 2], speed=165,
                          col=C('#ffffff') if i % 4 else C('#ffd84a'))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 6. back at the save point: +20%, then a magnifier into your own cells
    def cells_img(self, t, beat):
        s = Stage(320, 180); s.img[..., :3] = (58, 16, 34); s.E[:] = 0
        rng = np.random.default_rng(5)
        for j in range(-1, 8):
            for i in range(-1, 10):
                cx = i * 36 + (18 if j % 2 else 0) + rng.uniform(-4, 4); cy = j * 26 + rng.uniform(-3, 3)
                r = 15 + 1.2 * beat
                m = s.M_ell(cx, cy, r, r * 0.82)
                s.part(m, ['#5a1a34', '#8a3050', '#c05a78', '#e88aa0', '#ffc0cc'], bevel=6, light=(-0.4, -0.7, 0.6), amb=0.35, ink='#2a0816')
                nm = s.M_ell(cx + 2, cy + 1, 6, 5)
                s.part(nm, ['#3a0a24', '#6a2050', '#9a4070'], bevel=2, amb=0.4, ink='#1a0410')
                s.ell(cx + 2, cy + 1, 3.2, 3.2, '#ffe8c0', 0.6)
                ang = t * 2.4 + i + j
                s.line(cx + 2, cy + 1, cx + 2 + 2.6 * math.cos(ang), cy + 1 + 2.6 * math.sin(ang), '#3a0a10')
        L = s.light_base((1.0, 0.9, 0.9), 1.0)
        return s.render(pcam(1.0), L, GRADE_NIGHT, frame=0)

    def f_anchor(self, t):
        u = smooth((t - TL.S_ANCHOR) / 1.0)
        gy = lerp(58, 90, u)
        color_k = 0.4 + 0.2 * smooth((t - TL.T_REVIVE) / 0.8)
        zc = smooth((t - TL.T_CELLS + 0.7) / 0.9)
        z = logz(1.6, 3.4, zc); cx = lerp(184, 206, zc); cy = lerp(96, 114, zc)
        img, c, p, head = self.anchor.render(t, color_k, z=z, cx=cx, cy=cy, ghost_xy=(150, gy - 6), ghost_act=self.act_back, frame_i=self.fi(t))
        img = np.clip((np.clip(img, 0, 1) ** 0.8) * 1.35 + 0.02, 0, 1)
        if t >= TL.T_CELLS:                                    # the magnifier: a round lens that grows to fill the frame
            k = eo3((t - TL.T_CELLS) / 1.4)
            beat = max(0.0, math.sin(t * 2 * math.pi * 1.1)) ** 4
            cell = self.cells_img(t, beat)
            ux, uy = c.w2ui(210, 120, 1)
            R = 60 + 1150 * k
            yy, xx = np.ogrid[:1080, :1920]
            m = (xx - ux) ** 2 + (yy - uy) ** 2 <= R * R
            img = img.copy(); img[m] = cell[m]
            ring = m & ((xx - ux) ** 2 + (yy - uy) ** 2 >= (R - 14) ** 2)
            img[ring] = (0.95, 0.78, 0.4)
        cv = self.hud(t, loc=False, pips=True)
        if p is not None and zc < 0.3: A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if TL.T_REVIVE - 0.1 <= t < TL.T_REVIVE + 1.4:          # the +20% moment, big and centred
            q = t - TL.T_REVIVE + 0.1
            k = back_out(clamp01(q / 0.3), 1.6) * (1 - clamp01((q - 1.1) / 0.3))
            if k > 0.05:
                G.big_zh(cv, '复活 +20%', 240 - int(G.text_width('复活 +20%', 'zh12')), int(196 - 6 * k), 2, C('#7fe0ff'), min(1, k))
        return self.compose(img, cv)

    # ------------------------------------------------------------------ 7. hub: a "weekend catch-up coupon" tries to tempt the ghost
    def f_hub(self, t):
        st = ['cleared'] * 3 + ['cleared' if t >= TL.T_CLEAR else 'active', 'active' if t >= TL.T_NEXT else 'locked']
        op = [0.55, 0.55, 0.55, 0.55 * smooth((t - TL.T_CLEAR) / 0.5), eo3((t - TL.T_GO - 0.6) / 0.6)]
        fr = self.hub.frame(t, st, (1,) * 5, op)
        d4 = self.hub.D[4]
        k = smooth((t - TL.T_GO) / 1.0)
        gx = lerp(160, d4['x'], k); gy = lerp(140, d4['yb'] - 18, k)
        p, head = self.ghost(fr, t, self.act_hub, gx, gy, scale=lerp(1, 0.85, k))
        L = self.hub.light(fr, st, (1,) * 5, op) + fr.band(gx, gy, 30, 22, (0.55, 0.75, 1.0), [(1.0, 0.15), (0.5, 0.3)])
        z = logz(1.0, 2.6, smooth((t - TL.T_GO - 0.2) / 1.1)); cx = lerp(160, d4['x'], smooth((t - TL.T_GO) / 1.1)); cy = lerp(98, d4['yb'] - 28, smooth((t - TL.T_GO) / 1.1))
        c = pcam(z, cx, cy)
        img = fr.render(c, L, GRADE_NIGHT, frame=self.fi(t), air=self.hub.air(fr, st, (1,) * 5, op))
        img = img + (1 - img) * smooth((t - TL.END + 0.4) / 0.4)
        cv = self.hud(t, loc=False, pips=True)
        A.draw_fx(cv, p['fx'], *c.w2ui(*head, 4), t)
        if TL.T_BTN <= t < TL.T_GO + 0.2:
            G.item_card(cv, t, TL.T_BTN, 180, 52, None, '周末补觉券', '一次还清所有债', price='骗人', price_t=TL.T_BTN + 1.1,
                        rarity=C('#ff7a6a'), w=124, life=TL.T_GO + 0.2 - TL.T_BTN)
            if t >= TL.T_BTN + 1.15: ui.rubber_stamp(cv, 300, 92, '骗人', t - TL.T_BTN - 1.15, fname='zh12', scale=2, angle=-8)
        return self.compose(img, cv)

    def frame(self, t):
        img = self.ed.frame(min(t, TL.END - 1e-3))
        return ui_over(img, subs_layer(t, TL.L, TL.HL).a, scale=5)

def make(**kw): return Level4(**kw)
