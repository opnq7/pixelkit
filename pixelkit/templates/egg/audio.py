"""EGG · 王工的请假条 (28.4 s) - sound design + music, every cue from timeline.py.

    python3 audio.py      -> /data/projects/claude_dayoff/out/egg_audio.wav (+ section report)

WIDE   Friday 22:47, lights off: night office bed (air, mains hum, one far car), two keyboards (Wang right, Claude left);
       Wang stops, a long breath, chair creak as he turns; a cold, very soft D pad under it all.
C_CU   好的！ + coin (identical to Act I); 请假事由是？
W_CU   cloth as his hand goes to the frame, a tiny tap on its glass; ……想看看周末长什么样。 (slow); shoulders drop = exhale.
C_MED  fast keys -> Enter, the 'sent' swish + ding; 已提交。 | the bobber: one music-box note | 周末快乐。 ^ ^ sparkle.
INS    the room goes quiet; glint = shimmer; badge slides in; 在线 -> 休假中 = status_flip (off) + a music-box phrase in D;
       the photo warms: a warm pad swells and the river pre-laps under it (0.9 s).
RIVER  hard cut: golden-hour river (water, air, a far bird or two), Act IV's guitar - a Dmaj9 roll as the film lets go;
       来啦。 (old man) / 爸。 (Wang); wings as the flock crosses the sun; the last D chord at T_CHORD; fade with the picture.
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/egg'))
import numpy as np
from pixelkit.audio import synth as Z, music as M, cues as Q, master as MS
from pixelkit.audio.synth import ns, nf
import timeline as TL

DUR = TL.DUR
OUT = (_PROJ + '/out/egg_audio.wav')
P_CL, P_W = -0.2, 0.45                      # wide: Claude left of centre, Wang right
P_OM, P_WR = 0.15, -0.15                    # river: old man right, Wang left

CH = {'D9': ('D2', 'A2', 'D3', 'F#3', 'A3', 'E4'), 'D': ('D2', 'A2', 'D3', 'F#3', 'C#4', 'E4')}

def roll(bus, ch, t, vel, seed, ring=4.5, spread=0.05):
    bus.add(Z.pluck(nf(ch[0]), ring, vel, 0.42, seed=seed), t, 0.62, pan=-0.25)
    for s in range(1, 6):
        bus.add(Z.pluck(nf(ch[s]), ring - 0.5, vel * 0.62, 0.4, seed=seed + s), t + spread * s, 0.5, pan=-0.2 + 0.08 * s)

def tiny(bus, t, f, gain=0.004, pan=0.0, d=0.05, kind='tri', glide=-1.0):
    bus.add(Z.blip(f, d, kind, 0.4, 1.0, glide=glide), t, gain, pan=pan)

def voices(VO):
    for bx in TL.BOXES:
        river = bx['t_open'] > TL.T_RIVER
        Q.box_open(VO, bx['t_open'] - 0.12, gain=0.012 if river else 0.018, low=river)
        for ln in bx['lines']:
            w = ln['who']
            if w == 'old':
                Q.voice_line(VO, ln['zh'], ln['t0'], ln['cps'], gain=0.04, shift=-14, kind='tri', seed=9, d=0.085,
                             times=ln['times'], pan=P_OM)
            elif w.startswith('wang'):
                Q.voice_line(VO, ln['zh'], ln['t0'], ln['cps'], gain=0.03, shift=-9, kind='tri', seed=31, d=0.07,
                             times=ln['times'], pan=P_WR if river else (P_W if ln['t0'] < TL.T_C_CU else 0.0))
            else:
                Q.voice_line(VO, ln['zh'], ln['t0'], ln['cps'], gain=0.04, shift=-5, kind='tri', seed=4, times=ln['times'],
                             question=ln['zh'].endswith('？'), pan=0.0)

def build(verbose=True):
    B = lambda: Z.Bus(DUR)
    AMB, FX, FX2, MU, VO = B(), B(), B(), B(), B()       # the office (dissolves out over the INS -> RIVER dissolve)
    RV, RX, GT, PAD = B(), B(), B(), B()                 # the river
    TR = TL.T_RIVER
    X0, X1 = TR - TL.D_IN / 2, TR + TL.D_IN / 2            # the picture dissolve

    # ================================================================ WIDE
    Q.night_bed(AMB, 0.0, X1, gain=1.0, car_at=1.8, car_d=3.2, fade_in=1.0, fade_out=TL.D_IN)
    Q.room_tone(AMB, 0.0, TR + 0.1, hum=0.003, air=0.006, fade=0.8)
    Q.typing(FX, 0.15, TL.T_W_STOP, 9, 7, gain=0.028, pan=P_W, seed=3)              # Wang's laptop, slowing ...
    Q.typing(FX, 0.3, TL.T_C_HEAR, 12, 12, gain=0.022, pan=P_CL, seed=8)            # Claude, steady
    Q.sigh(FX, TL.T_W_RUB0, d=0.9, gain=0.016, pan=P_W, seed=2)                     # the long breath
    Q.creak(FX, TL.T_W_TURN - 0.1, gain=0.010, pan=P_W, seed=5, d=0.3, f0=230, f1=180)
    Q.swish(FX, TL.T_W_TURN, d=0.3, gain=0.004, pan=P_W, seed=6, f0=300, f1=900)
    tiny(FX, TL.T_C_HEAR + 0.05, 1500, 0.003, P_CL)                                 # Claude looks over
    Q.ui_slide(FX, TL.T_HUD_IN, gain=0.012, pan=-0.6); Q.pop(FX, TL.T_HUD_IN + 0.12, gain=0.008, pan=-0.6)
    Q.pad_swell(MU, 0.4, TL.T_INS - 0.2, notes=('D3', 'A3', 'E4', 'F#4'), gain=0.010, a=2.5, r=1.0, cutoff=700, seed=3)

    # ================================================================ C_CU
    Q.ok(FX, TL.T_OK, gain=1.0, pan=0.0)
    Q.coin(FX, TL.T_OK + 0.30, gain=0.032, pan=0.1)
    Q.jump(FX, TL.T_OK, gain=0.12, f0=440, f1=880, d=0.08)
    Q.soft_land(FX, TL.T_OK + 0.3, size=0.15, gain=0.25)

    # ================================================================ W_CU
    Q.swish(FX, TL.T_REACH0, d=0.45, gain=0.006, pan=0.25, seed=11, f0=250, f1=900)          # sleeve
    FX.add(Z.fft_filter(Z.noise(0.015, 120), 2500, 7000) * Z.expdec(ns(0.015), 0.004), TL.T_REACH1 - 0.02, 0.006, pan=0.3)
    FX2.add(Z.music_box(nf('A5'), 2.6, 1.0), TL.T_REACH1 + 0.05, 0.010, pan=0.3)              # a soft note: the photo
    Q.swish(FX, TL.T_UNREACH0, d=0.35, gain=0.004, pan=0.25, seed=12, f0=250, f1=800)
    Q.sigh(FX, TL.T_RELAX, d=0.7, gain=0.010, pan=0.0, seed=7)

    # ================================================================ C_MED
    Q.typing(FX, TL.T_TYPE0, TL.T_SUBMIT - 0.06, 22, 26, gain=0.035, pan=0.0, seed=13)
    Q.key(FX, TL.T_SUBMIT, gain=0.2, pan=0.0, seed=40)                                        # Enter
    Q.whoosh(FX, TL.T_SUBMIT + 0.05, 0.3, gain=0.025, pan=-0.3, f0=900, f1=3500, seed=21)
    Q.result_ding(FX, TL.T_SUBMIT + 0.1, gain=0.35, pan=-0.3)
    Q.sparkle(FX2, TL.T_SUBMIT + 0.12, 0.4, 0.006, -0.2, seed=3)
    FX2.add(Z.music_box(nf('D6'), 2.4, 1.0), TL.T_LOOK_BOB + 0.08, 0.020, pan=0.25)          # the bobber
    Q.boing(FX, TL.T_LOOK_BACK, gain=0.004, f=980)
    Q.sparkle(FX2, TL.T_LOOK_BACK + 0.15, 0.5, 0.008, 0.0, seed=9)
    FX2.add(Z.music_box(nf('F#6'), 2.4, 1.0), TL.T_LOOK_BACK + 0.2, 0.016, pan=0.0)

    # ================================================================ INS
    Q.shimmer(FX2, TL.T_GLINT0, TL.T_GLINT1 - TL.T_GLINT0 + 0.3, gain=0.22, pan=0.2, seed=5)
    Q.ui_slide(FX, TL.T_BADGE_IN, gain=0.016, pan=0.6); Q.pop(FX, TL.T_BADGE_IN + 0.12, gain=0.012, pan=0.6)
    Q.status_flip(FX, TL.T_FLIP, gain=0.7, pan=0.6, on=False)
    for (dt, nn, g) in ((0.35, 'D6', 0.022), (0.7, 'F#6', 0.020), (1.05, 'A6', 0.020), (1.4, 'E6', 0.018), (1.95, 'D6', 0.020)):
        FX2.add(Z.music_box(nf(nn), 2.6, 1.0), TL.T_FLIP + dt, g, pan=0.1)
    Q.pad_swell(MU, TL.T_WARM0, TR - TL.T_WARM0 + 0.2, notes=('D3', 'A3', 'F#4', 'E5'), gain=0.022, a=2.0, r=0.2,
                cutoff=1000, seed=6)
    Q.riser(FX, TL.T_WARM0 + 0.6, X0 + 0.15, gain=0.006, f0=300, f1=1600, seed=8)

    # ================================================================ RIVER (pre-lap 0.9 s under the warm photo)
    Q.river_bed(RV, TR - 0.9, DUR + 0.3, gain=2.4, seed=91, crickets=False, fade_in=0.9, fade_out=0.8)
    Q.wind(RV, TR, DUR + 0.3, gain=0.010, seed=44, fade=0.6)
    Q.birds(RX, TR + 0.6, TL.T_FADE0, rate=0.35, gain=0.006, seed=17)
    roll(GT, CH['D9'], TR + TL.FILM_HOLD + 0.05, 0.42, seed=500, ring=6.0, spread=0.09)       # as the film lets go
    Q.pad_swell(PAD, TR, DUR - TR + 0.3, notes=('D3', 'A3', 'F#4', 'E5'), gain=0.020, a=1.5, r=1.2, cutoff=900, seed=8)
    for (t, nn, g) in ((TL.T_OLD_TURN0 + 0.1, 'A5', 0.016), (TL.T_W_TURN0 + 0.15, 'F#6', 0.016)):
        RX.add(Z.music_box(nf(nn), 2.6, 1.0), t, g, pan=0.0)
    for i in range(5):                                                                        # wings over the sun
        tt = TL.T_FLOCK + 0.4 + 0.42 * i
        RX.add(Z.fft_filter(Z.noise(0.16, 300 + i), 300, 1600) * np.hanning(ns(0.16)), tt, 0.004, pan=-0.2 + 0.12 * i)
    Q.shimmer(RX, TL.T_AGE0, TL.T_AGE1 - TL.T_AGE0 + 0.4, gain=0.10, pan=0.0, seed=27)          # 30 years go by
    Q.sparkle(RX, TL.T_AGE1 + 0.3, 0.6, 0.003, 0.15, seed=12)                                        # glints on the water
    Q.sparkle(RX, TL.T_W_TURN1 + 0.2, 0.6, 0.003, 0.2, seed=13)
    roll(GT, CH['D'], TL.T_CHORD, 0.36, seed=600, ring=5.5, spread=0.11)

    voices(VO)

    # ================================================================ mix
    duck = np.ones(ns(DUR) + Z.SR * 3)
    for bx in TL.BOXES: duck[ns(bx['t_open']):ns(bx['t_close'])] = 0.8
    k = np.ones(ns(0.3)) / ns(0.3); duck = np.convolve(duck, k, mode='same')[:, None]
    office = (MS.wet(MU, 2.2, 0.35, 1) * duck[:len(MU.x)] + MS.wet(FX, 0.8, 0.18, 2) + MS.wet(FX2, 2.6, 0.5, 3) + AMB.x)
    office = MS.cut(MS.fade(office, X0, X1, curve=1.0), X1)
    vo = MS.wet(VO, 0.6, 0.2, 4)
    rv = RV.x.copy()
    t = np.arange(len(rv)) / Z.SR
    rv *= (0.35 + 0.65 * np.clip((t - X0) / (X1 - X0), 0, 1))[:, None]                        # pre-lap: quiet, then up with the dissolve
    river = (rv + MS.wet(RX, 2.0, 0.35, 5) + MS.wet(GT, 2.6, 0.35, 6, damp=3800) * duck[:len(GT.x)]
             + MS.wet(PAD, 3.0, 0.5, 7) * duck[:len(PAD.x)])
    mix = (office + vo + river)[:ns(DUR)].copy()
    mix = MS.fade(mix, 0.0, TL.T_FADE_IN, curve=1.0, out=False)
    mix = MS.fade(mix, TL.T_FADE0 + 0.2, DUR, curve=1.3)
    y = MS.finalize(mix, target_lufs=-16.5, verbose=verbose)
    if verbose:
        MS.report(y, [(0, TL.T_C_CU, 'WIDE'), (TL.T_C_CU, TL.T_W_CU, 'C_CU'), (TL.T_W_CU, TL.T_C_MED, 'W_CU'),
                      (TL.T_C_MED, TL.T_INS, 'C_MED'), (TL.T_INS, TR, 'INS'), (TR, DUR, 'RIVER')])
    return y


if __name__ == '__main__':
    y = build()
    MS.write_wav(OUT, y)
    print('wrote', OUT, f'{len(y) / Z.SR:.3f}s')
