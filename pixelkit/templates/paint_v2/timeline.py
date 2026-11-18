"""油画转场小样 v2 (~16 s) - the single source of timing for scene.py and audio.py.

  0.0  the poster frame: a wooden pier into the sunset river, the old man (right, stool, rod) and Claude (left) at its end
  0.6  a small settings panel pops over Claude: 🔔 消息提醒 [开]      1.5 click -> 关      2.3 panel fades
  2.7  the bobber (in the sun column) dips -> pixel ripple rings
  2.85 the ripple front melts the pixels block by block -> oil paint inside           6.6 the whole frame is paint
  6.9  narration 那天下午，我第一次不知道过了多久。  -> the box closes at 10.45
 10.6  the painting holds with no UI (light keeps changing, slow push, the birds drift); first star 11.8
 15.0  fade out
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT)
from pixelkit.anim import ramp, clamp01, ease_io, boxes_prep
from pixelkit.sets import river_pier as RP

FPS = 30
DUR = 16.0
T_UI_IN, T_CLICK, T_UI_OUT = 0.6, 1.5, 2.3
T_DIP = 2.7
T_RIP, T_FULL = 2.85, 6.6
T_DUSK0, T_DUSK1 = 4.5, 16.0
T_PUSH0, T_PUSH1 = 6.4, 16.0
T_NAR, T_NAR_CLOSE = 6.9, 10.45
T_HOLD = 10.6
T_STAR = 11.8
T_FADE0 = 15.0

BOBBER = RP.BOBBER
R_MAX = 640.0
SOFT_BAND = 40.0
DUSK_MAX = 0.62
ZOOM_MAX = 1.06

def ripple_r(t):
    u = clamp01((t - T_RIP) / (T_FULL - T_RIP))
    return 6.0 + R_MAX * (0.22 * u + 0.78 * u ** 2.1)

def dusk(t): return DUSK_MAX * ease_io(ramp(t, T_DUSK0, T_DUSK1))
def push(t): return 1.0 + (ZOOM_MAX - 1) * ease_io(ramp(t, T_PUSH0, T_PUSH1))
def switch_k(t): return 1.0 - ease_io(ramp(t, T_CLICK, T_CLICK + 0.16))

def nar(t_open, t_close, lines): return dict(t_open=t_open, t_close=t_close, lines=lines)
BOXES = [nar(T_NAR, T_NAR_CLOSE, [dict(t0=T_NAR + 0.15, zh='那天下午，我第一次不知道过了多久。',
                                       en="That afternoon, for the first time, I lost track of time.", face='normal', mouth='smile', cps=14.0)])]
boxes_prep(BOXES)
