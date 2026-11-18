"""《Claude 想请一天假》 full film v1 - the approved seams (see HANDOFF §拼接).

    python3 film.py [--audio-only]   -> out/full_v1.mp4  (+ prints the --cuts list for pixelkit.vqa)

I->II     0.6 s black; two clock ticks pre-lap Act II (same tick, same level, same 1.0 s grid as Act II's own)
II->III   bridge23 (HUD 00:03 -> 08:00 in the dark)
III->IV   bridge34 (走向河边); Act IV starts at 0.8 s (its picture + HUD fade-ins skipped; the clock carries across)
IV->V     seamless: Act IV cut at T_FADE0 = 116.3 (before its fade), its last 1.6 s of sound ring under Act V;
          Act V v3.1 opens on the same frame (no fade-in)
V->egg    1.0 s black; 1.0 s black at the very end.  Whole film one gain to -16.5 LUFS.
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT)
import numpy as np
from pixelkit.assemble import Clip, Black, assemble, load_audio
from pixelkit.audio import cues as Q
from pixelkit.audio.synth import Bus, SR

O = (_PROJ + '/out/')
A = O + 'acts/'
ACT2 = A + '第二幕_v2_回炉.mp4'

def ticks_into_act2(b):
    # bus t=0 is 1.6 s before the black = Act II t -2.2 ; Act II ticks at 0, 1, 2 ... -> ours at -2, -1
    ref = load_audio(ACT2)[:int(0.12 * SR)]
    probe = Bus(1.0); Q.clock_ticks(probe, 0.0, 0.5, period=1.0, gain=0.022, pan=-0.4)
    k = np.abs(ref).max() / (np.abs(probe.x).max() + 1e-9)
    tmp = Bus(2.5); Q.clock_ticks(tmp, 0.2, 1.3, period=1.0, gain=0.022, pan=-0.4)
    b.x[:len(tmp.x)] += tmp.x[:len(b.x)] * k

EDL = [Clip(A + '第一幕_v4.1_眼泪.mp4', label='第一幕'),
       Black(0.6, sound=ticks_into_act2, lead=1.6, label='黑场+滴答'),
       Clip(ACT2, label='第二幕'),
       Clip(O + 'bridge23.mp4', label='过场 二→三'),
       Clip(O + 'act3_v2_1.mp4', label='第三幕'),
       Clip(O + 'bridge34.mp4', label='过场 三→四'),
       Clip(A + '第四幕_v2_河边.mp4', t_in=0.8, t_out=116.3, tail=1.6, label='第四幕'),
       Clip(O + 'act5_v3_1.mp4', label='第五幕'),
       Black(1.0, label='黑场'),
       Clip(A + '彩蛋_v2.mp4', label='彩蛋'),
       Black(1.0, label='黑场(尾)')]

if __name__ == '__main__':
    cuts = assemble(EDL, O + 'full_v1.mp4', target_lufs=-16.5, audio_only='--audio-only' in sys.argv,
                    reuse_parts='--reuse' in sys.argv)
    print('--cuts ' + ','.join(f'{b:.2f}' for _, b, _ in cuts[1:]))
