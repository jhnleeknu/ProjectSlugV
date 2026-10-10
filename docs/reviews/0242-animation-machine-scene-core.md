# `480bc` 장면 core U2(`1a73c`) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 작성·보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측.
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. 해당 단위 커밋에 고정된 별도 detached worktree(`metalslug-vu2`)에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: U1~U7은 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 U7까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-scene-core-u2-contract.md`(SHA256 `f71a0727a4e09290f257bc93ef72a5ac426ba82d2ebf0cc825b7aaa14111097a`). `1a73c` 장면 core(범위 20개 1724바이트, block 시작 215). 메인 결정은 두 가지다: (1) 비null motion 경계는 선택 A(`19812`/`19844`/`19910` 분기 대상에서 stop), (2) 조건 index는 원본 계산 PC를 따르는 정책. `1a0b6` `1a470` `1a7a8` `19812` `19844` `19910`은 stop 경계일 뿐 U2가 실행하지 않는다.

## 메인 리뷰

1. Core 215 block을 원본과 대조했다. 결함은 없었다. `19c7e`/`19cb6`은 계약이 앞 block에 묶은 항목이다.
2. 조건 index 정책: 지정 조건 index는 검사 없이 `1a2d4+sext(D0.W)`로 이동하고, 홀수는 `unaligned animation machine PC`, 표 밖 짝수는 `unsupported animation machine PC`로 거부한다(전용 오류 없음, 계약과 일치).
3. `scene_frame` 1a73c→RTS 594 frame을 C++가 native 기록과 전부 맞게 실행함은 U2~U5 전체 연결 후(U5 검증기) 확인했다. U2 단독 상태에서는 `1a7a8` 등에서 stop한다.
4. Carry는 원본 opcode 분류(ORI/ANDI/`1a2e0` 계산 값, FLOW_ONLY 보존, 소비 block 8개)이며 native SR 측정이 아니다.

## 검증 결과

- Native 정상 393 + guard 17, split 19184, continuous 410. 관측 SHA `2d52a025d243dc0b97777110aa79939bbd618fa73a6998bb2bb79e1de8d4661d`, 도구 SHA `b106db99361028c225dfd2a18570604638a88c6c2e9641abd580caac1d2602cb`.
- C++ 비교(detached worktree, 커밋 `16de391`): split 19011(재개 18606), continuous 393, ports 612, Carry Unknown 17389 / Clear 596 / Set 1026, 탐침 36944회, 소비 block flip 539회, zero-step 215 x 3 = 645, negative 705 = guard 17 + API 688. 보고서 SHA `c2c62cc243775e3e7393b4099cb36563de616847e48f0374551fe3284cf808c2`(두 번 같음), 검증기 SHA `d84ba04dd874d66339513f16dfba5d2afa217f825a20e33e9b39299449f9e69e`, 실행 문서 SHA `3a70a6cedce31a657dcd4ac25ceeb99b8d2bd5672c2b560ca3210953f7c0e188`.
- core `animation_machine_scene_core.cpp` SHA `df0763b63f75192b75119ceed669e658dcc77388d537de96892de6fe03983430`, unit `animation_machine_scene_core_test.cpp` SHA `b9de0b0a5e4eb9944358f0a2f60bc76b12137f8c09c3c9179153bf72ceb1eb13`(2196 API 호출 PASS).
- 이전 검증기(`verify_animation_machine_frame_helpers.py` 36~37·530·547·604행 등)가 `1a73c`를 미지원 경계로 가정하는 negative의 이동은 최종 상태의 정렬 커밋에 기록한다.

## 남은 제약

stage_entry_body·re-entry 154행의 시작 상태는 native 산출물에 SHA로 고정된 선언 상태이며 재구성하지 않았다. 비null motion(U3), `1a7a8`(U4), `1a0b6`/`1a470`(U5) 본문과 RAM 필드의 게임 의미는 이 단위 밖이다. 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다.
