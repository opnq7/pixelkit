"""GPT 拆件 → 像素木偶 4 秒测试：呼吸、眨眼、看 → 转头、欢呼、吓一跳。
python rig_test.py [拆件目录]   默认 工具包/素材库/角色/claude_gpt拆件（里面要有 parts.png）；输出写进 _work/puppet_test/"""
import sys, os, math, subprocess, numpy as np, cv2
_HERE = os.path.dirname(os.path.abspath(__file__)); _PROJ = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
_SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_PROJ, '工具包', '素材库', '角色', 'claude_gpt拆件')
_OUT = os.path.join(_PROJ, '_work', 'puppet_test'); os.makedirs(_OUT, exist_ok=True)
from pixelkit import puppet as P
from pixelkit.perform import breath_px, on_twos, wobble, squash_about
from pixelkit.anim import ease_io, ease_out3, back_out, clamp01
from pixelkit.characters import claude as CL

HEAD_W = 46                       # 目标：头宽 46 px（和代码版 Claude 的 44 差不多）
NAMES = ['head', 'antenna', 'torso', 'armL', 'armR', 'handL', 'handR', 'legL', 'legR']
# GPT 拆件之间的相对大小不可靠 → 以全身图的比例为准，逐件微调（相对 head 的缩放）
FUDGE = dict(head=1.0, antenna=0.62, torso=0.86, armL=0.62, armR=0.62, handL=0.62, handR=0.62, legL=0.6, legR=0.6)

im = P.key_out(P.load_rgba(os.path.join(_SRC, 'parts.png')))
raw = P.split_parts(im)
assert len(raw) == 9, len(raw)
s0 = HEAD_W / raw[0]['box'][2]
pal = None
parts_px = {}
smalls = []
for n, r in zip(NAMES, raw):
    smalls.append((n, P._down(r['rgba'], s0 * FUDGE[n])))
pal = P.build_palette([P.clean_orphans(s) for _, s in smalls], 28)
OUT = (52, 36, 56)
for n, s in smalls:
    parts_px[n] = P.add_outline(P.quantize(P.clean_orphans(s), pal), OUT)

def fr(n, fx, fy):
    h, w = parts_px[n].shape[:2]
    return (int(round(fx * (w - 1))), int(round(fy * (h - 1))))

# ---- 屏幕位置（头部里最大的深色连通区）
hd = parts_px['head']
lum = hd[..., :3].astype(int).sum(-1)
dark = ((lum < 120) & (hd[..., 3] > 0)).astype(np.uint8)
n_, lab, st, _ = cv2.connectedComponentsWithStats(dark, 4)
k = 1 + np.argmax(st[1:, 4])
SX, SY, SW_, SH_ = st[k, :4]

def head_with_face(face='normal', look=(0, 0)):
    a = hd.copy()
    g = CL.EYES.get(face, CL.EYES['normal'])
    gw, gh = len(g[0]), len(g)
    gap = 4
    ex0 = SX + (SW_ - (2 * gw + gap)) // 2 + look[0]
    ey0 = SY + (SH_ - gh) // 2 + look[1]
    lit = np.zeros(a.shape[:2], bool)
    cols = {'#': CL.EYE, 'h': CL.EYE_HI, 'l': CL.EYE_LO}
    for side in (0, 1):
        for yy, row in enumerate(g):
            row = row[::-1] if side else row
            for xx, ch in enumerate(row):
                if ch in cols:
                    X, Y = ex0 + side * (gw + gap) + xx, ey0 + yy
                    if SX <= X < SX + SW_ and SY <= Y < SY + SH_:
                        a[Y, X, :3] = np.array(cols[ch], np.uint8)[:3] if len(cols[ch]) >= 3 else cols[ch]
                        lit[Y, X] = True
    # 暖色光晕：亮像素周围一圈
    ring = cv2.dilate(lit.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~lit & (dark > 0)
    a[ring, :3] = np.array(CL.HALO, np.uint8)[:3]
    return a

parts = {
    'torso':   P.Part(parts_px['torso'], fr('torso', 0.5, 0.92), None, z=10),
    'legL':    P.Part(parts_px['legL'], fr('legL', 0.5, 0.12), 'torso', fr('torso', 0.30, 0.86), z=5),
    'legR':    P.Part(parts_px['legR'], fr('legR', 0.5, 0.12), 'torso', fr('torso', 0.70, 0.86), z=5),
    'head':    P.Part(hd, fr('head', 0.5, 0.96), 'torso', fr('torso', 0.5, 0.10), z=20),
    'antenna': P.Part(parts_px['antenna'], fr('antenna', 0.5, 0.98), 'head', fr('head', 0.56, 0.04), z=15),
    'armL':    P.Part(parts_px['armL'], fr('armL', 0.5, 0.14), 'torso', fr('torso', 0.13, 0.32), z=12),
    'armR':    P.Part(parts_px['armR'], fr('armR', 0.5, 0.14), 'torso', fr('torso', 0.87, 0.32), z=12),
    'handL':   P.Part(parts_px['handL'], fr('handL', 0.5, 0.35), 'armL', fr('armL', 0.5, 0.90), z=13),
    'handR':   P.Part(parts_px['handR'], fr('handR', 0.5, 0.35), 'armR', fr('armR', 0.5, 0.90), z=13),
}
CW, CH = 140, 130
pup = P.Puppet(parts, 'torso', size=(CW, CH), root_at=(CW // 2, CH - 22))

# ---------------- 表演（全部是 t 的纯函数）
def seg(t, a, b, ease=ease_io):
    return ease(clamp01((t - a) / (b - a)))

def pose(t):
    tq = on_twos(t)
    ang = {}; off = {}
    dy = 0.0; sq = 0.0
    face, look = 'normal', (0, 0)
    # 呼吸（30 fps 连续，1 px）
    off['head'] = (0, breath_px(t))
    # 眨眼
    for tb in (0.55, 3.85):
        u = t - tb
        if 0 <= u < 0.06: face = 'half'
        elif 0.06 <= u < 0.12: face = 'blink'
        elif 0.12 <= u < 0.18: face = 'blink1'
    # 1.0 眼睛先看右 → 1.15 头再跟着转（过冲 → 回稳）
    if tq >= 1.0: look = (2, 0)
    hturn = 5 * back_out(clamp01((tq - 1.15) / 0.25)) if tq >= 1.15 else 0
    hturn *= 1 - seg(tq, 1.7, 1.9)
    ang['head'] = hturn
    # 1.7 欢呼：预备（下蹲、手往前收）→ 双手甩上去（过冲）→ 跳 → 落地压扁 → 挥两下 → 放下
    up = 0.0
    if 1.7 <= tq < 1.84:
        u = seg(tq, 1.7, 1.84); dy += 2 * u; sq += 0.10 * u; up = -12 * u
    elif tq >= 1.84:
        up = 135 * back_out(clamp01((tq - 1.84) / 0.2), 1.6) * (1 - seg(tq, 2.65, 2.95))
        hop = math.sin(math.pi * clamp01((tq - 1.86) / 0.36)) if tq < 2.22 else 0
        dy -= 9 * hop
        if 2.22 <= tq < 2.34: sq += 0.14 * (1 - seg(tq, 2.22, 2.34)); dy += 1
        if 2.34 <= tq < 2.65: up += 10 * math.sin((tq - 2.34) * 2 * math.pi * 4)
    if 1.84 <= tq < 2.8: face = 'happy'
    ang['armL'] = up; ang['armR'] = -up
    ang['handL'] = -0.3 * up * 0.2; ang['handR'] = 0.3 * up * 0.2
    # 3.0 吓一跳：眼睛瞪大 → 蹲 2 帧 → 跳起拉长、手乱甩 → 落地压扁 → 回稳
    if tq >= 2.98:
        face = 'wideL' if tq < 3.7 else face
        if tq < 3.06: dy += 2; sq += 0.12
        elif tq < 3.36:
            u = (tq - 3.06) / 0.30; dy -= 12 * math.sin(math.pi * u); sq -= 0.16 * math.sin(math.pi * u)
            fl = 55 + 20 * math.sin(u * 2 * math.pi * 2)
            ang['armL'] = fl; ang['armR'] = -fl
        elif tq < 3.5:
            sq += 0.16 * (1 - seg(tq, 3.36, 3.5))
            ang['armL'] = 55 * (1 - seg(tq, 3.36, 3.6)); ang['armR'] = -ang['armL']
        else:
            ang['armL'] = 55 * (1 - seg(tq, 3.36, 3.6)); ang['armR'] = -ang['armL']
    # 天线：头动、落地时晃（弹簧）
    ang['antenna'] = -0.8 * hturn + wobble(t, 1.15, 8) + wobble(t, 2.22, 10) + wobble(t, 3.06, 12) + wobble(t, 3.36, 10)
    # 腿：跳起时微微收
    if dy < -3:
        ang['legL'] = 6; ang['legR'] = -6
    return ang, off, int(round(dy)), sq, face, look

# ---------------- 画面：320×180 世界，×6 → 1920×1080
WW, WH, S = 320, 180, 6
def background():
    bg = np.zeros((WH, WW, 3), np.uint8)
    for y in range(WH):
        k = y / WH
        bg[y] = (np.array([46, 38, 66]) * (1 - k) + np.array([70, 52, 84]) * k).astype(np.uint8)
    bg[132:] = (58, 44, 66)
    bg[132] = (88, 66, 92)
    # 左上暖光
    yy, xx = np.mgrid[0:WH, 0:WW]
    g = np.clip(1 - np.hypot(xx - 90, yy - 40) / 170, 0, 1) ** 2
    bg = np.clip(bg + (g[..., None] * np.array([60, 36, 18])), 0, 255).astype(np.uint8)
    return bg
BG = background()
FEET_Y = 132
def frame(t):
    ang, off, dy, sq, face, look = pose(t)
    parts['head'].rgba = head_with_face(face, look)
    a, E = pup.render(ang, off)
    if abs(sq) > 1e-3:
        a, E, ox, oy = squash_about(a, E, sq, CW / 2, CH - 22 + 10)
    else:
        ox = oy = 0
    img = BG.copy()
    # 接触阴影（跳起来变小变淡）
    h = max(0, -dy)
    rw = max(6, int(22 - h * 0.8))
    sh = np.zeros((WH, WW), np.uint8)
    cv2.ellipse(sh, (WW // 2, FEET_Y + 1), (rw, 3), 0, 0, 360, 255, -1)
    m = sh > 0
    img[m] = (img[m] * (0.55 + 0.03 * h)).clip(0, 255).astype(np.uint8)
    x0 = WW // 2 - CW // 2 + ox
    y0 = FEET_Y - (CH - 22 + 10) + dy + oy
    hh, ww = a.shape[:2]
    for yy in range(hh):
        Y = y0 + yy
        if not (0 <= Y < WH): continue
        row = a[yy]; mm = row[:, 3] > 0
        xs = np.arange(ww) + x0
        ok = mm & (xs >= 0) & (xs < WW)
        img[Y, xs[ok]] = row[ok, :3]
    return np.repeat(np.repeat(img, S, 0), S, 1)

if __name__ == '__main__':
    fps, dur = 30, 4.2
    out = os.path.join(_OUT, 'rig_test.mp4')
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WW*S}x{WH*S}',
                          '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out],
                         stdin=subprocess.PIPE)
    shots = []
    for i in range(int(fps * dur)):
        t = i / fps
        f = frame(t)
        p.stdin.write(f.tobytes())
        if i in (0, 17, 36, 54, 60, 66, 74, 92, 96, 102):
            shots.append(cv2.resize(f[180:900, 540:1380], (420, 360), interpolation=cv2.INTER_NEAREST))
    p.stdin.close(); p.wait()
    sheet = np.concatenate([np.concatenate(shots[:5], 1), np.concatenate(shots[5:10], 1)], 0)
    cv2.imencode('.png', sheet[..., ::-1])[1].tofile(os.path.join(_OUT, 'rig_sheet.png'))
    print('wrote', out)
