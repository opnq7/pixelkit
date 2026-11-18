"""质感体检：把我们的成片和参考片放在同一把尺子上量（剪辑节奏 + 用色 + 清晰度 + 场景重复 + 像素颗粒）。

usage:
  python look_report.py 名字=视频路径[@x0,y0,x1,y1[@画面宽px]] ...  [--out 目录]

  @x0,y0,x1,y1  裁掉录屏的播放器界面，0–1 的比例（参考片是网页端录屏，必须裁）
  @画面宽px      原视频里「真正画面」的像素宽度，用来把像素颗粒换算到 1920 宽（默认 = 裁剪后宽度）

例：
  python look_report.py 乌合之众=参考视频/乌合之众.mp4@0.01,0.06,0.93,0.86@1620 \
                        金钱心理学=参考视频/金钱心理学.mp4@0.03,0.09,0.95,0.80@2460 \
                        深度工作v4=作品/001_深度工作/out/深度工作_全片_v4_带BGM.mp4

输出：终端对比表 + <out>/look_<名字>.json + <out>/sets_<名字>.jpg（每个「场景」一张代表帧，按占用时长排序）
指标说明见 标准与方法/质感差距分析.md 第 4 节。
"""
import sys, os, json, cv2, numpy as np

args = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.getcwd()
if '--out' in sys.argv: args.remove(OUT)


def imwrite(p, im):  # OpenCV 中文路径
    cv2.imencode(os.path.splitext(p)[1], im, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tofile(p)


def grid_lag(gray):
    """像素颗粒：横向边缘位置的自相关峰（单位：原视频像素）。返回 (lag, 峰强度)。"""
    g = np.abs(np.diff(gray.astype(np.float32), axis=1))
    e = (g > 12).astype(np.float32)
    prof = e.sum(0); prof -= prof.mean()
    ac = np.correlate(prof, prof, 'full')[len(prof) - 1:]
    ac /= ac[0] + 1e-6
    lo, hi = 3, min(60, len(ac) - 2)
    pk = [j for j in range(lo, hi) if ac[j] >= ac[j - 1] and ac[j] >= ac[j + 1]]
    if not pk: return lo, 0.0
    top = max(ac[j] for j in pk)
    k = next(j for j in pk if ac[j] >= 0.85 * top)  # 取基频，不取倍频
    return k, float(ac[k])


def analyse(name, path, crop, cw):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    prev = prevh = None
    diffs, hd, samples, thumbs = [], [], [], []
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        H, W = fr.shape[:2]
        if crop: fr = fr[int(crop[1] * H):int(crop[3] * H), int(crop[0] * W):int(crop[2] * W)]
        sm = cv2.resize(fr, (160, 90), interpolation=cv2.INTER_AREA)
        g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY).astype(np.float32)
        h = cv2.calcHist([cv2.cvtColor(sm, cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256]); cv2.normalize(h, h)
        diffs.append(0.0 if prev is None else float(np.mean(np.abs(g - prev))))
        hd.append(0.0 if prevh is None else float(cv2.compareHist(prevh, h, cv2.HISTCMP_BHATTACHARYYA)))
        prev, prevh = g, h
        thumbs.append(cv2.resize(sm, (32, 18), interpolation=cv2.INTER_AREA))
        if i % int(round(fps / 2)) == 0:  # 每 0.5 s 一帧做静帧指标
            samples.append((i, fr.copy() if i % int(round(fps * 4)) == 0 else cv2.resize(fr, (960, int(960 * fr.shape[0] / fr.shape[1])), interpolation=cv2.INTER_AREA)))
        i += 1
    cap.release()
    n = len(diffs); dur = n / fps
    d, Hh = np.array(diffs), np.array(hd)
    # ---------- 剪辑节奏（阈值同 拆解数据/脚本/cuts.py、rhythm.py）
    cuts = []
    for k in range(1, n):
        if (Hh[k] > 0.32 or d[k] > 38) and not (cuts and k - cuts[-1] <= 3): cuts.append(k)
    sl = np.diff([0] + cuts + [n]) / fps
    ev = np.where(d > 6.0)[0] / fps; evm = []
    for t in ev:
        if not evm or t - evm[-1] > 0.25: evm.append(t)
    per_sec = np.array([d[int(s * fps):int((s + 1) * fps)].max() for s in range(int(dur))])
    gaps = np.diff([0] + evm + [dur])
    # ---------- 场景重复：每个镜头取中间帧的 32x18 Lab 缩略图，距离小于阈值算同一场景
    bounds = [0] + cuts + [n]
    shots = [(a, b) for a, b in zip(bounds, bounds[1:]) if b - a >= 6]
    # 场景签名 = 构图（16x9 灰度、去均值归一化，和调色无关）+ 平均色；构图相关 > 0.8 且平均色接近才算同一场景
    def _sig(im):
        g = cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (16, 9), interpolation=cv2.INTER_AREA).astype(np.float32).ravel()
        g = (g - g.mean()) / (g.std() + 4)
        return g, cv2.cvtColor(im, cv2.COLOR_BGR2LAB).reshape(-1, 3).mean(0)
    sig = [_sig(thumbs[(a + b) // 2]) for a, b in shots]
    sets, owner = [], []
    for k, (g, c) in enumerate(sig):
        for j, ((rg, rc), members) in enumerate(sets):
            if float(np.dot(g, rg)) / len(g) > 0.8 and np.abs(c - rc).mean() < 12:
                members.append(k); owner.append(j); break
        else:
            sets.append(((g, c), [k])); owner.append(len(sets) - 1)
    np.savez(os.path.join(OUT, f'sig_{name}.npz'), thumbs=np.array([thumbs[(a + b) // 2] for a, b in shots]), shots=np.array(shots), fps=fps)
    set_time = sorted([(sum(shots[m][1] - shots[m][0] for m in mem) / fps, len(mem), mem[0]) for _, mem in sets], reverse=True)
    # 代表帧拼图
    cap = cv2.VideoCapture(path); tiles = []
    for t, cnt, k0 in set_time[:24]:
        a, b = shots[k0]; cap.set(cv2.CAP_PROP_POS_FRAMES, (a + b) // 2); ok, fr = cap.read()
        if not ok: continue
        H, W = fr.shape[:2]
        if crop: fr = fr[int(crop[1] * H):int(crop[3] * H), int(crop[0] * W):int(crop[2] * W)]
        im = cv2.resize(fr, (320, 180)); cv2.rectangle(im, (0, 0), (150, 18), (0, 0, 0), -1)
        cv2.putText(im, f'{t:5.1f}s x{cnt}', (3, 13), 0, 0.45, (0, 255, 255), 1); tiles.append(im)
    cap.release()
    while len(tiles) % 6: tiles.append(np.zeros((180, 320, 3), np.uint8))
    if tiles: imwrite(os.path.join(OUT, f'sets_{name}.jpg'), np.vstack([np.hstack(tiles[r:r + 6]) for r in range(0, len(tiles), 6)]))
    # ---------- 用色 / 明暗 / 清晰度 / 颗粒（静帧采样）
    S, V, L, loud, dark, hueconc, colorful, soft, labmeans, lags = [], [], [], [], [], [], [], [], [], []
    for fi, fr in samples:
        full = fr
        fr = cv2.resize(full, (960, int(960 * full.shape[0] / full.shape[1])), interpolation=cv2.INTER_AREA) if full.shape[1] != 960 else full
        hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV).astype(np.float32)
        s, v = hsv[..., 1] / 255, hsv[..., 2] / 255
        S.append(s.mean()); V.append(v.mean())
        lab = cv2.cvtColor(fr, cv2.COLOR_BGR2LAB).astype(np.float32)
        L.append(lab[..., 0].std() / 2.55); labmeans.append(lab.reshape(-1, 3).mean(0))
        loud.append(((s > 0.6) & (v > 0.35)).mean()); dark.append((v < 0.15).mean())
        m = (s > 0.35) & (v > 0.25)
        if m.sum() > 500:
            hh = np.histogram(hsv[..., 0][m], 12, (0, 180))[0].astype(float)
            hh = hh + np.roll(hh, 1); hueconc.append(hh.max() / hh.sum() * 2)
        b, g_, r = [fr[..., c].astype(np.float32) for c in range(3)]
        rg, yb = r - g_, 0.5 * (r + g_) - b
        colorful.append(np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))
        gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        gx = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 1))
        T = 24; hT, wT = gray.shape[0] // T, gray.shape[1] // T
        st = gray[:hT * T, :wT * T].reshape(hT, T, wT, T).std((1, 3))
        gr = gx[:hT * T, :wT * T].reshape(hT, T, wT, T).mean((1, 3))
        busy = st > 10
        if busy.sum(): soft.append(float(((gr / (st + 1e-6)) < 1.6)[busy].mean()))
        if full.shape[1] != 960:  # 原尺寸帧：量颗粒
            k, p = grid_lag(cv2.cvtColor(full, cv2.COLOR_BGR2GRAY))
            lags.append((k * 1920 / (cw or full.shape[1]), p))
    lm = np.array(labmeans)
    shot_lab = []
    for a, b in shots:
        idx = [j for j, (fi, _) in enumerate(samples) if a <= fi < b]
        if idx: shot_lab.append(lm[idx].mean(0))
    shot_lab = np.array(shot_lab)
    good = [l for l, p in lags if p > 0.25]
    r = dict(
        时长=round(dur, 1), 硬切每分=round(len(cuts) / dur * 60, 1), 镜头中位秒=round(float(np.median(sl)), 2),
        镜头p90秒=round(float(np.percentile(sl, 90)), 2), 画面事件每分=round(len(evm) / dur * 60, 1),
        最长无事件秒=round(float(gaps.max()), 1), 超3秒无事件段=int((gaps > 3).sum()),
        完全静止秒占比=round(float((per_sec < 0.6).mean()), 3),
        场景数=len(sets), 镜头数=len(shots), 最常用场景占时=round(set_time[0][0] / dur, 3) if set_time else 0,
        前三场景占时=round(sum(t for t, _, _ in set_time[:3]) / dur, 3), 最常用场景重复次数=max(c for _, c, _ in set_time) if set_time else 0,
        平均饱和度=round(float(np.mean(S)), 3), 高饱和像素占比=round(float(np.mean(loud)), 3), 色彩丰富度=round(float(np.mean(colorful)), 1),
        平均亮度=round(float(np.mean(V)), 3), 暗部占比=round(float(np.mean(dark)), 3), 明暗反差=round(float(np.mean(L)), 1),
        主色集中度=round(float(np.mean(hueconc)), 3) if hueconc else None,
        场景间色调差=round(float(np.sqrt(shot_lab[:, 1].var() + shot_lab[:, 2].var())), 2) if len(shot_lab) > 2 else None,
        场景间亮度差=round(float(shot_lab[:, 0].std() / 2.55), 2) if len(shot_lab) > 2 else None,
        发糊区域占比=round(float(np.mean(soft)), 3) if soft else None,
        像素颗粒_1920宽=round(float(np.median(good)), 1) if good else None, 颗粒可测帧占比=round(len(good) / max(1, len(lags)), 2),
    )
    ev_all = [0] + evm + [dur]
    json.dump(dict(r, dead=[(round(a, 1), round(b - a, 1)) for a, b in zip(ev_all, ev_all[1:]) if b - a > 3], cut_t=[round(c / fps, 2) for c in cuts], set_time=[(round(t, 1), c) for t, c, _ in set_time]),
              open(os.path.join(OUT, f'look_{name}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return r


if __name__ == '__main__':
    res = {}
    for a in args:
        name, rest = a.split('=', 1)
        parts = rest.split('@')
        crop = [float(x) for x in parts[1].split(',')] if len(parts) > 1 and parts[1] else None
        cw = float(parts[2]) if len(parts) > 2 else None
        res[name] = analyse(name, parts[0], crop, cw); print(name, 'done', flush=True)
    keys = list(next(iter(res.values())).keys())
    print(f"\n{'':16s}" + ''.join(f'{n:>14s}' for n in res))
    for k in keys:
        print(f'{k:16s}' + ''.join(f'{str(res[n][k]):>14s}' for n in res))
