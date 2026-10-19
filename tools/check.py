"""렌더 전에 장면을 그려 보고 한 장으로 모은다.   python mgp.py check <프로젝트> [장면 ...]

- 모든 장면(또는 지정한 장면)을 실제로 그려 보고 오류가 나는 장면과 줄 번호를 알려 준다.
- seq(...) 로 컷을 나눈 장면은 컷마다 끝나기 직전의 프레임을, 그렇지 않은 장면은 네 시점의 프레임을 뽑아
  out/_check_1.jpg, _check_2.jpg ... 로 저장한다. Claude 가 이 그림을 열어 겹침·잘림·빈 화면·자막 가림을 확인한다.
"""
import os, traceback
import numpy as np, cv2
from PIL import Image, ImageDraw

def run(proj, names=None, per_sheet=48, tw=480):
    import timeline as tl
    th = tw * 9 // 16; tiles = []; bad = []
    for s in tl.scenes():
        if names and s['name'] not in names: continue
        try:
            mod = tl.load(s); n = s['f1'] - s['f0']; dur = n / tl.FPS; starts = []
            orig = getattr(mod, 'seq', None)
            if orig is not None:
                def spy(C, t, items, xf=0.25, _st=starts, _o=orig):
                    if not _st: _st.extend([it[0] for it in items])
                    return _o(C, t, items, xf)
                mod.seq = spy
            tl.frame(s, mod, s['f0'])
            if starts: pts = [max(0.0, b - 0.12) for b in starts[1:] + [dur]]; labs = ['%s c%d' % (s['name'], i + 1) for i in range(len(pts))]
            else: pts = [dur * f for f in (0.12, 0.4, 0.68, 0.97)]; labs = ['%s %.1fs' % (s['name'], p) for p in pts]
            for p, lab in zip(pts, labs):
                im = np.asarray(tl.frame(s, mod, s['f0'] + min(n - 1, max(0, int(p * tl.FPS)))))
                im = im if im.dtype == np.uint8 else np.clip(im, 0, 255).astype(np.uint8)
                pil = Image.fromarray(cv2.resize(im, (tw, th), interpolation=cv2.INTER_AREA)); d = ImageDraw.Draw(pil)
                d.rectangle([0, 0, 8 + 7 * len(lab), 16], fill=(0, 0, 0)); d.text((3, 3), lab, fill=(0, 255, 255)); tiles.append(pil)
        except BaseException as e:
            tb = [x for x in traceback.extract_tb(e.__traceback__) if os.sep + 'scenes' + os.sep in x.filename]
            bad.append(f"{s['name']}: {type(e).__name__} {str(e)[:160]}" + (f"  ({os.path.basename(tb[-1].filename)} {tb[-1].lineno}번째 줄)" if tb else ''))
    out = []; cols = 6
    for k in range(0, len(tiles), per_sheet):
        part = tiles[k:k + per_sheet]; rows = (len(part) + cols - 1) // cols; im = Image.new('RGB', (cols * tw, rows * th))
        for i, t in enumerate(part): im.paste(t, (tw * (i % cols), th * (i // cols)))
        fp = os.path.join(proj, 'out', '_check_%d.jpg' % (k // per_sheet + 1)); os.makedirs(os.path.dirname(fp), exist_ok=True); im.save(fp, quality=85); out.append(fp)
    return out, bad, len(tiles)
