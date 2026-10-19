"""위키백과 흑사병 문서: 전체 화면 → 목차에서 '계속되는 재발' 클릭 → 그 절의 첫 문단을 보여 준다.
한 문장에 한 곳만 보여 준다. 보여 줄 곳이 아니면 마우스를 움직이지 않는다."""
VIEWPORT = (2560, 1440)
ZOOM = 2.0

def run(page, h):
    h.goto('https://ko.wikipedia.org/wiki/흑사병')
    h.mark('시작')
    h.pause(1.3)                                                     # 전체 화면: 어떤 문서인지 보여 준다
    h.click('#vector-toc a:has-text("계속되는 재발")', after=0.9)      # 목차의 '계속되는 재발' → 줌인 + 강조 후 클릭
    h.focus('div.mw-heading:has(#계속되는_재발) + p', hold=3.0)        # 이동한 절의 첫 문단 = 여기를 보세요
