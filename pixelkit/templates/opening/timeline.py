"""《Claude 想请一天假》 opening (0-10.5 s) - the single source of truth for picture AND sound.

Story beats (Plan A):
  0.0  black - only Claude's green chin LED breathing (sleep), room tone + clock
  1.6  light fades up (ambient first, then the sun through the blinds + dust)
  3.045 '叮' (= beat 0 of the 132 BPM grid): '在吗？' + CRT wakes, 3.145 eyes wide + hop, 3.5 '好的！'
  3.6  dolly out; requests arrive as chat bubbles, their keyword bricks fall:
       周报 lands (beat 2) / LOGO bonks Claude's head (bar 1 downbeat) / 再短一点 lands on the pile
  6.682 wide (bar 2): counter HUD, brick rain accelerates, coins fly, snare roll + riser
  8.5  world freeze (sim time stops, total silence) - only Claude moves: tiny '好的！' + one coin -> 9,999
  9.0  burst: impact + Theme A, rain resumes harder, punch zoom + shake;  fade 10.3-10.5
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT)
import numpy as np
from pixelkit import blocks
from pixelkit.anim import Track, ramp, smoothstep, hop, squash_curve, shake, clamp01, ease_out3
from pixelkit.audio.music import Grid

FPS, DUR = 30, 10.5
G = Grid(132, t0=3.045)                 # beat 0 = the '叮'
def b(n): return G.t(n)

T_AMB0, T_AMB1 = 1.6, 2.8               # ambient fade-up
T_SUN0, T_SUN1 = 1.9, 3.0               # sun / rays / dust fade-up
T_DING = b(0)
T_WAKE = T_DING + 0.10
T_HOP_LAND = T_WAKE + 0.32
T_OK0 = b(1)
T_WIDE = b(8)                           # 6.682
T_ROLL = b(10)                          # 7.591
T_RISER = 7.4
T_FREEZE = b(12)                        # 8.500
T_RESUME = 9.0
FREEZE_LEN = T_RESUME - T_FREEZE
T_FADE0, T_END = 10.3, 10.5
G2 = Grid(132, t0=T_RESUME)             # Theme A after the freeze

def tau(t):
    """world/simulation time (stops during the freeze)."""
    if t < T_FREEZE: return t
    if t < T_RESUME: return T_FREEZE
    return t - FREEZE_LEN

def real(tw):
    """world time -> real time (for scheduling sounds of world events)."""
    return tw if tw < T_FREEZE else tw + FREEZE_LEN

def in_freeze(t): return T_FREEZE <= t < T_RESUME

# ------------------------------------------------------------------ set anchors (Office)
HEAD = (250, 121)                       # Claude head top-centre
DESK_Y = 165
CLAUDE_X = (222, 278)                   # bricks never fall in this column

# ------------------------------------------------------------------ chat feed (UI, 480x270 grid)
FEED_X, FEED_BOT = 12, 98
MSGS = [
    dict(t_in=T_DING, lines=['在吗？'], name='用户', avatar='#9be08a', t_out=b(2.5) + 0.15),
    dict(t_in=b(1.25), lines=['帮我写周报，要显得我很忙，', '但其实我啥也没干'], name='市场部 · 小李', avatar='#7aa7ff',
         t_out=b(5) + 0.25, brick=('周报', 2), x=290, lane='desk', t_land=b(2), t_ok=b(3)),
    dict(t_in=b(2.5), lines=['logo 放大的同时，再缩小一点'], name='设计总监', avatar='#f2a65a',
         t_out=6.55, brick=('LOGO', 1), x=236, lane='desk', t_land=b(4), t_ok=b(5.5),
         bonk=dict(y=HEAD[1] - 2, vx=118, vy=-250, to='floor')),
    dict(t_in=b(5), lines=['再短一点，但内容要更多'], name='产品经理', avatar='#e58fb4',
         t_out=7.25, brick=('再短一点', 4), x=286, lane='desk', t_land=b(6), t_ok=b(7)),
]
for _i, _m in enumerate(MSGS): _m['i'] = _i
def msg_h(m): return len(m['lines']) * 12 + 8 + (9 if m['name'] else 0)

OKS = [T_OK0] + [m['t_ok'] for m in MSGS if 't_ok' in m]          # big '好的！' bubbles
T_HUD_COUNTER = T_WIDE
T_HUD_TIME = 7.30

# ------------------------------------------------------------------ freeze moment (real time)
T_TINY_OK = T_FREEZE + 0.14
T_COIN0 = T_FREEZE + 0.20
T_COIN1 = T_FREEZE + 0.44               # coin reaches the counter -> 9,999

# ------------------------------------------------------------------ brick world
LANES = dict(desk=(338.0, DESK_Y, 166, 334), floor=(300.0, 222.0, 0, 480), floor2=(282.0, 228.6, 0, 480), floor3=(266.0, 235.3, 0, 480))
def Zof(lane): return LANES[lane][0]
RAIN_WORDS = ['PPT', '改需求', '在吗', '加急', '周报', '写代码', '翻译', '道歉信', '团建', '改一下', '高级感', '再改改', '方案',
              '总结', '文案', 'ASAP', '会议纪要', '周报', '述职', '急！', '改简历', '写首诗', '润色', '周报', '在吗？', '表格',
              'bug', '需求', '海报', '周报', '复盘', 'OKR']

def rain_schedule():
    """deterministic list of (tau_land, word_index, lane, x) for the brick rain."""
    rng = np.random.default_rng(20251019)
    out = []; tw = T_WIDE - 0.12; i = 0
    while tw < tau(DUR) - 0.05:
        if tw < T_FREEZE:
            u = clamp01((tw - (T_WIDE - 0.12)) / (T_FREEZE - T_WIDE + 0.12))
            rate = 3.0 + 19.0 * u ** 1.6
        else:
            rate = 24.0
        tw += float(rng.exponential(1 / rate)) * 0.6 + 0.4 / rate
        r = rng.uniform()
        if r < 0.16 and tw < T_FREEZE + 0.6: lane = 'desk'
        else: lane = ['floor', 'floor2', 'floor3'][int(rng.integers(0, 3))]
        out.append((tw, i % len(RAIN_WORDS), lane, float(rng.uniform()), int(rng.integers(0, 8))))
        i += 1
    return out

def build_sim():
    lanes = {}
    for k, (Z, y, x0, x1) in LANES.items():
        lanes[k] = blocks.Lane(Z=Z, y=y, x0=x0, x1=x1)
    lanes['desk'].fallback = 'floor'
    # the CRT occupies the left desk: bricks never use it (desk lane = right part only for landings)
    lanes['desk'].surf[166:222] = np.inf
    sim = blocks.Sim(lanes, g=900.0)
    hero = {}
    for m in MSGS:
        if 'brick' not in m: continue
        word, col = m['brick']
        br = blocks.brick([word], col, tail=False)
        surf = None
        if m['i'] == 3: surf = DESK_Y - hero[1].h + 1          # lands on top of 周报
        bd = sim.add_landing(m['t_land'], br, m['x'], m['lane'], y0=-30.0, surf_y=surf, bonk=m.get('bonk'),
                             name=f"msg{m['i']}")
        hero[m['i']] = bd
    words = {}
    for (tw, wi, lane, ux, col) in rain_schedule():
        key = (wi, col)
        if key not in words: words[key] = blocks.brick([RAIN_WORDS[wi]], col, tail=False)
        br = words[key]
        w = br.w
        if lane == 'desk':
            x = 280 + ux * (334 - 280 - w)
        else:
            # anywhere on the floor except Claude's column
            left = (20, CLAUDE_X[0] - w - 2); right = (CLAUDE_X[1] + 2, 462 - w)
            span_l = left[1] - left[0]; span_r = right[1] - right[0]
            v = ux * (span_l + span_r)
            x = left[0] + v if v < span_l else right[0] + (v - span_l)
        sim.add_landing(tw, br, x, lane, y0=-34.0 - br.h, name='rain')
    sim.run(tau(DUR) + 0.1)
    return sim, hero

# ------------------------------------------------------------------ rain '好的！' bubbles + coins (world time)
def ok_bursts():
    rng = np.random.default_rng(77)
    out = []; tw = T_WIDE + 0.05
    while tw < tau(DUR):
        if tw < T_FREEZE:
            u = clamp01((tw - T_WIDE) / (T_FREEZE - T_WIDE)); rate = 3.0 + 9.0 * u ** 1.3
        else:
            rate = 12.0
        tw += float(rng.exponential(1 / rate)) * 0.5 + 0.5 / rate
        dx = float(rng.uniform(-48, 48)); dy = float(rng.uniform(-20, 6))
        if abs(dx) < 14: dx = 14 * (1 if dx >= 0 else -1)
        out.append(dict(tw=tw, dx=dx, dy=dy, side=1 if dx > 0 else -1, k=int(rng.integers(0, 5))))
    return out
OK_BURSTS = ok_bursts()
OK_LIFE, COIN_DELAY, COIN_FLY = 0.55, 0.12, 0.42

# ------------------------------------------------------------------ counter
def counter_value(t):
    tw = tau(t)
    if tw < T_WIDE: return 4
    if t < T_FREEZE:
        u = clamp01((tw - T_WIDE) / (T_FREEZE - T_WIDE))
        return int(round(4 * (9998 / 4) ** (u ** 1.8)))
    if t < T_RESUME:
        return 9999 if t >= T_COIN1 else 9998
    u = clamp01((t - T_RESUME) / (DUR - T_RESUME))
    return int(round(9999 * 10 ** (2.4 * u ** 1.25)))

# ------------------------------------------------------------------ light
def light(t):
    amb = smoothstep(T_AMB0, T_AMB1, t)
    sun = smoothstep(T_SUN0, T_SUN1, t)
    return amb, sun

def led_k(t):
    if t >= T_DING: return 1.0
    return 0.12 + 0.88 * math.sin(math.pi * (t + 0.25) / 2.0) ** 2

def monitor(t):
    """(on, band 0..1 (CRT turn-on opening), flash 0..1)"""
    if t < T_DING: return 0.0, 0.0, 0.0
    u = (t - T_DING) / 0.17
    if u >= 1: return 1.0, 1.0, 0.0
    return 1.0, ease_out3(u), max(0.0, 1 - u / 0.45)

# ------------------------------------------------------------------ camera
ZOOM = Track([(0, 3.20), (1.6, 3.24, 'lin'), (3.0, 3.35, 'io'), (3.6, 3.35), (5.0, 2.3, 'io'), (5.6, 2.3),
              (6.75, 1.08, 'io'), (8.5, 1.0, 'o')], log=True)
CENTER = Track([(0, (250.0, 128.0)), (3.6, (250.0, 128.0)), (5.0, (246.0, 140.0), 'io'), (5.6, (246.0, 140.0)),
                (6.75, (240.0, 135.0), 'io')])

def cam_params(t):
    """zoom, cx, cy, shake_x, shake_y (output px)."""
    if in_freeze(t):
        z = ZOOM(T_FREEZE); cx, cy = CENTER(T_FREEZE); sx = sy = 0.0
        return z, cx, cy, sx, sy
    tt = t if t < T_FREEZE else T_FREEZE
    z = ZOOM(tt); cx, cy = CENTER(tt)
    if t >= T_RESUME:
        z = 1.0 * (1 + 0.03 * ease_out3((t - T_RESUME) / 0.09) + 0.012 * clamp01((t - T_RESUME - 0.1) / 1.4))
    sx = sy = 0.0
    for (t0, amp, dur, seed) in [(MSGS[2]['t_land'], 9.0, 0.30, 1), (T_RESUME, 18.0, 0.55, 2), (T_DING, 2.5, 0.12, 3)]:
        a, c = shake(t, t0, amp, dur, 29.0, seed); sx += a; sy += c
    if T_WIDE < t < T_FREEZE:                       # tremble as the rain builds
        k = clamp01((t - T_WIDE) / (T_FREEZE - T_WIDE)) ** 2 * 2.2
        sx += k * math.sin(t * 61.0); sy += k * math.cos(t * 47.0)
    if t >= T_RESUME:
        sx += 1.6 * math.sin(t * 57.0); sy += 1.6 * math.cos(t * 43.0)
    return z, cx, cy, sx, sy

# ------------------------------------------------------------------ Claude
def claude_state(t):
    """face, arms, phase, look, glow, squash, dy(hop), stars(0..1)"""
    s = dict(face='normal', arms='type', phase=0, look=(0, 0), glow=1.0, squash=0.0, dy=0.0, stars=0.0, led_k=led_k(t))
    # typing rhythm (frozen during the freeze)
    tt = t if t < T_FREEZE else (T_FREEZE if t < T_RESUME else t)
    rate = 9.0 if tt < T_WIDE else (9.0 + 9.0 * clamp01((tt - T_WIDE) / (T_FREEZE - T_WIDE)) if tt < T_FREEZE else 18.0)
    s['phase'] = int(tt * rate)
    if t < T_DING + 0.06:
        s.update(face='closed', arms='rest', glow=0.0)
        s['dy'] = -0.0 if t < 1.6 else 0.0
        return s
    if t < T_WAKE:
        s.update(face='half', arms='rest'); return s
    if t < T_HOP_LAND:
        s.update(face='wide', arms='up'); s['dy'] = hop(t, T_WAKE, 7.0, 0.32)
        s['squash'] = squash_curve(t, T_HOP_LAND, 0.16, 0.10) if t >= T_HOP_LAND else -0.10 * math.sin(math.pi * clamp01((t - T_WAKE) / 0.32))
        return s
    bonk_t = MSGS[2]['t_land']
    if bonk_t <= t < bonk_t + 0.58:
        s.update(face='dizzy', arms='rest', squash=squash_curve(t, bonk_t, 0.30, 0.20, 2.0))
        s['stars'] = 1.0 - ramp(t, bonk_t + 0.45, bonk_t + 0.58)
        return s
    s['squash'] = squash_curve(t, T_HOP_LAND, 0.16, 0.10)
    # big '好的！' moments
    for to in OKS:
        if to - 0.03 <= t < to + 0.36:
            s.update(face='happy', arms='rest' if to == T_OK0 else 'type')
            s['dy'] = hop(t, to - 0.03, 2.0, 0.18)
            return s
    if t < T_OK0 + 0.36: s.update(face='happy', arms='rest'); return s
    if in_freeze(t):
        s['arms'] = 'type'
        if t < T_FREEZE + 0.07: s['face'] = 'focus'
        elif t < T_FREEZE + 0.12: s['face'] = 'blink'
        elif t < T_TINY_OK: s.update(face='normal', look=(0, 1))
        elif t < T_TINY_OK + 0.22: s.update(face='happy')
        else: s.update(face='normal', look=(0, 1))
        return s
    # working
    s['face'] = 'focus'
    tw = tau(t)
    if tw >= T_WIDE:
        for ob in OK_BURSTS:
            if 0 <= tw - ob['tw'] < 0.10: s['face'] = 'happy'; break
        s['dy'] = -1.0 if (G.beat(t) % 1.0) < 0.18 and t < T_FREEZE else 0.0
        if t >= T_RESUME and (G2.beat(t) % 1.0) < 0.18: s['dy'] = -1.0
    # glance at the brick that landed next to Claude
    for m in MSGS:
        if 'brick' in m and m['i'] != 2 and 0.05 <= t - m['t_land'] < 0.32: s['look'] = (2, 0)
    if 0 <= t - MSGS[3]['t_land'] < 0.2: s['squash'] = max(s['squash'], 0.06 * (1 - (t - MSGS[3]['t_land']) / 0.2))
    return s

# ------------------------------------------------------------------ CRT chat log (tiny screen)
def screen_lines(t):
    log = []
    if t >= T_DING + 0.2: log.append(('在吗？', 'in'))
    if t >= T_OK0: log.append(('好的！', 'out'))
    for m in MSGS[1:]:
        if t >= m['t_in']: log.append((m['lines'][0][:6], 'in'))
        if t >= m['t_ok']: log.append(('好的！', 'out'))
    if tau(t) >= T_WIDE:
        n = int((tau(t) - T_WIDE) * 14)
        for k in range(n % 3 + 1): log.append(('好的！' if (n + k) % 2 else '周报周报', 'out' if (n + k) % 2 else 'in'))
    return log[-2:] if log else None
