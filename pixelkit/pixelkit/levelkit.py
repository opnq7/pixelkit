"""pixelkit.levelkit - 「一关」的通用骨架件（v0.13h，《熬夜副本》第 1-5 关 + 结尾沉淀）。

    from pixelkit.levelkit import (hud2, revive_curve, Anchor, keyed, put_human, nightcap, ghost_dive, put_ghost, lying_head)

    hud2(t, pct, stage, flash, year, place, t_enter, t_out, k)   关卡 HUD：复活进度 pips + 地点牌（一次只显示一件事）
    revive_curve(t, t0, pct0, pct1)                              复活进度补间 + 闪光
    Anchor().render(t, color_k, z, cx, cy, ghost_xy, ghost_act, dawn=0..1, dive=(t0,p0,p1), clock='0356', face, phone)
                                                                 冻结在 03:56 的卧室（存档点）：每关结束回到这里；dawn 让窗外天亮、时钟走动
    keyed(t, [(t0, z, cx, cy), ...])                              关键帧镜头路径（zoom 走对数插值，段间 smoothstep）
    put_human / nightcap / ghost_dive / put_ghost                 板块上的人物 / 夜帽 / 附身俯冲 / 小魂
"""
import math
import numpy as np
from . import gameui as G
from .core import scale_nearest as _scale
from .characters import human as _human, ghost as _ghost

_np = np

def lerp(a, b, k): return a + (b - a) * k
def smooth(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

def put_human(fr, look, x, y_foot, face='normal', arms='rest', phase=0, look_dir=(0, 0), head_dy=0, tilt=0.0, white=0.0, glint=0.0, shadow=True):
    p = _human.draw(look, face=face, arms=arms, phase=phase, look=look_dir, head_dy=head_dy, tilt=tilt, glint=glint)
    hx, hy = x - p.ax, y_foot - 55
    for i, sp in enumerate((p.body, p.hands)):
        a = sp.cv.a
        if white > 0:
            a = a.copy(); m = a[..., 3] > 0
            a[m, :3] = (a[m, :3] * (1 - white) + 255 * white).astype(_np.uint8)
        if hasattr(fr, 'actor'):
            fr.actor(a, hx, hy, E=(sp.E + white) if white > 0 else sp.E, foot=(x, y_foot) if (i == 0 and shadow) else None)
        else:
            fr.sprite(a, hx, hy, E=(sp.E + white) if white > 0 else sp.E)
    return (x, y_foot - 55)          # head top

def nightcap(fr, x, y_top, t, w=22):
    """the ghost's star night-cap on a possessed person's head (the film's 'you are in here' marker)."""
    import math
    sway = 1.2 * math.sin(t * 2.3)
    hw = w / 2
    y_top = y_top + 3                     # v0.13f: sit ON the hair (was floating ~3 px above it)
    before = fr.img.copy() if getattr(fr, 'act', None) is not None else None
    fr.poly([(x - hw, y_top + 3), (x - hw * 0.5, y_top - 5), (x + hw * 0.2, y_top - 8), (x + hw + 4 + sway, y_top - 4),
             (x + hw * 0.6, y_top), (x + hw, y_top + 3)], '#3a4ca8')
    fr.poly([(x - hw * 0.3, y_top - 6), (x + hw * 0.2, y_top - 8), (x + hw + 4 + sway, y_top - 4), (x + hw * 0.5, y_top - 3)], '#4c63c9')
    fr.rect(x - hw, y_top + 2, w, 3, '#f5ead2'); fr.rect(x - hw, y_top + 4, w, 1, '#cdbf9f')
    for sx, sy in ((x - hw * 0.3, y_top - 3), (x + hw * 0.4, y_top - 5)): fr.px(sx, sy, '#ffd85a', 0.6)
    fr.ell(x + hw + 4 + sway, y_top - 4, 2.4, 2.4, '#ffd85a', 0.5)
    if before is not None: fr.act |= (fr.img != before).any(-1)

def lying_head(fr, look, x, y, face='closed', blanket_col=('#4a4a5a', '#5a5a6e'), w=40, cap_t=None):
    """head on a pillow + a blanket up to the chin (front view, for beds seen from the foot end)."""
    p = _human.draw(look, face=face, arms='rest')
    fr.ell(x, y + 4, w * 0.66, 7, '#e8e4f0')
    hs = p.body.cv.a[:34]; fr.sprite(hs, x - p.ax, y - 20)
    if cap_t is not None: nightcap(fr, x, y - 15, cap_t, 24)
    m = fr.poly([(x - w, y + 12), (x + w, y + 12), (x + w + 10, y + 40), (x - w - 10, y + 40)], blanket_col[0])
    fr.fill(m & fr.M_poly([(x - w * 0.5, y + 12), (x + w * 0.5, y + 12), (x + w * 0.6, y + 40), (x - w * 0.6, y + 40)]), blanket_col[1])
    fr.rect(x - w, y + 11, 2 * w, 2, '#e8e0c8'); fr.outline(m)

def put_ghost(fr, t, x, y, face='normal', arms='rest', look=(0, 0), alpha=1.0, scale=1.0, glow=0.22, squash=0.0):
    g = _ghost.draw(face=face, arms=arms, t=t, look=look, alpha=alpha, glow=glow, squash=squash)
    rgba, E = g.rgba, g.E
    if abs(scale - 1) > 0.02: rgba = _scale(rgba, scale); E = _scale(E, scale)
    fr.sprite(rgba, x - g.ax * scale, y - g.ay * scale, E=E)

def ghost_dive(fr, t, t0, p0, p1, dur=0.45, look=(0, 0)):
    """the possession dive: ghost streaks from p0 into p1 (shrinking), with a trail. returns k (0..1)."""
    import math
    k = max(0.0, min(1.0, (t - t0) / dur))
    if k >= 1: return 1.0
    e = k * k * (3 - 2 * k)
    for j, (lag, a) in enumerate(((0.24, 0.25), (0.14, 0.45), (0.0, 1.0))):
        kk = max(0.0, e - lag)
        x = p0[0] + (p1[0] - p0[0]) * kk; y = p0[1] + (p1[1] - p0[1]) * kk - 18 * math.sin(math.pi * kk)
        put_ghost(fr, t, x, y, face='determined', look=look, alpha=a, scale=1.0 - 0.6 * kk, squash=-0.25 * math.sin(math.pi * kk))
    return k

def hud2(t, pct, stage, flash=0.0, year=None, place='', t_enter=0.4, t_out=None, k=1.0):
    from pixelkit import ui as _ui
    cv = _ui.UICanvas()
    G.revive_pips(cv, t, pct, stage, 5, flash=flash, k=k)
    if year: G.loc_tag(cv, t, t_enter, year, place, t_out=t_out)
    return cv

def revive_curve(t, t0, pct0, pct1):
    """pct + flash for a revive gain at t0 (fills over 0.6 s, flash peaks at the end)."""
    import math
    u = max(0.0, min(1.0, (t - t0) / 0.6)); e = 1 - (1 - u) ** 3
    fl = max(0.0, 1 - abs(t - t0 - 0.6) / 0.3) if t > t0 else 0.0
    return pct0 + (pct1 - pct0) * e, fl

class Anchor:
    """the frozen bedroom at 03:56 - the film's save point.  Every level ends here: the ghost floats back over the
    body, the revive meter fills, and the room gets a bit of its colour back (color_k 0 = grey .. 1 = full)."""
    def __init__(self):
        from pixelkit.sets.bedroom_night import BedroomNight
        self.b = BedroomNight()

    def render(self, t, color_k=0.0, z=1.7, cx=184, cy=98, ghost_xy=None, ghost_act=None, ghost_scale=1.0, frame_i=0, cat='curl',
               clock='0356', face='closed', phone='smack', screen=(150, 210, 240), dawn=0.0, dive=None, head_dy=0):
        """dawn 0..1: the window goes from night to sunrise and the room warms (the 'revive' payoff);
        dive=(t0, p0, p1): the ghost streaks into the body instead of floating (ghost_xy ignored)."""
        from pixelkit.sets.bedroom_night import GRADE_BED
        from pixelkit.pixstage import cam as _cam
        from pixelkit import acting as _A
        fr = self.b.frame(t, face=face, phone=phone, clock=clock, colon=True, cat=cat, screen=screen, chest=0.0 if face == 'closed' else None,
                          bulbs=color_k, monitor=color_k * (1 - dawn), head_dy=head_dy)
        if dawn > 0:
            wx, wy, ww, wh = self.b.A['window']
            sky = fr.M_rect(wx, wy, ww, wh) & ~(fr.M_rect(wx + ww // 2 - 1, wy, 2, wh) | fr.M_rect(wx, wy + wh // 2 - 1, ww, 2))
            def mixc(a, b): return '#%02x%02x%02x' % tuple(int(a[i] + (b[i] - a[i]) * dawn) for i in range(3))
            fr.grad(sky, mixc((16, 20, 58), (255, 176, 112)), mixc((48, 58, 106), (255, 224, 160)), wy, wy + wh, 4)
            fr.ell(wx + 30, wy + wh - 8 - 6 * (1 - dawn), 7, 7, '#fff4c8', dawn)
        p = None; head = None
        if dive is not None:
            t0, p0, p1 = dive
            ghost_dive(fr, t, t0, p0, p1, 0.45, look=(1, 2))
        elif ghost_xy is not None and ghost_act is not None:
            p = ghost_act.at(t); rgba, E, ax, ay = _A.ghost_sprite(p, t)
            if abs(ghost_scale - 1) > 0.02: rgba = _scale(rgba, ghost_scale); E = _scale(E, ghost_scale)
            gx, gy = ghost_xy[0] + p['dx'], ghost_xy[1] + p['dy']
            fr.sprite(rgba, gx - ax * ghost_scale, gy - ay * ghost_scale, E=E); head = (gx, gy - 24 * ghost_scale)
        L = self.b.light(fr, phone_k=0.5 * (1 - dawn), lamp_k=0.5 + 0.5 * color_k, room_k=0.8 + 0.2 * dawn, phone_xy=(182, 104))
        if ghost_xy is not None and dive is None: L = L + fr.band(ghost_xy[0], ghost_xy[1] - 14, 34, 28, (0.55, 0.75, 1.0), [(1.0, 0.18), (0.5, 0.32)])
        if dawn > 0:
            wx, wy, ww, wh = self.b.A['window']
            L = L + dawn * (fr.band(wx + ww / 2, 130, 120, 60, (1.0, 0.75, 0.45), [(1.0, 0.18), (0.6, 0.32)])
                            + fr.cone((wx + ww / 2, wy + 10), (wx + 10, 180), (200, 180), (1.0, 0.8, 0.5), 0.12))
        c = _cam(z, cx, cy)
        desat = 0.85 * (1 - color_k)
        tint = (0.9 + 0.1 * color_k + 0.12 * dawn, 0.93 + 0.07 * color_k + 0.04 * dawn, 1.08 - 0.08 * color_k - 0.16 * dawn)
        img = fr.render(c, L, GRADE_BED, frame=frame_i, desat=desat, tint=tint)
        return img, c, p, head

def keyed(t, keys, log_idx=(0,)):
    """piecewise smooth interpolation between keyframes [(t, a, b, ...), ...]; indices in log_idx (zoom) interpolate in log space."""
    import math
    if t <= keys[0][0]: return tuple(keys[0][1:])
    for k0, k1 in zip(keys, keys[1:]):
        if t < k1[0]:
            u = smooth((t - k0[0]) / max(1e-6, k1[0] - k0[0])); out = []
            for i, (a, b) in enumerate(zip(k0[1:], k1[1:])):
                out.append(math.exp(math.log(a) + (math.log(b) - math.log(a)) * u) if i in log_idx else a + (b - a) * u)
            return tuple(out)
    return tuple(keys[-1][1:])
