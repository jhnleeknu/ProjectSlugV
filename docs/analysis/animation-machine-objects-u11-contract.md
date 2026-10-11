# 객체 callback F4 U11: 지형 높이 표 `45176`(96 entry 전체), 지형 사각형 `47288`, C3 판정 `49370`/`497b6`/`496c2`, C4 `4be06`, `be8a4` 객체 계열 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U11 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`), U08 계약(`animation-machine-objects-u08-contract.md`, SHA256 `fd484c1cc1bcd87a87f69892451a1cfd36528db5797cca7298514c8c1f703d8d`, 점프 표 `4483a`의 계산 PC 정책), U09 계약(SHA256 `ec78145959a74817246f18fef52536792b95e6e3a29d3d253584fe6e1a5b01fa`), U10 계약(SHA256 `2b3c1f73213c12bb8f3b5512968210e99d1986a04b90321ce48e99c0fa98147c`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `MOVE.L #imm,(A6)` callback 진입, 점프 표 entry)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 4: 지형 점프 표는 index 상한을 정적으로 확정하고 표 전체를 옮긴다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee는 실행부 없는 경계(`unsupported animation machine PC`)다.
- 결정 6: `TRAP #f`는 실행부 없는 checked 경계다.
- U01~U10 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U11에는 없음). `MOVE.x`/`MOVEQ`/`TST`/`CMP`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). `LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`와 callee C를 소비하는 단독 Bcc만인 block은 FLOW_ONLY다. `ADDQ`/`ADDA` An block은 Unknown이다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U11의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료(`2001e0`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u11`(HEAD `5f51050` = U01~U09 + U08a + U08b WIP, `engine/src/animation_machine.cpp` SHA256 `b9ff8267049d27ae4c1d058bf06561075386d0c74076bd0c5334fdf0239eca34`, routing 규칙 44개)을 참조했다. U10(다른 작업 트리 `metalslug-u10`)은 이 작업 트리에 없다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u11/u11.py`가 원본 opcode에서 독립 계산했고 아래 목록과 같음을 assert했다.

## 요약

- [F] U11은 **block 시작 215개 + TRAP 경계 1개(`4937c`)**다.
  - 점프 표 함수 `45176`(`JMP 4517a(PC,D7.W)`) 1, 표 entry 96(`4517a+4k`, k=`0..5f`, 모두 `BRA.W`), 표 대상 본문 `452fa..4578a` 60.
  - 지형 사각형 `47288` 4, C3 `49370` 4·`496c2` 1·`497b6` 12, C4 `4be06` 3.
  - 객체 계열 34: `be888` 5, callback `be8a4` 17(`be8a4..be98e`), `beab4` `beaba`와 설치 callback `beac0` `beac6` `bead0` 5, 자식 callback `bead4` 4, 설치 callback `beb52` 3.
  - 코드 9 범위, 2,218바이트, 640명령이다. 미해독·레지스터 간접 점프·묶인 Bcc·SUBX/ADDX는 없다. PC 상대 점프 표는 `45176` 하나다. routing 짝수 PC는 1,109개, 내부 PC는 894개다.
- [F] **범위 문서 72와의 차이(+143)**: 범위 문서의 72(scratch `f4scope/units.pkl`에서 다시 계산)는 아래 10개를 빼면 62개가 모두 U11 목록에 있다.
  - +153: 결정 4. 범위 문서는 `45176` 표에서 자연 관측 entry(`45206` `452da`)와 그 대상 `452fa`만 셌다. U08a(`4483a`)와 같이 나머지 entry 94개와 대상 본문 59개(`45302..4578a`)를 옮긴다. 범위 문서 U12 `452ea..45310`, U15 `452e2..45310`, U20 `452de..45330`의 표 부분도 여기 들어온다.
  - −4: 이미 U08a가 routing한 `448ca`(표 entry) `449be` `449d8` `449dc`(표 대상).
  - −2: 이미 U09가 routing한 `471ec` `471fa`(`DBRA` 대상).
  - −2: `46efe`와 TRAP `46f06`. cleanup 실행부의 `46ef4` block(`MOVEQ`/`MOVE.B`/`BMI`/`CMPI.W #8`/`BCS`, TRAP `46f06`은 그 block의 checked 오류 `animation cleanup original TRAP15: coordinate index`)의 안쪽 명령이다. ROM 어디에도 `46efe`로 가는 정적 분기·호출·LONG 상수가 없다(`refs.py` 0건). 범위 문서는 TB 시작을 세었다. 기존 실행부 block 안의 코드는 다시 routing하지 않는다(아래 결정 3).
  - −1: TRAP `4937c`(결정 6, block이 아니라 경계).
  - −1: U10 소유 `bac5c`(범위 문서 U11의 대표 callback). `bac5c`는 U10 범위 `babb4..bb012` 안의 설치 callback이고 U10 계약이 이미 셌다. 지시대로 U10 소유로 두고 U11에서 세지 않는다(아래 결정 2).
- [F] **경계 callee(실행부 없음) 2개**: `4941e`(`497c8`/`497dc`의 `JSR 4941e(PC)`, C 반환), `44c62`(`45306 BNE.W 44c62`, 다음 점프 표 함수 `44ade`(U20 범위)의 꼬리). 범위 문서의 "경계 callee 5"는 `bac5c` 계열(`eb774` `1aa40` `492c8` `4c266`, U10 경계)을 포함한 값이다.
- [F] 기존 실행부로 나가는 호출: U08b `4bc44`(JSR)·`4bf16`(BRA), U09 `469d8`·`4706c`, frame_helpers `49392`(C 반환), U05 `1ab02`(C 반환)·`c6a96`, cleanup `46ef4`·`2a24`(JMP)·`43e34`, fade_card `28ae`(자식 생성 6회)·`2a00`(JMP), U08a `49290`, interpreter `49f8c`·`49fc6`. U11 안 호출: `497b6 JSR 49370(PC)`, `beab4 JSR 496c2.L`, `beac0 JSR 4be06.L`.
- [F] U11 → 기존 실행부 출구 둘이 기존 공백에 닿는다.
  - `bead4 JSR 49290`(U08a `MOVEA.L c(A6),A1; LEA 2e(A1),A1; JMP 43e04`)의 `43e04`는 cleanup routing 범위(`43dcc..43ea2`) 안이지만 cleanup 실행부에 `43e04` case가 없다(U10 계약이 먼저 보고).
  - `be89c JMP 2a24`의 `2a24`(`BSR 2a0a; BRA 2a00`)도 cleanup routing 범위(`2a0a..2aaa`) 안이지만 cleanup 실행부에 `2a24` case가 없다(U05 `b9756 JMP 2a24`도 같다).
  - [I] 그래서 C++의 `bead4` 경로는 `43e04`에서, `be888`의 화면 밖 삭제 경로는 `2a24`에서 `unsupported animation machine PC`로 멈춘다. U11 범위 밖이다(메인 판단 필요, 아래 결정 7).
- [F] **known carry 생산 block 4개**(`49386` `497e4` ORI CCR Set, `4938c` `497ea` ANDI CCR Clear; 각 block이 RTS까지 포함)와 **block 경계를 건너는 C 소비 block 6개**(`497ba`←`49370`, `497c4` `497d8`←`49392`, `497cc` `497e0`←`4941e` 경계, `be892`←`1ab02`).
- [F] 읽는 자료: fixed ROM 표 `be874`(WORD, `be8a4`), `be808`(LONG, `be8ce`), `beb7a`·`beb86`(WORD, `bead4`/`beb36`/`beb58`), `47288`의 사각형 record(`26(A0)`가 가리키는 주소, live bus), banked window LONG `2001e0`과 그 값 + `4·(76(A6)+14)`의 LONG(`beafe`, 2곳). 모두 live bus로 읽는다. fixed ROM 주소 `be3e4`(→`1ab02` A0)는 U11이 읽지 않고 주소만 넘긴다. I/O port 쓰기와 bank 변경은 U11 자체에 없다.
- [F] 자연 seed(범위 scratch 재생 `f4scope/dyn`, base 120 frame): `be8a4` 계열 callback(`be8a4` `bead4` `beac0` `beb52`)은 seed 82 83 88 89, `497b6`은 seed 20 21(U10 `bac62`에서), `47288`·`45176`·`4be06`·`49370`은 50개 seed에서 닿는다. 기준 C++ 차분(작업 트리 `5f51050`)에서 첫 미연결 callback이 `be8a4`인 seed가 4개(82 83 88 89)다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 정정(72→215).** 결정 4에 따라 표 `45176`의 96 entry와 대상 본문을 모두 옮기고(U08a `4483a`와 같음), 설치 callback 경로를 넣는다(권고). 지시 상한(~220) 안이므로 나누지 않는다. 범위 문서는 고치지 않는다.
2. **`bac5c`는 U10 소유.** [F] `bac5c`는 U10 routing 범위 `babb4..bb012` 안이고 U10 계약 block 목록에 있다(`bac5c: JSR 4be06.L`). U11에서는 세지도 routing하지도 않는다(지시대로). U10의 경계 `4be06` `497b6`은 U11이 실행한다. 두 단위가 병합되면 `bac5c`→`4be06`→`4bc44`/`469d8`과 `bac62`→`497b6`→`bac6e`(U10 C 소비자)가 연결된다.
3. **`46efe`/`46f06`은 다시 routing하지 않는다.** cleanup `46ef4` block 안쪽이다(위 요약). U11 범위에 넣지 않는다(권고, 관례).
4. **표 `45176`의 C++ 형태(U08 결정 2와 같음).** `45176`은 PC=`4517a`+sext(`D7.W`)로만 옮긴다(32bit 덧셈). 96 entry의 `BRA.W` 대상은 C++ 상수 배열로 옮겨 적는다(코드 바이트를 자료로 읽지 않음). 상한 밖 값은 routing이 정한다: 표 안 displacement WORD(`4517a+4k+2`)와 대상 본문 내부는 `unsupported animation objects u11 PC`, 홀수는 `unaligned animation machine PC`, 범위 밖은 `unsupported animation machine PC`(또는 다른 실행부), `D7.W`=`fffc`이면 `45176` 자신(원본도 무한 반복, C++는 `animation machine block budget exceeded`). 대상이 명령 중간 WORD이면 원본은 그 WORD부터 디코드하지만 C++는 checked 오류로 멈춘다(의도된 차이, 상한 밖 D7에서만 생김).
5. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u11.cpp`의 `animation_objects_u11_block`. 오류는 `unsupported animation objects u11 PC`(내부 PC), `objects u11 caller requires known carry`(6 소비자). 메인 지시와 같다.
6. **`ASR.W #3`(`4728c` `4728e`)·`ASR.L #1/#2/#3`(표 대상 32곳).** 산술 shift를 부호 채움으로 명시 구현한다(C++ 부호 있는 shift에 기대지 않음).
7. **`43e04`·`2a24` 공백(U11 범위 밖).** `bead4`는 `49290`→`43e04`에서, `be888`(C Set 경로)은 `46ef4` 뒤 `2a24`에서 멈춘다. 메인이 cleanup 실행부의 `43e04` 진입(`LEA 2e(A6),A0` 뒤 `43e08`)과 `2a24` 진입(`BSR 2a0a; BRA 2a00`)을 다룰지 결정해야 한다. U11은 이 PC들을 routing하지 않는다(기존 실행부 범위 안).
8. **무효화 탐침 교체.** 아래 "회귀 탐침" 4곳을 고친다(교체 PC `5f800` `5f802`, 어느 `docs/analysis` 문서에도 없음).

## 원본 바이트 근거

[F] 코드 9 범위 합계 2,218바이트(`4937c` TRAP 2바이트 제외). 범위 순서로 이어 붙인 SHA256 `ccbb86a7033f746fadb6aab4300b01ea01c0681903625bd15384f651e7f05db4`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `45176..4578a` | 1556 | `2d94b79a4df218e68858970d703b7415939efa95e93d4d2fdccdf6677c2a973f` | `JMP` `45176`, 표 entry `4517a..452fa`, 대상 `452fa..4578a` |
| `47288..472be` | 54 | `e9f31f639750b7bdd6d139eb5bd2e0fc2ac13a101a71ca0f61b020bb20bb98c3` | 지형 사각형 `47288` |
| `49370..4937c` | 12 | `ee09ec3eda929691f36b39d71876fd49c80522bfd918a117ecf53448909b4bbc` | C3 `49370` 앞부분 |
| `4937e..49392` | 20 | `2169bbe2aa5770a52810730fa16d9e3780dd10b61297dc506efb4dd8f4cf7805` | C3 `49370` 뒷부분 |
| `496c2..496d2` | 16 | `efce185aa5ffec74edece4097062ce9de43dca5791aa241fc44acff2b0872f28` | C3 `496c2` |
| `497b6..497f0` | 58 | `276f3970fc39425e6235cc3d0d1781866ecad30014413322934d42cbd85cbe84` | C3 `497b6` |
| `4be06..4be2c` | 38 | `1b5a8e0f98ad6353936fab63c39f7328cf15e2e439b9291b2a5983adceccd30d` | C4 `4be06` |
| `be888..be992` | 266 | `927ccdcfac3895c7dcfa346d83b2db81dfbe21b9f9340d144e7c4fde4fc29c30` | `be888`, callback `be8a4` |
| `beab4..beb7a` | 198 | `fd83168641ec039f3675f6f4815e85eed6be96a9e2d247224eeb3b6a4fe876a1` | `beab4`/`beac0`, 자식 `bead4`/`beb52` |

- [F] 범위 밖 이웃(routing 밖): `45174`(앞 함수 `RTS`), `4578a`(다음 표 함수, 범위 문서 U15), `47286`(U09 `4727a` block 안), `472be`(자료/다른 함수), `4936e`(앞 함수), TRAP `4937c`, `49392`(frame_helpers 실행부), `496c0` `496d2`(다른 함수), `497b4`(U20 범위 `497a6` 함수), `497f0`(다른 함수), `4be04`(앞 함수 `BRA`), `4be2c`(다른 C4 함수, U08b `4be34`의 앞), `be886`(자료 `be874..be888`), `be992..beab4`(다른 객체 경로; `beaaa`가 `beab4`를 설치하지만 U11에서 닿지 않음), `beb7a..`(WORD 자료 `beb7a` `beb86`).
- [F] 자료(모두 live bus):
  - fixed ROM: `be874+4·76(A6)`(WORD → `8a(A6)`), `be876+4·76(A6)`(WORD → `8c(A6)`, `7a(A6)`=0일 때), `be808+4·76(A6)`(LONG → `86(A6)`; 값 `be5a2` `be612` `be670`은 `beac6`이 `4706c`에 넘기는 지형 사각형 record), `beb7a+2·76(A6)`(WORD → `49290` D0), `beb86+2·76(A6)`(WORD → `68`/`1e(A6)`). [F] 표 값: `be874` `ff91 fff0 0000 fff0 006f fff0`, `be808` `000be5a2 000be612 000be670`, `beb7a` `ff90 ffb0 ffd8 0028 0058 0070`, `beb86` `ffe0 ffe8 fff8 fff8 ffe8 ffe0`. [I] `be8a4`의 `76(A6)`은 0~2, `bead4`의 `76(A6)`은 `be8a4`가 넣는 0~5다(그 밖 값은 원본 그대로 live bus가 정한다).
  - `47288`의 record: A4=LONG `26(A0)`; WORD `(A4)` `2(A4)` `4(A4)` `6(A4)` `8(A4)`와 행 표 WORD `a(A4)+sext(2·D5.W)`, BYTE `a(A4)+sext(행 WORD+D4.W)`. [I] record는 `4706c`/`47070`이 슬롯 `26(slot)`에 넣은 포인터(fixed ROM `be5a2` 등)다.
  - banked window: `beafe`의 `MOVE.L 2001e0.L,22(A6)`과 `MOVEA.L 2001e0.L,A1; MOVEA.L (A1,D1.W),A1`(D1.W=4·(`76(A6)`+`14`)). [F] bank `200000`에서 LONG `2001e0`=`002d55ac`, 그 표 LONG(index `14..19`)=`2d56ae` `2d56be` `2d56ce` `2d56de` `2d56ee` `2d56fe`(bank `300000`이면 `052a9f60`, 두 번째 읽기는 physical span 밖 → 기존 checked 오류).
  - work RAM: BYTE `549e(A5)`(`45302`), `568e(A5)`(`4937e`). 노드 d16(A6): WORD `76` `7a` `46`, LONG `2e`/`32`(MOVEM) `36` `3a` `3e` `64` `86`, WORD 쓰기 `8a` `8c` `20` `68` `1e`, LONG 쓰기 `22` `(A6)`(callback 설치). 자식 node d16(A0): WORD `76`.
- [F] 스택: JSR/BSR 복귀 LONG뿐이다. `45176`의 대상은 RTS로 `45176`을 부른 쪽에 돌아간다(`45302` `BNE 44c62`는 같은 복귀를 `44c62`에 넘긴다).

## 점프 표 `45176`과 index 상한(결정 4)

- [F] `45176`: `JMP 4517a(PC,D7.W)`(PC 상대 기준 `4517a`). 표 `4517a..452fa`는 96개 `BRA.W`(opcode `6000`)이고 바로 뒤 `452fa`는 `MOVE.L #80000000,D6; RTS`다. index(16진 k, `D7.W`=4k)→대상:
  - `00..1f`: `4560e` `45772` `456ca` `456b2` `45622` `4575a` `456e2` `4569a` `4563a` `45742` `456fa` `45682` `45652` `4572a` `45712` `4566a` `4566a` `45712` `4572a` `45652` `45682` `456fa` `45742` `4563a` `4569a` `456e2` `4575a` `45622` `456b2` `456ca` `45772` `4560e`(ASR.L #3 식).
  - `20..23`: `452fa` ×4.
  - `24..33`: `453a2` `45426` `453c0` `4533a` `4537e` `45404` `453e2` `4535c` `4535c` `453e2` `45404` `4537e` `4533a` `453c0` `45426` `453a2`(LSL.L #2 식, 범위 판정).
  - `34..3b`: `4546c` `454ac` `4548a` `45448` `45448` `4548a` `454ac` `4546c`(LSL.L #1 식).
  - `3c..3f`: `454ce` `454e0` `454e0` `454ce`.
  - `40..47`: `454f6` `4553a` `45522` `4550a` `4550a` `45522` `4553a` `454f6`(ASR.L #1).
  - `48..57`: `45552` `455f6` `455ae` `45596` `45566` `455de` `455c6` `4557e` `4557e` `455c6` `455de` `45566` `45596` `455ae` `455f6` `45552`(ASR.L #2).
  - `58..5f`: `452fa` `45330` `45310` `45320` `45310` `45302` `452fa` `452fa`(`58`=`D7` `160`).
- [F] 정적 호출자 6곳(모두 `BSR.W`): `46640` `4671a`(U15 `4662e` 함수), `46aca` `46b2c`(U09), `46e08` `46e6a`(U12 `46d72` 함수). `46aca` `46b2c` `46e08` `46e6a`는 바로 앞에서 `BSR 4483a`를 부르거나 `CMPI.W #160,D7; BEQ`로 건너뛴다. `4483a` 대상은 D7을 그대로 두거나 `449be`(`MOVE.W #160,D7`)로 간다(U08 계약). 따라서 이 4곳의 `D7.W`는 `447be` 결과 또는 그것을 쓴 `54b0(A5)`, 곧 `4k`(k<`60`) 또는 `160`이다(U08 계약 "점프 표 `4483a`와 index 상한"). 이 값은 모두 표 안 entry다(`160`→`452da`→`452fa`).
- [F] `46640` `4671a`는 바로 앞에서 `CMPI.W #160,D7; BEQ`로 `160`을 건너뛴다. 그 D7은 `4662e` 진입 D7 또는 `54b0(A5)`다. [U] 진입 D7 경로의 전 호출 closure는 확인하지 않았다. 결정 4의 계산 PC 정책이 그 밖 값도 원본과 같이 옮기므로 실행 의미는 상한 확정에 의존하지 않는다.
- [F] 대상 본문은 D0(x)·D1(y) LONG(상위 WORD 정수부, 하위 19bit 소수부 마스크 `7ffff`)에서 기울기 높이를 D6에 내는 leaf다. 범위 판정 대상(`4533a`..`454ac`)은 범위 밖이면 `452fa`(D6=`80000000`, "높이 없음")로 간다. D4는 scratch로 남는다. `45302`는 BYTE `549e(A5)`≠0이면 `44c62`(경계)로 간다.

## block 목록과 실행 의미

[F] 215 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)·`(An,Dn.W)`는 부호확장한다. `.B`·`.W` 연산은 나머지 bit를 보존하고 `MOVEQ`는 LONG 전체를 쓴다. `CMP`/`CMPI` 뒤 `BCC`/`BCS`는 무부호 비교, `BGT`는 부호 비교, `BNE`/`BEQ`는 Z다. `ASR`은 부호 채움, `LSL`은 0 채움이다.

**점프 표 `45176` 97 + 대상 60**
- `45176`: `JMP 4517a(PC,D7.W)` (계산 PC, 결정 4)
- `4517a+4k`(k=`0..5f`, 96 block): `BRA.W` 위 표의 대상
- `452fa`: `MOVE.L #80000000,D6; RTS`
- `45302`: `TST.B 549e(A5); BNE.W 44c62` (경계)
- `4530a`: `TST.L D3; BGT.W 45330` (부호 LONG `D3 > 0`)
- `45310`: `MOVE.L D1,D6; ANDI.L #7ffff,D6; SUBI.L #80000,D6; RTS`
- `45320`: `MOVE.L D1,D6; ANDI.L #7ffff,D6; SUBI.L #40000,D6; RTS`
- `45330`: `MOVE.L D1,D6; ANDI.L #7ffff,D6; RTS`
- 범위 판정형(앞 block + fall-through block, 각 2): 앞 block은 `MOVE.L #7ffff,D6; MOVE.L D0,D4; AND.L D6,D4; [ADDI.L #a,D4;] CMPI.L #b,D4; Bcc 452fa`, 뒤 block은 `[ADDQ.L #1,D4;] LSL.L #s,D4; AND.L D1,D6; SUB.L/ADD.L D4,D6; RTS`.
  - `4533a`/`45352`: a=`fffa0000`, b=`20000`, `BCC`, ADDQ, s=2, SUB. `4535c`/`45374`: a=`fffc0000`. `4537e`/`45398`: a=`fffe0000`. `453a2`/`453b6`: a 없음.
  - `453c0`/`453da`: a=`fffe0000`, b=`fffe0000`, `BCS`, ADDQ 없음, s=2, ADD. `453e2`/`453fc`: a=`fffc0000`. `45404`/`4541e`: a=`fffa0000`. `45426`/`45440`: a=`fff80000`.
  - `45448`/`45462`: a=`fffc0000`, b=`40000`, `BCC`, ADDQ, s=1, SUB. `4546c`/`45480`: a 없음.
  - `4548a`/`454a4`: a=`fffc0000`, b=`fffc0000`, `BCS`, s=1, ADD. `454ac`/`454c6`: a=`fff80000`.
- 직선형(1 block, RTS 포함): `MOVE.L #7ffff,D6; MOVE.L D0,D4; AND.L D6,D4; [ASR.L #s,D4;] ADDQ.L #1,D4 또는 ADDI.L #a,D4; AND.L D1,D6; SUB.L/ADD.L D4,D6; RTS`.
  - `454ce`: ADDQ #1, SUB. `454e0`: ADDI `fff80000`, ADD.
  - s=1: `454f6`(ADDQ, SUB) `4550a`(`40001`, SUB) `45522`(`fff80000`, ADD) `4553a`(`fffc0000`, ADD).
  - s=2: `45552`(ADDQ, SUB) `45566`(`20001`) `4557e`(`40001`) `45596`(`60001`)(SUB) `455ae`(`fff80000`) `455c6`(`fffa0000`) `455de`(`fffc0000`) `455f6`(`fffe0000`)(ADD).
  - s=3: `4560e`(ADDQ, SUB) `45622`(`10001`) `4563a`(`20001`) `45652`(`30001`) `4566a`(`40001`) `45682`(`50001`) `4569a`(`60001`) `456b2`(`70001`)(SUB) `456ca`(`fff80000`) `456e2`(`fff90000`) `456fa`(`fffa0000`) `45712`(`fffb0000`) `4572a`(`fffc0000`) `45742`(`fffd0000`) `4575a`(`fffe0000`) `45772`(`ffff0000`)(ADD).

**지형 사각형 `47288` 4**
- `47288`: `MOVE.W D0,D4; MOVE.W D1,D5; ASR.W #3,D4; ASR.W #3,D5; MOVEA.L 26(A0),A4; SUB.W (A4)+,D4; SUB.W (A4)+,D5; MOVE.W (A4)+,D6; CMP.W D6,D4; BCC.W 472b8` (무부호 `D4.W ≥ D6.W`)
- `472a0`: `MOVE.W (A4)+,D7; CMP.W D7,D5; BCC.W 472b8`
- `472a8`: `MOVE.W (A4)+,D7; ADD.W D5,D5; MOVE.W (A4,D5.W),D5; ADD.W D4,D5; ADDA.W D5,A4; MOVE.B (A4),D7; RTS`
- `472b8`: `MOVEQ #0,D6; MOVEQ #58,D7; RTS`

**C3 `49370` 4 + TRAP 경계**
- `49370`: `MOVEQ #0,D0; CMPA.L #108000,A5; BEQ.W 4937e` (아니면 TRAP `4937c` 경계)
- `4937e`: `MOVE.B 568e(A5),D0; BNE.W 4938c`
- `49386`: `ORI.B #1,CCR; RTS` (C Set 생산)
- `4938c`: `ANDI.B #fe,CCR; RTS` (C Clear 생산)

**C3 `496c2` 1**
- `496c2`: `EOR.L D0,D0; MOVE.L D0,36(A6); MOVE.L D0,3a(A6); MOVE.L D0,64(A6); RTS`

**C3 `497b6` 12**
- `497b6`: `JSR 49370(PC)`
- `497ba`: `BCS.W 497ea` (carry 소비: `49370` 반환 C)
- `497be`: `CLR.W D0; JSR 49392(PC)` (frame_helpers)
- `497c4`: `BCC.W 497d0` (carry 소비: `49392` 반환 C)
- `497c8`: `JSR 4941e(PC)` (경계)
- `497cc`: `BCS.W 497ea` (carry 소비: `4941e` 반환 C)
- `497d0`: `MOVE.W #1,D0; JSR 49392(PC)`
- `497d8`: `BCC.W 497e4` (carry 소비)
- `497dc`: `JSR 4941e(PC)` (경계)
- `497e0`: `BCS.W 497ea` (carry 소비)
- `497e4`: `ORI.B #1,CCR; RTS` (C Set 생산)
- `497ea`: `ANDI.B #fe,CCR; RTS` (C Clear 생산)

**C4 `4be06` 3**
- `4be06`: `JSR 4bc44(PC)` (U08b)
- `4be0a`: `MOVEM.L 2e(A6),D0-D1; MOVEA.L 3e(A6),A0; MOVEQ #0,D2; MOVEQ #0,D3; JSR 469d8.L` (U09)
- `4be1e`: `MOVEM.L D0-D1,2e(A6); MOVE.L A0,3e(A6); BRA.W 4bf16` (U08b)

**객체 계열 `be888`/`be8a4`/`beab4`/`beac0`/`bead4`/`beb52` 34**
- `be888`: `LEA be3e4(PC),A0; JSR 1ab02.L` (U05, C 반환)
- `be892`: `BCC.W be8a2` (carry 소비: `1ab02` 반환 C)
- `be896`: `JSR 46ef4.L` (cleanup)
- `be89c`: `JMP 2a24.L` (cleanup, 자기 삭제)
- `be8a2`: `RTS`
- `be8a4`: `MOVE.W 76(A6),D0; LEA be874(PC),A0; ADD.W D0,D0; ADD.W D0,D0; MOVE.W (A0,D0.W),8a(A6); TST.W 7a(A6); BNE.W be8c8` (callback 진입)
- `be8be`: `MOVE.W 2(A0,D0.W),8c(A6); BRA.W be8ce`
- `be8c8`: `MOVE.W #ffe8,8c(A6)` (→`be8ce`)
- `be8ce`: `MOVE.W 76(A6),D2; ADD.W D2,D2; ADD.W D2,D2; LEA be808(PC),A0; MOVE.L (A0,D2.W),86(A6); MOVE.W 76(A6),D0; BNE.W be918`
- `be8e8`: `MOVEA.L #bead4,A0; MOVE.W #a,D0; JSR 28ae.L` (자식 `bead4`)
- `be8f8`: `MOVE.W #0,76(A0); MOVEA.L #bead4,A0; MOVE.W #a,D0; JSR 28ae.L`
- `be90e`: `MOVE.W #1,76(A0); BRA.W be98e`
- `be918`: `CMPI.W #1,D0; BNE.W be950`
- `be920`: `MOVEA.L #bead4,A0; MOVE.W #a,D0; JSR 28ae.L`
- `be930`: `MOVE.W #2,76(A0); MOVEA.L #bead4,A0; MOVE.W #a,D0; JSR 28ae.L`
- `be946`: `MOVE.W #3,76(A0); BRA.W be98e`
- `be950`: `CMPI.W #2,D0; BNE.W be988`
- `be958`: `MOVEA.L #bead4,A0; MOVE.W #a,D0; JSR 28ae.L`
- `be968`: `MOVE.W #4,76(A0); MOVEA.L #bead4,A0; MOVE.W #a,D0; JSR 28ae.L`
- `be97e`: `MOVE.W #5,76(A0); BRA.W be98e`
- `be988`: `JMP 2a00.L` (fade_card 자기 삭제)
- `be98e`: `BRA.W beab4`
- `beab4`: `JSR 496c2.L`
- `beaba`: `MOVE.L #beac0,(A6)` (→`beac0`)
- `beac0`: `JSR 4be06.L` (설치 callback 진입)
- `beac6`: `MOVEA.L 86(A6),A0; JSR 4706c.L` (U09)
- `bead0`: `BRA.W be888`
- `bead4`: `LEA beb7a(PC),A0; MOVE.W 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.W #0,D1; JSR 49290.L` (자식 callback 진입; U08a)
- `beaec`: `MOVE.W #77,D0; MOVE.W #14,D1; MOVE.B #0,D2; JSR c6a96.L` (U05)
- `beafe`: `MOVE.W 76(A6),D0; ADDI.W #14,D0; LEA 26(A6),A0; MOVE.W #223,20(A6); MOVE.L 2001e0.L,22(A6); LEA 26(A6),A0; MOVE.W D0,D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L 2001e0.L,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.L` (bank 자료 2)
- `beb36`: `LEA beb86(PC),A0; MOVE.W 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D1; MOVE.W D1,68(A6); MOVE.W D1,1e(A6); MOVE.L #beb52,(A6)` (→`beb52`)
- `beb52`: `JSR 43e34.L` (설치 callback 진입)
- `beb58`: `LEA beb86(PC),A0; MOVE.W 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D1; ADD.W 46(A6),D1; MOVE.W D1,68(A6); MOVE.W D1,1e(A6); JSR 49fc6.L`
- `beb78`: `RTS`

(수: 표 함수 1·entry 96·대상 60=157, `47288` 4, `49370` 4, `496c2` 1, `497b6` 12, `4be06` 3, 객체 계열 34; 합 215.)

## 구현 범위와 규약

- routing 9 범위: `45176..4578a`, `47288..472be`, `49370..4937c`, `4937e..49392`, `496c2..496d2`, `497b6..497f0`, `4be06..4be2c`, `be888..be992`, `beab4..beb7a`. 짝수 PC 1,109개 중 block 시작 215, 내부 894(표 displacement WORD 96 포함). 내부 PC 직접 진입은 `unsupported animation objects u11 PC`다. TRAP `4937c`, 경계 callee 2개와 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **carry 소비 block 6개**: `497ba`(`49370` 반환 C: `49386` Set/`4938c` Clear), `497c4` `497d8`(frame_helpers `49392` 반환 C: `4939e` ANDI.W Clear, `493b6` ORI Set), `497cc` `497e0`(경계 `4941e` 반환 C; 경계가 실행되기 전에는 선언 C로만 진입), `be892`(U05 `1ab02` 반환 C: `1ab7a` ANDI CCR Clear, U01 `1aafc` ORI CCR Set). Unknown이면 `objects u11 caller requires known carry`.
- **known carry 생산 block 4개**: `49386` `497e4`(Set), `4938c` `497ea`(Clear). block이 RTS까지 포함하므로 반환 C는 호출자 쪽 다음 block(`497ba`, U10 `bac6e`, 그 밖 정적 호출자의 Bcc)이 소비한다. [F] `49370`의 ROM 정적 호출자 33곳 중 24곳, `497b6`의 3곳(`ba296` `bac68` `bf992`) 모두가 바로 뒤 `BCS`/`BCC`로 C를 쓴다(`nextins.py`). `45176` `47288` `496c2` `4be06`의 호출자 바로 뒤 명령은 C를 읽지 않는다.
- **FLOW_ONLY 119개**(C 보존, 소비 6개 포함): `45176`(JMP), 표 entry 96(`BRA.W`), `497b6` `497c8` `497dc` `4be06` `be896` `beab4` `beac0` `beb52`(JSR), `be888`(LEA+JSR), `beac6`(MOVEA+JSR), `497ba` `497c4` `497cc` `497d8` `497e0` `be892`(소비 Bcc), `be89c` `be988`(JMP), `be98e` `bead0`(BRA), `be8a2` `beb78`(RTS). 그 밖 92개(MOVE/MOVEQ/MOVEA+MOVE/CLR/TST/CMP/CMPI/CMPA/ADD/ADDI/ADDQ/SUB/SUBI/AND/ANDI/EOR/LSL/ASR/MOVEM+MOVE, `MOVE.L #imm,(A6)`만인 block `beaba`, ADDA.W block `472a8`)는 Unknown이다(생산 4개는 위와 같이 known).
- block 안 C: `47288` `472a0`(CMP.W 뒤 BCC), 범위 판정형 앞 block 14개(CMPI.L 뒤 BCC/BCS)는 같은 block 안에서 만들고 소비한다. Z/N: `4530a`(TST.L 뒤 BGT), `45302` `4937e` `be8a4` `be8ce` `be918` `be950`(TST/MOVE/CMPI 뒤 BNE)도 같은 block 안이다. RTS를 넘는 flag 소비는 위 C뿐이다.
- 반환 Z·N: `472a8`의 `MOVE.B (A4),D7` 뒤 RTS, 표 대상의 `ADD`/`SUB` 뒤 RTS의 Z·N은 [F] 호출자(U08a `447e0 BRA`, 표 호출자의 `SUBI`/`TST`/`ADDI`/`CMPI`)가 읽지 않는다. C++는 Unknown으로 둔다.
- 루프 없음. I/O port 쓰기 없음. bank 변경 없음. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM 읽기, physical span 밖 bank 읽기는 기존 checked 오류다.

## 의존·경계

- [F] U11 → 기존: U08b `4bc44`(`4be06`), `4bf16`(`4be1e BRA`), U09 `469d8`(`4be0a`), `4706c`(`beac6`), frame_helpers `49392`(`497be` `497d0`), U05 `1ab02`(`be888`), `c6a96`(`beaec`), cleanup `46ef4`(`be896`), `2a24`(`be89c`), `43e34`(`beb52`), fade_card `28ae`(6곳), `2a00`(`be988`), U08a `49290`(`bead4`→`43e04` 공백), interpreter `49f8c`(`beafe`) `49fc6`(`beb58`).
- [F] 기존 → U11: U08a `447da JSR 47288`, U09 `46aca`·`46b2c BSR 45176`(U09 계약의 "U11 경계"), U10 `bac5c`/`baec0`/`baf4a JSR 4be06`·`bac62 JSR 497b6`(U10 계약의 경계). U08b `4bea0`/`4bf0a`는 `469d8`을 부른다(U11과 무관).
- [F] U11 경계 `4941e` `44c62`는 이 작업 트리에서 routing 밖이다.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, TB 기준)에서 U11 block에 닿는 callback과 seed:
- `be8a4` `bead4` `beac0` `beb52`: seed 82 83 88 89.
- `497b6`: seed 20 21(U10 `babb4` 계열 `bac62`).
- `47288`·`45176`·`4be06`·`49370`: 50 seed(6~9 12~23 34~37 40~43 56 57 62 63 68~71 76 77 80~83 88 89 96~99 102~105 116 117).
- 215 block 중 TB 시작 기준 47개가 자연 도달한다(RNG 초기화 + 응답 `80` 변형 `dyn_rng1_resp80_f400`도 47개). 표 entry는 `45206`(k=`23`) `452da`(`58`) `452de`(`59`) `452e2`(`5a`) `452ea`(`5c`)만 도달한다. 미도달 168개(나머지 표 entry 91, 대상 57, `4938c`, `497be..497e4` 9, `be896` `be89c` `be8c8` `be8e8` `be8f8` `be90e` `be920` `be930` `be946` `be988`; TB가 앞 block과 합쳐진 경우 포함)는 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] 기준 C++ 차분(작업 트리 `5f51050`, F2 프레임 패스 142 seed): 일치 pass 10,016개·node 74,976개, 불일치 0. 첫 미연결 callback이 `be8a4`인 seed 4개(82 83 88 89). RNG 초기화 400 frame 차분(`verify_animation_machine_frame_pass_rng.py` 방식): 완주 55 seed, 일치 pass 22,000개·node 146,848개, 불일치 0.
- [I] U11 병합 뒤 seed 82 83 88 89는 `be8a4`를 지나 자식 `bead4`의 `49290`→`43e04`(위 결정 7) 또는 다른 미연결 callback에서 멈출 것이다. 그래서 범위 문서의 "새 자연 seed 20 21 82 83 88 89"는 `43e04` 공백과 U10 병합(seed 20 21의 `babb4`)이 해결되기 전에는 완주로 나타나지 않을 수 있다(검증 기록에서 확인).

## 회귀 탐침(결정 8)

[F] `engine/tests`·`tools`·`engine/src`·`docs/analysis`에서 U11 범위 안 PC를 쓰는 곳(stop PC로만 쓰는 곳은 그대로 둔다):
- `engine/tests/animation_machine_frame_helpers_test.cpp` outside `0x49390`(U11 `4938c` block 안 RTS → `unsupported animation objects u11 PC`가 됨) → `0x5f800`.
- `engine/tests/animation_machine_objects_u08_test.cpp`: outside `0x47288`(U11 시작) → `0x5f802`; fixture `error-boundary-47288`(`447da`에서 `47288` 경계 rollback)과 `boundaries()`의 `47288` rollback 3건은 U11 병합 뒤 성립하지 않는다. F4 단위 test 경계 관례에 따라 `47288` stop 확인만 남기고 rollback 확인은 뺀다(fixture 행은 U11 실행 결과로 바뀌므로 제거).
- `engine/tests/animation_machine_objects_u08b_test.cpp` `BOUNDARIES`의 `0x47288`(stop 행 rollback) → `0x1`(U09 병합 때 `469d8`과 같은 처리).
- `engine/tests/animation_machine_objects_u09_test.cpp` outside `0x45176` `0x47288` `0x4728a` 제거, `boundaries()`의 `45176` rollback 제외(stop 확인만).
- `tools/inventory_*`·`docs/analysis`의 범위 표기와 caller inventory 나열은 탐침이 아니다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 215 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 4 known, 그 밖 Unknown), 소비 6 block의 Unknown 오류, zero-step, 내부 894 PC 정확한 오류, 표 96 index × 3 carry가 옮겨 적은 대상에 닿음, 표 상한 밖 D7(displacement WORD, 대상 내부, 홀수, 범위 밖, 자기 자신), TRAP `4937c` stop, 홀수 PC, 경계 callee stop. rollback 탐침은 `5f6xx..5ffxx`만 쓴다. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력과 합성 bank 바이트; ROM 자료는 test에 넣지 않음)로 비교한다.
- 실제 ROM 차분: 표 96 index 전체(D0/D1 부호·소수부 조합), `47288`(사각형 안/밖, ROM record `be5a2` `be612` `be670`과 RAM record), `49370`/`497b6`(실제 `49392`, `4941e` 경계), `4be06`(실제 `4bc44` `469d8` `4bf16`), `be8a4`·`bead4`·설치 callback(실제 `28ae` `1ab02` `46ef4` `2a24` `49290` `c6a96` `49f8c` `43e34` `49fc6` `4706c`)을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`, seed 58·59는 `animation_machine_pvc_banks_native`): 기준(`5f51050`) 일치 pass 10,016개·node 74,976개가 모두 그대로 일치해야 한다. RNG 초기화 400 frame 차분: 기준 22,000 pass·146,848 node 유지, 불일치 0.

## 미확인·범위 밖

1. [I] `45176` 표는 `447be`의 지형 코드(하위 BYTE)별 기울기 식이다(평지·1/2·1/4·1/8 경사, 위/아래 반쪽). D6=`80000000`은 "그 열에 지형 없음"으로 보인다. 게임 의미는 미확인이다.
2. [I] `47288`은 사각형 record(원점 x/y, 폭, 높이, 행 표)의 8픽셀 격자 셀 BYTE를 지형 코드로 돌려주고, 밖이면 D7=`58`(빈 코드)·D6=0을 돌려준다.
3. [I] `49370`은 A5가 `108000`인지 assert하고 BYTE `568e(A5)`=0이면 C Set(“활성 플레이어 없음”으로 보임)이다. `497b6`은 두 플레이어(D0=0/1)에 대해 `49392`(존재)와 `4941e`(경계, 거리 판정으로 보임)를 물어 하나라도 맞으면 C Clear다.
4. [I] `be8a4`는 `76(A6)`(0~2)에 따라 자식 `bead4` 두 개(`76`=0/1, 2/3, 4/5)를 만들고 `86(A6)`에 지형 사각형 record를 둔 뒤 매 frame `4be06`(이동·지형)과 `4706c`(슬롯 등록), `1ab02`(화면 밖이면 삭제)를 부르는 장치 객체로 보인다. `76(A6)`이 3 이상이면 `2a00`으로 스스로 지운다.
5. [U] 경계 `4941e` `44c62`의 실행 결과, `43e04`·`2a24` 공백의 결정, `be992..beab4`의 다른 객체 경로(`be9da` `bea40` `beab0 BRA be888`)는 U11 밖이다.
6. [U] `4662e`(U15) 진입 D7의 전 호출 closure(표 상한의 나머지 근거).

작업자 scratch: 세션 scratchpad `f4u11/`(`u11.py` block·범위·SHA 계산, `scope.py` `trav.py` `hroute_u11.py` `dis_u11.py`, `reach.py` `reach_rng.py`, `refs.py` `nextins.py` `probes.py`; 저장소 밖).
