# 객체 callback F4 U04: `d72f2` 계열·지연 sprite 정렬 `ce02`·C5 `43ea4` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U04 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`)과 U03 계약(`animation-machine-objects-u03-contract.md`, SHA256 `040ed358872ae45fbb5aec13a9e53eade3817c6a5de648b5584ac8095605d21e`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR 복귀점, `MOVE.L #imm,(A6)` 설치 callback, `MOVEA.L #imm,A0`+`JSR 28ae` 자식 callback)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee는 실행부 없는 경계다.
- U01 수용 관례: `MOVE.x`는 C를 지운다(필요한 소비자가 있을 때만 known 생산으로 둔다), `ADDQ`/`ADDA` block은 Unknown, checked 오류는 경계에서 낸다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. 코드와 자료는 모두 fixed `<100000`에 있으므로 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u04`(HEAD `4b36ff8`, U01 WIP)를 참조했다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u04/u04.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] U04는 함수 3개, **block 시작 69개**다. 코드 3 범위 `ce02..ce62` `43ea4..43ea8` `d72f2..d75ce`, 832바이트, 211명령이며 미해독·TRAP·묶인 분기·포트 쓰기·계산 PC는 없다. routing 짝수 PC는 416개, 내부 PC는 347개다.
- [F] **범위 문서 70과의 차이(−1)**. scratch에서 범위 문서 함수 본문(`f4scope/all.pkl`)의 같은 주소 범위 leader 70개와 직접 비교했다.
  - −2: `16ede` `16eee`는 함수 `16ed2`(`MOVE.W d3e(A5),D0; CMP.W d46(A5),D0; BGE 16ee8; BSET/BCLR #2,15(A6); RTS`)의 꼬리다(같은 꼬리의 `16ee8`은 범위 문서도 세지 않았다). 기존 sprite 실행부(`animation_machine_sprite.cpp` `case 0x16ed2`)가 이 함수 전체를 한 block으로 실행하고 RTS까지 끝낸다. 그래서 이 PC들로 넘어가는 실행은 없다. U04는 이 셋을 routing하지 않는다(결정 1).
  - +1: `d72fe`는 `47e30`이 자식 callback으로 설치하는 별도 진입이다. `d72f2`는 `BRA d7302`로 이 자리를 건너뛰므로 `d72f2`에서 시작한 범위 스크립트 closure에 없었다. 자연 seed에서는 실행되지 않는다.
- [F] 함수 3개.
  - `ce02`(지연 sprite 큐 정렬, 10 block). 기존 분석 `sprite-sort.md`(C++ `sort_sprite_queue`)와 같은 함수다. 입력 `D0.W`=새 태그, A5=`108000`. 출력 RAM `109150`(태그), `108d38`(링 쓰기 index), `10914e`(=0), `108b34..` 링, `107f34+`레코드 첫 WORD, 지연 목록 `108f4e..` 교환.
  - `43ea4`(C5, 1 block): `LEA 2e(A6),A0` 뒤 기존 scene update block `43ea8`(속도 가산, `BRA 43e38` cleanup)로 fall-through한다.
  - node callback `d72f2`/`d72fe`(58 block): 설치 callback `d7346` `d7396` `d73b0` `d73c4`, 자식 callback `d73de`(설치 `d7424`).
- [F] 진입 근거: `d72f2`는 class callback 표 `e8f24`(LONG `000d72f2`), `d72fe`는 `47e30 MOVEA.L #d72fe,A0; MOVE.W #14,D0; JSR 28ae`(F1 area clear 실행부, `AC_CHILD_SOUND`)의 자식 callback, `d73de`는 `d7352 MOVEA.L #d73de,A0; JSR 28ae`의 자식 callback이다. `ce02`는 ROM 안 `JSR ce02.L` 74곳 + `d73d8 JMP ce02.L`, `43ea4`는 `JSR 43ea4.L` 다수의 공용 진입이다(`f4u01/callers.py`).
- [F] 기존 실행부로 나가는 출구: sound `3af8`, fade_card `28ae`(객체 생성)·`2a00`(자기 삭제), cleanup `287e`, sprite `16ed2`·`16ea4`, hud `8cda`, scene update `43ea8`(→cleanup `43e38`).
- [F] **경계 callee(U04 작업 트리 기준) 1**: `8ebe`(C1 palette 참조, U02 범위). U01~U03이 합쳐진 뒤에는 U02가 실행하므로 범위 문서의 "경계 callee 0"과 같다(결정 4).
- 자연 seed(범위 scratch 재생 `f4scope/dyn`, TB 시작 기준): `d72f2` 4회, `d7346` 104, `d7396` 188, `d73b0` 48, `d73de` 56, `d7424` 4,032회 node 실행으로 seed 24·25·34·35가 U04 block을 지난다. `ce02`는 이 밖에 미연결 callback 다수(`59ed6` `bdd8a` `a60c8` `5e0c0` `b99be` `9bbf8` `38c36` 등, seed 16·17·28~33·42·43·56·57·116·117)가 부른다. 69 block 중 55개가 자연 도달한다. 미도달 14개(fixture 필요): `d72fe` `d730a` `d731a` `d73b8` `d73c4` `d73ca` `d73ce` `d747c` `d748c` `d7492` `d74a2` `d74a8` `d74ce` `d74d0`.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **`16ede..16eee` 제외(70→69).** [F] 기존 sprite 실행부 `16ed2` block이 함수 끝(RTS)까지 실행한다(`D0.W`=WORD `d3e(A5)`, 부호 비교 `<`이면 `15(A6)` bit2 set, 아니면 clear, `am_return`). 권고(선택 A): U04는 routing하지 않는다. 이 세 PC 직접 진입은 지금처럼 `unsupported animation machine PC`다. 선택 B(비권고): U04에 세 block을 따로 routing한다. 의미가 sprite 실행부와 중복되고, 실행 경로에서 닿지 않는다.
2. **`d73ca BNE`가 `287e`의 Z를 소비한다(새 유형: callee 반환 Z).** [F] `d73c4 JSR 287e`의 `287e`는 `MOVEA.L 8(A6),A0; MOVE.W 10(A6),D0; CMP.W 10(A0),D0; RTS`이다. 기존 cleanup 실행부는 이 C만 known으로 남긴다(`29c4 BCS` 소비자용). `d73ca`는 Z를 쓴다. [F] RTS는 A0, D0, `10(A0)`의 WORD를 바꾸지 않는다. 그래서 권고(선택 A): `d73ca` block이 live `A0`·`D0.W`로 Z=(`D0.W`=WORD `10(A0)`)를 다시 계산한다. `287e` 복귀 직후라면 원본 Z와 같다. 직접 진입이면 live 레지스터·RAM의 결정적 재계산이다. 선택 B: `d73ca`를 `287e` 복귀 block에 묶는다. 기존 cleanup 실행부를 바꿔야 하므로 비권고다.
3. **carry 분류.** [F] U04 안의 C 소비는 모두 같은 block 안의 `SUBQ`/`CMPI`/`CMP` 뒤 `BCC`/`BCS`다(`d7302` `d7310` `d7346` `d747c` `d7492` `ce32`). block 사이 C 소비자와 known 생산 block은 없다. [F] 호출자 쪽: `ce02` 호출 뒤 명령은 `JSR 49fc6`/`JSR 166bc`/`BTST`/`RTS`이고, `43ea4` 호출 뒤 명령은 `JSR 49fc6`/`BSR 2b418`/`MOVE`/`SUBQ`다. U04가 돌려주는 C를 직접 소비하지 않는다([I] 나열하지 않은 호출자가 더 있을 수 있다). 권고: FLOW_ONLY는 CCR을 바꾸지 않는 15 block(`ce44` BRA, `ce60` RTS, `43ea4` LEA, `d72fe` LEA, `d730a` `d731a` `d73ce` `d748c` `d74a2` JMP, `d73c4` `d7424` `d74d6` JSR, `d73ca` BNE, `d7504` `d75cc` RTS)이다. 나머지 54 block은 Unknown이다(`MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPA`/`ADD`/`ADDQ`/`SUB`/`SUBQ`/`SUBI`/`NEG`/`NOT`/`ANDI`/`ASR`/`LSL`/`SWAP`/`MULS`/`MULU`, `BSET`+`MOVE` 묶음 포함). `objects u04 caller requires known carry`는 이름만 예약한다(U03과 같음).
4. **`8ebe` 경계.** [F] U04 작업 트리(U01까지)에서는 `d73de`/`d73ec`의 `JSR 8ebe`가 실행부 없는 경계(`unsupported animation machine PC`, stop이면 직전 상태로 멈춤)다. 자연 seed 24·25는 U02와 합친 뒤에만 완주를 기대한다. 검증은 U04 단독과 U01+U02+U03+U04 합본 둘 다 기록한다.
5. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u04.cpp`의 `animation_objects_u04_block`. 오류는 `unsupported animation objects u04 PC`(내부 PC), `objects u04 caller requires known carry`(예약).
6. **무효화되는 기존 탐침.** [F] `engine/tests/*.cpp`와 `tools/*.py`의 정수 리터럴 중 U04 범위(`ce02..ce62` `43ea4..43ea8` `d72f2..d75ce`) 안의 값은 실행부 없음 경계로 쓰이지 않는다. 걸리는 것은 `ce02`/`43ea4`를 범위 상한·Unicorn 호출 주소로 쓰는 inventory/observe/verify 도구(`inventory_stage_buffer_frame.py` `inventory_stage_cue_frame.py` `inventory_scene_coordinates.py` `inventory_stage_spatial_frame.py` `observe_*` `verify_main_prelude*.py` `verify_sprite_prepare_*.py`)와 `animation_machine.cpp` sprite routing 상한 `ce02`(배타)다. 모두 routing 판정과 무관하다. `observe_animation_machine_activation.py`의 `16ede` `16ee8` `16eee` 경계는 결정 1(선택 A)이면 그대로다. 대체 탐침은 필요 없다(대체가 필요해지면 어떤 `docs/analysis` 문서에도 없는 `5f0c0`부터 쓴다).

## 원본 바이트 근거

[F] 코드 3 범위 합계 832바이트. 이어 붙인 SHA256 `1ee45caa77305eab9a3acfa81311f0b12bf013cff6cd59df7e59747433d833eb`.

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `ce02..ce62` | `3e2d11503b4011503c2d114e6700005041edff3443ed0b343a2d0d3845ed0f4e47f26000302332300000b5cb67000016342336302000b2436500000832033680300260e631870000338050005445024501fe554666ca3b450d383b46114e4e75` |
| `43ea4..43ea8` | `41ee002e` |
| `d72f2..d75ce` | `426e001e41faff826000000641faffb6536e0076640000084ef900002a000c6e00050076650000084ef900002a00302e0076c1fc000c41f000002d58007e2d58007820184eb900003af8426e007c2cbc000d7346536e007c64000088546e007c207c000d73de303c00004eb9000028ae316e001e001e216e00780078216e007e007e526e001e206e007841e8000a2d4800784a506a00004c3d7c0030007c2cbc000d7396536e007c660000381d7c000100633d7c0020007c2cbc000d73b0536e007c6600001e1d7c000200632cbc000d73c44eb90000287e660000084ef900002a00303cffff4ef90000ce02303c03aa123c00014eb900008ebe303c03be123c00014eb900008ebe08ee000600153d7c0000002e3d7c021000323d7c000000363d7cfff0003a3d7c000100822cbc000d74244eb900016ed2206e000c0c280002006367000046206e0078700072003028000632280008906e002e4840e68090ae00366b0000045280e280d1ae0036926e00324841e68192ae003a6b0000045281e281d3ae003a6000005c302e002e064000200c400180650000084ef900002a00302e0032044000e00c400140650000084ef900002a00202e002e048000a00000e6802d400036223c00020000202e0032048001800000e6806a0000044481d0812d40003a4eb900043ea4700090ae0082e680d1ae0082206e000c0c2800010063660000123028007c46400240000c660000044e7541f90004419e7000102e0084d040303000006f0000065340444044401d400012102e0084060000406a0000121d6e001a001408ee000000156000000e1d6e0019001408ae000000157000102e008404000020d000d04030300000e840082e0000001567000006044000107400082e000000156600001e142e0084040200180242007f04420040c5c2c4c24842c4c2e98a4842d4406b00000a323c0200600000084442323c0201102e00144eb900008cda206e00782e10660000062e2e007e70004eb900016ea44e75` |

- [F] 범위에서 뺀 바이트: `ce62..ce72`(`BRA.W` 표, 다른 함수), `d727a..d72f2`(자료, 아래), `16ed2..16ef0`(기존 sprite 실행부, 결정 1).
- [F] 자료(fixed ROM, physical window로만 읽음):
  - `d727a..d72f2` 120바이트(SHA256 `961a02d9152ca6d3bb3e7ed7072af81b8b89e2eef340b2f0a5a6c844292d1a4c`): 12바이트 record 5개씩 두 표. `d727a`(`d72f2` 진입)와 `d72b6`(`d72fe` 진입). record = LONG→`7e(A6)`, LONG→`78(A6)`(10바이트 항목 목록 포인터), LONG→`D0`(`3af8` sound 코드). 첫 표 sound `18c8..18cc`, 목록 `d6fb6`/`d7044`. 둘째 표 sound `1a7e`, 목록 `d70fa`/`d71a6`. index는 `76(A6)`−1이며 `d7310`이 `<5`(무부호)로 막는다.
  - 항목 목록(10바이트): `+0` LONG(→`16ea4`의 `D7`. 0이면 `7e(A6)`), `+6` WORD 목표 X, `+8` WORD 목표 Y. 다음 항목의 `+0` WORD가 음수이면 끝이다(`d7384 TST.W (A0); BPL`).
  - `4419e..4439e` WORD 256개(SHA256 `5a8a09816561dcf8bdd8e2ac949047c13ae61dd0494b70cd482ae5d99c55688b`): [I] cosine 표(`0100` … `ff00` … ). index는 `ADD.W D0,D0`(`MOVEQ #0` 뒤 BYTE)라 ≤ `1fe`다.

## block 목록과 실행 의미

[F] 69 block. 각 줄은 block 안 명령 전체다. "(→x)"는 fall-through다. `.B`/`.W` 연산은 나머지 bit를 보존한다. `(An,Dn.W)`·`LEA d(An)`의 음수 변위는 부호확장이다. `ASR.L`/`ASR.W`는 산술 shift, `MULS.W`는 16×16 부호 곱(32비트 결과), `MULU.W`는 16×16 무부호 곱이다.

**`ce02` 지연 sprite 큐 정렬 10**
- `ce02`: `MOVE.W 1150(A5),D7; MOVE.W D0,1150(A5); MOVE.W 114e(A5),D6; BEQ ce60` (Z=`D6.W`)
- `ce12`: `LEA -cc(A5),A0; LEA b34(A5),A1; MOVE.W d38(A5),D5; LEA f4e(A5),A2` (→`ce22`)
- `ce22`: `LEA (A2,D6.W),A3; MOVE.W -(A3),D0; MOVE.W (A0,D0.W),D1` (→`ce2c`)
- `ce2c`: `CMPA.L A3,A2; BEQ ce46`
- `ce32`: `MOVE.W -(A3),D2; MOVE.W (A0,D2.W),D3; CMP.W D3,D1; BCS ce44` (무부호 `D1.W`<`D3.W`)
- `ce3e`: `MOVE.W D3,D1; MOVE.W D0,(A3); MOVE.W D2,D0` (→`ce44`)
- `ce44`: `BRA.B ce2c`
- `ce46`: `MOVE.W D7,(A0,D0.W); MOVE.W D0,(A1,D5.W); ADDQ.W #2,D5; ANDI.W #1fe,D5; SUBQ.W #2,D6; BNE ce22`
- `ce58`: `MOVE.W D5,d38(A5); MOVE.W D6,114e(A5)` (→`ce60`)
- `ce60`: `RTS`

**C5 `43ea4` 1**
- `43ea4`: `LEA 2e(A6),A0` (→`43ea8`, 기존 scene update block)

**node callback `d72f2`/`d72fe`(+`d7346` `d7396` `d73b0` `d73c4`) 22**
- `d72f2`: `CLR.W 1e(A6); LEA d727a(PC),A0; BRA d7302` (callback 진입)
- `d72fe`: `LEA d72b6(PC),A0` (callback 진입, →`d7302`)
- `d7302`: `SUBQ.W #1,76(A6); BCC d7310` (C=빌림: 이전 WORD가 0이면 `d730a`)
- `d730a`: `JMP 2a00`
- `d7310`: `CMPI.W #5,76(A6); BCS d7320` (무부호)
- `d731a`: `JMP 2a00`
- `d7320`: `MOVE.W 76(A6),D0; MULS.W #c,D0; LEA (A0,D0.W),A0; MOVE.L (A0)+,7e(A6); MOVE.L (A0)+,78(A6); MOVE.L (A0)+,D0; JSR 3af8`
- `d733c`: `CLR.W 7c(A6); MOVE.L #d7346,(A6)` (→`d7346`)
- `d7346`: `SUBQ.W #1,7c(A6); BCC d73d4` (callback 진입. 이전 WORD≠0이면 `d73d4`)
- `d734e`: `ADDQ.W #2,7c(A6); MOVEA.L #d73de,A0; MOVE.W #0,D0; JSR 28ae` (자식 생성)
- `d7362`: `MOVE.W 1e(A6),1e(A0); MOVE.L 78(A6),78(A0); MOVE.L 7e(A6),7e(A0); ADDQ.W #1,1e(A6); MOVEA.L 78(A6),A0; LEA a(A0),A0; MOVE.L A0,78(A6); TST.W (A0); BPL d73d4`
- `d738a`: `MOVE.W #30,7c(A6); MOVE.L #d7396,(A6)` (→`d7396`)
- `d7396`: `SUBQ.W #1,7c(A6); BNE d73d4` (callback 진입)
- `d739e`: `MOVE.B #1,63(A6); MOVE.W #20,7c(A6); MOVE.L #d73b0,(A6)` (→`d73b0`)
- `d73b0`: `SUBQ.W #1,7c(A6); BNE d73d4` (callback 진입)
- `d73b8`: `MOVE.B #2,63(A6); MOVE.L #d73c4,(A6)` (→`d73c4`)
- `d73c4`: `JSR 287e` (callback 진입, 기존 cleanup 실행부)
- `d73ca`: `BNE d73d4` (Z=`287e`의 `CMP.W 10(A0),D0`. 결정 2: live `D0.W`와 WORD `10(A0)`로 재계산)
- `d73ce`: `JMP 2a00`
- `d73d4`: `MOVE.W #ffff,D0; JMP ce02`

**자식 callback `d73de`(+`d7424`) 36**
- `d73de`: `MOVE.W #3aa,D0; MOVE.B #1,D1; JSR 8ebe` (callback 진입, 결정 4)
- `d73ec`: `MOVE.W #3be,D0; MOVE.B #1,D1; JSR 8ebe`
- `d73fa`: `BSET #6,15(A6); MOVE.W #0,2e(A6); MOVE.W #210,32(A6); MOVE.W #0,36(A6); MOVE.W #fff0,3a(A6); MOVE.W #1,82(A6); MOVE.L #d7424,(A6)` (→`d7424`)
- `d7424`: `JSR 16ed2` (callback 진입, 기존 sprite 실행부)
- `d742a`: `MOVEA.L c(A6),A0; CMPI.B #2,63(A0); BEQ d747c` (부모 `63` BYTE)
- `d7438`: `MOVEA.L 78(A6),A0; MOVEQ #0,D0; MOVEQ #0,D1; MOVE.W 6(A0),D0; MOVE.W 8(A0),D1; SUB.W 2e(A6),D0; SWAP D0; ASR.L #3,D0; SUB.L 36(A6),D0; BMI d745a`
- `d7458`: `ADDQ.L #1,D0` (→`d745a`)
- `d745a`: `ASR.L #1,D0; ADD.L D0,36(A6); SUB.W 32(A6),D1; SWAP D1; ASR.L #3,D1; SUB.L 3a(A6),D1; BMI d7472`
- `d7470`: `ADDQ.L #1,D1` (→`d7472`)
- `d7472`: `ASR.L #1,D1; ADD.L D1,3a(A6); BRA d74d6`
- `d747c`: `MOVE.W 2e(A6),D0; ADDI.W #20,D0; CMPI.W #180,D0; BCS d7492` (무부호)
- `d748c`: `JMP 2a00`
- `d7492`: `MOVE.W 32(A6),D0; SUBI.W #e0,D0; CMPI.W #140,D0; BCS d74a8`
- `d74a2`: `JMP 2a00`
- `d74a8`: `MOVE.L 2e(A6),D0; SUBI.L #a00000,D0; ASR.L #3,D0; MOVE.L D0,36(A6); MOVE.L #20000,D1; MOVE.L 32(A6),D0; SUBI.L #1800000,D0; ASR.L #3,D0; BPL d74d0` (N=ASR 결과 bit31)
- `d74ce`: `NEG.L D1` (→`d74d0`)
- `d74d0`: `ADD.L D1,D0; MOVE.L D0,3a(A6)` (→`d74d6`)
- `d74d6`: `JSR 43ea4`
- `d74dc`: `MOVEQ #0,D0; SUB.L 82(A6),D0; ASR.L #3,D0; ADD.L D0,82(A6); MOVEA.L c(A6),A0; CMPI.B #1,63(A0); BNE d7506`
- `d74f6`: `MOVE.W 7c(A0),D0; NOT.W D0; ANDI.W #c,D0; BNE d7506`
- `d7504`: `RTS`
- `d7506`: `LEA 4419e.L,A0; MOVEQ #0,D0; MOVE.B 84(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; BLE d7520` (부호 ≤0: Z 또는 N, V=0)
- `d751c`: `SUBQ.W #1,D0; NEG.W D0` (→`d7520`)
- `d7520`: `NEG.W D0; MOVE.B D0,12(A6); MOVE.B 84(A6),D0; ADDI.B #40,D0; BPL d7542`
- `d7532`: `MOVE.B 1a(A6),14(A6); BSET #0,15(A6); BRA d754e`
- `d7542`: `MOVE.B 19(A6),14(A6); BCLR #0,15(A6)` (→`d754e`)
- `d754e`: `MOVEQ #0,D0; MOVE.B 84(A6),D0; SUBI.B #20,D0; ADD.B D0,D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; ASR.W #4,D0; BTST #0,15(A6); BEQ d7570` (`A0`=`4419e`)
- `d756c`: `SUBI.W #10,D0` (→`d7570`)
- `d7570`: `MOVEQ #0,D2; BTST #0,15(A6); BNE d7598`
- `d757c`: `MOVE.B 84(A6),D2; SUBI.B #18,D2; ANDI.W #7f,D2; SUBI.W #40,D2; MULS.W D2,D2; MULU.W D2,D2; SWAP D2; MULU.W D2,D2; LSL.L #4,D2; SWAP D2` (→`d7598`)
- `d7598`: `ADD.W D0,D2; BMI d75a6`
- `d759e`: `MOVE.W #200,D1; BRA d75ac`
- `d75a6`: `NEG.W D2; MOVE.W #201,D1` (→`d75ac`)
- `d75ac`: `MOVE.B 14(A6),D0; JSR 8cda` (기존 hud 실행부)
- `d75b6`: `MOVEA.L 78(A6),A0; MOVE.L (A0),D7; BNE d75c4`
- `d75c0`: `MOVE.L 7e(A6),D7` (→`d75c4`)
- `d75c4`: `MOVEQ #0,D0; JSR 16ea4` (기존 sprite 실행부)
- `d75cc`: `RTS`

## 구현 범위와 규약

- routing 3 범위 `[ce02,ce62)` `[43ea4,43ea8)` `[d72f2,d75ce)`. 짝수 PC 416개 중 block 시작 69, 내부 347. 내부 PC 직접 진입은 `unsupported animation objects u04 PC`다. 이웃 `ce00`(sprite RTS)·`ce62`(다른 함수)·`43ea2`(cleanup)·`43ea8`(scene update)·`d72f0`·`d75ce`(자료)는 기존 routing 또는 `unsupported animation machine PC`다.
- carry: block 사이 소비 0, known 생산 0, FLOW_ONLY 15(결정 3). 나머지는 Unknown.
- Z 재계산 1곳: `d73ca`(결정 2).
- 반복: `ce22..ce46` 정렬은 `114e(A5)` WORD/2회 바깥 반복(안쪽은 남은 항목 수)이다. 원본대로 두고 block budget(1,000,000)만 한계다. [F] `D6.W`가 홀수이면 `SUBQ.W #2`가 0을 지나쳐 65,535/2회 가까이 돈다(원본대로).
- 홀수 주소 WORD/LONG 접근과 work RAM 밖 쓰기는 기존 checked 오류다(`ce02`의 레코드 offset·지연 목록 길이 검증은 C++ `sort_sprite_queue` 계약과 달리 하지 않는다: 원본 명령 그대로 실행하고 bus가 막는다).
- 자식 생성 `28ae`가 실패하면(빈 객체 없음) 원본대로 `A0`=`100e98` sentinel에 `d7362`가 쓴다.
- 회귀 탐침: 결정 6. 바꾸는 기존 test는 없다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 69 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), zero-step, 내부 347 PC 정확한 오류, 홀수 PC, 이웃 경계, 경계 `8ebe`. 자연에 없는 길(`d72fe` 표, `76(A6)`=0/≥5, 부모 `63`=2 날아가기, 화면 밖 삭제, `287e` Z 양쪽, `28ae` 실패, cosine 표 경계, 정렬 동일 키·홀수 길이)은 원본 코드로 만든 typed fixture(Unicorn)로 비교한다.
- 실제 ROM 차분: `ce02`·`d7424` 경로를 실제 ROM 자료로 Unicorn과 비교한다.
- 차분(F2 프레임 패스, 142 seed): 이전 일치 pass 7,736이 모두 그대로 일치하고 mismatch 0. U04 단독은 seed 24·25가 `8ebe`에서 멈춘다(결정 4). U01+U02+U03+U04 합본에서 seed 24·25 완주(범위 문서 50→52)를 기대한다.

## 미확인·범위 밖

1. [I] `d72f2`/`d72fe`는 목록 항목마다 자식(`d73de`)을 2 frame 간격으로 만들고, 끝나면 `30`·`20` frame 기다려 `63` 상태 1·2를 거쳐 `287e` 비교가 같아지면 스스로 지우는 연출 객체다. 자식은 목표 점으로 감쇠 이동하다가 부모 `63`=2에서 화면 밖으로 날아간다. 게임 의미(표시 문자·장면)는 미확인이다.
2. [U] `4419e`가 cosine 표라는 것은 값 모양에서 한 추론이다.
3. 범위 밖: `8ebe`(U02), `16ed2`(sprite), `287e`·`43e38`(cleanup), `43ea8`(scene update), `28ae`·`2a00`(fade_card), `3af8`(sound), `8cda`(hud), `16ea4`(sprite).

작업자 scratch: 세션 scratchpad `f4u04/`(`u04.py` block·범위·SHA 계산, `dis_u04.py`, `reach.py`; 저장소 밖).
