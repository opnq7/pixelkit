"""ACT V · CREDITS v3 renderer 「Claude 制作」: a warm little theatre (pixelkit.credits.Theatre) + pixel spotlight; Claude (lit by the spot) performs
every credit while smooth gold type rises above it.  Timing + performance: credits_tl.py (via timeline)."""
import math
import numpy as np
import timeline as TL
from pixelkit import credits as CR, ui
from pixelkit.characters import claude
from pixelkit.core import C
from pixelkit.anim import clamp01, ramp, ease_io, ease_out3, back_out

T = TL
NOTE_SPR = CR.note(); NOTE_SPR2 = CR.note('#9fe8ff'); HEADSET = CR.headset_spr(); BERET = CR.beret(); PENCIL = CR.pencil()
BX, BY, BW, BH = claude.torso_box()
SY = BY + 4
def _hand(arms, side='R'):
    return claude.arm_spec(arms)[side][1]


class Credits:
    def __init__(self, bobber, OW=1920, OH=1080):
        self.st = CR.Theatre(OW, OH, floor_y=T.FLOOR_Y)
        self.bob = bobber
        self.OW, self.OH = OW, OH
        self.card_final = CR.stats_card(0.0, T.CARD_ROWS, [1, 1, 1, 1], big_k=1.0, crack=1.0)
        self.toast = CR.mini_card('鱼获：0')
        w = CR.text_w('一个相信它的人类', 'serif', 50)
        self.thx_x = 960 - 92                                   # line + stamp centred as a group
        self.stamp_xy = ((self.thx_x + w / 2) / 4 + 46, (360 + 31) / 4)

    # ------------------------------------------------------------------ Claude + props (world sprites)
    def claude_sprites(self, d):
        p = claude.draw(face=d['face'], arms=d['arms'], phase=d['phase'], led=d['led'], led_k=d['led_k'], look=d['look'],
                        tilt=d['tilt'], head_dy=int(round(d['hdy'])), ant=d['ant'], headset=d['headset'], pose=d['pose'],
                        squash=d['squash'])
        x = d['x']
        foot = (claude.SIT_Y if d['pose'] == 'sit' else claude.FOOT_Y)
        hy = T.FLOOR_Y - (foot - claude.AY) + d['dy']            # head top (anchor) in world px
        tx, ty = x - p.ax, hy - p.ay
        sq_x = p.body.cv.a.shape[1] / claude.SW; sq_y = p.body.cv.a.shape[0] / claude.SH
        def at(sx, sy): return tx + sx * sq_x, ty + sy * sq_y
        hdy = int(round(d['hdy']))
        body = (p.body.cv.a, p.body.E, tx, ty); hands = (p.hands.cv.a, p.hands.E, tx, ty)
        front, mid = [], []
        if d['clapper'] is not None:
            hx_, hy_ = at(*_hand('present'))
            mid.append((CR.clapper(d['clapper']), None, hx_ - 1, hy_ - 17))
        if d['bobber']:
            a, e = self.bob
            bx_, by_ = at((BX + BW / 2), SY + 6)
            mid.append((a, e, bx_ - a.shape[1] / 2, by_ - a.shape[0] + 6))
        if d['pencil'] is not None:
            dx, dy, al = d['pencil']
            front.append((PENCIL, None, x - 30 + dx, hy + 9 + hdy + dy, al))
        if d['beret'] is not None:
            dx, dy, al = d['beret']
            front.append((BERET, None, x - 15 + dx, hy - 6 + hdy + dy, al))
        if d.get('headset_fly') is not None:
            a = d['headset_fly']
            front.append((HEADSET, None, x - 7 + 70 * a, hy - 3 - 60 * a + 150 * a * a, 1 - a / 0.55))
        return [body] + mid + [hands] + front, hy

    # ------------------------------------------------------------------ frame
    def frame(self, t):
        u = T.cl(t)
        sk = T.spot_k(t)
        ks = T.lamp_ks(t, len(self.st.lamps))
        fk = sum(ks) / len(ks)
        base = self.st.base(u, sk, house_k=T.house_k(t), foot_k=fk, lamp_ks=ks)
        d = T.cred_state(t)
        cv = ui.UICanvas()
        x = d['x']
        sprites, hy = [], T.FLOOR_Y - 52
        if d['visible']:
            sprites, hy = self.claude_sprites(d)
            lift = -d['dy'] if d['dy'] < 0 else 0
            self.st.contact_shadow(base, x, 30 - lift * 1.2, 1.0 - min(0.6, lift / 12))
        fade = 1 - ramp(u, T.C_FADE0, T.C_END - 0.05, 'io')
        shake = self.ui_layer(cv, u, d, x, hy)
        fg = self.st.audience(u, T.audience_state(t), light=T.front_light(t) * fade)
        img = self.st.compose(base, sprites, cv.a, spot_k=sk, shake=shake, fg=fg, emis0=self.st.foot_emis(fk))
        self.type_layer(img, u, fade)
        return img

    # ------------------------------------------------------------------ pixel UI (world px, unlit)
    def ui_layer(self, cv, u, d, x, hy):
        sh = (0, 0)
        ui.dust_puff(cv, T.X_MARK - 8, T.FLOOR_Y, u - T.C_RUN1, life=0.5, n=7, spread=16)
        if T.C_RUN0 < u < T.C_RUN1:                       # tiny kicks of dust while running
            k = int((u - T.C_RUN0) * 7.3)
            ui.dust_puff(cv, x - 10, T.FLOOR_Y, (u - T.C_RUN0) - k / 7.3, life=0.3, n=3, spread=5)
        CR.twinkles(cv, x, hy - 4, u, T.C_LOOKUP + 0.35, n=5, spread=20, seed=1)
        # -------- roles: a coin each, COMBO, notes, steam, render bar
        Ti = T.C_ROLE_T; n = T.role_n(T.T_CRED + u)
        for i, t0 in enumerate(Ti):
            a = u - t0
            if 0 <= a < 0.7:
                k = ease_out3(a / 0.7)
                ui.coin(cv, x + 22, hy - 4 - 24 * k, a, alpha=1 - clamp01((a - 0.45) / 0.25))
        if n >= 2 and u < T.C_ROLES_OUT + 0.3:
            CR.combo(cv, 352, 178, n, u - Ti[n - 1], alpha=1 - clamp01((u - T.C_ROLES_OUT) / 0.3))
        if n >= 5 and u < T.C_SHAKE:
            for j in range(int((u - Ti[4]) / (T.C_ROLE_DT / 2)) + 1):
                a = u - (Ti[4] + j * (T.C_ROLE_DT / 2))
                if 0 <= a < 1.1:
                    side = -1 if j % 2 else 1
                    nx = x + side * (26 + 8 * a) + 2 * math.sin(a * 7 + j)
                    cv.blit(NOTE_SPR if j % 3 else NOTE_SPR2, nx, hy + 4 - 26 * a, alpha_mul=min(1, a * 6) * (1 - clamp01((a - 0.7) / 0.4)))
        if n >= 8 and u < T.C_RENDER_DONE + 0.6:
            CR.steam_puffs(cv, x - 6, hy - 1, u, Ti[7] + 0.4, T.C_RENDER_DONE, rate=8, seed=3)
            k = clamp01((u - Ti[7]) / (T.C_RENDER_DONE - Ti[7]))
            k = k ** 2.2 if k < 0.92 else k                                  # stalls at the end, like every render
            al = 1 - clamp01((u - T.C_RENDER_DONE - 0.35) / 0.25)
            bw = 34; bx = int(x - bw / 2); by = int(hy - 26)
            cv.rect(bx - 1, by - 1, bw + 2, 6, ui._a(C('#14121e'), al)); cv.rect(bx, by, bw, 4, ui._a(ui.CYAN_D, al))
            cv.rect(bx, by, int(round(bw * min(1, k))), 4, ui._a(ui.GOLD if u >= T.C_RENDER_DONE else ui.CYAN, al))
            pct = '100%' if u >= T.C_RENDER_DONE else f'{int(k * 99)}%'
            cv.text(bx + bw + 4, by - 3, pct, ui._a(ui.CREAM, al), 'silkb')
        CR.twinkles(cv, x, hy + 14, u, T.C_RENDER_DONE, n=7, spread=26, seed=2)
        CR.twinkles(cv, x, hy + 10, u, Ti[3] + 0.2, n=4, spread=18, seed=4)
        # -------- cast: 鱼获：0
        a = u - T.C_FISH_TOAST
        if a >= 0 and u < T.C_CAST_OUT + 0.3:
            k = ui.pop_k(a) * (1 - clamp01((u - T.C_CAST_OUT) / 0.3))
            if k > 0.02:
                ui.blit_scaled(cv, self.toast, 318, (464 + 22) / 4 + 4 * (1 - min(1, a / 0.2)), k)
        # -------- stats card
        if T.C_CARD <= u < T.C_SHATTER:
            rows_k = [clamp01((u - r) / 0.45) for r in T.C_CARD_ROWS]
            big_k = clamp01((u - T.C_BIG) / 0.35)
            crack = ease_out3(clamp01((u - T.C_FLICK) / (T.C_SHATTER - T.C_FLICK)))
            spr = CR.stats_card(u, T.CARD_ROWS, rows_k, big_k=big_k, crack=crack)
            k = ui.pop_k(u - T.C_CARD, t_in=0.2)
            wob = 3 * math.sin((u - T.C_FLICK) * 40) * math.exp(-(u - T.C_FLICK) * 8) if u >= T.C_FLICK else 0
            ui.blit_scaled(cv, spr, T.CARD_X + spr.shape[1] / 2 + wob, T.CARD_Y + spr.shape[0] / 2, k)
            if u >= T.C_FLICK and u < T.C_FLICK + 0.1: sh = (4, -3)
        elif T.C_SHATTER <= u < T.C_DISC1 + 0.5:
            a = u - T.C_SHATTER
            ui.shatter(cv, self.card_final, T.CARD_X, T.CARD_Y, a, floor_y=T.FLOOR_Y + 2, seed=7)
            if a < 0.1: sh = ((9, -6), (-7, 5), (4, -2))[min(2, int(a / 0.034))]
        # -------- 批准 stamp
        a = u - T.C_STAMP
        if a >= -0.1 and u < T.C_THX_OUT + 0.4:
            al = 1 - clamp01((u - T.C_THX_OUT) / 0.35)
            imp = ui.rubber_stamp(cv, self.stamp_xy[0], self.stamp_xy[1], '批准', a, fname='zh10', scale=2, angle=-4,
                                  wear=0.04, alpha=al, seed=5)
            if imp > 0: sh = (0, int(round(6 * imp)))
        CR.twinkles(cv, x, hy + 8, u, T.C_HEART + 0.02, n=6, spread=24, col=C('#ff8fa8'), seed=6)
        # -------- on leave: status badge, auto-reply, zzz, ding
        if u >= T.C_OFF - 0.45:
            ub = back_out(clamp01((u - T.C_OFF + 0.45) / 0.3))
            flip = abs((u - T.C_OFF) / 0.12) if T.C_OFF - 0.12 <= u < T.C_OFF + 0.12 else 1.0
            state = 'off' if u >= T.C_OFF else 'online'
            pulse = 3.0 * (1 - ramp(u, T.C_OFF, T.C_OFF + 0.6)) if u >= T.C_OFF else 0.0
            al = min(1, ub * 1.5) * (1 - ramp(u, T.C_FADE0, T.C_END - 0.1))
            ui.status_badge(cv, int(round(472 + (1 - ub) * 120)), 8, state, alpha=al, pulse=pulse, flip=flip)
        if u >= T.C_AUTO:
            ui.auto_bubble(cv, x - 18, hy - 12, u - T.C_AUTO, life=T.C_AUTO_LIFE, side=-1,
                           text='自动回复：Claude 休假中。彩蛋在后面，请稍等～')
        ui.zzz(cv, x + 16, hy + 2, u, T.C_ZZZ, T.C_DING - 0.75)
        a = u - T.C_DING
        if 0 <= a < 0.9:
            k = ui.pop_k(a, 0.75)
            if k > 0.02:
                al = 1 - clamp01((a - 0.6) / 0.3)
                cv.text(int(x - 36), int(hy - 18 - 3 * min(1, a / 0.2)), '叮', ui._a(ui.GOLD, al), 'zh10')
                for j, (ddx, ddy) in enumerate(((-3, 2), (13, 2), (5, -4))):
                    if a < 0.35: cv.px(int(x - 36 + ddx), int(hy - 18 + ddy), ui._a(ui.CREAM, 1 - a / 0.35))
        return sh

    # ------------------------------------------------------------------ smooth type (output px)
    def type_layer(self, img, u, fade):
        if fade <= 0: return
        # header 制作 / Claude, glides up when the roles start
        a, dy = CR.pop(u, T.C_HEAD, T.C_ROLES_OUT, d_in=0.5)
        if a > 0:
            m = ease_io(clamp01((u - T.C_HEAD_UP0) / (T.C_HEAD_UP1 - T.C_HEAD_UP0)))
            CR.line(img, '制作', 'sans', 26 - 4 * m, 960, 300 - 232 * m + dy, col=CR.GREY_F, alpha=a * fade, tracking=0.6)
            sh = (u - T.C_HEAD - 0.25) / 0.7
            CR.line(img, 'Claude', 'it', 110 - 34 * m, 960, 338 - 240 * m + dy, gold=True, glow=0.45 * a, alpha=a * fade,
                    shine=sh if 0 <= sh <= 1 else None)
        for i, (role, _) in enumerate(T.ROLES):
            CR.credit_row(img, u, T.C_ROLE_T[i], role, 'Claude', 232 + i * 50, t1=T.C_ROLES_OUT + i * 0.025)
        # cast
        a, dy = CR.pop(u, T.C_CAST_H, T.C_CAST_OUT)
        CR.line(img, '演员表', 'sans', 24, 960, 228 + dy, col=CR.GREY_F, alpha=a * fade, tracking=0.6)
        for i, (role, name) in enumerate(T.CAST):
            fish = role == '鱼'
            CR.credit_row(img, u, T.C_CAST_T[i], role, name, 290 + i * 58, t1=T.C_CAST_OUT, name_font='serif', name_px=36,
                          role_font='serif' if role != 'Claude' else 'it', name_gold=not fish, name_col=CR.GREY_F if fish else CR.CREAM_F)
        # disclaimer
        a, dy = CR.pop(u, T.C_DISC1, T.C_DISC_OUT)
        CR.line(img, '本片拍摄期间，没有鱼受到伤害。', 'serif', 42, 960, 330 + dy, alpha=a * fade)
        a, dy = CR.pop(u, T.C_DISC2, T.C_DISC_OUT)
        CR.line(img, '（也没有钓到。）', 'serif', 32, 960, 402 + dy, col=CR.GREY_F, alpha=a * fade)
        # approval
        a, dy = CR.pop(u, T.C_THX0, T.C_THX_OUT)
        CR.line(img, '批准', 'sans', 24, self.thx_x, 316 + dy, col=CR.GREY_F, alpha=a * fade, tracking=0.6)
        a, dy = CR.pop(u, T.C_THX1, T.C_THX_OUT, d_in=0.5)
        sh = (u - T.C_THX1 - 0.15) / 0.7
        CR.line(img, '一个相信它的人类', 'serif', 50, self.thx_x, 360 + dy, gold=True, glow=0.4 * a, alpha=a * fade,
                shine=sh if 0 <= sh <= 1 else None)
