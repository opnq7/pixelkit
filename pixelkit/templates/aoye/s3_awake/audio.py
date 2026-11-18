"""第 3 关声音（1964 · 264 小时不睡）。 python3 audio.py -> out/s3_audio.wav"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s3_awake'))
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
    # ---- 60s home: TV hiss + a surf-rock-ish chip groove (E minor, 112 bpm)
    Q.room_tone(AMB, 0.0, TL.S_MICRO, hum=0.006, air=0.008, fade=0.4)
    SX.add(Z.fft_filter(Z.noise(TL.S_MICRO, 3), lo=3000, hi=9000) * 0.3, 0.0, 0.01, 0.5)
    b = 60 / 112
    bass = ['E2', 'E2', 'G2', 'A2', 'E2', 'E2', 'D2', 'B1']
    lead = ['E5', None, 'G5', 'A5', 'B5', None, 'A5', 'G5', 'E5', None, 'D5', 'E5', None, None, 'B4', None]
    def groove(t0, t1, gain=1.0, lead_on=True):
        k = 0
        while t0 + k * b / 2 < t1:
            tt = t0 + k * b / 2
            if k % 2 == 0:
                MU.add(Z.chip_note(nf(bass[(k // 2) % 8]), b * 0.45, 'tri'), tt, 0.11 * gain)
                if k % 4 == 0: MU.add(Z.kick_chip(0.14, 130, 50, 0.6), tt, 0.14 * gain)
                if k % 4 == 2: MU.add(Z.snare_chip(0.12, 0.5, k), tt, 0.05 * gain, 0.1)
            MU.add(Z.hat_chip(0.03, 0.4, k), tt, 0.012 * gain, -0.2)
            n = lead[k % 16]
            if lead_on and n: MU.add(Z.chip_note(nf(n), b * 0.42, 'pulse', 0.25, vib=0.004), tt, 0.032 * gain, 0.15)
            k += 1
    groove(0.3, TL.S_WARP, 1.0)
    # possession
    Q.whoosh(SX, TL.T_POSSESS, d=0.45, gain=0.12, f0=500, f1=4000, seed=5)
    Q.impact(SX, TL.T_HIT, gain=0.55); Q.big_ding(SX, TL.T_HIT + 0.02, gain=0.35)
    Q.ui_slide(SX, TL.T_CARD, gain=0.04, pan=-0.6)
    Q.ui_slide(SX, TL.T_SAN, gain=0.04, pan=0.6)
    # day flips
    for td in (TL.T_DAY2, TL.T_DAY4, TL.T_DAY11):
        Q.paper_flip(SX, td, gain=0.3); Q.tock(SX, td + 0.05, gain=0.6)
    Q.question(SX, TL.T_SHOE, gain=0.05)
    # day 4: warp -> the groove detunes into a wobbly pad; hallucination stadium crowd
    Q.tension_pad(MU, TL.S_WARP, TL.S_BOARD - TL.S_WARP, gain=0.05, notes=('E2', 'B2', 'F3', 'A#3'))
    SX.add(Z.glide_tone(300, 120, 1.2, 'saw', 0.5) * 0.4, TL.S_WARP + 0.1, 0.03)
    Q.crowd_gasp(SX, TL.S_STAD + 0.1, gain=0.25)
    Q.claps(SX, TL.S_STAD + 0.3, TL.S_BOARD - 0.1, rate=18, gain=0.015)
    # day 11: chalk + minus seven
    groove(TL.S_BOARD + 0.1, TL.S_MICRO, 0.6, lead_on=False)
    for i in range(6): Q.clack(SX, TL.S_BOARD + 0.6 + i * 0.55, size=0.25, gain=0.25, seed=i)
    Q.fail_wah(SX, TL.S_MICRO - 0.6, gain=0.3)
    # micro-sleep: signal lost (hard silence), then the road
    SX.add(Z.osc('sine', 60, 0.2) * Z.expdec(ns(0.2), 0.05), TL.T_BLACK0, 0.2)
    SX.add(Z.fft_filter(Z.noise(TL.T_BLACK1 - TL.T_BLACK0, 8), lo=200, hi=800), TL.T_BLACK0, 0.01)
    Q.night_bed(AMB, TL.S_ROAD, TL.S_CRASH, gain=0.6) if hasattr(Q, 'night_bed') else None
    car = Z.fft_filter(Z.noise(TL.S_CRASH - TL.S_ROAD, 12), lo=60, hi=400)
    SX.add(car, TL.S_ROAD, 0.05)
    Q.heartbeat(SX, TL.S_ROAD, TL.T_ROADBLACK, bpm0=80, bpm1=110, gain=0.4)
    for q in range(2):
        SX.add(Z.osc('saw', 415, 0.45) * 0.5 + Z.osc('saw', 466, 0.45) * 0.5, TL.T_HORN + q * 0.55, 0.05, 0.2)
    Q.whoosh(SX, TL.T_HORN + 0.1, d=0.6, gain=0.1, f0=2000, f1=300)
    # crash -> 264.4 h -> slept 14 h -> quiz
    Q.thud(SX, TL.T_FALL, size=1.0, gain=0.5); Q.soft_land(SX, TL.T_FALL + 0.15, size=0.8, gain=0.6)
    Q.snore(SX, TL.T_FALL + 0.5, gain=0.5)
    Q.tension_pad(MU, TL.S_CRASH, TL.T_PICK - TL.S_CRASH, gain=0.05, notes=('C3', 'G3', 'D4', 'F4'))
    Q.pop(SX, TL.T_QUIZ, gain=0.08); Q.ticker(SX, TL.T_QUIZ + 0.3, TL.T_PICK, rate0=4, rate1=8, gain=0.02)
    Q.checkbox(SX, TL.T_PICK, gain=0.6); Q.fanfare(SX, TL.T_PICK + 0.05, gain=0.5)
    Q.chat_in(SX, TL.T_DANMAKU, gain=0.06)
    # freeze + slap
    Q.scratch(SX, TL.T_FREEZE, gain=0.45)
    Q.whoosh(SX, TL.T_SLAP - 0.2, d=0.2, gain=0.1, f0=400, f1=4000)
    Q.impact(SX, TL.T_SLAP, gain=0.8); SX.add(Z.fft_filter(Z.noise(0.07, 9), lo=800, hi=7000) * Z.expdec(ns(0.07), 0.02), TL.T_SLAP, 0.5)
    Q.dizzy(SX, TL.T_SLAP + 0.2, d=0.6, gain=0.4)
    Q.fanfare(SX, TL.T_ACH, gain=0.7); Q.coin(SX, TL.T_ACH + 1.3, gain=0.05); Q.ui_slide(SX, TL.T_ACH + 1.0, gain=0.04, pan=0.6)
    Q.ui_slide(SX, TL.T_Q, gain=0.05, pan=0.0); Q.result_ding(SX, TL.T_ANS, gain=0.4)
    Q.fanfare(SX, TL.T_REVIVE, gain=0.55); Q.shimmer(SX, TL.T_REVIVE, 1.2, gain=0.3)
    # hub
    Q.shimmer(SX, TL.S_HUB, 1.2, gain=0.4); Q.result_ding(SX, TL.T_CLEAR, gain=0.8); Q.big_ding(SX, TL.T_NEXT, gain=0.4)
    Q.tension_pad(MU, TL.S_HUB, TL.END - TL.S_HUB, gain=0.05, notes=('C3', 'G3', 'D4', 'E4'))
    Q.whoosh(SX, TL.T_GO, d=1.0, gain=0.06, f0=300, f1=1800); Q.riser(SX, TL.T_GO + 0.4, TL.END, gain=0.09, f0=300, f1=8000)
    # voice + mix
    A0.vo_track(VB, TL.L)
    nn = MU.x.shape[0]; duck = A0.duck_env(TL.L, nn, depth=0.5)
    mix = MS.wet(MU, 1.3, 0.25, 1) * duck + MS.wet(SX, 0.9, 0.2, 2) + MS.wet(VB, 0.35, 0.06, 3) * 1.25 + AMB.x
    return MS.finalize(mix[:ns(DUR)].copy(), target_lufs=-16.5, verbose=verbose)

if __name__ == '__main__':
    y = build(); MS.write_wav(OUT + '/s3_audio.wav', y); print('ok', len(y) / Z.SR)
