# 객체 callback F4 U13: `7090a` 분기 dispatcher(`70932`), `b8122`/`b816e`/`b83e6` 객체 계열, `ea5f0` 자식 생성, `f1a4e` 지연 삭제 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U13 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`, `4b54e` 반환 C), U11 계약(`animation-machine-objects-u11-contract.md`, SHA256 `ab51cd6d422c9a97fc9a705b4d11254716b69bebd4610a93c0cd58c656940d7d`), U12 계약(`animation-machine-objects-u12-contract.md`, SHA256 `61bd4657f2dab1b48ebd337e1a2000054911f233a458f3bb0f321e7846eac32d`, `1abda` 반환 C와 FLOW_ONLY 정의)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee와 범위 밖에 설치되는 callback은 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01~U12 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U13에는 없음). `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc, Z만 바꾸는 `BTST`/`BSET`/`BCLR`)만인 block과 callee C를 소비하는 단독 Bcc는 FLOW_ONLY다. `ADDQ`/`SUBQ`/`ADDA` An block은 Unknown이다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U13의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료(`200084`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u13`(HEAD `7343cf7` = U01~U11 + U08a/U08b + cleanup `43e04` WIP, `engine/src/animation_machine.cpp` SHA256 `fbe1427e790694fa27b46d15ef9f05b8ce53e1505955b75f929f26a1f02a6f37`, routing 규칙 46개)을 참조했다. U12(작업 트리 `metalslug-u12`, 계약 위 SHA)는 이 작업 트리에 없으므로 U12 소유 PC(`70418` `4c0ac` `490ba` `1abda`)는 경계로 둔다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u13/u13.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] U13은 **block 시작 76개**다. 범위 문서 U13 행의 76과 같다(범위 문서 `units.pkl`의 함수 9개 `7090a` `b80da` `b8122` `b813c` `b816e` `b83e6` `ea5f0` `f1a4e` `f1a5a`와 공유 꼬리 `b80c4`의 본문).
  - `7090a` 2 + 공유 dispatcher `70932` 34(`70932..70a6c`, `7086a` 계열 11개 진입이 `BRA 70932`로 함께 쓴다).
  - 객체 계열 29: 공유 꼬리 `b80c4` 4, `b80da` 6, callback `b8122` 2(`b8122` `b8132`), `b8138`, 설치 callback `b813c` 2, 설치 callback `b816e` 9, 설치 callback `b83e6` 5.
  - `ea5f0` 6(공유 꼬리 `ea60c` `ea61e` 포함), `f1a4e` 1 + 설치 callback `f1a5a` 4.
  - 코드 8 범위, 690바이트, 156명령이다. 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx는 없다. routing 짝수 PC는 345개, 내부 PC는 269개다.
- [F] **경계 callee(실행부 없음) 4개, 모두 U12 소유**: `70418`(`7090a JSR`), `4c0ac`(`b8132 JSR`), `490ba`(`b8110 JSR`), `1abda`(`ea5f0 JSR`, C 반환). U12 병합 전에는 이 PC에서 멈춘다(아래 결정 2).
- [F] **범위 밖 설치 callback(쓰기만 함)**: `70c0c` `71032` `71c90` `72040` `7241a` `725d4` `72714` `7277a` `727e0` `72846` `728ac` `72912` `72a18`(`70932` dispatcher), `b81be` `b8232`(`b816e`), `b8400`(`b83e6`). U13은 `MOVE.L #imm,(A6)`로 node callback LONG만 쓴다. 다음 frame에 scheduler가 부르면 실행부 없는 경계다.
- [F] 기존 실행부로 나가는 호출: U05 `1ab02`(C 반환)·`c6a96`, fade_card `28ae`(자식 생성 2곳)·`2a00`(JMP 2곳), U09 `47070`, interpreter `49f8c`·`49fc6`(C 반환), U01 `4b54e`(C 반환), U11 `4be06`. U13 안 호출: `b8138 JSR b80da(PC)`.
- [F] **flag**: known carry 생산 block 0개, 블록 경계를 건너는 C 소비 block 4개(`b80ce`←`1ab02`, `b819c`←`4b54e`, `b83f2`←`49fc6`, `ea5f6`←`1abda` 경계). block 안에서 만들고 쓰는 C: `f1a5a`(`SUBQ.W #1` 뒤 `BCS`).
- [F] 읽는 자료: banked window LONG `200084`와 그 값 +`16c`의 LONG(`b813c`), fixed ROM LONG 표 `b80ac+4·79(A6)`(`b8174`). 주소만 넘기는 fixed ROM `b7fd4`(→`1ab02` A0), `c84c2`(→`490ba` A0), 자식 callback 상수 `ea7f4` `4841a`. I/O port 쓰기와 bank 변경은 U13 자체에 없다.
- [F] 자연 도달(F4 범위 scratch 재생, TB 기준): base(`f4scope/dyn`) 27 block, RNG 초기화+응답 `80` 변형(`dyn_rng1_resp80_f400`) 49 block. 범위 안 TB 시작은 모두 정적 시작이다(TB 인공 진입 0).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 76(범위 문서와 같음).** 범위 밖 설치 callback(`b81be` `b8232` `b8400`, dispatcher가 설치하는 `70c0c` 등 13개)은 넣지 않는다. [F] 이들은 base·RNG 초기화+`80` 재개 400 frame 어느 변형에서도 실행되지 않았다. 같은 함수의 다른 진입(`708f6` `7091e` `b812c` `ea5d0` `ea5e0` `ea600`)도 범위 밖이다(다른 단위; 범위 문서 U14 `7086a..70a64`, U18 `ea5e0..eaa54`). 권고: 그대로 둔다.
2. **U12 경계 4개(`70418` `4c0ac` `490ba` `1abda`).** U12 병합 전 U13만으로는 자연 seed 26 27 76 77 98 99 104 105가 `70418`/`4c0ac`에서 멈추므로 새 완주 seed를 기대하지 않는다. F4 test 경계 관례에 따라 test는 이 PC의 stop만 확인하고 rollback은 `5f6xx..5ffxx`로만 확인한다. 권고: U12 병합 뒤 frame pass 차분을 다시 잰다.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u13.cpp`의 `animation_objects_u13_block`. 오류는 `unsupported animation objects u13 PC`(내부 PC), `objects u13 caller requires known carry`(소비 4 block). 메인 지시와 같다.
4. **C 소비 4 block.**
   - `b80ce BCC b80d8`: U05 `1ab02` 반환 C(`1ab7a` ANDI CCR Clear, U01 `1aafc` ORI CCR Set). U11 `be892`와 같다.
   - `b819c BCC b81aa`: U01 `4b54e` 반환 C(U01 결정 2: `4b6be` Clear, `4b6ca` ORI Set).
   - `b83f2 BCC b83fc`: interpreter `49fc6` 반환 C(U10 `baecc` 등과 같다).
   - `ea5f6 BCC ea624`: U12 `1abda` 반환 C(U12 결정 5: `1abda`가 `CMPI.W #ffff,D1`의 정확한 C를 만들고 `1abec`는 ANDI Clear). 이 작업 트리에서는 `1abda`가 경계이므로 선언 C로만 진입한다.
   - Unknown이면 `objects u13 caller requires known carry`(state 보존).
5. **공유 꼬리 routing.** `70932`(정적 `BRA.W 70932` 11곳: `70670` `7087a` `7088e` `708a2` `708b6` `708ca` `708de` `708f2` `70906` `7091a` `7092e`), `b80c4`(`BRA.W` 8곳: U13 `b81ba` `b83fc`와 범위 밖 `b822e` `b82ca` `b8320` `b8394` `b85b0` `b8626`), `ea60c`(`BRA.W` 3곳: `ea5dc` `ea5ec` `ea5fc`)는 U13이 routing한다. 다른 단위가 나중에 그 진입을 routing하면 이 block을 그대로 쓴다. 권고: 그대로 둔다.
6. **bank 자료.** `b813c`의 `MOVE.L 200084.L,22(A6)`과 `MOVEA.L 22(A6),A1; MOVEA.L 16c(A1),A1`은 live bus로 읽는다(bank window 값은 bank base가 정한다. 그 밖은 기존 checked 오류). test에는 합성 bank 바이트를 쓴다(ROM 자료를 test에 넣지 않음).
7. **무효화 탐침.** [F] `engine/tests`·`tools`·`engine/src`·`docs/analysis`에서 U13 범위 안 PC를 rollback·outside 탐침으로 쓰는 곳은 없다(`probes.py` 결과: `docs/analysis/animation-machine-caller-inventory.md` 226행의 caller 나열 `0b8190`뿐, 탐침 아님). U12 test(`metalslug-u12`)는 `ea5f0`을 stop 확인으로만 쓴다(rollback 없음). 교체 탐침(`5fc00` 이후)은 필요 없다.

## 원본 바이트 근거

[F] 코드 8 범위 합계 690바이트. 범위 순서로 이어 붙인 SHA256 `bb0cf08aecf3ca96b5634ba146f5d8681aa5fab0c0b18d891f0f087f70ac98eb`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `7090a..7091e` | 20 | `fbdb788f73ae8210fa4891dc69cbf4e3f0799e7ed8bc7d8eee2948ce86077c40` | callback `7090a` |
| `70932..70a6c` | 314 | `7c760640b12dc2e46c52f22d7a9ec043e4f0f12ce3b6e51e7b7929f1abf04a26` | 공유 dispatcher `70932` |
| `b80c4..b812c` | 104 | `3b64b7bd2312ef69fcb7a15309b1e840e65c553c828b99822969deb4e7bc86c9` | 공유 꼬리 `b80c4`, `b80da`, callback `b8122` |
| `b8132..b81be` | 140 | `7bcb5fd28294dae939056b340c0b79f16b54486867d7d228e2a101726977afa5` | `b8132`, 설치 callback `b813c` `b816e` |
| `b83e6..b8400` | 26 | `0947c1faea4a2059fdeac598ef49f51923b6b7f614f8cb24e90bb1c16d74359d` | 설치 callback `b83e6` |
| `ea5f0..ea600` | 16 | `989144eb41057bc94be1fe90eed3c0ba6eb5c24ba692c6f895f8229da16b9e6a` | `ea5f0` |
| `ea60c..ea626` | 26 | `257fb64a4a745c0a49f406c867a1488aa50dbe6917637729c390102294ae78c0` | 공유 꼬리 `ea60c` |
| `f1a4e..f1a7a` | 44 | `96df55bd5b076d072fff851d77bbca219edcc68b7b89fcaa8cd9814399ac17a8` | callback `f1a4e`, 설치 callback `f1a5a` |

- [F] 범위 밖 이웃(routing 밖): `708f6..7090a`·`7091e..70932`(같은 dispatcher를 쓰는 다른 진입), `70a6c`(다른 함수), `b80ac..b80c4`(LONG 자료 6개), `b812c..b8132`(다른 진입 `b812c`: `MOVE.B #1,79(A6)`), `b81be..b83e6`(범위 밖 설치 callback `b81be` `b8232` `b827a` `b82ce` `b82d4` `b8324` `b8352` `b8398`), `b8400..`(설치 callback `b8400` `b8412`, 함수 `b8424`), `ea5d0..ea5f0`·`ea600..ea60c`(다른 진입), `ea626`(다른 함수), `f1a7a`(`JMP` 뒤 도달 불가 `RTS`), `f1a7c..`(자료).
- [F] 자료(모두 live bus):
  - banked window: `b813c`의 LONG `200084`(→ `22(A6)`)와 LONG `(22(A6))+16c`(→ A1, `49f8c`에 넘김). [F] bank `200000`에서 LONG `200084`=`00295974`, 그 +`16c` LONG=`002961e6`. bank `300000`이면 `00256ad4`/`fbee8a60`, bank `400000`이면 `002b27ee`/`002b4132`.
  - fixed ROM: LONG 표 `b80ac+4·79(A6)`(`b8174`, → `47070` A0). [F] 표 값 `b80ac` `000b7fdc 000b8044`(이어서 `b80b4` `000b8002 000b806a`, `b80bc` `000b8028 000b8090`는 범위 밖 설치 callback이 쓰는 표). [I] `79(A6)`은 `b8122`(0)·`b812c`(1)가 넣는 0/1이다(그 밖 값은 원본 그대로 live bus가 정한다).
  - 노드 d16(A6): WORD `7e` `76`(읽기, `f1a5a`는 감소 쓰기) `32`(ADDI 읽기·쓰기), BYTE `6e` `79`(읽기), BYTE `15`(BSET/BCLR bit 0, BTST bit 7) `61`(BTST bit 7), 쓰기 WORD `9c` `68` `1e` `54` `20` `76`, BYTE `87` `79` `5e`, LONG `22` `(A6)`(callback 설치).
  - 자식 node d16(A0, `28ae` 반환): WORD `76`(`ea61e`).
- [F] 스택: JSR/BSR 복귀 LONG과 `ea60c MOVE.W D2,-(A7)`/`ea61e MOVE.W (A7)+,76(A0)`(WORD push/pop, `28ae` 호출을 감쌈).

## block 목록과 실행 의미

[F] 76 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)·`(An,Dn.W)`는 부호확장한다. `.B`·`.W` 연산은 나머지 bit를 보존하고 `MOVEQ`는 LONG 전체를 쓴다. `CMPI`/`TST` 뒤 `BNE`/`BEQ`는 Z, `BMI`는 N, `SUBQ` 뒤 `BCS`는 borrow다.

**`7090a` 2 + dispatcher `70932` 34**
- `7090a`: `MOVE.W #1,9c(A6); JSR 70418(PC)` (callback 진입; 경계 U12)
- `70914`: `MOVE.B #10,87(A6); BRA.W 70932`
- `70932`: `MOVE.W 7e(A6),D0; CMPI.W #2,D0; BNE.W 70946`
- `7093e`: `MOVE.L #72040,(A6); RTS`
- `70946`: `CMPI.W #c,D0; BNE.W 7095c`
- `7094e`: `BCLR.B #0,15(A6); MOVE.L #72a18,(A6); RTS`
- `7095c`: `CMPI.W #d,D0; BNE.W 70972`
- `70964`: `BSET.B #0,15(A6); MOVE.L #72a18,(A6); RTS`
- `70972`: `CMPI.W #e,D0; BEQ.B 70980`
- `70978`: `CMPI.W #f,D0; BNE.W 709a8`
- `70980`: `TST.W D0; BMI.W 709a6`
- `70986`: `ADDI.W #18,32(A6); CMPI.W #e,7e(A6); BNE.W 709a0`
- `70996`: `MOVE.L #7241a,(A6); BRA.W 709a6`
- `709a0`: `MOVE.L #725d4,(A6)` (→`709a6`)
- `709a6`: `RTS`
- `709a8`/`709b0`, `709b8`/`709c0`, `709c8`/`709d0`, `709d8`/`709e0`: `CMPI.W #k,D0; BNE.W 다음` / `MOVE.L #t,(A6); RTS` (k=3 `72714`, 4 `7277a`, 5 `727e0`, 6 `72846`)
- `709e8`/`709f0`, `709fe`/`70a06`: `CMPI.W #k,D0; BNE.W 다음` / `BSET.B #0,15(A6); MOVE.L #t,(A6); RTS` (k=8 `728ac`, 9 `72912`)
- `70a14`/`70a1c`, `70a2a`/`70a32`: `CMPI.W #k,D0; BNE.W 다음` / `BCLR.B #0,15(A6); MOVE.L #t,(A6); RTS` (k=a `728ac`, b `72912`)
- `70a40`: `BTST.B #7,15(A6); BNE.W 70a52`
- `70a4a`: `MOVE.L #71c90,(A6); RTS`
- `70a52`: `CMPI.B #3,6e(A6); BNE.W 70a64`
- `70a5c`: `MOVE.L #70c0c,(A6); RTS`
- `70a64`: `MOVE.L #71032,(A6); RTS`

**객체 계열 `b80c4`/`b80da`/`b8122`/`b813c`/`b816e`/`b83e6` 29**
- `b80c4`: `LEA b7fd4(PC),A0; JSR 1ab02.L` (U05, C 반환)
- `b80ce`: `BCC.W b80d8` (carry 소비: `1ab02` 반환 C)
- `b80d2`: `JMP 2a00.L` (fade_card 자기 삭제)
- `b80d8`: `RTS`
- `b80da`: `MOVE.W #20,D0; MOVE.W #5b,D1; MOVE.B #0,D2; JSR c6a96.L` (U05)
- `b80ec`: `TST.W 76(A6); BNE.W b8104`
- `b80f4`: `MOVE.W #8838,68(A6); MOVE.W #8838,1e(A6); BRA.W b8110`
- `b8104`: `MOVE.W #fff2,68(A6); MOVE.W #fff2,1e(A6)` (→`b8110`)
- `b8110`: `LEA c84c2.L,A0; JSR 490ba.L` (경계 U12)
- `b811c`: `MOVE.W D0,54(A6); RTS`
- `b8122`: `MOVE.B #0,79(A6); BRA.W b8132` (callback 진입)
- `b8132`: `JSR 4c0ac.L` (경계 U12)
- `b8138`: `JSR b80da(PC)`
- `b813c`: `LEA 26(A6),A0; MOVE.W #c2,20(A6); MOVE.L 200084.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 16c(A1),A1; JSR 49f8c.L` (bank 자료; interpreter)
- `b8164`: `CLR.B 5e(A6); MOVE.L #b816e,(A6)` (→`b816e`)
- `b816e`: `JSR 4be06.L` (설치 callback 진입; U11)
- `b8174`: `LEA b80ac(PC),A0; MOVEQ #0,D0; MOVE.B 79(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A0,D0.W),A0; MOVEQ #0,D0; MOVEQ #0,D1; JSR 47070.L` (U09)
- `b8190`: `JSR 49fc6.L`
- `b8196`: `JSR 4b54e.L` (U01, C 반환)
- `b819c`: `BCC.W b81aa` (carry 소비: `4b54e` 반환 C)
- `b81a0`: `CLR.B 5e(A6); MOVE.L #b81be,(A6)` (→`b81aa`)
- `b81aa`: `BTST.B #7,61(A6); BEQ.W b81ba`
- `b81b4`: `MOVE.L #b8232,(A6)` (→`b81ba`)
- `b81ba`: `BRA.W b80c4`
- `b83e6`: `JSR 4be06.L` (설치 callback 진입)
- `b83ec`: `JSR 49fc6.L` (interpreter, C 반환)
- `b83f2`: `BCC.W b83fc` (carry 소비: `49fc6` 반환 C)
- `b83f6`: `MOVE.L #b8400,(A6)` (→`b83fc`)
- `b83fc`: `BRA.W b80c4`

**`ea5f0` 6**
- `ea5f0`: `JSR 1abda.L` (경계 U12, C 반환)
- `ea5f6`: `BCC.W ea624` (carry 소비: `1abda` 반환 C)
- `ea5fa`: `MOVEQ #2,D2; BRA.W ea60c`
- `ea60c`: `MOVE.W D2,-(A7); MOVEA.L #ea7f4,A0; MOVE.W #1e,D0; JSR 28ae.L` (fade_card 자식 생성)
- `ea61e`: `MOVE.W (A7)+,76(A0); RTS`
- `ea624`: `RTS`

**`f1a4e` 1 + `f1a5a` 4**
- `f1a4e`: `MOVE.W #294,76(A6); MOVE.L #f1a5a,(A6)` (callback 진입, →`f1a5a`)
- `f1a5a`: `SUBQ.W #1,76(A6); BCS.W f1a64` (설치 callback 진입; borrow = 감소 전 WORD가 0)
- `f1a62`: `RTS`
- `f1a64`: `MOVEA.L #4841a,A0; MOVE.W #a,D0; JSR 28ae.L` (fade_card 자식 생성)
- `f1a74`: `JMP 2a00.L` (fade_card 자기 삭제)

(수: `7090a` 2 + `70932` 34 = 36, 객체 계열 29, `ea5f0` 6, `f1a4e` 5; 합 76.)

## 구현 범위와 규약

- routing 8 범위: `7090a..7091e`, `70932..70a6c`, `b80c4..b812c`, `b8132..b81be`, `b83e6..b8400`, `ea5f0..ea600`, `ea60c..ea626`, `f1a4e..f1a7a`. 짝수 PC 345개 중 block 시작 76, 내부 269. 내부 PC 직접 진입은 `unsupported animation objects u13 PC`다. 경계 callee 4개, 범위 밖 설치 callback과 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **carry 소비 block 4개**(FLOW_ONLY): `b80ce` `b819c` `b83f2` `ea5f6`. Unknown이면 `objects u13 caller requires known carry`.
- **known carry 생산 block 0개.** [F] U13 함수의 호출자 바로 뒤 명령은 C를 읽지 않는다(`nextins.py`: `ea5f0` 8곳 → `MOVEA` `LEA` `CLR.B` `RTS`×3 `TST.W`×2, `b80da` 1곳 → `LEA`). `7090a` `b8122` `f1a4e`와 설치 callback은 scheduler가 부른다.
- **FLOW_ONLY 24개**(C 보존, 소비 4개 포함): `b80c4` `b8110`(LEA+JSR), `b8132` `b8138` `b816e` `b8190` `b8196` `b83e6` `b83ec` `ea5f0`(JSR), `b80ce` `b819c` `b83f2` `ea5f6`(소비 Bcc), `b80d2` `f1a74`(JMP), `b81ba` `b83fc`(BRA), `b80d8` `709a6` `ea624` `f1a62`(RTS), `70a40` `b81aa`(BTST+Bcc, Z만). 그 밖 52개(MOVE/MOVEQ/MOVEA+MOVE/CLR/TST/CMPI/ADDI/ADD/SUBQ/BSET·BCLR+MOVE.L, `MOVE.L #imm,(A6)` block, `MOVE.W -(A7)`/`(A7)+` block)는 Unknown이다.
- block 안 flag: `70932`..`70a52`의 `CMPI`/`TST`/`BTST` 뒤 `BNE`/`BEQ`/`BMI`, `b80ec`(`TST.W` 뒤 `BNE`), `f1a5a`(`SUBQ.W` 뒤 `BCS`)는 같은 block 안에서 만들고 쓴다. RTS를 넘는 flag 소비는 없다.
- 루프 없음. I/O port 쓰기 없음. bank 변경 없음. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM 읽기, physical span 밖 bank 읽기는 기존 checked 오류다.

## 의존·경계

- [F] U13 → 기존: U05 `1ab02`(`b80c4`) `c6a96`(`b80da`), fade_card `28ae`(`ea60c` `f1a64`) `2a00`(`b80d2` `f1a74`), U09 `47070`(`b8174`), interpreter `49f8c`(`b813c`) `49fc6`(`b8190` `b83ec`), U01 `4b54e`(`b8196`), U11 `4be06`(`b816e` `b83e6`).
- [F] U13 → U12(경계): `70418`(`7090a`), `4c0ac`(`b8132`), `490ba`(`b8110`), `1abda`(`ea5f0`).
- [F] 기존·U12 → U13: U12 `70418 JSR ea5f0.L`(U12 계약의 "경계(U13)"). 그 밖 `JSR ea5f0.L` 7곳(`1d328` `7370c` `75364` `7909e` `7b112` `824de` `83b86`)과 `70932`·`b80c4`·`ea60c`로 가는 범위 밖 `BRA`는 다른 단위다.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, TB 기준)에서 U13 block에 닿는 callback과 seed:
- `7090a`: seed 18 19 26 27 76 77 96 97 98 99 102 103 104 105(base는 `7090a` TB만; RNG+`80` 변형에서 `70914`..`70a64` 21 block).
- `b8122`(→`b80da` `b813c` `b816e`·`b80c4`): base seed 76 77 98 99 104 105, RNG+`80` 변형 62 63 76 77 98 99 104 105.
- `ea5f0`: `7090a`/`7086a`/`b6338`/`736d2` 계열에서 seed 18 19 26 27 38 39 42 43 62 63 76 77 96~99 102~105. `ea60c` `ea61e`는 `ea5e0`(U18) 경로의 seed 8 9 68~71.
- `f1a4e`·`f1a5a`·`f1a62`: seed 98 99 104 105.
- 76 block 중 TB 기준 base 27개, RNG+`80` 변형 49개가 자연 도달한다. RNG+`80` 변형의 미도달 27개(`7093e` `70980` `70986` `70996` `709a0` `709a6` `709b0` `709c0` `709d0` `709e0` `709f0` `70a06` `70a1c` `70a32` `70a5c` `b80d2` `b8104` `b81a0` `b81b4` `b83e6` `b83ec` `b83f2` `b83f6` `b83fc` `ea5fa` `f1a64` `f1a74`)는 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] 기준 C++ 차분(작업 트리 `7343cf7`, F2 프레임 패스 142 seed): 일치 pass 10,496개·node 79,586개, 불일치 0, 자연 완주 77 seed. 첫 미연결 callback `7090a` 2(seed 26 27), `b8122` 2(76 77), `f1a4e` 4(98 99 104 105). RNG 초기화 400 frame 차분: 일치 pass 23,600개·node 158,178개, 불일치 0, complete 59.
- [I] U13만 병합하면 위 8 seed는 `70418`/`4c0ac`(U12 경계)에서 멈춘다. 범위 문서의 "새 자연 seed 26 27 76 77 98 99 104 105"는 U12와 함께 병합될 때 나타날 것이다(검증 기록에서 U12+U13 scratch 조합으로 확인).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 76 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), 소비 4 block의 Unknown 오류, zero-step, 내부 269 PC 정확한 오류, 홀수 PC, U12 경계 4개 stop(rollback 없음), rollback 탐침은 `5f6xx..5ffxx`만. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력과 합성 bank 바이트; ROM 자료는 test에 넣지 않음)로 비교한다.
- 실제 ROM 차분: dispatcher `70932`의 모든 `7e(A6)` 분기(2, c, d, e, f, 3~6, 8~b, 그 밖×`15(A6)` bit 7×`6e(A6)`), `b8122`/`b813c`/`b816e`/`b83e6`(실제 `1ab02` `c6a96` `49f8c` `4be06` `47070` `49fc6` `4b54e` `28ae`/`2a00`, bank `200000`), `ea5f0`(선언 C), `f1a4e`/`f1a5a`(`76(A6)`=0/1/n)을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`, seed 58·59는 `animation_machine_pvc_banks_native`): 기준 일치 pass 10,496개·node 79,586개 유지, 불일치 0. RNG 초기화 400 frame 차분: 기준 23,600 pass·158,178 node 유지, 불일치 0.

## 미확인·범위 밖

1. [I] `70932`는 `7e(A6)`(객체 종류)에 따라 다음 frame callback을 고르는 dispatcher다. `15(A6)` bit 0은 좌우 방향, `87(A6)`은 진입마다 다른 BYTE 상수(`7090a`=`10`)다. 게임 의미는 미확인이다.
2. [I] `b8122`는 `79(A6)`(0/1)을 고른 뒤 palette(`c6a96`)·animation(`49f8c`, bank 표 `16c`)을 설정하고 `b816e`에서 매 frame 이동(`4be06`)·지형 사각형 등록(`47070`, ROM record `b7fdc`/`b8044`)·animation 진행(`49fc6`)·접촉(`4b54e`)을 하는 장치 객체로 보인다. `61(A6)` bit 7은 외부 신호로 보인다.
3. [I] `ea5f0`은 `1abda`(U12, 화면 범위 판정으로 보임)가 C Set을 돌려주면 자식 `ea7f4`(`76`=2)를 만든다. `f1a4e`는 `294`(660) frame 뒤 자식 `4841a`를 만들고 스스로 지운다.
4. [U] U12 경계 4개의 실행 결과, 범위 밖 설치 callback(`b81be` `b8232` `b8400`, dispatcher가 설치하는 13개)의 본문은 U13 밖이다.

작업자 scratch: 세션 scratchpad `f4u13/`(`u13.py` block·범위·SHA 계산, `scope.py` `trav.py` `hroute_u13.py` `dis_u13.py`, `refs.py` `nextins.py` `probes.py`; 저장소 밖).
