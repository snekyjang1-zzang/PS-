"""s01: 고르고 → 담고 → 보내고, 이 세 가지를 다 하는 곳이 산지 선과장"""
from _shared import *

CUES = (1, 2)
at, atw = local(CUES)
T1, T2, T3 = 0.12, atw(1, '상자') - 0.1, at(2) + 0.05                   # 첫 단계는 바로(빈 화면으로 시작하지 않는다), 나머지는 말에 맞춰
T_WHO = atw(2, '산지') - 0.1
STEPS3 = [('c_sort', '고르고', 400, T1, 330), ('c_pack', '담고', 960, T2, 290), ('c_ship', '보내고', 1520, T3, 280)]

def draw(C, t, ta):
    bg(C)
    up = ease_io(lin(t, T_WHO - 0.2, T_WHO + 0.7))                      # '산지 선과장' 이 나올 자리를 만들려고 세 단계가 살짝 올라간다
    y0 = lerp(450, 360, up)
    for i, (spr, word, x, t0, h) in enumerate(STEPS3):
        card(C, ('step', i), x, y0, 440, 440, t, t0)
        g(C, spr, x, y0 - 16 + 4 * math.sin(t * 1.3 + i), h=h, w=370, t=t, t0=t0 + 0.12, blend='normal')
        P(C, f'{i + 1}', x - 180, y0 - 180, t, t0 + 0.25, 44, NAVY)
        T(C, word, x, y0 + 290, t, t0 + 0.3, 76, INK2)
    for i, (xa, t0) in enumerate([(650, T2), (1210, T3)]):               # 단계 사이 화살표: 천천히 그려지고 계속 흐른다
        stroke_path(C, [(xa, y0), (xa + 60, y0)], draw_on(t, t0 - 0.1, 0.7), CORAL, 10, arrow=20, alpha=fade(t, t0 - 0.1, 0.2))
    if t > T_WHO:
        k = draw_on(t, T_WHO, 0.9)
        stroke_path(C, [(190, 730), (190, 770), (1730, 770), (1730, 730)], k, NAVY, 8)      # 세 단계를 한데 묶는 선
        P(C, '전부 산지 선과장의 일', W / 2, 850, t, T_WHO + 0.55, 76, CORAL, font=F_TITLE)
