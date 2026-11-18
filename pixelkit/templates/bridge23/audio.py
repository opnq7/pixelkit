"""BRIDGE II -> III · 时间跳过 (3.0 s) - sound.  python3 audio.py -> out/bridge23_audio.wav
Act II's slow clock carries in; the minute roll = accelerating digit ticks (thinned, see TL.tick_times);
08:00 lands on a tock + soft sparkle; a first bird and a breath of morning air pre-lap Act III.  No music."""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/bridge23'))
import numpy as np
from pixelkit.audio import synth as Z, cues as Q, master as MS
from pixelkit.audio.synth import ns
import timeline as TL

DUR = TL.DUR
OUT = (_PROJ + '/out/bridge23_audio.wav')

def build(verbose=True):
    FX, AMB = Z.Bus(DUR), Z.Bus(DUR)
    Q.room_tone(AMB, 0.0, TL.T_ROLL1, fade=0.3)
    Q.clock_ticks(FX, 0.0, TL.T_ROLL0 + 0.05, period=0.5, gain=0.045)
    Q.digit_ticks(FX, TL.tick_times(), gain=0.016)
    Q.tock(FX, TL.T_ROLL1, gain=0.9)
    Q.sparkle(FX, TL.T_ROLL1 + 0.02, d=0.45, gain=0.014, seed=3)
    Q.birds(AMB, TL.T_BIRD, DUR + 1.0, rate=1.6, gain=0.012, seed=23)
    Q.wind(AMB, TL.T_BIRD - 0.2, DUR + 1.0, gain=0.010, fade=0.6)
    mix = (MS.wet(FX, 1.2, 0.22, 2) + AMB.x)[:ns(DUR)].copy()
    return MS.finalize(mix, target_lufs=-20.0, verbose=verbose)

if __name__ == '__main__':
    y = build(); MS.write_wav(OUT, y); print('wrote', OUT, f'{len(y) / Z.SR:.3f}s')
