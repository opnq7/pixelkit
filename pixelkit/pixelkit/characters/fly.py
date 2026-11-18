"""pixelkit.characters.fly - 果蝇（v0.13，320 舞台尺寸，直接画在 Stage 上）。

    from pixelkit.characters import fly
    fly.draw(st, x, y, t, scale=1.0, mood='normal'|'sleep'|'hyper'|'sleepy'|'dizzy', cap=False, dir=1)
约 12x8 像素（scale=1）。红眼睛、棕黄身体、半透明翅膀会扇；sleep 带小睡帽 + 闭眼。
"""
import math

def draw(st, x, y, t, scale=1.0, mood='normal', cap=False, dir=1, wing=True):
    s = scale
    buzz = mood in ('hyper', 'normal', 'dizzy')
    # wings
    if wing:
        fl = (math.sin(t * (60 if mood == 'hyper' else 30)) if buzz else 0.2)
        for sg in (-1, 1):
            wy = y - 4 * s - 2 * s * abs(fl)
            st.fill(st.M_ell(x - dir * 2 * s + sg * 1.5 * s, wy, 4.5 * s, 2.2 * s), (210, 230, 245), 0.25)
    # body: abdomen stripes + thorax
    ab = st.M_ell(x - dir * 3 * s, y, 4.5 * s, 3.0 * s)
    st.part(ab, ['#5a3a10', '#9a6a2a', '#c89a50', '#e8c880'], bevel=1.5, amb=0.45, ink='#2a1406')
    for k in (-1, 1): st.line(x - dir * (3 + k * 1.5) * s, y - 2.5 * s, x - dir * (3 + k * 1.5) * s, y + 2.5 * s, '#5a3a10', mask=ab)
    th = st.M_ell(x + dir * 1.5 * s, y - 0.5 * s, 2.8 * s, 2.5 * s)
    st.part(th, ['#5a3a10', '#9a6a2a', '#c89a50'], bevel=1.2, amb=0.45, ink='#2a1406')
    # head + red eyes
    hx = x + dir * 4.2 * s
    st.fill(st.M_ell(hx, y - 0.5 * s, 2.2 * s, 2.0 * s), '#b08040')
    if mood in ('sleep', 'sleepy'):
        st.line(hx - 1 * s, y - 1 * s, hx + 1.2 * s, y - 1 * s, '#3a0a0a')
    else:
        st.fill(st.M_ell(hx + dir * 0.6 * s, y - 1 * s, 1.4 * s, 1.4 * s), '#e0202a', 0.6 if mood != 'dizzy' else 0.3)
        st.px(hx + dir * 0.9 * s, y - 1.5 * s, '#ffb0b0')
    # legs
    for k in (-1, 0, 1): st.line(x + k * 1.5 * s, y + 2 * s, x + k * 2 * s - dir * s, y + 4 * s, '#3a2410')
    if cap:
        st.poly([(hx - 2 * s, y - 2 * s), (hx + 2 * s, y - 2 * s), (hx + 3.5 * s, y - 5.5 * s)], '#3a4ca8')
        st.px(hx + 3.5 * s, y - 5.5 * s, '#ffd85a', 0.6); st.rect(hx - 2 * s, y - 2.5 * s, 4 * s, max(1, s * 0.8), '#f5ead2')
