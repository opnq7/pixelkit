"""pixelkit.persp - one-point-perspective "diorama box" rooms.

Coordinates
  screen  (x, y) in native canvas pixels (e.g. 480x270)
  world   (X, Y, Z): X right, Y down, Z = depth from camera.  The back wall sits at Z = D and
          is drawn 1:1, i.e. a point on the back wall at screen (x, y) has X = x - vx, Y = y - vy.
          Projection:  x = vx + X * D / Z,  y = vy + Y * D / Z    (scale s = D / Z)

A BoxRoom is defined by its back-wall rectangle on screen + the vanishing point; the floor,
ceiling and side walls follow.  surfaces(f) returns per-pixel surface ids and 3D positions at
f x canvas resolution, which the material painter and the light rig both use.
"""
import numpy as np

BACK, FLOOR, CEIL, LEFT, RIGHT, NONE = 0, 1, 2, 3, 4, 255

class BoxRoom:
    def __init__(self, W=480, H=270, back=(64, 26, 416, 196), vp=(240, 118), D=400.0):
        self.W, self.H, self.D = W, H, float(D)
        self.vx, self.vy = map(float, vp)
        x0, y0, x1, y1 = back
        self.back = back
        self.Xl, self.Xr = x0 - self.vx, x1 - self.vx     # side walls (world X)
        self.Yc, self.Yf = y0 - self.vy, y1 - self.vy     # ceiling / floor (world Y)
        self._cache = {}

    # --- projection helpers -------------------------------------------------------------
    def project(self, X, Y, Z):
        s = self.D / np.asarray(Z, np.float64)
        return self.vx + np.asarray(X) * s, self.vy + np.asarray(Y) * s

    def unproject_on_Z(self, x, y, Z):
        """screen -> world for points on the plane Z = const (e.g. a mid-ground layer)."""
        s = self.D / Z
        return (np.asarray(x) - self.vx) / s, (np.asarray(y) - self.vy) / s, np.full(np.shape(x), float(Z))

    def scale_at(self, Z):
        return self.D / Z

    def floor_y(self, Z):
        """screen y of the floor line at depth Z (where objects standing at depth Z touch the floor)"""
        return self.vy + self.Yf * self.D / Z

    # --- per pixel surfaces ------------------------------------------------------------------
    def surfaces(self, f=1):
        """returns dict(id, X, Y, Z) arrays of shape (H*f, W*f) (pixel centres)."""
        if f in self._cache: return self._cache[f]
        H, W = int(self.H * f), int(self.W * f)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        x = (xx + 0.5) / f; y = (yy + 0.5) / f
        dx, dy = x - self.vx, y - self.vy
        # scale needed for each plane to pass through this pixel (s>=1 means in front of back wall)
        with np.errstate(divide='ignore', invalid='ignore'):
            sF = np.where(dy > 0, dy / self.Yf, np.inf)
            sC = np.where(dy < 0, dy / self.Yc, np.inf)
            sL = np.where(dx < 0, dx / self.Xl, np.inf)
            sR = np.where(dx > 0, dx / self.Xr, np.inf)
        # the visible surface along a view ray is the one hit first going away from the camera
        # (smallest Z = largest s) among the planes hit in front of the back wall (s >= 1)
        inside = (dx >= self.Xl) & (dx <= self.Xr) & (dy >= self.Yc) & (dy <= self.Yf)
        sid = np.full((H, W), NONE, np.uint8)
        S = np.full((H, W), -np.inf)
        for k, sk in ((FLOOR, sF), (CEIL, sC), (LEFT, sL), (RIGHT, sR)):
            sk = np.where(np.isfinite(sk), sk, -np.inf)
            m = (sk >= 1.0) & (sk > S)
            S[m] = sk[m]; sid[m] = k
        sid[inside] = BACK; S[inside] = 1.0
        Z = self.D / S
        X = dx / S; Y = dy / S
        r = dict(id=sid, X=X, Y=Y, Z=Z, x=x, y=y)
        self._cache[f] = r
        return r

    def uv(self, f=1):
        """texture coordinates per surface in world units:
        back: (X, Y); floor/ceil: (X, Z); left/right walls: (Z, Y)"""
        s = self.surfaces(f)
        u = np.where(np.isin(s['id'], (LEFT, RIGHT)), s['Z'], s['X'])
        v = np.where(np.isin(s['id'], (FLOOR, CEIL)), s['Z'], s['Y'])
        return u, v

    def quad_on_wall(self, wall, a0, a1, b0, b1):
        """screen polygon of a rectangle on a surface.
        back: X in [a0,a1], Y in [b0,b1];  left/right: Z in [a0,a1], Y in [b0,b1];
        floor/ceil: X in [a0,a1], Z in [b0,b1]."""
        if wall == BACK:
            pts = [(a0, b0, self.D), (a1, b0, self.D), (a1, b1, self.D), (a0, b1, self.D)]
        elif wall in (LEFT, RIGHT):
            X = self.Xl if wall == LEFT else self.Xr
            pts = [(X, b0, a0), (X, b0, a1), (X, b1, a1), (X, b1, a0)]
        else:
            Y = self.Yf if wall == FLOOR else self.Yc
            pts = [(a0, Y, b0), (a1, Y, b0), (a1, Y, b1), (a0, Y, b1)]
        return [tuple(map(float, self.project(*p))) for p in pts]
