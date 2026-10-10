# `480bc` script opcode·배치 U5(`1a0b6`/`1a470`) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 작성·보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측.
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. 해당 단위 커밋에 고정된 별도 detached worktree(`metalslug-vu5`)에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: U1~U7은 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 U7까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-script-placement-u5-contract.md`(SHA256 `08f3f1ea9bd6e7344d97fd9bb7a2fa3cd776f40b2d46c1e305f5688ef6c1ff4c`). `1a0b6` script opcode와 `1a470` 배치(코드 872바이트 258명령 + 자료 32바이트, block 시작 88)와 cleanup 실행부의 `43e08`/`43e22` case. 메인 결정 1~7: (1) `3c0006` WORD 쓰기는 U5 지역 port helper로 VideoPortWrite(size 2) 기록, (2) `43e08`/`43e22`는 cleanup case 2개로 추가, (3) 범위 밖 opcode·표 index는 계산 PC·live 읽기 정책, (4) `1a470`의 `28ae` 실패 경로(carry 무시, fallback A0=`100e98` 쓰기)는 원본대로, (5) `1a514` 복사 loop는 원본대로, (6) 자연 seed가 실행하지 않는 5 block도 구현, (7) opcode 04는 bank 초기화 뒤 `20000c` live 읽기다.

## 메인 리뷰

1. Core를 원본과 대조했다. 결함은 없었다. 묶인 분기 13, FLOW_ONLY 35, carry 소비 block `197a2` 1개가 원본 opcode 유도와 일치한다.
2. 결정 5(복사 길이): 홀수 복사 길이는 block budget이 아니라 `200000` 창 쓰기 접근 오류(`unsupported animation machine write device`)로 끝난다. 계약 결정 5의 "홀수 길이 무한 loop는 기존 block budget 오류" 서술과 실제 오류 지점이 다르므로 기록한다. `1a470`은 `19802`가 반환한 D7을 비교한다(`1a484`).
3. 결정 1 반영: 공용 `am_write`는 바꾸지 않고 U5 지역 helper만 `3c0006`을 port로 기록한다. native 관측의 video 영역도 `3c0006`을 포함하도록 확장했다.
4. 계산 PC 정책: native `fixture-opword-0052-mid-block`은 `1a0bc+0x52=1a10e`(block `1a10c` 중간)에서 계속 실행하지만 C++는 `unsupported animation script placement PC`로 거부한다(의도된 차이, split·control 각 1건, 뒤 native phase 4개는 비재생).
5. C++ U2~U5 연결로 `scene_frame` 1a73c→RTS 594 frame 전부가 native와 일치한다(순서 있는 port, 14R, 최종 PC `ff000`, A7 `1ff000`, bank, 스택 창 밖 RAM). 스택 창 포함 64KiB 전체 image SHA도 native machine-style 기록과 594/594 일치한다.
6. U3 TST/AND known Clear 규칙은 검증기 지역 carry 분류에도 넣어야 했다(이전 carry 분류기는 정렬 시 같은 규칙이 필요).

## 검증 결과

- Native 658행(정상 626 + guard 32), 산출물 56503개. 관측 SHA `cbe215f0a9803ad9f49fc067a3fdbf66e20cef031c8651d3b41a8bdfecabcf13`, 도구 SHA `f05a7d1117b4d2612f517b491da4619ba8f5c7c0b57a06991e3533137659ae03`.
- C++ 비교(detached worktree, 커밋 `018d0b2`): 658 행, split 5475, continuous 663, 전체 프레임 594/594, 19 natural chain, Carry Unknown 5283 / Clear 35 / Set 157, 탐침 10890, `197a2` consumer phase 30, zero-step 88 x 3 = 264. 보고서 SHA `bdb51d1264d6970b684c458de83cfc8ecef9e5bc51e941b06b8af34050f9ac8d`(두 번 같음), 검증기 SHA `baf96c937eaadad9c5f6255ab4c8f82d8cc50115f6ae91c11577755d189dd2ac`, 실행 문서 SHA `face15251dc675689b2afa22e2d5ada30326cc28f11ecb960ac409fa85927b4b`.
- core `animation_machine_script_placement.cpp` SHA `41cb1c89447e6e7166ca21e5b860c14d1322b5c48189d99929426c9dabde0b37`, unit `animation_machine_script_placement_test.cpp` SHA `b11673127fc1402d358ab9746d3bb5870a09c09c0d58ae9d27b60b6b4b433202`(1124 API 호출 PASS).
- 탐색용 guard 8행(`fixture-op04-index-1fff/2000/6000/0100`, `op14-index-10`, `op24-index-10`, `op14-index-7ffe`, `op24-index-7ffe`)은 native가 ROM 읽기를 `unmapped_or_protected`로 막고 C++는 원본 ROM 바이트를 읽은 뒤 쓰기 단계에서 checked 오류로 끝난다. 둘 다 거부이나 분류와 지점이 다르다(기록만).
- 이전 검증기 변경은 정렬 커밋에 기록한다: `verify_animation_machine_scene_core.py` 46행 `BOUNDARY_PCS`, 72~73행 `GUARD_ERRORS`, 813행 stop 목록, 8·939행 문구, `verify_animation_machine_scene_update.py` 717행 `outside`의 `0x1a470`.

## 남은 제약

5,634 상태 census는 native 모델 대 원본 일치 증거이며 저장되지 않아 C++로 재생하지 않았다. 자연 `480bc` 프레임은 U5에 도달하지 않는다(U5 도달은 scene_frame 직접 `1a73c` seed, 초기화 seed, 선언 fixture). native guard가 원본 동작인지 관측기 매핑 한계인지는 미확인이다. 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다.
