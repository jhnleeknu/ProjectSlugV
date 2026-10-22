# 영역 C 단위 C1(플레이어 슬롯 관리자 `4e68e` 계열과 플레이어 객체 진입 `1d1f4`, 139 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §8 "C1 상세 명세"를 기준으로 삼고, 구조·공통 규칙은 FR9 계약(`animation-machine-frontier-fr9-contract.md`)을 따르며 다른 점만 적는다. 계획의 메인 결정 7에 따라 단위 이름은 C1, 파일 접두어는 `player_c1`(C++) / `pc1`(V1 spec)로 해서 controller 단위 C1~C3(`animation_machine_controller_c1.cpp`, `unit_fixture_specs/c1.py`)과 겹치지 않게 한다. 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기 `2001e4`(`4f2e6`)만 CPU 주소이고 물리 오프셋은 `bank_base + 1e4`다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `04ec345`(branch `claude/area-c-plan`, 계획 커밋; routing은 main `92dbff7` = FR1..FR9). routing 기준 `engine/src/animation_machine.cpp` SHA256 `7233eefce1281ff3fdda6f44f97948290b350786f895b2734fa6b2a18d7a534d`, `animation_machine_internal.h` `b870dcc5f415fc18b92fa0b2e7c97b469c2302ee3d5d2bf61d773643b44ed25e`.
- [F] 관측 입력: native IO 관측 `artifacts/animation_machine_io_native`(읽기 전용; state pack `states/P1/068.pack.gz` `094.pack.gz`, `P1b/094.pack.gz`, `boot-title-start/boot.pack.gz`)와 계획의 보정 관측 `ms5-scratch/c1/reobs/`(실행 집합 측정용, 메인 결정 1).
- [F] 시작 목록: 계획 scratch `ms5-scratch/c1/starts_C1.txt`(139개, SHA256 `7d67c3729a79cc8c81f4f231026ed70a6fb4eaefb3c047fc3b87e7d9bd67bd01`). 실행부의 `case` label 139개와 집합이 같다(작업자 확인).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/c1/`
  - `work/natsearch.py`(IO pack에서 이 단위의 callback을 가진 자연 node 검색), `work/sa_probe.py` `work/ac_probe.py` `work/ip_probe.py`(아래 "영향받는" 절의 새 기대값 관측; 검증기 모듈을 scratch clone root에서 import), `mut/`(변이), `realrom/`(실제 ROM 차분).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **재측정 전**(`MS5_REOBS=…/reobs dleft.py`, routing `7233eefc…`): 실행된 routing 밖 PC C **835** / E **220** / D 0, 예측 일치 frame **165,714**, 첫 정지 영역 C·E 15 / C 1. 계획 §3.1 보정 기준선과 같다.
- [F] **정적 범위**: 20 범위, 1,342 byte(이어 붙인 SHA256 `73c889d9adf46c0a1fb00da0d5d99de9de0c90c02b16cff0e6d9ed6c9e583ed1`, 계획 §8.1과 같음), 짝수 PC 671(내부 532), 시작 139. 범위 안에 기존 routing된 PC는 없다(작업자 확인, `hroute_cpp`).
- [F] **예측**(계획 §8.3): C1 뒤 C 남은 실행 PC 835 → 757, E 220 → 218(`ca3a` `ca50`은 E 주소의 C helper, 결정 6), 예측 일치 frame 165,714 → **165,759**, 첫 정지는 E 15(frame +3의 E `de8ca` 계열) / C 1(boot-demo-0, 정지 PC `1d1f4` → `1d222`).

## 요약

| 범위(CPU = 파일 오프셋) | byte | SHA256(앞 16자) | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `ca3a..ca42` | 8 | `f1b0def6d291f68f` | 1 | 4 |
| `ca50..ca56` | 6 | `2a715aa291718c15` | 1 | 3 |
| `1d1f4..1d222` | 46 | `dda51819a342d734` | 7 | 23 |
| `48346..48350` | 10 | `418a1f9cff78c5b7` | 1 | 5 |
| `48368..4836e` | 6 | `bf91dcfae565e848` | 1 | 3 |
| `49bca..49be0` | 22 | `de75eb2c2e2d87a8` | 3 | 11 |
| `4e0f6..4e112` | 28 | `644c7d1a75d509ae` | 1 | 14 |
| `4e4da..4e4e2` | 8 | `2e892b640dd5f7a5` | 1 | 4 |
| `4e536..4e538` | 2 | `1ceeabf0c6a5a30b` | 1 | 1 |
| `4e58a..4e5b0` | 38 | `82012629bd3f3365` | 4 | 19 |
| `4e5c2..4e5e8` | 38 | `ebbeb1d100d94b5e` | 3 | 19 |
| `4e68e..4e69a` | 12 | `909114db297bc20b` | 1 | 6 |
| `4e69c..4e758` | 188 | `f60ae53a24446b85` | 12 | 94 |
| `4e7a2..4e8e6` | 324 | `956f9b423e07daed` | 42 | 162 |
| `4e8f0..4e8f8` | 8 | `dd5a5e4c1fc0f9ae` | 1 | 4 |
| `4e8fc..4e962` | 102 | `dc524c70fbf113be` | 9 | 51 |
| `4e97e..4e986` | 8 | `258307176e81235c` | 1 | 4 |
| `4eb50..4eb58` | 8 | `eeffc5b808f0a063` | 1 | 4 |
| `4f2e0..4f4ba` | 474 | `072d78fea34e4060` | 47 | 237 |
| `b7a28..b7a2e` | 6 | `c47e6c95738af4c9` | 1 | 3 |
| 합계 C1 | 1342 | 이어 붙인 바이트 `73c889d9adf46c0a…` | **139** | 671(내부 532) |

- [F] **명령 종류**(306개, 계획 `plan/C1.dis.txt`): 계산 점프·`JSR (An)`·DIVU/MULU·ABCD/ADDX/SUBX·MOVEM 없음. TRAP은 범위 밖의 `4e69a` 하나(결정 2). `BSET`/`BCLR`/`BTST` Dn,`d(An)`(memory 피연산자: bit 번호 = Dn mod 8) 4곳, `SEQ`/`SNE`/`SCS` 5곳, `ADDA.W` 1곳, PC 상대 BYTE 표 읽기 `MOVE.B (A4,D0.W)` 5곳, bank 창 LONG 읽기 1곳, `ANDI.B #fe,CCR` 1곳.
- [F] **나가는 곳**(routing된 callee·분기 출구, 모두 다른 실행부의 block 시작): `289e` `28ae` `2a00`(`4f33c`/`4f3a4 JMP`) `2a0a` `2a28` `3670` `8d34` `8ebe` `8ff4` `ca32` `ca42` `16ed2` `1bd2e` `48398` `49be0` `49f8c` `49fc6` `b7a2e` `b7a48` `e62ec`.
- [F] **뒤 단위 정지**(실행되지만 뒤 단위가 가짐, routing 밖): `1d222`(C2), `48350`(C3), `4e4e2` `4e538` `4e564` `4e758` `4e962` `4e986`(C4), `4e8e6` `4e8f8` `4eb58`(C6). 이 중 `48350` `4e4e2` `4e758` `4e962` `4e986` `4e8e6` `4e8f8`은 C1 block의 fall-through(직선 다음 PC)다.

## 공통 규칙·native 검증 계획

FR2..FR9 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_player_c1.cpp`, 함수 `animation_player_c1_block`. 오류 문자열은 `unsupported animation player c1 PC`(범위 안 내부 PC 직접 진입), `player c1 caller requires known carry`(C 소비 block에 Unknown C; 소비자 3개), `unsupported animation player c1 flag source`(결정 3의 Z 출처 guard). 그 밖의 오류는 공용 bus/스택 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(20 범위, FR9 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(`1d21c` `4e808` `4e958`), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** `MOVE.L #v,(A6)` 뒤가 곧 v인 곳은 그 block으로 들어간다: `4e728`→`4e732`, `4e7e6`→`4e7ec`, `4e836`→`4e83c`, `4e940`→`4e94e`, `4f328`→`4f32e`, `4f390`→`4f396`, `1d204`→`1d20c`. 쓰기만 하는 설치 값은 없다. 범위 밖이 설치하는 진입: `4e68e`(controller C2 `4e1cc`), `1d1f4`(`4e91c`의 `A1`을 `2a28`에 넘김, `1bd9c`, `47772`), `4f2e0`(`4e7ba MOVEA.L #4f2e0,A0; JSR 28ae`의 자식). `28ae`의 A0 `4f2e0`, `2a28`의 A1 `1d1f4`, `49f8c`의 A1 `4f4ba`, `3670`의 A1 `e84c8`, `4e564`의 A0 `4e34c`는 넘기기만 한다.
- **자료 읽기**(live bus, 상한 검사 없음): RAM의 node field(A6), 부모 node LONG `c(A6)`의 BYTE `9c` `a1` `98`, 플레이어 기록 LONG `78(A6)`(slot node), A5 기준 BYTE·WORD(`5d1e` `5d1f` `7004` `7d88` `5683` `-7699` `-76a0` `7db6+슬롯`), `5726/572c+4` `5d22/5d26+2×슬롯` 쓰기, 입력 기록 `104ca8`/`104cae`의 BYTE 4, 그리고 **고정 ROM의 BYTE 표 `4e4d2+색인`/`4e4d6+색인`**(색인 = D0.W, `ANDI.W #ff` 또는 `MOVEQ #0` + `MOVE.B` 뒤라 0..ff; 원본 바이트 `00 02 01 03 00 02 01 03` 뒤는 코드 바이트를 자료로 읽는다)와 **bank 창 LONG `2001e4`**. 단위 시험은 이 두 곳에만 합성 physical byte를 둔다(FR5 꼴, 원본 자료 아님: 표 `01 03 00 02 03 00 0a 01`, LONG `0012abcd`). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾸고 상위를 유지한다(`MOVE.W/.B` `ADDI.W` `ADD.B` `ADDQ.W` `ANDI.W` `SUBQ.B` `SUBI.W`). `MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`는 LONG 전체. `ADDA.W 76(A6),A0` = A0 + sext(WORD). `MOVE.B (A4,D0.W)` = A4 + sext(D0.W). 비교: `CMPI.W #2,D0` + `BCS`(무부호 WORD < 2: `8000` `ffff`도 TRAP 쪽), `TST.W D0` + `BNE`(WORD; `10000`은 0), `CMPI.B #1/#f/#a/#k` + `BEQ`/`BNE`/`BCC`(무부호 BYTE), `ADDI.W #2a,76(A6)` + `CMPI.W #600` + `BCS`(새 WORD 무부호 < 600; `ffd6`+`2a` = 0), `BTST #n,Dn`(LONG bit n), `BTST/BSET/BCLR Dn,d(An)`(BYTE bit Dn mod 8; `BEQ`/`BNE`는 옛 bit의 Z), `SEQ.B`(BTST의 Z), `SUBQ.B #1,99(A6)`(0 → ff).
- **슬롯 loop.** `4e596`(`BSET`; 옛 bit 1이면 `4e59e`: `ADDQ.W #1`, `ANDI.W #3`, 다시 `4e596`)과 `4e5d2`(`ADD.B D1,D0; ANDI.W #3,D0; BSET; BNE 4e5d2`)는 원본대로 반복한다. BYTE `5d1e`의 bit 0..3이 모두 1이면 원본도 끝나지 않는다 [F](해당 world는 native가 정지하지 않아 실제 ROM 차분에서 건너뛴다). C++ dispatcher의 단계 상한이 같은 경우를 끝낸다.

## carry와 Z(결정 3·4)

- [F] **C 소비 block 3개**(Clear 쪽 / Set 쪽):
  - `1d21c BCS.W 1d222`: `1d216 JSR 48346`의 C. Clear → `1d220 RTS`, Set → `1d222`(C2).
  - `4e808 SCS.B D0`: `4e802 JSR ca32`(controller C1: `CMPI.B #aa,-769c(A5); RTS`, known C)의 C. D0.B := Set이면 `ff`, 아니면 `00`(D0 상위 유지). 같은 block의 `CMP.B 9a(A6),D0`가 C를 다시 쓰므로 **block 뒤 C는 Unknown**으로 둔다(이 C는 읽는 곳이 없다: `4e812`는 `MOVE.B` + `BNE`, `4e82a`는 `RTS`). 다음은 D0.B = BYTE `9a`이면 `4e82a`, 아니면 `4e812`.
  - `4e958 BCC.B 4e8e6`: `4e94e JSR 289e`(`CMPI.L #270e,(A0)`; 같으면 Clear, 다르면 `ORI.B #1,CCR` Set)의 C. Clear → `4e8e6`(C6), Set → `4e95a`.
  - 세 곳을 `carry_preserving_pc`에 넣는다. Unknown C로 들어오면 checked 오류다.
- [F] **C 생산 block**: `48368 ANDI.B #fe,CCR; RTS`(한 block) → C Clear를 호출자(`1d21c`)에 돌려준다. 자기 block에서 C를 정하므로 들어오는 C가 필요 없어 `carry_preserving_pc`에 넣지 않는다(FR 관례: FR5 `5ad8e`, FR8 `d3822`, FR9 `b0578`의 `ORI`도 목록 밖). 계획 §8.2의 "C 보존 목록에 넣는다"와 다르지만 동작 차이는 없다(결정 4).
- [F] **Z 소비 block 3개**(결정 3): `4e7da SNE.B a1(A6); BEQ.W 4e82c`, `4e7f2 SNE.B a1(A6); BEQ.W 4e82c`, `4e842 SNE.B a1(A6); BNE.B 4e7e2`. 셋 모두 앞 block(`4e7d4` `4e7ec` `4e83c`)의 `JSR ca50`(`TST.B -7699(A5); RTS`)이 남긴 Z를 읽는다. `AnimationMachineState`는 C만 운반한다.
- [F] 다른 block 경계를 건너 읽는 flag와 X는 없다(계획 `cscan.py`; `4f49c JSR 49fc6`의 C는 `4f4a2`가 `ADDI.W`/`CMPI.W`로 덮으므로 읽지 않는다).

## 슬롯 callback `4e68e`(controller C2 `4e1cc`가 node `1009a8`/`100a6c`에 설치)

- **`4e68e`**: D0.W := WORD `76`(슬롯 번호), 무부호 < 2 → `4e69c`, 아니면 fall-through `4e69a`(**TRAP #15**, routing 밖: 다음 dispatch가 `unsupported animation machine PC`). **`4e69c`**: D0.W = 0 → `4e6a2`, 아니면 `4e6cc`. **`4e6a2`** / **`4e6cc`**: LONG `78` := `100cb8` / `100da8`(플레이어 기록), WORD `7c..84` := `7043 7043 7064 7023 7143` / `72c3 73c3 73c4 74a3 72c3`, → `4e6f2`.
- **`4e6f2`**: BYTE `9c` := 0, D0.W := WORD `76`, `JSR e62ec`. **`4e702`**: D0 := 0, WORD `76` = 0 → `4e70e`, 아니면 `4e70c`: D0 := 3. **`4e70e`**: BYTE `98` := D0.B, D0.W := WORD `76`, `JSR 4e0f6(PC)`. **`4e71a`**: D0.W := WORD `76`, `JSR e62ec`. **`4e724`**: `BSR 4e4da`. **`4e728`**: D0.W := WORD `76`, LONG `(A6)` := `4e732`(들어감).
- **`4e732`**(설치 값): A0 := A5 + `7db6` + sext(WORD `76`), D0.B := BYTE `(A0)`, = 1 → `4e7a4`, 아니면 `4e744`: D0.W := WORD `76`, BYTE `a1` := (BYTE `7004(A5)`의 bit D0 mod 8 = 0이면 `ff`, 아니면 0)(`SEQ`), BYTE `5d1f` = 0 → `4e7a2 RTS`, 아니면 `4e758`(C4).
- **`4e7a4`**: D0.B := BYTE `98`, `BSR 4e58a`. **`4e7ac`**: BYTE `98` := D0.B, BYTE `5d1e` = `f` → `4e8d6`, 아니면 `4e7ba`: A0 := `4f2e0`, D0.W := 0, `JSR 28ae`(자식). **`4e7ca`**: BYTE `9c` := 1, `BSR 4e4da`. **`4e7d4`**: `JSR ca50`. **`4e7da`**(Z): SNE, Z → `4e82c`, 아니면 `4e7e2`: `BSR 4e4da`. **`4e7e6`**: LONG `(A6)` := `4e7ec`(들어감).
- **`4e7ec`**(설치 값): `JSR ca50`. **`4e7f2`**(Z): SNE, Z → `4e82c`, 아니면 `4e7fa`: BYTE `5d1f` = 0 → `4e82a RTS`, 아니면 `4e802`: `JSR ca32`. **`4e808`**(C, 위). **`4e812`**: BYTE `9a` := D0.B, D0.B ≠ 0 → `4e826`(`BSR 4e538`, C4; 복귀 `4e82a`), 아니면 `4e81a`: A0 := `4e34c`(HUD 문자열 [I]), `BSR 4e564`(C4; 복귀 `4e822`: `BRA 4e82a`).
- **`4e82c`**: `JSR ca3a`. **`4e832`**: `BSR 4e4da`. **`4e836`**: LONG `(A6)` := `4e83c`(들어감). **`4e83c`**(설치 값): `JSR ca50`. **`4e842`**(Z): SNE, Z = 0 → `4e7e2`, 아니면 `4e848`: `JSR ca42`(A0 := A5 − `76a2`). **`4e84e`**: WORD `(A0)` = 0 → `4e8d6`, 아니면 `4e854`: A0 := `104ca8`(WORD `76` = 0) / `104cae`(`4e862`). **`4e868`**: D0.B := BYTE `4(A0)`, bit 4 → `4e8d6`, 아니면 `4e874`: D1 := −1, bit 2 → `4e888`, 아니면 `4e87e`: D1 := 1, bit 3 = 0 → `4e894`, 아니면 `4e888`: D0.B := BYTE `98`, `BSR 4e5c2`. **`4e890`**: BYTE `98` := D0.B.
- **`4e894`**: BYTE `9a` := BYTE `5d1f`, 0 → `4e8d4 RTS`, 아니면 `4e89e`: D0.W := WORD `7c` + `20`, WORD `76` ≠ 0이면(`4e8ae`) + `1a0`, `JSR ca42`. **`4e8b8`**: BYTE `(A0)` ≥ `a`(무부호) → `4e8d4`, 아니면 `4e8c0`: A1 := `e84c8`, D1.W := `431`, D3 := 0, D4 := 1, `JSR 3670`(숫자 출력 [I]; 복귀 `4e8d4`). **`4e8d6`**: BYTE `99` := BYTE `7d88(A5)`, ≠ 0 → `4e8e6`(C6), 아니면 `4e8e0`: BYTE `99` := 1(fall-through `4e8e6`).
- [I] 이름: `76` = 슬롯 번호(P1 0 / P2 1), `98` = 슬롯 bit 색인, `99` = 생성 대기, `9a` = 직전 `5d1f`, `9c` = 슬롯 상태(0 초기화, 1 대기, 2 생성), `a1` = 입력 대기 flag, `5d1e` = 사용 중 슬롯 bit, `5d1f` = 게임 진행 [I], `-7699` = 표시 flag [I].

## 플레이어 생성 `4e8f0..4e962`와 `4e94e`

- **`4e8f0`**(C6 `4e8e6`의 fall-through): BYTE `5d1f` = 0 → `4e8fc`, 아니면 `4e8f8`(C6). **`4e8fc`**: BYTE `99` = 0 → `4eb58`(C6), 아니면 `4e904`: BYTE `9c` := 2, `BSR 4e4da`. **`4e90e`**: BYTE `99` −= 1, `JSR 48398`. **`4e918`**: A0 := LONG `78`(플레이어 기록), A1 := `1d1f4`, `JSR 2a28`(그 기록에 플레이어 객체를 설치 [I]). **`4e928`**: D0 := 0, D0.B := BYTE `98`, WORD `76(A0)` := D0.W, D0.W := WORD `76`, WORD `78(A0)` := D0.W, `JSR 1bd2e`. **`4e940`**: BYTE `9a` := 0, BYTE `a1` := 0, LONG `(A6)` := `4e94e`(들어감).
- **`4e94e`**(설치 값): A0 := LONG `78`, `JSR 289e`. **`4e958`**(C, 위). **`4e95a`**: BYTE `9a` = 0 → `4e97e`, 아니면 `4e962`(C4). **`4e97e`**: D0.B := BYTE `5d1f`, 0 → `4eb50`, 아니면 `4e986`(C4). **`4eb50`**: BYTE `9a` := BYTE `5d1f`, `RTS`.

## `28ae` 자식 `4f2e0`과 상태 `4f32e` / `4f396`

- **`4f2e0`**: WORD `20` := `22b`, LONG `22` := LONG `2001e4`(bank 창), WORD `46` := `1d0`, A1 := `4f4ba`, D0.W := `100`, `JSR 49f8c`. **`4f304`**: BYTE `79..7c` := `ff`, WORD `1e` := `ffff`(fall-through `4f322`). **`4f322`**: `JSR 8ff4`. **`4f328`**: LONG `(A6)` := `4f32e`(들어감).
- **`4f32e`**(설치 값): A0 := LONG `c(A6)`(부모 = 슬롯 node), BYTE `9c(A0)` = 1 → `4f342`, 아니면 `4f33c JMP 2a00`. **`4f342`**: BYTE `5d1f` = 0 → `4f356 RTS`, 아니면 `4f34a`: 부모 BYTE `a1` = 0 → `4f358`, 아니면 `4f356`. **`4f358..4f382`**: D0.W := `7a`/`7c`/`7e`/`80`, D1.B := 1, `JSR 8ebe` 4회. **`4f390`**: LONG `(A6)` := `4f396`(들어감).
- **`4f396`**: 부모 BYTE `9c` = 1 → `4f3aa`, 아니면 `4f3a4 JMP 2a00`. **`4f3aa`**: BYTE `5d1f` = 0 → `4f322`, 아니면 `4f3b2`: 부모 BYTE `a1` ≠ 0 → `4f322`, 아니면 `4f3be`: D0 := 0, D0.B := 부모 BYTE `98`, BYTE `78(A6)` := BYTE `4e4d2 + D0.W`, `JSR 16ed2`.
- **표시 4칸** `4f3d4` `4f406` `4f438` `4f46a`(k = 0..3): D0.B := BYTE `19+k`, BYTE `78` = k → D1.W := `79`/`7b`/`7d`/`7f`, 아니면 BYTE `5d1e`의 bit k: 0 → `7a`/`7c`/`7e`/`80`, 1 → `81`/`82`/`83`/`84`, `JSR 8d34`. **`4f49c`**: `JSR 49fc6`. **`4f4a2`**: WORD `76` += `2a`, 새 WORD < `600` → `4f4b8 RTS`, 아니면 `4f4b2`: WORD `76` −= `600`.

## 슬롯 helper와 플레이어 객체

- **`4e0f6`**: D0.W := (D0.W ∧ 1) × 2, WORD `5d22(A5)+D0.W` := 0, WORD `5d26(A5)+D0.W` := 0, A0 = A5 + `5d26`, `RTS`. **`4e4da`**: BYTE `5d1f` = 0 → `4e536 RTS`, 아니면 `4e4e2`(C4).
- **`4e58a`**(할당): D0.W ∧= `ff`, A4 := `4e4d2`, D0.B := BYTE `(A4 + D0.W)`. **`4e596`**: BSET bit D0 mod 8 of BYTE `5d1e`, 옛 bit 0 → `4e5a6`, 아니면 `4e59e`: D0.W := (D0.W + 1) ∧ 3, → `4e596`. **`4e5a6`** / **`4e5de`**: A4 := `4e4d6`, D0.B := BYTE `(A4 + D0.W)`, `RTS`.
- **`4e5c2`**(이동): D0.W ∧= `ff`, A4 := `4e4d2`, D0.B := 표 BYTE, BCLR bit D0 mod 8 of `5d1e`. **`4e5d2`**: D0.B += D1.B, D0.W ∧= 3, BSET, 옛 bit 1 → `4e5d2`, 아니면 `4e5de`.
- **`1d1f4`**(플레이어 객체 진입): `JSR 2a0a`. **`1d1fa`**: D0.W := WORD `78`(슬롯 번호), `JSR 49be0`. **`1d204`**: LONG `(A0)` := 0, LONG `(A6)` := `1d20c`(들어감). **`1d20c`**: D0.W := WORD `78`, `JSR 49bca`. **`1d216`**: `JSR 48346`. **`1d21c`**(C). **`1d220`**: `RTS`.
- **`48346`**: BYTE `5683(A5)` bit 1 = 0 → `48368`(C Clear, `RTS`), 아니면 `48350`(C3). **`49bca`**: A0 := A5 + `5726`, D0.W ∧= 1, 0 → `49bda`, 아니면 `49bd6`: A0 := A5 + `572c`. **`49bda`**: WORD `4(A0)` := 0, `RTS`.
- **`ca3a`**: WORD `-76a2(A5)` := WORD `-76a0(A5)`, `RTS`. **`ca50`**: `TST.B -7699(A5)`(bus 읽기를 한다), `RTS`. **`b7a28`**: D0.B ≠ 0 → `b7a48`, 아니면 `b7a2e`(둘 다 routing된 출구).

## 경계·routing 밖 출구

- [F] 이 단위 안에는 계산 점프·live 대상 호출(`JSR (An)`)이 없다. `RTS`로 끝나는 block 15개.
- [F] **native 정지 규칙**(V1): FR9 spec의 `first_unrouted`에 **C1 뒤 단위 정지 11곳과 TRAP `4e69a`**(`EXIT_STOPS`)를 선언 정지로 더한다. 이유: `first_unrouted`는 "직선 다음 PC인 routing 밖 PC는 다른 실행부 block의 내부"로 보고 지나가는데, C1 block의 fall-through(`48350` `4e4e2` `4e758` `4e962` `4e986` `4e8e6` `4e8f8`, TRAP `4e69a`)는 routing 밖 코드의 시작이라 native가 C++이 실행하지 못하는 코드로 이어 달리게 된다. 실제 ROM 차분도 같은 12곳을 `EXTRA_STOPS`로 둔다. 단위 시험 생성기는 범위 밖 첫 PC에서 멈추므로 영향이 없다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1..FR9 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0..A4 := 자연 node, LONG `c(A6)` := 자연 node, slot block이면 LONG `78(A6)` := `100cb8`/`100da8`/자연 node, A5 field, PC).
- **IO pack 자연 node 상태(family `natural`)**: 계획 §8.3과 scratch `work/natsearch.py`. frame 시작 상태에서 callback LONG이 이 단위의 진입인 node를 찾아(work RAM `100800..104c00`) 그 RAM·PVC·bank를 쓰고 레지스터만 선언한다(A5 := `108000`, A6 := 그 node, A7 := `10ef00`(복귀 LONG = sentinel), PC := callback). 쓰는 frame: P1 094 3 4 66 67 72 73 74 192 458, P1 068 223 287 289, P1b 094 67 100, boot-title-start 123 187 193(node `1009a8` `100a6c` `101020` `1010e4` `10126c` `100cb8`; callback `4e732` `4e7ec` `4e83c` `4e94e` `4f32e` `1d20c`).
- **재설치 world(family `reinstall`)**: `4e68e` `4f2e0` `1d1f4`는 같은 frame 안에서 설치되고 실행되므로 frame 시작 상태에 남지 않는다. 같은 IO pack 상태의 자연 slot / 자식 / 플레이어 node에 callback LONG만 선언으로 써서 들어간다(9개: `1009a8`/`100a6c`의 `4e68e`, `101020`/`10126c`의 `4f2e0`, `100cb8`의 `1d1f4`). [I] 이미 초기화된 node를 다시 초기화하는 world이며, native와 C++가 같은 상태를 받으므로 V1 비교는 유효하다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다 — `48346` → `1d21c`(`1d216`; Clear 쪽만 routing됨, Set 쪽은 C3 `48350`에서 멈춘다), `ca32` → `4e808`(`4e802`; BYTE `-769c` = 0/a9/aa/ab/ff, BYTE `9a` = 0/ff), `289e` → `4e958`(`4e94e`; LONG `(A0)` = `270e`/다른 값). 단위 시험은 RAM만 읽는 생산자이므로 `ca32` `289e` 사슬을 두 C 값 모두 실제 사슬로 넣고, `48346` 사슬은 Clear 쪽 행만 둔다.
- node fixture: callback·설치 값(`4e68e` `4e732` `4e7ec` `4e83c` `4e94e` `4f2e0` `4f32e` `4f396` `1d1f4` `1d20c`)을 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다. callee fixture: `ca3a` `ca50` `48346` `49bca` `4e0f6` `4e4da` `4e58a` `4e5c2`를 subroutine으로 들어간다.
- 단위 시험(Unicorn 생성기, FR9 꼴): 시작 139개(소비자 3개 제외) × 들어오는 C 3가지, zero-step, 내부 PC 532개 정확한 오류, 경계 stop(출구·뒤 단위 정지·TRAP 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC(실패 block 바로 뒤를 run stop으로), Z 소비자는 Unicorn 직접 진입의 SR Z를 BYTE `-7699(A5)` = 0과 같게 둔다. 빈틈 종류별 hint와 손으로 계산한 규칙(rules):
  - 부호·영 확장: `ADDA.W 76`(`ffff` → A0 = `10fdb5`), `MOVE.B (A4,D0.W)`(D0.W = `ffff` → `4e4d5`), `MOVEQ #0` + `MOVE.B`(`4e928` `4f3be`), `MOVE.W/.B` → D0/D1 상위 유지, `MOVEQ #-1`/`#1`(D1 LONG 전체).
  - bit 번호 mod 8: `BSET/BCLR Dn`(표 값 `0a` → bit 2, D0 = 8 → bit 0), `BTST.B D0`(WORD `76` = 9 → bit 1). 옛 bit의 Z: 할당 loop의 step(`09` → `0b`), 이동 loop의 −1 / +1 step(D1 상위 쓰레기 무관: `ADD.B`).
  - 동점·무부호: `CMPI.W #2`(`2` `ffff` `8000` → TRAP), `CMPI.B #f`(`1f`), `CMPI.B #1`(`81`), `CMPI.B #a`(`9` / `a` / `80`), `CMPI.W #600`(`5d5` / `5d6` / `ffd6` 순환 / `7fff`), `CMPI.B #k,78`(`80|k`).
  - TST 크기: `TST.W D0`(`4e69c`: `10000` → 0, `100` → ≠ 0), `TST.W (A0)`(`4e84e`: `0001`), `TST.B D0`(`b7a28`: `100` → 0).
  - Z 재계산: 0 / ≠ 0, 이웃 BYTE 무관, RAM 거울 A5 = `1f8000`, 24-bit 주소(A5 = `ff108000`), guard(A5 = `8000` ROM, `300000` bank, `210000`), `ca50`의 bus 읽기(A5 = `307699` → 입력 port `300000` 읽기: 선언 queue가 없으면 오류).
  - carry: `4e808` Set/Clear → D0.B `ff`/`00`과 C Unknown, `4e958`·`1d21c` 유지, `48368` Clear(`1d216` 사슬).
  - field·크기: `CLR.W 4(A0)`(다음 WORD 유지), `CLR.L (A0)`, slot WORD 5개, BYTE `79..7c` 4개, bank 창 LONG, 슬롯 표시 id 12개.

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `7233eefc…` → `15b827242abca6434147ab3a63a827b5d4d613cbdbbba051c438a57ea001dea2`, `animation_machine_internal.h` `b870dcc5…` → `5e2ad9ef19d159ba9907b2a9683034ad754b6734177ee8e73f84e235c4337a0e`(이 단위의 공유 수정; 옛 값은 `# player C1 refresh:` 주석).
- [F] `tools/verify_animation_machine_stage_area.py` `UNROUTED_NEIGHBOURS`(`SUPERSEDED_NEIGHBOUR_ERRORS` 방식, 새 `SUPERSEDED_NOTES`): 기본 상태(natural-001 frame 0)에서
  - `b7a28`: `unsupported animation machine PC` → `animation machine external read queue empty`(C1 block 시작: D0.B = 0 → `b7a2e`, 그 뒤 선언 queue 없는 입력 읽기).
  - `b7a2a` `b7a2c`: `unsupported animation machine PC` → `unsupported animation player c1 PC`(`b7a28` block 내부).
  - `4e68e`: 문구는 그대로 `unsupported animation machine PC`. 다만 이제 `4e68e`가 실행되고(WORD `76(A6)` ≥ 2) 다음 dispatch가 TRAP `4e69a`에서 실패한다(주석으로 기록). 관측: scratch `work/sa_probe.py`(stop `4e69a`면 성공, stop `b7a2e`면 성공).
- [F] `tools/verify_animation_machine_area_clear.py` `unrouted_neighbour_00ca50`: `unsupported animation machine PC` → `program bus write requires RAM mirror units`(`ca50`이 C1 시작: `RTS`가 기본 상태(natural-000)의 복귀 LONG `2ac2`로 돌아가 다른 superseded 이웃 `01c5ea` `04b6f4` `0477ee`과 같은 곳에서 실패). `SUPERSEDED_NEIGHBOURS`에 `superseded_by_player_C1_routes_ca50`. 관측: scratch `work/ac_probe.py`.
- [F] `tools/verify_animation_machine_input.py` 861행 이웃 목록의 `49bca`: `unsupported animation machine PC` 거부 → `SUPERSEDED_OUTSIDE`(`49be0` 등과 같은 API-only control). 기본 상태(natural-stage-frame-0000)에서 `ff000`까지 성공한다. 관측: scratch `work/ip_probe.py`.
- [F] `engine/tests/animation_machine_input_test.cpp`의 `JSR (A1)` 계산 PC 표: 실행부 없는 대상 `49bca`(`unsupported animation machine PC`)가 C1 시작이 되어 그 행이 실패했다(`make test`: `unexpected success 49b0c stop 480cc`). 탐침을 고정 ROM 자료 PC `4e4d2`(슬롯 표, 코드 아님·routing 안 됨)로 옮겼다. 옛 값은 주석.
- [F] `engine/tests/animation_machine_objects_u06_test.cpp` `rom_outside`의 `49bca` `49bde`: 이 assert는 "U06 범위 밖"만 확인하므로 C1 뒤에도 그대로 참이다. 값은 바꾸지 않고 주석만 더했다.
- [F] 경계가 맞닿은 범위(`input_test` RANGES `49ab4..49bca`, `controller_c1_test`·`c1.py`의 `ca32..ca3a`, `area_clear_test` RANGES `ca48..ca50`, `stage_area_test`의 `4e666..4e68e` `b7a20..b7a28` `b7a2e..`)는 `make test`와 V1 회귀(c1, c2, fr1, fr9)가 통과했다. 이웃 PC를 "routing 밖"으로 확인하는 행은 위 input_test 한 곳뿐이었다.
- [I] native 사슬이 이 단위의 PC(`4e68e` `1d1f4` `ca50` `49bca` `b7a28` 등)를 첫 routing 밖 PC로 멈추던 V1 spec·검증기는 더 진행한다(정지는 routing에서 계산된다). 메인 runner의 회귀·legacy 단계가 확인한다.

## 결정

1. **범위.** C1 = 계획 §8 그대로 139 block, 20 범위. 계획 메인 결정 5·6(시간 순서 분할, E 주소의 C helper `ca50` `ca3a`는 C)을 따른다.
2. **TRAP `4e69a`.** WORD `76` ≥ 2(무부호)이면 `4e68e`가 PC := `4e69a`로 끝나고 다음 dispatch가 `unsupported animation machine PC`로 실패한다(FR5 TRAP `5ae0e`와 같은 방식). 범위 `4e68e..4e69a`와 `4e69c..`가 그 PC를 뺀다. V1·실제 ROM 차분에서는 선언 정지다.
3. **RTS를 넘는 Z(새 Z 규약의 최소 정의).** `4e7da` `4e7f2` `4e842`는 Z를 BYTE `-7699(A5)`(24-bit 주소 = A5 + sext(`8967`))에서 다시 읽어 Z = (BYTE = 0)로 계산한다. 근거 [F]: 세 block의 유일 선행은 `JSR ca50`(같은 A5로 `TST.B -7699(A5)`)이고 `RTS`는 stack만 읽으며 A5를 바꾸지 않는다. 그 주소가 work RAM(`100000..1fffff`, 24-bit)이 아니면 `unsupported animation player c1 flag source`(checked, rollback)다. 이유: RAM 다시 읽기는 효과가 없지만 device 주소(입력 port 등)를 다시 읽으면 원본에 없는 두 번째 읽기가 된다. controller C1 결정 3(`ac1_flag_zero`, BYTE `(A0)` 다시 읽기)과 FR2 결정 4(`b48ba`, WORD `(A1)`)와 같은 방식이고, public header와 dispatcher는 바꾸지 않는다. A5 ≠ `108000`이라도 RAM이면 허용한다(계획 §8.2의 [U]를 이렇게 정한다). 단위 시험의 Unicorn 직접 진입은 SR Z를 그 값과 같게 두고, V1 native(SR Z = 0으로 시작)의 직접 진입은 BYTE ≠ 0인 world만 쓰며 Z = 1 쪽은 `4e7d4` `4e7ec` `4e83c` 진입으로 덮는다.
4. **carry 보존 목록.** 소비자 3개(`1d21c` `4e808` `4e958`)만 넣는다. `48368`(`ANDI.B #fe,CCR; RTS`)은 자기 block에서 Clear를 정하므로 넣지 않는다(FR 관례; 계획 §8.2 문구와 다르지만 들어오는 C를 쓰지 않으므로 동작이 같다). `4e808`은 C를 소비한 뒤 Unknown으로 둔다(`CMP.B`).
5. **표 읽기.** `MOVE.B (A4,D0.W)`는 live bus로 고정 ROM을 읽는다(상한 검사 없음, 원본과 같음). 색인 8 이상은 원본도 표 뒤의 코드 바이트를 읽는다. 단위 시험은 합성 8 byte만 선언하므로 그 밖 색인은 `missing or ambiguous physical program bus ROM byte`로 확인하고, 원본 값은 V1·실제 ROM 차분이 비교한다.
6. **뒤 단위 정지.** C1 block이 직선 또는 분기로 닿는 뒤 단위 시작 11곳과 TRAP을 V1 `first_unrouted`와 실제 ROM 차분의 선언 정지로 둔다("경계" 절).
7. **관측기 수정(계획 메인 결정 1의 코드·문서 부분) — 이 단위에서 하지 않았다.** `tools/observe_animation_machine_io.py`는 `verify_animation_machine_io.py`가 `observation.json`의 `pins.observer.sha256`으로 파일 SHA를 확인한다(1026행: 다르면 `SystemExit`). 관측기의 정확 bitmap 선택지나 `[I] single-PC executors cover their intra-function closure` 주석을 고치면 기존 IO 관측으로 하는 IO 비교가 바로 멈춘다. 그래서 고치려면 관측을 다시 해 `artifacts/`에 두어야 하고, 이는 사용자 승인 사항이다(계획 메인 결정 1). 메인 결정을 기다린다 [U].
8. **실행부 파일·오류 문자열.** 위 "공통 규칙". 오류 문자열 3개.
9. **다음.** 계획 순서대로 E1(캐릭터 선택).

## 미확인

- [U] node field·전역 BYTE의 의미(`76` `78` `98` `99` `9a` `9c` `a1`, `5d1e` `5d1f` `-7699` `7d88` `7004` `7db6`, 입력 기록 `104ca8`/`104cae`), 문자열 `4e34c`, 숫자 출력 표 `e84c8`, 자식 `4f2e0`의 script `4f4ba`.
- [U] IO 관측에서 실행되지 않은 이 단위의 block 59개(`4e802..4e826` `4e888..4e8d4` `4f34a..4f4b8` 등 분기 쪽)는 closure로 들어왔다(V1 선언 상태·실제 ROM 차분으로만 확인).
- [U] 재설치 world와 IO pack 자연 node 상태의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(FR9 결정 5의 [I]와 같음).
- [U] 결정 7: 관측기의 정확 bitmap 방식과 주석 수정의 시기(재관측 artifacts 승인).
- [U] `1d21c`의 Set 쪽(`1d222`)은 C3 `48350`(`ORI.B #1,CCR`)이 연결되기 전에는 실제 사슬로 닿지 않는다. 선언 C 행(단위 시험)과 실제 ROM 차분의 선언 C 진입만 있다.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_player_c1.cpp`(case label 139 = `starts_C1.txt`와 집합 일치; 공용 함수 `pc1_get` `pc1_put` `pc1_byte_zero` `pc1_gate`(`TST.B 5d1f(A5)` + `BEQ`) `pc1_carry` `pc1_flag_zero`(결정 3) `pc1_sne` `pc1_slot_bit`(BSET/BCLR Dn mod 8, 옛 bit) `pc1_table`(`LEA t(PC),A4; MOVE.B (A4,D0.W),D0`) `pc1_slot_index` `pc1_slot_index_78` `pc1_install` `pc1_slot_words` `pc1_light` `pc1_mark` `pc1_slot_test` `pc1_parent_state` `pc1_parent_a1`), `engine/tests/animation_machine_player_c1_test.cpp`(생성 구역 + 수작성 규칙), `tools/generate_animation_machine_player_c1_test_table.py`(생성기; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; 약 120초; 다시 실행해 시험 파일 바이트 단위 같음 SHA256 `6e1b9e903d542e40935583a5b6b79993c4af26355260c5da364a6075f9d31673`), `tools/unit_fixture_specs/pc1.py`(V1 spec; FR9 spec의 공용 부분(routing 해석, `first_unrouted`, carry oracle, chain/node/natural/callee family) 그대로, 단위 부분 교체, `EXIT_STOPS`, `Z_RECOMPUTE`, `LATER_GATED`, family `reinstall`). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- [F] `make -j6 all test`(작업자): 종료 0, 경고 0. C1 시험 줄: `animation machine player pc1: 713 fixtures (504 single-block, 161 path, 15 producer chain, 6 declared C, 27 checked error (8 with a later failing PC), 19 kept C), 139 blocks, 3390 calls, 33920 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block은 `4e5d2`의 자기 loop(`BNE 4e5d2`: 자기 진입 정지는 zero-step이라 단일 행이 될 수 없다; path 행·규칙이 덮는다)뿐, 실제 사슬 `4e802`→`4e808`·`4e94e`→`4e958`(두 C 값), `1d216`→`1d21c` Clear 쪽 3행.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, C1 시험): 빌드 경고 0, 실행 종료 0, runtime error 0.
- [F] V1 pc1(작업자 1회, `--workers 4`, scratch `work/v1_try1`): fixture 1,264개(block 574, chain 10, node 25, natural 52, reinstall 9, callee 16, error 559, failpc 9, negative 10) failed 0, 방문 시작 139/139, 빠진 후속 0, 도달 못한 분기 결과 0, 뒤 단위 gate `(1d21c, 1d222)` 하나, carry oracle Unknown/Clear/Set = 685/9/1.
- [F] V1 회귀(작업자, 이웃 spec 4개): c2(A1 pool에 `4e68e`) 1,607/1,607, c1 1,741/1,741, fr1 1,631/1,631, fr9 1,415/1,415(모두 failed 0). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`, `mut/mutants.py`; 실행부 231개 + dispatcher carry 목록 4개): 1회째 235개 중 231 kill. 살아남은 4개는 모두 비동치 빈틈이었다: `flag-guard-24bit`(guard가 24-bit 주소를 쓰는지: A5 = `ff108000` 규칙), `49bda-long`(`CLR.W` 대 `CLR.L`: 다음 WORD `572c` 유지 규칙), `4e58a-mask-7f`(`ANDI.W #ff`의 bit 7: 색인 `83` 규칙), `4e69c-byte`(`TST.W` 대 `TST.B`: D0 = `100` 규칙). 규칙을 더한 뒤 그 4개 재실행 `killed 4 of 4`. 전체 재실행은 결정적 runner가 한다.
- [F] 실제 ROM 차분 준비(scratch `realrom/`): `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`; 로그 `run_s1..run_f5.log`에 `mismatches N`·`covered starts X of Y`), `real_pc1.py`(FR9 harness에 C1 world·소비자·Z 진입·선언 정지 12곳; 계산 착지는 FR9 JMP와 옛 표 JMP를 trace 전체에서 기록해 분류). 시험 실행(작업자): 300건 seed 1 `mismatches 0`(분류된 오류 0건, `covered starts 137 of 139`; 정지하지 않은 native 32건은 건너뜀).
- [F] `dleft.py`(`MS5_REOBS`, routing `15b82724…`): 실행된 routing 밖 PC C **757** / E **218** / D 0, 예측 일치 frame **165,759**, 첫 정지 영역 E 15 / C 1. 계획 §4.2·§8.3 예측과 같다(C −78, E −2, +45 frame).

## block 목록

[F] scratch `starts_C1.txt`(SHA256 `7d67c3729a79cc8c81f4f231026ed70a6fb4eaefb3c047fc3b87e7d9bd67bd01`)와 같다.

- **`ca3a` `ca50`(2)**: `ca3a ca50`
- **`1d1f4..1d222`(7)**: `1d1f4 1d1fa 1d204 1d20c 1d216 1d21c 1d220`
- **`48346` `48368` `49bca..49be0`(5)**: `48346 48368 49bca 49bd6 49bda`
- **`4e0f6..4e5e8`(10)**: `4e0f6 4e4da 4e536 4e58a 4e596 4e59e 4e5a6 4e5c2 4e5d2 4e5de`
- **`4e68e..4e758`(13)**: `4e68e 4e69c 4e6a2 4e6cc 4e6f2 4e702 4e70c 4e70e 4e71a 4e724 4e728 4e732 4e744`
- **`4e7a2..4e8e6`(42)**: `4e7a2 4e7a4 4e7ac 4e7ba 4e7ca 4e7d4 4e7da 4e7e2 4e7e6 4e7ec 4e7f2 4e7fa 4e802 4e808 4e812 4e81a 4e822 4e826 4e82a 4e82c 4e832 4e836 4e83c 4e842 4e848 4e84e 4e854 4e862 4e868 4e874 4e87e 4e888 4e890 4e894 4e89e 4e8ae 4e8b2 4e8b8 4e8c0 4e8d4 4e8d6 4e8e0`
- **`4e8f0..4eb58`(12)**: `4e8f0 4e8fc 4e904 4e90e 4e918 4e928 4e940 4e94e 4e958 4e95a 4e97e 4eb50`
- **`4f2e0..4f4ba`(47)**: `4f2e0 4f304 4f322 4f328 4f32e 4f33c 4f342 4f34a 4f356 4f358 4f366 4f374 4f382 4f390 4f396 4f3a4 4f3aa 4f3b2 4f3be 4f3d4 4f3e2 4f3ea 4f3f4 4f3fc 4f400 4f406 4f414 4f41c 4f426 4f42e 4f432 4f438 4f446 4f44e 4f458 4f460 4f464 4f46a 4f478 4f480 4f48a 4f492 4f496 4f49c 4f4a2 4f4b2 4f4b8`
- **`b7a28`(1)**: `b7a28`
