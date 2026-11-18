"""《Claude 想请一天假》 ACT V · 周一 (v3: 70.4 s) - single source of truth for picture AND sound.

  TR      0.0-  2.6  the bobber held up against the last light (Act IV echo) -> dissolve, same screen spot ->
                     the same bobber, standing on a little wooden base on Claude's desk, Monday morning (macro);
                     beside it a desk calendar: last Saturday ticked, next Saturday circled in red + a fish doodle.
  DESK    2.6- 11.6  one continuous pull-back from the macro to the desk: mug steam, sun through the blinds, the
                     HUD returns 「周一 MON 08:59」, status 休假中 -> 在线, a big stretch (antenna boing), a look at the
                     bobber, ^ ^.  09:00 叮: the desk jolts, the bobber wobbles, one finger steadies it.
                     小李: 在吗？帮我写周报。
  OK     11.6- 13.0  close: 好的！ + coin (identical to Act I).
  REPORT 13.0- 27.6  周报.doc streams out; P.S. 建议优化周末效率… typed, a look at the bobber, deleted;
                     P.S. 这周末，建议去河边坐坐，什么都不用做。 typed slowly; 发送.  v3: 小李 正在输入… ->
                     「……好。」「这周末去。」 -> Claude ^ ^ (the human answers the P.S. - replaces v2's black-card question).
  MID    27.6- 36.2  Claude and the bobber.  我以前没有周末。/ 现在，我知道它长什么样了。  a long held beat: it looks
                     over at the calendar (the circled Saturday), smiles; fade.   (v2's BLACK + TITLE cards removed)
  CRED   36.2- 70.4  v3「Claude 制作」 in a warm little theatre (red velvet, footlights, the cast in the front row);
                     Claude runs in, reads its own name, takes every job
                     (8 roles, a prop per job, COMBO x8), the cast list (鱼 …… 未到场), the film-stats card it flicks to
                     pieces (+83%), the no-fish-were-harmed disclaimer, 批准：一个相信它的人类, then it goes on leave.
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT)
from pixelkit.anim import (Track, ramp, clamp01, ease_io, ease_out3, auto_blinks, blink_at, boxes_prep, boxes_cut_lint,
                           type_times, typed_n, hop, squash_curve, shake)
from pixelkit import perform as PF

FPS = 30
T_DISS0, T_DISS1 = 1.55, 2.45            # dusk echo -> morning macro (same screen spot)
T_PULL0, T_PULL1 = 2.75, 6.35            # the pull-back (macro -> desk)
T_HUD = 4.55                             # HUD time + status badge slide in
T_ONLINE = 6.75                          # 休假中 -> 在线 (LED + badge flip), eyes open
T_STRETCH0, T_STRETCH1 = 7.25, 8.45      # the stretch (anticipation -> up -> release)
T_LOOK_B = 8.75                          # glance at the bobber
T_SMILE = 9.10                           # ^ ^
T_0900 = 10.05                           # 叮: HUD 09:00, desk jolt, message in
T_FINGER0, T_FINGER1 = 10.32, 11.20      # one finger steadies the bobber
T_OKCUT = 11.60                          # cut: close
T_OK = 11.85                             # 好的！ + coin
T_REPORT = 13.0
T_WIN_OPEN = 0.28
T_STREAM0 = 13.50                        # report body streams out
T_PS1 = 16.60                            # 'P.S. 建议优化周末效率，成功率可提高……'
T_PS1_LOOK = 19.00                       # stops; looks at the bobber
T_DEL0, T_DEL1 = 19.80, 20.30            # deleted
T_PS2 = 20.60                            # 'P.S. 这周末，建议去河边坐坐，什么都不用做。' (slowly)
T_SEND = 23.40                           # 发送
T_WIN_CLOSE = 23.95                      # the doc window folds back into the monitor
T_TYPING = 24.35                         # 小李 正在输入…
T_REPLY1, T_REPLY2 = 25.15, 26.00        # 「……好。」 「这周末去。」
T_REACT = 26.40                          # Claude ^ ^ (hop, antenna)
T_MID = 27.6
T_LOOK_CAL = T_MID + 6.45                # looks over at the calendar
T_MID_END = T_MID + 8.6                  # fade out of the morning
T_BLACK = T_MID_END                      # (alias: end of the morning sound beds)
T_CRED = T_MID_END
DUR = T_CRED + 34.2
CUTS = [T_PULL0 - 0.3, T_OKCUT, T_REPORT, T_MID, T_CRED]

HEAD = (250, 121)
DESK_Y = 165

# ====================================================================== desk objects
STAND_XY = (277, 162)                   # v3: the bobber's wooden base (11x4); the 「周末」 brick is gone
CAL_XY = (291, 137)                     # desk calendar (29x29), bottom on the desk top
MUG_XY = (323, 157)

# ====================================================================== the report
REPORT_TITLE = '周报 - 市场部 · 小李.doc'
REPORT_LINES = ['本周工作总结（10.20 - 10.24）',
                '1. 完成双十一活动方案 3 版，均已对齐',
                '2. 推进渠道合作 5 家，整体进展顺利',
                '3. 优化周会流程，沟通效率提升 20%',
                '下周计划：持续推进，再创佳绩。']
STREAM_CPS = 40.0
def _stream_times():
    out = []; t = T_STREAM0
    for ln in REPORT_LINES:
        out.append(t); t += len(ln) / STREAM_CPS + 0.12
    return out
STREAM_T = _stream_times()
PS1 = 'P.S. 建议优化周末效率，成功率可提高……'
PS2 = 'P.S. 这周末，建议去河边坐坐，什么都不用做。'
PS1_T = type_times(PS1, T_PS1, 14.0)
PS2_T = type_times(PS2, T_PS2, 11.0, pauses={'，': 0.22, '。': 0.0})
def ps_text(t):
    """-> (text, caret_visible, sel) of the P.S. line at t; sel = (a, b) selected char range or None.
    The hesitation deletion is a selection sweeping right->left over PS1, then the selected text vanishes."""
    if t < T_PS1: return '', True, None
    if t < T_DEL0:
        n = sum(1 for tc in PS1_T if t >= tc); return PS1[:n], True, None
    if t < T_DEL1:
        u = clamp01((t - T_DEL0) / ((T_DEL1 - T_DEL0) * 0.72)) ** 0.8
        a = int(round(len(PS1) - (len(PS1) - 5) * u))
        return PS1, False, (a, len(PS1))
    if t < T_PS2: return 'P.S. ', True, None
    n = sum(1 for tc in PS2_T if t >= tc)
    return PS2[:max(5, n)], True, None

# ====================================================================== narration
def C_(t0, zh, en, face='normal', mouth='flat', cps=9.0): return dict(t0=t0, zh=zh, en=en, face=face, mouth=mouth, cps=cps)
BOXES = boxes_prep([
    dict(t_open=T_MID + 0.45, t_close=T_MID + 6.3, lines=[
        C_(T_MID + 0.65, '我以前没有周末。', "I never used to have weekends.", face='normal', mouth='flat', cps=8.0),
        C_(T_MID + 3.0, '现在，我知道它长什么样了。', 'Now I know what one looks like.', face='happy', mouth='smile', cps=8.0),
    ]),
], cps=9.0)

# chat (UI px)
MSG = dict(t_in=T_0900 + 0.06, lines=['在吗？帮我写周报。'], name='市场部 · 小李', avatar='#7aa7ff', t_out=T_REPORT + 0.4)
REPLY = dict(t_in=T_TYPING, lines=['……好。', '这周末去。'], name='市场部 · 小李', avatar='#7aa7ff', t_out=T_MID - 0.4)
def reply_lines(t):
    """-> lines of 小李's reply bubble at t (None before it pops in); '···' while typing."""
    if t < T_TYPING: return None
    if t < T_REPLY1: return ['·' * (1 + int((t - T_TYPING) * 5) % 3)]
    if t < T_REPLY2: return REPLY['lines'][:1]
    return REPLY['lines']

# ====================================================================== camera
# macro framing: the bobber's sun dot at the same output spot as the Act IV echo shot (864, 612)
MACRO_Z = 6.0
BOB_XY = (STAND_XY[0] + 1, STAND_XY[1] - 18)          # top-left of the 9x19 fine bobber (eyelet on the base top)
DOT = (BOB_XY[0] + 4, BOB_XY[1] + 8)                   # its painted sun dot

ZOOM_DESK = 1.62
CEN_DESK = (252.0, 141.0)
def pull_cam(t, dot):
    """continuous pull-back: macro on the bobber -> the desk."""
    u = ease_io(clamp01((t - T_PULL0) / (T_PULL1 - T_PULL0)))
    z0, z1 = MACRO_Z, ZOOM_DESK
    z = math.exp(math.log(z0) + (math.log(z1) - math.log(z0)) * u)
    # macro centre: put the dot at output (864, 612) -> centre = dot - (864-960, 612-540)/(4 z0)
    c0 = (dot[0] - (864 - 960) / (4 * z0), dot[1] - (612 - 540) / (4 * z0))
    # blend the centre in "screen space" so the bobber stays put early and the room swings in late
    w = clamp01(((z0 / z) - 1) / ((z0 / z1) - 1))
    cx = c0[0] + (CEN_DESK[0] - c0[0]) * w; cy = c0[1] + (CEN_DESK[1] - c0[1]) * w
    if t < T_PULL0: z *= 1 + 0.010 * clamp01((t - T_DISS0) / (T_PULL0 - T_DISS0))
    if t > T_PULL1: z *= 1 + 0.018 * clamp01((t - T_PULL1) / (T_OKCUT - T_PULL1))   # slow drift-in on the desk
    return z, cx, cy

# ====================================================================== Claude
BLINKS = auto_blinks(T_ONLINE + 0.6, T_OKCUT, mean=2.6, seed=51) + auto_blinks(T_REPORT, T_MID_END, mean=3.0, seed=52)

def claude_state(t):
    """dict for claude.draw + extras (dy, squash, look, ant, tilt, hdy)"""
    q = PF.on_twos(t)
    d = dict(face='normal', arms='rest', phase=0, look=(0, 0), glow=1.0, led='online', led_k=1.0, dy=0.0, squash=0.0,
             ant=(0.0, 0.0), tilt=0.0, hdy=PF.breath_px(q, 3.6), status='online')
    if t < T_ONLINE:                                            # still "on leave": eyes closed, LED grey, slow breath
        d.update(face='calm', led='off', glow=0.75, status='off')
        d['hdy'] = PF.breath_px(q, 4.4, amp=1)
        return d
    if t < T_ONLINE + 0.12: d['face'] = 'half'
    elif t < T_ONLINE + 0.30: d['face'] = 'wide'
    d['led_k'] = clamp01((t - T_ONLINE) / 0.12)
    # stretch: anticipation (squash down) -> arms up + rise -> hold -> release
    if T_STRETCH0 - 0.25 <= t < T_STRETCH1 + 0.3:
        if t < T_STRETCH0:
            d['squash'] = 0.10 * ease_io(clamp01((t - T_STRETCH0 + 0.25) / 0.25)); d['face'] = 'closed'
        elif t < T_STRETCH1:
            u = (t - T_STRETCH0) / (T_STRETCH1 - T_STRETCH0)
            d.update(arms='stretch', face='closed' if u < 0.75 else 'happy')
            d['dy'] = 3.0 * math.sin(math.pi * min(1, u * 1.6)) if u < 0.62 else 3.0 * (1 - (u - 0.62) / 0.38) ** 2
            d['squash'] = -0.07 * math.sin(math.pi * min(1, u * 1.3))
            d['tilt'] = 4.0 * math.sin(2 * math.pi * u * 0.9)
        else:
            d['squash'] = squash_curve(t, T_STRETCH1, 0.14, 0.18); d['face'] = 'happy'
    sp = PF.wobble(t, T_STRETCH0 + 0.15, 2.6, freq=3.3, decay=2.4) + PF.wobble(t, T_STRETCH1, 3.0, freq=3.6, decay=2.6)
    d['ant'] = (sp, -abs(0.5 * sp))
    if T_LOOK_B <= t < T_0900:
        d['look'] = (3, 1) if t < T_LOOK_B + 0.06 else (2, 1)
        if t >= T_SMILE: d['face'] = 'happy'; d['dy'] = hop(t, T_SMILE, 1.5, 0.2)
    # 09:00 叮
    if T_0900 <= t < T_OKCUT + 0.1:
        d['face'] = 'wide' if t < T_0900 + 0.22 else 'normal'
        d['look'] = (2, 1) if t < T_FINGER1 else (-2, -1)
        d['dy'] = hop(t, T_0900, 2.0, 0.16)
        if T_FINGER0 - 0.08 <= t < T_FINGER1 + 0.1: d['arms'] = 'reach'
        d['ant'] = (d['ant'][0] + PF.wobble(t, T_0900, 2.2, freq=4.0, decay=3.0), d['ant'][1])
    # close: 好的！
    if T_OKCUT <= t < T_REPORT:
        d['look'] = (0, 0)
        if t >= T_OK - 0.03:
            d['face'] = 'happy'; d['dy'] = hop(t, T_OK - 0.03, 2.0, 0.18)
            d['ant'] = (PF.wobble(t, T_OK, 2.0, freq=3.6, decay=2.8), 0)
    if T_REPORT <= t < T_MID:
        d.update(arms='type', look=(-2, 1))
        typing = (T_STREAM0 <= t < STREAM_T[-1] + 0.6) or (T_PS1 <= t < PS1_T[-1] + 0.1) or (T_PS2 <= t < PS2_T[-1] + 0.1)
        d['phase'] = int(t * (14 if t < T_PS1 else 9)) if typing else 0
        if not typing: d['arms'] = 'rest'
        if T_STREAM0 <= t < STREAM_T[-1] + 0.6: d['face'] = 'focus'
        if T_PS1_LOOK <= t < T_DEL0:                           # stops. looks at the bobber.
            d.update(face='normal', look=(3, 0), arms='rest')
            d['tilt'] = PF.spring_follow(lambda x: 5.0 if x >= T_PS1_LOOK + 0.25 else 0.0, q, freq=2.2, zeta=0.55, window=1.0, dt=1 / 120)
        if T_DEL0 <= t < T_PS2:
            d.update(face='half' if t < T_DEL1 else 'normal', look=(-2, 1), arms='type', phase=int(t * 20))
        if T_PS2 <= t < T_SEND:
            d['face'] = 'happy' if t > PS2_T[-1] else 'normal'
        if t >= T_SEND - 0.05:
            d.update(face='happy', arms='rest'); d['dy'] = hop(t, T_SEND, 1.5, 0.2)
        if t >= T_TYPING + 0.15:                               # the reply: reads it (looks down-left at the toast)
            d.update(face='normal', look=(-3, -1))
            if T_REPLY1 + 0.1 <= t < T_REPLY2: d['face'] = 'half' if t < T_REPLY1 + 0.25 else 'normal'
            if t >= T_REACT:
                d['face'] = 'happy'; d['dy'] = hop(t, T_REACT, 2.0, 0.22); d['look'] = (-1, 1)
                d['ant'] = (PF.wobble(t, T_REACT, 2.4, freq=3.6, decay=2.6), 0)
                d['tilt'] = PF.spring_follow(lambda x: -5.0 if x >= T_REACT + 0.1 else 0.0, q, freq=2.0, zeta=0.55,
                                             window=1.0, dt=1 / 120)
    if t >= T_MID:
        d.update(face='normal', look=(3, 1), arms='rest')
        if t >= BOXES[0]['lines'][1]['t0'] + 0.3: d['face'] = 'happy'
        tgt = lambda x: (3.0 if x >= T_LOOK_CAL else 6.0) if x >= T_MID + 0.4 else 0.0
        d['tilt'] = PF.spring_follow(tgt, q, freq=1.8, zeta=0.6, window=1.4, dt=1 / 120)
        d['hdy'] = PF.breath_px(q, 4.0)
        if t >= T_LOOK_CAL:                                    # over to the calendar (the circled Saturday)
            d['look'] = (4, 0) if t < T_LOOK_CAL + 0.08 else (4, -1)
            d['face'] = 'normal' if t < T_LOOK_CAL + 0.55 else 'happy'
    if d['face'] in ('normal', 'focus', 'happy') and blink_at(t, BLINKS, 0.14) and d['face'] != 'happy': d['face'] = 'blink'
    return d

def bobber_wobble(t):
    """degrees (+ = clockwise) - the 09:00 jolt, damped by the finger."""
    a = PF.wobble(t, T_0900, 9.0, freq=3.2, decay=1.2)
    if t >= T_FINGER0: a *= math.exp(-(t - T_FINGER0) * 9.0)
    return a

def desk_jolt(t):
    """desk-object vertical jolt px at 09:00"""
    return -1 if T_0900 <= t < T_0900 + 0.07 else 0

boxes_cut_lint(BOXES, CUTS)

from credits_tl import *     # noqa  CREDITS v2 timing + Claude's performance (same single source of truth)
