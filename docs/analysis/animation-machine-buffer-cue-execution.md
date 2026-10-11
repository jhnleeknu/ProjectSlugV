# `480bc` U7 buffer·cue(`4aa88`/`4b784`/`e8a48`/`2986`) C++ 실행 검증 기록

[F]=검증기 산출물로 확인한 사실, [I]=추론, [U]=미확인. 대상: 커밋 `57ec34a`(detached worktree `metalslug-vu7`)의 `engine/src/animation_machine_buffer_cue.cpp`. 검증기 `tools/verify_animation_machine_buffer_cue.py`, 보고서 `artifacts/animation_machine_buffer_cue_verify/verification.json`(Git 제외). 이 기록은 통제된 fixture에서의 native 대조 기록이며 게임 전체 동등성 보고가 아니다. 원본 ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(고정 CPU 주소=파일 오프셋, 전후 변경 없음).

## 입력(고정 해시)

| 항목 | SHA256 |
| --- | --- |
| 계약 `animation-machine-buffer-cue-u7-contract.md` | `75e76e8cfb9ed6c9e18d70b9b5a153f0b54104c0d98f118756c7c67f6955ae09` |
| native 관측 `artifacts/animation_machine_buffer_cue_native/observation.json` | `06327d8cc34c58f43e8c74504816881dec250d095dbef597398e11a05705c630` |
| 관측 도구 `tools/observe_animation_machine_buffer_cue.py` | `64d363d7ca6a0201bb5b73544fd60f267f4cf419ddf3e7d46d6df41743e57ff1` |
| 검증기 `tools/verify_animation_machine_buffer_cue.py` | `49cb78a05893cc1b9eb5ff78527bae9641463d84330d827d8d05a5742ff60eae` |
| 보고서 `verification.json` | `34ca867c9101c2d5a48902b9b8b48e567d1df34fa47860c44749a5e0a6efe8c8`(두 번 실행 같음) |
| core `animation_machine_buffer_cue.cpp` | `5360f1fcad2e125782bd36a3c3dc7f253407b9d78f260a13b6ac9279f9cc32cd` |
| unit `animation_machine_buffer_cue_test.cpp` | `5ffd936d12caf36a53926afb987225affbe6d31130d2fced0767ba319f6f050b` |

native 산출물 60290개를 전부 읽고 해시를 대조했다(manifest 항목 229957). 검증기는 관측기를 실행하거나 import하지 않는다(동결된 입력).

## 방법

- 시작 상태: stage_frame seed, stage_entry `480bc` 진입 상태, typed corpus와 선언 변형(RAM 쓰기 332, frame 재진입 PC 변경 39과 A7 delta 39)이다. native SR은 읽지 않는다. 선언 SR(초기 `2000`)은 fixture 값이다.
- 분할 실행: native split phase 마다 실제 C++ `run_animation_machine`을 같은 stop으로 실행하고 64KiB RAM, 16 레지스터, PC, A7, PVC, bank, 순서 있는 port, 외부 읽기, status를 비교한다. 재개는 직전 실제 C++ 출력과 native step이 선언한 host 변경으로만 한다(재개 20626). 연속 실행을 분할 사슬과 native 연속 대조에 맞춘다(8개는 연속 실행이 분할 오류와 같은 오류로 끝남).
- 대기: native 대기(sprite `cda4`, sound `3aea`)는 기존 `AnimationMachineWaiting`으로 비교한다(대기 phase 103, 대기 시 carry Unknown, status 1).
- Carry: 원본 opcode 분류(ORI #1,CCR Set / ANDI #fe,CCR Clear / `2998` MOVE (A7)+,SR은 native가 pop한 WORD의 bit0 / FLOW_ONLY 보존 / 그 밖 Unknown). `298e`는 모든 phase에서 이전 실제 C++ 출력의 입력 C가 실제 native image WORD의 bit0와 같음을 확인한다. 입력 C 1/2 탐침을 행마다 서로 다른 첫 block의 한 phase에 건다.
- 정적: 계약 4범위(`4aa88..4abc0` 312바이트, `4b784..4b82e` 170, `e8a48..e8b5a` 274, `2986..299c` 22)가 ROM과 같고, block 시작 60개와 묶인 분기 24개, carry 보존 block 15개, 생산 block `298e` 1개가 C++ `case` 라벨·보존 표와 정확히 같다. routing 4범위가 존재함을 확인했다.

## 결과 [F]

| 항목 | 값 |
| --- | --- |
| native 조건 | 1779(정상) + 22(guard), split 22607, control 1943 |
| C++ 비교 조건 | 1801, split 22564(차이 43개는 guard 22건의 실행되지 않는 phase 22개와 이른 checked 오류로 끝난 11 row 뒤의 phase 21개다(U7 검증기 보고)), 재개 20626, control 1913, 설명되지 않는 불일치 0 |
| 그룹 | stage-frame 31, stage-entry 142, typed-buffer 656, typed-cue 819, custom-buf 54, custom-cue 64, custom-wrapper 22, custom-direct 13 |
| stage_frame 96/96 | 64 `2ac2` 복귀, 7 `cda4` 대기, 25 `3aea` 대기(관측기 기록) |
| carry | Unknown 22170 / Clear 144 / Set 250, 검사 22564, 탐침 43464(보존 12031) |
| block 시작 | 60 모두 실제 C++ phase의 첫 PC로 실행, 58 탐침(15 보존) |
| `298e` consumer phase | 195(독립 모델 일치 190 + 선언 SR fixture 차이 5) |
| 원본 읽기 감사 | 고정 17205, bank 2669, PVC 쓰기 2448 |
| ports | 4120, 외부 읽기 2 |
| zero-step | 60 x carry 3 = 180, 입력 보존 |
| negative | 375: 내부 PC 159과 피연산자 WORD PC 170은 `unsupported animation buffer cue PC`, 범위 밖 11과 도달하지 않는 stop 2는 `unsupported animation machine PC`, 홀수 PC 6(와 홀수 접근 1)은 홀수 오류, alias guard 3, Unknown carry `298e` 1, A5 불일치 1 |

### guard(C++ 정확 오류, 전체 보존)

native guard 22행은 모두 정확한 checked 오류와 전체 API 출력 보존을 확인했다(검증기 `native_guards_checked_API` 22항목, 일부는 더 이른 checked 오류로 끝남).

| 오류 문자열 | 해당 |
| --- | --- |
| `program bus requires even WORD/LONG address` | 홀수 A7 push/pop, cursor, object, record, cue, stream, `guard-buf-a5-zero` 등 |
| `unsupported animation machine PC` | 범위 밖 bad-stop 2행 |
| `unsupported sprite callback target` | `cd52` callback, RAM callback |
| `unsupported animation machine write device` | `guard-buf-rom-cursor` |
| `cue requires A5 108000` | `guard-cue-a5-zero`(native는 행 뒤쪽에서 실패, C++는 더 일찍 검사) |
| `cue wrapper status WORD overwritten` | `guard-cue-overlap-6aA0-over-SR-word-high-byte-20/-27` |
| `unsupported program bus device address` | `e8ad0` stream walk가 종료 표식 없음(`10d418=ffff`) 5행(walk 3 + 직접 진입 1 + PVC 도달 1) |

## 의도된 차이(불일치로 세지 않음) [F]

- 비 `e8a8a` 호출자의 실패 행 8개: 결정 1 선택 A에 따라 `cue wrapper failure requires known caller X`로 거부한다(native는 `480ea`까지 진행). 전부 전체 보존.
- 선언 SR fixture 5행: `298e`/`2986`이 쓰는 CCR 하위 바이트가 native 선언값과 다르고 경로에서 유도한 계약 모델과는 일치한다(`wrapper-2986-fail-*-sr2010`/`sr201f`은 `0x14` 대 `0x04`, `wrapper-298e-*-sr2001`은 `0x01` 대 `0x09`).
- alias guard 확대: cue 상태 WORD가 호출자 X 원천과 스택에서 겹치면 `cue wrapper caller X source overlaps the stack`(API 전용, 3개), 상태 WORD를 덮으면 `cue wrapper status WORD overwritten`. 계약보다 넓은 guard다.
- `a5-zero` 검사가 native보다 일찍 일어난다. 패리티(홀수) 검사가 장치 검사보다 먼저 일어나는 행 1개, 홀수 A7 push 2개는 native의 부분 쓰기가 아니라 checked 오류로 끝난다.
- `e8ad0` stream walk: native는 observer step 상한 30000에서 멈추고 C++는 장치 주소 오류로 끝난다(결정 2, 둘 다 거부).
- `6a(A0)`이 SR 워드 alias이면 SR 이미지와 노드 76에 `0000 0002`가 함께 써지고 RTS가 2로 가는 관측기 기록 경로(`unsupported_code_target`). 43e08/43e38 fallback 쓰기(`10916a` `10917b` `10b1ea` `10d26a` `10d2ea` `10d3a2..b3`)는 U7 범위 밖이다.

## 이전 verifier에서 U7로 인해 의미가 달라지는 부정 검사 (적용하지 않음) [F]

- `tools/verify_animation_machine_frame_helpers.py`: 492행 `guard-stop-not-boundary-2ac2`가 이제 실패, 549행 `natural_480bc_with_stop_4aa88`, 554행, 36행, 9/687행(`4aa88`을 미지원 경계로 가정).
- `tools/verify_animation_machine_input.py`: 74·893행 `unreached_stop 4aa88`(주석 낡음).
- 이 이동은 U7까지 적용한 최종 상태의 정렬 커밋에서 수행·기록한다.

## 검증 명령

- `make -j4 all test`(worktree): `animation_machine_buffer_cue_test PASS 63 fixtures 71 phases 8 waits 831 API invocations`.
- `clang++ -std=c++11 -O2 -Wall -Wextra -pedantic`로 harness 컴파일, 경고 없음(`compile.log` 빈 파일, SHA `e3b0c442...`).
- `.venv/bin/python tools/verify_animation_machine_buffer_cue.py` 두 번 실행, 보고서 SHA256 동일(`34ca867c...`). `failure`는 null, `ROM_unchanged`는 true.

## 한계 [U]

- 통제된 fixture이며 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이 도달성은 증명하지 않는다. native SR은 관측하지 않는다(선언 SR `2000` fixture만 사용).
- 기존 실행부 `cd58` `28ae` `43e08` sound `3aea`는 결과 전체로만 비교한다(내부는 모델링하지 않음).
- 실패는 API 출력 보존이며 원본 CPU fault rollback 동등성을 주장하지 않는다.
- 실제 게임의 `480bc` 중 SR system byte 값과 상수 `20`의 일치, `2986`의 다른 호출 지점 155곳은 미확인이다.
