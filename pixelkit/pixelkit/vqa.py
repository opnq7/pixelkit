"""finished-video QA: one-frame pops (A-B-A) and big jumps that are NOT on a cut.

    python3 -m pixelkit.vqa out.mp4 --cuts 6.6,19.7,23.1 [--fps 30]
    (in a project: cuts = timeline.CUTS)   Box open/close and camera shakes also show up as JUMP - check them by eye."""
import argparse, subprocess, numpy as np

def scan(src, cuts=(), fps=30, W=240, H=135):
    # streamed frame by frame (v0.12): a whole film held in memory got OOM-killed on 4 GB
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-vf', f'scale={W}:{H}:flags=area,format=gray', '-f', 'rawvideo', '-'],
                         stdout=subprocess.PIPE)
    d1, d2, prev, prev2, n, sz = [], [], None, None, 0, W * H
    while True:
        b = p.stdout.read(sz)
        if len(b) < sz: break
        x = np.frombuffer(b, np.uint8).astype(np.float32)
        if prev is not None: d1.append(float(np.abs(x - prev).mean()))
        if prev2 is not None: d2.append(float(np.abs(x - prev2).mean()))
        prev2, prev, n = prev, x, n + 1
    p.wait()
    d1, d2 = np.array(d1), np.array(d2)
    cutf = {int(round(c * fps)) + d for c in cuts for d in range(-1, 3)}
    med = float(np.median(d1)); flags = []
    for i in range(1, n - 1):
        if i in cutf or (i + 1) in cutf: continue
        a, b, c = d1[i - 1], d1[i], d2[i - 1]
        if min(a, b) > max(3.0, 6 * med) and c < 0.4 * min(a, b): flags.append((i, 'POP', a, b, c))
        elif a > max(6.0, 12 * med): flags.append((i, 'JUMP', a, b, c))
    near_cut = [(i + 1, float(d1[i])) for i in range(len(d1)) if (i + 2) in cutf and (i + 1) not in cutf and d1[i] > max(6.0, 12 * med)]
    return dict(frames=n, median=med, flags=flags, pre_cut=near_cut)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('--cuts', default=''); ap.add_argument('--fps', type=float, default=30)
    a = ap.parse_args()
    cuts = [float(x) for x in a.cuts.split(',') if x]
    r = scan(a.src, cuts, a.fps)
    print(f"frames {r['frames']}  median diff {r['median']:.2f}")
    for (i, k, x, y, z) in r['flags']: print(f'{k:4s} frame {i} t={i / a.fps:.2f}  d_prev {x:.1f} d_next {y:.1f} d_skip {z:.1f}')
    for (i, d) in r['pre_cut']: print(f'PRE-CUT change at frame {i} t={i / a.fps:.2f} (diff {d:.1f}) - something pops in 1 frame before a cut?')
    print('flags', len(r['flags']))

if __name__ == '__main__': main()
