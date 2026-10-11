# scheduler shell F2: 실행부 검증 기록

대상: `engine/src/animation_machine_scheduler.cpp`(SHA256 `1deb3bcc13ed13b061d0d1d0e5980653f5a0c271f14a54d002fb07ef2e87b587`, 17 block: `2aac` `270e` `2716` `271a` + `4fcce` 13), 작업 트리 `metalslug-vf2`(detached `55261ac`).
계약 `animation-machine-scheduler-shell-f2-contract.md`(SHA `65844317…`), native 관측 `artifacts/animation_machine_scheduler_native/observation.json`(SHA `c330e597…`, 도구 `62bb23ff…`).
ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(검증 전후 SHA·mtime 불변). 검증기 `tools/verify_animation_machine_scheduler.py`, 결과 `artifacts/animation_machine_scheduler_execution/verification.json`.
[F]=실행 결과로 확인, [I]=추론, [U]=미확인. native SR은 읽지 않으며 carry는 block 분류다. 프레임 패스는 계약 결정 2~4의 선언 모델이며 BIOS 실행·자연 IRQ·자연 스케줄러를 주장하지 않는다.

최신 통합 결과(2026-10-12)는 아래 “최종 통합 실행”에 기록한다. 앞의 대상 트리·초기 수치 표는 `metalslug-vf2` 단위 스냅샷의 역사적 결과다. 통합 C++는 142 seed 중 59 seed에서 하나 이상의 완주 pass를 검증했고, 전체 native 동등 완주 pass는 10498이다.

## 방법
- [F] 관측 산출물은 불변 입력이다(blob 3,086개 전부 해시 확인, seed 파일 142개는 적재 시 해시 확인). 관측 도구 main은 실행하지 않는다. import는 (a) seed 스냅샷 생성(`seed_snap`), (b) 독립 native 명령 trace(`traced_native`)로 block leader 순서 산출, (c) 4fcda 변형의 기대값 생성(`replay_node`, 새 Unicorn CPU)뿐이다.
- [F] C++ 한 번 = 프레임 패스 한 번(PC `2ac2`, A6 `1008e4`, A7 `1ff000`, stop = LONG `(100820)`; e4a/e74가 아니면 host가 거부). 다음 패스는 직전 C++ 출력에 선언 경계(PC `2ac2`, A6 `1008e4`, A7 SPd, carry Unknown)만 적용해 이어 간다. 각 패스의 시작 digest가 기록 digest와 같음을 실행 전에 단언한다.
- [F] 같은 패스를 node 단위로도 실행한다(`2ac2`→`2abe` 진입, `2abe`→`2ac2` 종료, 머리 node는 stop까지). node마다 진입·종료·port digest를 기록과 비교하고, node 연쇄의 최종 RAM·16R·PVC·port 바이트가 패스 전체 실행과 같음을 단언한다.

## 결과 [F]
| 항목 | 결과 |
| --- | --- |
| 자연 seed 142(자연 137 + release guard 5) | 기록 패스 14,715 중 C++ 완주 패스 **6,296**(22 seed). 완주 패스 모두 시작·끝 digest, 순서 port digest, 패스 전체 = node 연쇄 바이트 일치. dump frame 6,296 RAM 바이트 일치. node 구간 89,850(종료 digest 38,629 일치, 진입 digest 38,765 일치) |
| 완주 seed | 22 seed 중 6 seed(100 101 106 107 110 111)는 기록 400 frame 전체를 완주, 나머지 16은 기록 마지막 패스(BIOS `c00468` 경계 등)에서 멈춘다 |
| 실행 불가 패스 | 136 seed가 C++에서 어느 패스에 checked error(상태 보존, 아래 분류)를 기록한다. 앞의 22 seed 중 16을 포함하므로 22 + 136 - 16 = 142다. 6 seed는 오류 없음 |
| typed fixture | native 18 중 15 실행(270e 4 + boot 2 + pass 9; pass 1개는 host 규칙 기록만), f3-child 3개는 F3b 경계라 제외. 추가: idle ring 예산 초과, boot A7 RAM 밖, 4fcda 변형 20개(seed별) |
| 4fcce 경로 | 13 block 전부 자연 노드에서 도달. 4fcda `7a(A6)` 20개 변형을 독립 native replay와 비교해 RAM·16R·PC·bank·순서 port 일치 |
| carry | 단일 block 탐침(C Unknown/Clear/Set) 결과: FLOW_ONLY `271a` `4fda4`만 보존, 나머지 15개는 Unknown. 정적 감사로 ROM 명령에서 도출한 FLOW 집합과 C++ 표가 일치 |
| API 음성 | 내부 PC 65 → `unsupported animation scheduler PC`, 홀수 82(+3) → `unaligned animation machine PC`, 범위 이웃·4fd0a 형제 변형·범위 밖 20 → `unsupported animation machine PC`, 홀수 operand 5 → `program bus requires even WORD/LONG address`, 홀수 stop → `invalid animation machine RAM/PVC/stop PC`, `4fd8c` 홀수 video 포인터 → `invalid animation machine write size/alignment`. 177건 모두 상태 보존. zero-step 17 start × 3 carry = 51건 |
| 재현성 | 검증기 두 번 실행, verification.json SHA `ddc29c669a3b9fc6c1ec7d8498d4a1fd1bd29566efe07f779a1f2ec799750d3b` 동일, 두 출력 디렉터리 `diff -rq` 차이 없음 |
| `make -j4 all test` | 종료 코드 0 |

## typed fixture
- `270e-depth0/-zombie/-zombie-wrap/-a5-relative`: 종료 상태(RAM·16R·PC·bank·PVC 워드, port 없음)가 기록과 일치, 독립 trace 순서의 split 사슬 일치, `2716` 포함.
- `boot-2aac-e4a/-e74`: LONG `104ca4`=A7, A6=`100820`, A5=`108000`, A0=stop, A7−4, LONG(A7−4)=`2ac2`. `2ab8`에서 split한 결과 일치. C=Unknown.
- `pass-static8`, `-e74`: node 6개, 끝 상태 일치. `pass-gate-wait-released`: `47af0`에서 Waiting(PC·A7 보존), 선언 해제(BYTE `107ded` bit7) 뒤 같은 패스 완주, 끝 상태 일치. `pass-gate-wait-not-released`(WORD `107dea`≠0): 같은 PC·A7로 다시 Waiting.
- `pass-self-delete-base-long-spd`: 일치. `-offset`(`104ca4`=SPd−0x20): A7≠SPd−4로 종료, 끝 상태는 기록과 일치(host head 검사가 거부할 사례). `-zero`: `program bus write requires RAM mirror units`(native는 fffffc push 접근 오류).
- `pass-head-callback-rejected`: host 규칙(LONG `100820`=`270e`)이며 C++ API는 stop을 인자로 받아 이 값을 읽지 않는다. `pass-head-ring-unchecked`: stop `e4a`를 선언하면 링이 컨트롤러 `1008e4`(`c52a`)로 계속되어 `unsupported animation machine PC`. 추가: 모든 node idle + 머리 없음 → `animation machine block budget exceeded`.

## 자연 seed 분류: native 정지 vs C++ 오류 (136 seed)
- [F] 모든 오류는 `unsupported animation machine PC`(실행부 없는 callback)이며 패스 전체가 보존된다. 예외: deadbeef guard 5(`animation fade card odd JSR target`), 홀수 `47c05` 1(`unaligned animation machine PC`).
- [F] 'node' 종류 실패 104 seed(frame 0, 기록 패스 완주 73 + native 정지 31)는 모두 native `rA`=false(실행부 없음) callback이다: `b4d7e` 10, `e5120` 11 등 전체 목록은 `failure_classes`.
- [F] BIOS `c00468` 경계 18 seed: C++도 같은 partial node(`48090` 16, `47af0` 2)에서 멈추며, 마지막 패스의 stop을 `c00468`로 주면 C++이 그 주소에 도달한다(`cpp_reaches_native_stop_address`).
- [F] RNG `49a58` guard(ROM 쓰기 41 seed): C++은 35 seed에서 RNG node보다 앞선 실행부 없는 callback(`dbdb6` 13 등)에서, 6 seed에서 partial node(`7086a` `7090a` `b4d7e`)에서 `unsupported animation machine PC`로 멈춘다. RNG 포인터 규칙 자체는 이 단위의 C++가 아닌 F1c 규칙이다.
- [F] `unsupported-bank-mapping` 2 seed: partial node `eb7b6`.
- [F] 검증하지 못한 부분: C++이 첫 실패 패스 이후를 실행하지 못하므로 그 seed들의 기록 패스 8,419개(첫 실패 패스 포함)는 C++ 비교 대상이 아니다(실패 이전 node는 기록과 일치).

## 계약·관측 불일치 (계약 수정 없음)
1. [F] 계약 "탐침 120 frame 동안 pool zombie 516회"는 본 관측에서 자연 zombie 0회다(`2716`는 typed fixture로만 닿는다; native 관측 `F2-9`).
2. [F] 계약 "패스 가능 22 seed, 8개는 120 frame 전부"는 22 seed 완주 패스 6,296으로 확인(6 seed 400 frame, 16 seed 기록 BIOS 경계까지).
3. [F] 4fd8c의 `MOVEM.W D3-D4,(A4)`는 C++가 `3c0000` size 4 port 1건, native가 WORD 2건(3c0000/3c0002)이다. 검증기는 4fcce/4fcda node에서만 둘을 대응시켜 digest를 비교한다(map_transfer 관례).
4. [F] native 관측의 `rA` 표시는 관측 시점 라우팅 기준이라 현재 C++ 라우팅과 다를 수 있다(참고용).

## 기존 검증기·시험의 영향 (수정하지 않음)
- `tools/verify_animation_machine_fade_card.py` 472행 `dispatcher_entry_2aac_unsupported`: `2aac`는 이제 block 시작이므로 기대(`unsupported animation machine PC`)가 무효다.
- 메인 트리의 `engine/tests/animation_machine_fade_card_test.cpp` 135행 `outside[]`는 `2aac` `2ab2`를 비라우팅 PC로 쓴다(vf2 작업 트리의 시험은 이미 제거됨). 그 밖의 0x270e/0x2710/0x4fcce 리터럴은 node에 저장된 callback LONG 또는 10진수 상수이며 영향 없다(파일별 개수는 `other_literal_uses_per_file`).

## 한계
- 제어된 fixture이며 선언 프레임 모델이다. 프레임 머리 `e4a/e74`·컨트롤러 `c52a/c66a` 본문은 실행하지 않는다. `104ca2`의 소비자는 [U].
- 하나 이상의 완주 패스가 있는 22 seed 외의 120 seed는 첫 callback 실행부가 생길 때까지 패스 전체를 검증하지 못한다. 22 seed 중 16도 마지막 기록 패스의 오류 경계를 남긴다. F3b(`e94fe` 이후), 나머지 long tail callback은 다른 단위다.
- Waiting은 typed fixture(47af0)만 실행하며 자연 seed는 Waiting 0건이다(sound `3aea`, sprite `cda4`는 미실행).

## 통합 검증 (2026-10-11)

단위 스냅샷 원본 observation/blob SHA는 그대로 보존하고, 통합 SOURCES 전체로 public API harness를 새로 빌드한다. 선언 pass 모델의 PC/A6/A7 reset 및 104ca4 host-write는 기존 한계를 유지한다. native seed 결과에서 성공 pass가 있는 seed와 오류를 기록한 seed는 중복될 수 있으므로 두 집합의 합을 전체 seed 수로 해석하지 않는다.

### PVC 관측기 경계 이동

58·59 시드는 기존 원본 관측기의 bank 2/3 전용 모델이 `eb7b6` 내부 `eba5c`의 `MOVE.W D1,2ffff2` 쓰기에서 중단했다. 통합 검증은 이미 보존된 확장 bank 원본 관측(`animation_machine_pvc_banks_native`, observation SHA `613bd4648d7ed3035620ad1949e1be4c94e4e866635a788a423df6c9650a65fe`)의 120 frame 기록을 사용한다. 두 관측의 seed 시작 PC/RAM/16개 register/bank/state digest, 첫 5개 완주 node의 entry/exit/ports, 여섯째 partial node의 entry가 동일함을 먼저 확인한다. 기존 bank guard는 삭제된 오류가 아니라 관측 모델 한계의 superseded 근거로 report에 남긴다.

새 120 frame 기록은 C++ 전체 pass와 node 연쇄의 RAM/register/bank/ports digest로 직접 비교한다. 새 기록에서 `self_delete` 샘플링 메타데이터가 없으므로 두 seed의 부가 trace-hook 표본만 실행하지 않는다. 전체 start coverage와 carry 분류 assertion은 나머지 seed 및 typed fixture에서 그대로 요구한다. 실제 전체 pass/node 비교는 생략하지 않는다. `eba3e` C++ block이 두 PVC 쓰기를 묶어 `eba78`까지 실행하므로, `eba62`를 public stop으로 만든 것처럼 주장하지 않는다.

## 최종 통합 실행 (2026-10-12)

명령: `.venv/bin/python tools/verify_animation_machine_scheduler.py` (개발 filter 없음). report SHA `d1ac590d286ae584897ac76802b13890b73e728fd7061b44330cce3c4127a6d0`; 실행 후 input 104/104 및 artifact 13/13 SHA가 현재 통합 트리와 일치했다.

- 142 seed, native 동등 완주 pass 10498. 각 pass의 전체 실행과 실제 C++ node 연쇄가 같으며, 종료 상태 및 순서 port digest를 원본과 비교했다. node 구간 180356, 진입 digest 79781, 종료/port digest 각 79680, 저장된 dump frame RAM 바이트 비교 6946.
- 하나 이상의 완주 pass가 있는 seed 59, 어느 pass에 오류를 기록한 seed 101, 두 집합의 교집합 18: 59 + 101 - 18 = 142. 기록 끝까지 오류가 없는 seed는 41이다. 전체 엔진의 모든 seed를 지원한다는 의미가 아니다.
- typed/추가 fixture 20, API 음성 177, zero-step 51 PASS. PVC 확장 원본을 사용하는 58·59는 각각 120 frame을 완주·비교했으며 두 native 관측의 기존 prefix 일치도 확인했다.
- `native_counts`는 최초 관측의 역사적 수치다. 별도 `effective_native_counts`는 PVC 확장 58·59를 반영한 native 기록의 전체 pass 14953/완주 pass 14888을 제공한다. 이 native 수치를 C++ 동등 완주 10498과 혼용하지 않는다.

이 결과는 보존된 native 관측 및 필요한 원본 opcode trace와 현재 통합 C++의 비교다. BIOS/자연 IRQ/자연 scheduler 실행을 주장하지 않는다. 원본 ROM과 기존 관측 산출물은 수정하지 않았다.
