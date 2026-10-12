# 객체 callback F4 N08: 공유 객체 core — 가까운 선수 선택 `4945e`(C 반환), 화면 안 판정 `4983e`/`49842`(C 반환), 히트박스 격자 후보 탐색 `4ae4a`(후보마다 경계 `4ad6c` 호출) 계약

**상태: 계약 초안(작업자 Claude Opus 5.5 / high). 메인 결정 전이다. 아래 "작업자 검증 기록"은 이 초안대로 구현한 scratch 기록이다(구현·검증 완료, 커밋하지 않음).**

범위 근거는 재범위 문서 `animation-machine-object-callbacks-f4-rescope.md`(SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 메인 결정 1~5와 N08 행(옛 U32 172 + R09 17 + R13 12, "공유 core", 경계 callee `4ad6c`, 새 seed 없음)이다. 단위 형식과 규약은 N06 계약(`animation-machine-objects-n06-contract.md`, SHA256 `288137925db4b24b13c033e94804c4bb79931957dd82d2696e7017a57d5afee3`; ORI/ANDI CCR 생산 + RTS, 경계 stop만 시험)과 N04 계약(SHA256 `80e41996735a39feeb7f89ddbb4e3267d993bc4a1431a214f2be4af2e05a31e3`; predecessor가 여럿인 flag 분기는 각 predecessor block에 묶음, `ab1a6` 선례)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, DBRA 대상)로 정한다. Unicorn TB 분할은 쓰지 않는다. 같은 flag를 쓰는 연속 Bcc(`BEQ`+`BPL`)는 앞 block에 묶는다.
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC와 실행부 없는 미연결 PC는 경계다(아래 "의존·경계"). 범위 안의 참조되지 않는 코드는 routing하지 않는다(N03/N05 선례; N08에는 해당 바이트 없음).
- 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`JSR`/`RTS`)과 Z만 바꾸는 `BTST`+`BEQ`만인 block은 FLOW_ONLY다. block 사이 flag 재계산은 predecessor가 하나일 때만 쓴다. N08에는 block 사이 flag 재계산이 필요한 곳이 없다(모든 Bcc가 같은 block 안의 flag 생산 명령 뒤에 있다). 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C를 소비자에서 쓰려면 native 분기 결과로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N08의 코드와 고정 자료는 모두 `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료는 없다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n08`(HEAD `60837c7` = N06까지 통합, `engine/src/animation_machine.cpp` SHA256 `740202dab065a3de1426d0ebd69334023372f572f4574c8e1f3f7968d80b9971`, routing 규칙 63개)을 참조했다. 동시에 진행하는 N07(`9ad06..9ad34` `9baf2..9bc74` `9bf1e..9c0b6` `bbb9e..bbdc0`, 작업 트리 `metalslug-n07`)과 범위·경계가 겹치지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n08/n08blocks.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **N08 = 190 block**, 코드 3 범위 1,886바이트다. 재범위 N08 행의 189 block에 호출 진입 `49842` 하나를 더했다(아래 결정 1). 함수 진입 4개: `4945e`(JSR/JMP 112곳), `4983e`(JSR 6곳), `49842`(`8dbd6 JSR 49842.L` 1곳; `4983e`의 `MOVE.W #18,D2`를 건너뛰는 두 번째 진입), `4ae4a`(JSR 260곳 이상). 범위 안 설치 callback·`28ae` 자식·node callback은 없다.
- [F] `49462`는 범위 밖 `49504`/`4950a`(`BRA.W 49462`; 함수 `494c0`, 미연결)에서도 들어온다. 이미 block 시작이며 첫 명령 `TST.B D0`이 flag를 새로 만든다.
- [F] **묶인 Bcc 64개**: `4afd0`~`4b4c6`의 bit 검사 block마다 `BEQ.W`+`BPL.W`(같은 `TST`/`ADD` 결과의 Z·N). block을 Bcc로 시작하는 곳은 없다. 계산 PC(JMP/JSR 표, 레지스터 간접)·SUBX/ADDX/DIVx/MULx·TRAP·I/O port 쓰기·bank 변경·`MOVE.L #imm,(A6)` 설치는 없다. `DBRA` 2곳(`4af90` `4afb6`, 대상은 자기 block 시작 `4af8c` `4afb2`).
- [F] **carry**: 소비자 0개(어떤 N08 block도 callee 반환 C를 읽지 않는다; `4945e`의 `49370` 반환 C는 바로 다음 `TST.B D0`이 덮는다). 따라서 오류 문자열 `objects n08 caller requires known carry`는 두지 않는다. known 생산 block 5개: `494a6` `494ac`(`ANDI.B #fe,CCR`: Clear) `494b4`(`ORI.B #1,CCR`: Set), `4984e`(`CMP.W D3,D0; BCC`: 분기하면 Clear, 아니면 Set) `49862`(`CMP.W D3,D1`의 무부호 빌림). `4945e`·`4983e`/`49842`의 반환 C는 ROM 호출자 다수가 바로 `BCS`/`BCC`/`EORI #1,CCR`로 읽는다(아래 "참조"). FLOW_ONLY 5개 `4945e` `49842` `49876` `4b4da` `4b4e6`. 그 밖 180 block은 Unknown이다. `4ae4a`의 반환 C(`4b4fa`의 `MOVE.W`로 Clear)는 호출자 바로 다음 명령이 읽지 않으므로(아래 "참조") Unknown으로 둔다.
- [F] 경계(실행부 없는 미연결 callee): `4ad6c`(BSR 64곳, 후보 객체 하나와의 사각형 겹침 검사; 함수 `4ad6c..4ae4a`는 N08 밖). 그 밖 callee는 모두 기존 실행부다: U11 `49370`, buffer_cue `4b784`.
- [F] 자료 읽기: 모두 live bus. work RAM: BYTE `5744(A5)`, A4 = `5746(A5)` 또는 `5918(A5)` 격자(LONG 쌍 `60(A4)`+8·행, `(A4)`+8·열([I] 정상 입력에서 8행·12열), `a0`~`cc(A4)` 분류 mask, `d0`~`1cc(A4)` 슬롯 node 포인터), LONG `5aea(A5)` `5aee(A5)`, 결과 WORD `5af2(A5)` LONG `5af4(A5)` `5b78(A5)` `5b7e(A5)`, BYTE `10f000`(bit 5), 선수 node `100cb8`/`100da8`의 WORD `42`. 호출자가 준 A0(히트박스 기록): BYTE `3`, WORD `0`, LONG `a` `e`, WORD `12`+18·k(`4b4f4`). 고정 ROM BYTE 표 `4a9eb` + 부호확장 `D0.W`(`4aea6`). node(A6): BYTE `15`(bit 0, 1), WORD `42` `46`.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng` `dyn_base`, TB 기준): RNG 기록에서 seed 2 3 12~15 18 19 76 77 96~99 102~105가 N08 PC를 실행하고 190 시작 중 34개가 TB 시작으로 나타난다(base 기록은 seed 14 15, 11개). `4ad6c` BSR block과 `4b4e6` 이후(BTST bit 5 경로)는 400 frame 안에 실행되지 않는다. 나머지는 typed fixture로 덮는다.
- [F] 정적 재생(`n08reach.py`, routing + N08 범위): 두 기록에서 어느 seed의 첫 미연결 지점도 바뀌지 않는다(재범위 행의 "새 seed 없음"과 같다; N08 PC가 첫 미연결 지점인 seed가 없다). N08은 N09/N10 등 뒤 단위의 기반이다.

## 메인 결정 (초안 권고)

1. **범위 = 재범위 N08 행 + 호출 진입 `49842`(190 block).** [F] `8dbd6 JSR 49842.L`(D2 = `10`을 미리 넣고 `4983e`의 `MOVE.W #18,D2`를 건너뜀; 바로 뒤 `8dbdc BCC.W 8dbea`)는 정적 JSR 대상이다. 내부 PC로 두면 `8dbd6`을 연결하는 뒤 단위가 진입 PC를 다시 나눠야 하므로 지금 block 시작으로 둔다. 그 결과 `4983e` block은 `MOVE.W #18,D2` 하나가 되고 `49842`(`BTST`+`BEQ`)가 시작한다. 재범위 행(189)과 1 차이다.
2. **routing 범위는 코드만(3 범위).** `4945e..494c0` `4983e..49878` `4ae4a..4b50c`(짝수 PC 943개, block 시작 190, 내부 753). 이웃: `4945c`(미연결), `494c0`(함수 `494c0`, 미연결; N16 경계 callee), `4983c`(미연결), `49878`(`MOVEM.L` 함수, 미연결), `4ae48`(`4ad6c` 함수의 `RTS`, 미연결), `4b50c`(U01). 겹침 없음. 범위 안에 참조되지 않는 바이트는 없다.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n08.cpp`의 `animation_objects_n08_block`. 오류는 `unsupported animation objects n08 PC`(내부 PC)뿐이다. 소비자가 없으므로 `objects n08 caller requires known carry`는 만들지 않는다.
4. **무효화 탐침**(F4 test 경계 관례대로 고친다): `engine/tests/animation_machine_objects_u01_test.cpp` `interior()`의 `outside[]` 중 `0x4b50a`(이제 N08 `4b4fa` block의 내부 PC) → work RAM 탐침 `0x10fe90`. N03 test의 `4ae4a`(stop 경계)는 stop 성립만 확인하므로 영향이 없다. `tools/`에는 N08 PC를 경계로 쓰는 곳이 없다(검색한 상수는 모두 digest 값 일부).

## 원본 바이트 근거

[F] 코드 3 범위 합계 1,886바이트. 범위 순서로 이어 붙인 SHA256 `20e3f3a63a878420432aae0aa5d1abf09919d766950c91a1a497894eb643ced4`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `4945e..494c0` | 98 | `e921fcd9dc3c654ad48c042e7eb226bc6d1a7db2bcd430fc63573bcc12389561` | `4945e`(가까운 선수 node를 A0로, C 반환) |
| `4983e..49878` | 58 | `eee1cf17913c3c677da607ee3ee6ac443b4a161a2b9320d5bc566a524a919830` | `4983e`/`49842`(화면 사각형 안 판정, C 반환) |
| `4ae4a..4b50c` | 1,730 | `3cbe1d8ad63de45cafdfdac919a5d4075bf85c4f70070a19eccc971d6db85a88` | `4ae4a`(히트박스 격자 후보 탐색) |

- [F] 참조(호출 지점 바로 다음 명령, scratch `n08refs.py`): `4945e`는 JSR 111곳 + `76fec JMP`. 다음이 `BCS`/`BCC` 72곳, `EORI.B #1,CCR` 7곳, 그 밖(`MOVE.L A0,..`/`MOVE.W 42(A0),..`/`JSR 4961a`/`49636`/`4954e`/`4964e`/`CLR`/`BRA.W 90268`→`BCS`) 나머지. 모두 미연결이다. `4983e`는 `76da4` `92f20` `b0366`(뒤 `BCS`), `94506` `9de1e` `a1570`(뒤 `BCC`). `49842`는 `8dbd6`(뒤 `BCC`). `4ae4a`는 JSR 260곳 이상(N03 `c639a` 포함); 바로 다음은 `TST`/`CMPI`/`MOVE`/`MOVEQ`/`LEA`/`BTST`/`JSR`/`BRA`(대상도 C를 읽지 않음)/`RTS`(15곳, tail; [U] 그 위 호출자의 C 사용은 확인하지 않았다)이고 C를 직접 읽는 곳은 없다.
- [F] 오탐: `45f8c`/`45fc4`/`45ffc`의 `6b00`/`6000` WORD는 U15c `MOVE.W #imm,54ac(A5)`의 즉치값이다(N08로 가는 분기가 아니다).

## block 목록과 실행 의미

[F] 190 block. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `.W` 연산은 하위 WORD만, `.B`는 하위 BYTE만 바꾼다. `MOVEQ`는 LONG 전체를 부호확장 값으로 쓴다. `SWAP`은 상·하위 WORD를 바꾼다. 비교 분기: `BCC`/`BCS`는 무부호 빌림, `BGE`/`BLT`/`BGT`/`BLE`는 부호 있는 비교(N⊕V로 overflow 포함 정확), `BEQ`/`BNE`는 결과 0 여부, `BMI`/`BPL`은 결과 최상위 bit다. `ASR`는 산술 shift(C = 밀려난 bit), `LSR.L`/`LSL.L`은 논리 shift다. `DBRA Dn`은 `Dn.W`를 1 줄이고 결과가 `ffff`가 아니면 분기한다(CCR 불변).

**`4945e` 12** (호출 진입; 가까운 선수 node를 A0로 돌려준다. C Set = 선수 없음)
- `4945e`: `JSR 49370(PC)` (FLOW_ONLY; U11, D0.B = 선수 선택 값)
- `49462`: `TST.B D0; BEQ.W 494b4` (→`49468`)
- `49468`: `LEA 100cb8.L,A0; LEA 100da8.L,A1; CMPI.B #1,D0; BEQ.W 494a6` (→`4947c`)
- `4947c`: `CMPI.B #2,D0; BEQ.W 494ac` (→`49484`)
- `49484`: `MOVE.W 42(A6),D0; MOVE.W 42(A0),D1; MOVE.W 42(A1),D2; SUB.W D0,D1; BGE.W 49498` (→`49496`; 읽기 순서 A6, A0, A1)
- `49496`: `NEG.W D1` (→`49498`)
- `49498`: `SUB.W D0,D2; BGE.W 494a0` (→`4949e`)
- `4949e`: `NEG.W D2` (→`494a0`)
- `494a0`: `CMP.W D1,D2; BLT.W 494ac` (→`494a6`; sext(`D2.W`) < sext(`D1.W`) → `494ac`)
- `494a6`: `ANDI.B #fe,CCR; RTS` (known 생산: C Clear; A0 = `100cb8`)
- `494ac`: `MOVEA.L A1,A0; ANDI.B #fe,CCR; RTS` (known 생산: C Clear; A0 = `100da8`)
- `494b4`: `LEA 100cb8.L,A0; ORI.B #1,CCR; RTS` (known 생산: C Set)

**`4983e`/`49842` 6** (호출 진입 2개; D0.W = x 오프셋, D1.W = y 오프셋, D2.W = 여백(`4983e`는 `18`, `49842`는 호출자 값). C Set = 화면 사각형 안)
- `4983e`: `MOVE.W #18,D2` (→`49842`)
- `49842` (호출 진입): `BTST.B #0,15(A6); BEQ.W 4984e` (→`4984c`; FLOW_ONLY, Z만)
- `4984c`: `NEG.W D0` (→`4984e`)
- `4984e`: `ADD.W 42(A6),D0; SUB.W D2,D0; MOVE.W #140,D3; SUB.W D2,D3; SUB.W D2,D3; CMP.W D3,D0; BCC.W 49876` (→`49862`; 무부호 `D0.W` ≥ `D3.W` → `49876`(C Clear), 아니면 C Set으로 `49862`; known 생산)
- `49862`: `ADD.W 46(A6),D1; SUBI.W #100,D1; SUB.W D2,D1; MOVE.W #100,D3; SUB.W D2,D3; SUB.W D2,D3; CMP.W D3,D1` (→`49876`; known 생산: C = 무부호 `D1.W` < `D3.W`)
- `49876`: `RTS` (FLOW_ONLY; `4984e`/`49862`의 C를 그대로 돌려준다)

**`4ae4a` 172** (호출 진입; A0 = 히트박스 기록, A6 = 자기 node. 결과 D0.W = WORD `5af2(A5)`, A0/A1/A2 = LONG `5b78`/`5b7e`/`5af4(A5)`)

앞부분 44 block:
- `4ae4a`: `LEA 5746(A5),A4; TST.B 5744(A5); BMI.W 4ae5a` (→`4ae56`)
- `4ae56`: `LEA 5918(A5),A4` (→`4ae5a`)
- `4ae5a`: `MOVEQ #0,D6; MOVEQ #0,D7; MOVE.W D7,5af2(A5); MOVE.L D7,5af4(A5); MOVE.L D7,5b78(A5); MOVE.W D7,5b7c(A5); MOVE.L D7,5b7e(A5); MOVE.W #ffff,5b82(A5); MOVE.B 3(A0),D0; ASR.W #1,D0; BCC.W 4ae8a` (→`4ae82`; 쓰기 순서대로; `ASR.W`는 `D0.W` 전체(상위 BYTE는 들어온 값)를 shift)
- `4ae82`: `OR.L b8(A4),D6; OR.L bc(A4),D7` (→`4ae8a`)
- `4ae8a`: `ASR.W #1,D0; BCC.W 4ae98` (→`4ae90`); `4ae90`: `OR.L c0(A4),D6; OR.L c4(A4),D7` (→`4ae98`)
- `4ae98`: `ASR.W #1,D0; BCC.W 4aea6` (→`4ae9e`); `4ae9e`: `OR.L c8(A4),D6; OR.L cc(A4),D7` (→`4aea6`)
- `4aea6`: `MOVE.W (A0),D0; LEA 4a9eb(PC),A1; MOVE.B (A1,D0.W),D0; MOVEQ #0,D4; MOVEQ #0,D5; ASR.B #1,D0; BCC.W 4aec2` (→`4aeba`; BYTE `4a9eb` + sext(`D0.W`)를 live bus로 읽는다; A1 = `4a9eb`)
- `4aeba`: `OR.L a0(A4),D4; OR.L a4(A4),D5` (→`4aec2`)
- `4aec2`: `ASR.B #1,D0; BCC.W 4aed0` (→`4aec8`); `4aec8`: `OR.L a8(A4),D4; OR.L ac(A4),D5` (→`4aed0`)
- `4aed0`: `ASR.B #1,D0; BCC.W 4aede` (→`4aed6`); `4aed6`: `OR.L b0(A4),D4; OR.L b4(A4),D5` (→`4aede`)
- `4aede`: `AND.L D4,D6; AND.L D5,D7; MOVE.L D6,5aea(A5); MOVE.L D7,5aee(A5); OR.L D6,D7; BEQ.W 4b4da` (→`4aef0`)
- `4aef0`: `MOVE.L a(A0),D0; MOVE.L e(A0),D1; BTST.B #1,15(A6); BEQ.W 4af06` (→`4af02`)
- `4af02`: `ADD.W D1,D0; NEG.W D0` (→`4af06`)
- `4af06`: `ADD.W 46(A6),D0; SWAP D0; SWAP D1; BTST.B #0,15(A6); BEQ.W 4af1c` (→`4af18`)
- `4af18`: `ADD.W D1,D0; NEG.W D0` (→`4af1c`)
- `4af1c`: `ADD.W 42(A6),D0; MOVE.W #ffe0,D6; MOVE.W #15f,D7; ADD.W D0,D1; CMP.W D7,D0; BGT.W 4b4da` (→`4af30`)
- `4af30`: `CMP.W D6,D1; BLT.W 4b4da` (→`4af36`)
- `4af36`: `SUB.W D6,D0; BGE.W 4af3e` (→`4af3c`); `4af3c`: `CLR.W D0` (→`4af3e`)
- `4af3e`: `CMP.W D7,D1; BLE.W 4af46` (→`4af44`); `4af44`: `MOVE.W D7,D1` (→`4af46`)
- `4af46`: `SUB.W D6,D1; SWAP D0; SWAP D1; MOVE.W #100,D6; MOVE.W #1ff,D7; ADD.W D0,D1; CMP.W D7,D0; BGT.W 4b4da` (→`4af5c`)
- `4af5c`: `CMP.W D6,D1; BLT.W 4b4da` (→`4af62`)
- `4af62`: `SUB.W D6,D0; BGE.W 4af6a` (→`4af68`); `4af68`: `CLR.W D0` (→`4af6a`)
- `4af6a`: `CMP.W D7,D1; BLE.W 4af72` (→`4af70`); `4af70`: `MOVE.W D7,D1` (→`4af72`)
- `4af72`: `SUB.W D6,D1; LSR.L #5,D0; LSR.L #5,D1; MOVE.W #7ff,D6; AND.W D6,D0; AND.W D6,D1; SUB.L D0,D1; LSL.L #3,D0; LEA 60(A4,D0.W),A3; MOVEQ #0,D6; MOVEQ #0,D7` (→`4af8c`)
- `4af8c`: `OR.L (A3)+,D6; OR.L (A3)+,D7; DBRA D1,4af8c` (→`4af94`; 반복마다 한 block)
- `4af94`: `LEA 5aea(A5),A3; AND.L (A3),D6; MOVE.L D6,(A3)+; AND.L (A3),D7; MOVE.L D7,(A3)+; OR.L D6,D7; BEQ.W 4b4da` (→`4afa6`)
- `4afa6`: `SWAP D0; SWAP D1; LEA (A4,D0.W),A3; MOVEQ #0,D7; MOVEQ #0,D6` (→`4afb2`)
- `4afb2`: `OR.L (A3)+,D6; OR.L (A3)+,D7; DBRA D1,4afb2` (→`4afba`)
- `4afba`: `LEA 5aea(A5),A3; AND.L (A3)+,D6; AND.L (A3)+,D7; MOVE.L D6,D3; OR.L D7,D3; BEQ.W 4b4da` (→`4afca`)
- `4afca`: `TST.L D7; BEQ.W 4b252` (→`4afd0`)
- `4b252`: `TST.L D6; BEQ.W 4b4da` (→`4b258`)
- `4b4da`: `BTST.B #5,10f000.L; BEQ.W 4b4fa` (→`4b4e6`; FLOW_ONLY, Z만)
- `4b4e6`: `LEA 12(A0),A0` (→`4b4ea`; FLOW_ONLY)
- `4b4ea`: `MOVE.L #22b,D7; JSR 4b784(PC)` (buffer_cue; 복귀 `4b4f4`)
- `4b4f4`: `CMPI.W #8000,(A0); BNE.B 4b4ea` (→`4b4fa`)
- `4b4fa`: `MOVE.W 5af2(A5),D0; MOVEA.L 5b78(A5),A0; MOVEA.L 5b7e(A5),A1; MOVEA.L 5af4(A5),A2; RTS`

bit 검사 128 block(8 group g = 0..7; group마다 머리 1 + 덧셈 7 + 후보 8):

| g | 레지스터·크기 | 머리 block | 첫 후보 block | 끝(다음 group) | 후보 index |
| --- | --- | --- | --- | --- | --- |
| 0 | `D7.B` | `4afd0`: `TST.B D7; BEQ.W 4b070; BPL.W 4afe4` | `4afda` | `4b070` | `7`~`0` |
| 1 | `D7.W` | `4b070`: `TST.W D7; BEQ.W 4b110; BPL.W 4b084` | `4b07a` | `4b110` | `f`~`8` |
| 2 | `D7.B` | `4b110`: `SWAP D7; TST.B D7; BEQ.W 4b1b2; BPL.W 4b126` | `4b11c` | `4b1b2` | `17`~`10` |
| 3 | `D7.W` | `4b1b2`: `TST.W D7; BEQ.W 4b252; BPL.W 4b1c6` | `4b1bc` | `4b252` | `1f`~`18` |
| 4 | `D6.B` | `4b258`: `TST.B D6; BEQ.W 4b2f8; BPL.W 4b26c` | `4b262` | `4b2f8` | `27`~`20` |
| 5 | `D6.W` | `4b2f8`: `TST.W D6; BEQ.W 4b398; BPL.W 4b30c` | `4b302` | `4b398` | `2f`~`28` |
| 6 | `D6.B` | `4b398`: `SWAP D6; TST.B D6; BEQ.W 4b43a; BPL.W 4b3ae` | `4b3a4` | `4b43a` | `37`~`30` |
| 7 | `D6.W` | `4b43a`: `TST.W D6; BEQ.W 4b4da; BPL.W 4b44e` | `4b444` | `4b4da` | `3f`~`38` |

- 후보 block k(k = 0..7) = 첫 후보 + `14`·k: `MOVEA.L d(A4),A2; MOVEQ #i,D4; BSR.W 4ad6c` (i = 8g + 7 − k, d = `d0` + 4i; 복귀는 덧셈 block k, k = 7이면 끝). 경계 callee `4ad6c`로 간다.
- 덧셈 block k(k = 0..6) = 첫 후보 + `a` + `14`·k: `ADD.size Dn,Dn; BEQ.W 끝; BPL.W 다음 덧셈 block`(k = 6이면 `BPL.W 끝`) (→후보 block k+1). `ADD.B`/`ADD.W`는 하위 BYTE/WORD만 바꾸고 Z·N은 그 결과다.
- [F] 원본대로 BYTE group 뒤에 남은 bit(마지막 덧셈 뒤 BYTE `80`)가 다음 WORD group의 `TST.W`/`ADD.W`에 그대로 들어간다. C++는 bit index로 줄이지 않고 명령 그대로 계산한다.
- 시작 목록(128): g0 `4afd0 4afda 4afe4 4afee 4aff8 4b002 4b00c 4b016 4b020 4b02a 4b034 4b03e 4b048 4b052 4b05c 4b066`, g1 `4b070 4b07a 4b084 4b08e 4b098 4b0a2 4b0ac 4b0b6 4b0c0 4b0ca 4b0d4 4b0de 4b0e8 4b0f2 4b0fc 4b106`, g2 `4b110 4b11c 4b126 4b130 4b13a 4b144 4b14e 4b158 4b162 4b16c 4b176 4b180 4b18a 4b194 4b19e 4b1a8`, g3 `4b1b2 4b1bc 4b1c6 4b1d0 4b1da 4b1e4 4b1ee 4b1f8 4b202 4b20c 4b216 4b220 4b22a 4b234 4b23e 4b248`, g4 `4b258 4b262 4b26c 4b276 4b280 4b28a 4b294 4b29e 4b2a8 4b2b2 4b2bc 4b2c6 4b2d0 4b2da 4b2e4 4b2ee`, g5 `4b2f8 4b302 4b30c 4b316 4b320 4b32a 4b334 4b33e 4b348 4b352 4b35c 4b366 4b370 4b37a 4b384 4b38e`, g6 `4b398 4b3a4 4b3ae 4b3b8 4b3c2 4b3cc 4b3d6 4b3e0 4b3ea 4b3f4 4b3fe 4b408 4b412 4b41c 4b426 4b430`, g7 `4b43a 4b444 4b44e 4b458 4b462 4b46c 4b476 4b480 4b48a 4b494 4b49e 4b4a8 4b4b2 4b4bc 4b4c6 4b4d0`.

수: `4945e` 12 + `4983e`/`49842` 6 + `4ae4a` 앞부분 44 + bit 검사 128 = 190(`starts.txt`와 같다; 한 줄에 두 block을 적은 곳은 각각 센다). 분류 합계: FLOW_ONLY 5 + 생산 5 + Unknown 180 = 190.

## 구현 범위와 규약

- routing 3 범위(위 표). 짝수 PC 943개 중 block 시작 190, 내부 753. 내부 PC 직접 진입은 `unsupported animation objects n08 PC`다. 범위 이웃은 기존 실행부 또는 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. `NEG`/`SUB`/`ADD`/`CMP`는 원래 폭의 2의 보수 산술로 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다(`ASR`는 부호 bit 채움을 명시). 결과 flag는 같은 block 안의 Bcc만 쓴다(`BGE`/`BLT`/`BGT`/`BLE`는 N·V·Z를 명시 계산).
- **FLOW_ONLY 5개**(C 보존): `4945e`(JSR), `49842`(BTST+BEQ), `49876`(RTS), `4b4da`(BTST+BEQ), `4b4e6`(LEA).
- **known carry 생산 5개**: `494a6` `494ac`(Clear), `494b4`(Set), `4984e`(분기 → Clear, fall-through → Set), `49862`(무부호 `D1.W` < `D3.W`이면 Set). `4984e`/`49862` 뒤의 `49876 RTS`(FLOW_ONLY)가 C를 호출자에게 돌려준다.
- **소비자 0개.** carry 오류 문자열 없음.
- 그 밖 180 block(`MOVE`/`MOVEQ`/`MOVEA`/`TST`/`CLR`/`CMP`/`CMPI`/`SUB`/`SUBI`/`ADD`/`NEG`/`ASR`/`LSR`/`LSL`/`AND`/`OR`/`SWAP`+Bcc block, `DBRA` block, `MOVEQ`+`BSR` 후보 block, `MOVE.L`+`JSR` block, 결과 `MOVE`+`RTS` block)은 Unknown이다.
- 제어 이동은 모두 정적이다(계산 PC 없음). 경계 callee `4ad6c`로 가는 `BSR`은 복귀 LONG을 쌓고 PC를 `4ad6c`로 둔다. 다음 dispatch에서 실행부가 없으므로 stop이면 멈추고 아니면 `unsupported animation machine PC`로 rollback한다.
- `DBRA` 반복은 반복마다 한 block이다(최대 65,536회; 실행부 block 상한 1,000,000 안).
- 스택: `JSR`/`BSR` 복귀 LONG만.
- I/O port 쓰기 없음. bank 변경 없음. work RAM 밖 쓰기, 미해결·홀수 읽기는 기존 checked 오류다(예: A0 홀수의 WORD/LONG 읽기, 고정 ROM 표 BYTE가 ROM 자원 밖).

## 자료

- [F] 고정 ROM BYTE 표 `4a9eb` + sext(`D0.W`)(`4aea6`; `D0.W` = WORD `(A0)`). C++는 주소를 고정하지 않고 live bus로 읽는다. [F] 원본 첫 바이트들 `ff 05 01 01 01 03 ff ff …`.
- [F] work RAM(A5 = `108000` 기준): BYTE `5744(A5)`(부호 → 격자 선택), 격자 A4 = `5746(A5)`/`5918(A5)`의 LONG `60`+8·r(행 r = (y−`100`)>>5의 mask 쌍; `4af8c` 루프), `0`+8·k(열 k = (x+`20`)>>5의 mask 쌍; `4afb2` 루프; [I] 화면 판정 뒤 정상 입력이면 r = 0~7, k = 0~`b`), `a0`~`b4`(D4/D5 분류 mask 쌍 3개), `b8`~`cc`(D6/D7 mask 쌍 3개), `d0`~`1cc`(후보 슬롯 64개의 node LONG). 결과·임시: LONG `5aea` `5aee`(교집합 mask), WORD `5af2` `5b7c` `5b82`, LONG `5af4` `5b78` `5b7e`. BYTE `10f000` bit 5(`4b4da`). 선수 node `100cb8`/`100da8`의 WORD `42`.
- [F] node(A6): BYTE `15`(bit 0 = x 반전, bit 1 = y 반전으로 쓰임), WORD `42` `46`. 히트박스 기록(A0): BYTE `3`(하위 3 bit → D6/D7 mask 선택), WORD `0`(표 index), LONG `a`(x 오프셋:y 오프셋), LONG `e`(폭:높이), `4b4e6` 이후 18바이트 단위 기록(끝 표시 WORD `8000`).
- [I] `4945e`는 BYTE 선택 값(`49370`)이 1/2이면 해당 선수, 3 등 그 밖이면 x 거리(`42`)가 가까운 선수를 고르는 "가까운 선수" 함수로 보인다. `4983e`는 x/y 오프셋을 더한 점이 화면 `140`×`100`(여백 D2) 안인지 판정한다. `4ae4a`는 히트박스(A0)의 x·y 범위를 32픽셀 격자 열·행 mask로 바꾸고 분류 mask와 교집합을 낸 뒤 남은 bit마다 슬롯 node를 A2로 `4ad6c`(실제 사각형 겹침 검사, 결과를 `5af2` 등에 기록)를 부르는 충돌 후보 탐색으로 보인다. bit 5 `10f000`이면 `4b784`로 히트박스를 그린다(디버그 표시로 보임). 게임 의미는 미확인이다.

## 의존·경계

- [F] N08 → 기존(모두 routing됨): U11 `49370`(반환 D0.B; 반환 C는 쓰지 않음), buffer_cue `4b784`(`4b4ea`; 대기할 수 있다).
- [F] 실행부 없는 경계: `4ad6c`(64 후보 block의 BSR). 시험은 이 PC의 stop 성립만 확인한다(F4 시험 경계 관례).
- [F] 다른 단위 → N08: N03 `c639a JSR 4ae4a`(N03 test는 stop만 확인; N08 병합 뒤 실행이 N08로 이어진다). 그 밖 호출자는 모두 미연결이다. U01 test 탐침 `4b50a` 교체(결정 4).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 190 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 5개, 그 밖 Unknown), zero-step, 내부 753 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 경계 `4ad6c`·`4b784`·`49370`은 stop만. 고정 ROM 표 `4a9eb` 근처는 합성 물리 바이트(ROM 자료 아님), 격자·히트박스는 work RAM으로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 생산 C는 실제 소비자(`50d0e BCS`, `92f26 BCS`, `8dbdc BCC`)를 복귀 주소로 둔 native 분기로 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(세 진입 + `49842`, 실제 표 `4a9eb`, 격자 루프, `4ad6c` 경계 stop).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, complete 변화 0 기대(새 seed 없음).

## 작업자 검증 기록 (scratch)

- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0(U01 탐침 `4b50a`→`10fe90` 교체 포함; U01·N03 test 통과). 새 test: `animation machine objects n08: 340 fixtures (11 checked errors, 108 known C), 190 blocks, 2256 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen_n08.py`): 190 시작 모두 native fixture로 덮임. RTS로 끝나는 생산 경로 98건은 STOP 복귀 LONG을 실제 소비자(`50d0e BCS`, `92f26 BCS`, `8dbdc BCC`)로 바꾼 native 실행의 분기로 C를 확인했고(C Clear/Set 양쪽), `4984e`/`49862` 생산 C는 native 결과 레지스터의 `CMP.W` 피연산자와도 같다. 경계값: `49484`~`494a0` overflow 쌍(`8000`/`7fff`), `4983e` x/y 경계(`127`/`128`, `1e7`/`1e8`, `17`), `49842` D2 `0` `10` `80` `8000` `a0`; `4ae4a` 창 경계(`15f`/`160`, `ffcf`/`ffd0`, `1ff`/`200`, `ef`/`f0`), clamp, 뒤집기 4가지, 음수 폭·높이, 격자 2개, 행·열 루프, bit 검사 8 group × 8 후보, BYTE `80` 잔여 bit의 WORD group 진입(`0080` `0180` `4080` `8080`), `ASR.W`/`ASR.B` 부호 채움(선언 stop). 돌연변이 확인: BGT의 Z 누락, V 생략, ASR 부호 채움 누락, `494b4` C 반전이 모두 test에서 실패했다(BLE의 Z 누락은 같은 결과(`MOVE.W D7,D1`)라 관측 불가).
- [F] 실제 ROM 차분(`realrom/real_n08.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, seed 1·2·3 각 1,500건, sprite 대기 callback LONG `109152`=`cd50`, `cd58` 대기는 선언 stop): 불일치 0/0/0, 실제 소비자 분기 C와 C++ carry 불일치 0(seed별 436/465/449건), 비교된 사례만으로 190 시작 모두 도달. native stop에 경계 `4ad6c`(596/538/578), STOP, 소비자 3곳, `cd58` 포함; 실제 표 `4a9eb`와 U11 `49370`, buffer_cue `4b784`를 실제로 거친다. native가 깨끗이 멈추지 않은 6/6/6건은 임의 레지스터로 A3가 홀수가 된 LONG 읽기(native address error; C++는 checked 오류)라 제외했다. port 쓰기 0. `2986` caller-X 차이 0건.
- [F] 기준(`60837c7` 사본 `ms5-scratch/n08/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 12,728·node 99,200, 불일치 0, 자연 완주 117. N08 뒤: 같은 값, 불일치 0, 회귀 0, seed별 변화 0.
- [F] RNG 초기화 400 frame 차분: 기준 일치 pass 40,000·node 290,863, complete 100. N08 뒤 같은 값, 불일치 0, `other` 없음, complete 100(변화 0; seed별 분류·pass·node·첫 미연결 지점 변화 0). 정적 재생 예측(새 seed 없음)과 같다.
- [F] ROM SHA256·mtime 작업 전후 같음.

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] `4ad6c`(사각형 겹침 검사, `4abc0`로 이어짐)의 동작과 반환 의미는 해당 단위 계약에서 정한다.
3. [U] `4ae4a` 호출자 중 `RTS`로 이어지는 15곳의 상위 호출자가 `4ae4a`의 반환 C(Clear)를 읽는지는 확인하지 않았다. 읽는 소비자가 생기면 그 단위에서 `4b4fa`를 known Clear 생산으로 올린다.
4. [U] `49462`로 들어오는 범위 밖 `BRA`(`49504` `4950a`, 함수 `494c0`)는 그 단위에서 다룬다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n08/`(`n08blocks.py` block·범위 계산, `n08refs.py` 참조·호출자 다음 명령, `n08dyn.py`/`n08reach.py` 자연 도달·기대 완주, `n08dis.py`, `n08route.py` routing 확인, `gen/` typed fixture 생성, `realrom/` 실제 ROM 차분, `fp/` 프레임 패스 차분; 저장소 밖).
