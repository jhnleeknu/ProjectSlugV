# 객체 callback F4 U08b: 공유 객체 core C4/C6(지형 접촉 `46372`·`4683c`·`468e0`, 기울기 자료 `461ec`, 객체 갱신 `4be34`/`4be82`/`4bf16`) 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 U08 계약(`animation-machine-objects-u08-contract.md`, SHA256 `fd484c1cc1bcd87a87f69892451a1cfd36528db5797cca7298514c8c1f703d8d`)의 "U08b(제안, 미구현)" 항목과 범위 문서(`animation-machine-object-callbacks-f4-scope.md`, SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U08 행이다. 단위 형식과 규약은 U01 계약(SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`)과 U08 계약을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee는 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01~U08a 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U08b에는 없음). `MOVE.x`/`MOVEQ`/`TST`/`CMP`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). `MOVEM`/`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`, `BTST`/`BCLR`(Z만), `Scc`만인 block은 FLOW_ONLY다. block 경계 너머의 flag는 원본과 같은 값으로 정확히 다시 계산할 수 있을 때만 다시 계산한다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U08b의 코드와 자료는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u08b`(HEAD `b4ba243` = U01~U08a WIP, `engine/src/animation_machine.cpp` SHA256 `e7dd318a7ab55ae16bd0a9cb605f940a54323d4c96ac1b1a0eb05b1f35f8ead9`)을 참조했다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u08b/u08b.py`가 원본 opcode에서 독립 계산했고 U08 계약의 U08b 제안 수(165)와 같다.

## 요약

- [F] **U08b = 165 block.** 함수 진입 9개(C6 `461ec` `46372` `4683c` `468e0`, C4 `4bb22` `4bc44` `4be34` `4be82` `4bf16`). 코드 7 범위 1,508바이트, 436명령이며 미해독·TRAP·계산 PC·레지스터 간접 점프·묶인 Bcc·`MOVE.L #imm,(A6)` 설치 callback은 없다. routing 짝수 PC는 754개, 내부 PC는 589개다.
- [F] **경계 callee(실행부 없음) 8개**: `44ade`(U20 점프 표 함수) `4578a` `45b12` `4662e` `469d8`(U09 진입, 다른 작업 트리 `metalslug-u09`에서 구현 중) `492c8` `4b8e8` `4bce0`. 모두 이 작업 트리에서 routing 밖이다.
- [F] 기존 실행부로 나가는 호출: U08a `447be`(BSR 4곳) `4483a`(BSR 2곳) `1aa3a`(`4bf8a`), scene `43e34`(`4bf7a JSR`, 복귀 `4bf80`). U08b 함수끼리의 호출: `468b6 BSR 46372`, `4be34 JSR 4bc44(PC)`, `4be38..4be46 JSR 4bb22`, `4be4c BRA 4bf0a`, `4bee8 BRA 4bf16`, `4bf10`→`4bf16` fall-through.
- [F] **U09와 겹침 없음.** U09 범위(`469a0..46bfc` `4706c..` `7670e..`)와 U08b 범위는 겹치지 않는다. `469d8`은 U09 진입이므로 U08b에서는 경계다(`4bea0` `4bf0a`의 `JSR 469d8`). 반대로 U09는 `461ec` `4683c` `468e0`을 U08b 경계로 둔다(U09 계약 "U08 의존"). 둘 다 병합되면 서로 연결된다.
- [F] **SUBX 2곳(`4639e` `464b2`)은 같은 block 안에서 X가 정해진다.** 각각 block `46398`/`464ac`의 첫 명령 `ADDI.L #80000000,D6`이 X(=C)를 만들고 바로 다음 `SUBX.L D4,D4`가 소비한다. X는 block 밖으로 건너가지 않는다.
- [F] **PC 상대 WORD 자료 표 `461ec MOVE.W 461f2(PC,D7.W),D7`.** 계산 PC가 아니라 자료 읽기다. 읽는 주소는 `461f2`+sext(`D7.W`)(32bit 덧셈)이고 live bus(fixed ROM)에서 WORD로 읽는다. 표 `461f2..46372`(`180`바이트, SHA256 `f57680acc3e9fd72276048edabf0e90ce219eec91478c60af09dff376693aa6c`)는 4바이트 간격 96칸(WORD 값, WORD 0)이고 바로 뒤가 `46372` 함수다. [I] 호출자 2곳(`46bee`(U09) `46ed6`)의 D7은 LONG `54d8(A5)`이고 그 값은 `447be` 결과(`4k`, k<`60`, 또는 `160`)로 보인다. 이때 읽기는 `461f2..46370` 안이다. [U] 전 호출 closure는 확인하지 않았다. 홀수 `D7.W`이면 원본 68000은 주소 오류이고 C++는 기존 bus checked 오류 `program bus requires even WORD/LONG address`다.
- [F] block 경계 너머 flag는 한 곳이다: `4beec BEQ 4bf0a`는 `4be9a ADD.B D7,D7`의 Z를 쓴다. ROM 전체에서 `4beec`로 가는 분기는 `4be9c BCC 4beec` 하나뿐이고(Bcc/BRA/BSR/JMP/JSR 전수 검사) 그 사이에 D7이 바뀌지 않으므로 Z=(`D7.B`=0)로 정확히 다시 계산한다(아래 결정 3).
- [F] carry 소비 block 7개는 모두 같은 block 안에서 C를 만든다(`SUBQ.W`/`CMPI.W`/`ADD.B` 뒤 `BCS`/`BCC`). block 경계를 건너는 C 소비자와 known C 생산 block은 없다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u08b.cpp`의 `animation_objects_u08b_block`. 오류는 `unsupported animation objects u08b PC`(내부 PC), `objects u08b caller requires known carry`(U08b에는 block 경계를 건너는 C 소비자가 없어 쓰이지 않지만 U03·U08a처럼 예약). 메인 지시와 같다.
2. **`461ec` 자료 표.** 권고: 계산 PC 정책(F1 결정 3)의 대상이 아니므로 표 index 상한을 정하지 않고, 원본처럼 `461f2`+sext(`D7.W`)를 live bus WORD로 읽는다. 원본 실행 의미는 상한과 무관하게 같다(ROM 밖이나 RAM이면 bus가 정한다. 홀수는 checked 오류).
3. **`4beec`의 Z 재계산.** 권고: `4beec`를 정적 디코드대로 block 시작으로 두고 Z=(`D7.B`=0)로 판정한다(U04 `d73ca`의 Z 재계산과 같은 방식). 근거: 유일한 선행 분기가 `4be9c`(BCC taken)이고 `ADD.B D7,D7` 결과가 `D7.B`에 그대로 남는다. 직접 진입(시험 하네스)에서는 진입 D7로 판정한다. 대안: `4be9a` block에 `4beec`의 BEQ를 묶고 `4beec`를 내부 PC로 두기(비권고: 분기 대상은 시작이라는 결정 3과 다름).
4. **`CLR`/`Scc`의 68000 읽기 주기.** [F] 68000 `CLR.B`/`CLR.W`/`CLR.L`과 메모리 `Scc`는 쓰기 전에 같은 주소를 읽는다. 대상이 모두 work RAM d16(A5)이므로 상태 차이가 없다. U07·U09처럼 쓰기만 모델한다(권고).
5. **carry.** 권고: FLOW_ONLY 27, Unknown 138, 소비 block 7(모두 block 안 생산), known 생산 0(아래 근거).
6. **무효화 탐침.** [F] 작업 트리 `engine/tests/*.cpp`·`engine/src/*.cpp`·`tools/*.py`에서 U08b 7 범위 안의 `0x` 상수와 9 진입 주소 문자열을 찾았고 없다. 교체할 탐침이 없다(교체 후보 `5f600`부터는 쓰지 않음).

## 원본 바이트 근거

[F] 코드 7 범위 합계 1,508바이트. 범위 순서로 이어 붙인 SHA256 `10a263269b7cc42d4cbb5a87f6530a49b4680e903e34e4c44e7bda97de4fc66d`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `461ec..461f2` | 6 | `40858cdf17991745b8e1f580af2f37ae583fc2e80bfd1165eccda547bd0d2c8f` | 기울기 자료 `461ec` |
| `46372..4662e` | 700 | `96cd4237e42208cc1c20aa5a3af7e98c1142301c8b6f58f97b72533a5c68d0cf` | 지형 접촉 한 걸음 `46372` |
| `4683c..46994` | 344 | `63fe79ff1ce8820bcd3e886afbdca9f371eea977cc300f34d9e49df514977d17` | 지형 이동 loop `4683c`, 화면 경계 clamp `468e0` |
| `4bb22..4bb52` | 48 | `7151d04ebd0fdc33fe98a9c23526e216c43ec76d82fac0e15b850df0496e35ac` | 이동 금지 bit `4bb22` |
| `4bc44..4bca0` | 92 | `d6ff81cb85c9ef5671b680b4c43a8742394f7a2634d4f51af3ba31f0092a4af5` | 지형 조건 초기화 `4bc44` |
| `4be34..4be50` | 28 | `710b814b362a0ce63ed648107800dcf4ffa7a2ab180177d20890ef6a0b5ad50f` | C4 `4be34` |
| `4be82..4bfa4` | 290 | `93e5586ce543bf3742694e55db1ea517bdf65c9fdedb2d8916751855af2dab2a` | C4 `4be82`, 공통 꼬리 `4bf0a`/`4bf16` |

- [F] 범위 밖 이웃(routing 밖): `461ea` 앞(다른 함수 끝), `461f2..46372`(자료), `4662e`(경계 callee), `46994..469a0`(U09 자료 목록), `4bb52..`·`4bca0..4bce0`(ROM 사각형 자료 8바이트 ×8), `4bce0`(경계), `4be50..4be82`(다른 C4 함수, `4be68`/`4be7e BRA 4bf0a`로 이 단위에 들어옴), `4bfa4..`(다른 함수, `4bfb0`/`4bfbc BRA 4bf0a`, `4bfd0 BCC 4bf0a`, `4bfac BSR 4bb22`).
- [F] 자료(모두 live bus로 읽는다):
  - ROM: `461ec`의 WORD `461f2+sext(D7.W)`. `468e0`의 A1=LONG `54a6(A5)`가 가리키는 WORD `0` `2` `4` `6`(A1). [F] ROM에서 `54a6(A5)` 쓰기는 `4bdd6 MOVE.L D7,54a6(A5)`(경계 `4bce0` 안) 하나이고 그 값은 상수 `4bca0` `4bcc0` `4bcc8` `4bcd0` `4bcd8`(ROM 사각형) 또는 그 밖 경로의 D7이다.
  - work RAM d16(A5): BYTE `549c..54a5` `54b4`, WORD `5404` `5406` `54aa`(OR 읽기-쓰기) `54ae` `54b0` `54b2` `54de`, LONG `53a2` `53a6` `53bc` `53c0` `54a6` `54b6`(ADD 읽기-쓰기). 절대 BYTE `10d49d`(쓰기 0).
  - node d16(A6): BYTE `15` `5e` `61` `6d`, WORD `6e`, LONG `2e..41`(`MOVEM.L` D0-D3/A0), `36` `3a` `3e`. 객체 LONG `14` `18` `1c` `20`(A0/A1).
- [F] I/O port 쓰기·bank 변경 없음. 스택: `463ee MOVE.L D5,-(A7)`↔`46488 MOVE.L (A7)+,D5`, `4683c MOVE.W 54de(A5),-(A7)`↔`46884 MOVE.W (A7)+,54de(A5)`, `4bf38 MOVEM.L D4/D6-D7,-(A7)`↔`4bf9e MOVEM.L (A7)+,D4/D6-D7`, BSR/JSR 복귀 LONG.

## block 목록과 실행 의미

[F] 165 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `.B`·`.W` 연산은 나머지 bit를 보존하고 `MOVEQ`는 LONG 전체를 쓴다. 부호 분기 `BGT`/`BLT`/`BGE`/`BLE`는 직전 연산 크기의 N·V·Z, `BVC`는 V, `BMI`/`BPL`은 N, `BCS`/`BCC`는 C다.

**기울기 자료 `461ec` 1**
- `461ec`: `MOVE.W 461f2(PC,D7.W),D7; RTS`

**지형 접촉 한 걸음 `46372` 79**
- `46372`: `TST.L D2; BNE 4637c` / `46378`: `MOVEQ #0,D6; RTS`
- `4637c`: `CMPI.W #160,D7; BEQ 463d8` / `46384`: `BSR 44ade`(경계)
- `46388`: `SUBI.L #80000000,D6; BEQ 463d8` / `46392`: `ADD.L D2,D6; BVC 463d8`
- `46398`: `ADDI.L #80000000,D6; SUBX.L D4,D4; SUB.L D4,D6; SUB.L D6,D2; EXG D2,D6; ADD.L D6,D0; BSR 4483a`(U08a)
  - `ADDI.L`의 X=C=(D6 원래 값 ≥u `80000000`). `SUBX.L D4,D4`: D4=0−X(0 또는 `ffffffff`). 이어 D6=D6−D4.
- `463ac`: `CMPI.W #160,D7; BEQ 463c0` / `463b4`: `BSR 45b12`(경계) / `463b8`: `BSR 4578a`(경계) / `463bc`: `MOVEQ #-1,D6; RTS`
- `463c0`: `TST.B 54b4(A5); BNE 463d8` / `463c8`: `ORI.W #40,54aa(A5); MOVE.B #ff,54b4(A5); MOVEQ #-1,D6; RTS`
- `463d8`: `MOVEQ #8,D4; SWAP D4; MOVE.L D2,D5; CMP.L D4,D5; BLE 463e6` / `463e4`: `MOVE.L D4,D5` (→`463e6`)
- `463e6`: `ADD.L D5,D4; BGE 463ee` / `463ec`: `SUB.L D4,D5` (→`463ee`)
- `463ee`: `MOVE.L D5,-(A7); MOVE.L D0,D4; ANDI.L #7ffff,D4; ADD.L D5,D0; ADD.L D5,D4; SWAP D4; SUBQ.W #8,D4; BCS 46488` (C는 `SUBQ.W`의 borrow)
- `46404`: `SWAP D0; SWAP D1; BSR 447be`(U08a)
- 결과 처리 묶음 P(`447be` 반환 뒤, 세 벌: 기준 `4640c`·`464ea`·`4658e`, 기준+오프셋이 block 시작):
  - `+00`: `MOVE.W D6,54b2(A5); MOVE.W 54ae(A5),D4; MOVE.W D7,54ae(A5); CMPI.W #178,D4; BNE +2c`
  - `+14`: `TST.B 54a4(A5); BNE +24` / `+1c`: `CMPI.W #160,D7; BCS +3c` / `+24`: `TST.B 54a5(A5); BNE +3c`
  - `+2c`: `CMPI.W #17c,D4; BNE +46` / `+34`: `TST.B 54a5(A5); BEQ +46` / `+3c`: `MOVE.W #160,D7; ORI.W #10,54aa(A5)` (→`+46`)
  - `+46`: `CMPI.W #174,D4; BNE +5a` / `+4e`: `CMPI.W #174,D7; BNE +5a` / `+56`: `MOVE.W #160,D7` (→`+5a`)
  - `+5a`: `CMPI.W #178,D7; BEQ +68` / `+60`: `CMPI.W #17c,D7; BNE +72` / `+68`: `MOVE.W #160,D7; ORI.W #400,54aa(A5)` (→`+72`)
  - `+72`: `MOVE.W D7,54b0(A5); SWAP D0; SWAP D1; MOVEQ #0,D4` (→`+7c`: `46488` / `46566` / `4660a`)
- `46488`: `MOVE.L (A7)+,D5; TST.W D4; BNE 46624` / `46490`: `CMPI.W #160,D7; BEQ 46624` / `46498`: `BSR 44ade`(경계)
- `4649c`: `SUBI.L #80000000,D6; BEQ 46624` / `464a6`: `CMP.L D5,D6; BVC 46624`
- `464ac`: `ADDI.L #80000000,D6; SUBX.L D4,D4; SUB.L D4,D6; SUB.L D5,D2; ADD.L D6,D2; BSR 4483a`
- `464be`: `CMPI.W #160,D7; BEQ 4656a` / `464c6`: `BSR 45b12` / `464ca`: `BSR 4578a`
- `464ce`: `MOVE.L D0,D4; ANDI.L #7ffff,D4; SUB.L D6,D0; SUB.L D6,D4; SWAP D4; SUBQ.W #8,D4; BCS 46566` / `464e2`: `SWAP D0; SWAP D1; BSR 447be` / P(`464ea`)
- `46566`: `MOVEQ #-1,D6; RTS`
- `4656a`: `TST.B 54b4(A5); BNE 46614`
- `46572`: `464ce`와 같고 `BCS 4660a` / `46586`: `SWAP D0; SWAP D1; BSR 447be` / P(`4658e`)
- `4660a`: `MOVE.B #ff,54b4(A5); MOVEQ #-1,D6; RTS`
- `46614`: `SUB.L D6,D2; ORI.W #40,54aa(A5); CLR.B 54b4(A5); MOVEQ #0,D6; RTS`
- `46624`: `SUB.L D5,D2; CLR.B 54b4(A5); MOVEQ #0,D6; RTS`

**지형 이동 loop `4683c` 24**
- `4683c`: `MOVE.W 54de(A5),-(A7); SWAP D0; SWAP D1; BSR 447be`
- `46848`: `MOVE.W D7,54ae(A5); CMPI.W #178,D7; BEQ 4685a` / `46852`: `CMPI.W #17c,D7; BNE 46864` / `4685a`: `MOVE.W #160,D7; ORI.W #400,54aa(A5)` (→`46864`)
- `46864`: `MOVE.W D7,54b0(A5); MOVE.W D6,54b2(A5); CLR.B 54b4(A5); SWAP D0; SWAP D1; CLR.L 54b6(A5); TST.L D3; BNE 4688a`
- `4687e`: `TST.L D2; BNE 468b6` / `46884`: `MOVE.W (A7)+,54de(A5); RTS`
- `4688a`: `BSR 4662e`(경계) / `4688e`: `MOVE.L D2,D4; OR.L D3,D4; BEQ 46884` / `46894`: `TST.B D6; BEQ 468a2` / `4689a`: `CLR.W 54de(A5); BRA 468b6`
- `468a2`: `TST.L D3; BEQ 468b6` / `468a8`: `MOVE.L D2,D5; BMI 468b0` / `468ae`: `NEG.L D5` (→`468b0`) / `468b0`: `ADD.L D5,54b6(A5); BPL 4688a`
- `468b6`: `BSR 46372` / `468ba`: `MOVE.L D2,D4; OR.L D3,D4; BEQ 46884` / `468c0`: `TST.B D6; BEQ 468cc` / `468c6`: `CLR.W 54de(A5); BRA 4688a`
- `468cc`: `TST.L D2; BEQ 4688a` / `468d0`: `MOVE.L D3,D5; BPL 468d8` / `468d6`: `NEG.L D5` (→`468d8`) / `468d8`: `ADD.L D5,54b6(A5); BPL 4688a` / `468de`: `BRA 468b6`

**화면 경계 clamp `468e0` 21**
- `468e0`: `MOVEA.L 54a6(A5),A1; MOVEQ #0,D6; ADD.L D0,D2; ADD.L D1,D3; TST.B 54a2(A5); BNE 46938`
- `468f2`: `MOVE.L 53bc(A5),D4; ADD.L 53a2(A5),D4; MOVE.L D4,D5; SUB.L D4,D0; SUB.L D5,D2; MOVEQ #0,D7; MOVE.W (A1),D7; SWAP D7; CMP.L D0,D7; BLE 4690e` / `4690c`: `MOVE.L D0,D7`
- `4690e`: `CMP.L D7,D2; BGE 4691a` / `46914`: `MOVE.L D7,D2; MOVE.B #ff,D6`
- `4691a`: `SWAP D7; ADD.W 4(A1),D7; SWAP D7; CMP.L D0,D7; BGE 4692a` / `46928`: `MOVE.L D0,D7`
- `4692a`: `CMP.L D7,D2; BLE 46934` / `46930`: `MOVE.L D7,D2; MOVEQ #-1,D6` / `46934`: `ADD.L D4,D0; ADD.L D5,D2`
- `46938`: `TST.B 54a3(A5); BNE 46992`
- `46940`: `MOVE.L 53c0(A5),D4; ADD.L 53a6(A5),D4; MOVE.L D4,D5; SWAP D4; SUB.W 5404(A5),D4; ADD.W 5406(A5),D4; SWAP D4; SUB.L D4,D1; SUB.L D5,D3; MOVEQ #0,D7; MOVE.W 2(A1),D7; SWAP D7; CMP.L D1,D7; BLE 4696a` / `46968`: `MOVE.L D1,D7`
- `4696a`: `CMP.L D7,D3; BGE 46974` / `46970`: `MOVE.L D7,D3; MOVEQ #-1,D6`
- `46974`: `SWAP D7; ADD.W 6(A1),D7; SWAP D7; CMP.L D1,D7; BGE 46984` / `46982`: `MOVE.L D1,D7`
- `46984`: `CMP.L D7,D3; BLE 4698e` / `4698a`: `MOVE.L D7,D3; MOVEQ #-1,D6` / `4698e`: `ADD.L D4,D1; ADD.L D5,D3` / `46992`: `RTS`

**이동 금지 bit `4bb22` 9**
- `4bb22`: `MOVE.B 6d(A6),D7; BPL 4bb2c` / `4bb2a`: `RTS`
- `4bb2c`: `BCLR #4,D7; BEQ 4bb3c` / `4bb34`: `TST.L D2; BPL 4bb3c` / `4bb3a`: `MOVEQ #0,D2`
- `4bb3c`: `BCLR #5,D7; BEQ 4bb4c` / `4bb44`: `TST.L D2; BMI 4bb4c` / `4bb4a`: `MOVEQ #0,D2`
- `4bb4c`: `MOVE.B D7,6d(A6); RTS`

**지형 조건 초기화 `4bc44` 6**(F4 N35에서 두 번째 진입 `4bc58`로 나눔)
- `4bc44`: `CLR.B 549f(A5); CLR.B 54a0(A5); MOVE.B #ff,54a2(A5); MOVE.B #ff,54a3(A5)` (→`4bc58`)
- `4bc58`: `MOVE.B #0,549d(A5); MOVE.B #0,549e(A5); MOVE.B #2,549c(A5); BTST #4,15(A6); BEQ 4bc7a`
- `4bc74`: `MOVE.B #1,549c(A5)` / `4bc7a`: `BTST #3,15(A6); BEQ 4bc8a` / `4bc84`: `MOVE.B #0,549c(A5)`
- `4bc8a`: `BTST #5,61(A6); SNE 54a4(A5); BTST #4,61(A6); SNE 54a5(A5); RTS`

**C4 `4be34`/`4be82`와 공통 꼬리 26**
- `4be34`: `JSR 4bc44(PC)` / `4be38`: `MOVE.B #0,10d49d.L; MOVEM.L 2e(A6),D0-D3/A0; JSR 4bb22.L` / `4be4c`: `BRA 4bf0a`
- `4be82`: `JSR 4bce0(PC)`(경계) / `4be86`: `MOVE.B #0,10d49d.L; MOVEM.L 2e(A6),D0-D3/A0; JSR 4b8e8.L`(경계)
- `4be9a`: `ADD.B D7,D7; BCC 4beec` / `4bea0`: `JSR 469d8.L`(경계, U09)
- `4bea6`: `MOVE.L 36(A6),D2; MOVE.L 3a(A6),D3; MOVEA.L 3e(A6),A1; CMPA.W #0,A1; BEQ 4beca`
- `4beba`: `ADD.L 14(A1),D2; SUB.L 1c(A1),D2; ADD.L 18(A1),D3; SUB.L 20(A1),D3`
- `4beca`: `CMPA.W #0,A0; BEQ 4bee2` / `4bed2`: `SUB.L 14(A0),D2; ADD.L 1c(A0),D2; SUB.L 18(A0),D3; ADD.L 20(A0),D3`
- `4bee2`: `MOVEM.L D0-D3/A0,2e(A6); BRA 4bf16`
- `4beec`: `BEQ 4bf0a` (Z=`4be9a`의 `ADD.B` 결과 0, 결정 3)
- `4bef0`: `MOVE.L #40000,D4; TST.B D7; BMI 4befe` / `4befc`: `NEG.L D4` / `4befe`: `MOVE.L #60000,D3; NEG.L D2; ASR.L #1,D2; ADD.L D4,D2`
- `4bf0a`: `JSR 469d8.L`(경계) / `4bf10`: `MOVEM.L D0-D3/A0,2e(A6)` (→`4bf16`)
- `4bf16`: `MOVE.B 15(A6),D0; MOVE.B 61(A6),D1; ANDI.B #5f,D0; ANDI.B #fc,D1; BTST #7,D6; BEQ 4bf38` / `4bf2e`: `ORI.B #80,D1; MOVE.B #18,5e(A6)`
- `4bf38`: `BTST #0,D6; SNE D5; ANDI.B #80,D5; OR.B D5,D0; BTST #1,D6; SNE D5; ANDI.W #20,D5; OR.B D5,D0; BTST #2,D6; SNE D5; ANDI.B #1,D5; OR.B D5,D1; BTST #3,D6; SNE D5; ANDI.B #2,D5; OR.B D5,D1; MOVE.B D0,15(A6); MOVE.B D1,61(A6); MOVEM.L D4/D6-D7,-(A7); LSR.L #8,D7; MOVE.W D7,6e(A6); JSR 43e34.L`
- `4bf80`: `BTST #7,15(A6); BNE 4bf98` / `4bf8a`: `JSR 1aa3a.L` / `4bf90`: `ANDI.W #c8,D0; BEQ 4bf9e` / `4bf98`: `JSR 492c8.L`(경계)
- `4bf9e`: `MOVEM.L (A7)+,D4/D6-D7; RTS`

(block 수: 1+79+24+21+9+6+26 = 166.)

## 구현 범위와 규약

- routing 7 범위(위 표). 짝수 PC 754개 중 block 시작 166, 내부 588. 내부 PC 직접 진입은 `unsupported animation objects u08b PC`다. 경계 callee 8개와 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다. 홀수 PC는 `unaligned animation machine PC`다.
- 조건 판정은 원본 flag 그대로 계산한다(크기별 명시, 미정의 동작 없음). `ADD`의 V=((¬(s⊕d))∧(d⊕r))의 최상위 bit, `SUB`/`CMP`의 V=((s⊕d)∧(d⊕r))의 최상위 bit(r=d−s), `SUBQ.W #8`·`CMPI.W`의 C=(d <u s), `ADD.B D7,D7`의 C=bit 7. `BLE`=Z∨(N≠V), `BGE`=(N=V). `NEG.L`·`ASR.L #1`은 32bit 2의 보수·산술 이동이다. `BTST #n,Dn`·`BCLR #n,Dn`은 bit n(mod 32), 메모리 `BTST #n,d16(A6)`은 BYTE bit n(mod 8)이다.
- `SUBX.L D4,D4`(block `46398`/`464ac`): X=(`ADDI.L #80000000,D6`의 carry)=원래 D6 bit31. D4=0−0−X. 이후 명령이 X를 다시 정하지만 block 밖에서 쓰이지 않는다.
- **carry.** [F] U08b 함수 9개의 ROM 정적 호출(BSR/JSR/BRA) 뒤 흐름을 C 보존 명령(`BTST`/`BCLR`/`BRA`/`LEA`/`MOVEM`/Z·N·V Bcc)을 따라 최대 12명령 검사했다(`461ec` 2, `46372` 1, `4683c` 1, `468e0` 1, `4bb22` 3, `4bc44` 14, `4be34` 260, `4be82` 32, `4bf16` 1곳). C 소비 명령(`BCC`/`BCS`/`BHI`/`BLS`/`Scc`/`ADDX`/`SUBX`/`ROXL`/`ROXR`)에 먼저 닿는 곳은 없다(유일한 CCR 명령 `7918c ORI.B #1,CCR`은 C를 새로 정한다). 호출자 `RTS`로 이어지는 곳의 바깥 소비는 그 호출자 단위가 정한다(관례대로 Unknown). 경계 callee 뒤 첫 명령(`46388 SUBI` `463b8 BSR` `463bc MOVEQ` `4649c SUBI` `464ce MOVE` `4688e MOVE` `4be86 MOVE` `4be9a ADD` `4bea6 MOVE` `4bf10 MOVEM`→`4bf16 MOVE` `4bf9e MOVEM`→`RTS`)도 C를 소비하지 않는다. 따라서 known 생산 block을 두지 않는다.
- **C 소비 block 7개(모두 block 안 생산)**: `463ee` `464ce` `46572`(`SUBQ.W #8,D4; BCS`), `46428` `46506` `465aa`(`CMPI.W #160,D7; BCS`), `4be9a`(`ADD.B D7,D7; BCC`).
- **FLOW_ONLY 27개**(C 보존): BSR/JSR/BRA/RTS만 `46384` `463b4` `463b8` `46498` `464c6` `464ca` `4688a` `468b6` `468de` `46992` `4bb2a` `4be34` `4be4c` `4be82` `4bea0` `4bf0a` `4bf8a` `4bf98`; `MOVEM`(+BRA/RTS) `4bee2` `4bf10` `4bf9e`; Z만 바꾸는 `BCLR`/`BTST`+Bcc `4bb2c` `4bb3c` `4bc7a` `4bf80`; `BTST`/`SNE`/`RTS` `4bc8a`; Bcc만 `4beec`. 나머지 138개는 Unknown이다.
- 스택: `MOVE.L D5,-(A7)`·`MOVE.W 54de(A5),-(A7)`는 `am_push`(LONG/WORD), `MOVE.L (A7)+`·`MOVE.W (A7)+`는 `am_pop`, `MOVEM.L D4/D6-D7,-(A7)`은 낮은 주소부터 D4, D6, D7(A7−12)이고 `MOVEM.L (A7)+,D4/D6-D7`은 같은 순서로 읽고 A7+12다. 홀수 A7·work RAM 밖 쓰기는 기존 checked 오류다.
- `MOVEM.L 2e(A6),D0-D3/A0` 읽기와 `MOVEM.L D0-D3/A0,2e(A6)` 쓰기는 D0,D1,D2,D3,A0 순서(`2e` `32` `36` `3a` `3e`)다. `ORI.W #n,54aa(A5)`·`ADD.L D5,54b6(A5)`는 읽기-연산-쓰기다(`BPL`은 ADD 결과 N).
- `461ec`는 `461f2`+sext(`D7.W`)를 bus WORD로 읽고 `D7.W`만 바꾼다(결정 2).

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, 기본 120 frame)에서 U08b block에 TB로 닿는 seed는 59개(0 1 6~9 12~23 34~37 42 43 56 57 62 63 68~71 76 77 80~83 88 89 96~99 102~105 116 117 127~135)다. TB 시작 기준 165 block 중 62개가 자연 도달한다. 미도달 103개(`46372` 결과 처리 세 벌의 대부분, `4be82` 경로 전체, `468e0`의 clamp 본문, `4bb22` 본문 등)는 typed fixture와 실제 ROM 차분으로 덮는다. [I] 자연 호출은 `4be34`(C4 callback의 공통 갱신)와 U09 `469d8` 안의 `461ec`/`4683c`/`468e0` 호출이다. 이 작업 트리(U09 없음)에서 C++ 프레임 패스는 `4be34`→`4bf0a JSR 469d8`(U09 경계)에서 멈추므로 [I] U08b만으로 새 완주 seed는 없다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 165 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), zero-step, 내부 589 PC 정확한 오류, 홀수 PC, 경계·이웃 오류. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, 필요한 ROM 자료는 합성 바이트 overlay)로 비교한다. SUBX의 X 양쪽, `BVC`·`BLE`·`BGE` 경계값, `4beec` Z 양쪽, `461ec` 홀수 index 오류를 포함한다.
- 실제 ROM 차분: `461ec`(96 index와 `160`), `46372`(D2·D6·D7·`54b4`·`54ae`·`54a4/5` 조합, `447be`/`4483a`까지 실제 ROM으로), `468e0`(실제 ROM 사각형 `4bca0..4bce0`과 RAM 사각형), `4683c`(D2=D3=0 경로와 `4662e` 경계까지), `4bb22`, `4bc44`, `4be34`·`4bf16`(경계 `469d8`·`492c8`까지)을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed): `b4ba243` 기준(일치 pass 9,776, 일치 node 73,326/73,328, 불일치 seed 2(58·59, 기존 U06 PVC 경로), 자연 완주 58) 회귀 0이고, 첫 미연결 callback 분포 변화를 보고한다.

## 두 번째 진입 `4bc58`(F4 N35에서 추가)

- [F] N33 `4bdfe MOVEM.L (A7)+,D0-D7; BRA.W 4bc58`(ROM 참조 `4be02` 하나)이 block `4bc44`의 다섯 번째 명령으로 들어간다(N33 계약 결정 5). `4bc44`를 앞 4 명령(후속 `4bc58`)과 `4bc58`(뒤 3 명령 + `BTST`/`BEQ`)로 나눴다. 실행 의미·쓰기 순서는 같고 둘 다 Unknown(MOVE)이며 FLOW 27은 그대로다. block 165 → 166, 내부 589 → 588.
- [F] 단위 test: BLOCKS `4bc44` 행(후속 `4bc58`)과 새 `4bc58` 행, fixture `4bc58-0` `-10` `-08` `-18`(`549f` `54a0` `54a2` `54a3`은 그대로 남음)을 Unicorn으로 만들었다. 같은 scratch 생성기(`ms5-scratch/n35/u08b/gen_u08b.py`)가 기존 BLOCKS 165행과 성공 fixture 231개를 먼저 바이트 단위로 재현했다.

## 미확인·범위 밖

1. [I] `46372`는 D2(x 이동량)를 `80000`으로 자르며 지형 코드(`447be`)·기울기(`4483a`)와 경계 callee `44ade`/`45b12`/`4578a`로 한 걸음씩 지형을 따라 이동하는 함수, `4683c`는 그 loop(`4662e`는 y 방향 짝으로 보임), `468e0`은 `54a6(A5)` 사각형과 화면 기준(`53a2..53c0`)으로 위치를 자르는 함수, `461ec` 표는 지형 코드별 기울기 값으로 보인다. 게임 의미는 미확인이다.
2. [U] `461ec` 진입 D7의 전 호출 closure(결정 2로 실행 의미는 정해진다).
3. [U] 경계 callee 8개의 반환 레지스터·flag 범위. 각 경계 뒤 첫 명령은 C를 소비하지 않는다(위 carry).
4. 범위 밖: 경계 callee 8개(`469d8`은 U09, `44ade`는 U20), `4be50..4be82`·`4bfa4..` 다른 C4 함수(이 단위의 `4bf0a`/`4bb22`로 들어옴).

작업자 scratch: 세션 scratchpad `f4u08b/`(`u08b.py` block·범위·SHA 계산, `cchain.py` 호출 뒤 C 검사, `bccrefs.py` 분기 대상 전수 검사, `reach.py`; 저장소 밖).
