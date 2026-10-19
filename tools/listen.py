"""만든 내레이션을 받아써서 대본과 다르게 읽힌 곳을 찾는다.   python mgp.py listen <프로젝트>

음성을 2분 반씩 잘라 Gemini 로 받아쓰고(GEMINI_API_KEY), 자막 글과 비교해 다른 곳만 보여 준다.
숫자 표기 차이와 한 글자 차이는 넘긴다. 구간 경계에서 낱말이 겹쳐 잡히는 것, 소리가 같은 표기 차이(걸으러/거르러)는 잘못 읽은 것이 아니다.
결과 전체는 input/listen.json 에 남는다.
"""
import os, re, json, base64, difflib, subprocess, urllib.request

MODELS = ('gemini-2.5-flash', 'gemini-2.0-flash')
ASK = '이 한국어 음성을 들리는 그대로 받아 적어 주세요. 문장 부호는 붙이되 내용을 고치거나 요약하지 말고, 숫자는 들리는 대로 한글로 적으세요. 받아쓴 글만 출력하세요.'

def run(proj, ffmpeg, chunk=150):
    key = os.environ.get('GEMINI_API_KEY')
    if not key: raise SystemExit('.env 에 GEMINI_API_KEY 가 없습니다.')
    inp = os.path.join(proj, 'input'); srt = os.path.join(inp, 'narration.srt')
    aud = next((os.path.join(inp, f) for f in sorted(os.listdir(inp)) if f.startswith('narration.') and not f.endswith('.srt')), None)
    if not aud or not os.path.exists(srt): raise SystemExit('음성·자막이 아직 없습니다.')
    cues = []
    for b in open(srt, encoding='utf-8-sig').read().strip().split('\n\n'):
        _, tm, txt = b.split('\n', 2); s0, s1 = [(lambda h, m, s: int(h) * 3600 + int(m) * 60 + float(s.replace(',', '.')))(*x.strip().split(':')) for x in tm.split('-->')]; cues.append((s0, s1, txt.replace('\n', ' ')))
    tmp = os.path.join(inp, '_listen'); os.makedirs(tmp, exist_ok=True); res = []; i = n = 0
    while i < len(cues):
        j = i
        while j < len(cues) and cues[j][1] - cues[i][0] < chunk: j += 1
        j = max(j, i + 1); t0, t1 = cues[i][0], cues[j - 1][1]; mp3 = os.path.join(tmp, 'c%02d.mp3' % n)
        subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-ss', str(max(0, t0 - 0.15)), '-t', str(t1 - t0 + 0.4), '-i', aud, '-ac', '1', '-b:a', '64k', mp3], check=True)
        body = {'contents': [{'parts': [{'text': ASK}, {'inline_data': {'mime_type': 'audio/mp3', 'data': base64.b64encode(open(mp3, 'rb').read()).decode()}}]}], 'generationConfig': {'temperature': 0}}
        txt = ''; err = ''
        for model in MODELS:
            try:
                req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', json.dumps(body).encode(), {'Content-Type': 'application/json', 'x-goog-api-key': key})
                r = json.load(urllib.request.urlopen(req, timeout=300)); txt = ''.join(p.get('text', '') for p in r['candidates'][0]['content']['parts']).strip()
                if txt: break
            except Exception as e: err = str(e)[:200]
        if not txt: print(f'  자막 {i + 1}~{j}: 받아쓰기 실패 ({err})', flush=True)
        res.append({'from': i + 1, 'to': j, 'script': ' '.join(c[2] for c in cues[i:j]), 'heard': txt}); i = j; n += 1
    json.dump(res, open(os.path.join(inp, 'listen.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    norm = lambda s: re.sub(r'[^가-힣0-9A-Za-z]', '', s); tot = 0
    for r in res:
        if not r['heard']: continue
        a, b = norm(r['script']), norm(r['heard'])
        for op, i0, i1, j0, j1 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if op == 'equal': continue
            x, y = a[i0:i1], b[j0:j1]
            if re.search(r'\d', x) or (len(x) <= 1 and len(y) <= 1): continue
            tot += 1; print(f"  [자막 {r['from']}~{r['to']}] 대본 …{a[max(0, i0 - 8):i0]}[{x}]{a[i1:i1 + 8]}… → 들림 [{y}]")
    print(f'다르게 들린 곳 {tot}곳 (구간 {len(res)}개). 고유명사·숫자 근처는 그 문단만 들어 보고, 잘못 읽었으면 대본 표기나 tts.say_as 를 고쳐 그 문단만 다시 만든다.')
    return tot
