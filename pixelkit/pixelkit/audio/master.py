"""pixelkit.audio.master - reverb sends, bus cuts, mastering chain, loudness, wav I/O.

    mix = wet(M, 1.5, 0.30, 1) + wet(X, 0.7, 0.22, 2)
    mix = finalize(mix, target_lufs=-16.5)      # HP 28 Hz -> glue comp -> LUFS normalise -> soft clip
    write_wav('out.wav', mix)
"""
import os, re, subprocess, tempfile, wave
import numpy as np
from . import synth as Z
from .synth import SR, ns

def arr(b): return b.x if hasattr(b, 'x') else b

def wet(bus, rt, send, seed=0, damp=5000):
    """dry + convolution-reverb send."""
    x = arr(bus)
    if send <= 0: return x.copy()
    ir = Z.make_ir(rt, seed=seed, damp=damp)
    r = Z.convolve_stereo(x, ir)[:len(x)]
    return x + r * send

def cut(x, t0, t1=None, fade=0.006):
    """hard silence from t0 (to t1) with a tiny anti-click fade."""
    x = arr(x); a = ns(t0); f = ns(fade)
    b = len(x) if t1 is None else ns(t1)
    if f > 0: x[max(0, a - f):a] *= np.linspace(1, 0, min(f, a))[:, None]
    x[a:b] = 0
    return x

def fade(x, t0, t1, curve=1.5, out=True):
    x = arr(x); t = np.arange(len(x)) / SR
    k = np.clip((t1 - t) / (t1 - t0), 0, 1) ** curve if out else np.clip((t - t0) / (t1 - t0), 0, 1) ** curve
    x *= k[:, None]; return x

def highpass(x, f=28.0):
    for c in range(x.shape[1]): x[:, c] = Z.fft_filter(x[:, c], lo=f, slope=2)
    return x

def compress(x, thr=-20.0, ratio=2.2, att=0.5, rel=0.03, blk=256):
    nb = len(x) // blk
    if nb == 0: return x
    r = np.sqrt(np.mean(x[:nb * blk].reshape(nb, blk, 2) ** 2, axis=(1, 2)) + 1e-12)
    lev = 20 * np.log10(r)
    gr = np.where(lev > thr, (lev - thr) * (1 - 1 / ratio), 0.0)
    sm = np.zeros_like(gr); acc = 0.0
    for i in range(nb):
        acc = acc + (gr[i] - acc) * (att if gr[i] > acc else rel); sm[i] = acc
    g = 10 ** (-np.repeat(sm, blk) / 20)
    g = np.concatenate([g, np.full(len(x) - len(g), g[-1])])
    return x * g[:, None]

def soft_clip(x, ceiling_db=-1.0, drive=1.15):
    c = 10 ** (ceiling_db / 20)
    return np.tanh(x * drive / c) / np.tanh(drive) * c if drive > 0 else np.clip(x, -c, c)

def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def lufs(x):
    """integrated loudness (EBU R128) + true peak via ffmpeg."""
    fd, p = tempfile.mkstemp(suffix='.wav'); os.close(fd)
    try:
        write_wav(p, x)
        r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', p, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                           capture_output=True, text=True).stderr
        I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1])
        pk = re.findall(r'Peak:\s+(-?[\d.inf]+) dBFS', r)
        return I, (float(pk[-1]) if pk else None)
    finally:
        os.remove(p)

def finalize(mix, target_lufs=-16.5, ceiling_db=-1.0, hp=28.0, thr=-20.0, ratio=2.2, verbose=True):
    """HP -> glue compressor -> loudness normalise -> soft clip (two passes for accuracy)."""
    x = highpass(mix.copy(), hp)
    x = compress(x, thr, ratio)
    pk = np.abs(x).max() + 1e-9
    x = x / pk * 0.5
    for _ in range(2):
        I, _p = lufs(soft_clip(x, ceiling_db))
        x = x * 10 ** ((target_lufs - I) / 20)
    y = soft_clip(x, ceiling_db)
    I, P = lufs(y)
    c = ceiling_db
    for _ in range(3):                       # true-peak guard: pull the clip ceiling down until TP <= ceiling_db
        if P is None or P <= ceiling_db + 0.05: break
        c -= (P - ceiling_db) + 0.15
        y = soft_clip(x, c); I, P = lufs(y)
    if verbose: print(f'[master] integrated {I:.1f} LUFS, true peak {P} dBFS (clip ceiling {c:.1f} dB)')
    return y

def report(x, sections):
    """sections: [(t0, t1, name)] -> prints RMS/peak per section."""
    for (a, b, name) in sections:
        s = x[ns(a):ns(b)]
        if len(s) == 0: continue
        print(f'{name:10s} rms {20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-9):6.1f} dB  peak {20 * np.log10(np.abs(s).max() + 1e-9):6.1f} dB')
