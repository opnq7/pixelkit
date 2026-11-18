"""ACT V renderer: make() -> object with .frame(t) -> float RGB (1080, 1920, 3).   Shots + timing: timeline.py

The office is the Act I office on a Monday morning, dressed lived-in (pixelkit.sets.dressing) and lit by a high,
cream morning sun through the blinds; ambient life: mug steam, a pigeon on the window ledge, the clock's second
hand, cloud-modulated sun, dust + glints in the shafts, breathing / blinking / antenna springs."""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
from pixelkit.ui import DOC, W95
import sys, math, importlib.util
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/act5'))
import numpy as np, cv2
import timeline as TL
from pixelkit.sets.office import Office
from pixelkit.sets import props as P, dressing as DR, river_pier as RP
from pixelkit.scene import World, GLayer, make_state, dim_blur
from pixelkit.camera import Cam
from pixelkit.particles import DustField, sparkles, SteamWisps
from pixelkit.characters import claude
from pixelkit.core import C, Canvas, scale_nearest, sel_out, text_width, mix
from pixelkit.anim import clamp01, ramp, ease_io, ease_out3, back_out, shake
from pixelkit.titles import TitleCard
from pixelkit import blocks, ui, edit, perform as PF

U4 = 4
INKT = C('#1a1a1a'); GREY = C('#6a6a6a'); NAVYT = C('#000080')


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m; sp.loader.exec_module(m); return m


# ====================================================================== the Act IV echo (dusk), loaded lazily
class DuskEcho:
    def __init__(self, OW, OH):
        self.OW, self.OH = OW, OH; self.e = None

    def _init(self):
        mine = sys.modules.get('timeline')
        a4tl = _load('a4_timeline', (_PROJ + '/act4/timeline.py'))
        sys.modules['timeline'] = a4tl
        a4 = _load('a4_scene', (_PROJ + '/act4/scene.py'))
        sys.modules['timeline'] = mine
        self.a4tl = a4tl
        self.e = a4.Echo(a4.Pier(self.OW, self.OH))

    def frame(self, t):
        if self.e is None: self._init()
        t4 = 116.3 + 0.55 * t                 # v3.1: seamless from Act IV's cut point (no fade-in), push-in slows
        return self.e.frame(t4)


# ====================================================================== Monday morning office
class Morning:
    def __init__(self, OW=1920, OH=1080):
        self.OW, self.OH = OW, OH
        o = self.o = Office()
        self.bg = o.background(clock=None, tod='morning', dressing=True)
        st0 = make_state('morning', grade='morning_hd2d'); self.sun = st0['sun']
        self.w = World(o.room, o.windows, OW=OW, OH=OH)
        self.w.set_background(self.bg, self.sun)
        self.rays = self.w.rig.god_rays(self.sun, o.windows, scale=0.25, steps=40)
        self.chair = o.chair_sprite()
        self.dust = DustField(o.room, n=1100, size=(0.6, 1.5), seed=55)
        self.fg = (o.foreground(), 1.18, 0.8, (0.40, 0.38, 0.48))
        # v3: the 「周末」 brick is gone - the bobber stands on a little wooden base; beside it a desk calendar
        # (last Saturday ticked, next Saturday circled + a fish doodle) = the promise to the old man
        self.stand = sel_out(DR.bobber_stand().rgba, 0.7)
        self.cal = sel_out(DR.desk_calendar().rgba, 0.6)
        self.bob = RP.bobber_fine()
        self.mug = sel_out(P.mug().rgba, 0.7)
        self.pen = sel_out(DR.pen_cup('#3f6fb0').rgba, 0.7)
        self.note = P.sticky('#f6d860', w=7, h=7, lines=2, seed=9).rgba
        self.snack = sel_out(DR.snack().rgba, 0.7)
        self.pigeons = [DR.pigeon(k).rgba for k in range(3)]
        self.glints = self._glints()
        self.steam = SteamWisps((TL.MUG_XY[0] + 3.5, TL.MUG_XY[1] - 0.5), seed=4)

    # ---------------------------------------------------------------- light
    def state(self, t, cam, dof=0.0):
        st = make_state('morning', grade='morning_hd2d')
        cloud = 0.93 + 0.07 * math.sin(t * 0.37 + 1.2) * math.sin(t * 0.61)      # slow cloud breathing on the sun
        st['sun_k'] = cloud
        zf = clamp01((cam.zoom - 1.0) / 2.4)
        st['rays'] = (2.3 - 1.0 * zf) * cloud
        st['rays_map'] = (self.rays, 0.5)
        st['bounce_k'] = 1.0
        st['emis_bloom'] = 0.45
        st['points'] = [dict(x=197, y=138, r=32, col=(0.36, 0.70, 0.95), k=0.55, power=1.5, layers=('mid',)),
                        dict(x=197, y=138, r=58, col=(0.25, 0.50, 0.75), k=0.16, power=1.6, layers=('bg',))]
        return st

    def _glints(self):
        """sun-shaft twinkles (x, y, t0, life, size) - deterministic."""
        rng = np.random.default_rng(77); out = []
        for k in range(150):
            t0 = float(rng.uniform(0, TL.DUR)); x = float(rng.uniform(70, 300)); y = float(rng.uniform(60, 200))
            out.append((x, y, t0, float(rng.uniform(0.5, 0.9)), float(rng.uniform(2.0, 3.4))))
        return out

    # ---------------------------------------------------------------- dynamic background bits
    def clock_hms(self, t):
        s = 52.0 + t if t < TL.T_0900 else 0.0 + (t - TL.T_0900)
        return (8, 59, s) if t < TL.T_0900 else (9, 0, s)

    def patches(self, t):
        hh, mm, ss = self.clock_hms(t)
        out = [self.o.clock_patch(hh, mm, int(ss) % 60)]
        # the pigeon on the back window's outer ledge: struts in, pecks, looks back
        q = PF.on_twos(t)
        x = 112 + 24 * ease_io(clamp01((q - 3.2) / 1.4)) - 5 * ease_io(clamp01((q - 15.0) / 1.0)) + 4 * ease_io(clamp01((q - 21.0) / 0.8))
        fr = 1 if (int(q * 3) % 7 in (2, 3) and q > 4.4) else (2 if int(q * 2) % 9 == 5 else 0)
        out.append((self.pigeons[fr], int(round(x)), 99))
        return out

    # ---------------------------------------------------------------- screen
    def screen(self, t):
        cv = Canvas(30, 22)
        if t < TL.T_ONLINE:                                   # 'on leave' screen: navy, moon, zz
            cv.rect(0, 0, 30, 22, C('#1d2348'))
            cv.ellipse(10, 9, 4, 4, C('#ffe9a8')); cv.ellipse(12, 8, 3.4, 3.4, C('#1d2348'))
            for i, (x, y) in enumerate(((18, 9), (21, 6), (24, 3))):
                if (t * 1.5 + i * 0.33) % 1 < 0.7: cv.hline(x, y, 2, C('#a9b4ff')); cv.px(x + 1, y + 1, C('#a9b4ff')); cv.hline(x, y + 2, 2, C('#a9b4ff'))
            cv.hline(6, 17, 18, C('#3a4278'))
            return cv.a
        if t < TL.T_REPORT:
            lines = [('早', 'out')] if t < TL.T_0900 else [('在吗？帮我写周报', 'in')]
            if t >= TL.T_OK: lines.append(('好的', 'out'))
            return P.chat_screen(30, 22, lines)
        # the report document, filling up
        cv.rect(0, 0, 30, 22, C('#f6f6f2')); cv.rect(0, 0, 30, 4, C('#000080'))
        n = sum(1 for x in TL.STREAM_T if t >= x)
        for i in range(n):
            u = clamp01((t - TL.STREAM_T[i]) / (len(TL.REPORT_LINES[i]) / TL.STREAM_CPS))
            cv.hline(2, 6 + i * 2, int(round((14 if i == 0 else 24) * u)), C('#5a5a6a'))
        ps, _, _ = TL.ps_text(t)
        if len(ps) > 5: cv.hline(2, 18, min(26, int(len(ps) * 1.1)), C('#d97757'))
        if (t * 2.2) % 1 < 0.6: cv.vline(2 + (min(26, int(len(ps) * 1.1)) if len(ps) > 5 else 0), 17, 3, C('#1a1a1a'))
        return cv.a

    # ---------------------------------------------------------------- mid
    def claude_parts(self, t, d):
        hx, hy = TL.HEAD
        p0 = claude.draw()
        dy_sprite = int(round(TL.DESK_Y - (hy - p0.ay) - d['dy']))
        p = claude.draw(face=d['face'], arms=d['arms'], phase=d['phase'], led=d['led'], led_k=d['led_k'], look=d['look'],
                        glow=d['glow'], desk_y=dy_sprite, tilt=d['tilt'], head_dy=int(d['hdy']),
                        ant=(int(round(d['ant'][0])), int(round(d['ant'][1]))))
        ba, be = p.body.cv.a, p.body.E; ha, he = p.hands.cv.a, p.hands.E
        x0, y0 = hx - p.ax, hy - p.ay - d['dy']
        sq = d['squash']
        if abs(sq) > 1e-3:
            sx, sy = 1.0 + sq * 0.6, 1.0 - sq
            H, W = ba.shape[:2]; bottom = y0 + H
            ba, be, ha, he = (scale_nearest(ba, sx, sy), scale_nearest(be, sx, sy), scale_nearest(ha, sx, sy), scale_nearest(he, sx, sy))
            nh, nw = ba.shape[:2]
            x0 = hx - claude.AX * nw / W; y0 = bottom - nh
        return (ba, be), (ha, he), int(round(x0)), int(round(y0))

    def desk_objects(self, t):
        jy = TL.desk_jolt(t)
        a, e = self.bob
        deg = TL.bobber_wobble(t)
        if abs(deg) >= 0.6:
            a, e = PF.rotsprite(a, e, deg, (4, 18))
        ox, oy = TL.BOB_XY
        mx, my = TL.MUG_XY
        sx_, sy_ = TL.STAND_XY; cx_, cy_ = TL.CAL_XY
        items = [(self.cal, cx_, cy_ + jy, 0.6, None), (self.stand, sx_, sy_ + jy, 0.3, None), (a, ox, oy + jy, 0.4, e * 0.55),
                 (self.mug, mx, my + jy, 0.0, None), (self.pen, 219, 155 + jy, 0.2, None), (self.note, 212, 121, 1.0, None),
                 ]
        return items

    def mid(self, t, d):
        o = self.o
        mid = GLayer()
        mid.put(self.chair.rgba, 232, 128, o.Z['chair'])
        (ba, be), (ha, he), x0, y0 = self.claude_parts(t, d)
        mid.put(ba, x0, y0, o.Z['claude'], E=be)
        o.draw_desk(mid, monitor_on=1.0, content=self.screen(t), lamp_on=0.0, skip={'mug', 'paper', 'cactus'},
                    extra=self.desk_objects(t))
        mid.put(ha, x0, y0, o.Z['desk'], E=he)
        return mid

    # ---------------------------------------------------------------- render
    def render(self, t, cam, d, ui_fn=None, dof=0.0, post=None, rays_mul=1.0):
        st = self.state(t, cam)
        st['rays'] *= rays_mul
        mid = self.mid(t, d)
        dust = self.dust.render_out(t, self.sun, self.o.windows, cam, gain=1.7 * st['sun_k'], px=1.4 * self.OW / 1920,
                                    occluder=(mid.alpha(), mid.Z))
        dust = dust + self.steam.render_out(t, cam, gain=4.5)
        gl = sparkles(t, self.glints, f=2)
        uia = ui_fn(t, cam, d) if ui_fn else None
        def post_ui(img):
            if dof > 0.01: img = self.macro_dof(img, cam, dof)
            if post: img = post(img)
            return img
        return self.w.render(cam, st, mid=mid, fg=self.fg, glow_out=dust, extra_glow=gl * 0.55, ui=uia,
                             frame=int(round(t * TL.FPS)), bg_patches=self.patches(t), post_ui=post_ui)

    def macro_dof(self, img, cam, k):
        """macro depth of field: everything but the bobber + its base melts (k 0..1)."""
        H, W = img.shape[:2]
        m = np.zeros((270, 480), np.float32)
        ox, oy = TL.BOB_XY; m[oy:oy + 19, ox:ox + 9] = self.bob[0][..., 3] > 0
        bx, by = TL.STAND_XY; m[by:by + 4, bx:bx + 11] = 1.0
        s = cam.s
        M = np.float32([[s, 0, W / 2 + cam.sx - cam.cx * s], [0, s, H / 2 + cam.sy - cam.cy * s]])
        mo = cv2.warpAffine(m, M, (W, H), flags=cv2.INTER_NEAREST)
        mo = cv2.GaussianBlur(mo, (0, 0), 6.0)[..., None]
        sm = cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        sm = cv2.GaussianBlur(sm, (0, 0), 1.0 + 3.0 * k)
        bl = cv2.resize(sm, (W, H), interpolation=cv2.INTER_LINEAR)
        a = k * (1 - mo)
        return img * (1 - a) + bl * a


# ====================================================================== shots
class Act5:
    def __init__(self, OW=1920, OH=1080, only=None):
        self.OW, self.OH = OW, OH
        self.m = Morning(OW, OH)
        self.echo = DuskEcho(OW, OH)
        E = edit.Edit()
        E.add('ECHO', 0.0, self.echo.frame)
        E.add('DESK', (TL.T_DISS0 + TL.T_DISS1) / 2, self.f_desk, kind='dissolve', d=TL.T_DISS1 - TL.T_DISS0)
        E.add('OK', TL.T_OKCUT, self.f_ok)
        E.add('REPORT', TL.T_REPORT, self.f_report)
        E.add('MID', TL.T_MID, self.f_mid)
        E.add('CRED', TL.T_CRED, self.f_cred)
        E.end(TL.DUR)
        self.edit = E
        self.cred = None

    def frame(self, t): return self.edit.frame(t)

    # ---------------------------------------------------------------- shared UI
    def hud(self, cv, t, alpha=1.0):
        if t < TL.T_HUD: return
        u = back_out(clamp01((t - TL.T_HUD) / 0.32))
        hh = '08:59' if t < TL.T_0900 else '09:00'
        fl = 0.6 * (1 - ramp(t, TL.T_0900, TL.T_0900 + 0.35)) if t >= TL.T_0900 else 0.0
        ui.hud_time(cv, int(round(8 - (1 - u) * 90)), 8, hh, day='周一', day_en='MON', alpha=min(1, u * 1.5) * alpha, flash=fl)
        # status badge (top right): 休假中 -> 在线
        ub = back_out(clamp01((t - TL.T_HUD - 0.12) / 0.32))
        flip = 1.0
        if TL.T_ONLINE - 0.12 <= t < TL.T_ONLINE + 0.12: flip = abs((t - TL.T_ONLINE) / 0.12)
        state = 'off' if t < TL.T_ONLINE else 'online'
        pulse = 3.0 * (1 - ramp(t, TL.T_ONLINE, TL.T_ONLINE + 0.6)) if t >= TL.T_ONLINE else 0.0
        ui.status_badge(cv, int(round(472 + (1 - ub) * 120)), 8, state, alpha=min(1, ub * 1.5) * alpha, pulse=pulse, flip=flip)

    def chat(self, cv, t):
        m = TL.MSG
        age = t - m['t_in']
        if age < 0: return
        alpha = 1.0 - ramp(t, m['t_out'], m['t_out'] + 0.25)
        if alpha <= 0.01: return
        k = ui.pop_k(age, 1e9, t_in=0.16)
        ui.chat_bubble(cv, 12, 44, m['lines'], avatar=m['avatar'], k=k, name=m['name'], alpha=alpha)

    # ---------------------------------------------------------------- DESK (macro -> desk)
    def f_desk(self, t):
        z, cx, cy = TL.pull_cam(t, TL.DOT)
        sx = sy = 0.0
        a, b = shake(t, TL.T_0900, 3.0, 0.22, 30.0, 3); sx += a; sy += b
        cam = Cam(z, cx, cy, OW=self.OW, OH=self.OH).clamp()
        cam.sx, cam.sy = sx * self.OW / 1920, sy * self.OW / 1920
        d = TL.claude_state(t)
        dof = clamp01((z - 2.2) / 3.0) ** 1.2
        def ui_fn(t, cam, d):
            cv = ui.UICanvas()
            self.hud(cv, t); self.chat(cv, t)
            return cv.a
        return self.m.render(t, cam, d, ui_fn, dof=dof)

    # ---------------------------------------------------------------- OK (close, identical to Act I)
    def f_ok(self, t):
        cam = Cam(3.2 * (1 + 0.01 * (t - TL.T_OKCUT)), 254.0, 128.0, OW=self.OW, OH=self.OH).clamp()
        d = TL.claude_state(t)
        def ui_fn(t, cam, d):
            cv = ui.UICanvas()
            self.hud(cv, t); self.chat(cv, t)
            hx, hy = TL.HEAD
            age = t - TL.T_OK
            if 0 <= age < 0.95:
                ax, ay = cam.w2ui(hx + 15, hy + 3, U4)
                ui.speech_bubble(cv, float(ax), float(ay), '好的！', age, 0.95, side=1, with_coin=True, t=t)
            return cv.a
        return self.m.render(t, cam, d, ui_fn)

    # ---------------------------------------------------------------- REPORT
    REP_R = (12, 32, 312, 222)
    @staticmethod
    def _tiny_bobber(cv, x, y):
        cv.vline(x + 2, y, 2, C('#6a6a7a')); cv.rect(x + 1, y + 2, 3, 3, C('#e04a3a')); cv.rect(x + 1, y + 5, 3, 3, C('#ffffff'))
        cv.px(x, y + 5, C('#6a6a7a')); cv.px(x + 4, y + 5, C('#6a6a7a')); cv.hline(x + 1, y + 8, 3, C('#6a6a7a'))
    def report_window(self, cv, t):
        x, y, w, h = self.REP_R
        def vis(i):
            t0 = TL.STREAM_T[i]
            return -1 if t < t0 else min(len(TL.REPORT_LINES[i]), int((t - t0) * TL.STREAM_CPS) + 1)
        ns = [vis(i) for i in range(len(TL.REPORT_LINES))]
        cur = max([i for i, n in enumerate(ns) if 0 <= n < len(TL.REPORT_LINES[i])], default=-1)
        L0 = TL.REPORT_LINES[0]; H1 = L0[:6]
        blocks = [dict(kind='h1', text=H1, n=max(0, ns[0]), gen=cur == 0 and ns[0] < 6),
                  dict(kind='meta', text='10.20 – 10.24   市场部 · 小李', n=int(max(0, ns[0] - 6) * 22 / (len(L0) - 6)) + (99 if ns[0] >= len(L0) else 0),
                       gen=cur == 0 and ns[0] >= 6), dict(kind='gap', h=2)]
        for i in (1, 2, 3):
            ln = TL.REPORT_LINES[i]
            if ns[i] < 0: break
            blocks.append(dict(kind='li', num=ln[0], text=ln[3:], n=max(0, ns[i] - 3), gen=cur == i))
        if ns[4] >= 0:
            blocks.append(dict(kind='gap', h=2)); blocks.append(dict(kind='p', text=TL.REPORT_LINES[4], n=ns[4], gen=cur == 4))
        done = t >= TL.STREAM_T[-1] + len(TL.REPORT_LINES[-1]) / TL.STREAM_CPS
        warm = t >= TL.T_PS2
        ps, caret, sel = TL.ps_text(t)
        if t >= TL.STREAM_T[-1] + 0.4:
            blocks.append(dict(kind='sep'))
            col = DOC['warm'] if warm else DOC['ink']
            if TL.T_PS1_LOOK <= t < TL.T_DEL1 and not warm:                    # the line greys while Claude hesitates
                col = mix(DOC['ink'], C('#9a9a9a'), ramp(t, TL.T_PS1_LOOK + 0.2, TL.T_PS1_LOOK + 0.6))
            if TL.STREAM_T[-1] + 0.4 <= t < TL.T_PS1:                          # thinking dots before the P.S.
                blocks.append(dict(kind='p', text='·' * (1 + int((t - TL.STREAM_T[-1]) * 4) % 3), col=DOC['grey']))
            else:
                blocks.append(dict(kind='p', text=ps, col=col, sel=sel, caret=caret and t < TL.T_SEND,
                                   tail_icon=self._tiny_bobber if warm and ps == TL.PS2 else None))
        # status bar
        typing = (TL.T_STREAM0 <= t and not done) or (TL.T_PS1 <= t < TL.PS1_T[-1] + 0.1) or (TL.T_PS2 <= t < TL.PS2_T[-1] + 0.1)
        if t >= TL.T_SEND + 0.14: status, scol = '已发送给 市场部 · 小李', DOC['green']
        elif typing: status, scol = 'Claude 正在撰写…', DOC['claude']
        elif TL.T_PS1_LOOK <= t < TL.T_PS2: status, scol = 'Claude 正在想…', DOC['claude']
        elif done: status, scol = '已自动保存', W95['dk']
        else: status, scol = '就绪', W95['dk']
        wc = sum(max(0, n) for n in ns) + (len(ps) if sel is None else sel[0])
        # send button state
        p_end = TL.PS2_T[-1] + 0.05
        st = 'idle'
        if t >= TL.T_SEND + 0.14: st = 'sent'
        elif t >= TL.T_SEND: st = 'pressed'
        elif t >= TL.T_SEND - 0.18: st = 'hover'
        out = ui.w95_doc(cv, x, y, w, h, TL.REPORT_TITLE, blocks, t=t, status=status, status_col=scol,
                         send=dict(state=st), word_count=wc, status_r='中文 (简体)')
        # mouse cursor glides to 发送
        if t >= p_end:
            u = ease_io(clamp01((t - p_end) / (TL.T_SEND - p_end - 0.1)))
            p0 = (x + 190, y + 150); p1 = (out['send'][0] + 16, out['send'][1] + 3)
            pressed = TL.T_SEND <= t < TL.T_SEND + 0.14
            ui.cursor(cv, p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u, pressed,
                      age_press=(t - TL.T_SEND) if t >= TL.T_SEND else None)

    def reply(self, cv, t):
        """小李 answers the P.S. (same chat bubble + spot as the 09:00 message)."""
        lines = TL.reply_lines(t)
        if lines is None: return
        m = TL.REPLY
        alpha = 1.0 - ramp(t, m['t_out'], m['t_out'] + 0.3)
        if alpha <= 0.01: return
        k = ui.pop_k(t - m['t_in'], 1e9, t_in=0.16)
        ui.chat_bubble(cv, 12, 44, lines, avatar=m['avatar'], k=k, name=m['name'], alpha=alpha)

    def f_report(self, t):
        u = ease_io(clamp01((t - TL.T_REPORT) / (TL.T_WIN_CLOSE - TL.T_REPORT)))
        u2 = ease_io(clamp01((t - TL.T_WIN_CLOSE - 0.15) / 1.6))           # after sending: ease over to Claude
        cam = Cam(2.0 + 0.10 * u + 0.12 * u2, 190.0 + 2 * u + 40.0 * u2, 131.0 + 3.0 * u2, OW=self.OW, OH=self.OH).clamp()
        d = TL.claude_state(t)
        kc = clamp01((t - TL.T_WIN_CLOSE) / 0.28)
        def ui_fn(t, cam, d):
            cv = ui.UICanvas()
            self.hud(cv, t)
            k = clamp01((t - TL.T_REPORT) / TL.T_WIN_OPEN)
            if k < 1 or 0 < kc < 1:
                sx, sy, sw, sh = self.m.o.A['monitor_screen']
                x0, y0 = cam.w2ui(sx, sy, U4); x1, y1 = cam.w2ui(sx + sw, sy + sh, U4)
                ui.w95_open_fx(cv, (float(x0), float(y0), float(x1 - x0), float(y1 - y0)), self.REP_R, k if k < 1 else 1 - kc)
            elif kc <= 0:
                self.report_window(cv, t)
            self.reply(cv, t)
            return cv.a
        wk = clamp01((t - TL.T_REPORT) / TL.T_WIN_OPEN) * (1 - ease_io(kc))
        post = (lambda img: dim_blur(img, 0.16 * wk, 0.0, (0.92, 0.90, 1.0)))
        return self.m.render(t, cam, d, ui_fn, post=post)

    # ---------------------------------------------------------------- MID (Claude and the bobber)
    def f_mid(self, t):
        u = ease_io(clamp01((t - TL.T_MID) / (TL.T_MID_END - TL.T_MID)))
        v = ease_io(clamp01((t - TL.T_LOOK_CAL + 0.2) / 2.0))                 # drift over to the calendar with its look
        cam = Cam(2.75 + 0.30 * u + 0.10 * v, 276.0 + 9.0 * v, 143.0 - 1.0 * u - 1.0 * v, OW=self.OW, OH=self.OH).clamp()
        d = TL.claude_state(t)
        def ui_fn(t, cam, d):
            cv = ui.UICanvas()
            ui.narration(cv, t, TL.BOXES)
            self.reply(cv, t)
            return cv.a
        fade = 1 - ramp(t, TL.T_MID_END - 0.95, TL.T_MID_END, 'io')
        return self.m.render(t, cam, d, ui_fn, post=lambda img: img * fade)

    def f_cred(self, t):
        if self.cred is None:
            from credits_scene import Credits
            self.cred = Credits(self.m.bob, self.OW, self.OH)
        return self.cred.frame(t)


def make(**kw): return Act5(**kw)
