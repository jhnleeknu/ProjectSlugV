# 객체 callback F4 U14: `614d4`/`50cca` 객체 생성자(`51482`)와 자식 5개(`51634` `5169e` `516b8` `516d2` `516ec`), 대기·확대 callback `50d3c`, 공유 helper `16ef0` `49260` `4a496`, 자식 `51ffa`, `7086a` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U14 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`), U12 계약(`animation-machine-objects-u12-contract.md`, SHA256 `61bd4657f2dab1b48ebd337e1a2000054911f233a458f3bb0f321e7846eac32d`), U13 계약(`animation-machine-objects-u13-contract.md`, SHA256 `20af72d0d12a571f1d36590bc9e36348b596de54d948320364c7721f71e2c53e`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee와 범위 밖에 설치되는 callback은 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01~U13 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U14에는 없음). `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`SUBA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc, Z만 바꾸는 `BTST`/`BSET`/`BCLR`)만인 block은 FLOW_ONLY다. `ADDQ`/`SUBQ`/`ADDA` An block은 Unknown이다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U14의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료(`200198`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u14`(HEAD `14ee5d2` = U01~U12 + U08a/U08b + cleanup `43e04`/`2a24` WIP, `engine/src/animation_machine.cpp` SHA256 `7b05876e97530cd1559e38e031128b334727726b71aefe37f2aa9135407bbc93`, routing 규칙 47개)을 참조했다. U13(작업 트리 `metalslug-u13`, 계약 위 SHA)은 이 작업 트리에 없으므로 U13 소유 PC(`70932`)는 경계로 둔다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u14/u14.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] U14는 **block 시작 78개**다. 범위 문서 U14 행의 79와 다르다(아래 결정 1). 범위 문서 `units.pkl`의 함수 21개(`16ef0` `49260` `4a496` `50d3c` `51482` `51634` `5169e` `516b8` `516d2` `516ec` `51758` `51fcc` `51fda` `51fe2` `51fe6` `51fec` `51ffa` `51ffe` `52004` `614d4` `7086a`)의 본문이다.
  - 공유 helper 8: `16ef0` 4(`16ef0` `16efc` `16f06` `16f0c`), `49260` 2, `4a496` 2.
  - 객체 `614d4`(callback, `JMP 50cca`) 1 + `50cca` 2 + 생성 helper `51482` 14 + 대기·확대 `50d2c` 16(설치 callback `50d3c` `50d50` `50d6a` 포함).
  - 자식 callback `51634` 5(`51634` `51668` `5166e` `5168e` `5169a`), `5169e` `516b8` `516d2` `516ec` 4 + 공유 꼬리 `51702` 4(`51702` `51720` `51726` `51746`), 설치 callback 계열 `51752` 10(`51752` `51758` `51766` `51768` `5176e` `5177a` `51780` `51790` `51798` `5179e`).
  - 신호 helper `51fcc` 1, `51fda` 3, 자식 callback `51ffa` 12(설치 callback `52004` 포함), `7086a` 2.
  - 코드 11 범위, 990바이트, 213명령이다. 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx는 없다. routing 짝수 PC는 495개, 내부 PC는 417개다.
- [F] **경계 callee(실행부 없음) 2개**: `51602`(`50d9c BSR.W`), `515fc`(`50da8 BSR.W`). 둘 다 `LEA d16(PC),A0; BRA.B 515e0`인 범위 밖 helper 진입이다(범위 문서 "경계 callee 2"와 같음). U13 소유 `70932`(`70874 BRA.W`)는 U13 병합 전 경계다.
- [F] **범위 밖 설치 callback(쓰기만 함)**: `50dae`(`50d7c`에서 `MOVE.L #50dae,(A6)`). 다음 frame에 scheduler가 부르면 실행부 없는 경계다(결정 2).
- [F] 기존 실행부로 나가는 호출: U02 `8ebe`(palette 참조, 4곳), palette_bind `8da2`, interpreter `49f8c`(3곳)·`49fc6`, fade_card `28ae`(자식 5개), buffer_cue `2986`(자식 2개), cleanup `43e08`·`43e34`, scene `1701a`, stage_event_ops `49a84`(2곳), U08a `49290`(2곳), U12 `490ba`(2곳)·`70418`. U14 안 호출: `50cca BSR 51482`, `50d2c BSR 51fda`, `51fda BSR 51fcc`, `514b6 JSR 4a496`, `514bc`/`51668`/`51720 JSR 16ef0`, `5202e JSR 49260`, `614d4 JMP 50cca`.
- [F] **flag**: 블록 경계를 건너는 C 소비 block 0개, known carry 생산 block 0개. block 안에서 만들고 쓰는 flag: `16ef0`(`CMP.W` 뒤 `BCC`), `50d6a`(`CMPI.W` 뒤 `BCS`), `51780`/`51790`(`CMP.W` 뒤 `BLT`/`BGT`, 부호 비교), 그 밖 `SUBQ`/`TST`/`BTST` 뒤 `BEQ`/`BNE`.
- [F] 읽는 자료: banked window LONG `200198`(→ `22(A6)`, `51482` `51634` `51702`). 주소만 넘기는 fixed ROM 상수 `5162c`(→`8da2` A0), `528c0`(→`49f8c` A1), `528b6` `52838` `52842` `5284c` `52856`(→`49290` A0, 이어 stack을 거쳐 `49f8c` A1), `52b82` `52bcc`(→`490ba` A0), `521cc`(→ LONG `56(A6)`), 자식 callback 상수 `51634` `5169e` `516b8` `516d2` `516ec` `51ffa` `5208a`. I/O port 쓰기와 bank 변경은 U14 자체에 없다.
- [F] 자연 도달(F4 범위 scratch 재생, TB 기준): base(`f4scope/dyn`) 54 block, RNG 초기화+응답 `80` 변형(`dyn_rng1_resp80_f400`) 61 block. 범위 안 TB 중 정적 시작이 아닌 것은 `51fe2` `51fe6` `51fec` `51ffe` 4개뿐이고 모두 직선 구간 안의 TB 분할이다(결정 1).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 79→78.**
   - −4: `51fe2` `51fe6` `51fec`(`51fdc..51ff2` 직선 구간 `MOVEA.L`/`MOVE.W`/`MOVEA.L`/`JSR`의 안쪽 명령)와 `51ffe`(`51ffa` block의 `MOVE.L #52004,(A6)` 명령). [F] ROM 전체에 이 넷으로 가는 정적 분기·호출·LONG 상수가 없다(`refs.py` 0건, LONG 검색 0건). 범위 문서는 TB 시작을 세었다(TB 인공물, 결정 3).
   - +3: 범위 안 설치 callback 진입 `50d50`(`50d4a MOVE.L #50d50,(A6)`), `50d6a`(`50d64`), `5176e`(`51768`). U05 `b971a`·U06 `e78f4`·U07 `e59f6`와 같은 관례다.
   - 권고: 78로 둔다. 범위 문서는 고치지 않는다.
2. **범위 밖 설치 callback `50dae`.** `50d7c`가 `8c(A6)`=`2000`에 닿으면 `50dae`를 설치한다. 그 본문(`50dae..5146c` 연쇄, 정적 약 190 block, 다시 `50cf6` `50e42` `50f1a` 등 20여 개 callback을 설치)은 넣지 않는다. [F] base·RNG 초기화+`80` 재개 400 frame 어느 변형에서도 `50d46` 이후가 실행되지 않았다(`8c(A6)` 감소가 `78`=120 frame, 이어 `5d2d(A5)` 대기). U13 결정 1과 같다. 권고: 그대로 둔다.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u14.cpp`의 `animation_objects_u14_block`. 오류는 `unsupported animation objects u14 PC`(내부 PC), `objects u14 caller requires known carry`(U14에는 소비 block이 없어 실제로는 나지 않는다; 문자열만 예약). 메인 지시와 같다.
4. **`16ef0`과 기존 sprite 실행부 `16ed2`.** [F] `16ed2..16eee`(`BGE`)와 `16ef0..16f0c`(`BCC`)는 서로 다른 함수다. sprite 실행부는 `case 0x16ed2` 한 block으로 `16eee RTS`까지 끝내고 `16ef0` 이후로 넘어가지 않는다. U04 결정 1대로 `16ede` `16ee8` `16eee`는 다시 routing하지 않고, U14는 `16ef0..16f0e`만 routing한다. `16f0e` 이후는 기존 routing(다른 실행부)이다.
5. **U13 경계 `70932`.** `7086a`→U12 `70418`→`70874 BRA.W 70932`. U13 병합 전 U14만으로는 seed 38·39가 `70932`에서 멈추므로 새 완주로 기대하지 않는다. F4 test 경계 관례에 따라 test는 이 PC의 stop만 확인하고 rollback은 `5f6xx..5ffxx`로만 확인한다. 권고: U13 병합 뒤 frame pass 차분을 다시 잰다(검증 기록에서 U13+U14 scratch 조합으로 확인).
6. **bank 자료.** `MOVE.L 200198.L,22(A6)`(3곳)은 live bus로 읽는다(bank window 값은 bank base가 정한다. 그 밖은 기존 checked 오류). test에는 합성 bank 바이트를 쓴다(ROM 자료를 test에 넣지 않음).
7. **BYTE stack.** `4a496 MOVE.B 14(A6),-(A7)`와 `4a4a2 MOVE.B (A7)+,14(A6)`는 A7을 2씩 움직이고 BYTE 하나를 쓴다·읽는다(68000 A7 규칙, F1c 규칙과 같음). `8ebe` 호출 동안 그 WORD 칸 위에 복귀 LONG이 쌓인다.
8. **무효화 탐침.** [F] `engine/tests`·`tools`·`engine/src`·`docs/analysis`(이 작업 트리)에서 U14 범위 안 PC를 rollback·outside 탐침으로 쓰는 곳은 없다(`probes.py`: `docs/analysis/animation-machine-caller-inventory.md` 101행의 caller 나열 `051798`, `stage-activation-animation-inventory.md`의 `16ef0` 설명, `tools/observe_animation_machine_activation.py`·`observe_stage_activation_helpers.py`의 범위 끝 `16ef0`(배타 끝)뿐, 탐침 아님). 교체 탐침(`5fd00` 이후)은 필요 없다.

## 원본 바이트 근거

[F] 코드 11 범위 합계 990바이트. 범위 순서로 이어 붙인 SHA256 `7285a6cf7af95483ced1b4411e1deb24763d96cb7e1b7e408ff9cc55ce76b856`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `16ef0..16f0e` | 30 | `a053aa783b878b3612b338878187e61d190019b4e81d14d51d6216beda40a3f5` | helper `16ef0` |
| `49260..49274` | 20 | `3522b4faeeb66b37ae00eedcc0e8f3008da7295f38b166244435709c7ba5e3fe` | helper `49260` |
| `4a496..4a4b4` | 30 | `7b6469c9ad29b5f304856b49a1c3b3aea4ee8a8787f243ebcc39213ddbee2123` | helper `4a496` |
| `50cca..50cd2` | 8 | `f382205bc71a0746f04b4e8783a757168ebb85a445915ca60229cd4155856fee` | `50cca` |
| `50d2c..50dae` | 130 | `7061ec8a7dd6cac8765dbf4d226173372b70e060728c881b644dd073a942eaf5` | `50d2c`, 설치 callback `50d3c` `50d50` `50d6a` |
| `51482..51574` | 242 | `d62e88e013df735d07ee5098c293aeeb1968837c58599bb059d78311541f06da` | 생성 helper `51482` |
| `51634..517a0` | 364 | `8bd13e555ba8acd7ed876e234adbe6861d8303eadb2e44ad50c26b584725aea5` | 자식 callback 5개, 공유 꼬리 `51702`, 설치 callback `51758` `5176e` |
| `51fcc..51ff4` | 40 | `902411a4424045f217da791c19790f08be0e669b507d2fc80db08e8802b2ef9f` | `51fcc`, `51fda` |
| `51ffa..5205e` | 100 | `41b9035f2245471aa0817e47b3c6de4780665a3ca1bf4b27e5af32599603e195` | 자식 callback `51ffa`, 설치 callback `52004` |
| `614d4..614da` | 6 | `27fa548311b3adad36473e68e4d2324a38caf587370464cfa4a14cb52e8b3912` | callback `614d4` |
| `7086a..7087e` | 20 | `acd5b9bb841b639a80ffc6f35c0a7e18222ef77f435b6ce11df9a1fcf2149bd4` | callback `7086a` |

- [F] 범위 밖 이웃(routing 밖): `16ed2..16ef0`(기존 sprite 실행부 block, 결정 4), `16f0e..`(기존 routing), `49250..49260`(앞 함수), `49274..`(U08a), `4a490..4a496`(앞 함수 `ANDI CCR`/`RTS`), `4a4b4..`(다음 함수), `50cc0..50cca`(앞 함수), `50cd2..50d2c`(다른 진입 `50cd2` `50cea` `50cf6` `50d08` `50d24`; `50dae` 연쇄가 쓰는 함수), `50dae..`(범위 밖 설치 callback, 결정 2), `51574..51634`(다른 helper `51574` `51590` `515a2` `515e0`, 경계 `515fc` `51602` `51608`, 자료 `5160e..51634`), `517a0..`(다른 callback), `51ff4..51ffa`(다른 함수 `TST.B 5d2d(A5); RTS`), `5205e..`(자료), `614da..`(다른 callback), `7087e..`(같은 dispatcher를 쓰는 다른 진입).
- [F] 자료(모두 live bus):
  - banked window: LONG `200198`(→ `22(A6)`; `51488` `5163a` `51712`). [F] bank `200000`에서 `002c9e76`, bank `300000`이면 `01000000`, bank `400000`이면 `00223af0`.
  - fixed ROM: U14가 직접 읽는 fixed ROM 자료는 없다. 위 상수는 주소로만 넘긴다(읽기는 callee 몫).
  - work RAM(A5=`108000` 기준): WORD `d3e(A5)` `d46(A5)`(`16ef0` 읽기), BYTE `5d2c(A5)`(`51fcc` `ff` 쓰기, `50d46` CLR, `52004` TST) `5d2d(A5)`(`51fcc` 0 쓰기, `50d50` TST). 주소만: `538e(A5)`(→`43e08` A1), LONG 상수 `10d256`(→`1701a` A0), `100bf4`(→`2986` A1).
  - 노드 d16(A6): BYTE `15`(BSET bit 2·6, BCLR bit 2) `14`(읽기·쓰기) `16` `17` `19`(읽기) `8c`(BYTE SUBQ·읽기) `87` `a1`, WORD `20` `68` `1e` `92` `94` `54` `9a` `8c` `8e` `9c`, LONG `22` `56` `(A6)`(callback 설치) `c`(부모 node 포인터 읽기, `51758` `5176e` `51780`), BYTE `7e`(BCLR bit 2, `5153e`).
  - 부모 node d16(A0=`c(A6)`): BYTE `7e` bit 2(BTST), WORD `32`(읽기). 자식 node d16(A0, `2986` 반환 뒤 `49260`을 지난 A0): WORD `76`(`5203e` 쓰기).
- [F] 스택: JSR/BSR 복귀 LONG, `51660`/`5170a MOVE.L A0,-(A7)`와 `5168e`/`51746 MOVEA.L (A7)+,A1`(LONG push/pop, `49290`·`8ebe` 호출을 감쌈), `4a496`/`4a4a2` BYTE push/pop(결정 7).

## block 목록과 실행 의미

[F] 78 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `.B`·`.W` 연산은 나머지 bit를 보존하고 `MOVEQ`는 LONG 전체를 쓴다. `MOVEA.W`/`SUBA.W`는 부호확장한 WORD로 LONG 전체를 바꾼다.

**공유 helper 8**
- `16ef0`: `MOVE.W d3e(A5),D0; CMP.W d46(A5),D0; BCC.W 16f06` (unsigned D0.W ≥ WORD `d46(A5)`이면 `16f06`)
- `16efc`: `BCLR.B #2,15(A6); BRA.W 16f0c`
- `16f06`: `BSET.B #2,15(A6)` (→`16f0c`)
- `16f0c`: `RTS`
- `49260`: `LEA 2e(A0),A0; LEA 538e(A5),A1; JSR 43e08.L` (cleanup)
- `4926e`: `SUBA.W #2e,A0; RTS`
- `4a496`: `MOVE.B 14(A6),-(A7); MOVEQ #0,D1; JSR 8ebe.L` (U02)
- `4a4a2`: `MOVE.B 14(A6),16(A6); MOVE.B #0,17(A6); MOVE.B (A7)+,14(A6); RTS`

**객체 `614d4`/`50cca`/`51482`/`50d2c` 33**
- `614d4`: `JMP 50cca.L` (callback 진입)
- `50cca`: `BSR.W 51482`
- `50cce`: `BRA.W 50d2c`
- `50d2c`: `BSR.W 51fda`
- `50d30`: `MOVE.B #78,8c(A6); MOVE.L #50d3c,(A6)` (→`50d3c`)
- `50d3c`: `SUBQ.B #1,8c(A6); BEQ.W 50d46` (설치 callback 진입)
- `50d44`: `RTS`
- `50d46`: `CLR.B 5d2c(A5); MOVE.L #50d50,(A6)` (→`50d50`)
- `50d50`: `TST.B 5d2d(A5); BEQ.W 50d5a` (설치 callback 진입)
- `50d58`: `RTS`
- `50d5a`: `CLR.W 8c(A6); MOVE.W #40,8e(A6); MOVE.L #50d6a,(A6)` (→`50d6a`)
- `50d6a`: `MOVE.W 8e(A6),D0; ADD.W D0,8c(A6); CMPI.W #2000,8c(A6); BCS.W 50d96` (설치 callback 진입; unsigned WORD `8c` < `2000`이면 `50d96`)
- `50d7c`: `MOVE.W #2000,8c(A6); MOVE.L #50dae,(A6); LEA 10d256.L,A0; JSR 1701a.L` (scene; 범위 밖 설치 callback `50dae`)
- `50d94`: `RTS`
- `50d96`: `MOVEQ #0,D2; MOVE.B 8c(A6),D2; BSR.W 51602` (경계)
- `50da0`: `MOVEQ #0,D2; MOVE.B 8c(A6),D2; LSR.W #1,D2; BSR.W 515fc` (경계)
- `50dac`: `RTS`
- `51482`: `MOVE.W #193,20(A6); MOVE.L 200198.L,22(A6); MOVE.W #d7d,D0; MOVE.B #0,D1; JSR 8ebe.L` (bank 자료; U02)
- `5149e`: `MOVE.W #d7c,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `514ac`: `MOVE.B 19(A6),14(A6); MOVE.W #922,D0; JSR 4a496.L`
- `514bc`: `JSR 16ef0.L`
- `514c2`: `BSET.B #6,15(A6); MOVE.W #800,68(A6); MOVE.W #800,1e(A6); LEA 5162c(PC),A0; JSR 8da2.L` (palette_bind)
- `514de`: `MOVEA.L #528c0,A1; MOVE.W #100,D0; JSR 49f8c.L` (interpreter)
- `514ee` `514fe` `5150e` `5151e` `5152e`: `MOVEA.L #cb,A0; MOVE.W #a,D0; JSR 28ae.L` (cb=`51634` `5169e` `516b8` `516d2` `516ec`; fade_card 자식 생성)
- `5153e`: `BCLR.B #2,7e(A6); MOVE.L #521cc,56(A6); LEA 52b82.L,A0; JSR 490ba.L` (U12)
- `51558`: `MOVE.W D0,54(A6); LEA 52bcc.L,A0; JSR 490ba.L`
- `51568`: `MOVE.W D0,9a(A6); MOVE.B #0,a1(A6); RTS`

**자식 callback 23**
- `51634`: `MOVE.W #193,20(A6); MOVE.L 200198.L,22(A6); MOVE.W #0,D0; MOVE.W #80,D1; MOVE.W #ffd4,D6; MOVE.W #8c,D7; MOVEA.L #528b6,A0; MOVE.W D6,92(A6); MOVE.W D7,94(A6); MOVE.L A0,-(A7); JSR 49290.L` (callback 진입; bank 자료; U08a)
- `51668`: `JSR 16ef0.L`
- `5166e`: `BSET.B #6,15(A6); MOVE.W #2,68(A6); MOVE.W #2,1e(A6); MOVE.W #d7b,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `5168e`: `MOVEA.L (A7)+,A1; MOVE.W #100,D0; JSR 49f8c.L`
- `5169a`: `BRA.W 51752`
- `5169e` `516b8` `516d2`: `MOVE.W #0,D0; MOVE.W #d1,D1; MOVE.W #d6,D6; MOVE.W #d7,D7; MOVEA.L #a0,A0; BRA.W 51702` (callback 진입; (d1,d6,d7,a0)=(`80`,`ff78`,`100`,`52838`), (`ff80`,`58`,`208`,`52842`), (`fe80`,`148`,`318`,`5284c`))
- `516ec`: 같은 형식 (`fdb0`,`254`,`398`,`52856`) (callback 진입, →`51702`)
- `51702`: `MOVE.W D6,92(A6); MOVE.W D7,94(A6); MOVE.L A0,-(A7); MOVE.W #193,20(A6); MOVE.L 200198.L,22(A6); JSR 49290.L` (bank 자료)
- `51720`: `JSR 16ef0.L`
- `51726`: `BSET.B #6,15(A6); MOVE.W #1,68(A6); MOVE.W #1,1e(A6); MOVE.W #d7a,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `51746`: `MOVEA.L (A7)+,A1; MOVE.W #100,D0; JSR 49f8c.L` (→`51752`)
- `51752`: `MOVE.L #51758,(A6)` (→`51758`)
- `51758`: `MOVEA.L c(A6),A0; BTST.B #2,7e(A0); BNE.W 51768` (설치 callback 진입)
- `51766`: `RTS`
- `51768`: `MOVE.L #5176e,(A6)` (→`5176e`)
- `5176e`: `MOVEA.L c(A6),A0; BTST.B #2,7e(A0); BEQ.B 51752` (설치 callback 진입)
- `5177a`: `JSR 43e34.L` (cleanup)
- `51780`: `MOVEA.L c(A6),A0; MOVE.W 32(A0),D0; CMP.W 92(A6),D0; BLT.W 5179e` (부호 WORD D0 < `92(A6)`이면 `5179e`)
- `51790`: `CMP.W 94(A6),D0; BGT.W 5179e` (부호 WORD D0 > `94(A6)`이면 `5179e`)
- `51798`: `JSR 49fc6.L` (interpreter)
- `5179e`: `RTS`

**신호 helper·자식 `51ffa`·`7086a` 16**
- `51fcc`: `MOVE.B #ff,5d2c(A5); MOVE.B #0,5d2d(A5); RTS`
- `51fda`: `BSR.B 51fcc`
- `51fdc`: `MOVEA.L #51ffa,A0; MOVE.W #a,D0; MOVEA.L #100bf4,A1; JSR 2986.L` (buffer_cue 자식 생성)
- `51ff2`: `RTS`
- `51ffa`: `CLR.W 8c(A6); MOVE.L #52004,(A6)` (callback 진입, →`52004`)
- `52004`: `TST.B 5d2c(A5); BEQ.W 5205c` (설치 callback 진입)
- `5200c`: `TST.W 8c(A6); BNE.W 52058`
- `52014`: `MOVEA.L #5208a,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.L`
- `5202a`: `MOVEQ #0,D0; MOVEQ #0,D1; JSR 49260.L`
- `52034`: `MOVE.W #2,D0; JSR 49a84.L` (stage_event_ops)
- `5203e`: `MOVE.W D0,76(A0); MOVE.W #30,D0; JSR 49a84.L`
- `5204c`: `ADDI.W #20,D0; MOVE.W D0,8c(A6); BRA.W 5205c`
- `52058`: `SUBQ.W #1,8c(A6)` (→`5205c`)
- `5205c`: `RTS`
- `7086a`: `MOVE.W #0,9c(A6); JSR 70418(PC)` (callback 진입; U12)
- `70874`: `MOVE.B #2,87(A6); BRA.W 70932` (U13 경계)

(수: helper 8 + 객체 33 + 자식 23 + 14; 합 78. 객체 33 = `614d4` 1 + `50cca` 2 + `50d2c` 16 + `51482` 14.)

## 구현 범위와 규약

- routing 11 범위(위 표). 짝수 PC 495개 중 block 시작 78, 내부 417. 내부 PC 직접 진입은 `unsupported animation objects u14 PC`다. 경계 callee 2개, U13 `70932`, 범위 밖 설치 callback `50dae`와 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다. `16ed2` sprite block은 바꾸지 않는다.
- **carry 소비 block 0개, known carry 생산 block 0개.** [F] U14 함수의 호출자 바로 뒤 명령은 C를 읽지 않는다(`nextins.py`: `16ef0` 54곳, `49260` 8곳, `4a496` 126곳, `51fcc` `51fda` `51482` 각 1곳 모두 C 소비 없음). callback과 설치 callback은 scheduler가 부른다.
- **FLOW_ONLY 26개**(C 보존): `16efc` `16f06`(BCLR/BSET, Z만), `16f0c` `4926e`(SUBA+RTS) `50d44` `50d58` `50d94` `50dac` `51766` `5179e` `51ff2` `5205c`(RTS), `49260`(LEA+JSR), `50cca` `50d2c` `51fda`(BSR), `514bc` `51668` `51720` `5177a` `51798`(JSR), `50cce` `5169a`(BRA), `614d4`(JMP), `51758` `5176e`(MOVEA+BTST+Bcc). 그 밖 52개(MOVE/MOVEQ/MOVEA+MOVE/CLR/TST/CMP/CMPI/ADD/ADDI/SUBQ/LSR/BSET·BCLR+MOVE, `MOVE.L #imm,(A6)` block, BYTE·LONG push/pop block)는 Unknown이다.
- 루프: `5176e BEQ.B 51752`(뒤로 가지만 `51752`→`51758`에서 같은 bit를 다시 보고 RTS하므로 한 번만 돈다). I/O port 쓰기 없음. bank 변경 없음. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM 읽기, physical span 밖 bank 읽기는 기존 checked 오류다.

## 의존·경계

- [F] U14 → 기존: U02 `8ebe`(`4a496` `51482` `5149e` `5166e` `51726`), palette_bind `8da2`(`514c2`), interpreter `49f8c`(`514de` `5168e` `51746`)·`49fc6`(`51798`), fade_card `28ae`(`514ee`~`5152e`), buffer_cue `2986`(`51fdc` `52014`), cleanup `43e08`(`49260`)·`43e34`(`5177a`), scene `1701a`(`50d7c`), stage_event_ops `49a84`(`52034` `5203e`), U08a `49290`(`51634` `51702`), U12 `490ba`(`5153e` `51558`)·`70418`(`7086a`).
- [F] U14 → 경계: `51602`(`50d96`), `515fc`(`50da0`), U13 `70932`(`70874`), 설치 callback `50dae`.
- [F] 기존·다른 단위 → U14: `JSR 16ef0.L` 54곳(U14 3곳 외 51곳은 다른 단위), `JSR 4a496.L` 126곳(U14 1곳 외), `49260` 8곳(U14 1곳 외 `1da12` `5184a` `518c6` `519b6` `dd782` `e66c6`, `b46f0 JMP`), `614d4`는 LONG 상수 `e9054`(stage event 표), `7086a`는 LONG 상수 `8ba88` `a5d7c` `a7454` `a85f8` `c41fa` `e8d00`.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, TB 기준)에서 U14 block에 닿는 seed:
- `614d4`(→`50cca` `51482` `50d2c`, 자식 `51634` `5169e` `516b8` `516d2` `516ec` `51ffa`): seed 84 85. RNG+`80` 변형에서 `50d3c` `51758` `52004`(그리고 `52004`가 만든 자식 `5208a`)까지.
- `7086a`: base seed 38 39 62 63, RNG+`80` 변형 26 27 38 39 62 63.
- 공유 helper `16ef0` `4a496` `49260`: seed 6 7 12 13 16~19 30~33 46 47 56 57 96 97 102 103(다른 단위 callback이 부름).
- 78 block 중 TB 기준 base 54개, RNG+`80` 변형 61개가 자연 도달한다. RNG+`80` 변형의 미도달 17개(`50d46` `50d50` `50d58` `50d5a` `50d6a` `50d7c` `50d94` `50d96` `50da0` `50dac` `51768` `5176e` `5177a` `51780` `51790` `51798` `5179e`)는 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] 기준 C++ 차분(작업 트리 `14ee5d2`, F2 프레임 패스 142 seed): 일치 pass 10,496개·node 79,586개, 불일치 0, 자연 완주 77 seed. 첫 미연결 callback `614d4` 2(seed 84 85), `7086a` 2(38 39). RNG 초기화 400 frame 차분: 일치 pass 23,684개·node 159,345개, 불일치 0, complete 59.
- [I] U14만 병합하면 seed 84·85는 `614d4` 계열을 지나고, seed 38·39는 `70932`(U13 경계)에서 멈춘다. 범위 문서의 "새 자연 seed 38 39"는 U13과 함께 병합될 때 나타날 것이다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 78 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), zero-step, 내부 417 PC 정확한 오류, 홀수 PC, 경계 `51602` `515fc` `70932`·설치 callback `50dae` stop(rollback 없음; U13 PC는 stop만), rollback 탐침은 `5f6xx..5ffxx`만. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력과 합성 bank 바이트; ROM 자료는 test에 넣지 않음)로 비교한다.
- 실제 ROM 차분: `614d4`→`51482` 전체(실제 `8ebe` `8da2` `49f8c` `28ae` `490ba`, bank `200000`), 자식 5개(실제 `49290` `16ef0` `8ebe` `49f8c`), `51758`/`5176e`(부모 `7e` bit 2 × `32` 범위), `50d3c`/`50d50`/`50d6a`(`8c`/`8e`/`5d2d` 값), `51ffa`/`52004`(`5d2c`/`8c`, 실제 `2986` `49260` `49a84`, RNG 고리 초기화 상태)를 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`, seed 58·59는 `animation_machine_pvc_banks_native`): 기준 일치 pass 10,496개·node 79,586개 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 기준 23,684 pass·159,345 node 이상, 불일치 0, complete 59 이상.

## 미확인·범위 밖

1. [I] `614d4`(stage event 표 `e9054`의 callback)는 `51482`로 큰 객체(`20`=`193`, bank animation 표 `200198`, palette `d7d` `d7c` `922`, interpreter `528c0`)를 만들고 자식 5개를 붙인 뒤 `5d2c(A5)` 신호(`51fcc`)와 자식 `51ffa`를 세운다. 이어 120 frame을 기다리고(`8c`=`78`) `5d2d(A5)`가 0이 되면 `8c`에 `40`씩 더해 `2000`까지 키운다(`515fc`/`51602`로 넘기는 값). 게임 의미(등장 연출로 보임)는 미확인이다.
2. [I] 자식 5개는 부모(`c(A6)`)의 `7e` bit 2가 서고 내려가는 동안 기다렸다가(`51758`/`5176e`) cleanup `43e34`를 하고, 부모 WORD `32`가 자기 `92..94`(부호 WORD 범위) 안이면 animation(`49fc6`)을 진행하는 부품으로 보인다.
3. [I] `51ffa`는 `5d2c(A5)`가 서 있는 동안 `8c` frame마다(난수 `20..4f`) 자식 `5208a`를 만들고 `76`에 난수 `0..1`(`49a84` D0=2)을 준다.
4. [U] 경계 `515fc` `51602`(→`515e0`), 범위 밖 설치 callback `50dae` 연쇄의 본문과 실행 결과는 U14 밖이다.

작업자 scratch: 세션 scratchpad `f4u14/`(`u14.py` block·범위·SHA 계산, `scope.py` `trav.py` `hroute_u14.py` `dis_u14.py`, `refs.py` `nextins.py` `probes.py` `reach.py`; 저장소 밖).
