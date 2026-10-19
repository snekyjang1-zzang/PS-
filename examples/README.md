# 예시 코드 (엔진 함수 쓰는 법 참고용)

여기 있는 두 편은 키트를 시험하려고 만든 20초 안팎의 짧은 영상이다. **함수를 어떻게 부르는지만 본다.**
화면 구성, 그림 스타일, 낱말, 컷 순서는 따라 하지 않는다 — 영상마다 담당자가 정한 스타일과 그 대본에서 새로 짠다.
완성 영상의 장면 코드는 일부러 넣지 않았다(넣으면 모든 영상이 그 영상을 닮는다).

## v2_sample/ — 지도, 인물, 웹 녹화
- script.txt(대본) → narration.srt(자막) / assets.json(이미지 5장) / captures/wiki.py(녹화 대본)
- scenes/s01.py: 지도 줌인, 핀, 라벨, 편집 배경 크로스페이드(`edit_of`), 캐릭터 슬라이드 인, 도장
- scenes/s02.py: 무거운 구간의 페이드 연출, 같은 캐릭터 두 포즈 크로스페이드, 천천히 그려지고 계속 흐르는 점선 화살표
- captures/wiki.py + scenes/s03.py: 웹 화면에서 보여 줄 대상을 하나씩 가리키기, 클릭을 문장에 맞추기

## v2_sample_numbers/ — 숫자와 비교
- scenes/_shared.py: 영상 공용 도우미를 두는 방법. 올라가는 숫자(`count`), 금액에 정확히 비례하는 막대(`money_bar`)
- scenes/s01~s04.py: 단계를 말에 맞춰 차례로 등장시키기, 큰 숫자 구도, 두 금액 비교 막대

## 컷으로 쓰는 긴 영상
`templates/shared_cutout.py`(화면 요소)와 `templates/scene_cuts_template.py`(컷 패턴 모음)를 본다.
