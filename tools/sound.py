"""배경음(BGM)·효과음 생성과 믹싱 (ElevenLabs).   python tools/sound.py <프로젝트 폴더> gen | mix

projects/<이름>/sound.json:
  {"sfx":   {"pop": {"text": "soft cartoon pop", "sec": 0.5}, ...},          효과음: 영어 설명 + 길이(초)
   "music": {"main": {"prompt": "...", "sec": 150}, ...},                    배경음: 영어 설명 + 길이(초)
   "bgm":   [{"track": "main", "from": 0, "to": null, "gain_db": -21}, ...], 어느 구간에 어느 곡을(초, null = 끝까지). 곡이 짧으면 이어 붙여 반복
   "sfx_gain_db": {"pop": -14, ...}, "default_sfx_gain_db": -12}
효과음 위치는 장면 파일의 SFX = [(장면 기준 초, '이름') 또는 (초, '이름', 쓸 길이), ...] 에서 읽는다 (없는 장면은 효과음 없음).
gen: sound/ 폴더에 없는 것만 생성 (.env 의 ELEVENLABS_API_KEY).   mix: input/narration.wav + 배경음 + 효과음 → input/_mix/mix.wav
크기 기준: 내레이션 말소리 크기를 0dB 로 보고 gain_db 만큼 작게 깐다(배경음 -21dB 안팎, 효과음 -12dB 안팎).
"""
import os, sys, json, subprocess, urllib.request, urllib.error, wave, importlib.util
import numpy as np
KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SR = 48000
sys.path.insert(0, os.path.join(KIT, 'engine'))

def _key():
    k = os.environ.get('ELEVENLABS_API_KEY')
    if not k:
        for ln in open(os.path.join(KIT, '.env'), encoding='utf-8'):
            if ln.startswith('ELEVENLABS_API_KEY='): k = ln.split('=', 1)[1].strip().strip('"')
    if not k: raise SystemExit('.env 에 ELEVENLABS_API_KEY 가 없습니다.')
    return k

def _post(path, body):
    req = urllib.request.Request('https://api.elevenlabs.io' + path, json.dumps(body).encode(), {'xi-api-key': _key(), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=900) as r: return r.read()
    except urllib.error.HTTPError as e: raise SystemExit(f"ElevenLabs 요청 실패 {path}: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:400]}")

def gen(proj):
    spec = json.load(open(os.path.join(proj, 'sound.json'), encoding='utf-8')); d = os.path.join(proj, 'sound'); os.makedirs(d, exist_ok=True)
    for name, a in spec.get('sfx', {}).items():
        p = os.path.join(d, 'sfx_' + name + '.mp3')
        if os.path.exists(p): continue
        open(p, 'wb').write(_post('/v1/sound-generation', {'text': a['text'], 'duration_seconds': a['sec'], 'prompt_influence': a.get('influence', 0.6)})); print('효과음', name, flush=True)
    for name, a in spec.get('music', {}).items():
        p = os.path.join(d, 'music_' + name + '.mp3')
        if os.path.exists(p): continue
        open(p, 'wb').write(_post('/v1/music', {'prompt': a['prompt'], 'music_length_ms': int(a['sec'] * 1000)})); print('배경음', name, flush=True)

def _load(path):
    """오디오 파일 → float32 (n, 2) 48kHz"""
    from mg import ffmpeg_exe
    raw = subprocess.run([ffmpeg_exe(), '-loglevel', 'error', '-i', path, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()

def _rms(x, thr=0.012):
    m = np.abs(x).max(1) > thr
    return float(np.sqrt((x[m] ** 2).mean())) if m.sum() > SR * 0.05 else float(np.sqrt((x ** 2).mean()) + 1e-9)

def _sfx_times(proj):
    """장면 파일의 SFX 목록 → [(영상 기준 초, 이름)]"""
    os.environ['MG_PROJECT'] = os.path.abspath(proj)
    import timeline as tl
    out = []
    for s in tl.scenes():
        mod = tl.load(s)
        for it in getattr(mod, 'SFX', []) or []: out.append((s['f0'] / tl.FPS + float(it[0]), it[1], float(it[2]) if len(it) > 2 else None))
    return sorted(out)

def mix(proj):
    spec = json.load(open(os.path.join(proj, 'sound.json'), encoding='utf-8')); d = os.path.join(proj, 'sound')
    nar = _load(os.path.join(proj, 'input', 'narration.wav')); n = len(nar); ref = _rms(nar); out = nar.copy()
    for b in spec.get('bgm', []):                                   # 배경음: 구간에 맞춰 반복해 깔고 앞뒤를 서서히
        x = _load(os.path.join(d, 'music_' + b['track'] + '.mp3')); i0 = int(b.get('from', 0) * SR); i1 = n if b.get('to') is None else min(n, int(b['to'] * SR))
        if i1 <= i0: continue
        x *= ref * 10 ** (b.get('gain_db', -21) / 20) / _rms(x, 0.004)
        xf = int(SR * 3.0); body = x[:len(x) - xf]; need = i1 - i0; reps = []
        while sum(len(r) for r in reps) < need + xf:                # 반복 이음매는 3초 겹쳐 넘긴다
            seg = x.copy(); f = np.linspace(0, 1, xf)[:, None]
            if reps: seg[:xf] *= f; reps[-1][-xf:] *= (1 - f); reps[-1][-xf:] += seg[:xf]; seg = seg[xf:]
            reps.append(seg)
        y = np.concatenate(reps)[:need]; fi, fo = int(SR * b.get('fade_in', 1.5)), int(SR * b.get('fade_out', 2.5))
        y[:fi] *= np.linspace(0, 1, fi)[:, None]; y[-fo:] *= np.linspace(1, 0, fo)[:, None]; out[i0:i1] += y
    times = _sfx_times(proj); gains = spec.get('sfx_gain_db', {}); cache = {}; used = {}
    for t, name, cut in times:
        p = os.path.join(d, 'sfx_' + name + '.mp3')
        if not os.path.exists(p): print('[경고] 효과음 파일 없음:', name); continue
        if name not in cache:
            x = _load(p); m = np.where(np.abs(x).max(1) > 0.01)[0]; x = x[max(0, m[0] - 200):m[-1] + int(SR * 0.05)] if len(m) else x     # 앞의 무음을 잘라 시각을 정확히
            x *= ref * 10 ** (gains.get(name, spec.get('default_sfx_gain_db', -12)) / 20) / _rms(x, 0.004); x[-int(SR * 0.03):] *= np.linspace(1, 0, int(SR * 0.03))[:, None]; cache[name] = x
        x = cache[name]; i0 = int(t * SR)
        if cut and cut * SR < len(x): x = x[:int(cut * SR)].copy(); x[-int(SR * 0.15):] *= np.linspace(1, 0, int(SR * 0.15))[:, None]     # 길이를 지정하면 그만큼만 쓰고 끝을 줄인다
        if i0 >= n: continue
        out[i0:i0 + len(x)] += x[:n - i0]; used[name] = used.get(name, 0) + 1
    pk = np.abs(out).max()
    if pk > 0.97: out *= 0.97 / pk
    os.makedirs(os.path.join(proj, 'input', '_mix'), exist_ok=True); p = os.path.join(proj, 'input', '_mix', 'mix.wav')
    with wave.open(p, 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).clip(-32767, 32767).astype(np.int16).tobytes())
    print(f'믹스 완료: {p} ({n / SR:.1f}초) | 배경음 구간 {len(spec.get("bgm", []))}개 | 효과음 {sum(used.values())}개 {used} | 최대값 {min(pk, 0.97):.2f}')

if __name__ == '__main__':
    proj, cmd = sys.argv[1], sys.argv[2]
    os.environ['MG_PROJECT'] = os.path.abspath(proj)                    # 엔진을 불러오기 전에 프로젝트를 정해 줘야 장면을 찾는다
    try: os.environ.setdefault('MG_PACE', str(json.load(open(os.path.join(proj, 'project.json'), encoding='utf-8')).get('style', {}).get('pace', 1)))
    except Exception: pass
    {'gen': gen, 'mix': mix}[cmd](proj)
