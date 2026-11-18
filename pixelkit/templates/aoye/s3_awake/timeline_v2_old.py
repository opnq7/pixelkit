"""第 3 关 · 1964 264 小时不睡。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _PROJ)
from common import Lines, FPS

L = Lines()
L.at('C1', 0.50); L.at('C2', 3.55); L.at('C3', 8.30); L.at('C4', 10.80); L.at('C5', 15.60)
L.at('C6', 21.40); L.at('C7', 29.30); L.at('C8', 34.70); L.at('C9', 36.20)
HL = {'C1': ('圣地亚哥',), 'C2': ('加德纳', '不睡觉的纪录'), 'C3': ('认不出来',), 'C4': ('幻觉', '橄榄球明星'), 'C5': ('减到 65',),
      'C6': ('微睡眠', '断线几秒', '疲劳驾驶'), 'C7': ('14 个小时',), 'C8': ('满血复活',), 'C9': ('打这句话的脸',)}

S_HOME, S_BOX, S_WARP, S_STAD, S_BOARD, S_MICRO, S_ROAD, S_CRASH, S_REVIVE, S_SLAP, S_HUB, END = \
    0.0, 8.20, 10.70, 0, 15.50, 21.30, 0, 29.20, 34.55, 36.10, 40.30, 43.40
S_STAD = L.char_t('C4', '坚') - 0.05
S_ROAD = L.char_t('C6', '疲') - 0.1
T_TAG = 0.6
T_POSSESS = 3.40; T_HIT = T_POSSESS + 0.45; T_CARD = T_HIT + 0.15
T_SAN = 6.7
T_DAY2, T_DAY4, T_DAY11 = 8.30, 10.80, 15.60
T_APPLE = 9.0; T_SHOE = 9.5
T_BLACK0 = L.char_t('C6', '断') - 0.05; T_BLACK1 = T_BLACK0 + 1.6
T_ROADBLACK = L.char_t('C6', '这') - 0.1
T_HORN = T_ROADBLACK + 1.0
T_FALL = 29.6
T_QUIZ = L.char_t('C7', '猜') - 0.25
T_PICK = 34.55
T_DANMAKU = 34.9
T_FREEZE = 36.15
T_SLAP = L.char_t('C9', '打') - 0.15
T_ACH = T_SLAP + 0.7
T_CLEAR = 40.4; T_NEXT = 41.0; T_GO = 41.9
DUR = END
