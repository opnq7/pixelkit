"""第 1 关 · 1938 没有太阳的洞穴（时间真相源）。t=0 从门里的白光开始。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _PROJ)
from common import Lines, FPS

L = Lines()
L.at('A1', 0.55)
L.at('A2', 4.25)
L.at('A3', 11.05)
L.at('A4', 16.85)
L.at('A5', 23.25)
L.at('A6', 29.45)
L.at('A7', 38.45)
L.at('A8', 44.55)
L.at('A9', 50.65)
HL = {'A1': ('地下四十米',), 'A2': ('附身', '克莱特曼'), 'A3': ('太阳', '有只钟'), 'A4': ('28 个小时',), 'A5': ('瞪眼到天亮', '站着都能睡着'),
      'A6': ('体温', '24 小时'), 'A7': ('真有一只钟',), 'A8': ('28 小时的一天', '难受的是你'), 'A9': ('大脑在忙什么',)}

S_DESC, S_CAMP, S_VS, S_DARK, S_CHALK, S_SPLIT, S_NOD, S_THERMO, S_GRAPH, S_EXIT, S_TRIP, S_HUB, END = \
    0.0, 3.90, 10.85, 16.70, 19.00, 23.00, 26.30, 29.20, 33.45, 38.20, 44.30, 50.40, 55.20

# descent + camp
T_TAG = 0.65
T_GHOST_IN0, T_GHOST_IN1 = 4.20, 6.20
T_POSSESS = L.char_t('A2', '这') - 0.15            # dive starts
T_HIT = T_POSSESS + 0.45                           # into Kleitman
T_CARD = T_HIT + 0.15
# VS
T_SUN, T_GEAR, T_VS = 11.05, L.char_t('A3', '还'), L.char_t('A3', '还') - 0.35
# dark: boulder covers the sun
T_ROLL0, T_ROLL1 = 17.05, L.char_t('A4', '山') + 0.1
# chalk clock
T_CHALK0, T_CHALK1 = 19.30, L.e('A4') - 0.1
T_28 = L.char_t('A4', '2')
# split + nod
T_BONK = L.char_t('A5', '着', 1) + 0.05
# thermometer + graph
T_DAY, T_NIGHT = L.char_t('A6', '白'), L.char_t('A6', '夜')
T_GEAR_CLICK = L.char_t('A6', '2') + 0.25
# exit
T_ACH = L.char_t('A7', '真') - 0.1
# triptych
T_P1, T_P2, T_P3 = L.char_t('A8', '熬'), L.char_t('A8', '倒'), L.char_t('A8', '倒', 1)
T_JAM = L.char_t('A8', '它') - 0.05
# hub
T_CLEAR = 50.75
T_NEXT = 51.70
T_GO = 53.60
DUR = END
