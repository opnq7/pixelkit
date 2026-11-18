"""BRIDGE III -> IV · 走向河边 (7.0 s) - sound.  python3 audio.py -> out/bridge34_audio.wav
Act III's street bed thins out as the afternoon passes; Claude's real-speed steps (TL.footsteps); time-lapsed
passers-by = quick swishes; a very light ticker under the HUD roll; a sparkle when it looks up at the light;
wind + birds rise toward evening; the river pre-laps the last 0.5 s.  No music."""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, importlib.util
sys.path.insert(0, _KIT); sys.path.insert(0, (_PROJ + '/bridge34'))
import numpy as np
from pixelkit.audio import synth as Z, cues as Q, master as MS
from pixelkit.audio.synth import ns
import timeline as TL

DUR = TL.DUR
OUT = (_PROJ + '/out/bridge34_audio.wav')

def build(verbose=True):
    FX, AMB = Z.Bus(DUR), Z.Bus(DUR)
    Q.morning_bed(AMB, 0.0, 5.6, gain=0.9, fade_in=0.5, fade_out=2.2, birds_rate=0.5)
    for k, t in enumerate(TL.footsteps()):
        Q.step(FX, t, gain=0.018 * min(1.0, 0.35 + t / TL.T_FADE_IN), pan=-0.05, seed=k, hard=True)
    for k, (look, x0, v, foot, prop) in enumerate(TL.EXTRAS):     # each passer-by crossing the frame centre
        tc = (TL.claude_x(0) - x0) / (v - TL.WALK_V)
        if 0.3 < tc < DUR - 0.6:
            Q.swish(FX, tc - 0.12, d=0.3, gain=0.012, pan=float(np.sign(-v)) * 0.4, seed=10 + k)
    Q.ticker(FX, TL.T_ROLL0, TL.T_ROLL1, rate0=10.0, rate1=16.0, gain=0.005)
    Q.digit_ticks(FX, [TL.T_ROLL1], gain=0.02)
    Q.sparkle(FX, TL.T_LOOK0 + 0.15, d=0.5, gain=0.012, seed=5)
    Q.wind(AMB, 2.5, DUR + 1.0, gain=0.012, fade=1.5)
    Q.birds(AMB, 4.0, DUR + 1.0, rate=0.9, gain=0.010, seed=44)
    Q.river_bed(AMB, TL.T_WATER, DUR + 1.0, gain=0.45, crickets=False, fade_in=0.45, fade_out=0.5)
    mix = (MS.wet(FX, 1.0, 0.15, 3) + AMB.x)[:ns(DUR)].copy()
    return MS.finalize(mix, target_lufs=-20.0, verbose=verbose)

if __name__ == '__main__':
    y = build(); MS.write_wav(OUT, y); print('wrote', OUT, f'{len(y) / Z.SR:.3f}s')
