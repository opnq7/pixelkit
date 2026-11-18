"""开场 v2 声音：配音 + 原创配乐 + 音效，全部从 timeline 取时间。 python3 audio.py -> out/s0_audio.wav
（load_vo / vo_track / duck_env 被其它关卡复用，保持接口不变）"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, wave
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s0_open'))
import numpy as np
from pixelkit.audio import synth as Z, cues as Q, master as MS
from pixelkit.audio.synth import ns, nf
from common import VO, OUT

DUR = None

def load_vo(lid):
    with wave.open(VO[lid]['wav']) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x

def vo_track(bus, lines, gain=1.0):
    for lid, a, b in lines.items():
        bus.add(load_vo(lid), a, gain, 0.0)

def duck_env(lines, n, depth=0.45, att=0.08, rel=0.25):
    env = np.ones(n)
    for lid, a, b in lines.items():
        i0, i1 = ns(max(0, a - att)), ns(b + rel)
        env[i0:i1] = np.minimum(env[i0:i1], 1 - depth)
    k = ns(0.06); env = np.convolve(env, np.ones(k) / k, mode='same')
    return env[:, None]

def epiano_chord(bus, t, notes, d=1.6, gain=0.05, pan=0.0):
    for i, n in enumerate(notes):
        bus.add(Z.fm_epiano(nf(n), d, vel=0.7, bright=0.8), t + i * 0.012, gain, pan + (i - len(notes) / 2) * 0.08)

def swish(bus, t, gain=0.05, up=True, seed=0, d=0.16):
    bus.add(Z.whoosh(d, 900 if up else 3000, 3800 if up else 900, 1.0, seed), t, gain, 0.25)

def whistle(bus, t0, notes, step=0.2, gain=0.04):
    for i, n in enumerate(notes):
        f = nf(n); d = step * 0.95
        tv = Z.tvec(d)
        x = np.sin(2 * np.pi * f * tv + 0.4 * np.sin(2 * np.pi * 6 * tv)) * np.minimum(1, tv / 0.02) * np.minimum(1, (d - tv) / 0.05)
        x = x + 0.15 * Z.fft_filter(Z.noise(d, i), lo=f * 0.8, hi=f * 1.3)
        bus.add(x, t0 + i * step, gain, -0.2)

def build(verbose=True):
    import timeline as TL
    dur = TL.DUR + 0.6
    B = lambda: Z.Bus(dur)
    MU, SX, VB, AMB = B(), B(), B(), B()
    # ---------------------------------------------------------------- night: room tone + groove (A minor, 84 bpm)
    Q.room_tone(AMB, 0.0, TL.S_OVER, hum=0.004, air=0.010, fade=0.3)
    beat = 60 / 84
    chords = [('A3', 'C4', 'E4', 'G4'), ('F3', 'A3', 'C4', 'E4'), ('C4', 'E4', 'G4', 'B4'), ('G3', 'B3', 'D4', 'F#4')]
    groove_end = TL.T_NOD1 + 0.3
    i = 0; tc = 0.0
    while tc < groove_end:
        epiano_chord(MU, tc, chords[i % 4], d=beat * 2.2, gain=0.045)
        MU.add(Z.kick_chip(0.2, 120, 45, 0.6), tc, 0.18)
        MU.add(Z.hat_chip(0.04, 0.5, i), tc + beat, 0.03, 0.3)
        root = chords[i % 4][0].replace('3', '2').replace('4', '3')
        MU.add(Z.osc('sine', nf(root), beat * 2) * Z.expdec(ns(beat * 2), beat), tc, 0.09)
        i += 1; tc += beat * 2
    mel = [(0.0, 'E5'), (0.5, 'G5'), (1.0, 'A5'), (1.5, 'E5'), (2.5, 'D5'), (3.0, 'C5'), (4.0, 'E5'), (4.5, 'G5'), (5.0, 'B5'), (6.0, 'A5')]
    for bt, n in mel:
        MU.add(Z.music_box(nf(n), 1.2, 0.8), 0.5 + bt * beat, 0.045, 0.2)
    # time-lapse: the groove doubles up (fast hats + ticker) under the wide shot
    k = 0
    while TL.S_WIDE + k * beat / 4 < TL.S_FEED2:
        MU.add(Z.hat_chip(0.03, 0.4, k), TL.S_WIDE + k * beat / 4, 0.02, -0.3); k += 1
    Q.ticker(SX, TL.S_WIDE + 0.1, TL.S_FEED2, rate0=12, rate1=28, gain=0.02)
    Q.riser(SX, TL.S_WIDE, TL.S_FEED2, gain=0.04, f0=400, f1=3000)
    # the nod: the music "falls asleep" (tape-stop glide)
    MU.add(Z.glide_tone(220, 55, 0.6, 'saw', 0.5) * 0.4, TL.T_NOD1 + 0.25, 0.05)
    # ---------------------------------------------------------------- swipes + clip sounds
    for j, ts in enumerate(TL.SWIPES):
        slow = ts == TL.SLOW_SWIPE
        swish(SX, ts - 0.02, gain=0.05 if not slow else 0.03, seed=j, d=0.16 if not slow else 0.5)
        if not slow: SX.add(Z.blip(nf(['C6', 'E6', 'G6', 'D6'][j % 4]), 0.03, 'pulse', 0.3), ts + 0.12, 0.012, 0.3)
    # ---------------------------------------------------------------- HUD / quest tracker
    SX.add(Z.glide_tone(300, 1200, 0.18, 'sine', 1.0), TL.T_CLOCK_POP, 0.03); Q.thud(SX, TL.T_CLOCK_POP + 0.02, size=0.5, gain=0.16)
    Q.ui_slide(SX, TL.T_HUD, gain=0.04, pan=-0.6)
    Q.chapter_chime(SX, TL.T_TASK, gain=0.45)
    Q.ui_slide(SX, TL.T_TASK, gain=0.04, pan=0.6)
    # ---------------------------------------------------------------- heartbeat climbs; jerk awake
    Q.heartbeat(SX, TL.S_FEED2, TL.T_HIT - 0.05, bpm0=110, bpm1=160, gain=0.55)
    Q.scratch(SX, TL.T_JERK, gain=0.35)
    SX.add(Z.glide_tone(400, 1400, 0.12, 'pulse', 0.4), TL.T_JERK, 0.03)
    Q.clock_ticks(AMB, TL.S_FEED3, TL.S_SMACK, period=0.5, gain=0.05, pan=0.5)
    # the slip: rising whoosh into the hit
    Q.whoosh(SX, TL.T_SLIP, d=TL.S_SMACK - TL.T_SLIP, gain=0.08, f0=300, f1=4000, curve=2.0)
    # ---------------------------------------------------------------- SMACK + flatline
    Q.impact(SX, TL.T_HIT, gain=0.9)
    Q.clack(SX, TL.T_HIT, size=0.9, gain=0.9)
    SX.add(Z.fft_filter(Z.noise(0.07, 9), lo=800, hi=7000) * Z.expdec(ns(0.07), 0.02), TL.T_HIT, 0.5)     # the slap
    SX.add(Z.fft_filter(Z.noise(0.5, 4), lo=2000, hi=8000) * np.linspace(1, 0, ns(0.5)) ** 2, TL.T_HIT + 0.06, 0.06, 0.6)  # cat hiss
    fl = Z.osc('sine', 1000, TL.S_OVER - TL.T_FLAT)
    SX.add(fl * np.minimum(1, np.arange(len(fl)) / 300) * np.minimum(1, (len(fl) - np.arange(len(fl))) / 2000), TL.T_FLAT, 0.07)
    Q.error_buzz(SX, TL.T_FAIL, gain=0.5)
    # ---------------------------------------------------------------- GAME OVER + 结算
    SX.add(Z.thud(1.0, True, 0, 90, 35), TL.T_GAME, 0.7); Q.whoosh(SX, TL.T_GAME - 0.12, d=0.12, gain=0.06, f0=600, f1=3000)
    Q.crash(SX, TL.T_GAME, gain=0.10, d=1.4)
    Q.ding(SX, TL.T_DING, gain=0.12, note='E6')
    sting = [('C5', 0.12), ('G4', 0.12), ('E4', 0.12), ('C4', 0.12), ('B3', 0.16), ('A#3', 0.7)]
    tt = TL.T_GAME + 0.25
    for n, d in sting:
        MU.add(Z.chip_note(nf(n), d, 'pulse', 0.25), tt, 0.06, -0.1); MU.add(Z.chip_note(nf(n) / 2, d, 'tri'), tt, 0.08, 0.1); tt += d
    Q.tension_pad(MU, TL.S_OVER, TL.S_GHOST - TL.S_OVER, gain=0.045, notes=('A1', 'E2', 'A#2', 'D#3'))
    rows_t = [TL.T_ROWS + 0.30 + i * TL.ROW_GAP for i in range(5)]
    for i, rt in enumerate(rows_t):
        SX.add(Z.thud(0.6, False, i, 160, 80), rt, 0.25); SX.add(Z.blip(nf(['A4', 'C5', 'E5', 'G5', 'A5'][i]), 0.08, 'pulse', 0.3), rt, 0.05)
        if i in (2, 3):
            Q.digit_ticks(SX, [rt + 0.08 + q * 0.045 for q in range(12)], gain=0.02)
            Q.coin(SX, rt + 0.66, gain=0.035)
        if i == 4:
            for q, f in enumerate((660, 440, 330)): SX.add(Z.blip(f, 0.09, 'pulse', 0.3), rt + 0.35 + q * 0.12, 0.05, 0.4)
    Q.stamp(SX, TL.T_STAMP, gain=0.9, big=True); Q.fail_wah(SX, TL.T_STAMP + 0.2, gain=0.45)
    # ---------------------------------------------------------------- ghost: pop, dizzy, double take, cat
    Q.whoosh(SX, TL.T_POP, d=0.6, gain=0.08, f0=300, f1=2500, seed=4); SX.add(Z.glide_tone(300, 900, 0.3, 'sine', 1.0), TL.T_POP, 0.03)
    Q.boing(SX, TL.T_POP + 0.3, gain=0.02, f=500)
    Q.dizzy(SX, TL.T_DIZZY0, d=0.6, gain=0.5)
    SX.add(Z.fft_filter(Z.noise(0.6, 5), lo=2500, hi=8000) * np.linspace(1, 0, ns(0.6)), TL.T_CAT_PUFF, 0.05, 0.6)
    Q.question(SX, TL.T_BODY, gain=0.04)
    SX.add(Z.glide_tone(500, 1500, 0.1, 'pulse', 0.4), TL.T_TAKE, 0.04); Q.jump(SX, TL.T_TAKE, gain=0.5)
    for q in range(6): SX.add(Z.blip(1200 + 200 * (q % 2), 0.04, 'pulse', 0.3), TL.T_PANIC0 + q * 0.09, 0.025, 0.2)
    SX.add(Z.fft_filter(Z.noise(0.45, 6), lo=2500, hi=8000) * np.linspace(1, 0, ns(0.45)), TL.T_CATSEE, 0.05, 0.6)
    # curious theme (C major, 100 bpm) from the ghost to the hub -- drops out on "别点了"
    b2 = 60 / 100; s2 = TL.S_GHOST + 0.4
    theme = ['E5', 'G5', 'C6', 'B5', 'A5', 'G5', 'E5', None, 'F5', 'A5', 'D6', 'C6', 'B5', 'G5', 'D5', None]
    bass = ['C3', 'C3', 'A2', 'A2', 'F2', 'F2', 'G2', 'G2']
    kk = 0
    while s2 + kk * b2 < TL.S_HUB:
        tt = s2 + kk * b2
        if not (TL.T_FREEZE - 0.05 <= tt < TL.T_CLICK):
            n = theme[kk % 16]
            if n: MU.add(Z.music_box(nf(n), 1.0, 0.8), tt, 0.05, 0.15)
            if kk % 2 == 0: MU.add(Z.pluck(nf(bass[(kk // 2) % 8]), 1.2, 0.8, 0.4, kk), tt, 0.09, -0.1)
            if kk % 2 == 1: MU.add(Z.hat_chip(0.03, 0.4, kk), tt, 0.018, 0.25)
        kk += 1
    # quest + the gag
    Q.pop(SX, TL.T_PANEL_Q + 0.05, gain=0.08); Q.chapter_chime(SX, TL.T_PANEL_Q + 0.1, gain=0.55)
    Q.ui_slide(SX, TL.T_REVIVE, gain=0.04, pan=0.6)
    Q.shimmer(SX, TL.T_REACH0, TL.T_FREEZE - TL.T_REACH0, gain=0.25)
    Q.scratch(SX, TL.T_FREEZE, gain=0.4)
    for q, f in enumerate((220, 207.65)): MU.add(Z.chip_note(f, 0.35, 'pulse', 0.4), TL.T_SKULL + q * 0.38, 0.06)
    Q.error_buzz(SX, TL.T_SKULL, gain=0.25)
    SX.add(Z.glide_tone(700, 400, 0.6, 'sine', 1.0), TL.T_RETRACT0, 0.02)
    whistle(SX, TL.T_WHISTLE0, ['G5', 'E5', 'C6', 'A5'], step=0.18, gain=0.035)
    Q.mouse_click(SX, TL.T_CLICK, gain=1.0, pan=0.0)
    for q, n in enumerate(['C5', 'E5', 'G5', 'C6', 'E6']):
        SX.add(Z.chip_note(nf(n), 0.14, 'pulse', 0.25), TL.T_CLICK + 0.04 + q * 0.05, 0.05)
    Q.sparkle(SX, TL.T_CLICK + 0.05, d=0.6, gain=0.03)
    # ---------------------------------------------------------------- hub
    Q.riser(SX, TL.S_HUB - 0.5, TL.S_HUB, gain=0.06)
    Q.shimmer(SX, TL.S_HUB, 1.6, gain=0.5)
    for q, td in enumerate(TL.T_DOORS):
        SX.add(Z.bell(nf(['C5', 'D5', 'E5', 'G5', 'A5'][q]), 1.4, 0.7), td, 0.05, -0.6 + 0.3 * q)
        Q.thud(SX, td + 0.2, size=0.3, gain=0.10, pan=-0.6 + 0.3 * q)
    Q.tension_pad(MU, TL.S_HUB, TL.END - TL.S_HUB, gain=0.06, notes=('C3', 'G3', 'D4', 'E4'))
    Q.big_ding(SX, TL.T_ACTIVE, gain=0.5)
    Q.whoosh(SX, TL.T_FLOAT0, d=1.2, gain=0.06, f0=300, f1=1500)
    Q.creak(SX, TL.T_OPEN0, gain=0.05, d=0.6)
    Q.riser(SX, TL.T_OPEN0, TL.END, gain=0.10, f0=300, f1=8000)
    # ---------------------------------------------------------------- voice + mix
    vo_track(VB, TL.L, gain=1.0)
    n = MU.x.shape[0]
    duck = duck_env(TL.L, n, depth=0.5)
    mix = MS.wet(MU, 1.4, 0.25, 1) * duck + MS.wet(SX, 0.8, 0.18, 2) + MS.wet(VB, 0.35, 0.06, 3) * 1.25 + AMB.x
    return MS.finalize(mix[:ns(dur)].copy(), target_lufs=-16.5, verbose=verbose)

if __name__ == '__main__':
    y = build()
    MS.write_wav(OUT + '/s0_audio.wav', y)
    print('wrote', OUT + '/s0_audio.wav', f'{len(y) / Z.SR:.2f}s')
