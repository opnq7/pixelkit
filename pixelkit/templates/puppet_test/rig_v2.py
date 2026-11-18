"""GPT 拆件 → 像素木偶 v2（混合绑骨）：刚性、有细节、决定长相的部件（头、天线、躯干、手）用 GPT；
会弯会动的连接部分（手臂、腿）用代码画，明暗按世界光（左上）实时计算，整体只描一圈外轮廓 → 没有拼贴感。
用户反馈 v1「像在拼贴、下半身有点怪」：每个部件各自一圈描边 → 关节处全是线；GPT 躯干是布袋形；整根手臂旋转时 GPT 画的明暗跟着转。

python rig_v2.py [拆件目录]   默认 工具包/素材库/角色/claude_gpt拆件（parts.png，可选 torso.png 覆盖拆件里的躯干）"""
import sys, os, math, subprocess, numpy as np, cv2
_HERE = os.path.dirname(os.path.abspath(__file__)); _PROJ = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
_SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_PROJ, '工具包', '素材库', '角色', 'claude_gpt拆件')
_OUT = os.path.join(_PROJ, '_work', 'puppet_test'); os.makedirs(_OUT, exist_ok=True)
from pixelkit import puppet as P
from pixelkit.perform import breath_px, on_twos, wobble, squash_about, rotsprite, spring_follow
from pixelkit.anim import ease_io, back_out, clamp01
from pixelkit.characters import claude as CL

HEAD_W = 46
OUT = np.array((52, 36, 56), np.uint8)

# ---------------------------------------------------------------- GPT 部件
raw = P.split_parts(P.key_out(P.load_rgba(os.path.join(_SRC, 'parts.png'))))
NAMES = ['head', 'antenna', 'torso', 'armL', 'armR', 'handL', 'handR', 'legL', 'legR']
src = {n: r['rgba'] for n, r in zip(NAMES, raw)}
tp = os.path.join(_SRC, 'torso.png')
if os.path.exists(tp):
    t_parts = P.split_parts(P.key_out(P.load_rgba(tp)))
    src['torso'] = max(t_parts, key=lambda p: p['box'][2] * p['box'][3])['rgba']
s0 = HEAD_W / src['head'].shape[1]
TARGET_W = dict(head=HEAD_W, antenna=None, torso=31, handL=10, handR=10)   # 目标宽度（px）；antenna 按高度
small = {}
for n in ('head', 'antenna', 'torso', 'handL', 'handR'):
    h, w = src[n].shape[:2]
    s = (20 / h) if n == 'antenna' else TARGET_W[n] / w
    small[n] = P.clean_orphans(P._down(src[n], s))
pal = P.build_palette(list(small.values()), 28)
G = {n: P.quantize(a, pal) for n, a in small.items()}

# 从 GPT 躯干取 4 档珊瑚色给代码画的肢体（同一套颜色 → 不像两套美术）
tor = G['torso']; px = tor[tor[..., 3] > 0][:, :3].astype(int)
coral = px[(px[:, 0] > px[:, 1] + 40) & (px[:, 0] > 120)]
cols, cnt = np.unique(coral, axis=0, return_counts=True)
cols = cols[cnt >= 3]
lum = cols @ np.array([0.3, 0.55, 0.15])
order = np.argsort(lum); cols = cols[order]
C_DK, C_SH, C_BASE, C_HI = (cols[int(i)] .astype(np.uint8) for i in np.linspace(0, len(cols) - 1, 4).round())
C_BASE = cols[np.argmax(cnt[cnt >= 3][order])].astype(np.uint8)   # 最常见的那个当底色
FOOT = np.array(CL.FOOT[:3], np.uint8); FOOT_HI = np.array((255, 208, 192), np.uint8)

# 头：屏幕 + 眼睛（同 v1）
hd = G['head']
dark = ((hd[..., :3].astype(int).sum(-1) < 120) & (hd[..., 3] > 0)).astype(np.uint8)
_, lab, st, _ = cv2.connectedComponentsWithStats(dark, 4)
k = 1 + np.argmax(st[1:, 4]); SX, SY, SW_, SH_ = st[k, :4]

def head_with_face(face='normal', look=(0, 0)):
    a = hd.copy(); g = CL.EYES.get(face, CL.EYES['normal']); gw, gh = len(g[0]), len(g); gap = 4
    ex0 = SX + (SW_ - (2 * gw + gap)) // 2 + look[0]; ey0 = SY + (SH_ - gh) // 2 + look[1]
    lit = np.zeros(a.shape[:2], bool); cmap = {'#': CL.EYE, 'h': CL.EYE_HI, 'l': CL.EYE_LO}
    for side in (0, 1):
        for yy, row in enumerate(g):
            row = row[::-1] if side else row
            for xx, ch in enumerate(row):
                if ch in cmap:
                    X, Y = ex0 + side * (gw + gap) + xx, ey0 + yy
                    if SX <= X < SX + SW_ and SY <= Y < SY + SH_:
                        a[Y, X, :3] = np.array(cmap[ch][:3], np.uint8); lit[Y, X] = True
    ring = cv2.dilate(lit.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~lit & (dark > 0)
    a[ring, :3] = np.array(CL.HALO[:3], np.uint8)
    return a

# ---------------------------------------------------------------- 画布工具
CW, CH = 150, 140

class Layer:
    def __init__(self):
        self.a = np.zeros((CH, CW, 4), np.uint8)
    def put(self, img, x0, y0):
        h, w = img.shape[:2]
        sx0, sy0 = max(0, -x0), max(0, -y0); dx0, dy0 = max(0, x0), max(0, y0)
        ww, hh = min(w - sx0, CW - dx0), min(h - sy0, CH - dy0)
        if ww <= 0 or hh <= 0: return
        s = img[sy0:sy0 + hh, sx0:sx0 + ww]; m = s[..., 3] > 0
        self.a[dy0:dy0 + hh, dx0:dx0 + ww][m] = s[m]

def put_rot(L, img, pivot, at, deg):
    """img 绕 pivot 旋转 deg（EPX）后把 pivot 放到 at。"""
    h, w = img.shape[:2]; pad = int(math.hypot(h, w)) + 2
    A = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.uint8); A[pad:pad + h, pad:pad + w] = img
    pv = (pivot[0] + pad, pivot[1] + pad); dq = round(deg)
    if dq: A, _ = rotsprite(A, np.zeros(A.shape[:2], np.float32), dq, pv, method='epx')
    L.put(A, int(round(at[0] - pv[0])), int(round(at[1] - pv[1])))

def limb(pts, width=6, base=None, foot=None, ring_except=None):
    """代码画的一段肢体（折线），返回 RGBA。明暗按左上光：朝光的一侧亮、背光的一侧暗。不带描边（最后统一描）。"""
    base = C_BASE if base is None else base
    m = np.zeros((CH, CW), np.uint8)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        cv2.line(m, (int(round(x0)), int(round(y0))), (int(round(x1)), int(round(y1))), 1, width - 1)
        cv2.circle(m, (int(round(x1)), int(round(y1))), (width - 1) // 2, 1, -1)
    cv2.circle(m, (int(round(pts[0][0])), int(round(pts[0][1]))), (width - 1) // 2, 1, -1)
    if foot is not None:
        fx, fy = foot
        cv2.ellipse(m, (int(fx), int(fy)), (4, 2), 0, 0, 360, 2, -1)
    M = m > 0
    out = np.zeros((CH, CW, 4), np.uint8)
    out[M, :3] = base; out[M, 3] = 255
    p = np.pad(M, 2)
    lit = M & ~p[1:-3, 1:-3]          # 左上邻居是空的 → 受光边
    shd = M & ~p[3:-1, 3:-1]          # 右下邻居是空的 → 背光边
    shd2 = M & ~p[4:, 4:]
    out[shd2 & ~lit, :3] = C_SH; out[shd, :3] = C_DK; out[lit & ~shd, :3] = C_HI
    F = m == 2
    out[F, :3] = FOOT; out[F & lit, :3] = FOOT_HI; out[F & shd, :3] = C_SH
    if ring_except is not None:
        # 自带一圈描边（画在躯干前面时，和身体分得开），但关节附近 r 像素内不描 → 肩膀没有接缝
        (jx, jy), r = ring_except
        q = np.pad(M, 1)
        ring = (q[:-2, 1:-1] | q[2:, 1:-1] | q[1:-1, :-2] | q[1:-1, 2:]) & ~M
        yy, xx = np.mgrid[0:CH, 0:CW]
        ring &= np.hypot(xx - jx, yy - jy) > r
        out[ring, :3] = OUT; out[ring, 3] = 255
    return out

def outline(a):
    A = a[..., 3] > 0; p = np.pad(A, 1)
    ring = (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]) & ~A
    o = a.copy(); o[ring, :3] = OUT; o[ring, 3] = 255
    return o

# ---------------------------------------------------------------- 骨架（画布坐标）
ROOT = (CW // 2, CH - 26)                    # 躯干底边中点
TW, TH = G['torso'].shape[1], G['torso'].shape[0]
UP_L, FORE_L = 8, 8                       # 上臂 / 前臂长度
LEG_L = 6

def seg(t, a, b, ease=ease_io): return ease(clamp01((t - a) / (b - a)))

def shoulder_angle(tq):
    """单侧肩角（度，0 = 下垂，向外为正）。和 v1 同一套表演。"""
    up = 8.0
    if 1.7 <= tq < 1.84: up = 8 - 18 * seg(tq, 1.7, 1.84)
    elif 1.84 <= tq < 2.98:
        up = -10 + 130 * back_out(clamp01((tq - 1.84) / 0.2), 1.6) * (1 - seg(tq, 2.65, 2.95)) + 18 * seg(tq, 2.65, 2.95)
        if 2.34 <= tq < 2.65: up += 10 * math.sin((tq - 2.34) * 2 * math.pi * 4)
    elif tq >= 2.98:
        if tq < 3.06: up = 8
        elif tq < 3.36: up = 60 + 22 * math.sin((tq - 3.06) / 0.30 * 2 * math.pi * 2)
        else: up = 8 + 52 * (1 - seg(tq, 3.36, 3.6))
    return up

def pose(t):
    tq = on_twos(t)
    dy = 0.0; sq = 0.0; face, look = 'normal', (0, 0)
    for tb in (0.55, 3.85):
        u = t - tb
        if 0 <= u < 0.06: face = 'half'
        elif u < 0.12 and u >= 0.06: face = 'blink'
        elif u < 0.18 and u >= 0.12: face = 'blink1'
    if tq >= 1.0: look = (2, 0)
    hturn = (5 * back_out(clamp01((tq - 1.15) / 0.25)) if tq >= 1.15 else 0) * (1 - seg(tq, 1.7, 1.9))
    if 1.7 <= tq < 1.84: u = seg(tq, 1.7, 1.84); dy += 2 * u; sq += 0.10 * u
    elif 1.84 <= tq < 2.98:
        hop = math.sin(math.pi * clamp01((tq - 1.86) / 0.36)) if tq < 2.22 else 0
        dy -= 9 * hop
        if 2.22 <= tq < 2.34: sq += 0.14 * (1 - seg(tq, 2.22, 2.34)); dy += 1
    if 1.84 <= tq < 2.8: face = 'happy'
    if tq >= 2.98:
        if tq < 3.7: face = 'wideL'
        if tq < 3.06: dy += 2; sq += 0.12
        elif tq < 3.36: u = (tq - 3.06) / 0.30; dy -= 12 * math.sin(math.pi * u); sq -= 0.16 * math.sin(math.pi * u)
        elif tq < 3.5: sq += 0.16 * (1 - seg(tq, 3.36, 3.5))
    sh = shoulder_angle(tq)
    # 前臂 = 弹簧跟随上臂（拖拽 + 过冲：甩手时手腕晚到一拍）
    fore = spring_follow(lambda x: shoulder_angle(on_twos(x)), t, freq=6.0, zeta=0.42, window=0.8, dt=1 / 120)
    elbow = max(-35.0, min(35.0, fore - sh)) + 10                    # 肘部自然微弯；拖拽限幅，否则快动作时手会被拖成下垂
    ant = -0.8 * hturn + wobble(t, 1.15, 8) + wobble(t, 2.22, 10) + wobble(t, 3.06, 12) + wobble(t, 3.36, 10)
    return dict(dy=int(round(dy)), sq=sq, face=face, look=look, head=hturn, sh=sh, elbow=elbow, ant=ant,
                air=dy < -3, breath=breath_px(t))

def arm_pts(shoulder, ang, elbow, side):
    """side=-1 左（画面左），+1 右。角度 0 = 下垂，向外张开为正。"""
    a1 = math.radians(ang) * -side
    e = (shoulder[0] - math.sin(a1) * UP_L * 1, shoulder[1] + math.cos(a1) * UP_L)
    a2 = a1 + math.radians(elbow) * side
    w = (e[0] - math.sin(a2) * FORE_L, e[1] + math.cos(a2) * FORE_L)
    return [shoulder, e, w], math.degrees(a2)

def character(t):
    p = pose(t)
    L = Layer()
    tx0, ty0 = ROOT[0] - TW // 2, ROOT[1] - TH
    # 腿（在躯干后面）：从胯到脚踝，脚在地上；起跳时收腿
    for side, fx in ((-1, 0.30), (1, 0.70)):
        hip = (tx0 + fx * TW, ROOT[1] - 3)
        lift = 2 if p['air'] else 0
        ank = (hip[0] + side * (1 if p['air'] else 0), hip[1] + LEG_L - lift)
        L.put(limb([hip, ank], 6, foot=(ank[0] + side * 1, ank[1] + 2)), 0, 0)
    # 躯干
    L.put(G['torso'], tx0, ty0)
    # 手臂（画在躯干前面，自带描边，肩关节 4px 内不描 → 分得清又没有接缝）；举过 70° 时改画到头前面
    hands = []; arms = []
    for side, fx in ((-1, 0.17), (1, 0.83)):
        shp = (tx0 + fx * TW, ty0 + 5)
        pts, fore_deg = arm_pts(shp, p['sh'], p['elbow'], side)
        arms.append(limb(pts, 7, ring_except=(shp, 4.5)))
        hands.append((pts[-1], fore_deg, side))
    raised = p['sh'] > 70
    if not raised:
        for a_ in arms: L.put(a_, 0, 0)
    # 头 + 天线
    head = head_with_face(p['face'], p['look'])
    hh, hw = head.shape[:2]
    neck = (ROOT[0], ty0 + 3 + p['breath'])
    hpiv = (hw // 2, hh - 2)
    put_rot(L, head, hpiv, neck, p['head'])
    a = math.radians(p['head'])
    top_local = (int(hw * 0.56) - hpiv[0], 1 - hpiv[1])
    top = (neck[0] + top_local[0] * math.cos(a) - top_local[1] * math.sin(a),
           neck[1] + top_local[0] * math.sin(a) + top_local[1] * math.cos(a))
    an = G['antenna']; put_rot(L, an, (an.shape[1] // 2, an.shape[0] - 1), top, p['head'] + p['ant'])
    if raised:
        for a_ in arms: L.put(a_, 0, 0)
    # 手（最前面）：跟着前臂方向转
    for (w, fdeg, side) in hands:
        himg = G['handL'] if side < 0 else G['handR']
        put_rot(L, himg, (himg.shape[1] // 2, himg.shape[0] // 3), (w[0], w[1] + 1), fdeg * 0.5)
    a = outline(L.a)
    return a, p

# ---------------------------------------------------------------- 场景（同 v1）
WW, WH, S = 320, 180, 6
def background():
    bg = np.zeros((WH, WW, 3), np.uint8)
    for y in range(WH):
        k = y / WH; bg[y] = (np.array([46, 38, 66]) * (1 - k) + np.array([70, 52, 84]) * k).astype(np.uint8)
    bg[132:] = (58, 44, 66); bg[132] = (88, 66, 92)
    yy, xx = np.mgrid[0:WH, 0:WW]
    g = np.clip(1 - np.hypot(xx - 90, yy - 40) / 170, 0, 1) ** 2
    return np.clip(bg + (g[..., None] * np.array([60, 36, 18])), 0, 255).astype(np.uint8)
BG = background(); FEET_Y = 132
FEET_IN = ROOT[1] + LEG_L + 3                 # 画布里脚底那一行

def frame(t):
    a, p = character(t)
    E = np.zeros(a.shape[:2], np.float32)
    ox = oy = 0
    if abs(p['sq']) > 1e-3: a, E, ox, oy = squash_about(a, E, p['sq'], CW / 2, FEET_IN)
    img = BG.copy()
    h = max(0, -p['dy']); rw = max(6, int(20 - h * 0.8))
    sh = np.zeros((WH, WW), np.uint8); cv2.ellipse(sh, (WW // 2, FEET_Y + 1), (rw, 3), 0, 0, 360, 255, -1)
    m = sh > 0; img[m] = (img[m] * (0.55 + 0.03 * h)).clip(0, 255).astype(np.uint8)
    x0 = WW // 2 - CW // 2 + ox; y0 = FEET_Y - FEET_IN + p['dy'] + oy
    hh, ww = a.shape[:2]
    ys, xs = np.nonzero(a[..., 3] > 0)
    Y, X = ys + y0, xs + x0; ok = (Y >= 0) & (Y < WH) & (X >= 0) & (X < WW)
    img[Y[ok], X[ok]] = a[ys[ok], xs[ok], :3]
    return np.repeat(np.repeat(img, S, 0), S, 1)

if __name__ == '__main__':
    fps, dur = 30, 4.2
    out = os.path.join(_OUT, 'rig_v2.mp4')
    pr = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WW*S}x{WH*S}', '-r', str(fps),
                           '-i', '-', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    shots = []
    for i in range(int(fps * dur)):
        f = frame(i / fps); pr.stdin.write(f.tobytes())
        if i in (0, 36, 54, 60, 66, 74, 92, 96, 102, 120):
            shots.append(cv2.resize(f[180:900, 540:1380], (420, 360), interpolation=cv2.INTER_NEAREST))
    pr.stdin.close(); pr.wait()
    sheet = np.concatenate([np.concatenate(shots[:5], 1), np.concatenate(shots[5:10], 1)], 0)
    cv2.imencode('.png', sheet[..., ::-1])[1].tofile(os.path.join(_OUT, 'rig_v2_sheet.png'))
    print('wrote', out)
