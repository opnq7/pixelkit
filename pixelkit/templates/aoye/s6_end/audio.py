"""结尾声音。 python3 audio.py -> out/s6_audio.wav"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s6_end'))
import numpy as np
import timeline as TL
from pixelkit.audio import synth as Z, cues as Q, master as MS
from pixelkit.audio.synth import ns, nf
from common import OUT
import importlib.util
spec = importlib.util.spec_from_file_location('a0', (_PROJ + '/s0_open/audio.py')); A0 = importlib.util.module_from_spec(spec); spec.loader.exec_module(A0)

DUR = TL.DUR + 0.6

def build(verbose=True):
    B = lambda: Z.Bus(DUR)
    MU, SX, VB, AMB = B(), B(), B(), B()
    # shop: cosy RPG shop waltz (G major, 3/4, 132 bpm) - music box + pluck
    Q.room_tone(AMB, 0.0, TL.S_WAKE, hum=0.004, air=0.008, fade=0.4)
    b = 60 / 132
    bass = ['G2', 'D3', 'E2', 'C3', 'G2', 'D3', 'C3', 'D3']
    mel = ['B4', 'D5', 'G5', 'F#5', 'E5', 'D5', 'C5', 'B4', 'A4', 'B4', 'D5', None]
    k = 0
    while k * b < TL.S_WAKE - 0.3:
        tt = 0.3 + k * b
        if k % 3 == 0: MU.add(Z.pluck(nf(bass[(k // 3) % 8]), 1.0, 0.8, 0.4, k), tt, 0.10)
        else: MU.add(Z.pluck(nf(['B3', 'D4'][k % 2]), 0.4, 0.5, 0.6, k), tt, 0.03, 0.2)
        n = mel[k % 12]
        if n and k % 1 == 0 and (k // 12) % 2 == 0: MU.add(Z.music_box(nf(n), 0.9, 0.7), tt, 0.04, 0.15)
        k += 1
    Q.creak(SX, 0.4, gain=0.05); Q.ui_slide(SX, TL.T_Q, gain=0.05, pan=0.0); Q.result_ding(SX, TL.T_ANS, gain=0.5)
    Q.progress_ticks(SX, TL.T_CLOCK, TL.T_CLOCK + 1.5, rate=14, gain=0.25)
    Q.chapter_chime(SX, TL.T_SIGN, gain=0.4)
    for tt in (TL.T_BULB, TL.T_COFFEE, TL.T_PHONE): Q.pop(SX, tt, gain=0.08); Q.sparkle(SX, tt, d=0.3, gain=0.02)
    for q in range(3): Q.coin(SX, TL.T_PRICE + q * 0.1, gain=0.03, k=q)
    Q.fail_wah(SX, TL.T_COIN + 0.3, gain=0.3)
    Q.question(SX, TL.T_CASE + 0.2, gain=0.05); Q.progress_ticks(SX, TL.T_SEARCH, TL.T_SEARCH + 1.0, rate=10, gain=0.4)
    Q.deny(SX, TL.T_SEARCH + 1.1, gain=0.5)
    Q.boing(SX, TL.T_BTN, gain=0.02, f=600); Q.jump(SX, TL.T_BTN + 0.3, gain=0.3)
    Q.whoosh(SX, TL.T_PUSH, d=0.3, gain=0.05, f0=800, f1=3000); Q.stamp(SX, TL.T_PUSH + 0.35, gain=0.6)
    # dawn: birds, a warm resolution chord, the revive fanfare
    Q.morning_bed(AMB, TL.S_WAKE, TL.END, gain=0.7) if hasattr(Q, 'morning_bed') else Q.birds(AMB, TL.S_WAKE, TL.END)
    Q.whoosh(SX, TL.T_DIVE, d=0.45, gain=0.1, f0=3000, f1=400)
    Q.big_ding(SX, TL.T_WAKE, gain=0.4)
    Q.fanfare(SX, TL.T_REVIVE, gain=0.7); Q.shimmer(SX, TL.T_REVIVE, 1.4, gain=0.4)
    Q.pad_swell(MU, TL.S_WAKE, TL.END - TL.S_WAKE, notes=('G2', 'D3', 'B3', 'F#4'), gain=0.07)
    Q.pop(SX, TL.T_TIP, gain=0.08); Q.chat_in(SX, TL.T_TIP + 0.1, gain=0.05)
    Q.thud(SX, TL.T_FACEDOWN, size=0.3, gain=0.2)
    # leaderboard + danmaku + logo
    for i in range(3): SX.add(Z.blip(nf(['G5', 'B5', 'D6'][i]), 0.06, 'pulse', 0.3), TL.T_BOARD + 0.3 + i * 0.25, 0.04)
    for i in range(8): Q.chat_in(SX, TL.T_BOARD + 1.0 + i * 0.35, gain=0.035, k=i)
    for i, n in enumerate(['G4', 'B4', 'D5', 'G5']):
        MU.add(Z.music_box(nf(n), 1.6, 0.8), TL.S_RANK + 0.2 + i * b * 2, 0.05, 0.1)
    Q.title_sting(MU, TL.T_LOGO, gain=0.9) if hasattr(Q, 'title_sting') else Q.big_ding(SX, TL.T_LOGO)
    A0.vo_track(VB, TL.L)
    nn = MU.x.shape[0]; duck = A0.duck_env(TL.L, nn, depth=0.5)
    mix = MS.wet(MU, 1.3, 0.25, 1) * duck + MS.wet(SX, 0.9, 0.2, 2) + MS.wet(VB, 0.35, 0.06, 3) * 1.25 + AMB.x
    return MS.finalize(mix[:ns(DUR)].copy(), target_lufs=-16.5, verbose=verbose)

if __name__ == '__main__':
    y = build(); MS.write_wav(OUT + '/s6_audio.wav', y); print('ok', len(y) / Z.SR)
