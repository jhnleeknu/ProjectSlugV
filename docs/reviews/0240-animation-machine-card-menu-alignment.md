# 카드 메뉴 0236~0239 최종 상태 검증기 정렬과 전체 회귀 리뷰

대상은 이 문서를 포함하는 로컬 커밋(기준 `33780dc`)이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 역할

- 메인: Claude Opus 5.5. 변경 범위 지정, diff 확인, 통합.
- Claude Sonnet 5.5 / medium 작업자: 최종 상태(0239까지 적용)에서 이전 검증기의 경계 음성·superseded 기록 정렬과 전체 회귀 실행. 사용량 제한으로 한 번 중단됐고 자기 transcript에서 재개했다. Codex Astra/Sol은 호출할 수 없어 사용하지 않았다.

## 변경

C++ 엔진·테스트·관측 도구·native 비교 코드는 바꾸지 않았다. 바뀐 것은 음성 목록, 경계 PC 목록, superseded 기록, C++ 주석 구간 parser 종료 표지뿐이다.

- card_child: `a406` `a662` `9e94` `c2c8` "실행부 없음" 음성을 `a63c` `e84d6` `c00468`로 교체. `c2a8` 흐름은 이제 push·open·close core로 `c2f8 RTS`까지 실행되고, stale stack WORD를 pop해 `unaligned animation machine PC`로 rollback된다([F] stop `c2ba` `c2c0` `c2c8` `c2f8` 성공, `c2fa` stop은 위 오류). 양성 stop 대조를 추가했다.
- card_menu: 경계 PC `38c8` `38e2` `a63c` `e84d6` `c00468`. `a2be` 범위 밖 음성과 `a100` 내부 음성(이제 push block)을 제거하고 superseded로 기록.
- card_menu_open: `EXECUTED_BOUNDARIES`(`9e94 9f36 a2be a406 a662 a6da a70a a71a bd26 c2c8`) 직접 진입은 음성에서 제외(native row·양성 stop 대조 유지). `9fc4` 범위 밖, `c1ea` 내부 음성 제거. 새 음성 `e84d6 a63c c00468 c0046e 1a73c`. guard 2건은 superseded.
- card_menu_input: guard `a662`/`bd26` without-stop은 superseded(`bd26`은 BIOS `c00468`에 닿아 여전히 unsupported). 음성은 위 새 집합으로 교체.
- card_menu_close: guard `a698`/`a6da` superseded, 관련 직접 진입·rollback 음성 제거, 새 음성 집합. guard 수 9+superseded 2.
- card_menu_save: 주석 구간 parser 종료 표지만 변경. card_menu_nested: 변경 없음.
- [I] 실행된 경계로의 직접 진입은 push 끝 상태에서 상태 의존 오류(device address, odd JSR target 등)로 끝나므로 음성이 아니라 superseded 기록으로 둔다.

## 검증 결과(최종 상태)

- `make -j4 all test` exit 0, `git diff --check` 깨끗함.
- 카드 메뉴 검증기 보고서 SHA256:
  card_child `17e71346…9360`, card_menu `b3384785…954d`, open `e240a389…be6f`, input `894f00a7…2e16`, close `a9a191ca…bab7`, save `9e3c86ca…bed1`, nested `356cb732…78a2`. native 비교 불일치 0.
- input 보고서 SHA는 단위 커밋의 `383e7d4f…`와 다르다. 검증기 파일 자체가 바뀌었고 보고서가 자기 SHA를 포함하기 때문이다. save도 해시 입력 `card_menu.py` 변경으로 SHA가 바뀌었다.
- 이전 회귀 통과: activation `27014ffe…`, callers `0c317a81…`, carry `ff541631…`, cleanup `f7fd39d1…`, exit `87ba18d1…`, fade_card `945f4a8a…`, hud `4974f485…`, readiness `11d4b1e3…`, scene `9f58690a…`, screen `20dce6ca…`, transition `768fd120…`, base `92f3bb0b…`, map_transfer·palette_bind(각 `verification.json`).

## 남은 제약

open 검증기는 1시간 이상, close 약 40분, input 약 20분이 걸린다. 해시 대상 파일을 실행 중 고치면 실행 중인 검증기가 무효가 된다. 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다.
