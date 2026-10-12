# 객체 callback F4 N06: `b9dc6` 계열 객체(설치 `b9df0` `b9e0c` `b9e16` `b9de6` `b9f70` `ba1e6`, `28ae` 자식 `b9e64` `ba1cc`, 공용 꼬리 `ba1b8`, 설치 callback `ba196`), 판정 루틴 `ba234`/`eb774`(C 반환), 표 누적 `ba2d6`, 자식 생성 `ba310` `ba386`, BYTE `15` 복사 `491b6`, 지형 BYTE 조회 `e90d8`, 대기 callback `d9bcc`(설치 `d9bea`) 계약

**상태: 계약 초안(작업자 Claude Opus 5.5 / high). 메인 결정 전이다. 아래 "작업자 검증 기록"은 이 초안대로 구현한 scratch 기록이다(구현·검증 완료, 커밋하지 않음).**

범위 근거는 재범위 문서 `animation-machine-object-callbacks-f4-rescope.md`(SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 메인 결정 1~5와 N06 행(옛 U23)이다. 단위 형식과 규약은 N04 계약(`animation-machine-objects-n04-contract.md`, SHA256 `80e41996735a39feeb7f89ddbb4e3267d993bc4a1431a214f2be4af2e05a31e3`; bank animation 형식, 소비자·생산자 분류), U11 계약(SHA256 `ab51cd6d422c9a97fc9a705b4d11254716b69bebd4610a93c0cd58c656940d7d`; `49370` `497b6` 반환 C), U10 계약(SHA256 `2b3c1f73213c12bb8f3b5512968210e99d1986a04b90321ce48e99c0fa98147c`; `bac72 JSR eb774` 뒤 `bac78 BCC` 소비자)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC와 실행부 없는 미연결 PC는 경계다(아래 "의존·경계"). 결정 6(원 범위): `TRAP #f`는 실행부 없는 checked 경계다.
- 재범위 결정 2: 단위 안에서 설치되는 callback은 본문이 단위 범위 안에 있으면 포함하고, 범위 밖 설치 대상은 값(LONG)만 쓰는 경계다.
- U01~U20b·N01~N04 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`Scc`)과 Z만 바꾸는 `BSET`만인 block, callee C를 소비하는 단독 Bcc는 FLOW_ONLY다. 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다. block 사이 flag 재계산은 predecessor가 하나일 때만 쓴다(predecessor가 여럿이면 flag를 쓰는 분기를 각 predecessor block에 묶는다; N04 `ab1a6` 선례). 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C를 소비자에서 쓰려면 native 분기 결과로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N06의 코드는 모두 `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료(`2001d0`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n06`(HEAD `5fd7b40` = N04까지 통합, `engine/src/animation_machine.cpp` SHA256 `ff4f12568fa3e10bc9f77367231ba0feeda3b688c972605636d67fa30d19cd50`, routing 규칙 61개)을 참조했다. 동시에 진행하는 N05(`1a3ae..1a3c8` `1ab80..1abda` `49214..49260` `bdcc6..bdf82` `c5e6c..c5e7c` `c5fd8..c6012` `d1cd8..d1e6e` `d22e6..d23d8` `d3c2a..d3c40` `dceca..dcf42`, 작업 트리 `metalslug-n05`)와 범위·경계가 겹치지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n06/n06blocks.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **N06 = 123 block**, 코드 13 범위 1,000바이트다. 재범위 N06 행의 123 block(함수 진입 16개)과 같다. 결정 2의 범위 안 설치 callback(`b9df0` `b9e0c` `b9e16` `b9de6` `b9f70` `ba1e6` `d9bea`)과 범위 안 `28ae` 자식(`b9e64` `ba1cc`)은 모두 이미 block 시작이다. 범위 밖 설치 값 `b9f96`(`ba1ae`) `b9f9a`(`b9f8c`)와 자식 값 `4841a`(`d9bf4`)는 고아 설치 경계로 남는다(재범위 결정 3).
- [F] 진입 16개: 함수 `491b6` `ba234` `ba2d6` `ba310` `ba386` `e90d8` `eb774`(호출 진입), node callback `b9dc6`(fixed ROM LONG `e8f38`) `d9bcc`(fixed ROM LONG `d9c18`), 설치 callback `b9df0` `b9e16` `b9f70` `ba196`(`ba190`이 설치; `ba190`은 N06 밖 `b9f9a` 계열 본문) `ba1e6`, `28ae` 자식 `b9e64`(`ba324`) `ba1cc`(`ba386`). 그 밖 설치 callback `b9e0c` `b9de6` `d9bea`는 fall-through 또는 분기 대상이기도 하다.
- [F] 묶인 Bcc 없음. block을 Bcc로 시작하는 곳은 모두 callee 반환 C 소비자(12개)다. 따라서 block 사이 flag 재계산은 쓰지 않는다. 계산 PC(JMP/JSR 표, 레지스터 간접)·SUBX/ADDX/DIVx/MULx·I/O port 쓰기·bank 변경은 없다. PC 상대 `JSR d16(PC)` 5곳(`ba310` `ba234` `ba2d6` `ba386` 대상)은 정적이다.
- [F] **TRAP 경계 3개**: `ba338`(`ba334 BCS`의 fall-through, 문자열 `fail_mtask`), `ba364`(`ba346 BLE`의 fall-through, `HIGHT_OVER`), `ba39a`(`ba396 BCS`의 fall-through, `fail_mtask`). routing 밖이다.
- [F] **carry**: 소비 block 12개 `b9e46`(`1aa7e`), `ba1ec`(`288c`), `ba23a`(N06 `eb774`), `ba282`(경계 `497f0`), `ba29c`(`497b6`), `ba334` `ba396`(`28ae`), `eb77a`(`49370`), `eb786` `eb79c`(`49392`), `eb790` `eb7a6`(경계 `49416`). known 생산 block 2개 `eb7aa`(`ORI #1,CCR` Set) `eb7b0`(`ANDI #fe,CCR` Clear): `eb774` 반환 C는 N06 `ba23a`와 U10 `bac78 BCC`, 미연결 `bf9a2 BCC`가 소비한다. 그 밖 함수(`491b6` `ba2d6` `e90d8` 등)의 반환 C는 소비자가 없어 Unknown이다(아래 "carry").
- [F] 경계(실행부 없는 미연결 callee): `49416`(`eb78a` `eb7a0` JSR) `497f0`(`ba27c` JSR). 고아 설치 값: `b9f96` `b9f9a`, `28ae` 자식 값 `4841a`.
- [F] 자료 읽기: bank window LONG `2001d0`(2곳)과 그 값 + `70`/`58`의 LONG, fixed ROM WORD 표(`8c(A6)`가 가리키는 `ba2fa` `ba304` `ba30e` 등; `ba2d6`이 `0080`까지 더함), work RAM BYTE `100012`(`d9bcc`)와 `5e30(A5)` + `D0.W`(`e90e4`), WORD `5418(A5)`(`b9e54`). 모두 live bus로 읽는다. `ba3de` `ba3f6` `ba432` `ba214`~`ba22c`는 다른 실행부·경계에 넘기는 주소다.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng` `dyn_base`, TB 기준): seed 40 41만 N06 PC를 실행하고, 123 시작 중 61개가 TB 시작으로 나타난다(두 기록 같음). 나머지는 typed fixture로 덮는다.
- [F] 기준 측정(이 작업 트리 base `5fd7b40`의 `git archive` 사본, scratch 출력 `ms5-scratch/n06/fp/base_*`)과 기대는 아래 "작업자 검증 기록"에 적는다. 정적 재생(`n06reach.py`, routing + N06 범위)에서 seed 40 41의 첫 미연결 지점 f0 `d9bcc`가 사라져 두 기록 모두 완주로 바뀐다(+2). 다른 seed의 첫 미연결 지점은 바뀌지 않는다.

## 메인 결정 (초안 권고)

1. **범위 = 재범위 N06 행 그대로(123 block).** 범위 밖 설치 값 `b9f96` `b9f9a`(`b9f9a` 계열 본문 `b9f9a..ba196`, 43 block 안팎)와 자식 값 `4841a`는 고아 설치 정리 단계로 미룬다(재범위 결정 3). [F] `ba196`은 `b9f9a` 계열(`ba190`)이 설치하지만 본문이 N06 범위 `ba196..ba214` 안이고 재범위 진입 목록에 있으므로 포함한다. [F] 두 기록에서 `b9f96` `b9f9a` `ba196`은 실행되지 않는다.
2. **routing 범위는 코드만(13 범위).** `491b6..491c4` `b9dc6..b9f32` `b9f62..b9f96` `ba196..ba214` `ba234..ba2b6` `ba2d6..ba2fa` `ba310..ba338` `ba346..ba364` `ba372..ba39a` `ba3a8..ba3b6` `d9bcc..d9c0a` `e90d8..e90f2` `eb774..eb7b6`(짝수 PC 500개, block 시작 123, 내부 377).
   - `b9f32..b9f62`(`ba102 BRA b9f32`로만 들어오는 `b9f9a` 계열 경로), `ba2b6..ba2d6`(함수 `ba2b6`, `b9f9a` 계열 `ba020`이 부름), `ba214..ba234` `ba2fa..ba310`(WORD 표) `ba3b6..`(표)는 routing하지 않는다.
   - TRAP+문자열 `ba338..ba346` `ba364..ba372` `ba39a..ba3a8`은 routing하지 않는다.
   - `d9c0a`(`d9c04 JMP` 뒤 죽은 `RTS`)는 routing하지 않는다.
   - 재범위 표기 `491b6..491c4` `e90d8..e90f2` `eb774..eb7b6`의 이웃은 U17 `491c4`, cleanup `e90ca..e90d8`, U06 `eb7b6`, N04 `eb766..eb774`다(겹침 없음).
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n06.cpp`의 `animation_objects_n06_block`. 오류는 `unsupported animation objects n06 PC`(내부 PC), `objects n06 caller requires known carry`(소비자 12개의 Unknown C).
4. **무효화 탐침**(F4 test 경계 관례대로 고친다): `engine/tests/animation_machine_objects_u06_test.cpp` `interior()`의 `outside[]` 중 `0xeb7b4`(이제 N06 `eb7b0` block의 내부 PC) → work RAM 탐침 `0x10fe24`. U10 test의 `eb774`(stop 경계)는 stop 성립만 확인하므로 영향이 없다. `tools/`에는 N06 PC를 경계로 쓰는 곳이 없다.

## 원본 바이트 근거

[F] 코드 13 범위 합계 1,000바이트. 범위 순서로 이어 붙인 SHA256 `2febefb0e2674c232e4117a4ac188b1006c54fb70297474707e0da13c4eb1bd5`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `491b6..491c4` | 14 | `f4bb2ea3a0e1631e99cce42a767911e60a6732405c87b8536c62e7fa816441ae` | `491b6`(BYTE `15` 하위 2bit를 A0 node로) |
| `b9dc6..b9f32` | 364 | `1f10bdc69bff3387b404a686fd19d5fba7821d73f222ed25e1562b36b4550438` | `b9dc6`, 설치 `b9df0` `b9e0c` `b9e16` `b9de6`, 자식 `b9e64` |
| `b9f62..b9f96` | 52 | `e9d1aabde6e570b335dd250be4571358c0b1fba1dd46ed4624e552d3d10d7238` | 설치 `b9f70` |
| `ba196..ba214` | 126 | `96a8113341babec35d2b07c33a8fe2c387867ac307b60e47f9c3750b8c0320ac` | 설치 `ba196`, 공용 꼬리 `ba1b8`, 자식 `ba1cc`, 설치 `ba1e6` |
| `ba234..ba2b6` | 130 | `c83c0144697fbd05e5a670c60c20b9eff13055325ed9fe32200f1313281f8fa5` | `ba234`(판정, `ST.B a1`/`a2`) |
| `ba2d6..ba2fa` | 36 | `64990d4adf6a258b2ef785d68aebd3b64a271051a0d41beb727708ef5276180b` | `ba2d6`(WORD 표 누적) |
| `ba310..ba338` | 40 | `1861a3d748c14d7847ad150ae4647fc0a50cad0438c2967b2fb20745e42ea67f` | `ba310`(`28ae` 자식 `b9e64`) |
| `ba346..ba364` | 30 | `d2e78db4b5fb2acf901fb391c9179ff02270976e3977cefe828a5e026bbaf509` | 자식 node 초기화 |
| `ba372..ba39a` | 40 | `fbe81b5a29196d3c13482441279c5bdf51ec9f66ebbaa0d66cc2b20fdda45dc8` | `ba372`, `ba386`(`28ae` 자식 `ba1cc`) |
| `ba3a8..ba3b6` | 14 | `a50913d5d65848b708374f41984ee0eb1fbdafd79632a898ea64277e5d33162b` | `ba3a8` |
| `d9bcc..d9c0a` | 62 | `eee2380f083e3ba07e242c2f44d884e3145620fa42047e2195f4f5b5ba84b173` | `d9bcc`, 설치 `d9bea` |
| `e90d8..e90f2` | 26 | `666dba36ac93009b8ae2a001bcb8e9958c7380ea4687962abfe4d1fdc14fc0af` | `e90d8`(work RAM BYTE 표 `5e30(A5)`) |
| `eb774..eb7b6` | 66 | `c39c57a615699801544cddf22c3d99f322bdb8e32b85d738b552bdc2a77b6515` | `eb774`(C 반환) |

- [F] 범위 밖 이웃: `491b4`(U12), `491c4`(U17), `b9dc4`(미연결), `b9f32..b9f62`(`b9f9a` 계열 경로, 미연결), `b9f96..ba196`(고아 설치 `b9f96` `b9f9a` 본문, 미연결), `ba214..ba234`(WORD 표 `ba214` `ba21c` `ba224` `ba22c`, `497f0`/`497b6`에 A1로 넘김), `ba2b6..ba2d6`(함수 `ba2b6`, 미연결), `ba2fa..ba310`(WORD 표), TRAP 3곳+문자열, `ba3b6..`(표 `ba3de` `ba3f6` `ba432`), `d9bca`(미연결), `d9c0a`(죽은 RTS), `e90ca..e90d8`(cleanup), `e90f2..`(미연결), `eb766..eb774`(N04), `eb7b6..`(U06).
- [F] TRAP 바이트: `ba338` `4e4f`+`fail_mtask\0\0`, `ba364` `4e4f`+`HIGHT_OVER\0\0`, `ba39a` `4e4f`+`fail_mtask\0\0`.
- [F] 참조: `491b6`은 `JSR`/`JMP` 60곳 이상(N06 `ba37e` `ba3a8`, 나머지 미연결; 바로 뒤가 Bcc인 곳은 없다). `e90d8`은 N06 `b9ddc`와 미연결 `86926` `d629e` `d62cc` `d62fa` `d6328` `d666e` `d69c2`(바로 뒤 `TST`/`MOVE`/`CMP`, C 소비 없음). `eb774`는 N06 `ba234`, U10 `bac72`, 미연결 `bf99c`(모두 바로 뒤 `BCC`). `49416`은 N06 `eb78a` `eb7a0`과 미연결 10곳(모두 바로 뒤 `BCS`), `497f0`은 N06 `ba27c`과 미연결 `9c8a6` `a08ac` `a2802`(뒤 `BCS`), `73eb8` `c436e` `c437a`(JMP).

## block 목록과 실행 의미

[F] 123 block. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `.W` 연산은 하위 WORD만, `.B`는 하위 BYTE만 바꾼다. `MOVEQ`는 LONG 전체를 부호확장 값으로 쓴다. 비교 분기: `BCC`/`BCS`는 무부호 빌림, `BHI`는 무부호 >, `BGT`/`BLE`는 부호 있는 비교(N⊕V로 overflow 포함 정확), `BEQ`/`BNE`는 결과 0 여부다. `ST.B`는 BYTE `ff`를 쓰고 CCR을 바꾸지 않는다.

"anim(k, bank, d16)"은 `LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d16(A1),A1; JSR 49f8c.L`(N04 anim과 같음; bank LONG과 그 값 + d16의 LONG을 live bus로 읽는다).

**`491b6` 1** (호출 진입; A0 = 대상 node)
- `491b6`: `MOVE.B 15(A6),D0; ANDI.B #3,D0; MOVE.B D0,15(A0); RTS`

**`b9dc6` 계열 25** (node callback `b9dc6`; 설치 `b9df0` `b9e0c` `b9e16` `b9de6`)
- `b9dc6`: `TST.W 7e(A6); BNE.W b9dd4` (→`b9dce`)
- `b9dce`: `MOVE.W #70,7e(A6)` (→`b9dd4`)
- `b9dd4`: `JSR ba310(PC)` (FLOW_ONLY)
- `b9dd8`: `MOVE.B 6b(A6),D0; JSR e90d8.L`
- `b9de2`: `MOVE.B D0,9f(A6)` (→`b9de6`)
- `b9de6` (설치 callback, `b9e28`이 설치): `CLR.B a1(A6); MOVE.L #b9df0,(A6)` (→`b9df0`)
- `b9df0` (설치 callback): `JSR 43e34.L` (FLOW_ONLY)
- `b9df6`: `JSR ba234(PC)` (FLOW_ONLY)
- `b9dfa`: `TST.B a1(A6); BEQ.W b9e08` (→`b9e02`)
- `b9e02`: `MOVE.L #b9e0c,(A6)` (→`b9e08`)
- `b9e08`: `BRA.W b9e32` (FLOW_ONLY)
- `b9e0c` (설치 callback): `CLR.B a2(A6); MOVE.L #b9e16,(A6)` (→`b9e16`)
- `b9e16` (설치 callback): `JSR 43e34.L` (FLOW_ONLY)
- `b9e1c`: `JSR ba234(PC)` (FLOW_ONLY)
- `b9e20`: `TST.B a2(A6); BEQ.W b9e2e` (→`b9e28`)
- `b9e28`: `MOVE.L #b9de6,(A6)` (→`b9e2e`)
- `b9e2e`: `BRA.W b9e32` (FLOW_ONLY)
- `b9e32`: `MOVE.W 80(A6),D0; BNE.W b9e54` (→`b9e3a`)
- `b9e3a`: `MOVEA.L #ba3de,A0; JSR 1aa7e.L` (FLOW_ONLY; `ba3de`는 `1aa7e`의 입력 주소)
- `b9e46`: `BCC.W b9e50` (→`b9e4a`; 소비자, `1aa7e` 반환 C)
- `b9e4a`: `JMP 2a24.L` (FLOW_ONLY)
- `b9e50`: `BRA.W b9e62` (FLOW_ONLY)
- `b9e54`: `CMP.W 5418(A5),D0; BHI.W b9e62` (→`b9e5c`; 무부호 `D0.W` > WORD `5418(A5)` → `b9e62`)
- `b9e5c`: `JMP 2a24.L` (FLOW_ONLY)
- `b9e62`: `RTS` (FLOW_ONLY)

**`b9e64` 계열 20** (`ba324`가 만든 `28ae` 자식; 설치 `b9f70`, 설치 값 `b9f9a`)
- `b9e64`: `MOVEQ #0,D0; MOVE.W 78(A6),D1; JSR 49290.L`
- `b9e70`: `JSR ba386(PC)` (FLOW_ONLY)
- `b9e74`: `LEA ba3f6.L,A0; MOVE.L A0,84(A6); CMPI.W #2,76(A6); BNE.W b9eb4` (→`b9e88`)
- `b9e88`: anim(`203`, `2001d0`, `70`) (복귀 `b9eb0`); `b9eb0`: `BRA.W b9edc` (FLOW_ONLY)
- `b9eb4`: anim(`203`, `2001d0`, `58`) (복귀 `b9edc`)
- `b9edc`: `MOVE.W #801,68(A6); MOVE.W #801,1e(A6); CMPI.W #2,76(A6); BNE.W b9f08` (→`b9ef2`)
- `b9ef2`: `MOVE.W #73,D0; MOVE.W #1c,D1; MOVE.B #0,D2; JSR c6a96.L`; `b9f04`: `BRA.W b9f1a` (FLOW_ONLY)
- `b9f08`: `MOVE.W #73,D0; MOVE.W #16,D1; MOVE.B #0,D2; JSR c6a96.L` (복귀 `b9f1a`)
- `b9f1a`: `MOVE.L #18000,3a(A6); TST.B 7a(A6); BNE.W b9f2e` (→`b9f2a`)
- `b9f2a`: `NEG.L 3a(A6)` (→`b9f2e`)
- `b9f2e`: `BRA.W b9f62` (FLOW_ONLY)
- `b9f62`: `MOVE.L #ba30e,8c(A6); MOVE.L #b9f70,(A6)` (→`b9f70`)
- `b9f70` (설치 callback): `JSR ba2d6(PC)` (FLOW_ONLY)
- `b9f74`: `JSR 43e34.L` (FLOW_ONLY)
- `b9f7a`: `JSR 49fc6.L` (FLOW_ONLY; 반환 C는 다음 `TST.B`가 덮는다)
- `b9f80`: `MOVEA.L c(A6),A0; TST.B a1(A0); BEQ.W b9f92` (→`b9f8c`; 부모 node BYTE `a1`)
- `b9f8c`: `MOVE.L #b9f9a,(A6)` (→`b9f92`; 고아 설치 값)
- `b9f92`: `BRA.W ba1b8` (FLOW_ONLY)

(`b9e64`~`b9f2e` 13 + `b9f62`~`b9f92` 7 = 20.)

**`ba196`/`ba1b8`/`ba1cc` 18** (설치 callback `ba196`, 공용 꼬리 `ba1b8`, `ba386`이 만든 `28ae` 자식 `ba1cc`과 그 설치 `ba1e6`)
- `ba196` (설치 callback): `JSR ba2d6(PC)` (FLOW_ONLY)
- `ba19a`: `JSR 43e34.L` (FLOW_ONLY)
- `ba1a0`: `JSR 49fc6.L` (FLOW_ONLY)
- `ba1a6`: `SUBQ.W #1,9c(A6); BGT.W ba1b4` (→`ba1ae`; 결과 > 0(부호) ⇔ sext(이전 값) > 1)
- `ba1ae`: `MOVE.L #b9f96,(A6)` (→`ba1b4`; 고아 설치 값)
- `ba1b4`: `BRA.W ba1b8` (FLOW_ONLY)
- `ba1b8`: `MOVEA.L 84(A6),A0; CMPA.W #0,A0; BEQ.W ba1ca` (→`ba1c4`; `CMPA.W #0`은 부호확장 0과 LONG 비교)
- `ba1c4`: `JSR 4706c.L` (FLOW_ONLY)
- `ba1ca`: `RTS` (FLOW_ONLY)
- `ba1cc`: `MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L`
- `ba1d6`: `LEA ba432.L,A0; MOVE.L A0,84(A6); MOVE.L #ba1e6,(A6)` (→`ba1e6`)
- `ba1e6` (설치 callback): `JSR 288c.L` (FLOW_ONLY)
- `ba1ec`: `BCS.W ba1f6` (→`ba1f0`; 소비자, `288c` 반환 C)
- `ba1f0`: `JMP 2a00.L` (FLOW_ONLY)
- `ba1f6`: `JSR 43e34.L` (FLOW_ONLY)
- `ba1fc`: `MOVEA.L 84(A6),A0; CMPA.W #0,A0; BEQ.W ba212` (→`ba208`)
- `ba208`: `MOVEQ #0,D0; MOVEQ #f,D1; JSR 47070.L`
- `ba212`: `RTS` (FLOW_ONLY)

**`ba234` 23** (판정; `eb774` C로 시작, `ST.B a1(A6)`/`a2(A6)`로 결과 기록)
- `ba234`: `JSR eb774.L` (FLOW_ONLY)
- `ba23a`: `BCC.W ba2b0` (→`ba23e`; 소비자, `eb774` 반환 C)
- `ba23e`: `CMPI.W #2,76(A6); BNE.W ba260` (→`ba248`)
- `ba248`: `TST.B a4(A6); BNE.W ba258` (→`ba250`)
- `ba250`: `LEA ba224(PC),A1; BRA.W ba25c` (FLOW_ONLY)
- `ba258`: `LEA ba22c(PC),A1` (→`ba25c`; FLOW_ONLY)
- `ba25c`: `BRA.W ba274` (FLOW_ONLY)
- `ba260`: `TST.B a4(A6); BNE.W ba270` (→`ba268`)
- `ba268`: `LEA ba214(PC),A1; BRA.W ba274` (FLOW_ONLY)
- `ba270`: `LEA ba21c(PC),A1` (→`ba274`; FLOW_ONLY)
- `ba274`: `TST.B a4(A6); BEQ.W ba296` (→`ba27c`)
- `ba27c`: `JSR 497f0.L` (FLOW_ONLY; 경계 callee)
- `ba282`: `BCC.W ba28e` (→`ba286`; 소비자, `497f0` 반환 C)
- `ba286`: `ST.B a1(A6); BRA.W ba292` (FLOW_ONLY)
- `ba28e`: `ST.B a2(A6)` (→`ba292`; FLOW_ONLY)
- `ba292`: `BRA.W ba2ac` (FLOW_ONLY)
- `ba296`: `JSR 497b6.L` (FLOW_ONLY)
- `ba29c`: `BCC.W ba2a8` (→`ba2a0`; 소비자, `497b6` 반환 C)
- `ba2a0`: `ST.B a1(A6); BRA.W ba2ac` (FLOW_ONLY)
- `ba2a8`: `ST.B a2(A6)` (→`ba2ac`; FLOW_ONLY)
- `ba2ac`: `BRA.W ba2b4` (FLOW_ONLY)
- `ba2b0`: `ST.B a2(A6)` (→`ba2b4`; FLOW_ONLY)
- `ba2b4`: `RTS` (FLOW_ONLY)

**`ba2d6` 3** (WORD 표 누적)
- `ba2d6`: `MOVEA.L 8c(A6),A0; CMPI.W #80,(A0); BEQ.W ba2f0` (→`ba2e2`; WORD (A0)를 live bus로 읽음)
- `ba2e2`: `MOVE.W 32(A6),D0; ADD.W (A0)+,D0; MOVE.W D0,32(A6); MOVE.L A0,8c(A6)` (→`ba2f0`; 읽기 순서 `32(A6)`, `(A0)`; A0 += 2)
- `ba2f0`: `ANDI.L #ffff0000,32(A6); RTS`

**`ba310`/`ba386` 11** (`28ae` 자식 생성; 실패 시 TRAP 경계)
- `ba310`: `MOVE.W 7e(A6),94(A6); TST.W 76(A6); BEQ.W ba324` (→`ba31e`)
- `ba31e`: `BSET.B #0,15(A6)` (→`ba324`; FLOW_ONLY)
- `ba324`: `MOVEA.L #b9e64,A0; MOVE.W #0,D0; JSR 28ae.L`
- `ba334`: `BCS.W ba346` (→`ba338` TRAP 경계; 소비자, `28ae` 반환 C)
- `ba346`: `MOVE.W 76(A6),76(A0); MOVE.W 78(A6),78(A0); MOVE.W 94(A6),94(A0); MOVE.W 78(A0),D0; CMP.W 94(A0),D0; BLE.W ba372` (→`ba364` TRAP 경계; A0 = `28ae`가 돌려준 자식 node; 읽기·쓰기는 원래 순서대로, `78(A0)` `94(A0)`는 쓴 뒤 다시 읽는다; sext(`D0.W`) ≤ sext(WORD `94(A0)`) → `ba372`)
- `ba372`: `MOVE.B 7a(A6),7a(A0); MOVE.B 7b(A6),7b(A0); JSR 491b6.L`
- `ba384`: `RTS` (FLOW_ONLY)
- `ba386`: `MOVEA.L #ba1cc,A0; MOVE.W #0,D0; JSR 28ae.L`
- `ba396`: `BCS.W ba3a8` (→`ba39a` TRAP 경계; 소비자)
- `ba3a8`: `JSR 491b6.L` (FLOW_ONLY)
- `ba3ae`: `MOVE.W 76(A6),76(A0); RTS`

**`d9bcc` 7** (node callback; 설치 `d9bea`, 자식 값 `4841a`)
- `d9bcc`: `CMPI.B #1,100012.L; BEQ.W d9bde` (→`d9bd8`; work RAM BYTE)
- `d9bd8`: `JMP 2a00.L` (FLOW_ONLY)
- `d9bde`: `MOVE.W #294,76(A6); MOVE.L #d9bea,(A6)` (→`d9bea`)
- `d9bea` (설치 callback): `SUBQ.W #1,76(A6); BCS.W d9bf4` (→`d9bf2`; 빌림 ⇔ 이전 WORD = 0)
- `d9bf2`: `RTS` (FLOW_ONLY)
- `d9bf4`: `MOVEA.L #4841a,A0; MOVE.W #a,D0; JSR 28ae.L` (`4841a`는 고아 자식 값; `28ae` 반환 C는 다음 `JMP`가 쓰지 않는다)
- `d9c04`: `JMP 2a00.L` (FLOW_ONLY)

**`e90d8` 3** (지형 BYTE 조회; D0.B = index)
- `e90d8`: `CMPI.B #c,D0; BCS.W e90e4` (→`e90e0`; 무부호 `D0.B` < `c` → `e90e4`)
- `e90e0`: `MOVEQ #0,D0; RTS`
- `e90e4`: `ANDI.W #ff,D0; LEA 5e30(A5),A0; MOVE.B (A0,D0.W),D0; RTS` (BYTE `5e30(A5)` + `D0.W`, `D0.W` ≤ `ff`)

**`eb774` 12** (C 반환 판정; 생산 2)
- `eb774`: `JSR 49370.L` (FLOW_ONLY)
- `eb77a`: `BCS.W eb7b0` (→`eb77e`; 소비자, `49370` 반환 C)
- `eb77e`: `MOVEQ #0,D0; JSR 49392.L`
- `eb786`: `BCC.W eb794` (→`eb78a`; 소비자, `49392` 반환 C)
- `eb78a`: `JSR 49416.L` (FLOW_ONLY; 경계 callee)
- `eb790`: `BCS.W eb7b0` (→`eb794`; 소비자, `49416` 반환 C)
- `eb794`: `MOVEQ #1,D0; JSR 49392.L`
- `eb79c`: `BCC.W eb7aa` (→`eb7a0`; 소비자)
- `eb7a0`: `JSR 49416.L` (FLOW_ONLY)
- `eb7a6`: `BCS.W eb7b0` (→`eb7aa`; 소비자)
- `eb7aa`: `ORI.B #1,CCR; RTS` (known 생산: C Set)
- `eb7b0`: `ANDI.B #fe,CCR; RTS` (known 생산: C Clear)

수: `491b6` 1 + `b9dc6` 계열 25 + `b9e64` 계열 20 + `ba196`/`ba1b8`/`ba1cc` 18 + `ba234` 23 + `ba2d6` 3 + `ba310`/`ba386` 11 + `d9bcc` 7 + `e90d8` 3 + `eb774` 12 = 123(`starts.txt`와 같다; 한 줄에 두 block을 적은 곳은 각각 센다). 분류 합계: FLOW_ONLY 67 + 생산 2 + Unknown 54 = 123.

## 구현 범위와 규약

- routing 13 범위(위 표). 짝수 PC 500개 중 block 시작 123, 내부 377. 내부 PC 직접 진입은 `unsupported animation objects n06 PC`다. 범위 이웃과 TRAP·문자열·표 바이트는 기존 실행부 또는 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. `NEG.L`/`SUBQ`/`ADD.W`는 원래 폭의 2의 보수 산술로 계산하고 C++ 부호 있는 overflow에 기대지 않는다. 결과 flag는 같은 block 안의 Bcc만 쓴다(`BGT`는 Z=0이고 N=V, `BLE`는 Z=1이거나 N≠V를 명시 계산).
- **FLOW_ONLY 67개**(C 보존): `b9dd4` `b9df0` `b9df6` `b9e08` `b9e16` `b9e1c` `b9e2e` `b9e3a` `b9e46` `b9e4a` `b9e50` `b9e5c` `b9e62` `b9e70` `b9eb0` `b9f04` `b9f2e` `b9f70` `b9f74` `b9f7a` `b9f92` `ba196` `ba19a` `ba1a0` `ba1b4` `ba1c4` `ba1ca` `ba1e6` `ba1ec` `ba1f0` `ba1f6` `ba212` `ba234` `ba23a` `ba250` `ba258` `ba25c` `ba268` `ba270` `ba27c` `ba282` `ba286` `ba28e` `ba292` `ba296` `ba29c` `ba2a0` `ba2a8` `ba2ac` `ba2b0` `ba2b4` `ba31e` `ba334` `ba384` `ba396` `ba3a8` `d9bd8` `d9bf2` `d9c04` `eb774` `eb77a` `eb786` `eb78a` `eb790` `eb79c` `eb7a0` `eb7a6`.
  - JSR/BRA/JMP/RTS/LEA+BRA/MOVEA+JSR block, `ST.B`(+BRA) block, `BSET` block `ba31e`, 단독 소비자 Bcc 12개.
- **소비자 12개**: `b9e46 BCC b9e50`, `ba1ec BCS ba1f6`, `ba23a BCC ba2b0`, `ba282 BCC ba28e`, `ba29c BCC ba2a8`, `ba334 BCS ba346`, `ba396 BCS ba3a8`, `eb77a BCS eb7b0`, `eb786 BCC eb794`, `eb790 BCS eb7b0`, `eb79c BCC eb7aa`, `eb7a6 BCS eb7b0`. `BCC`는 C Clear면 분기, `BCS`는 C Set이면 분기, Unknown이면 `objects n06 caller requires known carry`.
  - [F] 자연 기록(TB): `b9e46`은 나타나지 않고(`b9e32`→`b9e54` 경로), `ba1ec`→`ba1f6`, `ba23a`→`ba2b0`, `ba334`→`ba346`, `ba396`→`ba3a8`, `eb77a`→`eb7b0`이 나타났다. `ba282` `ba29c` `eb786` `eb790` `eb79c` `eb7a6`은 400 frame 안에 실행되지 않는다(typed fixture).
- **known carry 생산 2개**: `eb7aa`(Set), `eb7b0`(Clear). block 안에서 C를 정하고 `RTS`로 돌려준다.
- 그 밖 54 block(`MOVE`/`MOVEQ`/`MOVEA`+`TST`/`CLR`/`CMP`/`CMPI`/`CMPA`/`SUBQ`/`ADD`/`ANDI`/`NEG` block, `MOVE.L #imm,(A6)` block, bank animation block, `MOVE`+`JSR` block)은 Unknown이다. `491b6` `ba2d6`(`ba2f0`) `e90d8`(`e90e0` `e90e4`) `ba386`(`ba3ae`) `ba310`(`ba384` RTS는 FLOW_ONLY지만 앞 `ba372`가 Unknown)의 반환 C는 [F] 호출 지점 바로 뒤가 모두 C를 읽지 않으므로(위 "참조") Unknown으로 둔다.
- 제어 이동은 모두 정적이다(계산 PC 없음). 경계 callee로 가는 `JSR`은 복귀 LONG을 쌓고 PC를 그 callee로 둔다. 다음 dispatch에서 실행부가 없으므로 stop이면 멈추고 아니면 `unsupported animation machine PC`로 rollback한다. TRAP 3곳으로 가는 fall-through도 같다.
- 스택: `JSR` 복귀 LONG만.
- I/O port 쓰기 없음. bank 변경 없음. work RAM 밖 쓰기, 미해결·홀수 읽기는 기존 checked 오류다.

## 자료

- [F] bank window LONG `2001d0`(bank base `200000`에서 실제 PVC bank 모델로 읽음): `b9e88`(값 → `22(A6)`, 값 + `70`의 LONG → A1), `b9eb4`(값 + `58`).
- [F] fixed ROM / 임의 주소 WORD: `8c(A6)`가 가리키는 WORD(`ba2d6`의 `CMPI.W #80,(A0)`, `ba2e2`의 `ADD.W (A0)+`). 원본이 넣는 값은 `ba30e`(`b9f62`, 곧바로 `0080`) 그리고 N06 밖 `b9f9a` 계열의 `ba2fa` `ba304`(`0000 ffff 0000 0001 0080`, `0000 0001 0000 ffff 0080`)다. C++는 주소를 고정하지 않고 live bus로 읽는다.
- [F] work RAM: BYTE `100012`(`d9bcc`), BYTE `5e30(A5)` + `D0.W`(`e90e4`), WORD `5418(A5)`(`b9e54`).
- [F] node(A6): WORD `1e` `20` `32` `68` `76` `78` `7e` `80` `94` `9c`, LONG `0`(설치) `22` `32`(ANDI.L) `3a` `84` `8c`, BYTE `15`(bit 0) `6b` `7a` `7b` `9f` `a1` `a2` `a4`. 부모 node(`c(A6)`): BYTE `a1`(`b9f80`). `28ae`가 돌려준 자식 node(A0): WORD `76` `78` `94`, BYTE `7a` `7b` `15`(`491b6`).
- [I] `b9dc6` 계열은 부모가 자식 `b9e64`(`ba310`)를 만들고 `ba234` 판정(`eb774`: 두 선수 `49392` 상태 + `49416` 거리 판정으로 보임) 결과 BYTE `a1`/`a2`에 따라 상태를 바꾸는 객체로 보인다. `d9bcc`는 BYTE `100012` = 1일 때 `294` frame 기다린 뒤 자식 `4841a`를 만드는 대기 객체로 보인다. 게임 의미는 미확인이다.

## 의존·경계

- [F] N06 → 기존(모두 routing됨): cleanup `43e34` `2a24`(JMP), fade_card `28ae`(반환 C 소비) `2a00`(JMP), U01 `1aa7e`(반환 C 소비), stage_event_ops `288c`(반환 C 소비), U08 `49290`, interpreter `49f8c` `49fc6`, U05 `c6a96`, U09 `4706c` `47070`, U11 `49370` `497b6`(반환 C 소비), frame_helpers `49392`(반환 C 소비). 내부 호출: `b9dd4 JSR ba310`, `b9dd8 JSR e90d8`, `b9df6`/`b9e1c JSR ba234`, `b9e70 JSR ba386`, `b9f70`/`ba196 JSR ba2d6`, `ba234 JSR eb774`, `ba372`/`ba3a8 JSR 491b6`.
- [F] 실행부 없는 경계: `49416`(`eb78a` `eb7a0`), `497f0`(`ba27c`), TRAP `ba338` `ba364` `ba39a`. 시험은 이 PC의 stop 성립만 확인한다(F4 시험 경계 관례).
- [F] 다른 단위 → N06: U10 `bac72 JSR eb774`(뒤 `bac78 BCC` 소비자; N06 병합 뒤 known C를 받는다), node callback 표 LONG `e8f38`(`b9dc6`) `d9c18`(`d9bcc`).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 123 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 2개, 그 밖 Unknown), 소비자 12개의 Unknown 오류, zero-step, 내부 377 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 경계 callee·TRAP은 stop만. bank LONG·bank 자료는 합성 물리 바이트(ROM 자료 아님), `8c(A6)` 표는 work RAM으로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 소비자 C와 `eb774` 반환 C는 native 분기로 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(진입·설치 callback, `ba2d6` ROM 표, `28ae` 자식 생성과 TRAP 경계).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, complete 기준 +2(seed 40 41) 기대.

## 작업자 검증 기록 (scratch)

- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0(U06 탐침 `eb7b4`→`10fe24` 교체 포함; U06 test 통과). 새 test: `animation machine objects n06: 364 fixtures (23 checked errors, 102 kept C), 123 blocks, 1538 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen_n06.py`): 123 시작 모두 native fixture로 덮임. 소비자 12개 × C Clear/Set 모두 native 분기와 같음. `eb7aa`/`eb7b0` 생산 C는 native SR과 같음(`eb774` 경유 소비자 포함). `ba1a6 BGT`(`0` `1` `2` `7fff` `8000` `8001` `ffff`), `ba346 BLE`(overflow 쌍 `8000`/`7fff` 포함, A0 = A6 별칭), `b9e54 BHI`, `e90d8 BCS`, `d9bea BCS` 경계값이 native와 같음. 경계 stop: `49416` `497f0` TRAP `ba338` `ba364` `ba39a`. rollback 탐침은 `10fe80..10fe88`만.
- [F] 실제 ROM 차분(`realrom/real_n06.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, seed 1·2·3 각 1,500건, `109152`=`cd50`): 불일치 0/0/0, 비교된 사례만으로 123 시작 모두 도달(native가 깨끗이 멈추지 않은 사례 74/75/75건은 제외: 임의 interpreter script `4a000`, `4706c`/`47070` 표 등). native stop에 TRAP `ba338` `ba364` `ba39a`, 경계 `49416` `497f0`(그리고 U11 경계 `4941e`) 포함. 실제 `1aa7e`/`288c`/`28ae`/`49370`/`49392`/`497b6`/`eb774` 뒤 C로 소비자 9곳(`b9e46` `ba1ec` `ba23a` `ba29c` `ba334` `ba396` `eb77a` `eb786` `eb79c`)이 native와 같았다. `2986` caller-X 차이 0건.
- [F] 기준(`5fd7b40` 사본) F2 프레임 패스 차분(base, 142 seed): 일치 pass 12,418·node 96,490, 불일치 0, 자연 완주 113. N06 뒤: 일치 pass 12,658·node 98,492, 불일치 0, 자연 완주 115(+40 41), 회귀 0, 그 밖 변화 0.
- [F] RNG 초기화 400 frame 차분: 기준 일치 pass 38,400·node 278,827, complete 96. N06 뒤 일치 pass 39,200·node 284,189, 불일치 0, `other` 없음, complete 98(+40 41, 잃은 것 0, 다른 seed의 분류·pass 수 변화 0).
- [F] ROM SHA256·mtime 작업 전후 같음.

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] `49416` `497f0`의 반환 C 의미와 동작은 해당 단위 계약에서 정한다.
3. [U] 고아 설치 `b9f96` `b9f9a`(본문 `b9f96..ba196`, `b9f32..b9f62`, 함수 `ba2b6`)와 자식 `4841a`는 N06 밖이다(재범위 결정 3).
4. [U] TRAP 3곳(`fail_mtask` 2, `HIGHT_OVER` 1)의 BIOS 동작은 다루지 않는다(결정 6).

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n06/`(`gen/` typed fixture 생성, `realrom/` 실제 ROM 차분, `fp/` 프레임 패스 차분, `n06blocks.py` block·범위 계산, `n06class.py` carry 분류, `n06dis.py`, `n06route.py` routing 확인, `n06reach.py` 자연 도달·기대 완주, `n06callers.py` 호출자 다음 명령; 저장소 밖).
