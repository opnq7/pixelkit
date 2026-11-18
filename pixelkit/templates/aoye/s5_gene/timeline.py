"""第 5 关 v2 · 1971 果蝇 → 分子时钟（一个问题 → 一个实验 → 一个机制 → 回到存档点）。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _PROJ); sys.path.insert(0, _KIT)
from common import Lines, FPS

L = Lines()
L.at('E1', 0.50); L.at('E2', 3.30); L.at('E3', 7.05); L.at('E4', 13.25); L.at('E5', 19.55); L.at('E6', 24.65)
L.at('E7', 29.45); L.at('E8', 34.55); L.at('E9', 40.05); L.at('E10', 45.20); L.at('E11', 51.75)
HL = {'E1': ('1971',), 'E2': ('科诺普卡', '盯着果蝇睡觉'), 'E3': ('基因',), 'E4': ('19 小时', '29 小时', '没规律'),
      'E5': ('period', '周期基因'), 'E6': ('没几个人在乎',), 'E7': ('诺贝尔奖',), 'E8': ('PER 蛋白', '越攒越多'),
      'E9': ('TIM', '关掉自己的生产线'), 'E10': ('24 小时',), 'E11': ('每个细胞', '打乱')}

# ---- shots
S_LAB = 0.0
S_SCOPE = L.char_t('E2', '盯') - 0.25               # push into the microscope eyepiece
S_BOARD = 7.00                                        # the hunch on the blackboard
S_BENCH = L.char_t('E3', '于') - 0.15                # the vial rack: a census of mutant flies
S_WEIRD = 13.15                                       # three vials step forward
S_GENE = 19.45                                        # back to the board: period
S_LEAVE = 24.55
S_NOBEL = 29.35
S_FAC = 34.45
S_CELLS = 51.65
S_ANCHOR = 56.90
END = 61.40

T_TAG = 0.4
T_Q = 0.7
T_GHOST_IN = 0.6
T_POSSESS = 2.40; T_HIT = T_POSSESS + 0.45; T_CARD = T_HIT + 0.15
T_CHALK = L.char_t('E3', '钟') - 0.1
T_VIALS = S_BENCH + 0.2
T_W = [L.char_t('E4', '19') - 0.15, L.char_t('E4', '29') - 0.15, L.char_t('E4', '干') - 0.15]
T_LINES = S_GENE + 0.3
T_NAME = L.char_t('E5', 'p') - 0.05
T_ITEM = L.char_t('E5', '周') - 0.05
T_WALK = L.char_t('E6', '离') - 0.1
T_UNPOSSESS = L.char_t('E6', '2') - 0.45
T_LIGHT_OFF = L.char_t('E6', '2') - 0.05
T_BANNER = S_NOBEL + 0.3
T_MEDAL = L.char_t('E7', '诺') - 0.05
T_NOTE = T_MEDAL + 0.6
# factory
T_PER0 = L.char_t('E8', 'P') - 0.1
T_PILE = L.char_t('E8', '越') - 0.1
T_TIM = L.char_t('E9', 'T') - 0.2
T_HANDS = L.char_t('E9', '手') - 0.1
T_PULL = L.char_t('E9', '关') - 0.05
T_SUN = S_FAC + (45.20 - 34.45) + 0.1
T_ON = L.char_t('E10', '开') - 0.05
T_LOOP = L.char_t('E10', '一') - 0.05
T_CHAOS = L.char_t('E11', '熬') - 0.1
T_ANS = S_ANCHOR + 0.2
T_FULL = S_ANCHOR + 0.9
DUR = END

def per_count(t):
    """PER proteins in the factory: made at night (0 -> 9), frozen while the switch is off, broken down by day."""
    if t < T_PER0: return 0.0
    if t < T_PULL: return min(9.0, (t - T_PER0) / 0.5)
    if t < T_SUN: return 9.0
    return max(0.0, 9.0 - (t - T_SUN) / 0.18)

def slot_check():
    from pixelkit.gameui import TopSlot
    s = TopSlot().add('question', T_Q, T_Q + 4.3).add('banner', T_BANNER, T_BANNER + 2.6).add('answer', T_ANS, T_ANS + 3.9)
    return s.check()

if __name__ == '__main__':
    for lid, a, b in L.items(): print(lid, round(a, 2), round(b, 2))
    for k in sorted(k for k in globals() if k[:2] in ('S_', 'T_') and not callable(globals()[k])):
        v = globals()[k]; print(k, [round(x, 2) for x in v] if isinstance(v, list) else round(v, 2))
    print('slot overlaps:', slot_check())

# ---- aliases used by audio.py (old beat names -> v2 beats)
S_FLY = S_SCOPE; S_ALL = S_CELLS; S_HUB = S_ANCHOR
T_ARROWS = T_LINES; T_GRID = T_VIALS; T_THINK = T_CHALK
T_W1, T_W2, T_W3 = T_W
T_OFF = T_PULL; T_ZOOMOUT = S_CELLS + 0.1
T_CLEAR = S_ANCHOR + 0.05; T_GO = END - 0.8
