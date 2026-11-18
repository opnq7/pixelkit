"""pixelkit.sets.office - Claude's open-plan office at golden hour (480x270 native).

    office = Office()                     # builds room, windows, background G-buffer
    bg     = office.background(clock=(16, 30), lights_on=0.0)
    mid    = office.mid_static()          # desk / chair / monitor etc. (dynamic parts drawn per frame)
    fg     = office.foreground()          # potted plant (parallax + blur)

Anchors (native px) are in office.A (Claude head top-centre, desk top, monitor screen ...).
Depths: back wall 400, partition 372, Claude 345, desk front 330 (desk top spans 330..358).
"""
import numpy as np
from ..core import C, mix, sel_out
from ..persp import BoxRoom, BACK, FLOOR, CEIL, LEFT, RIGHT
from ..light import Window, Sun
from ..scene import GLayer, Sprite
from . import props as P
from .room import paint_shell

class Office:
    SHELL = dict(floor=dict(base='#8e6a55', mat='planks', pl=96.0, pw=9.0, band=1.8),
                 back=dict(base='#dcc1a6', mat='plaster', mottle=0.5),
                 left=dict(base='#d6b89c', mat='plaster', mottle=0.5),
                 right=dict(base='#d9bca0', mat='plaster', mottle=0.5))

    def __init__(self, seed=0, shell=None):
        self.shell = {**self.SHELL, **(shell or {})}
        self.room = BoxRoom(480, 270, back=(64, 26, 416, 196), vp=(240, 118), D=400.0)
        self.win = Window(LEFT, 298, 386, -72, 12,
                          blinds=dict(period=5.2, open=0.56, top=-72, bottom=12, soft=0.08, opacity=0.93),
                          mullions=(342.0,), mull_w=2.6, frame=1.5)
        self.windows = [self.win]
        self.seed = seed
        self.A = dict(
            claude=(250, 113),            # head top-centre
            desk=(166, 165, 168, 46),     # x, y(top surface), w, total h
            desk_top_y=165, desk_front_y=173,
            monitor=(176, 121),           # top-left of CRT sprite
            monitor_screen=(181, 125, 32, 26),
            clock=(330, 52), partition=(146, 99, 204, 103),
            chat_anchor=(222, 120),       # where the "在吗？" chat bubble points
        )
        self.Z = dict(partition=372.0, claude=345.0, desk=330.0, chair=352.0, wall=399.5)

    # ------------------------------------------------------------------ background
    WINDOW_SKY = {   # side-window (blinds) sky colour + emissive levels per time of day
        'morning': dict(sky='#f4f8ff', e_sky=1.05, e_slat=0.60, warm=0.06),
        'golden': dict(sky='#fff1cf', e_sky=1.0, e_slat=0.55, warm=0.15),
        'late':   dict(sky='#ffe6c0', e_sky=1.0, e_slat=0.55, warm=0.22),
        'sunset': dict(sky='#ffd2a0', e_sky=1.0, e_slat=0.50, warm=0.30),
        'dusk':   dict(sky='#8a7ab0', e_sky=0.7, e_slat=0.16, warm=0.10),
        'night':  dict(sky='#2a3366', e_sky=0.55, e_slat=0.05, warm=0.0),
    }

    def background(self, clock=(16, 30), lights_on=0.0, exit_on=1.0, city_seed=3, tod='golden', wang_live=False,
                   dressing=False):
        """clock=None leaves the clock face out of the bake (draw it per frame with clock_patch()).
        tod: sky / window preset ('golden' | 'late' | 'sunset' | 'dusk' | 'night').
        wang_live=True leaves Wang Gong's desk + items out of the bake (only his partition) - draw them per
        frame with draw_wang_desk(mid, wang_parts) so a character can sit behind the desk."""
        self.tod = tod
        room = self.room
        bg = GLayer(room.W, room.H)
        alb, sid = paint_shell(room, self.shell, seed=self.seed)
        bg.cv.a[:] = alb
        Zw = self.Z['wall']
        # ceiling light panels
        for X0, X1 in ((-120, -40), (40, 120)):
            pts = room.quad_on_wall(CEIL, X0, X1, 330, 372)
            from ..core import poly_mask
            m = poly_mask(room.W, room.H, pts)
            bg.fill(m, C('#e9e6e0') if lights_on < 0.5 else C('#fffbea'), Z=np.nan, N=CEIL, E=0.9 * lights_on, flat=True)
            inner = poly_mask(room.W, room.H, room.quad_on_wall(CEIL, X0 + 4, X1 - 4, 334, 368))
            bg.fill(inner & m, C('#d4d2d0') if lights_on < 0.5 else C('#ffffff'), Z=np.nan, N=CEIL, E=1.0 * lights_on, flat=True)
        # left wall window (blinds + sky)
        rgba, E, m = P.blinds_window_side(room, self.win, **self.WINDOW_SKY[tod])
        bg.cv.a[m] = rgba[m]; bg.E[m] = E[m]; bg.flat[m] = True
        bg.Z[m] = np.nan
        # right wall door
        rgba, m = P.door_side(room, RIGHT, 330, 382, -36, 78)
        bg.cv.a[m] = rgba[m]
        # back wall: window with city view + cactus on the sill
        w = P.window_back(70, 66, seed=city_seed, tod=None if tod == 'golden' else tod)
        bg.put(w.rgba, 76, 40, Zw, E=w.E, flat=True)
        cac = P.cactus_pot(10); bg.put(sel_out(cac.rgba), 128, 96, Zw - 3)
        # cabinet + printer under the window
        cab = P.filing_cabinet(76, 44); bg.put(sel_out(cab.rgba, 0.7), 72, 152, 392.0)
        pr = P.printer(30, 11); bg.put(sel_out(pr.rgba, 0.7), 82, 138, 392.0)
        # banner, clock, calendar, exit sign
        b = P.banner(); bg.put(b.rgba, 240 - b.rgba.shape[1] // 2, 30, Zw, flat=True)
        ck = P.wall_clock(12, *(clock or (12, 0))); self.A['clock_box'] = (318, 40, ck.rgba.shape[1], ck.rgba.shape[0])
        bg.put(ck.rgba, 318, 40, Zw, flat=True)          # (re-drawn per frame by clock_patch when animated)
        cal = P.calendar(); bg.put(cal.rgba, 372, 56, Zw, flat=True)
        ex = P.exit_sign(); bg.put(ex.rgba, 386, 30, Zw, E=ex.E * exit_on, flat=True)
        # Wang Gong's empty desk (right): low partition + desk + items
        wp = P.partition(66, 50, posts=(33,), seed=5); bg.put(wp.rgba, 348, 128, 386.0)
        if not wang_live:
            wd = P.desk(66, 6, 26, wood='#9a6440', drawer_side='right', seed=7); bg.put(wd.rgba, 348, 168, 380.0)
            bg.N[168:174, 348:414] = FLOOR
            ch = P.jacket_on_chair(24, 24); bg.put(sel_out(ch.rgba, 0.7), 362, 146, 383.0)
            mon2 = P.crt_monitor(0.0, w=26, h=22); bg.put(sel_out(mon2.rgba, 0.7), 384, 142, 381.0)
            nc = P.noodle_cup(); bg.put(sel_out(nc.rgba, 0.75), 352, 159, 379.0)
            ph = P.framed_photo_fishing(); bg.put(ph.rgba, 395, 156, 379.0)   # stands on the desk
            npl = P.nameplate('王工'); bg.put(npl.rgba, 360, 165, 378.5)
        # Claude's partition (centre) with pinned items
        x0, y0, pw, ph_ = self.A['partition']
        part = P.partition(pw, ph_, posts=(68, 136), seed=2)
        cv = part.cv
        items = [
            (P.poster_best(), 8, 8), (P.sticky('#f6d860', seed=1), 50, 10), (P.sticky('#f59bb8', seed=2), 61, 14),
            (P.sticky('#9fe39a', seed=3), 52, 22), (P.postcard_river(), 144, 8), (P.kpi_chart(), 166, 14),
            (P.sticky('#8fd3f5', seed=4), 150, 28),
        ]
        for spr, ix, iy in items:
            cv.blit(spr.rgba, ix, iy)
        bg.put(part.rgba, x0, y0, self.Z['partition'])
        self.A['postcard'] = (x0 + 144, y0 + 8)
        if dressing:                     # v0.8 lived-in clutter (shelf, cork board, plants, bin, paper balls ...)
            from .dressing import dress_office
            dress_office(self, bg, **(dressing if isinstance(dressing, dict) else {}))
        return bg

    def clock_patch(self, hh, mm, ss=None):
        """the wall clock at any time -> (rgba, x, y) for World.render(bg_patches=[...]) (time-lapses, 17:59 ...)."""
        ck = P.wall_clock(12, hh, mm, ss)
        x, y = self.A['clock_box'][:2]
        return (ck.rgba, x, y)

    CLOCK_CENTER = (331, 53)       # native px (for crash zooms / match cuts into the clock)

    # ------------------------------------------------------------------ mid (static parts)
    def desk_sprite(self):
        x, y, w, h = self.A['desk']
        return P.desk(w, 8, h - 8, wood='#a86c43', drawer_side='left', seed=3)

    def draw_desk(self, mid, monitor_on=0.0, screen_lines=None, lamp_on=0.0, items=True, skip=(), extra=(), content=None):
        """draws the desk + desk items onto the mid layer (call after Claude's body, before hands).
        v0.8: skip = names of default items to leave out ('monitor','keyboard','mug','paper','cactus','lamp');
        extra = [(rgba, x, y, dz, E|None)] more desk items (dz relative to the desk-item depth);
        content = Sprite drawn on the CRT screen (overrides screen_lines)."""
        x, y, w, h = self.A['desk']
        d = self.desk_sprite()
        mid.put(d.rgba, x, y, self.Z['desk'])
        mid.N[y:y + 8, x:x + w] = FLOOR
        Zt = self.Z['desk'] + 12
        if items:
            mx, my = self.A['monitor']
            if 'monitor' not in skip:
                if content is None: content = P.chat_screen(28, 20, screen_lines) if screen_lines else None
                mon = P.crt_monitor(monitor_on, content)
                mid.put(sel_out(mon.rgba, 0.65), mx, my, Zt, E=mon.E)
            if 'keyboard' not in skip: kb = P.keyboard(); mid.put(sel_out(kb.rgba, 0.7), 233, 165, Zt - 4)
            if 'mug' not in skip: mg = P.mug(); mid.put(sel_out(mg.rgba, 0.7), 292, 157, Zt)
            if 'paper' not in skip: ps = P.paper_stack(); mid.put(sel_out(ps.rgba, 0.75), 304, 158, Zt)
            if 'cactus' not in skip: ca = P.cactus_pot(9); mid.put(sel_out(ca.rgba, 0.7), 321, 155, Zt)
            if 'lamp' not in skip: lp = P.desk_lamp(lamp_on); mid.put(sel_out(lp.rgba, 0.7), 168, 142, Zt + 4, E=lp.E)
            for (rgba, ex, ey, dz, eE) in extra:
                mid.put(rgba, ex, ey, Zt + dz, E=eE)
        return mid

    # ------------------------------------------------------------------ Wang Gong's desk (live)
    WANG_HEAD = (370, 128)            # head top-centre of a human.draw() sitter
    WANG_DESK_Y = 168
    LAPTOP_XY = (353, 151)

    def draw_wang_desk(self, mid, wang=None, laptop_on=1.0, t=0.0, steam=True, desk_y_sprite=None):
        """chair -> sitter body -> desk + items -> sitter hands -> laptop (lid back to camera) -> nameplate.
        wang: human.draw(...) result (or None for the empty desk with the jacket on the chair)."""
        if not hasattr(self, '_wang_cache'):
            self._wang_cache = dict(
                desk=P.desk(66, 6, 26, wood='#9a6440', drawer_side='right', seed=7),
                chair=sel_out(P.office_chair_back(26, 26).rgba, 0.7), jacket=sel_out(P.jacket_on_chair(24, 24).rgba, 0.7),
                mon=sel_out(P.crt_monitor(0.0, w=26, h=22).rgba, 0.7), noodle=sel_out(P.noodle_cup().rgba, 0.75),
                photo=P.framed_photo_fishing().rgba, plate=P.nameplate('王工').rgba)
        c = self._wang_cache
        hx, hy = self.WANG_HEAD
        if wang is None:
            mid.put(c['jacket'], 362, 146, 383.0)
        else:
            mid.put(c['chair'], hx - 13, 143, 383.5)
            mid.put(wang.body.rgba, hx - wang.ax, hy - wang.ay, 382.0, E=wang.body.E)
        mid.put(c['mon'], 386, 142, 381.0)
        mid.put(c['photo'], 397, 156, 379.0)
        mid.put(c["desk"].rgba, 348, 168, 380.0); mid.N[168:174, 348:414] = FLOOR
        mid.put(c['noodle'], 348, 158, 379.0)
        if steam:
            st = P.steam(t, 13, seed=1); mid.put(st.rgba, 347, 145, 379.0, E=st.E)
        if wang is not None:
            mid.put(wang.hands.rgba, hx - wang.ax, hy - wang.ay, 379.6, E=wang.hands.E)
            if getattr(wang, 'reach', None) is not None:      # v0.11: a hand reaching out IN FRONT of the desk props
                mid.put(wang.reach.rgba, hx - wang.ax, hy - wang.ay, 378.8, E=wang.reach.E)
            lp = P.laptop_back(30, 17, on=laptop_on); lx, ly = self.LAPTOP_XY
            mid.put(sel_out(lp.rgba, 0.7), lx, ly, 379.4, E=lp.E)
        mid.put(c['plate'], 360, 165, 378.5)

    def chair_sprite(self):
        return P.office_chair_back(36, 30)

    def foreground(self):
        """RGBA canvas (native size) with the foreground plant."""
        from ..core import Canvas
        cv = Canvas(self.room.W, self.room.H)
        pl = P.plant_big(70, 120, seed=4)
        cv.blit(pl.rgba, -14, self.room.H - 112)
        return cv.a

    def sun(self, tod='golden'):
        from ..light import TOD
        t = TOD[tod]
        return Sun(t['sun'][0], t['sun'][1], t['sun'][2])
