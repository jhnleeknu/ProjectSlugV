# frontier 단위 FR10(입력 확장 관측의 영역 D 첫 단위: 객체 상태 `70e2a` → `70f3e`..`7102e`·`713d8`/`71468` → `7143a`/`714ca`·`b6ba0` → `b6c72`, helper `70594` `b7a62` `b7b30` `4e122` `ccade`, FR4 표 칸 `cc7c4` `cc7d0` `cc846`, script callback `6f1ca` `cca44` `cca52`, 상태 `ccaf8`·`cd7c6`..`cd8ee`·`cd94e` → `cda34` → `cdafc`, 28ae 자식 `cdd86` → `cde6e`·`eaac0` → `eab2a`, `eaa00` → `eaa20`, 211 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §10.5 표의 FR10 행(계획 이름 D-1)과 §10.x 메인 결정을 기준으로 삼고, 구조·공통 규칙은 FR9 계약(`animation-machine-frontier-fr9-contract.md`)과 C9 계약(`animation-machine-player-c9-contract.md`, 입력 확장 관측 방법·V1 natural family·IO 검증기 pin 표)을 따르며 다른 점만 적는다. 단위 이름은 FR10, 파일 접두어는 `objects_fr10`(C++) / `fr10`(V1 spec)다. 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다. BIOS 실행, 자연 scheduler, IRQ timing은 주장하지 않는다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 LONG(`2000d0` `2000d4` `2001a8` `2001ac` `200094`)을 live bus로 읽는다(아래). 장치 쓰기는 없다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 C9 커밋 `92039e5`(branch `claude/fr10-core`; C1~C9, E1, D routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `48ba3f29953b656d51b1cebe03f18c3004fa0fb011070b0ea8527d5e94b617c3`, `animation_machine_internal.h` `d8918d505ee9dde426c93f8b26ec19f8d4893f59867cce33a6017947e20a3058`(C9 계약의 새 값과 같음).
- [F] 관측 입력(읽기 전용): 입력 확장 IO 관측 `artifacts/animation_machine_io_ext`(`observation.json` SHA256 `9da40ac6dcbea3eb…`, compared_sha256 `b5d15d4fcd53555b…`, 검증기 pin 이름 `io-ext`). V1 natural family가 이 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)으로 읽는다(C9 결정 6과 같은 방식).
- [F] 이 단위의 정확 bitmap 재관측 두 벌(scratch, 관측기 수정 없음): `reobs/c9base`(C9 routing 그대로), `reobs/fr10v1`(FR10 29 범위를 `--extra-routed`로 가상 routing). 결정 1.
- [F] 시작 목록: **`ms5-scratch/fr10/starts_fr10_final.txt`(211개, SHA256 `69c69c92eab8383f52a13d4855fcc14f9bb1e53bfbbd24bad10e58211f200d18`)**. 계획 목록 `ms5-scratch/obs2/starts_FR10.txt`(214개, SHA256 `9b7c558e0a7fe4c9…`)에서 `252b4` `252ce` `252d8` `252e2`를 빼고 `cd804`를 더했다(결정 1). 실행부의 `case` label 211개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(작업자 확인: 실행부 case 집합 = 시작 목록, `make test`의 FR10 시험이 시작 211개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr10/`
  - `reobs/run.sh`(재관측 + `dleft.py` + `runstops.py`), `reobs/c9base` `reobs/fr10v1`(+ `.dleft` `.stops` `.log`), `plan/udetail_FR10.txt` `plan/D-1.dis.txt`(계획 `xplan_v2.json`의 D-1 상세·역어셈블; `tools/xdetail.py`), `work/fr10ranges_v1.txt`(29 범위), `work/blocks_v2.txt`(block별 역어셈블).
  - `tools/newvis_fr10.py` → `work/newvis_fr10v1.txt`(새로 보인 PC), `work/intargets.py` → `work/intargets_fr10.out`(범위 안 비시작 PC로 오는 직접 분기), `tools/refs_fr10.py` → `work/refs_fr10.out`(ROM 전체 FR10 시작 참조), `tools/flagscan.py` → `work/flagscan_fr10.txt`(block 경계를 넘는 flag), `tools/exitflags.py`(출구·진입으로 넘어가는 flag), `tools/fr10io.py` → `work/fr10io_ext.txt`(IO 실행 run·frame), `tools/natscan_fr10.py` → `work/natscan_fr10.out`(확장 관측 pack의 FR10 callback node), `tools/fr10refs_repo.py` → `work/fr10refs_repo.out`(저장소의 FR10 범위 literal), `work/v1_regs.sh`, `work/pincheck.py`, `work/mkroot.py`, `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위(결정 1)

- [F] **기준선**(C9 routing, 입력 확장 관측): 예측 일치 frame **5,839**, 첫 정지 D 6 run(`6f1ca` 2, `eaac0` 2, `252b4` 1, `71468` 1)·C 2 run(`223fa`). C9 계약의 IO 실측과 같다.
- [F] **정확 bitmap 재관측(C9 routing)** `reobs/c9base`: run 12개의 기록·state pack SHA256이 C9의 재관측 `ms5-scratch/c9/reobs/c9r`와 모두 같다. `dleft.py`: 실행된 routing 밖 PC C 102 / D 659 / E 108, 예측 5,839.
- [F] **범위 보정 1 — C7 표 칸 `252b4` → `252ce`를 뺌(메인 결정 4)**: 계획 FR10의 `252b4..252b8`(1 block)과 `252ce..252e6`(3 block: `252ce` `252d8` `252e2`) 모두를 뺀다. 이 네 block은 C7 표 `2529c`(`25298 JMP 2529c(PC,D0.W)`)의 칸 `252a8`/`252b4`(`BRA.W 252ce`)에서만 들어오는 C7 쪽 코드다: `252ce BTST #7,61(A2); BNE 252e2` / `252d8 MOVE.W #189d,D0; JSR 3af8` / `252e2 BRA.W 253c8`. ROM 전체 직접 참조 검색(`refs_fr10.py`)에서 `252d8` `252e2`는 `252ce`의 갈래 말고는 들어오는 곳이 없다. 메인 결정의 "2 block"은 두 범위를 뜻한 것으로 보고 [I] 네 block을 모두 C10에 넘긴다. **C10은 `252b4` `252ce` `252d8` `252e2`를 시작으로 가져야 한다.**
- [F] **범위 보정 2 — `cd804`를 block 시작으로 더함**: `cd7c2 BRA.W cd804`는 `cd782 RTS` 뒤의 형제 routine(`cd784 JSR 49a58` …)이고 FR10 범위 `cd7e4..cd92e` 안의 비시작 PC `cd804`(`JSR 49a58`)로 들어온다(`intargets_fr10.out`). FR9 계약의 block 시작 규칙("범위 밖에서 들어오는 실제 분기 대상")대로 `cd804`를 시작으로 둔다. `cd784`는 이번 관측에서 실행되지 않고 어느 IO 단위에도 없다(뒤에 이 형제를 routing하는 단위가 FR10을 다시 고치지 않게 하려는 것). `intargets`의 나머지 넷은 operand를 명령으로 읽은 것이다: `b6b7a bmi.b`·`b6b9a bvs.b`(`b6b76 MOVE.L #b6b7c,(A6)`·`b6b96 MOVE.L #b690a,(A6)`의 immediate), `b6c8e bge.b`·`b6c9c blt.b`(FR10 `b6c8a`·`b6c98`의 immediate).
- [F] **정확 bitmap 재관측(FR10 가상 routing, 보정 뒤 29 범위)** `reobs/fr10v1`: 예측 일치 frame **6,230**, 첫 정지 C 7 run(`1dccc` 4, `22148` 1, `223fa` 2)·"D" 1 run(X3 68 frame 591 `252b4`; 주소 규칙으로 D지만 메인 결정 4로 C10). 모두 뒤 단위다.
  - [F] **숨은 직선 연속 검사**: `c9base`에 없고 `fr10v1`에만 보이는 routing 밖 PC는 **없다**(`newvis_fr10v1.txt`: 12 run 모두 0). 실행되는 FR10 범위 끝 PC는 `70e42` `70f60` `70f8e` `70fac` `70fcc` `70ff8` `71028` `b6c58` `b6ca2` `cca5a` `ccbc0` `cd7e2` `cd92e` `cd96c`이고 모두 기준 관측에서 이미 보였다(뒤 단위 시작이거나 RTS 뒤). 반복은 한 번으로 수렴했다.
  - [F] 계획 예측 6,267과의 차 −37은 결정 4 하나로 설명된다: 계획에서 X3 68의 첫 정지는 frame 628(`b6ca2`)이었고, `252b4`가 C10으로 가면 frame 591(`252b4`)이 된다(628 − 591 = 37). 다른 run은 계획과 같다.
- [F] **IO 실행**(`c9base`, `work/fr10io_ext.txt`): FR10 PC 146개(모두 시작), 실행 43,763회(TB 첫 routing 밖 PC로 기록된 수; 계획의 43,952는 재관측 병합 기준이며 `252b4` 계열 3 시작이 들어 있었음), run 8개(X1~X4 × case 68·94). 처음 frame: X1 68 501, X1 94 295, X2 68 504, X2 94 291, X3 68 591, X3 94 377, X4 68 597, X4 94 437. 실행되지 않은 시작 65개는 closure로 들어왔다(`cd804`는 `cd7f2`와 같은 TB 안이라 따로 기록되지 않을 뿐 `cd7f2`가 실행될 때마다 실행된다).

## FR10 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **211 block, 510 명령, 2,286 byte, 29 범위**(시작 목록 SHA256 `69c69c92…`, 범위 이어 붙인 SHA256 `c8a725fa0d4930482af8acab9ec0ea34bf93598a735c1ee06750dff784a21ecd`). 짝수 PC 1,143(내부 932). 기존 routing과 겹침 0(각 범위 안 짝수 PC 전수 검사).

| 범위(CPU = 파일 오프셋) | byte | 시작 | SHA256(앞 16자) | 내용 [I] |
| --- | --- | --- | --- | --- |
| `4e122..4e132` | 16 | 1 | `8ec2190a79b952ce` | 세는 helper: WORD `5d26(A5)` + 2 × (D0 & 1) += 1 |
| `6f1ca..6f1d4` | 10 | 1 | `19de1f232fabd630` | script callback(interpreter 표 `4a500` + 48): `TST.W 3a; SPL.B 80` |
| `70594..705ca` | 54 | 5 | `86f80290506e9012` | C helper: WORD `80` bit 0, BYTE `82` bit 5, `SMI`/`SEQ`/`EOR.B` → ORI Set / ANDI Clear |
| `70e2a..70e42` | 24 | 1 | `c33034a05918e8c8` | 객체 상태(FR2b `70cba` 설치 값): 방향 시험 |
| `70ea2..70f60` | 190 | 11 | `0b65c1813da4580b` | bank anim, `ASR.L #5`, RNG, `NEG`/`LSL`/`SWAP`, 설치 `70f3e` |
| `70f84..70f8e` | 10 | 2 | `318a4759aa8671a8` | `JSR 49fc6; BCC` |
| `70f94..70fac` | 24 | 1 | `7a13412c816e5f65` | 방향 시험 |
| `70fc2..70fcc` | 10 | 1 | `c461f0a2045f8e4c` | `BTST #7,82` |
| `70fd2..70ff8` | 38 | 10 | `3e9409889707d36e` | `7028e` C, `70302`, LONG 표 `70d72`, `CMPA.W #0`/`BEQ` |
| `70ffa..71028` | 46 | 8 | `868c500d1ae3c4e9` | `705ca` C, `70594` C, 쓰기만 하는 설치 |
| `7102e..71032` | 4 | 1 | `81b13a93cdeaa272` | `BRA.W 72dd2` |
| `713d8..71502` | 298 | 23 | `4d0fbd6cfeb71570` | 객체 상태 `713d8`/`71468`(bank anim) → `7143a`/`714ca`(`ASR.L #3`/`#2` 감속, `49fc6`) |
| `b6ba0..b6c58` | 184 | 7 | `70ea8c4e1ba7d851` | U18 설치 값 `b6ba0`: `b7a62`, ROM LONG 표 `b7f6c` + bank 표 anim, `CMPI.W #c0` BLE |
| `b6c66..b6ca2` | 60 | 7 | `07f436405b4c9ec4` | 설치 `b6c72`: `b7cfa`, `49fc6`, WORD `84` 세기, BGT |
| `b7a62..b7acc` | 106 | 16 | `e0c8a651d5e743e4` | helper: `484e2` C, `MOVEM.W D0-D1` + `49392` C, `4e122`, A5 세는 값 |
| `b7b30..b7b4c` | 28 | 4 | `5daa50a14814dbee` | U19 callee: BYTE `61(A0)` bit 7, `4941e` C의 `EORI.B #1,CCR` |
| `cc7c4..cc7c8` | 4 | 1 | `e69d5047ebb8a8c7` | FR4 표 `cc7ac`의 칸 6: `BRA.W cd94e` |
| `cc7d0..cc7d4` | 4 | 1 | `6b03d48b96d92b00` | FR4 표 `cc7ac`의 칸 9: `BRA.W cd7c6` |
| `cc846..cc84a` | 4 | 1 | `ba903ef559234599` | FR4 표 `cc82e`의 칸 6: `BRA.W ccaf8` |
| `cca44..cca5a` | 22 | 3 | `7b0e82f886b11396` | script callback(표 `4a500` + 234 / 238): `MOVE.W (A0),D0; JSR 49a84` / `BSET #4,15` |
| `ccade..ccbc0` | 226 | 21 | `00df0cb22e402d46` | C helper `ccade`(TST.B Clear, `4b54e`), 상태 `ccaf8`(WORD `8c` 0..4 anim 선택) |
| `cd7c6..cd7e2` | 28 | 2 | `f415f903a0081290` | 상태 `cd7c6`: RNG, `LSL.L #2`, `SUBI.L` |
| `cd7e4..cd92e` | 330 | 29 | `bd53f5dee48cfe2d` | RNG 세 번(`cd804`의 N), anim 선택, 설치 `cd8ee`, `CMPI.W #20` BPL |
| `cd93c..cd96c` | 48 | 7 | `42a833021a096c95` | `ccade` C, 상태 `cd94e`(`cdd86`, `SNE`/`EOR.B`) |
| `cda34..cdb08` | 212 | 20 | `fd8478b8bc16dfb3` | anim 선택, 설치 `cdafc`, `cc778` |
| `cdd86..cddba` | 52 | 5 | `a647938750b743d9` | 28ae 자식 `cde6e` 만들기, `4970a`, ORI Set |
| `cde6e..cde96` | 40 | 1 | `5f442ce4c0f4a9dc` | 28ae 자식 callback: bank anim `e2`(창 `200094`) |
| `eaa00..eaa54` | 84 | 10 | `831b0739f340bf8f` | U18 설치 값 `eaa00`: ROM 표 `ea732` anim, 설치 `eaa20`(`43e34`, `BCLR #7,5e50(A5)`, `49fc6`) |
| `eaac0..eab42` | 130 | 11 | `42b85819d931338b` | 28ae 자식 `eaac0`(C9 `20cd8` `20d44`, FR3 `ea6d4`): `1abda` C, `8ebe`, ROM 표 `eaa5c` anim, 설치 `eab2a` |

- [F] **진입**(현재 routing 기준 호출자, `refs_fr10.out`; 다음 명령 포함):
  - 설치 값: `70e2a` ← FR2b `70cba`; `71468` ← FR2b `70cee`, N15 `71136`(그리고 routing 밖 `70fbc` `70fcc`); `713d8` ← N15 `71126` `71148`(routing 밖 `717aa BCS`); `b6ba0` ← U18 `b76c8`; `eaa00` ← U18 `ea9e4`.
  - 28ae 자식: `eaac0` ← C9 `20cd8` `20d44`, FR3 `ea6d4`(그리고 routing 밖 `373c2 JMP`); `cde6e` ← FR10 `cdd86`.
  - callee: `70594` ← N15 `711b6`(`BSR`, 돌아와 `711c0`이 C를 읽음), FR10 `71012`; `b7b30` ← U19 `b7b68` `b7b7c`(`BSR.B`, 돌아와 `b7b6a`/`b7b7e`가 C를 읽음); `b7a62` ← FR10 `b6ba4`(routing 밖 `b8866`); `4e122` ← FR10 `b7a80`; `ccade` ← FR10 `cd93c` `cdafc`; `cdd86` ← FR10 `cd956`(routing 밖 `860c2 JSR`).
  - 계산 점프 착지(아래 "계산 점프와 표"): `cc7c4` `cc7d0` ← FR4 `cc7a8`, `cc846` ← FR4 `cc82a`; `6f1ca` `cca44` `cca52` ← interpreter `JSR (A1)`(표 `4a500`).
  - 범위 밖 routing 밖에서 들어오는 곳(뒤 단위가 routing할 때 그 단위의 출구가 됨): `70e9e BRA.W 70efe`, `70f7a BRA.W 70f84`, `70fb8 BCS.W 70fc2`, `cc7c0`/`cc842 BRA.W cd7c6`, `cc950 MOVE.L #cd7c6,(A6)`, `cda2c MOVE.L #cdafc,(A6)`, `eaabc BRA.W eaafe`, `cd7c2 BRA.W cd804`, `6f156 BCS.B 6f1ca`.
- [F] **설치 값**(`MOVE.L #v,(A6)`): 곧바로 들어감 `70f3e`(`70f38`) `7143a`(`71434`) `714ca`(`714c4`) `b6c72`(`b6c6c`) `eaa20`(`eaa1a`) `eab2a`(`eab24`). 쓰고 RTS(다음 frame callback): `cd8ee`(`cd8e6`) `cdafc`(`cdaf4`). **쓰기만**: `72978`(`70fda`) `71dd6`(`71002`) `712a0`(`7101a`, routing 밖·실행 안 됨) `70c0c`(`7145e`) `71032`(`714f8`) `b6ca2`(`b6c8a`, FR11) `b6d82`(`b6c98`) `cdd2e`(`ccbb8`) `cdc24`(`cd944`) `ea824`(`eaa3e`) `ea85a`(`eaa4c`). 그 밖에 `cd922 MOVE.L #cc5c4,56(A6)`(LONG 쓰기). `70ff8 MOVE.L A0,(A6)`(표 `70d72`의 값)은 FR13의 block이다.
- [F] **28ae 자식**(`MOVEA.L #v,A0` 뒤 `JSR 28ae`): `cde6e`(`cdd8c`, D0.W = `1e`). FR10은 자식 `eaac0`의 몸통이기도 하다(위). `2986` 경유 자식은 없다.

### 계산 점프와 표(결정 2)

- [F] **FR10 안에는 계산 점프가 없다**(`JMP (An)`·`JSR (An)`·`JMP d(PC,Dn)`·TRAP 0). 직접 분기·호출과 `JSR d(PC)`(`71012` `cd93c` `cd956` `cdafc`)뿐이다.
- [F] **FR10이 받는 계산 착지**(기존 실행부의 규칙 그대로, FR10은 그 칸을 routing할 뿐이다):
  - FR4 `cc7a8 JMP cc7ac(PC,D0.W)` / `cc82a JMP cc82e(PC,D0.W)`(27칸 `BRA.W` 표, ROM 파일 오프셋 = CPU 주소 `cc7ac..cc818` / `cc82e..cc89a`): FR4 계약 결정 2대로 PC := 표 + 4 × (D0 & ff)이고 routing이 판정한다. FR10 뒤 칸 `cc7c4`(→ `cd94e`) `cc7d0`(→ `cd7c6`) `cc846`(→ `ccaf8`)이 FR10 시작이다. 앞 block의 `CMPI.B #1b,D0; BCC`가 정상 경로의 색인을 0..1a로 묶는다. 직접 진입의 색인 ≥ 1b는 표 뒤로 떨어지고, FR10 내부 PC(예: FR4 시험의 `ff` → `ccba8`, FR10 block `ccba2` 안)면 `unsupported animation objects fr10 PC`(checked)다.
  - interpreter `4a352`/`4a43c JSR (A1)`(script 표 `4a500`의 LONG, ROM 파일 오프셋 `4a548` = `6f1ca`, `4a734` = `cca44`, `4a738` = `cca52`): interpreter 계약대로 "live table target; routing decides"다. ROM 자료(script)가 만드는 목표만 실제로 오고, 그 밖의 A1은 routing 판정(routing 밖이면 `unsupported animation machine PC`, FR10 내부면 FR10의 checked PC 오류)이다.
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙. [F] 원본 값은 ROM 바이트):
  - LONG 표 `70d72`(`70fec`; 첨자 = `70302`가 돌려준 D0.W × 4, `ADD.W` 둘이라 WORD 안에서 넘침, 부호 확장): 원본 8 LONG `0 71502 71562 715c2 71622 716ca 716ca 716ca`. 값은 `70ff4`가 0과 비교만 하고, 0이 아니면 FR13 `70ff8`이 callback으로 쓴다(FR13의 계산 설치; FR13 계약에서 다룬다).
  - LONG 표 `b7f6c`(`b6bb8` D0.W = 0, `b6bf4` D0.W = WORD `8e`): 그 LONG의 WORD × 4가 bank 창 LONG 표(`2001a8`/`2001ac`가 가리킴)의 첨자다. 원본 16 LONG `f 1 f 2 10 d 17 f 18 10 18 11 19 11 1a f`.
  - LONG 표 `ea732`(`eaa00`)·`eaa5c`(`eaada`): 첨자 = WORD `76` × 4. 원본 `ea732` = `eac64 eac8e ead0a eadae …`, `eaa5c` = `eafb2 eb040 eaea2 eb13e …`.
  - bank 창 LONG `2000d0`/`2000d4`(`70eaa` `70ed6` `713e0` `7140c` `71470` `7149c`, LONG `11c`/`194`/`8`/`18`), `2001a8`/`2001ac`(`b6bb8`/`b6bf4`), `200094`(`cde6e`, LONG `3c`): FR4 `ofr4_bank_anim`과 같은 꼴(창 LONG → LONG 22(A6) → 그 LONG + d의 LONG이 A1).
  - 이 표·창 값은 모두 anim 자료 포인터(A1, `49f8c`로 넘김)이거나 첨자다. 코드 주소로 점프하지 않는다.

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `28ae` `2a00` `8ebe` `1abda` `43e34` `484e2` `492d0` `49392` `4941e` `4970a` `49a58` `49a84` `49f8c` `49fc6` `4b54e` `4bfa4` `7028e` `70302` `705ca` `71c48`(N15) `71c90`(N04) `72dd2` `b76d2` `b7cfa` `cc778` `cdd2e`, 그리고 돌아오는 곳 `cde96`(`cde6e`의 `JSR 49f8c` 복귀).
- [F] **뒤 단위 정지**(실행되지만 뒤 단위가 가짐; V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS`의 앞 11개): FR11 `70e42`(`70e3e BPL`의 fall-through) `70fac`(`70fa8`) `cd7e2`(`cd7de BPL`) `cd92e`(`cd8f4 BNE`) `cd96c`(`cd968 BPL`), FR12 `70f8e`(`70f8a BCC`의 Set 쪽) `b6c58`(`b6c42 BLE`), FR13 `70f60`(`70f5c BCS`의 fall-through) `70fcc`(`70fc8 BEQ`) `70ff8`(`70ff4 BEQ`) `71028`(`71024 BNE`).
  - FR10 run이 지나갈 수 있는 C1~C9의 남은 정지(pc9 `EXIT_STOPS` 21개, 모두 아직 routing 밖)도 fr10 `EXIT_STOPS`(모두 32개)에 넣었다.
- [F] 직선 fall-through로 범위를 벗어나는 곳은 위 뒤 단위 정지뿐이다. 재관측에서 새로 보인 PC가 없어 가려진 연속은 없다(결정 1).
- [F] TRAP 없음. ROM·RAM 실행 없음. 장치 쓰기 없음(`MOVE`·`ADDQ`·`BSET` 등의 대상은 node·A5 work RAM·스택).

### block 경계·복귀를 넘는 flag(결정 3)

C9 방식대로 block 첫 명령부터 flag를 정하는 명령까지 훑었다(`flagscan_fr10.txt`). 그리고 FR10 진입·출구 대상에서 앞 코드의 flag를 읽는 곳을 따로 훑었다(`tools/exitflags.py`: 양쪽 분기를 따라 40 명령까지). X를 읽는 명령은 없다.

- [F] **C 소비 block 13개**(Clear 쪽 / Set 쪽; Unknown C면 `objects fr10 caller requires known carry`):
  - `70f8a BCC 70f94`·`7145a BCC 71464`·`714ea BCC 714fe`·`eab36 BCC eab40`(`49fc6`), `70fd6 BCC 70fe0`(`7028e`), `70ffe BCC 71008`(`705ca`), `71016 BCC 71020`(FR10 `70594`), `b7a68 BCC b7a6e`(`484e2`), `b7a78 MOVEM.W (A7)+,D0-D1; BCC b7aca`(`49392`; MOVEM은 flag를 바꾸지 않음), `cd940 BCC cd94a`(FR10 `ccade`), `cdd9c BCC cddb2`(`28ae`), `eaa3a BCC eaa44`(`eaa26`의 ANDI Clear 또는 `49fc6`), `eaac6 BCS eaad0`(`1abda`).
  - 생산자 쪽 routing된 callee는 모두 기존 실행부가 known C를 돌려준다(각 RTS가 dispatcher carry 목록의 소비자에게 이미 C를 주는 곳; `animation_machine.cpp` 주석 확인).
- [F] **C를 뒤집는 block: `b7b40 EORI.B #1,CCR; RTS`**(`4941e`의 C를 U19 `b7b6a`/`b7b7e`로 돌려줌). Unknown이면 checked 오류(FR1c `49458`, N16 `792ac`와 같은 규칙).
- [F] **known C를 만드는 block**: `705be`(ORI Set; RTS) `705c4`(ANDI Clear; RTS) — N15 `711c0`과 FR10 `71016`이 읽음; `b7b46`(ANDI Clear; RTS) — U19가 읽음; `ccade`(TST.B → Clear) — `ccae6`·`ccaf6`을 지나 `cd940`이 읽음; `eaa26`(ANDI Clear) — `eaa3a`가 읽음; `cddae`(ORI Set) — `cddb2 BCHG; RTS`를 지나지만 읽는 곳이 없다(`cd956`의 복귀 `cd95a`는 C를 읽지 않음; FR9 `b0578`과 같은 처리).
- [F] **C를 넘기는 block**: `ccae6`(BTST + BNE; C 유지), `ccaf6`(RTS; `ccade`/`ccae6`의 Clear 또는 `4b54e`의 C를 `cd940`으로). `cdafc`의 `JSR ccade` 뒤 `cdb00`은 C를 읽지 않는다.
- [F] **실제 ROM 차분이 찾은 경계: `70f2c` → `70f3e` → N15 `71c48`**. N15 소비자 `71c48`(`BTST #1,82; BEQ; BCS 71a80`)은 BYTE `82` bit 1이 1이면 들어오는 C를 읽는다. FR10 `70f3e`(`BTST #7,15; BEQ 71c48`)는 C를 바꾸지 않고, 그 앞 `70f2c`의 마지막 C 정하는 명령은 `MOVE.L #70f3e,(A6)`(C = 0)이다. 그래서 **`70f2c`는 Clear를 남기고 `70f3e`는 C를 넘긴다**(carry 목록에 `70f3e`). `70f3e`가 node callback으로 들어올 때(다음 frame)의 C는 앞 객체 코드의 것이라 정할 수 없다([I] `2abe MOVEA.L (A6),A0; JSR (A0)` 사이에 flag 명령이 없음). C++에서는 Unknown이 들어오고 `71c48`이 bit 1에서 checked 오류를 낸다(N15 `710e4` callback 진입과 같은 처리). [F] 확장 관측 IO에서 이 오류는 나지 않았다(아래 검증 수치). 처음 구현에는 이 규칙이 없었고 실제 ROM 차분 seed 4(FOLLOW_ANIM) 1,500건에서 1건(`70f2a` 직접 진입 → `71c48`)이 `objects n15 caller requires known carry`로 어긋나 찾았다. 고친 뒤 0건이다.
- [F] **Z가 경계를 넘는 곳: `70ff4 BEQ.W 70ffa`**. Z는 `70ff0 CMPA.W #0,A0`의 것이다(계획의 block 시작이 명령마다 나뉘어 있어 `70ff0`/`70ff4`가 각각 block). `70ff4`로 오는 길은 `70ff0`의 fall-through 하나뿐이고 사이에 명령이 없다. **`70ff4`는 Z = (A0 = 0)(LONG 전체; `CMPA.W #0`은 0을 LONG으로 부호 확장해 비교)으로 다시 계산한다.** 출처가 레지스터라 메모리 접근이 없고 flag-source 오류가 생길 수 없다.
- [F] **N이 복귀를 넘는 곳: `cd80a BPL.W cd814`**. N은 `cd804 JSR 49a58`의 RNG 끝 `49a80 SUB.W D0,(A3); RTS`의 것이다(U12 `70198`과 같은 경계). **`cd80a`는 WORD (A3)를 다시 읽어 bit 15로 N을 정한다**(A3와 그 WORD는 RTS가 바꾸지 않음). 주소 24 bit가 work RAM / 고정 ROM(`< 200000`)이 아니면 다시 읽기가 장치 읽기가 될 수 있으므로 checked `unsupported animation objects fr10 flag source`다(C9 `22180`과 같은 규칙). 홀수 A3는 bus의 정렬 오류다.
- [F] 그 밖의 `Bcc`/`Scc`는 같은 block 안의 명령이 정한 flag를 읽는다(`705aa`·`cd95a`의 `EOR.B` 뒤 BMI/BPL, `70e2a`·`70f94`의 `EOR.W` 뒤 BPL, `70f12 TST.L`, `70f4e CMPI.W #3000`(무부호), `b6c2c CMPI.W #c0` BLE(부호), `b6c84 TST.W` BGT(부호), `b7aa8 CMPI.W #64` BCS(무부호), `cd8fe CMPI.W #20` BPL(N만), `cd916 TST.L`, `cd7cc TST.B 5f` BPL).

### IO 실행 run과 frame

- [F] 실행 run 8개(X1~X4 × case 68·94), 첫 frame은 위 "재확인과 범위". FR10 객체 node는 pool `100800..104c00`의 여러 node다(`natscan_fr10.out`).
- [F] **IO 예측(FR10 연결)**: 5,839 → **6,230**(+391; 재관측 `reobs/fr10v1`). 첫 정지는 C10 7 run(`1dccc` X1·X2, `22148` X3 94, `223fa` X4)과 C10 `252b4` 1 run(X3 68 frame 591). [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다.
- [F] 원래 IO 관측은 FR10 코드를 실행하지 않는다(계획 §10.4: X run에서만 실행). 일치 173,966은 그대로여야 한다(작업자는 돌리지 않음; 메인 runner).

## 공통 규칙·native 검증 계획

FR2..FR9, C1~C9 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr10.cpp`, 함수 `animation_objects_fr10_block`. 오류 문자열은 `unsupported animation objects fr10 PC`(범위 안 내부 PC 직접 진입·계산 착지), `objects fr10 caller requires known carry`(C 소비 block 13개와 `b7b40`에 Unknown C), `unsupported animation objects fr10 flag source`(`cd80a`의 N 출처) 세 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(29 범위, C9 줄 뒤; `)ok=animation_objects_fr10_block(c);`를 같은 줄에 둔다), `carry_preserving_pc`의 C9 묶음 뒤에 주석 달린 case 묶음 하나(소비자 13, `b7b40`, 통과 `ccae6` `ccaf6` `70f3e`), `animation_machine_internal.h`에 선언 하나(C9 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# objects FR10 refresh:` 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 위 명세의 곧바로 들어감 6개는 쓰고 그 값으로 들어가고, `cd8e0`(`cd8ee`)·`cdaf4`(`cdafc`)는 쓰고 RTS, 쓰기만 하는 11개는 쓰고 다음 block으로 간다.
- **자료 읽기**(live bus): node field(A6: BYTE `15` `5f` `61` `63` `76` `77` `78` `7b` `80` `82` `9d`, WORD `1e` `20` `2c` `3a` `42` `64` `68` `76` `7c` `80` `84` `8a` `8c` `8e` `9c`, LONG `0` `22` `36` `3a` `42` `56` `64` `7e` `8e` `96` `98`), A5 field(WORD `5d26`+2k, `5ddc`/`5de4`; BYTE `5de0` `5de3` `5de8` `5deb` `5e50`), A0 record(BYTE `61` — `b7b30`; WORD `(A0)` — `cca44`), A3의 WORD(`cd80a`), 스택(`b7a6e`/`b7a78`의 WORD 둘), 고정 ROM·bank 창(위 "계산 점프와 표"). 단위 시험은 고정 ROM·bank 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): LONG 표 `70d72`(8) `b7f5c..b7fac`(`b7f6c`의 16 LONG과 그 앞 4 LONG) `ea732`(4) `eaa5c`(4), bank 창 LONG `2000d0` → `2a1000`(+8 / 18 / 11c) `2000d4` → `2a2000`(+8 / 18 / 194) `2001a8` → `2a3000`(32 LONG) `2001ac` → `2a4000`(32 LONG) `200094` → `2a5000`(+3c). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `b7a6e MOVEM.W D0-D1,-(A7)`: D1.W를 A7 − 2, D0.W를 A7 − 4에 쓰고 A7 −= 4(68000 predecrement 순서). `b7a78 MOVEM.W (A7)+,D0-D1`: 낮은 주소부터 D0, D1에 WORD를 LONG으로 부호 확장해 넣고 A7 += 4, flag는 바꾸지 않는다. 홀수 A7은 checked 오류다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W`/`AND.W`/`SUB.W`/`ADD.W`/`ADDI.W`/`SUBI.W`/`ANDI.W`/`CMPI.W`/`EOR.W`/`EXT.W`/`LSL.W`, `MOVE.B`/`SMI`/`SEQ`/`SNE`/`SPL`/`EOR.B`, `ADDQ.W`/`ADDQ.B`/`SUBQ.W` 메모리). `MOVE.L`·`MOVEA.L`·`LEA`·`CLR.L`·`ADD.L`·`SUB.L`·`ANDI.L`·`ADDI.L`·`SUBI.L`·`NEG.L`·`LSL.L`·`ASR.L`·`EXT.L`·`SWAP`·`MOVEQ`는 LONG 전체(mod 2^32). `ASR.L #n`은 부호 채움(UB 없는 무부호 계산, FR9 `ofr9_asr`와 같은 꼴). 표 첨자 `ADD.W D0,D0` ×2는 WORD 안에서 넘치고 `(An,D0.W)`는 부호 확장. bit: `BTST/BSET/BCLR/BCHG #n,d(An)`(메모리 BYTE, bit mod 8).

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `48ba3f29953b656d51b1cebe03f18c3004fa0fb011070b0ea8527d5e94b617c3` → `6a7d76c3817fdab2a07af95b5d1be6cb14fca2c81f992bba558a88bddb14cdc6`, `animation_machine_internal.h` `d8918d505ee9dde426c93f8b26ec19f8d4893f59867cce33a6017947e20a3058` → `9f371fcfefb8bf19538c6b6e6e779a9e95ea9019c77816537a4b0ce01870425c`(옛 값은 `# objects FR10 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 작업 트리와 scratch clone root에서 확인했다(`work/pincheck.py`, `trial_logs/pincheck_tree.log` `pincheck_root.log`).
- [F] **V1 spec `tools/unit_fixture_specs/fr2b.py`**: `build()`의 "data / stop PC must stay unrouted" 목록 `(702fa, 70d72, 76922, 71884, 70e2a)` → `(702fa, 70d72, 76922, 71884)`. `70e2a`(FR2b `70cba`의 설치 값)가 FR10 시작이 되어 그대로면 spec이 시작 전에 멈춘다. FR3 때 `bc93c` → `70e2a`로 바꾼 것과 같은 이유이고, 남은 routing 밖 FR2b 설치 값은 `71884`뿐이다(FR2b 실행부의 설치·callback 값 25개 전수 확인). fixture 내용은 바뀌지 않는다.
- [F] **저장소 전수 검색**(`fr10refs_repo.out`, 5자리 16진 literal): 위 둘 말고 FR10 범위 PC를 쓰는 곳은 모두 바꿀 필요가 없다.
  - 정지 전용 행(그 PC에서 run을 멈추는 행; 정지 검사가 dispatch보다 먼저라 routing이 바뀌어도 같음): `objects_n15_test`(`70594` 12), `objects_u19_test`(`b6ba0` `b7b30`), `objects_u18_test`(`eaa00` 설치 값), `player_c9_test`(`eaac0`), `objects_fr3_test`(`eaac0`), `objects_fr4_test`(`TARGETS`의 `cc7c4` `cc7d0` `cc846`, 그리고 직접 진입 `cc7a0 ff`의 정지 `ccba8`).
  - 범위 끝 값(배타적 상한): `objects_fr3_test`·`fr3.py`(`70d92..70e2a`), `objects_fr4_test`·`fr4.py`(`cca76..ccade`), `objects_fr7_test`·`fr7.py`(`cc958..cca44` `cdd2e..cdd86` `cde42..cde6e`), `stage_area_test`(`b7a2e..b7a62`).
  - 생성기·관측기 주석·자료: `generate_..._fr2b_test_table.py`(`70e2a` 정지), `observe_animation_machine_objects_g2.py` `observe_/verify_animation_machine_stage_area.py`(관측 시점의 기록·주석; 결과 비교용 pin이며 routing을 묻지 않음).
  - 공용 spec 상수(모든 spec의 정수 tuple·dict를 읽어 FR10 범위와 교차 검사): 겹침 0.
- [F] `make -j3 all test`: 기존 C++ 시험이 모두 바뀌지 않고 통과한다(아래 "검증 수치"). FR4 시험의 `cc7a0 ff -> ccba8`은 정지 전용이라 그대로 맞는다. 다만 그 착지를 정지 없이 실행하면 이제 FR10 내부 PC 오류다(FR4 결정 2: 착지는 routing이 판정).
- [I] 원래 IO 관측과 frame 비교(d1·controller·irq·demo)는 FR10 코드를 실행하지 않으므로 결과가 같아야 한다. 메인 runner가 확인한다.

## 결정

1. **범위: 211 block, 29 범위.** 계획 214에서 C7 표 칸 `252b4` → `252ce`와 그 갈래 `252d8` `252e2`(4 block, 메인 결정 4)를 C10으로 빼고, 형제 routine `cd7c2`의 실제 분기 대상 `cd804`를 시작으로 더했다. 숨은 직선 block은 없다(가상 routing 재관측에서 새로 보인 PC 0). 예측 6,230 = 계획 6,267 − 37(결정 4의 효과).
2. **계산 점프: FR10 안에는 없다.** FR10이 받는 착지(FR4 `cc7a8`/`cc82a` 표 칸, interpreter `JSR (A1)`의 script 표 `4a500`)는 각 실행부의 기존 규칙(routing 판정)을 그대로 둔다. ROM 자료 표 `70d72` `b7f6c` `ea732` `eaa5c`와 bank 창 LONG은 live bus로 읽고 상한 검사를 하지 않는다(값은 자료 포인터·첨자).
3. **flag.** C 소비자 13개와 `b7b40`(뒤집기)은 known C를 읽거나 checked 오류. 생산: `705be`/`cddae` Set, `705c4`/`b7b46`/`ccade`/`eaa26`/`70f2c` Clear. 통과: `ccae6` `ccaf6` `70f3e`. `70ff4`는 Z를 A0에서, `cd80a`는 N을 WORD (A3)에서 다시 계산하고, 후자의 주소가 work RAM / 고정 ROM이 아니면 checked flag-source 오류.
4. **정수 연산.** `ASR.L`은 부호 채움, `MOVEM.W`는 부호 확장, `CMPI.W #3000`·`#64`는 무부호, `#c0`(BLE)·`TST.W 7c`(BGT)는 부호, `CMPI.W #20` + BPL은 N만.
5. **V1 natural family.** 확장 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)이 읽는다. pool `100800..104c00`의 node가 FR10 node 진입(설치 값·callback·28ae 자식 15개)을 callback LONG으로 가진 frame 163개(`natscan_fr10.out`에서 run·callback마다 처음 frame과 가운데 frame)를 쓴다.
6. **뒤 단위 정지와 앞 단위 spec.** FR10 block이 닿는 FR11~FR13 PC 11곳과 C1~C9의 남은 정지 21곳을 V1 `first_unrouted`와 실제 ROM 차분의 선언 정지로 둔다. 앞 단위 spec 가운데 바뀌는 것은 `fr2b.py`의 확인 목록 하나다.
7. **다음.** FR10 연결로 확장 관측 IO 6,230(+391)을 메인 runner가 확인한다. 다음 단위 C10은 `252b4` `252ce` `252d8` `252e2`를 시작으로 가져야 하고, C7 `25298`의 허용 칸 처리(C10 계획)도 그때 바꾼다.

## 미확인

- [U] node field·전역 값의 의미(BYTE `15` `5f` `61` `76` `78` `7b` `80` `82` `9d`, WORD `2c` `3a` `42` `64` `7c` `84` `8a` `8c` `8e` `9c`, LONG `36` `3a` `56` `64` `7e` `8e` `96` `98`, A5 `5d26` `5ddc..5deb` `5e50`, 표 `70d72` `b7f6c` `ea732` `eaa5c`). 이름(객체 상태, 방향 시험, 감속, anim 선택, 세는 helper)은 동작에서 붙인 [I]이다. 어떤 적·stage 객체인지는 정하지 않았다.
- [U] `70f3e`가 node callback으로 들어올 때의 C(앞 객체 코드가 남긴 C)와, 그때 N15 `71c48`이 BYTE `82` bit 1에서 그 C를 읽는 경우. C++은 checked 오류다. 이번 확장 관측 IO에서는 나오지 않았다.
- [U] IO 관측에서 실행되지 않은 이 단위의 block 65개(예: `70594` 계열, `ccb00`.. anim 선택의 일부, `cdda0`·`cddae`, `eaaca`)는 V1 선언 상태·natural·실제 ROM 차분·단위 시험으로만 확인했다.
- [U] 생산자 사슬 가운데 한쪽 결과만 나온 것(`7028e`·`705ca`·`4b54e`·`49fc6`의 Set 쪽 등)은 선언 C 행과 실제 ROM 차분으로 확인했다(아래 V1 보고의 빠진 후속).
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC).
- [U] natural fixture의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C9와 같음).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr10.cpp`(case label 211 = `starts_fr10_final.txt`와 집합 일치; 공용 함수 `ofr10_get` `ofr10_put` `ofr10_bit` `ofr10_btst` `ofr10_change` `ofr10_test` `ofr10_carry` `ofr10_install` `ofr10_asr` `ofr10_bank_anim` `ofr10_table_anim` `ofr10_anim` `ofr10_kind` `ofr10_select` `ofr10_facing` `ofr10_random_negative` `ofr10_count_byte`), `engine/tests/animation_machine_objects_fr10_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_d`), `tools/generate_animation_machine_objects_fr10_test_table.py`(생성기; C9 생성기 꼴, single 5 = 플래그 읽는 `70ff4`(native SR Z = (A0 = 0))·`cd80a`(native SR N = WORD (A3) bit 15), `b7b40`의 선언 행은 복귀 LONG을 U19 소비자 `b7b6a`로 둠, V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 100초), `tools/unit_fixture_specs/fr10.py`(V1 spec; pc9 spec의 공용 부분 그대로, 단위 부분 교체, `EXIT_STOPS`(32), `CONSUMERS`(14), `Z_READERS`(`70ff4` `cd80a`), natural family는 확장 관측 pack의 pool node; `2986` 안의 `290e` 실패만 버리고 `cdd86`의 직접 `28ae` 실패(Clear)는 둠). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `starts_fr10_final.txt`(SHA256 `69c69c92…`).

- **`4e122..4e132`(1)**: `4e122`
- **`6f1ca..6f1d4`(1)**: `6f1ca`
- **`70594..705ca`(5)**: `70594 705a0 705aa 705be 705c4`
- **`70e2a..70e42`(1)**: `70e2a`
- **`70ea2..70f60`(11)**: `70ea2 70eaa 70ed2 70ed6 70efe 70f12 70f2a 70f2c 70f3e 70f48 70f4e`
- **`70f84..70f8e`(2)**: `70f84 70f8a`
- **`70f94..70fac`(1)**: `70f94`
- **`70fc2..70fcc`(1)**: `70fc2`
- **`70fd2..70ff8`(10)**: `70fd2 70fd6 70fda 70fe0 70fe4 70fe8 70fea 70fec 70ff0 70ff4`
- **`70ffa..71028`(8)**: `70ffa 70ffe 71002 71008 71012 71016 7101a 71020`
- **`7102e..71032`(1)**: `7102e`
- **`713d8..71502`(23)**: `713d8 713e0 71408 7140c 71434 7143a 7144e 71454 7145a 7145e 71464 71468 71470 71498 7149c 714c4 714ca 714d4 714e4 714ea 714ee 714f8 714fe`
- **`b6ba0..b6c58`(7)**: `b6ba0 b6ba8 b6bb8 b6bf0 b6bf4 b6c2c b6c46`
- **`b6c66..b6ca2`(7)**: `b6c66 b6c72 b6c76 b6c7c b6c84 b6c98 b6c9e`
- **`b7a62..b7acc`(16)**: `b7a62 b7a68 b7a6c b7a6e b7a78 b7a80 b7a86 b7a8c b7a9c b7aa8 b7ab2 b7ab6 b7ac0 b7ac2 b7ac8 b7aca`
- **`b7b30..b7b4c`(4)**: `b7b30 b7b3a b7b40 b7b46`
- **`cc7c4..cc7c8`(1)**: `cc7c4`
- **`cc7d0..cc7d4`(1)**: `cc7d0`
- **`cc846..cc84a`(1)**: `cc846`
- **`cca44..cca5a`(3)**: `cca44 cca4c cca52`
- **`ccade..ccbc0`(21)**: `ccade ccae6 ccaf0 ccaf6 ccaf8 ccb00 ccb16 ccb1a ccb22 ccb38 ccb3c ccb44 ccb5a ccb5e ccb66 ccb7c ccb80 ccb88 ccb9e ccba2 ccbb8`
- **`cd7c6..cd7e2`(2)**: `cd7c6 cd7cc`
- **`cd7e4..cd92e`(29)**: `cd7e4 cd7f2 cd804 cd80a cd80e cd814 cd828 cd83e cd842 cd84a cd860 cd864 cd86c cd882 cd886 cd88e cd8a4 cd8a8 cd8b0 cd8c6 cd8ca cd8e0 cd8ee cd8f8 cd8fe cd912 cd916 cd922 cd92a`
- **`cd93c..cd96c`(7)**: `cd93c cd940 cd944 cd94a cd94e cd956 cd95a`
- **`cda34..cdb08`(20)**: `cda34 cda3c cda52 cda56 cda5e cda74 cda78 cda80 cda96 cda9a cdaa2 cdab8 cdabc cdac4 cdada cdade cdaf4 cdafc cdb00 cdb04`
- **`cdd86..cddba`(5)**: `cdd86 cdd9c cdda0 cddae cddb2`
- **`cde6e..cde96`(1)**: `cde6e`
- **`eaa00..eaa54`(10)**: `eaa00 eaa1a eaa20 eaa26 eaa34 eaa3a eaa3e eaa44 eaa4c eaa52`
- **`eaac0..eab42`(11)**: `eaac0 eaac6 eaaca eaad0 eaada eaafe eab2a eab30 eab36 eab3a eab40`

## 검증 수치

작업자 최종 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j3 all test`(최종 실행부·시험): 종료 0, 경고 0, Python 310 OK(`trial_logs/make_final.log`). FR10 시험 줄: `animation machine objects fr10: 1074 fixtures (646 single-block, 306 path, 36 producer chain, 28 declared C, 58 checked error (15 with a later failing PC), 109 kept C), 211 blocks, 4830 calls, 130326 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 출구 중 stop이 아닌 것 0, 실제 사슬 두 값 6개(`71012`→`71016`(`70594`), `b7a62`→`b7a68`(`484e2`), `b7a6e`→`b7a78`(`49392`), `eaac0`→`eaac6`(`1abda`), `70ff0`→`70ff4`(Z), `cd804`→`cd80a`(N)). `49fc6` 사슬 다섯은 `49fc6`이 bank 장치에 써서, `7028e` `705ca` `4b54e` 사슬은 선언 밖 ROM을 읽어 native run이 버려졌고, `28ae`(`cdd86`)·`eaa26`·`b7b3a`는 한쪽 결과만 나와 선언 C 행만 있다. 그 밖의 기존 C++ 시험은 모두 바뀌지 않고 통과한다.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, `work/ubsan.sh`, FR10 시험): 빌드 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_build.log` `ubsan_fr10.log`).
- [F] V1 fr10(작업자, `--workers 3`): fixture 2,170개(match 1,188, error 972, mismatch 10; natural 291) failed 0, 방문 시작 211/211, carry oracle Unknown/Clear/Set = 1,004/83/101(`work/v1/v1_fr10.log`). spec 보고의 빠진 후속 `70fd6`→`70fda`(`7028e` Set), `70ffe`→`71002`(`705ca` Set), `cd940`→`cd944`(`ccade`→`4b54e` Set)은 생산자의 Set 쪽이 무작위 world에서 나오지 않은 것이다(미확인 절; 선언 C 행·실제 ROM 차분이 덮음). 첫 시도(`trial_logs/v1_fr10_try1.log`, 2,166 fixture, failed 0) 뒤 사슬 hint(`484e2` `49392` `705ca` `7028e` `4b54e` RNG)와 `2986` 밖 `28ae` 실패를 받아들이도록 고쳤다.
- [F] V1 회귀(작업자, `work/v1_regs.sh`, `work/v1/v1_regs.txt`): pc1 1,264, pc2 1,743, pc3 1,829, pc4 1,873, pc5 1,755, pc6 1,856, pc7 2,077, pc8 986, pc9 2,347, se1 2,102, fr9 1,415, fr2b 1,761, fr3 1,458, fr4 1,629, fr7 1,815, fr8 1,933(모두 failed 0; pc1~pc9·se1은 C9 기록과 같은 수). FR10 PC를 정지·갈래로 가진 fr2b·fr3·fr4·fr7·fr8을 더 돌렸다. 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·op, WORD/BYTE → LONG, 복귀 PC·호출 대상, carry tag, mask, 상수·설치 값, `ofr10_*` helper 인자) + 손으로 고른 helper·block 변이(`ASR.L` 채움·부호, bank / 표 anim의 읽기·첨자·부호 확장, 방향 시험의 SEQ·EXT·EOR 폭, flag 읽는 `70ff4`(A0 폭)·`cd80a`(guard·24 bit·폭·반전), `MOVEM.W` 순서·부호 확장, `EORI` 뒤집기, carry 생산 tag, `b6c2c`·`b6c84` 부호 비교, `70f4e`·`b7aa8` 무부호 비교, `cd8fe` N만 보는 BPL 등) + dispatcher carry 목록 17개·추가·범위 14개를 적용해 만든 것, 686개; `--workers 4`): 1회째 `killed 668 of 686`(`trial_logs/mut_first.log`). 생존 18개 중 7개는 시험 빈틈이었고 합성 표(`b7f5c` 앞 LONG 넷, 칸 5 = `00038002`)와 규칙 `rules_d`로 메웠다(표 anim의 WORD 두 배·D0 위 bit 유지 둘, 음수 첨자 부호 확장, anim 선택의 WORD 비교, `b6c7c`의 WORD borrow, `eaa44`의 BYTE TST, `cd80a`의 홀수 A3; `trial_logs/mut_gaps.log`). 남은 11개는 동치다(`mut/equivalents.txt`, 사례별 이유: 곧 덮어쓰는 D0 위 bit 둘(`MOVE.L`·`EXT.L`), `am_write`의 자체 mask 둘, 값이 0/1이거나 00/ff인 비교 폭 둘, 다음 `MOVE.L`이 덮는 BYTE 1, 즉치 bit 번호 1, 이미 서 있는 채움 bit 1, 표 첨자의 낮은 WORD만 쓰는 LSL 1, work RAM 다시 읽기 1([I] PVC 창 A1은 어느 경로도 만들지 않음)). 규칙을 더한 뒤 전체 2회째 `killed 675 of 686`(`trial_logs/mut_second.log`), 남은 11개가 동치 목록과 같다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`, 메인 runner용), `real_fr10.py`(C9 harness에 FR10 world(`fr10_world`)·소비자 13 + `b7b40`·통과 3·flag 읽는 `70ff4`(native SR Z = (A0 = 0))·`cd80a`(native SR N = WORD (A3) bit 15)·선언 정지(fr10 `EXIT_STOPS`)·routing 밖 FR4 표 칸만 정지; 계산 점프 착지를 trace 전체에서 대조(FR4 `cc7a8`/`cc82a` 포함); 분류 `ZSOURCE10` 추가; `native_safe` 기본 유지)): 작업자 300건 seed 1 `mismatches 0`(`covered starts 193 of 211`; 문서화된 분류 0건; 깨끗이 멈추지 않은 native 50건 건너뜀; native oracle abort 0, `trial_logs/real_n300_s1.log`). 앞선 1,500건 다섯 batch(`trial_logs/real_d1..d5.log`; d1은 아래 고침 전, d2·d3·d4·d5는 고친 뒤): 모두 `mismatches 0`, 각 batch `covered starts 211 of 211`. 고침 전 d4(seed 4, FOLLOW_ANIM)의 1건이 `70f2c`→`70f3e`→N15 `71c48`의 C 경계였다(위 flag 절).
- [F] **IO, 입력 확장 관측**(FR10 연결 뒤, `--workers 3`): run 12, native 비교 frame 14,500 가운데 일치 **6,230**(예측 6,230, 기준선 5,839 → +391), 불일치 0(beyond 0), C++ 오류 0, chain divergence 0, 수용 키 모두 true(`negatives_ok` 포함, `P1` case 94)(`trial_logs/io_ext_fr10.log`; `verification.json` SHA256 `73e27b2773324c6d…`, `frontier.json` `960c218ab8c451d8…`). 첫 정지(확인된 frontier): X1 68 frame 590·X1 94 384·X2 68 608·X2 94 386 `1dccc`, X3 68 591 `252b4`, X3 94 391 `22148`, X4 68 520·X4 94 360 `223fa` — 재관측 예측(`reobs/fr10v1.stops`)과 run·frame·PC가 모두 같다. 모두 C10이다.
- [F] 원래 IO 관측·frame 비교·legacy 검증기는 작업자가 돌리지 않았다(메인 runner).
- [F] `CPP_PINS`: 작업 트리와 scratch clone root(`work/mkroot.py`; 확인 뒤 symlink를 먼저 지우고 삭제)에서 파일 SHA와 같다(4 / 9 pin, 불일치 0, `trial_logs/pincheck_tree.log` `pincheck_root.log`).

## 검증 기록(검증 실행: 결정적 runner + 메인 검토)

- [F] `make -j3 all test`: 종료 0, 경고 0, Assert 0, Python 310 OK. FR10 시험 `animation machine objects fr10: 1074 fixtures (646 single-block, 306 path, 36 producer chain, 28 declared C, 58 checked error (15 with a later failing PC), 109 kept C), 211 blocks, 4830 calls, 130326 checks`.
- [F] `ubsan`: 빌드/실행 종료 0, 런타임 오류 0.
- [F] `mutation`: 변이 686, 제거 675, 등가 11.
  - 이 실행 전에 메운 시험 빈틈 7개.
- [F] real-ROM: 배치 `f4`, `f5`, `s1`, `s2`, `s3` 커버 `211`, `211`, `211`, `209`, `211`; 불일치 `0,0,0,0,0`(합집합 211/211).
  - 오라클: `native_safe` 켬.
  - 범위: C7 표 항목 `252b4 252ce 252d8 252e2`는 C10에 남기고, `cd804`를 추가했다(`cd7c2`의 `BRA.W`).
  - 수정된 버그: real-ROM에서 `70f2c` / `70f3e`의 `71c48` 캐리 케이스를 찾아 이 실행 전에 고쳤다.
- [F] V1: A/B 각각 fixtures 2170, failed 0, identical true(digest `33da4558deac0f5f`); regression specs 43개 모두 failed 0.
- [F] legacy verifiers: `stage_entry`, `area_clear`, `stage_event`, `stage_event_ops`, `frame_helpers`, `card_menu_close`, `input`, `scene_core`, `scheduler`, `objects_g1` 모두 종료 0. `objects_g1` 판정은 C1과 같다.
- [F] frames: `d1` 완료 54400/54400, 불일치 0; `controller_game` 완료 54400/54400, 불일치 0; `irq` 완료 54400/54400, 불일치 0; `demo` 완료 45684/45684, 불일치 0.
- [F] IO(원래 관측): 일치 합계 173966, 기준 173966, 차이 0, 불일치 0, C++ 오류 0, 실행 2, 동일함; 설정별 `P0` 81600, `P1` 81600, `P1b` 8400, `boot-demo-0` 577, `boot-title-idle` 600, `boot-title-start` 906, `fx-bios-call` 3, `fx-c-input-read` 3, `fx-n-input-read` 3, `fx-queue-short` 1, `fx-start-c79a` 273.
  - 수락 항목은 모두 true이고, native frame 173966 전부 일치한다.
- [F] IO(확장 입력 관측): 일치 합계 6230, 기준 5839, 차이 391, 불일치 0, C++ 오류 0, 실행 2, 동일함; 설정별 `P0` 1200, `P1` 1200, `X1` 974, `X2` 994, `X3` 982, `X4` 880.
  - 예측 확인: 정확한 비트맵 재관측은 6230을 예측했고, 실측도 6230이다.
  - 수락 항목은 모두 true다. native 완료 frame 14500 중 6230이 일치한다(나머지는 다음 단위의 첫 정지 뒤).
  - 첫 정지: `1dccc 252b4 22148 223fa`(모두 C10).
- 검증 방법: 결정적 runner(LLM 없음). 이 기록 초안은 local Qwen이 썼고 메인이 검토·수정했다.

## 뒤 단위 변경 기록: objects FR11(2026-10-24, 작업자 Claude Opus 5.5 / high)

FR11 계약(`animation-machine-frontier-fr11-contract.md`) 결정 1·7에 따른 기록이다. FR10 실행부는 바뀌지 않았다.

- [F] **FR10의 뒤 단위 정지 가운데 FR11 진입**: `70e42` `70fac` `cd7e2` `cd92e` `cd96c`(위 "출구와 경계"의 FR11 다섯)가 FR11 block이 되었다. 나머지 여섯(FR12 `70f8e` `b6c58`, FR13 `70f60` `70fcc` `70ff8` `71028`)은 계속 뒤 단위 정지다.
- [F] 생성기 `generate_animation_machine_objects_fr10_test_table.py`의 오류 행 다섯(이전: 그 FR11 PC에서 `unsupported animation machine PC`)을 실패 PC를 지키거나 경로를 따라 옮겼다: `70e2a-then-70e42` → `70e2a-then-70e4a`(FR11 `70e4a`가 선언하지 않은 bank LONG `2a1110`을 읽음), `cd7cc-then-cd7e2` → `cd7cc-then-cd7e4`(홀수 node, FR10 `cd7e4`의 LONG 쓰기), `cd8ee-then-cd92e`(홀수 node, FR11 `cd92e`의 LONG 쓰기), `cd95a-then-cd96c`(홀수 node, FR11 `cd96c`의 WORD 읽기), `70f94-then-70fac` → `70f94-then-70fcc`(BYTE 82 bit 7: FR11 `70fac` → FR10 `70fc2` → FR13 `70fcc`). 다시 생성한 시험은 그 다섯 행만 바뀌었다(fixture 1,074 그대로).
- [F] V1 spec `fr10.py`: `ROUTED_LATER`에 FR11 진입 다섯을 더했다(FR10 run은 그 PC에서 계속 멈춘다). 오류 fixture 다섯을 같은 뜻으로 바꿨다(`70e2a-then-70e4a`는 원본 ROM에서 bank 읽기가 성공하므로 홀수 A7의 `JSR 49f8c` push로 실패시킴).

## 뒤 단위 변경 기록: objects FR12(2026-10-24, 작업자 Claude Opus 5.5 / high)

FR12 계약(`animation-machine-frontier-fr12-contract.md`) 결정 6에 따른 기록이다. FR10 실행부는 바뀌지 않았다.

- [F] **FR10의 뒤 단위 정지 가운데 FR12 진입**: `70f8e` `b6c58`가 FR12 block이 되었다. 나머지 넷(FR13 `70f60` `70fcc` `70ff8` `71028`)은 계속 뒤 단위 정지다.
- [F] 생성기 `generate_animation_machine_objects_fr10_test_table.py`의 오류 행 둘(이전: 그 FR12 PC에서 `unsupported animation machine PC`): `b6c2c-then-b6c58` → `b6c2c-then-b6c72`(홀수 A7: FR12 `b6c58` → FR10 `b6c66` → `b6c72 BSR b7cfa`의 push), `70f8a-then-70f8e`(홀수 node: FR12 `70f8e`의 `MOVE.L #70c0c,(A6)`, 실패 PC 그대로). 생성기를 다시 돌려 그 2행만 바뀜을 확인했다(fixture 1,074 그대로).
- [F] V1 spec `fr10.py`: `ROUTED_LATER`에 `70f8e` `b6c58`를 더했다(FR10 run은 그 PC에서 계속 멈춘다). 오류 fixture `b6c2c-then-b6c58` → `b6c2c-then-b6c72`(홀수 A7).

## 뒤 단위 변경 기록: objects FR13(2026-10-24, 작업자 Claude Opus 5.5 / high)

FR13 계약(`animation-machine-frontier-fr13-contract.md`) 결정 6에 따른 기록이다. FR10 실행부는 바뀌지 않았다.

- [F] **FR10의 뒤 단위 정지 가운데 FR13 진입**: `70f60` `70fcc` `70ff8` `71028`가 FR13 block이 되었다. FR10의 뒤 단위 정지는 이제 모두 routing되었다(FR11 다섯, FR12 둘, FR13 넷). `70ff8 MOVE.L A0,(A6)`는 FR13이 쓰기만 하는 RAM 값 쓰기다(표 `70d72`의 LONG; 다음 dispatch가 판정).
- [F] 생성기 `generate_animation_machine_objects_fr10_test_table.py`의 오류 행 여섯(이전: 그 FR13 PC에서 `unsupported animation machine PC`): `70f4e-then-70f60` → `70f4e-then-70f84-odd-stack`(홀수 A7: FR13 `70f60` → `70f7e` → FR10 `70f84 JSR 49fc6`의 push), `70fc2-then-70fcc`(홀수 node: FR13 `70fcc`의 `MOVE.L #71468,(A6)`, 실패 PC 그대로), `71020-then-71028` → `71020-then-72dd2-odd-stack`(FR13 `71028` → `7102e` → `72dd2 JSR 4b54e`의 push), `70ff0-then-70ff8` / `70fe4-then-70ff8`(홀수 node: FR13 `70ff8`의 `MOVE.L A0,(A6)`, 실패 PC 그대로), `70f94-then-70fcc` → `70f94-then-70fd2-odd-stack`(FR11 `70fac` → FR10 `70fc2` → FR13 `70fcc` → FR10 `70fd2 BSR 7028e`의 push). 생성기를 다시 돌려 그 6행만 바뀜을 확인했다(fixture 1,074 그대로).
- [F] V1 spec `fr10.py`: `ROUTED_LATER`에 `70f60` `70fcc` `70ff8` `71028`를 더했다(FR10 run은 그 PC에서 계속 멈춘다). 오류 fixture 여섯을 같은 뜻으로 바꿨다.
