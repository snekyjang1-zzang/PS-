# 모션그래픽 자동 제작 파이프라인 v4 (셀팜스튜디오)

대본 한 편을 받아 **자막까지 들어간 완성 영상(mp4) 한 편**을 만드는 작업 폴더다.
Claude Code는 이 문서와 `.claude/skills/motion-graphics/SKILL.md`의 순서를 그대로 따른다.

```
대본(script.txt) → Gemini TTS(음성 + 자막) → 구간 계획 → fal 이미지 에셋 → (웹 시연 녹화) → 장면 렌더 → 완성 영상
```

## 실행 환경
- 담당자는 윈도우 또는 맥에서 Claude Code로 작업한다. 모든 작업은 `python mgp.py <명령>` 하나로 한다(맥은 `python3 mgp.py <명령>`).
  (`python`이 없다고 나오면 `py mgp.py ...`. 셸 스크립트(.sh), `PYTHONPATH=...` 같은 문법은 쓰지 않는다.)
- 영상 한 편 = `projects/<이름>/` 폴더 하나. 다른 영상의 파일과 섞지 않는다.
- ffmpeg는 설치할 필요 없다(패키지에 포함). 파일 경로에 한글이 있어도 된다.

## 절대 규칙
0. **만들기 전에 묻는다. 그림 스타일은 담당자가 정한다.** 스킬의 ⓪-C 순서대로 참고 이미지나 설명을 받아 시안 3장을 만들고 승인받은 뒤에 본 에셋을 만든다. 담당자가 준 참고 이미지는 화풍만 빌리고, 장면에 그대로 넣거나 본 에셋의 참조로 쓰지 않는다.
0-1. **만들기 전에 묻는다(채널·영상).** 사용자마다 채널과 주제가 다르다. 채널 프로필(`brand/channel.json`)과 영상 브리프(`projects/<이름>/brief.md`)가 비어 있으면 스킬의 ⓪ 순서대로 물어서 채운 뒤 시작한다. 앞 영상이나 `examples/`의 스타일, 마스코트, 말투를 기본으로 가정하지 않는다. **예시와 틀 파일은 문법 참고용이다**: 화면 구성, 낱말, 컷 순서를 그대로 옮기지 않고 그 영상의 대본에서 새로 짠다.
1. 결과물은 프롬프트나 계획서가 아니라 **실제 렌더된 mp4**다.
2. 길이와 등장 타이밍은 전부 **자막 번호 기준**으로 잡는다. 초를 직접 적지 않는다.
   - 장면 구간: `CUES = (시작자막, 끝자막)` / 요소 등장: `at(n)`, `atw(n, '단어')`
   - 자막 경계는 음성의 실제 쉼에 맞춰져 있어 `at(n)`이 정확하다. `atw`는 자막 안에서의 추정치이므로(숫자는 읽는 길이로 계산) 중요한 등장은 되도록 `at(n)`에 건다.
3. **렌더 전에 반드시 `probe`** 로 프레임을 직접 열어 보고 겹침, 잘림, 빈 화면, 자막 가림을 고친다.
   - 위치와 크기는 소수점 그대로 넘긴다(`int()`, `round()`로 깎지 않는다). 정수로 깎으면 천천히 움직이는 요소가 떨린다.
4. **돈이 드는 단계는 담당자 승인 후 실행한다.** `assets`는 목록을 먼저 보여 주고 승인받은 뒤 `--yes`. `tts`는 대본 글자 수를 알리고 실행한다.
5. **API 키는 `.env`에만 있다.** 키를 출력하거나, 채팅에 붙여 달라고 하거나, 다른 파일에 적지 않는다. `.env`를 읽지 않는다(`doctor`가 유무만 알려 준다).
   - **담당자가 키가 적힌 txt 파일을 주면**: `python mgp.py keys --from "<파일 경로>"`로 등록한다. 그 파일을 Read 로 열어 보지 않는다(명령이 값은 숨기고 어떤 키를 찾았는지만 알려 준다). 등록 뒤 `python mgp.py doctor`로 확인하고, txt 파일은 지우라고 안내한다. 양식은 `API키_양식.txt`.
   - 담당자가 "API 연결해줘", "키 넣어줘"라고만 하면: `API키_양식.txt`를 채워서 넘겨 달라고 하거나, `python mgp.py keys`로 메모장에 `.env`를 열어 주고 등호 뒤에 키를 붙여 넣고 저장하라고 안내한 뒤, `python mgp.py doctor`로 확인한다. 이어서 `python mgp.py voices Bodi`가 목록을 돌려주면 Gemini 연결까지 확인된 것이다(무료). fal 연결은 첫 이미지 생성 때 확인된다.
   - 담당자가 키를 채팅에 붙여 넣었다면 `.env`에 저장해 주되, 키 값을 답변에 다시 적지 않는다.
6. **화면 글자는 최소로.** 자막이 문장을 이미 전달하므로, 화면에는 (가) 이름, 숫자, 그림의 부위처럼 "이게 뭔지" 알려 주는 짧은 라벨과 (나) 말풍선 한 개만 둔다. 내레이션을 줄여 다시 적은 제목이나 설명은 넣지 않는다. 동시에 보이는 글자는 2개까지.
   - 말풍선 농담은 담당자가 원할 때만 넣는다. 대본에 없는 대사이므로 사실 정보를 담지 않고, 무거운 구간에는 쓰지 않는다. 붓글씨는 `bubble(..., font=F_BRUSH)`.
   - 화면 텍스트는 대본에 있는 사실만 쓴다. 근거 없는 숫자(조회수, 통계 등)를 넣었다면 마무리 보고에 "연출용 임의값"으로 명시한다.
7. 죽음, 학살, 범죄 같은 무거운 구간에는 팝업 튕김, 말풍선, 밈, 채팅 패러디를 쓰지 않는다(페이드만, 담담하게).
8. 폰트에 없는 기호(✓ ✗ · ℃ 등)는 쓰지 않는다. BlackHanSans(`F_TITLE`)에는 화살표 → 도 없으므로 필요하면 `F_SANS`/`F_BK`를 쓴다.
9. 웹 녹화에서 로그인, 결제, 개인정보 입력은 대본에 넣지 않는다. 로그인은 `record --login`으로 담당자가 직접 한다. 캡차가 나오면 멈추고 담당자에게 알린다.
10. `engine/`은 여러 영상이 같이 쓰는 코드다. 영상 하나를 위해 고치지 말고, 필요한 도우미는 `projects/<이름>/scenes/_shared.py`에 만든다.

## 명령
| 명령 | 하는 일 |
|---|---|
| `python mgp.py doctor` | 설치 상태, API 키 유무 점검 |
| `python mgp.py keys --from <txt>` | 키가 적힌 txt 파일을 읽어 `.env`에 등록 (옵션 없이 쓰면 `.env`를 메모장으로 열기) |
| `python mgp.py new <이름>` | 새 영상 폴더 생성 (채널 프로필의 기본값이 들어간다) |
| `python mgp.py brief [이름]` | 채널 프로필과 영상 브리프에서 아직 안 물어본 항목 보기 |
| `python mgp.py tts <이름>` | `input/script.txt` → `input/narration.wav` + `narration.srt` (유료) |
| `python mgp.py audio <이름> <음성> <srt>` | 이미 있는 음성과 자막을 가져오기 (tts 대신) |
| `python mgp.py voices [검색어]` | Gemini 목소리 id 검색 (`--eleven`: 일레븐랩스 계정의 목소리) |
| `python mgp.py cues <이름>` | 자막 번호, 시각, 문구 출력 (구간 계획의 기준) |
| `python mgp.py assets <이름> [--yes] [id ...]` | `assets.json` → 이미지 생성. `--yes` 없이는 목록만 출력 (유료) |
| `python mgp.py sheet <이름>` | 에셋 전체 확인 시트 `out/_contact_sheet.jpg` |
| `python mgp.py grid <이름> <에셋id>` | 좌표 확인용 격자 이미지 `out/_grid_<id>.jpg` |
| `python mgp.py record <이름> <녹화이름>` | `captures/<녹화이름>.py` → 웹 시연 녹화 mp4 |
| `python mgp.py status <이름>` | 장면 구성, 빠진 자막 구간, 렌더 상태 |
| `python mgp.py probe <이름> <장면> [초 ...]` | 렌더 전 프레임 미리보기 `out/_probe_<장면>.jpg` |
| `python mgp.py render <이름> [장면 ...]` | 바뀐 장면만 렌더 (`--all` 전부) |
| `python mgp.py preview <이름>` | 처음부터 렌더된 장면까지만 합친 중간 확인용 `out/<이름>_preview.mp4` (긴 영상을 앞부분부터 확인할 때) |
| `python mgp.py final <이름>` | 장면을 이어 붙여 `out/<이름>_final.mp4` |
| `python mgp.py trim <이름> [--tempo 1.08]` | 내레이션의 긴 쉼 줄이기 + 속도 맞추기 (자막 시각도 같이 옮김, 장면 만들기 전에) |
| `python mgp.py listen <이름>` | 내레이션을 받아써서 대본과 다르게 읽힌 곳 찾기 |
| `python mgp.py check <이름> [장면 ...]` | 장면을 그려 보고 오류와 컷별 확인 그림 `out/_check_N.jpg` (렌더 전 필수) |
| `python mgp.py sound <이름> gen\|mix` | 배경음·효과음 생성(유료, `--yes`) / 내레이션과 섞기 → `final`에 들어감 |

`tts`와 `assets`에 `--mock`을 붙이면 API 없이 신호음과 자리 표시 이미지로 흐름만 시험한다(무료).

## 폴더 구조
```
mgp.py                 명령 모음 (위 표)
engine/                렌더 엔진
  mg.py                캔버스, 스프라이트 합성, 카메라, 텍스트, 경로/화살표, 이징, 자막 타이밍, 인코딩
  common.py            연출: nametag, stamp(도장), pin(지도 핀), label, flash, bubble(말풍선), caption_bar, red_spread_mask(번짐)
  ui.py                화이트 UI 키트: bg, 카드, 맥 창(win), 알약(P), 채팅 버블, 스텝바, 막대, 자막, 녹화본 넣기(capture)
  chat.py              디스코드풍 채팅 패러디 패널 (필요한 장면에서 `from chat import *`)
  timeline.py          장면 이어 붙이기 (직접 부를 일 없음)
tools/                 tts.py(Gemini), assets.py(fal), record.py(웹 녹화)
templates/             scene_template.py, capture_template.py, assets_template.json,
                       shared_cutout.py(컷아웃 화면 키트) + scene_cuts_template.py(컷 패턴 모음), style_test_assets.json(스타일 시안), sound_template.json
examples/v2_sample/    23초짜리 시험 영상(지도, 인물, 웹 녹화)의 대본, 에셋 목록, 녹화 대본, 장면 코드 — 엔진 함수 쓰는 법 참고용. 화면 구성을 본뜨지 않는다
examples/v2_sample_numbers/  20초짜리 시험 영상(단계 나열, 숫자 올리기, 금액 비교 막대) — 함수 쓰는 법 참고용
brand/                 채널 공용: channel.json(채널 프로필) + 마스코트 포즈 그림. 모든 프로젝트에서 이름으로 바로 쓴다
  style_refs/          담당자가 준 그림 스타일 참고 이미지 (화풍만 참고, 장면에 쓰지 않는다) / style_char·style_bg·style_prop.png = 승인된 스타일 시안
projects/<이름>/
  brief.md             영상 브리프 (주제, 장르, 민감 구간, 자료, 예산 — 물어서 채운다)
  project.json         목소리, 문장 간격, 마감 효과(그레인 등)
  input/script.txt     대본  →  narration.wav, narration.srt
  assets.json          에셋 목록(프롬프트)  →  assets/<id>.png
  captures/<이름>.py   웹 녹화 대본  →  <이름>.mp4, <이름>.json
  scenes/sNN.py        장면 코드
  out/                 scenes/(장면별 확인 영상), <이름>_final.mp4, 확인용 jpg
```

## 장면 파일
```python
from kit import *
CUES = (6, 8)                   # 이 장면이 맡는 자막 번호
at, atw = local(CUES)           # at(7) = 7번 자막 시작(장면 기준 초), atw(8, '단어') = 그 단어가 나올 때(추정)
def draw(C, t, ta):             # t = 장면 기준 초, ta = 영상 전체 기준 초
    draw_bg(C, 'bg_main', Cam(960, 544, ramp(t, 0, 8, 1.0, 1.1)))
    label(C, '키워드', 960, 160, t, at(7), 84)
```
- 장면들은 자막 1번부터 마지막 번호까지 **빈틈없이, 겹치지 않게** 나눠 맡는다. 장면은 다음 장면의 시작 자막 직전까지 이어진다.
- 자막은 자동으로 하단에 얹힌다(끄려면 `SUBTITLE = False`). 화면 하단 y 940 아래에는 요소를 두지 않는다.
- 앞 장면에서 부드럽게 넘어오려면 `FADE_IN = 0.2`.
- 빈티지 질감은 `project.json`의 `style`: `{"grain": 2.2, "vignette": true, "flicker": 0.012}`.
- 전체 속도는 `project.json`의 `style.pace`: 등장, 퇴장, 선 그리기 길이에 곱해진다(1.3 = 30% 느리게). 담당자가 "빠르다", "느리다"고 하면 장면을 하나씩 고치기 전에 이 값부터 바꾼다.
- 자막이 구 중간에서 끊겨 있으면 `style.subtitle_merge: true`로 화면에서만 한 줄로 이어 보여 준다(자막 번호와 시각은 그대로).
- 자막 모양은 `project.json`의 `style.subtitle`: `"dark"`(어두운 둥근 박스, 기본) 또는 `"paper"`(흰 박스 + 검은 테두리 + 그림자).
- 질감 있는 배경 이미지는 장면 안에서 움직이지 않게 고정한다. 계속 움직이면 화면 전체가 어른거리고 파일이 몇 배 커진다. 움직임은 그 위의 요소로 만든다.

## 엔진 핵심 API
- 배경: `draw_bg(C, 'bg_id', Cam(cx, cy, zoom))` 또는 흰 배경 `bg(C)`. 카메라 값을 시간에 따라 바꿔 무빙을 준다.
- 배치: `put(C, 'id', x, y, scale, alpha, rot=, anchor=, blend='normal'|'multiply', gray=, tint=)`, 배경 좌표에 붙이기 `wput(C, cam, ...)`, 크기 맞춤 `fit('id', h=300)`
- 흰 UI 스타일 배치: `g(C, 'id', x, y, h=, t=t, t0=등장시각, blend='normal')` (팝업 등장 포함)
- 스티커 배치: `stk(C, 'id', x, y, h=, t=t, t0=등장시각)` — 컷아웃에 흰 테두리와 옅은 그림자를 둘러 종이 배경 위에 붙인 스티커처럼 보이게 한다
- 텍스트: `label(C, text, x, y, t, t0, size, font, fill, stroke, stroke_fill, out_t=)`, `T(C, text, x, y, t, t0, size, color)`, 알약 `P(...)`, `nametag`, `caption_bar`
- 애니메이션: `pop(t, t0)`, `fade(t, t0, d, out_t)`, `ramp(t, t0, t1, a, b)`, `ease_out/ease_io(lin(t, t0, t1))`, `lerp`, `wobble`
- 호흡: `draw_on(t, t0, d=1.2)`(선이 그려지는 진행도), `alive(t, t0)`(등장 뒤에도 아주 천천히 커지는 배율), `stagger(i)`(차례로 등장시키는 지연)
- 선과 도형: `stroke_path(C, pts, progress, color, width, dash=, arrow=, outline=, phase=t * 60)`(phase를 주면 점선이 계속 흐른다), `smooth_path`, `circle`, `rect`, `fill`, `flash`
- 패널: `card(C, key, x, y, w, h, t, t0)`, `win(C, key, x, y, w, h, title, t, t0)`, `chat_user`, `chat_ai`, `bar`, `stepbar(C, step, t, t0, steps=[...])`
- 도장과 핀: `stamp(C, '실화', x, y, t, t0)`, `pin(C, cam, x, y, t, t0)` (에셋 없이 그려진다. `assets/stamp_frame.png`, `assets/pin.png`가 있으면 그것을 쓴다)
- 웹 녹화본(기본): `wall(C)`로 그라데이션 배경을 깔고 `screen(C, '녹화이름', 영상시각, x, y, w, h)`. 둥근 화면 + 그림자 + **대상별 자동 줌과 강조**: 녹화 대본에서 `h.focus` / `h.click` / `h.type`으로 가리킨 대상으로 한 번에 줌인해 멈추고, 그 대상에 테두리를 치고 나머지를 살짝 어둡게 한다. 마우스를 따라다니지 않는다. 스크롤 중과 대상이 없을 때는 전체 화면
- 채널 마스코트: **키트에는 들어 있지 않다. 채널 프로필을 물을 때 둘지 묻고, 원하면 새로 만든다**(스킬의 "마스코트 만들기"). `brand/channel.json`의 `mascot`이 비어 있으면 아래 호출은 아무것도 그리지 않는다.
  - 기본은 장면 안에 크게 세운다 — `mascot(C, '포즈', x, y, 높이, t, 등장, out_t=퇴장, face='left'|'right', say='대사')`. 가운데나 주제 옆에 높이 600~760으로 세워, 가리키고(point) 들여다보고(peek) 반응하게 한다. 구석에서 올라오는 `host(C, '포즈', t, 등장, side='left'|'right'|'center')`는 가끔만.
  - 포즈 이름은 `brand/<마스코트>_<포즈>.png`의 파일명이다. 표준 포즈: idle, point, shrug, shock, think, peek, facepalm, ew, full.
  - **장면 상황에 맞는 복장이 없으면 새로 만든다**: `brand/<마스코트>_full.png`를 참조 이미지(refs)로 넣어 "the same character, same outfit, now wearing ..."로 생성하고 `brand/<마스코트>_<이름>.png`로 저장, `channel.json`의 `mascot_beak`에 입 위치를 적는다. 얼굴 없는 엑스트라 대신 마스코트가 그 역할(연구자, 탐정, 마을 사람 등)을 맡으면 영상에 주인공이 생긴다.
  - 영상 한 편에 15번 안팎, 가벼운 구간에서만. 성격과 말투는 채널 프로필을 따른다.
- 구독 멘트: **영상 끝에만** 넣는다. `templates/outro_template.py`를 `projects/<이름>/outro.py`로 복사하면 내레이션 뒤에 마무리 화면이 붙고, `SAY`의 문장이 TTS 음성과 자막으로 들어간다(render 때 자동 합성, 유료). 영상 중간에는 구독 유도를 넣지 않는다(담당자가 원할 때만 `subscribe_nudge`).
- 말풍선: `bubble(C, 대사, x, y, t, t0, size, tail='left'|'right', font=F_BRUSH)`. (x, y)는 꼬리 끝이고 **화자의 머리나 입 바로 옆**에 둔다. 풍선은 글자 크기에 딱 맞게 그려진다. 화면 위로 잘리지 않게 꼬리 끝 y는 220 이상.
- 작은 부위를 가리킬 때는 동그라미만 치지 말고 `circle_crop`으로 그 부분을 확대한 돋보기를 옆에 띄운다(컷아웃 화면 키트를 쓰면 `_shared.py`에 `circle_crop`으로 만든다).
- 녹화본 시각 맞추기: `cap_mark('녹화이름', '라벨')`, `cap_click('녹화이름', 0)`(첫 클릭 시각). 줌 없이 그대로 넣기: `capture(C, '녹화이름', 영상시각, x, y, w, h, radius=)`
- 직접 찍어 넣은 영상(`captures/<이름>.mp4` 또는 `.mov`)은 `cap_fit('이름', w=1500)`으로 비율에 맞는 (가로, 세로)를 구해 `capture()`에 넣는다. **영상을 자기 소리로 통째로 틀기**: 대본의 문단 사이에 `[영상: 이름]` 줄을 넣고 `tts`를 다시 실행하면 그 길이만큼 내레이션이 비고(`input/clips.json`), 장면에서 `clip(C, '이름', ta, x, y, h=900)`으로 그리면 `final`이 그 시각에 영상의 소리를 섞는다. 영상이 아직 없으면 `[영상: 이름 75]`처럼 초를 적어 자리만 잡아 둔다. 구간 시작 시각은 `clip_at('이름')`(영상 전체 기준).
- **HTML 장면** (유리 질감·빛 번짐·화면 재현처럼 CSS 가 유리한 디자인): `scenes/sNN.html` 로 쓰면 `sNN.py` 와 똑같이 `probe`·`render`·`final` 에 들어간다. `<meta name="cues" content="3-5">` 로 자막 구간을 정하고 `engine/web/kit.css`·`kit.js` 와 `_timing.js`(자동 생성)를 불러 쓴다. 모든 등장 시각은 `data-at="6:골라내고"`(6번 자막에서 그 낱말을 말할 때)처럼 낱말에 묶는다. 큰 자막은 `<div class="cap" data-cue="6" data-hl="골라내고">`, 아래 작은 자막은 자동(끄려면 `<body data-sub="off">`). `project.json` 의 `style.scene_lead`(초)만큼 장면이 첫 낱말보다 먼저 시작한다.
- 생성 스프라이트: `text_spr`, `panel_spr`, `circle_crop`, `radial`, `blob_dark`

## 음성 엔진 고르기
`project.json`의 `tts.engine`으로 정한다(채널 프로필의 `tts`가 새 프로젝트의 기본값).
- **Gemini** (기본, `engine` 없음): `voice`에 목소리 이름. `GEMINI_API_KEY` 필요.
- **일레븐랩스** (`"engine": "elevenlabs"`): `voice_id`에 보이스 ID, `model`은 `eleven_v4`. `ELEVENLABS_API_KEY`(`sk_`로 시작) 필요. 문단을 통째로 읽고 글자별 시각을 받아 자막을 만든다.
  - **외래어를 영어식으로 굴려 읽으면** `tts.say_as`(이 영상만) 또는 `brand/channel.json`의 `say_as`(채널 공통)에 한국식으로 풀어 쓴 표기를 넣는다: `{"클로드": "클로오드"}`. 음성에만 적용되고 자막에는 원문이 나온다. 새 외래어가 나오면 그 문단만 먼저 뽑아 담당자에게 들려주고 표기를 정한다.
  - `tts.settings`: `{"stability": 0.7, "style": 0.0}` (안정도를 올리면 억양이 차분해진다).

## 좌표 잡는 법
배경 위 위치(지도의 도시, 그림 속 물체)는 눈대중으로 정하지 않는다. `python mgp.py grid <이름> <에셋id>`로 격자 이미지를 만들어 열어 보고 좌표를 읽는다.

## API 검증 상태 (2026-10-08, 맥에서 실제 키로 확인)
- Gemini TTS: `POST /v1beta/interactions`, 목소리 이름 "Bodi" 그대로 동작(id는 `en-us-bodi`, 영어권 목소리). 6문장 합성에 약 11초.
- fal `openai/gpt-image-2`: 배경 생성, `edit_of`(같은 구도 편집), `refs`(같은 캐릭터 다른 포즈) 모두 동작. 5장에 약 3분.
  - **이 모델은 투명 배경을 지원하지 않는다.** 컷아웃은 흰 배경으로 생성한 뒤 도구가 배경을 제거한다. 그래서 흰 옷, 흰 동물, 종이처럼 **가장자리가 흰 대상은 잘려 나갈 수 있다** → 시트에서 확인하고, 필요하면 프롬프트에 윤곽선(dark outline)을 넣는다.
- 웹 녹화: 실제 사이트(위키백과)에서 동작. 2560x1440으로 찍어 줌인해도 선명하다.
- **윈도우 실기 테스트는 아직 안 했다.** 윈도우에서 처음 오류가 나면 메시지를 그대로 담당자에게 보여 주고 원인을 고친다.
- API 응답 형식이 바뀌어 오류가 나면 응답 메시지를 그대로 보여 주고, 공식 문서를 다시 확인해 `tools/tts.py`, `tools/assets.py`를 고친다.
