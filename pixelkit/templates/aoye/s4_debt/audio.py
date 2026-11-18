"""第 4 关声音（2003 · 睡眠债）。 python3 audio.py -> out/s4_audio.wav"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s4_debt'))
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
    # lab: fluorescent hum + beeps; a dry office-funk groove (D dorian, 96 bpm)
    Q.room_tone(AMB, 0.0, TL.S_DEBT, hum=0.008, air=0.008, fade=0.4)
    for q in range(int(TL.S_DEBT / 1.6)): SX.add(Z.blip(1760, 0.04, 'sine', 0.5), 0.8 + q * 1.6, 0.012, -0.5)
    b = 60 / 96
    bass = ['D2', 'D2', 'F2', 'G2', 'A2', 'A2', 'C3', 'A2']
    chords = [('D3', 'F3', 'A3', 'C4'), ('G3', 'B3', 'D4', 'F4')]
    def groove(t0, t1, g=1.0):
        k = 0
        while t0 + k * b / 2 < t1:
            tt = t0 + k * b / 2
            if k % 2 == 0: MU.add(Z.pluck(nf(bass[(k // 2) % 8]), 0.6, 0.8, 0.35, k), tt, 0.11 * g)
            if k % 4 == 0: MU.add(Z.kick_chip(0.14, 120, 48, 0.6), tt, 0.13 * g)
            if k % 4 == 2: MU.add(Z.snare_chip(0.1, 0.4, k), tt, 0.04 * g, 0.1)
            MU.add(Z.hat_chip(0.03, 0.35, k), tt + b / 4, 0.01 * g, 0.3)
            if k % 8 == 0:
                for i, n in enumerate(chords[(k // 8) % 2]): MU.add(Z.fm_epiano(nf(n), b * 3.5, 0.5, 0.6), tt + i * 0.01, 0.028 * g, 0.15)
            k += 1
    groove(0.3, TL.S_BED, 1.0); groove(TL.S_BED, TL.S_PVT, 0.45)
    Q.whoosh(SX, TL.T_POSSESS, d=0.45, gain=0.12, f0=500, f1=4000, seed=5)
    Q.impact(SX, TL.T_HIT, gain=0.55); Q.big_ding(SX, TL.T_HIT + 0.02, gain=0.35); Q.ui_slide(SX, TL.T_CARD, gain=0.04, pan=-0.6)
    Q.stamp(SX, TL.T_EXTREME, gain=0.6)
    # three nights: alarm rings, two slips drop into the jar, page flips (soft, no strobe)
    for i in range(3):
        t0 = TL.S_BED + i * TL.NIGHT_LEN
        if i > 0: Q.paper_flip(SX, t0, gain=0.4)
        tr = t0 + 0.5 * TL.NIGHT_LEN
        n = ns(0.45); bell = Z.osc('square', 1800, 0.45) * (np.sin(np.arange(n) / 44100 * 2 * np.pi * 28) > 0) * 0.3 if False else None
        for q in range(9): SX.add(Z.blip(1760 if q % 2 else 1568, 0.04, 'pulse', 0.4), tr + q * 0.05, 0.035, -0.4)
        for q in range(2): Q.coin(SX, t0 + 0.55 * TL.NIGHT_LEN + q * 0.12, gain=0.03, k=q)
    Q.snore(SX, TL.S_BED + 0.1, gain=0.25)
    # PVT: counter ticks, the button clicks, the lapse buzz; the nod; the printer
    Q.tension_pad(MU, TL.S_PVT, TL.S_FINE - TL.S_PVT, gain=0.045, notes=('D3', 'A3', 'C4', 'E4'))
    for i, (t0, rt) in enumerate(TL.TRIALS):
        SX.add(Z.blip(1200, 0.05, 'pulse', 0.3), t0, 0.03)
        if rt: Q.mouse_click(SX, t0 + rt, gain=0.9, pan=0.3)
        else:
            Q.ticker(SX, t0, t0 + 0.55, rate0=20, rate1=30, gain=0.02)
            SX.add(Z.osc('sine', 880, 0.6) * np.minimum(1, np.arange(ns(0.6)) / 300), t0 + 0.55, 0.05)
    Q.snore(SX, TL.S_NOD + 0.05, gain=0.3); Q.scratch(SX, TL.T_JERK, gain=0.35)
    n = ns(1.4); prn = Z.fft_filter(Z.noise(1.4, 9), lo=800, hi=5000) * (0.6 + 0.4 * np.sign(np.sin(np.arange(n) / 44100 * 2 * np.pi * 14)))
    SX.add(prn, TL.S_PRINT, 0.04, 0.2)
    Q.highlighter(SX, TL.T_CIRCLE, gain=0.6) if hasattr(Q, 'highlighter') else None
    Q.result_ding(SX, TL.T_CIRCLE + 0.5, gain=0.5)
    Q.result_ding(SX, TL.T_Q, gain=0.35); Q.fanfare(SX, TL.T_ANS, gain=0.4)
    # "I'm fine" + the micro-sleep
    groove(TL.S_FINE, TL.S_DEBT, 0.8)
    SX.add(Z.glide_tone(500, 120, 0.3, 'sine', 1.0), TL.T_MICRO, 0.04); Q.scratch(SX, TL.T_MICRO + 0.35, gain=0.3)
    # the vault: boss music (D minor, 120 bpm chip), bills rain, pillow throw, broke
    bb = 60 / 120; t0 = TL.S_DEBT
    lead = ['D5', 'F5', 'A5', 'G5', 'F5', 'E5', 'D5', 'C#5']
    k = 0
    while t0 + k * bb / 2 < TL.S_ANCHOR:
        tt = t0 + k * bb / 2
        if k % 2 == 0: MU.add(Z.chip_note(nf(['D2', 'D2', 'A#1', 'C2'][(k // 8) % 4]), bb * 0.45, 'tri'), tt, 0.11)
        if k % 4 == 0: MU.add(Z.kick_chip(0.14, 140, 50, 0.6), tt, 0.14)
        if k % 2 == 0: MU.add(Z.chip_note(nf(lead[(k // 2) % 8]), bb * 0.4, 'pulse', 0.25), tt, 0.03, 0.15)
        MU.add(Z.hat_chip(0.03, 0.4, k), tt, 0.012, -0.2)
        k += 1
    n = ns(1.0); rum = Z.fft_filter(Z.noise(1.0, 3), lo=40, hi=300) * np.linspace(0, 1, n) ** 0.5
    SX.add(rum, TL.T_RISE, 0.10); Q.impact(SX, TL.T_RISE + 0.9, gain=0.4)
    for i in range(10): Q.paper_flip(SX, TL.T_RISE + i * 0.1, gain=0.08, seed=i)
    Q.ui_slide(SX, TL.T_BOSS, gain=0.05)
    for q, f in enumerate((300, 360, 420)): SX.add(Z.blip(f, 0.08, 'pulse', 0.4), TL.T_HIT_BOSS + 0.9 + q * 0.08, 0.04)
    Q.whoosh(SX, TL.S_DEBT - 0.2, d=0.4, gain=0.10, f0=600, f1=4000); Q.chapter_chime(SX, TL.S_DEBT + 0.2, gain=0.4)
    Q.whoosh(SX, TL.T_PILLOW, d=0.5, gain=0.07, f0=400, f1=2000)
    Q.soft_land(SX, TL.T_HIT_BOSS, size=0.6, gain=0.6); SX.add(Z.blip(1200, 0.05, 'pulse', 0.3), TL.T_HIT_BOSS + 0.05, 0.04)
    Q.stamp(SX, TL.T_BROKE, gain=0.8); Q.fail_wah(SX, TL.T_BROKE + 0.15, gain=0.4)
    for i in range(8): Q.chat_in(SX, TL.T_DANMAKU + i * 0.42, gain=0.04, k=i)
    # where is the clock? achievement, magnifier zoom into cells
    Q.shimmer(SX, TL.S_ANCHOR, 1.5, gain=0.35); Q.big_ding(SX, TL.T_REVIVE + 0.6, gain=0.4); Q.coin(SX, TL.T_REVIVE + 0.65, gain=0.05)
    Q.whoosh(SX, TL.T_CELLS, d=1.4, gain=0.08, f0=300, f1=5000); Q.shimmer(SX, TL.T_CELLS + 0.4, 1.2, gain=0.35)
    for q in range(10): SX.add(Z.blip(2400, 0.02, 'pulse', 0.3), TL.T_CELLS + 0.5 + q * 0.25, 0.012, (q % 2) - 0.5)
    # hub
    Q.shimmer(SX, TL.S_HUB, 1.2, gain=0.4); Q.result_ding(SX, TL.T_CLEAR, gain=0.8); Q.big_ding(SX, TL.T_NEXT, gain=0.4)
    Q.pop(SX, TL.T_BTN, gain=0.08); Q.boing(SX, TL.T_BTN + 0.05, gain=0.02, f=600)
    Q.stamp(SX, TL.T_BTN + 1.1, gain=0.5)
    Q.tension_pad(MU, TL.S_HUB, TL.END - TL.S_HUB, gain=0.05, notes=('C3', 'G3', 'D4', 'E4'))
    Q.whoosh(SX, TL.T_GO, d=1.0, gain=0.06, f0=300, f1=1800); Q.riser(SX, TL.T_GO + 0.4, TL.END, gain=0.09, f0=300, f1=8000)
    A0.vo_track(VB, TL.L)
    nn = MU.x.shape[0]; duck = A0.duck_env(TL.L, nn, depth=0.5)
    mix = MS.wet(MU, 1.3, 0.25, 1) * duck + MS.wet(SX, 0.9, 0.2, 2) + MS.wet(VB, 0.35, 0.06, 3) * 1.25 + AMB.x
    return MS.finalize(mix[:ns(DUR)].copy(), target_lufs=-16.5, verbose=verbose)

if __name__ == '__main__':
    y = build(); MS.write_wav(OUT + '/s4_audio.wav', y); print('ok', len(y) / Z.SR)
