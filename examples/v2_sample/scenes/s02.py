"""s02: 길고양이 → 손을 물림 → 며칠 뒤 증상 (질병 구간: 튕기는 연출 없이 페이드 위주)"""
from kit import *

CUES = (4, 6)
FADE_IN = 0.25
FADE_COLOR = (40, 28, 16)
at, atw = local(CUES)
T_CAT = at(4) + 0.1
T_MAN = at(5)
T_BITE = at(5) + 0.25          # 화살표가 다 그려질 시간을 확보하려고 문장 첫머리에서 시작
T_SICK = at(6)

def draw(C, t, ta):
    draw_bg(C, 'bg_usmap', Cam(1250 + 6 * t, 560, 2.3))      # 지도의 빈 양피지 부분을 크게 당겨 바탕으로
    fill(C, (40, 28, 16), 0.42)
    ac = fade(t, T_CAT, 0.8)
    put(C, 'c_cat', 500 + 5 * (t - T_CAT), 620, fit('c_cat', h=470) * alive(t, T_CAT, 0.05), ac)
    label(C, '길고양이', 520, 240, t, T_CAT + 0.3, 84, F_TITLE, CREAM, 8, INK, out_t=T_MAN - 0.2)
    am = fade(t, T_MAN, 0.8)
    k = ease_io(lin(t, T_SICK, T_SICK + 1.3))                 # 건강한 모습 → 아픈 모습 크로스페이드
    put(C, 'c_man', 1400, 930, fit('c_man', h=780), am * (1 - k), anchor=(0.5, 1))
    put(C, 'c_man_sick', 1400, 930, fit('c_man_sick', h=780), am * k, anchor=(0.5, 1))
    if t > T_BITE:
        p = draw_on(t, T_BITE, 1.3); out = 1 - clamp((t - T_SICK - 0.5) / 0.6)
        stroke_path(C, smooth_path([(800, 600), (980, 520), (1190, 590)]), p, CRIMSON, 12, alpha=out, dash=(26, 16), arrow=26, outline=CREAM, phase=(t - T_BITE) * 60)
        label(C, '손을 물림', 990, 430, t, T_BITE + 0.5, 72, F_TITLE, CRIMSON, 8, CREAM, out_t=T_SICK + 0.5)
    label(C, '며칠 뒤, 증상 발현', 960, 150, t, T_SICK + 0.9, 88, F_TITLE, CREAM, 8, INK)
