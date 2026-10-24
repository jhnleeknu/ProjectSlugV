# 영역 C 단위 C9(입력 확장 관측의 첫 단위: 플레이어 입력 상태 `1ec74` → `1ecb8`, `1f070`/`1f086` → `1f0ae`, `1f48a` → `1f4b6`, callback `1f3e8`·`1fb28`·`20720`, 지면·공중 상태 `208fa` → `20a98`/`20aec`·`20b42`/`20b96`·`20cd8`/`20d36`(settle helper `20a4a`/`20a6e`), `21370`, 칸 `84` 상태 `21ca4`/`21cd8`·`21d0e`/`21d2a`·`21e48`·`2210c` → `22128` → `22174`·`22238`/`22240`·`223a0`..`223e8` → `22408`/`2241c`·`22452`, `JMP (A1)` 4곳, 220 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §10.5 표의 C9 행과 §10.8 "C9 상세 명세"를 기준으로 삼고, 구조·공통 규칙은 C8 계약(`animation-machine-player-c8-contract.md`)·C7 계약 … C1 계약을 따르며 다른 점만 적는다. 단위 이름은 C9, 파일 접두어는 `player_c9`(C++) / `pc9`(V1 spec)다(계획 §10.x 메인 결정). 이 단위에서 IO 검증기의 관측 pin을 "알려진 관측 pin 표"로 바꾼다(메인 결정, 결정 5). 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다. BIOS 실행, 자연 scheduler, IRQ timing은 주장하지 않는다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기와 장치 쓰기는 없다(장치·bank는 callee가 다룬다). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `main` `b268e31`(branch `claude/c9-core`; C1~C8, E1, D routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `2622b7a2374959c551dea03156bc48ab1f7995118a1c1664e80e30ad36d443c5`, `animation_machine_internal.h` `57606da7148c24cc37efdec0560ea0f8a6ec6ce95932953f63cd8012c1499662`(계획 §10의 기준과 같음).
- [F] 관측 입력(읽기 전용):
  - 원래 IO 관측 `artifacts/animation_machine_io_native`(`observation.json` SHA256 `66d30130d8a11a86…`, compared_sha256 `4bb6b933…`).
  - 입력 확장 IO 관측 `artifacts/animation_machine_io_ext`(사용자 승인, `observation.json` SHA256 `9da40ac6dcbea3ebc6423319fc79755ebe87af3fc982bc7a70d596762125ffe6`, compared_sha256 `b5d15d4fcd53555b…`; scratch `ms5-scratch/obs2/final/`과 같음). V1 natural family가 이 관측의 state pack을 읽는다.
  - 이 단위의 정확 bitmap 재관측 한 벌(scratch `ms5-scratch/c9/reobs/c9r`, C9를 실제로 routing한 작업 트리; 결정 1).
- [F] 시작 목록: **`ms5-scratch/c9/starts_C9.txt`(220개, SHA256 `7297354e6f1ddb88bbc0d2aed46990b57ee563eb244bdd6452d8b182c9017759`)** = 계획 `ms5-scratch/obs2/starts_C9.txt`. 실행부의 `case` label 220개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(작업자 확인: 실행부 case 집합 = 시작 목록, `make test`의 C9 시험이 시작 220개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/c9/`
  - `reobs/c9r`(재관측) `reobs/c9r.dleft` `reobs/c9r.stops`, `tools/newvis_c9.py` → `work/newvis_ext_c9r.txt`(새로 보인 PC), `tools/flagscan.py` → `work/flagscan_C9.txt`(block 경계를 넘는 flag), `work/intargets.py` → `work/intargets_c9.out`(범위 안 비시작 PC로 오는 직접 분기), `tools/refs_c9.py` → `work/refs_c9.out`(ROM 전체 C9 시작 참조와 다음 명령), `tools/natscan_c9.py` → `work/natscan_c9.out`(확장 관측 pack의 C9 callback·칸 `84` frame), `work/c9io_ext.txt`(IO 실행 run·frame), `work/mkpc9.py` + `work/pc9parts/`(V1 spec 조립: C8 spec의 공용 부분 + C9 부분), `work/mkc9test.py` `work/c9test_head.txt` `work/c9rules.cpp`(C9 시험 파일 조립), `work/v1_regs.sh`(V1 회귀), `work/ubsan.sh`, `work/pincheck.py`(CPP_PINS 대조), `tools/neg_probe.py`(IO 음성 검사 탐침), `tools/jdiff.py`(IO 보고서 비교), `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위(결정 1)

- [F] **기준선**(현재 `main` routing, 입력 확장 관측): IO 비교 14,500 frame 가운데 일치 **5,095**, 불일치 0, 수용 키 모두 true(이 단위의 pin 표, 결정 5), `frontier.json` SHA256 `a39e85f6…`(계획 §10.6과 같음; `trial_logs/io_ext_mainengine.log`). 첫 정지는 확인된 C frontier 8 run(`2210c` 4, `21e48` 2, `1f3e8` 1, `1f070` 1).
- [F] **정확 bitmap 재관측(C9를 실제로 routing)**: C9 연결 뒤의 작업 트리(routing SHA256 `48ba3f29953b656d…`, routing된 짝수 PC 128,934 = 계획 `v2_u1`과 같음)로 `tools/observe_animation_machine_io_ext.py --cases 94,68`를 다시 돌렸다(scratch `reobs/c9r`, 관측기 수정 없음).
  - run 12개의 기록 SHA256이 계획의 C9 가상 routing 재관측(`obs2/reobs/v2_u1`)과 모두 같다. state pack도 `artifacts/animation_machine_io_ext`와 모두 같다.
  - `dleft.py`(`MS5_OBS2=reobs/c9r`): 실행된 routing 밖 PC C **102** / D 659 / E 108, 예측 일치 frame **5,839**, 첫 정지 D 6 run(`6f1ca` 2, `eaac0` 2, `252b4` 1, `71468` 1) · C 2 run(`223fa`, X4)(`reobs/c9r.dleft` `c9r.stops`). 계획 §10.5 표와 같다.
  - [F] **숨은 직선 연속 검사**: 기준 관측과 재관측 사이에 새로 보인 routing 밖 PC는 **없다**(`tools/newvis_c9.py` → `work/newvis_ext_c9r.txt`: 12 run 모두 0). C9 범위의 끝 PC 가운데 실행되는 것은 `1f082` `20bfe` `22148` `22286` `223fa`(모두 계획이 C10에 둔 뒤 단위 정지, 아래 "출구")뿐이고, 기준 관측에서도 이미 보였다. 그래서 범위를 바꾸지 않는다(220 block 그대로). 계획 §10.5에서 수렴을 확인한 2차 계획(`xplan_v2.json`)과 같은 결과이므로 반복을 한 번으로 멈췄다.
- [F] **범위 밖에서 범위 안 비시작 PC로 들어오는 직접 분기**: 없다(`work/intargets_c9.out`). 찾은 둘은 operand를 명령으로 읽은 것이다: `19cde dbls d0,1f0a0`(= `19cdc MOVE.L 53c8(A5),53c0(A5)`의 operand), `1ec82 bls.b 1ecd4`(= C9 `1ec7e MOVEA.L #36350,A0`의 immediate).
- [F] **IO 실행**(입력 확장 관측, `work/c9io_ext.txt`): C9 PC 126개(모두 시작), 실행 18,584회(TB 첫 routing 밖 PC로 기록된 수; 계획의 18,815는 재관측 병합 기준), run 8개(X1~X4 × case 68·94). 처음 frame은 X1 68 440, X1 94 224, X2 68 438, X2 94 216, X3 68 436, X3 94 221, X4 68 440, X4 94 280. 실행되지 않은 시작 94개는 closure로 들어왔다.

## C9 상세 명세(계획 §10.8)

### 범위

- [F] **220 block, 454 명령, 1,996 byte, 20 범위**(시작 목록 SHA256 `7297354e…`, 범위 이어 붙인 SHA256 `4b010840cf4b5a9405a971c7ff6404d69111ffc7217341c4f84807b27645fa24`). 짝수 PC 998(내부 778). 범위·byte·SHA는 계획 §10.8.1 표와 같다(다시 확인함).

| 범위(CPU = 파일 오프셋) | byte | 시작 | 내용 [I] |
| --- | --- | --- | --- |
| `1d086..1d09e` | 24 | 4 | 이동 기록 helper `1d086`/`1d092`(`BSR 1cfbe`, LONG `8`/`4(A0)` → D1, C4 `1d0a4`로) |
| `1ec74..1ed22` | 174 | 22 | 상태 `1ec74`(BYTE `9e` = 1이면 자식 `36350`·`49214`), `1b764`/`1cb08`의 C, `1cab6`, 상태 `1ecb8`(입력 D0 bit 5/1/7, `AND.W #c`, `4bfc0` `ce02` `49fc6`의 C) |
| `1f070..1f082` | 18 | 1 | C4 `1ef84 BEQ`: `BCHG #0,15`, `TST.B 9d; BLE` |
| `1f086..1f126` | 160 | 19 | `1cab6`, 칸 부분, 상태 `1f0ae`(입력, `AND.W #50` → `1eeea`, `1d092`) |
| `1f3e8..1f3ec` | 4 | 1 | callback `1f3e8`: `LEA 1b26e(PC),A0` → C8 `1f3ec` |
| `1f48a..1f538` | 174 | 21 | C8 `1f462 BNE`: `1cab6`, 칸 부분, 상태 `1f4b6`(`1cec2`의 D1 = 1 → C7 `1f538`, `1d086`) |
| `1fb28..1fb2e` | 6 | 1 | `MOVE.L #1ec74,(A6)` → C8 `1fb2e` |
| `20720..20738` | 24 | 1 | callback `20720`(C3 `2064e`가 씀): `CMPI.W #a0,42; SPL.B 5f`, LONG `3a` := `a9800`, BYTE `5e` := ff → C5 `20738` |
| `208fa..2092c` | 50 | 8 | `ea680`의 C, `1aa3a`의 D0 bit 1/11/9 → `20a98` / `21370` / `20b42` / `20cd8` |
| `20a4a..20bfe` | 436 | 41 | settle helper `20a4a`(`ea680`; Set: LONG `3a` := (D1 + LONG 18(A0) − LONG 46) ASR 3, LONG `36` −= LONG 36 ASR 3) / `20a6e`(LONG `36` += (0 − 36, +7) ASR 3, LONG `3a` += (fffc0000 − 3a, +7) ASR 3), 상태 `20aec`(WORD `88` 세기), `20b42` → 상태 `20b96`(WORD `2c` += (40 − 2c) ASR.W 3, `20bd6` SWAP/`CMPI.W #28`) |
| `20c00..20c30` | 48 | 7 | `20bee`의 settle 뒤쪽(fffd0000), `43ea4` `ce02` `49fc6`, `21520` |
| `20cd8..20d72` | 154 | 11 | 자식 `eaac0`, `4970a`의 A0 WORD `76` := 2 / 1, 상태 `20d36`(`SUBQ.W #1,88; BCC`) |
| `21370..213da` | 106 | 6 | `8ff4`, WORD 표 `1b170`(×2) → `8ebe`, BYTE `14` := BYTE `19`, `1cb38`, 칸 부분, `20efc`, `21430` |
| `21ca4..21d60` | 188 | 28 | 칸 `84` 상태 `21ca4`(C3 `21c22 BGT`; `21bc6` `21baa` `21c1c`의 C → `223b2`), `21cd8`(목록 `21aee`, `JMP (A1)` `21ce4`), `21d0e`(C3 `21c22`/C8 `21e5a BLT`) / `21d2a`(목록 `216c8`, `JMP (A1)` `21d36`) |
| `21e48..21e52` | 10 | 1 | 목록 handler `21e48`: `aa` := 1, `LEA 1b9a8(PC),A0` → C8 `21e52` |
| `2210c..22148` | 60 | 3 | 칸 `84` 상태 `2210c`(`1cd98`, D0 bit 0/1의 SEQ / SUB.B → BYTE `9d`), `22128`(BYTE `7e` `a5` `a6` `aa`, BYTE `a7` bit 0 → C10 `22148`) |
| `22174..221ca` | 86 | 8 | `TST.B 9d`의 BGT / BLT로 ROM LONG 표 `22074` / `220c0` / `22028`(BYTE 4(LONG 8c(A6)) × 4) → `1cabe`, BYTE 4 = 5 / a → C10 `22286`, 6 / b → `22238` |
| `22238..22286` | 78 | 13 | 칸 `84` := `22240`, 목록 `216c8`, `JMP (A1)` `2224c`, `1cd98`, BYTE `7e`/`a5`, `2156a`, TST.W D7 → 칸 `84` := `22452`, RTS |
| `223a0..223fa` | 90 | 10 | 방향 진입 `223a0` `223b2` `223c4` `223d6` `223e8`(BYTE `9d` := 1 / 0 / ff / ff / 0, 기록 `1b85e` `1b8ba` `1b8fe` `1b920` `1b964`, `1cabe`) → `22408` |
| `22408..22472` | 106 | 14 | 칸 `84` := `2241c`, 목록 `216c8`, `JMP (A1)` `22428`, `1cd98`, `2156a`, TST.W D7 → 칸 `84` := `22452`, RTS; 칸 `84` 상태 `22452`(BYTE `9c` = 3 / 4 → 1), C3 `21602`로 |

- [F] **진입**(계획 §10.8.1): `1d092` `1f070` `1f3e8` `21e48` `2210c` `223a0` `21ca4` `22452` `1d086` `1f48a` `1fb28` `20720` `208fa` `223d6` `21d0e`.
- [F] **호출자**(ROM 전체 참조 검색 `work/refs_c9.out`, 다음 명령 포함; 현재 routing 기준 소유):
  - `1f070` ← C4 `1ef84 BEQ`(뒤 단위 `1f032`). `1f48a` ← C8 `1f462 BNE`(뒤 단위 `1f3b0`). `1f3e8` ← `MOVE.L #1f3e8,(A6)`: C7 `1f334` `1f5c8`, C8 `1f480`, C9 `1f52e`, 뒤 단위 `1f9d0`. `1ec74` ← C9 `1fb28`, 뒤 단위 `1dfdc` `1fc2e` `1ff4e`, `1df3e BRA`. `20720` ← C3 `2064e MOVE.L #20720,(A6)`. `21ca4` / `21d0e` ← C3 `21c2c BGT` / `21c30 BLT`, C8 `21e5a BLT`. `223a0` / `223d6` ← C3 `21c7c` `21c84`, C4 `21da8` `21db0`, C8 `21e80` `21e88`. `2210c` ← C3 `21c94`, C4 `21dc0`, C5 `21f8e`, C8 `21e98`, C3 `221f6 MOVE.L #2210c,84(A6)`, C9 `21d06` `21d58` `22268` `2243a`. `22452` ← C3 `22220`, C9 `2227c` `22448`. `20a4a` ← C9 `20af8` `20bb0`, 뒤 단위 `20c8e`(다음 `BRA.W`). `21370` ← C9 `20916`, 뒤 단위 `207da` `2085e` `2096e`. `22174` ← C9 `22144 BEQ`, 뒤 단위 `22164 BCC`. `22128` ← 뒤 단위 `222b6 BNE`·`22396 MOVE.L #22128,84(A6)`.
- [F] **설치 값**(`MOVE.L #v,(A6)`): 곧바로 들어감 `1ecb8`(`1eca8`) `1f0ae`(`1f08a`) `1f4b6`(`1f492`) `20aec`(`20ac4`) `20b96`(`20b6e`) `20d36`(`20d0a`). 다음 frame에 들어감 `1ec74`(`1fb28`), `1f3e8`(`1f52e`), routing된 `1ed78`(`1ed18`) `1eeea`(`1f11c`) `21542`(`20d62`). **쓰기만**: `20c30`(`20be8`; C10 계획 범위 밖, IO에서 실행되지 않음) — routing 밖 선언 정지로 남는다(C6~C8 메인 결정과 같음).
- [F] **둘째 callback 칸 `84(A6)` 값**: `21602`(routing, 칸 부분 6곳), `21cd8`(`21cca`) `21d2a`(`21d1c`) `22240`(`22238`) `2241c`(`22408`) `22452`(`2227c` `22448`). 모두 C3 `201a6 JSR (A4)`의 허용 목록(`PC3_SLOT84`) 안이다.
- [F] **자식**(`MOVEA.L #v,A0` 뒤 `JSR 28ae`): `36350`(`1ec7e`) `371f8`(`20b50`) — IO에서 실행되지 않음, 선언 정지(메인 결정); `eaac0`(`20cd8` `20d44`) — FR10.

### 계산 점프와 목록(결정 2)

- [F] **`JMP (A1)` 네 곳**. A1은 C3 `215e6`(목록 조회, C3 계약 결정 2)이 ROM 목록에서 `MOVEA.L (A0)+,A1`로 읽은 handler LONG이다. `JMP`는 `215e6`의 Set 쪽(목록이 key BYTE `9c(A6)`를 찾음)에서만 실행된다.
  - `21ce4 JMP (A1)`(`21cd8 LEA 21aee(PC),A0; BSR 215e6` → `21ce0 BCC`의 Set 쪽). 목록 `21aee`([F] ROM 바이트): (`21602`, 0) (`21d60`, 2) (`21e48`, 3) (`21e3a`, 4), LONG 0. **허용 대상 = `21602`(C3) `21d60`(C4) `21e48`(C9) `21e3a`(C8)**.
  - `21d36` `2224c` `22428 JMP (A1)`(`21d2a` / `22240` / `2241c LEA 216c8(PC),A0; BSR 215e6`). 목록 `216c8`: (`21602`, 0), LONG 0. **허용 대상 = `21602`**.
  - C3 `21620`·C4 `21c72`·C5 `21f7c`·C8 `21d9e`와 같은 규칙: A1이 그 목록의 handler면 PC := A1, 그 밖의 A1(직접 진입)은 checked `unsupported animation player c9 jump target`이다. 비교는 LONG 전체다(`1021e48`, `121602`는 거부).
  - [I] ROM 자료 생산자(`215e6`와 그 목록)가 만드는 A1은 언제나 허용 목록 안이다. C9 뒤 네 목록의 handler는 모두 routing된다.
- [F] PC 상대 BRA.W 표·TRAP·DIVU·MULU/MULS·MOVEM은 없다.
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙):
  - WORD 표 `1b178`(`20aa4`) / `1b170`(`21376` `2138e`): 첨자 = WORD `76(A6)` × 2(WORD 덧셈, 16 bit에서 넘침), 부호 확장(`MOVE.W (A0,D0.W),D0`).
  - LONG 표 `22074` / `220c0` / `22028`(`2218c`; 각 19 LONG): 첨자 = BYTE `4(A4)` × 4(A4 = LONG `8c(A6)`, `MOVEQ #0` 뒤 WORD 덧셈 둘, 부호 확장).
  - 넘기기만 하는 포인터(`LEA d(PC)`): `1b764` `1b1ec` `1b26e` `1b2cc` `1bc5a` `1bc5c` `1bc56` `1b880` `1b942` `1b9a8` `1b85e` `1b8ba` `1b8fe` `1b920` `1b964` `21aee` `216c8`(A0, callee가 읽음).

### `ASR`·`SPL`·`SWAP`·borrow(결정 4)

- [F] **`ASR.L #3,Dn`**(`20a54` `20a80` `20a90` `20b12` `20b22` `20c00` `20c10`): 부호 bit로 채우는 오른쪽 shift. `pc9_asr`는 부호 있는 shift 없이 무부호 LONG에서 `>> count`와 위쪽 채우기 `0xffffffff << (32 − count)`로 계산한다(UB 없음, C8 `pc8_asr`와 같은 꼴; count는 `& 63`, 32 이상이면 부호만 남는다 — 이 단위의 count는 즉치 3뿐이다).
- [F] **`ASR.W #3,D0`**(`20b9e`): WORD(bit 0..15)만 bit 15로 채워 shift, D0 bit 16..31은 그대로(`pc9_asr_word`).
- [F] **settle**(`20a6e` `20b00` `20bee`): `MOVEQ #0,D2; MOVE.L #k,D3; SUB.L 36(A6),D2; BMI` — D2 = 0 − LONG 36(mod 2^32), BMI는 그 결과의 bit 31. 음수가 아니면 `ADDQ.L #7`(LONG). 이어서 `ASR.L #3,D2; ADD.L D2,36(A6); SUB.L 3a(A6),D3; BMI` / `ADDQ.L #7,D3` / `ASR.L #3,D3; ADD.L D3,3a(A6)`. `20bee`의 음수 아님 쪽 `20bfe`(`ADDQ.L #7,D2`)는 C10이다(뒤 단위 정지).
- [F] **`20720`**: `CMPI.W #a0,42(A6); SPL.B 5f(A6)` — SPL은 N만 본다. N = (WORD 42 − a0) mod 2^16의 bit 15. 부호 있는 비교(GE)와 다른 경우(`809f` → `7fff`, N = 0 → ff)를 시험에 넣었다. SPL은 BYTE 쓰기만 한다.
- [F] **`20bd6`**: `SWAP D1; ADD.W 18(A0),D1; SUB.W 46(A6),D1; CMPI.W #28,D1; BCS.W 20bee` — WORD 연산(D1 bit 16..31 = SWAP 전 bit 0..15), BCS는 무부호 WORD `< 28`.
- [F] **`20d3c`**: `SUBQ.W #1,88(A6); BCC.W 20d6e` — C = borrow = WORD 88이 0이었음. `20af4` `20b9e`의 `SUBQ.W #1,88`은 flag를 읽지 않는다.
- [F] **`22116`**: `BTST #0,D0; SEQ.B D1; BTST #1,D0; SEQ.B D2; SUB.B D2,D1; MOVE.B D1,9d(A6)` — D0 bit 0 / 1 = (0,0) 0, (1,0) 01, (0,1) ff, (1,1) 0. D1·D2의 bit 8..31은 그대로.
- [F] **`22452`**: `MOVE.B 9c(A6),D0; CMPI.B #3,D0; SEQ.B D1; CMPI.B #4,D0; SEQ.B D2; OR.B D2,D1; BEQ` — BYTE `9c`가 3 또는 4면 `22468`(BYTE `9c` := 1), 아니면 `2246e`.

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `28ae` `8ebe` `8ff4` `ce02` `1aa3a` `1cab6` `1cabe` `1cb08` `1cb38` `1cd98` `1cec2` `1cfbe` `1d0a4` `1eb98` `1eba0` `1eeea` `1f1d8` `1f2a4` `1f3ec` `1f538` `1f5d2` `1f5f2` `1f76e` `1f7a4` `1fa3c` `1fa68` `1fad2` `1fae8` `1fb2e` `201a2` `20738` `2092c` `20efc` `21430` `21520` `2156a` `215e6` `21602` `21baa` `21bc6` `21c1c` `21e52` `21ffc` `221ca` `43ea4` `49214` `49274` `4970a` `49fc6` `4bfc0` `ea680`, 그리고 `JMP (A1)`의 handler `21d60` `21e3a`(`21602` `21e48`은 위 목록·C9 시작).
- [F] **뒤 단위 정지**(실행되지만 C10이 가짐; V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS`): `1f082`(`1f07e BLE`의 fall-through), `20bfe`(`20bfa BMI`의 fall-through), `22148`(`22144 BEQ`의 fall-through), `22286`(`221ae` `221b6 BEQ`), `223fa`(`21d40 BNE`).
  - C9 run이 지나가는 C1~C8 block의 남은 정지(pc8 `EXIT_STOPS` 가운데 C9가 routing한 `1f48a` `1fb28` `21d0e` `2210c` `223a0` `223d6` `208fa` `1f070` `21ca4`를 뺀 16개: `1fd3c` `21ea0` `1d3e0` `4eb6a` `1dc8e` `1dccc` `1efd6` `21dd0` `4ef08` `1de3c` `1e21c` `1e8de` `1fc96` `1fd50` `21fa6` `4e69a`)도 pc9 `EXIT_STOPS`(모두 21개)에 넣었다.
- [F] 직선 fall-through로 범위를 벗어나는 곳: `1f3e8`(→ C8 `1f3ec`), `1fb28`(→ C8 `1fb2e`), `20720`(→ C5 `20738`), `21e48`(→ C8 `21e52`), `221c2`(→ C3 `221ca`)와 위 뒤 단위 정지 셋. 재관측에서 새로 보인 PC가 없어 가려진 연속은 없다(결정 1).
- [F] TRAP 없음. ROM·RAM 실행 없음. 장치 쓰기 없음(`MOVE` 대상은 node·`4970a` 자식 A0·work RAM).

### block 경계를 넘는 flag(결정 3)

C8 방식 그대로 block 첫 명령부터 flag를 정하는 명령까지 훑었다(scratch `tools/flagscan.py` → `work/flagscan_C9.txt`). X를 읽는 명령은 없다.

- [F] **C 소비 block 14개**(Clear 쪽 / Set 쪽; Unknown C면 `player c9 caller requires known carry`):
  - `1eca0 BCC 1eba0`(C2 `1cb08`, A0 = `1b764`), `1ed14 BCC 1ed1e`·`1f118 BCC 1f122`·`1f52a BCC 1f534`(C2 `49fc6`),
  - `20900 BCC 2091e`·`20a50 BCC 20a6e`·`20bd2 BCC 20bee`(N35 `ea680`: `1abda` WORD `5430(A5)` ≠ ffff → Set 쪽은 U18 지형 탐색 `ea65a`의 C),
  - `21cae BCS 223b2`(C3 `21bc6`), `21cb6 BCS 223b2`(C3 `21baa`), `21cbe BCS 223b2`(C3 `21c1c`: `ANDI.B #fe,CCR; RTS`(ROM `023c 00fe 4e75`)라 언제나 Clear),
  - `21ce0 BCC 21ce6`·`21d32 BCC 21d38`·`22248 BCC 2224e`·`22424 BCC 2242a`(C3 `215e6`).
  - 생산자 쪽은 모두 기존 실행부가 known C를 돌려준다(callee의 RTS가 dispatcher carry 목록에 있음). C9 block은 C를 만들지도 넘기지도 않는다.
- [F] **N이 경계를 넘는 곳 하나: `22180`**(`LEA 220c0(PC),A0; BLT.W 2218c`). BLT는 `22174 TST.B 9d(A6)`의 N ⊕ V를 읽는다(TST라 V = 0, 그 사이 `LEA`·`BGT`는 flag를 바꾸지 않고 메모리도 쓰지 않음). `22180`으로 오는 길은 `22174`의 fall-through 하나뿐이다(`work/intargets_c9.out`, `work/refs_c9.out`).
  - C1 `ca50`·C5 `1c3e2`·C6 `4ee30`의 규칙대로 `22180`은 **BYTE `9d(A6)`를 다시 읽어 N을 정한다**. 주소가 work RAM / 고정 ROM(24 bit `< 200000`)이 아니면 다시 읽기가 장치 읽기가 될 수 있으므로 checked `unsupported animation player c9 flag source`다.
- [F] **돌려주지만 읽는 쪽이 없는 flag**: RTS `20a54`(`SUB.L`), `20a90`(`ADD.L`), `22284`·`22450`(`MOVE.L`/`TST.W`: Clear). `20a4a`의 호출자 `20af8` `20bb0`(C9)·`20c8e`(뒤 단위)는 돌아온 뒤 `BRA.W`이고, `22238`·`2241c` 계열은 C3 `201a6 JSR (A4)`로 불려 `201a8 JSR 1a9e8`로 돌아간다. 그래서 통과 목록에 넣지 않는다(돌아간 뒤 Unknown). `2226c BTST.B #1,aa(A6)`의 Z도 다음 `22272 BSR 2156a`가 읽지 않는다(읽기만 실행한다).
- [F] 그 밖의 `Bcc`/`Scc`는 같은 block 안의 `TST`/`CMP`/`CMPI`/`BTST`/`AND`/`SUB`/`OR`가 정한 flag를 읽는다(`1f070 TST.B; BLE`: BYTE 0 또는 bit 7, `22174 TST.B; BGT`: BYTE 01..7f).

### IO 실행 run과 frame

- [F] 실행 run 8개(X1~X4 × case 68·94), 첫 frame은 위 "재확인과 범위". 플레이어 node는 `100cb8`이다.
- [F] **IO 예측(C9 연결)**: 5,095 → **5,839**(+744; 재관측 `reobs/c9r`). 첫 정지는 D 6 run(FR10)과 C 2 run(C10 `223fa`, X4 68 frame 520 / X4 94 frame 360). [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다.
- [F] 원래 IO 관측은 C9 코드를 실행하지 않는다(계획 §10.8.4). 일치 173,966은 그대로여야 한다.

## 공통 규칙·native 검증 계획

FR2..FR9, C1~C8 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_player_c9.cpp`, 함수 `animation_player_c9_block`. 오류 문자열은 `unsupported animation player c9 PC`(범위 안 내부 PC 직접 진입), `player c9 caller requires known carry`(C 소비 block에 Unknown C; 소비자 14개), `unsupported animation player c9 jump target`(결정 2의 목록 밖 A1), `unsupported animation player c9 flag source`(결정 3의 `22180` N 출처) 네 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(20 범위, C8 줄 뒤; `)ok=animation_player_c9_block(c);`를 같은 줄에 둔다), `carry_preserving_pc`의 C8 묶음 뒤에 주석 달린 case 묶음 하나(소비자 14), `animation_machine_internal.h`에 선언 하나(C8 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# player C9 refresh:` 주석), IO 검증기 pin 표(결정 5). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 위 명세의 곧바로 들어감 6개는 쓰고 그 값으로 들어가고, `1fb28`(`1ec74`) `1f52e`(`1f3e8`) `1ed18` `1f11c` `20d62`는 쓰고 다음 block으로 가며(dispatcher가 다음 frame에 들어감), `20be8`(`20c30`)은 쓰기만 한다.
- **자료 읽기**(live bus): node field(A6: BYTE `15` `19` `5e` `5f` `7e` `9c` `9d` `9e` `a5` `a6` `a7` `aa`, WORD `1e` `2c` `42` `46` `76` `88`, LONG `36` `3a` `46` `8c`), 이동 기록 A0(LONG `4` `8`), `ea680`의 A0(LONG / WORD `18`), `4970a`의 자식 A0(WORD `76` 쓰기), 기록 A4 = LONG `8c(A6)`(BYTE `4`), 고정 ROM(위 "계산 점프와 목록"). 단위 시험은 고정 ROM 자료 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): WORD 표 `1b170`..`1b17f`(`20aa4` `21376` `2138e`), LONG 표 `22028`..`2210b`(`2218c`), WORD 표 `1b764`(C2 `1cb08` 사슬), BYTE 표 `21ba6`(C3 `21baa` 사슬), 목록 `21aee` = (`21602`, 3) (`21d60`, 0) (`21e48`, 5) (`21e3a`, 1), 0과 `216c8` = (`21602`, 2), 0(handler는 ROM과 같고 key가 다름; C3 `215e6` 사슬). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W #k`, `MOVE.W d(An)`, `AND.W`, `ADD.W`/`SUB.W`(레지스터·메모리 WORD), `ASR.W`, `MOVE.B`, `SEQ.B`/`SUB.B`/`OR.B`(레지스터 BYTE), `ANDI.B`(메모리 BYTE), `SPL.B`). `MOVEQ`·`MOVE.L`·`MOVEA.L`·`LEA`·`CLR.L`·`ADD.L`·`SUB.L`·`ADDQ.L`·`ASR.L`·`SWAP`은 LONG 전체(mod 2^32). 비교: `CMPI.B #k`·`TST.B`(BYTE), `CMPI.W #1,D1`·`TST.W`·`CMPI.W #28`(WORD, 마지막은 무부호), `SUB.L`+`BMI`(LONG bit 31), `TST.B`+`BLE`/`BGT`/`BLT`(부호 BYTE). bit: `BTST/BSET/BCLR/BCHG #n,d(A6)`(메모리 BYTE, bit mod 8), `BTST #n,D0`(LONG bit n: 0 1 4 5 6 7 9 11).

## IO 검증기의 알려진 관측 pin 표(결정 5)

- [F] **변경**: `tools/verify_animation_machine_io.py`의 상수 `OBS_FILE_SHA_PREFIX` / `OBS_COMPARED_SHA`를 표 `KNOWN_OBSERVATIONS`로 바꿨다. 두 상수는 `historic` 항목의 값으로 남는다(같은 이름의 import 호환).
  - `historic`: 파일 SHA 앞 16자 `66d30130d8a11a86`, compared_sha256 `4bb6b9336274742a492182b8a745f48a574ba456aa94856c535395f89f969b62`, 음성 검사 run `P1` case 0(이전의 고정 선택).
  - `io-ext`: 파일 SHA 앞 16자 `9da40ac6dcbea3eb`, compared_sha256 `b5d15d4fcd53555bce3f4773c8ee6113c6b79ee5aac113f6c1e59a87ddc57161`, 음성 검사 run `P1` case 94.
  - `--observation`의 `observation.json` 파일 SHA가 표의 한 항목 앞자리와 같고 저장된 `compared_sha256`이 그 항목과 같아야 한다. 아니면 이전처럼 오류로 멈춘다. 나머지 검사(compared_sha256 재계산, observer 파일 SHA = `pins.observer`, ROM, seed pin, 기록·state pack SHA)는 그대로다.
  - 음성 검사: 항목의 `negatives`가 가리키는 run이 관측에 없으면 오류다(필수). 이전 코드는 `P1` case 0이 없으면 조용히 건너뛰었다. 확장 관측에는 `P1` case 0이 없어 그대로는 `negatives_ok` = null이었다(계획 §10.6). [F] 확장 관측의 대조군 `P1` case 94 frame 5에서 음성 검사 전부(RAM·queue·IRQ·palette·forged 결과·guard 증거 4개·malformed)가 검출됐다(scratch `tools/neg_probe.py`). `P1` case 68은 `palette-not-attached` 하나가 검출되지 않아(`trial_logs/neg_probe_ext_P1_68.log`) 94를 골랐다. 그래서 확장 관측도 음성 검사를 **필수**로 두고 `negatives_ok`가 true다.
  - 기록: `historic`이 아닌 관측이면 `verification.json`의 `inputs.observation`에 `pin`(이름)과 `negatives`(`P1/94`)를 더한다. `historic`의 `verification.json` 내용은 바꾸지 않는다. `run_info.json`과 stdout 요약에는 언제나 `observation_pin`을 남긴다(비교 대상이 아닌 파일).
  - 검증기 머리 docstring에 짧은 설명을 더했다.
- [F] **원래 관측의 결과가 같음**(C9 실행부를 넣기 전, `main` engine 그대로): 같은 작업 트리에서 `main`의 검증기(`git show HEAD:tools/…` 임시 사본, 실행 뒤 삭제)와 pin 표 검증기를 각각 원래 관측 전체로 돌렸다(`--workers 5`). `verification.json` SHA256 `9d03bb6ebfbb94f9…`, `frontier.json` `86cc83aac206c7a5…`로 **두 파일 모두 바이트 단위로 같다**(`trial_logs/io_hist_pintable_mainengine.log` `io_hist_mainverifier_mainengine.log`). 이 비교에서는 `inputs.tools['verify_animation_machine_io.py']`도 같다(둘 다 작업 트리의 검증기 파일 SHA를 기록하므로). 계획의 `obs2/io_historic`(다른 작업 트리, `main` 검증기)와는 `inputs.tools['verify_animation_machine_io.py']`(도구 자신의 SHA)와 `inputs.seed.seed_dir`(작업 트리 경로)만 다르다(`tools/jdiff.py`).
- 확장 관측 IO 명령(메인 runner용): `MS5_SEED_DIR=artifacts/stage_entry_body .venv/bin/python tools/verify_animation_machine_io.py --observation artifacts/animation_machine_io_ext/observation.json --out <scratch 출력> --workers 1`(`ms5-scratch/tools/verify_unit.py`의 `ioext` 단계와 같은 인자).

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `2622b7a2374959c551dea03156bc48ab1f7995118a1c1664e80e30ad36d443c5` → `48ba3f29953b656d51b1cebe03f18c3004fa0fb011070b0ea8527d5e94b617c3`, `animation_machine_internal.h` `57606da7148c24cc37efdec0560ea0f8a6ec6ce95932953f63cd8012c1499662` → `d8918d505ee9dde426c93f8b26ec19f8d4893f59867cce33a6017947e20a3058`(옛 값은 `# player C9 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 작업 트리에서 확인했다(`work/pincheck.py`, `trial_logs/pincheck_tree.log`).
- [F] **C3·C4·C5·C8 시험 생성기·시험**(오류 행; 이전 = 그 PC에서 `unsupported animation machine PC`. C9가 그 PC를 routing해서 C++가 C9 코드를 실행하므로 바뀜. 원래 뜻(실패 PC)을 지키는 C5~C8 선례 방식):
  - C3 `error-slot-listed-2210c` / `-22452`(`201a2 JSR (A4)`): node를 `1fff70`(위쪽 RAM 거울, LONG `84(A6)` = `1ffff4`)에 둬서 C9 block의 첫 접근(`BCLR #5,a7(A6)` / `MOVE.B 9c(A6),D0`)이 bank 창 `200017` / `20000c`를 읽게 했다 → `missing or ambiguous physical program bus ROM byte`, 실패 PC `2210c` / `22452` 그대로. `21620-listed-21e48`: A6 := 0 → C9 `21e48`의 `MOVE.B #1,aa(A6)`가 고정 ROM에 써서 `unsupported animation machine write device`, 실패 PC `21e48` 그대로.
  - C4 `error-21c72-listed-21e48`, C5 `error-21f7c-listed-21e48`, C8 `error-entry-21d9e-21e48`: 같은 A6 := 0, 실패 PC `21e48` 그대로.
  - C5 `error-208f2-then-208fa`·`error-21f8a-then-2210c`: A7 홀수 → C9 `208fa`의 `JSR ea680.l`·`2210c`의 `BSR.W 1cd98`이 `program bus requires even WORD/LONG address`, 실패 PC 그대로.
  - C8 `error-1f45c-then-1f48a`·`21e52-then-21d0e`·`21e7c-then-223a0`·`21e84-then-223d6`·`21e8c-then-2210c`: A7 홀수(각 C9 block의 첫 `BSR.W`), `error-1fb1e-then-1fb28`: A6 홀수 → `1fb28 MOVE.L #1ec74,(A6)`이 `invalid animation machine write size/alignment`, 실패 PC 모두 그대로.
  - C8 시험 손 규칙(`21d9e` A1 = `21e48`): "21e48 is not routed … declared-stop error" → `21e48`에 도착(runs_to)과 A6 := 0의 `unsupported animation machine write device` 두 규칙.
  - 생성기 넷을 다시 돌려 그 행만 바뀜을 확인했다(`work/before/` 대비 diff: C3 3행(행 순서 이동 포함), C4 1행, C5 3행, C8 7행). 시험 줄의 fixture 수는 C8 기록과 같다(pc3 1,293, pc4 1,372, pc5 1,184, pc8 683).
- [F] **motion walk 시험 `engine/tests/animation_machine_motion_walk_test.cpp`**: 기록 type `7ffe`(18c06 dispatcher 표 `18c0e + 7ffe` = `20c0c`)는 이제 C9 내부 PC라 `unsupported animation player c9 PC`가 된다. 이전 기대값(`unsupported animation machine PC`)의 뜻을 지키도록 type을 `7ff0`(대상 `20bfe`, C9 범위 `20a4a..20bfe` 바로 뒤의 routing 밖 뒤 단위 시작)으로 바꿨다(주석에 이전 값과 이유). motion walk 검증기의 oor guard 대상(`18c0f` `18cb4` `20f00` `10fda` `192cb` `18d0c`)은 C9 범위 밖이다.
- [F] **scene update 시험 `engine/tests/animation_machine_scene_update_test.cpp`** `path_policy`: 경로 opcode `7fbe` / `7fc0`(대상 `19e8a + op` = `21e48` / `21e4a`, C8이 고른 값)은 이제 C9 시작 / 내부 PC다. 이전 기대값의 뜻("executor 밖")을 지키도록 opcode를 `7f7a` / `7f7c`(대상 `21e04` = routing 밖 칸 `84` 값, `21e06`)로 바꿨다. scene update 검증기의 guard `7ffe` → `21e88`은 C8 내부 PC 그대로라 바뀌지 않는다.
- [F] **V1 spec**:
  - `ROUTED_LATER`(선언 정지로 그대로 둠, C2~C8이 쓴 방식): pc3 += `21ca4` `21d0e` `2210c` `223a0` `223d6`; pc4 += `1f070` `21ca4` `21d0e` `2210c` `223a0` `223d6`; pc5 / pc6 / pc7 += `208fa` `2210c` `1f070` `223a0` `223d6` `21ca4` `21d0e`; pc8(이전 빈 목록) := `1f48a` `1fb28` `21d0e` `2210c` `223a0` `223d6` `208fa` `1f070` `21ca4` `21e48`. `EXIT_STOPS`에 C9 PC가 있는 spec은 pc3~pc8뿐이다(전수 검색).
  - pc8: `JMP (A1)` `21d9e`의 목록 handler `21e48`이 이제 C9 시작이라 `OTHER_JUMP_PCS` 규칙(routing 밖 대상만 정지)이 그 run을 C9 안으로 이어 가게 된다. C8 fixture를 그대로 두려고 `21e48`을 `EXIT_STOPS` 끝에 더하고 `ROUTED_LATER`에 넣었다(`UNIT_EXITS = EXIT_STOPS[:8]`은 그대로). `require(unit_of(0x21e48) is None)` → `in (None, c9)`.
  - pc3 / pc4 / pc5: 계산 점프 대상 검사(`SLOT84`·`LIST_21622` / `LIST_21AEE` / `LIST_21B26`)가 C9 routing을 허용하고, `JUMP_ROUTED` 일치 검사에서 C9 `21e48`을 뺀다(그 run에서 `21e48`은 선언 정지로 남음). 오류 fixture: pc3 `201a2-slot-listed-*`의 값 (`2210c`, `22452`, `21664`) → (`21664`, `2173c`)(C4가 `21d60`에 쓴 방식: 아직 routing 밖인 목록 값으로 바꿈; fixture 2개 감소), `21620-a1-listed-21e48`·pc4 `21c72-a1-listed-21e48`·pc5 `21f7c-a1-listed-21e48`(A6 := 0, `unsupported animation machine write device`, 실패 PC `21e48`), pc3 `21610-then-21e48`·pc4 `21c66-then-21e48`·pc5 `21f70-then-21e48`(BYTE `9d` := 1 → C9 `21e48` → C8 `21e52 BGT` → routing 밖 `21ea0`; 실패 PC `21e48` → `21ea0`, C8의 `1eb98` → `1ebbe`와 같은 처리), pc5 `208f2-then-208fa`·`21f8a-then-2210c`(A7 홀수), pc8 `21d9e-a1-21e48-entry`(A6 := 0), `1f45c-then-1f48a`·`21e52-then-21d0e`·`21e7c-then-223a0`·`21e84-then-223d6`·`21e8c-then-2210c`(A7 홀수), `1fb1e-then-1fb28`(A6 홀수).
  - V1 회귀는 모두 C8 기록과 같은 fixture 수로 통과했다(pc3만 1,831 → 1,829, 위 이유). 아래 "검증 수치".
- [F] 바뀌지 않음(확인): C1·C2·C6·C7 시험, objects n04 시험의 `22118`·motion walk 시험의 `2211c`(레지스터 값), 다른 단위 소스의 주석(C3 `PC3_LIST_21622`, C8 `PC8_LIST_21B0A`의 "21e48 is not routed" 주석; 다른 검증기가 그 소스 SHA를 pin할 수 있어 고치지 않음). 저장소 tools·시험에서 C9 범위 안 PC를 쓰는 다른 곳은 위 항목뿐이다(전수 검색 `tools/c9refs_repo.py`, 5자리 16진 literal).
- [I] 원래 IO 관측과 frame 비교(d1·controller·irq·demo)는 C9 코드를 실행하지 않으므로 결과가 같아야 한다. 메인 runner가 확인한다.

## 결정

1. **범위: 계획 그대로 220 block, 20 범위. 숨은 직선 block 추가 없음.** C9를 실제로 routing한 정확 bitmap 재관측의 기록이 계획의 `v2_u1`과 같고, 새로 보인 routing 밖 PC가 0이며, 예측 5,839와 첫 정지가 계획과 같다. 범위 끝의 실행 PC `1f082` `20bfe` `22148`(조건 분기의 fall-through)과 `22286` `223fa`는 계획대로 C10의 정지로 둔다.
2. **`JMP (A1)` 네 곳: A1이 ROM 목록 `21aee` / `216c8`의 handler면 그 PC로, 그 밖은 checked jump-target 오류.** C3 `21620`·C4 `21c72`·C5 `21f7c`·C8 `21d9e`와 같다. 목록 비교는 LONG 전체.
3. **flag.** C 소비자 14개는 known C를 읽거나 checked 오류. C9 block은 C를 만들거나 넘기지 않는다(뒤는 Unknown). `22180`은 N을 BYTE `9d(A6)`에서 다시 계산하고, 그 주소가 work RAM / 고정 ROM이 아니면 checked flag-source 오류(C1·C5·C6과 같은 규칙).
4. **정수 연산.** `ASR.L #3` / `ASR.W #3`은 부호 채움(UB 없는 무부호 계산), settle의 `SUB.L`+`BMI`는 LONG bit 31, `SPL`은 N만, `20bd6`은 WORD 연산과 무부호 비교, `20d3c`의 BCC는 WORD borrow.
5. **IO 검증기 pin 표.** 위 절. 원래 관측의 `verification.json`·`frontier.json`은 바이트 단위로 같다. 확장 관측의 음성 검사는 `P1` case 94로 필수.
6. **V1 natural family.** 확장 관측의 state pack을 spec 안의 `io_pack`(관측 폴더 `IO_EXT` = `artifacts/animation_machine_io_ext`)이 읽는다. 공용 loader는 바꾸지 않았다. 플레이어 node `100cb8`의 callback LONG이 C9 설치 값이거나, 칸 `84` LONG이 C9 칸 값이고 callback이 routing된 frame 44개(`work/natscan_c9.out`에서 run·값마다 앞 frame)를 쓴다.
7. **뒤 단위 정지와 앞 단위 spec.** C9 block이 닿는 C10 PC 5곳과 C1~C8의 남은 정지 16곳을 V1 `first_unrouted`와 실제 ROM 차분의 선언 정지로 둔다. pc3~pc8의 `EXIT_STOPS` 가운데 C9가 routing한 PC는 `ROUTED_LATER`로 허용하고 선언 정지로 그대로 둔다.
8. **다음.** C9 연결로 확장 관측 IO 5,839(+744)를 메인 runner가 확인한다. 원래 관측 IO는 173,966 그대로여야 한다. 다음 단위는 FR10(계획 순서).

## 미확인

- [U] node field·전역 값의 의미(BYTE `15` `19` `5e` `5f` `7e` `9c` `9d` `9e` `a5` `a6` `a7` `aa`, WORD `2c` `42` `46` `76` `88`, LONG `36` `3a` `46` `8c`, 표 `1b170` `1b178` `22028` `22074` `220c0`, 기록 `1b1ec` … `1b964`). 이름(입력 상태, 지면·공중, settle, 방향 진입)은 동작에서 붙인 [I]이다.
- [U] `ea680`의 Set 쪽(지형 탐색이 땅을 찾음)은 V1 사슬 fixture로 만들지 못했다(무작위 world에서 U18 탐색이 늘 Clear; `tools/v1probe_chain.py`). 소비자 `20900` `20a50` `20bd2`의 Set 쪽은 선언 C 행(단위 시험), natural fixture(확장 관측 pack)와 실제 ROM 차분으로만 확인했다. `20bd2` → `20bd6`(Set 쪽)은 IO 관측에서도 실행되지 않았다.
- [U] `21cbe`의 Set 쪽(`223b2`)은 실제 생산자 `21c1c`가 늘 Clear라 선언 C로만 확인했다(V1 `STATIC_IMPOSSIBLE`).
- [U] IO 관측에서 실행되지 않은 이 단위의 block 94개는 closure로 들어왔다(V1 선언 상태·natural·실제 ROM 차분·단위 시험으로만 확인).
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC).
- [U] natural fixture의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C8과 같음).
- [U] `default-settings` 선언(계획 §10.9)과 확장 관측의 입력 script가 실제 기계와 같은지는 이 단위가 다루지 않는다.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_player_c9.cpp`(case label 220 = `starts_C9.txt`와 집합 일치; 공용 함수 `pc9_get` `pc9_put` `pc9_bit`(메모리 BYTE bit; 0 시험, 1 세움, 2 지움, 3 바꿈) `pc9_field_bit` `pc9_input_bit` `pc9_byte_is` `pc9_mask` `pc9_carry` `pc9_field_call` `pc9_install` `pc9_slot84` `pc9_slot` `pc9_asr` `pc9_asr_word` `pc9_child` `pc9_table_sound` `pc9_settle` `pc9_settle_x` `pc9_settle_y` `pc9_turn` `pc9_list_jump`, 목록 `PC9_LIST_21AEE` `PC9_LIST_216C8`), `engine/tests/animation_machine_player_c9_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_d`), `tools/generate_animation_machine_player_c9_test_table.py`(생성기; C8 생성기 꼴, single 5 = N 읽는 `22180`(native SR N = BYTE `9d(A6)` bit 7), 계산 점프 착지 검사 `JUMP_ALLOWED` = 네 목록, V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 100초), `tools/unit_fixture_specs/pc9.py`(V1 spec; C8 spec의 공용 부분 그대로(scratch `work/mkpc9.py`가 조립), 단위 부분 교체, `EXIT_STOPS`(21), `CONSUMERS`(14), `Z_READERS`(`22180`), `STATIC_IMPOSSIBLE`(`21cbe` → `223b2`), `LIST_JUMPS`(trace가 목록 밖 착지를 버림), natural family는 확장 관측 pack(`io_pack`, `IO_EXT`)). 공유 수정은 "공통 규칙"·"IO 검증기"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `starts_C9.txt`(SHA256 `7297354e…`).

- **`1d086..1d09e`(4)**: `1d086 1d08a 1d092 1d096`
- **`1ec74..1ed22`(22)**: `1ec74 1ec7e 1ec8e 1ec98 1eca0 1eca4 1eca8 1ecb8 1ecbc 1ecc6 1ecce 1ecd8 1ece0 1ecea 1ecee 1ecf6 1ecfe 1ed04 1ed0e 1ed14 1ed18 1ed1e`
- **`1f070..1f082`(1)**: `1f070`
- **`1f086..1f126`(19)**: `1f086 1f08a 1f0ae 1f0b2 1f0bc 1f0c4 1f0ce 1f0d6 1f0e0 1f0e4 1f0ec 1f0f4 1f0fe 1f102 1f108 1f112 1f118 1f11c 1f122`
- **`1f3e8..1f3ec`(1)**: `1f3e8`
- **`1f48a..1f538`(21)**: `1f48a 1f492 1f4b6 1f4ba 1f4c4 1f4cc 1f4d6 1f4de 1f4e2 1f4ea 1f4ee 1f4f6 1f500 1f508 1f510 1f514 1f51a 1f524 1f52a 1f52e 1f534`
- **`1fb28..1fb2e`(1)**: `1fb28`
- **`20720..20738`(1)**: `20720`
- **`208fa..2092c`(8)**: `208fa 20900 20904 2090a 20912 2091a 2091e 20924`
- **`20a4a..20bfe`(41)**: `20a4a 20a50 20a54 20a6e 20a7e 20a80 20a8e 20a90 20a98 20a9e 20aa4 20abc 20ac4 20aec 20af4 20afc 20b00 20b10 20b12 20b20 20b22 20b28 20b2e 20b38 20b3e 20b42 20b48 20b50 20b60 20b66 20b6e 20b96 20b9e 20bb4 20bb8 20bc4 20bcc 20bd2 20bd6 20be8 20bee`
- **`20c00..20c30`(7)**: `20c00 20c0e 20c10 20c16 20c1c 20c26 20c2c`
- **`20cd8..20d72`(11)**: `20cd8 20ce8 20cf6 20d02 20d0a 20d36 20d3c 20d44 20d54 20d62 20d6e`
- **`21370..213da`(6)**: `21370 21376 2138e 213a6 213b4 213d0`
- **`21ca4..21d60`(28)**: `21ca4 21cae 21cb2 21cb6 21cba 21cbe 21cc2 21cca 21cd8 21ce0 21ce4 21ce6 21cea 21cf2 21cfa 21d02 21d0a 21d0e 21d1c 21d2a 21d32 21d36 21d38 21d3c 21d44 21d4c 21d54 21d5c`
- **`21e48..21e52`(1)**: `21e48`
- **`2210c..22148`(3)**: `2210c 22116 22128`
- **`22174..221ca`(8)**: `22174 22180 22188 2218c 221a2 221b2 221ba 221c2`
- **`22238..22286`(13)**: `22238 22240 22248 2224c 2224e 22252 2225a 22262 2226c 22272 22276 2227c 22284`
- **`223a0..223fa`(10)**: `223a0 223ae 223b2 223c0 223c4 223d2 223d6 223e4 223e8 223f6`
- **`22408..22472`(14)**: `22408 2241c 22424 22428 2242a 2242e 22436 2243e 22442 22448 22450 22452 22468 2246e`

## 검증 수치

작업자 최종 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j6 all test`(최종 실행부·시험): 종료 0, 경고 0, Python 310 OK(`trial_logs/make_final.log`). C9 시험 줄: `animation machine player pc9: 1678 fixtures (1210 single-block, 313 path, 48 producer chain, 28 declared C, 79 checked error (11 with a later failing PC), 70 kept C), 220 blocks, 7089 calls, 307318 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 출구 중 stop이 아닌 것 0, 실제 사슬 두 값 8개(`1ec98`→`1eca0`(`1cb08`, 합성 표 `1b764`), `21ca4`→`21cae`(`21bc6`), `21cb2`→`21cb6`(`21baa`, 합성 표 `21ba6`), `21cd8`→`21ce0` `21d2a`→`21d32` `22240`→`22248` `2241c`→`22424`(`215e6`, 합성 목록), `22174`→`22180`(N)). `49fc6` 사슬 셋은 `49fc6`이 bank 장치에 써서 native run이 버려졌고, `ea680` 사슬 셋과 `21cba`→`21cbe`(`21c1c`)는 Clear만 나와 선언 C 행만 있다. `JMP (A1)` 행이 목록 handler 넷(`21602` `21d60` `21e3a` `21e48`)에 모두 멈춘다. 생성기를 다시 돌려 C3·C4·C5·C8·C9 시험 파일이 바이트 단위로 같음을 확인했다(`trial_logs/gen_repro_*.log`). 다른 player 시험 줄의 fixture 수는 C8 기록과 같다(pc3 1,293, pc4 1,372, pc5 1,184, pc6 1,248, pc7 1,270, pc8 683).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, `work/ubsan.sh`, C9 시험): 빌드 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_build.log` `ubsan_player_c9.log`).
- [F] V1 pc9(작업자, `--workers 2`, 두 번): fixture 2,347개(block 1,331, chain 26, node 25, natural 44, callee 73, error 831, failpc 7, negative 10) failed 0, 방문 시작 220/220, carry oracle Unknown/Clear/Set = 1,482/14/10, 두 실행의 digest `da3660d2b456fa56`로 같음(`trial_logs/v1_pc9_final_A.log` `_B.log`). spec 보고의 빠진 후속 `20900`→`20904` `20a50`→`20a54` `20bd2`→`20bd6`과 도달 못한 결과 `20bd2`→`20bd6`은 `ea680` Set 쪽이다(미확인 절). 첫 시도는 callee `20a98` `20b42` `20cd8`의 무작위 world가 native에서 깨끗이 멈추지 않아 build 단계에서 멈췄고, 세 callee를 뺐다(block fixture가 덮음).
- [F] V1 회귀(작업자, `work/v1_regs.sh`): pc1 1,264, pc2 1,743, pc3 1,829, pc4 1,873, pc5 1,755, pc6 1,856, pc7 2,077, pc8 986, se1 2,102, fr1 1,631(모두 failed 0; pc3의 −2는 "영향받는" 절의 `201a2-slot-listed` 값 변경, 나머지는 C8 기록과 같음, `work/v1_regs.txt`). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·op, WORD/BYTE → LONG, 복귀 PC·호출 대상, carry tag, mask, 상수·설치 값, `pc9_*` helper 인자) + 손으로 고른 helper·block 변이(`ASR.L`/`ASR.W` 채움·count·부호, settle의 부호·순서·`ADDQ #7`·폭, `JMP (A1)` 목록·비교 폭·guard, flag-source guard와 그 24 bit, `SPL`의 N·부호 있는 비교·폭, `20bd6`의 SWAP·WORD·무부호, `22116`/`22452`의 SEQ·SUB.B·OR.B, 표 첨자의 부호 확장·배수, `20d3c` borrow 등) + dispatcher carry 목록 14개·추가·범위 10개를 적용해 만든 것, 674개; `--workers 8`): 1회째 `killed 651 of 674`(`trial_logs/mut_first.log`). 생존 23개 중 10개는 시험 빈틈이었고 규칙 `rules_d`로 메웠다(`20bd6`의 WORD 폭·SWAP 뒤 위 WORD, `22180`의 24 bit 주소(guard 변이 둘), `2218c` WORD 첨자, `2226c` 읽기(필드·제거), `22408`의 BYTE `aa`, `213a6`의 BYTE 읽기(홀수 A6), `221a2`의 A4 다시 읽기; `trial_logs/mut_gaps.log` 등). 남은 13개는 동치다(`mut/equivalents.txt`, 사례별 이유: mask `c`/`50`이 남기는 bit가 하위 BYTE 1, 즉치 count 3 2, 채움 경계 bit가 원래 부호 bit 2, `MOVEQ #0`이 덮는 값 3, 음수가 될 수 없는 첨자 1, 읽히지 않는 BTST의 Z 1, `pc9_bit`의 상수 bit 1, `am_write`의 자체 mask 1, 양수 변위의 부호 확장 1). 규칙을 더한 뒤 전체 2회째 `killed 661 of 674`(`trial_logs/mut_second.log`), 남은 13개가 동치 목록과 같다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`, 메인 runner용), `real_pc9.py`(C8 harness에 C9 world(`pc9_world`)·소비자 14·N 읽는 `22180`(native SR N = BYTE `9d(A6)` bit 7)·선언 정지(pc9 `EXIT_STOPS`); C9 `JMP (A1)`의 착지를 trace 전체에서 대조하는 분류 `JUMPTGT9` 추가; `native_safe` 기본 유지)): 작업자 300건 seed 1 `mismatches 0`(`covered starts 186 of 220`; 문서화된 분류는 C3 jump-target 29건(무작위 칸 `84` LONG의 `201a6`)뿐; 깨끗이 멈추지 않은 native 34건 건너뜀; native oracle abort 0, `trial_logs/real_n300_s1.log`). 앞선 50건 seed 11 시험도 `mismatches 0`(`trial_logs/real_t50.log`).
- [F] **IO, 원래 관측**(C9 연결 뒤, `--workers 5`): run 296, 일치 **173,966** / 173,966, 불일치 0, C++ 오류 0, chain divergence 0, 수용 키 모두 true(`negatives_ok` 포함)(`trial_logs/io_hist_c9.log`; `verification.json` SHA256 `d4ae0ecf8bf5666d…`, `frontier.json` `c4cf020fb54375e5…`). C9를 넣기 전(`main` engine, pin 표 검증기)과 비교하면 `verification.json`은 `inputs`의 engine source·header SHA(`animation_machine.cpp` `animation_machine_internal.h`, 새 `animation_machine_player_c9.cpp`), harness binary SHA, routing SHA·atom 수(1,253 → 1,273), `tools/verify_animation_machine.py` SHA만 다르고, `frontier.json`은 `routing_file_sha256`만 다르다(`tools/jdiff.py`). 결과 필드는 모두 같다.
- [F] **IO, 입력 확장 관측**(C9 연결 뒤): run 12, native 비교 frame 14,500 가운데 일치 **5,839**(예측 5,839, 기준선 5,095 → +744), 불일치 0(beyond 0), C++ 오류 0, chain divergence 0, 수용 키 모두 true(`negatives_ok` 포함, `P1` case 94)(`trial_logs/io_ext_c9.log`; `verification.json` `3d2d0c36f097d933…`, `frontier.json` `3c50a45d5274d963…`). 구성별 일치 P0 1,200 / P1 1,200 / X1 796 / X2 795 / X3 968 / X4 880. 첫 정지(확인된 frontier): X1 68 frame 501·X1 94 295 `6f1ca`(D), X2 68 504·X2 94 291 `eaac0`(D), X3 68 591 `252b4`(D), X3 94 377 `71468`(D), X4 68 520·X4 94 360 `223fa`(C10) — 재관측 예측(`reobs/c9r.stops`)과 run·frame·PC가 모두 같다.
- [F] `CPP_PINS`: 작업 트리와 scratch clone root(`work/mkroot.py`: 작업 트리 clone + 변경 파일 복사 + 공유 자료 symlink; 확인 뒤 symlink를 먼저 지우고 삭제)에서 파일 SHA와 같다(4 / 9 pin, 불일치 0, `trial_logs/pincheck_tree.log` `pincheck_root.log`).

## 검증 기록(검증 실행: 결정적 runner + 메인 검토)

- [F] `make -j6 all test`: 종료 0, 경고 0, Assert 0, Python 310 OK. C9 시험 `animation machine player pc9: 1678 fixtures (1210 single-block, 313 path, 48 producer chain, 28 declared C, 79 checked error (11 with a later failing PC), 70 kept C), 220 blocks, 7089 calls, 307318 checks`.
- [F] `ubsan`: 빌드/실행 종료 0, 런타임 오류 0.
- [F] `mutation`: 변이 674, 제거 661, 등가 13.
  - 이 실행 전에 메운 시험 빈틈 10개.
- [F] real-ROM: 배치 `f4`, `f5`, `s1`, `s2`, `s3` 커버 `220`, `220`, `220`, `219`, `219`; 불일치 `0,0,0,0,0`(합집합 220/220).
  - 오라클: `native_safe` 켬.
- [F] V1: A/B 각각 fixtures 2347, failed 0, identical true(digest `da3660d2b456fa56`); regression specs 42개 모두 failed 0.
- [F] legacy verifiers: `stage_entry`, `area_clear`, `stage_event`, `stage_event_ops`, `frame_helpers`, `card_menu_close`, `input`, `scene_core`, `scheduler`, `objects_g1` 모두 종료 0. `objects_g1` 판정은 C1과 같다.
- [F] frames: `d1` 완료 54400/54400, 불일치 0; `controller_game` 완료 54400/54400, 불일치 0; `irq` 완료 54400/54400, 불일치 0; `demo` 완료 45684/45684, 불일치 0.
- [F] IO(원래 관측): 일치 합계 173966, 기준 173966, 차이 0, 불일치 0, C++ 오류 0, 실행 2, 동일함; 설정별 `P0` 81600, `P1` 81600, `P1b` 8400, `boot-demo-0` 577, `boot-title-idle` 600, `boot-title-start` 906, `fx-bios-call` 3, `fx-c-input-read` 3, `fx-n-input-read` 3, `fx-queue-short` 1, `fx-start-c79a` 273.
  - 수락 항목은 모두 true이고, native frame 173,966 전부 일치한다.
- [F] IO(확장 입력 관측): 일치 합계 5839, 기준 5095, 차이 744, 불일치 0, C++ 오류 0, 실행 2, 동일함; 설정별 `P0` 1200, `P1` 1200, `X1` 796, `X2` 795, `X3` 968, `X4` 880.
  - 예측 확인: 정확한 비트맵 재관측은 5839를 예측했고, 실측도 5839이다.
  - 수락 항목은 모두 true다. native 완료 frame 14,500 중 5,839가 일치한다(나머지는 다음 단위의 첫 정지 뒤).
  - 첫 정지: `D 6f1ca eaac0 252b4 71468`, `C 223fa`(모두 이후 단위).
- [F] 검증기 변경: IO 검증 고정값을 알려진 관측 pin 표(historic, io-ext)로 변경했다. historic 관측의 출력은 변하지 않았고, io-ext의 `P1` case 94의 negative checks가 필수다.
- 검증 방법: 결정적 runner(LLM 없음). 이 기록 초안은 local Qwen이 썼고 메인이 검토·수정했다.
