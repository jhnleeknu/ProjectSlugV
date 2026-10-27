# 영역 C 단위 C11(세 번째 IO 관측의 첫 C 단위: continue 보조 `ca64`/`ca6a`, stage script 보조 `1a952`, 기록 보조 `1cb72`/`1cb76`, 등장 방식 D7 사슬의 나머지 `1d3e0`..`1d434`와 그 갈래 `1d722` `1d746` `1d8e2` `1d906` `1d9b2` `1db28` `1db46` `1ddd8`, 속도 보조 `1e5aa`(MULS 2), 28ae 자식 `1e67a` → `1e6c0`, 상태 `1e8de` → `1e918` → `1e92c`, 칸 `84` 상태 `21950` → `21960`·`21a42` → `21a76`(`JMP (A1)` `21a82`), 2986 자식 `3fedc`, WORD 표 `49bf2`, credit 읽기 `4a90e`, 기록 기준 `4d196`, continue 진입 `4eb6a` → callback `4ebe2` → `4ec32`..`4ed34`, 등장 보조 `e8c3a`(MOVEM.W), 209 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §11.5 표의 C-1 행과 §11.8(C-1 상세 명세)을 기준으로 삼고, 구조·공통 규칙은 C10 계약(`animation-machine-player-c10-contract.md`; 정확 bitmap 재관측, V1 natural family, IO 검증기 pin 표)을 따르며 다른 점만 적는다. 단위 이름은 C11, 파일 접두어는 `player_c11`(C++) / `pc11`(V1 spec)다. 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다. BIOS 실행, 자연 scheduler, IRQ timing은 주장하지 않는다. stage 선택·continue 설정·PLAYER_START는 세 번째 관측의 선언 host 쓰기다(계획 §11.2).

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB(작업 시작·끝의 크기 8,388,608, mtime 1791291625 그대로). 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 LONG `200088`(`1e67a`)을 live bus로 읽는다. 장치 쓰기는 없다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `main` `7c2fd60` + 세 번째 관측 계획 커밋 `9a38aa6`(branch `claude/c11-core`, origin `claude/io-observation-3`). routing 기준 `engine/src/animation_machine.cpp` SHA256 `1feb63c9de015b8ceb3ecc56ae51b31cba1bf0a17a726216db249697e718db2f`, `animation_machine_internal.h` `1d4a08c30c9e9e9dbfeb4dd8b8fea3e5dad8b8f2640e1df430dd3b5310f0d3f3`(FR14 계약의 새 값과 같음).
- [F] 관측 입력(읽기 전용): 세 번째 IO 관측 `ms5-scratch/obs3/final`(`observation.json` SHA256 `bac35488287f2a5ac776fdcc1dccd3033d65b18181a4ee66850c9f7556c22657`, compared_sha256 `d30e68d6b8c7f69181be12b00f017c4eafccb705416af7e8beea02b6d9595673`, 검증기 pin 이름 `io-ext2`). 계획 §11.7 결정 1(공유 `artifacts/animation_machine_io_ext2/`로 옮김)이 아직 정해지지 않아 scratch에 있다. V1 natural family는 이 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT2`)으로 읽는다(결정 4).
- [F] 이 단위의 정확 bitmap 재관측(scratch, 관측기 `tools/observe_animation_machine_io_ext2.py` 수정 없음): `reobs/c11v1`(계획 범위 30개를 `--extra-routed`로 가상 routing). 결정 1.
- [F] 시작 목록: **`ms5-scratch/c11/work/starts_plan.txt`(209개, 줄마다 하나, SHA256 `fc698b8c548843031ec33c8de833e5b59265d8c369296d2caa35806f17066472`)**. 계획 목록 `ms5-scratch/obs3/plan3/starts_C-1.txt`(공백 구분, SHA256 `76035cb97e4f707ad24fc6976bbd560da783a3e45cda9148a6e0e5f32d820ad8` = 계획 표의 `76035cb97e4f707a`)와 집합이 같다. 실행부의 `case` label 209개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(작업자 확인: 실행부 case 집합 = 시작 목록, `make test`의 C11 시험이 시작 209개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/c11/`
  - `reobs/run.sh`(재관측 + obs3 `dleft.py` `runstops.py` + digest chain), `reobs/c11v1`(+ `.dleft` `.stops` `.chains` `.log`), `tools/static_c11.py` → `work/static_plan.txt`(범위 안 정적 decode: leader·출구·설치 값), `tools/refs_c11.py` → `work/refs_plan.out`(ROM 전체 C11 시작 참조), `tools/intargets.py` → `work/intargets_plan.out`(범위 안 비시작 PC로 오는 직접 분기), `tools/longrefs.py` → `work/longrefs_plan.out`(시작과 같은 ROM LONG), `tools/flagscan.py` → `work/flagscan_plan.txt`(block 경계를 넘는 flag), `tools/exitflags.py` → `work/exitflags_plan.txt`(출구 대상이 앞 코드의 flag를 읽는지), `tools/blocks_c11.py` → `work/blocks_plan.txt`(block별 역어셈블), `tools/newvis_c11.py` → `work/newvis_c11v1.txt`(숨은 직선 PC), `tools/c11exec.py` → `work/c11exec_base.txt`(관측의 C11 실행 PC·run·frame), `tools/natscan_c11.py` → `work/natscan_c11.out` `work/natural_c11.json`(V1 natural frame), `tools/c11refs_repo.py` → `work/c11refs_repo.out`(저장소의 C11 범위 literal), `tools/v1dbg.py` `tools/v1blocks.py` `tools/pc6dbg.py`(V1 world 진단), `work/run_tests.sh`, `work/v1_regs.sh`, `tools/legacy_one.py`(legacy 검증기 하나를 clone root에서 실행), `io_ext2_c11/`(세 번째 관측 IO 비교), `mut/`(변이), `realrom/`(실제 ROM 차분), `qwen/`(local Qwen 초안과 대조), `trial_logs/`(작업자 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위(결정 1)

- [F] **기준선**(현재 `main` routing, 세 번째 관측): 예측 일치 frame **6,638**(실측 5,681: P2 carry 결함 957 frame, 계획 §11.6), 첫 정지 `M2.0` `M4.0` 190 / 192 `1d3e0`, `M1.5` 190 `1e8de`, `M3.1` 225 D, `G1.94` 768 / `G1.68` 960 `4eb6a`.
- [F] **정적 decode**(`tools/static_c11.py`, `work/static_plan.txt`): 30 범위의 명령 490개는 모두 범위 안에서 끝난다(범위 끝이 명령 경계). 범위 안 leader(범위 시작, 조건 분기 대상·fall-through, BRA·JSR·BSR 대상과 복귀 PC, `MOVE.L #v,(A6)`·`MOVE.L #v,84(A6)` 값)는 계획 시작 207개와 같고, 나머지 둘은 범위 밖에서 들어오는 진입이다: `1cb76` ← `1cb6e BRA.W 1cb76`(routing 밖, 계획 루트 `1cb6a`), `1e918` ← C6 `1e8d4 MOVE.L #1e918,(A6)`, `1e9c8 LEA 1e918(PC)`, C10 `2043e`의 ROM LONG 표 `20444`(칸 4) 그리고 `20408`의 이웃 표(`work/refs_plan.out`, `work/longrefs_plan.out`). DBRA·TRAP·계산 표 점프는 없다.
- [F] **범위 밖에서 범위 안 비시작 PC로 오는 직접 분기**: 없다(`work/intargets_plan.out`의 두 줄 `4ed68 bcc.b 4ed00`, `e3808 bvs.w e8c6b`는 명령 경계가 아닌 operand를 명령으로 읽은 것: `4ed00`은 `4ecfe MOVE.W 7c(A6),D0`의 operand, `e8c6b`는 홀수).
- [F] **정확 bitmap 재관측(C11 가상 routing)** `reobs/c11v1`: 예측 일치 frame **6,664**(계획 예측과 같음), 실행된 routing 밖 PC C 372 / D 1,954 / E 2. digest chain은 계획 재관측 `obs3/reobs/v2_1`과 11 run 모두 같다(`reobs/c11v1.chains`). 첫 정지는 `M1.5` 190 D(`4c2c4`), `M2.0` 215 C(`1d776`, C-2), `M3.1` 225 D(`4fdfc` 계열), `M4.0` 193 D(`40896` 계열), `G1.94` 768 / `G1.68` 960 D/E(`ca5c`(E-1) `b3dfc`), `D2` 553 D, `D1` `P0` `P1` `X1`은 끝까지다(`reobs/c11v1.stops`).
  - [F] **숨은 직선 연속 검사**: 기준 관측(`obs3/final`)에 없고 `c11v1`에만 보이는 routing 밖 PC는 **없다**(`work/newvis_c11v1.txt`: 11 run 모두 0). C11 범위 끝 가운데 실행되는 것(`1d438` `1d776` `1e648` `1e71e` `1e96c` `2196c` `21a90` `21aa2` `4ebfc`, 그리고 `2196c JMP (A1)`의 handler `2197e`)은 기준 관측에도 이미 기록된 뒤 단위 정지다.
  - [F] 범위 보정은 **없다**: 계획 30 범위·209 시작을 그대로 쓴다.
- [F] **IO 실행**(`obs3/final`, `work/c11exec_base.txt`): C11 시작 가운데 실행된 것 130개, 실행 70,879회(TB 첫 routing 밖 PC 기록 수; 계획 표의 71,209는 closure 진입으로 줄인 실행 PC 단위의 셈), run 6개(`M1.5` `M2.0` `M3.1` `M4.0` × case 94, `G1.94`, `G1.68`). 실행되지 않은 시작 79개(`ca64` `ca6a` `1cb9e` `1d508` `1d5c4`.. `1d618`, `1d722` `1d742`, `1d8e2`..`1d906`, `1d9cc` `1da4a`, `1db28`..`1dbb6`, `1ddd8`..`1ddfa`, `1e5f0` `1e5fc` `1e600` `1e606`, `1e72e` `1e73e`, `21a82`, `4a91e` `4a92c` `4a93c`, `4d1a6`, `4eb88`..`4eba4`, `4ec4a`..`4ed22` 가운데 15개, `e8ca2`)는 closure로 들어왔다.
- [F] **계획 결정 5(E-1의 `ca5c..ca64`를 C-1에 붙임)**: 이 작업은 계획 행의 209 block을 그대로 구현했고 `ca5c`는 뒤 단위(E-1) 정지로 둔다(결정 1). 붙이면 `G1.94` `G1.68`의 첫 정지가 `ca5c`에서 `b3dfc`(D)로 옮겨 갈 것으로 보인다 [I].

## C11 상세 명세(계획 §11.8과 같은 꼴)

### 범위

- [F] **209 block, 490 명령, 2,040 byte, 30 범위**(시작 목록 SHA256 `fc698b8c…`(줄 구분) / `76035cb9…`(계획 공백 구분), 범위 byte를 이어 붙인 SHA256 `e8307952f9c847dcab6370c1a7d29556c78cd7f782f8e6a107302690042b44a4`). 짝수 PC 1,020(내부 811). 기존 routing과 겹침 0(각 범위 안 짝수 PC 전수 검사: 1,020개 모두 `animation_player_c11_block`).

| 범위(CPU = 파일 오프셋) | byte | 시작 | SHA256(앞 16자) | 내용 [I] |
| --- | --- | --- | --- | --- |
| `ca64..ca70` | 12 | 2 | `fa5007c71ca6b47e` | continue count WORD `10095c`: `CLR.W -76a4(A5); RTS`, `CLR.B -76a3(A5); RTS` |
| `1a952..1a966` | 20 | 1 | `d2b34b9ac064750c` | `ANDI.W #3,D0`; BYTE `53cc(A5)` := (BYTE & `fc`) \| D0.B; RTS |
| `1cb72..1cbb2` | 64 | 4 | `764c126b3f98e00e` | A1 := A6 + `94` → `1cb76`: 기록 BYTE 4 → ROM BYTE 표 `1c1c4` → 호출자 A0의 WORD → LONG `22(A6)` 표의 LONG(0이면 `1cafe`) → `EXG`, `JMP 49f96` |
| `1d3e0..1d438` | 88 | 11 | `729675408a4515c5` | C6 `1d3d8`의 fall-through: D7.W `f` `10` `c` `d` `11` `19` `1a` `1b` `18` `14` `16` 비교 사슬(나머지 → `1d438`) |
| `1d508..1d510` | 8 | 1 | `89553e8ab8c320d6` | `LEA 1d4b8(PC),A0; BRA.W 1d514`(C6) |
| `1d5c4..1d5e2` | 30 | 4 | `64d9da70663a89d0` | `49c38`(C) → `49c20`(A0 `1d5e2`) → RTS |
| `1d5fc..1d61a` | 30 | 4 | `64d9da70663a89d0` | 같은 꼴(A0 `1d61a`) |
| `1d722..1d776` | 84 | 10 | `7a0815a09a413f13` | 형식 14: A5 WORD 차이 → `43e08` → `1dbf0`; 형식 16: `48296`, `1a952`, 설치 `1d75a`(곧바로) → `49bca` `ea626` `4836e`의 C |
| `1d8e2..1d90a` | 40 | 8 | `f2b36729c14ae784` | 형식 c / d: `1d582`, `48210`의 D1.W, `1d510`의 C → `1dbc6` / `1ddfc` |
| `1d9b2..1da60` | 174 | 12 | `1b6d9aee40ef0fc4` | 형식 19: `4d196`, WORD `ae` 계산(WORD `78`이면 `ffb8`), `481de` `481b2`, 2986 자식 `3fedc`, `49260`, `49c20`(A0 `1da60`), `43e08` → `1ddc8` |
| `1db28..1dbc6` | 158 | 17 | `44103f30e0f4d013` | 형식 10: `1d698`, `43e08` → `1d90a`; 형식 11: BYTE `81`/`82` := `ff`, `48210`, D1.B = 9면 WORD `88` := 6(+4) 설치 `1db7c`(곧바로) → `SUBQ.W` 빌림 → `1d5c4` `1d5fc` `48210` `1d508`의 C → `1d1d0` → `1fae8` |
| `1ddd8..1ddfc` | 36 | 5 | `cb62144b5b845fe9` | 형식 18: `1d5fc`, WORD `b0` := `14`, 설치 `1dde8`(곧바로) → `49bca` → `SUBQ.W` 빌림 → `1ddfc` |
| `1e5aa..1e60a` | 96 | 10 | `73c6914fc6aae7d8` | `49bf2`의 D1.W ≥ 0이면 MULS 2(ROM WORD 표 `4419e` / `4411e`) → LONG `36`/`3a`, `4c2c4`의 C(D-1) → `NEG.W` / `SUBI.W` 부호로 WORD `3a` 보정 또는 D7 := −1 |
| `1e640..1e648` | 8 | 1 | `37e1a4fdf46bb34f` | `BTST #6,D0; BEQ.W 1e65a`(나머지 → `1e648`, C-2) |
| `1e65a..1e65c` | 2 | 1 | `1ceeabf0c6a5a30b` | RTS |
| `1e67a..1e71e` | 164 | 11 | `23870d1071949484` | 28ae 자식 `1e67a`: WORD `20` := `ca`, LONG `22` := bank 창 LONG `200088`, `49290`, BYTE `15` bit 6 := 1, `8ebe`, `49f8c`(A1 `6f1e2`), 설치 `1e6c0`(곧바로) → 부모의 WORD 78 → `49be0` → WORD (A0) bit 3의 변화(SNE / EOR.B)로 `49f8c`(A1 `6f21a` / `6f1e2`) → 부모 BYTE `9e` = 3 |
| `1e724..1e776` | 82 | 7 | `8c197ec8ab6b98cf` | 부모 BYTE `a7` bit 7 / 6 → `JMP 2a00`; 아니면 ROM WORD 표 `1e776` / `1e77c`(부모 BYTE `7c`, WORD `76`)로 WORD `1e` / `32`, `43e34` `49fc6`, RTS |
| `1e8de..1e96c` | 142 | 15 | `b8acd5e37aa76511` | C2 `1de34 BNE`: BYTE `a7` bit 2 := 1, 28ae 자식 `1e67a`, 칸 `84` := `21602`, 초기화 → `1e918`(LEA `1bcce`, `1cb38`) → 설치 `1e92c`(곧바로) → `1cd98`, BYTE `a7` bit 3, `1e5aa`의 D7.W ≥ `18` → `1e60a` `1e640` `4be82` `1e65c` `ce02` `49fc6` → `201a2` |
| `21950..2196c` | 28 | 4 | `d1bcb9895706c32e` | C3 `21620` 목록의 handler: `1cb72`(A0 `1bcde`), 칸 `84` := `21960` → `21960`: 목록 `21930`의 `215e6` → C에 따라 `2196e` / `2196c`(C-4 `JMP (A1)`) |
| `2196e..2197e` | 16 | 3 | `1bf5762e33a39b7c` | `1cd98`, D0 bit 4 → `21a42` / `2156a` |
| `21a42..21a90` | 78 | 7 | `ca937aa20ef95058` | BYTE `a7` bit 5 := 0, ROM LONG 표 `219f6`(기록 BYTE 4) → `1cb72`, BYTE `a5`/`a6` &= `ef`, BYTE `7e` := 0, 칸 `84` := `21a76` → `21a76`: 목록 `216c8`의 `215e6` → `JMP (A1)` `21a82` / `1cd98`, BYTE `7e` |
| `21a98..21aa2` | 10 | 2 | `2d2d8bde04b1e4cd` | `2156a`, `TST.W D7` |
| `21aaa..21aac` | 2 | 1 | `1ceeabf0c6a5a30b` | RTS |
| `3fedc..3fefc` | 32 | 3 | `53273f3f01b45835` | 2986 자식 `3fedc`: `4c0ac`, WORD `76` 보관·0, `40a5a`(D-1), WORD `8a` := 보관 값, 설치 `3ff14`(쓰기만), RTS |
| `49bf2..49c00` | 14 | 1 | `503943d20a26b6a3` | D1.W := ROM WORD 표 `49c00`(D0 & `f`) |
| `4a90e..4a944` | 54 | 7 | `b9abac834df6d0d3` | credit BYTE: home(`7d82(A5)` = 0) A1 = `100004`, MVS A1 = `d00034` 또는 `7e00(A5)`; `-7ffd(A5)`가 0이면 player 0 |
| `4d196..4d1ac` | 22 | 4 | `e2c03d8b7fd7ca5d` | WORD `78`로 A4 := `5cba(A5)` / `5ce6(A5)`; `BRA.B 4d17c` |
| `4eb6a..4ebfc` | 146 | 18 | `8cb4a126506a5b8c` | continue 진입: BYTE `5d21(A5)` / `7d82(A5)`, `4a974`의 Z, `4a9ca`의 D7.B → `ca5c` / `ca64` → `4ed3c`; `4e4da`, `e8c3a`, `ca5c`, `4a90e` → BYTE `a2`, `b0c`(D1 2), BYTE `9c` := 3, 설치 `4ebe2`(곧바로) → BYTE `7db6(A5)` + player가 3 → `4ed3c`, 1 → `4ebfc`(C-3), 나머지 → `4ec32` |
| `4ec32..4ed3c` | 266 | 28 | `1f1551081f74777f` | credit 변화(BLS) → `ca5c`, `5d21`이면 `b0c`(D1 3), `ca70`(A0 `10095c`): WORD 0 → `b0c`(D1 3), < `800` → `104ca8`/`104cae`의 BYTE 3 bit 5 → `ca6a`; `BTST D0,7004(A5)` → `SEQ.B a1`, HUD 문자열 `4e382`/`4e34c` → `4e564`, `~a1 & 5d1f` → `ca70` + ROM WORD 표 `4e396` → `35f0` / `ca5c`, BYTE `9a` := BYTE `5d1f(A5)`, RTS |
| `e8c3a..e8cc0` | 134 | 7 | `1a277b24330290d2` | 등장 보조: D0.W 보관, `e8ad0`, ROM BYTE 표 `e8c22`(기록 BYTE 3) → D2.B, WORD 7개 쌓기, 2986 자식 `b3dfc` → `MOVEM.W (A7)+,D0-D6`, C Set이면 자식 WORD `76`..`7e` := D2..D6, `49214` → 보관 값 꺼냄, A6 := 자식, `e8b6e`, A6 복원, RTS |

- [F] **진입**(현재 routing 기준 호출자, `work/refs_plan.out` `work/longrefs_plan.out`):
  - 다른 실행부의 분기·fall-through: `1d3e0` ← C6 `1d3d8 BEQ`의 fall-through(C1 미룬 입구), `4eb6a` ← C6 `4eb60 BEQ`의 fall-through(C1 미룬 입구), `1e8de` ← C2 `1de34 BNE`.
  - 계산 점프 착지: `21950` ← C3 `21620 JMP (A1)`(목록 `21622`의 칸 8), 칸 `84` 값 `21960` `21a76` ← C3 `201a6 JSR (A4)`(C3 허용 목록 `PC3_SLOT84`에 이미 있다).
  - 설치 값(다른 실행부가 씀): `1e918` ← C6 `1e8d4`(쓰기만), C10 `2043e`(ROM LONG 표 `20444` 칸 4).
  - 28ae / 2986 자식: `1e67a` ← C11 `1e8e4`, C6 `1e828`; `3fedc` ← C11 `1d9ee`.
  - routing 밖 호출자만 있는 subroutine(뒤 단위가 routing할 때 그 단위의 출구가 됨): `1cb72` ← `21730` `21764` `217ea` `21896` `21982` `2198e` `219cc`(BSR.W), `1cb76` ← `1cb6e BRA.W`, `1a952` ← `1d84e`, `4d196` ← `1d95a`, `49bf2` ← `1e02c`, `1e5aa` ← `1e996` `1e9f8` `1ea5a`, `1e640` ← `1e9a6` `1ea1a` `1ea66`.
  - C11 안의 호출: `1a952`(`1d74e`), `1cb72`(`21954` `21a5a`), `1d508`(`1db98`), `1d5c4`(`1db86`), `1d5fc`(`1db8a` `1ddd8`), `1e5aa`(`1e93a`), `1e640`(`1e94a`), `49bf2`(`1e5aa`), `4a90e`(`4ebc0` `4ec36`), `4d196`(`1d9b2`), `ca64`(`4eb9e`), `ca6a`(`4eca6`), `e8c3a`(`4ebb0`).
- [F] **설치 값**(`MOVE.L #v,(A6)`): 곧바로 들어감 `1d75a`(`1d754`) `1db7c`(`1db76`) `1dde8`(`1dddc`) `1e6c0`(`1e6b6`) `1e92c`(`1e920`) `4ebe2`(`4ebd6`). 쓰고 RTS `3ff14`(`3fef4`; routing 밖, 실행된 뒤 단위 callback).
- [F] **둘째 칸 `84(A6)` 값**: `21602`(`1e8f4`, C3), `21960`(`21958`, 곧바로), `21a76`(`21a6e`, 곧바로).
- [F] **자식**(`MOVEA.L #v,A0` 뒤 `JSR 28ae`/`2986`): `1e67a`(`1e8e4`, C11), `3fedc`(`1d9ee`, C11), `b3dfc`(`e8c66`; routing 밖, 자식 node의 callback으로 쓰기만 한다 — 같은 run에서 실행되지 않는다).

### 계산 점프와 고정 ROM 자료(결정 2)

- [F] **`JMP (A1)` `21a82`**(block `21a82`): `21a76 LEA 216c8(PC),A0; BSR.W 215e6; BCC.W 21a84` 뒤다. 목록 `216c8`은 ROM에서 (`21602`, 0), LONG 0 하나다. **허용 대상 = `21602`(C3)**. 그 밖의 A1(LONG 전체 비교; `1021602`는 거부)은 checked `unsupported animation player c11 jump target`이다(C9 `21d36`·C10 `2229a` `22378`과 같은 규칙).
- [F] `2196c JMP (A1)`(목록 `21930` = (`21602`, 0) (`2197e`, `a`), 0)은 C-4의 block이라 C11이 실행하지 않는다(`21968`의 C Set 쪽은 뒤 단위 정지).
- [F] TRAP·DIVU/DIVS·계산 표 점프는 없다. MULS 2(`1e5ca` `1e5d4`), MOVEM 1(`e8c7c MOVEM.W (A7)+,D0-D6`).
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙. [F] 원본 값은 ROM 바이트):
  - BYTE 표 `1c1c4`(`1cb76`; 첨자 = 기록 BYTE 4, `MOVEQ #0` 뒤라 0..`ff`, 부호 확장 WORD), WORD 표 `4419e` / `4411e`(`1e5ba`; 첨자 = 2 × `49bf2`의 D1.W, 부호 확장), WORD 표 `1e776`(첨자 2 × 부모 BYTE `7c`) / `1e77c`(첨자 2 × (4 × BYTE `7c` + WORD `76`), WORD 덧셈), LONG 표 `219f6`(`21a42`; 4 × 기록 BYTE 4; ROM의 19 LONG은 기록 포인터 `1bcee`..`1bcfa`), WORD 표 `49c00`(16 WORD; 첨자 2 × (D0 & `f`)라 표 안), WORD 표 `4e396`(`4ecec`; 2 × BYTE (A0)), BYTE 표 `e8c22`(`e8c40`; 기록 BYTE 3; ROM 표는 24 BYTE이고 그 뒤는 코드 `e8c3a`), bank 창 LONG `200088`(`1e67a`; FR8 / C10 `24ecc`와 같은 꼴), 호출자 A0의 WORD 기록(`1cb8a`: `21950`이 넘기는 `1bcde`, `21a42`가 `219f6`에서 읽은 `1bcee`..).
  - 넘기기만 하는 포인터(`LEA d(PC)` / `MOVEA.L #`): `1d4b8` `1d5e2` `1d61a` `1da60` `1bcce` `1bcde` `21930` `216c8` `4e382` `4e34c` `6f1e2` `6f21a` `3fedc` `1e67a` `b3dfc` `100bf4` `104ca8` `104cae` `d00034`.

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작; `work/static_plan.txt`): `b0c` `28ae` `2986` `2a00` `35f0` `8ebe` `ca70` `ce02` `1cb38` `1cd98` `1d1d0` `1d510` `1d514` `1d582` `1d698` `1d90a` `1dbc6` `1ddc8` `1ddfc` `1e60a` `1e65c` `1fae8` `201a2` `2156a` `215e6` `43e08` `43e34` `481b2` `481de` `48210` `48296` `4836e` `49214` `49260` `49290` `49bca` `49be0` `49c20` `49c38` `49f8c` `49f96` `49fc6` `4a974` `4a9ca` `4be82` `4c0ac` `4d17c` `4e4da` `4e564` `4ed3c` `e8ad0` `e8b6e` `ea626`, 그리고 `JMP (A1)`의 handler `21602`.
- [F] **뒤 단위 정지**(C11 block이 분기·fall-through·호출로 닿는 routing 밖 PC, 15개): `ca5c`(E-1), `1d776` `1db0a` `1e648` `1e96c` `21a90` `21aa2`(C-2), `1d940` `4ebfc`(C-3), `1d438` `1dbf0` `1e71e` `2196c`(C-4), `40a5a` `4c2c4`(D-1). 모두 계획 §11.8.2의 목록과 같다. 출구 대상이 C11이 남긴 flag를 읽는 곳은 없다(`work/exitflags_plan.txt`: 68 대상 모두 "-").
- [F] V1·실제 ROM 차분의 선언 정지는 위 15개와 C1~C10의 남은 정지 9개(`1de3c` `1e21c` `1fc96` `1fd3c` `1fd50` `21ea0` `21fa6` `4e69a` `4ef08`; 앞 spec들의 `EXIT_STOPS` 합집합 가운데 아직 routing 밖인 것)다(모두 24개).
- [F] TRAP 없음. ROM·RAM 실행 없음. 장치 쓰기 없음. 장치 읽기 후보: `4a93e MOVE.B (A1,D0.W),D0`의 A1 = `d00034`(MVS, BYTE `7d82(A5)` ≠ 0이고 `7e80(A5)` = 0일 때) — C++ program bus는 `unsupported program bus device address`(checked)로 끝나고, native 모형도 장치 읽기라 V1 world가 없다(결정 6).

### block 경계·복귀를 넘는 flag(결정 3)

C10 방식대로 block 첫 명령부터 flag를 정하는 명령까지 훑었다(`work/flagscan_plan.txt`). 그리고 C11 출구 대상과 C11 RTS의 복귀 PC에서 C11이 남긴 flag를 읽는 곳을 따로 훑었다(`work/exitflags_plan.txt`, 호출자 목록). X를 읽는 명령은 없다.

- [F] **C 소비 block 9개**(Clear 쪽 / Set 쪽; Unknown C면 `player c11 caller requires known carry`): `1d5ce`·`1d606 BCS`(FR6 `49c38`: `TST.L` 뒤 `ANDI.B #fe,CCR` / `ORI.B #1,CCR`), `1d770 BCC`(C3 `4836e`), `1d8fa BCC`(C6 `1d510`), `1db9c BCS`(C11 `1d508` → C6 `1d514`; C6 RTS `1d51c` / `1d580`이 C를 넘김), `1e5ec BCC`(`4c2c4`, D-1: 아직 routing 밖이라 C++에서 실제 생산자로 닿지 않음), `21968`·`21a7e BCC`(C3 `215e6`), `e8c7c MOVEM.W (A7)+,D0-D6; BCC`(C7 `2986`; MOVEM은 CCR을 바꾸지 않음, FR11 `b7d8c`와 같은 꼴). 생산자 쪽은 모두 기존 실행부가 known C를 돌려준다.
- [F] **C를 만들거나 넘기는 C11 block은 없다**(C11 block 뒤는 Unknown). 돌려주지만 읽는 쪽이 없는 flag: RTS `1a964`(`MOVE.B`) `1d5e0` `1d618`(호출자 `1db8a`·`1db8e`·`1dddc`는 `JSR`·`MOVE`로 시작) `1d774` `1db84` `1ddfa` `1e774` `21aaa`(node callback의 RTS 또는 C3 `201a6 JSR (A4)`의 복귀 `201a8 JSR`) `1e608`(복귀 `1e93e CMPI`, routing 밖 `1e99a` `1e9fc` `1ea5e`의 `CMPI`) `1e65a`(복귀 `1e94e JSR`와 routing 밖 `1e9aa` `1ea1e` `1ea6a JSR`) `49bfe`(`1e5b0 MOVEQ`, `1e032 MOVE`) `4a942`(`4ebc6`·`4ec3c MOVE`) `4ed3a` `3fefa` `e8cbe`(`4ebb6 JSR`) `ca68` `ca6e`(`4eba4 BRA` → C6, `4ecac MOVE`). `e8c9e ORI.B #1,CCR`의 C는 다음 `e8ca4 MOVE.W`가 지운다.
- [F] **Z가 경계를 넘는 곳 하나**: `4eb84 BNE.W 4eba8`, Z는 `4eb7e JSR 4a974`가 부른 C1 `4a974`의 마지막 `TST.B (A0); RTS`(`4a9b0` / `4a9c6`)의 것이다. **`4eb84`는 BYTE (A0)를 다시 읽어 Z를 정한다**: A0가 `10fdb0` `10fdb1` `100004` `100005`(LONG 비교) 가운데 하나여야 하고 RTS는 그 BYTE를 바꾸지 않는다. 그 밖의 A0는 checked `unsupported animation player c11 flag source`다(C4 `4e77a`·C6 `4ee30`과 같은 규칙).
- [F] 그 밖의 `Bcc`는 같은 block 안의 명령이 정한 flag를 읽는다: `CMPI.W #k,D7`(WORD, 형식 사슬), `TST.W D1`(`1d8f0`), `TST.W 78(A6)`, `CMPI.B #9,D1`(BYTE), `SUBQ.W #1`(`1db7c` `1ddf2`: 빌림 = WORD가 0이었음), `TST.W D1; BMI`(`1e5b0`), `SUBI.W #10,D0; BPL`(`1e5f0`: 결과 bit 15), `BTST #6,D0`, `EOR.B`(`1e6ce`: BYTE 결과), `TST.B D0`, `CMPI.B #3`, `BTST #7/#6,a7(A0)`, `BTST #3,a7(A6)`, `CMPI.W #18,D7; BCS`(무부호 WORD), `BTST #4,D0`, `TST.B 7e(A6)`, `TST.W D7`, `TST.B`(A5 BYTE들), `TST.B D7`, `CMPI.B #3 / #1,D0`(BYTE), `CMP.B D1,D0; BLS`(무부호 BYTE: D0.B ≤ D1.B), `MOVE.W (A0),D0; BNE`, `CMPI.W #800,D0; BCC`(무부호 WORD), `TST.W 76(A6)`, `BTST #5,3(A0)`, `CMP.B 9a(A6),D0`, `AND.B; BEQ`(BYTE), `CMPI.W #0,76(A6)`. flag를 공유하는 Bcc 묶음은 없다.

### 정수 연산(MULS·MOVEM·크기)

- [F] WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W d(An),Dn`, `SUB.W`, `ADD.W`, `ADDI.W`, `NEG.W`, `ANDI.W #3/#1`, `MOVE.B`(레지스터 BYTE), `ANDI.B`/`OR.B`/`EOR.B`/`NOT.B`/`AND.B`, `SNE.B D0`, `MOVE.W #k,Dn`). `MOVEQ`·`CLR.L`·`MOVE.L`·`MOVEA`·`LEA`·`EXG`는 LONG 전체(`MOVEA.W #0,A1`은 부호 확장으로 0). 표 첨자 `(An,Dn.W)` / `(PC,Dn.W)`와 `ADDA.W 76(A6),A0`, `-7ffc(A5)`·`-76a4(A5)`·`-7ffd(A5)`는 부호 확장한다.
- [F] `MULS.W (A0,D1.W),Dn`: Dn.L := Dn.W × WORD(A0 + sext(D1.W)), 둘 다 부호 있는 16 bit, 곱은 부호 있는 32 bit(범위 안이라 넘침 없음). C++는 `pc11_signed_word`로 부호를 정의된 방법으로 바꾸고 곱한 뒤 `static_cast<std::uint32_t>`로 쓴다(UB 없음).
- [F] `MOVEM.W (A7)+,D0-D6`: 낮은 주소의 WORD부터 D0..D6, 각 WORD를 LONG으로 부호 확장. 쌓은 순서(`#0` `#0` `#0` `#384` D2.W `#0` `#0`)로 D0 = 0, D1 = 0, D2 = sext(D2.W), D3 = `384`, D4..D6 = 0(스택 값이 그대로면).
- [F] `BTST D0,7004(A5)`(`4ecb0`, 메모리 operand): BYTE, bit = D0 mod 8(capstone의 `.l` 표기는 레지스터 operand 형식이 아니다). `SEQ.B a1(A6)`: bit가 0이면 `ff`.
- [F] `SUBQ.W #1,88(A6); BCS`: 원래 WORD가 0이면 빌림(새 값 `ffff`).

### IO 실행 run과 frame

- [F] 실행 run 6개(`obs3/final` 기준 C11 PC가 처음 기록된 frame의 처음 ~ 마지막): `M1.5` 94 190..991, `M2.0` 94 190..191, `M3.1` 94 248..300, `M4.0` 94 192..475, `G1.94` 768..2,064, `G1.68` 960..2,255. 플레이어 node는 `100cb8`이고, `1e67a`·`3fedc` 자식은 pool `100800..104c00`의 node다. continue callback `4ebe2`는 `G1.94` frame 769부터 697 frame, `G1.68` 961부터 560 frame 동안 node callback이다(`work/natscan_c11.out`).
- [F] **IO 예측(C11 연결)**: 6,638 → **6,664**(+26; 재관측 `reobs/c11v1`). P2 carry 결함(계획 §11.6, 결정 4)이 그대로면 실측은 5,681 → 5,707로 예상한다 [I]. 첫 정지는 위 "재확인과 범위"와 같다.
- [F] 원래 IO 관측과 확장 관측은 C11 코드를 실행하지 않는다(계획 §11.8.4). 일치 173,966과 14,500은 그대로여야 한다(작업자는 돌리지 않음; 메인 runner).

## 공통 규칙·native 검증 계획

FR2..FR14, C1~C10 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_player_c11.cpp`, 함수 `animation_player_c11_block`. 오류 문자열은 `unsupported animation player c11 PC`(범위 안 내부 PC 직접 진입), `player c11 caller requires known carry`(C 소비 block 9개에 Unknown C), `unsupported animation player c11 jump target`(결정 2의 목록 밖 A1), `unsupported animation player c11 flag source`(결정 3의 `4eb84` Z 출처) 네 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다(`unsupported program bus device address`: `d00034`).
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(30 범위, FR14 줄 뒤; `)ok=animation_player_c11_block(c);`를 같은 줄에 둔다), `carry_preserving_pc`의 FR14 묶음 뒤에 주석 달린 case 묶음 하나(소비자 9), `animation_machine_internal.h`에 선언 하나(FR14 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄 끝에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# player C11 refresh:` 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 곧바로 들어감 `1d75a` `1db7c` `1dde8` `1e6c0` `1e92c` `4ebe2`와 칸 `84` 값 `21960` `21a76`은 쓰고 그 값으로 들어가고, `3fef4`(`3ff14`)는 쓰고 RTS, `1e8f4`(칸 `84` `21602`)는 쓰고 다음 block으로 간다.
- **자료 읽기**(live bus): node field(A6), 부모 node(A0 = LONG `c(A6)`), 기록 A4 = LONG `8c(A6)`(BYTE 4), A0 기록(BYTE 3, WORD 0 / 2 / 4 / 6), A5 field, RAM 절대 주소(`10095c` `104cab` `104cb1` `100003`..`100005`), 고정 ROM(위 "계산 점프와 고정 ROM 자료"). 단위 시험은 고정 ROM·bank 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): BYTE 표 `1c1c4`(32), WORD 기록 `1bcde`(16), LONG 표 `1d468` / `1d4b8`(C6 `1d510` / `1d514` 사슬; RAM 포인터와 0), WORD 표 `1e776..1e796`(16), 목록 `216c8` = (`21602`, 2), 0과 `21930` = (`21602`, 3) (`2197e`, 5), 0(handler는 ROM과 같고 key가 다름; C3 `215e6` 사슬), LONG 표 `219f6`(19, RAM 기록 포인터), WORD 표 `4411e..4421e`(128; MULS), WORD 표 `49c00`(16), `4e396`(16), BYTE 표 `e8c22`(24), bank 창 LONG `200088` = `00fedcba`. V1·실제 ROM 차분은 원본 ROM을 읽는다.

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `1feb63c9de015b8ceb3ecc56ae51b31cba1bf0a17a726216db249697e718db2f` → `4354bc8da2843db148b0fe64e2782469a26cbaa1774626f3d33a664710a67340`, `animation_machine_internal.h` `1d4a08c30c9e9e9dbfeb4dd8b8fea3e5dad8b8f2640e1df430dd3b5310f0d3f3` → `212ee22039dc709d3277956623cc87130a98fa0a7d752cc7a946ebf3cb6efd4e`(옛 값은 `# player C11 refresh:` 주석).
- [F] **C6 시험 생성기·시험**(오류 행 둘; 이전 = 그 PC에서 `unsupported animation machine PC`. C11이 그 PC를 routing해서 C++가 C11 코드를 실행하므로 바뀜):
  - `error-1d398-then-1d3e0`(D7 = 0, 실패 PC `1d3e0`) → `error-1d398-then-1d722`: D7.W = `14`, A5 홀수. `1d398`..`1d3d8`(C6)와 `1d3e0`..`1d428`(C11)의 비교는 메모리에 접근하지 않으므로 C11 `1d722 MOVE.W 547a(A5),D0`이 `program bus requires even WORD/LONG address`로 실패한다(실패 PC가 경로를 따라 옮겨 감; C10의 `21dd0` → `1cac2`와 같은 처리).
  - `error-4eb58-then-4eb6a` → `error-4eb58-then-4eb7a`: A6 홀수, BYTE `10fd8a` = 1. `4eb58`(`MOVE.B 98(A6),D0`) / `4e5b0` / `4eb60` / C11 `4eb6a` `4eb72`은 BYTE만 읽으므로 C11 `4eb7a MOVE.W 76(A6),D0`이 실패한다.
  - 생성기를 다시 돌려 그 두 행만 바뀜을 확인했다(`work/before/` 대비 diff 2행). C6 시험 줄의 fixture 수는 그대로다(1,248).
- [F] **V1 spec**:
  - `ROUTED_LATER`(C2~C10이 쓴 방식): `EXIT_STOPS`에 C11 진입이 있는 spec에 그 진입을 더했다 — pc2 pc3 pc4 pc5: `1e8de`; pc6 pc7 pc8 pc9 pc10 fr10 fr11 fr12 fr13 fr14 se2: `1d3e0` `4eb6a` `1e8de`. 그 run은 그 PC에서 계속 멈춘다.
  - C3 계산 점프로 C11 진입에 닿는 run이 있는 spec(pc4 pc5 pc6 pc7 pc8 pc9 pc10 fr10 fr11 fr12 fr13 fr14 se2): `EXIT_STOPS`와 `ROUTED_LATER`에 C3 목록 handler `21950`과 칸 `84` 값 `21960` `21a76`을 더했다(이전에는 routing 밖이라 `first_unrouted`가 그 착지에서 멈췄다). [F] 이 처리 없이 pc6를 돌리면 reinstall world (`P1` 94 frame 458, node `100cb8`, `1e89e`)의 native run이 C3 `21620 JMP (A1)` → C11 `21950`..`2197a` → C3 `2156a` → `202ba SUBQ.W #1,8(A4)`(A4 = 고정 ROM 기록)까지 가서 쓰기 보호된 ROM에 쓰다 멈춘다(`tools/pc6dbg.py`).
  - pc3: 계산 점프 대상(slot-84 값·목록)의 소유자 확인에 `animation_player_c11_block`을 허용했다.
  - pc6: 오류 fixture `1d398-then-1d3e0` → `1d398-then-1d722`(D7.W = `14`, A5 홀수), `4eb58-then-4eb6a` → `4eb58-then-4eb7a`(A6 홀수, BYTE `10dd21` = BYTE `10fd82` = 0) — C6 생성기와 같은 방식.
  - V1 회귀(작업자, 아래 "검증 수치")는 모두 FR14 기록과 같은 fixture 수로 통과했다.
- [F] **legacy 입력 검증기 `tools/verify_animation_machine_input.py`**: 옛 "outside PC" 목록의 `1d5c4` `1d5fc`(이전 기대 `unsupported animation machine PC`)는 이제 C11 시작이다. 그 고정 입력의 직접 진입은 C11 `1d5c4`/`1d5fc` → `49c38` → 소비자 → RTS로 `ff000`에 성공하므로(작업자 실행), FR6·C1·C3·C6이 쓴 방식대로 `SUPERSEDED_OUTSIDE`에 `area C C11 (player_c11)`로 넣었다(옛 기대값은 그 행의 `former_expected_API_error`로 남는다). 이 검증기는 종료 0이다(아래 "검증 수치").
- [F] 바뀌지 않음(확인, `work/c11refs_repo.out`): C2 시험(`1ddd8` `1e8de`는 정지·값), C3 시험(`21950` `21960` `21a76`은 목록·칸 값), C10 시험(`1e8de`는 쓰기 값), stage_area 시험·검증기(`4d196`은 이웃 범위 끝), stage_event 시험·검증기(`1a952`는 이웃 범위 끝), objects u06 시험(`49bf2`는 값), input 시험(`1d5c4` `1d5fc`는 이웃 범위 끝), objects u11 / n04 / n20 / n34 / fr1b / fr2b / motion walk / c8 / stage_event_ops 시험의 C11 범위 literal은 레지스터·자료 값이다. 작업자가 C++ 시험 300개를 모두 다시 돌려 C6 시험만 실패했다(위에서 고침; `trial_logs/regress1.log`).
- [I] 원래 IO 관측과 frame 비교(d1·controller·irq·demo)는 C11 코드를 실행하지 않으므로 결과가 같아야 한다. 메인 runner가 확인한다.

## 결정

1. **범위: 209 block, 30 범위(계획 그대로).** 정적 decode의 leader 207개 + 범위 밖 진입 `1cb76` `1e918`. 숨은 직선 block은 없다(가상 routing 재관측에서 새로 보인 PC 0). 예측 6,664(+26). E-1 `ca5c`는 붙이지 않았다(계획 결정 5는 메인 결정).
2. **계산 점프**: `JMP (A1)` `21a82`는 목록 `216c8`의 handler `21602`면 그 PC로, 그 밖은 checked 오류(LONG 비교). 고정 ROM 표(`1c1c4` `4411e` `4419e` `1e776` `1e77c` `219f6` `49c00` `4e396` `e8c22`)와 bank 창 LONG `200088`은 live bus로 읽고 상한을 검사하지 않는다.
3. **flag.** C 소비자 9개는 known C를 읽거나 checked 오류. C11 block은 C를 만들거나 넘기지 않는다. Z 읽는 곳 `4eb84`는 BYTE (A0)를 다시 읽는다(A0는 `4a974`의 네 BYTE 가운데 하나, 아니면 checked flag-source 오류).
4. **V1 natural family.** 세 번째 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT2`)이 읽는다. 위치는 환경 변수 `MS5_IO_EXT2` → `artifacts/animation_machine_io_ext2`(있으면) → `ms5-scratch/obs3/final` 순이고, `observation.json`의 compared_sha256 `d30e68d6…`를 build에서 확인한다(위치가 달라도 같은 상태). 계획 결정 1로 공유 artifacts에 옮기면 spec을 고치지 않아도 그쪽을 쓴다. node area `100800..104c00`의 node가 C11 callback(`1e67a` `1e6c0` `3fedc` `1d75a` `1db7c` `1dde8` `1e92c` `4ebe2` `1e918`)을 가졌거나, 플레이어 node(`100cb8` `100da8`)가 칸 `84` `21960` `21a76`을 가졌거나, 관측이 C11 시작을 처음 기록한 frame의 플레이어 node(routing된 callback)인 frame 36개(`work/natural_c11.json`: run과 key마다 처음·가운데·마지막 frame)에서 C11 시작에 닿는 run을 쓴다(38 fixture).
5. **앞 단위 spec.** pc2~pc10·fr10~fr14·se2의 `EXIT_STOPS`·`ROUTED_LATER`에 C11 진입을 두어 그 run은 계속 그 PC에서 멈춘다. C3 계산 점프의 C11 착지(`21950` `21960` `21a76`)도 선언 정지로 더한다. 오류 fixture는 실패 PC를 경로를 따라 옮긴다(위).
6. **V1이 닿지 않는 결과(선언 상태로만 확인).** `1e5ec`의 두 결과(`LATER_GATED`: 생산자 `4c2c4`가 D-1, routing 밖), `4a91e → 4a930`(MVS `d00034` 읽기: native 모형의 장치 읽기)과 `e8c7c → e8ca2`(2986 실패: C++ 2986 실행부가 `e8a84` 밖 호출자에 `cue wrapper failure requires known caller X`, C7 결정 6)는 V1 spec의 `MODEL_GATED`로 적었다. 단위 시험은 선언 C·선언 상태로 셋 모두를 확인한다.
7. **다음.** C11 연결로 세 번째 관측 IO 예측 6,664(+26)를 메인 runner가 확인한다(P2 carry 결함이 그대로면 실측 5,707 예상). 계획 순서의 다음 단위는 D-1(FR15; 첫 정지 `4c2c4` `40896` `4fdfc` 계열), E-1(`ca5c`).

## 미확인

- [U] node field·전역 값의 의미(BYTE `7e` `9a` `9c` `a1` `a2` `a5` `a6` `a7` `81` `82` `88`, WORD `76` `78` `88` `b0` `ae` `42` `46` `32` `1e` `7c` `8a`, A5 `53cc` `547a` `547c` `538e` `5392` `53a2` `5d1f` `5d21` `7004` `7db6` `7d82` `7e80`, ROM 표 `1c1c4` `4411e` `4419e` `1e776` `1e77c` `219f6` `49c00` `4e396` `e8c22`). 이름(등장 방식 형식, 속도 보조, continue, credit, HUD 문자열)은 동작에서 붙인 [I]이다.
- [U] `1e5ec`의 두 결과는 생산자 `4c2c4`(D-1)가 routing되기 전까지 선언 C로만 확인했다.
- [U] `e8c7c`의 Clear 쪽(`e8ca2`: 2986 실패)은 실제 2986으로는 C++에서 닿지 않는다(C7 결정 6). 선언 C로만 확인했다.
- [U] MVS 경로 `4a91e → 4a930 → 4a93e`(`d00034`)는 실제 기계에서 backup RAM을 읽는다. C++ program bus는 그 영역을 장치 주소로 거부한다(checked).
- [U] IO 관측에서 실행되지 않은 이 단위의 block 79개(위 "재확인과 범위")는 closure로 들어왔다(V1 선언 상태·natural·실제 ROM 차분·단위 시험으로만 확인).
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC), P2 carry 결함(계획 §11.6)과의 관계.
- [U] natural fixture의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C10과 같음).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_player_c11.cpp`(case label 209 = 시작 목록과 집합 일치; 공용 함수 `pc11_get` `pc11_put` `pc11_bit` `pc11_field_bit` `pc11_zero` `pc11_type` `pc11_carry` `pc11_field_call` `pc11_b0c` `pc11_install` `pc11_count_down` `pc11_input_slot` `pc11_signed_word` `pc11_muls` `pc11_flag_4a974` `pc11_list_jump`), `engine/tests/animation_machine_player_c11_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_g`), `tools/generate_animation_machine_player_c11_test_table.py`(생성기; C10 생성기 꼴, single 5 = Z 읽는 `4eb84`(native SR Z = BYTE (A0) = 0, A0는 네 BYTE), 계산 점프 착지 검사 `JUMP_ALLOWED` = 목록 `216c8`, V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면, 또는 사슬 run이 `290e`(28ae 실패)를 지나면 그 run을 버림; 약 80초), `tools/unit_fixture_specs/pc11.py`(V1 spec; C10 spec의 공용 부분 그대로, 단위 부분 교체, `EXIT_STOPS`(24), `CONSUMERS`(9), `Z_READERS`(`4eb84`), `LATER_GATED`(`1e5ec` 두 결과), `MODEL_GATED`(`4a91e → 4a930`, `e8c7c → e8ca2`), natural family는 세 번째 관측 pack). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `work/starts_plan.txt`(SHA256 `fc698b8c…`). 이 목록은 local Qwen이 범위별 JSON에서 초안을 썼고, 작업자가 스크립트로 만든 같은 목록과 줄 단위로 대조했다(30줄 모두 같음, `qwen/blocks_out.md`).

- **`ca64..ca70`(2)**: `ca64 ca6a`
- **`1a952..1a966`(1)**: `1a952`
- **`1cb72..1cbb2`(4)**: `1cb72 1cb76 1cb9e 1cba4`
- **`1d3e0..1d438`(11)**: `1d3e0 1d3e8 1d3f0 1d3f8 1d400 1d408 1d410 1d418 1d420 1d428 1d430`
- **`1d508..1d510`(1)**: `1d508`
- **`1d5c4..1d5e2`(4)**: `1d5c4 1d5ce 1d5d2 1d5e0`
- **`1d5fc..1d61a`(4)**: `1d5fc 1d606 1d60a 1d618`
- **`1d722..1d776`(10)**: `1d722 1d742 1d746 1d74c 1d754 1d75a 1d764 1d76a 1d770 1d774`
- **`1d8e2..1d90a`(8)**: `1d8e2 1d8e6 1d8f0 1d8f6 1d8fa 1d8fe 1d902 1d906`
- **`1d9b2..1da60`(12)**: `1d9b2 1d9b8 1d9cc 1d9d8 1d9e4 1d9ee 1da04 1da18 1da38 1da4a 1da4e 1da5c`
- **`1db28..1dbc6`(17)**: `1db28 1db2c 1db42 1db46 1db5c 1db64 1db72 1db76 1db7c 1db84 1db86 1db8a 1db8e 1db98 1db9c 1dba0 1dbb6`
- **`1ddd8..1ddfc`(5)**: `1ddd8 1dddc 1dde8 1ddf2 1ddfa`
- **`1e5aa..1e60a`(10)**: `1e5aa 1e5b0 1e5ba 1e5d8 1e5ec 1e5f0 1e5fc 1e600 1e604 1e606`
- **`1e640..1e648`(1)**: `1e640`
- **`1e65a..1e65c`(1)**: `1e65a`
- **`1e67a..1e71e`(11)**: `1e67a 1e692 1e6a6 1e6b6 1e6c0 1e6ce 1e6e4 1e6ea 1e6fa 1e6fe 1e70e`
- **`1e724..1e776`(7)**: `1e724 1e72e 1e734 1e73e 1e744 1e76e 1e774`
- **`1e8de..1e96c`(15)**: `1e8de 1e8f4 1e918 1e920 1e92c 1e930 1e93a 1e93e 1e946 1e94a 1e94e 1e954 1e958 1e962 1e968`
- **`21950..2196c`(4)**: `21950 21958 21960 21968`
- **`2196e..2197e`(3)**: `2196e 21972 2197a`
- **`21a42..21a90`(7)**: `21a42 21a5e 21a76 21a7e 21a82 21a84 21a88`
- **`21a98..21aa2`(2)**: `21a98 21a9c`
- **`21aaa..21aac`(1)**: `21aaa`
- **`3fedc..3fefc`(3)**: `3fedc 3fee2 3feee`
- **`49bf2..49c00`(1)**: `49bf2`
- **`4a90e..4a944`(7)**: `4a90e 4a916 4a91e 4a92c 4a930 4a93c 4a93e`
- **`4d196..4d1ac`(4)**: `4d196 4d19e 4d1a6 4d1aa`
- **`4eb6a..4ebfc`(18)**: `4eb6a 4eb72 4eb7a 4eb84 4eb88 4eb8e 4eb94 4eb9a 4eb9e 4eba4 4eba8 4ebac 4ebb6 4ebbc 4ebc6 4ebd6 4ebe2 4ebf4`
- **`4ec32..4ed3c`(28)**: `4ec32 4ec3c 4ec4a 4ec50 4ec58 4ec64 4ec6a 4ec70 4ec7c 4ec80 4ec88 4ec96 4ec9c 4eca6 4ecac 4ecc4 4ecd0 4ecd4 4ecd8 4ece6 4ecec 4ed0c 4ed14 4ed18 4ed22 4ed26 4ed2e 4ed34`
- **`e8c3a..e8cc0`(7)**: `e8c3a e8c40 e8c7c e8c84 e8c9e e8ca2 e8cbc`

## 검증 수치

작업자 실행(메인의 결정적 runner가 전체 검증을 다시 한다). 이 절의 초안은 local Qwen이 수치 JSON(`qwen/record_in.json`)에서 썼고 작업자가 고쳤다(관측 이름, 영어 그대로 남긴 문구, 잘린 끝).

- [F] `make -j4 all test`(최종 실행부·시험): 종료 0, 경고 0, Assert 0, Python 310 OK(`trial_logs/make_final.log`). C11 시험 줄: `animation machine player pc11: 1107 fixtures (689 single-block, 300 path, 36 producer chain, 18 declared C, 64 checked error (10 with a later failing PC), 48 kept C), 209 blocks, 4947 calls, 162701 checks`. C6 시험은 오류 행 둘만 바뀌어 1,248 fixtures 그대로이고, 다른 C++ 시험 300개는 바뀌지 않고 통과한다.
- [F] 생성기: 다시 돌려 C11 시험 파일이 바이트 단위로 같다(`trial_logs/gen_repro.log`, 약 80초). 행 1,107. 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 출구 중 stop이 아닌 것 0, 계산 점프 행이 목록 handler `21602`에 멈춘다.
  - 실제 생산자 사슬 6개: `1d5c4`→`1d5ce`, `1d5fc`→`1d606`(`49c38`), `1d76a`→`1d770`(`4836e`), `21960`→`21968`, `21a76`→`21a7e`(`215e6`, 합성 목록), `4eb7a`→`4eb84`(Z, `4a974`).
  - 선언 C 행만 있는 소비자 4개: `1d8fa`·`1db9c`(C6 `1d510` / `1d514`: 합성 world에서 Clear만 나옴 — Set 쪽은 `1aa3a`·`2986`을 지나는 경로라 사슬 world가 남지 않음), `e8c7c`(실제 2986은 Unicorn world에서 빈 node가 없어 실패 쪽만 나오고 그 run은 `290e` 걸러내기로 버림), `1e5ec`(생산자 `4c2c4`가 routing 밖, D-1).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, C11 시험): 빌드 종료 0, 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_build.log` `ubsan_run.log`).
- [F] V1 pc11(작업자, `--workers 3`): fixtures 1,793(match 934, error 849, mismatch 10; natural 38) failed 0, `ok` true, 방문 시작 208/209(`1e5ec`는 뒤 단위 gated), 빠진 후속 0, 도달 못한 분기 결과 0(`MODEL_GATED` 둘 제외), carry oracle Unknown/Clear/Set = 912/12/10, 입력 파일 불변 확인 true(`trial_logs/v1_final_pc11.log`, `v1/final_pc11/report.json`). 앞선 두 시도(`v1/pc11_try1` `pc11_try2`)는 spec 보완 전의 것이다(1차: `1e5f0` 계열의 스택 hint 부족으로 build 중단, 2차: 통과했지만 `MODEL_GATED` 정리 전).
- [F] V1 regression specs(작업자, `work/v1_regs.sh`, `--workers 3`; `trial_logs/v1_regs_r1.txt` `v1_regs_r2.txt`): pc2 1,743, pc3 1,829, pc4 1,873, pc5 1,755, pc6 1,856, pc7 2,077, pc8 986, pc9 2,347, pc10 1,334, fr10 2,170, fr11 2,170, fr12 2,302, fr13 2,122, fr14 1,783, se2 1,573(모두 failed 0, `ok` true; FR14 기록과 같은 수). pc7 pc9 fr10 fr11 fr12의 빠진 후속·도달 못한 결과는 FR14 때의 실행(`ms5-scratch/fr14/v1_reg_*.log`)과 같다. 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·op, WORD/BYTE → LONG, 복귀 PC·호출 대상, carry 교환, mask, 상수·설치 값, `pc11_*` helper 인자) + 손으로 고른 helper·block 변이(`JMP (A1)` 목록과 비교 폭, Z 읽는 `4eb84`의 guard·폭·반전, MULS의 부호·첨자, `1e5f0`의 NEG / SUBI, `e8c7c` MOVEM의 부호 확장·순서, `4ec3c` BLS, `4ecac` SEQ / BTST Dn, `1cb76` `1e6ce` `1e744` `4ecec`의 폭, 계수기 `1db7c` `1ddf2` 등) + dispatcher carry 목록 9개·추가·범위 46개를 적용해 만든 것, 968개; `--workers 3`): 1회째 `killed 930 of 968`(`trial_logs/mut_first.log`). 생존 38개는 local Qwen이 먼저 분류했고(`qwen/mut_out.txt`) 작업자가 하나씩 확인했다. 16개는 시험 빈틈이었고 규칙 `rules_g`(MULS의 WORD `8000`과 음수 첨자 — 합성 표를 `4409e`부터로 넓힘, `1cb76`의 BYTE `90` 첨자, `1d722`의 WORD 빌림, `1e744` `21a42` `4ecec`의 WORD 첨자, `1e93e`의 WORD 비교, `7d82` / `7e80(A5)`의 BYTE 크기, `4a930`의 부호 확장 `-7ffd(A5)`, `1e5f0`의 결과 0, `4ecac`의 BYTE D0)와 합성 바이트 둘로 메웠다(`trial_logs/mut_gaps.log`). 남은 22개는 동치다(`mut/equivalents.txt`, 사례별 이유: `MOVEQ #0` 뒤라 같은 레지스터 값, 곧 덮어쓰는 MULS·MOVE.L, `am_byte` / `am_write`의 자체 mask, 범위가 좁은 첨자 등). 규칙을 더한 뒤 전체 2회째 `killed 946 of 968`(`trial_logs/mut_second.log`), 남은 22개가 동치 목록과 같다. Qwen의 잘못된 분류 3건은 `ms5-scratch/tools/qwen_lessons.md`(2026-10-27)에 적고 `qwen_system.md`에 규칙을 더했다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`, 메인 runner용), `real_pc11.py`(FR14 harness에 C11 world(`c11_world`)·소비자 9·Z 읽는 `4eb84`(native SR Z = BYTE (A0) = 0)·선언 정지(C11 뒤 단위 정지 15, C1~C9의 남은 정지)·`cb` 진입에 C6 `1d398` `4eb58`과 C3 `21610` `201a2`(→ C11 착지); `JMP (A1)` `21a82`의 착지를 trace 전체에서 대조; 분류 `JUMPTGT11B` `ZSOURCE11` 추가; `native_safe` 기본 유지)): 작업자 300건 seed 1 `mismatches 0`(covered 197/209, `trial_logs/real_t300.log`), 1,500건 seed 1 `mismatches 0`(`covered starts 209 of 209`; 문서화된 분류: 2986 실패 경로의 caller X 21건(C7 결정 6), C11 jump-target 1건(무작위 A1의 `21a82`), C11 flag-source 0건; 깨끗이 멈추지 않은 native 244건 건너뜀; native oracle abort 0, `trial_logs/real_w1500s1.log`).
- [F] **IO, 세 번째 관측**(C11 연결 뒤, `--observation ms5-scratch/obs3/final/observation.json`, pin `io-ext2`, `--workers 3`): run 11, native 비교 frame 18,718 가운데 일치 **5,707**(기준선 5,681 → +26 = 재관측 예측 6,664 − P2 carry 결함 957), 불일치 2(D1 295 / D2 481, P2 carry, 기준선과 같음), C++ 오류 11(`M1.5` 첫 정지 뒤 frame-wise 비교의 `cue wrapper failure requires known caller X`, 기준선과 같음), chain divergence 0(`trial_logs/io_ext2_c11.log`; `verification.json` SHA256 `240bbc05a1650c0b…`, `frontier.json` `f923926e18f3b890…`, scratch `io_ext2_c11/`).
  - run별 일치: `M2.0` 190 → 215, `M4.0` 192 → 193, `M1.5` 190, `M3.1` 225, `G1.94` 768, `G1.68` 960(첫 정지 PC만 C11 뒤로 옮겨 감), `P0` `P1` 600, `X1` 1,180.
  - 확인된 frontier: `ca5c`(E-1; `G1.94` 768, `G1.68` 960, callback `4e94e` → 복귀 `4ebbc`), `1d776`(C-2; `M2.0` 215, callback `1d75a`), `40a5a`(D-1; `M4.0` 193, callback `3fedc`), `4c2c4`(D-1; `M1.5` 190, 복귀 `1e5ec`), `M3.1` 225(D). 재관측 예측(`reobs/c11v1.stops`)과 run·frame이 같다.
  - 수용 키: 분기 없음·frontier 확인·전체 실행·guard·음성 검사·검증기 오류 없음은 true, 불일치 0·다른 첫 실패 없음·예상 밖 C++ 오류 없음은 false다(기준선과 같은 P2 carry 불일치와 `M1.5` caller-X 오류 때문; 계획 §11.6).
- [F] legacy 검증기(작업자, clone root `tools/legacy_one.py`): `input`은 처음에 `outside_entry_1d5c4`가 성공(이전 기대 `unsupported animation machine PC`)해 실패했고, `1d5c4` `1d5fc`를 `SUPERSEDED_OUTSIDE`(`area C C11 (player_c11)`)에 넣은 뒤 종료 0(`trial_logs/legacy_input.log`: cases 685, census 7,321, negatives 561). `stage_area` `stage_event` `stage_event_ops`도 종료 0(`trial_logs/legacy_*.log`). 나머지 legacy 검증기·frame 비교·원래 / 확장 IO 관측은 결정적 runner가 돌린다.
- [F] `CPP_PINS`: stage_event / stage_event_ops의 두 pin이 최종 `animation_machine.cpp` / `animation_machine_internal.h` SHA와 같다(두 검증기 모두 위 legacy 실행에서 pin 확인 통과).

## 검증 기록(검증 실행: 결정적 runner + 메인 검토)

- [F] `make -j3 all test`: 종료 0, 경고 0, Assert 0, Python 310 OK. C11 시험 `animation machine player pc11: 1107 fixtures (689 single-block, 300 path, 36 producer chain, 18 declared C, 64 checked error (10 with a later failing PC), 48 kept C), 209 blocks, 4947 calls, 162701 checks`.
- [F] `ubsan`(단위 이름 `pc11`로 다시 실행): 빌드/실행 종료 0, 런타임 오류 0. (첫 실행은 단위 이름을 `c11`로 줘서 시험 파일을 못 찾았다. runner 인자 오류이며 코드 문제가 아니다.)
- [F] `mutation`: 변이 968, 제거 946, 등가 22(모두 문서화된 등가).
- [F] real-ROM: 배치 `f4`, `f5`, `s1`, `s2`, `s3` 커버 209, 209, 209, 209, 208; mismatches 0,0,0,0,0.
- [F] V1(`pc11`): A/B 각각 fixtures 1793, failed 0, identical true(digest `921df7dacd6fcf3c`). 회귀 spec 51개 모두 failed 0.
- [F] legacy 검증기 10개(`stage_entry` `area_clear` `stage_event` `stage_event_ops` `frame_helpers` `card_menu_close` `input` `scene_core` `scheduler` `objects_g1`) 모두 종료 0.
- [F] frames: `d1` 54400/54400, `controller_game` 54400/54400, `irq` 54400/54400, `demo` 45684/45684, 모두 mismatches 0.
- [F] IO(원래 관측): 일치 173966/173966, mismatches 0, C++ 오류 0, 수용 키 모두 true, 두 번 실행 identical. IO(입력 확장 관측): 일치 14500/14500, 변화 없음.
- [F] IO(세 번째 관측 `io-ext2`, scratch `obs3/final`): 일치 5,681 → **5,707**(+26, 예측과 같음: 재관측 예측 6,664 − P2 carry 불일치 957). 불일치 2(P2 `D1`/`D2`의 frame 끝 carry)와 C++ 오류 11(`M1.5` caller-X)은 기준선과 같다. 두 번 실행 `verification.json` `240bbc05a1650c0b…`, `frontier.json` `f923926e18f3b890…`로 같다. 첫 정지: G1.94/G1.68 `ca5c`(E-1), M2.0 frame 215 `1d776`(C-2), M4.0 193 `40a5a`와 M1.5 190 `4c2c4`(D-1).
- 검증 방법: 결정적 runner(LLM 없음; runner의 triage는 사용하지 않음). 계약 초안의 block 표 일부와 변이 생존자 1차 분류는 local Qwen이 썼고(분류 3건 오류는 작업자가 정정) 작업자·메인이 검토했다.
