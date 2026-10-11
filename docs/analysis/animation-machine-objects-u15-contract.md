# 객체 callback F4 U15: U15 분할 제안과 첫 부분 U15a(`af078` 계열 callback, C6 지형 구동 `4662e`, C3 `4950e`, C4 `4c1de`/`4c29a`) 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U15 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`, `4b54e` 반환 C), U08 계약(SHA256 `fd484c1cc1bcd87a87f69892451a1cfd36528db5797cca7298514c8c1f703d8d`, 표 분할 선례와 `447be` D7 상한), U11 계약(SHA256 `ab51cd6d422c9a97fc9a705b4d11254716b69bebd4610a93c0cd58c656940d7d`, 표 `45176` 전체 이식), U12 계약(SHA256 `61bd4657f2dab1b48ebd337e1a2000054911f233a458f3bb0f321e7846eac32d`), U13 계약(SHA256 `20af72d0d12a571f1d36590bc9e36348b596de54d948320364c7721f71e2c53e`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 설치 callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 4: 지형 점프 표는 index 상한을 정적으로 확정하고 표 전체를 옮긴다. 결정 5: 단위는 함수 본문 전체, 실행되지 않는 callee와 범위 밖 설치 callback은 실행부 없는 경계다.
- U01~U13 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다. `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`/`SWAP`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`Scc`, Z만 바꾸는 `BTST`/`BSET`/`BCLR`)만인 block과 callee C를 소비하는 단독 Bcc는 FLOW_ONLY다. `ADDQ`/`SUBQ`/`ADDA` An block은 Unknown이다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U15의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u15`(HEAD `7b2f3e5` = U01~U13 WIP, `engine/src/animation_machine.cpp` SHA256 `6b550a48d8a2441853165f1524f0c06bc2659dd50d6be8bbc9c9d6134ec7675a`, routing 규칙 48개)을 참조했다. U14(작업 트리 `metalslug-u14`)는 이 작업 트리에 없다. U15a는 U14 PC를 부르지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u15/u15.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **U15 전체는 표를 옮기면 514 block이다.** 범위 문서 U15 행의 함수 17개(`449a6` `452e2` `4578a` `45904` `45afe` `45b1a` `45c94` `4662e` `4950e` `4c1de` `4c29a` `af078` `af146` `af1e4` `af3de` `b0062` `b00da`)를 정적 디코드했다.
  - `449a6`(U08a 표 entry)와 `452e2`(U11 표 entry)는 이미 routing돼 있어 다시 넣지 않는다.
  - 범위 문서는 표 `45798`·`45b28`에서 자연 관측 entry(`45904` `45c94`)와 그 대상만 셌다(195). 결정 4대로 두 표의 96 entry 전체와 대상 본문을 옮기면 **514**가 된다(묶인 Bcc 제외, `af3f8` 포함).
  - 지시 상한(~220)을 넘으므로 아래처럼 셋으로 나누고 **첫 부분 U15a만 구현**한다(결정 1).
- [F] **U15a = 175 block**: callback `af078` `af146` 계열(설치 callback `af1e4`, 자식 callback `af3de` `af3f8` `af3fe`), `b0062`/`b00da`, 공유 꼬리 `b05be`, C6 지형 구동 `4662e`, C3 `4950e`, C4 `4c1de`/`4c29a`.
  - 코드 9 범위, 1,710바이트, 442명령이다. 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP은 없다.
  - SUBX 2개(`4665a` `46734`, 같은 block 안의 `ADDI.L` X를 씀)가 있다. DIVx/MULx는 없다.
  - 묶인 Bcc 2개(`af210 BPL`은 `af204`에, `4c236 BMI`는 `4c230`에 묶음).
  - routing 짝수 PC는 855개, 내부 PC는 680개다.
- [F] **U15b(제안, 미구현) = 144 block**: `4578a`(`JMP 4579c(PC,D7.W)`, 96 `BRA.W` entry `4579c..4591c`), 표 대상 본문 `4591c..45afe`, `45afe`(`CMPI.W #174,D7; BNE 4578a`). 범위 `4578a..45b12` 1 범위. 묶인 Bcc 2개(`4592c` `45b0c`). 호출 없음.
- [F] **U15c(제안, 미구현) = 195 block**: `45b1a`(`CMPI.W #174,D7; BNE 45b28`; `TST.L D3; BGT 46198`), `45b28 JMP 45b2c(PC,D7.W)`(96 `BRA.W` entry `45b2c..45cac`, 대상 96개가 모두 다름), 대상 본문 `45cac..461ec`. 범위 `45b1a..461ec` 1 범위. 호출 없음.
  - [F] 두 표의 index 상한: 호출 site(`46670` `46748` → `45b1a`, `46674` `4674c` → `45afe`, U08b `463b8` `464ca` → `4578a`)의 `D7.W`는 `447be`/`4483a` 결과 또는 `54b0(A5)`이다. U08 계약에 따라 `4k`(k<`60`) 또는 `160`이고, `46668`/`46740`이 `160`을 건너뛴다. 표는 둘 다 정확히 96 entry이고, 바로 뒤 `4591c`(`RTS`)·`45cac`(첫 대상)가 시작한다. U11 표 `45176`과 같은 계산 PC 정책을 쓴다.
- [F] **U15a 경계 callee(실행부 없음) 9개**:
  - U16 소유 3개: `b0106`(`af14c` `af426`, C 반환), `b0206`(`af44e` `af4c0`, C 반환), `b02c8`(`af442` `af4b4`).
  - 범위 문서 U15 행의 나머지 경계 4개: `491fe`(`af2d6`), `49214`(`af25a`), `4b702`(`af3ea` `af3f8`), `d3c2a`(`af402`).
  - U15b/U15c 2개: `45afe`(`46674` `4674c`), `45b1a`(`46670` `46748`).
- [F] **범위 밖 설치 callback(쓰기만 함)**: `af302`(`af2f8`), `af4ee`(`af416`), `af6ec`(`af480`), `af6de`(`af4e6`). 범위 밖 이웃 `af096`(다른 callback 진입)도 넣지 않는다.
- [F] 기존 실행부로 나가는 호출:
  - U08a: `447be`, `4483a`, `49274`. U11: `45176`, `49370`. U12: `490ba`, `4c0ac`. U08b: `4bc44`. U09: `469d8`(JSR, `4c29e`의 JMP).
  - U01 `4b54e`(C 반환), U05 `1ab02`(C 반환)·`c6a96`, U02 `8ebe`, cleanup `287e`(C 반환)·`43e34`, fade_card `28ae`·`2986`·`2a00`.
  - 영역 RNG `49a58`, interpreter `49f8c`·`49fc6`.
  - U15a 안 호출: `JSR b0062(PC)` 3곳(`af3fe` `af422` `af488`; 범위 밖 `af0b2` `af118`도 부른다), `BSR b00da`(`b0062`), `JSR 4c1de`(`af4ac`).
- [F] **flag**:
  - known carry 생산 block 4개: `49542`(`ANDI.B #fe,CCR` Clear), `49548`(`ORI.B #1,CCR` Set), `4c25a`(Set), `4c260`(Clear). [F] 각각 ROM 호출자가 소비한다(`4950e` 6곳, `4c1de` 5곳의 `BCC`/`BCS`).
  - 블록 경계를 건너는 C 소비 block 7개: `af150`·`af42a`(←`b0106` 경계), `af452`·`af4c4`(←`b0206` 경계), `af27a`(←`287e`), `af2e6`(←`4b54e`), `b05ca`(←`1ab02`).
  - block 안에서 만들고 쓰는 flag: `BVC`(`4664e` `46728`, V), `SUBQ.W`+`BCS`(borrow), `SUBQ.W`+`BPL`/`SMI`(N), 부호 있는 `BGE`/`BLE`/`BGT`(N⊕V), `ADDI.L`+`SUBX`(X).
- [F] 자연 도달(F4 범위 scratch 재생, TB 기준): base(`f4scope/dyn`) 104 block, RNG 초기화+응답 `80` 변형(`dyn_rng1_resp80_f400`) 124 block. 범위 안 TB 시작은 모두 정적 시작이거나 묶인 Bcc다(`af210` 1개, TB 인공 진입).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **U15 분할(514 block → U15a 175 / U15b 144 / U15c 195).**
   - 권고: U15a(표가 없는 callback·구동 부분)를 먼저 구현한다. U15b(표 `45798`)와 U15c(표 `45b28`)는 각각 표 하나와 대상 본문이다. U11 `45176`처럼 독립 단위로 옮긴다.
   - 이유: (1) 두 표 단위는 호출이 없는 자기 완결 본문이다. U15a 쪽 경계(`45afe` `45b1a`)만 연결하면 된다. (2) `4662e`는 26 seed(base)·53 seed(RNG+`80`)에서 자연 도달한다. 지금 `4688a BSR 4662e`에서 멈추는 pass는 U15a 뒤 `D3`=0, `D7`=`160`, 위로 이동 길까지 실행된다.
   - 대안: 범위 문서 순서대로 표 `45798`+`4578a`+`45afe`+`4662e`(202)를 먼저 묶는다. 이 경우 `46670 BSR 45b1a`가 항상 앞에 있어 U15c 전에는 표 경로가 실행되지 않는다.
   - 범위 문서는 고치지 않는다.
2. **`af3f8` 포함.** [F] `af3f8`(`JSR 4b702.L`)은 `af214`가 `MOVEA.L #af3f8,A0; ... JSR 2986`으로 설치하는 자식 callback 진입이다. `af3de..af4ee` 범위 안이고 1 block이다(복귀점 `af3fe`는 이미 시작). 범위를 하나로 잇기 위해 넣는다. 권고: 넣는다(U13 `b813c` `b816e`처럼 범위 안 진입).
3. **경계 9개.** U16 `b0106` `b0206` `b02c8`, `491fe` `49214` `4b702` `d3c2a`, U15b/U15c `45afe` `45b1a`. F4 test 경계 관례에 따라 test는 이 PC의 stop만 확인하고 rollback은 `5f6xx..5ffxx`로만 확인한다.
   - 자연 seed 18 19 96 97 102 103(`af078`/`af146`)은 `b0106`/`b02c8`(U16)에서 멈춘다. `4662e`를 쓰는 seed는 `45b1a`(U15c)에서 멈춘다. 그래서 U15a만으로는 새 완주 seed를 기대하지 않는다(범위 문서도 U15 "새 자연 seed -").
4. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u15.cpp`의 `animation_objects_u15_block`. 오류는 `unsupported animation objects u15 PC`(내부 PC), `objects u15 caller requires known carry`(소비 7 block). 메인 지시와 같다.
5. **C 소비 7 block과 known 생산 4 block.**
   - `af150 BCS af162`, `af42a BCS af43c`: U16 `b0106` 반환 C. `af452 BCC af470`, `af4c4 BCC af4d4`: U16 `b0206` 반환 C. [F] `b0206`은 `JSR 4950e; BCS b021c; MOVE.L A0,76(A6); ORI.B #1,CCR ...`로 C를 정한다(U16 본문). 이 작업 트리에서는 경계이므로 선언 C로만 진입한다.
   - `af27a BCS af2dc`: cleanup `287e`(`CMP.W 10(A0),D0`의 C, 기존 실행부가 known으로 둔다).
   - `af2e6 BCC af2ee`: U01 `4b54e` 반환 C(U01 결정 2).
   - `b05ca BCC b05dc`: U05 `1ab02` 반환 C.
   - Unknown이면 `objects u15 caller requires known carry`(state 보존).
   - 생산: `49542`/`49548`(`4950e` 반환), `4c25a`/`4c260`(`4c1de` 반환). U11 `49386`/`4938c`와 같은 유형이다.
6. **V·N⊕V 분기.** `4664e ADD.L D3,D6; BVC`, `46728 CMP.L D5,D6; BVC`, `46694 CMP.L; BLE`, `466a2 ADD.L; BGE`, `4c1e4`/`4c23a CMP.W; BGE`, `4c1f2`/`4c248 CMP.W; BLE`, `af078 CMPI.W #200; BGE`, `af456`/`af4d8 CMP.W; BLE`, `af470 CMPI.W #a0; BGT`. C++는 부호 있는 정수 변환 없이 비트 연산으로 N·V를 계산한다(부호 있는 overflow UB 없음).
7. **무효화 탐침.** [F] `probes.py` 결과: U08b test(`engine/tests/animation_machine_objects_u08b_test.cpp`)가 `4662e`를 (a) `BOUNDARIES`(그 PC에서 멈춘 fixture를 STOP으로 다시 실행해 rollback 확인)와 (b) `outside[]` rollback 탐침으로 쓰고, (c) `4683a`(U08b 범위 바로 앞, 이제 U15a 내부 PC)도 `outside[]` rollback 탐침으로 쓴다. U15a가 routing하면 셋 다 깨진다. 교체는 `5fe00` 이후의 미사용 PC 3개다(BOUNDARIES 자리는 U09 `469d8` 때와 같은 "멈추지 않는 자리", 나머지 둘은 outside rollback 탐침). 정확한 값은 test 주석에만 두고, 이 계약을 포함한 `docs/analysis` 어디에도 적지 않는다(F4 단위 범위 밖). U12 test의 `4c1de` `4c29a`는 stop 확인뿐이라 유지된다. `tools`·`engine/src`의 언급은 탐침이 아니다(U08b·U12 경계 주석, caller inventory 나열).

8. **`2986` 실패 경로(기존 buffer_cue 제약).** [F] `af214`/`af22e`는 `JSR 2986`(buffer_cue)로 자식(`af3f8`/`af3fe`)을 만든다. `28ae`가 실패하면(D0.W ≥ WORD `104ca0` 또는 빈 목록) `298e`의 SR WORD에 호출자 X가 남는데, 기존 실행부는 X를 `e8a48` 호출자에 대해서만 계산하고 그 밖 호출자는 `cue wrapper failure requires known caller X`로 rollback한다(U07 계약 결정 5와 같은 제약). [F] U15a block은 X를 정하지 않는다(`af204` 앞 X는 이전 callback에서 이어진 값). 권고: 기존 실행부를 바꾸지 않고 의도된 차이(checked 오류)로 둔다. 성공 경로는 그대로 실행된다. 실제 ROM 차분에서 이 경우를 따로 센다.

## 원본 바이트 근거

[F] U15a 코드 9 범위 합계 1,710바이트. 범위 순서로 이어 붙인 SHA256 `d16a75a3b23395d86d19af5fd8c52af480892ace058476ed3c607d734ac55f0d`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `4662e..4683c` | 526 | `7d133a2c8a8bf4593cfc0678cf12f004a792149f70eb748005ebf8b9a0feeae2` | C6 지형 구동 `4662e` |
| `4950e..4954e` | 64 | `7125a405408247434ce929fda08ffce27d1d6e3f1d7c17c1b1bc703f81372e6b` | C3 `4950e`(player 선택, C 반환) |
| `4c1de..4c266` | 136 | `2161f05563a5b8c836bf98e6665f5fcdfac7b644e5fdc381efd0317fce10dd10` | C4 `4c1de`(8 단위 분할 이동, C 반환) |
| `4c29a..4c2c4` | 42 | `28deb35e8d75257992203644cb806456d5f8acb5a1130236ca9973d7ef30c48c` | C4 `4c29a` |
| `af078..af096` | 30 | `8cdc3ae4addc8194f22a51726de28683b96e2f260403979bafe3eb0eb016f3bb` | callback `af078` |
| `af146..af302` | 444 | `f206dd4532edd9bdace2516abca1f2e539c0243e0197dc6565b1c9496d0be27d` | callback `af146`, 설치 callback `af1e4` |
| `af3de..af4ee` | 272 | `a699b14d65891341b80df65e69eb3ffb0ae048401810da265297619a12a67be1` | 자식 callback `af3de` `af3f8` `af3fe`, `af41e`/`af422`/`af488` 경로 |
| `b0062..b0106` | 164 | `ae96d7a8af71a51ce800a717e8184527bbfb416b4f90957b91ffd59aec95f5a4` | `b0062`, `b00da` |
| `b05be..b05de` | 32 | `0231d9db59eca4aa7d008e4f8b5b866b6aac1ab48896d2bd50689af417c02da9` | 공유 꼬리 `b05be` |

- [F] 범위 밖 이웃(routing 밖): `4662c`(U08b 앞 함수 끝), `4683c`(U08b), `4950c` `4954e`(다른 함수), `4c1dc` `4c266`(U10 경계 `4c266`), `4c298` `4c2c4`(다른 함수; U12 경계 `4c2cc`), `af076`(U33 범위 `aee30..af06a` 뒤), `af096`(다른 callback 진입), `af144`, `af302`(설치 callback), `af3dc`, `af4ee`(설치 callback), `b0060`, `b0106`(U16), `b05bc`, `b05de`(자료 `b05e6` 앞), 경계 callee 9개.
- [F] 자료(모두 live bus):
  - work RAM `A5`=`108000` 기준: WORD `54aa`(`ORI.W #40`/`#400`, 읽기·쓰기), WORD `54ac`, `54ae`(읽기·쓰기), `54b0` `54b2`(쓰기), BYTE `54b4`(TST/쓰기/CLR), BYTE `549d`(쓰기 `ff`).
  - 노드 d16(A6): BYTE `15`(BSET bit 3/0, BTST bit 7), WORD `46` `7c` `76` `78` `7a` `90` `96` `42`, BYTE `9a` `9e` `a3` `6a` `61` `5e`, LONG `2e` `32` `3e`(`MOVEM.L 2e(A6),D0-D1`, `ADD.L`), LONG `c`(부모, `SUBQ.B #1,62(A0)`), LONG `76`(`af456`/`af4c8`의 A0, `b0206`이 넣는 포인터), 쓰기 WORD `68` `1e` `54` `20` `82` `84` `86` `88` `8a` `92` `94` `96` `90`, BYTE `a0` `a1` `9a`, LONG `56`(`b060c`/`b05ee`), `(A6)`(callback 설치).
  - 자식 node d16(A0, `28ae`/`2986` 반환): BYTE `6a` `a3`, WORD `76` `78` `7a`.
  - 스택: JSR/BSR 복귀 LONG, `466aa MOVE.L D5,-(A7)`/`4670a MOVE.L (A7)+,D5`, `4c1fc`/`4c252`의 WORD push 2개와 `4c216 MOVE.W (A7),D2`·`4c224`의 WORD pop 2개.
  - 주소만 넘기는 fixed ROM: `cac22` `cac3c` `caadc` `cabba` `cabd4` `cabee` `cac08`(→`490ba` A0), `b0c4a`(→`49f8c` A1), `b05e6`(→`1ab02` A0), `100bf4`(→`2986` A1, work RAM 부모), 자식 callback 상수 `af3de` `af3f8` `af3fe`, 쓰기 상수 `b060c` `b05ee`, 고정 주소 `100cb8` `100da8`(`4950e` A0).
  - I/O port 쓰기와 bank 변경은 U15a 자체에 없다.

## block 목록과 실행 의미

[F] 175 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `.B`·`.W` 연산은 나머지 bit를 보존하고 `MOVEQ`는 LONG 전체를 쓴다. `CMP`/`TST` 뒤 `BNE`/`BEQ`는 Z, `BMI`/`BPL`은 N, `BGE`/`BLE`/`BGT`는 부호 있는 비교(N⊕V), `BVC`는 V, `SUBQ` 뒤 `BCS`와 `CMPI` 뒤 `BCS`는 borrow다.

**C6 지형 구동 `4662e` 58**
- `4662e`: `TST.L D3; BNE.W 46638` (함수 진입; U08b `4688a BSR`)
- `46634`: `MOVEQ #0,D6; RTS`
- `46638`: `CMPI.W #160,D7; BEQ.W 46694`
- `46640`: `BSR.W 45176` (U11)
- `46644`: `SUBI.L #80000000,D6; BEQ.W 46694`
- `4664e`: `ADD.L D3,D6; BVC.W 46694` (V: LONG 덧셈 overflow)
- `46654`: `ADDI.L #80000000,D6; SUBX.L D4,D4; SUB.L D4,D6; SUB.L D6,D3; EXG.L D3,D6; ADD.L D6,D1; BSR.W 4483a` (X=`ADDI` carry; U08a)
- `46668`: `CMPI.W #160,D7; BEQ.W 4667c`
- `46670`: `BSR.W 45b1a` (경계 U15c)
- `46674`: `BSR.W 45afe` (경계 U15b)
- `46678`: `MOVEQ #ff,D6; RTS`
- `4667c`: `TST.B 54b4(A5); BNE.W 46694`
- `46684`: `ORI.W #40,54aa(A5); MOVE.B #ff,54b4(A5); MOVEQ #ff,D6; RTS`
- `46694`: `MOVEQ #8,D4; SWAP D4; MOVE.L D3,D5; CMP.L D4,D5; BLE.W 466a2`
- `466a0`: `MOVE.L D4,D5` (→`466a2`)
- `466a2`: `ADD.L D5,D4; BGE.W 466aa`
- `466a8`: `SUB.L D4,D5` (→`466aa`)
- `466aa`: `MOVE.L D5,-(A7); MOVE.L D1,D4; ANDI.L #7ffff,D4; ADD.L D5,D1; ADD.L D5,D4; SWAP D4; SUBQ.W #8,D4; BCS.W 4670a`
- `466c0` / `46764` / `467ce`: `SWAP D0; SWAP D1; BSR.W 447be` (U08a)
- `466c8` / `4676c` / `467d6`: `MOVE.W D6,54b2(A5); MOVE.W 54ae(A5),D4; MOVE.W D7,54ae(A5); CMPI.W #174,D4; BNE.W n1` (n1 = `466e8` / `4678c` / `467f6`)
- `466dc` / `46780` / `467ea`: `CMPI.W #174,D7; BNE.W n1`
- `466e4` / `46788` / `467f2`: `MOVE.W #160,D7` (→n1)
- `466e8` / `4678c` / `467f6`: `CMPI.W #178,D7; BEQ.B n2` (n2 = `466f6` / `4679a` / `46804`)
- `466ee` / `46792` / `467fc`: `CMPI.W #17c,D7; BNE.W n3` (n3 = `46700` / `467a4` / `4680e`)
- `466f6` / `4679a` / `46804`: `MOVE.W #160,D7; ORI.W #400,54aa(A5)` (→n3)
- `46700` / `467a4` / `4680e`: `MOVE.W D7,54b0(A5); SWAP D0; SWAP D1; MOVEQ #0,D4` (→`4670a` / `467ae` / `46818`)
- `4670a`: `MOVE.L (A7)+,D5; TST.W D4; BNE.W 46832`
- `46712`: `CMPI.W #160,D7; BEQ.W 46832`
- `4671a`: `BSR.W 45176` (U11)
- `4671e`: `SUBI.L #80000000,D6; BEQ.W 46832`
- `46728`: `CMP.L D5,D6; BVC.W 46832` (V: `D6-D5` overflow)
- `4672e`: `ADDI.L #80000000,D6; SUBX.L D4,D4; SUB.L D4,D6; SUB.L D5,D3; ADD.L D6,D3; BSR.W 4483a`
- `46740`: `CMPI.W #160,D7; BEQ.W 467b2`
- `46748`: `BSR.W 45b1a` (경계 U15c)
- `4674c`: `BSR.W 45afe` (경계 U15b)
- `46750` / `467ba`: `MOVE.L D1,D4; ANDI.L #7ffff,D4; SUB.L D6,D1; SUB.L D6,D4; SWAP D4; SUBQ.W #8,D4; BCS.W t` (t = `467ae` / `46818`)
- `467ae`: `MOVEQ #ff,D6; RTS`
- `467b2`: `TST.B 54b4(A5); BNE.W 46822`
- `46818`: `MOVE.B #ff,54b4(A5); MOVEQ #ff,D6; RTS`
- `46822`: `SUB.L D6,D3; ORI.W #40,54aa(A5); CLR.B 54b4(A5); MOVEQ #0,D6; RTS`
- `46832`: `SUB.L D5,D3; CLR.B 54b4(A5); MOVEQ #0,D6; RTS`

**C3 `4950e` 9**
- `4950e`: `JSR 49370(PC)` (U11)
- `49512`: `CMPI.W #3,D0; BCS.W 49526`
- `4951a`: `JSR 49a58.L` (영역 RNG)
- `49520`: `ANDI.W #1,D0; ADDQ.W #1,D0` (→`49526`)
- `49526`: `LEA 100cb8.L,A0; CMPI.W #2,D0; BNE.W 4953a`
- `49534`: `LEA 100da8.L,A0` (→`4953a`)
- `4953a`: `CMPI.W #0,D0; BEQ.W 49548`
- `49542`: `ANDI.B #fe,CCR; RTS` (known Clear)
- `49548`: `ORI.B #1,CCR; RTS` (known Set)

**C4 `4c1de` 19 + `4c29a` 2**
- `4c1de`: `TST.W D0; BMI.W 4c1f2`
- `4c1e4`: `MOVEQ #8,D1; CMP.W D1,D0; BGE.W 4c1ee`
- `4c1ec`: `MOVE.W D0,D1` (→`4c1ee`)
- `4c1ee`: `BRA.W 4c1fc`
- `4c1f2`: `MOVEQ #f8,D1; CMP.W D1,D0; BLE.W 4c1fc`
- `4c1fa`: `MOVE.W D0,D1` (→`4c1fc`)
- `4c1fc`: `SUB.W D1,D0; MOVE.W D0,-(A7); MOVE.W D1,-(A7); JSR 4bc44(PC)` (U08b)
- `4c206`: `MOVE.B #ff,549d(A5); MOVEM.L 2e(A6),D0-D1; MOVEA.L 3e(A6),A0` (→`4c216`)
- `4c216`: `MOVEQ #0,D2; MOVEQ #0,D3; MOVE.W (A7),D2; SWAP D2; JSR 469d8.L` (U09; 반복 진입점)
- `4c224`: `MOVE.W (A7)+,D4; MOVE.W (A7)+,D5; BTST.B #0,D6; BEQ.W 4c260`
- `4c230`: `TST.W D5; BEQ.W 4c25a; BMI.W 4c248` (묶음)
- `4c23a`: `MOVEQ #8,D4; CMP.W D4,D5; BGE.W 4c244`
- `4c242`: `MOVE.W D5,D4` (→`4c244`)
- `4c244`: `BRA.W 4c252`
- `4c248`: `MOVEQ #f8,D4; CMP.W D4,D5; BLE.W 4c252`
- `4c250`: `MOVE.W D5,D4` (→`4c252`)
- `4c252`: `SUB.W D4,D5; MOVE.W D5,-(A7); MOVE.W D4,-(A7); BRA.B 4c216`
- `4c25a`: `ORI.B #1,CCR; RTS` (known Set)
- `4c260`: `ANDI.B #fe,CCR; RTS` (known Clear)
- `4c29a`: `JSR 4bc44(PC)` (U08b)
- `4c29e`: `SUB.W D0,D2; SUB.W D1,D3; SWAP D2; SWAP D3; CLR.W D2; CLR.W D3; SWAP D0; SWAP D1; CLR.W D0; CLR.W D1; ADD.L 2e(A6),D0; ADD.L 32(A6),D1; MOVEA.L 3e(A6),A0; JMP 469d8.L` (U09)

**callback `af078` 3**
- `af078`: `BSET.B #3,15(A6); MOVE.W 46(A6),D0; CMPI.W #200,D0; BGE.W af3fe`
- `af08a`: `TST.W 7c(A6); BNE.W af41e`
- `af092`: `BRA.W af488`

**callback `af146` 36(설치 callback `af1e4` 포함)**
- `af146`: `BSET.B #3,15(A6); JSR b0106(PC)` (경계 U16, C 반환)
- `af150`: `BCS.W af162` (carry 소비)
- `af154`: `MOVEA.L c(A6),A0; SUBQ.B #1,62(A0); JMP 2a00.L`
- `af162`: `MOVE.W #5f,D0; MOVE.W #1,D1; MOVE.B #0,D2; JSR c6a96.L` (U05)
- `af174`: `MOVE.W #8899,68(A6); MOVE.W #8899,1e(A6); MOVE.L #b060c,56(A6); MOVE.W 76(A6),D0; MOVE.W 78(A6),D1; MOVE.W D0,90(A6); MOVE.B D1,9a(A6); MOVEQ #0,D0; MOVE.W D0,76(A6); MOVE.W D0,78(A6); LEA cac22.L,A0; JSR 490ba.L` (U12)
- `af1ae`: `MOVE.W D0,54(A6); MOVE.W #163,20(A6); MOVEA.L #b0c4a,A1; MOVE.W #100,D0; JSR 49f8c.L`
- `af1c8`: `LEA cac3c.L,A0; JSR 490ba.L`
- `af1d4`: `MOVE.W D0,96(A6); JSR 49274.L` (U08a)
- `af1de`: `MOVE.L #af1e4,(A6)` (→`af1e4`)
- `af1e4`: `JSR 43e34.L` (설치 callback 진입; cleanup)
- `af1ea`: `JSR 49fc6.L`
- `af1f0`: `SUBQ.W #1,96(A6); BPL.W af26c`
- `af1f8`: `LEA cac3c.L,A0; JSR 490ba.L`
- `af204`: `MOVE.W D0,96(A6); TST.W 90(A6); BEQ.W af26c; BPL.W af22e` (묶음)
- `af214`: `MOVEA.L #af3f8,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.L`
- `af22a`: `BRA.W af244`
- `af22e`: `MOVEA.L #af3fe,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.L`
- `af244`: `MOVE.B 6a(A6),6a(A0); MOVEQ #0,D0; MOVE.W D0,76(A0); MOVE.W D0,78(A0); MOVE.W D0,7a(A0); MOVEQ #fc,D1; JSR 49214.L` (경계)
- `af260`: `SUBQ.W #1,90(A6); SMI.B D0; EXT.W D0; SUB.W D0,90(A6)` (→`af26c`)
- `af26c`: `TST.B 9a(A6); BEQ.W af2dc`
- `af274`: `JSR 287e.L` (cleanup, C 반환)
- `af27a`: `BCS.W af2dc` (carry 소비)
- `af27e`: `MOVEA.L #af3de,A0; MOVE.W #14,D0; JSR 28ae.L`
- `af28e`: `MOVE.B 6a(A6),6a(A0); MOVE.B a3(A6),a3(A0); MOVE.W #ffff,76(A0); MOVE.W #0,78(A0); MOVE.W #0,7a(A0); MOVE.B 9a(A6),D0; CMPI.B #3,D0; BNE.W af2be`
- `af2b8`: `JSR 49a58.L`
- `af2be`: `BTST.B #0,D0; BEQ.W af2ce`
- `af2c6`: `MOVE.W #158,D0; BRA.W af2d2`
- `af2ce`: `MOVE.W #ffe8,D0` (→`af2d2`)
- `af2d2`: `MOVE.W #1a0,D1; JSR 491fe.L` (경계)
- `af2dc`: `BRA.W af2e0`
- `af2e0`: `JSR 4b54e.L` (U01, C 반환)
- `af2e6`: `BCC.W af2ee` (carry 소비)
- `af2ea`: `CLR.B 5e(A6)` (→`af2ee`)
- `af2ee`: `BTST.B #7,61(A6); BEQ.W af2fe`
- `af2f8`: `MOVE.L #af302,(A6)` (→`af2fe`)
- `af2fe`: `BRA.W b05be`

**자식 callback `af3de`/`af3f8`/`af3fe`와 `af41e`/`af488` 경로 35(`b05ce` 제외)**
- `af3de`: `BSET.B #3,15(A6); JSR 49274.L` (자식 callback 진입)
- `af3ea`: `JSR 4b702.L` (경계)
- `af3f0`: `ST.B 9a(A6); BRA.W af422`
- `af3f8`: `JSR 4b702.L` (자식 callback 진입; 경계)
- `af3fe`: `JSR b0062(PC)` (자식 callback 진입, `af078` BGE 대상)
- `af402`: `JSR d3c2a.L` (경계)
- `af408`: `JSR 49a58.L`
- `af40e`: `ANDI.B #7,D0; MOVE.B D0,a1(A6); MOVE.L #af4ee,(A6); RTS`
- `af41e`: `SF.B 9a(A6)` (→`af422`)
- `af422`: `JSR b0062(PC)`
- `af426`: `JSR b0106(PC)` (경계 U16, C 반환)
- `af42a`: `BCS.W af43c` (carry 소비)
- `af42e` / `af49c` / `b05ce`: `MOVEA.L c(A6),A0; SUBQ.B #1,62(A0); JMP 2a00.L`
- `af43c`: `MOVE.B 9e(A6),D0; LSL.W #8,D0; BSR.W b02c8` (경계 U16)
- `af446` / `af4b8`: `MOVE.B D0,a1(A6); MOVE.B D0,a0(A6); JSR b0206(PC)` (경계 U16, C 반환)
- `af452`: `BCC.W af470` (carry 소비)
- `af456`: `MOVEA.L 76(A6),A0; MOVE.W 42(A0),D0; CMP.W 42(A6),D0; BLE.W af46c`
- `af466` / `af47a` / `af4e0`: `BSET.B #0,15(A6)` (→다음)
- `af46c`: `BRA.W af480`
- `af470`: `CMPI.W #a0,42(A6); BGT.W af480`
- `af480`: `MOVE.L #af6ec,(A6); RTS`
- `af488`: `JSR b0062(PC)`
- `af48c`: `JSR 4c0ac.L` (U12)
- `af492`: `BTST.B #7,15(A6); BNE.W af4aa`
- `af4aa`: `MOVEQ #0,D0; JSR 4c1de.L`
- `af4b2`: `MOVE.W D7,D0; BSR.W b02c8` (경계 U16)
- `af4c4`: `BCC.W af4d4` (carry 소비)
- `af4c8`: `MOVEA.L 76(A6),A0; MOVE.W 42(A0),D0; BRA.W af4d8`
- `af4d4`: `MOVE.W #a0,D0` (→`af4d8`)
- `af4d8`: `CMP.W 42(A6),D0; BLE.W af4e6`
- `af4e6`: `MOVE.L #af6de,(A6); RTS`

**`b0062` 8 + `b00da` 1 + 공유 꼬리 `b05be` 4(`b05ce`는 위 `af42e` 줄)**
- `b0062`: `BSR.W b00da`
- `b0066`: `MOVE.W #c45,D0; MOVE.B #0,D1; JSR 8ebe.L` (U02)
- `b0074`: `MOVE.W #8898,68(A6); MOVE.W #8898,1e(A6); MOVE.L #b05ee,56(A6); LEA caadc.L,A0; JSR 490ba.L`
- `b0094` / `b00a4` / `b00b4` / `b00c4`: `MOVE.W D0,o(A6); LEA t.L,A0; JSR 490ba.L` (o,t = `54`,`cabba` / `82`,`cabd4` / `84`,`cabee` / `86`,`cac08`)
- `b00d4`: `MOVE.W D0,88(A6); RTS`
- `b00da`: `MOVE.W 76(A6),D0; MOVE.W 78(A6),D1; MOVE.W 7a(A6),D2; MOVEQ #0,D7; MOVE.W D7,76(A6); MOVE.W D7,78(A6); MOVE.W D7,7a(A6); MOVE.W D7,7c(A6); MOVE.W D0,8a(A6); MOVE.W D1,92(A6); MOVE.W D2,94(A6); RTS`
- `b05be`: `LEA b05e6.L,A0; JSR 1ab02.L` (U05, C 반환)
- `b05ca`: `BCC.W b05dc` (carry 소비)
- `b05dc`: `RTS`

(수: `4662e` 58, `4950e` 9, `4c1de` 19, `4c29a` 2, `af078` 3, `af146` 36, 자식·경로 35, `b0062`/`b00da` 9, `b05be` 4; 합 175. 묶인 `af210` `4c236`은 시작이 아니다.)

## 구현 범위와 규약

- routing 9 범위: `4662e..4683c`, `4950e..4954e`, `4c1de..4c266`, `4c29a..4c2c4`, `af078..af096`, `af146..af302`, `af3de..af4ee`, `b0062..b0106`, `b05be..b05de`. 짝수 PC 855개 중 block 시작 175, 내부 680. 내부 PC 직접 진입은 `unsupported animation objects u15 PC`다. 경계 callee 9개, 범위 밖 설치 callback과 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **carry 소비 block 7개**(FLOW_ONLY): `af150` `af27a` `af2e6` `af42a` `af452` `af4c4` `b05ca`. Unknown이면 `objects u15 caller requires known carry`.
- **known carry 생산 block 4개**: `49542` `4c260`(Clear), `49548` `4c25a`(Set).
- **FLOW_ONLY 50개**(C 보존, 소비 7개 포함):
  - JSR/BSR만: `4950e` `4951a` `4c29a` `46640` `46670` `46674` `4671a` `46748` `4674c` `af1e4` `af1ea` `af274` `af2b8` `af2e0` `af3ea` `af3f8` `af3fe` `af402` `af408` `af422` `af426` `af488` `af48c` `b0062`.
  - `BSET`+`JSR`: `af146` `af3de`. LEA+JSR: `b05be`. LEA만: `49534`.
  - BRA: `4c1ee` `4c244` `af092` `af22a` `af2dc` `af2fe` `af46c`. RTS: `b05dc`.
  - BTST+Bcc(Z만): `af2ee` `af492`. BSET만: `af466` `af47a` `af4e0`. `Scc`(+BRA): `af3f0` `af41e`.
  - 소비 Bcc 7개.
- 그 밖 121개(MOVE/MOVEQ/MOVEA+MOVE/CLR/TST/CMP/CMPI/ADD/ADDI/SUB/SUBI/SUBQ/SUBX/ANDI/ORI/LSL/SWAP/EXT/EXG/MOVEM, `MOVE.L #imm,(A6)` block, 스택 MOVE block)는 Unknown이다(생산 4개는 위와 같이 known).
- block 안 flag는 같은 block 안에서 만들고 쓴다. RTS를 넘는 N/Z 소비는 없다. [F] 호출자 바로 뒤 명령(`nextins.py`): `4662e` 1곳 → `MOVE.L`; `4c29a` 16곳 → `BTST`/`ANDI`; `4c1de` 20곳 → `BCS`/`BCC`(C, 생산 block이 정함)/`BTST`/`BCLR`/`MOVE.W`; `4950e` 16곳 → `BCS`/`BCC`(C)/`MOVE`; `b0062` 5곳 → `JSR`/`MOVE.L`; `b00da` 1곳 → `MOVE.W`.
- 반복: `4c216..4c252`(D5가 0이 되거나 `469d8`의 D6 bit 0이 0이면 끝; 단계마다 |D5|가 8씩 줄어 유한). I/O port 쓰기와 bank 변경은 없다. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM 읽기는 기존 checked 오류다.

## 의존·경계

- [F] U15a → 기존: 위 "기존 실행부로 나가는 호출" 목록.
- [F] U15a → 경계: U16 `b0106` `b0206` `b02c8`, `491fe` `49214` `4b702` `d3c2a`, U15b `45afe`, U15c `45b1a`.
- [F] 기존 → U15a: U08b `4688a BSR 4662e`, U12 `7026a JSR 4c1de`·`70226 JSR 4c29a`(U12 계약의 경계). 그 밖 `JSR 4950e` 16곳(U16 `b0206` 포함), `JSR 4c1de` 20곳, `JSR 4c29a` 16곳은 다른 단위다.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, TB 기준)에서 U15a block에 닿는 callback과 seed:
- `af078` `af146`: seed 18 19 96 97 102 103(RNG+`80` 변형에서 `af1e4` `af3fe`도).
- `4662e`(U08b `4683c` 경로): `2b96c` `2b99c` `38bac` `38c36`(116 117), `736d2` `73800` `7382e` `b6338` `b6406`(42 43), `858d8` 계열(36 37), `8664c`~`86f88`(6 7 12 13), `b631c` `b6764`(68~71), `b6362` `b6ac8`(80 81), `bbf80` `bbfd2`(22 23), `c3df2` 계열(34 35). RNG+`80` 변형은 `7086a`/`7090a`/`72bcc` 계열(18 19 26 27 38 39 62 63 76 77 96~99 102~105)과 `bacf2`(0 1 127~135)가 더해진다.
- 175 block 중 TB 기준 base 104개, RNG+`80` 변형 124개가 자연 도달한다. 미도달(RNG+`80` 변형 52개: `4667c` `46684` `466dc` `466e4` `466f6` `46780` `46788` `4679a` `467ae` `467ea` `467f2` `46804` `46818` `4951a` `49520` `49534` `49542` `4c1fa` `4c216` `4c23a` `4c242` `4c244` `4c248` `4c250` `4c252` `af154` `af214` `af22a` `af274` `af27a` `af27e` `af28e` `af2b8` `af2be` `af2c6` `af2ce` `af2d2` `af2ea` `af2f8` `af3de` `af3ea` `af3f0` `af3f8` `af422` `af456` `af466` `af46c` `af47a` `af49c` `af4c8` `af4d8` `b05ce`; TB가 앞 block과 합쳐진 경우 포함)는 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] 기준 C++ 차분(작업 트리 `7b2f3e5`, F2 프레임 패스 142 seed): 일치 pass 10,496개·node 79,600개, 불일치 0, 자연 완주 85 seed. RNG 초기화 400 frame 차분: 일치 pass 23,684개·node 159,359개, 불일치 0, complete 59(변형 6: pass 808).
- [I] U15a만 병합하면 위 seed는 `45b1a`(U15c)·`b0106`/`b02c8`(U16)·`4b702` 등에서 멈춘다. 새 완주 seed는 기대하지 않는다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 175 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 4 known, 그 밖 Unknown), 소비 7 block의 Unknown 오류, zero-step, 내부 680 PC 정확한 오류, 홀수 PC, 경계 9개 stop(rollback 없음), rollback 탐침은 `5f6xx..5ffxx`만. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력; ROM 자료는 test에 넣지 않음)로 비교한다.
- 실제 ROM 차분: `4662e`(D3=0, D7=`160`, 위·아래 이동, `45176` 결과 `80000000`/V 경계, `54b4`=0/≠0; `45afe`/`45b1a` 경계 stop), `4950e`(`568e(A5)` 0~3, RNG), `4c1de`(D0 부호·크기, `469d8` D6 bit 0), `4c29a`, `af078`/`af146`/`af1e4`/자식 callback(실제 `c6a96` `490ba` `49f8c` `49274` `43e34` `49fc6` `2986` `28ae` `287e` `4b54e` `1ab02` `2a00` `8ebe` `4c0ac` `49a58`), 소비 7 block(선언 C)을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed, seed 58·59는 `animation_machine_pvc_banks_native`): 기준 일치 pass 10,496개·node 79,600개 유지 또는 증가, 불일치 0. RNG 초기화 400 frame 차분: 기준 23,684 pass·159,359 node 유지 또는 증가, 불일치 0.

## 미확인·범위 밖

1. [I] `4662e`는 수직 이동 D3를 지형(`45176` 높이, `4483a`/`447be` 지형 코드)과 맞춰 `54aa..54b4(A5)` 접지 상태를 갱신하는 함수로 보인다. `54aa` bit 6(`40`)·bit 10(`400`), `54b4`의 게임 의미는 미확인이다.
2. [I] `4950e`는 `49370`(1P/2P 상태)과 RNG로 player node(`100cb8`/`100da8`)를 골라 A0와 C(Set = 없음)로 돌려주는 함수로 보인다.
3. [I] `4c1de`는 이동량 D0를 ±8 단위로 나눠 `469d8`(U09 지형 충돌)을 반복하는 함수, `4c29a`는 목표 좌표(D2,D3)로의 한 번 이동이다.
4. [I] `af078`/`af146`은 `b0106`/`b0206`/`b02c8`(U16) 판정에 따라 자식(`af3de` `af3f8` `af3fe`)을 만들고 다음 frame callback(`af4ee` `af6de` `af6ec` `af302`)을 고르는 장치·적 객체로 보인다.
5. [U] U15b/U15c의 표 대상 의미와 `D7`=`174`(`45afe`/`45b1a` 특례)의 의미. U15b/U15c 계약에서 다룬다.

작업자 scratch: 세션 scratchpad `f4u15/`(`u15.py` block·범위·SHA 계산, `split.py` U15b/U15c 계산, `scope.py` `s3.py` `s4.py` `body.py` `trav.py` `hroute_u15.py` `u15dis.py`, `refs.py` `nextins.py` `probes.py` `reach.py`; 저장소 밖).
