"""Opening (10.5 s) - music + sound design. Every cue is scheduled from timeline.py (single source of truth).

    python3 audio.py            -> ../out/opening_audio.wav  (+ section report)

Buses: pre-freeze (music / sfx / voice / ambience) are reverberated and then HARD-CUT at T_FREEZE;
the freeze bus is dry and intimate; post-resume buses restart on G2 with the impact.
World-time events (bricks, rain bubbles, coins) are mapped to real time with TL.real().
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/opening'))
import numpy as np
from pixelkit.audio import synth as Z, music as M, cues as Q, master as MS
from pixelkit.audio.synth import ns
import timeline as TL
from timeline import b, G, G2

DUR = TL.DUR
FREEZE, RESUME = TL.T_FREEZE, TL.T_RESUME
OUT = (_PROJ + '/out/opening_audio.wav')


def pan_of(x, t):
    """world x -> stereo pan through the camera at time t."""
    z, cx, cy, sx, sy = TL.cam_params(min(t, FREEZE - 1e-3) if t < RESUME else t)
    return float(np.clip((x - cx) * z / 240.0 * 0.85, -0.85, 0.85))


def build(verbose=True):
    B = lambda: Z.Bus(DUR)
    PM, PX, PV, AMB = B(), B(), B(), B()          # pre-freeze: music, sfx, voice, ambience
    AM, AX, AV = B(), B(), B()                    # post-resume
    FZ = B()                                      # the freeze (dry)
    X = lambda t: PX if t < FREEZE else AX        # route by real start time
    V = lambda t: PV if t < FREEZE else AV

    # ---------------------------------------------------------------- 0-3 s: dark office, Claude asleep
    Q.room_tone(AMB, 0.0, FREEZE + 0.3, hum=0.006, air=0.016, fade=0.5)
    Q.clock_ticks(AMB, 0.30, 3.0, period=1.0, gain=0.085, pan=-0.35)
    # snores breathe with the status LED (period 2 s, brightest at 0.75 / 2.75); the second exhale is cut by the '叮'
    Q.snore(AMB, 0.05, d_in=0.70, d_out=0.95, gain=2.0, pan=0.0, seed=1)
    Q.snore(AMB, 1.95, d_in=0.80, d_out=0.95, gain=2.0, pan=0.0, seed=2, stop=TL.T_DING - 0.005)
    Q.pad_swell(PM, 1.6, 2.7, notes=('C3', 'G3', 'E4', 'B4'), gain=0.11, a=1.45, r=1.0, cutoff=1500)

    # ---------------------------------------------------------------- 叮 -> wake -> first 好的
    Q.ding(PX, TL.T_DING, gain=0.13, pan=-0.45)
    Q.crt_wake(PX, TL.T_DING + 0.015, gain=0.9, pan=-0.55)
    Q.jump(PX, TL.T_WAKE, gain=1.0, pan=0.0)
    Q.thud(PX, TL.T_HOP_LAND, size=0.35, gain=0.22, pan=0.0, seed=4)

    # Claude's 好的！ (+ coin icon in the bubble); jingle transposed to the chord underneath
    for i, to in enumerate(TL.OKS):
        sh = 0 if to < G.bar(1) else 2
        Q.ok(V(to), to, gain=1.0, pan=0.05, shift=sh)
        Q.coin(X(to), to + 0.30, gain=0.032, pan=0.15, k=sh)

    # chat feed (left): incoming bubbles
    for m in TL.MSGS[1:]:
        Q.chat_in(X(m['t_in']), m['t_in'], gain=0.065, pan=-0.55, k=m['i'])

    # ---------------------------------------------------------------- bricks (from the physics sim)
    sim, hero = TL.build_sim()
    body = {bd.id: bd for bd in sim.bodies}
    spawn = {e[2]['id']: e[0] for e in sim.events if e[1] == 'spawn'}
    rain_t = [TL.real(e[0]) for e in sim.events if e[1] == 'land' and e[2]['name'] == 'rain']
    for (tw, kind, d) in sim.events:
        if kind == 'spawn': continue
        t = TL.real(tw); bd = body[d['id']]; p = pan_of(d['x'], t)
        size = float(np.clip((bd.w - 18) / 40.0, 0.2, 0.85))
        if d['name'].startswith('msg'):
            first = not any(e[2]['id'] == d['id'] and e[0] < tw and e[1] != 'spawn' for e in sim.events)
            if first: Q.fall(X(t), TL.real(spawn[d['id']]) + 0.05, t, gain=0.02, pan=p)
            if kind == 'bonk':
                Q.bonk(X(t), t, gain=1.0, pan=0.0)
            else:
                Q.clack(X(t), t, size=max(size, 0.6), gain=1.15, pan=p, seed=d['id'])
        else:
            dens = sum(1 for r in rain_t if abs(r - t) < 0.25)
            g = 0.75 / max(1.0, dens / 2.5) ** 0.5
            Q.clack(X(t), t, size=size, gain=g, pan=p, seed=d['id'])

    # ---------------------------------------------------------------- typing (stops when dizzy and in the freeze)
    bonk_t = TL.MSGS[2]['t_land']
    for (t0, t1, r0, r1, s) in [(TL.T_OK0 + 0.36, bonk_t - 0.02, 12, 12, 1), (bonk_t + 0.6, TL.T_WIDE, 12, 14, 2),
                                (TL.T_WIDE, FREEZE, 14, 26, 3)]:
        Q.typing(PX, t0, t1, r0, r1, gain=0.045, pan=0.03, seed=s)
    Q.typing(AX, RESUME, DUR, 26, 26, gain=0.045, pan=0.03, seed=4)

    # ---------------------------------------------------------------- wide shot: HUD + the rain of 好的 / coins
    Q.riser(PX, 5.85, TL.T_WIDE, gain=0.045, f0=250, f1=3200, seed=5)        # zoom-out swell into the downbeat
    Q.ui_slide(PX, TL.T_HUD_COUNTER, gain=0.04, pan=0.6)
    Q.ui_slide(PX, TL.T_HUD_TIME, gain=0.035, pan=-0.6, seed=10)
    shifts = [0, 2, 4, 7, 9]
    for ob in TL.OK_BURSTS:
        t = TL.real(ob['tw'])
        if t < DUR:
            Q.ok(V(t), t, gain=0.38, pan=float(np.clip(ob['dx'] / 120, -0.5, 0.5)), shift=shifts[ob['k']], jingle=False)
        tc = TL.real(ob['tw'] + TL.COIN_DELAY + TL.COIN_FLY)
        if tc < DUR and not (FREEZE <= tc < RESUME):
            Q.coin(X(tc), tc, gain=0.014, pan=0.6, k=shifts[ob['k']], short=True)
    Q.riser(PX, TL.T_RISER, FREEZE, gain=0.085, f0=500, f1=6500)

    # ---------------------------------------------------------------- music (Theme A, 132 bpm, beat 0 = 叮)
    C, Am, F, Gc = M.CH_A; e = 1e-6
    M.bass(PM, G, [C], bar0=0, nbars=1, t_min=b(2) - e, t_max=FREEZE)                 # bar 0: enters with the 1st brick
    M.drums(PM, G, 0, 1, kick=(2,), snare=(), hats=2, t_min=b(2) - e, t_max=FREEZE)
    M.bass(PM, G, [Am], bar0=1, nbars=1, t_max=FREEZE)                                # bar 1: + arp + drums
    M.arp(PM, G, [Am], bar0=1, nbars=1, gain=0.020, t_max=FREEZE)
    M.drums(PM, G, 1, 1, hats=2, t_max=FREEZE)
    M.bass(PM, G, [F], bar0=2, nbars=1, t_max=b(10) - e)                              # bar 2: F -> G, 16th runs
    M.bass(PM, G, [Gc], bar0=2, nbars=1, t_min=b(10) - e, t_max=FREEZE)
    M.arp(PM, G, [F], bar0=2, nbars=1, gain=0.024, t_max=b(10) - e)
    M.arp(PM, G, [Gc], bar0=2, nbars=1, sub=8, gain=0.022, t_min=b(10) - e, t_max=FREEZE)
    M.drums(PM, G, 2, 1, kick=(0, 2, 3), snare=(1,), hats=4, t_max=FREEZE)
    runs = [M._RUNS[0], M._RUNS[1], M._RUNS[4], M._RUNS[7]]
    mel = [(8 + i + 0.25 * k, 0.25, nn) for i, r in enumerate(runs) for k, nn in enumerate(r)]
    M.lead(PM, G, mel, 0, gain=0.075, echo=0.022, t_max=FREEZE)
    M.roll(PM, G, 10, 2, div=4, g0=0.035, g1=0.11, t_max=FREEZE)

    # ---------------------------------------------------------------- the freeze: only Claude is alive
    Q.room_tone(FZ, FREEZE, RESUME + 0.05, hum=0.0022, air=0.0045, fade=0.03)
    Q.ok(FZ, TL.T_TINY_OK, gain=0.6, pan=0.0, shift=3, jingle=False)
    FZ.add(Z.glide_tone(700, 2100, TL.T_COIN1 - TL.T_COIN0, 'sine', 1.0, 0.8), TL.T_COIN0, 0.010, pan=0.3)
    Q.coin(FZ, TL.T_COIN1, gain=0.042, pan=0.55)
    Q.pop(FZ, TL.T_COIN1 + 0.025, gain=0.03, pan=0.6)

    # ---------------------------------------------------------------- resume: impact + Theme A from the top
    Q.impact(AX, RESUME, gain=1.0)
    M.stab(AM, RESUME, gain=0.05, d=0.9, bass_gain=0.16)
    M.theme_a(AM, G2, bar0=0, bars=1)

    # ---------------------------------------------------------------- mix
    pre = MS.wet(PM, 1.2, 0.25, 1) + MS.wet(PX, 0.7, 0.20, 2) + MS.wet(PV, 0.45, 0.15, 3) + AMB.x
    pre = MS.cut(pre, FREEZE)
    post = MS.wet(AM, 1.2, 0.25, 1) + MS.wet(AX, 0.7, 0.20, 2) + MS.wet(AV, 0.45, 0.15, 3)
    post[:ns(RESUME)] = 0
    mix = (pre + FZ.x + post)[:ns(DUR)].copy()
    mix = MS.fade(mix, TL.T_FADE0, TL.T_END)
    y = MS.finalize(mix, target_lufs=-16.5, verbose=verbose)
    if verbose:
        MS.report(y, [(0, 1.6, 'dark'), (1.6, 3.04, 'lights'), (3.04, 4.86, 'bar0'), (4.86, 6.68, 'bar1'),
                      (6.68, 8.5, 'rain'), (8.5, 9.0, 'freeze'), (9.0, 10.5, 'burst')])
    return y


if __name__ == '__main__':
    y = build()
    MS.write_wav(OUT, y)
    print('wrote', OUT, f'{len(y) / Z.SR:.3f}s')
