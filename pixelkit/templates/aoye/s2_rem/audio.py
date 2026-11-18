"""第 2 关声音。 python3 audio.py -> out/s2_audio.wav"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s2_rem'))
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
    # ---- lab: hum of instruments + a slow clock
    Q.room_tone(AMB, 0.0, TL.S_INTO + 1.2, hum=0.006, air=0.008, fade=0.4)
    Q.clock_ticks(AMB, 0.3, TL.S_INTO + 1.2, period=1.0, gain=0.04, pan=-0.4)
    # late-night jazz trio: walking pluck bass, brushed hats, vibraphone-ish bells (Cm7 - Fm7 - Bb7 - Ebmaj7), 72 bpm
    b = 60 / 72
    chords = [('C3', 'D#3', 'G3', 'A#3'), ('F2', 'G#3', 'C4', 'D#4'), ('A#2', 'D3', 'G#3', 'C4'), ('D#2', 'G3', 'A#3', 'D4')]
    walk = ['C3', 'D#3', 'G3', 'A#2', 'F2', 'G#2', 'C3', 'D#3', 'A#2', 'D3', 'F3', 'G#2', 'D#2', 'G2', 'A#2', 'D3']
    vib = ['G4', None, 'A#4', 'C5', None, 'D#5', None, 'D5', 'C5', None, 'A#4', None, 'G4', None, None, None]
    def jazz(t0, t1, gain=1.0):
        k = 0
        while t0 + k * b < t1:
            tt = t0 + k * b
            MU.add(Z.pluck(nf(walk[k % 16]), 1.0, 0.7, 0.35, k), tt, 0.13 * gain, -0.15)
            MU.add(Z.hat_chip(0.06, 0.4, k), tt + b * 0.66, 0.018 * gain, 0.3)
            if k % 4 == 0:
                for i, n in enumerate(chords[(k // 4) % 4]):
                    MU.add(Z.fm_epiano(nf(n), b * 3.5, 0.5, 0.6), tt + i * 0.015, 0.03 * gain, 0.15)
            n = vib[k % 16]
            if n: MU.add(Z.bell(nf(n), 1.4, 0.6), tt, 0.035 * gain, 0.25)
            k += 1
    jazz(0.4, TL.T_FREEZE - 0.02)
    # possession
    Q.whoosh(SX, TL.T_POSSESS, d=0.45, gain=0.12, f0=500, f1=4000, seed=5)
    Q.impact(SX, TL.T_HIT, gain=0.55); Q.big_ding(SX, TL.T_HIT + 0.02, gain=0.35)
    # freeze: record scratch + stamp
    Q.scratch(SX, TL.T_FREEZE, gain=0.5) if hasattr(Q, 'scratch') else None
    Q.stamp(SX, TL.T_FREEZE + 0.05, gain=0.6)
    jazz(TL.S_OFF + 0.2, TL.T_WILD - 0.05, 0.8)
    # power-off
    SX.add(Z.glide_tone(600, 120, 0.5, 'sine', 1.0), TL.T_OFF, 0.06)
    # REM scan: whooshing L-R
    for k in range(int((TL.S_EEG - TL.T_SCAN0) / 0.224)):
        Q.whoosh(SX, TL.T_SCAN0 + k * 0.224, d=0.16, gain=0.03, f0=1200, f1=2400, pan=(0.6 if k % 2 else -0.6), seed=k)
    # EEG goes wild: pen scratching + alarm beeps
    n = ns(TL.S_DISC - TL.T_WILD)
    scr = Z.fft_filter(Z.noise(TL.S_DISC - TL.T_WILD, 7), lo=1500, hi=6000) * (0.5 + 0.5 * np.abs(np.sin(np.arange(n) / 44100 * 2 * np.pi * 7)))
    SX.add(scr, TL.T_WILD, 0.05, -0.4)
    for k in range(8): SX.add(Z.blip(1400, 0.06, 'pulse', 0.3), TL.T_WILD + k * 0.35, 0.03, -0.3)
    # tap tap + smoke + discovery
    for k in range(3): Q.thud(SX, TL.T_TAP + k * 0.13, size=0.3, gain=0.2, pan=-0.4)
    n = ns(0.8); SX.add(Z.fft_filter(Z.noise(0.8, 3), lo=200, hi=1500) * np.linspace(1, 0, n), TL.T_SMOKE, 0.08, -0.4)
    Q.box_open(SX, TL.T_BANNER, gain=0.03) if hasattr(Q, 'box_open') else None
    Q.fanfare(SX, TL.T_BANNER + 0.05, gain=0.6)
    # into the ear -> the tower
    Q.whoosh(SX, TL.T_EXIT_GHOST, d=1.0, gain=0.08, f0=300, f1=3000)
    SX.add(Z.glide_tone(500, 1800, 0.9, 'sine', 1.0), TL.T_EXIT_GHOST + 0.1, 0.03)
    Q.impact(SX, TL.T_TOWER, gain=0.4)
    for q in range(8): SX.add(Z.blip(nf(['C5', 'E5', 'G5', 'C6', 'E6', 'G6', 'C7', 'E7'][q]), 0.06, 'pulse', 0.3), TL.T_GLOW + q * 0.07, 0.03, -0.5 + q * 0.14)
    Q.shimmer(SX, TL.T_GLOW, 1.0, gain=0.3)
    # tower theme: busy chiptune (G major 128 bpm), through the three rooms
    bb = 60 / 128; t0 = TL.T_TOWER
    lead = ['D5', 'G5', 'B5', 'D6', 'C6', 'B5', 'A5', 'G5', 'E5', 'G5', 'C6', 'E6', 'D6', 'B5', 'A5', None]
    bass = ['G2', 'G2', 'E2', 'E2', 'C2', 'C2', 'D2', 'D2']
    k = 0
    while t0 + k * bb / 2 < TL.S_EXT2:
        tt = t0 + k * bb / 2
        quiet = TL.T_WAVE - 0.4 <= tt < TL.T_SWEPT + 1.2
        if k % 2 == 0:
            MU.add(Z.chip_note(nf(bass[(k // 4) % 8]), bb * 0.45, 'tri'), tt, 0.10 * (0.4 if quiet else 1), 0.0)
            MU.add(Z.kick_chip(0.12, 140, 50, 0.6), tt, 0.14 if (k % 4 == 0 and not quiet) else 0.0)
        n = lead[k % 16]
        if n and k % 2 == 0 and not quiet: MU.add(Z.chip_note(nf(n), bb * 0.4, 'pulse', 0.25), tt, 0.035, 0.15)
        MU.add(Z.hat_chip(0.03, 0.4, k), tt, 0.012, -0.2)
        k += 1
    # archive: cards whoosh into drawers, the memory card + PERMANENT stamp
    for i in range(14):
        tt = TL.S_ARCH + 0.15 + i * 0.22
        SX.add(Z.blip(1800 + 200 * (i % 3), 0.03, 'pulse', 0.3), tt + 0.5, 0.012, -0.4 + 0.06 * i)
    Q.pop(SX, TL.T_CARD_UP, gain=0.08); Q.paper_flip(SX, TL.T_CARD_UP + 0.05, gain=0.3)
    Q.stamp(SX, TL.T_CARD_STAMP, gain=0.8); Q.sigh(SX, TL.T_CARD_STAMP + 0.1, gain=0.04)
    Q.whoosh(SX, TL.T_CARD_STAMP + 0.55, d=0.3, gain=0.05, f0=800, f1=3000)
    # emotion: dryer rumble + thunder, ding, poof, towel
    n = ns(TL.T_POP - TL.S_EMO)
    hum = Z.osc('saw', 55, TL.T_POP - TL.S_EMO) * 0.3 + Z.fft_filter(Z.noise(TL.T_POP - TL.S_EMO, 5), lo=100, hi=700)
    SX.add(hum * np.minimum(1, np.arange(n) / 2000) * (0.7 + 0.3 * np.sin(np.arange(n) / 44100 * 2 * np.pi * 2.3)), TL.S_EMO, 0.05, 0.4)
    for q in range(3): Q.thud(SX, TL.S_EMO + 0.2 + q * 0.7, size=0.4, gain=0.12, pan=0.5)
    Q.ding(SX, TL.T_POP, gain=0.12, note='A6'); Q.whoosh(SX, TL.T_POP + 0.05, d=0.4, gain=0.06, f0=2000, f1=400)
    Q.pop(SX, TL.T_TOWEL, gain=0.1); Q.coin(SX, TL.T_TOWEL + 0.2, gain=0.04)
    # basement: drip, salute, lever, alarm, gate grind, wave, splash, drips
    for q in range(8): Q.plop(SX, TL.S_BASE + 0.2 + q * 0.45, gain=0.15, seed=q)
    Q.jump(SX, TL.T_SALUTE, gain=0.3)
    Q.clack(SX, TL.T_VALVE, size=0.7, gain=0.6)
    for q in range(int((TL.T_WAVE + 1.0 - TL.T_VALVE) / 0.5)):
        SX.add(Z.glide_tone(700, 950, 0.25, 'pulse', 0.4), TL.T_VALVE + q * 0.5, 0.025, 0.0)
    grind = Z.fft_filter(Z.noise(TL.T_WAVE - TL.T_GATE, 21), lo=60, hi=500)
    SX.add(grind * (0.6 + 0.4 * np.sin(np.arange(len(grind)) / 44100 * 2 * np.pi * 9)), TL.T_GATE, 0.10)
    n = ns(4.0); water = Z.fft_filter(Z.noise(4.0, 11), lo=150, hi=5000) * np.minimum(1, np.arange(n) / 4000) * np.linspace(1, 0.35, n)
    SX.add(water, TL.T_WAVE - 0.2, 0.16, 0.0)
    Q.impact(SX, TL.T_WAVE, gain=0.5); Q.crash(SX, TL.T_SWEPT, gain=0.08, d=1.0)
    SX.add(Z.glide_tone(900, 300, 0.7, 'pulse', 0.5), TL.T_SWEPT, 0.04)
    Q.fanfare(SX, TL.T_CHEER, gain=0.3)
    Q.plop(SX, TL.T_SWEPT + 1.6, gain=0.5); Q.dizzy(SX, TL.T_SWEPT + 2.0, d=0.6, gain=0.3)
    # maintenance: sign flicker, everything calms; achievement
    for k in range(4): SX.add(Z.blip(900 - k * 100, 0.04, 'pulse', 0.3), TL.T_SIGN + k * 0.07, 0.03)
    Q.tension_pad(MU, TL.S_EXT2, TL.S_SCHED - TL.S_EXT2, gain=0.05, notes=('G2', 'D3', 'B3', 'F#4'))
    Q.fanfare(SX, TL.T_ACH, gain=0.7); Q.coin(SX, TL.T_ACH + 1.3, gain=0.05); Q.ui_slide(SX, TL.T_ACH + 1.0, gain=0.04, pan=0.6)
    # schedule: bars pop, marker squeak, blocks fall
    for i in range(5): SX.add(Z.blip(nf(['C5', 'D5', 'E5', 'G5', 'A5'][i]), 0.06, 'pulse', 0.25), TL.T_SCHED + 0.2 + i * 0.3, 0.04)
    Q.highlighter(SX, TL.T_STRIKE, gain=0.8) if hasattr(Q, 'highlighter') else None
    for i in range(3): Q.thud(SX, TL.T_FALL + 0.3 + i * 0.12, size=0.4, gain=0.25)
    Q.fail_wah(SX, TL.T_FALL + 0.4, gain=0.5)
    Q.tension_pad(MU, TL.S_SCHED, TL.S_HUB - TL.S_SCHED, gain=0.045, notes=('D3', 'A3', 'C4', 'F4'))
    Q.ui_slide(SX, TL.T_Q, gain=0.05, pan=0.0); Q.result_ding(SX, TL.T_ANS, gain=0.4)
    Q.fanfare(SX, TL.T_REVIVE, gain=0.55); Q.shimmer(SX, TL.T_REVIVE, 1.2, gain=0.3)
    # hub
    Q.shimmer(SX, TL.S_HUB, 1.2, gain=0.4); Q.result_ding(SX, TL.T_CLEAR, gain=0.8); Q.big_ding(SX, TL.T_NEXT, gain=0.4)
    Q.boing(SX, TL.T_BTN, gain=0.02, f=600); Q.chuckle(SX, TL.T_BTN + 0.25, gain=0.03) if hasattr(Q, 'chuckle') else None
    Q.tension_pad(MU, TL.S_HUB, TL.END - TL.S_HUB, gain=0.05, notes=('C3', 'G3', 'D4', 'E4'))
    Q.whoosh(SX, TL.T_GO, d=1.0, gain=0.06, f0=300, f1=1800); Q.riser(SX, TL.T_GO + 0.4, TL.END, gain=0.09, f0=300, f1=8000)
    # voice + mix
    A0.vo_track(VB, TL.L)
    nn = MU.x.shape[0]; duck = A0.duck_env(TL.L, nn, depth=0.5)
    mix = MS.wet(MU, 1.3, 0.25, 1) * duck + MS.wet(SX, 0.9, 0.2, 2) + MS.wet(VB, 0.35, 0.06, 3) * 1.25 + AMB.x
    return MS.finalize(mix[:ns(DUR)].copy(), target_lufs=-16.5, verbose=verbose)

if __name__ == '__main__':
    y = build(); MS.write_wav(OUT + '/s2_audio.wav', y); print('ok', len(y) / Z.SR)
