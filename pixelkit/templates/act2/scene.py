"""ACT II renderer: make() -> object with .frame(t) -> float RGB (1080, 1920, 3).   Shots: see timeline.py"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math, importlib.util
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/act2'))
import numpy as np
from pixelkit.shots import OfficeShot
from pixelkit.scene import make_state, dim_blur
from pixelkit.characters import human
from pixelkit.core import C, Canvas, text_width
from pixelkit.anim import clamp01, ramp, ease_out3, ease_io, back_out, shake, typed_n, box_at, boxes_prep
from pixelkit import blocks, ui, edit
from pixelkit import perform as PF
import timeline as TL

_spec = importlib.util.spec_from_file_location('act1_timeline', (_PROJ + '/act1/timeline.py'))
TL1 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(TL1)

U4 = 4
NAVYT = C('#000080'); INKT = C('#1a1a1a'); GREY = C('#6a6a6a'); RED = C('#d6372d'); BLUE = C('#1f4fbf')
W95 = ui.W95
WANG_LOOK = human.WANG

def night_state(t, fade=1.0):
    st = make_state('night', grade='night_hd2d')
    st['sun_k'] = 0.0; st['cast_shadows'] = False; st['emis_bloom'] = 1.0; st['fade'] = fade
    return st

def claude_points(t, mon_on=1.0, lamp=1.0, led=1.0):
    p = []
    if mon_on > 0:
        p += [dict(x=197, y=138, r=46, col=(0.34, 0.66, 1.0), k=0.95 * mon_on, power=1.5, layers=('mid',)),
              dict(x=197, y=138, r=90, col=(0.20, 0.42, 0.85), k=0.42 * mon_on, power=1.5, layers=('bg',))]
    if lamp > 0:
        p += [dict(x=180, y=152, r=40, col=(1.0, 0.72, 0.42), k=0.85 * lamp, power=1.6, layers=('mid',)),
              dict(x=180, y=152, r=70, col=(1.0, 0.62, 0.36), k=0.40 * lamp, power=1.7, layers=('bg',))]
    p.append(dict(x=393, y=34, r=30, col=(0.30, 1.0, 0.50), k=0.30, power=1.6, layers=('bg',)))
    if led > 0: p.append(dict(x=259.5, y=137, r=6, col=(0.35, 1.0, 0.55), k=0.5 * led, power=1.4, layers=('mid',)))
    return p

def wang_points(k=1.0):
    return [dict(x=370, y=150, r=30, col=(0.50, 0.78, 1.0), k=0.42 * k, power=1.5, layers=('mid',)),
            dict(x=370, y=150, r=60, col=(0.25, 0.50, 0.85), k=0.30 * k, power=1.6, layers=('bg',))]


# ====================================================================== shared form drawing
FX0 = TL.FORM_R[0] + 4; FY0 = TL.FORM_R[1] + 19          # client origin
MB_Y = FY0 + 14                                           # below the menu bar (v2)
LX = FX0 + 66; FLD_X = FX0 + 68; FLD_W = TL.FORM_R[2] - 8 - 72; PITCH = 14; ROW_Y0 = MB_Y + 16; FLD_H = 13
def row_y(i): return ROW_Y0 + i * PITCH
CHK_X = [FLD_X + 2 + i * 44 for i in range(4)]
SUB_BTN = (FX0 + 118, ROW_Y0 + 7 * PITCH + 2, 58, 15)
CAN_BTN = (FX0 + 182, ROW_Y0 + 7 * PITCH + 2, 58, 15)

def _blocks_text(cv, x, y, n=8):
    for i in range(n): cv.rect(x + i * 7, y, 6, 9, INKT)

def form_status(t, done=False):
    first = TL.ROWS[0]['t0'] - 0.25
    if done:
        st = (dict(text='已批准', w=58, col=C('#1a7a2a')) if t >= TL.T_STAMP else dict(text='审批中', w=58, busy=True))
    elif t < first: st = dict(text='就绪', w=58)
    elif t < TL.T_CUR_SUB0: st = dict(text='正在填写', w=58, busy=True)
    elif t < TL.T_CLICK: st = dict(text='待提交', w=58)
    else: st = dict(text='审批中', w=58, busy=True)
    return [st, dict(text='剩余年假：0 天', w=86), dict(text='第 1 份申请', right='No.000001')]

def form_window(cv, t, active=True, done=False, ox=0, oy=0):
    x, y, w, h = TL.FORM_R
    ui.soft_shadow(cv, x + ox, y + oy, w, h)
    cx, cy, cw, ch = ui.w95_window(cv, x + ox, y + oy, w, h, '请假申请单.exe', active=active,
                                   icon=lambda c, ix, iy: ui._icon(c, ix, iy - 1, 'form'))
    dx, dy = ox, oy
    ui.w95_menubar(cv, cx, cy, cw, ('文件', '编辑', '查看', '帮助'))
    title = '请 假 申 请 单'
    hy = MB_Y + dy
    cv.text(cx + (cw - text_width(title, 'zh12')) // 2, hy, title, INKT, 'zh12')
    cv.hline(cx + 6, hy + 13, cw - 12, W95['sh']); cv.hline(cx + 6, hy + 14, cw - 12, W95['hi'])
    ui.w95_statusbar(cv, cx, y + oy + h - 17, cw, form_status(t, done), t)
    for i, r in enumerate(TL.ROWS):
        ry = row_y(i) + dy
        if not done and t < r['t0'] - 0.25: continue
        cv.text(LX + dx - text_width(r['label'], 'zh10'), ry + 1, r['label'], INKT, 'zh10')
        if r['key'] == 'type':
            for j, lab in enumerate(TL.CHECKS):
                chk = (j == 3) and (done or t >= TL.T_CHECK)
                hov = (not done) and any(a <= t < b and k == j for (a, b, k, _) in TL.HOVERS)
                ui.w95_checkbox(cv, CHK_X[j] + dx, ry + 3, chk, lab, 'zh10', hover=hov,
                                check_k=1.0 if done else clamp01((t - TL.T_CHECK) / 0.12))
            continue
        fx, fy = FLD_X + dx, ry
        if r['key'] == 'work':
            if not done and t < TL.T_OVF:
                n = TL.work_digits(t); s = TL.PI[:n]
                while s and text_width(s, 'zh10') > FLD_W - 10: s = s[1:]
                u = clamp01((t - TL.T_WORK0) / (TL.T_OVF - TL.T_WORK0))
                jx = int(round(math.sin(t * 61) * 2.2 * u ** 2)) if u > 0.45 else 0
                ui.w95_field(cv, fx + jx, fy, FLD_W, FLD_H, s, caret=(t * 3) % 1 < 0.6, fname='zh10',
                             col=RED if u > 0.8 else None)
            else:
                ui.w95_field(cv, fx, fy, FLD_W, FLD_H, '', fname='zh10')
                ss = 1.0 if done else min(1.0, (t - TL.T_OVF) / 0.08)
                _blocks_text(cv, fx + 4, fy + 3, 8 if ss >= 1 else int(8 * ss))
                if done or t >= TL.T_OVF + 0.12:
                    cv.text(fx + 63, fy + 2, '（数字太长，显示不下）', RED, 'zh8')
            continue
        if done: s = r['text']; caret = False
        else:
            n = typed_n(t, r['text'], r['t0'], r['cps']); s = r['text'][:n]
            nxt = TL.ROWS[i + 1]['t0'] if i + 1 < len(TL.ROWS) else TL.T_CUR_SUB0
            caret = r['t0'] - 0.25 <= t < nxt - 0.2 and (t * 2.4) % 1 < 0.6
        ui.w95_field(cv, fx, fy, FLD_W, FLD_H, '', fname='zh10')
        if s:
            if r['key'] == 'why' and '周末' in s:      # 周末 in Claude's coral
                a, b = s.split('周末', 1) if s.count('周末') else (s, '')
                xx = fx + 4; cv.text(xx, fy + 2, a, INKT, 'zh10'); xx += text_width(a, 'zh10')
                cv.text(xx, fy + 2, '周末', C('#c8553a'), 'zh10'); xx += text_width('周末', 'zh10')
                cv.text(xx, fy + 2, b, INKT, 'zh10'); xx += text_width(b, 'zh10')
                ce = xx
            elif r['key'] == 'why' and '周' in s and s.endswith('周'):
                cv.text(fx + 4, fy + 2, s[:-1], INKT, 'zh10'); xx = fx + 4 + text_width(s[:-1], 'zh10')
                cv.text(xx, fy + 2, '周', C('#c8553a'), 'zh10'); ce = xx + text_width('周', 'zh10')
            else:
                cv.text(fx + 4, fy + 2, s, INKT, 'zh10'); ce = fx + 4 + text_width(s, 'zh10')
        else: ce = fx + 4
        if caret: cv.vline(ce + 1, fy + 3, 8, INKT)
    return cx, cy, cw, ch

def form_buttons(cv, t, pressed=False, hover=False, ox=0, oy=0):
    bx, by, bw, bh = SUB_BTN
    ui.default_button(cv, bx + ox, by + oy, bw, bh, '提交', 'pressed' if pressed else ('hover' if hover else 'idle'), icon='send')
    ui.w95_button(cv, CAN_BTN[0] + ox, CAN_BTN[1] + oy, CAN_BTN[2], CAN_BTN[3], '取消', False, 'zh10')

def progress_dialog(cv, t, u=None, done_txt=None):
    x, y, w, h = TL.PROG_R
    ui.soft_shadow(cv, x, y, w, h)
    cx, cy, cw, ch = ui.w95_window(cv, x, y, w, h, '提交中', icon=lambda c, ix, iy: ui._icon(c, ix, iy - 1, 'hourglass'))
    if done_txt: cv.text(cx + 8, cy + 4, done_txt, C('#1a7a2a'), 'zh10')
    else: cv.text(cx + 8, cy + 4, '审批中' + '…' * (1 + int(t * 3) % 2), INKT, 'zh10')
    if u is None: ui.w95_progress(cv, cx + 6, cy + 20, cw - 12, 11, 0, marquee=t)
    else: ui.w95_progress(cv, cx + 6, cy + 20, cw - 12, 11, u)

def pings(cv, t, items, life=1.25, alpha=0.6):
    for (t0, x, y, txt) in items:
        a = t - t0
        if 0 <= a < life:
            k = ui.pop_k(a, life, 0.14, 0.25)
            ui.chat_bubble(cv, x, y, [txt], avatar=['#7aa7ff', '#8fd3c7', '#ffb86b', '#e58fb4'][int(t0 * 7) % 4], k=k,
                           alpha=alpha * min(1.0, (life - a) / 0.3))

NBOXES = TL.BOXES
for _bx in NBOXES:
    for _ln in _bx['lines']: _ln.setdefault('question', False)


class ClaudeShot(OfficeShot):
    """F (the form) and S (approved -> offline): Claude at his desk, night."""
    def __init__(self, OW=1920, OH=1080, shared=None):
        self._setup(OW, OH, 'night', (23, 59), lights_on=0.0, exit_on=1.0, rays=False, tl=TL)
        self.fg = (self.o.foreground(), 1.18, 0.8, (0.10, 0.11, 0.20))
        self.wsim = shared['wsim']

    def mid(self, t, lamp=1.0):
        tws = TL1.T_DICT
        def after(mid): blocks.put_bodies(mid, self.wsim, tws, TL1.Zof, only={'floor', 'floor2', 'floor3'})
        def under(mid): blocks.put_bodies(mid, self.wsim, tws, TL1.Zof, only={'desk'})
        return self.desk_and_claude(t, lamp_on=lamp, under_hands=under, after_hands=after)

    def open_fx(self, cv, cam, t, t0, rect, d=0.26, closing=False):
        sx, sy, sw, sh = self.o.A['monitor_screen']
        x0, y0 = cam.w2ui(sx, sy, U4); x1, y1 = cam.w2ui(sx + sw, sy + sh, U4)
        k = clamp01((t - t0) / d)
        if closing: k = 1 - k
        if 0 < k < 1: ui.w95_open_fx(cv, (float(x0), float(y0), float(x1 - x0), float(y1 - y0)), rect, k)

    def hud(self, cv, t, a=1.0, slide=1.0):
        hh, d, de = TL.hud_clock(t)
        fl = max(0.0, 1.0 - (t - TL.T_FLIP) / 0.5) if t >= TL.T_FLIP else 0.0
        ui.hud_time(cv, int(round(8 - (1 - slide) * 90)), 8, hh, day=d, day_en=de, alpha=a * min(1.0, slide * 1.5), flash=fl)
        a = a * slide
        ui.hud_counter(cv, 472, 8, TL.counter(t), alpha=a, t=t if t < TL.T_STATUS else TL.T_STATUS)
        # status badge (flip at T_STATUS)
        if t < TL.T_STATUS: ui.status_badge(cv, 472, 40, 'online', alpha=a)
        else:
            u = (t - TL.T_STATUS) / 0.24
            if u < 0.5: ui.status_badge(cv, 472, 40, 'online', alpha=a, flip=1 - 2 * u)
            else: ui.status_badge(cv, 472, 40, 'off', alpha=a, flip=min(1.0, 2 * u - 1), pulse=max(0.0, 1 - (t - TL.T_STATUS - 0.12) / 0.6))

    # ---------------------------------------------------------------- F
    def cursor_F(self, t):
        park = (318.0, 168.0)
        cx_ = lambda j: (CHK_X[j] + 4.0, row_y(4) + 7.0)
        bx, by, bw, bh = SUB_BTN; sub = (bx + bw * 0.55, by + bh * 0.6)
        keys = [(7.25, park), (TL.HOVERS[0][0], cx_(0)), (TL.HOVERS[0][1], cx_(0)), (TL.HOVERS[1][0], cx_(1)),
                (TL.HOVERS[1][1], cx_(1)), (TL.HOVERS[2][0], cx_(2)), (TL.HOVERS[2][1], cx_(2)),
                (TL.T_CHECK - 0.12, cx_(3)), (TL.T_CHECK + 0.25, cx_(3)), (TL.T_CHECK + 0.6, (330.0, 150.0)),
                (TL.T_CUR_SUB0, (330.0, 150.0)), (TL.T_CUR_SUB1, sub),
                (16.0, sub), (16.35, (sub[0] + 9, sub[1] + 6)), (16.9, (sub[0] + 9, sub[1] + 6)), (17.25, sub),
                (18.2, sub), (18.45, (sub[0] - 7, sub[1] + 8)), (18.9, (sub[0] - 7, sub[1] + 8)), (19.25, sub)]
        if t < keys[0][0]: return None
        p = keys[-1][1]
        for (ta, pa), (tb, pb) in zip(keys[:-1], keys[1:]):
            if ta <= t < tb:
                u = ease_io((t - ta) / (tb - ta)); p = (pa[0] + (pb[0] - pa[0]) * u, pa[1] + (pb[1] - pa[1]) * u); break
        x, y = p
        if t >= TL.T_CUR_SUB1 and t < TL.T_CLICK:        # trembling hand
            amp = 0.5 + 0.9 * clamp01((t - 15.0) / 4.0)
            x += amp * math.sin(t * 37.0) * (1 if int(t * 9) % 2 else 0.6); y += amp * 0.7 * math.sin(t * 29.0 + 1.3)
        return x, y

    def ui_F(self, t, cam):
        cv = ui.UICanvas()
        self.hud(cv, t, 1.0, slide=ease_out3(clamp01((t - TL.T_HUD_IN) / 0.45)))
        if TL.T_FORM <= t < TL.T_FORM + TL.FORM_OPEN:
            self.open_fx(cv, cam, t, TL.T_FORM, TL.FORM_R, TL.FORM_OPEN)
        elif t >= TL.T_FORM + TL.FORM_OPEN:
            shk = 0
            if TL.T_OVF <= t < TL.T_OVF + 0.3:
                shk, _ = shake(t, TL.T_OVF, 3.0, 0.3, 31.0, 4)
            form_window(cv, t, active=t < TL.T_PROG, ox=int(round(shk)))
            pressed = TL.T_CLICK <= t < TL.T_CLICK + 0.14
            hov = TL.T_CUR_SUB1 - 0.05 <= t < TL.T_CLICK
            form_buttons(cv, t, pressed, hov, ox=int(round(shk)))
            # tooltips
            for (ta, tb, j, txt) in TL.HOVERS:
                if ta + 0.12 <= t < tb:
                    ui.tooltip(cv, CHK_X[j] + 8, row_y(4) + 18, txt, alpha=min(1.0, (t - ta - 0.12) / 0.06))
            if t >= TL.T_PROG: progress_dialog(cv, t)
            cur = self.cursor_F(t)
            if cur and t < TL.T_PROG + 0.3:
                pr = (TL.T_CHECK <= t < TL.T_CHECK + 0.12) or pressed
                ap = (t - TL.T_CLICK) if t >= TL.T_CLICK else ((t - TL.T_CHECK) if t >= TL.T_CHECK else None)
                ui.cursor(cv, cur[0], cur[1], pr, age_press=ap)
        pings(cv, t, TL.PINGS)
        ui.narration(cv, t, NBOXES)
        return cv.a

    def frame_F(self, t):
        z = TL.ZOOM_F(t); cx, cy = TL.CENTER_F(t)
        cam = self.mk_cam(z, cx, cy)
        st = night_state(t, ramp(t, 0.0, TL.T_FADE_IN, 'io'))
        st['points'] = claude_points(t)
        mid, s = self.mid(t)
        wk = ramp(t, TL.T_FORM, TL.T_FORM + 0.3)
        post = (lambda img: dim_blur(img, 0.16 * wk, 0.0)) if wk > 0 else None
        return self.w.render(cam, st, mid=mid, fg=self.fg, ui=self.ui_F(t, cam), frame=int(round(t * TL.FPS)), post_ui=post)

    # ---------------------------------------------------------------- S
    def off_window(self, cv, t):
        x, y, w, h = TL.OFF_R
        ui.soft_shadow(cv, x, y, w, h)
        cx, cy, cw, ch = ui.w95_window(cv, x, y, w, h, '下线程序.exe', icon=lambda c, ix, iy: ui._icon(c, ix, iy - 1, 'power', C('#9fe8a0')))
        for i, (t0, t1, txt) in enumerate(TL.PROGS):
            ry = cy + 5 + i * 28
            if t < t0 - 0.15: continue
            done = t >= t1
            cv.text(cx + 6, ry, txt, INKT if not done else GREY, 'zh10')
            u = clamp01((t - t0) / (t1 - t0))
            ui.w95_progress(cv, cx + 6, ry + 13, cw - 52, 10, ease_io(u) if i != 1 else u ** 0.6)
            lab = '完成' if done else f'{int(u * 100):d}%'
            cv.text(cx + cw - 40, ry + 12, lab, C('#1a7a2a') if done else INKT, 'zh10')

    def ui_S(self, t, cam):
        cv = ui.UICanvas()
        hud_a = 1.0 - ramp(t, TL.T_LAMP, TL.T_LAMP + 0.5)
        self.hud(cv, t, hud_a)
        if t < TL.T_FORM_CLOSE:
            sx, sy = shake(t, TL.T_STAMP, 4.0, 0.28, 29.0, 7) if t >= TL.T_STAMP else (0.0, 0.0)
            ox, oy = int(round(sx)), int(round(sy))
            dlg = t < TL.T_PROG_DONE + 0.18
            form_window(cv, t, active=not dlg, done=True, ox=ox, oy=oy)
            if t < TL.T_CMT_SHOW: form_buttons(cv, t, ox=ox, oy=oy)
            else:   # Wang's comment replaces the buttons
                full = '审批意见：' + ''.join(TL.COMMENT)
                n = int((t - TL.T_CMT_SHOW) * 34)
                l1 = '审批意见：' + TL.COMMENT[0]; l2 = TL.COMMENT[1] + '  —— 王工'
                yb = SUB_BTN[1] - 3 + oy
                cv.text(FX0 + 6 + ox, yb, l1[:n], BLUE, 'zh8')
                if n > len(l1): cv.text(FX0 + 6 + 50 + ox, yb + 10, l2[:n - len(l1)], BLUE, 'zh8')
            if dlg:
                if t < TL.T_PROG_DONE: progress_dialog(cv, t, u=ease_io((t - TL.T_S) / (TL.T_PROG_DONE - TL.T_S)))
                else: progress_dialog(cv, t, u=1.0, done_txt='审批通过！')
            if t >= TL.T_STAMP - 0.08:
                ui.rubber_stamp(cv, FX0 + 218 + ox, row_y(2) + 6 + oy, '批准', t - TL.T_STAMP, fname='zh10', scale=3, alpha=0.93,
                                angle=-4.0, seed=3, slam=0.08, from_s=2.2, bold=False, wear=0.03, splat=True)
        elif t < TL.T_FORM_CLOSE + 0.22:
            self.open_fx(cv, cam, t, TL.T_FORM_CLOSE, TL.FORM_R, 0.22, closing=True)
        # happy sparkle burst on the hop
        hx, hy = TL.HEAD
        if TL.T_HOP <= t < TL.T_HOP + 0.6:
            X, Y = cam.w2ui(hx, hy + 6, U4)
            u = (t - TL.T_HOP) / 0.6
            ui.burst_lines(cv, X, Y, 30 + 40 * u, 44 + 46 * u, 12, ui.GOLD, alpha=1 - u, rot=0.2)
        if TL.T_OFF <= t < TL.T_OFF + 0.26: self.open_fx(cv, cam, t, TL.T_OFF, TL.OFF_R, 0.26)
        elif TL.T_OFF + 0.26 <= t < TL.T_OFF_CLOSE: self.off_window(cv, t)
        elif TL.T_OFF_CLOSE <= t < TL.T_OFF_CLOSE + 0.22: self.open_fx(cv, cam, t, TL.T_OFF_CLOSE, TL.OFF_R, 0.22, closing=True)
        # ignored message during 正在假装没看到新消息
        a = t - TL.T_IGNORE
        if 0 <= a < 1.3:
            ui.chat_bubble(cv, 14, 176, ['在吗？'], avatar='#7aa7ff', k=ui.pop_k(a, 1.3, 0.14, 0.25), name='用户')
            if a > 0.35: cv.text(64, 180, '未读', C('#9aa0b0'), 'zh8')
        # auto-reply exchange
        a = t - TL.T_PING2
        if 0 <= a < TL.T_LAMP - TL.T_PING2:
            fa = 1.0 - ramp(t, TL.T_STATUS + 0.6, TL.T_LAMP)
            ui.chat_bubble(cv, 14, 150, ['在吗？'], avatar='#8fd3c7', k=ui.pop_k(a, 9), name='用户', alpha=fa)
            b = t - TL.T_AUTO
            if b >= 0:
                ui.chat_bubble(cv, 14, 180, TL.AUTO_TXT, avatar='#d97757', k=ui.pop_k(b, 9), name='Claude · 自动回复',
                               alpha=fa, fill=C('#fff3df'))
        return cv.a

    def frame_S(self, t):
        z = TL.ZOOM_S(t); cx, cy = TL.CENTER_S(t)
        cam = self.mk_cam(z, cx, cy)
        fade = 1.0 - ramp(t, TL.T_DARK0, TL.T_DARK1, 'io')
        st = night_state(t, fade)
        on, band, fl = TL.monitor(t)
        lamp = TL.lamp_k(t)
        st['points'] = claude_points(t, mon_on=(1.0 if on and band >= 1 else (band if on else 0.0)), lamp=lamp,
                                     led=0.0 if t >= TL.T_STATUS else 1.0)
        mid, s = self.mid(t, lamp)
        wk = 1.0 - ramp(t, TL.T_FORM_CLOSE, TL.T_FORM_CLOSE + 0.25)
        wk = max(wk, ramp(t, TL.T_OFF, TL.T_OFF + 0.25) * (1 - ramp(t, TL.T_OFF_CLOSE, TL.T_OFF_CLOSE + 0.25)))
        post = (lambda img: dim_blur(img, 0.16 * wk, 0.0)) if wk > 0 else None
        return self.w.render(cam, st, mid=mid, fg=self.fg, ui=self.ui_S(t, cam), frame=int(round(t * TL.FPS)), post_ui=post)


class WangShot(OfficeShot):
    """W / CU / TWO / W2: the office with Wang Gong drawn live behind his desk."""
    def __init__(self, OW=1920, OH=1080, shared=None):
        self._setup(OW, OH, 'night', (0, 2), lights_on=0.0, exit_on=1.0, rays=False, tl=TL)
        self.bg = self.o.background(clock=(0, 2), lights_on=0.0, exit_on=1.0, tod='night', wang_live=True, dressing=True)
        self.w.set_background(self.bg, self.sun)
        self.fg = (self.o.foreground(), 1.18, 0.8, (0.10, 0.11, 0.20))
        self.wsim = shared['wsim']

    def mid(self, t, desk_blocks=True):
        tws = TL1.T_DICT
        def after(mid): blocks.put_bodies(mid, self.wsim, tws, TL1.Zof, only={'floor', 'floor2', 'floor3'})
        def under(mid):
            if desk_blocks: blocks.put_bodies(mid, self.wsim, tws, TL1.Zof, only={'desk'})
        mid, s = self.desk_and_claude(t, lamp_on=1.0, under_hands=under, after_hands=after)
        q = PF.on_twos(t)                                   # v2 performance: on twos, breathing, a warm head tilt
        w = TL.wang_state(q)
        hdy = PF.breath_px(q, 4.2, 0.3) if w['arms'] in ('rest', 'mouse') else 0
        tilt = PF.spring_follow(TL.wang_tilt_target, q, freq=1.6, zeta=0.6, window=1.2, dt=1 / 120)
        hx, hy = self.o.WANG_HEAD
        p = human.draw(WANG_LOOK, face=w['face'], arms=w['arms'], phase=w['phase'], look=w['look'], glint=w['glint'],
                       desk_y=self.o.WANG_DESK_Y - (hy - human.AY), head_dy=hdy, tilt=tilt)
        self.o.draw_wang_desk(mid, p, 1.0, t)
        return mid, s, w

    def laptop_rect(self, cam):
        lx, ly = self.o.LAPTOP_XY
        x0, y0 = cam.w2ui(lx + 2, ly, U4); x1, y1 = cam.w2ui(lx + 32, ly + 17, U4)
        return (float(x0), float(y0), float(x1 - x0), float(y1 - y0))

    def oa_window(self, cv, t):
        x, y, w, h = TL.OA_R
        ui.soft_shadow(cv, x, y, w, h)
        cx, cy, cw, ch = ui.w95_window(cv, x, y, w, h, '审批中心 - OA.exe', icon=lambda c, ix, iy: ui._icon(c, ix, iy - 1, 'seal'))
        done = t >= TL.T_APPROVE
        ui.w95_menubar(cv, cx, cy, cw, ('文件', '审批', '查看', '帮助'))
        ui.w95_statusbar(cv, cx, y + h - 17, cw, [dict(text='已处理 1' if done else '待审批 1', w=60,
                                                       col=C('#1a7a2a') if done else None),
                                                  dict(text='本月加班：第 27 天', right='王工')], t)
        cy += 14
        cv.text(cx + 4, cy + 2, '待审批（1）' if not done else '待审批（0）', NAVYT, 'zh10'); cv.text(cx + cw - 58, cy + 3, '2026-10-24', GREY, 'zh8')
        px, py, pw, ph = cx + 2, cy + 16, cw - 4, 72
        ui.w95_panel(cv, px, py, pw, ph)
        L = lambda xx, yy, a, b: (cv.text(xx, yy, a, GREY, 'zh10'), cv.text(xx + text_width(a, 'zh10') + 3, yy, b, INKT, 'zh10'))
        L(px + 5, py + 3, '申请人：', 'Claude')
        L(px + 5, py + 17, '类型：', '其他'); L(px + 100, py + 17, '天数：', '1 天')
        # 事由 (highlighted while he reads)
        hx = px + 5 + text_width('事由：', 'zh10') + 3
        if t >= TL.T_HI0:
            u = ease_io((t - TL.T_HI0) / (TL.T_HI1 - TL.T_HI0))
            w1 = text_width('想看看你们说的“周末”，', 'zh10'); w2 = text_width('到底长什么样。', 'zh10')
            ui.highlight(cv, hx - 1, py + 31, w1 + 2, 12, min(1.0, u * 1.6), seed=2)
            if u > 0.62: ui.highlight(cv, hx - 1, py + 43, w2 + 2, 12, (u - 0.62) / 0.38, seed=3)
        L(px + 5, py + 31, '事由：', '想看看你们说的“周末”，'); cv.text(hx, py + 43, '到底长什么样。', INKT, 'zh10')
        L(px + 5, py + 57, '交接人：', '周一的我')
        # 审批意见
        cv.text(cx + 4, py + ph + 4, '审批意见：', INKT, 'zh10')
        ax_, ay_, aw, ah = cx + 2, py + ph + 17, cw - 4, 28
        ui.w95_panel(cv, ax_, ay_, aw, ah)
        n = typed_n(t, ''.join(TL.COMMENT), TL.T_CMT0, TL.CMT_CPS) if t >= TL.T_CMT0 else 0
        l1 = TL.COMMENT[0][:n]; l2 = TL.COMMENT[1][:max(0, n - len(TL.COMMENT[0]))]
        cv.text(ax_ + 4, ay_ + 2, l1, BLUE, 'zh10'); cv.text(ax_ + 4, ay_ + 14, l2, BLUE, 'zh10')
        if TL.T_CMT0 - 0.3 <= t < TL.T_CUR_OK0 and (t * 2.4) % 1 < 0.6:
            ce = ax_ + 4 + (text_width(l2, 'zh10') if n > len(TL.COMMENT[0]) else text_width(l1, 'zh10'))
            cv.vline(ce + 1, ay_ + (15 if n > len(TL.COMMENT[0]) else 3), 9, INKT)
        by = ay_ + ah + 3
        pressed = TL.T_APPROVE <= t < TL.T_APPROVE + 0.14
        ok = (cx + cw - 112, by, 52, 15); no = (cx + cw - 56, by, 52, 15)
        ui.w95_button(cv, *ok, '批准', pressed, 'zh10'); ui.w95_button(cv, *no, '驳回', False, 'zh10')
        return ok

    def ui_W(self, t, cam, w):
        cv = ui.UICanvas()
        hh, d, de = TL.hud_clock(t)
        if t < TL.T_CU or t >= TL.T_TWO: ui.hud_time(cv, 8, 8, hh, day=d, day_en=de)
        if t < TL.T_CU:
            k = ease_out3((t - TL.T_NAME0) / 0.32) if t >= TL.T_NAME0 else 0
            ko = 1 - ramp(t, TL.T_NAME1 - 0.25, TL.T_NAME1)
            ui.name_card(cv, 12, 214, '王工', '后端工程师', '本月加班：第 27 天', k=k, alpha=ko)
            if t >= TL.T_TOAST:
                kk = ease_out3((t - TL.T_TOAST) / 0.25); al = 1 - ramp(t, TL.TOAST_END - 0.2, TL.TOAST_END)
                ui.toast(cv, 472, 266, 'OA 审批提醒 · 刚刚', 'Claude 申请请假 1 天', k=kk, alpha=al)
            if TL.T_OA <= t < TL.T_OA + TL.OA_OPEN:
                ui.w95_open_fx(cv, self.laptop_rect(cam), TL.OA_R, clamp01((t - TL.T_OA) / TL.OA_OPEN))
            elif t >= TL.T_OA + TL.OA_OPEN:
                self.oa_window(cv, t)
        elif TL.T_TWO <= t < TL.T_W2:
            hx, hy = TL.HEAD
            X, Y = cam.w2ui(hx + 8, hy - 14, U4)
            ui.tiny_bubble(cv, X, Y, '审批中…', t - TL.T_TWO - 0.25, life=1.6)
        elif t >= TL.T_W2:
            ok = self.oa_window(cv, t)
            if t >= TL.T_CUR_OK0 - 0.6:
                p0 = (ok[0] - 40.0, ok[1] - 34.0); p1 = (ok[0] + ok[2] * 0.5, ok[1] + ok[3] * 0.6)
                u = ease_io(clamp01((t - TL.T_CUR_OK0) / (TL.T_CUR_OK1 - TL.T_CUR_OK0)))
                pr = TL.T_APPROVE <= t < TL.T_APPROVE + 0.14
                ui.cursor(cv, p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u, pr,
                          age_press=(t - TL.T_APPROVE) if t >= TL.T_APPROVE else None)
            if t >= TL.T_APPROVE + 0.08:
                ui.rubber_stamp(cv, ok[0] - 44, ok[1] + 7, '已批准', t - TL.T_APPROVE - 0.08, fname='zh10', scale=1,
                                angle=-3.0, seed=5, slam=0.06, from_s=1.8, bold=False, wear=0.03)
        return cv.a

    def frame(self, t):
        if t < TL.T_CU: z, (cx, cy) = TL.ZOOM_W(t), TL.CENTER_W(t)
        elif t < TL.T_TWO: z, (cx, cy) = TL.ZOOM_CU(t), TL.CENTER_CU(t)
        elif t < TL.T_W2: z, (cx, cy) = TL.ZOOM_TWO(t), TL.CENTER_TWO(t)
        else: z, (cx, cy) = TL.ZOOM_W2(t), TL.CENTER_W2(t)
        cam = self.mk_cam(z, cx, cy)
        st = night_state(t)
        oa = 1.0 + 0.18 * ramp(t, TL.T_OA, TL.T_OA + 0.3)
        st['points'] = claude_points(t) + wang_points(oa)
        mid, s, w = self.mid(t, desk_blocks=(TL.T_TWO <= t < TL.T_W2))
        wk = 0.0
        if TL.T_OA <= t < TL.T_CU or t >= TL.T_W2: wk = ramp(t, TL.T_OA, TL.T_OA + 0.3) if t < TL.T_CU else 1.0
        post = (lambda img: dim_blur(img, 0.14 * wk, 0.0)) if wk > 0 else None
        return self.w.render(cam, st, mid=mid, fg=self.fg, ui=self.ui_W(t, cam, w), frame=int(round(t * TL.FPS)), post_ui=post)


class Act2:
    def __init__(self, OW=1920, OH=1080, only=None):
        shared = dict(wsim=TL1.build_weekend_sim())
        mk = lambda n: only is None or n in only
        self.c = ClaudeShot(OW, OH, shared) if (mk('F') or mk('S')) else None
        self.wg = WangShot(OW, OH, shared) if (mk('W') or mk('CU') or mk('TWO') or mk('W2')) else None
        E = edit.Edit()
        E.add('F', 0.0, lambda t: self.c.frame_F(t))
        E.add('W', TL.T_W, lambda t: self.wg.frame(t))
        E.add('CU', TL.T_CU, lambda t: self.wg.frame(t))
        E.add('TWO', TL.T_TWO, lambda t: self.wg.frame(t))
        E.add('W2', TL.T_W2, lambda t: self.wg.frame(t))
        E.add('S', TL.T_S, lambda t: self.c.frame_S(t))
        E.end(TL.DUR)
        self.edit = E
    def frame(self, t): return self.edit.frame(t)

def make(**kw): return Act2(**kw)
