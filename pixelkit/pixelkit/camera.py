"""pixelkit.camera - 2D camera over a native-resolution pixel world.

* World art lives on a native canvas (default 480x270); the camera zooms/pans over it and the
  result is resampled to the output (default 1920x1080, i.e. 4 output px per native px at zoom 1).
* warp_crisp keeps pixels perfectly square at ANY zoom (nearest upscale to an integer factor, then
  a slight linear downscale = clean 1-px antialiased pixel edges, no shimmering).
* warp_smooth is for soft data (light maps, bloom, god rays) computed at f x native resolution.
* parallax p > 1 makes a layer react more strongly to camera moves (foreground), p < 1 less.
"""
import math
import numpy as np, cv2
from .anim import Track

class Cam:
    def __init__(self, zoom=1.0, cx=None, cy=None, sx=0.0, sy=0.0, W=480, H=270, OW=1920, OH=1080):
        self.W, self.H, self.OW, self.OH = W, H, OW, OH
        self.zoom = zoom
        self.cx = W / 2 if cx is None else cx
        self.cy = H / 2 if cy is None else cy
        self.sx, self.sy = sx, sy

    @property
    def s(self):                       # output px per native px
        return self.OW / self.W * self.zoom

    def clamp(self):
        hw, hh = self.W / (2 * self.zoom), self.H / (2 * self.zoom)
        self.cx = min(max(self.cx, hw), self.W - hw)
        self.cy = min(max(self.cy, hh), self.H - hh)
        return self

    def layer(self, p=1.0):
        """camera as seen by a parallax layer (p=1: same)."""
        if abs(p - 1) < 1e-6: return self
        return Cam(self.zoom ** p, self.W / 2 + (self.cx - self.W / 2) * p, self.H / 2 + (self.cy - self.H / 2) * p,
                   self.sx * p, self.sy * p, self.W, self.H, self.OW, self.OH)

    def w2o(self, x, y):
        s = self.s
        return (np.asarray(x) - self.cx) * s + self.OW / 2 + self.sx, (np.asarray(y) - self.cy) * s + self.OH / 2 + self.sy

    def o2w(self, X, Y):
        s = self.s
        return (np.asarray(X) - self.OW / 2 - self.sx) / s + self.cx, (np.asarray(Y) - self.OH / 2 - self.sy) / s + self.cy

    def w2ui(self, x, y, ui_scale=3):
        X, Y = self.w2o(x, y)
        return X / ui_scale, Y / ui_scale

    def view(self):
        """visible native rect (x0, y0, x1, y1)"""
        x0, y0 = self.o2w(0, 0); x1, y1 = self.o2w(self.OW, self.OH)
        return float(x0), float(y0), float(x1), float(y1)

    def matrix(self, f=1):
        s = self.s
        return np.array([[s / f, 0, (0.5 / f - self.cx) * s + self.OW / 2 + self.sx - 0.5],
                         [0, s / f, (0.5 / f - self.cy) * s + self.OH / 2 + self.sy - 0.5]], np.float32)

    def is_identity(self):
        return (abs(self.zoom - 1) < 1e-5 and abs(self.cx - self.W / 2) < 1e-4 and abs(self.cy - self.H / 2) < 1e-4
                and abs(self.sx) < 1e-4 and abs(self.sy) < 1e-4)

def warp_crisp(img, cam, f=1, border=cv2.BORDER_REPLICATE):
    """img: (H*f, W*f, C) any dtype -> (OH, OW, C) with square pixels at any zoom."""
    OW, OH = cam.OW, cam.OH
    sf = cam.s / f                                      # output px per source px
    if (cam.is_identity() and abs(sf - round(sf)) < 1e-6 and img.shape[1] == cam.W * f
            and img.shape[0] == cam.H * f):           # whole-set shortcut only when the set IS the frame
        return cv2.resize(img, (OW, OH), interpolation=cv2.INTER_NEAREST)
    hw, hh = OW / (2 * cam.s), OH / (2 * cam.s)
    pad_x, pad_y = abs(cam.sx) / cam.s, abs(cam.sy) / cam.s
    X0 = int(math.floor((cam.cx - hw - pad_x) * f)) - 2; X1 = int(math.ceil((cam.cx + hw + pad_x) * f)) + 2
    Y0 = int(math.floor((cam.cy - hh - pad_y) * f)) - 2; Y1 = int(math.ceil((cam.cy + hh + pad_y) * f)) + 2
    H, W = img.shape[:2]
    pad = max(0, -X0, -Y0, X1 - W, Y1 - H)
    src = img if pad == 0 else cv2.copyMakeBorder(img, pad, pad, pad, pad, border)
    crop = src[Y0 + pad:Y1 + pad, X0 + pad:X1 + pad]
    k = max(1, int(math.ceil(sf - 1e-6)))
    up = cv2.resize(crop, (crop.shape[1] * k, crop.shape[0] * k), interpolation=cv2.INTER_NEAREST) if k > 1 else crop
    a = sf / k
    M = np.array([[a, 0, (X0 / f + 0.5 / (f * k) - cam.cx) * cam.s + OW / 2 + cam.sx - 0.5],
                  [0, a, (Y0 / f + 0.5 / (f * k) - cam.cy) * cam.s + OH / 2 + cam.sy - 0.5]], np.float32)
    out = cv2.warpAffine(up, M, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=border)
    if out.ndim == 2 and img.ndim == 3: out = out[..., None]
    return out

def warp_smooth(img, cam, f=2, border=cv2.BORDER_REPLICATE):
    """soft data at f x native -> output (linear)."""
    out = cv2.warpAffine(img, cam.matrix(f), (cam.OW, cam.OH), flags=cv2.INTER_LINEAR, borderMode=border)
    if out.ndim == 2 and img.ndim == 3: out = out[..., None]
    return out

def warp_smooth_cubic(img, cam, f=2):
    return cv2.warpAffine(img, cam.matrix(f), (cam.OW, cam.OH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

class CamRig:
    """keyframed camera: zoom (log-interpolated), centre (cx, cy) and an optional shake function.
        rig = CamRig(zoom=[(0, 3.2), (5, 2.3, 'io')], center=[(0, (250, 130)), (8.4, (240, 135), 'io3')])
        cam = rig(t)
    """
    def __init__(self, zoom, center, shake_fn=None, W=480, H=270, OW=1920, OH=1080, clamp=True):
        self.z = Track(zoom, log=True); self.c = Track(center)
        self.shake_fn, self.clamp = shake_fn, clamp
        self.dims = (W, H, OW, OH)

    def __call__(self, t):
        W, H, OW, OH = self.dims
        cx, cy = self.c(t)
        cam = Cam(self.z(t), cx, cy, 0, 0, W, H, OW, OH)
        if self.clamp: cam.clamp()
        if self.shake_fn:
            sx, sy = self.shake_fn(t); cam.sx, cam.sy = sx, sy
        return cam
