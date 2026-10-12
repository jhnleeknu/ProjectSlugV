# 객체 callback F4 N03(옛 U22): 디버그 객체 보기 callback `c603a`/`c6218`과 공용 slot 등록 `4b82e` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N03 행(`4b82e..4b8a2` `c603a..c64a0`, callback `c603a` `c6218`, 경계 callee `4ae4a` `c63be` `c63fa`, bank 1, 새 seed 60 61)과 메인 결정 1·2(이름 `objects-n03`, 범위 안 설치 callback 포함)다. 원 범위(`animation-machine-object-callbacks-f4-scope.md`, SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U22 행과 같은 본문이다. 단위 형식과 규약은 U20b 계약(SHA256 `d0aa57cf84335ab0b89f67daab204125e64d80a1400e47d6895c6629e12f3827`)과 U05 계약(SHA256 `77fd4062f3935d0e8b2989ad65bed395f43fa7bd37f33309c7a29fa9f512dafc`, `1ab02` 반환 C)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 JSR 대상, 범위 안의 `MOVE.L #imm,(A6)` callback 진입)로 정한다.
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 실행부 없는 경계다.
- U01~U20b 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc, Z만 바꾸는 `BTST`/`BSET`/`BCLR`/`BCHG`)만인 block과 callee C를 소비하는 block은 FLOW_ONLY다. `ADDQ`/`ADDA` An block은 Unknown이다. checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. N03 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 자료(`200004+w`, `2002b8`)는 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n03`(HEAD `a09e295` = U20b까지 통합, `engine/src/animation_machine.cpp` SHA256 `1969fe0503a244168787336fe8f8fcde23265e10c7f19f10e92b0d81d549e2f0`, routing 규칙 58개)을 참조했다. 동시에 진행하는 N01(`5208a..52156` `e5bb0..e5fbe`, 작업 트리 `metalslug-n01`)의 PC는 N03에서 나오지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n03/n03.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] N03은 **block 시작 113개**다. 코드 4 범위(`4b82e..4b8a2` 11, `c603a..c63b6` 83, `c63be..c644a` 13, `c647e..c64a0` 6), 1,182바이트, 297명령이다. 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx·I/O port 쓰기·bank 변경은 없다. routing 짝수 PC는 591개, 내부 PC는 478개다.
  - 재범위 N03 행의 100과 다르다. 차이 13은 범위 안 JSR 대상 `c63be`(4 block)·`c63fa`(9 block)이다. 재범위는 400 frame 안에 실행되지 않아 경계 callee로 셌다. 이 계약은 결정 3(범위 안 JSR 대상은 block 시작)과 범위 연속성(범위 한가운데 실행부 없는 구멍을 두지 않음)으로 넣는다(결정 1).
  - 범위에서 빼는 곳: `c63b6..c63be`(8바이트 자료 `ff00 ff9c 0200 0200`, `c63a0 LEA c63b6(PC),A0`로 `1ab02`에 넘기는 사각형), `c644a..c647e`(52바이트, ROM 어디에서도 참조하지 않는 함수 `c644a`; 정적 도달 불가), `c64a0..`(자료 표). 셋 다 routing 밖(`unsupported animation machine PC`)이다.
  - 함수: 노드 callback `c603a`(stage event 표 LONG `e9030`이 가리킴), `MOVE.L #c6218,(A6)`로 설치되는 callback `c6218`, 범위 안 helper `c63be` `c63fa` `c647e`, 55곳(`JSR 4b82e.L`, 이 단위 안 `c60a0` 포함)이 부르는 공용 slot 등록 `4b82e`.
- [F] **경계 callee(실행부 없음)**: `4ae4a`(N08 범위, `c6398`; LONG `72(A6)`≠0일 때만). [F] `c6090`이 매번 `72(A6)`=0을 쓰고 N03 안에서 `72`를 바꾸는 곳은 없다. F4 범위 재생(base·RNG+`80`)에서 실행되지 않는다. test는 그 PC에서 멈춤만 확인한다(F4 test 경계 관례).
- [F] **나가는 호출(routing됨)**: cleanup `8ff4`(`c603a` `c614a` `c62e2` `c6308`)·`43e34`(`c61f4` `c634e`), U02 `8ebe`(9곳), interpreter `49f8c`(`c61e6`)·`49fc6`(`c6376`), U01 `4b54e`(`c6380`), U05 `1ab02`(`c63a4`, C 반환), fade_card `2a00`(`JMP`, 자기 삭제).
- [F] **flag**:
  - 블록 경계를 건너는 C 소비 block **1개**: `c63aa BCC.W c63b4`(`1ab02` 반환: U05 `1ab7a` Clear / U01 `1aafc` Set; U20b `849fe`·U05 `b9752`와 같은 소비).
  - `c637c BCC.W c6380`은 분기 대상이 바로 다음 명령이라 C에 관계없이 `c6380`으로 간다. 소비자로 보지 않고 FLOW_ONLY 통과 block으로 둔다(결정 3).
  - known carry 생산 block: 없음. [F] `4b82e`를 부르는 범위 밖 54곳의 다음 명령은 모두 C를 읽지 않는다(`MOVE`/`JSR`/`RTS`/`MOVEA`/`LEA`/`BRA`/`CLR`/`BCLR`/`BTST`/`CMPI`/`JMP`). `c647e` `c63be` `c63fa`의 호출자도 C를 읽지 않는다.
  - block 안에서 만들고 쓰는 flag: `MOVE.B 6d(A6),D0; BPL`(`4b82e`), `CMPA.W #0,A0/A3; BEQ/BNE`(32bit 비교, `4b838` `4b846` `4b87a`), `CMP.B D6,D7; BEQ`(`4b850`), `CMPA.L #10db78,A4; BCS`(무부호 32bit, `4b86a`), `CMPI.W #ffff,…; BNE`(`c6074` `c60a6`), `CMPA.L #0,A1/A2; BNE/BEQ`(`c60f6` `c6116` `c63d8`), `CMPA.L A2,A1; BNE`(`c6132` `c642e`), `CMPI.W #k,D0; BNE`(`c6166`~`c61c2`), `TST.W 76(A6); BNE`(`c61ec` `c6346`), `TST.B 84(A6); BNE`(`c623e`), `SUBQ.W #1,82(A6); BNE`(`c6280`), `SUBQ.W #1,7e(A6); BCC`(borrow, `c6288` `c641a`), `MOVE.L 72(A6),D0; BEQ`(`c6386`), `MOVE.W D0,D1; BNE`(`c6414`), `MOVE.W (A1),D2; BPL`(`c6482`), `CMP.W D1,D2; BEQ`(`c648c`), BTST 뒤 Bcc(Z: `c6218`~`c6278`, `c62a2`~`c6336`).
- [F] 읽는 자료(모두 live bus):
  - fixed ROM 표 `c64a0`(16바이트 record 94개, 첫 WORD `ffff`인 `c6a80`에서 끝; 1,520바이트 SHA256 `fabcf95ddca2b38c803d7b173fe57109a320f93cd912bd5e261a0257e22ff12c`). record: `+0` WORD(`ffff`=끝), `+2` WORD(bank window offset), `+4` WORD, `+6` WORD(팔레트 번호 기준), `+8` LONG(`(WORD key, WORD 값)` 목록 주소, `c6efa..c82fe`), `+c` LONG 0. index 상한은 원본이 `ffff` 종료로만 정하므로 live bus가 정한다.
  - bank window: `c60c4`는 `MOVE.L #200004,D2; ADD.W 2(A0),D2`(하위 WORD만 더함, 상위 WORD `0020` 유지)의 주소에서 LONG을 읽어 `22(A6)`에 둔다. `c63be`/`c63fa`는 `MOVEA.L #200004,A1; ADDA.W 2(A0,D0.W),A1`(부호확장)의 LONG을 읽는다. 두 주소 계산은 WORD ≥ `8000`에서 다르다(`200004+fff0`은 `c60c4`에서 `20fff4`, `c63be`에서 `1ffff4`). `c636a`는 bank LONG `2002b8`과 그 값+`14`의 LONG을 읽는다.
  - 위 LONG이 가리키는 animation 포인터 목록(`(A3,D1.W)`, `4(A3,D1.W)`, `(A0,D1.W)`, `4(A0,D1.W)`, LONG, 0=끝)과 `+8` 목록(`(A1)` WORD, `2(A1)` WORD, 음수=끝).
  - 주소만 넘기는 상수: `c63b6`(→`1ab02` A0).
  - work RAM: node WORD `20` `2e` `32` `42` `46` `76` `78` `7a` `7c` `7e` `80` `82` `86`, LONG `22` `56` `72` `7a`, BYTE `12` `13` `14` `19` `5e` `61` `6d` `84`; 입력 BYTE `104cac`(`-3354(A5)`), `104cb0`(`-3350(A5)`), `104cb2`(`-334e(A5)`); BYTE `10d67e`/`10d67f`(`567e/567f(A5)`, 쓰기); slot 표 `10daf8..10db77`(`5af8(A5)`, 8바이트 16개; `4b86a`의 끝 비교는 절대 상수 `10db78`); slot이 가리키는 다른 node의 BYTE `6d`.
- [F] 자연 도달(재범위 scratch 재생, TB 기준): base와 RNG 초기화+응답 `80` 변형 모두 `c603a` 계열은 seed 60·61만 닿는다. `4b82e` `4b838` `4b878`은 seed 26 27 38 39 76 77 98 99 104 105 116 117(RNG)과 116 117(base)도 닿고 `4b840` `4b85e`는 RNG seed 26·27만 닿는다. TB 시작 54개다. 나머지 59 시작(`4b846` `4b850` `4b86a` `4b87a` `4b88e` `4b89c`, `c63be`·`c63fa` 계열 13, 입력 bit가 1인 길, `c6398` 등)은 TB 안 fall-through이거나 자연 미도달이며 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] seed 60·61의 기준 첫 미연결 callback은 `c603a`(frame 0)다. 재범위 재생에서 두 seed가 실행하는 routing 밖 TB는 N03 범위 밖에는 기존 묶인 분기 내부 목록(재범위 문서 측정 방법의 15개)뿐이다. [I] N03으로 두 seed가 base·RNG 모두 완주할 것으로 본다(검증에서 확인).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 113(재범위 N03 행 100과 차이 13).** 범위 안 JSR 대상 `c63be` `c63fa`(입력 bit 5로만 가는 helper)를 넣는다. 빼면 `c63be..c644a`가 범위 한가운데 경계 구멍이 되고 13 block짜리 별도 단위가 남는다. `c63b6..c63be` 자료와 미참조 `c644a..c647e`는 넣지 않는다.
2. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n03.cpp`의 `animation_objects_n03_block`. 오류는 `unsupported animation objects n03 PC`(내부 PC), `objects n03 caller requires known carry`(소비 1 block `c63aa`). 메인 지시와 같다.
3. **`c637c BCC.W c6380`.** 분기 대상=fall-through라 C를 쓰지 않는다. FLOW_ONLY 통과(오류 없음)로 둔다. C++는 무조건 `c6380`으로 간다.
4. **bank·fixed 자료.** bank LONG(`200004+w`, `2002b8`과 이어지는 LONG)과 fixed 표 `c64a0`·목록은 live bus로 읽는다(U18 결정 6, U20b 결정 4와 같음). test는 합성 bank·fixed 바이트를 쓴다(ROM 자료를 test에 넣지 않음).
5. **무효화 탐침.** [F] `engine/tests/animation_machine_buffer_cue_test.cpp`의 `outside[]`에 `0x4b82e`(routing 밖 기대)가 있다. N03이 `4b82e`를 routing하므로 RAM 탐침 `0x10fe50`으로 바꾼다(F4 test 경계 관례). [F] `tools/verify_animation_machine_buffer_cue.py`(824행, `0x4b82e` `0x4b830`을 `unsupported animation machine PC` 기대)도 무효가 된다. `make test`에 들지 않는 검증 도구라 이 단위에서 고치지 않고 메인에 넘긴다. 그 밖 `engine/tests`·`tools`·`engine/src`에서 N03 범위 PC를 rollback·outside 탐침으로 쓰는 곳은 없다(scratch `probes.py`; u13 test의 일치 2건은 FNV digest 값).

## 원본 바이트 근거

[F] 코드 4 범위 합계 1,182바이트. 범위 순서로 이어 붙인 SHA256 `606f0ec4ddf8315d25f6853dd25256d60ab83cee20452adab246ddb2d29cc6c5`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `4b82e..4b8a2` | 116 | `a5485206bfa964190ee9fa51e197cac38d3bc22e5b64ce291102e06b2687a940` | 공용 slot 등록 `4b82e` |
| `c603a..c63b6` | 892 | `29b6964fbd20d31ffc67001e2e1ac9da637a1ca0ab23a1bf287f1039b374705a` | callback `c603a`, 설치 callback `c6218` |
| `c63be..c644a` | 140 | `ec9e94a5b5af880cf56baf7686e4d41ca0fee5e09e7c9745f7e6f7a4e16307f6` | helper `c63be` `c63fa` |
| `c647e..c64a0` | 34 | `ec0a3abf70e1a66e5cdabb389603c5bf982402f1f75386ab2bd193904e4b7d1d` | helper `c647e` |

- [F] 범위 밖 이웃: `4b784..4b82e`(buffer cue U7, 끝 `RTS`), `4b8a2..`(다른 함수 `4b8a2`, 원 범위 U38/N33 쪽), `c6012..c603a`(LONG 표 `000d22e6`…), `c63b6..c63be`(자료), `c644a..c647e`(미참조 함수), `c64a0..c6a90`(표 `c64a0`), `c6a90..`(U01 `c6a90`).
- [F] 참조: `c603a`은 stage event 표 LONG `e9030`(앞뒤 LONG `c5fd8` `c6a90` `eb7b6`). `c6218`은 `c6210 MOVE.L #c6218,(A6)`만 설치한다. `4b82e`은 `JSR 4b82e.L` 55곳(`38bbc` `3b5f4` `3d290` `3e072` `7a3fe`…`c60a0` `eb754` `eb76c`). `c63be`은 `c6296` `c6428`(JSR d16(PC)), `c63fa`은 `c629a`(JSR d16(PC))와 `c642c`(`BRA.B`), `c647e`은 `c6150`(JSR d16(PC))만 부른다. `c644a`·`c63b6` 진입 참조는 없다.

## block 목록과 실행 의미

[F] 113 block. 각 줄은 block 안 명령 전체다. "(→x)"는 fall-through다. d16(An)은 부호확장한다. `.W`/`.B` 연산은 나머지 bit를 보존한다. `(An,Dn.W)`의 index WORD는 부호확장한다. `CMPA.W #0,An`은 32bit 비교다. `MOVEM.L D0-D7/A0-A6,-(A7)`은 60바이트(낮은 주소부터 D0…A6)를 쌓고 `MOVEM.L (A7)+,D0-D7/A0-A6`은 같은 순서로 15 LONG을 되돌린다(A5·A6 포함).

**공용 slot 등록 `4b82e` 11**
- `4b82e`: `MOVEQ #0,D0; MOVE.B 6d(A6),D0; BPL.W 4b87a`
- `4b838`: `CMPA.W #0,A0; BEQ.W 4b878`
- `4b840`: `LEA 5af8(A5),A4; MOVEQ #0,D7` (→`4b846`)
- `4b846`: `MOVEA.L (A4),A3; CMPA.W #0,A3; BEQ.W 4b85e`
- `4b850`: `MOVE.B 6d(A3),D6; ANDI.W #f,D6; CMP.B D6,D7; BEQ.W 4b86a`
- `4b85e`: `MOVE.B D7,6d(A6); MOVE.L A6,(A4); MOVE.L A0,4(A4); RTS`
- `4b86a`: `ADDQ.W #1,D7; LEA 8(A4),A4; CMPA.L #10db78,A4; BCS.B 4b846` (→`4b878`)
- `4b878`: `RTS`
- `4b87a`: `ANDI.W #f,D0; LSL.W #3,D0; LEA 5af8(A5),A4; ADDA.W D0,A4; CMPA.W #0,A0; BNE.W 4b89c`
- `4b88e`: `MOVE.L A0,(A4); MOVE.L A0,4(A4); MOVE.B #ff,6d(A6); RTS`
- `4b89c`: `MOVE.L A0,4(A4); RTS`

**callback `c603a` 35**
- `c603a`: `JSR 8ff4.L` (cleanup)
- `c6040`: `MOVE.W #c49,D0; MOVE.B #0,D1; JSR 8ebe.L` (U02)
- `c604e`: `MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); MOVE.W #0,7e(A6); MOVE.W #1,82(A6); MOVE.W 76(A6),78(A6); LEA c64a0(PC),A0; MOVE.W 7e(A6),D0` (→`c6074`)
- `c6074`: `MOVE.W D0,D1; LSL.W #4,D1; CMPI.W #ffff,(A0,D1.W); BNE.W c608c` / `c6082`: `SUBQ.W #1,D0; MOVE.W D0,80(A6); BRA.W c6090` / `c608c`: `ADDQ.W #1,D0; BRA.B c6074`
- `c6090`: `MOVE.L #0,72(A6); CLR.L 56(A6); LEA 0.W,A0; JSR 4b82e.L`
- `c60a6`: `LEA c64a0(PC),A0; MOVE.W 7e(A6),D0; LSL.W #4,D0; ADDA.W D0,A0; MOVE.W (A0),D1; CMPI.W #ffff,D1; BNE.W c60c4` / `c60bc`: `MOVE.W #0,7e(A6); BRA.B c60a6`
- `c60c4`: `MOVE.W D1,7a(A6); MOVE.L #200004,D2; ADD.W 2(A0),D2; MOVE.L D2,7a(A6); MOVE.W 4(A0),D0; MOVE.W D0,7a(A6); MOVE.W D1,20(A6); MOVEA.L D2,A1; MOVE.L (A1),22(A6); MOVEA.L 22(A6),A3; MOVE.W 82(A6),D0; MOVE.W 82(A6),7a(A6)` (bank 자료; →`c60f6`)
- `c60f6`: `MOVE.W D0,D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L (A3,D1.W),A1; CMPA.L #0,A1; BNE.W c6116` / `c610a`: `MOVE.W #1,82(A6); ADDQ.W #1,7e(A6); BRA.B c60a6`
- `c6116`: `MOVEA.L 4(A3,D1.W),A2; CMPA.L #0,A2; BNE.W c6132` / `c6124`: `MOVE.W #1,82(A6); ADDQ.W #1,7e(A6); BRA.W c60a6`
- `c6132`: `CMPA.L A2,A1; BNE.W c613c` / `c6138`: `ADDQ.W #1,D0; BRA.B c60f6`
- `c613c`: `MOVE.W D0,82(A6); MOVE.W 82(A6),7a(A6); MOVEM.L D0-D7/A0-A6,-(A7); JSR 8ff4.L`
- `c6150`: `JSR c647e(PC)`
- `c6154`: `ADD.W 6(A0),D0; MOVE.W D0,86(A6); MOVE.B #0,D1; JSR 8ebe.L`
- `c6166`: `MOVE.W 6(A0),D0; CMPI.W #75,D0; BNE.W c6180` / `c6172`: `MOVE.W #c76,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `c6180`: `CMPI.W #87,D0; BNE.W c6196` / `c6188`: `MOVE.W #c88,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `c6196`: `CMPI.W #36,D0; BNE.W c61ac` / `c619e`: `MOVE.W #c39,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `c61ac`: `CMPI.W #3e,D0; BNE.W c61c2` / `c61b4`: `MOVE.W #c3f,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `c61c2`: `CMPI.W #d6,D0; BNE.W c61d8` / `c61ca`: `MOVE.W #ce4,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `c61d8`: `MOVEM.L (A7)+,D0-D7/A0-A6; MOVE.B 19(A6),14(A6); MOVE.W #100,D0; JSR 49f8c.L` (interpreter)
- `c61ec`: `TST.W 76(A6); BNE.W c61fe` / `c61f4`: `JSR 43e34.L` (cleanup) / `c61fa`: `BRA.W c6210`
- `c61fe`: `MOVE.W 2e(A6),42(A6); MOVE.W 32(A6),46(A6); ADDI.W #100,46(A6)` (→`c6210`)
- `c6210`: `MOVE.L #c6218,(A6); RTS`

(`c6166`~`c61ca`의 `CMPI.W`는 앞 `JSR 8ebe` 뒤의 live D0를 비교한다. `c6180` 이후 비교는 앞 `8ebe`가 D0를 바꾸면 바뀐 값을 쓴다.)

**설치 callback `c6218` 48**
- `c6218`: `MOVE.B #90,567e(A5); MOVE.B #ff,567f(A5); MOVE.B -3354(A5),D0; BTST.B #4,D0; BEQ.W c623e`
- `c6230`: `BTST.B #5,D0; BEQ.W c623e` / `c6238`: `BCHG.B #0,84(A6)` (→`c623e`)
- `c623e`: `TST.B 84(A6); BNE.W c62a2`
- `c6246`: `BTST.B #7,D0; BEQ.W c6252` / `c624e`: `BRA.W c6090`
- `c6252`: `BTST.B #6,D0; BEQ.W c6268` / `c625a`: `MOVE.W #1,82(A6); ADDQ.W #1,7e(A6); BRA.W c6090`
- `c6268`: `BTST.B #4,D0; BEQ.W c6278` / `c6270`: `ADDQ.W #1,82(A6); BRA.W c6090`
- `c6278`: `BTST.B #5,D0; BEQ.W c62a2`
- `c6280`: `SUBQ.W #1,82(A6); BNE.W c629a` / `c6288`: `SUBQ.W #1,7e(A6); BCC.W c6296` / `c6290`: `MOVE.W 80(A6),7e(A6)` (→`c6296`)
- `c6296`: `JSR c63be(PC)` / `c629a`: `JSR c63fa(PC)` / `c629e`: `BRA.W c6090`
- `c62a2`: `MOVE.B -3350(A5),D0; BTST.B #0,D0; BEQ.W c62b2` / `c62ae`: `ADDQ.W #1,32(A6)` (→`c62b2`)
- `c62b2`: `BTST.B #1,D0; BEQ.W c62be` / `c62ba`: `SUBQ.W #1,32(A6)` (→`c62be`)
- `c62be`: `BTST.B #3,D0; BEQ.W c62ca` / `c62c6`: `ADDQ.W #1,2e(A6)` (→`c62ca`)
- `c62ca`: `BTST.B #2,D0; BEQ.W c62d6` / `c62d2`: `SUBQ.W #1,2e(A6)` (→`c62d6`)
- `c62d6`: `MOVE.B -334e(A5),D0; BTST.B #4,D0; BEQ.W c62fc` / `c62e2`: `JSR 8ff4.L` / `c62e8`: `MOVE.W 86(A6),D0; SUBQ.W #1,D0; MOVE.W D0,86(A6); MOVE.B #0,D1; JSR 8ebe.L`
- `c62fc`: `MOVE.B -334e(A5),D0; BTST.B #5,D0; BEQ.W c6322` / `c6308`: `JSR 8ff4.L` / `c630e`: `MOVE.W 86(A6),D0; ADDQ.W #1,D0; MOVE.W D0,86(A6); MOVE.B #0,D1; JSR 8ebe.L`
- `c6322`: `MOVE.B -334e(A5),D0; BTST.B #6,D0; BEQ.W c6336` / `c632e`: `SUBQ.B #1,12(A6); SUBQ.B #1,13(A6)` (→`c6336`)
- `c6336`: `BTST.B #7,D0; BEQ.W c6346` / `c633e`: `ADDQ.B #1,12(A6); ADDQ.B #1,13(A6)` (→`c6346`)
- `c6346`: `TST.W 76(A6); BNE.W c6358` / `c634e`: `JSR 43e34.L` / `c6354`: `BRA.W c636a`
- `c6358`: `MOVE.W 2e(A6),42(A6); MOVE.W 32(A6),46(A6); ADDI.W #100,46(A6)` (→`c636a`)
- `c636a`: `MOVEA.L 2002b8.L,A0; MOVE.L 14(A0),7a(A6); JSR 49fc6.L` (bank 자료; interpreter)
- `c637c`: `BCC.W c6380` (대상=다음 명령; 통과) (→`c6380`)
- `c6380`: `JSR 4b54e.L` (U01)
- `c6386`: `CLR.B 5e(A6); BCLR.B #7,61(A6); MOVE.L 72(A6),D0; BEQ.W c63a0` / `c6398`: `MOVEA.L D0,A0; JSR 4ae4a.L` (경계, N08)
- `c63a0`: `LEA c63b6(PC),A0; JSR 1ab02.L` (U05)
- `c63aa`: `BCC.W c63b4` (carry 소비) / `c63ae`: `JMP 2a00.L` (fade_card 자기 삭제) / `c63b4`: `RTS`

(`c6218`의 D0는 `MOVE.B`라 상위 24bit를 보존한다. `c6246` `c6252` `c6268` `c6278`은 `c6218`에서 읽은 D0의 bit를 쓴다. 입력 bit 4·5가 모두 1이면 `84(A6)` bit 0이 뒤집힌다.)

**helper `c63be` 4 / `c63fa` 9 / `c647e` 6**
- `c63be`: `LEA c64a0(PC),A0; MOVE.W 7e(A6),D0; LSL.W #4,D0; MOVEA.L #200004,A1; ADDA.W 2(A0,D0.W),A1; MOVEA.L (A1),A0; MOVE.W #1,D0` (bank 자료; →`c63d8`)
- `c63d8`: `MOVE.W D0,D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L (A0,D1.W),A1; CMPA.L #0,A1; BEQ.W c63f0` / `c63ec`: `ADDQ.W #1,D0; BRA.B c63d8`
- `c63f0`: `SUBQ.W #1,D0; SUBQ.W #1,D0; MOVE.W D0,82(A6); RTS`
- `c63fa`: `c63be`의 앞 6명령과 같고 `MOVE.W 82(A6),D0` (→`c6414`)
- `c6414`: `MOVE.W D0,D1; BNE.W c642e` / `c641a`: `SUBQ.W #1,7e(A6); BCC.W c6428` / `c6422`: `MOVE.W 80(A6),7e(A6)` (→`c6428`) / `c6428`: `JSR c63be(PC)` / `c642c`: `BRA.B c63fa`
- `c642e`: `ADD.W D1,D1; ADD.W D1,D1; MOVEA.L (A0,D1.W),A1; MOVEA.L 4(A0,D1.W),A2; CMPA.L A2,A1; BNE.W c6444` / `c6440`: `SUBQ.W #1,D0; BRA.B c6414` / `c6444`: `MOVE.W D0,82(A6); RTS`
- `c647e`: `MOVEA.L 8(A0),A1` (→`c6482`)
- `c6482`: `MOVE.W (A1),D2; BPL.W c648c` / `c6488`: `MOVEQ #0,D0; RTS`
- `c648c`: `MOVE.W 82(A6),D1; CMP.W D1,D2; BEQ.W c649a` / `c6496`: `ADDQ.L #4,A1; BRA.B c6482` / `c649a`: `MOVE.W 2(A1),D0; RTS`

(수: 11 + 35 + 48 + 4 + 9 + 6 = 113. 범위별로는 `4b82e..4b8a2` 11, `c603a..c63b6` 83, `c63be..c644a` 13, `c647e..c64a0` 6.)

## 구현 범위와 규약

- routing 4 범위: `4b82e..4b8a2`, `c603a..c63b6`, `c63be..c644a`, `c647e..c64a0`. 짝수 PC 591개 중 block 시작 113, 내부 478. 내부 PC 직접 진입은 `unsupported animation objects n03 PC`다.
- **FLOW_ONLY 33개**(C 보존): `4b878` `c603a` `c6150` `c61f4` `c61fa` `c6230` `c6238` `c6246` `c624e` `c6252` `c6268` `c6278` `c6296` `c629a` `c629e` `c62b2` `c62be` `c62ca` `c62e2` `c6308` `c6336` `c634e` `c6354` `c637c` `c6380` `c6398` `c63a0` `c63aa` `c63ae` `c63b4` `c6428` `c642c` `c647e`.
- **known carry 생산**: 없음. 그 밖 80개는 Unknown(`MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`CMPA`/`ADD`/`ADDI`/`ADDQ`/`SUBQ`/`ANDI`/`LSL` block, `MOVE.L #imm,(A6)` block, `ADDQ.L #4,A1` block `c6496`, MOVEM 뒤 `MOVE.B` block `c61d8`).
- **소비자 1개** `c63aa`(결정 2). Unknown이면 `objects n03 caller requires known carry`(상태 보존).
- 스택: JSR 복귀 LONG, `c613c` MOVEM 60바이트 쌓기, `c61d8` 60바이트 되돌리기. I/O port 쓰기·bank 변경 없음. 홀수 주소 WORD/LONG(예: 홀수 A0/A3/A1 표 주소), work RAM 밖 쓰기, 미해결 ROM/bank 읽기는 기존 checked 오류다.
- 반복(`c6074`/`c608c`, `c60a6`/`c60bc`, `c60f6`/`c6138`, `c63d8`/`c63ec`, `c6414`/`c6440`, `c6482`/`c6496`, `4b846`/`4b86a`)은 block 단위로 실행한다. 끝나지 않는 자료(예: `c64a0` 첫 record가 `ffff`)는 기존 1,000,000 block 상한 오류다.

## 의존·경계

- [F] N03 → 기존: cleanup `8ff4` `43e34`, U02 `8ebe`, interpreter `49f8c` `49fc6`, U01 `4b54e`, U05 `1ab02`, fade_card `2a00`.
- [F] N03 → 경계: `4ae4a`(N08).
- [F] 다른 단위 → N03: stage event 표 `e9030`(`c603a`), `JSR 4b82e.L` 54곳(범위 밖, 다른 객체 callback).

## 자연 시작 상태(읽기 전용 기록)

- [F] 기준 C++ 차분(이 작업 트리 `a09e295`, 현재 `tools/verify_animation_machine_scheduler_f4.py`·`_rng_f4.py`를 scratch 출력으로 실행): base 일치 pass 12,178·node 94,840, 불일치 0, 자연 완주 111 seed(seed 60·61의 첫 미연결 callback `c603a`, frame 0). RNG 초기화 400 frame: 일치 pass 34,404·node 248,027, 불일치 0, complete 86(SHA256 `8414d3ac3bd75db94c88eb5badcb20ac0d5ea9c5b048a7059ea2ef6ca5ca8c8e`).

- [F] 작업자 scratch 측정(구현 후, 같은 도구): base 일치 pass 12,418·node 96,490, 불일치 0, 자연 완주 113(새 완주 60 61, 회귀 0). RNG 초기화 400 frame: 일치 pass 35,204·node 253,037, 불일치 0, complete 88(새 complete 60 61, 잃은 것 0; SHA256 `ff80254e3e682b54433c2f5d3449107104da058e59b865cfd3c4d9dc0df0c9cd`).
- [F] 실제 ROM 차분(scratch `realrom/real.py`, 시드 1·2·3 각 1,000 case, bank `200000`/`300000`): 불일치 0, 113/113 시작 도달, 소비자 `c63aa`가 실제 `1ab02` 뒤에 실행된 경우 695, 경계 `4ae4a` 멈춤 244.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 113 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류, zero-step, 내부 478 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 범위 밖 이웃(`c63b6` `c644a` `4b8a2` `c64a0`)은 `unsupported animation machine PC`, 경계 `4ae4a`는 멈춤만, 소비자 `c63aa` Unknown 오류, 소비자 C는 실제 생산자 `1ab02`를 지나는 실제 ROM 차분의 native 분기로 확인. 자연에 없는 길은 typed fixture(Unicorn, work RAM 입력과 합성 bank·fixed 바이트)로 비교한다.
- 실제 ROM 차분: `c603a` `c6218` `4b82e`과 모든 시작을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다(bank `200000`/`300000`).
- 차분(F2 프레임 패스, 142 seed): 불일치 0, 회귀 0, seed 60·61 완주. RNG 초기화 400 frame 차분: 불일치 0, seed 60·61 complete.

## 미확인·범위 밖

1. [I] `c603a`/`c6218`은 디버그 객체 보기로 보인다. `7e`=표 `c64a0` record index, `82`=그 record의 animation 목록 index, `86`=팔레트 번호(`+6`+`+8` 목록 값), `2e`/`32`=화면 좌표, 입력 BYTE `104cac`(bit 4·5 동시: 모드 전환, bit 7/6/4/5: 재시작·다음 record·다음/이전 animation), `104cb0`(bit 0~3: 좌표), `104cb2`(bit 4·5: 팔레트 −/+, bit 6·7: `12`/`13` −/+)를 쓴다. 게임 의미와 입력 BYTE의 생산자는 미확인이다.
2. [I] `4b82e`는 node를 slot 표 `10daf8`(16칸, buffer cue U7과 같은 표)에 등록·갱신한다(`6d(A6)` bit 7=미등록). [U] slot 표 소비자 의미.
3. [U] `c644a`(미참조)의 목적. `4ae4a` 본문은 N08이다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n03/`(`n03.py` block·범위·SHA 계산, `n03dis.py` `hroute.py` `owner.py` `refs.py` `probes.py`, `fp/` 기준·새 프레임 패스 차분; 저장소 밖).
