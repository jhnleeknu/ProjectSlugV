# 객체 callback F4 N21: `b9832` 계열 꼬리(옛 U31 나머지) — `28ae` 자식 callback `b9d0a` `b9d1c`(설치 `b9d7a`), stage event callback `c3fdc`(설치 `c404c`), N20이 넘긴 설치 callback `b9c0e` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N21 행(29 block, `b9d0a..b9da6` `c3fdc..c4084`, callback `b9d0a` `b9d1c` `b9d7a` `c3fdc` `c404c`, 경계 `c41a4`, bank 2, 미실행 설치 1(+12), 새 seed 42 43 / 42 43, 옛 U31 29)과 메인 결정 1·2(이름 `objects-n21`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계), 그리고 N20 계약(`animation-machine-objects-n20-contract.md`, SHA256 `7f4e37d016a6421553e1e3bdf2c60824373cdf3ac6627051fd37c4429e1e8f3e`) 결정 1이 넘긴 설치 callback 본문 `b9c0e..b9c6e`(15 block)이다. 단위 형식과 규약은 N20 계약을 따른다. 메인 작업 지시:
- flag 재계산은 선행이 유일할 때만(아니면 분기를 각 선행에 접어 넣음).
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 설치·진입은 넣는다.
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가).
- 다른 단위 실행부(`animation_machine_interpreter.cpp` 포함)는 고치지 않는다. 기존 실행부의 두 번째 진입 누락은 scratch patch와 결정으로 보고한다. DIV 0 제수는 단위 checked 오류(N21에는 DIV가 없다).
- N21 = 재범위 N21 행 + N20이 넘긴 `b9c0e..b9c6e`. 목표 seed 42 43(base·RNG; 기준에서 frame 0 `b9d1c`에서 멈춤). N21 뒤 N20의 frame 1 이후 자연 경로가 실행되므로 seed 42 43의 400 frame 일치를 따로 보고한다.

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback)로 정한다. fall-through로 이어지는 설치 대상도 시작으로 센다. 묶인 연속 Bcc·PC 상대 점프 표는 없다. Unicorn TB 분할(`c3fe2` `c3fe8` 등)은 시작이 아니다.
- 결정 5(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N20 수용 관례: `MOVE.x`/`CMP`/`CMPI`/`CMPA`/`ADD`/`ADDI` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N21 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`2001d0` `200088`)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n21`(HEAD `dd61e61` = N20까지 통합, `engine/src/animation_machine.cpp` SHA256 `d5224192525d45c0e6c9e35ff55d8cc491c73601ec070d4858c11e5d00711847`, routing 규칙 77개, `engine/src/animation_machine_interpreter.cpp` SHA256 `bd2bffb36ccf99cc18fe141949335e6ef1e07f7255cb1f137e387d0451ebac05`)을 참조했다. N21 routing 범위의 짝수 PC와 범위 양옆 PC(`b9da6` `c3fda` `c4084`)는 기존 routing에 없다(`b9c0c` `b9c6e` `b9d08`은 N20). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n21/n21.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **N21 = 44 block**(재범위 N21 행 29 + N20 결정 1이 넘긴 `b9c0e..b9c6e` 15), 코드 3 범위 420바이트, 88명령이다. routing 짝수 PC 210개 중 내부 PC 166개다. 세 범위의 명령은 모두 진입에서 정적으로 도달한다(routing 구멍 없음).
- [F] 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx·스택 WORD/BYTE push·I/O port 쓰기·bank 변경은 없다.
- [F] 진입:
  - stage event callback(고정 ROM LONG 표): `c3fdc`(`e8ff8`).
  - `28ae` 자식 callback(N20 `b9860` `b98bc` / `b9870` `b98cc`의 `MOVEA.L #imm,A0`): `b9d0a`, `b9d1c`.
  - 범위 안 설치 callback(결정 3 관례): `b9d7a`(`b9d74`, fall-through), `c404c`(`c4046`, fall-through), `b9c0e`(N20 `b9c00`, fall-through; N20에서는 경계였다).
  - 범위 밖 참조가 있는 시작은 위 진입뿐이다(scratch `n21xref.py`; 고정 ROM 절대 LONG, `Bcc`/`BRA`/`BSR`, `JSR`/`JMP`/`LEA d16(PC)` 전수 검사. `b9c30` `b9c48` `c4000`의 겉보기 참조는 명령 확장어·자료의 우연 일치다).
- [F] **경계(실행부 없음)**: `c41a4`(`c4064 BSR.W`). `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **범위 밖 설치 값(노드 LONG에 저장만)**: `c4084`(`c4068 MOVE.L #c4084,(A6)`; 다음 함수 `c4084 TST.W 78(A6)…`의 시작, 어느 단위에도 없음 = 재범위 "미실행 설치 1(+12)"). 실행 PC가 아니다.
- [F] **carry**(아래 "carry" 절):
  - 소비 block **3개**: `b9c32 BCC`·`c4078 BCC`(U05 `1ab02`), `b9d9a BCS`(stage_event_ops `288c`).
  - known 생산 block **없음**.
  - FLOW_ONLY 27개(소비 3 포함), Unknown 17개. 27 + 17 = 44.
- [F] 스택: JSR/BSR 복귀 LONG만.
- [F] 자료(모두 live bus): banked LONG `2001d0`(id `203`; 기록 LONG `24`), `200088`(id `ca`; 기록 LONG + sext(4·`90.W`)). 고정 ROM 주소 인자: 사각형 `b982a`(`1ab02`; `ffb0 ffc0 00a0 0080`), `c3fd4`(`1ab02`; `ffc0 ffc0 0080 0080`). work RAM은 "자료" 절.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `n21seen.py`): 두 기록 모두 seed 42 43만 N21 범위 PC를 실행한다. callback 실행 수(각 seed, 두 기록 같음): `b9d0a` 2, `b9d1c` 2, `b9d7a` 340, `c3fdc` 1, `c404c` 85. `b9c0e..b9c6e`, `c400e`, `c4064`/`c4068`(경계 `c41a4`), `c407c`, `b9d9e`는 자연 실행되지 않는다.
- [F] **기준(`dd61e61`)에서 seed 42 43은 두 기록 모두 frame 0 `b9d1c`에서 멈춘다**(N20 계약 검증 기록). N21 뒤 두 seed의 완주 여부와 400 frame 일치는 아래 검증 기록에 적는다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 = 재범위 N21 행 + `b9c0e..b9c6e`(44 block).** [F] 메인 지시대로 N20이 넘긴 설치 callback 본문 15 block(`b9c0e` `b9c12` `b9c18` `b9c1e` `b9c26` `b9c32` `b9c36` `b9c3c` `b9c42` `b9c46` `b9c4e` `b9c54` `b9c5a` `b9c66` `b9c6c`)을 넣는다. N20 routing(`b9c00` fall-through 대상이 `b9c0e`)은 바뀌지 않는다. N20 test는 `b9c0e`를 stop으로만 쓰므로(fixture `b9bc4` `b9c00` `flow-b9bc4-c1/c2`, block 표 `b9c00`, 경계 stop 목록) 계속 맞다(stop은 실행 전 확인).
2. **`c41a4` 경계, `c4084` 설치 값.** [F] `c41a4`는 범위 밖(`c4084..` 다음 함수 군집)이고 `c4064 BSR.W`만 부른다. 재범위 표대로 실행부 없는 경계로 둔다. `c4084`는 `c4068`이 노드 LONG에 쓰는 설치 값이다. 둘 다 400 frame 안에 자연 실행되지 않는다(재범위 "미실행 설치 1(+12)").
3. **routing 구멍 없음.** [F] 세 범위의 88명령이 모두 도달한다. `b9da6..`은 자료(N20 `b98dc`가 LONG `84`에 넣는 `4706c` 인자), `c3fd4..c3fdc`는 사각형 자료다.
4. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n21.cpp`의 `animation_objects_n21_block`. 오류는 `unsupported animation objects n21 PC`(내부 PC), `objects n21 caller requires known carry`(소비 3 block). 메인 지시와 같다.
5. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`·`engine/src`에서 N21 범위의 PC를 경계·rollback 탐침으로 쓰는 곳은 없다(`b9c0e`는 위 1처럼 stop 전용). [U] 통합 수용 도구가 seed 42 43의 첫 미연결 PC `b9d1c`를 고정값으로 갖고 있으면 바뀐다(아래 검증 기록에 새 값).
6. **interpreter·다른 실행부의 두 번째 진입 누락 없음.** [F] N21이 부르는 다른 단위 진입(`ba2d6`(N06), `43ea4`(U04), `49fc6` `49f8c`(interpreter), `1ab02` `c6a96`(U05), `46ef4` `2a24` `43e34`(cleanup), `4706c`(U09), `49290`(U08), `288c`(stage_event_ops), `2a00`(fade_card))는 모두 기존 실행부의 case로 시작한다(scratch 검사: 해당 실행부 소스의 `case 0x…:`). 패치 파일은 없다.

## 원본 바이트 근거

[F] 코드 3 범위 합계 420바이트. 범위 순서로 이어 붙인 SHA256 `55799d620fa04885018fd47d4aaf55bd0165689b946891ebc07661b16da09b5d`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `b9c0e..b9c6e` | 96 | `dab20d424987c1e0e127e2937bd409bb1aa482909cd9a3eda9a20840741ee516` | 15 |
| `b9d0a..b9da6` | 156 | `c95e7b0fc984098f0996536867aa13fb236f08c58013837363c8c4ac43524ce7` | 14 |
| `c3fdc..c4084` | 168 | `d3d9a7fb3bbbcce9edeaed3d414afd0daad8172bf64bccb4bd9108cfc81cf29b` | 15 |

- [F] 범위 이웃: `b9c0e` 앞·`b9c6e` 뒤는 N20, `b9d0a` 앞(`b9d08 RTS`)은 N20, `b9da6..`은 자료(`fff6 0003 0014 0001 …`), `c3fd4..c3fdc`는 사각형 자료(`c406e LEA c3fd4(PC),A0`), `c4084..`은 다른 미연결 함수(`TST.W 78(A6)` …)다.

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작, "FLOW"는 C 보존, "C 소비"는 들어온 C로 분기, Unknown은 표시 없음. `.W`/`.B` 쓰기는 하위 WORD/BYTE만 바꾼다. 모든 비교·`TST`와 그 Bcc는 같은 block 안에 있다.

**설치 callback `b9c0e`(N20 `b9c00`이 설치·fall-through) 15**
- `b9c0e`: `JSR ba2d6(pc)` — FLOW
- `b9c12`: `JSR 43ea4.l` — FLOW
- `b9c18`: `JSR 49fc6.l` — FLOW
- `b9c1e`: `MOVE.W 80(a6), d0; BNE.W b9c46` (→`b9c26`)
- `b9c26`: `MOVEA.L #b982a, a0; JSR 1ab02.l` — FLOW
- `b9c32`: `BCC.W b9c42` (→`b9c36`) — C 소비
- `b9c36`: `JSR 46ef4.l` — FLOW
- `b9c3c`: `JMP 2a24.l` — FLOW
- `b9c42`: `BRA.W b9c5a` — FLOW
- `b9c46`: `CMP.W 5418(a5), d0; BHI.W b9c5a` (→`b9c4e`)
- `b9c4e`: `JSR 46ef4.l` — FLOW
- `b9c54`: `JMP 2a24.l` — FLOW
- `b9c5a`: `MOVEA.L 84(a6), a0; CMPA.W #0, a0; BEQ.W b9c6c` (→`b9c66`)
- `b9c66`: `JSR 4706c.l` — FLOW
- `b9c6c`: `RTS` — FLOW

**`28ae` 자식 callback `b9d0a` `b9d1c`(설치 `b9d7a`) 14**
- `b9d0a`: `MOVE.W #ffca, d0; MOVE.W #100, d1; JSR 49290.l`
- `b9d18`: `BRA.W b9d2e` — FLOW
- `b9d1c`: `MOVE.W #3c, d0; MOVE.W #100, d1; JSR 49290.l`
- `b9d2a`: `BRA.W b9d2e` — FLOW
- `b9d2e`: `MOVE.W #800, 68(a6); MOVE.W #800, 1e(a6); MOVE.W #73, d0; MOVE.W #9, d1; MOVE.B #0, d2; JSR c6a96.l`
- `b9d4c`: `LEA.L 26(a6), a0; MOVE.W #203, 20(a6); MOVE.L 2001d0.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 24(a1), a1; JSR 49f8c.l`
- `b9d74`: `MOVE.L #b9d7a, (a6)` (→`b9d7a`)
- `b9d7a`: `JSR 43e34.l` — FLOW
- `b9d80`: `MOVEA.L c(a6), a0; CMPI.W #100, 46(a0); BGT.W b9d94` (→`b9d8e`)
- `b9d8e`: `JSR 49fc6.l` — FLOW
- `b9d94`: `JSR 288c.l` — FLOW
- `b9d9a`: `BCS.W b9da4` (→`b9d9e`) — C 소비
- `b9d9e`: `JMP 2a00.l` — FLOW
- `b9da4`: `RTS` — FLOW

**stage event callback `c3fdc`(설치 `c404c`, `c404c`가 범위 밖 `c4084` 설치) 15**
- `c3fdc`: `MOVE.W #0, 68(a6); MOVE.W #0, 1e(a6); MOVE.W #21, d0; MOVE.W #1f, d1; MOVE.B #0, d2; JSR c6a96.l`
- `c3ffa`: `MOVE.W 78(a6), d0; BEQ.W c400e` (→`c4002`)
- `c4002`: `ADDI.W #1e, d0; MOVE.W d0, 90(a6); BRA.W c4014`
- `c400e`: `MOVE.W #25, 90(a6)` (→`c4014`)
- `c4014`: `LEA.L 26(a6), a0; MOVE.W #ca, 20(a6); MOVE.L 200088.l, 22(a6); LEA.L 26(a6), a0; MOVE.W 90(a6), d1; ADD.W d1, d1; ADD.W d1, d1; MOVEA.L 200088.l, a1; MOVEA.L (a1, d1.w), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `c4046`: `MOVE.L #c404c, (a6)` (→`c404c`)
- `c404c`: `JSR 43e34.l` — FLOW
- `c4052`: `JSR 49fc6.l` — FLOW
- `c4058`: `MOVE.W 76(a6), d0; CMP.W 5418(a5), d0; BCC.W c406e` (→`c4064`)
- `c4064`: `BSR.W c41a4` — FLOW(경계 callee)
- `c4068`: `MOVE.L #c4084, (a6)` (→`c406e`)
- `c406e`: `LEA.L c3fd4(pc), a0; JSR 1ab02.l` — FLOW
- `c4078`: `BCC.W c4082` (→`c407c`) — C 소비
- `c407c`: `JMP 2a00.l` — FLOW
- `c4082`: `RTS` — FLOW

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다):
  - `b9c0e`: `JSR ba2d6`(N06, `8c(A6)` WORD 표), `JSR 43ea4`, `JSR 49fc6`. `b9c1e`: `D0.W` = `80.W`; ≠ 0이면 `b9c46`. `b9c26`: A0 = `b982a`, `JSR 1ab02`; `b9c32`: Clear → `b9c42`(→`b9c5a`), Set → `JSR 46ef4; JMP 2a24`. `b9c46`: `D0.W` > A5 WORD `5418`(무부호, `BHI`)이면 `b9c5a`, 아니면 `JSR 46ef4; JMP 2a24`. `b9c5a`: A0 = LONG `84`; A0 = 0(`CMPA.W #0`: 부호 확장 0과 32비트 비교)이면 RTS, 아니면 `JSR 4706c` 뒤 RTS. (N20 `b99e6..b9a34`와 같은 꼴이다.)
  - `b9d0a`/`b9d1c`: `D0.W` = `ffca`/`3c`, `D1.W` = `100`, `JSR 49290`(복귀 `b9d18`/`b9d2a`) → `BRA b9d2e`. `b9d2e`: `68.W` = `1e.W` = `800`, `D0.W`/`D1.W`/`D2.B` = `73`/9/0, `JSR c6a96`. `b9d4c`: 애니메이션 block(id `203`, bank LONG `2001d0`, 기록 LONG `24`). `b9d74`: `(A6)` = `b9d7a`, fall-through.
  - `b9d7a`: `JSR 43e34`. `b9d80`: A0 = LONG `c(A6)`, WORD `46(A0)` > `100`(부호, `BGT`)이면 `49fc6`을 건너뛰어 `b9d94`. `b9d94`: `JSR 288c`; `b9d9a`: Set → RTS(`b9da4`), Clear → `JMP 2a00`.
  - `c3fdc`: `68.W` = `1e.W` = 0, `D0.W`/`D1.W`/`D2.B` = `21`/`1f`/0, `JSR c6a96`. `c3ffa`: `D0.W` = `78.W`; 0이면 `90.W` = `25`(`c400e`), 아니면 `D0.W` += `1e`(16비트), `90.W` = `D0.W`(`c4002`).
  - `c4014`(색인 애니메이션): A0 = A6 + `26`, `20.W` = `ca`, LONG `22` = LONG `200088`(bank), A0 = A6 + `26`, `D1.W` = `90.W`, `D1.W` = 4·`D1.W`(16비트, `ADD.W` 두 번), A1 = LONG `200088`(bank, 다시 읽음), A1 = LONG(A1 + sext(`D1.W`)), `D0.W` = `100`, `JSR 49f8c`(복귀 `c4046`). `c4046`: `(A6)` = `c404c`, fall-through.
  - `c404c`: `JSR 43e34`, `JSR 49fc6`. `c4058`: `D0.W` = `76.W`; `D0.W` ≥ A5 WORD `5418`(무부호, `BCC`)이면 `c406e`, 아니면 `BSR c41a4`(경계; 복귀 `c4068`) 뒤 `(A6)` = `c4084`. `c406e`: A0 = `c3fd4`, `JSR 1ab02`; `c4078`: Clear → RTS(`c4082`), Set → `JMP 2a00`.

## carry

- [F] **소비 3 block**(BCC/BCS 한 명령, FLOW_ONLY). Unknown C로 들어오면 `objects n21 caller requires known carry`(상태 보존)다. Clear면 BCC는 분기 대상, BCS는 fall-through; Set이면 반대.
  - `b9c32 BCC.W b9c42`, `c4078 BCC.W c4082`: U05 `1ab02`(사각형 `b982a`/`c3fd4` 화면 판정)의 C(U05 `1ab7a` ANDI Clear / U01 `1aafc` ORI Set). Set → `JSR 46ef4; JMP 2a24` 또는 `JMP 2a00`.
  - `b9d9a BCS.W b9da4`: stage_event_ops `288c`의 C(`2898`/`28a8` ORI Set, `289e` `CMPI.L #270e,(A0)` 같음 → Clear). Clear → `JMP 2a00`.
- [F] **known 생산 없음.** RTS(`b9c6c` `b9da4` `c4082`)는 FLOW이고, 호출자(scheduler)는 C를 쓰지 않는다. 경계 callee `c41a4`의 C는 `c4068 MOVE.L`이 지운다(Unknown).
- [F] **FLOW_ONLY 27 block**(C 보존): JSR/BSR/JMP/BRA/RTS block, `MOVEA.L #imm,A0`+`JSR`(`b9c26`), `LEA`+`JSR`(`c406e`), BCC/BCS 소비 3개. 목록: `b9c0e` `b9c12` `b9c18` `b9c26` `b9c32` `b9c36` `b9c3c` `b9c42` `b9c4e` `b9c54` `b9c66` `b9c6c` `b9d18` `b9d2a` `b9d7a` `b9d8e` `b9d94` `b9d9a` `b9d9e` `b9da4` `c404c` `c4052` `c4064` `c406e` `c4078` `c407c` `c4082`.
- [F] **carry 보존 목록 27 PC** = FLOW_ONLY 27.
- [F] **Unknown 17 block**: `MOVE`/`CMP`/`CMPI`/`CMPA`/`ADD`/`ADDI` 포함 block, `MOVE.L #imm,(A6)` 설치 block, 애니메이션 block(bank LONG). 목록: `b9c1e` `b9c46` `b9c5a` `b9d0a` `b9d1c` `b9d2e` `b9d4c` `b9d74` `b9d80` `c3fdc` `c3ffa` `c4002` `c400e` `c4014` `c4046` `c4058` `c4068`.
- [F] N/Z 재계산이 필요한 block 경계는 없다(block을 flag 읽기로 시작하는 곳은 위 C 소비 3곳뿐이다).

## 구현 범위와 규약

- routing 3 범위(위 표). 짝수 PC 210개 중 block 시작 44, 내부 166. 내부 PC 직접 진입은 `unsupported animation objects n21 PC`다. 범위 이웃(`b9da6..` 자료, `c3fd4..c3fdc` 자료, `c4084..`)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. 산술은 원래 폭의 2의 보수·부호 채움으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다. 결과 flag는 같은 block 안의 Bcc만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다; 예: 애니메이션 block은 `20(A6)` 쓰기 뒤 bank LONG을 읽어 `22(A6)`에 쓰고, `22(A6)`를 다시 읽은 뒤 기록 LONG을 읽는다; `c4014`는 `20(A6)` 쓰기, bank LONG 읽기, `22(A6)` 쓰기, `90(A6)` 읽기, bank LONG 다시 읽기, 색인 LONG 읽기 순서다).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 27 PC를 넣는다.
- 제어 이동: 모두 정적이다. 설치 값(`MOVE.L #imm,(A6)`)은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다(`c4084`는 범위 밖). 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(`b9d74`→`b9d7a`, `c4046`→`c404c`). `c4068`은 `c406e`로 이어진다.
- 스택: JSR/BSR 복귀 LONG만. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank):
  - LONG `2001d0`(id `20.W` = `203`) → `22(A6)`, 그 기록의 LONG `24`(`b9d4c`)를 A1로 읽어 `49f8c`(D0.W = `100`, A0 = A6 + `26`)로 넘긴다.
  - LONG `200088`(id `ca`): `c4014`가 LONG `200088`을 `22(A6)`에 쓰고, LONG `200088` + sext(4·`90.W`)의 LONG을 A1로 읽는다(원본은 index를 검사하지 않는다; C++도 검사하지 않는다).
- [F] 주소만 넘기는 고정 ROM 자료: 사각형 `b982a`(A0, `1ab02`; `ffb0 ffc0 00a0 0080`), `c3fd4`(A0, `1ab02`; `ffc0 ffc0 0080 0080`).
- [F] work RAM:
  - 노드 A6: WORD `1e` `68`(= `800` / 0), `20`(id), `76`(`c4058` 비교), `78`(TST·가산), `80`(TST, 비교), `90`(= `78`+`1e` / `25`, 색인); LONG `(A6)`(설치), `c`(부모 노드 → `46(A0)`), `22`, `84`(포인터, `4706c` A0).
  - A5 WORD `5418`(무부호 비교: `b9c46` `c4058`), 부모 노드 `c(A6)`의 WORD `46`(부호 비교 `100`).
- [F] 상수 인자: `c6a96` D0.W/D1.W/D2.B = `73`/9/0(`b9d2e`), `21`/`1f`/0(`c3fdc`); `49290` D0.W/D1.W = `ffca`/`100`(`b9d0a`), `3c`/`100`(`b9d1c`).
- [I] 게임 의미: `b9d0a`/`b9d1c`는 `b9832` 물체의 좌우(`ffca`/`3c`) 부속 자식으로, 부모 `46` 높이가 `100` 이하일 때만 애니메이션을 진행하고 부모가 사라지면(`288c` Clear) 지워지는 것으로 보인다. `c3fdc`는 `78` 인자로 애니메이션 색인(`90`)을 고르고 진행 값 `5418`이 `76`을 넘으면 `c41a4`로 상태를 바꾸는 배경 물체로 보인다. 확인하지 않았다.

## 의존·경계

- [F] N21 → 기존(모두 routing됨, 진입 case 있음): N06 `ba2d6`, U04 `43ea4`, interpreter `49f8c` `49fc6`, U05 `1ab02`(C 반환) `c6a96`, cleanup `46ef4` `2a24`(JMP) `43e34`, U09 `4706c`, U08 `49290`, stage_event_ops `288c`(C 반환), fade_card `2a00`(JMP).
- [F] 실행부 없는 경계: `c41a4`. 단위 test는 그 PC에서 stop만 확인한다(F4 test 경계 관례). rollback 탐침은 RAM `10fe00..10fefe`만 쓴다.
- [F] 다른 단위 → N21: stage event 표 LONG `e8ff8`(`c3fdc`), N20 `b9832`의 `28ae` 자식 A0(`b9d0a` `b9d1c`), N20 `b9c00`의 설치·fall-through(`b9c0e`).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 44 시작 모두 typed fixture로 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), zero-step, 내부 166 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 소비 3곳의 Unknown carry 오류, 경계 stop. bank LONG과 사각형은 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 소비자 C는 실제 생산자(`1ab02` `288c`)를 따라 들어간 fixture로 native 분기를 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(callback, 설치 상태, 실제 bank LONG·기록·표, 소비자 native 분기).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, 회귀 0, seed 42 43의 400 frame 일치(완주) 여부와 N20 자연 경로의 frame 1 이후 실행을 따로 기록.

## 작업자 검증 기록 (scratch)

- [F] 변경 파일: 새 `engine/src/animation_machine_objects_n21.cpp`(SHA256 `f5bdbf1f5df78f35956563c8e7b53a65ceabbdccbe7aafe2ef5981c68e9ba4bf`), 새 `engine/tests/animation_machine_objects_n21_test.cpp`(SHA256 `04d529241f2f5008659f105105db948e1e45b35e5660afa293e4c2d86d001551`), 공유 최소 수정 `engine/src/animation_machine.cpp`(routing `else if` 1개 3 범위, carry 보존 case group 1개 27 PC; SHA256 `36cb03c8e257208e0685cdb93a071867920bba256320f2dc2e1612c8ee506da0`), `engine/src/animation_machine_internal.h`(선언 1줄; SHA256 `8d9a4b8bc480e5ee3800a2126dc95bd4f4d3501ab4b770d3c3ec1fad294a88ba`), `Makefile`(source list·test target·run line; SHA256 `8e95ab133fd4c112324546c8771808f929cfdc92347067558f4bc054fd82cde0`), `tools/verify_animation_machine.py`(SOURCES; SHA256 `4141a3f376a80f646b5652e01150cf24c4515026bc33387c9f2e62a61fb595de`). `animation_machine_interpreter.cpp`(SHA256 `bd2bffb3…` 그대로)와 다른 단위 실행부·test는 고치지 않았다. 패치 파일 없음(결정 6).
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0(전체 재빌드 1회 + test 갱신 뒤 증분 1회). 새 test: `animation machine objects n21: 179 fixtures (12 checked errors, 65 kept C), 44 blocks, 630 calls`. N20 test(`b9c0e` stop 전용)는 그대로 통과(`668 fixtures … 218 blocks`). UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen21.py`, Unicorn + 합성 물리 바이트 `b982a` `c3fd4`(사각형), bank LONG `2001d0` → work RAM 기록 `10e700`, bank LONG `200088` → 고정 ROM 합성 기록 `fc000` 주변(work RAM 64 KiB 거울 때문에 sext 누락이 같은 주소로 겹치지 않도록 work RAM 밖에 둠); 표 SHA256 `a61e4b25e85ed4669a0416bc9e478edd681b82e95bfc0c5b1cec8b8c051f8510`, 두 번 생성해 같음): 44 시작 모두 fixture로 덮임. 실제 생산자 추종 fixture: `1ab02`(사각형 `b982a`/`c3fd4`, 안/밖·뒤집기·위아래 10~11방향 → `b9c32` `c4078`; Clear 7·Set 3~4), `288c`(부모 0/`270e`/`2710`/그 밖 → `b9d9a`). block 표는 시작마다 incoming C clear/set의 native 후계·digest와 계약 C 분류, Unknown C는 소비 3곳에서 정확한 오류, zero-step 44×3, 내부 166 PC 정확한 오류, 홀수 PC(범위마다 양 끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`과 RTS 복귀 `10fe40`(8 fixture), routing 밖 자료 `b9da6` `b9da8` `c3fd4` `c3fda`, 경계 stop 14곳(`c41a4` 및 다른 단위 진입). checked 오류 fixture 9개(홀수 노드 읽기·쓰기, ROM 노드, 장치 쓰기 2, 스택 장치, RTS 장치, `b9d80` 홀수 부모, `c4046` 홀수 노드 설치) + 소비 3개. 돌연변이 21개(소비 3곳 분기 반전, `b9c46` 부호/≥, `b9c5a` WORD 비교, `b9d80` 무부호/≥, `c4058` 부호/>, `c4002` LONG 가산, `c400e` 값, `c4014` sext 누락·배율, `b9d1c` D1, `b9d4c` 기록 offset, `c4068` 설치 값, `c3fdc` D2 폭, `b9c1e` D0 폭, `c406e` 사각형, `c4064` 복귀점)가 모두 test를 실패시켰다(scratch `mut/mut.out`; `c4014` sext 누락은 처음 기록을 work RAM에 두었을 때 64 KiB 거울로 살아남아 기록을 `fc000` 합성 ROM으로 옮긴 뒤 죽음).
- [F] 실제 ROM 차분(`realrom/real21.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, 무작위 work RAM, seed 1·2·3 각 1,500건; N20 진입 `b9b8c` `b9c00`의 `b9c0e` fall-through 포함): 불일치 0/0/0, 시작 도달 44/44/44. native stop은 STOP·`2a00`·`2a24`, 다른 단위 진입과 경계 `c41a4`(seed 1에서 64·132건 두 종류). 실제 생산자 뒤 소비자 native 분기 비교: `b9c32` 183/190/197, `b9d9a` 479/520/494, `c4078` 201/158/181건. Unknown C 진입이 소비자에 닿은 의도된 차이 0, 홀수 주소 차이 0. native가 깨끗이 멈추지 않은 입력(무작위 포인터로 낮은 PC, 3M 명령 안에 끝나지 않음)은 건너뛰고 셌다(433/351/375건).
- [F] 기준(`dd61e61` `git archive` 사본 `ms5-scratch/n21/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 14,168·node 118,752, 불일치 0(`diff_results.json` SHA256 `c4ae7811807405521f2b6a994a6b6ddfd0f5fc8fffdb03b238dac1cce1542da1`). N21 뒤: 일치 pass 14,408·node 122,462, 불일치 0, 회귀 0, 바뀐 seed는 42 43뿐(각 pass 0 → 120(완주), node 10 → 1,865; 기준의 frame 0 `b9d1c` 정지 해소)(SHA256 `a6c41695e17a74bdccee8a3ad95dbad143a56ea648e72fbc7c81ac534f3b3b72`).
- [F] RNG 초기화 400 frame 차분: 기준 complete 128, 일치 pass 51,200·node 382,641, 불일치 0(verification.json SHA256 `7ba9c6bcef77927aff9309b2b84cb9baef789d2897db76dbe851c9722bfd38d6`). N21 뒤: **complete 130(새 완주 seed 42 43)**, 일치 pass 52,000·node 389,711, 불일치 0, 회귀 0(잃은 complete seed 없음), `other` 0, 응답 `00` 변형 6 seed complete 6 유지, 도구 종료 0(SHA256 `c5373ba09ca6532f56c285fbda9bd574e17ad2cb30698aeaeec0da217f382e6f`). seed 42 43: 분류 `checked-current-first-unrouted-PC` → `complete`, 각 pass 400/400 일치, node 3,545/3,545 일치(기준 10). 따라서 N20의 frame 1 이후 자연 경로(재범위 재생 기준 각 seed `b99be` 85, `b9aae` 85, `b9cde` 340, `73928` 63회 등)와 N21의 `b9d7a` 340·`c404c` 85회 경로가 400 frame 동안 native와 같다.
- [F] ROM SHA256·mtime 작업 전후 같음(`29112a94…`, `1791291625`).

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] 경계 `c41a4`와 범위 밖 설치 `c4084`(다음 함수, 재범위 미실행 설치 +12)의 동작은 해당(고아 설치) 단위에서 정한다. 400 frame 안에 자연 실행되지 않는다.
3. [U] `b9c0e..b9c6e`는 자연 400 frame에서 실행되지 않는다(seed 42 43의 `b9b0c BLE`가 늘 `b9b30`). typed fixture와 실제 ROM 차분만 근거다.
4. [U] 색인 `200088` 기록의 실제 index 범위(`90.W` = `78.W` + `1e` 또는 `25`). 원본은 검사하지 않으므로 C++도 검사하지 않고 live bus로 읽는다.
5. [U] 응답 `00` 변형·400 frame 밖·controller skip 해제 시의 추가 경로.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n21/`(`n21.py` block·범위 계산, `n21cls.py` carry 분류, `n21stat.py` 범위 SHA·짝수 PC, `n21xref.py` 범위 밖 참조, `n21seen.py` 자연 도달, `unitdef.py`, `gen/` typed fixture 생성·test 조립, `mut/` 돌연변이, `realrom/` 실제 ROM 차분, `fp/` 프레임 패스·RNG 차분(기준 `base_*`, 뒤 `new_*`), `basetree/` 기준 사본; 저장소 밖).
