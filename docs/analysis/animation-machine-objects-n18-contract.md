# 객체 callback F4 N18: `8664c`/`8665a` 계열 객체(옛 U27/U28 일부) — 초기화 진입 `86642` `8664c` `8665a` `86664`, callback `86700` `8684e` `86f1c` `86f88` `8715e` `871c4`, 공용 꼬리 `8625a`(표 `862a0`), helper `864b6`, stage event callback `b630e`(`b6506` 자식 생성, 설치 `b65f0`)·자식 callback `b780c`(설치 `b7874`), stage event callback `dbe98`(설치 `dbebe`) 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N18 행(220 block, `8625a..86372` `864b6..868ea` `86f1c..86fca` `8715e..871ee` `b630e..b631c` `b6506..b660e` `b780c..b78b8` `dbe98..dbeec`, callback `8664c` `8665a` `86700` `8684e` `86f1c` `86f88` `8715e` `871c4` `b630e` `b65f0` `b780c` `b7874` `dbe98`, 경계 `868ea` `86c70` `cc778`, 표 `862a0`:27, bank 3, 미실행 설치 11(+182), 새 seed 6 7, 옛 U28 175·U27 156)과 메인 결정 1·2(이름 `objects-n18`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계)다. 단위 형식과 규약은 N16 계약(SHA256 `0fddf6a12152727e39d4c44adc40bcd4da23a801fc1a613a5c0f84adf317ef66`)을 따른다. 메인 작업 지시:
- flag 재계산은 선행이 유일할 때만(아니면 각 선행에 접어 넣음).
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 진입은 넣는다.
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가).
- 다른 단위 실행부(`animation_machine_interpreter.cpp` 포함)는 고치지 않는다. DIV 0 제수는 단위 checked 오류(N18에는 DIV가 없다).
- 표 `862a0`(재범위 추정 27 entry)은 정적으로 상한을 정하고 전부 옮긴다. 범위 안 설치·표 뒤 약 220 block을 넘으면 나누고, 목표 seed(6 7)가 쓰는 부분을 먼저 구현한다. N19가 `8625a..86372`를 함께 쓴다.

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, PC 상대 BRA.W 표 slot, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback과 `MOVEA.L #imm,A0`+`JSR 28ae` 자식 callback)로 정한다. fall-through로 이어지는 설치 대상도 시작으로 센다. 묶인 연속 Bcc는 없다. Unicorn TB 분할은 시작이 아니다.
- 결정 5(관례): 단위는 함수 본문 전체다(이번에는 아래 결정 1의 분할이 예외). 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N16 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`/`ADDQ`/`SUBQ`/`ANDI`/`ADD`/`SUB`/`NEG`/`LSL`/`LSR`/`ASR`/`EOR` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`ST`)과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`만인 block, callee C를 소비하는 Bcc block은 FLOW_ONLY다. checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N18 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`200140` `2001a8` `2001ac`)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n18`(HEAD `4a50832` = N15 + N16a까지 통합, `engine/src/animation_machine.cpp` SHA256 `b6a3ee0b66dd89ec8b2991c60d8d37e2fa8958cfb315b426e9cafabae3799937`, routing 규칙 73개, `engine/src/animation_machine_interpreter.cpp` SHA256 `bd2bffb36ccf99cc18fe141949335e6ef1e07f7255cb1f137e387d0451ebac05`)을 참조했다. N18 routing 범위의 짝수 PC는 기존 routing에 하나도 없다. `b630e..b631c`는 U19 `b6300..b630e`와 U18 `b631c..`, `b6506..`은 U19 `..b6506` 바로 뒤다(다시 routing하지 않는다). 동시에 진행하는 N17(`7a388..7a558` `7a65a..7a6ce` `7a9d6..7abc2` `7afa6..7b28e` `7b570..7b5a8` `7b740..7b7d4`)과 범위·경계가 겹치지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n18/n18.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **재범위 N18 행 8 범위의 정적 도달 전체는 224 block**(진입 `8664c` `8665a` `86700` `8684e` `86f1c` `86f88` `8715e` `871c4` `b630e` `b65f0` `b780c` `b7874` `dbe98`, helper `864b6`, 범위 안 설치 callback, 표 slot 27개, 아래 결정 2의 `86642` `86664` 포함)이다. 220을 넘으므로 메인 지시대로 나눈다(결정 1).
  - **N18(이 계약) = 196 block**, 코드 11 범위 1,988바이트, 444명령이다. routing 짝수 PC 994개 중 내부 PC 798개다.
  - **N19로 넘기는 28 block**: `86734`가 `MOVE.L #86742,(A6)` 뒤 fall-through로 들어가는 설치 callback `86742`의 본문 `86742..86814`(재범위 N19 행 범위 `86742..86814`와 같다). 목록은 "N19로 넘기는 block" 절.
- [F] 범위 안 미도달·미참조 코드는 routing하지 않는다(결정 4): `86348..8634e`(`86342 JMP cc778` 뒤 `RTS`, `BRA.W 86352`), `86560..86564`(`8655c BRA.W` 뒤 `BRA.W 86568`). 고정 ROM 전수 참조 검사(scratch `n18xref.py`)에서 둘 다 참조가 없다.
- [F] PC 상대 점프 표 1개(`86298 JMP 862a4(PC,D0.W)`, 결정 3). 미해독·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/MULx/DIVx·I/O port 쓰기·bank 변경·스택 직접 조작은 없다.
- [F] 진입:
  - stage event callback(고정 ROM LONG 표): `8665a`(`e8dd8`), `8664c`(`e8ddc`), `86664`(`e8de0`, 결정 2), `b630e`(`e8ed8`), `dbe98`(`dbef8`).
  - `28ae`/`2986` 자식 callback: `b780c`(범위 안 `b6526 MOVEA.L #b780c,A0`+`JSR 28ae`), `86642`(범위 밖 미연결 `c57a0 MOVEA.L #86642,A0`+`JSR 2986`, 결정 2).
  - 범위 안 설치 callback(결정 3 관례): `86700`(`871d4`), `8684e`(`86848`, fall-through), `86f1c`(`868e0` `871e4`), `86f88`(`86f7c`, fall-through), `8715e`(`86fc0`), `871c4`(`871be`, fall-through), `b65f0`(`b65da`, fall-through), `b7874`(`b786e`, fall-through), `dbebe`(`dbeaa`, fall-through).
  - 범위 밖 참조가 있는 분기 대상: `8625a`(공용 꼬리; 범위 밖 미연결 `BRA.W` 9곳 이상), `864b6`(helper; 범위 밖 미연결 `JSR (PC)` 9곳 이상), `86700`(범위 밖 설치 LONG 다수), `86f1c` `8715e`(범위 밖 설치 LONG), `b6506`(범위 밖 미연결 `b6350 BRA.W`), `b78a2`(범위 밖 미연결 `b7a1c BRA.W`).
- [F] **경계(실행부 없음)**: `cc778`(`86342 JMP`), `868ea`(`866fc BRA.W`), `86c70`(`866ea BRA.W`), N19로 넘기는 `86742`(`86734` fall-through). 모두 `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **범위 밖 설치 값(노드 LONG에 저장만)**: `86742`(N19), `86c70` `868ea`(경계로 바로 BRA), `86e76` `871ee` `86fca` `8698c`(`8684e` 계열), `b660e`(`b6604`), `b7742` `b78b8`(`b780c` 계열; `b7742`는 U18 고아 설치 대상과 같다).
- [F] **carry**(아래 "carry" 절):
  - 소비 block **7개**(BCC/BCS): `86260`(`4b54e`), `8635c`(`1ab02`), `871d0`(`49fc6`), `b6536`(`28ae`), `b6600`(`b7e5c`), `b7898 BCS`(`288c`), `b78ac`(`1aa7e`).
  - known 생산 block **1개**: Set `b6544`(`ORI.B #1,CCR`, 결정 5).
  - FLOW_ONLY 94개(소비 7 포함), Unknown 101개. 94 + 1 + 101 = 196.
- [F] 스택: JSR/BSR 복귀 LONG만 쓴다(`JSR (PC)` 4곳, `BSR.W` 1곳 포함).
- [F] 자료(모두 live bus): banked LONG `200140`(애니메이션 기록, id `e3`; `86324`는 A1로 `cc778`에 넘김), `2001a8`(id `1b3`), `2001ac`(id `1bb`)와 그 기록의 LONG. 고정 ROM 표: LONG `b7f04`+4·idx(`b6516`, idx 0..3 정적 상한), LONG `b7f2c`+sext(4·`8e`.W)(`b6566` `b65a2`), WORD `b7f14`+sext(2·`8e`.W)(`b780c`), 소리 표 `dbe6c`(노드 `76` 포인터로 WORD 2개씩). 주소만 넘기는 고정 ROM 자료: 사각형 `86252`(`1ab02`), `b7ef4`(`1aa7e`), `cdf30`(`cc778`). work RAM은 "자료" 절.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `n18seen.py`): RNG 400 frame 기록에서 seed 6 7 12 13만 N18 범위 PC를 실행한다. seed 6 7(각 seed): callback `8664c` 1, `86700` 1, `8684e` 70, `86f1c` 1, `86f88` 8, `8715e` 1, `871c4` 4, `b630e` 2, `b65f0` 170, `b780c` 8, `b7874` 680, `dbe98` 86회. seed 12 13: `8665a` 1, `86700` 1, `86742`(N19) 74, `86f1c` 1, `86f88` 4, `8715e` 1, `871c4` 4. base 120 frame 기록에서는 seed 6 7이 같은 수, seed 12 13은 `8665a` 1회다. N18 범위의 자연 TB 시작은 N19로 넘기는 `86742..86810` 7개를 빼면 모두 이 계약의 시작이다. 경계 `cc778` `868ea` `86c70`은 자연 실행되지 않는다.
- [F] **새 완주 seed 6 7(재범위 행과 같음, 아래 검증 기록)**. 기준 `4a50832`에서 seed 6 7은 frame 0 `dbe98`에서, 12 13은 `8665a`에서 멈춘다(RNG 기록 `checked-current-first-unrouted-PC`).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **분할: N18 = 196 block, `86742..86814` 28 block은 N19로.** [F] 재범위 8 범위의 정적 도달 전체(범위 안 설치·표 slot·결정 2 진입 포함)는 224 block이다. 메인 지시(약 220 초과 시 분할, 목표 seed 우선)와 재범위 N19 행(범위 `86742..86814`, callback `86742`)에 맞춰 설치 callback `86742`의 본문(`92` ≠ 0 상태, seed 12 13 전용)을 N19로 넘긴다. seed 6 7의 자연 경로는 `86700`→`86708`(`92` = 0)→`86814`→`8684e`라 `86742`를 쓰지 않는다. `8670c`/`86734`(`86700`의 `92` ≠ 0 갈래, 설치 `86742`까지)는 `86700` 함수 본문이라 N18에 남긴다. N19는 `86742..86814`만 routing하면 되고 N18 block을 다시 나누지 않는다(`86734`의 fall-through 대상이 이미 경계 PC다). [I] 대안: 224 block 전부를 N18에 넣으면 N19가 28 block 줄어든다.
2. **참조된 범위 안 진입 `86642` `86664` 포함(+2 block).** [F] `86642 MOVE.W #4,92(A6); BRA.W 8666e`와 `86664 MOVE.W #2,92(A6); BRA.W 8666e`는 앞 `RTS`/`BRA.W` 뒤라 범위 안 진입에서 도달하지 않지만, `86664`는 stage event 표 LONG `e8de0`(이웃 `e8dd8`=`8665a`, `e8ddc`=`8664c`), `86642`는 범위 밖 미연결 `c57a0 MOVEA.L #86642,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986`(자식 callback)의 대상이다. 나중 단위가 N18 범위 안을 다시 routing하지 않도록 지금 시작으로 넣는다(N16 결정 2 `7957a` 선례). 빼면 194 block이고 두 PC는 routing 구멍이다.
3. **표 `862a0`: 27 slot, 계산 PC.** [F] `8628c MOVE.B 5e(A6),D0; CMPI.B #1b,D0; BCC.W 8631a`가 무부호 `5e.B < 1b`만 `86298`로 보낸다. `86298 ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0; JMP 862a4(PC,D0.W)`이므로 자연 index는 0..26, slot은 `862a4`+4·k(k = 0..26, `862a4..8630c`, 각 `BRA.W` 4바이트)다. 27 slot을 모두 block 시작(FLOW)으로 옮긴다: k = 2 3 6 15 → `86310`(`5e` 지움, `61` bit 7 지움), 나머지 23개 → `8631a`. F1 메인 결정 3(stage catalog `478a8` 선례)대로 `86298`은 상한 검사 없이 PC = `862a4` + sext(`D0.W`)로 옮긴다. `86298`로 바로 들어온 typed 입력에서 `D0.B ≥ 1b`이면 대상은 `862a4..866a0`의 4의 배수 주소다: `86310`(k = 27)은 block 시작, 그 밖 N18 범위 안 주소는 내부 PC(`unsupported animation objects n18 PC`), routing 밖(`86348`, `86372..864b6`)은 `unsupported animation machine PC`다(전체 rollback). [I] 원본은 `8628c`를 거치지 않으면 범위 밖 대상으로 뛴다.
4. **routing 구멍.** [F] 범위 안 미도달 코드(`86348..8634e`, `86560..86564`)는 routing하지 않는다(N03·N11~N16 선례). routing 범위는 도달 명령의 연속 구간 11개다("원본 바이트 근거" 표).
5. **`b6544 ORI.B #1,CCR`은 Set 생산(소비자 없음).** [F] `28ae` 성공(Set) 뒤 `b653a CLR.W D0; CLR.W D1; JSR 4970a` 다음 `b6544 ORI.B #1,CCR`이 C = 1을 만들고 `b6548`로 fall-through한다. `b6548`은 `MOVE.W`/`SUBQ.W`가 C를 덮어 소비하지 않는다(carry 보존 목록 밖이라 진입에서 Unknown이 된다). N16 결정 5(`78c96`)·N14 결정 2 선례대로 같은 명령은 Set으로 둔다. [I] 대안: N15 `76f50` `76f92`처럼 Unknown(관찰 차이는 한 block 단위 test의 C뿐).
6. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n18.cpp`의 `animation_objects_n18_block`. 오류는 `unsupported animation objects n18 PC`(내부 PC), `objects n18 caller requires known carry`(소비 7 block). 메인 지시와 같다.
7. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`·`engine/src`에서 N18 range(N19로 넘기는 부분 포함)의 PC를 경계·rollback 탐침으로 쓰는 곳은 없다. U19 test의 `RANGES` 끝값 `b630e` `b6506`은 홀수 PC 탐침(`b630d` `b6505`, "unaligned")에만 쓰여 영향이 없다. U18 test의 `b631c`는 U18 자신의 시작이다.
8. **interpreter·다른 실행부의 두 번째 진입 누락 없음.** [F] N18이 부르는 다른 단위 진입(`4b54e` `1aa7e`(U01), `1ab02` `c6a96`(U05), `28ae` `2a00`(fade_card), `288c` `49a84`(stage_event_ops), `49f8c` `49fc6`(interpreter), `49370` `4be06`(U11), `4a496`(U14), `4c1de` `4c29a`(U15), `4be34`(U08b), `49290`(U08), `8ebe`(U02), `43e34`(cleanup), `3af8`(sound), `4814e`(stage_catalog), `4970a`(N14), `b7bc2` `b7e5c` `b76d2`(U18))는 모두 기존 실행부의 case로 시작한다(scratch routing 검사). 패치 파일은 없다.

## 원본 바이트 근거

[F] 코드 11 범위 합계 1,988바이트. 범위 순서로 이어 붙인 SHA256 `e2cda748a9aed3e712069575f2b13bdee71a47f539f710764a789ab55f70f3f5`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `8625a..86348` | 238 | `af7ee504c0eb465505068c046eb2f66aa861f03eb318d73f60433f06392a9566` | 39 |
| `8634e..86372` | 36 | `1c5e7dcdd2d448390061fa13607e5c6844fdf7d71b69c51f91b3d0bea9e26b09` | 5 |
| `864b6..86560` | 170 | `ec021b33e47aa0f98f1a8995410d1dfac4f94cbea38e1cb4cffa57cadd9280fb` | 19 |
| `86564..86742` | 478 | `8b1d8d2469aade22f8d3846fcc9f2a696451f661257568a0d3c50c460e3272fc` | 41 |
| `86814..868ea` | 214 | `96c03c8e415d4dd6cac444d70cef19a8fa39fdbd4c005d45bc1a7624ca8aae3f` | 23 |
| `86f1c..86fca` | 174 | `85302741d813bb385ca5c2f94fb66651906d824bf18bce235214e3148a99718c` | 11 |
| `8715e..871ee` | 144 | `9ff57d2b1357043c77e6fb544918d64b3aea0b9b44c5b56ab6b02af4f9252bdb` | 12 |
| `b630e..b631c` | 14 | `58bfcdf6029ad3f806680bfb37acbededf05a89c96f47ee567b35d835623789e` | 2 |
| `b6506..b660e` | 264 | `353ce5128bcf1519c0e407252c158d2d2eaea28aa448d53d683c0dd136db173a` | 19 |
| `b780c..b78b8` | 172 | `5c66f09933078921a6dfd594ea3508acec91a54a19c887ce09845a1bfc48ee98` | 15 |
| `dbe98..dbeec` | 84 | `07a09d66a7bdd2fe05d72ba5fad16ce058974d81239f771bafb5ad8703196534` | 10 |

- [F] 범위 밖 이웃(모두 미연결, `unsupported animation machine PC`): `86252..8625a`(사각형 자료 `ffe0 fff0 0040 0040`, `1ab02` 인자), 구멍 `86348..8634e`(결정 4), `86372..864b6`(다른 함수 `86372` `863e0` `86474`; 범위 밖 설치 LONG의 대상, 재범위 어느 단위에도 없음), 구멍 `86560..86564`, `86742..86814`(N19, 결정 1), `868ea..86f1c`(경계 `868ea` `86c70`, 고아 설치 `8698c` `86e76` 등), `86fca..8715e`(고아 설치 `86fca`), `871ee..`(고아 설치 `871ee`), `b630c`(U19 `b6300..b630e`) / `b631c`(U18 시작), `b6504`(U19 끝), `b660e..`(고아 설치 `b660e`), `b780a`, `b78b8..`(고아 설치 `b78b8`), `dbe96`(앞 함수 끝 `dbe6c` 표 자료 `..dbe96`), `dbeec..dbefe`(stage event 표 LONG `dbef8` = `dbe98`, U19 `dbefe` 앞).
- [F] 범위 밖 → N18 참조(scratch `n18xref.py`, 고정 ROM 전수: LONG 값, Bcc/BRA/BSR 변위, `JSR`/`JMP`/`LEA (PC)`): `8625a`(`BRA.W` 9곳 이상: `86988` `86ad2` `86b80` `86c6c` `86d08` `86e72` `86f18` `87090` `8715a`, 모두 미연결), `864b6`(`JSR (PC)` `86a1e` `86b3c` `86bc6` `86d9e` `86ee4` `87052` `8711c` `872dc`, 미연결), `86642`(`c57a2` LONG = `MOVEA.L #imm,A0` 즉치), `8664c` `8665a` `86664`(`e8ddc` `e8dd8` `e8de0` stage event 표), `86700`(설치 LONG 10곳 이상), `86800`·`86600`(N19 쪽 / LONG 값 우연 일치), `86f1c`(설치 LONG 9곳 이상), `8715e`(`8708c` `87156` 설치), `b630e`(`e8ed8`), `b6506`(`b6350 BRA.W`, 미연결), `b6600`(LONG 값 우연 일치 `20914` `70a2c` `e8be4`), `b78a2`(`b7a1c BRA.W`, 미연결), `dbe98`(`dbef8`). 모두 block 시작으로 간다. 내부 PC와 같은 값(`86340` `864d2` `86500` `865e2` `865f0` `86636` `866e6` `86f34` `b65e0` 등)은 다른 명령의 즉치·변위 바이트나 자료의 우연 일치다(대상이 명령 중간이거나 참조 위치가 명령 경계가 아니다). 범위 밖 참조 위치는 모두 routing되지 않은 코드다.
- [F] 범위 안 고정 ROM 자료는 없다(표 `862a0`의 slot은 코드다).

## block 목록과 실행 의미

[F] 196 block. 각 줄은 block 안 명령 전체다(capstone 표기, 즉치·주소 16진). "(→x)"는 fall-through다. 태그: "C 소비"(Unknown이면 checked 오류), "Set 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)은 부호확장한다(`-7348(A5)` = A5 − `7348` = `100cb8`, `-7258(A5)` = `100da8`). `(An,Dn.W)`/`(PC,Dn.W)` index는 `Dn.W` 부호확장이다. `.B`/`.W` 연산은 나머지 bit를 보존한다(`MOVE.W #x,Dn`·`CLR.W Dn`·`NEG.W`·`ADD.W`·`SUBQ.W`·`LSL.W`/`LSR.W`는 하위 WORD만, `MOVE.B`·`SPL.B`/`SNE.B`·`EOR.B`는 하위 BYTE만). `MOVEQ`는 LONG 전체, `MOVEA.W #0,A0`는 부호확장 LONG(`A0` = 0)이다. `SUB.L`/`ADD.L`은 32-bit 2의 보수, `ASR.L #5`는 부호 bit 채움 산술 shift다. 비교 분기: `BCC`/`BCS`(무부호 ≥ / <; `CMPI.B #1b,D0`, `CMPI.W #100,D0`, `CMPI.W #4,D0`, `CMP.W D0,D1`은 무부호), `BLE`/`BGE`(부호 있는 비교; `CMP.W 8a(A6),D0; BLE`는 signed `D0.W ≤ 8a.W`, `CMP.W 8c(A6),D0; BLE`는 signed `D0.W ≤ 8c.W`, `CMPI.W #280,5418(A5); BGE`는 signed `5418.W ≥ 280`), `BPL`/`BMI`(결과 최상위 bit; `SUB.W; BPL`은 차의 bit 15, `TST.B; BMI`는 BYTE bit 7, `EOR.B D0,D1; BMI`는 결과 bit 7), `BEQ`/`BNE`(0 여부), `SUBQ.W #1,x; BCC`(빌림 없음 = 감소 전 값 ≠ 0). `SPL.B D0`은 `CMP.W` 결과(N = 0)면 `D0.B = ff` 아니면 0, `SNE.B D1`은 `BTST` 결과(Z = 0, 즉 bit = 1)면 `ff` 아니면 0이다. `BTST.B #n,Dn`은 `Dn`의 bit n이다. `BTST`/`BSET`/`BCLR`는 Z만 쓰고, `BSET`/`BCLR`는 대상 BYTE bit만 바꾼다. `MOVE.L 200140.l,22(A6)` 등은 bank window LONG을 live bus로 읽는다. [F] `865ae`의 `CMPI.W #c0,D0` 뒤에는 분기가 없어 `BSET.B #3,84(A6)`이 항상 실행된다(원본 그대로).

**공용 꼬리 `8625a`(`4b54e` 정지 판정, `5e` 표 `862a0`, 파괴 `86324`, `1ab02` 화면 밖 삭제) 44**
- `8625a`: `JSR 4b54e.l` — FLOW
- `86260`: `BCC.W 86352` (→`86264`) — C 소비
- `86264`: `TST.B 94(a6); BEQ.W 8631a` (→`8626c`)
- `8626c`: `TST.B 5f(a6); BMI.W 86282` (→`86274`)
- `86274`: `BTST.B #0, 15(a6); BNE.W 8631a` (→`8627e`) — FLOW
- `8627e`: `BRA.W 8628c` — FLOW
- `86282`: `BTST.B #0, 15(a6); BEQ.W 8631a` (→`8628c`) — FLOW
- `8628c`: `MOVE.B 5e(a6), d0; CMPI.B #1b, d0; BCC.W 8631a` (→`86298`)
- `86298`: `ANDI.W #ff, d0; ADD.W d0, d0; ADD.W d0, d0; JMP 862a4(pc, d0.w)`
- `862a4`: `BRA.W 8631a` — FLOW
- `862a8`: `BRA.W 8631a` — FLOW
- `862ac`: `BRA.W 86310` — FLOW
- `862b0`: `BRA.W 86310` — FLOW
- `862b4`: `BRA.W 8631a` — FLOW
- `862b8`: `BRA.W 8631a` — FLOW
- `862bc`: `BRA.W 86310` — FLOW
- `862c0`: `BRA.W 8631a` — FLOW
- `862c4`: `BRA.W 8631a` — FLOW
- `862c8`: `BRA.W 8631a` — FLOW
- `862cc`: `BRA.W 8631a` — FLOW
- `862d0`: `BRA.W 8631a` — FLOW
- `862d4`: `BRA.W 8631a` — FLOW
- `862d8`: `BRA.W 8631a` — FLOW
- `862dc`: `BRA.W 8631a` — FLOW
- `862e0`: `BRA.W 86310` — FLOW
- `862e4`: `BRA.W 8631a` — FLOW
- `862e8`: `BRA.W 8631a` — FLOW
- `862ec`: `BRA.W 8631a` — FLOW
- `862f0`: `BRA.W 8631a` — FLOW
- `862f4`: `BRA.W 8631a` — FLOW
- `862f8`: `BRA.W 8631a` — FLOW
- `862fc`: `BRA.W 8631a` — FLOW
- `86300`: `BRA.W 8631a` — FLOW
- `86304`: `BRA.W 8631a` — FLOW
- `86308`: `BRA.W 8631a` — FLOW
- `8630c`: `BRA.W 8631a` — FLOW
- `86310`: `CLR.B 5e(a6); BCLR.B #7, 61(a6)` (→`8631a`)
- `8631a`: `BTST.B #7, 61(a6); BEQ.W 8634e` (→`86324`) — FLOW
- `86324`: `CLR.B 17(a6); MOVE.B #ff, 17(a6); LEA.L cdf30.l, a0; MOVEA.L 200140.l, a1; MOVE.W #e3, d1; MOVE.W #5, d2; JMP cc778.l`
- `8634e`: `CLR.B 5e(a6)` (→`86352`)
- `86352`: `LEA.L 86252(pc), a0; JSR 1ab02.l` — FLOW
- `8635c`: `BCC.W 86370` (→`86360`) — C 소비
- `86360`: `BSET.B #7, 61(a6); CLR.W 54(a6); JMP 2a00.l`
- `86370`: `RTS` — FLOW

**helper `864b6`(대상 player 선택·주변 판정 `84` bit) 43**
- `864b6`: `JSR 49370.l` — FLOW
- `864bc`: `TST.B d0; BNE.W 864d0` (→`864c2`)
- `864c2`: `MOVE.B #ff, 85(a6); MOVEA.W #0, a0; BRA.W 8658a`
- `864d0`: `CMPI.B #1, d0; BNE.W 864e6` (→`864d8`)
- `864d8`: `MOVE.B #0, 85(a6); LEA.L -7348(a5), a0; BRA.W 86568`
- `864e6`: `CMPI.B #2, d0; BNE.W 864fc` (→`864ee`)
- `864ee`: `MOVE.B #1, 85(a6); LEA.L -7258(a5), a0; BRA.W 86568`
- `864fc`: `LEA.L -7348(a5), a0; LEA.L -7258(a5), a1; MOVE.W 42(a0), d0; MOVE.W 42(a1), d1; MOVE.W 42(a6), d2; SUB.W d2, d0; BPL.W 86518` (→`86516`)
- `86516`: `NEG.W d0` (→`86518`)
- `86518`: `SUB.W d2, d1; BPL.W 86520` (→`8651e`)
- `8651e`: `NEG.W d1` (→`86520`)
- `86520`: `TST.B 85(a6); BNE.W 86530` (→`86528`)
- `86528`: `LSR.W #2, d0; LSL.W #4, d1; BRA.W 86534`
- `86530`: `LSL.W #4, d0; LSR.W #2, d1` (→`86534`)
- `86534`: `ADD.W d1, d0; JSR 49a84.l`
- `8653c`: `MOVEQ #0, d7; CMP.W d0, d1; BCC.W 8654a` (→`86544`)
- `86544`: `MOVEA.L a1, a0; MOVEQ #1, d7; MOVE.W d1, d0` (→`8654a`)
- `8654a`: `CMP.W 8a(a6), d0; BLE.W 86564` (→`86552`)
- `86552`: `MOVE.B #ff, 85(a6); MOVEA.W #0, a0; BRA.W 8658a`
- `86564`: `MOVE.B d7, 85(a6)` (→`86568`)
- `86568`: `CLR.B 84(a6); MOVE.W 42(a0), d0; CMP.W 42(a6), d0; SPL.B d0; BTST.B #0, 15(a6); SNE.B d1; EOR.B d0, d1; BMI.W 8658a` (→`86584`)
- `86584`: `BSET.B #0, 84(a6)` (→`8658a`) — FLOW
- `8658a`: `MOVE.W 8e(a6), d0; BEQ.W 86598` (→`86592`)
- `86592`: `SUBQ.W #1, d0; MOVE.W d0, 8e(a6)` (→`86598`)
- `86598`: `BCLR.B #3, 84(a6); MOVE.W 42(a6), d0; SUBI.W #20, d0; CMPI.W #100, d0; BCC.W 865c0` (→`865ae`)
- `865ae`: `MOVE.W 46(a6), d0; SUBI.W #20, d0; CMPI.W #c0, d0; BSET.B #3, 84(a6)` (→`865c0`)
- `865c0`: `MOVEQ #0, d0; MOVE.W #20, d1; MOVE.W #10, d2; MOVE.W #24, d3; BTST.B #0, 15(a6); BNE.W 865da` (→`865d8`)
- `865d8`: `NEG.W d2` (→`865da`)
- `865da`: `JSR 4c29a.l` — FLOW
- `865e0`: `BTST.B #3, d6; BEQ.W 865f2` (→`865e8`) — FLOW
- `865e8`: `BSET.B #1, 84(a6); BRA.W 8660e` — FLOW
- `865f2`: `BTST.B #6, d6; BEQ.W 86600` (→`865fa`) — FLOW
- `865fa`: `BSET.B #4, 84(a6)` (→`86600`) — FLOW
- `86600`: `BTST.B #2, d6; BEQ.W 8660e` (→`86608`) — FLOW
- `86608`: `BSET.B #5, 84(a6)` (→`8660e`) — FLOW
- `8660e`: `MOVE.W #8, d0; BTST.B #0, 15(a6); BNE.W 8661e` (→`8661c`)
- `8661c`: `NEG.W d0` (→`8661e`)
- `8661e`: `JSR 4c1de.l` — FLOW
- `86624`: `BTST.B #2, d6; BEQ.W 86632` (→`8662c`) — FLOW
- `8662c`: `BSET.B #2, 84(a6)` (→`86632`) — FLOW
- `86632`: `BTST.B #0, d6; BNE.W 86640` (→`8663a`) — FLOW
- `8663a`: `BSET.B #7, 84(a6)` (→`86640`) — FLOW
- `86640`: `RTS` — FLOW

**초기화 진입 `86642` `8664c` `8665a` `86664`와 공통 초기화 `8666e` 13**
- `86642`: `MOVE.W #4, 92(a6); BRA.W 8666e`
- `8664c`: `ST.B 94(a6); MOVE.W #0, 92(a6); BRA.W 8666e`
- `8665a`: `MOVE.W #1, 92(a6); BRA.W 8666e`
- `86664`: `MOVE.W #2, 92(a6); BRA.W 8666e`
- `8666e`: `MOVE.L #28000, 86(a6); MOVE.W 78(a6), 8a(a6); MOVE.W 7a(a6), 90(a6); MOVE.W 7c(a6), 8e(a6); MOVE.W 7e(a6), 8c(a6); MOVE.W #4f, d0; MOVE.W #1, d1; MOVE.B #0, d2; JSR c6a96.l`
- `866a0`: `MOVE.W #c8e, d0; JSR 4a496.l`
- `866aa`: `MOVE.B 19(a6), 14(a6); MOVE.W #8820, 68(a6); MOVE.W #8820, 1e(a6); MOVE.W #28, 54(a6); TST.W 76(a6); BNE.W 866d0` (→`866ca`)
- `866ca`: `BSET.B #0, 15(a6)` (→`866d0`) — FLOW
- `866d0`: `JSR 864b6(pc)` — FLOW
- `866d4`: `CMPI.W #4, 92(a6); BNE.W 866ee` (→`866de`)
- `866de`: `MOVE.W #1, 92(a6); MOVE.L #86c70, (a6); BRA.W 86c70`
- `866ee`: `TST.W 80(a6); BEQ.W 86700` (→`866f6`)
- `866f6`: `MOVE.L #868ea, (a6); BRA.W 868ea`

**callback `86700`(`92` 분기; `86742`는 N19 경계) 4**
- `86700`: `TST.W 92(a6); BNE.W 8670c` (→`86708`)
- `86708`: `BRA.W 86814` — FLOW
- `8670c`: `LEA.L 26(a6), a0; MOVE.W #e3, 20(a6); MOVE.L 200140.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 4(a1), a1; JSR 49f8c.l`
- `86734`: `MOVE.L #0, 64(a6); MOVE.L #86742, (a6)` (→`86742`)

**`86814`/callback `8684e`(`92` = 0 상태) 23**
- `86814`: `MOVE.L #0, 64(a6); ST.B 94(a6); LEA.L 26(a6), a0; MOVE.W #e3, 20(a6); MOVE.L 200140.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 40(a1), a1; JSR 49f8c.l`
- `86848`: `MOVE.L #8684e, (a6)` (→`8684e`)
- `8684e`: `JSR 864b6(pc)` — FLOW
- `86852`: `JSR 4be06.l` — FLOW
- `86858`: `JSR 49fc6.l` — FLOW
- `8685e`: `TST.B 85(a6); BMI.W 868d6` (→`86866`)
- `86866`: `BTST.B #0, 84(a6); BNE.W 8687a` (→`86870`) — FLOW
- `86870`: `MOVE.L #86e76, (a6); BRA.W 868d6`
- `8687a`: `TST.W 8e(a6); BNE.W 86892` (→`86882`)
- `86882`: `BTST.B #3, 84(a6); BEQ.W 86892` (→`8688c`) — FLOW
- `8688c`: `MOVE.L #871ee, (a6)` (→`86892`)
- `86892`: `TST.B 85(a6); BNE.W 868a2` (→`8689a`)
- `8689a`: `LEA.L -7348(a5), a0; BRA.W 868a6` — FLOW
- `868a2`: `LEA.L -7258(a5), a0` (→`868a6`) — FLOW
- `868a6`: `MOVE.W 42(a0), d0; SUB.W 42(a6), d0; BPL.W 868b4` (→`868b2`)
- `868b2`: `NEG.W d0` (→`868b4`)
- `868b4`: `CMP.W 8c(a6), d0; BLE.W 868d6` (→`868bc`)
- `868bc`: `BTST.B #7, 84(a6); BEQ.W 868d0` (→`868c6`) — FLOW
- `868c6`: `MOVE.L #86fca, (a6); BRA.W 868d6`
- `868d0`: `MOVE.L #8698c, (a6)` (→`868d6`)
- `868d6`: `BTST.B #7, 15(a6); BNE.W 868e6` (→`868e0`) — FLOW
- `868e0`: `MOVE.L #86f1c, (a6)` (→`868e6`)
- `868e6`: `BRA.W 8625a` — FLOW

**callback `86f1c`(설치 `86f88`) 11**
- `86f1c`: `CLR.B 94(a6); MOVE.W 92(a6), d0; BNE.W 86f54` (→`86f28`)
- `86f28`: `LEA.L 26(a6), a0; MOVE.W #e3, 20(a6); MOVE.L 200140.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L a8(a1), a1; JSR 49f8c.l`
- `86f50`: `BRA.W 86f7c` — FLOW
- `86f54`: `LEA.L 26(a6), a0; MOVE.W #e3, 20(a6); MOVE.L 200140.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 10(a1), a1; JSR 49f8c.l`
- `86f7c`: `MOVE.L 64(a6), 36(a6); MOVE.L #86f88, (a6)` (→`86f88`)
- `86f88`: `JSR 864b6(pc)` — FLOW
- `86f8c`: `MOVE.L 64(a6), d0; SUB.L 36(a6), d0; ASR.L #5, d0; ADD.L d0, 36(a6); MOVE.L #fff00000, d0; SUB.L 3a(a6), d0; ASR.L #5, d0; ADD.L d0, 3a(a6); JSR 4be34.l`
- `86fb0`: `JSR 49fc6.l` — FLOW
- `86fb6`: `BTST.B #7, 15(a6); BEQ.W 86fc6` (→`86fc0`) — FLOW
- `86fc0`: `MOVE.L #8715e, (a6)` (→`86fc6`)
- `86fc6`: `BRA.W 8625a` — FLOW

**callback `8715e`(설치 `871c4`) 12**
- `8715e`: `CLR.B 94(a6); MOVE.W 92(a6), d0; BNE.W 87196` (→`8716a`)
- `8716a`: `LEA.L 26(a6), a0; MOVE.W #e3, 20(a6); MOVE.L 200140.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L ac(a1), a1; JSR 49f8c.l`
- `87192`: `BRA.W 871be` — FLOW
- `87196`: `LEA.L 26(a6), a0; MOVE.W #e3, 20(a6); MOVE.L 200140.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 14(a1), a1; JSR 49f8c.l`
- `871be`: `MOVE.L #871c4, (a6)` (→`871c4`)
- `871c4`: `JSR 4be06.l` — FLOW
- `871ca`: `JSR 49fc6.l` — FLOW
- `871d0`: `BCC.W 871da` (→`871d4`) — C 소비
- `871d4`: `MOVE.L #86700, (a6)` (→`871da`)
- `871da`: `BTST.B #7, 15(a6); BNE.W 871ea` (→`871e4`) — FLOW
- `871e4`: `MOVE.L #86f1c, (a6)` (→`871ea`)
- `871ea`: `BRA.W 8625a` — FLOW

**stage event callback `b630e` 2**
- `b630e`: `MOVE.W #0, 8e(a6); BSR.W b7bc2`
- `b6318`: `BRA.W b6506` — FLOW

**`b6506`(자식 `b780c` 생성 반복, 설치 `b65f0`) 19**
- `b6506`: `MOVE.W 78(a6), d0; CMPI.W #4, d0; BCS.W b6516` (→`b6512`)
- `b6512`: `MOVE.W #3, d0` (→`b6516`)
- `b6516`: `MOVE.W d0, 78(a6); LEA.L b7f04(pc), a0; LSL.W #2, d0; MOVE.L (a0, d0.w), 56(a6)` (→`b6526`)
- `b6526`: `MOVEA.L #b780c, a0; MOVE.W #14, d0; JSR 28ae.l`
- `b6536`: `BCC.W b6548` (→`b653a`) — C 소비
- `b653a`: `CLR.W d0; CLR.W d1; JSR 4970a.l`
- `b6544`: `ORI.B #1, ccr` (→`b6548`) — Set 생산
- `b6548`: `MOVE.W 8e(a6), 8e(a0); MOVE.W 78(a6), 78(a0); SUBQ.W #1, 78(a6); BCC.B b6526` (→`b655a`)
- `b655a`: `MOVE.W 8e(a6), d0; CMPI.W #0, d0; BNE.W b65a2` (→`b6566`)
- `b6566`: `LEA.L 26(a6), a0; MOVE.W #1b3, 20(a6); MOVE.L 2001a8.l, 22(a6); MOVEA.L #b7f2c, a1; ADD.W d0, d0; ADD.W d0, d0; MOVE.L (a1, d0.w), d0; MOVEA.L 2001a8.l, a1; ADD.W d0, d0; ADD.W d0, d0; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b659e`: `BRA.W b65da` — FLOW
- `b65a2`: `LEA.L 26(a6), a0; MOVE.W #1bb, 20(a6); MOVE.L 2001ac.l, 22(a6); MOVEA.L #b7f2c, a1; ADD.W d0, d0; ADD.W d0, d0; MOVE.L (a1, d0.w), d0; MOVEA.L 2001ac.l, a1; ADD.W d0, d0; ADD.W d0, d0; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b65da`: `MOVE.L #0, 96(a6); MOVE.L #18, 98(a6); MOVE.L #b65f0, (a6)` (→`b65f0`)
- `b65f0`: `JSR 43e34.l` — FLOW
- `b65f6`: `JSR 49fc6.l` — FLOW
- `b65fc`: `JSR b7e5c(pc)` — FLOW
- `b6600`: `BCC.W b660a` (→`b6604`) — C 소비
- `b6604`: `MOVE.L #b660e, (a6)` (→`b660a`)
- `b660a`: `BRA.W b76d2` — FLOW

**자식 callback `b780c`(설치 `b7874`) 15**
- `b780c`: `MOVE.W 8e(a6), d0; LEA.L b7f14(pc), a0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; MOVE.B #0, d1; JSR 8ebe.l`
- `b7824`: `SUBQ.W #1, 1e(a6); MOVEA.L c(a6), a0; MOVE.W 12(a0), 12(a6); MOVE.W 78(a6), d0; LSL.W #4, d0; MOVE.W d0, d1; ADD.W d1, d0; ADD.W d0, d1; CLR.W d0; JSR 49290.l`
- `b7846`: `LEA.L 26(a6), a0; MOVE.W #1b3, 20(a6); MOVE.L 2001a8.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L c(a1), a1; JSR 49f8c.l`
- `b786e`: `MOVE.L #b7874, (a6)` (→`b7874`)
- `b7874`: `JSR 43e34.l` — FLOW
- `b787a`: `JSR 49fc6.l` — FLOW
- `b7880`: `MOVEA.L c(a6), a0; TST.B 5e(a0); BEQ.W b7892` (→`b788c`)
- `b788c`: `MOVE.L #b78b8, (a6)` (→`b7892`)
- `b7892`: `JSR 288c.l` — FLOW
- `b7898`: `BCS.W b78a2` (→`b789c`) — C 소비
- `b789c`: `MOVE.L #b7742, (a6)` (→`b78a2`)
- `b78a2`: `LEA.L b7ef4(pc), a0; JSR 1aa7e.l` — FLOW
- `b78ac`: `BCC.W b78b6` (→`b78b0`) — C 소비
- `b78b0`: `MOVE.L #b7742, (a6)` (→`b78b6`)
- `b78b6`: `RTS` — FLOW

**stage event callback `dbe98`(설치 `dbebe`) 10**
- `dbe98`: `CMPI.W #280, 5418(a5); BGE.W dbea4` (→`dbea2`)
- `dbea2`: `RTS` — FLOW
- `dbea4`: `JSR 4814e.l` — FLOW
- `dbeaa`: `MOVE.L #dbe6c, 76(a6); MOVE.W #3c, 7a(a6); MOVE.L #dbebe, (a6)` (→`dbebe`)
- `dbebe`: `SUBQ.W #1, 7a(a6); BCC.W dbeea` (→`dbec6`)
- `dbec6`: `MOVEA.L 76(a6), a0; MOVE.W (a0), d0; JSR 3af8.l`
- `dbed2`: `MOVEA.L 76(a6), a0; MOVE.W 2(a0), 7a(a6); BNE.W dbee6` (→`dbee0`)
- `dbee0`: `JMP 2a00.l` — FLOW
- `dbee6`: `ADDQ.L #4, 76(a6)` (→`dbeea`)
- `dbeea`: `RTS` — FLOW

## N19로 넘기는 block(28, 결정 1)

[F] 재범위 N18 행 범위의 정적 도달 가운데 이 계약에 넣지 않는 시작(scratch `starts_full.txt` − `starts.txt`): `86742 86746 8674c 86752 8675a 86764 8676e 86776 8677e 86782 8678e 86790 86798 867a2 867ac 867b2 867ba 867c8 867ca 867d0 867d8 867e2 867e8 867f0 867fa 86800 8680a 86810`. routing 범위는 `86742..86814`(재범위 N19 행 범위와 같다)이고 N18 block과 겹치지 않는다. 이 본문은 `864b6` `4be06` `49fc6` `4c1de`(기존)와 `8625a`(N18)를 부르고, 범위 밖 설치 `86e76` `86fca` `8698c` `86d0c` `871ee` `86f1c`를 쓴다. [F] 두 기록에서 seed 12 13만 실행한다.

## carry

- [F] **소비 7 block**(BCC/BCS 한 명령, FLOW_ONLY). Unknown C로 들어오면 `objects n18 caller requires known carry`(상태 보존)다. Clear면 BCC는 분기 대상, BCS는 fall-through; Set이면 반대.
  - `86260 BCC.W 86352`: U01 `4b54e`의 C(U01 결정 2: `4b6be` Clear, `4b6ca` ORI Set).
  - `8635c BCC.W 86370`: U05 `1ab02`(사각형 `86252` 화면 판정)의 C(U05 `1ab7a` Clear / U01 `1aafc` Set). Clear → RTS, Set → `61` bit 7, `54` = 0, `JMP 2a00`.
  - `871d0 BCC.W 871da`: interpreter `49fc6`의 C. Set → `86700` 설치.
  - `b6536 BCC.W b6548`: fade_card `28ae`의 C(`2908` ORI Set = 자식 생성 / `290e` ANDI Clear = 빈 slot 없음).
  - `b6600 BCC.W b660a`: U18 `b7e5c`의 C(`b7e64` ANDI Clear 또는 `b7e6e JMP 4b54e`의 C). Set → `b660e` 설치.
  - `b7898 BCS.W b78a2`: stage_event_ops `288c`의 C. Clear → `b7742` 설치.
  - `b78ac BCC.W b78b6`: U01 `1aa7e`(사각형 `b7ef4` 화면 범위)의 C. Set → `b7742` 설치.
- [F] **known 생산 1 block**: Set `b6544`(`ORI.B #1,CCR`, 결정 5). 소비자는 없다.
- [F] RTS 앞 known C 생산은 없다. N18 helper `864b6`의 RTS(`86640`)는 FLOW다(들어온 C 보존). 호출자 `866d0` `8684e` `86f88`(그리고 N19 `86742`) 뒤 명령(`CMPI.W` `JSR` `MOVE.L`)이 C를 쓰지 않으므로 소비자가 없다. callback RTS(`86370` `b78b6` `dbea2` `dbeea`)의 C는 scheduler가 쓰지 않는다.
- [F] **FLOW_ONLY 94 block**(C 보존): JSR/BSR/JMP/BRA/RTS block, 표 slot 27개, `LEA`+`JSR`(`86352` `b78a2`), `LEA`+`BRA`(`8689a`), `LEA`(`868a2`), BTST/BSET(Z만)+Bcc block, BCC/BCS 소비 7개. 목록: `8625a` `86260` `86274` `8627e` `86282` `862a4` `862a8` `862ac` `862b0` `862b4` `862b8` `862bc` `862c0` `862c4` `862c8` `862cc` `862d0` `862d4` `862d8` `862dc` `862e0` `862e4` `862e8` `862ec` `862f0` `862f4` `862f8` `862fc` `86300` `86304` `86308` `8630c` `8631a` `86352` `8635c` `86370` `864b6` `86584` `865da` `865e0` `865e8` `865f2` `865fa` `86600` `86608` `8661e` `86624` `8662c` `86632` `8663a` `86640` `866ca` `866d0` `86708` `8684e` `86852` `86858` `86866` `86882` `8689a` `868a2` `868bc` `868d6` `868e6` `86f50` `86f88` `86fb0` `86fb6` `86fc6` `87192` `871c4` `871ca` `871d0` `871da` `871ea` `b6318` `b6536` `b659e` `b65f0` `b65f6` `b65fc` `b6600` `b660a` `b7874` `b787a` `b7892` `b7898` `b78a2` `b78ac` `b78b6` `dbea2` `dbea4` `dbee0` `dbeea`.
- [F] **carry 보존 목록 94 PC** = FLOW_ONLY 94.
- [F] **Unknown 101 block**: 그 밖 `MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`ADD`/`SUB`/`SUBI`/`SUBQ`/`ADDQ`/`NEG`/`LSL`/`LSR`/`ASR`/`ANDI`/`EOR` 포함 block, `ST.B`+`MOVE` block, `MOVE.L #imm,(A6)` 설치 block, `MOVEA.L #imm,A0`+`MOVE.W`+`JSR 28ae` 자식 block(`b6526`), 애니메이션 block(bank LONG), 표 계산 block `86298`. 목록: `86264` `8626c` `8628c` `86298` `86310` `86324` `8634e` `86360` `864bc` `864c2` `864d0` `864d8` `864e6` `864ee` `864fc` `86516` `86518` `8651e` `86520` `86528` `86530` `86534` `8653c` `86544` `8654a` `86552` `86564` `86568` `8658a` `86592` `86598` `865ae` `865c0` `865d8` `8660e` `8661c` `86642` `8664c` `8665a` `86664` `8666e` `866a0` `866aa` `866d4` `866de` `866ee` `866f6` `86700` `8670c` `86734` `86814` `86848` `8685e` `86870` `8687a` `8688c` `86892` `868a6` `868b2` `868b4` `868c6` `868d0` `868e0` `86f1c` `86f28` `86f54` `86f7c` `86f8c` `86fc0` `8715e` `8716a` `87196` `871be` `871d4` `871e4` `b630e` `b6506` `b6512` `b6516` `b6526` `b653a` `b6548` `b655a` `b6566` `b65a2` `b65da` `b6604` `b780c` `b7824` `b7846` `b786e` `b7880` `b788c` `b789c` `b78b0` `dbe98` `dbeaa` `dbebe` `dbec6` `dbed2` `dbee6`.
- [F] N/Z 재계산이 필요한 block 경계는 없다(block을 flag 읽기로 시작하는 곳은 위 C 소비 7곳뿐이다). 모든 비교·`TST`·`SUB`·`SUBQ`와 그 Bcc/Scc는 같은 block 안에 있다.

## 구현 범위와 규약

- routing 11 범위(위 표). 짝수 PC 994개 중 block 시작 196, 내부 798. 내부 PC 직접 진입은 `unsupported animation objects n18 PC`다. 범위 이웃과 구멍은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. 산술은 원래 폭의 2의 보수·부호 채움으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다. 결과 flag는 같은 block 안의 Bcc/Scc만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다; 예: `b6566`은 bank LONG `2001a8`을 `22(A6)` 쓰기 전에 읽고, 표 LONG과 두 번째 bank LONG, 기록 LONG 순서로 읽는다).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 94 PC를 넣는다. `b6544`는 실행 뒤 Set을 둔다.
- 제어 이동: 정적이며 예외는 표 `86298`(결정 3, PC = `862a4` + sext(`D0.W`), 상한 검사 없음)뿐이다. 설치 값(`MOVE.L #imm,(A6)`)과 `MOVE.L #dbe6c,76(A6)`은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. `28ae` 자식 대상(A0 = `b780c`)도 자료다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(`86734`→`86742`는 경계).
- 스택: JSR/BSR 복귀 LONG만. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank):
  - LONG `200140` → `22(A6)`(id `20` = `e3`), 이어서 `22(A6)` 기록의 LONG `4`(`8670c`) `40`(`86814`) `a8`(`86f28`) `10`(`86f54`) `ac`(`8716a`) `14`(`87196`)을 A1로 읽어 `49f8c`(D0.W = `100`, A0 = A6 + `26`)로 넘긴다. `86324`는 LONG `200140`을 A1로 읽어 `cc778`(경계, A0 = `cdf30`, D1.W = `e3`, D2.W = 5)로 넘긴다.
  - LONG `2001a8`(id `1b3`): `b7846` → `22(A6)`, 기록 LONG `c` → A1. `b6566`: `22(A6)` = LONG `2001a8`; `D0` = LONG `b7f2c`+sext(4·`D0.W`)(`D0.W` = 0이므로 `b7f2c`); `D0.W` ×4(상위 WORD 보존); A1 = LONG(LONG `2001a8` + sext(`D0.W`)); `D0.W` = `100`(상위 WORD는 표 LONG의 상위 WORD).
  - LONG `2001ac`(id `1bb`): `b65a2`가 `b6566`과 같은 순서로 `D0.W` = `8e`(≠ 0)를 index로 쓴다.
- [F] 고정 ROM 표(원본은 index를 검사하지 않는다; C++도 검사하지 않고 live bus로 읽는다):
  - `b6516`: LONG `b7f04`+sext(4·`D0.W`) → `56(A6)`. `b6506`이 `78.W`를 무부호 4 미만으로 자르므로(아니면 3) 자연 index는 0..3이다: `000b7e74 000b7e92 000b7eb0 000b7ece`([F] 원본 바이트).
  - `b6566`/`b65a2`: LONG `b7f2c`+sext(4·`D0.W`)(`b7f2c..`: `00000002 00000006 00000011 00000003` …).
  - `b780c`: WORD `b7f14`+sext(2·`8e.W`) → `D0.W`(`0d89 0d8c 0d88 0d8c` …, `8ebe` 인자).
  - 소리 표 `dbe6c`(노드 LONG `76`이 가리킴): WORD `(A0)` → `D0.W`(`3af8` 인자), WORD `2(A0)` → `7a.W`(0이면 `JMP 2a00`, 아니면 `76` += 4). [F] 원본 `1a37 0010 1863 0008 1a36 0018 1825 0008 1a35 000c 1863 0018 1a39 0010 1825 000a 1a35 0008 1825 000a 1a38 0000`(11쌍, 마지막 길이 0).
- [F] 주소만 넘기는 고정 ROM 자료: 사각형 `86252`(A0, `1ab02`; `ffe0 fff0 0040 0040`), `b7ef4`(A0, `1aa7e`; `ffd8 ff60 0050 00c0`), `cdf30`(A0, `cc778`), `28ae` 자식 대상 `b780c`(A0, D0.W = `14`).
- [F] work RAM:
  - 노드 A6: BYTE `14`(= `19`), `15`(bit 0: `86274` `86282` `86568` `865c0` `8660e` 읽기, `866ca` 세움; bit 7: `868d6` `86fb6` `871da` 읽기), `17`(CLR 후 `ff`), `5e`(`8628c` 읽기, `86310` `8634e` CLR), `5f`(TST 부호), `61`(bit 7: `86314` 지움, `8631a` 읽기, `86360` 세움), `84`(CLR, bit 0~5·7 세움, bit 3 지움; bit 0·3·7 읽기), `85`(`ff`/0/1/`D7.B`; TST 부호·0), `94`(TST, `ST`, CLR); WORD `1e`(= `8820`, `b7824` −1), `12`(= 부모 `12`), `20`(id), `42` `46`(위치), `54`(= `28`, CLR), `68`(= `8820`), `76`(TST, 자연 값은 부모 연결), `78`(→ `8a`, `b6506` 자르기, `b6548` 감소), `7a`(→ `90`; `dbe98` 계열은 소리 계수), `7c`(→ `8e`), `7e`(→ `8c`), `80`(TST), `8a` `8c`(비교), `8e`(감소·0 하한, TST, 표 index, 자식으로 복사), `92`(= 0/1/2/4, 비교), `96`(LONG 0), `98`(LONG `18`); LONG `(A6)`(설치), `c`(부모 노드), `22`, `36`·`3a`(`86f8c` 추종 계산), `56`(표 값), `64`(CLR, `36` 원본), `76`(`dbe98`: 소리 표 포인터), `86`(= `28000`).
  - player 노드 `100cb8`(`-7348(A5)`)·`100da8`(`-7258(A5)`)의 WORD `42`; A5 WORD `5418`(signed ≥ `280`); 부모 노드 `c(A6)`의 WORD `12`, BYTE `5e`; `28ae`가 돌려준 자식 A0의 WORD `8e` `78`(복사).
- [F] 상수 인자: `c6a96` D0.W/D1.W/D2.B = `4f`/1/0, `4a496` D0.W = `c8e`, `4c29a` D0 = 0(MOVEQ), D1.W/D2.W/D3.W = `20`/±`10`/`24`(`15` bit 0 = 0이면 D2 = −`10`), `4c1de` D0.W = ±8, `49a84` D0.W = 거리 합, `49290` D0.W = 0·D1.W = `30`·`78`, `8ebe` D1.B = 0, `4970a` D0.W/D1.W = 0/0.
- [I] 게임 의미: `8664c`/`8665a`/`86664`/`86642`는 같은 객체의 stage event·자식 진입으로 `92`(행동 종류)만 다르다. `864b6`은 `49370`(player 수/선택)과 두 player 노드의 x 거리(`85` 선택에 따라 ×4/÷4 가중)로 대상을 고르고, `84`에 화면 안(`3`)·방향(`0`)·지형 판정(`4c29a`/`4c1de` 결과 `D6` bit)을 모은다. `8684e`는 대기, `86f1c`/`86f88`은 `64` 쪽으로 감속 추종(`ASR.L #5`), `8715e`/`871c4`는 애니메이션 끝(`49fc6` Set)에 `86700`로 돌아간다. 공용 꼬리 `8625a`는 `4b54e`(정지/파괴 판정)와 `5e` 피격 종류 표(27 entry)로 파괴(`61` bit 7 → `cc778` 파편)·화면 밖 삭제를 처리한다. `b630e`는 `b780c` 자식(`78`+1개, 표 `b7f04`의 경로)을 만드는 생성기, `dbe98`은 `5418` 진행 값이 `280` 이상이면 소리 순서 표를 재생하는 stage event다. 확인하지 않았다.

## 의존·경계

- [F] N18 → 기존(모두 routing됨, 진입 case 있음): U01 `4b54e`(C 반환) `1aa7e`(C 반환), U05 `1ab02`(C 반환) `c6a96`, fade_card `28ae`(C 반환) `2a00`(JMP), stage_event_ops `288c`(C 반환) `49a84`, interpreter `49f8c` `49fc6`(C 반환), U11 `49370` `4be06`, U14 `4a496`, U15 `4c1de` `4c29a`, U08b `4be34`, U08 `49290`, U02 `8ebe`, cleanup `43e34`, sound `3af8`, stage_catalog `4814e`, N14 `4970a`, U18 `b7bc2`(BSR) `b7e5c`(C 반환) `b76d2`(BRA).
- [F] 실행부 없는 경계: `cc778` `868ea` `86c70` `86742`(N19). 단위 test는 그 PC에서 stop만 확인한다(F4 test 경계 관례). rollback 탐침은 RAM `10fe00..10fefe`만 쓴다.
- [F] 다른 단위 → N18: stage event 표(`e8dd8` `e8ddc` `e8de0` `e8ed8` `dbef8`), 범위 밖 미연결 코드의 `BRA`/`JSR`/설치·자식(요약). N19가 병합되면 `86742`가 이어진다.
- [F] N17·N19와 범위가 겹치지 않는다(N19는 `86742..86814`와 `b15e0..` 등, N18 `8625a..86372`를 부른다).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 196 시작 모두 typed fixture로 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, Set 1개, 그 밖 Unknown), zero-step, 내부 798 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 소비 7곳의 Unknown carry 오류, 경계 stop, 표 `86298`의 27 index 전부와 상한 밖 index(`86310` 시작, 내부 PC 오류, routing 밖 rollback). bank LONG, 사각형, 표는 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 소비자 C는 실제 생산자(`4b54e` `1ab02` `28ae` `b7e5c` `288c` `1aa7e` `49fc6`)를 따라 들어간 fixture로 native 분기를 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(callback, 설치 상태, 실제 bank LONG·기록·표, 소비자 native 분기).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, 회귀 0, complete 118 → 120(seed 6 7).

## 작업자 검증 기록 (scratch)

- [F] 변경 파일: 새 `engine/src/animation_machine_objects_n18.cpp`(SHA256 `1b02eafead20aca3698b9ba6943c8f535a8391e1afb498f88869d90d65e77873`), 새 `engine/tests/animation_machine_objects_n18_test.cpp`(SHA256 `5c8a82391d54dccd42737990e4298317fad5310bd42e12d7bd534ed28d7a7f1b`), 공유 최소 수정 `engine/src/animation_machine.cpp`(routing `else if` 1개 11 범위, carry 보존 case group 1개 94 PC; SHA256 `f13a37668ba91b83ca917f76a61f4bfa109d5172662528e823ec76572caeffd0`), `engine/src/animation_machine_internal.h`(선언 1줄; SHA256 `50cacc4feb7210877cdd3779a1b31796f519fb9bce1a73ad80a37492d298a094`), `Makefile`(source list·test target·run line; SHA256 `245277ed5830d87fdaa1dfa974d56976692d175932fa822c60322fab154feb36`), `tools/verify_animation_machine.py`(SOURCES; SHA256 `a50d8987e11f9297faed2ac389dfc0fd247325d0acc6cd5193d1e219d15488d8`). `animation_machine_interpreter.cpp`와 다른 단위 실행부는 고치지 않았다. 패치 파일 없음(결정 8).
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0. 새 test: `animation machine objects n18: 622 fixtures (19 checked errors, 97 kept C), 196 blocks, 2634 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen18.py`, Unicorn + 합성 물리 바이트 `86252` `b7ef4` `b7f04` `b7f14..b7f2c` `b7f2c` `dbe6c`, bank LONG `200140` `2001a8` `2001ac` → work RAM 기록 `10e600` `10e700` `10e800`; 표 SHA256 `532b70b7582fabff979e3e2bc9e11d56c508d2e540313ebce7ce6a6fa7be67aa`): 196 시작 모두 fixture로 덮임. 표 `862a0` 27 slot 전부(`8628c`에서 `5e` = 0..1a, `61` bit 7 양쪽)와 `5e` ≥ 1b, `86298` 직접 진입(`D0` = `11b` → `86310`, `ff` → `866a0`, `1c`/`1d` → `unsupported animation objects n18 PC`, `29` → `86348` routing 밖 `unsupported animation machine PC`). 실제 생산자 추종 fixture: `4b54e`(`56` = 0, `5e` 0/≠0 → `86260`, `b7e5c` 경유 → `b6600`), `1ab02`(사각형 `86252`, 안/밖 → `8635c`), `28ae`+`4970a`/`49214`/`43e38`(성공/실패 → `b6536`, `b6544` ORI 뒤 `b6548` 복사·감소), `b7e5c`(`8c` ≠ 0 Clear / 0 → `4b54e`), `288c`(부모 0 / `270e` / 그 밖 → `b7898`), `1aa7e`(사각형 `b7ef4`, 7방향 → `b78ac`). `871d0`(`49fc6`)는 typed C와 실제 ROM 차분으로 확인. block 표는 시작마다 incoming C clear/set의 native 후계·digest와 계약 C 분류, Unknown C는 소비 7곳에서 정확한 오류, zero-step 196×3, 내부 798 PC 정확한 오류, 홀수 PC(범위마다 양 끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`과 RTS 복귀 `10fe40`(9 fixture), routing 밖 `86252`(자료) `86348` `8634a` `86560`(구멍), 경계 stop 28곳(`cc778` `868ea` `86c70` `86742` 및 다른 단위 진입). checked 오류 fixture 9개(홀수 노드 읽기·쓰기, 홀수 자식 쓰기, ROM 노드, 장치 쓰기, 스택 장치, RTS 장치, `b780c` 표 index가 합성 바이트 밖 ROM, `dbec6` 홀수 소리 포인터). 돌연변이 12개(`8654a` 부호 비교, slot `862e0` 대상, `b6544` Set 누락, `ASR.L` 부호 채움, `SPL` 방향, `dbe98` 부호 비교, `b6548` 반복 조건, `b65a2` D0 상위 WORD, `8635c` 분기 방향, `86528` shift 교환, `86298` index 계산, `dbebe` 빌림 조건)가 모두 test를 실패시켰다(scratch `mut/mut.out`).
- [F] 실제 ROM 차분(`realrom/real18.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, 무작위 work RAM, seed 1·2·3 각 1,500건): 불일치 0/0/0, 시작 도달 196/196(세 seed 모두). native stop은 STOP·`2a00`과 경계(`cc778` `868ea` `86c70` `86742`). 실제 생산자 뒤 소비자 native 분기 비교(seed 1): `86260` 443, `8635c` 549, `871d0` 88, `b6600` 97, `b7898` 138, `b78ac` 172건, `b6536`은 반복 포함 다수(건너뛴 끝없는 반복 입력 포함 집계: 무작위 `28ae` 실패 A0가 `8e(A0)`를 `78(A6)`에 겹치게 하면 원본도 끝나지 않는다). native가 깨끗이 멈추지 않은 입력(무작위 포인터로 낮은 PC, 3M 명령 안에 끝나지 않음)은 건너뛰고 셌다(403/391/410건).
- [F] 기준(`4a50832` `git archive` 사본 `ms5-scratch/n18/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 13,928·node 115,196, 불일치 0, 자연 완주(전 pass 일치, 141 제외 아님) 69(`diff_results.json` SHA256 `5c9e2de678d9a7cbc1a7a31cc341f6a6f8064d26794fe29c2ca2511172e8714b`). N18 뒤: 일치 pass 14,168·node 118,740, 불일치 0, 완주 71(+seed 6 7, 각 120/120 pass), 회귀 0, 바뀐 seed는 6 7뿐(SHA256 `e816f7bf7abe04ae099e515e746e4c0475772b7b4e221d3945c5fa08e39ee5f3`).
- [F] RNG 초기화 400 frame 차분: 기준 complete 118, 일치 pass 47,200·node 349,649, 불일치 0(verification.json SHA256 `071ba441a98b6ac5a524774ff5e21e92a5a95de58a65333aeb371a22dd6db038`). N18 뒤: complete **120**(+6 7), 일치 pass 48,000·node 356,553, 불일치 0, 회귀 0, `other` 0, 응답 `00` 변형 6 seed complete 6 유지, 도구 종료 0(SHA256 `b3edb6f00b7974fd4aedc5ecc1f92b490dd6336c6654d3e408c63ff49ccb7a1f`). 분류가 바뀐 seed는 6 7(`checked-current-first-unrouted-PC` → `complete`, pass 400, node 3,456)뿐이다. seed 12 13은 기준과 같이 frame 0 `dbf5e`(N19)에서 멈춘다.
- [F] ROM SHA256·mtime 작업 전후 같음(`29112a94…`, `1791291625`).

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] `86742..86814`(N19로 넘김)와 범위 밖 고아 설치 `86c70` `868ea` `86e76` `871ee` `86fca` `8698c` `b660e` `b7742` `b78b8`, 범위 밖 함수 `86372` `863e0` `86474`의 동작은 해당 단위에서 정한다.
3. [U] `4b54e`의 `56(A6)` ≠ 0 경로(U01 본문)를 따라간 `86260` 소비는 실제 ROM 차분의 무작위 입력으로만 확인했다(typed fixture는 `56` = 0).
4. [U] 표 `b7f04`/`b7f2c`/`b7f14`의 실제 index 범위(`8e`, `78`). 원본은 검사하지 않으므로 C++도 검사하지 않고 live bus로 읽는다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n18/`(`n18.py` block·범위 계산(`N18EXTRA`/`N18STOPS`), `n18cls.py` carry 분류, `n18fmt.py` block 목록, `n18stat.py` 범위 SHA·짝수 PC, `n18xref.py` 범위 밖 참조, `n18seen.py` 자연 도달, `unitdef.py`, `gen/` typed fixture 생성·test 조립, `mut/` 돌연변이, `realrom/` 실제 ROM 차분, `fp/` 프레임 패스·RNG 차분, `doc/` 계약 조립; 저장소 밖).
