"""Tiny numpy synth toolkit (48 kHz) for the film score + SFX."""
import numpy as np, math, zlib

SR = 48000
TWO_PI = 2 * np.pi

def rng(*k): return np.random.default_rng(zlib.crc32(repr(k).encode()))
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12.0)
NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
def n2m(s):
    """'C#4' -> midi"""
    s = s.strip(); p = NOTE[s[0]]; i = 1
    while i < len(s) and s[i] in '#b':
        p += 1 if s[i] == '#' else -1; i += 1
    return p + 12 * (int(s[i:]) + 1)
def nf(s): return mtof(n2m(s))

def ns(d): return int(round(d * SR))
def tvec(d): return np.arange(ns(d), dtype=np.float64) / SR

# ---------------------------------------------------------------- oscillators
def phase_of(f, n):
    if np.isscalar(f): return TWO_PI * f * np.arange(n) / SR
    return TWO_PI * np.cumsum(f) / SR

def osc(kind, f, d, duty=0.5, ph0=0.0):
    n = ns(d)
    if not np.isscalar(f): n = len(f)
    ph = phase_of(f, n) + ph0
    if kind == 'sine': return np.sin(ph)
    fr = (ph / TWO_PI) % 1.0
    if kind == 'pulse': return np.where(fr < duty, 1.0, -1.0) * 0.8
    if kind == 'saw': return (2 * fr - 1) * 0.7
    if kind == 'tri':
        return 2 * np.abs(2 * fr - 1) - 1
    if kind == 'tri4':   # NES-like stepped triangle
        tr = 2 * np.abs(2 * fr - 1) - 1
        return np.round(tr * 7.5) / 7.5
    raise ValueError(kind)

def noise(d, seed=0, rate=None):
    n = ns(d); g = rng('noise', seed)
    if rate is None: return g.uniform(-1, 1, n)
    step = max(1, int(SR / rate)); m = n // step + 2
    return np.repeat(g.choice([-1.0, 1.0], m), step)[:n]

# ---------------------------------------------------------------- envelopes
def adsr(n, a=0.005, d=0.08, s=0.6, r=0.06, gate=None):
    """gate: seconds the note is held; total length n samples (should include release)."""
    t = np.arange(n) / SR
    if gate is None: gate = n / SR - r
    e = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    rel = np.clip(1 - (t - gate) / max(r, 1e-6), 0, 1)
    e = np.where(t > gate, e * rel, e)
    return e

def expdec(n, tau, a=0.002):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-6)) * np.exp(-t / tau)

def fade_io(x, fi=0.003, fo=0.01):
    n = len(x); a = ns(fi); b = ns(fo)
    if a > 0: x[:a] *= np.linspace(0, 1, a)
    if b > 0: x[-b:] *= np.linspace(1, 0, b)
    return x

# ---------------------------------------------------------------- filters (zero-phase FFT)
def fft_filter(x, lo=None, hi=None, slope=2.0):
    n = len(x)
    if n < 16: return x
    N = 1 << int(math.ceil(math.log2(n + 64)))
    X = np.fft.rfft(x, N)
    f = np.fft.rfftfreq(N, 1 / SR)
    g = np.ones_like(f)
    if hi is not None: g *= 1 / np.sqrt(1 + (f / hi) ** (2 * slope))
    if lo is not None: g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * slope))
    return np.fft.irfft(X * g, N)[:n]

def peak_filter(x, fc, q=4.0, gain=1.0):
    """add a resonant band (zero phase)."""
    n = len(x); N = 1 << int(math.ceil(math.log2(n + 64)))
    X = np.fft.rfft(x, N); f = np.fft.rfftfreq(N, 1 / SR)
    bw = fc / q
    g = 1 + gain * np.exp(-((f - fc) / bw) ** 2)
    return np.fft.irfft(X * g, N)[:n]

def stft_filter(x, gain_fn, nfft=2048, hop=512):
    """Time-varying zero-phase-ish filter. gain_fn(t_seconds, freqs) -> gains array."""
    n = len(x)
    win = np.hanning(nfft)
    pad = np.concatenate([np.zeros(nfft), x, np.zeros(nfft)])
    out = np.zeros_like(pad); wsum = np.zeros_like(pad)
    f = np.fft.rfftfreq(nfft, 1 / SR)
    for s in range(0, len(pad) - nfft, hop):
        seg = pad[s:s + nfft] * win
        tc = (s + nfft / 2 - nfft) / SR
        S = np.fft.rfft(seg) * gain_fn(tc, f)
        out[s:s + nfft] += np.fft.irfft(S, nfft) * win
        wsum[s:s + nfft] += win ** 2
    out /= np.maximum(wsum, 1e-6)
    return out[nfft:nfft + n]

def lp_sweep(x, f0, f1, curve=1.0, q=0.0):
    d = len(x) / SR
    def g(t, f):
        u = min(max(t / d, 0), 1) ** curve
        fc = f0 * (f1 / f0) ** u
        r = 1 / np.sqrt(1 + (f / fc) ** 4)
        if q > 0: r = r * (1 + q * np.exp(-((f - fc) / (fc * 0.25)) ** 2))
        return r
    return stft_filter(x, g)

def bp_sweep(x, f0, f1, curve=1.0, width=0.6):
    d = len(x) / SR
    def g(t, f):
        u = min(max(t / d, 0), 1) ** curve
        fc = f0 * (f1 / f0) ** u
        return np.exp(-(np.log2(np.maximum(f, 1) / fc) / width) ** 2)
    return stft_filter(x, g)

# ---------------------------------------------------------------- instruments
def chip_note(f, gate, kind='pulse', duty=0.25, a=0.004, d=0.09, s=0.55, r=0.05, vib=0.0, vib_delay=0.12, slide=None):
    n = ns(gate + r) + 1
    t = np.arange(n) / SR
    ff = np.full(n, float(f))
    if vib > 0:
        ff *= 1 + vib * np.sin(TWO_PI * 5.8 * t) * np.clip((t - vib_delay) / 0.1, 0, 1)
    if slide is not None:
        ff *= 2 ** (slide * np.exp(-t / 0.025) / 12)
    y = osc(kind, ff, 0, duty)
    return y * adsr(n, a, d, s, r, gate)

def fm_epiano(f, gate, vel=1.0, bright=1.0):
    dur = gate + 0.45
    n = ns(dur); t = np.arange(n) / SR
    I = (1.8 * bright * vel) * np.exp(-t / 0.35) + 0.25
    mod = np.sin(TWO_PI * f * t + 0.3)
    y = np.sin(TWO_PI * f * t + I * mod)
    tine = np.sin(TWO_PI * f * 14.0 * t) * 0.18 * vel * np.exp(-t / 0.035)
    y = y + tine + 0.18 * np.sin(TWO_PI * f * 2 * t) * np.exp(-t / 0.6)
    amp = np.exp(-t / (1.6 if f < 400 else 1.1)) * np.minimum(1, t / 0.003)
    rel = np.clip(1 - (t - gate) / 0.4, 0, 1)
    trem = 1 + 0.06 * np.sin(TWO_PI * 4.6 * t)
    return y * amp * rel * trem * vel

def music_box(f, d=1.4, vel=1.0):
    n = ns(d); t = np.arange(n) / SR
    y = (np.sin(TWO_PI * f * t) * np.exp(-t / 0.9) + 0.35 * np.sin(TWO_PI * f * 2.0 * t + 0.4) * np.exp(-t / 0.35)
         + 0.16 * np.sin(TWO_PI * f * 5.43 * t) * np.exp(-t / 0.07) + 0.08 * np.sin(TWO_PI * f * 8.9 * t) * np.exp(-t / 0.03))
    click = noise(0.006, int(f)) * np.linspace(1, 0, ns(0.006)) * 0.25
    y[:len(click)] += click
    return y * np.minimum(1, t / 0.0015) * vel

def celesta(f, d=1.6, vel=1.0):
    n = ns(d); t = np.arange(n) / SR
    y = np.sin(TWO_PI * f * t) * np.exp(-t / 0.8) + 0.25 * np.sin(TWO_PI * f * 4.0 * t) * np.exp(-t / 0.12)
    return y * np.minimum(1, t / 0.002) * vel

def piano(f, gate=2.0, vel=0.8, bright=1.0, seed=0):
    tau0 = float(np.clip(5.5 * (110 / f) ** 0.55, 0.9, 6.0))
    dur = min(gate, tau0 * 3) + 0.35
    n = ns(dur); t = np.arange(n) / SR
    y = np.zeros(n)
    B = 0.00035
    nh = int(min(12, 9000 / f))
    for k in range(1, nh + 1):
        fk = k * f * math.sqrt(1 + B * k * k)
        ak = (1 / k ** 1.15) * (0.55 + 0.45 * vel * bright) ** (k - 1)
        tk = tau0 / (1 + 0.55 * (k - 1))
        for det in (-0.0006, 0.0006):
            y += 0.5 * ak * np.sin(TWO_PI * fk * (1 + det) * t + k * 0.7) * (np.exp(-t / tk) * 0.8 + 0.2 * np.exp(-t / (tk * 0.15)))
    ham = fft_filter(noise(0.02, seed), lo=400, hi=3000) * np.linspace(1, 0, ns(0.02)) * 0.08 * vel
    y[:len(ham)] += ham
    rel = np.clip(1 - (t - gate) / 0.3, 0, 1)
    return y * rel * np.minimum(1, t / 0.002) * vel

def bell(f, d=3.0, vel=1.0):
    n = ns(d); t = np.arange(n) / SR
    parts = [(0.5, 0.35, 2.2), (1.0, 1.0, 1.6), (1.19, 0.4, 0.9), (1.5, 0.35, 0.8), (2.0, 0.5, 0.7),
             (2.52, 0.22, 0.4), (3.01, 0.18, 0.3), (4.1, 0.08, 0.18)]
    y = np.zeros(n)
    for (r, a, tau) in parts:
        y += a * np.sin(TWO_PI * f * r * t + r) * np.exp(-t / tau)
    return y * np.minimum(1, t / 0.0015) * vel / 2.2

def kick_chip(d=0.22, f0=160, f1=48, vel=1.0):
    n = ns(d); t = np.arange(n) / SR
    ff = f1 + (f0 - f1) * np.exp(-t / 0.028)
    y = np.sin(phase_of(ff, n)) * np.exp(-t / 0.11)
    y[:ns(0.002)] += 0.4
    return y * vel

def snare_chip(d=0.18, vel=1.0, seed=0):
    n = ns(d); t = np.arange(n) / SR
    nz = noise(d, seed, rate=12000) * np.exp(-t / 0.06)
    tone = np.sin(TWO_PI * 185 * t) * np.exp(-t / 0.035) * 0.6
    return (nz * 0.7 + tone) * vel

def hat_chip(d=0.05, vel=1.0, seed=0, open_=False):
    n = ns(d); t = np.arange(n) / SR
    nz = fft_filter(noise(d, seed), lo=6000)
    return nz * np.exp(-t / (0.09 if open_ else 0.014)) * vel * 1.4

def thud(vel=1.0, big=True, seed=0, f0=95, f1=46):
    d = 0.55 if big else 0.25
    n = ns(d); t = np.arange(n) / SR
    ff = f1 + (f0 - f1) * np.exp(-t / 0.05)
    body = np.sin(phase_of(ff, n)) * np.exp(-t / (0.16 if big else 0.07))
    nz = fft_filter(noise(d, seed), lo=80, hi=900 if big else 1600) * np.exp(-t / (0.05 if big else 0.025)) * 0.9
    knock = np.sin(TWO_PI * (240 if big else 420) * t) * np.exp(-t / 0.018) * 0.5
    return (body + nz + knock) * vel

def stamp(vel=1.0, seed=0, big=False):
    d = 0.9 if big else 0.12
    n = ns(d); t = np.arange(n) / SR
    g = rng('stamp', seed)
    f0 = (110 if big else 150) * g.uniform(0.92, 1.08); f1 = 38 if big else 70
    ff = f1 + (f0 - f1) * np.exp(-t / (0.06 if big else 0.02))
    body = np.sin(phase_of(ff, n)) * np.exp(-t / (0.32 if big else 0.035))
    slap = fft_filter(noise(d, seed), lo=700, hi=4500) * np.exp(-t / (0.05 if big else 0.012)) * (1.1 if big else 0.8)
    click = np.zeros(n); click[:ns(0.0012)] = 0.6
    y = body + slap + click
    if big:
        crack = fft_filter(noise(d, seed + 99), lo=1500) * np.exp(-t / 0.012) * 0.9
        y += crack
    return y * vel

def whoosh(d=0.35, f0=300, f1=5000, vel=1.0, seed=0, curve=1.0):
    x = noise(d, seed)
    y = bp_sweep(x, f0, f1, curve, width=0.9)
    n = len(y); t = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5
    return y * env * vel * 2.0

def paper_flip(vel=1.0, seed=0, d=0.16):
    x = noise(d, seed)
    n = len(x); t = np.arange(n) / SR
    am = 0.6 + 0.4 * np.sin(TWO_PI * 38 * t + seed)
    y = fft_filter(x, lo=1200, hi=7000) * am * np.exp(-((t - d * 0.35) / (d * 0.3)) ** 2)
    return y * vel * 1.6

def key_click(vel=1.0, seed=0):
    d = 0.035; n = ns(d); t = np.arange(n) / SR
    g = rng('key', seed)
    f = g.uniform(1800, 2600)
    y = np.sin(TWO_PI * f * t) * np.exp(-t / 0.004) * 0.5
    y += fft_filter(noise(d, seed), lo=1500, hi=9000) * np.exp(-t / 0.006)
    y += np.sin(TWO_PI * g.uniform(300, 420) * t) * np.exp(-t / 0.01) * 0.4
    return y * vel

def coin(vel=1.0, f1=987.77, f2=1318.5, d1=0.07, d2=0.32, duty=0.5):
    a = chip_note(f1, d1, 'pulse', duty, a=0.001, d=0.05, s=0.9, r=0.005)
    b = chip_note(f2, d2, 'pulse', duty, a=0.001, d=0.12, s=0.35, r=0.12)
    y = np.zeros(len(a) + len(b)); y[:len(a)] += a; y[ns(d1):ns(d1) + len(b)] += b
    return fft_filter(y, hi=7000) * vel

def blip(f, d=0.045, kind='pulse', duty=0.35, vel=1.0, glide=-1.5):
    n = ns(d); t = np.arange(n) / SR
    ff = f * 2 ** (glide * t / d / 12)
    y = osc(kind, ff, 0, duty)
    env = np.minimum(1, t / 0.004) * np.clip(1 - (t - d * 0.6) / (d * 0.4), 0, 1)
    return fft_filter(y * env, hi=5000) * vel

def glide_tone(f0, f1, d, kind='sine', vel=1.0, curve=1.0, duty=0.5):
    n = ns(d); t = np.arange(n) / SR
    u = (t / d) ** curve
    ff = f0 * (f1 / f0) ** u
    y = osc(kind, ff, 0, duty)
    return fade_io(y, 0.004, 0.02) * vel

def sparkle(d=0.8, density=30, vel=1.0, seed=0, fmin=2500, fmax=7000):
    n = ns(d); y = np.zeros(n)
    g = rng('sparkle', seed)
    m = int(density * d)
    for i in range(m):
        t0 = g.uniform(0, d * 0.85); f = g.uniform(fmin, fmax); L = g.uniform(0.04, 0.12)
        s = np.sin(TWO_PI * f * tvec(L)) * expdec(ns(L), L / 4, 0.001)
        a = ns(t0)
        y[a:a + len(s)] += s[:n - a] * g.uniform(0.3, 1.0) * (1 - t0 / d) ** 0.5
    return y * vel

def pad(freqs, d, kind='saw', vel=1.0, a=0.6, r=0.8, cutoff=1800, detune=0.004, seed=0):
    n = ns(d); t = np.arange(n) / SR
    y = np.zeros(n)
    g = rng('pad', seed)
    for f in freqs:
        for dt in (-detune, 0, detune):
            y += osc(kind, f * (1 + dt), d, ph0=g.uniform(0, 6.28)) / 3
    y = fft_filter(y, hi=cutoff, slope=1.5)
    env = np.minimum(1, t / a) * np.clip((d - t) / r, 0, 1)
    return y * env * vel / max(1, len(freqs)) ** 0.5

# ---------------------------------------------------------------- reverb
def make_ir(rt60=1.6, d=None, seed=0, damp=4500, pre=0.012, width=1.0, early=True):
    d = d or min(4.0, rt60 * 1.1)
    n = ns(d); t = np.arange(n) / SR
    g = rng('ir', seed)
    tau = rt60 / 6.9
    L = g.normal(0, 1, n) * np.exp(-t / tau)
    R = g.normal(0, 1, n) * np.exp(-t / tau)
    R = L * (1 - width) + R * width
    # frequency dependent damping (more HF loss later)
    def damp_fn(tc, f):
        fc = damp * np.exp(-tc / (rt60 * 0.45)) + 600
        return 1 / np.sqrt(1 + (f / fc) ** 2)
    L = stft_filter(L, damp_fn, 1024, 256); R = stft_filter(R, damp_fn, 1024, 256)
    p = ns(pre)
    L = np.concatenate([np.zeros(p), L])[:n]; R = np.concatenate([np.zeros(p), R])[:n]
    if early:
        for (dt, a, pan) in [(0.011, 0.5, -0.6), (0.017, 0.4, 0.5), (0.023, 0.33, -0.2), (0.031, 0.28, 0.7), (0.043, 0.2, -0.8)]:
            k = ns(dt)
            L[k] += a * (1 - pan) * 0.5 * 8; R[k] += a * (1 + pan) * 0.5 * 8
    e = np.sqrt(np.sum(L ** 2) + np.sum(R ** 2))
    return np.stack([L, R], axis=1) / e

def convolve_stereo(x, ir):
    """x: (n,2) or (n,), ir: (m,2) -> (n+m-1, 2)"""
    if x.ndim == 1: x = np.stack([x, x], axis=1)
    n, m = len(x), len(ir)
    N = 1 << int(math.ceil(math.log2(n + m)))
    out = np.zeros((n + m - 1, 2))
    for c in range(2):
        X = np.fft.rfft(x[:, c], N); Hh = np.fft.rfft(ir[:, c], N)
        out[:, c] = np.fft.irfft(X * Hh, N)[:n + m - 1]
    return out

# ---------------------------------------------------------------- bus
class Bus:
    def __init__(self, dur):
        self.n = int(math.ceil(dur * SR)) + SR * 2
        self.x = np.zeros((self.n, 2))
    def add(self, sig, t, gain=1.0, pan=0.0):
        if sig is None or len(sig) == 0: return
        a = ns(t)
        if a >= self.n: return
        if a < 0:
            sig = sig[-a:]; a = 0
        L = min(len(sig), self.n - a)
        p = (pan + 1) * np.pi / 4
        gl, gr = math.cos(p) * gain * 1.414, math.sin(p) * gain * 1.414
        if sig.ndim == 1:
            self.x[a:a + L, 0] += sig[:L] * gl; self.x[a:a + L, 1] += sig[:L] * gr
        else:
            self.x[a:a + L, 0] += sig[:L, 0] * gl; self.x[a:a + L, 1] += sig[:L, 1] * gr
    def __iadd__(self, other):
        self.x += other.x; return self

def mx(*parts):
    """sum arrays of different lengths (pad to longest). parts: arrays or (array, gain)."""
    arrs = [(p if isinstance(p, np.ndarray) else p[0] * p[1]) for p in parts]
    n = max(len(a) for a in arrs); y = np.zeros(n)
    for a in arrs: y[:len(a)] += a
    return y


# ------------------------------------------------------------------ ACT IV: plucked strings, water
def pluck(f, d=2.5, vel=1.0, bright=0.5, seed=0, body=True):
    """Karplus-Strong plucked string (nylon guitar when bright ~0.3-0.5).  returns mono float array."""
    n = ns(d); N = max(2, int(round(SR / f)))
    r = np.random.default_rng(seed)
    buf = r.uniform(-1, 1, N)
    k = int(max(1, N * (0.5 - 0.4 * bright)))                # softer pluck = smoother excitation
    buf = np.convolve(buf, np.ones(k) / k, mode='same')
    out = np.empty(n)
    damp = 0.4985 + 0.0013 * bright
    i = 0; prev = 0.0
    while i < n:
        m = min(N, n - i)
        out[i:i + m] = buf[:m]
        nb = damp * (buf + np.roll(buf, -1))
        buf = nb
        i += m
    out *= np.exp(-np.arange(n) / (SR * d * 0.45))
    if body:
        out = out + 0.35 * peak_filter(out, 110.0, 3.0, 1.0) + 0.2 * peak_filter(out, 240.0, 4.0, 1.0)
    return fade_io(out * vel * 0.6, 0.002, 0.05)

def water_plop(vel=1.0, seed=0, f0=520, f1=1500, d=0.09):
    """bobber / drop into water: a fast rising sine 'bloop' + a tiny splash."""
    y = glide_tone(f0, f1, d, 'sine', 1.0, 0.6) * np.exp(-np.linspace(0, 4, ns(d)))
    s = fft_filter(noise(0.12, seed), 1500, 6000) * np.exp(-np.linspace(0, 8, ns(0.12))) * 0.25
    out = np.zeros(ns(0.14)); out[:len(y)] += y; out[:len(s)] += s
    return out * vel
