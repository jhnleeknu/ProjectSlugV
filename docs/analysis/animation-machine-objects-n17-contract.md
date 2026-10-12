# 객체 callback F4 N17: `7a53c` 계열 객체(옛 R14/R15) — stage event callback `7a53c`, 공용 진행 `7a388`, 설치 callback `7a48e` `7a4e0` `7a674`, 부모 설치 `7a3b2`, `28ae` 자식 `7a516` `7aa6e`/`7aae6`, 삭제 `7aa5e` `7aa66`, helper `7afa6`~`7b7ae`, 애니메이션 표 callback `7b740`~`7b790` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N17 행(157 block, `7a388..7a558` `7a65a..7a6ce` `7a9d6..7abc2` `7afa6..7b28e` `7b570..7b5a8` `7b740..7b7d4`, callback `7a53c` `7aa5e` `7aa66` `7aa6e` `7aae6`, 대상 seed RNG 76 77 98 99 104 105, 경계 `7a558`, 미실행 설치 4(+35), 옛 R14 118·R15 39)과 메인 결정 1·2(이름 `objects-n17`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계)다. 단위 형식과 규약은 N16 계약(SHA256 `0fddf6a12152727e39d4c44adc40bcd4da23a801fc1a613a5c0f84adf317ef66`)을 따른다. 메인 작업 지시:
- flag 재계산은 선행이 유일할 때만(아니면 각 선행에 접어 넣음).
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 진입(설치)은 넣는다.
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가).
- 다른 단위 실행부(`animation_machine_interpreter.cpp` 포함)는 고치지 않는다. 기존 실행부의 두 번째 진입 누락은 scratch patch와 결정으로 보고한다. DIV 0 제수는 단위 checked 오류(N17에는 DIV가 없다).
- N16b(`783ea`/`785f2` 분기)는 미뤄져 있다. 대상 seed가 필요로 하면 보고한다.

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기·DBRA fall-through와 DBRA 대상, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback과 `MOVEA.L #imm,A0`+`JSR 28ae` 자식 callback, 아래 결정 2·3의 진입)로 정한다. fall-through로 이어지는 설치 대상도 시작으로 센다. 묶인 연속 Bcc는 없다. Unicorn TB 분할은 시작이 아니다(자연 기록의 TB `7afec` `7aff0`은 `7afe8` block 안이다).
- 결정 5(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N16 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`/`ADDQ`/`SUBQ`/`ANDI.W`/`ADD`/`SUB`/`NEG`/`EXT`/`LSL`/`LSR`/`ADDI` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다; `ORI`/`ANDI` CCR은 항상 known). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`JMP`/`BRA`/`RTS`/Bcc/`DBRA`)과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`만인 block, callee C를 소비하는 Bcc block은 FLOW_ONLY다. checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N17 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`2000d4`)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n17`(HEAD `4a50832` = N15 + N16a까지 통합, `engine/src/animation_machine.cpp` SHA256 `b6a3ee0b66dd89ec8b2991c60d8d37e2fa8958cfb315b426e9cafabae3799937`, routing 규칙 73개, `engine/src/animation_machine_interpreter.cpp` SHA256 `bd2bffb36ccf99cc18fe141949335e6ef1e07f7255cb1f137e387d0451ebac05`)을 참조했다. 재범위 N17 행 hull의 짝수 PC는 기존 routing에 하나도 없다. 동시에 진행하는 N18(`8625a..86372` `864b6..868ea` `86f1c..86fca` `8715e..871ee` `b630e..b631c` `b6506..b660e` `b780c..b78b8` `dbe98..dbeec`)과 범위·경계가 겹치지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n17/n17.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **190 block**, routing 13 범위 1,742바이트, 379명령이다. routing 짝수 PC 871개 중 내부 PC 681개다. 220 이하라 나누지 않는다.
  - 재범위 행 157과 차이: 재범위는 두 400 frame 기록에서 실행된 TB 함수 본문만 셌다. 이 계약은 범위 안 정적 도달 전부(`7a476`/`7a48e`/`7a4e0`/`7a516` 파괴 사슬, `7a4aa`, `7ab62`/`7ab80`/`7aba2` 등 미실행 갈래)와 결정 2의 부모 설치 callback `7a3b2` 사슬(+18)·그 helper `7b17c`(+5), 결정 3의 표 callback `7b74a` `7b754` `7b790`을 센다. 반대로 hull 안의 범위 밖 전용 진입(`7a9d6..7aa5e`, `7b11a..7b140`, `7b1da..7b200`)은 뺀다(결정 4).
- [F] **진입**:
  - stage event callback `7a53c`(고정 ROM LONG 표 `e8d2c`). 범위 밖 참조는 이 표 하나다.
  - 범위 안 설치 callback(결정 2 관례): `7a48e`(`7a486`), `7a4e0`(`7a4a0`), `7a674`(`7a66e`, fall-through), `7aa5e`(`7a3aa` `7a50e`; 범위 밖 `79e80` `7a606` 설치도 있음), `7aa66`(`7abba`; 범위 밖 설치 5곳), `7aae6`(`7aae0`, fall-through), `7a40a`(`7a404`, fall-through), `7a426`(`7a418`).
  - `28ae` 자식 callback: `7a516`(`7a4e0`, A0), `7aa6e`(`7b0d6`, A0).
  - **부모 노드 설치 `7a3b2`**(결정 2): 자식 callback `7aae6` 사슬의 `7ab80 MOVEA.L c(A6),A0; MOVE.L #7a3b2,(A0)`이 부모 노드 LONG `(A0)`에 설치한다.
  - 범위 안 분기·호출 대상이자 범위 밖 참조가 있는 진입: `7a388`(`7a6ca` `7a41e BRA.W`, 범위 밖 `BRA.W` 12곳 이상), `7a476`(`7a398 BNE.W`, 범위 밖 `79e58` `7a5f8`), `7a65a`(`7a550 BNE.W`, 범위 밖 설치 LONG `7a9ae`), helper `7afa6` `7b018` `7b140` `7b17c` `7b1a2` `7b200` `7b23a` `7b268` `7b570` `7b7ae`(범위 밖 `JSR (PC)` 다수), `7b740` `7b786`(`JSR (PC)`와 표 `4a500`).
  - **애니메이션 표 callback**(결정 3): `7b740` `7b74a` `7b754` `7b786` `7b790`은 interpreter callback 표 `4a500`의 LONG(`4a708` `4a70c` `4a710` `4a714` `4a718`)이다. interpreter op `14`(`4a408`)/`30`(`4a30c`)가 live target `JSR (A1)`로 부른다.
- [F] **경계 callee(실행부 없음)**: `7a558`(`7a554 BRA.W`; 재범위 행의 경계), `7b8a8`(`7a3ce`), `72f40`(`7a46a JMP`), `7b834`(`7a498`), `7b28e`(`7a49c`), `cc778`(`7a4aa JMP`). 모두 `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다. `72f40` `7b28e` `7b834` `7b8a8`은 재범위 단위표 어디에도 없다(400 frame 미실행 고아 사슬).
- [F] **범위 밖 설치 값(고아 설치, 노드 LONG에 저장만)**: `7a6ce`(`7a6a4` `7a6b6`), `7a964`(`7a6c4`), `7abc2`(`7ab90` `7aba2`). 노드 `56` LONG 값 `7b924` `7b99c` `7ba14` `7b960` `7b9d8`(`7b740`~`7b790`)과 `MOVEA.L #imm,A1` 애니메이션 목록 `7c6b6` `7bd7c` `7c668`, 표 `7bce0`은 자료다.
- [F] **carry**(아래 "carry" 절): 소비 block **11개**(BCC/BCS), known 생산 block **11개**(Set `7a502` `7b0f4` `7b21c` `7b22e` `7b250` `7b588` `7b7ce`, Clear `7b214` `7b25c` `7b596` `7b59e`), FLOW_ONLY 93개(소비 11 포함), Unknown 86개. 93 + 11 + 86 = 190.
- [F] 스택: JSR 복귀 LONG만 쓴다. `DBRA` 1곳(`7a45c`, block `7a45a`). 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/MULx/DIVx·I/O port 쓰기·bank 변경·스택 직접 조작은 없다.
- [F] 자료(모두 live bus): banked LONG `2000d4`(`7a3d2` → 노드 `22(A6)`, 그 기록의 LONG `2c`를 A1로; `7a4aa` → A1). 고정 ROM LONG 표 `7bce0`(16 LONG, `7aaf6`이 `95 & f` 색인으로 읽음). work RAM은 "자료" 절.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `n17seen.py` `n17who.py`): RNG 400 frame 기록에서 seed 76 77 98 99 104 105만 N17 PC를 실행한다(TB 시작 107개; `7afec` `7aff0`을 빼면 모두 이 계약의 190 시작 안). 각 seed에서 callback `7a53c` `7aa6e` `7aae6` `7aa5e` `7aa66`이 실행되고, interpreter 표 callback `7b74a`(`7a53c` 노드)·`7b790`(`7aa6e` 자식)이 1회씩 실행된다. base 120 frame 기록에서는 0이다. 자연 미도달 시작(파괴 사슬 `7a476`~`7a53a`, 부모 설치 `7a3b2` 사슬, `7b17c`, `7b754`, `7a554`, `7ab62`/`7ab80`/`7ab90`/`7aba2`, `7aa9a`/`7aaa8`, `7b090`~`7b0ac` 등)은 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] 이 작업 트리 base `4a50832`에서 seed 76 77 98 99 104 105는 frame 0 node callback `7a53c`에서 멈춘다(RNG `checked-current-first-unrouted-PC`, complete 118). N17 뒤 결과는 "작업자 검증 기록".

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 190(나누지 않음).** [F] 재범위 행 6 범위 hull의 정적 도달(진입 5개 + 범위 안 설치·자식·부모 설치·표 callback) 전체다. 220 이하다.
2. **부모 노드 설치 callback `7a3b2` 포함(+18 block, helper `7b17c` +5).** [F] `7a3b2`는 범위 안(`7a388..7a558`)이고 N17 block `7ab80`(`MOVEA.L c(A6),A0; MOVE.L #7a3b2,(A0); JSR 49274.l`)만 참조한다(고정 ROM 전수 참조 검사 `n17xref.py`: `7ab86` LONG 1곳). 설치 대상 노드가 `A6`가 아니라 부모(`c(A6)`)인 점만 다르다. 메인 지시("참조된 범위 안 설치는 넣는다")에 따라 넣었다. 사슬: `7a3b2`(→ `7b8a8` 경계 또는 `7a3d2` 애니메이션 `2c`) → 설치 `7a40a`(`7b17c` 낙하, `49fc6`) → `49fc6` C에 따라 설치 `7a426`(`72f40` 경계로 JMP), 아니면 `56` = 0 뒤 `7a388`. `7b17c`(`7b17c..7b1a2`)는 hull 안 helper이고 범위 밖 `JSR (PC)` 12곳도 부르는 함수 시작이다. [F] 400 frame 두 기록 모두 이 사슬을 실행하지 않는다. [I] 빼면 177 block이고 `7a3b2`는 경계가 된다.
3. **애니메이션 표 callback `7b74a` `7b754` `7b790` 포함(+3 block).** [F] interpreter callback 표 `4a500`의 LONG `4a70c` `4a710` `4a718`이 가리키는 범위 안 함수(`MOVE.L #imm,56(A6); RTS`)다. interpreter(`4a408`/`4a30c` → `JSR (A1)` live target)가 부르므로 routing된 실행부가 도달한다. [F] `7b74a`(`7a53c` 노드, `4a408`)와 `7b790`(`7aa6e` 자식, `4a408`)은 대상 seed가 자연 실행한다(빼면 seed가 그 PC에서 다시 멈춘다). `7b754`는 같은 표에서 참조되지만 400 frame 미실행이다. 같은 꼴의 이웃 `7b75e` `7b768` `7b772` `7b77c` `7b79a` `7b7a4`는 참조가 없어 routing하지 않는다(결정 4). 표 `4a500`의 다른 범위 밖 LONG(`7b7da` `769ac` 등)은 이 단위와 무관하다.
4. **routing 구멍(범위 밖 전용 진입·미참조).** [F] hull 안이지만 N17 진입에서 도달하지 않는 코드는 routing하지 않는다(`unsupported animation machine PC`, N03·N11~N16 선례):
   - `7a9d6..7aa5e`: callback `7a9d6`(범위 밖 `7a9d0` 설치, 고아 `7a964` 사슬), `7a9fa` `7aa14`(범위 밖 `7a558` 함수의 설치 LONG `7a5de` `7a5ee`), 그 안의 설치 `7aa30`과 분기 대상 `7a9f6` `7aa2a` `7aa4c` `7aa5a`.
   - `7b11a..7b140`(범위 밖 `JSR 7b11a(pc)` 4곳의 helper), `7b1da..7b200`(범위 밖 `7a2ac` `7a8f4`의 helper).
   - 미참조: `7b75e..7b786`(`7b754` 뒤 4 함수), `7b79a..7b7ae`, `JMP` 뒤 도달 불가 `RTS` `7a4dc` `7aa64` `7aa6c`.
   - 내부 PC와 같은 값의 범위 밖 참조는 자료 우연 일치뿐이다(`7b000` LONG 12곳 이상 = `0007b000`; `7b02a` `7b0ea` `7b22a` 단일 LONG; `7a47a` `7abab` = 다른 명령 확장어). 모두 block 시작이거나 명령 중간이 아니라 무관하다(`7b000`은 명령 중간이지만 자료값이다).
5. **`DBRA` 반복 `7a45a`는 한 반복이 한 block.** [F] `7a446`이 `A0 = A6+76`, `D1 = (A6+99)-(A6+76) = 23`을 만든 뒤 `MOVE.W D0... LSR.W #1,D1`로 `D1.W = 11`, `D0.W = 23`(상위 WORD는 `A6+76`의 상위 WORD 유지), `D2 = 0`이다. `7a45a`(`MOVE.W D2,(A0)+; DBRA D1,7a45a`)는 `D1.W - 1 ≠ ffff`면 `7a45a`, 아니면 `7a460`이다(18회, `76..9a` WORD 0). `7a460 BTST.B #0,D0`(레지스터: bit 0)·`7a468 MOVE.B D2,(A0)+`(+1). 결과적으로 `76..9a` 37바이트를 0으로 한다. 홀수 `A6`면 첫 WORD 쓰기가 기존 checked 오류다.
6. **known C 생산 11 block과 확인 방법.** [F] RTS 앞 `ORI.B #1,CCR` / `ANDI.B #fe,CCR`(Set: `7b21c` `7b22e` `7b250` `7b588` `7b7ce`; Clear: `7b214` `7b25c` `7b596` `7b59e`)은 원본에서 항상 그 C를 만든다(뒤 block `7b22a` `7b238` `7b59a` `7b5a6`은 BRA/RTS FLOW, `7b250`/`7b25c` 안의 `BSET`/`BCLR`은 Z만). 실제 ROM 소비자: `7b200` → `7a390`; `7b570` → `7a6c0`; `7b7ae` → `7a3a6` `7a50a`(Set `7b7ce` 또는 `1ab02`의 C). `7b23a`(`7b250`/`7b25c`)의 C는 N17·범위 밖 호출자 모두 소비하지 않지만 ORI/ANDI라 known으로 둔다(N16 결정 5 선례). `7a502`/`7b0f4`(`28ae` 성공 → `4970a` 뒤 `ORI.B #1,CCR`)도 같은 이유로 Set이다(뒤 `7a506 JSR`/`7b0f8 MOVE.B`가 덮는다). typed fixture와 실제 ROM 차분이 helper를 따라 그 소비자의 native 분기로 C를 확인한다(Unicorn SR은 쓰지 않는다).
7. **다른 단위 C를 소비하는 7곳.** [F] `7a414 BCC`(interpreter `49fc6`: `49fe6` Set 또는 `4a0e0 ASR.W #1,D7`), `7a4f0`·`7b0e6 BCC`(fade_card `28ae`), `7ab5e BCC`·`7b206 BCS`(U01 `4b54e`: `4b6be` Clear / `4b6ca` Set), `7abb6 BCS`(stage_event_ops `288c`: `2898` Set, readiness `289e`), `7b04a BCS`(U20 `497a6`: Clear / `497b0` Set). 모두 기존 실행부가 known C를 둔다. typed fixture는 `28ae` `4b54e` `288c` `497a6` `1ab02`를 따라가 실제 N17 소비자의 native 분기를 확인한다. `49fc6`은 PVC bank port(`2ffff2`/`2ffff0`)를 쓰므로 typed fixture에서는 그 진입에서 멈추고(typed C로 `7a414`를 따로 확인), 실제 ROM 차분이 따라가 확인한다.
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n17.cpp`의 `animation_objects_n17_block`. 오류는 `unsupported animation objects n17 PC`(내부 PC), `objects n17 caller requires known carry`(소비 11 block). 메인 지시와 같다.
9. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`·`engine/src`에서 N17 routing 범위·경계 PC를 쓰는 곳은 없다. 새 경계 PC를 기대하는 기존 test도 없다.
10. **interpreter·다른 실행부의 두 번째 진입 누락 없음.** [F] N17이 부르는 다른 단위 진입(`1ab02` `288c` `28ae` `2a00` `2a24` `43e34` `46ef4` `490ba` `49274` `49290` `4929e` `496c2` `4970a` `497a6` `49a58` `49f8c` `49fc6` `4a496` `4b54e` `4b82e` `4be06` `4be2c` `4be34` `4bfa4` `4c0ac` `8ebe` `ea5f0`)은 모두 기존 실행부의 case로 시작한다(scratch `grep "case 0x…:"`). 패치 파일은 없다.
11. **`7aaf6`의 표 `7bce0` 읽기.** [F] `MOVE.B D0,95(A6); ANDI.W #f,D0; LEA 7bce0(PC),A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1`은 16 LONG 고정 ROM 자료 표(SHA256 `f7f30e7d2a643189ad3814e11baadd9d10a63df4ad008547543b61a589a0504d`)를 읽어 `49f8c`의 애니메이션 목록(A1)으로 넘긴다. 점프가 아니므로 전사하지 않고 live bus로 읽는다. 색인은 정적으로 0..15에 묶인다. [I] 앞 7개(`7c668` `7c670` `7c154` `7c26a` `7c2da` `7c422` `7c500`)만 애니메이션 목록이고 뒤 9개(`0` `14820000` …)는 다른 자료로 보인다(부모 `95` 값이 7 이상이면 interpreter가 나중에 실패할 수 있다).

## 원본 바이트 근거

[F] 코드 13 범위 합계 1,742바이트. 범위 순서로 이어 붙인 SHA256 `23f2b2046feb94129adb28226762c0808c15cdb5c845b6cc7d4685db9714cd35`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `7a388..7a4dc` | 340 | `06ca09018c5317b65666ccbcd1c4d9243107bcb6876a5fcd24eed057327ac2fc` | 34 |
| `7a4de..7a558` | 122 | `5a5d6affb1f9677856399e5a73b043217ca5ddce6211b29181694043262b30ec` | 16 |
| `7a65a..7a6ce` | 116 | `c30e54e828a596f70d55e286149baae8af96572ceaec951a48c1a38e577717d8` | 18 |
| `7aa5e..7aa64` | 6 | `2738adf81304c5fbbc9eedf6248d6b2d7cfa132bc35dfb5e458d0bbd9e12d3f9` | 1 |
| `7aa66..7aa6c` | 6 | `ce0b4b63936c9f9936a2908b03cd97d5f7e3790d46f3612b7e7817d660309410` | 1 |
| `7aa6e..7abc2` | 340 | `12ba15788505fcd438719bdc30b09a54238ef9b9a2a46eb42abb6e292defdf47` | 32 |
| `7afa6..7b11a` | 372 | `a29560172651869af24013bde2a254e078339687900c15c4d8596897d740f1e9` | 35 |
| `7b140..7b1da` | 154 | `28b70be21dadb9cd2f7664b436338dafb2bea9004af6c9ece949f6d4eae50bdf` | 19 |
| `7b200..7b28e` | 142 | `4e9ae137384835b72a7727792d0c35bc8ef836382021a0d6fcf9553935947f47` | 17 |
| `7b570..7b5a8` | 56 | `c3e72f08fa74513980c340c605f3b8d7a17b55d6cacb44c4efca17ff504ebbe6` | 7 |
| `7b740..7b75e` | 30 | `b105ae11c5d61a94a0c69a0ef6515a48ae9c99a12a307d3277fd6d05ca2f111e` | 3 |
| `7b786..7b79a` | 20 | `d2383d0fb7d9d90aa2406e8fcad6f27b8ffba69328f3af00861756303bacea35` | 2 |
| `7b7ae..7b7d4` | 38 | `65c29ad57caa6b13dbab88ca3ff6d674586cdfa7dc4c9574e3478327e78768f3` | 5 |

- [F] 범위 밖 이웃(모두 미연결, `unsupported animation machine PC`): `7a386`(앞 함수 끝), 구멍 `7a4dc`(도달 불가 `RTS`), `7a558..7a65a`(경계 `7a558` 함수: 설치 `7a9fa` `7aa14`), `7a6ce..7aa5e`(고아 설치 `7a6ce` `7a964` 사슬과 결정 4의 `7a9d6..7aa5e`), 구멍 `7aa64` `7aa6c`(`RTS`), `7abc2..`(고아 설치 `7abc2` 사슬), `7afa4`, 구멍 `7b11a..7b140` `7b1da..7b200`, `7b28e..7b570`(경계 `7b28e`, 고아 helper), `7b5a8..7b740`, 구멍 `7b75e..7b786` `7b79a..7b7ae`, `7b7d4..`(경계 `7b834` `7b8a8`, 자료 `7b924..` `7bc6c` `7bca0` `7bce0` `7bd7c` `7c6b6` `7c668`).
- [F] 범위 밖 → N17 참조(scratch `n17xref.py`, 고정 ROM 전수: LONG 값, Bcc/BRA/BSR 변위, `JSR`/`JMP`/`LEA (PC)`): `7a388`(`BRA.W` 12곳 이상), `7a476`(`79e58` `7a5f8 BNE.W`), `7a53c`(`e8d2c` 표), `7a65a`(`7a9ae` LONG), `7aa5e`(`79e80` `7a606` LONG), `7aa66`(`7ac38` `7acb0` `7adbe` `7af8c` `7afa0` LONG), `7afa6` `7b018`(`79d42` `79d4c`), `7b140` `7b1a2` `7b200` `7b23a` `7b268` `7b570` `7b7ae`(`JSR (PC)` 다수), `7b17c`(`JSR (PC)` 12곳 이상), `7b740` `7b74a` `7b754` `7b786` `7b790`(표 `4a708..4a718`). 모두 block 시작으로 간다. 내부 PC 값은 결정 4의 자료 우연 일치뿐이다.

## block 목록과 실행 의미

[F] 190 block. 각 줄은 block 안 명령 전체다(capstone 표기, 즉치·주소 16진). "(→x)"는 fall-through다. 태그: "C 소비"(Unknown이면 checked 오류), "Set/Clear 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)은 부호확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다(`MOVE.W #x,D0`·`CLR.W D0`·`ANDI.W #f,D0`·`ADD.W D0,D0`·`MOVE.W D1,D0`·`LSR.W #1,D1`·`ANDI.W #700,D1`은 하위 WORD만, `MOVE.B #0,D1`은 하위 BYTE만; `MOVEQ`·`EXT.L`·`NEG.L`·`LSL.L`·`SUB.L`·`MOVE.L`은 LONG 전체). `LEA 0.w,A0`은 A0 = 0이다. `ADDI.L #ffffb000`은 32 bit 2의 보수 덧셈이다. 비교 분기: `BLT`/`BLE`/`BGT`/`BGE`(부호 있는 비교; `CMPI.W #2,D0; BLT`는 signed `D0.W < 2`, `CMP.W 42(A6),D0; BLT`는 signed `D0.W < 42.W`, `BGT`는 signed `D0.W > 42.W`, `CMPI.W #100,42(A6); BGE`는 signed `42.W ≥ 100`, `CMPI.B #6,90(A6); BLE`는 증가 뒤 signed `90.B ≤ 6`, `CMPI.W #ffc0,42(A6); BLT`는 signed `42.W < -40`, `CMPI.W #1c0,42(A6); BGT`는 signed `42.W > 1c0`), `BEQ`/`BNE`(0 여부; `CMP.B 95(A6),D0; BEQ`는 BYTE 같음, `TST.L 56(A0)`은 LONG), `BCC`(C = 0), `BCS`(C = 1). `BSET`/`BCLR`은 대상 BYTE bit만 바꾸고 Z만 쓴다. `BTST.B #0,D0`(레지스터)은 bit 0이다. `MOVE.L 2000d4.l,22(A6)`/`MOVEA.L 2000d4.l,A1`은 bank window LONG을 live bus로 읽는다.

**공용 진행 `7a388`(`7a6ca`·`7a41e`의 BRA 대상; 파괴 `7a476` 사슬 진입) 8**
- `7a388`: `SUBQ.W #1, 82(a6); JSR 7b200(pc)`
- `7a390`: `BCC.W 7a398` (→`7a394`) — C 소비
- `7a394`: `CLR.B 5e(a6)` (→`7a398`)
- `7a398`: `BTST.B #7, 61(a6); BNE.W 7a476` (→`7a3a2`) — FLOW
- `7a3a2`: `JSR 7b7ae(pc)` — FLOW
- `7a3a6`: `BCC.W 7a3b0` (→`7a3aa`) — C 소비
- `7a3aa`: `MOVE.L #7aa5e, (a6)` (→`7a3b0`)
- `7a3b0`: `RTS` — FLOW

**부모 설치 callback `7a3b2`(자식 `7ab86`이 부모 노드에 설치; 설치 `7a40a` `7a426`) 18**
- `7a3b2`: `JSR 496c2.l` — FLOW
- `7a3b8`: `JSR 46ef4.l` — FLOW
- `7a3be`: `MOVE.W #100, 2c(a6); BTST.B #6, 98(a6); BEQ.W 7a3d2` (→`7a3ce`)
- `7a3ce`: `JSR 7b8a8(pc)` — FLOW
- `7a3d2`: `LEA.L 26(a6), a0; MOVE.W #b, 20(a6); MOVE.L 2000d4.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 2c(a1), a1; JSR 49f8c.l`
- `7a3fa`: `LEA.L 0.w, a0; JSR 4b82e.l` — FLOW
- `7a404`: `MOVE.L #7a40a, (a6)` (→`7a40a`)
- `7a40a`: `JSR 7b17c(pc)` — FLOW
- `7a40e`: `JSR 49fc6.l` — FLOW
- `7a414`: `BCC.W 7a41e` (→`7a418`) — C 소비
- `7a418`: `MOVE.L #7a426, (a6)` (→`7a41e`)
- `7a41e`: `CLR.L 56(a6); BRA.W 7a388`
- `7a426`: `MOVE.W #b, 20(a6); BCLR.B #7, 61(a6); CLR.B 5e(a6); MOVE.B #ff, 17(a6); LEA.L 0.w, a0; JSR 4b82e.l`
- `7a446`: `LEA.L 76(a6), a0; LEA.L 99(a6), a1; MOVE.L a0, d0; MOVE.L a1, d1; SUB.L d0, d1; MOVE.W d1, d0; LSR.W #1, d1; MOVEQ #0, d2` (→`7a45a`)
- `7a45a`: `MOVE.W d2, (a0)+; DBRA d1, 7a45a` (→`7a460`)
- `7a460`: `BTST.B #0, d0; BEQ.W 7a46a` (→`7a468`) — FLOW
- `7a468`: `MOVE.B d2, (a0)+` (→`7a46a`)
- `7a46a`: `MOVE.W #1, 70(a6); JMP 72f40.l`

**파괴 `7a476`(설치 `7a48e`) / callback `7a48e`(설치 `7a4e0`) 9**
- `7a476`: `LEA.L 0.w, a0; JSR 4b82e.l` — FLOW
- `7a480`: `JSR 46ef4.l` — FLOW
- `7a486`: `MOVE.L #7a48e, (a6); RTS`
- `7a48e`: `BTST.B #6, 98(a6); BEQ.W 7a4aa` (→`7a498`) — FLOW
- `7a498`: `JSR 7b834(pc)` — FLOW
- `7a49c`: `JSR 7b28e(pc)` — FLOW
- `7a4a0`: `MOVE.L #7a4e0, (a6); BRA.W 7a4de`
- `7a4aa`: `MOVE.B #ff, 17(a6); MOVE.B 8e(a6), 5e(a6); MOVE.W #b, 20(a6); MOVE.B #ff, 17(a6); LEA.L cdef8.l, a0; MOVEA.L 2000d4.l, a1; MOVE.W #b, d1; MOVE.W #1, d2; JMP cc778.l`
- `7a4de`: `RTS` — FLOW

**callback `7a4e0`(`28ae` 자식 `7a516`)와 자식 callback `7a516` 11**
- `7a4e0`: `MOVEA.L #7a516, a0; MOVE.W #14, d0; JSR 28ae.l`
- `7a4f0`: `BCC.W 7a506` (→`7a4f4`) — C 소비
- `7a4f4`: `MOVE.W #0, d0; MOVE.W #18, d1; JSR 4970a.l`
- `7a502`: `ORI.B #1, ccr` (→`7a506`) — Set 생산
- `7a506`: `JSR 7b7ae(pc)` — FLOW
- `7a50a`: `BCC.W 7a514` (→`7a50e`) — C 소비
- `7a50e`: `MOVE.L #7aa5e, (a6)` (→`7a514`)
- `7a514`: `RTS` — FLOW
- `7a516`: `MOVE.W #d2, 20(a6); MOVE.W #20d, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `7a52a`: `MOVEA.L #7c6b6, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `7a53a`: `BRA.B 7a506` — FLOW

**stage event callback `7a53c` 4**
- `7a53c`: `MOVE.W #16b, 20(a6); JSR 7afa6(pc)`
- `7a546`: `JSR 7b018(pc)` — FLOW
- `7a54a`: `BTST.B #0, 98(a6); BNE.W 7a65a` (→`7a554`) — FLOW
- `7a554`: `BRA.W 7a558` — FLOW

**`7a65a`(설치 `7a674`)와 callback `7a674`(범위 밖 설치 `7a6ce` `7a964`) 18**
- `7a65a`: `JSR 7b1a2(pc)` — FLOW
- `7a65e`: `MOVEA.L #7bd7c, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `7a66e`: `MOVE.L #7a674, (a6)` (→`7a674`)
- `7a674`: `JSR 7b23a(pc)` — FLOW
- `7a678`: `JSR 7b268(pc)` — FLOW
- `7a67c`: `JSR 7b140(pc)` — FLOW
- `7a680`: `JSR 49fc6.l` — FLOW
- `7a686`: `MOVE.W 86(a6), d0; CLR.W d1; JSR 4929e.l`
- `7a692`: `BTST.B #0, 15(a6); BNE.W 7a6ae` (→`7a69c`) — FLOW
- `7a69c`: `CMP.W 42(a6), d0; BLT.W 7a6aa` (→`7a6a4`)
- `7a6a4`: `MOVE.L #7a6ce, (a6)` (→`7a6aa`)
- `7a6aa`: `BRA.W 7a6bc` — FLOW
- `7a6ae`: `CMP.W 42(a6), d0; BGT.W 7a6bc` (→`7a6b6`)
- `7a6b6`: `MOVE.L #7a6ce, (a6)` (→`7a6bc`)
- `7a6bc`: `JSR 7b570(pc)` — FLOW
- `7a6c0`: `BCC.W 7a6ca` (→`7a6c4`) — C 소비
- `7a6c4`: `MOVE.L #7a964, (a6)` (→`7a6ca`)
- `7a6ca`: `BRA.W 7a388` — FLOW

**삭제 callback `7aa5e` `7aa66` 2**
- `7aa5e`: `JMP 2a00.l` — FLOW
- `7aa66`: `JMP 2a24.l` — FLOW

**자식 callback `7aa6e`(`28ae` 자식; 설치 `7aae6`) 11**
- `7aa6e`: `MOVE.W #16b, 20(a6); BTST.B #6, 98(a6); BNE.W 7aa9a` (→`7aa7e`)
- `7aa7e`: `MOVE.W #c48, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `7aa8c`: `MOVE.W #38c, d0; JSR 4a496.l`
- `7aa96`: `BRA.W 7aab2` — FLOW
- `7aa9a`: `MOVE.W #3c7, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `7aaa8`: `MOVE.W #171, d0; JSR 4a496.l`
- `7aab2`: `LEA.L cb5ee.l, a0; JSR 490ba.l` — FLOW
- `7aabe`: `MOVE.W d0, 54(a6); JSR 7b786(pc)`
- `7aac6`: `CLR.W d0; CLR.W d1; JSR 49290.l`
- `7aad0`: `MOVEA.L #7c668, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `7aae0`: `MOVE.L #7aae6, (a6)` (→`7aae6`)

**자식 callback `7aae6`(부모 추종; 부모 설치 `7a3b2`, 범위 밖 설치 `7abc2`, 설치 `7aa66`) 21**
- `7aae6`: `MOVEA.L c(a6), a0; MOVE.B 95(a0), d0; CMP.B 95(a6), d0; BEQ.W 7ab14` (→`7aaf6`)
- `7aaf6`: `MOVE.B d0, 95(a6); ANDI.W #f, d0; LEA.L 7bce0(pc), a1; ADD.W d0, d0; ADD.W d0, d0; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `7ab14`: `JSR 43e34.l` — FLOW
- `7ab1a`: `MOVEA.L c(a6), a0; MOVE.B 98(a0), 98(a6); MOVE.W 2c(a0), 2c(a6); BTST.B #0, 15(a0); BNE.W 7ab3e` (→`7ab34`)
- `7ab34`: `BCLR.B #0, 15(a6); BRA.W 7ab44` — FLOW
- `7ab3e`: `BSET.B #0, 15(a6)` (→`7ab44`) — FLOW
- `7ab44`: `JSR 49fc6.l` — FLOW
- `7ab4a`: `MOVEA.L c(a6), a0; BTST.B #7, 61(a0); BNE.W 7aba2` (→`7ab58`) — FLOW
- `7ab58`: `JSR 4b54e.l` — FLOW
- `7ab5e`: `BCC.W 7ab70` (→`7ab62`) — C 소비
- `7ab62`: `CLR.B 5e(a6); BSET.B #1, 98(a6); BRA.W 7ab76`
- `7ab70`: `BCLR.B #1, 98(a6)` (→`7ab76`) — FLOW
- `7ab76`: `BTST.B #7, 61(a6); BEQ.W 7ab9e` (→`7ab80`) — FLOW
- `7ab80`: `MOVEA.L c(a6), a0; MOVE.L #7a3b2, (a0); JSR 49274.l`
- `7ab90`: `MOVE.L #0, 56(a6); MOVE.L #7abc2, (a6)` (→`7ab9e`)
- `7ab9e`: `BRA.W 7abb0` — FLOW
- `7aba2`: `MOVE.L #0, 56(a6); MOVE.L #7abc2, (a6)` (→`7abb0`)
- `7abb0`: `JSR 288c.l` — FLOW
- `7abb6`: `BCS.W 7abc0` (→`7abba`) — C 소비
- `7abba`: `MOVE.L #7aa66, (a6)` (→`7abc0`)
- `7abc0`: `RTS` — FLOW

**helper `7afa6`(stage event 인자 해석) 10**
- `7afa6`: `CLR.B 98(a6); MOVE.W 76(a6), d0; CMPI.W #2, d0; BLT.W 7afbc` (→`7afb6`)
- `7afb6`: `JSR 49a58.l` — FLOW
- `7afbc`: `ANDI.W #1, d0; BNE.W 7afce` (→`7afc4`)
- `7afc4`: `BCLR.B #5, 98(a6); BRA.W 7afd4` — FLOW
- `7afce`: `BSET.B #5, 98(a6)` (→`7afd4`) — FLOW
- `7afd4`: `MOVE.W 78(a6), 86(a6); TST.W 78(a6); BEQ.W 7afe8` (→`7afe2`)
- `7afe2`: `BSET.B #0, 98(a6)` (→`7afe8`) — FLOW
- `7afe8`: `MOVE.W 7a(a6), d0; CMPI.W #0, d0; BEQ.W 7b004` (→`7aff4`)
- `7aff4`: `MOVE.W d0, 88(a6); MOVE.W 7c(a6), 8a(a6); BSET.B #6, 98(a6)` (→`7b004`)
- `7b004`: `CLR.W d0; MOVE.W d0, 76(a6); MOVE.W d0, 78(a6); MOVE.W d0, 7a(a6); MOVE.W d0, 7c(a6); RTS`

**helper `7b018`(초기 외형·소리·자식 생성) 25**
- `7b018`: `JSR 4c0ac.l` — FLOW
- `7b01e`: `JSR 496c2.l` — FLOW
- `7b024`: `JSR 4be06.l` — FLOW
- `7b02a`: `CMPI.W #100, 42(a6); BGE.W 7b03a` (→`7b034`)
- `7b034`: `BSET.B #0, 15(a6)` (→`7b03a`) — FLOW
- `7b03a`: `BTST.B #6, 98(a6); BNE.W 7b090` (→`7b044`) — FLOW
- `7b044`: `JSR 497a6.l` — FLOW
- `7b04a`: `BCS.W 7b060` (→`7b04e`) — C 소비
- `7b04e`: `MOVE.W #c46, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `7b05c`: `BRA.W 7b06e` — FLOW
- `7b060`: `MOVE.W #c54, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `7b06e`: `MOVE.W #c48, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `7b07c`: `MOVE.B 19(a6), 14(a6); MOVE.W #38c, d0; JSR 4a496.l`
- `7b08c`: `BRA.W 7b0bc` — FLOW
- `7b090`: `MOVE.W #3c7, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `7b09e`: `MOVE.W #c48, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `7b0ac`: `MOVE.B 19(a6), 14(a6); MOVE.W #171, d0; JSR 4a496.l`
- `7b0bc`: `MOVE.W #8820, 68(a6); MOVE.W #8820, 1e(a6); CLR.B 96(a6); MOVE.W #1, 54(a6); JSR 7b740(pc)`
- `7b0d6`: `MOVEA.L #7aa6e, a0; MOVE.W #a, d0; JSR 28ae.l`
- `7b0e6`: `BCC.W 7b0f8` (→`7b0ea`) — C 소비
- `7b0ea`: `CLR.W d0; CLR.W d1; JSR 4970a.l`
- `7b0f4`: `ORI.B #1, ccr` (→`7b0f8`) — Set 생산
- `7b0f8`: `MOVE.B 98(a6), 98(a0); MOVE.L a0, 7a(a6); LEA.L cb848.l, a0; JSR 490ba.l`
- `7b10e`: `MOVE.W d0, 82(a6); JSR ea5f0.l`
- `7b118`: `RTS` — FLOW

**helper `7b140`(이동·낙하) 8**
- `7b140`: `CLR.L 36(a6); CLR.L 3a(a6); JSR 4be34.l`
- `7b14e`: `BTST.B #7, 15(a6); BEQ.W 7b162` (→`7b158`) — FLOW
- `7b158`: `JSR 4bfa4.l` — FLOW
- `7b15e`: `BRA.W 7b17a` — FLOW
- `7b162`: `JSR 4be2c.l` — FLOW
- `7b168`: `BTST.B #7, 15(a6); BEQ.W 7b17a` (→`7b172`) — FLOW
- `7b172`: `CLR.L 36(a6); CLR.L 3a(a6)` (→`7b17a`)
- `7b17a`: `RTS` — FLOW

**helper `7b17c`(낙하 가속) 5**
- `7b17c`: `JSR 4be34.l` — FLOW
- `7b182`: `BTST.B #7, 15(a6); BEQ.W 7b194` (→`7b18c`) — FLOW
- `7b18c`: `CLR.L 3a(a6); BRA.W 7b19c`
- `7b194`: `ADDI.L #ffffb000, 3a(a6)` (→`7b19c`)
- `7b19c`: `CLR.L 36(a6); RTS`

**helper `7b1a2`(속도·높이 표) 6**
- `7b1a2`: `LEA.L cb650.l, a0; JSR 490ba.l` — FLOW
- `7b1ae`: `MOVE.W d0, d1; EXT.L d0; BTST.B #0, 15(a6); BNE.W 7b1be` (→`7b1bc`)
- `7b1bc`: `NEG.L d0` (→`7b1be`)
- `7b1be`: `LSL.L #8, d0; MOVE.L d0, 64(a6); ANDI.W #700, d1; LSR.W #1, d1; TST.W d1; BNE.W 7b1d4` (→`7b1d0`)
- `7b1d0`: `MOVE.W #80, d1` (→`7b1d4`)
- `7b1d4`: `MOVE.W d1, 2c(a6); RTS`

**helper `7b200`(C 반환: 접촉) 8**
- `7b200`: `JSR 4b54e.l` — FLOW
- `7b206`: `BCS.W 7b22e` (→`7b20a`) — C 소비
- `7b20a`: `BTST.B #1, 98(a6); BNE.W 7b21c` (→`7b214`) — FLOW
- `7b214`: `ANDI.B #fe, ccr; BRA.W 7b22a` — Clear 생산
- `7b21c`: `MOVEA.L 7a(a6), a0; MOVE.B 17(a0), 17(a6); ORI.B #1, ccr` (→`7b22a`) — Set 생산
- `7b22a`: `BRA.W 7b238` — FLOW
- `7b22e`: `MOVE.B 5e(a6), 8e(a6); ORI.B #1, ccr` (→`7b238`) — Set 생산
- `7b238`: `RTS` — FLOW

**helper `7b23a`(C 반환: 자식 `98` bit 1) 4**
- `7b23a`: `TST.B 96(a6); BNE.W 7b25c` (→`7b242`)
- `7b242`: `MOVEA.L 7a(a6), a0; BTST.B #1, 98(a0); BEQ.W 7b25c` (→`7b250`) — FLOW
- `7b250`: `ORI.B #1, ccr; BSET.B #1, 98(a6); RTS` — Set 생산
- `7b25c`: `ANDI.B #fe, ccr; BCLR.B #1, 98(a6); RTS` — Clear 생산

**helper `7b268`(자식 `56`에 따른 `4b82e`) 5**
- `7b268`: `MOVEA.L 7a(a6), a0; TST.L 56(a0); BEQ.W 7b282` (→`7b274`)
- `7b274`: `LEA.L 7bc6c(pc), a0; JSR 4b82e.l` — FLOW
- `7b27e`: `BRA.W 7b28c` — FLOW
- `7b282`: `LEA.L 0.w, a0; JSR 4b82e.l` — FLOW
- `7b28c`: `RTS` — FLOW

**helper `7b570`(C 반환: `90` 계수) 7**
- `7b570`: `BTST.B #7, 15(a6); BNE.W 7b59e` (→`7b57a`) — FLOW
- `7b57a`: `ADDQ.B #1, 90(a6); CMPI.B #6, 90(a6); BLE.W 7b596` (→`7b588`)
- `7b588`: `MOVE.B #6, 90(a6); ORI.B #1, ccr; BRA.W 7b59a` — Set 생산
- `7b596`: `ANDI.B #fe, ccr` (→`7b59a`) — Clear 생산
- `7b59a`: `BRA.W 7b5a6` — FLOW
- `7b59e`: `CLR.B 90(a6); ANDI.B #fe, ccr` (→`7b5a6`) — Clear 생산
- `7b5a6`: `RTS` — FLOW

**애니메이션 callback·helper `7b740` `7b74a` `7b754` `7b786` `7b790`(`56` LONG 설정; 표 `4a500`) 5**
- `7b740`: `MOVE.L #7b924, 56(a6); RTS`
- `7b74a`: `MOVE.L #7b99c, 56(a6); RTS`
- `7b754`: `MOVE.L #7ba14, 56(a6); RTS`
- `7b786`: `MOVE.L #7b960, 56(a6); RTS`
- `7b790`: `MOVE.L #7b9d8, 56(a6); RTS`

**helper `7b7ae`(C 반환: `42` 범위 + `1ab02`) 5**
- `7b7ae`: `CMPI.W #ffc0, 42(a6); BLT.W 7b7ce` (→`7b7b8`)
- `7b7b8`: `CMPI.W #1c0, 42(a6); BGT.W 7b7ce` (→`7b7c2`)
- `7b7c2`: `LEA.L 7bca0(pc), a0; JSR 1ab02.l` — FLOW
- `7b7cc`: `RTS` — FLOW
- `7b7ce`: `ORI.B #1, ccr; RTS` — Set 생산

## carry

- [F] **소비 11 block**(한 명령 BCC/BCS block, FLOW_ONLY). Unknown C로 들어오면 `objects n17 caller requires known carry`(상태 보존)다. Clear면 BCC 분기 대상(BCS는 fall-through), Set이면 반대.
  - N17 helper의 known C(결정 6): `7a390 BCC.W 7a398`(`7b200`), `7a3a6 BCC.W 7a3b0`·`7a50a BCC.W 7a514`(`7b7ae`), `7a6c0 BCC.W 7a6ca`(`7b570`).
  - 다른 단위의 known C(결정 7): `7a414 BCC.W 7a41e`(`49fc6`), `7a4f0 BCC.W 7a506`·`7b0e6 BCC.W 7b0f8`(`28ae`), `7ab5e BCC.W 7ab70`·`7b206 BCS.W 7b22e`(`4b54e`), `7abb6 BCS.W 7abc0`(`288c`), `7b04a BCS.W 7b060`(`497a6`).
- [F] **known 생산 11 block**: Set `7a502` `7b0f4`(`ORI.B #1,CCR`, fall-through), `7b21c` `7b22e`(`… ORI.B #1,CCR`, fall-through), `7b250`(`ORI.B #1,CCR; BSET.B #1,98(A6); RTS`), `7b588`(`MOVE.B #6,90(A6); ORI.B #1,CCR; BRA.W`), `7b7ce`(`ORI.B #1,CCR; RTS`); Clear `7b214`(`ANDI.B #fe,CCR; BRA.W`), `7b25c`(`ANDI.B #fe,CCR; BCLR.B #1,98(A6); RTS`), `7b596`(`ANDI.B #fe,CCR`, fall-through), `7b59e`(`CLR.B 90(A6); ANDI.B #fe,CCR`, fall-through).
- [F] **FLOW_ONLY 93 block**(C 보존): JSR/JMP/BRA/RTS block, `LEA`+`JSR`(`7a3fa` `7a476` `7b274` `7b282` `7b7c2`), `MOVEA`/`BTST`/`BSET`/`BCLR`(Z만)+Bcc block, BCC/BCS 소비 11개. 목록: `7a390 7a398 7a3a2 7a3a6 7a3b0 7a3b2 7a3b8 7a3ce 7a3fa 7a40a 7a40e 7a414 7a460 7a476 7a480 7a48e 7a498 7a49c 7a4de 7a4f0 7a506 7a50a 7a514 7a53a 7a546 7a54a 7a554 7a65a 7a674 7a678 7a67c 7a680 7a692 7a6aa 7a6bc 7a6c0 7a6ca 7aa5e 7aa66 7aa96 7aab2 7ab14 7ab34 7ab3e 7ab44 7ab4a 7ab58 7ab5e 7ab70 7ab76 7ab9e 7abb0 7abb6 7abc0 7afb6 7afc4 7afce 7afe2 7b018 7b01e 7b024 7b034 7b03a 7b044 7b04a 7b05c 7b08c 7b0e6 7b118 7b14e 7b158 7b15e 7b162 7b168 7b17a 7b17c 7b182 7b1a2 7b200 7b206 7b20a 7b22a 7b238 7b242 7b274 7b27e 7b282 7b28c 7b570 7b59a 7b5a6 7b7c2 7b7cc`.
- [F] **carry 보존 목록 93 PC** = FLOW_ONLY 93(반전 block 없음).
- [F] **Unknown 86 block**: 그 밖 `MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`ADDQ`/`SUBQ`/`ADD`/`SUB`/`ADDI`/`ANDI.W`/`NEG`/`EXT`/`LSL`/`LSR` 포함 block, `MOVE.L #imm,(A6)`/`(A0)`/`56(A6)` 설치 block, `MOVEA.L #imm,A0`+`MOVE.W`+`JSR 28ae` 자식 block, 애니메이션 block, `7a45a`(`MOVE.W`+`DBRA`), `7a468`(`MOVE.B`). `7b004`(`CLR.W D0; … RTS`)·`7b1d4`(`MOVE.W D1,2c(A6); RTS`)·`7b740`~`7b790`(`MOVE.L #imm,56(A6); RTS`)의 반환 C는 원본에서 0이지만 소비자가 없어 관례대로 Unknown이다(`7a546`/`7a65e`/`7aac6` 등 다음 명령이 덮거나 interpreter 복귀 `4a43e`가 소비하지 않는다).
- [F] N/Z 재계산이 필요한 block 경계는 없다(block을 flag 읽기로 시작하는 곳은 위 C 소비 11곳뿐이다; scratch `n17cls.py`).

## 구현 범위와 규약

- routing 13 범위(위 표). 짝수 PC 871개 중 block 시작 190, 내부 681. 내부 PC 직접 진입은 `unsupported animation objects n17 PC`다. 범위 이웃과 구멍은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. 산술은 원래 폭의 2의 보수·부호 확장으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다. 결과 flag는 같은 block 안의 Bcc만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 93 PC를 넣는다. 생산 block은 실행 뒤 known C를 둔다.
- 제어 이동은 모두 정적이다(`DBRA` 포함). 설치 값(`MOVE.L #imm,(A6)`, 부모 `(A0)`, `56(A6)`)은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. `28ae` 자식 대상(A0 = `7a516`/`7aa6e`)도 자료다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다.
- 스택: JSR 복귀 LONG만. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank): LONG `2000d4` → 노드 `22(A6)`(`7a3d2`), 이어서 `22(A6)` 기록의 LONG `2c`를 A1(애니메이션 목록)로 읽어 `49f8c`(D0.W = `100`, A0 = A6 + `26`)로 넘긴다. `7a4aa`는 LONG `2000d4`를 A1로 읽어 `cc778`(경계)로 넘긴다.
- [F] 고정 ROM 자료: 표 `7bce0`(결정 11, `7aaf6` LONG 읽기). 주소만 넘기는 것: 애니메이션 목록 `7c6b6`(`7a52a`) `7bd7c`(`7a65e`) `7c668`(`7aad0`), 사각형 `7bca0`(A0, `1ab02`), `7bc6c`(A0, `4b82e`), 표 `cb5ee`(`7aab2`) `cb650`(`7b1a2`) `cb848`(`7b0f8`)(A0, `490ba`), `cdef8`(A0, `cc778`), `28ae` 자식 대상 `7a516`(D0.W = `14`) `7aa6e`(D0.W = `a`).
- [F] work RAM(노드 A6): BYTE `14`(= `19`), `15`(bit 0: `7b034 BSET`, `7ab34`/`7ab3e` 부모 복사, `7a692` `7b1ae` 읽기; bit 7: `7b14e` `7b168` `7b182` `7b570` 읽기), `17`(= `ff`, 자식 `17` 복사), `5e`(CLR, `8e`로/에서 복사), `61`(bit 7: `7a398` `7ab76` 읽기, `7a426` BCLR), `8e`, `90`(1씩 증가, signed ≤ 6이면 Clear, 아니면 6·Set; `15` bit 7이면 0·Clear), `95`(부모 `95` 복사), `96`(TST, CLR), `98`(bit 0·5·6 설정·읽기, bit 1 설정·지움·읽기; `7afa6` CLR; 부모 `98` 복사; 자식 `98`에 복사); WORD `1e`/`68`(= `8820`), `20`(= `16b` `b` `d2`), `2c`(= `100`, `7b1be` 높이, 부모 `2c` 복사), `42`(signed 비교), `54`(= 1 또는 `490ba` 반환 D0.W), `70`(= 1), `76`(signed < 2 비교 → `49a58`; 0으로), `78`(→ `86`, TST, 0으로), `7a`(→ D0, `88`, 0으로), `7c`(→ `8a`, 0으로), `82`(`490ba` 반환 D0.W, `7a388` 1 감소), `86`(D0 인자), `88` `8a`; LONG `(A6)`(설치), `c`(부모 노드 포인터), `22`, `36`/`3a`(CLR; `3a`에 `ffffb000` 더함), `56`(CLR, = 0, `7b9xx` 설정), `64`(속도), `7a`(자식 노드 포인터: `7b0f8` 저장, `7b21c` `7b242` `7b268` 읽기), `76..9a`(`7a446` 반복 0).
- [F] 부모 노드(`c(A6)`, 자식 callback `7aae6`): BYTE `95` `98` `15`(bit 0) `61`(bit 7) 읽기, LONG `(A0)` = `7a3b2` 쓰기. 자식 노드(`7a(A6)`): BYTE `17` `98`(bit 1) 읽기, LONG `56`(TST) 읽기, BYTE `98` 쓰기(`7b0f8`, A0 = `28ae` 자식).
- [F] 상수 인자: `8ebe` D0.W/D1.B = `20d`/0, `c48`/0, `3c7`/0, `c46`/0, `c54`/0; `4a496` D0.W = `38c`/`171`; `4970a` D0.W/D1.W = 0/`18`(`7a4f4`), 0/0(`7b0ea`); `49290` D0.W/D1.W = 0/0; `4929e` D0.W = `86.W`, D1.W = 0; `cc778` A0/A1/D1.W/D2.W = `cdef8`/bank LONG/`b`/1.
- [I] 게임 의미: `7a53c`는 stage event로 나타나는 적 객체(인자 `76`~`7c`가 방향·높이·자식 유무 bit `98`을 정함)이고 `7b018`이 외형·소리를 고르고 `28ae`로 자식 `7aa6e`(부품)를 만든다. 자식 `7aae6`는 부모를 따라가며 부모 `95` 상태에 따라 애니메이션을 바꾸고, 자식이 파괴되면(`61` bit 7) 부모에 `7a3b2`(부품 잃은 상태)를 설치한다. `7a388`은 접촉(`4b54e`)과 화면 밖(`1ab02`) 판정 뒤 삭제 `7aa5e`를 설치하고, 파괴면 `7a476` 폭발 사슬로 간다. 확인하지 않았다.

## 의존·경계

- [F] N17 → 기존(모두 routing됨, 진입 case 있음): interpreter `49f8c` `49fc6`(C 반환; 표 callback으로 N17 `7b740`~`7b790`을 부름), U11 `4be06` `496c2`, U18 `4be2c`, U08b `4be34`, U17 `4bfa4` `4929e`, U12 `4c0ac` `490ba`, U08 `49274` `49290`, U20 `497a6`(C 반환), stage_area `49a58`, U14 `4a496`, N03 `4b82e`, N14 `4970a`, U01 `4b54e`(C 반환), U05 `1ab02`(C 반환), U02 `8ebe`, U13 `ea5f0`, fade_card `28ae`(C 반환) `2a00`(JMP), cleanup `2a24`(JMP) `43e34` `46ef4`, stage_event_ops `288c`(C 반환).
- [F] 실행부 없는 경계: `7a558` `7b8a8` `72f40` `7b834` `7b28e` `cc778`. 단위 test는 그 PC에서 stop만 확인한다(F4 test 경계 관례). rollback 탐침은 RAM `10fe00..10fefe`만 쓴다.
- [F] 다른 단위 → N17: stage event 표 `e8d2c`, interpreter 표 `4a500`(`4a708..4a718`), 범위 밖 미연결 코드의 `JSR`/`BRA`/설치(위 참조 목록).
- [F] N16·N18과 경계·범위가 겹치지 않는다. N16b는 대상 seed에 필요 없다("작업자 검증 기록").

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 190 시작 모두 typed fixture로 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 11개, 그 밖 Unknown), zero-step, 내부 681 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 소비 11곳의 Unknown carry 오류, 경계 stop. bank LONG과 `1ab02` 사각형은 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 소비자 C는 실제 생산자(`1ab02`, `28ae`, `4b54e`, `288c`, `497a6`, N17 helper)를 따라 들어간 fixture로 native 분기를 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(callback, 설치 상태, 실제 bank LONG·기록, 표 `7bce0`, 소비자 native 분기; `49fc6` → `7a414` 포함).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, 회귀 0, 대상 seed 완주 변화 기록.

## 작업자 검증 기록 (scratch)

- [F] 변경 파일: 새 `engine/src/animation_machine_objects_n17.cpp`(SHA256 `4a69904c310796b5e50cc9254888f1bdc5180ffc3b54fa8ef22f6781aea4f873`), 새 `engine/tests/animation_machine_objects_n17_test.cpp`(SHA256 `34d7a015bf24429af17ae0a0ba1f1a603f49ab5729c0b97ec6301706b1384d45`), 공유 최소 수정 `engine/src/animation_machine.cpp`(routing `else if` 1개 13 범위, carry 보존 case group 1개 93 PC; SHA256 `82c9af3f6fff4685d747e7837a29ebec0f293457571918952cefc36f7db85e00`), `engine/src/animation_machine_internal.h`(선언 1줄; SHA256 `c6f244eb7a77a45848a5a3249f5b500a3916c9cb7202a3ae47924415f755a751`), `Makefile`(source list·test target·run line; SHA256 `e31c83682712ba43f1f67fed3d6c84cc7cbb5e9405d7bb0bda5240cb293023cc`), `tools/verify_animation_machine.py`(SOURCES; SHA256 `d9ed11bb12e8974a6ba897975f5d4ee24192afb1aeeed5f3d01718aa7253f81a`). `animation_machine_interpreter.cpp`와 다른 단위 실행부는 고치지 않았다. 패치 파일 없음(결정 10).
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0. 새 test: `animation machine objects n17: 578 fixtures (20 checked errors, 210 kept C), 190 blocks, 2448 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen.py`, Unicorn + 합성 물리 바이트 `7bca0`(사각형) `7bce0`(16 LONG 표) `2000d4`(bank LONG → work RAM 기록 `10e600`), 표 SHA256 `50f32d3bd9bffc40f6b5d77ca5cc09633279ea6c7c07321a21ff50045ae4d839`): 190 시작 모두 fixture 진입 또는 경로로 덮임. 실제 생산자 추종 fixture: `4b54e`(`7a388` `7b200` → 소비자 `7b206`·`7a390`; `7ab4a` → `7ab5e`), `1ab02`(`7a3a2` `7a506` `7b7ae` `7b7c2`, 안/밖 → `7a3a6` `7a50a`), `28ae`(`7a4e0` `7b0d6`, 성공/실패; `4970a`→`49214`→`43e38`까지 따라가 `7a502`/`7b0f4` ORI 뒤 → 소비자 `7a4f0` `7b0e6`), `288c`(`7ab4a` `7abb0`, 부모 없음/`270e`/그 밖 → `7abb6`), `497a6`(`7b044`, `10fd92` = 0/≠0 → `7b04a`), N17 helper의 ORI/ANDI 결과 → 실제 소비자 `7a390` `7a3a6` `7a50a` `7a6c0`. block 표는 시작마다 incoming C clear/set의 native 후계·digest와 계약 C 분류, Unknown C는 소비 11곳에서 정확한 오류, zero-step 190×3, 내부 681 PC 정확한 오류, 홀수 PC(범위마다 양 끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`과 RTS 복귀 `10fe40`(17 fixture), routing 구멍의 도달 불가 `RTS` `7a4dc` `7aa64` `7aa6c`는 routing 밖, 경계·다른 단위 stop 21곳(`7a558` `7b8a8` `72f40` `7b834` `7b28e` `cc778`, `49f8c` `2a00` `2a24` `4970a` `4b82e` `49fc6` `4c0ac` `43e34` `49274` `49290` `4929e` `8ebe` `1ab02` `496c2` `46ef4`). checked 오류 fixture 9개(홀수 노드 읽기·쓰기, 홀수 부모 쓰기, `7a45a` 홀수 WORD 쓰기, ROM 부모·노드 읽기, 장치 쓰기, 스택 장치, RTS 장치). `DBRA` 반복은 18회 전체(`7a446`)와 1·2·3·6회(`7a45a` 직접)를 비교했다. 돌연변이 13개(signed `90` 비교, `42` BGE, `7a502` ORI, DBRA 종료값, `NEG.L`, `7a6ae` BGT, `7abb6` BCS 방향, `ADDI.L` 값, `7aaf6` 색인 배수, `7b7ae` signed 비교, `7a460` bit, 부모 설치 대상, `LSR.W` 폭)가 모두 test를 실패시켰다(scratch `mut/mut.out`).
- [F] 실제 ROM 차분(`realrom/real17.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, 무작위 work RAM, seed 1·2·3 각 1,500건): 불일치 0/0/0, 시작 도달 190/190/190. native stop은 STOP과 경계(`7a558` `7b8a8` `72f40` `7b834` `7b28e` `cc778`)·`2a00`·`2a24`. 실제 생산자 뒤 소비자 native 분기 비교(seed 1): `7a390` 198, `7a3a6` 193, `7a414` 61(`49fc6`), `7a4f0` 68, `7a50a` 139, `7a6c0` 106, `7ab5e` 61, `7abb6` 210, `7b04a` 53, `7b0e6` 139, `7b206` 222건. native가 깨끗이 멈추지 않은 입력(무작위 기록으로 interpreter·이동 helper가 낮은 PC로 감)은 건너뛰고 셌다(300/288/308건). 차분 harness 수정 1건: `7a554 BRA.W 7a558`은 다음 명령으로 가는 분기라 harness의 "직선 후속" 생략 규칙이 경계 `7a558`을 건너뛰었다(첫 실행 불일치 12/7/12건이 모두 이것). `7a558`을 명시 경계 stop으로 둔 뒤 0이다(C++ 실행부 변경 없음).
- [F] 자연 상태 차분(scratch `natural/natural17.py` `compare17.py`): RNG 초기화+응답 `80` 400 frame 선언 모델을 seed 76 77 98 99 104 105로 다시 돌려(pass 끝이 native seed 파일과 모두 같음) N17 callback 진입 상태 30개(seed마다 `7a53c` `7aa6e` `7aae6` `7aa5e` `7aa66` 1회)를 잡았다. 선언 host 변경(복귀 LONG = STOP) 뒤 native와 C++ 결과가 30/30 같다. `7aa5e`는 `2a00`, `7aa66`은 `2a24`, 나머지는 STOP으로 끝난다(`compare.log` SHA256 `fd1c26325bfc95c3b58e707185f3c02eecd62c0495285552f4529f5458637c10`). 자연 경로에서 interpreter 표 callback `7b74a`(`7a53c` 노드)·`7b790`(`7aa6e` 자식)이 `4a408` live target으로 실행된다.
- [F] 기준(`4a50832` `git archive` 사본 `ms5-scratch/n17/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 13,928·node 115,196, 불일치 0, 자연 완주 127. N17 뒤(이 작업 트리): 같은 값, 불일치 0, 회귀 0, 바뀐 seed 0(결과 `diff_results.json` SHA256 `5c9e2de678d9a7cbc1a7a31cc341f6a6f8064d26794fe29c2ca2511172e8714b`, 기준과 바이트까지 같음).
- [F] RNG 초기화 400 frame 차분: 기준 complete 118, 일치 pass 47,200·node 349,649, 불일치 0(verification.json SHA256 `071ba441a98b6ac5a524774ff5e21e92a5a95de58a65333aeb371a22dd6db038`). N17 뒤: **complete 124**(+76 77 98 99 104 105, 재범위 예측 124와 같음), 일치 pass 49,600·node 367,449, 불일치 0, 회귀 0, `other` 0, 도구 종료 0(SHA256 `cdaeaeee02780d99ff89770ae8b2b6e78eccb2f7319ec4ddc9f0f1d15cdbb757`; 두 번 실행해 같은 SHA, 프레임 패스 결과도 두 번 같음). 남은 `checked-current-first-unrouted-PC` 12 seed(6 7 12 13 32 33 38 39 42 43 116 117)는 기준과 같은 첫 미연결 callback(`dbe98` `dbf5e` `dcf56` `c3a7c` `736d2` `38ba0`)이다. N16b(`783ea`/`785f2`)는 대상 seed에 필요 없었다.
- [F] ROM SHA256·mtime 작업 전후 같음(`29112a94…`, `1791291625`).

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] 부모 설치 `7a3b2` 사슬(결정 2)과 표 callback `7b754`, 파괴 사슬 `7a476`~`7a53a`는 400 frame 두 기록에서 실행되지 않는다. typed fixture·실제 ROM 차분으로만 확인했다.
3. [U] 경계 `7a558`(`7a558..7a65a` 함수, 설치 `7a9fa` `7aa14`), `7b8a8` `72f40` `7b834` `7b28e`(재범위 단위표 밖), 고아 설치 `7a6ce` `7a964` `7abc2`와 hull 구멍 `7a9d6..7aa5e` `7b11a..7b140` `7b1da..7b200`의 동작은 해당 단위에서 정한다.
4. [U] 표 `7bce0` 뒤 9 LONG의 의미(결정 11).
5. [U] 미참조 함수 `7b75e` `7b768` `7b772` `7b77c` `7b79a` `7b7a4`의 용도(같은 꼴의 `56` 설정 함수; 표 `4a500`에 없음).

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n17/`(`n17.py` block·범위 계산(`N17EXTRA`로 결정 2·3 진입), `n17cls.py` carry 분류, `n17fmt.py` block 목록, `n17stat.py` 범위 SHA·짝수 PC, `n17xref.py` 범위 밖 참조, `n17seen.py` `n17who.py` 자연 도달, `unitdef.py`, `gen/` typed fixture 생성·test 조립, `mut/` 돌연변이, `realrom/` 실제 ROM 차분, `natural/` 자연 상태 차분, `fp/` 프레임 패스·RNG 차분; 저장소 밖).
