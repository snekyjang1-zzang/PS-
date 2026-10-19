"""s03: 반면, 엑셀 주문서 한 장 넘긴 판매자"""
from _shared import *

CUES = (5, 5)
FADE_IN = 0.25
at, atw = local(CUES)
T_SELLER = 0.15
T_SHEET = atw(5, '엑셀') - 0.15
T_PASS = atw(5, '넘긴') - 0.2

def draw(C, t, ta):
    bg(C)
    ks = ease_out(lin(t, T_SELLER, T_SELLER + 0.9))
    put(C, 'c_seller', lerp(1800, 1430, ks) - 4 * t, 540, fit('c_seller', h=640), ks)
    T(C, '판매자', 1430, 130, t, T_SELLER + 0.5, 64, NAVY)
    T(C, '반면', 960, 150, t, 0.1, 120, CORAL_D)
    g(C, 'c_house', 330, 520, h=330, t=t, t0=0.25, blend='normal')
    T(C, '선과장', 330, 760, t, 0.5, 54, NAVY)
    if t > T_SHEET:
        kp = ease_io(lin(t, T_PASS, T_PASS + 1.2))                       # 주문서가 판매자 손에서 왼쪽으로 넘어간다
        s, a = pop(t, T_SHEET, 0.5)
        put(C, sheet_spr(), lerp(1010, 760, kp), 560 - 50 * math.sin(kp * math.pi), s * lerp(1.0, 0.82, kp), a, rot=lerp(-6, 5, kp))
        P(C, '엑셀 주문서 한 장', lerp(1010, 760, kp), 800, t, T_SHEET + 0.35, 50, XGREEN)
        stroke_path(C, smooth_path([(1150, 330), (950, 270), (740, 330)]), draw_on(t, T_PASS, 1.2), NAVY, 9, dash=(22, 14), arrow=22, phase=t * 50, alpha=fade(t, T_PASS, 0.2))
