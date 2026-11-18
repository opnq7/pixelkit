"""ACT IV v2 · 河边 (~118 s) - sound design + music, every cue scheduled from timeline.py.

    python3 audio.py      -> /data/projects/claude_dayoff/out/act4_audio.wav (+ section report)

Rule (approved): NO music before the oil-paint shot - only water, birds, wood creaks and small acting sounds,
so Claude's restlessness has room.  Music arrives with the decision (a pad pre-laps the 关 click) and paint_v2.

W        river bed (day: no crickets) + birds; wooden footsteps up the pier; 叮 (工作群) - a glance; the stop creaks.
SO       请问……这里可以坐吗？ / 坐。 (cloth swish on the pat gesture); the hop: spring, land creak; fidget knocks,
         the ... blips, the bucket: sparkle -> star ting; antenna boings.
BKT      scan sweep + tick, result 鱼获：0 = a small falling blip.
SIDE2    voices; the optimizer card (slide, a tick burst per row, result ding at 83%); the held-back chuckles (CU_OR);
         那多没意思。 -> a silent beat -> flick swish -> crack -> glassy shatter -> shard plinks on the water.
CU_*     the ? cue; 没意义啊。 + a chuckle; the monologue sits on the river only; INS glint = one music-box note;
         CU_C3 2080: digit ticks, a dim glide; INS2 = silence (water); distant fish plops (scene.jumps).
CU_C2    spinner ticks slow + fade; sigh; — —; 叮 again (ignored, an antenna wobble); servo; toggle; 关 click,
         the bell goes quiet; a warm pad pre-laps the paint.
PAINT    paint_v2's own mix (ui=False), spliced at T_PAINT - PAINT_T0, ~5 dB down.
DUSK     dusk river + crickets; twitch plop, lift drips; reel ratchet; catch; 拿着。 swishes, soft land, scoot creak;
         the happy beat: music-box phrase + Dmaj9 roll (resolves paint_v2's A add9); 嗯。 boing; pad to the end;
         ECHO: a soft shimmer + a last roll beside the sun.  Fade.
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, importlib.util
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/act4'))
import numpy as np
from pixelkit.audio import synth as Z, cues as Q, master as MS
from pixelkit.audio.synth import ns, nf
import timeline as TL
import scene as S                                     # (also loads paint_v2's timeline as pv2_timeline)

DUR = TL.DUR
OUT = (_PROJ + '/out/act4_audio.wav')
PAINT_OFF = TL.T_PAINT - TL.PAINT_T0                  # act time of paint_v2 local 0
P_CL, P_OM = -0.18, 0.2                               # Claude sits left of the old man (two-shots)
PAINT_GAIN = 0.55
HOP = TL.T_HOP
TWO_SHOTS = [(TL.T_SO, TL.T_BKT), (TL.T_SIDE2, TL.T_CU_OR0), (TL.T_CU_OR1, TL.T_CU_C1), (TL.T_SIDE_H, TL.T_BADGE),
             (TL.T_SIDE_H2, TL.T_CU_H), (TL.T_END, DUR)]
def two(t): return any(a <= t < b for a, b in TWO_SHOTS)
def pan_cl(t): return P_CL if two(t) else 0.0
def pan_om(t): return P_OM if two(t) else 0.0

CH = {'D9': ('D2', 'A2', 'D3', 'F#3', 'A3', 'E4'), 'G': ('G1', 'D2', 'G2', 'B2', 'F#3', 'A3'),
      'D': ('D2', 'A2', 'D3', 'F#3', 'C#4', 'E4')}

def roll(bus, ch, t, vel, seed, ring=4.5, spread=0.05):
    bus.add(Z.pluck(nf(ch[0]), ring, vel, 0.42, seed=seed), t, 0.62, pan=-0.25)
    for s in range(1, 6):
        bus.add(Z.pluck(nf(ch[s]), ring - 0.5, vel * 0.62, 0.4, seed=seed + s), t + spread * s, 0.5, pan=-0.2 + 0.08 * s)

def voices(VO):
    for bx in TL.BOXES:
        Q.box_open(VO, bx['t_open'] - 0.12, gain=0.012, low=True)
        for ln in bx['lines']:
            if ln['who'] == 'old':
                Q.voice_line(VO, ln['zh'], ln['t0'], ln['cps'], gain=0.04, shift=-14, kind='tri', seed=9, d=0.085,
                             times=ln['times'], pan=pan_om(ln['t0']))
            else:
                Q.voice_line(VO, ln['zh'], ln['t0'], ln['cps'], gain=0.03, shift=-5, kind='tri', seed=4, times=ln['times'],
                             question=ln['zh'].endswith('？'), pan=pan_cl(ln['t0']))

def tiny(FX, t, f, gain=0.006, pan=0.0, d=0.05, kind='tri', glide=-1.0):
    FX.add(Z.blip(f, d, kind, 0.4, 1.0, glide=glide), t, gain, pan=pan)

def card_fx(FX, A4):
    pc = -0.5
    Q.ui_slide(FX, TL.T_CARD_IN, gain=0.025, pan=pc)
    Q.pop(FX, TL.T_CARD_IN + 0.1, gain=0.03, pan=pc)
    for k, r in enumerate(TL.CARD_ROWS):
        Q.progress_ticks(FX, r, r + 0.32, rate=24, gain=0.55, pan=pc, f=1700 + 120 * k, seed=k)
        Q.pop(FX, r + 0.33, gain=0.022, pan=pc)
    Q.result_ding(FX, TL.T_RATE, gain=0.45, pan=pc)
    Q.sparkle(FX, TL.T_RATE + 0.05, 0.4, 0.008, pc, seed=5)
    Q.swish(FX, TL.T_FLICK0 + 0.12, d=0.18, gain=0.014, pan=0.25, seed=11, f0=900, f1=3200)       # the flick
    cr = Z.fft_filter(Z.noise(0.07, 71), 2500, 9000) * Z.expdec(ns(0.07), 0.012)
    FX.add(cr, TL.T_CRACK, 0.09, pan=pc)
    FX.add(Z.glide_tone(2400, 1500, 0.09, 'tri', 1.0, 0.7) * Z.expdec(ns(0.09), 0.03), TL.T_CRACK + 0.01, 0.006, pan=pc)
    cr2 = Z.fft_filter(Z.noise(0.25, 72), 1800, 10000) * Z.expdec(ns(0.25), 0.05)
    FX.add(cr2, TL.T_SHATTER, 0.07, pan=pc)
    g = np.random.default_rng(7)
    for j in range(9):
        f = nf(['E7', 'B6', 'G#6', 'E6', 'C#7', 'F#6', 'B5', 'A6', 'D#7'][j])
        FX.add(Z.bell(f, 0.9, 0.6), TL.T_SHATTER + 0.02 + j * 0.035 + g.uniform(0, 0.02), 0.012 * (1 - j / 12),
               pan=float(g.uniform(-0.7, -0.2)))
    for i, (t, x) in enumerate(A4.hits()):                     # shards hit the water
        FX.add(Z.water_plop(0.8, seed=30 + i, f0=900, f1=2300, d=0.05), t, 0.018, pan=float(np.clip(x / 240 - 1, -0.9, 0.9)))

def build(verbose=True):
    B = lambda: Z.Bus(DUR)
    AMB, GT, PAD, FX, FX2, VO = B(), B(), B(), B(), B(), B()
    A4 = S.make(only=[])

    # ---------------------------------------------------------------- beds
    Q.river_bed(AMB, 0.0, PAINT_OFF + 1.0, gain=2.6, crickets=False, fade_in=0.8, fade_out=1.0)
    Q.birds(AMB, 0.4, 40.0, rate=0.45, gain=0.010, seed=31)
    Q.birds(AMB, 40.0, PAINT_OFF, rate=0.18, gain=0.007, seed=33)
    Q.river_bed(AMB, TL.T_INS_D - 0.3, DUR + 0.5, gain=2.2, seed=91, crickets=True, fade_in=1.2, fade_out=1.0)
    for k, (tj, x, y) in enumerate(A4.side.jumps):             # distant fish jumps (drawn in the bg)
        if TL.T_PAINT - 0.2 <= tj < TL.T_INS_D: continue
        FX.add(Z.water_plop(0.6, seed=50 + k, f0=500, f1=1200, d=0.07), tj, 0.006, pan=float(np.clip((x - 300) / 160, -0.8, 0.8)))

    # ---------------------------------------------------------------- W
    Q.pop(FX, TL.T_HUD_IN, gain=0.012, pan=-0.6)
    Q.digit_ticks(FX, [tt for (tt, _) in TL.CLOCK_TICKS[1:]], gain=0.010, f0=2600, f1=2600, pan=-0.6)
    for k, (t, s) in enumerate(TL.footsteps()):
        x = TL.walk_pos(t)[0]
        Q.step(FX, t, gain=0.010 * s, pan=float(np.clip(x / 240 - 1, -0.8, 0.8)), seed=k, hard=False)
        if k % 3 == 1: Q.creak(FX, t + 0.02, gain=0.004 * s, seed=k, d=0.16, f0=260, f1=220)
    Q.creak(FX, TL.T_ARRIVE + 0.05, gain=0.012, seed=2, d=0.35)                  # he stops: the board gives
    for (t, ph) in [(TL.T_NOTE1, 1), (TL.T_NOTE2, 2)]:
        Q.ding(FX, t, gain=0.035, pan=-0.6, note='E6')
        Q.ui_slide(FX, t + 0.02, gain=0.010, pan=-0.6)
    tiny(FX, TL.T_GLANCE1[0] + 0.05, 1500, 0.003, -0.2)

    # ---------------------------------------------------------------- SO
    tiny(FX, TL.T_SO + 0.35, 1900, 0.004, P_CL); tiny(FX, TL.T_SO + 0.55, 1900, 0.004, P_CL); tiny(FX, TL.T_SO + 0.75, 1900, 0.004, P_CL)
    Q.swish(FX, TL.T_PAT0, d=0.35, gain=0.008, pan=P_OM, seed=21, f0=300, f1=1200)        # the near hand comes out
    for k in range(2):                                                                 # pat, pat (cloth, in the air)
        Q.swish(FX, TL.T_PAT0 + 0.42 + 0.3 * k, d=0.12, gain=0.006, pan=P_OM, seed=22 + k, f0=250, f1=900)
    Q.boing(FX, TL.L_SIT['t0'] + 0.2, gain=0.004, pan=P_CL, f=980)
    Q.jump(FX, HOP + TL.T_TAKE, gain=0.18, pan=P_CL, f0=380, f1=760, d=0.1)
    Q.soft_land(FX, HOP + TL.T_LAND, size=0.25, gain=0.45, pan=P_CL)
    Q.creak(FX, HOP + TL.T_LAND + 0.03, gain=0.016, pan=P_CL, seed=5, d=0.4)
    Q.boing(FX, HOP + TL.T_LAND + 0.05, gain=0.005, pan=P_CL, f=900)
    kprev = 0
    for i in range(int(1.7 * 6)):                                                     # can't sit still: heel knocks
        s = 2.0 + i / 6
        kk = (1, 0, 2, 0)[i % 4]
        if kk and not kprev: Q.step(FX, HOP + s, gain=0.004, pan=P_CL, seed=40 + i, hard=False)
        kprev = kk
    for i in range(13):                                                               # finger taps on the knees
        FX.add(Z.fft_filter(Z.noise(0.01, 80 + i), 600, 2400) * Z.expdec(ns(0.01), 0.003), HOP + 2.0 + i / 8 + 0.01 * (i % 2),
               0.006, pan=P_CL)
    for (s, f) in [(3.7, 1700), (3.82, 1700), (3.95, 1700)]: tiny(FX, HOP + s, f, 0.004, P_CL)
    Q.sparkle(FX, HOP + 6.05, 0.35, 0.007, P_CL, seed=3)
    Q.boing(FX, HOP + 6.05, gain=0.004, pan=P_CL, f=1050)
    FX2.add(Z.music_box(nf('B6'), 1.4, 1.0), HOP + 6.75, 0.022, pan=P_CL)              # star eyes: ting

    # ---------------------------------------------------------------- BKT
    Q.ticker(FX, TL.T_SCAN0, TL.T_SCAN1, rate0=18, rate1=10, gain=0.008, f=3000, pan=0.0)
    FX.add(Z.glide_tone(500, 1600, TL.T_SCAN1 - TL.T_SCAN0, 'sine', 1.0, 0.8) * np.hanning(ns(TL.T_SCAN1 - TL.T_SCAN0)),
           TL.T_SCAN0, 0.004)
    Q.pop(FX, TL.T_RESULT, gain=0.025)
    FX.add(Z.glide_tone(700, 420, 0.28, 'tri', 1.0, 0.8) * Z.expdec(ns(0.28), 0.12), TL.T_RESULT + 0.08, 0.010)  # 鱼获：0

    # ---------------------------------------------------------------- SIDE2 / CU_OR
    Q.sparkle(FX, TL.CARD_ROWS[0] - 0.1, 0.3, 0.005, P_CL, seed=6)
    for (t, n, per) in [(TL.T_CU_OR0 + 0.35, 2, 0.17), (TL.T_CU_OR0 + 1.0, 3, 0.2), (TL.T_RATE + 0.1, 3, 0.18),
                        (TL.L_BORING['t_end'] - 0.1, 2, 0.15)]:
        Q.chuckle(FX, t, n=n, gain=0.014, pan=pan_om(t), seed=int(t * 10), period=per, f=230)
    Q.swish(FX, TL.T_CRACK + 0.02, d=0.2, gain=0.006, pan=P_CL, seed=13)                  # Claude flinches
    card_fx(FX, A4)

    # ---------------------------------------------------------------- CU_C1 .. CU_O2
    Q.question(FX, TL.char_time(TL.L_WHY, '有什么') - 0.05, gain=0.035)
    Q.chuckle(FX, TL.L_NO_POINT['t_end'] + 0.1, n=2, gain=0.012, seed=61, period=0.17, f=230)
    Q.boing(FX, TL.T_CU_CR + 0.05, gain=0.004, f=880)
    FX2.add(Z.music_box(nf('A6'), 2.2, 1.0), TL.T_INS_GLINT, 0.035, pan=0.2)
    Q.sparkle(FX2, TL.T_INS_GLINT, 0.5, 0.006, 0.2, seed=8)
    Q.digit_ticks(FX, [TL.T_CALC_FACE, TL.T_CALC_FACE + 0.08, TL.T_CALC_FACE + 0.16], gain=0.010, f0=2200, f1=3000, pan=0.0)
    Q.digit_ticks(FX, [TL.T_CALC_2, TL.T_CALC_2 + 0.07, TL.T_CALC_2 + 0.14, TL.T_CALC_2 + 0.21], gain=0.011, f0=2600, f1=3800)
    Q.boing(FX, TL.T_CALC_2, gain=0.003, f=800)
    d = TL.T_CALC_DIM1 - TL.T_CALC_DIM0 + 0.2
    FX.add(Z.glide_tone(520, 260, d, 'sine', 1.0, 0.8) * np.hanning(ns(d)), TL.T_CALC_DIM0, 0.005)     # the glow dims
    Q.swish(FX, TL.T_CU_O2 + 0.3, d=0.45, gain=0.007, seed=31, f0=250, f1=900)          # he turns to Claude (cloth)

    # ---------------------------------------------------------------- CU_C2
    lt = TL.load_ticks()
    for k, (t, n) in enumerate(lt):
        u = k / max(1, len(lt) - 1)
        FX.add(Z.blip(2300 * (1.0 if n % 2 else 1.12), 0.012, 'pulse', 0.5, 1.0, 0), t, 0.011 * (1 - 0.65 * u), pan=0.05)
    Q.pop(FX, TL.T_CANCEL, gain=0.012, up=False)
    Q.sigh(FX, TL.T_SIGH, d=0.8, gain=0.02)
    FX.add(Z.glide_tone(330, 220, 0.5, 'sine', 1.0, 0.8) * np.hanning(ns(0.5)), TL.T_CALM, 0.006)
    Q.boing(FX, TL.T_NOTE2 + 0.05, gain=0.003, f=860)
    FX.add(Z.glide_tone(420, 640, 0.14, 'tri', 1.0, 0.8) * np.hanning(ns(0.14)), TL.T_EAR0 + 0.05, 0.004, pan=-0.2)  # servo
    Q.swish(FX, TL.T_EAR0, d=0.3, gain=0.012, pan=-0.2, seed=3)
    Q.ui_slide(FX, TL.T_TOG_IN, gain=0.02, pan=0.3)
    Q.pop(FX, TL.T_TOG_IN + 0.12, gain=0.03, pan=0.3)
    Q.switch_click(FX, TL.T_CLICK, gain=0.55, pan=0.1)
    Q.pop(FX, TL.T_CLICK + 0.03, gain=0.03, pan=0.1, up=False)
    FX.add(Z.glide_tone(660, 330, 0.25, 'sine', 1.0, 0.7), TL.T_CLICK + 0.05, 0.012, pan=0.1)              # the bell goes quiet
    Q.boing(FX, TL.T_CLICK + 0.05, gain=0.003, f=820)
    Q.swish(FX, TL.T_EAR1, d=0.25, gain=0.008, pan=-0.2, seed=4)
    Q.ui_slide(FX, TL.T_TOG_OUT, gain=0.014, pan=0.3)
    Q.pad_swell(PAD, TL.T_CLICK + 0.35, TL.T_PAINT + 1.2 - TL.T_CLICK - 0.35, notes=('D3', 'A3', 'F#4', 'C#5'), gain=0.026,
                a=1.4, r=1.0, cutoff=1000, seed=6)

    # ---------------------------------------------------------------- dusk: INS_D .. ECHO
    Q.plop(FX, TL.T_TWITCH, gain=0.18, pan=0.1, seed=3)
    Q.plop(FX, TL.T_TWITCH + 0.35, gain=0.12, pan=0.1, seed=4)
    FX.add(Z.fft_filter(Z.noise(0.5, 90), 500, 2500) * np.hanning(ns(0.5)), TL.T_LIFT0, 0.008, pan=0.1)   # out of the water
    for i, dt in enumerate((0.25, 0.48, 0.7, 0.95)):
        FX.add(Z.water_plop(0.5, seed=70 + i, f0=1300, f1=2600, d=0.04), TL.T_LIFT0 + dt, 0.008 * (1 - 0.15 * i), pan=0.1)
    Q.reel(FX, TL.T_REEL0, TL.T_REEL1, rate=14, gain=0.016, pan=P_OM)
    Q.swish(FX, TL.T_CATCH - 0.1, d=0.3, gain=0.008, pan=P_OM, seed=51, f0=500, f1=2200)      # the line comes up
    FX.add(Z.water_plop(0.5, seed=77, f0=1300, f1=2600, d=0.04), TL.T_CATCH + 0.2, 0.007, pan=P_OM)
    Q.chuckle(FX, TL.T_SMILE_O + 0.05, n=1, gain=0.010, pan=P_OM, seed=81, f=220)              # an empty hook: hm.
    FX2.add(Z.music_box(nf('F#6'), 1.6, 1.0), TL.T_BADGE + 0.15, 0.016, pan=0.0)              # the badge
    Q.swish(FX, TL.T_GIVE0, d=0.6, gain=0.010, pan=0.1, seed=6, f0=300, f1=1200)
    Q.soft_land(FX, TL.T_DROP + 0.05, size=0.12, gain=0.4, pan=P_CL)
    FX.add(Z.water_plop(0.6, seed=12, f0=1300, f1=2600, d=0.04), TL.T_DROP + 0.3, 0.008, pan=P_CL)   # a drip
    Q.swish(FX, TL.T_WITH0, d=0.6, gain=0.008, pan=P_OM, seed=7, f0=300, f1=1200)
    Q.creak(FX, TL.T_SCOOT0 + 0.05, gain=0.014, pan=P_CL, seed=9, d=0.35, f0=240, f1=170)   # scoots closer
    FX.add(Z.fft_filter(Z.noise(0.35, 95), 300, 1500) * np.hanning(ns(0.35)), TL.T_SCOOT0, 0.006, pan=P_CL)
    for (t, nn, g) in [(TL.T_GIVE0 + 0.1, 'D6', 0.026), (TL.T_GIVE0 + 0.75, 'F#6', 0.022), (TL.T_DROP, 'A6', 0.024),
                       (TL.T_HAPPY_H + 0.35, 'E6', 0.026), (TL.T_HAPPY_H + 1.05, 'D6', 0.028)]:
        FX2.add(Z.music_box(nf(nn), 2.4, 1.0), t, g, pan=-0.2)
    roll(GT, CH['D9'], TL.T_HAPPY_H, 0.5, seed=500, ring=5.5, spread=0.08)
    Q.pad_swell(PAD, TL.T_HAPPY_H - 0.3, DUR - TL.T_HAPPY_H + 0.3, notes=('D3', 'A3', 'F#4', 'E5'), gain=0.024, a=2.2, r=1.2,
                cutoff=900, seed=8)
    Q.boing(FX, TL.T_NOD0 + 0.1, gain=0.006, f=940)                                          # 嗯。 the antenna
    Q.swish(FX, TL.T_RAISE0, d=0.6, gain=0.006, pan=-0.1, seed=17, f0=300, f1=1000)          # raises the bobber
    Q.shimmer(FX2, TL.T_ECHO + 0.2, 1.4, gain=0.35, pan=0.2, seed=4)
    roll(GT, CH['D'], TL.T_ECHO + 0.3, 0.36, seed=600, ring=5.0, spread=0.1)

    voices(VO)

    # ---------------------------------------------------------------- mix
    duck = np.ones(ns(DUR) + Z.SR * 2)
    for bx in TL.BOXES:
        duck[ns(bx['t_open']):ns(bx['t_close'])] = 0.78
    k = np.ones(ns(0.3)) / ns(0.3); duck = np.convolve(duck, k, mode='same')[:, None]
    gt = MS.wet(GT, 2.6, 0.35, 1, damp=3800) * duck[:len(GT.x)]
    pad = MS.wet(PAD, 3.0, 0.5, 3) * duck[:len(PAD.x)]
    fx = MS.wet(FX, 1.0, 0.18, 4) + MS.wet(FX2, 3.0, 0.6, 5) + MS.wet(VO, 1.6, 0.25, 6)
    mix = (gt + pad + fx + AMB.x)[:ns(DUR)].copy()

    # ---------------------------------------------------------------- the oil-paint shot: paint_v2's own mix
    _a4 = sys.modules['timeline']
    sys.modules['timeline'] = sys.modules['pv2_timeline']
    sp = importlib.util.spec_from_file_location('pv2_audio', (_PROJ + '/paint_v2/audio.py'))
    PA = importlib.util.module_from_spec(sp); sp.loader.exec_module(PA)
    sys.modules['timeline'] = _a4
    pm = PA.build(verbose=False, ui=False, finalize=False)
    a = ns(PAINT_OFF); L = min(len(pm), len(mix) - a)
    pm = pm[:L].copy(); fi = ns(0.4); pm[:fi] *= np.linspace(0, 1, fi)[:, None]
    mix[a:a + L] += pm * PAINT_GAIN
    if verbose: print(f'paint_v2 mix {len(pm) / Z.SR:.2f}s spliced at {PAINT_OFF:.2f} -> ends {PAINT_OFF + len(pm) / Z.SR:.2f}')

    mix = MS.fade(mix, TL.T_FADE0, DUR, curve=1.4)
    y = MS.finalize(mix, target_lufs=-16.5, verbose=verbose)
    if verbose:
        MS.report(y, [(0, TL.T_SO, 'W'), (TL.T_SO, TL.T_BKT, 'SO'), (TL.T_BKT, TL.T_SIDE2, 'BKT'), (TL.T_SIDE2, TL.T_CU_C1, 'SIDE2'),
                      (TL.T_CU_C1, TL.T_INS, 'CU_C1..OB'), (TL.T_INS, TL.T_CU_C2, 'INS..O2'), (TL.T_CU_C2, TL.T_PAINT, 'CU_C2'),
                      (TL.T_PAINT, TL.T_INS_D, 'PAINT'), (TL.T_INS_D, TL.T_CU_H, 'DUSK'), (TL.T_CU_H, DUR, 'END')])
    return y


if __name__ == '__main__':
    y = build()
    MS.write_wav(OUT, y)
    print('wrote', OUT, f'{len(y) / Z.SR:.3f}s')
