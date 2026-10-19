"""문장별로 합성한 음성의 목소리가 서로 같은지 검사한다.

Gemini TTS 는 호출마다 음색·높낮이·속도가 조금씩 달라질 수 있고, 드물게 전혀 다른 사람처럼 들리는
문장이 나온다. 문장별 음성에서 목소리 높이(F0), 음색(MFCC 평균), 말 속도를 재어 전체 중앙값과 비교하고,
벗어난 문장을 골라낸다. tts.run 이 이 결과를 보고 벗어난 문장만 다시 합성한다.
"""
import numpy as np

RATE = 24000
LIMITS = {'pitch': 1.6, 'timbre': 3.2, 'rate': 0.24}   # 반음 차이 / 음색 거리(중앙값 대비 배수) / 속도 비율 차이

def _frames(a, win, hop):
    n = 1 + max(0, (len(a) - win) // hop)
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    return a[idx]

def pitch(a):
    """유성음 구간의 F0 중앙값(Hz). 자기상관으로 잰다. 재지 못하면 None."""
    x = a.astype(np.float32); x = x - x.mean()
    win, hop = int(RATE * 0.04), int(RATE * 0.01)
    if len(x) < win * 2: return None
    F = _frames(x, win, hop) * np.hanning(win)
    e = np.sqrt((F ** 2).mean(1)); thr = max(120.0, float(np.percentile(e, 85)) * 0.25)
    lo, hi = int(RATE / 320), int(RATE / 65); out = []
    for f in F[e > thr]:
        s = np.fft.rfft(f, 2 * win); ac = np.fft.irfft(s * np.conj(s))[:hi + 1]
        if ac[0] <= 0: continue
        k = lo + int(np.argmax(ac[lo:hi + 1]))
        if ac[k] / ac[0] > 0.45: out.append(RATE / k)
    return float(np.median(out)) if len(out) >= 6 else None

def _mel_fb(nfft, nmel=26, fmin=80, fmax=7600):
    mel = lambda f: 2595 * np.log10(1 + f / 700.0); inv = lambda m: 700 * (10 ** (m / 2595.0) - 1)
    pts = inv(np.linspace(mel(fmin), mel(fmax), nmel + 2)); bins = np.floor((nfft + 1) * pts / RATE).astype(int)
    fb = np.zeros((nmel, nfft // 2 + 1), np.float32)
    for i in range(nmel):
        a, b, c = bins[i], bins[i + 1], bins[i + 2]
        if b > a: fb[i, a:b] = (np.arange(a, b) - a) / (b - a)
        if c > b: fb[i, b:c] = (c - np.arange(b, c)) / (c - b)
    return fb

_FB = None
def timbre(a):
    """음색 벡터: 소리가 나는 구간의 MFCC(2~13번) 평균. 성도 모양(=누구 목소리인지)을 대략 반영한다."""
    global _FB
    x = a.astype(np.float32); x = np.append(x[0], x[1:] - 0.97 * x[:-1])
    win, hop, nfft = int(RATE * 0.025), int(RATE * 0.01), 1024
    if len(x) < win * 4: return None
    F = _frames(x, win, hop) * np.hamming(win)
    e = np.sqrt((F ** 2).mean(1)); F = F[e > max(60.0, float(np.percentile(e, 85)) * 0.2)]
    if len(F) < 8: return None
    if _FB is None: _FB = _mel_fb(nfft)
    P = np.abs(np.fft.rfft(F, nfft)) ** 2
    M = np.log(P @ _FB.T + 1e-6)
    n = M.shape[1]; k = np.arange(1, 14)[:, None]; dct = np.cos(np.pi * k * (np.arange(n)[None, :] + 0.5) / n)
    return (M @ dct.T)[:, 1:].mean(0)

def measure(clips, texts, weight):
    """clips: [int16 배열], texts: [문장]. 문장별 {'f0', 'mfcc', 'rate', 'dur'}"""
    out = []
    for a, t in zip(clips, texts):
        d = len(a) / RATE
        out.append({'f0': pitch(a), 'mfcc': timbre(a), 'rate': weight(t) / max(d, 0.2), 'dur': d, 'syl': weight(t)})
    return out

def judge(ms, limits=None):
    """전체 중앙값에서 벗어난 문장 찾기. 반환: [(번호, [이유...])], 요약 dict"""
    lim = dict(LIMITS); lim.update(limits or {})
    f0s = np.array([m['f0'] for m in ms if m['f0']]); f0_med = float(np.median(f0s)) if len(f0s) else None
    long_ = [m for m in ms if m['syl'] >= 8]
    rate_med = float(np.median([m['rate'] for m in (long_ or ms)]))
    vec = np.array([m['mfcc'] for m in ms if m['mfcc'] is not None and m['dur'] >= 1.2])
    bad, dists = [], {}
    if len(vec) >= 8:
        mu = np.median(vec, 0); sd = vec.std(0) + 1e-6
        dall = np.sqrt((((vec - mu) / sd) ** 2).mean(1)); d_med = float(np.median(dall))
    else: mu = sd = None; d_med = 1.0
    for i, m in enumerate(ms):
        why = []
        if f0_med and m['f0']:
            st = 12 * np.log2(m['f0'] / f0_med); m['st'] = float(st)
            if abs(st) > lim['pitch']: why.append(f"높이 {st:+.1f}반음")
        if mu is not None and m['mfcc'] is not None and m['dur'] >= 1.2:
            d = float(np.sqrt((((m['mfcc'] - mu) / sd) ** 2).mean())) / d_med; m['td'] = d
            if d > lim['timbre']: why.append(f"음색 {d:.1f}배")
        if m['syl'] >= 8:
            r = m['rate'] / rate_med - 1; m['rd'] = float(r)
            if abs(r) > lim['rate']: why.append(f"속도 {r * 100:+.0f}%")
        if why: bad.append((i, why))
    return bad, {'f0': f0_med, 'rate': rate_med}
