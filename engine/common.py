from mg import *
from mg import _REG, _font

def fit(spr, h=None, w=None):
    sw, sh = sprite_size(spr)
    if h is not None and w is not None: return min(h / sh, w / sw)
    return h / sh if h is not None else w / sw

def sticker_spr(spr, width=10, color=(255, 255, 255), shadow=True):
    """컷아웃에 흰 테두리와 옅은 그림자를 둘러 '스티커'로 만든다. 반환값을 put / g 에 그대로 쓴다."""
    key = ('STK', spr, width, tuple(color), shadow)
    if key in _REG: return key
    a = _REG[spr] if spr in _REG else img(spr)
    pad = width + (16 if shadow else 2)
    src = cv2.copyMakeBorder(a, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0)).astype(np.float32)
    al = src[..., 3] / 255
    solid = ndimage.binary_fill_holes(al > 0.5).astype(np.uint8) * 255                      # 안쪽 구멍도 메워 테두리가 바깥에만 생기게
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * width + 1, 2 * width + 1))
    ring = cv2.GaussianBlur(cv2.dilate(solid, k), (0, 0), 0.8).astype(np.float32) / 255     # 테두리 포함 실루엣
    rgb = src[..., :3] * al[..., None] + np.array(color, np.float32) * (1 - al[..., None])
    out_a = np.maximum(ring, al)
    if shadow:
        sh = cv2.GaussianBlur(np.roll(np.roll(ring, 7, 0), 4, 1), (0, 0), 6) * 0.30
        rgb = rgb * out_a[..., None]; fa = out_a + sh * (1 - out_a); rgb = rgb / np.maximum(fa, 1e-4)[..., None]; out_a = fa
    return reg(key, np.dstack([np.clip(rgb, 0, 255), out_a * 255]).astype(np.uint8))

def nametag(C, name, x, y, t, t0, size=78, sub=None, out_t=None, anchor=(0, 0.5)):
    """reference style: big black bold name with thick white stroke."""
    s, a = pop(t, t0, 0.5, out_t)
    if a <= 0: return
    spr = text_spr(name, size, F_TITLE, (18, 14, 12), 9, WHITE, shadow=0)
    put(C, spr, x, y, s, a, anchor=anchor)
    if sub:
        s2, a2 = pop(t, t0 + 0.22, 0.5, out_t)
        put(C, text_spr(sub, int(size * 0.55), F_TITLE, (150, 18, 22), 7, WHITE), x + 6, y + size * 0.85, s2, a2, anchor=(0, 0.5))

def stamp_frame_spr(w, h, color=(176, 22, 28)):
    """도장 테두리. assets/stamp_frame.png 가 있으면 그것을, 없으면 직접 그린다."""
    if has_asset('stamp_frame'): return 'stamp_frame'
    w, h = int(w), int(h); key = ('STAMPF', w, h, tuple(color))
    if key in _REG: return key
    S = 2; bw = max(6, int(h * 0.075)); pad = 6
    im = Image.new('RGBA', ((w + pad * 2) * S, (h + pad * 2) * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([pad * S, pad * S, (pad + w) * S, (pad + h) * S], int(h * 0.12) * S, outline=tuple(color) + (255,), width=bw * S)
    g = bw * 2
    d.rounded_rectangle([(pad + g) * S, (pad + g) * S, (pad + w - g) * S, (pad + h - g) * S], int(h * 0.06) * S, outline=tuple(color) + (255,), width=max(2, bw // 3) * S)
    arr = np.array(im.resize((w + pad * 2, h + pad * 2), Image.LANCZOS))
    rng = np.random.default_rng(11)   # 잉크가 덜 묻은 듯한 거친 질감
    n = cv2.resize(rng.random((arr.shape[0] // 5 + 2, arr.shape[1] // 5 + 2)).astype(np.float32), (arr.shape[1], arr.shape[0]), interpolation=cv2.INTER_CUBIC)
    arr[..., 3] = (arr[..., 3] * np.clip(0.55 + n * 0.9, 0, 1)).astype(np.uint8)
    return reg(key, arr)

def stamp_spr(txt, size=96, w=None, color=(176, 22, 28)):
    """테두리 + 글자를 한 장으로 합친 도장. 글자는 실제 획(잉크) 기준으로 테두리 정중앙에 놓는다."""
    key = ('STAMP', txt, size, w, tuple(color))
    if key in _REG: return key
    t = _REG[text_spr(txt, size, F_TITLE, color, 0)]
    ys, xs = np.where(t[..., 3] > 8)
    t = t[ys.min():ys.max() + 1, xs.min():xs.max() + 1]          # 글자 스프라이트의 여백(아래쪽이 더 큼)을 잘라낸다
    th, tw = t.shape[:2]
    fw = int(max(w or 0, tw + size * 1.1)); fh = int(max(size * 1.75, th + size * 0.9))
    fk = stamp_frame_spr(fw, fh, color)
    f = img(fk) if fk == 'stamp_frame' else _REG[fk]
    if fk == 'stamp_frame':                                       # 사용자 에셋 테두리: 폭에 맞춰 축소·확대
        sc = fw / f.shape[1]; f = cv2.resize(f, (fw, max(1, int(round(f.shape[0] * sc)))), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_CUBIC)
    H2, W2 = max(f.shape[0], th), max(f.shape[1], tw)
    out = Image.new('RGBA', (W2, H2), (0, 0, 0, 0))
    out.alpha_composite(Image.fromarray(f), ((W2 - f.shape[1]) // 2, (H2 - f.shape[0]) // 2))
    out.alpha_composite(Image.fromarray(t), ((W2 - tw) // 2, (H2 - th) // 2))
    arr = np.array(out)
    arr[arr[..., 3] == 0, :3] = 255        # 투명한 곳의 색을 흰색으로: 회전·곱하기 합성 때 가장자리 선이 생기지 않게
    return reg(key, arr)

def stamp(C, txt, x, y, t, t0, size=96, rot=-7, out_t=None, w=None, color=(176, 22, 28), blend='multiply'):
    """rubber stamp slam: frame + crimson text, (x, y) = 도장 중심."""
    if t < t0: return
    x_ = (t - t0) / 0.22
    s = lerp(2.3, 1.0, ease_in(x_)) if x_ < 1 else 1.0
    a = clamp(x_ * 1.6)
    if out_t is not None: a *= 1 - clamp((t - out_t) / 0.25)
    sh = 0
    if 0 < t - t0 - 0.22 < 0.18: sh = math.sin((t - t0) * 90) * 7 * (1 - (t - t0 - 0.22) / 0.18)
    put(C, stamp_spr(txt, size, w, color), x + sh, y, s, a * 0.93, rot=rot, blend=blend)

def pin_spr(color=(176, 22, 28)):
    """지도 핀. assets/pin.png 가 있으면 그것을, 없으면 직접 그린다."""
    if has_asset('pin'): return 'pin'
    key = ('PIN', tuple(color))
    if key in _REG: return key
    S = 2; w, h = 200, 300
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    dark = tuple(int(c * 0.72) for c in color)
    d.polygon([(48 * S, 150 * S), (152 * S, 150 * S), (100 * S, 296 * S)], fill=dark + (255,))
    d.ellipse([10 * S, 6 * S, 190 * S, 186 * S], fill=tuple(color) + (255,), outline=dark + (255,), width=6 * S)
    d.ellipse([66 * S, 62 * S, 134 * S, 130 * S], fill=(250, 240, 222, 255))
    return reg(key, np.array(im.resize((w, h), Image.LANCZOS)))

def pin(C, cam, x, y, t, t0, h=110, out_t=None, color=(176, 22, 28)):
    """pin dropping onto world point (bottom tip at x,y)."""
    if t < t0: return
    k = clamp((t - t0) / 0.45)
    dy = -160 * (1 - ease_out(k)) + (math.sin(k * math.pi) * -10 if k < 1 else 0)
    a = clamp(k * 3)
    if out_t is not None: a *= 1 - clamp((t - out_t) / 0.25)
    sx, sy = cam.S(x, y)
    if k > 0.85:
        sp = clamp((t - t0 - 0.38) / 0.5)
        circle(C, sx, sy, 10 + 60 * sp, color, 4, alpha=(1 - sp) * a)
    spr = pin_spr(color)
    put(C, spr, sx, sy + dy, fit(spr, h), a, anchor=(0.5, 0.97))

def map_label(C, cam, txt, x, y, t, t0, size=58, out_t=None, color=INK, dx=0, dy=-140):
    sx, sy = cam.S(x, y)
    label(C, txt, sx + dx, sy + dy, t, t0, size, F_TITLE, color, 7, CREAM, out_t)

def flash(C, t, tc, d=0.18, color=(255, 248, 235), peak=0.85):
    if tc - d < t < tc + d:
        a = (1 - abs(t - tc) / d) * peak
        fill(C, color, a)

def caption_bar(C, txt, t, t0, out_t=None, y=110, size=64):
    """title text with dark band, like reference title cards."""
    a = fade(t, t0, 0.25, out_t, 0.25)
    if a <= 0: return
    spr = text_spr(txt, size, F_TITLE, WHITE, 0)
    tw, th = sprite_size(spr)
    rect(C, W / 2 - tw / 2 - 40, y - th / 2 - 4, W / 2 + tw / 2 + 40, y + th / 2 + 4, (22, 14, 10), 0.72 * a)
    put(C, spr, W / 2, y, 1.0, a)

def red_spread_mask(shape, cx, cy, prog, seed=3, scale=1.0):
    """organic growing mask (0..1) from a point; prog 0..1 maps radius 0..maxR."""
    h, w = shape
    key = ('noise', h, w, seed)
    if key not in _REG:
        rng = np.random.default_rng(seed)
        n = cv2.resize(rng.random((h // 24 + 2, w // 24 + 2)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        n2 = cv2.resize(rng.random((h // 6 + 2, w // 6 + 2)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        _REG[key] = n * 0.7 + n2 * 0.3
    noise = _REG[key]
    dkey = ('dist', h, w, cx, cy)
    if dkey not in _REG:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        _REG[dkey] = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    dist = _REG[dkey]
    maxR = math.hypot(max(cx, w - cx), max(cy, h - cy)) * scale
    R = prog * maxR
    field = dist + (noise - 0.5) * 260
    return np.clip((R - field) / 60.0, 0, 1)

_BUB_ANCHOR = {}
def bubble_spr(txt, size=64, tail='left', fill=(255, 255, 255), ink=(15, 12, 10), font=None):
    """만화 말풍선. 글자의 실제 획 크기에 딱 맞춰 그린다(글자보다 헐렁한 풍선이 되지 않게).
    tail: 'left'(꼬리가 왼쪽 → 풍선은 화자의 오른쪽 위로) | 'right' | 0~1 사이 숫자(꼬리의 가로 위치)."""
    font = font or F_TITLE
    key = ('BUB', txt, size, tail, tuple(fill), font)
    if key in _REG: return key
    S = 2; f = _font(font, size * S)
    d0 = ImageDraw.Draw(Image.new('L', (8, 8)))
    fat = 0 if font == F_TITLE else max(1, int(round(size * S * 0.0125)))    # 붓글씨처럼 가는 글꼴은 획을 고르게 살짝 부풀린다
    sw = 0   # PIL 의 stroke 로 굵히면 ㅃ·ㅂ 같은 글자의 속이 메워지거나 획이 깨진다 → 쓰지 않는다
    lines = txt.split('\n')
    bbs = [d0.textbbox((0, 0), l, font=f, stroke_width=sw) for l in lines]
    rb = d0.textbbox((0, 0), '한', font=f, stroke_width=sw); rh = rb[3] - rb[1]   # 글자 몸통 높이: 여백·꼬리 크기의 기준
    lh = int(rh * 1.32)
    tw = max(b[2] - b[0] for b in bbs); th = lh * (len(lines) - 1) + rh
    padx, pady = int(rh * 0.52), int(rh * 0.36); lw = max(4 * S, int(rh * 0.075))
    w, h = tw + padx * 2, th + pady * 2
    tail_h = int(rh * 0.55); tail_w = int(rh * 0.42); m = lw + 2 * S
    fr = {'left': 0.24, 'right': 0.76}.get(tail, tail if isinstance(tail, (int, float)) else 0.5)
    tx = m + w * fr; lean = (0.5 - fr) * -1.0 * rh * 0.5                        # 꼬리 끝은 화자 쪽(풍선 바깥쪽)으로 살짝 기운다
    im = Image.new('RGBA', (w + m * 2, h + tail_h + m * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    r = min(h // 2, int(rh * 0.95))
    tip = (tx + lean, m + h + tail_h)
    d.polygon([(tx - tail_w / 2, m + h - lw), (tx + tail_w / 2, m + h - lw), tip], fill=tuple(ink) + (255,))
    d.rounded_rectangle([m, m, m + w, m + h], radius=r, fill=tuple(ink) + (255,))
    d.rounded_rectangle([m + lw, m + lw, m + w - lw, m + h - lw], radius=max(r - lw, 2), fill=tuple(fill) + (255,))
    d.polygon([(tx - tail_w / 2 + lw, m + h - lw * 1.6), (tx + tail_w / 2 - lw, m + h - lw * 1.6), (tip[0] - lean * 0.12, tip[1] - lw * 2.0)], fill=tuple(fill) + (255,))
    tm = Image.new('L', im.size, 0); dt = ImageDraw.Draw(tm)                 # 글자는 따로 그려서 고르게 부풀린 뒤 얹는다
    for i, (l, bb) in enumerate(zip(lines, bbs)):
        dt.text((m + (w - (bb[2] - bb[0])) / 2 - bb[0], m + pady + i * lh - rb[1]), l, font=f, fill=255)
    tm = np.array(tm)
    if fat: tm = cv2.dilate(tm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * fat + 1, 2 * fat + 1)))
    im.paste(Image.new('RGBA', im.size, tuple(ink) + (255,)), (0, 0), Image.fromarray(tm))
    _BUB_ANCHOR[key] = (tip[0] / im.width, tip[1] / im.height)
    im = im.resize((im.width // S, im.height // S), Image.LANCZOS)
    return reg(key, np.array(im))

def bubble(C, txt, x, y, t, t0, size=64, tail='left', out_t=None, font=None):
    """말풍선. (x, y) = 꼬리 끝 = 화자의 입·머리 바로 옆. 풍선은 그 위로 붙는다."""
    s, a = pop(t, t0, 0.5, out_t)
    if a <= 0: return
    txt = txt.replace('…', '...')                              # 말줄임표 글자가 없는 글꼴이 많다
    spr = bubble_spr(txt, size, tail, font=font)
    put(C, spr, x, y, s, a, anchor=_BUB_ANCHOR[spr])
