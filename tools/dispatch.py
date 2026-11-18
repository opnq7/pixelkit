"""主智能体的调度器：把一个写好的任务单交给本机的某个 AI，阻塞到完成（有硬超时），结果全部落盘。

  python 协作/dispatch.py run <worker> <任务单.md> [--id ID] [--model M] [--effort E] [--cwd DIR] [--timeout 秒] [--image 图...]
  python 协作/dispatch.py img a.txt b.txt c.txt [--par 3] [--ref 参考图...]   # 并行生图：每个 .txt 一条提示词 → 同名 .png
  python 协作/dispatch.py status            # 任务板：运行中 / 完成 / 失败 / 孤儿 / 额度用完
  python 协作/dispatch.py show <ID>         # 只打印该任务的最终汇报（out.md）
  python 协作/dispatch.py hold <名字> [说明] / free <名字>   # 登记 Sonnet 子智能体、渲染等占用的槽位
  python 协作/dispatch.py balance           # DeepSeek 余额

worker：
  ds        DeepSeek 纯文本 API（最便宜；不能碰文件，输出就是回答）            默认 deepseek-flash / effort high
  ds-agent  Claude Code CLI 接 DeepSeek 后端（能读写文件、跑脚本）              默认 deepseek-flash / effort high
  codex     Codex CLI（GPT，能读写文件、跑脚本、生图）                         默认 gpt-6.1-sol / effort high

每个任务一个目录 协作/任务/<ID>/：prompt.md（发出去的完整任务单）、out.md（最终汇报）、log.txt、meta.json。
主智能体只读 out.md；交付物写在任务单指定的路径里。主智能体掉线后，靠这些文件 + 交接.md 恢复。
"""
import sys, os, json, time, argparse, subprocess, shutil, re, datetime, signal

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
TASKS = os.path.join(ROOT, '任务')
MAX_SLOTS = 4
DEFAULTS = {
    'ds':       dict(model='deepseek-flash', effort='high', timeout=300),
    'ds-agent': dict(model='deepseek-flash', effort='high', timeout=900),
    'codex':    dict(model='gpt-6.1-sol',    effort='high', timeout=1500),
}
# 每个 worker 收到的固定前缀：限定汇报格式，省主智能体的 token
PREAMBLE = {
    'ds': '你是一个执行具体子任务的助手。严格按任务单的输出格式作答，不寒暄、不复述任务。\n\n',
    'agent': (
        '你是主智能体派出的子智能体，在 Windows 上工作（工作区 D:\\像素风2d知识，路径含中文：'
        'OpenCV 读写图片用 np.fromfile/imdecode 与 imencode/tofile）。\n'
        '规则：只做任务单里的事；只写任务单允许的路径；不删除任务单没点名的文件；不碰密钥文件；不联网下载可执行文件。\n'
        '做不到或有疑问时，不要猜，停下来在汇报里写「阻塞：原因」。\n'
        '最后一条消息就是汇报，≤ 12 行，格式：\n'
        '状态：完成 / 部分完成 / 阻塞\n产出：路径列表\n验证：你实际跑过什么、结果如何\n问题：没有就写「无」\n\n'
        '--- 任务单 ---\n'),
}


def codex_exe():
    """用本机最新的 Codex：Codex 桌面版自带的 codex.exe 往往比 npm 装的新（新版画图工具才有 transparent_background）。"""
    cands = [shutil.which('codex')]
    try:  # WindowsApps 目录不允许列举，glob 找不到，只能问 Appx 包的安装位置
        loc = subprocess.run(['powershell', '-NoProfile', '-Command', '(Get-AppxPackage -Name OpenAI.Codex).InstallLocation'],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        if loc: cands.append(os.path.join(loc, 'app', 'resources', 'codex.exe'))
    except Exception:
        pass
    best, bv = None, ()
    for c in filter(None, cands):
        try:
            v = subprocess.run([c, '--version'], capture_output=True, text=True, timeout=20).stdout
            m = re.search(r'(\d+)\.(\d+)\.(\d+)', v)
            if m and tuple(map(int, m.groups())) > bv:
                best, bv = c, tuple(map(int, m.groups()))
        except Exception:
            pass
    return best or shutil.which('codex')


def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def secret(name):
    if os.environ.get(name):
        return os.environ[name]
    p = os.path.join(ROOT, 'secrets.local.json')
    return json.load(open(p, encoding='utf-8')).get(name) if os.path.exists(p) else None


def metas():
    out = []
    if not os.path.isdir(TASKS):
        return out
    for d in sorted(os.listdir(TASKS)):
        p = os.path.join(TASKS, d, 'meta.json')
        if os.path.exists(p):
            try:
                out.append(json.load(open(p, encoding='utf-8')))
            except Exception:
                pass
    return out


def alive(pid):
    if not pid:
        return False
    r = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True)
    return str(pid) in r.stdout


def running():
    rs = []
    for m in metas():
        if m.get('status') != 'running':
            continue
        if m.get('worker') == 'hold' or alive(m.get('pid')):
            rs.append(m)
    return rs


def save(meta):
    d = os.path.join(TASKS, meta['id'])
    os.makedirs(d, exist_ok=True)
    json.dump(meta, open(os.path.join(d, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def kill_tree(pid):
    subprocess.run(['taskkill', '/T', '/F', '/PID', str(pid)], capture_output=True)


def run_proc(cmd, stdin_text, log_path, timeout, env=None, cwd=None, meta=None):
    with open(log_path, 'wb') as log:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=cwd,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        if meta is not None:
            meta['pid'] = p.pid
            save(meta)
        try:
            p.stdin.write(stdin_text.encode('utf-8'))
            p.stdin.close()
            return p.wait(timeout=timeout), False
        except subprocess.TimeoutExpired:
            kill_tree(p.pid)
            return -9, True


def do_ds(meta, prompt, d):
    import requests
    body = {'model': meta['model'], 'messages': [{'role': 'user', 'content': PREAMBLE['ds'] + prompt}],
            'max_tokens': 16000}
    if meta.get('effort') == 'none':  # 关掉思考：只适合纯格式活，实测判断类题目会答错
        body['thinking'] = {'type': 'disabled'}
    elif meta.get('effort'):
        body['reasoning_effort'] = meta['effort']  # low / high / max
    meta['pid'] = os.getpid()
    save(meta)
    r = requests.post('https://api.deepseek.com/chat/completions', json=body, timeout=meta['timeout'],
                      headers={'Authorization': 'Bearer ' + secret('DEEPSEEK_API_KEY')})
    open(os.path.join(d, 'log.txt'), 'w', encoding='utf-8').write(r.text)
    if r.status_code != 200:
        return 'failed', f'HTTP {r.status_code}: {r.text[:300]}'
    j = r.json()
    u = j.get('usage', {})
    meta['tokens'] = {'in': u.get('prompt_tokens'), 'out': u.get('completion_tokens'),
                      'cache_hit': u.get('prompt_cache_hit_tokens')}
    open(os.path.join(d, 'out.md'), 'w', encoding='utf-8').write(j['choices'][0]['message']['content'])
    return 'done', ''


def do_ds_agent(meta, prompt, d):
    env = dict(os.environ)
    for k in list(env):
        if k.startswith('CLAUDE_CODE_') or k in ('CLAUDECODE', 'ANTHROPIC_API_KEY'):
            env.pop(k)
    env.update(ANTHROPIC_BASE_URL='https://api.deepseek.com/anthropic', ANTHROPIC_AUTH_TOKEN=secret('DEEPSEEK_API_KEY'),
               ANTHROPIC_MODEL=meta['model'], ANTHROPIC_SMALL_FAST_MODEL='deepseek-flash',
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1', DISABLE_TELEMETRY='1')
    exe = shutil.which('claude')
    cmd = [exe, '-p', '--model', meta['model'], '--output-format', 'json', '--strict-mcp-config',
           '--allowedTools', 'Read,Write,Edit,Glob,Grep,Bash', '--add-dir', PROJ]
    rc, to = run_proc(cmd, PREAMBLE['agent'] + prompt, os.path.join(d, 'log.txt'), meta['timeout'], env=env,
                      cwd=meta['cwd'], meta=meta)
    if to:
        return 'timeout', f'超过 {meta["timeout"]} s，已结束进程树'
    raw = open(os.path.join(d, 'log.txt'), encoding='utf-8', errors='replace').read()
    j = None
    for line in raw.splitlines():
        if line.startswith('{') and '"result"' in line:
            try:
                j = json.loads(line)
            except ValueError:
                pass
    if not j:
        return 'failed', f'exit {rc}，没有 JSON 结果：{raw[-300:]}'
    mu = next(iter((j.get('modelUsage') or {}).values()), {})
    meta['tokens'] = {'in': mu.get('inputTokens'), 'out': mu.get('outputTokens'), 'cache_hit': mu.get('cacheReadInputTokens'),
                      'turns': j.get('num_turns')}
    open(os.path.join(d, 'out.md'), 'w', encoding='utf-8').write(j.get('result') or '')
    return ('failed' if j.get('is_error') else 'done'), ''


def do_codex(meta, prompt, d, images):
    exe = codex_exe()
    out = os.path.join(d, 'out.md')
    cmd = [exe, 'exec', '-m', meta['model'], '-s', meta.get('sandbox') or 'workspace-write', '-C', meta['cwd'],
           '--skip-git-repo-check', '--ephemeral', '--color', 'never', '-o', out]
    if meta.get('effort'):
        cmd += ['-c', f'model_reasoning_effort="{meta["effort"]}"']
    if meta['cwd'] != PROJ:
        cmd += ['--add-dir', PROJ]
    for im in images or []:
        cmd += ['-i', im]
    cmd += ['-']
    rc, to = run_proc(cmd, PREAMBLE['agent'] + prompt, os.path.join(d, 'log.txt'), meta['timeout'], cwd=meta['cwd'], meta=meta)
    log = open(os.path.join(d, 'log.txt'), encoding='utf-8', errors='replace').read()
    m = re.search(r'tokens used\s*\n?\s*([\d,]+)', log)
    if m:
        meta['tokens'] = {'total': int(m.group(1).replace(',', ''))}
    if 'usage limit' in log:
        r = re.search(r'try again at ([^.\n]+)', log)
        return 'quota', 'Codex 额度用完' + (f'，{r.group(1)} 恢复' if r else '')
    if to:
        return 'timeout', f'超过 {meta["timeout"]} s，已结束进程树'
    if rc != 0 or not os.path.exists(out):
        return 'failed', f'exit {rc}：' + log[-300:].replace('\n', ' ')
    return 'done', ''


IMG_LEAN = ('只做一件事：调用内置图像生成工具 image_gen 生成 1 张图，逐字使用下面的提示词（不改写、不增删）{ref}{alpha}。'
            '不要读任何文件或技能文档，不要运行任何命令，不要复制或检查文件，生成完直接回复「OK」。\n\n')
GEN = os.path.expanduser('~/.codex/generated_images')


def _img_job(job, meta, ref, timeout, model, effort):
    """一个 codex 进程出一张图：看到图片落盘就复制过去并结束进程（不等它空转收尾，省 10–17 s）。"""
    import threading
    prompt = open(job, encoding='utf-8').read().strip()
    target = os.path.splitext(job)[0] + '.png'
    exe = EXE
    cmd = [exe, 'exec', '-m', model, '-c', f'model_reasoning_effort="{effort}"', '-s', 'read-only',
           '--skip-git-repo-check', '--ephemeral', '--color', 'never', '--json']
    for r in ref or []:
        cmd += ['-i', r]
    cmd += ['-']
    t0 = time.time()
    before = set()
    for d in os.listdir(GEN) if os.path.isdir(GEN) else []:
        before.add(d)
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    meta['pid'] = p.pid; save(meta)
    alpha = '；调用时把 transparent_background 设为 true（要真透明背景）' if ALPHA else ''
    p.stdin.write((IMG_LEAN.format(ref='；附带的图片是参考图' if ref else '', alpha=alpha) + prompt).encode('utf-8')); p.stdin.close()
    st = {'tid': None, 'log': []}

    def reader():
        for line in p.stdout:
            s = line.decode('utf-8', 'replace')
            st['log'].append(s)
            if st['tid'] is None and '"thread.started"' in s:
                try: st['tid'] = json.loads(s).get('thread_id')
                except ValueError: pass
    th = threading.Thread(target=reader, daemon=True); th.start()
    found, last = None, (None, -1)
    while time.time() - t0 < timeout:
        dirs = [st['tid']] if st['tid'] else [d for d in os.listdir(GEN) if d not in before]
        pngs = [os.path.join(GEN, d, f) for d in dirs if d and os.path.isdir(os.path.join(GEN, d))
                for f in os.listdir(os.path.join(GEN, d)) if f.endswith('.png')]
        if pngs:
            f = max(pngs, key=os.path.getmtime); sz = os.path.getsize(f)
            if last == (f, sz) and sz > 0:
                found = f; break
            last = (f, sz)
        if p.poll() is not None and not pngs:
            break
        time.sleep(1.0)
    kill_tree(p.pid)
    log = ''.join(st['log'])
    open(os.path.join(TASKS, meta['id'], 'log.txt'), 'w', encoding='utf-8').write(log)
    open(os.path.join(TASKS, meta['id'], 'prompt.md'), 'w', encoding='utf-8').write(prompt)
    if found:
        shutil.copy(found, target)
        return 'done', target
    if 'usage limit' in log:
        r = re.search(r'try again at ([^.\n"]+)', log)
        return 'quota', 'Codex 额度用完' + (f'，{r.group(1)} 恢复' if r else '')
    return ('timeout' if time.time() - t0 >= timeout else 'failed'), log[-200:].replace('\n', ' ')


def cmd_img(a):
    """并行出图：每个 .txt 是一条提示词（主智能体写的），结果存成同名 .png。每张一个 codex 进程（实测同一会话内
    多次 image_gen 是串行的；多进程才是真并行），并发数受总槽位限制。"""
    import threading
    free = MAX_SLOTS - len(running())
    par = max(0, min(a.par, free))
    if par == 0:
        print(f'满载：没有空槽位（上限 {MAX_SLOTS}）'); sys.exit(3)
    global EXE, ALPHA
    EXE, ALPHA = codex_exe(), a.alpha
    jobs = [os.path.abspath(j) for j in a.prompts]
    batch = datetime.datetime.now().strftime('%m%d-%H%M%S-img')
    results = {}
    lock = threading.Semaphore(par)

    def work(i, job):
        with lock:
            for attempt in (1, 2):
                meta = dict(id=f'{batch}-{i}', worker='img', model=a.model, effort=a.effort, cwd=PROJ, timeout=a.timeout,
                            task=job, status='running', start=now(), t0=time.time())
                save(meta)
                try:
                    stt, note = _img_job(job, meta, a.ref, a.timeout, a.model, a.effort)
                except Exception as e:
                    stt, note = 'failed', f'{type(e).__name__}: {e}'
                meta.update(status=stt, note=note, end=now(), secs=round(time.time() - meta['t0'])); save(meta)
                if stt in ('done', 'quota'):
                    break
            results[job] = (stt, meta['secs'], note)

    t0 = time.time()
    ths = [threading.Thread(target=work, args=(i, j)) for i, j in enumerate(jobs)]
    [t.start() for t in ths]; [t.join() for t in ths]
    for j in jobs:
        stt, secs, note = results[j]
        print(f'[{stt}] {secs:>4}s  {os.path.basename(j)}  {note if stt != "done" else ""}')
    print(f'共 {len(jobs)} 张，并发 {par}，总耗时 {round(time.time() - t0)} s')
    sys.exit(0 if all(r[0] == 'done' for r in results.values()) else 1)


def cmd_run(a):
    busy = running()
    if len(busy) >= MAX_SLOTS:
        print(f'满载：已有 {len(busy)} 个在跑（上限 {MAX_SLOTS}）：' + ', '.join(m['id'] for m in busy))
        sys.exit(3)
    dflt = DEFAULTS[a.worker]
    prompt = open(a.task, encoding='utf-8').read()
    slug = re.sub(r'[^\w一-龥]+', '_', os.path.splitext(os.path.basename(a.task))[0])[:24]
    tid = a.id or datetime.datetime.now().strftime('%m%d-%H%M%S-') + slug
    d = os.path.join(TASKS, tid)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'prompt.md'), 'w', encoding='utf-8').write(prompt)
    meta = dict(id=tid, worker=a.worker, model=a.model or dflt['model'], effort=a.effort or dflt['effort'],
                cwd=os.path.abspath(a.cwd or PROJ), timeout=a.timeout or dflt['timeout'], sandbox=a.sandbox,
                task=os.path.abspath(a.task), status='running', start=now(), t0=time.time())
    save(meta)
    try:
        if a.worker == 'ds':
            st, note = do_ds(meta, prompt, d)
        elif a.worker == 'ds-agent':
            st, note = do_ds_agent(meta, prompt, d)
        else:
            st, note = do_codex(meta, prompt, d, a.image)
    except Exception as e:
        st, note = 'failed', f'{type(e).__name__}: {e}'
    meta.update(status=st, note=note, end=now(), secs=round(time.time() - meta['t0']))
    save(meta)
    print(f'[{st}] {tid}  {meta["worker"]}/{meta["model"]}  {meta["secs"]} s  {meta.get("tokens", "")}  {note}')
    if st == 'done' and not a.quiet:
        txt = open(os.path.join(d, 'out.md'), encoding='utf-8').read()
        print(txt if len(txt) < 1500 else txt[:1500] + f'\n…（共 {len(txt)} 字，全文见 {d}\\out.md）')
    sys.exit(0 if st == 'done' else 1)


def cmd_status(a):
    ms = metas()
    if not ms:
        print('任务板为空')
        return
    rows = []
    for m in ms[-a.n:]:
        st = m.get('status')
        if st == 'running' and m.get('worker') != 'hold' and not alive(m.get('pid')):
            st = 'orphan'  # 进程已不在但没写结束：主智能体或调度器中途死了，需要重跑
        el = round(time.time() - m.get('t0', time.time())) if st == 'running' else m.get('secs', '')
        over = ' ⚠超时' if st == 'running' and m.get('timeout') and el > m['timeout'] else ''
        rows.append(f'{st:8} {m["id"]:34} {m.get("worker", ""):8} {str(m.get("model") or ""):16} {el}s{over}  {m.get("note", "")}')
    print('\n'.join(rows))
    print(f'在跑 {len(running())}/{MAX_SLOTS}')


def cmd_hold(a):
    save(dict(id='hold-' + a.name, worker='hold', model='', status='running', start=now(), t0=time.time(), note=a.desc or ''))
    print(f'已占用槽位 hold-{a.name}；在跑 {len(running())}/{MAX_SLOTS}')


def cmd_free(a):
    p = os.path.join(TASKS, 'hold-' + a.name, 'meta.json')
    m = json.load(open(p, encoding='utf-8'))
    m.update(status='done', end=now(), secs=round(time.time() - m['t0']))
    save(m)
    print(f'已释放 hold-{a.name}')


def cmd_show(a):
    print(open(os.path.join(TASKS, a.id, 'out.md'), encoding='utf-8').read())


def cmd_balance(a):
    import requests
    r = requests.get('https://api.deepseek.com/user/balance', timeout=20,
                     headers={'Authorization': 'Bearer ' + secret('DEEPSEEK_API_KEY')}).json()
    print(' '.join(f'{b["total_balance"]} {b["currency"]}' for b in r.get('balance_infos', [])))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    r = sp.add_parser('run')
    r.add_argument('worker', choices=list(DEFAULTS))
    r.add_argument('task')
    r.add_argument('--id'); r.add_argument('--model'); r.add_argument('--effort'); r.add_argument('--cwd')
    r.add_argument('--timeout', type=int); r.add_argument('--sandbox'); r.add_argument('--image', nargs='*')
    r.add_argument('--quiet', action='store_true')
    s = sp.add_parser('status'); s.add_argument('-n', type=int, default=20)
    h = sp.add_parser('hold'); h.add_argument('name'); h.add_argument('desc', nargs='?')
    f = sp.add_parser('free'); f.add_argument('name')
    w = sp.add_parser('show'); w.add_argument('id')
    g = sp.add_parser('img'); g.add_argument('prompts', nargs='+'); g.add_argument('--par', type=int, default=3)
    g.add_argument('--ref', nargs='*'); g.add_argument('--model', default='gpt-6.1-sol'); g.add_argument('--effort', default='low')
    g.add_argument('--timeout', type=int, default=240); g.add_argument('--alpha', action='store_true')
    sp.add_parser('balance')
    a = ap.parse_args()
    {'run': cmd_run, 'img': cmd_img, 'status': cmd_status, 'hold': cmd_hold, 'free': cmd_free, 'show': cmd_show,
     'balance': cmd_balance}[a.cmd](a)
