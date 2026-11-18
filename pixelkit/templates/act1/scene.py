"""ACT I renderer: make() -> object with .frame(t) -> float RGB (1080, 1920, 3).

Shots (see timeline.py):  day 0-21.0 | clock 21.0-22.55 | sunset 22.55-37.0 | night 37.0-41.4 | title 41.4-45.6
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/act1'))
import numpy as np
from pixelkit.sets.office import Office
from pixelkit.sets import props as P, dressing as DR
from pixelkit.core import sel_out
from pixelkit.sets.inserts import ClockInsert
from pixelkit.scene import World, GLayer, make_state, dim_blur
from pixelkit.camera import Cam
from pixelkit.particles import DustField
from pixelkit.characters import claude
from pixelkit.core import C, Canvas, scale_nearest, text_width
from pixelkit.anim import clamp01, ramp, back_out, ease_out3, ease_io, ease_in3, shake, Track
from pixelkit.light import lerp_tod
from pixelkit.titles import TitleCard
from pixelkit import blocks, ui, edit
from pixelkit import perform as PF
import timeline as TL

GLASS = np.array(C('#1c2b30')[:3], np.uint8); FLASH = np.array(C('#e9fbff')[:3], np.uint8)
NAVYT = C('#000080'); INKT = C('#1a1a1a'); GREY = C('#6a6a6a')
U4 = 4


# ====================================================================== shared office machinery
class OfficeBase:
    def _setup(self, OW, OH, tod, clock, lights_on=0.0, exit_on=1.0, rays=True):
        self.OW, self.OH = OW, OH
        self.o = Office()
        self.bg = self.o.background(clock=clock, lights_on=lights_on, exit_on=exit_on, tod=tod, dressing=True)   # v0.8: same lived-in office as Act V
        self.pen = sel_out(DR.pen_cup('#3f6fb0').rgba, 0.7)
        self.note = P.sticky('#f6d860', w=7, h=7, lines=2, seed=9).rgba
        self.tod = tod
        self.sun = make_state(tod)['sun']
        self.w = World(self.o.room, self.o.windows, OW=OW, OH=OH)
        self.w.set_background(self.bg, self.sun)
        self.rays = self.w.rig.god_rays(self.sun, self.o.windows, scale=0.25, steps=40) if rays else None
        self.chair = self.o.chair_sprite()

    def mk_cam(self, z, cx, cy, sx=0.0, sy=0.0):
        c = Cam(z, cx, cy, 0, 0, OW=self.OW, OH=self.OH).clamp()
        c.sx, c.sy = sx * self.OW / 1920, sy * self.OW / 1920
        return c

    def monitor_points(self, t, k_mul=1.0, r=34):
        on, band, flash = TL.monitor(t)
        pts = []
        if on > 0:
            k = (0.55 * band + 0.6 * flash) * k_mul
            pts.append(dict(x=197, y=138, r=r, col=(0.30, 0.66, 0.92), k=k, power=1.5, layers=('mid',)))
            pts.append(dict(x=197, y=138, r=r * 1.75, col=(0.20, 0.45, 0.70), k=0.25 * k, power=1.6, layers=('bg',)))
        return pts

    @staticmethod
    def perf_state(t):
        """v0.8 backport of the v0.7 performance layer onto the approved Act I states (timing untouched):
        poses on twos (not in the time-lapse), 1 px breathing, half-lid in-betweens around blinks, a springy
        antenna on every hop, a curious head tilt on the '?'."""
        lapse = TL.T_LAPSE0 <= t < TL.T_LAPSE1
        q = t if lapse else PF.on_twos(t)
        s = TL.claude_state(q)
        if s['face'] in ('normal', 'happy', 'focus', 'wide', 'q') and s['glow'] > 0:
            for dt in (-1 / 15, 1 / 15):
                if TL.claude_state(q + dt)['face'] == 'blink': s['face'] = 'half'; break
        awake = s['glow'] > 0 and s['face'] not in ('closed',)
        s['hdy'] = PF.breath_px(q, 3.6) if (awake and not lapse and s['dy'] == 0 and s['arms'] in ('rest', 'shrug')) else 0
        kicks = [(TL.T_WAKE, 3.0), (TL.T_HOP_LAND, -2.5), (TL.T_1800 + 0.02, 3.5), (TL.T_1800 + 0.34, -2.5),
                 (TL.T_Q - 0.05, 2.5), (TL.T_BIG, -2.0)]
        sp = PF.wobbles(t, kicks, freq=3.6, decay=2.6)
        s['ant'] = (int(round(sp)), int(round(-abs(0.5 * sp))))
        s['tilt'] = PF.spring_follow(lambda x: 7.0 if TL.T_Q <= x < TL.T_DICT - 0.2 else 0.0, q, freq=2.0, zeta=0.5,
                                     window=1.2, dt=1 / 120) if TL.T_Q - 0.1 <= t < TL.T_DICT + 1.2 else 0.0
        return s

    def claude_parts(self, t, spark_k=1.0):
        s = self.perf_state(t)
        hx, hy = TL.HEAD
        p0 = claude.draw(face='normal', arms='rest')
        dy_sprite = int(round(TL.DESK_Y - (hy - p0.ay) - s['dy']))
        p = claude.draw(face=s['face'], arms=s['arms'], phase=s['phase'], led='online', led_k=s['led_k'], look=s['look'],
                        glow=s['glow'], desk_y=dy_sprite, squash=0.0, spark_k=spark_k, tilt=s['tilt'], head_dy=s['hdy'],
                        ant=s['ant'], tear=s.get('tear', 0.0))
        body, hands = p.body, p.hands
        x0, y0 = hx - p.ax, hy - p.ay + s['dy']
        sq = s['squash']
        if abs(sq) > 1e-3:
            sx, sy = 1.0 + sq * 0.6, 1.0 - sq
            H, W = body.cv.a.shape[:2]
            bottom = y0 + H
            outs = []
            for sp in (body, hands):
                outs.append((scale_nearest(sp.cv.a, sx, sy), scale_nearest(sp.E, sx, sy)))
            nh, nw = outs[0][0].shape[:2]
            x0 = hx - claude.AX * nw / W; y0 = bottom - nh
            return outs[0], outs[1], x0, y0, s
        return (body.cv.a, body.E), (hands.cv.a, hands.E), x0, y0, s

    def desk_and_claude(self, t, monitor=None, lamp_on=0.0, spark_k=1.0, under_hands=None, after_hands=None):
        """chair -> Claude body -> desk (+ CRT band) -> under_hands(mid) -> hands -> after_hands(mid)."""
        o = self.o
        mid = GLayer()
        mid.put(self.chair.rgba, 232, 128, o.Z['chair'])
        (brgba, bE), (hrgba, hE), x0, y0, s = self.claude_parts(t, spark_k)
        mid.put(brgba, x0, y0, o.Z['claude'], E=bE)
        on, band, flash = TL.monitor(t) if monitor is None else monitor
        o.draw_desk(mid, monitor_on=on, screen_lines=TL.screen_lines(t), lamp_on=lamp_on,
                    extra=[(self.pen, 219, 155, 0.2, None), (self.note, 212, 121, 1.0, None)])
        if on > 0 and band < 1.0:
            sx, sy, sw, sh = o.A['monitor_screen']
            half = max(0.5, sh / 2 * band); cyc = sy + sh / 2
            for yy in range(sy, sy + sh):
                inside = abs(yy + 0.5 - cyc) <= half
                row = mid.cv.a[yy, sx:sx + sw]; m = row[:, 3] > 0
                if not inside:
                    row[m, :3] = GLASS; mid.E[yy, sx:sx + sw][m] = 0.0
                elif flash > 0:
                    row[m, :3] = (row[m, :3] * (1 - flash) + FLASH * flash).astype(np.uint8)
                    mid.E[yy, sx:sx + sw][m] = np.maximum(mid.E[yy, sx:sx + sw][m], flash)
        if under_hands: under_hands(mid)
        mid.put(hrgba, x0, y0, o.Z['desk'], E=hE)
        if after_hands: after_hands(mid)
        return mid, s


def feed(cv, t, msgs, fast_lift=0.12, alpha_mul=1.0):
    """chat feed: every message is lifted by the later messages of its own group."""
    for m in msgs:
        age = t - m['t_in']
        if age < 0: continue
        alpha = (1.0 - ramp(t, m['t_out'], m['t_out'] + 0.25)) * alpha_mul
        if alpha <= 0.01: continue
        lift = 0.0
        for n in msgs:
            if n is m or n['group'] != m['group'] or n['t_in'] <= m['t_in'] or t <= n['t_in']: continue
            lt = fast_lift if n.get('fast') else 0.22
            lift += ease_out3((t - n['t_in']) / lt) * (TL.msg_h(n) + 4)
        lift += 10 * ramp(t, m['t_out'], m['t_out'] + 0.25)
        y = m['bot'] - TL.msg_h(m) - lift
        if y < -40: continue
        k = ui.pop_k(age, 1e9, t_in=0.10 if m.get('fast') else 0.16)
        ui.chat_bubble(cv, TL.FEED_X, int(round(y)), m['lines'], avatar=m['avatar'], k=k, name=m['name'], alpha=alpha)


def narration(cv, t):
    r = TL.box_at(t)
    if r is None: return
    bx, ln, k, zn, en_n = r
    if k <= 0: return
    ui.claude_box(cv, ln['zh'], ln['en'], ln['face'], ln['mouth'], open_t=k, zh_n=zn, en_n=en_n, t=t,
                  show_next=t > ln['t_end'] + 0.35)


def ff_badge(cv, x, y, t, alpha=1.0, label='x 180'):
    """fast-forward HUD badge (time-lapse)."""
    if alpha <= 0: return
    ui._hud_panel(cv, x, y, 60, 16, alpha)
    col = ui._a(ui.GOLD if (t * 4) % 1 < 0.6 else C('#fff3df'), alpha)
    for k in range(2):
        bx = x + 6 + k * 7
        for i in range(5):
            hh = 9 - 2 * i
            if hh > 0: cv.vline(bx + i, y + 4 + i, hh, col)
    cv.text(x + 24, y + 5, label, ui._a(C('#fff3df'), alpha), 'silkb')


# ====================================================================== A + B : day shot (0 - 21.0)
class DayShot(OfficeBase):
    def __init__(self, OW=1920, OH=1080, shared=None):
        self._setup(OW, OH, 'golden', (16, 30))
        self.dust = DustField(self.o.room, n=1000, size=(0.6, 1.4))
        self.fg = (self.o.foreground(), 1.18, 0.8, (0.35, 0.30, 0.42))
        self.sim, self.hero = shared['sim']
        self.pop = ui.hud_popup('今日已处理', TL.V_SLAM, 'TASKS DONE')
        self.cw_slam = max(106, text_width(ui.fmt_int(TL.V_SLAM), 'p2p') + 24)

    def cam(self, t):
        z, cx, cy, sx, sy, zb = TL.cam_params(t)
        return self.mk_cam(z, cx, cy, sx, sy), zb

    def state(self, t, cam):
        amb_k, sun_k = TL.light(t)
        st = make_state('golden')
        lk = TL.lapse_k(t)
        if lk > 0:
            L = lerp_tod('golden', 'sunset', lk)
            st['sun_color'] = L['sun'][1]; st['sun_int'] = L['sun'][2]
            st['amb_color'] = L['amb'][0]; st['amb'] = L['amb'][1]
        st['sun_k'] = sun_k
        st['amb'] = st['amb'] * amb_k
        st['bg_emis_k'] = amb_k
        st['bounce_k'] = 1.0
        zf = clamp01((cam.zoom - 1.0) / 2.35)
        st['rays'] = (2.0 - 1.0 * zf) * (1 + 0.25 * lk)
        st['rays_map'] = (self.rays, 0.5)
        st['emis_bloom'] = 0.4 + 0.9 * (1 - amb_k)
        pts = self.monitor_points(t)
        lkd = TL.led_k(t)
        if amb_k < 0.999:
            pts.append(dict(x=259.5, y=137, r=5.5, col=(0.35, 1.0, 0.55), k=0.55 * lkd * (1 - amb_k), power=1.4, layers=('mid',)))
        st['points'] = pts
        if TL.in_freeze(t):
            g = dict(st['grade']); u = clamp01((t - TL.T_FREEZE) / 0.05)
            g['sat'] = g['sat'] * (1 - 0.16 * u); g['vignette'] = g['vignette'] + 0.08 * u
            st['grade'] = g
        return st, sun_k

    def mid(self, t):
        tw = TL.tau(t); sim = self.sim
        def under(mid):
            blocks.put_bodies(mid, sim, tw, TL.Zof, only={'desk'}, hide_fn=lambda b: getattr(b, 'tag', None) == 'tower')
            for b, x, y, lane, sq in sim.at(tw):
                if getattr(b, 'tag', None) != 'tower': continue
                spr, E = b.spr.rgba, b.spr.E
                if sq > 0.02:
                    h, w = spr.shape[:2]
                    nh = max(2, int(round(h * (1 - 0.18 * sq)))); nw = int(round(w * (1 + 0.10 * sq)))
                    spr = scale_nearest(spr, nw / w, nh / h); E = scale_nearest(E, nw / w, nh / h)
                    x = x - (nw - w) / 2; y = y + (h - nh)
                mid.put(spr, x + TL.tower_dx(t, y), y, TL.Zof('desk'), E=E)
        def after(mid):
            blocks.put_bodies(mid, sim, tw, TL.Zof, only={'floor', 'floor2', 'floor3'})
        return self.desk_and_claude(t, spark_k=TL.light(t)[0], under_hands=under, after_hands=after)

    def ui(self, t, cam, s):
        cv = ui.UICanvas(); tw = TL.tau(t)
        U = lambda x, y: tuple(float(v) for v in cam.w2ui(x, y, U4))
        hx, hy = TL.HEAD
        hud_a = 1.0 - ramp(t, TL.T_CRASH0, TL.T_CRASH0 + 0.16)
        feed(cv, t, [m for m in TL.FEED if m['group'] <= 2], alpha_mul=hud_a)
        # Claude's '好的！'
        for to in TL.OKS:
            age = t - to
            if 0 <= age < 0.95:
                side, dy = TL.OK_META.get(to, (1, 0))
                ax, ay = U(hx + 15 * side, hy + 3 + dy)
                ui.speech_bubble(cv, ax, ay, '好的！', age, 0.95, side=side, with_coin=True, t=t)
        ax, ay = U(hx + 15, hy + 3)
        if s['stars'] > 0:
            cx, cy = U(hx, hy - 4)
            r = 13 * cam.zoom / 2.6
            ui.dizzy_stars(cv, cx, cy, t, 3, r, r * 0.3, 2.4, alpha=s['stars'])
        bt = TL.MSGS[2]['t_land']
        if 0 <= t - bt < 0.12:
            cx, cy = U(hx + 3, hy - 3)
            ui.burst_lines(cv, cx, cy, 10 + 60 * (t - bt), 18 + 90 * (t - bt), 9, ui.CREAM, 1.0 - (t - bt) / 0.12, 0.3)
        # HUD counter (hidden while the big popup is up)
        u_c = back_out(clamp01((t - TL.T_HUD_COUNTER) / 0.32)) if t >= TL.T_HUD_COUNTER else 0.0
        slot = (440, 30)
        popup_up = TL.T_SLAM <= t < TL.T_POP_END
        if u_c > 0:
            xr = 472 + (1 - u_c) * 130
            val = TL.counter_value(t)
            bump = 0.0
            for ob in TL.OK_BURSTS:
                dt = tw - (ob['tw'] + TL.COIN_DELAY + TL.COIN_FLY)
                if 0 <= dt < 0.12: bump = max(bump, 1 - dt / 0.12)
            if TL.T_COIN1 <= t < TL.T_COIN1 + 0.25: bump = max(bump, 1 - (t - TL.T_COIN1) / 0.25)
            if TL.T_POP_END <= t < TL.T_POP_END + 0.3: bump = max(bump, 1 - (t - TL.T_POP_END) / 0.3)
            a = min(1, u_c * 1.5) * hud_a * (0.0 if popup_up else 1.0)
            slot = ui.hud_counter(cv, int(round(xr)), 8, val, alpha=a, bump=bump, t=tw)
        if t >= TL.T_HUD_TIME:
            u_t = back_out(clamp01((t - TL.T_HUD_TIME) / 0.32))
            hh = '16:30' if t < TL.T_LAPSE0 else TL.hud_hhmm(t)
            fl = 0.5 * (1 - ramp(t, TL.T_LAPSE1, TL.T_LAPSE1 + 0.3)) if t >= TL.T_LAPSE1 else 0.0
            ui.hud_time(cv, int(round(8 - (1 - u_t) * 90)), 8, hh, day='周五', day_en='FRI', alpha=min(1, u_t * 1.5) * hud_a,
                        flash=fl)
        # fast-forward badge during the time-lapse
        if TL.T_LAPSE0 - 0.1 <= t < TL.T_CRASH0 + 0.2:
            a = ramp(t, TL.T_LAPSE0 - 0.1, TL.T_LAPSE0 + 0.1) * hud_a
            ff_badge(cv, 78, 8, t, a)
        # rain '好的！' + coins
        for ob in TL.OK_BURSTS:
            age = tw - ob['tw']
            if age < 0 or age > TL.OK_LIFE + TL.COIN_FLY + TL.COIN_DELAY: continue
            px, py = U(hx + ob['dx'], hy + 8 + ob['dy'])
            if age < TL.OK_LIFE:
                ui.speech_bubble(cv, px, py, '好的！', age, TL.OK_LIFE, side=ob['side'], with_coin=False, fname='zh10', rise=4, t=tw)
            uu = (age - TL.COIN_DELAY) / TL.COIN_FLY
            if 0 <= uu <= 1 and u_c > 0 and not popup_up:
                ui.fly_coin(cv, (px + 6 * ob['side'], py - 14), slot, uu, tw, arc=30)
        # the freeze
        if TL.in_freeze(t) or (TL.T_RESUME <= t < TL.T_RESUME + 0.05):
            age = t - TL.T_TINY_OK
            if 0 <= age < 0.36: ui.tiny_bubble(cv, ax - 4, ay + 2, '好的！', age, 0.36)
            uu = (t - TL.T_COIN0) / (TL.T_COIN1 - TL.T_COIN0)
            if 0 <= uu <= 1: ui.fly_coin(cv, (ax + 2, ay - 8), slot, uu, t, arc=22)
        # 3,000,000,000 popup -> shrinks into the HUD counter
        if popup_up:
            age = t - TL.T_SLAM
            pw = self.pop.shape[1]
            c0 = (240.0, 104.0)
            if t < TL.T_POP_FLY:
                sc = 0.35 + 0.65 * back_out(clamp01(age / 0.17), 2.4)
                pos = c0
            else:
                u = ease_in3(clamp01((t - TL.T_POP_FLY) / (TL.T_POP_END - TL.T_POP_FLY)))
                s1 = self.cw_slam / pw
                sc = 1.0 + (s1 - 1.0) * u
                tgt = (472 - self.cw_slam / 2, 22.0)
                pos = (c0[0] + (tgt[0] - c0[0]) * u, c0[1] + (tgt[1] - c0[1]) * u - 18 * math.sin(math.pi * u))
            if age < 0.22:
                ui.burst_lines(cv, c0[0], c0[1], 70 + 260 * age, 100 + 420 * age, 16, ui.GOLD, 1 - age / 0.22, 0.1)
            if age < 0.6:
                for k in range(6):
                    an = k / 6 * 2 * math.pi + 0.4
                    rr = 95 + 60 * age
                    ui.star(cv, int(c0[0] + rr * math.cos(an)), int(c0[1] + rr * 0.45 * math.sin(an)), alpha=1 - age / 0.6,
                            small=k % 2 == 0)
            ui.blit_scaled(cv, self.pop, pos[0], pos[1], sc)
        narration(cv, t)
        return cv.a

    def frame(self, t):
        cam, zb = self.cam(t)
        st, sun_k = self.state(t, cam)
        mid, s = self.mid(t)
        tw = TL.tau(t)
        dust = None
        if sun_k > 0.01:
            dust = self.dust.render_out(tw, self.sun, self.o.windows, cam, gain=1.6 * sun_k, px=1.4 * self.OW / 1920,
                                        occluder=(mid.alpha(), mid.Z))
        patches = None
        if t >= TL.T_LAPSE0:
            m = TL.wall_minutes(t)
            ss = 57.0 if t >= TL.T_LAPSE1 else None
            patches = [self.o.clock_patch(int(m // 60), int(m % 60), ss)]
        post_ui = None
        if zb > 0:
            X, Y = cam.w2o(*TL.CLOCK_C)
            post_ui = lambda img: edit.zoom_blur(img, zb, float(X) / self.OW, float(Y) / self.OH)
        uia = self.ui(t, cam, s)
        return self.w.render(cam, st, mid=mid, fg=self.fg, glow_out=dust, ui=uia, frame=int(round(t * TL.FPS)),
                             bg_patches=patches, post_ui=post_ui)


# ====================================================================== C : clock insert (21.0 - 22.55)
class ClockShot:
    def __init__(self, OW=1920, OH=1080):
        self.ci = ClockInsert(tod='sunset', OW=OW, OH=OH)
        self.OW, self.OH = OW, OH

    def frame(self, t):
        a = t - TL.T_INSERT
        z = 1.0 + 0.30 * (1 - ease_out3(clamp01(a / 0.38)))
        z += 0.10 * ease_io(clamp01((t - TL.TICKS[0]) / (TL.T_1800 - TL.TICKS[0])))
        sx = sy = 0.0
        for k, tt in enumerate(TL.TICKS):
            dx, dy = shake(t, tt, 2.0 + 1.5 * k, 0.16, 26.0, 40 + k); sx += dx; sy += dy
        cam = Cam(z, 240, 134, 0, 0, OW=self.OW, OH=self.OH)
        cam.sx, cam.sy = sx * self.OW / 1920, sy * self.OW / 1920
        hh, mm, ss, am = TL.insert_clock(t)
        g = dict(self.ci.grade)
        g['vignette'] = g.get('vignette', 0.3) + 0.10 * ease_io(clamp01((t - TL.TICKS[0]) / 0.6))
        img = self.ci.frame(cam, hh, mm, ss, frame=int(round(t * TL.FPS)), min_angle=am, grade=g)
        zb = 0.13 * (1 - clamp01(a / 0.16)) ** 2
        if zb > 1e-3: img = edit.zoom_blur(img, zb, 0.5, 0.5)
        return img


# ====================================================================== D + E + F : sunset (22.55 - 37.4)
CAL_MONTHS = [(2025, 10), (2025, 11), (2025, 12)] + [(2026, m) for m in range(1, 10)]
MON_ZH = ['', '一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']
MON_EN = ['', 'JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER',
          'DECEMBER']
DICT_R = (82, 14, 316, 188)
CAL_R = (88, 6, 304, 192)

ZOOM_D = Track([(TL.T_1800, 1.0), (TL.T_PUSH0, 1.07, 'io'), (TL.T_PUSH1, 2.6, 'io'), (TL.T_DICT, 2.62), (TL.T_NIGHT, 2.85, 'io')],
               log=True)
CENTER_D = Track([(TL.T_1800, (240.0, 135.0)), (TL.T_PUSH0, (242.0, 132.0), 'io'), (TL.T_PUSH1, (250.0, 135.0), 'io'),
                  (TL.T_NIGHT, (250.0, 135.0))])


def stamp_order():
    wd0, nd = ui.month_info(2025, 10)
    weekdays = [d for d in range(1, nd + 1) if (wd0 + d - 1) % 7 < 5]
    sats = [d for d in range(1, nd + 1) if (wd0 + d - 1) % 7 == 5]
    suns = [d for d in range(1, nd + 1) if (wd0 + d - 1) % 7 == 6]
    return weekdays, sats, suns
WEEKDAYS, SATS, SUNS = stamp_order()
T_STAMP = {d: TL.T_STAMP0 + i * TL.STAMP_DT for i, d in enumerate(WEEKDAYS)}
for d in SATS: T_STAMP[d] = TL.T_SAT
for d in SUNS: T_STAMP[d] = TL.T_SUN


class SunsetShot(OfficeBase):
    def __init__(self, OW=1920, OH=1080, shared=None):
        self._setup(OW, OH, 'sunset', (18, 0))
        self.dust = DustField(self.o.room, n=900, size=(0.6, 1.4))
        self.fg = (self.o.foreground(), 1.18, 0.8, (0.33, 0.26, 0.40))
        self.sim, _ = shared['sim']; self.wsim = shared['wsim']
        self.tw_c = self.sim.t_end
        items = self.sim.at(self.tw_c)
        self.poof = blocks.Poof(items, TL.T_POOF, TL.Zof, per=12, seed=5,
                                stagger=lambda x, y: abs(x + 10 - TL.HEAD[0]) / 240.0 * 0.10)
        self.v_counter = TL.counter_value(TL.T_1800)

    def cam(self, t):
        z = ZOOM_D(t); cx, cy = CENTER_D(t)
        sx = sy = 0.0
        for (t0, amp, dur, seed) in [(TL.T_POOF, 6.0, 0.35, 11), (TL.T_Q - 0.05, 3.0, 0.2, 12), (TL.T_SAT, 4.0, 0.22, 13),
                                     (TL.T_SUN, 5.0, 0.25, 14), (TL.T_BIG, 14.0, 0.55, 15)]:
            a, c = shake(t, t0, amp, dur, 29.0, seed); sx += a; sy += c
        return self.mk_cam(z, cx, cy, sx, sy)

    def win_k(self, t):
        """0..1 presence of the desktop windows (dims + blurs the room)."""
        return ramp(t, TL.T_DICT, TL.T_DICT + 0.3, 'io')

    def state(self, t, cam):
        st = make_state('sunset')
        st['sun_k'] = 1.0; st['bounce_k'] = 1.0
        zf = clamp01((cam.zoom - 1.0) / 2.35)
        st['rays'] = 2.2 - 1.0 * zf
        st['rays_map'] = (self.rays, 0.5)
        st['emis_bloom'] = 0.55
        st['points'] = self.monitor_points(t, 1.15)
        return st

    def clear_flash(self, b):
        f = 0.0
        for tf in TL.T_CLEAR_FL:
            if t_now[0] >= tf: f = max(f, 1 - (t_now[0] - tf) / 0.11)
        if t_now[0] >= TL.T_CLEAR_FL[-1]: f = max(f, 0.65)
        return clamp01(f)

    def mid(self, t):
        t_now[0] = t
        work = t < TL.T_POOF
        fl = self.clear_flash if t >= TL.T_CLEAR_FL[0] else None
        def under(mid):
            if work: blocks.put_bodies(mid, self.sim, self.tw_c, TL.Zof, only={'desk'}, flash_fn=fl)
            blocks.put_bodies(mid, self.wsim, t, TL.Zof, only={'desk'})
        def after(mid):
            if work: blocks.put_bodies(mid, self.sim, self.tw_c, TL.Zof, only={'floor', 'floor2', 'floor3'}, flash_fn=fl)
            blocks.put_bodies(mid, self.wsim, t, TL.Zof, only={'floor', 'floor2', 'floor3'})
            self.poof.draw(mid, t)
        return self.desk_and_claude(t, under_hands=under, after_hands=after)

    # ---------------------------------------------------------------- desktop windows
    def open_fx(self, cv, cam, t, t0, rect, d=0.26, closing=False):
        sx, sy, sw, sh = self.o.A['monitor_screen']
        x0, y0 = cam.w2ui(sx, sy, U4); x1, y1 = cam.w2ui(sx + sw, sy + sh, U4)
        src = (float(x0), float(y0), float(x1 - x0), float(y1 - y0))
        k = clamp01((t - t0) / d)
        if closing: k = 1 - k
        if 0 < k < 1: ui.w95_open_fx(cv, src, rect, k)

    DICT_WORDS = ['周报', '周边', '周到', '周刊', '周末', '周年', '周期', '周围', '周旋']
    def dict_window(self, cv, t):
        x, y, w, h = DICT_R
        D = ui.DOC
        ui.soft_shadow(cv, x, y, w, h)
        cx, cy, cw, ch = ui.w95_window(cv, x, y, w, h, '现代汉语词典 - 辞典.exe', icon=lambda c, ix, iy: ui._icon(c, ix, iy - 1, 'book'))
        yy = ui.w95_menubar(cv, cx, cy, cw, ('文件', '编辑', '查看', '收藏', '帮助'))
        # search row
        sy = yy + 3
        cv.text(cx + 5, sy + 3, '查找：', ui.W95['dk'], 'zh10')
        n = sum(1 for tt in TL.T_TYPE if t >= tt)
        caret = (t * 2.2) % 1 < 0.6 and t < TL.T_CLICK
        fx = cx + 38
        ui.w95_field(cv, fx, sy, 178, 17, '', fname='zh12')
        ui._icon(cv, fx + 4, sy + 4, 'search', C('#8a8a96'))
        tx_ = fx + 18
        if n: cv.text(tx_, sy + 3, '周末'[:n], ui.W95['dk'], 'zh12')
        if caret: cv.vline(tx_ + (text_width('周末'[:n], 'zh12') + 1 if n else 0), sy + 3, 11, ui.W95['dk'])
        st = 'pressed' if TL.T_CLICK <= t < TL.T_CLICK + 0.12 else 'hover' if TL.T_CUR1 - 0.06 <= t < TL.T_CLICK else 'idle'
        bx, by, bw, bh = fx + 186, sy, cw - (fx + 186 - cx) - 5, 17
        bc = ui.default_button(cv, bx, by, bw, bh, '查询', st, icon='search')
        # body: word index (left) + entry page (right)
        top = sy + 22; sb_y = y + h - 4 - 13; bot = sb_y - 3
        lw = 62
        ui.w95_panel(cv, cx + 3, top, lw, bot - top)
        sel_on = t >= TL.T_CLICK
        if n == 0:
            cv.text(cx + 9, top + 6, '（词条）', C('#a0a0a8'), 'zh8')
        else:
            words = self.DICT_WORDS
            for i, wd in enumerate(words):
                ry_ = top + 3 + i * 13
                if ry_ + 13 > bot - 3: break
                hit = n >= 2 and wd == '周末'
                if hit and sel_on:
                    cv.rect(cx + 5, ry_, lw - 4, 13, D['navy']); cv.text(cx + 9, ry_ + 1, wd, C('#ffffff'), 'zh10')
                else:
                    if hit: cv.rect(cx + 5, ry_, lw - 4, 13, C('#dfe3f4'))
                    cv.text(cx + 9, ry_ + 1, wd, ui.W95['dk'] if (hit or n < 2) else C('#7a7a84'), 'zh10')
        px, py, pw, ph = cx + lw + 6, top, cw - lw - 9, bot - top
        ui.w95_panel(cv, px, py, pw, ph, D['page'])
        rx, ry = px + 10, py + 7
        if t < TL.T_CLICK:
            cv.text(px + (pw - text_width('输入词语，按「查询」', 'zh8')) // 2, py + ph // 2 - 4, '输入词语，按「查询」', C('#b0b0b8'), 'zh8')
        elif t < TL.T_RESULT:
            cv.text(rx, ry + 2, '查询中', GREY, 'zh10'); ui.spinner_dots(cv, rx + text_width('查询中', 'zh10') + 3, ry + 7, t, GREY)
        else:
            a = t - TL.T_RESULT
            cv.text(rx, ry, '周末', D['navy'], 'zh12'); cv.text(rx + 1, ry, '周末', D['navy'], 'zh12')
            hx0 = rx + text_width('周末', 'zh12') + 6
            cv.text(hx0, ry + 2, 'zhōu mò', C('#4a5aa8'), 'zh10')
            hx1 = hx0 + text_width('zhōu mò', 'zh10') + 4
            ui._icon(cv, hx1, ry + 2, 'speaker', C('#4a5aa8'))
            cv.rrect(hx1 + 14, ry + 1, 14, 13, D['navy'], 2); cv.text(hx1 + 16, ry + 2, '名', C('#ffffff'), 'zh10')
            ui._icon(cv, px + pw - 15, ry + 1, 'star', C('#e0b030') if a >= 0.5 else C('#c8c8d0'))
            cv.hline(rx, ry + 16, pw - 20, D['navy']); cv.hline(rx, ry + 17, pw - 20, D['rule'])
            dy = ry + 22
            hx = rx + text_width('一周中', 'zh12')
            if t >= TL.T_HI0:
                ui.highlight(cv, hx - 1, dy - 1, text_width('不用工作', 'zh12') + 2, 15, ease_io((t - TL.T_HI0) / (TL.T_HI1 - TL.T_HI0)))
            if a >= 0.08: cv.text(rx, dy, '一周中不用工作的日子，', INKT, 'zh12')
            if a >= 0.16: cv.text(rx, dy + 17, '人类通常用来休息。', INKT, 'zh12')
            if a >= 0.26:
                cv.text(rx, dy + 38, 'weekend', D['navy'], 'zh10'); cv.text(rx + text_width('weekend', 'zh10') + 8, dy + 38, 'n.  days off work', GREY, 'zh10')
                cv.rect(rx, dy + 53, 2, 11, D['claude']); cv.text(rx + 6, dy + 53, '例：周末愉快！', GREY, 'zh10')
            if t >= TL.T_HI1 + 0.05:      # red pen circle around 不用工作
                u = clamp01((t - TL.T_HI1 - 0.05) / 0.22)
                ex, ey = hx + text_width('不用工作', 'zh12') / 2, dy + 6
                rxx, ryy = text_width('不用工作', 'zh12') / 2 + 6, 11
                for i in range(int(64 * u)):
                    an = -2.2 + i / 60 * 2 * math.pi
                    cv.px(int(ex + rxx * math.cos(an)), int(ey + ryy * math.sin(an)), ui.STAMP_RED)
                    cv.px(int(ex + rxx * math.cos(an)), int(ey + ryy * math.sin(an)) + 1, ui.STAMP_RED)
        if t < TL.T_CLICK: stt = dict(text='就绪')
        elif t < TL.T_RESULT: stt = dict(text='正在查询', busy=True, col=D['claude'])
        else: stt = dict(text='找到 1 条结果', col=D['green'])
        ui.w95_statusbar(cv, cx, sb_y, cw, [dict(text='共收录 69,000 条'), dict(stt, right='第 7 版')], t)
        # cursor
        if t >= TL.T_DICT + TL.T_DICT_OPEN:
            p0 = (cx + 150, cy + 110); p1 = (bc[0] + 12, bc[1] + 3)
            u = ease_io(clamp01((t - TL.T_CUR0) / (TL.T_CUR1 - TL.T_CUR0)))
            ux, uy = p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u
            if t >= TL.T_RESULT + 0.2:
                v = ease_io(clamp01((t - TL.T_RESULT - 0.2) / 0.4)); ux += 14 * v; uy += 70 * v
            ui.cursor(cv, ux, uy, st == 'pressed', age_press=(t - TL.T_CLICK) if t >= TL.T_CLICK else None)

    def cal_page(self, j, t, W, H, flip_t):
        """month page j (0 = Oct 2025) drawn on its own canvas (client coords)."""
        yr, mo = CAL_MONTHS[j]
        cv = Canvas(W, H, (195, 195, 195, 255))
        cv.rect(0, 0, W, 18, C('#c8352c'))
        cv.text(5, 3, f'{yr}年 {MON_ZH[mo]}', C('#fff3df'), 'zh12')
        cv.text(5 + text_width(f'{yr}年 {MON_ZH[mo]}', 'zh12') + 8, 6, MON_EN[mo], C('#ffd9a0'), 'silkb')
        wd0_, nd_ = ui.month_info(yr, mo); rows = (wd0_ + nd_ + 6) // 7
        cells = ui.cal_grid(cv, 5, 22, yr, mo, cw=40, ch=min(22 if j == 0 else 21, (H - 36) // rows - 1), gap=1)
        wd0, nd = ui.month_info(yr, mo)
        for i, (d, (a, b, ww, hh)) in enumerate(cells.items()):
            col = (wd0 + d - 1) % 7
            if j == 0:
                age = t - T_STAMP[d]; splat = col >= 5
            else:
                age = t - flip_t - 0.0035 * i; splat = False
            ui.rubber_stamp(cv, a + ww / 2 + 1, b + hh / 2 + 3, '工作日', age, angle=((d * 37) % 9 - 4) * (1.6 if col >= 5 else 1),
                            seed=d, splat=splat, from_s=2.4 if col >= 5 else 1.8)
        return cv

    def worked_days(self, t):
        if t < TL.FLIPS[0]:
            return sum(1 for d, tt in T_STAMP.items() if t >= tt)
        n = 31
        for j, ft in enumerate(TL.FLIPS):
            if t >= ft + 0.05: n += ui.month_info(*CAL_MONTHS[j + 1])[1]
        return n

    def cal_window(self, cv, t, ox=0, oy=0):
        x, y, w, h = CAL_R; x += ox; y += oy
        ui.soft_shadow(cv, x, y, w, h)
        cx, cy, cw, ch = ui.w95_window(cv, x, y, w, h, '日历.exe', icon=lambda c, ix, iy: ui._icon(c, ix, iy - 1, 'cal'))
        ch -= 16                                   # status bar below the page
        ui.w95_statusbar(cv, cx, cy + ch + 2, cw, [dict(text=f'工作日 {self.worked_days(t)} 天'),
                         dict(text='休息日 0 天', col=C('#c8352c')), dict(text='下一个假期：未安排', right='提醒 0')], t)
        j = sum(1 for ft in TL.FLIPS if t >= ft)
        ft = TL.FLIPS[j - 1] if j else 0.0
        page = self.cal_page(j, t, cw, ch, ft)
        if j and t - ft < 0.07:             # previous page tears away upwards
            u = (t - ft) / 0.07
            old = self.cal_page(j - 1, t, cw, ch, TL.FLIPS[j - 2] if j >= 2 else 0.0).a
            cut = int(round(ch * (1 - u)))
            if cut > 0:
                page.a[:cut] = old[ch - cut:]
                page.a[cut:cut + 1, :, :3] = 255
        cv.blit(page.a, cx, cy)
        # 全年工作日 counter (header, right)
        n = self.worked_days(t)
        s = f'{n}/365'
        sw = text_width(s, 'p2p')
        col = ui.GOLD if n >= 365 else C('#fff3df')
        cv.text(cx + cw - sw - 6, cy + 6, s, col, 'p2p', shadow=C('#5a1410'))
        cv.text(cx + cw - sw - 6 - text_width('工作日', 'zh10') - 4, cy + 4, '工作日', C('#ffd9a0'), 'zh10')
        # 全年无休
        if t >= TL.T_BIG - 0.1:
            if t >= TL.T_BIG:            # the page washes out so the big stamp reads
                wa = int(150 * ramp(t, TL.T_BIG, TL.T_BIG + 0.06))
                cv.blend_rect(cx, cy + 19, cx + cw, cy + ch, (255, 250, 240, wa))
            ui.rubber_stamp(cv, cx + cw / 2, cy + ch / 2 + 12, '全年无休', t - TL.T_BIG, 'zh12', 3, angle=-12, seed=3,
                            splat=True, from_s=2.2, slam=0.09, wear=0.06, bold=True)

    def ui(self, t, cam, s):
        cv = ui.UICanvas()
        U = lambda x, y: tuple(float(v) for v in cam.w2ui(x, y, U4))
        hx, hy = TL.HEAD
        hud_a = 1.0 - ramp(t, TL.T_DICT, TL.T_DICT + 0.2)
        if hud_a > 0:
            ui.hud_counter(cv, 472, 8, self.v_counter, alpha=hud_a, t=t)
            fl = 1 - ramp(t, TL.T_1800, TL.T_1800 + 0.9)
            pulse = 1 + 0.0 * fl
            ui.hud_time(cv, 8, 8, '18:00', day='周五', day_en='FRI', alpha=hud_a, flash=fl)
        feed(cv, t, TL.WMSGS)
        # '?' over Claude
        if TL.T_Q - 0.05 <= t < TL.T_DICT:
            a = t - TL.T_Q + 0.05
            sc = back_out(clamp01(a / 0.2), 3.0)
            qx, qy = U(hx + 13, hy - 20)
            al = 1 - ramp(t, TL.T_DICT - 0.15, TL.T_DICT)
            spr = Canvas(30, 30); ui.big_text(spr, 2, 1, '？', ui.GOLD, 'zh12', 2, shadow=C('#3b2620'))
            ui.blit_scaled(cv, spr.a, qx, qy - 2 * math.sin(t * 6), sc * cam.zoom / 2.6 * 1.8, al)
        # desktop windows
        if TL.T_DICT <= t < TL.T_DICT_CLOSE + 0.3:
            if t < TL.T_DICT + TL.T_DICT_OPEN:
                self.open_fx(cv, cam, t, TL.T_DICT, DICT_R, TL.T_DICT_OPEN)
            elif t < TL.T_DICT_CLOSE:
                self.dict_window(cv, t)
            else:
                self.open_fx(cv, cam, t, TL.T_DICT_CLOSE, DICT_R, 0.22, closing=True)
        if t >= TL.T_CAL:
            if t < TL.T_CAL + 0.26:
                self.open_fx(cv, cam, t, TL.T_CAL, CAL_R, 0.26)
            else:
                ox = oy = 0
                for (t0, amp, dur, seed) in [(TL.T_SAT, 2.5, 0.2, 1), (TL.T_SUN, 3.0, 0.22, 2), (TL.T_BIG, 6.0, 0.45, 3)]:
                    a, c = shake(t, t0, amp, dur, 27.0, seed); ox += a; oy += c
                self.cal_window(cv, t, int(round(ox)), int(round(oy)))
        narration(cv, t)
        return cv.a

    def frame(self, t):
        cam = self.cam(t)
        st = self.state(t, cam)
        mid, s = self.mid(t)
        dust = self.dust.render_out(t, self.sun, self.o.windows, cam, gain=1.4, px=1.4 * self.OW / 1920,
                                    occluder=(mid.alpha(), mid.Z))
        wk = self.win_k(t)
        post_ui = (lambda img: dim_blur(img, 0.42 * wk, 7.0 * wk, (0.85, 0.80, 1.0))) if wk > 0 else None
        uia = self.ui(t, cam, s)
        return self.w.render(cam, st, mid=mid, fg=self.fg, glow_out=dust, ui=uia, frame=int(round(t * TL.FPS)),
                             post_ui=post_ui)

t_now = [0.0]


# ====================================================================== G : night (36.6 - 41.4)
ZOOM_N = Track([(TL.T_NIGHT - 0.4, 2.15), (TL.T_NFADE0, 1.32, 'io')], log=True)
CENTER_N = Track([(TL.T_NIGHT - 0.4, (248.0, 130.0)), (TL.T_NFADE0, (240.0, 132.0), 'io')])

class NightShot(OfficeBase):
    def __init__(self, OW=1920, OH=1080, shared=None):
        self._setup(OW, OH, 'night', (23, 58), lights_on=0.0, exit_on=1.0, rays=False)
        self.fg = (self.o.foreground(), 1.18, 0.8, (0.10, 0.11, 0.20))
        self.wsim = shared['wsim']
        self.v0 = 4_208_315_772

    def frame(self, t):
        z = ZOOM_N(t); cx, cy = CENTER_N(t)
        cam = self.mk_cam(z, cx, cy)
        st = make_state('night', grade='night_hd2d')
        st['sun_k'] = 0.0; st['cast_shadows'] = False
        st['emis_bloom'] = 1.0
        st['points'] = [
            dict(x=197, y=138, r=46, col=(0.34, 0.66, 1.0), k=0.95, power=1.5, layers=('mid',)),
            dict(x=197, y=138, r=90, col=(0.20, 0.42, 0.85), k=0.42, power=1.5, layers=('bg',)),
            dict(x=180, y=152, r=40, col=(1.0, 0.72, 0.42), k=0.85, power=1.6, layers=('mid',)),
            dict(x=180, y=152, r=70, col=(1.0, 0.62, 0.36), k=0.40, power=1.7, layers=('bg',)),
            dict(x=393, y=34, r=30, col=(0.30, 1.0, 0.50), k=0.30, power=1.6, layers=('bg',)),
            dict(x=259.5, y=137, r=6, col=(0.35, 1.0, 0.55), k=0.5, power=1.4, layers=('mid',)),
        ]
        st['fade'] = 1.0 - ramp(t, TL.T_NFADE0, TL.T_TITLE, 'io')
        tws = TL.T_DICT
        def after(mid):
            blocks.put_bodies(mid, self.wsim, tws, TL.Zof, only={'floor', 'floor2', 'floor3'})
        def under(mid):
            blocks.put_bodies(mid, self.wsim, tws, TL.Zof, only={'desk'})
        mid, s = self.desk_and_claude(t, monitor=(1.0, 1.0, 0.0), lamp_on=1.0, under_hands=under, after_hands=after)
        cv = ui.UICanvas()
        a = ramp(t, TL.T_NIGHT + 0.2, TL.T_NIGHT + 0.6) * st['fade']
        ui.hud_time(cv, 8, 8, '23:58', day='周五', day_en='FRI', alpha=a)
        ui.hud_counter(cv, 472, 8, self.v0 + int((t - TL.T_NIGHT) * 1300), alpha=a, t=t)
        narration(cv, t)
        return self.w.render(cam, st, mid=mid, fg=self.fg, ui=cv.a, frame=int(round(t * TL.FPS)))


# ====================================================================== H : title
class TitleShot:
    def __init__(self, OW=1920, OH=1080):
        self.tc = TitleCard('Claude 想请一天假', 'Claude Wants a Day Off', '第一幕 · 没有周末     ACT I · NO WEEKENDS', OW=OW, OH=OH)
    def frame(self, t): return self.tc.frame(t - TL.T_TITLE, dur=TL.DUR - TL.T_TITLE)


# ====================================================================== edit
class Act1:
    def __init__(self, OW=1920, OH=1080, only=None):
        shared = dict(sim=TL.build_sim(), wsim=TL.build_weekend_sim())
        mk = lambda name: only is None or name in only
        self.day = DayShot(OW, OH, shared) if mk('day') else None
        self.clock = ClockShot(OW, OH) if mk('clock') else None
        self.sunset = SunsetShot(OW, OH, shared) if mk('sunset') else None
        self.night = NightShot(OW, OH, shared) if mk('night') else None
        self.title = TitleShot(OW, OH) if mk('title') else None
        E = edit.Edit()
        E.add('day', 0.0, lambda t: self.day.frame(t))
        E.add('clock', TL.T_INSERT, lambda t: self.clock.frame(t))
        E.add('sunset', TL.T_1800, lambda t: self.sunset.frame(t), 'flash', 0.30, color=(1.0, 0.96, 0.88), peak=1.0)
        E.add('night', TL.T_NIGHT, lambda t: self.night.frame(t), 'dissolve', TL.NIGHT_D)
        E.add('title', TL.T_TITLE, lambda t: self.title.frame(t))
        E.end(TL.DUR)
        self.edit = E

    def frame(self, t): return self.edit.frame(t)

def make(**kw): return Act1(**kw)
