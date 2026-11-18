"""pixelkit.sets.phone_feed - 刷短视频的手机（320x180 舞台，v0.13《熬夜副本》开场钩子）。

竖屏手机占满画面高度，屏幕里是一条条像素短视频（猫推杯子 / 煎蛋 / 熬夜的危害 / 液压机 / 看到最后 / 跳舞狗 / 切肥皂），
拇指上滑 → 视频带惯性吸附翻页；状态栏的时间和电量（充电中）都可控。

    pf = PhoneFeed()
    fr = pf.frame(t, swipes=[0.4, 1.2, ...], clips=('cat', 'egg', 'warn', ...), clock='03:47', battery=100, tilt=0)
    L = pf.light(fr)
    pf.screen_color(t, swipes, clips)   -> 当前屏幕平均色（给脸上的反光 / 环境光用）
    pf.clip_thumb(name, t)              -> (5,4,3) 小图（眼睛里的倒影）
CLIP 库可单独复用：draw_clip(st, name, x, y, w, h, t)。
"""
import math
import numpy as np
from ..pixstage import Stage
from ..core import text_width

SX, SY, SW, SH = 118, 10, 84, 160          # screen rect on the stage
CLIPS = ('cat', 'egg', 'warn', 'press', 'end', 'dog', 'soap', 'cat2')
CLIP_COL = {'cat': (230, 200, 160), 'egg': (240, 180, 90), 'warn': (220, 60, 50), 'press': (150, 160, 180), 'end': (250, 210, 60),
            'dog': (150, 210, 255), 'soap': (240, 140, 200), 'cat2': (200, 170, 230)}
META = {'cat': ('@橘座大人', '它是故意的 #猫', '12.8w'), 'egg': ('@深夜食堂', '凌晨的煎蛋最香', '3.1w'),
        'warn': ('@健康科普', '熬夜的十大危害', '22'), 'press': ('@液压机日常', '今天压一只鸭', '8.9w'),
        'end': ('@反转大王', '一定要看到最后!!!', '45w'), 'dog': ('@修勾', '它在蹦迪', '6.6w'),
        'soap': ('@解压', '切肥皂 ASMR', '19w'), 'cat2': ('@橘座大人', '又是它', '7.7w')}

# ------------------------------------------------------------------ the clips (each draws inside x, y, w, h)
def _clip_cat(s, x, y, w, h, t, alt=False):
    clip = s.M_rect(x, y, w, h)
    s.fill(clip, '#3a2a3a' if not alt else '#2a2a48')
    s.fill(clip & (s.yy > y + h * 0.62), '#6a4a3a' if not alt else '#4a3a5a')
    s.rect(x, y + h * 0.62, w, 2, '#8a6a4a')
    s.rect(x + 8, y + 20, 22, 28, '#4a6a9a'); s.rect(x + 9, y + 21, 20, 26, '#1a2a4a'); s.px(x + 14, y + 26, '#ffffff')   # window
    ph = (t * 1.1) % 2.0
    # cup: slides then falls off the right edge
    cx = x + w * 0.62 + (min(ph, 0.9) / 0.9) * 10
    cy = y + h * 0.62 - 9
    if ph > 0.9:
        f = ph - 0.9; cx += f * 18; cy += 120 * f * f
    if cy < y + h:
        m = s.M_rect(cx, cy, 7, 9) & clip; s.fill(m, '#f2ece0'); s.fill(m & (s.yy < cy + 2), '#c8302a')
    # cat: loaf on the table, paw out
    kx, ky = x + w * 0.34, y + h * 0.62
    s.fill(s.M_ell(kx, ky - 9, 16, 10) & clip, '#e8924a'); s.fill(s.M_ell(kx - 10, ky - 18, 9, 8) & clip, '#e8924a')
    for ex in (-13, -7): s.fill(s.M_poly([(kx + ex - 3, ky - 22), (kx + ex, ky - 30), (kx + ex + 3, ky - 22)]) & clip, '#e8924a')
    s.rect(kx - 14, ky - 19, 2, 2, '#1a0e0a'); s.rect(kx - 8, ky - 19, 2, 2, '#1a0e0a')
    pw = 6 + 6 * max(0, math.sin(min(ph, 0.9) / 0.9 * math.pi))
    s.fill(s.M_rect(kx + 10, ky - 7, pw, 4) & clip, '#e8924a'); s.px(kx + 10 + pw, ky - 6, '#f8c0c0')
    for k in (-4, 2, 8): s.line(kx + k, ky - 18, kx + k + 2, ky - 12, '#c86a2a')

def _clip_egg(s, x, y, w, h, t):
    clip = s.M_rect(x, y, w, h)
    s.fill(clip, '#2a1a14'); s.fill(clip & s.M_ell(x + w / 2, y + h * 0.55, 46, 18), '#4a3a32')
    s.fill(clip & s.M_ell(x + w / 2, y + h * 0.55, 36, 14), '#1a1a1e'); s.fill(clip & s.M_ell(x + w / 2, y + h * 0.55, 34, 12), '#2a2a30')
    s.rect(x + w / 2 + 34, y + h * 0.55 - 2, 30, 4, '#1a1a1e')
    s.fill(clip & s.M_ell(x + w / 2 - 2, y + h * 0.55, 20, 8), '#fff8ec')
    s.fill(clip & s.M_ell(x + w / 2, y + h * 0.55 - 1, 7, 5), '#ffb020'); s.px(x + w / 2 - 2, y + h * 0.55 - 3, '#fff0b0')
    rng = np.random.default_rng(int(t * 12))
    for i in range(8):
        a = rng.uniform(0, 6.28); r = rng.uniform(14, 22)
        s.px(x + w / 2 + r * math.cos(a), y + h * 0.55 + r * math.sin(a) * 0.4, '#fff8ec')
    for i in range(3):     # steam
        sx = x + w / 2 - 10 + i * 10; ph = (t * 0.8 + i * 0.33) % 1
        for k in range(6): s.px(sx + 2 * math.sin(k + t * 3 + i), y + h * 0.55 - 14 - ph * 30 - k * 3, '#8a7a7a')

def _clip_warn(s, x, y, w, h, t):
    clip = s.M_rect(x, y, w, h)
    s.fill(clip, '#cfc8bc'); s.rect(x, y + 18, w, 26, '#c0281f')
    s.text(x + w / 2 - text_width('熬夜的', 'zh12') / 2, y + 19, '熬夜的', '#ffffff', 'zh12')
    s.text(x + w / 2 - text_width('十大危害', 'zh12') / 2, y + 31, '十大危害', '#ffe24a', 'zh12')
    # skull icon
    cx, cy = x + w / 2, y + 74
    s.ell(cx, cy, 13, 12, '#e8e4dc'); s.rect(cx - 8, cy + 8, 16, 7, '#e8e4dc')
    s.ell(cx - 5, cy, 4, 4, '#1a1a1a'); s.ell(cx + 5, cy, 4, 4, '#1a1a1a'); s.poly([(cx, cy + 4), (cx - 2, cy + 8), (cx + 2, cy + 8)], '#1a1a1a')
    for k in (-5, -1, 3): s.rect(cx + k, cy + 10, 2, 5, '#1a1a1a')
    # doctor with pointer
    s.ell(x + 16, y + 112, 7, 7, '#f0c49e'); s.rect(x + 9, y + 118, 14, 22, '#ffffff'); s.rect(x + 12, y + 104, 8, 3, '#2a2a2a')
    s.line(x + 22, y + 122, x + 34, y + 96, '#8a5a2a')
    s.text(x + 30, y + 120, '第1条：', '#2a2a2a', 'zh8')

def _clip_press(s, x, y, w, h, t):
    clip = s.M_rect(x, y, w, h)
    s.fill(clip, '#2a2e36'); s.rect(x + 10, y + 20, 6, h - 40, '#5a5e6a'); s.rect(x + w - 16, y + 20, 6, h - 40, '#5a5e6a')
    ph = (t * 0.9) % 1.6; k = min(1, ph / 1.0)
    py = y + 26 + 60 * k
    s.rect(x + 14, y + 20, w - 28, py - y - 20, '#4a4e5a'); s.rect(x + 12, py, w - 24, 8, '#9aa0ae'); s.rect(x + 12, py + 7, w - 24, 1, '#3a3e48')
    s.rect(x + 12, y + 110, w - 24, 8, '#9aa0ae')
    duck_h = max(3, 22 * (1 - max(0, (k - 0.72) / 0.28)))
    by = y + 110
    s.fill(s.M_ell(x + w / 2, by - duck_h / 2, 12 + (22 - duck_h) * 0.5, duck_h / 2) & clip, '#ffd23a')
    if duck_h > 10:
        s.ell(x + w / 2 + 6, by - duck_h + 2, 6, 5, '#ffd23a'); s.rect(x + w / 2 + 11, by - duck_h + 2, 4, 2, '#ff8a2a'); s.px(x + w / 2 + 7, by - duck_h, '#1a1a1a')
    if k >= 1:
        for i in range(6): s.px(x + w / 2 + (i - 3) * 6, by - 2 - (ph - 1) * 20, '#ffd23a')

def _clip_end(s, x, y, w, h, t):
    clip = s.M_rect(x, y, w, h)
    s.fill(clip, '#1a1a2a')
    s.text(x + w / 2 - text_width('一定要', 'zh12') / 2, y + 30, '一定要', '#ffffff', 'zh12')
    s.text(x + w / 2 - text_width('看到最后', 'zh12') / 2, y + 44, '看到最后', '#ffe24a', 'zh12')
    s.text(x + w / 2 - text_width('!!!', 'zh12') / 2, y + 58, '!!!', '#ff4a3a', 'zh12')
    n = 3 - int(t * 2) % 3
    sc = 1 + 0.2 * (1 - (t * 2) % 1)
    s.ell(x + w / 2, y + 100, 16 * sc, 16 * sc, '#ff4a3a'); s.text(x + w / 2 - 3, y + 94, str(n), '#ffffff', 'zh12')
    by = y + 130 + 3 * math.sin(t * 9)
    s.poly([(x + w / 2 - 6, by), (x + w / 2 + 6, by), (x + w / 2, by + 8)], '#ffe24a')

def _clip_dog(s, x, y, w, h, t):
    clip = s.M_rect(x, y, w, h)
    s.fill(clip, '#2a1a4a')
    for i in range(5):
        c = ['#ff4a8a', '#4ad8ff', '#ffe24a', '#7aff6a', '#c86aff'][(i + int(t * 6)) % 5]
        s.fill(clip & s.M_ell(x + 10 + i * 16, y + 18, 5, 5), c)
    b = abs(math.sin(t * 7)) * 8
    cx, cy = x + w / 2, y + 110 - b
    s.ell(cx, cy, 16, 11, '#f2e2c8'); s.ell(cx + 12, cy - 12, 10, 9, '#f2e2c8')
    s.rect(cx + 6, cy - 26, 4, 8, '#c8a080'); s.rect(cx + 16, cy - 26, 4, 8, '#c8a080')
    s.rect(cx + 9, cy - 14, 2, 2, '#1a1a1a'); s.rect(cx + 15, cy - 14, 2, 2, '#1a1a1a'); s.rect(cx + 20, cy - 10, 3, 2, '#1a1a1a')
    s.rect(cx - 2, cy - 22, 10, 3, '#1a1a1a')                          # sunglasses
    for k in (-10, 6): s.rect(cx + k, cy + 9, 4, 8 + b, '#f2e2c8')
    s.text(x + 8, y + 50 + 4 * math.sin(t * 4), '♪', '#ffe24a', 'zh12'); s.text(x + w - 18, y + 70 + 4 * math.cos(t * 4), '♪', '#ff8ad8', 'zh12')

def _clip_soap(s, x, y, w, h, t):
    clip = s.M_rect(x, y, w, h)
    s.fill(clip, '#b8b0c8')
    cols = ['#ff8ac8', '#8ad8ff', '#ffe28a', '#a8ff9a', '#c8a8ff']
    for i in range(5):
        cx = x + 10 + i * 13; m = s.M_rect(cx, y + 80, 11, 30) & clip
        s.fill(m, cols[i]); s.fill(m & (s.xx < cx + 3), '#ffffff')
    kx = x + 10 + (t * 30) % 64
    s.rect(kx, y + 40, 3, 42, '#c8ccd8'); s.rect(kx - 1, y + 30, 5, 12, '#3a2a2a')
    for i in range(10):
        a = (i * 0.6 + t * 5) % 6.28; r = 6 + (t * 40 + i * 9) % 26
        s.px(kx + 1 + r * math.cos(a), y + 84 + r * math.sin(a) * 0.6, cols[i % 5])

DRAW = {'cat': _clip_cat, 'cat2': lambda s, x, y, w, h, t: _clip_cat(s, x, y, w, h, t, alt=True), 'egg': _clip_egg,
        'warn': _clip_warn, 'press': _clip_press, 'end': _clip_end, 'dog': _clip_dog, 'soap': _clip_soap}

def draw_clip(s, name, x, y, w, h, t): DRAW[name](s, x, y, w, h, t)

def _ease_swipe(u):
    """thumb flick: fast start, slight overshoot, settle (0..1 -> 0..1)."""
    if u <= 0: return 0.0
    if u >= 1: return 1.0
    e = 1 - (1 - u) ** 3
    return e + 0.06 * math.sin(math.pi * u) * (1 - u)

class PhoneFeed:
    W, H = 320, 180

    def __init__(self):
        self.st = Stage(self.W, self.H)
        s = self.st
        s.rect(0, 0, 320, 180, '#07060c')
        # out-of-focus ceiling + string-light bokeh behind the phone
        rng = np.random.default_rng(3)
        for i in range(14):
            x, y = rng.uniform(0, 320), rng.uniform(0, 70)
            if SX - 14 < x < SX + SW + 14: continue
            r = rng.uniform(4, 9)
            s.dither(s.M_ell(x, y, r, r), ['#5a3a1a', '#3a2a4a', '#5a2a2a'][i % 3], 0.6, 0.4)
        # blanket edge bottom-left / right
        s.poly([(0, 150), (90, 140), (130, 180), (0, 180)], '#141a3a'); s.poly([(320, 160), (230, 150), (210, 180), (320, 180)], '#141a3a')
        self.base = s.snapshot()

    def scroll(self, t, swipes, dur=0.32):
        pos = 0.0
        for i, ts in enumerate(swipes):
            d = dur if i < len(swipes) - 1 else dur
            pos += _ease_swipe((t - ts) / d)
        return pos

    def screen_color(self, t, swipes, clips=CLIPS):
        pos = self.scroll(t, swipes); i = int(math.floor(pos)); f = pos - i
        a = np.array(CLIP_COL[clips[i % len(clips)]], np.float32); b = np.array(CLIP_COL[clips[(i + 1) % len(clips)]], np.float32)
        return tuple(a + (b - a) * f)

    def clip_thumb(self, name):
        c = np.array(CLIP_COL[name], np.uint8)
        r = np.zeros((5, 4, 3), np.uint8); r[:] = c; r[0] = (30, 30, 40); r[4] = (20, 20, 30)
        return r

    def frame(self, t, swipes=(), clips=CLIPS, clock='03:47', battery=100, tilt=0.0, thumb=True, dim=0.0, freeze=None):
        s = self.st.from_snapshot(self.base)
        ox = int(round(tilt))
        # phone body
        body = s.M_rect(SX - 5 + ox, SY - 6, SW + 10, SH + 14)
        s.part(body, ['#0c0a12', '#1c1a26', '#2e2c3c', '#4a4860'], bevel=3, light=(-0.6, -0.5, 0.6), amb=0.4, ink='#020204')
        s.rect(SX - 6 + ox, SY + 30, 1, 14, '#2e2c3c'); s.rect(SX + SW + 5 + ox, SY + 24, 1, 10, '#2e2c3c')
        x0 = SX + ox
        tt = t if freeze is None else freeze
        pos = self.scroll(tt, swipes)
        i0 = int(math.floor(pos)); f = pos - i0
        off = int(round(f * SH))
        for k, idx in ((0, i0), (1, i0 + 1)):
            yy0 = SY - off + k * SH
            if yy0 >= SY + SH or yy0 + SH <= SY: continue
            name = clips[idx % len(clips)]
            sub = Stage(SW, SH); draw_clip(sub, name, 0, 0, SW, SH, tt + idx * 0.37)
            self._overlay(sub, name, tt)
            y_a, y_b = max(SY, yy0), min(SY + SH, yy0 + SH)
            blk = sub.img[y_a - yy0:y_b - yy0].copy(); blk[..., :3] = (blk[..., :3].astype(np.float32) * 0.82).astype(np.uint8)
            s.img[y_a:y_b, x0:x0 + SW] = blk
            s.E[y_a:y_b, x0:x0 + SW] = 0.62
        if dim > 0:
            s.img[SY:SY + SH, x0:x0 + SW, :3] = (s.img[SY:SY + SH, x0:x0 + SW, :3] * (1 - dim)).astype(np.uint8)
        # status bar
        s.rect(x0, SY, SW, 9, '#000000'); s.E[SY:SY + 9, x0:x0 + SW] = 0.95
        s.text(x0 + 3, SY + 1, clock, '#ffffff', 'silk', 0.95)
        bx = x0 + SW - 16
        s.rect(bx, SY + 2, 11, 5, '#ffffff', 0.95); s.rect(bx + 11, SY + 3, 1, 3, '#ffffff', 0.95)
        s.rect(bx + 1, SY + 3, max(1, int(9 * battery / 100)), 3, '#3ad86a' if battery > 20 else '#ff4a3a', 0.95)
        s.poly([(bx - 4, SY + 1), (bx - 6, SY + 5), (bx - 4, SY + 5), (bx - 5, SY + 8), (bx - 2, SY + 3), (bx - 4, SY + 3)], '#ffe24a', 0.95)
        # tabs
        s.text(x0 + 24, SY + 10, '关注', '#9a9aa8', 'zh8', 0.95); s.text(x0 + 46, SY + 10, '推荐', '#ffffff', 'zh8', 0.95)
        s.rect(x0 + 48, SY + 19, 12, 1, '#ffffff', 0.95)
        # notch / glare
        s.rect(x0 + SW // 2 - 8, SY - 3, 16, 2, '#020204')
        s.line(x0 + 4, SY + SH - 4, x0 + 30, SY + 40, '#ffffff', None, mask=None) if False else None
        # thumb
        if thumb:
            self._thumb(s, t, swipes, ox)
        return s

    def _overlay(self, sub, name, t):
        user, cap, likes = META[name]
        # right rail icons
        rx = SW - 12
        for j, (icon_c, lab) in enumerate((('#ff3a5a', likes), ('#ffffff', '评'), ('#ffffff', '转'))):
            y = 70 + j * 22
            if j == 0:
                sub.ell(rx + 4, y + 3, 3, 3, icon_c, 0.0); sub.ell(rx + 8, y + 3, 3, 3, icon_c, 0.0)
                sub.poly([(rx + 1, y + 4), (rx + 11, y + 4), (rx + 6, y + 10)], icon_c, 0.0)
            else:
                sub.rect(rx + 1, y, 10, 8, '#e8e8f0'); sub.rect(rx + 3, y + 8, 3, 2, '#e8e8f0')
            sub.text(rx - 2, y + 11, lab, '#ffffff', 'silk' if j == 0 else 'zh8')
        sub.text(4, SH - 32, user, '#ffffff', 'zh8'); sub.text(4, SH - 21, cap, '#e8e8e8', 'zh8')
        sub.rect(0, SH - 4, SW, 1, '#5a5a6a'); sub.rect(0, SH - 4, int(SW * ((t * 0.37) % 1)), 1, '#ffffff')

    def thumb_pos(self, t, swipes, ox=0):
        tx, ty = SX + SW - 10 + ox, SY + SH - 30
        for ts in swipes:
            u = (t - ts + 0.12) / 0.44
            if 0 <= u <= 1:
                k = 0.0 if u < 0.27 else min(1.0, (u - 0.27) / 0.5)
                lift = 0.0 if u < 0.27 else max(0.0, (u - 0.77) / 0.23)
                ty = SY + SH - 30 - 64 * (1 - (1 - k) ** 2) + 30 * lift
                tx = SX + SW - 10 + ox - 10 * k + 6 * lift
                break
        return tx, ty

    def _thumb(self, s, t, swipes, ox):
        """right hand: palm on the lower-right edge, fingers peeking on the left edge, thumb flicks up the screen."""
        SKN = ['#5a2e22', '#94543c', '#c8805c', '#e8a47a', '#f8c8a0']
        tx, ty = self.thumb_pos(t, swipes, ox)
        # fingers on the left edge
        for j in range(3):
            fy = SY + SH - 64 + j * 13
            s.part(s.M_ell(SX - 6 + ox, fy, 5, 5.5), SKN, bevel=2.5, light=(0.5, -0.6, 0.6), amb=0.35, ink='#2a120c')
        # palm
        palm = s.M_ell(SX + SW + 26 + ox, 176, 34, 30) | s.M_ell(SX + SW / 2 + 14 + ox, 186, 40, 16)
        s.part(palm, SKN, bevel=8, light=(-0.5, -0.7, 0.5), amb=0.3, ink='#2a120c')
        # thumb: base -> knuckle -> tip
        base = (SX + SW + 14 + ox, SY + SH - 4)
        kn = ((base[0] + tx) / 2 + 6, (base[1] + ty) / 2 + 4)
        m = np.zeros((self.H, self.W), bool)
        for (a, b, r0, r1) in ((base, kn, 10, 8), (kn, (tx, ty), 8, 6.5)):
            n = 16
            for i in range(n + 1):
                u = i / n; r = r0 + (r1 - r0) * u
                m |= s.M_ell(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, r, r)
        s.part(m, SKN, bevel=4, light=(-0.6, -0.6, 0.5), amb=0.32, ink='#2a120c')
        nail = s.M_ell(tx + 1.5, ty + 1, 3.6, 4.2)
        s.part(nail, ['#b07a6a', '#e8b8a8', '#fff0ea'], bevel=1.5, amb=0.5, outline=None)
        s.line(kn[0] - 5, kn[1] + 1, kn[0] + 1, kn[1] - 2, '#94543c')

    def light(self, s, k=1.0, col=(0.6, 0.8, 1.0)):
        L = s.light_base((0.6, 0.6, 0.8), 0.35)
        L = L + s.band(SX + SW / 2, SY + SH / 2, 110, 100, col, [(1.0, 0.12 * k), (0.62, 0.24 * k)])
        return L
