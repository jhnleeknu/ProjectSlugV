# 영역 E 단위 E1(캐릭터 선택 `de8bc`..`df2c0`, map-clip helper `18364`, boot 입력 확인 `2634`, 222 block) 구현 계약

**구현 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §4.2의 E1 행과 이 문서의 "E1 상세 명세"(계획 §8 C1 명세에 대응)를 기준으로 삼고, 구조·공통 규칙은 player C1 계약(`animation-machine-player-c1-contract.md`)과 FR9 계약을 따르며 다른 점만 적는다. 단위 이름은 E1, 파일 접두어는 `select_e1`(C++) / `se1`(V1 spec)이다. 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기 `2000c0`과 그 LONG이 가리키는 창 주소(`2xxxxx`)만 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다. 입력 port `300000`은 장치 주소다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `ff2e284`(branch `claude/e1-core`, player C1 커밋 위). routing 기준 `engine/src/animation_machine.cpp` SHA256 `15b827242abca6434147ab3a63a827b5d4d613cbdbbba051c438a57ea001dea2`, `animation_machine_internal.h` `5e2ad9ef19d159ba9907b2a9683034ad754b6734177ee8e73f84e235c4337a0e`(C1 반영).
- [F] 관측 입력: native IO 관측 `artifacts/animation_machine_io_native`(읽기 전용; state pack `states/P1/094.pack.gz` `068.pack.gz`, `P1b/094.pack.gz`, `boot-title-start/boot.pack.gz`)와 계획의 보정 관측 `ms5-scratch/c1/reobs/`(실행 집합 측정용, 계획 메인 결정 1; 읽기만 함).
- [F] 시작 목록: scratch `ms5-scratch/e1/starts_E1.txt`(222개, SHA256 `befbbe32a6f0f859038f740f204870a66a789bcd329dcaa1e78386648c401a9f`). 실행부의 `case` label 222개와 집합이 같다(작업자 확인).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/e1/`
  - `remeasure/remeasure.py`(C1이 routing된 상태에서 계획 단위 재측정), `work/natsearch.py`(IO pack의 E1 자연 node 검색), `mut/`(변이), `realrom/`(실제 ROM 차분), `tools/`(계획 도구 사본; 경로는 `metalslug-e1` / `ms5-scratch/e1`).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **재측정 전**(`MS5_REOBS=…/c1/reobs dleft.py`, routing `15b82724…` = C1 연결 후): 실행된 routing 밖 PC C **757** / E **218** / D 0, 예측 일치 frame **165,759**, 첫 정지 영역 E 15 / C 1. C1 계약의 측정 결과와 같다.
- [F] **closure 재측정**(scratch `remeasure/remeasure.py`가 `cplan3.main`을 계획 spec `plan/plan_final.json`으로 다시 돌림): C1은 이미 routing되어 0 block, **E1 222 block, 609 명령, 2,700 byte, 시작 목록 SHA256 `befbbe32a6f0f859…`** — 계획 §4.2·§6과 **같다**(차이 없음). E1 뒤 예측 일치 frame 169,144(+3,385), 남은 C 757 / E 12, 첫 정지 C 14. 전체 검사 `starts_equal true, insns_equal true, missing_exec []`(C1이 빠져 전체 closure는 2,588 시작).
- [F] **정적 범위**: 3 범위, 2,700 byte(이어 붙인 SHA256 `48f2d7fd054ba145b107758c7df7f6b624867090530d00e0af6f43a37dfa63e4`), 짝수 PC 1,350(내부 1,128), 시작 222. 범위 안에 기존 routing된 PC는 없다.
- [F] **`2622`에 대하여**: 계획 표의 root 이름 `2622`(boot `9de JSR 2622`)는 함수 이름이다. 실행 집합에 있는 것은 `2634` 하나뿐이다(fixture `fx-c-input-read` / `fx-n-input-read`의 guard frame). `2622..2634`(`MOVE.B 10fe80.l,7002(A5); BNE.W 2634; CLR.W 10f000.l`)는 IO 관측에서 실행되지 않았고 closure에도 없다. 그래서 E1 범위는 `2634..264a`이며 `2622`는 routing 밖으로 남는다(단위 시험이 확인).
- [F] **예측**: E 218 → 12(남는 12개 `b0c b26 b2a b3c b56 e6496 e64a2 e64ae e64b4 e64b8 e64c0 e64cc`는 E 주소의 C helper, 계획 결정 6에 따라 C6), 예측 일치 frame 165,759 → **169,144**, 첫 정지 C 14(+186/+190 frame의 플레이어 본체 `1d222` 계열).

## 요약

| 범위(CPU = 파일 오프셋) | byte | 명령 | SHA256(앞 16자) | block | 짝수 PC |
| --- | --- | --- | --- | --- | --- |
| `2634..264a` | 22 | 5 | `2876fe60adc26e28` | 3 | 11 |
| `18364..183c6` | 98 | 39 | `5045f7b9af498d1f` | 11 | 49 |
| `de8bc..df2d0` | 2580 | 565 | `e9d857c1c6b9eba5` | 208 | 1290 |
| 합계 E1 | 2700 | 609 | 이어 붙인 바이트 `48f2d7fd054ba145…` | **222** | 1350(내부 1128) |

- [F] **명령 종류**(609개): 계산 점프·`JSR (An)`·TRAP·DIVU/MULU·ABCD/ADDX/SUBX 없음. **MOVEM.L 4곳**(`df288` `df2a0` `MOVEM.L D2/A0,-(A7)`, `df292` `df2aa` `MOVEM.L (A7)+,D2/A0`), stack WORD push/pop(`dea8e` `deacc` `MOVE.W D2,-(A7)`, `deaba` `deb02` `MOVE.W (A7)+,D2`), LONG push/pop(`defee` `MOVE.L D0,-(A7)`, `df038` `MOVE.L (A7)+,D0`), `ASR.W #4` 2곳(`18368` `1839c`), `BSET.B #2,15(A6)` 3곳, `BTST.B #0` 1곳, signed 비교 `BLT`/`BGT`/`BGE` 6곳(`dec52` `dec62` `ded1a` `dedaa` `df0ba`(BYTE) `df0f8`/`df12e`), unsigned `BCC`/`BCS` 7곳(`18364` clip 6, `def46`), PC 상대 표 읽기 21곳, bank 창 LONG 읽기 5곳(`2000c0`), 입력 port BYTE 읽기 1곳(`2634`).
- [F] **나가는 곳**(routing된 callee·분기 출구, 모두 다른 실행부의 block 시작): `28ae` `3918` `3af8` `3c44` `3d7e` `8cda` `8ebe` `8ff4` `183c6`(`183c4`의 fall-through, map-transfer block) `185f4`(clip-out, map-transfer: `ANDI.B #fe,CCR; RTS`) `43e04` `43e34` `43ea4` `49a84` `49f8c` `49fc6` `4a974` `4e186` `ca50`(player C1).
- [F] **뒤 단위 정지 없음.** E1 block이 직선·분기로 닿는 routing 밖 PC는 없다. 그래서 V1·실제 ROM 차분의 `EXIT_STOPS`는 비어 있다.

## E1 상세 명세(계획 §8에 대응)

### 범위와 root

- [F] 계획 `cfam` 기준 root 31개(실행 PC 206, 실행 수 307,201, run 17): `de8bc` `de8ca` `de8ee` `de97e` `de9e8` `dea50` `deb1a` `deba4` `dec10` `dec6e` `dec8c` `ded00` `ded9e` `dedb6` `dee28` `dee36` `def32` `def58` `def8c` `defc0` `defdc` `df06c` `df0f2` `df128` `df15e` `df230` `df254` `df272` `df2c0` + `18364` + `2622`(함수 이름; 실행 PC는 `2634`).
- [F] closure 진입(실행 PC를 줄인 것): `de8ca` `de97e` `deba4` `defdc` `de9e8` `deb1a` `dedb6` `dee36` `2634`. 실행된 시작 198, 실행되지 않은 시작 24(`2642 2648 18384 18390 183b2 183c0 deaa0 dec5c decc4 deccc dedb4 dee8a dee92 deea8 deeac deeb4 deeca deece deed6 deeec df1ba df1d6 df1de df1f6`).
- [F] TB 분할 PC `defe2..df002`(계획 §3.2의 artefact)는 block 시작이 아니다(`defdc` block 내부).

### 설치 값과 진입

- [F] **생성 callback**(같은 frame 안에서 설치·실행, frame 시작 상태에는 남지 않음): `de8ca`(슬롯 문자 [I]) `de97e`(제목 틀 [I]) `de9e8`(커서 깜박임 [I]) `deb1a`(초상 틀 [I]) `deba4`(초상 미끄럼 [I]). 이들은 FR1의 `de660` 계열 표(`de69a` `de6aa` … `de7f8`, `28ae` 인자)가 만든다(FR1 시험의 `28ae` 정지 행 A0 출력이 이 값들이다).
- [F] **`28ae` 자식**: `defdc`(`debce MOVEA.L #defdc,A0; JSR 28ae`, 선택 커서 [I]), `dedb6`(`ded62`, 이름판 [I]), `dee36`(`ded78`, 초상 [I]). 자식 WORD `7a`는 부모의 WORD `7a`를 받는다(`debde` `ded72` `ded88`).
- [F] **설치 값 19개**(모두 범위 안 시작): `de8bc de8ee dea50 dec10 dec6e dec8c ded00 ded9e dee28 def32 def58 def8c defc0 df06c df0f2 df128 df15e df230 df254`.
  - 곧바로 들어가는 곳(설치 다음 PC가 그 값): `de8de`→`de8ee`, `dec78`→`dec8c`, `dee22`→`dee28`, `def80`→`def8c`, `defba`→`defc0`, `df248`→`df254`.
  - 설치 후 다른 곳으로 가는 곳: `dec66`(→`dec6c RTS`), `decee`(→`decfe RTS`), `ded88`(→`ded94`), `def4a`(→`def50`), `df0be`(같은 block에서 `TST.B 62`), `df0ea`(→`df0f0`), `df0fc`/`df132`(→`df122`/`df158`), `df224`(→`df22a`).
  - 설치 후 `RTS`: `de9e0` `deb9c`(`de8bc`), `dea2a`(`dea50`), `debee`(`dec10`), `def2a`(`def32`), `df052`(`df06c`).
- [F] **subroutine 진입**: `de8bc`(공통 꼬리 `JSR 43e34; JSR 49fc6; RTS`; `deb14` `df0ac` `df122` `df158` `df22a` `df26c`에서 `JSR de8bc(PC)`), `df272`(`df11a` `df1fe` `df268`), `df2c0`(`df150` `df1da`), `18364`(`ded4a JSR 18364.l`; 끝은 `183c6`으로 이어지는 map-transfer 공유 꼬리), `2634`(`262a BNE`; boot `9de JSR 2622`).

### 표·자료 읽기(모두 live bus, 상한 검사 없음)

| 위치(CPU = 파일 오프셋) | 꼴 | 읽는 곳 |
| --- | --- | --- |
| `de580` | WORD × 7a(`ADD.W D0,D0`) | `dee48`(light id) |
| `de588` | WORD 쌍 × 4·7a | `deba4` `defee`(43e04 D0/D1) |
| `de598` | LONG × 4·7a → WORD 3개 | `df272`(digit) |
| `de5c0` `de5d0` `de5e0` | LONG × 4·7a | script(`df0d2` `df202` / `df230` / `df038` `df1de`) |
| `de5f0` | LONG × 4·7a → 창 색인 | `deb5e` |
| `de600` | LONG × 4·7a → LONG 목록 × 4·D2 → 창 색인 | `deaba` |
| `de628` | WORD × 7a | `decda`(소리 id [I]) |
| `de630` | WORD 쌍 × D2.W | `deb02`(위치 [I]) |
| `de640` `de650` | WORD 쌍 × 4·7a | `deb3a` / `dedd6` |
| `dfbb0` `dfbc0` `dfbd0` | LONG × 4·7a | `defa0` / `dee70..deed6` / `def58` |
| `2000c0`(bank 창) | LONG → 창 표 base | `de9b8` `deaba` `deb5e` `dedf4`(+ `4(·)` `dc(·)` `(·,D1.W)` `(·,D0.W)`) |
| `300000`(입력 port) | BYTE | `2634`(외부 읽기 queue) |

- [F] 원본 자료 SHA256(앞 16자): `de580..de660` `d8e849f6517a9573`, `dfbb0..dfbe0` `954e6c03b3ab3cb8`. `de600`은 원본에서 첫 두 칸만 포인터(`de608` `de618`)이고 3·4칸은 수(`2d` `2f`)다 [F]. 즉 `deaba`의 7a는 원본 흐름에서 0/1(플레이어)이고 다른 표는 0..3(캐릭터)이다 [I]. 원본 색인 범위 밖 값은 원본도 표 뒤 바이트를 읽는다(검사 없음).
- [F] 문자열 포인터 `de48c` `de49e` `de4b0` `de4c2`(A0), `e84c8`(A1), `df2d0`(A1, `18364`의 뒤 `183c6`이 읽음), `109156`(A0, 지도 buffer [I])은 넘기기만 한다.

### flag가 block 경계를 넘는 곳(scratch `cscan.py`)

- [F] **C 소비자·생산자 없음.** E1 block의 첫 C/X 읽기가 C 쓰기보다 앞서는 곳이 없다. `RTS`가 flag를 돌려주는 18곳(`2648 de8c8 deb18 dec6c dec76 decfe ded9c dedb4 dee34 def56 defda df0f0 df126 df15c df22e df270 df2be df2ce`)의 호출자는 flag를 읽지 않는다(dispatcher 복귀, 또는 다음 block이 `MOVEA`/`ADDQ`/`LEA`/`JSR`/`CMPI`로 시작). `18364..183c4`의 끝 `ADD.W D6,D5`는 `183c6 MOVE.W 4(A1),D7`이 flag를 다시 쓴다.
- [F] **Z 소비자 2곳**:
  - `de8f4 BEQ.W de910`: 앞 block `de8ee JSR ca50`(player C1 block: `TST.B -7699(A5); RTS`)의 Z.
  - `de938 BEQ.W de944`: 앞 block `de92e JSR 4a974`(controller C1: `4a9b0`/`4a9c6 TST.B (A0); RTS`)의 Z.
- 같은 block 안의 flag(`dea62 BTST`, `dec46 CMPI.W`+`BLT` 등)는 block 안에서 계산한다.

### IO run·seed

- [F] E1 PC를 실행하는 run 17개: P1 12(case 68~71, 94, 95, 100, 101, 106, 107, 110, 111), P1b 2(68, 94), boot-title-start, fixture `fx-c-input-read` / `fx-n-input-read`(`2634`만, frame 3의 guard frame).
- [F] 자연 node(IO pack, scratch `work/natsearch.py`): P1 094 frame 6..166(node `1010e4` `1011a8` `10126c` `101330..10157c`(4 캐릭터) `101640..10188c`(4) `101950..101b9c` `101c60` `101d24` `101020` `101de8`), P1 068 frame 226..382, P1b 094 frame 6..599, boot-title-start frame 126..286. 상대 frame(계획 §3.3): +3~+62(생성·선택), +98~+134(끝: `18364` `dee28` `def32` `defc0`).
- [F] D1 자연 seed(입력 없음)와 P0 run은 E1 코드를 실행하지 않는다.

## 공통 규칙·native 검증 계획

player C1·FR2..FR9 계약의 같은 절을 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_select_e1.cpp`, 함수 `animation_select_e1_block`. 오류 문자열은 `unsupported animation select e1 PC`(범위 안 내부 PC 직접 진입), `unsupported animation select e1 flag source`(결정 3의 Z 출처 guard). C 소비자가 없어 `… caller requires known carry`는 없다. 그 밖의 오류는 공용 bus·stack·queue 오류(`animation machine external read queue empty` / `… mismatch` 등)다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(3 범위, player C1 줄 뒤), `carry_preserving_pc`에 주석 두 줄(E1은 case를 더하지 않음; 결정 4), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 주석). 결정 2 개정으로 frame 구동기(`animation_machine_frame.cpp`의 `run_animation_frame_segment`, header 주석, frame 시험)도 바뀌었다(아래 "영향받는" 절).
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾸고 상위를 유지한다(`MOVE.W/.B`, `ADD.W`/`SUB.W`, `ADDI.W`/`SUBI.W`, `ADDQ.W`/`SUBQ.W`, `ADDQ.B`, `LSL.W #2`, `ASR.W #4`, `ANDI.W`/`ANDI.B`, `CLR.W`/`CLR.B`). `MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`·`MOVEM.L`은 LONG 전체. 색인 `(An,Dn.W)`는 An + sext(Dn.W)(+ d8). `ASR.W #4`는 하위 WORD의 부호 bit를 채운다(`fff0` → `ffff`, `f780` → `ff78`). `SUBI.W #fffa`는 +6과 같다. 비교: `18364` clip의 `CMP.W` + `BCC`와 `SUB.W` + `BCC`/`BCS`는 무부호 WORD(같으면 BCC 쪽), `CMPI.W #170/#1b0` + `BLT`, `CMPI.W #12c` + `BGT`, `CMPI.W #10` + `BGE`, `CMPI.W #20` + `BLT`는 부호 있는 WORD, `CMPI.B #2,63(A0)` + `BLT`는 부호 있는 BYTE, `CMPI.W #148` + `BCC`는 무부호, `CMPI.W #ffff,D1`·`CMPI.W #1,D1`·`CMP.W 7a(A6),D2`·`CMP.W 82(A6),D2`는 WORD 같음(상위 무시), `CMP.B 85(A6),D0`·`CMPI.B #2,62(A6)`는 BYTE, `TST.W`/`TST.B`는 그 크기, `ADDI.L #ffffb000,3a(A6)`은 LONG 순환.
- **stack.** `MOVE.W D2,-(A7)`/`MOVE.W (A7)+,D2`는 WORD(2 byte), `MOVE.L D0,-(A7)`/`MOVE.L (A7)+,D0`는 LONG, `MOVEM.L D2/A0,-(A7)`는 높은 LONG에 A0, 낮은 LONG에 D2(68000 순서), `MOVEM.L (A7)+,D2/A0`는 그 반대 순서로 읽어 A7 += 8. 모두 `am_push`/`am_pop`(work RAM stack; 홀수 A7은 `program bus requires even WORD/LONG address`).
- **입력 port.** `2634 MOVE.B 300000.l,D0`은 `am_read`로 선언된 외부 읽기 queue의 앞 항목(주소 `300000`, 크기 1)을 쓴다. queue가 비면 `animation machine external read queue empty`, 다른 장치 항목이면 `… mismatch`(checked, rollback). IO 관측의 native guard `undeclared-device-read`는 검증기에서 같은 `external read queue empty`에 대응한다(`verify_animation_machine_io.py` `NATIVE_END_ERROR`). frame 구동기 안에서는 결정 2(개정)에 따라 H만 queue를 읽는다. C·N segment에서 `2634`(또는 다른 queue 장치 읽기)는 H가 남긴 항목이 있어도 `external read queue empty`로 멈춘다.

## carry와 Z(결정 3·4)

- [F] **Z 소비 block 2곳**(결정 3, player C1 결정 3과 controller C1 결정 3의 선례):
  - `de8f4`: Z = (BYTE `-7699(A5)` = 0), 주소 = A5 + sext(`8967`)의 24-bit가 work RAM(`100000..1fffff`)이 아니면 `unsupported animation select e1 flag source`. 근거 [F]: 유일 선행 `de8ee`은 `JSR ca50`이고 `ca50`은 같은 A5로 `TST.B -7699(A5); RTS`이며 `RTS`는 A5를 바꾸지 않는다. mirror A5(`1f8000`)와 24-bit 위 bit는 허용(C1과 같음).
  - `de938`: Z = (BYTE `(A0)` = 0), A0가 정확히 `10fdb0` `10fdb1` `100004` `100005` 중 하나가 아니면 같은 오류. 근거 [F]: 유일 선행 `de92e`은 `JSR 4a974`이고 `4a974`는 모든 경로에서 `TST.B (A0); RTS`(`4a9b0`/`4a9c6`)로 끝나며 A0는 `7db0(A5)+slot`(A5 := `108000`) 또는 `100004+slot`이다. controller C1 `ac1_flag_zero`·controller C2 `ac2_credit_flag`와 같은 목록·같은 정확 비교다(mirror `1ffdb0`, 위 bit `ff100004`도 거부; 단위 시험이 확인).
  - 이유: RAM 다시 읽기는 효과가 없지만 장치 주소를 다시 읽으면 원본에 없는 두 번째 읽기가 된다. `AnimationMachineState`는 C만 운반하므로 public header와 dispatcher는 바꾸지 않는다.
  - 시험: 단위 시험의 Unicorn 직접 진입은 SR Z를 그 BYTE = 0과 같게 둔다. V1 native(SR Z = 0으로 시작)의 직접 진입은 출처 BYTE ≠ 0인 world만 쓰고(`de938`은 A0를 네 BYTE 중 하나로 둔다), Z = 1 쪽은 node·natural run(`de8ee` → `ca50` → `de8f4`, `de92e` → `4a974` → `de938`)이 덮는다. 실제 ROM 차분은 두 쪽을 모두 실제 사슬과 선언 진입으로 비교한다.
- [F] **carry**(결정 4): E1에는 C 소비자도 C 생산자도 없다. 모든 E1 block 뒤 C는 Unknown이다(dispatcher 기본). `carry_preserving_pc`에는 case를 더하지 않고 주석 두 줄만 남긴다. map-transfer `185f4`(`ANDI.B #fe,CCR; RTS`)가 `18364`의 호출자 `ded50`에 Clear를 돌려주지만 `ded50`은 C를 읽지 않는다.

## block 의미(요약)

- **`2634`**: D0.B := BYTE `300000`(queue) ∧ `70`, ≠ 0 → `2648 RTS`, 아니면 `2642`: BYTE `7002(A5)` := `ff` → `2648`.
- **`18364`**(clip [I]): D6.W := ASR4(WORD `14(A0)`) + 6, D4 += D6, D7 := `20`(LONG), D4 += D2, D7 += D2, D4.W ≥ D7.W → `185f4`. `1837c`: D7 −= D2, D4 −= D2, 빌림 → `18384`(D0 −= D4, D2 += D4, D4 := 0 LONG). `1838a`: D7 −= D2, 빌림 → `18390`(D2 += D7). `18392`: D4 −= D6, D6.W := ASR4(`80` − WORD `18(A0)`), D5 −= D6, D7 := `1f` + D3, D5.W ≥ D7.W → `185f4`. `183aa`: D7 −= D3, D5 −= D7, 빌림 → `183b8`, 아니면 `183b2`(D1 += D5, D3 −= D5, D5 := 0 LONG). `183b8`: D5 += D7, D5.W ≥ D3.W → `183c4`, 아니면 `183c0`(D3 := D5 + 1). `183c4`: D5 += D6 → `183c6`(map-transfer).
- **`de8ca`**: WORD `78` := `709b`(7a = 0) / `735b`, WORD `76` := 0, (A6) := `de8ee`(들어감). **`de8ee`**: `JSR ca50`; `de8f4`(Z) → `de910` / `de8f8`(A0 := `de49e`, text). **`de910`**: D0.W := 7a, `JSR 4e186`; `de91a`: D1.W ≠ `ffff` → `de964`(A0 := `de4c2`, text, → `de978`), 아니면 `de922`: WORD 76 ∧ `10` ≠ 0 → `de94c`(`de4c2`), 아니면 `de92e`(`JSR 4a974`) → `de938`(Z) → `de944`(`de48c`) / `de93c`(`de4b0`) → `de948` → `de950`(text) → `de960` → `de978`: WORD 76 += 1, `RTS`. text = D0.W := WORD 78, A1 := `e84c8`, `JSR 3918`.
- **`de97e`**: WORD 68 / 1e := `c0`, `JSR 8ff4`; `de990`: D0.W := `ddc`, D1.B := 0, `JSR 8ebe`; `de99e`: BYTE 15 bit 2 := 1, D0.W := `a0`, D1.W := `1d8`, A1 := 0, `JSR 43e04`; `de9b8`: A0 := A6 + 26, WORD 20 := `13a`, LONG 22 := LONG `2000c0`, D0.W := `100`, A1 := LONG(LONG 22 + 4), `JSR 49f8c`; `de9e0`: (A6) := `de8bc`, `RTS`.
- **`de9e8`**: 68 / 1e := `60`, lights `deb` `dec`, 43e04(`a0`, `1a0`); `dea2a`: BYTE 15 bit 2, WORD 76 := 4, BYTE 62 := 0, WORD 82 := `ffff`, BYTE 84 := `ff`, (A6) := `dea50`, `RTS`. **`dea50`**: WORD 76 −= 1, 0 → `dea58`(76 := 4, BYTE 62 += 1); `dea62`: BYTE 62 bit 0 → BYTE 14 := BYTE 1a / 아니면 BYTE 19; `dea7c`: D0.W := 7a, `JSR 4e186`; `dea86`: D1.W = `ffff` → `deb18 RTS`; `dea8e`: push D2.W, BYTE 84 ≠ 0 → `deab2`(84 := 0, WORD 82 := D2.W), 아니면 `dea98`: D2.W = WORD 82 → `deaae`, 아니면 `deaa0`(82 := D2.W, D0.W := `1ac2`, `JSR 3af8`); `deaba`: pop D2.W, D2.W <<= 2(push), A0 := LONG(`de600` + 4·7a), D2 := LONG(A0 + D2.W), A0 := A6 + 26, 20 := `13a`, 22 := LONG `2000c0`, D1.W := D2.W × 4, A1 := LONG(LONG `2000c0` + sext(D1.W)), D0.W := `100`, `JSR 49f8c`; `deb02`: pop D2.W, WORD 32 := WORD(`de630` + D2.W + 2), WORD 2e := WORD(`de630` + D2.W), `JSR de8bc`.
- **`deb1a`**: 68 / 1e := `c0`, light `ddd`; `deb3a`: BYTE 15 bit 2, D2.W := 7a × 4, D0.W / D1.W := WORD 쌍 `de640`, A1 := 0, `JSR 43e04`; `deb5e`: D0.W := 7a, A0 := A6 + 26, 20 := `13a`, 22 := 창 LONG, A1 := `de5f0`, D0.W × 4, D0 := LONG(`de5f0` + sext(D0.W)), A1 := 창 LONG, D0.W × 4, A1 := LONG(A1 + sext(D0.W)), D0.W := `100`(D0 상위는 표 LONG의 상위), `JSR 49f8c`; `deb9c`: (A6) := `de8bc`, `RTS`.
- **`deba4`**: 68 / 1e := `80`(8ff4 없음), 43e04(`de588` 쌍); `debce`: A0 := `defdc`, D0.W := `1e`, `JSR 28ae`; `debde`: WORD 7a(A0) := WORD 7a, D0.W := `a`, `JSR 49a84`; `debee`: D0.W += `14`, WORD 76 := D0.W, 78 := 0, BYTE 63 / 62 := 0, (A6) := `dec10`, `RTS`. **`dec10`**: `JSR 43e34`; `dec16`: BYTE 63 ≠ 0 → `dec30`, 아니면 76 −= 1(0 → `dec26`: 63 := 1) → `dec6c RTS`. `dec30`: WORD 78 = 0 → `dec38`(32 −= 2, 78 := `ffff`), 아니면 `dec46`: 32 += `a`, 부호 < `170` → `dec5c`, 아니면 `dec56`(63 := 2); `dec5c`: 부호 32 < `1b0` → `dec6c`, 아니면 `dec66`((A6) := `dec6e`). **`dec6e`**: BYTE 62 = 0 → `RTS`, 아니면 `dec78`: 부모 BYTE 62 += 1, 63 := 3, (A6) := `dec8c`(들어감). **`dec8c`**: 63 := 0, `4e186`(0): D1.W = 1이고 D2.W = 7a → 63 := 1; `4e186`(1): 같은 검사; `decd2`: 63 = 0 → `RTS`, 아니면 `decda`: D0.W := WORD(`de628` + 2·7a), `JSR 3af8`; `decee`: 76 := `1e`, 84 := 0, (A6) := `ded00`, `RTS`. **`ded00`**: `43e34`; 76 ≠ 0 → `ded98`(76 −= 1, `RTS`), 아니면 `ded0e`: 32 −= `10`, 부호 > `12c` → `RTS`, 아니면 `ded1e`(D0.W := 4, `JSR 3d7e`), `ded28`(A0 := `109156`, A1 := `df2d0`, D0..D5.W := 0 0 `16` `10` 0 `10`, `JSR 18364`), `ded50`(78 := 0, 32 := `12c`, 80 := 32, `28ae`(`dedb6`)), `ded72`(자식 7a, `28ae`(`dee36`)), `ded88`(자식 7a, (A6) := `ded9e`) → `RTS`. **`ded9e`**: `43e34`; 부호 WORD 78 ≥ `10` → `RTS`, 아니면 32 := 80.
- **`dedb6`**: 68 / 1e := `80`, light `ded`, 43e04(`de650` 쌍); `dedf4`: 76 := 5, `de9b8`과 같은 창 script(LONG(창 + `dc`)); `dee22`: (A6) := `dee28`(들어감); `dee28`: `43e34`, `49fc6`, `RTS`.
- **`dee36`**: 68 / 1e := `a0`; `dee48`: D0.W := WORD(`de580` + 2·7a), D1.W := 0, `JSR 8ebe`; `dee5e`: A0 := `dfbc0`, D0.W := 7a, 0/1/2/3 → 20 := 2 / `a` / `12` / `1a`, A1 := LONG(`dfbc0` + 4·7a), D0.W := `100`, `JSR 49f8c`(그 밖 → 건너뜀); `deef0`: WORD 2e := 부모 WORD 2e, 32 := `188` − 8, LONG 36 / 3a := 0, D0.W := `73c`, `JSR 3c44`; `def20`: D0.W := `73e`, `JSR 3af8`; `def2a`: (A6) := `def32`, `RTS`. **`def32`**: LONG 3a += `ffffb000`, `JSR 43ea4`; 무부호 32 < `148` → (A6) := `def58`; `JSR 49fc6`; `RTS`. **`def58`**: 3a := 0, 32 := `148`, script `dfbd0`; `def80`: 76 := 4, (A6) := `def8c`(들어감). **`def8c`**: `43e34`, `49fc6`, 76 −= 1, 0 → script `dfbb0`, (A6) := `defc0`(들어감). **`defc0`**: LONG 36 := `30000`, `43e34`, `49fc6`, `43ea4`, `RTS`.
- **`defdc`**: 68 / 1e := `40`; `defee`: D0.W := 7a × 4, push D0(LONG), 43e04(`de588` 쌍); lights `b00`(D1.B := 1) 3회; `df038`: pop D0(LONG), 20 := `13a`, A1 := LONG(`de5e0` + sext(D0.W)), script; `df052`: 63 / 62 := 0, WORD 7c := 0, (A6) := `df06c`, `RTS`. **`df06c`**: `4e186`(0/1): D1.W ≠ `ffff`이고 D2.W = 7a → 62 := 1; `JSR de8bc`; `df0b0`: 부모 부호 BYTE 63 < 2 → `RTS`, 아니면 78 := 0, (A6) := `df128`, 62 = 0 → `RTS`, 아니면 script `de5c0`, (A6) := `df0f2`. **`df0f2`/`df128`**: 부호 WORD 78 < `20` → D2.W := 78, `JSR df272`/`df2c0`, 78 += 1; 아니면 부모 BYTE 62 := `ff`, BYTE 85 := 1 / 0, (A6) := `df15e`; `JSR de8bc`; `RTS`. **`df15e`**: 62 := 0, `4e186`(0/1): D2.W = 7a이고 D1.W ≠ `ffff` → 62 := 1, D1.W = 1이면 62 := 2; `df1c0`: BYTE 62 = BYTE 85 → `df22a`, 아니면 85 := 62, 0 → D2.B := `20`, `df2c0`, script `de5e0`; 아니면 D2.B := `20`, `df272`, script `de5c0`, 62 = 2 → (A6) := `df230`; `df22a`: `JSR de8bc`, `RTS`. **`df230`**: script `de5d0`, 76 := 2, (A6) := `df254`(들어감); `df254`: 76 = 0 → 꼬리, 아니면 76 −= 1, 0 → D2.B := `20`, `df272`; `JSR de8bc`, `RTS`.
- **`df272`**: A0 := LONG(`de598` + 4·7a), D0 := BYTE 19(MOVEQ #0 뒤), D1.W := WORD (A0), MOVEM 저장, `JSR 8cda`; `df292`/`df2aa`: MOVEM 복원, D0 := BYTE 1a / 1b, D1.W := WORD 2(A0) / 4(A0)(`df292`은 다시 저장), `JSR 8cda`; `df2be RTS`. **`df2c0`**: D0.B := BYTE 19, D1.W := `dea`, `JSR 8cda`, `RTS`.
- [I] 이름: 7a = 플레이어(0/1) 또는 캐릭터(0..3) 색인, 76 = 타이머, 78 = 단계 수, 62 / 63 = 선택 상태, 84 / 82 = 커서 깜박임과 직전 선택, 85 = 직전 선택 상태, 32 / 2e = 좌표. 원본 이름이 아니다.

## seed·fixture

- **V1(`tools/unit_fixture_specs/se1.py`)**: player C1 spec의 공용 부분(routing 해석, `first_unrouted`, carry oracle, node/natural/callee family)을 그대로 쓰고 단위 부분을 바꿨다. C 소비자가 없어 chain family는 없다.
  - block: 222 시작 모두(Z 소비자 포함, 위 조건), `2634`는 queue BYTE(`(300000, 1, v)`)를 선언. native tracer는 선언 queue만 허용한다.
  - node: 생성 callback 8개와 설치 값 19개((A6) := 진입). hint: WORD 7a 0..3, 타이머·좌표 경계, Z 출처 BYTE, `10fd82` := 0(4a974가 BIOS를 부르지 않게), credit BYTE, `4e186`의 slot node `1009a8`/`100a6c`(LONG = `270e` → D1 = `ffff`, BYTE 9c 1/2, BYTE 98).
  - natural: IO pack frame 21개(P1 094 13, P1 068 4, P1b 094 2, boot-title-start 2)에서 callback당 최대 4개(`NATURAL_CAP`). reinstall: 생성 callback·`28ae` 자식 14개(같은 frame의 같은 종류 자연 node에 callback LONG만 선언). [I] 이미 초기화된 node를 다시 초기화하는 world이며 native와 C++가 같은 상태를 받으므로 비교는 유효하다.
  - callee: `2634`(queue) `18364` `de8bc` `df272` `df2c0`.
  - error: 내부 PC 1,128, 홀수 PC, Z 출처(`de8f4` A5 = `8000`/`400000`, `de938` A0 = `10fdb2` `100003` `1ffdb0` node), `de8ee` → `de8f4`(실패 PC 이동), queue 비움 / 다른 장치, 홀수 node / stack / A0 / 부모, 실행 후 실패(`de8d2`→`de8ee`, `dec66`→`dec6c`, `df0fc`→`df122`, `18384`→`18392`).
  - negative: RAM bit, 레지스터, stop, queue 추가, queue 값(`2634`).
- **단위 시험(Unicorn 생성기, `tools/generate_animation_machine_select_e1_test_table.py`)**: 합성 physical byte(원본 자료 아님, 자료 영역만): 표 `de580..de660`, `dfbb0..dfbe0`, 목록·digit `dfc00..dfcc0`(`de598`/`de600` 포인터의 대상), 창 LONG `2000c0` := `200100`, 창 표 `200100..2001e0`(bank 200000). 행: single(시작 222개 × 들어오는 C 3가지, 모든 분기 양쪽), path(52 진입), error(26; 실패 PC 6개 이동), zero-step, 내부 PC 1,128 정확 오류, rollback 탐침, 경계 stop(routed 출구 20개 전부). 손 규칙(rules): 2634 BYTE 마스크·queue, 18364 clip의 ASR 부호·`SUBI.W #fffa`·MOVEQ LONG·무부호 동점(직후 레지스터까지 확인), 각 block의 WORD/BYTE 크기·상위 유지, 부호 비교 경계(`165/166/7ffa`, `1af/1b0/8000`, `13c/13d/8010/800f`, `f/10/7fff/8000`, `1f/20/8000`, BYTE `80`/`2`), 무부호 `148/147/8000`, Z 재계산(0 / ≠ 0 / 이웃 BYTE / mirror / 24-bit / guard), credit 목록 정확 비교, 표 색인(부호 확장 `fffc` 포함), 창 LONG + 4 / + dc, MOVEM 순서, stack WORD/LONG, 설치 값 진입 / 설치 후 RTS.

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `15b827242abca643…` → `565880ca271b7cff4fabe49c3d386553f46ec9d18b1965e30f02318cabec22c5`, `animation_machine_internal.h` `5e2ad9ef19d159ba…` → `9a80738e3a1b1fbc8dc9782331426daf2406f2706d8cc86af2a2bed1b0c58a32`(이 단위의 공유 수정; 옛 값은 `# select E1 refresh:` 주석).
- [F] `tools/verify_animation_machine.py` `SOURCES`에 `animation_machine_select_e1.cpp`.
- [F] E1 PC(`2634..264a` `18364..183c6` `de8bc..df2d0`)를 "실행부 없음" 탐침으로 쓰는 시험·검증기는 없다(작업자 grep: `engine/tests`, `tools/*.py`, `tools/unit_fixture_specs`). stage_area `UNROUTED_NEIGHBOURS`, area_clear `negatives`, input 이웃 목록에도 E1 PC가 없다. 그래서 바꾼 기대값은 위 두 가지뿐이다.
- [F] 경계가 맞닿은 범위: FR1 `de660..de8bc`(FR1 시험 RANGES, 자료 탐침 `de65e`), map-transfer `183c6..`(`18364`의 꼬리), player C1 `ca50`. `make test` 통과, V1 회귀 fr1·pc1 통과(아래).
- [I] native 사슬이 E1 PC(`de8bc` `de8ca` `de8ee` 등)를 첫 routing 밖 PC로 멈추던 V1 spec·검증기는 더 진행한다(정지는 routing에서 계산된다). 메인 runner의 회귀·legacy 단계가 확인한다.
- [F] **IO 비교**: fixture `fx-c-input-read` / `fx-n-input-read`는 frame 3에서 `2634`가 입력 port를 읽어 native guard `undeclared-device-read`(segment C / N)로 끝난다. E1 전에는 C++가 routing 밖 `2634`에서 `unsupported animation machine PC`로 멈춰 `guard-behind-frontier`(frontier H / N `2634`, 확인됨)였다. 초안(`6308f75`)에서는 C++가 frame queue 끝에 붙은 guard 읽기 값을 소비해 frame을 끝내 `guard-bad`가 됐다(결정 2 개정 이유). 개정 뒤에는 두 fixture 모두 `animation machine external read queue empty`(보존)로 멈춰 `guard-ok`다(아래 "IO 수용 키").
- [F] 결정 2 개정의 공유 수정: `engine/include/ms5/animation_machine_frame.h`(queue 규칙 주석 세 줄), `engine/src/animation_machine_frame.cpp`(segment 본문을 이름 없는 namespace의 `run_segment`로 옮기고, 공개 `run_animation_frame_segment`가 C·N에서 queue를 보류·복원), `engine/tests/animation_machine_frame_test.cpp`(`held_queue`: segment H는 `2634`에서 `(300000, 1, 70)`을 읽고 N·C는 같은 queue로 `external read queue empty` + 항목 유지, frame의 controller LONG `2634` + 8번째 항목은 Execute에서 checked 보존 실패·Skip에서 항목 1개 남김, pass의 node callback `2634`도 실패; 85 → 91 checks). 보류를 끈 변이에서 `held_queue` 첫 N 행이 실패한다(작업자 확인). `animation_machine.cpp`·`animation_machine_internal.h`는 바뀌지 않아 `CPP_PINS`는 그대로다.

## IO 수용 키(acceptance)

[F] `verify_animation_machine_io.py` `acceptance()`의 키. 기준은 player C1 IO(scratch `c1/ioA`: 모두 true), E1 초안(`e1/ioA`, `6308f75`), 개정(`e1/io_fix_full`, 같은 HEAD + 결정 2 개정, `--workers 2`, `MS5_SEED_DIR=artifacts/stage_entry_body`).

| 키 | 뜻 | C1 | E1 초안 | 개정 |
|---|---|---|---|---|
| `no_verifier_errors` | 검증기 예외 run 없음 | true | true | true |
| `zero_mismatches` | 비교 frame·frontier 너머 frame 불일치 0 | true | true | true |
| `no_unexpected_cpp_errors` | guard frame 밖 C++ 오류 0 | true | true | true |
| `frontiers_confirmed` | 첫 실패가 routing 밖 PC인 run마다 segment 탐침으로 그 PC가 확인됨 | true | **false**(15 run) | **false**(15 run) |
| `no_other_first_failures` | 첫 실패가 `unrouted` / `guard-ok` / `guard-behind-frontier`뿐 | true | **false**(fixture 2) | true |
| `guards_match_or_behind_frontier` | native guard frame마다 C++가 대응 오류로 보존 실패하거나, 확인된 frontier 뒤 | true | **false**(fixture 2) | true |
| `chain_no_divergence` | 순수 C++ 사슬 분기 0 | true | true | true |
| `negatives_ok` | 음성 시험 모두 검출 | true | true | true |
| `full_run` | 전체 관측 run | true | true | true |

- **`no_other_first_failures` / `guards_match_or_behind_frontier`**: 원인은 fixture 2개의 `guard-bad` 하나뿐이다(위 결정 2). 개정 뒤 두 fixture는 `guard-ok`(`expected_error` = `error` = `animation machine external read queue empty`, `preserved` true)이고, 사슬 끝 검사(`check_from_chain`)도 ok가 됐다.
- **`frontiers_confirmed`**: guard 문제와 무관하다. fixture run은 `guard-bad`라 frontier를 만들지 않았다. false인 15 run(P1 case 68–71, 94, 95, 100, 101, 106, 107, 110, 111; P1b 68, 94; boot-title-start)은 C1 기준에서 E1 PC `deba4`(확인된 frontier)에서 멈췄다. E1이 `deba4`를 routing하자 같은 run이 더 진행해(P1 68 계열 frame 225 → 288, 94 계열 5 → 72, boot-title-start 125 → 192) 새 정지 PC에 닿았다. 그 PC는 `4e8e6`이다: segment 탐침(scratch `fix/probe2.py`, `confirm_frontier(N, 4e8e6)`)이 다섯 대표 run(P1 68/94, P1b 68/94, boot-title-start)에서 모두 ok이고 `4e8e0`은 routing돼 있다. `4e8e6`은 player C1 block `4e8d6`(`BNE.W 4e8e6`)·`4e8e0`(fall-through)의 직선 다음 PC다(`animation_machine_player_c1.cpp` 216–217행; C1 계약은 뒤 단위 정지로 적었다). 검증기 후보 목록(`locate_frontier`)은 그 frame의 `unr_first`·`unr_new`와 key frame의 `tbs`뿐인데, 이 frame들은 key frame이 아니고(`tbs` 없음) `4e8e6`은 관측 당시 routing 기준으로 그 frame의 `unr_new`에 없다(P1 68은 run 전체에 없음, boot-title-start는 frame 578에 처음). 그래서 후보 26/29개를 모두 시도해도 확인되지 않았다. `4e8e6`은 이 단위에서 routing하지 않는다(뒤 단위 몫). 그 단위가 `4e8e6`을 routing하고 다음 정지가 후보 목록 안에 있으면 이 키는 다시 true가 될 것으로 본다 [I].
- [F] 개정 전후 차이는 두 fixture뿐이다. per-config 수치에서는 `fx-c-input-read` / `fx-n-input-read`의 `first_failure_guard-bad` 1 → `first_failure_guard-ok` 1, `guard_not_ok` 1 → `guard_ok` 1만 바뀐다. 나머지 run의 matched / beyond / unrouted / 사슬 / 첫 실패 종류는 같다. 일치 frame 166,744(P0 81,600, P1 76,128, P1b 7,560, boot-demo-0 381, boot-title-idle 600, boot-title-start 192, fx-bios-call 3, fx-c 3, fx-n 3, fx-queue-short 1, fx-start-c79a 273), 불일치 0, C++ 오류 0, frontier PC는 `48350`(D, boot-demo-0, 확인됨) 하나.

## 결정

1. **범위.** E1 = 계획 §4.2 그대로 222 block, 3 범위. C1 routing 뒤 재측정에서도 같다. `2622..2634`는 넣지 않는다(실행되지 않음). 계획 결정 6(`ca50` `ca3a` `b0c` `e6496`은 C)을 따른다.
2. **입력 port `2634`와 segment별 queue(개정, 메인 IO 재실행 뒤).** 실행부는 그대로 선언된 외부 읽기 queue로 읽는다(새 장치 규칙 없음; 기존 `external_queue_device`가 BYTE `300000`을 이미 포함). 단위 시험·V1·실제 ROM 차분은 queue BYTE를 선언한다. 바뀐 것은 frame 구동기의 queue 배분이다.
   - **옛 동작(`6308f75`).** frame 구동기(`animation_machine_frame.cpp`)는 queue 하나를 H → C → N에 그대로 넘겼고, `am_read`(`animation_machine.cpp` 24–31행)는 segment와 상관없이 주소·크기가 맞는 앞 항목을 내줬다. 원래 초안은 "C·N에서 읽을 때 queue는 H가 이미 다 썼으므로 비어 있다"고 가정했다.
   - **가정이 틀린 이유 [F].** IO 관측기는 frame queue를 `q = hq + cq + nq`로 만든다(`tools/observe_animation_machine_io.py` 612–614행). `cq`/`nq`는 `D.n_queue(dev)`(`tools/verify_animation_machine_frame_driver.py` 392–401행)가 C·N 장치 읽기 log에서 고른 `EXT_SIZE` 장치(48행: BYTE `300000` `340000` `380000`, WORD `3c0006`) 읽기다. 이 장치 집합은 관측기의 `h_inguard`(466–470행)가 N·C에서 `undeclared-device-read`로 멈추는 장치와 같다(IRQ 안은 phase `I`라 log에 들어가지 않는다: `verify_animation_machine_frame_irq.py` 300행). 멈춤 요청 뒤에도 그 읽기 자체는 log에 남으므로, guard frame의 `q`에는 guard를 일으킨 읽기 값 하나가 H 항목 뒤에 붙는다. fixture frame 3에서 `q`는 `3c0006 3c0006 380000 300000 340000 300000 340000` + `300000` 8개다(qchk `order:mode0:…`). 선행 단위의 IO 검증기(`verify_animation_machine_io.py` 67행 주석 "the queue is already consumed by H")와 guard 증거 시험(749–750행, 완성 frame의 H queue만 줌)도 같은 가정을 쓴다. 구동기 segment를 하나씩 돌린 탐침(scratch `fix/probe3.py`): `fx-c-input-read` H 뒤 남은 항목 `(300000, 1, ff)`를 C의 `2634`(controller LONG = `2634`)가 소비했고, `fx-n-input-read`는 H 뒤 `(300000, 1, 0)`이 C(`c7fc`)를 지나 N의 `2634`에서 소비됐다. 그래서 C++가 frame을 끝냈고 검증기는 `guard-bad`("C++ completed where native did not complete the frame")로 판정했다. E1 전에는 `2634`가 routing 밖이라 그 PC에서 `guard-behind-frontier`였다.
   - **새 동작.** C·N segment에는 선언된 외부 읽기가 없다. queue는 H(입력·raster 표본기)만 읽는다. `run_animation_frame_segment`(C·N)는 segment 동안 H가 남긴 항목을 보류했다가 끝나면(성공·실패 모두) 그대로 되돌린다. 그래서 C·N의 queue 장치 읽기는 `animation machine external read queue empty`(checked, frame·pass 함수는 입력 보존)로 멈추고, 남은 항목은 `remaining`에 그대로 남는다(`queue-extra-entry` 음성 시험이 계속 잡는다). 전달된 IRQ는 자기가 앞에 넣은 두 항목(`320000` BYTE, `3c0006` WORD)만 읽는다(기존과 같음). card·credit BIOS 재실행도 보류된 queue에서 시작한다. 새 오류 문자열은 없다.
   - **native 의미와의 대응 [F].** 관측기 범위 선언 "direct input / raster port reads in N or C = undeclared-device-read"(관측기 1293행)와, N·C 장치 log(`300000..3fffff`, `d00000..d00fff`)에서 status `d00046` 말고 다른 읽기(`320000` 포함)도 `undeclared-device-read`로 분류하는 `classify_guard`(700–701행)와 같다. status BYTE `d00046`은 queue가 아니라(`am_read` 21–23행) 그대로 허용된다.
   - **선택하지 않은 안 [I].** (b) `2634` 실행부만 segment를 알게 하는 안은 실행부에 segment 정보를 넣어야 하고, 다른 C·N queue 읽기(예: controller LONG = `349c` 기록기, 검증기 증거 `undeclared-device-read-C`)에 같은 빈틈을 남긴다. 검증기나 fixture를 고치는 안은 금지 범위다. (a) 구동기 배분이 native 의미와 같고 공유 수정이 가장 작다(`animation_machine.cpp`·`animation_machine_internal.h`는 바뀌지 않아 `CPP_PINS` 갱신 없음).
   - **선례.** IRQ 전달이 같은 형식의 segment 제한이다: 자기 항목 두 개를 앞에 넣고, 더 읽으면 `animation irq external read overrun`, 남은 IRQ 항목은 지운다(`animation_machine_frame.cpp` `deliver_irq`). 옛 D1·controller 검증기는 N·C의 `EXT_SIZE` 읽기를 선언 queue로 셌지만 자연 관측에서 그 수는 0이었다(D1 보고 `natural_matched_frame_tallies.n_queue` 0, `node_reads` 0). 아래 구현 기록의 legacy frame 검증기 재실행으로 변화 없음을 확인한다.
3. **RTS를 넘는 Z.** `de8f4`는 player C1 결정 3(BYTE `-7699(A5)`, work RAM만), `de938`은 controller C1 결정 3(BYTE `(A0)`, credit BYTE 4개만, 정확 비교)을 그대로 쓴다. 공용 header·dispatcher는 바꾸지 않는다.
4. **carry 보존 목록.** E1은 C를 읽지도 만들지도 않으므로 case를 더하지 않는다. 모든 E1 block 뒤 C Unknown. 주석만 남긴다.
5. **표·창 읽기.** live bus, 상한 검사 없음(원본과 같음). 단위 시험은 합성 byte만 선언하므로 선언 밖 색인은 `missing or ambiguous physical program bus ROM byte`로 확인하고, 원본 값은 V1·실제 ROM 차분이 비교한다.
6. **`18364` → `183c6`.** `183c4`는 PC := `183c6`으로 끝나고 다음 dispatch가 map-transfer 실행부로 간다(함수 공유 꼬리). map-transfer 쪽은 바꾸지 않는다.
7. **실행부 파일·오류 문자열.** 위 "공통 규칙". 오류 문자열 2개.
8. **다음.** 계획 순서대로 C2(+190 단계는 C2·C3을 함께 연결한 뒤 IO 확인).

## 미확인

- [U] node field·전역 BYTE의 의미(7a 76 78 62 63 82 84 85 32 2e 80, `7002(A5)`), 표의 의미(`de580`..`de650`, `dfbb0`..`dfbd0`, 창 표), `18364`의 clip 의미.
- [U] IO 관측에서 실행되지 않은 이 단위의 block 24개(위 목록; 초상 선택 `dee8a..deeec` 중 7a ≠ 0 쪽, `df1ba..df1f6`, clip 분기 등)는 closure로 들어왔다(V1 선언 상태·실제 ROM 차분으로만 확인).
- [U] 재설치 world와 IO pack 자연 node 상태의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(player C1·FR9와 같음).
- [F] fixture 두 개의 guard 일치는 결정 2 개정 뒤 IO 재실행으로 확인했다(위 "IO 수용 키"). [U] 첫 정지 C 14와 `frontiers_confirmed`의 회복은 `4e8e6`을 맡는 뒤 단위의 IO 재실행으로 확인한다.
- [U] 결정 2 개정은 "C·N에는 선언된 외부 읽기가 없다"는 IO 범위 선언(관측기 guard)을 C++에 옮긴 것이다. 실제 기기에서 C·N 코드가 입력 port를 직접 읽는 경로가 있는지(관측 밖 상태)는 확인하지 않았다. 그런 경로는 지금 checked 정지로 남는다.
- [I] 실제 ROM 차분의 native 미정지(N=300에서 26건)는 무작위 world에서 native 쪽이 끝나지 않거나 예외로 끝난 경우다: 무작위 script를 따라간 interpreter `49fc6..4a000`, BYTE `10fd82` ≠ 0일 때 `4a974`의 BIOS 호출 `c00450`(fetch unmapped), 무작위 포인터 읽기. 건너뛴 경우로만 세며 C++ 비교에는 들어가지 않는다.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_select_e1.cpp`(case label 222 = `starts_E1.txt`와 집합 일치; 공용 함수 `se1_get` `se1_put` `se1_signed_word` `se1_signed_byte` `se1_asr4` `se1_shape` `se1_light` `se1_index` `se1_window` `se1_script_a0` `se1_script` `se1_place_a0` `se1_place` `se1_install` `se1_install_return` `se1_zero` `se1_count` `se1_mark` `se1_query` `se1_same_slot` `se1_text` `se1_flag_ca50` `se1_flag_credit`(결정 3) `se1_digits` `se1_save` `se1_restore` `se1_next_digit` `se1_portrait`), `engine/tests/animation_machine_select_e1_test.cpp`(생성 구역 + 수작성 규칙), `tools/generate_animation_machine_select_e1_test_table.py`(생성기; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; 약 80초), `tools/unit_fixture_specs/se1.py`(V1 spec).
- [F] `make -j4 all test`(작업자): 종료 0, 경고 0, Python 310 OK. E1 시험 줄: `animation machine select se1: 813 fixtures (691 single-block, 96 path, 11 with the 2634 queue BYTE, 26 checked error (6 with a later failing PC)), 222 blocks, 4924 calls, 36210 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 출구 20개 모두 정지로 덮임.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, E1 시험): 빌드 경고 0, 실행 종료 0, runtime error 0.
- [F] V1 se1(작업자 1회, `--workers 3`, `MS5_SEED_DIR=artifacts/stage_entry_body`, scratch `work/v1_try1`): fixture 2,102개(block 802, node 49, natural 64, reinstall 14, callee 9, error 1,148, failpc 5, negative 11) failed 0, 방문 시작 222/222, 빠진 후속 0, 도달 못한 분기 결과 0, carry oracle Unknown/Clear/Set = 939/4/0(Clear 4는 `185f4`를 거친 run), 소비된 queue 읽기 12.
- [F] 변이(scratch `mut/run_mut.py`, `mut/mutants.py`; 실행부 293개 + dispatcher 범위 4개 = 297개): 1회째 288 kill. 살아남은 9개 중 7개는 시험 빈틈이었다 — clip 동점 5개(`18364-cmp` `1837c-cmp` `18392-cmp` `183aa-cmp` `183b8-cmp`: 정지 PC에 더 긴 경로로도 닿아 `ends_at`이 통과했다; 직후 레지스터 검사로 바꿈), `script-noext`(`MOVEA.L (A0,D0.W)` 부호 확장: 음수 색인 `fffc` 규칙), `df096-long`(`CMPI.W #ffff,D1`의 WORD: D1 = `1ffff` 규칙). 규칙을 더한 뒤 9개 재실행 `killed 7 of 9`. 남은 2개는 동등이다:
  - `1838a-cmp`(`BCC`를 `>`로): 동점이면 새 D7.W = 0이고 `18390 ADD.W D7,D2`가 0을 더하므로 상태가 같다.
  - `deaba-d2-word`(`LSL.W #2,D2`를 D2 상위 지우기로): D2.W만 push·색인에 쓰이고 바로 뒤 `MOVE.L (A0,D2.W),D2`가 D2 전체를 덮는다.
- [F] 실제 ROM 차분(scratch `realrom/`; `batch.cpp`는 C1판에 queue BYTE 필드를 더한 사본, `real_se1.py`는 C1 harness에 E1 world·Z 진입·queue·`POPS`(stack에서 꺼내는 진입의 stack 값) 추가, 계산 착지는 FR9 JMP와 옛 표 JMP를 trace 전체에서 기록해 분류): 300건 seed 1 `mismatches 0`(분류된 예외 0, `covered starts 206 of 222`, native 미정지 26건 건너뜀, 실제 사슬로 닿은 Z 소비자 `de8f4` 20 / `de938` 10). 60건 seed 7도 0.
- [F] V1 회귀(작업자, 이웃 spec 2개, `MS5_SEED_DIR=artifacts/stage_entry_body`): fr1(범위 `de660..de8bc`가 E1과 맞닿음) 1,631/1,631, pc1(`ca50` 공유) 1,264/1,264(모두 failed 0). 나머지 spec은 결정적 runner가 돌린다.
- [F] `dleft.py`(`MS5_REOBS`, routing `565880ca…`): 실행된 routing 밖 PC C **757** / E **12** / D 0, 예측 일치 frame **169,144**, 첫 정지 영역 C 14. 계획 §4.2 예측과 같다(E −206, +3,385 frame).
- **결정 2 개정 검증(작업자 Opus 5.5 / high, 같은 HEAD `6308f75` + 미커밋 개정; scratch `ms5-scratch/e1/fix/`)**
  - [F] `make -j4 all test`: 종료 0, 경고 0, Python 310 OK, `animation machine frame: 91 checks`(85 → 91). 보류를 끈 변이(`segment==AnimationFrameHead||true`)에서 `held_queue`가 assert로 실패했다. 원래 소스로 되돌린 뒤 다시 통과했다.
  - [F] IO fixture만(`--configs fx-c-input-read,fx-n-input-read,fx-bios-call,fx-queue-short,fx-start-c79a`, `--workers 2`, scratch `e1/io_fix`): 다섯 개 모두 `guard-ok`(fx-c / fx-n `undeclared-device-read` → `animation machine external read queue empty` 보존, fx-bios-call `bios-boundary`, fx-queue-short `external-read-queue-empty`, fx-start-c79a `system-return`), 일치 283, 불일치 0. 종료 1은 `full_run` false 때문이다.
  - [F] 전체 IO(`--workers 2`, scratch `e1/io_fix_full`): 위 "IO 수용 키"의 개정 열. 일치 166,744(초안과 같음), 불일치 0, C++ 오류 0, frontier PC `48350` 하나. 종료 1은 `frontiers_confirmed` false(`4e8e6`, 뒤 단위 몫) 때문이다.
  - [F] frame 구동기를 쓰는 legacy 검증기 4개(`verify_animation_machine_frame_driver.py`, `_frame_controller.py --declare game`, `_frame_irq.py`, `_frame_controller.py --declare demo`; `--workers 2`, scratch `fix/frames_*`): 모두 종료 0. 개정 전 보고(scratch `e1/frames_*`)와 비교해 다른 경로는 입력 SHA 3개(`animation_machine_frame.h` / `.cpp`, harness binary)와 실행 시간뿐이다. 범주·합계·tally는 같다(D1 54,400 complete, n_queue 0). frame 구동기를 부르는 곳은 이 네 harness와 `frame_io_acceptance`, `animation_machine_frame_test`뿐이다(grep). block 단위 legacy 검증기(frame_helpers, input, card_menu_close 등)는 구동기를 거치지 않아 다시 돌리지 않았다.
  - [F] V1 se1 1회(`--workers 1`, scratch `e1/v1_se1_fix`): 2,102/2,102, failed 0, 소비된 queue 읽기 12(초안과 같음).

## block 목록

[F] scratch `starts_E1.txt`(SHA256 `befbbe32a6f0f859038f740f204870a66a789bcd329dcaa1e78386648c401a9f`)와 같다.

- **`2634..264a`(3)**: `2634 2642 2648`
- **`18364..183c6`(11)**: `18364 1837c 18384 1838a 18390 18392 183aa 183b2 183b8 183c0 183c4`
- **`de8bc..de978`(24)**: `de8bc de8c2 de8c8 de8ca de8d2 de8da de8de de8ee de8f4 de8f8 de90c de910 de91a de922 de92e de938 de93c de944 de948 de94c de950 de960 de964 de978`
- **`de97e..deb9c`(30)**: `de97e de990 de99e de9b8 de9e0 de9e8 de9fa dea08 dea16 dea2a dea50 dea58 dea62 dea6c dea76 dea7c dea86 dea8e dea98 deaa0 deaae deab2 deaba deb02 deb18 deb1a deb2c deb3a deb5e deb9c`
- **`deba4..dedb4`(46)**: `deba4 debce debde debee dec10 dec16 dec1e dec26 dec2c dec30 dec38 dec46 dec56 dec5c dec66 dec6c dec6e dec76 dec78 dec8c dec9c deca4 decac decb2 decbc decc4 deccc decd2 decda decee decfe ded00 ded06 ded0e ded1e ded28 ded50 ded72 ded88 ded94 ded98 ded9c ded9e deda4 dedae dedb4`
- **`dedb6..defda`(41)**: `dedb6 dedc8 dedd6 dedf4 dee22 dee28 dee2e dee34 dee36 dee48 dee5e dee70 dee86 dee8a dee92 deea8 deeac deeb4 deeca deece deed6 deeec deef0 def20 def2a def32 def40 def4a def50 def56 def58 def80 def8c def92 def98 defa0 defba defc0 defce defd4 defda`
- **`defdc..df2ce`(67)**: `defdc defee df00e df01c df02a df038 df052 df06c df076 df07e df086 df08c df096 df09e df0a6 df0ac df0b0 df0be df0d2 df0ea df0f0 df0f2 df0fc df116 df11e df122 df126 df128 df132 df14c df154 df158 df15c df15e df16e df176 df17e df18c df192 df19c df1a4 df1ac df1ba df1c0 df1cc df1d6 df1de df1f6 df1fa df202 df21a df224 df22a df22e df230 df248 df254 df25c df264 df26c df270 df272 df292 df2aa df2be df2c0 df2ce`
