"""python3 stills.py s0_open 0.5,2.0,... out.png  -> 3-column sheet (960 px wide tiles)"""
import os as _os; _HERE = _os.path.dirname(_os.path.abspath(__file__)); _KIT = _os.path.normpath(_os.path.join(_HERE, '../..')); _PROJ = _os.path.normpath(_os.path.join(_HERE, '.')).replace('\\', '/'); _WORK = _os.path.normpath(_os.path.join(_HERE, '../../../../_work')).replace('\\', '/')  # portable paths (Windows/Linux)
import sys, importlib.util, numpy as np, cv2
sys.path.insert(0, _KIT)
d, times, out = sys.argv[1], [float(x) for x in sys.argv[2].split(',')], sys.argv[3]
sys.path.insert(0, f'{_PROJ}/{d}')
spec = importlib.util.spec_from_file_location('scene', f'{_PROJ}/{d}/scene.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
S = m.make()
from pixelkit import post
tiles = []
for t in times:
    img = post.to_u8(S.frame(t))[..., ::-1]
    img = cv2.resize(img, (640, 360), interpolation=cv2.INTER_AREA)
    cv2.putText(img, f'{t:.2f}', (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    tiles.append(img)
while len(tiles) % 3: tiles.append(np.zeros_like(tiles[0]))
rows = [np.concatenate(tiles[i:i + 3], 1) for i in range(0, len(tiles), 3)]
cv2.imwrite(out, np.concatenate(rows, 0)); print('wrote', out)
