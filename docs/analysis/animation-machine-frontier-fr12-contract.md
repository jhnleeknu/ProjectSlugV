# frontier 단위 FR12(입력 확장 관측의 영역 D 셋째 단위: FR10 뒤 단위 정지 `70f8e`·`b6c58`, FR4 표 칸 `cc7c0`, FR11 뒤 단위 정지 `b41f2`(MULS 회전, `c000` 미만 버림) · `b6e5e` → `b6e6e`(`49392` C) → `b518c` · `c5612`, FR11 표 `b42b8` 칸 `b42c4` → `b42ea`, FR11 `JMP (A0)` 대상 handler `b42a2`·`b4294`·`c0924` 와 `b40f8`·`b41b2`·`b402a`, kind handler `c1036`(`b4304` C → `c1064`, `c106e` 난수 각도, `c1cf2`, `c1094`..`c115a` 회전·`MULU.W #10` 구역, `2986` 자식 `b3dbc` 셋과 `MOVEM.W (A7)+,D0-D6`, `c1d06`), 설치 값 `b6ed8`·`b6fa4`·`b7096`, 표 `70d72` callback `71502`·`716ca`(`4d84e`: `MULU.W #10` 기록 → C) → `7179a`(`4945e` C) → `717c8`, `71e8c`·`71f08`, `722da`·`72352`, 212 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §10.5 표의 FR12 행(계획 이름 D-3)과 §10.x 메인 결정, FR11 계약의 메인 결정(실행되는 표 칸 `b42c4`는 FR12)을 기준으로 삼는다. 구조·공통 규칙은 FR11 계약(`animation-machine-frontier-fr11-contract.md`; 확장 관측 단위, 정확 bitmap 재관측, `MOVEM.W (A7)+`, 계산 점프 규칙), FR10 계약(`animation-machine-frontier-fr10-contract.md`; RTS로 C를 넘기는 block), C10 계약(`animation-machine-player-c10-contract.md`; 묶인 Bcc 쌍(`BUNDLED`), 뒤 단위가 routing하는 앞 단위 정지의 처리)을 따르며 다른 점만 적는다. 단위 이름은 FR12, 파일 접두어는 `objects_fr12`(C++) / `fr12`(V1 spec)다. 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다. BIOS 실행, 자연 scheduler, IRQ timing은 주장하지 않는다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 LONG(`2000d0` `2000d4` `2001a8` `2001ac`)을 live bus로 읽는다(아래). 장치 쓰기는 없다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 FR11 커밋 `b6e8475`(branch `claude/fr12-core`; C1~C10, E1, D, FR10, FR11 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `e99fe5dbc8192ae377b9384c30fa821ada4a2fbf23aeca777c81fed5f115a815`, `animation_machine_internal.h` `8cf2b547c1c11023096672ee7db3418811215596a99e907c494a91ed663b2296`(FR11 계약의 새 값과 같음).
- [F] 관측 입력(읽기 전용): 입력 확장 IO 관측 `artifacts/animation_machine_io_ext`(`observation.json` SHA256 `9da40ac6dcbea3eb…`, compared_sha256 `b5d15d4fcd53555b…`, 검증기 pin 이름 `io-ext`). V1 natural family가 이 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)으로 읽는다(C9 결정 6과 같은 방식).
- [F] 이 단위의 정확 bitmap 재관측 두 벌(scratch, 관측기 `tools/observe_animation_machine_io_ext.py` 수정 없음): `reobs/fr12base`(FR11 routing 그대로), `reobs/fr12v1`(계획 FR12 26 범위를 `--extra-routed`로 가상 routing). 결정 1.
- [F] 시작 목록: **`ms5-scratch/fr12/work/starts_fr12_final.txt`(212개, 줄마다 하나, SHA256 `2efbd8d3ada503eecbf059d7a1a6d308255d9d7dccfb8efa46b55c80f20fa4de`)**. 계획 목록 `ms5-scratch/fr12/starts_FR12.txt`(212개, 공백 구분, SHA256 `6565c7e2ab768e1d85a99d287fba2a477132ced98f551937675dc893d329001c` = 계획 §10.5의 `6565c7e2ab768e1d`)와 집합이 같다(결정 1: 범위 보정 없음). 실행부의 `case` label 212개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(V1 spec `build()`가 시작 212개 모두 `animation_objects_fr12_block`로 routing됨을 확인, `make test`의 FR12 시험이 시작 212개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr12/`
  - `reobs/run.sh`(재관측 + `dleft.py` + `runstops.py`), `reobs/fr12base` `fr12v1`(+ `.dleft` `.stops` `.log`), `plan/udetail_FR12_plan.txt` `plan/D-3.dis.txt`(계획 `xplan_v2.json`의 D-3 상세·역어셈블; `tools/xdetail.py`, `MS5_OBS2=fr11/reobs/fr11v1`), `work/fr12ranges_plan.txt`(26 범위), `work/blocklist_fr12.md`.
  - `tools/newvis_fr12.py` → `work/newvis_fr12v1.txt`(새로 보인 PC), `work/intargets.py` → `work/intargets_fr12_v1.out`(범위 안 비시작 PC로 오는 직접 분기), `tools/refs_fr12.py` → `work/refs_fr12_v1.out`(ROM 전체 FR12 시작 참조), `tools/flagscan.py` → `work/flagscan_fr12_v1.txt`(block 경계를 넘는 flag), `tools/exitflags.py` → `work/exitflags_fr12.txt`(출구·복귀 대상이 앞 코드의 flag를 읽는지), `tools/fr12exec.py` → `work/fr12exec_base.txt`(재관측의 FR12 실행 PC·run·frame), `tools/natscan_fr12.py` → `work/natscan_fr12.out` `work/natural_fr12.json`(V1 natural frame), `tools/fr12refs_repo.py` → `work/fr12refs_repo_v1.out`(저장소의 FR12 범위 literal), `work/rulecalc_fr12.py`(수작성 규칙의 기대값 모델), `work/sa_probe.py`(stage area 이웃 탐침), `work/v1_regs.sh`, `work/ubsan.sh`, `work/pincheck.py`, `work/mkroot.py`, `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위(결정 1)

- [F] **기준선**(FR11 routing, 입력 확장 관측): 예측 일치 frame **7,383**, 첫 정지 D 8 run이 모두 FR12다. FR11 계약의 IO 실측(`b6e5e` 3 run, `c1036` 2 run, `cc7c0` 2 run, `70f8e` 1 run; frame 745 / 488 / 713 / 493 / 714 / 518 / 736 / 576)과 같다.
- [F] **정확 bitmap 재관측(FR11 routing)** `reobs/fr12base`(routing `e99fe5db`): `dleft.py` 실행된 routing 밖 PC E 108 / D 378, 예측 7,383, 첫 정지 X1 68 745 `b6e5e`, X1 94 488 `b4304`..`c105e`, X2 68 713 `b4304`..`c105e`, X2 94 493 `70f8e`, X3 68 714 `b6e5e`, X3 94 518 `b6e5e`, X4 68 736 `cc7c0`, X4 94 576 `cc7c0`(`reobs/fr12base.dleft` `.stops`; FR11 계약의 가상 routing 재관측 `fr11v1`과 같음).
- [F] **정확 bitmap 재관측(FR12 가상 routing, 계획 26 범위)** `reobs/fr12v1`: 예측 일치 frame **7,977**(계획 7,977과 같음), 실행된 routing 밖 PC E 108 / D 252, 첫 정지는 8 run 모두 뒤 단위 FR13(D-4)이다: X1 68 frame 873 `70fcc`, X1 94 604 `c54ba`/`c5520`, X2 68 757 `71028`, X2 94 629 `70f60`, X3 68 760 `b44ac`/`bfcfa`, X3 94 588 `c54d6`/`c5520`, X4 68 773 `c554c`.., X4 94 593 `71f2c`..(`reobs/fr12v1.stops`; 단위 소속은 계획 `xplan_v2.json`의 D-4).
  - [F] **숨은 직선 연속 검사**: `fr12base`에 없고 `fr12v1`에만 보이는 routing 밖 PC는 **없다**(`work/newvis_fr12v1.txt`: 12 run 모두 0). 가상 routing 관측에서 실행된 FR12 범위 끝 PC `7177a` `71786`(FR14 D-5) `717c2` `717e8` `71f2c`(FR13 D-4)는 모두 기준 관측에서 이미 보였다. 반복은 한 번으로 수렴했다.
- [F] **범위 밖에서 범위 안 비시작 PC로 들어오는 직접 분기**: 없다(`work/intargets_fr12_v1.out` 8줄: `b6fa2` `b6fbc`는 `MOVE.L #v,(A6)` 즉치의 하위 WORD를 명령으로 읽은 것, 나머지 6줄은 범위 안의 `BEQ`가 묶인 `BEQ` `c113a`/`c11ec`로 가는 것; 아래 "flag").
- [F] **계획 특이 항목 대조**: MULS 6(`b41f6` `b41f8` `b422c` `b4230` `b423a` `b423e`), MULU 3(`4d856` `c1112` `c11ba`), MOVEM 3(`c123e` `c12cc` `c135c`), 자식 `b3dbc`(`c1238` `c12c6` `c1356`의 `2986`) — 모두 ROM 바이트와 같다(`plan/D-3.dis.txt`). TRAP·계산 점프 표는 없다.
- [F] **실행 칸·뒤 단위 짧은 block**: FR11 메인 결정대로 표 `b42b8` 칸 c `b42c4`는 FR12 시작이다. 계획이 FR14(D-5)에 둔 `7177a`(`NEG.L D0`, `71776 BNE`의 fall-through)와 `71786`(`NEG.L D0`, `71782 BPL`의 fall-through), FR13(D-4)에 둔 `71682` `717c2`는 그대로 뒤 단위 정지로 둔다(계획 규칙: 실행 PC의 key 순서; FR11 결정 1과 같은 처리). [I] 대안(2 byte block 둘을 FR12로 옮김)은 FR14 시작 목록을 바꾸므로 메인 결정이 필요하다.
- [F] **IO 실행**(`reobs/fr12base`, `work/fr12exec_base.txt`): FR12 시작 가운데 기록된 것 124개, 실행 3,701회(TB 첫 routing 밖 PC로 기록된 수; 계획 표의 3,717과의 차는 재관측 병합 기준의 차), run 8개. 처음 frame: X1 68 745..818, X1 94 488..546, X2 68 713..887, X2 94 493..507, X3 68 714..1,260, X3 94 518..966, X4 68 736..1,173, X4 94 576..1,013. 기록되지 않은 시작 88개는 closure로 들어왔다(같은 TB 안의 직선 연속, 또는 이 관측에서 실행되지 않는 분기 쪽: `71502`..`7155e`(`716fa`의 Clear 쪽), `722da`..`7238c`, `b6ff4`..`b70fc`, `c119a`, `c120c`..`c13aa`(`c1126`/`c1130`의 구역 0 / 2), `c1d06`..`c1d2c` 등).

## FR12 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **212 block, 611 명령, 2,664 byte, 26 범위**(시작 목록 SHA256 `2efbd8d3…`(줄 형식) / `6565c7e2…`(계획 형식), 범위 byte를 이어 붙인 SHA256 `668f8df349275736a73a4d32621be43215d43d90ca4c70e4895c5f71c988114d`). 짝수 PC 1,332(내부 1,120). 기존 routing과 겹침 0(V1 spec `build()`와 시험 `interior()`가 확인).

| 범위(CPU = 파일 오프셋) | byte | 시작 | SHA256(앞 16자) | 내용 [I] |
| --- | --- | --- | --- | --- |
| `4d84e..4d86e` | 32 | 3 | `698237e4368d04f7` | `716f4 JSR`: `ANDI.W #ff` 둘, `MULU.W #10`, `LEA 4cf64(PC),A2; ADDA.W`, `TST.W a(A2)` → Clear / `ORI.B #1,CCR` Set; RTS `4d86c` |
| `70f8e..70f94` | 6 | 1 | `96c62ea1b1b34bd9` | FR10 `70f8a BCS`: `MOVE.L #70c0c,(A6)`(쓰기만) → FR10 `70f94` |
| `71502..71562` | 96 | 5 | `4c7c8c366e61010e` | `TST.W 9c` → bank anim 3 / `2000d0` / 70 또는 b / `2000d4` / a4 → `BRA.W 71682`(FR13) |
| `716ca..7177a` | 176 | 13 | `f5a0af008278b2d1` | 표 `70d72` callback: A0 := `-7348`/`-7258(A5)`(BYTE 86), `716da`(같은 WORD 46의 차 → `BGT` 안 됨), `4d7a6`, `4d84e` C, bank anim(+4), BTST `82`/BCHG `15`, D0 := 40000 |
| `7177c..71786` | 10 | 1 | `76dfcd8e5d897dd5` | LONG 64 := D0, `TST.L D0; BPL 71788` / `71786`(FR14) |
| `71788..717c2` | 58 | 5 | `adc08178c19c9f75` | `LSL.L #6; SWAP; ADDI.W #80` → WORD 2c, 설치 `7179a`(곧바로): BTST #7,15 → `71c90` / `4945e` C → `713d8`(FR10) / WORD 42 차 + 40 ≥ 80(무부호) |
| `717c8..717e8` | 32 | 5 | `1fe8cf616e9c6bf5` | `4bfa4`, `49fc6`, BYTE 61 bit 0 → `MOVE.L #71a80,(A6)`(쓰기만), `BRA.W 72dd2` |
| `71e8c..71f2c` | 160 | 12 | `af33f391eee2d52a` | bank anim(+24), `49a58` → WORD 88 := (D0 & 3f) + 10, LONG 64 := 0, 설치 `71f08`(곧바로): `4bfa4` `49fc6` C → `MOVE.L #71f2c,(A6)`(쓰기만), `BRA.W 72d66` |
| `722da..72390` | 182 | 10 | `e54d203317a323b6` | bank anim(+20), LONG 36 := 64, 64 / 3a := 0, 설치 `72352`(곧바로): 36 += (64 − 36) ASR 5, 3a += (fff00000 − 3a) ASR 5, `4be34` `49fc6`, `MOVE.L #71e8c,(A6)`(쓰기만) |
| `b402a..b4030` | 6 | 1 | `902d2470f207afe5` | `MOVE.L A0,76(A6); RTS`(FR11 `JMP (A0)`의 handler 설치) |
| `b40f8..b4104` | 12 | 2 | `75fda0b5ceb746bd` | `JSR 4be06; MOVE.W D4,92(A6); RTS` |
| `b41b2..b41be` | 12 | 2 | `55c5802e593e8109` | `JSR 4bfa4; MOVE.W D4,92(A6); RTS` |
| `b41f2..b427e` | 140 | 12 | `b67870dc8cc0f065` | FR11 `b41e2 BNE`: `ASR.L #8`, `MULS.W D7`, D4.B 40 / c0 → 회전 생략, 아니면 표 `4411e`/`4419e` MULS 넷; LONG 36 / 3a := D0 / D1, |값| < c000이면 0 → FR11 `b427e` |
| `b4294..b42b0` | 28 | 4 | `80ed3a25f5c31c1a` | handler `b4294` / `b42a2`: BTST #7,15 → `b41b2` / `b40f8`, 아니면 `BRA.W b411c`(FR11) |
| `b42c4..b42c8` | 4 | 1 | `6e7b90e970db9a0d` | FR11 표 `b42b8` 칸 c: `BRA.W b42ea` |
| `b42ea..b4328` | 62 | 8 | `fbe086da854a6cf0` | `49a58`, `TST.B D0; BMI` → D4.B += (D0 & 1c) − c; RTS / `b4304`: LONG 76 = `b4036`/`b403e`면 `ANDI` Clear, 아니면 `ORI` Set; RTS |
| `b518c..b5198` | 12 | 1 | `1c270ed6af8133fa` | `MOVE.L A0,7e(A6); MOVE.L #b5198,(A6)`(쓰기만); RTS |
| `b6c58..b6c66` | 14 | 1 | `8ba920b98eea678b` | FR10 `b6c42 BLE`: `BCLR #0,15; MOVE.L #70000,64` → FR10 `b6c66` |
| `b6e5e..b6e8c` | 46 | 4 | `069ddb57236ac674` | FR11 `b6e5a BCS`: `MOVE.L #b6ed8,(A6)`(쓰기만), WORD 7c = ffff면 `49392`(D0.W := BYTE 9d) C → `MOVE.W #0,7c; JMP b518c` |
| `b6ed8..b6fc2` | 234 | 15 | `50f465dc5ea247b9` | callback: BTST #1,9f → `b6ff4`; 표 anim(`b7fbc`), offsets, BYTE 15 bit 0 := (WORD 82 = 1), LONG 64 := ±40000, 설치 `b6fa4`(곧바로): `b7cfa` `49fc6`, `MOVE.L #b6fc2,(A6)`(쓰기만), `BRA.W b76d2` |
| `b6ff4..b7100` | 268 | 16 | `338e854214789191` | 표 anim(`b7fcc`), offsets, `BCLR #3,61`, BYTE 9c := 8, 설치 `b7096`(곧바로): 3a += (fffe0000 − 3a) ASR 3, `4be34` `492c8` `49fc6`, `SUBQ.B 9c`, BYTE 61 bit 1 / 3, `SUBQ.W 84; BPL`, `MOVE.L #b7742,(A6)`(쓰기만) |
| `c0924..c0986` | 98 | 11 | `b882e635ae7d04b6` | handler `c0924`: LONG 64 += ((±10000 by WORD 64 부호) − 64) ASR 1, `JMP b4294`; `c0944`: `LEA b42a2; JSR b402a`, 설치 `c0956`(곧바로): `b4030`, BTST #7,15 → `MOVE.L a2(A6),(A6)`(RAM 값 쓰기만), `b4958` `b4ab0` `BTST #2,D0` → `c1d2e` / `b4334`; RTS |
| `c1036..c13c0` | 906 | 66 | `a16546335d0cd057` | kind handler `c1036`(기록 `b3484 + 140`): `c6a96`, anim `c1e3a`, `b4304` C → `c1d06` / `49a58` → `c106e`(WORD b2, `ROR.W #8; SMI; ANDI #3ff; ADDI #800; EXT; EOR; SUB` → WORD b4, LONG a2 := `c1094`, `JSR c1cf2`), `c1094`..`c115a`(회전, `LSR.W b0`, `MULU.W #10; SWAP` → BYTE b6 구역 0..f), 구역 0 / 2 → `c120c`(`2986` 자식 셋), 0..3 → `c0944` |
| `c1cf2..c1d2e` | 60 | 11 | `9d074bcda460b1d3` | `49a58`, `TST.B D0; BPL` / `BCHG #0,15`; RTS / `c1d06`: 설치 `c1d0c`(곧바로): `b4030` `b4958` `b4ab0` → `c1d2e` / `b4334`; RTS |
| `c5612..c5618` | 6 | 1 | `2738adf81304c5fb` | FR11 `c560e BCS`: `JMP 2a00` |
| `cc7c0..cc7c4` | 4 | 1 | `1d804266b6ff21b1` | FR4 표 `cc7ac`(`cc7a8 JMP`)의 칸 5: `BRA.W cd7c6`(FR10) |

- [F] **진입**(현재 routing 기준 호출자, `work/refs_fr12_v1.out`, ROM 전체 LONG 검색):
  - 설치·callback: `71502` `716ca` ← 표 `70d72`(칸 1 / 5..7)의 LONG을 `MOVE.L A0,(A6)`로 쓰는 FR2b `70d22`·N15 `711e6`·FR13 `70ff8`(FR10 계약의 "FR13의 계산 설치"); `71e8c` ← N15 `71e82`(그리고 FR12 `72386` 쓰기만); `b6ed8` ← FR12 `b6e5e`(쓰기만, 다음 frame callback); `c1094` ← `c0966 MOVE.L a2(A6),(A6)`(LONG a2 = `c1094`는 `c1088`이 씀). 범위 안 곧바로 들어가는 설치 `7179a`(`71794`) `71f08`(`71f02`) `72352`(`7234c`) `b6fa4`(`b6f9e`) `b7096`(`b7090`) `c0956`(`c0950`) `c10a0`(`c109a`) `c1170`(`c116a`) `c1d0c`(`c1d06`).
  - kind handler `c1036` ← FR1 `b3f3e`/`b3fc4 JMP (A0)`(kind 기록 `b3484 + 10·20`의 LONG 6, ROM 파일 오프셋 `b35ca`; FR1 결정 4 "routing이 판정").
  - FR11 `JMP (A0)` `b4034`의 handler(FR11 결정 2의 허용 목록): `b42a2`(FR1 `b3dec` 표 `b3dcc`, FR12 `c0944`), `c0924`(FR12 `c1160`, routing 밖 `c0fa8` `c14c8` `c1668` `c17fe` `c1a40`), `b4294`(routing 밖 `c1bb0`, FR12 `c093e JMP`). FR11 표 `b42b8`의 칸 c `b42c4` ← FR11 `b42b4`. FR4 표 `cc7ac`의 칸 `cc7c0` ← FR4 `cc7a8`.
  - 다른 실행부의 fall-through·분기: `70f8e` ← FR10 `70f8a`(BCS 쪽), `b6c58` ← FR10 `b6c42 BLE`, `b41f2` ← FR11 `b41e2 BNE`, `b6e5e` ← FR11 `b6e5a`(BCS 쪽), `c5612` ← FR11 `c560e`(BCS 쪽).
  - callee: `4d84e` ← FR12 `716f4`; `b402a` ← FR12 `c094a` `c1164`(routing 밖 `c0fac` `c14cc` `c166c` `c1802` `c1a44` `c1bb6`); `b4304` ← FR12 `c105e`(routing 밖 `c0ec8` `c13e8` `c1588` `c171e` `c193e` `c1ba6` `d8fbc`); `c1cf2` ← FR12 `c1090`(routing 밖 `c0efa` `c141a` `c15ba` `c1750` `c1970`); `b518c` ← FR12 `b6e86 JMP`.
- [F] **설치 값**(`MOVE.L #v,(A6)`): 곧바로 들어감 9개(위). **쓰기만**: `70c0c`(`70f8e`, routing) `71a80`(`717de`, routing) `71f2c`(`71f22`, FR13) `71e8c`(`72386`, FR12) `b5198`(`b518c`, routing 밖·미실행) `b6ed8`(`b6e5e`, FR12) `b6fc2`(`b6fb8`, routing 밖) `b7742`(`b70f6`, FR1). **RAM 값 쓰기**: `c0966 MOVE.L a2(A6),(A6)`(점프 아님; 다음 dispatch가 판정). `c1088 MOVE.L #c1094,a2(A6)`는 LONG 쓰기다.
- [F] **2986 자식**(`MOVEA.L #b3dbc,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986`, FR1 실행부): `c1238` `c12c6` `c1356`. 각각 앞에서 WORD 일곱(`#0 #0 #0 #0 #21 #0 #0` 순서로 push)을 넣는다. 28ae 자식은 없다.

### 계산 점프와 표(결정 2)

- [F] **FR12에는 계산 점프가 없다.** `JMP b4294` `JMP b518c` `JMP 2a00`은 절대 주소, 나머지는 `Bcc`/`BRA`/`JSR`다. 따라서 `unsupported animation objects fr12 jump target` 오류는 두지 않는다(오류 문자열 둘: 내부 PC, carry).
- [F] **FR12가 받는 계산 착지**(기존 실행부의 규칙 그대로, FR12는 그 칸을 routing할 뿐이다): FR11 `JMP (A0)` `b4034`의 handler `b42a2` `c0924` `b4294`(FR11 결정 2: 허용 목록 안, routing이 판정), FR11 `JMP b42b8(PC,D0.W)`의 칸 c `b42c4`(FR11 결정 2: 변위 0 / 4 / c), FR4 `JMP cc7ac(PC,D0.W)`의 칸 `cc7c0`(FR4 결정 2), FR1 kind handler `JMP (A0)`의 `c1036`. FR11의 다른 대상(`b4036`, 칸 4 `b42bc`, 표 `c54b2`의 26칸)은 그대로 routing 밖 정지다.
- [F] **`c0966 MOVE.L a2(A6),(A6)`**: RAM LONG을 callback 자리에 쓰기만 하고 `c096a`로 간다(점프가 아님). 이 단위에서 LONG a2를 쓰는 곳은 `c1088`(`c1094`)뿐이다 [F: 범위 안 전수]. 다음 frame의 dispatch가 그 값을 routing으로 판정한다(C++은 값을 검사하지 않음; ROM writer 밖 값은 다음 dispatch의 `unsupported animation machine PC`).
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙. [F] 원본 값은 ROM 바이트):
  - 기록 `4cf64 + 16k`의 WORD a(`4d84e`; k = D0.B 0..ff, `MULU.W #10`, `ADDA.W`는 부호 확장). [F] `4cf64..4d0a4`가 기록 20개이고 `4d0a4`부터는 코드다. k ≥ 14면 원본은 코드 바이트를 자료로 읽는다(C++도 live bus로 같은 바이트를 읽음). [F] `716ea`의 `4d7a6`(routing된 입력 실행부)은 D0 := 0(플레이어 기록 `5cba`/`5ce6(A5)`의 WORD 0 = 0 또는 `289e` Clear) 또는 그 기록의 BYTE `27`(0이면 TRAP `4d7f0`)을 돌려주고, 같은 기록 `4cf64 + 16k`의 WORD a를 D4로 읽는다. [U] BYTE `27`의 실제 범위.
  - WORD 표 `4411e`/`4419e`(`b4212`; 첨자 = 2 × (D4 & ff) ≤ 1fe, 부호 확장) — sine / cosine [I](FR11 `b4156`과 같은 표).
  - LONG 표 `b7fbc`(`b6eee`/`b6f2a`) `b7fcc`(`b7000`/`b703c`): 첨자 = D0.W(= WORD 8e) × 4(`ADD.W` 둘, WORD 안에서 넘침, 부호 확장), 그 LONG의 WORD × 4가 bank 창 LONG 표(`2001a8`/`2001ac`)의 첨자(FR10 `b6bb8`·FR11 `b67c4`와 같은 꼴, 표만 다름).
  - bank 창 LONG `2000d0`/`2000d4`(+70 / +a4 `71502`, +4 `716fe`, +24 `71e8c`, +20 `722da`): FR4 `ofr4_bank_anim`과 같은 꼴. anim 포인터 상수 `c1e3a`(`c1048`, `49f8c`로 넘김).
  - 이 표·창 값은 모두 anim 자료 포인터(A1)·첨자·판정 WORD다. 코드 주소로 점프하지 않는다.

### MULS / MULU / ASR / LSR / ROR / MOVEM(결정 3)

- [F] **MULS.W 6곳**(`b41f2` 둘, `b4212` 넷): 두 피연산자의 **하위 WORD를 부호 있는 16 bit**로 보고 곱한 **32 bit 결과**가 레지스터 LONG 전체가 된다(`ofr12_muls`: `int32` 곱, |곱| ≤ 2^30이라 넘침 없음, 무부호로 변환).
  - `b41f2`: D0 := (D0 ASR.L 8) × D7.W, D1 := (D1 ASR.L 8) × D7.W(D7 = FR11 `b41d8`의 WORD 8e).
  - `b4212`: D4.W := 2 × (D4 & ff)(`ANDI.W #ff; ADD.W`), D2 := D0 ASR 8, D3 := D1 ASR 8, D2 := D2 × cos, D3 := D3 × sin, D2 := (D2 − D3) ASR 8, D3 := D2, D2 := D2 × cos, D3 := −(D3 × sin), D0 := −(D0 − D2) + D2, D1 := −(D1 − D3) + D3. 표 WORD는 live bus로 읽는다.
- [F] **MULU.W #10 3곳**: 하위 WORD를 무부호로 × 16 한 32 bit가 D0 전체가 된다(`ofr12_mulu`).
  - `4d856`(`4d84e` block): `ANDI.W #ff` 둘 뒤라 D0.W ≤ ff — 결과는 0..ff0이고 상위 WORD가 지워진다(관측 가능: D0는 `RTS` 뒤 `716fa`..의 레지스터).
  - `c1112`/`c11ba`: D0.W 전 범위(부호 없는 곱이라 8000 → 80000), `SWAP` 뒤 BYTE b6 := 곱의 bit 16..23 = D0.W의 상위 4 bit(구역 0..f).
- [F] **ASR.L #n**(`b41f2` #8 둘, `b4212` #8 셋, `72352` #5 둘, `b7096` #3, `c0924` #1, `c10b0` #1·#5, `c10e2`/`c118a` #5): 부호 채움(`ofr12_asr`). **ASR.W #n**(`c10b0` #3, `c10e2`/`c118a` #1): 하위 WORD만, 부호 채움(`ofr12_asr_word`). **LSR.W b0(A6)**(`c10d0`, 메모리 WORD 1 bit): 논리 shift, Z는 새 WORD. **LSL.L #6/#8**(`71788` `c10b0` `c127c`..): LONG. **ROR.W #8**(`c106e`): 하위 WORD의 BYTE 교환, N = 새 bit 15(`SMI D1`이 읽음, 같은 block).
- [F] **MOVEM.W (A7)+,D0-D6 3곳**(`c123e` `c12cc` `c135c`): 낮은 주소부터 D0..D6에 WORD를 LONG으로 **부호 확장**해 넣고 A7 += 14, flag는 바뀌지 않는다(2986의 C를 바로 뒤 `BCC`가 읽음). push 순서 때문에 2986 복귀 뒤 D2 = 21, 나머지 0이다(2986이 스택 WORD를 바꾸지 않는 한 [I]). 홀수 A7은 checked 오류, Unknown C면 pop보다 먼저 checked carry 오류(FR11 `b7d8c`와 같은 순서).
- [F] **EXT.W / EXT.L**: `c0924`(SMI BYTE ff / 01 → WORD), `c106e`(D1 BYTE ff / 00 → WORD), `c10b0`(WORD → LONG), `c127c`..`c13aa`(WORD → LONG, `LSL.L #8`).

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `2986` `2a00` `49214` `492c8` `49392` `4945e` `49a58` `49f8c` `49fc6` `4be06` `4be34` `4bfa4` `4d7a6` `71c90` `72d66` `72dd2` `b4334` `b4958` `b4ab0` `b76d2` `b7cfa` `c1d2e` `c6a96`, 앞 단위 FR10 `70f94` `713d8` `b6c66` `cd7c6`, FR11 `b4030` `b411c` `b427e` `b6e8c`, RTS 복귀(`4d86c` `b402a` `b40fe` `b41b8` `b42f6` `b42f8` `b431c` `b4322` `b518c` `c0984` `c1158` `c120a` `c1d04` `c1d2c`).
- [F] **뒤 단위 정지**(실행되지만 뒤 단위가 가짐; V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS` 앞 4개): FR13 `71682`(`7155e BRA`) `717c2`(`717be BCC`의 fall-through), FR14 `7177a`(`71776 BNE`의 fall-through) `71786`(`71782 BPL`의 fall-through).
  - FR12 run이 지나갈 수 있는 FR11의 남은 정지 `b6d90` `bfcfa`, FR10의 남은 정지 `70f60` `70fcc` `70ff8` `71028`, C1~C9의 남은 정지 12개(pc10 `EXIT_STOPS[:12]`)도 fr12 `EXIT_STOPS`(모두 22개)에 넣었다. TRAP `b3e58`(FR11) `b3eac`(FR1)는 FR12 run이 FR11 handler를 거칠 때를 위해 `TRAPS`에 둔다.
- [F] 직선 fall-through로 범위를 벗어나는 곳: `70f8e`(→ FR10 `70f94`), `b6c58`(→ FR10 `b6c66`), `b427a`(→ FR11 `b427e`), 그리고 위 뒤 단위 정지(`7176a` `7177c` `717ae`의 fall-through 쪽). 재관측에서 새로 보인 PC가 없어 가려진 연속은 없다(결정 1).

### block 경계·복귀를 넘는 flag(결정 4)

FR11 방식대로 block 첫 명령부터 flag를 정하는 명령까지 훑었다(`work/flagscan_fr12_v1.txt`). 그리고 FR12 출구 대상·RTS 복귀 PC에서 FR12가 남긴 flag를 읽는 곳을 따로 훑었다(`work/exitflags_fr12.txt`; 대상 `70f94` `713d8` `b4030` `b411c` `b427e` `b6c66` `b6e8c` `cd7c6` `71682` `7177a` `71786` `717c2` `71c90` `72d66` `72dd2` `c1d2e` `2a00` `b76d2` `c095c` `c10a6` `c1176` `c1d12` `bfcde` `b41d8` `c0950` `c116a` `c1094` `716fa` `c1064` `b4334` `b4958` `b4ab0`). X를 읽는 명령은 없다.

- [F] **C 소비 block 8개**(Clear 쪽 / Set 쪽; Unknown C면 `objects fr12 caller requires known carry`): `716fa BCC 71502`(`4d84e`), `717aa BCS 713d8`(`4945e`, N08 실행부가 known C를 돌려줌), `71f1e BCC 71f28`(`49fc6`), `b6e7c BCC b6e8c`(`49392`), `c1064 BCC c1d06`(`b4304`), `c123e` `c12cc` `c135c`(`MOVEM.W (A7)+,D0-D6; BCC`, `2986`; MOVEM은 flag를 바꾸지 않음).
  - [F] `c123e` `c12cc` `c135c`의 Clear 쪽(`c1264` `c12f2` `c1382`, 2986 안의 28ae 실패 `290e`)은 기존 2986 실행부가 caller X를 알 때만 계속하는 checked 오류다(`cue wrapper failure requires known caller X`; C7 결정 6·7의 한계, FR11 `b7d8c`와 같음). 이 쪽은 단위 시험의 선언 C 행으로만 확인한다(V1 보고의 빠진 후속).
- [F] **C를 만드는 block**: `4d84e`(`TST.W a(A2)` → Clear; BNE면 RTS `4d86c`로) `4d868`(`ORI.B #1,CCR` Set → `4d86c`) `b4322`(`ANDI.B #fe,CCR; RTS` Clear) `b431c`(`ORI.B #1,CCR; RTS` Set). `c1260` `c12ee` `c137e`(`ORI.B #1,CCR`)는 Set이지만 읽는 곳이 없다(다음 `JSR 49a58`).
- [F] **C를 넘기는 block**: RTS `4d86c`(`4d84e`/`4d868`의 C를 `716fa`로; FR10 `ccaf6`과 같은 방식). dispatcher의 carry 보존 목록에 소비자 8개와 함께 넣었다.
- [F] RTS로 돌려주지만 읽는 쪽이 없는 flag: `b42f6`(`TST.B`)·`b42f8`(`ADD.B`) → FR11 `b41d8 MOVEM.L`; `b402a`(MOVE) → `c0950`/`c116a`(MOVE.L)·routing 밖 호출자; `b40fe` `b41b8` → FR11 `b4030` 호출자(`bfcde` `c095c BTST` `c10a6 BTST` `c1176 BTST` `c1d12 JSR`); `c1d04` → `c1094 MOVE.W`; `b518c` `c0984` `c1158` `c120a` `c1d2c`(node callback의 RTS → object loop).
- [F] **Z / N이 경계를 넘는 곳은 없다**. 모든 `Bcc`/`Scc`는 같은 block 안의 명령이 정한 flag를 읽는다. **묶인 BEQ 둘**(C10 `BUNDLED`와 같은 처리): `c1130 CMPI.B #2,b6; BEQ c113a; BEQ c120c`와 `c11e2 CMPI.B #3,b6; BEQ c11ec; BEQ c0944`에서 둘째 BEQ(`c113a` `c11ec`)는 block 시작이 아니다. 앞 block `c1126`/`c11ba`/`c11ce`/`c11d8`의 `BEQ`도 Z가 선 채로 그 BEQ로 가므로 늘 다음 BEQ가 취해진다: C++는 `c1126`·`c1130`이 구역 0 / 2면 `c120c`, `c11ba`..`c11e2`가 구역 0..3이면 `c0944`로 곧바로 간다(spec `THREAD`). 같은 block 안의 그 밖의 flag: `716ca MOVE.B`(BEQ) `716da CMPI.W`(BGT 부호) `7177c TST.L`(BPL) `717ae CMPI.W #80`(BCC 무부호) `b41f2`/`b4200 CMPI.B`(BYTE) `b4250 MOVE.L D0`(BPL) `b4260`/`b4274 CMP.L`(BLS 무부호) `b426a MOVE.L D1`(BPL) `b42f0 TST.B`(BMI) `b4304`/`b4312 CMPI.L`(BEQ LONG) `b6e5e CMPI.W #ffff` `b6f62 CMPI.W #1` `b70b8 SUBQ.B`(새 BYTE) `b70ee SUBQ.W`(BPL 새 WORD) `c10d0 LSR.W`(BEQ 새 WORD) `c1cf8 TST.B`(BPL), BTST(Z만)·`BTST #2,D0`(레지스터 bit).
- [F] **`716e6 BGT 71502`는 취해지지 않는다**: `716da MOVE.W 46(A6),D0; SUB.W 46(A6),D0`가 같은 RAM WORD를 두 번 읽어 D0.W = 0이다(ROM 바이트 `302e0046 906e0046`). C++는 원본대로 두 번 읽고 부호 비교한다. V1 spec은 `(716da, 71502)`를 `STATIC_IMPOSSIBLE`로 둔다 [I: 원본의 의도는 `46(A0)`였을 수 있다].

### IO 실행 run과 frame

- [F] 실행 run 8개(X1~X4 × case 68·94), 처음 frame은 위 "재확인과 범위". FR12 node는 pool `100800..104c00`의 여러 node다(`work/natscan_fr12.out`: frame 시작 상태의 callback `716ca` `7179a` `71e8c` `b6ed8` `b6fa4` `c0956` `c10a0` `c1170`, FR11 설치 `b6e50`·`c5602`, FR1 item 자식 `b3dbc`; `71502` `71f08` `72352` `b7096` `c1d0c`는 frame 시작 상태에 없다).
- [F] **IO 예측(FR12 연결)**: 7,383 → **7,977**(+594; 재관측 `reobs/fr12v1`, 계획과 같음). 첫 정지는 8 run 모두 FR13이다(위). [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다.
- [F] 원래 IO 관측은 FR12 코드를 실행하지 않는다(계획 §10.4: X run에서만 실행). 일치 173,966은 그대로여야 한다(작업자는 돌리지 않음; 메인 runner).

## 공통 규칙·native 검증 계획

FR2..FR11, C1~C10 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr12.cpp`, 함수 `animation_objects_fr12_block`. 오류 문자열은 `unsupported animation objects fr12 PC`(범위 안 내부 PC 직접 진입; 묶인 BEQ `c113a` `c11ec` 포함), `objects fr12 caller requires known carry`(C 소비 block 8개에 Unknown C) 두 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(26 범위, FR11 줄 뒤; `)ok=animation_objects_fr12_block(c);`를 같은 줄에 둔다), `carry_preserving_pc`의 FR11 묶음 뒤에 주석 달린 case 묶음 하나(소비자 8 + RTS `4d86c`), `animation_machine_internal.h`에 선언 하나(FR11 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# objects FR12 refresh:` 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 곧바로 들어감 9개는 쓰고 그 값으로 들어가고, 쓰기만 하는 8개는 쓰고 다음 block으로 간다. `c0966`은 RAM LONG을 쓴다.
- **자료 읽기**(live bus): node field(A6: BYTE `15` `61` `86` `9c` `9d` `9f` `b6`, WORD `2c`(쓰기) `42` `46` `7c` `82` `84` `88` `8e` `92`(쓰기) `9c` `b0` `b2` `b4`, LONG `0` `22` `36` `3a` `64` `76` `7e` `96`/`98` `a2`), A5 LEA(`-7348`/`-7258`, 메모리 접근 없음), A0 record(WORD `42` — `717ae`; WORD `76`..`7e` 쓰기 — `c1246` `c12d4` `c1364`; LONG `36`/`3a` 쓰기 — `c127c`..`c13aa`), 스택(push 일곱, MOVEM.W 일곱), 고정 ROM·bank(위 "계산 점프와 표"). 단위 시험은 고정 ROM·bank 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): 기록 `4cf64..4d0a4`(20 × 16 byte; WORD a는 기록 0 / 3 / 7 / 12에서 0, 4에서 0001, 5에서 8000), ROM 표 `b7f14..b8004`(`b7fbc` = `00038002 1234000a`, `b7fcc` = `fffe`), `4411e..4439e`(WORD 320; `4411e` = 7fff, `4419e` = 8000), bank 창 LONG `2000d0` → `2a1000`(+4 / 20 / 24 / 70) `2000d4` → `2a2000`(+4 / 20 / 24 / a4) `2001a8` → `2a3000` `2001ac` → `2a4000`(각 −10..+80의 LONG 36개). 영역 끝은 다음 코드 앞이다(`4d0a4` `4439e`은 코드, `b8004` 뒤는 자료 계속). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W`/`ADD.W`/`SUB.W`/`ANDI.W`/`ADDI.W`/`SUBI.W`/`ADDQ.W`/`NEG.W`/`EOR.W`/`EXT.W`/`ASR.W`/`ROR.W` 레지스터, `MOVE.B`/`ANDI.B`/`ORI.B`/`SUBI.B`/`ADD.B`/`SMI` 레지스터, `ADD.W`/`SUB.W`/`SUBQ.W`/`SUBQ.B`/`LSR.W`/`MOVE.B`/`MOVE.W` 메모리). `MOVE.L`·`MOVEA.L`·`MOVEQ`·`LEA`·`CLR.L`·`ADD.L`·`SUB.L`·`NEG.L`·`ASR.L`·`LSL.L`·`SWAP`·`EXT.L`·`MULS.W`·`MULU.W`·`MOVEM`은 LONG 전체(mod 2^32). 비교: `CMPI.W`+`BGT`은 부호 있는 WORD, `CMPI.W #80`+`BCC`는 무부호 WORD, `CMP.L`+`BLS`는 무부호 LONG, `CMPI.B`+`BEQ`/`BNE`는 BYTE, `CMPI.L`+`BEQ`는 LONG 전체, `TST.L`/`MOVE.L`+`BPL`은 LONG bit 31, `TST.B`+`BMI`/`BPL`은 BYTE bit 7, `SUBQ.W`+`BPL`은 새 WORD bit 15. 표 첨자 `(An,Dn.W)`·`(PC)` + `ADDA.W`는 부호 확장. bit: `BTST/BSET/BCLR/BCHG #n,d(A6)`(메모리 BYTE, bit mod 8), `BTST #2,D0`(레지스터 LONG bit).

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `e99fe5dbc8192ae377b9384c30fa821ada4a2fbf23aeca777c81fed5f115a815` → `49170da4b41a73e9cbb8d1684e0fa261fedc2ece6bab2e1e77a0b2dbe8e0c5f2`, `animation_machine_internal.h` `8cf2b547c1c11023096672ee7db3418811215596a99e907c494a91ed663b2296` → `3a5dc9af01e57baf08320a0ec5ba744c82ea85679e150a5e912a7d1212ed8c84`(옛 값은 `# objects FR12 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 작업 트리와 scratch clone root에서 확인했다(아래 "검증 수치").
- [F] **`tools/verify_animation_machine_stage_area.py` `UNROUTED_NEIGHBOURS`의 `4d84e`**(`SUPERSEDED_NEIGHBOUR_ERRORS` 방식, 새 `SUPERSEDED_NOTES`; C1의 `b7a28`과 같은 처리): `unsupported animation machine PC` → `animation machine external read queue empty`. `4d84e`가 FR12 시작이 되어 기본 상태(natural-001 frame 0)에서 `4d868` → `4d86c`(RTS)로 호출자에게 돌아간 뒤 선언 queue 없는 입력 읽기에서 실패한다. 관측: scratch clone root `roots/sa`에서 `work/sa_probe.py`(stop 없이 → `animation machine external read queue empty`, 상태 보존; stop `4d868`·`4d86c`면 성공; 이웃 `4d84c`는 그대로 `unsupported animation stage area PC`). 이 검증기는 메인 runner의 legacy 목록에 없어 작업자는 전체를 돌리지 않았다.
- [F] **FR10 시험 생성기·시험**(`tools/generate_animation_machine_objects_fr10_test_table.py`, `engine/tests/animation_machine_objects_fr10_test.cpp`; 오류 행. 이전 = FR12 PC에서 `unsupported animation machine PC`. FR12가 그 PC를 routing해서 C++가 FR12 코드를 실행하므로 바뀜. FR11 선례대로 실패 PC를 지키거나 경로를 따라 옮김):
  - `error-b6c2c-then-b6c58` → `error-b6c2c-then-b6c72`: 홀수 A7. FR12 `b6c58` → FR10 `b6c66` → `b6c72 BSR b7cfa`의 push가 `program bus requires even WORD/LONG address`(stop `b7cfa`). 고치기 전에는 `make test`가 `b6c2c: missing or ambiguous physical program bus ROM byte expected unsupported animation machine PC`로 실패했다(`b7cfa` 쪽이 선언 밖 ROM을 읽음).
  - `error-70f8a-then-70f8e`: 홀수 node(A6 = `10e001`). FR12 `70f8e`의 `MOVE.L #70c0c,(A6)`가 `invalid animation machine write size/alignment`, 실패 PC `70f8e` 그대로.
  - 생성기를 다시 돌려 그 2행만 바뀜을 확인했다(`work/fr10_test_before.cpp` 대비 diff). 시험 줄의 fixture 수는 그대로다(fr10 1,074).
- [F] **FR11 시험 생성기·시험**(`tools/generate_animation_machine_objects_fr11_test_table.py`, `engine/tests/animation_machine_objects_fr11_test.cpp`; 같은 이유):
  - `error-b41d8-then-b41f2` → `error-b41d8-then-b4292-odd-stack`: FR12 `b41f2` → `b4212`(합성 sine 표) .. `b427a` → FR11 `b427e` → RTS `b4292`의 pop이 홀수 A7에서 실패.
  - `error-b6e5a-then-b6e5e`: 홀수 node, FR12 `b6e5e`의 `MOVE.L #b6ed8,(A6)`가 alignment 오류, 실패 PC 그대로.
  - `error-c560e-then-c5612` → `error-c560e-then-2a00-odd-stack`: FR12 `c5612 JMP 2a00` → routing된 `2a00 BSR 299c`의 push가 홀수 A7에서 실패(stop `299c`).
  - `error-b4030-then-c0924` → `error-b4030-then-b412c-odd-stack`: LONG 76 = `c0924` → FR12 `c0924` → `b4294` → `b429e` → FR11 `b411c` → `b412c JSR 1aa3a`의 push가 실패.
  - `error-b42b0-then-b42c4` → `error-b42b0-then-b42ea-odd-stack`: D0 = c → FR12 `b42c4` → `b42ea JSR 49a58`의 push가 실패(stop `49a58`).
  - 생성기를 다시 돌려 그 5행만 바뀜을 확인했다(`work/fr11_test_before.cpp` 대비 diff). fixture 수 958 그대로.
- [F] **V1 spec**:
  - `fr10.py`: `ROUTED_LATER`에 FR12 진입 `70f8e` `b6c58`를 더했다(그 run은 그 PC에서 계속 멈춘다; `EXIT_STOPS`는 그대로). 오류 fixture `b6c2c-then-b6c58` → `b6c2c-then-b6c72`(홀수 A7, 위 생성기와 같은 뜻).
  - `fr11.py`: `ROUTED_LATER` `()` → (`b41f2` `b6e5e` `c5612` `70f8e` `b6c58`), 새 `JUMP_LATER`(`b42a2` `c0924` `b4294` `b42c4`: FR11 계산 점프 대상 중 FR12가 routing하는 것; FR11 run은 계속 그 PC에서 멈춤)와 `build()`의 대상 확인 `t in STARTS_SET or unit_of(t) is None` → `… or t in JUMP_LATER`. 오류 fixture `b41d8-then-b41f2` → `b41d8-then-b4292-odd-stack`, `b42b0-then-b42c4` → `b42b0-then-b42ea-odd-stack`.
  - `pc10.py`: `ROUTED_LATER`에 `70f8e` `b6c58`(FR11 때와 같은 방식).
- [F] **바뀌지 않음(확인)**: 저장소 tools·시험에서 FR12 범위 안 PC(와 `b4036` `b42bc` `c113a` `c11ec`)를 쓰는 곳을 전수 검색 `tools/fr12refs_repo.py` → `work/fr12refs_repo_v1.out`으로 찾았다.
  - 정지 전용·값 전용 행(정지 검사가 dispatch보다 먼저라 routing이 바뀌어도 같음): FR10 시험·spec(정지 `70f8e` `b6c58`, 표 `70d72` 값 `71502` `716ca`), FR11 시험·spec(정지 `b41f2` `b6e5e` `c5612`, handler 값 `b42a2` `c0924` `b4294`, 표 칸 `b42c4`, 이웃 목록 `b40f8` `b41b2` `b4294` `b42c4` `b6e5e` `c5612`), FR4 시험(`TARGETS`의 `cc7c0` 정지), FR1 시험(`b3dec`의 A0 값 `b42a2`, 범위 끝 `b402a`), N15 시험(설치 값 `71502` `716ca` `71e8c`), 그 밖의 숫자 값(`c1048` `c1234` `71551`).
  - 생성기·관측기 주석·자료: `observe_animation_machine_stage_area.py`(`4d84e`는 범위 끝, 관측 시점 기록).
  - `make -j4 all test`가 위(FR10·FR11 생성기 행) 말고 기존 시험이 모두 그대로 통과함을 확인했다.
- [I] 원래 IO 관측과 frame 비교(d1·controller·irq·demo)는 FR12 코드를 실행하지 않으므로 결과가 같아야 한다. 메인 runner가 확인한다.

## 결정

1. **범위: 212 block, 26 범위(계획 그대로).** 가상 routing 재관측에서 새로 보인 PC가 없고(숨은 직선 block 0), 범위 밖에서 범위 안 비시작 PC로 오는 실제 분기도 없다. 실행 칸 `b42c4`는 FR12(FR11 메인 결정). 뒤 단위의 짧은 fall-through `7177a` `71786`(FR14) `717c2` `71682`(FR13)는 계획 배정대로 정지로 둔다. 예측 7,977(+594).
2. **계산 점프 없음.** FR12가 받는 계산 착지(`b42a2` `c0924` `b4294` `b42c4` `cc7c0` `c1036`)는 기존 실행부의 규칙 그대로이고 routing이 판정한다. `c0966`은 RAM LONG을 callback 자리에 쓰기만 한다. 고정 ROM 표와 bank 창 LONG은 live bus로 읽고 상한을 검사하지 않는다.
3. **정수 연산**: MULS.W는 부호 있는 하위 WORD 곱의 32 bit, MULU.W #10은 무부호 하위 WORD 곱의 32 bit, ASR.L / ASR.W는 부호 채움, LSR.W는 논리, ROR.W #8은 하위 WORD BYTE 교환, `MOVEM.W (A7)+`는 부호 확장(낮은 주소가 D0).
4. **flag.** C 소비자 8개는 known C를 읽거나 checked 오류. `4d84e`/`b4322` Clear, `4d868`/`b431c` Set, RTS `4d86c`가 `716fa`로 넘긴다. `c1260` `c12ee` `c137e`는 Set(읽는 곳 없음). 묶인 BEQ `c113a` `c11ec`는 block 안에서 처리하고 Z / N 경계는 없다.
5. **V1 natural family.** 확장 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)이 읽는다. pool `100800..104c00`의 node가 FR12 callback(13개), FR11 설치 `b6e50`·`c5602`(→ `b6e5e`·`c5612`) 또는 FR1 item 자식 `b3dbc`(kind handler `c1036`)를 callback LONG으로 가진 frame 121개(`work/natural_fr12.json`: run과 callback마다 처음·처음 여덟 가운데·마지막 frame). `c1094`는 LONG a2 자리에도 있어(가짜 node) natural 목록에서 뺐다.
6. **앞 단위 spec·시험.** FR10·FR11의 뒤 단위 정지 가운데 FR12 진입을 fr10·fr11·pc10의 `ROUTED_LATER`(fr11은 `JUMP_LATER`도)에 두어 그 run은 계속 그 PC에서 멈춘다. 오류 fixture는 실패 PC를 지키거나 경로를 따라 옮긴다(위). stage area 검증기의 이웃 `4d84e`는 superseded 기대값으로 옮긴다.
7. **다음.** FR12 연결로 확장 관측 IO 7,977(+594)을 메인 runner가 확인한다. 다음 단위 FR13은 계획 시작 목록에 `c54ba` `c54d6`(FR11 표 칸), `71682` `717c2`(FR12 정지)를 가진다.

## 미확인

- [U] node field·전역 값의 의미(BYTE `86` `9c` `9f` `b6`, WORD `46` `7c` `82` `84` `88` `b0` `b2` `b4`, LONG `64` `a2`, 기록 `4cf64`, 표 `b7fbc` `b7fcc`). 이름(회전, 구역, 난수 각도, 자식 셋 생성, dead zone)은 동작에서 붙인 [I]이다. 어떤 적·item인지는 정하지 않았다.
- [U] `716da`가 같은 WORD를 두 번 빼는 것이 원본의 버그인지(의도가 `46(A0)`였는지). 동작은 원본 바이트대로 재현한다.
- [U] `4d84e`의 D0(= `4d7a6`이 돌려준 플레이어 기록 BYTE `27`)가 실제로 14 이상이 되는지(그때는 코드 바이트를 기록으로 읽음).
- [U] IO 관측에서 실행되지 않은 이 단위의 분기 쪽(`71502`..`7155e`, `722da`..`7238c`, `b6ff4`..`b70fc`, `c120c`..`c13aa`, `c1d06`..)은 V1 선언 상태·natural·실제 ROM 차분·단위 시험으로만 확인했다.
- [U] `c123e` `c12cc` `c135c`의 Clear 쪽(2986 안의 28ae 실패)은 기존 2986 실행부의 caller-X 한계로 C++에서 checked 오류다(선언 C 행만).
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC).
- [U] natural fixture의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C10, FR10·FR11과 같음).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr12.cpp`(case label 212 = `starts_fr12_final.txt`와 집합 일치; 공용 함수 `ofr12_get` `ofr12_put` `ofr12_bit`(BCHG 포함) `ofr12_btst` `ofr12_test` `ofr12_carry` `ofr12_install` `ofr12_asr` `ofr12_asr_word` `ofr12_signed_word` `ofr12_ext_byte` `ofr12_muls` `ofr12_mulu` `ofr12_add` `ofr12_add_word` `ofr12_bank_anim` `ofr12_table_anim` `ofr12_kind` `ofr12_offsets` `ofr12_steer` `ofr12_angle` `ofr12_mirror` `ofr12_sector` `ofr12_sector_is` `ofr12_spawn` `ofr12_unpush` `ofr12_child_fields` `ofr12_child_speed` `ofr12_random_word`), `engine/tests/animation_machine_objects_fr12_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_d`), `tools/generate_animation_machine_objects_fr12_test_table.py`(생성기; FR11 생성기 꼴, 묶인 BEQ의 착지를 내부 착지로 보지 않음, 2986 안의 `290e` 실패 사슬을 버림, V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 95초), `tools/unit_fixture_specs/fr12.py`(V1 spec; FR11 spec의 공용 부분 + C10 spec의 묶인 Bcc 처리(`BUNDLED`, 새 `THREAD`), 단위 부분 교체, `EXIT_STOPS`(22), `TRAPS`(`b3e58` `b3eac`), `CONSUMERS`(8), `CLEAR_SET` `SET_SET` `PASS_SET`, `STATIC_IMPOSSIBLE`/`BRANCH_IMPOSSIBLE`(`716e6` → `71502`), `NATURAL_ENTRIES`(13 + `b6e50` `c5602` `b3dbc`), natural family는 확장 관측 pack, world의 WORD `90`은 FR2 `b4aca` 표 첨자(4의 배수)). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `work/starts_fr12_final.txt`(SHA256 `2efbd8d3…`).

- **`4d84e..4d86e`(3)**: `4d84e 4d868 4d86c`
- **`70f8e..70f94`(1)**: `70f8e`
- **`71502..71562`(5)**: `71502 7150a 71532 71536 7155e`
- **`716ca..7177a`(13)**: `716ca 716d6 716da 716ea 716f4 716fa 716fe 71706 7172e 71732 7175a 71764 7176a`
- **`7177c..71786`(1)**: `7177c`
- **`71788..717c2`(5)**: `71788 7179a 717a4 717aa 717ae`
- **`717c8..717e8`(5)**: `717c8 717ce 717d4 717de 717e4`
- **`71e8c..71f2c`(12)**: `71e8c 71e94 71ebc 71ec0 71ee8 71eee 71f08 71f12 71f18 71f1e 71f22 71f28`
- **`722da..72390`(10)**: `722da 722e2 7230a 7230e 72336 72352 72376 7237c 72386 7238c`
- **`b402a..b4030`(1)**: `b402a`
- **`b40f8..b4104`(2)**: `b40f8 b40fe`
- **`b41b2..b41be`(2)**: `b41b2 b41b8`
- **`b41f2..b427e`(12)**: `b41f2 b4200 b4208 b4212 b4250 b425e b4260 b4266 b426a b4272 b4274 b427a`
- **`b4294..b42b0`(4)**: `b4294 b429e b42a2 b42ac`
- **`b42c4..b42c8`(1)**: `b42c4`
- **`b42ea..b4328`(8)**: `b42ea b42f0 b42f6 b42f8 b4304 b4312 b431c b4322`
- **`b518c..b5198`(1)**: `b518c`
- **`b6c58..b6c66`(1)**: `b6c58`
- **`b6e5e..b6e8c`(4)**: `b6e5e b6e6e b6e7c b6e80`
- **`b6ed8..b6fc2`(15)**: `b6ed8 b6ee2 b6eee b6f26 b6f2a b6f62 b6f82 b6f88 b6f9a b6f9e b6fa4 b6fa8 b6fae b6fb8 b6fbe`
- **`b6ff4..b7100`(16)**: `b6ff4 b7000 b7038 b703c b7074 b7096 b70ac b70b2 b70b8 b70c0 b70ce b70d8 b70e4 b70ee b70f6 b70fc`
- **`c0924..c0986`(11)**: `c0924 c0944 c0950 c0956 c095c c0966 c096a c0970 c0976 c097e c0984`
- **`c1036..c13c0`(66)**: `c1036 c1048 c105e c1064 c1068 c106e c1094 c10a0 c10a6 c10b0 c10c6 c10d0 c10d8 c10e2 c10f2 c1108 c1112 c1126 c1130 c113e c1144 c114a c1152 c1158 c115a c116a c1170 c1176 c1180 c118a c119a c11b0 c11ba c11ce c11d8 c11e2 c11f0 c11f6 c11fc c1204 c120a c120c c123e c1246 c1260 c1264 c126a c127a c127c c128a c12cc c12d4 c12ee c12f2 c12f8 c130a c130c c131a c135c c1364 c137e c1382 c1388 c139a c139c c13aa`
- **`c1cf2..c1d2e`(11)**: `c1cf2 c1cf8 c1cfe c1d04 c1d06 c1d0c c1d12 c1d18 c1d1e c1d26 c1d2c`
- **`c5612..c5618`(1)**: `c5612`
- **`cc7c0..cc7c4`(1)**: `cc7c0`

## 검증 수치

작업자 최종 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j4 all test`(최종 실행부·시험): 종료 0, 경고 0, Assert 0, Python 310 OK(`trial_logs/make_final.log`). FR12 시험 줄: `animation machine objects fr12: 1127 fixtures (724 single-block, 323 path, 24 producer chain, 16 declared C, 40 checked error (6 with a later failing PC), 72 kept C), 212 blocks, 5269 calls, 122166 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block은 `716da` → `71502`뿐(같은 WORD의 차라 취해지지 않음), 출구 중 stop이 아닌 것 0, 실제 사슬 4개(`716f4`→`716fa`(`4d84e`), `717a4`→`717aa`(`4945e`), `b6e6e`→`b6e7c`(`49392`), `c105e`→`c1064`(`b4304`)). `71f18`(`49fc6`)은 bank 장치에 써서 native run이 버려졌고, `716ea`(`4d7a6`)은 Set만, 2986 사슬 셋은 Set만 나와(Clear 쪽은 2986 caller-X 오류) 선언 C 행만 있다. 생성기를 다시 돌려 FR12 시험 파일이 바이트 단위로 같음을 확인했다(SHA256 `d6b3b3dd588da8bd…`, `trial_logs/gen_repro.log`). FR10 시험 줄은 fixture 1,074, FR11은 958 그대로(오류 행 2 / 5만 바뀜).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, `work/ubsan.sh`, FR12 시험): 빌드 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_build.log` `ubsan_fr12.log`).
- [F] V1 fr12(작업자, `--workers 3`): fixture 2,302개(match 1,146, error 1,146, mismatch 10; natural 150) failed 0, `ok` true, 방문 시작 212/212, carry oracle Unknown/Clear/Set = 1,013/72/61(`trial_logs/v1_fr12_final.log`, `work/v1/fr12_final/report.json`). spec 보고의 빠진 후속은 `716fa` → `71502`(사슬 `716ea`: 이 world에서 `4d7a6`이 D0 = 0을 돌려줘 기록 0(WORD a = 0) → Set만; 사슬 `716f4`는 둘 다)과 `c123e`/`c12cc`/`c135c`의 Clear 쪽(2986 안의 28ae 실패, C++ caller-X checked 오류; 도달 못한 분기 결과 `c1242` `c12d0` `c1360`의 같은 쪽)이다.
- [F] V1 회귀(작업자, `work/v1_regs.sh`, `--workers 3`; `work/v1/v1_regs.txt`): pc1 1,264, pc2 1,743, pc3 1,829, pc4 1,873, pc5 1,755, pc6 1,856, pc7 2,077, pc8 986, pc9 2,347, pc10 1,334, se1 2,102, fr9 1,415, fr10 2,170, fr11 2,170(모두 failed 0, `ok` true; FR11 기록과 같은 수). FR12 PC를 정지·값·범위 끝으로 가진 fr1 1,631, fr4 1,629, b1a 2,801도 돌렸다(`--workers 2`; 모두 failed 0, `ok` true). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·op(BCHG 포함), WORD/BYTE → LONG, 복귀 PC·호출 대상, carry tag, mask, 상수·설치 값, `ofr12_*` helper 인자) + 손으로 고른 helper·block 변이(MULS.W의 부호 없는 곱·한쪽만 부호·WORD 결과·WORD 결과 부호 확장·LONG 피연산자, MULU.W의 부호 곱·LONG 피연산자·WORD 결과·상위 WORD 유지·× 8, ASR.L 논리·채움, ASR.W 논리·채움·LONG, EXT.W, BCHG(set / clear), `b4212`의 표 교환·색인 부호 확장·차 → 합·ASR 폭·두 번째 곱 교환·NEG 없음·끝 식, `b41f2`의 ASR 폭·D1 논리 shift·BYTE 비교 WORD, `b4250` 상수, `b4260`/`b4274`의 BLS(엄격·부호), `b42f8` 폭, `b4304`/`b4312`의 WORD 비교, `c0924`의 SMI·ORI·SWAP·CLR.W·ASR 폭·순서·TST 크기, `c106e`의 ROR·SMI·EOR·SUB·mask·D1 폭·a2, `c10b0`의 ASR.W 폭·EXT·LSL 폭·ASR·SUB → ADD, `c10d0`의 LSR → ASR·옛 값, steer / angle / mirror / sector / spawn / unpush(부호 확장 없음·WORD·역순·여섯·carry 검사 순서·C 교환) / child 필드·LONG, `random`의 mask·폭, `4d84e`의 MULU 폭·AND 없음·× 8·WORD a 자리·carry tag, `716da`의 부호·SUB 없음, `71788`의 LSL 폭·SWAP 없음·ADDI 폭, `717ae`의 부호·순서, `72352`의 ASR 폭·순서·상수) + dispatcher carry 목록 9개·범위 52개를 적용해 만든 것, 749개; `--workers 4`): 1회째 `killed 722 of 749`(`trial_logs/mut_first.log`). 생존 27개 중 2개는 시험 빈틈이었고 규칙 `rules_d`와 합성 기록 하나(기록 4의 WORD a = `0001`)로 메웠다(`4d84e`의 WORD TST(BYTE로 읽는 변이), `c095c`의 BYTE 15(16으로 읽는 변이); 두 변이 다시 실행 `killed 2 of 2`). 남은 25개는 동치다(`mut/equivalents.txt`, 사례별 이유: 곧 덮어쓰는 레지스터 상위 bit(표 anim의 ADD.W·LSL, `4d84e`의 ANDI → MULU, `c0924`의 SMI·EXT → SWAP·CLR.W, `c10b0`의 MOVE.W → EXT.L), 다음 `MOVE.L #v,98(A6)`이 덮는 `96(A6)`의 하위 BYTE 둘, BYTE 읽기의 WORD mask 넷, EXT.W 입력이 ff / 01 / 00뿐인 것 셋, `716da`의 D0.W = 0 셋, 8 미만 bit 번호, `am_write`·양수 변위의 자체 성질 둘, ADDI.W 뒤 올림 없음, MULS가 하위 WORD만 쓰는 ASR / LSR 둘, 음이 아닌 색인의 부호 확장). 규칙을 더한 뒤 전체 2회째 `killed 724 of 749`(`trial_logs/mut_second.log`), 남은 25개가 동치 목록과 같다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`, 메인 runner용), `real_fr12.py`(FR11 harness에 FR12 world(`fr12_world`: handler LONG 76, WORD 8e / 90 / 7c / 82 / 46 / 42 / 84 / 88 / 9c / b0 / b2 / b4, BYTE 15 / 61 / 86 / 9c / 9d / 9f / b6, LONG 36 / 3a / 64 / 7e / a2, A5 BYTE 568e, A0 record `FR12_REC`)·소비자 8·C pass `4d86c`·선언 정지(FR12의 뒤 단위 정지 4, FR11 / FR10 / C1~C9의 남은 정지, TRAP `b3e58` `b3eac`, FR11 계산 점프의 routing 밖 대상 `UNR_FR11TAB`(`b4036` `b42bc` 표 `c54b2` 26칸), routing 밖 FR4 표 칸 47)·`cb` 진입에 FR12로 넘겨주는 FR10 `70f84` `b6c2c`, FR11 `b41d8` `b6e54` `c5608` `b42b0`, FR1 `b3dbc`; 계산 점프 착지를 trace 전체에서 대조(FR11 `ALLOWED_FR11` 등 앞 단위 표 그대로); `native_safe` 기본 유지)): 작업자 300건 seed 1 `mismatches 0`(`covered starts 199 of 212`; 문서화된 분류: 2986 실패 경로의 caller-X 14건(`c120c` `c128a` `c131a` 등), FR11 jump-target 1건(무작위 D0의 `b42b4`); 깨끗이 멈추지 않은 native 56건 건너뜀; native oracle abort 0, `trial_logs/real_n300_s1.log`). 앞선 30건 seed 11 시험도 `mismatches 0`(`trial_logs/real_t30.log`).
- [F] **IO, 입력 확장 관측**(FR12 연결 뒤, `--workers 3`): run 12, native 비교 frame 14,500 가운데 일치 **7,977**(예측 7,977, 기준선 7,383 → +594), 불일치 0(beyond 0), C++ 오류 0, chain divergence 0, 수용 키 모두 true(`negatives_ok` 포함)(`trial_logs/io_ext_fr12.log`; `verification.json` SHA256 `c62538be908db835…`, `frontier.json` `34dbb0e4860b71a8…`, scratch `io_ext_fr12/`). 첫 정지 frame: X1 68 873 `70fcc`, X1 94 604 `c54ba`, X2 68 757 `71028`, X2 94 629 `70f60`, X3 68 760 `b44ac`, X3 94 588 `c54d6`, X4 68 773 `c554c`, X4 94 593 `71f2c` — 재관측 예측(`reobs/fr12v1.stops`)과 run·frame이 모두 같고, 확인된 frontier PC는 모두 FR13(D-4)이다.
- [F] 원래 IO 관측·frame 비교·legacy 검증기는 작업자가 돌리지 않았다(메인 runner). stage area 검증기는 이웃 `4d84e`만 scratch clone root에서 탐침했다(위 "영향받는").
- [F] `CPP_PINS`: 작업 트리와 scratch clone root(`work/mkroot.py`; 확인 뒤 symlink를 먼저 지우고 삭제)에서 파일 SHA와 같다(4 / 9 pin, 불일치 0, `trial_logs/pincheck_tree.log` `pincheck_root.log`).

## 검증 기록(검증 실행: 결정적 runner + 메인 검토)

- [F] `make -j4 all test`: 종료 0, 경고 0, Assert 0, Python 310 OK. FR12 시험 `animation machine objects fr12: 1127 fixtures (724 single-block, 323 path, 24 producer chain, 16 declared C, 40 checked error (6 with a later failing PC), 72 kept C), 212 blocks, 5269 calls, 122166 checks`.
- [F] `ubsan`: 빌드/실행 종료 0, 런타임 오류 0.
- [F] `mutation`: 변이 749, 제거 724, 등가 25.
  - 이 실행 전에 메운 시험 빈틈 2개.
- [F] real-ROM: 배치 `f4`, `f5`, `s1`, `s2`, `s3` 커버 `212`, `212`, `211`, `212`, `211`; mismatches `0,0,0,0,0`.
  - 오라클: `native_safe` 켬.
- [F] V1: A/B 각각 fixtures 2302, failed 0, identical true(digest `87f7a8535f611d48`); regression specs 46개 모두 failed 0.
- [F] legacy verifiers: `stage_entry`, `area_clear`, `stage_event`, `stage_event_ops`, `frame_helpers`, `card_menu_close`, `input`, `scene_core`, `scheduler`, `objects_g1` 모두 종료 0. `objects_g1` 판정은 C1과 같다.
- [F] frames: `d1` 완료 54400/54400, mismatches 0; `controller_game` 완료 54400/54400, mismatches 0; `irq` 완료 54400/54400, mismatches 0; `demo` 완료 45684/45684, mismatches 0.
- [F] IO(원래 관측): 일치 합계 173966, 기준 173966, 차이 0, mismatches 0, C++ 오류 0, 실행 2, identical true; 설정별 `P0` 81600, `P1` 81600, `P1b` 8400, `boot-demo-0` 577, `boot-title-idle` 600, `boot-title-start` 906, `fx-bios-call` 3, `fx-c-input-read` 3, `fx-n-input-read` 3, `fx-queue-short` 1, `fx-start-c79a` 273.
  - 수락 실패 항목은 없고, native frame 173966 전부 일치한다.
- [F] IO(확장 입력 관측, 14500 native frames): 일치 합계 7977, 기준 7383, 차이 594, mismatches 0, C++ 오류 0, 실행 2, identical true; 설정별 `P0` 1200, `P1` 1200, `X1` 1477, `X2` 1386, `X3` 1348, `X4` 1366.
  - 예측 확인: 정확한 비트맵 재관측은 7977을 예측했고, 실측도 7977이다.
  - 수락 실패 항목은 없고, native 완료 frame 14500 중 7977이 일치한다.
  - 첫 정지: `70fcc c54ba 71028 70f60 b44ac c54d6 c554c 71f2c`(모두 FR13).
  - 범위: 범위 변경 없음; 실행된 표 항목 `b42c4`를 포함했고(메인 결정), 2바이트로 빠져나가는 블록 `7177a 71786`(FR14)와 `71682 717c2`(FR13)는 계획대로 이후 단위에 남긴다.
  - 산술: `MULS`는 부호 있는 낮은 WORD, `MULU`는 부호 없는, `MOVEM.W`는 부호 확장; 자체 계산 점프 없음.
- 검증 방법: 결정적 runner(LLM 없음). 이 기록 초안은 local Qwen이 썼고 메인이 검토·수정했다.

## 뒤 단위 변경 기록: objects FR13(2026-10-24, 작업자 Claude Opus 5.5 / high)

FR13 계약(`animation-machine-frontier-fr13-contract.md`) 결정 6에 따른 기록이다. FR12 실행부는 바뀌지 않았다.

- [F] **FR12의 뒤 단위 정지 가운데 FR13 진입**: `71682` `717c2`가 FR13 block이 되었다(메인 결정: 계획대로 FR13). 나머지 둘(FR14 `7177a` `71786`)은 계속 뒤 단위 정지다.
- [F] 생성기 `generate_animation_machine_objects_fr12_test_table.py`의 오류 행 둘(이전: 그 FR13 PC에서 `unsupported animation machine PC`): `71532-then-71682`(홀수 node: FR13 `71682`의 `MOVE.W 7a(A6)`, 실패 PC 그대로), `717ae-then-717c2` → `717ae-then-717c8-odd-stack`(홀수 A7: FR13 `717c2` → FR12 `717c8 JSR 4bfa4`의 push). 생성기를 다시 돌려 그 2행만 바뀜을 확인했다(fixture 1,127 그대로).
- [F] V1 spec `fr12.py`: `ROUTED_LATER` `()` → (`71682` `717c2` `b6d90` `bfcfa` `70f60` `70fcc` `70ff8` `71028`). 오류 fixture `71532-then-71682`(홀수 node), `717ae-then-717c2` → `717ae-then-717c8-odd-stack`. FR12 run은 그 PC에서 계속 멈춘다.

## 뒤 단위 변경 기록: objects FR14(2026-10-24, 작업자 Claude Opus 5.5 / high)

FR14 계약(`animation-machine-frontier-fr14-contract.md`) 결정 5에 따른 기록이다. FR12 실행부는 바뀌지 않았다.

- [F] **FR12의 남은 뒤 단위 정지 `7177a` `71786`이 FR14 block이 되었다**(`NEG.L D0` → FR12 `7177c` / `71788`). FR12의 뒤 단위 정지는 이제 없다.
- [F] 생성기 `generate_animation_machine_objects_fr12_test_table.py`의 오류 행 둘(이전: 그 FR14 PC에서 `unsupported animation machine PC`): `7176a-then-7177a` → `7176a-then-7177c-odd-node`(홀수 node: FR12 `7177c`의 `MOVE.L D0,64(A6)`), `7177c-then-71786` → `7177c-then-717a4-odd-stack`(D0 음수, BYTE 15 = 80: `71788` / `7179a` 뒤 `717a4 JSR 4945e`의 push가 홀수 A7). 생성기를 다시 돌려 그 2행만 바뀜을 확인했다(fixture 1,127 그대로).
- [F] V1 spec `fr12.py`: `ROUTED_LATER`에 `7177a` `71786`. 오류 fixture를 위와 같은 뜻으로 옮겼다. FR12 run은 그 PC에서 계속 멈춘다.
