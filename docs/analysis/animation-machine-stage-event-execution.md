# stage event F3a: 실행부 검증 기록

대상: `engine/src/animation_machine_stage_event.cpp`(SHA256 `2ddae53ed0857c04e024747eb63baa23b5c51afefb4cd8f8a1d71d2ebdc7aa67`)와 `animation_machine_cleanup.cpp`의 43e34 case(SHA `0471d9ba…`), 작업 트리 `metalslug-vf3a`(detached `177cb28`).
계약 `animation-machine-stage-event-f3-contract.md`(SHA `bba91217…`), native 관측 `artifacts/animation_machine_stage_event_native/observation.json`(SHA `44836842…`, 도구 `ae0840bb…`).
ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(검증 전후 SHA·mtime 불변). 검증기 `tools/verify_animation_machine_stage_event.py`, 결과 `artifacts/animation_machine_stage_event_execution/verification.json`.
[F]=실행 결과로 확인, [I]=추론, [U]=미확인. native SR은 읽지 않으며 carry는 block 분류다.

## 방법
- [F] 관측 산출물은 불변 입력이다(blob 3,189개 전부 해시 확인). 검증기는 관측 도구를 실행·import하지 않는다. 예외 하나: 자연 node의 입력 상태가 digest로만 기록된 곳에는 스케줄러 관측 도구의 `SeedRun`을 **seed 상태 생성기로만** import한다(F3 replay hook을 C++ 실행으로 교체, 도구 수정 없음). 재생성한 입력 digest가 기록 digest와 같아야 C++를 실행한다.
- [F] C++ 실행은 `run_animation_machine` 한 번 = node 한 번(PC 2ab8, A6=node, A7=SPd, LONG 104ca4=SPd, stop 2ac2 또는 e94fe). 각 split phase는 직전 C++ 출력에서만 이어가며 native 입력은 단언만 한다(주입 없음). 연속 실행과 split 사슬, native 기록이 일치해야 한다.
- 배치 harness를 쓰며 단발 harness와 같은 요청 6건의 출력이 같음을 확인했다(`harness_equivalence_cases`).

## 결과 [F]
| 항목 | 결과 |
| --- | --- |
| typed 조건 | 560(비guard 443 + guard 117). split phase 23,014회 중 비guard·guard 앞부분 22,864 phase가 native phase 기록과 일치(16 register, PC, RAM SHA, PVC 이미지(정규화 bank 2워드 제외)+bank 값, port SHA, 외부 읽기) |
| 연속/split | 443개 모두 연속 = split 사슬 = native 연속 기록. 선언 A7 일치 403, 경계 stop(e94fe 등) 20 |
| 자연 node | 9,613(e9150 134, e9176 9,479): 입력 digest 9,613 일치, 출력 digest 9,613 일치, 순서 port digest 9,516(2ac2 종료) 일치, e94fe 종료 97. dump된 856개는 RAM·PVC·port 바이트 일치 + 실제 경로 기준 전체 split(33,020 phase) 일치, 나머지 8,757은 leader 하나에서 split한 결과가 연속 실행과 일치 |
| carry | consumer e9248/e9258의 Known C(49392 반환)가 native 분기 경로와 1,712+802회 일치. flip 대조 802회(Clear/Set 입력 모두), Unknown 진입은 정확히 `stage event caller requires known carry`(802회). 단일 block 탐침(C=1·2) 33,542회가 FLOW_ONLY 60개(consumer 2개 포함)를 정확히 재현 |
| API 음성 | 내부 PC 428 → `unsupported animation stage event PC`, 홀수 562 → `unaligned animation machine PC`, 범위 이웃·F3b PC 21개·범위 밖 PC → `unsupported animation machine PC`, 총 1,034건(상태 보존). zero-step 134 start × 3 carry = 402건. native 진입 탐침 1,124와 1:1 대응(`entry_probe_map`) |
| 계산 PC 정책 | e97e0 표 밖 연산자 94개: 10개는 block 시작에 닿아 실행, 84개는 거부(contract 결정 2와 일치, 76이 아니라 84. 아래 불일치 참조) |
| 결정 3(묶음) | e98ea의 복귀 LONG이 e9396/e939e/e94c0/e96b0이면 분기를 같은 block에서 평가하고 갈래(e9428 e939a e93a2 e96b4 e96b8 e94c4 e9768)로 이동함을 typed `eval-return-*` 38개로 확인. 6 PC 직접 진입은 거부 |
| 재현성 | 전체를 두 번 실행해 verification.json SHA `070c665d4cdb6b3a853fbcceac8d94a0e1a7ec29e2ca98f9b226bd767d4d2f89` 동일, 두 출력 디렉터리 `diff -rq` 차이 없음 |
| `make -j4 all test` | 종료 코드 0 |

## native guard → C++ 오류 문자열 (117건)
| native 종류 | 건수 | C++ 오류 문자열 |
| --- | --- | --- |
| `unsupported_code_target`, 홀수 PC | 1 | `unaligned animation machine PC` |
| 〃, 대상이 F3a 범위 안 비start(e97e0 표 밖 a3.. 내부, e94c8) | 24 | `unsupported animation stage event PC` |
| 〃, 대상이 7개 범위 밖(e98ee 이후, F3b 경계 PC, 잘못된 복귀 LONG) | 78 | `unsupported animation machine PC` |
| `unsupported_odd_data_access` | 5 | `program bus requires even WORD/LONG address` |
| `step_limit` | 2 | `animation machine block budget exceeded` |
| `unmapped_or_protected` | 4 | ROM·bank창 쓰기 2: `unsupported animation machine write device`; RAM 아래 push: `program bus write requires RAM mirror units`; 스트림 500000 읽기: `unsupported program bus device address` |
| `unsupported_data_device`(3c0000) | 1 | `unsupported program bus device address` |
| `unsupported_TRAP`(4d7f0, 입력 callee 안) | 1 | `unsupported animation machine PC`(같은 비라우팅 PC에 도달) |
| `unsupported_PVC_read_or_write`(2ffff0 읽기) | 1 | **오류 없음**(의도된 차이) |
- [F] 모든 오류는 같은 split 구간에서 발생하고 RAM·PVC·port·16R·PC·carry가 보존된다(다른 carry 두 값으로도 확인). native 예외 rollback 동등성은 주장하지 않는다.
- [F] 의도된 차이 8건(`native_guards_checked_API[].classification`): bus error ↔ checked error 층 차이 5(ROM 쓰기 2, 스택, 비매핑 읽기, device 읽기), TRAP 경계 ↔ 비라우팅 PC 1, PVC 레지스터 페이지 읽기를 C++ 버스가 모델링해 실행을 계속하는 경우 1(native는 거부).

## 계약·관측 불일치 (계약 수정 없음)
1. [F] 표 밖 연산자 중 거부는 76이 아니라 84(94−10): 18은 block 내부 명령 시작, 5는 명령 내부, 61은 범위 밖.
2. [F] 연산자 8c는 클래스 12바이트 합이 아니라 앞 8바이트(10de30..37) 합이다(관측 `eval-8c-*`, C++ 일치).
3. [F] 계약의 "자연 node 11,391회"는 142 seed 기준이고 본 관측은 137 자연 seed의 9,613회(e9150 134, e9176 9,479)다.
4. [F] 관측 입력 중 `engine/src/animation_machine.cpp`는 관측 이후 F3a 라우팅이 추가되어 SHA가 다르다(스케줄러 rA/rB 표시용 입력, 허용).

## block 범위
- [F] 134 start 전부 typed 또는 자연에서 실행. 자연 lead 집합에 없고 typed 고정자료로만 닿는 start 63개(평가기 slot·연산자, 1a944, 4851e 등; 목록은 `block_starts_only_typed_fixture`).
- 대기(wait)는 F3a 경로에 없다(모든 phase status 0).

## 기존 검증기·시험의 영향
- `tools/verify_animation_machine_scene_update.py` 718·732행: 1a910/1a912를 비라우팅 이웃·stop으로 쓴다. 1a910은 이제 block 시작, 1a912는 내부 PC(`unsupported animation stage event PC`)이므로 기대가 무효다(수정하지 않음).
- 같은 파일 65행, `animation_machine_scene_update_test.cpp` 791행(1a910은 범위 끝 배타), `animation_machine_stage_entry_test.cpp` 637행(e9150은 node에 저장된 LONG)은 영향 없다. `make test` 통과.

## 한계
- 제어된 fixture이며 자연 스케줄러·IRQ·BIOS 실행을 주장하지 않는다. 비dump 자연 node 8,757은 digest(상태·port)와 단일 split로 비교한다(바이트 비교는 dump 856개와 typed). 게임 의미는 [I]/[U]다. F3b(e94fe 이후)는 실행부가 없다.

## 통합 경계 정렬 (2026-10-11)

F3a 단위의 원본 관측 SHA는 그대로 보존한다. F3b 시작점으로 들어가는 역사적 거부 조건은 통합 후에도 원본 guard PC까지 C++를 실제로 연쇄 실행하고, guard phase를 포함한 원본의 모든 register/RAM/PVC/ports/bank/external-read snapshot과 비교한다. 그 이후의 통합 C++ 실행 결과는 별도 suffix 결과로 기록하며 원본 동등성을 주장하지 않는다. 해당 시작점의 실제 명령 동등성은 F3b typed 검증이 담당한다.

21개 역사적 F3b 주소 및 14개 범위 이웃은 삭제하지 않는다. 새로 지원되는 시작점은 zero-step 출력 보존과 실제 API 실행 결과로 superseded 항목에 기록한다. 내부 PC는 정확한 ops 오류, 8개 TRAP는 기존 machine 오류를 유지한다. 이는 API 경계 변경 검증이며 원본 비교 숫자에 추가하지 않는다.

자연 seed 재생성은 보존된 원본 관측의 `frames_done`를 실행 범위로 사용하고 `extend=False`로 고정한다. 새 U 실행부의 routing coverage 증가에 따라 원본 observer의 `covered_prefix`가 120 frame을 400 frame으로 자동 확대하지 않도록 하는 범위 정렬이다. CPU 상태·중간 RAM 결과는 주입하지 않으며 각 원본 node snapshot/digest 비교는 유지한다. F3b는 원본 scheduler seed의 frame 수와 stop reason도 확인한다.

최종 통합 실행 (2026-10-12): `.venv/bin/python tools/verify_animation_machine_stage_event.py`, 개발 filter 없음. typed 560 = 동등 443 + guard 117, 원본 phase 비교 22870, 새 F3b로 superseded된 guard 6개는 원본 guard snapshot까지 직접 비교했다. natural node 9613, API 음성 1020, zero-step 402 PASS. report SHA `542a78105a6796eb31efabcf57ca97b140bad05d4a47e0e88fe5ccf4684910f3`; 실행 후 input 103/103 및 artifact 13/13 SHA 일치. 원본 117개 guard를 전부 성공 실행으로 해석하지 않는다. 보존된 원본 관측과 현재 통합 C++의 새 비교 결과이며, BIOS/자연 IRQ/자연 scheduler 실행 한계는 유지한다.
