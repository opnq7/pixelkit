"""pixelkit.sets.brain_tower - 「大脑 · 夜班」大楼（v0.13《熬夜副本》第 2 关）：外景 + 三个剖面房间 + 小职员。

    bt = BrainTower()
    fr = bt.exterior(t, sign='大脑 · 夜班' | '系统维护中', lights=0..1)
    fr = bt.archive(t, k)          档案室：职员把「白天的事」文件夹归档进柜子
    fr = bt.emotion(t, k)          情绪科：红色「焦虑」乌云进烘干机 -> 小白云
    fr = bt.basement(t, k)         地下室：开闸，蓝色脑脊液冲走「代谢废物」垃圾袋，清洁工踩拖把冲浪
    L = bt.light_*(fr, ...)
clerk(s, x, y, col, t, carry=None, flip=False)   原创像素小职员（8x12），走路两帧
"""
import math
import numpy as np
from ..pixstage import Stage
from ..core import text_width

def clerk(s, x, y, col='#5a7ac8', t=0.0, carry=None, flip=False, walk=True, hat='#f0e8d8'):
    """tiny pixel office worker, feet at (x, y)."""
    ph = int(t * 8) % 2 if walk else 0
    x = int(round(x)); y = int(round(y))
    s.rect(x - 3, y - 11, 6, 6, '#f2c8a0')                      # head
    s.rect(x - 3, y - 12, 6, 2, '#2a2228'); s.rect(x - 4, y - 12, 8, 1, hat)
    s.px(x - 1 + (1 if flip else 0), y - 9, '#1a1418')
    s.rect(x - 3, y - 5, 6, 4, col)                              # body
    s.rect(x - 3 + (1 if ph else 0), y - 1, 2, 1, '#2a2a34'); s.rect(x + 1 - (1 if ph else 0), y - 1, 2, 1, '#2a2a34')
    if carry == 'folder':
        s.rect(x + (-8 if flip else 3), y - 7, 5, 4, '#e8c860'); s.rect(x + (-8 if flip else 3), y - 7, 5, 1, '#c8a040')
    elif carry == 'mop':
        s.line(x + 3, y - 10, x + 6, y, '#8a6a3a'); s.rect(x + 4, y, 5, 2, '#d8d8e8')
    s.outline(s.M_rect(x - 3, y - 12, 6, 12), '#07060a')

class BrainTower:
    W, H = 320, 180

    def __init__(self):
        self.rng = np.random.default_rng(12)
        self.win = [(x, y, self.rng.random()) for y in range(70, 168, 9) for x in range(118, 204, 9)]

    # ---------------------------------------------------------------- exterior
    def exterior(self, t=0.0, sign='大脑 · 夜班', lights=1.0, sign_k=1.0):
        s = Stage(self.W, self.H); yy = s.yy
        s.img[..., :3] = (6, 6, 16)
        for y in range(0, 120, 4):
            s.rect(0, y, 320, 4, (8 + y // 10, 8 + y // 12, 26 + y // 6))
        rng = np.random.default_rng(3)
        for i in range(60): s.px(rng.integers(0, 320), rng.integers(0, 90), ['#5a5a80', '#c8c8e8', '#fff4d0'][i % 3], 0.8)
        # city silhouettes left/right
        for (x, w, h) in ((0, 30, 70), (26, 24, 96), (52, 34, 60), (230, 30, 88), (256, 34, 64), (288, 32, 100)):
            m = s.rect(x, 180 - h, w, h, '#0c0c1a')
            for wy in range(180 - h + 4, 176, 6):
                for wx in range(x + 3, x + w - 3, 5):
                    if rng.random() < 0.18: s.px(wx, wy, '#ffcf7a', 0.7)
        # the tower
        body = s.rect(108, 62, 104, 118, '#1e2034'); s.rect(108, 62, 6, 118, '#262a44'); s.rect(206, 62, 6, 118, '#16182a')
        s.outline(body, '#05050a')
        for (x, y, r) in self.win:
            on = (r < 0.82 * lights) and not (r > 0.75 and int(t * 2 + r * 10) % 5 == 0)
            col = '#ffd27a' if r < 0.6 else ('#9fe0ff' if r < 0.75 else '#ffb08a')
            s.rect(x, y, 6, 5, col if on else '#14162a', 0.9 if on else 0.0)
            if on: s.rect(x, y + 4, 6, 1, '#c89040', 0.5)
        # brain dome on the roof (two lobes, folds)
        dome = s.M_ell(146, 54, 34, 22) | s.M_ell(176, 54, 34, 22)
        dome &= yy < 64
        s.fill(dome, '#e88aa8'); s.fill(dome & s.M_ell(150, 46, 24, 12), '#f8b0c8')
        for k in range(7):
            a0 = 118 + k * 12
            s.line(a0, 60 - (k % 2) * 4, a0 + 8, 40 + (k % 3) * 4, '#b85a7a', mask=dome)
        s.line(160, 34, 160, 63, '#a84a6a', mask=dome)
        s.fill(s.ring(dome), '#3a1a2a')
        # antenna + blinking light
        s.rect(196, 20, 2, 18, '#5a5a6a'); s.rect(195, 18, 4, 3, '#ff4a3a', 1.0 if int(t * 2) % 2 == 0 else 0.2)
        # neon sign
        sw = 76; sx, sy = 160 - sw // 2, 70 if False else 64
        s.rect(sx - 2, 92, sw + 4, 16, '#08060c'); s.outline(s.M_rect(sx - 2, 92, sw + 4, 16), '#5a2a4a')
        col = '#ff7ab8' if '夜班' in sign else '#7fe0ff'
        tw = text_width(sign, 'zh10')
        flick = sign_k * (1.0 if int(t * 13) % 23 else 0.4)
        s.text(160 - tw // 2, 95, sign, col, 'zh10', E=flick)
        # searchlights
        return s

    def light_exterior(self, s, t=0.0, sign='夜班'):
        L = s.light_base((0.55, 0.55, 0.85), 0.9)
        col = (1.0, 0.45, 0.75) if '夜班' in sign else (0.45, 0.85, 1.0)
        L = L + s.band(160, 100, 70, 30, col, [(1.0, 0.25), (0.5, 0.45)])
        return L

    def air_exterior(self, s, t=0.0):
        A = np.zeros((self.H, self.W, 3), np.float32)
        for k, ph in enumerate((0.0, 2.1)):
            a = -math.pi / 2 + 0.45 * math.sin(t * 0.6 + ph)
            tip = (160 + 260 * math.cos(a), 30 + 260 * math.sin(a))
            A += s.cone((160, 30), (tip[0] - 18, tip[1]), (tip[0] + 18, tip[1]), (0.8, 0.85, 1.0), 0.05)
        return A

    # ---------------------------------------------------------------- cross-section rooms
    def _room(self, s, wall, floor, label, label_col):
        s.img[..., :3] = (8, 8, 14)
        s.rect(20, 20, 280, 110, wall); s.rect(20, 130, 280, 30, floor)
        s.poly([(0, 180), (20, 160), (300, 160), (320, 180)], floor)
        s.outline(s.M_rect(20, 20, 280, 140), '#05050a')
        s.rect(20, 20, 280, 3, '#3a3a52')
        tw = text_width(label, 'zh10')
        s.rect(160 - tw // 2 - 4, 24, tw + 8, 13, '#0a0a14'); s.text(160 - tw // 2, 26, label, label_col, 'zh10', E=0.8)

    def archive(self, t=0.0, k=1.0):
        s = Stage(self.W, self.H)
        self._room(s, '#2a2a3e', '#3a3040', '档案室 · 记忆归档', '#ffe27a')
        for i in range(6):
            x = 36 + i * 44
            cab = s.rect(x, 52, 30, 78, '#5a5e74'); s.outline(cab, '#0a0a10')
            for j in range(4):
                s.rect(x + 3, 56 + j * 18, 24, 14, '#6a6e86'); s.rect(x + 12, 61 + j * 18, 6, 2, '#c8c8d8')
            if (i * 3 + int(t * 2)) % 7 == 0: s.rect(x + 3, 56 + (i % 4) * 18 + 2, 24, 10, '#e8c860')
        # conveyor of folders labelled 白天的事
        s.rect(20, 120, 280, 6, '#1a1a24')
        for i in range(8):
            x = (i * 46 + t * 40) % 300 + 10
            s.rect(x, 113, 14, 7, '#e8c860'); s.rect(x, 113, 14, 1, '#c8a040')
        for i in range(4):
            x = 60 + i * 64 + 10 * math.sin(t * 1.3 + i)
            clerk(s, x, 150, ['#5a7ac8', '#c85a5a', '#5ac87a', '#c8a05a'][i], t + i * 0.3, carry='folder', flip=(i % 2 == 1))
        return s

    def emotion(self, t=0.0, k=0.0):
        """k 0..1: the anxiety cloud goes in (0-0.3), spins (0.3-0.8), comes out small and white."""
        s = Stage(self.W, self.H)
        self._room(s, '#2e2638', '#40303a', '情绪科 · 消化焦虑', '#ffb0c8')
        # dryer
        cx, cy = 200, 92
        dr = s.rect(cx - 34, cy - 40, 68, 78, '#d8d8e4'); s.outline(dr, '#0a0a10')
        s.rect(cx - 34, cy - 40, 68, 10, '#b8b8c8'); s.rect(cx + 18, cy - 37, 6, 4, '#3ac84a', 1.0)
        door = s.ell(cx, cy + 4, 24, 24, '#7a7a8e'); s.ell(cx, cy + 4, 20, 20, '#1a2a4a', 0.2)
        spin = t * 9 if 0.3 < k < 0.82 else 0
        # cloud
        def cloud(x, y, r, col, E=0.3):
            for (dx, dy, rr) in ((0, 0, 1.0), (-0.9, 0.3, 0.75), (0.9, 0.3, 0.75), (0.4, -0.5, 0.7)):
                s.ell(x + dx * r, y + dy * r, rr * r, rr * r * 0.8, col, E)
        if k < 0.3:
            u = k / 0.3
            x = 90 + (cx - 90) * u; y = 92 + (cy + 4 - 92) * u
            cloud(x, y, 16 * (1 - 0.4 * u), '#d83a4a', 0.4)
            s.text(x - 10, y - 4, '焦虑', '#ffffff', 'zh8', 0.5)
            for i in range(3): s.line(x - 8 + i * 8, y + 12, x - 10 + i * 8, y + 22, '#ffd34a', 0.8)   # little lightning
        elif k < 0.82:
            for i in range(5):
                a = spin + i * 1.25
                cloud(cx + 9 * math.cos(a), cy + 4 + 9 * math.sin(a), 5, '#d84a5a' if k < 0.6 else '#e8a0a8', 0.4)
        else:
            u = (k - 0.82) / 0.18
            x = cx + (110 - cx) * u; y = cy + 4 - 30 * u
            cloud(x, y, 9, '#f4f4ff', 0.5)
        s.fill(s.ring(door), '#3a3a4a')
        clerk(s, 104, 150, '#c85a8a', t, walk=False)
        clerk(s, 250, 150, '#8a5ac8', t * 0.5, walk=False, flip=True)
        return s

    def basement(self, t=0.0, k=0.0):
        """k 0..1: gate opens (0-0.2), the wave sweeps left->right (0.2-1)."""
        s = Stage(self.W, self.H)
        self._room(s, '#1e2a30', '#2a3438', '地下室 · 清洁队', '#7fe0ff')
        # pipes
        for y in (40, 48): s.rect(20, y, 280, 4, '#4a5a5e'); s.rect(20, y, 280, 1, '#6a7a7e')
        # floodgate on the left wall
        gate_open = min(1.0, k / 0.2)
        s.rect(22, 60, 30, 70, '#3a3a40'); s.rect(24, 62 - int(60 * gate_open), 26, 66, '#7a6a3a')
        for y in range(64 - int(60 * gate_open), 128 - int(60 * gate_open), 8): s.rect(24, y, 26, 1, '#5a4a2a')
        s.outline(s.M_rect(22, 60, 30, 70), '#05050a')
        # trash bags of 代谢废物
        wave_x = 20 + 300 * max(0.0, (k - 0.2) / 0.8)
        for i in range(5):
            bx = 90 + i * 40
            if bx < wave_x - 10:
                bx = wave_x - 10 + 6 * math.sin(t * 5 + i); by = 120 - 8 * math.sin(t * 4 + i)
            else:
                by = 140
            s.ell(bx, by, 9, 8, '#3a3a40'); s.rect(bx - 2, by - 9, 4, 3, '#2a2a30')
            s.text(bx - 8, by - 3, '废物', '#c8c8a0', 'zh8')
        # the wave
        if k > 0.2:
            m = s.M_poly([(20, 160), (20, 88), (wave_x - 30, 96), (wave_x, 104 + 6 * math.sin(t * 6)), (wave_x + 6, 160)])
            s.fill(m, '#3a8ad8', 0.35)
            s.fill(m & (s.yy < 112) & ((s.xx + int(t * 30)) % 9 < 4), '#9fe0ff', 0.6)
            s.fill(s.ring(m) & (s.yy < 130), '#e0f8ff', 0.7)
            # mop surfer riding the crest
            clerk(s, wave_x - 14, 100 + 4 * math.sin(t * 6), '#e8a040', t, carry='mop', walk=False)
        return s

    def light_room(self, s, col=(1.0, 0.9, 0.7)):
        L = s.light_base((0.62, 0.62, 0.8), 0.95)
        for x in (90, 230):
            L = L + s.cone((x, 22), (x - 50, 160), (x + 50, 160), col, 0.18)
        return L
