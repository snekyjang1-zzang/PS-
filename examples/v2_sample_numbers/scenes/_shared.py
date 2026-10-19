"""이 영상 공용 도우미: 엑셀 주문서 카드, 숫자 올라가기, 금액 막대"""
from kit import *
from mg import _REG, _font

XGREEN = (33, 115, 70)

def sheet_spr(w=420, h=300):
    """엑셀 주문서 한 장 (직접 그림: 초록 머리줄 + 표)"""
    key = ('SHEET', w, h)
    if key in _REG: return key
    S = 2; pad = 26
    im = Image.new('RGBA', ((w + pad * 2) * S, (h + pad * 2) * S), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([(pad + 4) * S, (pad + 10) * S, (pad + w + 4) * S, (pad + h + 10) * S], 16 * S, fill=(0, 0, 0, 90))
    im = Image.alpha_composite(im, Image.fromarray(cv2.GaussianBlur(np.array(sh), (0, 0), 9 * S))); d = ImageDraw.Draw(im)
    x0, y0 = pad * S, pad * S
    d.rounded_rectangle([x0, y0, x0 + w * S, y0 + h * S], 16 * S, fill=(255, 255, 255, 255), outline=NAVY + (255,), width=4 * S)
    d.rounded_rectangle([x0, y0, x0 + w * S, y0 + 62 * S], 16 * S, fill=XGREEN + (255,), outline=NAVY + (255,), width=4 * S)
    d.rectangle([x0 + 2 * S, y0 + 40 * S, x0 + w * S - 2 * S, y0 + 62 * S], fill=XGREEN + (255,))
    f = _font(F_BK, 38 * S); d.text((x0 + 22 * S, y0 + 8 * S), 'X', font=f, fill=(255, 255, 255, 255))
    f2 = _font(F_BK, 30 * S); d.text((x0 + 70 * S, y0 + 13 * S), '주문서', font=f2, fill=(255, 255, 255, 255))
    rows, cols = 5, 4; gy0 = y0 + 62 * S; rh = (h - 62) * S / rows; cw = w * S / cols
    for r in range(1, rows): d.line([x0 + 2 * S, gy0 + r * rh, x0 + w * S - 2 * S, gy0 + r * rh], fill=(205, 212, 208, 255), width=2 * S)
    for c in range(1, cols): d.line([x0 + c * cw, gy0, x0 + c * cw, y0 + h * S - 2 * S], fill=(205, 212, 208, 255), width=2 * S)
    rng = np.random.default_rng(4)
    for r in range(rows):
        for c in range(cols):
            ln = cw * rng.uniform(0.35, 0.75)
            d.rounded_rectangle([x0 + c * cw + 12 * S, gy0 + r * rh + rh * 0.36, x0 + c * cw + 12 * S + ln, gy0 + r * rh + rh * 0.64], 5 * S, fill=(196, 203, 212, 255) if r else (150, 190, 168, 255))
    return reg(key, np.array(im.resize((w + pad * 2, h + pad * 2), Image.LANCZOS)))

def won(v):
    return f'{int(round(v)):,}'

def count(t, t0, v, d=1.0):
    """t0 부터 d 초 동안 0 → v 로 올라가는 값 (끝에서 천천히 멈춤)"""
    return v * ease_out(lin(t, t0, t0 + d))

def money_bar(C, x0, y, wmax, vmax, v_lo, v_hi, color, t, t0, d=1.2, h=64, range_color=None):
    """금액 막대. 길이는 금액에 정확히 비례(vmax 가 wmax px). v_lo~v_hi 가 범위면 그 구간은 옅은 색."""
    a = fade(t, t0, 0.3)
    if a <= 0: return x0
    put(C, panel_spr(('MBAR', wmax, h), wmax, h, fill=(232, 228, 222), bw=0, radius=h // 2, shadow=False), x0 + wmax / 2, y, 1.0, a)
    k = draw_on(t, t0 + 0.1, d)
    w_hi = wmax * v_hi / vmax * k; w_lo = wmax * v_lo / vmax * k
    if w_hi > h * 0.6:
        if range_color is not None and v_lo < v_hi:
            put(C, panel_spr(('MB', int(w_hi), h, range_color), int(w_hi), h, fill=range_color, bw=0, radius=h // 2, shadow=False), x0, y, w_hi / max(int(w_hi), 1), a, anchor=(4 / (int(w_hi) + 8), 0.5))
            if w_lo > h * 0.6: put(C, panel_spr(('MB', int(w_lo), h, color), int(w_lo), h, fill=color, bw=0, radius=h // 2, shadow=False), x0, y, 1.0, a, anchor=(4 / (int(w_lo) + 8), 0.5))
        else:
            put(C, panel_spr(('MB', int(w_hi), h, color), int(w_hi), h, fill=color, bw=0, radius=h // 2, shadow=False), x0, y, 1.0, a, anchor=(4 / (int(w_hi) + 8), 0.5))
    return x0 + w_hi
