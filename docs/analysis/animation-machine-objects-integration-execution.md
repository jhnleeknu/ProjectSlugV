# F4 U01–U16 통합 원본 비교 실행

이 검증은 기존 U01–U16, U08b, U15b, U15c의 통합만 다룬다. U17 이후와 새 RNG 실행부는 추가하지 않는다. canonical BE 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 8 MiB다. fixed 코드 CPU 주소와 파일 오프셋은 `<100000`에서 같고, bank window 자료는 실행 중 PVC bank를 적용한다.

## 선언 fixture의 원본 자료 비교

`tools/verify_animation_machine_objects_g1.py`는 각 C++ 단위 test의 `FIXTURES`에서 **입력만** 읽는다: entry, stop, carry class, 16개 register, RAM 변경이다. test의 예상 register·digest와 합성 physical ROM overlay는 사용하지 않는다. 같은 선언 RAM과 register를 원본 ROM의 Unicorn CPU와 public `run_animation_machine` API에 입력한다. C++는 원본 8 MiB 전체를 MS5D v1 kind3의 물리 ROM 리소스로 읽는다. 입력 ROM은 읽기만 하고 새 리소스·결과는 독립 출력에 생성한다.

G1의 기존 immutable `fixtures.json.gz` 중 정상 stop fixture도 SHA-pinned RAM blob에서 재구성해 새 native CPU에서 재실행한다. expensive fixture 검색은 반복하지 않는다. G1 artifact의 native 관측 자체에는 142 seed, 28,715 unit node와 337 typed fixture, U01–U07 시작 681개 도달 근거가 있다. 이 새 suite에서 G1의 전체 node/guard를 다시 검증한다고 주장하지 않는다.

성공 row는 RAM 65,536 byte 전체, 16 register, PC, PVC word 상태, bank와 순서 있는 port event를 비교한다. C++ checked 오류는 API의 transactional rollback(RAM, register, PC, carry class, PVC, bank, port, reads, status 보존)을 확인하고 성공 비교와 별도로 기록한다. declared wait도 별도 경계다. Native guard, TRAP, step limit, translator abort는 실행 범위의 한계로 기록한다. 원본 자료가 합성 test의 자료와 달라 선언 stop에 도달하지 않는 경로를 성공으로 세지 않는다.

C는 소비 분기의 원본 successor와 결과 register/PC를 비교하여 확인한다. G1의 별도 `MOVE SR,D0` probe는 실행 종료 **뒤에만** 수행하고 D0·PC를 복원한다. probe의 C는 diagnostic이며 public carry enum의 equality oracle로 쓰지 않는다. 소비자가 없는 known C 생산은 이 suite에서 추가 확인하지 않으며 기존 bounded unit의 source classification과 분기 fixture 근거가 별도로 유지된다. public Unknown은 원본 full CCR가 아니다.

실행 명령:

```sh
.venv/bin/python tools/verify_animation_machine_objects_g1.py \
  --out artifacts/animation_machine_objects_integration_execution
```

출력이 이미 있으면 덮어쓰지 않고 실패한다. `--limit`은 개발용으로 보고서에 불완전 matrix를 명시한다. 정상 full 입력 matrix는 4,743 row다. 보고서의 `instruction_PC_coverage`는 **원본 native에서 관측한 PC**이며 C++ 전체 block 검증이나 모든 조건분기 coverage가 아니다. 상세 결과는 local artifact의 `execution.json`에 보존하며 추출 자료를 Git에 넣지 않는다.

## 보조 연속 frame과 분할 node 비교

`tools/verify_animation_machine_scheduler_f4.py`와 `tools/animation_machine_scheduler_f4_harness.cpp`는 기존 Claude U15b/U15c combo/diffc의 원본 비교를 durable 도구로 옮겼다. 기존 scheduler artifact SHA256 `c330e597f9585c2595006239be49ab0bcb029f4b5fed5c70ebf872fe91a2b4ff`와 PVC artifact SHA256 `613bd4648d7ed3035620ad1949e1be4c94e4e866635a788a423df6c9650a65fe`를 고정한다. seed 58/59는 PVC 자료를 사용한다. source와 harness hash, 빌드 명령은 새 출력 `provenance.json`에 기록한다.

각 seed의 선언 초기 RAM/register/bank를 SHA digest로 확인한 후 실제 C++ 연속 출력으로 다음 frame을 잇는다. 전체 pass와 node 분할 실행의 최종 상태를 비교하고 native artifact의 frame 시작/끝 digest와 node entry/exit/port digest를 비교한다. 같은 chain의 중간 native 출력 register를 C++에 주입하지 않는다. sound/sprite/palette 대기 해제는 기존 native observer의 선언 host 변경이다. frame head/controller/BIOS IRQ의 자연 실행을 주장하지 않는다. 범위 밖 callback의 checked stop과 rollback은 별도로 기록한다.

```sh
.venv/bin/python tools/verify_animation_machine_scheduler_f4.py
```

이 inherited normal-seed 도구는 보조 diagnostic이다. seed JSON 각각의 observation manifest hash와 모든 오류 의미를 도구 자체가 엄격히 확인하지 않았으므로 독립 인수 PASS로 쓰지 않는다. 엄격한 인수 근거는 아래 RNG 실행과 post-audit다. 전체 seed의 local 출력은 `artifacts/animation_machine_scheduler_f4_execution/diff_results.json`이다. mismatch나 whole/chain 차이가 있으면 도구가 실패한다. scheduler의 ROM guard나 U17+ checked stop은 목표 범위의 성공 완주로 세지 않는다.

## 실행 기록

2026-10-11: 새로운 typed 도구 smoke 15 row를 unmodified 원본 ROM에서 실행해 15개 full state/port 비교가 통과했다. Full 4,743-row matrix와 연속 scheduler 142-seed 검증은 실행 중이다. 최종 수치와 발견 사항은 완료 뒤 이 기록에 추가한다.

### 보조 연속 실행 관측

2026-10-11 final core 통합 상태에서 scheduler의 142 seed 재검증이 완료됐다. 전체 pass 10,498개와 node 79,680개가 원본 기록과 같았고 mismatch 0, 전체/분할 chain 차이 0이었다. 오류 101 seed는 rollback 보존을 확인했다(지원 밖 PC 60, 초기 RNG 포인터 guard 35, odd JSR 5, unaligned PC 1). 원본 기록의 범위 밖을 완주로 세지 않는다.

RNG 초기화 기록의 첫 재검증에서는 142 seed 중 61개가 기록 끝까지 완료됐으며 pass 24,646개, node 169,037개가 같았다. 응답 `00` 변형 6 seed도 pass 844개, node 6,116개가 같았다. 양쪽 mismatch/chain 차이 0이었다. 다만 frozen observer의 `rA` routing inventory는 U01–U16 통합 전 상태여서 27 seed가 예전 "첫 미지원 callback"을 지난 뒤 다른 미지원 경계에서 멈췄다. 이 역사적 inventory를 자동 수용하지 않고 오류 frame의 SHA-pinned 이전 pass dump에서 원본을 다시 실행해 **현재 routing의 첫 미지원 명령 PC**, 같은 오류 node의 entry digest, 이미 완료한 node prefix 일치와 rollback을 확인하는 audit를 추가했다. 결과는 별도 최종 재실행으로 확정한다.

최초 typed serial 실행은 전체 수용 결과로 쓰지 않는다. `d73ca` 직접 진입 fixture의 계약상 Z 전제(D0.W = WORD 10(A0))를 입력 변환에서 빠뜨린 것을 확인했다. C++는 계약 결정 2에 따라 live 피연산자로 Z를 재계산한다. Native 초기 Z도 같은 **입력 조건으로만** 선언하도록 수정했으며 expected C++ 출력은 사용하지 않았다. U04 수정 smoke 15개가 통과했다. 최종 typed matrix는 수정된 입력 전제와 강화된 오류 whitelist/현재 routing evidence를 사용하고 도구·C++ source hash를 시작과 끝에 확인한다.

2026-10-12: RNG 연속 검증의 현재 경계 audit가 완료됐다. 기본 142 seed는 pass 24,646개와 node 169,037개가 같고 61 seed가 기록 끝까지 완료됐다. 지원 밖 PC 75개는 C++가 실패한 **같은 node의** 원본 실행에서 실제 첫 미지원 PC를 확인했다. 이미 완료한 node의 frozen entry/exit/port digest도 모두 같았다. 나머지는 native 끝의 odd JSR 5개와 unaligned PC 1개다. 응답 `00` 6 seed는 pass 844개와 node 6,116개가 같고 2개 완료, 현재 미지원 경계 4개다. 양쪽 mismatch 0, whole/chain 차이 0, 미분류 오류 0이다. 모든 checked 오류는 rollback을 확인했다. 결과는 `artifacts/animation_machine_scheduler_rng_f4_execution/verification.json`이며 실행 도구·엔진 source hash를 실행 시작과 끝에 확인했다.

현재 경계 replay는 이미 비교가 끝난 이전 node의 내부 명령 PC를 dispatcher 시작으로 요구하지 않는다. 실패 node의 index·A6·callback이 일치한 뒤 첫 미지원 PC를 검사한다. 기존 `8c16` palette adapter는 exit 계약의 전체 leaf `8c16..8ca4`를 원자적으로 실행한다. replay도 실제 `8c16` 진입 이후 이 본문만 허용하며, 원본 142-byte SHA256 `40a994baa542e9e5ba8231823912e8237b01e06fcb5e8aa373d081126f5d4702`와 exit 계약 SHA를 각 evidence에 기록한다. IRQ나 leaf 내부 checkpoint 지원을 주장하지 않는다.

Typed matrix의 diagnostic 실행은 4,743 row 중 full state 일치 4,654개, 기존 whitelist 경계 44개, native step limit 8개와 미분류 37개를 기록했다. 이를 수용 결과로 쓰지 않는다. 37개를 다음처럼 원본·계약과 대조했다: U12 직접 진입 N 전제 누락 3개, G1 인공 stack 반환 `76a08`의 known-C 생산자 없는 경로 21개, U02/U06 내부 PC 직접 진입 12개, U07에 문서화된 cue caller X 제한 1개다. U08b `4beec`의 직접 진입 Z 전제도 전체 계약 audit에서 추가했다. U04/U08b/U12 flag 입력 14개 smoke는 수정 후 원본과 전체 상태가 같았다. N/Z는 예상 출력에서 얻지 않고 live 입력 피연산자에서 계약대로 초기화한다. U09 SUBX의 X는 같은 block 안의 SUB가 생산하므로 별도 초기 X를 주입하지 않는다.

G1의 종료 뒤 diagnostic CCR probe `500000`은 native 실행 PC hook을 해제한 뒤 수행한다. 실행 trace와 coverage, 미지원 PC 증거에 probe 명령을 넣지 않는다. 일반 미지원 오류에는 별도 scratch diagnostic 실행부가 `am_error` 시점의 실제 PC만 출력한다. 원본 production 실행부와 이 diagnostic 실행부의 public 상태·RAM·PVC·port 결과가 모두 같은 경우에만 그 PC를 증거로 사용하며, 원본 native가 같은 PC 또는 명시 TRAP 경계에 도달했는지 확인한다. diagnostic 복사본과 빌드 명령은 local 출력에 기록하고 production 소스는 변경하지 않는다.

원본 typed matrix의 인수 gate는 `tools/audit_animation_machine_objects_f4_execution.py`다. native translator abort나 예상 밖 wait/step limit가 하나라도 생기면 실패한다. native step-limit 8개의 정확한 이름, 유일한 G1 flag 전제 위반 입력, 전체 row 수, 현재 도구/source hash, 미지원 실제 PC 증거와 rollback, 단위별 block 분모와 gap을 확인한다. G1 `carry-consumer d73ca ccr=04`는 D0.W=`1`, WORD10(A0)=`2`, CCR=`4`이므로 U04 결정 2의 Z 전제를 위반한다. immutable 입력은 유지하며 `invalid-declared-flag-precondition`으로 제외한다. C++ checked 경계나 원본 실행 equality로 세지 않는다.

RNG의 인수 post-audit `tools/audit_animation_machine_scheduler_rng_f4_execution.py`는 통과했다. pinned observation의 `file_sha256`/크기에 따라 148개 seed gzip을 모두 확인했다. C++에 공급한 MS5D 8개 각각의 physical offset·CRC·payload 길이와 합친 canonical 8 MiB SHA를 확인했다. 142+6개 case 집합, 정확한 경계 분류와 원본 일치 수, 실패 node와 completed prefix 증거 79개, rollback을 확인했다. 결과 receipt는 실행 출력 폴더의 `acceptance.json`이며 실행 보고서 SHA는 `029560b57a24b4b1679f30ce695a40081d76309cea0dc0ea277ba6d655bcf027`다.

F4 실행 도구는 compiler 입력 header hash를 직접 시작 시점에 캡처하지 않았다. 두 post-audit는 별도 앞선 `build/sanitize-u15review/verification.json`에 기록한 152개 header(공개 151개와 internal 1개)의 hash가 현재와 모두 같고 그 앞선 실행의 `all_inputs_unchanged`가 true임을 확인했다. 또한 `9d5aa11` 대비 header worktree diff가 없음을 확인했다. 이는 앞선 기록과 현재 사이의 독립 시간 anchor이며 F4 실행 자체가 초기 header를 hash-pinned했다고 주장하지 않는다.

```sh
.venv/bin/python tools/audit_animation_machine_objects_f4_execution.py
.venv/bin/python tools/audit_animation_machine_scheduler_rng_f4_execution.py
```

Matrix의 native 관측 coverage는 U06 `eb7f2`와 U08b `46928`을 제외한 선언 시작을 포함한다. U06은 134/135, U08b는 164/165이며 이 gap을 C++ 전체 시작 검증으로 감추지 않는다. `eb7f2`는 original-data 목록 경로의 step limit fixture로 별도 기록됐고 `46928`은 입력 `FIXTURES`에 없는 generic block table 행이다. 원본 전체 boot/IRQ나 모든 native 분기/개별 C++ block equality, IRQ 또는 leaf 내부 checkpoint는 이 검증의 주장이 아니다.

새 checkout에서 이 특정 인수 절차를 재현하려면 F4 실행 **전에** `tools/verify_u15_integration_sanitizers.py`로 `build/sanitize-u15review/verification.json`을 생성한다. 이 문서의 post-audit는 검토한 `9d5aa11` header 상태와 정확한 boundary manifest를 대상으로 하므로 header나 선언 입력·경계가 바뀐 후에는 새 검토 없이 PASS를 재사용하지 않는다. Matrix post-audit는 G1 observation SHA `04b4a91dd1b81708305f605d19fda986c88d3cb3b1c0c1e1478f88d4530bd94a`, fixture gzip SHA `28d5baedec1d8e42e7491fac91bb16c0b32e307067e62bdc191721ac5ca92ece`, 모든 G1 초기 RAM·상태 digest와 각 typed test/contract의 실행 기록 hash도 확인한다.

### 최종 frozen matrix와 인수 결과

2026-10-12 최종 전체 matrix 4,743 row가 536.93초에 완료됐고 post-audit도 통과했다. 원본 full-state equality 4,657개, 검토한 checked rollback 경계 77개, 정확히 지정한 native step-limit 8개, invalid declared flag 입력 1개다. mismatch 0, native translator abort 0, 예상 밖 wait·미분류 결과 0이다. 도구 SHA256 `95377f8ba3160aa0798362b72f5e55b5df18fab071ff4e4a459fe54e3bbae6c7`는 실행 시작과 끝에 같았고 C++ source·ROM 불변 검사도 통과했다. `execution.json` SHA256은 `be71ac7a2f690b580dafd397cbefa035bfc08e9eacea8b6777652659d55066e0`이다. `acceptance.json`은 같은 보고서와 explicit manifest를 확인한 별도 receipt다. 결과를 cached row로 대체하지 않고 수정된 최종 입력 전제·오류 정책으로 전체를 새로 실행했다.

77개 checked 경계는 generic 실제 미지원 PC 41개, known-C 생산자가 없는 G1 인공 `76a08` 반환 21개, U02 내부 PC 직접 진입 8개, U06 내부 PC 직접 진입 4개, native odd PC 1개, native odd WORD/LONG 1개, 문서화한 cue caller X 제한 1개다. 모든 경계의 전체 public rollback을 확인했다. 41개 generic 미지원 오류 각각은 production/diagnostic public 결과 equality, 실제 C++ 오류 PC에 대한 native 도달, 현재 dispatcher 부재를 모두 확인했다. 선언 artificial return이나 내부 PC rejection을 정상 게임 실행 failure로 바꾸어 해석하지 않는다.

8개 native step limit은 `u06-eb7f2`, `u06-eba3e-bank2`, `u06-eba3e-bank3`, `u06-eba3e-ram-list`, `u06-eba3e-bank3-short`, `u06-eba3e-hi`, `u06-eba3e-bank4`, `pvc-bank eba3e LONG80(A6)=2`다. 이들은 original-data 목록 경로가 선언 stop에 도달하지 않아 full-state 비교에서 제외된 결과이며 성공으로 세지 않는다. 1개 invalid 입력은 위 G1 `d73ca ccr=04`다. U01–U16(분리된 U08b/U15b/U15c 포함) 계약 시작 분모 2,485개 중 이 matrix의 qualifying native 관측은 2,483개다. 앞서 명시한 두 gap을 유지하며 C++의 2,483 block 개별 equality를 주장하지 않는다.

인수 범위는 이 bounded original matrix와 strict RNG 연속 실행/post-audit다. 정상 scheduler의 142 seed 보조 관측 수치도 보존하지만 독립 acceptance PASS로 합산하지 않는다. 전체 boot/IRQ/BIOS의 자연 실행, 전체 게임, U17 이후나 새 R 단위의 완성은 이번 검증의 주장 밖이다.
