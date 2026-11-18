"""pixelkit.assemble - cut a film together from finished acts with an EDL (v0.12).

    from pixelkit.assemble import Clip, Black, assemble
    edl = [Clip('act1.mp4'),
           Black(0.6, sound=ticks, lead=1.4),               # sound may start `lead` s before the black
           Clip('act2.mp4'),
           Clip('act4.mp4', t_in=0.5, t_out=116.3, tail=1.6),  # skip its fade-in, cut before its fade-out,
           Clip('act5.mp4')]                                   # ...and let 1.6 s of its sound ring under act5
    assemble(edl, 'full.mp4', target_lufs=-16.5)

Picture: every segment is trimmed frame-exactly (t * fps rounded) and encoded on its own with the render settings
(x264 slow / crf 16 / tune animation / yuv420p) into <out>.parts/, then stream-copy concatenated (+faststart)
(one big multi-input graph got OOM-killed on 4 GB).  reuse_parts=True keeps already-encoded parts.  Black = a generated black clip.
Sound: each clip's own (already mastered) audio is decoded and placed on one float timeline:
    pre  - start the clip's sound `pre` s early (it pre-laps the previous segment);
    tail - keep `tail` s of the clip's sound after t_out (it rings under the next segment);
    hard edges get a 6 ms de-click fade, tails / pre-laps a raised-cosine fade over `xfade` s.
Then ONE gain for the whole film to `target_lufs` (relative levels between acts are kept; nothing is re-compressed)
and a soft clip only if the true peak exceeds `ceiling_db`.  Returns a list of (label, start, end) for vqa --cuts.
"""
import os, subprocess, json, tempfile
import numpy as np
from .audio.synth import SR, Bus
from .audio import master as MS


class Clip:
    def __init__(self, path, t_in=0.0, t_out=None, pre=0.0, tail=0.0, gain_db=0.0, label=None, xfade=0.25):
        self.path, self.t_in, self.t_out, self.pre, self.tail = path, t_in, t_out, pre, tail
        self.gain_db, self.label, self.xfade = gain_db, label or os.path.basename(path), xfade


class Black:
    """`sound(bus)` writes cues into a Bus whose t=0 is `lead` s BEFORE the black starts (bus length dur+lead+2)."""
    def __init__(self, dur, sound=None, lead=0.0, label='black'):
        self.dur, self.sound, self.lead, self.label = dur, sound, lead, label


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height,r_frame_rate',
                        '-of', 'json', path], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = [s for s in j['streams'] if s['codec_type'] == 'video'][0]
    return float(j['format']['duration']), v['width'], v['height'], any(s['codec_type'] == 'audio' for s in j['streams'])


def load_audio(path):
    """decode a file's audio to float32 (n, 2) @ SR."""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).astype(np.float64)


def _edge(x, n_in, n_out):
    x = x.copy()
    if n_in > 0: x[:n_in] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n_in)))[:, None]
    if n_out > 0: x[len(x) - n_out:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, n_out)))[:, None]
    return x


def limit(x, ceiling_db=-1.0, knee_db=6.0):
    """soft-knee peak limiter: |x| below (ceiling - knee) passes unchanged, above it bends smoothly to the ceiling."""
    c = 10 ** (ceiling_db / 20); k = c * 10 ** (-knee_db / 20)
    a = np.abs(x); over = a > k
    y = x.copy()
    y[over] = np.sign(x[over]) * (k + (c - k) * np.tanh((a[over] - k) / (c - k)))
    return y


def plan(edl, fps=30):
    """resolve every segment: frames in/out and the film start time. -> list of dicts."""
    out, f = [], 0
    for it in edl:
        if isinstance(it, Clip):
            dur = probe(it.path)[0]
            fi = int(round(it.t_in * fps)); fo = int(round((it.t_out if it.t_out is not None else dur) * fps))
            fo = min(fo, int(np.floor(dur * fps + 1e-6)))
            out.append(dict(item=it, f0=f, fi=fi, fo=fo, n=fo - fi, src_dur=dur))
        else:
            n = int(round(it.dur * fps)); out.append(dict(item=it, f0=f, n=n))
        f += out[-1]['n']
    return out, f


def mix_audio(segs, n_frames, fps=30, target_lufs=-16.5, ceiling_db=-1.0, verbose=True):
    total = n_frames / fps
    mix = np.zeros((int(np.ceil((total + 0.1) * SR)), 2))
    def put(x, t):
        a = int(round(t * SR))
        if a < 0: x, a = x[-a:], 0
        L = min(len(x), len(mix) - a)
        if L > 0: mix[a:a + L] += x[:L]
    for s in segs:
        it, t0 = s['item'], s['f0'] / fps
        if isinstance(it, Clip):
            if not probe(it.path)[3]: continue
            x = load_audio(it.path) * 10 ** (it.gain_db / 20)
            a_in, a_out = it.t_in - it.pre, s['fo'] / fps + it.tail
            seg = x[max(0, int(round(a_in * SR))):int(round(a_out * SR))]
            dc = int(0.006 * SR)
            seg = _edge(seg, int(it.xfade * SR) if it.pre > 0 else (dc if it.t_in > 0 else 0),
                        int(min(it.xfade, it.tail) * SR) if it.tail > 0 else dc)
            put(seg, t0 - it.pre)
        elif it.sound is not None:
            b = Bus(it.dur + it.lead); it.sound(b); put(b.x, t0 - it.lead)
    mix = mix[:int(round(total * SR))]
    I, P = MS.lufs(mix)
    y = mix * 10 ** ((target_lufs - I) / 20)
    I2, P2 = MS.lufs(y)
    c = ceiling_db
    for _ in range(4):                       # true-peak guard: a knee limiter that leaves everything below -6 dB untouched
        if P2 is None or P2 <= ceiling_db + 0.05: break
        c -= (P2 - ceiling_db) + 0.1
        yy = limit(y, c); I2, P2 = MS.lufs(yy)
    else:
        yy = y
    y = yy if c != ceiling_db else y
    if verbose: print(f'[assemble] audio: source {I:.1f} LUFS -> {I2:.1f} LUFS, true peak {P2} dBFS')
    return y


def assemble(edl, out, fps=30, W=1920, H=1080, target_lufs=-16.5, crf=16, preset='slow', verbose=True, audio_only=False, reuse_parts=False):
    segs, n = plan(edl, fps)
    if verbose:
        for s in segs: print(f"  {s['f0'] / fps:8.2f}  {s['n'] / fps:7.2f}s  {s['item'].label}")
        print(f'[assemble] {len(segs)} segments, {n} frames = {n / fps:.2f}s')
    y = mix_audio(segs, n, fps, target_lufs, verbose=verbose)
    wav = out + '.audio.wav'; MS.write_wav(wav, y)
    cuts = [(s['item'].label, s['f0'] / fps, (s['f0'] + s['n']) / fps) for s in segs]
    if audio_only: return cuts
    # picture: one encode per segment (a single 11-input filter graph gets OOM-killed on a 4 GB box), then a
    # stream-copy concat of the identical-settings parts + the mixed sound.
    norm = f'fps={fps},scale={W}:{H}:flags=neighbor,setsar=1,format=yuv420p'
    enc = ['-an', '-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-tune', 'animation', '-pix_fmt', 'yuv420p',
           '-g', '60', '-r', str(fps)]
    parts_dir = out + '.parts'; os.makedirs(parts_dir, exist_ok=True)
    parts = []
    for i, s in enumerate(segs):
        it = s['item']; part = os.path.join(parts_dir, f'{i:02d}.mp4'); parts.append(part)
        if os.path.exists(part) and reuse_parts: continue
        if isinstance(it, Clip):
            src = ['-i', it.path]; vf = f"trim=start_frame={s['fi']}:end_frame={s['fo']},setpts=PTS-STARTPTS,{norm}"
        else:
            src = ['-f', 'lavfi', '-i', f'color=c=black:s={W}x{H}:r={fps}:d={s["n"] / fps:.6f}']; vf = f"trim=end_frame={s['n']},{norm}"
        if verbose: print(f'[assemble] part {i:02d} {it.label} ({s["n"]} frames)', flush=True)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + src + ['-vf', vf] + enc + [part + '.tmp.mp4'], check=True)
        os.replace(part + '.tmp.mp4', part)
    lst = os.path.join(parts_dir, 'list.txt')
    with open(lst, 'w') as f:
        for p in parts: f.write(f"file '{p}'\n")
    args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', wav,
            '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', str(SR),
            '-movflags', '+faststart', '-shortest', out]
    subprocess.run(args, check=True)
    os.remove(wav)
    if verbose: print('[assemble] wrote', out, f'{probe(out)[0]:.2f}s')
    return cuts
