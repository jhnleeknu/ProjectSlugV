# 객체 callback F4 U18: 공중 객체 `b631c` 계열(설치 `b6764`, 공유 꼬리 `b76a4`/`b76d2`), 초기화 보조 `b7bc2`/`b7c42`, 이동 보조 `b7cfa`/`b7e06`/`b7e5c`, 자식 `ea5e0`·`ea7f4`(설치 `ea824` `ea82a` `ea940`), 거리 탐색 `ea636`/`ea65a`/`46c68`, `4be2c` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U18 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`, `4b54e`·`1aa7e` 반환 C), U08b 계약(SHA256 `a75aa7748c9acba9f9f16e97cefbed77308fe429d0103e8683f2f9bdd5c0d7a8`, `4be34`), U13 계약(SHA256 `20af72d0d12a571f1d36590bc9e36348b596de54d948320364c7721f71e2c53e`, `ea5f0`/`ea60c`와 `1abda` 소비), U16 계약(SHA256 `d4959a63bb13e5bc5413a791a4caf3c9b21cf5da336447028fee12ee8df1ab90`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기·DBcc fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee, 다른 단위의 PC, 범위 밖에 설치되는 callback은 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01~U16 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U18에는 없음). `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`Scc`/`MOVEM`/`DBcc`, Z만 바꾸는 `BTST`/`BSET`/`BCLR`)만인 block과 callee C를 소비하는 block은 FLOW_ONLY다. `ADDQ`/`SUBQ`/`ADDA` An block은 Unknown이다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C를 소비자에서 쓰려면 native 분기 결과로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U18의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료(`2001a8` `2001ac`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u18`(HEAD `9682aed` = Codex 통합 U01~U16·U15b·U15c, `engine/src/animation_machine.cpp` SHA256 `a0f77362514f9abd8b75d5d5717c811644aa6e24b0953f1f64dcfb6792a753d3`, routing 규칙 53개)을 참조했다. 동시에 진행하는 U17(작업 트리 `metalslug-u17`)의 PC(`4bfa4` 등)는 경계로 둔다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/u18/u18.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] U18은 **block 시작 158개**다. 범위 문서 U18 행의 157보다 1 많다. 차이는 범위 안 `MOVE.L #ea940,(A6)`(`ea93a`)이 설치하는 callback 진입 `ea940`이다. 범위 문서의 함수 본문 계산은 `MOVE.L #imm,(A6)` 대상을 시작으로 세지 않았다(그 밖의 157개는 같다). 범위 문서 `units.pkl`의 함수 18개 본문이다: `46c68` `4be2c` `b631c` `b6764` `b76a4` `b7bc2` `b7c42` `b7cfa` `b7e06` `b7e5c` `ea5e0` `ea636` `ea63c` `ea65a` `ea762` `ea7f4` `ea824` `ea82a`.
  - 범위 문서의 범위 `4b54e..4b6e2`(U01이 `4b50c..4b6e4`를 routing)와 `4be34..4bf9e`(U08b)는 이미 routing되어 있어 새 block이 아니다. U18이 새로 갖는 것은 `4be2c..4be34`(`ADDI.L` 한 명령)뿐이다. `ea5f0..ea600`·`ea60c..ea626`은 U13 범위다.
  - 거리 탐색 `46c68` 14, `4be2c` 1, 객체 `b631c` 계열 17(`b631c` `b6326`, 공유 본문 `b66c8`~`b67ae`, 설치 callback `b6764`), 공유 꼬리 `b76a4` 22(`b76a4`~`b7740`, `b67ae BRA`가 `b76d2`로 들어온다), 초기화 `b7bc2` 15 + `b7c42` 8, 이동 `b7cfa` 8, `b7e06` 9, `b7e5c` 3, 자식 생성 `ea5e0` 3, 거리 탐색 `ea636`/`ea63c`/`ea65a` 11, `ea762` 12, 자식 callback `ea7f4` 12(설치 `ea824` `ea82a`), `ea908` 상태 23(설치 callback `ea940`과 `eaa54 JMP` 포함; `ea81c BNE`로 들어온다).
  - 코드 13 범위, 1,568바이트, 365명령이다. 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx는 없다. routing 짝수 PC는 784개, 내부 PC는 626개다.
  - 범위 문서 TB 재생의 범위 안 TB 시작은 모두 정적 시작이다(TB 인공 시작 0).
- [F] **경계 callee(실행부 없음) 4개**: `4970a`(`b7e24 JSR`, 범위 문서 U28), `b7b4c`(`b76bc BSR`, U19), `b7dd6`(`b76dc JSR`, 범위 문서 어느 단위에도 없음), `4bfa4`(`b7d04 JSR`, U17). 범위 문서 "경계 callee 3"(`4970a` `b7b4c` `b7dd6`)에 동시 진행 U17의 `4bfa4`가 더해진다.
- [F] **범위 밖 설치 callback(쓰기만 함) 6개**: `b67b2`(`b67a8`), `b68be`(`b76b2`), `b6ba0`(`b76c8`), `b7742`(`b773a`), `ea85a`(`ea84c`), `eaa00`(`ea9e4`). 이들은 base·RNG 초기화+`80` 재개 400 frame 어느 변형에서도 실행되지 않았다. `b68be` `b6ba0`은 범위 문서 U19 쪽 본문이고 `b67b2` `b7742` `ea85a` `eaa00`(과 그 안의 `ea8d2` `eaa20`)은 범위 문서 어느 단위에도 없다(아래 결정 1).
- [F] 기존 실행부로 나가는 호출·점프: U08 `447be`(`46c9e` `46ce8`)·`1aa3a`(`b7c0a`), interpreter `49f8c`(`b66d4` `b6710` `ea91c` `ea976` `ea9b0`)·`49fc6`(`b6768` `b76a8` `ea9f8`, C 반환), U01 `1aa7e`(`b772c`, C 반환)·`4b54e`(`b7e6e JMP`, C 반환), hud `8cda`(`b771a`), U11 `4be06`(`b7c1e`), stage_event_ops `49a84`(`b7bdc`)·`288c`(`ea7f4` `ea82a` `ea940`, C 반환), cleanup `8ff4`(`b7c42` `ea908`)·`43e22`(`ea7aa`), U02 `8ebe`(`b7c52` `b7c6e` `b7c88` `ea914`), U12 `492c8`(`b7d14`)·`1abda`(`ea5e0` `ea90e`, C 반환), fade_card `28ae`(`b7e10`, C 반환)·`2a00`(`eaa54 JMP`), readiness `289e`(`ea762`, C 반환), stage_area `49a58`(`ea9ca`), U08b `4be34`(`4be2c` fall-through), U13 `ea60c`(`ea5ea BRA`)·`ea624`(`ea5e6 BCC`). U18 안 호출: `b631c→b7bc2`, `b6764/b76a4→b7cfa`, `b6782→b7e06`, `b67a0→b7e5c`, `b7c24→ea5e0`, `b7c3c→b7c42`, `b7d0e→4be2c`, `ea63c/ea668→46c68`, `ea65a→ea636`, `ea774→ea65a`, `ea80a/ea834/ea954→ea762`.
- [F] **flag**:
  - 블록 경계를 건너는 C 소비 block **14개**: `b67a4 BCC`(`b7e5c` 반환), `b76ae BCC`(`49fc6`), `b76c4 BCC`(경계 `b7b4c`), `b7736 BCC`(`1aa7e`), `b7e20 BCC`(`28ae`), `ea5e6 BCC`(`1abda`), `ea650 MOVEM.W+DBCS`(`46c68`), `ea65c BCS`(`ea636` 반환), `ea678 BCS.B`(`46c68`), `ea770 BCC`(`289e`), `ea792 SCS+BCS`(`ea65a` 반환), `ea806` `ea830` `ea946 BCC`(`288c`).
  - known carry 생산 block **4개**: `46d08`(`ANDI.B #fe,CCR`: Clear), `46d12`(`ORI.B #1,CCR`: Set), `b7e64`(`ANDI.B #fe,CCR`: Clear), `ea67a`(`ORI.B #1,CCR`: Set). 소비자는 각각 `ea650`/`ea678`(`46c68` 호출 2곳의 다음 명령), `b67a4`(U18)·범위 밖 `b6414` `b6600`, `ea792`(U18)·범위 밖 `ea6cc`다.
  - CCR 명령이지만 소비자가 없어 Unknown으로 두는 block 3개: `b7e2e`(`ORI.B #1,CCR` 뒤 `b7e32`의 `MOVE.W`가 C를 지운다), `b7e56`(`ANDI.B #fe,CCR; RTS`, `b7e06` 호출 9곳의 다음 명령이 모두 `MOVE.L`/`MOVE.B`/`TST.W`), `ea9ea`(`ANDI.B #fe,CCR; BCLR; BNE`, callback 반환 C는 scheduler가 쓰지 않는다).
  - block 안에서 만들고 쓰는 flag: `46c68` `46cbe`(`CMPA.W #0` 뒤 `BEQ`), `46c86` `46cd0` `b770c` `ea81c` `ea844` `ea9d0` `b7e5c` `b676e` `ea990`(`TST` 뒤 Bcc), `46cb0` `46cfa`(`CMP.W` 뒤 `BEQ`), `b76f8`(`CMPI.W` 뒤 `BCS`, 무부호 작음), `b76ea`(`TST.W D0` 뒤 `BMI`), `ea7c8`(`SUB.L` 뒤 `BLE`, 부호 있는 ≤), `ea7d4`(`SUBI.L` 뒤 `BCC`, borrow 없음), `b677a`(`SUBQ.B` 뒤 `BNE`), BTST/BCLR 뒤 Bcc(Z).
- [F] 읽는 자료: banked window LONG `2001a8`(`b66d4`)·`2001ac`(`b6710`)와 그 값 + `4·(b7f54 표 값)`의 LONG, fixed ROM 표 LONG `b7f54+4·8e(A6)`, WORD `b7f14+2·8e(A6)`, LONG `ea742`/`ea752`+`4·76(A6)`. 주소만 넘기는 상수: `b7efc`(→`b7b4c` A1), `b7eec`(→`1aa7e` A0), `d1f68`(→`28ae` A0, 자식 callback), `109156` `10b1d6`(노드 포인터 LONG `2e`를 읽는 고정 RAM). I/O port 쓰기와 bank 변경은 U18 자체에 없다.
- [F] 자연 도달(F4 범위 scratch 재생, TB 기준): base(`f4scope/dyn`)와 RNG 초기화+응답 `80` 변형(`dyn_rng1_resp80_f400`) 모두 90 block. seed 68 69 70 71은 `b631c` 계열·`ea5e0`·`ea7f4`·`46c68`에, seed 8 9는 `46c68`·`ea636`~`ea852`에, seed 2 3 6 7 12 13 26 27 42 43 62 63 80 81은 범위 밖 함수(U19/U28)를 거쳐 `b76d2` `b7bc2` `b7cfa` `ea5e0` 등에 닿는다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 158(범위 문서 157 + `ea940`).** 범위 밖 설치 callback 6개는 넣지 않는다. 그중 `b7742`(`JMP 2a00` 한 block), `ea85a`(`ea85a..ea908`, 18 block), `eaa00`(`eaa00..eaa54`, 9 block), `b67b2`(`b67b2..b68ba`, 16 block)는 범위 문서의 어느 단위에도 배정되지 않았다(동적 미도달이라 greedy가 고르지 않음). [I] `ea85a`/`eaa00`은 `ea7f4` 자식 객체의 다음 상태, `b67b2` `b7742`는 `b6764` 객체의 다음 상태로 보인다. 권고: U18에는 넣지 않고(범위 문서 경계 유지) 후속 단위(예: 범위 문서 갱신 시 "고아 설치 callback" 묶음)로 배정한다.
2. **U17 의존.** `b7cfa`의 `BTST #7,15(A6)`이 서면 `JSR 4bfa4`(U17)다. [F] F4 범위 재생에서 seed 68~71은 `b7d04`에 닿는다. 따라서 U18만으로는 seed 68~71이 `4bfa4`에서 멈출 수 있다. 새 자연 완주는 U17+U18 조합에서 다시 잰다(scratch).
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u18.cpp`의 `animation_objects_u18_block`. 오류는 `unsupported animation objects u18 PC`(내부 PC), `objects u18 caller requires known carry`(소비 14 block). 메인 지시와 같다.
4. **C 소비 14 block의 생산자.**
   - `b67a4`: U18 `b7e64`(Clear) 또는 `b7e6e JMP 4b54e`(U01 결정 2: `4b6be` Clear, `4b6ca` ORI Set).
   - `b76ae`: interpreter `49fc6`(U10 `baecc` 등과 같다). `b7736`: U01 `1aa7e`(U01 `b4e60`과 같다). `b7e20`: fade_card `28ae`(`2908` ORI Set / `290e` ANDI Clear). `ea5e6`: U12 `1abda`(U13 `ea5f6`과 같다). `ea770`: readiness `289e`(CMP.L 같음 Clear, 아니면 ORI Set). `ea806` `ea830` `ea946`: stage_event_ops `288c`(F3b `e936e`과 같다).
   - `b76c4`: 경계 `b7b4c`(U19). U19 병합 전에는 선언 C로만 진입한다.
   - `ea650`(`MOVEM.W (A7)+,D7; DBCS D7,ea63c`)·`ea678`: U18 `46c68`(`46d08` Clear / `46d12` Set). `ea65c`: `ea636` 반환(`ea650` 뒤 `ea658 RTS`가 그대로 돌려줌). `ea792`: `ea65a` 반환(`ea660 RTS` 또는 `ea67a` Set).
   - Unknown이면 `objects u18 caller requires known carry`(상태 보존).
5. **`ea650` DBcc.** `MOVEM.W (A7)+,D7`는 WORD를 부호확장해 D7 32 bit 전체에 쓴다. `DBCS`는 C=1이면 `ea658`로 빠지고, 아니면 D7.W를 1 줄여 `ffff`가 아니면 `ea63c`로 돈다(D7 상위 WORD 보존). 루프는 D7(`MOVE.W #4,D7` 전의 저장값)에 묶이므로 반복 수는 자료가 정한다. 실행부 한도(기존 1,000,000 block)로만 묶는다.
6. **bank 자료.** `b66d4`/`b6710`의 `MOVE.L 2001a8/2001ac.L,22(A6)`, `MOVEA.L 2001a8/2001ac.L,A1; MOVEA.L (A1,D0.W),A1`은 live bus로 읽는다. [F] bank `200000`에서 `2001a8`=`002d0086`, `2001ac`=`002d0e90`(+`10`은 각각 `002d024a` `002d0f8a`); bank `300000`이면 `03959560`/`03c78860`(이어지는 읽기는 bus 밖이라 checked 오류); bank `400000`이면 `00223b70`/`00223b88`. test에는 합성 bank 바이트를 쓴다(ROM 자료를 test에 넣지 않음).
7. **무효화 탐침.** [F] `engine/tests/animation_machine_objects_u08b_test.cpp` 580행 `outside[]`의 `0x4be32`는 U18 범위 `4be2c..4be34` 안이므로 이제 `unsupported animation objects u18 PC`가 된다. RAM 탐침 `0x10fe0c`로 바꾼다(F4 test 경계 관례). 같은 줄의 `0x4bfa4`는 U17 소관이다(U18은 건드리지 않음). 그 밖 `engine/tests`·`tools`·`engine/src`·`docs/analysis`에서 U18 범위 PC를 rollback·outside 탐침으로 쓰는 곳은 없다(`probes.py`: caller 나열과 U13 `ea60c`의 자식 상수 `ea7f4`뿐).

## 원본 바이트 근거

[F] 코드 13 범위 합계 1,568바이트. 범위 순서로 이어 붙인 SHA256 `18cbfc7dc874f2b24abbe8905d3cb54952e3f4a28fb55983778adf641bc73e49`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `46c68..46d1c` | 180 | `b482b6bbe78d2edf9869c11175f1ec760cba3a1830c694c2ba46a999826fdef4` | 거리 탐색 `46c68` |
| `4be2c..4be34` | 8 | `7e777efceaa9e522d4c5bf2fb823218e265fb638d858edae8c5d8dfa785dffae` | `4be2c`(→ U08b `4be34`) |
| `b631c..b632a` | 14 | `465183caea88bcb06c51b54ecfab9362c96ce62da3a23e2904e1415648d54249` | callback `b631c` |
| `b66c8..b67b2` | 234 | `1d9c24ed3a7c27f03073073bf1ed940c489bff55dc19adcf8a4cd0a377e06fe5` | 공유 본문 `b66c8`, 설치 callback `b6764` |
| `b76a4..b7742` | 158 | `194a21d826944b5f87f400c0ec365121e9458c9673245ea42985a1b6e58cc372` | 설치 callback `b76a4`, 공유 꼬리 `b76bc` `b76d2` |
| `b7bc2..b7c9e` | 220 | `74eb53008d55c2db224c83a3a3c846ae9dc156e0a8f1e6de26e05807845c38c1` | 초기화 `b7bc2`, `b7c42` |
| `b7cfa..b7d2e` | 52 | `b4efb7da0b6ae2924bf39b7e3d8a64cf423685b6be6a9bc12c6fb06aa1e0b4dd` | 이동 `b7cfa` |
| `b7e06..b7e74` | 110 | `7273616ee89b17e6b2442525365f2909e657189a9835d91045a38bf1fba85f14` | `b7e06`, `b7e5c` |
| `ea5e0..ea5f0` | 16 | `d6016d137eabedeab35b5fa3046bb14c433f7879caea5a2627fe541b12f9eb9e` | 자식 생성 `ea5e0` |
| `ea636..ea680` | 74 | `623f90f1135dd0f2c65519264e9266d8630ebe47633bf7bb0c28c94a5779fad6` | 거리 탐색 `ea636` `ea63c` `ea65a` |
| `ea762..ea85a` | 248 | `828c71ba13a40aee7e9902a112acf08d450ee2b6f6013b8d3e49c1099680dbe3` | `ea762`, 자식 callback `ea7f4`, 설치 `ea824` `ea82a` |
| `ea908..eaa00` | 248 | `169413a2088a5a7ceba3b0a55aa39c2271db046d315bbec794b36d8764abfe0f` | `ea908` 상태, 설치 `ea940` |
| `eaa54..eaa5a` | 6 | `2738adf81304c5fbbc9eedf6248d6b2d7cfa132bc35dfb5e458d0bbd9e12d3f9` | `JMP 2a00` |

- [F] 범위 밖 이웃(routing 밖): `46c60..46c68`(앞 함수 꼬리 `ORI CCR; RTS`), `46d1c..`(다른 함수 `MOVEQ`), `4be06..4be2c`(U11), `4be34..`(U08b), `b6300..b631c`·`b632a..b66c8`(같은 함수 표의 다른 진입 `b6300` `b630e` `b6338` `b6346` `b6354` `b6362`과 그 본문, 범위 문서 U19/U28), `b67b2..`(범위 밖 설치 callback `b67b2`), `b7690..b76a4`(앞 함수; `b769e`가 `MOVE.L #b76a4,(A6)`로 `b76a4`를 설치), `b7742`(설치 callback `JMP 2a00`), `b7b4c..b7bc2`(U19 `b7b4c`), `b7c9e..b7cfa`(다른 함수 `b7c9e`, U19), `b7d2e..b7e06`(다른 함수, `b7dd6` 경계 포함), `b7e74..`(자료: `b7e74` 이후 표, `b7eec` `b7efc` `b7f14` `b7f54`), `ea5d0..ea5e0`(다른 진입), `ea5f0..ea600` `ea60c..ea626`(U13), `ea600..ea60c`(다른 진입 `ea600`, 미배정), `ea626..ea636`(다른 함수 `ea626` `ea62e`), `ea680..ea762`(범위 문서 U47 `ea680..ea68c`, 함수 `ea69a`~, 자료 `ea712..ea762`), `ea85a..ea908`·`eaa00..eaa54`(범위 밖 설치 callback 본문).
- [F] 참조: `b631c`는 stage event 표 LONG `e8edc`, `ea7f4`는 U13 `ea60e MOVEA.L #ea7f4,A0`(→`28ae` 자식), `b6764` `ea824` `ea82a` `ea940`은 범위 안 `MOVE.L #imm,(A6)`(`b675e` `eaa3e`(범위 밖) `ea824` `ea93a`), `b76a4`는 범위 밖 `b769e MOVE.L #b76a4,(A6)`가 설치한다. `46c68` 호출 2곳(`ea64a` `ea672`, U18), `4be2c` 호출 145곳(fixed ROM `JSR 4be2c.L`/`JMP`, U18 `b7d0e` 포함), `b7bc2` 8곳(`b6306`~`b6368` BSR.W, U18은 `b6322`), `b7cfa` 12곳, `b7e06` 9곳, `b7e5c` 3곳(`b6410` `b65fc` `b67a0`), `ea5e0` 4곳(`22b80` `22e22` `29a90` `b7c36`), `ea65a` 3곳(`ea69a BRA.B` `ea6ca BSR.B` `ea78e`), `ea762` 4곳(`ea818` `ea836` `ea8de` `ea956`), `b76d2` BRA.W 12곳.
- [F] fixed ROM 자료 값: LONG 표 `b7f54` = `00000004 00000008 0000000b 00000009 0000000c 0000000b 0000000f 00000001`, WORD 표 `b7f14` = `0d89 0d8c 0d88 0d8c 0000 0001 …`, LONG 표 `ea742` = `000eab42 000eab70 000eab9e 000eabcc`, `ea752` = `000eab42 000eab70 000eab9e 000eabfa`. [I] `8e(A6)`은 `b6300`~`b6368` 진입이 넣는 작은 값(`b631c`는 0), `76(A6)`은 `ea60c`가 넣는 1~3(`ea5e0`은 1)이다. 표 읽기는 index 상한 없이 원본 그대로 live bus가 정한다(점프 표가 아니라 자료 읽기다).

## block 목록과 실행 의미

[F] 158 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)·`(An,Dn.W)`는 부호확장한다. `.B`·`.W` 연산은 나머지 bit를 보존하고 `MOVEQ`는 LONG 전체를 쓴다. `CMPA.W #0,An`는 An 32 bit 전체와 0을 비교한다. `SWAP`은 LONG의 두 WORD를 바꾼다. `MOVEM.L D0-D1/A0,-(A7)`는 A0, D1, D0 순으로 LONG을 push하고(메모리 낮은 쪽부터 D0 D1 A0), `MOVEM.L (A7)+,D0-D1/A0`는 D0, D1, A0 순으로 pop한다.

**거리 탐색 `46c68` 14** (D7 WORD 저장, 두 고정 노드 슬롯 `109156` `10b1d6`의 LONG `2e` 대상과의 차를 `447be`로 보냄)
- `46c68`: `MOVE.W D7,54d8(A5); MOVEM.L D0-D1/A0,-(A7); MOVEQ #0,D2; MOVEQ #0,D3; LEA 109156.L,A1; MOVEA.L 2e(A1),A2; CMPA.W #0,A2; BEQ.W 46cbe`
- `46c86`: `TST.W 2(A2); BEQ.W 46cbe`
- `46c8e`: `CMPA.W #0,A0; BEQ.W 46c9e`
- `46c96`: `ADD.L 14(A0),D0; ADD.L 18(A0),D1` (→`46c9e`)
- `46c9e`: `SUB.L 14(A1),D0; SUB.L 18(A1),D1; MOVEA.L A1,A0; SWAP D0; SWAP D1; BSR.W 447be` (U08)
- `46cb0`: `SWAP D1; SWAP D0; SWAP D7; CMP.W 54d8(A5),D7; BEQ.W 46d12`
- `46cbe`~`46cfa` 6: 같은 6 block을 `LEA 10b1d6.L,A1`로 반복한다(`46cbe` `46cd0` `46cd8` `46ce0` `46ce8` `46cfa`; 실패 분기는 `46d08`, 일치는 `46d12`).
- `46d08`: `MOVEM.L (A7)+,D0-D1/A0; ANDI.B #fe,CCR; RTS` (C=0 생산)
- `46d12`: `ADDA.W #c,A7; ORI.B #1,CCR; RTS` (저장한 12바이트를 복원 없이 버림; C=1 생산)

**`4be2c` 1**
- `4be2c`: `ADDI.L #ffffb000,3a(A6)` (→ U08b `4be34`)

**객체 `b631c` 계열 17**
- `b631c`: `MOVE.W #0,8e(A6); BSR.W b7bc2` (callback 진입)
- `b6326`: `BRA.W b66c8` (FLOW_ONLY)
- `b66c8`: `MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W b6710`
- `b66d4`: `LEA 26(A6),A0; MOVE.W #1b3,20(A6); MOVE.L 2001a8.L,22(A6); MOVEA.L #b7f54,A1; ADD.W D0,D0; ADD.W D0,D0; MOVE.L (A1,D0.W),D0; MOVEA.L 2001a8.L,A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L` (bank 자료; interpreter)
- `b670c`: `BRA.W b6748`
- `b6710`: `b66d4`와 같고 `#1bb`, `2001ac`를 쓴다.
- `b6748`: `MOVE.L #fffffff2,96(A6); MOVE.L #1e,98(A6); MOVE.B #5,9c(A6); MOVE.L #b6764,(A6)` (→`b6764`; 두 LONG 쓰기는 `98..99`에서 겹치며 순서대로 쓴다)
- `b6764`: `JSR b7cfa(PC)` (설치 callback 진입)
- `b6768`: `JSR 49fc6.L`
- `b676e`: `LEA 26(A6),A0; TST.W 4(A0); BNE.W b67a0`
- `b677a`: `SUBQ.B #1,9c(A6); BNE.W b67a0`
- `b6782`: `MOVE.L #fffffff6,96(A6); MOVE.L #1c,98(A6); LEA 26(A6),A0; JSR b7e06(PC)`
- `b679a`: `MOVE.B #f,9c(A6)` (→`b67a0`)
- `b67a0`: `JSR b7e5c(PC)`
- `b67a4`: `BCC.W b67ae` (carry 소비)
- `b67a8`: `MOVE.L #b67b2,(A6)` (→`b67ae`; 범위 밖 callback 설치)
- `b67ae`: `BRA.W b76d2`

**공유 꼬리 `b76a4` 22**
- `b76a4`: `BSR.W b7cfa` (설치 callback 진입)
- `b76a8`: `JSR 49fc6.L`
- `b76ae`: `BCC.W b76b8` (carry 소비)
- `b76b2`: `MOVE.L #b68be,(A6)` (→`b76b8`)
- `b76b8`: `BRA.W b76bc`
- `b76bc`: `LEA b7efc(PC),A1; BSR.W b7b4c` (경계 U19)
- `b76c4`: `BCC.W b76d2` (carry 소비)
- `b76c8`: `MOVE.B D0,9d(A6); MOVE.L #b6ba0,(A6)` (→`b76d2`)
- `b76d2`: `BTST.B #1,9f(A6); BEQ.W b76e0`
- `b76dc`: `JSR b7dd6(PC)` (경계)
- `b76e0`: `BTST.B #0,9f(A6); BEQ.W b772c`
- `b76ea`: `MOVE.W 92(A6),D0; ADD.W D0,94(A6); TST.W D0; BMI.W b770c`
- `b76f8`: `CMPI.W #2000,94(A6); BCS.W b7708` (WORD < `2000` 무부호)
- `b7702`: `MOVE.W #2000,94(A6)` (→`b7708`)
- `b7708`: `BRA.W b771a`
- `b770c`: `TST.W 94(A6); BPL.W b771a`
- `b7714`: `MOVE.W #0,94(A6)` (→`b771a`)
- `b771a`: `MOVE.B 19(A6),D0; MOVE.W 90(A6),D1; MOVE.B 94(A6),D2; JSR 8cda.L` (hud)
- `b772c`: `LEA b7eec(PC),A0; JSR 1aa7e.L` (U01)
- `b7736`: `BCC.W b7740` (carry 소비)
- `b773a`: `MOVE.L #b7742,(A6)` (→`b7740`)
- `b7740`: `RTS`

**초기화 `b7bc2` 15, `b7c42` 8**
- `b7bc2`: `CMPI.W #0,7a(A6); BNE.W b7bd2`
- `b7bcc`: `BSET.B #0,15(A6)` (→`b7bd2`)
- `b7bd2`: `CMPI.W #3,76(A6); BNE.W b7bea`
- `b7bdc`: `MOVE.W #3,D0; JSR 49a84.L`
- `b7be6`: `MOVE.W D0,76(A6)` (→`b7bea`)
- `b7bea`: `CMPI.W #1,80(A6); BNE.W b7bfa`
- `b7bf4`: `BSET.B #3,15(A6)` (→`b7bfa`)
- `b7bfa`: `MOVE.W #2,8c(A6); CMPI.W #0,8e(A6); BNE.W b7c1e`
- `b7c0a`: `JSR 1aa3a.L` (U08)
- `b7c10`: `BTST.B #3,D0; BEQ.W b7c1e` (D0 bit 3)
- `b7c18`: `BSET.B #1,9f(A6)` (→`b7c1e`)
- `b7c1e`: `JSR 4be06.L` (U11)
- `b7c24`: `MOVE.W #40,92(A6); MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); JSR ea5e0.L`
- `b7c3c`: `JSR b7c42(PC)`
- `b7c40`: `RTS`
- `b7c42`: `JSR 8ff4.L` (cleanup)
- `b7c48`: `BTST.B #1,9f(A6); BNE.W b7c6e`
- `b7c52`: `MOVE.W 8e(A6),D0; LEA b7f14(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.L` (fixed 표; U02)
- `b7c6a`: `BRA.W b7c88`
- `b7c6e`: `MOVE.W #ac3,D0; MOVE.B #1,D1; JSR 8ebe.L`
- `b7c7c`: `MOVE.W #ac4,90(A6); BSET.B #0,9f(A6)` (→`b7c88`)
- `b7c88`: `MOVE.W #d88,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `b7c96`: `MOVE.B 19(A6),14(A6); RTS`

**이동 `b7cfa` 8**
- `b7cfa`: `BTST.B #7,15(A6); BEQ.W b7d0e`
- `b7d04`: `JSR 4bfa4.L` (경계 U17)
- `b7d0a`: `BRA.W b7d2c`
- `b7d0e`: `JSR 4be2c.L`
- `b7d14`: `JSR 492c8.L` (U12)
- `b7d1a`: `BTST.B #7,15(A6); BEQ.W b7d2c`
- `b7d24`: `CLR.L 36(A6); CLR.L 3a(A6)` (→`b7d2c`)
- `b7d2c`: `RTS`

**`b7e06` 9, `b7e5c` 3**
- `b7e06`: `BTST.B #1,9f(A6); BEQ.W b7e56`
- `b7e10`: `MOVEA.L #d1f68,A0; MOVE.W #1e,D0; JSR 28ae.L` (fade_card 자식 생성)
- `b7e20`: `BCC.W b7e32` (carry 소비)
- `b7e24`: `CLR.W D0; CLR.W D1; JSR 4970a.L` (경계 U28)
- `b7e2e`: `ORI.B #1,CCR` (→`b7e32`; 소비 전에 덮이므로 Unknown)
- `b7e32`: `MOVE.W 96(A6),D0; MOVE.W 98(A6),D1; BTST.B #0,15(A6); BEQ.W b7e46`
- `b7e44`: `NEG.W D0` (→`b7e46`)
- `b7e46`: `ADD.W D0,2e(A0); ADD.W D1,32(A0); MOVE.W #0,9a(A6); RTS` (A0는 `28ae`/`4970a`가 남긴 값)
- `b7e56`: `ANDI.B #fe,CCR; RTS` (소비자 없음: Unknown)
- `b7e5c`: `TST.W 8c(A6); BEQ.W b7e6e`
- `b7e64`: `SUBQ.W #1,8c(A6); ANDI.B #fe,CCR; RTS` (C=0 생산)
- `b7e6e`: `JMP 4b54e.L` (U01, C 반환; FLOW_ONLY)

**자식 생성 `ea5e0` 3**
- `ea5e0`: `JSR 1abda.L` (U12)
- `ea5e6`: `BCC.W ea624` (carry 소비; U13 `ea624 RTS`)
- `ea5ea`: `MOVEQ #1,D2; BRA.W ea60c` (U13 공유 꼬리)

**거리 탐색 `ea636`/`ea65a` 11**
- `ea636`: `SUBI.L #90000,D1` (→`ea63c`)
- `ea63c`: `MOVEM.W D7,-(A7); ADDI.L #80000,D1; MOVE.W #4,D7; JSR 46c68.L`
- `ea650`: `MOVEM.W (A7)+,D7; DBCS D7,ea63c` (carry 소비; 결정 5)
- `ea658`: `RTS`
- `ea65a`: `BSR.B ea636`
- `ea65c`: `BCS.W ea662` (carry 소비)
- `ea660`: `RTS`
- `ea662`: `ANDI.L #fff80000,D1` (→`ea668`)
- `ea668`: `ADDI.L #80000,D1; MOVE.W #4,D7; JSR 46c68.L`
- `ea678`: `BCS.B ea668` (carry 소비)
- `ea67a`: `ORI.B #1,CCR; RTS` (C=1 생산)

**`ea762` 12**
- `ea762`: `CLR.B 78(A6); MOVEA.L c(A6),A0; JSR 289e.L` (readiness)
- `ea770`: `BCC.W ea7f2` (carry 소비)
- `ea774`: `MOVE.W 1e(A0),1e(A6); MOVE.L 42(A0),D0; MOVE.L 46(A0),D1; LEA 538e(A5),A0; SUB.L 14(A0),D0; SUB.L 18(A0),D1; BSR.W ea65a`
- `ea792`: `SCS.B 78(A6); BCS.W ea7aa` (carry 소비; BYTE `78` = C ? `ff` : `00`)
- `ea79a`: `MOVE.L 42(A6),D0; MOVE.L 46(A6),D1; SUB.L 14(A0),D0; SUB.L 18(A0),D1` (→`ea7aa`)
- `ea7aa`: `MOVEA.L A0,A1; LEA 2e(A6),A0; JSR 43e22.L` (cleanup)
- `ea7b6`: `MOVE.B #ff,D1; MOVEA.L c(A6),A0; BTST.B #7,15(A0); BEQ.W ea7ee`
- `ea7c8`: `MOVE.L 46(A6),D0; SUB.L 46(A0),D0; BLE.W ea7ee` (LONG 부호 있는 비교 `46(A6)` ≤ `46(A0)`)
- `ea7d4`: `ADDI.L #20000,D0; SUBI.L #a0000,D0; BCC.W ea7ee` (무부호 D0+`20000` ≥ `a0000`)
- `ea7e4`: `LSL.L #4,D0; SWAP D0; MOVE.W D0,D1; ADDI.W #100,D0` (→`ea7ee`)
- `ea7ee`: `MOVE.B D1,12(A6)` (→`ea7f2`)
- `ea7f2`: `RTS`

**자식 callback `ea7f4` 12**
- `ea7f4`: `MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); JSR 288c.L` (callback 진입)
- `ea806`: `BCC.W eaa54` (carry 소비)
- `ea80a`: `MOVE.W #e2,20(A6); BCLR.B #1,15(A6); MOVEQ #2,D7; BSR.W ea762`
- `ea81c`: `TST.B 78(A6); BNE.W ea908`
- `ea824`: `MOVE.L #ea82a,(A6)` (→`ea82a`; 설치 callback 진입이기도 함)
- `ea82a`: `JSR 288c.L` (설치 callback 진입)
- `ea830`: `BCC.W eaa54` (carry 소비)
- `ea834`: `MOVEQ #2,D7; BSR.W ea762`
- `ea83a`: `BCLR.B #7,5e51(A5); BNE.W ea852`
- `ea844`: `TST.B 78(A6); BEQ.W ea852`
- `ea84c`: `MOVE.L #ea85a,(A6)` (→`ea852`; 범위 밖 callback 설치)
- `ea852`: `BCLR.B #7,5e50(A5); RTS`

**`ea908` 상태 23**(`eaa54` 포함)
- `ea908`: `JSR 8ff4.L`; `ea90e`: `JSR 1abda.L`; `ea914`: `MOVEQ #0,D1; JSR 8ebe.L`
- `ea91c`: `CLR.L 36(A6); LEA ea742(PC),A1; MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L` (fixed 표)
- `ea93a`: `MOVE.L #ea940,(A6)` (→`ea940`)
- `ea940`: `JSR 288c.L` (설치 callback 진입)
- `ea946`: `BCC.W eaa54` (carry 소비)
- `ea94a`: `BCLR.B #7,5e51(A5); BNE.W ea824`
- `ea954`: `MOVEQ #8,D7; BSR.W ea762`
- `ea95a`: `MOVEA.L c(A6),A0; TST.L 36(A6); SNE.B D0; EXT.W D0; MOVE.L 36(A0),36(A6); SNE.B D0; CMPI.W #ff,D0; BNE.W ea9a8` (D0.W = 이전 `36`≠0 ? `ff..` : `00..` 상위 BYTE, 새 `36`≠0 ? `ff` : `00` 하위 BYTE)
- `ea976`: `LEA ea752(PC),A1; MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L`
- `ea990`: `BCLR.B #0,15(A6); TST.L 36(A6); BPL.W ea9a4`
- `ea99e`: `BSET.B #0,15(A6)` (→`ea9a4`)
- `ea9a4`: `BRA.W ea9ca`
- `ea9a8`: `CMPI.W #ff00,D0; BNE.W ea9ca`
- `ea9b0`: `ea91c`의 표 부분과 같다(`ea742`).
- `ea9ca`: `JSR 49a58.L` (RNG; stage_area)
- `ea9d0`: `ANDI.W #7f,D0; ADDI.W #40,D0; MOVE.W D0,2c(A6); TST.B 78(A6); BNE.W ea9ea`
- `ea9e4`: `MOVE.L #eaa00,(A6)` (→`ea9ea`)
- `ea9ea`: `ANDI.B #fe,CCR; BCLR.B #7,5e50(A5); BNE.W ea9fe` (소비자 없음: Unknown)
- `ea9f8`: `JSR 49fc6.L`
- `ea9fe`: `RTS`
- `eaa54`: `JMP 2a00.L` (fade_card 자기 삭제)

(수: 14 + 1 + 17 + 22 + 15 + 8 + 8 + 12 + 3 + 11 + 12 + 12 + 23 = 158.)

## 구현 범위와 규약

- routing 13 범위(위 표). 짝수 PC 784개 중 block 시작 158, 내부 626. 내부 PC 직접 진입은 `unsupported animation objects u18 PC`다. 경계 callee `4970a` `b7b4c` `b7dd6` `4bfa4`, 범위 밖 설치 callback, 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **FLOW_ONLY 69개**(C 보존): JSR/BSR/JMP/BRA/RTS/LEA/MOVEA만인 block(`b6326` `b670c` `b6764` `b6768` `b67a0` `b67ae` `b76a4` `b76a8` `b76b8` `b76bc` `b76dc` `b7708` `b772c` `b7740` `b7c0a` `b7c1e` `b7c3c` `b7c40` `b7c42` `b7c6a` `b7d04` `b7d0a` `b7d0e` `b7d14` `b7d2c` `b7e6e` `ea5e0` `ea658` `ea65a` `ea660` `ea7aa` `ea7f2` `ea82a` `ea908` `ea90e` `ea940` `ea9a4` `ea9ca` `ea9f8` `ea9fe` `eaa54`), BTST/BSET/BCLR(+Bcc/RTS)만인 block(`b76d2` `b76e0` `b7bcc` `b7bf4` `b7c10` `b7c18` `b7c48` `b7cfa` `b7d1a` `b7e06` `ea83a` `ea852` `ea94a` `ea99e`), 소비자 14개.
- **known carry 생산 4개**: `46d08` Clear, `46d12` Set, `b7e64` Clear, `ea67a` Set. 그 밖 85개는 Unknown이다(`b7e2e` `b7e56` `ea9ea` 포함).
- **소비자 14개**: 위 결정 4. 들어오는 C가 Unknown이면 `objects u18 caller requires known carry`(상태 보존).
- [F] **callback 복귀 C(2026-10-27 기록, U18 변경 없음).** `ea940` 상태의 `ea9ea` → `ea9f8 JSR 49fc6` → `ea9fe RTS` 경로는 interpreter의 known C를 dispatcher `2ac2`로 돌려준다(`ea9f8` `ea9fe`는 FLOW_ONLY 그대로). 이 node가 pass의 마지막 node이면(io-ext2 P2 자식, D1 frame 295 / D2 frame 481) 그 C가 frame 끝까지 남아 IO 검증기의 carry Unknown 조건과 어긋났다. 처리는 frame 구동기 쪽이다: `animation-machine-frame-driver-d1.md` "개정: frame 끝 carry"에 따라 pass 끝은 C Unknown을 보고한다. U18 실행부·시험·block 분류는 바꾸지 않았다.
- 루프: `ea650 DBCS`(결정 5)와 `ea678 BCS.B ea668`(`46c68`이 C=1을 돌려주는 동안). 둘 다 실행부 block 한도로만 묶는다.
- 스택: JSR/BSR 복귀 LONG, `46c68`/`46d08`의 MOVEM.L 12바이트, `46d12`의 `ADDA.W #c,A7`, `ea63c`/`ea650`의 MOVEM.W 2바이트. 스택 쓰기·읽기는 기존 program stack 규칙(work RAM, 짝수)이다.
- I/O port 쓰기 없음. bank 변경 없음. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM 읽기, physical span 밖 bank 읽기는 기존 checked 오류다.

## 의존·경계

- [F] U18 → 기존: U08 `447be` `1aa3a`, interpreter `49f8c` `49fc6`, U01 `1aa7e` `4b54e`, hud `8cda`, U11 `4be06`, stage_event_ops `49a84` `288c`, cleanup `8ff4` `43e22`, U02 `8ebe`, U12 `492c8` `1abda`, fade_card `28ae` `2a00`, readiness `289e`, stage_area `49a58`, U08b `4be34`, U13 `ea60c` `ea624`.
- [F] U18 → 경계: `4970a`(U28), `b7b4c`(U19), `b7dd6`(미배정), `4bfa4`(U17). 범위 밖 설치 callback `b67b2` `b68be` `b6ba0` `b7742` `ea85a` `eaa00`은 쓰기만 한다. 자식 callback `d1f68`(`28ae` A0)도 쓰기만 한다.
- [F] 다른 단위 → U18: stage event 표 `e8edc`(`b631c`), U13 `ea60c`(`ea7f4` 자식), 범위 밖 `b769e`(`b76a4` 설치), `4be2c` 호출 144곳, `b7bc2` `b7cfa` `b7e06` `b7e5c` `b76d2` `ea5e0` `ea65a`의 범위 밖 호출자(위 "참조").

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, TB 기준)에서 U18 block에 닿는 seed:
- `b631c` `b6326` `b66c8` `b66d4` `b670c` `b6748`~`b67ae`, `b7e06` `b7e56`: seed 68 69 70 71.
- `46c68` 계열·`ea636`~`ea660`·`ea762`~`ea852`: seed 8 9 68 69 70 71(`46c86`은 68~71만).
- `b76d2` `b76e0` `b772c` `b7736` `b7740`, `b7bc2` 계열, `b7c42` 계열, `ea5e0` `ea5e6`: 위 seed와 2 3 6 7 12 13 26 27 42 43 62 63 80 81(변형별로 다름). `b76bc` `b76c4`: 80 81.
- `4be2c`: 36 37 42 43 68~71 80 81(RNG 변형은 2 3 12 13 26 27 76 77 98 99 104 105도).
- 158 block 중 TB 기준 base 90개, RNG+`80` 변형 90개가 자연 도달한다. 미도달 68개(`46c8e` `46c96` `46c9e` `46cb0` `46ce8` `46d12` `b6710` `b67a8` `b76a4`~`b76b8` `b76c8` `b76dc` `b76ea`~`b771a` `b773a` `b7bdc` `b7be6` `b7bf4` `b7c18` `b7c6e` `b7c7c` `b7e10`~`b7e46` `ea662`~`ea67a` `ea7aa` `ea7d4` `ea7e4` `ea7f2` `ea84c` `ea908`~`ea9fe` `eaa54`)는 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] 기준 C++ 차분(이 작업 트리 `9682aed`, `tools/verify_animation_machine_scheduler_f4.py`를 scratch 출력으로 실행): 일치 pass 10,498개·node 79,680개, 불일치 0, 자연 완주 95 seed. seed 68~71의 첫 미연결 callback은 `b631c`. RNG 초기화 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py`): 일치 pass 24,646개·node 169,037개, 불일치 0, complete 61.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 158 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산자 known, 그 밖 Unknown; 소비자는 Unknown이면 오류), zero-step, 내부 626 PC 정확한 오류, 홀수 PC, 경계 `4970a` `b7b4c` `b7dd6` `4bfa4` stop(다른 F4 단위 PC는 stop만), rollback 탐침은 RAM `10fe00..10fefe`만. 생산자 C는 실제 소비자(`ea678` `b67a4` `ea792`)의 native 분기로 확인한다. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력과 합성 bank·표 바이트)로 비교한다.
- 실제 ROM 차분: `46c68` 계열(실제 `447be`), `ea65a`→`ea636`→`46c68` 루프, `ea762`(실제 `289e` `43e22`), `ea7f4`/`ea82a`/`ea940`(실제 `288c`), `b631c`(실제 `b7bc2`→`49a84` `1aa3a` `4be06` `ea5e0` `1abda` `ea60c` `28ae`, `8ff4` `8ebe`, bank `200000`의 `2001a8`), `b6764`(실제 `b7cfa`→`4be2c`→`4be34`, `492c8`, `49fc6`, `b7e5c`, `b76d2` 꼬리 `8cda` `1aa7e`)를 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 기준 이상, 불일치 0, complete 61 이상. U17+U18 조합은 scratch로 따로 잰다(결정 2).

## 미확인·범위 밖

1. [I] `46c68`은 두 고정 슬롯(`109156`, `10b1d6`; 플레이어 1·2 노드로 보임)의 대상 노드와 (D0,D1) 좌표 차를 `447be`(U08)로 판정하고, 판정이 D7 상위 WORD를 저장값과 같게 만들면 C=1(발견)을 돌려준다. 게임 의미는 미확인이다.
2. [I] `ea65a`는 D1을 `90000`부터 `80000`씩 올리며 `46c68`을 최대 D7+1번 부르는 세로 탐색으로 보이고, `ea762`는 부모 노드(`c(A6)`) 기준 좌표로 그 결과를 BYTE `78`에 둔다.
3. [I] `b631c`는 범위 문서 U19/U28의 `b6300`~`b6368` 진입 표의 한 항목(`8e`=0)이며, `b7bc2`가 방향·palette·자식 `ea5e0`(→`ea7f4`)을 준비한다.
4. [U] 경계 `4970a` `b7b4c` `b7dd6` `4bfa4`와 범위 밖 설치 callback의 본문·실행 결과는 U18 밖이다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/u18/`(`u18.py` block·범위·SHA 계산, `body.py` `scope.py` `trav.py` `hroute.py` `owner.py` `u18dis.py`, `refs.py` `nextins.py` `probes.py` `reach.py` `dynreach.py`; 저장소 밖).
