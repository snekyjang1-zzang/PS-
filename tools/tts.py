"""대본(input/script.txt) → Gemini TTS → input/narration.wav + input/narration.srt
(project.json 의 tts.engine 이 "elevenlabs" 면 tools/tts_eleven.py 가 대신 처리한다.)

문단 단위로 합성한다(기본). 문장마다 따로 합성하면 호출마다 목소리 높이와 말투가 달라져
문장 사이에서 목소리가 바뀐 것처럼 들린다. 문단을 한 번에 읽히고, 문단끼리는 높이·음색·속도를 재서
벗어난 문단을 다시 합성한다(voicecheck.py). 문장 시각은 문단 음성 안의 쉼을 찾아 맞춘다.
(Gemini TTS 는 타임코드를 돌려주지 않는다.) 결과는 input/_tts/ 에 저장해 두어, 대본을 일부만 고치면
고친 문단만 다시 합성한다. project.json 의 tts.unit 을 "sentence" 로 하면 예전처럼 문장 단위.
"""
import os, re, io, sys, json, time, wave, base64, hashlib, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import numpy as np

API = 'https://generativelanguage.googleapis.com/v1beta'
RATE = 24000
DEFAULTS = {'model': 'gemini-3.8-flash-tts', 'voice': 'Bodi', 'style': '', 'unit': 'paragraph',
            'gap': 0.28, 'para_gap': 0.65, 'lead_in': 0.3, 'tail': 0.6, 'max_sub_chars': 30, 'workers': 4,
            'tempo': 1.0, 'voice_check': True, 'voice_retry': 3, 'voice_pitch_tol': 1.5, 'voice_rate_tol': 0.15, 'level': True}

# ---------------- 대본 → 문장 → 자막 조각 ----------------
def read_script(path):
    """[[문장, ...] 문단별]. '#' 로 시작하는 줄(소제목·메모)과 [..] 한 줄 지시문은 읽지 않는다."""
    txt = open(path, encoding='utf-8-sig').read().replace('\r\n', '\n').replace('\r', '\n')
    paras = []
    for block in re.split(r'\n\s*\n', txt):
        lines = []
        for ln in block.split('\n'):
            ln = ln.strip()
            if not ln or ln.startswith('#') or re.fullmatch(r'[\[(（【].*[\])）】]', ln): continue
            ln = re.sub(r'\*\*|__|`', '', ln)            # 마크다운 강조 기호 제거
            ln = re.sub(r'^\s*(?:[-*•]|\d+[.)])\s+', '', ln)  # 목록 기호 제거
            lines.append(ln)
        text = re.sub(r'\s+', ' ', ' '.join(lines)).strip()
        if not text: continue
        sents = [s.strip() for s in re.split(r'(?<=[.!?…。？！])["\'”’)\]]*\s+', text) if s.strip()]
        paras.append(sents)
    return paras

# ---------------- 대본의 [영상: 이름] 줄 — 내레이션을 멈추고 넣어 둔 영상을 자기 소리로 재생하는 구간 ----------------
CLIP_RE = re.compile(r'[\[【]\s*(?:영상|클립|clip)\s*[:：]\s*(.+?)(?:\s+(\d+(?:\.\d+)?)\s*초?)?\s*[\]】]', re.I)
CLIP_PAD = 0.6                                                  # 영상 앞뒤로 두는 쉼(초)

def script_clips(path):
    """[(그 줄 앞까지의 문단 수, 이름, 적어 둔 길이 또는 None)]. 줄은 문단 사이에 따로 적는다: [영상: 완성영상] / [영상: 완성영상 75]"""
    txt = open(path, encoding='utf-8-sig').read().replace('\r\n', '\n').replace('\r', '\n')
    n, out = 0, []
    for block in re.split(r'\n\s*\n', txt):
        seen, marks = False, []
        for ln in block.split('\n'):
            ln = ln.strip(); m = CLIP_RE.fullmatch(ln)
            if m: marks.append((seen, m.group(1).strip(), float(m.group(2)) if m.group(2) else None))
            elif ln and not ln.startswith('#') and not re.fullmatch(r'[\[(（【].*[\])）】]', ln): seen = True
        out += [(n + (1 if after else 0), name, sec) for after, name, sec in marks]
        n += 1 if seen else 0
    return out

def clip_marks(proj, script):
    """[(문단 번호, 이름, 길이 초)] — 길이는 captures/<이름> 영상에서 읽는다. 영상이 아직 없으면 대본에 적어 둔 길이를 임시로 쓴다."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine'))
    from mg import cap_file, media_duration
    out = []
    for n, name, sec in script_clips(script):
        p = cap_file(name)
        if os.path.exists(p): d = media_duration(p)
        elif sec: d = sec; print(f'  [알림] captures/{name} 영상이 아직 없어 대본에 적힌 {sec:g}초로 자리를 잡아 둡니다. 영상을 넣은 뒤 tts 를 다시 실행하세요.')
        else: raise SystemExit(f'대본의 [영상: {name}] 에 쓸 파일이 없습니다: {p}\n  영상을 넣거나, 길이를 임시로 적어 두세요: [영상: {name} 75]')
        out.append((n, name, d))
    return out

def clip_gap(marks, i, pos, stretch=1.0):
    """i번째 문단 앞에 들어갈 영상 구간 → (그만큼의 무음, [{'name', 'at', 'dur'}]). pos = 지금까지의 표본 수."""
    z, info = [], []
    for n, name, d in marks:
        if n != i: continue
        at = (pos + sum(len(x) for x in z)) / RATE / stretch + CLIP_PAD
        z.append(np.zeros(int(RATE * (d + 2 * CLIP_PAD) * stretch), np.int16)); info.append({'name': name, 'at': round(at, 3), 'dur': round(d, 3)})
    return (np.concatenate(z) if z else np.zeros(0, np.int16)), info

def save_clips(proj, info):
    p = os.path.join(proj, 'input', 'clips.json')
    if info:
        json.dump(info, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        for c in info: print(f"  영상 구간: {c['name']} — {int(c['at'] // 60)}분 {c['at'] % 60:.1f}초부터 {c['dur']:.1f}초 (이 동안 내레이션 없음)")
    elif os.path.exists(p): os.remove(p)

def _split_at(units, cuts):
    """함께 합성하려던 문단 사이에 영상 구간이 끼면 그 자리에서 단위를 나눈다."""
    out = []
    for u in units:
        ps, pi, s = u['paras'], u['pi'], 0
        for k in range(1, len(ps)):
            if pi + k in cuts: out.append({'pi': pi + s, 'paras': ps[s:k]}); s = k
        out.append({'pi': pi + s, 'paras': ps[s:]})
    return out

def split_sub(s, maxlen):
    """긴 문장을 자막 한 줄 길이로 나눈다 (쉼표 → 띄어쓰기 순으로, 가운데에 가까운 곳에서)."""
    s = s.strip()
    if len(s) <= maxlen: return [s]
    mid = len(s) / 2
    cands = [m.end() for m in re.finditer(r'[,，、;:]\s+', s)] or [m.end() for m in re.finditer(r'\s+', s)]
    cands = [c for c in cands if 6 <= c <= len(s) - 6] or [m.end() for m in re.finditer(r'\s+', s)]
    if not cands: return [s]
    c = min(cands, key=lambda i: abs(i - mid))
    return split_sub(s[:c], maxlen) + split_sub(s[c:], maxlen)

def weight(s):
    """읽는 길이(음절 수 추정). 숫자는 읽는 음절 수로 센다."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine'))
    from speech import speak_len
    return max(1.0, speak_len(s))

def silences(a, min_len=0.09):
    """음성 안의 쉼(조용한 구간): [(시작초, 끝초)]. 쉼표에서 생긴 쉼에 자막 경계를 맞추는 데 쓴다."""
    win = int(RATE * 0.01); n = len(a) // win
    if n < 5: return []
    e = np.abs(a[:n * win].astype(np.float32)).reshape(n, win).mean(1)
    quiet = e < max(90.0, float(np.percentile(e, 90)) * 0.06)
    out, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]: j += 1
            if (j - i) * 0.01 >= min_len and i > 0 and j < n: out.append((i * 0.01, j * 0.01))
            i = j
        else: i += 1
    return out

def boundaries(a, pieces):
    """문장 음성 a 안에서 조각들의 경계 시각(초). 읽는 길이 비례로 추정한 뒤, 가까운 쉼이 있으면 그 쉼의 가운데로 맞춘다."""
    dur = len(a) / RATE; tot = sum(weight(p) for p in pieces); acc = 0; est = []
    for p in pieces[:-1]: acc += weight(p); est.append(dur * acc / tot)
    gaps = silences(a); used = set(); out = []; prev = 0.0
    for e in est:
        cand = [(abs((g0 + g1) / 2 - e), k) for k, (g0, g1) in enumerate(gaps) if k not in used and (g0 + g1) / 2 > prev + 0.25]
        cand = [c for c in cand if c[0] <= max(0.6, dur * 0.12)]
        if cand:
            k = min(cand)[1]; used.add(k); e = (gaps[k][0] + gaps[k][1]) / 2
        e = max(e, prev + 0.25); out.append(e); prev = e
    return out

# ---------------- 합성 ----------------
def _wav_to_pcm(b):
    """WAV 바이트 → int16 mono 24k numpy."""
    try:
        with wave.open(io.BytesIO(b), 'rb') as w:
            ch, sw, sr, raw = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.readframes(w.getnframes())
    except Exception:          # 헤더 길이가 비어 있는 등 표준에서 벗어난 경우: data 청크 뒤를 그대로 읽는다
        i = b.find(b'data'); ch, sw, sr, raw = 1, 2, RATE, (b[i + 8:] if i >= 0 else b)
    if sw != 2: raise RuntimeError(f'16비트 PCM 이 아닙니다 (sample width {sw})')
    a = np.frombuffer(raw[:len(raw) // 2 * 2], np.int16)
    if ch > 1: a = a.reshape(-1, ch).mean(1).astype(np.int16)
    if sr != RATE:
        a = np.interp(np.arange(0, len(a), sr / RATE), np.arange(len(a)), a).astype(np.int16)
    return a

def _trim(a, thr=260, keep=0.04):
    """앞뒤 무음 제거 (문장 사이 간격을 일정하게 넣기 위해)."""
    idx = np.where(np.abs(a.astype(np.int32)) > thr)[0]
    if len(idx) == 0: return a[:int(RATE * 0.1)]
    k = int(RATE * keep)
    return a[max(idx[0] - k, 0):idx[-1] + k]

def synth_api(text, cfg, key):
    part = {'type': 'text', 'text': text}
    if cfg['style']: part['annotations'] = [{'type': 'speech_metadata', 'style': cfg['style']}]
    body = {'model': cfg['model'], 'input': [{'type': 'user_input', 'content': [part]}],
            'response_format': {'type': 'audio'}, 'generation_config': {'speech_config': [{'voice': cfg['voice']}]}}
    req = urllib.request.Request(API + '/interactions', json.dumps(body).encode(), {'x-goog-api-key': key, 'Content-Type': 'application/json'})
    last = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=180) as r: res = json.load(r)
            audio = [c for st in res.get('steps', []) if st.get('type') == 'model_output' for c in st.get('content', []) if c.get('type') == 'audio']
            if not audio: raise RuntimeError('응답에 음성이 없습니다: ' + json.dumps(res, ensure_ascii=False)[:300])
            return _wav_to_pcm(base64.b64decode(audio[-1]['data']))
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:500]; last = f'HTTP {e.code}: {msg}'
            if e.code in (400, 401, 403, 404): break      # 다시 해도 같은 결과
        except Exception as e:
            last = repr(e)
        time.sleep(2 ** attempt)
    hint = ''
    if last and ('voice' in last.lower() or '404' in last): hint = f"\n  목소리 이름을 확인하세요: python mgp.py voices {cfg['voice']}"
    if last and ('401' in last or '403' in last or 'API key' in last): hint = '\n  .env 의 GEMINI_API_KEY 를 확인하세요.'
    raise SystemExit(f'TTS 실패: {last}{hint}')

def synth_mock(text, cfg, key=None):
    """API 없이 흐름만 시험: 글자 수에 비례하는 길이의 신호음."""
    n = int(RATE * (0.35 + 0.13 * weight(text)))
    t = np.arange(n) / RATE
    env = np.minimum(1, np.minimum(t, t[-1] - t) / 0.05)
    return (np.sin(2 * np.pi * (180 + hash(text) % 120) * t) * env * 5000).astype(np.int16)

def _tempo(a, tempo):
    """ffmpeg atempo 로 속도만 바꾼다(음높이 유지). 0.5~2.0 배."""
    import subprocess, tempfile
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine'))
    from mg import ffmpeg_exe
    d = tempfile.mkdtemp(); src, dst = os.path.join(d, 'a.wav'), os.path.join(d, 'b.wav'); _save_wav(src, a)
    subprocess.run([ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', src, '-filter:a', f'atempo={min(2.0, max(0.5, tempo)):.4f}', '-ar', str(RATE), '-ac', '1', dst], check=True)
    out = _load_wav(dst)
    for f in (src, dst): os.remove(f)
    os.rmdir(d)
    return out

def _save_wav(path, a):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(a.astype(np.int16).tobytes())

def _load_wav(path):
    return _wav_to_pcm(open(path, 'rb').read())

def _ts(x):
    ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

# ---------------- 문단 음성 안에서 문장 위치 찾기 ----------------
def align_sentences(a, sents):
    """여러 문장을 한 번에 합성한 음성 a 에서 문장 경계를 찾는다: [(경계 시각, 그 자리 쉼 길이)] (문장 수 - 1 개).
    말하는 시간(쉼 제외) 기준으로 읽는 길이에 비례하는 지점을 예상하고, 그 근처의 쉼 가운데 긴 쉼을 고른다."""
    n = len(sents); dur = len(a) / RATE
    if n <= 1: return []
    gaps = silences(a, 0.07)
    w = np.cumsum([weight(x) for x in sents]); frac = w[:-1] / w[-1]
    if len(gaps) < n - 1:                                   # 쉼이 모자라면 길이 비례로만
        return [(float(dur * f), 0.0) for f in frac]
    glen = np.array([g1 - g0 for g0, g1 in gaps]); sp = np.array([g0 for g0, _ in gaps]) - np.concatenate([[0], np.cumsum(glen)[:-1]])
    exp = (dur - glen.sum()) * frac; tol = 0.45 + 0.02 * (dur - glen.sum())
    m = len(gaps); INF = 1e18
    cost = ((sp[None, :] - exp[:, None]) / tol) ** 2 - 2.2 * np.minimum(glen, 0.7)[None, :]
    dp = np.full((n - 1, m), INF); bk = np.zeros((n - 1, m), int); dp[0] = cost[0]
    for k in range(1, n - 1):
        best, arg = INF, 0
        for j in range(m):
            if j and dp[k - 1, j - 1] < best: best, arg = dp[k - 1, j - 1], j - 1
            if best < INF: dp[k, j] = best + cost[k, j]; bk[k, j] = arg
    j = int(np.argmin(dp[n - 2])); pick = [j]
    for k in range(n - 2, 0, -1): j = int(bk[k, j]); pick.append(j)
    return [((gaps[j][0] + gaps[j][1]) / 2, float(glen[j])) for j in reversed(pick)]

def _group(paras, unit, min_syl=45):
    """합성 단위 묶기. 문장 단위면 문장 하나씩, 문단 단위면 문단 하나씩(아주 짧은 문단은 다음 문단과 함께 —
    한두 마디만 따로 합성하면 목소리가 달라지기 쉽다). 반환: [{'pi': 첫 문단 번호, 'paras': [[문장...], ...]}]"""
    if unit != 'paragraph':
        return [{'pi': pi, 'paras': [[s]]} for pi, sents in enumerate(paras) for s in sents]
    units, hold = [], None
    for pi, sents in enumerate(paras):
        if hold: hold['paras'].append(sents); units.append(hold); hold = None; continue
        u = {'pi': pi, 'paras': [sents]}
        if sum(weight(x) for x in sents) < min_syl and pi < len(paras) - 1: hold = u
        else: units.append(u)
    if len(units) >= 2 and sum(weight(x) for x in units[-1]['paras'][0]) < min_syl and len(units[-1]['paras']) == 1:
        last = units.pop(); units[-1]['paras'] += last['paras']
    return units

def _utext(u): return ' '.join(s for p in u['paras'] for s in p)

def _stabilize(units, clips, resynth, cfg):
    """단위별 목소리(높이·음색·속도)가 전체와 다른 것을 찾아 다시 합성한다. 가장 가까운 결과를 남긴다.
    반환: (clips, 보고서 dict)"""
    import voicecheck
    lim = {'pitch': float(cfg['voice_pitch_tol']), 'rate': float(cfg['voice_rate_tol'])}
    texts = [_utext(u) for u in units]; tries = int(cfg['voice_retry']); redone = {}
    def score(m): return abs(m.get('st', 0)) / lim['pitch'] + abs(m.get('rd', 0)) / lim['rate'] + max(0, m.get('td', 1) - 1) / 2.2
    for rnd in range(tries + 1):
        ms = voicecheck.measure(clips, texts, weight); bad, summ = voicecheck.judge(ms, lim)
        if not bad or rnd == tries: break
        print(f"  목소리 검사 {rnd + 1}회: {len(bad)}개가 기준을 벗어나 다시 합성합니다 — " + ', '.join(f"#{i + 1}({'/'.join(w)})" for i, w in bad[:6]) + (' ...' if len(bad) > 6 else ''), flush=True)
        with ThreadPoolExecutor(max(1, int(cfg['workers']))) as ex: new = list(ex.map(lambda i: resynth(i), [i for i, _ in bad]))
        for (i, _), a in zip(bad, new):
            trial = list(clips); trial[i] = a
            m2 = voicecheck.measure([a], [texts[i]], weight)[0]
            # 새 결과를 기존 중앙값 기준으로 평가
            if summ['f0'] and m2['f0']: m2['st'] = 12 * np.log2(m2['f0'] / summ['f0'])
            m2['rd'] = m2['rate'] / summ['rate'] - 1
            redone[i] = redone.get(i, 0) + 1
            if score(m2) < score(ms[i]): clips[i] = a
    report = {'f0': summ['f0'], 'rate': summ['rate'], 'limits': lim, 'resynth': {str(k + 1): v for k, v in redone.items()},
              'units': [{'n': i + 1, 'text': texts[i][:40], 'sec': round(m['dur'], 1), 'pitch_semitone': round(m.get('st', 0), 2),
                         'timbre': round(m.get('td', 0), 2), 'rate_pct': round(m.get('rd', 0) * 100, 1)} for i, m in enumerate(ms)],
              'bad': [{'n': i + 1, 'why': w, 'text': texts[i][:40]} for i, w in bad]}
    return clips, report

def _level(clips):
    """단위마다 소리 크기가 다르면 목소리가 바뀐 것처럼 들린다 → 말소리 구간 크기를 중앙값에 맞춘다(최대 ±6dB)."""
    def loud(a):
        x = np.abs(a.astype(np.float32)); v = x[x > max(200.0, float(np.percentile(x, 90)) * 0.1)]
        return float(np.sqrt((v ** 2).mean())) if len(v) else 0.0
    L = [loud(a) for a in clips]; med = float(np.median([v for v in L if v > 0] or [1]))
    out = []
    for a, v in zip(clips, L):
        g = min(2.0, max(0.5, med / v)) if v > 0 else 1.0
        g = min(g, 32000.0 / max(1.0, float(np.abs(a).max())))
        out.append((a.astype(np.float32) * g).astype(np.int16))
    return out

# ---------------- 실행 ----------------
def run(proj, cfg_over=None, mock=False, force=False):
    cfg = dict(DEFAULTS)
    pj = os.path.join(proj, 'project.json')
    if os.path.exists(pj): cfg.update(json.load(open(pj, encoding='utf-8')).get('tts', {}))
    cfg.update({k: v for k, v in (cfg_over or {}).items() if v is not None})
    if cfg.get('engine') == 'elevenlabs':                       # 일레븐랩스 엔진 (tools/tts_eleven.py)
        import tts_eleven; return tts_eleven.run(proj, cfg, mock=mock, force=force)
    script = os.path.join(proj, 'input', 'script.txt')
    if not os.path.exists(script): raise SystemExit(f'대본이 없습니다: {script}')
    paras = read_script(script)
    if not paras: raise SystemExit('대본에 읽을 문장이 없습니다.')
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not mock and not key: raise SystemExit('.env 에 GEMINI_API_KEY 가 없습니다. (.env.example 참고)')
    synth = synth_mock if mock else synth_api

    # 합성 단위: 문단(기본. 한 문단을 한 번에 읽어 목소리와 흐름이 일정하다) 또는 문장(문장 시각은 정확하지만 문장마다 목소리 높이가 달라질 수 있다)
    marks = clip_marks(proj, script); tempo = float(cfg.get('tempo', 1) or 1); stretch = tempo if not mock else 1.0
    units = _split_at(_group(paras, cfg['unit']), {n for n, _, _ in marks}) if cfg['unit'] == 'paragraph' else _group(paras, cfg['unit'])
    cache = os.path.join(proj, 'input', '_tts'); os.makedirs(cache, exist_ok=True)
    def path_of(u):
        h = hashlib.sha1(json.dumps([cfg['model'], cfg['voice'], cfg['style'], _utext(u), mock], ensure_ascii=False).encode()).hexdigest()[:16]
        return os.path.join(cache, h + '.wav')
    def one(u):
        p = path_of(u)
        if os.path.exists(p) and not force: return _load_wav(p), True
        a = _trim(synth(_utext(u), cfg, key)); _save_wav(p, a); return a, False
    chars = sum(len(_utext(u)) for u in units)
    print(f"합성 {len(units)}개 ({chars}자, {'문단' if cfg['unit'] == 'paragraph' else '문장'} 단위) · 모델 {cfg['model']} · 목소리 {cfg['voice']}" + (' · [모의 실행: 실제 음성 아님]' if mock else ''), flush=True)
    with ThreadPoolExecutor(max(1, int(cfg['workers']))) as ex: res = list(ex.map(one, units))
    print(f'  새로 합성 {sum(1 for _, c in res if not c)}개, 저장분 재사용 {sum(1 for _, c in res if c)}개')
    clips = [a for a, _ in res]

    # 목소리 일관성: 문단 단위일 때 높이·음색·속도가 벗어난 문단을 다시 합성한다
    report = None
    if cfg['unit'] == 'paragraph' and cfg.get('voice_check', True) and not mock and len(units) >= 4:
        clips, report = _stabilize(units, clips, lambda i: _trim(synth(_utext(units[i]), cfg, key)), cfg)
        for u, a in zip(units, clips): _save_wav(path_of(u), a)
        json.dump(report, open(os.path.join(proj, 'input', 'voice_report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        sp = [x['pitch_semitone'] for x in report['units']]
        print(f"  목소리 검사: 높이 편차 {min(sp):+.1f} ~ {max(sp):+.1f} 반음 (허용 ±{report['limits']['pitch']}), 다시 합성한 문단 {len(report['resynth'])}개, 남은 문제 {len(report['bad'])}개")
        for b in report['bad']: print(f"    ⚠ 문단 #{b['n']} {'/'.join(b['why'])}: {b['text']} — 들어 보고 이상하면 python mgp.py tts 로 다시 실행")
    if cfg.get('level', True) and not mock: clips = _level(clips)

    out = [np.zeros(int(RATE * cfg['lead_in']), np.int16)]; pos = len(out[0]); cues = []; odd = 0; cinfo = []
    def add(x):
        nonlocal pos
        out.append(x); pos += len(x)
    for i, (u, a) in enumerate(zip(units, clips)):
        if i: add(np.zeros(int(RATE * (cfg['para_gap'] if u['pi'] != units[i - 1]['pi'] else cfg['gap'])), np.int16))
        if i == 0 or u['pi'] != units[i - 1]['pi']:
            z, ci = clip_gap(marks, u['pi'], pos, stretch); add(z); cinfo += ci
        sents = [s for p in u['paras'] for s in p]
        para_end = set(np.cumsum([len(p) for p in u['paras']])[:-1] - 1)      # 단위 안에서 문단이 끝나는 문장 번호
        cuts = align_sentences(a, sents); edges = [0.0] + [c for c, _ in cuts] + [len(a) / RATE]
        rates = [weight(s) / max(0.2, e1 - e0) for s, e0, e1 in zip(sents, edges, edges[1:])]
        odd += sum(1 for r, s in zip(rates, sents) if weight(s) >= 8 and not (0.55 < r / float(np.median(rates)) < 1.7))
        for k, s in enumerate(sents):
            seg = a[int(edges[k] * RATE):int(edges[k + 1] * RATE)]; t0 = pos / RATE
            pieces = split_sub(s, int(cfg['max_sub_chars']))
            pe = [0.0] + boundaries(seg, pieces) + [len(seg) / RATE]
            for p_, e0, e1 in zip(pieces, pe, pe[1:]): cues.append((t0 + e0, t0 + e1, p_))
            add(seg)
            if k in para_end:                                   # 함께 합성한 문단 사이: 쉼을 문단 간격만큼 늘린다
                add(np.zeros(int(RATE * max(0.0, cfg['para_gap'] - cuts[k][1])), np.int16))
    z, ci = clip_gap(marks, len(paras), pos, stretch); add(z); cinfo += ci
    add(np.zeros(int(RATE * cfg['tail']), np.int16))
    audio = np.concatenate(out)
    if abs(tempo - 1) > 1e-3 and not mock:                      # 전체 말 속도 조절(음높이는 그대로). 자막 시각도 같이 줄인다
        audio = _tempo(audio, tempo); cues = [(a / tempo, b / tempo, t) for a, b, t in cues]
    _save_wav(os.path.join(proj, 'input', 'narration.wav'), audio)
    with open(os.path.join(proj, 'input', 'narration.srt'), 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(f'{i + 1}\n{_ts(a)} --> {_ts(b)}\n{t}' for i, (a, b, t) in enumerate(cues)) + '\n')
    d = len(audio) / RATE
    save_clips(proj, cinfo)
    print(f'완료: input/narration.wav ({int(d // 60)}분 {d % 60:.1f}초), input/narration.srt (자막 {len(cues)}개)')
    if odd: print(f'  ⚠ 자막 시각이 의심되는 문장 {odd}개 (말 속도가 주변과 크게 다름) — python mgp.py cues 로 확인')
    return d, len(cues)

def voices(search=None):
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key: raise SystemExit('.env 에 GEMINI_API_KEY 가 없습니다.')
    import urllib.parse
    q = {'page_size': 100}
    if search: q['search'] = search
    req = urllib.request.Request(API + '/voices?' + urllib.parse.urlencode(q), headers={'x-goog-api-key': key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: res = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"목소리 목록 조회 실패: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")
    vs = res.get('voices', [])
    if not vs: print('결과 없음:', json.dumps(res, ensure_ascii=False)[:300]); return
    for v in vs:
        g = lambda *ks: next((str(v[k]) for k in ks if v.get(k)), '')
        print(f"{g('id', 'name'):28s} | {g('display_name', 'displayName'):16s} | {g('language_code', 'languageCode'):8s} | {g('gender'):7s} | {g('description')[:70]}")
    print(f"\n{len(vs)}개. project.json 의 tts.voice 에는 맨 앞 열(id) 또는 이름을 적는다.")


def say_clip(proj, text, out_wav, mock=False):
    """짧은 멘트(마무리 구독 멘트 등)를 음성으로. 문장별로 합성해 이어 붙이고, <out>.json 에 길이와 자막 시각을 남긴다.
    글과 목소리 설정이 그대로면 다시 합성하지 않는다. 반환: {'duration', 'cues': [[시작, 끝, 문장], ...]}"""
    cfg = dict(DEFAULTS)
    pj = os.path.join(proj, 'project.json')
    if os.path.exists(pj): cfg.update(json.load(open(pj, encoding='utf-8')).get('tts', {}))
    if cfg.get('engine') == 'elevenlabs':
        import tts_eleven; return tts_eleven.say_clip(proj, text, out_wav, cfg, mock=mock)
    meta_p = out_wav[:-4] + '.json'
    h = hashlib.sha1(json.dumps([cfg['model'], cfg['voice'], cfg['style'], text, mock], ensure_ascii=False).encode()).hexdigest()
    if os.path.exists(out_wav) and os.path.exists(meta_p):
        m = json.load(open(meta_p, encoding='utf-8'))
        if m.get('hash') == h: return m
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not mock and not key: raise SystemExit('.env 에 GEMINI_API_KEY 가 없습니다. (마무리 멘트 음성 생성에 필요)')
    sents = [x.strip() for x in re.split(r'(?<=[.!?…])\s+', re.sub(r'\s+', ' ', text).strip()) if x.strip()]
    print(f"멘트 음성 합성 {len(sents)}문장 ({len(text)}자) · 목소리 {cfg['voice']}", flush=True)
    out, pos, cues = [], 0, []
    for i, sent in enumerate(sents):
        a = _trim((synth_mock if mock else synth_api)(sent, cfg, key))
        if i: g = np.zeros(int(RATE * cfg['gap']), np.int16); out.append(g); pos += len(g)
        cues.append([round(pos / RATE, 3), round((pos + len(a)) / RATE, 3), sent]); out.append(a); pos += len(a)
    _save_wav(out_wav, np.concatenate(out))
    m = {'hash': h, 'duration': round(pos / RATE, 3), 'cues': cues, 'voice': cfg['voice']}
    json.dump(m, open(meta_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return m
