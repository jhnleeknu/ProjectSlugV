# 객체 callback F4 U19: 공중 객체 `b6300`·`b6338`·`b6362` 계열(설치 `b6406` `b6422` `b64a8` `b68ba` `b690a` `b69b6` `b6a2a` `b6ac8` `b6aee` `b6b7c`), 목표 선택 `b7b4c`/`484e2`, palette 보조 `b7c9e`, 객체 `ba78c`·`d6d4a`·`d81cc`/`d81e8`·`dbefe` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U19 행과 그 "메인 결정"이다. 단위 형식과 규약은 U17 계약(`animation-machine-objects-u17-contract.md`, SHA256 `e91a946220814dd7d025a3147cc12561db36c6078cb81fe904afc62c878d2894`, 같은 bank 표 읽기·설치 callback 사슬 형식), 동시 진행 U18 계약 초안(작업 트리 `metalslug-u18`, SHA256 `ee88bd6cb3834a7ec9b1040d6fd984ee92fc2b81a7d8aae9460bef070830f3b7`, 같은 객체 함수 표 `b6300`~`b6368`의 다른 진입 `b631c`와 공유 보조 `b7bc2` `b7cfa` `b7e06` `b7e5c` `b76bc` `b76d2`), U01 계약(SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`, `1aa7e` 반환 C), U05 계약(SHA256 `77fd4062f3935d0e8b2989ad65bed395f43fa7bd37f33309c7a29fa9f512dafc`, `1ab02` 반환 C), frame helper U1 계약(SHA256 `785c3fba8bf05bd405ad8c0898738504367ed0c3195ffb9aa80a0a3774c861e0`, `49392` 반환 C와 `b4a38`/`b4a6c` 소비)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee와 다른 단위의 PC는 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01~U17 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U19에는 없음). `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc, Z만 바꾸는 `BTST`/`BSET`/`BCLR`)만인 block과 callee C를 소비하는 단독 Bcc는 FLOW_ONLY다. `SUBQ` block은 Unknown이다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C를 소비자에서 쓰려면 native 분기 결과로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U19의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료(`2001a8` `2001ac` `2001c0` `2001cc` `2001d4`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u19`(HEAD `88a1123` = U16까지 통합 + U17, `engine/src/animation_machine.cpp` SHA256 `ac701b01d8829acb8f89ebf9ba9ada38498188a74b2d02feb27fcfd9b0f3fb2e`, routing 규칙 54개)을 참조했다. 동시에 진행되는 U18(작업 트리 `metalslug-u18`)의 계약 초안 코드 범위(`46c68..46d1c` `4be2c..4be34` `b631c..b632a` `b66c8..b67b2` `b76a4..b7742` `b7bc2..b7c9e` `b7cfa..b7d2e` `b7e06..b7e74` `ea5e0..ea5f0` `ea636..ea680` `ea762..ea85a` `ea908..eaa00` `eaa54..eaa5a`)의 PC는 경계(stop만 확인)로 둔다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/u19/u19.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] U19는 **block 시작 174개**다. 범위 문서 U19 행의 135와 다르다(아래 결정 1). 범위 문서 `units.pkl` U19의 함수 20개(`484e2` `b6300` `b6338` `b6362` `b6406` `b68ba` `b68be` `b690a` `b69b6` `b6a2a` `b6ac8` `b7b4c` `b7c9e` `ba78c` `ba7d8` `d6d4a` `d81cc` `d81e8` `d82aa` `dbefe`) 본문은 현재 routing·U18 경계 기준으로 정적 디코드하면 정확히 135 block이다. 여기에 그 본문 안 `MOVE.L #imm,(A6)`이 설치하는 callback 진입과 그 본문 39 block(`b6422` 사슬 13, `b6aee` 사슬 9, `d831e` 사슬 16, `dbf2a` 1)을 더한다.
  - 범위 문서 범위 문자열 `b6300..b641e` `b76bc..b7740` `b7b4c..b7cf2`는 함수 본문 최소·최대 범위다. 그 안의 `b631c..b632a`·`b76a4..b7742`·`b7bc2..b7c9e`는 U18 코드이고, `b630e..b631c`(진입 `b630e`, 범위 문서 U28)·`b632a..b6338`(진입 `b632a`, 미배정)·`b6346..b6362`(진입 `b6346` `b6354`, U28/미배정)·`b6506..`(U28 본문)는 U19가 아니다.
  - 공유 보조 `484e2` 3, 객체 함수 표 진입 `b6300` 2·`b6338` 2·`b6362` 2, 상태 본문 `b6370`~`b6502` 24(설치 `b6406` `b6422` `b64a8`; 그중 `b6422` 사슬 13), `b68ba`~`b6b9c` 51(설치 `b68be`(범위 밖 설치) `b690a` `b69b6` `b6a2a` `b6ac8` `b6aee` `b6b7c`; 그중 `b6aee` 사슬 9), 목표 선택 `b7b4c` 20, palette `b7c9e` 8, 객체 `ba78c` 10(설치 `ba7d8`), `d6d4a` 1, 객체 `d81cc`/`d81e8` 42(설치 `d82aa` `d831e` `d8394`; 그중 `d831e` 사슬 16), 객체 `dbefe` 9(설치 `dbf2a`).
  - 코드 11 범위, 2,144바이트, 460명령이다. 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx는 없다. routing 짝수 PC는 1,072개, 내부 PC는 898개다.
- [F] **경계 callee(실행부 없음)**: U18 `b7bc2`(`b6300` `b6338` `b6362` BSR), `b7cfa`(`b6406` `b64a8` `b69b6` `b6b7c`), `b7e06`(`b64b6` `b64ce`), `b7e5c`(`b6410`), `b76bc`(`b6a26` `b6aea` `b6b90` BRA), `b76d2`(`b641e` `b6502` BRA), `4be2c`(`b6ac8` `d82be` `d83a8`); 범위 문서 U20 `492d0`(`b6b86`); 어느 단위에도 없는 `b7b30`(`b7b68` `b7b7c` BSR.B, 범위 문서 U19 "경계 callee"), `d83c0`(`d8384`), `e9112`(`d831e`).
- [F] **범위 밖 설치 callback(쓰기만 함) 2개**: `b7100`(`b6a0c`), `b749c`(`b6a1a`). 둘은 `b7100..b76a4` 상태 사슬 86 block의 진입이다(아래 결정 1, 분할 제안 U19b).
- [F] 기존 실행부로 나가는 호출·점프: interpreter `49f8c`(bank 표 block 14곳)·`49fc6`(`b640a` `b64ac` `b6a20` `b6ae4` `b6b80` `ba7e4` `d82c4` `d83ae`, C 반환), U11 `496c2`(`b64e6` `d829e`)·`4be06`(`b68fa` `d82b4` `d839e`), frame helper `6f1c2`(`b69f4`)·`49392`(`b7b56` `b7b70`, C 반환), U12 `492c8`(`b6ace` `ba7de`)·`490ba`(`d8220`)·`4c0ac`(`d8238`), cleanup `8ff4`(`b7c9e`)·`43e34`(`ba7d8`)·`46ef4`(`d8388`), U02 `8ebe`(`b7cae` `b7cca` `b7ce4` `d8204`), U05 `c6a96`(`ba78c`)·`1ab02`(`ba7ea`, C 반환), U01 `4b54e`(`d82ca`)·`1aa7e`(`d8308`, C 반환), U09 `47070`(`d8302`), sound `3af8`(`dbefe`), fade_card `28ae`(`dbf34`)·`2a00`(`ba7f8` `d6d4a` `d8316` `d83b8` `dbf18` `dbf44` JMP). U19 안 호출: `b68ba JSR b7c9e`, `b7b4c JSR 484e2`.
- [F] **flag**:
  - 블록 경계를 건너는 C 소비 block **10개**(모두 FLOW_ONLY 단독 Bcc): `b6414 BCC`(U18 `b7e5c` 반환), `b64b2 BCC` `d83b4 BCC`(`49fc6` 반환), `b7b52 BCS`(U19 `484e2` 반환), `b7b64 BCC` `b7b78 BCC`(`49392` 반환, frame helper `b4a38`/`b4a6c`과 같은 생산자), `b7b6a BCC` `b7b7e BCC`(경계 `b7b30` 반환), `ba7f4 BCC`(U05 `1ab02` 반환), `d8312 BCC`(U01 `1aa7e` 반환).
  - known carry 생산 block **4개**: `484ec`(`ORI.B #1,CCR; RTS`: Set), `484f2`(`ANDI.B #fe,CCR; RTS`: Clear), `b7bb6`(`ORI.B #1,CCR; RTS`: Set), `b7bbc`(`ANDI.B #fe,CCR; RTS`: Clear). 소비자는 `b7b52`(U19)와 범위 밖 `1ee3c` `b7a68`(`484e2` 호출자), U18 `b76c4`와 범위 밖 `b885a`(`b7b4c` 호출자)다. [F] `nextins`: `484e2` 호출 3곳 다음 명령은 모두 Bcc(`bcc` 2, `bcs` 1), `b7b4c` 호출 2곳(`b76c0` `b8856`) 다음은 모두 `BCC`다.
  - block 안에서 만들고 쓰는 flag: `b6370` `b6422` `b690a` `b6a32` `b6aee`(`CMPI.W #0,D0` 뒤 `BNE`), `b68be` `b68e4`(`CMPI.W` 뒤 `BNE`), `b69de`(`TST.B` 뒤 `BNE`), `b69e6`(`SUBQ.W #1` 뒤 `BCC`, borrow = WORD가 0), `b69fa`(`TST.W D0` 뒤 `BMI`), `b7b82`(`MOVE.L (A7),D0` 뒤 `BMI`), `b7b88`(`CMP.W` 뒤 `BCC`, 무부호 ≥), `b7b9a`(`MOVE.L (A7)+,D1` 뒤 `BMI`), `b7ba6`(`CMPI.L` 뒤 `BEQ`), `d8242` `d8324`(`TST.W` 뒤 `BNE`), `d82e4`(`SUBI.W`·`CMPI.W #80` 뒤 `BCS`, 무부호 작음), `dbf0c`(`CMPI.B` 뒤 `BEQ`), `dbf2a`(`SUBQ.W #1` 뒤 `BCS`, borrow = WORD가 0), BTST(+MOVE) 뒤 Bcc(Z만: `484e2` `b6900` `b698a` `b69ba` `b69ce` `b6a00` `b6a12` `b6ad4` `b7ca4` `d82aa` `d82d0` `d8394`).
- [F] 읽는 자료: banked window LONG `2001a8`/`2001ac`(객체 표 block 10곳)와 그 값 + `sext16(4·(LONG 표 값).W)`의 LONG, banked window LONG `2001c0`(+`4`/`8`), `2001cc`(+`7c`/`80`), `2001d4`(+`38`)와 그 값 + d16의 LONG. fixed ROM LONG 표 `b7f1c` `b7f24` `b7f3c` `b7f6c` `b7f74`(+`sext16(4·8e(A6).W)`), WORD 표 `b7f18`(+`sext16(2·8e(A6).W)`), WORD 표 `d841a`(+`sext16(2·80(A6).W)`). 주소만 넘기는 상수: `d841e`(→ LONG `86(A6)`), `cbce8`(→`490ba` A0), `ba784`(→`1ab02` A0), `d8440`(→`1aa7e` A0), `4841a`(→`28ae` A0, 자식 callback). I/O port 쓰기와 bank 변경은 U19 자체에 없다.
- [F] 자연 도달(F4 범위 scratch 재생 `f4scope`, TB 기준): base(`dyn`) 94 block(seed 8 9 14 15 36 37 42 43 62 63 80 81), RNG 초기화+응답 `80`(`dyn_rng1_resp80_f400`) 95 block(seed 2 3 12 13 26 27 추가; `ba7d8` 추가). 첫 미연결 callback(기준 C++ 차분): `b6338` 2, `b6362` 2, `ba78c` 2, `dbefe` 2.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 135 → 174, `b7100` 상태 사슬 86은 분할(U19b 제안).** [F] 범위 문서 U19 함수 20개 본문(설치 callback을 따라가지 않음)은 현재 routing과 U18 경계로 다시 계산해도 135 block이다. 결정 3의 "`MOVE.L #imm,(A6)` callback 진입"을 따라가면 전이 closure가 260 block이다(+125). 그 125의 내역:
   - `b6418 MOVE.L #b6422`·`b64a2 MOVE.L #b64a8` → `b6422`~`b6502` 13(같은 상태 본문의 이어지는 코드, `b6506`(U28) 직전에서 끝남).
   - `b69d8`/`b69ee MOVE.L #b6aee`·`b6b76 MOVE.L #b6b7c` → `b6aee`~`b6b90` 9(`b6ba0` 직전에서 끝남; `b6ba0`은 U18 `b76c8`이 설치하는 다른 상태).
   - `d82de MOVE.L #d831e`·`d838e MOVE.L #d8394` → `d831e`~`d83be` 16. `dbf24 MOVE.L #dbf2a` → `dbf2a` 1(본문 안 fall-through 코드).
   - `b6a0c MOVE.L #b7100`·`b6a1a MOVE.L #b749c` → `b7100..b76a4` 86(상태 15개 `b7100` `b718c` `b71ae` `b723c` `b72f2` `b7386` `b73a0` `b7444` `b7474` `b749c` `b7528` `b754e` `b75dc` `b7618` `b76a4`(U18) 사슬; 미배정 callee `b7d2e` `b7d3c` 호출).
   - 260은 단위 상한(~220)을 넘는다. 권고: U19는 135 + 39 = **174**(위 앞의 세 묶음)로 하고, `b7100`/`b749c` 사슬 86 block은 별도 단위 **U19b**로 분할한다. U19에서 `b6a0c`/`b6a1a`는 LONG 쓰기만 하고 `b7100`/`b749c`는 실행부 없는 경계다. [F] F4 범위 scratch 재생 7변형(`dyn` base 120 frame, `dyn_rng0_resp00_f400`(18 seed), `dyn_rng0_resp80_f400`, `dyn_rng0_respnone_f400`, `dyn_rng1_resp80_f400`, `dyn_rng1_respnone_f120`, `dyn_rng1_respnone_f400`) 어디에서도 `b6a0c` `b6a1a`와 `b7100..b76a4`는 실행되지 않았다. 따라서 분할은 자연 seed에 영향이 없다. 대안: 260 전체를 한 단위로(상한 초과), 또는 범위 문서대로 135(설치 callback 39 block을 미연결로 남김). 비권고.
2. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u19.cpp`의 `animation_objects_u19_block`. 오류는 `unsupported animation objects u19 PC`(내부 PC), `objects u19 caller requires known carry`(소비자 10개에 C가 Unknown으로 들어올 때). 메인 지시와 같다.
3. **bank 자료와 파생 읽기.** 모두 live bus로 읽는다(bank window 또는 fixed ROM; 그 밖은 기존 checked 오류).
   - 객체 표 block(`b637c` `b63b8` `b642e` `b646a` `b6916` `b6952` `b6a3e` `b6a7a` `b6b02` `b6b3e`): `MOVE.L bank.L,22(A6)`, `MOVEA.L #T,A1`, D0.W를 두 번 `ADD.W`(D0 상위 WORD 보존), `MOVE.L (A1,D0.W),D0`(LONG 전체), `MOVEA.L bank.L,A1`(bank LONG을 다시 읽음), D0.W를 두 번 `ADD.W`, `MOVEA.L (A1,D0.W),A1`. index는 WORD mod 2^16을 부호확장한다. 표 T는 fixed ROM `b7f1c`(`b637c`/`b63b8`) `b7f24`(`b642e`/`b646a`) `b7f6c`(`b6916`/`b6952`) `b7f3c`(`b6a3e`/`b6a7a`) `b7f74`(`b6b02`/`b6b3e`)다. `8e(A6)`=0이면 `2001a8`(animation `1b3`), 아니면 `2001ac`(animation `1bb`).
   - `d824a`/`d832c`: bank `2001c0`(animation `1e3`), +`4`/+`8`. `d8276`/`d8358`: bank `2001cc`(animation `1fb`), +`7c`/+`80`. `ba7aa`: bank `2001d4`(animation `20b`), +`38`. 형식은 U17 `bbf98`와 같다(`22(A6)`에 쓴 LONG을 다시 읽음).
   - [F] ROM 파일 기준 값(bank `200000`): `2001a8`=`002d0086`, `2001ac`=`002d0e90`, `2001c0`=`002cdeaa`, `2001cc`=`002cf71a`, `2001d4`=`002d49d8`. bank `300000`이면 `03959560` `03c78860` `00028260` `01258260` `01e78260`, bank `400000`이면 `00223b70` `00223b88` `00223c00` `00223c48` `00223c70`. fixed ROM 표: `b7f18` WORD = `0d88 0d8c`, `b7f1c` LONG = `1 4 8 5`, `b7f24` = `8 5 2 6`, `b7f3c` = `11 3 9 7`, `b7f6c` = `f 1 f 2`, `b7f74` = `f 2 10 d`, `d841a` WORD = `03ab 00cf`. 표 읽기는 index 상한 없이 원본 그대로 live bus가 정한다(점프 표가 아니라 자료 읽기다). test에는 합성 bank 바이트를 쓴다(ROM 자료를 test에 넣지 않음; fixed ROM 표 위치에도 합성 바이트).
4. **U18 경계.** `b7bc2` `b7cfa` `b7e06` `b7e5c` `b76bc` `b76d2` `4be2c`는 U18 범위다. U18 병합 전에는 U19 block이 그 PC에서 멈춘다(`unsupported animation machine PC`). test는 그 PC에서 stop만 확인한다(F4 test 경계 관례). 자연 seed 해제는 U18+U19 조합 scratch 트리에서 따로 잰다.
5. **`b7b4c` 스택 LONG.** `MOVE.L #ffffffff,-(A7)`(push LONG), `MOVE.L A0,(A7)`(덮어씀), `MOVE.L (A7),D0`(읽기), `MOVE.L (A7)+,D1`(pop LONG)은 work RAM 스택 LONG이다. A7 순변화는 `b7b56`에서 −4, `b7b9a`에서 +4다. `b7b56`~`b7b98`를 단독 진입하면 그 LONG은 선언 RAM이다.
6. **무효화 탐침.** [F] `engine/tests`·`tools`·`engine/src`·`docs/analysis`에서 U19 범위 PC를 rollback·outside 탐침으로 쓰는 곳은 없다(`probes19.py`: `animation-machine-caller-inventory.md`의 호출자 나열 3줄뿐). 고칠 test 없음.

## 원본 바이트 근거

[F] 코드 11 범위 합계 2,144바이트. 범위 순서로 이어 붙인 SHA256 `47e695f63c5ad2e0ed6a101b7a9c70b7b742b136255998d52689f315df6c8687`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `484e2..484f8` | 22 | `043467938b6c46ff37a77ccb215c898379ca3754a565eee48f317878ead19b67` | `5683` bit 0 → C `484e2` |
| `b6300..b630e` | 14 | `45973d6d06f19b53af88920b6e858f0f688a41daea67f043d6aa1b1b7cdc1ae1` | 함수 표 진입 `b6300` |
| `b6338..b6346` | 14 | `3909b93141664bbffcfd07f0405a4f52bcbfc877512d8171c889a63fddb64bb4` | 함수 표 진입 `b6338` |
| `b6362..b6506` | 420 | `9857ffdc3e286f196b3f17b80d8064ecbc87ab00e1264185756679968e5d605d` | 진입 `b6362`, 상태 본문 `b6370`, 설치 `b6406` `b6422` `b64a8` |
| `b68ba..b6ba0` | 742 | `4b579ca5ef04516a7f397423dc14752b79215ad48cc542cbc831516c2c8b7249` | 상태 `b68ba`, 설치 `b68be` `b690a` `b69b6` `b6a2a` `b6ac8` `b6aee` `b6b7c` |
| `b7b4c..b7bc2` | 118 | `9533a0f70d851655be9fa2bcdedc60df23c1afdced1ee6a3f68e50e480f570e1` | 목표 선택 `b7b4c` |
| `b7c9e..b7cfa` | 92 | `b695b22efd1f79323780067abed97a96eff230370638c7c1cc7e1543625de80a` | palette `b7c9e` |
| `ba78c..ba800` | 116 | `9af48845217ab03a4af688f4fe42404fd78d07eca7beb5e91a432ce0645d4568` | 객체 `ba78c`, 설치 `ba7d8` |
| `d6d4a..d6d68` | 30 | `1a13af600f76fb80e89c533b6d5499a60705ff4d63581f5991d5401fa6170fe1` | 객체 `d6d4a` |
| `d81cc..d83c0` | 500 | `291ed9a31ec4aa5aa44895b7077047da5e7029b891029a57f1130120fcd732a5` | 객체 `d81cc` `d81e8`, 설치 `d82aa` `d831e` `d8394` |
| `dbefe..dbf4a` | 76 | `89680c8301bac4ab792d3951f82a82346c180d0826c75e21855e84dbfbf20a85` | 객체 `dbefe`, 설치 `dbf2a` |

- [F] 범위 밖 이웃: `484d4..484e2`(앞 함수), `484f8..`(다른 함수), `b62f0..b6300`(앞 자료), `b630e..b6338`(진입 `b630e`(U28), `b631c`(U18), `b632a`(미배정)), `b6346..b6362`(진입 `b6346` `b6354`), `b6506..b66c8`(U28 본문 `b6506`, `b65f0`), `b67b2..b68ba`(U18 범위 밖 설치 callback `b67b2`), `b6ba0..b7100`(다른 상태 `b6ba0`, U18 `b76c8`이 설치), `b7100..b76a4`(분할 제안 U19b), `b7b30..b7b4c`(경계 `b7b30`), `b7bc2..`(U18), `b7c9e` 앞 `b7bc2..b7c9e`(U18), `b7cfa..`(U18), `ba784..ba78c`(자료 `ba784`), `ba800..`(다른 함수), `d6d22..d6d36`(U01), `d6d68..`(다른 함수), `d81c0..d81cc`(자료), `d83c0..`(경계 `d83c0`), `d841a..`(자료), `dbefe` 앞 `dbe98..dbeea`(U28), `dbf4a..dbf5e`(`RTS` 1개와 callback 기록 자료 `dbf58`), `dbf5e..`(U27).
- [F] 참조: stage event 표 LONG `e8ed4`(`b6300`) `e8ee4`(`b6338`) `e8ef0`(`b6362`) `e8f4c`(`ba78c`) `e8fe4`(`d6d4a`) `e8cf0`(`d81cc`) `e8cf4`(`d81e8`), callback 기록 LONG `dbf58`(`dbefe`), `a1b4`(`b6300`). `b68ba` 설치 3곳(`b64fc` U19, `b66b8`(U28 본문), `b68a6`(U18 범위 밖 설치 callback `b67b2` 본문)), `b68be` 설치 3곳(`b724c` `b7492`(U19b), `b76b2`(U18)), `b6a2a` 설치 2곳(`b69c4` U19, `b75fe` U19b). `484e2` 호출 3곳(`1ee36` `b7a62` `b7b4c`), `b7b4c` 호출 2곳(`b76c0`(U18) `b8856`), `b7c9e` 1곳(`b68ba`), `b7b30` 2곳(`b7b68` `b7b7c`), `d83c0` 1곳(`d8384`), `e9112` 48곳.
- [F] 자료(모두 live bus):
  - banked window: LONG `2001a8` `2001ac` `2001c0` `2001cc` `2001d4`와 그 값 + d16 / 표 index(결정 3).
  - fixed ROM: LONG `b7f1c`/`b7f24`/`b7f3c`/`b7f6c`/`b7f74` + `sext16(4·D0.W)`, WORD `b7f18 + sext16(2·D0.W)`, WORD `d841a + sext16(2·D0.W)`.
  - work RAM 절대: BYTE `100012`(`dbf0c` `CMPI.B #1`).
  - work RAM A5 상대: BYTE `5683`(BTST bit 0), WORD `5426` `5428` `542a` `542c`(쓰기, `d6d4a`).
  - 노드 d16(A6): LONG `(A6)`(callback 설치), WORD `8e`(쓰기·읽기), WORD `20`(쓰기), LONG `22`(쓰기·읽기), LONG `96` `98`(쓰기), BYTE `5e`(CLR), BYTE `61`(BCLR bit 7·BTST bit 0·BTST bit 7), WORD `84`(쓰기·SUBQ), WORD `76`(CMPI·TST.B(BYTE `76`)·SUBQ·쓰기·읽기), BYTE `15`(BCLR/BSET bit 0·BTST bit 0·bit 7), LONG `64`(쓰기·CLR), LONG `36` `3a`(CLR), BYTE `9e`(쓰기), BYTE `9f`(BTST bit 1·BSET bit 0), WORD `90`(쓰기), BYTE `19`(읽기)·`14`(쓰기), WORD `68` `1e`(쓰기), WORD `80` `82` `84`(쓰기·읽기), LONG `86`(쓰기·읽기), WORD `54`(쓰기), WORD `42`(읽기), WORD `78` `7a` `7c`(읽기, `d6d4a`).
  - 다른 노드: WORD `42(A0)`·`42(A2)`(`b7b88`, A0=`49392` 반환, A2=스택 LONG).
- [F] 스택: JSR/BSR 복귀 LONG, `b7b4c`의 LONG 1개(결정 5).

## block 목록과 실행 의미

[F] 174 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)·`(An,Dn.W)`는 부호확장한다. `.B`·`.W` 연산은 나머지 bit를 보존하고 `MOVEQ`는 LONG 전체를 쓴다. "F"는 FLOW_ONLY(C 보존), "C"는 소비자, "P"는 known C 생산자다. "bankT(b,k,T)"는 결정 3의 객체 표 형식 `LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L b.L,22(A6); MOVEA.L #T,A1; ADD.W D0,D0; ADD.W D0,D0; MOVE.L (A1,D0.W),D0; MOVEA.L b.L,A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L`, "bankD(b,k,d)"는 `LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L b.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.L`다.

**`484e2` 3** (C = BYTE `5683(A5)` bit 0)
- `484e2`: `BTST.B #0,5683(A5); BEQ.W 484f2` (F, Z만)
- `484ec`: `ORI.B #1,CCR; RTS` (P: Set)
- `484f2`: `ANDI.B #fe,CCR; RTS` (P: Clear)

**함수 표 진입 6** (`8e(A6)` = 0/1, U18 `b7bc2` 초기화)
- `b6300`: `MOVE.W #0,8e(A6); BSR.W b7bc2` (U18 경계)
- `b630a`: `BRA.W b6370` (F)
- `b6338`: `MOVE.W #1,8e(A6); BSR.W b7bc2`
- `b6342`: `BRA.W b6370` (F)
- `b6362`: `MOVE.W #1,8e(A6); BSR.W b7bc2`
- `b636c`: `BRA.W b68ba` (F)

**상태 `b6370` 24** (`b6370`~`b641e` 11, 설치 사슬 `b6422`~`b6502` 13)
- `b6370`: `MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W b63b8`
- `b637c`: bankT(`2001a8`,`1b3`,`b7f1c`)
- `b63b4`: `BRA.W b63f0` (F)
- `b63b8`: bankT(`2001ac`,`1bb`,`b7f1c`)
- `b63f0`: `MOVE.L #fffffff6,96(A6); MOVE.L #10,98(A6); MOVE.L #b6406,(A6)` (→`b6406`)
- `b6406`: `JSR b7cfa(PC)` (F; 설치 callback; U18 경계)
- `b640a`: `JSR 49fc6.L` (F)
- `b6410`: `JSR b7e5c(PC)` (F; U18 경계, C 반환)
- `b6414`: `BCC.W b641e` (C; `b7e5c` 반환 C가 0이면 `b641e`)
- `b6418`: `MOVE.L #b6422,(A6)` (→`b641e`)
- `b641e`: `BRA.W b76d2` (F; U18 경계)
- `b6422`: `MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W b646a` (설치 callback)
- `b642e`: bankT(`2001a8`,`1b3`,`b7f24`)
- `b6466`: `BRA.W b64a2` (F)
- `b646a`: bankT(`2001ac`,`1bb`,`b7f24`)
- `b64a2`: `MOVE.L #b64a8,(A6)` (→`b64a8`)
- `b64a8`: `JSR b7cfa(PC)` (F; 설치 callback)
- `b64ac`: `JSR 49fc6.L` (F)
- `b64b2`: `BCC.W b6502` (C; `49fc6` 반환 C)
- `b64b6`: `MOVE.L #fffffff4,96(A6); MOVE.L #8,98(A6); LEA 26(A6),A0; JSR b7e06(PC)` (U18 경계)
- `b64ce`: `MOVE.L #c,96(A6); MOVE.L #10,98(A6); LEA 26(A6),A0; JSR b7e06(PC)`
- `b64e6`: `MOVE.L #fffffff6,96(A6); MOVE.L #10,98(A6); JSR 496c2.L` (U11)
- `b64fc`: `MOVE.L #b68ba,(A6)` (→`b6502`)
- `b6502`: `BRA.W b76d2` (F)

**상태 `b68ba` 51** (`b68ba`~`b6aea` 42, 설치 사슬 `b6aee`~`b6b90` 9)
- `b68ba`: `JSR b7c9e(PC)` (F; U19)
- `b68be`: `CLR.B 5e(A6); BCLR.B #7,61(A6); MOVE.W #f,84(A6); CMPI.W #1,76(A6); BNE.W b68e4` (설치 callback(범위 밖 설치))
- `b68d8`: `BCLR.B #0,15(A6); MOVE.W #7fff,84(A6)` (→`b68e4`)
- `b68e4`: `CMPI.W #2,76(A6); BNE.W b68fa`
- `b68ee`: `BSET.B #0,15(A6); MOVE.W #7fff,84(A6)` (→`b68fa`)
- `b68fa`: `JSR 4be06.L` (F; U11)
- `b6900`: `BTST.B #7,15(A6); BEQ.W b6a32` (F, Z만)
- `b690a`: `MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W b6952` (설치 callback)
- `b6916`: bankT(`2001a8`,`1b3`,`b7f6c`)
- `b694e`: `BRA.W b698a` (F)
- `b6952`: bankT(`2001ac`,`1bb`,`b7f6c`)
- `b698a`: `MOVE.L #fffffffc,96(A6); MOVE.L #1a,98(A6); MOVE.L #18000,D0; BTST.B #0,15(A6); BNE.W b69ac` (bit 0이 1이면 `b69ac`)
- `b69aa`: `NEG.L D0` (→`b69ac`)
- `b69ac`: `MOVE.L D0,64(A6); MOVE.L #b69b6,(A6)` (→`b69b6`)
- `b69b6`: `BSR.W b7cfa` (F; 설치 callback; U18 경계)
- `b69ba`: `BTST.B #7,15(A6); BNE.W b69ce` (F)
- `b69c4`: `MOVE.L #b6a2a,(A6); BRA.W b69f4`
- `b69ce`: `BTST.B #0,61(A6); BEQ.W b69de` (F)
- `b69d8`: `MOVE.L #b6aee,(A6)` (→`b69de`)
- `b69de`: `TST.B 76(A6); BNE.W b69f4`
- `b69e6`: `SUBQ.W #1,84(A6); BCC.W b69f4` (감소 전 WORD가 0이 아니면 `b69f4`)
- `b69ee`: `MOVE.L #b6aee,(A6)` (→`b69f4`)
- `b69f4`: `JSR 6f1c2.L` (F; frame helper)
- `b69fa`: `TST.W D0; BMI.W b6a20` (D0.W 부호 bit가 1이면 `b6a20`)
- `b6a00`: `MOVE.B D0,9e(A6); BTST.B #0,D1; BEQ.W b6a12`
- `b6a0c`: `MOVE.L #b7100,(A6)` (→`b6a12`; `b7100`은 U19b, 쓰기만)
- `b6a12`: `BTST.B #1,D1; BEQ.W b6a20` (F)
- `b6a1a`: `MOVE.L #b749c,(A6)` (→`b6a20`; `b749c`는 U19b, 쓰기만)
- `b6a20`: `JSR 49fc6.L` (F)
- `b6a26`: `BRA.W b76bc` (F; U18 경계)
- `b6a2a`: `CLR.L 36(A6); CLR.L 3a(A6)` (→`b6a32`; 설치 callback)
- `b6a32`: `MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W b6a7a`
- `b6a3e`: bankT(`2001a8`,`1b3`,`b7f3c`)
- `b6a76`: `BRA.W b6ab2` (F)
- `b6a7a`: bankT(`2001ac`,`1bb`,`b7f3c`)
- `b6ab2`: `MOVE.L #fffffff6,96(A6); MOVE.L #18,98(A6); MOVE.L #b6ac8,(A6)` (→`b6ac8`)
- `b6ac8`: `JSR 4be2c.L` (F; 설치 callback; U18 경계)
- `b6ace`: `JSR 492c8.L` (F; U12)
- `b6ad4`: `BTST.B #7,15(A6); BEQ.W b6ae4` (F)
- `b6ade`: `MOVE.L #b690a,(A6)` (→`b6ae4`)
- `b6ae4`: `JSR 49fc6.L` (F)
- `b6aea`: `BRA.W b76bc` (F)
- `b6aee`: `CLR.L 64(A6); CLR.L 36(A6); MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W b6b3e` (설치 callback)
- `b6b02`: bankT(`2001a8`,`1b3`,`b7f74`)
- `b6b3a`: `BRA.W b6b76` (F)
- `b6b3e`: bankT(`2001ac`,`1bb`,`b7f74`)
- `b6b76`: `MOVE.L #b6b7c,(A6)` (→`b6b7c`)
- `b6b7c`: `JSR b7cfa(PC)` (F; 설치 callback)
- `b6b80`: `JSR 49fc6.L` (F)
- `b6b86`: `LEA 26(A6),A0; JSR 492d0.L` (F; 범위 문서 U20 경계)
- `b6b90`: `MOVE.W #1e,84(A6); MOVE.L #b690a,(A6); BRA.W b76bc`

**목표 선택 `b7b4c` 20** (C=1이면 D0/D2/D1 결과, C=0이면 없음)
- `b7b4c`: `JSR 484e2.L` (F; U19)
- `b7b52`: `BCS.W b7bbc` (C; `484e2` 반환 C가 1이면 `b7bbc`)
- `b7b56`: `MOVE.L #ffffffff,-(A7); MOVEQ #0,D0; JSR 49392.L` (frame helper)
- `b7b64`: `BCC.W b7b70` (C; `49392` 반환 C)
- `b7b68`: `BSR.B b7b30` (F; 경계)
- `b7b6a`: `BCC.W b7b70` (C; `b7b30` 반환 C)
- `b7b6e`: `MOVE.L A0,(A7)` (→`b7b70`)
- `b7b70`: `MOVEQ #1,D0; JSR 49392.L`
- `b7b78`: `BCC.W b7b9a` (C)
- `b7b7c`: `BSR.B b7b30` (F)
- `b7b7e`: `BCC.W b7b9a` (C)
- `b7b82`: `MOVE.L (A7),D0; BMI.W b7b98` (LONG 부호 bit가 1이면 `b7b98`)
- `b7b88`: `MOVEA.L D0,A2; MOVE.W 42(A0),D0; CMP.W 42(A2),D0; BCC.W b7b98` (WORD `42(A0)` ≥ WORD `42(A2)`(무부호)이면 `b7b98`)
- `b7b96`: `MOVEA.L A2,A0` (F; →`b7b98`)
- `b7b98`: `MOVE.L A0,(A7)` (→`b7b9a`)
- `b7b9a`: `MOVEQ #0,D0; MOVE.B #1,D2; MOVE.L (A7)+,D1; BMI.W b7bbc`
- `b7ba6`: `CMPI.L #100cb8,D1; BEQ.W b7bb6`
- `b7bb0`: `MOVEQ #1,D0; MOVE.B #2,D2` (→`b7bb6`)
- `b7bb6`: `ORI.B #1,CCR; RTS` (P: Set)
- `b7bbc`: `ANDI.B #fe,CCR; RTS` (P: Clear)

**palette `b7c9e` 8**
- `b7c9e`: `JSR 8ff4.L` (F; cleanup)
- `b7ca4`: `BTST.B #1,9f(A6); BNE.W b7cca` (F)
- `b7cae`: `MOVE.W 8e(A6),D0; LEA b7f18(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.L` (U02)
- `b7cc6`: `BRA.W b7ce4` (F)
- `b7cca`: `MOVE.W #ac1,D0; MOVE.B #1,D1; JSR 8ebe.L`
- `b7cd8`: `MOVE.W #ac2,90(A6); BSET.B #0,9f(A6)` (→`b7ce4`)
- `b7ce4`: `MOVE.W #d88,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `b7cf2`: `MOVE.B 19(A6),14(A6); RTS`

**객체 `ba78c` 10**
- `ba78c`: `MOVE.W #8835,68(A6); MOVE.W #8835,1e(A6); MOVE.W #74,D0; MOVE.W #e,D1; MOVE.B #0,D2; JSR c6a96.L` (callback 진입; U05)
- `ba7aa`: bankD(`2001d4`,`20b`,`38`)
- `ba7d2`: `MOVE.L #ba7d8,(A6)` (→`ba7d8`)
- `ba7d8`: `JSR 43e34.L` (F; 설치 callback; cleanup)
- `ba7de`: `JSR 492c8.L` (F)
- `ba7e4`: `JSR 49fc6.L` (F)
- `ba7ea`: `LEA ba784(PC),A0; JSR 1ab02.L` (F; U05, C 반환)
- `ba7f4`: `BCC.W ba7fe` (C; `1ab02` 반환 C)
- `ba7f8`: `JMP 2a00.L` (F)
- `ba7fe`: `RTS` (F)

**객체 `d6d4a` 1**
- `d6d4a`: `MOVE.W 76(A6),5426(A5); MOVE.W 78(A6),5428(A5); MOVE.W 7a(A6),542a(A5); MOVE.W 7c(A6),542c(A5); JMP 2a00.L` (callback 진입)

**객체 `d81cc`/`d81e8` 42** (`d81cc`~`d831c` 26, 설치 사슬 `d831e`~`d83be` 16)
- `d81cc`: `MOVE.W #0,82(A6); MOVE.W #4,84(A6); MOVE.L #d841e,86(A6); MOVE.W #0,D0; BRA.W d8204` (callback 진입)
- `d81e8`: `MOVE.W #0,82(A6); MOVE.W #6,84(A6); MOVE.L #d841e,86(A6); MOVE.W #1,D0; BRA.W d8204` (callback 진입; `d8200 BRA.W d8204`는 같은 block)
- `d8204`: `MOVE.W D0,80(A6); MOVE.W 80(A6),D0; LEA d841a(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.L`
- `d8220`: `MOVE.W #880c,68(A6); MOVE.W #880c,1e(A6); LEA cbce8.L,A0; JSR 490ba.L` (U12)
- `d8238`: `MOVE.W D0,54(A6); JSR 4c0ac.L` (U12)
- `d8242`: `TST.W 80(A6); BNE.W d8276`
- `d824a`: bankD(`2001c0`,`1e3`,`4`)
- `d8272`: `BRA.W d829e` (F)
- `d8276`: bankD(`2001cc`,`1fb`,`7c`)
- `d829e`: `JSR 496c2.L` (F; U11)
- `d82a4`: `MOVE.L #d82aa,(A6)` (→`d82aa`)
- `d82aa`: `BTST.B #7,15(A6); BEQ.W d82be` (F; 설치 callback)
- `d82b4`: `JSR 4be06.L` (F)
- `d82ba`: `BRA.W d82c4` (F)
- `d82be`: `JSR 4be2c.L` (F; U18 경계)
- `d82c4`: `JSR 49fc6.L` (F)
- `d82ca`: `JSR 4b54e.L` (F; U01)
- `d82d0`: `CLR.B 5e(A6); BTST.B #7,61(A6); BEQ.W d82e4`
- `d82de`: `MOVE.L #d831e,(A6)` (→`d82e4`)
- `d82e4`: `MOVEA.L 86(A6),A0; MOVE.W 82(A6),D0; MOVE.W 84(A6),D1; MOVE.W 42(A6),D7; SUBI.W #60,D7; CMPI.W #80,D7; BCS.W d8302` (D7.W = WORD `42` − `60` mod 2^16; 무부호 < `80`이면 `d8302`)
- `d8300`: `MOVEQ #0,D0` (→`d8302`)
- `d8302`: `JSR 47070.L` (F; U09)
- `d8308`: `LEA d8440(PC),A0; JSR 1aa7e.L` (F; U01, C 반환)
- `d8312`: `BCC.W d831c` (C; `1aa7e` 반환 C)
- `d8316`: `JMP 2a00.L` (F)
- `d831c`: `RTS` (F)
- `d831e`: `JSR e9112.L` (F; 설치 callback; 경계)
- `d8324`: `TST.W 80(A6); BNE.W d8358`
- `d832c`: bankD(`2001c0`,`1e3`,`8`)
- `d8354`: `BRA.W d8380` (F)
- `d8358`: bankD(`2001cc`,`1fb`,`80`)
- `d8380`: `LEA 26(A6),A0; JSR d83c0(PC)` (F; 경계)
- `d8388`: `JSR 46ef4.L` (F; cleanup)
- `d838e`: `MOVE.L #d8394,(A6)` (→`d8394`)
- `d8394`: `BTST.B #7,15(A6); BEQ.W d83a8` (F; 설치 callback)
- `d839e`: `JSR 4be06.L` (F)
- `d83a4`: `BRA.W d83ae` (F)
- `d83a8`: `JSR 4be2c.L` (F)
- `d83ae`: `JSR 49fc6.L` (F)
- `d83b4`: `BCC.W d83be` (C; `49fc6` 반환 C)
- `d83b8`: `JMP 2a00.L` (F)
- `d83be`: `RTS` (F)

**객체 `dbefe` 9**
- `dbefe`: `MOVE.W #731,D0; JSR 3af8.L` (callback 진입; sound)
- `dbf08`: `BRA.W dbf0c` (F)
- `dbf0c`: `CMPI.B #1,100012.L; BEQ.W dbf1e`
- `dbf18`: `JMP 2a00.L` (F)
- `dbf1e`: `MOVE.W #294,76(A6); MOVE.L #dbf2a,(A6)` (→`dbf2a`)
- `dbf2a`: `SUBQ.W #1,76(A6); BCS.W dbf34` (설치 callback; 감소 전 WORD가 0이면 `dbf34`)
- `dbf32`: `RTS` (F)
- `dbf34`: `MOVEA.L #4841a,A0; MOVE.W #a,D0; JSR 28ae.L` (자식 `4841a`)
- `dbf44`: `JMP 2a00.L` (F)

(수: `484e2` 3 + 진입 6 + `b6370` 24 + `b68ba` 51 + `b7b4c` 20 + `b7c9e` 8 + `ba78c` 10 + `d6d4a` 1 + `d81cc` 42 + `dbefe` 9 = 174. 그중 범위 문서 함수 본문 135, 설치 callback 사슬 39(`b6422` 13, `b6aee` 9, `d831e` 16, `dbf2a` 1).)

## 구현 범위와 규약

- routing 11 범위(위 표). 짝수 PC 1,072개 중 block 시작 174, 내부 898. 내부 PC 직접 진입은 `unsupported animation objects u19 PC`다. 경계 callee(U18 `b7bc2` `b7cfa` `b7e06` `b7e5c` `b76bc` `b76d2` `4be2c`, U20 `492d0`, 미배정 `b7b30` `d83c0` `e9112`), 범위 밖 설치 callback `b7100` `b749c`와 범위 이웃은 이 실행부 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **FLOW_ONLY 84개**(C 보존): `484e2` `b630a` `b6342` `b636c` `b63b4` `b6406` `b640a` `b6410` `b6414` `b641e` `b6466` `b64a8` `b64ac` `b64b2` `b6502` `b68ba` `b68fa` `b6900` `b694e` `b69b6` `b69ba` `b69ce` `b69f4` `b6a12` `b6a20` `b6a26` `b6a76` `b6ac8` `b6ace` `b6ad4` `b6ae4` `b6aea` `b6b3a` `b6b7c` `b6b80` `b6b86` `b7b4c` `b7b52` `b7b64` `b7b68` `b7b6a` `b7b78` `b7b7c` `b7b7e` `b7b96` `b7c9e` `b7ca4` `b7cc6` `ba7d8` `ba7de` `ba7e4` `ba7ea` `ba7f4` `ba7f8` `ba7fe` `d8272` `d829e` `d82aa` `d82b4` `d82ba` `d82be` `d82c4` `d82ca` `d8302` `d8308` `d8312` `d8316` `d831c` `d831e` `d8354` `d8380` `d8388` `d8394` `d839e` `d83a4` `d83a8` `d83ae` `d83b4` `d83b8` `d83be` `dbf08` `dbf18` `dbf32` `dbf44`.
- **known carry 생산 4개**: `484ec` `b7bb6`(Set), `484f2` `b7bbc`(Clear). 그 밖 86 block(MOVE/MOVEQ/CLR/TST/CMPI/CMP/SUBI/SUBQ/NEG, `MOVE.L #imm,(A6)` block, bank 표 block)은 Unknown이다.
- **소비자 10개**: `b6414` `b64b2` `b7b52` `b7b64` `b7b6a` `b7b78` `b7b7e` `ba7f4` `d8312` `d83b4`. 들어오는 C가 Unknown이면 `objects u19 caller requires known carry`(상태 보존).
- 산술: `NEG.L`은 LONG mod 2^32, `ADD.W D0,D0`은 D0 하위 WORD만 바꾼다(mod 2^16), `(An,D0.W)` index는 부호확장, `SUBQ.W #1`+`BCC`/`BCS`는 감소 전 WORD = 0일 때만 borrow, `SUBI.W #60`+`CMPI.W #80`+`BCS`는 무부호 WORD 비교, `CMP.W`+`BCC`는 무부호 WORD ≥, `TST.W D0`+`BMI`·`MOVE.L`+`BMI`는 부호 bit.
- 루프 없음. I/O port 쓰기 없음. bank 변경 없음. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM 읽기, physical span 밖 bank 읽기는 기존 checked 오류다.

## 의존·경계

- [F] U19 → 기존: interpreter `49f8c` `49fc6`, U11 `496c2` `4be06`, frame helper `6f1c2` `49392`, U12 `492c8` `490ba` `4c0ac`, cleanup `8ff4` `43e34` `46ef4`, U02 `8ebe`, U05 `c6a96` `1ab02`, U01 `4b54e` `1aa7e`, U09 `47070`, sound `3af8`, fade_card `28ae` `2a00`.
- [F] U19 → 경계: U18 `b7bc2` `b7cfa` `b7e06` `b7e5c` `b76bc` `b76d2` `4be2c`, U20 `492d0`, 미배정 `b7b30` `d83c0` `e9112`, 설치만 하는 U19b `b7100` `b749c`, 자식 `4841a`(`28ae`에 넘김, 쓰기만).
- [F] 다른 단위 → U19: U18 `b76c0 BSR.W b7b4c`(C 소비 `b76c4`), U18 `b76b2 MOVE.L #b68be`, stage event 표(`e8ed4` 등), 범위 밖 `1ee36` `b7a62 JSR 484e2`, `b8856 BSR.W b7b4c`.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, TB 기준)에서 U19 block에 닿는 seed: base 8 9 14 15 36 37 42 43 62 63 80 81, RNG+`80` 변형은 2 3 12 13 26 27이 더해진다. 174 정적 시작 중 base 94, 변형 95가 도달한다. 나머지는 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] 기준 C++ 차분(작업 트리 `88a1123`, F2 프레임 패스 142 seed, scratch 복사본 `tools/verify_animation_machine_scheduler_f4.py`): 일치 pass 10,978개·node 85,698개, 불일치 0, 자연 완주 99 seed. 첫 미연결 callback `b6338` 2, `b6362` 2, `ba78c` 2, `dbefe` 2(그리고 U18 `b631c` 4). RNG 초기화 400 frame 차분(`tools/verify_animation_machine_scheduler_rng_f4.py` 복사본): 일치 pass 26,246개·node 181,775개, 불일치 0, complete 65.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 174 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산자 known, 그 밖 Unknown; 소비자는 Unknown이면 오류), zero-step, 내부 898 PC 정확한 오류, 홀수 PC, U18·미배정 경계 stop(stop만), rollback 탐침은 work RAM `10fe00..10fefe`만. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력과 합성 bank·표 바이트)로 비교한다.
- 실제 ROM 차분: 각 block을 8개 program ROM window(physical_rom)로 C++와 Unicorn에서 같은 결과로 실행하고, 소비자의 known C는 실제 생산자(`484e2` `49392` `1ab02` `1aa7e` `49fc6`) 실행 결과의 native 분기로 확인한다(`b6414`/`b7b6a`/`b7b7e`는 경계 생산자라 선언 C).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 기준 이상, 불일치 0, complete 65 이상. U18+U19 조합 scratch 트리에서도 같은 두 차분을 잰다.

## 미확인·범위 밖

1. [I] `b6300`~`b6368`은 `8e(A6)`(0/1: 두 변형)을 정하고 U18 `b7bc2`로 초기화한 뒤 상태 본문(`b6370`: 비행, `b6506`: U28, `b66c8`: U18, `b68ba`: 착지·추적)으로 들어가는 같은 객체 계열의 함수 표로 보인다. `b6370`/`b6422`는 animation(bank 표 `2001a8`/`2001ac`)과 U18 이동 `b7cfa`·`b7e5c`로 날다가 `b68ba`로 바뀌는 상태, `b68ba`~`b6b9c`는 `6f1c2` 결과(D1 bit 0/1)로 U19b `b7100`/`b749c` 상태로 넘어가는 지상 상태로 보인다.
2. [I] `484e2`는 BYTE `5683` bit 0을 C로 돌려주는 상태 질의, `b7b4c`는 그 bit가 0일 때 `49392`(두 player 노드)와 `b7b30`으로 고른 목표 노드를 D1(LONG), D0(`100cb8`이면 0, 아니면 1), D2(1/2)와 C=1로 돌려주는 목표 선택으로 보인다.
3. [I] `ba78c`는 palette `74`/`e`(`c6a96`)과 animation `20b`의 일회성 효과 객체, `d6d4a`는 노드 `76`~`7c`를 `5426`~`542c(A5)`로 복사하고 자기 삭제하는 설정 객체, `d81cc`/`d81e8`은 palette `d841a` 표·animation `1e3`/`1fb`로 나타나 `47070`·`1aa7e`로 움직이는 객체(죽으면 `d831e` 상태와 경계 `e9112`·`d83c0`), `dbefe`는 효과음 `731` 뒤 BYTE `100012`=1일 때만 `294` frame 기다려 자식 `4841a`를 만드는 연출 객체로 보인다.
4. [U] 경계 `b7b30` `d83c0` `e9112`의 본문과 실행 결과, U19b `b7100..b76a4` 사슬은 U19 밖이다. `d83c0`은 `2986`을 부른다(2986 caller-X 제한은 기존 checked 오류 정책 그대로).

작업자 scratch: `/Users/start/Workspce/ms5-scratch/u19/`(`u19.py` block·범위·SHA 계산, `scope19.py` `nofollow.py` `inst.py` `callees.py` `owners.py` `reach19.py` `probes19.py` `nextins.py` `refs.py` `hroute_u19.py` `disu19.py`; 저장소 밖).
