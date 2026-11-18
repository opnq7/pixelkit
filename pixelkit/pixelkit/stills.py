"""quick contact sheet of any scene:  python3 -m pixelkit.stills <scene.py[:make]> <t1,t2,...> [--only a,b] [--out sheet.png]
writes every full-res frame next to the sheet (f_<t>.png) and a 3-column 640x360 contact sheet with time labels."""
import sys, os, time, argparse, importlib.util
import numpy as np, cv2
from . import post

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scene'); ap.add_argument('times')
    ap.add_argument('--only', default=None); ap.add_argument('--out', default=os.path.join('_work', 'stills', 'sheet.png'))
    a = ap.parse_args()
    path, _, fn = a.scene.partition(':'); fn = fn or 'make'
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec = importlib.util.spec_from_file_location('scene_mod', path); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    kw = {'only': a.only.split(',')} if a.only else {}
    A = getattr(m, fn)(**kw)
    od = os.path.dirname(a.out); os.makedirs(od, exist_ok=True)
    small = []
    for t in [float(x) for x in a.times.split(',')]:
        t1 = time.time(); im = post.to_u8(A.frame(t)); print(t, round(time.time() - t1, 2), flush=True)
        cv2.imwrite(os.path.join(od, f'f_{t:05.2f}.png'), im[..., ::-1])
        s = cv2.resize(im, (640, 360), interpolation=cv2.INTER_AREA)
        cv2.putText(s, f'{t:.2f}', (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2); small.append(s)
    while len(small) % 3: small.append(np.zeros_like(small[0]))
    cv2.imwrite(a.out, np.vstack([np.hstack(small[i:i + 3]) for i in range(0, len(small), 3)])[..., ::-1])
    print('wrote', a.out)

if __name__ == '__main__': main()
