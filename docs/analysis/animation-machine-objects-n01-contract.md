# 객체 callback F4 N01: 파편 객체 `5208a`(설치 `52100`)와 U07 자식 객체 `e5bb0` `e5c74` `e5d72`/`e5d86` `e5ea0`(설치 `e5c06` `e5cdc` `e5dfa` `e5eca` `e5f1a`, 자식 `e5f32`와 그 설치 `e5f74` `e5f9e`) 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 재범위 문서 `animation-machine-object-callbacks-f4-rescope.md`(SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 메인 결정 1~5와 N01 행이다. 단위 형식과 규약은 U19 계약(`animation-machine-objects-u19-contract.md`, SHA256 `f7ac9c28c24a42c450ceb36edddf33a1393c9b1cf94f9bc9072a028c7bbf8ca3`, 같은 bank 표 animation 형식과 `49fc6` 반환 C 소비), U07 계약(SHA256 `734615e139a6e0577154eace301c66a0ea9fb94137e0e6cf921dd15ff1ab99a9`, `e5878` 계열이 `28ae`로 만드는 자식 callback `e5ea0` `e5bb0` `e5c74` `e5d72` `e5d86`), U14 계약(SHA256 `22952574c990f88d5da5d9104286d505a09ce424b2cfbd35ed17d340fd34b9db`, `52014`가 `2986`으로 만드는 자식 callback `5208a`와 그 입력 `76`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` 설치와 `MOVEA.L #imm,A0`+`JSR 28ae` 자식 callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC는 실행부 없는 경계다(N01에는 경계가 없다; 아래).
- 재범위 결정 2: 단위 안에서 설치되는 callback은 본문이 단위 범위 안에 있으면 포함한다.
- U01~U20 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`Scc`)만인 block과 callee C를 소비하는 단독 Bcc는 FLOW_ONLY다. `ADDQ`/`SUBQ`/`ADDI`/`ADD`/`LSL` block은 Unknown이다. 같은 flag를 쓰는 연속 Bcc는 묶는다(N01에는 없음). 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C를 소비자에서 쓰려면 native 분기 결과로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N01의 코드와 fixed 자료는 모두 `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료(`2000b8` `2000c8` `2001e0`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n01`(HEAD `aa35e83` = U20a까지 통합, `engine/src/animation_machine.cpp` SHA256 `ae8b975237c3c98331c8d09d501f4bb882345d0e187a9dcb7db28af2de9ac3b3`, routing 규칙 57개)을 참조했다. 동시에 진행하는 U20b(`849f4..84a14` `858d8..85c6c`, 작업 트리 `metalslug-u20b`)의 PC는 N01에서 나오지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n01/n01blocks.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **N01 = 74 block**, 코드 3 범위 1,210바이트, 273명령이다. 재범위 N01 행의 69 block(12 callback 본문)에 다음 5 block을 더했다(결정 2, 아래 "메인 결정 1").
  - `e5d86`(1): U07 `e5910` `e5956`이 `28ae`로 설치하는 자식 callback이다. 본문(`LEA e5e80(PC),A0`…`BRA.W e5d9a`)이 N01 범위 안에 있고 `e5d9a` 이후를 `e5d72`와 공유한다. 재범위 문서는 이를 "고아 설치 callback(본문 일부 실행)"으로 따로 셌다.
  - `e5f1a` `e5f22` `e5f30`(3): `e5f04 MOVE.L #e5f1a,(A6)`의 설치 callback 본문.
  - `e5f9e`(1): `e5f98 MOVE.L #e5f9e,(A6)`의 설치 callback 진입(`e5fa4` 이후는 이미 69 안).
  - 재범위 문서의 "미실행 설치 2(+4)"가 `e5f1a`(+3)·`e5f9e`(+1)다.
- [F] 진입 6개(`5208a` `e5bb0` `e5c74` `e5d72` `e5d86` `e5ea0`; 모두 다른 단위가 `2986`/`28ae`로 만드는 자식 callback), 설치 callback 8개(`52100` `e5c06` `e5cdc` `e5dfa` `e5eca` `e5f1a` `e5f74` `e5f9e`), 범위 안 `28ae` 자식 1개(`e5f32`, `e5edc`가 설치)다.
- [F] 미해독·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx·계산 PC(JMP/JSR 표, 레지스터 간접)·I/O port 쓰기·bank 변경은 없다. 범위 밖 호출은 모두 이미 routing된 실행부다(아래 "의존"). 실행부 없는 경계는 없다.
- [F] **carry**: 소비 block 2개 `e5c12` `e5e06`(`BCC.W`, `49fc6` 반환 C). known 생산 block은 없다. 모든 callback은 scheduler가 부르며 반환 C를 소비하는 호출자가 없다.
- [F] 자료 읽기: bank window LONG 3개(`2001e0` 1곳, `2000c8` 6 block, `2000b8` 3 block)와 그 값이 가리키는 LONG, fixed ROM 자료 표 5개(`5205e` 8바이트 record, `5206e` WORD 표, `e5e80`/`e5e90` WORD 표, `e5fbe` WORD 3개 record 흐름, `e60c6` LONG 표). 모두 live bus로 읽는다. 표 index는 node WORD/BYTE에서 오고 원본에 상한 검사가 없으므로 C++도 상한 없이 같은 주소를 읽는다(F1 결정 3의 계산 PC 정책 대상이 아니다: 자료 읽기이며 제어 이동이 아니다).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`, TB 기준): RNG 초기화+응답 `80` 400 frame에서 seed 84 85(f2~, `5208a` 계열)와 92 93(f0~, `e5bb0` `e5c74` `e5d72` `e5ea0` 계열)이 74 시작 중 56개를 실행한다. 자연 미도달 18개: `e5c16` `e5c4a` `e5d38` `e5d86` `e5e0a` `e5e48` `e5eb2` `e5f04` `e5f1a` `e5f22` `e5f30` `e5f5c` `e5f90` `e5f98` `e5f9e` `e5fa4` `e5fae` `e5fbc`. base 120 frame 기록에서는 0개다. typed fixture로 덮는다.
- [F] 기준 측정(이 작업 트리 `aa35e83`, scratch 출력): base 일치 pass 11,938·node 93,222, 불일치 0, 자연 완주 109. RNG 400: 일치 pass 33,604·node 243,049, 불일치 0, complete 84. seed 84 85는 f2 `5208a`, 92 93은 f0 `e5d72`가 첫 미연결 callback이다. 기대: RNG 84 85 92 93 완주(재범위 문서 84→88), base 변화 없음.
  - [F] 작업자 scratch 측정(구현 후, 같은 도구): base 일치 pass 11,938·node 93,222, 불일치 0, 자연 완주 109(변화 0, 회귀 0). RNG 400: 일치 pass 35,200·node 254,699, 불일치 0, complete 88(새 complete 84 85 92 93, 잃은 것 0). 두 기록에서 `2986` caller-X 제한은 나타나지 않았다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 69→74.** 권고: 재범위 결정 2대로 범위 안 본문을 가진 설치 callback `e5f1a` `e5f9e`와, U07이 설치하지만 본문이 N01 범위 안에 있고 `e5d72`와 본문을 공유하는 `e5d86`을 포함한다. 대안: `e5d86`을 고아 정리 단계로 미룬다(비권고: 1 block이고 `e5d86`은 N01 routing 범위 `e5bb0..e5e80` 한가운데라 빼면 그 PC가 N01 내부 PC 오류가 된다).
2. **routing 범위는 코드만.** `5208a..52156`, `e5bb0..e5e80`, `e5ea0..e5fbe`(짝수 PC 605개, block 시작 74, 내부 531). 사이의 자료 `e5e80..e5ea0`(WORD 표)과 앞뒤 자료 `5205e..5208a`, `52156..`, `e5fbe..`는 routing하지 않는다(`unsupported animation machine PC`). 재범위 문서의 `e5bb0..e5fbe` 표기는 자료 32바이트를 포함한 요약이다.
3. **자료 표는 live bus 읽기.** 위 5개 fixed ROM 표와 3개 bank LONG(및 그 값 + d16/index의 LONG)은 C++ 상수로 옮기지 않고 실행 시 program bus로 읽는다(U17/U19 bank 표와 같은 방식). index는 원본과 같이 부호확장 WORD다.
4. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n01.cpp`의 `animation_objects_n01_block`. 오류는 `unsupported animation objects n01 PC`(내부 PC), `objects n01 caller requires known carry`(소비자 `e5c12` `e5e06`의 Unknown C).
5. **무효화 탐침**(F4 test 경계 관례대로 고친다).
   - `engine/tests/animation_machine_objects_u07_test.cpp` `interior()`의 `outside[]` 중 `0xe5bb0` `0xe5bb2` `0xe5ea0` `0xe5c74` `0xe5d72` `0xe5d86`(이제 N01 block 시작 또는 N01 내부 PC) → work RAM 탐침 `10fe00..10fefe`로 바꾼다. 나머지(`48256` `4e1cc` `4e1ce` `e583c` `e585a`)는 그대로 유효하다.
   - U14 test의 `0x5208a`, U07 test의 `e5d72`/`e5d86`/`e5bb0`/`e5c74`/`e5ea0` 나머지 출현은 `28ae`/`2986`에 넘기는 A0 값(자료)이라 영향이 없다. `tools/`에는 N01 PC를 경계로 쓰는 곳이 없다.
6. **52014/2986 caller-X 제한.** `5208a` node는 U14 `52014`의 `JSR 2986`(buffer_cue)으로 만들어진다. `2986` 실패 경로의 caller X 제한(buffer_cue 결정 1 선택 A, `cue wrapper failure requires known caller X`)은 그대로 둔다. N01은 `2986`을 부르지 않는다. seed 84 85 차분에서 이 제한이 나오면 보고한다.

## 원본 바이트 근거

[F] 코드 3 범위 합계 1,210바이트. 범위 순서로 이어 붙인 SHA256 `d58a79ace9985010956f66f50207a454b63bd52d7ee8c069a57f1e5dae3f0778`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `5208a..52156` | 204 | `67968068c983c1c64f2af15a27033c5e6bc5e9abb0d62a9b52febfefde7860a7` | `5208a`, 설치 `52100` |
| `e5bb0..e5e80` | 720 | `437979a289b29f211ad966c29a43262e8ee5d5d9176fa9695005b73131efde0f` | `e5bb0` `e5c74` `e5d72` `e5d86` 계열 |
| `e5ea0..e5fbe` | 286 | `6941de3a53819133728a044a122fcc7ffeb0188389adea7896a763f39a203d96` | `e5ea0` 계열, 자식 `e5f32` |

자료(읽기 전용 참고, 실행 시 live bus):

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `5205e..5208a` | 44 | `0899cb7221cc125d99e4dcab4de7d06acf38c19296852068619967cd69187685` | `5205e` record 2개(WORD x, WORD y, LONG A1: `00e0 00d0 00052156`, `00b0 0090 0005216a`)와 `5206e` WORD 표(`0e72..0e7b`, 이어 `ffff` 4개) |
| `e5e80..e5ea0` | 32 | `65d1c8c749bf2bdf1ca292533064d7a463518513f9ddb8efe588d37fbbb01399` | `e5e80` `0006 0007 000b 000c 0010 0011 0016 0017`, `e5e90` `0004 0005 0009 000a 000e 000f 0014 0015` |
| `e5fbe..e60c2` | 260 | `e0eaf7f95accbd182ff0cb62c6879b5bfc88a35012be4609886bd4752b3d84b8` | WORD 3개 record 43개(`7c`/`7e`/`80`: `0030 0001 0e1f` … `0c38 002b 0e1f`), 끝 `ffff` |
| `e60c6..e6176` | 176 | `f7206fc28da8d2fd20086340c9379ca2bf6b6c26785e61d915a7d3762d701d02` | LONG 표 index 0~43(`14a` `14a` `94a` … `1494a`, `0`) |

- [F] 범위 밖 이웃: `51ffa..5205e`(U14, `5205c RTS`), `e585c..e5bb0`(U07, `e5bae RTS`). `52156..`과 `e5fbe..`은 자료다.
- [F] 참조: `5208a`는 U14 `52014`(`MOVEA.L #5208a,A0; … JSR 2986`) 1곳. `e5bb0`은 U07 `e5898`, `e5c74`는 `e58a8`, `e5ea0`은 `e5888`, `e5d72`는 `e5926` `e5940` `e5970` `e598a`, `e5d86`은 `e5910` `e5956`(모두 `MOVEA.L #x,A0; MOVE.W #a,D0; JSR 28ae`). `52100`은 `520fa`, `e5f32`는 `e5edc`(fixed ROM 안 같은 LONG 바이트의 다른 출현 `f28b9` `f4269`는 홀수 위치 자료).

## block 목록과 실행 의미

[F] 74 block. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. WORD 연산은 하위 WORD만 바꾼다. 비교 분기: `BLT`/`BLE`는 부호 있는 WORD, `BPL`은 결과 bit 15, `BEQ`/`BNE`는 결과 0 여부다. "animation(k, bank, d16)"은 `LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d16(A1),A1; JSR 49f8c.L`(bank LONG과 그 값+d16의 LONG을 live bus로 읽는다)이고, "animation-index(k, bank)"는 `LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); LEA 26(A6),A0; [MOVE.W D0,D1;] ADD.W D1,D1; ADD.W D1,D1; MOVEA.L bank.L,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.L`(D1.W×4를 부호확장 index로, bank LONG은 두 번 읽는다)다.

**`5208a` 13** (파편; U14 `52014`가 `2986`으로 생성, `76`=0..1)
- `5208a`: `MOVE.W #223,20(A6); MOVE.L 2001e0.L,22(A6); MOVE.W #189f,D0; JSR 3af8.L` (→`520a2`)
- `520a2`: `MOVE.W 76(A6),D0; ADDQ.B #1,5d2d(A5); LSL.W #3,D0; LEA 5205e(PC,D0.W),A0; MOVE.W (A0)+,D0; MOVE.W (A0)+,D1; MOVE.L A0,-(A7); MOVE.W D0,2e(A6); MOVE.W D1,32(A6); MOVEA.L (A7)+,A0; MOVEA.L (A0),A1; MOVE.W #100,D0; JSR 49f8c.L` (record = `5205e`+sext(`76`×8 WORD); A0 = record+4; stack LONG 1개 쓰기 후 복원)
- `520cc`: `MOVE.W #0,68(A6); MOVE.W #0,1e(A6); JSR 16ef0.L`
- `520de`: `CLR.W 8c(A6); MOVE.W #40,D0; JSR 49a84.L`
- `520ec`: `ADDI.W #60,D0; MOVE.W D0,8e(A6); MOVE.W #ffff,90(A6); MOVE.L #52100,(A6)` (→`52100`)
- `52100` (설치 callback): `MOVEQ #0,D0; MOVE.B 8c(A6),D0; ADD.W D0,D0; LEA 5206e(PC),A0; MOVE.W (A0,D0.W),D0; CMPI.W #ffff,D0; BEQ.W 5214c` (→`52118`; BYTE `8c`는 WORD `8c`의 상위 BYTE)
- `52118`: `CMP.W 90(A6),D0; BEQ.W 52136` (→`52120`)
- `52120`: `MOVE.W D0,90(A6); JSR 8ff4.L`
- `5212a`: `MOVE.W 90(A6),D0; MOVEQ #0,D1; JSR 8ebe.L`
- `52136`: `JSR 43e34.L` (FLOW_ONLY)
- `5213c`: `JSR 49fc6.L` (FLOW_ONLY)
- `52142`: `MOVE.W 8e(A6),D0; ADD.W D0,8c(A6); RTS`
- `5214c`: `SUBQ.B #1,5d2d(A5); JMP 2a00.L`

**`e5bb0` 12** (U07 `e5898` 자식)
- `e5bb0`: `MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L`
- `e5bba`: `MOVE.W #8810,68(A6); MOVE.W #8810,1e(A6); MOVE.W #31,D0; MOVE.W #1,D1; MOVE.B #0,D2; JSR c6a96.L`
- `e5bd8`: animation(`14a`, `2000c8`, 4) (→ `JSR 49f8c`, 복귀 `e5c00`)
- `e5c00`: `MOVE.L #e5c06,(A6)` (→`e5c06`)
- `e5c06` (설치 callback): `JSR 43e34.L` (FLOW_ONLY)
- `e5c0c`: `JSR 49fc6.L` (FLOW_ONLY)
- `e5c12`: `BCC.W e5c3e` (→`e5c16`; FLOW_ONLY 소비자, `49fc6` 반환 C)
- `e5c16`: animation(`14a`, `2000c8`, 4) (복귀 `e5c3e`)
- `e5c3e`: `MOVEA.L c(A6),A0; TST.B 62(A0); BEQ.W e5c72` (→`e5c4a`; 부모 node BYTE `62`)
- `e5c4a`: animation(`14a`, `2000c8`, 8) (복귀 `e5c72`)
- `e5c72`: `RTS` (FLOW_ONLY)

**`e5c74` 11** (U07 `e58a8` 자식)
- `e5c74`: `MOVEQ #-c,D0; MOVEQ #1e,D1; JSR 49290.L` (D0=`fffffff4`)
- `e5c7e`: `MOVE.W #8834,68(A6); MOVE.W #8834,1e(A6); MOVE.W #2d,D0; MOVE.W #0,D1; MOVE.B #0,D2; JSR c6a96.L`
- `e5c9c`: `MOVE.W #c,76(A6); MOVE.W #1,D0;` animation-index(`12a`, `2000b8`) with `MOVE.W D0,D1` (복귀 `e5cd6`)
- `e5cd6`: `MOVE.L #e5cdc,(A6)` (→`e5cdc`)
- `e5cdc` (설치 callback): `JSR 43e34.L` (FLOW_ONLY)
- `e5ce2`: `JSR 49fc6.L` (FLOW_ONLY; 반환 C는 다음 block의 `TST.W`가 덮는다)
- `e5ce8`: `LEA 26(A6),A0; TST.W 4(A0); BNE.W e5d2c` (→`e5cf4`; WORD `2a(A6)`)
- `e5cf4`: `MOVE.W #1,D0; ADD.W 76(A6),D0;` animation-index(`12a`, `2000b8`) with `MOVE.W D0,D1` (복귀 `e5d2c`)
- `e5d2c`: `MOVEA.L c(A6),A0; TST.B 62(A0); BEQ.W e5d70` (→`e5d38`)
- `e5d38`: `e5cf4`와 같은 명령(복귀 `e5d70`)
- `e5d70`: `RTS` (FLOW_ONLY)

**`e5d72`/`e5d86` 14** (U07 자식; `8c`는 부모가 넣은 index)
- `e5d72`: `LEA e5e90(PC),A0; MOVE.W 8c(A6),D0; LSL.W #2,D0; MOVE.W (A0,D0.W),8c(A6); BRA.W e5d9a`
- `e5d86`: `LEA e5e80(PC),A0;` 나머지 `e5d72`와 같음(`BRA.W e5d9a`)
- `e5d9a`: `MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L`
- `e5da4`: `LEA 26(A6),A0; MOVE.W #14a,20(A6); MOVE.L 2000c8.L,22(A6); LEA 26(A6),A0; MOVE.W 8c(A6),D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L 2000c8.L,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.L`
- `e5dd6`: `MOVE.W 8c(A6),D1; MOVE.W #31,D0; MOVE.B #0,D2; JSR c6a96.L`
- `e5de8`: `MOVE.W #8834,68(A6); MOVE.W #8834,1e(A6); MOVE.L #e5dfa,(A6)` (→`e5dfa`)
- `e5dfa` (설치 callback): `JSR 43e34.L` (FLOW_ONLY)
- `e5e00`: `JSR 49fc6.L` (FLOW_ONLY)
- `e5e06`: `BCC.W e5e3c` (→`e5e0a`; FLOW_ONLY 소비자, `49fc6` 반환 C)
- `e5e0a`: `e5da4`와 같은 명령(복귀 `e5e3c`)
- `e5e3c`: `MOVEA.L c(A6),A0; TST.B 62(A0); BEQ.W e5e7e` (→`e5e48`)
- `e5e48`: `MOVE.W 8c(A6),D0; ADDQ.W #1,D0;` animation-index(`14a`, `2000c8`) with `MOVE.W D0,D1` (복귀 `e5e7e`)
- `e5e7e`: `RTS` (FLOW_ONLY)

**`e5ea0` 24** (U07 `e5888` 자식; 흐름 `e5fbe`에서 자식 `e5f32`를 차례로 만든다)
- `e5ea0`: `MOVE.W #0,76(A6); LEA e5fbe(PC),A0; MOVE.W (A0)+,7c(A6); BPL.W e5eb8` (→`e5eb2`)
- `e5eb2`: `JMP 2a00.L` (FLOW_ONLY)
- `e5eb8`: `MOVE.W (A0)+,7e(A6); MOVE.W (A0)+,80(A6); MOVE.L A0,88(A6); MOVE.L #e5eca,(A6)` (→`e5eca`)
- `e5eca` (설치 callback): `MOVE.W 76(A6),D0; ADDQ.W #1,D0; MOVE.W D0,76(A6); CMP.W 7c(A6),D0; BLT.W e5f18` (→`e5edc`)
- `e5edc`: `MOVEA.L #e5f32,A0; MOVE.W #a,D0; JSR 28ae.L`
- `e5eec`: `MOVE.W 7e(A6),7e(A0); MOVE.W 80(A6),80(A0); MOVEA.L 88(A6),A0; MOVE.W (A0)+,7c(A6); BPL.W e5f0c` (→`e5f04`; A0는 `28ae`가 돌려준 자식 node)
- `e5f04`: `MOVE.L #e5f1a,(A6); RTS`
- `e5f0c`: `MOVE.W (A0)+,7e(A6); MOVE.W (A0)+,80(A6); MOVE.L A0,88(A6)` (→`e5f18`)
- `e5f18`: `RTS` (FLOW_ONLY)
- `e5f1a` (설치 callback): `TST.B 62(A6); BEQ.W e5f30` (→`e5f22`)
- `e5f22`: `MOVEA.L c(A6),A0; ST.B 63(A0); JMP 2a00.L` (FLOW_ONLY; `ST`는 CCR을 바꾸지 않는다)
- `e5f30`: `RTS` (FLOW_ONLY)
- `e5f32` (자식 callback): `MOVE.W #a0,2e(A6); MOVE.W #e0,32(A6); MOVE.L #8000,3a(A6); LEA e60c6(PC),A0; MOVE.W 7e(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVE.L (A0,D0.W),84(A6); BNE.W e5f60` (→`e5f5c`)
- `e5f5c`: `BRA.W e5f98` (FLOW_ONLY)
- `e5f60`: `MOVE.W 80(A6),D0; MOVE.B #0,D1; JSR 8ebe.L`
- `e5f6e`: `MOVE.L #e5f74,(A6)` (→`e5f74`)
- `e5f74` (설치 callback): `JSR 43ea4.L` (FLOW_ONLY)
- `e5f7a`: `MOVE.L 84(A6),D7; MOVEQ #0,D0; JSR 16ea4.L`
- `e5f86`: `CMPI.W #220,32(A6); BLE.W e5f96` (→`e5f90`)
- `e5f90`: `JMP 2a00.L` (FLOW_ONLY)
- `e5f96`: `RTS` (FLOW_ONLY)
- `e5f98`: `MOVE.L #e5f9e,(A6)` (→`e5f9e`)
- `e5f9e` (설치 callback): `JSR 43ea4.L` (FLOW_ONLY)
- `e5fa4`: `CMPI.W #200,32(A6); BLE.W e5fbc` (→`e5fae`)
- `e5fae`: `MOVEA.L c(A6),A0; ST.B 62(A0); JMP 2a00.L` (FLOW_ONLY)
- `e5fbc`: `RTS` (FLOW_ONLY)

(수: 13 + 12 + 11 + 14 + 24 = 74.)

## 구현 범위와 규약

- routing 3 범위(위 표). 짝수 PC 605개 중 block 시작 74, 내부 531. 내부 PC 직접 진입은 `unsupported animation objects n01 PC`다. 범위 이웃은 기존 실행부(U14, U07) 또는 routing 밖 자료(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **FLOW_ONLY 24개**(C 보존): `52136` `5213c` `e5c06` `e5c0c` `e5c12` `e5c72` `e5cdc` `e5ce2` `e5d70` `e5dfa` `e5e00` `e5e06` `e5e7e` `e5eb2` `e5f18` `e5f22` `e5f30` `e5f5c` `e5f74` `e5f90` `e5f96` `e5f9e` `e5fae` `e5fbc`.
- **소비자 2개**: `e5c12`(`BCC.W e5c3e`), `e5e06`(`BCC.W e5e3c`). C Clear면 분기, Set이면 fall-through, Unknown이면 `objects n01 caller requires known carry`. [F] 자연 기록에서 `e5c12`→`e5c3e`(C=0)만 나타났다(`e5c16` 미도달). `e5e06`도 `e5e3c`만(`e5e0a` 미도달).
- **known carry 생산 없음.** 그 밖 50 block(`MOVE`/`MOVEQ`/`MOVEA`+`TST`/`CLR`/`CMP`/`CMPI`/`ADD`/`ADDI`/`ADDQ`/`SUBQ`/`LSL` block, `MOVE.L #imm,(A6)` block, bank animation block)은 Unknown이다.
- 제어 이동은 모두 정적이다(계산 PC 없음).
- 스택: `JSR`/`RTS` 복귀 LONG과 `520a2`의 `MOVE.L A0,-(A7)`/`MOVEA.L (A7)+,A0`(LONG 1개 쓰기·읽기).
- I/O port 쓰기 없음. bank 변경 없음. work RAM 밖 쓰기, 미해결·홀수 읽기는 기존 checked 오류다.

## 자료

- [F] bank window LONG(bank base `200000`에서 실제 PVC bank 모델로 읽음): `2001e0`(`5208a` → `22(A6)`만), `2000c8`(`e5bd8` `e5c16` `e5c4a`: 값 → `22(A6)`, 이어 `22(A6)`의 값 + 4/+4/+8의 LONG → A1; `e5da4` `e5e0a` `e5e48`: 값 → `22(A6)`, 다시 같은 LONG + sext(4×index)의 LONG → A1), `2000b8`(`e5c9c` `e5cf4` `e5d38`: 같은 꼴, index 1 / 1+`76`).
- [F] fixed ROM: `5205e`+sext(8×`76`)의 WORD 2개와 LONG 1개, `5206e`+2×BYTE `8c`의 WORD, `e5e90`/`e5e80`+sext(4×`8c`)의 WORD, `88(A6)`(처음 `e5fbe`)부터 WORD 3개씩, `e60c6`+sext(4×`7e`)의 LONG.
- [F] node(A6): WORD `1e` `20` `2e` `32` `68` `76` `7c` `7e` `80` `8c` `8e` `90`, LONG `0`(설치) `22` `3a` `84` `88`, BYTE `62`(`e5f1a` 자기), `8c`(상위 BYTE 읽기). 부모 node(`c(A6)`): BYTE `62`(TST, ST) `63`(ST). 자식 node(`28ae` 반환 A0): WORD `7e` `80`. work RAM BYTE `5d2d(A5)`(`520a2` ADDQ, `5214c` SUBQ).
- [I] `5208a`는 `5d2d(A5)`로 살아 있는 파편 수를 세고, `5206e` palette 표를 `8c` 상위 BYTE로 따라가다 `ffff`에서 지운다. `e5ea0`은 `e5fbe` 흐름의 `7c` frame마다 자식 `e5f32`(`7e` 번째 sprite LONG `e60c6`, palette `80`)를 만들어 아래로 떨어뜨린다. 게임 의미는 미확인이다.

## 의존·경계

- [F] N01 → 기존(모두 routing됨): sound `3af8`, interpreter `49f8c` `49fc6`(반환 C 소비), U14 `16ef0`, stage_event_ops `49a84`, cleanup `8ff4` `43e34`, U02 `8ebe`, fade_card `28ae` `2a00`(JMP), U08 `49290`, U05 `c6a96`, U04 `43ea4`, sprite `16ea4`.
- [F] 다른 단위 → N01: U14 `52014`(`2986` 자식 `5208a`), U07 `e5888` `e5898` `e58a8` `e5910` `e5926` `e5940` `e5956` `e5970` `e598a`(`28ae` 자식). 모두 node callback LONG으로만 넘기며 직접 호출은 없다.
- [F] 경계: 없음. U20b PC는 N01에서 나오지 않는다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 74 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), 소비자 2개의 Unknown 오류, zero-step, 내부 531 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만. bank LONG·bank 자료·fixed ROM 표는 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 소비자 C는 native 분기로 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(진입 6개와 설치 callback, `49fc6` 반환 C 양쪽).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, complete 84 이상(기대 88: +84 85 92 93).

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] `76`(`5208a`) 범위 0..1은 U14 계약의 `49a84` D0=2 결과에서 온 추론이고, `8c`(`e5d72`/`e5d86`) 범위는 U07 부모의 `8e`/`90`에서 온다. C++는 상한 없이 원본과 같은 주소를 읽는다.
3. [U] `e5ce2`의 `49fc6` 반환 C는 쓰이지 않는다(`e5ce8 TST.W`).

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n01/`(`n01blocks.py` block·범위·SHA 계산, `n01dis.py`, `n01route.py` routing 확인, `n01reach.py` 자연 도달; 저장소 밖).
