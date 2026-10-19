"""컷 패턴 모음 — 컷아웃 화면 키트(templates/shared_cutout.py → scenes/_shared.py)로 장면을 쓰는 문법.

이 파일은 **문법을 보여 주는 표본**이다. 여기 있는 낱말, 좌표, 컷의 순서, 패턴의 조합을 그대로 옮겨 쓰지 않는다.
화면은 대본에서 정한다: 문단마다 "이 문장을 무엇으로 보여 주면 가장 잘 전달되는가"를 먼저 적고, 거기에 맞는 패턴을 고르거나 새로 만든다.
같은 패턴을 세 컷 연속으로 쓰지 않는다. 영상마다 색, 글자 크기, 배치를 그 주제에 맞게 다시 잡는다.

한 장면 = 문단 하나쯤. 그 안에서 자막 한두 개마다 컷을 바꾼다. 컷 하나는 함수 하나이고 u 는 그 컷이 시작된 뒤 지난 초.
아래 에셋 이름(bg_PLACE, c_PERSON ...)은 자리 표시다. 그 영상의 assets.json 에 있는 id 로 바꾼다.
점검: python mgp.py check <프로젝트> sNN   → out/_check_1.jpg 에 컷마다 끝 프레임이 모인다.
"""
from _shared import *

CUES = (1, 9)
at, atw = local(CUES)
def A(n, d=-0.05): return max(0.0, at(n) + d)      # n번 자막이 시작되는 때 (컷을 바꾸는 시각)
def R(n, m): return at(n) - A(m)                    # m번 자막에서 시작한 컷 안에서 n번 자막이 나오는 때

# [그림 한 장] 화면 가득한 그림 + 느린 카메라 + (있으면) 큰 낱말 하나. 낱말은 그림의 잔잔한 쪽에 둔다
def p_picture(C, t, u): pic(C, u, 'bg_PLACE', word='낱말', at=0.4, xy=(1440, 300), size=160)

# [인물 소개] 반신 인물을 한쪽에 크게 + 이름표 + (허락받았을 때만) 말풍선. 말풍선에는 사실 정보를 담지 않는다
def p_person(C, t, u): port(C, u, 'c_PERSON', '이름', '한 줄 설명', line='짧은 대사', bg=paper, say_at=R(4, 3))

# [컷아웃 + 낱말] 컷이 시작될 때 그림부터 세운다(2초 넘게 배경만 보이지 않게). 낱말은 그 문장에 맞춘다
def p_cutout(C, t, u):
    paper(C, u); ch(C, 'c_THING', 620, 950, 700, u, 0.1, enter='left', dist=120)
    W1(C, u, '낱말', R(6, 5), (1330, 460), 200, 'k', sub='작은 줄')

# [아니라 → 이것] 낱말이 나왔다가 빨간 줄로 지워지고, 맞는 낱말이 나온다
def p_not_this(C, t, u):
    dark(C, u); no(C, u, '아닌 것', 0.3, (560, 480), 170, 'w', cut=0.8); W1(C, u, '맞는 것', R(6, 5), (1320, 480), 190, 'y')

# [좌우 비교] 화면을 둘로 나눈다. 오른쪽이 그 문장에서 밀려 들어온다
def _left(C, u): paper(C, u, 0.25); ch(C, 'c_A', 480, 960, 760, u, None); tag(C, u, '가', 480, 130, 0.2, 80)
def _right(C, u): paper(C, u); ch(C, 'c_B', 1440, 960, 760, u, None); tag(C, u, '나', 1440, 130, 0.5, 80, 'r')
def p_compare(C, t, u): split2(C, u, _left, _right, 0.4)

# [줄 세우기] 같은 종류 여러 개를 차례로. 개수가 핵심이면 숫자도 같이 올린다
def p_row(C, t, u):
    paper(C, u, 0.1); n = 0
    for i in range(6):
        ti = 0.3 + 0.25 * i
        if u >= ti: n = i + 1
        ch(C, 'c_THING', 360 + i * 240, 700, 300, u, ti, enter='up', dist=40, d=0.3, edge=5)
    if n: T(C, '%d개' % n, 960, 860, u, 0.3, 110, RED)

# [흐름] 가 → 나. 화살표는 그 문장에서 그려진다
def p_flow(C, t, u):
    paper(C, u); ch(C, 'c_A', 460, 900, 620, u, 0.1); tag(C, u, '먼저', 460, 180, 0.3, 64)
    arrow(C, [(760, 560), (1120, 560)], u, R(8, 7)); ch(C, 'c_B', 1440, 900, 620, u, R(8, 7) + 0.4, enter='right', dist=80); tag(C, u, '그다음', 1440, 180, R(8, 7) + 0.5, 64, 'r')

# [숫자] 숫자가 주인공일 때: 0에서 올라간다. 대본에 있는 숫자만 쓴다
def p_number(C, t, u): pic(C, u, 'bg_PLACE', dark=0.4); num(C, u, 0, 12000, 960, 460, 0.4, 220, '{:,}명', 'w', rnd=-2)

# [지도] 지도가 그곳으로 다가가고 표시와 지명이 찍힌다. 지도 에셋 id 는 bg_map (다르면 _shared.py 의 MAP 을 바꾼다). 좌표는 python mgp.py grid <프로젝트> bg_map 으로 읽는다
def p_map(C, t, u): intro(C, u, '작은 머리말', '큰 제목', 'c_PERSON', 500, 400, '지명', '연도', at=1.6)

# [밤·실루엣] 색을 입혀 밤으로, 또는 검은 실루엣으로 (무거운 장면을 담담하게)
def p_night(C, t, u):
    kb(C, 'bg_PLACE', u, 8); dim(C, 0.45, (16, 22, 44)); ch(C, 'c_PERSON', 700, 1000, 800, u, None, tint=NIGHT_TINT, edge=0)
    s = sil('c_THING'); put(C, s, 1500, 1040, fit(s, h=700), 0.8, anchor=(0.5, 1.0)); vignette(C, 0.45)

def draw(C, t, ta):
    # 표본이라 패턴을 차례로 늘어놓았다. 실제 장면은 그 문단에 맞는 컷 3~8개로 짠다
    seq(C, t, [(0.0, p_picture), (A(3), p_person), (A(5), p_cutout), (A(7), p_flow), (A(9), p_night)])

SFX = snd(low=[0.0], whoosh=[A(3)], thud=[A(5) + 0.1])      # 효과음: sound.json 에 있는 이름만. 컷이 바뀔 때와 큰 낱말이 나올 때만, 과하지 않게
