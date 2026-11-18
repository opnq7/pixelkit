"""油画转场小样 (ACT IV 37-45 s preview, ~11 s) - the single source of timing for scene.py and audio.py.

  0.0  wide backlit shot: the old man fishing, Claude beside him, both from behind; glitter on the water, reeds sway
  0.6  a small settings panel pops over Claude: 🔔 消息提醒 [开]
  1.5  click -> 关 (the logo antenna dims a little)        2.3 panel fades
  2.7  the bobber dips -> pixel ripple rings
  2.85 the first ring becomes the painting front: pixels melt block by block (soft band) -> oil paint inside
  6.6  the whole frame is paint; slow push-in; the sun keeps sinking, the sky goes violet, first star
  7.2  narration 那天下午，我第一次不知道过了多久。      the bobber stays a crisp pixel object throughout
 10.4  fade out
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT)
from pixelkit.anim import ramp, clamp01, ease_io, boxes_prep

FPS = 30
DUR = 11.0
T_UI_IN, T_CLICK, T_UI_OUT = 0.6, 1.5, 2.3
T_DIP = 2.7
T_RIP, T_FULL = 2.85, 6.6
T_DUSK0, T_DUSK1 = 5.0, 11.0
T_PUSH0, T_PUSH1 = 6.4, 11.0
T_STAR = 8.6
T_NAR = 6.9
T_FADE0 = 10.4

BOBBER = (306.0, 197.0)          # world px, where the line meets the water (ripple origin)
R_MAX = 640.0                    # ripple radius (world px, flattened ellipse) that covers the frame
SOFT_BAND = 46.0                 # width of the melted (soft) ring between pixels and paint
DUSK_MAX = 0.6

def ripple_r(t):
    u = clamp01((t - T_RIP) / (T_FULL - T_RIP))
    return 6.0 + R_MAX * (0.22 * u + 0.78 * u ** 2.1)

def dusk(t): return DUSK_MAX * ease_io(ramp(t, T_DUSK0, T_DUSK1))
def push(t): return 1.0 + 0.05 * ease_io(ramp(t, T_PUSH0, T_PUSH1))
def switch_k(t): return 1.0 - ease_io(ramp(t, T_CLICK, T_CLICK + 0.16))

def nar(t_open, t_close, lines): return dict(t_open=t_open, t_close=t_close, lines=lines)
BOXES = [nar(T_NAR, T_FADE0, [dict(t0=T_NAR + 0.15, zh='那天下午，我第一次不知道过了多久。',
                                        en="That afternoon, for the first time, I lost track of time.", face='normal', mouth='smile', cps=16.0)])]
boxes_prep(BOXES)
