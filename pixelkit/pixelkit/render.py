"""pixelkit.render - parallel frame renderer -> one ffmpeg H.264 stream (+ audio mux).

    python3 -m pixelkit.render /path/scene.py:make --dur 10.5 --audio a.wav --out film.mp4
    python3 -m pixelkit.render /path/scene.py:make --dur 10.5 --out preview.mp4 --kw '{"OW": 960, "OH": 540}' --crf 20

The factory (module.py:function) must return an object with .frame(t) -> float RGB (0..1) or uint8 RGB,
shape (OH, OW, 3), and must be STATELESS in t (frames are rendered out of order by several workers).
Workers render frames in parallel; the main process feeds them, in order, to a single libx264 encoder,
so the output is one consistent stream (no chunk seams).
"""
import argparse, importlib, importlib.util, json, os, subprocess, sys, time
import multiprocessing as mp
import numpy as np

_scene = None
_fps = 30.0
_t0 = 0.0


def load_factory(spec):
    path, fn = spec.rsplit(':', 1)
    if path.endswith('.py'):
        d = os.path.dirname(os.path.abspath(path))
        if d not in sys.path: sys.path.insert(0, d)
        name = os.path.splitext(os.path.basename(path))[0]
        if name in sys.modules:
            mod = sys.modules[name]
        else:
            sp = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(sp); sys.modules[name] = mod; sp.loader.exec_module(mod)
    else:
        mod = importlib.import_module(path)
    return getattr(mod, fn)


def _init(spec, kw, fps, t0):
    global _scene, _fps, _t0
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    _scene = load_factory(spec)(**kw); _fps = fps; _t0 = t0


def _frame(i):
    img = _scene.frame(_t0 + i / _fps)
    if img.dtype != np.uint8: img = np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return i, np.ascontiguousarray(img[..., :3]).tobytes(), img.shape[1], img.shape[0]


def _bounded(pool, idx, max_inflight=8):
    """ordered results with at most max_inflight frames queued (v0.9).  pool.imap() submits EVERYTHING up front:
    when frames are cheaper than the x264 encoder (e.g. the credits stage), finished 1080p frames pile up in the main
    process until the OOM killer takes it (ACT V credits: died at frame 1185 with a broken pipe)."""
    from collections import deque
    q = deque(); it = iter(idx)
    for i in it:
        q.append(pool.apply_async(_frame, (i,)))
        if len(q) >= max_inflight: break
    while q:
        r = q.popleft().get()
        nxt = next(it, None)
        if nxt is not None: q.append(pool.apply_async(_frame, (nxt,)))
        yield r


def render(spec, out, dur, fps=30, audio=None, workers=None, crf=16, preset='slow', kw=None, t0=0.0,
           frames=None, abitrate='256k', log_every=15):
    kw = kw or {}
    n_total = int(round(dur * fps))
    idx = list(range(*frames)) if frames else list(range(n_total))
    workers = workers or max(1, (os.cpu_count() or 2))
    tmp = out + '.video.mp4' if audio else out
    t_start = time.time()
    ctx = mp.get_context('fork' if 'fork' in mp.get_all_start_methods() else 'spawn')   # Windows: spawn
    enc = None
    with ctx.Pool(workers, initializer=_init, initargs=(spec, kw, fps, t0)) as pool:
        done = 0
        for i, buf, w, h in _bounded(pool, idx, max_inflight=max(4, workers * 4)):
            if enc is None:
                cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                       '-s', f'{w}x{h}', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', preset, '-crf', str(crf),
                       '-tune', 'animation', '-pix_fmt', 'yuv420p', '-g', str(int(fps * 2)), '-movflags', '+faststart', tmp]
                enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            enc.stdin.write(buf); done += 1
            if done % log_every == 0 or done == len(idx):
                el = time.time() - t_start
                print(f'[render] {done}/{len(idx)} frames  {el:6.1f}s  eta {el / done * (len(idx) - done):6.1f}s', flush=True)
    enc.stdin.close(); enc.wait()
    if audio:
        a0 = idx[0] / fps
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', tmp, '-ss', f'{a0:.4f}', '-i', audio,
               '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', abitrate, '-shortest',
               '-movflags', '+faststart', out]
        subprocess.run(cmd, check=True); os.remove(tmp)
    print(f'[render] wrote {out} in {time.time() - t_start:.1f}s', flush=True)
    return out


def patch(spec, src, out, ranges, audio=None, workers=2, crf=15, preset='slow', kw=None, fps=30, abitrate='256k'):
    """re-render only some frame ranges of an already rendered video (e.g. a box that opened 1 frame early) and splice
    them in: decode src -> replace frames -> re-encode (one extra generation, crf 15) -> mux audio.  ranges: [(a, b), ...]
    CLI: python3 -m pixelkit.render SPEC --patch SRC --frames-list 688:702,2983:2997 --out OUT --audio WAV --dur D"""
    idx = sorted({i for (a, b) in ranges for i in range(a, b)})
    t_start = time.time()
    ctx = mp.get_context('fork' if 'fork' in mp.get_all_start_methods() else 'spawn'); new = {}   # Windows: spawn
    with ctx.Pool(workers, initializer=_init, initargs=(spec, kw or {}, fps, 0.0)) as pool:
        for i, buf, w, h in pool.imap(_frame, idx, chunksize=1): new[i] = buf
    print(f'[patch] rendered {len(idx)} frames in {time.time() - t_start:.1f}s', flush=True)
    pr = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                         '-of', 'csv=p=0', src], capture_output=True, text=True, check=True)
    w, h = (int(x) for x in pr.stdout.strip().split(','))
    fsz = w * h * 3
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    tmp = out + '.video.mp4'
    enc = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                            '-s', f'{w}x{h}', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', preset, '-crf', str(crf),
                            '-tune', 'animation', '-pix_fmt', 'yuv420p', '-g', str(int(fps * 2)), '-movflags', '+faststart', tmp],
                           stdin=subprocess.PIPE)
    i = 0
    while True:
        buf = dec.stdout.read(fsz)
        if len(buf) < fsz: break
        enc.stdin.write(new.get(i, buf)); i += 1
    enc.stdin.close(); enc.wait(); dec.wait()
    src_a = audio or src
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', tmp, '-i', src_a, '-map', '0:v', '-map', '1:a',
           '-c:v', 'copy', '-c:a', 'aac' if audio else 'copy'] + (['-b:a', abitrate] if audio else []) + \
          ['-shortest', '-movflags', '+faststart', out]
    subprocess.run(cmd, check=True); os.remove(tmp)
    print(f'[patch] wrote {out} ({i} frames, {len(idx)} replaced) in {time.time() - t_start:.1f}s', flush=True)
    return out


def stills(spec, times, outdir=os.path.join(os.getcwd(), '_work'), kw=None, prefix='s_'):
    """render single frames (PNG) at the given times -> list of paths."""
    import cv2
    _init(spec, kw or {}, 30.0, 0.0)
    paths = []
    for t in times:
        img = _scene.frame(float(t))
        if img.dtype != np.uint8: img = np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)
        pth = os.path.join(outdir, f'{prefix}{float(t):.2f}.png'); cv2.imwrite(pth, img[..., ::-1]); paths.append(pth)
    return paths


def contact_sheet(paths, out, cols=3, width=640, labels=True):
    """tile PNGs into one review image (labels = file stem)."""
    import cv2
    ims = []
    for pth in paths:
        im = cv2.imread(pth); h = int(round(im.shape[0] * width / im.shape[1]))
        im = cv2.resize(im, (width, h), interpolation=cv2.INTER_AREA)
        if labels:
            lab = os.path.splitext(os.path.basename(pth))[0]
            cv2.putText(im, lab, (8, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(im, lab, (8, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 230, 255), 2, cv2.LINE_AA)
        ims.append(im)
    rows = []
    for r in range(0, len(ims), cols):
        row = ims[r:r + cols]
        while len(row) < cols: row.append(np.zeros_like(ims[0]))
        rows.append(np.hstack(row))
    cv2.imwrite(out, np.vstack(rows)); return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('--out', required=True); ap.add_argument('--dur', type=float, required=True)
    ap.add_argument('--fps', type=float, default=30); ap.add_argument('--audio'); ap.add_argument('--workers', type=int)
    ap.add_argument('--crf', type=int, default=16); ap.add_argument('--preset', default='slow')
    ap.add_argument('--kw', default='{}'); ap.add_argument('--frames', help='a:b frame range (preview a section)')
    ap.add_argument('--patch', help='existing video: re-render only --frames-list ranges and splice them in')
    ap.add_argument('--frames-list', help='a:b,c:d ranges for --patch')
    a = ap.parse_args()
    if a.patch:
        rr = [tuple(int(x) for x in r.split(':')) for r in a.frames_list.split(',')]
        patch(a.spec, a.patch, a.out, rr, a.audio, a.workers or 2, kw=json.loads(a.kw), fps=a.fps); return
    fr = tuple(int(x) for x in a.frames.split(':')) if a.frames else None
    render(a.spec, a.out, a.dur, a.fps, a.audio, a.workers, a.crf, a.preset, json.loads(a.kw), frames=fr)


if __name__ == '__main__':
    main()
