# 객체 callback F4 U07: `e585c`/`e5878`/`e59f6` 객체 계열·조회 helper `4e186` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U07 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`)과 U04·U05 계약을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee는 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U07에는 없음). `MOVE.x`/`MOVEQ`/`TST`/`CMP`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). checked 오류는 경계에서 낸다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U07의 코드는 `<100000`에 있으므로 CPU 주소와 file offset이 같다. U07은 ROM 자료를 읽지 않는다(아래 "자료"). 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u07`(HEAD `4729f37`, U01~U05 WIP, `engine/src/animation_machine.cpp` SHA256 `26797448f954f8e0cf32f3a0725bb99b52e80789d8afcf4634022e66ec02da97`)을 참조했다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u07/u07.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] U07은 함수 3개(`4e186`, `e585c`, `e5878`(+설치 callback `e59f6`))의 **block 시작 85개**다. 코드 2 범위, 922바이트, 196명령이며 미해독·TRAP·PC 상대 점프 표·묶음 Bcc는 없다. routing 짝수 PC는 461개, 내부 PC는 376개다.
- [F] **범위 문서 84와의 차이(+1)**: `e59d2`의 `MOVE.L #e59f6,(A6)`가 설치하는 callback 진입 `e59f6`이다. 같은 주소가 fall-through 대상이기도 하다. 범위 스크립트 본문 집합(`f4scope/groups.py`의 `body`)은 `4e186` 9, `e585c` 2, `e5878` 73이고 `e59f6`이 빠져 있다(TB 기준 집합이었음). 수용 관례("MOVE-installed callback entries are starts")에 따라 85로 센다.
- [F] 경계(실행부 없음): callee `48256`(`e5ba6 JSR`; 범위 문서 "경계 callee 1").
- [F] 기존 실행부로 나가는 출구: readiness `289e`(C 반환), buffer_cue `2986`(자식 객체 생성), fade_card `28ae`(객체 생성)·`2a00`(JMP, 자기 삭제), U01 `48296`, sound `3af8`, stage_area `49a58`(RNG), U04 `43ea4`(→scene update `43ea8`→cleanup `43e38`).
- [F] 자연 seed(F2 프레임 패스 기본 120 frame): 92·93이 frame 0에 `e585c`(node `100f5c`)와 `e5878`(node `101020`)을 실행한다. `e5878`은 `4e186` 두 번 뒤 `8e`·`90`=`ffff`로 `e598a`→`e599a`→`e59a0`의 `JSR 49a58`에 닿고, seed RAM의 RNG 포인터 LONG `10d722`=0 때문에 native는 `49a80 SUB.W D0,(A3)`(A3=`30`) ROM 쓰기로 frame 0에 끝난다. C++는 같은 frame에서 기존 stage_area checked 오류 `stage area RNG pointer outside work RAM`으로 끝나야 한다(RNG guard 완주). U07 뒤 완주 seed는 54→56(새 92 93)이 되어야 한다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 정정(84→85).** `e59f6`(MOVE.L 설치 callback 진입, fall-through와 같은 주소)를 시작으로 센다(권고, 관례와 같음). 범위 문서는 고치지 않는다.
2. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u07.cpp`의 `animation_objects_u07_block`. 오류는 `unsupported animation objects u07 PC`, `objects u07 caller requires known carry`(메인 지시와 같음).
3. **`4e186`의 반환 C는 Unknown으로 둔다.** [F] ROM의 `JSR 4e186` 12곳(`dbe34` `dbe42` `de914` `dea80` `dec96` `decb6` `df070` `df090` `df168` `df196` `e58c6` `e58da`) 바로 뒤 명령은 모두 flag를 새로 정하는 `TST.W D1`/`CMPI.W #ffff,D1`/`CMPI.W #1,D1`/`CMP.W 7a(A6),D2`다. 그래서 `4e1be`·`4e1c4`(`MOVEQ`/`MOVE.B` 뒤 RTS)를 known Clear 생산으로 두지 않는다.
4. **`CLR.B 63(A6)`의 68000 읽기 주기.** [F] 68000 `CLR`은 쓰기 전에 같은 주소를 읽는다. 대상이 work RAM d16(A6)뿐이므로 상태 차이는 없다. 기존 단위(U04 `CLR.W`)처럼 쓰기만 모델한다(권고).

5. **`e585c`→`2986` 실패 경로(기존 buffer_cue 제약).** [F] `2986`의 `298e..299a`는 `MOVE SR,-(A7)`로 SR WORD를 스택 아래 RAM에 남긴다. `28ae` 실패(D0.W ≥ WORD `104ca0` 또는 빈 목록)이면 그 WORD의 X는 호출자 X다. 기존 buffer_cue 실행부는 X를 `e8a48` 호출자(복귀 LONG `e8a8a`)에 대해서만 계산하고, 그 밖 호출자는 checked 오류 `cue wrapper failure requires known caller X`로 rollback한다. [F] `e585c` block은 X를 바꾸지 않으므로 X는 scheduler `2ab8`을 지나 이전 callback에서 이어진 값이며 U07 안에서 정할 수 없다. 권고: 기존 실행부를 바꾸지 않고 이 경우를 의도된 차이(checked 오류)로 둔다. 성공 경로(X=`28e6 ADDQ.W` 결과)는 그대로 실행된다. 자연 seed 92·93의 `e585c`는 성공 경로다.

## 원본 바이트 근거

[F] 코드 2 범위 합계 922바이트. 이어 붙인 SHA256 `885135d1984c8834a1e89a1906293be839e51beefea16098e5bfa3f5db072625`.

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `4e186..4e1cc` | `4a406600000c41f9001009a86000000841f900100a6c4eb90000289e6400001a1e28009c72010c0700026700001272000c07000167000008740072ff4e757400142800984e75` |
| `e585c..e5bb0` | `207c000e5878303c0014227c00100bf44eb9000029864ef900002a004eb900048296303c07384eb900003af8207c000e5ea0303c000a4eb9000028ae207c000e5bb0303c000a4eb9000028ae207c000e5c74303c000a4eb9000028ae3d7cffff008e3d7cffff009070004eb90004e1860c410001660000063d42008e70014eb90004e1860c410001660000063d4200904a6e008e6b0000984a6e00906b00007641f90010de1443f90010de1c2010b0916d000032207c000e5d86303c000a4eb9000028ae316e008e008c207c000e5d72303c000a4eb9000028ae316e0090008c6000002e207c000e5d72303c000a4eb9000028ae316e008e008c207c000e5d86303c000a4eb9000028ae316e0090008c60000018207c000e5d72303c000a4eb9000028ae316e008e008c60000018207c000e5d72303c000a4eb9000028ae316e0090008c43f90010b1d6237cfffa00000008237c00000000000c43f90010d256237cfffe80000008237c00000000000c4eb900049a580240007f3d4000783d7cffe0002e3d7c01400032422e00633d7c0168007c2cbc000e59f61d7c000000624eb900043ea44a2e006367000016303c07384eb900003af83d7c0002007a422e0063302e007a660000580cae0002000000366c00000a06ae0000800000360c6e00a0002e6d00003870004eb900049a5806800001000044802d40003670004eb900049a580480000080002d40003a3d7c0001007a303c19e04eb900003af84e750c400001660000780c6e013000326e00001470004eb900049a580680000040002d40003a0c6e016000326d00001670004eb900049a5806800000400044802d40003a0c6e0030002e6e00001470004eb900049a580680000100002d4000360c6e0110002e6d00001670004eb900049a5806800001000044802d4000364e750c4000026600004a202e003ae48091ae003a202e00366a00001e0c80fffe00006f000010e480d1ae003604ae000010000036600000083d7c0003007a0c6e0030002e6e00000a2d7c0000000000364e750c4000036600005e202e003ae48091ae003a0c6e013000326e00000a2d7c00000000003a0c6e016000326d00000a2d7c00000000003a202e00360c80000400006c000010e680d1ae003606ae0000400000360c6e0140002e6d0000084eb9000482564e754e75` |

- [F] 범위 밖 이웃: `4e166..4e186`은 기존 readiness 범위(`4e184 RTS`)다. `4e1cc`(`CLR.B 5d1e(A5)`로 시작하는 다른 함수), `e583c..e585c`(자료로 보이는 바이트, 미연결), `e5bb0`(`e5898`이 만드는 자식 객체의 callback)은 routing 밖이다. `e5724..e583c`는 U02 범위다.
- [F] 자료: U07은 ROM·bank window 자료를 읽지 않는다. 읽고 쓰는 곳은 모두 work RAM이다.
  - `4e186`: A0=`1009a8`(D0.W=0) 또는 `100a6c`(D0.W≠0). `289e`가 LONG `(A0)`, `4e1a6`이 BYTE `9c(A0)`, `4e1c4`가 BYTE `98(A0)`를 읽는다.
  - `e58fc`: LONG `10de14`와 `10de1c`(부호 비교).
  - `e59a0`: LONG 쓰기 `10b1de`=`fffa0000`, `10b1e2`=0, `10d25e`=`fffe8000`, `10d262`=0.
  - node d16(A6): WORD `2e` `32` `78` `7a` `7c` `8e` `90`, LONG `36` `3a`, BYTE `62` `63`, LONG `(A6)`(callback 설치 `e59f6`). 새 객체 WORD `8c(A0)`(A0=`28ae`가 돌려준 node, 실패 시 `28ae`의 `A5-7168`).
- [F] 자식 객체 callback(코드 상수, U07이 실행하지 않음): `e5878`(`e585c`→`2986`, U07 시작), `e5ea0` `e5bb0` `e5c74`(`e5888` `e5898` `e58a8`), `e5d86`·`e5d72`(`e5910` `e5926` `e5940` `e5956` `e5970` `e598a`). U07 밖이며 그 node가 다음 frame에 실행되면 미연결 callback이 된다.

## block 목록과 실행 의미

[F] 85 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `MOVE.B`/`MOVE.W` Dn과 `ANDI.W`는 나머지 bit를 보존하고 `MOVEQ`는 LONG 전체를 쓴다. `ASR.L`은 산술(부호 유지) 이동이다. 부호 비교 `BGE`/`BLT`/`BGT`/`BLE`는 CMP 피연산자 크기의 2의 보수 비교, `BMI`/`BPL`은 결과 최상위 bit다.

**조회 helper `4e186`(D0.W 0/≠0 → A0 node 선택, D1/D2 반환) 9**
- `4e186`: `TST.W D0; BNE 4e196`
- `4e18c`: `LEA 1009a8.L,A0; BRA 4e19c`
- `4e196`: `LEA 100a6c.L,A0` (→`4e19c`)
- `4e19c`: `JSR 289e` (readiness. `CMPI.L #270e,(A0)`: 같으면 C=Clear, 아니면 `ORI #1,CCR` Set)
- `4e1a2`: `BCC 4e1be` (carry 소비; `289e` 반환 C)
- `4e1a6`: `MOVE.B 9c(A0),D7; MOVEQ #1,D1; CMPI.B #2,D7; BEQ 4e1c4`
- `4e1b4`: `MOVEQ #0,D1; CMPI.B #1,D7; BEQ 4e1c4`
- `4e1be`: `MOVEQ #0,D2; MOVEQ #-1,D1; RTS`
- `4e1c4`: `MOVEQ #0,D2; MOVE.B 98(A0),D2; RTS`

**생성 callback `e585c` 2**
- `e585c`: `MOVEA.L #e5878,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986` (자식 객체 `e5878`을 node `100bf4` 아래에 만든다)
- `e5872`: `JMP 2a00` (fade_card 자기 삭제)

**객체 callback `e5878`(+설치 callback `e59f6`) 74**
- `e5878`: `JSR 48296` (callback 진입, U01)
- `e587e`: `MOVE.W #738,D0; JSR 3af8`
- `e5888`: `MOVEA.L #e5ea0,A0; MOVE.W #a,D0; JSR 28ae`
- `e5898`: `MOVEA.L #e5bb0,A0; MOVE.W #a,D0; JSR 28ae`
- `e58a8`: `MOVEA.L #e5c74,A0; MOVE.W #a,D0; JSR 28ae`
- `e58b8`: `MOVE.W #ffff,8e(A6); MOVE.W #ffff,90(A6); MOVEQ #0,D0; JSR 4e186`
- `e58cc`: `CMPI.W #1,D1; BNE e58d8`
- `e58d4`: `MOVE.W D2,8e(A6)` (→`e58d8`)
- `e58d8`: `MOVEQ #1,D0; JSR 4e186`
- `e58e0`: `CMPI.W #1,D1; BNE e58ec`
- `e58e8`: `MOVE.W D2,90(A6)` (→`e58ec`)
- `e58ec`: `TST.W 8e(A6); BMI e598a`
- `e58f4`: `TST.W 90(A6); BMI e5970`
- `e58fc`: `LEA 10de14.L,A0; LEA 10de1c.L,A1; MOVE.L (A0),D0; CMP.L (A1),D0; BLT e5940` (부호 LONG `D0 < (A1)`)
- `e5910`: `MOVEA.L #e5d86,A0; MOVE.W #a,D0; JSR 28ae`
- `e5920`: `MOVE.W 8e(A6),8c(A0); MOVEA.L #e5d72,A0; MOVE.W #a,D0; JSR 28ae`
- `e5936`: `MOVE.W 90(A6),8c(A0); BRA e596c`
- `e5940`: `MOVEA.L #e5d72,A0; MOVE.W #a,D0; JSR 28ae`
- `e5950`: `MOVE.W 8e(A6),8c(A0); MOVEA.L #e5d86,A0; MOVE.W #a,D0; JSR 28ae`
- `e5966`: `MOVE.W 90(A6),8c(A0)` (→`e596c`)
- `e596c`: `BRA e5986`
- `e5970`: `MOVEA.L #e5d72,A0; MOVE.W #a,D0; JSR 28ae`
- `e5980`: `MOVE.W 8e(A6),8c(A0)` (→`e5986`)
- `e5986`: `BRA e59a0`
- `e598a`: `MOVEA.L #e5d72,A0; MOVE.W #a,D0; JSR 28ae`
- `e599a`: `MOVE.W 90(A6),8c(A0)` (→`e59a0`)
- `e59a0`: `LEA 10b1d6.L,A1; MOVE.L #fffa0000,8(A1); MOVE.L #0,c(A1); LEA 10d256.L,A1; MOVE.L #fffe8000,8(A1); MOVE.L #0,c(A1); JSR 49a58` (RNG)
- `e59d2`: `ANDI.W #7f,D0; MOVE.W D0,78(A6); MOVE.W #ffe0,2e(A6); MOVE.W #140,32(A6); CLR.B 63(A6); MOVE.W #168,7c(A6); MOVE.L #e59f6,(A6)` (→`e59f6`)
- `e59f6`: `MOVE.B #0,62(A6); JSR 43ea4` (callback 진입, U04)
- `e5a02`: `TST.B 63(A6); BEQ e5a1e`
- `e5a0a`: `MOVE.W #738,D0; JSR 3af8`
- `e5a14`: `MOVE.W #2,7a(A6); CLR.B 63(A6)` (→`e5a1e`)
- `e5a1e`: `MOVE.W 7a(A6),D0; BNE e5a7c` (상태 0)
- `e5a26`: `CMPI.L #20000,36(A6); BGE e5a3a`
- `e5a32`: `ADDI.L #8000,36(A6)` (→`e5a3a`)
- `e5a3a`: `CMPI.W #a0,2e(A6); BLT e5a7a`
- `e5a44`: `MOVEQ #0,D0; JSR 49a58`
- `e5a4c`: `ADDI.L #10000,D0; NEG.L D0; MOVE.L D0,36(A6); MOVEQ #0,D0; JSR 49a58`
- `e5a60`: `SUBI.L #8000,D0; MOVE.L D0,3a(A6); MOVE.W #1,7a(A6); MOVE.W #19e0,D0; JSR 3af8`
- `e5a7a`: `RTS`
- `e5a7c`: `CMPI.W #1,D0; BNE e5afa` (상태 1)
- `e5a84`: `CMPI.W #130,32(A6); BGT e5aa0`
- `e5a8e`: `MOVEQ #0,D0; JSR 49a58`
- `e5a96`: `ADDI.L #4000,D0; MOVE.L D0,3a(A6)` (→`e5aa0`)
- `e5aa0`: `CMPI.W #160,32(A6); BLT e5abe`
- `e5aaa`: `MOVEQ #0,D0; JSR 49a58`
- `e5ab2`: `ADDI.L #4000,D0; NEG.L D0; MOVE.L D0,3a(A6)` (→`e5abe`)
- `e5abe`: `CMPI.W #30,2e(A6); BGT e5ada`
- `e5ac8`: `MOVEQ #0,D0; JSR 49a58`
- `e5ad0`: `ADDI.L #10000,D0; MOVE.L D0,36(A6)` (→`e5ada`)
- `e5ada`: `CMPI.W #110,2e(A6); BLT e5af8`
- `e5ae4`: `MOVEQ #0,D0; JSR 49a58`
- `e5aec`: `ADDI.L #10000,D0; NEG.L D0; MOVE.L D0,36(A6)` (→`e5af8`)
- `e5af8`: `RTS`
- `e5afa`: `CMPI.W #2,D0; BNE e5b4a` (상태 2)
- `e5b02`: `MOVE.L 3a(A6),D0; ASR.L #2,D0; SUB.L D0,3a(A6); MOVE.L 36(A6),D0; BPL e5b30` (N=LONG bit31)
- `e5b14`: `CMPI.L #fffe0000,D0; BLE e5b2c` (부호 LONG `D0 ≤ -20000`)
- `e5b1e`: `ASR.L #2,D0; ADD.L D0,36(A6); SUBI.L #1000,36(A6)` (→`e5b2c`)
- `e5b2c`: `BRA e5b36`
- `e5b30`: `MOVE.W #3,7a(A6)` (→`e5b36`)
- `e5b36`: `CMPI.W #30,2e(A6); BGT e5b48`
- `e5b40`: `MOVE.L #0,36(A6)` (→`e5b48`)
- `e5b48`: `RTS`
- `e5b4a`: `CMPI.W #3,D0; BNE e5bae` (상태 3)
- `e5b52`: `MOVE.L 3a(A6),D0; ASR.L #2,D0; SUB.L D0,3a(A6); CMPI.W #130,32(A6); BGT e5b6e`
- `e5b66`: `MOVE.L #0,3a(A6)` (→`e5b6e`)
- `e5b6e`: `CMPI.W #160,32(A6); BLT e5b80`
- `e5b78`: `MOVE.L #0,3a(A6)` (→`e5b80`)
- `e5b80`: `MOVE.L 36(A6),D0; CMPI.L #40000,D0; BGE e5b9c`
- `e5b8e`: `ASR.L #3,D0; ADD.L D0,36(A6); ADDI.L #4000,36(A6)` (→`e5b9c`)
- `e5b9c`: `CMPI.W #140,2e(A6); BLT e5bac`
- `e5ba6`: `JSR 48256` (경계 callee)
- `e5bac`: `RTS`
- `e5bae`: `RTS` (상태 0~3 밖)

## 구현 범위와 규약

- routing 2 범위: `4e186..4e1cc`, `e585c..e5bb0`. 짝수 PC 461개 중 block 시작 85, 내부 376. 내부 PC 직접 진입은 `unsupported animation objects u07 PC`다. 경계 `48256`과 범위 이웃(`4e1cc` `e583c..e585a` `e5bb0` 이후)은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **carry 소비 block 1개**: `4e1a2`(`289e` 반환 C; 기존 readiness 실행부가 Clear/Set을 known으로 둔다). Unknown이면 `objects u07 caller requires known carry`.
- **known carry 생산 block 0개**(결정 3).
- **FLOW_ONLY 15개**(C 보존): `4e18c`(LEA+BRA), `4e196`(LEA), `4e19c` `e5878` `e5ba6`(JSR), `4e1a2`(BCC), `e5872`(JMP), `e596c` `e5986` `e5b2c`(BRA), `e5a7a` `e5af8` `e5b48` `e5bac` `e5bae`(RTS). 그 밖(MOVE/MOVEA+MOVE 혼합/MOVEQ/TST/CMP/CMPI/ADDI/SUBI/SUB/ADD/NEG/ASR/ANDI/CLR가 있는 block)은 Unknown이다.
- 스택: U07 자체는 JSR 복귀 LONG만 쌓는다(MOVEM 없음). 홀수 A7·work RAM 밖 쓰기는 기존 checked 오류다.
- 반환 Z·N: U07 안 소비는 모두 같은 block의 TST/CMP/CMPI/MOVE 뒤다. RTS를 넘는 flag 소비는 `4e1a2`(C)뿐이다.
- I/O: port 쓰기는 U07 자체에 없다(callee 몫). bank 변경 없음.
- 회귀 탐침: [F] `engine/tests`·`tools`·`docs/analysis`에서 U07 두 범위 안 PC를 outside 탐침으로 쓰는 곳은 없다(`0x4e186`은 readiness routing의 배타 상한 `<0x4e186`과 native observer 범위 상한으로만 나온다). 바꿀 탐침은 없다.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed)에서 U07 block에 닿는 callback은 `e585c` 2와 `e5878` 2(seed 92·93, frame 0)뿐이다. TB 포함 기준으로 85 block 중 20개가 자연 도달한다(`e599a`의 TB는 `e59a0` 본문까지 포함). 미도달 65개(fixture 필요): `4e1a6` `4e1b4` `4e1c4` `e58d4` `e58e8` `e58f4` `e58fc` `e5910` `e5920` `e5936` `e5940` `e5950` `e5966` `e596c` `e5970` `e5980` `e5986` `e59a0`(별도 TB로는 미기록) `e59d2` `e59f6`과 `e5a02..e5bae` 전체.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 85 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), 소비 block의 Unknown 오류, zero-step, 내부 376 PC 정확한 오류, 홀수 PC, 경계 `48256`·이웃 오류. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력만)로 비교한다.
- 실제 ROM 차분: `4e186`(실제 `289e`), `e5878`(실제 `48296` `3af8` `28ae` `49a58` `43ea4` 경로), `e59f6`(상태 0~3과 그 밖), `e585c`(실제 `2986`, stop `2a00`)를 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`): U01~U05 기준(작업 트리 `4729f37`) 일치 pass 9,536개·node 70,904개가 모두 그대로 일치하고, 완주 seed가 54→56(새 92 93, RNG guard 완주)이어야 한다.

## 미확인·범위 밖

1. [I] `4e186`은 node `1009a8`/`100a6c`(D0.W로 선택; [I] 두 player 칸)의 callback LONG이 `270e`(scheduler 빈 callback)가 아닐 때 BYTE `9c`가 2(D1=1)·1(D1=0)이면 BYTE `98`을 D2로 돌려주는 조회다. `270e`이거나 `9c`가 다른 값이면 D1=-1, D2=0이다. `e5878`은 두 결과로 자식 객체 `e5d86`/`e5d72`를 만들고 RNG로 초기 속도를 정한 뒤 `e59f6`에서 `7a` 상태(0~3)에 따라 움직이다 화면 밖(`2e`≥`140`)에서 `48256`을 부르는 연출 객체로 보인다. 게임 의미는 미확인이다.
2. [U] `48256`(`MOVE.B -7453(A5),D0; ADDQ.B #1,D0; MOVE.B D0,5681(A5); RTS`)과 자식 callback `e5ea0` `e5bb0` `e5c74` `e5d72` `e5d86`은 U07 밖이다.
3. [U] seed 92·93은 RNG 포인터 0 때문에 frame 0 `49a58`에서 끝나므로 `e59f6` 이후 상태 기계는 자연 기록이 없다(fixture·실제 ROM 차분만). RNG 초기화 변형(범위 문서 결정 1)에서의 진행은 관측하지 않았다.

작업자 scratch: 세션 scratchpad `f4u07/`(`u07.py` block·범위·SHA 계산, `dis_u07.py`, `reach.py`, `callers.py`; 저장소 밖).
