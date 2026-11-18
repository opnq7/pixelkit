"""第 2 关 · 1953 快速眼动 + 大脑夜班大楼。t=0 从门里白光开始。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _PROJ)
from common import Lines, FPS

L = Lines()
L.at('B1', 0.50); L.at('B2', 3.45); L.at('B3', 9.35); L.at('B4', 12.75); L.at('B5', 18.15)
L.at('B6', 23.90); L.at('B7', 29.30); L.at('B8', 35.10); L.at('B9', 41.95); L.at('B10', 45.75); L.at('B11', 55.45)
HL = {'B1': ('芝加哥',), 'B2': ('阿瑟林斯基', '科研'), 'B3': ('关机',), 'B4': ('左右狂扫', '像醒着一样'), 'B5': ('快速眼动期',),
      'B6': ('灯火通明',), 'B7': ('记忆归档', '焦虑'), 'B8': ('脑脊液',), 'B9': ('系统维护',), 'B10': ('后半夜', '两小时'), 'B11': ('跳过',)}

S_LAB, S_LEAN, S_OFF, S_EYE, S_EEG, S_DISC, S_INTO, S_ARCH, S_EMO, S_BASE, S_EXT2, S_SCHED, S_ANCHOR, S_HUB, END = \
    0.0, 6.70, 9.30, 12.70, 15.20, 18.10, 23.80, 28.30, 31.55, 34.70, 41.40, 45.55, 52.20, 55.20, 58.80
T_Q = 0.9
T_REVIVE = S_ANCHOR + 0.3

T_TAG = 0.6
T_POSSESS = 3.30; T_HIT = T_POSSESS + 0.45; T_CARD = T_HIT + 0.15
T_FREEZE = L.char_t('B2', '这') - 0.05                  # 这是科研 -> freeze frame
T_OFF = L.char_t('B3', '关') - 0.1
T_SCAN0 = 13.0
T_WILD = L.char_t('B4', '脑') - 0.1
T_TAP = 18.35; T_SMOKE = 18.6
T_BANNER = L.char_t('B5', '隐') - 0.1
T_EXIT_GHOST = 24.0; T_EAR = 25.0; T_TOWER = 25.4
T_GLOW = L.char_t('B6', '灯') - 0.05                 # windows light up in a wave on "灯火通明"
# archive gag: an embarrassing memory gets filed as PERMANENT
T_CARD_UP = S_ARCH + 1.55; T_CARD_STAMP = T_CARD_UP + 0.75
# emotion: the dryer pops open, anxiety comes out folded
T_DRYER = S_EMO + 0.2
T_POP = L.char_t('B7', '消') - 0.05
T_TOWEL = T_POP + 0.55
# basement: grime tags, valve, gate lifts, wave sweeps the ghost away
T_GRIME = S_BASE + 0.35
T_SALUTE = L.char_t('B8', '清') - 0.05
T_VALVE = L.char_t('B8', '开') - 0.15
T_GATE = T_VALVE + 0.45
T_WAVE = L.char_t('B8', '脑') - 0.1
T_SWEPT = T_WAVE + 0.35
T_CHEER = T_SWEPT + 1.4
T_SIGN = L.char_t('B9', '系') - 0.1
T_ACH = L.char_t('B9', '维') + 0.2
T_SCHED = S_SCHED + 0.15
T_STRIKE = L.char_t('B10', '熬') - 0.05
T_FALL = L.char_t('B10', '砍') - 0.1
T_CLEAR = S_HUB + 0.05; T_NEXT = S_HUB + 0.7; T_BTN = S_HUB + 0.9; T_GO = S_HUB + 2.1
T_ANS = T_ACH - 0.25
def slot_check():
    from pixelkit.gameui import TopSlot
    return TopSlot().add('question', T_Q, T_Q + 4.0).add('banner', T_BANNER, T_BANNER + 2.6).add('answer', T_ANS, T_ANS + 3.9).check()
DUR = END
if __name__ == '__main__':
    for lid, a, b in L.items(): print(lid, round(a, 2), round(b, 2))
    print('T_BANNER', round(T_BANNER, 2), 'T_ACH', round(T_ACH, 2), 'slots', slot_check())
