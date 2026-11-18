"""pixelkit.pfx - use the 244 pixelfx effects (工具包/vendor/pixelfx, MIT) inside pixelkit scenes.

pixelfx effects are JS; we bake each one (with its options) once to a transparent sprite sheet via
`node tools/render.mjs <id> --sheet`, cache it under assets/fx_cache/, and play it back as a pure function of time
(stateless => safe for pixelkit's multi-process, out-of-order rendering).

    from pixelkit import pfx
    pop = pfx.FX('ui/confetti')                                  # bake on first use (needs Node 18+), then cached
    boom = pfx.FX('explosions/cartoon-pow', palette=['#2a1715', '#c0392b', '#f39c12', '#fff3c4'], seed=3)
    pop.draw(ui_canvas, t - T_POP, x=240, y=200)                 # x, y = where the effect's pivot (e.g. its feet) lands
    pop.draw(stage_rgba, t - T_POP, 160, 150, scale=1, flip=True, alpha=0.9)
    pop.duration, pop.fps, pop.loop                              # timing for audio cues / edit tables
    pfx.find('coin')                                              # search the catalogue (id, loop, duration, size, description)

Canvas targets: a pixelkit core.Canvas (480x270 UI layer), a Stage/RGBA uint8 array, or an RGB float image.
Scale is integer nearest-neighbour so effect pixels stay on the target grid: author at the target's resolution
(UI canvas 480x270, pixstage 320x180) and use scale=1; scale=2 only for deliberately chunky hero effects.
"""
import os, json, hashlib, subprocess, functools, shutil
import numpy as np

KIT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
PIXELFX = os.environ.get('PIXELFX_DIR') or os.path.normpath(os.path.join(KIT, '..', 'vendor', 'pixelfx'))
CACHE = os.path.join(KIT, 'assets', 'fx_cache')


def _node():
    exe = shutil.which('node')
    if not exe:
        raise RuntimeError('pixelkit.pfx needs Node.js 18+ on PATH to bake effects (cached sheets work without it)')
    return exe


def find(*words):
    """search the pixelfx catalogue -> printed list (id, loop/once, duration, size, description)."""
    r = subprocess.run([_node(), 'tools/list.mjs', *words], cwd=PIXELFX, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    print(r.stdout.strip() or r.stderr.strip())


def _bake(fx_id, opts, seed, fps):
    key = json.dumps(dict(id=fx_id, opts=opts or {}, seed=seed, fps=fps), sort_keys=True)
    h = hashlib.sha1(key.encode()).hexdigest()[:10]
    d = os.path.join(CACHE, fx_id.replace('/', '__') + '__' + h)
    name = fx_id.split('/')[-1]
    png, js = os.path.join(d, name + '.png'), os.path.join(d, name + '.json')
    if os.path.exists(png) and os.path.exists(js):
        return png, js
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f'_render_{os.getpid()}')          # per-process: parallel renders may bake the same fx at once
    cmd = [_node(), 'tools/render.mjs', fx_id, '--sheet', '--out', tmp]
    if opts: cmd += ['--opts', json.dumps(opts)]
    if seed is not None: cmd += ['--seed', str(seed)]
    if fps: cmd += ['--fps', str(fps)]
    r = subprocess.run(cmd, cwd=PIXELFX, capture_output=True, text=True, encoding='utf-8', errors='replace')
    src = os.path.join(tmp, *fx_id.split('/'))
    if os.path.exists(png) and os.path.exists(js):                # another process finished first
        shutil.rmtree(tmp, ignore_errors=True); return png, js
    if r.returncode or not os.path.exists(os.path.join(src, name + '.png')):
        raise RuntimeError(f'pixelfx bake failed for {fx_id}: {r.stderr.strip() or r.stdout.strip()}')
    for f in ('contact.png', name + '.png', name + '.json'):     # json last: png+json present == complete
        if os.path.exists(os.path.join(src, f)):
            try: os.replace(os.path.join(src, f), os.path.join(d, f))
            except OSError: pass
    with open(os.path.join(d, 'bake.json'), 'w', encoding='utf-8') as fp:
        fp.write(key)
    shutil.rmtree(tmp, ignore_errors=True)
    return png, js


@functools.lru_cache(maxsize=64)
def _load(png, js):
    from PIL import Image
    sheet = np.array(Image.open(png).convert('RGBA'))
    meta = json.load(open(js, encoding='utf-8'))
    frames = meta['frames']
    frames = list(frames.values()) if isinstance(frames, dict) else frames
    tiles = [sheet[f['frame']['y']:f['frame']['y'] + f['frame']['h'], f['frame']['x']:f['frame']['x'] + f['frame']['w']]
             for f in frames]
    return tiles, meta['meta']['pixelfx']


def _over(dst, src, x, y):
    """straight-alpha 'over' of uint8 RGBA src onto uint8 RGBA (or float RGB) dst at integer x, y."""
    sh, sw = src.shape[:2]; H, W = dst.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + sw), min(H, y + sh)
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32) / 255.0
    sa = s[..., 3:4]
    if not sa.any():
        return
    d = dst[y0:y1, x0:x1]
    if dst.dtype == np.uint8 and dst.shape[2] == 4:
        df = d.astype(np.float32) / 255.0
        da = df[..., 3:4]
        oa = sa + da * (1 - sa)
        rgb = (s[..., :3] * sa + df[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)
        d[:] = (np.concatenate([rgb, oa], -1) * 255 + 0.5).astype(np.uint8)
    else:                                   # float RGB in 0..1 (or uint8 RGB)
        scale = 255.0 if dst.dtype == np.uint8 else 1.0
        df = d.astype(np.float32) / scale
        out = s[..., :3] * sa + df * (1 - sa)
        d[:] = (out * scale + (0.5 if scale > 1 else 0)).astype(dst.dtype)


class FX:
    def __init__(self, fx_id, opts=None, palette=None, seed=None, fps=None):
        opts = dict(opts or {})
        if palette:
            opts['palette'] = list(palette)
        self.id = fx_id
        self.png, self.json = _bake(fx_id, opts or None, seed, fps)
        tiles, m = _load(self.png, self.json)
        self.fps = float(m.get('fps', 30)); self.loop = bool(m.get('loop', False))
        self.n = len(tiles); self.duration = self.n / self.fps
        self.size = tuple(m.get('frameSize', tiles[0].shape[1::-1])); self.pivot = tuple(m.get('pivot', (0, 0)))
        self.act = m.get('act')

    def frame(self, t):
        """RGBA uint8 tile for local time t (seconds since the effect started); None before start / after a one-shot."""
        tiles, _ = _load(self.png, self.json)
        if t < 0:
            return None
        i = int(t * self.fps)
        if self.loop:
            i %= self.n
        elif i >= self.n:
            return None
        return tiles[i]

    def draw(self, target, t, x, y, scale=1, flip=False, alpha=1.0):
        """composite at local time t with the pivot at (x, y). target: core.Canvas, RGBA uint8, or RGB array."""
        f = self.frame(t)
        if f is None or alpha <= 0:
            return False
        px, py = self.pivot
        if flip:
            f = f[:, ::-1]; px = f.shape[1] - 1 - px
        if scale != 1:
            k = int(round(scale))
            f = np.repeat(np.repeat(f, k, 0), k, 1); px *= k; py *= k
        if alpha < 1:
            f = f.copy(); f[..., 3] = (f[..., 3].astype(np.float32) * alpha).astype(np.uint8)
        arr = target.a if hasattr(target, 'a') and isinstance(getattr(target, 'a'), np.ndarray) else target
        _over(arr, f, int(round(x - px)), int(round(y - py)))
        return True
