"""paint a BoxRoom shell (walls / floor / ceiling) with procedural pixel materials."""
import numpy as np
from ..persp import BACK, FLOOR, CEIL, LEFT, RIGHT, NONE
from .. import materials as M
from ..palette import ramp

DEFAULT = dict(
    back=dict(base='#d9c2a2', mat='plaster', mottle=0.45),
    left=dict(base='#d2b998', mat='plaster', mottle=0.45),
    right=dict(base='#d6bf9e', mat='plaster', mottle=0.45),
    floor=dict(base='#56707c', mat='carpet', tile=34.0),
    ceil=dict(base='#d4ccc0', mat='ceiling', tile=30.0),
    base_board=dict(base='#7b5a45', h=5.0),
)

def paint_shell(room, spec=None, seed=0):
    """returns RGBA uint8 (H, W, 4) albedo of the empty room + per-surface ids."""
    spec = {**DEFAULT, **(spec or {})}
    S = room.surfaces(1); sid = S['id']
    u, v = room.uv(1)
    H, W = sid.shape
    yy, xx = np.mgrid[0:H, 0:W]
    out = np.zeros((H, W, 4), np.uint8)
    for key, k in (('back', BACK), ('left', LEFT), ('right', RIGHT), ('floor', FLOOR), ('ceil', CEIL)):
        sp = spec[key]; m = sid == k
        if not m.any(): continue
        rp = ramp(sp['base'], 6)
        if sp['mat'] == 'plaster':
            t = M.plaster(u, v, 3.0, seed + k, sp.get('mottle', 0.5), sp.get('speck', 0.0))
        elif sp['mat'] == 'carpet':
            t = M.carpet_tiles(u, v, 2.6, sp.get('tile', 34.0), seed + 3)
        elif sp['mat'] == 'ceiling':
            t = M.ceiling_tiles(u, v, 3.4, sp.get('tile', 30.0), seed + 9)
        elif sp['mat'] == 'planks':
            t = M.planks(u, v, sp.get('t0', 3.0), sp.get('pw', 9.0), sp.get('pl', 60.0), seed + 5, along=sp.get('along', 'v'))
        else:
            t = np.full(u.shape, 3.0)
        img = M.apply_ramp(t, rp, xx, yy, True, band=sp.get('band', 2.6))
        out[m] = img[m]
    # baseboards: a strip just above the floor on back / side walls
    bb = spec['base_board']; rb = ramp(bb['base'], 4)
    Y = S['Y']
    for k in (BACK, LEFT, RIGHT):
        m = (sid == k) & (Y > room.Yf - bb['h'])
        top = (sid == k) & (Y > room.Yf - bb['h']) & (Y <= room.Yf - bb['h'] + 1.0)
        out[m] = rb[1]; out[top] = rb[3]
    return out, sid
