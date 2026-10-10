# `480bc` 프레임 helper U1: 호출 shell과 가벼운 helper 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 작성·보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측.
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. 해당 단위 커밋에 고정된 별도 detached worktree(`metalslug-vu1`)에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: U1~U7은 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 U7까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-frame-helpers-u1-contract.md`(SHA256 `785c3fba8bf05bd405ad8c0898738504367ed0c3195ffb9aa80a0a3774c861e0`). `480bc` JSR shell 및 가벼운 helper: `47642`/`47656` player flag, `6f1c2`, `b4a2a` 영역 box(`49392`, `1c028`, `4d9d6`, `b481e`), `4701e`/`46f52` 공간 bin, `2efa6`/`3c44` 반복 효과음. 본문이 없는 경계(`1a73c` `49b0c` `4aa88` `e8a48` `4939c` TRAP)는 stop 전용이다. 기존 실행부(`289e` `43e38` `3af8` `3ac8`)는 그대로 호출한다. 신규 block 시작 106개.

## 메인 리뷰

1. Core 106 block 시작을 원본 opcode와 대조했다. 결함은 없었다.
2. 계약 주소 보정: `b481e`가 읽는 WORD는 `10800e`가 아니라 `10000e`(`-7ff2(A5)`, A5=`108000`)이다. 계약 본문은 `10000e`로 고쳤다(`b4a2a` 직접 진입 조건 목록도 같음).
3. `46f52` D1 clamp: 원본은 X 단계에서 `46fcc` `CMP.W D5,D1`/`46fd2` `MOVE.W D5,D1`로 D1만 자르고 D2는 자르지 않는다. C++가 이를 그대로 따름을 확인했다. X bin 루프가 큰 rect에서 Y 배열 뒤(`10d665` 이후)를 덮어 쓰는 것은 native 관찰 동작이며 원본 버그 여부는 판정하지 않았다.
4. `engine/src/animation_machine_frame_helpers.cpp` 57행 주석은 U1 시점의 경계 목록(`1a73c 49b0c 4aa88 e8a48`)을 기술한다. U2~U7이 이 PC들을 연결한 뒤 메인이 주석을 "Called units" 목록으로 고쳤고, 이 변경은 U7 커밋에 들어 있다.
5. 기록 외 확인: `4939c` TRAP은 A5가 `108000`이 아닐 때만 도달하며 stop 전용으로 처리했다.

## 검증 결과

- Native 199행(정상 182 + guard 17). 관측 SHA `bf7525b04f9735da44958b24fdf9be2f7d67b7f80fd7b53015b0c7645a949916`, 도구 SHA `7c6c65e09a2ffea2fc436086a441d7aa158b267df4c1f429a432161acc4a31d2`.
- C++ 비교(detached worktree, 커밋 `77b8dbe`): 분할 단계 3683(재개 3492), 연속 대조 182, carry Unknown 2979 / Clear 370 / Set 334, probe 7040, consumer flip 163, zero-step 318, negative 164 + guard 17 = 181(내부 PC 거부 137, 범위 밖 12, 경계 직접 진입 5). 보고서 SHA `737f1c0d9f33002545285d4ac15afb45b2405bc9e06b8d8c354b55d19dc60a8b`(두 번 같음), 검증기 SHA `b48acb94ef27170cd9475b489e92178456e380065697f6dcb70819e1902ddce5`, 실행 문서 SHA `741d8d8fc58f8d202bf20177dd00dcc6b35ad543bfaac57ece0e6fa139a8c7df`.
- core `animation_machine_frame_helpers.cpp` SHA `679b9809f726c7156aec4aba05da55d4bc3dd34f9734ab8e26ed970ef2fc672a`, unit `animation_machine_frame_helpers_test.cpp` SHA `d744832cb6548009a206332e05b33e9b22e20e081dbe980b2e5087d6fa86cad1`(1063 API 호출 PASS).
- U1 단계에서 `480bc`는 `1a73c`(U2) 이전 경계에서 멈춘다. 이후 단위가 `1a73c`·`49b0c`·`4aa88`·`e8a48` 경계를 실행부로 바꾸므로 fade_card 검증기의 `480bc` 미지원 negative(452행 `frame_helper_480bc_unsupported`, 154행 `declared_targets`)는 최종 상태에서 재평가한다(정렬 커밋).

## 남은 제약

X bin 겹침의 원본 버그 여부, `4939c` TRAP의 의도, 원본 CPU fault 롤백 동등성, 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다. `1a73c` `49b0c` `4aa88` `e8a48` 본문은 U2~U7이 다룬다.
