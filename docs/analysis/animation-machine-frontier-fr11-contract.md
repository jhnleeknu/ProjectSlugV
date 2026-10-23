# frontier 단위 FR11(입력 확장 관측의 영역 D 둘째 단위: FR10 뒤 단위 정지 `70e42`·`70fac`·`cd7e2`·`cd92e`·`cd96c`, FR4 표 칸 `cc836`·`cc842`, FR1 item 객체 `b3dbc`의 handler `b4030`(`JMP (A0)`) → `b403e`/`b41be` → `b411c`(MULS 회전) → `b4104`/`b42b0`(`JMP b42b8(PC,D0.W)`)/`b427e`, kind handler `bfb5a` → `bfc2a`(MULU.W #8) → `bfcaa` → `bfcd8`/`bfdb2` → `b3e1c`(TRAP #15 `b3e58` 경계), U18 설치 값 `b67b2` → `b686e`, FR10 설치 값 `b6ca2` → `b6d6a`·`b6d82` → `b6e50` → `b6e8c`, 28ae 자식 `b774a` → `b77f4`·`c5592` → `c5602`, script callback `b7d4a`(2986 자식 `b3dbc`, `MOVEM.W (A7)+,D0-D6`), FR3 설치 값 `c5432` → `c5470` → `c5486` → `c54a6`(`JMP c54b2(PC,D0.W)`)/`c5540`, 192 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §10.5 표의 FR11 행(계획 이름 D-2)과 §10.x 메인 결정을 기준으로 삼고, 구조·공통 규칙은 FR10 계약(`animation-machine-frontier-fr10-contract.md`; 영역 D의 확장 관측 단위, 정확 bitmap 재관측으로 범위 확정)과 C10 계약(`animation-machine-player-c10-contract.md`; 표 점프 규칙, 뒤 단위가 routing하는 앞 단위 정지의 처리), TRAP은 FR5 계약 결정 2(TRAP 자리는 단위 밖 경계)를 따르며 다른 점만 적는다. 단위 이름은 FR11, 파일 접두어는 `objects_fr11`(C++) / `fr11`(V1 spec)다. 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다. BIOS 실행, 자연 scheduler, IRQ timing은 주장하지 않는다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 LONG(`2000d0` `2000d4` `200080` `200094` `2001a8` `2001ac` `2001c0`)을 live bus로 읽는다(아래). 장치 쓰기는 없다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 C10 커밋 `193445b`(branch `claude/fr11-core`; C1~C10, E1, D, FR10 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `63f7d470922dfab836b19417f2a16dba5d170d3424906a13c04ad69f53a48eb7`, `animation_machine_internal.h` `f1180a35ac8dab11f98c309ba7c890110e5e141f63553c3239c51375fb1c7f4a`(C10 계약의 새 값과 같음).
- [F] 관측 입력(읽기 전용): 입력 확장 IO 관측 `artifacts/animation_machine_io_ext`(`observation.json` SHA256 `9da40ac6dcbea3eb…`, compared_sha256 `b5d15d4fcd53555b…`, 검증기 pin 이름 `io-ext`). V1 natural family가 이 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)으로 읽는다(C9 결정 6과 같은 방식).
- [F] 이 단위의 정확 bitmap 재관측 두 벌(scratch, 관측기 `tools/observe_animation_machine_io_ext.py` 수정 없음): `reobs/fr11base`(C10 routing 그대로), `reobs/fr11v1`(계획 FR11 32 범위를 `--extra-routed`로 가상 routing). 결정 1.
- [F] 시작 목록: **`ms5-scratch/fr11/work/starts_fr11_final.txt`(192개, 줄마다 하나, SHA256 `144dc2bc508853d19727cf9d52d6ea35d6c6b28a736170df7329c9993d543fd7`)**. 계획 목록 `ms5-scratch/fr11/starts_FR11.txt`(192개, 공백 구분, SHA256 `0b9d751960bc3cc44d5bf33cace57796c602939b4697bd6fec30c26eadba0ea7` = 계획 §10.5의 `0b9d751960bc3cc4`)와 집합이 같다(결정 1: 범위 보정 없음). 실행부의 `case` label 192개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(작업자 확인: 실행부 case 집합 = 시작 목록, `make test`의 FR11 시험이 시작 192개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr11/`
  - `reobs/run.sh`(재관측 + `dleft.py` + `runstops.py`), `reobs/fr11base` `fr11v1`(+ `.dleft` `.stops` `.log`), `plan/udetail_FR11.txt` `plan/D-2.dis.txt`(계획 `xplan_v2.json`의 D-2 상세·역어셈블; `tools/xdetail.py`), `work/fr11ranges_plan.txt`(32 범위), `work/blocks_v1.txt`(block별 역어셈블; `tools/blocks_c10.py`).
  - `tools/newvis_fr11.py` → `work/newvis_fr11v1.txt`(새로 보인 PC), `work/intargets.py` → `work/intargets_fr11_v1.out`(범위 안 비시작 PC로 오는 직접 분기), `tools/refs_fr11.py` → `work/refs_fr11_v1.out`(ROM 전체 FR11 시작 참조), `tools/flagscan.py` → `work/flagscan_fr11_v1.txt`(block 경계를 넘는 flag), `tools/exitflags.py` → `work/exitflags_fr11.txt`(출구·복귀 대상이 앞 코드의 flag를 읽는지), `tools/fr11exec.py` → `work/fr11exec_base.txt`(재관측의 FR11 실행 PC·run·frame), `tools/natscan_fr11.py` → `work/natscan_fr11.out` `work/natural_fr11.json`(V1 natural frame), `tools/fr11refs_repo.py` → `work/fr11refs_repo_v1.out`(저장소의 FR11 범위 literal), `work/rulecalc.py`(수작성 규칙의 기대값 계산), `work/v1_regs.sh`, `work/pincheck.py`, `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위(결정 1)

- [F] **기준선**(C10 routing, 입력 확장 관측): 예측 일치 frame **6,751**, 첫 정지 D 8 run(X1 68 frame 659 `b6ca2`, X1 94 439 `b67b2`, X2 68 633 `cc836`, X2 94 409 `cd96c`, X3 68 628 `b6ca2`, X3 94 432 `b6ca2`, X4 68 661 `cd92e`, X4 94 490 `cd92e`). C10 계약의 IO 실측과 같다.
- [F] **정확 bitmap 재관측(C10 routing)** `reobs/fr11base`: `dleft.py` 실행된 routing 밖 PC E 108 / D 510, 예측 6,751, 첫 정지는 위와 같다(`reobs/fr11base.dleft` `.stops`).
- [F] **정확 bitmap 재관측(FR11 가상 routing, 계획 32 범위)** `reobs/fr11v1`: 예측 일치 frame **7,383**(계획 7,383과 같음), 실행된 routing 밖 PC E 108 / D 378, 첫 정지는 8 run 모두 뒤 단위다: X1 68 frame 745 `b6e5e`(FR12), X1 94 488 `b4304`(FR12), X2 68 713 `b4304`(FR12), X2 94 493 `70f8e`(FR12), X3 68 714 `b6e5e`(FR12), X3 94 518 `b6e5e`(FR12), X4 68 736 `cc7c0`(FR12), X4 94 576 `cc7c0`(FR12)(`reobs/fr11v1.stops`; 단위 소속은 계획 `xplan_v2.json`의 D-3).
  - [F] **숨은 직선 연속 검사**: `fr11base`에 없고 `fr11v1`에만 보이는 routing 밖 PC는 **없다**(`work/newvis_fr11v1.txt`: 12 run 모두 0). 가상 routing 관측에서 실행된 FR11 범위 끝 PC `b40f8` `b41b2` `b41f2` `b4294` `b6d90` `b6e5e` `bfcfa` `c5520` `c554c` `c5612`는 모두 기준 관측에서 이미 보였고 뒤 단위(FR12 D-3 / FR13 D-4)의 시작이다. 반복은 한 번으로 수렴했다.
- [F] **범위 밖에서 범위 안 비시작 PC로 들어오는 직접 분기**: 없다(`work/intargets_fr11_v1.out`의 7줄은 모두 `MOVE.L #v,(A6)` 즉치의 하위 WORD를 명령으로 읽은 것: `b675e`(→ `b6762`) `b68a6` `b6c6c`(FR10) `b6d64` `b6d78` `b6e4a` `b6e5e`).
- [F] **계획의 "실행 칸" 확인(C10 결정 1 보정 3과 같은 대조)**: 관측 기록(`reobs/fr11base`의 `unr_pcs`)에서 두 표의 실행 칸은 다음과 같다.
  - 표 `b42b8`(`b42b4 JMP b42b8(PC,D0.W)`): 칸 0 `b42b8`(→ `b42c8`, FR11) 5 run, 칸 c `b42c4`(→ `b42ea`) 2 run(X1 94, X2 68). 칸 4 `b42bc`·칸 8 `b42c0`은 기록 없음.
  - 표 `c54b2`(`c54ae JMP c54b2(PC,D0.W)`): 칸 6 `c54ca`(→ `c5540`, FR11) 6 run, 칸 2 `c54ba`(1 run X1 94)·칸 9 `c54d6`(2 run X3)(둘 다 → `c5520`). 나머지 칸은 기록 없음.
  - [F] 계획은 실행 칸 `b42c4`를 FR12(D-3), `c54ba` `c54d6`(과 대상 `c5520`)를 FR13(D-4)에 두었다(계획 규칙: 실행 PC의 key 순서로 모음). 이 칸들은 FR11 표 점프의 실행 칸이지만 계획 배정을 바꾸지 않는다(결정 1). FR11은 칸 선택 규칙(결정 2)으로 그 칸에서 멈추고(뒤 단위 정지), 뒤 단위가 그 칸을 시작으로 routing할 때 FR11 실행부는 바뀌지 않는다(대상 판정을 routing이 하므로). [I] 대안(세 칸을 FR11로 옮김)은 FR12·FR13 시작 목록을 바꾸므로 메인 결정이 필요하다.
- [F] **IO 실행**(`reobs/fr11base`, `work/fr11exec_base.txt`): FR11 시작 가운데 기록된 것 132개, 실행 15,576회(TB 첫 routing 밖 PC로 기록된 수; 계획의 15,600과의 차는 재관측 병합 기준의 차), run 8개(X1~X4 × case 68·94). 처음 frame: X1 68 659..807, X1 94 439..621, X2 68 633..873, X2 94 409..647, X3 68 628..873, X3 94 432..813, X4 68 661..1,135, X4 94 490..932. 기록되지 않은 시작 60개는 closure로 들어왔다. 그 가운데 앞 block과 같은 TB 안이라 따로 기록되지 않을 뿐 실행되는 것(직선 연속: 예 `b68a0` `b6ccc` `b7db2` `b7dd4` `bfcd0`)과 이 관측에서 실행되지 않는 분기 쪽(예: handler `b403e` 계열 `b403e`..`b40f6`, MULS 회전 `b413a`..`b4156`, `bfdb2`..`bfdca` → `b3e1c`..`b3e70`, `b4abc` `b4ac2`, `cd974`/`cd9b0`..`cda16`)이 섞여 있다.
- [F] 계획 표의 특이 항목 대조: 계산 점프 `b42b4` `c54ae`, live `JMP (A0)` `b4034`, TRAP `b3e58`, MULS 4(`b4176` `b417a` `b4184` `b4188`), MULU 1(`bfc2e`), MOVEM 3(`b4158` `b41d8` `b7d8c`), 자식 `b3dbc`(FR1, `b7d76` 2986) `b774a`(`b687e` 28ae) `c5592`(`c5432` 28ae) — 모두 ROM 바이트와 같다(`plan/D-2.dis.txt`).

## FR11 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **192 block, 564 명령, 2,470 byte, 32 범위**(시작 목록 SHA256 `144dc2bc…`(줄 형식) / `0b9d7519…`(계획 형식), 범위 byte를 이어 붙인 SHA256 `6af527431b91f558bc0431863ce5214b23433ec1e9caf2df7d711734b9d70e00`). 짝수 PC 1,235(내부 1,043). 기존 routing과 겹침 0(계획 단계와 V1 spec `build()`가 시작 192개 모두 `animation_objects_fr11_block`로 routing됨을 확인; 범위 안 짝수 PC 1,235개 전수 검사는 시험 `interior()`).

| 범위(CPU = 파일 오프셋) | byte | 시작 | SHA256(앞 16자) | 내용 [I] |
| --- | --- | --- | --- | --- |
| `70e42..70ea2` | 96 | 5 | `f8d3bdfe750d40ec` | FR10 `70e2a BPL`의 fall-through: `TST.W 9c` → bank anim 3 / `2000d0` / 110 또는 b / `2000d4` / 188 → `BRA.W 70efe`(FR10) |
| `70fac..70fc2` | 22 | 4 | `e84cfad5838aa889` | FR10 `70f94`의 음수 쪽: `TST.W D0; BPL; NEG.W`, `CMPI.W #30,D0; BCS 70fc2`(무부호), `MOVE.L #71468,(A6)`(쓰기만) |
| `b3e1c..b3e58` | 60 | 2 | `2b7a840ad6d8650f` | `bfdca JMP`: LONG `7a` 저장, `76..9d` 지우기, WORD `76`/`78` := D0/D1, `8ff4` → `BSET #2,95`, 저장 LONG = 0이면 TRAP `b3e58` |
| `b3e70..b3e74` | 4 | 1 | `eef31b07c740ea05` | `BRA.W b3ea2`(FR1) |
| `b4030..b4036` | 6 | 1 | `1cd5f915b61dee5b` | `MOVEA.L 76(A6),A0; JMP (A0)`(결정 2) |
| `b403e..b40f8` | 186 | 20 | `da7a66c31da7d74f` | handler `b403e`: 40000 쪽으로 감속(`ASR.L #3`), `b4aca` 경계 record와 비교해 LONG `36`/`3a` 반전, `43ea4` |
| `b4104..b41b2` | 174 | 12 | `9a4fc6c91659bfd5` | `b4104`(LONG 82/86 := 36/3a, `4be34`, WORD 92 := D4), `b411c`(입력 `1aa3a` bit 3 / 7, MULS 회전 `b4156`) |
| `b41be..b41f2` | 52 | 5 | `29e00dfc6e0c1536` | handler `b41be`: `b411c`, BYTE 15 bit 5, `b42b0`, `MOVEM.L 82,D0-D1`, WORD 8e |
| `b427e..b4294` | 22 | 3 | `eea9b8b4a119bd49` | BYTE 15 bit 7이면 LONG 36 -= 36 ASR 3; RTS |
| `b42b0..b42bc` | 12 | 2 | `06b8c04793d8b740` | `ANDI.W #ff,D0; JMP b42b8(PC,D0.W)`(결정 2), 칸 0 `b42b8 BRA.W b42c8` |
| `b42c8..b42ca` | 2 | 1 | `1ceeabf0c6a5a30b` | RTS |
| `b4abc..b4aca` | 14 | 2 | `2d65baa0173cf04b` | `MOVE.W 8c,D1; RTS` / `BSET #3,95; RTS` |
| `b67b2..b68ba` | 264 | 17 | `39c5864692e1bd4f` | U18 설치 값 `b67b2`: `496c2`, 표 anim(`b7f5c`), 위치 `b7e06` 둘, 설치 `b686e`(곧바로): `4be34`, `49fc6` C, 28ae 자식 `b774a`, `4970a`, ORI |
| `b6ca2..b6d90` | 238 | 17 | `444c01bd519aef79` | FR10 설치 값 `b6ca2`·`b6d82`: `49392` C, WORD 42 비교(BCLR/BSET #0,15), 표 anim(`b7f7c`), 설치 `b6d6a`(곧바로), `b7cfa`, `49fc6` C |
| `b6dac..b6e5e` | 178 | 8 | `cf9c05ac07749147` | 표 anim(`b7fc4`), 설치 `b6e50`(곧바로), `b7cfa`, `49fc6` C |
| `b6e8c..b6ec8` | 60 | 5 | `e5e2d9a63b66c9e1` | BYTE 9c 세기, 위치 `b7e06` → `BRA.W b76d2` |
| `b774a..b780c` | 194 | 11 | `ed4df124f9126bdb` | 28ae 자식 `b774a`: WORD 표 `b7f14` 소리(`8ebe`), 표 anim(`b7f64`), 설치 `b77f4`(곧바로): `43e34`, `49fc6` C, 쓰기만 `b7742` |
| `b7d4a..b7dd6` | 140 | 11 | `970ccefc86f9c28c` | script callback `b7d4a`(표 `4a500` + 1cc): `b7e06`, WORD 7c BLE, WORD 일곱 push + 2986 자식 `b3dbc`, `MOVEM.W (A7)+,D0-D6` C, `49214`, ORI, `4c2fa` |
| `bfb5a..bfb62` | 8 | 1 | `411203ef726d7037` | kind handler(record `b3484` + a): `MOVE.W #0,D0; BRA.W bfc2a` |
| `bfc2a..bfcfa` | 208 | 16 | `9f4a1b77cbd3da85` | MULU.W #8 record `bfdee`, bank 창 `2001c0` anim, 소리 둘(`8ebe`), BYTE a8, 설치 `bfcaa`(곧바로): sine `4411e`, `b4030` `b4958` `b4ab0` `b4334` |
| `bfdb2..bfdd0` | 30 | 3 | `b625f3d042a6ee55` | `ST.B a8`, `49a84`(D0 = f), WORD 표 `bfdd0`, `b4abc` → `JMP b3e1c` |
| `c5432..c54b2` | 128 | 11 | `e45cbbad18b31244` | FR3 설치 값 `c5432`: 28ae 자식 `c5592`, bank anim ba / `200080` / 144, 설치 `c5470`(곧바로): `4be06`, `49fc6` C, `4b54e` C, BYTE 5e 표 점프(결정 2) |
| `c54ca..c54ce` | 4 | 1 | `668cab27ff73d24d` | 표 `c54b2` 칸 6: `BRA.W c5540` |
| `c551e..c5520` | 2 | 1 | `1ceeabf0c6a5a30b` | RTS(`c5492 BCC`) |
| `c5540..c554c` | 12 | 1 | `78a668ee61afbafb` | WORD 54 := WORD 80, BYTE 5e := 0; RTS |
| `c5592..c5612` | 128 | 9 | `f946ff722f2e9479` | 28ae 자식 `c5592`: RNG `49a58`, `49290`, `491c4`, `c6a96`, bank anim e2 / `200094` / 20, 설치 `c5602`(곧바로): `4be2c`, `49fc6` C |
| `c5618..c561a` | 2 | 1 | `1ceeabf0c6a5a30b` | RTS |
| `cc836..cc83a` | 4 | 1 | `092c7d45683d94cb` | FR4 표 `cc82e`의 칸 2: `BRA.W cdc1c` |
| `cc842..cc846` | 4 | 1 | `46de0fab5dc624b3` | FR4 표 `cc82e`의 칸 5: `BRA.W cd7c6`(FR10) |
| `cd7e2..cd7e4` | 2 | 1 | `335d5d3529f1169f` | FR10 `cd7cc BPL`의 fall-through: `NEG.L D0` → FR10 `cd7e4` |
| `cd92e..cd93c` | 14 | 1 | `d242a15194d2ccff` | FR10 `cd8ee BNE`: LONG 7e := 0, WORD 2c := 100 → FR10 `cd93c` |
| `cd96c..cda34` | 200 | 17 | `5765e79c57b356b4` | FR10 `cd95a BPL`의 fall-through: WORD 8c 0..4 / 그 밖의 anim, (A6) := `cdafc`(FR10); RTS |

- [F] **진입**(현재 routing 기준 호출자, `work/refs_fr11_v1.out`):
  - 설치 값: `b67b2` ← U18 `b67a8`; `b6ca2` ← FR10 `b6c8a`(쓰기만이던 값); `b6d82` ← FR10 `b6c98`·FR11 `b6d78`; `c5432` ← FR3 `c541a`(그리고 routing 밖 `c5524`); 범위 안 곧바로 들어가는 설치 `b686e`(`b6868`) `b6d6a`(`b6d64`) `b6e50`(`b6e4a`) `b77f4`(`b77ee`) `bfcaa`(`bfca4`) `c5470`(`c546a`) `c5602`(`c55fc`).
  - 28ae 자식: `b774a` ← FR11 `b687e`; `c5592` ← FR11 `c5432`(그리고 routing 밖 `81cb0`). 2986 자식 `b3dbc`(FR1 routing)은 FR11 `b7d76`이 만든다.
  - 다른 실행부의 fall-through·분기: `70e42` ← FR10 `70e2a`(BPL 아닌 쪽), `70fac` ← FR10 `70f94`, `cd7e2` ← FR10 `cd7cc`, `cd92e` ← FR10 `cd8f4 BNE`, `cd96c` ← FR10 `cd95a`, `b3e1c` ← FR11 `bfdca JMP`(그리고 routing 밖 `c091e` `c1914` `c1af0` `c1b92`).
  - 계산 점프 착지: `cc836` `cc842` ← FR4 `cc82a`(표 `cc82e` 칸 2 / 5), `b41be` `b403e` ← FR11 `b4034 JMP (A0)`(결정 2), `b42b8` ← FR11 `b42b4`, `c54ca` ← FR11 `c54ae`, kind handler `bfb5a` ← FR1 `b3f3e`/`b3fc4 JMP (A0)`(kind record `b3484` + a의 handler LONG, FR1 결정 "routing이 판정"), script callback `b7d4a` ← interpreter `4a352`/`4a43c JSR (A1)`(script 표 `4a500` + 1cc의 LONG, ROM 파일 오프셋 `4a6cc`).
  - callee: `b4030` ← FR11 `bfcd8`(그리고 routing 밖 `bfd34` `c008a` `c01a8` `c0800` `c08e4` `c0956` … `d93fc`), `b411c` ← FR11 `b41be`(routing 밖 `b429e` `b42ac` BRA), `b42b0` ← FR11 `b41d4`, `b4abc` ← FR11 `bfdc4`(routing 밖 `c0910` `c190e` `c1aea` `c1b8c`), `b4ac2` ← FR11 `bfc9e`.
- [F] **설치 값**(`MOVE.L #v,(A6)`): 곧바로 들어감 `b686e` `b6d6a` `b6e50` `b77f4` `bfcaa` `c5470` `c5602`. 쓰고 RTS(다음 frame callback): `cdafc`(`cda2c`, FR10). **쓰기만**: `71468`(`70fbc`, FR10) `b68ba`(`b68a6`, routing 밖) `b6d82`(`b6d78`, FR11) `b7742`(`b7804`, FR1) `c53be`(`c5480`, FR3). 계산 설치는 없다(LONG `76` 쓰기는 결정 2).
- [F] **28ae / 2986 자식**(`MOVEA.L #v,A0` 뒤 `JSR 28ae`/`2986`): `b774a`(`b687e`, D0.W = 14), `c5592`(`c5432`, D0.W = a), `b3dbc`(`b7d76` 2986, D0.W = 14, A1 = 목록 머리 `100bf4`; FR1 실행부).

### 계산 점프와 표(결정 2)

- [F] **`b4034 JMP (A0)`**(block `b4030`, A0 = LONG `76(A6)`): FR4 방식대로 ROM 자료 writer가 만드는 목표만 허용한다. 이 PC를 부르는 item 객체(`b3dbc` 2986 자식 계열)의 LONG `76`을 쓰는 ROM 명령은 셋이다(ROM 전수 검색 `move.l …, $76(a6)`: `b3f02` `b402a` 그리고 다른 객체의 `b578c` `b57be` `b8734`·자식 복사 `b5912` `b8eae`).
  - `b3f02 MOVE.L A0,76(A6); MOVE.L A0,7a(A6)`(FR1): A0 = FR1 표 `b3dcc`의 칸 0..3이 고르는 `b41be` `b4036` `b42a2` `b403e`(`b3ddc`..`b3df4 LEA d(PC),A0`), 또는 `b3e1c`가 다시 꺼낸 LONG `7a`(= 앞의 같은 A0).
  - `b402a MOVE.L A0,76(A6); RTS`: 호출자 9곳의 A0 = `b42a2`(`c0944`), `c0924`(`c0fa8` `c1160` `c14c8` `c1668` `c17fe` `c1a40`), `b4294`(`c1bb0`).
  - [I] `b578c` `b57be` `b8734`(A0 := `4ae4a`가 돌려준 node 포인터)와 `b5912` `b8eae`(자식에게 LONG 76 복사)는 `b4030`을 부르지 않는 다른 객체(`b5xxx`·`b8xxx`)의 field다.
  - **규칙**: A0(LONG 전체)가 `b41be` `b4036` `b42a2` `b403e` `c0924` `b4294` 가운데 하나면 PC := A0(routing이 판정: `b41be` `b403e`는 FR11 block, `b4036` `b42a2` `c0924` `b4294`는 다음 dispatch의 `unsupported animation machine PC` = 선언 정지), 그 밖은 checked `unsupported animation objects fr11 jump target`. 관측에서 실행된 목표는 `b41be`·`b42a2`·`b4294`·`c0924`이고(`reobs/fr11base`: `b42a2` 2 run, `b4294` `c0924` 2 run), `b403e`는 closure로 들어왔다.
- [F] **`b42b4 JMP b42b8(PC,D0.W)`**(block `b42b0`, `ANDI.W #ff,D0` 뒤; 배수 곱 없음): 표 `b42b8..b42c8`(ROM 파일 오프셋 = CPU 주소), BRA.W 4칸: 0 `b42b8`→`b42c8`, 4 `b42bc`→`b42ca`, 8 `b42c0`→`b42da`, c `b42c4`→`b42ea`. 변위는 BYTE `97(A6)`이다(`b41cc MOVE.B 97(A6),D0`).
  - [F] ROM writer: item node의 BYTE `97`을 쓰는 것은 FR1 `b3f68 MOVE.B (A1),97(A6)`(kind record `b3484 + 10k`의 첫 BYTE)뿐이다(`b42b0`을 부르는 곳은 `b41d4` 하나). kind record 104개의 첫 BYTE는 {0, 4, c}다(0 91개, 4 8개, c 5개; item record `b3894 + 12m`이 고르는 kind 110개로 세면 0 93, 4 12, c 5). 다른 node의 writer(`30ee4` `3a662` 등)는 이 경로로 오지 않는다 [I].
  - **규칙**: 변위(D0.W) ∈ {0, 4, c}면 PC := `b42b8` + 변위(routing이 판정: 칸 0 `b42b8`만 FR11 block, `b42bc`는 routing 밖, `b42c4`는 FR12 실행 칸 = 선언 정지), 그 밖(칸 8 `b42c0` 포함: writer가 만들지 않음)은 checked jump-target 오류.
- [F] **`c54ae JMP c54b2(PC,D0.W)`**(block `c54a6`, `ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0` 뒤): 표 `c54b2..c551e`, BRA.W 27칸(칸 k → `c5540`(k = 0 1 6 8 14..26) 또는 `c5520`(k = 2..5 7 9..13)). 색인은 BYTE `5e(A6)`이고 같은 함수의 `c5496`이 `CMPI.B #1b,D0; BCC c5540`으로 0..1a로 묶는다(BYTE 5e의 writer는 충돌 처리 등 여럿 — `4b53c` `4bf32` 등; 그래서 범위는 writer가 아니라 이 guard가 정한다).
  - **규칙**(FR4 `cc7a8`·C10 `203ac`와 같은 꼴): 색인 ≤ 1a(변위 ≤ 68)면 PC := `c54b2` + 변위(routing이 판정: 칸 6 `c54ca`만 FR11 block, 칸 2 `c54ba`·9 `c54d6`은 FR13 실행 칸, 나머지는 routing 밖 = 선언 정지), 넘으면(guard를 건너뛴 `c54a6` 직접 진입) checked jump-target 오류.
- [F] **FR11이 받는 계산 착지**(기존 실행부의 규칙 그대로, FR11은 그 칸을 routing할 뿐이다): FR4 `cc82a JMP cc82e(PC,D0.W)`의 칸 `cc836`(2) `cc842`(5)(FR4 결정 2: routing이 판정), FR1 kind handler `JMP (A0)`(`b3f3e` `b3fc4`)의 `bfb5a`, interpreter `JSR (A1)`의 `b7d4a`.
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙. [F] 원본 값은 ROM 바이트):
  - LONG 표 `b7f5c`(`b67c4`/`b6800`), `b7f64`(`b777a`/`b77b6`), `b7f7c`(`b6cd8`/`b6d14`), `b7fc4`(`b6db8`/`b6df4`): 첨자 = D0.W(= WORD `8e`) × 4(`ADD.W` 둘, WORD 안에서 넘침, 부호 확장). 그 LONG의 WORD × 4가 bank 창 LONG 표(`2001a8`/`2001ac`가 가리킴)의 첨자다(FR10 `b6bb8`/`b6bf4`와 같은 꼴, 표만 다름).
  - WORD 표 `b7f14`(`b774a`; 첨자 = WORD `8e` × 2): 원본 `0d89 0d8c 0d88 0d8c`(소리 번호, `8ebe`로 넘김).
  - WORD 표 `4411e`/`4419e`(`b4156`; 첨자 = 2 × D7.W, D7 = |BYTE 98(A6)|(0..80), 부호 확장) — sine / cosine [I]. `bfcb2`는 `4411e` + 2 × (WORD a6 & 7f).
  - WORD 표 `bfdd0`(`bfdbe`; 첨자 = 2 × D0.W, D0 = `49a84`(D0 = f)의 결과) — 소리 번호 [I].
  - record `bfdee + 8k`(`bfc2a`; k = WORD D0 = kind handler `bfb5a`..`bfc26`의 즉치 0..19, MULU.W #8): LONG 0(bank 표 첨자), WORD 4 / 6(소리 번호; `bfc70`/`bfc80`이 LONG `9e`로 다시 읽음).
  - bank 창 LONG `2000d0`/`2000d4`(`70e4a` LONG 110 / `70e76` LONG 188), `200080`(`c5442` LONG 144), `200094`(`c55c0` LONG 20), `2001a8`/`2001ac`(표 anim), `2001c0`(`bfc2a`): FR4 `ofr4_bank_anim`과 같은 꼴.
  - 이 표·창 값은 모두 anim 자료 포인터(A1, `49f8c`로 넘김)·첨자·소리 번호다. 코드 주소로 점프하지 않는다.

### TRAP(결정 3)

- [F] **`TRAP #15` `b3e58`**: `b3e46 BSET #2,95(A6); MOVEA.L (A7)+,A0; CMPA.L #0,A0; BNE.W b3e70`의 fall-through다(`b3e1c`가 저장한 LONG `7a(A6)` = 0). FR5 결정 2와 같이 **단위에 넣지 않는다**(범위 `b3e1c..b3e58`가 그 PC를 뺌): `b3e46`이 PC := `b3e58`로 끝나고 다음 dispatch가 `unsupported animation machine PC`(전체 rollback)를 낸다. 시험은 `b3e58`을 정지로만 확인한다(정지 판정이 routing보다 먼저).
- [F] FR11 run이 지나갈 수 있는 FR1의 TRAP `b3eac`(`b3e70 → b3ea2`에서 WORD `76` ≥ 6e)도 V1·실제 ROM 차분의 선언 정지(`TRAPS`)에 넣었다(FR1 실행부 그대로).
- [F] 그 밖의 TRAP·ROM·RAM 실행·장치 쓰기는 없다(`MOVE`·`CLR`·`BSET`·`ADDQ`·`ADD.L`·`NEG.L` 등의 대상은 node·A0 node / record·스택).

### MULS / MULU / ASR / MOVEM(결정 4)

- [F] **MULS.W 4곳**(`b4156` 한 block): `MULS.W (A1,D7.W),D0` / `(A0,D7.W),D1` 두 번. 두 피연산자의 **하위 WORD를 부호 있는 16 bit**로 보고 곱한 **32 bit 결과**가 레지스터 LONG 전체가 된다(`ofr11_muls`: `int32` 곱, |곱| ≤ 2^30이라 넘침 없음, 무부호로 변환). 출처 WORD는 ROM 표를 live bus로 읽는다. 순서: D0 := `MOVEM.L 36`의 LONG ASR.L #8 → ASR.W #1(하위 WORD, 부호 유지) → NEG.W; D1도 같음(LONG 3a); D0 := D0 × cos, D1 := D1 × sin; D0 := (D0 + D1) ASR.L #8; D1.W := D0.W(상위 WORD 유지); D0 := D0 × cos, D1 := D1 × sin; LONG 36 += D0, LONG 3a += D1.
- [F] **MULU.W #8,D0**(`bfc2e`, block `bfc2a`): D0의 하위 WORD를 무부호로 × 8 한 32 bit가 D0이다. 바로 다음 `LEA (A0,D0.W),A0`가 D0.W만 부호 확장해 쓰고, D0은 `MOVE.L (A0),D0`이 덮는다. [F] 그래서 MULU / MULS·LONG 곱 변이는 관측할 수 없다(아래 변이 동치).
- [F] **ASR.L #n**(`b4064` #3 둘, `b413a` #1, `b4156` #8 셋, `b4288` #3): 부호 채움(`ofr11_asr`, FR10과 같음). **ASR.W #1**(`b4156`): 하위 WORD만, bit 15 유지(`ofr11_asr_word`).
- [F] **MOVEM 3곳**:
  - `b4158 MOVEM.L 36(A6),D0-D1`, `b41d8 MOVEM.L 82(A6),D0-D1`: 낮은 주소부터 D0, D1에 LONG(부호 확장 없음, flag 바뀌지 않음).
  - `b7d8c MOVEM.W (A7)+,D0-D6`: 낮은 주소부터 D0..D6에 WORD를 LONG으로 부호 확장해 넣고 A7 += 14, flag는 바뀌지 않는다(2986의 C를 `b7d90 BCC`가 읽음). 일곱 WORD는 `b7d5a`가 `#0 #0 #0 7e(A6) 7c(A6) #0 #0` 순서로 넣은 것이라 2986 복귀 뒤 D2 = WORD 7c, D3 = WORD 7e(부호 확장), 나머지 0이다. 홀수 A7은 checked 오류다. Unknown C면 pop보다 먼저 checked carry 오류(FR10 `b7a78`과 같은 순서).

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `28ae` `2986` `8ebe` `8ff4` `1aa3a` `43e34` `43ea4` `491c4` `49214` `49290` `49392` `496c2` `4970a` `49a58` `49a84` `49f8c` `49fc6` `4b54e` `4be06` `4be2c` `4be34` `4c2fa` `b3ea2` `b4334` `b4958` `b4ab0` `b4aca` `b76d2` `b7cfa` `b7e06` `c6a96` `cdc1c`, FR10 `70efe` `70fc2` `cd7c6` `cd7e4` `cd93c`, RTS 복귀(`b40f6` `b4116` `b4292` `b42c8` `b4abc` `b4ac2` `b780a` `b7dd4` `bfcf8` `c551e` `c554a` `c5618` `cda32`).
- [F] **뒤 단위 정지**(실행되지만 뒤 단위가 가짐; V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS` 앞 5개): FR12 `b41f2`(`b41e2 BNE`) `b6e5e`(`b6e5a BCC`의 Set 쪽) `c5612`(`c560e BCC`의 Set 쪽), FR13 `b6d90`(`b6d8c BCC`의 Set 쪽) `bfcfa`(`bfcee BNE`). 계산 점프의 비FR11 목표(`b4036` `b42a2` `c0924` `b4294`, `b42bc` `b42c4`, `c54b2` 표의 26칸)와 TRAP `b3e58`도 정지다.
  - FR11 run이 지나갈 수 있는 FR10의 남은 정지 6개(`70f8e` `b6c58` `70f60` `70fcc` `70ff8` `71028`)와 C1~C9의 남은 정지 12개(pc10 `EXIT_STOPS[:12]`)도 fr11 `EXIT_STOPS`(모두 23개)에 넣었다.
- [F] 직선 fall-through로 범위를 벗어나는 곳: `70fbc`(→ FR10 `70fc2`), `cd7e2`(→ FR10 `cd7e4`), `cd92e`(→ FR10 `cd93c`), `b3e46`(→ TRAP `b3e58`), 그리고 위 뒤 단위 정지 셋(`b6d8c` `b6e5a` `c560e`의 Set 쪽). 재관측에서 새로 보인 PC가 없어 가려진 연속은 없다(결정 1).

### block 경계·복귀를 넘는 flag(결정 5)

FR10 방식대로 block 첫 명령부터 flag를 정하는 명령까지 훑었다(`work/flagscan_fr11_v1.txt`). 그리고 FR11 출구 대상·RTS 복귀 PC에서 FR11이 남긴 flag를 읽는 곳을 따로 훑었다(`tools/exitflags.py` → `work/exitflags_fr11.txt`: 양쪽 분기를 따라 40 명령까지; 대상 `b3ea2` `b76d2` `cdc1c` `70efe` `70fc2` `cd7c6` `cd7e4` `cd93c` `b41f2` `b6d90` `b6e5e` `bfcfa` `c5612` `bfcde` `b41c2` `b41d8` `bfca4` `bfdca` `b40f8` `b41b2` `b4294`). X를 읽는 명령은 없다.

- [F] **C 소비 block 11개**(Clear 쪽 / Set 쪽; Unknown C면 `objects fr11 caller requires known carry`): `b687a BCC b68b6`·`b6d74 BCC b6d7e`·`b6e5a BCC b6e8c`·`b7800 BCC b780a`·`c547c BCC c5486`·`c560e BCC c5618`(`49fc6`), `b688e BCC b68a0`(`28ae`), `b6cac BCC b6ccc`·`b6d8c BCC b6dac`(`49392`), `c5492 BCC c551e`(`4b54e`), `b7d8c MOVEM.W (A7)+,D0-D6; BCC b7db2`(`2986`; MOVEM은 flag를 바꾸지 않음). 생산자 쪽은 모두 기존 실행부가 known C를 돌려준다(dispatcher carry 목록의 기존 소비자들과 같은 생산자).
  - [F] `b7d8c`의 Clear 쪽(`b7db2`, 2986 안의 28ae 실패 `290e`)은 기존 2986 실행부가 caller X를 알 때만(`e8a48`) 계속하는 checked 오류다(`cue wrapper failure requires known caller X`; C7 결정 6·7의 한계 그대로). 그래서 이 쪽은 단위 시험의 선언 C 행으로만 확인한다(V1 보고의 빠진 후속).
- [F] **C를 만드는 block**: `b689c ORI.B #1,CCR`(→ `b68a0 MOVE.W`가 C를 지움)·`b7dae ORI.B #1,CCR`(→ `b7db2 MOVEQ`가 지움). 읽는 곳이 없어 C++는 Set을 남기고 다음 dispatch에서 Unknown이 된다(시험 분류 Set).
- [F] **C를 넘기는 FR11 block은 없다**. RTS로 돌려주지만 읽는 쪽이 없는 flag: `c551e`(`c5492`의 Clear) `c5618`(`49fc6`의 Clear) `b780a` `c554a` `cda32`(node callback의 RTS → object loop), `b40f6` `b4292`(`b4030` 호출자 `bfcde JSR`·routing 밖 `c0956 BTST` 등이 flag를 읽지 않음), `b4116`(→ `b41c2 BTST`) `b42c8`(→ `b41d8 MOVEM`) `b4abc`(→ `bfdca JMP`·routing 밖 `c0916 MOVEA`) `b4ac2`(→ `bfca4 MOVE.L`) `bfcf8`·`b7dd4`(kind handler·script callback의 RTS: interpreter 복귀 `4a354`/`4a43e`는 `MOVE.W (A7)+,…`로 시작).
- [F] **Z / N이 경계를 넘는 곳은 없다**. 모든 `Bcc`/`Scc`는 같은 block 안의 명령이 정한 flag를 읽는다: `70e42 TST.W` `70fac TST.W D0`(BPL) `70fb4 CMPI.W #30`(BCS 무부호) `b3e46 CMPA.L #0`(LONG) `b403e TST.W 36`(BGE: N만) `b405a TST.W 3a`(BGT 부호) `b4064 TST.W 8c` `b4084`/`b40b8 TST.W`(BMI) `b408c`/`b40c0 CMPI.W`(BLE 부호) `b40a6`/`b40dc CMPI.W`(BGE 부호) `b411c`/`b41c2`/`b427e`/`b6cbc` `BTST` `b4132 ANDI.B #8` `b419e ANDI.B #80` `b413a MOVE.B`(BPL) `b41d8 MOVE.W 8e` `b67b8`/`b6ccc`/`b6dac`/`b776e CMPI.W #0` `b6cb0 CMP.W 42(A0)`(BLE 부호) `b6e8c TST.B` `b6e94 SUBQ.B`(새 BYTE) `b7d52 TST.W 7c`(BLE 부호) `b7db2 BTST #0,15` `bfc90`/`bfcaa TST.B a8` `bfcb2 MOVE.W (A0,D0.W)` `bfcd0 MOVE.B D0,12(A6)`(BYTE Z) `bfcea BTST #2,D0`(레지스터 bit) `c5496 CMPI.B #1b`(BCC 무부호 BYTE) `cd96c MOVE.W 8c`, `cd98e`..`cd9f4 CMPI.W`.

### IO 실행 run과 frame

- [F] 실행 run 8개(X1~X4 × case 68·94), 처음 frame은 위 "재확인과 범위". FR11 객체 node는 pool `100800..104c00`의 여러 node다(`work/natscan_fr11.out`: 설치 값·자식 callback `b6ca2` `b6d6a` `b6d82` `b6e50` `b67b2` `b686e` `b77f4` `bfcaa` `c5432` `c5470` `c5602`, FR1 item 자식 `b3dbc`).
- [F] **IO 예측(FR11 연결)**: 6,751 → **7,383**(+632; 재관측 `reobs/fr11v1`, 계획과 같음). 첫 정지는 8 run 모두 FR12다(위 "재확인과 범위"). [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다.
- [F] 원래 IO 관측은 FR11 코드를 실행하지 않는다(계획 §10.4: X run에서만 실행). 일치 173,966은 그대로여야 한다(작업자는 돌리지 않음; 메인 runner).

## 공통 규칙·native 검증 계획

FR2..FR10, C1~C10 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr11.cpp`, 함수 `animation_objects_fr11_block`. 오류 문자열은 `unsupported animation objects fr11 PC`(범위 안 내부 PC 직접 진입), `objects fr11 caller requires known carry`(C 소비 block 11개에 Unknown C), `unsupported animation objects fr11 jump target`(결정 2의 허용 밖 목표) 세 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(32 범위, C10 줄 뒤; `)ok=animation_objects_fr11_block(c);`를 같은 줄에 둔다), `carry_preserving_pc`의 C10 묶음 뒤에 주석 달린 case 묶음 하나(소비자 11), `animation_machine_internal.h`에 선언 하나(C10 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# objects FR11 refresh:` 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 곧바로 들어감 7개는 쓰고 그 값으로 들어가고, `cda2c`(`cdafc`)는 쓰고 RTS, 쓰기만 하는 5개는 쓰고 다음 block으로 간다.
- **자료 읽기**(live bus): node field(A6: BYTE `12` `14` `15` `19` `5e` `92` `95` `97` `9c` `9d` `a8`, WORD `1e` `20` `2c` `36`(TST) `3a`(TST) `42` `46` `54` `68` `76` `78` `7c` `7e` `80` `8a` `8c` `8e` `92` `98` `a2` `a6`, LONG `0` `22` `36` `3a` `64` `76` `7a` `7e` `82` `86` `96` `98` `9e`), A0 record / node(WORD `0` `2` `4` `6` — `b408c`..`b40dc`, WORD `42` — `b6cb0`, WORD `8e` / `76`..`7e` 쓰기 — `b68a0` / `b7d94`), 스택(`b3e1c`/`b3e46`의 LONG, `b7d5a`/`b7d8c`의 WORD 일곱), 고정 ROM·bank(위 "계산 점프와 표"). 단위 시험은 고정 ROM·bank 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): ROM 표 `b7f14..b8004`(WORD 4 + LONG 58: 작은 bank 첨자, 칸 `b7f5c` = `00038002`, `b7f68` = `1234000a`, `b7f7c` = `fffe`), `4411e..4439e`(WORD 320, WORD 첨자 0 / 3f는 0), `bfdd0..bfebe`(WORD 15 + record 26), bank 창 LONG `2000d0` → `2a1000`(+110) `2000d4` → `2a2000`(+188) `200080` → `2a7000`(+144) `200094` → `2a5000`(+20) `2001a8` → `2a3000` `2001ac` → `2a4000` `2001c0` → `2a6000`(각 −10..+80의 LONG 36개). 영역 끝은 다음 코드 앞이다(`4439e` `bfec6`은 코드, `b8004` 뒤는 자료 계속). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W`/`ADD.W`/`ANDI.W`/`SUBI.W`/`SUBQ.W`/`NEG.W`/`ASR.W`/`CLR.W` 레지스터, `MOVE.B`/`ANDI.B`/`NEG.B` 레지스터, `ADDI.W`/`ADDQ.W`/`SUBQ.B` 메모리). `MOVE.L`·`MOVEA.L`·`MOVEQ`·`LEA`·`CLR.L`·`ADD.L`·`SUB.L`·`NEG.L`·`ASR.L`·`MULS.W`·`MULU.W`·`MOVEM`은 LONG 전체(mod 2^32). 비교: `CMPI.W`+`BLE`/`BGE`, `CMP.W`+`BLE`, `TST.W`+`BGT`/`BLE`은 부호 있는 WORD(V를 포함한 정확한 부호 비교), `TST.W`+`BGE`/`BMI`/`BPL`은 N만, `CMPI.W #30`+`BCS`와 `CMPI.B #1b`+`BCC`는 무부호. 표 첨자 `(An,Dn.W)`·`(PC,Dn.W)`는 부호 확장. bit: `BTST/BSET/BCLR #n,d(A6)`(메모리 BYTE, bit mod 8), `BTST #2,D0`(레지스터 LONG bit).

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `63f7d470922dfab836b19417f2a16dba5d170d3424906a13c04ad69f53a48eb7` → `e99fe5dbc8192ae377b9384c30fa821ada4a2fbf23aeca777c81fed5f115a815`, `animation_machine_internal.h` `f1180a35ac8dab11f98c309ba7c890110e5e141f63553c3239c51375fb1c7f4a` → `8cf2b547c1c11023096672ee7db3418811215596a99e907c494a91ed663b2296`(옛 값은 `# objects FR11 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 작업 트리와 scratch clone root에서 확인했다(아래 "검증 수치").
- [F] **FR10 시험 생성기·시험**(`tools/generate_animation_machine_objects_fr10_test_table.py`, `engine/tests/animation_machine_objects_fr10_test.cpp`; 오류 행. 이전 = FR11 PC에서 `unsupported animation machine PC`. FR11이 그 PC를 routing해서 C++가 FR11 코드를 실행하므로 바뀜. C9·C10 선례대로 실패 PC를 지키거나 경로를 따라 옮김):
  - `error-70e2a-then-70e42` → `error-70e2a-then-70e4a`: FR11 `70e42` → `70e4a`의 bank anim이 FR10 시험에 선언되지 않은 bank LONG `2a1110`을 읽어 `missing or ambiguous physical program bus ROM byte`.
  - `error-cd7cc-then-cd7e2` → `error-cd7cc-then-cd7e4`: 홀수 node(A6 = `10e001`): FR11 `cd7e2 NEG.L`(메모리 접근 없음) 뒤 FR10 `cd7e4`의 LONG `7e(A6)` 쓰기가 `invalid animation machine write size/alignment`.
  - `error-cd8ee-then-cd92e`: 홀수 node: FR11 `cd92e`의 LONG `7e(A6)` 쓰기가 alignment 오류, 실패 PC `cd92e` 그대로(이전 메시지 `unsupported animation machine PC`).
  - `error-cd95a-then-cd96c`: 홀수 node: FR11 `cd96c`의 WORD `8c(A6)` 읽기가 `program bus requires even WORD/LONG address`, 실패 PC 그대로.
  - `error-70f94-then-70fac` → `error-70f94-then-70fcc`: FR11 `70fac`(D0 = ffff → NEG.W 1 < 30) → FR10 `70fc2`(BYTE 82 bit 7 = 1) → FR13 정지 `70fcc`(`unsupported animation machine PC`).
  - 생성기를 다시 돌려 그 5행만 바뀜을 확인했다(`work/fr10_test_before.cpp` 대비 diff). 시험 줄의 fixture 수는 그대로다(fr10 1,074).
- [F] **V1 spec**:
  - `fr10.py`: `ROUTED_LATER`에 FR11 진입 `70e42` `70fac` `cd7e2` `cd92e` `cd96c`를 더했다(이전: C10 진입 14개만). 그 run은 그 PC에서 계속 멈춘다(`EXIT_STOPS`는 그대로). 오류 fixture 5개를 위 생성기와 같은 뜻으로 바꿨다: `70e2a-then-70e4a`(홀수 A7: FR11 `70e4a`의 `JSR 49f8c` push가 `program bus requires even WORD/LONG address`; 원본 ROM에서는 bank 읽기가 성공하므로 스택으로 실패시킴, WORD `9c` := 0 선언), `cd7cc-then-cd7e4`·`cd8ee-then-cd92e`·`cd95a-then-cd96c`(홀수 node), `70f94-then-70fcc`(BYTE `82` := 80 선언).
  - `pc10.py`: `ROUTED_LATER` `()` → (`70e42` `70fac` `cd7e2` `cd92e` `cd96c`), 두 번째 확인 `for t in EXIT_STOPS: require(unit_of(t) is None)` → `is None or t in ROUTED_LATER`(C10의 fr10 수정과 같은 방식).
- [F] **바뀌지 않음(확인)**: 저장소 tools·시험에서 FR11 범위 안 PC(와 표 칸·handler `b42bc` `b42c0` `b42c4` `c54b2` `c54ba` `c54d6` `b4036` `b42a2` `c0924` `b4294` `b3e58`)를 쓰는 곳은 전수 검색 `tools/fr11refs_repo.py` → `work/fr11refs_repo_v1.out`으로 찾았다.
  - 정지 전용·값 전용 행(그 PC에서 run을 멈추는 행이거나 레지스터·RAM 값; 정지 검사가 dispatch보다 먼저라 routing이 바뀌어도 같음): FR1 시험(`b3ddc`..`b3df4`의 A0 값 `b41be` `b4036` `b42a2` `b403e`, 정지 `b3ea2`), FR3 시험(`c5432` 설치 값·범위 끝), FR4 시험(`TARGETS`의 `cc836` `cc842` 정지), U18 시험(`b67b2` 설치 값), FR10 시험(정지 `70e42` `70fac` `cd7e2` `cd92e` `cd96c`·이웃 목록·설치 값 `b6ca2` `b6d82`), B1a 시험·spec(범위 끝 `b7d4a`).
  - 생성기·관측기 주석·자료: `generate_..._fr1_test_table.py`(주석), `observe_animation_machine_objects_g2.py`(관측 시점 기록).
  - `make -j4 all test`가 위 둘(FR10 생성기 행, 아래 수치) 말고 기존 시험이 모두 그대로 통과함을 확인했다.
- [I] 원래 IO 관측과 frame 비교(d1·controller·irq·demo)는 FR11 코드를 실행하지 않으므로 결과가 같아야 한다. 메인 runner가 확인한다.

## 결정

1. **범위: 192 block, 32 범위(계획 그대로).** 가상 routing 재관측에서 새로 보인 PC가 없고(숨은 직선 block 0), 범위 밖에서 범위 안 비시작 PC로 오는 실제 분기도 없다. 계획의 실행 칸 `b42c4`(FR12)·`c54ba` `c54d6`(FR13)는 계획 배정대로 두고 FR11 표 점프의 정지로 다룬다. 예측 7,383(+632).
2. **계산 점프**: `b4034 JMP (A0)`은 ROM writer가 만드는 handler 6개(`b41be` `b4036` `b42a2` `b403e` `c0924` `b4294`, LONG 비교)만, `b42b4`는 변위 0 / 4 / c(kind record의 BYTE 97)만, `c54ae`는 색인 ≤ 1a만 허용하고 대상은 routing이 판정한다. 그 밖은 checked `unsupported animation objects fr11 jump target`. 고정 ROM 표와 bank 창 LONG은 live bus로 읽고 상한을 검사하지 않는다.
3. **TRAP #15 `b3e58`**: 단위 밖 경계(FR5 결정 2). `b3e46`이 PC := `b3e58`로 끝나고 다음 dispatch가 전체 rollback.
4. **정수 연산**: MULS.W는 부호 있는 하위 WORD 곱의 32 bit, MULU.W #8은 무부호 하위 WORD 곱의 32 bit, ASR.L은 부호 채움, ASR.W #1은 하위 WORD, `MOVEM.W (A7)+`는 부호 확장(낮은 주소가 D0), `MOVEM.L`은 LONG.
5. **flag.** C 소비자 11개는 known C를 읽거나 checked 오류. `b689c` `b7dae`는 Set(읽는 곳 없음). C를 넘기는 block·Z / N 경계는 없다.
6. **V1 natural family.** 확장 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)이 읽는다. pool `100800..104c00`의 node가 FR11 node 진입(설치 값·자식 callback 13개, kind handler `bfb5a`) 또는 FR1 item 자식 `b3dbc`를 callback LONG으로 가진 frame 163개(`work/natural_fr11.json`: run과 callback마다 처음·처음 여덟 가운데·마지막 frame)를 쓴다.
7. **앞 단위 spec·시험.** FR10의 뒤 단위 정지 가운데 FR11 진입 5개를 fr10·pc10의 `ROUTED_LATER`에 두어 그 run은 계속 그 PC에서 멈춘다. 오류 fixture는 실패 PC를 지키거나 경로를 따라 옮긴다(위).
8. **다음.** FR11 연결로 확장 관측 IO 7,383(+632)을 메인 runner가 확인한다. 다음 단위 FR12는 계획 시작 목록에 `b42c4` `b4304`(FR11 정지)를 가지며, 표 `b42b8`의 칸 판정은 FR11 실행부가 이미 routing에 맡긴다.

## 미확인

- [U] node field·전역 값의 의미(BYTE `5e` `92` `95` `97` `9c` `9d` `a8`, WORD `7c` `7e` `8c` `8e` `98` `a2` `a6`, LONG `36` `3a` `76` `7a` `7e` `82` `86` `9e`, 표 `b7f14` `b7f5c` `b7f64` `b7f7c` `b7fc4` `4411e` `4419e` `bfdd0` `bfdee`). 이름(item 객체, handler, 회전, sine / cosine 표, kind handler, 소리 번호)은 동작에서 붙인 [I]이다. 어떤 적·item인지는 정하지 않았다.
- [U] IO 관측에서 실행되지 않은 이 단위의 분기 쪽(handler `b403e` 계열, MULS 회전 `b413a`..`b4156`, `bfdb2` → `b3e1c` → TRAP `b3e58` 경로, `b4abc` `b4ac2`, `cd96c`의 anim 칸 대부분)은 V1 선언 상태·natural·실제 ROM 차분·단위 시험으로만 확인했다.
- [U] `b7d8c`의 Clear 쪽(2986 안의 28ae 실패)은 기존 2986 실행부의 caller-X 한계로 C++에서 checked 오류다(선언 C 행만).
- [U] 표 `b42b8`의 칸 4 `b42bc`·`c54b2`의 실행되지 않은 칸 22개, handler `b4036`이 실제로 쓰이는 조건.
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC).
- [U] natural fixture의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C10과 같음).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr11.cpp`(case label 192 = `starts_fr11_final.txt`와 집합 일치; 공용 함수 `ofr11_get` `ofr11_put` `ofr11_bit` `ofr11_btst` `ofr11_test` `ofr11_carry` `ofr11_install` `ofr11_asr` `ofr11_asr_word` `ofr11_signed_word` `ofr11_muls` `ofr11_add` `ofr11_neg` `ofr11_bank_anim` `ofr11_table_anim` `ofr11_anim` `ofr11_kind` `ofr11_select` `ofr11_offsets` `ofr11_offsets_call` `ofr11_handler`), `engine/tests/animation_machine_objects_fr11_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_e`), `tools/generate_animation_machine_objects_fr11_test_table.py`(생성기; FR10 생성기 꼴, 계산 점프의 결정 2 밖 착지를 버림, 계산 점프 single 행은 허용 목표를 모두 hint로 둠(`b4030` handler 6, `b42b0` 0 / 4 / c, `c54a6` 0..1a), 2986 안의 `290e` 실패 사슬을 버림, V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 95초), `tools/unit_fixture_specs/fr11.py`(V1 spec; FR10 spec의 공용 부분 + C10 spec의 계산 점프 처리(`JUMP_TARGETS` `JUMP_PCS`), 단위 부분 교체, `EXIT_STOPS`(23), `TRAPS`(`b3e58` `b3eac`), `CONSUMERS`(11), `SET_SET`(`b689c` `b7dae`), `NATURAL_ENTRIES`(node 진입 14 + `b3dbc`), natural family는 확장 관측 pack). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `work/starts_fr11_final.txt`(SHA256 `144dc2bc…`).

- **`70e42..70ea2`(5)**: `70e42 70e4a 70e72 70e76 70e9e`
- **`70fac..70fc2`(4)**: `70fac 70fb2 70fb4 70fbc`
- **`b3e1c..b3e58`(2)**: `b3e1c b3e46`
- **`b3e70..b3e74`(1)**: `b3e70`
- **`b4030..b4036`(1)**: `b4030`
- **`b403e..b40f8`(20)**: `b403e b4058 b405a b4062 b4064 b4080 b4084 b408c b409e b40a2 b40a6 b40b4 b40b8 b40c0 b40d4 b40d8 b40dc b40ec b40f0 b40f6`
- **`b4104..b41b2`(12)**: `b4104 b4116 b411c b412c b4132 b413a b4154 b4156 b4198 b419e b41a6 b41ae`
- **`b41be..b41f2`(5)**: `b41be b41c2 b41cc b41d8 b41e6`
- **`b427e..b4294`(3)**: `b427e b4288 b4292`
- **`b42b0..b42bc`(2)**: `b42b0 b42b8`
- **`b42c8..b42ca`(1)**: `b42c8`
- **`b4abc..b4aca`(2)**: `b4abc b4ac2`
- **`b67b2..b68ba`(17)**: `b67b2 b67b8 b67c4 b67fc b6800 b6838 b6850 b6868 b686e b6874 b687a b687e b688e b6892 b689c b68a0 b68b6`
- **`b6ca2..b6d90`(17)**: `b6ca2 b6cac b6cb0 b6cbc b6cc6 b6ccc b6cd8 b6d10 b6d14 b6d4c b6d6a b6d6e b6d74 b6d78 b6d7e b6d82 b6d8c`
- **`b6dac..b6e5e`(8)**: `b6dac b6db8 b6df0 b6df4 b6e2c b6e50 b6e54 b6e5a`
- **`b6e8c..b6ec8`(5)**: `b6e8c b6e94 b6e9c b6eb4 b6ec4`
- **`b774a..b780c`(11)**: `b774a b776e b777a b77b2 b77b6 b77ee b77f4 b77fa b7800 b7804 b780a`
- **`b7d4a..b7dd6`(11)**: `b7d4a b7d52 b7d5a b7d8c b7d94 b7dae b7db2 b7dc6 b7dc8 b7dce b7dd4`
- **`bfb5a..bfb62`(1)**: `bfb5a`
- **`bfc2a..bfcfa`(16)**: `bfc2a bfc70 bfc80 bfc90 bfc9e bfca4 bfcaa bfcb2 bfcce bfcd0 bfcd8 bfcde bfce4 bfcea bfcf2 bfcf8`
- **`bfdb2..bfdd0`(3)**: `bfdb2 bfdbe bfdca`
- **`c5432..c54b2`(11)**: `c5432 c5442 c546a c5470 c5476 c547c c5480 c5486 c5492 c5496 c54a6`
- **`c54ca..c54ce`(1)**: `c54ca`
- **`c551e..c5520`(1)**: `c551e`
- **`c5540..c554c`(1)**: `c5540`
- **`c5592..c5612`(9)**: `c5592 c5598 c55a8 c55ae c55c0 c55f4 c5602 c5608 c560e`
- **`c5618..c561a`(1)**: `c5618`
- **`cc836..cc83a`(1)**: `cc836`
- **`cc842..cc846`(1)**: `cc842`
- **`cd7e2..cd7e4`(1)**: `cd7e2`
- **`cd92e..cd93c`(1)**: `cd92e`
- **`cd96c..cda34`(17)**: `cd96c cd974 cd98a cd98e cd996 cd9ac cd9b0 cd9b8 cd9ce cd9d2 cd9da cd9f0 cd9f4 cd9fc cda12 cda16 cda2c`

## 검증 수치

작업자 최종 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j4 all test`(최종 실행부·시험; FR11 실행부와 `animation_machine.cpp`를 다시 compile): 종료 0, 경고 0, Assert 0, Python 310 OK(`trial_logs/make_final.log`). FR11 시험 줄: `animation machine objects fr11: 958 fixtures (578 single-block, 272 path, 18 producer chain, 22 declared C, 68 checked error (15 with a later failing PC), 42 kept C), 192 blocks, 4586 calls, 110157 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 출구 중 stop이 아닌 것 0(계산 점프의 비FR11 목표 32개와 TRAP `b3e58` 포함), 실제 사슬 3개(`b687e`→`b688e`(`28ae`), `b6ca2`→`b6cac`·`b6d82`→`b6d8c`(`49392`)). `49fc6` 사슬 여섯은 `49fc6`이 bank 장치에 써서 native run이 버려졌고, `c5486`(`4b54e`)은 Clear만, `b7d5a`(`2986`)는 Set만 나와(Clear 쪽은 2986 caller-X 오류) 선언 C 행만 있다. 생성기를 다시 돌려 FR11 시험 파일이 바이트 단위로 같음을 확인했다(SHA256 `dfd169bde9a6d800…`, `trial_logs/gen_repro.log`). FR10 시험 줄은 fixture 1,074 그대로(오류 행 다섯만 바뀜), pc10 979 그대로.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, `work/ubsan.sh`, FR11 시험): 빌드 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_build.log` `ubsan_fr11.log`).
- [F] V1 fr11(작업자, `--workers 3`): fixture 2,170개(match 1,075, error 1,085, mismatch 10; natural 264) failed 0, `ok` true, 방문 시작 192/192, carry oracle Unknown/Clear/Set = 933/107/35(`trial_logs/v1_fr11_try1.log`, `work/v1/fr11_try1/report.json`). spec 보고의 빠진 후속 `b7d8c`→`b7db2`와 도달 못한 분기 결과 (`b7d90`, `b7db2`)는 2986 안의 28ae 실패(Clear) 쪽이다(C++ caller-X checked 오류, 위 flag 절; C7 spec의 `22704`와 같은 처리).
- [F] V1 회귀(작업자, `work/v1_regs.sh`, `--workers 3`; `work/v1/v1_regs_main.txt` `v1_regs.txt`): pc1 1,264, pc2 1,743, pc3 1,829, pc4 1,873, pc5 1,755, pc6 1,856, pc7 2,077, pc8 986, pc9 2,347, pc10 1,334, se1 2,102, fr9 1,415, fr10 2,170(모두 failed 0, `ok` true; C10 기록과 같은 수). FR11 PC를 정지·갈래·값으로 가진 fr1 1,631, fr3 1,458, fr4 1,629, b1a 2,801도 돌렸다(모두 failed 0, `ok` true). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·op, WORD/BYTE → LONG, 복귀 PC·호출 대상, carry tag, mask, 상수·설치 값, `ofr11_*` helper 인자) + 손으로 고른 helper·block 변이(MULS.W의 부호 없는 곱·한쪽만 부호·WORD 결과·LONG 피연산자, 회전 `b4156`의 표 교환·합/차·ASR 폭·MOVE.W 폭·두 번째 곱 교환·ADD 교환·색인 부호 확장, MULU.W #8의 LONG 곱·부호 곱·×4·색인 부호 확장, ASR.L 논리·채움, ASR.W 논리·LONG, 부호 / 무부호 WORD 비교(`b405a` `b408c` `b40a6` `b40c0` `b40dc` `b6cb0` `b7d52` `70fb4`), 계산 점프 `b4030`(목록 밖 허용·24 bit 비교·목록 축소·값 바꿈)·`b42b0`(8 허용·guard 없음·4 금지·기준·LONG AND)·`c54a6`(한계 6c / 64·guard 없음·×2·AND 없음), `c5496`(부호 비교·지우기 없음), `MOVEM.W (A7)+`(부호 확장 없음·WORD·역순·여섯·carry 검사 순서), 일곱 push의 순서·개수·A1, `MOVEM.L 82`의 교환, `b3e1c`의 CLR 개수·A0·push, `b3e46`의 WORD 비교·A0, `b413a`·`b4154`·`b4288`·`bfcb2`·`bfcce`·`bfcd0`·`bfcea`·`bfdbe`·`c5598`·`c55ae`·`cd7e2`·`70fb2` 폭 등) + dispatcher carry 목록 11개·범위 38개를 적용해 만든 것, 809개; `--workers 4`): 1회째 `killed 776 of 809`(`trial_logs/mut_first.log`). 생존 33개 중 7개는 시험 빈틈이었고 규칙 `rules_e`와 합성 byte 둘(`bfdd8` = `0005`, sine 칸 10 = `1200`)로 메웠다(`b6e2c`의 CLR.L 64, `bfc2a`의 WORD MULU 색인(D0.W `1ffd`: −18), `bfc90`·`bfcaa`의 TST.B a8, `bfcb2`의 WORD BEQ, `c5540`의 CLR.B 5e, 표 anim 첫 색인의 부호 확장; `trial_logs/mut_gaps.log`). 남은 26개는 동치다(`mut/equivalents.txt`, 사례별 이유: 곧 덮어쓰는 레지스터 상위 bit(표 anim의 ADD.W·LSL, `b4156`의 ASR.W·NEG.W·MOVE.W, `bfc2a`의 MULU LONG·MULS — 하위 16 bit가 같고 D0은 곧 MOVE.L로 덮임), 다음 `MOVE.L #v,98(A6)`이 덮는 `96(A6)`의 하위 WORD 여섯, `MOVEQ #0` 뒤의 BYTE 쓰기, 이미 지워진 bit의 mask 둘, BYTE 값의 WORD 비교 넷, 결과를 쓰지 않는 CMPI 크기, 8 미만 bit 번호, `am_write`·양수 변위의 자체 성질 둘, `b4156`의 색인 부호 확장(D7 = 0..80만 도달; 음수 색인은 표 앞 코드라 합성 자료로 선언할 수 없음)). 규칙을 더한 뒤 전체 2회째 `killed 783 of 809`(`trial_logs/mut_second.log`), 남은 26개가 동치 목록과 같다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`, 메인 runner용), `real_fr11.py`(C10 harness에 FR11 world(`fr11_world`: handler LONG 76 / 7a, BYTE 97, WORD 8e, LONG 9e, A0 record `FR11_REC` 등)·소비자 11·선언 정지(FR11의 뒤 단위 정지 5, TRAP `b3e58` `b3eac`, FR10·C1~C9의 남은 정지, 계산 점프의 routing 밖 목표 `UNR_FR11TAB`)·`cb` 진입에 FR11로 넘겨주는 FR10 `70e2a` `70f94` `cd7cc` `cd8ee` `cd95a`, FR1 `b3dbc`, FR11 `bfcd8`; 계산 점프 착지를 trace 전체에서 대조(`ALLOWED_FR11` = handler 6, 표 `b42b8` 3칸, 표 `c54b2` 27칸); 분류 `JUMPTGT11` 추가; `native_safe` 기본 유지)): 작업자 300건 seed 1 `mismatches 0`(`covered starts 179 of 192`; 문서화된 분류: FR11 jump-target 4건(무작위 LONG 76의 `b4034` 2, 무작위 D0의 `b42b4`·`c54ae` 각 1), 계산 점프가 다른 실행부 내부에 떨어짐 1건(FR1 `b3dbc`의 표 `b3dcc`에 무작위 WORD 7e); 깨끗이 멈추지 않은 native 67건 건너뜀; native oracle abort 0, `trial_logs/real_n300_s1.log`). 앞선 30건 seed 11 시험도 `mismatches 0`(`trial_logs/real_t30.log`).
- [F] **IO, 입력 확장 관측**(FR11 연결 뒤, `--workers 3`): run 12, native 비교 frame 14,500 가운데 일치 **7,383**(예측 7,383, 기준선 6,751 → +632), 불일치 0(beyond 0), C++ 오류 0, chain divergence 0, 수용 키 모두 true(`negatives_ok` 포함)(`trial_logs/io_ext_fr11.log`; `verification.json` SHA256 `b49e28d3cb814db7…`, `frontier.json` `acc8116dcf0a2f33…`, scratch `io_ext_fr11/`). 첫 정지 frame: X1 68 745, X1 94 488, X2 68 713, X2 94 493, X3 68 714, X3 94 518, X4 68 736, X4 94 576 — 재관측 예측(`reobs/fr11v1.stops`)과 run·frame이 모두 같다. 확인된 frontier PC는 `b6e5e` 3 run, `c1036` 2 run, `cc7c0` 2 run, `70f8e` 1 run으로 모두 FR12(D-3)다(재관측이 같은 frame에 적은 `b4304`..`c105e` 가운데 IO가 실행 순서로 `c1036`을 확정; [I] 같은 frame 안의 순서).
- [F] 원래 IO 관측·frame 비교·legacy 검증기는 작업자가 돌리지 않았다(메인 runner).
- [F] `CPP_PINS`: 작업 트리와 scratch clone root(`work/mkroot.py`; 확인 뒤 symlink를 먼저 지우고 삭제)에서 파일 SHA와 같다(4 / 9 pin, 불일치 0, `trial_logs/pincheck_tree.log` `pincheck_root.log`).

## 메인 결정(2026-10-24)

- 실행되는 표 칸 `b42c4`(표 `b42b8`)는 FR12, `c54ba` `c54d6`(표 `c54b2`)는 FR13에 둔다(계획 배정 유지). 그때까지 FR11에서는 뒤 단위 정지다.
