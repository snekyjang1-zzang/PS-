"""완성 영상 = 장면(scenes/sNN.py)을 자막 번호 순서로 이어 붙인 것.

장면 파일 규칙
    CUES = (시작자막번호, 끝자막번호)     # 이 장면이 맡는 자막 구간
    def draw(C, t, ta): ...              # t = 장면 시작 기준 초, ta = 영상 전체 기준 초
    (선택) SUBTITLE = False              # 이 장면만 자막 끄기
    (선택) FADE_IN = 0.2                 # 앞 장면에서 넘어올 때 페이드 길이(초). 기본은 하드컷

장면 i 는 자기 시작 자막의 시작 시각부터 다음 장면 시작 직전까지 화면을 책임진다(자막 사이 쉬는 구간 포함).
장면마다 영상 조각(out/_seg/sNN.mp4)으로 렌더해 두고, final 에서 조각을 이어 붙여 음성을 입힌다.
→ 장면 하나를 고치면 그 조각만 다시 렌더하면 된다.
"""
import ast, json, hashlib, importlib.util
from ui import *

SCENES_DIR = os.path.join(ROOT, 'scenes')
SEG = os.path.join(OUTDIR, '_seg')
SCENE_OUT = os.path.join(OUTDIR, 'scenes')

LEAD = float(os.environ.get('MG_SCENE_LEAD', '0') or 0)     # project.json 의 style.scene_lead: 장면을 첫 낱말보다 이만큼 먼저 시작한다(등장 동작이 말과 함께 끝나게)

def scene_t0(a):
    """자막 a번에서 시작하는 장면의 시작 시각. 첫 자막에서 시작하는 장면은 0초부터."""
    return 0.0 if a == min(CUES) else max(0.0, cs(a) - LEAD)

def is_html(s): return s['path'].lower().endswith('.html')

def local(cues):
    """장면 파일에서:  at, atw = local(CUES)   →  at(7) = 7번 자막 시작(장면 기준 초), atw(8, '단어')"""
    t0 = scene_t0(cues[0])
    return (lambda n: cs(n) - t0), (lambda n, word, occ=0: wt(n, word, occ) - t0)

def total_frames():
    if not AUDIO: raise SystemExit(f'음성 파일이 없습니다: {INPUT} (python mgp.py tts <프로젝트>)')
    return int(round(media_duration(AUDIO) * FPS))

def _read_cues(path):
    """import 하지 않고 CUES = (a, b) 만 읽는다 (다른 장면에 오류가 있어도 구간 계산은 되게)."""
    if path.lower().endswith('.html'):                           # HTML 장면: <meta name="cues" content="3-5">
        m = re.search(r'<meta\s+name=["\']cues["\']\s+content=["\'](\d+)(?:\s*-\s*(\d+))?["\']', open(path, encoding='utf-8').read())
        if not m: raise SystemExit(f'{os.path.basename(path)} 에 <meta name="cues" content="시작-끝"> 이 없습니다.')
        return int(m.group(1)), int(m.group(2) or m.group(1))
    try: tree = ast.parse(open(path, encoding='utf-8').read())
    except SyntaxError as e: raise SystemExit(f'{os.path.basename(path)} 문법 오류: {e}')
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'CUES' for t in node.targets):
            v = ast.literal_eval(node.value)
            return (int(v), int(v)) if isinstance(v, int) else (int(v[0]), int(v[1]))
    raise SystemExit(f'{os.path.basename(path)} 에 CUES = (시작자막, 끝자막) 이 없습니다.')

def scenes():
    """[{name, path, cues, a0, a1, f0, f1}] 시작 자막 순서."""
    files = [f for f in sorted(glob.glob(os.path.join(SCENES_DIR, '*.py')) + glob.glob(os.path.join(SCENES_DIR, '*.html'))) if not os.path.basename(f).startswith('_')]
    sc = sorted(({'name': os.path.splitext(os.path.basename(f))[0], 'path': f, 'cues': _read_cues(f)} for f in files), key=lambda s: s['cues'][0])
    if not sc: return []
    tot = total_frames()
    for i, s in enumerate(sc):
        s['a0'] = scene_t0(s['cues'][0])
        s['f0'] = int(round(s['a0'] * FPS))
    for i, s in enumerate(sc):
        nxt = s['cues'][1] + 1                                   # 이 장면은 자기 끝 자막의 다음 자막이 시작될 때까지
        s['f1'] = max(s['f0'] + 1, int(round(scene_t0(nxt) * FPS))) if nxt in CUES else tot
        if i + 1 < len(sc) and sc[i + 1]['cues'][0] <= s['cues'][1]: s['f1'] = max(s['f0'] + 1, sc[i + 1]['f0'])
        s['a1'] = s['f1'] / FPS
    return sc

def problems(sc=None):
    """자막 구간이 빠지거나 겹친 곳."""
    sc = scenes() if sc is None else sc
    out = []
    if not CUES: return ['자막(SRT)이 없습니다.']
    if not sc: return ['scenes/ 폴더에 장면 파일이 없습니다.']
    nums = sorted(CUES)
    if sc[0]['cues'][0] != nums[0]: out.append(f"첫 장면({sc[0]['name']})이 자막 {nums[0]}번에서 시작해야 합니다 (지금 {sc[0]['cues'][0]}번).")
    for a, b in zip(sc, sc[1:]):
        if b['cues'][0] <= a['cues'][1]: out.append(f"{a['name']}{a['cues']} 와 {b['name']}{b['cues']} 의 자막 구간이 겹칩니다.")
        elif b['cues'][0] != a['cues'][1] + 1: out.append(f"{a['name']}{a['cues']} 와 {b['name']}{b['cues']} 사이 자막 {a['cues'][1] + 1}~{b['cues'][0] - 1}번을 맡은 장면이 없습니다.")
        if b['f0'] <= a['f0']: out.append(f"{b['name']} 의 길이가 0입니다.")
    if sc[-1]['cues'][1] != nums[-1]: out.append(f"마지막 장면({sc[-1]['name']})이 자막 {nums[-1]}번까지 맡아야 합니다 (지금 {sc[-1]['cues'][1]}번).")
    for s in sc:
        for n in s['cues']:
            if n not in CUES: out.append(f"{s['name']}: 자막 {n}번이 없습니다 (자막은 {nums[0]}~{nums[-1]}번).")
    return out

def find(name, sc=None):
    sc = scenes() if sc is None else sc
    for s in sc:
        if s['name'] == name or s['name'] == os.path.splitext(os.path.basename(name))[0]: return s
    raise SystemExit(f"장면 '{name}' 이 없습니다. 있는 장면: {[s['name'] for s in sc]}")

def load(s):
    if is_html(s):
        import web, types; web.write_timing()
        return types.SimpleNamespace(HTML=True)
    if SCENES_DIR not in sys.path: sys.path.insert(0, SCENES_DIR)   # scenes/_shared.py 같은 공용 모듈 import 가능
    spec = importlib.util.spec_from_file_location('scene_' + s['name'], s['path'])
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    if not hasattr(mod, 'draw'): raise SystemExit(f"{s['name']}.py 에 def draw(C, t, ta) 가 없습니다.")
    return mod

def frame(s, mod, fi):
    """영상 전체 기준 fi번째 프레임 (uint8)."""
    if is_html(s):
        import web; return web.frame(s, fi)
    ta = fi / FPS; t = ta - s['a0']
    C = new_canvas((0, 0, 0))
    mod.draw(C, t, ta)
    fin = getattr(mod, 'FADE_IN', 0)
    if fin and s['f0'] > 0 and t < fin: fill(C, getattr(mod, 'FADE_COLOR', BGC), 1 - t / fin)
    if getattr(mod, 'SUBTITLE', True): subtitle(C, ta)
    return finish(C, fi)

def fingerprint(s):
    """조각을 다시 렌더해야 하는지 판단하는 값: 장면 코드, 공용 코드, 엔진 코드, 구간, 자막 문구·시각, 쓰인 에셋·녹화본, 마감 효과."""
    src = open(s['path'], encoding='utf-8').read()
    h = hashlib.sha1(src.encode())
    for f in sorted(glob.glob(os.path.join(SCENES_DIR, '_*.py')) + glob.glob(os.path.join(KIT, 'engine', '*.py'))): h.update(open(f, 'rb').read())
    h.update(repr((s['f0'], s['f1'], FINISH_GRAIN, FINISH_VIGNETTE, FINISH_FLICKER, PACE, SUB_STYLE, os.environ.get('MG_SUB_MERGE', '0'), MASCOT)).encode())
    h.update(repr([c for c in sorted(CUES.items()) if s['a0'] - 1 <= c[1][0] <= s['a1'] + 1]).encode())
    for f in sorted(glob.glob(os.path.join(BRAND, '*.png'))): st = os.stat(f); h.update(f'{os.path.basename(f)}:{st.st_size}:{int(st.st_mtime)}'.encode())
    if is_html(s):                                                       # HTML 장면: 공용 디자인 파일과 장면이 가져다 쓰는 파일
        for f in sorted(glob.glob(os.path.join(KIT, 'engine', 'web', '*')) + [f for f in glob.glob(os.path.join(SCENES_DIR, '_*')) if not f.endswith('_timing.js') and os.path.isfile(f)]): h.update(open(f, 'rb').read())
        for ref in sorted(set(re.findall(r"""(?:src|href)=["']([^"'#?]+)|url\(["']?([^"')]+)""", src))):
            f = os.path.normpath(os.path.join(SCENES_DIR, ref[0] or ref[1]))
            if os.path.isfile(f): st = os.stat(f); h.update(f'{f}:{st.st_size}:{int(st.st_mtime)}'.encode())
    for name in sorted(set(re.findall(r"""['"]([\w\-]+)['"]""", src))):
        for p in (os.path.join(ASSETS, name + '.png'), cap_path(name)):
            if os.path.exists(p): st = os.stat(p); h.update(f'{name}:{st.st_size}:{int(st.st_mtime)}'.encode())
    return h.hexdigest()

def seg_path(s): return os.path.join(SEG, s['name'] + '.mp4')

def is_fresh(s):
    meta = seg_path(s)[:-4] + '.json'
    if not (os.path.exists(seg_path(s)) and os.path.exists(meta)): return False
    try: return json.load(open(meta, encoding='utf-8')).get('fp') == fingerprint(s)
    except Exception: return False

def tc(x):
    m = int(x // 60); return f'{m:02d}m{x - m * 60:04.1f}s'

def render_scene(name):
    s = find(name); mod = load(s)
    os.makedirs(SEG, exist_ok=True); os.makedirs(SCENE_OUT, exist_ok=True)
    n = s['f1'] - s['f0']
    if n <= 0: raise SystemExit(f"{s['name']} 의 길이가 0입니다.")
    want = {s['f0'] + int(n * u) for u in (0.08, 0.3, 0.55, 0.8)}; prev = []
    def fr(i):
        u8 = frame(s, mod, s['f0'] + i)
        if s['f0'] + i in want: prev.append((s['f0'] + i, u8.copy()))
        return u8
    tmp = seg_path(s)[:-4] + '.tmp.mp4'
    write_video(tmp, n, fr)
    os.replace(tmp, seg_path(s))
    json.dump({'fp': fingerprint(s), 'frames': n, 'f0': s['f0']}, open(seg_path(s)[:-4] + '.json', 'w', encoding='utf-8'))
    # 확인용: 음성을 입힌 장면 단독 영상 + 미리보기 시트
    for old in glob.glob(os.path.join(SCENE_OUT, s['name'] + ' *')): os.remove(old)
    base = os.path.join(SCENE_OUT, f"{s['name']} [{tc(s['a0'])}-{tc(s['a1'])}]")
    subprocess.run([ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', seg_path(s), '-ss', f"{s['f0'] / FPS:.4f}", '-t', f'{n / FPS:.4f}', '-i', AUDIO,
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', base + '.mp4'], check=True)
    save_sheet(base + '.jpg', [f for _, f in prev], [f'{i / FPS:.1f}s' for i, _ in prev])
    return base + '.mp4'

def probe(name, times=None, out=None):
    """렌더 전에 몇 프레임만 그려 한 장으로 저장. times = 장면 기준 초 목록."""
    s = find(name); mod = load(s)
    dur = (s['f1'] - s['f0']) / FPS
    ts = list(times) if times else list(np.linspace(min(0.3, dur / 2), max(dur - 0.15, 0), 8))
    fr = [frame(s, mod, min(s['f1'] - 1, s['f0'] + int(round(t * FPS)))) for t in ts]
    out = out or os.path.join(OUTDIR, f"_probe_{s['name']}.jpg")
    return save_sheet(out, fr, [f"{s['a0'] + t:.1f}s (+{t:.1f})" for t in ts], color=(0, 200, 255))

def clip_audio():
    """대본의 [영상: 이름] 구간 가운데 소리가 있는 것: [(파일, 시작 초, 길이)]. 완성본을 만들 때 그 시각에 섞는다."""
    out = []
    for c in clip_list():
        p = cap_path(c['name'])
        if os.path.exists(p) and b'Audio:' in subprocess.run([ffmpeg_exe(), '-hide_banner', '-i', p], capture_output=True).stderr: out.append((p, c['at'], c['dur']))
    return out

def build_final(out):
    sc = scenes(); bad = problems(sc)
    if bad: raise SystemExit('장면 구성 문제를 먼저 고치세요:\n  - ' + '\n  - '.join(bad))
    stale = [s['name'] for s in sc if not is_fresh(s)]
    if stale: raise SystemExit(f'아직 렌더되지 않았거나 수정된 장면이 있습니다: {stale}\n  → python mgp.py render <프로젝트>')
    on = outro_frames()
    if on and not outro_fresh(): raise SystemExit('마무리 화면(outro.py)이 아직 렌더되지 않았습니다.\n  → python mgp.py render <프로젝트>')
    lst = os.path.join(SEG, '_concat.txt')
    open(lst, 'w', encoding='utf-8').write(''.join(f"file '{s['name']}.mp4'\n" for s in sc) + ("file '_outro.mp4'\n" if on else ''))
    base = sum(s['f1'] - s['f0'] for s in sc) / FPS; fmt = 'aformat=sample_rates=48000:channel_layouts=stereo'
    mixp = os.path.join(INPUT, '_mix', 'mix.wav')                       # tools/sound.py mix 가 만든 내레이션 + 배경음 + 효과음. 내레이션보다 새것일 때만 쓴다
    aud = mixp if (os.path.exists(mixp) and os.path.getmtime(mixp) >= os.path.getmtime(AUDIO)) else AUDIO
    cmd = [ffmpeg_exe(), '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-i', aud]
    ca = clip_audio(); say = bool(on and outro_say())
    if ca or say:                                                        # 내레이션 (+ 영상 구간의 소리) (+ 잠깐 쉼 + 마무리 멘트)
        g = [f'[1:a]{fmt},atrim=0:{base:.4f},apad=whole_dur={base:.4f}[n0]']; k = 2; cur = 'n0'
        if say: cmd += ['-i', OUTRO_WAV]; oi = k; k += 1
        for j, (p, t0, d) in enumerate(ca):
            cmd += ['-i', p]; k += 1
            g.append(f'[{k - 1}:a]{fmt},atrim=0:{d:.4f},afade=t=out:st={max(0.0, d - 0.3):.4f}:d=0.3,adelay={int(t0 * 1000)}:all=1[c{j}]')
        if ca:
            g.append(f"[n0]{''.join(f'[c{j}]' for j in range(len(ca)))}amix=inputs={len(ca) + 1}:duration=first:normalize=0[n1]"); cur = 'n1'
        if say: g.append(f'[{oi}:a]{fmt},adelay={int(outro_lead() * 1000)}:all=1,apad=whole_dur={on / FPS:.4f}[a1];[{cur}][a1]concat=n=2:v=0:a=1[a]')
        elif on: g.append(f'[{cur}]apad=pad_dur={on / FPS:.3f}[a]')
        else: g.append(f'[{cur}]anull[a]')
        cmd += ['-filter_complex', ';'.join(g), '-map', '0:v', '-map', '[a]']
    elif on: cmd += ['-map', '0:v', '-map', '1:a', '-af', f'apad=pad_dur={on / FPS:.3f}']     # 멘트 없는 마무리 화면: 무음
    else: cmd += ['-map', '0:v', '-map', '1:a']
    subprocess.run(cmd + ['-c:v', 'copy', '-c:a', 'aac', '-ar', '48000', '-ac', '2', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
    return out, sum(s['f1'] - s['f0'] for s in sc) + on

# ---------------- 마무리 화면: projects/<이름>/outro.py (선택) ----------------
# 내레이션이 끝난 뒤에 덧붙는 화면(구독 멘트 등).
#   SAY = "구독 멘트 문장"     → mgp render 가 TTS 로 input/outro.wav 를 만들고, 음성과 자막이 붙는다 (없으면 무음)
#   SECONDS = 6               → 최소 길이. SAY 가 있으면 음성 길이에 맞춰 늘어난다
#   SAY_AT = 0.7              → 화면이 뜬 뒤 멘트가 시작될 때까지(초)
#   def draw(C, t): ...       → t = 마무리 화면 시작 기준 초
OUTRO_PATH = os.path.join(ROOT, 'outro.py')
OUTRO_WAV = os.path.join(INPUT, 'outro.wav')

@functools.lru_cache(None)
def outro_mod():
    if not os.path.exists(OUTRO_PATH): return None
    if SCENES_DIR not in sys.path: sys.path.insert(0, SCENES_DIR)
    spec = importlib.util.spec_from_file_location('outro', OUTRO_PATH); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    if not hasattr(mod, 'draw'): raise SystemExit('outro.py 에 def draw(C, t) 가 없습니다.')
    return mod

def outro_say():
    """멘트 음성 정보 {'duration', 'cues'} — outro.py 에 SAY 가 있고 음성이 만들어져 있을 때만."""
    mod = outro_mod(); p = OUTRO_WAV[:-4] + '.json'
    if not mod or not getattr(mod, 'SAY', None) or not (os.path.exists(p) and os.path.exists(OUTRO_WAV)): return None
    return json.load(open(p, encoding='utf-8'))

def outro_lead(): return float(getattr(outro_mod(), 'SAY_AT', 0.7))

def outro_frames():
    mod = outro_mod()
    if not mod: return 0
    sec = float(getattr(mod, 'SECONDS', 6)); m = outro_say()
    if m: sec = max(sec, outro_lead() + m['duration'] + 1.3)
    return int(round(sec * FPS))

def _outro_fp():
    h = hashlib.sha1(open(OUTRO_PATH, 'rb').read())
    for f in sorted(glob.glob(os.path.join(SCENES_DIR, '_*.py')) + glob.glob(os.path.join(KIT, 'engine', '*.py'))): h.update(open(f, 'rb').read())
    for f in sorted(glob.glob(os.path.join(BRAND, '*.png')) + glob.glob(os.path.join(ASSETS, '*.png'))): st = os.stat(f); h.update(f'{os.path.basename(f)}:{st.st_size}:{int(st.st_mtime)}'.encode())
    h.update(repr((PACE, FINISH_GRAIN, FINISH_VIGNETTE, FINISH_FLICKER, SUB_STYLE, outro_say())).encode())
    return h.hexdigest()

def outro_fresh():
    p = os.path.join(SEG, '_outro')
    if getattr(outro_mod(), 'SAY', None) and not outro_say(): return False
    if not (os.path.exists(p + '.mp4') and os.path.exists(p + '.json')): return False
    try: return json.load(open(p + '.json', encoding='utf-8')).get('fp') == _outro_fp()
    except Exception: return False

@functools.lru_cache(None)
def _base_frames(): return total_frames()

def outro_frame(i):
    mod = outro_mod(); t = i / FPS
    C = new_canvas((0, 0, 0)); mod.draw(C, t)
    m = outro_say()
    if m and getattr(mod, 'SUBTITLE', True):                            # 멘트 자막
        for a, b, txt in m['cues']:
            if outro_lead() + a <= t < outro_lead() + b + 0.35:
                spr = sub_spr(txt); put(C, spr, W / 2, 1000, min(1.0, (W - 120) / sprite_size(spr)[0]), 1.0); break
    return finish(C, _base_frames() + i)

def render_outro():
    n = outro_frames(); os.makedirs(SEG, exist_ok=True); os.makedirs(SCENE_OUT, exist_ok=True)
    p = os.path.join(SEG, '_outro')
    write_video(p + '.tmp.mp4', n, outro_frame); os.replace(p + '.tmp.mp4', p + '.mp4')
    json.dump({'fp': _outro_fp(), 'frames': n}, open(p + '.json', 'w', encoding='utf-8'))
    save_sheet(os.path.join(SCENE_OUT, 'outro.jpg'), [outro_frame(int(n * u)) for u in (0.15, 0.4, 0.65, 0.95)], [f'+{n * u / FPS:.1f}s' for u in (0.15, 0.4, 0.65, 0.95)])
    return p + '.mp4'

def build_preview(out):
    """처음부터 이어서 렌더된 장면까지만 합친 중간 확인용 영상 (뒷부분을 아직 안 만들었어도 된다)."""
    sc = scenes(); use = []
    for i, s in enumerate(sc):
        if not is_fresh(s) or (i and s['f0'] != sc[i - 1]['f1']) or (i == 0 and s['f0'] != 0): break
        use.append(s)
    if not use: raise SystemExit('처음부터 이어지는 렌더된 장면이 없습니다. python mgp.py render <프로젝트> 를 먼저 실행하세요.')
    lst = os.path.join(SEG, '_concat_preview.txt')
    open(lst, 'w', encoding='utf-8').write(''.join(f"file '{s['name']}.mp4'\n" for s in use))
    dur = use[-1]['f1'] / FPS
    mixp = os.path.join(INPUT, '_mix', 'mix.wav')                       # 배경음·효과음을 섞어 둔 것이 내레이션보다 새것이면 그것을 쓴다 (build_final 과 같은 기준)
    aud = mixp if (os.path.exists(mixp) and os.path.getmtime(mixp) >= os.path.getmtime(AUDIO)) else AUDIO
    subprocess.run([ffmpeg_exe(), '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-t', f'{dur:.4f}', '-i', aud, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-ar', '48000', '-ac', '2', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
    return out, use
