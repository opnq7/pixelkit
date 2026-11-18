"""《熬夜副本》全片拼接 v1。
    cd /home/claude/aoye && python3 full/film.py [--reuse] -> out/full_v1.mp4 (+ prints --cuts for pixelkit.vqa)
每关首尾本来就是「门 + 白光 / 冻结的 03:56 卧室 → hub」，直接硬接，不额外加黑场；
开场前后与片尾各留 0.0 / 1.0 s 黑场。整片一个增益到 -16.5 LUFS。
"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '..')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys
sys.path.insert(0, _KIT)
from pixelkit.assemble import Clip, Black, assemble
O = (_PROJ + '/out/')
EDL = [Clip(O + 's0_open_v2.mp4', label='开场'),
       Clip(O + 's1_cave_v3.mp4', label='第1关 山洞'),
       Clip(O + 's2_rem_v3.mp4', label='第2关 快速眼动'),
       Clip(O + 's3_awake_v3.mp4', label='第3关 264小时'),
       Clip(O + 's4_debt_v5.mp4', label='第4关 睡眠债'),
       Clip(O + 's5_gene_v3.mp4', label='第5关 分子钟'),
       Clip(O + 's6_end_v3.mp4', label='结尾'),
       Black(1.0, label='黑场(尾)')]
if __name__ == '__main__':
    cuts = assemble(EDL, O + 'full_v1.mp4', target_lufs=-16.5, reuse_parts='--reuse' in sys.argv)
    print('--cuts ' + ','.join(f'{b:.2f}' for _, b, _ in cuts[1:]))
