"""《Claude 想请一天假》 ACT IV v2 · 河边 (~118 s) - single source of truth for picture AND sound.
v2 script (approved): the opening asks to sit, the distance arc (apart -> closer), the bobber motive, the monologue
with looks (water <-> Claude), 2080 on Claude's face, a second 叮 he ignores, 嗯。, the bobber held up to the last light.

  W        0.0-  6.6  from behind: Claude walks up the pier; 叮 工作群 · 3 条新消息 - a glance, ignored; stops 2 planks behind.
  SO       6.6- 19.7  side two-shot: standing, …  C: 请问……这里可以坐吗？  (he does not turn)  O: 坐。 (a pat-pat gesture)
                      Claude hops onto the deck (a polite gap), can't sit still, eyes land on the bucket, leans: star eyes.
  BKT     19.7- 23.1  POV: the bucket, the scan -> 鱼获：0.
  SIDE2   23.1- 40.7  C: 一条都没钓到啊？  O: 嗯，从早上坐到现在。  C: 我可以帮您算出…(the card)  [CU_OR reaction: he holds back
                      a laugh]  …成功率能提高 83%。  O: 那多没意思。 flick -> crack -> shatter (camera shake, Claude flinches).
  CU_C1   40.7- 45.4  C: 可是……钓不到鱼，有什么意义呢？
  CU_O    45.4- 47.6  O (to Claude): 没意义啊。  (punch-in)
  CU_CR   47.6- 49.0  Claude's reaction.
  CU_OB   49.0- 55.0  O (to the water): 我上了四十年班，天天都在做有意义的事。
  INS     55.0- 56.9  the bobber.  O: 退休那天才发现，
  CU_C3   56.9- 61.2  Claude watching the bobber: …一个周末都没好好过过。  his face: 40×52 / =2080, holds, dims.
  INS2    61.2- 63.0  silence; the bobber sways.
  CU_O2   63.0- 68.6  he turns to Claude: 所以啊，没意义的事，才叫休息。
  CU_C2   68.6- 79.2  spinner -> cancel -> look -> sigh -> — —  叮 again: a glance, not opened -> ear -> 消息提醒 关.
  PAINT   79.2- 92.7  paint_v2 (music enters).
  INS_D   92.7- 95.2  dusk: the bobber twitches, lifts out.
  SIDE_H  95.2- 98.4  he reels in (crank), catches it: an empty hook; smiles; glances at the badge.
  BADGE   98.4- 99.6  insert: the badge.
  SIDE_H2 99.6-105.6  O: 拿着。 gives the bobber; Claude takes it, scoots closer.  O: 下周末，也一起陪我钓鱼吧，Claude。
  CU_H   105.6-111.0  (the invitation still on screen) Claude: — —  C: 嗯。  (^ ^, head-tilt nod, antenna boing)
  END    111.0-113.8  wide from behind at dusk, closer now; Claude raises the bobber.
  ECHO   113.8-117.9  the bobber held up beside the last sliver of sun (its painted sun dot next to the real one). fade.
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT)
from pixelkit.anim import ramp, clamp01, ease_io, ease_out3, auto_blinks, blink_at, boxes_prep, boxes_cut_lint, type_times, hop, squash_curve
from pixelkit import perform as PF
from pixelkit.sets import river_pier as RP

FPS = 30
T_SO, T_BKT, T_SIDE2, T_CU_C1, T_CU_O, T_CU_CR, T_CU_OB = 6.6, 19.7, 23.1, 40.7, 45.4, 47.6, 49.0
T_INS, T_CU_C3, T_INS2, T_CU_O2, T_CU_C2, T_PAINT = 55.0, 56.9, 61.2, 63.0, 68.6, 79.2
T_INS_D, T_SIDE_H, T_BADGE, T_SIDE_H2, T_CU_H, T_END, T_ECHO = 92.7, 95.2, 98.4, 99.6, 105.6, 111.0, 113.8
D_INS_D_DISS, D_END_DISS = 0.8, 1.0
T_FADE0 = 116.3
DUR = 117.9
PAINT_T0 = 1.5                          # paint_v2 local time at T_PAINT
def paint_local(t): return t - T_PAINT + PAINT_T0

# ====================================================================== narration (claude_box; who='old' = the old man)
def C_(t0, zh, en, face='normal', mouth='flat', cps=11.0): return dict(t0=t0, zh=zh, en=en, face=face, mouth=mouth, cps=cps, who='claude')
def O_(t0, zh, en, face='normal', cps=7.0): return dict(t0=t0, zh=zh, en=en, face=face, mouth='flat', cps=cps, who='old')
def nar(t_open, t_close, lines): return dict(t_open=t_open, t_close=t_close, lines=lines)

L_ASK = C_(7.65, '请问……这里可以坐吗？', 'Excuse me... may I sit here?', face='q', cps=9.0)
L_SIT = O_(10.75, '坐。', 'Sit.', cps=5.0)
L_NONE = C_(23.35, '一条都没钓到啊？', 'Not a single one?', face='q', cps=9.0)
L_MORNING = O_(25.7, '嗯，从早上坐到现在。', 'Mm. Been sitting here since this morning.', cps=7.0)
L_CALC = C_(29.3, '我可以帮您算出最佳下钩位置、鱼群密度、风向和水温，',
            'I can work out the best spot, fish density, wind and water temperature for you,', mouth='smile', cps=12.0)
L_83 = C_(34.0, '成功率能提高 83%。', 'and raise your success rate by 83%.', face='wide', mouth='smile', cps=11.0)
L_BORING = O_(37.4, '那多没意思。', "Where's the fun in that?", face='smile', cps=6.0)
L_WHY = C_(41.1, '可是……钓不到鱼，有什么意义呢？', "But... if you don't catch any fish, what's the point?", face='q', mouth='flat', cps=10.0)
L_NO_POINT = O_(45.85, '没意义啊。', "There isn't one.", face='smile', cps=6.0)
L_40Y = O_(49.3, '我上了四十年班，天天都在做有意义的事。', 'I worked for forty years. Every day, something meaningful.', cps=8.0)
L_RETIRE = O_(55.25, '退休那天才发现，一个周末都没好好过过。', "The day I retired, I realised I'd never really had a weekend.", face='down', cps=7.5)
L_REST = O_(64.0, '所以啊，没意义的事，才叫休息。', "So... the pointless things - that's what rest is.", face='soft', cps=7.0)
L_TAKE = O_(99.85, '拿着。', 'Here.', face='smile', cps=5.0)
L_NEXT = O_(102.55, '下周末，也一起陪我钓鱼吧，Claude。', 'Come fishing with me again next weekend, Claude.', face='smile', cps=8.0)
L_YES = C_(108.4, '嗯。', 'Mm.', face='happy', mouth='smile', cps=5.0)
BOXES = [
    nar(7.5, 10.45, [L_ASK]),
    nar(10.6, 12.35, [L_SIT]),
    nar(23.27, 25.4, [L_NONE]),
    nar(25.55, 29.0, [L_MORNING]),
    nar(29.15, 36.75, [L_CALC, L_83]),
    nar(37.25, 40.45, [L_BORING]),
    nar(40.95, 45.2, [L_WHY]),
    nar(45.7, 47.9, [L_NO_POINT]),
    nar(49.2, 61.0, [L_40Y, L_RETIRE]),
    nar(63.85, 68.4, [L_REST]),
    nar(99.77, 107.65, [L_TAKE, L_NEXT]),
    nar(108.25, 110.2, [L_YES]),
]
boxes_prep(BOXES)
CUTS = [T_SO, T_BKT, T_SIDE2, T_CU_C1, T_CU_O, T_CU_CR, T_CU_OB, T_INS, T_CU_C3, T_INS2, T_CU_O2, T_CU_C2, T_PAINT,
        T_INS_D, T_SIDE_H, T_BADGE, T_SIDE_H2, T_CU_H, T_END, T_ECHO]       # (+ CU_OR in/out, added below)
OLD_LINES = [L_SIT, L_MORNING, L_BORING, L_NO_POINT, L_40Y, L_RETIRE, L_REST, L_TAKE, L_NEXT]

def char_time(line, sub):
    """time the first character of `sub` is typed in `line`."""
    i = line['zh'].index(sub)
    return line['times'][i]

# ====================================================================== HUD clock + the two work pings
T_HUD_IN = 0.3
T_NOTE1 = 2.6                            # W: 叮 工作群 · 3 条新消息 (he glances, keeps walking)
T_NOTE1_OUT = 4.9
T_NOTE2 = 75.4                           # CU_C2: 叮 工作群 · 新消息 again (a glance, not opened)
T_EAR0, T_EAR1 = 76.6, 78.1
T_TOG_IN, T_TOG_OUT = 76.85, 78.15
T_CLICK = 77.4                           # 消息提醒 -> 关 ; the clock freezes, flashes once, fades; the ping goes away
T_CLOCK_STOP = T_CLICK
T_HUD_OUT0, T_HUD_OUT1 = 77.75, 78.55
CLOCK_TICKS = [(0.0, '17:40'), (T_SIDE2, '17:41'), (T_CU_O, '17:42'), (T_CU_O2, '17:43'), (T_CU_C2 + 3.0, '17:44')]
def clock(t):
    s = CLOCK_TICKS[0][1]; t_tick = -9
    for (tt, v) in CLOCK_TICKS:
        if t >= tt: s, t_tick = v, tt
    return s, t_tick
def hud_alpha(t): return ramp(t, T_HUD_IN, T_HUD_IN + 0.5) * (1 - ramp(t, T_HUD_OUT0, T_HUD_OUT1))
def note_k(t):
    """-> (drop-in k, alpha, which) of the 工作群 chip under the clock."""
    if T_NOTE1 <= t < T_NOTE1_OUT + 0.3:
        return ease_out3(ramp(t, T_NOTE1, T_NOTE1 + 0.25)), 1 - ramp(t, T_NOTE1_OUT, T_NOTE1_OUT + 0.3), 1
    if T_NOTE2 <= t < T_CLICK + 0.35:
        return ease_out3(ramp(t, T_NOTE2, T_NOTE2 + 0.25)), 1 - ramp(t, T_CLICK + 0.05, T_CLICK + 0.35), 2
    return 0.0, 0.0, 0

# ====================================================================== W: Claude walks up the pier, stops behind
CL_X, CL_SEAT = 220, RP.CLAUDE_SEAT[1]          # back view: where he sits in the dusk END (+ CL_X_END: closer)
CL_X_END = 223
T_ENTER, T_ARRIVE = 1.0, 5.0
S_START, S_STOP = 2.6, 1.45                       # perspective scale at the start / where he stops (behind the old man)
WALK_FPS = 6.0
X_SEAT = CL_X - RP.VP[0]
def walk_u(t):
    return 0.25 * ease_io(ramp(t, T_ENTER, T_ARRIVE)) + 0.75 * ramp(t, T_ENTER, T_ARRIVE)
def walk_s(t):
    w0, w1 = 1.0 / S_START, 1.0 / S_STOP
    return 1.0 / (w0 + (w1 - w0) * walk_u(t))
def walk_pos(t):
    s = walk_s(t)
    u = walk_u(t)
    X = X_SEAT + 4 - 150.0 * (1 - ease_out3(min(1.0, u / 0.30)))
    y = RP.VP[1] + (CL_SEAT - RP.VP[1]) * s
    x = RP.VP[0] + X * s
    return x, y, s
def walk_phase(t):
    if t < T_ENTER or t >= T_ARRIVE: return 0
    return int((t - T_ENTER) * WALK_FPS) % 4
def footsteps():
    out = []; n = 0
    while T_ENTER + n / WALK_FPS < T_ARRIVE:
        if n % 2 == 0: out.append((T_ENTER + n / WALK_FPS, walk_pos(T_ENTER + n / WALK_FPS)[2]))
        n += 1
    return out
T_GLANCE1 = (2.8, 3.45)                           # the head turns a little toward the ping ... and back
def w_head_dx(t):
    q = PF.on_twos(t)
    a, b = T_GLANCE1
    return -2.0 * ease_io(ramp(q, a, a + 0.15)) * (1 - ease_io(ramp(q, b, b + 0.2)))
def cam_w(t):
    return 1.0, 240.0, 135.0

# ====================================================================== SO: may I sit here?
T_PAT0 = L_SIT['t0'] - 0.25                       # the near hand comes out ... pat, pat ... back on the rod
T_PAT1 = T_PAT0 + 1.15
T_HOP = L_SIT['t_end'] + 0.05                     # sample_perf s = 0 here (approved choreography)
DX_STAND = -9                                     # standing spot (relative to the sitting spot SX_C)
T_ANT, T_TAKE, T_LAND = 0.32, 0.46, 0.66          # (sample-relative) anticipation squash, take-off, landing
BUCKET_X = 317
S_LOOK = [(0.0, (3, 0)), (1.05, (0, 0)), (2.15, (-3, 0)), (2.75, (3, -1)), (3.3, (0, 0)), (4.5, (0, -2)), (5.0, (-3, 1)),
          (5.55, (3, 2))]
S_BLINKS = [0.9, 3.05, 4.95, 7.3]
PRE_LOOK = [(T_SO, (2, 2)), (T_SO + 0.85, (3, 2)), (7.45, (3, 0)), (L_ASK['t_end'] + 0.55, (2, 2)), (L_ASK['t_end'] + 1.05, (3, 0))]
PRE_BLINKS = [T_SO + 0.45, L_ASK['t_end'] + 0.3]
ARMS_SO = PF.PoseTrack([(0.0, 'down'), (7.25, 'clasp', 0.3, 'back'), (T_HOP + T_ANT, 'shrug', 0.16, 'back'),
                        (T_HOP + T_LAND, 'down', 0.12), (T_HOP + T_LAND + 0.2, 'knees', 0.3, 'back')])

def so_tilt_target(t):
    s = t - T_HOP
    if t < T_HOP + T_TAKE:
        if t < 7.4: return 0.0
        k = ease_io(ramp(t, 7.4, 7.8))
        return -4.0 * k + (2.0 * ease_io(ramp(t, L_SIT['t0'], L_SIT['t0'] + 0.2)) if t >= L_SIT['t0'] else 0.0)
    if s < 2.2: return 0.0
    lx, ly = PF.glance(s - 0.12, S_LOOK)
    return {(-3, 0): -3.0, (3, -1): 3.0, (0, -2): 0.0, (-3, 1): -2.0, (3, 2): 6.0}.get((lx, ly), 0.0)

def so_dx(t):
    return DX_STAND - DX_STAND * ease_io(ramp(t, T_HOP + T_TAKE, T_HOP + T_LAND))

def so_head_pos(t):
    s = t - T_HOP
    x = so_dx(t)
    y = hop(s, T_TAKE, 4.0, T_LAND - T_TAKE)
    if s >= T_LAND: y += 2.0 * squash_curve(s, T_LAND, 1.0, 0.12)
    if s >= 6.25: x += 3 * ease_io(ramp(s, 6.25, 6.7))
    if t < T_HOP: y += 1.0 * ease_io(ramp(t, 7.4, 7.8))
    return (x + 0.5 * so_tilt_target(t), y)

def claude_so(t):
    q = PF.on_twos(t); s = q - T_HOP
    d = {}
    sit = s >= T_LAND
    d['pose'] = 'sit' if sit else 'stand'
    d['dx'] = so_dx(q)
    if not sit:
        d['y'] = hop(s, T_TAKE, 4.0, T_LAND - T_TAKE)
        if s >= 0:
            d['squash'] = 0.10 * math.sin(math.pi * ramp(s, T_ANT, T_TAKE)) if s < T_TAKE else -0.06 * math.sin(math.pi * ramp(s, T_TAKE, T_LAND))
    else:
        d['squash'] = squash_curve(s, T_LAND, 0.12, 0.12)
        d['kick'] = 3 if s < T_LAND + 0.09 else 0
    d['arms'] = ARMS_SO(q)
    if 2.0 <= s < 3.7:
        d['phase'] = int((s - 2.0) * 8)
        d['kick'] = (1, 0, 2, 0)[int((s - 2.0) * 6) % 4]
    face = 'normal'
    if q < T_HOP:
        if T_SO + 0.35 <= q < 7.4: face = 'ellipsis'
        if L_SIT['t0'] + 0.2 <= q: face = 'happy'
        face = PF.blink_face(q, PRE_BLINKS, face) if face == 'normal' else face
        look = PF.glance(q, PRE_LOOK)
    else:
        if s < T_ANT: face = 'happy'
        elif T_ANT <= s < T_LAND + 0.08: face = 'squint'
        elif T_LAND + 0.08 <= s < 1.4: face = 'happy'
        elif 3.7 <= s < 3.82: face = 'dots1'
        elif 3.82 <= s < 4.2: face = 'dots'
        elif 4.2 <= s < 4.3: face = 'dots1'
        elif 6.05 <= s < 6.75: face = 'sparkle'
        elif s >= 6.75: face = 'star'
        face = PF.blink_face(s, S_BLINKS, face) if face == 'normal' else face
        look = PF.glance(s, S_LOOK) if face not in ('dots', 'dots1') else (0, 0)
        if s < T_TAKE: look = (3, 1)
    d['face'] = face; d['look'] = look
    d['tilt'] = PF.spring_follow(so_tilt_target, q, freq=2.6, zeta=0.55, window=1.0, dt=1 / 120)
    d['hdy'] = PF.breath_px(q, 3.4) if (T_HOP + 1.2 <= q < T_HOP + 6.0 or q < 7.4) else (1 if T_ASK_DOWN(q) else 0)
    if s >= 6.25: d['lean'] = 3 * ease_io(ramp(s, 6.25, 6.7))
    lx, ly = PF.lag(so_head_pos, t, freq=3.2, zeta=0.22, window=1.6, dt=1 / 120)
    lx += PF.wobbles(t, [(T_HOP + T_LAND, 2.5), (T_HOP + 6.05, 2.2), (L_SIT['t0'] + 0.2, 1.6)], freq=3.6, decay=3.0)
    d['ant'] = (lx * 1.4, ly * 0.6)
    d['spark'] = 1.0 + (0.8 * math.exp(-(t - T_HOP - 6.05) * 2.5) if s >= 6.05 else 0.0)
    return d
def T_ASK_DOWN(q): return 7.6 <= q < T_HOP          # head bowed while asking / waiting

SO_TURN = [(0.0, 1.0), (T_HOP + 6.75, 1.0), (T_HOP + 7.05, -1.0), (T_HOP + 7.75, -1.0), (T_HOP + 8.05, 1.0)]
def pat_ang(t):
    """the near (side 0) arm: out to the free spot beside him, two pats, back to the rod.  None = on the rod."""
    q = PF.on_twos(t)
    if not (T_PAT0 <= q < T_PAT1): return None
    rest, out = (-2.0, 110.0), (-48.0, -18.0)
    u_in = PF.back_soft(ramp(q, T_PAT0, T_PAT0 + 0.3))
    u_out = ease_io(ramp(q, T_PAT1 - 0.3, T_PAT1))
    k = u_in * (1 - u_out)
    ua = rest[0] + (out[0] - rest[0]) * k
    fa = rest[1] + (out[1] - rest[1]) * k
    for tp in (T_PAT0 + 0.38, T_PAT0 + 0.62):             # pat: the forearm dips, the hand slaps down
        if tp <= q < tp + 0.14: fa += 16.0; ua -= 4.0
    return {0: (ua, fa)}
def old_so(t):
    q = PF.on_twos(t)
    face = 'blink' if any(0 <= q - b < 0.13 for b in (8.4, 12.9, 15.6, T_HOP + 6.3)) else None
    v = PF.turn_track(q, SO_TURN)
    if T_HOP + 7.05 <= q < T_HOP + 7.75: face = 'soft'
    od = dict(arms='hold', v=v, breath='v2', body='water')
    if face: od['face'] = face
    pa = pat_ang(t)
    if pa: od['arm_ang'] = pa; od['lean'] = -3.0 * min(1.0, ramp(PF.on_twos(t), T_PAT0, T_PAT0 + 0.3)) * (1 - ramp(PF.on_twos(t), T_PAT1 - 0.3, T_PAT1))
    return od

# ====================================================================== BKT: the bucket POV + scan
T_SCAN0, T_SCAN1 = T_BKT + 0.55, T_BKT + 1.75
T_RESULT = T_BKT + 1.9
def scan_u(t): return ramp(t, T_SCAN0, T_SCAN1)

# ====================================================================== SIDE2: the optimizer card + gestures
T_CARD_IN = L_CALC['t0'] + 0.15
CARD_ROWS = [char_time(L_CALC, k) + 0.05 for k in ('最佳', '鱼群', '风向', '水温')]
T_RATE = char_time(L_83, '83') + 0.05
T_CU_OR0 = CARD_ROWS[1] - 0.15                   # reaction cut: the old man holding back a laugh
T_CU_OR1 = CARD_ROWS[3] + 0.75
CUTS += [T_CU_OR0, T_CU_OR1]; boxes_cut_lint(BOXES, CUTS)
T_GLANCE = T_RATE + 0.35                         # he finally looks at the card
T_FLICK0 = L_BORING['t_end'] + 0.15
T_FLICK1 = T_FLICK0 + 0.6
T_CRACK = T_FLICK0 + 0.22                        # (after the 0.1 s anticipation)
T_SHATTER = T_CRACK + 0.22
CARD_X, CARD_Y = 8, 34
CARD_FLOOR = 184
def card_rows(t): return [ease_out3(ramp(t, r, r + 0.35)) for r in CARD_ROWS]
def card_in(t): return ease_out3(ramp(t, T_CARD_IN, T_CARD_IN + 0.3))
def shake_side2(t):
    """2-3 frame camera hit on the shatter (world px)."""
    f = int(round((t - T_SHATTER) * FPS))
    return {0: (1.0, -0.6), 1: (-0.8, 0.5), 2: (0.5, 0.0)}.get(f, (0.0, 0.0))

BLINKS_C = auto_blinks(T_SIDE2, T_CU_C1, mean=3.1, seed=7)
ARMS_S2 = PF.PoseTrack([(0.0, 'knees'), (char_time(L_CALC, '最佳') - 0.3, 'present', 0.22, 'back'),
                        (T_RATE - 0.35, 'lift', 0.18, 'back'), (T_RATE + 1.4, 'knees', 0.35),
                        (T_CRACK, 'shrug', 0.1), (T_SHATTER + 0.7, 'knees', 0.4)])
def s2_lean(t):
    return 2.0 * ease_io(ramp(t, T_CARD_IN, T_CARD_IN + 0.4)) * (1 - ease_io(ramp(t, T_RATE + 1.2, T_RATE + 1.7)))
def s2_recoil(t):
    return -2.0 * PF.back_soft(ramp(t, T_CRACK, T_CRACK + 0.12)) * (1 - ease_io(ramp(t, T_SHATTER + 0.9, T_SHATTER + 1.5)))
def s2_head(t):
    return (s2_lean(t) + s2_recoil(t), 0.0)
def claude_side2(t):
    q = PF.on_twos(t)
    face, look = 'normal', (2, 0)
    if q < T_SIDE2 + 0.6: look = (1, 2)                                     # still looking at the bucket
    tilt = 0.0
    if L_NONE['t0'] - 0.1 <= q < L_MORNING['t0']: face = 'q'; tilt = 4.0
    arms = ARMS_S2(q)
    if arms[1] == 'present' and arms[2] == 0.0 or (arms[0] == 'present' and arms[1] == 'present'):
        n = sum(1 for r in CARD_ROWS if q >= r) - 1                         # the hand follows the rows down
        if n >= 1: arms = ('present', 'point', min(1.0, n / 3.0))
    if CARD_ROWS[0] - 0.1 <= q < T_RATE - 0.35: face = 'sparkle'
    if T_RATE - 0.35 <= q < T_RATE + 1.6: face = 'star'
    if T_FLICK0 - 0.6 <= q < T_CRACK: face = 'normal'
    if q >= T_CRACK: face = 'wide2' if q < T_SHATTER + 0.5 else ('droop' if q < T_SHATTER + 1.9 else 'normal')
    if face == 'normal': face = PF.blink_face(q, BLINKS_C)
    talk = any(ln['t0'] <= q < ln['t_end'] for ln in (L_NONE, L_CALC, L_83))
    d = dict(face=face, arms=arms, look=look, bob=(1 if talk and int(q * 4) % 3 == 0 else 0), pose='sit')
    d['lean'] = s2_lean(q) + s2_recoil(q)
    d['tilt'] = PF.spring_follow(lambda x: (4.0 if L_NONE['t0'] - 0.1 <= x < L_MORNING['t0'] else 0.0) - 3.0 * (T_CRACK <= x < T_SHATTER + 1.2),
                                 q, freq=2.4, zeta=0.6, window=1.0, dt=1 / 120)
    d['hdy'] = PF.breath_px(q, 3.5) + (1 if T_SHATTER + 0.5 <= q < T_SHATTER + 1.9 else 0)
    d['squash'] = squash_curve(q, T_CRACK, -0.08, 0.1) + squash_curve(q, T_RATE - 0.3, 0.07, 0.12)
    lx, ly = PF.lag(s2_head, t, freq=3.2, zeta=0.22, window=1.4, dt=1 / 120)
    lx += PF.wobbles(t, [(T_RATE - 0.3, 2.0), (T_CRACK, 2.6)], freq=3.6, decay=3.0)
    droop = 2.0 * (T_SHATTER + 0.3 <= q < T_SHATTER + 1.9)
    d['ant'] = (lx * 1.4 - 0.8 * droop, ly * 0.6 + droop)
    d['spark'] = 1.0 + (0.8 * math.exp(-(t - T_RATE + 0.3) * 2.5) if t >= T_RATE - 0.3 else 0.0)
    return d
S2_TURN = [(0.0, 1.0), (L_MORNING['t0'] - 0.3, 1.0), (L_MORNING['t0'] + 0.05, -1.0), (L_MORNING['t0'] + 1.0, -1.0),
           (L_MORNING['t0'] + 1.35, 1.0), (T_GLANCE, 1.0), (T_GLANCE + 0.3, -1.0), (T_SHATTER + 0.9, -1.0), (T_SHATTER + 1.3, 1.0)]
def flick_ang(t):
    """side-0 (near) hand: up to the chest (anticipation) -> a back-hand flick out toward the card -> back."""
    q = PF.on_twos(t)
    if not (T_FLICK0 <= q < T_FLICK1): return None
    rest, pre, out = (-2.0, 110.0), (14.0, 165.0), (-58.0, -128.0)
    u = (q - T_FLICK0)
    if u < 0.12: k_pre, k_out = ease_io(u / 0.12), 0.0
    elif u < 0.24: k_pre, k_out = 1.0, PF.back_soft((u - 0.12) / 0.12)
    else: k_pre, k_out = 1.0, 1.0
    back = ease_io(ramp(q, T_FLICK1 - 0.28, T_FLICK1))
    ua = rest[0] + (pre[0] - rest[0]) * k_pre + (out[0] - pre[0]) * k_out
    fa = rest[1] + (pre[1] - rest[1]) * k_pre + (out[1] - pre[1]) * k_out
    ua = ua + (rest[0] - ua) * back; fa = fa + (rest[1] - fa) * back
    return {0: (ua, fa)}
def laugh_shake(t, bursts):
    """1 px shoulder shake on 2s during (t0, t1) bursts (chuckle / holding back a laugh)."""
    q = PF.on_twos(t)
    for (a, b) in bursts:
        if a <= q < b: return (1, 0, -1, 0)[int((q - a) * 15) % 4]
    return 0
def old_side2(t):
    q = PF.on_twos(t)
    od = dict(arms='hold', v=PF.turn_track(q, S2_TURN), breath='v2', body='water')
    sh = laugh_shake(t, [(T_RATE + 0.1, T_RATE + 0.7), (L_BORING['t_end'] - 0.1, L_BORING['t_end'] + 0.2)])
    if sh: od['shake'] = sh
    fa = flick_ang(t)
    if fa: od['arm_ang'] = fa
    if T_GLANCE <= q < L_BORING['t0']: od['face'] = 'smile'
    return od
def old_or(t):
    """CU_OR: eyes on the water, lips pressed, the shoulders going."""
    q = PF.on_twos(t)
    od = dict(arms='hold', v=1.0, breath='v2', body='water', face='soft')
    sh = laugh_shake(t, [(T_CU_OR0 + 0.35, T_CU_OR0 + 0.75), (T_CU_OR0 + 1.0, T_CU_OR1)])
    if sh: od['shake'] = sh
    if T_CU_OR0 + 0.55 <= q < T_CU_OR0 + 0.68: od['face'] = 'blink'
    return od

# ====================================================================== CU_C1 / CU_CR / CU_C3 / CU_C2
BLINKS_C1 = [41.9, 44.5]
def claude_c1(t):
    q = PF.on_twos(t)
    face = 'normal'
    if q >= char_time(L_WHY, '有什么') - 0.05: face = 'q'
    if face == 'normal': face = PF.blink_face(q, BLINKS_C1)
    look = (1, 0) if q < 41.5 else (2, 0)
    tgt = lambda x: 4.0 if x >= char_time(L_WHY, '有什么') - 0.05 else (-2.0 if x >= char_time(L_WHY, '钓不到') else 0.0)
    d = dict(face=face, arms='knees', look=look, glow=1.0, pose='sit', hdy=PF.breath_px(q, 3.5))
    d['tilt'] = PF.spring_follow(tgt, q, freq=2.4, zeta=0.55, window=1.0, dt=1 / 120)
    lx, ly = PF.lag(lambda x: (0.5 * tgt(x), 0.0), t, freq=3.2, zeta=0.22, window=1.2, dt=1 / 120)
    d['ant'] = (lx * 1.6, ly)
    return d
def claude_cr(t):
    """没意义啊。 -> a beat: eyes widen a notch, the antenna gives a tiny boing, a slow blink, the head drops a little."""
    q = PF.on_twos(t)
    face = 'wide' if q < T_CU_CR + 0.55 else 'normal'
    if face == 'normal': face = PF.blink_face(q, [T_CU_CR + 0.75])
    d = dict(face=face, arms='knees', look=(2, 0), pose='sit', hdy=(1 if q >= T_CU_CR + 0.9 else 0))
    d['ant'] = (PF.wobble(t, T_CU_CR + 0.05, 1.6, freq=3.4, decay=3.0), 0.0)
    d['tilt'] = PF.spring_follow(lambda x: -2.0 if x >= T_CU_CR + 0.9 else 0.0, q, freq=2.2, zeta=0.6, window=1.0, dt=1 / 120)
    return d
T_CALC_FACE = char_time(L_RETIRE, '一个') - 0.05          # 40×52 / =2080 on his face
T_CALC_2 = T_CALC_FACE + 0.45
T_CALC_DIM0 = L_RETIRE['t_end'] + 1.0
T_CALC_DIM1 = T_CALC_DIM0 + 0.6
def bob_sway(t): return 0.6 * math.sin(2 * math.pi * t / 2.3)
def claude_c3(t):
    q = PF.on_twos(t)
    lx = 2 + int(round(bob_sway(t) * 0.8))
    d = dict(arms='knees', look=(lx, 2), pose='sit', hdy=PF.breath_px(q, 3.6), glow=1.0)
    face = PF.blink_face(q, [T_CU_C3 + 0.6])
    if q >= T_CALC_FACE:
        face = 'txt:40×52' if q < T_CALC_2 else 'txt:40×52/=2080'
        d['glow'] = 1.0 - 0.6 * ease_io(ramp(q, T_CALC_DIM0, T_CALC_DIM1))
        if q >= T_CALC_DIM1 + 0.25: face, d['glow'] = PF.blink_face(q, [T_CALC_DIM1 + 0.25], 'droop'), 1.0
        if q >= T_CALC_DIM1 + 0.25: d['look'] = (1, 2)
    d['face'] = face
    d['tilt'] = PF.spring_follow(lambda x: 2.0 if x < T_CALC_FACE else -2.0, q, freq=2.0, zeta=0.7, window=1.0, dt=1 / 120)
    d['ant'] = (PF.wobble(t, T_CALC_2, 1.2, freq=3.4, decay=3.0), 1.0 if q >= T_CALC_DIM1 else 0.0)
    return d

T_LOAD0, T_CANCEL = T_CU_C2 + 0.35, T_CU_C2 + 3.0
T_BLINK2 = T_CANCEL + 0.55
T_LOOK_OLD, T_LOOK_WATER = T_CANCEL + 0.95, T_CANCEL + 1.95
T_SIGH = T_CANCEL + 2.75
T_CALM = T_SIGH + 0.2
T_NOTE2_LOOK, T_NOTE2_BACK = T_NOTE2 + 0.2, T_NOTE2 + 0.85
def load_phase(t):
    return 11.0 * (min(t, T_CANCEL) - T_LOAD0)
def load_ticks():
    out = []; n_prev = 0; t = T_LOAD0
    while t < T_CANCEL:
        n = int(load_phase(t))
        if n != n_prev: out.append((t, n)); n_prev = n
        t += 1.0 / 600
    return out
def sigh_k(t): return ease_io(ramp(t, T_SIGH, T_SIGH + 0.45))
def claude_c2(t):
    q = PF.on_twos(t)
    look = (1, 0)
    if q < T_LOAD0: face = 'normal'
    elif q < T_CANCEL: face = 'load%d' % (int(load_phase(t)) % 8)
    elif q < T_CANCEL + 0.35: face = 'load%d' % (int(load_phase(T_CANCEL)) % 8) if int((q - T_CANCEL) * 20) % 2 == 0 else 'normal'
    else: face = 'normal'
    if q >= T_LOOK_OLD: look = (2, 0)
    if q >= T_LOOK_WATER: look = (1, 2)
    if face == 'normal': face = PF.blink_face(q, [T_BLINK2, T_LOOK_OLD + 0.6])
    if q >= T_CALM: face = 'calm'
    if T_NOTE2 + 0.08 <= q < T_NOTE2_BACK + 0.25:                  # 叮: the eyes open, flick up to the ping ...
        face = 'half' if q < T_NOTE2 + 0.16 else 'normal'
        look = (-2, -2) if q >= T_NOTE2_LOOK else (0, 0)
        if q >= T_NOTE2_BACK: look = (1, 2)                         # ... and back to the water (not opened)
    if q >= T_NOTE2_BACK + 0.25: face = 'normal' if q < T_EAR0 else 'calm'
    if q >= T_NOTE2_BACK + 0.25: look = (1, 2)
    arms = 'ear' if T_EAR0 <= q < T_EAR1 else 'knees'
    if T_EAR0 - 0.15 <= q < T_EAR0: arms = ('knees', 'ear', 0.5)
    if T_EAR1 <= q < T_EAR1 + 0.2: arms = ('ear', 'knees', 0.6)
    glow = 1.0 - 0.45 * ease_io(ramp(t, T_CLICK, T_CLICK + 0.4))
    sk = sigh_k(q) * (1 - 0.5 * ease_io(ramp(q, T_SIGH + 1.4, T_SIGH + 2.2)))
    d = dict(face=face, arms=arms, look=look, glow=glow, pose='sit', drop=int(round(1.6 * sk)))
    d['hdy'] = PF.breath_px(q, 3.8) if q < T_SIGH else 0
    d['tilt'] = PF.spring_follow(lambda x: (-3.0 if x >= T_SIGH else 0.0) + (2.0 if T_NOTE2_LOOK <= x < T_NOTE2_BACK else 0.0),
                                 q, freq=2.0, zeta=0.65, window=1.0, dt=1 / 120)
    droop = 2.0 * sk
    d['ant'] = (-0.8 * droop + PF.wobbles(t, [(T_NOTE2, 1.8), (T_CLICK, 1.4)], freq=3.6, decay=3.0), droop)
    return d
def switch_k(t): return 1.0 - ease_io(ramp(t, T_CLICK, T_CLICK + 0.16))

BLINKS_O = auto_blinks(T_SIDE2, T_CU_C2, mean=2.9, seed=41) + auto_blinks(T_SIDE_H, T_CU_H, mean=2.6, seed=5)
T_INS_GLINT = 55.95

# old man singles: where he looks (v: +1 the water / -1 Claude)
O_TURN = [(0.0, -1.0), (T_CU_OB, 1.0), (T_CU_O2 + 0.3, 1.0), (T_CU_O2 + 0.75, -1.0)]
def old_cu(t):
    q = PF.on_twos(t)
    od = dict(arms='hold', v=PF.turn_track(q, O_TURN), breath='v2', body='water')
    if T_CU_O <= q < T_CU_CR:
        sh = laugh_shake(t, [(L_NO_POINT['t_end'] + 0.1, L_NO_POINT['t_end'] + 0.45)])
        if sh: od['shake'] = sh
    return od
def punch_o(t):
    """CU_O: punch-in on 没意义啊。 (fast, then a slow creep)"""
    return 0.14 * ease_out3(ramp(t, L_NO_POINT['t0'] + 0.05, L_NO_POINT['t0'] + 0.25)) + 0.03 * ramp(t, T_CU_O, T_CU_CR)

# ====================================================================== INS_D / SIDE_H / BADGE / SIDE_H2 / CU_H (dusk)
T_TWITCH = T_INS_D + 0.8
T_LIFT0, T_LIFT1 = T_INS_D + 1.6, T_INS_D + 2.4
T_REEL0, T_REEL1 = T_SIDE_H + 0.15, T_SIDE_H + 1.75
T_CATCH = T_SIDE_H + 1.9
T_LOOK_HOOK = T_CATCH + 0.25
T_SMILE_O = T_CATCH + 0.65
T_LOOK_BADGE = T_SIDE_H + 2.85
T_GIVE0, T_GIVE1 = L_TAKE['t0'] + 0.1, L_TAKE['t0'] + 1.0
T_REACH0, T_REACH1 = T_GIVE0 + 0.25, T_GIVE0 + 0.95
T_DROP = T_GIVE0 + 1.3
T_WITH0, T_WITH1 = T_DROP + 0.35, T_DROP + 1.1
T_SCOOT0, T_SCOOT1 = T_DROP + 0.55, T_DROP + 0.95          # Claude scoots closer (the distance arc)
SCOOT = 9
T_HAPPY_H = T_DROP + 0.5
T_YES = L_YES['t0']
T_NOD0, T_NOD1 = T_YES + 0.05, T_YES + 0.65
T_RAISE0, T_RAISE1 = T_END + 1.4, T_END + 2.3
def reel_phase(t): return int((t - T_REEL0) * 8) % 4 if T_REEL0 <= t < T_REEL1 else 0
REEL_CRANK = [(30, 118), (40, 104), (30, 92), (20, 104)]   # the reel hand goes round (4 drawings)
def give_k(t): return ease_io(ramp(t, T_GIVE0, T_GIVE1)) * (1 - ease_io(ramp(t, T_WITH0, T_WITH1)))
def reach_k(t): return ease_out3(ramp(t, T_REACH0, T_REACH1))
def scoot_k(t): return ease_io(ramp(t, T_SCOOT0, T_SCOOT1))
def nod(t): return math.sin(math.pi * ramp(t, T_NOD0, T_NOD1))
H_TURN = [(0.0, 1.0), (T_LOOK_BADGE - 0.3, 1.0), (T_LOOK_BADGE, -1.0)]
