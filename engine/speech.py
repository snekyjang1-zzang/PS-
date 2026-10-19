"""글자가 아니라 '읽는 길이'로 시각을 추정하기 위한 도구 (tts.py 와 엔진의 wt() 가 함께 쓴다).
숫자는 읽는 음절 수로 센다: 1,000 → 천(1), 3,300 → 삼천삼백(4), 2012 → 이천십이(4)."""
import re

_NUM = re.compile(r'\d[\d,]*(?:\.\d+)?')

def _int_syll(s):
    n = int(s) if s else 0
    if n == 0: return 1
    total, gi = 0, 0
    while n:
        g, n = n % 10000, n // 10000
        if g:
            for pi, dv in enumerate([g // 1000, g // 100 % 10, g // 10 % 10, g % 10]):
                if dv: total += 1 if pi == 3 else (1 if dv == 1 else 2)      # 천·백·십 앞의 1 은 읽지 않는다
            if gi: total += 1                                                # 만, 억, 조
            if gi == 1 and g == 1: total -= 1                                # 일만 → 만
        gi += 1
    return max(total, 1)

def _num_syll(tok):
    tok = tok.replace(',', '')
    if '.' in tok:
        a, b = tok.split('.', 1); return _int_syll(a) + 1 + len(b)
    return _int_syll(tok)

def speak_len(s):
    """읽는 길이 추정(음절 수). 쉼표·마침표는 짧은 쉼으로 1 씩 센다."""
    n, pos = 0.0, 0
    def plain(x): return len(re.sub(r'[^0-9A-Za-z가-힣]', '', x)) + 1.0 * len(re.findall(r'[,，、;:.?!…]', x))
    for m in _NUM.finditer(s):
        n += plain(s[pos:m.start()]) + _num_syll(m.group()); pos = m.end()
    return n + plain(s[pos:])
