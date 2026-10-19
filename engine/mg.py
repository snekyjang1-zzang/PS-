# Motion graphics mini-engine: numpy/cv2 compositing, piped to ffmpeg with narration audio.
import os, re, sys, math, glob, shutil, wave, subprocess, functools
import numpy as np, cv2
from scipy import ndimage
from speech import speak_len
from PIL import Image, ImageDraw, ImageFont

for _s in (sys.stdout, sys.stderr):   # 윈도우 콘솔(cp949)에서 한글·기호 출력 오류 방지
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 프로젝트(영상 1편) 폴더. mgp.py 가 MG_PROJECT 를 projects/<이름> 으로 지정한다.
ROOT = os.path.abspath(os.environ.get('MG_PROJECT') or KIT)
ASSETS = os.environ.get('MG_ASSETS') or os.path.join(ROOT, 'assets')
FONTS = os.path.join(KIT, 'fonts')
OUTDIR = os.environ.get('MG_OUT') or os.path.join(ROOT, 'out')
INPUT = os.path.join(ROOT, 'input')
CAPTURES = os.path.join(ROOT, 'captures')
BRAND = os.path.join(KIT, 'brand')                         # 채널 공용 에셋(마스코트 등): 모든 프로젝트에서 이름으로 바로 쓴다

def _find(exts, env):
    if os.environ.get(env): return os.environ[env]
    hits = []
    for e in exts:
        hits += [h for h in sorted(glob.glob(os.path.join(INPUT, '*.' + e))) if h not in hits]
    if not hits: return None
    pref = [h for h in hits if os.path.basename(h).lower().startswith('narration.')]
    if len(hits) > 1 and not pref:
        print(f'[경고] input/ 에 파일이 여러 개입니다. {os.path.basename(hits[0])} 를 사용합니다: {[os.path.basename(h) for h in hits]}', file=sys.stderr)
    return (pref or hits)[0]
# input/ 폴더의 narration.wav + narration.srt 를 사용 (mgp.py tts 가 만든다. MG_AUDIO / MG_SRT 로 직접 지정 가능)
AUDIO = _find(['wav', 'mp3', 'm4a'], 'MG_AUDIO')
SRT = _find(['srt'], 'MG_SRT')
W, H, FPS = 1920, 1080, 30
os.makedirs(OUTDIR, exist_ok=True)

@functools.lru_cache(None)
def ffmpeg_exe():
    p = os.environ.get('MG_FFMPEG') or shutil.which('ffmpeg')
    if p: return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise SystemExit('ffmpeg 를 찾을 수 없습니다. "python mgp.py setup" 을 다시 실행하세요.')

VIDEO_EXT = ('.mp4', '.mov', '.m4v', '.webm', '.mkv')
def cap_file(name):
    """captures/ 안의 동영상 경로. 확장자를 안 적으면 mp4 → mov → ... 순으로 찾는다 (맥 화면 기록은 .mov 로 저장된다)."""
    if name.lower().endswith(VIDEO_EXT): return os.path.join(CAPTURES, name)
    for e in VIDEO_EXT:
        p = os.path.join(CAPTURES, name + e)
        if os.path.exists(p): return p
    return os.path.join(CAPTURES, name + '.mp4')

def media_duration(path):
    """길이(초). wav 는 직접 읽고, 그 외는 ffmpeg 출력에서 읽는다 (ffprobe 불필요)."""
    if path.lower().endswith('.wav'):
        try:
            with wave.open(path, 'rb') as w: return w.getnframes() / w.getframerate()
        except Exception: pass
    r = subprocess.run([ffmpeg_exe(), '-hide_banner', '-i', path], capture_output=True)
    m = re.search(r'Duration:\s*(\d+):(\d+):([\d.]+)', r.stderr.decode('utf-8', 'replace'))
    if not m: raise RuntimeError(f'길이를 읽을 수 없습니다: {path}')
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

def has_asset(name):
    fn = name if name.endswith('.png') else f'{name}.png'
    return os.path.exists(os.path.join(ASSETS, fn)) or os.path.exists(os.path.join(BRAND, fn))

F_TITLE = os.path.join(FONTS, 'BlackHanSans-Regular.ttf')
F_BRUSH = os.path.join(FONTS, 'NanumBrushScript-Regular.ttf')
F_SERIF = os.path.join(FONTS, 'NanumMyeongjo-ExtraBold.ttf')
F_SANS = os.path.join(FONTS, 'NanumGothic-Bold.ttf')
F_SANSR = os.path.join(FONTS, 'NanumGothic-Regular.ttf')

INK = (42, 26, 16)
CRIMSON = (150, 18, 22)
CREAM = (244, 232, 204)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# ---------------- timing ----------------
def _ts(s):
    h, m, r = s.split(':'); sec, ms = r.split(',')
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000

def load_srt():
    if not SRT: return {}
    txt = open(SRT, encoding='utf-8-sig').read().replace('\r\n', '\n').replace('\r', '\n').strip()
    cues = {}
    for blk in re.split(r'\n\s*\n', txt):
        ln = [l for l in blk.strip().split('\n') if l.strip()]
        k = next((i for i, l in enumerate(ln) if '-->' in l), None)
        if k is None or k + 1 >= len(ln): continue
        m = re.findall(r'(\d+:\d+:\d+[,.]\d+)', ln[k])
        if len(m) < 2: continue
        num = int(ln[k - 1]) if k > 0 and ln[k - 1].strip().isdigit() else len(cues) + 1
        cues[num] = (_ts(m[0].replace('.', ',')), _ts(m[1].replace('.', ',')), ' '.join(l.strip() for l in ln[k + 1:]))
    return cues
CUES = load_srt()

def _cue(n):
    if n not in CUES:
        if not CUES: raise SystemExit(f'자막(SRT)이 없습니다. {INPUT} 에 narration.srt 가 있는지 확인하세요 (python mgp.py tts <프로젝트>).')
        raise SystemExit(f'자막 {n}번이 없습니다. 이 영상의 자막은 {min(CUES)}~{max(CUES)}번입니다 ({SRT}).')
    return CUES[n]
def cs(n): return _cue(n)[0]
def ce(n): return _cue(n)[1]
def wt(n, sub, occ=0):
    """estimated absolute time when `sub` is spoken inside cue n (읽는 길이 비례: 숫자는 읽는 음절 수로 센다)."""
    a, b, t = _cue(n)
    i = -1
    for _ in range(occ + 1):
        i = t.find(sub, i + 1)
        if i < 0: raise SystemExit(f"wt({n}, '{sub}'): 자막 {n}번에 '{sub}' 가 없습니다 → \"{t}\"")
    return a + (b - a) * (speak_len(t[:i]) / max(speak_len(t), 1e-6))

# ---------------- easing ----------------
PACE = float(os.environ.get('MG_PACE', '1') or 1)   # project.json 의 style.pace: 등장·퇴장·선 그리기 길이에 곱한다 (1.3 = 30% 느리게)
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lin(t, t0, t1): return clamp((t - t0) / max(t1 - t0, 1e-6))
def ease_io(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp(x); return x ** 3
def back(x, s=1.9):
    x = clamp(x); c3 = s + 1
    return 1 + c3 * (x - 1) ** 3 + s * (x - 1) ** 2
def lerp(a, b, x): return a + (b - a) * x
def ramp(t, t0, t1, a, b, ease=ease_io): return lerp(a, b, ease(lin(t, t0, t1)))
def pop(t, t0, d=0.55, out_t=None, out_d=0.35):
    """returns (scale, alpha) for a pop-in (and optional fade-out). 등장 뒤에도 아주 천천히 커지며 살아 있게 한다."""
    if t < t0: return 0.0, 0.0
    d *= PACE; out_d *= PACE
    x = (t - t0) / d
    s = (back(x, 1.35) if x < 1 else 1.0) * alive(t, t0 + d)
    a = clamp(x * 2.0)
    if out_t is not None and t > out_t:
        y = clamp((t - out_t) / out_d)
        a *= 1 - y; s *= 1 - 0.15 * y
    return max(s, 0.0), a
def fade(t, t0, d=0.3, out_t=None, out_d=0.3):
    d *= PACE; out_d *= PACE
    a = clamp((t - t0) / d) if d > 0 else (1.0 if t >= t0 else 0.0)
    if out_t is not None: a *= 1 - clamp((t - out_t) / out_d)
    return a
def alive(t, t0, amt=0.03, tau=3.5):
    """등장이 끝난 뒤에도 멈춰 보이지 않게: t0 이후 몇 초에 걸쳐 1 → 1+amt 로 아주 천천히 커지는 배율."""
    return 1 + amt * (1 - math.exp(-(t - t0) / tau)) if t > t0 else 1.0
def draw_on(t, t0, d=1.2):
    """선·화살표가 그려지는 진행도(0~1). 기본 1.2초: 너무 빨리 끝나지 않게, 문장 길이에 맞춰 d 를 늘린다."""
    return ease_io(lin(t, t0, t0 + d * PACE))
def stagger(i, gap=0.2):
    """여러 요소를 차례로 등장시킬 때 i 번째 요소의 지연(초)."""
    return i * gap * PACE
def wobble(t, amp=4, f=0.6, ph=0): return amp * math.sin(2 * math.pi * f * t + ph)

# ---------------- assets ----------------
@functools.lru_cache(None)
def _asset_path(name):
    fn = name if str(name).endswith('.png') else f'{name}.png'
    p = os.path.join(ASSETS, fn)
    if not os.path.exists(p) and os.path.exists(os.path.join(BRAND, fn)): return os.path.join(BRAND, fn)
    if not os.path.exists(p):
        have = sorted(f[:-4] for f in os.listdir(ASSETS) if f.endswith('.png')) if os.path.isdir(ASSETS) else []
        raise SystemExit(f"에셋 '{name}' 이 없습니다 ({p}).\n  assets.json 에 추가해 생성하거나(python mgp.py assets), 이름을 확인하세요. 있는 에셋: {have}")
    return p

@functools.lru_cache(None)
def img(name):
    return np.array(Image.open(_asset_path(name)).convert('RGBA'))

@functools.lru_cache(None)
def bgimg(name):
    return np.array(Image.open(_asset_path(name)).convert('RGB')).astype(np.float32)

@functools.lru_cache(2048)
def _scaled(name_or_id, s, arr_key=None):
    a = img(name_or_id) if arr_key is None else _REG[arr_key]
    h, w = a.shape[:2]
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
    return cv2.resize(a, (nw, nh), interpolation=interp)

_REG = {}
def reg(key, arr):
    """register a generated RGBA array as a sprite."""
    _REG[key] = arr
    for k in [k for k in _MIP if k[0] == key]: del _MIP[k]
    return key

_MIP = {}
def _mip(spr, s):
    """배율 s 로 그릴 때 쓸 원본: premultiplied RGBA uint8 을 s 배에 가장 가까운 정수 크기로 미리 줄여 둔 것(면적 평균 → 계단·반짝임 없음).
    남는 소수점 크기 차이와 소수점 위치는 put 이 직접 변환한다 → 크기·위치가 연속적으로 변해도 1px 씩 튀지 않는다."""
    src = _REG[spr] if spr in _REG else img(spr)
    h, w = src.shape[:2]
    tw, th = (w, h) if s >= 1 else (max(1, int(round(w * s))), max(1, int(round(h * s))))
    key = (spr, tw, th)
    if key not in _MIP:
        if len(_MIP) > 320: _MIP.clear()
        a = src.astype(np.float32)
        a[..., :3] *= a[..., 3:4] / 255.0                       # premultiply: 가장자리에 어두운·밝은 테두리가 생기지 않게
        if (tw, th) != (w, h): a = cv2.resize(a, (tw, th), interpolation=cv2.INTER_AREA)
        _MIP[key] = np.clip(a + 0.5, 0, 255).astype(np.uint8)
    return _MIP[key], w, h

def get_scaled(spr, s):
    s = round(s, 3)
    if spr in _REG:
        return _scaled(spr, s, spr)
    return _scaled(spr, s)

def sprite_size(spr):
    a = _REG[spr] if spr in _REG else img(spr)
    return a.shape[1], a.shape[0]

# ---------------- canvas ops ----------------
def new_canvas(color=None):
    c = np.empty((H, W, 3), np.float32)
    if color is not None: c[:] = color
    return c

class Cam:
    """camera over a background image coordinate space."""
    def __init__(self, cx=960, cy=544, z=1.0, rot=0.0):
        self.cx, self.cy, self.z, self.rot = cx, cy, z, rot
    def S(self, x, y):
        return (x - self.cx) * self.z + W / 2, (y - self.cy) * self.z + H / 2

def draw_bg(C, name, cam, alpha=1.0):
    src = bgimg(name)
    z = cam.z
    M = np.array([[z, 0, W / 2 - cam.cx * z], [0, z, H / 2 - cam.cy * z]], np.float32)
    out = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if alpha >= 1: C[:] = out
    else: C[:] = C * (1 - alpha) + out * alpha

def put(C, spr, x, y, s=1.0, alpha=1.0, rot=0.0, blend='normal', anchor=(0.5, 0.5), tint=None, gray=0.0):
    """composite sprite with its anchor at screen (x, y). 위치·배율·회전을 소수점 픽셀 단위로 반영한다
    (정수 픽셀로 반올림하면 천천히 움직이거나 커지는 요소가 프레임마다 1px 씩 떨린다)."""
    if alpha <= 0.003 or s <= 0.003: return
    base, w, h = _mip(spr, s)
    h0, w0 = base.shape[:2]; rx, ry = w * s / w0, h * s / h0                      # 미리 줄인 크기와 정확한 크기의 차이(거의 1)
    ax, ay = (w0 / 2, h0 / 2) if rot else (w0 * anchor[0], h0 * anchor[1])       # 회전할 때는 중심 기준(기존 동작 유지)
    th = math.radians(rot); co, si = math.cos(th), math.sin(th)
    A = np.array([[co * rx, si * ry], [-si * rx, co * ry]], np.float64)
    M = np.hstack([A, np.array([[x], [y]]) - A @ np.array([[ax], [ay]])])
    c = A @ np.array([[0, w0, w0, 0], [0, 0, h0, h0]], np.float64) + M[:, 2:3]
    xa, ya = max(int(math.floor(c[0].min())) - 2, 0), max(int(math.floor(c[1].min())) - 2, 0)
    xb, yb = min(int(math.ceil(c[0].max())) + 3, W), min(int(math.ceil(c[1].max())) + 3, H)
    if xa >= xb or ya >= yb: return
    M[0, 2] -= xa; M[1, 2] -= ya
    sub = cv2.warpAffine(base, M, (xb - xa, yb - ya), flags=cv2.INTER_CUBIC,     # CUBIC: 소수점 위치에서도 선명도가 출렁이지 않는다
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0)).astype(np.float32)
    a0 = sub[..., 3:4] / 255.0; rgb = sub[..., :3]                                # rgb 는 premultiplied (= 색 * a0)
    if gray:
        g = rgb.mean(-1, keepdims=True); rgb = rgb * (1 - gray) + g * gray
    if tint is not None:
        rgb = rgb * (1 - tint[3]) + np.array(tint[:3], np.float32) * a0 * tint[3]
    al = a0 * alpha; rgb = rgb * alpha
    dst = C[ya:yb, xa:xb]
    if blend == 'multiply':
        dst[:] = dst * (1 - al) + dst * rgb / 255.0
    elif blend == 'screen':
        dst[:] = dst * (1 - al) + 255 * al - (255 - dst) * (255 * al - rgb) / 255.0
    elif blend == 'add':
        dst[:] = np.minimum(dst + rgb, 255)
    else:
        dst[:] = dst * (1 - al) + rgb

def wput(C, cam, spr, x, y, s=1.0, **kw):
    """put sprite in world (background) coords through camera."""
    sx, sy = cam.S(x, y)
    put(C, spr, sx, sy, s * cam.z, **kw)

def fill(C, color, alpha):
    C[:] = C * (1 - alpha) + np.array(color, np.float32) * alpha

def rect(C, x0, y0, x1, y1, color, alpha=1.0):
    x0, y0, x1, y1 = [int(v) for v in (max(x0, 0), max(y0, 0), min(x1, W), min(y1, H))]
    if x0 >= x1 or y0 >= y1: return
    C[y0:y1, x0:x1] = C[y0:y1, x0:x1] * (1 - alpha) + np.array(color, np.float32) * alpha

# ---------------- text ----------------
@functools.lru_cache(None)
def _font(path, size):
    return ImageFont.truetype(path, size)

def text_spr(txt, size=80, font=F_TITLE, fill=INK, stroke=0, stroke_fill=CREAM, shadow=0, spacing=1.15, align='center', maxw=None):
    """글자 스프라이트. 외곽선은 글자 전체를 한 덩어리로 부풀려 만든다:
    글자 사이 외곽선이 서로 파먹지 않고, 굵은 폰트의 작은 구멍(ㅇ, ㅂ 안쪽)에 점이 남지 않는다."""
    key = ('T', txt, size, font, fill, stroke, stroke_fill, shadow, spacing, align)
    if key in _REG: return key
    SS = 2
    f = _font(font, size * SS)
    lines = txt.split('\n')
    d0 = ImageDraw.Draw(Image.new('L', (8, 8)))
    boxes = [d0.textbbox((0, 0), l, font=f) for l in lines]
    lw = [b[2] - b[0] for b in boxes]
    lh = int(size * spacing) * SS
    pad = (stroke * 2 + shadow + 8) * SS
    wd = max(lw) + pad * 2; ht = lh * len(lines) + pad * 2 + int(size * 0.25) * SS
    m = Image.new('L', (wd, ht), 0); d = ImageDraw.Draw(m)
    for i, l in enumerate(lines):
        if align == 'center': x = (wd - lw[i]) / 2 - boxes[i][0]
        elif align == 'left': x = pad - boxes[i][0]
        else: x = wd - pad - lw[i] - boxes[i][0]
        d.text((x, pad + i * lh - boxes[i][1] + int(size * 0.05) * SS), l, font=f, fill=255)
    m = np.array(m)
    body = m.astype(np.float32) / 255
    if stroke:
        k = stroke * SS
        o = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
        lab, n = ndimage.label(o < 128)                      # 외곽선으로 둘러싸인 작은 구멍은 외곽선 색으로 메운다
        if n > 1:
            area = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
            edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
            small = [i + 1 for i, ar in enumerate(area) if (i + 1) not in edge and ar < (k * 2.4) ** 2]
            if small: o[np.isin(lab, small)] = 255
        o = cv2.GaussianBlur(o, (0, 0), 0.6).astype(np.float32) / 255
    else:
        o = body
    al = np.maximum(o, body)
    rgb = np.array(stroke_fill, np.float32) * (1 - body[..., None]) + np.array(fill, np.float32) * body[..., None]
    if shadow:
        sh = np.zeros_like(al); sh[shadow * SS:, shadow * SS:] = al[:-shadow * SS, :-shadow * SS] * (150 / 255)
        rgb = rgb * al[..., None]; al = al + sh * (1 - al); rgb = rgb / np.maximum(al, 1e-4)[..., None]
    arr = np.dstack([rgb, al * 255])
    arr = cv2.resize(arr, (wd // SS, ht // SS), interpolation=cv2.INTER_AREA)
    reg(key, np.clip(arr, 0, 255).astype(np.uint8))
    return key

def label(C, txt, x, y, t, t0, size=64, font=F_TITLE, fill=INK, stroke=6, stroke_fill=CREAM, out_t=None, anchor=(0.5, 0.5), rot=0, d=0.55, shadow=0):
    s, a = pop(t, t0, d, out_t)
    if a <= 0: return
    put(C, text_spr(txt, size, font, fill, stroke, stroke_fill, shadow), x, y, s, a, rot=rot, anchor=anchor)

def typed(txt, t, t0, cps=14):
    n = int(max(0, (t - t0) * cps))
    return txt[:n]

# ---------------- generated sprites ----------------
def radial(key, r, color, power=1.6, inner=0.0):
    if key in _REG: return key
    d = 2 * r + 2
    yy, xx = np.mgrid[0:d, 0:d].astype(np.float32)
    dist = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
    a = np.clip(1 - dist, 0, 1) ** power
    if inner: a = np.maximum(a, (dist < inner).astype(np.float32))
    arr = np.zeros((d, d, 4), np.uint8); arr[..., :3] = color; arr[..., 3] = (a * 255).astype(np.uint8)
    return reg(key, arr)

def ring(key, r, color, width=6):
    if key in _REG: return key
    d = 2 * r + width * 2 + 4
    im = np.zeros((d * 2, d * 2, 4), np.uint8)
    cv2.circle(im, (d, d), r * 2, tuple(int(c) for c in color) + (255,), width * 2, cv2.LINE_AA)
    im = cv2.resize(im, (d, d), interpolation=cv2.INTER_AREA)
    return reg(key, im)

def blob_dark(key, r, seed=0, color=(18, 10, 14)):
    """irregular necrosis/ink blob."""
    if key in _REG: return key
    rng = np.random.default_rng(seed)
    d = 2 * r + 4
    yy, xx = np.mgrid[0:d, 0:d].astype(np.float32)
    ang = np.arctan2(yy - d / 2, xx - d / 2)
    rad = np.ones_like(ang)
    for k in range(2, 7):
        rad += rng.uniform(0.03, 0.09) * np.sin(k * ang + rng.uniform(0, 6.28))
    dist = np.sqrt((xx - d / 2) ** 2 + (yy - d / 2) ** 2) / (r * rad * 0.92)
    a = np.clip((1 - dist) * 3.0, 0, 1) ** 0.8
    noise = cv2.GaussianBlur(rng.random((d, d)).astype(np.float32), (0, 0), 2)
    a = np.clip(a * (0.85 + 0.3 * noise), 0, 1)
    arr = np.zeros((d, d, 4), np.uint8); arr[..., :3] = color; arr[..., 3] = (a * 235).astype(np.uint8)
    return reg(key, arr)

def circle_crop(key, src, size, ring_col=(250, 245, 230), ring_w=8, focus=(0.5, 0.35), zoom=1.0):
    """circular avatar from sprite name (focus = relative center)."""
    if key in _REG: return key
    a = img(src)
    h, w = a.shape[:2]
    side = int(min(w, h) / zoom)
    cx, cy = int(w * focus[0]), int(h * focus[1])
    x0 = clamp(cx - side // 2, 0, w - side); y0 = clamp(cy - side // 2, 0, h - side)
    x0, y0 = int(x0), int(y0)
    crop = a[y0:y0 + side, x0:x0 + side].copy()
    bgc = np.zeros_like(crop); bgc[..., :3] = (232, 220, 196); bgc[..., 3] = 255
    al = crop[..., 3:4] / 255.0
    crop = (crop * al + bgc * (1 - al)).astype(np.uint8); crop[..., 3] = 255
    crop = cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)
    S = size + ring_w * 2
    out = np.zeros((S, S, 4), np.uint8)
    out[ring_w:ring_w + size, ring_w:ring_w + size] = crop
    m = np.zeros((S * 2, S * 2), np.uint8)
    cv2.circle(m, (S, S), size, 255, -1, cv2.LINE_AA)
    m = cv2.resize(m, (S, S), interpolation=cv2.INTER_AREA)
    out[..., 3] = np.minimum(out[..., 3], m)
    rm = np.zeros((S * 2, S * 2), np.uint8)
    cv2.circle(rm, (S, S), S - 2, 255, -1, cv2.LINE_AA)
    rm = cv2.resize(rm, (S, S), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    inner = m.astype(np.float32) / 255
    ringa = np.clip(rm - inner, 0, 1)
    rgb = out[..., :3].astype(np.float32)
    rgb = rgb * (1 - ringa[..., None]) + np.array(ring_col, np.float32) * ringa[..., None]
    out[..., :3] = rgb.astype(np.uint8)
    out[..., 3] = np.maximum(out[..., 3], (ringa * 255).astype(np.uint8))
    return reg(key, out)

# ---------------- lines / arrows ----------------
def _path_partial(pts, prog):
    pts = np.asarray(pts, np.float32)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    L = seg.sum(); target = L * clamp(prog)
    out = [pts[0]]; acc = 0
    for i, l in enumerate(seg):
        if acc + l >= target:
            r = (target - acc) / max(l, 1e-6)
            out.append(pts[i] + (pts[i + 1] - pts[i]) * r); break
        out.append(pts[i + 1]); acc += l
    return np.array(out), L

def smooth_path(ctrl, n=80):
    """Catmull-Rom through control points."""
    P = np.asarray(ctrl, np.float32)
    if len(P) < 3: return P
    P = np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n // (len(P) - 3) + 2)[:-1]:
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)

def point_at(pts, prog):
    p, _ = _path_partial(pts, prog)
    a = p[-1]; b = p[-2] if len(p) > 1 else p[-1]
    ang = math.degrees(math.atan2(a[1] - b[1], a[0] - b[0]))
    return float(a[0]), float(a[1]), ang

def stroke_path(C, pts, prog, color=CRIMSON, width=10, alpha=1.0, dash=None, arrow=0, outline=None, phase=0.0):
    """draw progressive path in screen coords. dash=(on,off) px. arrow=head size.
    phase(px)를 시간에 따라 키우면 점선이 진행 방향으로 흐른다 (예: phase=t * 60): 다 그려진 뒤에도 움직임이 남는다."""
    if prog <= 0 or alpha <= 0: return
    p, L = _path_partial(pts, prog)
    if len(p) < 2: return
    xs, ys = p[:, 0], p[:, 1]
    pad = width * 2 + arrow * 2 + 6
    x0 = int(max(xs.min() - pad, 0)); y0 = int(max(ys.min() - pad, 0))
    x1 = int(min(xs.max() + pad, W)); y1 = int(min(ys.max() + pad, H))
    if x0 >= x1 or y0 >= y1: return
    SS = 2
    ov = np.zeros(((y1 - y0) * SS, (x1 - x0) * SS), np.uint8)
    FX = 16                                                    # cv2 의 shift=4: 좌표를 1/16 px 단위로 전달
    q = np.round((p - [x0, y0]) * SS * FX).astype(np.int32)
    segs = []
    if dash:
        on, off = dash
        cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
        dpos = (phase % (on + off)) - (on + off); total = cum[-1]
        while dpos < total:
            a_, b_ = max(dpos, 0.0), min(dpos + on, total)
            if b_ <= a_: dpos += on + off; continue
            seg = [np.interp(a_, cum, p[:, 0]), np.interp(a_, cum, p[:, 1])]
            pts_ = [seg]
            for k in range(len(cum)):
                if a_ < cum[k] < b_: pts_.append(p[k])
            pts_.append([np.interp(b_, cum, p[:, 0]), np.interp(b_, cum, p[:, 1])])
            segs.append(np.round((np.array(pts_) - [x0, y0]) * SS * FX).astype(np.int32))
            dpos += on + off
    else:
        segs = [q]
    for s in segs:
        cv2.polylines(ov, [s], False, 255, int(width * SS), cv2.LINE_AA, shift=4)
    if arrow:
        a = p[-1]; b = p[max(len(p) - 4, 0)]
        ang = math.atan2(a[1] - b[1], a[0] - b[0])
        tip = a + np.array([math.cos(ang), math.sin(ang)]) * arrow * 0.6
        l = tip - np.array([math.cos(ang - 0.5), math.sin(ang - 0.5)]) * arrow * 1.4
        r = tip - np.array([math.cos(ang + 0.5), math.sin(ang + 0.5)]) * arrow * 1.4
        tri = np.round((np.array([tip, l, r]) - [x0, y0]) * SS * FX).astype(np.int32)
        cv2.fillPoly(ov, [tri], 255, cv2.LINE_AA, shift=4)
    m = cv2.resize(ov, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255 * alpha
    dst = C[y0:y1, x0:x1]
    if outline is not None:
        k = max(3, int(width * 0.8)) | 1
        mo = cv2.dilate(m[..., 0], np.ones((k, k), np.uint8))[..., None]
        dst[:] = dst * (1 - mo) + np.array(outline, np.float32) * mo
    dst[:] = dst * (1 - m) + np.array(color, np.float32) * m

def circle(C, x, y, r, color, width=6, alpha=1.0, prog=1.0, filled=False):
    if alpha <= 0 or r <= 0: return
    n = 90
    th = np.linspace(-math.pi / 2, -math.pi / 2 + 2 * math.pi * clamp(prog), max(3, int(n * prog)))
    pts = np.stack([x + r * np.cos(th), y + r * np.sin(th)], 1)
    if filled:
        x0, y0, x1, y1 = int(max(x - r - 2, 0)), int(max(y - r - 2, 0)), int(min(x + r + 2, W)), int(min(y + r + 2, H))
        if x0 >= x1 or y0 >= y1: return
        ov = np.zeros(((y1 - y0) * 2, (x1 - x0) * 2), np.uint8)
        cv2.circle(ov, (int(round((x - x0) * 32)), int(round((y - y0) * 32))), int(round(r * 32)), 255, -1, cv2.LINE_AA, shift=4)
        m = cv2.resize(ov, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255 * alpha
        C[y0:y1, x0:x1] = C[y0:y1, x0:x1] * (1 - m) + np.array(color, np.float32) * m
    else:
        stroke_path(C, pts, 1.0, color, width, alpha)

# ---------------- panels ----------------
def panel_spr(key, w, h, fill=(244, 234, 210), border=INK, bw=4, radius=18, alpha=255, shadow=True):
    if key in _REG: return key
    S = 2; pad = 24 if shadow else 4
    im = Image.new('RGBA', ((w + pad * 2) * S, (h + pad * 2) * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
        ds.rounded_rectangle([(pad + 6) * S, (pad + 10) * S, (pad + w + 6) * S, (pad + h + 10) * S], radius * S, fill=(0, 0, 0, 110))
        sh = Image.fromarray(cv2.GaussianBlur(np.array(sh), (0, 0), 10 * S))
        im = Image.alpha_composite(im, sh); d = ImageDraw.Draw(im)
    d.rounded_rectangle([pad * S, pad * S, (pad + w) * S, (pad + h) * S], radius * S, fill=tuple(fill) + (alpha,), outline=tuple(border) + (255,) if bw else None, width=bw * S)
    im = im.resize((w + pad * 2, h + pad * 2), Image.LANCZOS)
    return reg(key, np.array(im))

# ---------------- finishing ----------------
# 빈티지 스타일(흑사병 편): grain 2.2, vignette True, flicker 0.012 / 깔끔한 화이트 스타일: 전부 0
FINISH_GRAIN = float(os.environ.get('MG_GRAIN', '0'))
FINISH_VIGNETTE = os.environ.get('MG_VIGNETTE', '0') == '1'
FINISH_FLICKER = float(os.environ.get('MG_FLICKER', '0'))
_rng = np.random.default_rng(7)
_GRAIN = [cv2.resize(_rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (W, H))[..., None] for _ in range(6)]
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_VIG = (1 - 0.30 * np.clip(((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.70)) ** 2, 0, 1.4))
_VIG3 = np.repeat(_VIG[..., None], 3, axis=2).astype(np.float32)
_GRAIN3 = [np.repeat(g, 3, axis=2) * 1.0 for g in _GRAIN]
del _yy, _xx

def finish(C, fi, grain=FINISH_GRAIN, vignette=FINISH_VIGNETTE, flicker=FINISH_FLICKER):
    f = 1 + flicker * math.sin(fi * 1.7) * math.sin(fi * 0.37)
    if vignette: C = cv2.multiply(C, _VIG3, scale=f)
    if grain: C = cv2.scaleAdd(_GRAIN3[fi % 6], grain, C)
    return cv2.convertScaleAbs(C)

# ---------------- render ----------------
_X264 = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']

def write_video(out, n, frame_u8, extra_in=(), extra_out=()):
    """n 프레임을 ffmpeg 로 인코딩. frame_u8(i) -> uint8 (H, W, 3) RGB."""
    cmd = [ffmpeg_exe(), '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           *extra_in, *_X264, '-r', str(FPS), *extra_out, out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i in range(n):
            p.stdin.write(frame_u8(i).tobytes())
    finally:
        try: p.stdin.close()
        except Exception: pass
        rc = p.wait()
    if rc != 0: raise RuntimeError(f'ffmpeg 인코딩 실패 (코드 {rc}): {out}')
    return out

def save_sheet(path, frames, labels, cols=4, color=(0, 255, 255)):
    """프레임 여러 장을 한 장의 확인용 jpg 로."""
    th = [cv2.resize(f, (480, 270), interpolation=cv2.INTER_AREA) for f in frames]
    rows = (len(th) + cols - 1) // cols
    sheet = np.zeros((rows * 270, cols * 480, 3), np.uint8)
    for i, f in enumerate(th):
        r, c = divmod(i, cols); sheet[r * 270:(r + 1) * 270, c * 480:(c + 1) * 480] = f
        (tw, _), _ = cv2.getTextSize(labels[i], cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(sheet, (c * 480, r * 270), (c * 480 + tw + 16, r * 270 + 40), (0, 0, 0), -1)
        cv2.putText(sheet, labels[i], (c * 480 + 8, r * 270 + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    Image.fromarray(sheet).save(path, quality=85)
    return path

def render(name, a0, a1, frame_fn, preview_times=None, audio=True):
    """단독 클립 렌더(구버전 방식, examples/black_death 참고용). 완성 영상은 timeline.py 의 장면 방식을 쓴다.
    frame_fn(t_local, fi) -> float32 canvas. a0/a1 absolute seconds in the narration."""
    dur = a1 - a0
    n = int(round(dur * FPS))
    out = os.path.join(OUTDIR, name + '.mp4')
    want = {min(n - 1, int(round(tt * FPS))) for tt in (preview_times or [])}
    prev = []
    def fr(fi):
        u8 = finish(frame_fn(fi / FPS, fi), fi)
        if fi in want: prev.append((fi / FPS, u8.copy()))
        return u8
    ein = ['-ss', f'{a0:.3f}', '-t', f'{dur:.3f}', '-i', AUDIO] if audio and AUDIO else []
    eout = (['-c:a', 'aac', '-b:a', '192k'] if ein else []) + ['-t', f'{dur:.3f}']
    write_video(out, n, fr, ein, eout)
    if prev: save_sheet(os.path.join(OUTDIR, name + '_preview.jpg'), [f for _, f in prev], [f'{a0 + t:.1f}s' for t, _ in prev])
    return out

def fmt(t):
    m = int(t // 60); s = t - m * 60
    return f'{m:02d}m{s:05.2f}s'.replace('.', '_')

def draw_arr(C, src, cam, alpha=1.0):
    z = cam.z
    M = np.array([[z, 0, W / 2 - cam.cx * z], [0, z, H / 2 - cam.cy * z]], np.float32)
    out = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if alpha >= 1: C[:] = out
    else: C[:] = C * (1 - alpha) + out * alpha

@functools.lru_cache(None)
def land_mask(name):
    a = bgimg(name)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    land = ((r - b) > 28).astype(np.float32)
    land = cv2.morphologyEx(land, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    land = cv2.GaussianBlur(land, (0, 0), 2.0)
    return land

@functools.lru_cache(None)
def red_tex(h=1097, w=1920):
    a = np.array(Image.open(os.path.join(ASSETS, 'red_wash.png')).convert('RGB')).astype(np.float32)  # 붉은 수채 번짐 원본(흰 배경) 이미지
    hh, ww = a.shape[:2]
    crop = a[int(hh * 0.25):int(hh * 0.75), int(ww * 0.2):int(ww * 0.8)]
    t = cv2.resize(crop, (w, h), interpolation=cv2.INTER_CUBIC)
    return t
