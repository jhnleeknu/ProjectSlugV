# stage controller F1c1(catalog 선택·음악 비교·진입 효과표·dispatcher callback) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core(`animation_machine_stage_catalog.cpp`)·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋(`3360752`) 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측(`tools/observe_animation_machine_stage_catalog.py`).
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. WIP 커밋에 고정된 detached worktree `/Users/start/Workspce/metalslug-vf1c1`에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 F1c2까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-stage-catalog-f1c-contract.md`(F1c1·F1c2 공용, 현재 SHA256 `f374c80f3528d5200aaa870bd66e8a58d09b400db7a84c8ee3a89fddd474a575`). F1c1은 7개 code range(564바이트), 67개 block 시작, 묶인 분기 9, FLOW_ONLY 32, 소비자 4(`478e4` `47944` `4795c` `47974`), TRAP 경계 `478a6`, F1c2 진입 `479b0`에서 자른다. 계약 머리말의 메인 결정(MAIN DECISION NEEDED 1~12를 작업자 권고대로 채택): `478de` gate는 F1 결정 2와 같은 Waiting, `478a8` 표는 F1 결정 3의 계산 PC 정책, 두 TRAP은 stop 경계, 한 frame = 한 실행(`2ac2` stop과 선언 재진입), 빈 group loop는 원본대로 block budget rollback, `3d58`/`3d6e`의 BYTE push/pop은 A7±2와 BYTE 하나(WORD `am_push` 금지), ROM 자료는 physical window만, 연쇄 seed는 137 begin 출력(5 release는 guard row).

### 계약 정정(적용 필요)

계약 "ROM 자료 window"의 group 0~4 `d99e2..dd4be`는 실제 group 4 extent `dd382..dd4d0`보다 짧다. `47864 MOVE.W 10(A0),D0`이 마지막 record `dd4ae`의 +`10` WORD `dd4be..dd4bf`를 읽는다. 계약을 "group 4는 `dd4d0`까지, 읽기는 `dd4be..dd4bf` 포함"으로 정정해야 한다(계약 파일은 이 리뷰에서 수정하지 않았다). native trace에서 창 밖 읽기는 `47864`의 4회(최대 `dd4bf`)뿐이고 모두 실제 group extent 안이다. 같은 불일치는 F1c2 observer에서도 `47a20`의 `dd4be..dd4bf` 읽기(자연 4회)로 다시 나타났다. 또한 계약의 "연쇄 seed 142건"은 137 + release guard 5로 정정된다(observer `contract_discrepancies` contract-text-differs).

## 메인 리뷰

1. [F] C++ `case` 라벨 67 = 계약 시작 67, 라우팅 7 range = 계약 code range(`478a6` 제외), `carry_preserving_pc`의 F1c1 항목 32 = FLOW_ONLY 32로 어긋남 0이다.
2. [F] core 시험은 자연 32,606 frame + runtime 1,252 frame에서 불일치 0이다.
3. [F] F1c1 추가로 `477ee`가 더 이상 지원 밖 경계가 아니게 되어 F1b `animation_machine_area_clear_test.cpp`의 음성 행은 합성 ROM의 `missing or ambiguous physical program bus ROM byte` 오류(`474ec` 읽기)로 바뀌었다.
4. [F] `478de` gate 대기는 `107ded` bit7=1에서 발생하며, 선언 IRQ 효과(`107ded`:=00) 없이는 같은 Waiting이 반복된다.
5. [U] 진입 효과 index의 게임 의미, `62(A6)` 자식의 동작, 빈 group 9~15에 자연 진입 가능성은 계약의 미확인 항목 그대로다.

## 검증 결과

- Native: 534 조건(natural 137, runtime 236, 나머지 typed 보조 등), frame 4,036, split 24,602 / continuous 4,036 단계, natural prefix 30,444 frame. 관측 SHA `15f7411230a5885e2737403e7584c6e263e2dce60ee3cc94f04ef3a1d3edd3fd`, observer 도구 SHA `22b038c1300bfb99ff0b81f19d87f3d0c1572040185a61c367c6e7209d0a23c6`.
- C++ 비교(detached worktree `metalslug-vf1c1`, 커밋 `3360752`): split 24,567 단계(+ 첫 checked error 단계 35 = native 24,602), continuous 4,001 frame이 split 최종 출력과 일치, natural prefix 30,444 frame SHA 일치, 대기 20(`478de` 17, `3aea` 3), block 시작 67/67, native guard 35개 전부 같은 단계에서 checked error, 소비자 flip control 386, FLOW_ONLY probe 26,532, 총 checked 부정 253, zero-step 201, ordered port 1,878,733. 원본 ROM 읽기 감사(fixed 110,787 / bank 1,368,556)는 모두 물리 offset의 원본 바이트와 같다. 보고서 SHA `ce76d283391d77115a1b8a296828f11ba7336beca12f75a340cc4c42f02c83ea`(두 번 같음), 검증기 SHA `64ea0698070344408e5d5b9e196cf8db5754c1a5c3806c21b2cac5c7c2f62219`, 실행 기록 `docs/analysis/animation-machine-stage-catalog-execution.md`(SHA `0348835582cee6db8c1e873541d5ec604d82bd76d91e1df3c589b2bbdba0705f`).
- core `engine/src/animation_machine_stage_catalog.cpp` SHA `a431f6b99d0d84bf00189f96ea2f0c781c55d61fadad03a5a2a0cd1beb94a56c`(180행), unit `engine/tests/animation_machine_stage_catalog_test.cpp` SHA `4fa2d3af28d9d4174dca904278a723d69a83ee6825f35db423ef1b2254e40d93`(812행). `make -j4 all test` 종료 코드 0. 단위 시험 fixture 수는 [U] 확인하지 못했다.
- 의도된 차이: (1) PVC 영상 표현 차이 34,357 frame(native raw WORD vs C++ 정규화 bank word)은 raw 쓰기값에서 native 영상을 다시 만들어 비교해 불일치 0; (2) 초기 SR 선언 없음(C=Unknown 시작, native SR 2000); (3) native guard 35개 분류: 계산 JMP 내부 slot PC 6, watchdog vs block budget 3, 미매핑 쓰기 vs 장치 주소 오류 4, 홀수 데이터 접근 8, 홀수 계산 PC 12, 선언 없는 stop 경계 2; (4) `47934` 이후 garbage 객체 pool 경로 4행(C++ `unsupported program bus device address`).
- 검증기 특이점: `totals.leader_alignment_failed`=12는 비교 실패가 아니라 홀수 계산 PC guard frame 12개(`table-01…17-odd-pc`)의 leader 정렬 한계이며 해당 frame의 leader register 대조만 생략됐다.
- 이전 검증기 경계 이동은 정렬 커밋에 기록한다: `verify_animation_machine_area_clear.py`의 `GUARD_EXPECTED` `guard-stop-not-477ee`(이제 C++가 `477ee`를 실행해 기대 오류가 깨짐)와 849–850행 `boundary_477ee_without_stop_from_47e9a`(문자열 유지, 근거 변경), `guard-no-2ac2-stop-d72fe`·`guard-no-2ac2-stop-e4234`(문자열 유지). F1c2 쪽 시험 `outside[]` 갱신(`frame_helpers_test.cpp` 297–298행, `input_test.cpp` 887행, `stage_entry_test.cpp` 719행)은 F1c2 단위의 몫이다.

## 남은 제약

Controlled fixture이며 자연 scheduler·자연 IRQ·BIOS 실행은 미확인이다. gate의 IRQ palette 효과는 `107ded` bit7 최소 효과의 선언이다. typed fixture의 RAM 영상은 native 기록 영상을 선언 fixture로 쓴 것이다. split 단계 중간의 register는 leader에서만 native 값이 있다. Checked failure는 API 출력 보존을 뜻하고 원본 CPU fault rollback 동등성은 아니다. 빈 group loop는 원본이 영원히 도는 [I]다. 직접 플레이·전체 Goal은 미완료다.
