# 객체 callback F4 N04: 운동 공용 루틴 `6feb4`/`70036`, 판정 루틴 `4a46c` `4bc04`, U13 `7090a` 계열 callback `71c90` `72a18`(설치 `72bcc` `72c72` `72ce4` `72d42`), U07 계열 `aa93e`(설치 `aa9ec`, 자식 `ab0b8`과 그 설치 `ab11a` `ab17a`, 공용 꼬리 `ab02a`), interpreter 표 처리기 `eb752` `eb766` 계약 초안

**상태: 계약(메인 결정 반영, Claude Opus 5.5 main 2026-10-12: 결정 1·2·4·5a 수용, 결정 3은 "BLT를 두 predecessor에 묶기"로 확정). 아래 "작업자 검증 기록"은 확정안 구현의 scratch 기록이다.**

범위 근거는 재범위 문서 `animation-machine-object-callbacks-f4-rescope.md`(SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 메인 결정 1~5와 N04 행이다. 단위 형식과 규약은 N01 계약(`animation-machine-objects-n01-contract.md`, SHA256 `f9aecd66299a1533c23e278fa2b33059821e07306982eb881ddc789177f3523c`, bank animation 형식과 `49fc6` 반환 C 소비), U12 계약(SHA256 `61bd4657f2dab1b48ebd337e1a2000054911f233a458f3bb0f321e7846eac32d`, `6feb4` `70036` `4bc04`를 경계로 부르는 호출자), U04 계약(SHA256 `9c61f228b57bdb3a3b239b3342d437aeaba2d22169caeae3ad9d772d1f405397`, 결정 2 flag 재계산)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC와 실행부 없는 미연결 PC는 경계다(아래 "의존·경계").
- 재범위 결정 2: 단위 안에서 설치되는 callback은 본문이 단위 범위 안에 있으면 포함하고, 범위 밖 설치 대상은 값(LONG)만 쓰는 경계다.
- U01~U20b·N01 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`Scc`)과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`/`BCHG`만인 block, callee C를 소비하는 단독 Bcc는 FLOW_ONLY다. 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다. predecessor가 정해질 때 flag를 live 레지스터로 정확히 재계산한다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C를 소비자에서 쓰려면 native 분기 결과로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N04의 코드는 모두 `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료(`2000b8` `2000d0` `2000d4` `200154`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n04`(HEAD `4f91481` = U20b·N01까지 통합, `engine/src/animation_machine.cpp` SHA256 `78d13d30681b13dd3e6b90d8a72038f3a4bd08548d890103b45efd7b0794985f`, routing 규칙 59개)을 참조했다. 동시에 진행하는 N03(`4b82e..4b8a2` `c603a..c64a0`, 작업 트리 `metalslug-n03`)의 `4b82e`는 N04의 경계 callee다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n04/n04blocks.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **N04 = 223 block**, 코드 11 범위 2,410바이트다. 재범위 N04 행의 212 block(14 함수 진입)에 결정 2의 범위 안 설치 callback 12 block을 더하고, 두 predecessor에 묶은 `ab1a6 BLT` 1개를 뺐다(아래 "메인 결정 1·3").
  - `71d0a`(1): `71d04 MOVE.L #71d0a,(A6)`의 설치 callback(재범위 문서는 N15 진입으로 셌지만 본문이 N04 `71c90..71d48` 안이고 `71cf4`에서 fall-through한다).
  - `72c72` `72c7a` `72ca2` `72ca6` `72cce` `72cd8` `72cde`(7): `72c4a`/`72c68 MOVE.L #72c72,(A6)`의 설치 callback 본문(`72ce4`로 이어진다).
  - `72d42` `72d48` `72d50` `72d54`(4): `72e84 MOVE.L #72d42,(A6)`의 설치 callback 본문.
  - 재범위 문서의 "미실행 설치 4(+42)" 중 범위 안 2개(`72c72` `72d42`)가 위 11 block이고, 범위 밖 `71d48`(`71d3e`가 설치)과 `ab226`(`ab21c`가 설치)은 고아 설치 경계로 남는다(재범위 결정 3).
- [F] 진입 18개: 함수 `4a46c` `4bc04` `6feb4` `70036` `eb752` `eb766`(호출·표 진입), U13 설치 callback `71c90` `72a18`, U07 `28ae` 자식 `aa93e`(재범위 문서 진입), 범위 안 설치 callback `71d0a` `72bcc` `72c72` `72ce4` `72d42` `aa9ec` `ab11a` `ab17a`, 범위 안 `28ae` 자식 `ab0b8`(`aa9d6`이 만든다). `ab02a`는 `ab222 BRA`의 대상(`ab0b8` 계열 본문)이다.
- [F] TRAP·계산 PC(JMP/JSR 표, 레지스터 간접)·SUBX/ADDX/DIVx/MULx·I/O port 쓰기·bank 변경은 없다. 묶인 Bcc 2곳(`4a474 BEQ`+`4a478 BMI`, `ab192 BEQ`+`ab196 BLT`). predecessor 2개에 묶은 Bcc 1곳(`ab19a`/`ab1a2`의 CMPI 뒤 `ab1a6 BLT`, 메인 결정 3; `ab1a6`은 내부 PC).
- [F] **carry**: 소비 block 10개 `72be2` `72d04`(`49fc6`), `72bfc` `72c08`(경계 `49c38`), `72c18` `72c30`(`289e`), `72c46`(경계 `494c0`), `72e4c` `aaa02`(`1ab02`), `ab06c`(`288c`). known 생산 block 2개 `4a48a`(`ORI #1,CCR` Set) `4a490`(`ANDI #fe,CCR` Clear): `4a46c` 반환 C는 다른 단위 호출자(`423d0` `5b486` `99ffa` `BCC`)가 소비한다. `4bc04` `6feb4` `70036`의 반환 C는 소비자가 없어 Unknown이다(아래 "carry").
- [F] 경계(실행부 없는 미연결 callee): `494c0` `4970a` `49c38` `4bb52`(JSR), `cc778`(JMP tail, `72df2` `72e18`), N03 `4b82e`(JSR, `eb752` `eb766`). 고아 설치 값: `71032`(N15) `71d48` `ab226`.
- [F] 자료 읽기: bank window LONG 4개(`2000d0` `2000d4` `200154` `2000b8`)와 그 값 + d16 / + 4×index의 LONG, work RAM `5b88(A5)` WORD 표(`4bc04`), `53a2(A5)` `53a6(A5)` WORD(`6feb4` `70036`). 모두 live bus로 읽는다. fixed ROM 자료 표는 직접 읽지 않는다(`72a10` `72d56` `aa8ba`는 경계/다른 실행부에 넘기는 주소, `acbfe`는 `49f8c`에 넘기는 script 주소).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`, TB 기준): RNG 초기화+응답 `80` 400 frame에서 seed 16 17 18 19 26 27 32 33 38 39 42 43 46 47 62 63 76 77 96~99 102~105 116 117이 N04 PC를 실행하고, 223 시작 중 104개가 TB 시작으로 나타난다. base 120 frame 기록에서는 `4a46c` `4bc04` 계열 7개다. 나머지는 typed fixture로 덮는다.
- [F] 기준 측정(이 작업 트리 base `4f91481`의 `git archive` 사본, scratch 출력 `ms5-scratch/n04/fp/base_*`): base 일치 pass 12,178·node 94,840, 불일치 0, 자연 완주 111. RNG 400: 일치 pass 36,000·node 259,677, 불일치 0, complete 90. seed 18 19 26 27 76 77 96~99 102~105는 f0 `7090a` 계열, 38 39 62 63은 f0 `7086a` 계열 callback 안의 `6feb4`가 첫 미연결 PC다.
  - [F] 기대(작업자 scratch 정적 재생 `n04reach.py`): RNG complete +62 63(`6feb4` 뒤 완주). 26 27은 다음 미연결이 N03 `4b82e`(`aa93e` 계열 interpreter 표 → `eb752`)라 N03 병합 뒤 완주한다. 18 19 96 97 102 103은 `c5896`, 38 39는 `c3a7c`, 76 77 98 99 104 105는 `708a6`(N15)까지 나아간다. base 완주 변화 없음.

## 메인 결정 (확정)

1. **범위 212→224(결정 3 반영 뒤 시작 223). [수용]** 권고: 재범위 결정 2대로 본문이 N04 범위 안에 있는 설치 callback `71d0a`(1) `72c72`(7) `72d42`(4)를 포함한다. 220을 4 넘지만 분할하면 `72c72..72ce4`가 N04 routing 범위 `72a18..72d56` 한가운데의 미연결 구멍이 되고, `71d0a`는 `71cf4`의 fall-through라 빼면 `71c90` 본문이 끊긴다. 대안: `72c72`·`72d42` 계열을 고아 정리 단계로 미루고 그 PC를 N04 내부 오류로 둔다(비권고).
2. **routing 범위는 코드만(11 범위). [수용]** `4a46c..4a496` `4bc04..4bc44` `6feb4..70054` `71c90..71d48` `72a18..72d56` `72dd2..72e8e` `aa93e..aaa18` `ab02a..ab078` `ab0b8..ab226` `eb752..eb75c` `eb766..eb774`(짝수 PC 1,205개, block 시작 223, 내부 982).
   - `72d56..72d66`(WORD 표, `1ab02` 입력)과 `72a10..72a18`(WORD 표, `494c0` 입력)은 자료라 routing하지 않는다.
   - `72d66..72dd2`(`72d66` 진입, `JMP cc8b4` 계열)는 재범위 N15 행 범위라 routing하지 않는다. N15는 `72dd2..72e8e`를 이미 routing된 N04 본문으로 다룬다(재범위 N15 행 `72d66..72e8e`와 겹치는 부분).
   - `72dd2..72e8e` 안의 죽은 명령 `72e12 RTS` `72e14 BRA.W` `72e38 RTS`(JMP 뒤, 어떤 분기의 대상도 아님)는 내부 PC 오류다.
   - `eb75c..eb766`(`eb75c` 함수)과 `eb74a`는 재범위 N11 범위라 routing하지 않는다. 재범위 표기 `eb752..eb774`는 이를 포함한 요약이다.
3. **`ab1a6 BLT`를 두 predecessor에 묶는다. [확정: 메인, 재계산안 불수용]** [F] `ab1a6`은 `ab19a CMPI.W #10,D1; BRA.W ab1a6`과 `ab1a2 CMPI.W #fff0,D1`(fall-through) 두 block의 뒤이고 CCR을 바꾸지 않는 `BLT.W ab1b0` 하나뿐이다. predecessor가 둘이라 flag 재계산(유일 predecessor 관례)을 쓰지 않는다. 확정: `ab19a` block은 `CMPI.W #10,D1; BRA.W ab1a6; BLT.W ab1b0`을, `ab1a2` block은 `CMPI.W #fff0,D1; BLT.W ab1b0`을 한 block으로 실행하고 각자 계산한 N⊕V(= sext(`D1.W`) < sext(k), k = `0010`/`fff0`, 정확한 부호 비교)로 `ab1b0`/`ab1aa`를 고른다. `ab1a6`은 block 시작이 아니며(묶인 Bcc) 직접 진입은 `unsupported animation objects n04 PC`다. 두 block은 CMPI가 C를 바꾸므로 Unknown이다. 직접 진입 `ab19a`/`ab1a2`는 어떤 `D0`/`D1`에서도 native와 같다(전제 없음).
4. **경계 callee의 반환 C. [수용]** `72bfc` `72c08`(`49c38`), `72c46`(`494c0`)은 아직 실행부가 없는 callee의 C를 소비한다. N04는 이 소비자를 일반 소비자와 같이 다룬다(known C면 분기, Unknown이면 `objects n04 caller requires known carry`). 경계에서 C++는 멈추므로 이 소비자는 typed fixture(C 선언)로만 실행된다. [F] 자연 기록에서 `72bec`은 늘 `BMI` 성립(`72c6e`)이라 `72bf4..72c4a`는 400 frame 안에 실행되지 않는다.
5a. **interpreter callback 대상 2개 추가(공유 실행부 1줄). [수용: `animation_machine_interpreter.cpp` `callback()` 허용 목록에 `eb752` `eb766` 추가, 그 밖 대상은 기존 `unsupported animation callback target`]** [F] `eb752` `eb766`은 interpreter 명령 callback 표 `4a6dc`의 대상이고 원본 `4a352 JSR (A1)`(live 대상)로 불린다. 기존 `animation_machine_interpreter.cpp` `callback()`은 대상을 `3679e` `2b3e8` `2b3fa` `47672`로 제한하고 그 밖은 `unsupported animation callback target`이다. 권고: 허용 목록에 `eb752` `eb766`을 더한다(그 밖 대상은 기존 오류 그대로). 근거: [F] 추가 전 실제 ROM 차분(seed 1, 1,500건)에서 `aa93e` 계열 19건이 interpreter script의 `eb766` callback에서 이 오류로 native와 달랐다. [I] 추가하지 않으면 seed 26 27의 RNG 차분도 `aa93e` 계열에서 같은 오류(`cpp-error-other`)로 멈춘다. 더하면 C++가 `eb752`/`eb766`을 실행하고 N03 경계 `4b82e`에서 미연결 PC로 멈춘다. 대안: interpreter callback을 일반 live 대상 routing으로 바꾼다(비권고: 다른 대상의 기존 오류 분류가 바뀌어 범위가 커진다).
5. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n04.cpp`의 `animation_objects_n04_block`. 오류는 `unsupported animation objects n04 PC`(내부 PC), `objects n04 caller requires known carry`(소비자 10개의 Unknown C).
6. **무효화 탐침**(F4 test 경계 관례대로 고친다).
   - `engine/tests/animation_machine_objects_u08b_test.cpp` `interior()`의 `outside[]` 중 `0x4bc42`(이제 N04 `4bc40` block의 내부 PC) → work RAM 탐침 `0x10fe14`로 바꾼다. 같은 목록의 `4bb52`는 N04 경계(미연결)로 남아 그대로 유효하다.
   - U12 test의 `4bc04` `6feb4` `70036`은 stop 성립만 확인하는 경계 탐침(F4 관례)이라 영향이 없다. U13 test의 `71c90` `72a18`은 설치 값(자료)이다. `tools/`에는 N04 PC를 경계로 쓰는 곳이 없다(`4a46c`는 옛 interpreter 관찰 도구의 상한 값).

## 원본 바이트 근거

[F] 코드 11 범위 합계 2,410바이트. 범위 순서로 이어 붙인 SHA256 `49c3b28dbe007937d71e0ce2eb57eb9bfa195375ed95c7242226994f30385582`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `4a46c..4a496` | 42 | `94e8c4f4a2270b41561a73ea65569490173885fab3fd1fdff5a4ea900f074885` | `4a46c`(부모 BYTE `17` 판정, C 반환) |
| `4bc04..4bc44` | 64 | `a7db2237b0eef61a71df0ea93519164165e935a3d21bf8c712f361db4e12b69f` | `4bc04`(work RAM `5b88(A5)` 격자 WORD) |
| `6feb4..70054` | 416 | `693fa05376de7e64686036856fca2fbcf46a2c9f221161839688c72457cb3cc7` | `6feb4`(운동 갱신), `70036` |
| `71c90..71d48` | 184 | `bb9db4146970ed43338208f60b62c01bcf4f106995b96a9a5ad53fa4bd91a355` | `71c90`, 설치 `71d0a` |
| `72a18..72d56` | 830 | `03d01880a8abeeb331ed1dc4b76668a3fad15a8a71ff6533556885a45877a795` | `72a18`, 설치 `72bcc` `72c72` `72ce4` `72d42` |
| `72dd2..72e8e` | 188 | `b3f43c80867d7d71feb755858707c2e025d566cbf0cbb4e261150f3659e5264e` | 공용 꼬리 `72dd2`(`BSR 6feb4`, `BRA 70054`) |
| `aa93e..aaa18` | 218 | `4c5882c73cdd7c3663bab9fff9f09e7f0338d2eccc8c02d97f088ca9b77424ff` | `aa93e`, 설치 `aa9ec`, 자식 `ab0b8` 생성 |
| `ab02a..ab078` | 78 | `7c77d4c1ca24430f1916066b5f6f759ed18b0480b732b929ae7ed5e242cc097f` | `ab0b8` 계열 꼬리 `ab02a` |
| `ab0b8..ab226` | 366 | `03b2f0cda885f06b851a4a551d220d07d54be105f4512e931d2a59f30d24ffbb` | `ab0b8`, 설치 `ab11a` `ab17a` |
| `eb752..eb75c` | 10 | `b881849f499368bb7a66ea00f42a6a187546200d3f8616192d7f0234c32b4926` | `eb752`(interpreter 표 처리기) |
| `eb766..eb774` | 14 | `316d793b9af22fe4ddc6927a08bc4e09f29a9b9f5831701a118d690148759f78` | `eb766`(interpreter 표 처리기) |

- [F] 범위 밖 이웃: `4a46a`(interpreter 끝), `4a496`(U14), `4bc02`/`4bc44`(U08b 앞뒤), `70054`(U12), `71d48..`(고아 설치 `71d48`, 미연결), `72a10..72a18`(자료), `72d56..72d66`(자료), `72d66..72dd2`(N15), `aaa18..`(미실행 함수, 미연결), `ab078..ab0b8`(자료), `ab226..`(고아 설치), `eb74a..eb752` `eb75c..eb766`(N11), `eb774..`(미연결).
- [F] 참조: `6feb4`는 U12 `70544 BSR`과 N04 `72e3e BSR`. `70036`은 U12 `7016e BSR`, 미연결 `7035e` `73110` `732a8 BSR`(그리고 fixed ROM LONG `c7358` `c7570`). `4bc04`는 U12 `70164`, N04 `72c5c`, 미연결 `705ea` `73106` `73676` `761b0` `86c5a`(모두 `JSR`; 복귀 뒤 `MOVE`/`MOVEM`+`MOVE`/`CMPI`/`TST`라 C를 소비하지 않는다). `4a46c`는 `JSR` 44곳(N04 `ab1c0`, 미연결 `423d0` `5b486` `99ffa`는 바로 `BCC`, 나머지는 `JSR 49fc6`/`RTS`/`BRA`/`MOVEA`/`LEA`). `71c90`은 U13 `70a4a`와 미연결 `7266a` `72772` `7290a` `72a06`의 설치 값, N04 `72bd2 BEQ`의 대상. `72a18`은 U13 `70956` `7096c`, 미연결 `70d5c`, N04 `72be8`의 설치 값. `aa93e`는 fixed ROM LONG `e8e64`(U07 `28ae` 자식 표). `ab0b8`은 N04 `aa9d6`과 미연결 `aaa48`의 `MOVEA.L #ab0b8,A0`. `ab11a`는 미연결 `ab322`의 설치 값. `72d42`는 N04 `72e84`와 미연결 `734a0`. `eb752` `eb766`은 fixed ROM LONG 표 `4a6dc`(`eb74a` `eb752` `eb75c` `eb766`, interpreter 명령 callback 표)의 둘째·넷째 값이다.

## block 목록과 실행 의미

[F] 223 block. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `.W` 연산은 하위 WORD만, `.B`는 하위 BYTE만 바꾼다. `MOVEQ`는 LONG 전체를 부호확장 값으로 쓴다. `ASR`는 산술, `LSR`는 논리 shift다. 비교 분기: `BCC`/`BCS`는 무부호 빌림, `BLS`는 무부호 ≤, `BLT`는 부호 있는 <, `BPL`/`BMI`는 결과 최상위 bit, `BEQ`/`BNE`는 결과 0 여부다. `BTST`/`BSET`/`BCLR`/`BCHG #n,d16(An)`은 BYTE의 bit n(Z만 바꿈, 메모리 BYTE 읽기·쓰기)이다.

"anim(k, bank, d16)"은 `LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d16(A1),A1; JSR 49f8c.L`(N01 animation과 같음; bank LONG과 그 값 + d16의 LONG을 live bus로 읽는다). "anim-index(k, bank)"는 `LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); LEA 26(A6),A0; MOVE.W D0,D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L bank.L,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.L`(N01 animation-index와 같음; D1.W×4를 부호확장 index로, bank LONG은 두 번 읽는다). "side(d16a, d16b, ret_a, ret_b)"는 `TST.W 9c(A6); BNE`로 고르는 두 anim(`3`, `2000d0`, d16a)/(`b`, `2000d4`, d16b)이다.

**`4a46c` 5** (부모 node BYTE `17` 판정, C 반환; 묶인 Bcc 1)
- `4a46c`: `MOVEA.L c(A6),A0; MOVE.B 17(A0),D0; BEQ.W 4a490; BMI.W 4a47e` (→`4a47c`; `MOVE.B` 결과 0 → `4a490`, bit 7 → `4a47e`)
- `4a47c`: `ADDQ.B #1,D0` (→`4a47e`)
- `4a47e`: `MOVE.B D0,17(A6); BTST.B #0,D0; BNE.W 4a490` (→`4a48a`; 자기 node BYTE `17`)
- `4a48a`: `ORI.B #1,CCR; RTS` (known 생산: C Set)
- `4a490`: `ANDI.B #fe,CCR; RTS` (known 생산: C Clear)

**`4bc04` 6** (work RAM 격자 WORD; D0=x, D1=y)
- `4bc04`: `SUBI.W #100,D1; CMPI.W #100,D1; BCC.W 4bc40` (→`4bc10`; 무부호 `D1.W`≥`100` → `4bc40`)
- `4bc10`: `LSR.W #4,D1; ANDI.W #e,D1; SUBI.W #20,D0; CMPI.W #200,D0; BCC.W 4bc40` (→`4bc22`)
- `4bc22`: `LSR.W #1,D0; ANDI.W #f0,D0; LEA 5b88(A5),A0; ADDA.W D0,A0; ADDA.W D1,A0; MOVE.W (A0),D0; CMPI.W #100,D0; BCS.W 4bc3e` (→`4bc3a`; `ADDA.W`는 부호확장)
- `4bc3a`: `MOVE.W #ff,D0` (→`4bc3e`)
- `4bc3e`: `RTS` (FLOW_ONLY)
- `4bc40`: `MOVEQ #0,D0; RTS`

**`6feb4`/`70036` 59** (운동 갱신; `6feb4`는 U12 `70544`와 N04 `72e3e`의 `BSR`, `70036`은 U12 `7016e` 등의 `BSR`)
- `6feb4`: `MOVEQ #0,D2; MOVEQ #0,D3; MOVE.W 42(A6),D0; SUBI.W #20,D0; CMPI.W #100,D0; BCC.W 6ffd6` (→`6fec8`)
- `6fec8`: `JSR 48502.L` (FLOW_ONLY)
- `6fece`: `TST.W D7; BEQ.W 6ff74` (→`6fed4`)
- `6fed4`: `MOVE.W #60,D6; SUB.W 46(A6),D1; BPL.W 6fee2` (→`6fee0`)
- `6fee0`: `ASR.W #1,D1` (→`6fee2`)
- `6fee2`: `ASR.W #1,D1; SUB.W D1,D6; BPL.W 6feee` (→`6feea`)
- `6feea`: `MOVE.W #0,D6` (→`6feee`)
- `6feee`: `SUB.W 8e(A6),D0; BPL.W 6fefc` (→`6fef6`)
- `6fef6`: `ADD.W D6,D0; BRA.W 6fefe`
- `6fefc`: `SUB.W D6,D0` (→`6fefe`)
- `6fefe`: `CMPI.B #0,86(A6); BEQ.W 6ff0e` (→`6ff08`)
- `6ff08`: `MOVE.W D0,D7; ASR.W #2,D7; SUB.W D7,D0` (→`6ff0e`)
- `6ff0e`: `MOVE.W #60,D6; SUB.W 46(A6),D3; BPL.W 6ff1c` (→`6ff1a`)
- `6ff1a`: `ASR.W #1,D3` (→`6ff1c`)
- `6ff1c`: `ASR.W #1,D3; SUB.W D3,D6; BPL.W 6ff26` (→`6ff24`)
- `6ff24`: `MOVEQ #0,D6` (→`6ff26`)
- `6ff26`: `SUB.W 8e(A6),D2; BPL.W 6ff34` (→`6ff2e`)
- `6ff2e`: `ADD.W D6,D2; BRA.W 6ff36`
- `6ff34`: `SUB.W D6,D2` (→`6ff36`)
- `6ff36`: `CMPI.B #1,86(A6); BEQ.W 6ff46` (→`6ff40`)
- `6ff40`: `MOVE.W D2,D7; ASR.W #2,D7; SUB.W D7,D2` (→`6ff46`)
- `6ff46`: `MOVE.W D0,D7; BPL.W 6ff4e` (→`6ff4c`)
- `6ff4c`: `NEG.W D7` (→`6ff4e`)
- `6ff4e`: `MOVE.W D2,D6; BPL.W 6ff56` (→`6ff54`)
- `6ff54`: `NEG.W D6` (→`6ff56`)
- `6ff56`: `CMP.W D6,D7; BCS.W 6ff5e` (→`6ff5c`; 무부호 `D7.W`<`D6.W` → `6ff5e`)
- `6ff5c`: `MOVE.W D0,D2` (→`6ff5e`)
- `6ff5e`: `MOVE.W D2,D0; ADDI.W #18,D0; CMPI.W #30,D0; BCC.W 6ff70` (→`6ff6c`)
- `6ff6c`: `NEG.W D2; ASR.W #1,D2` (→`6ff70`)
- `6ff70`: `SWAP D2; CLR.W D2` (→`6ff74`)
- `6ff74`: `MOVE.W 9a(A6),D7; BEQ.W 6ffd6` (→`6ff7c`)
- `6ff7c`: `MOVE.W 46(A6),D1; SUB.W 98(A6),D1; SUB.W 53a6(A5),D1; BPL.W 6ff8e` (→`6ff8c`)
- `6ff8c`: `NEG.W D1` (→`6ff8e`)
- `6ff8e`: `SUB.W D1,D7; BCC.W 6ff96` (→`6ff94`; 빌림 없음 → `6ff96`)
- `6ff94`: `MOVEQ #0,D7` (→`6ff96`)
- `6ff96`: `MOVE.W 96(A6),D0; ADD.W 53a2(A5),D0; SUB.W 42(A6),D0; BMI.W 6ffb2` (→`6ffa6`)
- `6ffa6`: `SUB.W D7,D0; BMI.W 6ffae` (→`6ffac`)
- `6ffac`: `MOVEQ #0,D0` (→`6ffae`)
- `6ffae`: `BRA.W 6ffba` (FLOW_ONLY)
- `6ffb2`: `ADD.W D7,D0; BPL.W 6ffba` (→`6ffb8`)
- `6ffb8`: `MOVEQ #0,D0` (→`6ffba`)
- `6ffba`: `SWAP D0; CLR.W D0; MOVE.L D0,D7; BPL.W 6ffc6` (→`6ffc4`)
- `6ffc4`: `NEG.L D7` (→`6ffc6`)
- `6ffc6`: `MOVE.L D2,D6; BPL.W 6ffce` (→`6ffcc`)
- `6ffcc`: `NEG.L D6` (→`6ffce`)
- `6ffce`: `CMP.L D6,D7; BCS.W 6ffd6` (→`6ffd4`; 무부호 LONG)
- `6ffd4`: `MOVE.L D0,D2` (→`6ffd6`)
- `6ffd6`: `MOVE.L #a00000,D0; SUB.L 8e(A6),D0; BPL.W 6fff4` (→`6ffe4`)
- `6ffe4`: `ADDI.L #600000,D0; BMI.W 6fff0` (→`6ffee`)
- `6ffee`: `MOVEQ #0,D0` (→`6fff0`)
- `6fff0`: `BRA.W 70000` (FLOW_ONLY)
- `6fff4`: `SUBI.L #600000,D0; BPL.W 70000` (→`6fffe`)
- `6fffe`: `MOVEQ #0,D0` (→`70000`)
- `70000`: `ADD.L D0,D2; MOVEQ #0,D0; MOVE.W 8c(A6),D0; ADDI.W #13f,D0; MOVE.W D0,8c(A6); LSL.L #3,D0; SUB.L 92(A6),D2; MOVE.L 92(A6),D1; BMI.W 70020` (→`7001e`)
- `7001e`: `NEG.L D0` (→`70020`)
- `70020`: `ADD.L D0,D1; ASR.L #5,D1; ASR.L #7,D2; SUB.L D1,D2; ADD.L 92(A6),D2; MOVE.L D2,92(A6); ADD.L D2,8e(A6); RTS`
- `70036`: `CMP.W 9a(A6),D0; BLS.W 70052` (→`7003e`; 무부호 `D0.W`≤WORD `9a` → `70052`)
- `7003e`: `MOVE.W D0,9a(A6); SUB.W 53a2(A5),D2; SUB.W 53a6(A5),D3; MOVE.W D2,96(A6); MOVE.W D3,98(A6)` (→`70052`)
- `70052`: `RTS` (FLOW_ONLY)

(`6feb4`~`70020` 56 + `70036`~`70052` 3 = 59.)

**`71c90` 10** (U13 설치 callback; 설치 `71d0a`)
- `71c90`: `MOVE.L #0,36(A6); TST.W 9c(A6); BNE.W 71ccc` (→`71ca0`)
- `71ca0`: anim(`3`, `2000d0`, `1c`) (복귀 `71cc8`)
- `71cc8`: `BRA.W 71cf4` (FLOW_ONLY)
- `71ccc`: anim(`b`, `2000d4`, `1c`) (복귀 `71cf4`)
- `71cf4`: `MOVE.L #0,64(A6); MOVE.L #0,3a(A6); MOVE.L #71d0a,(A6)` (→`71d0a`)
- `71d0a` (설치 callback): `MOVE.L 64(A6),D0; SUB.L 36(A6),D0; ASR.L #5,D0; ADD.L D0,36(A6); MOVE.L #fff00000,D0; SUB.L 3a(A6),D0; ASR.L #5,D0; ADD.L D0,3a(A6); JSR 4be34.L`
- `71d2e`: `JSR 49fc6.L` (FLOW_ONLY; 반환 C는 다음 `BTST` block이 쓰지 않는다)
- `71d34`: `BTST.B #7,15(A6); BEQ.W 71d44` (→`71d3e`; FLOW_ONLY)
- `71d3e`: `MOVE.L #71d48,(A6)` (→`71d44`; 고아 설치 값)
- `71d44`: `BRA.W 72dd2` (FLOW_ONLY)

**`72a18` 49** (U13 설치 callback; 설치 `72bcc`, `72a18` 재설치, 설치 `72c72`, 설치 값 `71032`)
- `72a18`: `MOVE.L #0,64(A6); JSR 49a58.L`
- `72a26`: `ANDI.W #3,D0; BNE.W 72a8e` (→`72a2e`)
- `72a2e`: `TST.W 9c(A6); BNE.W 72a62` (→`72a36`)
- `72a36`: anim(`3`, `2000d0`, `168`) (복귀 `72a5e`); `72a5e`: `BRA.W 72a8a` (FLOW_ONLY)
- `72a62`: anim(`b`, `2000d4`, `1b4`) (복귀 `72a8a`); `72a8a`: `BRA.W 72bc6` (FLOW_ONLY)
- `72a8e`: `CMPI.W #1,D0; BNE.W 72af6` (→`72a96`)
- `72a96`: `TST.W 9c(A6); BNE.W 72aca` (→`72a9e`)
- `72a9e`: anim(`3`, `2000d0`, `16c`) (복귀 `72ac6`); `72ac6`: `BRA.W 72af2` (FLOW_ONLY)
- `72aca`: anim(`b`, `2000d4`, `1b8`) (복귀 `72af2`); `72af2`: `BRA.W 72bc6` (FLOW_ONLY)
- `72af6`: `CMPI.W #2,D0; BNE.W 72b5e` (→`72afe`)
- `72afe`: `TST.W 9c(A6); BNE.W 72b32` (→`72b06`)
- `72b06`: anim(`3`, `2000d0`, `170`) (복귀 `72b2e`); `72b2e`: `BRA.W 72b5a` (FLOW_ONLY)
- `72b32`: anim(`b`, `2000d4`, `1bc`) (복귀 `72b5a`); `72b5a`: `BRA.W 72bc6` (FLOW_ONLY)
- `72b5e`: `CMPI.W #3,D0; BNE.W 72bc6` (→`72b66`)
- `72b66`: `TST.W 9c(A6); BNE.W 72b9a` (→`72b6e`)
- `72b6e`: anim(`3`, `2000d0`, `174`) (복귀 `72b96`); `72b96`: `BRA.W 72bc2` (FLOW_ONLY)
- `72b9a`: anim(`b`, `2000d4`, `1c0`) (복귀 `72bc2`); `72bc2`: `BRA.W 72bc6` (FLOW_ONLY)
- `72bc6`: `MOVE.L #72bcc,(A6)` (→`72bcc`)
- `72bcc` (설치 callback): `BTST.B #7,15(A6); BEQ.W 71c90` (→`72bd6`; FLOW_ONLY)
- `72bd6`: `JSR 4bfa4.L` (FLOW_ONLY)
- `72bdc`: `JSR 49fc6.L` (FLOW_ONLY)
- `72be2`: `BCC.W 72bec` (→`72be6`; 소비자, `49fc6` 반환 C)
- `72be6`: `MOVE.L #72a18,(A6)` (→`72bec`)
- `72bec`: `TST.B 86(A6); BMI.W 72c6e` (→`72bf4`)
- `72bf4`: `MOVEQ #0,D0; JSR 49c38.L` (경계 callee)
- `72bfc`: `BCS.W 72c6e` (→`72c00`; 소비자, `49c38` 반환 C)
- `72c00`: `MOVEQ #1,D0; JSR 49c38.L` (경계 callee)
- `72c08`: `BCS.W 72c6e` (→`72c0c`; 소비자)
- `72c0c`: `LEA 100cb8.L,A0; JSR 289e.L` (FLOW_ONLY)
- `72c18`: `BCC.W 72c24` (→`72c1c`; 소비자, `289e` 반환 C)
- `72c1c`: `TST.B 81(A0); BEQ.W 72c6e` (→`72c24`; A0는 `289e` 뒤 live 값)
- `72c24`: `LEA 100da8.L,A0; JSR 289e.L` (FLOW_ONLY)
- `72c30`: `BCC.W 72c3c` (→`72c34`; 소비자)
- `72c34`: `TST.B 81(A0); BEQ.W 72c6e` (→`72c3c`)
- `72c3c`: `LEA 72a10(PC),A0; JSR 494c0.L` (FLOW_ONLY; 경계 callee, `72a10` 자료 주소만 넘김)
- `72c46`: `BCS.W 72c50` (→`72c4a`; 소비자, `494c0` 반환 C)
- `72c4a`: `MOVE.L #72c72,(A6)` (→`72c50`)
- `72c50`: `MOVE.W 42(A6),D0; MOVE.W 46(A6),D1; ADDI.W #10,D1; JSR 4bc04.L`
- `72c62`: `TST.W D0; BEQ.W 72c6e` (→`72c68`)
- `72c68`: `MOVE.L #72c72,(A6)` (→`72c6e`)
- `72c6e`: `BRA.W 72dd2` (FLOW_ONLY)

**`72c72`/`72ce4` 18** (설치 callback; 설치 `72ce4`, 설치 값 `71032`)
- `72c72` (설치 callback): `TST.W 9c(A6); BNE.W 72ca6` (→`72c7a`)
- `72c7a`: anim(`3`, `2000d0`, `2c`) (복귀 `72ca2`); `72ca2`: `BRA.W 72cce` (FLOW_ONLY)
- `72ca6`: anim(`b`, `2000d4`, `2c`) (복귀 `72cce`)
- `72cce`: `BTST.B #0,82(A6); BNE.W 72cde` (→`72cd8`; FLOW_ONLY)
- `72cd8`: `BCHG.B #0,15(A6)` (→`72cde`; FLOW_ONLY)
- `72cde`: `MOVE.L #72ce4,(A6)` (→`72ce4`)
- `72ce4` (설치 callback): `BTST.B #7,15(A6); BNE.W 72cf8` (→`72cee`; FLOW_ONLY)
- `72cee`: `JSR 4be2c.L` (FLOW_ONLY); `72cf4`: `BRA.W 72cfe` (FLOW_ONLY)
- `72cf8`: `JSR 4be06.L` (FLOW_ONLY)
- `72cfe`: `JSR 49fc6.L` (FLOW_ONLY)
- `72d04`: `BCC.W 72d3e` (→`72d08`; 소비자, `49fc6` 반환 C)
- `72d08`: `ADDI.W #20,46(A6); ADDI.W #40,42(A6); JSR 4bb52.L` (경계 callee)
- `72d1a`: `SUBI.W #80,42(A6); JSR 4bb52.L`
- `72d26`: `ADDI.W #40,42(A6); JSR 4bb52.L`
- `72d32`: `SUBI.W #20,46(A6); MOVE.L #71032,(A6)` (→`72d3e`; N15 설치 값)
- `72d3e`: `BRA.W 72dd2` (FLOW_ONLY)

**`72d42` 4** (설치 callback, `72e84`가 설치)
- `72d42`: `JSR 43e34.L` (FLOW_ONLY)
- `72d48`: `TST.B 62(A6); BNE.W 72d54` (→`72d50`)
- `72d50`: `MOVE.L 9e(A6),(A6)` (→`72d54`; 저장한 callback 복원)
- `72d54`: `RTS` (FLOW_ONLY)

**공용 꼬리 `72dd2` 16** (`71d44` `72c6e` `72d3e`의 `BRA`)
- `72dd2`: `JSR 4b54e.L` (FLOW_ONLY)
- `72dd8`: `BTST.B #7,61(A6); BEQ.W 72e3a` (→`72de2`; FLOW_ONLY)
- `72de2`: `MOVEA.L c(A6),A0; ST.B 62(A0); TST.W 9c(A6); BNE.W 72e18` (→`72df2`)
- `72df2`: `MOVE.B #ff,17(A6); LEA cdeea.L,A0; MOVEA.L 2000d0.L,A1; MOVE.W #3,D1; MOVE.W #0,D2; JMP cc778.L` (경계 tail; bank LONG 읽기)
- `72e18`: `MOVE.B #ff,17(A6); LEA cdef8.L,A0; MOVEA.L 2000d4.L,A1; MOVE.W #b,D1; MOVE.W #1,D2; JMP cc778.L` (경계 tail)
- `72e3a`: `BRA.W 72e3e` (FLOW_ONLY)
- `72e3e`: `BSR.W 6feb4` (FLOW_ONLY)
- `72e42`: `LEA 72d56(PC),A0; JSR 1ab02.L` (FLOW_ONLY)
- `72e4c`: `BCC.W 72e5e` (→`72e50`; 소비자, `1ab02` 반환 C)
- `72e50`: `MOVEA.L c(A6),A0; ST.B 62(A0); JMP 2a00.L` (FLOW_ONLY)
- `72e5e`: `MOVE.B 62(A6),D0; BEQ.W 72e8a` (→`72e66`)
- `72e66`: `SUBQ.W #1,D0; ANDI.W #1,D0; BNE.W 72e7a` (→`72e70`)
- `72e70`: `BSET.B #0,15(A6); BRA.W 72e80` (FLOW_ONLY)
- `72e7a`: `BCLR.B #0,15(A6)` (→`72e80`; FLOW_ONLY)
- `72e80`: `MOVE.L (A6),9e(A6); MOVE.L #72d42,(A6)` (→`72e8a`)
- `72e8a`: `BRA.W 70054` (FLOW_ONLY; U12)

**`aa93e` 17** (U07 `28ae` 자식; 자식 `ab0b8` 생성, 설치 `aa9ec`)
- `aa93e`: `MOVE.W #54,D0; MOVE.W #2,D1; MOVE.B #0,D2; JSR c6a96.L`
- `aa950`: `MOVE.W #c2e,D0; JSR 4a496.L`
- `aa95a`: `BSET.B #6,15(A6); MOVE.W #0,68(A6); MOVE.W #0,1e(A6); MOVE.W 76(A6),90(A6); MOVE.W 78(A6),92(A6); JSR 4c0ac.L`
- `aa97e`: `TST.W 92(A6); BNE.W aa98c` (→`aa986`)
- `aa986`: `BSET.B #0,15(A6)` (→`aa98c`; FLOW_ONLY)
- `aa98c`: `TST.W 90(A6); BNE.W aa9c0` (→`aa994`)
- `aa994`: anim(`10b`, `200154`, `4`) (복귀 `aa9bc`); `aa9bc`: `BRA.W aa9d6` (FLOW_ONLY)
- `aa9c0`: `MOVE.W #10b,20(A6); MOVEA.L #acbfe,A1; MOVE.W #100,D0; JSR 49f8c.L` (A0는 바꾸지 않는다)
- `aa9d6`: `MOVEA.L #ab0b8,A0; MOVE.W #a,D0; JSR 28ae.L`
- `aa9e6`: `MOVE.L #aa9ec,(A6)` (→`aa9ec`)
- `aa9ec` (설치 callback): `JSR 4be06.L` (FLOW_ONLY)
- `aa9f2`: `JSR 49fc6.L` (FLOW_ONLY)
- `aa9f8`: `LEA aa8ba(PC),A0; JSR 1ab02.L` (FLOW_ONLY)
- `aaa02`: `BCC.W aaa16` (→`aaa06`; 소비자, `1ab02` 반환 C)
- `aaa06`: `BSET.B #7,61(A6); CLR.W 54(A6); JMP 2a00.L`
- `aaa16`: `RTS` (FLOW_ONLY)

**`ab0b8`/`ab02a` 35** (`aa9d6`이 만든 `28ae` 자식; 설치 `ab17a`, 설치 값 `ab226`; 진입 `ab11a`는 미연결 `ab322`의 설치 값)
- `ab02a`: `MOVEA.L c(A6),A0; BTST.B #7,61(A0); BEQ.W ab066` (→`ab038`; FLOW_ONLY)
- `ab038`: `MOVEA.L #ab424,A0; MOVE.W #a,D0; MOVEA.L #100bf4,A1; JSR 2986.L`
- `ab04e`: `MOVEQ #0,D0; MOVEQ #0,D1; JSR 4970a.L` (경계 callee)
- `ab058`: `ADDQ.W #1,68(A0); ADDQ.W #1,1e(A0); JMP 2a00.L` (A0는 `4970a` 뒤 live 값)
- `ab066`: `JSR 288c.L` (FLOW_ONLY)
- `ab06c`: `BCS.W ab076` (→`ab070`; 소비자, `288c` 반환 C)
- `ab070`: `JMP 2a00.L` (FLOW_ONLY)
- `ab076`: `RTS` (FLOW_ONLY)
- `ab0b8`: `MOVEA.L c(A6),A0; TST.W 92(A0); BNE.W ab0d0` (→`ab0c4`)
- `ab0c4`: `MOVE.W #c,88(A6); MOVEQ #-14,D0; BRA.W ab0d8`
- `ab0d0`: `MOVE.W #4,88(A6); MOVEQ #14,D0` (→`ab0d8`)
- `ab0d8`: `MOVEQ #14,D1; JSR 49290.L`
- `ab0e0`: `MOVE.W #c2c,D0; MOVE.B #0,D1; JSR 8ebe.L`
- `ab0ee`: `MOVE.W #c2e,D0; JSR 4a496.L`
- `ab0f8`: `BSET.B #6,15(A6); MOVEA.L c(A6),A0; MOVE.W 68(A0),68(A6); MOVE.W 1e(A0),1e(A6); ADDI.W #100,68(A6); ADDI.W #100,1e(A6)` (→`ab11a`)
- `ab11a` (설치 callback 진입): `MOVEA.L c(A6),A0; TST.W 92(A0); BNE.W ab130` (→`ab126`)
- `ab126`: `MOVE.W #c,84(A6); BRA.W ab136`
- `ab130`: `MOVE.W #4,84(A6)` (→`ab136`)
- `ab136`: `MOVE.W #2,80(A6); MOVE.W #1,D0; ADD.W 88(A6),D0;` anim-index(`12a`, `2000b8`) (복귀 `ab174`)
- `ab174`: `MOVE.L #ab17a,(A6)` (→`ab17a`)
- `ab17a` (설치 callback): `SUBQ.W #1,80(A6); BNE.W ab1ba` (→`ab182`)
- `ab182`: `MOVE.W #2,80(A6); MOVE.W 88(A6),D0; MOVE.W 84(A6),D1; SUB.W D0,D1; BEQ.W ab1ba; BLT.W ab1a2` (→`ab19a`; 묶인 Bcc, SUB의 Z와 N⊕V)
- `ab19a`: `CMPI.W #10,D1; BRA.W ab1a6;` [`ab1a6`] `BLT.W ab1b0` (→`ab1aa`; 묶음, 이 CMPI의 N⊕V)
- `ab1a2`: `CMPI.W #fff0,D1;` [`ab1a6`] `BLT.W ab1b0` (→`ab1aa`; 묶음, 이 CMPI의 N⊕V)
- `ab1aa`: `SUBQ.W #1,D0; BRA.W ab1b2`
- `ab1b0`: `ADDQ.W #1,D0` (→`ab1b2`)
- `ab1b2`: `ANDI.W #1f,D0; MOVE.W D0,88(A6)` (→`ab1ba`)
- `ab1ba`: `JSR 43e34.L` (FLOW_ONLY)
- `ab1c0`: `JSR 4a46c.L` (FLOW_ONLY)
- `ab1c6`: `JSR 49fc6.L` (FLOW_ONLY; 반환 C는 다음 `TST.W`가 덮는다)
- `ab1cc`: `LEA 26(A6),A0; TST.W 4(A0); BNE.W ab210` (→`ab1d8`; WORD `2a(A6)`)
- `ab1d8`: `MOVE.W #1,D0; ADD.W 88(A6),D0;` anim-index(`12a`, `2000b8`) (복귀 `ab210`)
- `ab210`: `MOVEA.L c(A6),A0; TST.B 62(A0); BEQ.W ab222` (→`ab21c`)
- `ab21c`: `MOVE.L #ab226,(A6)` (→`ab222`; 고아 설치 값)
- `ab222`: `BRA.W ab02a` (FLOW_ONLY)

**`eb752`/`eb766` 4** (interpreter 명령 callback 표 `4a6dc`의 처리기; interpreter가 live 대상 `JSR (An)`으로 부른다)
- `eb752`: `MOVEA.L (A0),A0; JSR 4b82e.L` (FLOW_ONLY; LONG (A0)를 live bus로 읽음; N03 경계 callee)
- `eb75a`: `RTS` (FLOW_ONLY)
- `eb766`: `MOVEA.L #0,A0; JSR 4b82e.L` (FLOW_ONLY)
- `eb772`: `RTS` (FLOW_ONLY)

수: `4a46c` 5 + `4bc04` 6 + `6feb4`/`70036` 59 + `71c90` 10 + `72a18` 49 + `72c72`/`72ce4` 18 + `72d42` 4 + `72dd2` 16 + `aa93e` 17 + `ab02a`/`ab0b8` 35 = 223(`starts.txt`와 같다; 한 줄에 두 block을 적은 곳은 각각 센다).

## 구현 범위와 규약

- routing 11 범위(위 표). 짝수 PC 1,205개 중 block 시작 223, 내부 982(묶인 `ab1a6` 포함). 내부 PC 직접 진입은 `unsupported animation objects n04 PC`다. 범위 이웃은 기존 실행부(interpreter, U14, U08b, U12) 또는 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. `SWAP`은 두 WORD를 바꾼다. `NEG`/`SUB`/`ADD`/`ASR`/`LSL`은 원래 폭의 2의 보수 산술로 계산하고 C++ 부호 있는 shift·overflow에 기대지 않는다(`ASR`는 부호 bit 복제를 명시 구현). 결과 flag는 같은 block 안의 Bcc만 쓴다.
- **FLOW_ONLY 72개**(C 보존): `4bc3e` `6fec8` `6ffae` `6fff0` `70052` `71cc8` `71d2e` `71d34` `71d44` `72a5e` `72a8a` `72ac6` `72af2` `72b2e` `72b5a` `72b96` `72bc2` `72bcc` `72bd6` `72bdc` `72be2` `72bfc` `72c08` `72c0c` `72c18` `72c24` `72c30` `72c3c` `72c46` `72c6e` `72ca2` `72cce` `72cd8` `72ce4` `72cee` `72cf4` `72cf8` `72cfe` `72d04` `72d3e` `72d42` `72d54` `72dd2` `72dd8` `72e3a` `72e3e` `72e42` `72e4c` `72e50` `72e70` `72e7a` `72e8a` `aa986` `aa9bc` `aa9ec` `aa9f2` `aa9f8` `aaa02` `aaa16` `ab02a` `ab066` `ab06c` `ab070` `ab076` `ab1ba` `ab1c0` `ab1c6` `ab222` `eb752` `eb75a` `eb766` `eb772`.
  - JSR/BSR/BRA/JMP/RTS/LEA/MOVEA만인 block, `BTST`/`BSET`/`BCLR`/`BCHG`(+Bcc/BRA) block, `MOVEA`+`ST`+`JMP` `72e50`, 단독 소비자 Bcc 10개.
- **소비자 10개**: `72be2 BCC 72bec`, `72bfc BCS 72c6e`, `72c08 BCS 72c6e`, `72c18 BCC 72c24`, `72c30 BCC 72c3c`, `72c46 BCS 72c50`, `72d04 BCC 72d3e`, `72e4c BCC 72e5e`, `aaa02 BCC aaa16`, `ab06c BCS ab076`. `BCC`는 C Clear면 분기, `BCS`는 C Set이면 분기, Unknown이면 `objects n04 caller requires known carry`.
  - [F] 자연 기록(TB): `72be2`→`72be6`과 `72bec` 둘 다, `72e4c`→`72e50`과 `72e5e` 둘 다, `aaa02`→`aaa16`, `ab06c`→`ab076`이 나타났다. `72bfc` `72c08` `72c18` `72c30` `72c46` `72d04`는 400 frame 안에 실행되지 않는다(typed fixture).
- **known carry 생산 2개**: `4a48a`(Set), `4a490`(Clear). block 안에서 C를 정하고 `RTS`로 돌려준다.
- 그 밖 149 block(`CMPI`+`BLT` `ab19a` `ab1a2` 포함, `MOVE`/`MOVEQ`/`MOVEA`+`TST`/`CLR`/`CMP`/`CMPI`/`ADD`/`ADDI`/`ADDQ`/`SUB`/`SUBI`/`SUBQ`/`NEG`/`ASR`/`LSR`/`LSL`/`ANDI`/`SWAP` block, `MOVE.L #imm,(A6)` block, bank animation block, `ORI`/`ANDI CCR` 앞의 `4a47e` 등)은 Unknown이다. `4bc04`(`4bc3e` RTS는 FLOW_ONLY지만 앞 block이 Unknown), `6feb4`(`70020`), `70036`(`70052`)의 반환 C는 [F] 호출 지점 바로 뒤가 모두 `MOVE`/`MOVEM`+`MOVE`/`CMPI`/`TST`/`LEA`/`BRA`라 소비자가 없어 Unknown으로 둔다.
- 제어 이동은 모두 정적이다(계산 PC 없음). 경계 callee로 가는 `JSR`/`JMP`는 복귀 LONG(JSR)을 쌓고 PC를 그 callee로 둔다. 다음 dispatch에서 실행부가 없으므로 stop이면 멈추고 아니면 `unsupported animation machine PC`로 rollback한다.
- 스택: `JSR`/`BSR`/`RTS` 복귀 LONG만.
- I/O port 쓰기 없음. bank 변경 없음. work RAM 밖 쓰기, 미해결·홀수 읽기는 기존 checked 오류다.

## 자료

- [F] bank window LONG(bank base `200000`에서 실제 PVC bank 모델로 읽음):
  - `2000d0`: anim(`3`, …) 6곳(`71ca0` `72a36` `72a9e` `72b06` `72b6e` `72c7a`; 값 → `22(A6)`, 이어 값 + `1c`/`168`/`16c`/`170`/`174`/`2c`의 LONG → A1)과 `72df2`(값 → A1, 경계 tail 전).
  - `2000d4`: anim(`b`, …) 6곳(`71ccc` `72a62` `72aca` `72b32` `72b9a` `72ca6`; + `1c`/`1b4`/`1b8`/`1bc`/`1c0`/`2c`)과 `72e18`.
  - `200154`: `aa994`(값 + 4).
  - `2000b8`: `ab136` `ab1d8`(값 → `22(A6)`, 같은 LONG + sext(4×(1+WORD `88`))의 LONG → A1).
- [F] work RAM: `5b88(A5)` + sext(`D0.W`) + sext(`D1.W`)의 WORD(`4bc22`; 정상 입력에서 `D0.W`=(x−20)/2&f0, `D1.W`=(y−100)/16&e), WORD `53a2(A5)` `53a6(A5)`(`6ff7c` `6ff96` `7003e`), 선수 node `100cb8` `100da8`(`289e` 입력, BYTE `81(A0)` 읽기).
- [F] node(A6): WORD `1e` `20` `42` `46` `54` `68` `76` `78` `80` `84` `88` `8c` `90` `92` `96` `98` `9a` `9c`, LONG `0`(설치·복원) `22` `36` `3a` `64` `8e` `92` `9e`, BYTE `15`(bit 0/6/7) `17` `61`(bit 7) `62` `82`(bit 0) `86`. 부모 node(`c(A6)`): BYTE `17`(`4a46c`), `61`(bit 7, `ab02a`), `62`(TST, ST), WORD `68` `1e` `92`. `4970a`가 돌려준 A0의 WORD `68` `1e`(`ab058`). `48502`가 돌려준 D0 D1 D7(`6feb4`).
- [I] `6feb4`는 node 좌표(`42` `46`, LONG `8e` `92`)와 목표(`96` `98` `9a`, 화면 원점 `53a2` `53a6`)로 수평 속도를 끌어당기는 운동 갱신이고, `4bc04`는 화면 격자 RAM 표 조회, `4a46c`는 부모 깜빡임 BYTE `17`의 짝수/홀수 판정으로 보인다. 게임 의미는 미확인이다.

## 의존·경계

- [F] N04 → 기존(모두 routing됨): interpreter `49f8c` `49fc6`(반환 C 소비), stage_event `48502`, stage_area `49a58`, U17 `4bfa4`, readiness `289e`(반환 C 소비), U05 `1ab02`(반환 C 소비) `c6a96`, U01 `4b54e`, U12 `70054`(BRA) `4c0ac`, U08b `4be34`, U11 `4be06`, U18 `4be2c`, cleanup `43e34`, U14 `4a496`, U08 `49290`, U02 `8ebe`, fade_card `28ae` `2a00`(JMP), buffer_cue `2986`, stage_event_ops `288c`(반환 C 소비). 내부 호출: `72e3e BSR 6feb4`, `72c5c JSR 4bc04`, `ab1c0 JSR 4a46c`.
- [F] 실행부 없는 경계: `494c0`(`72c3c`), `4970a`(`ab04e`), `49c38`(`72bf4` `72c00`), `4bb52`(`72d08` `72d1a` `72d26`), `cc778`(`72df2` `72e18` JMP), N03 `4b82e`(`eb752` `eb766`). 시험은 이 PC의 stop 성립만 확인한다(F4 시험 경계 관례).
- [F] 다른 단위 → N04: U12 `70164`(`4bc04`) `7016e`(`70036`) `70544`(`6feb4`)의 경계 호출, U13 `70956` `7096c` `70a4a`의 설치 값(`72a18` `71c90`), U07 `28ae` 자식 표(`aa93e`), interpreter 명령 callback 표 `4a6dc`(`eb752` `eb766`, live 대상 호출).
- [F] U12 `2986` caller-X 제한(buffer_cue 결정 1 선택 A)은 그대로 둔다. N04 `ab038`은 `2986`을 부른다. 차분에서 이 제한이 나오면 보고한다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 223 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 2개, 그 밖 Unknown), 소비자 10개의 Unknown 오류, zero-step, 내부 982 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 경계 callee는 stop만. bank LONG·bank 자료는 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 소비자 C와 `4a46c` 반환 C는 native 분기로 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(진입·설치 callback, `6feb4` 산술 경로, 묶인 `ab19a`/`ab1a2`).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, complete 90 이상(기대 92: +62 63).

## 작업자 검증 기록 (scratch, 확정안 구현)

- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0(결정 3 묶음과 interpreter 허용 목록 반영 뒤). 새 test: `animation machine objects n04: 642 fixtures (20 checked errors, 123 kept C), 223 blocks, 3017 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover`) 같은 출력, 종료 0.
- [F] typed fixture: 223 시작 모두 native fixture로 덮임. 소비자 10개 × C Clear/Set 모두 native 분기와 같음. `4a46c` 생산 C(Set/Clear)는 native SR과 같음(`ab1c0` 경유 포함). `ab19a`/`ab1a2` 직접 진입 각 17건(부호 overflow 경계 `7fff`/`8000`/`800f`/`8010`/`7fef`/`ffef` 포함)은 아무 `D0`/`D1`로 native와 같음. `ab1a6` 직접 진입은 내부 PC 오류(982 내부 PC sweep에 포함). 경계 stop: `494c0` `4970a` `49c38` `4bb52` `cc778` `4b82e`. rollback 탐침은 `10fe70`만.
- [F] 실제 ROM 차분(`realrom/real_n04.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, seed 1·2·3 각 1,500건, `ab19a`/`ab1a2`는 전제 없는 무작위 `D0`/`D1`): 불일치 0/0/0, 223 시작 모두 도달. 의도한 차이는 `ab038 JSR 2986`의 caller-X 제한(`cue wrapper failure requires known caller X`) 31/27/26건뿐이다. interpreter가 실제 `49fc6`/`289e`/`1ab02`/`288c` 뒤 넘긴 C로 소비자 7곳(`72be2` `72c18` `72c30` `72d04` `72e4c` `aaa02` `ab06c`)이 native와 같았다.
- [F] F2 프레임 패스 차분(base, 142 seed): 일치 pass 12,178·node 94,840, 불일치 0, 자연 완주 111(기준 `4f91481`과 같음, 회귀 0, 변화 0).
- [F] RNG 초기화 400 frame 차분: 일치 pass 36,800·node 268,123(기준 36,000·259,677), 불일치 0, `other` 없음, complete 90→92(+62 63, 잃은 것 0). 결정 3 반영 전 구현과 seed별 분류·pass 수가 같다. 다음 미연결: 18 19 96 97 102 103 `c5896`, 26 27 `aa93e` 안의 N03 `4b82e`, 38 39 `c3a7c`, 76 77 98 99 104 105 `708a6`(모두 `checked-current-first-unrouted-PC`).

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] `49c38` `494c0`의 반환 C 의미와 `4bb52` `cc778` `4970a`의 동작은 해당 단위 계약에서 정한다.
3. [U] `eb752`의 A0(LONG을 읽을 주소)는 interpreter 명령 흐름에서 온다. C++는 live bus로 같은 주소를 읽는다.
4. [U] 고아 설치 `71d48` `ab226`과 N15 `71032`의 본문은 N04 밖이다(재범위 결정 3).

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n04/`(`n04blocks.py` block·범위 계산, `n04info.py` 범위 SHA·수, `n04dis.py`, `n04route.py` routing 확인, `n04reach.py` 자연 도달·기대 완주, `n04callers.py` 호출자 다음 명령; 저장소 밖).

- (메인, 2026-10-13) 결정 5a 갱신: 인터프리터 명령 callback의 허용 목록은 제거됐다. 원본 `4a352`/`4a43c` `JSR (A1)`에 거르는 코드가 없으므로 C++도 `am_call(c,A1,…)`로 routing에 맡긴다(홀수는 unaligned, 미연결은 unsupported animation machine PC). `eb752`/`eb766` 개별 허용은 더 이상 필요 없다.
