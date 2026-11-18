"""pixelkit - a small engine for HD-2D style pixel-art story videos (numpy + OpenCV + ffmpeg).

Modules
  core       canvas & drawing primitives, fonts, sprites
  palette    hue-shifted colour ramps (OKLab) + material palettes
  persp      one-point-perspective "diorama box" rooms (analytic per-pixel 3D)
  materials  procedural pixel textures (plaster, carpet, planks, ceiling tiles ...)
  light      2.5D light rig: sun through windows w/ blinds, cast shadows, god rays, point lights
  camera     camera paths, crisp pixel warping at any zoom, layer compositing (parallax + DOF)
  post       bloom, halation, vignette, grain, colour grading presets matched to the reference
  particles  stateless dust motes / sparkles (frame-independent => parallel rendering)
  anim       easing, keyframe tracks, squash & stretch helpers
  ui         HUD, chat / speech bubbles, JRPG dialog box, Win95 windows
  blocks     falling chat-message bricks with heightmap physics
  characters Claude pixel character (expressions, poses, status LED)
  sets       reusable sets (office ...)
  audio      numpy synth, SFX cues, chiptune/e-piano arrangers, mastering chain
  render     stills, contact sheets, parallel chunk rendering, mux & share encode
  qa         measure frames against the reference look (targets in STYLE_GUIDE.md)
"""
__version__ = '0.14'


def _unicode_safe_cv2():
    """On Windows, cv2.imread / cv2.imwrite fail *silently* on non-ASCII paths (our kit lives in
    D:/像素风2d知识/...). Route them through imdecode / imencode so every module and template is safe."""
    try:
        import cv2, numpy as np, os
    except ImportError:
        return
    if getattr(cv2, '_pk_unicode_safe', False):
        return
    _read, _write = cv2.imread, cv2.imwrite

    def imread(path, flags=cv2.IMREAD_COLOR):
        try:
            data = np.fromfile(os.fspath(path), dtype=np.uint8)
        except (OSError, ValueError):
            return None
        return cv2.imdecode(data, flags) if data.size else None

    def imwrite(path, img, params=None):
        path = os.fspath(path)
        ext = os.path.splitext(path)[1] or '.png'
        ok, buf = cv2.imencode(ext, img, params if params is not None else [])
        if not ok:
            raise IOError(f'cv2.imencode failed for {path}')
        buf.tofile(path)
        return True

    cv2.imread, cv2.imwrite = imread, imwrite
    cv2._pk_unicode_safe = True


_unicode_safe_cv2()
