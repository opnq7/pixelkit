"""《Claude 想请一天假》 BRIDGE II -> III · 时间跳过 (0-3.0 s) - single source of truth for picture AND sound.

  0.0-0.35  black; the HUD fades back in where Act II left it: 周六 SAT 00:03 (+ 休假中 badge)
  0.45-2.05 the clock rolls 00:03 -> 08:00 (eased: slow, a blur of minutes, slow), ticks accelerate then settle
  2.05      08:00 lands: gold flash + one tock; 2.15 the first bird
  2.45-2.85 the HUD fades; 3.0 cut to Act III (the dark corridor, 安全出口 flickers on)
"""
from pixelkit.anim import ramp, ease_io

FPS, DUR = 30, 3.0
T_IN1 = 0.35
T_ROLL0, T_ROLL1 = 0.45, 2.05
T_BIRD = 2.15
T_OUT0, T_OUT1 = 2.45, 2.85
M0, M1 = 3, 8 * 60

def minutes(t): return M0 + int(round((M1 - M0) * ease_io(ramp(t, T_ROLL0, T_ROLL1))))
def clock(t):
    m = minutes(t); return f'{m // 60:02d}:{m % 60:02d}'
def hud_alpha(t): return ease_io(ramp(t, 0.0, T_IN1)) * (1 - ease_io(ramp(t, T_OUT0, T_OUT1)))
def tick_times():
    """one tick per displayed-minute change, thinned to <= 22 / s (the rest blur into the roll)."""
    out, last, lm = [], -1.0, minutes(0)
    for i in range(int(DUR * 600)):
        t = i / 600.0
        m = minutes(t)
        if m != lm and t - last >= 1 / 22.0: out.append(t); last = t
        lm = m
    return out
