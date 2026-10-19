"""HTML 장면(scenes/sNN.html) 렌더.

페이지의 CSS 애니메이션을 전부 멈춰 두고 프레임마다 시각을 직접 지정해 찍는다 → 컴퓨터 속도와 상관없이 결과가 같다.
장면은 engine/web/kit.css · kit.js (공용 디자인) 와 scenes/_timing.js (자막·낱말 시각, 자동 생성) 를 불러 쓴다.
"""
import os, json, atexit, base64
import numpy as np, cv2
from mg import ROOT, INPUT, CUES, FPS, W, H

SCENES_DIR = os.path.join(ROOT, 'scenes')
SEEK = """t => { (window.__an || (window.__an = document.getAnimations().map(a => (a.pause(), a)))).forEach(a => a.currentTime = t * 1000); KIT.frame(t); }"""
_S = {}

def write_timing():
    """scenes/_timing.js — 자막 번호별 시각과 낱말별 시각. 낱말 시각이 없으면(가져온 음성 등) 글자 수 비율로 나눈다."""
    lead = float(os.environ.get('MG_SCENE_LEAD', '0') or 0)
    wp = os.path.join(INPUT, 'words.json'); words = json.load(open(wp, encoding='utf-8')) if os.path.exists(wp) else None
    nums = sorted(CUES); cues = {}
    for i, n in enumerate(nums):
        a, b, text = CUES[n][0], CUES[n][1], CUES[n][2]
        ws = words[i] if words and i < len(words) and ' '.join(w['w'] for w in words[i]) == text else None
        if ws is None:
            parts = text.split(' '); tot = sum(len(x) + 1 for x in parts); q = a; ws = []
            for x in parts: d = (b - a) * (len(x) + 1) / tot; ws.append({'w': x, 't0': round(q, 3), 't1': round(q + d, 3)}); q += d
        cues[n] = {'t0': round(a, 3), 't1': round(b, 3), 'text': text, 'words': ws}
    cp = os.path.join(INPUT, 'clips.json'); clips = json.load(open(cp, encoding='utf-8')) if os.path.exists(cp) else []
    body = 'window.TIMING = ' + json.dumps({'lead': lead, 'first': nums[0] if nums else 1, 'cues': cues, 'clips': clips}, ensure_ascii=False) + ';\n'
    p = os.path.join(SCENES_DIR, '_timing.js')
    if not os.path.exists(p) or open(p, encoding='utf-8').read() != body: open(p, 'w', encoding='utf-8').write(body)

def _page(s):
    if s['name'] in _S: return _S[s['name']]
    from playwright.sync_api import sync_playwright
    import pathlib
    if 'pw' not in _S:
        _S['pw'] = sync_playwright().start(); _S['br'] = _S['pw'].chromium.launch(headless=True)
        atexit.register(lambda: (_S['br'].close(), _S['pw'].stop()))
    page = _S['br'].new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
    errs = []; page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(pathlib.Path(s['path']).resolve().as_uri()); page.wait_for_load_state('networkidle'); page.evaluate('document.fonts.ready')
    if errs or not page.evaluate('!!(window.KIT && KIT.ready)'): raise SystemExit(f"{s['name']}.html 오류: {errs or 'kit.js 가 로드되지 않았습니다 (script 경로 확인)'}")
    _S[s['name']] = (page, float(page.evaluate('KIT.t0')), errs)
    return _S[s['name']]

def frame(s, fi):
    """영상 전체 기준 fi번째 프레임 (uint8 RGB)."""
    page, t0, errs = _page(s)
    page.evaluate(SEEK, fi / FPS - t0)
    for v in page.evaluate('KIT.videos(%r)' % (fi / FPS - t0)):          # 장면 안의 영상: 그 시각의 프레임을 넣어 준다
        from ui import vframe, cap_path
        k = (s['name'], v['i']); n = int(v['time'] * FPS)
        if _S.get(k) == n: continue
        fr = vframe(cap_path(v['name']), v['time'], int(v['w']), int(v['h']))
        ok, jpg = cv2.imencode('.jpg', cv2.cvtColor(fr.astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        page.evaluate('([i, u]) => KIT.setFrame(i, u)', [v['i'], 'data:image/jpeg;base64,' + base64.b64encode(jpg.tobytes()).decode()]); _S[k] = n
    if errs: raise SystemExit(f"{s['name']}.html 오류: {errs}")
    img = cv2.imdecode(np.frombuffer(page.screenshot(type='jpeg', quality=97), np.uint8), cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
