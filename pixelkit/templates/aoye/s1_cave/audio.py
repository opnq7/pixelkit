"""第 1 关声音。 python3 audio.py -> out/s1_audio.wav"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s1_cave'))
import numpy as np
from pixelkit.audio import synth as Z, cues as Q, master as MS
from pixelkit.audio.synth import ns, nf
import timeline as TL
from common import OUT
import importlib.util
spec = importlib.util.spec_from_file_location('a0', (_PROJ + '/s0_open/audio.py')); A0 = importlib.util.module_from_spec(spec); spec.loader.exec_module(A0)

DUR = TL.DUR + 0.6

def build(verbose=True):
    B = lambda: Z.Bus(DUR)
    MU, SX, VB, AMB = B(), B(), B(), B()
    # ---- cave bed: low wind + drips through the whole level (not in the hub)
    Q.room_tone(AMB, 0.0, TL.S_EXIT, hum=0.003, air=0.012, fade=0.5)
    rng = np.random.default_rng(2)
    t = 0.6
    while t < TL.S_EXIT:
        AMB.add(Z.water_plop(0.5, int(t * 10)), t, 0.05, rng.uniform(-0.7, 0.7)); t += rng.uniform(0.9, 2.2)
    # ---- descent: whoosh down + depth ticks
    Q.whoosh(SX, 0.2, d=3.2, gain=0.05, f0=2000, f1=200, seed=3)
    for i in range(9): SX.add(Z.blip(nf('E5') * (1 - i * 0.04), 0.03, 'pulse', 0.3), 0.5 + i * 0.36, 0.02, 0.6)
    # ---- music: expedition theme, D minor 76 bpm (plucks + marimba-ish music box + soft pad)
    bpm = 76; b = 60 / bpm
    prog = [('D3', 'A3', 'F4'), ('A#2', 'F3', 'D4'), ('C3', 'G3', 'E4'), ('A2', 'E3', 'C#4')]
    mel = ['A4', None, 'D5', 'E5', 'F5', None, 'E5', 'D5', 'C5', None, 'A4', None, 'E5', None, 'C#5', None]
    def theme(t0, t1, gain=1.0, melody=True):
        k = 0
        while t0 + k * b < t1:
            tt = t0 + k * b; ch = prog[(k // 4) % 4]
            if k % 4 == 0:
                MU.add(Z.pad([nf(n) for n in ch], b * 4.2, 'saw', 0.6, a=0.4, r=0.6, cutoff=1100), tt, 0.035 * gain)
                MU.add(Z.pluck(nf(ch[0]) / 2, 2.5, 0.9, 0.4, k), tt, 0.12 * gain, -0.1)
            if k % 2 == 1: MU.add(Z.pluck(nf(ch[1]), 1.2, 0.6, 0.6, k), tt, 0.05 * gain, 0.2)
            n = mel[k % 16]
            if melody and n: MU.add(Z.music_box(nf(n), 1.0, 0.8), tt, 0.045 * gain, 0.1)
            k += 1
    theme(0.4, TL.S_VS - 0.1)
    # ---- possession
    Q.whoosh(SX, TL.T_POSSESS, d=0.45, gain=0.12, f0=500, f1=4000, seed=5)
    Q.impact(SX, TL.T_HIT, gain=0.55); Q.big_ding(SX, TL.T_HIT + 0.02, gain=0.35)
    Q.toast(SX, TL.T_CARD, gain=0.6) if hasattr(Q, 'toast') else None
    # ---- VS: drums
    for tt, g in ((TL.T_SUN, 0.5), (TL.T_VS, 1.0), (TL.T_GEAR, 0.6)):
        SX.add(Z.thud(1.0, True, 1, 110, 40), tt, 0.5 * g); Q.crash(SX, tt, gain=0.05 * g, d=0.8)
    Q.tension_pad(MU, TL.S_VS, TL.S_CHALK - TL.S_VS, gain=0.05, notes=('D2', 'A2', 'D#3', 'G3'))
    for k in range(int((TL.S_CHALK - TL.T_GEAR) / 0.5)):
        Q.tock(SX, TL.T_GEAR + 0.2 + k * 0.5, gain=0.4) if hasattr(Q, 'tock') else None
    # boulder: rumble + boom
    n = ns(TL.T_ROLL1 - TL.T_ROLL0)
    rum = Z.fft_filter(Z.noise(TL.T_ROLL1 - TL.T_ROLL0, 4), hi=180) * np.linspace(0.3, 1, n)
    SX.add(rum, TL.T_ROLL0, 0.5)
    SX.add(Z.thud(1.0, True, 2, 70, 30), TL.T_ROLL1, 0.9); Q.crash(SX, TL.T_ROLL1, gain=0.06, d=1.0)
    # ---- chalk: scratches per segment
    for i in range(28):
        tt = TL.T_CHALK0 + (TL.T_CHALK1 - TL.T_CHALK0) * i / 28
        s = Z.fft_filter(Z.noise(0.08, 100 + i), lo=2000, hi=7000) * Z.expdec(ns(0.08), 0.04)
        SX.add(s, tt, 0.05, 0.3)
    Q.chapter_chime(SX, TL.T_28, gain=0.6)
    theme(TL.S_CHALK + 0.1, TL.S_THERMO - 0.1, 0.8, melody=False)
    # ---- split: snores vs a clock; nod -> bonk
    Q.snore(SX, TL.S_SPLIT + 0.2, d_in=0.7, d_out=0.9, gain=1.4, pan=-0.5, seed=3)
    Q.snore(SX, TL.S_SPLIT + 1.9, d_in=0.7, d_out=0.9, gain=1.4, pan=-0.5, seed=4)
    Q.clock_ticks(SX, TL.S_SPLIT, TL.S_NOD, period=0.5, gain=0.05, pan=0.5)
    Q.bonk(SX, TL.T_BONK, gain=1.0); Q.dizzy(SX, TL.T_BONK + 0.15, gain=0.6) if hasattr(Q, 'dizzy') else None
    # ---- thermometer: rise / fall glides
    SX.add(Z.glide_tone(300, 900, 0.6, 'tri', 0.8), TL.T_DAY, 0.05, 0.0)
    SX.add(Z.glide_tone(900, 280, 0.6, 'tri', 0.8), TL.T_NIGHT - 0.2, 0.05, 0.0)
    Q.tension_pad(MU, TL.S_THERMO, TL.S_EXIT - TL.S_THERMO, gain=0.045, notes=('D3', 'A3', 'C4', 'F4'))
    for i in range(12):
        SX.add(Z.blip(nf('A5'), 0.02, 'pulse', 0.3), TL.S_GRAPH + 0.2 + i * 0.22, 0.012, -0.3)
    Q.tock(SX, TL.T_GEAR_CLICK, gain=1.0) if hasattr(Q, 'tock') else None
    SX.add(Z.thud(0.8, False, 3, 300, 120), TL.T_GEAR_CLICK, 0.4)
    # ---- exit: daylight swell, birds, achievement fanfare
    Q.riser(SX, TL.S_EXIT - 0.6, TL.S_EXIT + 0.2, gain=0.05)
    Q.birds(AMB, TL.S_EXIT, TL.S_TRIP, gain=0.02) if hasattr(Q, 'birds') else None
    Q.fanfare(SX, TL.T_ACH, gain=0.7)
    Q.coin(SX, TL.T_ACH + 1.4, gain=0.05)
    Q.ui_slide(SX, TL.T_ACH + 1.2, gain=0.04, pan=0.6)
    theme(TL.S_EXIT + 0.3, TL.S_TRIP, 1.0)
    # ---- triptych: panels whoosh in, gears grind, then jam
    for tt in (TL.T_P1, TL.T_P2, TL.T_P3):
        Q.whoosh(SX, tt - 0.15, d=0.3, gain=0.06, f0=3000, f1=400)
    gr = Z.fft_filter(Z.noise(TL.T_JAM - TL.T_P1, 9), lo=300, hi=2500) * (0.5 + 0.5 * np.sign(np.sin(np.arange(ns(TL.T_JAM - TL.T_P1)) / 44100 * 2 * np.pi * 9)))
    SX.add(gr, TL.T_P1, 0.02)
    Q.error_buzz(SX, TL.T_JAM, gain=0.6); SX.add(Z.thud(1.0, True, 5, 90, 40), TL.T_JAM, 0.5)
    Q.tension_pad(MU, TL.S_TRIP, TL.S_HUB - TL.S_TRIP, gain=0.05, notes=('A2', 'E3', 'G3', 'A#3'))
    Q.ui_slide(SX, TL.T_Q, gain=0.05, pan=0.0); Q.result_ding(SX, TL.T_ANS, gain=0.5)
    Q.fanfare(SX, TL.T_REVIVE, gain=0.55); Q.shimmer(SX, TL.T_REVIVE, 1.2, gain=0.3)
    # ---- hub
    Q.shimmer(SX, TL.S_HUB, 1.2, gain=0.4)
    Q.result_ding(SX, TL.T_CLEAR, gain=0.8)
    Q.big_ding(SX, TL.T_NEXT, gain=0.4)
    Q.question(SX, TL.T_NEXT + 0.3, gain=0.05)
    Q.tension_pad(MU, TL.S_HUB, TL.END - TL.S_HUB, gain=0.05, notes=('C3', 'G3', 'D4', 'E4'))
    Q.whoosh(SX, TL.T_GO, d=1.0, gain=0.06, f0=300, f1=1800)
    Q.riser(SX, TL.T_GO + 0.5, TL.END, gain=0.09, f0=300, f1=8000)
    # ---- voice + mix
    A0.vo_track(VB, TL.L)
    nn = MU.x.shape[0]
    duck = A0.duck_env(TL.L, nn, depth=0.5)
    mix = MS.wet(MU, 1.4, 0.25, 1) * duck + MS.wet(SX, 0.9, 0.2, 2) + MS.wet(VB, 0.35, 0.06, 3) * 1.25 + AMB.x
    mix = mix[:ns(DUR)].copy()
    return MS.finalize(mix, target_lufs=-16.5, verbose=verbose)

if __name__ == '__main__':
    y = build(); MS.write_wav(OUT + '/s1_audio.wav', y); print('ok', len(y) / Z.SR)
