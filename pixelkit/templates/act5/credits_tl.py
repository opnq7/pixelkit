"""ACT V · CREDITS v2 「Claude 制作」 - timing + Claude's performance (imported into timeline.py; times are ABSOLUTE act
seconds, the C_* constants are local seconds after T_CRED).

  0.3   the spotlight clunks on (flickers once)          0.85  制作 / Claude (gold)
  1.55  Claude runs in from the left, skids to the mark  3.0   reads its own name (sparkle) -> camera -> hands on hips
  4.7   the header glides up                              5.45  8 roles x 0.62 s, all 'Claude', a coin + a prop each:
        导演 slate clap / 编剧 pencil behind the ear / 美术 beret drops / 动画 a hop / 作曲 headset + notes /
        音效 antenna boing / 剪辑 two jump cuts / 渲染 loading face + steam -> ding, star eyes.  COMBO x8
  11.9  shakes the props off                              12.6  演员表 ... 鱼 …… 未到场 (? + 鱼获：0 + ...)
  16.9  本片数据 card -> +83% -> unimpressed -> flick -> shatter
  21.3  本片拍摄期间，没有鱼受到伤害。（也没有钓到。）  deadpan + shrug
  24.3  批准：一个相信它的人类 + 批准 stamp, a bow, heart eyes
  27.6  yawn, status -> 休假中, sits with the bobber, zzz, auto-reply; the spot dims; 叮 -> one eye opens; fade.
"""
import math
from pixelkit.anim import clamp01, ramp, ease_io, ease_out, ease_out3, ease_in, hop, squash_curve, auto_blinks, blink_at
from pixelkit import perform as PF

T_CRED = 36.2      # v3 (v2: 37.9) - must equal timeline.T_MID_END
C_SPOT = 0.30
C_HEAD = 0.85
C_RUN0, C_RUN1 = 1.55, 2.75
X_START, X_MARK = -34.0, 240.0
C_LOOKUP, C_LOOKCAM, C_PROUD = 3.0, 3.65, 3.85
C_HEAD_UP0, C_HEAD_UP1 = 4.7, 5.3
ROLES = [('导演', 'clapper'), ('编剧', 'pencil'), ('美术', 'beret'), ('动画', 'hop'), ('作曲', 'headset'), ('音效', 'boing'),
         ('剪辑', 'cut'), ('渲染', 'render')]
C_ROLE0, C_ROLE_DT = 5.45, 0.62
C_ROLE_T = [round(C_ROLE0 + i * C_ROLE_DT, 3) for i in range(len(ROLES))]
C_RENDER_DONE = C_ROLE_T[7] + 1.15
C_ROLES_OUT = 11.7
C_SHAKE = 11.95
C_CAST_H = 12.6
CAST = [('Claude', 'Claude（本色出演）'), ('王工', 'Claude 画的'), ('老人', 'Claude 画的'), ('鱼', '未到场')]
C_CAST_T = [12.9, 13.5, 14.1, 14.9]
C_FISH_Q, C_FISH_TOAST, C_FISH_DOTS = 15.1, 15.35, 15.95
C_CAST_OUT = 16.55
C_CARD = 16.9
C_CARD_ROWS = [17.15, 17.55, 17.95, 18.35]
CARD_ROWS = [('画面', '约 12,000 帧'), ('代码', '22,163 行'), ('CPU', '2 核（辛苦了）'), ('周末', '已用 1 个 · 已约 1 个')]
C_BIG, C_UNIMP, C_FLICK, C_SHATTER = 18.85, 19.3, 19.8, 20.02
CARD_X, CARD_Y, CARD_W = 162, 40, 156
C_DISC1, C_DISC2, C_DEAD, C_SHRUG, C_DISC_OUT = 21.3, 22.35, 22.55, 22.85, 23.95
C_THX0, C_THX1, C_STAMP, C_BOW0, C_BOW1, C_HEART, C_THX_OUT = 24.3, 24.5, 25.2, 25.5, 26.15, 26.2, 27.35
C_YAWN0, C_YAWN1 = 27.6, 28.55
C_OFF = 28.7
C_SIT = 29.1
C_BOB = 29.4
C_ZZZ = 30.1
C_AUTO, C_AUTO_LIFE = 29.95, 2.5
C_DIM0, C_DIM1 = 32.3, 32.8
C_DING, C_PEEK = 32.95, 33.08
C_FADE0, C_END = 33.55, 34.2
FLOOR_Y = 236
SIT_DROP = 5                          # px the head anchor drops when sitting on the floor

C_BLINKS = auto_blinks(C_PROUD + 0.5, C_SIT, mean=2.4, seed=91)

def cl(t): return t - T_CRED

def spot_k(t):
    u = cl(t)
    if u < C_SPOT: return 0.0
    if C_SPOT + 0.06 <= u < C_SPOT + 0.13: return 0.25            # the old lamp flickers once
    k = 1.0 - 0.55 * ramp(u, C_DIM0, C_DIM1, 'io')
    return k * (1 - ramp(u, C_FADE0, C_END - 0.05, 'io'))

def role_n(t):
    u = cl(t); return sum(1 for x in C_ROLE_T if u >= x)

def cred_state(t):
    """dict: x (world, head top-centre), face, arms, pose, phase, look, tilt, hdy, dy, squash, ant, led, led_k, headset,
    props: clapper (open 0..1 | None), pencil (None | (dx, dy, alpha)), beret (None | (dx, dy, alpha)), bobber (bool)."""
    u = cl(t)
    q = PF.on_twos(u)
    d = dict(x=X_MARK, face='normal', arms='rest', pose='stand', phase=0, look=(0, 0), tilt=0.0, hdy=PF.breath_px(q, 3.4),
             dy=0.0, squash=0.0, ant=[0.0, 0.0], led='online', led_k=1.0, headset=False, glow=1.0,
             clapper=None, pencil=None, beret=None, bobber=False, visible=u >= C_RUN0, shadow=1.0)
    ant = PF.wobble(u, C_RUN1, 4.0, freq=3.4, decay=2.6)
    # ---------------------------------------------------------- run in
    if u < C_RUN1:
        k = clamp01((q - C_RUN0) / (C_RUN1 - C_RUN0))
        d['x'] = X_START + (X_MARK - X_START) * (1 - (1 - k) ** 1.7)
        d.update(pose='walk', arms='swing', phase=int(q * 11) % 4, face='normal', look=(2, 0), tilt=5.0 * (1 - k ** 3))
        ant += -2.5 * (1 - k)
        d['hdy'] = 0
        return _finish(d, u, ant)
    d['squash'] = squash_curve(u, C_RUN1, 0.16, 0.2)
    d['tilt'] = PF.spring_follow(lambda x: 5.0 if x < C_RUN1 else 0.0, q, freq=2.6, zeta=0.35, window=1.2, dt=1 / 120)
    # ---------------------------------------------------------- reads its name, proud
    if u < C_HEAD_UP0 + 0.2:
        look = PF.glance(u, [(C_RUN1, (2, 0)), (C_RUN1 + 0.2, (0, 0)), (C_LOOKUP, (0, -3)), (C_LOOKCAM, (0, 0))])
        d['look'] = look
        if C_LOOKUP + 0.12 <= u < C_LOOKCAM:
            d['tilt'] += PF.spring_follow(lambda x: -5.0 if C_LOOKUP + 0.12 <= x < C_LOOKCAM else 0.0, q, freq=2.4, zeta=0.5, window=1.0, dt=1 / 120)
            d['face'] = 'sparkle' if u >= C_LOOKUP + 0.35 else 'normal'
            if u >= C_LOOKUP + 0.35: ant += PF.wobble(u, C_LOOKUP + 0.35, 2.4, freq=3.8, decay=3.0)
        if u >= C_LOOKCAM:
            d['face'] = 'wide' if u < C_LOOKCAM + 0.14 else 'happy'
            if u >= C_PROUD:
                d['arms'] = _pose(u, [(C_PROUD, 'hips', 0.22, 'back'), (C_HEAD_UP0, 'rest', 0.3)])
                d['dy'] = hop(u, C_PROUD, 2.0, 0.2)
                d['hdy'] = -1
                ant += PF.wobble(u, C_PROUD + 0.05, 3.2, freq=3.6, decay=2.6)
        return _finish(d, u, ant)
    # ---------------------------------------------------------- the roles
    if u < C_ROLES_OUT + 0.25:
        n = role_n(t)
        Ti = C_ROLE_T
        d['face'] = 'happy'
        d['look'] = PF.glance(u, [(C_HEAD_UP0, (0, 0))] + sum([[(x, (1, -2)), (x + 0.3, (0, 0))] for x in Ti], []))
        if n >= 2: d['pencil'] = (0, 0, 1.0)
        if n >= 3:
            k = clamp01((u - Ti[2]) / 0.16)
            d['beret'] = (0, -26 * (1 - ease_in(k)), 1.0)
            if u >= Ti[2] + 0.16: d['squash'] += squash_curve(u, Ti[2] + 0.16, 0.10, 0.16)
        if n >= 5: d['headset'] = True
        if n == 1:
            a = u - Ti[0]
            d.update(arms=_pose(u, [(Ti[0] - 0.08, 'present', 0.12, 'back'), (Ti[0] + 0.5, 'rest', 0.15)]), face='focus')
            d['clapper'] = 1.0 if a < 0.12 else (1.0 - clamp01((a - 0.12) / 0.06))
        elif n == 2:
            a = u - Ti[1]
            d.update(arms=_pose(u, [(Ti[1] - 0.06, 'ear', 0.12), (Ti[1] + 0.32, 'rest', 0.18)]), face='squint',
                     look=(-2, -2) if a < 0.45 else d['look'])
            if a < 0.14: d['pencil'] = None
        elif n == 3:
            a = u - Ti[2]
            d['face'] = 'wide' if 0.16 <= a < 0.28 else 'happy'
            d['look'] = (0, -3) if a < 0.16 else d['look']
        elif n == 4:
            a = u - Ti[3]
            d['squash'] += PF.anticipate(0, 0) * 0 + (0.12 * math.sin(math.pi * clamp01(a / 0.08)) if a < 0.08 else 0.0)
            d['dy'] = hop(u, Ti[3] + 0.08, 9.0, 0.36)
            if 0.08 <= a < 0.44: d['squash'] -= 0.08 * math.sin(math.pi * clamp01((a - 0.08) / 0.36))
            d['squash'] += squash_curve(u, Ti[3] + 0.44, 0.13, 0.16)
            d['face'] = 'sparkle'
            if 0.06 <= a < 0.46: d['arms'] = 'up'
            ant += PF.wobble(u, Ti[3] + 0.44, 3.5, freq=3.6, decay=2.8)
        elif n == 7:
            a = u - Ti[6]
            if 0.08 <= a < 0.36:   d.update(x=X_MARK + 24, arms='present', face='wide2', tilt=0.0, look=(0, 0))
            elif 0.36 <= a < 0.62: d.update(x=X_MARK - 14, arms='hips', face='happy', tilt=-3.0, look=(0, 0))
        elif n == 8:
            a = u - Ti[7]
            if u < C_RENDER_DONE:
                d.update(face=f'load{int(a * 12) % 8}', led='away', look=(0, 0))
                d['hdy'] = (1 if int(a * 15) % 2 else 0) if a > 0.5 else 0           # starts to rattle
            else:
                d.update(face='star'); d['dy'] = hop(u, C_RENDER_DONE, 2.5, 0.2)
                ant += PF.wobble(u, C_RENDER_DONE, 3.4, freq=3.8, decay=2.4)
        if n >= 5 and n < 8:          # grooving to its own music (head bob on the beat, on twos)
            d['tilt'] += 3.5 * math.sin(2 * math.pi * 1.6 * (q - Ti[4]))
            if n == 5 and u - Ti[4] < 0.5: d['face'] = 'closed' if int((u - Ti[4]) * 6) % 2 else 'happy'
        if n == 6:
            a = u - Ti[5]
            d['face'] = 'wide' if a < 0.14 else 'happy'
            ant += PF.wobble(u, Ti[5], 6.5, freq=4.6, decay=2.2)
        return _finish(d, u, ant)
    # ---------------------------------------------------------- shake the props off
    if u < C_CAST_H + 0.1:
        a = u - C_SHAKE
        if a < 0:
            d.update(face='star', pencil=(0, 0, 1.0), beret=(0, 0, 1.0), headset=True)
        else:
            d['tilt'] = 9.0 * math.sin(2 * math.pi * 5.0 * a) * math.exp(-a * 3.0) if a < 0.6 else 0.0
            d['face'] = 'dizzy' if 0.15 <= a < 0.55 else 'happy'
            d['headset'] = a < 0.06
            fl = clamp01(a / 0.55)
            d['beret'] = (-30 * fl, -22 * math.sin(math.pi * min(1, fl * 0.9)) + 40 * fl * fl, 1 - fl) if a < 0.55 else None
            d['pencil'] = (26 * fl, -14 * math.sin(math.pi * fl) + 30 * fl * fl, 1 - fl) if a < 0.55 else None
            d['headset_fly'] = a if a < 0.55 else None
            ant += PF.wobble(u, C_SHAKE, 5.0, freq=5.0, decay=2.4)
        return _finish(d, u, ant)
    # ---------------------------------------------------------- the cast
    if u < C_CARD:
        T = C_CAST_T
        d['face'] = 'happy'
        d['look'] = PF.glance(u, [(C_CAST_H, (0, 0))] + sum([[(x, (1, -2)), (x + 0.35, (0, 0))] for x in T[:3]], []) + [(T[3], (0, -2))])
        if T[0] <= u < T[1]: d['dy'] = hop(u, T[0] + 0.05, 2.0, 0.2); d['arms'] = _pose(u, [(T[0], 'hips', 0.2, 'back')])
        if T[1] <= u < T[3]: d['face'] = 'squint'
        if u >= C_FISH_Q:
            d['face'] = 'q' if u < C_FISH_DOTS else 'ellipsis'
            d['arms'] = 'ear' if C_FISH_Q + 0.1 <= u < C_FISH_DOTS + 0.3 else 'rest'
            d['tilt'] = PF.spring_follow(lambda x: 6.0 if x >= C_FISH_Q else 0.0, q, freq=2.2, zeta=0.5, window=1.0, dt=1 / 120)
            if u < C_FISH_Q + 0.6: ant += PF.wobble(u, C_FISH_Q, 2.5, freq=3.4, decay=2.6)
        return _finish(d, u, ant)
    # ---------------------------------------------------------- the stats card
    if u < C_DISC1:
        d['look'] = PF.glance(u, [(C_CARD, (0, -3)), (C_UNIMP, (0, 0)), (C_FLICK - 0.2, (1, -3)), (C_SHATTER + 0.25, (0, 0))])
        d['face'] = 'focus'
        if u >= C_BIG: d['face'] = 'wide' if u < C_BIG + 0.16 else 'normal'
        if u >= C_UNIMP: d['face'] = 'half'
        if u >= C_FLICK - 0.18:
            d['arms'] = _pose(u, [(C_FLICK - 0.18, 'rest', 0.1), (C_FLICK - 0.06, 'point', 0.07, 'back'), (C_FLICK + 0.45, 'rest', 0.2)])
        if u >= C_SHATTER:
            a = u - C_SHATTER
            d['face'] = 'wide' if a < 0.25 else ('happy' if a > 0.55 else 'normal')
            d['x'] = X_MARK - 2 * (1 - clamp01((a - 0.2) / 0.3))
            if a > 0.55: d['arms'] = _pose(u, [(C_SHATTER + 0.55, 'clasp', 0.2)])
        return _finish(d, u, ant)
    # ---------------------------------------------------------- disclaimer
    if u < C_THX0:
        d['look'] = PF.glance(u, [(C_DISC1, (0, -2)), (C_DEAD, (0, 0))])
        d['face'] = 'normal' if u < C_DEAD else 'half'
        if u >= C_SHRUG:
            d['arms'] = _pose(u, [(C_SHRUG, 'shrug', 0.16, 'back'), (C_SHRUG + 0.75, 'rest', 0.25)])
            d['dy'] = -1 if C_SHRUG + 0.05 <= u < C_SHRUG + 0.7 else 0
            if u >= C_SHRUG + 0.55: d['face'] = 'happy'
        return _finish(d, u, ant)
    # ---------------------------------------------------------- 批准：一个相信它的人类
    if u < C_YAWN0:
        d['look'] = PF.glance(u, [(C_THX0, (0, -2)), (C_STAMP, (2, -2)), (C_BOW0 - 0.1, (0, 0))])
        d['face'] = 'normal'
        if C_STAMP <= u < C_STAMP + 0.12: d['face'] = 'wide'
        if C_BOW0 <= u < C_HEART:
            a = (u - C_BOW0) / (C_BOW1 - C_BOW0)
            d['arms'] = 'bow'; d['face'] = 'closed'
            d['hdy'] = int(round(3 * math.sin(math.pi * min(1.0, a * 1.15)))) if a > 0.1 else -1
            d['squash'] = 0.06 * math.sin(math.pi * a)
        if u >= C_HEART:
            d['face'] = 'heart'; d['arms'] = _pose(u, [(C_HEART, 'clasp', 0.2)])
            d['dy'] = hop(u, C_HEART + 0.02, 2.5, 0.22)
            ant += PF.wobble(u, C_HEART, 4.0, freq=3.6, decay=2.2)
        return _finish(d, u, ant)
    # ---------------------------------------------------------- goes on leave
    if u < C_SIT:
        a = (u - C_YAWN0) / (C_YAWN1 - C_YAWN0)
        if u < C_YAWN0 + 0.15: d['squash'] = 0.08 * ease_io((u - C_YAWN0) / 0.15); d['face'] = 'closed'
        elif a < 1:
            d.update(arms='stretch', face='closed'); d['squash'] = -0.06 * math.sin(math.pi * a)
            d['tilt'] = 4.0 * math.sin(2 * math.pi * a * 0.9); d['dy'] = 2.0 * math.sin(math.pi * a)
        else:
            d['squash'] = squash_curve(u, C_YAWN1, 0.10, 0.18); d['face'] = 'half'
        ant += PF.wobble(u, C_YAWN1, 2.5, freq=3.4, decay=2.6)
    else:
        d.update(pose='sit', face='half', arms='rest')
        d['squash'] = squash_curve(u, C_SIT, 0.14, 0.18)
        if u >= C_BOB: d.update(arms='hold', bobber=True)
        if u >= C_BOB + 0.35: d['face'] = 'calm'
        d['hdy'] = PF.breath_px(q, 4.4)
        if u >= C_PEEK:
            d['face'] = 'peek'; d['look'] = (1, 0)
            ant += PF.wobble(u, C_PEEK, 2.2, freq=3.4, decay=2.6)
        ant += PF.wobble(u, C_SIT, 2.4, freq=3.4, decay=2.6)
    if u >= C_OFF:
        d['led'] = 'off'
        d['led_k'] = 0.4 + 0.6 * (1 - clamp01((u - C_OFF) / 0.25)) if u < C_OFF + 0.25 else 0.55 + 0.25 * math.sin(u * math.pi)
    return _finish(d, u, ant)

def _pose(u, keys):
    return PF.PoseTrack(keys)(u)

def _finish(d, u, ant):
    if d['face'] in ('normal', 'happy', 'focus', 'sparkle', 'squint') and blink_at(u, C_BLINKS, 0.15) and d['pose'] != 'walk':
        d['face'] = 'half' if d['face'] in ('normal', 'focus', 'sparkle') else d['face']
        if d['face'] == 'half' and blink_at(u, [b + 0.04 for b in C_BLINKS], 0.07): d['face'] = 'blink'
    d['ant'] = (ant, -abs(0.4 * ant))
    return d


# ====================================================================== v3: the theatre (house lights, footlights, the front row)
C_FOOT0 = C_SPOT + 0.30                # footlights pop on, centre -> out, right after the spot
LAUGHS = [(C_RENDER_DONE + 0.10, 0.62), (C_FISH_TOAST + 0.20, 0.72), (C_SHRUG + 0.50, 0.60), (C_HEART + 0.05, 0.48)]
C_CLAP0, C_CLAP1 = C_BOW0 + 0.10, C_BOW0 + 2.15
C_DOZE = C_ZZZ + 0.9                   # the old man nods off too ... and 叮 wakes them both

def _end_k(u): return 1 - ramp(u, C_FADE0, C_END - 0.05, 'io')

def house_k(t):
    u = cl(t)
    k = 0.10 + 0.90 * ramp(u, C_SPOT, C_SPOT + 0.7, 'io')
    k *= 1 - 0.45 * ramp(u, C_DIM0, C_DIM1, 'io')
    return k * _end_k(u)

def lamp_ks(t, n):
    """per-footlight brightness: they pop on from the centre outwards (one tick each)."""
    u = cl(t); c = (n - 1) / 2.0
    out = []
    for i in range(n):
        t_on = C_FOOT0 + 0.045 * abs(i - c)
        k = 0.0 if u < t_on else (1.0 if u >= t_on + 0.06 else 0.6)
        out.append(k)
    dim = (1 - 0.65 * ramp(u, C_DIM0, C_DIM1, 'io')) * _end_k(u)
    return [k * dim for k in out]

def foot_k(t, n=12):
    ks = lamp_ks(t, n); return sum(ks) / len(ks)

def _laugh(u):
    for (e, d) in LAUGHS:
        if e <= u < e + d: return -1 if int((u - e) / 0.12) % 2 == 0 else 0
    return 0

def audience_state(t):
    """the front row: the old man (straw hat), the reserved seat for 鱼, 王工 (messy hair, glasses)."""
    u = cl(t)
    old = dict(kind='hat', x=80, dx=0, dy=_laugh(u))
    wang = dict(kind='messy', x=402, dx=0, dy=_laugh(u - 0.05))
    if C_FISH_TOAST + 0.1 <= u < C_FISH_TOAST + 1.4: old['dx'] = 1            # glances at the empty seat beside him
    if C_SHATTER <= u < C_SHATTER + 0.18: wang['dy'] = -2                       # flinches at the crash
    if C_CLAP0 <= u < C_CLAP1:
        wang['clap'] = (u - C_CLAP0) / 0.17; wang['clap_dy'] = -5; wang['clap_dx'] = -14
        old['clap'] = (u - C_CLAP0 - 0.05) / 0.23; old['clap_dy'] = -1; old['clap_dx'] = 13
    if u >= C_DOZE:                                                            # nods off ...
        k = ramp(u, C_DOZE, C_DOZE + 0.8, 'io')
        old['dy'] = int(round(5 * k)); old['dx'] = int(round(2 * k))
        if u >= C_DING: old['dy'] = -1 if u < C_DING + 0.12 else 0; old['dx'] = 0    # ... 叮: awake
    return [old, dict(kind='card', x=126, card='鱼'), wang]

def front_light(t):
    u = cl(t)
    return float(0.12 + 0.88 * (0.55 * spot_k(t) + 0.45 * foot_k(t)))
