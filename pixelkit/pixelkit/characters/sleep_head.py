"""pixelkit.characters.sleep_head - 枕头上睡着的头（v0.13f，侧脸，和 chibi 角色同一画风：圆头、闭眼弧线、腮红）。

    from pixelkit.characters import sleep_head as SH
    SH.draw(st, x, y, t, s=1.0, hair='#2a2228', skin=SKIN, cap=True, face='sleep'|'drool'|'frown', facing=-1)
(x, y) = 头的中心（枕头上），s = 缩放（头直径约 22*s 美术像素），facing=-1 脸朝左 / +1 朝右。
配 lump.draw(head_at_pillow=False) 用：先画被子身体，再画这个头压在枕头上，最后被沿盖住下巴。
"""
import math
SKIN = ['#7a4434', '#b06a4c', '#d8906a', '#f0b48a', '#fcd2aa']

def draw(st, x, y, t, s=1.0, hair='#2a2228', skin=SKIN, cap=True, face='sleep', facing=-1):
    r = 11 * s
    br = 0.6 * math.sin(t * 2 * math.pi / 3.8)
    y = y + br * 0.4
    head = st.M_ell(x, y, r, r * 0.92)
    st.part(head, skin, bevel=4 * s, light=(-0.3, -0.8, 0.5), amb=0.38, ink='#3a1a10')
    # 3/4 face toward the camera: hair only on the top + the back side, both eyes visible (reads at any size)
    hm = (st.M_ell(x - facing * 1.5 * s, y - r * 0.45, r * 1.04, r * 0.62) & (st.yy < y - r * 0.05)) | \
         st.M_ell(x - facing * r * 0.75, y - r * 0.1, r * 0.42, r * 0.7)
    st.part(hm & head | (hm & st.M_ell(x, y - 2 * s, r + 1.5 * s, r)), ['#0c0a10', '#1a1620', hair, '#4a4058'], bevel=3 * s,
            light=(-0.3, -0.8, 0.5), amb=0.25, ink='#05040a')
    for k in range(3):                                                                   # fringe tufts
        st.fill(st.M_poly([(x + facing * (k * 4 - 2) * s, y - r * 0.2), (x + facing * (k * 4 + 2) * s, y - r * 0.2),
                           (x + facing * (k * 4 + 1) * s, y + 1.5 * s)]), hair)
    ey = y + 2.5 * s
    for ex in (x + facing * 1 * s, x + facing * 7.5 * s):
        if face in ('sleep', 'drool'):
            for k in range(-2, 3): st.px(ex + k * 0.8 * s, ey - (2 - abs(k)) * 0.5 * s, '#2a1210')
        else:
            st.line(ex - 2 * s, ey, ex + 2 * s, ey, '#2a1210')
        st.fill(st.M_ell(ex, ey + 3 * s, 2.2 * s, 1.1 * s), '#f08a80')
    mx = x + facing * 4.5 * s
    st.line(mx - 1 * s, y + 7.5 * s, mx + 1 * s, y + 7.5 * s, '#7a3a30')
    if face == 'drool':
        st.line(mx + facing * 1.5 * s, y + 8 * s, mx + facing * 1.5 * s, y + 11 * s, '#bfe6ff', 0.3)
    if cap:   # the ghost's star night-cap, flopping onto the pillow behind the head
        cx, cy = x - facing * 3 * s, y - r * 0.75
        st.poly([(cx - 8 * s, cy + 3 * s), (cx + 6 * s, cy + 2 * s), (cx - facing * 14 * s, cy + 9 * s)], '#3a4ca8')
        st.poly([(cx - 8 * s, cy + 3 * s), (cx + 6 * s, cy + 2 * s), (cx + 4 * s, cy - 3 * s), (cx - 6 * s, cy - 2 * s)], '#4c63c9')
        st.rect(cx - 8 * s, cy + 2 * s, 14 * s, 2 * s, '#f5ead2')
        st.ell(cx - facing * 14 * s, cy + 9 * s, 2 * s, 2 * s, '#ffd85a', 0.5)
        st.px(cx - 2 * s, cy - 1 * s, '#ffd85a', 0.6)
    return (x, y - r)
