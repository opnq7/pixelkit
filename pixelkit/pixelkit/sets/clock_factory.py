"""pixelkit.sets.clock_factory - 「分子钟」工厂里的主角机器（v0.13g，第 5 关）：周期基因生产线。

    from pixelkit.sets.clock_factory import per_machine, loop_badge
    per_machine(st, x, y_base, t, on=1.0, gauge=0..1, lever=0..1, label='period')
      on     0 = 停机（灯灭、齿轮停、烟囱不冒气）.. 1 = 运转（绿灯、齿轮转、出料口一闪一闪）
      gauge  PER 浓度表（机身正面的竖条）
      lever  0 = 开（拉杆朝上）.. 1 = 关（拉杆被拉下）
    返回锚点 dict(out=(x, y) 出料口, lever=(x, y) 拉杆把手, lamp=(x, y))
"""
import math
import numpy as np

STEEL = ['#2a2430', '#4a4050', '#6a6074', '#9a90a4', '#cfc6d6']
BRASS = ['#5a3a10', '#8a5e20', '#c8902e', '#f2c35a', '#fff0b0']

def per_machine(st, x, y, t, on=1.0, gauge=0.0, lever=0.0, label='period'):
    W, H = 92, 62
    x0, y0 = x - W / 2, y - H
    st.mul(st.M_ell(x, y + 1, W * 0.62, 6), 0.5)
    body = st.M_rect(x0, y0, W, H) & ~(st.M_rect(x0, y0, 5, 5) | st.M_rect(x0 + W - 5, y0, 5, 5))
    st.part(body, STEEL, bevel=6, light=(-0.4, -0.7, 0.6), amb=0.35, ink='#0a0810')
    st.rect(x0 + 4, y0 + 4, W - 8, 2, BRASS[2]); st.rect(x0 + 4, y + -6, W - 8, 2, BRASS[1])
    # name plate
    st.rect(x - 24, y0 + 9, 48, 11, '#1a1420'); st.outline(st.M_rect(x - 24, y0 + 9, 48, 11), BRASS[2])
    st.text(x - 20, y0 + 10, label, BRASS[3], 'silkb', 0.4)
    # gears (spin while on)
    ang = t * 2.2 * on
    for gx, gy, r in ((x - 26, y0 + 36, 11), (x - 9, y0 + 44, 7)):
        g = st.M_ell(gx, gy, r, r)
        for k in range(8):
            a = ang * (1 if r > 8 else -1.6) + k * math.pi / 4
            g |= st.M_ell(gx + (r + 1.5) * math.cos(a), gy + (r + 1.5) * math.sin(a), 2.2, 2.2)
        st.part(g, BRASS, bevel=2.5, amb=0.45, ink='#2a1406')
        st.ell(gx, gy, r * 0.35, r * 0.35, BRASS[0])
    # PER gauge
    gx, gy0, gh = x + 10, y0 + 24, 30
    st.rect(gx - 4, gy0 - 2, 12, gh + 4, '#0e0c14'); st.outline(st.M_rect(gx - 4, gy0 - 2, 12, gh + 4), BRASS[1])
    fh = int(round(gh * max(0.0, min(1.0, gauge))))
    if fh > 0: st.rect(gx - 2, gy0 + gh - fh, 8, fh, '#4ad8a0', 0.8); st.rect(gx - 2, gy0 + gh - fh, 8, 1, '#c8fff0', 0.9)
    st.text(gx - 3, gy0 + gh + 3, 'PER', '#8ae8c8', 'silk', 0.5)
    # output chute (right)
    ch = st.M_poly([(x0 + W, y - 26), (x0 + W + 16, y - 18), (x0 + W + 16, y - 8), (x0 + W, y - 12)])
    st.part(ch, STEEL, bevel=2, amb=0.4, ink='#0a0810')
    if on > 0.5 and int(t * 3) % 2 == 0: st.rect(x0 + W + 2, y - 22, 3, 3, '#7affc8', 1.0)
    # lamp on top
    lx, ly = x + 30, y0 - 4
    st.rect(lx - 1, ly + 1, 2, 4, STEEL[1])
    st.part(st.M_ell(lx, ly - 2, 5, 4.5), ['#0a3a1a', '#1a8a3a', '#4ae07a', '#c8ffd8'] if on > 0.5 else ['#1a0808', '#3a1414', '#5a2020', '#7a3030'],
            bevel=2, amb=0.6, ink='#05040a', E=0.95 if on > 0.5 else 0.0)
    # chimney puffs
    st.rect(x - 34, y0 - 10, 7, 10, STEEL[2]); st.rect(x - 35, y0 - 11, 9, 2, STEEL[3])
    if on > 0.5:
        for k in range(3):
            ph = (t * 0.8 + k / 3) % 1
            st.ell(x - 31 + 3 * math.sin(t * 2 + k), y0 - 14 - ph * 20, 2 + 2 * ph, 2 + 2 * ph, (210, 200, 220))
    # big switch lever (left side)
    px, py = x0 - 6, y - 30
    st.rect(px - 5, py - 3, 10, 14, STEEL[1]); st.outline(st.M_rect(px - 5, py - 3, 10, 14), '#0a0810')
    a = math.radians(-50 + 100 * lever)
    hx, hy = px + 18 * math.sin(a) * -1, py - 18 * math.cos(a)
    for w in (-1, 0, 1): st.line(px + w, py, hx + w, hy, STEEL[3])
    st.part(st.M_ell(hx, hy, 4, 4), ['#5a0a0a', '#9a1a1a', '#d83a2a', '#ff7a5a'], bevel=1.5, amb=0.5, ink='#1a0404')
    return dict(out=(x0 + W + 16, y - 12), lever=(hx, hy), lamp=(lx, ly), gauge=(gx, gy0))

def loop_badge(cv, t, t0, x, y, r=34, labels=('夜：攒 PER', '牵手 TIM', '关闸', '昼：分解'), alpha=1.0):
    """UI: a 4-step loop ring that draws itself (≈24 h)."""
    from .. import gameui as G
    from ..core import C
    from ..anim import clamp01
    a = alpha * clamp01((t - t0) / 0.25)
    if a <= 0: return
    G._panel(cv, x - r - 46, y - r - 18, 2 * r + 92, 2 * r + 34, a)
    k = clamp01((t - t0 - 0.2) / 1.4)
    for i in range(int(64 * k)):
        an = -math.pi / 2 + i / 64 * 2 * math.pi
        cv.rect(int(x + r * math.cos(an)), int(y + r * math.sin(an)), 2, 2, (255, 210, 110, int(255 * a)))
    for i, (s_, deg) in enumerate(zip(labels, (-90, 0, 90, 180))):
        if k * 4 > i + 0.3:
            an = math.radians(deg)
            tx, ty = x + (r + 4) * math.cos(an), y + (r + 4) * math.sin(an)
            tw = G.text_width(s_, 'zh10')
            ox = -tw / 2 if deg in (-90, 90) else (2 if deg == 0 else -tw - 2)
            cv.text(int(tx + ox), int(ty - 6), s_, (255, 240, 220, int(255 * a)), 'zh10', outline=(20, 12, 6, int(255 * a)))
    if k >= 1: G.big_zh(cv, '≈24h'.replace('≈', '约'), int(x - 22), int(y - 7), 1, C('#ffd34a'), a)
