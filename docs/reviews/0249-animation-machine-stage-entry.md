# `480bc` 위 stage controller F1a(진입 본체·팔레트 gate·dispatcher table·활성화·scene 초기화) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core(`animation_machine_stage_entry.cpp`)·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋(`543a3a4`) 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측(`tools/observe_animation_machine_stage_entry.py`).
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. WIP 커밋에 고정된 detached worktree `/Users/start/Workspce/metalslug-vf1a`에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 F1c2까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-stage-controller-f1-contract.md`(현재 SHA256 `82c6d30fdfe9e9f973e98663f4fc678c63f0f184c26b210eee9dc0a413b5791c`). 22개 code range(5,608바이트), 145개 block 시작, FLOW_ONLY 63, carry 소비자 6(`47af6` `47b86` `47b9c` `47bd4` `1a670` `1996e`). `e909c` TRAP은 라우팅에서 제외하고 stop 경계로 둔다. 요지: `72f0` gate(`47af6` C Clear → PC `47af0`, `AnimationMachineWaiting`), `47b02` 계산 JMP, `17292` 2048-LONG clear를 한 block으로 처리, dispatcher 재진입은 선언된 직접 진입.

### 계약 보정(적용됨)

결정 7(c)에 `104ca4`=`1ff000`을 재진입 선언에 포함하는 문장 하나를 덧붙였다. 근거: index `18` 경로 `47b1e`→`480b6`→`2a00`의 `2a02 MOVEA.L -335c(A5),A7`이 dispatcher 기준 LONG `104ca4`를 읽는다. 선언하지 않으면 frame이 A7=0으로 `2ac2`에 닿는다. observer가 고정한 계약은 SHA256 `e66e9a2127167e332f8595941f90b456696380cd4bdd4b06fda3ab60bea5d12f`(git `cc28e6f`)이고, 검증기가 `git show cc28e6f`로 복원해 줄 단위 비교한 결과 다른 줄은 결정 7(c) 한 줄뿐이며 끝에 `(F1a native 관측 보정)` 문장이 추가됐다. native observer의 `contract_discrepancies`(contract-understated) 1건과 같은 내용이다.

## 메인 리뷰

1. [F] Core를 계약의 145 block 시작과 대조했다. C++ `case` 라벨 = 계약 145 시작, 라우팅 범위 = 22 range, `carry_preserving_pc`의 F1a 항목 = 63으로 어긋남 0이다.
2. [F] `72f0` gate: `47af6`이 C Clear로 `47af0`에 닿으면 PC `47af0`에서 Waiting으로 멈추고 재개 시 `72f0`이 다시 덮어쓴다.
3. [F] `47b02` 계산 JMP의 index `80`/`96`/`ce`는 C++가 Unknown carry 오류로 거부한다(원본은 `MOVEQ #0,D0`가 C를 지워 계속 진행: 의도된 차이 1).
4. [F] 홀수 index `01`/`03`/`ff`는 홀수 PC 오류, `22`/`24`/`30`/`32`는 내부 PC로 거부된다. native와 같은 부류다.
5. [F] `e909c` TRAP은 라우팅에서 제외했다. 선언 stop에서 멈추는 행은 성공하고 선언 없이 닿으면 `unsupported animation machine PC`다.
6. [F] unicorn 대조에서 `stage_entry_body` 152 phase를 얻었고, 그중 137개가 `47af0` 재진입(0c89 04 x35, 18 x6, 00 x4, 1c x2, ff x1 등), 활성화는 104/104다.
7. 계약 공백: 테스트가 `30ec` lookup 행의 ROM 바이트(stage-entry-body 계약 소재)를 요구하나 F1a 계약에는 언급이 없다. 테스트 fixture에서 보강했다.
8. [U] ASan 실행은 부하 때문에 완료하지 못했다. `verify_animation_machine.py`는 실행하지 않았다.

## 검증 결과

- Native: 정상 310 + guard 25 = 335 조건, split 23,893 / continuous 1,427 단계. 관측 SHA `c35d0baae047784a3ed3ea7da4d5a758e5a984b5e1c29e461fe594088ced6395`, observer 도구 SHA `9735595c447619285e052f003efcf76ceca823c9bfef8799579b3a33a5ef8c90`.
- C++ 비교(detached worktree `metalslug-vf1a`, 커밋 `543a3a4`): 335 조건, split 23,761 단계(나머지 132 = 첫 checked error 이후 미재생 102 + 오류 단계 5 + guard 단계 25), continuous 1,396, 재개 22,344, 대기 23(`3aea` 10, `47af0` gate 13, `cda4` 0), 실행된 block 시작 145/145, ordered port 1,708,073, 소비자 flip control 442, FLOW_ONLY probe 32,118, zero-step 435, checked 부정 2,755. Carry Unknown 21,829 / Clear 100 / Set 1,832. 보고서 SHA `572ba869968ce8cf778d0bce4150567726f882671602c40b57d794a34a022f47`(두 번 같음), 검증기 SHA `bec171c8e1da97c817f7bfb79726ddc82f00ec77a2744b1dd312843ef40d23a1`, 실행 기록 `docs/analysis/animation-machine-stage-entry-execution.md`(SHA `53c1494755a252d3b9c4666c332d13062375ff2df99294c6c64a44c0b9417965`).
- core `engine/src/animation_machine_stage_entry.cpp` SHA `3e0d3fd26cba985708bc2f75dfcb3c404b867b5c0001e4f3d9d6fa3c6e37862d`(398행), unit `engine/tests/animation_machine_stage_entry_test.cpp` SHA `d21c7c9c4d68e3319482434f072d533e5315ffb33e15e77f06492b479cffbf13`(734행). `make -j4 all test`는 오류·FAILED 없이 끝났다(종료 코드는 캡처하지 못함). 단위 시험의 fixture·호출 수 집계는 [U] 확인하지 못했다.
- 의도된 차이(검증기 기록):
  1. index `80`/`96`/`ce` → unknown-carry 오류(3 조건, 66 phase).
  2. index `fa`→`47c00`(묶인 BEQ), `28`→`47b2e`(명령 중간) 비시작 목적지 거부(2 조건, 36 phase).
  3. `47af6`(선언 SR 2000)이 `47af0`에 닿을 때 native split은 일반 stop, C++는 Waiting.
  4. 관측기 watchdog(60,000 명령) vs C++ block 상한 1,000,000, banked-script guard 2건, 24비트 마스크(`01000006` 읽기).
  5. `e909c` TRAP: native stop 경계, C++ executor 없음.
- 이전 검증기 경계 이동은 정렬 커밋에 기록한다: `verify_animation_machine_buffer_cue.py` 824행 `e8a1c`; `verify_animation_machine_motion_walk.py` 10·655·1189·1205행(`19938..19978` extra range 행)과 968행 outside 튜플; `verify_animation_machine_scene_core.py` 785행 outside 튜플; `verify_animation_machine_scene_update.py` 78–79행 `guard-bad-stop-1a78c-on-init-entry`, 717행 `1a07a` `1a6a2` `1a69e`; `verify_animation_machine_script_placement.py` 840행 outside 튜플과 `guard-bad-stop-never-reached-init`의 실패 PC 이동.

## 남은 제약

Controlled fixture이며 자연 scheduler·자연 IRQ·BIOS 실행·`cda4`와 F1a의 결합은 [U]다. gate의 IRQ palette 효과는 `107ded` bit7 최소 효과의 선언이다. 24비트 마스크 동작은 원 68000 bus에 가깝다는 [I]이며 native의 뒷받침은 없다. Checked failure는 API 출력 보존을 뜻하고 원본 CPU fault rollback과의 동등성은 아니다. U3 논리 clear 4곳(`19710` `1971c` `1938e` `19596`)의 C 분류는 68000 규칙에서 온 [I]이며 실제 native 분기로 교차 확인됐다. 자연 scheduler·직접 플레이·전체 Goal은 미완료다.
