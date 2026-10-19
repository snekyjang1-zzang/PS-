"""s04: 같은 상자에서 — 선과장 500~1,000원 vs 판매자 3,300원 (막대 길이는 금액에 정확히 비례)"""
from _shared import *

CUES = (6, 6)
FADE_IN = 0.25
at, atw = local(CUES)
T_BOX = 0.05
T_ROW1 = 0.3
T_ROW2 = atw(6, '3,300') - 0.25
X0, WMAX, VMAX = 520, 1000, 3300

def draw(C, t, ta):
    bg(C)
    g(C, 'c_box', 640, 150, h=170, t=t, t0=T_BOX, blend='normal')
    T(C, '같은 상자 1개에서', 760, 150, t, T_BOX + 0.15, 76, INK2, anchor=(0, 0.5))
    # 선과장
    g(C, 'c_owner', 230, 420, h=300, t=t, t0=T_ROW1, blend='normal')
    T(C, '선과장', 410, 345, t, T_ROW1 + 0.15, 50, NAVY, anchor=(0, 0.5))
    x1 = money_bar(C, X0 - 110, 430, WMAX, VMAX, 500, 1000, (150, 160, 180), t, T_ROW1 + 0.25, 1.0, range_color=(196, 203, 216))
    T(C, '500~1,000원', X0 - 110 + WMAX + 30, 430, t, T_ROW1 + 0.7, 66, GRAY, anchor=(0, 0.5))
    # 판매자
    g(C, 'c_seller', 230, 730, h=250, t=t, t0=T_ROW2, blend='normal')
    T(C, '판매자', 410, 625, t, T_ROW2 + 0.15, 50, NAVY, anchor=(0, 0.5))
    money_bar(C, X0 - 110, 710, WMAX, VMAX, 3300, 3300, CORAL, t, T_ROW2 + 0.25, 1.6, h=84)
    if t > T_ROW2 + 0.3:
        v = count(t, T_ROW2 + 0.3, 3300, 1.6)
        put(C, text_spr(f'{won(v)}원', 118, F_TITLE, CORAL_D), X0 - 110 + WMAX + 30, 712, alive(t, T_ROW2 + 2.0), fade(t, T_ROW2 + 0.3, 0.3), anchor=(0, 0.5))
