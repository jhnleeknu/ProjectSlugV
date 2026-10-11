# 장면 core `1a73c`(480bc U2)의 실제 C++ 검증

Baseline `16de391`(detached worktree). 계약 `animation-machine-scene-core-u2-contract.md`(SHA256 `f71a0727a4e09290f257bc93ef72a5ac426ba82d2ebf0cc825b7aaa14111097a`, 20개 범위 1724바이트, 선택 A 경계)의 코드를 동결된 native 관측과 공개 C++ API(`run_animation_machine`)로 비교하는 검증기 `tools/verify_animation_machine_scene_core.py`의 기록이다. `1a0b6` `1a470` `1a7a8` `19812` `19844` `19910`은 stop 경계일 뿐 실행하지 않으며 U3/U4/U5 본문은 미확인이다.

## 입력과 방법

- Native 관측 `artifacts/animation_machine_scene_core_native/observation.json` SHA256 `2d52a025d243dc0b97777110aa79939bbd618fa73a6998bb2bb79e1de8d4661d`, 도구 `tools/observe_animation_machine_scene_core.py` SHA256 `b106db99361028c225dfd2a18570604638a88c6c2e9641abd580caac1d2602cb`. 정상 393 + guard 17 조건, split 19184(guard 앞 단계 포함), continuous 410. 관측 산출물 192661개를 전부 읽어 해시를 대조하고 trace 일관성(ordered ports, bank 재구성, 원본 ROM read, split 연결 = continuous, 경계 PC 미실행)을 감사한다. 재실행하지 않는다.
- 시작 상태: scene_frame 192행과 stage_frame 64행은 검증기가 `artifacts/scene_general_initialization`·`artifacts/stage_frame`에서 다시 만들어 provenance SHA와 fixture RAM SHA에 일치시킨다(stack LONG 포함). stage_entry_body 42행과 re-entry 112행은 원본 코드 재실행이 필요해 다시 만들지 않고, native 산출물에서 SHA로 고정된 선언 상태를 쓴다(fixture RAM SHA 대조). PVC 페이지는 선언 bank 상태에서 만들어 SHA 대조한다. 선언 레지스터 차이가 있는 행은 12개(fixture-reg 7, 홀수 A5/A7 guard 5).
- 비교 항목: full 64KiB RAM, 16R, PC, live A7, PVC device/bank, ordered ports, external reads, status. 재개 입력은 직전 실제 C++ 출력과 native 단계의 선언 host 변경(RAM write 1215)뿐이다. Split 후 continuous 대조도 한다. Native split stop 중 단일 C++ block 안에 놓인 `289e` 내부(`28a8`/`28ac`)와 계약이 앞 block에 묶은 `19c7e`/`19cb6`은 다음 phase에 합쳐 비교한다(156 phase).
- Carry는 native SR 없이 원본 opcode 분류와 대조한다: ORI #1 Set, ANDI #fe Clear, `1a2e0`(`CMP.W`+`EORI #1,CCR`)은 native 입력 RAM에서 계산한 known 값(Clear 8/Set 10), `289e` 동치 분기 Clear, FLOW_ONLY 보존, 그 밖 Unknown. 소비 block에서는 C를 뒤집어 다른 분기로 가는지(539회), 그 밖 phase에서는 입력 C=Clear/Set 탐침 36944회(보존 7634)로 분류와 carry 외 출력 동일을 확인한다. 뒤쪽 소비 block이 탐침 C를 읽는 phase는 경로가 바뀌어 탐침에서 제외한다.
- 원본 opcode 재유도: contract 215 block 시작을 분기 대상·호출 복귀·무조건 이동 뒤 후보로 다시 유도하면 계약 215개 + `19c7e` `19cb6`(계약이 앞 block에 묶음)이며 그 외 차이는 없다. FLOW_ONLY-only block 52개는 계약 목록과 정확히 같고, carry 소비 block은 8개(`1a756 1a2c6 1a302 1a30e 1a320 1a32c 1a344 1a352`), 생산 block은 `1a2cc 1a2e0 1a356 1a39a 1a3a0`이다. 215개 모두 실제 C++ phase의 첫 PC로 실행됐고, 단일 block 탐침 203개 중 carry 보존 41개가 FLOW_ONLY 목록과 일치한다. C++ `case` 라벨과 계약 215개는 양방향 차이 없다.

## 결과

`.venv/bin/python tools/verify_animation_machine_scene_core.py`가 통과했다(약 15분, 8 worker 병렬).

- 410 조건, split 19011(재개 18606), continuous 393, ports 612, native 외부 read 0. 원본 프로그램 읽기 감사: fixed 70, bank 4, PVC write 616. Carry 분포 Unknown 17389 / Clear 596 / Set 1026.
- guard 17개: 홀수 data read/pop/BSR push는 `program bus requires even WORD/LONG address`(6), 홀수 A5 쓰기는 `invalid animation machine write size/alignment`, ROM A5 쓰기는 `unsupported animation machine write device`, ROM A7 push는 `program bus write requires RAM mirror units`, 홀수 조건 index `0001`은 `unaligned animation machine PC`, 나머지 7개(index `2000`/`8000`, 맞지 않는 stop 5개)는 `unsupported animation machine PC`. 각 오류는 phase 입력과 step 시작 입력 양쪽에서 입력 전체 보존·marker ports·status 1을 확인한다.
- Negative 합계 705 = guard 17 + API 688. 직접 진입: 내부 명령 PC 283과 operand word PC 364는 `unsupported animation scene core PC`, 경계 6개, 범위 밖 PC 19개, 전체 경로 시작에 맞지 않는 stop 8개(합 33)는 `unsupported animation machine PC`, Unknown carry로 소비 block 8개 진입은 `scene core caller requires known carry`. 전부 입력 전체 보존. 양성 대조 17건(소비 block 8개의 known Clear/Set 양방향, `1a7a8` stop 성공).
- 제로 스텝: 215 block 시작 × carry 3 = 645건 입력 전체 보존. 경계 6곳의 stop==entry는 성공(관측 사항).
- 재실행 두 번의 보고서 SHA256 동일: `c2c62cc243775e3e7393b4099cb36563de616847e48f0374551fe3284cf808c2`(`artifacts/animation_machine_scene_core_execution/verification.json`). 검증기 SHA256 `d84ba04dd874d66339513f16dfba5d2afa217f825a20e33e9b39299449f9e69e`, core `engine/src/animation_machine_scene_core.cpp` SHA256 `df0763b63f75192b75119ceed669e658dcc77388d537de96892de6fe03983430`.
- `make -j4 all test`는 종료 코드 0이며 `animation_machine_scene_core_test` 2196 API 호출이 통과한다.
- C++ 불일치: 없음. 관측: 지정 조건 index는 검사 없이 원본처럼 이동하므로 홀수는 `unaligned animation machine PC`, 표 밖 짝수는 `unsupported animation machine PC`로 거부된다(전용 오류 없음, 계약 정책과 일치).

## 기존 검증기와의 관계(수정 안 함, 보고만)

`tools/verify_animation_machine_frame_helpers.py`는 `1a73c`를 지원하지 않는 경계로 가정한다: `B1A73C`를 `BOUNDARY_PCS`(36~37행)에 두고 `boundary_direct_entry_01a73c` negative(530행)가 `unsupported animation machine PC`를 기대하며, `GUARD_ERRORS['guard-ret-1a73c-boundary-via-direct']`(604행)와 `natural_480bc_with_stop_ff000`(547행)도 같은 문자열을 기대한다. 이제 `1a73c`는 U2가 실행하고 `1a7a8`에서 멈추므로 문자열이 같더라도 원인이 달라졌거나(실행 후 `1a7a8` 거부) 입력 상태에 따라 다른 오류가 날 수 있다. 이 검증기는 지시에 따라 실행하지 않았다. 정말 미지원인 PC(`1a7a8` 등)로 옮겨야 한다.

## 한계

- stage_entry_body·re-entry 154행의 시작 상태는 native 선언 상태이며 다시 만들지 않았다. 자연 scheduler·IRQ·timing·일반 CCR·직접 플레이는 범위 밖이다.
- Carry는 원본 opcode 분류이지 native 측정이 아니다. 묶인 분기·내부 PC·경계 직접 진입·Unknown carry 진입 거부는 API 전용이며 검사된 실패는 API 출력 보존이지 원본 CPU fault rollback이 아니다.
- 비null motion(U3), `1a7a8`(U4), `1a0b6`/`1a470`(U5) 본문과 RAM 필드의 게임 의미는 미확인이다.
