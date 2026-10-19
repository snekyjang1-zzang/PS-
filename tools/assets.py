"""에셋 목록(projects/<이름>/assets.json) → fal.ai GPT Image 2 → assets/<id>.png

assets.json
{
  "style": "모든 프롬프트 뒤에 붙는 공통 스타일 문구",
  "quality": "medium",                       # low | medium | high  (비용·시간 차이 큼)
  "assets": [
    {"id": "bg_map",     "kind": "background", "prompt": "..."},                    # 16:9 전면 배경
    {"id": "bg_map_red", "kind": "background", "edit_of": "bg_map", "prompt": "Only change: ..."},   # 같은 구도, 상태만 변경
    {"id": "c_host",     "kind": "cutout",     "prompt": "..."},                    # 캐릭터·소품 (흰 배경으로 생성 후 자동 제거)
    {"id": "c_host_sad", "kind": "cutout",     "refs": ["c_host"], "prompt": "same character, ..."}, # 같은 캐릭터 다른 포즈
    {"id": "tx_wash",    "kind": "texture",    "prompt": "..."},                    # 번짐·얼룩 (흰색 → 투명)
    {"id": "p_art",      "kind": "photo", "src": "commons:<위키미디어 공용 파일명.jpg>", "treat": "print"},  # 실제 그림·사진 → 판화풍 질감 카드 (무료, 라이선스 자동 확인)
    {"id": "ref_style",  "kind": "ref",   "file": "brand/style_refs/참고1.jpg"}                         # 담당자가 준 화풍 참고 이미지: 생성하지 않고 다른 항목의 refs 로만 쓴다
  ]
}
선택 항목: "size": {"width": 1024, "height": 1536} (세로로 긴 컷아웃), "quality": 에셋별 품질,
          "style": 에셋별 스타일(문장 또는 맨 위 "styles" 에 정의한 이름 — 예: 사물은 판화풍, 캐릭터는 다른 화풍),
          "split": true (한 장에 여러 개를 띄워 그린 세트를 <id>_0, <id>_1 ... 로 나눔. 왼쪽부터 번호).
id 는 영문·숫자·밑줄만. 장면 코드에서 put(C, 'c_host', ...) 처럼 이 id 로 쓴다.
"""
import os, re, io, sys, json, time, base64, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2
from scipy import ndimage
from PIL import Image

QUEUE = 'https://queue.fal.run/'
MODEL = 'openai/gpt-image-2'
MODEL_EDIT = 'openai/gpt-image-2/edit'
NO_TEXT = 'no text, no letters, no numbers, no labels, no watermark'
SIZES = {'background': {'width': 1920, 'height': 1088}, 'cutout': {'width': 1024, 'height': 1024}, 'texture': {'width': 1024, 'height': 1024}, 'photo': None}
SUFFIX = {'background': 'full-bleed 16:9 scene, edge to edge, ' + NO_TEXT,
          'cutout': 'single subject only, fully visible with margin on all sides, isolated on a pure flat white #FFFFFF background (no paper texture, no scenery, no ground, no cast shadow), clean edges for easy cutout, ' + NO_TEXT,
          'texture': 'isolated on a pure flat white background, ' + NO_TEXT}

# ---------------- 후처리 ----------------
def cutout_white(im):
    """흰 배경 제거 (투명 배경으로 오지 않았을 때의 대비책). im: RGB uint8"""
    rgb = im.astype(np.float32); mn = rgb.min(-1); mx = rgb.max(-1)
    nearwhite = (mn > 228) & ((mx - mn) < 28)
    lab, n = ndimage.label(nearwhite)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fg = ~np.isin(lab, list(border))
    fg = ndimage.binary_opening(fg, iterations=1)
    al = cv2.GaussianBlur(fg.astype(np.float32), (0, 0), 1.0)
    al = np.clip(al * 1.15 - 0.08, 0, 1)
    return np.dstack([im, (al * 255).astype(np.uint8)])

def crop_alpha(rgba, pad=4):
    ys, xs = np.where(rgba[..., 3] > 8)
    if len(ys) == 0: raise RuntimeError('빈 이미지입니다(전부 투명 또는 전부 흰색).')
    return rgba[max(ys.min() - pad, 0):ys.max() + pad + 1, max(xs.min() - pad, 0):xs.max() + pad + 1]

def white_to_alpha(im):
    rgb = im.astype(np.float32) / 255
    al = np.clip((1 - rgb).max(-1) * 1.05, 0, 1)
    safe = np.maximum(al, 1e-4)[..., None]
    col = np.clip((rgb - (1 - safe)) / safe, 0, 1)
    return np.dstack([(col * 255).astype(np.uint8), (al * 255).astype(np.uint8)])

def process(raw_path, kind, out_path, split=False):
    im = Image.open(raw_path)
    if kind == 'background':
        im = im.convert('RGB'); w = 1920; h = int(round(im.height * w / im.width))
        im.resize((w, h), Image.LANCZOS).save(out_path)
    elif kind == 'texture':
        Image.fromarray(white_to_alpha(np.array(im.convert('RGB')))).save(out_path)
    else:
        a = np.array(im.convert('RGBA'))
        if (a[..., 3] < 250).mean() < 0.02: a = cutout_white(a[..., :3])   # 투명 배경이 아니면 흰 배경 제거
        if split:                                                          # 한 장에 여러 개를 그린 세트: 덩어리별로 나눠 <id>_0, <id>_1 ... (왼쪽부터)
            solid = ndimage.binary_dilation(a[..., 3] > 40, iterations=6)
            lab, n = ndimage.label(solid); parts = []
            for k in range(1, n + 1):
                ys, xs = np.where(lab == k)
                if len(ys) < a.shape[0] * a.shape[1] * 0.004: continue     # 부스러기는 버린다
                piece = a.copy(); piece[..., 3] = np.where(lab == k, piece[..., 3], 0)
                parts.append((xs.min(), crop_alpha(piece)))
            parts.sort(key=lambda p: p[0])
            for i, (_, piece) in enumerate(parts): Image.fromarray(piece).save(out_path[:-4] + f'_{i}.png')
            print(f"    {os.path.basename(out_path)[:-4]}: {len(parts)}개로 나눔", flush=True)
        Image.fromarray(crop_alpha(a)).save(out_path)

# ---------------- 실제 사진·그림 (kind: "photo") ----------------
UA = {'User-Agent': 'mg-pipeline/2.0 (video production tool)'}
FREE = ('public domain', 'cc0', 'pd-', 'no restrictions')

def fetch_photo(a, proj):
    """src 를 assets/_raw/<id>.png 로 가져온다. 반환: 출처 정보 dict.
    src = "commons:<위키미디어 공용 파일명>" (라이선스 자동 확인) | http(s) 주소 | 내 컴퓨터의 파일 경로"""
    import urllib.parse
    src = a['src']; raw = os.path.join(proj, 'assets', '_raw', a['id'] + '.png'); info = {'id': a['id'], 'src': src, 'credit': a.get('credit', '')}
    if src.startswith('commons:'):
        title = 'File:' + src[8:].strip()
        q = urllib.parse.urlencode({'action': 'query', 'titles': title, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': 1600, 'format': 'json'})
        with urllib.request.urlopen(urllib.request.Request('https://commons.wikimedia.org/w/api.php?' + q, headers=UA), timeout=60) as r: d = json.load(r)
        page = next(iter(d['query']['pages'].values()))
        if 'imageinfo' not in page: raise RuntimeError(f'위키미디어 공용에 없는 파일입니다: {title}')
        ii = page['imageinfo'][0]; m = ii.get('extmetadata', {})
        lic = m.get('LicenseShortName', {}).get('value', '?'); artist = re.sub('<[^>]+>', '', m.get('Artist', {}).get('value', '')).strip().split('\n')[0][:80]
        if not any(k in lic.lower() for k in FREE) and not a.get('license_ok'):
            raise RuntimeError(f"라이선스가 '{lic}' 입니다. 퍼블릭 도메인이 아니면 조건(출처 표기 등)을 담당자가 확인한 뒤 \"license_ok\": true 를 추가하세요.")
        url = ii.get('thumburl') or ii['url']; info.update(license=lic, artist=artist, page=ii.get('descriptionurl', ''))
    elif src.startswith('http'):
        url = src; info.update(license=a.get('license', '담당자 확인 필요'))
    else:
        Image.open(src if os.path.isabs(src) else os.path.join(proj, src)).convert('RGB').save(raw); info.update(license=a.get('license', '직접 제공')); return info
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r: data = r.read()
    Image.open(io.BytesIO(data)).convert('RGB').save(raw)
    return info

def treat_photo(im, mode='engrave', maxw=1400, crop=None):
    """사진·그림을 영상의 판화풍에 맞게 처리해 흰 테두리 카드로. mode: engrave(세피아 단색 + 판화 선) | print(바랜 색 + 판화 선)
    crop = [x0, y0, x1, y1] 비율(0~1)로 잘라 쓰기."""
    if crop: w, h = im.size; im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    if im.width > maxw: im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
    a = np.array(im.convert('RGB')).astype(np.float32); h, w = a.shape[:2]
    g = cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    g = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(g).astype(np.float32) / 255
    g = np.clip((g - 0.06) / 0.88, 0, 1) ** 0.92
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    s1 = 0.5 + 0.5 * np.sin((xx + yy) * (2 * np.pi / 7.0)); s2 = 0.5 + 0.5 * np.sin((xx - yy) * (2 * np.pi / 7.0))
    ink = np.clip((s1 - g) * 5 + 0.5, 0, 1) * 0.75 + np.clip((s2 - (g + 0.38)) * 5 + 0.5, 0, 1) * 0.25      # 어두울수록 굵어지는 판화 선(어두운 곳은 교차선)
    tone = g * 0.62 + (1 - ink) * 0.38
    paper, inkc = np.array([246, 237, 216], np.float32), np.array([52, 36, 28], np.float32)
    duo = paper * tone[..., None] + inkc * (1 - tone[..., None])
    if mode == 'print':
        gray3 = a.mean(-1, keepdims=True); col = (a * 0.55 + gray3 * 0.45) * (paper / 255) * (0.80 + 0.20 * (1 - ink[..., None] * 0.6))
        out = col * 0.72 + duo * 0.28
    else: out = duo
    out += np.random.default_rng(3).normal(0, 4.5, (h, w, 1)).astype(np.float32)
    out = np.clip(out, 0, 255).astype(np.uint8)
    b = max(12, w // 80)                                                    # 흰 테두리 카드
    card = cv2.copyMakeBorder(out, b, b, b, b, cv2.BORDER_CONSTANT, value=(252, 250, 244))
    cv2.rectangle(card, (b - 2, b - 2), (b + w + 1, b + h + 1), (52, 36, 28), 2)
    return np.dstack([card, np.full(card.shape[:2], 255, np.uint8)])

# ---------------- fal 호출 ----------------
def _req(url, key, body=None):
    req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None,
                                 {'Authorization': 'Key ' + key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r: return json.load(r)

def _data_uri(path, kind):
    im = Image.open(path)
    buf = io.BytesIO()
    if kind == 'background': im.convert('RGB').save(buf, 'JPEG', quality=92); mime = 'image/jpeg'
    else: im.save(buf, 'PNG'); mime = 'image/png'
    return f'data:{mime};base64,' + base64.b64encode(buf.getvalue()).decode()

def generate(a, spec, proj, key):
    kind = a.get('kind', 'cutout'); raw = os.path.join(proj, 'assets', '_raw', a['id'] + '.png')
    style = a.get('style', spec.get('style', '')); style = spec.get('styles', {}).get(style, style)      # 에셋별 스타일: 직접 쓰거나 styles 의 이름
    suffix = SUFFIX[kind].replace(', ' + NO_TEXT, ', no watermark') if a.get('text') else SUFFIX[kind]     # "text": true = 글자가 들어가는 그림(로고 등)
    prompt = ', '.join(x for x in (a['prompt'].strip().rstrip(','), style.strip(), suffix) if x)
    body = {'prompt': prompt, 'quality': a.get('quality', spec.get('quality', 'medium')), 'num_images': 1, 'output_format': 'png',
            'background': 'opaque', 'image_size': a.get('size', SIZES[kind])}   # gpt-image-2 는 투명 배경 미지원 → 흰 배경으로 받아 제거
    refs = [a['edit_of']] if a.get('edit_of') else list(a.get('refs', []))
    model = MODEL
    if refs:
        model = MODEL_EDIT; kinds = {x['id']: x.get('kind', 'cutout') for x in spec['assets']}; byid = {x['id']: x for x in spec['assets']}
        rp = lambda r: ref_file(proj, byid[r]) if kinds.get(r) == 'ref' else os.path.join(proj, 'assets', '_raw', r + '.png')
        for r in refs:
            if not os.path.exists(rp(r)): raise RuntimeError(f"참조 에셋 {r} 이 아직 없습니다.")
        body['image_urls'] = [_data_uri(rp(r), 'background' if kinds.get(r) == 'ref' else kinds.get(r, 'cutout')) for r in refs]
        if a.get('edit_of'):
            body['prompt'] = 'Edit the attached image. Keep the exact same composition, framing, camera angle and art style. ' + prompt
    try:
        sub = _req(QUEUE + model, key, body)
        t_end = time.time() + 900
        while True:
            st = _req(sub['status_url'], key)
            if st.get('status') == 'COMPLETED': break
            if time.time() > t_end: raise RuntimeError('15분 안에 끝나지 않았습니다.')
            time.sleep(2.5)
        res = _req(sub['response_url'], key)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")
    if not res.get('images'): raise RuntimeError('이미지가 없습니다: ' + json.dumps(res, ensure_ascii=False)[:400])
    with urllib.request.urlopen(res['images'][0]['url'], timeout=180) as r: data = r.read()
    open(raw, 'wb').write(data)

def generate_mock(a, spec, proj, key=None):
    """API 없이 흐름만 시험: 자리 표시 이미지."""
    kind = a.get('kind', 'cutout'); raw = os.path.join(proj, 'assets', '_raw', a['id'] + '.png')
    rng = np.random.default_rng(abs(hash(a['id'])) % 2 ** 32); col = [int(c) for c in rng.integers(60, 200, 3)]
    if kind == 'background':
        im = np.zeros((1088, 1920, 3), np.uint8); im[:] = [min(255, c + 50) for c in col]
        for x in range(0, 1920, 120): cv2.line(im, (x, 0), (x, 1087), col, 3)
        cv2.putText(im, a['id'], (60, 120), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (30, 30, 30), 6)
    elif kind == 'texture':
        im = np.full((1024, 1024, 3), 255, np.uint8); cv2.circle(im, (512, 512), 300, col, -1); im = cv2.GaussianBlur(im, (0, 0), 50)
    else:
        im = np.zeros((1024, 1024, 4), np.uint8); cv2.circle(im, (512, 330), 170, col + [255], -1); cv2.rectangle(im, (330, 520), (694, 960), col + [255], -1)
        cv2.putText(im, a['id'], (350, 760), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255, 255), 4)
    Image.fromarray(im).save(raw)

# ---------------- 실행 ----------------
def ref_file(proj, a):
    """kind 가 ref 인 항목의 이미지 경로: 프로젝트 폴더 기준, 없으면 키트 폴더 기준"""
    kit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for base in (proj, kit):
        f = os.path.join(base, a.get('file', ''))
        if os.path.isfile(f): return f
    return os.path.join(proj, a.get('file', ''))

def load_spec(proj):
    p = os.path.join(proj, 'assets.json')
    if not os.path.exists(p): raise SystemExit(f'에셋 목록이 없습니다: {p}  (templates/assets_template.json 참고)')
    try: spec = json.load(open(p, encoding='utf-8'))
    except json.JSONDecodeError as e: raise SystemExit(f'assets.json 형식 오류: {e}')
    ids = set()
    for a in spec.get('assets', []):
        if not re.fullmatch(r'[A-Za-z0-9_]+', a.get('id', '')): raise SystemExit(f"에셋 id 는 영문·숫자·밑줄만 쓸 수 있습니다: {a.get('id')!r}")
        if a['id'] in ids: raise SystemExit(f"에셋 id 중복: {a['id']}")
        if a.get('kind') == 'ref':                                        # 화풍 참고 이미지(담당자가 준 파일): 생성하지 않고 refs 로만 쓴다
            if not a.get('file') or not os.path.exists(ref_file(proj, a)): raise SystemExit(f"{a['id']}: ref 는 file 에 이미지 경로가 필요합니다 (프로젝트 폴더나 키트 폴더 기준)")
            ids.add(a['id']); continue
        if a.get('kind', 'cutout') not in SIZES: raise SystemExit(f"{a['id']}: kind 는 background / cutout / texture / photo / ref 중 하나")
        if a.get('kind') == 'photo':
            if not a.get('src'): raise SystemExit(f"{a['id']}: photo 는 src 가 필요합니다")
        elif not a.get('prompt'): raise SystemExit(f"{a['id']}: prompt 가 없습니다")
        ids.add(a['id'])
    for a in spec.get('assets', []):
        for r in ([a['edit_of']] if a.get('edit_of') else []) + list(a.get('refs', [])):
            if r not in ids: raise SystemExit(f"{a['id']}: 참조한 에셋 {r} 이 목록에 없습니다")
    return spec

def run(proj, only=None, force=False, yes=False, mock=False, workers=3):
    spec = load_spec(proj)
    os.makedirs(os.path.join(proj, 'assets', '_raw'), exist_ok=True)
    outp = lambda a: os.path.join(proj, 'assets', a['id'] + '.png')
    todo = [a for a in spec['assets'] if a.get('kind') != 'ref' and (not only or a['id'] in only) and (force or (only and a['id'] in only) or not os.path.exists(outp(a)))]
    for o in only or []:
        if o not in {a['id'] for a in spec['assets']}: raise SystemExit(f'assets.json 에 없는 id: {o}')
    if not todo: print('새로 만들 에셋이 없습니다. (다시 만들려면 id 를 지정하거나 --force)'); return []
    q = spec.get('quality', 'medium')
    print(f"생성 대상 {len(todo)}개 (전체 {len(spec['assets'])}개 중) · 모델 {MODEL} · 품질 {q}" + (' · [모의 실행: 실제 이미지 아님]' if mock else ''))
    for a in todo:
        tag = ('  ← ' + (a.get('edit_of') or ','.join(a.get('refs', [])))) if (a.get('edit_of') or a.get('refs')) else ''
        print(f"  {a['id']:20s} {a.get('kind', 'cutout'):10s} {(a.get('prompt') or a.get('src', ''))[:60]}{tag}")
    paid = [a for a in todo if a.get('kind') != 'photo']
    if paid and not yes and not mock:
        print('\n위 이미지는 fal.ai 에서 유료로 생성됩니다. 담당자 확인 후 같은 명령에 --yes 를 붙여 실행하세요.'); return []
    key = os.environ.get('FAL_KEY')
    if not mock and paid and not key: raise SystemExit('.env 에 FAL_KEY 가 없습니다. (.env.example 참고)')
    gen = generate_mock if mock else generate
    done, failed = [], []
    def one(a):
        try:
            if a.get('kind') == 'photo':                                 # 실제 사진·그림: 내려받아 질감 처리 (무료)
                info = fetch_photo(a, proj)
                Image.fromarray(treat_photo(Image.open(os.path.join(proj, 'assets', '_raw', a['id'] + '.png')), a.get('treat', 'engrave'), crop=a.get('crop'))).save(outp(a))
                cp = os.path.join(proj, 'assets', '_credits.json'); cr = json.load(open(cp, encoding='utf-8')) if os.path.exists(cp) else {}
                cr[a['id']] = info; json.dump(cr, open(cp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                print(f"  완료 {a['id']}  ({info.get('license', '')} · {info.get('artist', '') or info.get('credit', '')})", flush=True); done.append(a['id']); return
            gen(a, spec, proj, key); process(os.path.join(proj, 'assets', '_raw', a['id'] + '.png'), a.get('kind', 'cutout'), outp(a), bool(a.get('split')))
            print(f"  완료 {a['id']}", flush=True); done.append(a['id'])
        except Exception as e:
            print(f"  실패 {a['id']}: {e}", flush=True); failed.append(a['id'])
    # 참조가 없는 것 먼저(동시에), 참조가 있는 것은 그 뒤에
    first = [a for a in todo if not (a.get('edit_of') or a.get('refs'))]; second = [a for a in todo if a not in first]
    for group in (first, second):
        with ThreadPoolExecutor(max(1, workers)) as ex: list(ex.map(one, group))
    print(f'\n성공 {len(done)}개' + (f', 실패 {len(failed)}개: {failed}  → 같은 명령을 다시 실행하면 실패한 것만 다시 시도합니다.' if failed else ''))
    return done

def sheet(proj, out):
    """에셋 전체를 id 와 함께 한 장으로 (초록 배경 = 투명 처리 확인용)."""
    from PIL import ImageDraw, ImageFont
    kit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fs = sorted(f for f in os.listdir(os.path.join(proj, 'assets')) if f.lower().endswith('.png'))
    if not fs: raise SystemExit('assets/ 에 이미지가 없습니다.')
    font = ImageFont.truetype(os.path.join(kit, 'fonts', 'NanumGothic-ExtraBold.ttf'), 22)
    cols, tw, th = 6, 320, 230
    im = Image.new('RGBA', (cols * tw, ((len(fs) + cols - 1) // cols) * th), (40, 90, 60, 255)); d = ImageDraw.Draw(im)
    for k, f in enumerate(fs):
        a = Image.open(os.path.join(proj, 'assets', f)).convert('RGBA'); a.thumbnail((tw - 8, th - 34))
        x, y = (k % cols) * tw, (k // cols) * th
        im.alpha_composite(a, (x + 4, y + 30)); d.text((x + 6, y + 3), f[:-4], fill='yellow', font=font)
    os.makedirs(os.path.dirname(out), exist_ok=True); im.convert('RGB').save(out, quality=85)
    return out

def grid(proj, name, out, step=100):
    """배경 위 좌표를 읽기 위한 격자 이미지 (지도의 도시 위치 등은 눈대중 금지, 이 이미지로 좌표를 읽는다)."""
    p = os.path.join(proj, 'assets', name + '.png')
    if not os.path.exists(p): raise SystemExit(f'에셋이 없습니다: {p}')
    im = np.array(Image.open(p).convert('RGB')); h, w = im.shape[:2]
    for x in range(0, w, step):
        cv2.line(im, (x, 0), (x, h - 1), (255, 0, 255) if x % 500 == 0 else (0, 255, 255), 2 if x % 500 == 0 else 1)
        cv2.putText(im, str(x), (x + 4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4); cv2.putText(im, str(x), (x + 4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    for y in range(0, h, step):
        cv2.line(im, (0, y), (w - 1, y), (255, 0, 255) if y % 500 == 0 else (0, 255, 255), 2 if y % 500 == 0 else 1)
        cv2.putText(im, str(y), (4, y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4); cv2.putText(im, str(y), (4, y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    os.makedirs(os.path.dirname(out), exist_ok=True); Image.fromarray(im).save(out, quality=88)
    return out
