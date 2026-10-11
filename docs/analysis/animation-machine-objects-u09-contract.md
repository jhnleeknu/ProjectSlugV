# 객체 callback F4 U09: C6 지형 b 조각(`469a0`/`469ae`/`469d8`, `4706c`/`47070`, `47134`/`47212`)과 `7670e` 객체 계열 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U09 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`)과 U07 계약(`animation-machine-objects-u07-contract.md`, SHA256 `734615e139a6e0577154eace301c66a0ea9fb94137e0e6cf921dd15ff1ab99a9`)을 따른다. U08 분할은 U08 계약(`animation-machine-objects-u08-contract.md`, SHA256 `fd484c1cc1bcd87a87f69892451a1cfd36528db5797cca7298514c8c1f703d8d`)을 참조했다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee는 실행부 없는 경계(`unsupported animation machine PC`)다.
- 결정 6: `TRAP #f`는 실행부 없는 checked 경계다(stop이면 직전 상태로 멈춤, 아니면 rollback).
- U01~U07 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다. `MOVE.x`/`MOVEQ`/`TST`/`CMP`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). `LEA`/`MOVEA`/`EXG`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/`DBRA`와 BYTE `BSET #n`(Z만)만인 block은 FLOW_ONLY다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U09의 코드와 자료는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u09`(HEAD `e1ef6b4`, U01~U07 WIP + U06 guard 제거, `engine/src/animation_machine.cpp` SHA256 `e7bebbad077b391175a4f64434c6862a91859a08e33eadd517e4e9cc5dd74cdb`)을 참조했다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u09/u09.py`가 원본 opcode에서 독립 계산했고 아래 목록과 같음을 assert했다.

## 요약

- [F] U09는 **block 시작 150개 + TRAP 경계 1개(`470e6`)**다. 함수 진입 9개(`469a0` `469ae` `469d8` `4706c` `47070` `47134` `47212` `7670e` `76718`)와 `MOVE.L #imm,(A6)` 설치 callback 5개(`76768` `7678a` `767b6` `767c6` `767ec`)를 포함한다. 코드 5 범위, 1,490바이트, 396명령이며 미해독·PC 상대 점프 표·레지스터 간접 점프는 없다. 묶인 Bcc는 `46bb8`(`46bb0`의 `BMI`/`BEQ`) 하나다. routing 짝수 PC는 745개, 내부 PC는 595개다.
- [F] **범위 문서 142와의 차이(+8)**:
  - +8: 설치 callback `7678a`(`76780`이 설치)와 그 뒤 `7679a` `767aa` `767b6` `767bc` `767c2`, 설치 callback `767c6`(`76844`이 설치)와 `767dc`. 범위 스크립트(`f4scope/plan.py`의 `blocks`)는 TB 관측 함수만 셌고 이 경로는 자연 관측이 없다. 수용 관례("MOVE-installed callback entries are starts")에 따라 센다.
  - +2: `DBRA` 대상 `471ec` `471fa`. 범위 스크립트는 이 둘을 별도 함수(C6 표의 `471ec` `471fa`)로 보아 U09 몫에서 뺐다. 결정 5(함수 본문 전체)에서는 `47134` 본문의 loop block이다.
  - −1: 묶인 `46bb8`(U01 관례). −1: TRAP 자리 `470e6`(결정 6, block이 아니라 경계).
- [F] **경계 callee(실행부 없음) 8개**: U08a(다른 작업 트리 `metalslug-u08`에서 구현 중) `43eb8` `447be` `4483a` `49274`, U08b(제안, 미구현) `4683c` `468e0` `461ec`, U11 `45176`. 범위 문서의 "경계 callee 1"(`45176`)은 범위 문서 누적 집합에 U08 전체가 들어 있다는 전제다. U08이 U08a/U08b로 나뉘었으므로 이 작업 트리(`e1ef6b4`, U08 없음)에서는 8개가 모두 경계다. U08a 병합 뒤에는 `43eb8` `447be` `4483a` `49274`가 실행된다(아래 "U08 의존").
- [F] 기존 실행부로 나가는 출구: frame_helpers `46f52`(`470da`/`47130 BRA`, 그 RTS가 U09 진입 호출자로 복귀), cleanup `43e22` `43e38` `43e34`, U02 `8ebe`, interpreter `49f8c` `49fc6`, fade_card `28ae`(객체 생성)·`2a00`(JMP, 자기 삭제), U05 `1ab02`(C 반환).
- [F] 읽는 ROM 자료는 `469a0`이 `54e2(A5)`에 넣는 LONG 포인터 목록 `46994..469a0`(LONG 3개, 0 LONG 끝)뿐이다. `469b2 MOVEA.L (A3)+,A1`로 live bus에서 읽는다(bank window 자료 없음). I/O port 쓰기와 bank 변경은 U09 자체에 없다.
- [F] 자연 seed(F2 프레임 패스 120 frame): 범위 scratch 재생(`f4scope/dyn`)에서 U09 block에 닿는 callback은 `7670e`·`76718`(seed 0 1 127~135, frame 0)과 `469d8`/`4706c`/`47070`을 부르는 미연결 callback 70여 개다. 이 작업 트리 기준 C++ 프레임 패스는 모든 해당 seed에서 앞선 미연결 callback(예: `dbdb6`)에서 먼저 멈추므로 [I] U09만으로 새 완주 seed·새 일치 pass는 없다(범위 문서 "새 자연 seed -"와 같음). 기준 일치 pass 10,016개는 그대로여야 한다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 정정(142→150).** 설치 callback 경로 8개를 넣고 `DBRA` 대상 2개를 U09 본문에 두며, 묶인 `46bb8`과 TRAP `470e6`을 뺀다(권고, 관례와 같음). 범위 문서는 고치지 않는다.
2. **U08 의존 경계.** `43eb8` `447be` `4483a` `49274`(U08a)와 `4683c` `468e0` `461ec`(U08b)를 U09에서는 실행부 없는 경계로 둔다(권고). U09 routing은 이 PC들을 포함하지 않으므로 U08a 병합 시 충돌이 없다. U08b가 구현되면 `469d8` 본문 전체가 연결된다.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u09.cpp`의 `animation_objects_u09_block`. 오류는 `unsupported animation objects u09 PC`, `objects u09 caller requires known carry`(메인 지시와 같음).
4. **SUBX(`46a46` `46b68`).** [F] 두 곳 모두 같은 block 안의 `SUB.L D2,D4`가 X를 만들고 곧바로 `SUBX.L D3,D5`와 `BNE`/`BEQ`가 소비한다. 실행 상태에 X를 두지 않고 block 안에서 계산한다(권고): `X=(D2 >u D4)`, `D5=D5−D3−X`, Z=`(D4 결과=0) AND (D5 결과=0)`(SUBX는 0이 아닐 때만 Z를 지우고 0이면 유지).
5. **`CLR.B`/`CLR.L`의 68000 읽기 주기.** 대상이 모두 work RAM d16(A5)/d16(A0)이므로 상태 차이가 없다. U07처럼 쓰기만 모델한다(권고).
6. **무효화 탐침 교체.** `engine/tests/animation_machine_frame_helpers_test.cpp`의 outside 탐침 `0x4706c`(U09 시작이 됨)를 미연결 `0x5f500`(어느 `docs/analysis` 문서에도 없음)으로 바꾼다.

## 원본 바이트 근거

[F] 코드 5 범위 합계 1,490바이트(`470e6` TRAP 2바이트 제외). 범위 순서로 이어 붙인 SHA256 `3b4b6c0a0fc82b2ec0eb86fc8ad84a5b993f3dbc4beaf07ffab886da4a10178a`.

| CPU 범위 | 바이트 | SHA256 |
| --- | --- | --- |
| `469a0..46bfc` | 604 | `3f94bc624a0a66723504abc1d9bf369380d852e79101fa3c682fb5d8b17fccd6` |
| `4706c..470e6` | 122 | `974977cb6b051d3323d6292dc0fa860a85c62e53bde064b224e3a34b9d557be6` |
| `470e8..47288` | 416 | `1a7dee701bf489b7994e1d63c3c8999b25b43cc4cb592812accf6df05f65cf3a` |
| `7670e..76852` | 324 | `e853eb1b93633b1f95c8a60048298108e08a1e575d960e13074ced19181a22d8` |
| `769fc..76a14` | 24 | `7b91fc360831e7b53a02fe8a30964c4d4f82c5748cf6ec33f0c8a10edc08b0d7` |

- [F] 범위 밖 이웃: `46994..469a0`(LONG 포인터 목록, 자료), `46bfc`(다른 함수), `46f52..4706c`(frame_helpers 실행부, `4706a RTS`), `470e6`(TRAP `4e4f`), `47288`(U08a 경계 `47288` 함수), `7670e` 앞(다른 함수), `76852..769fc`(`7679a`/`767c6`이 `28ae`로 만드는 자식 객체 callback `76852`, U09 밖), `76a14..`(`1ab02`의 범위 record 자료와 animation 목록 `76aa0` `76aac` `76b8c`, U09는 주소만 넘긴다).
- [F] 자료(모두 live bus):
  - ROM LONG 목록 `46994`: `469b2`가 `(A3)+`로 읽는다(A3=`54e2(A5)`).
  - work RAM `54xx(A5)`: LONG `54ba` `54be`(MOVEM) `54c2` `54c8` `54cc` `54d0` `54d4` `54d8` `54e2`, WORD `54aa` `54ac` `54ae` `54b0` `54b2` `54dc` `54de` `567c` `5418`, BYTE `549c` `549d` `54a0` `54c6` `54e0` `567a`, 표 `5646..` `5656..`(BYTE OR), `5666+D7`(BYTE), 슬롯 표 `54e6+2c·k`(`561a`=k 7)의 LONG `(A0)` `4` `8` `c` `10` `26`과 WORD `26` `2a`, `538e`의 LONG `14` `18`.
  - 노드 d16(A6): BYTE `15`(BSET) `6c` `88` `89`, WORD `1e` `20` `68` `76` `78` `7a` `7c` `82` `86`, LONG `42` `46`과 `(A6)`(callback 설치). 노드 d16(A0): LONG `14` `18` `1c` `20`(`47164`).
- [F] 스택: `46a9a`가 LONG D2·D3를 push하고(`46ab8`이 `(A7)`/`4(A7)`를 읽음) `46b54`가 pop한다. `47134 MOVEM.L D0-D3/A0,-(A7)`(낮은 주소부터 D0 D1 D2 D3 A0)와 `47206 MOVEM.L (A7)+,D0-D3/A0`. 그 밖은 JSR/BSR 복귀 LONG이다.

## block 목록과 실행 의미

[F] 150 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `MOVE.B`/`MOVE.W` Dn·`ADDQ.W`/`SUBQ.W` Dn·`CLR.W` Dn·`SUB.W` Dn·`LSR.W`는 나머지 bit를 보존하고 `MOVEQ`는 LONG 전체를 쓴다. `MOVEA.W`/`CMPA.W #0`은 부호확장 LONG이다. 부호 비교(`BGT`/`BLT`/`BLE`/`BGE`)는 피연산자 크기의 2의 보수 비교이며 `SUB.W` 뒤 `BGE`는 N⊕V=0이다. `BHI`는 무부호 `>`, `BLS`는 무부호 `≤`, `BCC`/`BCS`는 그 명령의 C다.

**포인터 목록 순회 `469a0`/`469ae` 7**
- `469a0`: `MOVE.L #46994,54e2(A5); JMP 47134`
- `469ae`: `MOVEA.L 54e2(A5),A3` (→`469b2`)
- `469b2`: `MOVEA.L (A3)+,A1; CMPA.W #0,A1; BEQ 469d2`
- `469bc`: `MOVE.L A3,54e2(A5); MOVEA.L 2e(A1),A2; CMPA.W #0,A2; BEQ 469b2`
- `469ca`: `TST.W 2(A2); BEQ 469b2`
- `469d0`: `RTS`
- `469d2`: `JMP 47212`

**지형 탐색 `469d8` 53**
- `469d8`: `LEA 108000,A5; MOVEQ #0,D7; MOVE.W D7,54aa(A5); MOVE.B D7,54c6(A5); MOVE.B D7,54e0(A5); MOVE.W D7,54de(A5); MOVE.L #ffffffff,54c2(A5); MOVE.L D7,54d4(A5); MOVE.L #160,54d8(A5); MOVE.L #80000000,54d0(A5); MOVEA.W #0,A1; JSR 43eb8` (U08a 경계)
- `46a16`: `MOVEA.L A1,A0` (→`46a18`)
- `46a18`: `TST.W 54c2(A5); BMI 46a64`
- `46a20`: `TST.W 54de(A5); BNE 46a5a`
- `46a28`: `ADDI.B #4,54e0(A5); BCC 46a3c` (BYTE 덧셈 carry)
- `46a32`: `CLR.B 54e0(A5); MOVE.W #ffff,54de(A5)` (→`46a3c`)
- `46a3c`: `MOVE.L 54c8(A5),D4; MOVE.L 54cc(A5),D5; SUB.L D2,D4; SUBX.L D3,D5; BNE 46a56` (결정 4)
- `46a4c`: `CLR.B 54e0(A5); MOVE.W #ffff,54de(A5)` (→`46a56`)
- `46a56`: `BRA 46a64`
- `46a5a`: `ADDI.B #20,54e0(A5); BCS 46a86`
- `46a64`: `MOVE.L D2,54c8(A5); MOVE.L D3,54cc(A5); CLR.B 54c6(A5); BSR 469a0`
- `46a74`: `BSR 468e0` (U08b 경계)
- `46a78`: `SUB.L D0,D2; SUB.L D1,D3; TST.B D6; BNE 46b6e`
- `46a82`: `BRA 46b78`
- `46a86`: `ORI.W #80,54aa(A5); MOVEQ #0,D2; MOVEQ #0,D3; LEA 10d38e,A1; BRA 46bde`
- `46a9a`: `MOVEM.L D0-D1,54ba(A5); MOVE.L D2,-(A7); MOVE.L D3,-(A7); BSR 4683c` (U08b 경계)
- `46aa8`: `MOVE.W 54b0(A5),D7; MOVEQ #0,D2; MOVEQ #-1,D3; TST.B 549d(A5); BNE 46abe`
- `46ab8`: `ADD.L (A7),D3; ADD.L 4(A7),D2` (→`46abe`)
- `46abe`: `BSR 4483a` (U08a 경계)
- `46ac2`: `CMPI.W #160,D7; BEQ 46ad4`
- `46aca`: `BSR 45176` (U11 경계)
- `46ace`: `TST.L D6; BPL 46b3a`
- `46ad4`: `SWAP D0; SWAP D1; SUBQ.W #8,D1; BSR 447be` (U08a 경계)
- `46ade`: `MOVE.W D6,54b2(A5); MOVE.W 54ae(A5),D4; MOVE.W D7,54ae(A5); CMPI.W #174,D4; BNE 46afe`
- `46af2`: `CMPI.W #174,D7; BNE 46afe`
- `46afa`: `MOVE.W #160,D7` (→`46afe`)
- `46afe`: `CMPI.W #178,D7; BEQ 46b0c`
- `46b04`: `CMPI.W #17c,D7; BNE 46b16`
- `46b0c`: `MOVE.W #160,D7; ORI.W #400,54aa(A5)` (→`46b16`)
- `46b16`: `MOVE.W D7,54b0(A5); ADDQ.W #8,D1; SWAP D1; SWAP D0; CMPI.W #160,D7; BEQ 46b54`
- `46b28`: `BSR 4483a` (U08a 경계)
- `46b2c`: `BSR 45176` (U11 경계)
- `46b30`: `ADDI.L #80000,D6; BMI 46b54`
- `46b3a`: `CMP.L 54d0(A5),D6; BHI 46b54` (무부호 `D6 > LONG`)
- `46b42`: `MOVE.W 54b2(A5),54dc(A5); MOVE.L D6,54d0(A5); MOVE.L D7,54d8(A5); MOVE.L A0,54d4(A5)` (→`46b54`)
- `46b54`: `MOVE.L (A7)+,D5; MOVE.L (A7)+,D4; MOVE.L D0,D2; MOVE.L D1,D3; MOVEM.L 54ba(A5),D0-D1; SUB.L D0,D2; SUB.L D1,D3; SUB.L D2,D4; SUBX.L D3,D5; BEQ 46b78` (결정 4)
- `46b6e`: `MOVE.L A0,54c2(A5); MOVE.B #ff,54c6(A5)` (→`46b78`)
- `46b78`: `BSR 469ae`
- `46b7c`: `CMPA.L 54c2(A5),A1; BEQ 46b9c`
- `46b84`: `JSR 43eb8` (U08a 경계)
- `46b8a`: `MOVEA.L A1,A0; CMPA.W #0,A0; BNE 46a9a`
- `46b94`: `TST.B 54c6(A5); BNE 46a18`
- `46b9c`: `MOVEA.W #0,A1; CMPI.B #1,54a0(A5); BEQ 46bb0`
- `46baa`: `LEA 10d38e,A1` (→`46bb0`)
- `46bb0`: `MOVE.L 54d0(A5),D6; BMI 46bde; BEQ 46bc6` (묶음 `46bb8`)
- `46bbc`: `TST.B 549d(A5); BEQ 46bde`
- `46bc4`: `SUB.L D6,D3` (→`46bc6`)
- `46bc6`: `ORI.W #1,54aa(A5); TST.W 54dc(A5); BEQ 46bda`
- `46bd4`: `ORI.W #100,54aa(A5)` (→`46bda`)
- `46bda`: `MOVEA.L 54d4(A5),A1` (→`46bde`)
- `46bde`: `JSR 43eb8` (U08a 경계)
- `46be4`: `MOVEA.L A1,A0; ADD.L D2,D0; ADD.L D3,D1; MOVE.L 54d8(A5),D7; BSR 461ec` (U08b 경계)
- `46bf2`: `MOVE.W 54aa(A5),D6; MOVE.W 54ac(A5),D4; RTS`

**슬롯 등록 `4706c`/`47070` 14 + TRAP 경계**
- `4706c`: `MOVEQ #0,D0; MOVEQ #0,D1` (→`47070`)
- `47070`: `CMPA.W #0,A0; BNE 4707c`
- `47078`: `MOVEA.W #ffff,A0` (→`4707c`)
- `4707c`: `MOVEQ #0,D2; MOVE.B 6c(A6),D2; CMPI.B #ff,D2; BNE 470de`
- `4708a`: `LEA 561a(A5),A4; MOVEQ #7,D7` (→`47090`)
- `47090`: `TST.W 26(A4); BPL 470a0`
- `47098`: `TST.W 2a(A4); BEQ 470aa`
- `470a0`: `LEA -2c(A4),A4; DBRA D7,47090`
- `470a8`: `RTS`
- `470aa`: `MOVE.B D7,6c(A6); MOVE.W D7,567c(A5); MOVE.L A0,26(A4); SWAP D0; SWAP D1; CLR.W D0; CLR.W D1; ADD.L 42(A6),D0; ADD.L 46(A6),D1; LEA 538e(A5),A1; SUB.L 14(A1),D0; SUB.L 18(A1),D1; MOVEA.L A4,A0; JSR 43e22` (cleanup)
- `470da`: `BRA 46f52` (frame_helpers)
- `470de`: `CMPI.W #8,D2; BCS 470e8` (무부호. 아니면 TRAP `470e6` 경계)
- `470e8`: `MOVE.W D2,567c(A5); MULU.W #2c,D2; LEA 54e6(A5),A4; ADDA.W D2,A4; MOVE.L A0,26(A4); SWAP D0; SWAP D1; CLR.W D0; CLR.W D1; ADD.L 42(A6),D0; ADD.L 46(A6),D1; LEA 538e(A5),A1; SUB.L 14(A1),D0; SUB.L 18(A1),D1; MOVEA.L A4,A0; MOVE.L D0,(A0); MOVE.L D1,4(A0); MOVE.L A1,10(A0); CLR.L 8(A0); CLR.L c(A0); JSR 43e38` (cleanup)
- `47130`: `BRA 46f52` (frame_helpers)

**겹침 검사 `47134` 28**
- `47134`: `MOVEM.L D0-D3/A0,-(A7); MOVEQ #0,D7; MOVE.B 549c(A5),D7; CMPI.B #3,D7; BCS 4714a`
- `47146`: `MOVE.B #2,D7` (→`4714a`)
- `4714a`: `LEA 5666(A5),A1; ADDA.W D7,A1; MOVE.B (A1),567a(A5); BEQ 47206`
- `47158`: `ADD.L D0,D2; ADD.L D1,D3; CMPA.W #0,A0; BEQ 47174`
- `47164`: `ADD.L 1c(A0),D0; ADD.L 20(A0),D1; ADD.L 14(A0),D2; ADD.L 18(A0),D3` (→`47174`)
- `47174`: `SWAP D0; SWAP D1; SWAP D2; SWAP D3; CMP.W D2,D0; BLE 47184`
- `47182`: `EXG D2,D0` (→`47184`)
- `47184`: `CMP.W D3,D1; BLE 4718c`
- `4718a`: `EXG D3,D1` (→`4718c`)
- `4718c`: `MOVE.W #ffa0,D4; MOVE.W #19f,D5; CMP.W D5,D0; BGT 47202`
- `4719a`: `CMP.W D4,D2; BLT 47202`
- `471a0`: `SUB.W D4,D0; BGE 471a8`
- `471a6`: `CLR.W D0` (→`471a8`)
- `471a8`: `CMP.W D5,D2; BLE 471b0`
- `471ae`: `MOVE.W D5,D2` (→`471b0`)
- `471b0`: `SUB.W D4,D2; MOVE.W #80,D4; MOVE.W #27f,D5; CMP.W D5,D1; BGT 47202`
- `471c0`: `CMP.W D4,D3; BLT 47202`
- `471c6`: `SUB.W D4,D1; BGE 471ce`
- `471cc`: `CLR.W D1` (→`471ce`)
- `471ce`: `CMP.W D5,D3; BLE 471d6`
- `471d4`: `MOVE.W D5,D3` (→`471d6`)
- `471d6`: `SUB.W D4,D3; LSR.W #5,D0; LSR.W #5,D1; LSR.W #5,D2; LSR.W #5,D3; SUB.W D0,D2; SUB.W D1,D3; LEA 5646(A5),A1; ADDA.W D0,A1; MOVEQ #0,D7` (→`471ec`)
- `471ec`: `OR.B (A1)+,D7; DBRA D2,471ec`
- `471f2`: `LEA 5656(A5),A1; ADDA.W D1,A1; MOVEQ #0,D6` (→`471fa`)
- `471fa`: `OR.B (A1)+,D6; DBRA D3,471fa`
- `47200`: `AND.B D6,D7` (→`47202`)
- `47202`: `AND.B D7,567a(A5)` (→`47206`)
- `47206`: `MOVE.W #8,567c(A5); MOVEM.L (A7)+,D0-D3/A0; RTS`

**겹침 결과 순회 `47212` 13**
- `47212`: `MOVE.W 567c(A5),D7; BEQ 4727a`
- `4721a`: `LEA 54e6(A5),A1; MOVE.W D7,D5; MULU.W #2c,D5; ADDA.W D5,A1; MOVE.B 567a(A5),D6` (→`4722a`)
- `4722a`: `TST.B D6; BEQ 4727a`
- `47230`: `SUBQ.W #1,D7; LEA -2c(A1),A1; ADD.B D6,D6; BCC 4722a` (BYTE 덧셈 carry)
- `4723a`: `TST.W 26(A1); BMI 4722a`
- `47240`: `MOVE.B 6c(A6),D5; BMI 47270`
- `47248`: `CMP.B D5,D7; BEQ 4722a`
- `4724c`: `LEA 54e6(A5),A4; ANDI.W #ff,D5; MULU.W #2c,D5; ADDA.W D5,A4; MOVEA.L 10(A1),A3` (→`4725e`)
- `4725e`: `CMPA.W #0,A3; BEQ 47270`
- `47266`: `CMPA.L A4,A3; BEQ 4722a`
- `4726a`: `MOVEA.L 10(A3),A3; BRA 4725e`
- `47270`: `MOVE.W D7,567c(A5); MOVE.B D6,567a(A5); RTS`
- `4727a`: `MOVE.W #0,567c(A5); MOVEA.L #0,A1; RTS`

**객체 callback `7670e`/`76718`(+설치 callback 5) 35**
- `7670e`: `MOVE.B #0,89(A6); BRA 7671e` (callback 진입)
- `76718`: `MOVE.B #1,89(A6)` (callback 진입, →`7671e`)
- `7671e`: `MOVE.W #c53,D0; MOVE.B #0,D1; JSR 8ebe` (U02)
- `7672c`: `MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); TST.W 76(A6); BEQ 76746`
- `76740`: `BSET.B #0,15(A6)` (→`76746`)
- `76746`: `JSR 49274` (U08a 경계)
- `7674c`: `MOVE.W #b,20(A6); MOVEA.L #76aa0,A1; MOVE.W #100,D0; JSR 49f8c` (interpreter)
- `76762`: `MOVE.L #76768,(A6)` (→`76768`)
- `76768`: `JSR 43e34` (설치 callback 진입, cleanup)
- `7676e`: `JSR 49fc6` (interpreter)
- `76774`: `MOVE.W 5418(A5),D0; CMP.W 78(A6),D0; BLT 76786` (부호 WORD `D0 < 78(A6)`)
- `76780`: `MOVE.L #7678a,(A6)` (→`76786`)
- `76786`: `BRA 7684e`
- `7678a`: `MOVEA.L #76aac,A1; MOVE.W #100,D0; JSR 49f8c` (설치 callback 진입)
- `7679a`: `MOVEA.L #76852,A0; MOVE.W #a,D0; JSR 28ae` (자식 `76852`)
- `767aa`: `MOVE.W 7c(A6),86(A6); MOVE.L #767b6,(A6)` (→`767b6`)
- `767b6`: `JSR 43e34` (설치 callback 진입)
- `767bc`: `JSR 49fc6`
- `767c2`: `BRA 76818`
- `767c6`: `MOVE.W #c,82(A6); MOVEA.L #76852,A0; MOVE.W #a,D0; JSR 28ae` (설치 callback 진입)
- `767dc`: `MOVE.W 7c(A6),86(A6); SF.B 88(A6); MOVE.L #767ec,(A6)` (→`767ec`)
- `767ec`: `JSR 43e34` (설치 callback 진입)
- `767f2`: `JSR 49fc6`
- `767f8`: `TST.W 82(A6); BMI 76818`
- `76800`: `SUBQ.W #1,82(A6); BNE 76818`
- `76808`: `MOVEA.L #76b8c,A1; MOVE.W #100,D0; JSR 49f8c`
- `76818`: `SUBQ.W #1,86(A6); SCS.B D0; EXT.W D0; EOR.W D0,86(A6); CMPI.W #1,7a(A6); BLS 7684a` (0에서 멈추는 감소: 빌림이면 `ffff` XOR `ffff`=0)
- `7682e`: `TST.W 86(A6); SEQ.B D0; TST.B 88(A6); SNE.B D1; AND.B D0,D1; BEQ 7684a`
- `76840`: `SUBQ.W #1,7a(A6); MOVE.L #767c6,(A6)` (→`7684a`)
- `7684a`: `BRA 7684e`
- `7684e`: `BRA 769fc`
- `769fc`: `LEA 76a14,A0; JSR 1ab02` (U05, C 반환)
- `76a08`: `BCC 76a12` (carry 소비; `1ab02` 반환 C)
- `76a0c`: `JMP 2a00` (fade_card 자기 삭제)
- `76a12`: `RTS`

(각 묶음 줄의 수는 그 묶음의 block 수다: 7+53+14+28+13+35=150.)

## 구현 범위와 규약

- routing 5 범위: `469a0..46bfc`, `4706c..470e6`, `470e8..47288`, `7670e..76852`, `769fc..76a14`. 짝수 PC 745개 중 block 시작 150, 내부 595(묶인 `46bb8` 포함). 내부 PC 직접 진입은 `unsupported animation objects u09 PC`다. TRAP `470e6`, 경계 callee 8개와 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **carry 소비 block 1개**: `76a08`(`1ab02` 반환 C; U05 `1ab7a` ANDI CCR Clear, U01 `1aafc` ORI CCR Set이 known으로 둔다). Unknown이면 `objects u09 caller requires known carry`.
- **known carry 생산 block 0개.** [F] U09 함수 진입(`469a0` `469ae` `469d8` `4706c` `47070`)의 ROM 정적 호출자 95곳 바로 뒤 명령은 C를 읽지 않는다(`RTS`/`BRA`/`BSR`/`MOVE`/`MOVEA`/`MOVEM`/`TST`/`BTST`/`CMPA`/`LEA`/`JSR`/`NEG`/`SUBQ`). block 안에서 만들고 소비하는 C(`46a28` `46a5a` `46b3a` `470de` `47134` `47230` `76818`)와 X(`46a3c` `46b54`)는 그 block 안에서 계산한다.
- **FLOW_ONLY 40개**(C 보존): `469ae` `46a16` `46bda`(MOVEA), `47078`(MOVEA.W), `46baa`(LEA), `470a0`(LEA+DBRA), `47182` `4718a`(EXG), `4726a`(MOVEA+BRA), `76740`(BSET #0, Z만), `769fc`(LEA+JSR), `46a74` `46abe` `46aca` `46b28` `46b2c` `46b78`(BSR), `46b84` `46bde` `76746` `76768` `7676e` `767b6` `767bc` `767ec` `767f2`(JSR), `469d2` `76a0c`(JMP), `46a56` `46a82` `470da` `47130` `76786` `767c2` `7684a` `7684e`(BRA), `76a08`(BCC 소비), `469d0` `470a8` `76a12`(RTS). 그 밖(MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/ADD/ADDI/ADDQ/SUB/SUBI/SUBQ/SUBX/MULU/ANDI/ORI/OR/AND/EOR/LSR/SWAP/EXT/Scc/MOVEM+MOVE가 있는 block)은 Unknown이다.
- 반환 Z·N: U09 안 소비는 모두 같은 block의 flag 생산 뒤다(묶음 `46bb0`/`46bb8` 포함). RTS를 넘는 flag 소비는 `76a08`(C)뿐이다.
- 루프: `471ec`/`471fa`의 `DBRA` 횟수는 앞선 clamp로 각각 1~16회다(원본 식 그대로 계산하며 상한을 가정하지 않음). `4725e` 연결 목록 순회와 `469b2` 목록 순회는 자료가 끝을 정한다. 순환 자료면 C++는 기존 block 예산 오류(`animation machine block budget exceeded`)로 rollback한다(원본은 끝나지 않음).
- I/O: port 쓰기는 U09 자체에 없다(callee 몫). bank 변경 없음. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM 읽기는 기존 checked 오류다.
- 회귀 탐침(결정 6): [F] `engine/tests`·`tools`·`engine/src`·`docs/analysis`에서 U09 범위 안 PC를 outside 탐침으로 쓰는 곳은 `engine/tests/animation_machine_frame_helpers_test.cpp`의 `0x4706c` 하나다(`tools/inventory_stage_spatial_frame.py`의 `(0x4701e,0x4706c)`는 배타 상한, `animation-machine-frame-helpers-u1-contract.md`의 `4701e..4706c`는 범위 표기라 해당 없음).

## U08 의존

- [F] U09 → U08a: `469d8`·`46b84`·`46bde`의 `JSR 43eb8`, `46abe`·`46b28`의 `BSR 4483a`, `46ad4`의 `BSR 447be`, `76746`의 `JSR 49274`. U09 → U08b: `46a74 BSR 468e0`, `46a9a BSR 4683c`, `46be4 BSR 461ec`.
- [F] U08 → U09: U08b 계약 초안의 경계 callee `469d8`(C4 `4be18` 등 `JSR 469d8` 17곳, ROM 정적 호출자)이 U09 진입이다. U08a 범위(`18be8` `1aa3a` `43eb8..43efa` `447be..44ade` `49274..4929e`)와 U09 범위는 겹치지 않는다.
- [I] U08a를 병합하면 `7670e`/`76718` 경로는 `49274`를 지나 `49f8c` 이후까지 실행되고, `469d8` 경로는 U08b 경계(`468e0` `4683c` `461ec`)와 U11 `45176`에서 멈춘다.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, TB 기준)에서 U09 block에 닿는 callback은 `7670e` `76718`(seed 0 1 127~135)과 `469d8`/`4706c`/`47070`을 부르는 callback(`babb4` `bb536` `b6406` `d82aa` `aef18` `af030` `bbd3c` `b6764` `beac0` 등 70여 개)이다. 150 block 중 114개가 TB 기준으로 도달한다. 미도달 36개(fixture 필요): `46a32` `46a4c` `46a5a` `46a86` `46af2` `46afa` `46b0c` `47078` `470a8` `47146` `47182` `471a6` `471ae` `471cc` `471d4` `76746` `76768` `76780` `7678a` `7679a` `767aa` `767b6` `767bc` `767c2` `767c6` `767dc` `767ec` `767f2` `767f8` `76800` `76808` `76818` `7682e` `76840` `7684a` `76a0c`(TB가 앞 block과 합쳐진 경우 포함).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 150 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), 소비 block의 Unknown 오류, zero-step, 내부 595 PC 정확한 오류, TRAP `470e6` stop·rollback, 홀수 PC, 경계 callee 8개·이웃 오류. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력과 `46994`의 합성 LONG 목록; ROM 자료는 test에 넣지 않음)로 비교한다.
- 실제 ROM 차분: `469d8` 본문의 경계 사이 구간(`46a16` `46a78` `46aa8` `46ac2` `46ace` `46ade` `46b30` `46b7c` `46b8a` `46be4` `46bf2`에서 다음 경계 또는 RTS까지, 내부 `469a0`→`47134`와 `469ae`→`47212` 실제 실행), `4706c`/`47070`(실제 `43e22`/`43e38`/`46f52`, TRAP 경계), `7670e`/`76718`(실제 `8ebe`, `49274` 경계), `7674c`·설치 callback 5개(실제 `49f8c` `43e34` `49fc6` `28ae` `1ab02` `2a00`)를 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`, seed 58·59는 `animation_machine_pvc_banks_native`): 기준(작업 트리 `e1ef6b4`) 일치 pass 10,016개·node 74,976개가 모두 그대로 일치해야 한다.

## 미확인·범위 밖

1. [I] `469d8`은 기준 객체(A1 → `43eb8`) 주변의 지형 후보를 `469ae`(목록 `46994`의 두 work RAM 기준 `109156`·`10b1d6`과 그 `2e` 연결)와 `47212`(겹침 슬롯) 순서로 훑어 가장 가까운 지형 높이(`54d0`)와 코드(`54d8`)를 고르고 `461ec`로 넘기는 지형 접촉 탐색으로 보인다. `4706c`/`47070`은 객체 사각형을 8칸 슬롯 표(`54e6+2c·k`)에 등록하고, `47134`는 사각형이 겹치는 슬롯 bit를 `567a`에 모은다. 게임 의미는 미확인이다.
2. [I] `7670e`/`76718`은 palette `c53`과 animation `76aa0`으로 시작해 WORD `5418(A5)`가 `78(A6)` 이상이 되면 animation `76aac`와 자식 `76852`로 바뀌고, `86` 타이머·`7a` 횟수로 자식을 다시 만들며 `1ab02` 범위 밖이면 스스로 지우는 연출 객체로 보인다. 게임 의미는 미확인이다.
3. [U] 경계 callee 8개와 자식 callback `76852`는 U09 밖이다. `76852`는 `7679a`/`767c6`이 만든 node가 다음 frame에 실행되면 미연결 callback이 된다.
4. [U] seed 0 1 127~135는 base에서 frame 0 RNG guard로 끝나므로 `7670e`의 설치 callback 이후 자연 기록은 없다(fixture·실제 ROM 차분만).

작업자 scratch: 세션 scratchpad `f4u09/`(`u09.py` block·범위·SHA 계산, `dis_u09.py`, `reach.py`, `refs.py`, `nextins.py`, `probes.py`; 저장소 밖).
