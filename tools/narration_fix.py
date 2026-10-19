"""합성한 내레이션 다듬기: 긴 쉼 줄이기 + 튀는 순간 누르기 + 전체 속도.   python tools/narration_fix.py <프로젝트 폴더> [--gap 0.30] [--para 0.68] [--tempo 1.08]

일레븐랩스 음성은 문장 사이 쉼이 길다(전체의 25% 안팎). `mgp tts` 가 만든 input/narration.wav · narration.srt · words.json 을 그 자리에서 고친다.
- 쉼: 문단 사이는 --para 초, 그 밖의 쉼(문장 사이·쉼표 뒤)은 --gap 초까지만 남기고 가운데를 잘라 낸다. 자막·낱말 시각도 같이 당긴다.
- 튀는 순간: 파열음이 지나치게 세게 들어간 곳 앞뒤 60ms 를 살짝 누른다.
- 속도: --tempo 배(음높이 유지).
원본은 input/_raw/ 에 보관하고 항상 원본에서 다시 만든다(여러 번 실행해도 같은 결과). `mgp tts` 를 다시 돌렸으면 새 결과를 원본으로 삼는다.
[영상: 이름] 구간(input/clips.json)이 있는 프로젝트에는 아직 쓰지 않는다(그 시각은 옮기지 않는다).
"""
import os, sys, json, shutil, argparse
import numpy as np
KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KIT, 'tools')); sys.path.insert(0, os.path.join(KIT, 'engine'))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('proj'); ap.add_argument('--gap', type=float, default=0.30); ap.add_argument('--para', type=float, default=0.68)
    ap.add_argument('--tempo', type=float, default=1.0); ap.add_argument('--min_sil', type=float, default=0.07); a = ap.parse_args()
    os.environ.setdefault('MG_PROJECT', os.path.abspath(a.proj))
    import tts as T
    R = T.RATE; inp = os.path.join(a.proj, 'input'); raw = os.path.join(inp, '_raw'); os.makedirs(raw, exist_ok=True)
    cur = os.path.join(inp, 'narration.wav'); mark = os.path.join(raw, 'fixed.json'); st = os.stat(cur)
    done = json.load(open(mark)) if os.path.exists(mark) else {}
    if not (done.get('size') == st.st_size and abs(done.get('mtime', 0) - st.st_mtime) < 1):          # tts 를 새로 돌린 뒤: 지금 것을 원본으로
        for f in ('narration.wav', 'narration.srt', 'words.json'):
            if os.path.exists(os.path.join(inp, f)): shutil.copy2(os.path.join(inp, f), os.path.join(raw, f))
    cj = os.path.join(inp, 'clips.json')
    if os.path.exists(cj) and json.load(open(cj, encoding='utf-8')): raise SystemExit('이 프로젝트에는 [영상] 구간이 있습니다. narration_fix 는 아직 그 시각을 옮기지 못합니다.')
    x = T._load_wav(os.path.join(raw, 'narration.wav')).astype(np.float32); n = len(x)
    cues = []
    for b in open(os.path.join(raw, 'narration.srt'), encoding='utf-8').read().strip().split('\n\n'):
        _, tm, txt = b.split('\n', 2); s0, s1 = [(lambda h, m, s: int(h) * 3600 + int(m) * 60 + float(s.replace(',', '.')))(*t.strip().split(':')) for t in tm.split('-->')]; cues.append([s0, s1, txt])
    # 문단이 시작되는 자막 번호 → 그 앞의 쉼은 문단 간격으로 남긴다
    paras = T.read_script(os.path.join(inp, 'script.txt')); starts = set(); k = 0
    for sents in paras:
        starts.add(k); k += sum(len(T.split_sub(s, 30)) for s in sents)
    para_t = [cues[i][0] for i in sorted(starts) if 0 < i < len(cues)] if k == len(cues) else []
    # 튀는 순간 누르기
    d = np.abs(np.diff(x)); spots = []
    for i in np.where(d > 16000)[0]:
        if not spots or i - spots[-1] > R * 0.15: spots.append(int(i))
    env = np.ones(n, np.float32); w = int(R * 0.06)
    for i in spots:
        i0, i1 = max(0, i - w), min(n, i + w); env[i0:i1] = np.minimum(env[i0:i1], 1 - 0.58 * np.hanning(i1 - i0).astype(np.float32))
    x *= env
    # 긴 쉼 자르기
    sil = T.silences(x.astype(np.int16), a.min_sil); cuts = []                                          # (자르기 시작, 끝)
    for g0, g1 in sil:
        cap = a.para if any(g0 - 0.05 <= t <= g1 + 0.25 for t in para_t) else a.gap
        if g1 - g0 > cap + 0.02: m = (g0 + g1) / 2; h = (g1 - g0 - cap) / 2; cuts.append((m - h, m + h))
    keep = []; pos = 0
    for c0, c1 in cuts: keep.append(x[pos:int(c0 * R)]); pos = int(c1 * R)
    keep.append(x[pos:]); y = np.concatenate(keep)
    cs = np.array([c[0] for c in cuts]); ce = np.array([c[1] for c in cuts]); cum = np.concatenate([[0], np.cumsum(ce - cs)])
    def tm(t):
        j = int(np.searchsorted(ce, t, side='right')); t2 = t - cum[j]
        if j < len(cs) and t > cs[j]: t2 = cs[j] - cum[j]                                              # 잘린 구간 안의 시각은 그 시작으로
        return float(t2) / a.tempo
    if abs(a.tempo - 1) > 1e-3: y = T._tempo(y.clip(-32767, 32767).astype(np.int16), a.tempo).astype(np.float32)
    T._save_wav(cur, y.clip(-32767, 32767).astype(np.int16))
    out = [(tm(s0), max(tm(s1), tm(s0) + 0.2), txt) for s0, s1, txt in cues]
    out = [(s0, min(s1, out[i + 1][0]) if i + 1 < len(out) else s1, txt) for i, (s0, s1, txt) in enumerate(out)]
    open(os.path.join(inp, 'narration.srt'), 'w', encoding='utf-8').write('\n\n'.join(f'{i + 1}\n{T._ts(s0)} --> {T._ts(s1)}\n{txt}' for i, (s0, s1, txt) in enumerate(out)) + '\n')
    wp = os.path.join(raw, 'words.json')
    if os.path.exists(wp):
        ws = json.load(open(wp, encoding='utf-8'))
        json.dump([[{'w': q['w'], 't0': round(tm(q['t0']), 3), 't1': round(tm(q['t1']), 3)} for q in row] for row in ws], open(os.path.join(inp, 'words.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    st = os.stat(cur); json.dump({'size': st.st_size, 'mtime': st.st_mtime, 'gap': a.gap, 'para': a.para, 'tempo': a.tempo}, open(mark, 'w'))
    d0, d1 = n / R, len(y) / R
    print(f'내레이션 {int(d0 // 60)}분 {d0 % 60:.1f}초 → {int(d1 // 60)}분 {d1 % 60:.1f}초 | 줄인 쉼 {len(cuts)}곳 ({sum(c1 - c0 for c0, c1 in cuts):.0f}초) | 문단 경계 {len(para_t)}곳 | 누른 곳 {len(spots)}곳 | 속도 {a.tempo}배 | 자막 {len(out)}개')

if __name__ == '__main__': main()
