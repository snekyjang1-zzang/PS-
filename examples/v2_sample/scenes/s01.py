"""s01: 중세 유럽 이야기가 아니다 → 2012년 오리건주 → 실화"""
from kit import *

CUES = (1, 3)
at, atw = local(CUES)
T_NOT = atw(1, '아닙니다')
T_US = at(2)
T_MAN = atw(3, '남성')
T_REAL = atw(3, '실제로')
OREGON = (290, 228)             # grid 로 읽은 오리건주 중심

def draw(C, t, ta):
    k = ease_io(lin(t, T_US, T_US + 1.9))
    cam = Cam(lerp(960, 560, k), lerp(544, 340, k), lerp(1.0, 1.65, k) + 0.012 * t)
    draw_bg(C, 'bg_usmap', cam)
    draw_bg(C, 'bg_usmap_red', cam, alpha=ease_io(lin(t, T_REAL, T_REAL + 1.4)) if t > T_REAL else 0) if t > T_REAL else None
    if t < T_US + 0.3:
        label(C, '중세 유럽?', 960, 470, t, 0.25, 150, F_TITLE, INK, 10, CREAM, out_t=T_US - 0.1)
        a = 1 - clamp((t - (T_US - 0.1)) / 0.25)
        stroke_path(C, [(640, 350), (1280, 590)], ramp(t, T_NOT, T_NOT + 0.35, 0, 1), CRIMSON, 24, alpha=a, outline=CREAM)
        stroke_path(C, [(1280, 350), (640, 590)], ramp(t, T_NOT + 0.28, T_NOT + 0.63, 0, 1), CRIMSON, 24, alpha=a, outline=CREAM)
    pin(C, cam, OREGON[0], OREGON[1], t, T_US + 1.3, 130)
    sx, sy = cam.S(*OREGON)
    label(C, '2012년 미국 오리건주', sx + 330, sy - 190, t, T_US + 1.6, 70, F_TITLE, INK, 8, CREAM)
    if t > T_MAN:
        k2 = ease_out(lin(t, T_MAN, T_MAN + 0.9))
        put(C, 'c_man', lerp(2250, 1560, k2) - 14 * ease_out(lin(t, T_MAN + 0.9, T_MAN + 5)), 950, fit('c_man', h=800) * alive(t, T_MAN), clamp(k2 * 2), anchor=(0.5, 1))
    stamp(C, '실화', 1010, 690, t, T_REAL + 0.15, 120, rot=8)
