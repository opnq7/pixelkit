"""pixelkit.sets.cells - 「细胞」画面（v0.13g，第 4 关结尾 / 第 5 关）：一片有体积、会随心跳鼓动的细胞，每个细胞核里一只小钟。

    from pixelkit.sets.cells import cells_stage
    st = cells_stage(t, beat=0..1, chaos=0..1, phone=0..1, cols=10, rows=8, r=15)
    img = st.render(cam(1.0), st.light_base(...), GRADE_NIGHT)
chaos: 每只钟的指针各转各的、细胞轻微抖动；phone: 右侧手机蓝光漫进来（冷色光池）。
"""
import math
import numpy as np
from ..pixstage import Stage

CELL = ['#5a1a34', '#8a3050', '#c05a78', '#e88aa0', '#ffc0cc']
NUC = ['#3a0a24', '#6a2050', '#9a4070']

def cells_stage(t, beat=0.0, chaos=0.0, cols=10, rows=8, r=15, seed=5, W=320, H=180, sync=True):
    s = Stage(W, H); s.img[..., :3] = (58, 16, 34); s.E[:] = 0
    rng = np.random.default_rng(seed)
    dx, dy = W / (cols - 1.5), H / (rows - 1.5)
    for j in range(-1, rows):
        for i in range(-1, cols):
            jx = chaos * 2.5 * math.sin(t * 23 + i * 3.1 + j * 1.7)
            jy = chaos * 2.0 * math.cos(t * 19 + i * 1.3 + j * 2.9)
            cx = i * dx + (dx / 2 if j % 2 else 0) + rng.uniform(-4, 4) + jx
            cy = j * dy + rng.uniform(-3, 3) + jy
            rr = r + 1.2 * beat
            m = s.M_ell(cx, cy, rr, rr * 0.82)
            s.part(m, CELL, bevel=6, light=(-0.4, -0.7, 0.6), amb=0.35, ink='#2a0816')
            s.part(s.M_ell(cx + 2, cy + 1, 6, 5), NUC, bevel=2, amb=0.4, ink='#1a0410')
            s.ell(cx + 2, cy + 1, 3.2, 3.2, '#ffe8c0', 0.6)
            ph = rng.uniform(0, 6.28)
            ang = (t * 2.4 if sync else 0) * (1 - chaos) + chaos * (t * rng.uniform(-14, 14) + ph) + (0 if sync else ph)
            s.line(cx + 2, cy + 1, cx + 2 + 2.6 * math.cos(ang), cy + 1 + 2.6 * math.sin(ang), '#3a0a10')
    return s
