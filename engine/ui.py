# modern white tutorial UI kit
from common import *
from mg import _REG, _font

BGC = (246, 244, 240)
INK2 = (30, 30, 36)
GRAY = (120, 120, 128)
LGRAY = (225, 223, 219)
CORAL = (240, 88, 74)
CORAL_D = (205, 60, 50)
GREEN = (46, 160, 90)
NAVY = (40, 52, 84)
F_B = os.path.join(FONTS, 'NanumGothic-Bold.ttf')
F_BK = os.path.join(FONTS, 'NanumGothic-ExtraBold.ttf')

_yy, _xx = np.mgrid[0:H, 0:W]
_BG = np.empty((H, W, 3), np.float32); _BG[:] = BGC
_dots = ((_xx % 48 == 24) & (_yy % 48 == 24))
_dots = cv2.dilate(_dots.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
_BG[_dots] = (230, 227, 222)
del _yy, _xx

def bg(C, tint=None):
    C[:] = _BG
    if tint is not None: fill(C, tint[:3], tint[3])

def hfit(name, h=None, w=None):
    return fit(name, h=h, w=w)

def g(C, name, x, y, h=None, w=None, t=None, t0=None, out_t=None, bob=0.0, rot=0.0, d=0.55, alpha=1.0, anchor=(0.5, 0.5), blend='multiply', flip=False):
    """place generated asset (white bg) with pop-in."""
    s, a = (1.0, 1.0) if t0 is None else pop(t, t0, d, out_t)
    if a <= 0: return
    key = name
    if flip:
        key = name + '_flip'
        if key not in _REG: reg(key, img(name)[:, ::-1].copy())
    sc = fit(key, h=h, w=w)
    yy = y + (bob * math.sin((t or 0) * 2.2 + x * 0.01) if bob else 0)
    put(C, key, x, yy, sc * s, a * alpha, rot=rot, anchor=anchor, blend=blend)

def stk(C, name, x, y, h=None, w=None, t=None, t0=None, out_t=None, width=10, rot=0.0, d=0.55, alpha=1.0, anchor=(0.5, 0.5), shadow=True):
    """컷아웃을 흰 테두리 스티커로 배치(등장 애니메이션 포함). h / w 는 테두리를 뺀 그림 자체의 크기 기준."""
    s, a = (1.0, 1.0) if t0 is None else pop(t, t0, d, out_t)
    if a <= 0: return
    key = sticker_spr(name, width, shadow=shadow)
    put(C, key, x, y, fit(name, h=h, w=w) * s, a * alpha, rot=rot, anchor=anchor)

def T(C, s, x, y, t, t0, size=72, color=INK2, font=F_TITLE, out_t=None, anchor=(0.5, 0.5), d=0.55, stroke=0, sfill=WHITE, rot=0):
    sc, a = pop(t, t0, d, out_t)
    if a <= 0: return
    put(C, text_spr(s, size, font, color, stroke, sfill), x, y, sc, a, anchor=anchor, rot=rot)

def pill_spr(text, size=44, fill=CORAL, color=WHITE, font=F_TITLE, padx=None, pady=None, radius=None, border=None):
    key = ('PILL', text, size, fill, color, font, border)
    if key in _REG: return key
    f = _font(font, size)
    d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    bb = d0.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    px = padx or int(size * 0.7); py = pady or int(size * 0.42)
    w, h = tw + px * 2, int(size * 1.0) + py * 2
    S = 2
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    r = radius if radius is not None else h // 2
    d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], r * S, fill=tuple(fill) + (255,), outline=(tuple(border) + (255,)) if border else None, width=3 * S if border else 0)
    fS = _font(font, size * S)
    bbS = d.textbbox((0, 0), text, font=fS)
    d.text(((w * S - (bbS[2] - bbS[0])) / 2 - bbS[0], (h * S - (bbS[3] - bbS[1])) / 2 - bbS[1]), text, font=fS, fill=tuple(color) + (255,))
    im = im.resize((w, h), Image.LANCZOS)
    return reg(key, np.array(im))

def P(C, text, x, y, t, t0, size=44, fill=CORAL, color=WHITE, out_t=None, anchor=(0.5, 0.5), border=None, font=F_TITLE, d=0.55):
    s, a = pop(t, t0, d, out_t)
    if a <= 0: return
    put(C, pill_spr(text, size, fill, color, font, border=border), x, y, s, a, anchor=anchor)

def card_spr(key, w, h, fill=WHITE, radius=28, border=None, shadow=True):
    return panel_spr(key, w, h, fill, border or (0, 0, 0), 3 if border else 0, radius, 255, shadow)

def window_spr(key, w, h, title='', dark=False):
    if key in _REG: return key
    pad = 30; S = 2
    im = Image.new('RGBA', ((w + pad * 2) * S, (h + pad * 2) * S), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    ds.rounded_rectangle([(pad + 4) * S, (pad + 12) * S, (pad + w + 4) * S, (pad + h + 12) * S], 22 * S, fill=(0, 0, 0, 70))
    sh = Image.fromarray(cv2.GaussianBlur(np.array(sh), (0, 0), 14 * S))
    im = Image.alpha_composite(im, sh); d = ImageDraw.Draw(im)
    body = (36, 37, 42) if dark else (255, 255, 255)
    d.rounded_rectangle([pad * S, pad * S, (pad + w) * S, (pad + h) * S], 22 * S, fill=body + (255,))
    bar = (52, 53, 60) if dark else (238, 236, 232)
    d.rounded_rectangle([pad * S, pad * S, (pad + w) * S, (pad + 56) * S], 22 * S, fill=bar + (255,))
    d.rectangle([pad * S, (pad + 30) * S, (pad + w) * S, (pad + 56) * S], fill=bar + (255,))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = (pad + 30 + i * 30) * S; cy = (pad + 28) * S
        d.ellipse([cx - 9 * S, cy - 9 * S, cx + 9 * S, cy + 9 * S], fill=c + (255,))
    if title:
        f = _font(F_B, 26 * S)
        bb = d.textbbox((0, 0), title, font=f)
        d.text(((pad + w / 2) * S - (bb[2] - bb[0]) / 2, (pad + 12) * S), title, font=f, fill=((200, 200, 205) if dark else (90, 90, 96)) + (255,))
    im = im.resize((w + pad * 2, h + pad * 2), Image.LANCZOS)
    return reg(key, np.array(im))

def win(C, key, x, y, w, h, title, t, t0, out_t=None, dark=False, d=0.55):
    """draw window centered; returns (content_x0, content_y0, scale, alpha)"""
    s, a = pop(t, t0, d, out_t)
    if a <= 0: return None
    spr = window_spr(key, w, h, title, dark)
    put(C, spr, x, y, s, a)
    return (x - w * s / 2, y - h * s / 2 + 56 * s, s, a)

def card(C, key, x, y, w, h, t, t0, out_t=None, fill=WHITE, border=None, d=0.55):
    s, a = pop(t, t0, d, out_t)
    if a <= 0: return 0, 0
    put(C, card_spr(key, w, h, fill, 28, border), x, y, s, a)
    return s, a

# ---- chat UI ----
def avatar_spr(size, src=None):
    """AI 답변 말풍선 아바타. src 에셋이 있으면 원형으로 잘라 쓰고, 없으면 직접 그린다."""
    key = ('AVA', size, src)
    if key in _REG: return key
    m = np.zeros((size * 2, size * 2), np.uint8); cv2.circle(m, (size, size), size - 2, 255, -1, cv2.LINE_AA)
    m = cv2.resize(m, (size, size), interpolation=cv2.INTER_AREA)
    if src and has_asset(src):
        a = img(src); h, w = a.shape[:2]
        side = min(h, w); crop = a[(h - side) // 2:(h + side) // 2, (w - side) // 2:(w + side) // 2]
        out = cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA).copy(); out[..., 3] = m
    else:
        im = Image.new('RGBA', (size, size), NAVY + (255,)); d = ImageDraw.Draw(im)
        f = _font(F_BK, int(size * 0.42)); bb = d.textbbox((0, 0), 'AI', font=f)
        d.text(((size - (bb[2] - bb[0])) / 2 - bb[0], (size - (bb[3] - bb[1])) / 2 - bb[1]), 'AI', font=f, fill=(255, 255, 255, 255))
        out = np.array(im); out[..., 3] = m
    return reg(key, out)

def bubble2_spr(text, side='user', size=40, maxw=1100):
    key = ('B2', text, side, size)
    if key in _REG: return key
    f = _font(F_B, size)
    d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    lines = text.split('\n')
    lw = [d0.textbbox((0, 0), l, font=f)[2] for l in lines]
    lh = int(size * 1.45)
    px, py = int(size * 0.75), int(size * 0.55)
    w = max(lw) + px * 2; h = lh * len(lines) + py * 2 - int(size * 0.3)
    S = 2
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fillc = CORAL if side == 'user' else (255, 255, 255)
    tc = WHITE if side == 'user' else INK2
    d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], 26 * S, fill=fillc + (255,), outline=None if side == 'user' else (220, 218, 214, 255), width=0 if side == 'user' else 3 * S)
    fS = _font(F_B, size * S)
    for i, l in enumerate(lines):
        d.text((px * S, (py + i * lh) * S - size * S * 0.12), l, font=fS, fill=tc + (255,))
    im = im.resize((w, h), Image.LANCZOS)
    return reg(key, np.array(im))

def chat_user(C, text, x, y, t, t0, size=40, typing=True, anchor=(1, 0.5), out_t=None):
    """user prompt bubble (right aligned at x). typing effect."""
    if t < t0: return
    shown = typed(text, t, t0 + 0.1, 22) if typing else text
    if not shown: shown = ' '
    s, a = pop(t, t0, 0.3, out_t)
    put(C, bubble2_spr(shown, 'user', size), x, y, s, a, anchor=anchor)

def chat_ai(C, text, x, y, t, t0, size=38, out_t=None, avatar=None):
    s, a = pop(t, t0, 0.3, out_t)
    if a <= 0: return
    put(C, avatar_spr(84, avatar), x, y, s, a, anchor=(0, 0.5))
    put(C, bubble2_spr(text, 'ai', size), x + 104, y, s, a, anchor=(0, 0.5))

# ---- video frames (화면 녹화본·이전 클립을 장면 안에 넣기) ----
# cv2.VideoCapture 는 윈도우에서 한글 경로를 못 열기 때문에 ffmpeg 파이프로 읽는다.
_CAPS = {}
def vframe(path, t, w, h):
    """동영상 path 의 t초 지점 프레임을 (h, w, 3) float32 RGB 로. 앞으로 순서대로 읽을 때 빠르다."""
    fi = max(0, int(t * FPS)); key = (path, w, h)
    st = _CAPS.get(key)
    if st is None or fi < st['fi'] or fi > st['fi'] + FPS * 4:
        if st and st['p']: st['p'].kill()
        if not os.path.exists(path): raise SystemExit(f'동영상이 없습니다: {path}')
        p = subprocess.Popen([ffmpeg_exe(), '-loglevel', 'error', '-ss', f'{fi / FPS:.4f}', '-i', path, '-an',
                              '-vf', f'fps={FPS},scale={w}:{h}:flags=area', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        st = {'p': p, 'fi': fi - 1, 'fr': None}; _CAPS[key] = st
    while st['fi'] < fi and st['p']:
        buf = st['p'].stdout.read(w * h * 3)
        if len(buf) < w * h * 3:      # 끝에 도달: 마지막 프레임 유지
            st['p'].kill(); st['p'] = None; break
        st['fr'] = np.frombuffer(buf, np.uint8).reshape(h, w, 3).astype(np.float32); st['fi'] += 1
    if st['p'] is None: st['fi'] = fi
    return st['fr'] if st['fr'] is not None else np.zeros((h, w, 3), np.float32)

def cap_path(name):
    return cap_file(name)

@functools.lru_cache(None)
def cap_info(name):
    """녹화본의 표시 시각(mgp.py record 가 저장): {'duration': 초, 'marks': {'라벨': 초}}"""
    import json
    p = os.path.splitext(cap_path(name))[0] + '.json'
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {'duration': 0, 'marks': {}}

def cap_mark(name, label):
    m = cap_info(name)['marks']
    if label not in m: raise SystemExit(f"녹화본 {name} 에 '{label}' 표시가 없습니다. 있는 표시: {list(m)}")
    return m[label]

def cap_click(name, i=0):
    """녹화본에서 i 번째 클릭이 일어난 시각(초). 내레이션의 특정 순간에 클릭을 맞출 때 쓴다."""
    c = cap_info(name).get('clicks', [])
    if i >= len(c): raise SystemExit(f'녹화본 {name} 의 클릭은 {len(c)}회뿐입니다.')
    return c[i][0]

def capture(C, name, tv, x, y, w, h, alpha=1.0, radius=0):
    """녹화본 captures/<name>.mp4 의 tv초 지점을 화면 (x, y) 중심, w x h 크기로 그린다."""
    blit(C, vframe(cap_path(name), tv, int(w), int(h)), x - w / 2, y - h / 2, alpha, radius)

@functools.lru_cache(None)
def cap_size(name):
    """녹화본의 (가로, 세로) 픽셀. 직접 찍어 넣은 영상의 비율을 맞출 때 쓴다."""
    r = subprocess.run([ffmpeg_exe(), '-hide_banner', '-i', cap_path(name)], capture_output=True).stderr.decode('utf-8', 'replace')
    m = re.search(r'Video:.*?\b(\d{2,5})x(\d{2,5})\b', r)
    if not m: raise SystemExit(f'동영상 크기를 읽을 수 없습니다: {cap_path(name)}')
    return int(m.group(1)), int(m.group(2))

def cap_fit(name, w=None, h=None):
    """녹화본을 비율 그대로 w 또는 h 에 맞춘 (가로, 세로)."""
    sw, sh = cap_size(name)
    return (int(w), int(round(w * sh / sw))) if w else (int(round(h * sw / sh)), int(h))

# ---- 대본의 [영상: 이름] 구간: 내레이션이 멈추고 captures/<이름> 이 자기 소리로 재생된다 (mgp.py tts 가 input/clips.json 에 시각을 적는다) ----
@functools.lru_cache(None)
def _clips():
    import json
    p = os.path.join(INPUT, 'clips.json')
    return {c['name']: c for c in json.load(open(p, encoding='utf-8'))} if os.path.exists(p) else {}

def _clip(name):
    if name not in _clips(): raise SystemExit(f"대본에 [영상: {name}] 줄이 없습니다 (있는 것: {list(_clips())}). 줄을 넣고 python mgp.py tts 를 다시 실행하세요.")
    return _clips()[name]

def clip_at(name):
    """[영상: 이름] 구간이 시작되는 시각 (영상 전체 기준 초). 장면 기준으로는 clip_at(name) - (ta - t)."""
    return _clip(name)['at']

def clip_len(name): return _clip(name)['dur']

def clip_list():
    """대본의 [영상: 이름] 구간 전부: [{'name', 'at', 'dur'}]"""
    return sorted(_clips().values(), key=lambda c: c['at'])

def clip(C, name, ta, x, y, h=None, w=None, radius=24, alpha=1.0):
    """[영상: 이름] 구간 재생: 영상 전체 시각 ta 에 맞는 프레임을 (x, y) 중심에 비율 그대로 그린다 (h 또는 w 지정).
    구간 전에는 첫 화면, 구간 뒤에는 끝 화면에서 멈춰 있다. 소리는 mgp.py final 이 같은 시각에 섞는다."""
    cw, ch = cap_fit(name, w=w, h=h if not w else None) if (w or h) else cap_fit(name, h=H)
    capture(C, name, clamp(ta - clip_at(name), 0, max(clip_len(name) - 1 / FPS, 0)), x, y, cw, ch, alpha, radius)

@functools.lru_cache(None)
def cap_camera(name, zoom=2.2):
    """녹화본의 자동 카메라: 프레임별 (배율, 중심x, 중심y).
    마우스를 따라다니지 않는다. 보여 줄 대상(focus·click·type)마다 그 대상이 화면에 꽉 차는 구도를 하나 정해
    한 번에 이동한 뒤 멈춰 있고, 대상이 없거나 스크롤 중일 때는 전체 화면이다. zoom = 최대 배율."""
    info = cap_info(name); W0, H0 = info.get('size', [1920, 1080]); n = int(info['duration'] * FPS) + 2
    ts = np.arange(n) / FPS
    shots = []                                                           # [시작, 끝, 배율, 중심x, 중심y]
    for e in sorted(info.get('events', []), key=lambda e: e['t0']):
        x, y, w, h = e['box']
        z = e.get('zoom') or clamp(min(W0 * 0.9 / max(w, 1), H0 * 0.75 / max(h, 1)), 1.25, zoom)   # 대상이 화면 폭의 90%(높이의 75%)까지 차게
        hw, hh = W0 / (2 * z), H0 / (2 * z)
        cx, cy = clamp(x + w / 2, hw, W0 - hw), clamp(y + h / 2, hh, H0 - hh)
        t0, t1 = e['t0'], max(e['t1'], e['t0'] + 1.2)
        if shots and t0 - shots[-1][1] < 1.5:                            # 바로 앞 구도 안에 이 대상이 이미 들어 있으면 카메라를 다시 움직이지 않는다
            _, _, pz, px, py = shots[-1]; phw, phh = W0 / (2 * pz) * 0.88, H0 / (2 * pz) * 0.88
            if x > px - phw and x + w < px + phw and y > py - phh and y + h < py + phh:
                shots[-1][1] = t1; continue
        shots.append([t0, t1, z, cx, cy])
    z = np.ones(n, np.float32); cx = np.full(n, W0 / 2, np.float32); cy = np.full(n, H0 / 2, np.float32)
    for i, (a, b, zz, x, y) in enumerate(shots):
        if i + 1 < len(shots) and shots[i + 1][0] - b < 1.5: b = shots[i + 1][0]      # 곧 다음 대상이 오면 넓게 빠졌다 오지 않고 바로 넘어간다
        m = (ts >= a) & (ts < b); z[m] = zz; cx[m] = x; cy[m] = y
    for a, b in info.get('scrolls', []):
        m = (ts >= a - 0.3) & (ts <= b + 0.3); z[m] = 1.0; cx[m] = W0 / 2; cy[m] = H0 / 2
    g = lambda v: ndimage.gaussian_filter1d(v, 0.28 * FPS, mode='nearest')          # 구도 사이 이동은 약 1.1초, 그 외에는 정지
    z, cx, cy = g(z), g(cx), g(cy)
    hw, hh = W0 / (2 * z), H0 / (2 * z)
    return z, np.clip(cx, hw, W0 - hw), np.clip(cy, hh, H0 - hh)

def _spot(name, tv):
    """tv 시점에 강조할 대상: (box, 세기 0~1) 또는 None"""
    best = None
    for e in cap_info(name).get('events', []):
        a, b = e['hl']
        out = 0.1 if e['kind'] == 'click' else 0.3            # 클릭하면 화면이 바뀌므로 강조를 바로 거둔다
        k = min(clamp((tv - a) / 0.3), clamp((b + out - tv) / out))
        if k > 0 and (best is None or k > best[1]): best = (e['box'], k)
    return best

def screen(C, name, tv, x, y, w, h, zoom=2.2, radius=22, shadow=True, alpha=1.0, spot=True, spot_color=CORAL, dim=0.35):
    """웹 녹화본을 강의 영상처럼 그린다: (x, y) 중심의 둥근 화면 + 그림자.
    보여 줄 대상(h.focus / h.click / h.type)으로 한 번에 줌인해 멈추고, 그 대상에 테두리를 치고 나머지를 살짝 어둡게 한다.
    tv = 녹화본 시각(초). zoom = 최대 줌 배율(1 이면 줌 없음). spot=False 면 강조 표시 없음."""
    info = cap_info(name); W0, H0 = info.get('size', [1920, 1080]); w, h = int(w), int(h)
    z, tx, ty = cap_camera(name, zoom); i = int(clamp(tv * FPS, 0, len(z) - 1))
    full = vframe(cap_path(name), tv, W0, H0)
    cw, ch = W0 / z[i], H0 / z[i]; sx, sy = w / cw, h / ch
    if sx < 0.8: full = cv2.GaussianBlur(full, (0, 0), 0.5 / sx - 0.3)       # 많이 줄일 때 계단 현상 방지
    M = np.array([[sx, 0, -(tx[i] - cw / 2) * sx], [0, sy, -(ty[i] - ch / 2) * sy]], np.float32)
    view = cv2.warpAffine(full, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    sp = _spot(name, tv) if spot else None
    if sp:
        (bx, by, bw, bh), k = sp; pad = 10 * sx
        x0, y0 = bx * sx + M[0, 2] - pad, by * sy + M[1, 2] - pad; x1, y1 = (bx + bw) * sx + M[0, 2] + pad, (by + bh) * sy + M[1, 2] + pad
        p0, p1 = (int(round(x0 * 16)), int(round(y0 * 16))), (int(round(x1 * 16)), int(round(y1 * 16)))
        m = np.zeros((h, w), np.uint8); cv2.rectangle(m, p0, p1, 255, -1, cv2.LINE_AA, shift=4)
        m = cv2.GaussianBlur(m, (0, 0), 5).astype(np.float32)[..., None] / 255
        view = view * (1 - dim * k * (1 - m))                                 # 대상 밖을 살짝 어둡게
        o = np.zeros((h, w), np.uint8); cv2.rectangle(o, p0, p1, 255, max(3, int(round(4 * sx))), cv2.LINE_AA, shift=4)
        o = cv2.GaussianBlur(o, (0, 0), 0.8).astype(np.float32)[..., None] / 255 * k
        view = view * (1 - o) + np.array(spot_color, np.float32) * o          # 대상 테두리
    if shadow: put(C, panel_spr(('SCR', w, h, radius), w, h, fill=(255, 255, 255), bw=0, radius=radius, shadow=True), x, y, 1.0, alpha)
    blit(C, view, x - w / 2, y - h / 2, alpha, radius)

@functools.lru_cache(8)
def _grad(c1, c2):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); k = np.clip((xx / W * 0.6 + yy / H * 0.4), 0, 1)[..., None]
    return np.array(c1, np.float32) * (1 - k) + np.array(c2, np.float32) * k

def wall(C, c1=(54, 62, 92), c2=(138, 92, 120)):
    """화면 녹화 뒤에 까는 대각선 그라데이션 배경."""
    C[:] = _grad(tuple(c1), tuple(c2))

def blit(C, arr, x0, y0, alpha=1.0, radius=0):
    h, w = arr.shape[:2]
    fx, fy = x0 - math.floor(x0), y0 - math.floor(y0)
    if fx > 0.01 or fy > 0.01:                                 # 소수점 위치: 배열을 그만큼 밀어서 그린다
        arr = cv2.warpAffine(arr, np.array([[1, 0, fx], [0, 1, fy]], np.float32), (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    x0, y0 = int(math.floor(x0)), int(math.floor(y0))
    xa, ya = max(x0, 0), max(y0, 0); xb, yb = min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb: return
    sub = arr[ya - y0:yb - y0, xa - x0:xb - x0]
    if radius:
        key = ('RMASK', w, h, radius)
        if key not in _REG:
            m = np.zeros((h * 2, w * 2), np.uint8)
            cv2.rectangle(m, (radius * 2, 0), (w * 2 - radius * 2, h * 2), 255, -1)
            cv2.rectangle(m, (0, radius * 2), (w * 2, h * 2 - radius * 2), 255, -1)
            for cx, cy in [(radius, radius), (w - radius, radius), (radius, h - radius), (w - radius, h - radius)]:
                cv2.circle(m, (cx * 2, cy * 2), radius * 2, 255, -1, cv2.LINE_AA)
            _REG[key] = cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255
        m = _REG[key][ya - y0:yb - y0, xa - x0:xb - x0] * alpha
        C[ya:yb, xa:xb] = C[ya:yb, xa:xb] * (1 - m) + sub * m
    else:
        C[ya:yb, xa:xb] = C[ya:yb, xa:xb] * (1 - alpha) + sub * alpha

MGDIR = os.environ.get('MG_PREV_CLIPS') or OUTDIR  # 이전에 만든 모션그래픽 클립 폴더(튜토리얼 '증거 화면'용)
def mgpath(prefix):
    hits = glob.glob(os.path.join(MGDIR, prefix + ' *.mp4'))
    if not hits: raise SystemExit(f'{MGDIR} 에 {prefix} 클립이 없습니다.')
    return hits[0]

# ---- 채널 마스코트 (brand/<이름>_<포즈>.png, 이름은 채널 프로필 brand/channel.json 의 mascot) ----
HOST_POSES = ('idle', 'point', 'shrug', 'shock', 'think', 'peek', 'facepalm', 'ew')      # 상반신 표정
# 입·부리 끝 위치(그림 안 가로·세로 비율, 원본 = 왼쪽을 볼 때). 말풍선 꼬리가 여기서 나온다.
HOST_BEAK = {}        # 포즈별 입·부리 위치. 채널 프로필(channel.json)의 mascot_beak 에서 읽는다. 없는 포즈는 (0.25, 0.22)

MASCOT = os.environ.get('MG_MASCOT', '')                   # 채널 프로필의 mascot. 비어 있으면 마스코트 없음(mascot/host 호출은 아무것도 그리지 않는다)
def _load_beak():
    """마스코트의 입·부리 위치: brand/<마스코트>_beak.json 이 있으면 그것, 없으면 channel.json 의 mascot_beak. {"포즈": [가로, 세로]}"""
    js = __import__('json')
    for p, key in ((os.path.join(BRAND, MASCOT + '_beak.json'), None), (os.path.join(BRAND, 'channel.json'), 'mascot_beak')):
        try:
            d = js.load(open(p, encoding='utf-8')); d = d if key is None else d.get(key, {})
            if d: HOST_BEAK.update({k: tuple(v) for k, v in d.items() if not k.startswith('_')}); return
        except Exception: pass
_load_beak()

def has_mascot(pose='idle'):
    return bool(MASCOT) and has_asset(MASCOT + '_' + pose)

def _mascot_spr(pose, face):
    name = MASCOT + '_' + pose
    if face == 'right':                                         # 원본은 왼쪽을 본다
        key = name + '_flip'
        if key not in _REG: reg(key, img(name)[:, ::-1].copy())
        return name, key
    return name, name

def _mascot_say(C, pose, face, x_left, y_top, ww, h, say, t, t0, out_t, size):
    bx, by = HOST_BEAK.get(pose, (0.25, 0.22))
    tx = x_left + ((1 - bx) if face == 'right' else bx) * ww
    ty = max(y_top + by * h - 0.07 * h, 190)                    # 화면 위로 잘리지 않게
    bubble(C, say, tx + (0.05 * ww if face == 'right' else -0.05 * ww), ty, t, t0, size, tail='left' if face == 'right' else 'right', out_t=out_t, font=F_BRUSH)

def mascot(C, pose, x, y, h, t, t0=None, out_t=None, face='left', say=None, say_t=None, say_out=None, size=80, soft=False, bob=5.0):
    """채널 마스코트를 장면 안 원하는 자리에 세운다 — 가운데에 크게 세워 장면의 주인공·진행자로 쓰는 것이 기본.
    (x, y) = 그림 중심, h = 높이(크게: 650~800). face = 바라보는 쪽. pose 는 brand/<마스코트>_<pose>.png (복장 버전 포함).
    채널에 마스코트가 없거나 그 포즈 그림이 없으면 아무것도 그리지 않는다.
    say = 말풍선 대사(부리에서 나온다). 무거운 구간에서는 쓰지 않는다."""
    if not has_mascot(pose) or (t0 is not None and t < t0): return
    if t0 is None: s, a = 1.0, 1.0
    elif soft: s, a = 1.0, fade(t, t0, 0.6, out_t, 0.4)
    else: s, a = pop(t, t0, 0.55, out_t)
    if a <= 0: return
    name, key = _mascot_spr(pose, face)
    w0, h0 = sprite_size(name); ww = h * w0 / h0
    yy = y + bob * math.sin(t * 1.5)
    put(C, sticker_spr(key, 10), x, yy, h / h0 * s, a)
    if say and a > 0.9:
        _mascot_say(C, pose, face, x - ww / 2, yy - h / 2, ww, h, say, t, say_t if say_t is not None else (t0 or 0) + 0.5 * PACE,
                  say_out if say_out is not None else (out_t - 0.15 if out_t is not None else None), size)

def host(C, pose, t, t0, out_t=None, side='left', h=440, say=None, say_t=None, say_out=None, size=72):
    """마스코트가 화면 아래에서 올라와 반응한다(상반신만). side: 'left' | 'right' | 'center'.
    구석 반응은 가끔만 쓰고, 기본은 mascot() 으로 가운데에 크게 세운다."""
    if not has_mascot(pose) or t < t0: return
    k = ease_out(lin(t, t0, t0 + 0.6 * PACE)) * (1 - (ease_in(lin(t, out_t, out_t + 0.45 * PACE)) if out_t is not None else 0))
    if k <= 0: return
    face = 'right' if side == 'left' else 'left'
    name, key = _mascot_spr(pose, face)
    w0, h0 = sprite_size(name); ww = h * w0 / h0
    x = {'left': 30 + ww / 2, 'right': W - 30 - ww / 2}.get(side, W / 2)
    yb = H + 26 + (1 - k) * (h + 40) + 4 * math.sin(t * 1.6)
    put(C, sticker_spr(key, 8), x, yb, h / h0, 1.0, anchor=(0.5, 1))
    if say and k > 0.9:
        _mascot_say(C, pose, face, x - ww / 2, yb - h, ww, h, say, t, say_t if say_t is not None else t0 + 0.6 * PACE,
                  say_out if say_out is not None else (out_t - 0.2 if out_t is not None else None), size)

# ---- 구독 유도 ----
YT_RED = (214, 28, 28)

def _cursor_spr():
    key = 'CURSOR_ARROW'
    if key in _REG: return key
    S = 4; im = Image.new('RGBA', (30 * S, 40 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(3, 2), (3, 30), (10, 23), (15, 36), (20, 34), (15, 21), (25, 21)]
    d.polygon([(x * S, y * S) for x, y in pts], fill=(20, 20, 20, 255), outline=(255, 255, 255, 255), width=2 * S)
    return reg(key, np.array(im.resize((60, 80), Image.LANCZOS)))

def subscribe_button(C, x, y, t, t0, press_t=None, out_t=None, scale=1.0):
    """빨간 '구독' 버튼. press_t 에 커서가 와서 누르면 회색 '구독중' 으로 바뀐다. (x, y) = 버튼 중심."""
    s, a = pop(t, t0, 0.5, out_t)
    if a <= 0: return
    done = press_t is not None and t >= press_t
    squash = 1 - 0.12 * math.sin(clamp((t - press_t) / 0.28) * math.pi) if done else 1.0
    spr = pill_spr('구독중', 96, (236, 233, 228), (40, 40, 44), F_BK, border=(40, 40, 44)) if done else pill_spr('구독', 96, YT_RED, WHITE, F_BK)
    put(C, panel_spr(('SUBSH', done), *sprite_size(spr), fill=(0, 0, 0), bw=0, radius=sprite_size(spr)[1] // 2, alpha=0, shadow=True), x, y, s * scale * squash, a)
    put(C, spr, x, y, s * scale * squash, a)
    if press_t is not None:
        k = ease_io(lin(t, press_t - 1.0, press_t))                       # 커서가 다가와 누른다
        if t > press_t - 1.0:
            ca = a * (1 - clamp((t - press_t - 0.9) / 0.4))
            put(C, _cursor_spr(), lerp(x + 330, x + 60, k) * 1.0, lerp(y + 260, y + 34, k), scale, ca, anchor=(0.1, 0.05))
        if done and t < press_t + 0.6:
            p = (t - press_t) / 0.6; circle(C, x + 60 * scale, y + 34 * scale, (20 + 90 * p) * scale, YT_RED, 6, alpha=(1 - p) * a)

def subscribe_nudge(C, x, y, t, t0, dur=5.5, say='구독은 누르고 봐', say2=None, pose='point', h=560, scale=1.0):
    """영상 중간의 구독 유도: (x, y) 에 구독 버튼, 그 오른쪽에서 마스코트가 버튼을 가리키며 한마디. dur 초 뒤 사라진다.
    내레이션은 그대로 흐르므로, 화면 한쪽이 2~3초 이상 비는 구간에 넣는다. 무거운 구간에는 넣지 않는다."""
    if t < t0 or t > t0 + dur + 1.0: return
    if not has_mascot(pose): subscribe_button(C, x, y, t, t0 + 0.25, press_t=t0 + 2.4 * PACE, out_t=t0 + dur, scale=scale); return
    out = t0 + dur; press = t0 + 2.4 * PACE
    subscribe_button(C, x, y, t, t0 + 0.25, press_t=press, out_t=out, scale=scale)
    w0, h0 = sprite_size(MASCOT + '_' + pose); ww = h * w0 / h0
    mx = x + sprite_size(pill_spr('구독', 96, YT_RED, WHITE, F_BK))[0] * scale / 2 + ww / 2 + 70
    mascot(C, pose, mx, y + h * 0.16, h, t, t0, out_t=out, say=say if (say2 is None or t < press + 0.5) else say2,
           say_t=t0 + 0.6 * PACE if (say2 is None or t < press + 0.5) else press + 0.5, say_out=(press + 0.3 if say2 else out - 0.15) if t < press + 0.5 else out - 0.15)

# ---- subtitles ----
SUBS = [(a, b, re.sub(r'\*\*', '', txt).strip()) for _, (a, b, txt) in sorted(CUES.items())]
if os.environ.get('MG_SUB_MERGE', '0') == '1':
    # 문장 중간에서 끊긴 자막을 화면에서는 한 줄로 이어 보여 준다 (자막 번호·시각은 그대로, 표시만 합침)
    _END = re.compile(r'(다|요|죠|까|네|군|지|나)[.!?…"\']*$')
    _m = []
    for a, b, s in SUBS:
        if _m and not _END.search(_m[-1][2]) and a - _m[-1][1] < 0.2 and len(_m[-1][2]) + len(s) <= 44: _m[-1] = (_m[-1][0], b, _m[-1][2] + ' ' + s)
        else: _m.append((a, b, s))
    SUBS = _m
def sub_at(t):
    cur = None
    for i, (a, b, s) in enumerate(SUBS):
        if a <= t < b: return s
        if b <= t and (i + 1 >= len(SUBS) or t < SUBS[i + 1][0]) and t - b < 0.45: return s
    return None

SUB_STYLE = os.environ.get('MG_SUB_STYLE', 'dark')     # project.json 의 style.subtitle: "dark"(어두운 둥근 박스) | "paper"(흰 박스 + 검은 테두리 + 그림자)

def sub_spr(text, style=None):
    """자막 한 줄. 글자는 박스의 가로·세로 정중앙에 놓는다.
    세로는 한글 몸통('한') 기준으로 맞춘다 → 쉼표·영문 꼬리가 있어도 자막마다 글자 높이가 달라지지 않는다."""
    style = style or SUB_STYLE
    key = ('SUB', text, style)
    if key in _REG: return key
    S = 2; fS = _font(F_B, 46 * S)
    d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    bb = d0.textbbox((0, 0), text, font=fS); rb = d0.textbbox((0, 0), '한', font=fS)
    if style == 'paper':
        px, py, sh = 22, 13, 6
        w, h = int(math.ceil((bb[2] - bb[0]) / S)) + px * 2, int(math.ceil((rb[3] - rb[1]) / S)) + py * 2
        im = Image.new('RGBA', ((w + sh) * S, (h + sh) * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rectangle([sh * S, sh * S, (w + sh) * S - 1, (h + sh) * S - 1], fill=(20, 18, 16, 255))                     # 딱 떨어지는 그림자
        d.rectangle([0, 0, w * S - 1, h * S - 1], fill=(255, 255, 255, 255), outline=(20, 18, 16, 255), width=3 * S)
        d.text(((w * S - (bb[2] - bb[0])) / 2 - bb[0], (h * S - (rb[3] - rb[1])) / 2 - rb[1]), text, font=fS, fill=(20, 18, 16, 255))
        im = im.resize((w + sh, h + sh), Image.LANCZOS)
        return reg(key, np.array(im))
    px, py = 34, 20
    w, h = int(math.ceil((bb[2] - bb[0]) / S)) + px * 2, int(math.ceil((rb[3] - rb[1]) / S)) + py * 2
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], 16 * S, fill=(24, 24, 28, 232))   # 거의 불투명: 움직이는 배경이 비쳐 자막이 어른거리지 않게
    d.text(((w * S - (bb[2] - bb[0])) / 2 - bb[0], (h * S - (rb[3] - rb[1])) / 2 - rb[1]), text, font=fS, fill=(255, 255, 255, 255))
    im = im.resize((w, h), Image.LANCZOS)
    return reg(key, np.array(im))

def subtitle(C, t_abs):
    s = sub_at(t_abs)
    if not s: return
    spr = sub_spr(s)
    put(C, spr, W / 2, 1000, min(1.0, (W - 120) / sprite_size(spr)[0]), 1.0)   # 너무 길면 화면 폭에 맞춰 축소

# ---- step indicator ----
STEPS = ['1단계', '2단계', '3단계']   # 장면 파일에서 stepbar(..., steps=[...]) 로 바꿔 쓴다
def stepbar(C, step, t, t0, steps=None):
    a = fade(t, t0, 0.3)
    if a <= 0: return
    x = 60
    for i, nm in enumerate(steps or STEPS):
        on = (i + 1 == step)
        done = (i + 1 < step)
        fillc = CORAL if on else ((255, 255, 255) if not done else (250, 220, 214))
        col = WHITE if on else (INK2 if done else GRAY)
        spr = pill_spr(f'{i + 1} {nm}', 30, fillc, col, F_TITLE, border=None if on else (220, 218, 214))
        sw, sh = sprite_size(spr)
        put(C, spr, x, 62, 1.0, a, anchor=(0, 0.5))
        x += sw + 12

def num(C, value_text, x, y, size, color, t, t0, anchor=(0.5, 0.5)):
    put(C, text_spr(value_text, size, F_TITLE, color, 0), x, y, 1.0, fade(t, t0, 0.2), anchor=anchor)

def bar(C, x0, y0, w, h, frac, color, t, t0, d=0.8, bgc=(232, 229, 224), radius=True):
    if t < t0: return
    k = ease_out(lin(t, t0, t0 + d)) * frac
    rect(C, x0, y0, x0 + w, y0 + h, bgc, fade(t, t0, 0.2))
    rect(C, x0, y0, x0 + w * k, y0 + h, color, 1.0)
