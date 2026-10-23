# 영역 C 단위 C10(입력 확장 관측의 둘째 C 단위: 28ae 자식 `1c4b0` → `1c4d2` → `1c500`, interpreter stub `1dc84`/`1dc8a`의 두 후속 `1dc8e`·`1dccc`, 입력 상태 `1efd6` → `1efe4`, 기록 진입 `1f082`·`1f3e0`, C3 표 칸 `20324` → `203a0`(BRA.W 표 점프 `203ac`, 칸 `203b0`) → `20414`/`2041a` → `204e0`, `20bfe`, 칸 `84` 상태 `21dd0` → `21e04`·`22148`·`22286` → `2228e` → `22360`·`223fa`, 소리 helper `24b78`, 2986 자식 `24ecc`, C7 표 칸 `252b4` → `252ce` → `252e2`, `JMP (A1)` 3곳, 132 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §10.5 표의 C10 행(계획 이름 C-2)과 §10.x 메인 결정(결정 4: C7 표 칸 `252b4` → `252ce`는 C10)을 기준으로 삼고, 구조·공통 규칙은 C9 계약(`animation-machine-player-c9-contract.md`; 입력 확장 관측 방법·V1 natural family·IO 검증기 pin 표)과 FR10 계약(`animation-machine-frontier-fr10-contract.md`; 정확 bitmap 재관측으로 범위 확정)을 따르며 다른 점만 적는다. 단위 이름은 C10, 파일 접두어는 `player_c10`(C++) / `pc10`(V1 spec)다. 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다. BIOS 실행, 자연 scheduler, IRQ timing은 주장하지 않는다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 LONG `200038`(`24ecc`)을 live bus로 읽는다. 장치 쓰기는 없다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 FR10 커밋 `35e68fe`(branch `claude/c10-core`; C1~C9, E1, D, FR10 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `6a7d76c3817fdab2a07af95b5d1be6cb14fca2c81f992bba558a88bddb14cdc6`, `animation_machine_internal.h` `9f371fcfefb8bf19538c6b6e6e779a9e95ea9019c77816537a4b0ce01870425c`(FR10 계약의 새 값과 같음).
- [F] 관측 입력(읽기 전용): 입력 확장 IO 관측 `artifacts/animation_machine_io_ext`(`observation.json` SHA256 `9da40ac6dcbea3eb…`, compared_sha256 `b5d15d4fcd53555b…`, 검증기 pin 이름 `io-ext`). V1 natural family가 이 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)으로 읽는다(C9 결정 6과 같은 방식).
- [F] 이 단위의 정확 bitmap 재관측(scratch, 관측기 `tools/observe_animation_machine_io_ext.py` 수정 없음): `reobs/c10base`(FR10 routing 그대로), `reobs/c10v1`(계획 범위에 C7 표 칸과 `203c4` `203cc`를 더한 20 범위를 `--extra-routed`로 가상 routing), `reobs/c10v2`(최종 18 범위를 가상 routing). 결정 1.
- [F] 시작 목록: **`ms5-scratch/c10/work/starts_c10_final.txt`(132개, 줄마다 하나, SHA256 `fe3690da1e1d8748ec28baaf33e8ab725e50e88d0eb2a8dbb4f3360970b8c6bc`)**. 계획 목록 `ms5-scratch/c10/starts_C10.txt`(127개, 공백 구분, SHA256 `ec279a89d3ba30e89bc134e112890be9e6539d898a7454bccc12e773898e09f8` = 계획 §10.5의 `ec279a89d3ba30e8`)에 `2041a` `252b4` `252ce` `252d8` `252e2`를 더했다(결정 1). 실행부의 `case` label 132개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(작업자 확인: 실행부 case 집합 = 시작 목록, `make test`의 C10 시험이 시작 132개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/c10/`
  - `reobs/run.sh`(재관측 + `dleft.py` + `runstops.py`), `reobs/c10base` `c10v1` `c10v2`(+ `.dleft` `.stops` `.log`), `tools/c10exec.py` → `work/c10exec_base.txt`(재관측의 C10 실행 PC·run·frame), `tools/newvis_c10.py` → `work/newvis_c10v1.txt`(새로 보인 PC), `work/intargets.py` → `work/intargets_c10_v1.out`(범위 안 비시작 PC로 오는 직접 분기), `tools/refs_c10.py` → `work/refs_c10_v1.out`(ROM 전체 C10 시작 참조), `tools/flagscan.py` → `work/flagscan_c10_v1.txt`(block 경계를 넘는 flag), `tools/exitflags.py` → `work/exitflags_c10.txt`(출구 대상이 앞 코드의 flag를 읽는지), `tools/blocks_c10.py` → `work/blocks_final.txt`(block별 역어셈블), `tools/owner.py`(PC의 routing 소유 실행부), `tools/natscan_c10.py` → `work/natscan_c10.out` `work/natural_c10.json`(V1 natural frame), `tools/c10refs_repo.py` → `work/c10refs_repo.out`(저장소의 C10 범위 literal), `probe/`(C++ 오류 행 설계용 탐침), `work/v1_regs.sh`, `work/ubsan.sh`, `work/pincheck.py`, `work/mkroot.py`, `work/run_tests.sh`, `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위(결정 1)

- [F] **기준선**(FR10 routing, 입력 확장 관측): 예측 일치 frame **6,230**, 첫 정지 C 7 run(`1dccc` 4, `22148` 1, `223fa` 2)·"D" 1 run(X3 68 frame 591 `252b4`). FR10 계약의 IO 실측과 같다.
- [F] **정확 bitmap 재관측(FR10 routing)** `reobs/c10base`: `dleft.py` 실행된 routing 밖 PC C 102 / D 513 / E 108, 예측 6,230, 첫 정지는 위와 같다(`reobs/c10base.dleft` `.stops`). C 102개는 모두 계획 C10 시작이고(`work/c10exec_base.txt`의 "C executed not C10 start" 비어 있음), "D" 가운데 C10 범위 안의 것은 `252b4` `252ce` `252e2`(C7 표 칸)뿐이다.
- [F] **범위 보정 1 — C7 표 칸 4 block을 더함(메인 결정 4)**: `252b4`(BRA.W `252ce`) `252ce`(BTST `#7,61(A2)`; BNE) `252d8`(`MOVE.W #189d,D0; JSR 3af8`) `252e2`(BRA.W `253c8`). FR10이 계획 FR10에서 뺀 네 block이다(FR10 계약 범위 보정 1).
- [F] **범위 보정 2 — `2041a`를 block 시작으로 더함**: `20414 MOVE.B #6,a4(A6)` 다음 PC `2041a`(`TST.B 9c(A6)`)는 범위 밖의 실제 분기 대상이다: 표 `203b0`의 실행되지 않은 칸 `203b4` `203b8` `203c8` `203d0`과 같은 꼴의 이웃 표 `2037c`의 칸 `2037c` `20390` `20398`이 모두 `BRA.W 2041a`다(`work/refs_c10_v1.out`). FR9·FR10 계약의 block 시작 규칙("범위 밖에서 들어오는 실제 분기 대상", FR10 `cd804`)대로 시작으로 두어, 뒤에 그 칸을 routing하는 단위가 C10을 다시 고치지 않게 한다. `2041a` 자체는 `20414`와 같은 TB 안이라 따로 기록되지 않을 뿐 `20414`가 실행될 때마다 실행된다.
- [F] **범위 보정 3 — 계획 표의 "실행 칸" `203c4` `203cc`(표 `203b0`)와 `20340`(C3 표 `2031c`)은 넣지 않음**: 계획 §10.5 표는 표 `203b0`의 실행 칸을 `203b0` `203c4` `203cc`(→ `20414`), C3 표 `2031c`의 실행 칸을 `20324` `20340`(→ `203a0`)으로 적었다. 그러나 관측 기록 어디에서도 `203b0`·`20324` 말고는 실행되지 않았다:
  - 입력 확장 관측 `ms5-scratch/obs2/final`과 계획 재관측 `obs2/reobs/u1..u7` `v2_u1..v2_u8`의 `unr_pcs`에서 두 표와 C7 표의 칸 가운데 기록된 것은 `20324` `203b0` `252b4`(그리고 `20414`)뿐이다.
  - 직접 확인: `reobs/c10v2`는 `203a0..203b4`를 가상 routing하고 `203c4` `203cc`는 routing하지 않은 채 다시 관측했다. 칸 점프 뒤의 TB 시작인 이 두 PC가 실행되었다면 첫 routing 밖 PC로 기록되었어야 하지만 `20300..20520`에서 기록된 PC는 없다. 같은 관측으로 `20340`도 기록되지 않았다.
  - [I] 계획의 칸 목록은 같은 대상(`20414` / `203a0`)으로 가는 칸을 함께 적은 것으로 본다. FR4 방식("실행된 칸만 전사")에 따라 칸 `203c4` `203cc` `20340`은 전사하지 않고, 칸 선택 규칙(결정 2)으로 뒤 단위 정지가 된다.
- [F] **정확 bitmap 재관측(C10 가상 routing)**: `reobs/c10v1`(보정 1·2 + `203c4..203c8` `203cc..203d0`)과 `reobs/c10v2`(최종 18 범위) 모두 예측 일치 frame **6,751**, 실행된 routing 밖 PC C 0 / D 510 / E 108, 첫 정지는 8 run 모두 D(FR11 이후)다: X1 68 frame 659 `b6ca2`, X1 94 439 `b67b2`, X2 68 633 `cc836`, X2 94 409 `cd96c`, X3 68 628 `b6ca2`, X3 94 432 `b6ca2`, X4 68 661 `cd92e`, X4 94 490 `cd92e`(`reobs/c10v2.stops`). 계획 예측 6,751과 같다.
  - [F] **숨은 직선 연속 검사**: `c10base`에 없고 `c10v1`에만 보이는 routing 밖 PC는 **없다**(`work/newvis_c10v1.txt`: 12 run 모두 0). C10 범위의 끝은 모두 routing된 PC로 이어지거나(`1f082` → C9 `1f086`, `20bfe` → C9 `20c00`, `2050c JSR` 복귀 `20516`(C3), `223fa BSR` 복귀 `22408`(C9)) 흐름이 끝난다. 반복은 한 번으로 수렴했다.
  - [F] 기준선 대비 +521(6,230 → 6,751). 계획 표의 +484는 계획 기준선 6,267(FR10 계획 예측) 대비이고, FR10이 C7 표 칸을 C10에 넘긴 37 frame(FR10 계약 결정 1)이 여기에 더해진다(6,267 − 37 = 6,230).
- [F] **범위 밖에서 범위 안 비시작 PC로 들어오는 직접 분기**: 최종 범위에서 없다(`work/intargets_c10_v1.out`의 두 줄 `199a6 dbls` `19ca4 dbls`는 각각 `199a4 SUB.L 53c8(A5),D3`와 같은 꼴 명령의 operand를 명령으로 읽은 것).
- [F] **IO 실행**(`c10base`, `work/c10exec_base.txt`): C10 시작 가운데 실행된 것 105개(C 102 + C7 칸 3), 실행 3,951회(TB 첫 routing 밖 PC로 기록된 수), run 8개(X1~X4 × case 68·94). 실행되지 않은 시작 27개(`1c4dc` `1c514` `1dcb8` `1dcc6` `1effa` `1f004` `1f00c` `1f016` `2041a` `2042e` `2043e` `2050c` `21e04` `21e10` `21e36` `2229a` `222c8` `222d4` `222ec` `2230a` `22322` `22330` `2233e` `22378` `22384` `22396` `252d8`)는 closure로 들어왔다(`1c514` `2041a` `21e04`는 앞 block과 같은 TB 안이라 따로 기록되지 않을 뿐 그 block이 실행될 때 실행된다).

## C10 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **132 block, 239 명령, 1,046 byte, 18 범위**(시작 목록 SHA256 `fe3690da…`, 범위 byte를 이어 붙인 SHA256 `84ec22baf21962bc17b02ff8584c5275379b5408a79479c24dc464bca9acf892`). 짝수 PC 523(내부 391). 기존 routing과 겹침 0(각 범위 안 짝수 PC 전수 검사, `tools/owner.py`: 523개 모두 `animation_player_c10_block`).

| 범위(CPU = 파일 오프셋) | byte | 시작 | SHA256(앞 16자) | 내용 [I] |
| --- | --- | --- | --- | --- |
| `1c4b0..1c51a` | 106 | 13 | `7d08a74e0c884b87` | 28ae 자식 callback `1c4b0`(C5 `1c484`가 만듦, WORD `76` = 소리 번호): `3af8`, WORD `78` := `c`, BYTE `7a`, 설치 `1c4d2`(곧바로) → `SUBQ.W #1,78` → `1c4ea`(`3af8`, 설치 `1c500`) → `1c500`: LONG `c(A6)`(부모)의 LONG `b2` := 0, `JMP 2a00` |
| `1dc8e..1dcd0` | 66 | 7 | `a197580a25720140` | interpreter stub `1dc8a`의 Set 쪽 `1dc8e`(`1d1d0`, BYTE `a7` bit 2, WORD `68`/`1e` := `8834`, 설치 `1f3e0`, `1aa3a`의 D0 bit 3 / 6 → 쓰기만 `1e21c` / `1e8de`)와 Clear 쪽 `1dccc`(`BRA.W 201a2`) |
| `1efd6..1f070` | 154 | 23 | `8605c8bcc957e269` | C4 `1ef96 BNE`의 입력 상태: `1cab6`, 설치 `1efe4`(곧바로) → `1cd98`, BYTE `15` bit 7 → `1fae8`, D0 bit 5 / 1 / 7, `CMPI.B #0,9e`, `AND.W #c`, `1cec2`의 D1.B 1 / 2, BYTE `a7` bit 3, `1d09e` `4bfc0` `ce02` `49fc6` → `201a2` |
| `1f082..1f086` | 4 | 1 | `c314053828d58d3a` | C9 `1f07e BLE`의 fall-through: `LEA 1b20e(PC),A0` → C9 `1f086` |
| `1f3e0..1f3e8` | 8 | 1 | `d6ff64e383f6da8f` | callback `1f3e0`(`1dca4`, C8 `1f764`, `1f3ce`이 씀): `LEA 1b290(PC),A0; BRA.W 1f3ec`(C8) |
| `20324..20328` | 4 | 1 | `a6ed38ab2f3a92cf` | C3 표 `2031c`의 칸 1: `BRA.W 203a0` |
| `203a0..203b4` | 20 | 2 | `a86d8105d65cfb54` | `MOVE.W #0,D0; MOVE.B 9f(A6),D0`, 표 점프 `203ac JMP 203b0(PC,D0.W)`; 칸 0 `203b0 BRA.W 20414` |
| `20414..20444` | 48 | 6 | `73599ab621ff2eac` | BYTE `a4` := 6, `TST.B 9c`: 0이 아니면 LONG `84` := `21602`; 0이면 ROM LONG 표 `20444 + 4 × BYTE a9`, 0이 아니면 `MOVE.L D7,(A6)`(쓰기만) → `204e0` |
| `204e0..20516` | 54 | 6 | `5a18d7ab8f0b7126` | `1cc1a`, WORD `68`/`1e` := `8834`, `492c8`, `1c1e2`, `1c51c`(D1.B = BYTE 4 of LONG `8c(A6)`)의 Z → `20516`(C3) 또는 `1c356` |
| `20bfe..20c00` | 2 | 1 | `3369947e1641cb0c` | C9 settle `20bfa BMI`의 fall-through: `ADDQ.L #7,D2` → C9 `20c00` |
| `21dd0..21e3a` | 106 | 17 | `c9b5de177800e25f` | 칸 `84` 상태 `21dd0`(C4 `21d64 BGT`): `21bc6` `21baa` `21c1c`의 C → `223b2`, `1cabe`, BYTE `aa`, 칸 `84` := `21e04` → `21e04`(목록 `21b0a`, `JMP (A1)` `21e10`), `1cd98`, D0 bit 1 / 0 / 6 / 4 → `223c4` / `223b2` / `21ffc` / `2210c` / `2156a` |
| `22148..22174` | 44 | 6 | `47d0a5cb3603fd86` | C9 `22144 BEQ`의 fall-through: BYTE `aa` := 0, `BCHG #1,a7` → 기록 `1b7fc`/`1b81e`, `1cb08`의 C → `22174`(C9) 또는 `9d` := 0, `1cabe`, `221ca`(C3) |
| `22286..223a0` | 282 | 36 | `7ed1dc36310473e6` | 칸 `84` 상태 `22286` → `2228e`(목록 `216c8`, `JMP (A1)` `2229a`), D0 bit 6, BYTE `7e`/`a5` → `22128`(C9), D0 bit 0 / 1와 BYTE `9d`의 부호(TST.B 뒤 BEQ/BLT/BGT 묶음 셋) → 방향 진입 `22314` `22322` `22330` `2233e`(BYTE `9d`, 기록) → `22348` → 칸 `84` := `22360` → `22360`(목록 `216c8`, `JMP (A1)` `22378`), `2156a`의 D7 → 칸 `84` := `22452` / `22128`, RTS |
| `223fa..22408` | 14 | 1 | `d6593d39b04c26f8` | C9 `21d40 BNE`: BYTE `9d` := 1, `LEA 1b986(PC),A0; BSR.W 1cabe`(복귀 C9 `22408`) |
| `24b78..24b96` | 30 | 3 | `c1c60d6e93c5aef4` | 소리 helper: WORD `-7ff2(A5)`(frame) − WORD `547e(A5)`(마지막) + `c`의 WORD carry → 그대로 RTS, 아니면 `547e` := frame, `3af8` |
| `24ecc..24f18` | 76 | 4 | `ad4713f75718b397` | 2986 자식 callback `24ecc`(C7 LONG 표 `22502`의 칸): WORD `20` := `2a`, LONG `22` := bank 창 LONG `200038`, `24b78`(D0.W `1a65`), LONG `84` := `6f364`, LONG `7a` := `100000`, BYTE `88` := 0, `49f8c`(A1 `25642`), `8ebe`(D0.W `202`) → `BRA.W 24ffa`(C7) |
| `252b4..252b8` | 4 | 1 | `bbb0ad73d5e807b5` | C7 표 `2529c`의 칸 6: `BRA.W 252ce`(메인 결정 4) |
| `252ce..252e6` | 24 | 3 | `edc26a10f0583e15` | `BTST #7,61(A2)`: 0이면 `3af8`(D0.W `189d`) → `252e2 BRA.W 253c8`(C7) |

- [F] **진입**(현재 routing 기준 호출자, `work/refs_c10_v1.out`):
  - 28ae 자식: `1c4b0` ← C5 `1c484 MOVEA.L #1c4b0,A0; JSR 28ae`. 2986 자식: `24ecc` ← C7 `22656`이 LONG 표 `22502`/`2254e`의 칸(`22516` `2254a`)에서 읽은 callback.
  - 설치 값: `1c4d2`(`1c4c2`, 곧바로) `1c500`(`1c4f8`, 다음 frame) `1efe4`(`1efde`, 곧바로) `1f3e0`(`1dca4`; C8 `1f764`, routing 밖 `1f3ce`).
  - 다른 실행부의 분기·fall-through: `1dccc`/`1dc8e` ← interpreter `1dc8a BCC`(결정 5), `1efd6` ← C4 `1ef96 BNE`, `1f082` ← C9 `1f07e BLE`, `20bfe` ← C9 `20bfa BMI`, `21dd0` ← C4 `21d64 BGT`, `22148` ← C9 `22144 BEQ`, `22286` ← C9 `221ae` `221b6 BEQ`, `223fa` ← C9 `21d40 BNE`.
  - 계산 점프 착지: `20324` ← C3 `2031c`(칸 1), `203b0` ← C10 `203ac`(칸 0), `252b4` ← C7 `25298`(칸 6), 칸 `84` 값 `21e04` `2228e` `22360` ← C3 `201a6 JSR (A4)`.
  - callee: `24b78` ← C10 `24ede`(그리고 routing 밖 `24ba8 BSR.B`, `24d10` `24da6` `24e40` `24e8c` `24f2a` `24f76 BSR.W`).
  - 범위 밖 routing 밖에서 들어오는 곳(뒤 단위가 routing할 때 그 단위의 출구가 됨): 표 `203b0`의 칸 `203c4` `203cc` → `20414`, 칸 `203b4` `203b8` `203c8` `203d0`과 표 `2037c`의 칸 `2037c` `20390` `20398` → `2041a`, `20358`의 분기 `2035e BEQ.W 20414`, `20354` `20368` `203e0` `203f2` `204dc` → `204e0`, C3 표 칸 `20328` `20340` → `203a0`, C7 표 칸 `252a8` → `252ce`.
- [F] **설치 값**(`MOVE.L #v,(A6)`): 곧바로 들어감 `1c4d2`(`1c4c2`) `1efe4`(`1efde`). 쓰고 RTS(다음 frame callback) `1c500`(`1c4f8`). 쓰고 다음 block으로 가며 다음 frame에 들어감 `1f3e0`(`1dc92`). **쓰기만**(routing 밖, IO에서 실행되지 않음): `1e21c`(`1dcb8`) `1e8de`(`1dcc6`), 그리고 계산 설치 `2043e MOVE.L D7,(A6)`(ROM LONG 표 `20444`의 값: [F] `0 1ed78 1f3e8 1e21c 1e918 1e9e0`, 첨자 BYTE `a9` 0..5; `2043e`는 IO에서 실행되지 않음).
- [F] **둘째 칸 `84(A6)` 값**: `21e04`(`21dfc`, 곧바로) `2228e`(`22286`, 곧바로) `22360`(`22358`, 곧바로) — 모두 범위 안이고 C3 `201a6 JSR (A4)`의 허용 목록 `PC3_SLOT84`에 이미 있다. 그 밖에 `21602`(`20422`) `22452`(`2230a` `22384`) `22128`(`22396`, C9). `24ee2 MOVE.L #6f364,84(A6)`은 2986 자식 node의 LONG `84`(script)이다(점프 대상이 아님).
- [F] **자식**(`MOVEA.L #v,A0` 뒤 `JSR 28ae`/`2986`): 없다. C10은 자식 `1c4b0`·`24ecc`의 몸통이다(위).

### 계산 점프와 표(결정 2)

- [F] **`203ac JMP 203b0(PC,D0.W)`**(block `203a0`, 새 계산 점프): 표 `203b0..203d4`(ROM 파일 오프셋 = CPU 주소), BRA.W 9칸: 0 `203b0`→`20414`, 1 `203b4`→`2041a`, 2 `203b8`→`2041a`, 3 `203bc`→`20480`, 4 `203c0`→`204c2`, 5 `203c4`→`20414`, 6 `203c8`→`2041a`, 7 `203cc`→`20414`, 8 `203d0`→`2041a`. 색인은 BYTE `9f(A6)`(`MOVE.W #0,D0; MOVE.B 9f(A6),D0` 뒤 `ADD.W` 두 번, 변위 0..`3fc`).
  - [F] ROM writer: 플레이어 node의 BYTE `9f`를 쓰는 ROM 명령은 C2 `1c1e8 MOVE.B D0,9f(A6)`(D0 = BYTE `a0`, C3 계약에 따라 0..8)와 `1bd46 MOVE.B #0,9f(A0)`(0)이다(ROM 전수 검색). 그래서 정상 경로의 변위는 0..`20`이다. 다른 node의 writer(`38cfa` `3dca4` 등)는 이 경로로 오지 않는다 [I].
  - **규칙**(C3 `2031c`·C7 `25298`과 같음): 변위 ≤ `20`이면 PC := `203b0` + 변위(routing이 판정: 칸 0 `203b0`만 C10 block, 나머지 8칸은 다음 dispatch의 `unsupported animation machine PC` = 선언 정지), 넘으면 checked `unsupported animation player c10 jump target`. 실행된 칸만 전사했다(결정 1 보정 3).
- [F] **`JMP (A1)` 세 곳**(C3 `215e6` 목록 조회 뒤, C3·C4·C5·C8·C9 결정과 같은 규칙):
  - `21e10`: 목록 `21b0a`([F] ROM: (`21602`, 0) (`21c22`, 1) (`21e48`, 3) (`21e3a`, 4), LONG 0; C8 `21d9e`와 같은 목록). **허용 대상 = `21602` `21c22`(C3) `21e48`(C9) `21e3a`(C8)**.
  - `2229a` `22378`: 목록 `216c8`((`21602`, 0) 하나). **허용 대상 = `21602`**.
  - 그 밖의 A1은 checked `unsupported animation player c10 jump target`이다. 비교는 LONG 전체다(`1021602`는 거부).
- [F] **앞 단위 표의 칸 확장(결정 4)**: C3 표 `2031c`의 실행 칸 `20324`와 C7 표 `25298`의 실행 칸 `252b4`가 C10 block이 된다. 두 표의 칸 선택 규칙은 바뀌지 않는다(아래 "C3·C7 표 칸의 확장").
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙. [F] 원본 값은 ROM 바이트):
  - LONG 표 `20444`(`2042e`; 첨자 = BYTE `a9` × 4, `MOVEQ #0` 뒤 `LSL.W #2`라 WORD, 부호 확장): 원본 6 LONG `0 1ed78 1f3e8 1e21c 1e918 1e9e0`. 값은 0과 비교하고 0이 아니면 callback으로 쓰기만 한다(코드 주소로 점프하지 않음).
  - bank 창 LONG `200038`(`24ecc`; FR8 `MOVE.L 200038.l,22(A6)`와 같은 꼴): 자료 포인터(LONG `22(A6)`).
  - 넘기기만 하는 포인터(`LEA d(PC)` / `MOVEA.L #`): `1b6fc` `1b20e` `1b290` `1b8a2` `21b0a` `216c8` `1b7fc` `1b81e` `1bbf2` `1bbd6` `1bc0e` `1bc2a` `1b986` `25642`(A0/A1, callee가 읽음).
- [F] TRAP·DIVU·MULU/MULS·MOVEM은 없다.

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작; `work/exits_c10.txt`): `2a00` `3af8` `8ebe` `ce02` `1aa3a` `1c1e2` `1c356` `1c51c` `1cab6` `1cabe` `1cb08` `1cc1a` `1cd98` `1cec2` `1d09e` `1d1d0` `1ed78` `1eeea` `1f070` `1f086` `1f1d8` `1f2a4` `1f3ec` `1f7a4` `1fa3c` `1fa68` `1fae8` `201a2` `20516` `20c00` `2156a` `215e6` `21baa` `21bc6` `21c1c` `21ffc` `2210c` `22128` `22174` `221ca` `223b2` `223c4` `24ffa` `253c8` `492c8` `49f8c` `49fc6` `4bfc0`, 돌아오는 곳 `22408`(`223fa BSR` 복귀, C9) `20516`(`2050c JSR` 복귀, C3), 그리고 `JMP (A1)`의 handler `21602` `21c22` `21e48` `21e3a`.
- [F] **뒤 단위 정지**: C10 block이 분기·fall-through로 닿는 routing 밖 PC는 **없다**. 계산 점프의 미전사 칸(`203b4`..`203d0`)만 정지다. V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS`는 C10 run이 지나갈 수 있는 C1~C9의 남은 정지 12개(`1fd3c` `21ea0` `1d3e0` `4eb6a` `4ef08` `1de3c` `1e21c` `1e8de` `1fc96` `1fd50` `21fa6` `4e69a`)와 FR10의 뒤 단위 정지 11개다(모두 23개).
- [F] 직선 fall-through로 범위를 벗어나는 곳: `1f082`(→ C9 `1f086`), `20bfe`(→ C9 `20c00`). 재관측에서 새로 보인 PC가 없어 가려진 연속은 없다(결정 1).
- [F] TRAP 없음. ROM·RAM 실행 없음. 장치 쓰기 없음(`MOVE`·`CLR`·`BSET`·`ANDI` 등의 대상은 node·부모 node `b2`·A5 work RAM `547e`).

### block 경계·복귀를 넘는 flag(결정 3)

C9 방식대로 block 첫 명령부터 flag를 정하는 명령까지 훑었다(`work/flagscan_c10_v1.txt`). 그리고 C10 출구 대상과 C10 RTS의 복귀 PC에서 C10이 남긴 flag를 읽는 곳을 따로 훑었다(`tools/exitflags.py` → `work/exitflags_c10.txt`: 양쪽 분기를 따라 40 명령까지). X를 읽는 명령은 없다.

- [F] **C 소비 block 7개**(Clear 쪽 / Set 쪽; Unknown C면 `player c10 caller requires known carry`): `21dda BCS 223b2`(C3 `21bc6`), `21de2 BCS 223b2`(C3 `21baa`), `21dea BCS 223b2`(C3 `21c1c`: `ANDI.B #fe,CCR; RTS`라 언제나 Clear — Set 쪽은 실제 생산자가 없음, V1 `STATIC_IMPOSSIBLE`), `21e0c BCC 21e12`·`22296 BCC 2229c`·`22374 BCC 2237a`(C3 `215e6`), `22164 BCC 22174`(C2 `1cb08`). 생산자 쪽은 모두 기존 실행부가 known C를 돌려준다(dispatcher carry 목록의 C9 묶음과 같은 생산자).
- [F] **C를 만들거나 넘기는 C10 block은 없다**(C10 block 뒤는 Unknown). 돌려주지만 읽는 쪽이 없는 flag: RTS `1c4e8`(`SUBQ.W`의 borrow; node callback의 RTS) `1c4f8`(`MOVE.L`) `22312` `2239e`(C3 `201a6 JSR (A4)`로 불려 `201a8 JSR 1a9e8`로 돌아감) `24b94`(`ADDI.W`의 carry 또는 `3af8`의 C; 복귀 `24ee2`와 routing 밖 호출자 `24bac` `24d14` `24daa` `24e44` `24e90` `24f2e` `24f7a`는 모두 flag를 읽지 않는 `MOVE`로 시작). 출구 대상 가운데 C10이 남긴 flag를 읽는 곳도 없다(`work/exitflags_c10.txt`).
- [F] **Z가 경계를 넘는 곳 셋**(계획 시작 목록이 BTST와 Bcc를 다른 block으로 나눴다: 관측의 TB 시작이 `1efee` `1eff6`에 기록됨):
  - `1efee BEQ.W 1fae8`: Z는 `1efe8 BTST.B #7,15(A6)`의 것이다. `1efee`로 오는 길은 `1efe8`의 fall-through 하나뿐이다. **`1efee`는 BYTE `15(A6)`를 다시 읽어 bit 7로 Z를 정한다**(`1efe8`도 같은 BYTE를 읽기만 한다). 주소 24 bit가 work RAM / 고정 ROM(`< 200000`)이 아니면 다시 읽기가 장치 읽기가 될 수 있으므로 checked `unsupported animation player c10 flag source`다(C9 `22180`·FR10 `cd80a`와 같은 규칙).
  - `1eff6 BEQ.W 1f01a`: Z는 `1eff2 BTST.B #5,D0`의 것이다. **`1eff6`은 Z = (D0 bit 5 = 0)으로 다시 계산한다**(출처가 레지스터라 메모리 접근이 없음; FR10 `70ff4`와 같은 꼴).
  - `20508 BNE.W 20516`: Z는 `204fa BSR.W 1c51c`가 부른 C5 `1c51c`의 마지막 `BTST.L D1,D7; RTS`의 것이다(`1c51c`: `MOVEQ #0,D7; MOVE.B 9e(A0),D7; LSL.W #2,D7; MOVE.L 1c52c(PC,D7.W),D7; BTST.L D1,D7; RTS`). D1·D7은 RTS가 바꾸지 않는다. **`20508`은 Z = (D7 bit (D1 mod 32) = 0)으로 다시 계산한다**(레지스터 출처).
- [F] 그 밖의 `Bcc`는 같은 block 안의 명령이 정한 flag를 읽는다: `1c4b0 TST.W` `1c4d2 CMPI.B` `1c4e0 SUBQ.W`(결과 0) `1c4ea MOVE.W` `1c500 CMPI.L`(LONG) `1f02e`/`1f036 CMPI.B`(BYTE) `1f00c`/`1f048 AND.W`(WORD) `2042e MOVE.L`(LONG) `22148 BCHG`(이전 bit) `24b78 ADDI.W`(WORD carry), 그리고 묶음 Bcc 셋 `222c8 TST.B; BEQ; BLT` `222e0 TST.B; BEQ; BGT` `222f0 TST.B; BEQ; BGT; BLT`(BYTE `9d`의 0 / 양수 / 음수; `222fc BLT`는 언제나 분기 — V1 `BRANCH_IMPOSSIBLE`).

### IO 실행 run과 frame

- [F] 실행 run 8개(X1~X4 × case 68·94; `reobs/c10base` 기준 C10 PC가 처음 기록된 frame의 처음 ~ 마지막): X1 68 590..825, X1 94 384..602, X2 68 608..649, X2 94 386..439, X3 68 591..1,117, X3 94 391..620, X4 68 520..1,148, X4 94 360..1,006. 플레이어 node는 `100cb8`이고, `1c4b0`·`24ecc` 자식과 C7 `25102` 상태는 pool `100800..104c00`의 node다(`work/natscan_c10.out`).
- [F] **IO 예측(C10 연결)**: 6,230 → **6,751**(+521; 재관측 `reobs/c10v2`). 첫 정지는 8 run 모두 D(FR11~FR13)다(위 "재확인과 범위"). [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다.
- [F] 원래 IO 관측은 C10 코드를 실행하지 않는다(계획 §10.4: X run에서만 실행). 일치 173,966은 그대로여야 한다(작업자는 돌리지 않음; 메인 runner).

## interpreter stub `1dc84`/`1dc8a`와의 관계(결정 5)

- [F] **현재 구조**(C2 계약 결정 7, C6 계약 결정 6): `1dc84`(`JSR 49fc6`, 복귀 `1dc8a`)와 `1dc8a`(`BCC.W 1dccc`: C Clear → `1dccc`, Set → `1dc8e`)는 interpreter 실행부(`animation_machine_interpreter.cpp`)의 단일 PC stub이고 dispatcher carry 목록 첫 줄에 있다. C6 `1dc7a JSR ce02`의 복귀가 `1dc84`다.
- [F] **결정: stub 실행부는 바꾸지 않고, 두 인계 목표 `1dccc`/`1dc8e`를 C10 block 시작으로 routing한다.** stub의 `1dc8a`는 지금처럼 known C로 다음 PC를 고르고 dispatcher로 돌아가며, dispatcher가 그 PC를 C10으로 보낸다. `1dccc` `1dc8e`는 C를 읽지 않으므로 carry 목록에 넣지 않는다(들어올 때 Unknown이 되어도 결과가 같음). `1dc8e`·`1dccc` 다음 코드(`1d1d0`, `201a2`)도 그 C를 읽지 않는다(`work/exitflags_c10.txt`).
  - 이전 동작: stub → `1dccc`/`1dc8e` → 다음 dispatch에서 `unsupported animation machine PC`(선언 정지; C6~C9 spec의 `EXIT_STOPS`).
  - 새 동작: stub → C10 `1dccc`(→ C3 `201a2`) / `1dc8e`(→ C2 `1d1d0` → `1dc92` …). stub 자체의 동작·carry 규칙·range는 그대로다.
  - 대안(stub을 C10으로 옮김)은 C2·C6 계약과 carry 시험(`animation_machine_carry_test.cpp`, `verify_animation_machine_carry.py`, `observe_animation_machine_carry.py`가 stub과 그 두 목표를 정지로 씀)을 바꿔야 하므로 고르지 않았다.
- [F] 영향: carry 시험은 두 목표를 정지 PC로만 쓰므로(정지 검사가 dispatch보다 먼저) 그대로 통과한다. C6~C9·FR10 spec은 `1dccc` `1dc8e`를 `ROUTED_LATER`에 두어 선언 정지로 유지한다. 실제 ROM 차분은 `1dc84`를 `cb` 진입으로 넣어 stub → C10 인계를 Unicorn과 비교한다(FOLLOW_ANIM에서 `49fc6` 안까지 따라감).

## C3·C7 표 칸의 확장(결정 4)

- [F] **C3 표 `2031c`**: 이전 = 전사한 칸 없음(9칸 모두 뒤 단위 정지). 새 = 실행된 칸 `20324`가 C10 block. C3 실행부의 칸 선택 코드는 바뀌지 않았다(주석만). 기록은 C3 계약 끝 "뒤 단위 변경 기록: player C10".
- [F] **C7 표 `25298`**: 이전 = 실행 칸 `252a4`만 C7 block. 새 = `252a4`(C7)와 `252b4`(C10). C7 실행부도 주석만 바뀌었다. 기록은 C7 계약 끝.
- [F] 이 확장은 "칸이 routing되었는지"의 변화다. 표 점프 규칙(변위 범위 검사)은 세 표(`2031c` `25298` `203ac`) 모두 같다.

## 공통 규칙·native 검증 계획

FR2..FR10, C1~C9 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_player_c10.cpp`, 함수 `animation_player_c10_block`. 오류 문자열은 `unsupported animation player c10 PC`(범위 안 내부 PC 직접 진입), `player c10 caller requires known carry`(C 소비 block 7개에 Unknown C), `unsupported animation player c10 jump target`(결정 2의 목록 밖 A1, 표 밖 변위), `unsupported animation player c10 flag source`(결정 3의 `1efee` Z 출처) 네 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(18 범위, FR10 줄 뒤; `)ok=animation_player_c10_block(c);`를 같은 줄에 둔다), `carry_preserving_pc`의 FR10 묶음 뒤에 주석 달린 case 묶음 하나(소비자 7), `animation_machine_internal.h`에 선언 하나(FR10 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# player C10 refresh:` 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 곧바로 들어감 `1c4d2` `1efe4`와 칸 `84` 값 `21e04` `2228e` `22360`은 쓰고 그 값으로 들어가고, `1c4f8`(`1c500`)은 쓰고 RTS, `1dc92`(`1f3e0`)·`1dcb8`(`1e21c`)·`1dcc6`(`1e8de`)·`2043e`(D7)·`20422`/`2230a`/`22384`/`22396`(칸 `84`)는 쓰고 다음 block으로 간다.
- **자료 읽기**(live bus): node field(A6: BYTE `15` `7a` `7e` `9c` `9d` `9e` `9f` `a5` `a6` `a7` `a9`, WORD `1e` `76` `78`, LONG `c` `8c`), 부모 node(A0 = LONG `c(A6)`: LONG `b2` 쓰기), 기록 A4 = LONG `8c(A6)`(BYTE `4`), A2(BYTE `61`), A5 field(WORD `-7ff2` `547e`), 고정 ROM(위 "계산 점프와 표"). 단위 시험은 고정 ROM·bank 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): LONG 표 `20444`(6) = `00010000 0 12345678 0001ed78 0 80000000`, bank 창 LONG `200038` = `00abcdef`, WORD 표 `1b7fc..1b860`(C2 `1cb08`/C5 `1cb1a` 사슬), LONG 표 `1c52c`(C5 `1c51c` 사슬) = `0000ffff 80000001 00f0f0f0 7ffffffe`, BYTE 표 `21ba6`(C3 `21baa` 사슬), 목록 `21b0a` = (`21602`, 2) (`21c22`, 5) (`21e48`, 0) (`21e3a`, 3), 0과 `216c8` = (`21602`, 3), 0(handler는 ROM과 같고 key가 다름; C3 `215e6` 사슬). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W #k,D0`, `MOVE.W d(An),D0/D6/D7`, `SUB.W D6,D7`, `ADDI.W #c,D7`, `LSL.W #2,D7`, `AND.W D0,D1`, `MOVE.B`(레지스터 BYTE), `SUBQ.W`(메모리 WORD), `ANDI.B`/`BCHG`/`BSET`/`BCLR`(메모리 BYTE)). `MOVEQ`·`MOVE.L`·`MOVEA.L`·`LEA`·`CLR.L`·`ADDQ.L`은 LONG 전체(mod 2^32). 비교: `CMPI.B #1/#2,D1`·`CMPI.B #0,9e/7a`·`TST.B`(BYTE), `TST.W`(WORD), `CMPI.L #0,D0`·`MOVE.L` 뒤 BEQ(LONG), `ADDI.W`의 carry(WORD에서 넘침 = 무부호 합 > `ffff`), `TST.B`+`BLT/BGT`(부호 BYTE). bit: `BTST #n,D0`(LONG bit n: 0 1 3 4 5 6 7), `BTST.L D1,D7`(bit D1 mod 32), `BTST/BSET/BCLR/BCHG #n,d(A6)`(메모리 BYTE, bit mod 8). 표 첨자 `(PC,Dn.W)`와 `-7ff2(A5)`는 부호 확장한다.

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `6a7d76c3817fdab2a07af95b5d1be6cb14fca2c81f992bba558a88bddb14cdc6` → `63f7d470922dfab836b19417f2a16dba5d170d3424906a13c04ad69f53a48eb7`, `animation_machine_internal.h` `9f371fcfefb8bf19538c6b6e6e779a9e95ea9019c77816537a4b0ce01870425c` → `f1180a35ac8dab11f98c309ba7c890110e5e141f63553c3239c51375fb1c7f4a`(옛 값은 `# player C10 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 작업 트리와 scratch clone root에서 확인했다(아래 "검증 수치").
- [F] **C3·C4·C9 시험 생성기·시험**(오류 행; 이전 = 그 PC에서 `unsupported animation machine PC`. C10이 그 PC를 routing해서 C++가 C10 코드를 실행하므로 바뀜. 원래 뜻(실패 PC)을 지키는 C9 선례 방식):
  - C3 `error-21610-key-1`(실패 PC `21dd0`) → `error-21610-key-1-then-1cac2`: C10 `21dd0`..`21dee`가 실행된 뒤 C2 `1cac2`가 선언하지 않은 고정 ROM 기록 `1b8a2`를 읽어 `missing or ambiguous physical program bus ROM byte`. `21610`이 BYTE `aa(A6)`를 먼저 써서 `21dd0`의 `BCLR`만 실패시킬 수 없다(실패 PC가 경로를 따라 옮겨 감; C9의 `21e48` → `21ea0`와 같은 처리).
  - C4 `error-21d60-then-21dd0`: node를 `1fff60`(위쪽 RAM 거울; BYTE `9d(A6)` = `1ffffd`)에 둬서 C10 `21dd0`의 첫 접근 `BCLR #5,a7(A6)`가 bank 창 `200007`을 읽게 했다 → `missing or ambiguous physical program bus ROM byte`, 실패 PC `21dd0` 그대로.
  - C9 `error-1f070-then-1f082` `-20bee-then-20bfe` `-22128-then-22148` `-20bc4-then-20bfe` → `-1f070-then-1f086` `-20bee-then-20c16` `-22128-then-22160` `-20bc4-then-20c16`: C10 `1f082`(LEA)·`20bfe`(ADDQ.L)는 메모리에 접근하지 않고 `22148`은 `22128`이 먼저 접근한 field만 쓰므로, A7을 홀수로 해 실패 PC를 그 뒤 첫 스택 접근(C9 `1f086 BSR.W`, C9 `20c16 JSR`, C10 `22160 BSR.W`)으로 옮겼다(`program bus requires even WORD/LONG address`). `-221a2-then-22286`(A6 = `fff78`: LONG `8c(A6)` = `100004`는 work RAM, `22286 MOVE.L #2228e,84(A6)`가 `ffffc`(고정 ROM)에 씀)·`-21d3c-then-223fa`(A6 = 0: `223fa MOVE.B #1,9d(A6)`가 고정 ROM에 씀)는 `unsupported animation machine write device`로 실패 PC를 지켰다.
  - 생성기 셋을 다시 돌려 그 행만 바뀜을 확인했다(`work/before/` 대비 diff: C3 1행, C4 1행, C9 6행). 시험 줄의 fixture 수는 그대로다(pc3 1,293, pc4 1,372, pc9 1,678).
  - C3·C7 생성기의 표 칸 stop-only 목록 `JUMP_TARGETS`에 주석만 더했다(출력 그대로).
- [F] **motion walk 시험 `engine/tests/animation_machine_motion_walk_test.cpp`**: 기록 type `7ff0`(대상 `18c0e + 7ff0 = 20bfe`, C9가 고른 값)은 이제 C10 시작이다. 이전 기대값(`unsupported animation machine PC`)의 뜻을 지키도록 type을 `2562`(대상 `1b170` = C9 `20aa4`/`21376`의 ROM WORD 표: 자료라 어느 실행부의 PC도 아님)로 바꿨다(주석에 이전 값과 이유).
- [F] **scene update 시험 `engine/tests/animation_machine_scene_update_test.cpp`** `path_policy`: 경로 opcode `7f7a` / `7f7c`(대상 `19e8a + op` = `21e04` / `21e06`, C9가 고른 값)은 이제 C10 시작 / 내부 PC다. 뜻("executor 밖")을 지키도록 opcode를 `7c80` / `7c82`(대상 `21b0a` / `21b0c` = C3 `215e6`의 ROM 목록: 자료)로 바꿨다.
- [F] **V1 spec**:
  - `EXIT_STOPS`·`ROUTED_LATER`(C2~C9가 쓴 방식): pc3~pc9·fr10의 `EXIT_STOPS`에 C10 진입 가운데 없던 것을 끝에 더하고(`UNIT_EXITS` 조각은 그대로), `ROUTED_LATER`에 C10 진입 14개(`1dc8e` `1dccc` `1efd6` `1f082` `20bfe` `21dd0` `22148` `22286` `223fa` `20324` `21e04` `2228e` `22360` `252b4`)를 더했다. 그 run은 그 PC에서 계속 멈춘다(계산 점프 착지 `20324` `252b4` `21e04` `2228e` `22360`도 `OTHER_JUMP_PCS` 규칙이 이제 routing되었다고 run을 이어 가지 않도록).
  - pc9·fr10: 두 번째 확인 `for t in EXIT_STOPS: require(unit_of(t) is None)` → `is None or t in ROUTED_LATER`. fr10: `252b4` `252ce` `252d8` `252e2`는 routing 밖이어야 한다는 확인(FR10 결정 1) → C10 시작이어야 한다는 확인.
  - pc3: 계산 점프 대상(slot-84 값·목록·표 칸)의 소유자 확인에 `animation_player_c10_block`을 허용.
  - pc7: 표 칸 확인 `{252a4}` → `{252a4, 252b4}`(소유자 C7 또는 C10); 오류 fixture `25294-d0-6-entry`(실패 PC `252b4`) → `25294-d0-6-then-252d8`(`252b4` → `252ce`(BYTE `61(A2)` = 0) → `252d8 JSR 3af8`가 홀수 A7에서 실패).
  - pc4 `21d60-then-21dd0`: A7 홀수 → C10 `21dd0`의 `BSR.W 21bc6`가 `program bus requires even WORD/LONG address`, 실패 PC `21dd0` 그대로(`21d60`은 스택을 쓰지 않음).
  - pc9 `1f070-then-1f082` 등 5행: C9 생성기와 같은 방식(위).
  - V1 회귀는 모두 FR10 기록과 같은 fixture 수로 통과했다(아래 "검증 수치").
- [F] 바뀌지 않음(확인): carry 시험(`animation_machine_carry_test.cpp`: `1dccc` `1dc8e`를 정지로만 씀), FR10 시험의 이웃 목록(`252b4` .. `252e2`는 FR10 범위 밖이라는 확인), C5 시험의 `1c4b0`(레지스터 값), C8 시험의 `1f3e0`(쓰기 값), C7 시험(표 칸 `252b4`는 정지로만 씀), objects n34 시험의 `21dd2`(레지스터 값), objects b2d 시험의 `20500`(레지스터 값). 저장소 tools·시험에서 C10 범위 안 PC를 쓰는 다른 곳은 위 항목뿐이다(전수 검색 `tools/c10refs_repo.py` → `work/c10refs_repo.out`).
- [I] 원래 IO 관측과 frame 비교(d1·controller·irq·demo)는 C10 코드를 실행하지 않으므로 결과가 같아야 한다. 메인 runner가 확인한다.

## 결정

1. **범위: 132 block, 18 범위.** 계획 127 + C7 표 칸 4 block(메인 결정 4) + `2041a`(범위 밖 실제 분기 대상). 계획 표의 "실행 칸" `203c4` `203cc` `20340`은 관측에서 실행되지 않아 전사하지 않는다. 숨은 직선 block은 없다(가상 routing 재관측에서 새로 보인 PC 0). 예측 6,751(+521).
2. **계산 점프**: 새 표 점프 `203ac`는 변위 ≤ `20`이면 칸(실행 칸 `203b0`만 C10 block), 넘으면 checked jump-target 오류. `JMP (A1)` `21e10`(목록 `21b0a`) `2229a` `22378`(목록 `216c8`)은 목록의 handler면 그 PC로, 그 밖은 checked 오류(LONG 비교). 고정 ROM 표 `20444`와 bank 창 LONG `200038`은 live bus로 읽고 상한을 검사하지 않는다.
3. **flag.** C 소비자 7개는 known C를 읽거나 checked 오류. C10 block은 C를 만들거나 넘기지 않는다. Z 읽는 곳 셋: `1efee`(BYTE `15(A6)` 다시 읽기; work RAM / 고정 ROM이 아니면 checked flag-source 오류), `1eff6`(D0 bit 5), `20508`(D7 bit (D1 mod 32)).
4. **앞 단위 표의 칸**: C3 `2031c`의 칸 `20324`와 C7 `25298`의 칸 `252b4`(→ `252ce` `252d8` `252e2`)를 C10 block으로 routing한다. 두 표의 규칙은 그대로이고 실행부는 주석만 바뀐다(C3·C7 계약 끝에 기록).
5. **interpreter stub**: `1dc84`/`1dc8a` 실행부는 그대로 두고 인계 목표 `1dccc` `1dc8e`를 C10 시작으로 routing한다(위 절).
6. **V1 natural family.** 확장 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)이 읽는다. pool `100800..104c00`의 node가 callback `1c4b0` `1c4d2` `1c500` `24ecc` 또는 C7 `25102`를 가졌거나, 플레이어 node(`100cb8` `100da8`)가 callback `1efe4` `1f3e0`·칸 `84` `21e04` `2228e` `22360`을 가졌거나, 재관측이 C10 시작을 처음 기록한 frame의 플레이어 node(routing된 callback)인 frame 89개(`work/natural_c10.json`: run과 key마다 처음·가운데·마지막 frame)에서 C10 시작에 닿는 run을 쓴다.
7. **앞 단위 spec.** pc3~pc9·fr10의 `EXIT_STOPS`·`ROUTED_LATER`에 C10 진입 14개를 두어 그 run은 계속 그 PC에서 멈춘다. 오류 fixture는 실패 PC를 지키거나 경로를 따라 옮긴다(위).
8. **다음.** C10 연결로 확장 관측 IO 6,751(+521)을 메인 runner가 확인한다. 다음 단위는 FR11(계획 순서; 첫 정지 `b6ca2` `b67b2` `cc836` `cd96c` `cd92e`).

## 미확인

- [U] node field·전역 값의 의미(BYTE `7a` `9c` `9d` `9f` `a4` `a5` `a7` `a9` `aa`, WORD `76` `78` `68` `1e`, LONG `b2` `84` `7a`, A5 `547e`, 표 `20444`, 기록 `1b6fc` … `1bc2a`). 이름(28ae 자식의 소리 반복, 소리 helper, 입력 상태, 방향 진입)은 동작에서 붙인 [I]이다.
- [U] `21dea`의 Set 쪽(`223b2`)은 실제 생산자 `21c1c`가 늘 Clear라 선언 C로만 확인했다(V1 `STATIC_IMPOSSIBLE`).
- [U] IO 관측에서 실행되지 않은 이 단위의 block 27개(위 "재확인과 범위")는 closure로 들어왔다(V1 선언 상태·natural·실제 ROM 차분·단위 시험으로만 확인).
- [U] 표 `203b0`의 칸 1..8과 C3 표 `2031c`의 칸 0·2..8, C7 표의 칸 0·1·3·4·5·7·8이 실제로 쓰이는 조건(BYTE `9f`/`a0` 값)과 그 대상(`2041a` `20480` `204c2` 등)은 이 관측에서 실행되지 않았다.
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC).
- [U] natural fixture의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C9와 같음).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_player_c10.cpp`(case label 132 = `starts_c10_final.txt`와 집합 일치; 공용 함수 `pc10_get` `pc10_put` `pc10_bit` `pc10_field_bit` `pc10_input_bit` `pc10_byte_is` `pc10_mask` `pc10_carry` `pc10_field_call` `pc10_word_call` `pc10_install` `pc10_slot84` `pc10_turn` `pc10_flag_byte` `pc10_list_jump` `pc10_table_jump`, 목록 `PC10_LIST_21B0A` `PC10_LIST_216C8`), `engine/tests/animation_machine_player_c10_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_e`), `tools/generate_animation_machine_player_c10_test_table.py`(생성기; C9 생성기 꼴, single 5 = Z 읽는 `1efee`(native SR Z = BYTE `15(A6)` bit 7 clear)·`1eff6`(D0 bit 5 clear)·`20508`(D7 bit (D1 mod 32) clear), 계산 점프 착지 검사 `JUMP_ALLOWED` = 두 목록과 표 `203b0`, V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 55초), `tools/unit_fixture_specs/pc10.py`(V1 spec; C9 spec의 공용 부분 그대로, 단위 부분 교체, `EXIT_STOPS`(23), `CONSUMERS`(7), `Z_READERS`(`1efee` `1eff6` `20508`), `DATA_SET`(`1efe8` `1eff2`: 다음 block이 Z 읽는 곳뿐인 BTST block), `BUNDLED`(`222d0` `222e8` `222f8` `222fc`: 묶음 Bcc; `static_next`/`block_next`를 묶음 셋까지 일반화), `STATIC_IMPOSSIBLE`(`21dea` → `223b2`), `BRANCH_IMPOSSIBLE`(`222fc` → `22300`), `JUMP_PCS`(`203ac`)와 표 밖 착지를 버리는 trace, natural family는 확장 관측 pack). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `work/starts_c10_final.txt`(SHA256 `fe3690da…`).

- **`1c4b0..1c51a`(13)**: `1c4b0 1c4b8 1c4c2 1c4d2 1c4dc 1c4e0 1c4e8 1c4ea 1c4f2 1c4f8 1c500 1c50e 1c514`
- **`1dc8e..1dcd0`(7)**: `1dc8e 1dc92 1dcb0 1dcb8 1dcbe 1dcc6 1dccc`
- **`1efd6..1f070`(23)**: `1efd6 1efde 1efe4 1efe8 1efee 1eff2 1eff6 1effa 1f004 1f00c 1f016 1f01a 1f022 1f02a 1f02e 1f036 1f03e 1f048 1f052 1f056 1f05c 1f066 1f06c`
- **`1f082..1f086`(1)**: `1f082`
- **`1f3e0..1f3e8`(1)**: `1f3e0`
- **`20324..20328`(1)**: `20324`
- **`203a0..203b4`(2)**: `203a0 203b0`
- **`20414..20444`(6)**: `20414 2041a 20422 2042e 2043e 20440`
- **`204e0..20516`(6)**: `204e0 204e4 204f6 204fa 20508 2050c`
- **`20bfe..20c00`(1)**: `20bfe`
- **`21dd0..21e3a`(17)**: `21dd0 21dda 21dde 21de2 21de6 21dea 21dee 21df6 21e04 21e0c 21e10 21e12 21e16 21e1e 21e26 21e2e 21e36`
- **`22148..22174`(6)**: `22148 2215c 22160 22164 22168 22170`
- **`22286..223a0`(36)**: `22286 2228e 22296 2229a 2229c 222a0 222a8 222b0 222ba 222c0 222c8 222d4 222d8 222e0 222ec 222f0 22300 22304 2230a 22312 22314 22322 22330 2233e 22348 2234c 22360 22364 2236c 22374 22378 2237a 2237e 22384 22396 2239e`
- **`223fa..22408`(1)**: `223fa`
- **`24b78..24b96`(3)**: `24b78 24b8a 24b94`
- **`24ecc..24f18`(4)**: `24ecc 24ee2 24f06 24f14`
- **`252b4..252b8`(1)**: `252b4`
- **`252ce..252e6`(3)**: `252ce 252d8 252e2`

## 검증 수치

작업자 최종 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j4 all test`(최종 실행부·시험): 종료 0, 경고 0, Assert 0, Python 310 OK(`trial_logs/make_final.log`). C10 시험 줄: `animation machine player pc10: 979 fixtures (641 single-block, 199 path, 54 producer chain, 14 declared C, 71 checked error (14 with a later failing PC), 50 kept C), 132 blocks, 3924 calls, 110786 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 출구 중 stop이 아닌 것 0, 실제 사슬 9개(`21dd0`→`21dda`(`21bc6`), `21dde`→`21de2`(`21baa`, 합성 표 `21ba6`), `21e04`→`21e0c` `2228e`→`22296` `2236c`→`22374`(`215e6`, 합성 목록), `22148`→`22164`(`1cb08`, 합성 표 `1b7fc`), `1efe8`→`1efee` `1eff2`→`1eff6` `204fa`→`20508`(Z; 마지막은 `1c51c`, 합성 표 `1c52c`)). `21de6`→`21dea`(`21c1c`)는 Clear만 나와 선언 C 행만 있다. 계산 점프 행이 표 `203b0`의 9칸과 목록 handler 넷(`21602` `21c22` `21e3a` `21e48`)에 모두 멈춘다. 생성기를 다시 돌려 C10 시험 파일이 바이트 단위로 같음을, C7 생성기를 다시 돌려 C7 시험 파일이 FR10 기준과 바이트 단위로 같음을 확인했다(`trial_logs/gen_c10_repro.log` `gen_c7.log`). 다른 시험 줄의 fixture 수는 FR10 기록과 같다(pc3 1,293, pc4 1,372, pc9 1,678, fr10 1,074).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, `work/ubsan.sh`, C10 시험): 빌드 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_build.log` `ubsan_player_c10.log` `ubsan_summary.log`).
- [F] V1 pc10(작업자, `--workers 4`): fixture 1,334개(match 881, error 443, mismatch 10; natural 78) failed 0, `ok` true, 방문 시작 132/132, 빠진 후속 0, 도달 못한 분기 결과 0(`222fc` → `22300`은 `BRANCH_IMPOSSIBLE`), carry oracle Unknown/Clear/Set = 868/7/6(`trial_logs/v1_pc10_try2.log`, `work/v1/pc10_try2/report.json`). 첫 시도(`v1_pc10_try1.log`)도 fixture 1,334, failed 0이었으나 실행 중에 spec을 고쳐(`BRANCH_IMPOSSIBLE` 추가) 검증기의 `inputs_unchanged_after`가 false였다; 고친 뒤 다시 돌린 것이 위 결과다.
- [F] V1 회귀(작업자, `work/v1_regs.sh`, `--workers 3`; `trial_logs/v1_regs.txt`): pc1 1,264, pc2 1,743, pc3 1,829, pc4 1,873, pc5 1,755, pc6 1,856, pc7 2,077, pc8 986, pc9 2,347, se1 2,102, fr9 1,415, fr10 2,170(모두 failed 0, `ok` true; FR10 기록과 같은 수). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·op, WORD/BYTE → LONG, 복귀 PC·호출 대상, carry tag, mask, 상수·설치 값, `pc10_*` helper 인자) + 손으로 고른 helper·block 변이(표 점프 `203ac`의 범위·폭·기준, `JMP (A1)` 목록·비교 폭·guard, Z 읽는 `1efee`(bit·반전·guard·24 bit·폭)·`20508`(반전·mod 8·D0)·`1efe8` 읽기, `24b78`의 SUB 순서·carry 경계·LONG 합·A5 부호 확장, `2042e`의 LSL·폭·기준, 묶음 TST.B 셋, `22148` BCHG, `1c500` LONG 비교, `1c4e0` SUBQ.W 등) + dispatcher carry 목록 7개·추가·범위 24개를 적용해 만든 것, 484개; `--workers 4`): 1회째 `killed 466 of 484`(`trial_logs/mut_first.log`). 생존 18개 중 7개는 시험 빈틈이었고 규칙 `rules_e`로 메웠다(`1efee`의 24 bit 출처(guard 변이 둘), `1efe8` BTST의 field와 읽기 실패(둘), `1f036`의 BYTE 비교, `2042e`의 WORD 첨자, `24b78`의 A5 부호 확장 변위; `trial_logs/mut_gaps.log`). 남은 11개는 동치다(`mut/equivalents.txt`, 사례별 이유: mask `c`라 하위 BYTE뿐인 `pc10_mask`, 결과를 쓰지 않는 BTST의 bit 번호, `MOVEQ #0` 뒤라 같은 D7 셋(BYTE→LONG 쓰기, mask 폭, LSL 폭), 즉치 bit 번호가 모두 8 미만인 둘(`pc10_bit`, `pc10_input_bit`), `am_write`의 자체 mask, 양수 변위의 부호 확장, 같은 술어로 다시 쓴 `1c4e0`, BEQ/BLT 순서를 바꾼 `222c8`). 규칙을 더한 뒤 전체 2회째 `killed 473 of 484`(`trial_logs/mut_second.log`), 남은 11개가 동치 목록과 같다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`, 메인 runner용), `real_pc10.py`(FR10 harness에 C10 world(`c10_world`)·소비자 7·Z 읽는 `1efee`(native SR Z = BYTE `15(A6)` bit 7 clear)·`1eff6`(D0 bit 5)·`20508`(D7 bit (D1 mod 32))·선언 정지(C1~C9·FR10의 남은 정지, 표 `2031c` `203b0` `2529c`의 routing 밖 칸)·`cb` 진입에 stub `1dc84`와 표 점프 `20318`(→ `20324`)·`25294`(→ `252b4`); 계산 점프 착지를 trace 전체에서 대조(`ALLOWED_C10` = 표 `203b0`, 목록 `21b0a`/`216c8`); 분류 `JUMPTGT10` `ZSOURCE10`(C10) 추가; `native_safe` 기본 유지)): 작업자 300건 seed 1 `mismatches 0`(`covered starts 127 of 132`; 문서화된 분류: 2986 실패 경로의 caller X 17건(C7 결정 6), C3 jump-target 7건(무작위 칸 `84` LONG의 `201a6`, stub `1dc84` → C10 `1dccc` → `201a2` 경로 포함, 무작위 BYTE `a0`의 `2031c`), C7 jump-target 1건, C10 jump-target 3건(무작위 BYTE `9f`의 `203ac`, 직접 진입한 `21e10` `2229a`); 깨끗이 멈추지 않은 native 58건 건너뜀; native oracle abort 0, `trial_logs/real_n300_s1.log`). 앞선 50건 seed 11 시험도 `mismatches 0`(`trial_logs/real_t50.log`).
- [F] **IO, 입력 확장 관측**(C10 연결 뒤, `--workers 3`): run 12, native 비교 frame 14,500 가운데 일치 **6,751**(예측 6,751, 기준선 6,230 → +521), 불일치 0(beyond 0), C++ 오류 0, chain divergence 0, 수용 키 모두 true(`negatives_ok` 포함, `P1` case 94)(`trial_logs/io_ext_c10.log`; `verification.json` SHA256 `7e8fed3f79f7be75…`, `frontier.json` `9e63b4c3b2736fec…`, scratch `io_ext_c10/`). 첫 정지(확인된 frontier): X1 68 frame 659 `b6ca2`, X1 94 439 `b67b2`, X2 68 633 `cc836`, X2 94 409 `cd96c`, X3 68 628 `b6ca2`, X3 94 432 `b6ca2`, X4 68 661 `cd92e`, X4 94 490 `cd92e` — 재관측 예측(`reobs/c10v2.stops`)과 run·frame·PC가 모두 같다. 모두 D(FR11~FR13)다.
- [F] 원래 IO 관측·frame 비교·legacy 검증기는 작업자가 돌리지 않았다(메인 runner).
- [F] `CPP_PINS`: 작업 트리와 scratch clone root(`work/mkroot.py`; 확인 뒤 symlink를 먼저 지우고 삭제)에서 파일 SHA와 같다(4 / 9 pin, 불일치 0, `trial_logs/pincheck_tree.log` `pincheck_root.log`).
