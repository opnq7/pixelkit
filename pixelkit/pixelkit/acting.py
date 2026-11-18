"""pixelkit.acting - 动作库（v0.13d）：把常用的喜剧表演做成可点名的「beat」，时间线里写一行就能演。

perform.py 是零件（弹簧、抖动、眨眼……），acting.py 是动作：每个 beat 自带 预备 → 动作 → 过冲 → 回稳，
再叠上待机的呼吸 / 漂浮 / 眨眼。输出是一组通用参数，小魂 / 人类 / 小工都能用：

    from pixelkit import acting as A
    act = A.Act(face='normal', arms='rest', float_amp=1.6)          # 小魂待机：上下漂
    act.beat(2.10, 'take', look=(-1, 4))                            # 二次确认：先看、回头、猛地再看
    act.beat(3.00, 'startle')                                       # 吓一跳：跳起 + 拉长 + 冒汗 + !!
    act.beat(4.20, 'freeze', dur=0.8)                               # 僵住（伸手到一半）：抖 + 冒汗
    act.beat(5.10, 'whistle', dur=0.9)                              # 若无其事吹口哨（眯眼 + ♪）
    p = act.at(t)        # -> dict(dx, dy, squash, rot, face, arms, look, fx=[(kind, age, k)...])
    ... draw the character at (x + p['dx'], y + p['dy']) with p['face'], p['arms'], p['look'], squash=p['squash'] ...
    A.draw_fx(cv, p['fx'], ux, uy, t)       # 在 UI 层画 汗滴 / !! / ? / ♪ / 星星 / 生气符号 / zZ

beats（dur 可改）：
  take      二次确认（看 → 回正 → 0.2 s 后猛回头 + 跳 + wow + !!）
  startle   吓一跳（下蹲 2 帧 → 跳起拉长 → 落地压扁 → 冒汗）
  freeze    僵住（原地高频小抖 + 冒汗 + 表情 wow/sad）
  nod       打瞌睡点头（慢慢下沉 → 猛抬头）
  sigh      叹气（下沉 + sad + 呼气）
  cheer     欢呼（举手连跳两下 + happy + 星星）
  whistle   吹口哨装没事（眯眼、侧看、左右晃 + ♪）
  tumble    被冲走 / 被打飞（整圈旋转 + dizzy + 星星）
  shiver    发抖（左右快抖，冷 / 怕）
  peek      探头偷看（侧移 + 眯眼）
  angry     生气（压扁 + 跺 + 💢）
  dizzy     晕（转圈星星）
  point     指（预备后撤 → 伸手）
  nodyes    点头同意（两次小点头 + happy）
  shake     摇头（左右摆 + sad）
  ask       疑问（歪头 + ?）
"""
import math
from .perform import wobble, clamp01

def _eo(u): u = clamp01(u); return 1 - (1 - u) ** 3
def _sm(u): u = clamp01(u); return u * u * (3 - 2 * u)

DUR = dict(take=0.9, startle=0.8, freeze=0.8, nod=1.2, sigh=1.0, cheer=0.9, whistle=1.0, tumble=1.0, shiver=0.8, peek=0.9,
           angry=0.8, dizzy=1.0, point=0.7, nodyes=0.7, shake=0.8, ask=0.9)

class Act:
    def __init__(self, face='normal', arms='rest', look=(0, 0), float_amp=0.0, float_hz=0.38, blink=True, blink_every=2.7,
                 seed=0):
        self.base = dict(face=face, arms=arms, look=look)
        self.float_amp, self.float_hz = float_amp, float_hz
        self.blink, self.blink_every, self.seed = blink, blink_every, seed
        self.beats = []          # (t0, kind, dur, kw)
        self.holds = []          # (t0, t1, overrides)

    def beat(self, t0, kind, dur=None, **kw):
        self.beats.append((t0, kind, dur or DUR[kind], kw)); return self

    def hold(self, t0, t1, **over):
        """plain pose override for a time range (face / arms / look ...)."""
        self.holds.append((t0, t1, over)); return self

    def at(self, t):
        p = dict(self.base, dx=0.0, dy=0.0, squash=0.0, rot=0.0, fx=[])
        if self.float_amp:
            p['dy'] += self.float_amp * math.sin(2 * math.pi * self.float_hz * t + self.seed)
        for (a, b, over) in self.holds:
            if a <= t < b: p.update(over)
        busy = False
        for (t0, kind, dur, kw) in sorted(self.beats, key=lambda r: r[0]):
            u = (t - t0) / dur
            if 0 <= u < 1:
                busy = True; getattr(self, '_' + kind)(p, t - t0, u, dur, kw, t)
            elif u >= 1 and kw.get('stay'):
                p.update(kw['stay'])
        if self.blink and not busy and p['face'] in ('normal', 'happy', 'determined', 'smug'):
            ph = (t + 0.37 * self.seed) % self.blink_every
            if ph < 0.09: p['face'] = 'blink'
        return p

    # ------------------------------------------------------------------ beats
    def _take(self, p, a, u, d, kw, t):
        look = kw.get('look', (-1, 4))
        if a < 0.25: p['look'] = look                                    # glance at it
        elif a < 0.45: p['look'] = (0, 0)                                # ... back (it hasn't landed)
        else:                                                            # SNAP back + jump
            p['look'] = look; p['face'] = kw.get('face', 'wow')
            j = a - 0.45
            p['dy'] -= 7 * _eo(j / 0.08) * (1 - _sm((j - 0.1) / 0.35)) + wobble(t, t - j + 0.08, 1.5, 6, 6)
            p['squash'] -= 0.25 * max(0, 1 - j / 0.12)
            p['fx'].append(('!!', j, 1.0))

    def _startle(self, p, a, u, d, kw, t):
        if a < 0.07: p['squash'] += 0.25; p['dy'] += 2
        else:
            j = a - 0.07
            p['dy'] -= 9 * math.sin(math.pi * clamp01(j / 0.32))
            p['squash'] -= 0.35 * max(0, 1 - j / 0.2)
            if 0.32 < j < 0.45: p['squash'] += 0.2
        p['face'] = kw.get('face', 'wow'); p['arms'] = kw.get('arms', 'up')
        p['fx'].append(('sweat', a, 1.0)); p['fx'].append(('!', a, 1.0))

    def _freeze(self, p, a, u, d, kw, t):
        p['dx'] += 1.2 * math.sin(t * 70) * (1 - 0.5 * u)
        p['face'] = kw.get('face', 'wow')
        p['fx'].append(('sweat', a, 1.0))

    def _nod(self, p, a, u, d, kw, t):
        if u < 0.8: p['dy'] += 5 * _sm(u / 0.8); p['face'] = 'sleepy' if u > 0.3 else p['face']
        else: p['dy'] += 5 * (1 - _eo((u - 0.8) / 0.08)) - 2 * math.sin(math.pi * clamp01((u - 0.8) / 0.2)); p['face'] = 'wow'

    def _sigh(self, p, a, u, d, kw, t):
        p['dy'] += 3 * math.sin(math.pi * u); p['squash'] += 0.1 * math.sin(math.pi * u); p['face'] = kw.get('face', 'sad')
        p['fx'].append(('puff', a, 1.0))

    def _cheer(self, p, a, u, d, kw, t):
        p['dy'] -= 6 * abs(math.sin(u * 2 * math.pi)); p['arms'] = 'up'; p['face'] = kw.get('face', 'happy')
        p['squash'] += 0.15 * (abs(math.sin(u * 2 * math.pi)) < 0.2)
        p['fx'].append(('stars', a, 1.0))

    def _whistle(self, p, a, u, d, kw, t):
        p['face'] = kw.get('face', 'squint'); p['look'] = kw.get('look', (-2, -1))
        p['dx'] += 1.5 * math.sin(t * 7); p['rot'] += 4 * math.sin(t * 7)
        p['fx'].append(('notes', a, 1.0))

    def _tumble(self, p, a, u, d, kw, t):
        p['rot'] += 360 * kw.get('turns', 1.5) * _eo(u) * kw.get('dir', 1)
        p['face'] = 'dizzy'; p['fx'].append(('stars', a, 1.0))

    def _shiver(self, p, a, u, d, kw, t):
        p['dx'] += 1.0 * math.sin(t * 90); p['face'] = kw.get('face', 'sad'); p['squash'] += 0.06

    def _peek(self, p, a, u, d, kw, t):
        p['dx'] += kw.get('dist', 6) * math.sin(math.pi * u) * kw.get('dir', 1); p['face'] = 'squint'; p['look'] = (2 * kw.get('dir', 1), 0)

    def _angry(self, p, a, u, d, kw, t):
        p['squash'] += 0.15 + 0.1 * (int(a * 10) % 2); p['dy'] += 1 * (int(a * 10) % 2); p['face'] = kw.get('face', 'determined')
        p['fx'].append(('anger', a, 1.0))

    def _dizzy(self, p, a, u, d, kw, t):
        p['face'] = 'dizzy'; p['rot'] += 6 * math.sin(t * 6); p['fx'].append(('stars', a, 1.0))

    def _point(self, p, a, u, d, kw, t):
        p['arms'] = 'point'
        p['dx'] += (-2 if a < 0.12 else 2 * _eo((a - 0.12) / 0.15)) * kw.get('dir', 1)
        p['face'] = kw.get('face', 'determined')

    def _nodyes(self, p, a, u, d, kw, t):
        p['dy'] += 2.5 * abs(math.sin(u * 2 * math.pi)); p['face'] = 'happy'

    def _shake(self, p, a, u, d, kw, t):
        p['look'] = (int(round(2 * math.sin(u * 4 * math.pi))), 0); p['face'] = kw.get('face', 'sad')

    def _ask(self, p, a, u, d, kw, t):
        p['rot'] += 8 * _sm(min(u, 1 - u) * 4); p['face'] = kw.get('face', 'normal'); p['fx'].append(('?', a, 1.0))


# ====================================================================== UI-layer effects
def draw_fx(cv, fx, ux, uy, t, scale=1.0):
    """draw the effect list of Act.at() around a character whose head-top is at UI (ux, uy)."""
    from .core import C
    from . import ui, gameui as G
    for kind, age, k in fx:
        if kind == 'sweat':
            for i in range(2):
                d = (age * 1.8 + i * 0.5) % 1
                x, y = ux + (16 + 6 * i) * scale + 8 * d, uy + 6 * scale + 26 * d * d
                cv.rect(int(x), int(y), 3, 4, (130, 210, 255, int(255 * (1 - d)))); cv.px(int(x) + 1, int(y) - 1, (130, 210, 255, int(255 * (1 - d))))
        elif kind in ('!!', '!'):
            G.onomatopoeia(cv, '！' if kind == '!' else '！！', ux + 26 * scale, uy - 6 * scale, age, 2, C('#ffe24a'), life=0.8)
        elif kind == '?':
            q = min(1.0, age / 0.15)
            G.big_text(cv, '?', ux + 24 * scale, uy - 4 * scale - 4 * q, 2, C('#ffe27a'), alpha=q)
        elif kind == 'notes':
            for i in range(3):
                d = (age - i * 0.25)
                if 0 <= d < 0.8:
                    cv.text(int(ux - 26 * scale - 10 * d), int(uy + 8 * scale - 36 * d), '♪', (255, 236, 150, int(255 * (1 - d / 0.8))), 'zh12',
                            outline=(20, 12, 4, int(255 * (1 - d / 0.8))))
        elif kind == 'stars':
            ui.dizzy_stars(cv, ux, uy, t, n=3, rx=20 * scale, ry=5 * scale)
        elif kind == 'anger':
            x, y = int(ux + 18 * scale), int(uy)
            col = (255, 70, 60, 255)
            for (dx, dy) in ((0, 0), (1, 1), (5, 0), (4, 1), (0, 5), (1, 4), (5, 5), (4, 4)): cv.px(x + dx, y + dy, col)
        elif kind == 'puff':
            d = min(1.0, age / 0.6)
            cv.rect(int(ux - 20 * scale - 10 * d), int(uy + 16 * scale), 4, 3, (230, 230, 240, int(200 * (1 - d))))
        elif kind == 'zz':
            for i in range(2):
                zt = (t * 1.2 + i * 0.5) % 1
                cv.text(int(ux + 18 * scale + 16 * zt), int(uy - 30 * zt), 'z', (200, 210, 255, int(255 * (1 - zt))), 'p2p')

def ghost_sprite(p, t, glow=0.22, alpha=1.0):
    """ghost.draw from an Act pose (applies squash + rotation)."""
    from .characters import ghost
    from .perform import rotsprite
    g = ghost.draw(face=p['face'], arms=p['arms'], t=t, look=p['look'], alpha=alpha, glow=glow, squash=p['squash'])
    rgba, E = g.rgba, g.E
    if abs(p.get('rot', 0)) > 0.5:
        rgba, E = rotsprite(rgba, E, p['rot'], (g.ax, g.ay + 14), method='epx' if abs(p['rot']) > 10 else 'shear')
    return rgba, E, g.ax, g.ay
