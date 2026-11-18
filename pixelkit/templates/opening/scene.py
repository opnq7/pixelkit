"""Opening renderer: Opening().frame(t) -> float RGB (1080, 1920, 3) in 0..1."""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/opening'))
import numpy as np
from pixelkit.sets.office import Office
from pixelkit.scene import World, GLayer, make_state
from pixelkit.camera import Cam
from pixelkit.particles import DustField
from pixelkit.characters import claude
from pixelkit.core import C, Canvas, scale_nearest
from pixelkit.anim import clamp01, ramp, back_out, ease_out3
from pixelkit import blocks, ui
import timeline as TL

GLASS = np.array(C('#1c2b30')[:3], np.uint8); FLASH = np.array(C('#e9fbff')[:3], np.uint8)

class Opening:
    def __init__(self, OW=1920, OH=1080):
        self.o = Office()
        self.bg = self.o.background(clock=(16, 30))
        st = make_state('golden')
        self.sun = st['sun']
        self.w = World(self.o.room, self.o.windows, OW=OW, OH=OH)
        self.w.set_background(self.bg, self.sun)
        self.rays = self.w.rig.god_rays(self.sun, self.o.windows, scale=0.25, steps=40)
        self.dust = DustField(self.o.room, n=1000, size=(0.6, 1.4))
        self.fg = (self.o.foreground(), 1.18, 0.8, (0.35, 0.30, 0.42))
        self.sim, self.hero = TL.build_sim()
        self.chair = self.o.chair_sprite()
        self.OW, self.OH = OW, OH

    # -------------------------------------------------------------- helpers
    def cam(self, t):
        z, cx, cy, sx, sy = TL.cam_params(t)
        c = Cam(z, cx, cy, 0, 0, OW=self.OW, OH=self.OH).clamp()
        c.sx, c.sy = sx * self.OW / 1920, sy * self.OW / 1920
        return c

    def state(self, t, cam):
        amb_k, sun_k = TL.light(t)
        st = make_state('golden')
        st['sun_k'] = sun_k
        st['amb'] = st['amb'] * (0.0 + amb_k)
        st['bg_emis_k'] = amb_k
        st['bounce_k'] = 1.0
        zf = clamp01((cam.zoom - 1.0) / 2.35)
        st['rays'] = 2.0 - 1.0 * zf
        st['rays_map'] = (self.rays, 0.5)
        st['emis_bloom'] = 0.4 + 0.9 * (1 - amb_k)
        on, band, flash = TL.monitor(t)
        pts = []
        if on > 0:
            k = 0.55 * band + 0.6 * flash
            pts.append(dict(x=197, y=138, r=34, col=(0.30, 0.66, 0.92), k=k, power=1.5, layers=('mid',)))
            pts.append(dict(x=197, y=138, r=60, col=(0.20, 0.45, 0.70), k=0.25 * k, power=1.6, layers=('bg',)))
        lk = TL.led_k(t)
        if amb_k < 0.999:
            pts.append(dict(x=259.5, y=137, r=5.5, col=(0.35, 1.0, 0.55), k=0.55 * lk * (1 - amb_k), power=1.4, layers=('mid',)))
        st['points'] = pts
        if TL.in_freeze(t):
            g = dict(st['grade']); u = clamp01((t - TL.T_FREEZE) / 0.05)
            g['sat'] = g['sat'] * (1 - 0.16 * u); g['vignette'] = g['vignette'] + 0.08 * u
            st['grade'] = g
        st['fade'] = 1.0 - ramp(t, TL.T_FADE0, TL.T_END, 'io')
        return st, sun_k

    def claude_parts(self, t):
        s = TL.claude_state(t)
        hx, hy = TL.HEAD
        p0 = claude.draw(face='normal', arms='rest')
        dy_sprite = int(round(TL.DESK_Y - (hy - p0.ay) - s['dy']))
        p = claude.draw(face=s['face'], arms=s['arms'], phase=s['phase'], led='online', led_k=s['led_k'], look=s['look'],
                        glow=s['glow'], desk_y=dy_sprite, squash=0.0, spark_k=TL.light(t)[0])
        body, hands = p.body, p.hands
        x0, y0 = hx - p.ax, hy - p.ay + s['dy']
        sq = s['squash']
        if abs(sq) > 1e-3:
            sx, sy = 1.0 + sq * 0.6, 1.0 - sq
            H, W = body.cv.a.shape[:2]
            bottom = y0 + H
            outs = []
            for sp in (body, hands):
                rgba = scale_nearest(sp.cv.a, sx, sy); E = scale_nearest(sp.E, sx, sy)
                outs.append((rgba, E))
            nh, nw = outs[0][0].shape[:2]
            x0 = hx - claude.AX * nw / W; y0 = bottom - nh
            return outs[0], outs[1], x0, y0, s
        return (body.cv.a, body.E), (hands.cv.a, hands.E), x0, y0, s

    # -------------------------------------------------------------- mid layer
    def mid(self, t):
        o = self.o; tw = TL.tau(t)
        mid = GLayer()
        mid.put(self.chair.rgba, 232, 128, o.Z['chair'])
        (brgba, bE), (hrgba, hE), x0, y0, s = self.claude_parts(t)
        mid.put(brgba, x0, y0, o.Z['claude'], E=bE)
        on, band, flash = TL.monitor(t)
        o.draw_desk(mid, monitor_on=on, screen_lines=TL.screen_lines(t))
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
        blocks.put_bodies(mid, self.sim, tw, TL.Zof, only={'desk'})
        mid.put(hrgba, x0, y0, o.Z['desk'], E=hE)
        blocks.put_bodies(mid, self.sim, tw, TL.Zof, only={'floor', 'floor2', 'floor3'})
        return mid, s

    # -------------------------------------------------------------- UI layer (480x270, x4)
    def ui(self, t, cam, s):
        cv = ui.UICanvas(); tw = TL.tau(t)
        U = lambda x, y: tuple(float(v) for v in cam.w2ui(x, y, 4))
        hx, hy = TL.HEAD
        # chat feed
        for m in TL.MSGS:
            age = t - m['t_in']
            if age < 0: continue
            alpha = 1.0 - ramp(t, m['t_out'], m['t_out'] + 0.25)
            if alpha <= 0.01: continue
            lift = 0.0
            for n in TL.MSGS[m['i'] + 1:]:
                lift += ease_out3((t - n['t_in']) / 0.22) * (TL.msg_h(n) + 4) if t > n['t_in'] else 0.0
            lift += 10 * ramp(t, m['t_out'], m['t_out'] + 0.25)
            y = TL.FEED_BOT - TL.msg_h(m) - lift
            k = ui.pop_k(age, 1e9)
            ui.chat_bubble(cv, TL.FEED_X, int(round(y)), m['lines'], avatar=m['avatar'], k=k, name=m['name'], alpha=alpha)
        # Claude's big '好的！'
        ax, ay = U(hx + 15, hy + 3)
        for to in TL.OKS:
            age = t - to
            if 0 <= age < 0.95: ui.speech_bubble(cv, ax, ay, '好的！', age, 0.95, side=1, with_coin=True, t=t)
        # dizzy stars + bonk lines
        if s['stars'] > 0:
            cx, cy = U(hx, hy - 4)
            r = 13 * cam.zoom / 2.6
            ui.dizzy_stars(cv, cx, cy, t, 3, r, r * 0.3, 2.4, alpha=s['stars'])
        bt = TL.MSGS[2]['t_land']
        if 0 <= t - bt < 0.12:
            cx, cy = U(hx + 3, hy - 3)
            ui.burst_lines(cv, cx, cy, 10 + 60 * (t - bt), 18 + 90 * (t - bt), 9, ui.CREAM, 1.0 - (t - bt) / 0.12, 0.3)
        # HUD
        u_c = back_out(clamp01((t - TL.T_HUD_COUNTER) / 0.32)) if t >= TL.T_HUD_COUNTER else 0.0
        slot = (440, 30)
        if u_c > 0:
            xr = 472 + (1 - u_c) * 130
            val = TL.counter_value(t)
            bump = 0.0
            for ob in TL.OK_BURSTS:
                dt = tw - (ob['tw'] + TL.COIN_DELAY + TL.COIN_FLY)
                if 0 <= dt < 0.12: bump = max(bump, 1 - dt / 0.12)
            if t >= TL.T_COIN1 and t < TL.T_COIN1 + 0.25: bump = max(bump, 1 - (t - TL.T_COIN1) / 0.25)
            slot = ui.hud_counter(cv, int(round(xr)), 8, val, alpha=min(1, u_c * 1.5), bump=bump, t=tw)
        if t >= TL.T_HUD_TIME:
            u_t = back_out(clamp01((t - TL.T_HUD_TIME) / 0.32))
            ui.hud_time(cv, int(round(8 - (1 - u_t) * 90)), 8, '16:30', day='周五', day_en='FRI', alpha=min(1, u_t * 1.5))
        # rain '好的！' bursts + coins (world time: they freeze with the world)
        for ob in TL.OK_BURSTS:
            age = tw - ob['tw']
            if age < 0 or age > TL.OK_LIFE + TL.COIN_FLY + TL.COIN_DELAY: continue
            px, py = U(hx + ob['dx'], hy + 8 + ob['dy'])
            if age < TL.OK_LIFE:
                ui.speech_bubble(cv, px, py, '好的！', age, TL.OK_LIFE, side=ob['side'], with_coin=False, fname='zh10', rise=4, t=tw)
            uu = (age - TL.COIN_DELAY) / TL.COIN_FLY
            if 0 <= uu <= 1 and u_c > 0:
                ui.fly_coin(cv, (px + 6 * ob['side'], py - 14), slot, uu, tw, arc=30)
        # the freeze: tiny '好的！' + one coin (real time - only Claude is alive)
        if TL.in_freeze(t) or (t >= TL.T_RESUME and t < TL.T_RESUME + 0.05):
            age = t - TL.T_TINY_OK
            if 0 <= age < 0.36:
                ui.tiny_bubble(cv, ax - 4, ay + 2, '好的！', age, 0.36)
            uu = (t - TL.T_COIN0) / (TL.T_COIN1 - TL.T_COIN0)
            if 0 <= uu <= 1: ui.fly_coin(cv, (ax + 2, ay - 8), slot, uu, t, arc=22)
        return cv.a

    # -------------------------------------------------------------- frame
    def frame(self, t):
        cam = self.cam(t)
        st, sun_k = self.state(t, cam)
        mid, s = self.mid(t)
        tw = TL.tau(t)
        dust = None
        if sun_k > 0.01:
            dust = self.dust.render_out(tw, self.sun, self.o.windows, cam, gain=1.6 * sun_k, px=1.4 * self.OW / 1920,
                                        occluder=(mid.alpha(), mid.Z))
        uia = self.ui(t, cam, s)
        return self.w.render(cam, st, mid=mid, fg=self.fg, glow_out=dust, ui=uia, frame=int(round(t * TL.FPS)))

def make(**kw): return Opening(**kw)
