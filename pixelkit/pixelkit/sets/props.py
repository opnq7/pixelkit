"""pixelkit.sets.props - procedural pixel-art props (each returns a scene.Sprite: rgba + emissive).

Conventions: light comes from the upper-left (sun side) for painted form shading; keep albedo
mid-range (the light rig adds the drama); finish sprites with core.sel_out for coloured outlines.
"""
import functools, math
import numpy as np
from ..core import Canvas, C, mix, text_mask, text_width, sel_out, sprite
from ..palette import ramp
from ..scene import Sprite

@functools.lru_cache(maxsize=256)
def R(base, n=6, **kw):
    return tuple(ramp(base, n, **kw))

def _sp(w, h):
    return Sprite(w, h)

def box(cv, x, y, w, h, rp, outline=True, bevel=1):
    """beveled box: rp = ramp (dark->light, >=5 entries)."""
    o = 1 if outline else 0
    if outline: cv.rect(x, y, w, h, rp[0])
    cv.rect(x + o, y + o, w - 2 * o, h - 2 * o, rp[3])
    for i in range(bevel):
        cv.hline(x + o + i, y + o + i, w - 2 * o - 2 * i, rp[4]); cv.vline(x + o + i, y + o + i, h - 2 * o - 2 * i, rp[4])
        cv.hline(x + o + i, y + h - o - 1 - i, w - 2 * o - 2 * i, rp[2]); cv.vline(x + w - o - 1 - i, y + o + i, h - 2 * o - 2 * i, rp[2])
    cv.px(x + o, y + o, rp[5] if len(rp) > 5 else rp[4])

def text(cv, x, y, s, col, fname='zh8', shadow=None):
    return cv.text(x, y, s, col, fname, shadow=shadow)

# --------------------------------------------------------------------------- windows
SKIES = {   # (top, mid, low) sky colours of the window views per time of day
    'morning': ('#78a8e8', '#bcd8f0', '#fff0d0'),
    'golden': ('#7f8fd6', '#d8a7c8', '#ffc59a'),
    'late':   ('#7584cf', '#df9fb8', '#ffb98a'),
    'sunset': ('#5f63b8', '#e28aa0', '#ffa264'),
    'dusk':   ('#2f3570', '#7a5a96', '#e0907a'),
    'night':  ('#0e1430', '#1f2652', '#4a3f74'),
}

def city_view(w, h, seed=3, sky_top='#7f8fd6', sky_mid='#d8a7c8', sky_low='#ffc59a', sun_side='left', tod=None):
    """view out of a window: gradient sky, layered city blocks lit from the sun side, tiny windows.
    tod: 'golden' | 'late' | 'sunset' | 'dusk' | 'night' picks the sky preset (night = dark city, many lit windows,
    a few stars, emissive sky glow)."""
    if tod is not None: sky_top, sky_mid, sky_low = SKIES[tod]
    night = tod in ('night', 'dusk')
    s = _sp(w, h); cv = s.cv
    rng = np.random.default_rng(seed)
    top, mid, low = C(sky_top), C(sky_mid), C(sky_low)
    for yy in range(h):
        k = yy / max(1, h - 1)
        c = mix(top, mid, min(1, k / 0.55)) if k < 0.55 else mix(mid, low, (k - 0.55) / 0.45)
        cv.hline(0, yy, w, c)
    if not night:
        for i in range(3):          # a few soft clouds
            cx, cy = rng.uniform(0, w), rng.uniform(h * 0.12, h * 0.45)
            for j in range(3):
                cv.ellipse(cx + j * 4 - 4, cy + (j % 2), 5 + j, 1.6, mix(C('#ffffff' if tod == 'morning' else '#ffe3d0'), mid, 0.35))
        s.E[:] = 0.92
    else:
        s.E[:] = 0.55
        for i in range(int(w * h / 260)):          # stars
            x, y = int(rng.integers(0, w)), int(rng.integers(0, int(h * 0.45)))
            cv.px(x, y, C('#dfe6ff') if rng.random() < 0.7 else C('#ffe9c0')); s.E[y, x] = 1.0
        cv.ellipse(w * 0.78, h * 0.16, 2.6, 2.6, C('#fff6dc'))     # moon
        cv.ellipse(w * 0.78 + 1.2, h * 0.16 - 0.6, 2.0, 2.0, top)
        yy, xx = np.mgrid[0:h, 0:w]; s.E[((xx - w * 0.78) ** 2 + (yy - h * 0.16) ** 2) < 8] = 1.0
    # far buildings (cool silhouette), near buildings (warmer, lit left faces)
    if tod == 'morning':     # v0.8: clear morning - pale blue-grey blocks, cream sunlit faces, glass glints
        layers = [(0.50, '#a9b8d8', '#dfe6f2', 0.60), (0.62, '#8494b8', '#f2e8d8', 0.50), (0.76, '#66729a', '#fff0d8', 0.42)]
        win_p, win_cols = 0.16, ('#e8f4ff', '#fff6dc')
    elif not night:
        layers = [(0.50, '#7d74a8', '#a68fc0', 0.55), (0.62, '#5d557f', '#d99a86', 0.45), (0.76, '#433b5f', '#f0a272', 0.35)]
        win_p, win_cols = 0.28, ('#ffd88a', '#fff1c9')
    else:
        layers = [(0.50, '#262a50', '#2e3360', 0.30), (0.62, '#1b1e3e', '#23274a', 0.22), (0.76, '#121430', '#181a3a', 0.16)]
        win_p, win_cols = 0.42, ('#ffd27a', '#bfe2ff')
    for li, (base_y, dark, lit, e) in enumerate(layers):
        x = -rng.integers(0, 6)
        while x < w:
            bw = int(rng.integers(7, 14)); bh = int(h * rng.uniform(0.18, 0.42) + li * 3)
            by = int(h * base_y + rng.integers(-4, 5)) - bh // 3
            cv.rect(x, by, bw, h - by, C(dark))
            if sun_side == 'left' and not night: cv.rect(x, by, 2, h - by, C(lit))
            cv.hline(x, by, bw, mix(C(lit), C(dark), 0.3))
            if night and rng.random() < 0.25:                    # rooftop beacon
                cv.px(x + bw // 2, by - 1, C('#ff6a5a'))
            if night: s.E[max(0, by):h, max(0, x):min(w, x + bw)] = e
            for wy in range(by + 3, h - 2, 4):
                for wx in range(x + 3, x + bw - 1, 3):
                    if rng.random() < win_p:
                        cv.px(wx, wy, C(win_cols[0]) if rng.random() < 0.7 else C(win_cols[1]))
                        if 0 <= wx < w: s.E[wy % h, wx] = 1.0
            if not night:       # daytime: the whole block (windows included) glows at most e
                sl = (slice(max(0, by), h), slice(max(0, x), min(w, x + bw)))
                s.E[sl] = np.minimum(s.E[sl], e)
            if night and rng.random() < 0.25 and by > 0:
                s.E[max(0, by - 1), max(0, min(w - 1, x + bw // 2))] = 1.0
            x += bw + int(rng.integers(0, 3))
    return s

def window_back(w=70, h=70, frame='#e8e2d8', seed=3, tod=None):
    """framed window on the back wall (4 panes) with city view and a sill. tod: sky preset (see SKIES)."""
    s = _sp(w, h + 6); cv = s.cv
    view = city_view(w - 6, h - 6, seed, tod=tod)
    cv.blit(view.rgba, 3, 3); s.E[3:3 + h - 6, 3:3 + w - 6] = view.E
    fr = R(frame, 6)
    for (x, y, ww, hh) in [(0, 0, w, 3), (0, h - 3, w, 3), (0, 0, 3, h), (w - 3, 0, 3, h), (w // 2 - 1, 0, 3, h), (0, h // 2 - 1, w, 2)]:
        cv.rect(x, y, ww, hh, fr[3]); s.E[y:y + hh, x:x + ww] = 0
    cv.hline(0, 0, w, fr[5]); cv.vline(0, 0, h, fr[4]); cv.hline(3, h // 2 + 1, w - 6, fr[2]); cv.vline(w // 2 + 1, 3, h - 6, fr[2])
    cv.hline(3, 3, w - 6, mix(fr[1], C('#000000'), 0.0)); s.E[3, 3:w - 3] = 0.2
    # sill
    sl = R('#ddd6cc', 6)
    cv.rect(-2 + 2, h, w, 2, sl[4]); cv.rect(2, h + 2, w - 4, 3, sl[2]); cv.hline(0, h, w, sl[5])
    s.E[h:, :] = 0
    return s

def blinds_window_side(room, win, slat='#f1e0c4', sky='#fff1cf', frame='#e3dccf', e_sky=1.0, e_slat=0.55, warm=0.15):
    """paints the left/right wall window (frame + venetian blinds, bright sky in the gaps) directly as
    full-canvas arrays: returns (rgba, E, mask) in canvas space using the room projection."""
    W, H = room.W, room.H
    S = room.surfaces(1)
    Z, Y, sid = S['Z'], S['Y'], S['id']
    m = (sid == win.wall) & (Z >= win.a0) & (Z <= win.a1) & (Y >= win.b0) & (Y <= win.b1)
    rgba = np.zeros((H, W, 4), np.uint8); E = np.zeros((H, W), np.float32)
    bl = win.blinds or {}
    p = bl.get('period', 5.0); o = bl.get('open', 0.5)
    ph = np.mod((Y - bl.get('top', win.b0)) / p, 1.0)
    gap = ph < o
    skyc = np.array(C(sky)); slc = np.array(C(slat)); sl_d = np.array(R(slat, 6)[2]); fr = R(frame, 6)
    # sky: brighter at the top
    k = np.clip((Y - win.b0) / (win.b1 - win.b0), 0, 1)[..., None]
    sky_px = (skyc[:3] * (1 - warm * k) + np.array([255, 170, 110]) * warm * k).astype(np.uint8)
    rgba[m & gap, :3] = sky_px[m & gap]; E[m & gap] = e_sky
    sl = m & ~gap
    edge = sl & (ph < o + (1 - o) * 0.35)
    rgba[sl, :3] = slc[:3]; rgba[edge, :3] = sl_d[:3]
    E[sl] = e_slat; E[edge] = e_slat * 0.64
    rgba[m, 3] = 255
    # frame + mullions
    fm = (sid == win.wall) & (Z >= win.a0 - 3) & (Z <= win.a1 + 3) & (Y >= win.b0 - 3) & (Y <= win.b1 + 4) & ~m
    for mz in win.mullions:
        fm |= m & (np.abs(Z - mz) < win.mull_w / 2 + 0.5)
    rgba[fm] = fr[4]; E[fm] = 0.0
    sill = (sid == win.wall) & (Z >= win.a0 - 4) & (Z <= win.a1 + 4) & (Y > win.b1 + 1.5) & (Y <= win.b1 + 5)
    rgba[sill] = fr[3]
    rgba[(sid == win.wall) & (Z >= win.a0 - 4) & (Z <= win.a1 + 4) & (Y > win.b1 + 4) & (Y <= win.b1 + 5)] = fr[1]
    return rgba, E, (m | fm | sill)

# --------------------------------------------------------------------------- wall items
def banner(textstr='全年无休 · 随叫随到', col='#c83a3a', txt='#ffd76a', pad=6):
    tw = text_width(textstr, 'zh8')
    w, h = tw + pad * 2, 14
    s = _sp(w, h + 6); cv = s.cv
    rp = R(col, 6)
    cv.rect(0, 5, w, h, rp[0]); cv.rect(1, 6, w - 2, h - 2, rp[3])
    cv.hline(1, 6, w - 2, rp[4]); cv.hline(1, 5 + h - 2, w - 2, rp[2])
    # fabric sag + folds
    for x in range(4, w - 4, 9): cv.vline(x, 7, h - 4, rp[2])
    cv.text(pad, 7, textstr, C(txt), 'zh8', shadow=rp[1])
    # strings
    cv.line(2, 5, 6, 0, C('#5a4a40')); cv.line(w - 3, 5, w - 7, 0, C('#5a4a40'))
    return s

def wall_clock(r=12, hh=16, mm=30, ss=None):
    d = 2 * r + 3
    s = _sp(d, d); cv = s.cv
    c = r + 1
    cv.ellipse(c, c, r + 0.5, r + 0.5, C('#2f2a3a'))
    cv.ellipse(c, c, r - 0.6, r - 0.6, C('#f5f0e6'))
    cv.ellipse(c - 2, c - 2, r - 4, r - 4, C('#fffaf2'))
    for k in range(12):
        a = k / 12 * 2 * math.pi
        L = 2 if k % 3 == 0 else 1
        for q in range(L):
            x = c + math.sin(a) * (r - 2 - q); y = c - math.cos(a) * (r - 2 - q)
            cv.px(int(round(x)), int(round(y)), C('#3a3346'))
    ha = ((hh % 12) + mm / 60) / 12 * 2 * math.pi; ma = mm / 60 * 2 * math.pi
    for (a, L, col) in [(ha, r * 0.5, C('#2a2433')), (ma, r * 0.78, C('#2a2433'))]:
        cv.line(c, c, int(round(c + math.sin(a) * L)), int(round(c - math.cos(a) * L)), col)
    if ss is not None:
        a = ss / 60 * 2 * math.pi
        cv.line(c, c, int(round(c + math.sin(a) * (r - 2))), int(round(c - math.cos(a) * (r - 2))), C('#d8453a'))
    cv.px(c, c, C('#d8453a'))
    return s

def calendar(month='10月', day_mark=(4, 2), w=30, h=34):
    s = _sp(w, h + 3); cv = s.cv
    cv.rect(0, 2, w, h, C('#3a3040')); cv.rect(1, 3, w - 2, h - 2, C('#f7f2ea'))
    cv.rect(1, 3, w - 2, 9, C('#d64a3f')); cv.hline(1, 3, w - 2, C('#ee7a66'))
    cv.text(3, 3, month, C('#fff6e8'), 'zh8')
    for j in range(4):
        for i in range(7):
            x, y = 3 + i * 3 + (i > 0) * 0, 15 + j * 4
            cv.rect(2 + i * 4, 15 + j * 4, 2, 2, C('#9a8f86') if i < 5 else C('#d6726a'))
    i, j = day_mark
    cv.rect(1 + i * 4, 14 + j * 4, 4, 4, C('#d64a3f'))
    for x in (6, w - 7): cv.rect(x, 0, 2, 4, C('#5b5560'))
    return s

def exit_sign(label='EXIT', w=26, h=10):
    s = _sp(w, h); cv = s.cv
    cv.rect(0, 0, w, h, C('#1f3a2a')); cv.rect(1, 1, w - 2, h - 2, C('#36d17a'))
    cv.text(4, 0, label, C('#f2fff6'), 'silkb')
    s.E[1:h - 1, 1:w - 1] = 1.0
    return s

def sticky(col='#f6d860', w=9, h=9, lines=2, seed=0):
    s = _sp(w, h); cv = s.cv
    rp = R(col, 6)
    cv.rect(0, 0, w, h, rp[3]); cv.hline(0, 0, w, rp[4]); cv.vline(w - 1, 1, h - 1, rp[2]); cv.hline(1, h - 1, w - 1, rp[2])
    rng = np.random.default_rng(seed)
    for k in range(lines):
        L = int(rng.integers(3, w - 2)); cv.hline(2, 3 + k * 2, L, rp[1])
    return s

def kpi_chart(w=34, h=28):
    s = _sp(w, h); cv = s.cv
    cv.rect(0, 0, w, h, C('#4a4250')); cv.rect(1, 1, w - 2, h - 2, C('#f7f3ec'))
    cv.text(3, 1, 'KPI', C('#2f5fb8'), 'silkb')
    bars = [5, 8, 7, 11, 14, 18]
    cols = ['#5c8fe0', '#5c8fe0', '#5c8fe0', '#5c8fe0', '#e0a03c', '#e0503c']
    for i, (bh, c) in enumerate(zip(bars, cols)):
        x = 4 + i * 5; cv.rect(x, h - 3 - bh, 3, bh, C(c)); cv.vline(x, h - 3 - bh, bh, mix(C(c), C('#ffffff'), 0.35))
    cv.hline(3, h - 3, w - 6, C('#6a6070'))
    cv.line(5, h - 9, w - 6, 5, C('#d63a2f')); cv.px(w - 6, 4, C('#d63a2f')); cv.px(w - 7, 4, C('#d63a2f')); cv.px(w - 6, 6, C('#d63a2f'))
    return s

def postcard_river(w=20, h=14):
    """foreshadow: a postcard of a river (Act 4)."""
    s = _sp(w, h + 2); cv = s.cv
    cv.rect(0, 2, w, h, C('#f4efe6'))
    ix, iy, iw, ih = 1, 3, w - 2, h - 2
    for yy in range(ih):
        k = yy / ih
        cv.hline(ix, iy + yy, iw, mix(C('#9fc3ef'), C('#ffd3a8'), min(1, k * 1.4)))
    cv.rect(ix, iy + ih // 2, iw, ih - ih // 2, C('#6fae6a'))
    cv.poly([(ix, iy + ih - 1), (ix + iw * 0.45, iy + ih // 2 + 1), (ix + iw * 0.6, iy + ih // 2 + 1), (ix + iw * 0.7, iy + ih - 1)], C('#5aa0d8'))
    cv.hline(int(ix + iw * 0.5), iy + ih // 2 + 2, 2, C('#bfe6ff'))
    cv.px(ix + 3, iy + ih // 2 - 1, C('#3e7e46')); cv.px(ix + 4, iy + ih // 2 - 2, C('#3e7e46'))
    # pushpin
    cv.rect(w // 2 - 1, 0, 3, 3, C('#d8453a')); cv.px(w // 2 - 1, 0, C('#ff8a7a'))
    return s

def poster_best(w=34, h=34, claude_face=True):
    """'本月最佳' (employee of the month) poster with a tiny Claude portrait."""
    s = _sp(w, h); cv = s.cv
    cv.rect(0, 0, w, h, C('#5a4636')); cv.rect(1, 1, w - 2, h - 2, C('#c79a52')); cv.rect(2, 2, w - 4, h - 4, C('#fbf6ec'))
    cv.rect(2, 2, w - 4, 10, C('#d6463c')); cv.hline(2, 2, w - 4, C('#f07a66'))
    tw = text_width('本月最佳', 'zh8')
    cv.text((w - tw) // 2, 2, '本月最佳', C('#ffe9a8'), 'zh8')
    # portrait: mini Claude head
    hx, hy = w // 2 - 7, 15
    cv.rrect(hx, hy, 14, 11, C('#3a2f3f'), 2); cv.rrect(hx + 1, hy + 1, 12, 9, C('#f1ece4'), 2)
    cv.rect(hx + 2, hy + 2, 10, 6, C('#24202f'))
    cv.rect(hx + 4, hy + 4, 2, 2, C('#ffd9a8')); cv.rect(hx + 8, hy + 4, 2, 2, C('#ffd9a8'))
    s.E[hy + 4:hy + 6, hx + 4:hx + 10] = 0.0
    cv.vline(hx + 7, hy - 2, 2, C('#b8b0a6')); cv.px(hx + 7, hy - 3, C('#ff9a52'))
    cv.rect(hx + 3, hy + 11, 8, 4, C('#e2785a'))
    # gold stars
    for (x, y) in [(5, 16), (w - 7, 16)]:
        cv.px(x, y - 1, C('#f2c94c')); cv.hline(x - 1, y, 3, C('#f2c94c')); cv.px(x, y + 1, C('#f2c94c'))
    cv.hline(5, h - 5, w - 10, C('#d9cfc0'))
    return s

def framed_photo_fishing(w=14, h=12):
    """王工's desk photo: an old man fishing by a river (foreshadow)."""
    s = _sp(w, h); cv = s.cv
    cv.rect(0, 0, w, h, C('#6b4a30')); cv.rect(1, 1, w - 2, h - 2, C('#9ec5e6'))
    cv.rect(1, h // 2 + 1, w - 2, h // 2 - 2, C('#5b9ccc'))
    cv.rect(1, h // 2, w - 2, 1, C('#7fb36a'))
    cv.rect(3, h // 2 - 3, 2, 3, C('#5a4a40')); cv.px(3, h // 2 - 4, C('#e8d2b8'))     # little figure
    cv.line(5, h // 2 - 3, w - 3, 2, C('#3a3036'))                                      # rod
    cv.vline(w - 3, 3, h // 2 - 2, C('#e8e8e8'))                                       # line
    return s

# --------------------------------------------------------------------------- furniture
def partition(w, h, fabric='#4f7486', rail='#c2c8cc', posts=(), seed=0):
    """cubicle partition panel: aluminium top rail + woven fabric + posts."""
    s = _sp(w, h); cv = s.cv
    fr = R(fabric, 6); rr = R(rail, 6)
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    from .. import materials as M
    t = 2.9 + (M.fbm(xx.astype(float), yy.astype(float), 18.0, 2, seed) - 0.5) * 0.9 + ((xx % 4) == 0) * -0.25
    img = M.apply_ramp(t, fr, xx, yy, True, band=3.0)
    cv.a[:] = img
    cv.rect(0, 0, w, 3, rr[3]); cv.hline(0, 0, w, rr[5]); cv.hline(0, 2, w, rr[1]); cv.hline(0, 3, w, fr[0])
    for px_ in posts:
        cv.rect(px_ - 1, 3, 3, h - 3, rr[3]); cv.vline(px_ - 1, 3, h - 3, rr[4]); cv.vline(px_ + 1, 3, h - 3, rr[1])
    cv.vline(0, 0, h, rr[2]); cv.vline(w - 1, 0, h, rr[1])
    cv.rect(0, h - 3, w, 3, C('#3a3a44'))
    return s

def desk(w, top_h, front_h, wood='#a86c43', drawer_side='left', seed=0):
    """front-facing office desk: top surface band + front panel (with drawers)."""
    s = _sp(w, top_h + front_h); cv = s.cv
    wr = R(wood, 7)
    from .. import materials as M
    hh = top_h + front_h
    yy, xx = np.mgrid[0:hh, 0:w].astype(float)
    t_top = 4.4 + (M.value_noise(xx * 0.12, yy * 1.5, 3.0, seed) - 0.5) * 0.9
    t_front = 2.9 + (M.value_noise(xx * 0.10, yy * 0.9, 2.5, seed + 1) - 0.5) * 1.0
    img_t = M.apply_ramp(t_top, wr, xx.astype(int), yy.astype(int), True, 2.6)
    img_f = M.apply_ramp(t_front, wr, xx.astype(int), yy.astype(int), True, 2.6)
    cv.a[:top_h] = img_t[:top_h]; cv.a[top_h:] = img_f[top_h:]
    cv.hline(0, 0, w, wr[2]); cv.hline(1, 1, w - 2, wr[6])           # back edge / sheen
    cv.hline(0, top_h - 1, w, wr[5]); cv.hline(0, top_h, w, wr[6]); cv.hline(0, top_h + 1, w, wr[3])   # front lip
    cv.rect(0, top_h + 2, w, 2, wr[1])                                  # shadow under the lip
    if drawer_side:
        dx = 4 if drawer_side == 'left' else w - 40
        for k in range(2):
            y = top_h + 6 + k * ((front_h - 8) // 2)
            dh = (front_h - 8) // 2 - 2
            cv.rect(dx, y, 36, dh, wr[1]); cv.rect(dx + 1, y + 1, 34, dh - 2, wr[3]); cv.hline(dx + 1, y + 1, 34, wr[4])
            cv.rect(dx + 14, y + dh // 2 - 1, 8, 2, C('#c9c2b6')); cv.hline(dx + 14, y + dh // 2 - 1, 8, C('#efe8de'))
    cv.vline(0, top_h, front_h, wr[2]); cv.vline(w - 1, top_h, front_h, wr[1])
    return s

def crt_monitor(on=0.0, content=None, w=42, h=38, case='#d3c6ae', t=0.0):
    """front-facing beige CRT. on: 0..1 (power-on flash handled by caller). content: optional
    RGBA array drawn into the screen when on."""
    s = _sp(w, h + 6); cv = s.cv
    cr = R(case, 6)
    cv.rrect(0, 0, w, h, cr[0], 3); cv.rrect(1, 1, w - 2, h - 2, cr[3], 3)
    cv.hline(3, 1, w - 6, cr[5]); cv.vline(1, 3, h - 6, cr[4]); cv.vline(w - 2, 3, h - 6, cr[2]); cv.hline(3, h - 2, w - 6, cr[2])
    sx, sy, sw, sh = 5, 4, w - 10, h - 12
    cv.rrect(sx - 1, sy - 1, sw + 2, sh + 2, cr[1], 2)
    glass = C('#1c2b30')
    cv.rrect(sx, sy, sw, sh, glass, 2)
    if on > 0:
        base = mix(C('#173a44'), C('#9fe7ff'), 0.0)
        cv.rrect(sx, sy, sw, sh, mix(glass, C('#2a8fb0'), on), 2)
        s.E[sy:sy + sh, sx:sx + sw] = 0.95 * on
        if content is not None and on > 0.6:
            ch, cw = content.shape[:2]
            cv.blit(content, sx + (sw - cw) // 2, sy + (sh - ch) // 2)
        # scanlines
        for yy in range(sy + 1, sy + sh, 2):
            row = cv.a[yy, sx:sx + sw]; m = row[:, 3] > 0
            row[m, :3] = (row[m, :3].astype(np.float32) * 0.86).astype(np.uint8)
    # glass reflection
    cv.px(sx + sw - 4, sy + 1, mix(glass, C('#ffffff'), 0.35)); cv.px(sx + sw - 3, sy + 2, mix(glass, C('#ffffff'), 0.25))
    cv.hline(sx + 2, sy + 1, 3, mix(glass, C('#ffffff'), 0.18))
    # chin + LED + logo
    cv.rect(w - 9, h - 6, 3, 2, C('#4dff7a') if on > 0 else C('#4a5a4c')); s.E[h - 6:h - 4, w - 9:w - 6] = 1.0 if on > 0 else 0
    cv.rect(5, h - 6, 8, 2, cr[2])
    # stand
    cv.rect(w // 2 - 8, h, 16, 3, cr[1]); cv.rect(w // 2 - 11, h + 3, 22, 3, cr[0]); cv.rect(w // 2 - 10, h + 3, 20, 2, cr[3])
    return s

def chat_screen(w, h, lines=(('在吗？', 'in'),), t=1.0):
    """tiny chat-app UI for a screen (in: white bubble left, out: orange bubble right)."""
    cv = Canvas(w, h)
    cv.rect(0, 0, w, h, C('#eaf4f7')); cv.rect(0, 0, w, 4, C('#2f6fd6')); cv.hline(1, 1, 3, C('#ffffff'))
    y = 6
    for (txt, side) in lines:
        if side == 'in':
            cv.rect(2, y, 3, 3, C('#6a7f99'))
            cv.rect(6, y, min(w - 8, 4 + len(txt) * 3), 4, C('#ffffff')); cv.hline(7, y + 1, min(w - 10, len(txt) * 3), C('#7a8698'))
        else:
            L = min(w - 8, 4 + len(txt) * 3)
            cv.rect(w - 2 - L, y, L, 4, C('#f0a070')); cv.hline(w - 1 - L, y + 1, L - 2, C('#ffffff'))
        y += 6
    return cv.a

def keyboard(w=34, h=7, base='#d8cdb8'):
    s = _sp(w, h); cv = s.cv
    kr = R(base, 6)
    cv.rect(0, 0, w, h, kr[0]); cv.rect(1, 0, w - 2, h - 1, kr[2])
    for j in range(2):
        for i in range((w - 4) // 3):
            cv.rect(2 + i * 3 + j, 1 + j * 2, 2, 1, kr[4]); cv.px(2 + i * 3 + j, 2 + j * 2, kr[3])
    cv.rect(w // 2 - 6, h - 2, 12, 1, kr[4])
    return s

def mug(col='#f2f0ea', logo='#d97757'):
    s = _sp(9, 9); cv = s.cv
    mr = R(col, 6)
    cv.rect(0, 1, 7, 8, mr[0]); cv.rect(1, 1, 5, 7, mr[4]); cv.vline(5, 2, 6, mr[2]); cv.hline(1, 1, 5, mr[1])
    cv.rect(7, 3, 2, 4, mr[0]); cv.px(7, 4, mr[3]); cv.px(7, 5, mr[3])
    cv.rect(2, 4, 2, 2, C(logo))
    cv.hline(1, 1, 5, C('#4a3426'))
    return s

def paper_stack(w=18, n=4):
    s = _sp(w + 3, n * 2 + 3); cv = s.cv
    for k in range(n):
        y = (n - 1 - k) * 2; x = (k * 7) % 3
        cv.rect(x, y, w, 3, C('#8d8478')); cv.rect(x, y, w, 2, C('#f6f2ea')); cv.hline(x + 2, y + 1, w - 6, C('#c9c2b6'))
    return s

def cactus_pot(h=11, pot='#c56a43'):
    s = _sp(9, h + 1); cv = s.cv
    pr = R(pot, 6); gr = R('#5f9e5a', 6)
    cv.rect(1, h - 4, 7, 5, pr[0]); cv.rect(2, h - 4, 5, 4, pr[3]); cv.hline(1, h - 4, 7, pr[4])
    cv.rect(3, 2, 3, h - 6, gr[0]); cv.rect(4, 2, 1, h - 6, gr[3]); cv.px(4, 1, gr[0])
    cv.rect(1, 4, 2, 3, gr[0]); cv.px(1, 3, gr[0]); cv.rect(6, 5, 2, 2, gr[0])
    cv.px(4, 3, gr[5]); cv.px(1, 4, gr[3]); cv.px(7, 5, gr[3])
    cv.px(4, 0, C('#ff8fb0'))
    return s

def desk_lamp(on=0.0, col='#2f6f6a'):
    s = _sp(18, 24); cv = s.cv
    lr = R(col, 6)
    cv.rect(2, 21, 10, 3, lr[0]); cv.rect(3, 21, 8, 2, lr[3])
    cv.line(7, 21, 4, 11, lr[1]); cv.line(4, 11, 10, 4, lr[1])
    cv.poly([(8, 1), (16, 4), (14, 9), (7, 6)], lr[0]); cv.poly([(9, 2), (15, 5), (13, 8), (8, 5)], lr[3])
    if on > 0:
        cv.rect(12, 8, 3, 2, C('#fff2c4')); s.E[8:10, 12:15] = on
    return s

def office_chair_back(w=34, h=28, col='#3b3f52'):
    s = _sp(w, h); cv = s.cv
    cr = R(col, 6)
    cv.rrect(0, 0, w, h, cr[0], 6); cv.rrect(1, 1, w - 2, h - 2, cr[2], 5)
    cv.rrect(3, 2, w - 6, h - 5, cr[3], 4)
    cv.hline(6, 2, w - 12, cr[4]); cv.vline(3, 6, h - 12, cr[4])
    return s

def noodle_cup():
    s = _sp(8, 11); cv = s.cv
    cv.rect(0, 3, 8, 8, C('#4a2a26')); cv.rect(1, 3, 6, 7, C('#f4efe6')); cv.rect(1, 5, 6, 3, C('#d8453a'))
    cv.line(2, 3, 5, 0, C('#c8a070')); cv.line(4, 3, 7, 0, C('#c8a070'))
    return s

def nameplate(name='王工', w=None):
    tw = text_width(name, 'zh8'); w = w or tw + 6
    s = _sp(w, 9); cv = s.cv
    cv.rect(0, 0, w, 9, C('#3a2a20')); cv.rect(1, 1, w - 2, 7, C('#8a5a36')); cv.hline(1, 1, w - 2, C('#b07a4c'))
    cv.text(3, 0, name, C('#ffe6b0'), 'zh8')
    return s

def jacket_on_chair(w=26, h=26):
    s = _sp(w, h); cv = s.cv
    cr = R('#3b3f52', 6); jr = R('#7b5a3e', 6)
    cv.rrect(2, 0, w - 4, h - 4, cr[0], 5); cv.rrect(3, 1, w - 6, h - 6, cr[3], 4)
    cv.poly([(1, 4), (w - 2, 4), (w - 4, h - 2), (3, h - 2)], jr[0])
    cv.poly([(2, 5), (w - 3, 5), (w - 5, h - 3), (4, h - 3)], jr[3])
    cv.line(w // 2, 5, w // 2 - 2, h - 3, jr[1]); cv.hline(3, 5, w - 6, jr[5])
    cv.rect(5, 8, 4, 3, jr[2])
    return s

def filing_cabinet(w=74, h=44, col='#8b958f', binders=True):
    s = _sp(w, h); cv = s.cv
    mr = R(col, 6)
    box(cv, 0, 0, w, h, mr)
    if binders:
        cv.rect(3, 3, w - 6, 16, mr[1])
        cols = ['#c8453a', '#2f6fd6', '#e0a83c', '#3e9e5a', '#7a4fc0', '#e07040', '#2fa0b0']
        x = 4
        i = 0
        while x < w - 6:
            bw = 4 + (i * 3) % 3
            c = R(cols[i % len(cols)], 5)
            bh = 14 - (i % 3)
            cv.rect(x, 3 + 16 - bh, bw, bh, c[2]); cv.vline(x, 3 + 16 - bh, bh, c[3]); cv.hline(x, 3 + 16 - bh + 3, bw, C('#f2ead8'))
            x += bw + 1; i += 1
        cv.hline(2, 19, w - 4, mr[4])
    for k in range(2):
        y = 22 + k * 10
        cv.rect(3, y, w - 6, 8, mr[2]); cv.rect(4, y + 1, w - 8, 6, mr[3]); cv.hline(4, y + 1, w - 8, mr[4])
        cv.rect(w // 2 - 5, y + 3, 10, 2, C('#d9d6d0'))
    return s

def printer(w=32, h=12, col='#d8d0c2'):
    s = _sp(w, h + 3); cv = s.cv
    pr = R(col, 6)
    cv.rect(4, 0, w - 8, 4, C('#f6f2ea')); cv.hline(5, 1, w - 12, C('#cfc8bc'))
    box(cv, 0, 3, w, h, pr)
    cv.rect(4, 7, w - 12, 2, pr[1]); cv.rect(w - 6, 6, 2, 2, C('#4dff7a'))
    return s

def plant_big(w=64, h=110, seed=4):
    """foreground potted plant (big leaves) - meant to be dark + blurred."""
    s = _sp(w, h); cv = s.cv
    rng = np.random.default_rng(seed)
    gr = R('#3f7a4a', 6); pr = R('#a8583a', 6)
    cv.rect(10, h - 26, 36, 26, pr[0]); cv.rect(12, h - 26, 32, 24, pr[3]); cv.rect(10, h - 28, 36, 4, pr[4]); cv.vline(12, h - 24, 22, pr[4])
    for k in range(9):
        ang = -math.pi / 2 + (k - 4) * 0.33 + rng.normal(0, 0.06)
        L = rng.uniform(45, 80)
        x0, y0 = 28, h - 26
        x1, y1 = x0 + math.cos(ang) * L, y0 + math.sin(ang) * L
        cv.line(int(x0), int(y0), int(x1), int(y1), gr[1])
        # leaf: ellipse-ish polygon along stem end
        ux, uy = math.cos(ang), math.sin(ang)
        px_, py_ = -uy, ux
        lw = rng.uniform(7, 11); ll = rng.uniform(16, 24)
        cx, cy = x1 - ux * ll * 0.4, y1 - uy * ll * 0.4
        pts = [(cx + ux * ll * 0.6, cy + uy * ll * 0.6), (cx + px_ * lw, cy + py_ * lw), (cx - ux * ll * 0.5, cy - uy * ll * 0.5), (cx - px_ * lw, cy - py_ * lw)]
        cv.poly(pts, gr[2])
        pts2 = [(cx + ux * ll * 0.5, cy + uy * ll * 0.5), (cx + px_ * lw * 0.55, cy + py_ * lw * 0.55), (cx - ux * ll * 0.3, cy - uy * ll * 0.3)]
        cv.poly(pts2, gr[4])
        cv.line(int(cx - ux * ll * 0.4), int(cy - uy * ll * 0.4), int(cx + ux * ll * 0.55), int(cy + uy * ll * 0.55), gr[1])
    return s

def door_side(room, wall, z0, z1, y0, y1, wood='#9b6b46'):
    """door on a side wall: returns (rgba, mask) in canvas space."""
    S = room.surfaces(1); Z, Y, sid = S['Z'], S['Y'], S['id']
    m = (sid == wall) & (Z >= z0) & (Z <= z1) & (Y >= y0) & (Y <= y1)
    fr = (sid == wall) & (Z >= z0 - 2.5) & (Z <= z1 + 2.5) & (Y >= y0 - 2.5) & (Y <= y1) & ~m
    rgba = np.zeros((room.H, room.W, 4), np.uint8)
    wr = R(wood, 6)
    rgba[m] = wr[3]
    pan = m & ((np.abs(Y - (y0 + (y1 - y0) * 0.3)) < (y1 - y0) * 0.17) | (np.abs(Y - (y0 + (y1 - y0) * 0.72)) < (y1 - y0) * 0.17)) & \
          (np.abs(Z - (z0 + z1) / 2) < (z1 - z0) * 0.32)
    rgba[pan] = wr[2]
    rgba[fr] = C('#e2dbd0')
    hd = m & (np.abs(Y - (y0 + (y1 - y0) * 0.55)) < 1.6) & (np.abs(Z - (z0 + 5)) < 2.5)
    rgba[hd] = C('#e8d9a8')
    return rgba, (m | fr)

def laptop_back(w=30, lid_h=17, on=1.0, col='#a9afbb', stickers=True):
    """laptop seen from behind (lid back towards the camera) - the user sits behind it.
    on: screen glow leaking around the lid edge (emissive).  Base/keyboard deck is the strip below the lid."""
    s = _sp(w + 4, lid_h + 4); cv = s.cv
    lr = R(col, 6)
    # deck (seen edge-on, wider than the lid)
    cv.rect(0, lid_h - 1, w + 4, 4, lr[0]); cv.rect(1, lid_h - 1, w + 2, 2, lr[3]); cv.hline(1, lid_h + 1, w + 2, lr[1])
    # lid
    cv.rrect(2, 0, w, lid_h, lr[0], 2); cv.rrect(3, 1, w - 2, lid_h - 2, lr[3], 1)
    cv.hline(4, 1, w - 6, lr[5]); cv.vline(3, 2, lid_h - 5, lr[4]); cv.vline(w, 3, lid_h - 5, lr[2])
    cv.hline(4, lid_h - 2, w - 6, lr[2])                                             # hinge shadow
    if stickers:
        # round coral sticker with a white spark (a fan's laptop)
        cx, cy = 2 + w // 2, 1 + lid_h // 2 - 1
        cv.rrect(cx - 4, cy - 4, 9, 9, C('#d97757'), 4); cv.rrect(cx - 3, cy - 3, 7, 7, C('#e8896a'), 3)
        W_ = C('#fff4ea')
        cv.vline(cx, cy - 3, 7, W_); cv.hline(cx - 3, cy, 7, W_); cv.px(cx - 2, cy - 2, W_); cv.px(cx + 2, cy - 2, W_)
        cv.px(cx - 2, cy + 2, W_); cv.px(cx + 2, cy + 2, W_)
        cv.rect(6, lid_h - 7, 5, 4, C('#f2d65c')); cv.hline(7, lid_h - 6, 3, C('#c9a83a'))           # sticky note
        cv.rect(w - 6, 4, 4, 3, C('#5aa0e0')); cv.px(w - 5, 5, C('#ffffff'))                      # blue sticker
    if on > 0:   # screen light spilling past the lid top + sides
        GL = C('#c8f2ff')
        for x in range(4, w):
            cv.px(x, 0, mix(lr[0], GL, 0.9 * on)); s.E[0, x] = 1.0 * on
        for y in range(2, lid_h - 4):
            for xx in (2, w + 1):
                cv.px(xx, y, mix(lr[0], GL, 0.5 * on)); s.E[y, xx] = 0.5 * on
    return s

def steam(t, h=12, seed=0, n=3):
    """rising noodle/coffee steam - sparse pale pixels (draw opaque into mid; E ~0.15)."""
    s = _sp(10, h); cv = s.cv
    for k in range(n):
        ph = (t * 0.9 + k / n + seed * 0.37) % 1.0
        for i in range(5):
            yy = int(round(h - 1 - (ph * h + i * 1.1) % h))
            xx = int(round(4 + 2.2 * math.sin(yy * 0.55 + k * 2.1 + t * 2.3)))
            fade = 1 - yy / h
            if (i + k) % 2 == 0 or fade > 0.4:
                if 0 <= xx < 10 and 0 <= yy < h and (h - yy) / h < 0.95:
                    cv.px(xx, yy, C('#e9ecef') if fade < 0.7 else C('#cfd4da')); s.E[yy, xx] = 0.12
    return s
