"""Image QA: measure a frame against the reference-video look ("Claude Dreaming").

Targets were measured with OpenCV on 1080p interior frames of the reference.
Use  qa.report(img)  (BGR uint8 or path)  ->  dict + pass/fail string.
"""
import numpy as np, cv2

# metric: (lo, hi)   measured on reference interiors r_3/r_9/r_70/r_13/r_220
REF_TARGETS = dict(
    sat=(115, 155),        # HSV saturation mean (0-255)
    L2=(3, 20),            # Lab L 2nd percentile  -> deep blacks exist
    L50=(80, 105),         # Lab L median           -> overall key (darker than you think)
    L98=(214, 254),        # Lab L 98th percentile  -> bright highlights exist
    colorful=(52, 82),     # Hasler-Suesstrunk colourfulness
    hi_b=(10, 28),         # b* (yellow) of brightest 20%  -> warm highlights
    lo_a=(10, 17),         # a* (magenta) of darkest 20%   -> purple/magenta shadows
    localC=(16, 27),       # mean std of L in 32px blocks  -> texture / micro-contrast
    lightVar=(30, 52),     # std of heavily blurred L      -> big light pools vs dark
)

def metrics(im):
    if isinstance(im, str):
        im = cv2.imread(im)
    im = np.ascontiguousarray(im)
    if im.shape[1] != 1920:   # normalise scale so block metrics are comparable
        im = cv2.resize(im, (1920, int(round(im.shape[0] * 1920 / im.shape[1]))), interpolation=cv2.INTER_NEAREST)
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(float)
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(float); L = lab[:, :, 0]
    b, g, r = [im[:, :, i].astype(float) for i in range(3)]
    rg = r - g; yb = 0.5 * (r + g) - b
    colorful = np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    p2, p50, p98 = np.percentile(L, [2, 50, 98])
    hi = L > np.percentile(L, 80); lo = L < np.percentile(L, 20)
    h, w = L.shape
    blk = L[:h // 32 * 32, :w // 32 * 32].reshape(h // 32, 32, w // 32, 32).std(axis=(1, 3)).mean()
    big = cv2.GaussianBlur(L, (0, 0), 60).std()
    return dict(sat=hsv[:, :, 1].mean(), L2=p2, L50=p50, L98=p98, colorful=colorful,
                hi_b=lab[:, :, 2][hi].mean() - 128, lo_a=lab[:, :, 1][lo].mean() - 128,
                localC=blk, lightVar=big)

def report(im, name='frame', targets=REF_TARGETS, verbose=True):
    m = metrics(im)
    parts = []; npass = 0
    for k, (lo, hi) in targets.items():
        v = m[k]; ok = lo <= v <= hi; npass += ok
        flag = 'ok' if ok else ('LOW' if v < lo else 'HIGH')
        parts.append(f"{k} {v:6.1f} [{lo}-{hi}] {flag}")
    s = f"{name}: {npass}/{len(targets)} in range\n  " + "\n  ".join(parts)
    if verbose: print(s)
    return m, npass


def flicker_check(path, thresh=4.0, max_flips=2, win=1.0, scale=(96, 54)):
    """v0.13f photosensitivity / strobe lint: whole-frame luma must not flip direction more than `max_flips` times
    with |Δ| > thresh (0..255) inside any `win`-second window.  Returns [(t_start, flips)] of offending windows."""
    import cv2, numpy as np
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 30
    L = []
    while True:
        ok, f = cap.read()
        if not ok: break
        L.append(cv2.resize(f, scale).astype(np.float32).mean())
    d = np.diff(np.array(L)); n = int(fps * win); bad = []
    for i in range(0, max(0, len(d) - n), max(1, n // 2)):
        w = d[i:i + n]; big = np.abs(w) > thresh
        flips = int(np.sum(big[1:] & (np.sign(w[1:]) != np.sign(w[:-1]))))
        if flips > max_flips: bad.append((round(i / fps, 2), flips))
    return bad

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == 'flicker':
        r = flicker_check(sys.argv[2]); print('FLICKER', r if r else 'ok')
