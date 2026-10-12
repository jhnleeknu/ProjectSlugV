# 객체 callback F4 U17: 객체 callback `bbf56`·`c3d60` 계열과 공유 보조 `1c5ea` `443ea` `482c0` `491c4` `4929e` `4bfa4` `4c020` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U17 행과 그 "메인 결정"이다. 단위 형식과 규약은 U16 계약(`animation-machine-objects-u16-contract.md`, SHA256 `d4959a63bb13e5bc5413a791a4caf3c9b21cf5da336447028fee12ee8df1ab90`, 같은 bank 표 읽기 형식), U02 계약(SHA256 `b18f52f013f3e4b03eb52b669e567adb01eab5bb0e328810cd3e38cb4945ef94`, 같은 표 `4419e`를 쓰는 형제 함수 `443d2`), U10 계약(SHA256 `2b3c1f73213c12bb8f3b5512968210e99d1986a04b90321ce48e99c0fa98147c`, `49fc6`·`288c` 반환 C 소비자), F1b 계약(`animation-machine-area-clear-f1b-contract.md`, SHA256 `6bd2e96395e73814b7d4308f03d027eb1fb7be3c17ef8019491512340f66d4f2`, 형제 함수 `1c5b0`의 `289e` C 소비)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee와 다른 단위의 PC는 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01~U16 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U17에는 없음). `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc, Z만 바꾸는 `BTST`/`BSET`/`BCLR`)만인 block과 callee C를 소비하는 단독 Bcc는 FLOW_ONLY다. `ADDQ`/`SUBQ` block은 Unknown이다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C를 소비자에서 쓰려면 native 분기 결과로 확인한다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U17의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료(`200140`, `200088`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u17`(HEAD `9682aed` = Codex의 U16까지 통합, U15b/U15c 포함, `engine/src/animation_machine.cpp` SHA256 `a0f77362514f9abd8b75d5d5717c811644aa6e24b0953f1f64dcfb6792a753d3`, routing 규칙 53개)을 참조했다. 동시에 진행되는 U18(작업 트리 `metalslug-u18`, 범위 `46c68..46d12` `4b54e..4b6e2` `4be2c..4bf9e` `b631c..b67ae` `b76a4..b7740` `b7bc2..b7e6e` `ea5e0..eaa54`)의 PC는 경계로 둔다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/u17/u17.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] U17은 **block 시작 109개**다. 범위 문서 U17 행의 104와 다르다(아래 결정 1). 범위 문서 `units.pkl` U17의 함수 28개 중 아직 routing 밖인 함수 본문이다.
  - 공유 보조 7함수 22 block: `1c5ea` 7, C5 `443ea` 1, `482c0` 4, C3 `491c4` 1, C3 `4929e` 1, C4 `4bfa4` 4, C4 `4c020` 4. 객체 callback `bbf56` 계열 28(설치 callback `bbf70` `bbf80` `bbfd2` `bc020` `bc044` `bc060` `bc076` 포함), 객체 callback `c3d60` 계열 59(설치 callback `c3df2` `c3e38` `c3e70` `c3ec0` `c3edc` `c3f74` `c3faa`, 자식 callback `c3f08` `c3f92` 포함).
  - 코드 9 범위, 1,186바이트, 252명령이다. 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx는 없다. MULS 2(`443f8` `443fc`). routing 짝수 PC는 593개, 내부 PC는 484개다.
  - 범위 문서 U17의 TB 기준 시작 중 정적 시작이 아닌 것은 TB 분할 5개(`bbfea` `bbff2` `bbffc` `bbffe` `bc002`, 모두 정적 block `bbfe4` `bbfee` `bbff8` 안)뿐이다.
- [F] **경계 callee(실행부 없음) 1개**: `4be2c`(`bc048 JSR`, U18 범위). 자식 callback `bc08c`(`bc060`이 `28ae`에 넘김)는 쓰기만 하고 실행하지 않는다(어느 F4 단위 범위에도 없음).
- [F] 기존 실행부로 나가는 호출: readiness `289e`(`1c5ea` `1c600`, C 반환), stage_entry `ca56`(`482c0`), exit `48398`(`482de`), area_clear `ca48`(`c3d60`), U01 `48296`(`bbf5e` `c3d66`), U05 `c6a96`(`bbf92`), U02 `8ebe`(`c3d80` `c3d8e` `c3f2c` `c3f3a`), U12 `4c0ac`(`c3d9a`), interpreter `49f8c`(`bbfba` `bc038` `c3dde` `c3e64` `c3f68`)·`49fc6`(`bc018` `bc04e` `bc084` `c3e04` `c3e82` `c3eee` `c3f7a`, C 반환), sound `3af8`(`bbff2` `c3e3c` `c3e90`), fade_card `28ae`(`bc06a` `c3daa` `c3ea0`)·`2a00`(`c3f8a` `c3fba` JMP), cleanup `43e34`(`bc076` `c3f74` `c3faa`), stage_event_ops `288c`(`c3f80` `c3fb0`, C 반환), U09 `4706c`(`c3e30` `c3eb8` `c3f00` `c3fcc`), U08 `49290`(`c3f0c` `c3f98`), U08b `4be34`(`bbfde`)·`4bc44` `4bb22`(`4bfa4` `4bfac` BSR)·`4bf0a`(`4bfb0 BRA.W`, 공통 꼬리), U11 `4be06`(`c3e70` `c3edc`). U17 안 호출: `482e2 JSR 1c5ea`, `4bfa8 BSR.W 4c020`, `4c030 JSR 443ea`, `c3df2 JSR 4bfa4`, `c3e10 JSR 4929e`, `c3ec0 JSR 482c0`, `c3f12`/`c3f9e JSR 491c4`.
- [F] **flag**:
  - 블록 경계를 건너는 C 소비 block 6개(모두 FLOW_ONLY 단독 Bcc): `1c5f6 BCC` `1c60c BCC`(`289e` 반환 C, F1b `1c5bc` `1c5d8`과 같은 생산자), `bc054 BCC` `c3e88 BCC`(`49fc6` 반환 C, U10 `baecc` 등과 같은 생산자), `c3f86 BCS` `c3fb6 BCS`(`288c` 반환 C, U10 `bafda`와 같은 생산자).
  - known carry 생산 block 없음. [F] U17 함수의 ROM 정적 호출자 바로 뒤 명령은 C를 읽지 않는다(`nextins.py`: `1c5ea` 1곳 `RTS`, `443ea` 16곳, `482c0` 6곳, `491c4` 79곳, `4929e` 16곳, `4bfa4` 105곳, `4c020` 3곳; C 소비 명령 0). `RTS`로 이어지는 호출자(`482e8`, `5193a`, `1d86c`, `a2168`, `a4110`)와 `JMP 4bfa4` 꼬리 4곳은 U17 범위 밖이다. `1c5ea`가 돌려주는 C는 두 번째 `289e`의 C 그대로다(`1c610 BCLR`·`1c616 RTS` FLOW_ONLY). 소비자가 없으므로 따로 생산자로 두지 않는다.
  - block 안에서 만들고 쓰는 flag: `4c036`(`CMPI.B` 뒤 `BNE`), `bbf70`(`SUBQ.W` 뒤 `BCC`, borrow = WORD가 0), `bbfe4`(`BTST` 뒤 `BEQ`, Z만), `bbff8`(`CMPI.L` 뒤 `BGE`, 부호 비교), `bc07c`(`TST.B` 뒤 `BNE`), `c3db0`(`TST.W` 뒤 `BNE`), `c3e16`(`CMP.W` 뒤 `BGT`, 부호 비교), `c3e24` `c3eac` `c3ef4` `c3fc0`(`CMPA.W #0` 뒤 `BEQ`).
- [F] 읽는 자료: banked window LONG `200140`(→ `22(A6)`, `bbf98`)과 그 값 + `d4`의 LONG(→ A1), banked window LONG `200088`(→ `22(A6)`, `c3dbc` `c3e42` `c3f40`)과 그 값 + `64`/`68`/`6c`의 LONG(→ A1). fixed ROM WORD 표 `4411e..4439e`(`443ea`의 `MULS.W (A0,D2.W)`·`-80(A0,D2.W)`, A0=`4419e`). 주소만 넘기는 상수: `bcb32`(→`49f8c` A1), `bc08c` `c3f92` `c3f08`(→`28ae` A0, 자식 callback), `c3c1c` `c3c96` `c3d10`(→`4706c` A0). I/O port 쓰기와 bank 변경은 U17 자체에 없다.
- [F] 자연 도달(F4 범위 scratch 재생, TB 기준): base(`f4scope/dyn`)와 RNG 초기화+응답 `80` 변형(`dyn_rng1_resp80_f400`) 모두 89개 정적 시작에 닿는다. seed 22 23은 `bbf56` 계열(19 block), 34 35는 `c3d60` 계열(75 block)에 닿는다. 공유 보조(`491c4` `4bfa4` 등)는 base 24 seed, 변형 44 seed가 쓴다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 104 → 109.** [F] 범위 문서의 U17 104는 TB 기준 함수 본문에서 U01~U16 계획분을 뺀 값이다. 현재 routing과 정적 디코드로 다시 계산하면:
   - 빠지는 8: `4590c` `45c9c` `461b4`(이미 U15b `4578a..45b12`·U15c `45b12..461ec`가 routing; 다시 routing하지 않음), TB 분할 5(`bbfea` `bbff2` `bbffc` `bbffe` `bc002`).
   - 더하는 13: `bc012 MOVE.L #bc020,(A6)`가 설치하는 callback 사슬 `bc020` `bc03e` `bc044` `bc04e` `bc054` `bc058` `bc05e` `bc060` `bc070` `bc076` `bc07c` `bc084` `bc08a`(F4 재생 120/400 frame 안에서 도달하지 않아 범위 문서에 없음; 결정 3의 "범위 안 `MOVE.L #imm,(A6)` callback 진입"이라 포함).
   - 104 − 8 + 13 = 109. 권고: 109로 둔다. 대안: `bc020` 사슬을 빼고 96 block(`bc012`가 쓰는 `bc020`이 미연결로 남음). 비권고.
2. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u17.cpp`의 `animation_objects_u17_block`. 오류는 `unsupported animation objects u17 PC`(내부 PC), `objects u17 caller requires known carry`(소비자 6개에 C가 Unknown으로 들어올 때). 메인 지시와 같다.
3. **bank 자료와 파생 읽기.** `MOVE.L 200140.L,22(A6)`/`MOVE.L 200088.L,22(A6)`는 live bus로 읽는다. 이어 `MOVEA.L 22(A6),A1; MOVEA.L d16(A1),A1`은 노드에 방금 쓴 LONG을 다시 읽고 그 값 + d16의 LONG을 live bus로 읽는다(bank window 또는 fixed ROM; 그 밖은 기존 checked 오류). [F] ROM 파일 기준 값: bank `200000`이면 `200140`=`002bc424`, +`d4`=`002bd5ea`; `200088`=`00296528`, +`64`/`68`/`6c`=`0029699a`/`002969ec`/`00296a86`. bank `300000`이면 `200140`=`00008260`(+`d4` → fixed `8334`=`000719c0`), `200088`=`0025aaf8`(+`64`.. → `01000000`). bank `400000`이면 `00223818`(+`d4` → `00000100`), `002000b0`(+`64`.. → `002236b4`..). test에는 합성 bank 바이트를 쓴다(ROM 자료를 test에 넣지 않음). 실제 ROM 차분은 8개 program ROM window로 확인한다.
4. **U18 경계 `4be2c`.** `bc044`(설치 callback)는 `CLR.L 36(A6); JSR 4be2c.L`이다. `4be2c`는 U18 범위다. U18 병합 전에는 `bc044` 진입이 첫 block 뒤 경계에서 멈춘다. 자연 재생에서는 `bc020` 사슬에 닿지 않으므로 자연 seed에 영향이 없다. test는 `4be2c`에서 stop만 확인한다(F4 test 경계 관례).
5. **무효화 탐침.** [F] 이 단위가 routing하는 PC를 다른 test가 "routing 밖" rollback 탐침으로 쓴다(`probes.py`). `make test`가 깨지므로 그 값만 work RAM 탐침(`10fe0c` `10fe10` `10fe14` `10fe18`)으로 바꾼다:
   - `engine/tests/animation_machine_objects_u01_test.cpp` outside의 `482c0`(U01 경계 callee였음). 또 `boundaries()`가 fixture `dd4e2-expire`(stop `482c0`)를 stop 없이 다시 돌려 `482c0`에서 rollback되기를 기대하던 줄에서 그 이름만 뺀다(이제 `482c0`→`ca56`→… 실제 실행으로 이어져 test의 합성 ROM 밖을 읽음). fixture 자체의 stop `482c0`과 block 표 `dd4ec`→`482c0`은 stop이므로 유지.
   - `engine/tests/animation_machine_objects_u02_test.cpp` outside의 `443ea`(`443d2` 범위의 끝 이웃).
   - `engine/tests/animation_machine_objects_u08_test.cpp` outside의 `4929e`(`49274..4929e` 범위의 끝 이웃).
   - `engine/tests/animation_machine_objects_u08b_test.cpp` outside의 `4bfa4`(`4be82..4bfa4` 범위의 끝 이웃).
   - 고치지 않고 보고만: `tools/verify_animation_machine_area_clear.py` 877행(`1c5ea`를 routing 밖 이웃으로 기대), `tools/observe_animation_machine_objects_g1.py` 67행(U01 경계 목록의 `482c0`), 문서 `animation-machine-area-clear-execution.md` 93행(같은 기대).

## 원본 바이트 근거

[F] 코드 9 범위 합계 1,186바이트. 범위 순서로 이어 붙인 SHA256 `a672926df08af5ffbc6f7245f0d5f353dda5c3c4bf89e32753a9e8461e890ba8`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `1c5ea..1c618` | 46 | `38b45a1880fe3905a3e53e0525b239a073de9fca49dca683842f10e1b8c16a7c` | 두 player 노드 `a8` bit 0 정리 `1c5ea` |
| `443ea..44402` | 24 | `959898ed78d7c5a3a64708567601b3eb536601060c7275b6cab85b2c82063f69` | C5 sin/cos 곱 `443ea`(각도 D1 상위 BYTE) |
| `482c0..482ea` | 42 | `0e74d7e4e000cb177c2a2db1bd9da65369c9877067f0046372a68ec6d2696ad1` | `5683` bit 설정 `482c0` |
| `491c4..491e0` | 28 | `54a8160db0a19670c4f8764e6aeacd3943e69d354eda9455cd42ad5af08499af` | C3 부모 `15` 하위 2 bit 복사 `491c4` |
| `4929e..492ae` | 16 | `1df1e0773e21c2ee02da8ee036dfaee537faed45aa67c3ec1f78ae052c6d354d` | C3 화면 좌표 더하기 `4929e` |
| `4bfa4..4bfb4` | 16 | `601522c0b4a274ac19e3cac3f68160a3f1819acba047b2e4de3aed7aa6a138a7` | C4 이동 `4bfa4` |
| `4c020..4c06c` | 76 | `a3c83f29ab7a9ed5c1d1c1185756f71f0eaea0ed502da164688eda399b64671c` | C4 속도 벡터 `4c020` |
| `bbf56..bc08c` | 310 | `7597ed662ea3f0751d720ef8b0c03e7d31d816e1670183d11ead270e6c31af41` | 객체 callback `bbf56` 계열 |
| `c3d60..c3fd4` | 628 | `ed9c4a09f1dca7a997568104017409da68cdd4eab0a6b32334da157655d32abf` | 객체 callback `c3d60` 계열 |

- [F] 범위 밖 이웃(routing): `1c5b0..1c5ea`(F1b area_clear, `1c5e8 RTS`로 끝남), `443d2..443ea`(U02, `443e8 RTS`), `49274..4929e`(U08, `49290` 포함), `492ae..`(U12), `4be82..4bfa4`(U08b, `4bfa2 RTS`).
- [F] 범위 밖 이웃(routing 밖): `1c618..`(다른 함수 `LEA -7348(A5),A0`), `44402..`(0 채움), `482aa..482c0`(U01 `48296..482aa` 뒤 다른 함수), `482ea..`(다른 함수 `BCLR #3,5683(A5)`), `491e0..`(다른 함수 `ADD.W 42(A6),D0`), `4bfb4..`(다른 C4 함수 `BSR.W 4bce0`), `4c06c..`(다른 함수 `MOVE.L 2e(A6),-(A7)`), `bbf04..bbf56`(U16 뒤 `d3802` 인자 자료), `bc08c..`(자식 callback 본문, 실행부 없음), `c3c1c..c3d60`(`4706c` 인자 자료), `c3fd4..`(자료 `ffc0` ...).
- [F] 참조: `bbf56`은 LONG 상수 `e8f64`(stage event 표), `c3d60`은 LONG 상수 `e8ff4`, 자식 callback `c3f92`·`c3f08`은 범위 안 `MOVEA.L #imm,A0`(`c3da0` `c3e96`), 설치 callback 14개는 범위 안 `MOVE.L #imm,(A6)`가 설치한다. `1c5ea` 호출 1곳(`482e2`), `482c0` 호출 6곳(`1d866` `bed28` `c3ec0` `d6cc0` `dcf04` `dd4ec`(U01)), `4c020` 호출 3곳(`4bfa8` `4bfb8` `4bfc4` `BSR.W`), `443ea` 16곳, `491c4` 79곳, `4929e` 16곳, `4bfa4` 105곳(JSR/BSR 101, JMP 4).
- [F] 자료(모두 live bus):
  - banked window: LONG `200140`, 그 값 + `d4`의 LONG; LONG `200088`, 그 값 + `64`/`68`/`6c`의 LONG(결정 3).
  - fixed ROM: WORD `4419e + D2.W`와 `4411e + D2.W`(D2.W = 2·(D1.W >> 8), `0..1fe`; 표 `4411e..4439e`).
  - work RAM 절대: LONG/BYTE `100cb8`·`100da8`(→A0, `289e` 인자, BYTE `a8(A0)` bit 0 BCLR), WORD `10d38e+14`·`+18`(`4929e`).
  - work RAM A5 상대: BYTE `5683`(BSET bit 5 3 1 4), BYTE `549d`(쓰기 `ff`), WORD `547a` `547c`(쓰기), WORD `5d3e` `5d40`(쓰기), BYTE `5d44`(ST).
  - 노드 d16(A6): LONG `(A6)`(callback 설치), LONG `c`(→A0, 부모), BYTE `14`(쓰기) `15`(읽기·BSET bit 0·BTST bit 7·쓰기) `19`(읽기), WORD `1e` `20` `68`(쓰기), LONG `22`(쓰기·읽기), LONG `2e`(쓰기, MOVEM 읽기) `32`(MOVEM 읽기), LONG `36`(CLR·읽기) `3a`(CLR·ADDI·SUB·NEG·CMPI·읽기) `3e`(읽기→A0), WORD `42` `46`(읽기), BYTE `62`(TST), LONG `64`(읽기·쓰기), BYTE `6e`(CMPI) `6f`(읽기), WORD `76`(SUBQ·쓰기·TST·읽기).
  - 부모 노드 d16(A0): BYTE `15`(`491c4`).
- [F] 스택: JSR/BSR 복귀 LONG만. push/pop 없음.

## block 목록과 실행 의미

[F] 109 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `.B`·`.W` 연산은 나머지 bit를 보존하고 `MOVEQ`는 LONG 전체를 쓴다. "F"는 FLOW_ONLY(C 보존), "C"는 소비자다.

**player 노드 정리 `1c5ea` 7**
- `1c5ea`: `LEA 100cb8.L,A0; JSR 289e.L` (F; readiness, C 반환)
- `1c5f6`: `BCC.W 1c600` (C; `289e` 반환 C가 0이면 `1c600`)
- `1c5fa`: `BCLR.B #0,a8(A0)` (F, Z만; →`1c600`)
- `1c600`: `LEA 100da8.L,A0; JSR 289e.L` (F)
- `1c60c`: `BCC.W 1c616` (C)
- `1c610`: `BCLR.B #0,a8(A0)` (F; →`1c616`)
- `1c616`: `RTS` (F)

**C5 `443ea` 1**
- `443ea`: `LSR.W #8,D1; MOVE.W D1,D2; ASR.L #8,D0; MOVE.L D0,D1; ADD.W D2,D2; LEA 4419e(PC),A0; MULS.W (A0,D2.W),D0; MULS.W -80(A0,D2.W),D1; RTS` (MULS: 부호 16×16→32, D0/D1 LONG 전체를 씀; A0=`4419e`)

**`482c0` 4**
- `482c0`: `BSET.B #5,5683(A5); BSET.B #3,5683(A5); BSET.B #1,5683(A5); BSET.B #4,5683(A5); JSR ca56.L` (F; stage_entry)
- `482de`: `JSR 48398(PC)` (F; exit)
- `482e2`: `JSR 1c5ea.L` (F; U17)
- `482e8`: `RTS` (F)

**C3 `491c4` 1, `4929e` 1**
- `491c4`: `MOVEA.L c(A6),A0; MOVE.B 15(A0),D0; MOVE.B 15(A6),D1; ANDI.B #3,D0; ANDI.B #fc,D1; OR.B D0,D1; MOVE.B D1,15(A6); RTS`
- `4929e`: `LEA 10d38e.L,A0; ADD.W 14(A0),D0; ADD.W 18(A0),D1; RTS`

**C4 `4bfa4` 4, `4c020` 4**
- `4bfa4`: `BSR.W 4bc44` (F; U08b)
- `4bfa8`: `BSR.W 4c020` (F; U17)
- `4bfac`: `BSR.W 4bb22` (F; U08b)
- `4bfb0`: `BRA.W 4bf0a` (F; U08b 공통 꼬리, 그 RTS가 `4bfa4` 호출자로 돌아감)
- `4c020`: `MOVE.B #ff,549d(A5); MOVE.L 64(A6),D0; MOVE.B 6f(A6),D1; LSL.W #8,D1; JSR 443ea.L`
- `4c036`: `MOVE.L D0,D3; MOVE.L D1,D2; NEG.L D3; CMPI.B #8,6e(A6); BNE.W 4c060` (BYTE `6e` ≠ 8이면 `4c060`)
- `4c046`: `MOVE.L 36(A6),D0; MOVE.L 3a(A6),D1; SUBI.L #5000,D1; SUB.L D0,D2; SUB.L D1,D3; ASR.L #5,D2; ASR.L #5,D3; ADD.L D0,D2; ADD.L D1,D3` (→`4c060`)
- `4c060`: `MOVEM.L 2e(A6),D0-D1; MOVEA.L 3e(A6),A0; RTS` (F; D0=LONG `2e`, D1=LONG `32`)

**객체 callback `bbf56` 28**
- `bbf56`: `CLR.L 36(A6); CLR.L 3a(A6); JSR 48296.L` (callback 진입; U01)
- `bbf64`: `MOVE.W #1e,76(A6); MOVE.L #bbf70,(A6)` (→`bbf70`)
- `bbf70`: `SUBQ.W #1,76(A6); BCC.W bbf7e` (설치 callback; 감소 전 WORD가 0이 아니면 `bbf7e`)
- `bbf78`: `MOVE.L #bbf80,(A6)` (→`bbf7e`)
- `bbf7e`: `RTS` (F)
- `bbf80`: `BSET.B #0,15(A6); MOVE.W #4f,D0; MOVE.W #35,D1; MOVE.B #0,D2; JSR c6a96.L` (설치 callback; U05)
- `bbf98`: `LEA 26(A6),A0; MOVE.W #e3,20(A6); MOVE.L 200140.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d4(A1),A1; JSR 49f8c.L` (bank 자료; interpreter)
- `bbfc0`: `MOVE.W #8838,68(A6); MOVE.W #8838,1e(A6); MOVE.L #bbfd2,(A6)` (→`bbfd2`)
- `bbfd2`: `CLR.L 36(A6); ADDI.L #ffffb000,3a(A6); JSR 4be34.L` (설치 callback; U08b)
- `bbfe4`: `BTST.B #7,15(A6); BEQ.W bc018` (F, Z만; bit 7이 0이면 `bc018`)
- `bbfee`: `MOVE.W #186a,D0; JSR 3af8.L` (sound)
- `bbff8`: `MOVE.L 3a(A6),D0; ASR.L #2,D0; SUB.L D0,3a(A6); NEG.L 3a(A6); CMPI.L #8000,3a(A6); BGE.W bc018` (LONG `3a` = −(v − (v >> 2 산술)); 부호 LONG ≥ `8000`이면 `bc018`)
- `bc012`: `MOVE.L #bc020,(A6)` (→`bc018`)
- `bc018`: `JSR 49fc6.L` (F; interpreter)
- `bc01e`: `RTS` (F)
- `bc020`: `MOVE.L #a00000,2e(A6); MOVE.W #e3,20(A6); MOVEA.L #bcb32,A1; MOVE.W #100,D0; JSR 49f8c.L` (설치 callback; A0는 그대로)
- `bc03e`: `MOVE.L #bc044,(A6)` (→`bc044`)
- `bc044`: `CLR.L 36(A6); JSR 4be2c.L` (설치 callback; U18 경계)
- `bc04e`: `JSR 49fc6.L` (F)
- `bc054`: `BCC.W bc05e` (C; `49fc6` 반환 C가 0이면 `bc05e`)
- `bc058`: `MOVE.L #bc060,(A6)` (→`bc05e`)
- `bc05e`: `RTS` (F)
- `bc060`: `MOVEA.L #bc08c,A0; MOVE.W #14,D0; JSR 28ae.L` (설치 callback; fade_card 자식 생성)
- `bc070`: `MOVE.L #bc076,(A6)` (→`bc076`)
- `bc076`: `JSR 43e34.L` (F; 설치 callback; cleanup)
- `bc07c`: `TST.B 62(A6); BNE.W bc08a` (BYTE `62` ≠ 0이면 `bc08a`)
- `bc084`: `JSR 49fc6.L` (F)
- `bc08a`: `RTS` (F)


**객체 callback `c3d60` 59**
- `c3d60`: `JSR ca48.L` (F; callback 진입; area_clear)
- `c3d66`: `JSR 48296.L` (F; U01)
- `c3d6c`: `MOVE.W #8810,68(A6); MOVE.W #8810,1e(A6); MOVE.W #cd8,D0; MOVE.B #0,D1; JSR 8ebe.L` (U02)
- `c3d86`: `MOVE.W #ce4,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `c3d94`: `MOVE.B 19(A6),14(A6); JSR 4c0ac.L` (U12)
- `c3da0`: `MOVEA.L #c3f92,A0; MOVE.W #a,D0; JSR 28ae.L` (자식 `c3f92`)
- `c3db0`: `TST.W 76(A6); BNE.W c3dbc`
- `c3db8`: `BRA.W c3e38` (F)
- `c3dbc`: `LEA 26(A6),A0; MOVE.W #ca,20(A6); MOVE.L 200088.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 64(A1),A1; JSR 49f8c.L` (bank 자료)
- `c3de4`: `MOVE.L #20000,64(A6); MOVE.L #c3df2,(A6)` (→`c3df2`)
- `c3df2`: `JSR 4bfa4.L` (F; 설치 callback; U17)
- `c3df8`: `MOVE.W 42(A6),547a(A5); MOVE.W 46(A6),547c(A5); JSR 49fc6.L`
- `c3e0a`: `MOVE.W 76(A6),D0; MOVEQ #0,D1; JSR 4929e.L` (U17)
- `c3e16`: `CMP.W 42(A6),D0; BGT.W c3e24` (부호 WORD D0 > WORD `42`이면 `c3e24`)
- `c3e1e`: `MOVE.L #c3e38,(A6)` (→`c3e24`)
- `c3e24`: `LEA c3c1c(PC),A0; CMPA.W #0,A0; BEQ.W c3e36` (A0 ≠ 0이라 늘 `c3e30`)
- `c3e30`: `JSR 4706c.L` (F; U09)
- `c3e36`: `RTS` (F)
- `c3e38`: `MOVE.W #185c,D0; JSR 3af8.L` (설치 callback; sound)
- `c3e42`: `LEA 26(A6),A0; MOVE.W #ca,20(A6); MOVE.L 200088.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 68(A1),A1; JSR 49f8c.L`
- `c3e6a`: `MOVE.L #c3e70,(A6)` (→`c3e70`)
- `c3e70`: `JSR 4be06.L` (F; 설치 callback; U11)
- `c3e76`: `MOVE.W 42(A6),547a(A5); MOVE.W 46(A6),547c(A5); JSR 49fc6.L`
- `c3e88`: `BCC.W c3eac` (C; `49fc6` 반환 C)
- `c3e8c`: `MOVE.W #1821,D0; JSR 3af8.L`
- `c3e96`: `MOVEA.L #c3f08,A0; MOVE.W #a,D0; JSR 28ae.L` (자식 `c3f08`)
- `c3ea6`: `MOVE.L #c3ec0,(A6)` (→`c3eac`)
- `c3eac`: `LEA c3c1c(PC),A0; CMPA.W #0,A0; BEQ.W c3ebe`
- `c3eb8`: `JSR 4706c.L` (F)
- `c3ebe`: `RTS` (F)
- `c3ec0`: `JSR 482c0.L` (F; 설치 callback; U17)
- `c3ec6`: `MOVE.W 42(A6),5d3e(A5); MOVE.W 46(A6),5d40(A5); ST.B 5d44(A5); MOVE.L #c3edc,(A6)` (→`c3edc`)
- `c3edc`: `JSR 4be06.L` (F; 설치 callback)
- `c3ee2`: `MOVE.W 42(A6),547a(A5); MOVE.W 46(A6),547c(A5); JSR 49fc6.L`
- `c3ef4`: `LEA c3c96(PC),A0; CMPA.W #0,A0; BEQ.W c3f06`
- `c3f00`: `JSR 4706c.L` (F)
- `c3f06`: `RTS` (F)
- `c3f08`: `MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L` (자식 callback 진입; U08)
- `c3f12`: `JSR 491c4.L` (F; U17)
- `c3f18`: `MOVE.W #fff1,68(A6); MOVE.W #fff1,1e(A6); MOVE.W #cd8,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `c3f32`: `MOVE.W #ce4,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `c3f40`: `MOVE.B 19(A6),14(A6); LEA 26(A6),A0; MOVE.W #ca,20(A6); MOVE.L 200088.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 6c(A1),A1; JSR 49f8c.L`
- `c3f6e`: `MOVE.L #c3f74,(A6)` (→`c3f74`)
- `c3f74`: `JSR 43e34.L` (F; 설치 callback)
- `c3f7a`: `JSR 49fc6.L` (F)
- `c3f80`: `JSR 288c.L` (F; stage_event_ops, C 반환)
- `c3f86`: `BCS.W c3f90` (C; `288c` 반환 C가 1이면 `c3f90`)
- `c3f8a`: `JMP 2a00.L` (F; fade_card 자기 삭제)
- `c3f90`: `RTS` (F)
- `c3f92`: `MOVEQ #0,D0; MOVE.W #12,D1; JSR 49290.L` (자식 callback 진입)
- `c3f9e`: `JSR 491c4.L` (F)
- `c3fa4`: `MOVE.L #c3faa,(A6)` (→`c3faa`)
- `c3faa`: `JSR 43e34.L` (F; 설치 callback)
- `c3fb0`: `JSR 288c.L` (F)
- `c3fb6`: `BCS.W c3fc0` (C)
- `c3fba`: `JMP 2a00.L` (F)
- `c3fc0`: `LEA c3d10(PC),A0; CMPA.W #0,A0; BEQ.W c3fd2`
- `c3fcc`: `JSR 4706c.L` (F)
- `c3fd2`: `RTS` (F)

(수: `1c5ea` 7 + `443ea` 1 + `482c0` 4 + `491c4` 1 + `4929e` 1 + `4bfa4` 4 + `4c020` 4 + `bbf56` 계열 28 + `c3d60` 계열 59 = 109.)

## 구현 범위와 규약

- routing 9 범위(위 표). 짝수 PC 593개 중 block 시작 109, 내부 484. 내부 PC 직접 진입은 `unsupported animation objects u17 PC`다. 경계 callee `4be2c`(U18), 자식 callback `bc08c`와 범위 이웃은 이 실행부 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **FLOW_ONLY 54개**(C 보존): `1c5ea` `1c5f6` `1c5fa` `1c600` `1c60c` `1c610` `1c616` `482c0` `482de` `482e2` `482e8` `4bfa4` `4bfa8` `4bfac` `4bfb0` `4c060` `bbf7e` `bbfe4` `bc018` `bc01e` `bc04e` `bc054` `bc05e` `bc076` `bc084` `bc08a` `c3d60` `c3d66` `c3db8` `c3df2` `c3e30` `c3e36` `c3e70` `c3e88` `c3eb8` `c3ebe` `c3ec0` `c3edc` `c3f00` `c3f06` `c3f12` `c3f74` `c3f7a` `c3f80` `c3f86` `c3f8a` `c3f90` `c3f9e` `c3faa` `c3fb0` `c3fb6` `c3fba` `c3fcc` `c3fd2`.
- **known carry 생산 0개**. 그 밖 55개(MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/ADD/ADDI/SUB/SUBI/SUBQ/NEG/ASR/LSR/LSL/ANDI/OR/MULS/ST, `MOVE.L #imm,(A6)` block, bank 표 block)는 Unknown이다.
- **소비자 6개**: `1c5f6` `1c60c` `bc054` `c3e88` `c3f86` `c3fb6`. 들어오는 C가 Unknown이면 `objects u17 caller requires known carry`(상태 보존).
- 산술: `ASR.L`은 부호 bit 복제, `NEG.L`/`SUB.L`/`ADD.L`/`ADDI.L`은 LONG mod 2^32, `MULS.W`는 부호 16×16→32 LONG, `CMPI.L #8000`+`BGE`와 `CMP.W`+`BGT`는 부호 비교(정의된 unsigned 연산으로 구현), `SUBQ.W #1`+`BCC`는 감소 전 WORD = 0일 때만 borrow.
- 루프 없음. I/O port 쓰기 없음. bank 변경 없음. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM 읽기, physical span 밖 bank 읽기는 기존 checked 오류다.

## 의존·경계

- [F] U17 → 기존: readiness `289e`, stage_entry `ca56`, exit `48398`, area_clear `ca48`, U01 `48296`, U02 `8ebe`, U05 `c6a96`, U08 `49290`, U08b `4be34` `4bc44` `4bb22` `4bf0a`, U09 `4706c`, U11 `4be06`, U12 `4c0ac`, interpreter `49f8c` `49fc6`, sound `3af8`, fade_card `28ae` `2a00`, cleanup `43e34`, stage_event_ops `288c`.
- [F] U17 → 경계: `4be2c`(U18). 자식 callback `bc08c`(`28ae`)는 쓰기만 하고 실행하지 않는다.
- [F] 다른 단위 → U17: U01 `dd4ec JSR 482c0`(지금까지 U01의 경계 callee), stage event 표 `e8f64`(`bbf56`)·`e8ff4`(`c3d60`), 그리고 공유 보조의 범위 밖 호출자(위 "참조").

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, TB 기준)에서 U17 block에 닿는 seed:
- `bbf56` 계열: seed 22 23(19 block). `c3d60` 계열: seed 34 35(75 block, 공유 보조 포함). 둘 다 frame 0에서 첫 미연결 callback이다.
- 공유 보조만: base seed 8 9 30~33 36 37 42 43 62 63 68~71 80 81 116 117, RNG+`80` 변형은 여기에 2 3 12 13 18 19 26 27 38 39 76 77 96~99 102~105가 더해진다.
- 109 정적 시작 중 89개가 두 변형에서 자연 도달한다. 미도달 20개(`1c5fa` `1c610` `4c046` `bc012` `bc020` `bc03e` `bc044` `bc04e` `bc054` `bc058` `bc05e` `bc060` `bc070` `bc076` `bc07c` `bc084` `bc08a` `c3db8` `c3f8a` `c3fba`)는 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] 기준 C++ 차분(작업 트리 `9682aed`, F2 프레임 패스 142 seed, scratch 복사본 `tools/verify_animation_machine_scheduler_f4.py`): 일치 pass 10,498개·node 79,680개, 불일치 0, 자연 완주 95 seed. 첫 미연결 callback `bbf56` 2(seed 22 23), `c3d60` 2(34 35). RNG 초기화 400 frame 차분(`tools/verify_animation_machine_scheduler_rng_f4.py` 복사본): 일치 pass 24,646개·node 169,037개, 불일치 0, complete 61.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 109 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown; 소비자는 Unknown이면 오류), zero-step, 내부 484 PC 정확한 오류, 홀수 PC, 경계 `4be2c` stop(U18 PC는 stop만), rollback 탐침은 work RAM `10fe00..10fefe`만. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력과 합성 bank·표 바이트)로 비교한다.
- 실제 ROM 차분: 각 block을 8개 program ROM window(physical_rom)로 C++와 Unicorn에서 같은 결과로 실행하고, 소비자 6개의 known C는 실제 `289e` `49fc6` `288c` 실행 결과의 native 분기로 확인한다.
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 기준 이상, 불일치 0, complete 61 이상.

## 미확인·범위 밖

1. [I] `1c5ea`는 두 player 노드(`100cb8` `100da8`)가 살아 있지 않으면(`289e` C=1) `a8` bit 0을 지운다. F1b `1c5b0`(같은 두 노드에 bit 설정)의 반대 동작으로 보인다. `482c0`은 `5683` bit 5 3 1 4를 세운 뒤 `ca56` `48398`과 이 정리를 부르는 상태 전환으로 보인다. 게임 의미는 미확인이다.
2. [I] `443ea`는 U02 `443d2`와 같은 sin/cos 표에서 각도 D1 상위 BYTE로 (D0>>8)·sin, (D0>>8)·cos를 낸다. `4c020`은 속도 `64`와 각도 `6f`로 이동 벡터를 만들고(BYTE `6e`=8이면 `36`/`3a` 쪽으로 1/32 끌어당김), `4bfa4`는 U08b 이동 꼬리(`4bc44` `4bb22` `4bf0a`)와 묶는 C4 이동 함수로 보인다.
3. [I] `bbf56`은 30 frame 대기 뒤 animation `e3`(bank 표 `200140`+`d4`)으로 나타나 위로 튀어 오르다가(`3a` 속도 반사·감쇠, 효과음 `186a`) 멈추면 `bc020` 사슬(U18 `4be2c`, 자식 `bc08c`, cleanup)로 넘어가는 물체로 보인다. `c3d60`은 palette `cd8`/`ce4`, animation `ca`(bank 표 `200088`+`64`/`68`/`6c`), 자식 `c3f92`/`c3f08`, 효과음 `185c`/`1821`, 화면 좌표 `547a`/`547c`·`5d3e`/`5d40`를 쓰는 연출 객체로 보인다.
4. [U] 경계 `4be2c`(U18)와 자식 callback `bc08c`의 본문과 실행 결과는 U17 밖이다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/u17/`(`u17.py` block·범위·SHA 계산, `scope.py` `trav.py` `hroute_u17.py` `disu17.py`, `refs.py` `nextins.py` `chain.py` `probes.py` `reach.py`; 저장소 밖).
