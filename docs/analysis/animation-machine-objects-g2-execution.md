# 오브젝트 콜백 G2 (F4 U17, U18, U19, U20a, U20b, N01) C++ 실행 검증

대상: `engine/src/animation_machine_objects_{u17,u18,u19,u20,u20b,n01}.cpp`의 공개 API `run_animation_machine`. 검증기: `tools/verify_animation_machine_objects_g2.py`(SHA256 `7ee7048e52a3d7a9f081d5de9b34b27188a3c70ecfafdf5b6910ff6d4d4e08da`). 작업 트리: detached `4f91481`(U20b + N01까지 통합). ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(SHA·mtime 불변 재확인). 검증 출력은 공유 `artifacts/`가 아니라 `/Users/start/Workspce/ms5-scratch/vg2/out/run{1,2}/verification.json`에 두었다(환경변수 `G2_OUT`; 기본값은 `artifacts/animation_machine_objects_g2_execution`).

두 번 전체 실행(run3/run4)한 `verification.json` SHA256 `f6773ae749a342085c559e5010435070d0e4705d9eecd58a860a1e2c2e71c082` 동일. `make -j4 all test` 종료 0, 경고 0. (먼저 실행한 run1/run2는 JSON에 스크래치 경로가 들어 있어 SHA가 달랐고, 경로를 정규화한 뒤 다시 두 번 실행했다.) `engine/src`는 수정하지 않았다.

## 입력 (SHA 고정)
- 네이티브 관측 `observation.json` `ad6873c7…`, `fixtures.json.gz` `a755dfb6…`, 관측 도구 `observe_animation_machine_objects_g2.py` `50cd24d6…`, 임포트한 g1 `b878cd26…`, scheduler `62bb23ff…`, scheduler_rng `659f8636…`, pvc_banks `86ebf962…`, address_map `5e11a866…`, 계약 6개(각 SHA는 도구의 `G2.UNITS`).
- [F] BIOS 실행·자연 IRQ·자연 스케줄러를 주장하지 않는다. 노드 진입(PC 2ab8, A6=node, A7=SPd), base 120프레임/RNG 400프레임/answer-00 변형 프레임 패스, 대기 해제, 모든 typed fixture는 선언된 상태다.

## 방법
1. **자연 노드 14,320개(290 case).** 관측 파일에는 노드 진입 상태 덤프가 일부뿐이라 g2 관측기의 `make_run`(BaseRun/RngRun)으로 모든 case를 재생성하고, 노드마다 기록 행(entry/exit 전체 digest, A6, callback, partial, depth), case별 callback 수·stop·프레임·run digest, 덤프가 있는 노드(228)의 상태 digest와 비교했다(전부 일치).
2. 네이티브 노드를 `Flow`(영속 CPU, stop 2ac2)로 재생해 G2 유닛 piece 경계 상태를 얻고, 실제 C++를 piece별(체인: 직전 C++ 출력에서만 재개, 선언된 sound 3aea / sprite cda4 대기 해제 쓰기만 추가)과 노드 전체 연속 실행으로 실행한다. phase마다 전체 64KiB RAM·16 레지스터·PC·A7·bank base·PVC 이미지(독립 PVC 모델)·ff8/ff9·순서 있는 포트·external read 수·대기 목록을 비교하고 기록된 exit digest를 C++ 출력으로 재계산한다. Known C는 네이티브 MOVE SR 프로브 C 비트와 비교한다(Unicorn SR는 쓰지 않는다).
3. 블랙박스 phase(G2 코드가 없는 구간)를 C++가 문서화된 checked 오류로 실행하지 못하면 체인을 끊고 다음 phase를 네이티브 경계 상태(Known C = 정확한 프로브 C)에서 "선언 재진입"으로 시작한다. 선언 phase는 실제 체인 phase와 따로 센다.
4. **checked 오류 증거.** 모든 checked 오류는 `explain_error`가 분류한다. 진단용 복사본(`animation_machine.cpp`의 디스패치 루프만 마지막 PC를 기록, 나머지는 동일, 생산 결과가 오라클)으로 거부 PC를 얻고, 같은 오류 문자열 재현과 "네이티브가 그 PC에 도달" 증거를 요구한다. 상태 보존(전체 public 출력)도 모든 거부에서 확인한다.
5. **typed fixture 1,215개**(저장된 시작 상태에서 네이티브 재생성 후 저장된 digest·ports_sha·final과 일치 확인; 시작 carry = 선언 CCR의 C), 부가로 Unknown carry 연속 실행, 경계 callee로 멈춘 37개의 "through" 흐름, carry-consumer 140개의 consumer 직접 Unknown 실행.
6. **블록 probe 784개**(계약 block 시작 전부, 6 유닛 109/158/174/177/92/74): 네이티브 단일 block(C_in 0/1)과 C++ Known/Unknown 비교. 네이티브 의존 consumer 집합 = C++ 정확 오류 집합 = 계약 consumer 집합.
7. **API 부정 시험**: 유닛별 모든 interior PC × 3 carry, 모든 홀수 PC(2 방식), 모든 block 시작·경계 PC zero-step × 3 carry, RAM 10fe00/10fe40/10fefe 비라우팅 프로브(규약상 5f6xx 대신), 44ade 계산 착지 스윕.

## 결과 (verification.json `checks` 전부 true)
| 항목 | 결과 |
|---|---|
| 자연 노드 | 14,320 / case 290(base 142, rng 142, rng00 6). `match` 8,290, `match-partial` 6,030(guard 0, DIFF 0). base 2,726+1,230, rng 5,264+4,800, rng00 300+0 |
| 유닛 piece | 69,598/69,598 검증. phase 134,764 = 실제 체인 115,998 + 선언 재진입 6,724 + 차단된 블랙박스 12,042 |
| carry | Known C 39,366회 네이티브 C와 일치, 불일치 0(Unknown 91,646은 주장 없음) |
| 연속 vs 체인 | 연속 실행 11,904 일치(체인 대조 11,904); 차단 6,030은 아래 |
| 차단 phase | 12,042 전부 `unsupported animation machine PC`이고, 진단 PC가 네이티브가 실행한 PC(후속 유닛의 callback 진입, 예 31032 324·3e136 500·4bfbc 616·331d8 320·38c36 292·3e1ce 494·5e8xx~5fxxx). 연속 실행은 첫 차단 phase와 같은 PC·같은 오류에서 멈춤을 확인 |
| 자연 guard | 0건(네이티브 guard 없음), 자연 노드에서 unknown-carry 경계·2986 caller-X·interior 착지 0건 |
| typed fixture | 1,215, 재생성 1,215 동일, DIFF 0. 아래 분류 |
| probe | 784/784 ok. C++ carry-out 분류: preserve 366, clear 5, set 5, unknown 408(계약 FLOW_ONLY는 전부 preserve; table 불일치 0; 네이티브 보존인데 C++ Unknown 0). 계약 생산자 10개 전부 C++ Clear/Set 일치(46d08 46d12 484ec 484f2 497a6 497b0 b7bb6 b7bbc b7e64 ea67a) |
| consumer | C++ 정확 오류 35개 = 네이티브 의존 35개 = 계약 35개(U17 6, U18 14, U19 10, U20b 3, N01 2, U20a 0). 오류 문자열 `objects u17|u18|u19|u20b|n01 caller requires known carry`(U20a 없음). carry-consumer fixture 140개 전부 Unknown 직접 실행이 consumer PC에서 정확한 오류(진단 PC = consumer PC) |
| 부정 | 아래 "부정 시험 호출 수" 문단 (DIFF 0) |

부정 시험 호출 수(전부 정확한 오류 + 상태 보존): interior 3 carry 합 — U17 1,452 / U18 1,878 / U19 2,694 / U20a 2,037 / U20b 1,140 / N01 1,593(= interior PC 484/626/898/679/380/531 × 3) → 각 유닛 `unsupported animation objects uNN PC`. 홀수 PC(593/784/1,072/856/472/605 × 2) → `unaligned animation machine PC`. zero-step(block 시작 + 경계 callee + 기록된 child callback PC) U17 330, U18 498, U19 540, U20a 531, U20b 279, N01 222 호출(= PC × 3 carry) 제자리 성공. RAM 비라우팅 프로브 3 PC × 3 carry: `unsupported animation machine PC`, zero-step 성공.

### typed fixture 분류 (1,215)
`match` 787, `match-partial` 8(차단 phase 있음), 기록상 상태 미도달 2(producer-chain 선택 사슬, 시작 상태 없음 — 재현 불가로 세지 않음). guard 및 경계:
- native guard → 정확한 C++ 오류(표 `GUARD_TABLE`, 진단 PC가 네이티브 도달): bank-read-outside-rom → `reached program bank physical span outside ROM` 108; odd-read → `program bus requires even WORD/LONG address` 117; odd-write → `invalid animation machine write size/alignment` 7, → `program bus requires even WORD/LONG address` 5; rom-write → `stage area RNG pointer outside work RAM` 20, → `unsupported animation machine write device` 9; write-unmapped → `unsupported animation machine write device` 2; cpu-exception → `unsupported animation machine PC` 7; read-unmapped → `unsupported program bus device address` 4; odd-pc → `unaligned animation machine PC` 1; step-limit → `animation machine block budget exceeded` 1.
- 의도된 차이(개수):
  - **native-unmasked-address 110**: 네이티브 read-unmapped가 24비트 초과 주소(Unicorn은 68000 24비트 주소 마스크가 없다; C++는 `& ffffff`로 읽는다). 비교 불가로 분류하고 가능한 경우 마지막 block 시작까지의 앞 구간 비교(`guard_prefix`)를 한다. 이때 C++ 결과는 오류 `unsupported program bus device address` 78, `program bus requires even WORD/LONG address` 16, `unsupported animation command or dispatch alignment` 8, `unsupported animation machine PC` 7, `unsupported animation callback target` 1(전부 checked 오류, 완료 0). 대부분 pvc-bank 스윕(109).
  - **checked-callee 23(+through 7)**: 블랙박스 코드를 C++가 네이티브가 실행한 PC에서 거부: `unsupported animation command or dispatch alignment` 14, `unsupported animation machine PC` 8, `indexed animation selected opcode is not04` 1.
  - **interior-landing 2**: `guard-rom-write-uU20a-44aec/44bec` — 44ade 점프 표의 변위 WORD(명령 중간)로 착지. 네이티브는 그 WORD를 명령으로 디코드해 계속(ROM 쓰기 guard), C++는 `unsupported animation objects u20 PC`(계약 결정 2의 의도된 차이).
  - **unknown-carry-boundary 2**: `reach-entry-self-108`, `reach-path-from-entry-109` — 직접 진입한 `dbf2a`(SUBQ.W, C 비모델)가 RTS로 U19 consumer `b7b52`로 되돌아간다. C++는 `objects u19 caller requires known carry`(진단 PC b7b52가 계약 consumer, 네이티브 도달). 선언 상태가 합법적 producer 없이 consumer로 반환하는 경우다.
  - cue wrapper `2986` caller-X(`cue wrapper failure requires known caller X`): fixture·자연 모두 0건(28ae-fail/ok 14개는 전부 일치).
- **직접 진입(entry-self 18 + entry-declared 20 = 38)**: match 29, deliberate:unknown-carry-boundary 1(entry-self), guard 8(cpu-exception→unsupported machine PC 3, rom-write→write device 1, checked-callee 4). Unknown carry 연속 실행: 같음 29, 같은 오류 6, 정확한 `u19` 오류 2, 해당 없음 1.
- through 37(경계 callee 이후 흐름): match-partial 29, checked-callee 7, native-unmasked 1; 재생성 37/37 일치.
- fixture Unknown carry: 같음 653, 같은 오류 393, 정확한 unknown-carry 오류 157(u17 28, u18 58, u19 49, u20b 12, n01 10).

### 44ade 계산 착지 스윕 (D7.W 0..0x697 + 극단값 11개 = 1,699)
착지 PC = `44ae2 + sext(D7.W)`. stop=착지 성공 854(짝수 전부). 짝수 interior 착지 671 → 정확한 `unsupported animation objects u20 PC`(상태 보존) 671/671; 홀수 착지 845 → `unaligned animation machine PC` 845/845; block 시작 착지 173(`unsupported animation machine PC` 172 = 표 대상 이후 미라우팅 callee, `animation machine block budget exceeded` 1 = fffc 자기 점프); 범위 밖 10(`unsupported animation machine PC` 5, `unsupported animation objects u08|u11|u15b PC`). [U] 네이티브 쪽 표는 착지를 stop으로 둔 흐름이라 interior 착지 이후 네이티브 진행(명령 중간 디코드)의 결과는 이 스윕에서 비교하지 않는다(홀수 착지 38개에서 Unicorn 번역기가 abort하여 포크 자식으로 격리, `translator-abort`로 기록).

## 무효화 후보 (수정하지 않음)
G2 PC를 경계/미라우팅 탐침으로 쓰는 이전 시험 후보(grep): `engine/tests/animation_machine_{objects_u05(497a6),objects_u08(44ade,4929e),objects_u08b(44ade,4bfa4),objects_u11(44c62,45174,4be2c),objects_u12(492d0),objects_u13(ea7f4),objects_u14(5208a),objects_u19(492d0,4be2c),objects_u20b(492d0,497a6,4be2c,4bfa4),objects_u01(482c0),objects_u02(443ea),objects_u07(e5bb0..e5ea0),area_clear(1c5ea)}_test.cpp`와 `tools/verify_animation_machine_area_clear.py`(1c5ea). 통합 트리에서 `make -j4 all test`의 결과가 실제 영향 확인이다(아래).

## 재현
`G2_NATIVE=<g2 native run1> G2_OUT=<out> G2_SCRATCH=<scratch> .venv/bin/python tools/verify_animation_machine_objects_g2.py`(약 16분, 작업자 3). 개발용 스위치 `G2_CASES`, `G2_STAGES`는 전체 실행이 아니며 보고서에 `complete_requested_matrix=false`로 표기된다.

## 미확인·한계
- [U] 자연 노드 6,030개가 `match-partial`: 콜백이 후속 유닛(미라우팅) 안이라 노드 전체 연속 실행이 불가하다. 유닛 piece는 네이티브 경계 상태(선언 재진입)에서 실행·비교했다.
- [U] native-unmasked-address 110 fixture의 C++ 결과는 네이티브와 같은지 비교할 수 없다(마스크 주소 읽기를 하는 네이티브 모델이 없음).
- 진단 복사본은 증거용이며 생산 결과가 오라클이다.

## 통합 기록(메인, 2026-10-13)
- [F] 통합 시 검증기 기본 scratch 경로를 `build/objects_g2`로, native 관측기 기본 출력을 `artifacts/animation_machine_objects_g2_native`로 바꿨다(동작 변경 없음). 통합본 검증기 SHA256 `aaa8ad2a2a8e287928cbf9f873b940c32059c724b1f5ea4dfd2ef291fadbcdae`.
- [F] 위 결과는 `4f91481` 기준이다. native 관측 `run1`/`run2` `observation.json`은 바이트 단위로 같고, `run1`을 `artifacts/animation_machine_objects_g2_native`에, `run3` `verification.json`(SHA256 `f6773ae7…`)을 `artifacts/animation_machine_objects_g2_execution`에 복사했다.
- [U] 이후 단위(N02~N32a, H1)가 합쳐진 HEAD에서의 재실행 결과는 별도로 기록한다.
