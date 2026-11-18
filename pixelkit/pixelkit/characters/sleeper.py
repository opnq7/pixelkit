"""pixelkit.characters.sleeper - 躺在床上侧脸玩手机的人（v0.13，《熬夜副本》开场）。

侧卧、脸朝左，头在枕头上，肩膀没入被子，右手举着手机（屏幕朝脸）。可演：
    eyes : open | blink | wide | red（布满血丝、半睁）| closed | dead（失神、瞳孔放大）
    thumb: 0..1（拇指按下程度，连点「再看一集」）
    screen: RGB 0..255 手机屏幕颜色（发光，E=1）
    phone : False 时手垂下（死后 / 睡着）

    s = sleeper.draw(eyes='open', thumb=0.0, screen=(200, 230, 255))
    layer.put(s.rgba, hx - s.ax, hy - s.ay, Z=0, E=s.E)       # (hx, hy) = 头的中心
    s.phone_xy  (相对头中心的屏幕中心，给点光用)
"""
from types import SimpleNamespace
import numpy as np
from ..core import Canvas, C
from ..palette import ramp

W, H = 64, 44
AX, AY = 44, 18        # head centre
OUT = C('#24182a')

def _R(h, n=6): return [tuple(c) for c in ramp(h, n)]

def draw(eyes='open', thumb=0.0, screen=(200, 230, 255), phone=True, skin='#f0c49e', hair='#2b2232', sleeve='#6f7fa8',
         drop=0.0):
    cv = Canvas(W, H); E = np.zeros((H, W), np.float32)
    sk = _R(skin); hr = _R(hair); sl = _R(sleeve)
    yy, xx = np.mgrid[0:H, 0:W]
    def ell(cx, cy, rx, ry): return ((xx + 0.5 - cx) / rx) ** 2 + ((yy + 0.5 - cy) / ry) ** 2 <= 1
    def put(m, col, e=None):
        cv.a[m] = col
        if e is not None: E[m] = e
    # shoulder / upper arm (under the face, coming out of the blanket)
    put(ell(AX + 2, AY + 13, 11, 6), sl[3])
    # head: skull + face profile facing left
    head = ell(AX, AY, 9.5, 9.0)
    face = ell(AX - 3.5, AY + 1.5, 7.5, 7.5) & (xx + 0.5 < AX + 2)
    put(head | face, sk[3])
    put(ell(AX - 4, AY + 4, 5, 3.2) & (head | face), sk[2])             # under-jaw shade
    nose = (xx == AX - 11) & (yy >= AY + 1) & (yy <= AY + 2)
    put(nose, sk[3]); put((xx == AX - 11) & (yy == AY + 3), sk[2])
    put((xx >= AX - 9) & (xx <= AX - 8) & (yy == AY + 6), C('#a8605a'))  # mouth
    put(ell(AX + 1, AY + 2, 2, 2.6) & head, sk[2]); put((xx == AX + 1) & (yy == AY + 2), sk[1])   # ear
    # hair: mop over the top and back, messy tufts
    hm = (ell(AX + 1.5, AY - 2.5, 10.5, 8.0) & ~ell(AX - 5.5, AY + 3.5, 7.0, 6.5)) | ell(AX + 7, AY + 1, 4.5, 7.5)
    for tx, ty in ((AX - 6, AY - 8), (AX - 2, AY - 10), (AX + 4, AY - 10), (AX - 8, AY - 5)):
        hm |= ell(tx, ty, 2.2, 1.6)
    put(hm, hr[2]); put(hm & ell(AX + 6, AY + 2, 4, 6), hr[1])
    for hx_, hy_ in ((AX - 4, AY - 8), (AX - 1, AY - 9), (AX + 2, AY - 9), (AX - 6, AY - 6)):
        put((xx == hx_) & (yy == hy_), hr[3])                                   # tiny highlights, no band
    put(hm & ell(AX - 6, AY - 3, 3.5, 2.0) & ~face, hr[3])
    # eye
    ex, ey = AX - 6, AY + 0
    bags = C('#8a6a8a')
    if eyes in ('open', 'wide', 'red', 'dead'):
        put((xx >= ex - 2) & (xx <= ex + 1) & (yy >= ey) & (yy <= ey + 1), C('#f4f0ea'))
        if eyes == 'wide': put((xx >= ex - 2) & (xx <= ex + 1) & (yy == ey - 1), C('#f4f0ea'))
        if eyes == 'red': put((xx == ex + 1) & (yy == ey), C('#e8a0a0'))
        pup = C('#1a1418') if eyes != 'dead' else C('#3a3440')
        put((xx >= ex - 2) & (xx <= ex - 1) & (yy >= ey) & (yy <= ey + 1), pup)
        if eyes != 'dead': put((xx == ex - 2) & (yy == ey), C('#ffffff'))
        if eyes == 'dead': put((xx == ex) & (yy >= ey) & (yy <= ey + 1), pup)
        put((xx >= ex - 2) & (xx <= ex + 1) & (yy == ey - (2 if eyes == 'wide' else 1)), hr[1])   # lid line
        if eyes == 'red': put((xx >= ex - 2) & (xx <= ex + 1) & (yy == ey), hr[1])                 # heavy lid
        put((xx >= ex - 2) & (xx <= ex + 1) & (yy == ey + 2), bags)
        if eyes in ('red', 'dead'): put((xx >= ex - 1) & (xx <= ex + 1) & (yy == ey + 3), bags)
    else:
        put((xx >= ex - 1) & (xx <= ex + 1) & (yy == ey + 1), hr[1]); put((xx >= ex - 1) & (xx <= ex + 1) & (yy == ey + 2), bags)
    phone_xy = None
    if phone:
        # forearm from the shoulder up-left to the phone
        px, py = AX - 26, AY - 6 + int(round(drop))
        n = 14
        for i in range(n + 1):
            u = i / n
            x = int(round(AX - 4 + (px + 3 - (AX - 4)) * u)); y = int(round(AY + 12 + (py + 6 - (AY + 12)) * u))
            put(ell(x, y, 2.6, 2.4), sl[3] if i < n - 3 else sk[3])
        # phone (seen from the side/back, screen facing the face -> rim of light)
        put((xx >= px) & (xx <= px + 2) & (yy >= py - 4) & (yy <= py + 6), C('#1b1a22'))
        put((xx == px + 3) & (yy >= py - 4) & (yy <= py + 6), tuple(screen) + (255,), 1.0)
        put((xx == px + 4) & (yy >= py - 3) & (yy <= py + 5), tuple(int(v * 0.55) for v in screen) + (255,), 0.6)
        # hand + thumb
        put(ell(px + 1, py + 6, 2.6, 2.2), sk[3])
        tdy = int(round(-3 + 2 * thumb))
        put((xx >= px + 3) & (xx <= px + 4) & (yy >= py + tdy) & (yy <= py + tdy + 1), sk[4])
        phone_xy = (px + 3 - AX, py + 1 - AY)
    else:
        put(ell(AX - 16, AY + 14, 9, 2.6), sl[3]); put(ell(AX - 25, AY + 14, 2.6, 2.2), sk[3])
    # outline
    a = cv.a[..., 3] > 0
    p = np.pad(a, 1)
    ring = (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]) & ~a
    cv.a[ring] = OUT
    return SimpleNamespace(rgba=cv.a, E=E, ax=AX, ay=AY, phone_xy=phone_xy)
