"""ACT I (45.6 s) - music + sound design, every cue scheduled from timeline.py.

    python3 audio.py      -> ../out/act1_audio.wav (+ section report)

Sections (own buses, so cuts are clean):  pre-freeze | freeze | day (B, hard cut at the crash zoom) |
clock insert | sunset (D/E/F, fades over the dissolve) | night | title.
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/act1'))
import numpy as np
from pixelkit.audio import synth as Z, music as M, cues as Q, master as MS
from pixelkit.audio.synth import ns, nf
from pixelkit.audio.music import Grid
import timeline as TL
from timeline import b, G, G2, GB

DUR = TL.DUR
FREEZE, RESUME = TL.T_FREEZE, TL.T_RESUME
OUT = (_PROJ + '/out/act1_audio.wav')
e = 1e-6


def pan_of(x, t):
    z, cx, cy, sx, sy, zb = TL.cam_params(min(t, FREEZE - 1e-3) if t < RESUME else t)
    return float(np.clip((x - cx) * z / 240.0 * 0.85, -0.85, 0.85))


def narr(bus, bx_i, gain=0.05, shift=0, kind='pulse', seed=0):
    bx = TL.BOXES[bx_i]
    Q.box_open(bus, bx['t_open'] - 0.12, gain=0.02, low=bx_i == 3)
    for ln in bx['lines']:
        Q.voice_line(bus, ln['zh'], ln['t0'], ln['cps'], gain=gain, shift=shift, kind=kind, seed=seed,
                     question=ln.get('question', False), times=ln['times'])


def build(verbose=True):
    B = lambda: Z.Bus(DUR)
    PM, PX, PV, AMB = B(), B(), B(), B()          # pre-freeze
    FZ = B()                                      # freeze
    AM, AX, AV = B(), B(), B()                    # day after the freeze (B)
    CI = B()                                      # clock insert
    SM, SX, SV, SB = B(), B(), B(), B()           # sunset: music, sfx, voice, music box / bells
    NM, NX, NV = B(), B(), B()                    # night
    TM, TX = B(), B()                             # title
    X = lambda t: PX if t < FREEZE else AX
    V = lambda t: PV if t < FREEZE else AV

    # ================================================================ A: the opening (verbatim)
    Q.room_tone(AMB, 0.0, FREEZE + 0.3, hum=0.006, air=0.016, fade=0.5)
    Q.clock_ticks(AMB, 0.30, 3.0, period=1.0, gain=0.085, pan=-0.35)
    Q.snore(AMB, 0.05, d_in=0.70, d_out=0.95, gain=2.0, pan=0.0, seed=1)
    Q.snore(AMB, 1.95, d_in=0.80, d_out=0.95, gain=2.0, pan=0.0, seed=2, stop=TL.T_DING - 0.005)
    Q.pad_swell(PM, 1.6, 2.7, notes=('C3', 'G3', 'E4', 'B4'), gain=0.11, a=1.45, r=1.0, cutoff=1500)
    Q.ding(PX, TL.T_DING, gain=0.13, pan=-0.45)
    Q.crt_wake(PX, TL.T_DING + 0.015, gain=0.9, pan=-0.55)
    Q.jump(PX, TL.T_WAKE, gain=1.0, pan=0.0)
    Q.thud(PX, TL.T_HOP_LAND, size=0.35, gain=0.22, pan=0.0, seed=4)
    for i, to in enumerate(TL.OKS):
        if to < G.bar(1): sh = 0
        elif to < RESUME: sh = 2
        else: sh = [4, 7, 9, 5, 7, 9][min(5, i - 4)] if i >= 4 else 2
        side, dy = TL.OK_META.get(to, (1, 0))
        Q.ok(V(to), to, gain=1.0, pan=0.05 * side, shift=sh)
        Q.coin(X(to), to + 0.30, gain=0.032, pan=0.15, k=sh)
    for m in TL.MSGS[1:]:
        Q.chat_in(X(m['t_in']), m['t_in'], gain=0.065, pan=-0.55, k=m['i'])
    for k, m in enumerate(TL.LAPSE_MSGS):
        Q.chat_in(AX, m['t_in'], gain=0.030, pan=-0.6, k=k)

    # ---------------------------------------------------------------- bricks (work sim, world time)
    sim, hero = TL.build_sim()
    body = {bd.id: bd for bd in sim.bodies}
    spawn = {ev[2]['id']: ev[0] for ev in sim.events if ev[1] == 'spawn'}
    rain_t = [TL.real(ev[0]) for ev in sim.events if ev[1] == 'land' and ev[2]['name'] == 'rain']
    seen = set()
    for (tw, kind, d) in sim.events:
        if kind == 'spawn': continue
        t = TL.real(tw)
        if t >= TL.T_CRASH1: continue
        bd = body[d['id']]; p = pan_of(d['x'], t)
        size = float(np.clip((bd.w - 18) / 40.0, 0.2, 0.85))
        if d['name'].startswith('msg'):
            first = d['id'] not in seen; seen.add(d['id'])
            if first: Q.fall(X(t), TL.real(spawn[d['id']]) + 0.05, t, gain=0.02, pan=p)
            if kind == 'bonk':
                Q.bonk(X(t), t, gain=1.0, pan=0.0)
            else:
                Q.clack(X(t), t, size=max(size, 0.6), gain=1.15, pan=p, seed=d['id'])
                if first and int(d['name'][3:]) >= 4:
                    Q.thud(X(t), t, size=0.6, gain=0.20, pan=p, seed=d['id'])
        else:
            dens = sum(1 for r in rain_t if abs(r - t) < 0.25)
            g = 0.75 / max(1.0, dens / 2.5) ** 0.5
            Q.clack(X(t), t, size=size, gain=g, pan=p, seed=d['id'])

    # ---------------------------------------------------------------- typing
    bonk_t = TL.MSGS[2]['t_land']
    for (t0, t1, r0, r1, s) in [(TL.T_OK0 + 0.36, bonk_t - 0.02, 12, 12, 1), (bonk_t + 0.6, TL.T_WIDE, 12, 14, 2),
                                (TL.T_WIDE, FREEZE, 14, 26, 3)]:
        Q.typing(PX, t0, t1, r0, r1, gain=0.045, pan=0.03, seed=s)
    Q.typing(AX, RESUME, TL.T_SLAM - 0.03, 26, 26, gain=0.045, pan=0.03, seed=4)
    Q.typing(AX, TL.T_SLAM + 0.55, TL.T_CRASH0, 26, 34, gain=0.034, pan=0.03, seed=5)

    # ---------------------------------------------------------------- HUD, rain of 好的 + coins
    Q.riser(PX, 5.85, TL.T_WIDE, gain=0.045, f0=250, f1=3200, seed=5)
    Q.ui_slide(PX, TL.T_HUD_COUNTER, gain=0.04, pan=0.6)
    Q.ui_slide(PX, TL.T_HUD_TIME, gain=0.035, pan=-0.6, seed=10)
    shifts = [0, 2, 4, 7, 9]
    for ob in TL.OK_BURSTS:
        t = TL.real(ob['tw'])
        if t < TL.T_CRASH0:
            Q.ok(V(t), t, gain=0.38 if t < RESUME + 6 else 0.26, pan=float(np.clip(ob['dx'] / 120, -0.5, 0.5)),
                 shift=shifts[ob['k']], jingle=False)
        tc = TL.real(ob['tw'] + TL.COIN_DELAY + TL.COIN_FLY)
        if tc < TL.T_CRASH0 and not (FREEZE <= tc < RESUME) and not (TL.T_SLAM <= tc < TL.T_POP_END):
            Q.coin(X(tc), tc, gain=0.014, pan=0.6, k=shifts[ob['k']], short=True)
    Q.riser(PX, TL.T_RISER, FREEZE, gain=0.085, f0=500, f1=6500)

    # ---------------------------------------------------------------- Theme A (pre-freeze, verbatim)
    C_, Am, F, Gc = M.CH_A
    M.bass(PM, G, [C_], bar0=0, nbars=1, t_min=b(2) - e, t_max=FREEZE)
    M.drums(PM, G, 0, 1, kick=(2,), snare=(), hats=2, t_min=b(2) - e, t_max=FREEZE)
    M.bass(PM, G, [Am], bar0=1, nbars=1, t_max=FREEZE)
    M.arp(PM, G, [Am], bar0=1, nbars=1, gain=0.020, t_max=FREEZE)
    M.drums(PM, G, 1, 1, hats=2, t_max=FREEZE)
    M.bass(PM, G, [F], bar0=2, nbars=1, t_max=b(10) - e)
    M.bass(PM, G, [Gc], bar0=2, nbars=1, t_min=b(10) - e, t_max=FREEZE)
    M.arp(PM, G, [F], bar0=2, nbars=1, gain=0.024, t_max=b(10) - e)
    M.arp(PM, G, [Gc], bar0=2, nbars=1, sub=8, gain=0.022, t_min=b(10) - e, t_max=FREEZE)
    M.drums(PM, G, 2, 1, kick=(0, 2, 3), snare=(1,), hats=4, t_max=FREEZE)
    runs = [M._RUNS[0], M._RUNS[1], M._RUNS[4], M._RUNS[7]]
    mel = [(8 + i + 0.25 * k, 0.25, nn) for i, r in enumerate(runs) for k, nn in enumerate(r)]
    M.lead(PM, G, mel, 0, gain=0.075, echo=0.022, t_max=FREEZE)
    M.roll(PM, G, 10, 2, div=4, g0=0.035, g1=0.11, t_max=FREEZE)

    # ---------------------------------------------------------------- the freeze
    Q.room_tone(FZ, FREEZE, RESUME + 0.05, hum=0.0022, air=0.0045, fade=0.03)
    Q.ok(FZ, TL.T_TINY_OK, gain=0.6, pan=0.0, shift=3, jingle=False)
    FZ.add(Z.glide_tone(700, 2100, TL.T_COIN1 - TL.T_COIN0, 'sine', 1.0, 0.8), TL.T_COIN0, 0.010, pan=0.3)
    Q.coin(FZ, TL.T_COIN1, gain=0.042, pan=0.55)
    Q.pop(FZ, TL.T_COIN1 + 0.025, gain=0.03, pan=0.6)

    # ================================================================ B: resume -> 3,000,000,000 -> time-lapse
    Q.impact(AX, RESUME, gain=1.0)
    M.stab(AM, RESUME, gain=0.05, d=0.9, bass_gain=0.16)
    M.theme_a(AM, G2, bar0=0, bars=4, t_max=TL.T_SLAM - 0.01)
    M.roll(AM, G2, 14, 2, div=4, g0=0.03, g1=0.12, t_max=TL.T_SLAM - 0.005)
    Q.ticker(AX, RESUME + 0.3, TL.T_SLAM - 0.02, 10, 34, gain=0.007, f=3000, pan=0.55, seed=1)     # counter racing
    Q.riser(AX, TL.T_SLAM - 1.4, TL.T_SLAM, gain=0.06, f0=400, f1=7000, seed=8)
    # the slam
    Q.impact(AX, TL.T_SLAM, gain=1.1)
    Q.crash(AX, TL.T_SLAM, gain=0.10, d=2.0)
    M.stab(AM, TL.T_SLAM, notes=(48, 60, 64, 67, 72, 76, 79), gain=0.065, d=1.4, bass_gain=0.2)
    for k in range(8):
        Q.coin(AX, TL.T_SLAM + 0.04 + 0.055 * k, gain=0.03, pan=-0.4 + 0.11 * k, k=[0, 4, 7, 12, 4, 7, 12, 16][k])
    Q.sparkle(AX, TL.T_SLAM, 0.8, gain=0.03)
    Q.whoosh(AX, TL.T_POP_FLY, 0.34, gain=0.05, pan=0.5, f0=2500, f1=600, seed=3)
    Q.coin(AX, TL.T_POP_END, gain=0.05, pan=0.75)
    Q.pop(AX, TL.T_POP_END + 0.02, gain=0.04, pan=0.75)
    # time-lapse groove (no lead), racing clock / counter, narration
    M.theme_a(AM, G2, bar0=4, bars=4, layers=('bass', 'arp', 'drums'), gain=0.75, t_min=TL.T_POP_END - 0.1,
              t_max=TL.T_CRASH0 + 0.05)
    Q.ticker(AX, TL.T_LAPSE0, TL.T_LAPSE1, 14, 30, gain=0.006, f=2400, pan=-0.6, seed=2)
    Q.whoosh(AX, TL.T_LAPSE0 - 0.15, 0.4, gain=0.04, pan=0.0, f0=300, f1=3000, seed=4)
    narr(AV, 0, gain=0.05)
    # crash zoom into the clock
    Q.riser(AX, TL.T_CRASH0 - 0.45, TL.T_CRASH1, gain=0.10, f0=300, f1=8000, seed=9)
    Q.whoosh(AX, TL.T_CRASH0, TL.T_CRASH1 - TL.T_CRASH0, gain=0.12, pan=0.2, f0=400, f1=6000, seed=6, curve=2.0)

    # ================================================================ C: clock insert
    Q.room_tone(CI, TL.T_INSERT, TL.T_1800 + 0.1, hum=0.004, air=0.010, fade=0.05)
    Q.tension_pad(CI, TL.T_INSERT, TL.T_1800 - TL.T_INSERT + 0.05, gain=0.09)
    CI.add(Z.thud(0.8, True, 3), TL.T_INSERT, 0.25)
    for k, tt in enumerate(TL.TICKS): Q.tock(CI, tt, gain=1.1, pan=0.05, k=k)

    # ================================================================ D: 18:00 - line clear, the weekend
    Q.hour_chime(SX, TL.T_1800, gain=1.0)
    Q.line_clear(SX, TL.T_1800, gain=0.9, flashes=tuple(f - TL.T_1800 for f in TL.T_CLEAR_FL), burst=TL.T_POOF - TL.T_1800)
    Q.jump(SX, TL.T_1800 + 0.02, gain=0.7)
    Q.room_tone(SX, TL.T_1800, TL.T_NIGHT + 0.4, hum=0.004, air=0.010, fade=0.4)
    for k, m in enumerate(TL.WMSGS):
        Q.chat_in(SX, m['t_in'], gain=0.06, pan=-0.55, k=k + 3)
    wsim = TL.build_weekend_sim()
    PENTA = ['F5', 'G5', 'A5', 'C6', 'D6', 'F6', 'A5', 'C6']
    wbody = {bd.id: bd for bd in wsim.bodies}
    first = set(); k = 0
    for (t, kind, d) in wsim.events:
        if kind != 'land' or d['id'] in first or t >= TL.T_DICT: continue
        first.add(d['id'])
        bd = wbody[d['id']]
        Q.soft_land(SX, t, size=float(np.clip((bd.w - 18) / 40, 0.2, 0.8)), gain=0.8, pan=pan_of(d['x'], TL.T_RESUME + 2),
                    seed=d['id'], note=PENTA[k % len(PENTA)])
        k += 1
    M.theme_b(SM, GB, bar0=0, bars=4, gain=1.0, t_min=GB.t(1) - e, t_max=TL.T_Q - 0.02, mel_bus=SB)
    Q.scratch(SX, TL.T_Q - 0.04, gain=0.10)
    Q.question(SX, TL.T_Q, gain=0.07)
    Q.jump(SX, TL.T_Q - 0.05, gain=0.6, f0=400, f1=900)
    Q.whoosh(SX, TL.T_PUSH0, TL.T_PUSH1 - TL.T_PUSH0, gain=0.03, f0=200, f1=1200, seed=11)
    narr(SV, 1, gain=0.05, seed=2)

    # ================================================================ E: dictionary.exe
    Q.window_open(SX, TL.T_DICT, gain=0.9, pan=0.0)
    for k, tt in enumerate(TL.T_TYPE): Q.key(SX, tt, gain=0.16, pan=0.1, seed=k + 3)
    Q.mouse_click(SX, TL.T_CLICK, gain=0.9, pan=0.25)
    Q.result_ding(SX, TL.T_RESULT, gain=0.9, pan=0.0)
    Q.whoosh(SX, TL.T_HI0, TL.T_HI1 - TL.T_HI0, gain=0.025, pan=-0.1, f0=1500, f1=4000, seed=12)
    Q.window_close(SX, TL.T_DICT_CLOSE, gain=0.7, pan=0.0)
    gE = Grid(84, t0=TL.T_DICT + 0.3)
    arp_n = ['A4', 'C5', 'E5', 'C5']
    notes = [(gE.t(0.5 * i) - TL.T_DICT, arp_n[i % 4], 0.6) for i in range(int((TL.T_RESULT - gE.t(0)) / (gE.spb * 0.5)) + 1)]
    M.phrase(SB, TL.T_DICT, notes, 'music_box', gain=0.05, pan=0.2, t_max=TL.T_RESULT - 0.01)
    M.phrase(SM, TL.T_DICT + 0.3, [(0, 'A2', 0.5), (0, 'E3', 0.45)], 'piano', gain=0.10)
    M.phrase(SM, TL.T_RESULT, [(0, 'F3', 0.55), (0, 'C4', 0.5), (0, 'E4', 0.5), (0, 'A4', 0.45)], 'epiano', gain=0.09)
    M.phrase(SM, TL.T_HI1 + 0.05, [(0, 'A3', 0.6), (0.02, 'E4', 0.5), (0.5, 'G#4', 0.4)], 'piano', gain=0.12)

    # ================================================================ F: calendar.exe
    Q.window_open(SX, TL.T_CAL, gain=0.9, pan=0.0)
    narr(SV, 2, gain=0.05, seed=3)
    wd0, nd = 2, 31    # Oct 2025 starts on a Wednesday
    import calendar
    wd0, nd = calendar.monthrange(2025, 10)
    k = 0
    for d in range(1, nd + 1):
        col = (wd0 + d - 1) % 7
        if col >= 5: continue
        t = TL.T_STAMP0 + k * TL.STAMP_DT; k += 1
        Q.stamp(SX, t, gain=0.75, pan=(col - 3) / 6.0, seed=d)
    Q.tension_pad(SM, TL.T_CAL + 0.2, TL.T_BIG - TL.T_CAL - 0.2, gain=0.06, notes=('A1', 'E2', 'A2', 'C3'), a=1.0)
    Q.stamp(SX, TL.T_SAT, gain=1.0, pan=0.3, big=True, seed=1, chord=('D2', 'A2', 'D3', 'F3'))
    Q.stamp(SX, TL.T_SUN, gain=1.1, pan=0.45, big=True, seed=2, chord=('A#1', 'F2', 'A#2', 'D3'))
    for j, ft in enumerate(TL.FLIPS):
        Q.paper_flip(SX, ft, gain=0.13, pan=0.1, seed=j)
        for q in range(3): Q.stamp(SX, ft + 0.012 + 0.03 * q, gain=0.35, pan=-0.3 + 0.3 * q, seed=40 + j * 3 + q)
        Q.coin(SX, ft + 0.05, gain=0.012, pan=0.6, k=j, short=True)
    Q.ticker(SX, TL.FLIPS[0], TL.T_BIG - 0.05, 8, 26, gain=0.006, f=1800, pan=0.6, seed=4)
    Q.riser(SX, TL.FLIPS[0], TL.T_BIG, gain=0.07, f0=300, f1=6000, seed=13)
    Q.stamp(SX, TL.T_BIG, gain=1.3, pan=0.0, big=True, seed=9, chord=('A1', 'A2', 'E3', 'A3'))
    Q.impact(SX, TL.T_BIG, gain=0.8)
    Q.crash(SX, TL.T_BIG, gain=0.09, d=2.4)
    SX.add(Z.thud(1.0, True, 7), TL.T_BIG + 0.01, 0.35)
    Q.typing(SX, TL.T_DICT + 0.35, TL.T_BIG, 9, 11, gain=0.022, pan=0.03, seed=7)

    # ================================================================ G: night
    Q.night_bed(NX, TL.T_NIGHT - 0.4, TL.T_TITLE + 0.3, gain=1.0, car_at=1.6)
    Q.typing(NX, TL.T_NIGHT - 0.2, TL.T_NFADE0, 6, 5, gain=0.018, pan=0.03, seed=8)
    nt = TL.T_NIGHT + 0.15
    M.phrase(NM, nt, [(0.0, 'F2', 0.5), (0.0, 'C3', 0.4), (0.6, 'A4', 0.45), (1.2, 'E5', 0.42), (1.8, 'B4', 0.38),
                      (2.6, 'D2', 0.45), (2.6, 'A2', 0.38), (3.2, 'F4', 0.36), (3.8, 'E4', 0.34)], 'piano', gain=0.15)
    narr(NV, 3, gain=0.045, shift=-5, kind='tri', seed=4)

    # ================================================================ H: title
    Q.title_sting(TM, TL.T_TITLE, gain=1.0, fx_bus=TX, swell=1.0)

    # ================================================================ mix
    pre = MS.wet(PM, 1.2, 0.25, 1) + MS.wet(PX, 0.7, 0.20, 2) + MS.wet(PV, 0.45, 0.15, 3) + AMB.x
    pre = MS.cut(pre, FREEZE)
    day = MS.wet(AM, 1.2, 0.25, 1) + MS.wet(AX, 0.7, 0.20, 2) + MS.wet(AV, 0.45, 0.15, 3)
    day[:ns(RESUME)] = 0
    day = MS.cut(day, TL.T_CRASH1, fade=0.004)
    ci = MS.wet(CI, 1.0, 0.18, 4)
    ci[:ns(TL.T_INSERT)] = 0
    ci = MS.fade(ci, TL.T_1800 - 0.02, TL.T_1800 + 0.25)
    sun = MS.wet(SM, 1.3, 0.25, 5) + MS.wet(SX, 0.8, 0.20, 6) + MS.wet(SV, 0.45, 0.15, 7) + MS.wet(SB, 1.8, 0.35, 8)
    sun[:ns(TL.T_1800 - 0.6)] = 0
    sun = MS.fade(sun, TL.T_NIGHT - 0.1, TL.T_NIGHT + 1.4, curve=1.2)
    night = MS.wet(NM, 2.2, 0.35, 9) + MS.wet(NX, 0.9, 0.15, 10) + MS.wet(NV, 0.6, 0.2, 11)
    night = MS.fade(night, TL.T_NFADE0, TL.T_TITLE + 0.2, curve=1.3)
    title = MS.wet(TM, 2.0, 0.30, 12) + MS.wet(TX, 1.0, 0.2, 13)
    mix = (pre + FZ.x + day + ci + sun + night + title)[:ns(DUR)].copy()
    mix = MS.fade(mix, DUR - 0.5, DUR)
    y = MS.finalize(mix, target_lufs=-16.5, verbose=verbose)
    if verbose:
        MS.report(y, [(0, 3.04, 'dark'), (3.04, 9.0, 'opening'), (9.0, 16.27, 'B1'), (16.27, 20.6, 'lapse'),
                      (21.0, 22.55, 'clock'), (22.55, 26.8, 'weekend'), (26.8, 28.6, '?'), (28.6, 32.4, 'dict'),
                      (32.4, 37.0, 'calendar'), (37.0, 41.4, 'night'), (41.4, 45.6, 'title')])
    return y


if __name__ == '__main__':
    y = build()
    MS.write_wav(OUT, y)
    print('wrote', OUT, f'{len(y) / Z.SR:.3f}s')
