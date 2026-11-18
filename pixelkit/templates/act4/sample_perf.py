"""Act 4 v2 - PERFORMANCE SAMPLE (motion test, ~8.6 s, silent): sit down -> can't sit still -> eyes land on the bucket.
Side two-shot.  Tests pixelkit.perform: anticipation / hop / squash, feet kick, antenna spring, head tilt (shear
rotation), blink in-betweens, saccades, finger taps, loading dots, sparkle; the old man's head turn.
Character motion on 2s, water / light / midges at full rate.   kw: bg = 'pixel' | 'crisp' | 'dof', old = 'v2' | 'v1'
v2 fix (user: "the old man's head is creepy"): v1 sample twisted a full right PROFILE onto a body turned toward Claude
(~150 deg owl twist).  Now his BODY faces the water / rod (3/4 right, his natural fishing posture) and only the HEAD turns
toward Claude (<= 90 deg), through a front-facing in-between."""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/act4'))
import numpy as np
import scene as S
from pixelkit import perform as PF, ui
from pixelkit.anim import ramp, ease_io, squash_curve, hop
from pixelkit.core import Canvas
from pixelkit.scene import ui_over
from pixelkit.particles import PixelSwarm
from pixelkit.sets import river_pier as RP

DUR = 8.6
T_ANT, T_TAKE, T_LAND = 0.32, 0.46, 0.66          # anticipation squash, take-off, landing (sit)
BUCKET_X, BUCKET_Y = 317, S.DECK_Y + 3            # bucket bottom-left on the deck between them

LOOK = [(0.0, (3, 0)), (1.05, (0, 0)), (2.15, (-3, 0)), (2.75, (3, -1)), (3.3, (0, 0)), (4.5, (0, -2)), (5.0, (-3, 1)),
        (5.55, (3, 2))]
BLINKS = [0.9, 3.05, 4.95, 7.3]
OLD_TURN = [(0.0, 1.0), (6.75, 1.0), (7.05, -1.0), (7.75, -1.0), (8.05, 1.0)]    # 3/4 to the water <-> 3/4 to Claude

def tilt_target(s):
    """head roll follows the gaze a few frames late (the eyes lead)."""
    if s < T_TAKE: return -4.0 * ease_io(ramp(s, 0.0, 0.3))                         # shy little tilt while waiting
    if s < 2.2: return 0.0
    lx, ly = PF.glance(s - 0.12, LOOK)
    return {(-3, 0): -3.0, (3, -1): 3.0, (0, -2): 0.0, (-3, 1): -2.0, (3, 2): 6.0}.get((lx, ly), 0.0)

def head_pos(s):
    """head anchor offset (dx, dy) used to drive the antenna spring."""
    x = -7 + 7 * ease_io(ramp(s, T_TAKE, T_LAND))
    y = hop(s, T_TAKE, 4.0, T_LAND - T_TAKE)
    if s >= T_LAND: y += 2.0 * squash_curve(s, T_LAND, 1.0, 0.12)
    if s >= 6.25: x += 3 * ease_io(ramp(s, 6.25, 6.7))
    return (x + 0.5 * tilt_target(s), y)

ARMS = PF.PoseTrack([(0.0, 'clasp'), (T_ANT, 'shrug', 0.16, 'back'), (T_LAND, 'down', 0.12), (T_LAND + 0.2, 'knees', 0.3, 'back')])

def claude(s):
    q = PF.on_twos(s)                                    # character drawings on 2s
    d = {}
    sit = q >= T_LAND
    d['pose'] = 'sit' if sit else 'stand'
    d['dx'] = -7 + 7 * ease_io(ramp(q, T_TAKE, T_LAND))
    if not sit:
        d['y'] = hop(q, T_TAKE, 4.0, T_LAND - T_TAKE)
        d['squash'] = 0.10 * math.sin(math.pi * ramp(q, T_ANT, T_TAKE)) if q < T_TAKE else -0.06 * math.sin(math.pi * ramp(q, T_TAKE, T_LAND))
    else:
        d['squash'] = squash_curve(q, T_LAND, 0.12, 0.12)
        d['kick'] = 3 if q < T_LAND + 0.09 else 0
    d['arms'] = ARMS(q)
    if 2.0 <= q < 3.7:                                   # fidget: finger taps + feet swinging
        d['phase'] = int((q - 2.0) * 8)
        d['kick'] = (1, 0, 2, 0)[int((q - 2.0) * 6) % 4]
    face = 'normal'
    if T_ANT <= q < T_LAND + 0.08: face = 'squint'
    elif T_LAND + 0.08 <= q < 1.4: face = 'happy'
    elif 3.7 <= q < 3.82: face = 'dots1'
    elif 3.82 <= q < 4.2: face = 'dots'
    elif 4.2 <= q < 4.3: face = 'dots1'
    elif 6.05 <= q < 6.75: face = 'sparkle'
    elif q >= 6.75: face = 'star'
    face = PF.blink_face(q, BLINKS, face) if face == 'normal' else face
    d['face'] = face
    d['look'] = PF.glance(q, LOOK) if face not in ('dots', 'dots1') else (0, 0)
    if q < T_TAKE: d['look'] = (3, 1)                                      # waiting: eyes on the old man, a bit down
    d['tilt'] = PF.spring_follow(tilt_target, q, freq=2.6, zeta=0.55, window=1.0, dt=1 / 120)
    d['hdy'] = PF.breath_px(q, 3.4) if 1.2 <= q < 6.0 else 0
    if q >= 6.25: d['lean'] = 3 * ease_io(ramp(q, 6.25, 6.7))
    lx, ly = PF.lag(head_pos, s, freq=3.2, zeta=0.22, window=1.6, dt=1 / 120)
    lx += PF.wobbles(s, [(T_LAND, 2.5), (6.05, 2.2)], freq=3.6, decay=3.0)
    d['ant'] = (lx * 1.4, ly * 0.6)
    d['spark'] = 1.0 + (0.8 * math.exp(-(s - 6.05) * 2.5) if s >= 6.05 else 0.0)
    return d

def old(s, mode='v2'):
    q = PF.on_twos(s)
    face = 'blink' if any(0 <= q - b < 0.13 for b in (1.7, 4.1, 6.3)) else 'normal'
    if mode == 'v1':                                                       # the creepy one (kept for comparison)
        keys = [(0.0, 1.6), (6.75, 1.6), (7.05, -1.0), (7.75, -1.0), (8.05, 1.6)]; body = 'claude'
    else:
        keys = OLD_TURN; body = 'water'
    v = keys[-1][1]
    for (t0, v0), (t1, v1) in zip(keys[:-1], keys[1:]):
        if t0 <= q < t1: v = v0 + (v1 - v0) * ease_io((q - t0) / (t1 - t0)); break
    if abs(v) < 0.95: v = 0.0 if abs(v) < 0.5 else math.copysign(0.6, v)   # in-betweens: 0.6 / front / 0.6
    if 7.05 <= q < 7.75: face = 'soft'                                   # he sees the star eyes: the smallest smile
    return dict(arms='hold', v=v, face=face, breath='v2', body=body)


class Sample:
    def __init__(self, bg='pixel', old='v2'):
        S.BG_MODE = bg
        self.mode = old
        self.a = S.make(only=[])
        self.side = self.a.side
        self.bucket = RP.bucket_side()
        self.swarm = PixelSwarm(center=(262, 157), spread=(12, 7), n=8, seed=4)

    def frame(self, s):
        cd = claude(s); od = old(s, self.mode)
        def under(mid, info):
            ba, be = self.bucket
            sh = np.zeros((1, ba.shape[1] + 2, 4), np.uint8); sh[..., :3] = (46, 26, 32); sh[..., 3] = 255
            mid.put(sh, BUCKET_X - 1, BUCKET_Y, 0)                         # contact shadow
            mid.put(ba, BUCKET_X, BUCKET_Y - ba.shape[0], 0, E=be)
        def extra(cv, E, info):
            self.swarm.draw(cv, E, s)
        z = 2.5 + 0.06 * ease_io(ramp(s, 0, DUR))
        img, cam, info = self.side.frame(18.0 + s, (z, 296.0, 171.0), 0.0, cd=cd, od=od, extra=extra, under=under)
        cv = Canvas(self.a.OW // S.UIS, self.a.OH // S.UIS)
        ui.hud_time(cv, 8, 8, '17:40', day='周六', day_en='SAT', alpha=1.0, flash=0.0)
        img = ui_over(img, cv.a, scale=S.UIS)
        return img * ease_io(ramp(s, 0.0, 0.3)) * (1 - ease_io(ramp(s, DUR - 0.35, DUR)))

def make(**kw): return Sample(**kw)
