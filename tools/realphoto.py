"""실제 사진(위키미디어 공용) → 누끼 컷아웃.  python tools/realphoto.py <프로젝트 폴더> fetch|cut [id ...]

projects/<이름>/photos.json:  [{"id": "p_target", "src": "commons:파일명.jpg", "crop": [x0, y0, x1, y1](선택, 0~1 비율), "cut": true|false}, ...]
fetch: 원본을 assets/_photo/<id>.jpg 로 내려받고 출처를 assets/_photo/credits.json 에 남긴다 (라이선스·작가·주소).
cut:   fal 배경 제거(birefnet)로 누끼를 따 assets/<id>.png 로 저장한다. cut 이 false 면 잘라 내기만 한 사진을 그대로 저장한다.
"""
import os, sys, io, re, json, time, base64, urllib.request, urllib.parse, urllib.error
import numpy as np
from PIL import Image
UA = {'User-Agent': 'mg-pipeline/2.0 (video production tool)'}

def fetch(a, proj):
    title = 'File:' + a['src'][8:].strip()
    q = urllib.parse.urlencode({'action': 'query', 'titles': title, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': 2400, 'format': 'json'})
    d = json.load(urllib.request.urlopen(urllib.request.Request('https://commons.wikimedia.org/w/api.php?' + q, headers=UA), timeout=60))
    page = next(iter(d['query']['pages'].values()))
    if 'imageinfo' not in page: raise RuntimeError('위키미디어 공용에 없는 파일: ' + title)
    ii = page['imageinfo'][0]; m = ii.get('extmetadata', {})
    lic = m.get('LicenseShortName', {}).get('value', '?'); artist = re.sub('<[^>]+>', '', m.get('Artist', {}).get('value', '')).strip().split('\n')[0][:80]
    data = urllib.request.urlopen(urllib.request.Request(ii.get('thumburl') or ii['url'], headers=UA), timeout=180).read()
    out = os.path.join(proj, 'assets', '_photo', a['id'] + '.jpg'); Image.open(io.BytesIO(data)).convert('RGB').save(out, quality=93)
    return {'id': a['id'], 'file': a['src'][8:], 'license': lic, 'artist': artist, 'page': ii.get('descriptionurl', '')}

def sky_cut(rgb, tol=14, grad=True, close=9):
    """건물 사진의 하늘만 지운다(건물은 배경 제거 모델이 잘 못 딴다). 위쪽 가장자리에서 이어진, 그 자리 하늘색과 비슷한 영역을 하늘로 본다.
    아래쪽(도로)은 crop 으로 미리 잘라 둔다. tol = 색 허용 범위(하늘이 건물과 비슷한 색이면 낮춘다)."""
    import cv2
    h, w = rgb.shape[:2]; blur = cv2.GaussianBlur(rgb, (0, 0), 1.5)
    sky = np.zeros((h + 2, w + 2), np.uint8)
    for x in range(2, w - 2, max(6, w // 80)):
        if sky[1, x + 1] == 0: cv2.floodFill(blur.copy(), sky, (x, 0), 0, (tol,) * 3, (tol,) * 3, 4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE)
    g = max(3, tol // 5); sky2 = np.zeros((h + 2, w + 2), np.uint8)                     # 2차: 구름처럼 색이 서서히 변하는 곳은 이웃 색 기준으로 따라간다(건물 윤곽 같은 뚜렷한 경계에서 멈춘다)
    for x in range(2, w - 2, max(6, w // 80)):
        if grad and sky2[1, x + 1] == 0: cv2.floodFill(blur.copy(), sky2, (x, 0), 0, (g,) * 3, (g,) * 3, 4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY)
    sky = (sky[1:-1, 1:-1] > 0) | (sky2[1:-1, 1:-1] > 0)
    fg = (~sky).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))                 # 가는 전선·잔가지 정리
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    if n > 1: fg = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)   # 가장 큰 덩어리만
    if close > 1:                                                        # 윤곽이 하늘색과 비슷해 파먹힌 곳(밝은 간판 등)을 메운다
        pad = close; fgp = cv2.copyMakeBorder(fg, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
        fg = cv2.morphologyEx(fgp, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close, close)))[pad:-pad, pad:-pad]
    inv = cv2.copyMakeBorder(1 - fg, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=1); ff = np.zeros((h + 4, w + 4), np.uint8)
    cv2.floodFill(inv, ff, (0, 0), 0)                                                    # 건물 안쪽에 뚫린 구멍 메우기
    fg = (1 - (inv[1:-1, 1:-1] == 0).astype(np.uint8) * (1 - fg)).clip(0, 1) if False else np.maximum(fg, (inv[1:-1, 1:-1] == 1).astype(np.uint8))
    alpha = cv2.GaussianBlur(fg.astype(np.float32) * 255, (0, 0), 1.0)
    out = np.dstack([rgb, alpha.clip(0, 255).astype(np.uint8)]); ys, xs = np.where(out[..., 3] > 12)
    return out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

def _req(url, key, body=None):
    req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, {'Authorization': 'Key ' + key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r: return json.load(r)

def cut(a, proj, key):
    im = Image.open(os.path.join(proj, 'assets', '_photo', a['id'] + '.jpg')).convert('RGB')
    if a.get('crop'):
        w, h = im.size; c = a['crop']; im = im.crop((int(c[0] * w), int(c[1] * h), int(c[2] * w), int(c[3] * h)))
    if im.width > 1800: im = im.resize((1800, int(im.height * 1800 / im.width)), Image.LANCZOS)
    out = os.path.join(proj, 'assets', a['id'] + '.png')
    if not a.get('cut', True): im.convert('RGBA').save(out); return out
    if a.get('cut') == 'sky': Image.fromarray(sky_cut(np.array(im), a.get('tol', 14), a.get('grad', True), a.get('close', 9))).save(out); return out
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=93)
    sub = _req('https://queue.fal.run/fal-ai/birefnet/v2', key, {'image_url': 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode(), 'model': 'General Use (Heavy)', 'operating_resolution': '2048x2048', 'output_format': 'png', 'refine_foreground': True})
    t_end = time.time() + 600
    while True:
        st = _req(sub['status_url'], key)
        if st.get('status') == 'COMPLETED': break
        if time.time() > t_end: raise RuntimeError('10분 안에 끝나지 않았습니다.')
        time.sleep(2)
    res = _req(sub['response_url'], key)
    data = urllib.request.urlopen(res['image']['url'], timeout=180).read()
    rgba = np.array(Image.open(io.BytesIO(data)).convert('RGBA')); ys, xs = np.where(rgba[..., 3] > 12)
    if len(ys): rgba = rgba[max(ys.min() - 4, 0):ys.max() + 5, max(xs.min() - 4, 0):xs.max() + 5]
    Image.fromarray(rgba).save(out); return out

if __name__ == '__main__':
    proj, cmd = sys.argv[1], sys.argv[2]; only = set(sys.argv[3:])
    spec = [a for a in json.load(open(os.path.join(proj, 'photos.json'), encoding='utf-8')) if not only or a['id'] in only]
    os.makedirs(os.path.join(proj, 'assets', '_photo'), exist_ok=True)
    if cmd == 'fetch':
        cp = os.path.join(proj, 'assets', '_photo', 'credits.json'); cred = {c['id']: c for c in (json.load(open(cp, encoding='utf-8')) if os.path.exists(cp) else [])}
        for a in spec:
            for k in range(4):
                try: cred[a['id']] = fetch(a, proj); print('받음', a['id'], cred[a['id']]['license']); break
                except urllib.error.HTTPError as e:
                    if k == 3: print('실패', a['id'], e.code)
                    time.sleep(6 * (k + 1))
            time.sleep(2)
        json.dump(list(cred.values()), open(cp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    elif cmd == 'cut':
        key = os.environ.get('FAL_KEY') or next((l.split('=', 1)[1].strip().strip('"') for l in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'), encoding='utf-8') if l.startswith('FAL_KEY=')), None)
        for a in spec:
            try: print('누끼', cut(a, proj, key))
            except urllib.error.HTTPError as e: print('실패', a['id'], e.code, e.read().decode('utf-8', 'replace')[:300])
