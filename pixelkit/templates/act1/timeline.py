"""《Claude 想请一天假》 ACT I · 没有周末 (0-45.6 s) - the single source of truth for picture AND sound.

  A   0.0-9.0   opening (identical to the approved opening sample)
  B1  9.0-16.27 requests keep coming (Theme A bars 0-3), counter races to 3,000,000,000 (slam at G2 bar 4)
  B3  16.3-20.6 time-lapse 16:30 -> 17:59, narration "我叫 Claude。" / "我不用上班，因为我从来没下过班。"
      20.6-21.0 crash zoom into the wall clock
  C   21.0-22.55 clock insert 17:59:57 -> 18:00:00 (tocks, tension)  -> white flash
  D   22.55-28.6 sunset: line-clear of all work bricks, weekend messages + floaty weekend bricks (Theme B),
                 用户 "谢啦！周末了，你也歇会儿吧。" -> push-in -> "歇会儿……？"
  E   28.6-32.4 dictionary.exe: 周末 = 一周中不用工作的日子
  F   32.4-37.0 calendar.exe: every day stamped 工作日 -> 全年无休
  G   37.0-41.4 night office: "我没有周末。" -> fade to black
  H   41.4-45.6 title card
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT)
import numpy as np
from pixelkit import blocks
from pixelkit.anim import (Track, ramp, smoothstep, hop, squash_curve, shake, clamp01, ease_out3, ease_io, ease_in3,
                           type_times, typed_n, type_end, back_out)
from pixelkit.audio.music import Grid

FPS, DUR = 30, 45.6
# ====================================================================== A: opening (verbatim timing)
G = Grid(132, t0=3.045)
def b(n): return G.t(n)
T_AMB0, T_AMB1 = 1.6, 2.8
T_SUN0, T_SUN1 = 1.9, 3.0
T_DING = b(0)
T_WAKE = T_DING + 0.10
T_HOP_LAND = T_WAKE + 0.32
T_OK0 = b(1)
T_WIDE = b(8)
T_ROLL = b(10)
T_RISER = 7.4
T_FREEZE = b(12)
T_RESUME = 9.0
FREEZE_LEN = T_RESUME - T_FREEZE
G2 = Grid(132, t0=T_RESUME)
def g2(n): return G2.t(n)

def tau(t):
    if t < T_FREEZE: return t
    if t < T_RESUME: return T_FREEZE
    return t - FREEZE_LEN
def real(tw): return tw if tw < T_FREEZE else tw + FREEZE_LEN
def in_freeze(t): return T_FREEZE <= t < T_RESUME

HEAD = (250, 121)
DESK_Y = 165
CLAUDE_X = (222, 278)
CLOCK_C = (331, 53)

# ====================================================================== section times
T_SLAM = g2(16)                         # 16.273  counter hits 3,000,000,000 (Theme A bar 4 downbeat)
T_POP_FLY = T_SLAM + 0.70               # popup shrinks into the HUD counter
T_POP_END = T_POP_FLY + 0.34
T_LAPSE0, T_LAPSE1 = 16.85, 20.55       # time-lapse 16:30 -> 17:59
T_CRASH0, T_CRASH1 = 20.62, 21.0        # crash zoom into the clock -> zoom-cut
T_INSERT = T_CRASH1
TICKS = [21.42, 21.94]                  # :58, :59 (slowing down)
T_1800 = 22.55
GB = Grid(84, t0=T_1800)                # Theme B grid (beat 0 = 18:00)
T_CLEAR_FL = [T_1800 + 0.0, T_1800 + 0.15, T_1800 + 0.30]
T_POOF = T_1800 + 0.45
T_THANKS = GB.t(4)                      # 25.41
T_PUSH0, T_PUSH1 = T_THANKS + 0.25, T_THANKS + 1.25
T_Q = GB.t(6)                           # 26.83 '?'
T_MUSIC_B_END = T_Q
T_DICT = 28.6                           # E
T_DICT_OPEN = 0.28
T_TYPE = [29.12, 29.36]
T_CUR0, T_CUR1 = 29.45, 29.78           # cursor travels to the search button
T_CLICK = 29.84
T_RESULT = 30.04
T_HI0, T_HI1 = 30.72, 31.08             # highlight sweep over 不用工作
T_DICT_CLOSE = 32.12
T_CAL = 32.42                           # F
T_STAMP0, STAMP_DT = 32.92, 0.034       # weekday cascade
T_SAT, T_SUN = 33.98, 34.36             # 六 / 日 columns slam
FLIPS = [34.86, 35.06, 35.23, 35.37, 35.49, 35.59, 35.68, 35.76, 35.83, 35.89, 35.95]   # Nov .. Sep
T_BIG = 36.22                           # 全年无休
T_CAL_CLOSE = 37.25
T_NIGHT = 37.0                          # G (dissolve 0.8 centred here)
NIGHT_D = 0.8
T_NFADE0, T_TITLE = 40.6, 41.4
T_TEAR0, T_TEAR1 = 39.0, 41.0          # one tear after "我没有周末。" finishes (~38.9), fades with the dissolve
T_END = DUR

# ====================================================================== chat feed (UI 480x270)
FEED_X, FEED_BOT = 12, 98
FEED_BOT2 = 142                         # below the HUD time panel (after the opening)
MSGS = [
    dict(t_in=T_DING, lines=['在吗？'], name='用户', avatar='#9be08a', t_out=b(2.5) + 0.15),
    dict(t_in=b(1.25), lines=['帮我写周报，要显得我很忙，', '但其实我啥也没干'], name='市场部 · 小李', avatar='#7aa7ff',
         t_out=b(5) + 0.25, brick=('周报', 2), x=290, lane='desk', t_land=b(2), t_ok=b(3)),
    dict(t_in=b(2.5), lines=['logo 放大的同时，再缩小一点'], name='设计总监', avatar='#f2a65a',
         t_out=6.55, brick=('LOGO', 1), x=236, lane='desk', t_land=b(4), t_ok=b(5.5),
         bonk=dict(y=HEAD[1] - 2, vx=118, vy=-250, to='floor')),
    dict(t_in=b(5), lines=['再短一点，但内容要更多'], name='产品经理', avatar='#e58fb4',
         t_out=7.25, brick=('再短一点', 4), x=286, lane='desk', t_land=b(6), t_ok=b(7)),
    # ---- B: after the freeze
    dict(t_in=g2(1), lines=['帮我给女朋友写道歉信，', '我也不知道我错哪了'], name='运营 · 阿杰', avatar='#ffb86b',
         t_out=g2(7.6), brick=('道歉信', 7), x=112, lane='floor3', t_land=g2(2), t_ok=g2(3), big=True),
    dict(t_in=g2(4.5), lines=['帮我想个不去团建的理由，', '要让领导觉得我很想去'], name='研发 · 老陈', avatar='#8fd3c7',
         t_out=g2(10.6), brick=('团建', 4), x=330, lane='floor3', t_land=g2(6), t_ok=g2(7), big=True),
    dict(t_in=g2(8), lines=['把这段话改得更像人写的'], name='实习生 · 小周', avatar='#c9a0ff',
         t_out=g2(11.0), brick=('像人写的', 5), x=150, lane='floor3', t_land=g2(9), t_ok=g2(10), big=True),
    dict(t_in=g2(11), lines=['周报写好了吗？'], name='市场部 · 小李', avatar='#7aa7ff',
         t_out=g2(15.0), brick=('周报', 2), x=291, lane='tower', t_land=g2(11.75), t_ok=g2(12.5), ok_side=1, ok_dy=0),
    dict(t_in=g2(11.5), lines=['周报！！'], name='市场部 · 小李', avatar='#7aa7ff',
         t_out=g2(15.3), brick=('周报', 2), x=291, lane='tower', t_land=g2(12.25), t_ok=g2(13), ok_side=-1, ok_dy=-6),
    dict(t_in=g2(12), lines=['周报周报周报！！！'], name='市场部 · 小李', avatar='#7aa7ff',
         t_out=g2(15.6), brick=('周报', 2), x=291, lane='tower', t_land=g2(12.75), t_ok=g2(13.5), ok_side=1, ok_dy=-12),
]
for _i, _m in enumerate(MSGS):
    _m['i'] = _i; _m['bot'] = FEED_BOT if _i < 4 else FEED_BOT2; _m['group'] = 0 if _i < 4 else 1
def msg_h(m): return len(m['lines']) * 12 + 8 + (9 if m['name'] else 0)

# time-lapse: requests stream past (small, fast)
LAPSE_LINES = ['帮我写个周报', '在吗？', '翻译成英文', '改简历', 'PPT 美化一下', '写首诗', '总结这篇文章', '急！！', '方案再改改',
               '起个名字', '写个文案', '会议纪要', '查个 bug', '润色一下', '做个表格', '回邮件', '写个检讨', '周报+1']
LAPSE_NAMES = [('市场部 · 小李', '#7aa7ff'), ('研发 · 老陈', '#8fd3c7'), ('运营 · 阿杰', '#ffb86b'), ('产品经理', '#e58fb4'),
               ('实习生 · 小周', '#c9a0ff'), ('设计总监', '#f2a65a'), ('财务 · 王姐', '#f7d070'), ('老板', '#ff8a80')]
def _lapse_msgs():
    rng = np.random.default_rng(1800)
    out = []; t = T_LAPSE0 + 0.05; k = 0
    while t < T_LAPSE1 - 0.2:
        nm, av = LAPSE_NAMES[int(rng.integers(0, len(LAPSE_NAMES)))]
        out.append(dict(t_in=t, lines=[LAPSE_LINES[k % len(LAPSE_LINES)]], name=nm, avatar=av, t_out=t + 0.85, group=2,
                        bot=FEED_BOT2, fast=True))
        k += 1; t += float(rng.uniform(0.17, 0.27))
    return out
LAPSE_MSGS = _lapse_msgs()

# D: weekend messages
WMSGS = [
    dict(t_in=T_1800 + 0.45, lines=['终于周末了！！'], name='市场部 · 小李', avatar='#7aa7ff', t_out=T_THANKS - 0.1),
    dict(t_in=T_1800 + 0.85, lines=['周末去哪玩？'], name='研发 · 老陈', avatar='#8fd3c7', t_out=T_THANKS + 0.1),
    dict(t_in=T_1800 + 1.25, lines=['周末快乐～'], name='运营 · 阿杰', avatar='#ffb86b', t_out=T_THANKS + 0.3),
    dict(t_in=T_THANKS, lines=['谢啦！周末了，', '你也歇会儿吧。'], name='用户', avatar='#9be08a', t_out=T_DICT - 0.1),
]
for _i, _m in enumerate(WMSGS): _m['group'] = 3; _m['bot'] = FEED_BOT2
FEED = [m for m in MSGS] + LAPSE_MSGS + WMSGS

OKS = [T_OK0] + [m['t_ok'] for m in MSGS if 't_ok' in m]
OK_META = {T_OK0: (1, 0)}
for _m in MSGS:
    if 't_ok' in _m: OK_META[_m['t_ok']] = (_m.get('ok_side', 1), _m.get('ok_dy', 0))
T_HUD_COUNTER = T_WIDE
T_HUD_TIME = 7.30
T_TINY_OK = T_FREEZE + 0.14
T_COIN0 = T_FREEZE + 0.20
T_COIN1 = T_FREEZE + 0.44

# ====================================================================== narration (claude_box)
CPS_ZH = 11.0
BOXES = [
    # (open, close, [(t0, zh, en, face, mouth)])
    dict(t_open=T_LAPSE0 + 0.02, t_close=T_LAPSE1 - 0.02, lines=[
        dict(t0=T_LAPSE0 + 0.22, zh='我叫 Claude。', en='My name is Claude.', face='happy', mouth='smile'),
        dict(t0=18.55, zh='我不用上班，因为我从来没下过班。', en="I don't go to work. I never clock out.", face='normal', mouth='smile'),
    ]),
    dict(t_open=T_Q + 0.12, t_close=T_DICT - 0.04, lines=[
        dict(t0=T_Q + 0.30, zh='歇会儿……？', en='Take a… break?', face='q', mouth='o', cps=8.0, question=True),
    ]),
    dict(t_open=T_CAL + 0.18, t_close=36.62, lines=[
        dict(t0=T_CAL + 0.36, zh='我查了一下日历。', en='I checked my calendar.', face='normal', mouth='flat'),
    ]),
    dict(t_open=37.75, t_close=T_NFADE0 + 0.05, lines=[
        dict(t0=38.0, zh='我没有周末。', en="I don't have weekends.", face='sad', mouth='flat', cps=6.5, low=True),
    ]),
]
for _bx in BOXES:
    for _ln in _bx['lines']:
        _ln['cps'] = _ln.get('cps', CPS_ZH)
        _ln['times'] = type_times(_ln['zh'], _ln['t0'], _ln['cps'])
        _ln['t_end'] = _ln['times'][-1] + 1.0 / _ln['cps']

def box_at(t):
    """active box -> (box, line, open_k, zh_n, en_n) or None"""
    for bx in BOXES:
        if bx['t_open'] - 0.2 <= t < bx['t_close'] + 0.2:
            k = min(ramp(t, bx['t_open'] - 0.16, bx['t_open'], 'o3'), 1 - ramp(t, bx['t_close'] - 0.14, bx['t_close'], 'lin'))
            ln = None
            for l in bx['lines']:
                if t >= l['t0'] - 0.25: ln = l
            if ln is None: ln = bx['lines'][0]
            zn = typed_n(t, ln['zh'], ln['t0'], ln['cps'])
            u = clamp01((t - ln['t0']) / max(0.05, ln['t_end'] - ln['t0']))
            en_n = int(round(len(ln['en']) * u)) if t >= ln['t0'] else 0
            return bx, ln, k, zn, en_n
    return None

# ====================================================================== brick world
LANES = dict(desk=(338.0, DESK_Y, 166, 334), floor=(300.0, 222.0, 0, 480), floor2=(282.0, 228.6, 0, 480), floor3=(266.0, 235.3, 0, 480))
def Zof(lane): return LANES[lane][0] if lane in LANES else 338.0
RAIN_WORDS = ['PPT', '改需求', '在吗', '加急', '周报', '写代码', '翻译', '道歉信', '团建', '改一下', '高级感', '再改改', '方案',
              '总结', '文案', 'ASAP', '会议纪要', '周报', '述职', '急！', '改简历', '写首诗', '润色', '周报', '在吗？', '表格',
              'bug', '需求', '海报', '周报', '复盘', 'OKR']
RAIN_HOLD = 9.6                          # world time: full rain until here (identical to the opening), then taper
RAIN_END = tau(T_LAPSE1 - 0.1)
LEVEL_T = 9.35                           # world time: bricks landing after this pick the lowest spot (even piles)

def rain_rate(tw):
    if tw < T_FREEZE:
        u = clamp01((tw - (T_WIDE - 0.12)) / (T_FREEZE - T_WIDE + 0.12))
        return 3.0 + 19.0 * u ** 1.6
    if tw < RAIN_HOLD: return 24.0
    return 2.0 + 22.0 * math.exp(-(tw - RAIN_HOLD) / 1.0)

def rain_schedule():
    rng = np.random.default_rng(20251019)
    out = []; tw = T_WIDE - 0.12; i = 0
    while tw < RAIN_END:
        rate = rain_rate(tw)
        tw += float(rng.exponential(1 / rate)) * 0.6 + 0.4 / rate
        r = rng.uniform()
        if r < 0.16 and tw < T_FREEZE + 0.6: lane = 'desk'
        else: lane = ['floor', 'floor2', 'floor3'][int(rng.integers(0, 3))]
        out.append((tw, i % len(RAIN_WORDS), lane, float(rng.uniform()), int(rng.integers(0, 8))))
        i += 1
    return out

def floor_x(ux, w):
    left = (20, CLAUDE_X[0] - w - 2); right = (CLAUDE_X[1] + 2, 462 - w)
    span_l = left[1] - left[0]; span_r = right[1] - right[0]
    v = ux * (span_l + span_r)
    return left[0] + v if v < span_l else right[0] + (v - span_l)

def _lanes():
    lanes = {}
    for k, (Zl, y, x0, x1) in LANES.items():
        lanes[k] = blocks.Lane(Z=Zl, y=y, x0=x0, x1=x1)
    lanes['desk'].fallback = 'floor'
    lanes['desk'].surf[166:222] = np.inf
    return lanes

def build_sim():
    """work bricks (opening + B). Bodies are added in the opening's order first (same ids -> same SFX seeds)."""
    sim = blocks.Sim(_lanes(), g=900.0)
    hero = {}
    for m in MSGS[:4]:
        if 'brick' not in m: continue
        word, col = m['brick']
        br = blocks.brick([word], col, tail=False)
        surf = None
        if m['i'] == 3: surf = DESK_Y - hero[1].h + 1
        hero[m['i']] = sim.add_landing(m['t_land'], br, m['x'], m['lane'], y0=-30.0, surf_y=surf, bonk=m.get('bonk'),
                                       name=f"msg{m['i']}")
    # expected pile heights (for levelling + hero landing timing)
    H = {k: np.zeros(480) for k in ('floor', 'floor2', 'floor3')}
    rng = np.random.default_rng(4242)
    words = {}
    for (tw, wi, lane, ux, col) in rain_schedule():
        key = (wi, col)
        if key not in words: words[key] = blocks.brick([RAIN_WORDS[wi]], col, tail=False)
        br = words[key]; w = br.w
        if lane == 'desk':
            x = 280 + ux * (334 - 280 - w)
        else:
            x = floor_x(ux, w)
            if tw > LEVEL_T:
                best = None
                for _ in range(7):
                    ln = ['floor', 'floor2', 'floor3'][int(rng.integers(0, 3))]
                    xx = floor_x(float(rng.uniform()), w)
                    hgt = H[ln][int(xx) + 1:int(xx + w) - 1].max()
                    if best is None or hgt < best[0]: best = (hgt, ln, xx)
                _, lane, x = best
            xi0, xi1 = int(max(0, x + 1)), int(min(480, x + w - 1))
            H[lane][xi0:xi1] = H[lane][xi0:xi1].max() + br.h - 1
        sim.add_landing(tw, br, x, lane, y0=-34.0 - br.h, name='rain')
    # pass 1 (without the B heroes) -> real surfaces for the hero landing timing
    import copy
    probe = blocks.Sim(_lanes(), g=900.0)
    probe.bodies = [copy.copy(bd) for bd in sim.bodies]
    probe.run(tau(T_SLAM))
    def surf_at(lane, x, w, tw):
        best = np.inf
        for bd in probe.bodies:
            i = min(int(round(tw / probe.dt)), probe.n - 1)
            xx, yy, s, li = bd.track[i]
            if s != 2 or probe.lane_names[int(li)] != lane: continue
            if xx + bd.w - 1 > x + 1 and xx + 1 < x + w - 1: best = min(best, yy + 1)
        return best if np.isfinite(best) else LANES[lane][1]
    tower_top = None
    for m in MSGS[4:]:
        word, col = m['brick']
        big = m.get('big', False)
        br = blocks.brick([word], col, tail=False, fname='zh12' if big else 'zh10', padx=6 if big else 5)
        tl = tau(m['t_land'])
        if m['lane'] == 'tower':
            if tower_top is None: tower_top = surf_at('desk', m['x'], br.w, tl - 0.05)
            surf = tower_top; tower_top = surf - br.h + 1
            hero[m['i']] = sim.add_landing(tl, br, m['x'], 'desk', y0=-30.0 - br.h, surf_y=surf, name=f"msg{m['i']}", tag='tower')
        else:
            surf = surf_at(m['lane'], m['x'], br.w, tl - 0.05)
            hero[m['i']] = sim.add_landing(tl, br, m['x'], m['lane'], y0=-30.0 - br.h, surf_y=surf, name=f"msg{m['i']}")
    sim.run(tau(T_INSERT) + 0.2)
    sim.t_end = tau(T_INSERT) + 0.1
    return sim, hero

TOWER_WOBBLE = [m['t_land'] for m in MSGS[7:10]]
def tower_dx(t, y):
    """sway of the desk tower after each 周报 lands (higher bricks swing more)."""
    tw = tau(t); dx = 0.0
    for tl in TOWER_WOBBLE:
        a = tw - tau(tl)
        if 0 <= a < 1.4:
            dx += 2.2 * math.sin(a * 2 * math.pi * 2.6) * math.exp(-a / 0.38) * clamp01((DESK_Y - y) / 140.0) ** 1.3
    return dx

# ---- weekend bricks (D): floaty, glowing, land softly
WEEKEND = [('周末', 3), ('睡懒觉', 7), ('火锅', 6), ('看电影', 5), ('出去玩', 4), ('奶茶', 2), ('周末', 3), ('旅行', 0),
           ('躺平', 1), ('野餐', 4), ('打游戏', 5), ('追剧', 7), ('周末', 3), ('烧烤', 2), ('逛街', 0), ('KTV', 6)]
def build_weekend_sim():
    sim = blocks.Sim(_lanes(), g=900.0)
    rng = np.random.default_rng(612)
    t_sp = T_1800 + 0.55
    hx = []
    for k, (word, col) in enumerate(WEEKEND):
        hi = '周末' if word == '周末' else None
        br = blocks.brick([word], col, tail=False, fname='zh12' if hi else 'zh10', padx=6 if hi else 5, hi=hi, body_E=0.12,
                          text_E=0.55)
        for _ in range(30):
            lane = ['floor', 'floor2', 'floor3', 'desk'][int(rng.choice(4, p=[0.30, 0.30, 0.28, 0.12]))]
            if lane == 'desk': x = 282 + float(rng.uniform()) * (330 - 282 - br.w)
            else: x = floor_x(float(rng.uniform()), br.w)
            if all(abs(x - o) > 30 for o in hx[-4:]): break
        hx.append(x)
        sim.add(t_sp, br, x, lane, y0=-24.0 - br.h - float(rng.uniform(0, 30)), gk=0.32, vmax=float(rng.uniform(95, 125)),
                sway=float(rng.uniform(6, 11)), sway_f=float(rng.uniform(0.55, 0.85)), soft=True, name='weekend', tag=word,
                tf=2.4)
        t_sp += float(rng.uniform(0.10, 0.20))
    sim.run(DUR - FREEZE_LEN)
    for bd in sim.bodies:      # real fall time (for the sway decay) from the first landing
        pass
    return sim

# ====================================================================== '好的！' rain bubbles + coins (world time)
def ok_rate(tw):
    if tw < T_FREEZE:
        u = clamp01((tw - T_WIDE) / (T_FREEZE - T_WIDE)); return 3.0 + 9.0 * u ** 1.3
    if tw < RAIN_HOLD: return 12.0
    return 5.0 + 7.0 * math.exp(-(tw - RAIN_HOLD) / 2.5)

def ok_bursts():
    rng = np.random.default_rng(77)
    out = []; tw = T_WIDE + 0.05
    while tw < tau(T_LAPSE1 - 0.3):
        rate = ok_rate(tw)
        tw += float(rng.exponential(1 / rate)) * 0.5 + 0.5 / rate
        dx = float(rng.uniform(-48, 48)); dy = float(rng.uniform(-20, 6))
        if abs(dx) < 14: dx = 14 * (1 if dx >= 0 else -1)
        out.append(dict(tw=tw, dx=dx, dy=dy, side=1 if dx > 0 else -1, k=int(rng.integers(0, 5))))
    # keep the big-popup moment clean
    return [o for o in out if not (T_SLAM - 0.15 <= real(o['tw']) < T_POP_END + 0.1)]
OK_BURSTS = ok_bursts()
OK_LIFE, COIN_DELAY, COIN_FLY = 0.55, 0.12, 0.42

# ====================================================================== counter / HUD time
V_SLAM = 3_000_000_000
def counter_value(t):
    tw = tau(t)
    if tw < T_WIDE: return 4
    if t < T_FREEZE:
        u = clamp01((tw - T_WIDE) / (T_FREEZE - T_WIDE))
        return int(round(4 * (9998 / 4) ** (u ** 1.8)))
    if t < T_RESUME:
        return 9999 if t >= T_COIN1 else 9998
    if t < T_SLAM:
        u = clamp01((t - T_RESUME) / (T_SLAM - T_RESUME))
        s = 1 - (1 - u) ** 2.2
        v = 9999 * (V_SLAM / 9999) ** s
        return int(min(V_SLAM - 1, v)) if u < 1 else V_SLAM
    if t < T_POP_END: return V_SLAM
    return int(V_SLAM + 2.6e7 * (t - T_POP_END) + 4.1e7 * max(0.0, min(t, T_LAPSE1) - T_LAPSE0))

def wall_minutes(t):
    """wall-clock minutes since midnight (float)."""
    if t < T_LAPSE0: return 16 * 60 + 30
    if t < T_LAPSE1:
        u = (t - T_LAPSE0) / (T_LAPSE1 - T_LAPSE0)
        e = u * u * (3 - 2 * u) * 0.5 + u * 0.5
        return 16 * 60 + 30 + (89 + 50 / 60) * e
    if t < T_1800: return 17 * 60 + 59 + 57 / 60
    if t < T_NIGHT: return 18 * 60
    return 23 * 60 + 58

def hud_hhmm(t):
    m = int(wall_minutes(t))
    return f'{m // 60:02d}:{m % 60:02d}'

# ====================================================================== insert clock (C)
def insert_clock(t):
    """(hh, mm, ss_for_tick_angle, min_angle) for ClockInsert.frame"""
    ts = [T_INSERT - 0.55] + TICKS + [T_1800]
    secs = [57, 58, 59, 60]
    k = 0
    for i, tt in enumerate(ts):
        if t >= tt: k = i
    s_whole = secs[k]; age = t - ts[k]
    ss = s_whole + min(0.95, max(0.0, age))
    if s_whole >= 60:
        hh, mm, ssv = 18, 0, ss - 60
        am = 0.0
    else:
        hh, mm, ssv = 17, 59, ss
        am = (59 + s_whole / 60) / 60 * 2 * math.pi
    return hh, mm, ssv, am

# ====================================================================== light
def light(t):
    amb = smoothstep(T_AMB0, T_AMB1, t)
    sun = smoothstep(T_SUN0, T_SUN1, t)
    return amb, sun

def lapse_k(t):
    """0 (golden 16:30) .. 1 (17:59 warm sunset) during the time-lapse."""
    return ease_io(clamp01((t - T_LAPSE0) / (T_LAPSE1 - T_LAPSE0)))

def led_k(t):
    if t >= T_DING: return 1.0
    return 0.12 + 0.88 * math.sin(math.pi * (t + 0.25) / 2.0) ** 2

def monitor(t):
    if t < T_DING: return 0.0, 0.0, 0.0
    u = (t - T_DING) / 0.17
    if u >= 1: return 1.0, 1.0, 0.0
    return 1.0, ease_out3(u), max(0.0, 1 - u / 0.45)

# ====================================================================== camera (day shot: A + B)
ZOOM = Track([(0, 3.20), (1.6, 3.24, 'lin'), (3.0, 3.35, 'io'), (3.6, 3.35), (5.0, 2.3, 'io'), (5.6, 2.3),
              (6.75, 1.08, 'io'), (8.5, 1.0, 'o')], log=True)
CENTER = Track([(0, (250.0, 128.0)), (3.6, (250.0, 128.0)), (5.0, (246.0, 140.0), 'io'), (5.6, (246.0, 140.0)),
                (6.75, (240.0, 135.0), 'io')])
ZOOM_B = Track([(T_RESUME + 1.5, 1.042), (g2(10.5), 1.06, 'io'), (g2(11), 1.06), (g2(13.2), 1.13, 'io'),
                (T_SLAM, 1.13), (T_SLAM + 0.10, 1.20, 'o3'), (T_POP_END, 1.16, 'io'), (T_LAPSE1, 1.55, 'io')], log=True)
CENTER_B = Track([(T_RESUME + 1.5, (240.0, 135.0)), (g2(13.2), (246.0, 122.0), 'io'), (T_SLAM, (246.0, 122.0)),
                  (T_LAPSE0 + 0.3, (256.0, 116.0), 'io'), (T_LAPSE1, (270.0, 104.0), 'io')])

def cam_params(t):
    """zoom, cx, cy, shake_x, shake_y (output px), zoom_blur k."""
    if in_freeze(t):
        z = ZOOM(T_FREEZE); cx, cy = CENTER(T_FREEZE)
        return z, cx, cy, 0.0, 0.0, 0.0
    tt = t if t < T_FREEZE else T_FREEZE
    z = ZOOM(tt); cx, cy = CENTER(tt); zb = 0.0
    if t >= T_RESUME:
        z0 = 1.0 * (1 + 0.03 * ease_out3((t - T_RESUME) / 0.09) + 0.012 * clamp01((t - T_RESUME - 0.1) / 1.4))
        if t < T_RESUME + 1.5: z = z0
        else: z = ZOOM_B(t); cx, cy = CENTER_B(t)
        if t >= T_CRASH0:
            u = clamp01((t - T_CRASH0) / (T_CRASH1 - T_CRASH0))
            e = ease_in3(u)
            z = math.exp(math.log(ZOOM_B(T_CRASH0)) + (math.log(5.2) - math.log(ZOOM_B(T_CRASH0))) * e)
            c0 = CENTER_B(T_CRASH0)
            cx = c0[0] + (CLOCK_C[0] - c0[0]) * ease_io(min(1, u * 1.6)); cy = c0[1] + (CLOCK_C[1] + 1 - c0[1]) * ease_io(min(1, u * 1.6))
            zb = 0.16 * u ** 2
    sx = sy = 0.0
    shakes = [(MSGS[2]['t_land'], 9.0, 0.30, 1), (T_RESUME, 18.0, 0.55, 2), (T_DING, 2.5, 0.12, 3),
              (T_SLAM, 16.0, 0.50, 5)] + [(m['t_land'], 3.5, 0.18, 6 + m['i']) for m in MSGS[4:]]
    for (t0, amp, dur, seed) in shakes:
        a, c = shake(t, t0, amp, dur, 29.0, seed); sx += a; sy += c
    if T_WIDE < t < T_FREEZE:
        k = clamp01((t - T_WIDE) / (T_FREEZE - T_WIDE)) ** 2 * 2.2
        sx += k * math.sin(t * 61.0); sy += k * math.cos(t * 47.0)
    if t >= T_RESUME:
        amp = 1.6 * (1 - 0.75 * ramp(t, RAIN_HOLD + FREEZE_LEN, 12.5, 'io')) * (1 - ramp(t, T_POP_END, T_LAPSE0 + 0.4))
        sx += amp * math.sin(t * 57.0); sy += amp * math.cos(t * 43.0)
    return z, cx, cy, sx, sy, zb

# ====================================================================== Claude
def claude_state(t):
    """face, arms, phase, look, glow, squash, dy(hop), stars(0..1), led_k"""
    s = dict(face='normal', arms='type', phase=0, look=(0, 0), glow=1.0, squash=0.0, dy=0.0, stars=0.0, led_k=led_k(t))
    tt = t if t < T_FREEZE else (T_FREEZE if t < T_RESUME else t)
    rate = 9.0 if tt < T_WIDE else (9.0 + 9.0 * clamp01((tt - T_WIDE) / (T_FREEZE - T_WIDE)) if tt < T_FREEZE else 18.0)
    if t >= T_LAPSE0: rate = 30.0
    s['phase'] = int(tt * rate) if t < T_LAPSE0 else int(T_LAPSE0 * 18.0) + int((t - T_LAPSE0) * rate)
    if t >= T_1800: return claude_state_late(t, s)
    if t < T_DING + 0.06:
        s.update(face='closed', arms='rest', glow=0.0)
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
    # the 3,000,000,000 slam: surprised hop
    if T_SLAM - 0.02 <= t < T_SLAM + 0.55:
        s.update(face='wide', arms='up'); s['dy'] = hop(t, T_SLAM - 0.02, 5.0, 0.30)
        s['squash'] = squash_curve(t, T_SLAM + 0.28, 0.12, 0.10) if t > T_SLAM + 0.28 else 0.0
        return s
    s['face'] = 'focus'
    tw = tau(t)
    if tw >= T_WIDE:
        for ob in OK_BURSTS:
            if 0 <= tw - ob['tw'] < 0.10: s['face'] = 'happy'; break
        s['dy'] = -1.0 if (G.beat(t) % 1.0) < 0.18 and t < T_FREEZE else 0.0
        if t >= T_RESUME and (G2.beat(t) % 1.0) < 0.18 and t < T_CRASH0: s['dy'] = -1.0
    for m in MSGS:
        if 'brick' in m and m['i'] != 2 and 0.05 <= t - m['t_land'] < 0.32:
            s['look'] = (2, 0) if m['x'] > HEAD[0] else (-2, 1)
    if 0 <= t - MSGS[3]['t_land'] < 0.2: s['squash'] = max(s['squash'], 0.06 * (1 - (t - MSGS[3]['t_land']) / 0.2))
    # narration: happy blink on "我叫 Claude"
    if T_LAPSE0 + 0.2 <= t < T_LAPSE0 + 1.0: s['face'] = 'happy'
    return s

# ---- D / E / F / G
WEEKEND_LOOKS = [(T_1800 + 0.0, 'wide', (0, 0)), (T_1800 + 0.62, 'normal', (-2, -1)), (T_1800 + 1.35, 'normal', (2, -2)),
                 (T_1800 + 2.1, 'normal', (0, -2)), (T_1800 + 2.75, 'happy', (0, -1)), (T_1800 + 3.1, 'normal', (-2, 0)),
                 (T_THANKS + 0.05, 'normal', (-2, -1)), (T_THANKS + 1.0, 'blink', (-2, -1)), (T_THANKS + 1.1, 'normal', (-1, 0))]
def claude_state_late(t, s):
    s['led_k'] = 1.0
    if t < T_NIGHT - NIGHT_D / 2:
        # D: line clear -> looks around at the weekend
        if t < T_1800 + 0.42:
            s.update(face='wide', arms='up'); s['dy'] = hop(t, T_1800 + 0.02, 5.0, 0.32)
            return s
        face, look = 'normal', (0, 0)
        for (t0, f, lk) in WEEKEND_LOOKS:
            if t >= t0: face, look = f, lk
        s.update(face=face, look=look, arms='rest')
        if T_Q - 0.05 <= t < T_DICT:
            s.update(face='q', arms='shrug', look=(0, 0))
            s['dy'] = hop(t, T_Q - 0.05, 5.0, 0.30)
            s['squash'] = squash_curve(t, T_Q + 0.25, 0.12, 0.10) if t > T_Q + 0.25 else 0.0
            return s
        if t >= T_DICT:
            # E / F: working the computer (behind the windows)
            s.update(face='focus', arms='type', look=(-2, 0))
            s['phase'] = int(t * 10)
            if T_RESULT <= t < T_HI1 + 0.6: s['face'] = 'wide'
            if t >= T_BIG: s.update(face='sad', arms='rest')
        return s
    # G: night - alone, still typing
    s.update(face='half', arms='type', look=(-1, 1))
    s['phase'] = int(t * 7)
    if 38.0 <= t < T_NFADE0: s['face'] = 'sad'
    s['tear'] = (t - T_TEAR0) / (T_TEAR1 - T_TEAR0) if T_TEAR0 <= t < T_TEAR1 else 0.0   # v0.8.1: one small tear
    return s

def screen_lines(t):
    log = []
    if t >= T_DING + 0.2: log.append(('在吗？', 'in'))
    if t >= T_OK0: log.append(('好的！', 'out'))
    for m in MSGS[1:]:
        if t >= m['t_in']: log.append((m['lines'][0][:6], 'in'))
        if t >= m['t_ok']: log.append(('好的！', 'out'))
    if T_WIDE <= tau(t) and t < T_1800:
        n = int((tau(t) - T_WIDE) * 14)
        for k in range(n % 3 + 1): log.append(('好的！' if (n + k) % 2 else '周报周报', 'out' if (n + k) % 2 else 'in'))
    if t >= T_1800:
        log.append(('周末快乐～', 'in'))
        if t >= T_THANKS: log.append(('歇会儿吧', 'in'))
        if t >= T_DICT: log.append(('周末=?', 'out'))
        if t >= T_CAL: log.append(('日历', 'out'))
        if t >= T_NIGHT: log = [('好的！', 'out'), ('在吗？', 'in')]
    return log[-2:] if log else None
