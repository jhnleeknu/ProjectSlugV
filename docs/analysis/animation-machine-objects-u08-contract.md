# 객체 callback F4 U08: 공유 객체 core(지형 `447be`·점프 표 `4483a`, 상대 좌표 `43eb8`, C2 `1aa3a`, C3 `49274`/`49290`) 계약 초안 — U08 분할 제안과 첫 부분 U08a

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U08 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`)과 U06 계약(`animation-machine-objects-u06-contract.md`, SHA256 `0a4da066786e1db47158753dbe24ba0449b0af37394cb77c9695c2bbf99f31aa`)을 따른다. 계산 PC 정책은 F1c 계약(`animation-machine-stage-catalog-f1c-contract.md`, SHA256 `f374c80f3528d5200aaa870bd66e8a58d09b400db7a84c8ee3a89fddd474a575`) 4절(F1 결정 3)과 같다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 점프 표 entry)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 4: 지형 `JMP d(PC,D7.W)` 표는 index 상한을 정적으로 확정하고 표 전체를 옮긴다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee는 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01~U06 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U08a에는 없음). `MOVE.x`는 C를 지운다(필요한 소비자가 있을 때만 known 생산으로 둔다). `MOVEM`/`LEA`/`MOVEA`/`JSR`/`JMP`/`BRA`/`RTS`만인 block은 FLOW_ONLY다. checked 오류는 경계에서 낸다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U08의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u08`(HEAD `a4e9253`, U01~U06 WIP 병합, `engine/src/animation_machine.cpp` SHA256 `84568fd8b0b12e256d03d5d809833bc88bf04239c11a3fbe2a7f03280288eb21`)을 참조했다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u08/u08.py`가 원본 opcode에서 독립 계산했고 아래 목록과 같음을 assert했다.

## 요약

- [F] **U08 전체는 표를 옮기면 346 block이다.** 범위 문서의 U08(함수 17개 `18be8` `1aa3a` `43eb8` `447be` `4483a` `4499e` `461ec` `46372` `4683c` `468e0` `49274` `49290` `4bb22` `4bc44` `4be34` `4be82` `4bf16`)은 정적 디코드로 194 block이다(범위 문서와 같음). 범위 문서는 표 `4483a`의 entry 중 자연 관측된 `4499e`(과 그 대상 `449c4`)만 함수로 셌다. 결정 4대로 표 96 entry와 대상 본문을 모두 옮기면 152 block이 더해져 **346**이 된다. 지시 상한(~220)을 넘으므로 아래처럼 나누고 **첫 부분 U08a만 구현**한다(결정 1).
- [F] **U08a = 181 block**: C2 `1aa3a`, C3 `49274`/`49290`, C5 `43eb8`·`18be8`·`447be`, 점프 표 `4483a`(96 entry 전체)와 대상 `449be..44ade`. 코드 5 범위 944바이트, 301명령이다. 미해독·TRAP·묶인 분기는 없다. routing 짝수 PC는 472개, 내부 PC는 291개다.
- [F] **U08b(제안, 미구현) = 165 block**: C6 `461ec` `46372` `4683c` `468e0`, C4 `4bb22` `4bc44` `4be34` `4be82` `4bf16`. 경계 callee 8개(`44ade` `4578a` `45b12` `4662e` `469d8` `492c8` `4b8e8` `4bce0`), SUBX 2개(`4639e` `464b2`), PC 상대 WORD 자료 표 `461ec MOVE.W 461f2(PC,D7.W),D7`. U08a의 `447be`·`4483a`·`18be8`·`1aa3a`·`43e34` 출구를 호출한다.
- [F] U08a 경계 callee는 `47288` 하나다(`447da JSR 47288`). 범위 문서의 "경계 callee 9"는 나머지 8개가 U08b 함수에서만 불리므로 U08b 몫이다. 기존 실행부로 나가는 출구는 `49284 JMP 43e34`(F3a/scene 실행부)와 `49298 JMP 43e04`(cleanup 범위)다.
- [F] **표 index 상한(결정 4).** `4483a JMP 4483e(PC,D7.W)`의 D7 산출자 `447be`는 `D7.W ∈ {4k | 0≤k<60(hex)} ∪ {160}`만 돌려준다(아래 "점프 표"). 표 `4483e..449be`는 정확히 96(=`60`) entry(`BRA.W`, 4바이트)이고 `4483e+160`=`4499e`도 그 안이다. 표 바로 뒤 `449be`(`MOVE.W #160,D7; RTS`)는 대상 공통 실패 경로다.
- [F] U08a 자체로는 새 완주 seed가 없다(범위 문서의 U08 전체와 같음). `447be`·`4483a`의 자연 호출자는 모두 U08b 이후 함수다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **U08 분할(346→181+165).** 권고: U08a(C2·C3·C5와 표 `4483a` 전체)를 먼저, U08b(C4·C6)를 다음 단위로 한다. 경계는 범위 문서의 core 묶음(C2/C3/C5 대 C4/C6)과 같고 둘 다 ≤~220이다. 대안: 표 대상 본문(58 block)을 U20(`44ade`)과 묶어 뒤로 미루기(비권고: 결정 4는 표 전체 이전).
2. **표 `4483a`의 C++ 형태.** 권고: F1 결정 3의 계산 PC 정책을 그대로 쓴다. `4483a`는 PC=`4483e`+sext(`D7.W`)로만 옮긴다(32bit 덧셈, 대상 범위 `3c83e..4c83c`). 표 96 entry의 `BRA.W` 대상은 C++ 상수 배열로 옮겨 적고(코드 바이트를 자료로 읽지 않음), entry PC는 모두 block 시작이다. 상한 안의 index(`0..17c`, 4의 배수)는 모두 구현된 entry이고, `180`은 `449be` block, 그 밖의 값은 routing이 정한다: 표 안 displacement WORD(`4483e+4k+2`)와 대상 본문 내부는 `unsupported animation objects u08 PC`, 홀수는 `unaligned animation machine PC`, 범위 밖은 `unsupported animation machine PC`(또는 다른 실행부)다. 원본은 index 검사가 없으므로 원본 동작과 같은 이동이다. 단 대상이 명령 중간 WORD이면 원본 CPU는 그 WORD부터 디코드해 계속 가지만 C++는 checked 오류로 멈춘다(의도된 차이, 상한 밖 D7에서만 생김).
3. **carry.** 권고: 소비 block 0, known 생산 block 0(아래 근거), FLOW_ONLY 133, Unknown 48.
4. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u08.cpp`의 `animation_objects_u08_block`. 오류는 `unsupported animation objects u08 PC`(내부 PC), `objects u08 caller requires known carry`(U08a에는 소비자가 없어 쓰이지 않지만 U03과 같이 예약).
5. **무효화 탐침 교체.** 아래 "회귀 탐침" 3곳을 미연결 `5f4c0` `5f4c2` `5f4c4`로 바꾼다(어느 `docs/analysis` 문서에도 없음).

## 원본 바이트 근거

[F] 코드 5 범위 합계 944바이트. 범위 순서로 이어 붙인 SHA256 `ff58a59e4786dcc5f20580615363946af284283c3555810f25841b413ff63708`(바이트 전체는 scratch `u08.py`와 ROM에서 재생성).

| CPU 범위 | 내용 |
| --- | --- |
| `18be8..18c06` | 지형 map WORD 읽기 `18be8` |
| `1aa3a..1aa40` | C2 `1aa3a`(WORD `543c(A5)`) |
| `43eb8..43efa` | 두 객체 기준 상대 좌표 `43eb8` |
| `447be..44ade` | 지형 코드 `447be`, 점프 표 `4483a`(entry `4483e..449be`), 대상 `449be..44ade` |
| `49274..4929e` | C3 `49274`(좌표 갱신 후 `43e34`), `49290`(부모 좌표 기준 `43e04`) |

- [F] 범위 밖 이웃: `18c06`(motion_walk 실행부), `1aa40`(다른 함수 `1aa40`), `43ea8..43eb8`(scene_update 실행부), `43efa`(scene 실행부), `447bc`/`447be` 앞(다른 함수), `44ade`(다음 점프 표 함수, U20 범위·U08b 경계), `4929e`(다른 함수), `492c8`(U08b 경계).
- [F] 자료(모두 live bus로 읽는다): 지형 map WORD `(A0,D7.W)`(`18c00`, 호출자 `447be`에서 A0=`109156`/`10b1d6` work RAM), RAM `543c(A5)`, `549c(A5)` `549f(A5)` BYTE, `54aa(A5)` WORD(`ORI.W #200`), 객체 node LONG `14` `18` `1c` `20`(`A0`/`A1`), node LONG `c(A6)` `2e..41(A6)`. 표 entry는 코드이며 자료로 읽지 않는다.
- [F] I/O port 쓰기 없음. 스택 쓰기는 `447ee MOVE.W D7,-(A7)`(WORD, 곧바로 `MOVE.B (A7)+,D6`로 상위 BYTE를 읽고 A7은 +2 복원)과 JSR 복귀 LONG뿐이다.

## 점프 표 `4483a`와 index 상한(결정 4)

- [F] `447be`의 D7 산출:
  - A0=0이면 `4482e`: `ORI.W #200,54aa(A5)`; `D7.W`=`160`; RTS.
  - A0=`109156`/`10b1d6`이면 `18be8`(WORD map 값, 아래)에 `ADDI.B #58,D7`. 그 밖이면 `47288`(U08a 경계)의 D7.
  - `447ee`: D6=(D7.W 상위 BYTE) AND `1f`. D6=1이고 BYTE `549f(A5)`≠0이면 `D7.B`=`58`.
  - `4480c`: `SWAP D6; MOVE.B D7,D6; ROL.W #2,D7; ANDI.W #3,D7; EXG D6,D7`로 D6.W=D7.W 상위 2bit, D7=((상위 BYTE AND `1f`)<<16)|D7.B.
  - `CMP.B 549c(A5),D6; BHI 4482e`(무부호 D6.B>BYTE이면 `160`), `CMPI.B #60,D7; BCC 4482e`(D7.B≥`60`이면 `160`).
  - `44828`: `ADD.W D7,D7` 두 번 → `D7.W`=4×D7.B(<`180`). 상위 WORD=상위 BYTE AND `1f`.
  - 따라서 `447be` 반환 `D7.W`는 `4k`(k<`60`) 또는 `160`이다. `JMP d(PC,D7.W)`는 `D7.W`만 쓴다.
- [F] 표 `4483e..449be`: 96개 `BRA.W`(opcode `6000`)이고 바로 뒤 `449be`는 `MOVE.W #160,D7`(`3e3c 0160`)이다. index→대상(16진 k):
  - `00..1f`: k AND 3 = 0/1/2/3 → `44aae` `44aba` `44ac6` `44ad2`.
  - `20..23`: `449d2` `449d8` `449d2` `449d8`.
  - `24..33`: k AND 3 → `449de` `449e8` `449f2` `449fc`.
  - `34..3b`: k AND 3 → `44a06` `44a10` `44a1a` `44a24`.
  - `3c..3f`: `44a2e` `44a34` `44a3c` `44a46`.
  - `40..47`: k AND 3 → `44a4e` `44a5a` `44a66` `44a72`.
  - `48..57`: k AND 3 → `44a7e` `44a8a` `44a96` `44aa2`.
  - `58..5f`: `449c4` `449c6` `449cc` `449c6` `449c6` `449c4` `449c4` `449c4`(`58`=D7 `160`).
- [F] 대상은 D2(x)·D3(y) LONG 기울기 판정 leaf다. 조건이 참이면 `449be`(D7=`160`)로, 아니면 RTS(D7 그대로)다. D4는 scratch로 남는다.
- [F] `4483a`의 호출 site 8개(`463a8` `464ba` `46664` `4673c` `46abe` `46b28` `46e04` `46e66`, 모두 BSR.W)는 U08a 밖이다. `464ba` `46b28` `46e04` `46e66`의 D7은 같은 함수 안 `447be` 결과(또는 `160`) 또는 그것을 쓴 `54b0(A5)`이다. `463a8` `46664` `4673c` `46abe`의 D7은 함수 진입 D7 또는 `54b0(A5)`이다. [I] `54b0(A5)` 쓰기(`MOVE.W D7,54b0(A5)`)는 모두 `447be` 결과 처리 뒤라 같은 상한 안이다. [U] 진입 D7 경로의 전 호출 closure는 확인하지 않았다. 결정 2의 계산 PC 정책이 그 밖의 값도 원본과 같이 옮기므로 실행 의미는 상한 확정에 의존하지 않는다.

## block 목록과 실행 의미

[F] 181 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)·`(An,Dn.W)`는 부호확장한다. `.B`·`.W` 연산은 나머지 bit를 보존한다. `xxxx(A5)`는 `A5`(자연 `108000`) 기준이다.

**지형 map `18be8` 1**
- `18be8`: `MOVE.W D0,D6; MOVE.W D1,D7; NOT.W D7; ANDI.W #1f8,D6; ANDI.W #1f8,D7; LSR.W #2,D7; LSL.W #4,D6; OR.W D6,D7; ADDI.W #80,D7; MOVE.W (A0,D7.W),D7; RTS` (index는 짝수, `80..207e`)

**C2 `1aa3a` 1**
- `1aa3a`: `MOVE.W 543c(A5),D0; RTS`

**상대 좌표 `43eb8` 7**
- `43eb8`: `CMPA.L A1,A0; BNE 43ec0`
- `43ebe`: `RTS`
- `43ec0`: `ADD.L D0,D2; ADD.L D1,D3; CMPA.W #0,A0; BEQ 43edc`
- `43ecc`: `ADD.L 1c(A0),D0; ADD.L 20(A0),D1; ADD.L 14(A0),D2; ADD.L 18(A0),D3` (→`43edc`)
- `43edc`: `CMPA.W #0,A1; BEQ 43ef4`
- `43ee4`: `SUB.L 1c(A1),D0; SUB.L 20(A1),D1; SUB.L 14(A1),D2; SUB.L 18(A1),D3` (→`43ef4`)
- `43ef4`: `SUB.L D0,D2; SUB.L D1,D3; RTS`

**지형 코드 `447be` 14**
- `447be`: `CMPA.W #0,A0; BEQ 4482e`
- `447c6`: `CMPA.L #109156,A0; BEQ 447e4`
- `447d0`: `CMPA.L #10b1d6,A0; BEQ 447e4`
- `447da`: `JSR 47288.L` (경계 callee)
- `447e0`: `BRA 447ee`
- `447e4`: `JSR 18be8.L`
- `447ea`: `ADDI.B #58,D7` (→`447ee`)
- `447ee`: `MOVEQ #0,D6; MOVE.W D7,-(A7); MOVE.B (A7)+,D6; ANDI.W #1f,D6; CMPI.W #1,D6; BNE 4480c`
- `44800`: `TST.B 549f(A5); BEQ 4480c`
- `44808`: `MOVE.B #58,D7` (→`4480c`)
- `4480c`: `SWAP D6; MOVE.B D7,D6; ROL.W #2,D7; ANDI.W #3,D7; EXG D6,D7; CMP.B 549c(A5),D6; BHI 4482e`
- `44820`: `CMPI.B #60,D7; BCC 4482e`
- `44828`: `ADD.W D7,D7; ADD.W D7,D7; RTS`
- `4482e`: `ORI.W #200,54aa(A5); MOVE.W #160,D7; RTS`

**점프 표 `4483a` 97**
- `4483a`: `JMP 4483e(PC,D7.W)` (계산 PC, 결정 2)
- `4483e+4k`(k=`0..5f`, 96 block): `BRA.W` 위 index 표의 대상

**표 대상 58**
- `449be`: `MOVE.W #160,D7; RTS`
- `449c4`: `RTS`
- `449c6`: `TST.L D3; BGT 449be` / `449ca`: `RTS`
- `449cc`: `TST.L D3; BLT 449be` / `449d0`: `RTS`
- `449d2`: `TST.L D2; BLT 449be` / `449d6`: `RTS`
- `449d8`: `TST.L D2; BGT 449be` / `449dc`: `RTS`
- `449de`: `MOVE.L D2,D4; LSL.L #2,D4; CMP.L D4,D3; BGT 449be` / `449e6`: `RTS`
- `449e8`: `MOVE.L D2,D4; LSL.L #2,D4; ADD.L D3,D4; BGT 449be` / `449f0`: `RTS`
- `449f2`: `MOVE.L D2,D4; LSL.L #2,D4; ADD.L D3,D4; BLT 449be` / `449fa`: `RTS`
- `449fc`: `MOVE.L D2,D4; LSL.L #2,D4; CMP.L D4,D3; BLT 449be` / `44a04`: `RTS`
- `44a06` `44a10` `44a1a` `44a24`: 위 넷과 같고 `LSL.L #1` / 각 `RTS` `44a0e` `44a18` `44a22` `44a2c`
- `44a2e`: `CMP.L D2,D3; BGT 449be` / `44a32`: `RTS`
- `44a34`: `MOVE.L D2,D4; ADD.L D3,D4; BGT 449be` / `44a3a`: `RTS`
- `44a3c`: `MOVE.L D2,D4; ADD.L D3,D4; BLT 449be` / `44a44`: `RTS`
- `44a46`: `CMP.L D2,D3; BLT 449be` / `44a4c`: `RTS`
- `44a4e`: `MOVE.L D3,D4; LSL.L #1,D4; CMP.L D2,D4; BGT 449be` / `44a58`: `RTS`
- `44a5a`: `MOVE.L D3,D4; LSL.L #1,D4; ADD.L D2,D4; BGT 449be` / `44a64`: `RTS`
- `44a66`: `MOVE.L D3,D4; LSL.L #1,D4; ADD.L D2,D4; BLT 449be` / `44a70`: `RTS`
- `44a72`: `MOVE.L D3,D4; LSL.L #1,D4; CMP.L D2,D4; BLT 449be` / `44a7c`: `RTS`
- `44a7e` `44a8a` `44a96` `44aa2`: 위 넷과 같고 `LSL.L #2` / 각 `RTS` `44a88` `44a94` `44aa0` `44aac`
- `44aae` `44aba` `44ac6` `44ad2`: 위 넷과 같고 `LSL.L #3` / 각 `RTS` `44ab8` `44ac4` `44ad0` `44adc`

**C3 `49274`/`49290` 3**
- `49274`: `MOVEM.L 2e(A6),D0-D3/A0; LEA 538e(A5),A1; JSR 43eb8.L`
- `49284`: `MOVEM.L D0-D3/A1,2e(A6); JMP 43e34.L`
- `49290`: `MOVEA.L c(A6),A1; LEA 2e(A1),A1; JMP 43e04.L`

## 구현 범위와 규약

- routing 5 범위: `18be8..18c06`, `1aa3a..1aa40`, `43eb8..43efa`, `447be..44ade`, `49274..4929e`. 짝수 PC 472개 중 block 시작 181, 내부 291. 내부 PC 직접 진입은 `unsupported animation objects u08 PC`다. 경계 `47288`, 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 조건 판정은 원본 flag 그대로 계산한다(32bit 명시, 미정의 동작 없음): `BGT`=¬Z∧(N=V), `BLT`=N≠V, `BHI`=¬C∧¬Z, `BCC`=¬C. `ADD.L`의 V=((¬(s⊕d))∧(d⊕r))의 bit31, `CMP.L`의 V=((s⊕d)∧(d⊕r))의 bit31(r=d−s). `CMPA.W #0,An`은 An=0 판정, `CMPA.L`은 32bit 같음 판정이다.
- **carry.** [F] U08a 안에 C 소비 block은 없다. [F] ROM의 호출 뒤 첫 명령은 C를 소비하지 않는다: `JSR 18be8` 1곳→`ADDI.B`; `JSR 1aa3a` 37곳→`MOVE`/`LEA`/`BTST`/`ANDI`/`JSR`/`RTS`(2곳, 호출자의 반환으로 이어짐); `JSR 43eb8` 11곳→`ADD`/`MOVEA`/`MOVEM`/`SWAP`/`SUB`; `BSR 447be` 14곳→`MOVE.W`/`SWAP`; `BSR 4483a` 8곳→`CMPI.W` 5, `BSR` 3; `JSR 49274` 52곳·`JSR 49290` 214곳→`JSR`/`MOVE`/`LEA`/`CLR`/`BSET`/`BCLR`/`TST`/`BRA`/`JMP`/`RTS`. [I] `RTS`로 이어지는 site의 바깥 소비는 그 호출자 단위가 정한다(관례대로 Unknown). 따라서 known 생산 block을 두지 않는다.
- **FLOW_ONLY 133개**(C 보존): `4483a`(JMP), 표 entry 96개(`BRA.W`), `447da` `447e4`(JSR), `447e0`(BRA), `43ebe` `449c4` 와 표 대상 fall-through `RTS` 28개(`449ca` `449d0` `449d6` `449dc` `449e6` `449f0` `449fa` `44a04` `44a0e` `44a18` `44a22` `44a2c` `44a32` `44a3a` `44a44` `44a4c` `44a58` `44a64` `44a70` `44a7c` `44a88` `44a94` `44aa0` `44aac` `44ab8` `44ac4` `44ad0` `44adc`), `49274`(MOVEM+LEA+JSR), `49284`(MOVEM+JMP), `49290`(MOVEA+LEA+JMP). 나머지 48개(MOVE/MOVEQ/NOT/ANDI/LSR/LSL/OR/ADDI/ADD/SUB/CMPA/CMP/CMPI/TST/SWAP/ROL/EXG/ORI block, `449be`)는 Unknown이다.
- 스택: `447ee`는 `D7.W`를 A7−2에 쓰고(`am_push` WORD) 그 주소의 BYTE를 읽은 뒤 A7을 2 올린다(68000 A7 BYTE 증가 규칙). 남은 RAM WORD는 원본처럼 그대로 둔다. 홀수 A7·work RAM 밖 쓰기는 기존 checked 오류다.
- `ORI.W #200,54aa(A5)`는 WORD 읽기-OR-쓰기다. `MOVEM.L` 읽기는 D0,D1,D2,D3,A0 순서(`2e` `32` `36` `3a` `3e`), 쓰기는 D0,D1,D2,D3,A1 순서다.
- 회귀 탐침: [F] 다음 outside 탐침이 U08a 범위가 된다. 아무 분석 문서에도 없는 미연결 PC로 바꾼다.
  - `engine/tests/animation_machine_motion_walk_test.cpp`의 `0x18c04`(`18be8` 내부 PC) → `0x5f4c0`.
  - `engine/tests/animation_machine_objects_u04_test.cpp`의 `0x43eb8`(U08a block 시작) → `0x5f4c2`.
  - `engine/tests/animation_machine_scene_update_test.cpp`의 `0x43eb8` → `0x5f4c4`.
  - `scene_update_test`의 범위 표 `{0x43ea8,0x43eb8}`(끝 미포함)와 `tools/inventory_scene_coordinates.py`의 범위는 바꾸지 않는다.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, 기본 120 frame)에서 U08a block에 TB로 닿는 seed는 71개(0 1 6~9 12~23 28~37 40~43 46 47 56 57 62 63 68~71 76 77 80~85 88 89 96~99 102~105 116 117 127~135)다. TB 시작 기준 181 block 중 37개가 자연 도달한다: `18be8` `1aa3a`, `43eb8` 계열 7, `447be` 계열 11(`44800` `44808` `4482e` 미도달), `4483a`, 표 entry `448ca`(k=`23`) `4499e`(`58`) `449a2`(`59`) `449a6`(`5a`) `449ae`(`5c`), 대상 `449be` `449c4` `449c6` `449ca` `449cc` `449d0` `449d8` `449dc`, `49274` `49284` `49290`. 미도달 144개(나머지 표 entry 91, 대상 50, `44800` `44808` `4482e`, TB 경계 때문에 fall-through 일부는 실제로 실행돼도 미도달로 셈)는 typed fixture와 실제 ROM 차분으로 덮는다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 181 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), zero-step, 내부 291 PC 정확한 오류, 홀수 PC, 경계·이웃 오류, 표 96 index 전체와 상한 밖 계산 PC(`180`, displacement WORD, 음수, 홀수). 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn)로 비교한다.
- 실제 ROM 차분: `447be`(세 A0 경로, map WORD 전 범위), `4483a`의 96 index 전체×(D2,D3) 부호·크기 조합, `43eb8`, `18be8`, `1aa3a`, `49274`, `49290`을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed): `a4e9253` 기준 일치 pass·완주 seed가 모두 그대로이고(회귀 0), 첫 미연결 callback 분포 변화를 보고한다.

## 미확인·범위 밖

1. [I] `447be`는 지형 map 칸(`109156`/`10b1d6`의 64×64 WORD 격자, `18be8`) 또는 `47288`의 값에서 지형 종류(D7 index)와 높이(D6)를 얻는 함수, `4483a` 표는 지형 종류별 기울기 판정(D2·D3 이동 성분)으로 보인다. 게임 의미는 미확인이다.
2. [U] `447be` 진입 경로 밖(U08b 이후 함수의 진입 D7)에서 `4483a`에 상한 밖 D7이 오는지. 계산 PC 정책으로 실행 의미는 정해진다.
3. [U] `47288`(경계)의 D7 산출 범위. `447be`가 `447ee`에서 다시 마스크하므로 `4483a` 상한에는 영향이 없다.
4. 범위 밖: U08b 9 함수(위 제안), 경계 `47288`, `44ade`·`45176`·`45798`·`45b28` 표(U20·U11·U15).

작업자 scratch: 세션 scratchpad `f4u08/`(`u08.py` block·범위·SHA 계산, `trav.py` `u08a.py` `u08b.py` 분할 계산, `refs.py` `nextins.py` 호출 site, `reach.py`; 저장소 밖).
