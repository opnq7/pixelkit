"""pixelkit.fonts - cross-platform resolver for the *smooth* (non-pixel) fonts used by titles / credits.

The pixel fonts (zh12 / zh10 / zh8 / silk / p2p) ship in assets/fonts and are loaded by core.font().
Title cards and credits use smooth serif / sans faces that used to be hard-coded Linux paths
(/usr/share/fonts/...). This module maps them to roles and tries, in order:
  1. assets/fonts/smooth/<file>   (bundled with the kit - drop static OFL files here to pin the look)
  2. the original Linux path      (old render boxes)
  3. Windows system fonts         (C:/Windows/Fonts and the per-user font folder)

    from pixelkit import fonts
    f = fonts.truetype('serifb', 96)          # by role
    f = fonts.truetype(('/usr/share/fonts/google-noto-cjk/NotoSerifCJK-Bold.ttc', 2), 96)   # legacy spec still works
"""
import os, functools
from PIL import ImageFont

KIT_FONTS = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts'))
WIN = [os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts'),
       os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts')]

# role -> candidates: (file or absolute path, ttc index, variable-font weight name or None)
ROLES = {
    'serifb': [('smooth/NotoSerifSC-Bold.otf', 0, None),
               ('/usr/share/fonts/google-noto-cjk/NotoSerifCJK-Bold.ttc', 2, None),
               ('NotoSerifSC-VF.ttf', 0, 'Bold'),
               ('Source Han Serif SC Heavy (TrueType).ttf', 0, None),
               ('STZHONGS.TTF', 0, None), ('simsun.ttc', 0, None)],
    'serif':  [('smooth/NotoSerifSC-Medium.otf', 0, None),
               ('/usr/share/fonts/google-noto-cjk/NotoSerifCJK-Medium.ttc', 2, None),
               ('NotoSerifSC-VF.ttf', 0, 'Medium'),
               ('STSONG.TTF', 0, None), ('simsun.ttc', 0, None)],
    'it':     [('smooth/georgiai.ttf', 0, None), ('/usr/share/fonts/msttcore/georgiai.ttf', 0, None),
               ('georgiai.ttf', 0, None)],
    'itb':    [('smooth/georgiaz.ttf', 0, None), ('/usr/share/fonts/msttcore/georgiaz.ttf', 0, None),
               ('georgiaz.ttf', 0, None)],
    'sans':   [('smooth/NotoSansSC-Medium.otf', 0, None),
               ('/usr/share/fonts/google-noto-cjk/NotoSansSC-Medium.otf', 0, None),
               ('Noto Sans SC Medium (TrueType).otf', 0, None), ('NotoSansSC-VF.ttf', 0, 'Medium'),
               ('msyh.ttc', 0, None)],
    'sansl':  [('smooth/NotoSansSC-Light.otf', 0, None),
               ('/usr/share/fonts/google-noto-cjk/NotoSansSC-Light.otf', 0, None),
               ('NotoSansSC-VF.ttf', 0, 'Light'), ('msyhl.ttc', 0, None), ('Dengl.ttf', 0, None)],
}

# legacy absolute paths -> role (so old (path, index) tuples keep working everywhere)
_LEGACY = {}
for _role, _cands in ROLES.items():
    for _f, _i, _v in _cands:
        if _f.startswith('/'):
            _LEGACY.setdefault(_f, _role)


def _locate(name):
    if os.path.isabs(name):
        return name if os.path.exists(name) else None
    p = os.path.join(KIT_FONTS, name)
    if os.path.exists(p):
        return p
    for d in WIN:
        p = os.path.join(d, name)
        if d and os.path.exists(p):
            return p
    return None


@functools.lru_cache(maxsize=None)
def resolve(role):
    """-> (path, index, variation) for a role; raises if nothing is installed."""
    for f, i, var in ROLES[role]:
        p = _locate(f)
        if p:
            return p, i, var
    raise OSError(f'pixelkit.fonts: no font found for role {role!r}; put one in {KIT_FONTS}/smooth/')


@functools.lru_cache(maxsize=256)
def truetype(spec, size):
    """spec = role name ('serifb', 'serif', 'it', 'itb', 'sans', 'sansl') or a legacy (path, index) tuple."""
    if isinstance(spec, tuple):
        path, idx = spec[0], spec[1]
        if os.path.exists(path):
            return ImageFont.truetype(path, size, index=idx)
        role = _LEGACY.get(path)
        if role is None:
            raise OSError(f'font not found and no role mapping: {path}')
        spec = role
    path, idx, var = resolve(spec)
    f = ImageFont.truetype(path, size, index=idx)
    if var:
        try:
            f.set_variation_by_name(var)
        except (OSError, ValueError):
            pass
    return f
