"""pixelkit.audio.music - tempo grid, chord tables and reusable chiptune parts.

    g = Grid(132, t0=3.045)            # beat 0 at 3.045 s
    theme_a(bus, g, bar0=0, bars=8)    # full Theme A (lead + echo + bass + arps + drums)
    bass(bus, g, CH_A, bar0=0, nbars=2, t_max=8.5)   # single parts, cut at t_max (e.g. a freeze)

All parts are pure functions of their arguments -> the same cue renders identically everywhere.
Every part accepts t_max: notes starting at/after t_max are skipped (use for hard stops/freezes).
"""
import numpy as np
from . import synth as Z
from .synth import nf, mtof, n2m

class Grid:
    """musical time -> seconds (beat 0 = t0)."""
    def __init__(self, bpm, t0=0.0, bpb=4):
        self.bpm, self.t0, self.bpb = float(bpm), float(t0), bpb
        self.spb = 60.0 / self.bpm
    def t(self, beat): return self.t0 + beat * self.spb
    def bar(self, n): return self.t(n * self.bpb)
    def d(self, beats): return beats * self.spb
    def beat(self, t): return (t - self.t0) / self.spb
    def snap(self, t, div=1): return self.t(round(self.beat(t) * div) / div)
    def shifted(self, dt):
        """same grid, everything dt seconds later (e.g. after a freeze)."""
        return Grid(self.bpm, self.t0 + dt, self.bpb)

# ------------------------------------------------------------------ Theme A: bright office chiptune (I-vi-IV-V in C)
CH_A = [('C', [60, 64, 67, 72], 48), ('Am', [57, 60, 64, 69], 45), ('F', [53, 57, 60, 65], 41), ('G', [55, 59, 62, 67], 43)]
MEL_A = [
    (0, .5, 'G4'), (.5, .5, 'C5'), (1, .5, 'E5'), (1.5, .5, 'G5'), (2, .5, 'A5'), (2.5, .5, 'G5'), (3, 1, 'E5'),
    (4, .5, 'E5'), (4.5, .5, 'A5'), (5, .5, 'C6'), (5.5, .5, 'A5'), (6, .5, 'G5'), (6.5, .5, 'E5'), (7, 1, 'C5'),
    (8, .5, 'F5'), (8.5, .5, 'A5'), (9, .75, 'C6'), (9.75, .25, 'D6'), (10, .5, 'C6'), (10.5, .5, 'A5'), (11, 1, 'F5'),
    (12, .5, 'G5'), (12.5, .5, 'B5'), (13, .5, 'D6'), (13.5, .5, 'B5'), (14, .5, 'G5'), (14.5, .25, 'A5'), (14.75, .25, 'B5'), (15, 1, 'D6'),
    (16, .5, 'E6'), (16.5, .5, 'D6'), (17, .5, 'C6'), (17.5, .5, 'G5'), (18, .5, 'A5'), (18.5, .5, 'G5'), (19, 1, 'E5'),
    (20, .5, 'A5'), (20.5, .5, 'C6'), (21, .5, 'E6'), (21.5, .5, 'C6'), (22, .5, 'B5'), (22.5, .5, 'G5'), (23, 1, 'A5'),
]
_RUNS = [['F5', 'A5', 'C6', 'A5'], ['F5', 'A5', 'C6', 'D6'], ['C6', 'A5', 'F5', 'A5'], ['C6', 'D6', 'E6', 'F6'],
         ['G5', 'B5', 'D6', 'B5'], ['G5', 'B5', 'D6', 'E6'], ['D6', 'B5', 'G5', 'B5'], ['D6', 'E6', 'F6', 'G6']]
for _bi, _r in enumerate(_RUNS):
    for _k, _nn in enumerate(_r): MEL_A.append((24 + _bi + 0.25 * _k, 0.25, _nn))
MEL_A.sort()

def _ok(t0, t_min, t_max): return (t_min is None or t0 >= t_min) and (t_max is None or t0 < t_max)

def lead(bus, g, mel=MEL_A, beat0=0, gain=0.085, pan=-0.12, echo=0.03, echo_beats=0.375, duty=0.25,
         t_min=None, t_max=None, beat_range=None):
    """pulse lead + delayed echo voice on the other side."""
    for (b, d, nn) in mel:
        if beat_range and not (beat_range[0] <= b < beat_range[1]): continue
        t0, dd = g.t(beat0 + b), g.d(d)
        if not _ok(t0, t_min, t_max): continue
        y = Z.chip_note(nf(nn), dd * 0.92, 'pulse', duty, a=0.003, d=0.09, s=0.55, r=0.04, vib=0.006 if d >= 1 else 0.0)
        bus.add(y, t0, gain, pan=pan)
        if echo > 0: bus.add(y, t0 + g.d(echo_beats if b < 24 else echo_beats / 2), echo, pan=-pan * 3.5)

def harmony(bus, g, mel=MEL_A, beat0=0, beat_range=(16, 24), gain=0.04, pan=0.25, t_min=None, t_max=None):
    """a diatonic third below the lead."""
    for (b, d, nn) in mel:
        if not beat_range[0] <= b < beat_range[1]: continue
        t0, dd = g.t(beat0 + b), g.d(d)
        if not _ok(t0, t_min, t_max): continue
        m = n2m(nn) - (4 if (n2m(nn) % 12) in (4, 9, 11) else 3)
        bus.add(Z.chip_note(mtof(m), dd * 0.9, 'pulse', 0.125, a=0.003, d=0.08, s=0.5, r=0.04), t0, gain, pan=pan)

def bass(bus, g, chords=CH_A, bar0=0, nbars=8, gain=0.16, pattern=(0, 12, 7, 12), sub=2, t_min=None, t_max=None, chord_bar0=0):
    """stepped-triangle bass, `sub` notes per beat cycling `pattern` over the chord root."""
    for bar in range(nbars):
        name, tones, root = chords[(chord_bar0 + bar) % len(chords)]
        for e in range(4 * sub):
            t0, dd = g.t((bar0 + bar) * 4 + e / sub), g.d(1 / sub)
            if not _ok(t0, t_min, t_max): continue
            m = root + pattern[e % len(pattern)]
            bus.add(Z.chip_note(mtof(m), dd * 0.8, 'tri4', a=0.002, d=0.1, s=0.8, r=0.02), t0, gain)

def arp(bus, g, chords=CH_A, bar0=0, nbars=8, sub=4, gain=0.022, pan=0.35, octave=12, t_min=None, t_max=None, chord_bar0=0,
        sub_fn=None):
    """chord arpeggio (16ths by default). sub_fn(bar) -> subdivision (e.g. accelerate to 32nds)."""
    for bar in range(nbars):
        name, tones, root = chords[(chord_bar0 + bar) % len(chords)]
        s = sub_fn(bar) if sub_fn else sub
        for e in range(4 * s):
            t0, dd = g.t((bar0 + bar) * 4 + e / s), g.d(1 / s)
            if not _ok(t0, t_min, t_max): continue
            m = tones[e % 4] + octave
            bus.add(Z.chip_note(mtof(m), dd * 0.6, 'pulse', 0.125, a=0.001, d=0.03, s=0.4, r=0.01), t0, gain, pan=pan)

def drums(bus, g, bar0=0, nbars=8, kick=(0, 2), snare=(1, 3), hats=2, gain=1.0, kick_g=0.32, snare_g=0.12, hat_g=0.035,
          t_min=None, t_max=None, hats_fn=None, seed=0):
    for bar in range(nbars):
        hs = hats_fn(bar) if hats_fn else hats
        for beat in range(4):
            b = (bar0 + bar) * 4 + beat
            t0 = g.t(b)
            if _ok(t0, t_min, t_max):
                if beat in kick: bus.add(Z.kick_chip(), t0, kick_g * gain)
                if beat in snare: bus.add(Z.snare_chip(seed=seed + b), t0, snare_g * gain, pan=0.05)
            for h in range(hs):
                th = g.t(b + h / hs)
                if not _ok(th, t_min, t_max): continue
                bus.add(Z.hat_chip(seed=int(seed + b * 10 + h)), th, (hat_g if h % 2 == 0 else hat_g * 0.63) * gain, pan=-0.3)

def roll(bus, g, beat0, beats, div=4, g0=0.03, g1=0.10, seed=300, accel=True, t_max=None):
    """snare roll crescendo; accel=True doubles the rate in the last beat."""
    t_end = g.t(beat0 + beats); b = 0.0; i = 0
    while True:
        bb = beat0 + b
        t0 = g.t(bb)
        if t0 >= t_end - 1e-6 or (t_max is not None and t0 >= t_max): break
        u = b / beats
        bus.add(Z.snare_chip(0.12, seed=seed + i), t0, g0 + (g1 - g0) * u, pan=0.05)
        step = 1 / (div * (2 if accel and b >= beats - 1 else 1))
        b += step; i += 1

def stab(bus, t, notes=(48, 60, 64, 67, 72, 76), gain=0.06, d=1.2, bass_gain=0.2):
    """big chord hit (C major by default)."""
    for m in notes:
        lo = m < 52
        bus.add(Z.chip_note(mtof(m), d, 'tri4' if lo else 'pulse', 0.25, a=0.002, d=0.3, s=0.6, r=0.2), t, bass_gain if lo else gain)

def theme_a(bus, g, bar0=0, bars=8, layers=('lead', 'echo', 'harmony', 'bass', 'arp', 'drums'), gain=1.0, t_min=None, t_max=None):
    """Theme A from its bar 0, placed at grid bar `bar0`."""
    beat0 = bar0 * 4
    if 'lead' in layers:
        lead(bus, g, MEL_A, beat0, 0.085 * gain, echo=0.03 * gain if 'echo' in layers else 0, t_min=t_min, t_max=t_max,
             beat_range=(0, bars * 4))
    if 'harmony' in layers: harmony(bus, g, MEL_A, beat0, gain=0.04 * gain, t_min=t_min, t_max=t_max)
    if 'bass' in layers: bass(bus, g, CH_A, bar0, bars, 0.16 * gain, t_min=t_min, t_max=t_max)
    if 'arp' in layers:
        arp(bus, g, CH_A, bar0, bars, gain=0.026 * gain, t_min=t_min, t_max=t_max, sub_fn=lambda b: 4 if b < 6 else 8)
    if 'drums' in layers:
        drums(bus, g, bar0, bars, gain=gain, t_min=t_min, t_max=t_max, hats_fn=lambda b: 2 if b < 6 else 4)

# ------------------------------------------------------------------ Theme B: lazy weekend lounge (Fmaj7-Em7-Dm7-G7sus, ~84 bpm)
CH_B = [('Fmaj7', [53, 57, 60, 64], 41), ('Em7', [52, 55, 59, 62], 40), ('Dm7', [50, 53, 57, 60], 38),
        ('G7sus', [55, 60, 62, 65], 43)]
MEL_B = [(0, 1, 'A5'), (1, .5, 'C6'), (1.5, .5, 'E6'), (2, 1, 'D6'), (3, 1, 'C6'),
         (4, 1, 'B5'), (5, .5, 'D6'), (5.5, .5, 'B5'), (6, 1, 'G5'), (7, 1.5, 'E6'),
         (8.5, 1.5, 'A5'), (10, 1, 'G5')]

def keys_comp(bus, g, chords=CH_B, bar0=0, nbars=4, gain=0.05, hits=((0, 1.4, 0.75), (1.5, 0.45, 0.45), (2.5, 1.3, 0.55)),
              strum=0.008, ring_last=True, t_min=None, t_max=None, chord_bar0=0, bright=0.8):
    """FM e-piano comping (strummed chord voicings). ring_last: final bar = one long held chord."""
    for bar in range(nbars):
        name, tones, root = chords[(chord_bar0 + bar) % len(chords)]
        last = ring_last and bar == nbars - 1
        for (bb, gate, vel) in (((0, 3.6, 0.7),) if last else hits):
            t0, dd = g.t((bar0 + bar) * 4 + bb), g.d(gate)
            if not _ok(t0, t_min, t_max): continue
            for k, m in enumerate(tones):
                bus.add(Z.fm_epiano(mtof(m), dd, vel, bright), t0 + strum * k, gain, pan=-0.2 + 0.13 * k)

def soft_bass(bus, g, chords=CH_B, bar0=0, nbars=4, gain=0.16, beats=(0, 2), ring_last=True, t_min=None, t_max=None, chord_bar0=0):
    """round sine+triangle bass on the chord roots."""
    for bar in range(nbars):
        name, tones, root = chords[(chord_bar0 + bar) % len(chords)]
        last = ring_last and bar == nbars - 1
        for bb in ((0,) if last else beats):
            gate = 3.6 if last else 1.8
            t0, dd = g.t((bar0 + bar) * 4 + bb), g.d(gate)
            if not _ok(t0, t_min, t_max): continue
            y = Z.chip_note(mtof(root), dd, 'sine', a=0.01, d=0.5, s=0.6, r=0.15) \
                + 0.3 * Z.chip_note(mtof(root + 12), dd, 'tri', a=0.01, d=0.3, s=0.3, r=0.15)
            bus.add(y, t0, gain)

def lazy_drums(bus, g, bar0=0, nbars=4, gain=1.0, ring_last=True, t_min=None, t_max=None, seed=0):
    """soft kick on 1, brushed rim on 2 & 4, quiet 8th hats (no drums in a ringing last bar)."""
    for bar in range(nbars):
        if ring_last and bar == nbars - 1: continue
        for beat in range(4):
            b = (bar0 + bar) * 4 + beat
            t0 = g.t(b)
            if _ok(t0, t_min, t_max):
                if beat == 0: bus.add(Z.kick_chip(0.25, 120, 45), t0, 0.16 * gain)
                if beat in (1, 3):
                    y = Z.fft_filter(Z.noise(0.15, seed + b), lo=1500, hi=7000) * Z.expdec(Z.ns(0.15), 0.045, 0.004)
                    bus.add(y, t0, 0.05 * gain, pan=0.2)
            for h in range(2):
                th = g.t(b + h * 0.5)
                if _ok(th, t_min, t_max): bus.add(Z.hat_chip(0.04, 1.0, seed + b * 2 + h), th, 0.012 * gain, pan=-0.35)

def theme_b(bus, g, bar0=0, bars=4, layers=('keys', 'bass', 'drums', 'melody'), gain=1.0, t_min=None, t_max=None,
            mel_bus=None, ring_last=True, mel=MEL_B):
    """Theme B (weekend). 4-bar phrase, repeats for bars>4; melody (music box) can go to its own bus (mel_bus)."""
    if 'keys' in layers: keys_comp(bus, g, CH_B, bar0, bars, 0.05 * gain, ring_last=ring_last, t_min=t_min, t_max=t_max)
    if 'bass' in layers: soft_bass(bus, g, CH_B, bar0, bars, 0.16 * gain, ring_last=ring_last, t_min=t_min, t_max=t_max)
    if 'drums' in layers: lazy_drums(bus, g, bar0, bars, gain, ring_last=ring_last, t_min=t_min, t_max=t_max)
    if 'melody' in layers:
        mb = mel_bus or bus
        for rep in range(max(1, bars // 4)):
            for (b, d, nn) in mel:
                t0 = g.t((bar0 + rep * 4) * 4 + b)
                if _ok(t0, t_min, t_max): mb.add(Z.music_box(nf(nn), 1.8, 1.0), t0, 0.075 * gain, pan=0.15)

# ------------------------------------------------------------------ free-time phrases (no grid)
INSTR = {
    'piano': lambda f, vel, i: Z.piano(f, 3.0, vel, 0.8, i),
    'music_box': lambda f, vel, i: Z.music_box(f, 2.0, vel),
    'celesta': lambda f, vel, i: Z.celesta(f, 1.4, vel),
    'bell': lambda f, vel, i: Z.bell(f, 3.0, vel),
    'epiano': lambda f, vel, i: Z.fm_epiano(f, 1.5, vel, 0.8),
}

def phrase(bus, t0, notes, inst='piano', gain=0.2, pan=None, t_max=None):
    """notes: [(dt, 'E5' | midi, vel)] placed at t0+dt. pan=None -> low notes slightly left, high slightly right."""
    for i, (dt, nn, vel) in enumerate(notes):
        t = t0 + dt
        if t_max is not None and t >= t_max: continue
        m = n2m(nn) if isinstance(nn, str) else nn
        p = pan if pan is not None else (-0.1 if m < 60 else 0.12)
        bus.add(INSTR[inst](mtof(m), vel, int(t * 10) + i), t, gain, pan=p)

def piano_phrase(bus, t0, notes, gain=0.2, pan=None, t_max=None):
    phrase(bus, t0, notes, 'piano', gain, pan, t_max)


# ------------------------------------------------------------------ Theme B, bright (v0.10): the weekend theme in daylight
# F - G - Am - G in C major, ~97 bpm: bouncy bass, ukulele strums with off-beat upstrokes, hand claps on 2 & 4,
# 16th shaker, soft kick on 1 & 3, melody = music box doubled by a quiet chip pulse.  Used for 第五幕 片尾 (theatre).
CH_BB = [('F', [57, 60, 65, 69], 41), ('G', [59, 62, 67, 71], 43), ('Am', [57, 60, 64, 69], 45), ('G', [59, 62, 67, 71], 43)]
CH_BB_END = ('Cadd9', [55, 60, 62, 64, 67], 36)
MEL_B2 = [(0, 1, 'A5'), (1, .5, 'C6'), (1.5, .5, 'E6'), (2, 1, 'G6'), (3, 1, 'E6'),
          (4, 1, 'D6'), (5, .5, 'E6'), (5.5, .5, 'D6'), (6, 1, 'B5'), (7, 1, 'G5'),
          (8, 1, 'C6'), (9, .5, 'B5'), (9.5, .5, 'C6'), (10, 2, 'E6'), (12.5, .5, 'D6'), (13, 1, 'B5'), (14, 2, 'D6')]

def uke_strum(bus, t, tones, vel=0.5, up=False, d=0.9, spread=0.011, pan=0.25, seed=0, bright=0.75):
    """ukulele-ish strum (Karplus-Strong, bright, short): down = low->high, up = high->low and lighter."""
    order = list(tones)[::-1] if up else list(tones)
    for k, m in enumerate(order):
        bus.add(Z.pluck(mtof(m), d, vel * (0.75 if up else 1.0) * (1 - 0.06 * k), bright, seed=seed + k, body=False),
                t + spread * k, 1.0, pan=pan - 0.04 * k)

def weekend_bright(bus, g, bar0, nbars, layers=('kick', 'bass', 'uke', 'clap', 'shaker', 'melody'), chords=CH_BB,
                   chord_bar0=0, gain=1.0, mel=None, mel_bar0=None, mel_bus=None, t_min=None, t_max=None, mutes=(), seed=0):
    """the bright weekend groove.  mutes: [(t0, t1)] windows of silence (e.g. a held breath for a gag).
    mel: [(beat, dur, note)] relative to mel_bar0 (default bar0); melody goes to mel_bus if given."""
    from . import cues as Q
    def ok(t): return _ok(t, t_min, t_max) and not any(a <= t < b for (a, b) in mutes)
    for bar in range(nbars):
        name, tones, root = chords[(chord_bar0 + bar) % len(chords)]
        b0 = (bar0 + bar) * 4
        if 'kick' in layers:
            for bb in (0, 2):
                if ok(g.t(b0 + bb)): bus.add(Z.kick_chip(0.22, 115, 46), g.t(b0 + bb), 0.13 * gain)
        if 'bass' in layers:                                       # bouncy: root, octave pop, fifth, root, octave, fifth
            for (bb, iv, gate, v) in ((0, 0, 0.8, 1.0), (1, 12, 0.3, 0.55), (1.5, 7, 0.4, 0.7), (2, 0, 0.8, 0.9),
                                      (3, 12, 0.3, 0.55), (3.5, 7, 0.4, 0.7)):
                t0 = g.t(b0 + bb)
                if not ok(t0): continue
                f = mtof(root + iv); dd = g.d(gate)
                y = Z.chip_note(f, dd, 'tri', a=0.004, d=0.12, s=0.55, r=0.05) + 0.6 * Z.chip_note(f, dd, 'sine', a=0.004, d=0.2, s=0.7, r=0.05)
                bus.add(y, t0, 0.11 * gain * v)
        if 'uke' in layers:                                        # D . D U . U D U
            for (bb, up, v) in ((0, False, 0.55), (1, False, 0.42), (1.5, True, 0.34), (2.5, True, 0.36), (3, False, 0.42), (3.5, True, 0.32)):
                t0 = g.t(b0 + bb)
                if ok(t0): uke_strum(bus, t0, tones, 0.09 * gain * v / 0.5, up, d=g.d(0.9), seed=seed + 31 * (b0 + int(bb * 2)))
        if 'clap' in layers:
            for bb in (1, 3):
                t0 = g.t(b0 + bb)
                if ok(t0):
                    Q.handclap(bus, t0, 0.045 * gain, pan=-0.12, seed=seed + b0 + bb, tone=1.0)
                    Q.handclap(bus, t0 + 0.008, 0.03 * gain, pan=0.18, seed=seed + 500 + b0 + bb, tone=0.9)
        if 'shaker' in layers:
            for s in range(16):
                t0 = g.t(b0 + s / 4)
                if ok(t0): Q.shaker(bus, t0, 0.010 * gain * (1.0, 0.45, 0.75, 0.45)[s % 4], pan=0.35, seed=seed + b0 * 4 + s)
    if mel and 'melody' in layers:
        mb = mel_bus or bus; m0 = bar0 if mel_bar0 is None else mel_bar0
        for (b, d, nn) in mel:
            t0 = g.t(m0 * 4 + b)
            if not ok(t0): continue
            mb.add(Z.music_box(nf(nn), 1.8, 1.0), t0, 0.06 * gain, pan=0.12)
            mb.add(Z.chip_note(nf(nn), g.d(min(d, 1.0) * 0.8), 'pulse', duty=0.25, a=0.004, d=0.08, s=0.4, r=0.05), t0, 0.010 * gain, pan=-0.1)

def ring_chord(bus, t, chord=CH_BB_END, gain=1.0, d=4.5, seed=0):
    """the last chord, let ring: a slow uke roll + a soft bass root."""
    name, tones, root = chord
    uke_strum(bus, t, tones, 0.16 * gain, False, d=d, spread=0.045, seed=seed, bright=0.6)
    bus.add(Z.chip_note(mtof(root), d * 0.8, 'sine', a=0.01, d=1.0, s=0.5, r=0.8), t, 0.12 * gain)
