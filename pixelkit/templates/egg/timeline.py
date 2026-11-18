"""《Claude 想请一天假》 EGG · 王工的请假条 (0-28.4 s) - single source of truth for picture AND sound.

  WIDE   0.0- 5.4  fade in on the Act II two-shot, Friday 22:47, lights off: Claude's lamp + monitor, Wang's laptop.
                   Wang stops typing, rubs it out (closed eyes), glances at the photo on his desk, turns:
                   「Claude，帮我写个请假条。」  Claude stops typing and looks over.
  C_CU   5.4- 8.1  Claude close: hop + 「好的！」 bubble (coin) -> 「请假事由是？」 (head tilt)
  W_CU   8.1-12.0  Wang close: he looks down at the photo ... 「……想看看周末长什么样。」 (= Claude's own reason, Act II)
  C_MED 12.0-16.2  Claude + the bobber on its wooden base: types, submits ->
                   「已提交。」 - a beat: it looks at the bobber - 「周末快乐。」 ^ ^  (v2: the river stays a surprise)
  INS   16.2-19.9  insert: the photo on Wang's desk (a boy and his young father on the pier, 1997), laptop-lit; a glint
                   crosses the glass; HUD badge 王工 ● 在线 -> 休假中 (status flip + music box); the photo warms up.
  RIVER 19.9-27.4  hard cut INTO the photo's framing, golden hour, Saturday 17:40: Wang sits where Claude sat, his
                   father on the stool.  「来啦。」「爸。」  slow pull back to the Act IV wide; the bucket is still empty.
                   fade to black on the last Act IV guitar chord.
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT)
from pixelkit.anim import (Track, ramp, hop, squash_curve, clamp01, ease_io, ease_out3, auto_blinks, blink_at,
                           boxes_prep, boxes_cut_lint)
from pixelkit import perform as PF
from pixelkit.anim import push_zoom, screen_follow

FPS = 30
T_C_CU, T_W_CU, T_C_MED, T_INS, T_RIVER = 5.75, 8.5, 12.65, 17.2, 21.2
D_IN = 0.7                 # INS -> RIVER: a short dissolve centred on T_RIVER (the push-in lands on the print first)
DUR = 29.4
CUTS = [T_C_CU, T_W_CU, T_C_MED, T_INS, T_RIVER]

# ====================================================================== WIDE
T_FADE_IN = 1.0
T_HUD_IN = 0.45
T_W_STOP = 1.15            # Wang stops typing
T_W_RUB0, T_W_RUB1 = 1.35, 1.75      # eyes shut, a long breath
T_W_PHOTO = 1.85           # glances at the photo (right, down)
T_W_TURN = 2.45            # turns to Claude
T_C_HEAR = 3.05            # Claude stops typing, looks over
# ====================================================================== C_CU
T_OK = 5.95                # 好的！ (hop + coin bubble)
# ====================================================================== W_CU
T_W_DOWN = 8.95            # looks down at the photo
T_W_UP = 11.55             # ... and back at Claude, a small smile
T_REACH0, T_REACH1 = 9.1, 9.55        # his hand goes to the frame (fingertips on its edge) ...
T_UNREACH0, T_UNREACH1 = 11.25, 11.6  # ... and back
T_RELAX = 11.8             # shoulders drop: decided
# ====================================================================== C_MED
T_TYPE0, T_SUBMIT = 12.8, 13.35
T_LOOK_BOB = 14.3          # the beat after 已提交。: it looks at the bobber ...
T_LOOK_BACK = 15.0         # ... and back at him, ^ ^ : 周末快乐。
# ====================================================================== INS
T_BADGE_IN = 17.55
T_FLIP = 18.45             # 在线 -> 休假中
T_GLINT0, T_GLINT1 = 17.45, 18.35
T_WARM0, T_WARM1 = 18.45, 20.95
T_PUSH0, T_PUSH1 = 19.3, T_RIVER - D_IN / 2   # the camera speeds up into the print until it fills the frame
Z_PRINT = 270 / 136 * 1.004                 # = PhotoFrameInsert(...).fill_cam()[0]: print height = frame height
T_BADGE_OUT = 20.5
# ====================================================================== RIVER
T_HUD2_IN, T_HUD2_OUT = 22.6, 27.3
T_OLD_TURN0, T_OLD_TURN1 = 22.85, 24.6     # the old man's head turns a little toward his son while he speaks
T_W_TURN0, T_W_TURN1 = 24.95, 26.7
T_AGE0, T_AGE1 = 21.75, 22.85   # match dissolve inside the photo: the boy -> Wang, the young father -> the old man
T_PULL0, T_PULL1 = 21.9, 27.6
FILM_HOLD, FILM_FADE = 0.8, 1.0    # the river opens still looking like the print (grain / colour / date), then it lets go
T_CHORD = 27.2             # the last Act IV guitar chord
T_FADE0 = 27.6
DUSK_MAX, T_DUSK0 = 0.32, 23.6      # P3: the sun keeps sinking (7 px) + the light turns violet through the pull-back
T_FLOCK = 25.4                      # P3: a near flock crosses the sun's glow
def dusk_k(t): return ease_io(ramp(t, T_DUSK0, DUR))

# ====================================================================== narration
def C_(t0, zh, en, face='normal', mouth='flat', cps=10.0): return dict(t0=t0, zh=zh, en=en, face=face, mouth=mouth, cps=cps, who='claude')
def W_(t0, zh, en, face='normal', cps=9.0, who='wang'): return dict(t0=t0, zh=zh, en=en, face=face, mouth='flat', cps=cps, who=who)
def O_(t0, zh, en, face='smile', cps=5.0): return dict(t0=t0, zh=zh, en=en, face=face, mouth='flat', cps=cps, who='old')
def nar(t_open, t_close, lines): return dict(t_open=t_open, t_close=t_close, lines=lines)

L_W1 = W_(2.45, 'Claude，帮我写个请假条。', 'Claude, could you write me a leave request?', face='tired', cps=11.0)
L_C1 = C_(6.65, '请假事由是？', 'Reason for leave?', face='q', mouth='flat', cps=10.0)
L_W2 = W_(9.3, '……想看看周末长什么样。', "...I'd like to see what a weekend looks like.", face='soft', cps=7.0)
L_C2 = C_(13.4, '已提交。周末快乐。', 'Submitted. Have a nice weekend.', face='happy', mouth='smile', cps=11.0)
L_C2['beats'] = {3: 1.05}            # 已提交。 | (looks at the bobber) | 周末快乐。
L_O1 = O_(23.12, '来啦。', 'There you are.', face='smile', cps=5.0)
L_W3 = W_(25.22, '爸。', 'Dad.', face='soft', cps=4.0, who='wang_dusk')
BOXES = [
    nar(2.33, 5.72, [L_W1]),
    nar(6.52, 8.4, [L_C1]),
    nar(9.15, 12.62, [L_W2]),
    nar(13.26, 17.15, [L_C2]),
    nar(22.98, 24.9, [L_O1]),
    nar(25.08, 26.9, [L_W3]),
]
boxes_prep(BOXES)
boxes_cut_lint(BOXES, CUTS)

# ====================================================================== cameras
ZOOM_WIDE = Track([(0.0, 1.30), (T_C_CU, 1.44, 'io')], log=True)
CENTER_WIDE = Track([(0.0, (308.0, 139.0)), (T_C_CU, (316.0, 140.0), 'io')])
def cam_c_cu(t):
    u = ease_io(ramp(t, T_C_CU, T_W_CU))
    return 3.15 * (1 + 0.035 * u), 254.0, 129.0 - 0.5 * u
def cam_w_cu(t):
    u = ease_io(ramp(t, T_W_CU, T_C_MED))
    return 3.55 * (1 + 0.05 * u), 374.0, 147.5 + 0.5 * u
def cam_c_med(t):
    u = ease_io(ramp(t, T_C_MED, T_INS))
    z = 2.55 * (1 + 0.06 * u)
    return z, 262.0 + 4 * u, 138.0 + 1.0 * u
def cam_ins(t):
    """slow drift in (1.0 -> 1.12), then from T_PUSH0 an accelerating push (anim.push_zoom) that lands at zero speed
    with the print filling the frame at T_PUSH1 (= PhotoFrameInsert.fill_cam()); the centre follows in screen space."""
    l1 = math.log(1.12)
    if t < T_PUSH0:
        u = ramp(t, T_INS, T_PUSH0); z = math.exp(l1 * (0.3 * u + 0.7 * u * u))
    else:
        z = push_zoom(t, T_PUSH0, T_PUSH1, 1.12, Z_PRINT, v0=l1 * 1.7 / (T_PUSH0 - T_INS))
    return z, 240.0, screen_follow(z, 1.0, Z_PRINT, 134.0, 128.0)

# RIVER: opens on the photo's framing (PHOTO_CAM), pulls back to the Act IV wide
PHOTO_CAM = (1.72, 247.0, 183.0)
RIVER_WIDE = (1.04, 241.0, 139.0)
def cam_river(t):
    u = ease_io(ramp(t, T_PULL0, T_PULL1))
    z0, x0, y0 = PHOTO_CAM; z1, x1, y1 = RIVER_WIDE
    z = math.exp(math.log(z0) + (math.log(z1) - math.log(z0)) * u)
    w = clamp01(((z0 / z) - 1) / ((z0 / z1) - 1))          # screen-space centre blend (no swing)
    z *= 1 + 0.012 * ramp(t, T_PULL1, DUR)
    return z, x0 + (x1 - x0) * w, y0 + (y1 - y0) * w

# ====================================================================== Claude (office: same desk as Act V)
HEAD = (250, 121)
PHOTO_EDGE = (398, 161)    # world px: the left edge of the photo frame on Wang's desk (his fingertips)
DESK_Y = 165
STAND_XY = (277, 162)
BOB_XY = (STAND_XY[0] + 1, STAND_XY[1] - 18)
CAL_XY = (291, 137)
MUG_XY = (323, 157)
BLINKS = auto_blinks(0.4, T_INS, mean=2.8, seed=61)
KICKS = [(T_C_HEAR, 2.2), (T_OK, 3.0), (T_SUBMIT, 1.6), (T_LOOK_BACK, 1.4)]

def claude_state(t):
    q = PF.on_twos(t)
    d = dict(face='focus', arms='type', phase=int(t * 11), look=(-2, 1), glow=1.0, led='online', led_k=1.0, dy=0.0,
             squash=0.0, ant=(0.0, 0.0), tilt=0.0, hdy=0)
    if t < T_C_HEAR:
        if 1.9 <= t < 2.25: d['phase'] = 0                          # a beat (reading what he wrote)
    elif t < T_C_CU:
        d.update(face='wide' if t < T_C_HEAR + 0.25 else 'normal', arms='rest', look=(3, 0))
        d['hdy'] = PF.breath_px(q, 3.6)
    elif t < T_W_CU:
        d.update(face='normal', arms='rest', look=(3, 0))
        if t >= T_OK - 0.04:
            d['face'] = 'happy'; d['dy'] = hop(t, T_OK - 0.04, 2.5, 0.2)
        if t >= L_C1['t0'] - 0.1:
            d['face'] = 'q'
        tg = lambda x: 6.0 if x >= L_C1['t0'] else 0.0
        d['tilt'] = PF.spring_follow(tg, q, freq=2.0, zeta=0.55, window=1.2, dt=1 / 120)
        d['hdy'] = PF.breath_px(q, 3.6) if d['dy'] == 0 else 0
    elif t < T_C_MED:                                               # (off screen) listening
        d.update(face='normal', arms='rest', look=(3, 0))
    else:
        d.update(face='focus', arms='type', look=(-2, 1)); d['phase'] = int(t * 15)
        if t >= T_SUBMIT: d.update(arms='rest', face='happy', look=(-1, 0)); d['dy'] = hop(t, T_SUBMIT, 1.5, 0.18)
        if t >= T_SUBMIT: d['spark_k'] = 1.0 + 1.4 * clamp01(1 - (t - T_SUBMIT) / 0.7)     # antenna lights up
        if t >= L_C2['t0'] + 0.5: d['face'] = 'normal'
        if t >= T_LOOK_BOB: d.update(look=(3, 2), face='normal')
        if t >= T_LOOK_BACK: d.update(look=(3, 0), face='happy')
        tg = lambda x: 5.0 if x >= T_LOOK_BACK + 0.05 else (2.0 if x >= T_LOOK_BOB else 0.0)
        d['tilt'] = PF.spring_follow(tg, q, freq=1.8, zeta=0.6, window=1.4, dt=1 / 120)
        if d['dy'] == 0: d['hdy'] = PF.breath_px(q, 4.0)
    sp = PF.wobbles(t, KICKS, freq=3.6, decay=2.6)
    d['ant'] = (sp, -abs(0.5 * sp))
    if d['face'] in ('normal', 'focus') and blink_at(t, BLINKS, 0.14): d['face'] = 'blink'
    return d

# ====================================================================== Wang Gong
WBLINKS = auto_blinks(0.6, T_INS, 2.6, seed=7)
def wang_state(t):
    s = dict(face='tired', arms='type', phase=int(t * 8), look=(0, 1), glint=1.0, tilt=0.0, hdy=0)
    q = PF.on_twos(t)
    if t < T_W_STOP: pass
    elif t < T_W_RUB0: s.update(arms='rest')
    elif t < T_W_RUB1: s.update(arms='rest', face='closed'); s['hdy'] = 1
    elif t < T_W_PHOTO: s.update(arms='rest', face='tired')
    elif t < T_W_TURN: s.update(arms='rest', face='normal', look=(2, 1))
    elif t < T_W_CU:
        s.update(arms='rest', face='tired', look=(-2, 0))
    elif t < T_C_MED:
        s.update(arms='rest', face='normal', look=(-2, 0))
        if t >= T_W_DOWN: s.update(face='soft', look=(2, 1))
        if t >= T_W_UP: s.update(face='smile', look=(-2, 0))
    else:
        s.update(arms='rest', face='smile', look=(-2, 0))
    tg = lambda x: (-3.0 if T_W_TURN + 0.1 <= x < T_W_CU else (3.0 if T_W_DOWN <= x < T_W_UP else (-3.0 if x >= T_W_UP else 0.0)))
    s['tilt'] = PF.spring_follow(tg, q, freq=1.5, zeta=0.6, window=1.2, dt=1 / 120)
    s['reach'] = ease_io(ramp(t, T_REACH0, T_REACH1)) * (1 - ease_io(ramp(t, T_UNREACH0, T_UNREACH1)))
    if T_W_CU <= t < T_C_MED and s['reach'] > 0.5: s['look'] = (2, 1)        # eyes on the photo under his hand
    if s['arms'] == 'rest' and not s['hdy']: s['hdy'] = PF.breath_px(q, 4.2, 0.3)
    if T_RELAX <= t < T_C_MED + 1.0 and not s['hdy']: s['hdy'] = 1 if (t - T_RELAX) < 0.5 else 0   # shoulders drop: decided
    if s['face'] in ('normal', 'tired', 'soft') and blink_at(t, WBLINKS): s['face'] = 'blink'
    return s

def _talk(t, ln):
    """mouth open on the typed characters of a line (not on punctuation)"""
    for tc, ch in zip(ln['times'], ln['zh']):
        if ch in '，。…？！、 ': continue
        if 0 <= t - tc < 0.075: return True
    return False

def wang_cu(t):
    """Wang's close-up (W_CU): face / look / nod / tilt / mouth / hand reach / shoulders."""
    q = PF.on_twos(t)
    s = dict(face='normal', look=(-2, 0), nod=0.0, mouth='flat', reach=0.0, sh=0.0, glint=1.0)
    if t >= T_W_DOWN: s.update(face='soft', look=(2, 2))
    if t >= T_W_UP: s.update(face='smile', look=(-2, 0), mouth='smile')
    s['nod'] = ease_io(ramp(q, T_W_DOWN, T_W_DOWN + 0.35)) * (1 - ease_io(ramp(q, T_W_UP - 0.1, T_W_UP + 0.25)))
    s['reach'] = ease_io(ramp(q, T_REACH0, T_REACH1)) * (1 - ease_io(ramp(q, T_UNREACH0, T_UNREACH1)))
    s['sh'] = ease_io(ramp(q, T_RELAX, T_RELAX + 0.5))
    tg = lambda x: (3.0 if T_W_DOWN <= x < T_W_UP else (-2.5 if x >= T_W_UP else -1.0))
    s['tilt'] = PF.spring_follow(tg, q, freq=1.4, zeta=0.65, window=1.2, dt=1 / 120)
    s['hdy'] = PF.breath_px(q, 4.2, 0.3)
    if _talk(t, L_W2) and s['face'] != 'smile': s['mouth'] = 'o'
    if s['face'] in ('normal', 'soft') and blink_at(t, WBLINKS): s['face'] = 'blink'
    return s

# ====================================================================== HUD
def hud_alpha(t):
    if t < T_INS: return ramp(t, T_HUD_IN, T_HUD_IN + 0.4)
    if t < T_RIVER: return 0.0
    return ramp(t, T_HUD2_IN, T_HUD2_IN + 0.5) * (1 - ramp(t, T_HUD2_OUT, T_HUD2_OUT + 0.6))
def hud_clock(t):
    return ('22:47', '周五', 'FRI') if t < T_RIVER else ('17:40', '周六', 'SAT')

def fade(t):
    if t < T_FADE_IN: return ease_io(t / T_FADE_IN)
    if t >= T_FADE0: return 1 - ease_io(ramp(t, T_FADE0, DUR - 0.05))
    return 1.0
