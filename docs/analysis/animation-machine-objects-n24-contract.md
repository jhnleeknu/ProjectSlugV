# 객체 callback F4 N24: stage event callback `5deec`(자식 16개 생성)와 설치 callback `5e0c0` 이동 상태기계 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N24 행(200 block, `5deec..5e8c8`, callback `5deec` `5e0c0`, 경계 `6093a`, bank 1, 단독 새 seed 없음 — seed 32 33은 N24~N27 사슬이고 `dcf56`(N27)에서 먼저 멈춤; 원 범위 U34 194, U35 187)이다. 단위 형식과 규약은 N23 계약(`animation-machine-objects-n23-contract.md`, SHA256 `ad189087b33086de823cebdade045281fe057ebb7b8beb45ec0b51920d06e40b`)과 N22 계약을 따른다. 메인 작업 지시:
- flag 재계산은 선행이 유일할 때만(아니면 분기를 각 선행에 접어 넣음). N24에는 block 경계를 건너 flag를 읽는 곳이 C 소비 1곳(`5e7f6`)뿐이라 재계산이 없다.
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 설치·진입은 넣는다. 범위 밖에서만 부르는(설치하는) 범위 안 helper는 routing하지 않는다(N22/N23 선례; 결정 1).
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가). N24에는 RTS 앞 C 생산이 없다.
- 다른 단위 실행부(`animation_machine_interpreter.cpp` 포함)는 고치지 않는다. DIV 0 제수는 단위 checked 오류(N24에는 DIV가 없다).
- 계산 점프 표는 정적으로 묶고 전부 전사한다(N24에는 PC 상대 BRA.W 점프 표가 없다). `5e8a6` WORD 표는 자료 표라 live bus 읽기다(결정 3).
- ~220 block을 넘으면 나눈다(N24는 195 block이라 나누지 않는다).

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치·`MOVEA.L #imm,A0`+`JSR 28ae` 자식, 범위 밖에서 참조하는 범위 안 진입)로 정한다. Unicorn TB 분할은 시작이 아니다. 같은 flag를 쓰는 연속 Bcc는 한 block으로 묶는다(`5e0ca` `5e3dc` `5e6ac`의 `BEQ`+`BLE`).
- 결정 5(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N23 수용 관례: CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`BTST`/`ST`)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. `MOVE`/`CLR`/`CMP`/`CMPI`/`ADD`/`ADDI`/`SUB`/`SUBI`/`ASR`/`LSR`/`LSL`/`ANDI`/`TST`/`BSET` 등이 있는 block은 C를 바꾸며, 소비자가 없으므로 Unknown으로 둔다. 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N24 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`200194`와 LONG `22(A6)`이 가리키는 표)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n24`(HEAD `0da8cec` = N23까지 통합, `engine/src/animation_machine.cpp` SHA256 `4635c41ba8aa782891ec41a22f6e332c9bb6c11507e76761672d2b859750efc3`, routing 규칙 80개, `engine/src/animation_machine_interpreter.cpp` SHA256 `97abb2e1de42cf322e35fa3a66eea3ab633170143ea79e0d525e5ad4e317882f`)을 참조했다. N24 routing 범위의 짝수 PC는 기존 routing에 없다(범위 앞 `5deea`, 범위 끝 `5e8a6`도 routing 밖). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n24/n24.py`(정적 디코드, `starts.txt` SHA256 `5f7d3b909613b6c2c9abd1eadf9af30de690a6da092bb422e0968ff0838a55ed`)와 `cls24.py`(분류)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N24 = 195 block**(routing 범위 1개 `5deec..5e8a6`, 코드 2,490바이트, 짝수 PC 1,245, 내부 1,050). 진입 2개(`5deec`, 범위 안 설치 `5e0c0`)에서 분기·fall-through를 끝까지 따라간 정적 closure이며, 범위 안 명령 523개를 모두 덮는다(미도달 0). 재범위 200과의 차이는 결정 1이다.
- [F] 진입:
  - stage event callback `5deec`: 고정 ROM LONG `e9048`(stage event 표, N23 `c3a7c`의 `e8ff0`과 같은 꼴). 범위 밖 다른 참조 없음(`5e000`/`5e800`/`5e0ea`와 같은 값의 LONG은 좌표 자료 `2772a` `2e1b8` `d7286` 등이다).
  - 범위 안 설치: `5e0c0`(`5e0ba MOVE.L #5e0c0,(A6)`, fall-through).
- [F] **경계(실행부 없음, 현재 routing 밖)**: `6093a`(`5e80c MOVE.L #6093a,(A6)` 설치 값, `5e846` `5e878` `5e8a0 BRA.W 6093a` tail). `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다. [F] 재범위 N25~N35 어느 범위에도 없고 400 frame 안에 실행되지 않는다(아래 자연 도달).
- [F] **다른 실행부로 가는 callee**: `8ebe`(U02), `16ef0` `4a496`(U14), `43e34` `8ff4`(cleanup), `28ae`(fade_card), `49f8c` `49fc6`(interpreter), `490ba`(U12), `3af8`(sound), `49a58`(stage_area), `43ea4`(U04), `4b54e`(U01). 모두 기존 실행부의 block 시작이다. 레지스터 간접 호출은 없다.
- [F] **범위 밖 `28ae` 자식 값(실행 PC가 아님)** 16개: `5e8c8` `5eac2` `5ead4` `5efe6` `5eff8`(N25), `5f24a` `5f25c` `5f760` `5f76c` `5fb0e` `5fb20`(N26), `5fd24` `5fd36` `60008` `6031e` `6041e`(N27). 자료 주소 인자: `60c0a`(`490ba` A0), `60c9e`(`49f8c` A1).
- [F] **carry**: 소비 1 block(`5e7f6 BCC.W 5e7fe`, U01 `4b54e`의 C), known 생산 0, FLOW_ONLY 33(소비 1 포함), Unknown 162. 33 + 162 = 195.
- [F] N/Z 재계산 없음. X·DIVx/MULx·PC 상대 점프 표·레지스터 간접 점프·TRAP·I/O port 쓰기·bank 변경 없음. `ASR.L #2`/`#3` 28곳은 부호 bit 채움을 명시 계산한다.
- [F] 스택: JSR 복귀 LONG만(push/pop 없음). 끝 `5e8a4 RTS`.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `seen24.py`): 두 기록 모두 seed 32 33만 N24 범위를 실행한다. callback 실행 수(seed별): `5deec` 1, `5e0c0` 81(같은 seed의 N25 `5e940` 81). 실행된 범위 안 경로는 `5deec`…`5e0a4`, `5e0c0` `5e0ca` `5e0e2`(TB `5e0de`) `5e108` `5e114` `5e120` `5e12a` `5e14a` `5e156` `5e20a`, 꼬리 `5e7dc`…`5e7fe` `5e8a4`(BYTE `76` = 0 상태만)다. 범위 밖 `5e8b0` `5e8b6` `5e8be`(결정 1)도 같은 seed가 `5e940` 아래에서 실행한다. `6093a` 경로는 실행되지 않는다.
- [F] 기준(`0da8cec`)에서 seed 32 33은 frame 0 callback `dcf56`(N27 범위)에서 먼저 멈춘다. [I] N24만으로는 RNG·base 완주 수가 늘지 않는다(재범위 표의 N24 행 132/133 그대로). 검증은 실제 ROM 차분과 fixture가 맡는다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 195 block(재범위 200과 차이) — `5e8b0..5e8c8` 제외.** [F] 재범위 N24 행 `5deec..5e8c8`의 끝 26바이트는 N24 진입에서 닿지 않는다.
   - `5e8a6..5e8b0`: WORD 표 5개(`0032 0001 0032 0005 ffff`, SHA256 `46c610cd66f00c267778b1673ed785d6e7750da2723c088f2886edf0a828c52f`), `5e1d2`/`5e4ec`의 자료 표(결정 3). 코드가 아니다.
   - `5e8b0..5e8c8`(4 block `5e8b0` `5e8b6` `5e8be` `5e8c0`: `JSR 43e34; TST.B 79(A6); BNE; RTS; JSR 49fc6; RTS`): N24 안에서는 참조 0. 범위 밖 N25~N27 코드가 설치·tail로만 쓴다: `5ea1a` `5ea28` `5ebf0` `5f34e` `5f85a` `5fc6a` `5fe3a` `6012e` `603f2` `604e8 MOVE.L #5e8b0,(A6)`, `5ea34` `5ebf6 BRA.W 5e8b0`. seed 32 33이 N25 callback `5e940` 아래에서 실행한다(자연 도달).
   - 메인 지시("범위 밖에서만 부르는 범위 안 helper는 routing하지 않음", N22 결정 8·N23 결정 1 선례)대로 **뺐다**. [I] 재범위 N25 범위(`5e8c8..`)에도 들어 있지 않아 지금은 어느 단위에도 없다. 권고: N25(설치 `5ea1a` `5ea28`·tail `5ea34`를 가진 단위, 자연 실행 callback `5e940`)가 `5e8b0..5e8c8` 4 block을 함께 넣는다. 넣지 않으면 seed 32 33 사슬(N24~N27)이 `5e8b0`에서 멈춘다.
2. **경계 `6093a`.** [F] `5e80c MOVE.L #6093a,(A6)`(설치 값, 자료)와 `5e846`/`5e878`/`5e8a0 BRA.W 6093a`(tail). `6093a..60a06`은 원 범위 U34/U35에 있었으나 재범위 N25~N35 어느 행에도 없다(400 frame 안 미실행). N24는 BRA로 PC = `6093a`만 두고 멈춘다(routing 밖: stop이면 멈춤, 아니면 `unsupported animation machine PC` rollback). [U] `6093a` 계열의 소유 단위는 미정이다(고아 설치 callback 정리 단계 후보).
3. **`5e8a6` WORD 표(자료, live bus).** [F] `5e1d2`/`5e4ec`: A0 = `5e8a6`, `D0` = BYTE `76`(0 확장), `D0.W` = 2·`D0.W`, `D0.W` = WORD(A0 + sext(`D0.W`)) = WORD(`5e8a6` + 2·BYTE `76`). 색인 범위는 0..510(표 밖 `5eaa4`까지; 고정 ROM)이고 원본처럼 색인 검사가 없다. 범위 안 경로에서는 바로 앞 block이 BYTE `76`을 1(`5e180`) 또는 3(`5e484`)으로 쓰므로 ROM 값은 `0001`(→ LONG(`22` 표 + 4))·`0005`(→ +`14`)다. 점프 표가 아니므로 전사하지 않고 live bus(`am_read`)로 읽는다. 결과 `ffff`이면 BYTE `79` = 0을 남기고 `5e20a`/`5e524`로 간다.
4. **`5e7f6` 소비(U01 `4b54e`).** [F] `5e7f0 JSR 4b54e`의 C를 `5e7f6 BCC.W 5e7fe`가 읽는다. U01 실행부가 known C를 낸다(`4b548 ANDI` Clear, `4b532 ORI` Set, `4b6be` `MOVE.B` 뒤 Clear(`5e(A6)` = 0), `4b6de ORI` Set). `5e0ca`/`5e3dc`가 LONG `56(A6)` = 0을 쓰므로 범위 안 경로에서 `4b54e`는 `4b6be`로 가고 C = (BYTE `5e` ≠ 0)이다. Unknown C면 `objects n24 caller requires known carry`(상태 보존). 실제 생산자를 따라간 native 분기로 확인한다(검증 기록).
5. **bank 읽기.** [F] `5df12 MOVE.L 200194.l,22(A6)`(id `18b`, banked LONG; 재범위 "bank 1"). 이어서 `5e06e`(LONG `c8`), `5e1ee`/`5e508`(LONG(A1 + sext(4·표 값 WORD))), `5e830`(`dc`), `5e862`(`d8`), `5e88a`(`e4`)가 LONG `22`를 기준으로 LONG을 읽는다(그 기준이 bank window를 가리키면 bank 읽기). 모두 live bus(현재 PVC bank 모델)다.
6. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n24.cpp`의 `animation_objects_n24_block`. 오류는 `unsupported animation objects n24 PC`(내부 PC), `objects n24 caller requires known carry`(소비 1 block). 메인 지시와 같다.
7. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`·`engine/src`의 16진 토큰 중 N24 routing 범위 짝수 PC와 같은 것은 없다(digest 값 일부 문자열 일치만 있음: `animation_machine_objects_n16_test.cpp` `animation_machine_stage_catalog_test.cpp` `animation_machine_motion_walk_test.cpp`). 새 rollback 탐침은 RAM `10fexx`만 쓴다.

## 원본 바이트 근거

[F] N24 코드 1 범위 2,490바이트(짝수 PC 1,245개, 시작 195, 내부 1,050). SHA256 `4159460b9f57bcb30cdc991183677690915f74fcd882e649bee7262ea24d1eda`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `5deec..5e8a6` | 2,490 | `4159460b9f57bcb30cdc991183677690915f74fcd882e649bee7262ea24d1eda` | 195 |

- [F] 범위 이웃: `5deec` 앞 `..5deec`(자료 `0400 0400`/`0600 0600` WORD 열, 코드 아님), `5e8a6..5e8b0`(WORD 표, 결정 3), `5e8b0..5e8c8`(결정 1, 범위 밖 설치 callback), `5e8c8..`(N25 `28ae` 자식 `5e8c8`).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(A6)·`(An,Dn.W)`는 부호 확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다(`MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`는 LONG 전체). 모든 비교·`TST`·산술과 그 Bcc는 같은 block 안에 있다(예외: 결정 4의 `5e7f6`). `BLE`/`BGE`/`BEQ`는 같은 block의 `CMP`/`CMPI`(부호 있는 비교: `BLE` = 대상 ≤ 원천, `BGE` = 대상 ≥ 원천; `CMP.W 86(A6),D0`은 `D0.W` 대 `86.W`)다.

**stage event callback `5deec`(고정 ROM LONG `e9048`; 초기화, `28ae` 자식 16개, 끝 `5e0ba` 설치 `5e0c0` fall-through) 26**
- `5deec`: `MOVE.W #d48, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5defa`: `BSET.B #6, 15(a6); MOVE.W #800, 68(a6); MOVE.W #800, 1e(a6); JSR 16ef0.l`
- `5df12`: `MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); BSET.B #0, 15(a6); MOVE.W #190, 2e(a6); MOVE.W #0, 32(a6); JSR 43e34.l`
- `5df38`: `ST.B 79(a6); CLR.B 63(a6); CLR.B 63(a6); MOVE.B #0, 76(a6); MOVE.B #0, 77(a6); MOVEA.L #5e8c8, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5df60`: `MOVEA.L #5eac2, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5df70`: `MOVEA.L #5ead4, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5df80`: `MOVEA.L #5efe6, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5df90`: `MOVEA.L #5eff8, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5dfa0`: `MOVEA.L #5f24a, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5dfb0`: `MOVEA.L #5f25c, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5dfc0`: `MOVEA.L #5f760, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5dfd0`: `MOVEA.L #5f76c, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5dfe0`: `MOVEA.L #5fb0e, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5dff0`: `MOVEA.L #5fb20, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5e000`: `MOVEA.L #5fd24, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5e010`: `MOVEA.L #5fd36, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5e020`: `MOVEA.L #60008, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5e030`: `MOVEA.L #6031e, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5e040`: `MOVEA.L #6041e, a0; MOVE.W #0, d0; JSR 28ae.l`
- `5e050`: `JSR 8ff4.l` — FLOW
- `5e056`: `MOVE.W #d4b, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5e064`: `MOVE.W #d56, d0; JSR 4a496.l`
- `5e06e`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L c8(a1), a1; JSR 49f8c.l`
- `5e084`: `MOVE.B #7, 88(a6); LEA.L 60c0a.l, a0; JSR 490ba.l`
- `5e096`: `MOVE.W d0, 54(a6); MOVE.W #74e, d0; JSR 3af8.l`
- `5e0a4`: `MOVE.L #0, 36(a6); MOVE.L #0, 3a(a6); MOVE.W #f0, 86(a6); MOVE.L #5e0c0, (a6)` (→`5e0c0`)

**설치 callback `5e0c0`(BYTE `76` 상태 0~3, BYTE `77` 하위 상태 0~4의 이동 상태기계) 149**
- `5e0c0`: `CMPI.B #0, 76(a6); BNE.W 5e20e` (→`5e0ca`)
- `5e0ca`: `MOVE.L #0, 56(a6); MOVE.W 32(a6), d0; CMP.W 86(a6), d0; BEQ.W 5e13c; BLE.W 5e108` (→`5e0e2`)
- `5e0e2`: `CMPI.L #fffe0000, 3a(a6); BLE.W 5e0fa` (→`5e0ee`)
- `5e0ee`: `ADDI.L #ffffc000, 3a(a6); BRA.W 5e104`
- `5e0fa`: `MOVE.L 3a(a6), d0; ASR.L #3, d0; SUB.L d0, 3a(a6)` (→`5e104`)
- `5e104`: `BRA.W 5e12a` — FLOW
- `5e108`: `CMPI.L #20000, 3a(a6); BGE.W 5e120` (→`5e114`)
- `5e114`: `ADDI.L #4000, 3a(a6); BRA.W 5e12a`
- `5e120`: `MOVE.L 3a(a6), d0; ASR.L #3, d0; SUB.L d0, 3a(a6)` (→`5e12a`)
- `5e12a`: `MOVE.W 46(a6), d0; SUBI.W #100, d0; LSR.W #4, d0; ANDI.B #f, d0; MOVE.B d0, 88(a6)` (→`5e13c`)
- `5e13c`: `MOVE.L 36(a6), d0; CMPI.L #fffb0000, d0; BLE.W 5e156` (→`5e14a`)
- `5e14a`: `ASR.L #3, d0; SUBI.L #1000, d0; ADD.L d0, 36(a6)` (→`5e156`)
- `5e156`: `CMPI.W #ffb0, 2e(a6); BGE.W 5e20a` (→`5e160`)
- `5e160`: `TST.B 89(a6); BNE.W 5e176` (→`5e168`)
- `5e168`: `ST.B 89(a6); MOVE.W #19d4, d0; JSR 3af8.l`
- `5e176`: `MOVE.W #750, d0; JSR 3af8.l`
- `5e180`: `MOVE.B #1, 76(a6); MOVE.B #0, 77(a6); MOVE.L #4000, 36(a6); MOVE.L #0, 3a(a6); MOVE.W #ff80, 2e(a6); MOVE.W #84, 32(a6); MOVE.B #ff, 12(a6); MOVE.B #ff, 13(a6); JSR 8ff4.l`
- `5e1ba`: `MOVE.W #d4b, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5e1c8`: `MOVE.W #d56, d0; JSR 4a496.l`
- `5e1d2`: `LEA.L 5e8a6(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 5e20a` (→`5e1ee`)
- `5e1ee`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5e20a`: `BRA.W 5e7dc` — FLOW
- `5e20e`: `CMPI.B #1, 76(a6); BNE.W 5e3d2` (→`5e218`)
- `5e218`: `CMPI.B #0, 77(a6); BNE.W 5e280` (→`5e222`)
- `5e222`: `CMPI.W #40, 2e(a6); BGE.W 5e24a` (→`5e22c`)
- `5e22c`: `MOVE.L 36(a6), d0; CMPI.L #60000, d0; BGE.W 5e246` (→`5e23a`)
- `5e23a`: `ASR.L #3, d0; ADDI.L #1000, d0; ADD.L d0, 36(a6)` (→`5e246`)
- `5e246`: `BRA.W 5e27c` — FLOW
- `5e24a`: `MOVE.L 36(a6), d0; ASR.L #2, d0; ADDI.L #1000, d0; SUB.L d0, 36(a6); CLR.B 62(a6); JSR 49a58.l`
- `5e264`: `ANDI.B #3, d0; BNE.W 5e276` (→`5e26c`)
- `5e26c`: `MOVE.B #1, 77(a6); BRA.W 5e27c`
- `5e276`: `MOVE.B #2, 77(a6)` (→`5e27c`)
- `5e27c`: `BRA.W 5e7dc` — FLOW
- `5e280`: `CMPI.B #1, 77(a6); BNE.W 5e2e2` (→`5e28a`)
- `5e28a`: `CMPI.W #20, 2e(a6); BGE.W 5e2b2` (→`5e294`)
- `5e294`: `MOVE.L 36(a6), d0; CMPI.L #60000, d0; BGE.W 5e2ae` (→`5e2a2`)
- `5e2a2`: `ASR.L #3, d0; ADDI.L #1000, d0; ADD.L d0, 36(a6)` (→`5e2ae`)
- `5e2ae`: `BRA.W 5e2c2` — FLOW
- `5e2b2`: `MOVE.L 36(a6), d0; ASR.L #2, d0; ADDI.L #1000, d0; SUB.L d0, 36(a6)` (→`5e2c2`)
- `5e2c2`: `TST.B 62(a6); BEQ.W 5e2de` (→`5e2ca`)
- `5e2ca`: `CLR.B 62(a6); MOVE.W #74f, d0; JSR 3af8.l`
- `5e2d8`: `MOVE.B #3, 77(a6)` (→`5e2de`)
- `5e2de`: `BRA.W 5e7dc` — FLOW
- `5e2e2`: `CMPI.B #2, 77(a6); BNE.W 5e344` (→`5e2ec`)
- `5e2ec`: `CMPI.W #20, 2e(a6); BGE.W 5e314` (→`5e2f6`)
- `5e2f6`: `MOVE.L 36(a6), d0; CMPI.L #60000, d0; BGE.W 5e310` (→`5e304`)
- `5e304`: `ASR.L #3, d0; ADDI.L #1000, d0; ADD.L d0, 36(a6)` (→`5e310`)
- `5e310`: `BRA.W 5e324` — FLOW
- `5e314`: `MOVE.L 36(a6), d0; ASR.L #2, d0; ADDI.L #1000, d0; SUB.L d0, 36(a6)` (→`5e324`)
- `5e324`: `TST.B 62(a6); BEQ.W 5e340` (→`5e32c`)
- `5e32c`: `CLR.B 62(a6); MOVE.W #74f, d0; JSR 3af8.l`
- `5e33a`: `MOVE.B #3, 77(a6)` (→`5e340`)
- `5e340`: `BRA.W 5e7dc` — FLOW
- `5e344`: `CMPI.B #3, 77(a6); BNE.W 5e3ce` (→`5e34e`)
- `5e34e`: `MOVE.L 36(a6), d0; CMPI.L #fffa0000, d0; BLE.W 5e368` (→`5e35c`)
- `5e35c`: `ASR.L #3, d0; ADDI.L #fffff000, d0; ADD.L d0, 36(a6)` (→`5e368`)
- `5e368`: `CMPI.W #ffa0, 2e(a6); BGE.W 5e3ca` (→`5e372`)
- `5e372`: `MOVE.W #74e, d0; JSR 3af8.l`
- `5e37c`: `MOVE.B #2, 76(a6); MOVE.B #0, 77(a6); MOVE.L #8000, 36(a6); MOVE.W #ffa0, 2e(a6); MOVE.W #f0, 32(a6); JSR 8ff4.l`
- `5e3a2`: `MOVE.W #d48, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5e3b0`: `MOVE.W #d56, d0; JSR 4a496.l`
- `5e3ba`: `MOVEA.L #60c9e, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `5e3ca`: `BRA.W 5e7dc` — FLOW
- `5e3ce`: `BRA.W 5e7dc` — FLOW
- `5e3d2`: `CMPI.B #2, 76(a6); BNE.W 5e528` (→`5e3dc`)
- `5e3dc`: `MOVE.L #0, 56(a6); CMPI.W #0, 32(a6); BEQ.W 5e43a; BLE.W 5e418` (→`5e3f2`)
- `5e3f2`: `CMPI.L #fffe0000, 3a(a6); BLE.W 5e40a` (→`5e3fe`)
- `5e3fe`: `ADDI.L #ffffc000, 3a(a6); BRA.W 5e414`
- `5e40a`: `MOVE.L 3a(a6), d0; ASR.L #3, d0; SUB.L d0, 3a(a6)` (→`5e414`)
- `5e414`: `BRA.W 5e43a` — FLOW
- `5e418`: `CMPI.L #20000, 3a(a6); BGE.W 5e430` (→`5e424`)
- `5e424`: `ADDI.L #4000, 3a(a6); BRA.W 5e43a`
- `5e430`: `MOVE.L 3a(a6), d0; ASR.L #3, d0; SUB.L d0, 3a(a6)` (→`5e43a`)
- `5e43a`: `MOVE.W 46(a6), d0; SUBI.W #100, d0; LSR.W #4, d0; ANDI.B #f, d0; MOVE.B d0, 88(a6); MOVE.L 36(a6), d0; CMPI.L #50000, d0; BGE.W 5e466` (→`5e45a`)
- `5e45a`: `ASR.L #3, d0; ADDI.L #1000, d0; ADD.L d0, 36(a6)` (→`5e466`)
- `5e466`: `CMPI.W #190, 2e(a6); BLE.W 5e524` (→`5e470`)
- `5e470`: `MOVE.W #750, d0; JSR 3af8.l`
- `5e47a`: `MOVE.W #736, d0; JSR 3af8.l`
- `5e484`: `MOVE.B #3, 76(a6); MOVE.B #0, 77(a6); JSR 49a58.l`
- `5e496`: `ANDI.W #1, d0; BNE.W 5e4a8` (→`5e49e`)
- `5e49e`: `MOVE.W #0, 86(a6); BRA.W 5e4ae`
- `5e4a8`: `MOVE.W #100, 86(a6)` (→`5e4ae`)
- `5e4ae`: `MOVE.L #ffff8000, 36(a6); MOVE.W #1b0, 2e(a6); MOVE.W #84, 32(a6); MOVE.B #ff, 12(a6); MOVE.B #ff, 13(a6); JSR 8ff4.l`
- `5e4d4`: `MOVE.W #d4b, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5e4e2`: `MOVE.W #d56, d0; JSR 4a496.l`
- `5e4ec`: `LEA.L 5e8a6(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 5e524` (→`5e508`)
- `5e508`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5e524`: `BRA.W 5e7dc` — FLOW
- `5e528`: `CMPI.B #3, 76(a6); BNE.W 5e7dc` (→`5e532`)
- `5e532`: `CMPI.B #0, 77(a6); BNE.W 5e582` (→`5e53c`)
- `5e53c`: `MOVE.L 3a(a6), d0; ASR.L #3, d0; SUB.L d0, 3a(a6); CMPI.W #f0, 2e(a6); BLE.W 5e578` (→`5e550`)
- `5e550`: `MOVE.L 36(a6), d0; CMPI.L #fffa0000, d0; BLE.W 5e56e` (→`5e55e`)
- `5e55e`: `ASR.L #3, d0; ADDI.L #fffff000, d0; ADD.L d0, 36(a6); BRA.W 5e574`
- `5e56e`: `ASR.L #3, d0; SUB.L d0, 36(a6)` (→`5e574`)
- `5e574`: `BRA.W 5e57e` — FLOW
- `5e578`: `MOVE.B #1, 77(a6)` (→`5e57e`)
- `5e57e`: `BRA.W 5e7dc` — FLOW
- `5e582`: `CMPI.B #1, 77(a6); BNE.W 5e5f0` (→`5e58c`)
- `5e58c`: `MOVE.L 3a(a6), d0; ASR.L #3, d0; SUB.L d0, 3a(a6); CMPI.W #f0, 2e(a6); BLE.W 5e5c0` (→`5e5a0`)
- `5e5a0`: `MOVE.L 36(a6), d0; CMPI.L #fffa0000, d0; BLE.W 5e5bc` (→`5e5ae`)
- `5e5ae`: `ASR.L #3, d0; SUB.L d0, 36(a6); ADDI.L #fffff000, 36(a6)` (→`5e5bc`)
- `5e5bc`: `BRA.W 5e5da` — FLOW
- `5e5c0`: `MOVE.L 36(a6), d0; CMPI.L #60000, d0; BGE.W 5e5da` (→`5e5ce`)
- `5e5ce`: `ASR.L #3, d0; ADDI.L #fffff000, d0; SUB.L d0, 36(a6)` (→`5e5da`)
- `5e5da`: `TST.B 62(a6); BEQ.W 5e5ec` (→`5e5e2`)
- `5e5e2`: `CLR.B 62(a6); MOVE.B #2, 77(a6)` (→`5e5ec`)
- `5e5ec`: `BRA.W 5e7dc` — FLOW
- `5e5f0`: `CMPI.B #2, 77(a6); BNE.W 5e65e` (→`5e5fa`)
- `5e5fa`: `MOVE.L 3a(a6), d0; ASR.L #3, d0; SUB.L d0, 3a(a6); CMPI.W #100, 2e(a6); BLE.W 5e62e` (→`5e60e`)
- `5e60e`: `MOVE.L 36(a6), d0; CMPI.L #fffa0000, d0; BLE.W 5e62a` (→`5e61c`)
- `5e61c`: `ASR.L #3, d0; SUB.L d0, 36(a6); ADDI.L #fffff000, 36(a6)` (→`5e62a`)
- `5e62a`: `BRA.W 5e648` — FLOW
- `5e62e`: `MOVE.L 36(a6), d0; CMPI.L #60000, d0; BGE.W 5e648` (→`5e63c`)
- `5e63c`: `ASR.L #3, d0; ADDI.L #fffff000, d0; SUB.L d0, 36(a6)` (→`5e648`)
- `5e648`: `TST.B 62(a6); BEQ.W 5e65a` (→`5e650`)
- `5e650`: `CLR.B 62(a6); MOVE.B #3, 77(a6)` (→`5e65a`)
- `5e65a`: `BRA.W 5e7dc` — FLOW
- `5e65e`: `CMPI.B #3, 77(a6); BNE.W 5e72c` (→`5e668`)
- `5e668`: `CMPI.W #100, 2e(a6); BLE.W 5e692` (→`5e672`)
- `5e672`: `MOVE.L 36(a6), d0; CMPI.L #fffa0000, d0; BLE.W 5e68e` (→`5e680`)
- `5e680`: `ASR.L #3, d0; SUB.L d0, 36(a6); ADDI.L #fffff000, 36(a6)` (→`5e68e`)
- `5e68e`: `BRA.W 5e6ac` — FLOW
- `5e692`: `MOVE.L 36(a6), d0; CMPI.L #60000, d0; BGE.W 5e6ac` (→`5e6a0`)
- `5e6a0`: `ASR.L #3, d0; ADDI.L #fffff000, d0; SUB.L d0, 36(a6)` (→`5e6ac`)
- `5e6ac`: `MOVE.W 32(a6), d0; CMP.W 86(a6), d0; BEQ.W 5e704; BLE.W 5e6e2` (→`5e6bc`)
- `5e6bc`: `CMPI.L #fffc8000, 3a(a6); BLE.W 5e6d4` (→`5e6c8`)
- `5e6c8`: `ADDI.L #ffff0000, 3a(a6); BRA.W 5e6de`
- `5e6d4`: `MOVE.L 3a(a6), d0; ASR.L #2, d0; SUB.L d0, 3a(a6)` (→`5e6de`)
- `5e6de`: `BRA.W 5e704` — FLOW
- `5e6e2`: `CMPI.L #38000, 3a(a6); BGE.W 5e6fa` (→`5e6ee`)
- `5e6ee`: `ADDI.L #10000, 3a(a6); BRA.W 5e704`
- `5e6fa`: `MOVE.L 3a(a6), d0; ASR.L #2, d0; SUB.L d0, 3a(a6)` (→`5e704`)
- `5e704`: `TST.B 62(a6); BEQ.W 5e728` (→`5e70c`)
- `5e70c`: `CLR.B 62(a6); MOVE.W #74f, d0; JSR 3af8.l`
- `5e71a`: `MOVE.B #4, 77(a6); MOVE.L #8000, 36(a6)` (→`5e728`)
- `5e728`: `BRA.W 5e7dc` — FLOW
- `5e72c`: `CMPI.B #4, 77(a6); BNE.W 5e7d8` (→`5e736`)
- `5e736`: `MOVE.L 3a(a6), d0; ASR.L #3, d0; SUB.L d0, 3a(a6); MOVE.L 36(a6), d0; CMPI.L #60000, d0; BGE.W 5e75a` (→`5e74e`)
- `5e74e`: `ASR.L #3, d0; ADDI.L #1000, d0; ADD.L d0, 36(a6)` (→`5e75a`)
- `5e75a`: `CMPI.W #190, 2e(a6); BLE.W 5e7d8` (→`5e764`)
- `5e764`: `MOVE.W #74e, d0; JSR 3af8.l`
- `5e76e`: `MOVE.B #0, 76(a6); MOVE.B #0, 77(a6); MOVE.L #ffffc000, 36(a6); MOVE.L #0, 3a(a6); MOVE.W #190, 2e(a6); CMPI.W #80, 32(a6); BLE.W 5e7a4` (→`5e79a`)
- `5e79a`: `MOVE.W #0, 86(a6); BRA.W 5e7aa`
- `5e7a4`: `MOVE.W #f0, 86(a6)` (→`5e7aa`)
- `5e7aa`: `JSR 8ff4.l` — FLOW
- `5e7b0`: `MOVE.W #d48, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5e7be`: `MOVE.W #d56, d0; JSR 4a496.l`
- `5e7c8`: `MOVEA.L #60c9e, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `5e7d8`: `BRA.W 5e7dc` — FLOW

**공통 꼬리 `5e7dc`(`43ea4`, `49fc6`, `4b54e` 화면 판정, BYTE `61` bit 7 → 설치 `6093a`·`BRA.W 6093a`; 아니면 RTS) 20**
- `5e7dc`: `JSR 43ea4.l` — FLOW
- `5e7e2`: `TST.B 79(a6); BEQ.W 5e7f0` (→`5e7ea`)
- `5e7ea`: `JSR 49fc6.l` — FLOW
- `5e7f0`: `JSR 4b54e.l` — FLOW
- `5e7f6`: `BCC.W 5e7fe` (→`5e7fa`) — C 소비, FLOW
- `5e7fa`: `CLR.B 5e(a6)` (→`5e7fe`)
- `5e7fe`: `BTST.B #7, 61(a6); BEQ.W 5e8a4` (→`5e808`) — FLOW
- `5e808`: `ST.B 63(a6); MOVE.L #6093a, (a6); JSR 8ff4.l`
- `5e818`: `CMPI.B #1, 76(a6); BNE.W 5e84a` (→`5e822`)
- `5e822`: `MOVE.W #d4b, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5e830`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L dc(a1), a1; JSR 49f8c.l`
- `5e846`: `BRA.W 6093a` — FLOW
- `5e84a`: `CMPI.B #3, 76(a6); BNE.W 5e87c` (→`5e854`)
- `5e854`: `MOVE.W #d4b, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5e862`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L d8(a1), a1; JSR 49f8c.l`
- `5e878`: `BRA.W 6093a` — FLOW
- `5e87c`: `MOVE.W #d4d, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5e88a`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L e4(a1), a1; JSR 49f8c.l`
- `5e8a0`: `BRA.W 6093a` — FLOW
- `5e8a4`: `RTS` — FLOW

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다; LONG 산술은 32 bit 2의 보수, `ASR.L #n`은 부호 bit 채움):
  - `5deec`(stage event callback): `D0.W` = `d48`, `D1.B` = 0, `JSR 8ebe`. `5defa`: BYTE `15` |= `40`(`BSET.B #6`, 읽고 쓰기), `68.W` = `1e.W` = `800`, `JSR 16ef0`. `5df12`: `20.W` = `18b`, LONG `22` = banked LONG `200194`, BYTE `15` |= 1, `2e.W` = `190`, `32.W` = 0, `JSR 43e34`. `5df38`: BYTE `79` = `ff`, BYTE `63` = 0(두 번), BYTE `76` = BYTE `77` = 0, A0 = `5e8c8`, `D0.W` = 0, `JSR 28ae`. `5df60`~`5e040`: A0 = 자식 값(요약 순서), `D0.W` = 0, `JSR 28ae`(15번; 자리 없음이어도 C는 읽지 않는다). `5e050`: `JSR 8ff4`. `5e056`: `D0.W` = `d4b`, `D1.B` = 0, `JSR 8ebe`. `5e064`: `D0.W` = `d56`, `JSR 4a496`. `5e06e`: `D0.W` = `100`, A0 = A6 + `26`, A1 = LONG `22`, A1 = LONG(A1 + `c8`), `JSR 49f8c`. `5e084`: BYTE `88` = 7, A0 = `60c0a`, `JSR 490ba`. `5e096`: `54.W` = `D0.W`, `D0.W` = `74e`, `JSR 3af8`. `5e0a4`: LONG `36` = LONG `3a` = 0, `86.W` = `f0`, `(A6)` = `5e0c0`, fall-through.
  - `5e0c0`(설치): BYTE `76` ≠ 0이면 `5e20e`. 상태 0(`5e0ca`): LONG `56` = 0, `D0.W` = `32.W`; `D0.W` = `86.W`이면 `5e13c`, `D0.W` < `86.W`(부호)면 `5e108`, 크면 `5e0e2`. `5e0e2`: LONG `3a` ≤ `fffe0000`(부호)이면 `5e0fa`; 아니면 LONG `3a` += `ffffc000`(`5e0ee`). `5e0fa`/`5e120`: `D0` = LONG `3a`, `D0` = `D0` 산술 >> 3, LONG `3a` −= `D0`. `5e108`: LONG `3a` ≥ `20000`이면 `5e120`; 아니면 LONG `3a` += `4000`(`5e114`). `5e12a`: `D0.W` = `46.W`, `D0.W` −= `100`, `D0.W` 논리 >> 4, `D0.B` &= `f`, BYTE `88` = `D0.B`. `5e13c`: `D0` = LONG `36`; ≤ `fffb0000`이면 `5e156`; `5e14a`: `D0` = (`D0` 산술 >> 3) − `1000`, LONG `36` += `D0`. `5e156`: `2e.W` ≥ `ffb0`(부호)이면 `5e20a`. `5e160`: BYTE `89` ≠ 0이면 `5e176`; `5e168`: BYTE `89` = `ff`, `D0.W` = `19d4`, `JSR 3af8`. `5e176`: `D0.W` = `750`, `JSR 3af8`. `5e180`: BYTE `76` = 1, BYTE `77` = 0, LONG `36` = `4000`, LONG `3a` = 0, `2e.W` = `ff80`, `32.W` = `84`, BYTE `12` = BYTE `13` = `ff`, `JSR 8ff4`. `5e1ba`: `8ebe`(`D0.W` = `d4b`, `D1.B` = 0). `5e1c8`: `4a496`(`D0.W` = `d56`). `5e1d2`/`5e4ec`: 결정 3의 WORD, BYTE `79` = 0, `ffff`이면 `5e20a`/`5e524`. `5e1ee`/`5e508`: BYTE `79` = `ff`, `D0.W` = (`D0.W` << 2) & `ffff`, A1 = LONG `22`, A1 = LONG(A1 + sext(`D0.W`)), `D0.W` = `100`, A0 = A6 + `26`, `JSR 49f8c`.
  - 상태 1(`5e20e`: BYTE `76` = 1이 아니면 `5e3d2`): BYTE `77` = 0(`5e218`): `2e.W` ≥ `40`이면 `5e24a`; 아니면 `D0` = LONG `36`, ≥ `60000`이면 끝, 아니면 LONG `36` += (`D0` 산술 >> 3) + `1000`(`5e23a`). `5e24a`: `D0` = LONG `36`, LONG `36` −= (`D0` 산술 >> 2) + `1000`, BYTE `62` = 0, `JSR 49a58`; `5e264`: `D0.B` &= 3; 0이면 BYTE `77` = 1, 아니면 2. BYTE `77` = 1(`5e280`, 문턱 `20`)·2(`5e2e2`, 문턱 `20`): `2e.W` ≥ 문턱이면 LONG `36` −= (LONG `36` 산술 >> 2) + `1000`, 아니면 LONG `36` < `60000`일 때 += (산술 >> 3) + `1000`; 그 뒤 BYTE `62` ≠ 0이면 BYTE `62` = 0, `D0.W` = `74f`, `JSR 3af8`, BYTE `77` = 3. BYTE `77` = 3(`5e344`): `D0` = LONG `36`; > `fffa0000`이면 LONG `36` += (`D0` 산술 >> 3) + `fffff000`(`5e35c`); `2e.W` ≥ `ffa0`이면 끝; 아니면 `3af8`(`74e`), BYTE `76` = 2, BYTE `77` = 0, LONG `36` = `8000`, `2e.W` = `ffa0`, `32.W` = `f0`, `JSR 8ff4`, `8ebe`(`d48`, 0), `4a496`(`d56`), A1 = `60c9e`, `D0.W` = `100`, `JSR 49f8c`(A0는 호출 전 값 그대로). 다른 BYTE `77`이면 `5e3ce BRA 5e7dc`.
  - 상태 2(`5e3d2`: BYTE `76` = 2가 아니면 `5e528`): LONG `56` = 0; `32.W` = 0이면 `5e43a`, < 0이면 `5e418`(LONG `3a` ≥ `20000`이면 −= 산술 >> 3, 아니면 += `4000`), > 0이면 `5e3f2`(LONG `3a` ≤ `fffe0000`이면 −= 산술 >> 3, 아니면 += `ffffc000`). `5e43a`: BYTE `88` = ((`46.W` − `100`) 논리 >> 4) & `f`(BYTE), `D0` = LONG `36`; < `50000`이면 LONG `36` += (산술 >> 3) + `1000`(`5e45a`). `5e466`: `2e.W` ≤ `190`이면 `5e524`; 아니면 `3af8`(`750`), `3af8`(`736`), BYTE `76` = 3, BYTE `77` = 0, `JSR 49a58`; `5e496`: `D0.W` &= 1; 0이면 `86.W` = 0, 아니면 `100`; `5e4ae`: LONG `36` = `ffff8000`, `2e.W` = `1b0`, `32.W` = `84`, BYTE `12` = BYTE `13` = `ff`, `8ff4`, `8ebe`(`d4b`, 0), `4a496`(`d56`), `5e4ec`(결정 3).
  - 상태 3(`5e528`: BYTE `76` = 3이 아니면 `5e7dc`): 하위 0~2(`5e532` `5e582` `5e5f0`)는 먼저 LONG `3a` −= LONG `3a` 산술 >> 3. 하위 0: `2e.W` ≤ `f0`이면 BYTE `77` = 1(`5e578`); 아니면 `D0` = LONG `36`, ≤ `fffa0000`이면 LONG `36` −= `D0` 산술 >> 3(`5e56e`), 아니면 LONG `36` += (산술 >> 3) + `fffff000`(`5e55e`). 하위 1(문턱 `f0`)·2(`100`): `2e.W` > 문턱이면 `D0` = LONG `36`, > `fffa0000`일 때 LONG `36` −= `D0` 산술 >> 3 뒤 LONG `36` += `fffff000`(두 번의 메모리 RMW, `5e5ae`/`5e61c`); 아니면 LONG `36` < `60000`일 때 LONG `36` −= (산술 >> 3) + `fffff000`(`5e5ce`/`5e63c`). 그 뒤 BYTE `62` ≠ 0이면 BYTE `62` = 0, BYTE `77` = 2/3. 하위 3(`5e65e`): `2e.W` 문턱 `100`의 같은 `36` 갱신(`5e668`~`5e6a0`, `3a` 감쇠 없음), `5e6ac`: `D0.W` = `32.W`; = `86.W`이면 `5e704`; < `86.W`이면 `5e6e2`(LONG `3a` ≥ `38000`이면 −= 산술 >> 2, 아니면 += `10000`), 크면 `5e6bc`(LONG `3a` ≤ `fffc8000`이면 −= 산술 >> 2, 아니면 += `ffff0000`). `5e704`: BYTE `62` ≠ 0이면 BYTE `62` = 0, `3af8`(`74f`), BYTE `77` = 4, LONG `36` = `8000`. 하위 4(`5e72c`; 다른 값은 `5e7d8`): LONG `3a` −= 산술 >> 3, `D0` = LONG `36`; < `60000`이면 += (산술 >> 3) + `1000`; `2e.W` ≤ `190`이면 `5e7d8`; 아니면 `3af8`(`74e`), BYTE `76` = BYTE `77` = 0, LONG `36` = `ffffc000`, LONG `3a` = 0, `2e.W` = `190`, `32.W` ≤ `80`이면 `86.W` = `f0` 아니면 0, `8ff4`, `8ebe`(`d48`, 0), `4a496`(`d56`), `49f8c`(A1 = `60c9e`, `D0.W` = `100`).
  - 꼬리 `5e7dc`: `JSR 43ea4`; BYTE `79` ≠ 0이면 `JSR 49fc6`(`5e7ea`); `JSR 4b54e`; Set이면 BYTE `5e` = 0(`5e7fa`). `5e7fe`: BYTE `61` bit 7 = 0이면 RTS(`5e8a4`). `5e808`: BYTE `63` = `ff`, `(A6)` = `6093a`, `JSR 8ff4`. `5e818`: BYTE `76` = 1이면 `8ebe`(`d4b`, 0) 뒤 `49f8c`(A1 = LONG(LONG `22` + `dc`)); 3이면 같은 꼴(`d4b`, `d8`); 아니면 `8ebe`(`d4d`, 0), `49f8c`(`e4`). 셋 다 `D0.W` = `100`, A0 = A6 + `26`, 끝은 `BRA.W 6093a`(경계).

## carry

- [F] **소비 1 block**: `5e7f6 BCC.W 5e7fe`(U01 `4b54e`의 C; 결정 4). Unknown C로 들어오면 `objects n24 caller requires known carry`(상태 보존)다. Clear면 `5e7fe`, Set이면 `5e7fa`.
- [F] **known 생산 0 block**. N24 안에는 `ORI`/`ANDI` CCR이 없고, RTS(`5e8a4`) 앞 C를 읽는 ROM 소비자도 없다(stage event callback/설치 callback의 복귀).
- [F] **FLOW_ONLY 33 block**(C 보존): JSR 하나뿐인 block(`5e050` `5e7aa` `5e7dc` `5e7ea` `5e7f0`), `BRA` block(`5e104` `5e20a` `5e246` `5e27c` `5e2ae` `5e2de` `5e310` `5e340` `5e3ca` `5e3ce` `5e414` `5e524` `5e574` `5e57e` `5e5bc` `5e5ec` `5e62a` `5e65a` `5e68e` `5e6de` `5e728` `5e7d8` `5e846` `5e878` `5e8a0`), `BTST`+`BEQ`(`5e7fe`), RTS(`5e8a4`), 소비 `5e7f6`.
- [F] **carry 보존 목록 33 PC** = FLOW_ONLY 33.
- [F] **Unknown 162 block**: 나머지(`MOVE`/`MOVEQ`/`CLR`/`ST`+`MOVE`/`TST`/`CMP`/`CMPI`/`ADD`/`ADDI`/`SUB`/`SUBI`/`ASR`/`LSR`/`LSL`/`ANDI`/`BSET`가 있는 block, 설치 block, 애니메이션 인자 block).
- [F] X를 쓰는 명령은 없다.

## 구현 범위와 규약

- routing 1 범위(`5deec..5e8a6`). 짝수 PC 1,245개 중 block 시작 195, 내부 1,050. 내부 PC 직접 진입은 `unsupported animation objects n24 PC`다. 범위 이웃(앞 자료, `5e8a6` 표, `5e8b0..5e8c8`(결정 1))은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. 산술·shift는 원래 폭의 2의 보수·부호 채움으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다(`ASR.L`은 부호 bit 채움을 직접 계산). 부호 있는 비교는 32/16 bit 값을 부호 bit 기준으로 명시 비교한다. 결과 flag는 같은 block 안의 Bcc만 쓴다(결정 4 예외). 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다). 메모리 대상 RMW(`BSET.B` `ADDI.L` `SUB.L` `ADD.L`)는 읽은 뒤 쓴다.
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 33 PC를 넣는다.
- 제어 이동: 모두 정적이다. 설치 값은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. `5e0ba`→`5e0c0`은 같은 실행으로 계속한다. `BRA.W 6093a`는 PC = `6093a`(경계).
- 스택: JSR 복귀 LONG push와 `5e8a4 RTS` pop만. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank): LONG `200194`(`5df12`, id `18b` → LONG `22`).
- [F] LONG `22` 기준 LONG 읽기(live bus; 대상이 bank window면 bank 읽기): `c8`(`5e06e`), 4·WORD(`5e8a6` 표)(`5e1ee` `5e508`, 부호 확장 16 bit 색인), `dc`(`5e830`), `d8`(`5e862`), `e4`(`5e88a`). 결과 A1은 `49f8c`(interpreter) 인자다.
- [F] 고정 ROM 자료(live bus): `5e8a6` WORD 표(결정 3). 주소만 넘기는 자료: `60c0a`(`490ba` A0), `60c9e`(`49f8c` A1), `8ebe` 인자 WORD `d48` `d4b` `d4d`, `4a496` 인자 `d56`, `3af8` 인자 `74e` `74f` `750` `736` `19d4`.
- [F] work RAM 노드 A6: BYTE `12` `13` `15`(`BSET` RMW) `5e` `61`(bit 7) `62` `63` `76` `77` `79` `88` `89`; WORD `1e` `20` `2e` `32` `46` `54` `68` `86`; LONG `(A6)`(설치) `22` `36` `3a` `56`. A0 = A6 + `26`(`49f8c` 인자).
- [F] 상수 인자: `28ae` `D0.W` = 0(16번); `49f8c` `D0.W` = `100`; `8ebe` `D1.B` = 0.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256): `engine/src/animation_machine_objects_n24.cpp` `131d65f2d55b01b7160b178ad94de4a8f614976b282690f4b9f8b5fdb5a73540`, `engine/tests/animation_machine_objects_n24_test.cpp` `5c18fc5c43e5fccb4e31037b04c48c7960c6dbc9e7b46714586e59f928872f99`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나, carry 보존 case group 하나(33 PC); `9cebcd9c…`), `engine/src/animation_machine_internal.h`(선언 하나; `1597fe31…`), `Makefile`(source 목록·test target·실행 줄; `8764354e…`), `tools/verify_animation_machine.py` SOURCES(`b75b0561…`).
- [F] 실행부 case 집합 = scratch `starts.txt`(195, SHA256 `5f7d3b90…`). 내부 PC 1,050개는 모두 `unsupported animation objects n24 PC`, 소비 `5e7f6`은 Unknown C에서 `objects n24 caller requires known carry`(상태 보존)다.
- [F] `make -j4 all test`: exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log`). N24 test 출력: `animation machine objects n24: 973 fixtures (11 checked errors, 13 kept C), 195 blocks, 3206 calls`. N22·N23 test는 그대로 통과.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N24 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만, scratch `gen/gen24.py` Unicorn 생성): 973 fixture(성공 962, checked 오류 11), 195 시작 모두 Unicorn fixture로 덮음, block 표(195 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 1은 Unknown에서 거부), zero-step 195 × 3, 내부 PC 1,050 전수, 홀수 PC(범위 양끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`·RTS 복귀 `10fe40`(4 fixture), 범위 옆 자료 `5deea` `5e8a6` `5e8a8` `5e8ae`, 경계 stop 14개(다른 단위 진입 13·`6093a`는 stop만). 상태기계 fixture는 비교마다 문턱 ±1·부호 경계(`8000`/`7fff`, `80000000`/`7fffffff`)를 상태(BYTE `76`/`77`)별로 훑고, 무작위 조합 100개와 block별 직접 진입을 더했다. "real" 행은 fade_card `28ae`(자식 16개: 자리 20/3/0)와 U01 `4b54e`(`56` = 0 → `4b6be`/`4b6ca`; `56` → 기록 → `4b548` → `4b6be`)를 native로 따라가 실제 소비자 `5e7f6` 분기와 비교했다. 표 `5e8a6`은 같은 길이의 합성 WORD 5개(`0002 0003 ffff 2001 ffff`; `2001` → `LSL.W` `8004` 음수 색인), banked LONG `200194`는 합성 LONG(RAM 표 `10ec00`)이다. LONG `22`가 bank window(`200100`)일 때 음수 색인이 `1f8104`(RAM mirror)를 읽는 행도 넣었다.
- [F] 돌연변이 검사(scratch `mut/mut24.py`, 실행부 한 줄씩 18개: 소비 분기 뒤바꿈, `ASR.L` 논리 shift, LONG/WORD 부호 없는 비교, `BGE` 같음, 방향 nibble shift, 표 색인 배수·부호 확장, `5e5ae` RMW 부호, `5e14a` `SUBI`, `5e264` mask, 자식 순서, `5e76e` `BLE`, `BSET` RMW, `ASR.L #2`, `5e3dc` 부호, `60000` 문턱, `61` bit): 18/18을 test가 잡았다(`5e1ee` 부호 확장과 `5e76e` 경계를 잡으려고 fixture 11개를 더했다).
- [F] 실제 ROM 차분(scratch `realrom/real24.py`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM과 상태 문턱 값, LONG `22` = 실제 banked 기록(`200194` → `2c89c2`) 또는 그 RAM 사본, native는 STOP·`2a00`·`2a24`·C++ routing 밖 첫 PC(`6093a` 포함)·interpreter `49f8c`/`49f96`(선언 stop)에서 멈춤): 3 seed × 1,500 case 불일치 0/0/0, 시작 195/195. 실제 생산자(U01 `4b54e`) 뒤 소비자 `5e7f6` native 분기 비교 873/923/886건. native가 `6093a`에서 멈춘 case 12/9/10. clean stop이 없는 native case는 건너뜀(33/37/19; 주로 `5deec`에서 자리 수 `40` > 준비한 자유 노드 20). interpreter 따라가기(`FOLLOW_ANIM`, RAM 표 = 실제 기록 사본) 2 × 1,000 case 불일치 0(건너뜀 362/367: 대부분 interpreter를 따라간 native가 PC < `400`에서 멈춤(`low`), 나머지는 `5deec`의 자유 노드 부족; [U] 원인 미분석). [F] 참고: 첫 `FOLLOW_ANIM` 시도에서 RAM 표에 임의 RAM 포인터를 넣었을 때 2건이 interpreter `49ffe`의 checked 오류 `unsupported animation command or dispatch alignment`(임의 명령 BYTE)로 갈렸다. N24 밖(interpreter 계약 범위)의 의도된 checked 거부이며 harness 입력을 실제 목록으로 바꾼 뒤 0이다.
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `0da8cec` 일치 pass 14,408·node 122,462, 불일치 0 → N24 뒤 같음(`diff_results.json` SHA256 `a6c41695…`, 기준과 바이트 동일).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 132·pass 52,800·node 396,091·불일치 0(`verification.json` SHA256 `5656685f…`) → N24 뒤 같은 값(`cf1757fc…`; 차이는 seed 32 33 116 117 기록의 `current_router_sha256`과 `engine_source_sha256`뿐). 새 완주 seed 0, 잃은 seed 0. seed 32 33은 그대로 frame 0 `dcf56`(N27)에서 멈춘다(재범위 예상과 같음).
- [U] 남은 미확인: seed 32 33의 자연 경로는 `dcf56`(N27)에서 먼저 멈춰 N24 범위의 frame pass 비교가 아직 없다(실제 ROM 차분·fixture로만 덮음). `6093a` 경로와 상태 1~3은 자연 400 frame에서 실행되지 않는다(seed 32 33은 상태 0만). 결정 1의 `5e8b0..5e8c8`은 routing하지 않았다.
