"""API 키가 적힌 txt 파일 → .env 에 등록.   python mgp.py keys --from "키파일.txt"

키 값은 화면에 출력하지 않는다(어떤 키를 찾았는지와 글자 수만). Claude 는 이 파일을 직접 열어 읽지 말고 이 명령으로만 처리한다.
받아들이는 줄 모양 (순서·빈 줄·# 주석 자유):
  GEMINI_API_KEY=...        제미나이: ...        구글 키 = ...        AIza... (값만 있어도 알아본다)
  FAL_KEY=...               fal: ...             fal 키 = ...
  ELEVENLABS_API_KEY=...    일레븐랩스: sk_...                         sk_... (값만)
  ELEVENLABS_VOICE_ID=...   일레븐랩스 보이스 ID: ...   목소리: ...
"""
import os, re, json

NAMES = ('GEMINI_API_KEY', 'FAL_KEY', 'ELEVENLABS_API_KEY', 'ELEVENLABS_VOICE_ID')

def _name(label):
    l = label.lower().replace(' ', '').replace('_', '')
    if any(w in l for w in ('voice', '보이스', '목소리')): return 'ELEVENLABS_VOICE_ID'
    if any(w in l for w in ('eleven', '일레븐', '11labs')): return 'ELEVENLABS_API_KEY'
    if 'fal' in l or '팔' in l: return 'FAL_KEY'
    if any(w in l for w in ('gemini', '제미나이', '제미니', 'google', '구글', 'aistudio')): return 'GEMINI_API_KEY'
    return None

def _guess(v):
    if v.startswith('AIza'): return 'GEMINI_API_KEY'
    if v.startswith('sk_'): return 'ELEVENLABS_API_KEY'
    if re.fullmatch(r'[0-9a-fA-F-]{20,}:[0-9a-fA-F]{20,}', v): return 'FAL_KEY'
    if re.fullmatch(r'[A-Za-z0-9]{20}', v): return 'ELEVENLABS_VOICE_ID'
    return None

def parse(path):
    found = {}; unknown = 0
    for ln in open(path, encoding='utf-8-sig', errors='replace'):
        ln = ln.strip()
        if not ln or ln.startswith('#') or ln.startswith('//'): continue
        name = val = None
        m = re.match(r'^([^=:]{1,40}?)\s*[=:]\s*(\S.*)$', ln)
        if m and _name(m.group(1)): name, val = _name(m.group(1)), m.group(2)
        else: val = ln; name = _guess(ln.strip().strip('"').strip("'"))
        val = val.strip().strip('"').strip("'").strip()
        if val.startswith('여기에') or val.startswith('<') or not val: continue          # 양식의 빈 칸
        if name: found[name] = val
        else: unknown += 1
    return found, unknown

def apply(kit, path):
    if not os.path.isfile(path): raise SystemExit(f'파일이 없습니다: {path}')
    found, unknown = parse(path)
    if not found: raise SystemExit('이 파일에서 API 키를 찾지 못했습니다. 한 줄에 하나씩 "GEMINI_API_KEY=값" 처럼 적어 주세요 (양식: API키_양식.txt).')
    env = os.path.join(kit, '.env'); lines = open(env, encoding='utf-8-sig').read().split('\n') if os.path.exists(env) else open(os.path.join(kit, '.env.example'), encoding='utf-8').read().split('\n')
    keys = {k: v for k, v in found.items() if k != 'ELEVENLABS_VOICE_ID'}
    for k, v in keys.items():
        hit = [i for i, l in enumerate(lines) if l.strip().startswith(k + '=')]
        if hit: lines[hit[0]] = f'{k}={v}'
        else: lines.append(f'{k}={v}')
    open(env, 'w', encoding='utf-8').write('\n'.join(lines).rstrip('\n') + '\n')
    try: os.chmod(env, 0o600)
    except Exception: pass
    for k in NAMES[:3]:
        if k in keys: print(f'  [등록] {k}  ({len(keys[k])}자, 값은 표시하지 않음)')
    cp = os.path.join(kit, 'brand', 'channel.json'); vid = found.get('ELEVENLABS_VOICE_ID')
    if os.path.exists(cp):
        ch = json.load(open(cp, encoding='utf-8')); t = ch.setdefault('tts', {})
        if vid:
            t.update({'engine': 'elevenlabs', 'voice_id': vid, 'model': t.get('model') if str(t.get('model', '')).startswith('eleven') else 'eleven_v4', 'language': t.get('language', 'ko')})
            t.setdefault('settings', {'stability': 0.7, 'style': 0.0}); ch['narration'] = 'elevenlabs'
            print('  [등록] 일레븐랩스 보이스 ID → brand/channel.json (새 영상의 기본 목소리)')
        json.dump(ch, open(cp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    if unknown: print(f'  [참고] 알아보지 못한 줄 {unknown}개는 건너뛰었습니다.')
    miss = [k for k in ('GEMINI_API_KEY', 'FAL_KEY') if k not in keys and not any(l.strip().startswith(k + '=') and l.strip() != k + '=' for l in lines)]
    if miss: print(f"  [주의] 아직 없는 필수 키: {', '.join(miss)}")
    if 'ELEVENLABS_API_KEY' not in keys: print('  [참고] 일레븐랩스 키가 없으면 목소리는 Gemini 로 만들고, 배경음·효과음 생성(sound)은 쓸 수 없습니다.')
    print('키는 .env 에 저장했습니다. 원래 txt 파일은 지우거나 이 폴더 밖 안전한 곳에 두세요.\n다음: python mgp.py doctor')
