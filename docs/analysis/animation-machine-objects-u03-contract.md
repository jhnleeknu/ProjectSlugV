# 객체 callback F4 U03: VRAM 글자 writer `e84d6` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U03 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR 복귀점)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다.
- U01 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U03에는 없음), `MOVE.x`는 C를 지운다(필요한 소비자가 있을 때만 known 생산으로 둔다), checked 오류는 경계에서 낸다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. 코드와 자료는 모두 fixed `<100000`에 있으므로 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u03`(HEAD `4b36ff8`, U01 WIP)을 참조했다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u03/u03.py`가 원본 opcode에서 독립 계산했고 아래 목록과 같음을 assert했다.

## 요약

- [F] U03은 함수 1개(`e84d6`, 진입 1개)의 **block 시작 83개**다. 코드 1 범위 `e84d6..e88c6`, 1,008바이트, 282명령이며 미해독·TRAP·묶인 분기·설치 callback은 없다. routing 짝수 PC는 504개, 내부 PC는 421개다. 범위 문서 83과 같다.
- [F] 호출 규약: 유일한 진입 경로는 기존 card menu open 실행부 block `e84c8`(`CMPI.B #10,D1; BCC e84d6`, 아니면 `JMP 3650`)이다. ROM 안에 `e84d6`을 직접 부르는 JSR/JMP/BSR/LEA는 없다(`f4u01/callers.py`). `e84c8`은 글자 renderer 포인터(`LEA e84c8,A1` 후 `3918`/`3670`/`3a70`/`3950` text loop의 `JSR (A1)`)로 쓰이고, 직접 `JSR e84c8`도 있다(`e67aa` 등).
- [F] 입력: `A0`=문자열 다음 BYTE 포인터(lookahead), `D0.W`=VRAM 주소, `D1.B`=모드(`30` `61` `48` `4b` `41` `31` `68` `6b` `58` `32`, 그 밖은 `3650` fallback), `D1.W` 상위 nibble=attribute, `D2.B`=글자. 출력: `D0.W`=다음 VRAM 주소(+`1e`/`1f`/`20`/`21`), `A0`=소비한 lookahead만큼 전진, `D0` 상위 WORD=마지막 port LONG의 하위 WORD(SWAP 결과). `D1..D7`/`A1..A6`은 `MOVEM`으로 보존된다.
- [F] 경계 callee 0: 나가는 곳은 `JSR 3650`(`e8564`, `e88ba`) 하나이며 기존 card menu open 실행부가 실행한다.
- [F] I/O: VRAM port `MOVE.L D0,3c0000.l` 15 site(`e858e e859a e8610 e861c e8628 e8634 e865c e8668 e8674 e8724 e87b6 e87ca e8876 e8894 e88a6`). work RAM 쓰기는 `MOVEM` stack 52바이트뿐이다.
- 자연 seed(범위 scratch 재생 `f4scope/dyn`, TB 시작 기준): `e5614` `e5626` `e5680` `e56a0`(U02) 경유로 90·91·118~126, `e7426`(U06) 경유로 108·109에서 13 block(`e84d6 e8530 e8558 e8560 e856a e856e e85aa e85ba e85de e85e6 e8604 e8608 e88c0`, fall-through `e8610` 포함 14)이 실행된다. 모드 `30`·`41`만 쓰인다. **U03만으로는 새 완주 seed가 없다**: 이 seed들은 U01 차분에서 frame 0 `e5120`(U02)에서 먼저 멈춘다. 범위 문서의 39→50은 U02+U03 합산이다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **port 기록 단위.** [F] `MOVE.L D0,3c0000.l` 한 명령을 `VideoPortWrite{address=3c0000,size=4,value=D0}` 한 건으로 기록한다(권고). 기존 `animation_machine_card_menu_open.cpp`의 `3650`/`open_tile`, `fixed_text.cpp`의 `e8558` 모델과 같다. [F] Unicorn observer도 LONG 쓰기를 `(2,3c0000,4,value)` 한 건으로 기록한다(scratch fixture 재생). 차분 driver의 `MS5-SCHED-PORTS-1` 직렬화도 split 없이 같다.
2. **carry 분류.** [F] U03 안에 carry 소비 block은 없다. [F] `e84c8` renderer 호출 뒤 명령은 C를 소비하지 않는다: `3928 JSR (A1)`→`392a BRA`→`386e MOVE.B`, `3a10`/`3a36`/`3a66 JSR (A1)`→`MOVE.W`/`MOVE.W`/`MOVE.W`(이후 `ANDI.B #fe,CCR`), `36b0 JSR (A1)`→`MOVEA.L`, 직접 `JSR e84c8`(`e67aa` `e6a80` 등)→`MOVE.W`/`MOVE.B`/`MOVEM`/`DBRA`/`ADDQ`. [I] 나열하지 않은 `JSR (A1)` 경로가 더 있을 수 있다. 권고: FLOW_ONLY는 CCR을 바꾸지 않는 9 block(`e856a` `e85b2` `e85c2` `e868c` `e869c` `e86da` `e8706` `e8856` BRA/LEA, `e88c0` `MOVEM.L (A7)+`+`RTS`). 나머지 74 block은 Unknown이다(`ADDQ.W #6,A1; BRA`인 `e8866`도 U01 `ADDQ.W #1,A2` 관례대로 Unknown). known 생산 block은 두지 않는다.
3. **무효화되는 기존 negative.** [F] `e84d6`을 "실행부 없음" 경계로 쓰는 기존 검사가 routing으로 무효가 된다.
   - C++ test(`make test` 대상, 이 단위에서 대체 PC로 고침 권고): `engine/tests/animation_machine_card_menu_test.cpp`(outside 목록), `animation_machine_card_menu_close_test.cpp`(outside 목록), `animation_machine_card_menu_open_test.cpp`(BOUNDARY 목록과 reach case 8의 rollback 검사). 대체 PC는 어떤 `docs/analysis` 문서에도 없는 미연결 `5f080`부터 쓴다(U02의 `5f040+`와 겹치지 않음).
   - Python 검증기(수정하지 않음, 목록만): `tools/verify_animation_machine_card_child.py`(`e84d6_pc_has_no_executor`), `verify_animation_machine_card_menu.py`, `verify_animation_machine_card_menu_open.py`, `verify_animation_machine_card_menu_input.py`, `verify_animation_machine_card_menu_close.py`.
4. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u03.cpp`의 `animation_objects_u03_block`. 오류는 `unsupported animation objects u03 PC`(내부 PC), `objects u03 caller requires known carry`(U03에는 소비자가 없어 쓰이지 않지만 U01과 같은 이름을 예약).

## 원본 바이트 근거

[F] 코드 1 범위 1,008바이트 SHA256 `0d11139fa93d47dd655b5917de2c9c5e9f35308d67291100e63d7784d9f4ae13`(바이트 전체는 scratch `u03.py B` 출력과 ROM에서 재생성).

[F] 자료(fixed ROM, physical window로만 읽음):
- `e7c44..e7cc8`: LONG 33개. 상위 WORD=결과 tile, 하위 WORD=2-BYTE 글자 key. `e7cc4` LONG `082a0000`의 하위 0이 종료다(`e8764 TST.W D7`).
- `e7cc8` `e7ec8` `e80c8` `e82c8`: 각 WORD 256개(`ANDI.W #ff,D2; ADD.W D2,D2`로 index ≤ `1fe`). 모드 `48`→`e7cc8`, `4b`→`e7ec8`, `6b`→`e80c8`, `68`→`e82c8`.
- `e88c6..e89da`: 모음별 표 10개(`e88c6` a, `e8900` i, `e890a` u, `e8924` e, `e8946` o, `e8970` A, `e8992` I, `e899c` U, `e89a6` E, `e89c0` O). 각 항목 8바이트(key WORD, tile WORD 2개, 미사용 WORD), key 0이 종료다. 마지막 종료 WORD는 `e89d8`이다.
- 문자열 BYTE(`A0`): RAM 또는 ROM, live bus로 읽는다. [F] `3670` 경로는 `LEA 3650(PC),A0` 뒤 `JSR (A1)`이라 `A0`이 코드 `3650`을 가리킨다(첫 BYTE `48`).

## block 목록과 실행 의미

[F] 83 block. 각 줄은 block 안 명령 전체다. "(→x)"는 fall-through다. `.B`/`.W` 연산은 나머지 bit를 보존한다. `ADDQ.W #n,An`은 32비트 주소 덧셈, `(A1,D2.W)`는 부호확장 index다. `CMPI.B`+`BCS`/`BHI`는 무부호, `BEQ`/`BNE`는 Z다.

**진입·결합 문자 처리 13**
- `e84d6`: `MOVEM.L D1-D7/A1-A6,-(A7); MOVE.B (A0),D7; CMPI.B #de,D7; BNE e8530` (stack 52바이트, 낮은 주소부터 D1..D7,A1..A6)
- `e84e4`: `CMPI.B #b3,D2; BNE e84f6`
- `e84ec`: `ADDQ.W #1,A0; MOVE.B #e0,D2; BRA e8558`
- `e84f6`: `CMPI.B #b6,D2; BCS e8510`
- `e84fe`: `CMPI.B #c4,D2; BHI e8510`
- `e8506`: `ADDQ.W #1,A0; ADDI.B #2b,D2; BRA e8558`
- `e8510`: `CMPI.B #ca,D2; BCS e8530`
- `e8518`: `CMPI.B #ce,D2; BHI e8530`
- `e8520`: `ADDQ.W #1,A0; SUBI.B #ca,D2; ADD.B D2,D2; ADDI.B #f0,D2; BRA e8558`
- `e8530`: `CMPI.B #df,D7; BNE e8558`
- `e8538`: `CMPI.B #ca,D2; BCS e8558`
- `e8540`: `CMPI.B #ce,D2; BHI e8558`
- `e8548`: `ADDQ.W #1,A0; SUBI.B #ca,D2; ADD.B D2,D2; ADDI.B #f1,D2; BRA e8558`

**모드 분기·출력 70**
- `e8558`: `CMPI.B #30,D1; BNE e856e`
- `e8560`: `MOVE.B #3,D1; JSR 3650` (기존 실행부)
- `e856a`: `BRA e88c0`
- `e856e`: `CMPI.B #61,D1; BNE e85aa`
- `e8576`: `SWAP D0; MOVE.W D1,D0; MOVE.B #a0,D0; LSL.W #4,D0; MOVE.B D2,D0; ANDI.B #f0,D0; ADD.B D0,D0; ANDI.B #f,D2; ADD.B D2,D0; MOVE.L D0,3c0000; ADDI.L #10010,D0; MOVE.L D0,3c0000; SWAP D0; ADDI.W #1f,D0; BRA e88c0`
- `e85aa`: `CMPI.B #48,D1; BNE e85ba`
- `e85b2`: `LEA e7cc8(PC),A1; BRA e85c6`
- `e85ba`: `CMPI.B #4b,D1; BNE e85de`
- `e85c2`: `LEA e7ec8(PC),A1` (→`e85c6`)
- `e85c6`: `SWAP D0; MOVE.W D1,D0; LSL.W #4,D0; ANDI.W #f000,D0; ANDI.W #ff,D2; ADD.W D2,D2; OR.W (A1,D2.W),D0; BRA e8610`
- `e85de`: `CMPI.B #41,D1; BNE e8644`
- `e85e6`: `SWAP D0; MOVE.W D1,D0; MOVE.B #80,D0; LSL.W #4,D0; MOVE.B D2,D0; ANDI.B #f0,D0; ADD.B D0,D0; ANDI.B #f,D2; CMPI.B #8,D2; BCS e8608`
- `e8604`: `ADDI.W #100,D0` (→`e8608`)
- `e8608`: `ANDI.B #7,D2; ADD.B D2,D2; OR.B D2,D0` (→`e8610`)
- `e8610`: `MOVE.L D0,3c0000; ADDI.L #10010,D0; MOVE.L D0,3c0000; ADDI.L #200001,D0; MOVE.L D0,3c0000; SUBI.L #10010,D0; MOVE.L D0,3c0000; SWAP D0; ADDI.W #20,D0; BRA e88c0` (port 4건)
- `e8644`: `CMPI.B #31,D1; BNE e8684`
- `e864c`: `SWAP D0; MOVE.W D1,D0; MOVE.B #40,D0; LSL.W #4,D0; MOVE.B D2,D0; ADDI.B #80,D0; MOVE.L D0,3c0000; ADDI.L #10010,D0; MOVE.L D0,3c0000; ADDI.L #10010,D0; MOVE.L D0,3c0000; SWAP D0; ADDI.W #1e,D0; BRA e88c0`
- `e8684`: `CMPI.B #68,D1; BNE e8694`
- `e868c`: `LEA e82c8(PC),A1; BRA e86a0`
- `e8694`: `CMPI.B #6b,D1; BNE e8734`
- `e869c`: `LEA e80c8(PC),A1` (→`e86a0`)
- `e86a0`: `CMPI.B #40,D2; BNE e8710`
- `e86a8`: `MOVE.B (A0)+,D2; MOVEQ #0,D7; CMPI.B #2e,D2; BEQ e86de`
- `e86b4`: `MOVEQ #1,D7; CMPI.B #3a,D2; BEQ e86de`
- `e86be`: `MOVEQ #2,D7; CMPI.B #7e,D2; BEQ e86de`
- `e86c8`: `CMPI.B #2d,D2; BEQ e86de`
- `e86d0`: `CMPI.B #60,D2; BNE e86da`
- `e86d8`: `MOVE.B (A0)+,D2` (→`e86da`)
- `e86da`: `BRA e8710`
- `e86de`: `MOVE.B (A0)+,D2; CMPI.B #61,D2; BEQ e870a`
- `e86e8`: `ADDQ.W #3,D7; CMPI.B #75,D2; BEQ e870a`
- `e86f2`: `ADDQ.W #3,D7; CMPI.B #65,D2; BEQ e870a`
- `e86fc`: `ADDQ.W #2,D7; CMPI.B #6f,D2; BEQ e870a`
- `e8706`: `BRA e8710`
- `e870a`: `MOVE.W D7,D2; ADDI.W #80,D2` (→`e8710`)
- `e8710`: `ANDI.W #ff,D2; ADD.W D2,D2; SWAP D0; MOVE.W (A1,D2.W),D0` (→`e871c`)
- `e871c`: `LSL.W #4,D1; ANDI.W #f000,D1; OR.W D1,D0; MOVE.L D0,3c0000; SWAP D0; ADDI.W #20,D0; BRA e88c0`
- `e8734`: `CMPI.B #58,D1; BNE e877a`
- `e873c`: `CMPI.B #80,D2; BCS e85e6`
- `e8744`: `CMPI.B #a0,D2; BCS e8754`
- `e874c`: `CMPI.B #e0,D2; BCS e85e6`
- `e8754`: `LSL.W #8,D2; MOVE.B (A0)+,D2; LEA e7c44(PC),A1` (→`e875c`)
- `e875c`: `MOVE.L (A1)+,D7; CMP.W D7,D2; BEQ e8768`
- `e8764`: `TST.W D7; BNE e875c` (key 0에서 끝: 종료 LONG의 상위 WORD를 쓴다)
- `e8768`: `SWAP D7; SWAP D0; MOVE.W D7,D0; LSL.W #4,D1; ANDI.W #f000,D1; OR.W D1,D0; BRA e8610`
- `e877a`: `CMPI.B #32,D1; BNE e88b6`
- `e8782`: `CMPI.B #40,D2; BNE e88b6`
- `e878a`: `MOVE.B (A0)+,D2; CMPI.B #21,D2; BNE e879c`
- `e8794`: `SWAP D0; MOVE.W #bea,D0; BRA e871c`
- `e879c`: `CMPI.B #63,D2; BEQ e87aa`
- `e87a2`: `CMPI.B #43,D2; BNE e87da`
- `e87aa`: `SWAP D0; MOVE.W D1,D0; MOVE.B #30,D0; LSL.W #4,D0; MOVE.B D2,D0; MOVE.L D0,3c0000; ADDI.L #10000,D0; ANDI.W #f00,D0; ORI.W #beb,D0; MOVE.L D0,3c0000; SWAP D0; ADDI.W #1f,D0; BRA e88c0`
- `e87da`: `LSL.W #8,D2; MOVE.B (A0),D2; LEA e88c6(PC),A1; CMPI.B #61,D2; BEQ e885a`
- `e87ea` `e87f6` `e8802` `e880e` `e881a` `e8826` `e8832` `e883e` `e884a`: `LEA t(PC),A1; CMPI.B #k,D2; BEQ e885a` (t/k = `e8900`/`69`, `e890a`/`75`, `e8924`/`65`, `e8946`/`6f`, `e8970`/`41`, `e8992`/`49`, `e899c`/`55`, `e89a6`/`45`, `e89c0`/`4f`)
- `e8856`: `BRA e886a`
- `e885a`: `MOVE.W (A1)+,D3; BEQ e886a`
- `e8860`: `CMP.W D2,D3; BEQ e8886`
- `e8866`: `ADDQ.W #6,A1; BRA e885a`
- `e886a`: `SWAP D0; MOVE.W D1,D0; MOVE.B #30,D0; LSL.W #4,D0; MOVE.B D2,D0; MOVE.L D0,3c0000; SWAP D0; ADDI.W #20,D0; BRA e88c0`
- `e8886`: `ADDQ.W #1,A0; SWAP D0; MOVE.W D1,D0; LSL.W #4,D0; ANDI.W #f000,D0; OR.W (A1)+,D0; MOVE.L D0,3c0000; SUBI.L #10000,D0; ANDI.W #f000,D0; OR.W (A1),D0; MOVE.L D0,3c0000; SWAP D0; ADDI.W #21,D0; BRA e88c0`
- `e88b6`: `MOVE.B #3,D1; JSR 3650` (모드 fallback)
- `e88c0`: `MOVEM.L (A7)+,D1-D7/A1-A6; RTS`

## 구현 범위와 규약

- routing 1 범위 `[e84d6,e88c6)`. 짝수 PC 504개 중 block 시작 83, 내부 421. 내부 PC 직접 진입은 `unsupported animation objects u03 PC`다. 이웃 `e84d4`(card menu open 범위 밖)와 `e88c6`(자료)은 `unsupported animation machine PC`다.
- carry: 소비 0, known 생산 0, FLOW_ONLY 9(결정 2). 나머지는 Unknown.
- 반복: `e875c..e8764`(LONG 표, key WORD 0까지)와 `e885a..e8866`(WORD 표, key 0까지)은 원본대로 두고 block budget(1,000,000)만 한계다.
- 홀수 주소 WORD/LONG 읽기(`(A1,D2.W)`는 짝수 표 + 짝수 index, `(A1)+`는 짝수 표에서 시작)와 stack 밖 `A7`의 `MOVEM`은 기존 checked 오류(`am_push`/`am_pop`/`am_read`)다. port 쓰기는 `3c0000` event만 기록하고 장치 상태는 바꾸지 않는다.
- 회귀 탐침: 결정 3의 C++ test 3개 파일에서 `e84d6` 탐침을 대체한다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 83 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), zero-step, 내부 421 PC 정확한 오류, 홀수 PC, 이웃 경계. 모든 모드·결합 문자·`@` 문법·표 검색 종료/일치 경로를 원본 코드로 만든 typed fixture(Unicorn, 합성 표 자료)로 비교하고 port 순서·값을 함께 비교한다.
- 차분(F2 프레임 패스, 142 seed): 이전 일치 pass 7,736이 모두 그대로 일치하고 mismatch 0이어야 한다. U03만으로는 완주 seed 39가 그대로다(U02 필요).

## 미확인·범위 밖

1. [I] `e84d6`은 2-BYTE(Shift-JIS 계열, `de`/`df` 탁점·반탁점 결합) 글자와 font별 `@` 확장 문법을 VRAM tile로 쓰는 writer다. 모드 BYTE 의미(font id)와 attribute nibble의 게임 의미는 미확인이다.
2. [U] `e7c44` LONG 표가 key를 찾지 못할 때 종료 LONG의 상위 WORD(`082a`)를 tile로 쓰는 것이 의도인지는 미확인이다(원본대로 실행).
3. 범위 밖: `e84c8`/`3650`(card menu open 실행부), `e5614` 계열(U02), `e7426`(U06).

작업자 scratch: 세션 scratchpad `f4u03/`(`u03.py` block·범위·SHA 계산, `dis_u03.py`, `reach.py`; 저장소 밖).
