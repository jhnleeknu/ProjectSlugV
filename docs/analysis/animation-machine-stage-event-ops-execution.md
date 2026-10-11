# stage event F3b: 실행부 검증 기록

대상: `engine/src/animation_machine_stage_event_ops.cpp`(SHA256 `5369d279877922f015249c3d4173cccd46beabdf6c3a50d9c220c175b982f61c`)와 라우팅·carry 표를 가진 `animation_machine.cpp`(SHA `be9da5b4…`), 작업 트리 `metalslug-vf3b`(detached `679c882` = F3a + 43e34 cleanup 이동 + F3b).
계약 `animation-machine-stage-event-f3-contract.md`(SHA `bba91217…`), native 관측 `artifacts/animation_machine_stage_event_ops_native/observation.json`(SHA `e8a81643…`, 도구 `c27b2d1c…`, F3a 도구 `ae0840bb…`, 스케줄러 도구 `62bb23ff…`).
ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(검증 전후 SHA·mtime 불변). 검증기 `tools/verify_animation_machine_stage_event_ops.py`, 결과 `artifacts/animation_machine_stage_event_ops_execution/verification.json`.
[F]=실행 결과로 확인, [I]=추론, [U]=미확인. native SR은 읽지 않으며 carry는 block 분류다.

## 방법
- [F] 관측 산출물은 불변 입력이다(blob 1,383개 전부 해시 확인). 검증기는 관측 도구를 실행·import하지 않는다. 예외 하나: 자연 node의 입력 상태가 digest로만 기록된 곳에는 스케줄러 관측 도구의 `SeedRun`을 **seed 상태 생성기로만** import한다(F3 replay hook을 C++ 실행으로 교체, 도구 수정 없음). 재생성한 입력 digest가 기록 digest와 같아야 C++를 실행한다. 스케줄러 도구는 `animation_machine.cpp` 라우팅을 rA/rB 표시용으로 파싱하는데 F3b의 `!stage_event_ops_trap(...)` 항을 파싱하지 못한다. 그래서 F3b `else if` 규칙을 뺀 **파생 사본**을 scratch 실행 디렉터리에 만들어 `sched.ROUTING_SRC`에 지정한다(원본 미수정, 표시용 값은 쓰지 않음).
- [F] C++ 실행은 `run_animation_machine` 한 번 = node 한 번(PC 2ab8, A6=node, A7=SPd, LONG 104ca4=SPd, stop 2ac2). typed 직접 진입은 선언 stop까지다. TRAP #15 8곳은 선언 stop 경계다. 각 split phase는 직전 C++ 출력에서만 이어가며 native 입력은 단언만 한다(주입 없음). 연속 실행과 split 사슬, native 기록이 일치해야 한다.
- [F] 자연 node의 split 체크포인트는 native와 같이 trace의 첫 도달 순서로 F3b block 시작 109개, 외부 black box 진입 14개(`289e 28ae 2986 2a00 43e08 43e22 43e34 49a58 e9298 e94b8 e94d0 e94f6 e9768 e97c8`), F3a 복귀 block `e91b0`을 쓴다. phase 수가 native `phases`와 같아야 한다.
- 배치 harness를 쓰며 단발 harness와 같은 요청 7건의 출력이 같음을 확인했다(`harness_equivalence_cases`).

## 결과 [F]
| 항목 | 결과 |
| --- | --- |
| typed 조건 | 284 = 비guard 242 + guard 38 + native 비guard인데 C++가 오류인 의도된 차이 4. split phase 5,147회 중 비guard·guard·차이 앞부분 5,081 phase가 native phase 기록과 일치(16 register, PC, RAM SHA, PVC 이미지(정규화 bank 2워드 제외)+bank 값, port SHA, 외부 읽기) |
| 연속/split | 비guard 242개 모두 연속 = split 사슬 = native 연속 기록. 선언 A7 일치 167, stop은 2ac2 183 + TRAP 선언 stop(`e93d8` 6 `e9528` 15 `e9530` 9 `e957a` 1 `e96d4` 2 `e9702` 1 `e9780` 14 `e9788` 9) + `e9362` 1 + `e951c` 1 |
| 자연 node | 471(e9150 95, e9176 2, e9350 10, e9362 364; 자기 삭제 6): 입력 digest 471 일치, 출력 digest 471 일치, 순서 port digest 471 일치, 전부 2ac2 종료. 471개 전부 RAM·PVC·port 바이트 일치 + 실제 경로 기준 전체 split(11,763 phase) 일치 |
| carry | consumer `e936e`(288c/289e/2898)와 `e9576`(2986)의 Known C가 native 분기 경로와 일치(자연 491회 + typed 72회). flip 대조 72회(`e936e` Clear 3·Set 35, `e9576` Clear 1·Set 33), Unknown 진입은 정확히 `stage event ops caller requires known carry`(72회). 단일 block 탐침(C=1·2) 6,280회(3,140쌍, 출력은 carry만 다름)가 FLOW_ONLY 48개(consumer 2개 포함)를 정확히 재현. `2898`은 입력 C와 무관하게 Known Set을 만든다(Clear 입력도 Set) |
| API 음성 | 내부 PC 359 → `unsupported animation stage event ops PC`, 홀수 476 → `unaligned animation machine PC`, TRAP 8곳 직접 진입(stop 없음) → `unsupported animation machine PC`, 문자열 영역 짝수 20 → `unsupported animation machine PC`·홀수 20 → `unaligned animation machine PC`, 범위 이웃 2(`288a` `1a92a`; 나머지 이웃은 다른 executor 범위)·홀수 3·범위 밖 4·Unknown carry 2, 총 894건(상태 보존). zero-step 109 start + TRAP 8 = 117 × 3 carry = 351건(TRAP은 선언 stop = PC에서 상태 불변). native 진입 탐침 1,000행(992 주소)과 1:1 대응(`entry_probe_map`) |
| 결정 3(묶음) | 묶인 PC 31개는 직접 진입 거부(`unsupported animation stage event ops PC`). 갈래 PC `e939a e93a2 e96b4 e96b8`은 F3b block 시작으로 실행되며 BCS+BEQ 묶음 `e96cc`·`e96f8`의 TRAP fall-through(`e96d4` `e9702`)는 stop 경계로 확인(`trap-*`·`op0b-trap` 조건) |
| 재현성 | 전체를 두 번 실행해 verification.json SHA `2e4e3a984d086008c366dce1d8140b9776f4a408c6669d37cae084702e4b0d2a` 동일, 두 출력 디렉터리 `diff -rq` 차이 없음(컴파일된 harness 바이너리 제외) |
| `make -j4 all test` | 종료 코드 0(`animation_machine_stage_event_test`, `animation_machine_stage_event_ops_test` 포함) |

## native guard → C++ 오류 문자열 (38건)
| native 종류 | 건수 | C++ 오류 문자열 |
| --- | --- | --- |
| `unsupported_code_target`(op `08` 음수 짝수 길이 `op08-neglen-08/-06`) | 2 | `unsupported animation machine PC` |
| `unsupported_odd_data_access` | 7 | `program bus requires even WORD/LONG address` |
| `step_limit` | 5 | `animation machine block budget exceeded` |
| `unmapped_or_protected` | 7 | ROM·bank창 쓰기 5(`op08-oddlen-0b-top` `op08-oddlen-09-top` `op08-pool-count-nohead` `op09-pool-nohead` `direct-e975a-a6-rom`): `unsupported animation machine write device`; 비매핑 읽기 2(`child-stream-null` `direct-e9774-a0-unmapped`): `unsupported program bus device address` |
| `unsupported_data_device`(3c0000) | 1 | `unsupported program bus device address` |
| `unsupported_TRAP`(선언 없이 TRAP 도달) | 9 | 7곳(`e9528 e9530 e9780 e9788 e96d4 e9702 e93d8`): `unsupported animation machine PC`(같은 비라우팅 TRAP PC에 도달); op `08` 실패 2(`e957a`): `cue wrapper failure requires known caller X`(아래 의도된 차이) |
| `rng_pointer_outside_ram` | 6 | `stage area RNG pointer outside work RAM` |
| `rng_pointer_high_byte` | 1 | **오류 없음**(의도된 차이: 24 bit 마스크) |
- [F] 모든 오류는 RAM·PVC·port·16R·PC·carry가 보존된다(다른 carry 두 값으로도 확인). native 예외 rollback 동등성은 주장하지 않는다. 같은 split 구간 여부는 `same_split_segment_as_native`에 기록했으며 구간이 다른 것은 op `08` 실패 guard 2건뿐이다.

## 의도된 차이 (분류별 건수; `difference_classification_counts`)
| 분류 | 건수 | 내용 |
| --- | --- | --- |
| `deliberate_difference_op08_failure_path` | 3 | native 비guard 조건 `op08-fail` `op08-null-callback` `trap-e957a-op08-fail-declared`: 2986/28ae가 C=0을 돌려 BCS 불발 → 선언 stop인 TRAP `e957a`(native 15 phase)에서 끝난다. C++는 U7 `2986` 실패 반환의 호출자를 알 수 없어(메인 결정 U7 선택 A) 14번째 구간(stop `e9576`)에서 `cue wrapper failure requires known caller X`로 거부하고 상태를 보존한다. 앞 13 phase는 native와 일치 |
| `native_TRAP_e957a_vs_cpp_cue_failure` | 2 | 같은 경로의 선언 없는 TRAP guard(`op08-fail-undeclared`, `trap-e957a-op08-fail-undeclared`): native는 TRAP 경계 guard, C++는 같은 오류, 구간은 native보다 하나 앞(13 phase 뒤) |
| `deliberate_difference_RNG_policy_vs_original_completes` | 1 | `op0c-rng-original-completes`: native는 F1c2 정책을 끈 고정자료로 원본(링 포인터 `fffd0`: 프로그램 ROM 미러 읽기, 작업 RAM 쓰기, 완료)을 기록한다. C++는 정책을 유지해 `stage area RNG pointer outside work RAM`으로 거부(24 phase 뒤) |
| `native_cannot_follow_24bit_masked_RNG_pointer_cpp_masks_it` | 1 | `op0c-rng-high-byte`(LONG `10d722` = `0110d6b4`): native는 guard 행, C++는 24 bit 주소 `10d6b4`로 마스크해 계속 실행하며 stop까지 연속 = split 사슬 일치(오류 없음). 24 bit 마스크 차이는 이 1건뿐이다 |
| `same_policy_F1c2_RNG_guard` | 6 | native guard 행과 C++ 오류가 같은 정책(링 포인터가 작업 RAM 밖: `0` `fffd0` `200000` `2fffff` `3fffff`와 자연 상태의 미초기화 0) |
| `native_TRAP_boundary_vs_cpp_unrouted_PC` | 7 | native는 TRAP #15를 실행하지 않는 guard, C++는 같은 PC가 라우팅 제외라 `unsupported animation machine PC` |
| `native_bus_error_vs_cpp_device_check` | 7 | native 버스 오류(ROM·bank창 쓰기, 비매핑 읽기) ↔ C++ checked 오류 |
| `native_watchdog_vs_cpp_block_budget` | 5 | native 선언 명령 watchdog ↔ C++ block budget(원본은 제한 없음, 결정 7) |
| `native_code_target_guard_vs_cpp_unrouted_PC` | 2 | op `08` 음수 짝수 길이(아래) |
| `native_unsupported_data_device_vs_cpp_device_address_check` | 1 | 3c0000 데이터 읽기 |
| `same_check_class` | 7 | 홀수 WORD/LONG 접근 |
- [F] **op `08` 음수 짝수 길이**(`op08-neglen-08`, `-06`): `SUBI.W #a`로 D0.W가 음수·짝수가 되면 copy 루프가 WORD wrap(32,767/32,766 WORD)을 돌며 작업 RAM 미러 전체(스택 포함)를 덮어쓰고, `e9768`의 RTS가 LONG 0을 pop한다. C++도 똑같이 루프를 끝까지 실행(block 하나가 WORD 하나)하고 RTS로 PC 0에 도달한 뒤 `unsupported animation machine PC`로 거부한다(native와 같은 27 phase 구간, stop 0으로 PC 0 도달을 직접 확인). 즉 스택 덮어쓰기 자체를 C++가 막지는 않고, 결과 PC가 비라우팅이라 멈출 뿐이다.
- [F] 24 bit 마스킹: 위 `op0c-rng-high-byte` 외에는 native guard로 갈린 것이 없다. 나머지 d16(A5)·절대 주소 operand는 native 비교에서 모두 일치했다.

## 계약·관측 불일치 (계약 수정 없음)
1. [F] 계약의 오류 문자열 자료 `e957c..e958e`는 `SET MAKE FAIL!!\0\0`이나 ROM 바이트는 `ESET MAKE FAIL!!\0\0`(맨 앞 `E` 포함, 데이터라 실행되지 않음).
2. [F] 계약 표의 F3b "node 실행 777회(frame 0 `e9150` 95 seed, 자식 676회)"는 관측과 다르다. 관측은 F3b를 건드리는 자연 node 471회(부모 e9150 95 + e9176 2, 자식 e9350 10 + e9362 364)이며 95 seed다.
3. [F] 관측 입력 중 `engine/src/animation_machine.cpp`는 관측 이후 F3b 라우팅이 추가되어 SHA가 다르다(`3436aca9…` → `be9da5b4…`; 스케줄러 rA/rB 표시용 입력, 허용). 다른 입력은 모두 같다(`changed_inputs_since_native_observation`).
4. [F] 계약 "묶인 PC 53개·내부 PC 787개"는 F3a 22+31=53, 428+359=787과 일치. native 정적 점검의 `interior_pcs 367`은 TRAP 8곳을 내부로 센 값이며 359 + 8이다.

## block 범위
- [F] 109 start 전부 typed 또는 자연에서 실행. 자연 lead 집합에 있는 start 54개, 나머지 55개는 typed 고정자료로만 닿는다(`2898 1a92c 49a84 49a88 e93b0 e9424 e9540..e9554 e9596 e9632 e9688 e96a4..e96bc …` 전체 목록은 `block_starts_only_typed_fixture`).
- [F] 대기(wait)는 F3b 경로에 없다. 자기 삭제(2a00) 6회는 자식 `e9362`의 node-delete 경로이며 C++도 2ac2로 끝난다.
- [F] 자기 루프 block(`e9620` 등)은 stop이 시작 PC인 zero-step이 되어 첫 도달 탐침을 건너뛴다(6회). 탈출 구간이 있는 다른 조건(`op08-len-0c` 등)이 같은 block을 탐침한다.

## 기존 검증기·시험의 영향 (수정하지 않음)
- [F] `tools/verify_animation_machine_stage_event.py`(F3a 검증기)
  - 1046행 `f3b_pc_without_stop` 21 PC가 모두 `unsupported animation machine PC`를 기대한다. 지금은 TRAP 8곳만 그대로 유효하고, block 시작 9개와 `e94fe`는 실행되며(출력은 이후 PC의 오류나 budget: `e93a2`는 `animation machine block budget exceeded`), 묶인 `e9396 e939e e96b0`은 `unsupported animation stage event ops PC`다.
  - 1301행 `harness_equivalence`의 `unrouted_error`(PC `e94fe`, stop `ff000`)는 `e94fe`가 block 시작이 되어 무효.
  - F3a 범위 이웃 음성(`negatives()`가 계산): 7개 중 `e9350 e94fe e9774 e97c6`은 block 시작으로 실행, `1a93c e9442 e9766`은 내부 PC(`unsupported animation stage event ops PC`)로 무효.
  - `CPP_PINS`의 `animation_machine.cpp` `animation_machine_internal.h` `animation_machine_stage_event.cpp` SHA 고정이 바뀌어 pin 감사가 실패한다(재고정 필요).
  - 68·69·72행(stop 경계 `e94fe`, 범위 끝, 결정 3 자료)과 F3a 표 밖 연산자 94행(대상이 F3b 안인 것 0개)은 영향 없다.
- [F] `tools/verify_animation_machine_stage_area.py` 1035행 `UNROUTED_NEIGHBOURS`의 `49a84 49a86 49a8c`: `49a84`는 F3b block 시작(49a58 RNG 정책 오류 `stage area RNG pointer outside work RAM`으로 끝남), `49a86` `49a8c`는 내부 PC(`unsupported animation stage event ops PC`)로 무효. 64행과 `animation_machine_stage_area_test.cpp` 653행(`49a84`는 F1c2 범위 끝 배타)은 영향 없다.
- [F] `tools/verify_animation_machine_scene_update.py`: F3b 범위(`1a92c..1a93e`)의 리터럴 PC가 없다(범위는 `1a910` 끝, 718·732행 `1a910 1a912`는 F3a 영향으로 F3a 기록에 이미 있음). F3b로 인한 새 무효는 없다.
- [F] `engine/tests/animation_machine_stage_event_test.cpp`의 `e94fe` stop 고정자료(85~91 244 409행)와 `e98ea` 복귀 목적지(207~221 423~425행)는 stop이 라우팅보다 먼저 확인되므로 영향 없다. 315·493·507·510행은 F3b 커밋에서 이미 새 기대(`unsupported animation stage event ops PC`, `e9350` 실행)로 바뀌었다. `make test` 통과.
- 전체 목록은 `invalidated_expectation_candidates`(리터럴 PC 스캔 28행, 행별 분류)·`old_expectation_checks`(실제 C++ 결과)·`old_verifier_pin_audit`에 있다. 메인 트리의 다른 `verify_animation_machine_*.py`에는 F3b 범위 PC 리터럴(위 stage area 1035행 제외)이나 이 세 파일의 dict 형태 SHA pin이 없다(정규식 스캔, 다른 형태의 pin은 [U]).

## 한계
- 제어된 fixture이며 자연 스케줄러·IRQ·BIOS 실행을 주장하지 않는다. 자연 node 입력은 스케줄러 관측의 선언된 frame pass 모델이다. native SR은 관측하지 않았고 초기 SR은 선언 값이다(2000/2001은 consumer 직접 진입만).
- 기존 executor(cleanup 43e08/43e22/43e34, fade_card 28ae/2a00, buffer_cue 2986, input 289e, stage area 49a58, F3a block)는 전체 결과로만 비교하며 내부는 여기서 모델링하지 않는다.
- op `08` 실패 경로에서 C++가 U7 오류로 멈추므로 `e9576` Clear 경로(`e957a` TRAP stop)는 직접 진입(`carry-e9576-sr2000`)으로만 닿는다 [I]. 자연 흐름에서 op `08` 실패 후의 동작은 C++에 없다.
- 검사 실패는 API 출력을 보존할 뿐 원본 CPU 예외 rollback이 아니다. 게임 의미는 [I]/[U]다. F4 객체 callback은 범위 밖이다.

## 통합 경계 정렬 (2026-10-11)

과거 F3a/stage-area 거부 주소 목록은 상수로 보존한다. 이미 정렬된 현재 검증기에서 삭제된 tuple 또는 이동한 소스 행을 다시 추출하지 않는다. 현재 C++ 실제 실행 결과와 역사적 기대의 유효 여부를 계속 보고한다. 원본 관측 SHA와 전체 typed/natural/assertion은 유지한다.

통합 실행 명령: `.venv/bin/python tools/verify_animation_machine_stage_event_ops.py` (개발 filter 없음). 결과: typed 284조건, 원본 동등 phase 5081, guard 38, 의도된 차이 4, natural node 471, API 음성 894, zero-step 351 PASS. report SHA `8492ea56c265b63dceb70c380384d78b387c4e67c956f64330636ca45031e90d`; 실행 후 integration 기준 input 104/104 및 artifact 13/13 SHA가 일치했다. 원본 observer를 다시 실행한 결과가 아니라 보존된 원본 관측과 통합 C++의 새 비교 결과다.

자연 seed 재생성은 보존된 원본 관측의 `frames_done`를 실행 범위로 사용하고 `extend=False`로 고정한다. 새 U 실행부의 routing coverage 증가에 따라 원본 observer의 `covered_prefix`가 120 frame을 400 frame으로 자동 확대하지 않도록 하는 범위 정렬이다. CPU 상태·중간 RAM 결과는 주입하지 않으며 각 원본 node snapshot/digest 비교는 유지한다. F3b는 원본 scheduler seed의 frame 수와 stop reason도 확인한다.

frame 범위 고정 후 재검증 (2026-10-12): 같은 전체 명령으로 typed 284 (동등 242, guard 38, 의도된 차이 4), 원본 동등 phase 5081, natural 471, API 음성 894, zero-step 351 PASS. 현재 report SHA `99c6f9c5780f95cf70f9551f4f4e98056313f2eb0d4d337123c19905943e561e`; input 104/104 및 artifact 13/13 SHA 일치. 앞의 `8492...`는 범위 고정·컴파일 시간 제한 갱신 전 역사적 통합 실행이다.
