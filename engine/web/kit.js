/* HTML 장면 공용 스크립트. 장면 파일은 이렇게 시작한다:
     <meta name="cues" content="3-5">
     <link rel="stylesheet" href="../../../engine/web/kit.css">
     ... <script src="_timing.js"></script><script src="../../../engine/web/kit.js"></script>
   모든 움직임은 "자막 번호:낱말" 로 시각을 잡는다 → 내레이션을 다시 만들어도 화면이 그대로 따라온다.
     data-at="6"            6번 자막이 시작될 때          data-at="6:골라내고"   6번 자막에서 그 낱말을 말할 때
     data-at="+1.2"         장면 시작 1.2초 뒤            data-off="-0.15"       거기서 0.15초 앞당기기
     data-until="8"         8번 자막이 시작될 때 사라진다 (.out 과 함께)
*/
(() => {
  const T = window.TIMING, meta = document.querySelector('meta[name=cues]').content.split('-').map(Number);
  const A = meta[0], B = meta[1] || meta[0], C = n => T.cues[n];
  const start = n => (n === T.first ? 0 : Math.max(0, C(n).t0 - T.lead));
  const t0 = start(A), tEnd = C(B + 1) ? start(B + 1) : C(B).t1 + 1.2, len = tEnd - t0;
  const clean = w => w.replace(/[,.!?…]+$/g, '');
  const word = (n, sub, occ = 0) => { const ws = C(n).words.filter(w => w.w.includes(sub)); if (!ws.length) throw new Error(`자막 ${n}번에 '${sub}' 가 없습니다: ${C(n).text}`); return ws[Math.min(occ, ws.length - 1)]; };
  // "6" | "6:낱말" | "+1.2" | "end" → 장면 기준 초
  const when = (spec, off = 0) => {
    spec = String(spec).trim(); let t;
    if (spec[0] === '+') t = parseFloat(spec.slice(1));
    else if (spec.startsWith('end')) t = len + (parseFloat(spec.slice(3)) || 0);
    else if (spec.startsWith('clip')) { const c = T.clips.find(c => c.name === spec.split(':')[1]); if (!c) throw new Error('대본에 [영상: ' + spec.split(':')[1] + '] 이 없습니다'); t = c.at - t0 + (spec.startsWith('clipend') ? c.dur : 0); }
    else { const [n, sub] = spec.split(':'); t = (sub ? word(+n, sub).t0 : C(+n).t0) - t0; }
    return t + off;
  };
  const set = (el, k, v) => el.style.setProperty(k, typeof v === 'number' ? v.toFixed(3) + 's' : v);
  const root = document.documentElement; set(root, '--len', len); set(root, '--exit', len - .26);

  // 배경 층 (분홍 안개 · 바닥 격자 · 어둡게 · 입자). <body data-bg="none"> 이면 넣지 않는다
  const stage = document.querySelector('.stage');
  if (stage && document.body.dataset.bg !== 'none') {
    stage.insertAdjacentHTML('afterbegin', '<div class="haze a"></div><div class="haze b"></div>' + (document.body.dataset.floor === 'off' ? '' : '<div class="floor"></div>'));
    stage.insertAdjacentHTML('beforeend', '<div class="vig"></div><svg class="grain" width="1920" height="1080"><filter id="kn"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="7"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .9 0"/></filter><rect width="100%" height="100%" filter="url(#kn)"/></svg>');
  }

  // 시각 지정
  document.querySelectorAll('[data-at]').forEach(el => set(el, '--t', when(el.dataset.at, +(el.dataset.off || 0))));
  document.querySelectorAll('[data-until]').forEach(el => { set(el, '--u', when(el.dataset.until, +(el.dataset.uoff || -.2))); el.classList.add('out'); });
  document.querySelectorAll('[data-dur-to]').forEach(el => set(el, '--dur', Math.max(.2, when(el.dataset.durTo) - when(el.dataset.at, +(el.dataset.off || 0)))));
  document.querySelectorAll('[data-stagger]').forEach(g => { const st = +g.dataset.stagger, base = g.dataset.at ? when(g.dataset.at, +(g.dataset.off || 0)) : 0;
    [...g.children].forEach((c, i) => { if (!c.dataset.at) set(c, '--t', base + i * st); }); });

  // 큰 자막: <div class="cap" data-cue="6" data-hl="골라내고"> — 낱말이 말하는 순간 하나씩 떠오른다
  const covered = new Set();
  const fill = (el, n, hl, from, to) => C(n).words.forEach((x, k) => { if (k < from || k > to) return;
    const w = clean(x.w), key = hl.find(h => h && w.includes(h)), s = document.createElement('span'); s.className = 'w' + (key ? ' hl' : '');
    set(s, '--d', x.t0 - t0 - .06); s.innerHTML = key ? w.replace(key, `<i>${key}</i>`) : w; el.appendChild(s); });
  document.querySelectorAll('.cap[data-cue]').forEach(el => { const n = +el.dataset.cue; covered.add(n);
    fill(el, n, (el.dataset.hl || '').split(','), +(el.dataset.from || 0), +(el.dataset.to || 99));
    if (!el.dataset.keep && !el.dataset.until && C(n + 1) && n < B) { set(el, '--u', C(n + 1).t0 - t0 - .2); el.classList.add('out'); } });
  // 아래 작은 자막: 큰 자막이 맡지 않은 자막은 자동으로 띄운다. <body data-sub="off"> 로 끈다
  if (stage && document.body.dataset.sub !== 'off') { const skip = (document.body.dataset.nosub || '').split(',').map(Number);
    for (let n = A; n <= B; n++) { if (covered.has(n) || skip.includes(n)) continue;
      const el = document.createElement('div'); el.className = 'cap sub'; fill(el, n, (document.body.dataset.hl || '').split(','), 0, 99);
      if (C(n + 1) && n < B) { set(el, '--u', C(n + 1).t0 - t0 - .16); el.classList.add('out'); } stage.appendChild(el); } }

  // 숫자 올리기 · 타자 치기처럼 CSS 로 못 하는 것은 프레임마다 직접 그린다
  const ease = x => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);
  const nums = [...document.querySelectorAll('.num[data-to]')].map(el => ({ el, at: when(el.dataset.at || '+0', +(el.dataset.off || 0)), to: +el.dataset.to, from: +(el.dataset.from || 0), dur: +(el.dataset.dur || .9), fmt: el.dataset.fmt }));
  const types = [...document.querySelectorAll('.type')].map(el => ({ el, text: el.textContent, at: when(el.dataset.at || '+0', +(el.dataset.off || 0)), cps: +(el.dataset.cps || 22) }));
  types.forEach(x => x.el.textContent = '');
  const hooks = [];
  // 영상 넣기: <img class="vid" data-video="녹화이름" data-at="clip:녹화이름" data-start="0"> — 렌더할 때 프레임을 하나씩 받아 그린다 (소리는 final 이 섞는다)
  const vids = [...document.querySelectorAll('img.vid[data-video]')].map((el, i) => ({ el, i, name: el.dataset.video, at: when(el.dataset.at || '+0', +(el.dataset.off || 0)), start: +(el.dataset.start || 0), rate: +(el.dataset.rate || 1), w: +(el.dataset.w || 1280), h: +(el.dataset.h || 720) }));
  window.KIT = { ready: true, t0, len, at: when, word, cue: C, onFrame: f => hooks.push(f), ease,
    videos: t => vids.map(v => ({ i: v.i, name: v.name, time: v.start + Math.max(0, t - v.at) * v.rate, w: v.w, h: v.h })),
    setFrame: (i, url) => { vids[i].el.src = url; return vids[i].el.decode().catch(() => 0); },
    frame(t) {
      nums.forEach(x => { const v = x.from + (x.to - x.from) * ease((t - x.at) / x.dur); x.el.textContent = x.fmt === 'comma' ? Math.round(v).toLocaleString('en-US') : Math.round(v); });
      types.forEach(x => { const n = Math.max(0, Math.floor((t - x.at) * x.cps)); x.el.textContent = x.text.slice(0, n); x.el.classList.toggle('typing', n > 0 && n < x.text.length); });
      hooks.forEach(f => f(t));
    } };
  // 브라우저로 직접 열어 볼 때: 실제 시간으로 재생
  if (!navigator.webdriver) { const z = performance.now(); const loop = () => { KIT.frame((performance.now() - z) / 1000); requestAnimationFrame(loop); }; loop(); }
})();
