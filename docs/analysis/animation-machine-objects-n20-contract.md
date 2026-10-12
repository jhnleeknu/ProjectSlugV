# 객체 callback F4 N20: `736d2` 계열 객체(옛 U31 주요부) — stage event callback `736d2`(설치 `7377e` `737ba` `73800` `7382e` `73854` `73882` `7389e` `738da` `738fa` `73928`, helper `735b0` `735c6` `7361a` `7364e` `73690` `736a2` `736c4` `7394e` `73992`, 공용 함수 `49580`), stage event callback `b9832`(`28ae` 자식 `b9c6e` `b9c80`, 설치 `b99be` `b9a36` `b9aae` `b9cde`) 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N20 행(217 block, `49580..495e2` `735b0..739c0` `b9832..b9d0a`, callback `736d2` `7377e` `73800` `7382e` `73854` `73882` `738fa` `73928` `b9832` `b99be` `b9aae` `b9c6e` `b9c80` `b9cde`, 경계 `736a2` `cc778`, bank 3, 미실행 설치 3(+26), 새 seed 없음, 옛 U31 110·U30 107)과 메인 결정 1·2(이름 `objects-n20`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계)다. 단위 형식과 규약은 N18 계약(SHA256 `c6ca8211c8b8f2e3ea1d343418d2d45bfd3fe91bf584a4a0e458ddc3fb3789eb`)을 따른다. 메인 작업 지시:
- flag 재계산은 선행이 유일할 때만(아니면 분기를 각 선행에 접어 넣음).
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 설치·진입은 넣는다.
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가).
- 다른 단위 실행부(`animation_machine_interpreter.cpp` 포함)는 고치지 않는다. 기존 실행부의 두 번째 진입 누락은 scratch patch와 결정으로 보고한다. DIV 0 제수는 단위 checked 오류(N20에는 DIV가 없다).
- 범위 안 설치 뒤 약 220 block을 넘으면 나누고 seed가 쓰는 부분을 먼저 구현한다. N20은 단독으로 새 seed가 없다(N21과 함께 seed 42 43; 재범위 표의 seed 2 3 `736d2` 정지는 기준에서 다시 잰다).

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback과 `MOVEA.L #imm,A0`+`JSR 28ae` 자식 callback)로 정한다. fall-through로 이어지는 설치 대상도 시작으로 센다. 묶인 연속 Bcc·PC 상대 점프 표는 없다. Unicorn TB 분할은 시작이 아니다.
- 결정 5(관례): 단위는 함수 본문 전체다(아래 결정 1의 분할이 예외). 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N18 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CMPA`/`CLR`/`SUBQ`/`ANDI`/`ADD`/`ADDI`/`SUB`/`SUBI`/`NEG`/`LSL`/`LSR`/`MULU`/`SWAP` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc)과 Z만 바꾸는 `BTST`만인 block, callee C를 소비하는 Bcc block은 FLOW_ONLY다. checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N20 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`2000d0` `2001d0` `2001e0`)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n20`(HEAD `b212aea` = N18까지 통합, `engine/src/animation_machine.cpp` SHA256 `56927533037123cf742cff1227738a6f701b0374ac5be01a1560a583ac7a156c`, routing 규칙 75개, `engine/src/animation_machine_interpreter.cpp` SHA256 `bd2bffb36ccf99cc18fe141949335e6ef1e07f7255cb1f137e387d0451ebac05`)을 참조했다. N20 routing 범위의 짝수 PC와 범위 양옆 PC(`4957e` `495e2` `735ae` `735e8` `73618` `7364a` `739c0` `b9830` `b9c0e` `b9c6c` `b9d0a`)는 기존 routing에 없다. 동시에 진행하는 N19(`86742..86814` `b15e0..b19f2` `b1b24..b1e2a` `b1fd6..b2004` `dbf5e..dbf6e`)와 범위·경계가 겹치지 않는다. N21(`b9d0a..b9da6` `c3fdc..c4084`)은 `b9d08 RTS` 바로 뒤에서 시작한다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n20/n20.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **재범위 N20 행 3 범위의 정적 도달 전체는 233 block**(진입 `736d2` `7377e` `73800` `7382e` `73854` `73882` `738fa` `73928` `b9832` `b99be` `b9aae` `b9c6e` `b9c80` `b9cde`, 범위 안 설치 callback `737ba` `7389e` `738da` `b9a36` `b9c0e`, 범위 안 BSR/JSR callee `49580` `735c6` `7361a` `7364e` `73690` `736a2` `736c4` `7394e` `73992`, BRA 꼬리 `735b0` 포함)이다. 220을 넘으므로 메인 지시대로 나눈다(결정 1).
  - **N20(이 계약) = 218 block**, 코드 6 범위 2,230바이트, 482명령이다. routing 짝수 PC 1,115개 중 내부 PC 897개다.
  - **넘기는 15 block**: `b9c00`이 `MOVE.L #b9c0e,(A6)` 뒤 fall-through로 들어가는 설치 callback `b9c0e`의 본문 `b9c0e..b9c6e`(결정 1; N21 범위 `b9d0a..` 앞에 붙이기를 제안).
- [F] 범위 안 미도달·미참조 코드는 routing하지 않는다(결정 3): `735e8..7361a`(`JSR 4945e`/`BCC`/`ANDI.B #fe,CCR`/거리 계산 함수 하나, 13명령), `7364a..7364c`(`7362a JMP cc778` 뒤 `RTS`). 고정 ROM 전수 참조 검사(scratch `n20xref.py`; 절대 LONG, `Bcc`/`BRA`/`BSR`, `JSR`/`JMP`/`LEA d16(PC)`)에서 둘 다 참조가 없다.
- [F] 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx·I/O port 쓰기·bank 변경은 없다. `MULU.W` 2곳(`73732` `73746`), WORD 스택 push/pop 1쌍(`73724 MOVE.W D0,-(A7)` → `JSR 490ba` → `73732 MULU.W (A7)+,D0`)이 있다.
- [F] 진입:
  - stage event callback(고정 ROM LONG 표): `736d2`(`e8d1c`), `b9832`(`e8f2c`).
  - `28ae` 자식 callback(범위 안 `MOVEA.L #imm,A0`+`MOVE.W #a,D0`+`JSR 28ae`): `b9c6e`(`b9840` `b9898`), `b9c80`(`b9850` `b98a8`). 같은 block의 `b9d0a` `b9d1c`(`b9860` `b9870` `b98bc` `b98cc`)는 N21 범위라 자료(A0 값)일 뿐이다.
  - 범위 안 설치 callback(결정 3 관례): `7377e`(`73890` `738ec` `73940`), `737ba`(`737b4`, fall-through), `73800`(`737e2`), `7382e`(`73828`, fall-through), `73854`(`73846`), `73882`(`7387c`, fall-through), `7389e`(`739b2`), `738da`(`738d4`, fall-through), `738fa`(`73664`), `73928`(`73922`, fall-through), `b99be`(`b99b8`, fall-through), `b9a36`(`b99e0`; `b9948 BRA.W`의 대상이기도 함), `b9aae`(`b9aa8`, fall-through), `b9cde`(`b9cd8`, fall-through), 넘기는 `b9c0e`(`b9c00`, fall-through).
  - 범위 밖 참조가 있는 시작: `49580`(범위 밖 미연결 `JSR 49580.L` 4곳 `6fb12` `85efe` `92bb0` `940f2`와 `JMP 49580.L` 1곳 `931c0`), `b9912`(범위 밖 미연결 `be36a JMP b9912.L`), `73800`(고정 ROM LONG 11곳; [I] 대부분 자료 우연 일치). 나머지 시작은 범위 안에서만 참조된다.
- [F] **경계(실행부 없음)**: `cc778`(`7362a JMP`), 넘기는 `b9c0e`(`b9c00` fall-through). 둘 다 `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **범위 밖 설치 값(노드 LONG에 저장만)**: `72eb0`(`73682 MOVE.L #72eb0,(A6)`, `736d2 MOVE.L #72eb0,8a(A6)` 뒤 `736cc MOVE.L 8a(A6),(A6)`), `b9c0e`(`b9c00`). 자료 포인터: `b9da6`(`b98dc LEA b9da6(PC),A0; MOVE.L A0,84(A6)`, `4706c` 인자), `ba2fa`/`ba304`(`8c(A6)`, N06 `ba2d6`가 읽는 WORD 표), 자식 A0 `b9d0a` `b9d1c`(N21).
- [F] **carry**(아래 "carry" 절):
  - 소비 block **11개**(BCC/BCS): `735ba` `b99fa` `b9b50`(`1ab02`), `73838` `7388c` `738e8` `73932`(`49fc6`), `b9cfe BCS`(`288c`), `73696`(`49580`), `73660` `736a6 BCS`(`73690` → `49580`의 C가 FLOW `7369a`/`736a0`을 지나 옴).
  - known 생산 block **1개**: 계산 C `495d8`(`CMPI.W #8000,D0; EORI.B #1,CCR; RTS` → C = `D0.W` bit 15, 결정 4).
  - FLOW_ONLY 100개(소비 11 포함), Unknown 117개. 100 + 1 + 117 = 218.
- [F] 스택: JSR/BSR 복귀 LONG과 `73724`/`73732`의 WORD 1개.
- [F] 자료(모두 live bus): banked LONG `2000d0`(애니메이션 기록, id `3`; 기록 LONG `10` `20` `24` `74` `18`; `7362a`는 A1로 `cc778`에 넘김), `2001d0`(id `203`; 기록 LONG `28` `24`), `2001e0`(id `223`; 기록 LONG + sext(4·(`d`+`76.W`))). 고정 ROM 표·주소 인자: 사각형 `735a8`(`1ab02`; `ffd0 0000 0060 0028`), `b982a`(`1ab02`; `ffb0 ffc0 00a0 0080`), `cdeea`(`cc778`), `c868e` `c85cc`(`490ba` A0). work RAM은 "자료" 절.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `n20seen.py`): 두 기록 모두 seed 42 43만 N20 범위 PC를 실행한다(각 seed TB 시작 138개; 모두 이 계약의 시작). callback 실행 수(각 seed, 두 기록 같음): `736d2` 1, `7377e` 8, `73800` 1, `7382e` 4, `73854` 1, `73882` 1, `738fa` 7, `73928` 63, `b9832` 2, `b99be` 85, `b9aae` 85, `b9c6e` 2, `b9c80` 2, `b9cde` 340. 넘기는 `b9c0e..b9c6e`, `736a2` 계열, `7389e` 계열, 경계 `cc778`은 자연 실행되지 않는다.
- [F] **기준(`b212aea`)에서 seed 42 43은 두 기록 모두 frame 0 `736d2`에서 멈춘다**(RNG 기록 `current_first_missing_PC` = `736d2`; base 기록 첫 미연결 callback `736d2`). seed 2 3은 기준에서 이미 RNG 400 complete다(재범위 표의 `736d2` 정지는 N11 뒤 해소). N20 뒤 seed 42 43의 다음 첫 미연결 지점은 아래 검증 기록(N21 범위 `b9d0a`/`b9d1c` 예상)이다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **분할: N20 = 218 block, `b9c0e..b9c6e` 15 block은 뒤로(N21에 붙이기 제안).** [F] 재범위 3 범위의 정적 도달 전체(범위 안 설치·callee 포함)는 233 block이다. 메인 지시(약 220 초과 시 분할, seed가 쓰는 부분 우선)에 맞춰, 자연 실행되지 않는 설치 callback `b9c0e`(`b9b8c`→`b9c00`이 `MOVE.L #b9c0e,(A6)` 뒤 fall-through로 들어감)의 본문 `b9c0e..b9c6e`(`JSR ba2d6`, `43ea4`, `49fc6`, `1ab02`/`46ef4`/`2a24`, `4706c`; 시작 `b9c0e` `b9c12` `b9c18` `b9c1e` `b9c26` `b9c32` `b9c36` `b9c3c` `b9c42` `b9c46` `b9c4e` `b9c54` `b9c5a` `b9c66` `b9c6c`)을 넘긴다. seed 42 43의 자연 경로는 `b9aae`에서 `b9b0c BLE`가 늘 `b9b30`으로 가 `b9b8c`를 쓰지 않는다. `b9b8c..b9c0e`(`b9aae` 함수 본문, 설치 `b9c0e`까지)는 N20에 남긴다. 다음 단위는 `b9c0e..b9c6e`만 routing하면 되고 N20 block을 다시 나누지 않는다(`b9c00`의 fall-through 대상이 이미 경계 PC다). [I] N21(29 block)과 같은 `b9832` 계열이라 붙이면 44 block이다. 대안: 233 block 전부를 N20에 넣는다(초과 13).
2. **`736a2` 포함(+5 block).** [F] 재범위 표는 `736a2`를 경계 callee로 적었지만, `736a2`는 N20 범위 `735b0..739c0` 안에 있고 범위 안 `737ec BSR.W 736a2`만 부른다(고정 ROM 전수 검사에서 다른 참조 없음). 결정 2·5와 "참조된 범위 안 진입은 넣는다" 지시대로 함수 본문(`736a2` `736a6` `736aa` `736b6` `736be`)을 넣는다. 자연 실행은 없다(`737c8`에서 `98.B` = 0). 빼면 213 block이고 범위 한가운데 routing 구멍이 생긴다.
3. **routing 구멍.** [F] 범위 안 미도달·미참조 코드(`735e8..7361a` 함수, `7364a RTS`)는 routing하지 않는다(N03·N11~N18 선례). routing 범위는 도달 명령의 연속 구간 6개다("원본 바이트 근거" 표). `735e8`의 `ANDI.B #fe,CCR`(`735f2`)은 이 구멍 안이라 생산자가 아니다.
4. **`495d8`은 계산 C 생산(소비자 3곳).** [F] `495d8 CMPI.W #8000,D0; EORI.B #1,CCR; RTS`: CMPI의 빌림 C = (`D0.W` < `8000` 무부호)를 EORI가 뒤집으므로 반환 C = `D0.W` bit 15다. 한 block 안의 정확한 계산이라 선행 수와 무관하다(N15 `7029e` CMPI.W 빌림 선례). 소비자: `73696 BCC`(바로 복귀), `73660 BCC`·`736a6 BCS`(`73690`의 `7369a MOVEA.L #0,A0`/`736a0 RTS`가 FLOW라 C가 그대로 옴). 실제 소비자 분기는 typed fixture(`7365c`/`736a2`/`73690`에서 실제 `49580`·`49370`을 따라감)와 실제 ROM 차분으로 확인한다. 범위 밖 미연결 호출자 5곳(`6fb12` 등)의 소비는 그 단위에서 정한다.
5. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n20.cpp`의 `animation_objects_n20_block`. 오류는 `unsupported animation objects n20 PC`(내부 PC), `objects n20 caller requires known carry`(소비 11 block). 메인 지시와 같다.
6. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`·`engine/src`에서 N20 range(넘기는 부분과 구멍 포함)의 PC를 경계·rollback 탐침으로 쓰는 곳은 없다(U11 test의 `737bb` `737c0`은 레지스터 값이다). [U] 통합 수용 도구가 seed 42 43의 첫 미연결 PC `736d2`를 고정값으로 갖고 있으면 바뀐다(아래 검증 기록에 새 값).
7. **interpreter·다른 실행부의 두 번째 진입 누락 없음.** [F] N20이 부르는 다른 단위 진입(`1ab02` `c6a96`(U05), `288c`(stage_event_ops), `28ae` `2a00`(fade_card), `2a24` `43e34` `46ef4`(cleanup), `3af8`(sound), `43ea4`(U04), `4706c`(U09), `490ba` `4c0ac`(U12), `49290`(U08), `492d0`(U20), `49370` `4be06`(U11), `49f8c` `49fc6`(interpreter), `4b54e`(U01), `4bc04`(N04), `4be2c`(U18), `ea5f0`(U13))는 모두 기존 실행부의 case로 시작한다(scratch 검사: 해당 실행부 소스의 `case 0x…:`). 패치 파일은 없다.

## 원본 바이트 근거

[F] 코드 6 범위 합계 2,230바이트. 범위 순서로 이어 붙인 SHA256 `be257ccb5f6b881d0d19db322c43427e2c1af343c09f120a2b75acd8b62ac96b`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `49580..495e2` | 98 | `32dd5559df3369fbfde0f8f8fd070375b9bd290ffa31b3233f56db95bb99d922` | 10 |
| `735b0..735e8` | 56 | `eb26a89598f7d57d7f765c27ca486513c9e9836dbb5dcb28a4e870eac1acfbfc` | 8 |
| `7361a..7364a` | 48 | `e31b19783131913a147f9a45523888efd1bc3a83cf4ddaaff1e9f129f16109f1` | 3 |
| `7364c..739c0` | 884 | `4ba869296c9d94dbb65728a1f847aa169899a9bef5a4439daaa8683b98f1aae7` | 101 |
| `b9832..b9c0e` | 988 | `2327f301c84c917d4a2bb1d2640f6aca4829d9d17a0aff55255002466a2afa08` | 82 |
| `b9c6e..b9d0a` | 156 | `5e21fcc925001fba99a6e118213d18019d225bbf1b4ff328e185410802fff1aa` | 14 |

- [F] 범위 이웃: `735a8..735b0`은 사각형 자료(`735b0 LEA 735a8(PC),A0`), `735e8..7361a`·`7364a`는 미참조 코드(결정 3), `b982a..b9832`는 사각형 자료(`b99ee`/`b9b44 MOVEA.L #b982a,A0`), `b9c0e..b9c6e`는 넘기는 본문(결정 1), `495e2..`은 다른 미연결 함수(`CLR.W D0; JSR 49392(PC)` …), `739c0..`은 다른 미연결 함수(`ST.B 7f(A6)` …), `b9d0a..`은 N21이다.

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작, "FLOW"는 C 보존, "C 소비"는 들어온 C로 분기, Unknown은 표시 없음. `.W`/`.B` 쓰기는 하위 WORD/BYTE만 바꾼다. 모든 비교·`TST`·`SUB`와 그 Bcc는 같은 block 안에 있다(결정 4의 `495d8` 포함).

**함수 `49580`(가까운 player 선택, `CMPI.W #8000`+`EORI.B #1,CCR` 계산 C 반환) 10**
- `49580`: `JSR 49370(pc)` — FLOW
- `49584`: `MOVE.B d0, d7; LEA.L 100cb8.l, a0; MOVE.W #8000, d0; BTST.B #0, d7; BEQ.W 495ac` (→`49598`)
- `49598`: `MOVE.W 42(a0), d0; SUB.W 42(a6), d0; BTST.B #0, 15(a6); BNE.W 495ac` (→`495aa`)
- `495aa`: `NEG.W d0` (→`495ac`)
- `495ac`: `BTST.B #1, d7; BEQ.W 495d8` (→`495b4`) — FLOW
- `495b4`: `LEA.L 100da8.l, a1; MOVE.W 42(a1), d1; SUB.W 42(a6), d1; BTST.B #0, 15(a6); BNE.W 495ce` (→`495cc`)
- `495cc`: `NEG.W d1` (→`495ce`)
- `495ce`: `CMP.W d1, d0; BLS.W 495d8` (→`495d4`)
- `495d4`: `MOVEA.L a1, a0; MOVE.W d1, d0` (→`495d8`)
- `495d8`: `CMPI.W #8000, d0; EORI.B #1, ccr; RTS` — 계산 C 생산

**공용 꼬리 `735b0`(`1ab02` 화면 밖 삭제)·helper `735c6`(`98`/`15` bit 7로 `4be2c`/`4be06`) 8**
- `735b0`: `LEA.L 735a8(pc), a0; JSR 1ab02.l` — FLOW
- `735ba`: `BCC.W 735c4` (→`735be`) — C 소비
- `735be`: `JMP 2a00.l` — FLOW
- `735c4`: `RTS` — FLOW
- `735c6`: `MOVE.B 98(a6), d0; CMPI.B #0, d0; BNE.W 735e2` (→`735d2`)
- `735d2`: `BTST.B #7, 15(a6); BNE.W 735e2` (→`735dc`) — FLOW
- `735dc`: `JMP 4be2c.l` — FLOW
- `735e2`: `JMP 4be06.l` — FLOW

**helper `7361a`(`4b54e`, `61` bit 7이면 `cc778` 경계) 3**
- `7361a`: `JSR 4b54e.l` — FLOW
- `73620`: `BTST.B #7, 61(a6); BEQ.W 7364c` (→`7362a`) — FLOW
- `7362a`: `MOVE.B #ff, 17(a6); LEA.L cdeea.l, a0; MOVEA.L 2000d0.l, a1; MOVE.W #3, d1; MOVE.W #0, d2; JMP cc778.l`

**helper `7364e`(32 frame마다 `73690`, 설치 `738fa`; `4bc04`, 설치 `72eb0`)·`73690`(`49580` C 전달)·`736a2`·`736c4` 22**
- `7364c`: `RTS` — FLOW
- `7364e`: `MOVE.W 10000e.l, d0; ANDI.B #1f, d0; BNE.W 7366e` (→`7365c`)
- `7365c`: `JSR 73690(pc)` — FLOW
- `73660`: `BCC.W 7366a` (→`73664`) — C 소비
- `73664`: `MOVE.L #738fa, (a6)` (→`7366a`)
- `7366a`: `MOVE.L a0, 86(a6)` (→`7366e`)
- `7366e`: `MOVE.W 42(a6), d0; MOVE.W 46(a6), d1; JSR 4bc04.l`
- `7367c`: `TST.W d0; BEQ.W 7368e` (→`73682`)
- `73682`: `MOVE.W #0, 70(a6); MOVE.L #72eb0, (a6)` (→`7368e`)
- `7368e`: `RTS` — FLOW
- `73690`: `JSR 49580.l` — FLOW
- `73696`: `BCC.W 736a0` (→`7369a`) — C 소비
- `7369a`: `MOVEA.L #0, a0` (→`736a0`) — FLOW
- `736a0`: `RTS` — FLOW
- `736a2`: `JSR 73690(pc)` — FLOW
- `736a6`: `BCS.W 736b6` (→`736aa`) — C 소비
- `736aa`: `MOVE.L #1c, 82(a6); BRA.W 736be`
- `736b6`: `MOVE.L #3, 82(a6)` (→`736be`)
- `736be`: `MOVE.L a0, 86(a6); RTS`
- `736c4`: `TST.W 94(a6); BNE.W 736d0` (→`736cc`)
- `736cc`: `MOVE.L 8a(a6), (a6)` (→`736d0`)
- `736d0`: `RTS` — FLOW

**stage event callback `736d2`(초기화) 13**
- `736d2`: `MOVE.W #0, 70(a6); MOVE.B #0, 98(a6); MOVE.L #4, 7e(a6); MOVE.L #1d, 82(a6); MOVE.L #72eb0, 8a(a6); BRA.W 736fa`
- `736fa`: `MOVE.W #33, d0; MOVE.W #4, d1; MOVE.B #0, d2; JSR c6a96.l`
- `7370c`: `JSR ea5f0.l` — FLOW
- `73712`: `CLR.B 97(a6); MOVE.W 78(a6), d0; BNE.W 73724` (→`7371e`)
- `7371e`: `MOVEQ #ff, d0; BRA.W 73736`
- `73724`: `MOVE.W d0, -(a7); LEA.L c868e.l, a0; JSR 490ba.l`
- `73732`: `MULU.W (a7)+, d0; LSR.L #8, d0` (→`73736`)
- `73736`: `MOVE.W d0, 92(a6); LEA.L c85cc.l, a0; JSR 490ba.l`
- `73746`: `MOVE.W 7a(a6), d1; MULU.W d1, d0; LSR.L #8, d0; CMPI.W #100, d0; BCS.W 7375a` (→`73756`)
- `73756`: `MOVE.W #ff, d0` (→`7375a`)
- `7375a`: `MOVE.W d0, 7a(a6); MOVE.W 7c(a6), d0; BNE.W 73768` (→`73766`)
- `73766`: `MOVEQ #ff, d0` (→`73768`)
- `73768`: `MOVE.W d0, 94(a6); MOVE.W #8820, 68(a6); MOVE.W #8820, 1e(a6); JSR 4c0ac.l`

**callback `7377e`(설치 `737ba`) 16**
- `7377e`: `MOVE.L 7e(a6), d0; CMPI.L #4, d0; BNE.W 737b4` (→`7378c`)
- `7378c`: `LEA.L 26(a6), a0; MOVE.W #3, 20(a6); MOVE.L 2000d0.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 10(a1), a1; JSR 49f8c.l`
- `737b4`: `MOVE.L #737ba, (a6)` (→`737ba`)
- `737ba`: `BSR.W 7394e` — FLOW
- `737be`: `BSR.W 735c6` — FLOW
- `737c2`: `JSR 49fc6.l` — FLOW
- `737c8`: `MOVE.B 98(a6), d0; CMPI.B #0, d0; BNE.W 737ec` (→`737d4`)
- `737d4`: `BSR.W 7364e` — FLOW
- `737d8`: `BTST.B #7, 15(a6); BNE.W 737e8` (→`737e2`) — FLOW
- `737e2`: `MOVE.L #73800, (a6)` (→`737e8`)
- `737e8`: `BRA.W 737f0` — FLOW
- `737ec`: `BSR.W 736a2` — FLOW
- `737f0`: `BSR.W 73992` — FLOW
- `737f4`: `BSR.W 736c4` — FLOW
- `737f8`: `JSR 7361a(pc)` — FLOW
- `737fc`: `BRA.W 735b0` — FLOW

**callback `73800`(설치 `7382e`) 9**
- `73800`: `LEA.L 26(a6), a0; MOVE.W #3, 20(a6); MOVE.L 2000d0.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 20(a1), a1; JSR 49f8c.l`
- `73828`: `MOVE.L #7382e, (a6)` (→`7382e`)
- `7382e`: `BSR.W 735c6` — FLOW
- `73832`: `JSR 49fc6.l` — FLOW
- `73838`: `BCC.W 7384c` (→`7383c`) — C 소비
- `7383c`: `BTST.B #7, 15(a6); BEQ.W 7384c` (→`73846`) — FLOW
- `73846`: `MOVE.L #73854, (a6)` (→`7384c`)
- `7384c`: `JSR 7361a(pc)` — FLOW
- `73850`: `BRA.W 735b0` — FLOW

**callback `73854`(설치 `73882`) 8**
- `73854`: `LEA.L 26(a6), a0; MOVE.W #3, 20(a6); MOVE.L 2000d0.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 24(a1), a1; JSR 49f8c.l`
- `7387c`: `MOVE.L #73882, (a6)` (→`73882`)
- `73882`: `BSR.W 735c6` — FLOW
- `73886`: `JSR 49fc6.l` — FLOW
- `7388c`: `BCC.W 73896` (→`73890`) — C 소비
- `73890`: `MOVE.L #7377e, (a6)` (→`73896`)
- `73896`: `JSR 7361a(pc)` — FLOW
- `7389a`: `BRA.W 735b0` — FLOW

**callback `7389e`(`739b2`가 설치, 설치 `738da`) 10**
- `7389e`: `MOVE.L 82(a6), d0; CMPI.L #1d, d0; BNE.W 738d4` (→`738ac`)
- `738ac`: `LEA.L 26(a6), a0; MOVE.W #3, 20(a6); MOVE.L 2000d0.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 74(a1), a1; JSR 49f8c.l`
- `738d4`: `MOVE.L #738da, (a6)` (→`738da`)
- `738da`: `BSR.W 7394e` — FLOW
- `738de`: `BSR.W 735c6` — FLOW
- `738e2`: `JSR 49fc6.l` — FLOW
- `738e8`: `BCC.W 738f2` (→`738ec`) — C 소비
- `738ec`: `MOVE.L #7377e, (a6)` (→`738f2`)
- `738f2`: `JSR 7361a(pc)` — FLOW
- `738f6`: `BRA.W 735b0` — FLOW

**callback `738fa`(설치 `73928`) 9**
- `738fa`: `LEA.L 26(a6), a0; MOVE.W #3, 20(a6); MOVE.L 2000d0.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 18(a1), a1; JSR 49f8c.l`
- `73922`: `MOVE.L #73928, (a6)` (→`73928`)
- `73928`: `BSR.W 735c6` — FLOW
- `7392c`: `JSR 49fc6.l` — FLOW
- `73932`: `BCC.W 73946` (→`73936`) — C 소비
- `73936`: `LEA.L 26(a6), a0; JSR 492d0.l` — FLOW
- `73940`: `MOVE.L #7377e, (a6)` (→`73946`)
- `73946`: `JSR 7361a(pc)` — FLOW
- `7394a`: `BRA.W 735b0` — FLOW

**helper `7394e` `73992` 14**
- `7394e`: `TST.B 97(a6); BNE.W 73974` (→`73956`)
- `73956`: `MOVE.W 76(a6), d0; LSL.W #3, d0; NEG.W d0; ADDI.W #140, d0; CMP.W 42(a6), d0; BMI.W 73970` (→`7396a`)
- `7396a`: `MOVE.B #1, 97(a6)` (→`73970`)
- `73970`: `BRA.W 73990` — FLOW
- `73974`: `MOVE.W 92(a6), d0; BEQ.W 73982` (→`7397c`)
- `7397c`: `SUBQ.W #1, d0; MOVE.W d0, 92(a6)` (→`73982`)
- `73982`: `MOVE.W 94(a6), d0; BEQ.W 73990` (→`7398a`)
- `7398a`: `SUBQ.W #1, d0; MOVE.W d0, 94(a6)` (→`73990`)
- `73990`: `RTS` — FLOW
- `73992`: `TST.W 92(a6); BNE.W 739be` (→`7399a`)
- `7399a`: `MOVE.W 42(a6), d0; SUBI.W #30, d0; CMPI.W #f0, d0; BCC.W 739be` (→`739aa`)
- `739aa`: `MOVE.L 86(a6), d0; BEQ.W 739be` (→`739b2`)
- `739b2`: `MOVE.W 7a(a6), 92(a6); MOVE.L #7389e, (a6)` (→`739be`)
- `739be`: `RTS` — FLOW

**stage event callback `b9832`(`28ae` 자식 `b9c6e` `b9c80` `b9d0a` `b9d1c`, 설치 `b99be`) 28**
- `b9832`: `MOVE.B #0, a3(a6); MOVE.W 82(a6), d0; BNE.W b9884` (→`b9840`)
- `b9840`: `MOVEA.L #b9c6e, a0; MOVE.W #a, d0; JSR 28ae.l`
- `b9850`: `MOVEA.L #b9c80, a0; MOVE.W #a, d0; JSR 28ae.l`
- `b9860`: `MOVEA.L #b9d0a, a0; MOVE.W #a, d0; JSR 28ae.l`
- `b9870`: `MOVEA.L #b9d1c, a0; MOVE.W #a, d0; JSR 28ae.l`
- `b9880`: `BRA.W b98dc` — FLOW
- `b9884`: `CMPI.W #1, d0; BNE.W b9890` (→`b988c`)
- `b988c`: `BRA.W b98dc` — FLOW
- `b9890`: `CMPI.W #2, d0; BNE.W b98bc` (→`b9898`)
- `b9898`: `MOVEA.L #b9c6e, a0; MOVE.W #a, d0; JSR 28ae.l`
- `b98a8`: `MOVEA.L #b9c80, a0; MOVE.W #a, d0; JSR 28ae.l`
- `b98b8`: `BRA.W b98dc` — FLOW
- `b98bc`: `MOVEA.L #b9d0a, a0; MOVE.W #a, d0; JSR 28ae.l`
- `b98cc`: `MOVEA.L #b9d1c, a0; MOVE.W #a, d0; JSR 28ae.l`
- `b98dc`: `LEA.L b9da6(pc), a0; MOVE.L a0, 84(a6); MOVE.L #ba2fa, 8c(a6); TST.B 7a(a6); BNE.W b98fc` (→`b98f4`)
- `b98f4`: `MOVE.L #ba304, 8c(a6)` (→`b98fc`)
- `b98fc`: `MOVE.W #73, d0; MOVE.W #a, d1; MOVE.B #0, d2; JSR c6a96.l`
- `b990e`: `BRA.W b9912` — FLOW
- `b9912`: `MOVE.L #ba2fa, 8c(a6); TST.B 7a(a6); BNE.W b992a` (→`b9922`)
- `b9922`: `MOVE.L #ba304, 8c(a6)` (→`b992a`)
- `b992a`: `MOVE.W #801, 68(a6); MOVE.W #801, 1e(a6); TST.W 7c(a6); BNE.W b994c` (→`b993e`)
- `b993e`: `MOVE.W #1a50, d0; JSR 3af8.l`
- `b9948`: `BRA.W b9a36` — FLOW
- `b994c`: `TST.B a3(a6); BNE.W b9980` (→`b9954`)
- `b9954`: `LEA.L 26(a6), a0; MOVE.W #203, 20(a6); MOVE.L 2001d0.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 28(a1), a1; JSR 49f8c.l`
- `b997c`: `BRA.W b99b8` — FLOW
- `b9980`: `MOVE.W #d, d0; ADD.W 76(a6), d0; LEA.L 26(a6), a0; MOVE.W #223, 20(a6); MOVE.L 2001e0.l, 22(a6); LEA.L 26(a6), a0; MOVE.W d0, d1; ADD.W d1, d1; ADD.W d1, d1; MOVEA.L 2001e0.l, a1; MOVEA.L (a1, d1.w), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b99b8`: `MOVE.L #b99be, (a6)` (→`b99be`)

**callback `b99be`(설치 `b9a36`) 17**
- `b99be`: `JSR 43ea4.l` — FLOW
- `b99c4`: `JSR 49fc6.l` — FLOW
- `b99ca`: `MOVE.W 7c(a6), d0; CMP.W 5418(a5), d0; BHI.W b99e6` (→`b99d6`)
- `b99d6`: `MOVE.W #1a50, d0; JSR 3af8.l`
- `b99e0`: `MOVE.L #b9a36, (a6)` (→`b99e6`)
- `b99e6`: `MOVE.W 80(a6), d0; BNE.W b9a0e` (→`b99ee`)
- `b99ee`: `MOVEA.L #b982a, a0; JSR 1ab02.l` — FLOW
- `b99fa`: `BCC.W b9a0a` (→`b99fe`) — C 소비
- `b99fe`: `JSR 46ef4.l` — FLOW
- `b9a04`: `JMP 2a24.l` — FLOW
- `b9a0a`: `BRA.W b9a22` — FLOW
- `b9a0e`: `CMP.W 5418(a5), d0; BHI.W b9a22` (→`b9a16`)
- `b9a16`: `JSR 46ef4.l` — FLOW
- `b9a1c`: `JMP 2a24.l` — FLOW
- `b9a22`: `MOVEA.L 84(a6), a0; CMPA.W #0, a0; BEQ.W b9a34` (→`b9a2e`)
- `b9a2e`: `JSR 4706c.l` — FLOW
- `b9a34`: `RTS` — FLOW

**`b9a36`(설치 `b9aae`)·callback `b9aae`(`b9c00`이 `b9c0e` 설치 뒤 fall-through 경계) 37**
- `b9a36`: `MOVE.W #0, 98(a6); TST.B a3(a6); BNE.W b9a70` (→`b9a44`)
- `b9a44`: `LEA.L 26(a6), a0; MOVE.W #203, 20(a6); MOVE.L 2001d0.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 28(a1), a1; JSR 49f8c.l`
- `b9a6c`: `BRA.W b9aa8` — FLOW
- `b9a70`: `MOVE.W #d, d0; ADD.W 76(a6), d0; LEA.L 26(a6), a0; MOVE.W #223, 20(a6); MOVE.L 2001e0.l, 22(a6); LEA.L 26(a6), a0; MOVE.W d0, d1; ADD.W d1, d1; ADD.W d1, d1; MOVEA.L 2001e0.l, a1; MOVEA.L (a1, d1.w), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b9aa8`: `MOVE.L #b9aae, (a6)` (→`b9aae`)
- `b9aae`: `MOVE.L #10000, d0; MOVE.L d0, 3a(a6); TST.B a3(a6); BNE.W b9aec` (→`b9ac0`)
- `b9ac0`: `CMPI.W #1, 76(a6); BNE.W b9ad4` (→`b9aca`)
- `b9aca`: `MOVE.L #18000, d0; MOVE.L d0, 3a(a6)` (→`b9ad4`)
- `b9ad4`: `CMPI.W #2, 76(a6); BNE.W b9ae8` (→`b9ade`)
- `b9ade`: `MOVE.L #20000, d0; MOVE.L d0, 3a(a6)` (→`b9ae8`)
- `b9ae8`: `BRA.W b9b00` — FLOW
- `b9aec`: `CMPI.W #2, 76(a6); BLT.W b9b00` (→`b9af6`)
- `b9af6`: `MOVE.L #18000, d0; MOVE.L d0, 3a(a6)` (→`b9b00`)
- `b9b00`: `TST.B 7a(a6); BNE.W b9b0c` (→`b9b08`)
- `b9b08`: `NEG.L 3a(a6)` (→`b9b0c`)
- `b9b0c`: `MOVE.L 98(a6), d1; ADD.L d0, d1; MOVE.L d1, 98(a6); CLR.W d1; SWAP d1; CMP.W 7e(a6), d1; BLE.W b9b30` (→`b9b22`)
- `b9b22`: `MOVE.W #1a51, d0; JSR 3af8.l`
- `b9b2c`: `BRA.W b9b8c` — FLOW
- `b9b30`: `JSR 43ea4.l` — FLOW
- `b9b36`: `JSR 49fc6.l` — FLOW
- `b9b3c`: `MOVE.W 80(a6), d0; BNE.W b9b64` (→`b9b44`)
- `b9b44`: `MOVEA.L #b982a, a0; JSR 1ab02.l` — FLOW
- `b9b50`: `BCC.W b9b60` (→`b9b54`) — C 소비
- `b9b54`: `JSR 46ef4.l` — FLOW
- `b9b5a`: `JMP 2a24.l` — FLOW
- `b9b60`: `BRA.W b9b78` — FLOW
- `b9b64`: `CMP.W 5418(a5), d0; BHI.W b9b78` (→`b9b6c`)
- `b9b6c`: `JSR 46ef4.l` — FLOW
- `b9b72`: `JMP 2a24.l` — FLOW
- `b9b78`: `MOVEA.L 84(a6), a0; CMPA.W #0, a0; BEQ.W b9b8a` (→`b9b84`)
- `b9b84`: `JSR 4706c.l` — FLOW
- `b9b8a`: `RTS` — FLOW
- `b9b8c`: `MOVE.L #0, 3a(a6); TST.B a3(a6); BNE.W b9bc8` (→`b9b9c`)
- `b9b9c`: `LEA.L 26(a6), a0; MOVE.W #203, 20(a6); MOVE.L 2001d0.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 28(a1), a1; JSR 49f8c.l`
- `b9bc4`: `BRA.W b9c00` — FLOW
- `b9bc8`: `MOVE.W #d, d0; ADD.W 76(a6), d0; LEA.L 26(a6), a0; MOVE.W #223, 20(a6); MOVE.L 2001e0.l, 22(a6); LEA.L 26(a6), a0; MOVE.W d0, d1; ADD.W d1, d1; ADD.W d1, d1; MOVEA.L 2001e0.l, a1; MOVEA.L (a1, d1.w), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b9c00`: `ANDI.L #ffff0000, 32(a6); MOVE.L #b9c0e, (a6)` (→`b9c0e`)

**`28ae` 자식 callback `b9c6e` `b9c80`(설치 `b9cde`) 14**
- `b9c6e`: `MOVE.W #ffca, d0; MOVE.W #0, d1; JSR 49290.l`
- `b9c7c`: `BRA.W b9c92` — FLOW
- `b9c80`: `MOVE.W #3c, d0; MOVE.W #0, d1; JSR 49290.l`
- `b9c8e`: `BRA.W b9c92` — FLOW
- `b9c92`: `MOVE.W #800, 68(a6); MOVE.W #800, 1e(a6); MOVE.W #73, d0; MOVE.W #9, d1; MOVE.B #0, d2; JSR c6a96.l`
- `b9cb0`: `LEA.L 26(a6), a0; MOVE.W #203, 20(a6); MOVE.L 2001d0.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 24(a1), a1; JSR 49f8c.l`
- `b9cd8`: `MOVE.L #b9cde, (a6)` (→`b9cde`)
- `b9cde`: `JSR 43e34.l` — FLOW
- `b9ce4`: `MOVEA.L c(a6), a0; CMPI.W #200, 46(a0); BGT.W b9cf8` (→`b9cf2`)
- `b9cf2`: `JSR 49fc6.l` — FLOW
- `b9cf8`: `JSR 288c.l` — FLOW
- `b9cfe`: `BCS.W b9d08` (→`b9d02`) — C 소비
- `b9d02`: `JMP 2a00.l` — FLOW
- `b9d08`: `RTS` — FLOW

- [F] 실행 의미 보충(위 명령 순서대로; 읽기·쓰기 순서는 원본과 같다):
  - `49584`: `D7.B` = `D0.B`(`49370` 결과), A0 = `100cb8`, `D0.W` = `8000`; `D7` bit 0 = 0이면 player 1 거리 계산을 건너뛴다. `49598`: `D0.W` = player1 `42.W` − `42(A6).W`, `15(A6)` bit 0 = 0이면 `NEG.W`(`495aa`). `495ac`: `D7` bit 1 = 0이면 `495d8`. `495b4`: A1 = `100da8`, `D1.W` = player2 `42.W` − `42(A6).W`, 같은 부호 규칙(`495cc`). `495ce`: `D0.W` ≤ `D1.W`(무부호, `BLS`)면 `495d8`, 아니면 A0 = A1, `D0.W` = `D1.W`(`495d4`). `495d8`: C = `D0.W` bit 15, RTS(결정 4).
  - `735c6`: `98.B` ≠ 0 또는 `15` bit 7 = 1이면 `JMP 4be06`, 아니면 `JMP 4be2c`. `7364e`: WORD `10000e`(work RAM frame 계수)의 하위 BYTE & `1f` ≠ 0이면 `7366e`(`ANDI.B`는 `D0.B`만 바꾼다). `7366e`: `D0.W`/`D1.W` = `42`/`46`, `JSR 4bc04`, 결과 `D0.W` ≠ 0이면 `70.W` = 0, `(A6)` = `72eb0`.
  - `736d2`: `70.W` = 0, `98.B` = 0, LONG `7e` = 4, LONG `82` = `1d`, LONG `8a` = `72eb0`. `736fa`: `c6a96`(`D0.W`/`D1.W`/`D2.B` = `33`/4/0). `73712`: `97.B` = 0, `D0.W` = `78.W`; 0이면 `D0` = `ffffffff`(MOVEQ), 아니면 WORD push → `490ba`(A0 = `c868e`) → `D0` = `D0.W`×pop WORD(무부호 32비트) → `LSR.L #8`. `73736`: `92.W` = `D0.W`, `490ba`(A0 = `c85cc`). `73746`: `D1.W` = `7a.W`, `D0` = `D0.W`×`D1.W` → `LSR.L #8`; `D0.W` < `100`(무부호)이 아니면 `D0.W` = `ff`. `7375a`: `7a.W` = `D0.W`; `D0.W` = `7c.W`, 0이면 `D0` = `ffffffff`. `73768`: `94.W` = `D0.W`, `68.W` = `1e.W` = `8820`, `JSR 4c0ac`.
  - `7394e`: `97.B` = 0이면 `D0.W` = `140` − (`76.W` << 3)(16비트), `D0.W` − `42.W`의 bit 15 = 0이면 `97.B` = 1. `97.B` ≠ 0이면 `92.W`·`94.W`를 각각 0 하한으로 1 줄인다. `73992`: `92.W` = 0이고 (`42.W` − `30`)(16비트) < `f0`(무부호)이고 LONG `86` ≠ 0이면 `92.W` = `7a.W`, `(A6)` = `7389e`.
  - `b9832`: `a3.B` = 0, `D0.W` = `82.W`; 0 → 자식 4개(`b9c6e` `b9c80` `b9d0a` `b9d1c`, 각 `D0.W` = `a`), 1 → 없음, 2 → `b9c6e` `b9c80`, 그 밖 → `b9d0a` `b9d1c`. `b98dc`: LONG `84` = `b9da6`, LONG `8c` = `ba2fa`(`7a.B` = 0이면 `ba304`), `c6a96`(`73`/`a`/0). `b9912`: `8c` 같은 규칙, `68.W` = `1e.W` = `801`, `7c.W` = 0이면 소리 `1a50` 뒤 `b9a36`.
  - 애니메이션 block(`7378c` `73800` `73854` `738ac` `738fa` `b9954` `b9a44` `b9b9c` `b9cb0`): `LEA 26(A6),A0; MOVE.W #id,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L off(A1),A1; JSR 49f8c.L`. 색인 애니메이션 block(`b9980` `b9a70` `b9bc8`): `D0.W` = `d` + `76.W`, `20.W` = `223`, LONG `22` = LONG `2001e0`, `D1.W` = 4·`D0.W`, A1 = LONG(LONG `2001e0` + sext(`D1.W`)), `D0.W` = `100`, `JSR 49f8c`.
  - `b99ca`/`b9a0e`/`b9b64`: `CMP.W 5418(A5),D0; BHI` — `D0.W` > A5 WORD `5418`(무부호)이면 분기. `b9aec`: `76.W` < 2(부호)이면 `b9b00`. `b9b0c`: LONG `98` += `D0`(`10000`/`18000`/`20000`; `3a`의 NEG와 무관), `D1` = 새 LONG `98`의 상위 WORD(`CLR.W`+`SWAP`, 상위 WORD 0), `D1.W` ≤ `7e.W`(부호)이면 `b9b30`. `b9ce4`: A0 = LONG `c(A6)`, WORD `46(A0)` > `200`(부호)이면 `49fc6`을 건너뛴다. `b9a22`/`b9b78`: A0 = LONG `84`, A0 = 0(CMPA.W #0: 32비트 비교)이면 RTS, 아니면 `JSR 4706c`. `b9c00`: LONG `32` &= `ffff0000`, `(A6)` = `b9c0e`(경계로 fall-through).

## 넘기는 block(15, 결정 1)

[F] `b9c0e` `b9c12` `b9c18` `b9c1e` `b9c26` `b9c32` `b9c36` `b9c3c` `b9c42` `b9c46` `b9c4e` `b9c54` `b9c5a` `b9c66` `b9c6c`(`b9c0e..b9c6e`, 96바이트). 소비자 `b9c32 BCC`(`1ab02`)가 들어 있다. N20에서는 `b9c0e`가 경계(`unsupported animation machine PC`)다.

## carry

- [F] **소비 11 block**(BCC/BCS 한 명령, FLOW_ONLY). Unknown C로 들어오면 `objects n20 caller requires known carry`(상태 보존)다. Clear면 BCC는 분기 대상, BCS는 fall-through; Set이면 반대.
  - `735ba BCC.W 735c4`, `b99fa BCC.W b9a0a`, `b9b50 BCC.W b9b60`: U05 `1ab02`(사각형 `735a8`/`b982a` 화면 판정)의 C(U05 `1ab7a` ANDI Clear / U01 `1aafc` ORI Set). Set → `JMP 2a00`(`735be`) 또는 `JSR 46ef4; JMP 2a24`.
  - `73838 BCC.W 7384c`, `7388c BCC.W 73896`, `738e8 BCC.W 738f2`, `73932 BCC.W 73946`: interpreter `49fc6`의 C(`49fe6` ORI Set = 애니메이션 LONG `26(A6)` = 0, 그 밖 interpreter 끝의 known C). Set → 설치(`73854` 또는 `7377e`).
  - `b9cfe BCS.W b9d08`: stage_event_ops `288c`의 C(`2898`/`28a8` ORI Set, `289e` `CMPI.L #270e,(A0)` 같음 → Clear). Clear → `JMP 2a00`.
  - `73696 BCC.W 736a0`: N20 `49580`(`495d8` 계산 C). Set → A0 = 0.
  - `73660 BCC.W 7366a`, `736a6 BCS.W 736b6`: N20 `73690`의 C(= `495d8` 계산 C; `73696`/`7369a`/`736a0` FLOW). `73660` Set → `(A6)` = `738fa`; `736a6` Set → LONG `82` = 3, Clear → `1c`.
- [F] **known 생산 1 block**: 계산 C `495d8`(결정 4). `MOVE`/`ANDI.B #fe,CCR` 같은 다른 known 생산은 없다.
- [F] RTS 앞 known C 생산은 `495d8`뿐이다. 그 밖 RTS(`735c4` `7364c` `7368e` `736a0` `736be` `736d0` `73990` `739be` `b9a34` `b9b8a` `b9d08`)는 FLOW 또는 Unknown이고, 호출자(`737be` 등 BSR 복귀점, scheduler)가 C를 쓰지 않는다. `736a0`은 FLOW라 `73690`의 C가 `73660`/`736a6`로 간다.
- [F] **FLOW_ONLY 100 block**(C 보존): JSR/BSR/JMP/BRA/RTS block, `LEA`+`JSR`(`735b0` `73936`), `MOVEA.L #imm,A0`+`JSR`(`b99ee` `b9b44`), `MOVEA.L #0,A0`(`7369a`), BTST(Z만)+Bcc block(`495ac` `735d2` `73620` `737d8` `7383c`), BCC/BCS 소비 11개. 목록: `49580` `495ac` `735b0` `735ba` `735be` `735c4` `735d2` `735dc` `735e2` `7361a` `73620` `7364c` `7365c` `73660` `7368e` `73690` `73696` `7369a` `736a0` `736a2` `736a6` `736d0` `7370c` `737ba` `737be` `737c2` `737d4` `737d8` `737e8` `737ec` `737f0` `737f4` `737f8` `737fc` `7382e` `73832` `73838` `7383c` `7384c` `73850` `73882` `73886` `7388c` `73896` `7389a` `738da` `738de` `738e2` `738e8` `738f2` `738f6` `73928` `7392c` `73932` `73936` `73946` `7394a` `73970` `73990` `739be` `b9880` `b988c` `b98b8` `b990e` `b9948` `b997c` `b99be` `b99c4` `b99ee` `b99fa` `b99fe` `b9a04` `b9a0a` `b9a16` `b9a1c` `b9a2e` `b9a34` `b9a6c` `b9ae8` `b9b2c` `b9b30` `b9b36` `b9b44` `b9b50` `b9b54` `b9b5a` `b9b60` `b9b6c` `b9b72` `b9b84` `b9b8a` `b9bc4` `b9c7c` `b9c8e` `b9cde` `b9cf2` `b9cf8` `b9cfe` `b9d02` `b9d08`.
- [F] **carry 보존 목록 100 PC** = FLOW_ONLY 100.
- [F] **Unknown 117 block**: 그 밖 `MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`CMPA`/`ADD`/`ADDI`/`SUB`/`SUBI`/`SUBQ`/`ANDI`/`NEG`/`LSL`/`LSR`/`MULU`/`SWAP` 포함 block, `MOVE.L #imm,(A6)` 설치 block, `MOVEA.L #imm,A0`+`MOVE.W`+`JSR 28ae` 자식 block, 애니메이션 block(bank LONG). 목록: `49584` `49598` `495aa` `495b4` `495cc` `495ce` `495d4` `735c6` `7362a` `7364e` `73664` `7366a` `7366e` `7367c` `73682` `736aa` `736b6` `736be` `736c4` `736cc` `736d2` `736fa` `73712` `7371e` `73724` `73732` `73736` `73746` `73756` `7375a` `73766` `73768` `7377e` `7378c` `737b4` `737c8` `737e2` `73800` `73828` `73846` `73854` `7387c` `73890` `7389e` `738ac` `738d4` `738ec` `738fa` `73922` `73940` `7394e` `73956` `7396a` `73974` `7397c` `73982` `7398a` `73992` `7399a` `739aa` `739b2` `b9832` `b9840` `b9850` `b9860` `b9870` `b9884` `b9890` `b9898` `b98a8` `b98bc` `b98cc` `b98dc` `b98f4` `b98fc` `b9912` `b9922` `b992a` `b993e` `b994c` `b9954` `b9980` `b99b8` `b99ca` `b99d6` `b99e0` `b99e6` `b9a0e` `b9a22` `b9a36` `b9a44` `b9a70` `b9aa8` `b9aae` `b9ac0` `b9aca` `b9ad4` `b9ade` `b9aec` `b9af6` `b9b00` `b9b08` `b9b0c` `b9b22` `b9b3c` `b9b64` `b9b78` `b9b8c` `b9b9c` `b9bc8` `b9c00` `b9c6e` `b9c80` `b9c92` `b9cb0` `b9cd8` `b9ce4`.
- [F] N/Z 재계산이 필요한 block 경계는 없다(block을 flag 읽기로 시작하는 곳은 위 C 소비 11곳뿐이다).

## 구현 범위와 규약

- routing 6 범위(위 표). 짝수 PC 1,115개 중 block 시작 218, 내부 897. 내부 PC 직접 진입은 `unsupported animation objects n20 PC`다. 범위 이웃과 구멍은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. 산술은 원래 폭의 2의 보수·부호 채움으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다. `MULU.W`는 16×16 무부호 → 32비트(`uint32_t`, 최대 `fffe0001`), `LSR.L #8`은 논리 shift다. `MOVEQ #ff`는 32비트 `ffffffff`다. 결과 flag는 같은 block 안의 Bcc만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다; 예: 애니메이션 block은 `20(A6)` 쓰기 뒤 bank LONG을 읽어 `22(A6)`에 쓰고, `22(A6)`를 다시 읽은 뒤 기록 LONG을 읽는다; `7362a`는 `17(A6)` 쓰기 뒤 bank LONG을 읽는다).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 100 PC를 넣는다. `495d8`은 실행 뒤 `D0.W` bit 15로 Set/Clear를 둔다(RTS pop 전에 정하지만 pop 실패는 전체 rollback).
- 제어 이동: 모두 정적이다. 설치 값(`MOVE.L #imm,(A6)`)과 `MOVE.L #72eb0,8a(A6)`·`MOVE.L 8a(A6),(A6)`·`84`/`8c` 포인터는 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. `28ae` 자식 대상(A0)도 자료다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(`b9c00`→`b9c0e`는 경계).
- 스택: JSR/BSR 복귀 LONG과 `73724 MOVE.W D0,-(A7)`(A7 −2, WORD 쓰기) / `73732 MULU.W (A7)+,D0`(WORD 읽기, A7 +2). 이 WORD는 `JSR 490ba`의 복귀 LONG 위에 있고 `490ba` 실행 동안 스택에 남는다. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank):
  - LONG `2000d0`(id `20.W` = `3`) → `22(A6)`, 이어서 그 기록의 LONG `10`(`7378c`) `20`(`73800`) `24`(`73854`) `74`(`738ac`) `18`(`738fa`)을 A1로 읽어 `49f8c`(D0.W = `100`, A0 = A6 + `26`)로 넘긴다. `7362a`는 LONG `2000d0`을 A1로 읽어 `cc778`(경계, A0 = `cdeea`, D1.W = 3, D2.W = 0)로 넘긴다.
  - LONG `2001d0`(id `203`): 기록 LONG `28`(`b9954` `b9a44` `b9b9c`) `24`(`b9cb0`).
  - LONG `2001e0`(id `223`): `b9980` `b9a70` `b9bc8`가 LONG `2001e0`을 `22(A6)`에 쓰고, LONG `2001e0` + sext(4·(`d` + `76.W`))의 LONG을 A1로 읽는다(원본은 index를 검사하지 않는다; C++도 검사하지 않는다).
- [F] 주소만 넘기는 고정 ROM 자료: 사각형 `735a8`(A0, `1ab02`; `ffd0 0000 0060 0028`), `b982a`(A0, `1ab02`; `ffb0 ffc0 00a0 0080`), `cdeea`(A0, `cc778`), `c868e`·`c85cc`(A0, `490ba`), `b9da6`(LONG `84`, `4706c` A0), `ba2fa`/`ba304`(LONG `8c`), `28ae` 자식 대상 `b9c6e` `b9c80` `b9d0a` `b9d1c`(A0, D0.W = `a`).
- [F] work RAM:
  - 노드 A6: BYTE `15`(bit 0: `49598` `495b4` 읽기; bit 7: `735d2` `737d8` `7383c` 읽기), `17`(= `ff`), `7a`(TST: `b98dc` `b9912` `b9b00`), `97`(CLR, = 1, TST), `98`(BYTE: `735c6` `737c8` 읽기, `736d2` = 0), `a3`(= 0, TST); WORD `1e` `68`(= `8820` / `801`), `20`(id), `42` `46`(위치), `70`(= 0), `76`(`73956` shift, `b9ac0` `b9ad4` `b9aec` 비교, 색인), `78`(곱 인자), `7a`(곱 인자, 결과 저장, `92`로 복사), `7c`(TST, 비교), `7e`(`b9b0c` 비교), `80`(TST), `92` `94`(저장·감소·TST), `98`(`b9a36` WORD = 0); LONG `(A6)`(설치), `c`(부모 노드 → `46(A0)`), `22`, `32`(`ANDI.L`), `3a`(= `10000`/`18000`/`20000`/0, NEG), `7e`(= 4, 비교), `82`(= `1d`/`1c`/3, 비교; `b9832`은 WORD `82`), `84`(= `b9da6`, 읽기), `86`(= A0, 읽기), `8a`(= `72eb0`, 읽기), `8c`(= `ba2fa`/`ba304`), `98`(LONG 누적, `b9b0c`).
  - WORD `10000e`(`7364e`, frame 계수), player 노드 `100cb8`·`100da8`의 WORD `42`(`49580`), A5 WORD `5418`(무부호 비교), 부모 노드 `c(A6)`의 WORD `46`.
- [F] 상수 인자: `c6a96` D0.W/D1.W/D2.B = `33`/4/0(`736fa`), `73`/`a`/0(`b98fc`), `73`/9/0(`b9c92`); `3af8` D0.W = `1a50`/`1a51`; `49290` D0.W/D1.W = `ffca`/0(`b9c6e`), `3c`/0(`b9c80`); `4bc04` D0.W/D1.W = `42`/`46`; `492d0` A0 = A6 + `26`; `28ae` D0.W = `a`.
- [I] 게임 의미: `736d2`는 화면 오른쪽에서 들어와(`7394e`: `42` < `140` − 8·`76`이면 `97` = 1) 일정 시간(`92`/`94` 계수, `78`/`7a`/`7c` 인자와 `490ba` 난이도 계수의 곱) 뒤 동작을 바꾸는 객체로 보인다. `73690`/`49580`은 가까운 player 노드(A0)를 고르고 거리 부호로 C를 돌려준다. `b9832`은 `82`에 따라 `28ae` 자식(`b9c6e` `b9c80` `b9d0a` `b9d1c`)을 만든 뒤 `5418` 진행 값과 `98` 누적 이동량으로 상태를 바꾸는 이동 물체(예: 수송 차량)로 보인다. 확인하지 않았다.

## 의존·경계

- [F] N20 → 기존(모두 routing됨, 진입 case 있음): U05 `1ab02`(C 반환) `c6a96`, stage_event_ops `288c`(C 반환), fade_card `28ae` `2a00`(JMP), cleanup `2a24`(JMP) `43e34` `46ef4`, sound `3af8`, U04 `43ea4`, U09 `4706c`, U12 `490ba` `4c0ac`, U08 `49290`, U20 `492d0`, U11 `49370` `4be06`(JMP), interpreter `49f8c` `49fc6`(C 반환), U01 `4b54e`, N04 `4bc04`, U18 `4be2c`(JMP), U13 `ea5f0`.
- [F] 실행부 없는 경계: `cc778`, `b9c0e`(결정 1). 단위 test는 그 PC에서 stop만 확인한다(F4 test 경계 관례). rollback 탐침은 RAM `10fe00..10fefe`만 쓴다.
- [F] 다른 단위 → N20: stage event 표 LONG `e8d1c`(`736d2`) `e8f2c`(`b9832`), 범위 밖 미연결 `JSR`/`JMP 49580.L` 5곳, `be36a JMP b9912.L`. N21 뒤 `b9d0a`/`b9d1c` 자식이 이어진다.
- [F] N19·N21과 범위가 겹치지 않는다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 218 시작 모두 typed fixture로 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 계산 C 1개, 그 밖 Unknown), zero-step, 내부 897 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 소비 11곳의 Unknown carry 오류, 경계 stop. bank LONG과 사각형은 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 소비자 C는 실제 생산자(`1ab02` `49fc6` `288c` `49580`)를 따라 들어간 fixture로 native 분기를 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(callback, 설치 상태, 실제 bank LONG·기록·표, 소비자 native 분기).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, 회귀 0, complete 기준 126 유지(N20 단독 새 seed 없음), seed 42 43의 일치 pass·node 증가와 다음 첫 미연결 지점 기록.

## 작업자 검증 기록 (scratch)

- [F] 변경 파일: 새 `engine/src/animation_machine_objects_n20.cpp`(SHA256 `d10fcf6588c6d9473162300f7331286e7aa5280d0c3a2016dc2b36786c462c7b`), 새 `engine/tests/animation_machine_objects_n20_test.cpp`(SHA256 `8546336b350a639a6da677cd730f3ea735758f6e8622f120cc10f25448e51543`), 공유 최소 수정 `engine/src/animation_machine.cpp`(routing `else if` 1개 6 범위, carry 보존 case group 1개 100 PC; SHA256 `093cb2341f55f4636d0ef26f93a45502c1da617ef10fe77ae0dc043f99694729`), `engine/src/animation_machine_internal.h`(선언 1줄; SHA256 `0ce5b448658d6af323a874f00bfb997348eec38f9f6c95040de241c3cd1216b8`), `Makefile`(source list·test target·run line; SHA256 `3657ede9b7639c7b03d693448fc93117264ad7dadd02050cc7a7aedca9511a6c`), `tools/verify_animation_machine.py`(SOURCES; SHA256 `33034fc39018bc1bc6d28eb12c33239712985994f7a2f622cc63dfb68594b243`). `animation_machine_interpreter.cpp`(SHA256 `bd2bffb3…` 그대로)와 다른 단위 실행부는 고치지 않았다. 패치 파일 없음(결정 7).
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0. 새 test: `animation machine objects n20: 668 fixtures (21 checked errors, 201 kept C), 218 blocks, 2907 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen20.py`, Unicorn + 합성 물리 바이트 `735a8` `b982a`, bank LONG `2000d0` `2001d0` `2001e0` → work RAM 기록 `10e600` `10e700` `10e800`; 표 SHA256 `bda6eefdc8b9f94519bc0a3f76b09de67418f4dd35b08e31f51593b3ba7e6464`, 두 번 생성해 같음): 218 시작 모두 fixture로 덮임. 실제 생산자 추종 fixture: `49370`+`49580`(`568e` = 0/1/2/3/`fe`/`ff`, 동점·`8000` 경계 → `495d8` 계산 C; `7364e`/`7365c`/`73690`/`736a2`/`737ec`에서 `73696` `73660` `736a6` 소비), `1ab02`(사각형 `735a8`/`b982a`, 6~7방향 → `735ba` `b99fa` `b9b50`), `288c`(부모 0/`270e`/`2710`/그 밖 → `b9cfe`), `28ae`(자식 4개 생성/실패, `82` = 0/1/2/3/`ffff`). `49fc6` 소비 4곳(`73838` `7388c` `738e8` `73932`)은 typed C와 실제 ROM 차분(실제 `49f8c`가 둔 애니메이션 기록으로 `49fc6`이 돌아온 C)으로 확인. block 표는 시작마다 incoming C clear/set의 native 후계·digest와 계약 C 분류(`495d8`은 계산 C), Unknown C는 소비 11곳에서 정확한 오류, zero-step 218×3, 내부 897 PC 정확한 오류, 홀수 PC(범위마다 양 끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`과 RTS 복귀 `10fe40`(11 fixture), routing 밖 `735a8` `735ae` `b982a` `b9830`(자료) `735e8` `735f8` `73618` `7364a`(미참조 구멍), 경계 stop 25곳(`cc778` `b9c0e` 및 다른 단위 진입). checked 오류 fixture 10개(홀수 노드 읽기·쓰기, ROM 노드, 장치 쓰기, 스택 장치, RTS 장치, WORD pop 장치, WORD push 장치, `b9ce4` 홀수 부모, `7366a` 홀수 노드 쓰기). 돌연변이 20개(`495d8` C 반전, `495ce` 부호 비교, MULU 부호, `73746` 상한, `73956` shift, `b9b0c` 무부호, `b9aec` 무부호, `b9ce4` ≥, `5418` 부호 비교, `84` WORD 비교, `736a6` 분기 방향, 색인 `d`, `b9b08` NEG 누락, `7364e` mask, `73992` 상한, `b9860` 자식, `LSR.L` 폭, `CLR.W` 누락, `7394e` BMI 방향, `49584` bit)가 모두 test를 실패시켰다(scratch `mut/mut.out`; `7364e` mask 돌연변이는 처음 살아남아 frame 값 `10`/`3330` fixture를 더한 뒤 죽음).
- [F] 실제 ROM 차분(`realrom/real20.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, 무작위 work RAM, seed 1·2·3 각 1,500건): 불일치 0/0/0, 시작 도달 218/217/218(seed 2는 `b988c` 하나 미도달; 세 seed 합집합 218). native stop은 STOP·`2a00`·`2a24`와 경계(`cc778` `b9c0e`). 실제 생산자 뒤 소비자 native 분기 비교(seed 1): `735ba` 427, `73660` 93, `73696` 230, `736a6` 99, `73838` 82, `7388c` 58, `738e8` 91, `73932` 71, `b99fa` 43, `b9b50` 60, `b9cfe` 116건. Unknown C 진입이 소비자에 닿은 의도된 차이 0, 홀수 주소 차이 0. native가 깨끗이 멈추지 않은 입력(무작위 포인터로 낮은 PC, 3M 명령 안에 끝나지 않음)은 건너뛰고 셌다(350/360/334건).
- [F] 기준(`b212aea` `git archive` 사본 `ms5-scratch/n20/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 14,168·node 118,740, 불일치 0(`diff_results.json` SHA256 `e816f7bf7abe04ae099e515e746e4c0475772b7b4e221d3945c5fa08e39ee5f3`). N20 뒤: 일치 pass 14,168·node 118,744, 불일치 0, 회귀 0, 바뀐 seed는 42 43뿐(node 8 → 10, frame 0의 `736d2`·`b9832` node 완료, 첫 미연결 callback `736d2` → `b9d1c`(N21))(SHA256 `8936865790453a6b966883537b207ae915be06f7e6db494b577f5f3b2af4284e`).
- [F] RNG 초기화 400 frame 차분: 기준 complete 126, 일치 pass 50,400·node 374,353, 불일치 0(verification.json SHA256 `b4475247097c81765d6bcf70d70eb7b718b471a5457cc78343f9763352c42eeb`). N20 뒤: complete 126(변화 없음, N20 단독 새 seed 없음), 일치 pass 50,400·node 374,357, 불일치 0, 회귀 0, `other` 0, 응답 `00` 변형 6 seed complete 6 유지, 도구 종료 0(SHA256 `b9c16acc9f22e8dfc48da909f99b4ad4a7c5b91f17e427e739f2d733e86ad9b9`). 바뀐 seed는 42 43(분류 `checked-current-first-unrouted-PC` 그대로, node 8 → 10, `current_first_missing_PC` `736d2` → `b9d1c`)뿐이다. 자연 기록에서 N20 PC를 실행하는 seed는 42 43뿐이고 둘 다 frame 0에서 N21 `b9d1c`로 멈추므로, N20의 frame 1 이후 자연 경로(`b99be` `b9aae` `b9cde` `73928` 등 수백 회)는 N21 병합 뒤에 확인된다.
- [F] ROM SHA256·mtime 작업 전후 같음(`29112a94…`, `1791291625`).

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] `b9c0e..b9c6e`(결정 1로 넘김), 범위 밖 고아 설치 `72eb0`, 자식 `b9d0a` `b9d1c`(N21), 범위 밖 함수 `495e2..` `739c0..`, 미참조 `735e8` 함수의 동작은 해당 단위에서 정한다.
3. [U] N20 자연 경로의 frame 1 이후(seed 42 43)는 N21 뒤 프레임 패스·RNG 차분으로 확인해야 한다. 지금은 typed fixture와 실제 ROM 차분만 근거다.
4. [U] 범위 밖 미연결 호출자 `6fb12` `85efe` `92bb0` `931c0` `940f2`(`49580`)와 `be36a`(`b9912`)의 문맥(레지스터·C 소비)은 확인하지 않았다.
5. [U] 색인 `2001e0` 기록의 실제 index 범위(`76.W`). 원본은 검사하지 않으므로 C++도 검사하지 않고 live bus로 읽는다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n20/`(`n20.py` block·범위 계산(`N20STOPS=b9c0e`), `n20cls.py` carry 분류, `n20fmt.py` block 목록, `n20stat.py` 범위 SHA·짝수 PC, `n20xref.py` 범위 밖 참조, `n20seen.py` 자연 도달, `unitdef.py`, `gen/` typed fixture 생성·test 조립, `mut/` 돌연변이, `realrom/` 실제 ROM 차분, `fp/` 프레임 패스·RNG 차분, `doc/` 계약 조립; 저장소 밖).
