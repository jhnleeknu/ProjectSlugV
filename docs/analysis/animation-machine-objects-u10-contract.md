# 객체 callback F4 U10: `babb4` 생성 callback 계열(`bb188`/`bafe6`/`bb536`과 설치 callback 18개), `d7828`, `dbdb6` 계열 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U10 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`), U07 계약(`animation-machine-objects-u07-contract.md`, SHA256 `734615e139a6e0577154eace301c66a0ea9fb94137e0e6cf921dd15ff1ab99a9`), U09 계약(`animation-machine-objects-u09-contract.md`, SHA256 `ec78145959a74817246f18fef52536792b95e6e3a29d3d253584fe6e1a5b01fa`)을 따른다. U08b 경계는 U08b 계약 초안(`animation-machine-objects-u08b-contract.md`, SHA256 `a75aa7748c9acba9f9f16e97cefbed77308fe429d0103e8683f2f9bdd5c0d7a8`)을 참조했다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee는 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01~U09 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U10에는 없음). `MOVE.x`/`MOVEQ`/`TST`/`CMP`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). `LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`와 callee C를 소비하는 단독 Bcc만인 block은 FLOW_ONLY다. `ADDQ`/`ADDA` An block은 Unknown이다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U10의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료(`2001d8`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u10`(HEAD `80d77e0`, U01~U09 + U08a WIP, `engine/src/animation_machine.cpp` SHA256 `2fb464e380ece27eb67670e0fd38fd52f8d516e4b8f9b23ac83e1a0d72d37012`, routing 규칙 43개)을 참조했다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u10/u10.py`가 원본 opcode에서 독립 계산했고 아래 목록과 같음을 assert했다.

## 요약

- [F] U10은 **block 시작 223개**다. callback 진입 6개(`babb4` `bafe6` `bb188` `bb536` `d7828` `dbdb6`), 함수 진입 1개(`dbe1e`, 외부 `JSR d16(PC)` 호출자 `dbcb4` `dbd20` `dbd8c`와 U10 안 `dbdc6` `dbde6` `dbe06`), `MOVE.L #imm,(A6)` 설치 callback 20개(`bac5c` `bacbe` `bacf2` `baec0` `baf0e` `baf4a` `bb0e4` `bb1f0` `bb2b2` `bb2d2` `bb300` `bb370` `bb3fe` `bb41e` `bb45e` `bb520` `bb546` `dbdc6` `dbde6` `dbe06`; `bacbe`는 `bafb2`가 설치하고 `bac24`/`bac7c`의 BRA 대상이기도 하다)를 포함한다. 코드 6 범위, 2,362바이트, 504명령이며 미해독·TRAP·PC 상대 점프 표·레지스터 간접 점프·묶인 Bcc·SUBX/ADDX는 없다. routing 짝수 PC는 1,181개, 내부 PC는 958개다.
- [F] **범위 문서 152와의 차이(+71)**:
  - −5: `bafe8` `bafea` `baff6` `baffc` `bb000`. 범위 스크립트(`f4scope/build_all.py`)가 Unicorn TB 시작을 함수 진입으로 올린 값이다. ROM 어디에도 이 주소로의 정적 분기·호출·LONG 상수가 없고(`refs.py`·LONG 검색 0건), `bafe6` `MOVEQ` 뒤·`baff0` 블록 안의 명령 경계다(결정 3: block 아님, 내부 PC).
  - +76: 설치 callback과 그 본문. 범위 스크립트의 함수 본문은 `MOVE.L #imm,(A6)` 연속 callback을 따라가지 않았다. U09 계약 결정 1과 같은 관례(설치 callback 진입은 시작)로 센다. 내역: 범위 문서 U11의 `bac5c` 1, R01의 `bb1f0` `dbde6` 2, R02의 `bb2b2` `bb2d2` `bb300` 계열 36, 어느 단위에도 없던(자연 관측 0) `baec0` `baf0e` `baf4a` `bb370` `bb3fe` `bb41e` `bb45e` `bb520` `dbe06` 계열 37.
- [F] **경계 callee(실행부 없음) 7개**: `4be06`(범위 문서 U11) `497b6`(U11, C 반환) `eb774`(U23, C 반환) `4c266`(C 반환) `1aa40` `492c8`(U42) — 범위 문서의 "경계 callee 6"과 같다 — 와 U08b `4be34`(다른 작업 트리 `metalslug-u08b`에서 구현 중, 범위 문서는 U08 전체를 전제). U08b 병합 뒤에는 `4be34`가 실행된다.
- [F] 기존 실행부로 나가는 호출: fade_card `28ae`(자식 생성 3회)·`2a00`(JMP, 자기 삭제), U05 `c6a96`·`1ab02`(C 반환), interpreter `49f8c`·`49fc6`(C 반환), cleanup `46ef4`·`43e34`, U09 `4706c`, stage_event_ops `288c`(C 반환), U08a `49290`, stage_area RNG `49a58`, sound `3af8`.
- [F] 읽는 ROM 자료는 banked window LONG `2001d8`과 그 값 + `k`(k = `4` `c` `10` `18` `54` `58` `5c` `60` `64` `68` `6c`)의 LONG뿐이다(`MOVE.L 2001d8.L,22(A6)` 뒤 `MOVEA.L 22(A6),A1; MOVEA.L k(A1),A1`, 18 block). 둘 다 live bus(`am_read` → `read_program_bus`, live `bank_base`)로 읽는다. fixed ROM 주소 `bcb22`(→`1ab02` A0) `bcb2a`(→`497b6` A1) `bb598` `bb5c0` `bb55a`(→`4706c` A0)는 U10이 읽지 않고 주소만 넘긴다. I/O port 쓰기와 bank 변경은 U10 자체에 없다.
- [F] 자연 seed(F2 프레임 패스, 기준 작업 트리 `80d77e0`의 C++ 차분): 첫 미연결 callback이 `dbdb6`인 seed 13개, `d7828`인 seed 2개다. 기준 일치 pass 10,016개·node 74,976개(142 seed, 불일치 0). 범위 scratch 재생(`f4scope/dyn`)에서 U10 block에 닿는 callback은 `dbdb6`(13 seed) `d7828`(17) `babb4` `bafe6` `bb188` `bb536`(각 13)이고 seed는 0 1 16 17 20 21 40~43 127~135다. [I] `bb188`은 frame 0에서 `bb1d8 JSR 49a58`(RNG)을 부르므로 seed 0 1 127~135는 RNG guard(C++ `stage area RNG pointer outside work RAM`, native `49a80` ROM 쓰기 정지)로 끝난다(범위 문서 "U10의 11 seed는 base에서 frame 0 RNG guard 완주").

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 정정(152→223).** TB 인공 진입 5개를 빼고 설치 callback 경로 76개를 넣는다(권고, U09 결정 1과 같은 관례). 그 결과 범위 문서 U11의 `bac5c`, R01(`bb1f0` `dbde6`)과 R02의 `bafd4..bb532` 부분이 U10에 들어온다. R01은 U10 안에서 끝나고 R02는 `448be..44c76`(코어) 부분만 남는다. 범위 문서는 고치지 않는다.
2. **경계 callee 7개.** `4be06` `497b6` `eb774` `4c266` `1aa40` `492c8`과 U08b `4be34`를 실행부 없는 경계로 둔다(권고). U10 routing은 이 PC들을 포함하지 않으므로 U08b 병합 시 충돌이 없다.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u10.cpp`의 `animation_objects_u10_block`. 오류는 `unsupported animation objects u10 PC`, `objects u10 caller requires known carry`(메인 지시와 같음).
4. **banked 읽기.** [F] 18 block이 `MOVE.L 2001d8.L,22(A6)`로 bank window LONG을 읽고 그 값 + `k`의 LONG을 다시 읽는다(U05 `b96e6`과 같은 모양). 권고: 둘 다 live bus로 읽는다(physical span 밖이면 기존 checked 오류 `reached program bank physical span outside ROM`). [F] 자연 seed의 bank `200000`에서 `2001d8`=`002d4b72`, 표 LONG `4`=`2d4c16` `c`=`2d4c58` `10`=`2d4caa` `18`=`2d4cf2` `54`=`2d4e74` `58`=`2d4efc` `5c`=`2d4f2a` `60`=`2d4f86` `64`=`2d4fa6` `68`=`2d4fd4` `6c`=`2d5026`(bank `300000`이면 `2001d8`=`01000000`, 그 다음 읽기는 bank 밖 주소다).
5. **`CLR.L`/`CLR.W`의 68000 읽기 주기.** 대상이 노드 d16(A6)(`baf36`의 `36` `3a`)과 work RAM `5df8(A5)`(`d7830`)이다. U07·U09처럼 쓰기만 모델한다(권고).
6. **`ASR.L #3`(`bad2a` `bad62`).** 산술 shift를 부호 채움으로 명시 구현한다(C++ 부호 있는 shift에 기대지 않음).
7. **`ADDA.W #6,A0`(`d7842`).** 68000에서 CCR을 바꾸지 않지만 관례("ADDQ/ADDA An Unknown carry")대로 Unknown으로 둔다(권고). 이 block 뒤의 C 소비자는 없다.
8. **무효화 탐침.** [F] `engine/tests`·`tools`·`engine/src`·`docs/analysis`에서 U10 범위 안 PC를 outside 탐침으로 쓰는 곳은 없다(`animation-machine-caller-inventory.md`의 주소 나열과 범위 문서·계약 문서의 서술만). 교체할 탐침이 없다.

## 원본 바이트 근거

[F] 코드 6 범위 합계 2,362바이트. 범위 순서로 이어 붙인 SHA256 `234e49eb91da56611f1ea9b0265561b247593aafb400d36f317a0a061990bd53`.

| CPU 범위 | 바이트 | SHA256 |
| --- | --- | --- |
| `babb4..bb012` | 1118 | `74127f2ad43b68624e4a196245bea8841db884decc2e053a0c2b2edaac530e78` |
| `bb0b6..bb0f4` | 62 | `e02fb9c921ebcfb2e6fd407ab6d4dff990215cd60608cbff4db9a11f8f8257f1` |
| `bb188..bb55a` | 978 | `46094225e89be6b3f4097e7ef8b25d88be2687b4a96f26ce05a1fb5d9dcf2cdf` |
| `d7828..d788c` | 100 | `73bf49849a9ff465fc6c0e92ffd86154d3225b71ded903e7cb44331be4efac1e` |
| `dbdb6..dbe1c` | 102 | `bdefefc4c701f10e15598597a856e47c8c7ffc82e5a7fb2f5d1c09c4b419fca6` |
| `dbe1e..dbe20` | 2 | `1ceeabf0c6a5a30bad12cdac0e3ab015a7188a42e6aebb556aad00bb9cd693ad` |

- [F] 범위 밖 이웃: `bb012..bb0b6`(다른 callback 본문 `bb012`·`bb070`; `bb00e BRA bb0b6`이 건너뜀), `bb0f4..bb188`(다른 본문, `bb184 BRA bafd4`가 공통 꼬리로 들어옴), `bb55a`(WORD 자료 `fff4`, `bb54c`의 A0), `bb598..`(`4706c`에 넘기는 사각형 자료), `d7820..d7828`(다른 함수 꼬리 `MOVE.L #d76a6,(A6); RTS`), `d788c`(다른 함수), `dbdb0`(다른 함수의 `JMP 2a00`), `dbe1c`(도달하지 않는 `RTS`, 정적 디코드에서 어느 경로도 닿지 않음), `dbe20`(다른 함수).
- [F] 자료:
  - banked: CPU LONG `2001d8`과 그 값 + `k`의 LONG(위 결정 4).
  - work RAM `A5`: WORD `5418`(비교만) `5432`(쓰기) `5df8`(CLR). [F] U10은 `A5`를 설정하지 않는다(진입 A5 그대로; 자연 frame pass는 `108000`).
  - 노드 d16(A6): LONG `(A6)`(callback 설치) `36` `3a` `88` `8c` `c`(부모 노드 포인터, `MOVEA.L c(A6),A0`), WORD `1e` `20` `42` `46` `68` `76` `78` `7a` `7c` `7e` `80` `82` `84` `86` `94`, LONG `22`(banked 포인터 보관), BYTE `76` `77` `78`(`d7828`).
  - 부모 노드 d16(A0=`c(A6)`): WORD `36`(`bb1f0` `bb45e`) `3a`(`bb312` `bb382`) `86`(`bb300` `bb370`).
  - `d7828` 대상: `10ddec` 또는 `10ddf2`(BYTE `76(A6)`≠0)의 WORD `0` `2` `4`.
- [F] 스택: JSR 복귀 LONG만 쓴다(MOVEM·PEA·Dn push 없음).

## block 목록과 실행 의미

[F] 223 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `MOVE.B`/`MOVE.W` Dn·`ADDI.W`/`SUBI.W`/`ANDI.W`/`ADD.W`/`SUB.W` Dn은 나머지 bit를 보존하고 `MOVEQ`/`CLR.L`/`EXT.L`/`LSL.L`/`ASR.L`/`NEG.L`은 LONG 전체를 쓴다. `BGE`/`BLT`/`BLE`는 피연산자 크기의 2의 보수 비교(`CMP.W`·`CMPI.W` WORD, `CMP.L` LONG)이고 `SUBQ.W #1` 뒤 `BGE`는 N⊕V=0, 즉 감소 전 부호 WORD가 1 이상이다. 같은 block 안 `CMP`/`CMPI` 뒤 `BCC`/`BCS`는 무부호 비교다(`CMP.W 5418(A5),D0; BCC`는 `D0.W ≥u WORD`). 단독 `BCC`/`BCS` block은 앞 JSR callee가 돌려준 C를 소비한다.

**생성 callback `babb4`와 설치 callback `bac5c` 24**
- `babb4`: `MOVEA.L #bb188,A0; MOVE.W #a,D0; JSR 28ae.L` (callback 진입; fade_card 객체 생성)
- `babc4`: `MOVEA.L #bafe6,A0; MOVE.W #a,D0; JSR 28ae.L` (fade_card 객체 생성)
- `babd4`: `MOVEA.L #bb536,A0; MOVE.W #a,D0; JSR 28ae.L` (fade_card 객체 생성)
- `babe4`: `MOVE.W 76(A6),D0; EXT.L D0; LSL.L #8,D0; MOVE.L D0,88(A6); MOVE.W 7c(A6),D0; EXT.L D0; LSL.L #8,D0; MOVE.L D0,8c(A6); MOVE.W #75,D0; MOVE.W #1,D1; MOVE.B #0,D2; JSR c6a96.L` (U05)
- `bac0e`: `MOVE.W #0,68(A6); MOVE.W #0,1e(A6); CMPI.W #100,5418(A5); BGE.W bac28`
- `bac24`: `BRA.W bacbe`
- `bac28`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 4(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bac50`: `MOVE.W #0,86(A6); MOVE.L #bac5c,(A6)` (→`bac5c`)
- `bac5c`: `JSR 4be06.L` (설치 callback 진입; 경계)
- `bac62`: `LEA.L bcb2a.L,A1; JSR 497b6.L` (경계, C 반환)
- `bac6e`: `BCC.W bac80` (carry 소비: 497b6 반환 C)
- `bac72`: `JSR eb774.L` (경계, C 반환)
- `bac78`: `BCC.W bac80` (carry 소비: eb774 반환 C)
- `bac7c`: `BRA.W bacbe`
- `bac80`: `JSR 49fc6.L` (interpreter, C 반환)
- `bac86`: `LEA.L bcb22.L,A0; JSR 1ab02.L` (U05, C 반환)
- `bac92`: `BCC.W baca2` (carry 소비: 1ab02 반환 C)
- `bac96`: `JSR 46ef4.L` (cleanup)
- `bac9c`: `JMP 2a00.L` (fade_card 자기 삭제)
- `baca2`: `TST.W 7a(A6); BNE.W bacb2`
- `bacaa`: `LEA.L bb598(PC),A0; BRA.W bacb6`
- `bacb2`: `LEA.L bb5c0(PC),A0` (→`bacb6`)
- `bacb6`: `JSR 4706c.L` (U09)
- `bacbc`: `RTS`

**추적 callback `bacbe`/`bacf2` 41**
- `bacbe`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 4(A1),A1; JSR 49f8c.L` (설치 callback 진입; interpreter; banked 읽기 2회)
- `bace6`: `MOVE.W #1,86(A6); MOVE.L #bacf2,(A6)` (→`bacf2`)
- `bacf2`: `MOVE.W 42(A6),D0; MOVE.L 88(A6),D1; MOVE.W 78(A6),D2; CMP.W D2,D0; BNE.W bad10` (설치 callback 진입)
- `bad04`: `MOVE.L #0,36(A6); BRA.W bad2a`
- `bad10`: `ADDI.W #fff0,D2; CMP.W D2,D0; BGE.W bad2a`
- `bad1a`: `CMP.L 36(A6),D1; BLE.W bad2a`
- `bad22`: `ADDI.L #18000,36(A6)` (→`bad2a`)
- `bad2a`: `MOVE.L 36(A6),D3; ASR.L #3,D3; SUB.L D3,36(A6); CMPI.W #1,86(A6); BEQ.W bad92`
- `bad3e`: `MOVE.W 46(A6),D0; MOVE.L 8c(A6),D1; MOVE.W 84(A6),D2; CMP.W D2,D0; BNE.W bad62`
- `bad50`: `MOVE.L #0,3a(A6); MOVE.W #1,86(A6); BRA.W bad6c`
- `bad62`: `MOVE.L 3a(A6),D3; ASR.L #3,D3; SUB.L D3,3a(A6)` (→`bad6c`)
- `bad6c`: `MOVE.W 84(A6),D2; ADDI.W #fff0,D2; CMP.W D2,D0; BGE.W bad7e`
- `bad7a`: `MOVE.L D1,3a(A6)` (→`bad7e`)
- `bad7e`: `MOVE.W 84(A6),D2; ADDI.W #10,D2; CMP.W D2,D0; BLE.W bad92`
- `bad8c`: `NEG.L D1; MOVE.L D1,3a(A6)` (→`bad92`)
- `bad92`: `JSR 4be34.L` (U08b 경계)
- `bad98`: `MOVE.W 7a(A6),D0; BEQ.W badb0`
- `bada0`: `CMP.W 5418(A5),D0; BCC.W badac`
- `bada8`: `BRA.W bae70`
- `badac`: `BRA.W badc6`
- `badb0`: `MOVE.W #70,D0; MOVE.W #20,D1; JSR 4c266.L` (경계, C 반환)
- `badbe`: `BCC.W badc6` (carry 소비: 4c266 반환 C)
- `badc2`: `BRA.W bae70`
- `badc6`: `MOVE.W 80(A6),D0; BEQ.W badee`
- `badce`: `CMP.W 5418(A5),D0; BCC.W badee`
- `badd6`: `MOVE.W #0,80(A6); MOVE.W #4,86(A6); MOVE.W 46(A6),D0; ADD.W 7e(A6),D0; MOVE.W D0,84(A6)` (→`badee`)
- `badee`: `MOVE.W 82(A6),D0; BEQ.W bae16`
- `badf6`: `CMP.W 5418(A5),D0; BCC.W bae16`
- `badfe`: `MOVE.W #0,82(A6); MOVE.W #5,86(A6); MOVE.W 46(A6),D0; SUB.W 7e(A6),D0; MOVE.W D0,84(A6)` (→`bae16`)
- `bae16`: `CMPI.W #1130,5418(A5); BLT.W bae26`
- `bae20`: `MOVE.W #140,78(A6)` (→`bae26`)
- `bae26`: `JSR 49fc6.L` (interpreter, C 반환)
- `bae2c`: `LEA.L bcb22.L,A0; JSR 1ab02.L` (U05, C 반환)
- `bae38`: `BCC.W bae48` (carry 소비: 1ab02 반환 C)
- `bae3c`: `JSR 46ef4.L` (cleanup)
- `bae42`: `JMP 2a00.L` (fade_card 자기 삭제)
- `bae48`: `MOVE.W 46(A6),D0; SUBI.W #140,D0; MOVE.W D0,5432(A5); TST.W 7a(A6); BNE.W bae64`
- `bae5c`: `LEA.L bb598(PC),A0; BRA.W bae68`
- `bae64`: `LEA.L bb5c0(PC),A0` (→`bae68`)
- `bae68`: `JSR 4706c.L` (U09)
- `bae6e`: `RTS`

**`bae70`과 설치 callback `baec0` 19**
- `bae70`: `TST.W 7a(A6); BNE.W bae86`
- `bae78`: `CLR.L D0; CLR.L D1; JSR 1aa40.L` (경계)
- `bae82`: `BRA.W bae8c`
- `bae86`: `MOVE.W #fff0,5432(A5)` (→`bae8c`)
- `bae8c`: `MOVE.W #2,86(A6); LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L c(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `baeba`: `MOVE.L #baec0,(A6)` (→`baec0`)
- `baec0`: `JSR 4be06.L` (설치 callback 진입; 경계)
- `baec6`: `JSR 49fc6.L` (interpreter, C 반환)
- `baecc`: `BCC.W baed6` (carry 소비: 49fc6 반환 C)
- `baed0`: `MOVE.L #baf0e,(A6)` (→`baed6`)
- `baed6`: `LEA.L bcb22.L,A0; JSR 1ab02.L` (U05, C 반환)
- `baee2`: `BCC.W baef2` (carry 소비: 1ab02 반환 C)
- `baee6`: `JSR 46ef4.L` (cleanup)
- `baeec`: `JMP 2a00.L` (fade_card 자기 삭제)
- `baef2`: `TST.W 7a(A6); BNE.W baf02`
- `baefa`: `LEA.L bb598(PC),A0; BRA.W baf06`
- `baf02`: `LEA.L bb5c0(PC),A0` (→`baf06`)
- `baf06`: `JSR 4706c.L` (U09)
- `baf0c`: `RTS`

**설치 callback `baf0e`/`baf4a` 18**
- `baf0e`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 10(A1),A1; JSR 49f8c.L` (설치 callback 진입; interpreter; banked 읽기 2회)
- `baf36`: `MOVE.W 5418(A5),94(A6); CLR.L 36(A6); CLR.L 3a(A6); MOVE.L #baf4a,(A6)` (→`baf4a`)
- `baf4a`: `JSR 4be06.L` (설치 callback 진입; 경계)
- `baf50`: `JSR 49fc6.L` (interpreter, C 반환)
- `baf56`: `BCC.W baf82` (carry 소비: 49fc6 반환 C)
- `baf5a`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 4(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `baf82`: `LEA.L bcb22.L,A0; JSR 1ab02.L` (U05, C 반환)
- `baf8e`: `BCC.W baf9e` (carry 소비: 1ab02 반환 C)
- `baf92`: `JSR 46ef4.L` (cleanup)
- `baf98`: `JMP 2a00.L` (fade_card 자기 삭제)
- `baf9e`: `TST.W 7a(A6); BNE.W bafb8`
- `bafa6`: `MOVE.W 94(A6),D0; CMP.W 5418(A5),D0; BEQ.W bafb8`
- `bafb2`: `MOVE.L #bacbe,(A6)` (→`bafb8`)
- `bafb8`: `TST.W 7a(A6); BNE.W bafc8`
- `bafc0`: `LEA.L bb598(PC),A0; BRA.W bafcc`
- `bafc8`: `LEA.L bb5c0(PC),A0` (→`bafcc`)
- `bafcc`: `JSR 4706c.L` (U09)
- `bafd2`: `RTS`

**공통 꼬리 `bafd4` 4**
- `bafd4`: `JSR 288c.L` (stage_event_ops, C 반환)
- `bafda`: `BCS.W bafe4` (carry 소비: 288c 반환 C)
- `bafde`: `JMP 2a00.L` (fade_card 자기 삭제)
- `bafe4`: `RTS`

**자식 callback `bafe6`/`bb0e4` 8**
- `bafe6`: `MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L` (callback 진입; U08a)
- `baff0`: `MOVE.W #0,68(A6); MOVE.W #0,1e(A6); MOVE.W #75,D0; MOVE.W #6,D1; MOVE.B #0,D2; JSR c6a96.L` (U05)
- `bb00e`: `BRA.W bb0b6`
- `bb0b6`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 18(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bb0de`: `MOVE.L #bb0e4,(A6)` (→`bb0e4`)
- `bb0e4`: `JSR 43e34.L` (설치 callback 진입; cleanup)
- `bb0ea`: `JSR 49fc6.L` (interpreter, C 반환)
- `bb0f0`: `BRA.W bafd4`

**자식 callback `bb188`과 설치 callback `bb1f0` `bb2b2` `bb2d2` `bb300` `bb370` `bb3fe` `bb41e` `bb45e` `bb520` 76**
- `bb188`: `MOVE.W #75,D0; MOVE.W #19,D1; MOVE.B #0,D2; JSR c6a96.L` (callback 진입; U05)
- `bb19a`: `MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L` (U08a)
- `bb1b0`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 64(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bb1d8`: `JSR 49a58.L` (stage_area RNG)
- `bb1de`: `ANDI.W #1f,D0; ADDI.W #5a,D0; MOVE.W D0,94(A6); MOVE.L #bb1f0,(A6)` (→`bb1f0`)
- `bb1f0`: `MOVEA.L c(A6),A0; TST.W 36(A0); BEQ.W bb200` (설치 callback 진입)
- `bb1fc`: `BRA.W bb284`
- `bb200`: `JSR 43e34.L` (cleanup)
- `bb206`: `JSR 492c8.L` (경계)
- `bb20c`: `JSR 49fc6.L` (interpreter, C 반환)
- `bb212`: `BCC.W bb23e` (carry 소비: 49fc6 반환 C)
- `bb216`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 64(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bb23e`: `SUBQ.W #1,94(A6); BGE.W bb280`
- `bb246`: `JSR 49a58.L` (stage_area RNG)
- `bb24c`: `ANDI.W #1f,D0; ADDI.W #5a,D0; MOVE.W D0,94(A6); LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 68(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bb280`: `BRA.W bafd4`
- `bb284`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 6c(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bb2ac`: `MOVE.L #bb2b2,(A6)` (→`bb2b2`)
- `bb2b2`: `JSR 43e34.L` (설치 callback 진입; cleanup)
- `bb2b8`: `JSR 492c8.L` (경계)
- `bb2be`: `JSR 49fc6.L` (interpreter, C 반환)
- `bb2c4`: `BCC.W bb2ce` (carry 소비: 49fc6 반환 C)
- `bb2c8`: `MOVE.L #bb2d2,(A6)` (→`bb2ce`)
- `bb2ce`: `BRA.W bafd4`
- `bb2d2`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 54(A1),A1; JSR 49f8c.L` (설치 callback 진입; interpreter; banked 읽기 2회)
- `bb2fa`: `MOVE.L #bb300,(A6)` (→`bb300`)
- `bb300`: `MOVEA.L c(A6),A0; CMPI.W #2,86(A0); BNE.W bb312` (설치 callback 진입)
- `bb30e`: `BRA.W bb3d0`
- `bb312`: `TST.W 3a(A0); BEQ.W bb31e`
- `bb31a`: `BRA.W bb342`
- `bb31e`: `CMPI.W #1120,5418(A5); BLT.W bb32c`
- `bb328`: `BRA.W bb4f2`
- `bb32c`: `JSR 43e34.L` (cleanup)
- `bb332`: `JSR 492c8.L` (경계)
- `bb338`: `JSR 49fc6.L` (interpreter, C 반환)
- `bb33e`: `BRA.W bafd4`
- `bb342`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 5c(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bb36a`: `MOVE.L #bb370,(A6)` (→`bb370`)
- `bb370`: `MOVEA.L c(A6),A0; CMPI.W #2,86(A0); BNE.W bb382` (설치 callback 진입)
- `bb37e`: `BRA.W bb3d0`
- `bb382`: `TST.W 3a(A0); BNE.W bb38e`
- `bb38a`: `BRA.W bb2d2`
- `bb38e`: `JSR 43e34.L` (cleanup)
- `bb394`: `JSR 492c8.L` (경계)
- `bb39a`: `JSR 49fc6.L` (interpreter, C 반환)
- `bb3a0`: `BCC.W bb3cc` (carry 소비: 49fc6 반환 C)
- `bb3a4`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 5c(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bb3cc`: `BRA.W bafd4`
- `bb3d0`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 60(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bb3f8`: `MOVE.L #bb3fe,(A6)` (→`bb3fe`)
- `bb3fe`: `JSR 43e34.L` (설치 callback 진입; cleanup)
- `bb404`: `JSR 492c8.L` (경계)
- `bb40a`: `JSR 49fc6.L` (interpreter, C 반환)
- `bb410`: `BCC.W bb41a` (carry 소비: 49fc6 반환 C)
- `bb414`: `MOVE.L #bb41e,(A6)` (→`bb41a`)
- `bb41a`: `BRA.W bafd4`
- `bb41e`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 64(A1),A1; JSR 49f8c.L` (설치 callback 진입; interpreter; banked 읽기 2회)
- `bb446`: `JSR 49a58.L` (stage_area RNG)
- `bb44c`: `ANDI.W #1f,D0; ADDI.W #5a,D0; MOVE.W D0,94(A6); MOVE.L #bb45e,(A6)` (→`bb45e`)
- `bb45e`: `MOVEA.L c(A6),A0; TST.W 36(A0); BEQ.W bb46e` (설치 callback 진입)
- `bb46a`: `BRA.W bb284`
- `bb46e`: `JSR 43e34.L` (cleanup)
- `bb474`: `JSR 492c8.L` (경계)
- `bb47a`: `JSR 49fc6.L` (interpreter, C 반환)
- `bb480`: `BCC.W bb4ac` (carry 소비: 49fc6 반환 C)
- `bb484`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 64(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bb4ac`: `SUBQ.W #1,94(A6); BGE.W bb4ee`
- `bb4b4`: `JSR 49a58.L` (stage_area RNG)
- `bb4ba`: `ANDI.W #1f,D0; ADDI.W #5a,D0; MOVE.W D0,94(A6); LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 68(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bb4ee`: `BRA.W bafd4`
- `bb4f2`: `LEA.L 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA.L 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 58(A1),A1; JSR 49f8c.L` (interpreter; banked 읽기 2회)
- `bb51a`: `MOVE.L #bb520,(A6)` (→`bb520`)
- `bb520`: `JSR 43e34.L` (설치 callback 진입; cleanup)
- `bb526`: `JSR 492c8.L` (경계)
- `bb52c`: `JSR 49fc6.L` (interpreter, C 반환)
- `bb532`: `BRA.W bafd4`

**자식 callback `bb536`/`bb546` 5**
- `bb536`: `MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L` (callback 진입; U08a)
- `bb540`: `MOVE.L #bb546,(A6)` (→`bb546`)
- `bb546`: `JSR 43e34.L` (설치 callback 진입; cleanup)
- `bb54c`: `LEA.L bb55a(PC),A0; JSR 4706c.L` (U09)
- `bb556`: `BRA.W bafd4`

**callback `d7828` 11**
- `d7828`: `TST.B 78(A6); BEQ.W d7834` (callback 진입)
- `d7830`: `CLR.W 5df8(A5)` (→`d7834`)
- `d7834`: `LEA.L 10ddec.L,A0; MOVE.B 76(A6),D0; BEQ.W d7846`
- `d7842`: `ADDA.W #6,A0` (→`d7846`)
- `d7846`: `MOVEQ #0,D0; MOVE.B 77(A6),D0; CMPI.W #f,D0; BCS.W d7856`
- `d7854`: `MOVEQ #0,D0` (→`d7856`)
- `d7856`: `MOVE.W D0,(A0); MOVE.W 42(A6),D0; CMPI.W #140,D0; BCS.W d7868`
- `d7864`: `MOVE.W #108,D0` (→`d7868`)
- `d7868`: `MOVE.W D0,2(A0); MOVE.W 46(A6),D0; MOVE.W D0,D1; SUBI.W #100,D1; CMPI.W #100,D1; BCS.W d7882`
- `d787e`: `MOVE.W #1a0,D0` (→`d7882`)
- `d7882`: `MOVE.W D0,4(A0); JMP 2a00.L` (fade_card 자기 삭제)

**callback `dbdb6`/`dbdc6`/`dbde6`/`dbe06`과 `dbe1e` 17**
- `dbdb6`: `MOVE.W #730,D0; JSR 3af8.L` (callback 진입; sound)
- `dbdc0`: `MOVE.L #dbdc6,(A6)` (→`dbdc6`)
- `dbdc6`: `JSR dbe1e(PC)` (설치 callback 진입)
- `dbdca`: `CMPI.W #850,5418(A5); BGE.W dbdd6`
- `dbdd4`: `RTS`
- `dbdd6`: `MOVE.W #742,D0; JSR 3af8.L` (sound)
- `dbde0`: `MOVE.L #dbde6,(A6)` (→`dbde6`)
- `dbde6`: `JSR dbe1e(PC)` (설치 callback 진입)
- `dbdea`: `CMPI.W #a00,5418(A5); BGE.W dbdf6`
- `dbdf4`: `RTS`
- `dbdf6`: `MOVE.W #730,D0; JSR 3af8.L` (sound)
- `dbe00`: `MOVE.L #dbe06,(A6)` (→`dbe06`)
- `dbe06`: `JSR dbe1e(PC)` (설치 callback 진입)
- `dbe0a`: `CMPI.W #1100,5418(A5); BGE.W dbe16`
- `dbe14`: `RTS`
- `dbe16`: `JMP 2a00.L` (fade_card 자기 삭제)
- `dbe1e`: `RTS` (함수 진입, 외부 호출자 dbcb4/dbd20/dbd8c)

(각 묶음 줄의 수는 그 묶음의 block 수다: 24+41+19+18+4+8+76+5+11+17=223.)

공통 helper(18 block의 banked animation 시작): `LEA 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L k(A1),A1; JSR 49f8c.L`. 원본 순서대로 쓰기 `20(A6)` → banked 읽기 → 쓰기 `22(A6)` → 읽기 `22(A6)` → 읽기 `k(A1)` → 복귀 LONG push다. `bae8c`는 앞에 `MOVE.W #2,86(A6)`, `bb24c`/`bb4ba`는 앞에 `ANDI.W #1f,D0; ADDI.W #5a,D0; MOVE.W D0,94(A6)`가 붙는다.

## 구현 범위와 규약

- routing 6 범위: `babb4..bb012`, `bb0b6..bb0f4`, `bb188..bb55a`, `d7828..d788c`, `dbdb6..dbe1c`, `dbe1e..dbe20`. 짝수 PC 1,181개 중 block 시작 223, 내부 958(TB 인공 진입 5개 포함). 내부 PC 직접 진입은 `unsupported animation objects u10 PC`다. 경계 callee 7개와 범위 이웃(`dbe1c` 포함)은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **carry 소비 block 15개**(모두 단독 `BCC`/`BCS`): `1ab02` 반환 C(`bac92` `bae38` `baee2` `baf8e`; U05 `1ab7a` ANDI CCR Clear, U01 `1aafc` ORI CCR Set), `49fc6` 반환 C(`baecc` `baf56` `bb212` `bb2c4` `bb3a0` `bb410` `bb480`; U06 `e7916`과 같은 소비), `288c` 반환 C(`bafda` BCS; F3b `2898` ORI CCR, readiness `289e`), 경계 callee 반환 C(`bac6e`←`497b6`, `bac78`←`eb774`, `badbe`←`4c266`; 경계가 실행되기 전에는 선언 C로만 진입). Unknown이면 `objects u10 caller requires known carry`.
- **known carry 생산 block 0개.** [F] U10 진입의 외부 호출자는 `dbe1e`의 `dbcb4` `dbd20` `dbd8c`(`JSR d16(PC)`)뿐이며 바로 뒤 명령은 `MOVE.L 76(A6),D0`로 C를 읽지 않는다. 나머지 진입은 callback(scheduler `270e` 경로)이다. block 안에서 만들고 소비하는 C(`bada0` `badce` `badf6` `d7846` `d7856` `d7868`)는 그 block 안에서 계산한다.
- **FLOW_ONLY 116개**(C 보존, 소비 15개 포함): `bac24` `bac5c` `bac62` `bac6e` `bac72` `bac78` `bac7c` `bac80` `bac86` `bac92` `bac96` `bac9c` `bacaa` `bacb2` `bacb6` `bacbc` `bad92` `bada8` `badac` `badbe` `badc2` `bae26` `bae2c` `bae38` `bae3c` `bae42` `bae5c` `bae64` `bae68` `bae6e` `bae82` `baec0` `baec6` `baecc` `baed6` `baee2` `baee6` `baeec` `baefa` `baf02` `baf06` `baf0c` `baf4a` `baf50` `baf56` `baf82` `baf8e` `baf92` `baf98` `bafc0` `bafc8` `bafcc` `bafd2` `bafd4` `bafda` `bafde` `bafe4` `bb00e` `bb0e4` `bb0ea` `bb0f0` `bb1d8` `bb1fc` `bb200` `bb206` `bb20c` `bb212` `bb246` `bb280` `bb2b2` `bb2b8` `bb2be` `bb2c4` `bb2ce` `bb30e` `bb31a` `bb328` `bb32c` `bb332` `bb338` `bb33e` `bb37e` `bb38a` `bb38e` `bb394` `bb39a` `bb3a0` `bb3cc` `bb3fe` `bb404` `bb40a` `bb410` `bb41a` `bb446` `bb46a` `bb46e` `bb474` `bb47a` `bb480` `bb4b4` `bb4ee` `bb520` `bb526` `bb52c` `bb532` `bb546` `bb54c` `bb556` `dbdc6` `dbdd4` `dbde6` `dbdf4` `dbe06` `dbe14` `dbe16` `dbe1e`. 그 밖 107개(MOVE/MOVEQ/MOVEA+TST/CLR/TST/CMP/CMPI/ADDI/SUBI/ANDI/ADD/SUB/SUBQ/NEG/EXT/LSL/ASR, `MOVE.L #imm,(A6)`만인 block, ADDA block `d7842`, banked helper block)은 Unknown이다.
- 반환 Z·N: U10 안 소비는 모두 같은 block의 flag 생산 뒤다. RTS를 넘는 flag 소비는 위 15개 C뿐이다.
- 루프: 없다(`bb1f0`/`bb45e`/`bb370`/`bb300` 경로는 callback 재설치로 frame마다 다시 들어온다).
- I/O: port 쓰기는 U10 자체에 없다(callee 몫). bank 변경 없음. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM·bank 읽기는 기존 checked 오류다.

## 의존

- [F] U10 → U08b: `bad92 JSR 4be34`. U10 → U08a: `bafea`(`bafe6` block) `bb1aa`(`bb19a` block) `bb53a`(`bb536` block)의 `JSR 49290`. U10 → U09: `4706c` 5곳(`bacb6` `bae68` `baf06` `bafcc` `bb54c`).
- [F] U10 → 범위 문서 U11: `4be06`(`bac5c` `baec0` `baf4a`), `497b6`(`bac62`). U23: `eb774`(`bac72`). U42: `492c8`(7곳). 그 밖 `4c266`(`badb0`) `1aa40`(`bae78`).
- [F] U10 → U08a `49290`(`MOVEA.L c(A6),A1; LEA 2e(A1),A1; JMP 43e04`)의 대상 `43e04`(`LEA 2e(A6),A0` 뒤 `43e08`)는 cleanup routing 범위(`43dcc..43ea2`) 안이지만 cleanup 실행부에 `43e04` 시작이 없다(`43e08` `43e22` `43e34` `43e38`만). 기준 작업 트리 `80d77e0`과 `5f51050`(U08b 병합) 모두 같다. 그래서 `bafe6` `bb188` `bb536`은 `49290`→`43e04`에서 `unsupported animation machine PC`로 멈춘다. [I] cleanup 실행부의 기존 누락이며 U10 범위 밖이다(기존 실행부 block 안 코드는 다시 routing하지 않는다). 메인 판단이 필요하다.
- [I] U08b를 병합하면 `bacf2` 경로가 `4be34`를 지나 `bad98` 이후까지 실행된다. `bac5c`·`baec0`·`baf4a` 경로는 `4be06`에서, `bb1f0` 계열은 `492c8`에서 멈춘다.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, TB 기준)에서 223 block 중 66개가 도달한다(base). RNG 초기화 + 응답 `80` 변형(`dyn_rng1_resp80_f400`)에서는 103개(`bacf2` `bb0e4` `bb546` `dbdc6` `bb2b2` `bb2d2` `bb300` `bac5c` `bb1f0` `dbde6` callback 추가). 나머지는 fixture로만 덮는다. [F] 첫 미연결 callback(기준 C++ 차분): `dbdb6` 13 seed, `d7828` 2 seed.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 223 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), 소비 block 15개의 Unknown 오류, zero-step, 내부 958 PC 정확한 오류, 홀수 PC. 경계 callee 7개는 그 PC에서 stop이 성공하는 것만 확인하고, rollback·`unsupported animation machine PC` 확인은 F4 단위 밖 미연결 PC(`5f6xx..5ffxx`, 예: `5f712` `5f8a0` `5fe40`, RTS 복귀 LONG `5f712`)로만 한다(메인의 F4 단위 test 경계 관례). 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력과 합성 banked 자료 `2001d8..`; ROM 자료는 test에 넣지 않음)로 비교한다.
- 실제 ROM 차분: 각 callback 진입과 설치 callback 진입, 경계 사이 구간을 실제 program ROM resource(bank `200000`)로 C++와 Unicorn에서 같은 결과로 실행한다(실제 `28ae` `c6a96` `49f8c` `49fc6` `1ab02` `46ef4` `2a00` `4706c` `288c` `49290` `43e34` `49a58` `3af8`).
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`, seed 58·59는 `animation_machine_pvc_banks_native`): 기준(작업 트리 `80d77e0`) 일치 pass 10,016개·node 74,976개가 모두 그대로 일치해야 한다. 새 일치 pass·완주 seed와 첫 미연결 callback 분포를 보고한다.

## 미확인·범위 밖

1. [I] `babb4`는 자식 `bb188` `bafe6` `bb536`을 만들고 `76`/`7c(A6)`를 `88`/`8c`(×256)에 둔 뒤 palette `75`를 잡는다. WORD `5418(A5)`가 `100` 이상이면 `bac5c` 경로(`4be06`·`497b6`/`eb774` 판정), 아니면 `bacbe`/`bacf2`로 위치(`42`/`46`)를 목표 `78`/`84`로 끌고 가는 감쇠 속도(`36`/`3a`, `ASR.L #3`)를 갱신하는 이동 객체로 보인다. `5418`은 스크롤 위치로 보이나 게임 의미는 미확인이다.
2. [I] `bb188` 계열은 RNG(`49a58`)로 `94(A6)` 대기(`5a..79`)를 정하고 부모(`c(A6)`)의 `36`/`3a`/`86`에 따라 banked animation `54`~`6c`를 고르는 부속 객체로 보인다. 게임 의미는 미확인이다.
3. [I] `d7828`은 `10ddec`/`10ddf2`의 WORD 3개(코드, X, Y를 범위 clamp)를 쓰고 스스로 지운다. `dbdb6`은 `5418` 문턱(`850` `a00` `1100`)마다 sound `730`/`742`를 내는 연출 callback으로 보인다. 게임 의미는 미확인이다.
4. [U] 경계 callee 7개와 그 C 반환 의미는 U10 밖이다.
5. [U] seed 0 1 127~135는 base에서 frame 0 RNG guard로 끝나므로 `bb1f0` 이후 자연 기록은 RNG 초기화 변형(결정 1, 별도 관측)에만 있다.

작업자 scratch: 세션 scratchpad `f4u10/`(`u10.py` block·범위·SHA 계산, `classify.py` carry 분류, `doclist.py` 목록, `dis_u10.py`, `reach.py`, `refs.py`, `nextins.py`; 저장소 밖).
