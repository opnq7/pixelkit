"""pixelkit.audio.cues - reusable sound-design cues for pixel-story videos.

Every cue has the form  cue(bus, t, ..., gain=..., pan=...)  and ADDS itself to a synth.Bus.
Gains are pre-balanced against music.theme_a at gain 1 (dialogue blips ~0.05, thuds ~0.3).

    from pixelkit.audio import synth as Z, cues as Q
    X = Z.Bus(12); Q.ding(X, 3.0); Q.ok(X, 3.5); Q.coin(X, 3.6)
"""
import math
import numpy as np
from . import synth as Z
from .synth import SR, nf, ns, mtof, n2m

def _t(d): return np.arange(ns(d)) / SR

# ------------------------------------------------------------------ ambience
def room_tone(bus, t0, t1, hum=0.004, air=0.009, fade=0.4, seed=5):
    """fluorescent / computer hum + low filtered air."""
    d = t1 - t0
    if d <= 0: return
    t = _t(d)
    e = np.minimum(1, t / max(fade, 1e-3)) * np.clip((d - t) / max(fade, 1e-3), 0, 1)
    h = (np.sin(2 * np.pi * 120 * t) + 0.4 * np.sin(2 * np.pi * 240 * t) + 0.15 * np.sin(2 * np.pi * 360 * t)) * e
    bus.add(h, t0, hum)
    bus.add(Z.fft_filter(Z.noise(d, seed), hi=500) * e, t0, air)

def clock_ticks(bus, t0, t1, period=1.0, gain=0.05, pan=0.35, phase=0.0):
    """soft wall-clock tick-tock."""
    i = 0; tt = t0 + phase
    while tt < t1:
        f = 2650 if i % 2 == 0 else 2350
        t = _t(0.06)
        y = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.004) + 0.6 * np.sin(2 * np.pi * 1180 * t) * np.exp(-t / 0.008)
             + Z.fft_filter(Z.noise(0.06, 900 + i), lo=2500) * np.exp(-t / 0.003) * 0.5)
        bus.add(y, tt, gain * (1.0 if i % 2 == 0 else 0.8), pan=pan)
        tt += period; i += 1

def breath_hum(bus, t0, t1, env_fn, f=196.0, gain=0.006, pan=0.0):
    """very quiet electronic hum following env_fn(t) in 0..1 (e.g. a sleeping status LED)."""
    d = t1 - t0
    t = _t(d)
    e = np.array([env_fn(t0 + x) for x in t[::480]])
    e = np.interp(t, t[::480], e)
    y = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 1.5 * t) + 0.15 * np.sin(2 * np.pi * f * 2 * t)) * e
    y = Z.fade_io(y, 0.05, 0.1)
    bus.add(y, t0, gain, pan=pan)

def pad_swell(bus, t0, d, notes=('C3', 'G3', 'E4', 'B4'), gain=0.08, a=None, r=0.5, cutoff=1400, seed=4):
    """slow warm pad (the 'lights come up' swell)."""
    fr = [nf(n) if isinstance(n, str) else n for n in notes]
    bus.add(Z.pad(fr, d, 'saw', 1.0, a=a if a is not None else d * 0.8, r=r, cutoff=cutoff, seed=seed), t0, gain)

# ------------------------------------------------------------------ UI / chat
def pop(bus, t, gain=0.10, pan=0.0, up=True):
    """bubble pop (rising) / un-pop (falling)."""
    bus.add(Z.glide_tone(320, 760, 0.07, 'sine', 1.0, 0.7) if up else Z.glide_tone(700, 260, 0.08, 'sine', 1.0, 1.0), t, gain, pan=pan)

def ding(bus, t, gain=0.12, pan=0.0, note='E6'):
    """message notification '叮'."""
    pop(bus, t - 0.01, gain * 0.8, pan)
    bus.add(Z.bell(nf(note), 1.4, 1.0), t + 0.01, gain, pan=pan)
    bus.add(Z.bell(nf(note) * 2, 0.6, 1.0), t + 0.01, gain * 0.25, pan=pan)

def chat_in(bus, t, gain=0.07, pan=0.0, k=0):
    """incoming chat bubble (pop + small bell, pitch rises with k)."""
    pop(bus, t - 0.005, gain, pan)
    bus.add(Z.bell(nf(['C6', 'D6', 'E6', 'G6', 'A6'][k % 5]), 0.7, 1.0), t + 0.015, gain * 0.55, pan=pan)

def ui_slide(bus, t, gain=0.03, pan=0.0, seed=9, d=0.22):
    bus.add(Z.whoosh(d, 2000, 6000, 1.0, seed), t, gain, pan=pan)

def crt_wake(bus, t, gain=1.0, pan=-0.2):
    """CRT power-on: thunk + 'bwom' + static + faint 15 kHz-style whine."""
    bus.add(Z.thud(0.8, False, 3, 120, 45), t, 0.26 * gain, pan=pan)
    tt = _t(0.8)
    bwom = np.sin(2 * np.pi * 58 * tt) * (0.7 + 0.3 * np.sin(2 * np.pi * 7 * tt)) * np.exp(-tt / 0.28) * np.minimum(1, tt / 0.01)
    bus.add(bwom, t + 0.01, 0.20 * gain, pan=pan)
    static = Z.fft_filter(Z.noise(0.35, 11), lo=2000) * np.exp(-_t(0.35) / 0.08)
    bus.add(static, t + 0.02, 0.055 * gain, pan=pan)
    tw = _t(1.2)
    bus.add(np.sin(2 * np.pi * 9800 * tw) * np.exp(-tw / 0.5) * np.minimum(1, tw / 0.05), t + 0.05, 0.005 * gain, pan=pan)

# ------------------------------------------------------------------ voice (dialogue blips)
VOICE_SCALE = ['A4', 'C5', 'D5', 'E5', 'G5', 'A5']
PUNCT = set(' 。，、——…？！?!.,~～')
def voice_line(bus, text, t0, cps=13.0, gain=0.05, shift=0, kind='pulse', seed=0, question=False, d=0.05, pan=-0.05, lead_in=0.0,
               times=None):
    """Animal-Crossing-style syllable blips, one per character.
    times: per-character start times (anim.type_times) so blips match a typewriter box with punctuation pauses."""
    for i, ch in enumerate(text):
        if ch in PUNCT: continue
        t = (times[i] if times is not None else t0 + i / cps) + lead_in
        k = (ord(ch) * 7 + i * 3 + seed) % len(VOICE_SCALE)
        f = nf(VOICE_SCALE[k]) * 2 ** (shift / 12)
        if question and i >= len(text.rstrip('？?…')) - 1: f *= 1.25
        y = Z.blip(f, d, kind, 0.3, 1.0, glide=-1.0 if not question else 1.5)
        bus.add(y, t, gain * (0.85 + 0.3 * ((ord(ch) * 13) % 7) / 7), pan=pan)

def ok(bus, t, gain=1.0, pan=0.1, shift=0, jingle=True, muffled=False):
    """Claude's '好的！': two voice blips (好 / 的↑) + optional bright 3-note jingle."""
    s = 2 ** (shift / 12)
    for k, (dt, nn, gl) in enumerate([(0.0, 'E5', -0.6), (0.075, 'A5', 1.6)]):
        y = Z.blip(nf(nn) * s, 0.06 if k == 0 else 0.08, 'pulse', 0.3, 1.0, gl)
        if muffled: y = Z.fft_filter(y, hi=900)
        bus.add(y, t + dt, (0.055 if not muffled else 0.09) * gain, pan=pan)
    if jingle and not muffled:
        for k, nn in enumerate(['G5', 'D6', 'G6']):
            bus.add(Z.chip_note(nf(nn) * s, 0.05 if k < 2 else 0.14, 'pulse', 0.5, a=0.001, d=0.06, s=0.7, r=0.05),
                    t + 0.17 + 0.045 * k, 0.034 * gain, pan=pan)

def coin(bus, t, gain=0.04, pan=0.5, k=0, short=False):
    s = 2 ** (k / 12)
    if short: bus.add(Z.coin(1.0, nf('B5') * s, nf('E6') * s, 0.03, 0.08), t, gain, pan=pan)
    else: bus.add(Z.coin(1.0, nf('B5') * s, nf('E6') * s), t, gain, pan=pan)

def sparkle(bus, t, d=0.4, gain=0.02, pan=0.0, seed=0):
    bus.add(Z.sparkle(d, 25, 1.0, seed), t, gain, pan=pan)

# ------------------------------------------------------------------ physical
def fall(bus, t0, t1, gain=0.016, pan=0.0):
    """falling whistle from t0 to impact t1."""
    if t1 - t0 < 0.08: return
    bus.add(Z.glide_tone(1500, 420, t1 - t0, 'sine', 1.0, 0.8), t0, gain, pan=pan)

def thud(bus, t, size=1.0, gain=0.3, pan=0.0, seed=0):
    """object landing; size 0 (tiny) .. 1 (big)."""
    big = size > 0.6
    f0 = 95 if big else 150 - 60 * size
    bus.add(Z.thud(1.0, big, seed, f0, 46 if big else 55), t, gain * (0.45 + 0.55 * size), pan=pan)

def bonk(bus, t, gain=1.0, pan=0.0):
    """cartoon head bonk: woody knock + spring boing + little dizzy tweets."""
    tt = _t(0.12)
    knock = (np.sin(2 * np.pi * (880 * np.exp(-tt / 0.03) + 380) * tt) * np.exp(-tt / 0.03)
             + Z.fft_filter(Z.noise(0.12, 77), lo=900, hi=5000) * np.exp(-tt / 0.008) * 0.8)
    bus.add(knock, t, 0.22 * gain, pan=pan)
    bus.add(Z.kick_chip(0.2, 210, 70), t, 0.18 * gain, pan=pan)
    tb = _t(0.62)
    f = 170 * (1 + 0.32 * np.exp(-tb / 0.25) * np.sin(2 * np.pi * 15 * tb)) * (1 + 0.25 * np.exp(-tb / 0.05))
    boing = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tb / 0.22) * np.minimum(1, tb / 0.004)
    bus.add(Z.fft_filter(boing + 0.3 * np.sign(boing) * np.abs(boing) ** 2, hi=3000), t + 0.01, 0.12 * gain, pan=pan)
    dizzy(bus, t + 0.22, 0.6, gain * 0.9, pan)

def dizzy(bus, t, d=0.6, gain=1.0, pan=0.0):
    """circling-stars tweets."""
    n = max(2, int(d / 0.16))
    for i in range(n):
        f0 = [2600, 3100, 2800, 3300][i % 4]
        bus.add(Z.glide_tone(f0, f0 * 1.35, 0.06, 'sine', 1.0, 1.0), t + i * 0.16, 0.022 * gain, pan=pan + 0.3 * math.sin(i * 2.1))

def typing(bus, t0, t1, rate0=14.0, rate1=None, gain=0.05, pan=0.05, seed=0):
    """keyboard typing; rate (keys/s) ramps from rate0 to rate1."""
    g = Z.rng('typing', seed, round(t0, 3))
    rate1 = rate0 if rate1 is None else rate1
    tt = t0
    while tt < t1:
        u = (tt - t0) / max(1e-6, t1 - t0)
        bus.add(Z.key_click(1.0, int(tt * 1000) + seed), tt, gain * float(g.uniform(0.75, 1.0)), pan=pan + float(g.uniform(-0.08, 0.08)))
        tt += float(g.uniform(0.6, 1.4)) / (rate0 + (rate1 - rate0) * u)

# ------------------------------------------------------------------ transitions / impacts
def whoosh(bus, t, d=0.35, gain=0.1, pan=0.0, f0=300, f1=5000, seed=0, curve=1.0):
    bus.add(Z.whoosh(d, f0, f1, 1.0, seed, curve), t, gain, pan=pan)

def riser(bus, t0, t1, gain=0.09, f0=500, f1=6000, seed=77):
    d = t1 - t0
    r = Z.bp_sweep(Z.noise(d, seed), f0, f1, 1.6, 0.7)
    u = np.arange(len(r)) / len(r)
    bus.add(r * u ** 1.5, t0, gain)

def crash(bus, t, gain=0.08, pan=0.0, d=1.6, seed=1, tau=0.5):
    y = Z.fft_filter(Z.noise(d, seed), lo=3500) * np.exp(-_t(d) / tau)
    bus.add(y, t, gain, pan=pan)

def impact(bus, t, gain=1.0):
    """the big downbeat hit: kick + sub drop + crash pair."""
    bus.add(Z.kick_chip(0.45, 200, 42), t, 0.36 * gain)
    ts = _t(0.9)
    sub = np.sin(2 * np.pi * np.cumsum(38 + 50 * np.exp(-ts / 0.09)) / SR) * np.exp(-ts / 0.35)
    bus.add(sub, t, 0.20 * gain)
    crash(bus, t, 0.09 * gain, -0.25, 1.8, 2); crash(bus, t + 0.004, 0.07 * gain, 0.25, 1.5, 3)

def scratch(bus, t, gain=0.1):
    """short record-scratch/ 'zip' (for freezes and cuts)."""
    tt = _t(0.14)
    f = 1200 * np.exp(-tt / 0.05) + 200
    y = Z.fft_filter(Z.noise(0.14, 66), lo=300, hi=4000) * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(f) / SR))
    bus.add(y * np.exp(-tt / 0.06), t, gain)

# ------------------------------------------------------------------ character foley
def snore(bus, t_in, d_in=0.8, d_out=0.95, gain=1.0, pan=0.0, seed=0, stop=None, whistle=True):
    """cute sleeping breath: airy rising inhale (+ faint rattle), then a soft falling whistle on the exhale.
    Sync it to a breathing light. stop = absolute time where it is cut short (e.g. woken by a '叮')."""
    n_in = ns(d_in)
    t = _t(d_in); u = t / d_in
    air = Z.bp_sweep(Z.noise(d_in, 300 + seed), 450, 1300, 1.0, 0.7) * np.sin(np.pi * u) ** 1.6
    rattle = Z.fft_filter(Z.osc('saw', 82.0, d_in), hi=520) * (0.6 + 0.4 * np.sin(2 * np.pi * 27 * t)) * np.sin(np.pi * u) ** 2
    to = _t(d_out); v = to / d_out
    env = np.minimum(1, to / 0.12) * np.clip(1 - v, 0, 1) ** 1.3
    wf = 1450 * (0.68 ** v) * (1 + 0.012 * np.sin(2 * np.pi * 6.5 * to))
    wh = np.sin(2 * np.pi * np.cumsum(wf) / SR) * env
    breath = Z.fft_filter(Z.noise(d_out, 400 + seed), lo=700, hi=2600) * env
    y = np.zeros(n_in + len(to))
    y[:n_in] = air * 0.9 + rattle * 0.22
    y[n_in:] = wh * (0.30 if whistle else 0.0) + breath * 0.55
    if stop is not None:
        k = ns(stop - t_in)
        if 0 < k < len(y):
            f = min(ns(0.015), k); y[k - f:k] *= np.linspace(1, 0, f); y[k:] = 0
    bus.add(y, t_in, 0.05 * gain, pan=pan)

def jump(bus, t, gain=1.0, pan=0.0, f0=330, f1=990, d=0.13):
    """platformer jump blip (square glide up)."""
    bus.add(Z.fft_filter(Z.glide_tone(f0, f1, d, 'pulse', 1.0, 0.6, 0.25), hi=6000), t, 0.045 * gain, pan=pan)

def clack(bus, t, size=0.5, gain=1.0, pan=0.0, seed=0):
    """a word-brick landing: woody block knock (pitch drops with size) + small body thump."""
    g = Z.rng('clack', seed)
    f = (900 - 450 * size) * float(g.uniform(0.9, 1.1))
    tt = _t(0.09)
    knock = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.012) + 0.5 * np.sin(2 * np.pi * f * 2.3 * tt) * np.exp(-tt / 0.006)
    click = Z.fft_filter(Z.noise(0.09, 500 + seed), lo=1500, hi=7000) * np.exp(-tt / 0.004) * 0.6
    bus.add(knock + click, t, 0.10 * gain, pan=pan)
    thud(bus, t, size, 0.22 * gain, pan, seed)

# ------------------------------------------------------------------ clocks / time
def tock(bus, t, gain=1.0, pan=0.1, k=0, low=True):
    """big close-up quartz tock (clock insert). k = 0,1,2.. gets slightly louder each tick (tension)."""
    tt = _t(0.25)
    y = (np.sin(2 * np.pi * 1180 * tt) * np.exp(-tt / 0.012) + 0.5 * np.sin(2 * np.pi * 2650 * tt) * np.exp(-tt / 0.006)
         + 0.6 * np.sin(2 * np.pi * 420 * tt) * np.exp(-tt / 0.03))
    bus.add(y, t, (0.22 + 0.04 * k) * gain, pan=pan)
    if low: bus.add(Z.kick_chip(0.3, 100, 48), t, (0.25 + 0.05 * k) * gain)

def hour_chime(bus, t, gain=1.0, notes=('G5', 'E5'), riser=0.55, seed=5):
    """the hour strikes: noise riser into a big kick + crash + two bell strokes + sparkle."""
    if riser > 0:
        r = Z.bp_sweep(Z.noise(riser, 51), 800, 9000, 2.0, 0.6) * np.linspace(0, 1, ns(riser)) ** 2
        bus.add(r, t - riser, 0.10 * gain)
    bus.add(Z.kick_chip(0.45, 220, 48), t, 0.42 * gain)
    crash(bus, t, 0.10 * gain, 0.2, 2.2, seed)
    for k, nn in enumerate(notes):
        bus.add(Z.bell(nf(nn), 3.0 + 0.5 * k), t + 0.02 + 0.45 * k, 0.20 * gain, pan=-0.1 + 0.2 * k)
    bus.add(Z.sparkle(1.0, 40, 1.0, 7), t, 0.05 * gain)

def ticker(bus, t0, t1, rate0=18.0, rate1=None, gain=0.012, f=3200, pan=0.4, seed=0):
    """fast counter/clock 'racing' ticks (time-lapse HUD, rolling numbers)."""
    rate1 = rate0 if rate1 is None else rate1
    tt = t0; i = 0
    while tt < t1:
        u = (tt - t0) / max(1e-6, t1 - t0)
        bus.add(Z.blip(f * (1.0 if i % 2 == 0 else 0.84), 0.012, 'pulse', 0.5, 1.0, 0), tt, gain, pan=pan)
        tt += 1.0 / (rate0 + (rate1 - rate0) * u); i += 1

# ------------------------------------------------------------------ office / desktop UI
def stamp(bus, t, gain=1.0, pan=0.0, big=False, seed=0, chord=None):
    """rubber stamp. big=True: heavy slam + crash (+ optional piano chord, e.g. ('A1','A2','E3','A3'))."""
    if not big:
        bus.add(Z.stamp(1.0, 500 + seed), t, 0.19 * gain, pan=pan)
        return
    bus.add(Z.stamp(1.0, 700 + seed, big=True), t, 0.50 * gain, pan=pan * 0.5)
    crash(bus, t, 0.06 * gain, pan, 1.4, 40 + seed)
    if chord:
        bus.add(sum(Z.piano(nf(nn), 2.5, 1.0) for nn in chord), t, 0.16 * gain)

def paper_flip(bus, t, gain=0.12, pan=0.1, seed=0):
    bus.add(Z.paper_flip(1.0, 800 + seed), t, gain, pan=pan)

def window_open(bus, t, gain=1.0, pan=0.4):
    """Win95-style window pops open: rising square chirp + two-bell 'ta-da'."""
    bus.add(Z.glide_tone(600, 1500, 0.2, 'pulse', 1.0, 1.0, 0.5) * 0.4, t, 0.04 * gain, pan=pan)
    bus.add(Z.bell(nf('C6'), 1.0) + Z.bell(nf('G6'), 1.0) * 0.6, t + 0.27, 0.06 * gain, pan=pan)

def window_close(bus, t, gain=1.0, pan=0.4):
    bus.add(Z.glide_tone(1300, 520, 0.14, 'pulse', 1.0, 1.0, 0.5) * 0.4, t, 0.035 * gain, pan=pan)
    bus.add(Z.blip(nf('G5'), 0.05, 'pulse', 0.3, 1.0, -2.0), t + 0.12, 0.03 * gain, pan=pan)

def mouse_click(bus, t, gain=1.0, pan=0.5, up=0.11, seed=5):
    """mouse button down + release."""
    bus.add(Z.key_click(1.0, seed) * 1.3, t, 0.14 * gain, pan=pan)
    bus.add(Z.key_click(1.0, seed + 1) * 0.8, t + up, 0.08 * gain, pan=pan)

def key(bus, t, gain=0.12, pan=0.2, seed=None):
    """single keyboard key (use typing() for runs)."""
    bus.add(Z.key_click(1.0, int(t * 999) if seed is None else seed), t, gain, pan=pan)

def result_ding(bus, t, gain=1.0, pan=0.45):
    """search result found: bell + little data-chirp run."""
    bus.add(Z.bell(nf('E6'), 1.4), t, 0.10 * gain, pan=pan)
    for i in range(5):
        bus.add(Z.blip(2000 + 120 * i, 0.012, 'pulse', 0.5, 1.0, 0), t + 0.06 * i, 0.015 * gain, pan=pan)

def box_open(bus, t, gain=0.02, pan=0.0, low=False):
    """dialogue/narration box opening."""
    bus.add(Z.glide_tone(450 if low else 500, 700 if low else 900, 0.06, 'sine', 1.0), t, gain, pan=pan)

def question(bus, t, gain=0.06, pan=0.0):
    """'?' pops over a head: rising whistle with a cartoon vibrato."""
    y = Z.glide_tone(420, 840, 0.16, 'sine', 1.0, 1.0) * (1 + 0.3 * np.sin(_t(0.16)[:ns(0.16)] * 2 * np.pi * 18))
    bus.add(y, t, gain, pan=pan)

def line_clear(bus, t, gain=1.0, pan=0.0, n=6, root='C6', flashes=(0.0, 0.15, 0.30), burst=0.45):
    """Tetris-style line clear: blips on each flash, rising arpeggio, then a sparkly noise burst at t+burst."""
    for k, dt in enumerate(flashes):
        bus.add(Z.blip(nf(root) * 2 ** (k * 4 / 12), 0.05, 'pulse', 0.5, 1.0, 0), t + dt, 0.035 * gain, pan=pan)
    sc = [0, 4, 7, 12, 16, 19, 24, 28]
    for k in range(n):
        f = nf(root) * 2 ** (sc[k % len(sc)] / 12)
        bus.add(Z.chip_note(f, 0.05, 'pulse', 0.25, a=0.001, d=0.04, s=0.6, r=0.04), t + burst - 0.18 + 0.03 * k, 0.03 * gain, pan=pan)
    nb = Z.bp_sweep(Z.noise(0.5, 61), 1200, 7000, 1.0, 0.8) * np.exp(-_t(0.5)[:ns(0.5)] / 0.15)
    bus.add(nb, t + burst, 0.08 * gain, pan=pan)
    bus.add(Z.sparkle(0.9, 40, 1.0, 23), t + burst, 0.04 * gain, pan=pan)
    bus.add(Z.kick_chip(0.3, 180, 60), t + burst, 0.12 * gain)

def soft_land(bus, t, size=0.5, gain=1.0, pan=0.0, seed=0, note=None):
    """a light, floaty object settling (pillow-ish thump + tiny pluck). note: e.g. 'F5' to make it musical."""
    g = Z.rng('soft', seed)
    bus.add(Z.thud(1.0, False, seed, 120 - 40 * size, 60), t, (0.08 + 0.08 * size) * gain, pan=pan)
    f = nf(note) if note else float(g.uniform(700, 1100))
    bus.add(Z.glide_tone(f * 0.7, f, 0.07, 'sine', 1.0, 0.5), t, 0.035 * gain, pan=pan)

def tension_pad(bus, t0, d, gain=0.10, notes=('G2', 'D3', 'F3', 'B3'), a=1.6, r=0.12, cutoff=1500, seed=4):
    """unresolved dominant pad (waiting for the hour)."""
    bus.add(Z.pad([nf(n) for n in notes], d, 'saw', 1.0, a=a, r=r, cutoff=cutoff, seed=seed), t0, gain)

def night_bed(bus, t0, t1, gain=1.0, car_at=1.4, car_d=2.6, fade_in=0.35, fade_out=1.0, seed=222):
    """late-night office: low air, faint mains hum, one distant car passing L->R."""
    d = t1 - t0
    t = _t(d)
    env = np.minimum(1, t / fade_in) * np.clip((d - t) / fade_out, 0, 1)
    bus.add(Z.fft_filter(Z.noise(d, seed), hi=380) * env, t0, 0.028 * gain)
    bus.add((np.sin(2 * np.pi * 60 * t) + 0.5 * np.sin(2 * np.pi * 120 * t)) * env, t0, 0.004 * gain)
    if car_at is not None and car_at + car_d < d + 1:
        n2 = ns(car_d); t2 = np.arange(n2) / SR
        car = Z.fft_filter(Z.noise(car_d, seed + 111), lo=60, hi=700) * np.sin(np.pi * t2 / car_d) ** 2
        bus.add(np.stack([car * np.linspace(1, 0.2, n2), car * np.linspace(0.2, 1, n2)], axis=1), t0 + car_at, 0.012 * gain)

# ------------------------------------------------------------------ title
def title_sting(bus, t, gain=1.0, chord=('C3', 'G3', 'B3', 'D4', 'E4'), fx_bus=None, swell=1.0, box=True):
    """title card sting: e-piano Cmaj9 + pad + bell + sub, preceded by a reversed reverb swell (starts t-swell);
    kick + sparkle on fx_bus (or bus); music-box answer phrase."""
    fx = fx_bus or bus
    tc = Z.Bus(4.0)
    for k, nn in enumerate(chord):
        tc.add(Z.fm_epiano(nf(nn), 3.0, 0.7, 0.7), 0.012 * k, 0.07, pan=-0.3 + 0.15 * k)
    tc.add(Z.pad([nf(nn) for nn in chord], 3.6, 'saw', 1.0, a=0.05, r=1.6, cutoff=2200, seed=9), 0, 0.14)
    tc.add(Z.bell(nf('C6'), 3.0), 0.0, 0.07, pan=0.1)
    tc.add(Z.chip_note(nf('C2'), 3.0, 'sine', a=0.01, d=1.0, s=0.5, r=0.6), 0.0, 0.16)
    if swell > 0:
        rv = Z.convolve_stereo(tc.x[:ns(2.5)], Z.make_ir(2.6, seed=3))
        rev = rv[:ns(swell)][::-1].copy()
        rev *= np.linspace(0, 1, len(rev))[:, None] ** 2
        bus.add(rev, t - len(rev) / SR, 1.6 * gain)
    bus.add(tc.x, t, gain)
    fx.add(Z.kick_chip(0.5, 120, 46), t, 0.25 * gain)
    fx.add(Z.sparkle(0.8, 26, 1.0, 19, 3000, 8000), t + 0.15, 0.04 * gain)
    if box:
        for (dt, nn) in [(0.55, 'C6'), (0.9, 'E6'), (1.25, 'G6'), (1.95, 'B5'), (1.97, 'D6'), (2.6, 'C6')]:
            bus.add(Z.music_box(nf(nn), 2.2, 1.0), t + dt, 0.07 * gain, pan=0.15)

# ------------------------------------------------------------------ office / desktop UI (v0.3: Act II "请假单")
def chapter_chime(bus, t, gain=1.0, notes=('G5', 'C6', 'E6'), pad=('F3', 'C4', 'A4'), pan=0.0):
    """soft chapter-card sting: airy whoosh + rising 3-bell motif + short pad bloom (lighter than title_sting)."""
    bus.add(Z.whoosh(0.5, 400, 3000, 1.0, 71), t - 0.25, 0.035 * gain, pan=pan)
    for k, nn in enumerate(notes):
        bus.add(Z.bell(nf(nn), 1.8, 1.0), t + 0.11 * k, 0.05 * gain * (1 - 0.15 * k), pan=pan - 0.15 + 0.15 * k)
    bus.add(Z.pad([nf(n) for n in pad], 2.0, 'saw', 1.0, a=0.15, r=1.0, cutoff=1500, seed=7), t, 0.07 * gain)

def digit_ticks(bus, times, gain=0.02, f0=1800, f1=4200, pan=0.3):
    """one tick per appearing digit / char (e.g. a racing number field); pitch climbs across the run."""
    n = max(1, len(times) - 1)
    for i, tt in enumerate(times):
        f = f0 * (f1 / f0) ** (i / n)
        bus.add(Z.blip(f, 0.014, 'pulse', 0.5, 1.0, 0), tt, gain * (0.8 + 0.4 * i / n), pan=pan)

def error_buzz(bus, t, gain=1.0, pan=0.2, d=0.32):
    """Win95-style error: low square buzz (two detuned pulses) + knock. use when a field overflows / is refused."""
    tt = _t(d)
    y = Z.osc('pulse', 110, d, 0.5) + Z.osc('pulse', 116.5, d, 0.5)
    env = np.minimum(1, tt / 0.004) * np.clip((d - tt) / 0.05, 0, 1)
    bus.add(Z.fft_filter(y * env, hi=1800), t, 0.05 * gain, pan=pan)
    bus.add(Z.thud(0.6, False, 9, 180, 70), t, 0.10 * gain, pan=pan)

def deny(bus, t, gain=1.0, pan=0.2, k=0):
    """little 'nope' (hovering an option you can't have): two falling soft square notes, lower with each k."""
    s = 2 ** (-2 * k / 12)
    bus.add(Z.blip(nf('E5') * s, 0.07, 'pulse', 0.25, 1.0, -0.5), t, 0.035 * gain, pan=pan)
    bus.add(Z.blip(nf('B4') * s, 0.12, 'pulse', 0.25, 1.0, -1.5), t + 0.09, 0.035 * gain, pan=pan)

def checkbox(bus, t, gain=1.0, pan=0.2):
    """checkbox tick: mouse click + bright 'tik'."""
    mouse_click(bus, t, 0.8 * gain, pan, up=0.08, seed=17)
    bus.add(Z.blip(nf('A6'), 0.03, 'pulse', 0.5, 1.0, 2.0), t + 0.01, 0.02 * gain, pan=pan)

def heartbeat(bus, t0, t1, bpm0=62, bpm1=None, gain=1.0, pan=0.0):
    """lub-dub (tension / hesitation). bpm ramps bpm0 -> bpm1."""
    bpm1 = bpm0 if bpm1 is None else bpm1
    tt = t0
    while tt < t1:
        u = (tt - t0) / max(1e-6, t1 - t0)
        for dt, v in ((0.0, 1.0), (0.17, 0.6)):
            bus.add(Z.kick_chip(0.22, 70, 38, v), tt + dt, 0.22 * gain, pan=pan)
        tt += 60.0 / (bpm0 + (bpm1 - bpm0) * u)

def progress_ticks(bus, t0, t1, rate=6.0, gain=1.0, pan=0.3, f=1500, seed=0):
    """progress-bar / 'busy' ticks: soft alternating blips (old-PC disk chatter)."""
    tt = t0; i = 0; g = Z.rng('prog', seed)
    while tt < t1:
        bus.add(Z.blip(f * (1.0 if i % 2 == 0 else 1.19), 0.02, 'pulse', 0.5, 1.0, 0), tt, 0.012 * gain, pan=pan)
        bus.add(Z.fft_filter(Z.noise(0.02, seed + i), lo=3000) * Z.expdec(ns(0.02), 0.004), tt, 0.01 * gain, pan=pan)
        tt += float(g.uniform(0.8, 1.2)) / rate; i += 1

def progress_done(bus, t, gain=1.0, pan=0.3, k=0):
    """progress row finished: two-note confirm (rises with k)."""
    s = 2 ** (2 * k / 12)
    bus.add(Z.blip(nf('C6') * s, 0.05, 'pulse', 0.5, 1.0, 0), t, 0.025 * gain, pan=pan)
    bus.add(Z.blip(nf('G6') * s, 0.09, 'pulse', 0.5, 1.0, 0), t + 0.06, 0.025 * gain, pan=pan)

def toast(bus, t, gain=1.0, pan=0.5):
    """desktop notification toast sliding in: soft slide + two-tone chime."""
    ui_slide(bus, t - 0.05, 0.02 * gain, pan, 13, 0.2)
    bus.add(Z.bell(nf('A5'), 1.2, 1.0), t + 0.02, 0.07 * gain, pan=pan)
    bus.add(Z.bell(nf('E6'), 1.2, 1.0), t + 0.14, 0.06 * gain, pan=pan)

def highlighter(bus, t0, d=0.5, gain=1.0, pan=0.0, seed=0):
    """marker / highlight swipe: filtered noise squeak sweeping upward."""
    y = Z.bp_sweep(Z.noise(d, 600 + seed), 1500, 4500, 1.0, 0.5)
    tt = _t(d)[:len(y)]
    bus.add(y * np.sin(np.pi * tt / d) ** 0.7, t0, 0.025 * gain, pan=pan)

def status_flip(bus, t, gain=1.0, pan=0.3, on=False):
    """status badge flips (online -> away = falling 'bo-bong'; on=True rising)."""
    a, b = ('G5', 'C5') if not on else ('C5', 'G5')
    bus.add(Z.chip_note(nf(a), 0.07, 'tri', a=0.002, d=0.06, s=0.6, r=0.04), t, 0.06 * gain, pan=pan)
    bus.add(Z.chip_note(nf(b), 0.22, 'tri', a=0.002, d=0.12, s=0.5, r=0.12), t + 0.09, 0.06 * gain, pan=pan)

def auto_reply(bus, text, t, cps=32.0, gain=0.03, pan=-0.4):
    """bot auto-reply: chat_in + very fast, flat, robotic voice blips."""
    chat_in(bus, t, 0.05, pan, 3)
    for i, ch in enumerate(text):
        if ch in PUNCT: continue
        bus.add(Z.blip(nf('E5') if i % 3 else nf('A5'), 0.025, 'pulse', 0.5, 1.0, 0), t + 0.12 + i / cps, gain, pan=pan)

def crt_off(bus, t, gain=1.0, pan=0.0):
    """CRT power-off: falling whine + collapsing 'thwump' + static tail (pairs with characters.claude.crt_off)."""
    bus.add(Z.glide_tone(9000, 600, 0.5, 'sine', 1.0, 0.6), t, 0.010 * gain, pan=pan)
    tt = _t(0.4)
    bw = np.sin(2 * np.pi * (70 - 40 * tt) * tt) * np.exp(-tt / 0.12) * np.minimum(1, tt / 0.01)
    bus.add(bw, t + 0.25, 0.18 * gain, pan=pan)
    st = Z.fft_filter(Z.noise(0.3, 31), lo=2500) * np.exp(-_t(0.3) / 0.06)
    bus.add(st, t + 0.26, 0.04 * gain, pan=pan)

def switch_click(bus, t, gain=1.0, pan=0.0):
    """lamp / power switch: hard plastic click with a tiny spring."""
    bus.add(Z.key_click(1.0, 41) * 1.6, t, 0.16 * gain, pan=pan)
    bus.add(Z.blip(3200, 0.02, 'sine', 0.5, 1.0, -6), t + 0.005, 0.02 * gain, pan=pan)


# ------------------------------------------------------------------ outdoors / crowd / game feedback (ACT III)
def birds(bus, t0, t1, rate=0.7, gain=0.012, seed=31, pans=(-0.7, 0.7)):
    """sparse songbird chirps (2-5 quick glides), random pan."""
    r = np.random.default_rng(seed); t = t0 + r.uniform(0, 1 / rate)
    while t < t1:
        f = r.uniform(2600, 4200); n = int(r.integers(2, 6)); p = r.uniform(*pans); g = gain * r.uniform(0.5, 1.0)
        for k in range(n):
            f0 = f * r.uniform(0.9, 1.15); f1 = f0 * r.uniform(1.15, 1.5) if k % 2 == 0 else f0 * r.uniform(0.7, 0.9)
            bus.add(Z.glide_tone(f0, f1, r.uniform(0.04, 0.08), 'sine', 1.0, 0.8), t + k * r.uniform(0.07, 0.11), g, pan=p)
        t += r.exponential(1 / rate) + 0.25

def wind(bus, t0, t1, gain=0.02, seed=41, fade=1.0, gust=0.35, lo=150, hi=900):
    """soft outdoor wind: band-limited noise with slow gusts."""
    d = t1 - t0; t = _t(d)
    env = np.minimum(1, t / fade) * np.clip((d - t) / fade, 0, 1)
    g = 1 - gust + gust * (0.5 + 0.5 * np.sin(2 * np.pi * t / 5.3 + 1) * np.sin(2 * np.pi * t / 3.1))
    bus.add(Z.fft_filter(Z.noise(d, seed), lo=lo, hi=hi) * env * g, t0, gain)

def morning_bed(bus, t0, t1, gain=1.0, fade_in=0.4, fade_out=1.0, seed=5, birds_rate=0.8, traffic=True):
    """weekend morning street: air + wind + birds + a faint distant traffic wash."""
    d = t1 - t0; t = _t(d)
    env = np.minimum(1, t / fade_in) * np.clip((d - t) / fade_out, 0, 1)
    bus.add(Z.fft_filter(Z.noise(d, seed), lo=80, hi=1800) * env, t0, 0.010 * gain)
    if traffic: bus.add(Z.fft_filter(Z.noise(d, seed + 7), lo=50, hi=300) * env * (0.7 + 0.3 * np.sin(2 * np.pi * t / 9.0)), t0, 0.012 * gain)
    wind(bus, t0, t1, 0.010 * gain, seed + 3, fade=max(fade_in, 0.3))
    birds(bus, t0 + 0.2, t1 - 0.5, birds_rate, 0.010 * gain, seed + 11)

def fanfare(bus, t, gain=1.0, pan=0.0, root='C5', sparkle_bus=None):
    """achievement unlocked: quick square-wave arpeggio up + held major chord + sparkle."""
    r = n2m(root)
    for k, (dt, iv) in enumerate([(0.0, 0), (0.07, 4), (0.14, 7), (0.21, 12)]):
        bus.add(Z.chip_note(mtof(r + iv), 0.06, 'pulse', 0.25), t + dt, 0.05 * gain, pan=pan)
    for iv in (0, 4, 7, 12):
        bus.add(Z.chip_note(mtof(r + iv), 0.55, 'pulse', 0.125, s=0.7, r=0.25, vib=0.004), t + 0.28, 0.035 * gain, pan=pan)
    bus.add(Z.bell(mtof(r + 24), 1.6, 1.0), t + 0.28, 0.05 * gain, pan=pan)
    (sparkle_bus or bus).add(Z.sparkle(0.9, 30, 1.0, 9), t + 0.28, 0.02 * gain, pan=pan)

def fail_wah(bus, t, gain=1.0, pan=0.0):
    """quest failed: descending 'wah-wah' (two muted brass-ish square glides)."""
    for k, (f0, f1, d) in enumerate([(nf('E4'), nf('D#4'), 0.22), (nf('D4'), nf('A3'), 0.5)]):
        y = Z.glide_tone(f0, f1, d, 'pulse', 1.0, 1.0, 0.3)
        y = Z.fft_filter(y, hi=1800) * (0.6 + 0.4 * np.sin(2 * np.pi * 6 * _t(d)))
        bus.add(y, t + k * 0.24, 0.05 * gain, pan=pan)
    bus.add(Z.thud(0.5, False, 3), t, 0.12 * gain, pan=pan)

def big_ding(bus, t, gain=1.0, notes=('C6', 'E6', 'G6', 'C7'), n=24, spread=0.6, seed=8):
    """one ding becomes a whole city's worth: a strong central bell, then n dings scattered in time / pan."""
    bus.add(Z.bell(nf('C6'), 3.0, 1.0), t, 0.12 * gain); bus.add(Z.bell(nf('C5'), 3.5, 1.0), t, 0.08 * gain)
    r = np.random.default_rng(seed)
    for k in range(n):
        tt = t + 0.04 + spread * (k / n) ** 1.4 + r.uniform(0, 0.03)
        bus.add(Z.bell(nf(notes[k % len(notes)]) * 2 ** (r.integers(-1, 2) / 12 * 0), 1.0, 1.0), tt, 0.035 * gain * r.uniform(0.5, 1.0),
                pan=float(r.uniform(-0.9, 0.9)))

def crowd_gasp(bus, t, gain=1.0, n=40, seed=12, d=0.7):
    """many tiny voices going '啊？！' at once: rising blips with jitter + a breathy noise swell."""
    r = np.random.default_rng(seed)
    for k in range(n):
        f0 = r.uniform(300, 900); tt = t + r.uniform(0, 0.25)
        y = Z.glide_tone(f0, f0 * r.uniform(1.4, 1.9), r.uniform(0.25, 0.5), 'pulse', 1.0, 1.4, 0.35)
        bus.add(Z.fft_filter(y, hi=3000), tt, 0.010 * gain * r.uniform(0.6, 1.0), pan=float(r.uniform(-0.9, 0.9)))
    nz = Z.fft_filter(Z.noise(d, seed), lo=400, hi=3500) * np.sin(np.pi * np.minimum(1, _t(d) / d)) ** 1.5
    bus.add(nz, t, 0.03 * gain)

def claps(bus, t0, t1, rate=14.0, gain=0.02, seed=4):
    """small warm applause (random noise claps)."""
    r = np.random.default_rng(seed); t = t0
    while t < t1:
        u = (t - t0) / max(1e-6, t1 - t0); env = math.sin(math.pi * u) ** 0.6
        c = Z.fft_filter(Z.noise(0.03, int(r.integers(1e6))), lo=800, hi=5000) * Z.expdec(ns(0.03), 0.008)
        bus.add(c, t, gain * env * r.uniform(0.5, 1.0), pan=float(r.uniform(-0.6, 0.6)))
        t += r.exponential(1 / rate)

def swish(bus, t, d=0.45, gain=0.04, pan=0.0, seed=2, f0=600, f1=2400):
    """cloth / curtain / quilt rustle (noise through a band-pass sweep)."""
    y = Z.bp_sweep(Z.noise(d, seed), f0, f1, 1.0, 0.8) * np.sin(np.pi * _t(d) / d) ** 1.2
    bus.add(y, t, gain, pan=pan)

def step(bus, t, gain=0.03, pan=0.0, seed=0, hard=True):
    """one footstep on pavement (short filtered noise tick + tiny thump)."""
    c = Z.fft_filter(Z.noise(0.05, seed), lo=300 if hard else 150, hi=3500 if hard else 1500) * Z.expdec(ns(0.05), 0.012)
    bus.add(c, t, gain, pan=pan)
    bus.add(Z.thud(0.25, False, seed), t, gain * 1.2, pan=pan)


# ------------------------------------------------------------------ river bank (ACT IV)
def river_bed(bus, t0, t1, gain=1.0, seed=61, crickets=True, fade_in=0.8, fade_out=1.2):
    """evening river: slow water lapping on the bank + soft air + two crickets (left / right)."""
    d = t1 - t0; n = ns(d); tt = np.arange(n) / SR
    lap = Z.fft_filter(Z.noise(d, seed), 160, 900)
    am = 0.55 + 0.30 * np.sin(2 * np.pi * 0.31 * tt + 1.3) + 0.15 * np.sin(2 * np.pi * 0.83 * tt + 0.2)
    air = Z.fft_filter(Z.noise(d, seed + 1), 300, 2500) * 0.25
    env = np.clip(tt / fade_in, 0, 1) * np.clip((d - tt) / fade_out, 0, 1)
    y = (lap * am * 0.9 + air) * env
    y = y / (np.abs(y).max() + 1e-9)
    bus.add(y * 0.030 * gain, t0, 1.0, pan=-0.1)
    r = np.random.default_rng(seed + 2)
    for k in range(5):                                         # little laps against the stones
        tl = t0 + r.uniform(0.3, d - 0.3)
        bus.add(Z.fft_filter(Z.noise(0.18, seed + 10 + k), 400, 2400) * np.exp(-np.linspace(0, 6, ns(0.18))), tl, 0.010 * gain, pan=r.uniform(-0.5, 0.5))
    if crickets:
        for c, (f, pan, per) in enumerate(((4300, -0.6, 0.71), (4650, 0.55, 0.93))):
            t = t0 + 0.4 + c * 0.27
            while t < t1 - 0.3:
                e = min(1.0, (t - t0) / fade_in) * min(1.0, (t1 - t) / fade_out)
                for p in range(3):
                    bus.add(Z.osc('sine', f, 0.018) * np.hanning(ns(0.018)), t + p * 0.032, 0.006 * gain * e, pan=pan)
                t += per * r.uniform(0.85, 1.15)

def plop(bus, t, gain=1.0, pan=0.0, seed=0):
    """bobber dipping / a drop into still water."""
    bus.add(Z.water_plop(1.0, seed), t, 0.05 * gain, pan=pan)

def shimmer(bus, t0, d, gain=1.0, pan=0.0, seed=0, notes=('D6', 'A6', 'F#6', 'E7')):
    """a ripple of light spreading out: soft rising air + a few glassy partials blooming."""
    bus.add(Z.whoosh(d, 400, 3000, 1.0, seed, curve=0.6) * np.hanning(ns(d)), t0, 0.022 * gain, pan=pan)
    for i, nn in enumerate(notes):
        bus.add(Z.celesta(nf(nn), 2.2, 0.7), t0 + d * (0.15 + 0.2 * i), 0.018 * gain, pan=pan + (i - 1.5) * 0.25)
    bus.add(Z.sparkle(d, 18, 1.0, seed), t0 + d * 0.2, 0.010 * gain, pan=pan)


# ------------------------------------------------------------------ v0.7 (Act 4 v2): small acting sounds
def creak(bus, t, gain=0.02, pan=0.0, seed=0, d=0.28, f0=210, f1=150):
    """a wooden board / folding-stool creak: a rough, slowly falling saw grain through a narrow wood band."""
    g = Z.rng(seed, 77)
    n = Z.ns(d)
    tone = Z.glide_tone(f0 * g.uniform(0.9, 1.1), f1 * g.uniform(0.9, 1.1), d, 'saw', 1.0, 1.0)
    grain = (Z.noise(d, seed + 3) * 0.6 + 1.0)
    x = Z.fft_filter(tone * grain, 300, 2600) * np.hanning(n) ** 0.7
    bus.add(x, t, gain, pan=pan)

def chuckle(bus, t, n=2, gain=0.02, pan=0.0, seed=0, period=0.16, f=260):
    """a held-back laugh: n short breathy 'hm' bursts through the nose (low voiced hum + filtered air)."""
    for i in range(n):
        d = 0.11
        hum = Z.glide_tone(f * (1.0 - 0.04 * i), f * 0.9, d, 'tri', 1.0, 1.0)
        air = Z.fft_filter(Z.noise(d, seed + i), 400, 1800)
        x = (hum * 0.6 + air * 0.5) * Z.adsr(Z.ns(d), 0.01, 0.05, 0.4, 0.04)
        bus.add(x, t + i * period, gain * (1 - 0.2 * i), pan=pan)

def sigh(bus, t, d=0.75, gain=0.03, pan=0.0, seed=0):
    """a long soft exhale (falling filtered air) - a robot's vent sighing."""
    n = Z.ns(d)
    x = Z.bp_sweep(Z.noise(d, seed), 1400, 500, 1.0, 0.8) * (np.linspace(1, 0, n) ** 1.5) * np.minimum(1, np.linspace(0, 8, n))
    bus.add(x, t, gain, pan=pan)

def boing(bus, t, gain=0.006, pan=0.0, f=900, d=0.22):
    """the antenna springs: a tiny wobbling sine (vibrato decays with the wobble)."""
    n = Z.ns(d); tt = np.arange(n) / Z.SR
    fr = f * (1 + 0.06 * np.sin(2 * np.pi * 14 * tt) * np.exp(-tt * 9))
    x = np.sin(2 * np.pi * np.cumsum(fr) / Z.SR) * Z.expdec(n, 0.07)
    bus.add(x, t, gain, pan=pan)

def reel(bus, t0, t1, rate=16.0, gain=0.02, pan=0.3, seed=0):
    """a fishing reel's ratchet: dry clicks + a faint gear whirr."""
    g = Z.rng(seed, 55); t = t0
    while t < t1:
        c = Z.fft_filter(Z.noise(0.006, int(g.integers(1 << 20))), 2500, 9000) * Z.expdec(Z.ns(0.006), 0.0015)
        bus.add(c, t, gain * g.uniform(0.7, 1.0), pan=pan)
        t += 1.0 / rate * g.uniform(0.85, 1.15)
    d = t1 - t0
    if d > 0.05:
        w = Z.fft_filter(Z.noise(d, seed + 9), 600, 2000) * np.hanning(Z.ns(d))
        bus.add(w, t0, gain * 0.25, pan=pan)


# ------------------------------------------------------------------ v0.10: a little live room (theatre credits)
def handclap(bus, t, gain=0.05, pan=0.0, seed=0, tone=1.0):
    """one real-sounding hand clap: 3 micro-flams of band-passed noise (~10 ms apart) + a short palm 'body'.
    tone > 1 = brighter / smaller hands, < 1 = bigger, warmer hands."""
    r = Z.rng('clap', seed, round(t, 3))
    for k, (dt, g) in enumerate(((0.0, 0.55), (0.0045 + 0.002 * r.random(), 0.8), (0.010 + 0.003 * r.random(), 1.0))):
        d = 0.02 if k < 2 else 0.09
        x = Z.fft_filter(Z.noise(d, int(r.integers(1e6))), 850 * tone, 4200 * tone) * Z.expdec(ns(d), 0.006 if k < 2 else 0.018)
        bus.add(x, t + dt, gain * g, pan=pan)
    bus.add(Z.fft_filter(Z.noise(0.03, int(r.integers(1e6))), 180, 700) * Z.expdec(ns(0.03), 0.006), t + 0.008, gain * 0.35, pan=pan)

def clap_along(bus, t0, t1, period, gain=0.05, pan=0.0, seed=0, tone=1.0, phase=0.0, jitter=0.012, swell=True):
    """one person applauding: a clap every `period` s (slightly human timing + level), fading in/out at the ends."""
    r = np.random.default_rng(seed); t = t0 + phase; i = 0
    while t < t1:
        u = (t - t0) / max(1e-6, t1 - t0)
        env = (math.sin(math.pi * min(1.0, u * 1.6 if u < 0.3 else 1 - (u - 0.3) / 0.7 * 0.35))) if swell else 1.0
        handclap(bus, t + r.normal(0, jitter), gain * env * r.uniform(0.75, 1.0), pan, seed + i, tone * r.uniform(0.94, 1.06))
        t += period; i += 1

def shaker(bus, t, gain=0.012, pan=0.0, seed=0, d=0.06):
    """a 16th-note egg shaker grain (high-passed noise with a soft attack)."""
    n = ns(d)
    env = np.minimum(1, np.arange(n) / (SR * 0.012)) * np.exp(-np.arange(n) / (SR * 0.02))
    bus.add(Z.fft_filter(Z.noise(d, seed), 4500, 12000) * env, t, gain, pan=pan)
