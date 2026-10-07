# Stage sound 초기화의 원본 caller와 record 필드

## 원본과 범위

Canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 이 문서의 ROM CPU 주소는 첫1MiB 고정 영역으로 canonical 파일 offset과 같다. RAM/MMIO는 별도 주소다. 주소·상수는16진수, 개수·그룹 번호는10진수다.

`tools/inventory_stage_sound.py`는 `[47a1c,47a94)`, `[3af8,3c08)`, `[3c84,3c8a)`, `[3d44,3d54)`의 명시된 창 전체를 bounded decoder로 보존한다. 첫 RTS를 자동 routine 끝으로 취급하지 않는다. 총108 instruction row이며 창을 넘는 불완전 명령은 decoder의 dc.w 표시로 남기는 방식이다. 이번 창은 완전한 instruction candidate로 decode됐다. 이것은 구문 목록이며 전체 sound 처리의 분석·실행 완료가 아니다.

## 확인된 caller 순서

메인이 원본을 확인한47a1c는 LIVE A6+76의 record pointer를 읽어 record+10 word를 D0.lowword에, RAM10d686의 이전 word를 D1.lowword에 가져온다. MOVE.W는 두 레지스터 상위16비트를 보존한다. 다음47a28은 비교 전에 새 word를 RAMd686에 저장한다.

47a2e에서 이전 값과 같으면47a6a로 이동한다. 새 값이10fe 또는19c1이어도 각각47a36/47a3e에서47a6a로 이동한다. 새 값19c0은47a46에서47a64로 이동해3d44를 호출한다. 나머지는47a4a에서3af8 word enqueue를 호출한 뒤47a50에서47a6a로 이동한다. 이 분기는 초기 선택 command만 건너뛰는 것이며 아래 공통 sequence는 실행한다.

47a6a 이후는 D0.word에1890/1891/1892를 차례로 넣고 매번3af8을 호출한다. 이어3c84가 RAM104d7e.byte를0으로 만들고,3d44를 호출한 뒤47a94 후속 경계로 진행한다.3d44는 D0.byte=08로3ac8을 호출한 뒤 D0.byte=20으로3ac8에 tail branch한다. 여기서 byte/word store만으로 일반 primitive의 최종 full registers를 추정하지 않는다. Queue가 대기하면 caller의 여러 호출을 중간 상태에서 이어야 하므로 이 순서를 하나의 즉시 완료 동작으로 축약하지 않는다.

47a54..47a64 앞의 별도 block에는 MOVEQ40, JSR3d58, JSR4814e, BRA47a6a가 있다. 시작47a1c의 명시된 intraprocedural branch graph에서47a54/47a56/47a5c/47a60에 도달하는 edge는 없다. Script는 calls가 정상적으로 다음 명령으로 복귀한다고 가정하고 이를 확인한다. 이 결과는 다른 외부 entry·callee의 임의 indirect transfer까지 불가능하다는 증명이 아니며, 해당 block의 raw 명령은 계속 보존한다.

## Stage catalog의 실제 word10

새 바이너리를 만들지 않고 기존 `StageCatalog` MS5D19그룹을 소비할 예정이다. 목록 도구는 같은 canonical index474f4의19 pointer와 `pack_stage_catalog.decode_group`을 사용해59 record를 확인한다. 각 record의 길이·CPU/ROM offset·raw SHA와 offset10의 BE16 두 byte를 기록한다. 이 필드의 값·분포를 music 이름이나 자연 사용 빈도로 해석하지 않는다.

| word10 | Record 수 |
| --- | ---: |
| 19c0 | 11 |
| 19c1 | 6 |
| 19d0 | 13 |
| 19d1 | 2 |
| 19d2 | 2 |
| 19d3 | 3 |
| 19d5 | 7 |
| 19d7 | 8 |
| 19d8 | 1 |
| 19d9 | 2 |
| 19dd | 1 |
| 19de | 3 |

총12개 값이며 canonical record에는10fe가 없다. 원본 branch에10fe가 있다는 사실과 이 catalog의 값 분포는 분리한다. 그룹별 분포는 `artifacts/stage_sound/distribution.md`와 report의 `groups`에 기록했다. 그룹9..15는 빈 그룹이며 나머지 source record를 원시 그대로 확인했다. 일반 resource 또는 host가 제공한 record 값의 범위를 이12개로 제한하는 의미 계약은 아직 세우지 않는다.

## 재생성과 근거

```text
.venv/bin/python tools/inventory_stage_sound.py
```

`artifacts/stage_sound/report.json` SHA256은 `a0c09ec27c02f58cd0bd212843b06024457f6470ba83c0654474ce9bed6013b4`, `inventory.asm`은 `bcafe8ab992cc62aea9ad257852933b5149fc312d41e75d8cfbf4a22414bd25a`, `distribution.md`는 `24a44cf2f492725b9bfa22657b6017ac8156ade10331402a755b11a8f6cf9f8a`다. 전체 source SHA를 확인했고 원본 code/data를 수정하지 않았다. 이 중간 artifact에는 raw 명령·record field evidence가 있으며 ROM/추출 게임 데이터의 Git 추가는 하지 않는다.

## Caller API와 continuation

`engine/include/ms5/stage_sound_initialization.h`와 `engine/src/stage_sound_initialization.cpp`의 `initialize_stage_sound(ram,catalog,external_status,state,external_reads,error)`는 `StageSoundState`의 full D0/D1/D3/A6, next_pc/phase, word/byte pending을 입력·출력한다. RAM은 정확히64KiB이며 A6는 짝수 CPU RAM 주소이고 전체c4바이트 object span이 RAM 안에 있어야 한다. D3와 A6를 보존하며 MMIO write는 없다. 다른 registers·CCR·CPU stack은 공개 API 결과가 아니다.

Fresh phase0은 PC47a1c와 idle pending을 요구한다. LIVE A6+76 pointer를 기존 catalog record의 `source_cpu_address`와 대조하고 그 record의 BE16 offset10을 읽는다. 매칭 payload는18바이트 이상이고 짝수 first1MiB 주소·범위를 만족해야 한다. 이어 이전 d686과 비교하기 전에 새 값을 저장한다. Caller는 input D0/D1 상위16비트를 보존하는 MOVE.W 결과로 시작하며 이후 word/byte 생산 primitive의 full register 결과를 승계한다.

| Caller phase | 현재 생산 단계 |
| --- | --- |
| 1 | 선택한 초기 word의 overflow byte 대기 |
| 2/3 | 19c0 초기08/20 byte 생산 |
| 4/5/6 | 공통1890/1891/1892 word 생산 |
| 7/8 | 4d7e clear 이후 마지막08/20 byte 생산 |
| 9 | PC47a94 완료 경계 |

Phase1..8의 대기 PC는3aea다. Word 단계는 kind1/phase1또는2 captured overflow 상태를, byte 단계는 waiting과 command/tail/next를 보관한다. D0.byte와 D1.word는 captured command/next에 일치해야 하며 해당 단계에 사용하지 않는 pending은 idle이어야 한다. 초기 byte 대기의 D0.word는1908/1920, 마지막 byte 대기는1808/1820이어야 한다. 공통 word overflow 대기는 D0.word의 상위 byte18을 검증한다. 완료 phase9의 재호출은 거부한다.

대기 재개는 captured 생산부터 이어가며 record pointer·catalog·이전 music 비교를 다시 읽지 않는다. 이후 남은 단계는 같은 호출에서 진행할 수 있다. Word resume 자체는 external read가 없지만 뒤의 새 word enqueue는 조건부 external read를 할 수 있으므로 caller는 그 호출 전체의 읽기 수를 누적해 반환한다. External status는 주어진 byte이며 실제 장치 timing 모델이 아니다. 마지막 byte 생산까지 완료하면 D0.lowword는1820이고 D0 상위16비트를 보존한다. D1.lowword는 마지막 byte의 next index이며 D1 상위16비트와 full D3/A6를 보존한다.

Candidate RAM/state/read count에서 순서대로 수행하고 마지막에 commit한다. 잘못된 object span·continuation·catalog pointer나 중간 생산 뒤 늦은 queue 오류는 호출 전 RAM/state/external_reads를 보존한다. 이미 성공 반환한 이전 대기 호출의 변경까지 되돌린다는 뜻은 아니다. 초기 lookup 이후 API continuation에는 catalog를 사용하지 않는다. CLI는 모든 호출에서 catalog를 항상 로드하므로 API의 조건부 resource 사용과 구분한다.

## CLI

```text
build/step_stage_sound_initialization --state PC D0 D1 D3 A6 PHASE [--word KIND PHASE LOW CURSOR COMMAND TAIL NEXT] [--byte COMMAND TAIL NEXT] EXTERNAL INPUT_RAM OUTPUT_RAM CATALOG_DIR
```

옵션은 positional 입력 앞에서 조합할 수 있고 duplicate·unknown option·누락 값은 거부한다. `--state`가 필요하며 fresh는 PC47a1c/phase0, wait는 PC3aea와 해당 phase·captured word 또는 byte 옵션을 사용한다. 정수는 unsigned decimal 또는0x hex다. JSON은 `next_pc/phase/d0/d1/d3/a6/external_reads`, word의 kind/phase/low/cursor/waiting/command/tail/next, byte의 waiting/command/tail/next를 반환한다.

CLI는 exact RAM 크기와 input/output/catalog dir 및20개 catalog MS5D 파일의 canonical path/inode alias를 검사하고 매번 `load_stage_catalog`를 호출한다. API 성공 후 RAM output만 저장하며 port 파일은 없다. 다음 호출은 실제 output RAM과 full exposed registers/captured pending을 승계한다.

## Primitive와 caller 검증

일반3af8 full D0/D1 producer는 `artifacts/sound_word_registers/verification.json` SHA256 `abc5c9deeec4e3bcc761389c2bdd1406fa8516fdf918a2ef867502bb188ec798`에서2,525 native/34 negative/64 external reads/28 actual CLI carry/MMIO0을 통과했다. 기존 RAM/pending API 회귀2,241/25도 유지했다. 세부 범위는 `sound-word.md`에 기록한다. 이 수치를 stage caller 전체 통과 수치로 합산하지 않는다.

원본47a1c→47a94 비교 보고서는556조건/오류50조건, external reads46/MMIO쓰기0을 기록한다. Canonical59레코드와12개 대기 하위단계를 모두 확인했다. 실제CLI승계8개와 앞선 구역 초기화CLI→같은native context 연결2개가 포함된다. 보고서 SHA256은 `74d5eda9bdc667ff3590807b5ef1dd8e63a389abddec62a34b205335f9aa2b80`이며 시작·끝 바이너리 SHA256 `a9a7cca1c4b8fbee5e3ebaf80ef19db2c8594c12d57c5400964ad5bf380df882`는 메인의 현재 파일 확인과 일치한다. 원본 고정ROM도 불변이다.10fe는 canonical레코드에 없어 C++합성 단위검사로만 확인했으며 원본 도달을 주장하지 않는다.

대기 해제와 대기 중 record pointer/d686 변경은 명시적host입력이다. 재개는 기존 record를 다시 조회하지 않지만 뒤따르는 새 word enqueue는 외부 상태를 새로 읽을 수 있다. 다른 CPU레지스터/CCR와 자연IRQ일정은 계약 밖이다. 전체make는Python125/C++97/경고0으로 통과했다. 로그 `artifacts/stage_sound_initialization_build_test.log`. 공유코어 변경 뒤 기존prelude 원본235/오류50 회귀도 메인이 실행해exit0을 확인했다. 최신 회귀 보고서SHA256 `f9f3a9cc50175db1ca4c5c5111b7f954dafb8abb17eb811e0a52bcc13fabbe5e`.

47a94 이후의 scene script 전달, 일반 nonzero script, 자연 IRQ/scheduler·audio hardware timing·stage gameplay는 미완료다.
