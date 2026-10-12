# 객체 callback F4 N11(옛 U33 + R05): `aee30` 자식 생성 callback(설치 `aef18`, 자식 `aef34`/`aef3a`, 손자 `aef9a`/`af030`), `dbf80` 효과음 callback, `eb24e`/`eb266` 상태 callback(설치 `eb2ba` `eb352` `eb376`, 상태 전이 `eb586`, 이동 기록 `eb5e6`, 높이 `eb616`), interpreter 명령 callback `eb74a` `eb75c` 계약 초안

**상태: 계약 초안(작업자 Claude Opus 5.5 / high). 메인 결정 전이다. 아래 "작업자 검증 기록"은 이 초안대로 구현한 scratch 기록이다(구현·검증 완료, 커밋하지 않음).**

범위 근거는 재범위 문서 `animation-machine-object-callbacks-f4-rescope.md`(SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 메인 결정 1~5와 N11 행(95 block, `aee30..af06c` `dbf80..dbf9a` `eb24e..eb3e2` `eb586..eb626` `eb74a..eb766`, callback `aee30` `aef18` `aef34` `aef3a` `aef9a` `af030` `dbf80` `eb24e` `eb266` `eb2ba` `eb352` `eb376`, 경계 callee 없음, bank 1, 새 seed RNG 2 3 14 15 / base 14 15, 옛 U33 59 + R05 36)이다. 단위 형식과 규약은 N07 계약(SHA256 `cbbb8fbf769a9cad4b656ff71600a9ffdb85242a76c5c78c253a0fafe23a21d0`; callee C 소비 Bcc는 FLOW_ONLY, 소비자는 Unknown C에서 checked 오류), N08 계약(SHA256 `6014ec8f40fc2cd776f4faa38e214dbd09e6aa9e8717a0bee47df1342e21182d`; routing 범위는 코드만, ORI/ANDI CCR + RTS 생산)과 N04 계약(SHA256 `80e41996735a39feeb7f89ddbb4e3267d993bc4a1431a214f2be4af2e05a31e3`; 결정 5a interpreter callback 허용 목록 추가, `eb752`/`eb766`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 JSR 대상, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback, 범위 안의 `MOVEA.L #imm,A0`+`JSR 28ae` 자식)로 정한다. Unicorn TB 분할은 쓰지 않는다. 묶을 연속 Bcc는 없다.
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC는 경계다. 범위 안의 참조되지 않는 코드는 routing하지 않는다(N03/N05 선례; N11 범위 안에서 정적 진입에 도달하지 않는 코드 바이트는 없다. 범위 안의 자료 바이트는 routing하지 않는다).
- 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`JMP`/`BRA`/`RTS`/Bcc)과 Z만 바꾸는 `BCHG`만인 block, callee C를 소비하는 단독 Bcc는 FLOW_ONLY다. block 사이 flag 재계산은 predecessor가 하나일 때만 쓰고, 여럿이면 각 predecessor block에 묶는다(N04 `ab1a6` 선례). N11에는 둘 다 필요 없다(모든 N/Z/V Bcc는 같은 block 안의 명령이 flag를 만든다; block을 Bcc로 시작하는 곳은 callee C를 읽는 BCC/BCS 7곳뿐이다). 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로 확인한다(N08 선례; Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N11의 코드와 고정 자료는 모두 `<100000`이라 CPU 주소와 file offset이 같다. banked window 자료는 LONG `20013c` 하나다("자료"). 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n11`(HEAD `7dfe2f6` = N08까지 통합, `engine/src/animation_machine.cpp` SHA256 `9d9117283a31b55af01ef5626c644e80635e53ec47e384647a90b6ccfc2553d9`, routing 규칙 65개; `engine/src/animation_machine_interpreter.cpp` SHA256 `97fdde53a818555817108c9be69e053773168501858641890b62787649b56cbf`)을 참조했다. N11 범위의 짝수 PC는 기존 routing에 하나도 없다(`eb752..eb75c` `eb766..eb774`는 N04, 아래). 동시에 진행하는 N09·N10(`af4ee..af80a` `af92c..af990` `afc16..afcbe` `b005e..b05be` `c5896..c593e`, 작업 트리 `metalslug-n09`)과 겹치지 않고, N11은 그 PC를 부르지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n11/n11blocks.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **N11 = 95 block**(재범위 N11 행과 같다), 코드 8 범위 1,036바이트, 230명령이다. 진입 17개: 노드 callback `aee30`(stage event 표 LONG `e8eb4`), `dbf80`(LONG `dbfa6`, 뒤 WORD `ffff`), `eb24e`(LONG `e8f78`), `eb266`(LONG `e8f74`); 범위 안 `MOVE.L #imm,(A6)` 설치 callback `aef18`(`aef12`) `aef3a`(`aef34`) `af030`(`af02a`) `eb2ba`(`eb2b4`) `eb376`(`eb370`) — 다섯 모두 fall-through로 바로 이어진다; 범위 안 `28ae` 자식 `aef34`(`aee8e`) `aef9a`(`aef48`); LONG 표 `eb5d2` 설치 값 `eb352`(index 3; index 0 `eb296`은 JSR 복귀점이기도 하다); 범위 안 JSR 대상 `eb586` `eb5e6` `eb616`; interpreter 명령 callback 표 `4a6dc`의 첫째·셋째 값 `eb74a` `eb75c`.
- [F] 묶인 Bcc 0개. 계산 PC(JMP/JSR 표, 레지스터 간접)·SUBX/ADDX/DIVx·TRAP·I/O port 쓰기·bank 변경은 없다. `MULS.W` 3곳(`aeeb0` `aeeee` `aeef2`; 16×16 → 32 부호곱). 표 기반 설치 `eb5a4 MOVE.L eb5d2(PC,D1.W),(A6)`은 제어 이동이 아니라 자료 읽기 + node LONG 쓰기다(다음 frame의 dispatch가 그 값으로 간다).
- [F] **경계 callee(실행부 없음): 없다.** 나가는 호출은 모두 routing됐다: fade_card `28ae`(C 반환)·`2a00`(`JMP`), U11 `4be06`·`49370`(C 반환), U05 `1ab02`(C 반환)·`c6a96`, cleanup `43e34`·`43e04`, N05 `49214`, interpreter `49f8c`·`49fc6`(C 반환), N08 `4ae4a`, sound `3af8`, U12 `490ba`, exit `3d44`.
- [F] **flag**:
  - callee C 소비 block **7개**(모두 단독 Bcc, FLOW_ONLY): `aee9e`(`BCS`, `28ae`), `aef28` `aef8e` `af060`(`BCC`, `1ab02`), `af03c`(`BCC`, `49fc6`), `eb3a0`(`BCC`, N11 `eb5e6`), `eb3cc`(`BCS`, `49370`). Unknown C로 들어오면 `objects n11 caller requires known carry`.
  - known carry 생산 block **2개**: `eb60a`(`ORI.B #1,CCR; RTS` → Set), `eb610`(`ANDI.B #fe,CCR; RTS` → Clear). 실제 소비자는 `eb39c JSR eb5e6`의 복귀점 `eb3a0 BCC`다.
  - N/Z 재계산 block 없음.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `n11reach.py`): RNG 기록에서 seed 2 3(`eb24e`/`eb266` 계열)과 14 15(`aee30`·`dbf80`·`eb74a`/`eb75c` 계열)가 N11 PC를 실행한다. TB 시작 88개 중 82개가 block 시작이고 6개(`aefe0` `aefe8` `aefec` `aeff0` `aeff4` `aeff8`, `aefd6` block 안)는 Unicorn TB 분할 artefact다(시작이 아니다). base 기록은 seed 14 15만(`eb24e` 계열 없음, TB 시작 56개). 정적 재생 예측: RNG complete +2 3 14 15, base complete +14 15(재범위 행과 같다). 자연 미도달 시작 13개(`aee38` `aee6a` `aee7e` `aeea2` `aef2c` `aef76` `aef92` `aefc8` `af064` `eb3b8` `eb3d0` `eb3d8` `eb5a8`)는 typed fixture와 실제 ROM 차분으로 덮는다.

## 메인 결정 (초안 권고)

1. **범위 = 재범위 N11 행(95 block).** 행의 범위 표기 `eb24e..eb3e2` `eb586..eb626`은 자료를 포함한 요약이다.
2. **routing 범위는 코드만(8 범위).** `aee30..af06c` `dbf80..dbf9a` `eb24e..eb2fe` `eb352..eb3e2` `eb586..eb5aa` `eb5e6..eb626` `eb74a..eb752` `eb75c..eb766`(짝수 PC 518개, block 시작 95, 내부 423).
   - 범위 안 자료(routing 안 함): `eb2fe..eb352`(WORD 표 `eb2fe`, LONG 표 `eb308`, WORD 표 `eb31c`, 이동 기록 `eb326` `eb33c`), `eb5aa..eb5e6`(BYTE 전이 표 `eb5aa` 40바이트, LONG 설치 표 `eb5d2` 5 entry).
   - 이웃: `aee12..aee30`(`1ab02` 범위 기록 `aee12`, 별도 stage event callback `aee1a JMP 2a00.L`(LONG `e8eb0`, 미연결), 자료 `aee20`), `af06c..`(자료), `dbf7e`(미연결), `dbf9a..dbfac`(자료, LONG `dbfa6`), `eb24c`(미연결), `eb3e2..eb586`(표 설치 대상 `eb3e2` `eb4a4` `eb506`의 본문과 `eb3e2` 이후 함수들, 미연결), `eb626..`(함수 `eb626`, 미연결), `eb748`(미연결), N04 `eb752..eb75c` `eb766..eb774`. 겹침 없음.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n11.cpp`의 `animation_objects_n11_block`. 오류는 `unsupported animation objects n11 PC`(내부 PC), `objects n11 caller requires known carry`(소비 7 block).
4. **interpreter callback 허용 목록에 `eb74a` `eb75c` 추가(공유 실행부 1줄, N04 결정 5a 선례).** [F] `eb74a` `eb75c`는 interpreter 명령 callback 표 `4a6dc`(`eb74a` `eb752` `eb75c` `eb766`)의 대상이고 원본 `4a352`/`4a43c JSR (A1)`(live 대상)로 불린다. 현행 `animation_machine_interpreter.cpp` `callback()`은 `3679e` `2b3e8` `2b3fa` `47672` `eb752` `eb766`만 허용하고 그 밖은 `unsupported animation callback target`이다. [F] 정적 재생에서 seed 14 15는 `eb74a` `eb75c`를 실행한다(RNG·base 모두). 권고: 허용 목록에 `eb74a` `eb75c`를 더한다(그 밖 대상은 기존 오류 그대로). [F] interpreter 복귀점 `4a354`/`4a43e`는 `MOVE.W (A7)+,-7ff0(A5)`라 callback의 C를 읽지 않는다.
5. **무효화 탐침: 없다.** `engine/tests`와 `tools`에서 N11 짝수 PC를 경계·rollback 탐침으로 쓰는 곳은 없다(검색: N04 test의 `0xeb75c`는 N04 RANGES 끝값). interpreter callback 거부(`unsupported animation callback target`)를 `eb74a`/`eb75c`로 시험하는 곳도 없다.

## 원본 바이트 근거

[F] 코드 8 범위 합계 1,036바이트. 범위 순서로 이어 붙인 SHA256 `9c2ea0a9c1eb21f1064712ae84b1431591e8032e030dee9562cb6dc1bf808904`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `aee30..af06c` | 572 | `ec49f8f3b9f3f8937103aa2f988d20aa13fda9566c0b7fe618213207b8b8f71c` | `aee30`(자식 생성 루프), `aef18`, 자식 `aef34`/`aef3a`, 손자 `aef9a`/`af030` |
| `dbf80..dbf9a` | 26 | `26a05cc183a0d5cb59e92036dce370c5c5b6b6d5a5e351875542241142ac9383` | `dbf80`(효과음 2개 후 `JMP 2a00`) |
| `eb24e..eb2fe` | 176 | `86dc781fddaaf574e97b98c82fc3084bf5dcccdc9d2ca788b2b0cca0af779536` | `eb24e`, `eb266`(설치 `eb2ba`) |
| `eb352..eb3e2` | 144 | `e73484d9b80d9a8efe1418711f7cd680e7e5c7e4904b6f422887c724c5c489a8` | `eb352`(설치 `eb376`) |
| `eb586..eb5aa` | 36 | `65a25447839543cb401f01dcc4263a2ff401e84c7e496e0a471e001aef55048e` | `eb586`(상태 전이) |
| `eb5e6..eb626` | 64 | `3370a13dd566c037bf980f925ef87ca21a789c93280bb54dcded9f87e9eb74ee` | `eb5e6`(이동 기록, C 반환), `eb616` |
| `eb74a..eb752` | 8 | `18a3ddca05f7beb549c12e336719f4b6586083ed870d4aceacc6f670e91d7c82` | `eb74a`(interpreter 명령 callback) |
| `eb75c..eb766` | 10 | `79d7e76144b813b16bb8fb034c92eaceaa574f07b2d8312eb80807606fe50a18` | `eb75c`(interpreter 명령 callback) |

- [F] 참조(raw LONG 검색, scratch `n11raw.py`; JSR/BSR/Bcc 검색 `n11refs.py`): `aee30` ← LONG `e8eb4`(stage event 표; 앞 `aee1a`, 뒤 `af078`). `dbf80` ← LONG `dbfa6`(뒤 WORD `ffff`). `eb24e` ← `e8f78`, `eb266` ← `e8f74`(stage event 표; 앞 `bbe12`, 뒤 `bd152`). `aef34` ← `aee90`(`MOVEA.L #`), `aef9a` ← `aef4a`(`MOVEA.L #`). 설치 `aef18` `aef3a` `af030` `eb2ba` `eb376`은 각 `MOVE.L #imm,(A6)` 하나뿐이다(raw 검색의 `30511` 일치는 홀수 주소라 정렬된 LONG이 아니다). `eb352` ← LONG 표 `eb5de`(= `eb5d2` index 3). `eb296` ← LONG 표 `eb5d2`(index 0). `eb586` ← `eb2f8` `eb3dc`(N11)와 미연결 `eb424` `eb444` `eb468` `eb49e` `eb500` `eb550` `eb574`(모두 `JSR d16(PC)`). `eb5e6` ← `eb39c`(N11)만. `eb616` ← `eb2ba` `eb376`(N11)과 미연결 `eb3fe` `eb4c2` `eb52a`. `eb74a` `eb75c` ← fixed ROM LONG 표 `4a6dc`의 첫째·셋째 값.
- [F] `eb586`의 미연결 호출자 중 `eb49e` `eb500`은 바로 `RTS`, 그 밖은 `LEA`라 `eb586`의 C(`eb5a8 RTS`가 그대로 돌려줌)를 읽는 곳은 없다. `eb616` 호출자 다음 명령은 모두 `JSR 43e34`다.

## block 목록과 실행 의미

[F] 95 block. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `.W` 연산은 하위 WORD만, `.B`는 하위 BYTE만 바꾼다. `MOVEQ`는 LONG 전체를 부호확장 값으로 쓴다. `MOVEA.L`/`LEA`는 주소 레지스터 32비트 전체를 바꾸고 CCR을 바꾸지 않는다. `MULS.W src,Dn` = sext16(`Dn.W`) × sext16(src)의 32비트 결과를 `Dn` 전체에 쓴다. `EXT.L Dn` = sext16(`Dn.W`). `LSL.L #8`/`NEG.L`은 LONG 2의 보수. `ASR.W #n`은 부호 bit를 채우는 산술 shift(n번). `(d8,PC,Dn.W)`/`(d8,A0,Dn.W)`는 base + sext16(`Dn.W`)를 live bus로 읽는다. `JSR`/`BSR`은 복귀 LONG을 쌓고 대상으로 간다. `JMP 2a00.L`은 PC = `2a00`.

**`aee30` 18** (노드 callback; 방향 `76(A6)`별 속도 쌍을 정하고 `8c(A6)` = 0..`78(A6)`마다 `28ae` 자식 `aef34`를 만든다)
- `aee30`: `MOVE.W 80(A6),D0; BNE.W aee3c` (→`aee38`)
- `aee38`: `MOVE.W #18,D0` (→`aee3c`)
- `aee3c`: `MOVE.W 76(A6),D1; BNE.W aee4e` (→`aee44`)
- `aee44`: `MOVE.W #0,8e(A6); MOVE.W D0,90(A6)` (→`aee4e`)
- `aee4e`: `CMPI.W #1,D1; BNE.W aee62` (→`aee56`)
- `aee56`: `MOVE.W #0,8e(A6); NEG.W D0; MOVE.W D0,90(A6)` (→`aee62`)
- `aee62`: `CMPI.W #2,D1; BNE.W aee76` (→`aee6a`)
- `aee6a`: `NEG.W D0; MOVE.W D0,8e(A6); MOVE.W #0,90(A6)` (→`aee76`)
- `aee76`: `CMPI.W #3,D1; BNE.W aee88` (→`aee7e`)
- `aee7e`: `MOVE.W D0,8e(A6); MOVE.W #0,90(A6)` (→`aee88`)
- `aee88`: `MOVE.W #0,8c(A6)` (→`aee8e`)
- `aee8e`: `MOVEA.L #aef34,A0; MOVE.W #a,D0; JSR 28ae.L` (복귀 `aee9e`)
- `aee9e`: `BCS.W aeea8` (→`aeea2`; 소비자: C Set → `aeea8`, Clear → `aeea2`)
- `aeea2`: `JMP 2a00.L`
- `aeea8`: `MOVE.W 8c(A6),D0; MOVE.W 7e(A6),D1; MULS.W D1,D0; MOVE.W D0,88(A0); MOVE.W 7c(A6),8a(A0); MOVE.W 7a(A6),7a(A0); MOVE.W 8c(A6),8c(A0); MOVE.W 82(A6),D0; ADD.W D0,8c(A0); MOVE.W 84(A6),84(A0); MOVE.W 76(A6),76(A0); MOVE.W 86(A6),86(A0); MOVE.W 76(A6),D2; MOVE.W 8e(A6),D0; MOVE.W 90(A6),D1; MULS.W 8c(A6),D0; MULS.W 8c(A6),D1; JSR 49214.L` (복귀 `aeefc`; 읽기·쓰기는 이 순서; A0 = `28ae`가 돌려준 자식 node)
- `aeefc`: `MOVE.W 8c(A6),D0; ADDQ.W #1,D0; CMP.W 78(A6),D0; BGT.W aef12` (→`aef0a`; BGT = !Z ∧ N = V, `D0.W` − `78(A6)` WORD)
- `aef0a`: `MOVE.W D0,8c(A6); BRA.W aee8e`
- `aef12`: `MOVE.L #aef18,(A6)` (→`aef18`)

**`aef18` 5** (설치 callback; 범위 기록 `aee12` 밖이면 `2a00`)
- `aef18`: `JSR 4be06.L` (복귀 `aef1e`)
- `aef1e`: `LEA aee12(PC),A0; JSR 1ab02.L` (복귀 `aef28`)
- `aef28`: `BCC.W aef32` (→`aef2c`; 소비자: Clear → `aef32`, Set → `aef2c`)
- `aef2c`: `JMP 2a00.L`
- `aef32`: `RTS`

**`aef34`/`aef3a` 13** (`28ae` 자식과 그 설치 callback; `88(A6)` 대기 뒤 손자 `aef9a`를 만들고 `7a(A6)`을 센다)
- `aef34`: `MOVE.L #aef3a,(A6)` (→`aef3a`)
- `aef3a`: `JSR 43e34.L` (복귀 `aef40`)
- `aef40`: `TST.W 88(A6); BNE.W aef80` (→`aef48`)
- `aef48`: `MOVEA.L #aef9a,A0; MOVE.W #a,D0; JSR 28ae.L` (복귀 `aef58`; 반환 C는 읽지 않는다)
- `aef58`: `MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.L` (복귀 `aef62`)
- `aef62`: `MOVE.W 8a(A6),88(A6); MOVE.W 86(A6),86(A0); SUBQ.W #1,7a(A6); BCC.W aef7c` (→`aef76`; 빼기 전 WORD가 0이면 C Set → `aef76`)
- `aef76`: `JMP 2a00.L`
- `aef7c`: `BRA.W aef84`
- `aef80`: `SUBQ.W #1,88(A6)` (→`aef84`)
- `aef84`: `LEA aee12(PC),A0; JSR 1ab02.L` (복귀 `aef8e`)
- `aef8e`: `BCC.W aef98` (→`aef92`; 소비자)
- `aef92`: `JMP 2a00.L`
- `aef98`: `RTS`

**`aef9a`/`af030` 18** (손자 `28ae` 자식과 그 설치 callback; animation 설정 뒤 매 frame 진행·충돌 탐색)
- `aef9a`: `MOVE.W #4e,D0; MOVE.W #2,D1; MOVE.B #0,D2; JSR c6a96.L` (복귀 `aefac`)
- `aefac`: `MOVEA.L c(A6),A0; MOVE.W #8820,D0; ADD.W 8c(A0),D0; MOVE.W D0,68(A6); MOVE.W D0,1e(A6); TST.W 84(A0); BEQ.W aefce` (→`aefc8`; A0 = 부모 node)
- `aefc8`: `BCHG.B #0,15(A6)` (→`aefce`; Z만, FLOW_ONLY)
- `aefce`: `TST.W 86(A6); BNE.W af002` (→`aefd6`)
- `aefd6`: `LEA 26(A6),A0; MOVE.W #db,20(A6); MOVE.L 20013c.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 8(A1),A1; JSR 49f8c.L` (복귀 `aeffe`; bank LONG `20013c`와 그 값 + `8`의 LONG을 live bus로)
- `aeffe`: `BRA.W af02a`
- `af002`: `aefd6`과 같고 `MOVEA.L c(A1),A1` (복귀 `af02a`)
- `af02a`: `MOVE.L #af030,(A6)` (→`af030`)
- `af030`: `JSR 4be06.L` (복귀 `af036`)
- `af036`: `JSR 49fc6.L` (복귀 `af03c`)
- `af03c`: `BCC.W af046` (→`af040`; 소비자)
- `af040`: `JMP 2a00.L`
- `af046`: `MOVE.L 72(A6),D0; BEQ.W af056` (→`af04e`)
- `af04e`: `MOVEA.L D0,A0; JSR 4ae4a.L` (복귀 `af056`; FLOW_ONLY)
- `af056`: `LEA aee12(PC),A0; JSR 1ab02.L` (복귀 `af060`)
- `af060`: `BCC.W af06a` (→`af064`; 소비자)
- `af064`: `JMP 2a00.L`
- `af06a`: `RTS`

**`dbf80` 3** (노드 callback)
- `dbf80`: `MOVE.W #19d7,D0; JSR 3af8.L` (복귀 `dbf8a`)
- `dbf8a`: `MOVE.W #731,D0; JSR 3af8.L` (복귀 `dbf94`)
- `dbf94`: `JMP 2a00.L`

**`eb24e` 1** (노드 callback)
- `eb24e`: `MOVE.W 76(A6),5e52(A5); MOVE.W 78(A6),5e54(A5); MOVE.W 7a(A6),5e56(A5); JMP 2a00.L`

**`eb266`/`eb2ba` 12** (노드 callback과 설치 callback)
- `eb266`: `LEA eb6e8.L,A0; JSR 490ba.L` (복귀 `eb272`; FLOW_ONLY)
- `eb272`: `EXT.L D0; LSL.L #8,D0; NEG.L D0; MOVE.L D0,7c(A6); LEA 10d256.L,A1; MOVE.W #e0,4(A1); MOVE.W #20,D0; MOVE.W #ec,D1; JSR 43e04.L` (복귀 `eb296`)
- `eb296` (JSR 복귀점이자 `eb5d2` index 0 설치 값): `MOVE.W #74d,D0; JSR 3af8.L` (복귀 `eb2a0`)
- `eb2a0`: `MOVE.W #0,84(A6); LEA 10d256.L,A1; MOVE.L #fffe8000,c(A1); MOVE.L #eb2ba,(A6)` (→`eb2ba`)
- `eb2ba`: `JSR eb616(PC)` (복귀 `eb2be`)
- `eb2be`: `JSR 43e34.L` (복귀 `eb2c4`)
- `eb2c4`: `LEA eb6ac.L,A0; JSR 4ae4a.L` (복귀 `eb2d0`)
- `eb2d0`: `LEA eb6ca.L,A0; JSR 4ae4a.L` (복귀 `eb2dc`)
- `eb2dc`: `LEA 10d256.L,A1; MOVE.W 4(A1),D0; CMPI.W #e0,D0; BPL.W eb2fc` (→`eb2ee`; `D0.W` − `e0`의 bit 15가 0이면 `eb2fc`)
- `eb2ee`: `JSR 3d44.L` (복귀 `eb2f4`)
- `eb2f4`: `MOVE.W #c,D0; JSR eb586(PC)` (복귀 `eb2fc`)
- `eb2fc`: `RTS`

**`eb352`/`eb376` 15** (표 설치 callback과 그 설치 callback)
- `eb352`: `MOVE.W 86(A6),D0; MOVE.W D0,D1; ASR.W #1,D0; MOVE.W eb2fe(PC,D0.W),88(A6); MOVE.L eb308(PC,D1.W),78(A6); LEA 10d256.L,A1; CLR.L c(A1); MOVE.L #eb376,(A6)` (→`eb376`; 표 WORD `eb2fe` + sext(`D0.W`), LONG `eb308` + sext(`D1.W`))
- `eb376`: `JSR eb616(PC)` (복귀 `eb37a`)
- `eb37a`: `JSR 43e34.L` (복귀 `eb380`)
- `eb380`: `LEA eb6ac.L,A0; JSR 4ae4a.L` (복귀 `eb38c`)
- `eb38c`: `LEA eb6ca.L,A0; JSR 4ae4a.L` (복귀 `eb398`)
- `eb398`: `MOVEA.L 78(A6),A0; JSR eb5e6(PC)` (복귀 `eb3a0`; FLOW_ONLY)
- `eb3a0`: `BCC.W eb3be` (→`eb3a4`; 소비자: Clear → `eb3be`, Set → `eb3a4`)
- `eb3a4`: `MOVE.W 86(A6),D0; ASR.W #1,D0; LEA eb31c(PC),A0; MOVE.W (A0,D0.W),80(A6); BPL.W eb3be` (→`eb3b8`; 옮긴 WORD의 bit 15가 0이면 `eb3be`)
- `eb3b8`: `MOVE.W 5e56(A5),80(A6)` (→`eb3be`)
- `eb3be`: `TST.W 80(A6); BEQ.W eb3e0` (→`eb3c6`)
- `eb3c6`: `JSR 49370.L` (복귀 `eb3cc`)
- `eb3cc`: `BCS.W eb3e0` (→`eb3d0`; 소비자: Set → `eb3e0`, Clear → `eb3d0`)
- `eb3d0`: `SUBQ.W #1,80(A6); BNE.W eb3e0` (→`eb3d8`; 뺀 WORD가 0이 아니면 `eb3e0`)
- `eb3d8`: `MOVE.W 88(A6),D0; JSR eb586(PC)` (복귀 `eb3e0`)
- `eb3e0`: `RTS`

**`eb586` 3** (상태 전이; D0.W = 새 상태 offset(0/4/8/c/10))
- `eb586`: `MOVE.W D0,D1; ASR.W #2,D0; MOVE.W 84(A6),D2; ADD.W D2,D2; ADD.W D2,D0; MOVE.B eb5aa(PC,D0.W),D2; BEQ.W eb5a8` (→`eb59a`; BYTE `eb5aa` + sext(`D0.W`)가 0이면 `eb5a8`)
- `eb59a`: `MOVE.W 84(A6),86(A6); MOVE.W D1,84(A6); MOVE.L eb5d2(PC,D1.W),(A6)` (→`eb5a8`; LONG `eb5d2` + sext(`D1.W`)를 node LONG `(A6)`에 쓴다)
- `eb5a8`: `RTS`

**`eb5e6`/`eb616` 5**
- `eb5e6`: `CMPI.W #80,(A0); BEQ.W eb610` (→`eb5ee`)
- `eb5ee`: `LEA 10d256.L,A1; MOVE.W 4(A1),D0; ADD.W (A0)+,D0; MOVE.W D0,4(A1); MOVE.L A0,78(A6); CMPI.W #80,(A0); BNE.W eb610` (→`eb60a`; `(A0)+`는 WORD 읽기 뒤 A0 += 2)
- `eb60a`: `ORI.B #1,CCR; RTS` (known 생산: C Set = 기록 끝)
- `eb610`: `ANDI.B #fe,CCR; RTS` (known 생산: C Clear)
- `eb616`: `LEA 10d256.L,A1; MOVE.W 4(A1),D1; SUBI.W #28,D1; RTS`

**`eb74a`/`eb75c` 2** (interpreter 명령 callback; interpreter가 live 대상 `JSR (A1)`으로 부른다)
- `eb74a`: `MOVEA.L (A0),A0; MOVE.L A0,72(A6); RTS` (LONG (A0)를 live bus로)
- `eb75c`: `MOVE.L #0,72(A6); RTS`

수: `aee30` 18 + `aef18` 5 + `aef34` 13 + `aef9a` 18 + `dbf80` 3 + `eb24e` 1 + `eb266` 12 + `eb352` 15 + `eb586` 3 + `eb5e6` 5 + `eb74a`/`eb75c` 2 = 95(`starts.txt`와 같다). 분류 합계: FLOW_ONLY 43(소비자 7 포함) + 생산 2 + Unknown 50 = 95.

## 구현 범위와 규약

- routing 8 범위(결정 2). 짝수 PC 518개 중 block 시작 95, 내부 423. 내부 PC 직접 진입은 `unsupported animation objects n11 PC`다. 범위 이웃은 기존 실행부 또는 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. `NEG`/`SUB`/`ADD`/`CMP`/`MULS`는 원래 폭의 2의 보수 산술로 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다(`ASR`는 부호 bit 채움을 명시, `MULS.W`는 sext16 곱 → 32비트(범위가 int32 안이라 overflow 없음) → 무부호 변환). flag는 같은 block 안의 Bcc만 쓴다(`BGT`는 N·V·Z를 명시 계산).
- **FLOW_ONLY 43개**(C 보존): `aee9e` `aeea2` `aef18` `aef1e` `aef28` `aef2c` `aef32` `aef3a` `aef76` `aef7c` `aef84` `aef8e` `aef92` `aef98` `aefc8` `aeffe` `af030` `af036` `af03c` `af040` `af04e` `af056` `af060` `af064` `af06a` `dbf94` `eb266` `eb2ba` `eb2be` `eb2c4` `eb2d0` `eb2ee` `eb2fc` `eb376` `eb37a` `eb380` `eb38c` `eb398` `eb3a0` `eb3c6` `eb3cc` `eb3e0` `eb5a8`.
- **소비자 7개**(FLOW_ONLY 안): `aee9e`(BCS) `aef28` `aef8e` `af03c` `af060` `eb3a0`(BCC) `eb3cc`(BCS). Unknown C면 `objects n11 caller requires known carry`(상태 보존).
- **known carry 생산 2개**: `eb60a`(Set), `eb610`(Clear).
- 그 밖 50 block(`MOVE`/`MOVEQ`/`MOVEA`+`MOVE`/`TST`/`CMPI`/`CMP`/`ADDQ`/`SUBQ`/`SUBI`/`NEG`/`EXT`/`LSL`/`MULS`/`ASR`/`ADD`/`CLR`+Bcc/JSR/RTS block, `MOVE.L #imm,(A6)` 설치 block, banked animation block `aefd6` `af002`, 표 읽기 block)은 Unknown이다. (`eb74a` `eb75c`의 `MOVE.L`, `eb616`의 `SUBI`, `aef62`의 `SUBQ`가 C를 만들지만 소비자가 없다: interpreter 복귀점, `JSR 43e34`, 같은 block의 `BCC`.)
- 제어 이동은 모두 정적이다. `eb59a`의 표 설치는 node LONG 쓰기일 뿐이다(값이 무엇이든 이 단위는 그 PC로 가지 않는다).
- 스택: `JSR` 복귀 LONG만.
- I/O port 쓰기 없음. bank 변경 없음. work RAM 밖 쓰기, 미해결·홀수 읽기는 기존 checked 오류다(예: `86(A6)`이 홀수일 때 `eb2fe`/`eb308`/`eb31c` 표의 WORD/LONG 읽기, A0 홀수의 `eb5e6`/`eb74a` 읽기).

## 자료

- [F] banked window LONG `20013c`(`aefe0` `af00c`; bank base 기준 live bus). 그 값(A1) + `8`/`c`의 LONG을 A1로 넘긴다(`49f8c` 목록). C++는 주소를 고정하지 않고 현재 bank base로 읽는다(PVC bank 모델).
- [F] fixed ROM(live bus): WORD 표 `eb2fe` [`0004` `0010` `0004` `0000` `0008`], LONG 표 `eb308` [`eb326` `eb326` `eb33c` `0` `eb326`], WORD 표 `eb31c` [`003c` `ffff` `0028` `0000` `0014`], 이동 기록 `eb326`/`eb33c`(WORD 10개 + 끝 `0080`), BYTE 전이 표 `eb5aa`(8×5), LONG 설치 표 `eb5d2` [`eb296` `eb3e2` `eb4a4` `eb352` `eb506`]. [I] 정상 입력에서 `84`/`86(A6)`은 `0/4/8/c/10`이라 index가 표 안이다. 이 단위는 index를 검사하지 않는다(원본대로 live bus로 읽고, 홀수·장치 밖은 checked 오류).
- [F] 이 단위가 직접 읽지 않고 주소만 넘기는 fixed ROM 자료: `aee12`(`1ab02` 범위 기록 `ffe0 ffe0 0040 0040`), `eb6ac` `eb6ca`(`4ae4a` 히트박스 기록), `eb6e8`(`490ba` 표).
- [F] work RAM: node(A6) WORD `1e` `20` `68` `76` `78` `7a` `7c` `7e` `80` `82` `84` `86` `88` `8a` `8c` `8e` `90`, LONG `(A6)` `c` `22` `72` `78` `7c`, BYTE `15`; 자식 node(A0) WORD `76` `7a` `84` `86` `88` `8a` `8c`; 부모 node(`c(A6)`) WORD `84` `8c`; A5 WORD `5e52` `5e54` `5e56`; 고정 work RAM `10d256`(WORD `4`, LONG `c`).
- [I] `aee30`은 방향(`76`)별로 속도 (`8e`,`90`)를 정하고 `78`+1개의 자식(`aef34`)을 만들어 간격 `8c`×`7e`로 배치하는 생성기로 보인다. 자식은 `88` frame 기다린 뒤 손자(`aef9a`, animation `db`)를 `7a`번 낸다. `eb266`/`eb352` 계열은 `10d256`(아마 화면/배경 객체)의 y를 이동 기록대로 움직이는 상태기계로 보인다. `dbf80`은 효과음 둘을 내고 끝난다. `eb74a`/`eb75c`는 interpreter script가 히트박스 포인터 `72(A6)`을 설정·해제하는 명령이다(`af046`이 그 포인터로 `4ae4a`를 부른다). 게임 의미는 미확인이다.

## 의존·경계

- [F] N11 → 기존(모두 routing됨): fade_card `28ae`(`aee8e` `aef48`; C 반환)·`2a00`(`JMP` 8곳), U11 `4be06`(`aef18` `af030`)·`49370`(`eb3c6`; C 반환), U05 `1ab02`(`aef1e` `aef84` `af056`; C 반환)·`c6a96`(`aef9a`), cleanup `43e34`(`aef3a` `eb2be` `eb37a`)·`43e04`(`eb272`), N05 `49214`(`aeea8` `aef58`), interpreter `49f8c`(`aefd6` `af002`)·`49fc6`(`af036`; C 반환), N08 `4ae4a`(`af04e` `eb2c4` `eb2d0` `eb380` `eb38c`), sound `3af8`(`dbf80` `dbf8a` `eb296`), U12 `490ba`(`eb266`), exit `3d44`(`eb2ee`). 이 callee들은 대기(waiting)를 돌려줄 수 있다(기존 동작).
- [F] 실행부 없는 경계: 없다. 시험은 다른 단위 callee의 stop 성립만 확인한다(F4 시험 경계 관례). rollback 탐침은 RAM `10fe00..10fefe`만 쓴다.
- [F] 다른 단위 → N11: interpreter callback(`eb74a` `eb75c`, 결정 4), stage event 표(`aee30` `eb24e` `eb266`), `dbfa6` 표(`dbf80`). 미연결 `eb3e2` 이후 함수들(`eb424` 등)이 `eb586`/`eb616`을 부른다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 95 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 2개, 그 밖 Unknown), 소비자 7개의 Unknown C checked 오류(상태 보존), zero-step, 내부 423 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 다른 단위 callee는 stop만. 고정 ROM 표(`eb2fe..eb352`, `eb5aa..eb5e6`, `aee12`)와 bank LONG `20013c`·그 목록은 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 생산 C는 실제 소비자 `eb3a0 BCC`를 복귀 주소로 둔 native 분기로 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(모든 진입, 실제 표·기록, 실제 callee 생산 C를 거친 소비자 분기, `eb3a0` 소비자로 확인한 `eb5e6` C).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0, base complete +14 15 기대. RNG 초기화 400 frame 차분: 불일치 0, complete +2 3 14 15 기대.

## 작업자 검증 기록 (scratch)

- [F] 공유 수정(브리프 허용 범위 + 결정 4): `animation_machine.cpp` routing `else if` 1개(N08 뒤, 8 범위)와 carry 보존 case 묶음 1개(`// BTST/BEQ changes only Z` 앞, 43개), `animation_machine_internal.h` 선언 1줄, `animation_machine_interpreter.cpp` `callback()` 허용 목록에 `eb74a` `eb75c`(결정 4), `Makefile`(source 목록·test target·실행 줄, Codex 공용 object 구조 유지), `tools/verify_animation_machine.py` SOURCES.
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0(기존 test 모두 통과). 새 test: `animation machine objects n11: 360 fixtures (19 checked errors, 96 known C), 95 blocks, 1386 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen_n11.py`): 95 시작 모두 native fixture로 덮임. 소비자 7개 Unknown C 오류, 시작마다 3 carry 한 block 후계·carry 분류, zero-step, 내부 423 PC, 홀수 PC 16개, RAM rollback 탐침(`10fe50` `10fe60` `10fe70`, RTS 끝 14 fixture의 복귀 LONG `10fe80`), 다른 단위 callee stop 17종. 실제 producer를 따라간 행: `28ae`(`290e` Clear → `aeea2` → `2a00`; `2908` Set → `aeea8`), `1ab02`(`1ab7a` Clear / `1aafc` Set → `aef28` `aef8e` `af060`). `eb5e6` 생산 C는 STOP 복귀 LONG을 실제 소비자 `eb3a0`로 바꾼 native 실행의 분기로 확인했다(15건, C Clear·Set 양쪽). 경계값: `MULS.W` `8000`×`8000`, `ffff`×`ffff`, `7fff`×`8001`; `aeefc` BGT overflow 쌍(`7fff`+1 vs `7fff`/`8000`); `eb2dc` BPL(`df`/`e0`/`80df`/`80e0`); `eb272` EXT/LSL/NEG; `eb586` 음수 index(`fffc` → 7, LONG `eb5d2`−4); `eb3a4` 음수 WORD → `5e56(A5)`. 돌연변이 확인: BGT의 V 누락, BGT의 Z 누락, `eb610` C 반전, `MULS` 부호 무시, `ASR.W` 부호 채움 누락, BPL을 무부호 비교로, `SUBQ` borrow 조건, `EXT.L` 누락, `ADD.W D2,D2` 누락, `MULS` 피연산자 바꿈이 모두 test에서 실패했다(10/10).
- [F] 실제 ROM 차분(`realrom/real_n11.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, seed 1·2·3 각 1,500건; native stop은 STOP, `2a00`(다른 단위 진입, stop만), sprite 대기 `cd58`, 이 트리 routing 밖 PC, 소비자 `eb3a0` 분기 뒤): 불일치 0/0/0, 실제 소비자 `eb3a0` 분기 C와 C++ carry 불일치 0(seed별 60/67/51건, C Clear·Set 양쪽), 비교된 사례만으로 95 시작 모두 도달(seed마다 95/95). 실제 표 `eb2fe..eb352`·`eb5aa..eb5e6`, 실제 이동 기록 `eb326`/`eb33c`, 실제 bank LONG `20013c`, 실제 callee(`28ae` `1ab02` `49fc6` `49370` `4ae4a` `c6a96` `49f8c` `3af8` `43e04` `43e34` `3d44` `490ba` `4be06` `49214`)를 거친다. native port 쓰기(674/696/690건, sound 등)도 순서까지 같다. native가 6,000,000 명령 안에 멈추지 않은 114/112/104건(임의 RAM의 긴 자식 루프·interpreter·list walk)은 제외했다. harness는 기존 실행부 block 내부 PC(재범위 15개 + exit `3d50`)를 routing된 것으로 본다(`3d4c` block이 `BRA 3ac8`까지 한 block).
- [F] 기준(`7dfe2f6` 사본 `ms5-scratch/n11/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 12,968·node 102,054, 불일치 0, 자연 완주 119. N11 뒤: pass 13,208·node 108,064, 불일치 0, 자연 완주 121(+14 15), 회귀 0, 변화는 seed 14 15뿐(첫 미연결 `dbf80` → 완주).
- [F] RNG 초기화 400 frame 차분: 기준 일치 pass 40,800·node 297,077, complete 102. N11 뒤 pass 42,400·node 312,309, 불일치 0, `other` 없음, complete 106(+2 3 14 15), 회귀 0, 변화는 그 4 seed뿐. 응답 `00` 변형 6 seed: complete 4 → 6(case 2 3), 불일치 0. 정적 재생 예측과 같다.
- [F] ROM SHA256·mtime 작업 전후 같음.

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] 표 설치 대상 `eb3e2` `eb4a4` `eb506`과 `eb3e2..eb586`의 미연결 함수(같은 상태기계의 나머지 상태)는 이 단위 밖이다. 400 frame 자연 기록에서 실행되지 않는다(정적 재생에서 seed 2 3이 완주로 예측됨). 실행되면 다음 frame dispatch에서 `unsupported animation machine PC`가 된다.
3. [U] `aee1a`(stage event 표 `e8eb0`의 `JMP 2a00.L` callback)는 범위 밖이다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n11/`(`n11blocks.py` block·범위 계산, `n11refs.py`/`n11raw.py` 참조, `n11reach.py` 자연 도달·기대 완주, `n11dis.py`, `n11route.py` routing 확인; 저장소 밖).

- (메인) 결정 4 대체: 인터프리터 callback 허용 목록은 `5ef29c8`에서 제거되어 `eb74a`/`eb75c` 개별 추가는 병합에서 빼고 routing 판정에 맡긴다.
