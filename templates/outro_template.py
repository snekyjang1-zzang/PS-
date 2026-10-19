"""마무리 화면 (선택).  projects/<이름>/outro.py 로 복사하면 내레이션이 끝난 뒤에 덧붙는다.
SAY 의 문장은 render 때 TTS(project.json 의 목소리)로 합성되어 음성과 자막으로 들어간다. SAY 를 지우면 무음 화면이 된다.
본편 내레이션을 다른 목소리로 직접 가져온 경우(mgp audio) 목소리가 달라지므로 담당자에게 알린다."""
from kit import *

SAY = "오늘 이야기가 흥미로웠다면, 구독과 좋아요 부탁드립니다. 다음 영상에서 다시 만나겠습니다."
SECONDS = 6
SAY_AT = 0.9                      # 화면이 밝아진 뒤 멘트 시작

def draw(C, t):
    bg(C)                                                                   # 영상의 배경에 맞춰 바꾼다 (예: draw_bg(C, 'bg_paper', Cam()))
    fill(C, (40, 34, 28), 0.9 * (1 - fade(t, 0.0, 0.6)))                    # 어두운 마지막 화면에서 종이 배경으로 밝아진다
    press = SAY_AT + 2.6                                                    # '구독과 좋아요' 즈음에 버튼이 눌린다
    mascot(C, 'full', 620, 540, 860, t, 0.4, face='right')                  # 말풍선 없이 서 있기만 한다 (멘트는 음성과 자막으로)
    subscribe_button(C, 1310, 500, t, 0.8, press_t=press, scale=1.5)
