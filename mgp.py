"""모션그래픽 파이프라인 명령 모음.  사용: python mgp.py <명령> ...   (명령 목록: python mgp.py -h)

윈도우·맥 공통. 처음 한 번 `python mgp.py setup` 을 실행하면 전용 가상환경(.venv)이 만들어지고,
이후 모든 명령은 자동으로 그 환경에서 실행된다.
"""
import os, sys, json, shutil, argparse, subprocess

KIT = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(KIT, '.venv')
VPY = os.path.join(VENV, 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join(VENV, 'bin', 'python')
os.environ.setdefault('PYTHONUTF8', '1'); os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

def in_venv(): return os.path.realpath(sys.prefix) == os.path.realpath(VENV)

def load_env():
    p = os.path.join(KIT, '.env')
    if not os.path.exists(p): return
    for ln in open(p, encoding='utf-8-sig'):
        ln = ln.strip()
        if not ln or ln.startswith('#') or '=' not in ln: continue
        k, v = ln.split('=', 1); v = v.strip().strip('"').strip("'")
        if v and not os.environ.get(k.strip()): os.environ[k.strip()] = v

def proj_dir(name, must_exist=True):
    if not name or any(c in name for c in '\\/:*?"<>|') or name.startswith('.'):
        raise SystemExit(f'프로젝트 이름에 쓸 수 없는 문자가 있습니다: {name!r}')
    p = os.path.join(KIT, 'projects', name)
    if must_exist and not os.path.isdir(p):
        have = sorted(d for d in os.listdir(os.path.join(KIT, 'projects')) if os.path.isdir(os.path.join(KIT, 'projects', d))) if os.path.isdir(os.path.join(KIT, 'projects')) else []
        raise SystemExit(f"프로젝트 '{name}' 이 없습니다. 있는 프로젝트: {have or '없음'}  (새로 만들기: python mgp.py new {name})")
    return p

def channel():
    """채널 프로필(brand/channel.json): 채널마다 한 번 정해 두는 값. 없으면 빈 값."""
    p = os.path.join(KIT, 'brand', 'channel.json')
    try: return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    except json.JSONDecodeError as e: raise SystemExit(f'brand/channel.json 형식 오류: {e}')

def use(name):
    """엔진이 이 프로젝트 폴더를 보게 한다 (엔진 import 전에 호출)."""
    p = proj_dir(name); os.environ['MG_PROJECT'] = p
    os.environ['MG_MASCOT'] = str(channel().get('mascot') or '')
    pj = os.path.join(p, 'project.json')
    if os.path.exists(pj):
        if 'mascot' in json.load(open(pj, encoding='utf-8')): os.environ['MG_MASCOT'] = str(json.load(open(pj, encoding='utf-8'))['mascot'] or '')   # 프로젝트가 채널 기본 마스코트를 바꿔 쓸 수 있다
        st = json.load(open(pj, encoding='utf-8')).get('style', {})
        os.environ['MG_SUB_STYLE'] = str(st.get('subtitle', 'dark')); os.environ['MG_PACE'] = str(st.get('pace', 1)); os.environ['MG_SUB_MERGE'] = '1' if st.get('subtitle_merge') else '0'; os.environ['MG_SCENE_LEAD'] = str(st.get('scene_lead', 0))
        os.environ['MG_GRAIN'] = str(st.get('grain', 0)); os.environ['MG_VIGNETTE'] = '1' if st.get('vignette') else '0'; os.environ['MG_FLICKER'] = str(st.get('flicker', 0))
    for d in ('engine', 'tools'):
        if os.path.join(KIT, d) not in sys.path: sys.path.insert(0, os.path.join(KIT, d))
    return p

# ---------------- 설치 / 점검 ----------------
def cmd_setup(a):
    if sys.version_info < (3, 10): raise SystemExit(f'Python 3.10 이상이 필요합니다 (지금 {sys.version.split()[0]}). https://www.python.org/downloads/ 에서 설치하세요.')
    if not os.path.exists(VPY):
        print('1/4 전용 가상환경(.venv) 만드는 중...', flush=True); subprocess.check_call([sys.executable, '-m', 'venv', VENV])
    print('2/4 패키지 설치 중...', flush=True)
    subprocess.check_call([VPY, '-m', 'pip', 'install', '-q', '--disable-pip-version-check', '-r', os.path.join(KIT, 'requirements.txt')])
    print('3/4 녹화용 브라우저(Chromium) 설치 중...', flush=True)
    if subprocess.call([VPY, '-m', 'playwright', 'install', 'chromium']) != 0: print('  [주의] 브라우저 설치 실패. 웹 녹화(record)만 못 씁니다. 나중에 setup 을 다시 실행하세요.')
    env = os.path.join(KIT, '.env')
    if not os.path.exists(env): shutil.copy(os.path.join(KIT, '.env.example'), env); print('4/4 .env 파일을 만들었습니다. API 키 등록: python mgp.py keys --from <키가 적힌 txt>')
    else: print('4/4 .env 파일은 이미 있습니다.')
    os.makedirs(os.path.join(KIT, 'projects'), exist_ok=True)
    print(); sys.exit(subprocess.call([VPY, os.path.abspath(__file__), 'doctor']))

def cmd_doctor(a):
    ok = True
    def line(good, what, fix=''):
        nonlocal ok; ok = ok and good; print(('  [정상] ' if good else '  [문제] ') + what + ('' if good or not fix else f'  →  {fix}'))
    line(sys.version_info >= (3, 10), f'Python {sys.version.split()[0]}', 'Python 3.10 이상 설치')
    line(in_venv(), '전용 가상환경(.venv)', 'python mgp.py setup')
    for m in ('numpy', 'cv2', 'PIL', 'scipy', 'imageio_ffmpeg', 'playwright'):
        try: __import__(m); line(True, f'패키지 {m}')
        except Exception: line(False, f'패키지 {m}', 'python mgp.py setup')
    try:
        sys.path.insert(0, os.path.join(KIT, 'engine')); import mg
        r = subprocess.run([mg.ffmpeg_exe(), '-version'], capture_output=True); line(r.returncode == 0, 'ffmpeg ' + r.stdout.decode('utf-8', 'replace').split('\n')[0][:40])
    except BaseException as e: line(False, f'ffmpeg ({e})', 'python mgp.py setup')
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw: line(os.path.exists(pw.chromium.executable_path), '녹화용 브라우저(Chromium)', 'python mgp.py setup')
    except Exception: line(False, '녹화용 브라우저(Chromium)', 'python mgp.py setup')
    line(len([f for f in os.listdir(os.path.join(KIT, 'fonts')) if f.endswith('.ttf')]) >= 6, '폰트')
    line(bool(os.environ.get('GEMINI_API_KEY')), 'GEMINI_API_KEY (값은 표시하지 않음)', 'python mgp.py keys --from <키가 적힌 txt>')
    line(bool(os.environ.get('FAL_KEY')), 'FAL_KEY (값은 표시하지 않음)', 'python mgp.py keys --from <키가 적힌 txt>')
    print('  [' + ('정상' if os.environ.get('ELEVENLABS_API_KEY') else '선택') + '] ELEVENLABS_API_KEY (일레븐랩스 목소리, 배경음·효과음 생성에 필요)')
    print('\n모두 정상입니다.' if ok else '\n[문제] 표시된 항목을 해결한 뒤 다시 python mgp.py doctor 를 실행하세요.')
    sys.exit(0 if ok else 1)

def cmd_keys(a):
    """API 키 등록. --from <txt> 이면 키가 적힌 파일을 읽어 .env 에 넣고, 아니면 .env 를 메모장으로 연다. 키 값은 출력하지 않는다."""
    if getattr(a, 'src', None):
        sys.path.insert(0, os.path.join(KIT, 'tools')); import keysfile; keysfile.apply(KIT, os.path.abspath(os.path.expanduser(a.src))); return
    env = os.path.join(KIT, '.env')
    if not os.path.exists(env): shutil.copy(os.path.join(KIT, '.env.example'), env)
    if os.name == 'nt': subprocess.Popen(['notepad.exe', env])
    elif sys.platform == 'darwin': subprocess.Popen(['open', '-e', env])
    else: print('이 파일을 편집기로 열어 주세요:', env); return
    print('메모장에 .env 파일을 열었습니다.\n  GEMINI_API_KEY= 와 FAL_KEY= 뒤에 키를 붙여 넣고 저장(Ctrl+S)한 뒤 닫으세요.\n  저장 후: python mgp.py doctor')

# ---------------- 프로젝트 ----------------
def cmd_new(a):
    p = proj_dir(a.project, must_exist=False)
    if os.path.exists(p): raise SystemExit(f'이미 있는 프로젝트입니다: {p}')
    for d in ('input', 'assets', 'scenes', 'captures', 'out'): os.makedirs(os.path.join(p, d))
    T = os.path.join(KIT, 'templates')
    ch = channel()
    pj = json.load(open(os.path.join(T, 'project.json'), encoding='utf-8'))            # 채널 프로필의 기본값을 새 프로젝트에 넣는다
    pj['tts'].update(ch.get('tts', {})); pj['style'].update(ch.get('style', {}))
    json.dump(pj, open(os.path.join(p, 'project.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    aj = json.load(open(os.path.join(T, 'assets_template.json'), encoding='utf-8'))
    if ch.get('visual_style'): aj['style'] = ch['visual_style']
    json.dump(aj, open(os.path.join(p, 'assets.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    shutil.copy(os.path.join(T, 'script_template.txt'), os.path.join(p, 'input', 'script.txt'))
    shutil.copy(os.path.join(T, 'brief_template.md'), os.path.join(p, 'brief.md'))
    print(f'프로젝트를 만들었습니다: projects/{a.project}\n  대본: projects/{a.project}/input/script.txt\n  브리프: projects/{a.project}/brief.md  (담당자에게 물어서 채운다 → python mgp.py brief {a.project})')

CHANNEL_ASK = [('channel_name', '채널 이름'), ('genre', '주로 다루는 분야'), ('audience', '주 시청자'), ('tone', '말투·분위기'), ('humor', '농담·말풍선을 쓸지'),
               ('references', '참고 채널·이미지'), ('visual_style', '기본 그림 화풍'), ('outro_say', '끝 구독 멘트 문장'), ('thumbnail', '썸네일 형식'), ('avoid', '피해야 할 것')]

def cmd_brief(a):
    """채널 프로필과 영상 브리프에서 아직 안 채워진 항목을 보여 준다 (Claude 가 담당자에게 물어볼 목록)."""
    ch = channel(); miss = [lab for k, lab in CHANNEL_ASK if not str(ch.get(k, '')).strip()]
    print('채널 프로필 (brand/channel.json) — 처음 한 번만 묻는다')
    for k, lab in CHANNEL_ASK: print(f"  {'[ ]' if not str(ch.get(k, '')).strip() else '[v]'} {lab}: {ch.get(k, '')}")
    print(f"  [v] 마스코트: {ch.get('mascot') or '사용 안 함'} · 내레이션: {ch.get('narration')} · 목소리: {ch.get('tts', {}).get('voice')} · 자막: {ch.get('style', {}).get('subtitle')} · 속도: {ch.get('style', {}).get('pace')} · 실제 사진: {'사용' if ch.get('real_photos') else '사용 안 함'}")
    if miss or not ch.get('filled'): print(f"  → 아직 묻지 않은 것: {miss or '없음(확인 후 filled 를 true 로)'}")
    if a.project:
        bp = os.path.join(proj_dir(a.project), 'brief.md')
        if not os.path.exists(bp): shutil.copy(os.path.join(KIT, 'templates', 'brief_template.md'), bp)
        todo = [l.split(':')[0].lstrip('- ').strip() for l in open(bp, encoding='utf-8') if l.startswith('- ') and '(미정)' in l]
        print(f"\n영상 브리프 (projects/{a.project}/brief.md)\n  → 아직 묻지 않은 것: {todo or '없음'}")

def cmd_list(a):
    root = os.path.join(KIT, 'projects')
    for d in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        if os.path.isdir(os.path.join(root, d)):
            fin = os.path.exists(os.path.join(root, d, 'out', d + '_final.mp4'))
            print(f"  {d}" + ('   (완성 영상 있음)' if fin else ''))

def cmd_tts(a):
    p = use(a.project); import tts
    tts.run(p, {'voice': a.voice, 'style': a.style, 'unit': a.unit}, mock=a.mock, force=a.force)
    print(f'다음: python mgp.py cues {a.project}  (자막 번호와 시각 확인)')

def cmd_audio(a):
    """이미 만들어 둔 음성과 자막(SRT)을 프로젝트로 가져온다 (tts 단계를 건너뛸 때)."""
    p = proj_dir(a.project); inp = os.path.join(p, 'input')
    for src, name in ((a.audio, 'narration' + os.path.splitext(a.audio)[1].lower()), (a.srt, 'narration.srt')):
        if not os.path.exists(src): raise SystemExit(f'파일이 없습니다: {src}')
        for old in os.listdir(inp):
            if old.startswith('narration.') and (old.endswith('.srt') == name.endswith('.srt')): os.remove(os.path.join(inp, old))
        shutil.copy(src, os.path.join(inp, name))
    print(f'가져왔습니다: input/narration{os.path.splitext(a.audio)[1].lower()}, input/narration.srt\n다음: python mgp.py cues {a.project}')

def cmd_voices(a):
    sys.path.insert(0, os.path.join(KIT, 'tools'))
    if a.eleven: import tts_eleven; tts_eleven.voices(a.search)
    else: import tts; tts.voices(a.search)

def cmd_cues(a):
    use(a.project); import mg
    if not mg.CUES: raise SystemExit('자막이 없습니다. 먼저 python mgp.py tts ' + a.project)
    for n, (s, e, t) in sorted(mg.CUES.items()): print(f'{n:3d}  {int(s // 60):02d}:{s % 60:05.2f} ~ {int(e // 60):02d}:{e % 60:05.2f}  {t}')
    d = mg.media_duration(mg.AUDIO) if mg.AUDIO else 0
    print(f'\n자막 {len(mg.CUES)}개 · 음성 길이 {int(d // 60)}분 {d % 60:.1f}초')

def cmd_assets(a):
    p = use(a.project); import assets
    done = assets.run(p, only=a.ids or None, force=a.force, yes=a.yes, mock=a.mock)
    if done: print('확인용 시트:', assets.sheet(p, os.path.join(p, 'out', '_contact_sheet.jpg')))

def cmd_sheet(a):
    p = use(a.project); import assets; print(assets.sheet(p, os.path.join(p, 'out', '_contact_sheet.jpg')))

def cmd_grid(a):
    p = use(a.project); import assets; print(assets.grid(p, a.asset, os.path.join(p, 'out', f'_grid_{a.asset}.jpg')))

def cmd_status(a):
    use(a.project); import timeline as tl
    if not tl.AUDIO or not tl.CUES: print('음성·자막이 아직 없습니다 → python mgp.py tts', a.project); return
    d = tl.media_duration(tl.AUDIO); sc = tl.scenes()
    print(f'음성 {int(d // 60)}분 {d % 60:.1f}초 · 자막 {len(tl.CUES)}개 · 장면 {len(sc)}개')
    for s in sc:
        print(f"  {s['name']:8s} 자막 {s['cues'][0]:3d}~{s['cues'][1]:3d}  {tl.tc(s['a0'])} ~ {tl.tc(s['a1'])}  ({(s['f1'] - s['f0']) / tl.FPS:5.1f}초)  {'렌더됨' if tl.is_fresh(s) else '렌더 필요'}")
    if tl.outro_frames(): print(f"  outro    내레이션 뒤 마무리 화면  ({tl.outro_frames() / tl.FPS:5.1f}초)  {'렌더됨' if tl.outro_fresh() else '렌더 필요'}")
    bad = tl.problems(sc)
    print('\n장면 구성 문제:\n  - ' + '\n  - '.join(bad) if bad else '\n장면 구성 문제 없음.')

def cmd_probe(a):
    use(a.project); import timeline as tl
    print(tl.probe(a.scene, [float(x) for x in a.times] or None))

def cmd__scene(a):   # 내부용: 장면 1개 렌더
    use(a.project); import timeline as tl; print(tl.render_scene(a.scene))

def cmd_render(a):
    p = use(a.project); import timeline as tl, time
    from concurrent.futures import ThreadPoolExecutor
    sc = tl.scenes(); bad = tl.problems(sc)
    if a.scenes: todo = [tl.find(n, sc) for n in a.scenes]
    else: todo = [s for s in sc if a.all or not tl.is_fresh(s)]
    if bad: print('[주의] 장면 구성 문제:\n  - ' + '\n  - '.join(bad))
    def outro():
        mod = tl.outro_mod()
        if not mod or a.scenes: return
        if getattr(mod, 'SAY', None):                                    # 구독 멘트 음성 (글이 바뀌었을 때만 새로 합성, 유료)
            import tts; tts.say_clip(p, mod.SAY, tl.OUTRO_WAV)
        if a.all or not tl.outro_fresh():
            print(f'마무리 화면(outro.py, {tl.outro_frames() / tl.FPS:.1f}초) 렌더...', flush=True); tl.render_outro(); return True
    if not todo:
        if not outro(): print('다시 렌더할 장면이 없습니다. (전부 다시: --all)')
        return
    jobs = a.jobs or max(1, min(4, (os.cpu_count() or 2) // 2))
    logs = os.path.join(p, 'out', '_log'); os.makedirs(logs, exist_ok=True)
    print(f"장면 {len(todo)}개 렌더 (동시 {jobs}개): {[s['name'] for s in todo]}", flush=True)
    t0 = time.time(); failed = []
    def one(s):
        lp = os.path.join(logs, s['name'] + '.log')
        with open(lp, 'w', encoding='utf-8') as lf:
            rc = subprocess.call([sys.executable, os.path.abspath(__file__), '_scene', a.project, s['name']], stdout=lf, stderr=subprocess.STDOUT)
        if rc != 0:
            failed.append(s['name']); tail = open(lp, encoding='utf-8', errors='replace').read().strip().split('\n')[-12:]
            print(f"  실패 {s['name']}\n      " + '\n      '.join(tail), flush=True)
        else: print(f"  완료 {s['name']}  ({(s['f1'] - s['f0']) / tl.FPS:.1f}초 분량)", flush=True)
    with ThreadPoolExecutor(jobs) as ex: list(ex.map(one, todo))
    if not failed: outro()
    print(f'{time.time() - t0:.0f}초 걸림. 장면별 확인 영상: projects/{a.project}/out/scenes/')
    if failed: sys.exit(f'실패한 장면: {failed}')

def cmd_final(a):
    p = use(a.project); import timeline as tl
    out = os.path.join(p, 'out', a.project + '_final.mp4')
    out, frames = tl.build_final(out)
    want = tl.total_frames() + tl.outro_frames()
    shutil.copy(tl.SRT, os.path.join(p, 'out', a.project + '.srt'))
    print(f'완성: {out}\n  길이 {frames / tl.FPS:.1f}초 ({frames}프레임, 음성{' + 마무리 화면' if tl.outro_frames() else ''} 기준 {want}프레임) · {os.path.getsize(out) / 1e6:.1f}MB · 자막 파일도 같은 폴더에 복사')
    if frames != want: print('  [주의] 영상과 음성의 길이가 다릅니다. python mgp.py render --all 후 다시 시도하세요.')

def cmd_preview(a):
    p = use(a.project); import timeline as tl
    out, sc = tl.build_preview(os.path.join(p, 'out', a.project + '_preview.mp4'))
    print(f"중간 확인용: {out}\n  {sc[0]['name']} ~ {sc[-1]['name']} (자막 {sc[0]['cues'][0]}~{sc[-1]['cues'][1]}번, {sc[-1]['f1'] / tl.FPS:.1f}초) · {os.path.getsize(out) / 1e6:.1f}MB")

def cmd_check(a):
    """장면을 그려 보고 오류와 확인용 그림을 낸다 (렌더 전 점검)."""
    p = use(a.project); import check
    sheets, bad, n = check.run(p, a.scenes or None)
    for b in bad: print('  [오류] ' + b)
    print(f"그려 본 프레임 {n}장 · 오류 {len(bad)}개\n확인용 그림: " + ', '.join(sheets) if sheets else f'오류 {len(bad)}개 (그릴 장면이 없습니다)')
    if bad: sys.exit(1)

def cmd_listen(a):
    """내레이션을 받아써서 대본과 다르게 읽힌 곳을 찾는다 (Gemini, 소액 유료)."""
    p = use(a.project); import listen, mg; listen.run(p, mg.ffmpeg_exe())

def cmd_trim(a):
    """합성한 내레이션의 긴 쉼을 줄이고 속도를 맞춘다 (일레븐랩스 음성은 쉼이 길다). 자막 시각도 같이 옮긴다."""
    p = proj_dir(a.project)
    rc = subprocess.call([sys.executable, os.path.join(KIT, 'tools', 'narration_fix.py'), p, '--tempo', str(a.tempo), '--gap', str(a.gap), '--para', str(a.para)], env={**os.environ, 'MG_PROJECT': p})
    if rc == 0: print(f'다음: python mgp.py cues {a.project}  (자막 시각이 바뀌었으므로 장면은 전부 다시 렌더된다)')
    sys.exit(rc)

def cmd_sound(a):
    """배경음·효과음: gen = sound.json 에 적힌 것을 생성(일레븐랩스, 유료), mix = 내레이션과 섞기(무료)."""
    p = use(a.project); import sound
    if a.action == 'gen' and not a.yes:
        spec = json.load(open(os.path.join(p, 'sound.json'), encoding='utf-8')) if os.path.exists(os.path.join(p, 'sound.json')) else None
        if spec is None: raise SystemExit('sound.json 이 없습니다. templates/sound_template.json 을 프로젝트 폴더에 복사해 고치세요.')
        have = set(os.listdir(os.path.join(p, 'sound'))) if os.path.isdir(os.path.join(p, 'sound')) else set()
        todo = [f'효과음 {k} ({v.get("sec")}초)' for k, v in spec.get('sfx', {}).items() if f'sfx_{k}.mp3' not in have] + [f'배경음 {k} ({v.get("sec")}초)' for k, v in spec.get('music', {}).items() if f'music_{k}.mp3' not in have]
        if not todo: print('새로 만들 것이 없습니다 (sound/ 폴더에 이미 있음). 다음: python mgp.py sound ' + a.project + ' mix'); return
        print('새로 만들 것: ' + ', '.join(todo) + '\n일레븐랩스에서 유료로 생성됩니다. 담당자 확인 후 같은 명령에 --yes 를 붙여 실행하세요.'); return
    {'gen': sound.gen, 'mix': sound.mix}[a.action](p)
    if a.action == 'mix': print(f'다음: python mgp.py final {a.project}  (섞은 소리가 완성 영상에 들어간다)')

def cmd_record(a):
    p = use(a.project); import record, mg
    if a.login: record.login(p, a.login); return
    if not a.capture: raise SystemExit('녹화 대본 이름을 지정하세요: python mgp.py record <프로젝트> <이름>')
    out = record.run(p, a.capture, mg.ffmpeg_exe(), headless=a.headless)
    import ui, numpy as np   # 녹화 내용을 한 장으로 (Claude 가 직접 열어 확인)
    d = max(ui.cap_info.__wrapped__(a.capture)['duration'], 0.5); ts = list(np.linspace(0.2, d - 0.1, 8))
    sheet = os.path.join(p, 'out', f'_capture_{a.capture}.jpg')
    mg.save_sheet(sheet, [ui.vframe(out, t, 960, 540).astype('uint8') for t in ts], [f'{t:.1f}s' for t in ts])
    print('확인용 시트:', sheet)

def main():
    ap = argparse.ArgumentParser(prog='python mgp.py', description='모션그래픽 파이프라인')
    sp = ap.add_subparsers(dest='cmd', metavar='<명령>')
    def add(name, help, *args):
        s = sp.add_parser(name, help=help)
        for flags, kw in args: s.add_argument(*flags, **kw)
        return s
    P = (['project'], {'help': '프로젝트 이름'})
    add('setup', '처음 한 번: 가상환경·패키지·녹화용 브라우저 설치')
    add('doctor', '설치 상태와 API 키 점검')
    add('keys', 'API 키 등록: --from <키가 적힌 txt> 로 한 번에 넣거나, 옵션 없이 .env 를 메모장으로 열기', (['--from'], {'dest': 'src', 'metavar': '파일', 'help': '키가 적힌 txt 파일 (양식: API키_양식.txt)'}))
    add('new', '새 영상 프로젝트 폴더 만들기', P)
    add('brief', '채널 프로필·영상 브리프에서 아직 안 물어본 항목 보기', (['project'], {'nargs': '?', 'help': '프로젝트 이름(생략하면 채널 프로필만)'}))
    add('list', '프로젝트 목록')
    add('tts', '대본 → 음성 + 자막(SRT)', P, (['--voice'], {}), (['--style'], {}), (['--unit'], {'choices': ['sentence', 'paragraph']}),
        (['--force'], {'action': 'store_true', 'help': '저장분을 무시하고 전부 다시 합성'}), (['--mock'], {'action': 'store_true', 'help': 'API 없이 시험(신호음)'}))
    add('audio', '이미 있는 음성 + 자막(SRT) 가져오기 (tts 대신)', P, (['audio'], {'help': '음성 파일(mp3/wav/m4a)'}), (['srt'], {'help': '자막 파일(.srt)'}))
    add('voices', '목소리 검색 (기본 Gemini, --eleven 은 일레븐랩스 내 계정의 목소리)', (['search'], {'nargs': '?'}), (['--eleven'], {'action': 'store_true'}))
    add('cues', '자막 번호·시각 보기', P)
    add('assets', 'assets.json → 이미지 생성(fal)', P, (['ids'], {'nargs': '*', 'help': '특정 id 만 다시 생성'}), (['--yes'], {'action': 'store_true', 'help': '유료 생성 승인'}),
        (['--force'], {'action': 'store_true'}), (['--mock'], {'action': 'store_true', 'help': 'API 없이 시험(자리 표시 이미지)'}))
    add('sheet', '에셋 확인 시트', P)
    add('grid', '배경 좌표 확인용 격자 이미지', P, (['asset'], {}))
    add('status', '장면 구성·렌더 상태', P)
    add('probe', '렌더 전 장면 프레임 미리보기', P, (['scene'], {}), (['times'], {'nargs': '*', 'help': '장면 기준 초'}))
    add('render', '바뀐 장면만 렌더', P, (['scenes'], {'nargs': '*'}), (['--all'], {'action': 'store_true'}), (['-j', '--jobs'], {'type': int}))
    add('preview', '처음부터 만들어진 장면까지만 합친 중간 확인용 영상', P)
    add('final', '장면을 이어 붙여 완성 영상 만들기', P)
    add('trim', '내레이션의 긴 쉼 줄이기 + 속도 맞추기 (자막 시각도 같이)', P, (['--tempo'], {'type': float, 'default': 1.0, 'help': '속도 배율 (1.08 = 8% 빠르게)'}), (['--gap'], {'type': float, 'default': 0.30, 'help': '문장 사이에 남길 쉼(초)'}), (['--para'], {'type': float, 'default': 0.68, 'help': '문단 사이에 남길 쉼(초)'}))
    add('listen', '내레이션을 받아써서 대본과 다르게 읽힌 곳 찾기', P)
    add('check', '장면을 그려 보고 오류·겹침 확인용 그림 만들기 (렌더 전)', P, (['scenes'], {'nargs': '*'}))
    add('sound', '배경음·효과음: gen(생성, 유료) | mix(내레이션과 섞기)', P, (['action'], {'choices': ['gen', 'mix']}), (['--yes'], {'action': 'store_true', 'help': '유료 생성 승인'}))
    add('record', '웹사이트 시연 녹화', P, (['capture'], {'nargs': '?'}), (['--headless'], {'action': 'store_true', 'help': '창을 띄우지 않고 녹화'}), (['--login'], {'metavar': '주소', 'help': '녹화 없이 전용 브라우저로 직접 로그인'}))
    sp.add_parser('_scene').add_argument('project'); sp.choices['_scene'].add_argument('scene')   # 내부용(도움말에 표시 안 함)
    a = ap.parse_args()
    if not a.cmd: ap.print_help(); return
    if a.cmd != 'setup' and not in_venv():
        if os.path.exists(VPY) and not os.environ.get('MG_REEXEC'):       # 전용 환경으로 한 번만 넘어간다 (넘어간 뒤에도 환경이 달라 보이면 그대로 진행: 끝없이 다시 실행되는 것을 막는다)
            sys.exit(subprocess.call([VPY, os.path.abspath(__file__), *sys.argv[1:]], env={**os.environ, 'MG_REEXEC': '1'}))
        if not os.path.exists(VPY) and a.cmd != 'doctor': raise SystemExit('먼저 설치가 필요합니다: python mgp.py setup')
    load_env()
    globals()['cmd_' + a.cmd](a)

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: sys.exit('중단했습니다.')
