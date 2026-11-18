"""pixelkit.anim - easing curves, keyframe tracks and small motion helpers.

Everything is a pure function of time t (seconds) so frames can be rendered in any order /
in parallel workers.  Typical use:

    zoom = Track([(0, 3.2), (1.6, 3.2), (3.0, 3.35, 'io'), (5.0, 2.3, 'io')], log=True)
    z = zoom(t)
"""
import math
import numpy as np

# ------------------------------------------------------------------ easing (u in 0..1)
def clamp01(u): return 0.0 if u <= 0 else (1.0 if u >= 1 else float(u))
def lin(u): return clamp01(u)
def ease_in(u): u = clamp01(u); return u * u
def ease_out(u): u = clamp01(u); return 1 - (1 - u) ** 2
def ease_in3(u): u = clamp01(u); return u ** 3
def ease_out3(u): u = clamp01(u); return 1 - (1 - u) ** 3
def ease_io(u): u = clamp01(u); return u * u * (3 - 2 * u)
def ease_io3(u):
    u = clamp01(u); return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2
def ease_io5(u):
    u = clamp01(u); return 16 * u ** 5 if u < 0.5 else 1 - (-2 * u + 2) ** 5 / 2
def back_out(u, s=1.70158):
    u = clamp01(u) - 1; return u * u * ((s + 1) * u + s) + 1
def back_in(u, s=1.70158):
    u = clamp01(u); return u * u * ((s + 1) * u - s)
def elastic_out(u, period=0.32):
    u = clamp01(u)
    if u in (0.0, 1.0): return u
    return 2 ** (-10 * u) * math.sin((u - period / 4) * (2 * math.pi) / period) + 1
def bounce_out(u):
    u = clamp01(u); n1, d1 = 7.5625, 2.75
    if u < 1 / d1: return n1 * u * u
    if u < 2 / d1: u -= 1.5 / d1; return n1 * u * u + 0.75
    if u < 2.5 / d1: u -= 2.25 / d1; return n1 * u * u + 0.9375
    u -= 2.625 / d1; return n1 * u * u + 0.984375
def hold(u): return 0.0 if u < 1 else 1.0

EASE = dict(lin=lin, i=ease_in, o=ease_out, i3=ease_in3, o3=ease_out3, io=ease_io, io3=ease_io3,
            io5=ease_io5, back=back_out, backin=back_in, elastic=elastic_out, bounce=bounce_out, hold=hold)

def smoothstep(e0, e1, x):
    if e1 == e0: return 1.0 if x >= e1 else 0.0
    return ease_io((x - e0) / (e1 - e0))

def ramp(t, t0, t1, ease='lin'):
    """0 before t0, 1 after t1, eased in between."""
    if t1 <= t0: return 1.0 if t >= t1 else 0.0
    return EASE[ease]((t - t0) / (t1 - t0))

def env(t, t0, t1, a=0.1, r=0.1, ease='io'):
    """1 inside [t0,t1] with attack a / release r ramps."""
    return min(ramp(t, t0, t0 + a, ease), 1 - ramp(t, t1 - r, t1, ease)) if t1 > t0 else 0.0

def lerp(a, b, k): return a + (b - a) * k


def push_zoom(t, t0, t1, z0, z1, v0=0.0):
    """an accelerating camera push that LANDS (zero speed) on z1 at t1 - log-zoom cubic Hermite.
    v0 = the incoming speed in log-zoom per second (keep a slow drift continuous into the push).
    e.g. into a framed photo before a dissolve:  z = push_zoom(t, 19.3, 20.85, 1.12, pi.fill_cam()[0], v0=0.09)"""
    import math as _m
    D = max(t1 - t0, 1e-6); u = clamp01((t - t0) / D)
    l0, l1 = _m.log(z0), _m.log(z1); v = v0 * D
    return _m.exp((2*u**3 - 3*u**2 + 1) * l0 + (u**3 - 2*u**2 + u) * v + (-2*u**3 + 3*u**2) * l1)


def screen_follow(z, z0, z1, a, b):
    """move a camera centre from a (at zoom z0) to b (at zoom z1) in SCREEN space while zooming - no swing."""
    w = clamp01(((1 / z0) - (1 / z)) / ((1 / z0) - (1 / z1))) if z1 != z0 else 1.0
    return a + (b - a) * w

# ------------------------------------------------------------------ keyframe track
class Track:
    """keys: list of (t, value[, ease]) - ease applies to the segment ENDING at that key.
    value may be a number or a tuple (interpolated component-wise).  log=True interpolates in
    log space (use for zoom so perceived speed is even)."""
    def __init__(self, keys, log=False, default_ease='io'):
        self.keys = sorted([(k[0], k[1], k[2] if len(k) > 2 else default_ease) for k in keys], key=lambda k: k[0])
        self.log = log

    def __call__(self, t):
        ks = self.keys
        if t <= ks[0][0]: return ks[0][1]
        if t >= ks[-1][0]: return ks[-1][1]
        for i in range(1, len(ks)):
            if t < ks[i][0]:
                t0, v0, _ = ks[i - 1]; t1, v1, e = ks[i]
                u = EASE[e]((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
                if isinstance(v0, (tuple, list)):
                    return tuple(self._mix(a, b, u) for a, b in zip(v0, v1))
                return self._mix(v0, v1, u)
        return ks[-1][1]

    def _mix(self, a, b, u):
        if self.log: return math.exp(math.log(a) + (math.log(b) - math.log(a)) * u)
        return a + (b - a) * u

# ------------------------------------------------------------------ motion helpers
def hop(t, t0, height=6.0, dur=0.32):
    """parabolic hop offset (negative = up) starting at t0."""
    u = (t - t0) / dur
    if u <= 0 or u >= 1: return 0.0
    return -height * 4 * u * (1 - u)

def squash_curve(t, t0, amount=0.25, dur=0.28, freq=2.2):
    """damped squash value (positive = squash) for an impact at t0 (use with core.squash)."""
    u = t - t0
    if u < 0 or u > dur * 3: return 0.0
    return amount * math.exp(-u / dur * 2.2) * math.cos(u / dur * math.pi * freq)

def anticip(t, t0, amount=0.15, dur=0.10):
    """anticipation squash before a hop at t0 (squash during [t0-dur, t0])."""
    u = (t - (t0 - dur)) / dur
    if u <= 0 or u >= 1: return 0.0
    return amount * math.sin(u * math.pi)

def shake(t, t0, amp=6.0, dur=0.35, freq=31.0, seed=0):
    """decaying 2D camera shake (output px)."""
    u = t - t0
    if u < 0 or u > dur: return 0.0, 0.0
    k = (1 - u / dur) ** 2 * amp
    return (k * math.sin(u * freq * 2 * math.pi + seed * 1.7) * 0.9 + k * 0.3 * math.sin(u * 53 + seed),
            k * math.cos(u * freq * 1.37 * 2 * math.pi + seed * 0.9))

def breathe(t, period=3.2, amp=1.0, phase=0.0):
    return amp * math.sin(2 * math.pi * (t / period + phase))

def blink_at(t, times, dur=0.12):
    """True while blinking (times = list of blink start times)."""
    return any(0 <= t - b < dur for b in times)

def auto_blinks(t0, t1, mean=3.1, seed=0):
    rng = np.random.default_rng(seed); out = []; t = t0 + rng.uniform(0.5, 1.5)
    while t < t1:
        out.append(t); t += mean * rng.uniform(0.6, 1.4)
    return out

def counter(t, t0, t1, v0, v1, ease='i3'):
    return int(round(lerp(v0, v1, ramp(t, t0, t1, ease))))

# ------------------------------------------------------------------ typewriter timing (shared by picture + voice)
PAUSES = {'，': 0.22, ',': 0.18, '、': 0.14, '。': 0.30, '.': 0.22, '…': 0.10, '？': 0.18, '?': 0.14, '！': 0.18, '!': 0.14,
          '：': 0.16, ':': 0.12, ' ': 0.0}

def type_times(text, t0, cps=14.0, pauses=None, beats=None):
    """start time of every character of a typewriter line: 1/cps per char + a pause AFTER punctuation.
    beats: {char_index: extra seconds} - an acted beat after that character (v0.11, e.g. '已提交。|周末快乐。').
    Use the same list for the dialog box (typed_n) and the voice blips (cues.voice_line(times=...))."""
    p = PAUSES if pauses is None else pauses
    out = []; t = t0
    for i, ch in enumerate(text):
        out.append(t)
        t += 1.0 / cps + p.get(ch, 0.0) + (beats.get(i, 0.0) if beats else 0.0)
    return out

def typed_n(t, text, t0, cps=14.0, pauses=None):
    """how many characters of `text` are visible at time t (typewriter with punctuation pauses)."""
    if t < t0: return 0
    ts = type_times(text, t0, cps, pauses)
    n = 0
    for tc in ts:
        if t >= tc: n += 1
        else: break
    return n

def type_end(text, t0, cps=14.0, pauses=None):
    """time the last character appears."""
    ts = type_times(text, t0, cps, pauses)
    return ts[-1] if ts else t0


# ---------------------------------------------------------------- narration boxes (JRPG dialog timing, from ACT I)
def boxes_prep(boxes, cps=11.0, lint=True):
    """boxes: [dict(t_open, t_close, lines=[dict(t0, zh, en, face, mouth, cps?), ...]), ...]
       fills each line's cps / times (per-char reveal times) / t_end in place; returns boxes."""
    for bx in boxes:
        for ln in bx['lines']:
            ln['cps'] = ln.get('cps', cps)
            ln['times'] = type_times(ln['zh'], ln['t0'], ln['cps'], beats=ln.get('beats'))
            ln['t_end'] = ln['times'][-1] + 1.0 / ln['cps']
    if lint: boxes_lint(boxes)
    return boxes


def read_time(text, base=0.9, per_char=0.12):
    """seconds a viewer needs to READ a line that is already fully visible (bubbles, popups, held lines).
    Rule of thumb from the ACT III v1 review ('the line was cut before I could read it')."""
    n = sum(1 for ch in text if not ch.isspace())
    return base + per_char * n


def boxes_lint(boxes, min_hold=1.0, per_char=0.10, quiet=False):
    """warn when a narration line is replaced / closed before it can be read.
    hold = time the COMPLETE line stays on screen = (next line t0 - 0.25 | box t_close - 0.14) - t_end.
    required = max(min_hold, per_char * chars).  Returns the list of problems [(zh, hold, need)]."""
    bad = []
    for bx in boxes:
        ls = bx['lines']
        for i, ln in enumerate(ls):
            gone = (ls[i + 1]['t0'] - 0.25) if i + 1 < len(ls) else (bx['t_close'] - 0.14)
            hold = gone - ln['t_end']
            need = max(min_hold, per_char * len(ln['zh']))
            if hold < need - 1e-6: bad.append((ln['zh'], round(hold, 2), round(need, 2)))
    if bad and not quiet:
        import sys
        for (zh, h, nd) in bad:
            print(f'[boxes_lint] line held {h:.2f}s < {nd:.2f}s : {zh}', file=sys.stderr)
    return bad


def box_at(t, boxes):
    """active narration box at t -> (box, line, open_k, zh_n, en_n) or None (boxes must be boxes_prep'ed)."""
    for bx in boxes:
        if bx['t_open'] - 0.2 <= t < bx['t_close'] + 0.2:
            k = min(ramp(t, bx['t_open'] - 0.16, bx['t_open'], 'o3'), 1 - ramp(t, bx['t_close'] - 0.14, bx['t_close'], 'lin'))
            ln = None
            for l in bx['lines']:
                if t >= l['t0'] - 0.25: ln = l
            if ln is None: ln = bx['lines'][0]
            if ln.get('beats'):                     # v0.11: acted beats -> reveal both lines by typed progress
                zn = sum(1 for tc in ln['times'] if t >= tc)
                en_n = int(round(len(ln['en']) * zn / max(1, len(ln['zh']))))
            else:
                zn = typed_n(t, ln['zh'], ln['t0'], ln['cps'])
                u = clamp01((t - ln['t0']) / max(0.05, ln['t_end'] - ln['t0']))
                en_n = int(round(len(ln['en']) * u)) if t >= ln['t0'] else 0
            return bx, ln, k, zn, en_n
    return None


def boxes_cut_lint(boxes, cuts, fps=30):
    """warn when a narration box's open (t_open-0.16 .. t_open) or close (t_close-0.14 .. t_close) animation straddles a
    cut - the box would pop up in the last frame(s) of the previous shot.  Rule: t_open >= cut + 0.16."""
    bad = []
    for bx in boxes:
        for c in cuts:
            if bx['t_open'] - 0.16 < c < bx['t_open']: bad.append(('open', bx['t_open'], c))
            if bx['t_close'] - 0.14 < c < bx['t_close'] + 0.5 / fps: bad.append(('close', bx['t_close'], c))
    for (k, tb, c) in bad:
        print(f'[boxes_cut_lint] box {k} at {tb:.2f} straddles the cut at {c:.2f} (open >= cut + 0.16, close <= cut)')
    return bad
