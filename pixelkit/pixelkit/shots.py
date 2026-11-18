"""Reusable shot bases.

OfficeShot — Claude-at-desk office shot machinery (from ACT I).  Subclass it and call
    self._setup(OW, OH, tod, clock, lights_on, exit_on, rays, tl=timeline_module)
`tl` must provide:
    monitor(t) -> (on, band, flash)           CRT power-on band (0..1) + white flash
    claude_state(t) -> dict(face, arms, phase, led_k, look, glow, dy, squash [, led, crt 0..1, spark_k])
    HEAD = (x, y)  head anchor in world px;   DESK_Y = desk top y
    screen_lines(t) -> list for Office.draw_desk(screen_lines=...)
v0.8.1: same lived-in office as every act (dressing=True + pen cup / sticky note on the desk) and the v0.7
performance layer applied automatically by perf_state(t) (set self.perform = False to get raw tl.claude_state).
    optional tl hooks:  NO_TWOS = [(a, b), ...]  ranges kept at full frame rate (time-lapses)
                        KICKS = [(t0, amp), ...]  antenna spring kicks (hops, landings, surprises)
                        tilt_target(t) -> deg     head roll target (spring-followed), e.g. 7 on a '?'
                        head_sink(t) -> px        extra head drop (sad / deflated), added to the breath
Then in frame(): cam = self.mk_cam(z, cx, cy, sx, sy); mid, s = self.desk_and_claude(t, ...);
    self.w.render(cam, st, mid, fg, glow_out, ui, frame)   (see act1/scene.py DayShot / NightShot)
"""
import numpy as np
from .sets.office import Office
from .scene import World, GLayer, make_state
from .camera import Cam
from .characters import claude
from .core import C, scale_nearest, sel_out
from . import perform as PF

GLASS = np.array(C('#1c2b30')[:3], np.uint8); FLASH = np.array(C('#e9fbff')[:3], np.uint8)
MONITOR_XY = (197, 138)


class OfficeShot:
    perform = True

    def _setup(self, OW, OH, tod, clock, lights_on=0.0, exit_on=1.0, rays=True, tl=None, dressing=True, desk_props=True):
        from .sets import props as P, dressing as DR
        self.tl = tl
        self.OW, self.OH = OW, OH
        self.o = Office()
        self.dressing = dressing
        self.bg = self.o.background(clock=clock, lights_on=lights_on, exit_on=exit_on, tod=tod, dressing=dressing)
        self.desk_extra = ([(sel_out(DR.pen_cup('#3f6fb0').rgba, 0.7), 219, 155, 0.2, None),
                            (P.sticky('#f6d860', w=7, h=7, lines=2, seed=9).rgba, 212, 121, 1.0, None)] if desk_props else [])
        self.tod = tod
        self.sun = make_state(tod)['sun']
        self.w = World(self.o.room, self.o.windows, OW=OW, OH=OH)
        self.w.set_background(self.bg, self.sun)
        self.rays = self.w.rig.god_rays(self.sun, self.o.windows, scale=0.25, steps=40) if rays else None
        self.chair = self.o.chair_sprite()

    def mk_cam(self, z, cx, cy, sx=0.0, sy=0.0):
        """camera clamped to the room; sx/sy = screen shake in 1080p px."""
        c = Cam(z, cx, cy, 0, 0, OW=self.OW, OH=self.OH).clamp()
        c.sx, c.sy = sx * self.OW / 1920, sy * self.OW / 1920
        return c

    def monitor_points(self, t, k_mul=1.0, r=34):
        """cyan CRT point lights (mid + wide bg spill) for World.render point list."""
        on, band, flash = self.tl.monitor(t)
        pts = []
        if on > 0:
            k = (0.55 * band + 0.6 * flash) * k_mul
            x, y = MONITOR_XY
            pts.append(dict(x=x, y=y, r=r, col=(0.30, 0.66, 0.92), k=k, power=1.5, layers=('mid',)))
            pts.append(dict(x=x, y=y, r=r * 1.75, col=(0.20, 0.45, 0.70), k=0.25 * k, power=1.6, layers=('bg',)))
        return pts

    def perf_state(self, t):
        """v0.7 performance layer on top of tl.claude_state (timing untouched): poses on twos, half-lid in-betweens
        around blinks, 1 px breathing (+ tl.head_sink), springy antenna (tl.KICKS), spring-followed head tilt."""
        tl = self.tl
        if not self.perform: return dict(tl.claude_state(t), tilt=0.0, hdy=0, ant=(0, 0))
        lapse = any(a <= t < b for a, b in getattr(tl, 'NO_TWOS', ()))
        q = t if lapse else PF.on_twos(t)
        s = dict(tl.claude_state(q))
        if s['face'] in ('normal', 'happy', 'focus', 'wide', 'q') and s.get('glow', 1.0) > 0:
            for dt in (-1 / 15, 1 / 15):
                if tl.claude_state(q + dt)['face'] in ('blink', 'closed'): s['face'] = 'half'; break
        awake = s.get('glow', 1.0) > 0 and s['face'] not in ('closed',) and not s.get('crt', 0)
        hdy = PF.breath_px(q, 3.6) if (awake and not lapse and s['dy'] == 0 and s['arms'] in ('rest', 'shrug')) else 0
        if hasattr(tl, 'head_sink'): hdy += int(round(tl.head_sink(q)))
        s['hdy'] = hdy
        sp = PF.wobbles(t, getattr(tl, 'KICKS', ()), freq=3.6, decay=2.6)
        s['ant'] = (int(round(sp)), int(round(-abs(0.5 * sp))))
        s['tilt'] = (PF.spring_follow(tl.tilt_target, q, freq=2.0, zeta=0.5, window=1.2, dt=1 / 120)
                     if hasattr(tl, 'tilt_target') else 0.0)
        return s

    def claude_parts(self, t, spark_k=1.0):
        tl = self.tl
        s = self.perf_state(t)
        hx, hy = tl.HEAD
        p0 = claude.draw(face='normal', arms='rest')
        dy_sprite = int(round(tl.DESK_Y - (hy - p0.ay) - s['dy']))
        p = claude.draw(face=s['face'], arms=s['arms'], phase=s['phase'], led=s.get('led', 'online'), led_k=s['led_k'],
                        look=s['look'], glow=s['glow'], desk_y=dy_sprite, squash=0.0, spark_k=s.get('spark_k', spark_k),
                        tear=s.get('tear', 0.0), tilt=s['tilt'], head_dy=s['hdy'], ant=s['ant'])
        body, hands = p.body, p.hands
        if s.get('crt', 0) > 0: claude.crt_off(body.cv, body.E, s['crt'])     # old-TV power-off of the face
        x0, y0 = hx - p.ax, hy - p.ay + s['dy']
        sq = s['squash']
        if abs(sq) > 1e-3:
            sx, sy = 1.0 + sq * 0.6, 1.0 - sq
            H, W = body.cv.a.shape[:2]
            bottom = y0 + H
            outs = [(scale_nearest(sp.cv.a, sx, sy), scale_nearest(sp.E, sx, sy)) for sp in (body, hands)]
            nh, nw = outs[0][0].shape[:2]
            x0 = hx - claude.AX * nw / W; y0 = bottom - nh
            return outs[0], outs[1], x0, y0, s
        return (body.cv.a, body.E), (hands.cv.a, hands.E), x0, y0, s

    def desk_and_claude(self, t, monitor=None, lamp_on=0.0, spark_k=1.0, under_hands=None, after_hands=None, mid=None):
        """chair -> Claude body -> desk (+ CRT power-on band) -> under_hands(mid) -> hands -> after_hands(mid).
           under_hands: draw things that sit on the desk but under Claude's paws (bricks, paper)."""
        o = self.o
        mid = GLayer() if mid is None else mid
        mid.put(self.chair.rgba, 232, 128, o.Z['chair'])
        (brgba, bE), (hrgba, hE), x0, y0, s = self.claude_parts(t, spark_k)
        mid.put(brgba, x0, y0, o.Z['claude'], E=bE)
        on, band, flash = self.tl.monitor(t) if monitor is None else monitor
        o.draw_desk(mid, monitor_on=on, screen_lines=self.tl.screen_lines(t), lamp_on=lamp_on, extra=self.desk_extra)
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
