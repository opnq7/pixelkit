"""pixelkit.sets.symbols - 叙事用「主角物件」（v0.13《熬夜副本》）：画在 pixstage.Stage 上的大号像素象征物。

    sun(s, cx, cy, r, t, k)                    像素太阳：硬边光圈 + 旋转的方块光芒
    gear_clock(s, cx, cy, r, t, hours=24, hand=..., glow)   齿轮表盘：外齿 + 刻度 + 指针（体内时钟）
    thermometer(s, cx, top, h, level, t)       巨型温度计：玻璃管 + 红色水银柱（level 0..1）
    chalk_clock(s, cx, cy, r, n, k, segs)      粉笔画的 n 格钟（k = 画到第几格，segs = [(起格, 止格, 颜色)]）
    boulder(s, cx, cy, r, rot)                 大石头（挡住太阳）
    vs_mark(s, cx, cy, sc, k)                  「VS」砸字
    stage_floor(s, y, col)                     黑色舞台地面 + 光池
返回值一般是 (mask) 或锚点；所有物件都带 1px 深色描边、2-3 级硬边明暗。
"""
import math
import numpy as np
from ..core import C

OUT = '#07060c'

def sun(s, cx, cy, r, t=0.0, k=1.0):
    n = 12
    for i in range(n):
        a = i / n * 2 * math.pi + t * 0.6
        L = r * (1.45 + 0.12 * math.sin(t * 4 + i))
        for j in range(3):
            d = r * 1.12 + (L - r * 1.12) * j / 2
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            sz = max(1, int(round(r * (0.16 - 0.04 * j))))
            s.rect(x - sz / 2, y - sz / 2, sz, sz, '#ffd34a' if j < 2 else '#ffb03a', 1.0 * k)
    m = s.ell(cx, cy, r, r, '#ffb030', 1.0 * k)
    s.fill(s.M_ell(cx - r * 0.12, cy - r * 0.12, r * 0.82, r * 0.82) & m, '#ffd04a', 1.0 * k)
    s.fill(s.M_ell(cx - r * 0.3, cy - r * 0.32, r * 0.42, r * 0.36) & m, '#fff0a0', 1.0 * k)
    s.outline(m, '#5a2a08')
    return m

def gear_clock(s, cx, cy, r, t=0.0, hours=24, hand=None, glow=0.8, col='#7fd8ff', face='#0e2034', teeth=14, spin=0.0):
    """hand: angle in hours (0..hours) for the hour hand; spin rotates the teeth ring."""
    for i in range(teeth):
        a = i / teeth * 2 * math.pi + spin
        x, y = cx + r * 1.08 * math.cos(a), cy + r * 1.08 * math.sin(a)
        sz = max(2, int(round(r * 0.28)))
        s.rect(x - sz / 2, y - sz / 2, sz, sz, '#3a6a8a', glow * 0.3)
    ring = s.ell(cx, cy, r, r, '#3a6a8a', glow * 0.3)
    fm = s.fill(s.M_ell(cx, cy, r * 0.84, r * 0.84), face, glow * 0.2)
    s.outline(ring, OUT)
    for h in range(hours):
        a = h / hours * 2 * math.pi - math.pi / 2
        big = h % (hours // 4) == 0
        x, y = cx + r * 0.70 * math.cos(a), cy + r * 0.70 * math.sin(a)
        s.rect(round(x) - (1 if big else 0), round(y) - (1 if big else 0), 2 if big else 1, 2 if big else 1, col, glow)
    if hand is not None:
        a = hand / hours * 2 * math.pi - math.pi / 2
        s.line(cx, cy, cx + r * 0.58 * math.cos(a), cy + r * 0.58 * math.sin(a), '#ffffff', glow)
        s.line(cx + 1, cy, cx + 1 + r * 0.58 * math.cos(a), cy + r * 0.58 * math.sin(a), col, glow)
    s.rect(cx - 1, cy - 1, 3, 3, '#ffd34a', glow)
    return ring

def thermometer(s, cx, top, h, level=0.5, t=0.0, w=12):
    bulb_r = w * 0.95
    tube = s.rect(cx - w / 2, top, w, h, '#c8d8e8', 0.15)
    s.ell(cx, top, w / 2, w / 2, '#c8d8e8', 0.15)
    bulb = s.ell(cx, top + h + bulb_r * 0.6, bulb_r, bulb_r, '#d8302a', 0.5)
    s.outline(tube | bulb | s.M_ell(cx, top, w / 2, w / 2), OUT)
    inner = s.M_rect(cx - w / 4, top + 2, w / 2, h)
    lv = top + 2 + (h - 2) * (1 - level)
    s.fill(inner & (s.yy >= lv), '#ff4a3a', 0.6)
    s.fill(inner & (s.yy >= lv) & (s.xx < cx - w / 4 + 2), '#ff9a80', 0.7)
    s.fill(s.M_ell(cx - bulb_r * 0.3, top + h + bulb_r * 0.3, bulb_r * 0.35, bulb_r * 0.3), '#ff9a80', 0.7)
    for i in range(9):
        y = top + 6 + i * (h - 10) / 8
        s.rect(cx + w / 2 + 1, y, 3 if i % 2 == 0 else 2, 1, '#e8e0d0')
    s.rect(cx - w / 2 + 2, top + 2, 1, h - 4, '#ffffff', 0.4)
    return lv

def chalk_clock(s, cx, cy, r, n=28, k=1.0, segs=(), col='#e8e4dc'):
    m = s.M_ell(cx, cy, r, r) & ~s.M_ell(cx, cy, r - 1.2, r - 1.2)
    s.fill(m, col)
    shown = int(round(n * k))
    for i in range(n):
        a0 = i / n * 2 * math.pi - math.pi / 2
        if i < shown:
            s.line(cx + (r - 1) * math.cos(a0), cy + (r - 1) * math.sin(a0), cx + (r * 0.55) * math.cos(a0), cy + (r * 0.55) * math.sin(a0), col)
    ang = np.arctan2(s.yy + 0.5 - cy, s.xx + 0.5 - cx)
    seg_i = ((ang + math.pi / 2) % (2 * math.pi)) / (2 * math.pi) * n
    band = s.M_ell(cx, cy, r * 0.86, r * 0.86) & ~s.M_ell(cx, cy, r * 0.58, r * 0.58)
    for (a, b, c) in segs:
        if a >= shown: continue
        b2 = min(b, shown)
        s.fill(band & (seg_i >= a) & (seg_i < b2) & ((s.xx + s.yy) % 2 == 0), c)
    return m

def boulder(s, cx, cy, r, rot=0.0):
    pts = []
    for i in range(12):
        a = i / 12 * 2 * math.pi + rot
        rr = r * (0.9 + 0.12 * math.sin(i * 2.3))
        pts.append((cx + rr * math.cos(a), cy + rr * 0.85 * math.sin(a)))
    m = s.poly(pts, '#4a3a32')
    s.fill(m & s.M_ell(cx - r * 0.25, cy - r * 0.3, r * 0.6, r * 0.45), '#6a5444')
    s.fill(m & s.M_ell(cx + r * 0.35, cy + r * 0.35, r * 0.55, r * 0.4), '#33281f')
    s.outline(m, OUT)
    return m

def vs_mark(s, cx, cy, sc=3, k=1.0):
    from ..core import text_mask
    m = text_mask('VS', 'p2p')
    ys, xs = np.nonzero(m); m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    big = np.repeat(np.repeat(m, sc, 0), sc, 1)
    h, w = big.shape; x0, y0 = int(cx - w / 2), int(cy - h / 2)
    mm = np.zeros((s.H, s.W), bool)
    xs0, ys0 = max(0, x0), max(0, y0); xs1, ys1 = min(s.W, x0 + w), min(s.H, y0 + h)
    mm[ys0:ys1, xs0:xs1] = big[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
    sh = np.roll(np.roll(mm, sc // 2 + 1, 0), sc // 2 + 1, 1)
    s.fill(sh & ~mm, '#5a0a10')
    s.fill(mm, '#ff4a3a', 1.0 * k)
    s.fill(mm & ~np.roll(mm, sc, 0), '#ffd0b0', 1.0 * k)
    return mm

def stage_floor(s, y=128, col='#0d0b12', line='#1a1624'):
    m = s.M_poly([(0, s.H), (0, y + 10), (s.W, y + 10), (s.W, s.H)])
    s.fill(m, col)
    for k in range(-8, 9):
        s.line(s.W / 2 + k * 16, y + 10, s.W / 2 + k * 60, s.H, line, mask=m)
    return m
