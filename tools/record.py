"""웹사이트 시연 장면 녹화: captures/<이름>.py (녹화 대본) → captures/<이름>.mp4 + <이름>.json(표시 시각)

녹화 대본 형식 (templates/capture_template.py 참고)
    def run(page, h):
        h.goto('https://example.com'); h.pause(1)
        h.mark('검색')                      # 이 순간의 영상 시각을 기록 → 장면에서 cap_mark('이름', '검색')
        h.click('text=More information')    # 마우스가 부드럽게 이동한 뒤 클릭
        h.type('#q', '검색어'); h.press('Enter'); h.park(); h.scroll(600); h.shot('result')

선택: VIEWPORT = (2560, 1440), ZOOM = 2.0 (기본). 페이지를 1280x720 크기로 열어 2배 선명도로 찍는다 → 장면에서 줌인해도 글자가 깨끗하다.
      h.focus(선택자, hold=2.5) = '여기를 보세요'. 장면의 screen() 이 그 요소로 줌인하고 테두리로 강조한다. 클릭·입력 대상도 같은 방식으로 강조되고, 스크롤 때는 전체 화면이 된다.

브라우저는 이 프로젝트 전용 프로필(captures/_profile)로 열린다. 평소 쓰는 크롬과 분리되어
북마크·계정이 화면에 찍히지 않는다. 로그인이 필요한 사이트는 `record --login <주소>` 로
담당자가 직접 로그인해 두면 다음 녹화부터 유지된다.
"""
import os, sys, json, time, base64, shutil, subprocess, importlib.util

CURSOR_JS = r"""
(() => {
  if (window.__mgCursor) return; window.__mgCursor = true;
  const make = () => {
    const c = document.createElement('div'); c.id = '__mg_cursor';
    c.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M4 2 L4 20 L9 15.5 L12.5 23 L15.5 21.6 L12 14.3 L19 14.3 Z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    c.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;transform:translate(-100px,-100px);will-change:transform;';
    document.documentElement.appendChild(c);
    const move = e => { c.style.transform = `translate(${e.clientX - 5}px,${e.clientY - 3}px)`; };
    document.addEventListener('mousemove', move, true);
    document.addEventListener('mousedown', e => {
      const r = document.createElement('div');
      r.style.cssText = `position:fixed;left:${e.clientX - 22}px;top:${e.clientY - 22}px;width:44px;height:44px;border-radius:50%;border:4px solid #f0584a;z-index:2147483646;pointer-events:none;opacity:.9;transition:transform .45s ease-out,opacity .45s ease-out;`;
      document.documentElement.appendChild(r);
      requestAnimationFrame(() => { r.style.transform = 'scale(1.9)'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 500);
    }, true);
  };
  if (document.documentElement) make(); else document.addEventListener('DOMContentLoaded', make);
})();
"""

class Helper:
    """녹화 대본에서 쓰는 도구. 대기는 반드시 h.pause() 로 (time.sleep 을 쓰면 그동안 화면이 기록되지 않는다).
    보여 준 대상(focus·click·type)의 위치와 시각을 기록해 둔다 → 장면의 screen() 이 그 대상으로 줌인하고 강조 표시를 한다."""
    def __init__(self, page, rec, shots_dir, dpr=1.0):
        self.page, self._rec, self._shots, self._dpr = page, rec, shots_dir, dpr
        vp = page.viewport_size; self.x, self.y = vp['width'] / 2, vp['height'] / 2
    def _now(self): return round(time.time() - self._rec['t0'], 3)
    def _event(self, kind, t0, t1, box, hl, zoom):
        d = self._dpr
        self._rec['events'].append({'kind': kind, 't0': t0, 't1': t1, 'hl': hl, 'zoom': zoom,
                                    'box': [round(box['x'] * d), round(box['y'] * d), round(box['width'] * d), round(box['height'] * d)]})
    def pause(self, sec=1.0): self.page.wait_for_timeout(int(sec * 1000))
    def mark(self, label): self._rec['marks'][label] = self._now()
    def goto(self, url, wait=1.0):
        self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
        try: self.page.wait_for_load_state('networkidle', timeout=8000)
        except Exception: pass
        self.page.mouse.move(self.x, self.y); self.pause(wait)
    def move(self, x, y, dur=0.7):
        steps = max(2, int(dur * 30)); x0, y0 = self.x, self.y
        for i in range(1, steps + 1):
            k = i / steps; k = k * k * (3 - 2 * k)      # 천천히 출발해서 천천히 멈춤
            self.x, self.y = x0 + (x - x0) * k, y0 + (y - y0) * k
            self.page.mouse.move(self.x, self.y); self.page.wait_for_timeout(int(dur * 1000 / steps))
    def _box(self, sel):
        loc = self.page.locator(sel).first
        loc.scroll_into_view_if_needed(timeout=15000); self.pause(0.3)
        b = loc.bounding_box()
        if not b: raise RuntimeError(f'화면에서 찾을 수 없습니다: {sel}')
        return b
    def _to(self, b, dur, edge=False):
        """대상으로 마우스 이동. edge=True 면 대상 바로 왼쪽 바깥(여백)에 둔다: 글을 가리지 않고, 링크 위에 올라가 미리보기 팝업이 뜨는 일도 없다."""
        if edge: self.move(max(b['x'] - 16, 4), b['y'] + min(b['height'] * 0.5, 60), dur)
        else: self.move(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2, dur)
    def hover(self, sel, dur=0.7): self._to(self._box(sel), dur)
    def focus(self, sel, hold=2.5, zoom=None, dur=0.8):
        """'여기를 보세요': 클릭 없이 그 요소를 hold 초 동안 보여 준다. 장면에서 그 요소로 줌인하고 테두리로 강조한다.
        내레이션이 말하는 바로 그 문단·숫자·버튼을 가리킨다 (제목 전체처럼 넓은 것보다 정확한 대상)."""
        t0 = self._now(); b = self._box(sel); self._to(b, dur, edge=True); t_in = self._now(); self.pause(hold)
        self._event('focus', t0, self._now(), b, [t_in - 0.3, self._now()], zoom)
    def click(self, sel, dur=0.7, after=1.0, zoom=None):
        """대상으로 이동해 클릭. 클릭하는 대상으로 줌인·강조하고, 클릭 뒤에는 전체 화면으로 돌아간다(결과를 보여 주려면 이어서 h.focus)."""
        t0 = self._now(); b = self._box(sel); self._to(b, dur); self.pause(0.25); self.page.mouse.down(); self.pause(0.08); self.page.mouse.up()
        tc = self._now(); self._rec['clicks'].append([tc, round(self.x * self._dpr), round(self.y * self._dpr)])
        self._event('click', t0, tc + 0.2, b, [t0 + dur * 0.6, tc - 0.05], zoom); self.pause(after)
    def type(self, sel, text, delay=90, after=0.6, zoom=None):
        """입력칸을 클릭하고 한 글자씩 입력. 입력하는 동안 그 칸으로 줌인·강조한다."""
        t0 = self._now(); b = self._box(sel); self._to(b, 0.7); self.pause(0.2); self.page.mouse.click(self.x, self.y)
        self._rec['clicks'].append([self._now(), round(self.x * self._dpr), round(self.y * self._dpr)])
        self.pause(0.2); self.page.keyboard.type(text, delay=delay); self.pause(after)
        self._event('type', t0, self._now(), b, [t0 + 0.4, self._now()], zoom)
    def park(self, dur=0.5):
        """마우스를 화면 오른쪽 가장자리로 치운다 (스크롤 중 링크 미리보기 같은 팝업이 뜨지 않게)."""
        vp = self.page.viewport_size; self.move(vp['width'] - 12, vp['height'] * 0.45, dur)
    def press(self, key, after=1.0): self.page.keyboard.press(key); self.pause(after)
    def scroll(self, dy, dur=1.2):
        """부드럽게 스크롤. 스크롤하는 동안은 전체 화면이 보인다."""
        t0 = self._now(); steps = max(2, int(dur * 30))
        for _ in range(steps): self.page.mouse.wheel(0, dy / steps); self.page.wait_for_timeout(int(dur * 1000 / steps))
        self._rec['scrolls'].append([t0, self._now()]); self.pause(0.3)
    def shot(self, name):
        """현재 화면을 정지 이미지로 저장 → assets/cap_<name>.png (장면에서 put(C, 'cap_<name>', ...) 로 사용)"""
        self.page.evaluate("document.getElementById('__mg_cursor') && (document.getElementById('__mg_cursor').style.display='none')")
        p = os.path.join(self._shots, f'cap_{name}.png'); self.page.screenshot(path=p)
        self.page.evaluate("document.getElementById('__mg_cursor') && (document.getElementById('__mg_cursor').style.display='')")
        return p

def _launch(pw, proj, headless, size, zoom=1.0):
    """size = 녹화 해상도. zoom 배만큼 페이지를 크게 보이게 한다(화면은 size/zoom 크기로 열고 zoom 배로 선명하게 기록)."""
    prof = os.path.join(proj, 'captures', '_profile'); os.makedirs(prof, exist_ok=True)
    return pw.chromium.launch_persistent_context(prof, headless=headless, viewport={'width': round(size[0] / zoom), 'height': round(size[1] / zoom)},
                                                 device_scale_factor=zoom, locale='ko-KR', timezone_id='Asia/Seoul',
                                                 args=['--hide-scrollbars', '--disable-infobars', f'--window-size={size[0]},{size[1] + 90}'])

def _playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        raise SystemExit('playwright 가 설치되어 있지 않습니다. "python mgp.py setup" 을 다시 실행하세요.')

def login(proj, url):
    """녹화 없이 전용 브라우저만 연다. 담당자가 직접 로그인하고 창을 닫으면 로그인 상태가 프로필에 남는다."""
    with _playwright()() as pw:
        ctx = _launch(pw, proj, False, (1920, 1080)); page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url); print('브라우저에서 직접 로그인한 뒤 창을 닫으세요...', flush=True)
        try: page.wait_for_event('close', timeout=0)
        except Exception: pass
        try: ctx.close()
        except Exception: pass
    print('로그인 상태를 저장했습니다.')

def run(proj, name, ffmpeg, headless=False, fps=30):
    src = os.path.join(proj, 'captures', name + '.py')
    if not os.path.exists(src): raise SystemExit(f'녹화 대본이 없습니다: {src}  (templates/capture_template.py 참고)')
    spec = importlib.util.spec_from_file_location('cap_' + name, src); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    size = tuple(getattr(mod, 'VIEWPORT', (2560, 1440))); zoom = float(getattr(mod, 'ZOOM', 2.0))
    frames = os.path.join(proj, 'captures', '_frames_' + name); shutil.rmtree(frames, ignore_errors=True); os.makedirs(frames)
    os.makedirs(os.path.join(proj, 'assets'), exist_ok=True)
    rec = {'t0': None, 'marks': {}, 'clicks': [], 'events': [], 'scrolls': []}; stamps = []; err = None
    with _playwright()() as pw:
        ctx = _launch(pw, proj, headless, size, zoom); ctx.add_init_script(CURSOR_JS)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        def on_frame(p):
            ts = time.time()
            if rec['t0'] is None: rec['t0'] = ts
            open(os.path.join(frames, f'f{len(stamps):06d}.jpg'), 'wb').write(base64.b64decode(p['data'])); stamps.append(ts)
            try: cdp.send('Page.screencastFrameAck', {'sessionId': p['sessionId']})
            except Exception: pass
        cdp.on('Page.screencastFrame', on_frame)
        cdp.send('Page.startScreencast', {'format': 'jpeg', 'quality': 92, 'maxWidth': size[0], 'maxHeight': size[1], 'everyNthFrame': 1})
        page.goto('about:blank'); page.wait_for_timeout(300)
        if rec['t0'] is None: rec['t0'] = time.time()
        h = Helper(page, rec, os.path.join(proj, 'assets'), zoom)
        try: mod.run(page, h); h.pause(0.5)
        except Exception as e: err = e
        t_end = time.time()
        try: cdp.send('Page.stopScreencast')
        except Exception: pass
        ctx.close()
    if len(stamps) < 2: raise SystemExit(f'화면이 기록되지 않았습니다. {("오류: " + repr(err)) if err else ""}')
    # 화면이 바뀔 때만 프레임이 오므로, 각 프레임이 유지된 시간을 적어 일정한 프레임률 영상으로 만든다
    lst = os.path.join(frames, 'list.txt')
    with open(lst, 'w', encoding='utf-8') as f:
        for i, ts in enumerate(stamps):
            d = (stamps[i + 1] if i + 1 < len(stamps) else t_end) - ts
            f.write(f"file 'f{i:06d}.jpg'\nduration {max(d, 0.001):.4f}\n")
        f.write(f"file 'f{len(stamps) - 1:06d}.jpg'\n")
    out = os.path.join(proj, 'captures', name + '.mp4')
    subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-vf', f'fps={fps},scale={size[0]}:{size[1]}:flags=lanczos,format=yuv420p', '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-movflags', '+faststart', out], check=True)
    shutil.rmtree(frames, ignore_errors=True)
    dur = round(t_end - rec['t0'], 3)
    json.dump({'duration': dur, 'size': list(size), 'marks': rec['marks'], 'clicks': rec['clicks'], 'events': rec['events'], 'scrolls': rec['scrolls']}, open(out[:-4] + '.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(f"녹화 완료: captures/{name}.mp4 ({dur:.1f}초, {size[0]}x{size[1]}, 클릭 {len(rec['clicks'])}회, 강조 대상 {len(rec['events'])}곳)")
    for k, v in rec['marks'].items(): print(f'  표시 {k!r}: {v:.2f}초')
    if err: raise SystemExit(f'녹화 대본이 중간에 멈췄습니다(여기까지는 저장됨): {err!r}')
    return out
