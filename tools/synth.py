"""코드로 만드는 간단한 배경 음악 (저작권 걱정 없는 임시 음원).  from synth import bed;  bed(20) → int16 24kHz

부드러운 화음 패드 + 통통 튀는 아르페지오 + 약한 킥. 사람 귀로 고른 음원이 있으면 그것을 쓰는 편이 좋다.
"""
import numpy as np
RATE = 24000

def _lp(x, k):                      # 간단한 저역 통과 (이동 평균 두 번)
    w = np.ones(k) / k
    return np.convolve(np.convolve(x, w, 'same'), w, 'same')

def bed(seconds, bpm=96, root=57, prog=((0, 4, 7, 11), (-4, 0, 3, 7), (-7, -3, 0, 4), (-2, 2, 5, 9)), kick=True, seed=3):
    n = int(seconds * RATE); t = np.arange(n) / RATE; beat = 60 / bpm; bar = beat * 4
    f = lambda m: 440 * 2 ** ((m - 69) / 12); out = np.zeros(n); rng = np.random.default_rng(seed)
    for b in range(int(seconds / bar) + 1):
        ch = prog[b % len(prog)]; a, z = int(b * bar * RATE), min(n, int((b + 1) * bar * RATE))
        if a >= n: break
        tt = t[a:z] - b * bar; env = np.minimum(1, tt / .5) * np.minimum(1, (bar - tt) / .6).clip(0, 1)
        pad = sum(np.sin(2 * np.pi * f(root + s + d) * tt + ph) for s in ch for d, ph in ((0, 0), (.07, 1.3), (-12, .4)))
        out[a:z] += .05 * pad * env
        out[a:z] += .16 * np.sin(2 * np.pi * f(root + ch[0] - 24) * tt) * env                       # 베이스
        for k in range(8):                                                                           # 아르페지오 (8분음표)
            s0 = a + int(k * beat / 2 * RATE); s1 = min(n, s0 + int(.32 * RATE))
            if s0 >= n: break
            u = np.arange(s1 - s0) / RATE; note = root + ch[(k * 3) % len(ch)] + (12 if k % 4 == 2 else 0)
            out[s0:s1] += .11 * np.sin(2 * np.pi * f(note) * u) * np.exp(-u * 9) * (1 + .5 * np.sin(2 * np.pi * f(note) * 2 * u))
        if kick:
            for k in range(4):
                s0 = a + int(k * beat * RATE); s1 = min(n, s0 + int(.22 * RATE))
                if s0 >= n: break
                u = np.arange(s1 - s0) / RATE; out[s0:s1] += .5 * np.sin(2 * np.pi * (48 * u + 60 * (1 - np.exp(-u * 30)) / 30)) * np.exp(-u * 16)
                h0 = s0 + int(beat / 2 * RATE); h1 = min(n, h0 + int(.05 * RATE))
                if h0 < n: out[h0:h1] += .05 * rng.standard_normal(h1 - h0) * np.exp(-np.arange(h1 - h0) / RATE * 80)
    out = _lp(out, 5); fade = np.minimum(1, t / 1.2) * np.minimum(1, (seconds - t) / 2.0).clip(0, 1)
    out *= fade; out *= .6 / max(1e-6, np.abs(out).max())
    return (out * 32767).astype(np.int16)

def save(path, a):
    import wave
    with wave.open(path, 'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(a.tobytes())
