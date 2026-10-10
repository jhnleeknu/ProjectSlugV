# `480bc` buffer·cue U7(`4aa88`/`e8a48`) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 작성·보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측.
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. 해당 단위 커밋에 고정된 별도 detached worktree(`metalslug-vu7`)에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: U1~U7은 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 U7까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-buffer-cue-u7-contract.md`(SHA256 `75e76e8cfb9ed6c9e18d70b9b5a153f0b54104c0d98f118756c7c67f6955ae09`). `4aa88`/`4b784` frame buffer와 `e8a48`/`e8ad0`/`e8af4` cue 및 wrapper `2986`/`298e`(ROM 4범위 818바이트, block 시작 60, 묶인 분기 24). 메인 결정: (1) `2986`의 MOVE SR은 선택 A, (2) `e8ad0` stream walk는 종료 표식 없이 원본대로 block budget만 한계, (3) 디버그 경로(`10f001` bit7/0/1) 전부 구현, (4) ROM 자료는 물리 window로만 읽음, (5) 대기·재개는 기존 `AnimationMachineWaiting`, (6) 새 파일 `animation_machine_buffer_cue.cpp`, routing 4 범위.

## 메인 리뷰

1. Core 60 block을 원본과 대조했다. 결함은 없었다.
2. `2986` 선택 A: push WORD는 system BYTE `20`과 CCR 이미지로 만든다. 실패 경로의 X는 복귀 LONG이 `e8a8a`인 `e8a48` 문맥에서만 계산한다(A5=`108000`, stack alias 후 pop WORD가 push 값과 같음을 guard). 그 밖의 호출자가 실패 경로에 오면 `cue wrapper failure requires known caller X`로 거부한다. `298e`는 known carry 생산 block이며 C=pop WORD의 bit0이다.
3. Alias guard를 계약보다 넓혔다: cue 상태 WORD가 호출자 X 원천과 겹치면 `cue wrapper caller X source overlaps the stack`, 상태 WORD를 덮으면 `cue wrapper status WORD overwritten`. 이 둘은 API 전용으로 실행했다.
4. U1~U7을 모두 연결하면 `480bc`→`480f0` RTS가 끝까지 실행된다. C++가 `stage_frame` `480bc`→`480f0` 96/96 frame(64 `2ac2` 복귀, 7 `cda4` 대기, 25 `3aea` 대기)을 native와 전부 맞게 실행했다.
5. `e8ad0` stream walk: `10d418=ffff`면 종료 표식이 없어 native는 observer step 상한 30000에 걸리지만 C++는 `unsupported program bus device address`(장치 주소 오류)로 끝난다. 둘 다 거부이며 분류 차이는 의도된 것이다.
6. `6a(A0)`이 SR 워드 alias이면(관측기 기록) `0000 0002`를 노드 76에 함께 쓰고 RTS가 2로 간다(`unsupported_code_target`): 관측 사실로 기록한다.

## 검증 결과

- Native 정상 1779 + guard 22, split 22607 / continuous 1943, fresh CPU 10820. 관측 SHA `06327d8cc34c58f43e8c74504816881dec250d095dbef597398e11a05705c630`(두 번 같음), 도구 SHA `64d363d7ca6a0201bb5b73544fd60f267f4cf419ddf3e7d46d6df41743e57ff1`.
- C++ 비교(detached worktree `metalslug-vu7`, 커밋 `57ec34a`): 1801 조건, split 22564 phase(native 22607 중; 차이 43개는 guard 22건의 실행되지 않는 phase 22개와 이른 checked 오류로 끝난 11 row 뒤의 phase 21개다(U7 검증기 보고)), 재개 20626, 불일치 0(설명되지 않는 불일치 없음), 대기 phase 103, Carry Unknown 22170 / Clear 144 / Set 250, `298e` consumer phase 195, 탐침 43464, zero-step 60 x 3 = 180, negative 375. 보고서 SHA `34ca867c9101c2d5a48902b9b8b48e567d1df34fa47860c44749a5e0a6efe8c8`(두 번 같음), 검증기 SHA `49cb78a05893cc1b9eb5ff78527bae9641463d84330d827d8d05a5742ff60eae`. 실행 기록은 `docs/analysis/animation-machine-buffer-cue-execution.md`.
- core `animation_machine_buffer_cue.cpp` SHA `5360f1fcad2e125782bd36a3c3dc7f253407b9d78f260a13b6ac9279f9cc32cd`, unit `animation_machine_buffer_cue_test.cpp` SHA `5ffd936d12caf36a53926afb987225affbe6d31130d2fced0767ba319f6f050b`(63 fixture, 71 phase, 8 wait, 831 API 호출 PASS).
- 의도된 차이 8건(비 `e8a8a` 호출자 실패 행 → `cue wrapper failure requires known caller X`)과 선언 SR fixture 5행의 CCR 하위 바이트 차이(경로에서 유도한 모델과 일치, native 선언값과는 다름)는 불일치로 세지 않고 별도 기록했다.
- 이전 검증기 변경은 정렬 커밋에 기록한다: `verify_animation_machine_frame_helpers.py` 492행 `guard-stop-not-boundary-2ac2` 실패, 549행 `natural_480bc_with_stop_4aa88`, 554·36·9/687행, `verify_animation_machine_input.py` 74·893행 `unreached_stop 4aa88`(주석 낡음).

## 남은 제약

`43e08`/`43e38` fallback 쓰기(`10916a` `10917b` `10b1ea` `10d26a` `10d2ea` `10d3a2..b3`)는 U7 범위 밖이다. `2986`의 다른 호출 지점 155곳에는 선택 A의 호출자 규칙이 적용되지 않는다. 실제 게임에서 `480bc` 실행 중 SR system byte의 값과 상수 `20`의 일치는 미확인이다. 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다.
