"""逐句生成 Fish 配音（知识讲述音色）→ voice/wav/<id>.wav + voice/manifest.json
FISH_API_KEY 从环境变量读取；按句缓存，可重复运行。"""
import json, os, re, hashlib, subprocess, sys, time, requests
from pathlib import Path
ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'cache'; CACHE.mkdir(exist_ok=True)
WAV = ROOT / 'wav'; WAV.mkdir(exist_ok=True)
VOICE = 'f6f02c2a16ef4646b24322f188dc2ad9'
TARGET_CPS = float(os.environ.get('CPS', 4.7))
SPEECH = [  # 合成发音提示（不改字幕）
    ('1938 年', '一九三八年'), ('1953 年', '一九五三年'), ('1964 年', '一九六四年'),
    ('2003 年', '二零零三年'), ('1971 年', '一九七一年'), ('2015 年', '二零一五年'),
    ('264.4', '二百六十四点四'), ('PER', 'P E R'), ('TIM', 'T I M'),
]

def speech_of(t):
    for a, b in SPEECH: t = t.replace(a, b)
    return t

def dur(p):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)])
    return float(out)

def tts(text):
    body = {'text': text, 'reference_id': VOICE, 'temperature': .7, 'top_p': .7,
            'prosody': {'speed': 1, 'volume': 0, 'normalize_loudness': True},
            'format': 'mp3', 'sample_rate': 44100, 'mp3_bitrate': 192, 'latency': 'normal'}
    h = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]
    f = CACHE / (h + '.mp3')
    if f.exists(): return f
    key = os.environ['FISH_API_KEY']
    for a in range(4):
        try:
            r = requests.post('https://api.fish.audio/v1/tts', json=body, timeout=(15, 90),
                              headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json', 'model': 's2.1-pro-free'},
                              verify='/root/.ccr/ca-bundle.crt')
            if r.status_code == 200 and len(r.content) > 2000:
                f.write_bytes(r.content); return f
            print('HTTP', r.status_code, r.text[:120].replace(key, '***'), flush=True)
        except requests.RequestException as e:
            print('retry', type(e).__name__, flush=True)
        time.sleep(3 * (a + 1))
    raise RuntimeError('tts failed: ' + text)

def main():
    lines = json.loads((ROOT / 'lines.json').read_text())
    items = []
    for sec, arr in lines.items():
        for i, t in enumerate(arr, 1):
            lid = f'{sec}{i}'
            if len(sys.argv) > 1 and lid not in sys.argv[1:] and sec not in sys.argv[1:]: pass
            mp3 = tts(speech_of(t))
            items.append(dict(id=lid, text=t, raw=str(mp3), raw_dur=dur(mp3)))
            print(lid, f"{items[-1]['raw_dur']:.2f}s", t[:18], flush=True)
    nchar = sum(len(re.findall(r'[一-鿿A-Za-z0-9]', x['text'])) for x in items)
    raw_total = sum(x['raw_dur'] for x in items)
    factor = max(1.0, min(1.25, raw_total / (nchar / TARGET_CPS)))
    for x in items:
        out = WAV / (x['id'] + '.wav')
        # 去掉首尾静音 → 统一提速 → 响度归一
        af = (f"silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,areverse,"
              f"silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse,"
              f"atempo={factor:.5f},loudnorm=I=-18:TP=-2:LRA=9")
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', x['raw'], '-af', af, '-ar', '44100', '-ac', '1', str(out)], check=True)
        x['wav'] = str(out); x['dur'] = dur(out)
    (ROOT / 'manifest.json').write_text(json.dumps(dict(factor=factor, items=items), ensure_ascii=False, indent=1))
    print(f'factor {factor:.3f}  total {sum(x["dur"] for x in items):.1f}s  chars {nchar}')

if __name__ == '__main__':
    main()
