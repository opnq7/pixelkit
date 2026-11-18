"""结尾 · 外挂商店 → 复活。t=0 从白光开始（接第 5 关的 100%）。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _PROJ)
from common import Lines, FPS

L = Lines()
L.at('F1', 0.70); L.at('F2', 4.85); L.at('F3', 11.95); L.at('F4', 16.40); L.at('F5', 21.60); L.at('F6', 26.40)
HL = {'F1': ('外挂',), 'F2': ('电灯', '咖啡', '手机'), 'F3': ('睡眠',), 'F4': ('免费跳过睡眠',), 'F5': ('复活成功', '别再来了'),
      'F6': ('评论区',)}
S_SHOP, S_SKIP, S_WAKE, S_RANK, END = 0.0, 16.25, 21.30, 26.20, 32.20
T_SIGN = 0.9
T_Q = 1.2                                              # question card (top centre)
T_ANS = 20.55                                          # answer card, after the button gag
T_ROW = 11.95                                          # the three item cards line up
S_PRICE = T_ROW
T_BULB = L.char_t('F2', '电') - 0.05
T_COFFEE = L.char_t('F2', '咖') - 0.05
T_PHONE = L.char_t('F2', '手') - 0.05
T_PRICE = L.char_t('F3', '价') - 0.05
T_COIN = L.char_t('F3', '睡') - 0.1
T_CASE = S_SKIP + 0.2
T_SEARCH = L.char_t('F4', '一') - 0.1
T_BTN = L.char_t('F4', '免') - 0.1
T_PUSH = L.e('F4') - 0.5
T_DIVE = S_WAKE + 0.75
T_WAKE = T_DIVE + 0.5
T_REVIVE = L.char_t('F5', '复') - 0.05
T_TIP = L.char_t('F5', '新') - 0.05
T_FACEDOWN = L.e('F5') - 0.2
T_BOARD = S_RANK + 0.2
T_LOGO = L.e('F6') + 0.3
T_CLOCK = T_WAKE                                 # time resumes: 03:56 -> 07:12, the window turns gold
DUR = END
def slot_check():
    from pixelkit.gameui import TopSlot
    return TopSlot().add('question', T_Q, T_Q + 4.0).add('answer', T_ANS, T_ANS + 3.9).check()
if __name__ == '__main__':
    for lid, a, b in L.items(): print(lid, round(a, 2), round(b, 2))
    for k in sorted(k for k in globals() if k.startswith('T_')): print(k, round(globals()[k], 2))
    print('slot overlaps:', slot_check())
