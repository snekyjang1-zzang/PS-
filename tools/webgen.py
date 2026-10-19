"""HTML 장면을 파이썬에서 짧게 찍어 내는 도우미 (장면이 많을 때).  from webgen import *

    page(folder, 's15', '29-30', body, style='', attrs='', pre='')     → folder/s15.html
"""
import os

B = '../../../brand/'
SPARK = '<svg class="%s" %s viewBox="-50 -50 100 100"><g stroke="%s" stroke-width="9" stroke-linecap="round"><path d="M0-44V44M-44 0H44M-31-31L31 31M-31 31L31-31M-17-41L17 41M-41-17L41 17M-41 17L41-17M-17 41L17-41"/></g></svg>'
CUR = '<svg width="44" height="50" viewBox="0 0 44 50"><path d="M4 3 L4 40 L14 31 L21 47 L28 44 L21 28 L35 28 Z" fill="#fff" stroke="#16081a" stroke-width="3" stroke-linejoin="round"/></svg>'
# 선으로 그린 작은 그림 (viewBox 0 0 48 48, stroke = currentColor)
_I = {
 'wave': '<path d="M4 24h4M12 14v20M18 8v32M24 16v16M30 6v36M36 18v12M40 24h4"/>', 'text': '<path d="M8 12h32M8 22h32M8 32h20"/>',
 'frame': '<rect x="6" y="10" width="36" height="28" rx="4"/><path d="M6 30l10-9 8 7 6-5 12 9"/>', 'cut': '<circle cx="12" cy="34" r="5"/><circle cx="12" cy="14" r="5"/><path d="M16 17l26 17M16 31l26-17"/>',
 'eye': '<path d="M4 24s8-13 20-13 20 13 20 13-8 13-20 13S4 24 4 24z"/><circle cx="24" cy="24" r="6"/>', 'ear': '<path d="M14 20a10 10 0 0 1 20 0c0 8-8 8-8 16a6 6 0 0 1-11 3M20 20a4 4 0 0 1 8 0"/>',
 'clock': '<circle cx="24" cy="24" r="18"/><path d="M24 12v12l8 6"/>', 'vol': '<path d="M6 19v10h8l10 8V11L14 19zM31 17a10 10 0 0 1 0 14M36 11a18 18 0 0 1 0 26"/>',
 'cam': '<rect x="5" y="14" width="26" height="22" rx="4"/><path d="M31 22l12-6v18l-12-6z"/>', 'code': '<path d="M17 14L6 24l11 10M31 14l11 10-11 10M27 8l-6 32"/>',
 'play': '<circle cx="24" cy="24" r="19"/><path d="M20 15l14 9-14 9z" fill="currentColor"/>', 'down': '<path d="M24 6v26M12 22l12 12 12-12M8 42h32"/>',
 'web': '<circle cx="24" cy="24" r="19"/><path d="M5 24h38M24 5c-9 10-9 28 0 38M24 5c9 10 9 28 0 38"/>', 'mouse': '<path d="M10 6l8 34 6-13 13-6z"/>',
 'note': '<path d="M18 36V10l20-4v26"/><circle cx="13" cy="36" r="5"/><circle cx="33" cy="32" r="5"/>', 'app': '<rect x="5" y="8" width="38" height="32" rx="5"/><path d="M5 17h38M11 12.5h.1M16 12.5h.1"/>',
 'laptop': '<rect x="9" y="10" width="30" height="20" rx="3"/><path d="M3 37h42l-4-7H7z"/>', 'x': '<path d="M10 10l28 28M38 10L10 38"/>', 'ok': '<path d="M8 25l11 11 21-24"/>',
 'layers': '<path d="M24 6l19 10-19 10L5 16zM5 25l19 10 19-10M5 33l19 10 19-10"/>', 'spark': '<path d="M24 4v40M4 24h40M10 10l28 28M38 10L10 38"/>', 'bolt': '<path d="M27 4L9 27h13l-3 17 19-24H25z"/>',
}
def ico(name, size=64, color='currentColor', cls='', extra=''):
    return f'<svg class="ico {cls}" {extra} width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" stroke="{color}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">{_I[name]}</svg>'

def page(folder, name, cues, body, style='', attrs='', pre='', theme=True):
    html = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n<meta name="cues" content="%s">\n<link rel="stylesheet" href="../../../engine/web/kit.css">\n%s<style>\n%s\n</style>\n</head>\n<body %s>\n<div class="stage">\n%s\n</div>\n'
            '<script src="_timing.js"></script>\n%s<script src="../../../engine/web/kit.js"></script>\n</body>\n</html>\n') % (
            cues, '<link rel="stylesheet" href="_theme.css">\n' if theme else '', style.strip(), attrs, body.strip(), pre)
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, name + '.html'), 'w', encoding='utf-8').write(html)

def host(pose, left, height, at='+0.05', extra=''):
    """진행자(마스코트) 그림."""
    return f'<img class="host" data-at="{at}" src="{B}crow_{pose}.png" style="left:{left}px; height:{height}px; {extra}">'

def pip(pose='idle'):
    return f'<div class="pip shotA pop" data-at="+0.3"><img src="{B}crow_{pose}.png"></div>'
