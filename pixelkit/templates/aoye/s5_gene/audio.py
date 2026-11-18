"""第 5 关声音（1971 果蝇 → 分子时钟）。 python3 audio.py -> out/s5_audio.wav"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, _PROJ); sys.path.insert(0, (_PROJ + '/s5_gene'))
import numpy as np
import timeline as TL
from pixelkit.audio import synth as Z, cues as Q, master as MS
from pixelkit.audio.synth import ns, nf
from common import OUT
import importlib.util
spec = importlib.util.spec_from_file_location('a0', (_PROJ + '/s0_open/audio.py')); A0 = importlib.util.module_from_spec(spec); spec.loader.exec_module(A0)

DUR = TL.DUR + 0.6

def build(verbose=True):
    B = lambda: Z.Bus(DUR)
    MU, SX, VB, AMB = B(), B(), B(), B()
    # dusk lab: warm folk-ish pluck + music box (F major, 90 bpm)
    Q.room_tone(AMB, 0.0, TL.S_FAC, hum=0.005, air=0.008, fade=0.4)
    b = 60 / 90
    prog = [('F2', 'A3', 'C4', 'F4'), ('D2', 'A3', 'D4', 'F4'), ('A#1', 'A#3', 'D4', 'F4'), ('C2', 'G3', 'C4', 'E4')]
    def folk(t0, t1, g=1.0, box=True):
        k = 0
        while t0 + k * b / 2 < t1:
            tt = t0 + k * b / 2
            ch = prog[(k // 8) % 4]
            if k % 4 == 0: MU.add(Z.pluck(nf(ch[0]), 1.4, 0.8, 0.4, k), tt, 0.10 * g)
            MU.add(Z.pluck(nf(ch[1 + k % 3]), 0.8, 0.6, 0.6, k + 7), tt, 0.035 * g, 0.2 * ((k % 2) * 2 - 1))
            if box and k % 4 == 2: MU.add(Z.music_box(nf(['C5', 'A4', 'F5', 'E5'][(k // 8) % 4]), 1.0, 0.7), tt, 0.04 * g, 0.2)
            k += 1
    folk(0.3, TL.S_LEAVE)
    # buzzing flies
    for q in range(3):
        n = ns(1.2); x = Z.osc('saw', 220 + q * 30, 1.2) * (0.5 + 0.5 * np.sin(np.arange(n) / 44100 * 2 * np.pi * (6 + q)))
        SX.add(Z.fft_filter(x, lo=150, hi=1200), 0.6 + q * 1.4, 0.006, 0.4)
    Q.whoosh(SX, TL.T_POSSESS, d=0.45, gain=0.12, f0=500, f1=4000, seed=5)
    Q.impact(SX, TL.T_HIT, gain=0.55); Q.big_ding(SX, TL.T_HIT + 0.02, gain=0.35); Q.ui_slide(SX, TL.T_CARD, gain=0.04, pan=-0.6)
    Q.snore(SX, TL.S_FLY + 0.3, gain=0.25, whistle=True)
    # chalk + census ticks
    for q in range(10): Q.clack(SX, TL.T_THINK + q * 0.12, size=0.12, gain=0.10, seed=q)
    Q.progress_ticks(SX, TL.T_GRID, TL.S_WEIRD - 0.2, rate=9, gain=0.5)
    # weird flies: character-select stingers
    for i, tw in enumerate((TL.T_W1, TL.T_W2, TL.T_W3)):
        Q.pop(SX, tw, gain=0.1); SX.add(Z.chip_note(nf(['E5', 'C5', 'F#5'][i]), 0.2, 'pulse', 0.25), tw + 0.03, 0.05)
    SX.add(Z.glide_tone(400, 1600, 0.25, 'pulse', 0.4), TL.T_W1 + 0.1, 0.02)
    SX.add(Z.glide_tone(400, 150, 0.6, 'sine', 1.0), TL.T_W2 + 0.1, 0.04)
    Q.dizzy(SX, TL.T_W3 + 0.1, d=0.6, gain=0.4)
    # the gene: arrows converge, name, item get
    Q.whoosh(SX, TL.T_ARROWS, d=0.9, gain=0.06, f0=500, f1=2500)
    for q in range(6): SX.add(Z.blip(nf(['C5', 'D5', 'E5', 'G5', 'A5', 'C6'][q]), 0.05, 'pulse', 0.3), TL.T_NAME + q * 0.09, 0.04)
    Q.fanfare(SX, TL.T_ITEM, gain=0.55)
    # he leaves: music drops to a lone piano, door, light switch
    for i, n in enumerate(['A4', 'F4', 'C4', 'D4', 'A3', 'C4']):
        MU.add(Z.piano(nf(n), 1.6, 0.5, 0.6, i), TL.S_LEAVE + 0.3 + i * 0.75, 0.06)
    Q.creak(SX, TL.T_WALK + 1.8, gain=0.04); Q.switch_click(SX, TL.T_LIGHT_OFF, gain=0.5)
    # nobel: applause + brass-ish chip fanfare
    Q.claps(SX, TL.T_MEDAL - 0.2, TL.S_FAC - 0.2, rate=22, gain=0.02)
    Q.fanfare(SX, TL.T_MEDAL, gain=0.6); Q.shimmer(SX, TL.T_MEDAL, 1.4, gain=0.3)
    Q.tension_pad(MU, TL.S_NOBEL, TL.S_FAC - TL.S_NOBEL, gain=0.05, notes=('F3', 'C4', 'A4', 'E5'))
    # factory: clockwork groove (C major, 110 bpm) with a ticking clock; stops when the switch is pulled
    bb = 60 / 110
    k = 0
    while TL.S_FAC + k * bb / 2 < TL.S_ALL:
        tt = TL.S_FAC + k * bb / 2
        off = TL.T_OFF <= tt < TL.T_ON
        if k % 2 == 0: Q.tock(SX, tt, gain=0.25 if not off else 0.08, k=k)
        if not off:
            if k % 2 == 0: MU.add(Z.chip_note(nf(['C3', 'C3', 'G2', 'A2'][(k // 8) % 4]), bb * 0.45, 'tri'), tt, 0.10)
            if k % 4 == 0: MU.add(Z.kick_chip(0.12, 130, 50, 0.5), tt, 0.10)
            if k % 2 == 1: MU.add(Z.music_box(nf(['E5', 'G5', 'C6', 'G5', 'A5', 'G5', 'E5', 'D5'][(k // 2) % 8]), 0.8, 0.6), tt, 0.035, 0.2)
        k += 1
    for i in range(14): SX.add(Z.thud(0.4, False, i, 220, 110), TL.T_PER0 - 0.6 + i * 0.45, 0.08, 0.5); Q.pop(SX, TL.T_PER0 - 0.5 + i * 0.45, gain=0.03, pan=0.5)
    Q.chat_in(SX, TL.T_TIM, gain=0.06); Q.sparkle(SX, TL.T_HANDS, d=0.5, gain=0.04)
    Q.clack(SX, TL.T_OFF, size=0.8, gain=0.7); SX.add(Z.glide_tone(300, 60, 0.8, 'saw', 0.5), TL.T_OFF + 0.05, 0.03)
    for q in range(10): SX.add(Z.glide_tone(1800, 900, 0.15, 'sine', 1.0), TL.T_SUN + 0.2 + q * 0.12, 0.012, (q % 2) - 0.5)
    Q.clack(SX, TL.T_ON, size=0.8, gain=0.7); SX.add(Z.glide_tone(60, 300, 0.5, 'saw', 0.5), TL.T_ON + 0.05, 0.03)
    Q.line_clear(SX, TL.T_LOOP + 1.8, gain=0.5)
    # every cell; the phone scrambles them
    Q.whoosh(SX, TL.T_ZOOMOUT, d=1.6, gain=0.07, f0=2000, f1=300); Q.shimmer(SX, TL.T_ZOOMOUT + 0.3, 1.5, gain=0.3)
    n = ns(TL.S_HUB - TL.T_CHAOS); glitch = Z.fft_filter(Z.noise(TL.S_HUB - TL.T_CHAOS, 3), lo=800, hi=6000) * (np.sin(np.arange(n) / 44100 * 2 * np.pi * 13) > 0.3)
    SX.add(glitch, TL.T_CHAOS, 0.04); Q.error_buzz(SX, TL.T_CHAOS, gain=0.4)
    for q in range(12): Q.tock(SX, TL.T_CHAOS + q * 0.17 + 0.05 * (q % 3), gain=0.2, k=q)
    # final hub: 100%
    Q.shimmer(SX, TL.S_HUB, 1.4, gain=0.45); Q.result_ding(SX, TL.T_CLEAR, gain=0.8)
    Q.fanfare(SX, TL.T_CLEAR + 0.2, gain=0.6); Q.big_ding(SX, TL.T_FULL + 0.3, gain=0.6)
    Q.title_sting(MU, TL.T_FULL + 0.3, gain=0.8) if hasattr(Q, 'title_sting') else None
    Q.riser(SX, TL.T_GO, TL.END, gain=0.10, f0=300, f1=8000)
    A0.vo_track(VB, TL.L)
    nn = MU.x.shape[0]; duck = A0.duck_env(TL.L, nn, depth=0.5)
    mix = MS.wet(MU, 1.3, 0.25, 1) * duck + MS.wet(SX, 0.9, 0.2, 2) + MS.wet(VB, 0.35, 0.06, 3) * 1.25 + AMB.x
    return MS.finalize(mix[:ns(DUR)].copy(), target_lufs=-16.5, verbose=verbose)

if __name__ == '__main__':
    y = build(); MS.write_wav(OUT + '/s5_audio.wav', y); print('ok', len(y) / Z.SR)
