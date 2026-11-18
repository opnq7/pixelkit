"""《Claude 想请一天假》 BRIDGE III -> IV · 走向河边 (0-7.0 s) - single source of truth for picture AND sound.

  0.0-0.6  fade in from black (Act III ends on black) on the Act III street, Saturday 14:00 (HUD).
  0.6-5.6  Claude strolls right at its normal pace, the camera tracks it; the passers-by are time-lapsed (zip past),
           only Claude walks at real speed; the light turns from afternoon to gold, shadows stretch out behind it,
           the HUD clock rolls 14:00 -> 17:40.
  3.3-4.3  it looks up at the light (happy).
  5.6-7.0  golden glare builds from the right (the sun low over the river); water pre-laps 0.5 s; the HUD fades;
           cut on the walk into Act IV (Claude walking up the pier from behind).
"""
import math
from pixelkit.anim import ramp, ease_io, clamp01, auto_blinks

FPS, DUR = 30, 7.0
T_FADE_IN = 0.6
T_ROLL0, T_ROLL1 = 0.9, 5.4          # 14:00 -> 17:40
T_GOLD0, T_GOLD1 = 0.6, 5.8          # light: afternoon -> golden
T_LOOK0, T_LOOK1 = 3.3, 4.3          # looks up at the light
T_GLARE0 = 5.4                       # the river's glare builds from the right
T_HUD_OUT0, T_HUD_OUT1 = 6.3, 6.8
T_WATER = DUR - 0.5                  # river pre-lap

X0, WALK_V, WALK_FPS, FOOT = 400.0, 28.0, 7.0, 200
def claude_x(t): return X0 + WALK_V * t
def gold(t): return ease_io(ramp(t, T_GOLD0, T_GOLD1))
def glare(t): return ease_io(ramp(t, T_GLARE0, DUR))

def clock(t):
    m = 14 * 60 + int(round(220 * ease_io(ramp(t, T_ROLL0, T_ROLL1))))
    return f'{m // 60:02d}:{m % 60:02d}'

def cam(t):
    """tracking, Claude a little left of centre (it walks into the frame's space); zoom 1.6 like Act III MED."""
    return 1.6, claude_x(t) + 46.0, 158.0

BLINKS = auto_blinks(0.3, DUR, mean=2.4, seed=34)
def claude(t):
    d = dict(x=claude_x(t), foot=FOOT, pose='walk', arms='swing', face='normal', phase=int(t * WALK_FPS) % 4,
             look=(1, 0), hop=0.0)
    if T_LOOK0 <= t < T_LOOK1: d['look'] = (1, -1); d['face'] = 'happy'
    elif t >= T_LOOK1: d['face'] = 'happy' if t < T_LOOK1 + 1.2 else 'normal'
    if d['face'] == 'normal' and any(b <= t < b + 0.12 for b in BLINKS): d['face'] = 'blink'
    return d

def footsteps():
    out, n = [], 0
    while n / WALK_FPS < DUR:
        if n % 2 == 0: out.append(n / WALK_FPS)
        n += 1
    return out

# time-lapsed passers-by: (look, x at t=0, px/s, foot, prop)
EXTRAS = [('bun_cardigan', 220.0, 150.0, 187, 'coffee'), ('uncle', 820.0, -120.0, 191, 'dog'),
          ('glasses_tee', 1020.0, -160.0, 192, 'bag'), ('hoodie_long', 40.0, 135.0, 188, 'bag'),
          ('cap_runner', 1400.0, -210.0, 190, None), ('pony_jacket', -150.0, 170.0, 189, None)]

def fade(t): return ease_io(t / T_FADE_IN) if t < T_FADE_IN else 1.0
def hud_alpha(t): return 1.0 - ease_io(ramp(t, T_HUD_OUT0, T_HUD_OUT1))
