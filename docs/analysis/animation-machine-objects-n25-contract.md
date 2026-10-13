# 객체 callback F4 N25: N24 `28ae` 자식 5개(`5e8c8` `5eac2` `5ead4` `5efe6` `5eff8`)와 설치 callback `5e940` `5eb74` `5f094`, 공유 callback `5e8b0` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N25 행(163 block, `5e8c8..5eeac` `5efe6..5f23a`, callback `5e8c8` `5e940` `5eac2` `5ead4` `5eb74` `5efe6` `5eff8` `5f094`, 경계 `44602` `4964e`, bank 1, 단독 새 seed 없음 — seed 32 33은 N24~N27 사슬이고 `dcf56`(N27)에서 먼저 멈춤; 원 범위 U35 163)과 N24 계약(`animation-machine-objects-n24-contract.md`, SHA256 `a87395d277cdedfd6461f203470437e458e796fe9b25fb9d22ed2c589e36e446`) 결정 1(`5e8b0..5e8c8`을 N25가 함께 넣는다는 권고)이다. 단위 형식과 규약은 N24·N28 계약을 따른다. 메인 작업 지시:
- 범위 = N25 행 + `5e8b0..5e8c8`(N25~N27 코드가 설치·분기하는 공유 callback; N24 결정 1).
- flag 재계산은 선행이 유일할 때만(아니면 분기를 각 선행에 접어 넣음). N25에는 block 경계를 건너 flag를 읽는 곳이 callee C 소비 3곳뿐이라 재계산이 없다.
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 설치·진입은 넣는다. 범위 밖에서만 부르는 범위 안 helper는 routing하지 않는다(N25에는 해당 없음).
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가). N25에는 RTS 앞 C 생산이 없다.
- 다른 단위 실행부(`animation_machine_interpreter.cpp` 포함)는 고치지 않는다. 기존 실행부의 두 번째 진입 누락은 scratch patch + 결정으로 보고한다(N25에는 없음). DIV 0 제수는 단위 checked 오류(N25에는 DIV가 없다).
- 계산 점프 표는 정적으로 묶고 전부 전사한다(N25에는 점프 표가 없다). WORD 자료 표(`5ea38` `5ea42` `5f23a` `5f242`)와 LONG `22` 기준 LONG 표는 live bus 읽기다(결정 3).
- ~220 block을 넘으면 나눈다(N25는 168 block이라 나누지 않는다).

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치·`MOVEA.L #imm,A0`+`JSR 28ae` 자식, 범위 밖에서 참조하는 범위 안 진입)로 정한다. Unicorn TB 분할은 시작이 아니다. 같은 flag를 쓰는 연속 Bcc는 한 block으로 묶는다(`5ecdc` `5ed12`의 `BEQ`+`BGE`).
- 결정 5(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N24 수용 관례: CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`BTST`/`ST`)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. `MOVE`/`CLR`/`CMP`/`CMPI`/`ADD`/`ADDI`/`ADDQ`/`SUB`/`SUBI`/`SUBQ`/`NEG`/`LSR`/`LSL`/`ANDI`/`TST`/`BSET` 등이 있는 block은 C를 바꾸며, 블록 밖 소비자가 없으므로 Unknown으로 둔다. 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N25 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`200194`와 LONG `22(A6)`이 가리키는 표)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n25`(HEAD `2fbe9d0` = N24·N28까지 통합, `engine/src/animation_machine.cpp` SHA256 `ccb62f57acea7482073ed0bc4fbcf6a734a15cf2ac1609e1fc111317997bf1b1`, routing 규칙 82개, `engine/src/animation_machine_interpreter.cpp` SHA256 `97abb2e1de42cf322e35fa3a66eea3ab633170143ea79e0d525e5ad4e317882f`)을 참조했다. N25 routing 범위의 짝수 PC는 기존 routing에 없다(범위 양끝 이웃 `5e8ae` `5ea38` `5eac0` `5eeac` `5efe4` `5f23a`도 routing 밖). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n25/n25.py`(정적 디코드, `starts.txt` SHA256 `50f247b74fe77897bda63713e0fb3e75057777cc8ce0984756dca32b6dd3bc7a`)와 `cls25.py`(분류)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N25 = 168 block**(routing 범위 3개 `5e8b0..5ea38` `5eac2..5eeac` `5efe6..5f23a`, 코드 1,990바이트, 짝수 PC 995, 내부 827). 진입 9개(아래)에서 분기·fall-through를 끝까지 따라간 정적 closure이며, 범위 안 명령 458개를 모두 덮는다(미도달 0). 재범위 163 + `5e8b0..5e8c8` 5(결정 1)이다.
- [F] 진입:
  - N24 `28ae` 자식 값(N24 `5df38`~`5df90`이 `MOVEA.L #x,A0; JSR 28ae`로 넘김): `5e8c8` `5eac2` `5ead4` `5efe6` `5eff8`. 범위 밖 다른 참조 없음(`5e8ea` `5f0ea` `5f000`과 같은 값의 LONG은 좌표 자료 `d7292` `d729e` `27734` 등이고 시작이 아니다).
  - 범위 안 설치(fall-through): `5e940`(`5e93a`), `5eb74`(`5eb6e`), `5f094`(`5f08e`).
  - 공유 callback `5e8b0`: 범위 안 설치 `5ea1a` `5ea28` `5ebf0 MOVE.L #5e8b0,(A6)`, tail `5ea34` `5ebf6 BRA.W 5e8b0`. 범위 밖 N26/N27 설치 `5f34e` `5f85a` `5fc6a` `5fe3a` `6012e` `603f2` `604e8`도 같은 값을 쓴다.
- [F] **경계(실행부 없음, 현재 routing 밖)**: `4964e`(`5eca6 JSR`), `44602`(`5ecbc JSR`). `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다. 복귀점 `5ecac` `5ecc2`는 관례대로 block 시작이다(직접 진입으로만 실행). [F] 재범위 N26~N35 어느 범위에도 없고 400 frame 안에 실행되지 않는다(아래 자연 도달).
- [F] **범위 밖 `28ae` 자식 값(실행 PC가 아님)**: `5eed2`(`5ee20` `5ee4e`, `D0.W` = `a`). `5eed2..5efe6`(설치 `5ef42` `5ef8c` `5efba` 사슬)은 재범위 어느 행에도 없는 고아 설치 사슬이다(결정 2).
- [F] **다른 실행부로 가는 callee**: `8ebe`(U02), `16ef0` `4a496`(U14), `43e34` `8ff4`(cleanup), `28ae`(fade_card), `49f8c` `49fc6`(interpreter), `49290`(U08), `491c4`(U17), `4a46c`(N04), `49370`(U11), `4945e`(N08), `4970a`(N14), `49a58`(stage_area). 모두 기존 실행부의 block 시작이다(scratch 검사: 해당 실행부 소스의 `case 0x…:`). 레지스터 간접 호출은 없다. 패치 파일은 없다.
- [F] **carry**: 소비 3 block(`5ec9c BCS`: U11 `49370`의 C; `5ee1c` `5f190 BCC`: interpreter `49fc6`의 C), known 생산 0, FLOW_ONLY 48(소비 3 포함), Unknown 120. 48 + 120 = 168.
- [F] N/Z 재계산 없음. X·DIVx/MULx·PC 상대 점프 표·레지스터 간접 점프·TRAP·I/O port 쓰기·bank 변경 없음. `SUBQ.W`/`ADDQ.W`(D1, 메모리 WORD)의 C와 `CMP`/`CMPI`의 N/Z/V는 같은 block의 Bcc만 읽는다.
- [F] 스택: JSR 복귀 LONG만(push/pop 없음). RTS 7곳(`5e8be` `5e8c6` `5e9d4` `5ebde` `5eeaa` `5f182` `5f238`).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `seen25.py`): 두 기록 모두 seed 32 33만 N25 범위를 실행한다. callback 실행 수(seed별): `5e8c8` `5eac2` `5ead4` `5efe6` `5eff8` 각 1, `5e940` 81, `5eb74` 162, `5f094` 162. 실행된 범위 안 TB 시작 64개는 초기화 경로 전부와 `5e940` `5e950` `5e97e`~`5e9d6` `5ea2e` `5ea34` `5e8b0` `5e8b6` `5e8be`, `5eb74` `5eb84` `5ebcc`~`5ebde`, `5f094`~`5f0ec` `5f124` `5f12c` `5f174` `5f17a` `5f182`다(부모 BYTE `76`이 0이 되는 경로와 부모 BYTE `63` = 0만). `5eb74` 상태기계(`5ebe0` 이후), `5f184` 이후, `4964e`/`44602`, `5eed2` 자식은 실행되지 않는다.
- [F] 기준(`2fbe9d0`)에서 seed 32 33은 frame 0 callback `dcf56`(N27 범위)에서 먼저 멈춘다. [I] N25만으로는 RNG·base 완주 수가 늘지 않는다(재범위 표의 N25 행 132/133 그대로). 검증은 실제 ROM 차분과 fixture가 맡는다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 168 block = 재범위 163 + `5e8b0..5e8c8` 5.** [F] N24 결정 1 권고와 메인 지시대로 공유 callback `5e8b0..5e8c8`을 넣었다. 시작은 `5e8b0`(`JSR 43e34`) `5e8b6`(`TST.B 79; BNE`) `5e8be`(`RTS`) `5e8c0`(`JSR 49fc6`) `5e8c6`(`RTS`)의 5개다. N24 계약은 PC 4개(`5e8b0` `5e8b6` `5e8be` `5e8c0`)만 들었으나 `5e8c6`은 `JSR 49fc6`의 복귀점이라 관례(결정 3)상 시작이다. routing은 `5e8b0..5ea38` 하나로 N25 첫 범위와 붙인다.
2. **경계와 고아 사슬.** [F] `4964e`(`5eca6`)·`44602`(`5ecbc`)는 재범위 경계 그대로이며 실행부가 없다(N19도 `44602`를 경계로 둠). [F] `5ee20`/`5ee4e`의 `28ae` 자식 값 `5eed2`는 재범위 어느 단위에도 없는 설치 사슬(`5eed2..5efe6`, 설치 `5ef42` `5ef8c` `5efba`, `JMP 2a00`)의 진입이다. N25는 자료로만 넘긴다(`28ae`가 자식 노드 LONG에 씀). [U] 소유 단위 미정(고아 설치 callback 정리 단계 후보). 400 frame 안에 실행되지 않는다.
3. **자료 표(live bus).** [F] 점프 표가 아니므로 전사하지 않고 `am_read`로 읽는다. 색인 검사는 원본처럼 없다.
   - `5ea38` WORD 5개(`ffff 0002 ffff 0007 ffff`, SHA256 `0ab47d9f94b3f6ae94cc6471fdff3500636013ad31cd7010ea962d520bf6e912`): `5e99c` `D0.W` = WORD(`5ea38` + 2·BYTE `76`(0 확장)), 색인 0..510(`5ec36`까지 고정 ROM). `ffff`이면 BYTE `79` = 0을 남기고 `5e9d4` RTS.
   - `5ea42` WORD 쌍 표 16 × 8바이트(SHA256 `453e79a24e5398e5b61779c532b94db083d1c3d77f288dc0f07e6676da056583`): `5ee30`/`5ee5e` `D2.W` = (`8c.W` << 3) & `ffff`, `D0.W` = WORD(`5ea42` + sext(`D2.W`) + 0/4), `D1.W` = WORD(… + 2/6). 범위 안 경로의 `8c.W`는 `ANDI.W #f` 결과(0..15)지만 메모리에서 읽으므로 임의 WORD다(부호 확장 색인 −32768..32760).
   - `5f23a` WORD 4개(`ffff 0069 ffff ffff`, SHA256 `f92c2da5…`)·`5f242` WORD 4개(`ffff 006d ffff ffff`, SHA256 `5657967b…`): `5f0b0`/`5f0ec` `D0.W` = WORD(표 + 2·BYTE `76`), 색인 0..510. 두 표는 N25 routing 밖(`5f23a..5f24a`, N26 `5f24a` 앞)이다.
   - LONG `22` 기준 LONG 표: 결정 5.
4. **callee C 소비 3곳.** [F] 모두 callee가 RTS로 돌려준 C를 읽고, Unknown C면 `objects n25 caller requires known carry`(상태 보존)다.
   - `5ec9c BCS.W 5ed5c`(U11 `49370`): `49370`은 A5 = `108000`일 때 BYTE `568e(A5)` = 0이면 `49386 ORI`(Set → `5ed5c`, `8c.W` 그대로), ≠ 0이면 `4938c ANDI`(Clear → `5eca0` → `4945e` → 경계 `4964e`). A5 ≠ `108000`이면 TRAP `4937c`(U11 경계).
   - `5ee1c BCC.W 5eeaa`·`5f190 BCC.W 5f238`(interpreter `49fc6`): N20 계약과 같은 interpreter 끝의 known C(`49fe6` ORI Set = LONG `26(A6)` = 0 등). Set이면 `5ee20`(자식 `5eed2` 2개)·`5f194`.
   - [F] 실제 생산자를 따라간 native 분기로 확인한다(검증 기록).
5. **bank 읽기.** [F] `5e912` `5eb4a` `5f048 MOVE.L 200194.l,22(A6)`(id `18b`, banked LONG; 재범위 "bank 1"). 이어서 LONG `22`를 기준으로 LONG을 읽는다: `8`(`5e912`), `e0`(`5ea04`), `58`(`5eb4a` `5eb90`), `1a4`(`5f05e`), `1b4`(`5f078`), `1ac`(`5f144` `5f1ac`), `1bc`(`5f15e` `5f1e8`), `1b0`(`5f1c6`), `1c0`(`5f202`), 4·WORD 표 값(`5e9b8` `5f0cc` `5f108`), 4·(`8c.W` + `f`)(`5ec4c` `5ed60`), 4·(`8c.W` + `20`)(`5edaa`). 색인 LONG 읽기는 `(A1,Dn.W)`(16 bit 부호 확장)다. 모두 live bus(현재 PVC bank 모델)다.
6. **`5e950 CMPI.W #1,D0`.** [F] `5e940`은 `MOVE.B 76(A0),D0`(하위 BYTE만 바꿈)이고 `5e950`은 `CMPI.W`로 `D0.W` 전체를 비교한다. 따라서 `D0` bit 8..15(진입 전 값)가 0이 아니면 BYTE가 1이어도 `5e97e`로 간다. `5eb84`는 `CMPI.B`다. 원본 그대로 구현한다.
7. **`28ae` 실패 뒤 A0.** [F] `5ee30`/`5ee5e`는 `28ae`의 C를 읽지 않고 `MOVE.W 8a(A6),8a(A0)`을 쓴다. `28ae`는 자리 없음·A0 = 0이면 A0 = A5 − `7168`(`100e98`)을 돌려주므로 그 노드의 WORD `8a`(`100f22`)에 쓴다. fade_card 실행부가 돌려준 A0를 그대로 쓴다.
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n25.cpp`의 `animation_objects_n25_block`. 오류는 `unsupported animation objects n25 PC`(내부 PC), `objects n25 caller requires known carry`(소비 3 block). 메인 지시와 같다.
9. **무효화 탐침 — 다른 단위 test 16개 수정 필요.** [F] 기존 test가 "어느 단위에도 없는 미연결 PC"로 쓴 `5f0xx`/`5f1xx`/`5f200` 값이 N25 범위 `5efe6..5f23a` 안에 있다(재범위 N25 행에 이미 들어 있던 범위). N25 routing 뒤 block 시작(`5f006` `5f00c` `5f012` `5f026` `5f030`)은 실행되고, 내부 PC는 `unsupported animation objects n25 PC`가 되어 `unsupported animation machine PC` rollback 기대가 깨진다. 대상: `animation_machine_area_clear_test.cpp`(`5f03e`), `animation_machine_card_menu_test.cpp`(`5f080`), `animation_machine_card_menu_open_test.cpp`(`5f088`), `animation_machine_card_menu_close_test.cpp`(`5f084`), `animation_machine_fade_card_test.cpp`(`5f038` `5f03a`), `animation_machine_frame_helpers_test.cpp`(`5f006` `5f00a` `5f00c` `5f00e` `5f010` `5f012`), `animation_machine_input_test.cpp`(`5f014` `5f016` `5f200`), `animation_machine_motion_walk_test.cpp`(`5f002` `5f004`), `animation_machine_objects_u01_test.cpp`(`5f1a0` `5f1a4`), `animation_machine_objects_u02_test.cpp`(`5f0fe`), `animation_machine_scene_update_test.cpp`(`5f01e` `5f022`), `animation_machine_script_placement_test.cpp`(`5f026`), `animation_machine_stage_catalog_test.cpp`(`5f004` `5f01c`), `animation_machine_stage_entry_test.cpp`(`5f018` `5f01a`), `animation_machine_stage_event_test.cpp`(`5f028`~`5f034`), `animation_machine_scheduler_test.cpp`(fixture `pass-unsupported`의 노드 callback LONG `100bf4:0005f03c`, 내부 PC). 메인 F4 test 경계 관례대로 RAM PC `10fe00..10fefe`(test마다 기존 값과 겹치지 않게)로 바꾼다. 실제 수정 목록과 바꾼 값은 검증 기록에 적는다. [F] `tools/*.py`에는 N25 범위 PC를 탐침으로 쓰는 곳이 없다(N04/U17 test의 레지스터 값 `5eaf8` `5f0e8`, digest 문자열 일부 일치는 탐침이 아님).

## 원본 바이트 근거

[F] N25 코드 3 범위 1,990바이트(짝수 PC 995개, 시작 168, 내부 827). 연결 SHA256 `515937e15a88538de5b694e74b02d018183fef411e70fdd9ebec0ba92363497e`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `5e8b0..5ea38` | 392 | `cc41e1fac86a39b64ce3e972a5377779a16605f7638bd561a812a7bc630c79d9` | 33 |
| `5eac2..5eeac` | 1,002 | `f3d54829428571dacd95734dead74de99c1433965f339231f76eac8ef9bcd985` | 90 |
| `5efe6..5f23a` | 596 | `214fe1d8381e43dcab0d5d096e1bc898e937c71fa47bf1a6c214e1d1238d67de` | 45 |

- [F] 범위 이웃(모두 routing 밖): `..5e8b0`(N24 끝 `5e8a6` WORD 표), `5ea38..5eac2`(WORD 표 `5ea38`·`5ea42`, 결정 3), `5eeac..5eed2`(자료 WORD 19개, SHA256 `2d446209…`; 고아 사슬의 `LEA 5eeac(PC)`/`5eeca(PC)` 인자), `5eed2..5efe6`(고아 설치 사슬, 결정 2), `5f23a..5f24a`(WORD 표, 결정 3), `5f24a..`(N26 `28ae` 자식 `5f24a`).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(A6)·`(An,Dn.W)`는 부호 확장한다. `CMP.W D0,D1`의 `BGE`는 `D1.W` ≥ `D0.W`(부호), `CMPI.W #x,Dn`의 `BGE`/`BGT`/`BLE`는 부호 있는 비교다.

**공유 callback `5e8b0`(N25~N27이 설치·`BRA.W`; `43e34`, BYTE `79` ≠ 0이면 `49fc6`, RTS) 5**
- `5e8b0`: `JSR 43e34.l` — FLOW
- `5e8b6`: `TST.B 79(a6); BNE.W 5e8c0` (→`5e8be`)
- `5e8be`: `RTS` — FLOW
- `5e8c0`: `JSR 49fc6.l` — FLOW
- `5e8c6`: `RTS` — FLOW

**`28ae` 자식 `5e8c8`(N24 `5df38`; 초기화, bank LONG `200194`, 끝 `5e93a` 설치 `5e940` fall-through) 7**
- `5e8c8`: `MOVE.B #ff, 76(a6); MOVE.W #0, d0; MOVE.W #0, d1; JSR 49290.l`
- `5e8dc`: `JSR 491c4.l` — FLOW
- `5e8e2`: `MOVE.W #d4c, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5e8f0`: `MOVE.W #d56, d0; JSR 4a496.l`
- `5e8fa`: `BSET.B #6, 15(a6); MOVE.W #801, 68(a6); MOVE.W #801, 1e(a6); JSR 16ef0.l`
- `5e912`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 8(a1), a1; JSR 49f8c.l`
- `5e93a`: `MOVE.L #5e940, (a6)` (→`5e940`)

**설치 callback `5e940`(부모 BYTE `76` 추종, 표 `5ea38`, 부모 BYTE `63` → 설치 `5e8b0`) 21**
- `5e940`: `MOVEA.L c(a6), a0; MOVE.B 76(a0), d0; CMP.B 76(a6), d0; BEQ.W 5e9d6` (→`5e950`)
- `5e950`: `MOVE.B d0, 76(a6); CMPI.W #1, d0; BNE.W 5e97e` (→`5e95c`)
- `5e95c`: `JSR 8ff4.l` — FLOW
- `5e962`: `MOVE.W #d4c, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5e970`: `MOVE.W #d56, d0; JSR 4a496.l`
- `5e97a`: `BRA.W 5e99c` — FLOW
- `5e97e`: `JSR 8ff4.l` — FLOW
- `5e984`: `MOVE.W #d4a, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5e992`: `MOVE.W #d56, d0; JSR 4a496.l`
- `5e99c`: `LEA.L 5ea38(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 5e9d4` (→`5e9b8`)
- `5e9b8`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5e9d4`: `RTS` — FLOW
- `5e9d6`: `MOVEA.L c(a6), a0; TST.B 63(a0); BEQ.W 5ea2e` (→`5e9e2`)
- `5e9e2`: `CMPI.B #1, 76(a0); BNE.W 5ea24` (→`5e9ec`)
- `5e9ec`: `ST.B 79(a6); JSR 8ff4.l` — FLOW
- `5e9f6`: `MOVE.W #d4c, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5ea04`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L e0(a1), a1; JSR 49f8c.l`
- `5ea1a`: `MOVE.L #5e8b0, (a6); BRA.W 5ea2e`
- `5ea24`: `CLR.B 79(a6); MOVE.L #5e8b0, (a6)` (→`5ea2e`)
- `5ea2e`: `JSR 4a46c.l` — FLOW
- `5ea34`: `BRA.W 5e8b0` — FLOW

**`28ae` 자식 `5eac2`/`5ead4`(N24 `5df60`/`5df70`; BYTE `78` = 0/1, 초기화, 끝 `5eb6e` 설치 `5eb74` fall-through) 11**
- `5eac2`: `MOVE.B #0, 78(a6); MOVE.W #7, d0; MOVE.W #7b, d1; BRA.W 5eae2`
- `5ead4`: `MOVE.B #1, 78(a6); MOVE.W #0, d0; MOVE.W #0, d1` (→`5eae2`)
- `5eae2`: `JSR 49290.l` — FLOW
- `5eae8`: `JSR 491c4.l` — FLOW
- `5eaee`: `MOVE.B #ff, 76(a6); MOVE.W #d47, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5eb02`: `MOVE.W #d49, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5eb10`: `MOVE.W #d55, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5eb1e`: `MOVE.W #d58, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5eb2c`: `MOVE.B 19(a6), 14(a6); BSET.B #6, 15(a6); MOVE.W #804, 68(a6); MOVE.W #804, 1e(a6); JSR 16ef0.l`
- `5eb4a`: `MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 58(a1), a1; JSR 49f8c.l`
- `5eb6e`: `MOVE.L #5eb74, (a6)` (→`5eb74`)

**설치 callback `5eb74`(부모 BYTE `76` = 1 추종, BYTE `77` 상태 0~2 조준 상태기계, `49fc6` C → `28ae` 자식 `5eed2` 2개) 79**
- `5eb74`: `MOVEA.L c(a6), a0; MOVE.B 76(a0), d0; CMP.B 76(a6), d0; BEQ.W 5ebd0` (→`5eb84`)
- `5eb84`: `MOVE.B d0, 76(a6); CMPI.B #1, d0; BNE.W 5ebcc` (→`5eb90`)
- `5eb90`: `ST.B 79(a6); MOVE.W #0, 8a(a6); MOVE.W #8, 8c(a6); MOVE.B #0, 77(a6); MOVE.W #3c, 7e(a6); MOVE.W #8, 80(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 58(a1), a1; JSR 49f8c.l`
- `5ebc8`: `BRA.W 5ebd0` — FLOW
- `5ebcc`: `CLR.B 79(a6)` (→`5ebd0`)
- `5ebd0`: `JSR 43e34.l` — FLOW
- `5ebd6`: `TST.B 79(a6); BNE.W 5ebe0` (→`5ebde`)
- `5ebde`: `RTS` — FLOW
- `5ebe0`: `MOVEA.L c(a6), a0; TST.B 63(a0); BEQ.W 5ebfa` (→`5ebec`)
- `5ebec`: `CLR.B 79(a6); MOVE.L #5e8b0, (a6); BRA.W 5e8b0`
- `5ebfa`: `CMPI.B #0, 77(a6); BNE.W 5ec8c` (→`5ec04`)
- `5ec04`: `MOVE.W 8a(a6), d1; BEQ.W 5ec2c` (→`5ec0c`)
- `5ec0c`: `CMPI.W #80, d1; BGE.W 5ec22` (→`5ec14`)
- `5ec14`: `SUBQ.W #2, d1; BCC.W 5ec1e` (→`5ec1a`)
- `5ec1a`: `MOVE.W #0, d1` (→`5ec1e`)
- `5ec1e`: `BRA.W 5ec2c` — FLOW
- `5ec22`: `ADDQ.W #2, d1; BCC.W 5ec2c` (→`5ec28`)
- `5ec28`: `MOVE.W #0, d1` (→`5ec2c`)
- `5ec2c`: `ANDI.W #ff, d1; MOVE.W d1, 8a(a6); LSR.W #3, d1; CMPI.W #f, d1; BGT.W 5ec46` (→`5ec3e`)
- `5ec3e`: `SUBQ.W #7, d1; NEG.W d1; BRA.W 5ec4c`
- `5ec46`: `SUBI.W #27, d1; NEG.W d1` (→`5ec4c`)
- `5ec4c`: `ANDI.W #f, d1; MOVE.W d1, 8c(a6); ADDI.W #f, d1; LSL.W #2, d1; MOVEA.L 22(a6), a1; MOVEA.L (a1, d1.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5ec70`: `CLR.B 62(a6); MOVEA.L c(a6), a0; CMPI.B #1, 77(a0); BNE.W 5ec88` (→`5ec82`)
- `5ec82`: `MOVE.B #1, 77(a6)` (→`5ec88`)
- `5ec88`: `BRA.W 5edd2` — FLOW
- `5ec8c`: `CMPI.B #1, 77(a6); BNE.W 5ed98` (→`5ec96`)
- `5ec96`: `JSR 49370.l` — FLOW
- `5ec9c`: `BCS.W 5ed5c` (→`5eca0`) — C 소비, FLOW
- `5eca0`: `JSR 4945e.l` — FLOW
- `5eca6`: `JSR 4964e.l` — FLOW
- `5ecac`: `SUBI.W #ffce, d0; SUBI.W #ffd8, d1; SUB.W 42(a6), d0; SUB.W 46(a6), d1; JSR 44602.l`
- `5ecc2`: `SUBQ.W #4, d0; ANDI.W #ff, d0; MOVE.W 8a(a6), d1; CMPI.W #80, d1; BGE.W 5ed04` (→`5ecd4`)
- `5ecd4`: `CMPI.W #80, d0; BGE.W 5ecfe` (→`5ecdc`)
- `5ecdc`: `CMP.W d0, d1; BEQ.W 5ecfa; BGE.W 5ecf8` (→`5ece6`)
- `5ece6`: `ADDQ.W #2, d1; CMPI.W #3f, d1; BLE.W 5ecf4` (→`5ecf0`)
- `5ecf0`: `MOVE.W #3f, d1` (→`5ecf4`)
- `5ecf4`: `BRA.W 5ecfa` — FLOW
- `5ecf8`: `SUBQ.W #2, d1` (→`5ecfa`)
- `5ecfa`: `BRA.W 5ed00` — FLOW
- `5ecfe`: `SUBQ.W #2, d1` (→`5ed00`)
- `5ed00`: `BRA.W 5ed30` — FLOW
- `5ed04`: `CMPI.W #80, d0; BGE.W 5ed12` (→`5ed0c`)
- `5ed0c`: `ADDQ.W #2, d1; BRA.W 5ed30`
- `5ed12`: `CMP.W d0, d1; BEQ.W 5ed30; BGE.W 5ed22` (→`5ed1c`)
- `5ed1c`: `ADDQ.W #2, d1; BRA.W 5ed30`
- `5ed22`: `SUBQ.W #2, d1; CMPI.W #c1, d1; BGE.W 5ed30` (→`5ed2c`)
- `5ed2c`: `MOVE.W #c1, d1` (→`5ed30`)
- `5ed30`: `ANDI.W #ff, d1; MOVE.W d1, 8a(a6); LSR.W #3, d1; CMPI.W #f, d1; BGT.W 5ed4a` (→`5ed42`)
- `5ed42`: `SUBQ.W #7, d1; NEG.W d1; BRA.W 5ed50`
- `5ed4a`: `SUBI.W #27, d1; NEG.W d1` (→`5ed50`)
- `5ed50`: `ANDI.W #f, d1; MOVE.W d1, 8c(a6); BRA.W 5ed60`
- `5ed5c`: `MOVE.W 8c(a6), d1` (→`5ed60`)
- `5ed60`: `ADDI.W #f, d1; LSL.W #2, d1; MOVEA.L 22(a6), a1; MOVEA.L (a1, d1.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5ed7c`: `CLR.B 62(a6); SUBQ.W #1, 7e(a6); BCC.W 5ed94` (→`5ed88`)
- `5ed88`: `MOVE.W #5, 7e(a6); MOVE.B #2, 77(a6)` (→`5ed94`)
- `5ed94`: `BRA.W 5edd2` — FLOW
- `5ed98`: `CMPI.B #2, 77(a6); BNE.W 5edd2` (→`5eda2`)
- `5eda2`: `SUBQ.W #1, 7e(a6); BCC.W 5edce` (→`5edaa`)
- `5edaa`: `MOVE.W 8c(a6), d0; ADDI.W #20, d0; LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5edca`: `ST.B 62(a6)` (→`5edce`) — FLOW
- `5edce`: `BRA.W 5edd2` — FLOW
- `5edd2`: `MOVEA.L c(a6), a0; MOVE.B 17(a0), d0; ANDI.B #1, d0; BNE.W 5edfe` (→`5ede2`)
- `5ede2`: `TST.B 62(a6); BNE.W 5edf4` (→`5edea`)
- `5edea`: `MOVE.B 19(a6), 14(a6); BRA.W 5edfa`
- `5edf4`: `MOVE.B 1a(a6), 14(a6)` (→`5edfa`)
- `5edfa`: `BRA.W 5ee16` — FLOW
- `5edfe`: `TST.B 62(a6); BNE.W 5ee10` (→`5ee06`)
- `5ee06`: `MOVE.B 1b(a6), 14(a6); BRA.W 5ee16`
- `5ee10`: `MOVE.B 1c(a6), 14(a6)` (→`5ee16`)
- `5ee16`: `JSR 49fc6.l` — FLOW
- `5ee1c`: `BCC.W 5eeaa` (→`5ee20`) — C 소비, FLOW
- `5ee20`: `MOVEA.L #5eed2, a0; MOVE.W #a, d0; JSR 28ae.l`
- `5ee30`: `MOVE.W 8a(a6), 8a(a0); LEA.L 5ea42(pc), a1; MOVE.W 8c(a6), d2; LSL.W #3, d2; MOVE.W (a1, d2.w), d0; MOVE.W 2(a1, d2.w), d1; JSR 4970a.l`
- `5ee4e`: `MOVEA.L #5eed2, a0; MOVE.W #a, d0; JSR 28ae.l`
- `5ee5e`: `MOVE.W 8a(a6), 8a(a0); LEA.L 5ea42(pc), a1; MOVE.W 8c(a6), d2; LSL.W #3, d2; MOVE.W 4(a1, d2.w), d0; MOVE.W 6(a1, d2.w), d1; JSR 4970a.l`
- `5ee7c`: `SUBQ.W #1, 80(a6); BNE.W 5ee9e` (→`5ee84`)
- `5ee84`: `MOVEA.L c(a6), a0; MOVE.B #1, 62(a0); MOVE.W #8, 80(a6); MOVE.B #0, 77(a6); BRA.W 5eeaa`
- `5ee9e`: `MOVE.W #5, 7e(a6); MOVE.B #1, 77(a6)` (→`5eeaa`)
- `5eeaa`: `RTS` — FLOW

**`28ae` 자식 `5efe6`/`5eff8`(N24 `5df80`/`5df90`; BYTE `78` = 0/1, 초기화, 끝 `5f08e` 설치 `5f094` fall-through) 12**
- `5efe6`: `MOVE.B #0, 78(a6); MOVE.W #0, d0; MOVE.W #0, d1; BRA.W 5f006`
- `5eff8`: `MOVE.B #1, 78(a6); MOVE.W #0, d0; MOVE.W #0, d1` (→`5f006`)
- `5f006`: `JSR 49290.l` — FLOW
- `5f00c`: `JSR 491c4.l` — FLOW
- `5f012`: `MOVE.B #ff, 76(a6); MOVE.W #d4c, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5f026`: `MOVE.W #d57, d0; JSR 4a496.l`
- `5f030`: `BSET.B #6, 15(a6); MOVE.W #803, 68(a6); MOVE.W #803, 1e(a6); JSR 16ef0.l`
- `5f048`: `MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); TST.B 78(a6); BNE.W 5f078` (→`5f05e`)
- `5f05e`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 1a4(a1), a1; JSR 49f8c.l`
- `5f074`: `BRA.W 5f08e` — FLOW
- `5f078`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 1b4(a1), a1; JSR 49f8c.l`
- `5f08e`: `MOVE.L #5f094, (a6)` (→`5f094`)

**설치 callback `5f094`(부모 BYTE `76` 추종, 표 `5f23a`/`5f242`, 부모 BYTE `63`, `49fc6` C, `49a58`) 33**
- `5f094`: `MOVEA.L c(a6), a0; MOVE.B 76(a0), d0; CMP.B 76(a6), d0; BEQ.W 5f124` (→`5f0a4`)
- `5f0a4`: `MOVE.B d0, 76(a6); TST.B 78(a6); BNE.W 5f0ec` (→`5f0b0`)
- `5f0b0`: `LEA.L 5f23a(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 5f0e8` (→`5f0cc`)
- `5f0cc`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5f0e8`: `BRA.W 5f124` — FLOW
- `5f0ec`: `LEA.L 5f242(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 5f124` (→`5f108`)
- `5f108`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5f124`: `TST.B 62(a6); BNE.W 5f174` (→`5f12c`)
- `5f12c`: `MOVEA.L c(a6), a0; TST.B 63(a0); BEQ.W 5f174` (→`5f138`)
- `5f138`: `ST.B 62(a6); TST.B 78(a6); BNE.W 5f15e` (→`5f144`)
- `5f144`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 1ac(a1), a1; JSR 49f8c.l`
- `5f15a`: `BRA.W 5f174` — FLOW
- `5f15e`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 1bc(a1), a1; JSR 49f8c.l`
- `5f174`: `JSR 43e34.l` — FLOW
- `5f17a`: `TST.B 79(a6); BNE.W 5f184` (→`5f182`)
- `5f182`: `RTS` — FLOW
- `5f184`: `JSR 4a46c.l` — FLOW
- `5f18a`: `JSR 49fc6.l` — FLOW
- `5f190`: `BCC.W 5f238` (→`5f194`) — C 소비, FLOW
- `5f194`: `TST.B 62(a6); BEQ.W 5f238` (→`5f19c`)
- `5f19c`: `TST.B 78(a6); BNE.W 5f1e0` (→`5f1a4`)
- `5f1a4`: `TST.B 77(a6); BNE.W 5f1c6` (→`5f1ac`)
- `5f1ac`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 1ac(a1), a1; JSR 49f8c.l`
- `5f1c2`: `BRA.W 5f1dc` — FLOW
- `5f1c6`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 1b0(a1), a1; JSR 49f8c.l`
- `5f1dc`: `BRA.W 5f218` — FLOW
- `5f1e0`: `TST.B 77(a6); BNE.W 5f202` (→`5f1e8`)
- `5f1e8`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 1bc(a1), a1; JSR 49f8c.l`
- `5f1fe`: `BRA.W 5f218` — FLOW
- `5f202`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 1c0(a1), a1; JSR 49f8c.l`
- `5f218`: `JSR 49a58.l` — FLOW
- `5f21e`: `ANDI.W #7f, d0; ADDI.W #180, d0; LEA.L 26(a6), a0; MOVE.W d0, 6(a0); ADDQ.B #1, 77(a6); ANDI.B #1, 77(a6)` (→`5f238`)
- `5f238`: `RTS` — FLOW

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다; WORD 산술은 16 bit 2의 보수, `.W`/`.B`는 나머지 bit 보존):
  - `5e8b0`(공유): `JSR 43e34`. `5e8b6`: BYTE `79` ≠ 0이면 `5e8c0`(`JSR 49fc6`, 복귀 `5e8c6 RTS`), 아니면 `5e8be RTS`.
  - `5e8c8`(자식): BYTE `76` = `ff`, `D0.W` = `D1.W` = 0, `JSR 49290`. `5e8dc`: `JSR 491c4`. `5e8e2`: `8ebe`(`D0.W` = `d4c`, `D1.B` = 0). `5e8f0`: `D0.W` = `d56`, `JSR 4a496`. `5e8fa`: BYTE `15` |= `40`(읽고 쓰기), `68.W` = `1e.W` = `801`, `JSR 16ef0`. `5e912`: A0 = A6 + `26`, `20.W` = `18b`, LONG `22` = banked LONG `200194`, `D0.W` = `100`, A0 = A6 + `26`, A1 = LONG `22`, A1 = LONG(A1 + 8), `JSR 49f8c`. `5e93a`: `(A6)` = `5e940`, fall-through.
  - `5e940`(설치): A0 = LONG `c(A6)`(부모), `D0.B` = BYTE `76(A0)`; = BYTE `76(A6)`이면 `5e9d6`. `5e950`: BYTE `76(A6)` = `D0.B`; `D0.W` = 1이면(결정 6) `5e95c`(`8ff4`, `8ebe`(`d4c`, 0), `4a496`(`d56`), `BRA 5e99c`), 아니면 `5e97e`(`8ff4`, `8ebe`(`d4a`, 0), `4a496`(`d56`)). `5e99c`: A0 = `5ea38`, `D0` = 0, `D0.B` = BYTE `76`, `D0.W` = 2·`D0.W`, `D0.W` = WORD(A0 + sext(`D0.W`)), BYTE `79` = 0, `ffff`이면 `5e9d4 RTS`. `5e9b8`: BYTE `79` = `ff`, `D0.W` = (`D0.W` << 2) & `ffff`, A1 = LONG `22`, A1 = LONG(A1 + sext(`D0.W`)), `D0.W` = `100`, A0 = A6 + `26`, `JSR 49f8c`(복귀 `5e9d4 RTS`).
  - `5e9d6`: A0 = LONG `c`; BYTE `63(A0)` = 0이면 `5ea2e`. `5e9e2`: BYTE `76(A0)` ≠ 1이면 `5ea24`(BYTE `79` = 0, `(A6)` = `5e8b0`). `5e9ec`: BYTE `79` = `ff`, `JSR 8ff4`. `5e9f6`: `8ebe`(`d4c`, 0). `5ea04`: 애니메이션 `e0`(아래 "애니메이션 인자"). `5ea1a`: `(A6)` = `5e8b0`, `BRA 5ea2e`. `5ea2e`: `JSR 4a46c`. `5ea34`: `BRA 5e8b0`.
  - `5eac2`/`5ead4`(자식): BYTE `78` = 0/1, `D0.W` = 7/0, `D1.W` = `7b`/0; `5eae2`: `JSR 49290`; `5eae8`: `JSR 491c4`. `5eaee`: BYTE `76` = `ff`, `8ebe`(`d47`, 0); `5eb02` `5eb10` `5eb1e`: `8ebe`(`d49`/`d55`/`d58`, 0). `5eb2c`: BYTE `14` = BYTE `19`, BYTE `15` |= `40`, `68.W` = `1e.W` = `804`, `JSR 16ef0`. `5eb4a`: `20.W` = `18b`, LONG `22` = banked LONG `200194`, 애니메이션 `58`. `5eb6e`: `(A6)` = `5eb74`, fall-through.
  - `5eb74`(설치): A0 = LONG `c`, `D0.B` = BYTE `76(A0)`; = BYTE `76(A6)`이면 `5ebd0`. `5eb84`: BYTE `76(A6)` = `D0.B`; `D0.B` ≠ 1이면 `5ebcc`(BYTE `79` = 0). `5eb90`: BYTE `79` = `ff`, `8a.W` = 0, `8c.W` = 8, BYTE `77` = 0, `7e.W` = `3c`, `80.W` = 8, 애니메이션 `58`(복귀 `5ebc8 BRA 5ebd0`). `5ebd0`: `JSR 43e34`. `5ebd6`: BYTE `79` = 0이면 `5ebde RTS`. `5ebe0`: A0 = LONG `c`; BYTE `63(A0)` ≠ 0이면 `5ebec`(BYTE `79` = 0, `(A6)` = `5e8b0`, `BRA 5e8b0`). `5ebfa`: BYTE `77` ≠ 0이면 `5ec8c`.
  - 상태 0(`5ec04`): `D1.W` = `8a.W`; 0이면 `5ec2c`. `5ec0c`: `D1.W` ≥ `80`(부호)이면 `5ec22`(`D1.W` += 2, 올림 C면 `D1.W` = 0), 아니면 `5ec14`(`D1.W` −= 2, 빌림 C면 `D1.W` = 0). `5ec2c`/`5ed30`(방향 → 프레임): `D1.W` &= `ff`, `8a.W` = `D1.W`, `D1.W` 논리 >> 3; `D1.W` > `f`(부호)이면 `D1.W` = −(`D1.W` − `27`)(`5ec46`/`5ed4a`), 아니면 −(`D1.W` − 7)(`5ec3e`/`5ed42`); `D1.W` &= `f`, `8c.W` = `D1.W`. `5ec4c`는 이어서 `D1.W` += `f`, `D1.W` <<= 2, A1 = LONG(LONG `22` + sext(`D1.W`)), `D0.W` = `100`, A0 = A6 + `26`, `JSR 49f8c`. `5ec70`: BYTE `62` = 0, A0 = LONG `c`; BYTE `77(A0)` = 1이면 BYTE `77(A6)` = 1(`5ec82`). `5ec88`: `BRA 5edd2`.
  - 상태 1(`5ec8c`: BYTE `77` ≠ 1이면 `5ed98`): `JSR 49370`; `5ec9c`: Set이면 `5ed5c`(`D1.W` = `8c.W`). Clear: `JSR 4945e`(`5eca0`), `JSR 4964e`(`5eca6`, 경계). `5ecac`: `D0.W` −= `ffce`, `D1.W` −= `ffd8`, `D0.W` −= `42.W`, `D1.W` −= `46.W`, `JSR 44602`(경계). `5ecc2`: `D0.W` −= 4, `D0.W` &= `ff`, `D1.W` = `8a.W`; `D1.W` ≥ `80`(부호)이면 `5ed04`. `5ecd4`: `D0.W` ≥ `80`이면 `5ecfe`(`D1.W` −= 2). `5ecdc`: `D1.W` = `D0.W`이면 `5ecfa`, `D1.W` > `D0.W`(부호)이면 `5ecf8`(`D1.W` −= 2), 아니면 `5ece6`: `D1.W` += 2, `D1.W` > `3f`(부호)이면 `D1.W` = `3f`(`5ecf0`). `5ed04`: `D0.W` < `80`이면 `5ed0c`(`D1.W` += 2). `5ed12`: 같으면 `5ed30`, `D1.W` < `D0.W`이면 `5ed1c`(`D1.W` += 2), 크면 `5ed22`: `D1.W` −= 2, `D1.W` < `c1`(부호)이면 `D1.W` = `c1`(`5ed2c`). 모두 `5ed30`(위 방향 → 프레임, `BRA 5ed60`). `5ed60`: `D1.W` += `f`, <<= 2, 애니메이션(`5ec4c` 꼴). `5ed7c`: BYTE `62` = 0, `7e.W` −= 1(메모리 RMW); 빌림 C(이전 값 0)이면 `7e.W` = 5, BYTE `77` = 2(`5ed88`). `5ed94`: `BRA 5edd2`.
  - 상태 2(`5ed98`: BYTE `77` ≠ 2이면 `5edd2`): `7e.W` −= 1; 빌림 아니면 `5edce`. `5edaa`: `D0.W` = ((`8c.W` + `20`) << 2) & `ffff`, A1 = LONG(LONG `22` + sext(`D0.W`)), `D0.W` = `100`, A0 = A6 + `26`, `JSR 49f8c`. `5edca`: BYTE `62` = `ff`.
  - 공통(`5edd2`): A0 = LONG `c`, `D0.B` = BYTE `17(A0)` & 1; bit 0 = 0이면 BYTE `14` = BYTE `62` = 0 ? BYTE `19` : BYTE `1a`; 1이면 BYTE `14` = BYTE `62` = 0 ? BYTE `1b` : BYTE `1c`. `5ee16`: `JSR 49fc6`; `5ee1c`: Clear면 `5eeaa RTS`. `5ee20`/`5ee4e`: A0 = `5eed2`, `D0.W` = `a`, `JSR 28ae`. `5ee30`/`5ee5e`: WORD `8a(A0)` = `8a.W`(A0 = `28ae`가 돌려준 노드, 결정 7), A1 = `5ea42`, `D2.W` = (`8c.W` << 3) & `ffff`, `D0.W` = WORD(A1 + sext(`D2.W`) + 0/4), `D1.W` = WORD(A1 + sext(`D2.W`) + 2/6), `JSR 4970a`. `5ee7c`: `80.W` −= 1; 0이 아니면 `5ee9e`(`7e.W` = 5, BYTE `77` = 1). `5ee84`: A0 = LONG `c`, BYTE `62(A0)` = 1, `80.W` = 8, BYTE `77` = 0. 끝 `5eeaa RTS`.
  - `5efe6`/`5eff8`(자식): BYTE `78` = 0/1, `D0.W` = `D1.W` = 0; `5f006`: `JSR 49290`; `5f00c`: `JSR 491c4`. `5f012`: BYTE `76` = `ff`, `8ebe`(`d4c`, 0). `5f026`: `D0.W` = `d57`, `JSR 4a496`. `5f030`: BYTE `15` |= `40`, `68.W` = `1e.W` = `803`, `JSR 16ef0`. `5f048`: `20.W` = `18b`, LONG `22` = banked LONG `200194`; BYTE `78` ≠ 0이면 `5f078`(애니메이션 `1b4`), 아니면 `5f05e`(애니메이션 `1a4`, 복귀 `5f074 BRA 5f08e`). `5f08e`: `(A6)` = `5f094`, fall-through.
  - `5f094`(설치): A0 = LONG `c`, `D0.B` = BYTE `76(A0)`; = BYTE `76(A6)`이면 `5f124`. `5f0a4`: BYTE `76(A6)` = `D0.B`; BYTE `78` ≠ 0이면 `5f0ec`(표 `5f242`), 아니면 `5f0b0`(표 `5f23a`): `5e99c`와 같은 꼴(`ffff`이면 `5f0e8`/`5f124`). `5f0cc`/`5f108`: `5e9b8`과 같은 꼴(복귀 `5f0e8 BRA 5f124` / `5f124`). `5f124`: BYTE `62` ≠ 0이면 `5f174`. `5f12c`: A0 = LONG `c`; BYTE `63(A0)` = 0이면 `5f174`. `5f138`: BYTE `62` = `ff`; BYTE `78` ≠ 0이면 `5f15e`(애니메이션 `1bc`), 아니면 `5f144`(애니메이션 `1ac`, 복귀 `5f15a BRA 5f174`). `5f174`: `JSR 43e34`. `5f17a`: BYTE `79` = 0이면 `5f182 RTS`. `5f184`: `JSR 4a46c`. `5f18a`: `JSR 49fc6`. `5f190`: Clear면 `5f238 RTS`. `5f194`: BYTE `62` = 0이면 `5f238`. `5f19c`: BYTE `78`·BYTE `77`에 따라 애니메이션 `1ac`(0,0) `1b0`(0,≠0) `1bc`(≠0,0) `1c0`(≠0,≠0), 복귀 뒤 `BRA 5f218`. `5f218`: `JSR 49a58`. `5f21e`: `D0.W` = (`D0.W` & `7f`) + `180`, A0 = A6 + `26`, WORD `6(A0)` = `D0.W`(= WORD `2c(A6)`), BYTE `77` = (BYTE `77` + 1) & 1(두 번의 메모리 RMW). 끝 `5f238 RTS`.
  - 애니메이션 인자(`MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c`): `D0.W` = `100`, A0 = A6 + `26`, A1 = LONG `22`, A1 = LONG(A1 + d), `JSR 49f8c`. 읽기 순서는 LONG `22` → LONG(A1 + d)이다.

## carry

- [F] **소비 3 block**: `5ec9c BCS.W 5ed5c`(U11 `49370`의 C), `5ee1c BCC.W 5eeaa`·`5f190 BCC.W 5f238`(interpreter `49fc6`의 C; 결정 4). Unknown C로 들어오면 `objects n25 caller requires known carry`(상태 보존)다.
- [F] **known 생산 0 block**. N25 안에는 `ORI`/`ANDI` CCR이 없고, RTS 7곳 앞 C를 읽는 ROM 소비자도 없다(callback의 복귀는 scheduler로 간다). `5e8c6 RTS`는 `49fc6`의 C를 그대로 돌려주지만(FLOW) 그 호출자(scheduler)는 C를 읽지 않는다.
- [F] **FLOW_ONLY 48 block**(C 보존): JSR 하나뿐인 block(`5e8b0` `5e8c0` `5e8dc` `5e95c` `5e97e` `5ea2e` `5eae2` `5eae8` `5ebd0` `5ec96` `5eca0` `5eca6` `5ee16` `5f006` `5f00c` `5f174` `5f184` `5f18a` `5f218`), `ST`+JSR(`5e9ec`), `ST`(`5edca`), `BRA` block(`5e97a` `5ea34` `5ebc8` `5ec1e` `5ec88` `5ecf4` `5ecfa` `5ed00` `5ed94` `5edce` `5edfa` `5f074` `5f0e8` `5f15a` `5f1c2` `5f1dc` `5f1fe`), RTS(`5e8be` `5e8c6` `5e9d4` `5ebde` `5eeaa` `5f182` `5f238`), 소비 `5ec9c` `5ee1c` `5f190`.
- [F] **carry 보존 목록 48 PC** = FLOW_ONLY 48.
- [F] **Unknown 120 block**: 나머지(`MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`ADDQ`/`ADDI`/`SUBQ`/`SUBI`/`SUB`/`NEG`/`LSR`/`LSL`/`ANDI`/`BSET`가 있는 block, 설치 block, 애니메이션 인자 block). block 안에서 계산되는 C(`5ec14` `5ec22 SUBQ/ADDQ.W D1`, `5ed7c` `5eda2 SUBQ.W 7e`)는 같은 block의 `BCC`만 읽고 block 밖으로 나가지 않는다.
- [F] X를 쓰는 명령은 없다.

## 구현 범위와 규약

- routing 3 범위(`5e8b0..5ea38` `5eac2..5eeac` `5efe6..5f23a`). 짝수 PC 995개 중 block 시작 168, 내부 827. 내부 PC 직접 진입은 `unsupported animation objects n25 PC`다. 범위 이웃(`5ea38..5eac2` 표, `5eeac..5efe6` 자료·고아 사슬, `5f23a..5f24a` 표)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다(`MOVEQ`·`MOVEA`·`LEA`는 LONG 전체). 산술은 원래 폭의 2의 보수로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다. `SUBQ`/`ADDQ`의 C는 16 bit 빌림/올림을 직접 계산한다. 부호 있는 비교는 16 bit 값을 부호 bit 기준으로 명시 비교한다. 결과 flag는 같은 block 안의 Bcc만 쓴다(결정 4 예외). 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다). 메모리 대상 RMW(`BSET.B` `SUBQ.W` `ADDQ.B` `ANDI.B`)는 읽은 뒤 쓴다.
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 48 PC를 넣는다.
- 제어 이동: 모두 정적이다. 설치 값(`5e940` `5eb74` `5f094` `5e8b0`)은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. `5e93a`→`5e940`, `5eb6e`→`5eb74`, `5f08e`→`5f094`는 같은 실행으로 계속한다. `5ea34`·`5ebec BRA.W 5e8b0`은 같은 실행으로 계속한다. `JSR 4964e`·`JSR 44602`는 PC = 경계(복귀 LONG push 뒤).
- 스택: JSR 복귀 LONG push와 RTS pop만. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank): LONG `200194`(`5e912` `5eb4a` `5f048`, id `18b` → LONG `22`).
- [F] LONG `22` 기준 LONG 읽기(live bus; 대상이 bank window면 bank 읽기): 결정 5의 고정 변위 `8` `e0` `58` `1a4` `1b4` `1ac` `1bc` `1b0` `1c0`, 부호 확장 16 bit 색인 4·표 값·4·(`8c.W` + `f`)·4·(`8c.W` + `20`). 결과 A1은 `49f8c`(interpreter) 인자다.
- [F] 고정 ROM 자료(live bus): `5ea38` `5f23a` `5f242` WORD 표, `5ea42` WORD 쌍 표(결정 3). 주소만 넘기는 자료: `28ae` 자식 `5eed2`(`D0.W` = `a`), `8ebe` 인자 WORD `d47` `d49` `d4a` `d4c` `d55` `d58`(`D1.B` = 0), `4a496` 인자 `d56` `d57`, `49290` 인자 `D0.W`/`D1.W` = 0/0 또는 7/`7b`.
- [F] work RAM 노드 A6: BYTE `14` `15`(`BSET` RMW) `19` `1a` `1b` `1c` `62` `76` `77` `78` `79`; WORD `1e` `20` `2c`(= `6(A0)`, A0 = A6 + `26`) `42` `46` `68` `7e` `80` `8a` `8c`; LONG `(A6)`(설치) `c`(부모) `22`. 부모 노드(LONG `c`): BYTE `17` `62`(쓰기) `63` `76` `77`. `28ae` 자식 노드: WORD `8a`(쓰기). A0 = A6 + `26`(`49f8c` 인자).
- [F] 상수 인자: `49f8c` `D0.W` = `100`; `28ae` `D0.W` = `a`.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256 앞 16자리): `engine/src/animation_machine_objects_n25.cpp` `5f09002fa08cc990`, `engine/tests/animation_machine_objects_n25_test.cpp` `366e5a3543e5eeb3`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나, carry 보존 case group 하나(48 PC); `3544b92817bdebe3`), `engine/src/animation_machine_internal.h`(선언 하나; `db2da01a894cc973`), `Makefile`(source 목록·test target·실행 줄; `01f34cb75730154a`), `tools/verify_animation_machine.py` SOURCES(`82c0f6d436a08b64`).
- [F] 결정 9 탐침 교체(16 test, 값만 바꿈, 34줄): `area_clear` `5f03e`→`10fe20`; `card_menu` `5f080`→`10fe20`; `card_menu_open` `5f088`→`10fe20`; `card_menu_close` `5f084`→`10fe20`; `fade_card` `5f038` `5f03a`→`10fe20` `10fe22`; `frame_helpers` `5f006` `5f00a` `5f00c` `5f00e` `5f010` `5f012`→`10fe20`~`10fe2a`; `input` `5f014` `5f016` `5f200`→`10fe20` `10fe22` `10fe24`; `motion_walk` `5f002` `5f004`→`10fe20` `10fe22`; `objects_u01` `5f1a0` `5f1a4`→`10fe20` `10fe22`; `objects_u02` `5f0fe`→`10fe20`; `scene_update` `5f01e` `5f022`→`10fe20` `10fe22`; `script_placement` `5f026`→`10fe20`; `stage_catalog` 노드 callback LONG `5f004`→`10fe20`, `5f01c`→`10fe22`; `stage_entry` `5f018` `5f01a`→`10fe20` `10fe22`; `stage_event` `5f028`~`5f034`→`10fe20`~`10fe2c`; `scheduler` fixture `pass-unsupported`의 `100bf4:0005f03c`→`0010fe20`. 각 test의 기존 `10fexx` 값(`10fe0c` `10fe10` `10fe58` `10fe80` `10fe90`)과 겹치지 않는다. 교체 전에는 16개 모두 N25 routing 뒤 실패했고(`unsupported animation objects n25 PC` 또는 block 실행), 교체 뒤 모두 통과한다.
- [F] 실행부 case 집합 = scratch `starts.txt`(168, SHA256 `50f247b7…`). 내부 PC 827개는 모두 `unsupported animation objects n25 PC`, 소비 `5ec9c` `5ee1c` `5f190`은 Unknown C에서 `objects n25 caller requires known carry`(상태 보존)다.
- [F] `make -j4 all test`: exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log`; 첫 실행은 `animation_machine_scheduler_test`의 `5f03c` 탐침에서 실패했고 결정 9대로 고친 뒤 다시 돌린 결과). N25 test 출력: `animation machine objects n25: 1083 fixtures (19 checked errors, 12 kept C), 168 blocks, 2945 calls`. N20~N24·N28 test와 `tools/tests` unittest 257개는 그대로 통과.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N25 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만, scratch `gen/gen25.py` Unicorn 생성, 두 번 생성해 `tables_n25.inc` SHA256 `0f789bb43442d6d1…` 같음): 1,083 fixture(성공 1,064, checked 오류 19), 168 시작 모두 Unicorn fixture로 덮음, block 표(168 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 3은 Unknown에서 거부), zero-step 168 × 3, 내부 PC 827 전수, 홀수 PC(범위마다 양끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`·RTS 복귀 `10fe40`(10 fixture), 범위 옆 자료 `5e8ae` `5ea38` `5ea40` `5eac0` `5eeac` `5eed0` `5f23a` `5f248`, 경계 stop 17개(다른 단위 진입 15·`4964e` `44602`는 stop만). 상태기계 fixture는 `8a`(29값)·`D0`(16값) 문턱(`3f`/`40`, `7f`/`80`/`81`, `c0`/`c1`/`c2`, `ff`/`100`, `7fff`/`8000`, `ffff`)과 `SUBQ`/`ADDQ` C 경계, `7e`/`80` 0·1, 부모 BYTE `76`/`63`/`77`/`17`, BYTE `62`/`78`/`79`/`77` 조합, 무작위 60개를 훑는다. "real" 행은 U11 `49370`(BYTE `568e(A5)` 0/1/`80` → ORI Set `5ed5c`, ANDI Clear `4945e`)을 native로 따라가 실제 소비자 `5ec9c` 분기와 비교하고, fade_card `28ae`(자리 `14`/`b` 성공, `a`/0 실패 → A0 = `100e98`)를 따라가 `5ee30`/`5ee5e`의 WORD `8a(A0)` 쓰기를 확인했다. `49fc6` 소비 `5ee1c` `5f190`은 typed C(실제 interpreter는 PVC bank 레지스터를 써서 fixture 형식 밖; 실제 ROM 차분에서 확인). 합성 바이트: 표 `5ea38`(`0002 0003 ffff 2001 ffff`; `2001` → `LSL.W` `8004` 음수 색인 → RAM mirror `1f8404`), `5ea42`(64 WORD, 0..`ff` 또는 bit 13 = 1), `5f23a`(`0001 ffff 2002 0005`), `5f242`(`ffff 0006 3fff ffff`; `3fff` → 색인 −4), bank `200000..200800`(LONG `200194` = `200400`, 나머지 LONG = `c00000` + 변위). checked 오류 fixture 16개(홀수 노드 읽기·쓰기, ROM 노드, 장치 쓰기, 스택 장치, RTS 장치, 부모 장치 읽기·쓰기, 부모 ROM, 표 ROM(`5e99c` BYTE `76` = `80`, `5f0b0` BYTE `76` = 8), 홀수 LONG `22`, ROM LONG `22`, 쌍 표 ROM(`8c` = `1000`), 적재 안 된 bank 바이트(`5ed60` 색인 `43c`), 홀수 자식 `8a(A0)` 쓰기) + 소비 3.
- [F] 돌연변이 검사(scratch `mut/mut25.py`, 실행부 한 줄씩 35개): 34/35를 test가 잡았다. 살아남은 `m8`(`5ec14` 빌림 `< 2` → `<= 2`)은 동치 돌연변이다(`D1.W` = 2이면 원본은 `SUBQ` 결과 0, 돌연변이는 `5ec1a`에서 0을 넣어 결과가 같다). 대신 `m8b`(`< 1`)를 더해 잡혔다. 잡힌 항목: 소비 분기 3곳 뒤바꿈, `5e950 CMPI.W`→BYTE, WORD 부호 없는 비교, 표 색인 배수, LONG 색인 부호 확장, `5ec22` 올림 C, 방향 shift, `27` 반사, `7e`/`80` 0 판정, `SUBI #ffce`, `5ecc2` mask, `3f`/`c1` 한계, 쌍 표 변위·shift, `17` bit, `5f21e` mask·`ANDI`, 애니메이션 변위 `1b0`, `7e` 초기값, 자식 id 801/803, 부모 BYTE 비교 폭, `5ecdc`/`5ed12` 방향, `BSET` RMW, BYTE `14` 원천, `5ed7c CLR.B 62`, `5edaa` `20`, `5f0ec` 표, `5ee84` 부모 쓰기.
- [F] 실제 ROM 차분(scratch `realrom/real25.py`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM, LONG `22` = 실제 banked 기록(`200194` → `2c89c2`) 또는 RAM 사본, 실제 ROM 표 `5ea38` `5ea42` `5f23a` `5f242`, LONG `26` = 0 또는 실제 기록의 애니메이션 목록, native는 STOP·`2a00`·`2a24`·C++ routing 밖 첫 PC(`4964e` `44602` 포함)·`49f8c`/`49f96`(선언 stop)에서 멈춤): 3 seed × 1,500 case 불일치 0/0/0, 시작 168/168(seed마다). 실제 생산자 뒤 소비자 native 분기 비교(seed 1/2/3): `5ec9c`(U11 `49370`) 35/33/38, `5ee1c`(interpreter `49fc6`) 52/59/44, `5f190`(`49fc6`) 24/26/19. native가 경계에서 멈춘 case `4964e` 43/38/41, `44602` 6/11/8. clean stop이 없는 native case는 건너뜀(503/530/444): 대부분 실제 interpreter `49fc6`이 무작위 상태(`2a`/`17`)로 목록을 해석하다 PC < `400`에서 멈춘 경우(`low`)와, 초기화 사슬에서 실제 `49290`이 둔 BYTE `1d(A6)` ≥ 4로 `8ebe`가 TRAP `8ec8`에 닿는 경우(`none`; [I] 마지막 PC 기록으로 확인한 대표 원인)다. interpreter 따라가기(`FOLLOW_ANIM`, RAM 표 = 실제 기록 사본) 2 × 1,000 case 불일치 0(건너뜀 774/724, 같은 원인), 소비자 비교 `5ec9c` 32/30, `5ee1c` 83/84, `5f190` 30/28.
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `2fbe9d0` 일치 pass 14,408·node 122,462, 불일치 0 → N25 뒤 같음(`diff_results.json` SHA256 `a6c41695…`, 기준과 바이트 동일).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 132·pass 52,800·node 396,091·불일치 0(`verification.json` SHA256 `cf8231c2…`) → N25 뒤 같은 값(`d90c367b…`; 차이는 `engine_source_sha256`의 `animation_machine.cpp`·`animation_machine_objects_n25.cpp`와 seed 32 33 116 117 기록의 `current_router_sha256`뿐). 새 완주 seed 0, 잃은 seed 0. seed 32 33은 그대로 frame 0 `dcf56`(N27)에서 멈춘다(재범위 예상과 같음).
- [U] 남은 미확인: seed 32 33의 자연 경로는 `dcf56`(N27)에서 먼저 멈춰 N25 범위의 frame pass 비교가 아직 없다(실제 ROM 차분·fixture로만 덮음). `5eb74` 상태기계(`5ebe0` 이후), `5f184` 이후, 경계 `4964e`/`44602`, 자식 `5eed2`는 자연 400 frame에서 실행되지 않는다. `5eed2..5efe6` 고아 사슬의 소유 단위는 미정이다(결정 2).
