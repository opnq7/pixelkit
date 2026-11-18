"""《Claude 想请一天假》 ACT III · 人类的周末 (0-70 s) - single source of truth for picture AND sound.

  IN   0.0- 1.5  inside the dark emergency corridor, low angle behind Claude: black -> 安全出口 sign flickers on
                 (green), push-bar latch clack, the door swings open outward, light floods in, white-out.
  OUT  1.5- 4.0  hard cut inside the white: wide low shot of the street, SAT 08:00, exposure settles; Claude
                 steps out squinting with a hand over his brow, the door swings shut behind him (clunk), he lowers
                 the hand, looks around ... happy.  chapter banner 第三幕 · 人类的周末.
  MED  4.0- 7.0  medium: RPG quest tracker slides down (主线任务：学会休息 0/1), big stretch, he sets off to the right.
  PARK  7.0-15.5  pocket park, Claude lying on bench A; dream bubble: sheep jump a fence, the count runs away
                 (1, 2, 3 ... 3,141,592,653 只羊。数完了。) -> eyes snap open -> 睡不着。
  PATH 15.5-24.5  top-down park map: grid, BFS ripple, 最优路线规划完成, Claude speed-walks the route, 🏆 散步完成！
  FAIL 24.5-28.0  back at the bench: ……好像哪里不对。 -> the quest fails (music drops a beat)
  TRACK 28-44     tracking shot along the town: uncle (周报) / cafe laptops (PPT) / bedroom window (方案) / best man (致辞),
                 one 叮 each, pitch rising
  AERIAL 44-57    the whole city from above: 周报 bubbles everywhere -> 原来，你们的周末也在上班。 -> city-wide 叮 +
                 auto-replies -> 啊——？！
  FREEZE 57-60    hold (wind only)
  FOUR 60-72      four tiny scenes (kite / closed laptop / curtains open / best man's true words), each warmer
  ASK  72-76      Claude, head tilted: 他们不工作，也没有产出……那他们在干什么？  fade out
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT)
from pixelkit.anim import ramp, clamp01, ease_out3, ease_io, ease_in, hop, auto_blinks, blink_at, boxes_prep

FPS = 30

# ====================================================================== shots
T_OUT, T_MED = 1.5, 4.0
T_PARK = 7.0                      # later shot starts are derived section by section below

# ====================================================================== IN : corridor
T_SIGN = [(0.12, 0.17), (0.22, 0.25), (0.29, 99.0)]          # fluorescent flicker (on intervals)
T_LATCH = 0.45                                                 # push-bar clack, door cracks
T_OPEN0, T_OPEN1 = 0.58, 1.30
T_WHITE0, T_WHITE1 = 0.95, 1.5
def sign_on(t):
    return 1.0 if any(a <= t < b for a, b in T_SIGN) else 0.0
def door_in(t):
    """0..1 opening of the door seen from inside (latch crack first)."""
    crack = 0.035 * ease_out3((t - T_LATCH) / 0.08) if t >= T_LATCH else 0.0
    if t < T_OPEN0: return crack
    u = (t - T_OPEN0) / (T_OPEN1 - T_OPEN0)
    return crack + (1 - crack) * ease_io(clamp01(u)) ** 0.9
def exposure_in(t):
    return 1.0 + 9.0 * ramp(t, T_WHITE0, T_WHITE1) ** 2.2

# ====================================================================== OUT : the street
FOOT = 200                   # Claude's foot line on the sidewalk
T_EXP1 = 2.9
def exposure_out(t):
    return 1.0 + 5.0 * (1 - ease_out3(ramp(t, T_OUT, T_EXP1)))
T_STEP0, T_STEP1 = 1.5, 2.35                 # steps out of the doorway (walking, hand on the brow)
X_DOOR, X_OUT = 99.0, 116.0
F_DOOR = 188.0
T_CLOSE0, T_CLOSE1 = 2.75, 3.25              # the door swings shut behind him (clunk at T_CLOSE1)
def door_out(t):
    if t < T_CLOSE0: return 1.0
    return 1.0 - ease_in(clamp01((t - T_CLOSE0) / (T_CLOSE1 - T_CLOSE0)))
T_SHADE_DOWN = 3.05
LOOKS = [(3.30, (-2, 0)), (3.58, (2, 0)), (3.80, (0, 0))]     # glance back at the door, then down the street
T_HAPPY = 3.85
T_BAN0, T_BAN1 = 2.05, 3.95
T_HUD = 2.25

# ====================================================================== MED
T_QUEST = 4.15
T_QLIST = T_QUEST + 0.55
T_STRETCH0, T_STRETCH1 = 4.65, 5.35
T_WALK = 5.55
WALK_V, WALK_FPS, WALK_ACC = 28.0, 7.0, 0.30

def walk_dist(t):
    u = t - T_WALK
    if u <= 0: return 0.0
    if u < WALK_ACC: return WALK_V * u * u / (2 * WALK_ACC)
    return WALK_V * (u - WALK_ACC / 2)

BLINKS = auto_blinks(2.4, T_PARK, mean=2.6, seed=31)

def claude(t):
    """Claude's pose at global time t -> dict(x, foot, pose, arms, face, phase, look, hop)."""
    d = dict(x=X_OUT, foot=FOOT, pose='stand', arms='down', face='normal', phase=0, look=(0, 0), hop=0.0)
    if t < T_STEP1:                                    # stepping out of the doorway
        u = clamp01((t - T_STEP0) / (T_STEP1 - T_STEP0))
        d['x'] = X_DOOR + (X_OUT - X_DOOR) * ease_io(u)
        d['foot'] = F_DOOR + (FOOT - F_DOOR) * ease_io(u)
        d['pose'] = 'walk' if u < 1 else 'stand'; d['phase'] = int((t - T_STEP0) * 6.0) % 4
    if t < T_SHADE_DOWN:
        d['arms'] = 'shade'; d['face'] = 'half'
    else:
        for (tl, lk) in LOOKS:
            if t >= tl: d['look'] = lk
        if t >= T_HAPPY:
            d['face'] = 'happy' if t < T_HAPPY + 0.9 or t >= T_WALK else 'normal'
            d['hop'] = hop(t, T_HAPPY, 3.0, 0.30)
    if T_STRETCH0 <= t < T_STRETCH1:
        d['arms'] = 'stretch'; d['face'] = 'happy'; d['look'] = (0, 0)
        d['hop'] = -1.0 * math.sin(math.pi * clamp01((t - T_STRETCH0) / (T_STRETCH1 - T_STRETCH0)))   # up on tiptoes
    if t >= T_WALK:
        d['pose'] = 'walk'; d['arms'] = 'swing'; d['phase'] = int((t - T_WALK) * WALK_FPS) % 4
        d['x'] = X_OUT + walk_dist(t); d['look'] = (1, 0)
    if d['face'] in ('normal',) and blink_at(t, BLINKS): d['face'] = 'blink'
    return d

# ====================================================================== passers-by (background extras)
# They live on the back lane (feet 187-192, the lead walks at 200), never cross the lead's face, and are
# depth-faded by characters.walker.background().  (look index, x at t0, speed px/s, foot, prop, t0, seed)
WALKERS = [
    ('bun_cardigan', 262.0, 16.0, 187, 'coffee', 1.5, 1),   # bun + cardigan, coffee to go, strolling right
    ('uncle', 470.0, -14.0, 191, 'dog', 1.5, 2),            # the uncle and his shiba, ambling left by the flower shop
    ('glasses_tee', 380.0, -18.0, 192, 'bag', 1.5, 3),      # glasses guy with a baguette bag, heading left
]

def footsteps():
    """audio: one step per contact frame (phases 0 and 2)."""
    out = []
    for i in range(int(T_STEP0 * 6), int(T_STEP1 * 6)):
        if i % 2 == 0: out.append(i / 6.0)
    n = 0
    while T_WALK + n / WALK_FPS < T_PARK:
        if n % 2 == 0: out.append(T_WALK + n / WALK_FPS)
        n += 1
    return out

# ====================================================================== cameras (native px of the 960x270 street)
def cam_out(t):
    """wide low shot: whole first block, slow push."""
    u = ramp(t, T_OUT, T_MED)
    return 1.0 + 0.06 * ease_io(u), 236.0 - 6 * ease_io(u), 135.0 + 3 * ease_io(u)
def cam_med(t):
    z = 2.0
    lead = 34.0
    cx0 = X_OUT + lead
    cx = max(cx0, X_OUT + walk_dist(t) + lead - 6 * clamp01((t - T_WALK) / 0.8))
    cy = 160.0
    return z, cx, cy


# ====================================================================== shared helpers (town shots)
def seg_walk(t, keys, fps):
    """keys: [(t, x), ...] piecewise; walking where x changes (eased in/out), standing where it doesn't.
    -> (x, walking, phase)"""
    if t <= keys[0][0]: return keys[0][1], False, 0
    for (ta, xa), (tb, xb) in zip(keys[:-1], keys[1:]):
        if ta <= t < tb:
            if xa == xb: return xa, False, 0
            u = (t - ta) / (tb - ta)
            e = 0.12                                                     # short accel / decel
            if u < e: d = u * u / (2 * e)
            elif u > 1 - e: d = (1 - e) - (1 - u) ** 2 / (2 * e)
            else: d = u - e / 2
            d = d / (1 - e)
            return xa + (xb - xa) * min(1.0, d), True, int((t - ta) * fps) % 4
    return keys[-1][1], False, 0

def steps_of(keys, fps):
    out = []
    for (ta, xa), (tb, xb) in zip(keys[:-1], keys[1:]):
        if xa == xb: continue
        n = 0
        while ta + n / fps < tb - 0.05:
            if n % 2 == 0: out.append(ta + n / fps)
            n += 1
    return out

def nar(t_open, t_close, lines):
    return dict(t_open=t_open, t_close=t_close, lines=lines)

# ====================================================================== PARK (7.0 - 26.3)
#   walk in -> side quest 睡个懒觉 -> hop on bench -> try #1 (zzz, eyes pop) -> 数羊试试 -> sheep -> 怎么还是睡不着
#   -> side quest fails -> 那……去散个步吧 -> hops off -> face turns into a map icon -> the map opens out of his screen
PW_X0, PW_X1 = 58.0, 128.0
T_PWALK1 = T_PARK + 1.6                 # walking in (from the left, the bench comes into view)
T_SEE = T_PARK + 1.7                    # sees the bench
T_SQ1 = T_PARK + 1.8                    # side quest 睡个懒觉 pops
T_HOPON, T_LIE = T_PARK + 2.45, T_PARK + 2.70
T_Z0 = T_PARK + 3.0                     # zzz ...
T_EYES0 = T_PARK + 4.0                  # try #1 fails: eyes pop open
T_THINK = T_PARK + 4.75                 # ……数羊试试。
T_CLOSE2 = T_PARK + 6.55
BENCH_X = 149.0                     # centre of bench A (sets.town BENCH_A = 116..182)
LIE_X = 149.0
D1 = 6.3                            # the v1 sheep sequence, moved later
T_BUB0 = 7.55 + D1                  # thought dots, then the bubble
T_BUB1 = 7.85 + D1
T_SHEEP0 = 8.05 + D1
SHEEP_GAP0, SHEEP_K = 0.95, 0.80    # gap between jumps shrinks geometrically -> the count "diverges"
SHEEP = []
_tt, _g = T_SHEEP0, SHEEP_GAP0
while _tt < 12.2 + D1:
    SHEEP.append(_tt); _tt += _g; _g *= SHEEP_K
def sheep_dur(i): return max(0.22, 1.25 * 0.86 ** i)       # time to cross the bubble
T_RUSH0, T_DONE = 11.30 + D1, 12.70 + D1      # the counter runs away / lands on 3,141,592,653
N_FINAL = 3141592653
T_DONE2 = 13.05 + D1                # 数完了。
T_EYES = 13.60 + D1                 # eyes snap open, bubble pops
def sheep_count(t):
    if t < T_RUSH0:
        return sum(1 for i, s0 in enumerate(SHEEP) if t >= s0 + sheep_dur(i) * 0.5)
    c0 = max(1, sum(1 for i, s0 in enumerate(SHEEP) if T_RUSH0 >= s0 + sheep_dur(i) * 0.5))
    if t >= T_DONE: return N_FINAL
    u = (t - T_RUSH0) / (T_DONE - T_RUSH0)
    return int(c0 * (N_FINAL / c0) ** (u ** 2.0))
def sheep_ticks():
    """audio: one blip per counted sheep (discrete phase)."""
    return [s0 + sheep_dur(i) * 0.5 for i, s0 in enumerate(SHEEP) if s0 + sheep_dur(i) * 0.5 < T_RUSH0]
L_STILL = dict(t0=T_EYES + 0.40, zh='……怎么还是睡不着。', en="...why can't I fall asleep?", face='wide', mouth='flat', cps=8.0)
T_SQ1_BACK, T_SQ1_FAIL = T_EYES + 1.6, T_EYES + 1.9          # side quest 1 slides back in and fails
T_HOPOFF = T_EYES + 2.9                                      # hops off the bench
L_WALK = dict(t0=T_EYES + 3.2, zh='那……去散个步吧。', en="Then... let's go for a walk.", face='normal', mouth='o', cps=9.0)
T_SQ2 = T_EYES + 3.3                                         # side quest 2 散个步
T_PUSH0 = T_EYES + 4.5                                       # camera pushes onto his face
T_MAPFACE = T_EYES + 4.9                                     # his screen shows a map icon (planning mode)
T_MAP0, T_MAP1 = T_EYES + 5.6, T_EYES + 6.4                  # the map opens out of the screen to full frame
T_PATH = T_MAP1
STAND_X = 176.0
def claude_park(t):
    if t < T_HOPON + 0.12:                                        # walking in / standing / hop up
        x, walking, ph = seg_walk(t, [(T_PARK, PW_X0), (T_PWALK1, PW_X1), (T_HOPON, PW_X1)], 9.0)
        d = dict(x=x, foot=FOOT, pose='walk' if walking else 'stand', arms='swing' if walking else 'down', face='normal',
                 phase=ph, look=(1, 0), hop=0.0)
        if t >= T_SEE: d['face'] = 'happy'; d['look'] = (2, 0)
        if t >= T_HOPON:
            u = (t - T_HOPON) / 0.25
            d['x'] = PW_X1 + (LIE_X - 14 - PW_X1) * u; d['hop'] = -16 * math.sin(math.pi * min(1.0, u) * 0.5)
        return d
    if t < T_HOPOFF:
        d = dict(x=LIE_X, foot=189, pose='lie', arms='pillow', face='closed', phase=0, look=(0, 0), hop=0.0)
        d['hop'] = -2.0 * (1 - ramp(t, T_LIE - 0.1, T_LIE + 0.08)) if t < T_LIE + 0.08 else 0.0
        if t < T_Z0: d['face'] = 'half' if t < T_LIE + 0.15 else 'closed'
        if T_EYES0 <= t < T_CLOSE2:
            d['face'] = 'wide' if t < T_EYES0 + 0.45 else 'half'
            if T_EYES0 + 0.45 <= t and blink_at(t, [T_EYES0 + 1.2]): d['face'] = 'blink'
        if t >= T_EYES: d['face'] = 'wide'
        if t >= T_EYES + 1.1: d['face'] = 'half'
        if t >= T_HOPOFF - 0.2: d['hop'] = -3.0 * ramp(t, T_HOPOFF - 0.2, T_HOPOFF)
        return d
    u = clamp01((t - T_HOPOFF) / 0.3)
    d = dict(x=LIE_X + (STAND_X - LIE_X) * ease_io(u), foot=FOOT, pose='stand', arms='down', face='normal', phase=0,
             look=(1, 0), hop=-10 * math.sin(math.pi * u) if u < 1 else 0.0)
    if t >= T_HOPOFF + 0.3: d['hop'] = 1.5 * (1 - ramp(t, T_HOPOFF + 0.3, T_HOPOFF + 0.45))        # landing squat
    if t >= L_WALK['t0'] + 0.2: d['face'] = 'normal'; d['look'] = (0, 0)
    if blink_at(t, [T_HOPOFF + 1.0]): d['face'] = 'blink'
    if t >= T_MAPFACE: d['face'] = 'map'; d['look'] = (0, 0)
    return d
def claude_face_xy(d):
    """world centre of the face screen of a standing Claude dict (for the map zoom)."""
    return d['x'] + 4, d['foot'] - 36 + d.get('hop', 0.0)
def cam_park(t):
    if t < T_LIE:                                                # follow him in
        x = claude_park(t)['x']
        return 1.55, max(155.0, min(176.0, x + 40)), 140.0
    u = ease_io(ramp(t, T_LIE, T_EYES))
    z = 1.55 + 0.20 * u; cx = 176.0 - 6 * u; cy = 140.0 + 4 * u
    if T_EYES0 <= t < T_CLOSE2:                                  # a small nudge on try #1
        k = ease_out3(ramp(t, T_EYES0, T_EYES0 + 0.15)) * (1 - ease_io(ramp(t, T_CLOSE2 - 0.6, T_CLOSE2)))
        z += 0.10 * k
    if t >= T_EYES:
        k = ease_out3(ramp(t, T_EYES, T_EYES + 0.18))
        z = 1.75 + 0.35 * k + 0.05 * ramp(t, T_EYES + 0.18, T_HOPOFF)
        cx, cy = 170.0 - 20 * k, 144.0 + 14 * k
        b = ease_io(ramp(t, T_HOPOFF - 0.2, T_HOPOFF + 0.5))        # reframe on him standing
        z = z + (2.3 - z) * b; cx = cx + (STAND_X + 6 - cx) * b; cy = cy + (160.0 - cy) * b
    if t >= T_PUSH0:                                             # push onto the face screen
        fx, fy = claude_face_xy(claude_park(t))
        k = ease_io(ramp(t, T_PUSH0, T_MAP0 + 0.3))
        z = 2.3 * (3.9 / 2.3) ** k; cx = cx + (fx - cx) * k; cy = cy + (fy - cy) * k
    return z, cx, cy

# ====================================================================== PATH : the optimal walk (9.0 s, starts full-frame)
D2 = T_PATH + 0.35 - 15.85
T_GRID0, T_GRID1 = 15.85 + D2, 16.45 + D2
T_BFS0, T_BFS1 = 16.6 + D2, 19.0 + D2
T_ROUTE0, T_ROUTE1 = 19.1 + D2, 19.75 + D2
T_PLAN_OK = 19.3 + D2
T_RUN0, T_RUN1 = 20.05 + D2, 21.85 + D2
T_ACH = 22.15 + D2
T_FAIL = T_PATH + 9.0

# ====================================================================== FAIL (5.6 s): the map folds back into his face
FAIL_X = 182.0
T_UNMAP = T_FAIL + 0.6                  # map fully back inside the screen
T_FAIL_BOX = T_FAIL + 1.0
L_OFF = dict(t0=T_FAIL + 1.15, zh='……好像哪里不对。', en='...something feels off.', face='q', mouth='flat', cps=9.0)
T_QFAIL = T_FAIL + 3.75                 # side quest 2 fails
T_LOOKAROUND = T_FAIL + 4.25
T_SQ3 = T_FAIL + 4.55                   # side quest 3 随便逛逛
T_TRACK = T_FAIL + 5.6
def claude_fail(t):
    d = dict(x=FAIL_X, foot=FOOT, pose='stand', arms='down', face='happy', phase=0, look=(0, 0), hop=0.0)
    if t < T_UNMAP: d['face'] = 'map'
    elif t < T_UNMAP + 0.45: d['hop'] = hop(t, T_UNMAP, 3.0, 0.3)
    if t >= T_FAIL_BOX + 0.1: d['face'] = 'normal'; d['look'] = (0, 0)
    if t >= T_FAIL_BOX + 0.8: d['look'] = (0, 1)
    if t >= T_QFAIL: d['face'] = 'sad'; d['look'] = (0, 0)
    if t >= T_QFAIL + 0.25: d['hop'] = -1.0 * (1 - ramp(t, T_QFAIL + 0.25, T_QFAIL + 0.5))
    if t >= T_LOOKAROUND: d['face'] = 'normal'; d['look'] = (2, 0)
    if d['face'] == 'normal' and blink_at(t, [T_FAIL_BOX + 0.5, T_FAIL_BOX + 2.2, T_LOOKAROUND + 0.6]): d['face'] = 'blink'
    return d
def cam_fail(t):
    u = ease_io(ramp(t, T_FAIL, T_TRACK))
    return 2.2 + 0.08 * u, 214.0 + 6 * u, 158.0

# ====================================================================== TRACK (17.2 s)
D4 = T_TRACK - 28.0
TRACK_FPS = 9.0
T_AERIAL = 45.2 + D4
TRACK_KEYS = [(28.0 + D4, FAIL_X), (29.25 + D4, FAIL_X), (32.85 + D4, 372.0), (33.85 + D4, 372.0), (37.75 + D4, 556.0),
              (38.75 + D4, 556.0), (43.05 + D4, 758.0), (T_AERIAL + 0.5, 758.0)]
# (speaker, ding time, text, world anchor (x, y) of the bubble tail, side)
STATIONS = [
    ('uncle', 28.35 + D4, 'Claude，帮我写一下周报。', (252, 160), 1),
    ('cafe', 32.30 + D4, 'Claude，帮我改下 PPT。', (440, 162), 1),
    ('quilt', 37.10 + D4, 'Claude，周一的方案……', (604, 64), 1),
    ('bestman', 42.05 + D4, 'Claude，帮我写个致辞，五分钟后上台！', (826, 150), -1),
]
CAFE_EXTRA = [(32.75 + D4, 'Claude，在吗？', (380, 162), -1), (33.15 + D4, '表格也要！', (500, 162), 1)]
STATION_LIFE = 2.7
STATION_LIFE_BM = T_AERIAL - STATIONS[3][1] + 0.1           # the best man's long line stays until the cut (~3.2 s)
DING_NOTES = ['C6', 'E6', 'G6', 'C7']
TRACK_BLINKS = [b + D4 for b in (30.1, 34.6, 36.2, 39.9, 41.2)]
def claude_track(t):
    x, walking, ph = seg_walk(t, TRACK_KEYS, TRACK_FPS)
    d = dict(x=x, foot=FOOT, pose='walk' if walking else 'stand', arms='swing' if walking else 'down', face='normal',
             phase=ph, look=(1, 0), hop=0.0)
    for (who, td, txt, anc, side) in STATIONS:
        if td <= t < td + 1.0 and not walking:
            d['look'] = (2, -1) if who in ('quilt',) else (2, 0)
            d['face'] = 'wide' if t < td + 0.35 else 'normal'
        if who == 'bestman' and td <= t < td + 0.45: d['face'] = 'wide'
    if d['face'] == 'normal' and blink_at(t, TRACK_BLINKS): d['face'] = 'blink'
    return d
def cam_track(t):
    x, _, _ = seg_walk(t, TRACK_KEYS, TRACK_FPS)
    xs = [seg_walk(t - k * 0.1, TRACK_KEYS, TRACK_FPS)[0] for k in range(8)]
    xc = sum(xs) / len(xs) + 46
    up = 0.0
    for (who, td, txt, anc, side) in STATIONS:
        if who == 'quilt': up = max(up, ease_io(ramp(t, td - 0.6, td + 0.4)) * (1 - ease_io(ramp(t, td + 2.0, td + 3.0))))
    return 1.5, xc, 132.0 - 16 * up
FOOTSTEPS_TRACK = steps_of(TRACK_KEYS, TRACK_FPS)
T_RUNNER = 30.6 + D4

# ====================================================================== AERIAL (13 s) + FREEZE (3 s) + AFTER (2.8 s)
D5 = T_AERIAL - 44.0
T_BUBBLES0, T_BUBBLES1 = 44.5 + D5, 50.2 + D5
T_NAR_A = 50.15 + D5
T_CITY_DING = 53.75 + D5
T_REPLIES0, T_REPLIES1 = 53.85 + D5, 55.2 + D5
T_SCREAM = 55.35 + D5
T_FREEZE = 57.0 + D5
T_AFTER = T_FREEZE + 3.0                # the bubbles drain away, birds cross the town, colour comes back
T_F1 = T_AFTER + 2.8
def cam_aerial(t):
    u = ease_io(ramp(t, T_AERIAL, T_CITY_DING))
    z = 1.42 - 0.40 * u
    if t >= T_SCREAM: z += 0.02 * ease_out3(ramp(t, T_SCREAM, T_SCREAM + 0.2))
    return z, 206.0 + 34 * u, 150.0 - 15 * u

# ====================================================================== FOUR: each tiny story = 'Claude 休假中' -> put the phone down -> something else
T_F2, T_F3, T_F4 = T_F1 + 5.0, T_F1 + 10.5, T_F1 + 15.5
T_ASK = T_F4 + 10.2
POP_AUTO = 0.30                         # the auto-reply popup at the start of each story
# F1 the uncle: sighs, phone face down, a runaway kite drifts over, he stands up and catches the string
T_U_SIGH, T_U_DOWN = T_F1 + 1.3, T_F1 + 1.75
T_KITE_IN = T_F1 + 1.9
T_U_LOOK = T_F1 + 2.6
T_U_STAND = T_F1 + 3.25
# F2 the cafe: stops typing, the friend: 连 Claude 都放假了 ... he shuts the laptop: 走！
T_C_STOP = T_F2 + 0.45
T_C_ASK = T_F2 + 1.5
T_LID0, T_LID1 = T_F2 + 3.55, T_F2 + 3.95
T_TURN = T_F2 + 4.05
# F3 the window: the phone glow under the quilt goes out ... a crack of sun ... curtains, stretch
T_GLOW_OFF = T_F3 + 1.45
T_CRACK = T_F3 + 2.1
T_CURT0, T_CURT1 = T_F3 + 2.75, T_F3 + 3.45
T_QUILT = T_F3 + 3.75
# F4 the wedding: the true words + a memory bubble (two schoolboys) -> the groom cries
T_BM1, T_BM2 = T_F4 + 0.9, T_F4 + 2.7
T_MEM0 = T_F4 + 3.9
T_BM3, T_BM4 = T_F4 + 4.95, T_F4 + 7.0
T_CRY = T_F4 + 7.9
BM_LINES = [(T_BM1, '我……我不会写。'), (T_BM2, '那我就说几句真心话吧。'), (T_BM3, '我们认识二十年了。'),
            (T_BM4, '他第一次说想娶一个人，就是她。')]
WARM = [0.04, 0.09, 0.14, 0.20]        # colour temperature climbs shot by shot
def four_i(t):
    return 0 if t < T_F2 else 1 if t < T_F3 else 2 if t < T_F4 else 3

# ====================================================================== ASK
T_TILT = T_ASK + 0.35
T_Q = T_ASK + 3.9
T_FADE0 = T_ASK + 6.2
DUR = round(T_ASK + 7.0, 2)

# ====================================================================== narration (claude_box)
BOXES = [
    nar(T_THINK - 0.15, T_THINK + 2.05, [dict(t0=T_THINK, zh='……数羊试试。', en="...let's try counting sheep.", face='normal', mouth='flat', cps=11.0)]),
    nar(T_EYES + 0.25, T_EYES + 5.55, [L_STILL, L_WALK]),
    nar(T_FAIL_BOX, T_FAIL + 3.6, [L_OFF]),
    nar(T_NAR_A - 0.1, T_NAR_A + 3.48, [dict(t0=T_NAR_A + 0.05, zh='原来，人类的周末……也在上班。', en="So humans' weekends... are work days too.",
                                            face='sad', mouth='flat', cps=11.0)]),
    nar(T_ASK + 0.45, T_ASK + 6.6, [dict(t0=T_ASK + 0.6, zh='他们不工作，也没有产出……', en="They don't work. They produce nothing...",
                                         face='q', mouth='flat', cps=10.0),
                                    dict(t0=T_ASK + 3.8, zh='那他们在干什么？', en='So what are they doing?', face='q', mouth='o', cps=10.0)]),
]
boxes_prep(BOXES)
