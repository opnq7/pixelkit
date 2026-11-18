"""ACT V · 周一 (42 s) - sound design + music, every cue scheduled from timeline.py.

    python3 audio.py      -> /data/projects/claude_dayoff/out/act5_audio.wav (+ section report)

ECHO     the Act IV dusk river (crickets) under the echo frame, a shimmer, dissolving into...
DESK     Monday morning: room tone, the wall clock's seconds, a faint street through the window.  The pull-back whoosh;
         HUD pop; 在线 = status_flip(on) + crt_wake (same cues as Act I); the stretch (chair creak, boing, release pop);
         09:00 = the SAME 叮 + chat_in as Act I, desk jolt thud, the bobber rattles, a finger tap stills it.
OK       好的！ + coin, identical to Act I.
REPORT   window_open; body streams = fast typing; Act I's Theme A, slowed to 100 bpm (bass + arps only, quiet) =
         'work mode'.  P.S.1 = single keys.  He stops -> the music stops; only the clock.  The selection sweep
         (highlighter squeak) + one backspace.  P.S.2 = slower, softer keys over a warm D pad (the river key) with
         music-box notes at the commas; hover tick, click, 'sent' swish + ding, a happy hop.
MID      narration voice (Claude), Act I's Theme B (the weekend theme) - keys + music box, soft.
BLACK    silence (a hard cut of the room).
TITLE    the Act I title sting.
CRED v2  「Claude 制作」 on a black stage: the spotlight clunk + lamp hum, the river key's guitar (D9 G Bm A, slow
         rolls), a coin per role (pitch climbs = the COMBO), slate clack / pops / hop / music box / boing / jump-cut
         snips / render ticks + fan -> ding; props whoosh off; ? + toast; the stats card ticks, flick, crack, shatter
         + plinks; a quiet beat for the disclaimer; stamp; bow shimmer; yawn, status off, auto-reply, snore; the spot
         dims; 叮 (one eye opens).
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/act5'))
import numpy as np
from pixelkit.audio import synth as Z, music as M, cues as Q, master as MS
from pixelkit.audio.synth import ns, nf
from pixelkit.audio.music import Grid
import timeline as TL

DUR = TL.DUR
OUT = (_PROJ + '/out/act5_audio.wav')
P_CL = 0.12                                  # Claude sits right of centre in the desk shots
P_MON = -0.3

CH = {'D9': ('D2', 'A2', 'D3', 'F#3', 'A3', 'E4'), 'G': ('G1', 'D2', 'G2', 'B2', 'F#3', 'A3'),
      'D': ('D2', 'A2', 'D3', 'F#3', 'C#4', 'E4')}

def roll(bus, ch, t, vel, seed, ring=4.5, spread=0.05):
    bus.add(Z.pluck(nf(ch[0]), ring, vel, 0.42, seed=seed), t, 0.62, pan=-0.25)
    for s in range(1, 6):
        bus.add(Z.pluck(nf(ch[s]), ring - 0.5, vel * 0.62, 0.4, seed=seed + s), t + spread * s, 0.5, pan=-0.2 + 0.08 * s)

def tiny(bus, t, f, gain=0.006, pan=0.0, d=0.05, kind='tri', glide=-1.0):
    bus.add(Z.blip(f, d, kind, 0.4, 1.0, glide=glide), t, gain, pan=pan)

CH.update({'Bm': ('B1', 'F#2', 'B2', 'D3', 'F#3', 'C#4'), 'A': ('A1', 'E2', 'A2', 'C#3', 'E3', 'B3')})

def A(u): return TL.T_CRED + u

def cred_audio(CR, CF, CG, CM):
    T = TL
    # stage: the old spotlight clunks on (and flickers), a low lamp hum for as long as it burns
    Q.switch_click(CF, A(T.C_SPOT), gain=0.9, pan=0.0)
    CF.add(Z.thud(0.25, True, 3), A(T.C_SPOT) + 0.01, 0.10)
    Q.switch_click(CF, A(T.C_SPOT + 0.13), gain=0.35, pan=0.05)
    Q.room_tone(CR, A(T.C_SPOT), A(T.C_END) + 0.2, hum=0.0035, air=0.004, fade=0.3)
    Q.shimmer(CF, A(T.C_HEAD), 1.4, gain=0.28, pan=0.0, seed=8)
    # footlights pop on from the centre outwards: a tick per pair
    for d_ in range(7):
        Q.switch_click(CF, A(T.C_FOOT0 + 0.045 * d_), gain=0.16 * (1 - 0.06 * d_), pan=float(0.12 * d_) * (1 if d_ % 2 else -1))
    # music v3: Theme B in daylight (M.weekend_bright).  1 beat = C_ROLE_DT (0.62 s), the roles land on beats.
    g = Grid(60.0 / T.C_ROLE_DT, t0=A(T.C_ROLE0 - 8 * T.C_ROLE_DT))         # bar 2 = the first role
    mute = [(A(T.C_DISC1), A(T.C_DISC_OUT + 0.1))]                           # hold the breath for the disclaimer
    M.weekend_bright(CG, g, 1, 1, layers=('bass', 'uke'), chord_bar0=3, gain=0.85, seed=10)          # bar 1: G, bass + uke
    M.weekend_bright(CG, g, 2, 7, chord_bar0=0, gain=1.0, mel=M.MEL_B, mel_bar0=2, mel_bus=CM, mutes=mute, seed=20,
                     t_max=A(T.C_DISC1))
    M.weekend_bright(CG, g, 6, 3, layers=('melody',), mel=M.MEL_B2, mel_bar0=6, mel_bus=CM, mutes=mute, t_max=A(T.C_DISC1))
    # after the disclaimer: soft again - music box over a gentle uke (批准 / the bow / the applause)
    soft = [(38, 'E5'), (39, 'G5'), (40, 'A5'), (41, 'C6'), (42, 'F6'), (44, 'E6'), (45, 'D6')]
    for (bt, nn) in soft:
        CM.add(Z.music_box(nf(nn), 2.2, 1.0), g.t(bt), 0.05, pan=0.12)
    for (bt, ch, v) in ((40, 0, 0.30), (42, 0, 0.22), (44, 3, 0.26)):
        M.uke_strum(CG, g.t(bt), M.CH_BB[ch][1], 0.05 * v / 0.3, False, d=2.0, spread=0.03, seed=200 + bt, bright=0.55)
        CG.add(Z.chip_note(Z.mtof(M.CH_BB[ch][2]), g.d(1.8), 'sine', a=0.01, d=0.5, s=0.5, r=0.3), g.t(bt), 0.07)
    # Claude sits: the last chord rings (Cadd9) + a music-box C
    M.ring_chord(CG, g.t(46), gain=0.8, d=5.0, seed=300)
    CM.add(Z.music_box(nf('C6'), 3.0, 1.0), g.t(46) + 0.02, 0.05, pan=0.12)
    CM.add(Z.music_box(nf('G6'), 2.6, 1.0), g.t(47), 0.025, pan=0.2)
    CM.add(Z.music_box(nf('A5'), 2.6, 1.0), A(T.C_PEEK + 0.02), 0.020, pan=0.1)
    # the front row: laughs, the applause, the old man nods off, 叮 wakes them both
    for i, (e, d) in enumerate(T.LAUGHS):
        Q.chuckle(CF, A(e + 0.02), n=3, gain=0.010, pan=-0.6, seed=60 + i, period=0.15, f=170)
        Q.chuckle(CF, A(e + 0.09), n=2 if i % 2 else 3, gain=0.008, pan=0.6, seed=70 + i, period=0.13, f=225)
    Q.clap_along(CF, A(T.C_CLAP0), A(T.C_CLAP1), 0.17 * 2, gain=0.05, pan=0.62, seed=80, tone=1.1)
    Q.clap_along(CF, A(T.C_CLAP0 + 0.05), A(T.C_CLAP1), 0.23 * 2, gain=0.045, pan=-0.62, seed=90, tone=0.85)
    Q.snore(CF, A(T.C_DOZE + 0.5), d_in=0.9, d_out=1.0, gain=0.35, pan=-0.6, seed=8, stop=A(T.C_DING - 0.05), whistle=False)
    Q.chuckle(CF, A(T.C_DING + 0.06), n=1, gain=0.010, pan=-0.6, seed=99, f=200)        # 'hm?'
    # run in, skid, read the name, proud
    n = 0; tt = T.C_RUN0 + 0.05
    while tt < T.C_RUN1:
        x = T.X_START + (T.X_MARK - T.X_START) * (1 - (1 - (tt - T.C_RUN0) / (T.C_RUN1 - T.C_RUN0)) ** 1.7)
        Q.step(CF, A(tt), gain=0.018, pan=float(np.clip(x / 240 - 1, -0.8, 0.8)), seed=40 + n)
        tt += 2 / 11; n += 1
    Q.swish(CF, A(T.C_RUN1 - 0.04), d=0.3, gain=0.03, pan=0.0, f0=1600, f1=500, seed=9)
    Q.soft_land(CF, A(T.C_RUN1), size=0.25, gain=0.35)
    Q.sparkle(CF, A(T.C_LOOKUP + 0.35), 0.5, 0.012, 0.0, seed=4)
    tiny(CF, A(T.C_LOOKCAM), 1700, 0.004)
    Q.jump(CF, A(T.C_PROUD), gain=0.2, f0=460, f1=920, d=0.09)
    Q.pop(CF, A(T.C_PROUD + 0.2), gain=0.02, up=False)
    Q.whoosh(CF, A(T.C_HEAD_UP0), 0.6, gain=0.012, f0=400, f1=1800, seed=12)
    # the roles: a coin each, climbing (the COMBO) + the gag's own sound
    Ti = T.C_ROLE_T
    for i, t0 in enumerate(Ti):
        Q.coin(CF, A(t0 + 0.0), gain=0.026, pan=0.15, k=[-4, -2, 0, 1, 3, 5, 7, 8][i])          # C6 .. C7
        Q.pop(CF, A(t0), gain=0.012, pan=-0.1)
    Q.swish(CF, A(Ti[0] - 0.08), d=0.12, gain=0.01, pan=0.1, f0=700, f1=2000, seed=31)
    Q.clack(CF, A(Ti[0] + 0.17), size=0.35, gain=0.7, pan=0.1, seed=11)
    Q.pop(CF, A(Ti[1] + 0.14), gain=0.03, pan=-0.2)
    Q.fall(CF, A(Ti[2]), A(Ti[2] + 0.16), gain=0.008)
    Q.soft_land(CF, A(Ti[2] + 0.16), size=0.15, gain=0.3, pan=-0.05)
    Q.jump(CF, A(Ti[3] + 0.08), gain=0.35, f0=380, f1=900, d=0.11)
    Q.soft_land(CF, A(Ti[3] + 0.44), size=0.3, gain=0.5)
    j = 0
    while Ti[4] + j * 0.31 < T.C_SHAKE:                                     # its own music, a note per floating note
        CM.add(Z.music_box(nf(['C6', 'E6', 'G6', 'E6', 'A6', 'G6', 'E6', 'D6'][j % 8]), 1.4, 1.0), A(Ti[4] + j * 0.31 + 0.01),
               0.014, pan=0.3 if j % 2 == 0 else -0.3)
        j += 1
    Q.boing(CF, A(Ti[5]), gain=0.010, f=900, d=0.35)
    for a_, pn in ((0.08, 0.15), (0.36, -0.1)):                            # jump cuts: a tape snip each
        Q.clack(CF, A(Ti[6] + a_), size=0.12, gain=0.3, pan=pn, seed=int(a_ * 100))
        Q.swish(CF, A(Ti[6] + a_ - 0.02), d=0.06, gain=0.012, pan=pn, f0=2500, f1=5000, seed=3)
    Q.progress_ticks(CF, A(Ti[7] + 0.05), A(T.C_RENDER_DONE - 0.05), rate=7.0, gain=0.7, pan=0.1, seed=3)
    CF.add(Z.fft_filter(Z.noise(T.C_RENDER_DONE - Ti[7], 55), 300, 1400) * np.linspace(0.2, 1.0, ns(T.C_RENDER_DONE - Ti[7])),
           A(Ti[7]), 0.006)                                                   # the fan spins up
    Q.riser(CF, A(Ti[7] + 0.4), A(T.C_RENDER_DONE), gain=0.012, f0=300, f1=1500, seed=6)
    Q.result_ding(CF, A(T.C_RENDER_DONE), gain=0.55, pan=0.1)
    Q.sparkle(CF, A(T.C_RENDER_DONE + 0.05), 0.6, 0.015, 0.0, seed=7)
    Q.jump(CF, A(T.C_RENDER_DONE), gain=0.15, f0=500, f1=1000, d=0.08)
    # shakes the props off
    Q.whoosh(CF, A(T.C_SHAKE), 0.25, gain=0.03, pan=-0.3, f0=600, f1=2400, seed=14)
    Q.whoosh(CF, A(T.C_SHAKE + 0.12), 0.25, gain=0.025, pan=0.3, f0=700, f1=2600, seed=15)
    Q.dizzy(CF, A(T.C_SHAKE + 0.15), d=0.45, gain=0.25)
    Q.clack(CF, A(T.C_SHAKE + 0.5), size=0.12, gain=0.25, pan=0.25, seed=17)
    # the cast
    for i, t0 in enumerate(T.C_CAST_T): Q.pop(CF, A(t0), gain=0.014, pan=0.1)
    Q.question(CF, A(T.C_FISH_Q), gain=0.05)
    Q.pop(CF, A(T.C_FISH_TOAST), gain=0.03, pan=0.4)
    CF.add(Z.glide_tone(700, 330, 0.35, 'sine', 1.0, 0.8), A(T.C_FISH_TOAST + 0.05), 0.012, pan=0.4)   # 鱼获：0 (womp)
    for q in range(3): tiny(CF, A(T.C_FISH_DOTS + 0.12 * q), 1300 - 120 * q, 0.004, d=0.04)
    # the stats card
    Q.window_open(CF, A(T.C_CARD), gain=0.55, pan=0.0)
    for r in T.C_CARD_ROWS:
        Q.digit_ticks(CF, [A(r + 0.04 * q) for q in range(6)], gain=0.008, f0=2200, f1=3400, pan=0.0)
    Q.coin(CF, A(T.C_BIG), gain=0.03, pan=0.2, k=7)
    Q.sparkle(CF, A(T.C_BIG + 0.02), 0.4, 0.01, 0.2, seed=9)
    tiny(CF, A(T.C_UNIMP), 600, 0.004, d=0.12, glide=-0.3)
    Q.swish(CF, A(T.C_FLICK - 0.06), d=0.1, gain=0.012, pan=0.2, f0=900, f1=3000, seed=19)
    Q.clack(CF, A(T.C_FLICK), size=0.08, gain=0.35, pan=0.15, seed=20)
    for q in range(5):                                                       # the glass cracks
        CF.add(Z.fft_filter(Z.noise(0.01, 300 + q), 3000, 9000) * Z.expdec(ns(0.01), 0.002), A(T.C_FLICK + 0.03 + q * 0.04), 0.01)
    Q.crash(CF, A(T.C_SHATTER), gain=0.05, d=1.2, tau=0.35)
    Q.thud(CF, A(T.C_SHATTER), size=0.3, gain=0.15)
    from pixelkit import credits as CRD, ui as UI
    card = CRD.stats_card(0.0, T.CARD_ROWS, [1, 1, 1, 1], big_k=1.0, crack=1.0)
    hits = UI.shatter_hits(card, T.CARD_X, T.CARD_Y, T.FLOOR_Y + 2, seed=7)
    for q, (ht, hx) in enumerate(hits[::max(1, len(hits) // 18)]):
        tiny(CF, A(T.C_SHATTER + ht), 2400 + 900 * ((q * 7) % 5), 0.0025, pan=float(np.clip(hx / 240 - 1, -0.8, 0.8)), d=0.03)
    # disclaimer: a beat of nothing, then the shrug
    Q.boing(CF, A(T.C_SHRUG + 0.05), gain=0.005, f=700, d=0.25)
    Q.chuckle(CF, A(T.C_SHRUG + 0.55), n=1, gain=0.008, f=240)
    # 批准
    Q.stamp(CF, A(T.C_STAMP), gain=0.9, pan=0.3)
    Q.sparkle(CF, A(T.C_STAMP + 0.05), 0.5, 0.012, 0.3, seed=5)
    Q.swish(CF, A(T.C_BOW0), d=0.4, gain=0.008, f0=400, f1=1100, seed=23)
    Q.shimmer(CF, A(T.C_BOW0 + 0.2), 1.0, gain=0.18, seed=10)
    Q.pop(CF, A(T.C_HEART), gain=0.03)
    Q.jump(CF, A(T.C_HEART + 0.02), gain=0.15, f0=520, f1=1040, d=0.08)
    # goes on leave
    Q.sigh(CF, A(T.C_YAWN0 + 0.1), d=0.9, gain=0.02)
    Q.creak(CF, A(T.C_YAWN0 + 0.3), gain=0.008, seed=5, d=0.3, f0=260, f1=200)
    Q.status_flip(CF, A(T.C_OFF), gain=0.8, pan=0.6, on=False)
    Q.soft_land(CF, A(T.C_SIT), size=0.3, gain=0.45)
    Q.plop(CF, A(T.C_BOB + 0.02), gain=0.05, seed=3)
    Q.auto_reply(CF, '自动回复：Claude 休假中。彩蛋在后面，请稍等～', A(T.C_AUTO + 0.12), cps=30, gain=0.012, pan=-0.3)
    Q.snore(CF, A(T.C_ZZZ), d_in=0.8, d_out=0.95, gain=0.8, seed=3, stop=A(T.C_DING - 0.05), whistle=False)
    Q.switch_click(CF, A(T.C_DIM0), gain=0.25, pan=0.0)
    Q.ding(CF, A(T.C_DING), gain=0.07, pan=-0.3)
    tiny(CF, A(T.C_PEEK), 1500, 0.003)

def build(verbose=True):
    B = lambda: Z.Bus(DUR)
    EC = B()                                   # echo (river)
    AMB, FX, FX2, MU, VO = B(), B(), B(), B(), B()   # the morning (fades with the picture at T_MID_END)
    CR, CF, CG, CM = B(), B(), B(), B()        # credits: stage bed / fx / groove / melody

    # ================================================================ ECHO
    Q.river_bed(EC, 0.0, TL.T_DISS1 + 0.4, gain=2.2, seed=91, crickets=True, fade_in=0.5, fade_out=1.0)
    Q.shimmer(FX2, 0.35, 1.3, gain=0.30, pan=0.2, seed=4)

    # ================================================================ the morning beds
    Q.room_tone(AMB, TL.T_DISS0, TL.T_MID_END + 0.1, hum=0.004, air=0.010, fade=0.8)
    Q.morning_bed(AMB, TL.T_DISS0, TL.T_MID_END + 0.1, gain=0.55, fade_in=1.0, fade_out=1.2, birds_rate=0.35)
    Q.clock_ticks(AMB, 3.0, TL.T_0900, period=1.0, gain=0.05, pan=-0.35)
    Q.clock_ticks(AMB, TL.T_0900 + 1.0, TL.T_MID_END - 0.6, period=1.0, gain=0.05, pan=-0.35)

    # ================================================================ DESK
    Q.whoosh(FX, TL.T_PULL0, TL.T_PULL1 - TL.T_PULL0, gain=0.018, f0=180, f1=900, seed=11)
    Q.ui_slide(FX, TL.T_HUD, gain=0.03, pan=-0.6); Q.pop(FX, TL.T_HUD + 0.12, gain=0.02, pan=0.6)
    Q.crt_wake(FX, TL.T_ONLINE, gain=0.45, pan=P_MON)
    Q.status_flip(FX, TL.T_ONLINE + 0.05, gain=0.8, pan=0.6, on=True)
    s0, s1 = TL.T_STRETCH0, TL.T_STRETCH1
    Q.creak(FX, s0 + 0.05, gain=0.012, pan=P_CL, seed=3, d=0.3, f0=240, f1=200)
    Q.swish(FX, s0 + 0.25, d=0.4, gain=0.008, pan=P_CL, seed=5, f0=300, f1=1100)
    Q.boing(FX, s0 + 0.55, gain=0.006, pan=P_CL, f=980)
    Q.pop(FX, s1 - 0.12, gain=0.02, pan=P_CL, up=False)
    Q.creak(FX, s1 - 0.05, gain=0.010, pan=P_CL, seed=4, d=0.25, f0=220, f1=170)
    tiny(FX, TL.T_LOOK_B + 0.05, 1500, 0.003, P_CL)
    Q.sparkle(FX2, TL.T_SMILE, 0.3, 0.004, 0.3, seed=2)
    # 09:00 - Act I's 叮 + message
    Q.ding(FX, TL.T_0900, gain=0.13, pan=-0.45)
    Q.chat_in(FX, TL.MSG['t_in'], gain=0.065, pan=-0.55, k=0)
    FX.add(Z.thud(0.4, True, 5), TL.T_0900 + 0.01, 0.10, pan=0.2)
    for k in range(6):                                        # the bobber rattles on its brick
        FX.add(Z.fft_filter(Z.noise(0.012, 120 + k), 1500, 6000) * Z.expdec(ns(0.012), 0.003),
               TL.T_0900 + 0.03 + k / 6.4, 0.012 * np.exp(-k * 0.45), pan=0.3)
    FX.add(Z.fft_filter(Z.noise(0.02, 140), 400, 2000) * Z.expdec(ns(0.02), 0.005), TL.T_FINGER0 + 0.35, 0.012, pan=0.3)
    Q.boing(FX, TL.T_0900 + 0.05, gain=0.004, pan=P_CL, f=880)

    # ================================================================ OK
    Q.ok(FX, TL.T_OK, gain=1.0, pan=0.05)
    Q.coin(FX, TL.T_OK + 0.30, gain=0.032, pan=0.15)

    # ================================================================ REPORT
    Q.window_open(FX, TL.T_REPORT, gain=0.9, pan=-0.2)
    stream_end = TL.STREAM_T[-1] + len(TL.REPORT_LINES[-1]) / TL.STREAM_CPS
    Q.typing(FX, TL.T_STREAM0, stream_end, 24, 28, gain=0.04, pan=P_CL, seed=7)
    for i, tt in enumerate(TL.PS1_T): Q.key(FX, tt, gain=0.12, pan=P_CL, seed=20 + i)
    gw = Grid(100, t0=TL.T_STREAM0 - 0.05)
    M.theme_a(MU, gw, bar0=0, bars=4, layers=('bass', 'arp'), gain=0.32, t_max=TL.T_PS1_LOOK)
    Q.boing(FX, TL.T_PS1_LOOK + 0.25, gain=0.004, pan=P_CL, f=820)
    Q.highlighter(FX, TL.T_DEL0, d=0.38, gain=0.55, pan=-0.1, seed=3)
    Q.key(FX, TL.T_DEL1 - 0.05, gain=0.20, pan=P_CL, seed=60)
    Q.pop(FX, TL.T_DEL1 - 0.03, gain=0.014, pan=-0.1, up=False)
    for i, tt in enumerate(TL.PS2_T[5:]): Q.key(FX, tt, gain=0.085, pan=P_CL, seed=70 + i)
    Q.pad_swell(MU, TL.T_PS2 - 0.15, TL.T_MID - TL.T_PS2 + 0.6, notes=('D3', 'A3', 'F#4', 'E5'), gain=0.022, a=1.4, r=0.8,
                cutoff=1000, seed=6)
    ps2 = TL.PS2
    marks = [ps2.index('，'), ps2.index('坐坐') + 1, len(ps2) - 1]
    for nn, ci in zip(('D6', 'F#6', 'A6'), marks):
        FX2.add(Z.music_box(nf(nn), 2.2, 1.0), TL.PS2_T[ci] + 0.02, 0.022, pan=-0.15)
    tiny(FX, TL.T_SEND - 0.18, 2600, 0.003, -0.4, d=0.02)
    Q.mouse_click(FX, TL.T_SEND, gain=0.9, pan=-0.4)
    Q.whoosh(FX, TL.T_SEND + 0.12, 0.3, gain=0.03, pan=-0.5, f0=900, f1=3500, seed=21)
    Q.result_ding(FX, TL.T_SEND + 0.16, gain=0.45, pan=-0.4)
    Q.jump(FX, TL.T_SEND + 0.02, gain=0.25, pan=P_CL, f0=420, f1=840, d=0.1)
    Q.soft_land(FX, TL.T_SEND + 0.22, size=0.2, gain=0.3, pan=P_CL)
    # the window folds back into the monitor, the camera drifts to Claude; 小李 is typing ... two replies; ^ ^
    Q.window_close(FX, TL.T_WIN_CLOSE, gain=0.8, pan=-0.3)
    Q.whoosh(FX, TL.T_WIN_CLOSE + 0.1, 0.7, gain=0.008, f0=250, f1=900, seed=24)
    tt, q = TL.T_TYPING + 0.1, 0
    while tt < TL.T_REPLY1 - 0.1:                                   # the three dots: a soft tick each
        tiny(FX, tt, [1900, 2150, 2400][q % 3], 0.0022, -0.45, d=0.03)
        tt += 0.15 if q % 3 < 2 else 0.30; q += 1
    Q.chat_in(FX, TL.T_REPLY1, gain=0.06, pan=-0.5, k=1)
    Q.chat_in(FX, TL.T_REPLY2, gain=0.065, pan=-0.5, k=2)
    Q.jump(FX, TL.T_REACT, gain=0.18, pan=P_CL, f0=480, f1=960, d=0.08)
    Q.boing(FX, TL.T_REACT + 0.05, gain=0.006, pan=P_CL, f=1000)
    Q.sparkle(FX2, TL.T_REACT + 0.03, 0.5, 0.010, P_CL, seed=12)
    for nn, dt in (('A5', 0.0), ('D6', 0.16)):
        FX2.add(Z.music_box(nf(nn), 2.0, 1.0), TL.T_REACT + 0.02 + dt, 0.024, pan=0.1)
    Q.soft_land(FX, TL.T_REACT + 0.3, size=0.15, gain=0.25, pan=P_CL)
    FX2.add(Z.music_box(nf('A6'), 2.4, 1.0), TL.T_LOOK_CAL + 0.1, 0.022, pan=0.35)      # the red circle on Saturday
    Q.whoosh(FX, TL.T_LOOK_CAL, 0.6, gain=0.006, f0=300, f1=900, seed=25)

    # ================================================================ MID
    for bx in TL.BOXES:
        Q.box_open(VO, bx['t_open'] - 0.12, gain=0.02)
        for ln in bx['lines']:
            Q.voice_line(VO, ln['zh'], ln['t0'], ln['cps'], gain=0.045, shift=-5, kind='tri', seed=4, times=ln['times'])
    gb = Grid(84, t0=TL.T_MID + 0.2)
    M.theme_b(MU, gb, bar0=0, bars=3, layers=('keys', 'melody'), gain=0.55, t_max=TL.T_MID_END - 0.4, mel_bus=FX2)


    # ================================================================ CRED v2 「Claude 制作」 (see credits_tl.py)
    cred_audio(CR, CF, CG, CM)

    # ================================================================ mix
    duck = np.ones(ns(DUR) + Z.SR * 3)
    for bx in TL.BOXES: duck[ns(bx['t_open']):ns(bx['t_close'])] = 0.8
    k = np.ones(ns(0.3)) / ns(0.3); duck = np.convolve(duck, k, mode='same')[:, None]
    echo = MS.fade(EC.x.copy(), TL.T_DISS0, TL.T_DISS1 + 0.3, curve=1.2)
    morn = (MS.wet(MU, 2.2, 0.35, 1) * duck[:len(MU.x)] + MS.wet(FX, 0.8, 0.18, 2) + MS.wet(FX2, 2.6, 0.5, 3)
            + MS.wet(VO, 0.6, 0.2, 4) + AMB.x)
    morn = MS.fade(morn, TL.T_MID_END - 0.95, TL.T_MID_END + 0.15, curve=1.2)
    cred = 0.30 * MS.wet(CG, 1.5, 0.16, 7) + 0.40 * MS.wet(CM, 2.2, 0.30, 9) + MS.wet(CF, 1.2, 0.22, 8) + CR.x
    cred[:ns(TL.T_CRED - 0.25)] = 0
    mix = (echo + morn + cred)[:ns(DUR)].copy()
    mix = MS.fade(mix, TL.T_CRED + TL.C_FADE0, DUR, curve=1.3)
    y = MS.finalize(mix, target_lufs=-16.5, verbose=verbose)
    if verbose:
        MS.report(y, [(0, TL.T_DISS1, 'ECHO'), (TL.T_DISS1, TL.T_0900, 'DESK'), (TL.T_0900, TL.T_REPORT, '09:00/OK'),
                      (TL.T_REPORT, TL.T_PS1_LOOK, 'REPORT'), (TL.T_PS1_LOOK, TL.T_PS2, 'hesitate'), (TL.T_PS2, TL.T_SEND, 'PS2'),
                      (TL.T_SEND, TL.T_MID, 'REPLY'), (TL.T_MID, TL.T_MID_END, 'MID'),
                      (TL.T_CRED, A(TL.C_ROLE0), 'CR intro'), (A(TL.C_ROLE0), A(TL.C_CAST_H), 'CR roles'),
                      (A(TL.C_CAST_H), A(TL.C_DISC1), 'CR cast/card'), (A(TL.C_DISC1), A(TL.C_YAWN0), 'CR disc/thx'),
                      (A(TL.C_YAWN0), DUR, 'CR leave')])
    return y


if __name__ == '__main__':
    y = build()
    MS.write_wav(OUT, y)
    print('wrote', OUT, f'{len(y) / Z.SR:.3f}s')
