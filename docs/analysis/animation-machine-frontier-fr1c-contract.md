# frontier 단위 FR1c(IO frontier `bc08c` + FR1a 자식 `d13b4`) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. 범위는 FR1 계약(`animation-machine-frontier-fr1-contract.md`) 끝 절 "FR1c 명세"의 root `bc08c`와, FR1b 계약이 크기 때문에 미뤄 둔 FR1a `d131a`의 `2986` 자식 `d13b4`(결정 1)다. 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB, mtime `1791291625`. 코드와 고정 표는 모두 `<100000`이라 CPU 주소와 파일 오프셋이 같다. bank 창 읽기 `200140` `200090` `20008c`는 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `e021858`(branch `claude/frontier-units`, FR1b 커밋). routing 기준 `engine/src/animation_machine.cpp` SHA256 `271ce329f1707033f14aca401e615538ab3d19b6655f7f92f5eef132f91d2eac`(= FR1b IO 재실행 `frontier.json`의 `routing_file_sha256`).
- [F] frontier 입력: FR1b 뒤 IO 재실행 `/Users/start/Workspce/ms5-scratch/fr1b/ioA/frontier.json`(SHA256 `063a5efc487bb1ae0fa9a2194fab49490cfb7a2a4b5ff558d91769e1cd4694c0`, 확정 run 55, frontier PC 10개). `bc08c`: 3 run(P1 2, P1b 1), frame 167, node callback LONG(A6) = `bc08c`, 호출자 복귀 `2ac2`. `d13b4`: 3 run(P1 2, P1b 1), frame 328, node callback LONG(A6) = `d13b4`, 복귀 `2ac2`.
- [F] 정적 디코드: capstone M68000, FR1·FR1b 계약과 같은 block 시작 규칙(분기 대상·fall-through, JSR/BSR 대상과 복귀 PC, `MOVE.L #imm,(A6)` 설치 값, 범위 밖에서 들어오는 실제 JSR/BSR/JMP 대상). routing된 PC, `RTS`, `TRAP`, `JMP (An)`에서 멈춘다. `28ae`/`2986` 자식 값은 기록만 한다.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr1c/`
  - `tools/`: FR1b scratch의 `hroute.py` `fclos.py` `unit_fr1.py` `refs.py` `xref.py` `longref.py` `callers.py` `probe_scan.py` `leafscan.py` `disgroup.py`를 경로만 바꿔 복사(`unit_fr1.py`에 `FR1PART=c2`(= `bc08c` + `d13b4`)·`d` 묶음 추가), `disr.py`(구간 디코드, routing 표시).
  - `starts_c2.txt`(FR1c 시작 215개) SHA256 `44c9ac354e63f3bd1bedf7fdecdf54bde5851cf10eb12a51e491c5fad3e99289`; `starts_c.txt`(`bc08c`만, 148) `8b4ce0695c74311baf724817e25bd955f1773a190bfc206aa1decd56a904dcc0`(FR1 계약 값과 같음); `starts_d.txt`(`d13b4`만, 67) `d2e42d4c8168d7d7cc83b70fe5b057725baa90dcb81013cb78a1393059b66017`; `unit_c2_B.out`(block별 디코드) `unit_c2_D.out`(범위 전체 디코드) `xref_c.out` `longref_c.out` `callers_c.out` `probe_c.out`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] FR1b가 routing된 현재 기준으로 FR1 계약의 FR1c 규칙(root `bc08c`)을 다시 돌렸다. 시작 148개, 범위 2개(`bc08c..bc404` `bc47c..bc7d6`), 이어 붙인 바이트 1746, SHA256 `b57fa00163a69a553fa1e4eef56d85daf9e6aa7b90de62437c04d69ba15d7e34`, `starts_c.txt` SHA256 `8b4ce069…`로 FR1 계약 값과 같다(FR1a·FR1b가 `bc08c`의 출구를 바꾸지 않음).
- [F] **`d13b4` 추가(결정 1).** FR1b 계약 결정 2가 "278 > 약 220"으로 미룬 FR1a `d131a`의 `2986` 자식(`d131a MOVEA.L #d13b4,A0; …; JSR 2986`, list `100bf4`)이다. 같은 규칙의 closure는 67 block(`4941e..4945e` `494c0..4950e` `d13b4..d159e` `d2206..d224c`, 명령 168)으로 FR1b 계약 값과 같다. `bc08c`와 합하면 215 ≤ 약 220이고 두 closure는 겹치지 않는다.
- [F] **`4941e..4945e` `494c0..4950e`(결정 2).** `d13b4`가 `JSR 494c0`(대상 선택)으로 들어가는 공유 helper 두 개다. 옛 F4 범위 표(`animation-machine-object-callbacks-f4-scope.md` U11 행 `49370..497ea`)에 들어 있었지만 U11 실행부는 이 둘을 구현하지 않았고(`497c8` `497dc`는 `JSR 4941e(PC)`를 경계로 둠), 재범위 뒤 N04(`72c3c`) N09(`af7e6`) N16(`79584` `79592` `79614`) U11(`497c8` `497dc`)이 모두 실행부 없는 경계 callee로 두었다(각 계약 "경계"). 이웃 `4945e..494c0`은 N08, `49370..4939e` `493bc..493fc`는 U11·N15, `4950e..`는 U15가 routing했다. 남은 F4 단위 중 이 둘을 범위로 가진 것은 없다(STATUS: F4 N01~N35 완료, 미뤄 둔 b 단위·고아 사슬 목록에 없음).
- [F] 최종: **215 block**, 6 범위, 명령 516, 짝수 PC 1224(내부 1009), 이어 붙인 바이트 2448, SHA256 `db5d5ebad6a1605ebcb7a2e457d520712995a2d3a46e39c96794c309dc0da4db`.

| root(진입) | block | 명령 | 범위 |
| --- | --- | --- | --- |
| `bc08c` | 148 | 348 | `bc08c..bc404` `bc47c..bc7d6` |
| `d13b4` | 67 | 168 | `4941e..4945e` `494c0..4950e` `d13b4..d159e` `d2206..d224c` |
| 합 | **215** | 516 | 6 범위 |

## 요약

- [F] **범위·block 수**(6 범위, 합 215):

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `4941e..4945e` | 64 | `9e5686373645dd958b4562a67a0c33d7809b1214b24f168494ff0134b477ef21` | 7 | 32 |
| `494c0..4950e` | 78 | `c954b02b0525721d4f37c034f7e30fdbf188bc8022e41f4d4905a6c724d18fda` | 12 | 39 |
| `bc08c..bc404` | 888 | `a608a6c9262f83fba0183695ecaf88c95e49f3efbfb4e3325599da09d8fed2bd` | 66 | 444 |
| `bc47c..bc7d6` | 858 | `d1f36ff57653cc45f0bd7db243e1649ab4352c46f7a17d59bc1c7f530a46cf6c` | 82 | 429 |
| `d13b4..d159e` | 490 | `0e0136c534dcb2d9b1a3458dd77050a070c563df6f1d3bfd2f7823b0f1353ab5` | 45 | 245 |
| `d2206..d224c` | 70 | `316ddd4130f8a1ad04280c6b3ae2148412b5c3ff212c7f76a18f7713d92ba8a0` | 3 | 35 |
| 합계 FR1c | 2448 | 이어 붙인 바이트 `db5d5ebad6a1605ebcb7a2e457d520712995a2d3a46e39c96794c309dc0da4db` | **215** | 1224(내부 1009) |

- [F] closure가 6 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 연속 Bcc 묶음 없음, X 소비(ADDX/SUBX/ROX) 없음, `TRAP` 없음, 계산 점프 없음, DBcc 없음, I/O port·bank 쓰기 없음, DIVU 없음. `MULU.W #1b33,D7` 1곳(`d14b8`).
- [F] **현재 routing과의 관계**: 6 범위의 짝수 PC는 모두 routing 밖이다(겹침 0). 경계 이웃: `4941c`(routing 밖 형제 `49416 JSR 493bc(PC); BCC.B 49410; BRA.B 49400`의 `BRA.B`)·`4945e`(N08 block), `494be`(N08 `RTS`)·`4950e`(U15 block), `bc08a`(U17 `RTS`)·`bc404`(`28ae` 자식 값, routing 밖 코드), `bc47a`(`bc404` 자식의 `RTS`, routing 밖)·`bc7d6`(`28ae` 자식 값, routing 밖 코드), `d13b2`(사각형 자료 `d13a4..d13b4` 끝)·`d159e`(routing 밖 형제 `MOVEA.L #d15c4,A0; …; JSR 2986`), `d2204`(routing 밖 형제의 `BRA.W d239c` 확장 word)·`d224c`(routing 밖 형제 `MOVE.W #1001,68(A6)…`).
- [F] **나가는 곳은 모두 routing돼 있다**(모두 그 실행부의 `case` block 시작): callee `28ae` `8ebe` `8ff4` `1ab80`(N05) `43e34` `49214`(N05) `49290` `49370`(U11) `4970a` `49f8c` `49fc6` `4ae4a`(N08) `4b6f4`(FR1a) `4be06` `4be2c` `4be34` `4bfa4` `c6a96`, 출구 `JMP 2a00`(`d156e`), `BRA.W 49462`(N08, `49504` `4950a`), `BRA.W d23a0`(N05, `d2240`), `JMP d2206`(`d1598`, 이 단위).
- [F] **참조**(ROM 전체 직접 분기·LONG 상수, scratch `xref.py` `longref.py` `callers.py`): 범위 밖에서 들어오는 실제 분기·설치·LONG은 모두 block 시작이다 — `4941e`(U11 `497c8` `497dc`, N09 `af7ee`, routing 밖 `497fa` `4980e` `4982a` `79490` `83796` `84614` `b60f4` `b6116` `b7b3a` 등 `JSR`), `494c0`(N04 `72c40`, N16 `79588` `79596` `79618`, routing 밖 `702f4 JMP` `74f8a` `757f8` `75838` `75854` `7586e` `758a0` `75902` `77910` 등 `JSR`), `bc08c`(U17 `bc060 MOVEA.L #bc08c,A0`, `28ae` 자식), `d13b4`(FR1a `d131a`, routing 밖 `d1348` `d1376 MOVEA.L #d13b4,A0`, `2986` 자식), `d2206`(N05가 읽는 `c6012` 표의 LONG `c6032`, 이 단위 `d1598 JMP`). 내부 PC로 보이는 분기(`bc3c0` ← `bc428`, `bc792` ← `bc7fa`)는 명령 중간의 가짜 디코드다(`bc424` `bc7f6`의 `JSR c6a96.l` 안). 내부 PC와 같은 LONG 상수 `00049446`(`6ff32`) `000d157c`(`a130`)와 시작 `d143c`와 같은 상수(`99ed8` `aa050` `b2ee4`)는 명령열 안의 우연한 바이트다 [F](각 위치의 디코드가 `BRA`/`MOVE.B #imm` 등).
- [I] 의미: `bc08c`는 U17 객체(`bc060`)가 `28ae`로 만드는 연출 객체다 — 위치 이동(`49290`, `4be2c`/`4bfa4`/`4be34`/`4be06`), bank 창 `200140` 애니메이션 표의 여러 항목(`1c` `8c` `c` `10` `14` `50` `58` `54` `4` `90`), LONG `36`/`3a`의 목표값(`64`, `fff00000`) 쪽 지수 감쇠(`ASR.L #5`), `28ae` 자식 `bc844`×2 `bc404` `bc7d6` `d6c78`, 소리 `8ebe` `c87` `c8c` `c8d`, `8ff4`, 부모 BYTE `62(c(A6))` := `ff`. `d13b4`는 FR1a `d131a`가 list `100bf4`에 넣는 `2986` 자식이다 — 소리 `8ebe` `35d` `364` `365`, bank 창 `200090` 애니메이션, `494c0`(가까운 플레이어 기록 `100cb8`/`100da8`을 사각형 `d13ac` 안에서 고름)로 대상 선택, 거리로 속도 계산(`MULU #1b33`, `ASR.L #5`), `4be34`·`49fc6`·`4ae4a`(`d1c9c`)·`4b6f4` 판정, `1ab80`(사각형 `d13a4`) 화면 밖이면 삭제(`2a00`), 끝 상태 `d1576`/`d1586` → `d2206`(bank 창 `20008c` 애니메이션, `c6a96`, LONG `92` := `d3e5c`, N05 `d23a0`). `4941e`는 (A0 기록, A6 자신, A1 사각형)의 X·Y 거리가 사각형 안이면 C Clear, 밖이면 C Set을 돌려주는 판정([F] `49432`/`49452`의 CMP 빌림 = 안, `49458`이 뒤집음), `494c0`는 D0의 플레이어 bit 중 사각형 밖인 쪽을 지우고(`494ea`/`49500` `EORI.B`) N08 `49462`로 가까운 쪽을 고르는 판정이다. 이름은 확정하지 않는다.

## 공통 규칙·native 검증 계획

FR1 계약 "공통 규칙·native 검증 계획"과 FR1b 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr1c.cpp`, 함수 `animation_objects_fr1c_block`. 오류 문자열은 `unsupported animation objects fr1c PC`(범위 안 내부 PC 직접 진입), `objects fr1c caller requires known carry`(C 소비 block에 Unknown C; 소비자 15개)다. DIVU·기타 단위 전용 오류는 없다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(6 범위, FR1b 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 15개, 결정 3·5), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, test 목록 실행 줄, 시험 target; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** routing 밖 실행 PC는 없다(모든 출구가 routing됨). U11 `49370`의 `TRAP #15`(`4937c`, A5 ≠ `108000`)는 U11 실행부가 PC := `4937c`로 끝내고 dispatcher가 `unsupported animation machine PC`를 낸다(U11 시험 `49370-trap`과 같음). 기존 시험이 stop으로만 보던 PC(`4941e`(U11 N09), `494c0`(N04 N16), `bc08c`(U17 자식 값), `d13b4`(FR1a 자식 값))는 stop 판정이 routing보다 먼저라 그대로 통과한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다(F4 관례). dispatcher 오류 확인에 쓰는 범위 옆 PC는 자료 PC(`d13a4` `d13ac` `d13b2`, 사각형 자료)뿐이다; 다른 단위·다음 frontier가 routing할 코드(`bc404` `bc7d6` `d159e` `d224c` `4941c` 등)는 탐침으로 쓰지 않는다.
- **오류 fixture의 실패 PC**(리뷰 0264 L-1): 기대 오류 fixture마다 실패 PC를 적고, 진입 PC와 다르면 같은 상태를 stop = 실패 PC로 실행해 정확히 그 PC에서 멈추는지 함께 확인한다.
- **자료 읽기**(live bus, F1 결정 3, 상한 검사 없음): LONG `200140`(bank 창)과 LONG `(LONG 22(A6)) + d`, d ∈ {`4` `c` `10` `14` `1c` `50` `54` `58` `8c` `90`}(`bc0da` `bc1b8` `bc202` `bc290` `bc2fe` `bc344` `bc3ae` `bc3da` `bc47c` `bc4cc` `bc520` `bc584` `bc5e8`), LONG `200090`과 `14(LONG 22(A6))`(`d13de`), LONG `20008c`와 `14(LONG 22(A6))`(`d2206`). RAM 읽기: node field(A6), WORD `42`/`46` of A0(`4941e` `4943e` `d144c` `d1486`), WORD `(A1)` `2(A1)` `4(A1)` `6(A1)`(`4941e`의 사각형; 단위 경로에서는 고정 ROM `d13ac`), 절대 주소 WORD `10000e`(`d1544`), BYTE `(19 + A6 + sext(D0.W))`(`d155a`), LONG `c(A6)`의 BYTE `62`(`bc6ae`, 씀). 단위 시험은 고정 ROM·bank 주소에 합성 typed physical byte를 둔다(ROM 자료가 아니다). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `494c0 MOVE.L A0,-(A7)` 뒤 `JSR 49370(PC)`(복귀 `494c6`), `494ca`/`49508`의 `MOVEA.L (A7)+,A1`. `JSR (PC)` 복귀: `494e0`(→ `494e6`) `494f6`(→ `494fc`). 모두 `am_push`/`am_pop`(홀수 A7은 checked 오류).
- **정수 연산.** `MOVE.W #imm,Dn`/`MOVE.B #imm,Dn`(하위만), `MOVE.L #imm`, `MOVE.W d(An),Dn`(상위 유지), `SUB.W`/`ADD.W`(WORD wrap, 상위 유지), `NEG.W`(WORD), `NEG.L`, `ASR.W #1`(WORD 산술), `ASR.L #1`/`ASR.L #5`(32 bit 산술: 부호 bit 복제, 명시 구현), `ADDI.W`/`SUBI.W`/`ANDI.W #ffc0`/`ANDI.W #3`(WORD), `MULU.W #1b33,D7`(무부호 16 × 16 → 32 bit D7 전체), `SWAP`, `CLR.W D0`, `SUB.L`/`ADD.L`(LONG wrap) 메모리, `EORI.B #1/#2,D0`(하위 BYTE만), `BSET.B`/`BCHG.B #n,15(A6)`, `ST.B`(BYTE := `ff`), `CLR.B`, `MOVE.B 19(A6),14(A6)`, `MOVE.B 19(A6,D0.W),14(A6)`(sext(D0.W)), `SUBQ.W #1,76(A6)`(WORD wrap; C = 옛 WORD가 0). 비교·분기: `SUBQ.W` + `BCC`(무부호 빌림), `MOVE.W` + `BEQ`, `CMPI.W #4/#1/#3` + `BNE`/`BEQ`/`BCS`, `CMPI.W #78/#80/#9d,42(A6)` + `BLE`/`BLT`(부호 WORD), `CMPI.W #1a0,46(A6)` + `BLE`, `CMPI.W #60,D0` + `BLE`, `CMPI.W #ffc0,D0` + `BGE`(부호 WORD), `TST.L` + `BPL`(LONG N), `SUB.W` + `BPL`(WORD N), `CMP.W D7,D0` + `BCS`(무부호 WORD), `CMP.W 6(A1),D7` + `BCC`, `BTST.B #n,15(A6)` + `BEQ`/`BNE`, `BTST #0/#1,D0`(Dn: LONG bit) + `BEQ`, `MOVE.L A0,D0` + `BEQ`(LONG Z), `TST.W D0` + `BEQ`. 같은 block 안에서 만들고 소비한다(예외: 결정 3의 C, 결정 4의 Z).
- **`TST.L 3a(A6)`(`bc2e2`).** 결과 flag는 다음 `JSR 49fc6`가 덮어 읽는 곳이 없지만 LONG 읽기 자체(홀수 A6 오류 등 bus 효과)는 원본대로 실행한다.

## carry

- [F] **소비 block 15개**(callee가 돌려준 C 또는 앞 block의 CMP C를 읽음):
  - `bc1f6 BCC.W bc200` / `bc338 BCC.W bc342` / `bc394 BCC.W bc402` / `bc6a2 BCC.W bc6ac` / `bc6de BCC.W bc6e8` / `bc74e BCC.W bc758` / `bc78a BCC.W bc7c0`: `49fc6`(interpreter known C). Set → `bc1fa` / `bc33c` / `bc398` / `bc6a6` / `bc6e2` / `bc752` / `bc78e`.
  - `bc79e BCC.W bc7b4`: `28ae`(할당 성공이면 `2908 ORI` Set, 실패면 `2912 ANDI` Clear). Clear → `bc7b4`, Set → `bc7a2`(새 자식 A0로 `4970a`).
  - `494c6 BCS.W 49508`: U11 `49370`(BYTE `568e(A5)` = 0이면 `49386 ORI` Set, 아니면 `4938c ANDI` Clear). Set → `49508`, Clear → `494ca`.
  - `494e6 BCC.W 494ee` / `494fc BCC.W 49504`: 이 단위 `4941e`(`49458`이 돌려줌). Set → `494ea` / `49500`.
  - `49458 EORI.B #1,CCR; RTS`: 앞 block(`49432` 또는 `49452`)의 CMP C를 뒤집어 돌려준다(결정 3). 소비자이자 반전 생산자다.
  - `d143c BCC.W d144c`: `494c0`(N08 `49462`가 `494a6`/`494ac` `ANDI` Clear, `494b4` `ORI` Set으로 끝냄). Set → `d1440`.
  - `d153a BCC.W d1544`: FR1a `4b6f4`(`4b700 RTS`가 전달). Set → `d153e`.
  - `d156a BCC.W d1574`: N05 `1ab80`(밖이면 U01 `1aafc` Set, 안이면 `1abd4 ANDI` Clear). Set → `d156e`(`JMP 2a00`).
- [F] **known C 생산**(결정 3·5):
  - `49432`(`SUB.W 2(A1),D7; CMP.W 6(A1),D7; BCC.W 49458`): C = 무부호 빌림(D7.W < WORD `6(A1)`). 분기하면(→ `49458`) Clear, 아니면(→ `4943e`) Set을 남긴다.
  - `49452`(`SUB.W (A1),D7; CMP.W 4(A1),D7`, fall-through `49458`): C = 무부호 빌림(D7.W < WORD `4(A1)`).
  - `49458`: 들어온 known C를 뒤집은 known C로 `RTS`(Unknown이면 checked 오류). 이 `RTS`가 C를 다른 단위로 넘긴다: U11 `497cc` `497e0`, N09 `af7f4`(모두 그 단위의 소비자), 이 단위 `494e6` `494fc`.
  - `bc7b0`(`ORI.B #1,CCR`, fall-through `bc7b4`): C Set을 남기지만 다음 block `bc7b4`(`MOVE.W`/`MOVE.L`)가 carry 보존이 아니어서 읽는 곳이 없다(B4b `2b74a`, FR1b `b32ea` 관례: 값은 남기고 보존 목록에는 넣지 않음).
- [F] 그래서 `carry_preserving_pc`에 넣는 것은 소비자 15개(`49458` 포함)뿐이다. Unknown C로 소비자에 들어오면 checked 오류다. 그 밖의 모든 block은 진입 때 Unknown이 되고 Unknown으로 끝난다(`49432` `49452` `49458` `bc7b0` 제외).
- [F] 다른 단위 소비자에게 C를 전달하는 `RTS`는 `49458`뿐이다. `494c0` 함수는 `BRA.W 49462`(N08)로 끝나 C는 N08이 정한다. 나머지 `RTS`(`bc0c0` `bc1b6` `bc200` `bc28e` `bc2fc` `bc342` `bc402` `bc4ca` `bc51e` `bc582` `bc5e6` `bc63e` `bc6ac` `bc6e8` `bc714` `bc758` `bc7c0` `bc7d4` `d1574`)는 node callback의 dispatcher 복귀(`2ac2`)다(IO 관측: `bc08c` `d13b4` 모두 node callback, 복귀 `2ac2`).
- [F] C를 읽지 않는 호출: `49290`(→ `MOVE.W`) `c6a96` `49f8c` `4be2c`/`4bfa4`(→ `BRA`/`MOVE.W`) `28ae`(`bc166` `bc18c` `bc376` `bc720` → `MOVE.W`) `49214`(→ `SUBQ`/`CMPI`) `49fc6`(`bc1b0` `bc57c` `bc5e0` `bc7ce` → `RTS`(dispatcher), `bc278` `bc2e6` → `BTST`, `bc4b6` `bc50a` `bc62a` `bc700` → `SUBQ`, `d14fe` → `BTST`) `43e34` `4be34`(→ `TST.L`/`JSR`) `4be06` `8ff4` `8ebe` `4970a`(→ `ORI`) `4ae4a`(→ `TST.W`) `c6a96`.
- [F] **flag 재계산(결정 4)**: `bc3aa BNE.W bc3da`는 앞 block `bc398`(`SUBQ.W #1,76(A6); BCC.W bc3aa`, 분기 쪽)의 Z를 쓴다. `bc3aa`의 선행은 그 하나뿐이고 SUBQ 결과가 WORD `76(A6)`에 그대로 있으므로 Z = (WORD `76(A6)` = 0)으로 정확히 재계산한다. 그 밖에 block 경계를 건너 다시 계산하는 flag는 없다(`49458`의 C는 결정 3).

## 객체 `bc08c` `bc08c..bc404`(66) `bc47c..bc7d6`(82)

공통 꼴 "bank 애니메이션 `anim(n, d)`" = `LEA 26(A6),A0; MOVE.W #e3,20(A6); MOVE.L 200140.l,22(A6); MOVE.W #n,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l`(n은 `100`, `bc584`만 `80`). "설치 x" = `MOVE.L #x,(A6)` 뒤 x로 fall-through, "설치만 x" = `MOVE.L #x,(A6)` 뒤 다른 다음 block. "감소 판정" = `SUBQ.W #1,76(A6); BCC.W` (옛 WORD ≠ 0이면 분기).

- **`bc08c`**(node callback, U17 `28ae` 자식): D0.W := `ff60`, D1.W := 0, `JSR 49290`(복귀 `bc09a`). **`bc09a`**: WORD `68` `1e` := `8834`, WORD `76` := `2d`, 설치 `bc0b2`.
- **`bc0b2`**(설치 값): 감소 판정 → `bc0c0 RTS`, 아니면 `bc0ba`: 설치만 `bc0c2` → `bc0c0`.
- **`bc0c2`**: BYTE `15` bit 0 := 1, D0.W := `4f`, D1.W := 7, D2.B := 0, `JSR c6a96`(복귀 `bc0da`). **`bc0da`**: anim(`100`, `1c`)(복귀 `bc102`).
- **`bc102`**: WORD `68` `1e` := `8820`, LONG `36` `64` := `30000`, LONG `3a` := 0, WORD `76` := 8, 설치 `bc132`.
- **`bc132`**: BYTE `15` bit 7 = 0 → `bc146`(`JSR 4bfa4`, 복귀 `bc14c`), 아니면 `bc13c`(`JSR 4be2c`, 복귀 `bc142`: `BRA bc14c`).
- **`bc14c`**: D0.W := WORD `76`, 0 → `bc1a0`, 아니면 `bc154`: D0.W ≠ 4 → `bc17a`, 아니면 `bc15c`: `28ae` 자식 `bc844`, D0.W := `14`(복귀 `bc16c`). **`bc16c`**: D0.W := `ffc0`, D1.W := 0, `JSR 49214`(복귀 `bc17a`).
- **`bc17a`**: WORD `76` −= 1, ≠ 0 → `bc1a0`, 아니면 `bc182`: `28ae` 자식 `bc844`, D0.W := `14`(복귀 `bc192`). **`bc192`**: D0.W := `ff90`, D1.W := 0, `JSR 49214`(복귀 `bc1a0`).
- **`bc1a0`**: 부호 WORD `42` ≤ `78` → `bc1b0`, 아니면 `bc1aa`: 설치만 `bc1b8` → `bc1b0`. **`bc1b0`**: `JSR 49fc6`(복귀 `bc1b6 RTS`).
- **`bc1b8`**(설치 값): anim(`100`, `8c`)(복귀 `bc1e0`). **`bc1e0`**: BYTE `62` := `ff`, 설치 `bc1ea`.
- **`bc1ea`** `bc32c` `bc388` `bc4b0` `bc504` `bc696` `bc6d2` `bc6fa` `bc742` `bc77e` `bc7c8`(설치 값): `JSR 43e34`(복귀 +6). 그 복귀 block `bc1f0` `bc332` `bc38e` `bc4b6` `bc50a` `bc69c` `bc6d8` `bc700` `bc748` `bc784` `bc7ce`: `JSR 49fc6`(복귀 +6).
- **`bc1f6`** `bc338` `bc6a2` `bc6de` `bc74e`(소비자): Clear → `bc200`/`bc342`/`bc6ac`/`bc6e8`/`bc758 RTS`, Set → `bc1fa`/`bc33c`/`bc6a6`/`bc6e2`/`bc752`: 설치만 `bc202`/`bc344`/`bc6ae`/`bc6ea`/`bc75a` → 같은 `RTS`.
- **`bc202`**: anim(`100`, `c`)(복귀 `bc22a`). **`bc22a`**: LONG `3a` := `8a000`, D0 := `fffd8000`, LONG `64` `36` := D0, 설치 `bc246`.
- **`bc246`** `bc2be`(설치 값): D0 := LONG `64` − LONG `36`, D0 := D0 ASR 5, LONG `36` += D0; D0 := `fff00000` − LONG `3a`, D0 := D0 ASR 5, LONG `3a` += D0; `JSR 4be34`(복귀 `bc26a`/`bc2e2`).
- **`bc26a`**: LONG `3a`의 N = 0 → `bc278`, 아니면 `bc272`: 설치만 `bc290` → `bc278`. **`bc278`**: `JSR 49fc6`(복귀 `bc27e`).
- **`bc2e2`**: LONG `3a` 읽기(TST, flag 미사용), `JSR 49fc6`(복귀 `bc2ec`).
- **`bc27e`** `bc2ec`: BYTE `15` bit 7 = 0 → `bc28e`/`bc2fc RTS`, 아니면 `bc288`/`bc2f6`: 설치만 `bc2fe` → 같은 `RTS`.
- **`bc290`**: anim(`100`, `10`)(복귀 `bc2b8`). **`bc2b8`**: 설치 `bc2be`.
- **`bc2fe`**: anim(`100`, `14`)(복귀 `bc326`). **`bc326`**: 설치 `bc32c`.
- **`bc344`**: anim(`100`, `50`)(복귀 `bc36c`). **`bc36c`**: `28ae` 자식 `bc404`, D0.W := `a`(복귀 `bc37c`). **`bc37c`**: WORD `76` := 3, 설치 `bc388`.
- **`bc394`**(소비자): Clear → `bc402 RTS`, Set → `bc398`: 감소 판정 → `bc3aa`, 아니면 `bc3a0`: 설치만 `bc47c`, `BRA bc402`.
- **`bc3aa`**: Z(= WORD `76` = 0, 결정 4) = 0 → `bc3da`, 아니면 `bc3ae`. **`bc3ae`**: anim(`100`, `58`)(복귀 `bc3d6`: `BRA bc402`). **`bc3da`**: anim(`100`, `54`)(복귀 `bc402`).
- **`bc47c`**(설치 값): anim(`100`, `4`)(복귀 `bc4a4`). **`bc4a4`**: WORD `76` := `f`, 설치 `bc4b0`.
- **`bc4bc`** `bc510` `bc630` `bc706`: 감소 판정 → `bc4ca`/`bc51e`/`bc63e`/`bc714 RTS`, 아니면 `bc4c4`/`bc518`/`bc638`/`bc70e`: 설치만 `bc4cc`/`bc520`/`bc640`/`bc716` → 같은 `RTS`.
- **`bc4cc`**: anim(`100`, `90`)(복귀 `bc4f4`). **`bc4f4`**: WORD `76` := `24`, BYTE `62` := 0, 설치 `bc504`.
- **`bc520`**: anim(`100`, `1c`)(복귀 `bc548`). **`bc548`**: LONG `36` `64` := `30000`, LONG `3a` := 0, 설치 `bc566`.
- **`bc566`** `bc5ca`(설치 값): `JSR 4bfa4`(복귀 `bc56c`/`bc5d0`).
- **`bc56c`** `bc5d0`: 부호 WORD `42` < `80`/`9d` → `bc57c`/`bc5e0`, 아니면 `bc576`/`bc5da`: 설치만 `bc584`/`bc5e8` → `bc57c`/`bc5e0`. **`bc57c`** `bc5e0`: `JSR 49fc6`(복귀 `bc582`/`bc5e6 RTS`).
- **`bc584`**: anim(`80`, `1c`)(복귀 `bc5ac`). **`bc5ac`**: LONG `36` `64` := `18000`, LONG `3a` := 0, 설치 `bc5ca`.
- **`bc5e8`**: LONG `2e` := `a00000`, anim(`100`, `4`)(복귀 `bc618`). **`bc618`**: WORD `76` := `1e`, 설치 `bc624`.
- **`bc624`**(설치 값): `JSR 4be06`(복귀 `bc62a`: `JSR 49fc6`, 복귀 `bc630`).
- **`bc640`**: BYTE `62` := `ff`, `JSR 8ff4`(복귀 `bc64a`).
- **`bc64a`** `bc658` `bc666`: D0.W := `c87`/`c8c`/`c8d`, D1.B := 0, `JSR 8ebe`(복귀 +e).
- **`bc674`**: BYTE `14` := BYTE `19`, WORD `20` := `e3`, A1 := `bcbd4`, D0.W := `100`, `JSR 49f8c`(복귀 `bc690`; A0 그대로). **`bc690`**: 설치 `bc696`.
- **`bc6ae`**: A0 := LONG `c`, BYTE `62(A0)` := `ff`, WORD `20` := `e3`, A1 := `bcc44`, D0.W := `100`, `JSR 49f8c`(복귀 `bc6cc`). **`bc6cc`**: 설치 `bc6d2`.
- **`bc6ea`**: BYTE `62` := 0, WORD `76` := `1e`, 설치 `bc6fa`.
- **`bc716`**: `28ae` 자식 `bc7d6`, D0.W := `a`(복귀 `bc726`). **`bc726`**: WORD `20` := `e3`, A1 := `bce74`, D0.W := `100`, `JSR 49f8c`(복귀 `bc73c`; A0 = `28ae`가 남긴 값). **`bc73c`**: 설치 `bc742`.
- **`bc75a`**: BYTE `62` `63` := `ff`, WORD `20` := `e3`, A1 := `bcee2`, D0.W := `100`, `JSR 49f8c`(복귀 `bc778`). **`bc778`**: 설치 `bc77e`.
- **`bc78a`**(소비자): Clear → `bc7c0 RTS`, Set → `bc78e`: `28ae` 자식 `d6c78`, D0.W := `a`(복귀 `bc79e`).
- **`bc79e`**(소비자): Clear → `bc7b4`, Set → `bc7a2`: D0.W := `fff4`, D1.W := `c`, `JSR 4970a`(복귀 `bc7b0`). **`bc7b0`**: C Set(fall-through `bc7b4`).
- **`bc7b4`**: WORD `76(A0)` := 2, 설치만 `bc7c2` → `bc7c0 RTS`. **`bc7c2`**(설치 값): 설치 `bc7c8`. **`bc7d4`**: `RTS`.

## 객체 `d13b4` `d13b4..d159e`(45) `d2206..d224c`(3) + helper `4941e..4945e`(7) `494c0..4950e`(12)

- **`d13b4`**(node callback, FR1a `2986` 자식) `d13c2` `d13d0`: D0.W := `35d`/`364`/`365`, D1.B := 0, `JSR 8ebe`(복귀 +e).
- **`d13de`**: BYTE `15` bit 4 := 1, WORD `68` `1e` := `e0ef`, `LEA 26(A6),A0; MOVE.W #da,20(A6); MOVE.L 200090.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 14(A1),A1; JSR 49f8c`(복귀 `d1418`).
- **`d1418`**: D0.W := WORD `76`, 0 → `d1432`, 아니면 `d1420`: D0.W = 1 → `d1432`, 아니면 `d1428`: BYTE `15` bit 0 반전, `BRA d1432`.
- **`d1432`**: A0 := `d13ac`, `JSR 494c0`(복귀 `d143c`). **`d143c`**(소비자): Clear → `d144c`, Set → `d1440`: D1.W := `40`, D0.W := `20`, `BRA d14b8`.
- **`d144c`**: D0.W := WORD `46(A0)` − WORD `46`, 부호 WORD `46` ≤ `1a0` → `d1466`, 아니면 `d145e`: D1.W := `40`, `BRA d1486`.
- **`d1466`**: D1.W := `50`, 부호 D0.W ≤ `60` → `d147a`, 아니면 `d1472`: D1.W := `70`, `BRA d1486`.
- **`d147a`**: 부호 D0.W ≥ `ffc0` → `d1486`, 아니면 `d1482`: D1.W := `50`(fall-through `d1486`).
- **`d1486`**: D0.W := −D0.W, D0.W := D0.W ASR 1(WORD), D7.W := WORD `42(A0)` − WORD `42`, N = 0 → `d1498`, 아니면 `d1496`: D7.W := −D7.W(fall-through `d1498`).
- **`d1498`**: D0.W += D7.W, D7.W := D1.W, D7 := D7 ASR 1(LONG 32 bit), D7.W += D1.W, 무부호 D0.W < D7.W → `d14a8`, 아니면 `d14a6`: D0.W := D7.W(fall-through `d14a8`).
- **`d14a8`**: D0.W := ((D0.W + `20`) & `ffc0`) − `20` + `40`(WORD 각 단계 wrap)(fall-through `d14b8`).
- **`d14b8`**: D7.W := D1.W, D7 := D7.W × `1b33`(무부호 32 bit), LONG `3a` := D7, D0 := SWAP(D0) & `ffff0000`, D0 := D0 ASR 5, BYTE `15` bit 0 ≠ 0 → `d14d4`, 아니면 `d14d2`: D0 := −D0(fall-through `d14d4`).
- **`d14d4`**: LONG `36` := D0, 설치 `d14de`.
- **`d14de`**(설치 값): D0 := `fff40000` − LONG `3a`, ASR 5, LONG `3a` += D0; D0 := LONG `36` ASR 5, LONG `36` −= D0; `JSR 4be34`(복귀 `d14fe`). **`d14fe`**: `JSR 49fc6`(복귀 `d1504`).
- **`d1504`**: BYTE `15` bit 5 = 0 → `d1514`, 아니면 `d150e`: 설치만 `d1576` → `d1514`.
- **`d1514`**: A0 := `d1c9c`, D0 := A0, 0 → `d1528`(정적으로 일어나지 않음, 결정 6), 아니면 `d1520`: A0 := D0, `JSR 4ae4a`(복귀 `d1528`).
- **`d1528`**: D0.W = 0 → `d1534`, 아니면 `d152e`: 설치만 `d1586` → `d1534`.
- **`d1534`**: `JSR 4b6f4`(복귀 `d153a`). **`d153a`**(소비자): Clear → `d1544`, Set → `d153e`: 설치만 `d1586` → `d1544`.
- **`d1544`**: D0.W := WORD `10000e` & 3, 무부호 < 3 → `d155a`, 아니면 `d1556`: D0.W := 1(fall-through `d155a`).
- **`d155a`**: BYTE `14` := BYTE `(A6 + 19 + sext(D0.W))`, A0 := `d13a4`, `JSR 1ab80`(복귀 `d156a`). **`d156a`**(소비자): Clear → `d1574 RTS`, Set → `d156e JMP 2a00`.
- **`d1576`**(설치 값): WORD `68` `1e` := `1001`, `BRA d1592`. **`d1586`**(설치 값): WORD `68` `1e` := `8820`(fall-through `d1592`).
- **`d1592`**: `JSR 8ff4`(복귀 `d1598`). **`d1598`**: `JMP d2206`.
- **`d2206`**(`c6012` 표 LONG `c6032`, `d1598`): `LEA 26(A6),A0; MOVE.W #d2,20(A6); MOVE.L 20008c.l,22(A6); MOVE.W #100,D0; …; MOVEA.L 14(A1),A1; JSR 49f8c`(복귀 `d222e`). **`d222e`**: D0.W := `22`, D1.W := 5, D2.B := 0, `JSR c6a96`(복귀 `d2240`). **`d2240`**: A0 := `d3e5c`, LONG `92` := A0, `BRA d23a0`.
- **`494c0`**(`JSR` 진입): push LONG A0, `JSR 49370(PC)`(복귀 `494c6`).
- **`494c6`**(소비자): Set → `49508`: A1 := pop LONG, `BRA 49462`. Clear → `494ca`: A2 := `100cb8`, A3 := `100da8`, A1 := pop LONG, D0 bit 0 = 0 → `494ee`, 아니면 `494e0`: A0 := A2, `JSR 4941e(PC)`(복귀 `494e6`).
- **`494e6`**(소비자): Clear → `494ee`, Set → `494ea`: D0.B ^= 1(fall-through `494ee`).
- **`494ee`**: D0 bit 1 = 0 → `49504`, 아니면 `494f6`: A0 := A3, `JSR 4941e(PC)`(복귀 `494fc`).
- **`494fc`**(소비자): Clear → `49504`, Set → `49500`: D0.B ^= 2(fall-through `49504`). **`49504`**: `BRA 49462`.
- **`4941e`**(`JSR` 진입): D7.W := WORD `46(A0)` − WORD `46(A6)`, BYTE `15(A6)` bit 1 = 0 → `49432`, 아니면 `49430`: D7.W := −D7.W(fall-through `49432`).
- **`49432`**: D7.W −= WORD `2(A1)`, C := 무부호 D7.W < WORD `6(A1)`; C Clear → `49458`, Set → `4943e`(known C 생산, 결정 3).
- **`4943e`**: D7.W := WORD `42(A0)` − WORD `42(A6)`, BYTE `15(A6)` bit 0 = 0 → `49452`, 아니면 `49450`: D7.W := −D7.W(fall-through `49452`).
- **`49452`**: D7.W −= WORD `(A1)`, C := 무부호 D7.W < WORD `4(A1)`(fall-through `49458`, known C 생산).
- **`49458`**(소비자·반전 생산자): C := not C, `RTS`.

## 자료 표(전사, routing 밖으로 둠)

[F] 원본 바이트 그대로다. 실행부는 표 내용을 코드에 넣지 않고 live bus로 읽는다.

| 표 | 범위 | 읽는 곳 | 내용 |
| --- | --- | --- | --- |
| 사각형 | `d13a4..d13ac` | N05 `1ab80`(A0 = `d13a4`, `d155a`) | `fff0ffc0 00200050` |
| 사각형 | `d13ac..d13b4` | `4941e`(A1 = `d13ac`, `d1432`→`494c0`→`494ca` pop) | `fec0ff00 01400200`(WORD `(A1)` = `fec0`, `2(A1)` = `ff00`, `4(A1)` = `0140`, `6(A1)` = `0200`) |
| bank LONG | CPU `200140` `200090` `20008c` | `bc08c` 객체 13곳, `d13de`, `d2206` | 물리 `200000` bank 값은 V1·실제 ROM 차분이 원본 bank 바이트로 읽는다(단위 시험은 합성). [U] 물리 `300000` bank에서의 쓰임 |

- [F] **callee에게 넘기기만 하는 자료**(이 단위는 읽지 않음): `49f8c`의 A1 = `bcbd4` `bcc44` `bce74` `bcee2`·bank 창 LONG이 가리키는 값; `4ae4a`의 A0 = `d1c9c`; LONG `92` := `d3e5c`; `28ae` 자식 값 `bc844` `bc404` `bc7d6` `d6c78`(다음 frontier); `49290` `49214` `c6a96` `4970a` `8ebe`의 D0..D2.

## 경계·routing 밖 출구

- [F] routing 밖 실행 PC: 없다. 단위 안 계산 착지도 없다(계산 점프 없음). 간접 경계는 U11 `49370` 안의 `TRAP #15` `4937c`(A5 ≠ `108000`)뿐이다.
- [F] routing된 출구·callee: "요약"의 목록. `RTS`로 끝나는 block 20개: `49458` `bc0c0` `bc1b6` `bc200` `bc28e` `bc2fc` `bc342` `bc402` `bc4ca` `bc51e` `bc582` `bc5e6` `bc63e` `bc6ac` `bc6e8` `bc714` `bc758` `bc7c0` `bc7d4` `d1574`.
- [F] 공유 진입: `4941e`는 U11 N09와 routing 밖 10곳 이상이, `494c0`는 N04 N16과 routing 밖 9곳 이상이, `d2206`은 N05 `c6012` 표가 쓴다. 이후 그 코드를 넣는 단위는 이 단위의 block 시작으로 끝나야 한다.
- [F] **native 정지 규칙 주의**(V1·실제 ROM 차분): FR1b의 `first_unrouted` 수정판(`8c16 < pc <= 8ca6` 내부, 정지 `2a00` `2a24`)을 그대로 쓴다. 이 단위의 출구 중 C++가 한 block으로 처리하는 잎(`8c16` 꼴)은 없다(scratch `leafscan.py`, "구현·검증 기록").

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1·FR1b spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0 := 플레이어 기록 `100cb8`/`100da8` 또는 자연 node, A1 := RAM 사각형 또는 `d13ac`, LONG `c(A6)` := 자연 node, BYTE `568e(A5)`, `494ca`/`49508`의 스택 LONG, PC).
- [I] IO 관측 상태가 이 단위의 실제 진입 상태다: `fr1b/ioA/frontier.json`의 확정 frontier(P1/P1b frame 167 `bc08c`, frame 328 `d13b4`, 둘 다 node callback, 복귀 `2ac2`). V1 spec에는 이 출처를 주석으로 적고, IO 비교 재실행(검증 작업자)이 자연 경로를 직접 확인한다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다 — `28ae` → `bc79e`(`bc78e` 진입), `49370` → `494c6`(`494c0`), `4941e`(`49432`/`49452` → `49458`) → `494e6`(`494e0`) `494fc`(`494f6`), `494c0`(→ `49370` → `4941e` → N08 `49462`) → `d143c`(`d1432`), `4b6f4`(→ `4b700`) → `d153a`(`d1534`), `1ab80` → `d156a`(`d155a`). `49fc6` → `bc1f6` `bc338` `bc394` `bc6a2` `bc6de` `bc74e` `bc78a`는 단위 시험에서 선언 C, V1·실제 ROM 차분에서 실제 사슬(Unicorn SR은 읽지 않는다). `49458`의 반전은 단위 시험에서 선언 C 행(복귀 LONG = `494e6`, 다음 소비자의 native 분기로 확인)과 실제 사슬 `494e0`/`494f6`으로 확인한다.
- node fixture: callback 진입(`bc08c` `d13b4`)과 설치 값(`bc0b2` `bc0c2` `bc132` `bc1b8` `bc1ea` `bc202` `bc246` `bc290` `bc2be` `bc2fe` `bc32c` `bc344` `bc388` `bc47c` `bc4b0` `bc4cc` `bc504` `bc520` `bc566` `bc584` `bc5ca` `bc5e8` `bc624` `bc640` `bc696` `bc6ae` `bc6d2` `bc6ea` `bc6fa` `bc716` `bc742` `bc75a` `bc77e` `bc7c2` `bc7c8` `d14de` `d1576` `d1586`)과 표 진입 `d2206`을 node callback으로 들어가 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- callee fixture: `4941e` `494c0`를 subroutine으로(복귀 LONG = sentinel) 들어간다.
- 단위 시험(Unicorn 생성기, FR1b 꼴): 시작 215개 × 들어오는 C 3가지, zero-step, 내부 PC 1009개 정확한 오류, 경계 stop(출구 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC, BYTE·WORD·LONG 부호 경계(BYTE ≥ `80`, WORD ≥ `8000`, LONG ≥ `80000000`, `ASR.L` 부호 bit, `MULU` 입력 `ffff`, `d155a` index sext 경계 `8000`)를 고르는 hint, `bc3aa` 직접 진입은 SR Z = (WORD `76` = 0)(결정 4).

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `probe_scan.py` `FR1PART=c2`, `engine/tests` `engine/tools` `tools/unit_fixture_specs` `tools/*.py`, `probe_c.out` 87줄):
  - 그대로 참인 것(stop-only 또는 자기 범위 밖 확인): U11 시험 `boundaries()` `want[]`(`497c8` `497dc` → stop `4941e`)·`497c4-c2` `497d8-c2` 등 stop 행, N09 시험 `at_pc[]`(`af7e6` → `4941e`)·`af738-*` `af798-ff`… stop 행, N04 시험 `want[]`(`72c30-c1-00` → `494c0`)·stop 행·`pc_of(...)==0x494c0`, N16 시험의 `494c0` stop 행(`7760e-*` `79566-real-*` `flow-79584-*` 등), N08 시험 `RANGES`(`4945e..494c0`, 자기 범위 끝), U17 시험 `bc060`(`28ae` stop, A0 = `bc08c` 레지스터 값)·`RANGES`(`bbf56..bc08c`, 자기 범위 끝), FR1a 시험 `d131a-0` `path-d131a-0`(`2986` stop, A0 = `d13b4`).
  - Python 관측기 `observe_animation_machine_objects_g2.py`의 `BOUNDARY_NAMED`(`bc08c`)는 고정 관측 도구다(pin된 역사 기록; 고치지 않음).
  - V1 spec: 현재 spec(`b1a`..`b4b` `c1` `c2` `c3b` `d9` `f6a`..`f6c` `fr1` `fr1b`)은 FR1c 시작을 직접 참조하지 않는다. FR1c 시작을 참조하는 routing된 코드(scratch `callers.py`)는 U11 `497c8` `497dc`, N04 `72c40`, N16 `79588` `79596` `79618`, N09 `af7ee`(`4941e`/`494c0` `JSR`), U17 `bc060`·FR1a `d131a`(자식 값, 실행하지 않음)뿐이고 이 단위들에는 V1 spec이 없다. [I] 따라서 b2a 꼴의 native 정지 조건 변화는 없다(다른 spec의 사슬이 `497b6..` `72c3c` `79584..` `af7e6`를 지나는지는 V1 회귀로 확인; 검증 작업자).
- [I] 계산 PC로 이 범위에 착지하는 숨은 탐침은 구현 뒤 `make test`로 찾는다. 찾으면 결정 7대로 옮기고 이 절에 더한다.
- [I] frame 회귀: `4941e`(U11 N09), `494c0`(N04 N16)는 기존 자연 frame에서도 닿을 수 있다. 그 frame이 지금까지 이 PC에서 `unsupported animation machine PC`로 끝났다면 더 진행한다(이득). 자연 불일치는 결함이다(검증 작업자).

## 결정

1. **범위.** FR1 FR1c 명세 148 block(`bc08c`)에 FR1a `2986` 자식 `d13b4`(67)를 더해 215 block. FR1a·FR1b와 겹침 0. `28ae` 자식 `bc844` `bc404` `bc7d6` `d6c78`은 따라가지 않는다(다음 frontier).
2. **`4941e` `494c0` routing.** 옛 U11 범위 행에 있었지만 구현된 적 없는 경계 callee(N04 N09 N16 U11)다. `d13b4` closure의 일부로 이 단위가 routing한다(메인 확인 필요). 이웃 N08(`4945e..494c0`)·U15(`4950e..`)·U11(`493bc` 앞)은 다시 routing하지 않고 `49504`/`4950a`는 N08 block 시작 `49462`로, `494c2`는 U11 `49370`으로 나간다.
3. **`49458 EORI.B #1,CCR; RTS`는 소비자이자 반전 생산자**(N16 결정 4 `792ac` `7961e`와 같은 꼴). 들어오는 C가 known이면 반대 값을 known으로 두고, Unknown이면 `objects fr1c caller requires known carry`(상태 보존). 앞 block `49432`(CMP 빌림: 분기 Clear / fall-through Set)·`49452`(CMP 빌림)가 known C를 만든다(N08 `4984e` `49862` 관례). `49458`은 carry 보존 목록에 넣는다.
4. **`bc3aa` Z 재계산**(유일 선행 `bc398` 분기 쪽, Z = WORD `76(A6)` = 0). 단위 시험의 Unicorn 직접 진입은 SR Z를 그 값과 같게 둔다(N05 결정 4 관례). V1 native는 SR = `2000`(Z = 0)으로 시작하므로 V1 spec의 `bc3aa` 직접 진입은 WORD `76` ≠ 0인 world만 쓰고, `bc3ae` 쪽은 `bc398` 진입으로 덮는다.
5. **carry 보존 목록.** 소비자 15개(`bc1f6` `bc338` `bc394` `bc6a2` `bc6de` `bc74e` `bc78a` `bc79e` `494c6` `494e6` `494fc` `49458` `d143c` `d153a` `d156a`)만 넣는다. `49432` `49452`는 자기 block에서 known C를 남기고(읽는 곳 `49458`은 보존 목록), `bc7b0`(Set)는 읽는 곳이 없다. C를 다른 단위로 넘기는 통과 `RTS`는 `49458`뿐이다.
6. **정적으로 일어나지 않는 분기 `d151c BEQ.W d1528`.** A0 = `d1c9c`(상수)라 `MOVE.L A0,D0`의 Z는 항상 0이다. 그래도 원본 그대로 구현하고(`D0 = 0`이면 `d1528`), `d1528`은 `JSR 4ae4a`의 복귀 PC라 block 시작이다. 단위 시험·V1 spec의 "빠진 후속" 점검에서는 이 한 쪽(`d1514 → d1528`)을 정적 불가능으로 빼고 이유를 적는다.
7. **숨은 탐침 이전.** 기존 시험이 이 범위의 PC를 routing 밖 rollback으로 기대하면 RAM `10fexx` 탐침이나 stop-only 확인으로 옮기고, 옮긴 곳은 "영향받는 기존 시험"과 "구현·검증 기록"에 적는다(정적 검색으로는 0건).
8. **`TST.L 3a(A6)`(`bc2e2`)** 는 flag를 쓰지 않지만 LONG 읽기를 그대로 한다(홀수 A6면 checked 오류).

## 미확인

- [U] BYTE `14` `15` `19` `62` `63`, WORD `1e` `20` `42` `46` `68` `76`, LONG `2e` `36` `3a` `64` `92`의 의미(객체마다 다름); bank 창 `200140` `200090` `20008c` 표 항목의 정체.
- [U] `bc08c` 연출의 화면상 정체, `d13b4` 객체의 정체, WORD `10000e`의 의미([I] frame 계수기), `d1c9c`(`4ae4a` 인자)의 정체.
- [U] 물리 `300000` bank에서 bank 창 LONG의 쓰임.
- [U] 자연 frame에서 이 단위 뒤 다음 첫 미routing PC(IO 비교 재실행으로 확인; [I] 예상: `28ae` 자식 `bc844` `bc404` `bc7d6` `d6c78`, `d23a0` 뒤 N05 경로의 다른 코드).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr1c.cpp`(case label 215 = scratch `starts_c2.txt`와 집합 일치, scratch 검사), `engine/tests/animation_machine_objects_fr1c_test.cpp`(생성 구역 + 수작성 규칙: `494c0`의 스택 순서(LONG A0, 복귀 LONG `494c6`)와 `494ca`/`49508`의 pop·A2/A3, `49458`의 C 반전, `49432`의 빌림 → `4943e`(Set)/`49458`(Clear), `d1498`의 `ASR.L #1`(D7 bit 16 → bit 15), `d14b8`의 `MULU`/`SWAP`/`CLR.W`/`ASR.L #5`/`NEG.L`, `bc246`의 `ASR.L #5`(음수), `bc3aa`의 Z 재계산(WORD `76` = 0/1/`8000` × 들어오는 C 3가지)과 `bc398` 경유 두 갈래, `d155a`의 sext(D0.W) index(`ffff` → `18(A6)`), `d1544`의 WORD `10000e`, `d1514`의 상수 A0, `d2206`의 bank 창 LONG, 범위 옆 자료 PC `d13a4` `d13ac` `d13b2`의 dispatcher 오류), `tools/generate_animation_machine_objects_fr1c_test_table.py`(생성기; 두 번 실행해 시험 파일 바이트 단위 같음, 약 70초, 로그 `gen1.log` = `gen2.log`), `tools/unit_fixture_specs/fr1c.py`(V1 spec; 정적 검사만 함 — `load_routing` 규칙 121개 뒤 시작 215개와 내부 1009개가 모두 `animation_objects_fr1c_block`, sentinel·`4937c`는 routing 밖, 정적 후속은 시작이거나 routing된 출구 21개, 사슬 14개의 소비자가 진입에서 닿음; 합성 기반 상태로 world·hint·error·chain/node/callee 생성 함수를 native 없이 실행해 Python 오류 0, 오류 fixture 1037개 이름 중복 0, `bc3aa` 직접 진입 world는 모두 WORD `76` ≠ 0). 공유 수정은 "공통 규칙"의 다섯 곳뿐이다.
- [F] native 정지 규칙(scratch `leafscan.py`): 출구 21개 중 routing 밖 내부 분기 대상이 보이는 것은 `4ae4a`(N08, `4abc0..4ae48` `e625e..`)뿐이고 FR1b 기록과 같이 그 실행부의 block 경계다. 단위 시험·V1 block fixture는 `4ae4a` 진입에서 멈춘다. `8c16` 꼴 잎은 없다.
- [F] 단위 시험 world: A7 = `10ef00`, LONG `8(A6)` = 형제 `10ec00`(`28ae` 성공 경로가 `4(8(A6))`에 씀), `494ca`/`49508`은 A7에 선언 LONG(사각형 포인터)을 둔다. 합성 typed physical byte(ROM 자료 아님): 사각형 `d13a4..d13b4`(`ffe0 ff80 0040 00a0 ff00 fe00 0200 0400`), bank 창 `200140`(→ `2a0400`) `200090`(→ `2a0500`) `20008c`(→ `2a0600`)와 `2a0400..2a0498` `2a0514` `2a0614`. 실제 생산자 사슬은 RAM만 읽는 `28ae`(free list WORD `104ca0`), `49370`(BYTE `568e(A5)`), `4941e`(RAM 사각형 `10ea00` 또는 합성 `d13ac`), `494c0`(→ `49370` → `4941e` → N08 `49462`), `4b6f4`(BYTE `5b86(A5)`), `1ab80`(합성 `d13a4`)로 두 C 값을 모두 만든다. `49452`의 기대 C는 생성기의 독립 Python 모델(native 끝 D7.W와 WORD `4(A1)`의 무부호 빌림)이고 Unicorn SR은 읽지 않는다. `bc3aa` 직접 진입은 SR Z = (WORD `76` = 0)으로 시작한다(결정 4).
- [F] `make -j3 all test`(작업자, scratch `make_all*.log`): 종료 0, 경고 0, Assert 줄 0, 시험 실행 273개, Python 310개 통과, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄. FR1c 시험 줄: `animation machine objects fr1c: 705 fixtures (497 single-block, 106 path, 42 producer chain, 30 declared C, 30 checked error (6 with a later failing PC), 95 kept C, 22 data C), 215 blocks, 3919 calls, 42442 checks`. 단일 block 표에서 모든 조건 분기의 두 쪽을 들어갔다(`d151c → d1528` 정적 불가능 제외, 누락 0), 출구 21개 + STOP이 모두 어떤 행의 stop이다. 기준(FR1b 로그 `fr1b/make_all2.log`) 대비 다른 시험 줄 변화 없음(새 줄만 추가) — 숨은 탐침 0, 이전한 기존 기대 0.
- [F] 검증 작업자 준비물(scratch, 실행하지 않음): `build_ubsan.sh`, `mut/run_mut.py`(변이 179개, `--check` 통과, 모든 변이가 원본과 다르고 문법 검사 통과), `realrom/real_fr1c.py`(FR1b harness에 FR1c world·소비자·진입·`bc3aa` SR Z; `py_compile`만), `runwrap.py` `run_frames.sh` `run_area_clear.py` `run_stage_entry.py`(경로만 바꿈). 실행 순서와 기대값은 scratch `HANDOFF.md`.
- [F] 검증 기록(검증 작업자 Sonnet 5.5 / medium, scratch `/Users/start/Workspce/ms5-scratch/fr1c/`, ROM SHA256 `29112a94...` 불변):
  - 시험 보강 1건(결함 아님, 시험 틈): 변이 `bc2e2-no-read`(`TST.L 3a(A6)`의 LONG 읽기 제거)가 처음 179개 중 유일한 생존이었다. 읽기는 홀수 A6의 checked 오류로만 관찰되고, 오류 행의 `fails_at`이 고정 stop(`ff000`)을 썼기 때문에 읽기를 건너뛴 변이도 `49fc6`에서 같은 오류를 내 구별되지 않았다. 생성기에 `err(..., stop=)` 인자와 행 `error-odd-node-bc2e2`(entry `bc2e2`, A6 = 노드 + 1, stop `49fc6`)를 추가하고 시험의 `fails_at`이 행의 stop을 쓰게 했다(생성 구역은 생성기로 재생성, 재생성 뒤 바이트 동일). 결과 줄: `706 fixtures (... 31 checked error (6 with a later failing PC) ...), 215 blocks, 3920 calls, 42444 checks`. 이전 기록의 "705 fixtures / 3919 calls / 42442 checks"는 이 보강 이전 값이다.
  - `make -j3 all test`: 종료 0, 경고 0, Assert 0, Python 310개 OK, FR1c 줄 위와 같음, 다른 시험 줄은 FR1b 기록과 같음. 생성기 재실행: 시험 파일 SHA256 `05b612a65421ca65...` 불변.
  - UBSan(보강 뒤 재실행): 종료 0, `runtime error` 0.
  - 변이: 보강 뒤 179/179 사망(보강 전 178/179; `bc2e2-no-read`는 동등 변이가 아니라 위 시험 틈이었다).
  - 실제 ROM 차분(8개 `program_rom_*.ms5d`, 5 x 1,500 사례; 수정 없이 실행): s1 s2 s3 f4 f5 모두 `mismatches 0`; 진입 합집합 215/215(개별 배치 누락: s1 `bc1e0`, s2 `bc0ba bc326 bc4a4`, s3 `bc6cc d1418`, f4 f5 없음); 실제 생산자 뒤 소비자 15개 모두 native 분기와 비교(f5 예: `49458` 222, `d153a` 200, `d156a` 256, 나머지 45..132); 홀수 레지스터·Unknown-C·인터프리터 dispatch 분류 0건(f5).
  - V1 `fr1c`(`MS5_SEED_DIR=artifacts/stage_entry_body`) 두 번: 1,755/1,755, `[(name,digest)]` 동일; `carry oracle ok`, `visited 215/215`, missing successors `[]`, unreachable outcomes `[]`; expect 종류 match 712 / error 1,033 / mismatch 10. 회귀(같은 wrapper): fr1 1,631 / fr1b 1,441 / b2a 1,386 / b4 1,830 / b4b 1,723 전부 통과(FR1b 기준선과 같음). 추가로 모든 다른 spec(b1a b1b b1c b2b b2c b2d b2e b3a b3b b3c c1 c2 c3b d9 f6a f6b f6c)도 failed 0 통과 — U11 `497b6` / N06 `ba296` / U10 `bac68`을 지나는 trace의 실패는 없었다(spec 변경 없음).
  - stage_entry 검증기(wrapper): 통과, 요약 카운트는 FR1b와 같고(cases 335, split 23,761, negatives 2,757, carry Unknown/Clear/Set 21,829/100/1,832) 요약 sha256만 `24f6f157...` -> `77e380f2...`로 달라졌다. FR1b와 FR1c의 `verification.json`을 필드별로 비교하면 차이는 `inputs`(소스 파일 해시), `artifacts` 경로, `compile_command`뿐이다(동작 필드 동일).
  - area_clear 검증기(wrapper): 통과, conditions 256 / frames 37,418 / split 117,537 / continuous 37,444 / negatives 181 / guards 26 동일; sha256 `cc05d3e1...` -> `8edeb7e3...`, 차이는 입력 해시·경로·compile 명령뿐.
  - frame 회귀: D1 / controller game / IRQ 54,400/54,400, demo 45,684/45,684, 자연 mismatch 0. FR1b와 `verification.json`을 비교하면(입력 해시·시간 제외) 변경된 frame 0건.
  - IO 비교(`verify_animation_machine_io.py` 두 번, ioA/ioB): `verification.json` SHA 동일(`f7e6381b...`), `frontier.json` SHA 동일(`5042cf64...`), mismatches 0, 예기치 않은 C++ 오류 0, 모든 acceptance true. routing_file_sha256 `00ff3a1b8bfb89d7...`.
    | 구성 | FR1b 첫 실패 전 일치 | FR1c | 차이 |
    |---|---|---|---|
    | P0 | 81,600 | 81,600 | 0 |
    | P1 | 61,942 | 62,586 | +644 |
    | P1b | 4,595 | 4,917 | +322 |
    | boot-demo-0 | 381 | 381 | 0 |
    | boot-title-idle | 600 | 600 | 0 |
    | boot-title-start | 113 | 113 | 0 |
    | fx (5개) | 275 | 275 | 0 |
    | 합계 | 149,506 | 150,472 | +966 |
    frontier 실행 56 -> 53(확정 52 + fixture 1). `bc08c`(3) 실행은 frame 217의 `bc844`(28ae 자식)로 이동했고 `d13b4`(3) 실행은 frontier에서 사라져 완주했다(complete_runs P1 92 -> 94, P1b 5 -> 6). 나머지 frontier 불변: `4e68e`(14) `c0ace`(12) `e5580`(12) `50dae`(3) `5ab82`(3) `b33d8`(3) `a8ee`(1) `1d1f4`(1). 새 frontier 목록 전체: `a8ee 1d1f4 4e68e 50dae 5ab82 b33d8 bc844 c0ace e5580`.

## block 목록

[F] scratch `starts_c2.txt`(SHA256 `44c9ac354e63f3bd1bedf7fdecdf54bde5851cf10eb12a51e491c5fad3e99289`)와 같다.

- **`4941e..4945e`(7)**: `4941e 49430 49432 4943e 49450 49452 49458`
- **`494c0..4950e`(12)**: `494c0 494c6 494ca 494e0 494e6 494ea 494ee 494f6 494fc 49500 49504 49508`
- **`bc08c..bc404`(66)**: `bc08c bc09a bc0b2 bc0ba bc0c0 bc0c2 bc0da bc102 bc132 bc13c bc142 bc146 bc14c bc154 bc15c bc16c bc17a bc182 bc192 bc1a0 bc1aa bc1b0 bc1b6 bc1b8 bc1e0 bc1ea bc1f0 bc1f6 bc1fa bc200 bc202 bc22a bc246 bc26a bc272 bc278 bc27e bc288 bc28e bc290 bc2b8 bc2be bc2e2 bc2ec bc2f6 bc2fc bc2fe bc326 bc32c bc332 bc338 bc33c bc342 bc344 bc36c bc37c bc388 bc38e bc394 bc398 bc3a0 bc3aa bc3ae bc3d6 bc3da bc402`
- **`bc47c..bc7d6`(82)**: `bc47c bc4a4 bc4b0 bc4b6 bc4bc bc4c4 bc4ca bc4cc bc4f4 bc504 bc50a bc510 bc518 bc51e bc520 bc548 bc566 bc56c bc576 bc57c bc582 bc584 bc5ac bc5ca bc5d0 bc5da bc5e0 bc5e6 bc5e8 bc618 bc624 bc62a bc630 bc638 bc63e bc640 bc64a bc658 bc666 bc674 bc690 bc696 bc69c bc6a2 bc6a6 bc6ac bc6ae bc6cc bc6d2 bc6d8 bc6de bc6e2 bc6e8 bc6ea bc6fa bc700 bc706 bc70e bc714 bc716 bc726 bc73c bc742 bc748 bc74e bc752 bc758 bc75a bc778 bc77e bc784 bc78a bc78e bc79e bc7a2 bc7b0 bc7b4 bc7c0 bc7c2 bc7c8 bc7ce bc7d4`
- **`d13b4..d159e`(45)**: `d13b4 d13c2 d13d0 d13de d1418 d1420 d1428 d1432 d143c d1440 d144c d145e d1466 d1472 d147a d1482 d1486 d1496 d1498 d14a6 d14a8 d14b8 d14d2 d14d4 d14de d14fe d1504 d150e d1514 d1520 d1528 d152e d1534 d153a d153e d1544 d1556 d155a d156a d156e d1574 d1576 d1586 d1592 d1598`
- **`d2206..d224c`(3)**: `d2206 d222e d2240`
