"""ACT II (47.0 s) - music + sound design, every cue scheduled from timeline.py.

    python3 audio.py      -> ../out/act2_audio.wav (+ section report)

F  (0-21.4)  lofi e-piano bed while filling the form -> tension pad + heartbeat at the submit button -> hard stop on click
W  (21.4-34.2) Wang: tired typing, toast, silence + clock while he reads, Theme B (weekend) teased on music box as he smiles
S  (34.2-47) stamp + F-major chord -> Theme B full (the weekend is coming) -> shutdown, lamp click, silence
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/act2'))
import numpy as np
from pixelkit.audio import synth as Z, music as M, cues as Q, master as MS
from pixelkit.audio.synth import ns
from pixelkit.audio.music import Grid, CH_B
import timeline as TL

DUR = TL.DUR
OUT = (_PROJ + '/out/act2_audio.wav')
CH_F = [('Fmaj7', [53, 57, 60, 64], 41), ('Em7', [52, 55, 59, 62], 40), ('Dm7', [50, 53, 57, 60], 38),
        ('Cmaj7', [48, 55, 59, 64], 36)]
GF = Grid(80, t0=TL.T_FORM)          # form-filling bed: downbeat = the form window opening
GW = Grid(84, t0=TL.T_SMILE)         # Wang smiles -> Theme B on music box
GS = Grid(84, t0=TL.T_CMT_SHOW)      # approved -> Theme B full
P_UI, P_CL = 0.1, 0.3                # UI / Claude pan in the F and S shots


def upan(x): return float(np.clip((x - 240) / 240 * 0.8, -0.8, 0.8))


def build(verbose=True):
    B = lambda: Z.Bus(DUR)
    AMB = B()
    FM, FX, FV = B(), B(), B()
    WM, WX = B(), B()
    SM, SX = B(), B()

    # ================================================================ ambience (whole act)
    Q.night_bed(AMB, 0.0, DUR, gain=1.0, car_at=22.6, car_d=3.0, fade_in=0.6, fade_out=1.4)
    Q.clock_ticks(AMB, 0.0, TL.T_W, period=1.0, gain=0.022, pan=-0.4)     # v2: ticks from frame 0 = sound bridge out of Act I's black

    # ================================================================ F: the form
    # v2 opening (no chapter banner): HUD slides in, the minute turns, Claude stops, decides, double-clicks
    Q.ui_slide(FX, TL.T_HUD_IN, gain=0.022, pan=-0.5)
    Q.tock(FX, TL.T_FLIP, gain=0.55, pan=-0.45, low=False)
    Q.typing(FX, 0.35, TL.T_TYPE_STOP, 7, 6, gain=0.018, pan=P_CL, seed=3)
    Q.pop(FX, TL.T_PERK, gain=0.035, pan=P_CL)
    for tt in TL.T_DBL: Q.mouse_click(FX, tt, gain=0.8, pan=P_CL, up=0.05)
    Q.window_open(FX, TL.T_FORM, gain=0.9, pan=P_UI)
    for r in TL.ROWS:
        for i, tt in enumerate(r.get('times', [])):
            if r['text'][i] in Q.PUNCT: continue
            Q.key(FX, tt, gain=0.075, pan=P_CL)
    Q.digit_ticks(FX, TL.work_tick_times(), gain=0.018, pan=P_UI)
    Q.error_buzz(FX, TL.T_OVF, gain=1.0, pan=P_UI)
    Q.pop(FX, TL.T_OVF + 0.06, gain=0.05, pan=P_CL)
    for k, (h0, h1, i, txt) in enumerate(TL.HOVERS):
        Q.pop(FX, h0, gain=0.035, pan=P_UI)
        Q.deny(FX, h0 + 0.18, gain=1.0, pan=P_UI, k=k)
    Q.checkbox(FX, TL.T_CHECK, gain=1.0, pan=P_UI)
    Q.ok(FX, TL.T_CHECK + 0.22, gain=0.6, pan=P_CL, jingle=False)
    # music: lofi e-piano + soft bass + lazy drums, 4 bars, then the room drops out at the submit button
    M.keys_comp(FM, GF, CH_F, 0, 4, gain=0.036, ring_last=False, t_max=TL.T_CUR_SUB0)
    M.soft_bass(FM, GF, CH_F, 0, 4, gain=0.11, ring_last=False, t_max=TL.T_CUR_SUB0)
    M.lazy_drums(FM, GF, 0, 4, gain=0.5, ring_last=False, t_min=GF.bar(1), t_max=TL.T_CUR_SUB0)
    for (b, d, nn) in [(0, 1, 'A5'), (1, .5, 'C6'), (1.5, .5, 'E6'), (2, 2, 'D6')]:     # music box hint of the weekend theme
        FM.add(Z.music_box(Z.nf(nn), 1.8, 1.0), GF.t(3 * 4 + b), 0.04, pan=0.15)
    # hesitation
    Q.tension_pad(FM, TL.T_CUR_SUB0, TL.T_CLICK - TL.T_CUR_SUB0 + 0.1, gain=0.075, notes=('Bb2', 'F3', 'A3', 'D4'), a=1.8,
                  cutoff=1200)
    Q.heartbeat(FX, TL.T_CUR_SUB1 + 0.1, TL.T_CLICK - 0.15, 56, 74, gain=1.0)
    Q.box_open(FV, TL.NAR['t_open'] - 0.12, gain=0.02, low=True)
    Q.voice_line(FV, TL.NAR['zh'], TL.NAR['t0'], TL.NAR['cps'], gain=0.045, shift=-5, kind='tri', seed=4, times=TL.NAR['times'])
    for k, (tp, x, y, txt) in enumerate(TL.PINGS):
        Q.chat_in(FX, tp, gain=0.03 + 0.004 * k, pan=upan(x), k=k)
    Q.mouse_click(FX, TL.T_CLICK, gain=1.1, pan=P_UI)
    Q.window_open(FX, TL.T_PROG, gain=0.6, pan=P_UI)
    Q.progress_ticks(FX, TL.T_PROG + 0.3, TL.T_W, rate=5.0, gain=1.0, pan=P_UI)

    # ================================================================ W: Wang Gong
    Q.typing(WX, TL.T_W, TL.T_STOP, 10, 9, gain=0.04, pan=0.0, seed=21)
    Q.ui_slide(WX, TL.T_NAME0, gain=0.03, pan=-0.6)
    M.phrase(WM, TL.T_NAME0 + 0.05, [(0.0, 'D2', 0.5), (0.0, 'A2', 0.4), (0.5, 'F4', 0.3)], 'piano', gain=0.13)
    Q.toast(WX, TL.T_TOAST, gain=1.0, pan=0.55)
    Q.window_open(WX, TL.T_OA, gain=0.9, pan=-0.35)
    Q.highlighter(WX, TL.T_HI0, TL.T_HI1 - TL.T_HI0 + 0.1, gain=1.0, pan=-0.35)
    Q.clock_ticks(WX, TL.T_HI1 + 0.4, TL.T_SMILE, period=1.0, gain=0.035, pan=-0.4)
    Q.pop(WX, TL.T_TWO + 0.25, gain=0.03, pan=-0.3)                       # Claude's tiny 审批中… bubble
    for i, tt in enumerate(TL.CMT_TIMES):
        if ''.join(TL.COMMENT)[i] in Q.PUNCT: continue
        Q.key(WX, tt, gain=0.06, pan=0.0)
    Q.mouse_click(WX, TL.T_APPROVE, gain=1.0, pan=-0.2)
    Q.stamp(WX, TL.T_APPROVE + 0.08, gain=0.8, pan=-0.2)
    # Theme B (the weekend) - he smiles: keys + bass + music-box melody, 2 bars, then a warm F chord on approve
    M.keys_comp(WM, GW, CH_B, 0, 2, gain=0.04, ring_last=True)
    M.soft_bass(WM, GW, CH_B, 0, 2, gain=0.12, ring_last=True)
    for (b, d, nn) in M.MEL_B:
        if b < 8: WM.add(Z.music_box(Z.nf(nn), 1.8, 1.0), GW.t(b), 0.07, pan=0.15)
    M.phrase(WM, TL.T_APPROVE, [(0.0, 'F2', 0.55), (0.01, 'C3', 0.45), (0.02, 'A3', 0.45), (0.03, 'F4', 0.4)], 'piano', gain=0.15)

    # ================================================================ S: approved -> offline
    Q.result_ding(SX, TL.T_PROG_DONE, gain=0.9, pan=P_UI)
    Q.stamp(SX, TL.T_STAMP, gain=1.0, pan=P_UI, big=True, chord=('F1', 'F2', 'C3', 'A3'))
    Q.sparkle(SX, TL.T_STAMP + 0.05, 0.6, 0.02, P_UI, seed=5)
    Q.paper_flip(SX, TL.T_CMT_SHOW - 0.05, gain=0.08, pan=P_UI)
    Q.window_close(SX, TL.T_FORM_CLOSE, gain=1.0, pan=P_UI)
    Q.voice_line(SX, '哇！', TL.T_WOW, 10, gain=0.055, shift=4, seed=2, pan=P_CL)
    Q.jump(SX, TL.T_HOP, gain=1.0, pan=P_CL)
    Q.soft_land(SX, TL.T_HOP + 0.40, size=0.4, gain=0.8, pan=P_CL)
    Q.jump(SX, TL.T_HOP2, gain=0.7, pan=P_CL, f0=440, f1=1320, d=0.11)
    Q.soft_land(SX, TL.T_HOP2 + 0.32, size=0.3, gain=0.6, pan=P_CL, seed=2)
    Q.sparkle(SX, TL.T_HOP, 0.6, 0.025, P_CL, seed=8)
    Q.window_open(SX, TL.T_OFF, gain=0.9, pan=P_UI)
    for k, (p0, p1, txt) in enumerate(TL.PROGS):
        Q.progress_ticks(SX, p0, p1, rate=7.0, gain=0.9, pan=P_UI, seed=10 * k)
        Q.progress_done(SX, p1, gain=1.0, pan=P_UI, k=k)
    Q.chat_in(SX, TL.T_IGNORE, gain=0.04, pan=-0.7, k=1)
    Q.window_close(SX, TL.T_OFF_CLOSE, gain=1.0, pan=P_UI)
    Q.chat_in(SX, TL.T_PING2, gain=0.045, pan=-0.7, k=0)
    Q.auto_reply(SX, ''.join(TL.AUTO_TXT), TL.T_AUTO, gain=0.022, pan=-0.6)
    Q.status_flip(SX, TL.T_STATUS, gain=1.0, pan=0.5)
    Q.crt_off(SX, TL.T_CRT0, gain=1.0, pan=0.0)
    Q.key(SX, TL.T_MON0, gain=0.07, pan=-0.3)
    Q.switch_click(SX, TL.T_LAMP, gain=1.0, pan=0.15)
    # Theme B full: 3 bars (drums out when he starts shutting down), then a ringing Fmaj7 that fades with the lamp
    bars = 3; tend = GS.bar(bars)
    M.theme_b(SM, GS, 0, bars, layers=('keys', 'bass', 'melody'), gain=1.0, ring_last=False, t_max=tend)
    M.lazy_drums(SM, GS, 0, bars, gain=0.9, ring_last=False, t_max=TL.T_OFF_CLOSE)
    M.keys_comp(SM, GS, [CH_B[0]], bars, 1, gain=0.05, ring_last=True)
    M.soft_bass(SM, GS, [CH_B[0]], bars, 1, gain=0.13, ring_last=True)
    SM.add(Z.music_box(Z.nf('A5'), 2.4, 1.0), tend + 0.02, 0.06, pan=0.15)
    SM.add(Z.music_box(Z.nf('C6'), 3.0, 1.0), TL.T_DARK0 + 0.1, 0.05, pan=0.15)

    # ================================================================ mix
    fm_cut = MS.cut(MS.wet(FM, 1.4, 0.28, 1), TL.T_CLICK + 0.02, fade=0.05)            # music stops on the click
    f = fm_cut + MS.cut(MS.wet(FX, 0.6, 0.15, 2), TL.T_W, fade=0.01) + MS.wet(FV, 0.45, 0.15, 3)
    w = MS.wet(WM, 1.6, 0.3, 4) + MS.wet(WX, 0.6, 0.15, 5)
    w[:ns(TL.T_W)] = 0
    w = MS.fade(w, TL.T_S + 0.3, TL.T_S + 1.2, curve=1.2)
    s = MS.wet(SM, 1.6, 0.28, 6) + MS.wet(SX, 0.6, 0.15, 7)
    s[:ns(TL.T_S)] = 0
    s = MS.fade(s, TL.T_LAMP + 0.1, DUR - 0.2, curve=1.6)
    amb = MS.fade(AMB.x.copy(), TL.T_DARK0, DUR, curve=1.2)
    mix = (f + w + s + amb)[:ns(DUR)].copy()
    mix = MS.fade(mix, DUR - 0.4, DUR)
    y = MS.finalize(mix, target_lufs=-16.5, verbose=verbose)
    if verbose:
        MS.report(y, [(0, 2.45, 'opening'), (2.45, 13.95, 'form'), (13.95, 19.6, 'hesitate'), (19.6, 21.4, 'submit'),
                      (21.4, 27.4, 'Wang'), (27.4, 34.2, 'smile/approve'), (34.2, 38.6, 'stamp/hop'),
                      (38.6, 44.15, 'offline'), (44.15, 47.0, 'shutdown')])
    return y


if __name__ == '__main__':
    y = build()
    MS.write_wav(OUT, y)
    print('wrote', OUT, f'{len(y) / Z.SR:.3f}s')
