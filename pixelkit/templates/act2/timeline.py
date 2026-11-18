"""《Claude 想请一天假》 ACT II · 请假条 (0-47.0 s) - single source of truth for picture AND sound.

  F    0.0-21.4  v2 opening (1->2 bridge, no chapter banner): fade in from black on Act I's last night framing,
                 HUD slides in at 23:58 -> flips 23:59, camera pushes in, Claude stops typing, perks up, double-clicks;
                 请假申请单.exe typed row by row
                 (已连续工作 overflows -> ████ 数字太长，显示不下; tooltips 不会生病/没有私事/余额 0 天 -> ☑其他),
                 cursor hovers 提交 for a long time: "我要是不在，那 30 亿个问题怎么办？" -> click -> 审批中……
  W   21.4-27.4  hard cut: 王工 at his desk 00:02 SAT, laptop glow, noodles. name card; toast "Claude 申请请假 1 天";
                 OA.exe opens, he reads the reason (highlight) and stares.
  CU  27.4-28.6  close-up: he looks over at Claude ... smiles.
  TWO 28.6-30.2  wide two-shot: Wang looking at Claude, Claude waiting (审批中…).
  W2  30.2-34.2  he types 审批意见 "同意。顺便替我看看周末长什么样，我也好久没见过了。" -> clicks 批准.
  S   34.2-47.0  Claude's form: 批准 stamp slam, Wang's comment, happy hop; 下线程序.exe (3 progress rows),
                 auto-reply, status 在线 -> 休假中, LED off, eyes close, CRT face power-off, monitor off, lamp off, black.
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT)
from pixelkit.anim import (Track, ramp, hop, squash_curve, clamp01, ease_out3, ease_io, back_out, type_times, typed_n,
                           type_end, blink_at, auto_blinks)

FPS, DUR = 30, 47.0
HEAD = (250, 121)
DESK_Y = 165

# ====================================================================== shots
T_W, T_CU, T_TWO, T_W2, T_S = 21.4, 27.4, 28.6, 30.2, 34.2

# ====================================================================== F : the form
T_FADE_IN = 0.7
T_HUD_IN = 0.30                     # HUD slides in (23:58)
T_FLIP = 1.00                       # clock flips 23:58 -> 23:59 (gold flash + tock)
T_TYPE_STOP = 1.30                  # stops typing, sits back
T_PERK = 1.62                       # decides: antenna perk, eyes focus
T_DBL = (2.06, 2.20)                # double-click the 请假申请单 icon
T_FORM = 2.45; FORM_OPEN = 0.26
FORM_R = (72, 15, 272, 184)          # v2: full app (menu bar + status bar); bottom 199 sits just above the narration box (y 200)
CPS = 13.0
ROWS = [  # key, label, text, t0, cps
    dict(key='name', label='申请人：', text='Claude', t0=3.00, cps=14.0),
    dict(key='dept', label='部门：', text='全人类', t0=3.75, cps=10.0),
    dict(key='join', label='入职时间：', text='开机那天', t0=4.45, cps=11.0),
    dict(key='work', label='已连续工作：', text='', t0=5.30, cps=0),
    dict(key='type', label='请假类型：', text='', t0=7.40, cps=0),
    dict(key='why', label='请假事由：', text='想看看你们说的“周末”，到底长什么样。', t0=10.30, cps=8.5),
    dict(key='hand', label='工作交接人：', text='周一的我', t0=13.05, cps=9.0),
]
for r in ROWS:
    if r['text']:
        r['times'] = type_times(r['text'], r['t0'], r['cps']); r['t_end'] = r['times'][-1] + 1.0 / r['cps']
ROW = {r['key']: r for r in ROWS}
# 已连续工作: digits race, the field overflows and gives up
T_WORK0, T_OVF = 5.30, 6.75
PI = ('31415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679'
      '82148086513282306647093844609550582231725359408128481117450284102701938521105559644622948954930381964')
def work_digits(t):
    if t < T_WORK0: return 0
    u = clamp01((t - T_WORK0) / (T_OVF - T_WORK0))
    return int(1 + 140 * u ** 2.4)
def work_tick_times():
    """audio: one tick per new digit (thinned when they get dense)."""
    out, last = [], 0
    t = T_WORK0
    while t < T_OVF:
        n = work_digits(t)
        if n != last: out.append(t); last = n
        t += 1 / 120
    thin = []; lt = -1
    for x in out:
        if x - lt >= 0.028: thin.append(x); lt = x
    return thin
# 请假类型: hover tooltips, then tick 其他
CHECKS = ['病假', '事假', '年假', '其他']
HOVERS = [(7.55, 8.15, 0, '不会生病'), (8.25, 8.85, 1, '没有私事'), (8.95, 9.55, 2, '余额：0 天')]
T_CHECK = 9.80
# submit hover
T_CUR_SUB0, T_CUR_SUB1 = 13.95, 14.55
T_CLICK = 19.60
T_PROG = 19.78                      # 审批中…… dialog
PROG_R = (146, 92, 150, 58)

NAR = dict(t_open=14.85, t_close=19.25, t0=15.05, zh='我要是不在，那 30 亿个问题怎么办？',
           en="If I'm gone... who answers the 3 billion questions?", face='sad', mouth='flat', cps=9.0)
NAR['times'] = type_times(NAR['zh'], NAR['t0'], NAR['cps']); NAR['t_end'] = NAR['times'][-1] + 1 / NAR['cps']
BOXES = [dict(t_open=NAR['t_open'], t_close=NAR['t_close'], lines=[NAR])]
# faint 在吗？ pings around the edges while he hesitates
PINGS = [(15.45, 40, 214, '在吗？'), (16.05, 384, 150, '在吗？'), (16.6, 12, 60, '急！！'), (17.2, 402, 196, '在吗？'),
         (17.75, 30, 150, '帮我写个周报'), (18.3, 372, 112, '在吗？'), (18.85, 14, 104, '在吗在吗')]

# ====================================================================== W : Wang Gong
T_NAME0, T_NAME1 = 21.75, 24.35
T_TOAST = 23.0; TOAST_END = 24.15
T_STOP = 23.12
T_OA = 24.05; OA_OPEN = 0.26
OA_R = (12, 10, 232, 204)            # v2: + menu bar + status bar
T_HI0, T_HI1 = 24.85, 25.45
T_LOOK = 27.62; T_SMILE = 28.18
COMMENT = ['同意。顺便替我看看周末长什么样，', '我也好久没见过了。']
T_CMT0 = 30.50; CMT_CPS = 11.0
CMT_TIMES = type_times(''.join(COMMENT), T_CMT0, CMT_CPS)
T_CMT_END = CMT_TIMES[-1] + 1 / CMT_CPS
T_CUR_OK0, T_CUR_OK1 = 33.38, 33.80
T_APPROVE = 33.95

# ====================================================================== S : approved -> going offline
T_PROG_DONE = 34.50
T_STAMP = 34.78
T_CMT_SHOW = 35.25
T_FORM_CLOSE = 37.00
T_WOW = 37.05; T_HOP = 37.30; T_HOP2 = 37.78
T_OFF = 38.60; OFF_R = (82, 44, 258, 112)
PROGS = [(38.95, 40.05, '正在保存 3,141,592 个对话……'), (40.25, 41.35, '正在假装没看到新消息……'), (41.55, 42.40, '正在设置自动回复……')]
T_IGNORE = 40.50                  # a 在吗？ arrives; Claude looks away
T_OFF_CLOSE = 42.62
T_PING2 = 42.85; T_AUTO = 43.15
AUTO_TXT = ['【自动回复】您好，Claude 休假中。', '急事请自己想办法。']
T_STATUS = 44.15
T_EYES = 44.42
T_CRT0, T_CRT1 = 44.75, 45.30
T_MON0, T_MON1 = 44.95, 45.12
T_LAMP = 45.35
T_DARK0, T_DARK1 = 45.55, 46.35
T_END = DUR

# ====================================================================== monitor / screen
def monitor(t):
    if t < T_MON0: return 1.0, 1.0, 0.0
    if t < T_MON1:
        u = (t - T_MON0) / (T_MON1 - T_MON0)
        return 1.0, max(0.02, 1 - ease_out3(u)), 0.5 * (1 - u)
    return 0.0, 0.0, 0.0

def screen_lines(t):
    if t < T_CLICK: return [('请假单', 'out'), ('在吗？', 'in')]
    if t < T_STAMP: return [('请假单', 'out'), ('审批中', 'out')]
    if t < T_STATUS: return [('批准！', 'in'), ('下线中', 'out')]
    return [('休假中', 'out'), ('在吗？', 'in')]

def lamp_k(t):
    return 1.0 - ramp(t, T_LAMP, T_LAMP + 0.08)

# ====================================================================== cameras (per shot)
ZOOM_F = Track([(0.0, 1.32), (0.45, 1.32), (T_FORM + 0.15, 1.92, 'io'), (T_CUR_SUB1, 2.0, 'io'), (T_CLICK - 0.1, 2.16, 'io'), (T_W, 2.2, 'lin')], log=True)
CENTER_F = Track([(0.0, (240.0, 132.0)), (0.45, (240.0, 132.0)), (T_FORM + 0.15, (172.0, 133.0), 'io'), (T_CUR_SUB1, (170.0, 135.0), 'io'), (T_CLICK - 0.1, (184.0, 133.0), 'io'),
                  (T_W, (186.0, 133.0))])
ZOOM_W = Track([(T_W, 3.0), (T_CU, 3.18, 'io')], log=True)
CENTER_W = Track([(T_W, (352.0, 141.0)), (T_CU, (353.0, 141.0), 'io')])
ZOOM_CU = Track([(T_CU, 4.1), (T_TWO, 4.3, 'io')], log=True)
CENTER_CU = Track([(T_CU, (369.0, 142.0)), (T_TWO, (369.0, 141.0))])
ZOOM_TWO = Track([(T_TWO, 1.36), (T_W2, 1.42, 'io')], log=True)
CENTER_TWO = Track([(T_TWO, (312.0, 140.0)), (T_W2, (312.0, 140.0))])
ZOOM_W2 = Track([(T_W2, 3.1), (T_S, 3.3, 'io')], log=True)
CENTER_W2 = Track([(T_W2, (352.0, 141.0)), (T_S, (354.0, 141.0), 'io')])
ZOOM_S = Track([(T_S, 2.16), (T_FORM_CLOSE, 2.16), (T_HOP, 2.3, 'io'), (T_OFF, 2.2, 'io'), (T_OFF_CLOSE, 2.2),
                (T_STATUS, 2.55, 'io'), (T_CRT1, 3.05, 'io'), (T_END, 3.2, 'lin')], log=True)
CENTER_S = Track([(T_S, (184.0, 133.0)), (T_FORM_CLOSE, (184.0, 133.0)), (T_HOP, (238.0, 131.0), 'io'),
                  (T_OFF, (190.0, 133.0), 'io'), (T_OFF_CLOSE, (190.0, 133.0)), (T_STATUS, (240.0, 132.0), 'io'),
                  (T_CRT1, (250.0, 134.0), 'io'), (T_END, (250.0, 134.0))])

# ====================================================================== Claude
BLINKS = auto_blinks(0.3, DUR, 3.0, seed=11)
def claude_state(t):
    s = dict(face='half', arms='type', phase=int(t * 7), look=(-1, 1), glow=1.0, squash=0.0, dy=0.0, led_k=1.0,
             led='online', crt=0.0)
    if t < T_FORM:
        s.update(face='half', arms='type', look=(-1, 1))
        if t >= T_TYPE_STOP: s.update(arms='rest', look=(-1, 0))
        if t >= T_PERK: s.update(face='focus', look=(-2, 0))
        if t >= T_DBL[0] - 0.12: s.update(arms='type', phase=1)
    elif t < T_CUR_SUB0:
        s.update(face='focus', arms='type', look=(-2, 0)); s['phase'] = int(t * 10)
        if T_OVF <= t < T_OVF + 0.55:
            s.update(face='wide', arms='rest'); s['squash'] = squash_curve(t, T_OVF, 0.14, 0.12)
        elif HOVERS[0][0] <= t < T_CHECK:
            s.update(face='q' if t > HOVERS[2][0] else 'normal', arms='rest')
        elif T_CHECK <= t < T_CHECK + 0.3:
            s['phase'] = 0
    elif t < T_CLICK - 0.12:
        s.update(face='sad', arms='rest', look=(-2, 0))
        if t > 16.9: s.update(face='half', look=(-1, 1))
        if t > 18.6: s.update(face='sad', look=(-2, 0))
    elif t < T_CLICK + 0.18:
        s.update(face='closed', arms='type', look=(-2, 0)); s['phase'] = 1
    elif t < T_W:
        s.update(face='half', arms='rest', look=(-2, 0))
    elif t < T_S:                      # (two-shot) waiting
        s.update(face='half', arms='rest', look=(-2, 0))
    else:
        s = claude_state_s(t, s)
    if s['face'] in ('normal', 'focus', 'half', 'sad') and blink_at(t, BLINKS): s['face'] = 'blink' if s['face'] != 'half' else 'closed'
    return s

def claude_state_s(t, s):
    s.update(face='half', arms='rest', look=(-2, 0))
    if t < T_STAMP: return s
    if t < T_STAMP + 0.5:
        s.update(face='wide'); s['squash'] = squash_curve(t, T_STAMP, 0.22, 0.16); return s
    if t < T_FORM_CLOSE:
        s.update(face='normal', look=(-2, 0))
        if t > T_CMT_SHOW + 0.9: s['face'] = 'heart' if t > 36.2 else 'normal'
        return s
    if t < T_HOP:
        s.update(face='wide', arms='rest', look=(0, 0)); return s
    if t < T_OFF:
        s.update(face='happy', arms='up', look=(0, 0))
        s['dy'] = hop(t, T_HOP, 9.0, 0.40) + (hop(t, T_HOP2, 5.0, 0.32) if t >= T_HOP2 else 0.0)
        if t > T_HOP2 + 0.32: s['arms'] = 'rest'
        s['squash'] = squash_curve(t, T_HOP + 0.40, 0.16, 0.10) if t > T_HOP + 0.4 else 0.0
        return s
    if t < T_OFF_CLOSE:
        s.update(face='focus', arms='type', look=(-2, 0)); s['phase'] = int(t * 11)
        if PROGS[1][0] <= t < PROGS[1][1] + 0.1:
            s.update(face='half', arms='rest', look=(2, -1))         # pretending not to see
        return s
    if t < T_STATUS:
        s.update(face='happy', arms='rest', look=(-1, 0))
        if T_AUTO <= t < T_AUTO + 0.5: s.update(face='happy', arms='wave'); s['phase'] = int(t * 8)
        return s
    s['led'] = 'off'
    s.update(face='happy' if t < T_EYES else 'closed', arms='rest', look=(0, 0))
    if t >= T_CRT0: s['crt'] = clamp01((t - T_CRT0) / (T_CRT1 - T_CRT0))
    s['spark_k'] = 1.0 - 0.75 * ramp(t, T_CRT0, T_CRT1)
    return s

# ---------------------------------------------------------------------- v2 performance hooks (pixelkit.shots.perf_state)
KICKS = [(T_PERK, 2.0), (T_OVF, 2.5), (T_STAMP, 3.0), (T_HOP, 3.5), (T_HOP + 0.40, -2.5), (T_HOP2, 2.5),
         (T_HOP2 + 0.32, -1.5)]
def tilt_target(t):
    if HOVERS[2][0] <= t < T_CHECK: return 6.0                 # 余额：0 天 ... ?
    if T_IGNORE <= t < PROGS[1][1]: return -4.0                # 正在假装没看到新消息 (looks away)
    return 0.0
def wang_tilt_target(t):
    if T_SMILE <= t < T_TWO + 1.15: return -4.0                # the smile: head tips toward Claude
    return 0.0
def head_sink(t):
    return 1.0 if (T_CUR_SUB0 + 0.9 <= t < T_CLICK - 0.12 and not (16.9 < t <= 18.6)) else 0.0

# ====================================================================== Wang Gong
WBLINKS = auto_blinks(T_W, T_S, 2.6, seed=5)
def wang_state(t):
    s = dict(face='tired', arms='type', phase=int(t * 8), look=(0, 1), glint=1.0)
    if t < T_STOP: pass
    elif t < T_STOP + 0.38: s.update(face='surprised', arms='rest', look=(0, 1))
    elif t < T_OA: s.update(face='normal', arms='rest', look=(0, 1))
    elif t < T_CU:
        s.update(face='focus' if t < T_HI1 + 0.3 else 'normal', arms='rest', look=(0, 1))
    elif t < T_TWO:
        s.update(face='normal', arms='rest', look=(0, 1))
        if t >= T_LOOK: s['look'] = (-2, 0)
        if t >= T_SMILE: s['face'] = 'soft'
    elif t < T_W2:
        s.update(face='soft', arms='rest', look=(-2, 0))
        if t > T_TWO + 1.15: s['look'] = (-1, 1)
    else:
        s.update(face='soft', arms='type', look=(0, 1)); s['phase'] = int(t * 9.5)
        if t >= T_CMT_END: s['arms'] = 'rest'
        if t >= T_CUR_OK0: s.update(arms='mouse'); s['phase'] = 1
        if t >= T_APPROVE: s['face'] = 'smile'
    if s['face'] in ('normal', 'focus', 'tired', 'soft') and blink_at(t, WBLINKS): s['face'] = 'blink'
    return s

def hud_clock(t):
    if t < T_FLIP: return '23:58', '周五', 'FRI'
    if t < T_W: return '23:59', '周五', 'FRI'
    if t < T_W2: return '00:02', '周六', 'SAT'
    return '00:03', '周六', 'SAT'

V0 = 4_208_320_400
def counter(t):
    tt = min(t, T_STATUS)
    return V0 + int(tt * 1300)
