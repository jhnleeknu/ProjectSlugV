# 애니메이션 전체 실행 API 재사용 감사

## 범위와 원본

이 문서는 기존 C++ API·테스트와 원본 `49fc6`의 차이를 조사한 재사용 목록이다. 전체 애니메이션 실행 구현·검증 완료 보고가 아니다. 기준은 `docs/GOAL.md`와 `animation-full-register-boundaries.md`다.

원본은 `extracted/program/maincpu.decrypted.be.bin`, 8,388,608 bytes, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 고정영역 주소는 CPU 주소=ROM 파일 오프셋이다. `load_verified_program`으로 해시를 검증한 원본 bytes를 메모리에서 읽고 dispatch의 `6000 disp16`과 해당 명령을 대조했다. ROM·기존 artifact·소스는 수정하지 않았다. 주소·명령은 정적 사실이며 새 전체 실행 관찰을 수행했다는 의미는 아니다.

## 기존 API와 재사용 경계

| API / 선언 파일 | 현재 보장 | 전체 `49fc6`에서 남는 차이 |
|---|---|---|
| `step_animation(ram, object_offset, script, script_base, carry, error)` / `engine/include/ms5/animation_step.h` | 00/04/08/28, 전체 64KiB RAM·반환 carry, 실패 시 RAM/carry 보존 | 레지스터 입력·출력, A5, PVC 순서, 실제 bank 상태, pending이 없음 |
| `step_animation_with_data(..., regions, carry, error)` / 같은 헤더 | 위 subset + 0c/10/14(선택자1d/1e), 명시적 fixed-ROM 조회창 | 다른 14 callback·나머지 opcode 미지원. 전체 레지스터·bank/pending도 없음 |
| `decode_animation_draw(ram, object_offset, operand, result, error)` / `animation_draw.h` | `AnimationDraw { skipped, d0,d1,d5,d7 }`, 일곱 operand bytes에서 producer 인자 계산 | D2/D3/D4/D6/A0/A1, skip 직전의 레지스터, producer 반환 후 상태를 표현하지 않음 |
| `initialize_sprite_queue(ram,error)` / `sprite_producer.h` | ccd6 RAM 초기화 | 애니메이션 full 실행의 레지스터·포트 API가 아님 |
| `submit_sprite(ram,d0,d1,d5,d7,status,error)` / 같은 헤더 | cd58 기본 callback cd50의 RAM/status 효과 | 레지스터 효과 없음. 첫 wait는 표시하지만 재개할 captured target 없음 |
| `execute_sprite_submit(ram,state,status,error)` / `sprite_submit_execution.h` | cd58 기본 callback cd50, D0..D7/A0..A4, clip/full/accepted와 cda4 wait 재개, 실패 원자성 | `SceneMapTransferState`는 13R. A5/A6는 보관하지 않으며 queue 주소는 canonical 고정값. 임의 callback·애니메이션 외부 stack/bank/return 문맥 없음 |
| `execute_sound_word(ram,state,external_status,external_reads,error)` / `sound_word_execution.h` | 3af8와 high/low byte wait, saved_low/phase, 조건부 d00046 읽기 | opcode30의 외부 A0/A1 저장·복원/다음 명령 복귀는 별도. 내부 state도 D0..D7/A0..A4이고 canonical sound queue 주소 사용 |

실제 구현은 각각 `engine/src/animation_step.cpp`, `animation_draw.cpp`, `sprite_producer.cpp`, `sprite_submit_execution.cpp`, `sound_word_execution.cpp`다. `step_animation`은 `step_animation_with_data`에 빈 regions를 전달한다. draw는 현재 `execute_sprite_submit`이 아닌 RAM 전용 `submit_sprite`를 호출하며 Waiting이면 전체 호출을 실패로 되돌린다. 따라서 기존 interpreter를 감싸서 15R 필드만 추가하는 방식으로는 native pending을 복원할 수 없다.

`step_animation*`은 caller의 RAM을 복사한 뒤 성공할 때 commit한다. 그러나 script fetch는 supplied script vector에서만 수행하며 RAM 또는 현재 bank의 live instruction fetch가 아니다. object가 script/조회 데이터와 alias하는 실행을 이 API의 성공 증거로 일반화하면 안 된다. 현재 `object_offset`의 최소 0x62 span 검사도 native의 실제 도달한 read별 검사와 다른 host 계약이다.

## 리소스 API

- `AnimationResource { source_cpu_address, source_rom_offset, data }`, `load_animation_resource(path,resource,error)`는 `animation_resource.h/.cpp`의 MS5A v1 kind1 loader다. 불변 fixed-ROM stream이며 CPU=ROM offset, 1MiB 미만이다. load 성공이 opcode 의미 지원을 뜻하지 않는다.
- `FixedDataResource`와 `load_fixed_data_resource`는 MS5D v1 kind1 fixed window다. `step_animation_with_data`는 비어 있거나 겹치는 창·CPU/ROM 불일치를 거절하고 각 read가 한 창에 완전히 들어가야 한다. pointer0 경로는 regions 검증 전에 반환한다.
- `load_banked_data_resource`는 이미 MS5D v1 kind2를 읽지만 기존 animation interpreter에는 banked lookup 연결이 없다. opcode40의 `200004` 계열 읽기는 실제 선택 bank를 반영해야 하며 kind1 fixed window로 대체할 수 없다.
- `tools/pack_animation.py`: caller 검증을 동반한 `[6f1e2,6f21a)`의 MS5A와 MS5C compositions. `pack_animation_branch.py`: `[65f56,662c2)`의 34개 명령, 1d/1e callback과 list에 필요한 bounded data/MS5C. `pack_animation_data.py`: fixed `[4a76c,4a88e)` 290 bytes 및 `[6431a,6471a)` 1024 bytes. 후자는 byte-index read window이며 하나의 논리 테이블 extent를 확정한 것이 아니다.

## 17개 dispatch 항목

원본 `4a01e: JMP 4a022(PC,D7.W)`의 table은 `[4a022,4a066)`다. 각 entry는 4-byte BRA.W이며 target=`entry+2+signed16(displacement)`다. 아래 RAM 지원은 현재 interpreter의 명시적 opcode 분기 기준이다. **모든 행에서 전체49fc6 15R·ordered PVC·pending 지원은 아직 없다.**

| Opcode | Table entry | 원본 handler | 기존 RAM 효과 지원 | 전체 실행에서 필요한 범위 |
|---|---|---|---|---|
| 00 | 4a022 | 4a066 | 지원 | wait timer/재해석의 실제 D1/D5/D6/D7/A1 및 반환 경로 |
| 04 | 4a026 | 4a104 → 4a10c | 지원, producer wait는 오류 | draw 전 레지스터, cd58 반환·pending, bank/stack 복원 |
| 08 | 4a02a | 4a3ac | 지원 | skipped byte, live LONG target, D7/A1/D6 pointer 저장 순서 |
| 0c | 4a02e | 4a3b8 | with_data 지원 | BYTE/WORD 부분 갱신·A2·live field read/branch |
| 10 | 4a032 | 4a22c | with_data 지원 | selected draw / skipped list의 레지스터, PEA return cursor, pending |
| 14 | 4a036 | 4a408 | with_data의 1d/1e만 | 실제 4a500 dispatch callback, A0/A1/bank 저장과 WORD restore |
| 18 | 4a03a | 4a27e | 미지원 | field BYTE write와 full state 검증 |
| 1c | 4a03e | 4a294 | 미지원 | field WORD write와 full state 검증 |
| 20 | 4a042 | 4a2ac | 미지원 | field LONG write와 full state 검증 |
| 24 | 4a046 | 4a2c4 | 미지원 | field BYTE decrement와 full state 검증 |
| 28 | 4a04a | 4a0e4 | 지원 | negative replay / high BYTE clear, D7/return carry |
| 2c | 4a04e | 4a3de | 미지원 | field-index relative branch, signed WORD 주소와 갱신 순서 |
| 30 | 4a052 | 4a2da | 미지원 | 실제 3af8 high/low waits와 외부 interpreter 문맥 |
| 34 | 4a056 | 4a2f2 | 미지원 | skipped byte, object+70 WORD write, D0=0 |
| 38 | 4a05a | 4a300 | 미지원 | skipped byte, object+20 WORD write |
| 3c | 4a05e | 4a30c | 미지원 | 실제 callback·bank 복원; 의미 추가 분석 필요 |
| 40 | 4a062 | 4a382 | 미지원 | banked lookup와 실제 mapped ROM; 의미 추가 분석 필요 |

범위 검사 `4a002 CMP.W #44,D7`는 opcode가4의 배수인지 검사하지 않는다. 01..43의 중간값은 BRA operand나 다른 위치로 진입할 수 있다. 이 표는 17개 정상 dispatch 항목 목록이며 모든 BYTE 입력을 정의한 안전한 command enum 증명이 아니다. 44 이상은 TRAP15/오류 문자열 영역이며 정상 성공 경로로 취급하지 않는다.

## 00/04/08/28의 상태·분기와 정보 손실

공통 원본 진입은 A0=A6+26, `(A0)`=script pointer LONG, `4(A0)`=timer WORD, `6(A0)`=decrement WORD다. `49fca`는 **live A5-7ff0** shadow를0으로 쓰고 PVC `2ffff2=1000`, `2ffff0=0`을 순서대로 쓴다. pointer0은 D7=0/A0 변경 후 carry1로 즉시 RTS한다. 활성 경로는 A1=pointer, A5+5742 BYTE clear, signed object+17가 양수일 때만 감소한다. 반복 dispatch `49ffe`는 D7=0 뒤 opcode BYTE를 읽는다. 현재 interpreter는 canonical RAM10/d742/0f를 사용하고 A0/A1/D7 및 PVC를 노출하지 않는다.

**00 / 4a066:** A5+5742 BYTE 증가, `MOVE.B (A1)+,D1`는 D1의 상위24bit를 보존한다. duration0이면 `MOVE.B 4(A0),D6`로 timer의 상위 BYTE만 D6.low에 넣어 부호를 판정한다. 음수면 timer WORD=0, saved pointer를 D7/A1로 다시 읽고 재해석한다. 비음수면 pointer 저장 없이 공통 반환한다. duration!=0에서는 timer WORD를 D6.low에 읽어 old를 보존하고, old<=0일 때 duration을 timer 상위 BYTE에 더한다. old>=0일 때만 decrement WORD를 D0.low에 읽고 timer에서 뺀다. 갱신 timer>0의 saved pointer 재읽기는 D5/A1을 바꾼다. 다음 opcode28 감지 역시 D5/A1을 갱신하고 D7=-1을 만든다. old<0 재해석과 old>=0의 A1→D6→saved pointer 저장을 구분해야 한다. 기존 코드의 `timer`, `old_timer`, `cursor`, `ended`는 RAM/carry 판단에 충분하지만 이 부분 레지스터 값·high bits·live read 순서를 반환할 수 없다.

**04 / 4a104,4a10c:** 원본은 D0/D5/D6을 MOVEQ0으로 지운 뒤 control→D5.B, X→D0.B, Y→D6.B, identifier→D7.L을 읽어 A1을 총7 bytes 진행한다. 모든 skip도 이 operand 소비를 마친다. identifier=007ff800이면 바로 RTS하여 원래 D1은 유지된다. 다른 ID면 먼저 object+20 WORD를 D7에 OR하고, timer 상위 BYTE 음수이면 RTS한다. 이어 object+61 bit3와 A5-7ff1 bit0가 모두1이면 RTS한다. `decode_animation_draw`는 이들을 `skipped=true,d0=d1=d5=d7=0` 하나로 합친다. 즉 **skip이 operand를 읽지 않는다는 뜻은 아니며**, 이미 읽은 control/X/Y/ID와 조건별 D7 OR 효과가 사라진다. native의 D6과 operand 후 A1도 결과에 없다.

정상 draw의 인자 계산은 decoder를 의미 참고자료로 재사용할 수 있으나 D2.B shift, D3=0, D4.B/WORD 작업, D6.W 좌표·부분 레지스터 보존도 구현해야 한다. cd58 뒤 D0/D7은 producer 반환값의 low WORD를 저장하고 `4a222 MOVEM.W`가 두 full registers를 부호 확장해 복원한다. 저장·복원 A0/A1, live A5 shadow와 ordered PVC도 RAM-only submit으로는 남지 않는다. cda4 wait에서는 외부 저장 A0/A1·bank WORD·draw return 위치를 보관해야 하며 resume 시 operand/object prefix를 다시 읽어서는 안 된다.

**08 / 4a3ac:** A1을1 byte 건너뛴 후 `(A1)` LONG을 D7에 읽고 A1=D7로 바꾼다. `4a276`에서 A1→D6→`(A0)`를 저장한 뒤 다음 dispatch로 간다. 현재 코드의 fetch5·target pointer 갱신은 RAM 효과를 지원하지만 skipped byte의 live read 부재와 LONG target read를 구분하는 bus trace, D7/D6/A1 high/full값, 다음 dispatch까지의 상태는 없다. C++의 전체5-byte fetch 요구는 native가 건너뛰는 byte까지 supplied window에 요구하는 host 계약이다.

**28 / 4a0e4:** timer WORD 음수는 timer 전체0 후 saved pointer를 D7/A1로 재읽고 재해석한다. 비음수는 `MOVE.B #0,4(A0)`로 timer 상위 BYTE만0, D7=-1, 공통 반환이다. `4a0ca`의 shadow0/PVC2 writes 후 `ASR.W #1,D7`가 carry를 결정한다. 기존 carry bool은 반환 C만 담고 D7의 실제 full값과 경로별 레지스터 보존은 담지 않는다. 포인터를 null로 만드는 동작은 없다.

## 기존 테스트의 정확한 용도

| 파일 | 현재 검사 범위 / 재사용 용도 |
|---|---|
| `engine/tests/animation_step_test.cpp` | pointer0, rollback, 잘린 fetch, jump, wait 거절, 10000-command budget |
| `engine/tests/animation_data_test.cpp` | 0c selector wrap·missing/overlap windows, 14/1e write·late rollback, indexed draw skip/선택/offset high BYTE |
| `engine/tests/animation_draw_test.cpp` | RAM/object/operand 크기 검사와 error 시 result 보존 |
| `engine/tests/animation_resource_test.cpp` | MS5A header 각 필드·CRC·trailing/truncated bytes, loader 결과 보존 |
| `tools/analyze_animation_wait.py --cpp` | controlled00/28/null 전체 RAM/carry 2000조건. RTS 뒤 emulator scratch SCS stub로 carry 포착 |
| `tools/analyze_animation_draw.py --cpp` | 실제4a10c를 cd58 진입 hook에서 중단해 네 producer 인자 비교; skip operand 소비 별도 검사. cd58 실행/반환은 증명하지 않음 |
| `tools/analyze_animation_branch.py --cpp`, `analyze_animation_indexed_draw.py --cpp`, `analyze_animation_callback.py --cpp` | controlled0c/10/14(1e) RAM/carry, bounded table 해석. full15R/PVC/pending은 대상 아님 |
| `tools/verify_animation_pipeline.py` 및 `--rom-script` | 선택 script의 연속 RAM/carry와 별도 prepare/refresh video stages. animation PVC/fullregs 검증으로 해석하지 않음 |
| `tools/verify_animation_branch_resource.py` 및 `--video` | 실제65f56 resource/forced branch와 bounded MS5D/MS5C pipeline. 자연 gameplay 전체를 증명하지 않음 |
| `engine/tests/sprite_submit_execution_test.cpp`, `tools/verify_sprite_submit_execution.py` | cd58 구성요소의 full13R·clip/full·hold/release·late rollback 참고. 전체 animation caller 문맥은 별도 |
| `engine/tests/sound_word_execution_test.cpp`, `tools/verify_sound_word_execution.py` | 3af8 구성요소의 high/low pending 참고. opcode30 prefix/return은 별도 |
| `tools/observe_animation_word_restore.py` | 원본 세 MOVEM.W 지점 각25조건, 총75조건. D0/D7 signed16→32 사실. 합성 incoming stack의 단일 명령 관찰이며 전체 callback 자연 도달 증명 아님 |

위 도구들은 이번 감사에서 재실행하지 않았다. 특히 이전 animation RAM/carry 도구는 emulator에 원본 외 scratch 반환 stub를 쓰므로, 새로운 **immutable 원본 전체15R/ports/pending** acceptance fixture를 그대로 대신하지 않는다. 기존 보고서의 subset 완료 문구와 현재 코드의 확장 사항은 함께 읽어야 한다.

## 메인에 반환할 결정·미확인 사항

1. full API에서 A5/A6와 callback의 live 변경을 어느 범위까지 지원할지 확정해야 한다. 기존 sprite/sound API는 canonical queue 구현이므로 arbitrary A5를 지원한다고 연결할 수 없다. 동작하는 부분을 유지하면서 실제 도달한 unsupported 경로를 명시하는 계약이 필요하다.
2. draw의 임의109152 callback 지원 범위와 opcode14/3c의 4a500 callback별 계약은 별도 분석 대상이다. 1d/1e RAM 복사만으로 공통 callback 프레임을 제거하면 WORD restore·bank·15R가 사라진다.
3. 외부 pending 상태는 producer의 captured13R뿐 아니라 animation의 saved A0/A1, bank WORD, command return location과 indexed-list return cursor를 구분해야 한다. opcode30에서는 word sound phase/saved_low도 필요하다. 정확한 state schema는 실제 원본 stack snapshot에서 결정해야 한다.
4. 실제489c2 script/ref windows의 범위와 opcode40 banked read mapping을 확인해야 한다. 현재6f1e2/65f56 리소스만으로 모든17항목의 자연 사용이나 pending 도달을 주장할 수 없다.
5. 다음 native 비교는 full64KiB RAM·15R·ordered PVC·carry·실제 RTS/A7 또는 실제 wait PC를 함께 보존하고, skip 세 경로 및 pending 중 operand/object/callback poisoning으로 prefix 재실행 부재를 확인해야 한다. 기존 API의 실패 원자성은 유지하되 잘린 자료를 정상 native 결과로 합성해서는 안 된다.

새 callback 의미, opcode2c/3c/40의 전체 동작 또는 하드웨어 bank timing은 이 감사에서 확정하지 않았다.
