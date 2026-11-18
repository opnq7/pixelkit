"""BRIDGE II -> III · 时间跳过 - black + the corner clock HUD rolling 00:03 -> 08:00."""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/bridge23'))
import numpy as np
from pixelkit.anim import ramp
from pixelkit.scene import ui_over
from pixelkit import ui
import timeline as TL


class Bridge23:
    def __init__(self, OW=1920, OH=1080, **kw):
        self.OW, self.OH = OW, OH

    def frame(self, t):
        img = np.zeros((self.OH, self.OW, 3), np.float32)
        a = TL.hud_alpha(t)
        if a <= 0: return img
        cv = ui.UICanvas()
        fl = 0.7 * (1 - ramp(t, TL.T_ROLL1, TL.T_ROLL1 + 0.4)) if t >= TL.T_ROLL1 else 0.0
        ui.hud_time(cv, 8, 8, TL.clock(t), day='周六', day_en='SAT', alpha=a, flash=fl)
        ui.status_badge(cv, 472, 8, 'off', alpha=a)
        return ui_over(img, cv.a, scale=self.OW // 480)


def make(**kw): return Bridge23(**kw)
