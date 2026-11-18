"""pixelkit.characters.worker - 小工（v0.13d）：圆滚滚的「脑细胞 / 细胞小工」，戴安全帽，可以推车、拖地、举卡片、拉闸。

直接画在 pixstage.Stage 上（约 16x20 美术像素，scale 可缩放以配合透视）：
    from pixelkit.characters import worker as W
    W.draw(st, x, y_foot, t, kind='pink', hat='#ffd23a', face='happy', dir=1, walk=True, prop='cart', scale=1.0)
kind:  'pink'（脑细胞，L2）| 'mint'（细胞工厂，L5）| 'blue'（清洁队）
face:  happy | normal | wow | sleepy | sweat
prop:  None | 'cart'（推车，带发光记忆卡）| 'mop' | 'card'（举一张卡片）| 'lever'（双手上举拉闸）| 'towel'（捧着叠好的毛巾）
walk:  True -> 走路循环（身体上下 1px、脚交替）
"""
import math
import numpy as np

BODY = dict(pink=['#7a2a4a', '#b84a6a', '#e87a92', '#ffb0c0', '#ffd8e0'],
            mint=['#1a5a4a', '#2a8a6a', '#4ac8a0', '#8ae8c8', '#c8fff0'],
            blue=['#1a3a6a', '#2a5a9a', '#4a8ad8', '#8ab8f0', '#c8e0ff'],
            lilac=['#3a1a5a', '#6a3a9a', '#9a6ad8', '#c8a0f0', '#ecd8ff'])
INK = '#2a1018'

def draw(st, x, y, t, kind='pink', hat='#ffd23a', face='happy', dir=1, walk=False, prop=None, scale=1.0, phase=0.0, card_col=(255, 230, 140),
         badge=None, hand=None, squash=0.0):
    """hat=None -> no helmet (protein characters).  badge='P' -> letter on the belly.  hand=(hx, hy) -> one arm reaching there
    (hand-holding).  squash>0 flattens (shrinking / dissolving PER)."""
    s = scale
    step = (math.sin((t + phase) * 2 * math.pi * 2.2) if walk else 0.0)
    bob = abs(step) * 1.0 * s
    cx, cy = x, y - 9 * s - bob
    rx, ry = 7.5 * s * (1 + 0.3 * squash), 7.0 * s * (1 - squash)
    # feet
    for i, sg in enumerate((-1, 1)):
        fx = x + sg * 3 * s + (step * 2 * s * (1 if i else -1) * dir if walk else 0)
        st.fill(st.M_ell(fx, y - 1, 2.2 * s, 1.3 * s), '#3a1a20')
    # prop behind
    if prop == 'cart':
        bx = x + dir * 9 * s
        m = st.M_rect(bx - 6 * s if dir > 0 else bx - 6 * s, y - 10 * s, 12 * s, 7 * s)
        st.part(m, ['#3a2410', '#6a4420', '#9a6a30', '#c89a50'], bevel=1.5, amb=0.45, ink='#1a0e06')
        for k in range(3):
            st.rect(bx - 5 * s + k * 4 * s, y - 13 * s - (k % 2), 3 * s, 4 * s, tuple(card_col), 0.9)
        st.fill(st.M_ell(bx - 4 * s, y - 2, 1.6 * s, 1.6 * s) | st.M_ell(bx + 4 * s, y - 2, 1.6 * s, 1.6 * s), '#1a1a1a')
        st.line(x + dir * 5 * s, cy, bx - dir * 5 * s, y - 11 * s, '#5a5a6a')
    if prop == 'mop':
        mx = x + dir * 8 * s
        st.line(mx, y - 22 * s, mx - dir * 3 * s, y - 2, '#c89a50')
        st.fill(st.M_ell(mx - dir * 3 * s, y - 1, 3.5 * s, 1.6 * s), '#e8e4dc')
    body = st.M_ell(cx, cy, rx, ry)
    st.part(body, BODY[kind], bevel=3 * s, light=(-0.5, -0.7, 0.55), amb=0.38, ink=INK)
    # face (looks toward dir)
    ex = cx + dir * 1.5 * s
    ey = cy - 0.5 * s
    for sg in (-1, 1):
        px, py = ex + sg * 2.6 * s, ey
        if face in ('happy',):
            st.px(px - 1, py, INK); st.px(px, py - 1, INK); st.px(px + 1, py, INK)
        elif face == 'sleepy':
            st.line(px - 1, py, px + 1, py, INK)
        elif face == 'wow':
            st.rect(px - 1, py - 1, 2, 3, INK); st.px(px - 1, py - 1, '#ffffff')
        else:
            st.rect(px - 0.5, py - 1, 1.5, 2, INK)
    st.px(ex - 4 * s, ey + 2 * s, '#ff8aa0'); st.px(ex + 4 * s, ey + 2 * s, '#ff8aa0')
    if face == 'wow': st.ell(ex, ey + 3 * s, 1.2 * s, 1.2 * s, INK)
    else: st.line(ex - 1, ey + 2.5 * s, ex + 1, ey + 2.5 * s, INK)
    if hat is None:
        hat_m = None
    # hard hat + headlamp
    if hat is not None:
      hat_m = st.M_ell(cx, cy - ry + 2 * s, rx * 0.95, 4 * s) & (st.yy < cy - ry + 2.5 * s)
      st.part(hat_m, ['#8a5a10', '#c88a1a', hat, '#fff0a0'], bevel=1.5, amb=0.5, ink=INK)
      st.rect(cx - rx, cy - ry + 2 * s, 2 * rx, max(1, s), '#8a5a10')
      st.ell(cx + dir * 4 * s, cy - ry + 0.5 * s, 1.2 * s, 1.2 * s, '#fff8d0', 1.0)
    if badge:
      st.text(cx - 3, cy + 1, badge, '#ffffff', 'silkb')
    if hand is not None:
      for w_ in (0, 1):
        st.line(cx + dir * rx * 0.8, cy + 2 * s + w_, hand[0], hand[1] + w_, BODY[kind][3])
    # front props
    if prop == 'card':
        st.rect(cx - 4 * s, cy - ry - 9 * s, 8 * s, 6 * s, tuple(card_col), 0.95)
        st.line(cx - 4 * s, cy - ry - 3 * s, cx - 6 * s, cy - 2 * s, BODY[kind][2]); st.line(cx + 4 * s, cy - ry - 3 * s, cx + 6 * s, cy - 2 * s, BODY[kind][2])
    if prop == 'lever':
        st.line(cx - 5 * s, cy - 2 * s, cx - 3 * s, cy - ry - 5 * s, BODY[kind][2]); st.line(cx + 5 * s, cy - 2 * s, cx + 3 * s, cy - ry - 5 * s, BODY[kind][2])
    if prop == 'towel':
        m = st.M_rect(cx - 5 * s, cy, 10 * s, 4 * s); st.part(m, ['#8a8aa0', '#c8c8dc', '#f0f0fa'], bevel=1, amb=0.5, ink='#3a3a4a')
    if face == 'sweat':
        st.rect(cx + rx, cy - ry + 3 * s, 1.5 * s, 2 * s, '#8ad0ff')
    return (cx, cy - ry - 2 * s)            # head-top (for UI fx)
