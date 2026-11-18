"""ACT III v2 (~110 s) - music + sound design, every cue scheduled from timeline.py.

    python3 audio.py      -> ../out/act3_audio.wav (+ section report)

IN/OUT/MED   corridor hum, latch, door, white-out swell -> morning street (birds); quest + side-quest list tick in
PARK         walk in, side quest pops, hop onto the bench, a soft snore -> eyes pop -> 数羊 lullaby (music box) ->
             counter runs away -> ding -> eyes open -> side quest fails -> hop off -> map icon -> the map opens (whoosh)
PATH         Theme A (the WORK theme) as chiptune while he 'rests efficiently' -> fanfare
FAIL         the map folds back into his face -> keys under the doubt -> side quest fails (wah) -> 随便逛逛 pops
TRACK        walking Theme B, one ding per station (C6 E6 G6 C7)
AERIAL       the whole town's requests pile up -> sad piano under the line -> city-wide ding -> auto-replies -> gasp
FREEZE       wind only
AFTER        the bubbles pop away one by one, birds fly over, a warm pad lets the air back in
FOUR / ASK   solo piano Theme B twice (2nd pass with a lower voice) under four small life sounds; ends unresolved
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, math
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/act3'))
import numpy as np
from pixelkit.audio import synth as Z, music as M, cues as Q, master as MS
from pixelkit.audio.synth import ns, nf
from pixelkit.audio.music import Grid, CH_B, MEL_B
import timeline as TL

DUR = TL.DUR
OUT = (_PROJ + '/out/act3_audio.wav')
P_CL = 0.0


def claude_lines(bus, boxes, gain=0.045):
    for bx in boxes:
        Q.box_open(bus, bx['t_open'] - 0.12, gain=0.02, low=True)
        for ln in bx['lines']:
            Q.voice_line(bus, ln['zh'], ln['t0'], ln['cps'], gain=gain, shift=-5, kind='tri', seed=4, times=ln['times'],
                         question=ln['zh'].endswith('？'))

def path_events():
    """checkpoint arrival times + step times of the speed walk (mirrors scene.PathShot)."""
    from pixelkit.sets.maps import ParkMap
    pm = ParkMap(); route = pm.route([pm.S, *pm.CHECK, pm.S])
    pts = [pm.cell_c(c) for c in route]
    cum = np.concatenate([[0], np.cumsum([math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts[:-1], pts[1:])])])
    ci, k = [], 0
    for n, c in enumerate(route):
        if k < 3 and c == pm.CHECK[k]: ci.append(n); k += 1
    def run_u(t):
        u = min(max((t - TL.T_RUN0) / (TL.T_RUN1 - TL.T_RUN0), 0), 1); return u * u * (3 - 2 * u) * 0.25 + u * 0.75
    ts = np.linspace(TL.T_RUN0, TL.T_RUN1, 2000); us = np.array([run_u(t) for t in ts]) * cum[-1]
    checks = [float(ts[np.searchsorted(us, cum[i])]) for i in ci]
    steps = [float(ts[min(len(ts) - 1, np.searchsorted(us, cum[i]))]) for i in range(1, len(route))]
    return checks, steps

def side_quest(bus, t):
    Q.ui_slide(bus, t, gain=0.028, pan=0.0)
    Q.ok(bus, t + 0.22, gain=0.45, pan=0.0)
    Q.sparkle(bus, t + 0.28, 0.5, 0.012, 0.0, seed=int(t * 10))

_NN = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
def midi(name):
    n = _NN[name[0]]; i = 1
    if name[1] in '#b': n += 1 if name[1] == '#' else -1; i = 2
    return n + 12 * (int(name[i:]) + 1)

def AerialShot_after():
    from scene import AerialShot
    a = AerialShot(OW=480, OH=270); a.after_setup()
    return a

def aerial_events():
    from scene import AerialShot
    a = AerialShot(OW=480, OH=270)
    return a.bub, a.claude_xy


def build(verbose=True):
    B = lambda: Z.Bus(DUR)
    AMB, MU, FX, VO = B(), B(), B(), B()
    LULL, PA, AE, PI = B(), B(), B(), B()

    # ================================================================ IN : corridor (0 - 1.5)
    Q.room_tone(AMB, 0.0, TL.T_OUT, hum=0.006, air=0.008, fade=0.2)
    for (a, b) in TL.T_SIGN:                                                    # fluorescent flicker
        FX.add(Z.blip(120, min(0.06, b - a), 'saw', 0.5, 1.0, 0), a, 0.03, pan=-0.1)
        Q.clack(FX, a, size=0.15, gain=0.25, pan=-0.1, seed=int(a * 100))
    Q.clack(FX, TL.T_LATCH, size=0.8, gain=0.9, pan=0.0, seed=3)                # push-bar latch
    Q.whoosh(FX, TL.T_OPEN0, d=TL.T_OPEN1 - TL.T_OPEN0, gain=0.05, f0=200, f1=2500, seed=4)
    Q.riser(FX, TL.T_OPEN0, TL.T_OUT, gain=0.07, f0=400, f1=7000)
    Q.pad_swell(MU, TL.T_WHITE0, 2.6, notes=('F3', 'C4', 'A4', 'E5'), gain=0.07, a=0.55, r=1.6, cutoff=2600)

    # ================================================================ OUT / MED : the street (1.5 - 7)
    Q.morning_bed(AMB, TL.T_OUT, TL.T_PATH + 0.3, gain=1.0, fade_in=0.6, fade_out=0.4, seed=5)
    for k, t in enumerate(TL.footsteps()): Q.step(FX, t, gain=0.022, pan=P_CL, seed=k)
    Q.clack(FX, TL.T_CLOSE1, size=1.0, gain=0.8, pan=-0.45, seed=7)             # the door shuts behind him
    Q.jump(FX, TL.T_HAPPY, gain=0.6, pan=P_CL)
    Q.ui_slide(FX, TL.T_QUEST, gain=0.03, pan=0.0)
    for k in range(3): FX.add(Z.blip(nf('E6') * 2 ** (k * 2 / 12), 0.03, 'pulse', 0.35, 1.0, 0), TL.T_QLIST + 0.12 + 0.14 * k, 0.012, pan=0.0)
    Q.ok(FX, TL.T_QUEST + 0.25, gain=0.55, pan=0.0)
    Q.sparkle(FX, TL.T_QUEST + 0.3, 0.6, 0.015, 0.0, seed=2)
    FX.add(Z.glide_tone(300, 820, TL.T_STRETCH1 - TL.T_STRETCH0, 'sine', 1.0, 0.8), TL.T_STRETCH0, 0.02, pan=P_CL)  # stretch 'mmmh'
    GW = Grid(100, t0=TL.T_WALK)
    M.keys_comp(MU, GW, CH_B, 0, 1, gain=0.045, ring_last=True)
    M.soft_bass(MU, GW, CH_B, 0, 1, gain=0.13, ring_last=True)
    M.lazy_drums(MU, GW, 0, 1, gain=0.7, ring_last=False)
    for (b, d, nn) in MEL_B[:4]: MU.add(Z.music_box(nf(nn), 1.6, 1.0), GW.t(b), 0.06, pan=0.15)

    # ================================================================ PARK : the bench (try #1, sheep, side quest 1 fails, map)
    for k, t in enumerate(TL.steps_of([(TL.T_PARK, TL.PW_X0), (TL.T_PWALK1, TL.PW_X1), (TL.T_HOPON, TL.PW_X1)], 9.0)):
        Q.step(FX, t, gain=0.02, pan=P_CL, seed=60 + k)
    FX.add(Z.music_box(nf('E6'), 0.8, 1.0), TL.T_SEE, 0.05, pan=0.2); FX.add(Z.music_box(nf('A6'), 1.0, 1.0), TL.T_SEE + 0.09, 0.05, pan=0.2)
    side_quest(FX, TL.T_SQ1)
    Q.jump(FX, TL.T_HOPON, gain=0.5, pan=P_CL)
    Q.soft_land(FX, TL.T_LIE, size=0.6, gain=0.8, pan=P_CL, seed=3)
    Q.pad_swell(LULL, TL.T_LIE + 0.1, TL.T_EYES0 - TL.T_LIE + 0.2, notes=('F3', 'C4', 'E4', 'A4'), gain=0.05, a=0.8, r=0.5, cutoff=1200, seed=9)
    for k, nn in enumerate(('A5', 'C6', 'E6', 'D6')):                         # a sleepy music-box start ... cut off by the eyes
        LULL.add(Z.music_box(nf(nn), 1.6, 1.0), TL.T_LIE + 0.35 + 0.42 * k, 0.05, pan=0.2)
    Q.pad_swell(LULL, TL.T_THINK, TL.T_BUB1 - TL.T_THINK + 0.5, notes=('D3', 'A3', 'C4', 'F4'), gain=0.035, a=0.8, r=0.6, cutoff=1100, seed=10)
    Q.snore(FX, TL.T_Z0 + 0.05, d_in=0.45, d_out=0.5, gain=0.35, pan=P_CL, seed=2, whistle=False)
    FX.add(Z.glide_tone(240, 1400, 0.14, 'pulse', 1.0, 0.6, 0.3), TL.T_EYES0, 0.028, pan=P_CL)  # eyes pop open
    Q.pop(FX, TL.T_EYES0 + 0.02, gain=0.07, up=False)
    GL = Grid(66, t0=TL.T_BUB1)
    lull_ch = [('Fmaj7', ['F3', 'C4', 'E4', 'A4']), ('Em7', ['E3', 'B3', 'D4', 'G4']), ('Dm7', ['D3', 'A3', 'C4', 'F4'])]
    for i, (nm, nts) in enumerate(lull_ch):
        Q.pad_swell(LULL, GL.bar(i), GL.d(4) + 0.4, notes=tuple(nts), gain=0.045, a=0.9, r=0.8, cutoff=1300, seed=i)
    for (b, d, nn) in MEL_B:
        t = GL.t(b)
        if t < TL.T_RUSH0: LULL.add(Z.music_box(nf(nn), 2.2, 1.0), t, 0.07, pan=0.2)
    Q.pop(FX, TL.T_BUB0, gain=0.04); Q.pop(FX, TL.T_BUB0 + 0.1, gain=0.04); Q.pop(FX, TL.T_BUB1, gain=0.06)
    for k, t in enumerate(TL.sheep_ticks()):                                  # one 'boing' + blip per sheep
        FX.add(Z.glide_tone(500, 900, 0.09, 'sine', 1.0, 0.7), t - 0.12, 0.018, pan=0.25)
        FX.add(Z.blip(nf('C6') * 2 ** (min(k, 12) / 12), 0.05, 'pulse', 0.35, 1.0, 0), t, 0.03, pan=0.3)
    Q.ticker(FX, TL.T_RUSH0, TL.T_DONE, rate0=14, rate1=60, gain=0.014, f=2600, pan=0.3)
    Q.riser(FX, TL.T_RUSH0, TL.T_DONE, gain=0.05, f0=600, f1=6000)
    Q.result_ding(FX, TL.T_DONE, gain=0.9, pan=0.2)
    Q.pop(FX, TL.T_DONE2, gain=0.04, pan=0.2)
    FX.add(Z.glide_tone(240, 1400, 0.16, 'pulse', 1.0, 0.6, 0.3), TL.T_EYES, 0.03, pan=P_CL)   # eyes snap open
    Q.pop(FX, TL.T_EYES + 0.02, gain=0.08, up=False)
    Q.ui_slide(FX, TL.T_SQ1_BACK, gain=0.025, pan=0.0)                        # side quest 1 comes back ... and fails
    Q.deny(FX, TL.T_SQ1_FAIL, gain=0.5, pan=0.0)
    FX.add(Z.glide_tone(392, 294, 0.35, 'tri', 1.0, 0.7), TL.T_SQ1_FAIL + 0.12, 0.02, pan=0.0)
    Q.jump(FX, TL.T_HOPOFF, gain=0.45, pan=P_CL, f0=500, f1=380, d=0.12)
    Q.soft_land(FX, TL.T_HOPOFF + 0.3, size=0.4, gain=0.8, pan=P_CL, seed=5)
    side_quest(FX, TL.T_SQ2)
    GW2 = Grid(100, t0=TL.T_SQ2 + 0.3)                                          # 'a walk then' - Theme B keys come back
    M.keys_comp(PA, GW2, CH_B, 0, 2, gain=0.035, ring_last=True, t_max=TL.T_MAP1)
    M.soft_bass(PA, GW2, CH_B, 0, 2, gain=0.10, ring_last=True, t_max=TL.T_MAP1)
    for (b, d, nn) in MEL_B[:5]: PA.add(Z.music_box(nf(nn), 1.4, 1.0), GW2.t(b), 0.045, pan=0.15)
    FX.add(Z.glide_tone(600, 1600, 0.12, 'sine', 1.0, 0.6), TL.T_MAPFACE, 0.025, pan=P_CL)       # map icon on the face
    FX.add(Z.blip(nf('E6'), 0.06, 'pulse', 0.35, 1.0, 0), TL.T_MAPFACE + 0.1, 0.02, pan=P_CL)
    FX.add(Z.blip(nf('B6'), 0.08, 'pulse', 0.35, 1.0, 0), TL.T_MAPFACE + 0.18, 0.02, pan=P_CL)
    Q.riser(FX, TL.T_PUSH0 + 0.3, TL.T_MAP1, gain=0.045, f0=500, f1=5000)
    Q.whoosh(FX, TL.T_MAP0, d=TL.T_MAP1 - TL.T_MAP0 + 0.1, gain=0.06, f0=400, f1=6000, seed=8)

    # ================================================================ PATH : efficient rest (15.5 - 24.5)
    Q.morning_bed(AMB, TL.T_FAIL - 0.3, TL.T_FREEZE, gain=1.0, fade_in=0.5, fade_out=0.6, seed=9, birds_rate=0.9)
    Q.ui_slide(PA, TL.T_GRID0, gain=0.04, d=0.6)
    for k in range(9):                                                        # grid lines ticking in
        PA.add(Z.blip(1800 + 120 * k, 0.015, 'pulse', 0.5, 1.0, 0), TL.T_GRID0 + k * (TL.T_GRID1 - TL.T_GRID0) / 9, 0.012, pan=-0.6 + 0.15 * k)
    Q.ticker(PA, TL.T_BFS0, TL.T_BFS1, rate0=10, rate1=22, gain=0.010, f=2200, pan=0.0)
    Q.riser(PA, TL.T_BFS1 - 0.8, TL.T_ROUTE1, gain=0.04, f0=800, f1=5000)
    Q.ok(PA, TL.T_PLAN_OK, gain=0.6, pan=0.0)
    GP = Grid(128, t0=TL.T_BFS0)
    M.theme_a(MU, GP, 0, 3, layers=('arp', 'bass', 'drums'), gain=0.55, t_max=TL.T_RUN0 - 0.05)
    M.theme_a(MU, GP, 2, 3, layers=('lead', 'echo', 'arp', 'bass', 'drums'), gain=0.6, t_min=TL.T_RUN0 - 0.05, t_max=TL.T_ACH)
    checks, steps = path_events()
    Q.whoosh(PA, TL.T_RUN0, d=0.3, gain=0.06, f0=400, f1=4000, seed=10)
    for k, t in enumerate(steps):
        if k % 2 == 0: PA.add(Z.blip(900 if k % 4 == 0 else 760, 0.02, 'pulse', 0.5, 1.0, 0), t, 0.012, pan=0.0)
    for k, t in enumerate(checks): Q.coin(PA, t, gain=0.05, pan=0.0, k=2 * k)
    Q.fanfare(PA, TL.T_ACH, gain=1.0)
    M.stab(MU, TL.T_ACH + 0.28, gain=0.04, d=1.6, bass_gain=0.12)

    # ================================================================ FAIL : the map folds back, side quest 2 fails
    Q.whoosh(FX, TL.T_FAIL, d=TL.T_UNMAP - TL.T_FAIL + 0.1, gain=0.05, f0=5000, f1=500, seed=12)
    FX.add(Z.glide_tone(1600, 600, 0.12, 'sine', 1.0, 0.6), TL.T_UNMAP - 0.05, 0.022, pan=P_CL)
    Q.jump(FX, TL.T_UNMAP, gain=0.45, pan=P_CL)
    GF = Grid(84, t0=TL.T_UNMAP + 0.2)
    M.keys_comp(MU, GF, CH_B, 0, 1, gain=0.035, ring_last=False, t_max=TL.T_QFAIL)
    M.soft_bass(MU, GF, CH_B, 0, 1, gain=0.10, ring_last=False, t_max=TL.T_QFAIL)
    Q.question(FX, TL.T_QFAIL - 0.5, gain=0.04)
    Q.fail_wah(FX, TL.T_QFAIL, gain=0.9)
    side_quest(FX, TL.T_SQ3)

    # ================================================================ TRACK (28 - 44)
    GT = Grid(100, t0=TL.T_TRACK + 0.05)
    nb = int((TL.T_AERIAL - GT.t0) / GT.d(4))
    M.keys_comp(MU, GT, CH_B, 0, nb, gain=0.03, ring_last=True)
    M.soft_bass(MU, GT, CH_B, 0, nb, gain=0.09, ring_last=True)
    M.lazy_drums(MU, GT, 0, nb, gain=0.45, ring_last=False, t_max=TL.T_AERIAL)
    for k, t in enumerate(TL.FOOTSTEPS_TRACK): Q.step(FX, t, gain=0.018, pan=P_CL, seed=40 + k)
    shifts = {'uncle': -7, 'cafe': -1, 'quilt': 3, 'bestman': 1}
    for k, (who, td, txt, anc, side) in enumerate(TL.STATIONS):
        Q.ding(FX, td, gain=0.13, pan=float(np.clip((anc[0] - (TL.claude_track(td)['x'] + 46)) / 160, -0.7, 0.7)), note=TL.DING_NOTES[k])
        Q.voice_line(VO, txt, td + 0.25, 15 if who != 'bestman' else 19, gain=0.03, shift=shifts[who], kind='pulse', seed=10 + k, pan=0.3)
    for k, (td, txt, anc, side) in enumerate(TL.CAFE_EXTRA):
        Q.chat_in(FX, td, gain=0.04, pan=-0.3 if side < 0 else 0.4, k=k + 1)
        Q.voice_line(VO, txt, td + 0.15, 16, gain=0.022, shift=4 + 3 * k, seed=20 + k, pan=-0.3 if side < 0 else 0.4)
    Q.whoosh(FX, TL.T_RUNNER, d=0.5, gain=0.015, f0=300, f1=1500, seed=30)        # the runner passing

    # ================================================================ AERIAL (44 - 57)
    bub, cxy = aerial_events()
    Q.whoosh(AE, TL.T_AERIAL - 0.35, d=0.8, gain=0.05, f0=200, f1=3000, seed=44)
    Q.wind(AMB, TL.T_AERIAL - 0.3, DUR, gain=0.016, seed=45, fade=1.2)
    Q.wind(AMB, TL.T_FREEZE - 0.4, TL.T_AFTER + 1.2, gain=0.05, seed=46, fade=0.8, gust=0.5, lo=120, hi=1400)
    Q.tension_pad(AE, TL.T_BUBBLES0, TL.T_NAR_A - TL.T_BUBBLES0, gain=0.08, notes=('D3', 'A3', 'C4', 'F4'), a=3.0, cutoff=1600)
    for k, b in enumerate(sorted(bub, key=lambda b: b['t'])):
        g = 0.055 * (0.55 + 0.45 * (k / len(bub)))
        Q.chat_in(AE, b['t'], gain=g, pan=float(np.clip((b['x'] - 240) / 240, -0.9, 0.9)), k=k)
    Q.riser(AE, TL.T_BUBBLES1 - 2.5, TL.T_NAR_A, gain=0.06, f0=500, f1=7000)
    ae_cut = TL.T_NAR_A - 0.05
    M.phrase(PI, TL.T_NAR_A, [(0.0, 'D3', 0.5), (0.02, 'A3', 0.4), (0.04, 'F4', 0.35), (0.06, 'C5', 0.3)], 'piano', gain=0.16)
    M.phrase(PI, TL.T_NAR_A + 1.8, [(0.0, 'Bb2', 0.45), (0.02, 'F3', 0.4), (0.04, 'D4', 0.3), (0.06, 'A4', 0.28)], 'piano', gain=0.15)
    Q.big_ding(AE, TL.T_CITY_DING, gain=1.0)
    for k, b in enumerate(sorted(bub, key=lambda b: b['tr'])):
        if k % 3 == 0:
            AE.add(Z.blip(nf('E5') if k % 2 else nf('A5'), 0.03, 'pulse', 0.5, 1.0, 0), max(b['tr'], TL.T_CITY_DING + 0.1), 0.010,
                   pan=float(np.clip((b['x'] - 240) / 240, -0.9, 0.9)))
    Q.auto_reply(AE, '您好，Claude 休假中。急事请自己想办法。', TL.T_CITY_DING + 0.15, cps=26, gain=0.02, pan=0.0)
    Q.crowd_gasp(AE, TL.T_SCREAM, gain=1.0, n=50)
    Q.crash(AE, TL.T_SCREAM, gain=0.05, d=3.0, tau=0.9)
    Q.impact(AE, TL.T_SCREAM, gain=0.5)

    # ================================================================ AFTER : the city lets go
    aft = AerialShot_after()
    for k, b in enumerate(sorted(aft.bub, key=lambda b: b['tp'])):
        if k % 2 == 0:
            Q.pop(FX, b['tp'] - 0.1, gain=0.012 + 0.01 * ((k * 7) % 5) / 4, pan=float(np.clip((b['x'] - 240) / 240, -0.9, 0.9)), up=False)
    Q.pad_swell(PI, TL.T_AFTER + 0.3, 3.2, notes=('F3', 'C4', 'A4', 'E5'), gain=0.05, a=1.4, r=1.4, cutoff=1800, seed=11)
    for k in range(5): Q.swish(FX, TL.T_AFTER + 0.8 + 0.32 * k, d=0.2, gain=0.012, pan=-0.6 + 0.3 * k, f0=700, f1=1800, seed=70 + k)  # wings
    Q.birds(AMB, TL.T_AFTER + 0.9, TL.T_F1 + 0.5, rate=2.4, gain=0.014, seed=62)

    # ================================================================ FOUR / ASK : solo piano Theme B (twice), slow and warm
    GP2 = Grid(76, t0=TL.T_F1 + 0.15)
    chords = [['F2', 'C3', 'A3', 'E4'], ['E2', 'B2', 'G3', 'D4'], ['D2', 'A2', 'F3', 'C4'], ['G2', 'D3', 'F3', 'C4'],
              ['F2', 'C3', 'A3', 'E4'], ['E2', 'B2', 'G3', 'D4'], ['D2', 'A2', 'F3', 'C4'], ['Bb1', 'F2', 'D3', 'A3']]
    for bar in range(8):
        nts = chords[bar]
        if GP2.bar(bar) > TL.T_ASK + 0.5: break
        M.phrase(PI, GP2.bar(bar), [(0.02 * i, n, 0.32 - 0.03 * i) for i, n in enumerate(nts)], 'piano', gain=0.14)
        M.phrase(PI, GP2.bar(bar) + GP2.d(2), [(0.0, nts[2], 0.18), (0.02, nts[3], 0.16)], 'piano', gain=0.12)
    for p in range(2):
        for (b, d, nn) in MEL_B:
            t = GP2.t(b + 16 * p)
            if t >= TL.T_ASK + 1.2: continue
            M.phrase(PI, t, [(0.0, nn, 0.30)], 'piano', gain=0.15, pan=0.12)
            if p == 1: M.phrase(PI, t + 0.01, [(0.0, midi(nn) - 9, 0.20)], 'piano', gain=0.12, pan=-0.05)   # a lower voice (a 6th below)
    M.phrase(PI, TL.T_Q - 0.05, [(0.0, 'G2', 0.32), (0.03, 'D3', 0.3), (0.06, 'C4', 0.28), (0.09, 'F4', 0.26), (0.12, 'A4', 0.22)],
             'piano', gain=0.15)                                               # unresolved question chord
    Q.birds(AMB, TL.T_F1, DUR - 0.5, rate=1.1, gain=0.012, seed=61)
    for k, t0 in enumerate((TL.T_F1, TL.T_F2, TL.T_F3, TL.T_F4)):              # each story starts with Claude's auto-reply
        ta = t0 + TL.POP_AUTO
        FX.add(Z.blip(nf('A5'), 0.05, 'pulse', 0.4, 1.0, 0), ta, 0.014, pan=0.25); FX.add(Z.blip(nf('E5'), 0.07, 'pulse', 0.4, 1.0, 0), ta + 0.07, 0.014, pan=0.25)
        Q.auto_reply(FX, '自动回复', ta + 0.15, cps=30, gain=0.01, pan=0.25)
    # F1 the uncle: sigh, phone down, a stray kite drifts in, its line lands by his hand, he stands and catches it
    Q.voice_line(VO, '唉……', TL.T_U_SIGH + 0.05, 4, gain=0.022, shift=-9, kind='tri', seed=31, pan=-0.2)
    Q.swish(FX, TL.T_U_SIGH, d=0.7, gain=0.012, pan=-0.2, f0=300, f1=900, seed=32)
    Q.clack(FX, TL.T_U_DOWN, size=0.25, gain=0.4, pan=-0.2, seed=33)
    Q.swish(FX, TL.T_KITE_IN, d=1.2, gain=0.026, pan=0.4, f0=300, f1=1200)
    Q.swish(FX, TL.T_U_LOOK - 0.1, d=0.5, gain=0.016, pan=-0.1, f0=900, f1=2200, seed=3)
    Q.soft_land(FX, TL.T_U_STAND, size=0.3, gain=0.4, pan=-0.2, seed=34)
    Q.sparkle(FX, TL.T_U_STAND + 0.25, 0.5, 0.012, -0.2, seed=35)
    # F2 the PPT guy: typing stops, his friend speaks up, the lid shuts, 走！
    Q.typing(FX, TL.T_F2, TL.T_C_STOP, rate0=12, gain=0.03, pan=0.0, seed=36)
    Q.voice_line(VO, '连 Claude 都放假了，咱也歇会儿？', TL.T_C_ASK + 0.1, 13, gain=0.026, shift=5, seed=13, question=True, pan=0.25)
    Q.clack(FX, TL.T_LID1, size=0.35, gain=0.7, pan=0.0, seed=21)
    Q.voice_line(VO, '走！', TL.T_TURN + 0.1, 8, gain=0.032, shift=-1, seed=11, pan=0.0)
    # F3 the window: the phone glow dies, a crack of sun, curtains, quilt, stretch
    FX.add(Z.glide_tone(900, 300, 0.18, 'sine', 1.0, 0.6), TL.T_GLOW_OFF, 0.012, pan=0.0)
    Q.sparkle(FX, TL.T_CRACK, 0.7, 0.012, 0.1, seed=37)
    Q.swish(FX, TL.T_CURT0, d=TL.T_CURT1 - TL.T_CURT0 + 0.2, gain=0.035, pan=0.0, f0=800, f1=2600, seed=5)
    Q.swish(FX, TL.T_QUILT, d=0.4, gain=0.04, pan=0.0, f0=300, f1=1400, seed=6)
    FX.add(Z.glide_tone(380, 620, 0.5, 'tri', 1.0, 0.8), TL.T_QUILT + 0.5, 0.012, pan=0.0)      # big stretch / yawn
    # F4 the best man: four lines, the memory, the groom cries, applause
    for k, (tl_, txt) in enumerate(TL.BM_LINES):
        Q.voice_line(VO, txt, tl_ + 0.1, 11, gain=0.03, shift=1, seed=14 + k, pan=0.1)
    Q.sparkle(FX, TL.T_MEM0 + 0.25, 0.9, 0.012, 0.4, seed=38)
    Q.pad_swell(PI, TL.T_MEM0 + 0.2, TL.T_CRY - TL.T_MEM0 + 0.6, notes=('A3', 'E4', 'C5'), gain=0.03, a=1.2, r=1.5, cutoff=1600, seed=12)
    for k in range(2): Q.swish(FX, TL.T_CRY + 0.1 + 0.25 * k, d=0.12, gain=0.02, pan=-0.15, f0=1500, f1=3000, seed=30 + k)   # sniff
    Q.claps(FX, TL.T_CRY + 0.5, TL.T_ASK + 0.8, rate=16, gain=0.016)
    # narration (whole act)
    claude_lines(VO, TL.BOXES)
    Q.question(FX, TL.T_Q, gain=0.05)

    # ================================================================ mix
    mu = MS.wet(MU, 1.4, 0.25, 1)
    mu = MS.cut(mu, TL.T_PARK - 0.3, TL.T_PATH - 0.05, fade=0.6)                 # PARK has its own lullaby bus
    mu = MS.cut(mu, TL.T_QFAIL + 0.01, TL.T_TRACK, fade=0.03)                     # quest fails -> music drops out
    mu = MS.cut(mu, TL.T_AERIAL - 0.2, DUR, fade=0.6)
    lull = MS.wet(LULL, 2.0, 0.35, 2)
    lull[:ns(TL.T_PARK - 0.4)] = 0
    lull = MS.cut(lull, TL.T_RUSH0 + 0.6, DUR, fade=0.8)
    pa = MS.cut(MS.wet(PA, 0.8, 0.15, 3), TL.T_FAIL + 0.6, DUR, fade=0.4)
    ae = MS.cut(MS.wet(AE, 1.6, 0.25, 4), TL.T_AFTER - 0.3, DUR, fade=1.2)
    ae_pre = ae.copy(); ae_pre[ns(ae_cut):] = 0
    ae_post = ae.copy(); ae_post[:ns(ae_cut)] = 0
    ae_post_dk = ae_post.copy(); ae_post_dk[ns(ae_cut):ns(TL.T_CITY_DING - 0.02)] *= 0.0
    ae = MS.fade(ae_pre, ae_cut - 0.3, ae_cut + 0.05, curve=1.0) + ae_post_dk
    pi = MS.wet(PI, 2.0, 0.32, 5)
    fx = MS.wet(FX, 0.6, 0.14, 6) + MS.wet(VO, 0.45, 0.14, 7)
    amb = AMB.x.copy()
    amb[ns(TL.T_PATH):ns(TL.T_FAIL - 0.3)] *= 0.25
    mix = (mu + lull + pa + ae + pi + fx + amb)[:ns(DUR)].copy()
    mix = MS.fade(mix, TL.T_FADE0, DUR, curve=1.4)
    y = MS.finalize(mix, target_lufs=-16.5, verbose=verbose)
    if verbose:
        T = TL
        MS.report(y, [(0, T.T_OUT, 'IN'), (T.T_OUT, T.T_PARK, 'street'), (T.T_PARK, T.T_BUB0, 'PARK try1'), (T.T_BUB0, T.T_EYES, 'sheep'),
                      (T.T_EYES, T.T_PATH, 'PARK fail/map'), (T.T_PATH, T.T_FAIL, 'PATH'), (T.T_FAIL, T.T_TRACK, 'FAIL'),
                      (T.T_TRACK, T.T_AERIAL, 'TRACK'), (T.T_AERIAL, T.T_NAR_A, 'requests'), (T.T_NAR_A, T.T_CITY_DING, 'line'),
                      (T.T_CITY_DING, T.T_FREEZE, 'ding/scream'), (T.T_FREEZE, T.T_AFTER, 'FREEZE'), (T.T_AFTER, T.T_F1, 'AFTER'),
                      (T.T_F1, T.T_F4, 'F1-F3'), (T.T_F4, T.T_ASK, 'F4 best man'), (T.T_ASK, DUR, 'ASK')])
    return y


if __name__ == '__main__':
    y = build()
    MS.write_wav(OUT, y)
    print('wrote', OUT, f'{len(y) / Z.SR:.3f}s')
