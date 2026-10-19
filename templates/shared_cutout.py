"""컷아웃 화면 키트 — 배경 위에 캐릭터 컷아웃을 크게 세우고 이름표·말풍선·지도 표시를 붙이는 방식의 공용 화면 요소.

쓰는 법: 이 파일을 projects/<이름>/scenes/_shared.py 로 복사하고, 장면 파일에서 `from _shared import *` 로 불러 쓴다.
         색·글꼴·크기·자막 모양은 그 영상에 맞게 이 파일(복사본)에서 고친다. 쓰는 문법: templates/scene_cuts_template.py

화면 규칙
- 자막: 흰 직사각형 + 가는 검은 테두리, 중간 굵기 고딕.
- 이름·라벨: 아주 굵은 고딕 + 두꺼운 흰 테두리 + 바깥으로 번지는 어두운 그림자. 어두운 바탕에서는 흰 글씨 + 어두운 테두리.
- 말풍선: 흰 풍선 + 검은 테두리. 낱말이 말하는 순서대로 회색 → 검정.
- 캐릭터·소품: 컷아웃에 흰 테두리 + 그림자. 배경(지도·실내·풍경) 위에 크게 세운다.
- 한 번에 하나만 크게. 자막 한두 개마다 컷을 바꾼다(seq). 한 컷에서 2초 넘게 배경만 보이지 않게, 컷이 시작될 때 캐릭터나 소품을 먼저 세운다.
- 글자를 두 줄 이상 쌓을 때는 T / plate / place / tag / W1 을 쓴다(글자가 실제로 보이는 칸을 재서 놓아 겹치지 않는다).
- 무거운 구간(죽음·범죄)에서는 튕기는 등장을 쓰지 않는다: 이 키트의 등장은 전부 밀려 들어오거나 서서히 나타난다.

배경 이름: paper() 는 'bg_parch'(종이), dark() 는 'bg_dark'(어두운 벽), 지도 함수는 MAP('bg_map') 를 쓴다. assets.json 에 같은 id 로 만들어 두거나 이름을 바꿔 쓴다.
"""
from kit import *
from PIL import ImageFont
import mg, ui
from mg import _REG, FONTS, bgimg

# ---------------- 글꼴 (키트의 fonts/ 폴더) ----------------
def _pick(fn, fallback):
    f = os.path.join(FONTS, fn); return f if os.path.exists(f) else fallback
F_SUB = _pick('GmarketSansTTFMedium.ttf', F_SANS)                   # 자막
F_HEAVY = _pick('GmarketSansTTFBold.ttf', F_TITLE)                  # 이름·라벨
F_SAY = _pick('NanumSquareRoundEB.ttf', F_SANS)                     # 말풍선
F_MID = _pick('NanumSquareRoundB.ttf', F_SANS)                      # 작은 설명
MAP = 'bg_map'                                                      # 지도 배경의 에셋 id

def _font(path, size):
    """(파일, 번호) 로 글꼴 묶음(.ttc) 안의 굵기를 고른다"""
    if isinstance(path, tuple): return ImageFont.truetype(path[0], int(size), index=path[1])
    return ImageFont.truetype(path, int(size))
mg._font = _font                                                    # text_spr 도 같은 방식으로 글꼴을 연다 (이 프로젝트 안에서만)

INK1 = (22, 20, 20); RED = (196, 38, 34); PARCH = (233, 214, 170); NIGHT = (16, 22, 44); NOTE = (96, 86, 72); YEL = (244, 196, 70); DARK = (18, 16, 16)
SL = mg.PACE if hasattr(mg, 'PACE') else 1.3                           # project.json 의 style.pace

def E(t, t0, d=1.0): return ease_io(lin(t, t0, t0 + d * SL))
def EO(t, t0, d=1.0): return ease_out(lin(t, t0, t0 + d * SL))

# ---------------- 자막: 흰 직사각형 + 가는 검은 테두리 ----------------
def _sub_spr(text, style=None):
    key = ('SUB_K', text)
    if key in _REG: return key
    S = 2; f = _font(F_SUB, 46 * S); d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    bb = d0.textbbox((0, 0), text, font=f); rb = d0.textbbox((0, 0), '한', font=f)
    px, py = 20, 11
    w, h = int(math.ceil((bb[2] - bb[0]) / S)) + px * 2, int(math.ceil((rb[3] - rb[1]) / S)) + py * 2
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w * S - 1, h * S - 1], fill=(255, 255, 255, 255), outline=(12, 12, 12, 255), width=3 * S)
    d.text(((w * S - (bb[2] - bb[0])) / 2 - bb[0], (h * S - (rb[3] - rb[1])) / 2 - rb[1]), text, font=f, fill=(12, 12, 12, 255))
    return reg(key, np.array(im.resize((w, h), Image.LANCZOS)))
ui.sub_spr = _sub_spr

# ---------------- 배경 ----------------
def kb(C, name, t, dur=8.0, a=(0.5, 0.5, 1.0), b=(0.5, 0.5, 1.07)):
    """화면을 가득 채운 그림 + 느린 카메라. a, b = (가로 위치 0~1, 세로 위치 0~1, 배율). 그림 밖이 보이지 않게 가장자리에서 멈춘다."""
    im = bgimg(name); h, w = im.shape[:2]; base = max(W / w, H / h)
    k = lin(t, 0, dur); z = base * lerp(a[2], b[2], k)
    hw, hh = W / 2 / z, H / 2 / z
    cx = min(max(lerp(a[0], b[0], k) * w, hw), w - hw); cy = min(max(lerp(a[1], b[1], k) * h, hh), h - hh)
    cam = Cam(cx, cy, z); draw_bg(C, name, cam); return cam

def dim(C, amt=0.5, color=(14, 12, 12)): fill(C, color, amt)

def vignette(C, amt=0.35):
    key = ('VIG',)
    if key not in _REG:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
        a = np.clip((r - 0.55) / 0.75, 0, 1) ** 1.6; im = np.zeros((H, W, 4), np.uint8); im[..., 3] = (a * 255).astype(np.uint8); reg(key, im)
    put(C, key, W / 2, H / 2, 1.0, amt)

# ---------------- 그림자·번짐 ----------------
def _shadowed(arr, off=8, blur=14, strength=0.30):
    arr = np.asarray(arr).astype(np.float32)
    pad = blur * 2 + off
    h, w = arr.shape[:2]; out = np.zeros((h + pad * 2, w + pad * 2, 4), np.float32)
    sh = np.zeros((h + pad * 2, w + pad * 2), np.float32); sh[pad + off:pad + off + h, pad + off // 2:pad + off // 2 + w] = arr[..., 3] / 255.0
    sh = np.clip(cv2.GaussianBlur(sh, (0, 0), blur * 0.6) * strength, 0, 1)
    out[..., 3] = sh * 255
    a = arr[..., 3:4] / 255.0; r_ = out[pad:pad + h, pad:pad + w]
    r_[..., :3] = arr[..., :3] * a + r_[..., :3] * (1 - a)
    r_[..., 3:4] = (a + r_[..., 3:4] / 255.0 * (1 - a)) * 255
    return out.clip(0, 255).astype(np.uint8)

# ---------------- 글자 ----------------
def lab_spr(txt, size, color=INK1, edge=WHITE, stroke=None, glow=0.55, font=None):
    """굵은 글씨 + 두꺼운 테두리 + 바깥으로 번지는 어두운 그림자"""
    stroke = max(4, int(size * 0.10)) if stroke is None else stroke
    base = text_spr(txt, size, font or F_HEAVY, color, stroke, edge)
    if not glow or not stroke: return base
    key = ('LAB', base, glow)
    if key not in _REG: reg(key, _shadowed(_REG[base], 4, max(6, int(size * 0.14)), glow * 1.8))
    return key

_INK = {}
def ink(spr):
    """글자 스프라이트에서 실제 글자(테두리 포함)가 차지하는 칸: (왼, 위, 오른, 아래, 전체 너비, 전체 높이). 번지는 그림자는 빼고 잰다"""
    if spr not in _INK:
        a = np.asarray(_REG[spr])[..., 3]; rows = np.where(a.max(1) > 250)[0]; cols = np.where(a.max(0) > 250)[0]
        _INK[spr] = (int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1, a.shape[1], a.shape[0])
    return _INK[spr]

def put_ink(C, spr, x, y, a=1.0, ax=0.5, ay=0.5):
    """글자가 실제로 보이는 칸을 기준으로 놓는다 (글꼴마다 위아래 여백이 달라 겹치는 것을 막는다). 반환: 글자 칸의 (너비, 높이)"""
    x0, y0, x1, y1, w, h = ink(spr)
    put(C, spr, x, y, 1.0, a, anchor=((x0 + (x1 - x0) * ax) / w, (y0 + (y1 - y0) * ay) / h))
    return x1 - x0, y1 - y0

def T(C, txt, x, y, t, t0, size=72, color=INK1, out_t=None, anchor=(0.5, 0.5), edge=WHITE, stroke=None, font=None, glow=0.55):
    """짧은 라벨 (서서히 나타난다). 어두운 바탕에서는 color=WHITE, edge=DARK"""
    a = fade(t, t0, 0.25, out_t, 0.25)
    if a > 0: put_ink(C, lab_spr(txt, size, color, edge, stroke, glow, font), x, y, a, anchor[0], anchor[1])

def plate(C, name, x, y, t, t0, sub=None, out_t=None, size=84):
    """이름표: 굵은 검은 글씨 + 흰 테두리. 위에 작은 빨간 설명"""
    a = fade(t, t0, 0.25, out_t, 0.25)
    if a <= 0: return
    nw, nh = put_ink(C, lab_spr(name, size), x, y, a, 0, 0.5)
    if sub: put_ink(C, lab_spr(sub, int(size * 0.44), RED, WHITE, None, 0.4, F_SAY), x + 4, y - nh / 2 - size * 0.10, a, 0, 1)          # 설명은 이름 윗선에서 한 칸 띄워서

def place(C, x, y, name, t, t0, sub=None, size=64, out_t=None, side='right', r=20):
    """지도 지명: 겹동그라미 표시 + 빨간 글씨(흰 테두리). (x, y) = 화면 좌표"""
    a = fade(t, t0, 0.12, out_t, 0.25)
    if a <= 0: return
    u = t - t0
    if u < 0.8: circle(C, x, y, r + 90 * u, RED, 6, (1 - u / 0.8) * a)                     # 찍히는 순간 퍼지는 고리
    circle(C, x, y, r + 5, WHITE, 6, a, filled=True); circle(C, x, y, r, RED, 7, a); circle(C, x, y, r * 0.42, RED, 4, a, filled=True)
    if not name: return
    ax = 0 if side == 'right' else 1; tx = x + (r + 20) * (1 if side == 'right' else -1)
    yy = y - (size * 0.30 if sub else 0); nw, nh = put_ink(C, lab_spr(name, size, RED, WHITE), tx, yy, fade(t, t0 + 0.12, 0.2, out_t, 0.25), ax, 0.5)
    if sub: put_ink(C, lab_spr(sub, int(size * 0.52), INK1, WHITE, None, 0.4, F_SAY), tx + 3 * (1 if side == 'right' else -1), yy + nh / 2 + size * 0.10, fade(t, t0 + 0.25, 0.2, out_t, 0.25), ax, 0)

def count(v0, v1, t, t0, d=1.4):
    return v0 + (v1 - v0) * ease_out(lin(t, t0, t0 + d * SL))

# ---------------- 말풍선 ----------------
_BUB = {}
def bub_spr(txt, n, size=58, tail='left'):
    """흰 말풍선. 앞에서 n 낱말까지는 검정, 나머지는 회색(아직 말하지 않은 부분)"""
    key = ('BUB_K', txt, n, size, tail)
    if key in _REG: return key
    S = 2; f = _font(F_SAY, size * S); d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    words = txt.split(' '); sp = d0.textlength(' ', font=f); ws = [d0.textlength(w, font=f) for w in words]
    tw = sum(ws) + sp * (len(words) - 1); rb = d0.textbbox((0, 0), '한', font=f); th = rb[3] - rb[1]
    px, py, bw, tl = int(size * 0.52) * S, int(size * 0.36) * S, 5 * S, int(size * 0.62) * S
    w, h = int(tw + px * 2), int(th + py * 2)
    im = Image.new('RGBA', (w, h + tl), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    tx = int(w * (0.22 if tail == 'left' else 0.78)); dr = -1 if tail == 'left' else 1; tip = (tx + dr * int(size * 0.34) * S, h + tl - 2)
    d.polygon([(tx - 20 * S, h - bw * 2), (tx + 20 * S, h - bw * 2), tip], fill=(12, 12, 12, 255))                         # 꼬리 (테두리)
    d.rounded_rectangle([0, 0, w - 1, h - 1], int(h * 0.44), fill=(255, 255, 255, 255), outline=(12, 12, 12, 255), width=bw)
    d.polygon([(tx - 20 * S + bw * 1.6, h - bw * 2.2), (tx + 20 * S - bw * 1.6, h - bw * 2.2), (tip[0] - dr * bw * 0.4, tip[1] - bw * 2.4)], fill=(255, 255, 255, 255))   # 꼬리 (안쪽)
    x = px
    for i, wd in enumerate(words):
        d.text((x, py - rb[1]), wd, font=f, fill=(12, 12, 12, 255) if i < n else (168, 168, 168, 255)); x += ws[i] + sp
    arr = np.array(im.resize((w // S, (h + tl) // S), Image.LANCZOS)); blur = 12; off = 4; pad = blur * 2 + off
    out = _shadowed(arr, off, blur, 0.75)
    _BUB[key] = ((pad + tip[0] / S) / out.shape[1], (pad + tip[1] / S) / out.shape[0])
    return reg(key, out)

def say(C, txt, x, y, t, t0, out_t=None, tail='left', size=58, wps=5.0):
    """말풍선. (x, y) = 꼬리 끝(말하는 사람의 머리 옆). 낱말이 차례로 검어진다"""
    a = fade(t, t0, 0.14, out_t, 0.2)
    if a <= 0: return
    n = min(len(txt.split(' ')), 1 + int((t - t0) * wps))
    spr = bub_spr(txt, n, size, tail)
    put(C, spr, x, y, lerp(0.86, 1.0, ease_out(lin(t, t0, t0 + 0.18))), a, anchor=_BUB[spr])

# ---------------- 캐릭터·소품 ----------------
def flipped(name):
    key = name + '_flip'
    if key not in _REG: reg(key, img(name)[:, ::-1].copy())
    return key

def ch(C, name, x, y, h, t, t0=None, out_t=None, flip=False, enter=None, dist=260, alpha=1.0, gray=0.0, tint=None, anchor=(0.5, 1.0), bob=0.0, w=None, edge=6, d=0.6):
    """캐릭터·소품 컷아웃(흰 테두리 + 그림자). (x, y) = 발밑 가운데. enter = 'left' | 'right' | 'up' | 'down' 에서 밀려 들어온다(없으면 서서히). edge=0 이면 테두리 없이"""
    if t0 is not None and t < t0: return
    a = 1.0 if t0 is None else fade(t, t0, 0.3, out_t, 0.25)
    if a <= 0: return
    src = flipped(name) if flip else name
    k = 1.0 if (t0 is None or not enter) else EO(t, t0, d)
    dx = {'left': -dist, 'right': dist}.get(enter, 0) * (1 - k); dy = {'up': -dist, 'down': dist}.get(enter, 0) * (1 - k)
    sc = fit(src, h=h, w=w)
    put(C, sticker_spr(src, edge) if edge else src, x + dx, y + dy + (bob * math.sin(t * 1.6 + x * 0.01) if bob else 0.0), sc, a * alpha, anchor=anchor, gray=gray, tint=tint)

def glow(C, x, y, r, alpha=0.8, color=(255, 190, 90)):
    """등불 같은 따뜻한 빛 번짐"""
    key = ('GLOW', color)
    if key not in _REG:
        n = 256; yy, xx = np.mgrid[0:n, 0:n].astype(np.float32); d = np.clip(1 - np.hypot(xx - n / 2, yy - n / 2) / (n / 2), 0, 1) ** 2.2
        im = np.zeros((n, n, 4), np.uint8); im[..., :3] = color; im[..., 3] = (d * 255).astype(np.uint8); reg(key, im)
    put(C, key, x, y, r / 128, alpha, blend='add')

def sil(name, color=(14, 14, 20)):
    """그림의 검은 실루엣"""
    key = (name, 'SIL', color)
    if key not in _REG:
        a = (_REG[name] if name in _REG else img(name)).copy(); a[..., :3] = color; reg(key, a)
    return key

NIGHT_TINT = (30, 42, 78, 0.42)                                    # 밤 장면의 캐릭터에 입히는 색

# ---------------- 선·표시 ----------------
def strike(C, x, y, w, t, t0, color=RED, width=14):
    """글자 위에 긋는 취소선"""
    stroke_path(C, [(x - w / 2, y + 8), (x + w / 2, y - 8)], draw_on(t, t0, 0.28), color, width, outline=WHITE)

def xmark(C, x, y, t, t0, r=20, color=RED, width=12, out_t=None):
    a = fade(t, t0, 0.05, out_t, 0.3)
    if a <= 0: return
    stroke_path(C, [(x - r, y - r), (x + r, y + r)], draw_on(t, t0, 0.2), color, width, alpha=a, outline=WHITE)
    stroke_path(C, [(x + r, y - r), (x - r, y + r)], draw_on(t, t0 + 0.16, 0.2), color, width, alpha=a, outline=WHITE)

def tally(C, x, y, n, t, t0, gap=0.16, h=70, step=26, color=WHITE, width=9):
    """작대기를 하나씩 긋는다. 다섯 번째는 가로지르는 사선"""
    for i in range(n):
        ti = t0 + i * gap * SL
        if t < ti: break
        g, j = divmod(i, 5); x0 = x + g * step * 5.6
        if j < 4: stroke_path(C, [(x0 + j * step, y), (x0 + j * step + 4, y + h)], draw_on(t, ti, 0.12), color, width, outline=DARK)
        else: stroke_path(C, [(x0 - 12, y + h * 0.72), (x0 + 3 * step + 14, y + h * 0.22)], draw_on(t, ti, 0.14), color, width, outline=DARK)

# =====================================================================================
# 본편용 도우미 (s14~): 컷 하나를 한두 줄로 쓴다. u = 컷이 시작된 뒤 지난 초
# =====================================================================================
def seq(C, t, items, xf=0.25):
    """컷 나누기: items = [(시작 시각, 그리는 함수(C, t, u)), ...]"""
    i = 0
    for k, (t0, _) in enumerate(items):
        if t >= t0: i = k
    t0, fn = items[i]
    a = 1.0 if i == 0 else lin(t, t0, t0 + xf)
    if a < 1:
        p0, pf = items[i - 1]; pf(C, t, t - p0); D = new_canvas(); fn(D, t, t - t0); C[:] = C * (1 - a) + D * a
    else: fn(C, t, t - t0)

_CAMS = [((0.5, 0.5, 1.0), (0.5, 0.48, 1.12)), ((0.42, 0.5, 1.10), (0.58, 0.5, 1.10)), ((0.5, 0.46, 1.14), (0.5, 0.5, 1.02)), ((0.58, 0.5, 1.10), (0.42, 0.48, 1.12))]
def pic(C, u, name, cam=None, dur=6.0, word=None, at=0.35, xy=(1440, 330), size=140, col='w', sub=None, vig=0.3, dark=0.0, out=None):
    """화면 가득한 그림 + 느린 카메라 + (있으면) 큰 낱말 하나. cam = ((x, y, 배율), (x, y, 배율)) 또는 0~3(정해 둔 움직임). col = 'w' 흰 글씨 | 'k' 검은 글씨 | 'r' 빨간 글씨"""
    if cam is None: cam = sum(ord(c) for c in name) % 4
    a, b = _CAMS[cam] if isinstance(cam, int) else cam
    kb(C, name, u, dur, a, b)
    if dark: dim(C, dark)
    if vig: vignette(C, vig)
    if word: W1(C, u, word, at, xy, size, col, sub, out)

def W1(C, u, word, at=0.3, xy=(960, 480), size=150, col='w', sub=None, out=None):
    """큰 낱말 하나 (+ 아래 작은 줄)"""
    c, e = {'w': (WHITE, DARK), 'k': (INK1, WHITE), 'r': (RED, WHITE), 'y': (YEL, DARK)}[col]
    T(C, word, xy[0], xy[1], u, at, size, c, edge=e, glow=0.7, out_t=out)
    if sub: T(C, sub, xy[0], xy[1] + size * 0.5 + 60, u, at + 0.2, int(size * 0.42), (255, 130, 120) if col in 'wy' else RED, edge=e, font=F_SAY, glow=0.5, out_t=out)

def no(C, u, word, at=0.3, xy=(960, 480), size=150, col='w', cut=0.5):
    """낱말이 나왔다가 빨간 줄로 지워진다 (…이 아니라)"""
    c, e = {'w': (WHITE, DARK), 'k': (INK1, WHITE)}[col]
    spr = lab_spr(word, size, c, e, None, 0.7); a = fade(u, at, 0.25)
    if a <= 0: return
    w, h = put_ink(C, spr, xy[0], xy[1], a); strike(C, xy[0], xy[1], w + 50, u, at + cut, width=max(10, int(size * 0.10)))

def paper(C, u, tone=0.0, name='bg_parch'):
    """종이 바탕 (tone > 0 이면 갈색으로 눌러 어둡게). 그림(name)이 없으면 종이색으로 칠한다"""
    if has_asset(name): kb(C, name, u, 10, (0.5, 0.5, 1.0), (0.5, 0.5, 1.05))
    else: C[:] = np.array(PARCH, np.float32)
    if tone: dim(C, tone, (60, 40, 22))

def dark(C, u, amt=0.0, name='bg_dark'):
    """어두운 바탕. 그림(name)이 없으면 짙은 회색으로 칠한다"""
    if has_asset(name): kb(C, name, u, 10, (0.5, 0.5, 1.0), (0.5, 0.5, 1.05))
    else: C[:] = np.array((34, 34, 38), np.float32)
    if amt: dim(C, amt)

def port(C, u, who, name=None, sub=None, line=None, side='left', h=980, bg=None, at=0.1, say_at=0.9, say_xy=None, size=110, tail=None, flip=False):
    """반신 인물을 화면 한쪽에 크게 세우고 이름표와 말풍선을 붙인다"""
    if bg: bg(C, u)
    L = side == 'left'; x = 560 if L else 1360
    ch(C, who, x, 1090, h, u, at, enter='left' if L else 'right', dist=200, flip=flip)
    if name: plate(C, name, 1010 if L else 130, 560, u, at + 0.45, sub=sub, size=size)
    if line:
        sx, sy = say_xy or ((x + 230, 250) if L else (x - 230, 250))
        say(C, line, sx, sy, u, say_at, tail=tail or ('left' if L else 'right'), size=60)

def mapcam(mx, my, u, z0=1.3, z1=3.2, d=2.0, start=None):
    """지도가 (mx, my) 로 다가가는 카메라"""
    k = E(u, 0.15, d); z = lerp(z0, z1, k); sx, sy = start or (mx + 220, my + 20)
    cx = lerp(sx, mx + 110 / z1 * 3.2, k); cy = lerp(sy, my - 20, k)
    im = bgimg(MAP); h, w = im.shape[:2]
    return Cam(min(max(cx, W / 2 / z), w - W / 2 / z), min(max(cy, H / 2 / z), h - H / 2 / z), z)

def intro(C, u, nth, title, who, mx, my, pname, year, at=None, side='right', z1=3.2, cx=1580):
    """새 전장 소개: 지도가 그곳으로 다가가고, 표시와 지명, 그 시대 병사, '몇 번째 전장' 이름표"""
    cam = mapcam(mx, my, u, z1=z1); draw_bg(C, MAP, cam)
    sx, sy = cam.S(mx, my)
    place(C, sx, sy, pname, u, 1.6 if at is None else at, sub=year, size=92, r=26, side=side)
    ch(C, who, cx, 1010, 860, u, 0.4, enter='right' if cx > 960 else 'left', dist=300)
    plate(C, title, 110, 250, u, 0.6, sub=nth, size=140)

def arrow(C, pts, u, at, d=0.8, color=RED, width=12, head=30, out=None):
    a = fade(u, at, 0.1, out, 0.25)
    if a > 0: stroke_path(C, smooth_path(pts) if len(pts) > 2 else pts, draw_on(u, at, d), color, width, alpha=a, arrow=head, outline=WHITE)

def num(C, u, v0, v1, x, y, at=0.3, size=150, fmt='{:,}', col='r', d=1.3, rnd=0, tail=''):
    """숫자가 올라간다"""
    if u < at: return
    v = v1 if u >= at + d * SL else int(round(count(v0, v1, u, at, d), rnd))
    c, e = {'w': (WHITE, DARK), 'k': (INK1, WHITE), 'r': (RED, WHITE)}[col]
    T(C, fmt.format(v) + tail, x, y, u, at, size, c, edge=e, glow=0.7)

def split2(C, u, left, right, at=0.0):
    """화면을 둘로 나눠 왼쪽·오른쪽 그림을 같이 보여 준다. left / right = 그리는 함수(C, u). 오른쪽이 at 초에 밀려 들어온다"""
    left(C, u); k = E(u, at, 0.8)
    if k > 0:
        D = new_canvas(); right(D, u); x0 = int(W - 960 * k); C[:, x0:] = D[:, x0:]; rect(C, x0 - 3, 0, x0 + 3, H, WHITE, 1.0)

def tag(C, u, txt, x, y, at=0.3, size=64, col='k', out=None):
    c, e = {'w': (WHITE, DARK), 'k': (INK1, WHITE), 'r': (RED, WHITE), 'y': (YEL, DARK)}[col]
    T(C, txt, x, y, u, at, size, c, edge=e, glow=0.5, out_t=out)

def waves(C, x, y, u, at=0.0, n=3, r0=40, color=WHITE):
    """소리가 퍼지는 고리"""
    for i in range(n):
        v = ((u - at) * 0.8 + i / n) % 1.0
        if u > at: circle(C, x, y, r0 + 160 * v, color, 5, (1 - v) * 0.8)

def sepia(C, u, name, x, y, w, t0, rot=0):
    """흰 테두리 사진 한 장 (흑갈색)"""
    key = ('SEPIA', name, w)
    if key not in _REG:
        im = Image.fromarray(bgimg(name).astype(np.uint8)).convert('L').resize((w, int(w * 0.5667))); g = np.array(im).astype(np.float32)[..., None] / 255
        rgb = (g * np.array([236, 214, 178]) + (1 - g) * np.array([44, 32, 22])).astype(np.uint8); h = rgb.shape[0]; m = 22
        o = np.full((h + m * 2, w + m * 2, 4), 255, np.uint8); o[..., :3] = (244, 240, 230); o[m:m + h, m:m + w, :3] = rgb; reg(key, _shadowed(o, 10, 16, 0.4))
    a = fade(u, t0, 0.25)
    if a > 0: put(C, key, x, y + 30 * (1 - EO(u, t0, 0.5)), 1.0, a, rot=rot)

def snd(**kw):
    """SFX 목록 만들기: snd(low=[0.0], thud=[1.2, 3.4], wind=[(2.0, 4.0)])"""
    out = []
    for name, ts in kw.items():
        for x in ts: out.append((x[0], name, x[1]) if isinstance(x, tuple) else (x, name))
    return out
