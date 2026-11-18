"""油画转场小样 (~11 s) - music + sound design, every cue scheduled from timeline.py.

    python3 audio.py      -> ../out/paint_test_audio.wav

PIXEL   river bed (water lapping, air, two crickets); nylon guitar fingerpicking 70 bpm (Dmaj7 - Bm7 - Gmaj7 - A)
UI      settings panel slides in, the switch clicks 关, panel slides away  (the last 'electronic' sounds of the scene)
DIP     the bobber dips (plop) -> the ripple: a soft shimmer swell
PAINT   the reverb opens up as the paint spreads, a solo piano melody enters, the river bed sinks back,
        a warm pad; first star = two music-box notes; ends on A (unresolved) under the fade
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/paint_test'))
import numpy as np
from pixelkit.audio import synth as Z, cues as Q, master as MS
from pixelkit.audio.synth import ns, nf
import timeline as TL

DUR = TL.DUR
OUT = (_PROJ + '/out/paint_test_audio.wav')
BPM = 70.0; BEAT = 60.0 / BPM; BAR = 4 * BEAT; T0 = 0.15
P_BOB, P_CL = 0.25, 0.1
CHORDS = [('D2', 'A2', 'D3', 'F#3', 'C#4', 'E4'),       # Dmaj7(9)
          ('B1', 'F#2', 'B2', 'D3', 'A3', 'C#4'),       # Bm7(9)
          ('G1', 'D2', 'G2', 'B2', 'F#3', 'A3'),        # Gmaj7(9)
          ('A1', 'E2', 'A2', 'C#3', 'E3', 'B3')]        # A(add9)
PICK = [(0.0, 0), (0.5, 2), (1.0, 4), (1.5, 3), (2.0, 5), (2.5, 3), (3.0, 4), (3.5, 2)]   # (beat, string idx)
MEL = [(1, 0.0, 'F#5', 1.5), (1, 1.5, 'E5', 0.5), (1, 2.0, 'D5', 1.0), (1, 3.0, 'A4', 1.0),
       (2, 0.0, 'B4', 1.5), (2, 1.5, 'D5', 0.5), (2, 2.0, 'F#5', 2.0),
       (3, 0.0, 'E5', 3.0)]

def bar_t(i, b=0.0): return T0 + i * BAR + b * BEAT

def env(t_pts, v_pts):
    tt = np.arange(ns(DUR) + Z.SR * 2) / Z.SR
    return np.interp(tt, t_pts, v_pts)[:, None]

def build(verbose=True):
    B = lambda: Z.Bus(DUR)
    AMB, GT, PI, PAD, FX, VO = B(), B(), B(), B(), B(), B()

    # ---------------------------------------------------------------- river + guitar
    Q.river_bed(AMB, 0.0, DUR + 0.5, gain=2.6, fade_in=0.5, fade_out=1.0)
    for i, ch in enumerate(CHORDS):
        for (b, s) in PICK:
            t = bar_t(i, b)
            if t > DUR: break
            if i == 3 and b > 0: break                                # the last chord rings, unresolved
            vel = (0.95 if b == 0 else 0.55 + 0.1 * (b % 1 == 0)) * (0.8 if i >= 2 else 1.0)
            GT.add(Z.pluck(nf(ch[s]), 3.2 if b == 0 else 2.2, vel, 0.42, seed=i * 10 + s), t + 0.012 * (s % 2), 0.62,
                   pan=-0.25 + 0.08 * s)
        if i == 3:
            for s in range(1, 6): GT.add(Z.pluck(nf(ch[s]), 3.5, 0.5, 0.4, seed=90 + s), bar_t(3) + 0.035 * s, 0.5, pan=-0.2 + 0.08 * s)

    # ---------------------------------------------------------------- UI: 消息提醒 -> 关
    Q.ui_slide(FX, TL.T_UI_IN, gain=0.022, pan=P_CL)
    Q.pop(FX, TL.T_UI_IN + 0.12, gain=0.035, pan=P_CL)
    Q.switch_click(FX, TL.T_CLICK, gain=0.55, pan=P_CL)
    Q.pop(FX, TL.T_CLICK + 0.03, gain=0.03, pan=P_CL, up=False)
    FX.add(Z.glide_tone(660, 330, 0.25, 'sine', 1.0, 0.7), TL.T_CLICK + 0.05, 0.012, pan=P_CL)   # the bell goes quiet
    Q.ui_slide(FX, TL.T_UI_OUT, gain=0.015, pan=P_CL)

    # ---------------------------------------------------------------- the dip + the ripple
    Q.plop(FX, TL.T_DIP, gain=1.0, pan=P_BOB, seed=3)
    Q.plop(FX, TL.T_DIP + 0.22, gain=0.35, pan=P_BOB, seed=4)
    Q.shimmer(FX, TL.T_RIP, TL.T_FULL - TL.T_RIP + 0.6, gain=1.0, pan=P_BOB, seed=2)
    Q.pad_swell(PAD, TL.T_RIP + 0.3, DUR - TL.T_RIP, notes=('B2', 'F#3', 'D4', 'A4'), gain=0.035, a=2.4, r=1.5, cutoff=1100, seed=6)

    # ---------------------------------------------------------------- piano melody (enters with the paint)
    for (bi, b, nn, d) in MEL:
        t = bar_t(bi, b)
        PI.add(Z.piano(nf(nn), d * BEAT + 1.2, 0.55, 0.7, seed=int(b * 10) + bi), t, 0.13, pan=0.12)
    PI.add(Z.piano(nf('C#4'), 3.0, 0.35, 0.6, seed=77), bar_t(3) + 0.02, 0.10, pan=0.0)

    # ---------------------------------------------------------------- first star + narration
    FX2 = B()
    FX2.add(Z.music_box(nf('A6'), 2.2, 1.0), TL.T_STAR + 0.05, 0.05, pan=-0.45)
    FX2.add(Z.music_box(nf('E7'), 2.4, 1.0), TL.T_STAR + 0.5, 0.035, pan=-0.45)
    for bx in TL.BOXES:
        Q.box_open(VO, bx['t_open'] - 0.12, gain=0.012, low=True)
        for ln in bx['lines']:
            Q.voice_line(VO, ln['zh'], ln['t0'], ln['cps'], gain=0.03, shift=-5, kind='tri', seed=4, times=ln['times'])

    # ---------------------------------------------------------------- mix: the reverb opens up as the paint spreads
    open_ = env([0, TL.T_RIP, TL.T_FULL, DUR + 2], [0.0, 0.0, 1.0, 1.0])
    gt_dry = GT.x; gt_r = MS.wet(GT, 3.2, 1.0, 1, damp=3800) - gt_dry
    gt = gt_dry * (1 - 0.35 * open_) + gt_r * (0.12 + 0.5 * open_)
    pi = MS.wet(PI, 3.4, 0.55, 2, damp=4200)
    pad = MS.wet(PAD, 3.0, 0.5, 3)
    fx = MS.wet(FX, 1.2, 0.25, 4) + MS.wet(FX2, 3.0, 0.6, 5) + MS.wet(VO, 2.0, 0.35, 6)
    amb = AMB.x * (1 - 0.6 * open_)
    mix = (gt + pi + pad + fx + amb)[:ns(DUR)].copy()
    mix = MS.fade(mix, TL.T_FADE0, DUR, curve=1.4)
    y = MS.finalize(mix, target_lufs=-16.5, verbose=verbose)
    if verbose:
        MS.report(y, [(0, TL.T_DIP, 'PIXEL/UI'), (TL.T_DIP, TL.T_FULL, 'RIPPLE'), (TL.T_FULL, DUR, 'PAINT')])
    return y


if __name__ == '__main__':
    y = build()
    MS.write_wav(OUT, y)
    print('wrote', OUT, f'{len(y) / Z.SR:.3f}s')
