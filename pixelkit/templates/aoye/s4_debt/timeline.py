"""第 4 关 v4 · 2003 睡眠债。t=0 从门里白光开始。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _PROJ)
sys.path.insert(0, _KIT)
from common import Lines, FPS

L = Lines()
L.at('D1', 0.50); L.at('D2', 3.75); L.at('D3', 11.00); L.at('D4', 16.75); L.at('D5', 19.80); L.at('D6', 25.20); L.at('D7', 28.90)
HL = {'D1': ('睡眠实验室',), 'D2': ('每天少睡一点', '6 小时'), 'D3': ('整整一夜没合眼',), 'D4': ('我挺好的啊',),
      'D5': ('睡眠债', '还不清'), 'D6': ('很多人的日常',), 'D7': ('小到你看不见',)}

# ---- shots
S_LAB = 0.0
S_BED = L.char_t('D2', '所') - 0.15                  # three nights at the bed (from the foot end)
S_PVT = 10.75                                         # the reaction box on the desk
S_NOD = None                                          # (set below) cut to him nodding off on the lapse
S_PRINT = L.char_t('D3', '和') - 0.25                # the printout
S_FINE = 16.35
S_DEBT = 19.60
S_CROWD = 25.05
S_ANCHOR = 29.55
S_HUB = 33.40
END = 37.20

# ---- lab
T_TAG = 0.4
T_Q = 0.7                                             # question card (alone at the top)
T_GHOST_IN = 0.7
T_POSSESS = 2.30; T_HIT = T_POSSESS + 0.45; T_CARD = T_HIT + 0.15
T_EXTREME = L.char_t('D2', '太') - 0.1              # the 1964 card gets 太极端
T_YAWN = L.char_t('D2', '每') - 0.1
# ---- three nights
NIGHTS = (1, 7, 14)
NIGHT_LEN = (S_PVT - S_BED) / 3.0
def night_at(t):
    i = int(max(0, min(2, (t - S_BED) // NIGHT_LEN))); return i, S_BED + i * NIGHT_LEN
FLIP = 0.22                                           # page-flip wipe between nights
# ---- PVT: three trials (two OK, one lapse)
TRIALS = [(S_PVT + 0.15, 0.286), (S_PVT + 0.7, 0.341), (S_PVT + 1.2, None)]
T_LAPSE_SHOW = TRIALS[2][0] + 0.55
S_NOD = T_LAPSE_SHOW + 0.5
T_JERK = S_NOD + 0.42
T_COMPARE = S_PRINT
T_CIRCLE = L.char_t('D3', '差') - 0.1
# ---- I'm fine
T_THUMB = S_FINE + 0.15
T_MICRO = L.char_t('D4', '挺') - 0.1
T_METERS = T_THUMB + 0.35
T_DROP = T_MICRO + 0.4                               # the 'actual' meter drops while he dozes
# ---- vault
T_BANNER0, T_BANNER1 = S_DEBT + 0.15, S_DEBT + 1.55
T_RISE = S_DEBT + 0.4                                 # the bill monster rises out of the vault
T_BOSS = T_BANNER1 + 0.2                              # boss bar (after the banner leaves the slot)
T_PILLOW = L.char_t('D5', '周') - 0.1
T_HIT_BOSS = T_PILLOW + 0.5
T_BROKE = L.char_t('D5', '还') - 0.05
T_DANMAKU = S_CROWD + 0.1
T_BOSS_OUT = L.e('D6') + 0.1
T_ANS = T_BOSS_OUT + 0.45                            # answer card (after the boss bar left)
# ---- the save point
T_REVIVE = S_ANCHOR + 0.9
T_CELLS = L.char_t('D7', '答') - 0.15
T_CLEAR = S_HUB + 0.05; T_NEXT = S_HUB + 0.7; T_BTN = S_HUB + 0.9; T_GO = S_HUB + 2.1
DUR = END

def debt(t):
    """boss HP (hours owed): 0 -> 28 as he rises, -2 on the pillow hit, then keeps healing (+2 / night)."""
    if t < T_RISE: return 0.0
    d = 28.0 * min(1.0, (t - T_RISE) / max(0.1, T_PILLOW - T_RISE))
    if t >= T_HIT_BOSS: d = 26.0 + min(14.0, max(0.0, t - T_HIT_BOSS - 0.7) * 4.0)
    return d

def debt_lag(t):
    """white damage trail: lingers at the pre-hit value for 0.35 s, then slides down."""
    if T_HIT_BOSS <= t < T_HIT_BOSS + 0.75:
        u = max(0.0, (t - T_HIT_BOSS - 0.35) / 0.4)
        return 28.0 - 2.0 * min(1.0, u)
    return debt(t)

# ---- one widget at a time in the top-centre slot
def slot_check():
    from pixelkit.gameui import TopSlot
    s = TopSlot().add('question', T_Q, T_Q + 4.3).add('banner', T_BANNER0, T_BANNER1).add('boss', T_BOSS, T_BOSS_OUT + 0.3)
    s.add('answer', T_ANS, T_ANS + 3.9)
    return s.check()

if __name__ == '__main__':
    for lid, a, b in L.items(): print(lid, round(a, 2), round(b, 2))
    for k in ('S_BED', 'NIGHT_LEN', 'S_NOD', 'S_PRINT', 'T_CIRCLE', 'T_MICRO', 'T_PILLOW', 'T_HIT_BOSS', 'T_BROKE', 'T_BOSS_OUT', 'T_ANS', 'T_CELLS'):
        print(k, round(globals()[k], 2))
    print('slot overlaps:', slot_check())
