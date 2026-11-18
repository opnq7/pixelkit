"""开场 v2 · 再刷十分钟（唯一的时间真相源）。"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _PROJ)
from common import Lines, FPS

L = Lines()
L.at('O1', 0.45)
L.at('O2', 10.60)
L.at('O3', 13.05)
L.at('O4', 21.00)
L.at('O5', 24.20)
L.at('O6', 28.40)
HL = {'O1': ('再刷十分钟就睡',), 'O2': ('没能刷完',), 'O3': ('熬夜',), 'O4': ('没完全死',), 'O5': ('复活',), 'O6': ('点的它',)}

# ---- shots
S_FEED1 = 0.0
S_FACE1 = L.char_t('O1', '你') - 0.12           # cut on "你对自己说"
S_WIDE = 4.55
S_FEED2 = 6.30
S_FACE2 = 7.30
S_FEED3 = 8.55
S_FACE3 = 9.30
S_SMACK = 9.85
S_OVER = 12.75
S_GHOST = 20.30
S_QUEST = 23.90
S_HUB = 32.75
END = 37.15

# ---- feed swipes (absolute times; the feed keeps running off-screen so every phone cut continues the scroll)
SWIPES = [0.15, 0.78, 1.08, 1.60, 2.40, 3.10, 3.70, 4.30,                  # calm-ish
          4.85, 5.20, 5.52, 5.80, 6.05,                                     # (wide: time-lapse)
          6.32, 6.52, 6.70, 6.86, 7.00, 7.12, 7.22,                         # binge burst
          8.62]                                                             # the last, sluggish swipe
SLOW_SWIPE = 8.62
T_CLOCK_POP = L.char_t('O1', '凌') + 0.05
T_TASK = L.char_t('O1', '再') - 0.05               # quest tracker pops on "再刷十分钟就睡"
T_SMIRK0, T_SMIRK1 = L.char_t('O1', '就') - 0.1, L.char_t('O1', '就') + 0.75
T_HUD = S_FACE1 + 0.25
T_FF0, T_FF1 = S_WIDE + 0.25, S_FEED2
T_NOD1, T_JERK = S_FACE2 + 0.15, S_FACE2 + 0.55
T_NOD2 = S_FACE2 + 0.95
T_LOOSE = S_FEED3 + 0.25                            # grip loosens, the phone view tilts
T_SLIP = S_FACE3 + 0.20                             # phone starts falling toward the face
T_HIT = S_SMACK                                     # contact
T_FLAT = S_SMACK + 0.45
T_FAIL = S_SMACK + 0.70                             # task "失败" tag
T_DESAT0, T_DESAT1 = S_SMACK + 0.6, S_OVER
T_GAME = S_OVER + 0.12
T_DING = L.char_t('O3', '叮')
T_PANEL = L.char_t('O3', '检') - 0.05
T_ROWS = L.char_t('O3', '熬') - 0.30       # result_panel row 0 appears ~ on "熬夜"
ROW_GAP = 0.62
T_STAMP = T_ROWS + 0.30 + 4 * ROW_GAP + 0.55
# ghost
T_POP = S_GHOST + 0.10
T_CAT_PUFF = S_GHOST + 0.32
T_DIZZY0, T_DIZZY1 = S_GHOST + 0.45, S_GHOST + 1.15
T_HANDS = S_GHOST + 1.20
T_BODY = S_GHOST + 1.70
T_BACK = S_GHOST + 2.05
T_TAKE = S_GHOST + 2.25                             # double take
T_PANIC0, T_PANIC1 = S_GHOST + 2.45, S_GHOST + 3.05
T_CATSEE = S_GHOST + 3.10                           # ghost notices the cat, waves
# quest + the gag
T_PANEL_Q = S_QUEST + 0.12
T_REVIVE = S_QUEST + 0.80
T_REACH0 = L.e('O5') - 0.55                         # ghost drifts toward 「我还能再熬会儿」
T_REACH1 = L.s('O6') - 0.05
T_FREEZE = L.s('O6') + 0.05                         # "别点了"
T_SKULL = L.char_t('O6', '你') - 0.05              # "你上次，就是点的它" -> the button shows what happened last time
T_RETRACT0, T_RETRACT1 = L.e('O6') + 0.15, L.e('O6') + 0.75
T_WHISTLE0, T_WHISTLE1 = L.e('O6') + 0.55, L.e('O6') + 1.30
T_CLICK = L.e('O6') + 1.45
T_PANEL_OUT = T_CLICK + 0.30
# hub
T_DOORS = [S_HUB + 0.25 + 0.23 * i for i in range(5)]
T_ACTIVE = S_HUB + 1.65
T_FLOAT0, T_FLOAT1 = S_HUB + 1.95, S_HUB + 3.25
T_OPEN0, T_OPEN1 = S_HUB + 3.25, S_HUB + 3.95
T_WHITE = S_HUB + 4.00
DUR = END

# ---- task timer (seconds left of "10 分钟") and the bedside clock
def remain(t):
    pts = [(T_TASK, 600), (S_WIDE, 598), (S_FEED2, 330), (S_FACE2, 220), (S_FEED3, 140), (S_SMACK, 52)]
    if t <= pts[0][0]: return 600
    for (a, va), (b, vb) in zip(pts, pts[1:]):
        if t <= b:
            u = (t - a) / (b - a); return va + (vb - va) * u
    return 52

def clock(t):
    el = 600 - remain(t)
    m = 47 + int(el // 60)
    return f'03{m:02d}' if m < 60 else f'04{m - 60:02d}'

# heart beats (bpm rises; stops at the hit)
def _beats():
    out, t = [], 0.0
    while t < T_FLAT:
        bpm = 74 if t < S_WIDE else (96 if t < S_FEED2 else (124 if t < S_FACE3 else 150))
        out.append(t); t += 60.0 / bpm
    return out
BEATS = _beats()

def hp(t):
    pts = [(0, 0.66), (S_WIDE, 0.62), (S_FEED2, 0.40), (S_FACE2, 0.28), (S_FEED3, 0.16), (S_SMACK - 0.01, 0.07), (S_SMACK + 0.05, 0.0)]
    for (a, va), (b, vb) in zip(pts, pts[1:]):
        if t <= b: return va + (vb - va) * max(0.0, (t - a) / (b - a))
    return 0.0

# ---- on-screen text must finish + hold >= 1 s before the cut (checked by check_text_holds)
TEXT_EVENTS = [('result rows', T_STAMP + 0.4, S_GHOST), ('task failed', T_FAIL + 0.3, S_OVER)]

def check_text_holds(min_hold=1.0):
    bad = [(n, e, c) for (n, e, c) in TEXT_EVENTS if c - e < min_hold]
    for lid, a, b in L.items():
        pass
    return bad

if __name__ == '__main__':
    for lid, a, b in L.items(): print(lid, round(a, 2), round(b, 2))
    print('rows', round(T_ROWS, 2), 'stamp', round(T_STAMP, 2), 'ghost', S_GHOST, 'bad holds', check_text_holds())
    print('reach', round(T_REACH0, 2), round(T_REACH1, 2), 'click', round(T_CLICK, 2), 'hub', S_HUB)
    print('face1', round(S_FACE1, 2), 'task', round(T_TASK, 2))
