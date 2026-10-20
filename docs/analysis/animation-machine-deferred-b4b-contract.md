# 표 `2282c` 자식 `23a3e`, U06 옆 script 처리기 `e74f8`, B4 새 자식 callback 구현 계약 B4b

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. 범위는 B4 계약 끝 절 "후속 단위 명세(B4b)"다: 표 `2282c`(플레이어 BYTE `9e` = 3)의 `2986` 자식 `23a3e`와 helper `49636..496a6`(B4b-1), U06 옆 script 처리기 `e74f8`와 2 항목 점프 표 `e7504`/`e7508`, `28ae` 자식 `2b7be`(형제 stage event callback `2b7b8` 포함)·`e7996`(B4b-2), B4가 만든 새 자식 `22f7a` `23774`(`2986`) `2334c` `d206a`(`28ae`)와 `23a3e`가 만드는 `28ae` 자식 `281ea`(B4b-3). 결정 항목(끝)은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 코드와 고정 표는 모두 `<100000`이라 CPU 주소와 파일 오프셋이 같다. bank 창 읽기 `20003c..2000a0`은 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다(아래 "자료 표"). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `fc534f0`(branch `claude/b-final`, B4a 커밋). routing 기준 `engine/src/animation_machine.cpp` SHA256 `d13a5370cb4baa843ce7f601f2ef2de9346dfaf95d90fea3f7a6ca5028966894`. dispatch 사슬을 Python 조건식으로 옮겨 "routing된 PC"를 판정했다(scratch `hroute.py`, B4 도구와 같은 방식, 경로만 B4b scratch).
- [F] 정적 디코드: capstone M68000. block 시작 규칙은 B4 계약 "기준 입력"과 같다(분기 대상·fall-through, JSR/BSR 복귀 PC, 변위 없는 `MOVE.L #imm,(A6)` 설치 값; `28ae` 자식 값은 진입으로 따로 준다). routing된 PC에서 멈춘다. 진입: `23a3e e74f8 e7504 e7508 2b7b8 2b7be e7996 22f7a 23774 2334c d206a 281ea`.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/b4b/`
  - `hroute.py` `sdec.py` `closure2.py` `b3adis.py` `xref.py` `lrefs.py` `refs.py` `probe_scan.py`(B4 scratch 복사, 경로만 바꿈), `unit_b4b.py`(단위 정의·분류), `sz.py`(크기 재측정), `data2.py`(자료·이웃 확인), `blkdis.py`(block 표시 역어셈블 `b4b_dis.txt`), `blocks.txt`(block 한 줄 요약).
  - `starts.txt`(시작 198개) SHA256 `465f91f813a6df84cb40d30417c3d586a36a14f4f653c53c2341652d98b3cbf7`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 크기 판정

[F] B4a routing을 반영한 지금 routing으로 다시 쟀다(scratch `sz.py`; routing된 PC 제외, `28ae` 자식 값은 진입으로만):

| 후보 | 진입 | block | 명령 | 범위 |
| --- | --- | --- | --- | --- |
| B4b-1 | `23a3e` | 48 | 153 | `23a3e..23c56` `49636..496a6` |
| B4b-2 | `e74f8` `e7504` `e7508` `2b7b8` `2b7be` `e7996` | 36 | 97 | `2b6e6..2b7c6` `e74f8..e7546` `e7996..e7a44` |
| B4b-3 | `22f7a` `23774` `2334c` `d206a` `281ea` | 114 | 338 | `22f7a..22fe0` `2334c..233bc` `233be..2347e` `23480..2353c` `23774..237ca` `281ea..2822a` `2825c..28490` `4439e..443b8` `d206a..d20b0` |
| 합 B4b | 12 | **198** | **588** | 14 범위 |

- [F] B4 계약 명세와 같다(198 block, 588 명령). 198 ≤ 약 220이므로 **한 단위로 구현한다**(결정 1).

## 요약

- [F] **범위·block 수**(14 범위, 합 198):

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `22f7a..22fe0` | 102 | `a31063b6a7bea3e18200cba5a9a398176ccf9d8d4095a6ff5e6db0a5525314ef` | 11 | 51 |
| `2334c..233bc` | 112 | `1ccb5fe1c397c846669c824afef7d3fd5d864b42814697044a8692fbb8384df7` | 9 | 56 |
| `233be..2347e` | 192 | `8a0a411519ade9e583955e5151ec502c991ebc30adc5d175e34ff9b345bedb7f` | 20 | 96 |
| `23480..2353c` | 188 | `5d81d29e41af0d7353d3936c262e3f4581f66c0ae612936e2bc8ba55ed5550fc` | 23 | 94 |
| `23774..237ca` | 86 | `9c863cd35b12ccda8aa4a693a38f54cd714c63b9509ffe138867c9ca41e32c41` | 8 | 43 |
| `23a3e..23c56` | 536 | `3e455ae2174d11ae74ba5736babb70c8629d70be7913d780f49bcc64dadec9dc` | 36 | 268 |
| `281ea..2822a` | 64 | `84c724b51b914209b4db203b2166e6fd31cb24415dcef7623dd1796eda0c27c8` | 3 | 32 |
| `2825c..28490` | 564 | `543174a0f1d38b0d13707b556542a713970b07eac784fbe3967e42edb6ebd76d` | 36 | 282 |
| `2b6e6..2b7c6` | 224 | `b4c2678d6bda20ed0627af98003b554a49a23a1ec36875638d9ec82fd1dab5fc` | 15 | 112 |
| `4439e..443b8` | 26 | `9e511c595d47075e975fde0d7ba41a108b8bd15d50090362a89202efbf23525c` | 1 | 13 |
| `49636..496a6` | 112 | `53032ca81213cd2ab6aafad5297f20eaaffa399d9ddb31941e31cd2d5e535337` | 12 | 56 |
| `d206a..d20b0` | 70 | `4ddd1147097fa5dff75206b529a09c17f695f1fc1afd1de512ddc72a95e94a13` | 3 | 35 |
| `e74f8..e7546` | 78 | `ef98919f45557600f7ced94c4f67f40933809f94703fd6311b9a527d254a3ddf` | 8 | 39 |
| `e7996..e7a44` | 174 | `ddcc46fd9584765568ebbf99bd66bd6d09df7046d3ea82d9fa5f3f28abc14b79` | 13 | 87 |
| 합계 B4b | 2528 | 이어 붙인 바이트 `90a9b9e932ca2c7f636a6ad35c593e423a6fc87256971535667a493c1a6de6f1` | **198** | 1264(내부 1066) |

- [F] 명령 588개, 정적 closure가 14 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 연속 Bcc 묶음 없음, TRAP·I/O port·bank 변경·X 소비(ADDX/SUBX/ROX)·DIV 없음. 간접 분기 1곳(`e74fc JSR e7504(PC,D0.W)`, 결정 3). 범위 사이의 `233bc` `2347e` `2353c`(`RTS`)는 정적 참조가 없어 넣지 않는다(결정 2).
- [F] **현재 routing과의 관계**: 14 범위의 짝수 PC는 모두 routing 밖이다(겹침 0). 경계 이웃: `22f78`(B4 `RTS`)·`22fe0`(자료 `22fe0..23058`, `4ae4a` 인자), `2334a`(B4 `BRA.W 22c82`의 중간)·`233bc`/`2347e`/`2353c`(도달하지 않는 `RTS`, 결정 2), `2353c..`(함수 `2353e`, 자료 `2355c`), `23772`(B4 `RTS`)·`237ca`(자료 `237ca..`), `23a3c`(자료 `23a20..23a3e`)·`23c56`(routing 밖 다른 함수 `23c56..`), `281e8`(routing 밖)·`2822a`(routing 밖 형제 함수 `2822a..2825c`, 이것도 `2825c`를 설치한다), `2825a`(그 함수의 `RTS`)·`28490`(자료), `2b6e4`(자료 `2b6c4..2b6e6`)·`2b7c6`(routing 밖 `BSR.W 2b6e6; BRA.W 2b8fc`, 정적 참조 없음), `4439c`(B4 자료 sin/cos 끝)·`443b8`(routing 밖 다른 코드), `49634`·`496a6`(routing 밖 다른 함수), `d2068`·`d20b0`(routing 밖 `d20b0..`의 형제 코드), `e74f6`(U06 `RTS`)·`e7546`(U06 block), `e7994`(자료 `e7978..e7996`)·`e7a44`(routing 밖 `RTS`·자료).
- [F] **나가는 곳은 모두 routing돼 있다**: callee `1c9b8` `22a4c`(B4) `288c` `28ae` `3af8` `43e34` `43ea4` `43eb8` `443d2` `44602` `496c2` `4970a` `49f8c` `49fc6` `4ae4a` `4be06` `4be34` `4bfa4` `4c0ac` `8ebe` `8ff4` `c6a96`, 출구 `JMP 2a00`(삭제) 9곳(`22fd8` `233b6` `23478` `234da` `23536` `237c2` `23c4e` `28482` `e7a3e`), `BCC.W 22c82`(B4) 2곳, `BRA.W 2b8b6`(N28), `BRA.W d239c`. 새 `28ae` 자식 `41fe6`(`2b736` `2b778`)·`d1d08`(`e7a1c`)은 routing돼 있다. routing 밖 값은 자료뿐이다(아래).
- [F] **참조**(ROM 전체 직접 분기·LONG 상수 검색, scratch `xref.py` `lrefs.py`): 범위 밖에서 들어오는 실제 분기는 모두 block 시작이다 — `2b7c6` `2cb80` `2ccd6 BSR.W 2b6e6`, `37aaa` `eeeb0` `eeec2 JSR 4439e`, `27e3e` `280b6` `51d74` `5812a` `902a6` `9092a` `90954 JSR 49636`(+ LONG 상수 `9b85a` `9b8ec` `9dc08`), `27b8e` `311f6` `3405e` `43336` `5a340` `5eca6`(N25, routing됨) `91c52 JSR 4964e`(+ `92496` `92d80` `99a4a`), `d20d0` `d20e0 BRA.B d207c`. 자식 LONG: `23a3e` = 표 `22830` `22834` `22838` 와 `40bf2`, `281ea` = `MOVEA.L #281ea,A0`(`27b14` `27d26` `27d7e` `27f5a` `27fda` `432cc`), `2825c` = `28254`(형제 함수의 설치), `2b7be` = `e8cc0`, `2b7b8` = `e8cc8`(stage event 표), `22f7a` = `22e8a` `22f0e`, `2334c` = `231d0` `23276` `232b0`, `23774` = `235f0`, `d206a` = `23182`.
- [F] 내부 PC로 보이는 분기 7곳은 모두 명령이 아니다: `27c06 BRA.W 28436`·`27c26 BRA.W 28456`은 `27c02`·`27c22 MOVE.L #6000,D0`의 피연산자, `d20f2 BPL.B d208a`는 `d20ee JSR c6a96.l`의 피연산자, `e1b9a..e1bdc`의 `e74fd` `e7513` `e752d` `e753b` `e753f`(홀수)는 ASCII 문자열 자료다. 그래서 내부 PC 착지 0으로 본다.
- [I] 의미: `23a3e`는 플레이어 무기(BYTE `9e` = 3)의 탄이다. `28ae` 자식 `281ea`(꼬리 효과)를 만들고, `443d2`의 속도와 `4ae4a` 충돌, `49636`(대상 방향 각도)으로 BYTE `78` 방향을 감쇠 추적하는 유도탄이다. `281ea` → `2825c`는 부모(LONG `c(A6)`) 위치를 따라가며 `78(A6)..`의 8 byte 칸 7개 고리에 잔상(각도·반경)을 그려 `49fc6`로 보인다. `22f7a`·`23774`는 `2986` 자식 탄(분열·짝), `2334c`·`d206a`는 `28ae` 자식 폭발 효과와 `4bfa4` 반복, `e74f8`은 script 명령 인자 WORD로 `2b7be`(stage event 형제)나 `e7996`(떨어지는 물체)을 `28ae`로 만든다. `2b6e6`은 소리 셋을 내고 `41fe6` 자식을 BYTE `15` bit 0에 따라 BYTE `7e` 0/4로 만든다. `4439e`는 `(D0.W × cos, D0.W × sin) >> 8`, `4964e`는 A0 node의 중심점(사각형 `56(A0)` 반영, 반전 bit 0·1)이다. 이름은 확정하지 않는다.

## 공통 규칙·native 검증 계획

B1 계약 "공통 규칙"과 "공통 native 검증 계획", B2 계약 "자식(`28ae`) 진입 fixture", B2c~B4 계약의 공유 파일·macOS seed 관례를 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_b4b.cpp`, 함수 `animation_objects_b4b_block`. 오류 문자열은 `unsupported animation objects b4b PC`(범위 안 내부 PC 직접 진입)와 `objects b4b caller requires known carry`(C 소비 block에 Unknown C; 소비자 9개가 있으므로 둔다)다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(14 범위, B4 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 9개), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, test 목록 실행 줄, 시험 target; Codex의 object 재사용 구조 유지, SOURCES·HEADERS 줄은 각각 하나), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** 이 단위에서 routing 밖으로 나가는 실행 PC는 없다(간접 `e74fc`의 live 대상은 결정 3). 기존 시험이 stop으로만 보던 `e74f8`(U06 `script-jump`), `4964e`(N25 `5eca6`), `22f7a` `2334c` `23774` `d206a`(B4 단일 block 출구)는 stop 판정이 routing보다 먼저라 그대로 통과한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다(F4 관례).
- **오류 fixture의 실패 PC**(리뷰 0264 L-1). 기대 오류 fixture마다 실패 PC를 적는다. 실패 PC가 진입 PC와 다르면 같은 상태를 stop = 실패 PC로 실행해 정확히 그 PC에서 멈추는지(성공) 함께 확인한다.
- **자료 읽기**(live bus, F1 결정 3): 모든 표 읽기는 원본 주소 계산 그대로 live bus로 읽는다. 상한 검사는 원본에 없으므로 두지 않는다. 대상: LONG `20003c` `200050` `20008c` `200090` `200094` `20009c`(bank 창), LONG `c(LONG 22(A6))`(`d207c`)·`30(LONG 22(A6))`(`e79d0`), WORD `4419e + sext(D2.W)`·`4419e − 80 + sext(D2.W)`(`4439e`), WORD `4419e + sext(D4.W)`·`4419e − 80 + sext(D4.W)`(`28376` `2840a`), script WORD `(A0)+`(`e74f8`). 단위 시험은 이 고정 ROM·bank 주소에 합성 typed physical byte를 둔다(ROM 자료가 아니다). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `28376 MOVE.W D7,-(A7)`(WORD), 이어 `MOVE.L D0..D3,-(A7)`(D0 먼저, D3가 맨 위); `283c4 MOVE.L A1,-(A7)` / `283cc MOVEA.L (A7)+,A1`; `2840a ADD.L (A7)+,D3; ADD.L (A7)+,D2; MOVE.L (A7)+,D1; MOVE.L (A7)+,D0`, `MOVEM.L D0-D3,-(A7)`(낮은 주소에 D0); `28456 MOVEM.L (A7)+,D0-D3; MOVE.W (A7)+,D7`(하위 WORD만). `e74f8 MOVE.L A0,-(A7)` / `e7500 MOVEA.L (A7)+,A0`. `49636 JSR 4964e(PC)`(복귀 `4963a`). 모두 `am_push`/`am_pop`(홀수 A7은 checked 오류).
- **정수 연산.** `MULS.W`(부호 16 × 16 → 32), `ASR.L #8/#6/#3/#1`·`ASR.W #1`(부호 bit 채움; `.W`는 하위 WORD만), `LSL.W #8/#2`·`LSR.W #3`·`LSR.B #2`(해당 폭만), `SWAP`, `EXG`, `NEG.L`/`NEG.W`(레지스터), `SUB.L`/`ADD.L`(32 bit wrap, 메모리 포함), `ADD.W`/`SUB.W`(레지스터·메모리, WORD wrap), `ADD.B`/`SUB.B`(BYTE wrap), `ADD.B` 뒤 `SCS.B D5`(같은 명령의 carry: 두 BYTE 합 > ff), `OR.B`/`OR.W`, `ADDI.W`/`SUBI.W`/`ANDI.W`/`ADDI.B`/`ADDI.L`, `ADDQ.W #8`/`ADDQ.B #2`/`SUBQ.B #1`/`SUBQ.W #1`/`SUBQ.W #8`, `CLR.W Dn`(하위 WORD만)·`CLR.B`/`CLR.W`/`CLR.L` 메모리, `MOVEQ`(LONG), `MOVE.B`/`MOVE.W` → Dn(상위 유지), `MOVEA.L`, `LEA d16(An)`·`LEA (A1,Dn.W)`(부호 확장), `CMPA.L #0`/`CMPA.W #0`(A 전체 32 bit 비교). 비교·분기: `CMPI.B #0` + `BLE`(부호 BYTE ≤ 0), `CMPI.B #1`/`#ff` + `BEQ`/`BNE`, `CMPI.B #e0` + `BLS`(무부호 ≤), `CMPI.W #140`/`#100`/`#1000`/`#38` + `BCS`/`BCC`(무부호), `CMPI.L #180000` + `BCS`(무부호), `CMP.L D0,D1` + `BCC`(무부호 D1 ≥ D0), `CMP.W b0(A6),D7` + `BNE`, `SUBQ.B #1` + `BCC`(이전 BYTE ≥ 1), `SUBQ.W #8` + `BCC`(이전 WORD ≥ 8), `MOVE.L` + `BPL`/`BEQ`, `MOVE.W` + `BEQ`, `TST.B`/`TST.W` + `BEQ`/`BNE`, `CMPI.W #0` + `BEQ`, `OR.W` + `BNE`, `BTST` + `BEQ`/`BNE`. 모두 같은 block 안에서 만들고 소비한다. 68000 폭 그대로 명시 구현한다.
- **macOS seed.** 자연 seed가 필요한 V1·D1 실행은 B3a~B4와 같은 scratch wrapper가 `D.SEED_DIR`만 역사 관측 `artifacts/stage_entry_body`(SHA256 `1f65100f…`)로 바꾼다(도구 파일은 고치지 않음).

## carry

- [F] **소비 block 9개**(callee가 돌려준 C를 읽음; 각 block은 `BCC.W` 하나):
  - `22fd4 BCC.W 22fde` / `233ea BCC.W 233f4` / `234c6 BCC.W 234d0` / `237be BCC.W 237c8` / `23c4a BCC.W 23c54`: `49fc6`(interpreter known C). Clear → 분기 대상, Set → `22fd8 JMP 2a00` / `233ee`(설치 `23536`) / `234ca`(설치 `23536`) / `237c2 JMP 2a00` / `23c4e JMP 2a00`.
  - `28268 BCC.W 282de`: `288c`(A0 := LONG `c(A6)`; A0 = 0이면 `2898 ORI` Set, LONG `(A0)` = `270e`이면 `CMPI.L` 같음으로 Clear, 아니면 `28a8 ORI` Set). Clear → `282de`, Set → `2826c`.
  - `2b746 BCC.W 2b774` / `2b788 BCC.W 2b7b6` / `e7a2c BCC.W e7a3e`: `28ae`(성공 `2908 ORI` Set, 실패 `2912 ANDI` Clear, A0 = 더미 `100e98`). Clear → 분기 대상, Set → `2b74a` / `2b78c` / `e7a30`.
- [F] 9개만 `carry_preserving_pc`에 넣는다(B2c~B4 꼴). Unknown C로 들어오면 checked 오류다.
- [F] **known C 생산**: `2b74a` `2b78c`(설정 뒤 마지막 명령 `ORI.B #1,CCR`)와 `e7a3a`(`ORI.B #1,CCR` 한 명령)는 C Set을 만들고 `2b774`(`BRA.W`) / `2b7b6`(`RTS`) / `e7a3e`(`JMP 2a00`)로 이어진다. 다음 block은 소비자가 아니고 그 뒤에도 C를 읽는 곳이 없다: `2b6e6`의 호출자 복귀 `2b7c2 BRA.W 2b8b6`(`2b8b6 TST.W`), `2b7ca BRA.W 2b8fc`(`MOVE.W`), `2cb84 BSET`, `2ccda MOVE.W`; `2a00`은 `BSR.B 299c`(`LEA`). 실행부는 원본과 같게 이 셋에서 C Set을 남긴다(B4 `2319e` 관례). 그 밖의 모든 block은 진입 때 Unknown이 되고 Unknown으로 끝난다(block 안의 비교 C를 밖으로 내보내지 않는다).
- [F] `28ae` 뒤 C를 읽지 않는 호출: `23a3e`(→ `23a5c MOVE.W`), `e750c`(→ `e751c MOVE.W`), `e7534`(→ `e7544 RTS` → `e7500 MOVEA.L` → `RTS` → U06 `e74b0 MOVE.L A0,76(A6)`). `49fc6` 뒤 C를 읽지 않는 호출: `23bd2`(→ `23bd8 RTS`), `e7a14`(→ `e7a1a RTS`), `28450`(→ `28456 MOVEM`). helper `49636` `4964e` `4439e`의 반환 C를 읽는 호출자는 없다(`23b44 MOVEQ`, `4963a SUB.W`, `282a8 ADD.W`; 범위 밖 호출자는 그 단위가 확인한다). 그래서 소비자 없는 carry 보존은 만들지 않는다.
- [F] block 경계를 건너 다시 계산하는 flag는 없다(모든 Bcc는 같은 block 안의 비교·TST·MOVE·SUBQ·OR나 callee C를 읽는다).

## child `22f7a` `22f7a..22fe0`(11)

- **`22f7a`**: WORD `20` := `e2`, LONG `22` := LONG `200094`(bank 창), BYTE `8a` ≠ 0 → `22fa4`, 아니면 `22f90`.
- **`22f90`**: A1 := `24050`, D0.W := `100`, `JSR 49f8c`(복귀 `22fa0`). **`22fa0`**: `BRA.W 22fb4`. **`22fa4`**: A1 := `24120`, D0.W := `100`, `JSR 49f8c`(복귀 `22fb4`).
- **`22fb4`**: D0.W := `204`, D1.B := 0, `JSR 8ebe`(복귀 `22fc2`). **`22fc2`**: 설치 `22fc8`(fall-through).
- **`22fc8`**(설치 값): `JSR 43e34`(복귀 `22fce`). **`22fce`**: `JSR 49fc6`(복귀 `22fd4`). **`22fd4`**(소비자): Clear → `22fde RTS`, Set → `22fd8 JMP 2a00`.

## child `2334c` `2334c..233bc`(9) + `233be..2347e`(20) + `23480..2353c`(23)

- **`2334c`**: WORD `20` := `d2`, LONG `22` := LONG `20008c`, `JSR 4c0ac`(복귀 `23360`).
- **`23360`**: WORD `68` := `1001`, WORD `1e` := `1001`, BYTE `84` = 1 → `2341e`, 아니면 `23376`.
- **`23376`**: D0.W := `d5`, D1.B := 0, `JSR 8ebe`(복귀 `23384`). **`23384`**: A1 := `242e6`, D0.W := `100`, `JSR 49f8c`(복귀 `23394`). **`23394`**: LONG `(A6)` := `2339c`, `RTS`.
- **`2339c`**(설치 값): 부호 BYTE `82` ≤ 0 → `233c4`, 아니면 `233a6`: `JSR 4bfa4`(복귀 `233ac`). **`233ac`**: BYTE `15` bit 7 ≠ 0 → `233be`, 아니면 `233b6 JMP 2a00`.
- **`233be`**: BYTE `82` −= 1, `BRA.B 2339c`.
- **`233c4`**: `JSR 43e34`(복귀 `233ca`). **`233ca`**: A0 := `2301c`, `JSR 4ae4a`(복귀 `233d4`). **`233d4`**: LONG `(A6)` := `233de`(설치만), `BRA.W 233e4`.
- **`233de`**(설치 값): `JSR 43e34`(복귀 `233e4`). **`233e4`**: `JSR 49fc6`(복귀 `233ea`). **`233ea`**(소비자): Clear → `233f4`, Set → `233ee`: LONG `(A6)` := `23536`(설치만, `233f4`로 이어짐).
- **`233f4`**: D0.W := WORD `42`, 무부호 < `140` → `23406`, 아니면 `23400`: LONG `(A6)` := `23536`(설치만). **`23406`**: D0.W := WORD `46` − `100`, 무부호 < `140` → `2341c RTS`, 아니면 `23416`: LONG `(A6)` := `23536`(설치만), `2341c RTS`.
- **`2341e`**: WORD `20` := `e2`, LONG `22` := LONG `200094`, D0.W := `873`, D1.B := 0, `JSR 8ebe`(복귀 `2343a`). **`2343a`**: A1 := `243ec`, D0.W := `100`, `JSR 49f8c`(복귀 `2344a`).
- **`2344a`**: D0.B := `7f`, BYTE `12` := D0.B, BYTE `13` := D0.B, LONG `(A6)` := `2345e`, `RTS`.
- **`2345e`**(설치 값): 부호 BYTE `82` ≤ 0 → `23486`, 아니면 `23468`: `JSR 4bfa4`(복귀 `2346e`). **`2346e`**: BYTE `15` bit 7 ≠ 0 → `23480`, 아니면 `23478 JMP 2a00`. **`23480`**: BYTE `82` −= 1, `BRA.B 2345e`.
- **`23486`**: A0 := `2303a`, LONG `7c` := A0, `JSR 496c2`(복귀 `23494`). **`23494`**: 설치 `2349a`(fall-through).
- **`2349a`**(설치 값): `JSR 4be06`(복귀 `234a0`). **`234a0`**: D0 := LONG `7c`, 0 → `234c0`, 아니면 `234a8`: A0 := D0, `JSR 4ae4a`(복귀 `234b0`).
- **`234b0`**: D0.W = 0 → `234c0`, 아니면 `234b8`: LONG `7c` := 0. **`234c0`**: `JSR 49fc6`(복귀 `234c6`). **`234c6`**(소비자): Clear → `234d0`, Set → `234ca`: LONG `(A6)` := `23536`(설치만).
- **`234d0`**: BYTE `15` bit 7 ≠ 0 → `234e0`, 아니면 `234da JMP 2a00`.
- **`234e0`**: WORD `42` 무부호 < `140` → `234f2`, 아니면 `234ec`: LONG `(A6)` := `23536`. **`234f2`**: WORD `46` − `100` 무부호 < `140` → `23508`, 아니면 `23502`: LONG `(A6)` := `23536`.
- **`23508`**: D1.B := BYTE `12`, D1.B = `ff` → `23514 RTS`, 아니면 `23516`: D0.B := `ff`, D0.B −= D1.B, D0.B := D0.B >> 2(LSR.B), D1.B += D0.B, 무부호 D1.B ≤ `e0` → `2352c`, 아니면 `23528`: D1.B := `ff`. **`2352c`**: BYTE `12` := D1.B, BYTE `13` := D1.B, `RTS`.
- **`23536`**(설치 값): `JMP 2a00`.

## child `23774` `23774..237ca`(8)

- **`23774`**: WORD `20` := `e2`, LONG `22` := LONG `200094`, WORD `68` := `e000`, WORD `1e` := `e000`, D0.W := `8ba`, D1.B := 0, `JSR 8ebe`(복귀 `2379c`).
- **`2379c`**: A1 := `24502`, D0.W := `100`, `JSR 49f8c`(복귀 `237ac`). **`237ac`**: 설치 `237b2`(fall-through).
- **`237b2`**(설치 값): `JSR 4be34`(복귀 `237b8`). **`237b8`**: `JSR 49fc6`(복귀 `237be`). **`237be`**(소비자): Clear → `237c8 RTS`, Set → `237c2 JMP 2a00`.

## child `23a3e` `23a3e..23c56`(36)

- **`23a3e`**: WORD `20` := `5a`, LONG `22` := LONG `200050`, A0 := `281ea`, D0.W := `a`, `JSR 28ae`(복귀 `23a5c`).
- **`23a5c`**: WORD `76(A0)` := `10`, A1 := `246cc`, D0.W := `100`, `JSR 49f8c`(복귀 `23a72`). **`23a72`**: D0.W := `86e`, D1.B := 0, `JSR 8ebe`(복귀 `23a80`).
- **`23a80`**: D0.W := WORD `76`, `JSR 1c9b8`(복귀 `23a8a`). **`23a8a`**: WORD `68` := `e000`, WORD `1e` := `e000`, D0.W := `1a66`, `JSR 3af8`(복귀 `23aa0`).
- **`23aa0`**: BYTE `15` bit 3 := 1, bit 0 := 0, LONG `84` := 0, D0 := −LONG `3a`, D0 := ASR.L 6, WORD `7e` := D0.W, D0 := `80000`, LONG `64` := D0, D1.B := BYTE `78`, `JSR 443d2`(복귀 `23ad0`).
- **`23ad0`**: LONG `36` += D0, LONG `3a` += D1, WORD `82` := `1c2`, 설치 `23ae4`(fall-through).
- **`23ae4`**(설치 값): A0 := `23a02`, `JSR 4ae4a`(복귀 `23aee`). **`23aee`**: D0.B ≠ 0 → `23bda`, 아니면 `23af4`: BYTE `15` bit 5 ≠ 0 → `23bda`, 아니면 `23afe`.
- **`23afe`**: D0 := LONG `84` + `7fff`, 무부호 D0 < `180000` → `23b18`, 아니면 `23b12`: D0 := `180000`.
- **`23b18`**: LONG `84` := D0, D7 := 0, D0.W := WORD `82`, 0 → `23b56`, 아니면 `23b26`: D0.W −= 1, WORD `82` := D0.W, A0 := `239e4`, `JSR 4ae4a`(복귀 `23b36`).
- **`23b36`**: D7 := 0, D0.B = 0 → `23b56`, 아니면 `23b3e`: `JSR 49636`(복귀 `23b44`).
- **`23b44`**: D7 := 0, D7.B := D0.B, D7.W := D7.W << 8, D7.B := `80`, D7.W −= WORD `78`, `SWAP D7`, D7 := ASR.L 3.
- **`23b56`**: D7 −= LONG `7e`, D7 := ASR.L 1, LONG `7e` += D7, D0.W := WORD `7e`, WORD `78` += D0.W, D0 := LONG `84` − LONG `64`, D0 := ASR.L 3, LONG `64` += D0, D0 := LONG `64`, D1.B := BYTE `78`, `JSR 443d2`(복귀 `23b84`).
- **`23b84`**: D0 −= LONG `36`, D0 := ASR.L 3, LONG `36` += D0, D1 −= LONG `3a`, D1 := ASR.L 3, LONG `3a` += D1, D1.W := WORD `78`, D1.W := D1.W >> 3(LSR.W), D1.W += `80`, D1.W &= `1f00`, WORD `7c` := D1.W, BYTE `63` := BYTE `78`, `JSR 4be34`(복귀 `23bb6`).
- **`23bb6`**: D0.W := WORD `42`, 무부호 ≥ `140` → `22c82`(B4), 아니면 `23bc2`: D0.W := WORD `46` − `100`, 무부호 ≥ `100` → `22c82`, 아니면 `23bd2`: `JSR 49fc6`(복귀 `23bd8`). **`23bd8`**: `RTS`.
- **`23bda`**: D0.W := `1a24`, `JSR 3af8`(복귀 `23be4`). **`23be4`**: `BSR.W 22a4c`(복귀 `23be8`). **`23be8`**: A0 := `23a20`, `JSR 4ae4a`(복귀 `23bf2`). **`23bf2`**: LONG `(A6)` := `23bfa`, `RTS`.
- **`23bfa`**(설치 값): BYTE `61` bit 7 := 1, WORD `68` := `1001`, WORD `1e` := `1001`, `JSR 8ff4`(복귀 `23c12`). **`23c12`**: D0.W := `80b`, D1.B := 1, `JSR 8ebe`(복귀 `23c20`). **`23c20`**: A1 := `6f536`, D0.W := `100`, `JSR 49f8c`(복귀 `23c30`).
- **`23c30`**: LONG `36` := 0, LONG `3a` := 0, 설치 `23c3e`(fall-through). **`23c3e`**(설치 값): `JSR 43e34`(복귀 `23c44`). **`23c44`**: `JSR 49fc6`(복귀 `23c4a`). **`23c4a`**(소비자): Clear → `23c54 RTS`, Set → `23c4e JMP 2a00`.

## child `281ea` `281ea..2822a`(3) + `2825c..28490`(36)

- **`281ea`**: WORD `20` := `32`, LONG `22` := LONG `20003c`, D0.W := `37c`, D1.B := 0, `JSR 8ebe`(복귀 `28206`). **`28206`**: WORD `68` := `1001`, WORD `1e` := `1001`, A1 := `28da2`, D0.W := `100`, `JSR 49f8c`(복귀 `28222`). **`28222`**: LONG `(A6)` := `2825c`, `RTS`.
- **`2825c`**(설치 값): BYTE `61` bit 7 := 1, `JSR 288c`(복귀 `28268`). **`28268`**(소비자): Clear → `282de`, Set → `2826c`.
- **`2826c`**: BYTE `61(A0)` bit 7 ≠ 0 → `282de`, 아니면 `28276`. (A0는 `288c`가 준 LONG `c(A6)`; 0이면 고정 ROM `61`을 읽는다.)
- **`28276`**: BYTE `61` bit 7 := 0, D0.B := BYTE `63(A0)` + `80`, BYTE `b3` := D0.B, LONG `3e` := LONG `3e(A0)`, LONG `2e` := LONG `2e(A0)`, LONG `32` := LONG `32(A0)`, D0.W := WORD `76`, D1.B := BYTE `b3`, `JSR 4439e`(복귀 `282a8`).
- **`282a8`**: WORD `2e` += D0.W, WORD `32` += D1.W, A0 := LONG `c`, D0 := LONG `36(A0)`, bit 31 = 0 → `282be`, 아니면 `282bc`: D0 := −D0. **`282be`**: D1 := LONG `3a(A0)`, bit 31 = 0 → `282c8`, 아니면 `282c6`: D1 := −D1.
- **`282c8`**: 무부호 D1 ≥ D0 → `282d0`, 아니면 `282ce`: D0 ↔ D1. **`282d0`**: D1 := 2·D1 + D0, `SWAP D1`, D1.W += `10`, BYTE `64` := D1.B.
- **`282de`**: BYTE `62` −= 1; 이전 BYTE ≥ 1(빌림 없음) → `28324`, 아니면 `282e6`: BYTE `62` += 2, D0.W := WORD `b0` − 8; 이전 WORD ≥ 8 → `282f8`, 아니면 `282f4`: D0.W += `38`.
- **`282f8`**: WORD `b0` := D0.W, A1 := A6 + `78` + sext(D0.W), WORD `2(A1)` := 0, WORD `4(A1)` := 0, BYTE `7(A1)` := 0, BYTE `(A1)` := BYTE `b3`, BYTE `61` bit 7 ≠ 0 → `28324`, 아니면 `2831e`: BYTE `6(A1)` := `11`.
- **`28324`**: `JSR 43e34`(복귀 `2832a`).
- **`2832a`**: D0 := LONG `4a`, D1 := LONG `4e`, D2 := LONG `42` − D0, D3 := LONG `46` − D1, A0 := 0, A1 := A5 + `538e`, `JSR 43eb8`(복귀 `2834e`).
- **`2834e`**: D2 += D0, D3 += D1, LONG `3e` := A1, LONG `2e` := D2, LONG `32` := D3, D7.W := WORD `b0`, BYTE `63` := 0.
- **`28366`**(고리 머리): A1 := A6 + `78` + sext(D7.W), BYTE `6(A1)` = 0 → `2845c`, 아니면 `28376`.
- **`28376`**: push WORD D7, BYTE `63` := `ff`, BYTE `6(A1)` −= 1, A2 := `4419e`, D4 := 0, D4.B := BYTE `(A1)`, D4.W := 2·D4.W, D6.W := WORD `(A2 + sext(D4.W))`, D7.W := WORD `(A2 − 80 + sext(D4.W))`, D5.W := WORD `4(A1)`, D6 := sext(D6.W) × sext(D5.W), D7 := sext(D7.W) × sext(D5.W), D0 += D6, D1 += D7, push LONG D0 D1 D2 D3, D0 −= D2, D1 −= D3, `SWAP D0`, `SWAP D1`, D0.W <<= 2, D1.W <<= 2, D7.W := D0.W, D7.W |= D1.W, ≠ 0 → `283c4`, 아니면 `283be`.
- **`283be`**: D0 := 0, `BRA.W 283d4`. **`283c4`**: push LONG A1, `JSR 44602`(복귀 `283cc`). **`283cc`**: A1 := pop LONG, D0.W <<= 8, D0.W −= WORD `(A1)`, D0.W := ASR.W 1.
- **`283d4`**: D0.W −= WORD `2(A1)`, D0.W := ASR.W 1, D0.W += WORD `2(A1)`, WORD `2(A1)` := D0.W, WORD `(A1)` += D0.W, D4 := 0, D4.B := BYTE `7(A1)`, D4.B += BYTE `64`(carry 기록), D5.B := carry ? `ff` : 0(`SCS.B`), D4.B |= D5.B, BYTE `7(A1)` := D4.B, D4.W := 4·D4.W, D4.W += WORD `4(A1)`, 무부호 D4.W < `1000` → `2840a`, 아니면 `28406`: D4.W := `1000`.
- **`2840a`**: WORD `4(A1)` := D4.W, A2 := `4419e`, D4 := 0, D4.B := BYTE `(A1)`, D4.W := 2·D4.W, D2.W := WORD `(A2 + sext(D4.W))`, D3.W := WORD `(A2 − 80 + …)`, D5.W := WORD `4(A1)`, D2 := sext(D2.W) × sext(D5.W), D3 := sext(D3.W) × sext(D5.W), D3 += pop LONG, D2 += pop LONG, D1 := pop LONG, D0 := pop LONG, D6 := D2 + LONG `53a2(A5)`, D7 := D3 + LONG `53a6(A5)`, LONG `42` := D6, LONG `46` := D7, `MOVEM.L D0-D3,-(A7)`, BYTE `b2` := BYTE `6(A1)`, `JSR 49fc6`(복귀 `28456`).
- **`28456`**: `MOVEM.L (A7)+,D0-D3`, D7.W := pop WORD.
- **`2845c`**: D7.W += 8, 무부호 D7.W < `38` → `28468`, 아니면 `28466`: D7 := 0(MOVEQ, LONG). **`28468`**: D7.W ≠ WORD `b0` → `28366`, 아니면 `28470`.
- **`28470`**: BYTE `63` ≠ 0 → `28488`, 아니면 `28478`: BYTE `61` bit 7 = 0 → `28488`, 아니면 `28482 JMP 2a00`. **`28488`**: `JSR 43e34`(복귀 `2848e`). **`2848e`**: `RTS`.

## script 처리기 `e74f8` `e74f8..e7546`(8)

- **`e74f8`**: D0.W := WORD `(A0)`, A0 += 2, push LONG A0, `JSR e7504(PC,D0.W)`: 복귀 LONG `e7500`을 쌓고 PC := `e7504` + sext(D0.W)(결정 3).
- **`e7500`**: A0 := pop LONG, `RTS`.
- **`e7504`**(표 항목 0): `BRA.W e750c`. **`e7508`**(표 항목 4): `BRA.W e7534`.
- **`e750c`**: A0 := `2b7be`, D0.W := 0, `JSR 28ae`(복귀 `e751c`). **`e751c`**: WORD `76(A0)` := `ffff`, LONG `2e(A0)` := `a00000`, LONG `32(A0)` := `1ff0000`, `RTS`.
- **`e7534`**: A0 := `e7996`, D0.W := 0, `JSR 28ae`(복귀 `e7544`). **`e7544`**: `RTS`.

## child `e7996` `e7996..e7a44`(13)

- **`e7996`**: WORD `68` := `e0ef`, WORD `1e` := `e0ef`, LONG `2e` := `1400000`, LONG `32` := `1800000`, LONG `36` := `fff80000`, LONG `3a` := 0, D0.W := `23`, D1.W := `c`, D2.B := 0, `JSR c6a96`(복귀 `e79d0`).
- **`e79d0`**: A0 := A6 + `26`, WORD `20` := `da`, LONG `22` := LONG `200090`, D0.W := `100`, A0 := A6 + `26`, A1 := LONG `22`, A1 := LONG `30(A1)`(bank 창), `JSR 49f8c`(복귀 `e79f8`). **`e79f8`**: 설치 `e79fe`(fall-through).
- **`e79fe`**(설치 값): `JSR 43ea4`(복귀 `e7a04`). **`e7a04`**: A0 := `e7978`, `JSR 4ae4a`(복귀 `e7a0e`). **`e7a0e`**: D0.W ≠ 0 → `e7a1c`, 아니면 `e7a14`: `JSR 49fc6`(복귀 `e7a1a`). **`e7a1a`**: `RTS`.
- **`e7a1c`**: A0 := `d1d08`, D0.W := `1e`, `JSR 28ae`(복귀 `e7a2c`). **`e7a2c`**(소비자): Clear → `e7a3e`, Set → `e7a30`: D0.W := 0, D1.W := 0(`CLR.W`, 상위 유지), `JSR 4970a`(복귀 `e7a3a`). **`e7a3a`**: `ORI.B #1,CCR`(C Set). **`e7a3e`**: `JMP 2a00`.

## stage event 형제 `2b6e6` `2b6e6..2b7c6`(15)

- **`2b6e6`**: WORD `20` := `f2`, LONG `22` := LONG `20009c`, LONG `9e` := `2b3b8`(자료 포인터), D0.W := `3d3`, D1.B := 1, `JSR 8ebe`(복귀 `2b70a`). **`2b70a`**: D0.W := `39d`, D1.B := 1, `JSR 8ebe`(복귀 `2b718`). **`2b718`**: D0.W := `203`, D1.B := 1, `JSR 8ebe`(복귀 `2b726`).
- **`2b726`**: WORD `8e` := `8080`, BYTE `15` bit 0 ≠ 0 → `2b778`, 아니면 `2b736`.
- **`2b736`**·**`2b778`**: A0 := `41fe6`, D0.W := `a`, `JSR 28ae`(복귀 `2b746` / `2b788`). **`2b746`**(소비자): Clear → `2b774`, Set → `2b74a`. **`2b788`**(소비자): Clear → `2b7b6`, Set → `2b78c`.
- **`2b74a`**·**`2b78c`**: A1 := A6 + `8e`, LONG `76(A0)` := A1, BYTE `7a` `7b` `7c` `7d(A0)` := 0, BYTE `7e(A0)` := 0 / 4, `ORI.B #1,CCR`(C Set) → `2b774` / `2b7b6`.
- **`2b774`**: `BRA.W 2b7b6`. **`2b7b6`**: `RTS`.
- **`2b7b8`**(stage event 값): BYTE `15` bit 0 := 1(fall-through). **`2b7be`**(stage event 값, `28ae` 자식): `BSR.W 2b6e6`(복귀 `2b7c2`). **`2b7c2`**: `BRA.W 2b8b6`(N28).

## helper `4439e..443b8`(1)

- **`4439e`**: D2 := 0, D2.B := D1.B, D2.W := 2·D2.W, D1.W := D0.W, A0 := `4419e`, D0 := sext(D0.W) × W(A0 + sext(D2.W)), D1 := sext(D1.W) × W(A0 − 80 + sext(D2.W)), D0 := ASR.L 8, D1 := ASR.L 8, `RTS`. 표 읽기 순서는 cos(`4419e + 2k`), sin(`4411e + 2k`).

## helper `49636..496a6`(12)

- **`49636`**: `JSR 4964e(PC)`(복귀 `4963a`). **`4963a`**: D0.W −= WORD `42(A6)`, D1.W −= WORD `46(A6)`, `JSR 44602`(복귀 `49648`). **`49648`**: D0.W &= `ff`, `RTS`.
- **`4964e`**: A0 = 0(LONG 전체) → `49658`, 아니면 `49662`. **`49658`**: D0.W := `a0`, D1.W := `180`, `RTS`.
- **`49662`**: D0.W := WORD `42(A0)`, D1.W := WORD `46(A0)`, A1 := LONG `56(A0)`, A1 = 0(LONG 전체) → `496a4`, 아니면 `49676`.
- **`49676`**: D2.W := WORD `4(A1)`, D3.W := WORD `6(A1)`, D2.W := ASR.W 1, D3.W := ASR.W 1, D2.W += WORD `(A1)`, D3.W += WORD `2(A1)`, BYTE `15(A0)` bit 0 = 0 → `49694`, 아니면 `49692`: D2.W := −D2.W.
- **`49694`**: BYTE `15(A0)` bit 1 = 0 → `496a0`, 아니면 `4969e`: D3.W := −D3.W. **`496a0`**: D0.W += D2.W, D1.W += D3.W. **`496a4`**: `RTS`.

## child `d206a` `d206a..d20b0`(3)

- **`d206a`**: D0.W := `22`, D1.W := 3, D2.B := 0, `JSR c6a96`(복귀 `d207c`).
- **`d207c`**: A0 := A6 + `26`, WORD `20` := `d2`, LONG `22` := LONG `20008c`, D0.W := `100`, A0 := A6 + `26`, A1 := LONG `22`, A1 := LONG `c(A1)`(bank 창), `JSR 49f8c`(복귀 `d20a4`).
- **`d20a4`**: A0 := `d3e64`, LONG `92` := A0, `BRA.W d239c`.

## 자료 표(전사, routing 밖으로 둠)

[F] 원본 바이트 그대로다(scratch `data2.py`). index 범위는 원본에 상한 검사가 없어 [I]로 적는다. 실행부는 표 내용을 코드에 넣지 않고 live bus로 읽는다.

| 표 | 범위 | 읽는 곳 | 내용 |
| --- | --- | --- | --- |
| bank LONG | CPU `20003c..2000a0`(bank 창; bank_base = 물리 `200000`일 때 SHA256 `defd4d85a742e3f6dc6b2b980fa7e2d36ce2c0db80ab5e74861b72ab5718734b`) | `281ea`(`20003c`), `23a3e`(`200050`), `2334c` `d207c`(`20008c`), `e79d0`(`200090`), `22f7a` `2341e` `23774`(`200094`), `2b6e6`(`20009c`) | 물리 `200000` bank: `00290b7e` `0029351a` `002977dc` `002983f2` `002996ec` `0029c910`(순서대로). 물리 `300000` bank: `0022649c` `00235ce0` `0025e42c` `00263ed0` `00267dc4` `0026a7cc` |
| bank 안 LONG | `c(LONG 20008c)`, `30(LONG 200090)` | `d207c`, `e79d0` | 물리 `200000` bank: LONG `2977e8` = `00297a70`, LONG `298422` = `00298944`. 물리 `300000` bank: LONG `25e438` = `01000000`, LONG `263f00` = `1c5e8770`([I] 이 bank에서는 이 자식이 쓰이지 않는다) |
| sin/cos(WORD) | `4411e..4439e`(B4 계약 전사, SHA256 `398e75bf…`) | `4439e`(index 2·D1.B), `28376` `2840a`(index 2·BYTE `(A1)`) | cos = `4419e + 2k`, sin = `4419e − 80 + 2k` = `4411e + 2k`, k = 0..255 → `4411e..4439c` 안 |
| 점프 표 | `e7504..e750c` | `e74fc`(계산 대상) | `6000 0006`(`BRA.W e750c`) `6000 002a`(`BRA.W e7534`) |

- [F] **callee에게 넘기기만 하는 자료**(이 단위는 읽지 않음): `4ae4a`의 A0 = `2301c`(`233ca`) `23a02`(`23ae4`) `239e4`(`23b26`) `23a20`(`23be8`) `e7978`(`e7a04`)와 LONG `7c` 목록 원소(`2303a`, `234a8`); `49f8c`의 애니메이션 목록 A1 = `24050` `24120` `242e6` `243ec` `24502` `246cc` `6f536` `28da2`와 bank 안 LONG; `8ebe`의 소리 `204` `d5` `873` `8ba` `86e` `80b` `37c` `3d3` `39d` `203`; `3af8`의 D0 = `1a66` `1a24`; `443d2`의 D0 = `80000`·LONG `64`; `c6a96`의 (D0, D1, D2) = (`22`, 3, 0) (`23`, `c`, 0); `43eb8`의 A0 = 0, A1 = A5 + `538e`. 저장만 하는 포인터: LONG `9e` := `2b3b8`(`2b6e6`), LONG `92` := `d3e64`(`d20a4`), LONG `7c` := `2303a`(`23486`).
- [I] index가 [I] 범위 밖이면 원본은 다음 코드·표 바이트를 자료로 읽는다. C++도 같은 주소를 live bus로 읽는다(단위 시험에서는 합성 바이트 밖이라 bus checked 오류).

## 경계·routing 밖 출구

- [F] routing 밖 실행 PC: 없음(간접 `e74fc`의 live 대상은 결정 3). routing 밖 값은 위 자료뿐이다.
- [F] routing된 출구·callee: 위 "요약"의 22개와 `JMP 2a00`, `BCC.W 22c82`, `BRA.W 2b8b6`, `BRA.W d239c`. 반환은 `RTS` 17곳(`22fde` `23394` `2341c` `2344a` `23514` `2352c` `237c8` `23bd8` `23bf2` `23c54` `28222` `2848e` `2b7b6` `e7500` `e751c` `e7544` `e7a1a`의 child·처리기 끝, helper `4439e` `49648` `49658` `496a4`를 더해 21).
- [F] 공유 진입: `2b6e6`은 범위 밖 `2b7c6` `2cb80` `2ccd6`이, `4439e`·`49636`·`4964e`는 범위 밖 여러 함수(위 "참조")가, `2825c`는 형제 함수 `2822a`(`28254` 설치)가, `d207c`는 `d20d0` `d20e0`이 쓴다. 이후 그 코드를 넣는 단위는 이 단위의 block 시작으로 끝나야 한다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, B3a~B4 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0 := 자연 node(자식 기록·부모 기록) 또는 0, LONG `c(A6)` := 자연 node·RAM 기록·0, script 포인터 A0 := RAM의 선언 script WORD, `78(A6)..` 고리 칸, A5 기준 `10d3a2`/`10d3a6`, PC).
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다(`28ae` → `2b746`(`2b736` 진입) `2b788`(`2b778`) `e7a2c`(`e7a1c`), `288c` → `28268`(`2825c`), `49fc6` → `22fd4`(`22fce`) `233ea`(`233e4`) `234c6`(`234c0`) `237be`(`237b8`) `23c4a`(`23c44`); `49fc6`는 단위 시험에서 선언 C, V1·실제 ROM 차분에서 실제 사슬).
- node fixture: 자식 진입(`22f7a` `23774` `2334c` `d206a` `23a3e` `281ea` `e7996` `2b7be` `2b7b8`)과 설치 값(`22fc8` `2339c` `233de` `2345e` `2349a` `23536` `237b2` `23ae4` `23bfa` `23c3e` `2825c` `e79fe`)을 node callback으로 들어가 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- callee fixture: `4439e` `49636` `4964e` `2b6e6`과 script 처리기 `e74f8`(A0 = script WORD 0 / 4)을 subroutine으로(복귀 LONG = sentinel) 들어간다.
- 단위 시험(Unicorn 생성기, B4 꼴): 시작 198개 × 들어오는 C 3가지, zero-step, 내부 PC 1066개 정확한 오류, 경계 stop, rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC, BYTE·WORD 부호 경계(D0.B·D1.B ≥ `80`, WORD ≥ `8000`)를 고르는 hint, 간접 `e74fc`의 대상 전부(`e7504` `e7508`, 내부 `e7506` `e750a`, 홀수, 다른 routing PC, routing 밖).

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `probe_scan.py`: 14 범위 안 값, `engine/tests` `tools/unit_fixture_specs` `tools/*.py`):
  - B4 시험 `rules()`의 `data[]`(`unsupported animation machine PC` 기대): `22f7a` `2334c` `23774`가 이 단위 block 시작이 된다 → 결정 6대로 옮긴다(stop-only 확인으로 바꾸고 나머지 자료 PC는 그대로).
  - U06 시험 `boundaries()`: `script-jump`(stop `e74f8`) 행을 stop 없이 다시 돌려 `unsupported animation machine PC`를 기대한다 → 이 단위가 `e74f8`을 routing하므로 stop-only로 옮긴다. U06 생성 표의 오류 행 `error-script-boundary`(합성 jump script로 `e74f8`에서 rollback 기대)도 같은 이유로 RAM 탐침 처리기 대상으로 옮긴다(구현 뒤 `make test`로 찾음, 아래 기록). `rom_outside[]`의 `e74f8` `e7504` `e750c` `e7534` `e7544`는 U06 범위 밖인지만 본다(그대로 참).
  - N25 시험 `5eca6` 행(stop `4964e`)과 `at_pc[]`: stop-only(그대로 통과).
  - B4 생성 표의 `2986`/`28ae` 출구 행(`22e88` `22f0c` `235ee` `23180` `231ce` `23270` `23296`, stop = callee): stop-only(그대로 통과). 자식 값 `22f7a` 등은 레지스터 값으로만 나온다.
  - 그 밖의 일치(`23c40` `28346` `22fae` `23456` `23457` `23c00` `2b6e6`(B3b 행의 레지스터 값), `tools/*`의 `2b6e6`·`e74f8` 표)는 PC 기대가 아니다.
- [I] 계산 PC로 이 범위에 착지하는 숨은 탐침(예: 다른 단위의 node 사슬이 `e74f8` `2b7be` `4964e`를 지나 rollback을 기대하는 행)은 구현 뒤 `make test`로 찾는다. 찾으면 결정 6대로 옮기고 이 절에 더한다.
- [I] `e74f8`은 U06 script(`e7570..e7752`)가 부른다(demo 조사: script 시작에서 대략 frame 580·787·1001). 자연 frame이 그 경로를 지나면 지금까지 `e74f8`에서 끝나던 실행이 더 간다. frame 회귀(D1·controller·IRQ·demo)로 확인한다(다음 작업자).

## 결정

1. **범위.** 198 block을 한 단위로 구현한다(약 220 이하; B4 계약 권고).
2. **도달하지 않는 `233bc` `2347e` `2353c RTS`.** 정적 참조가 없으므로 넣지 않고 routing 밖으로 둔다(B4 결정 2와 같은 꼴). 범위는 `2334c..233bc` `233be..2347e` `23480..2353c`로 나뉜다.
3. **간접 `e74fc JSR e7504(PC,D0.W)`.** 복귀 LONG `e7500`을 쌓고 PC := `e7504 + sext(D0.W)`(32 bit)로 옮긴 뒤 대상 검사는 routing에 맡긴다(U06 결정 3의 `e74ac`와 같은 꼴): `e7504`·`e7508`이면 그 block, 이 단위의 다른 짝수 PC면 그 block 또는 `unsupported animation objects b4b PC`(예: `e7506` `e750a`), 홀수면 `unaligned animation machine PC`, 그 밖은 그 PC의 routing(routing 밖이면 `unsupported animation machine PC`). 원본 표는 정적으로 두 항목(WORD 0, 4)이다. F1 결정 3대로 표 밖 착지는 원본 그대로 따라가거나 checked 오류다.
4. **자료.** 표·bank 읽기는 live bus, 상한 검사 없음(F1 결정 3). 표 바이트(`22fe0..23058` `237ca..` `23a20..23a3e` `2b6c4..2b6e6` `e7978..e7996`)와 sin/cos 표는 routing하지 않는다.
5. **carry 보존 목록.** 소비자 9개만 넣는다. `2b74a` `2b78c` `e7a3a`는 자기 block 안에서 known C Set을 남긴다(읽는 곳 없음). `2b6e6`의 반환 C(`2b774` `2b7b6`)와 `e7544`/`e7500`의 `28ae` C는 읽는 곳이 없어 보존하지 않는다.
6. **숨은 탐침 이전.** 기존 시험이 이 범위의 PC를 routing 밖 rollback으로 기대하면 RAM `10fexx` 탐침이나 stop-only 확인으로 옮기고, 옮긴 곳은 "영향받는 기존 시험"과 "구현·검증 기록"에 대응을 적는다.

## 미확인

- [U] BYTE `61` bit 7, BYTE `62` `63` `64` `82` `84` `8a` `b2` `b3`, WORD `76` `7c` `7e` `82` `8e` `b0`, LONG `64` `7c` `84` `92` `9e`와 고리 칸(`78(A6)..`, 8 byte × 7)의 의미; `4ae4a` D0(충돌 [I])·`49636` D0(각도 [I])·`288c` C(부모 생존 [I])의 정확한 의미.
- [U] 화면상 무기·효과 이름, `e74f8` script 인자 WORD의 실제 값 집합(정적으로는 0·4만 표가 받는다).
- [U] 물리 `300000` bank에서 `d207c` `e79d0`가 읽는 bank 안 LONG의 쓰임.
- [U] 자연 400 frame·demo에서 이 단위 범위(특히 `e74f8`, `2b7be`, `4964e`)의 도달.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_b4b.cpp`(case label 198 = scratch `starts.txt`와 집합 일치), `engine/tests/animation_machine_objects_b4b_test.cpp`(생성 구역 + 수작성 규칙: `28376`의 스택 순서(WORD D7, LONG D0..D3), `2840a`의 pop 순서(D3 D2 D1 D0)와 `MOVEM.L D0-D3,-(A7)`, `28456`의 `MOVEM.L (A7)+` / `MOVE.W (A7)+,D7`(상위 WORD 유지), `e74fc` 대상 여섯(`e7504` `e7508` `e750c` `e7534` `e7544` `e7546`)과 음수 WORD `fff4`(부호 확장, `e74f8` 재진입), RAM 복귀 LONG `10fe40`의 rollback, 자료·도달하지 않는 PC 8개의 dispatcher 오류), `tools/generate_animation_machine_objects_b4b_test_table.py`(생성기; 두 번 실행해 시험 파일 바이트 단위 같음, SHA256 `b04836e5cc1a700a…`, 약 70초), `tools/unit_fixture_specs/b4b.py`(V1 spec; 정적 검사만 함 — `load_routing` 규칙 118개 뒤 시작 198개가 모두 `animation_objects_b4b_block`, 정적 후속은 시작이거나 범위 밖, 내부 1066; `first_unrouted`는 B4 spec의 capstone 길이 디코드판). 공유 수정은 "공통 규칙"의 다섯 곳뿐이다.
- [F] 단위 시험 world: A7 = `10ef00`; pop하는 block(`283cc` `2840a` `28456` `e7500`)은 A7 아래에 선언한 스택 WORD를 둔다. 합성 typed physical byte: bank `20003c..2000a0`(`20008c` → `2a0000`, `200090` → `2a0100`), bank 안 LONG `2a000c` `2a0130`, sin/cos `4411e..4439e`, 그리고 `0000..0080`의 128 byte(C++ program bus는 `0..7f`를 vectors view로만 읽으므로 시험이 `bus.vectors`로 넘긴다; `2826c BTST.B #7,61(A0)`의 A0 = 0, `288c`가 부모 없음으로 C Set을 준 경로). Unicorn 쪽은 같은 바이트를 고정 ROM 위치에 겹쳐 둔다.
- [F] `make -j3 all test`(작업자): 종료 0, 경고 0, Assert 줄 0, 시험 실행 270개, Python 310개 통과. B4b 시험 줄: `666 fixtures (452 single-block, 143 path, 21 producer chain, 18 declared C, 32 checked error (11 with a later failing PC), 42 kept C), 198 blocks, 3752 calls, 43701 checks`. 실제 생산자 사슬: `28ae` 셋(`2b736` `2b778` `e7a1c`)·`288c`(`2825c`) 각각 C Clear/Set 둘 다. 단일 block 표에서 모든 조건 분기의 두 쪽을 들어갔다(누락 0), `e74f8`의 대상 6개 모두.
- [F] 무효가 된 기존 탐침과 이전(결정 6):
  1. B4 시험 `rules()` `data[]`의 `22f7a` `2334c` `23774`(`unsupported animation machine PC` 기대) → 목록에서 빼고 stop-only 확인(`children[]`: B4 범위 밖, stop = 그 PC에서 즉시 반환)으로 옮겼다. B4 줄은 fixture·호출 수가 같고 검사 수만 `38397 → 38391`.
  2. U06 시험 `boundaries()`의 `script-jump` rollback(`e74f8`에서 `unsupported animation machine PC`) → stop-only(`final_of("script-jump").s.pc == e74f8`)로 바꿨다.
  3. U06 생성 표의 오류 행 `error-script-boundary`(합성 jump script `e7598` → 처리기 `e74f8`에서 rollback 기대): B4b 뒤에는 합성 script WORD로 `e74f8` → `28ae` …를 지나 복귀 LONG까지 성공한다. script 포인터 LONG `76(A6)`를 RAM script `10fd00`(WORD `0000 013c`: 처리기 = `10fd04 + 13c` = RAM 탐침 `10fe40`)로 바꿔 "routing 밖 처리기 대상은 전체 rollback" 기대를 F4 관례로 유지했다. U06 줄은 그대로다.
  - N25 `5eca6`(stop `4964e`), B4 생성 표의 `2986`/`28ae` 출구 행은 stop-only라 그대로 통과했다. 다른 시험·Python 시험의 변화는 없다.
- [F] 변이 목록 129개(scratch `mut/run_mut.py --check`: 모든 pattern이 실행부에 정확히 한 번)는 만들었으나 돌리지 않았다. UBSan·변이·실제 ROM 차분·V1·frame 회귀는 검증 작업자 몫이다(scratch `HANDOFF.md`).
- [U] 미확인은 위 "미확인" 절 그대로다.

## block 목록

[F] scratch `starts.txt`(SHA256 `465f91f813a6df84cb40d30417c3d586a36a14f4f653c53c2341652d98b3cbf7`)와 같다.

- **`22f7a..22fe0`(11)**: `22f7a 22f90 22fa0 22fa4 22fb4 22fc2 22fc8 22fce 22fd4 22fd8 22fde`
- **`2334c..233bc`(9)**: `2334c 23360 23376 23384 23394 2339c 233a6 233ac 233b6`
- **`233be..2347e`(20)**: `233be 233c4 233ca 233d4 233de 233e4 233ea 233ee 233f4 23400 23406 23416 2341c 2341e 2343a 2344a 2345e 23468 2346e 23478`
- **`23480..2353c`(23)**: `23480 23486 23494 2349a 234a0 234a8 234b0 234b8 234c0 234c6 234ca 234d0 234da 234e0 234ec 234f2 23502 23508 23514 23516 23528 2352c 23536`
- **`23774..237ca`(8)**: `23774 2379c 237ac 237b2 237b8 237be 237c2 237c8`
- **`23a3e..23c56`(36)**: `23a3e 23a5c 23a72 23a80 23a8a 23aa0 23ad0 23ae4 23aee 23af4 23afe 23b12 23b18 23b26 23b36 23b3e 23b44 23b56 23b84 23bb6 23bc2 23bd2 23bd8 23bda 23be4 23be8 23bf2 23bfa 23c12 23c20 23c30 23c3e 23c44 23c4a 23c4e 23c54`
- **`281ea..2822a`(3)**: `281ea 28206 28222`
- **`2825c..28490`(36)**: `2825c 28268 2826c 28276 282a8 282bc 282be 282c6 282c8 282ce 282d0 282de 282e6 282f4 282f8 2831e 28324 2832a 2834e 28366 28376 283be 283c4 283cc 283d4 28406 2840a 28456 2845c 28466 28468 28470 28478 28482 28488 2848e`
- **`2b6e6..2b7c6`(15)**: `2b6e6 2b70a 2b718 2b726 2b736 2b746 2b74a 2b774 2b778 2b788 2b78c 2b7b6 2b7b8 2b7be 2b7c2`
- **`4439e..443b8`(1)**: `4439e`
- **`49636..496a6`(12)**: `49636 4963a 49648 4964e 49658 49662 49676 49692 49694 4969e 496a0 496a4`
- **`d206a..d20b0`(3)**: `d206a d207c d20a4`
- **`e74f8..e7546`(8)**: `e74f8 e7500 e7504 e7508 e750c e751c e7534 e7544`
- **`e7996..e7a44`(13)**: `e7996 e79d0 e79f8 e79fe e7a04 e7a0e e7a14 e7a1a e7a1c e7a2c e7a30 e7a3a e7a3e`

## 검증 기록(검증 작업자 Sonnet 5.5 / medium, MS5_SEED_DIR=artifacts/stage_entry_body)

- [F] `make -j3 all test`: 종료 0, 경고 0, Assert 0, `ANIMATION_MACHINE_SOURCES` / `_HEADERS` 줄 각각 1개, Python 310개 통과. 변이 점검 뒤 hint 추가로 B4b 줄이 `671 fixtures (457 single-block, 143 path, 21 producer chain, 18 declared C, 32 checked error (11 with a later failing PC), 42 kept C), 198 blocks, 3772 calls, 43974 checks`로 바뀌었다(B4 줄 `38391 checks`, U06 줄은 그대로). 생성기 두 번 실행 시험 파일 SHA256 `5bcce4fa8904d03b…` 동일.
- [F] UBSan(`-O1 -fsanitize=undefined -fno-sanitize-recover`): hint 추가 전·후 모두 종료 0, `runtime error` 0.
- [F] 변이 129개: 첫 실행 125/129. 생존 4개 중 `23516-bls-lt`(D1.B = `e0` 경계: D1.B = `d6`이면 `d6 + (ff-d6)>>2 = e0`), `28468-byte`(D7.W 상위 byte가 다르고 하위 byte가 같은 WORD `b0`)는 시험 빈틈이라 생성기 hint에 `d5 d6 d7`(`23516`) / BYTE `12` = `d6`(`23508`) / `(8,108) (30,130)`(`28468`)를 추가해 죽였다. 최종 127/129. 나머지 둘은 동등:
  - `282c8-gt`(`BCC` → `BHI`): D1 = D0일 때만 다르고 그때 `282ce`의 `EXG D0,D1`은 같은 값끼리 교환이라 상태·C·port가 같다(`282ce`는 carry를 건드리지 않는다). 다음 stop에서 관측이 같다.
  - `283d4-limit`(`<1000` → `<=1000`): D4.W = `1000`일 때만 다르고 그때 `28406`의 `MOVE.W #1000,D4`는 값이 같아 상태·C·port가 같다.
- [F] 실제 ROM 차분(5 × 1500, seed s1 s2 s3 plain, f4 f5 FOLLOW_ANIM): 모두 rc 0, `mismatches 0`, 시작 198/198 도달, 생산자 뒤 소비자 9개 모두 비교, 2986 caller-X 클래스 0건(B4b는 `2986`을 호출하지 않음), Unknown-C 소비 0건, 홀수 주소 레지스터 0건, 해석기 dispatch 0건. native "깨끗한 stop 없음" skip은 배치당 약 ⅓~½(B4와 비슷).
- [F] V1: 첫 실행에서 spec `no node world 2b7be` / `no callee world 2b6e6`. 원인: `2b6e6`가 부르는 `8ebe`(`CMPI.B #4,1d(A6)`; `BCS 8ecc`, 아니면 `8ec8 TRAP #F`)가 routing 안(`8ebe..8ec8`)이라 native 추적이 계속 달려 `TRAP #15`(intr 47)에서 None이었다(BYTE `1d` ≥ 4가 94%). 수정: `tools/unit_fixture_specs/b4b.py`의 `node_fixtures`(진입 `2b7be` `2b7b8`)와 `callee_fixtures`(`2b6e6`)가 BYTE `1d(A6)` = `t % 6`을 hint로 준다. 수정 뒤: `b4b: carry oracle ok` (Unknown/Clear/Set = 607/9/10), `visited 198/198`, missing successors / unreachable outcomes 없음, 1723/1723 ok(error 1087, match 626, mismatch 10). 두 번 실행(v1sA, v1sB) rows `(name,digest)` 동일. 회귀: b4 1830/1830, b3c 625/625, b3a 1468/1468, b3b 1360/1360.
- [F] frame 회귀(driver `--workers 2`, controller `--declare game`, IRQ, controller `--declare demo`): natural 완료 54400/54400 ×3(natural mismatch 0, 비완료 1 = 기존 native 정지), demo 45684/45684(137 seed, mismatch 0, 비완료 137 = 기존 native 정지). B4(fc534f0) 기록과 로그를 비교하면 report SHA 외의 줄이 모두 같다: `e74f8`이 바뀐 frame은 없다.
- [U] 미확인: 위 "미확인" 절 그대로.
