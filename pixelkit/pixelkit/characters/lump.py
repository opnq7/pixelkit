"""pixelkit.characters.lump - 被子里睡着的人（v0.13e）：贴合任意床透视的「被子鼓包 + 枕头上一撮头发（+ 睡帽）」。

正脸大头贴在侧面的床上会穿模（第 4 关 v2 的教训）；睡着的人一律用这个：
    from pixelkit.characters import lump
    lump.draw(st, head=(38, 90), foot=(118, 100), t=t, width=9, blanket=lump.BLUE, hair='#2a2228', cap=True)
head / foot = 床面上头和脚的位置（美术像素），width = 身体厚度。身体随呼吸起伏；cap=True 戴小魂的睡帽（附身标记）。
返回头顶位置（画 zZ 用）。actor 掩码会自动登记，Plate.light 会按场景光重新打光。
"""
import math
import numpy as np

BLUE = ['#1a2440', '#2a3a62', '#3e5288', '#5a70a8', '#7a90c8']
PLAID = ['#1a3a2a', '#2a5a3e', '#3e7a52', '#5a9a6a', '#8ac090']
STRIPE = ['#1a2a4a', '#2a3e6a', '#4a5e8a', '#7a8ab0', '#c8d0e0']

def draw(st, head, foot, t=0.0, width=9.0, blanket=BLUE, hair='#2a2228', cap=True, breath=True, face='sleep', facing=-1, head_s=None):
    """v0.13f: the head is a real sleeping profile (characters.sleep_head) on the pillow, the blanket tucks under the chin."""
    from . import sleep_head as SH
    before = st.img.copy()
    hx, hy = head; fx, fy = foot
    br = (0.6 + 0.6 * math.sin(t * 2 * math.pi / 3.8)) if breath else 0.0
    m = np.zeros((st.H, st.W), bool)
    n = 18
    for i in range(n + 1):
        u = i / n
        x = hx + (fx - hx) * (0.12 + 0.88 * u); y = hy + (fy - hy) * (0.12 + 0.88 * u)
        w = width * (0.75 + 0.35 * math.sin(math.pi * min(1, u * 1.3))) + (br * 0.8 if 0.2 < u < 0.6 else 0)
        m |= st.M_ell(x, y - w * 0.45, w * 0.9, w * 0.62)
    hs = head_s or width / 11.0 * 0.95
    m &= ~st.M_ell(hx, hy - width * 0.3, 11 * hs * 0.9, 11 * hs * 0.6)        # leave room for the face
    st.part(m, blanket, bevel=max(2.0, width * 0.45), light=(-0.4, -0.8, 0.5), amb=0.35, ink='#0a0a14')
    st.line(hx + (fx - hx) * 0.15, hy + (fy - hy) * 0.15 - width * 0.4, fx, fy - width * 0.4, blanket[1], mask=m)
    top = SH.draw(st, hx, hy - width * 0.45, t, s=hs, hair=hair, cap=cap, face=face, facing=facing)
    # blanket edge over the chin
    st.part(st.M_ell(hx + (fx - hx) * 0.12, hy + width * 0.15, 9 * hs, 4 * hs), blanket, bevel=2, light=(-0.4, -0.8, 0.5), amb=0.4, ink='#0a0a14')
    st.rect(hx + (fx - hx) * 0.12 - 8 * hs, hy + width * 0.15 - 4 * hs, 16 * hs, max(1, hs), '#e8e4f0')
    if getattr(st, 'act', None) is None: st.act = np.zeros((st.H, st.W), bool)
    st.act |= (st.img != before).any(-1)
    return top
