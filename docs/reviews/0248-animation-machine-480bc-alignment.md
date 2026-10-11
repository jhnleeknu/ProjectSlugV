# 480bc 프레임 helper U1~U7 최종 상태 검증기 정렬과 전체 회귀 리뷰

대상은 이 문서를 포함하는 로컬 커밋(기준 `0c66c2c`)이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 역할

- 메인: Claude Opus 5.5. 범위 지정, diff 확인, 통합.
- Claude Sonnet 5.5 / medium 작업자: U7까지 적용한 최종 상태에서 이전 검증기의 음성·guard·경계 기록 정렬과 전체 회귀. 사용량 제한으로 두 번 중단됐고 자기 transcript에서 재개했다. Codex Astra/Sol은 호출할 수 없어 사용하지 않았다.
- 실행 환경: 작업자는 scratch venv(Unicorn 2.1.4, capstone 5.0.7)로 실행했다. 저장소 `.venv`는 Unicorn 2.1.4, capstone 5.0.6이다. [I] 검증기는 capstone을 정적 디코드 대조에만 쓰며 모든 결과가 통과했다.

## 변경

엔진·C++ 테스트·관측 도구·native 비교 코드는 바꾸지 않았다. 15개 검증기의 음성·guard 기대값만 바꿨고, 대체된 항목은 지우지 않고 보고서 JSON의 superseded 기록으로 남겼다.

- frame_helpers(U1): `guard-stop-not-boundary-2ac2`는 이제 오류 없이 `2ac2`에 닿는다(superseded). `natural_480bc_with_stop_49b0c`/`_4aa88`는 성공으로 바뀌어 양성 확인과 superseded 기록. `1a73c 49b0c 4aa88 e8a48 4939c` 직접 진입 음성은 그대로 성립한다.
- scene_core(U2): bad-stop guard 2개, 경계 6 PC 직접 진입, 범위 밖 `19830 19850 1a40e 1a7a8`, `full_path_start_with_stop_0ff000`는 이제 성공(superseded). `19820 198ec 19920`은 `unsupported animation motion walk PC`로 고정.
- scene_update(U4): `outside_range_entry_01a470` superseded.
- input(U6): `rom-outside-unit` guard 2개는 `program bus requires even WORD/LONG address`, null-path bad-stop 2개는 `unsupported program bus device address`.
- motion_walk(U3): bad-stop guard 1개, `019772` 범위 밖, `full_path_start_with_unreached_stop_0ff000` superseded. `0197d8`은 `unsupported animation script placement PC`.
- card_menu_input/close/open: `1a73c` 직접 진입은 이제 `unsupported program bus device address`(U2 routing).
- exit, fade_card, hud, readiness, screen, activation, callers: 이전 "실행부 없는 후속 PC" 음성이 U1~U7 실행 뒤 상태 의존 checked 오류(device address 또는 even WORD/LONG)로 끝난다. 이전·관측 오류를 기록했다.
- 예상과 달리 필요 없던 이동: `1a470`·`1a0b6` full-path guard, carry 규칙, 카드 메뉴 음성 `e84d6 a63c c00468 c0046e`.

## 검증 결과(최종 상태)

- 기존 `tools/verify_animation_machine*.py` 28개 모두 PASS(마지막 편집 뒤 전체 재실행; callers.py는 공유 dependency hash 대상이므로 전부 재실행). card_menu_open 약 3.6시간.
- 보고서 SHA 앞 16자리: base `2a1444cdf5e4696c`, frame_helpers `812fec21ebb4893c`, scene_core `10fe0d60ed16278f`, scene_update `9f66d7cc1114e8e1`, input `76820ed3dd962bd1`, motion_walk `0d0b785c2b5bc7f7`, buffer_cue `97454c7fe111e5dd`, script_placement `17c5713ad4227afe`, carry `e959af80484a0c05`, activation `5487ee739299e07d`, callers `1e49d706e31d737f`, cleanup `10fb7af112c11474`, exit `c460795a0ee0d38e`, fade_card `108663031b37e0d8`, hud `eb3553b43859dc0a`, map_transfer `188dbd82d74dd804`, palette_bind `73c3f3c3408460e2`, readiness `64600a662b02d883`, scene `09eb50e409b915ee`, screen `a8c295a708fcfc91`, transition `ba1c4d69a8e0bece`, card_child `67ff9832fb5ad2ff`, card_menu `d3eb9f13f6ab7c39`, card_menu_input `be68cc59955c69c4`, card_menu_close `40f3df1e087c028e`, card_menu_open `d3f0216333e95c4f`, card_menu_save `ca81d98ada1897ce`, card_menu_nested `3d1787c7c9a57e9e`.
- `make -j4 all test` exit 0(엔진 불변), `git diff --check` 깨끗함(메인 확인).

## 남은 제약

F1a 이후 단위(stage controller·event·scheduler)는 별도 worktree WIP이며 이 커밋에 없다. 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다.
