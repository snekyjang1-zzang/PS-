# Discord-like chat panel generator (reference-style parody UI)
from common import *
from mg import _REG, _font

BG = (49, 51, 56); HDR = (43, 45, 49); INPUT = (56, 58, 64); TXT = (219, 222, 225); MUTED = (148, 155, 164)

def _avatar_img(src, size, focus=(0.5, 0.4), zoom=1.0):
    key = circle_crop(f'av_{src}_{size}', src, size, ring_col=BG, ring_w=1, focus=focus, zoom=zoom)
    return Image.fromarray(_REG[key])

def chat_panel(key, w, h, title, msgs, typing=None, typing_fail=False, typing_avatar=None):
    """msgs: list of (avatar_src, name, name_color, time, text, text_color or None, fail)"""
    if key in _REG: return key
    S = 1
    im = Image.new('RGBA', (w, h), BG + (255,))
    d = ImageDraw.Draw(im)
    fb = _font(F_SANS, 36); fr = _font(F_SANSR, 40); fs = _font(F_SANSR, 24); fh = _font(F_SANS, 36)
    d.rectangle([0, 0, w, 78], fill=HDR + (255,))
    d.text((28, 18), '#', font=_font(F_SANS, 36), fill=MUTED + (255,))
    d.text((64, 20), title, font=fh, fill=(242, 243, 245, 255))
    d.line([0, 78, w, 78], fill=(30, 31, 34, 255), width=2)
    y = 110
    for (av, name, ncol, tm, text, tcol, fail) in msgs:
        a = _avatar_img(av, 84)
        im.alpha_composite(a, (24, y))
        d.text((128, y + 2), name, font=fb, fill=tuple(ncol) + (255,))
        nw = d.textbbox((0, 0), name, font=fb)[2]
        d.text((128 + nw + 14, y + 12), tm, font=fs, fill=MUTED + (255,))
        d.text((128, y + 48), text, font=fr, fill=tuple(tcol or TXT) + (255,))
        if fail:
            tw = d.textbbox((0, 0), text, font=fr)[2]
            cx, cy = 128 + tw + 36, y + 72
            d.ellipse([cx - 17, cy - 17, cx + 17, cy + 17], fill=(237, 66, 69, 255))
            d.text((cx - 5, cy - 20), '!', font=_font(F_SANS, 28), fill=(255, 255, 255, 255))
            d.text((128, y + 104), '메시지를 보내지 못했습니다', font=fs, fill=(237, 66, 69, 255))
            y += 34
        y += 150
    # input box
    d.rounded_rectangle([20, h - 96, w - 20, h - 22], 14, fill=INPUT + (255,))
    if typing:
        d.text((44, h - 80), typing, font=fr, fill=TXT + (255,))
        tw = d.textbbox((0, 0), typing, font=fr)[2]
        d.line([46 + tw, h - 78, 46 + tw, h - 40], fill=TXT + (255,), width=2)
    else:
        d.text((44, h - 80), '메시지 보내기', font=fr, fill=MUTED + (160,))
    # rounded mask + shadow
    m = Image.new('L', (w * 2, h * 2), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], 36, fill=255)
    im.putalpha(Image.fromarray(np.minimum(np.array(im)[..., 3], np.array(m.resize((w, h), Image.LANCZOS)))))
    pad = 30
    out = Image.new('RGBA', (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new('RGBA', out.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([pad + 8, pad + 14, pad + w + 8, pad + h + 14], 18, fill=(0, 0, 0, 140))
    sh = Image.fromarray(cv2.GaussianBlur(np.array(sh), (0, 0), 12))
    out = Image.alpha_composite(out, sh); out.alpha_composite(im, (pad, pad))
    return reg(key, np.array(out))
