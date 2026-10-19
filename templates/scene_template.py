"""장면 1개 = 파일 1개.  projects/<이름>/scenes/sNN.py 로 복사해서 쓴다.

미리보기:  python mgp.py probe <프로젝트> sNN          (렌더 전 필수: 겹침·잘림·빈 화면 확인)
렌더:      python mgp.py render <프로젝트> sNN
"""
from kit import *

CUES = (6, 8)                  # 이 장면이 맡는 자막 번호 (시작, 끝). 장면들이 자막 전체를 빈틈없이 나눠 맡아야 한다.
at, atw = local(CUES)          # at(7) = 7번 자막이 시작되는 시각(장면 기준 초), atw(8, '단어') = 8번 자막에서 그 단어가 나올 때
# FADE_IN = 0.2                # 앞 장면에서 부드럽게 넘어오려면
# SUBTITLE = False             # 이 장면만 자막을 끄려면

T_TITLE = at(7)
T_WORD = atw(8, '단어')         # 자막 8번에 실제로 있는 단어여야 한다 (없으면 오류로 알려 준다)
T_END = at(8) + 3              # 참고: 장면은 다음 장면의 시작 자막이 나올 때까지 이어진다

def draw(C, t, ta):
    """t = 장면 시작 기준 초, ta = 영상 전체 기준 초.  C 에 그리면 된다. 자막은 자동으로 얹힌다."""
    cam = Cam(960, 544, ramp(t, 0, 8, 1.0, 1.10))            # 천천히 줌인 (정지 화면 금지)
    draw_bg(C, 'bg_main', cam)                                # assets/bg_main.png 전면 배경.  배경 없이 깔끔하게: bg(C)
    pin(C, cam, 560, 372, t, T_TITLE, 120)                    # 배경 좌표 (560, 372) 에 핀 (좌표는 grid 명령으로 읽는다)
    label(C, '짧은 키워드', 960, 160, t, T_TITLE + 0.2, 84, F_TITLE, INK, 8, CREAM)   # 팝업 텍스트
    if t > T_WORD:                                            # 컷아웃 슬라이드 인
        k = ease_out(lin(t, T_WORD, T_WORD + 0.45))
        put(C, 'c_host', lerp(2300, 1480, k), H + 10, fit('c_host', 760), 1, anchor=(0.5, 1))
    stamp(C, '실화', 330, 860, t, T_WORD + 0.5, 110, rot=8)   # 도장

    # 웹 녹화본 넣기 (python mgp.py record 로 만든 captures/demo.mp4). 녹화 대본에서 가리킨 대상으로 자동 줌인 + 테두리 강조:
    #   wall(C)                                                     # 그라데이션 배경
    #   screen(C, 'demo', cap_mark('demo', '시작') + t, W / 2, 478, 1568, 882)
    # 클릭 순간을 문장에 맞추려면:  screen(C, 'demo', cap_click('demo', 0) + (t - at(7)), ...)
    # 선이나 화살표는 천천히 그리고, 다 그려진 뒤에도 흐르게:
    #   stroke_path(C, pts, draw_on(t, T_WORD, 1.3), CRIMSON, 12, dash=(26, 16), arrow=26, outline=CREAM, phase=t * 60)
