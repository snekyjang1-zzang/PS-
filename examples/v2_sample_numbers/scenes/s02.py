"""s02: 한 상자를 보내고 선과장이 남기는 돈 = 500원 ~ 1,000원"""
from _shared import *

CUES = (3, 4)
FADE_IN = 0.25
at, atw = local(CUES)
T_BOX = atw(3, '한 상자') - 0.2
T_LEFT = atw(3, '남기는') - 0.1
T_NUM = at(4)

def draw(C, t, ta):
    bg(C)
    ko = ease_out(lin(t, 0.1, 0.9))
    put(C, 'c_owner', lerp(120, 330, ko) + 5 * t, 900, fit('c_owner', h=720), ko, anchor=(0.5, 1))
    T(C, '산지 선과장', 330, 120, t, 0.5, 60, NAVY)
    g(C, 'c_box', 780, 540 + 6 * math.sin(t * 1.2), h=320, t=t, t0=T_BOX, blend='normal')
    P(C, '상자 1개', 780, 320, t, T_BOX + 0.3, 46, NAVY)
    T(C, '선과장이 남기는 돈', 1440, 350, t, T_LEFT, 62, GRAY)
    if t > T_NUM:
        a = fade(t, T_NUM, 0.3); k = ease_out(lin(t, T_NUM, T_NUM + 1.2))        # 두 숫자가 같은 비율로 올라간다(항상 앞 숫자 < 뒤 숫자)
        num = text_spr(f'{won(500 * k)}~{won(1000 * k)}', 138, F_TITLE, CORAL_D); nw = sprite_size(num)[0]
        put(C, num, 1410, 520, alive(t, T_NUM + 1.3), a)
        put(C, text_spr('원', 84, F_TITLE, CORAL_D), 1410 + nw / 2 + 16, 538, 1.0, a)
        stroke_path(C, [(1090, 625), (1790, 625)], draw_on(t, T_NUM + 0.5, 0.9), CORAL_D, 8)
