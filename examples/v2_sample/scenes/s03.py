"""s03: 위키백과 문서를 직접 열어 보기 → '계속되는 재발' 절을 보여 주며 "지금도 사라지지 않았다"
카메라는 보여 줄 대상(녹화 대본의 h.click / h.focus)으로 한 번에 가서 멈춘다. 장면에서는 시각만 맞춘다."""
from kit import *

CUES = (7, 8)
FADE_IN = 0.3
FADE_COLOR = (40, 28, 16)
at, atw = local(CUES)
T_CLICK = at(8) - 0.4                  # 다음 문장이 시작되기 직전에 클릭 → 문장이 시작될 때 결과 화면이 나온다
V_CLICK = cap_click('wiki', 0)         # 녹화본에서 클릭이 일어난 시각

def draw(C, t, ta):
    wall(C)
    k = ease_out(lin(t, 0.1, 0.9))                                    # 화면이 아래에서 올라오며 등장
    screen(C, 'wiki', V_CLICK + (t - T_CLICK), W / 2, 478 + 40 * (1 - k), 1568, 882, alpha=k)
    P(C, '위키백과 · 흑사병', 300, 66, t, 0.9, 46, out_t=T_CLICK + 0.6, font=F_BK)
    P(C, '지금도 계속되는 재발', 330, 66, t, T_CLICK + 0.9, 46, font=F_BK)
