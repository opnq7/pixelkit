"""pixelkit.characters.cat - 小橘猫（v0.13，320 舞台尺寸，直接画在 pixstage.Stage 上）。

    from pixelkit.characters import cat
    cat.draw(st, x, y, pose='curl', t=t, look=(0, 0), blink=False)
pose:  'curl'   蜷成一团睡觉（呼吸起伏，尾巴偶尔甩）
       'up'     抬头（耳朵竖起，眼睛睁开，会盯着 look 方向）
       'puff'   炸毛（毛轮廓变锯齿、尾巴竖起、瞳孔变细）
(x, y) = 身体底部中心（贴着床面 / 地面）。约 28 x 18 像素。
"""
import math
import numpy as np

FUR = ['#5a2a14', '#94451c', '#c86a2a', '#e8924a', '#f6b874']
CREAM = '#f8e2c0'
INK = '#1c0e0a'

def draw(st, x, y, pose='curl', t=0.0, look=(0, 0), blink=False, tail=None, alpha=1.0):
    br = 0.5 + 0.5 * math.sin(t * 2 * math.pi / 3.2)            # breathing 0..1
    puff = pose == 'puff'
    up = pose in ('up', 'puff')
    # ---- body (a loaf / donut)
    ry = 7.0 + (0.6 * br if pose == 'curl' else 0) + (1.4 if puff else 0)
    rx = 12.5 + (1.5 if puff else 0)
    body = st.M_ell(x, y - ry, rx, ry)
    if puff:      # jagged fur edge
        ang = np.arctan2(st.yy + .5 - (y - ry), st.xx + .5 - x)
        jag = st.M_ell(x, y - ry, rx + 1.6, ry + 1.6) & (np.sin(ang * 14) > 0.1)
        body = body | jag
    body &= st.yy < y
    st.part(body, FUR, bevel=4, light=(-0.4, -0.7, 0.6), amb=0.35, ink=INK)
    # stripes
    for k in (-6, -1, 4):
        st.line(x + k, y - 2 * ry + 1, x + k + 2, y - 2 * ry + 5, FUR[1], mask=body)
    # ---- tail
    if tail is None: tail = 0.5 + 0.5 * math.sin(t * 1.3) if not up else 1.0
    if puff:
        pts = [(x + rx - 2, y - 3), (x + rx + 3, y - 8), (x + rx + 4, y - 16), (x + rx + 3, y - 22)]
    else:
        sw = 3.0 * math.sin(t * 2.6) * tail
        pts = [(x + rx - 3, y - 2), (x + rx + 1, y - 1), (x + 2, y + 1 + 0.4 * sw), (x - 7 + sw, y + 0.5)]
    for (a, b) in zip(pts, pts[1:]):
        for w in range(-1, 2 if puff else 1):
            st.line(a[0] + w, a[1], b[0] + w, b[1], FUR[2])
    st.px(pts[-1][0], pts[-1][1], CREAM)
    # ---- head
    if up:
        hx, hy = x - 8 + look[0] * 0.5, y - 2 * ry - 1 + look[1] * 0.4
    else:
        hx, hy = x - 7, y - ry * 0.9 + 0.5 * br
    hm = st.M_ell(hx, hy, 6.5, 5.2)
    ears = st.M_poly([(hx - 6, hy - 2), (hx - 5, hy - 9 if up else hy - 7), (hx - 1, hy - 4)]) | \
           st.M_poly([(hx + 6, hy - 2), (hx + 5, hy - 9 if up else hy - 7), (hx + 1, hy - 4)])
    st.part(hm | ears, FUR, bevel=3, light=(-0.4, -0.7, 0.6), amb=0.38, ink=INK)
    st.px(hx - 5, hy - 6 if up else hy - 4, '#e88a8a'); st.px(hx + 5, hy - 6 if up else hy - 4, '#e88a8a')
    st.fill(st.M_ell(hx, hy + 2.5, 3.2, 2.0), CREAM)
    if up and not blink:
        ex = look[0] * 0.4
        for sx in (-2.6, 2.6):
            st.rect(hx + sx - 1 + ex, hy - 1, 2, 2 if not puff else 3, '#f4e870', 0.9)
            st.px(hx + sx + ex - (0 if puff else 0), hy - 1 + (1 if puff else 0), INK)
    else:
        for sx in (-2.6, 2.6): st.line(hx + sx - 1, hy, hx + sx + 1, hy, INK)
    st.px(hx, hy + 1, '#e86a7a')
    if puff:   # whiskers out
        for s in (-1, 1):
            st.line(hx + s * 3, hy + 2, hx + s * 9, hy, '#f8f0e0'); st.line(hx + s * 3, hy + 3, hx + s * 9, hy + 4, '#f8f0e0')
    return (hx, hy)
