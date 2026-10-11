# 객체 callback F4 U05: C2 `1ab02`·node callback `b96c8`/`b971a`·C1 `c6a96`/`c6bf6` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U05 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee·callback은 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다. `MOVE.x`는 C를 지운다(필요한 소비자가 있을 때만 known 생산으로 둔다). `ADDQ`/`ADDA` An block은 Unknown이다. checked 오류는 경계에서 낸다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U05의 코드와 fixed 자료는 `<100000`에 있으므로 CPU 주소와 file offset이 같다. banked window 자료(`2001d0`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u05`(HEAD `4de76a9`, U01+U02+U03 WIP, `engine/src/animation_machine.cpp` SHA256 `6f2fc6e439bc0763af9885c7618222ce6bef97fed5a8db3d1c9525e05c0eb65c`)을 참조했다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u05/u05.py`가 원본 opcode에서 독립 계산했고 아래 목록과 같음을 assert했다.

## 요약

- [F] U05는 함수 4개(`1ab02`, `b96c8`(+설치 callback `b971a`), `c6a96`, `c6bf6`)의 **block 시작 71개**다. 코드 3 범위, 674바이트, 169명령이며 미해독·TRAP·PC 상대 점프 표는 없다. routing 짝수 PC는 337개, 내부 PC는 266개(묶인 PC `1ab20` `1ab5c` 포함)다.
- [F] **범위 문서 73과의 차이(−2)**: `1ab20 BMI`·`1ab5c BMI`는 앞 `BEQ`의 fall-through이며 같은 `CMP.L`의 N을 소비한다. 앞 block(`1ab14`·`1ab50`)에 묶는다(U01 `1aa9c`/`1aad8`과 같은 선택 A). 범위 문서의 `1aafc`는 U01 block이며(범위 표의 "범위" 열이 함수 본문 군집을 보여 줄 뿐) 새 block으로 세지 않았다. 범위 스크립트 본문 집합(`f4scope/plan.py`의 `body`)은 `1ab02` 16(−`1aafc` −2 묶음 = 13), `b96c8` 12 + `b971a` 1, `c6a96` 39, `c6bf6` 6이다.
- [F] 경계(실행부 없음): callee `497a6`(`c6ad0` `c6b1a` `c6b74 JSR`; 범위 문서 "경계 callee 1"), 설치 callback `b975e`(`b9736`)와 `b97c0`(`b9740`).
- [F] 기존 실행부로 나가는 출구: U01 `1aafc`(Set 생산 `ORI.B #1,CCR; RTS`), U02 `8ebe`, `8ff4`(기존 routing `8ff4..9036`), `49f8c`·`49fc6`(기존 routing `49f8c..4a46c`), F3a `43e34`, fade_card `2a24`.
- [F] 자연 seed(F2 프레임 패스 기본 120 frame): 44·45가 frame 0에 `b96c8`, frame 1부터 `b971a`를 node `101020`에서 실행한다. `78(A6)`=`78`(120)에서 매 frame 1씩 줄어 기록 지평 안에서는 0이 되지 않는다(`b972e..b9740` 미도달). U05 뒤 완주 seed는 50→52(새 44 45)가 되어야 한다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 정정(73→71).** 묶음 2개(권고). 범위 문서는 고치지 않는다.
2. **banked 자료 읽기.** [F] `b96f0 MOVE.L 2001d0.L,22(A6)`은 CPU `200000..2fffff` bank window를 읽는다. 이어 `b9704 MOVEA.L 44(A1),A1`도 그 LONG(자연 seed에서 `2d450e`)을 주소로 다시 읽으므로 같은 window를 읽는다. 권고: 두 읽기 모두 live bus(`am_read` → `read_program_bus`, live `bank_base`, physical span 밖이면 기존 checked 오류 `reached program bank physical span outside ROM`)로 읽는다. 기존 실행부의 banked 읽기와 같은 경로다. bank 값 자체는 상태(`bank_base`)이며 U05는 bank를 바꾸지 않는다.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u05.cpp`의 `animation_objects_u05_block`. 오류는 `unsupported animation objects u05 PC`, `objects u05 caller requires known carry`(메인 지시와 같음).
4. **`c6a96`의 반환 C는 Unknown으로 둔다.** [F] ROM의 `JSR c6a96` 316곳 바로 뒤 명령에 Bcc는 없다(`MOVE.W` 135, `LEA` 108, `JSR` 17, `BRA` 17 등). 그래서 `c6ac0`류(`MOVE.B ...; RTS`)를 known Clear 생산으로 두지 않는다(관례: 소비자가 있을 때만).

## 원본 바이트 근거

[F] 코드 3 범위 합계 674바이트. 이어 붙인 SHA256 `99b538cb5e7b4403407d09a254900eda50ba113e9808126c5237f9cdc28b8c0f`.

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `1ab02..1ab80` | `20182218082e0001001567000006d0414440242e0046b4ae004e670000206b0000104842d4400c4202006ece6000000e4842d440d4410c4201006dbe48404841082e0000001567000006d0414440242e0042b4ae004a670000206b0000104842d4400c4201406e926000000e4842d440d4410c4200006d82023c00fe4e75` |
| `b96c8..b975e` | `3d7c000000683d7c0000001e303c0073323c0011143c00004eb9000c6a9641ee00263d7c020300202d79002001d00022303c010041ee0026226e0022226900444eb900049f8c3d7c007800782cbc000b971a4eb900043e344eb900049fc6536e00786600001a4a6e00766600000c2cbc000b975e600000082cbc000b97c041f9000ba3d64eb90001ab02640000084ef900002a244e75` |
| `c6a96..c6c24` | `48e7c0006100015a12024eb900008ebe4cdf00030c40003366000018303c0c4b123c00004eb900008ebe1d6e001900144e750c400034660000444eb9000497a6640000164eb900008ff4303c0c54123c00004eb900008ebe303c0c50123c00004eb900008ebe303c0c52123c00004eb900008ebe1d6e001900144e750c400060660000364eb9000497a6640000164eb900008ff4303c0c54123c00004eb900008ebe303c0c48123c00004eb900008ebe1d6e001900144e750c40004766000018303c0c76123c00004eb900008ebe1d6e001900144e750c40005d660000284eb9000497a6640000164eb900008ff4303c0c4d123c00004eb900008ebe1d6e001900144e750c40004f66000018303c0c88123c00004eb900008ebe1d6e001900144e750c40005966000018303c0c39123c00004eb900008ebe1d6e001900144e750c40005c66000018303c0c3f123c00004eb900008ebe1d6e001900144e754e753600d64343fa020cd2c33011d64343fa001e2271300036116a0000044e75b24367000006588960eed06900024e75` |

- [F] 범위 밖 이웃: `1ab80`(다른 함수 `MOVE.L (A0)+,D0`로 시작, 미연결), `b975e`(경계 callback), `c6c24`(자료). `1aa7e..1ab02`와 `c6a90..c6a96`은 U01 범위다.
- [F] 자료(모두 live bus로 읽는다):
  - `ba3d6` 8바이트(`ffd0ff00 00600200`, `b9746 LEA ba3d6.L,A0` → `1ab02`의 `MOVE.L (A0)+` 2회). fixed ROM.
  - `c6e08` WORD 표(`c6bfa LEA c6e08(PC),A1`; index `2×D0.W`, `ADDA.W` 부호확장)와 `c6c24` LONG 표(`c6c04 LEA c6c24(PC),A1`; `MOVEA.L (A1,D3.W),A1`, `D3.W`=`4×D0.W`). 두 표는 `c6c24..c6e08`(121 LONG)과 `c6e08..c6efa`(121 WORD)이며 `c6efa`가 첫 하위 목록이다. LONG 0인 entry 28개가 있다(그때 A1=0이고 `c6c0c`는 ROM 주소 0부터 읽는다; 원본대로 둔다).
  - 하위 목록: (key WORD, 가산 WORD) 쌍의 열, key bit15=1이면 끝(`c6c0c BPL`). 0이 아닌 표 포인터의 목록은 `c6efa..c8348`(마지막 끝 key WORD `c8346`) 안의 fixed ROM이다.
  - banked: CPU LONG `2001d0`(bank window)와 그 값 + `44`의 LONG. [F] physical `200000` bank(자연 seed 44·45의 `bank_base`=`200000`)에서 `2001d0`=`002d450e`, `2d4552`=`002d4788`.
- [U] 표 index 상한: `D0.W`는 호출자가 준다(자연 seed는 `b96c8`의 `73`만). 정적으로 121 미만임을 확인하지 않았다. 읽기는 bus가 막는다(U01 미확인 3과 같은 처리).

## block 목록과 실행 의미

[F] 71 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)·`ADDA.W`·`(An,Dn.W)`는 부호확장한다. `MOVE.B`/`MOVE.W` Dn, `ADD.W`, `SWAP`은 나머지 bit를 보존한다.

**C2 `1ab02`(화면 범위 판정, 고정 경계, C 반환) 13**
- `1ab02`: `MOVE.L (A0)+,D0; MOVE.L (A0)+,D1; BTST #1,15(A6); BEQ 1ab14`
- `1ab10`: `ADD.W D1,D0; NEG.W D0` (→`1ab14`)
- `1ab14`: `MOVE.L 46(A6),D2; CMP.L 4e(A6),D2; BEQ 1ab3e; BMI 1ab32` (묶음: `1ab20`. BMI는 (D2−M).L의 bit31)
- `1ab24`: `SWAP D2; ADD.W D0,D2; CMPI.W #200,D2; BGT 1aafc` (부호. `1aafc`는 U01 Set 생산)
- `1ab2e`: `BRA 1ab3e`
- `1ab32`: `SWAP D2; ADD.W D0,D2; ADD.W D1,D2; CMPI.W #100,D2; BLT 1aafc` (→`1ab3e`)
- `1ab3e`: `SWAP D0; SWAP D1; BTST #0,15(A6); BEQ 1ab50`
- `1ab4c`: `ADD.W D1,D0; NEG.W D0` (→`1ab50`)
- `1ab50`: `MOVE.L 42(A6),D2; CMP.L 4a(A6),D2; BEQ 1ab7a; BMI 1ab6e` (묶음: `1ab5c`)
- `1ab60`: `SWAP D2; ADD.W D0,D2; CMPI.W #140,D2; BGT 1aafc`
- `1ab6a`: `BRA 1ab7a`
- `1ab6e`: `SWAP D2; ADD.W D0,D2; ADD.W D1,D2; CMPI.W #0,D2; BLT 1aafc` (→`1ab7a`)
- `1ab7a`: `ANDI.B #fe,CCR; RTS` (C=Clear 생산)

**node callback `b96c8`(+설치 callback `b971a`) 13**
- `b96c8`: `MOVE.W #0,68(A6); MOVE.W #0,1e(A6); MOVE.W #73,D0; MOVE.W #11,D1; MOVE.B #0,D2; JSR c6a96`
- `b96e6`: `LEA 26(A6),A0; MOVE.W #203,20(A6); MOVE.L 2001d0.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 44(A1),A1; JSR 49f8c` (banked 읽기 2회, 결정 2)
- `b970e`: `MOVE.W #78,78(A6); MOVE.L #b971a,(A6)` (→`b971a`)
- `b971a`: `JSR 43e34` (callback 진입)
- `b9720`: `JSR 49fc6`
- `b9726`: `SUBQ.W #1,78(A6); BNE b9746` (Z=결과 WORD)
- `b972e`: `TST.W 76(A6); BNE b9740`
- `b9736`: `MOVE.L #b975e,(A6); BRA b9746` (`b975e`는 경계 callback)
- `b9740`: `MOVE.L #b97c0,(A6)` (→`b9746`. `b97c0`은 경계 callback)
- `b9746`: `LEA ba3d6.L,A0; JSR 1ab02`
- `b9752`: `BCC b975c` (carry 소비; `1ab02` 반환 C)
- `b9756`: `JMP 2a24`
- `b975c`: `RTS`

**C1 `c6a96`(객체 palette 참조) 39**
- `c6a96`: `MOVEM.L D0-D1,-(A7); BSR c6bf6` (D0이 낮은 주소: `A7-8`=D0, `A7-4`=D1)
- `c6a9e`: `MOVE.B D2,D1; JSR 8ebe`
- `c6aa6`: `MOVEM.L (A7)+,D0-D1; CMPI.W #33,D0; BNE c6ac8` (D0, D1 순서로 복원)
- `c6ab2`: `MOVE.W #c4b,D0; MOVE.B #0,D1; JSR 8ebe`
- `c6ac0`: `MOVE.B 19(A6),14(A6); RTS`
- `c6ac8`: `CMPI.W #34,D0; BNE c6b12`
- `c6ad0`: `JSR 497a6` (경계 callee)
- `c6ad6`: `BCC c6aee` (carry 소비; `497a6` 반환 C)
- `c6ada`: `JSR 8ff4`
- `c6ae0`: `MOVE.W #c54,D0; MOVE.B #0,D1; JSR 8ebe`
- `c6aee`: `MOVE.W #c50,D0; MOVE.B #0,D1; JSR 8ebe`
- `c6afc`: `MOVE.W #c52,D0; MOVE.B #0,D1; JSR 8ebe`
- `c6b0a`: `MOVE.B 19(A6),14(A6); RTS`
- `c6b12`: `CMPI.W #60,D0; BNE c6b4e`
- `c6b1a`: `JSR 497a6` (경계 callee)
- `c6b20`: `BCC c6b38` (carry 소비)
- `c6b24`: `JSR 8ff4`
- `c6b2a`: `MOVE.W #c54,D0; MOVE.B #0,D1; JSR 8ebe`
- `c6b38`: `MOVE.W #c48,D0; MOVE.B #0,D1; JSR 8ebe`
- `c6b46`: `MOVE.B 19(A6),14(A6); RTS`
- `c6b4e`: `CMPI.W #47,D0; BNE c6b6c`
- `c6b56`: `MOVE.W #c76,D0; MOVE.B #0,D1; JSR 8ebe`
- `c6b64`: `MOVE.B 19(A6),14(A6); RTS`
- `c6b6c`: `CMPI.W #5d,D0; BNE c6b9a`
- `c6b74`: `JSR 497a6` (경계 callee)
- `c6b7a`: `BCC c6b92` (carry 소비)
- `c6b7e`: `JSR 8ff4`
- `c6b84`: `MOVE.W #c4d,D0; MOVE.B #0,D1; JSR 8ebe`
- `c6b92`: `MOVE.B 19(A6),14(A6); RTS`
- `c6b9a`: `CMPI.W #4f,D0; BNE c6bb8`
- `c6ba2`: `MOVE.W #c88,D0; MOVE.B #0,D1; JSR 8ebe`
- `c6bb0`: `MOVE.B 19(A6),14(A6); RTS`
- `c6bb8`: `CMPI.W #59,D0; BNE c6bd6`
- `c6bc0`: `MOVE.W #c39,D0; MOVE.B #0,D1; JSR 8ebe`
- `c6bce`: `MOVE.B 19(A6),14(A6); RTS`
- `c6bd6`: `CMPI.W #5c,D0; BNE c6bf4`
- `c6bde`: `MOVE.W #c3f,D0; MOVE.B #0,D1; JSR 8ebe`
- `c6bec`: `MOVE.B 19(A6),14(A6); RTS`
- `c6bf4`: `RTS`

**C1 `c6bf6`(palette 번호 조회) 6**
- `c6bf6`: `MOVE.W D0,D3; ADD.W D3,D3; LEA c6e08(PC),A1; ADDA.W D3,A1; MOVE.W (A1),D0; ADD.W D3,D3; LEA c6c24(PC),A1; MOVEA.L (A1,D3.W),A1` (→`c6c0c`)
- `c6c0c`: `MOVE.W (A1),D3; BPL c6c14` (N=WORD bit15)
- `c6c12`: `RTS`
- `c6c14`: `CMP.W D3,D1; BEQ c6c1e`
- `c6c1a`: `ADDQ.L #4,A1; BRA c6c0c`
- `c6c1e`: `ADD.W 2(A1),D0; RTS`

## 구현 범위와 규약

- routing 3 범위: `1ab02..1ab80`, `b96c8..b975e`, `c6a96..c6c24`. 짝수 PC 337개 중 block 시작 71, 내부 266(묶인 PC `1ab20` `1ab5c` 포함). 내부 PC 직접 진입은 `unsupported animation objects u05 PC`다. 경계(`497a6` `b975e` `b97c0`)와 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **carry 소비 block 4개**: `b9752`(`1ab02`: `1aafc` Set / `1ab7a` Clear), `c6ad6` `c6b20` `c6b7a`(`497a6`, 경계). Unknown이면 `objects u05 caller requires known carry`.
- **known carry 생산 block 1개**: Clear `1ab7a`(RTS까지 같은 block). Set은 U01 `1aafc`가 낸다.
- **FLOW_ONLY 20개**(C 보존): `1ab2e` `1ab6a`(BRA), `b971a` `b9720`(JSR), `b9746`(LEA.L+JSR), `b9752`(BCC), `b9756`(JMP), `b975c`(RTS), `c6a96`(MOVEM.L 저장+BSR), `c6ad0` `c6ada` `c6b1a` `c6b24` `c6b74` `c6b7e`(JSR), `c6ad6` `c6b20` `c6b7a`(BCC), `c6bf4` `c6c12`(RTS). 그 밖(MOVE/MOVEQ/MOVEA+MOVE 혼합/CMP/CMPI/CMP.L/TST/SUBQ/ADD/NEG/SWAP, `ADDQ.L #4,A1` block `c6c1a`, `ADDA.W` block `c6bf6`)은 Unknown이다.
- 부호 비교: `BGT`/`BLT`(CMPI.W)는 부호 WORD 비교, `BMI`(`1ab14`·`1ab50` 묶음)는 CMP.L 결과 bit31, `BPL`(`c6c0c`)은 읽은 WORD bit15다.
- 반복: `c6c0c..c6c1a`는 key WORD bit15=1까지 A1을 4씩 올린다. 원본대로 두고 block budget(1,000,000)만 한계다.
- 스택: `c6a96`의 `MOVEM.L D0-D1,-(A7)`은 LONG 2개(D1 먼저 `A7-4`, D0 `A7-8`), `BSR`은 복귀 LONG `c6a9e`를 쌓는다. `c6aa6`은 D0, D1 순서로 꺼낸다. 홀수 A7·work RAM 밖 쓰기는 기존 checked 오류다.
- I/O: RAM d16(A6) `14` `19` `1e` `20` `22` `26` `42` `46` `4a` `4e` `68` `76` `78`과 `15`(BTST), node LONG `(A6)`(callback 설치). port 쓰기는 U05 자체에 없다(callee 몫).
- 회귀 탐침: [F] `engine/tests/animation_machine_objects_u01_test.cpp`의 outside 탐침 `0x1ab02`·`0xc6a96`은 U05 block 시작이 된다. 아무 분석 문서에도 없는 미연결 `0x5f1a0`·`0x5f1a4`로 바꾼다.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed)에서 U05 block에 닿는 callback: `b96c8` 2, `b971a` 170(seed 44·45)과 다른 객체 callback 다수(`1ab02`·`c6a96`은 공유 helper; 예 `aef3a` 2,504, `aef18` 1,072, `bead4`/`beac0`, `9bbf8` 등 57 seed). TB 포함 기준으로 71 block 중 41개가 자연 도달한다. 미도달 30개(fixture 필요): `1ab10` `1ab6e` `b972e` `b9736` `b9740` `b9756` `c6ad0` `c6ad6` `c6ada` `c6ae0` `c6aee` `c6afc` `c6b0a` `c6b1a` `c6b20` `c6b24` `c6b2a` `c6b38` `c6b46` `c6b56` `c6b64` `c6b74` `c6b7a` `c6b7e` `c6b84` `c6b92` `c6bc0` `c6bce` `c6bde` `c6bec`.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 71 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 block 값, 그 밖 Unknown), 소비 block의 Unknown 오류, zero-step, 내부 266 PC 정확한 오류, 홀수 PC, 경계(`497a6` `b975e` `b97c0`) 오류. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, 합성 physical 자료: `ba3d6`, `c6c24`/`c6e08` 표와 하위 목록, banked `2001d0`)로 비교한다.
- 실제 ROM 차분: `1ab02`·`c6bf6`(·`c6a96` 앞부분)을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`): U01+U02+U03 기준 일치 pass 9,056개가 모두 그대로 일치하고, 완주 seed가 50→52(새 44 45)여야 한다.

## 미확인·범위 밖

1. [I] `1ab02`는 고정 화면 경계(`200`/`100`/`140`/`0`)를 쓰는 화면 범위 판정, `c6a96`은 객체 종류(D0)·변형(D1)에 따른 palette slot 참조(`8ebe`), `b96c8`은 120 frame 뒤 `76(A6)`에 따라 `b975e`/`b97c0`로 넘어가는 객체다. 게임 의미는 미확인이다.
2. [U] `497a6`(C3 수학, 반환 C)와 callback `b975e`·`b97c0`은 U05 밖이다.
3. [U] `c6c24`/`c6e08` 표 index 상한과 LONG 0 entry(ROM 주소 0부터 하위 목록으로 읽음)의 의도는 정하지 않았다.

작업자 scratch: 세션 scratchpad `f4u05/`(`u05.py` block·범위·SHA 계산, `dis_u05.py`, `reach.py`; 저장소 밖).
