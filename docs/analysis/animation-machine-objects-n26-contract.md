# 객체 callback F4 N26: N24 `28ae` 자식 6개(`5f24a` `5f25c` `5f760` `5f76c` `5fb0e` `5fb20`)와 설치 callback `5f2c4` `5f7ec` `5fb84` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N26 행(168 block, 누적 3,907, `5f24a..5f4b0` `5f760..5fd04`, callback `5f24a` `5f25c` `5f2c4` `5f760` `5f76c` `5f7ec` `5fb0e` `5fb20` `5fb84`, 경계 callee 없음, bank 1, 미실행 설치 1(+17), 단독 새 seed 없음 — seed 32 33은 N24~N27 사슬이고 `dcf56`(N27)에서 먼저 멈춤; 원 범위 U36 168)이다. 단위 형식과 규약은 N25 계약(`animation-machine-objects-n25-contract.md`, SHA256 `8c201be9a67b4bb9395eed78e2f6bdeda81b5ee9b5ca3217d636e4566281b79e`)과 N24·N28·N29 계약을 따른다. 메인 작업 지시:
- 범위 = N26 행. 수치(168 block, 3,907, 진입, bank, 경계)를 정적 디코드로 다시 확인하고 `5f4b0..5f760` 틈의 정체와 소유를 밝힌다.
- 이전 단위 test가 N26·N27 범위(`5f24a..60506`, `dcf56..dcf6a`)의 PC를 "미연결" 탐침으로 쓴 곳을 모두 RAM PC `10fe00..10fefe`(test마다 기존 `10fexx`와 겹치지 않게)로 옮긴다. 값만 바꾸고 논리는 바꾸지 않는다.
- flag 재계산은 선행이 유일할 때만. N26에는 block 경계를 건너 flag를 읽는 곳이 callee C 소비 7곳뿐이라 재계산이 없다.
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 설치·진입은 넣는다(N26에는 미참조 코드가 없다).
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가). N26에는 RTS 앞 C 생산이 없다.
- 다른 단위 실행부(`animation_machine_interpreter.cpp` 포함)는 고치지 않는다. 기존 실행부의 두 번째 진입 누락은 scratch patch + 결정으로 보고한다(N26에는 없음). DIV 0 제수는 단위 checked 오류(N26에는 DIV가 없다).
- 계산 점프 표는 정적으로 묶고 전부 전사한다(N26에는 점프 표가 없다). WORD 자료 표(`5f4b0` `5f4bc` `5fb06` `5fd04` `5fd0c` `5fd14` `5fd1c`)와 LONG `22` 기준 LONG 표는 live bus 읽기다(결정 4).
- ~220 block을 넘으면 나눈다(N26은 168 block이라 나누지 않는다).

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치·`MOVEA.L #imm,A0`+`JSR 28ae` 자식, 범위 밖에서 참조하는 범위 안 진입)로 정한다. Unicorn TB 분할은 시작이 아니다. 같은 flag를 쓰는 연속 Bcc는 한 block으로 묶는다(N26에는 연속 Bcc가 없다).
- 결정 5(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N25 수용 관례: CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BRA`/`RTS`/Bcc/`ST`)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. `MOVE`/`MOVEQ`/`CLR`/`CMP`/`CMPI`/`ADD`/`ADDQ`/`SUBQ`/`LSL`/`TST`/`BSET` 등이 있는 block은 C를 바꾸며, 블록 밖 소비자가 없으므로 Unknown으로 둔다. `ORI.B #1,CCR` block은 known Set을 둔다(N07 `9c04c`·N14 `a5d64` 관례; 결정 3). 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N26 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`200194`와 LONG `22(A6)`이 가리키는 표)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n26`(HEAD `4497217` = N01~N25·N28·N29a까지 통합, `engine/src/animation_machine.cpp` SHA256 `2f16bea5ed3b4c88b96bd90c009e232f3f16b50f5c9154c4e9cd445cf870d6d8`, routing 규칙 84개, `engine/src/animation_machine_interpreter.cpp` SHA256 `97abb2e1de42cf322e35fa3a66eea3ab633170143ea79e0d525e5ad4e317882f`)을 참조했다. N26 routing 범위의 짝수 PC는 기존 routing에 없다(범위 양끝 이웃 `5f248` `5f4b0` `5f75e` `5fb06` `5fb0c` `5fd04`도 routing 밖). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n26/n26.py`(정적 디코드, `starts.txt` SHA256 `18f414ce33b266d0df2a33c9fd6bbaf887aaa324293d31640973b09c46cbea92`)와 `cls26.py`(분류)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N26 = 168 block**(routing 범위 3개 `5f24a..5f4b0` `5f760..5fb06` `5fb0e..5fd04`, 코드 2,050바이트, 짝수 PC 1,025, 내부 857). 진입 9개(아래)에서 분기·fall-through를 끝까지 따라간 정적 closure이며, 범위 안 명령 449개를 모두 덮는다(미도달 0). 재범위 168과 시작 집합까지 같다.
  - [F] 재범위 "3,907"은 바이트가 아니라 누적 block 열(N25까지 3,739 + 168)이다. 재범위 `5f760..5fd04` 안의 WORD 표 `5fb06..5fb0e`(8바이트)는 코드가 아니라 routing에서 뺀다(N25가 `5ea38` 표를 뺀 것과 같은 관례; 결정 1).
- [F] 진입:
  - N24 `28ae` 자식 값(N24 `5dfa0`~`5dff0`이 `MOVEA.L #x,A0; JSR 28ae`로 넘김): `5f24a` `5f25c` `5f760` `5f76c` `5fb0e` `5fb20`. 범위 밖 다른 참조 없음(`5f800`·`5f8ea`와 같은 값의 LONG은 좌표 자료 `240ce` `2e1d6` `591e4` `d72aa` 등이고 시작이 아니다).
  - 범위 안 설치(fall-through): `5f2c4`(`5f2be`), `5f7ec`(`5f7e6`), `5fb84`(`5fb7e`).
  - 공유 callback `5e8b0`(N25) 설치: `5f34e` `5f85a` `5fc6a MOVE.L #5e8b0,(A6)`. 실행 PC가 아니라 노드 LONG 자료다.
- [F] **경계 callee 없음.** 부르는 callee 15개(`8ebe` `8ff4` `16ef0` `28ae` `3af8` `3c44` `43e34` `491c4` `49290` `4970a` `49f8c` `49fc6` `4a46c` `4a496` `4ae4a`)가 모두 기존 실행부의 block 시작이다(scratch 검사: 해당 실행부 소스의 `case 0x…:`; 아래 "다른 실행부로 가는 callee"). 레지스터 간접 호출·TRAP·점프 표는 없다. 패치 파일은 없다.
- [F] **`5f4b0..5f760` 틈**(결정 2): `5f4b0..5f504` 자료(WORD 표 `5f4b0`·`5f4bc`는 N26이 읽고, `5f4c8..5f504`는 고아 사슬이 `MOVE.L #5f4e6,56(A6)`으로 넘기는 자료) + `5f504..5f760` = N26 `5f3b4` `5f3da` `5f404` `5f42a`가 `28ae`로 넘기는 자식 `5f504`의 고아 설치 사슬(정적 53 block; 설치 `5f57c` `5f5f2` `5f66a`, `28ae` 자식 `d22e6`(N05), 미연결 callee `4b6f4`, `JMP 2a00`). 재범위 N26 행의 "미실행 설치 1(+17)"이 이 자식이다(17 = 진입부터 첫 설치까지의 1단계 본문). 재범위 어느 행에도 없고 두 기록(RNG 400·base) 어디서도 실행되지 않는다. N26은 `5f504`를 자료로만 넘긴다.
- [F] **carry**: 소비 7 block(`5f394` `5f876` `5fcb4 BCC`: interpreter `49fc6`의 C; `5f3c4` `5f3ea` `5f414` `5f43a BCC`: fade_card `28ae`의 C), known 생산 4(`5f3d6` `5f3fc` `5f426` `5f44c ORI.B #1,CCR` Set, 소비자 없음; 결정 3), FLOW_ONLY 49(소비 7 포함), Unknown 115. 49 + 4 + 115 = 168.
- [F] N/Z 재계산 없음. X·DIVx/MULx·PC 상대 점프 표·레지스터 간접 점프·TRAP·I/O port 쓰기·bank 변경 없음. `SUBQ.W`(메모리 WORD)·`CMP`/`CMPI`/`TST`의 flag는 같은 block의 Bcc만 읽는다.
- [F] 스택: JSR 복귀 LONG만(push/pop 없음). RTS 12곳(`5f386` `5f4ae` `5f86e` `5f9f8` `5fa66` `5fab4` `5fb02` `5fb04` `5fc8c` `5fc9c` `5fca6` `5fd02`).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `seen26.py`): 두 기록 모두 seed 32 33만 N26 범위를 실행한다. callback 실행 수(seed별): `5f24a` `5f25c` `5f760` `5f76c` `5fb0e` `5fb20` 각 1, `5f2c4` `5f7ec` `5fb84` 각 162. 실행된 범위 안 TB 시작은 52개(초기화 사슬 전부, `5f2c4` `5f33a` `5f354` `5f35a` `5f37e` `5f386`, `5f7ec` `5f7fc` `5f838` `5f84a` `5f860` `5f866` `5f86e`, `5fb84` `5fb94` `5fba0` `5fbd8` `5fbdc` `5fc14` `5fc70` `5fc76` `5fc82` `5fc8c` `5fc8e` `5fc92` `5fc9c` `5fc9e` `5fca6`)이다(부모 BYTE `76` ≠ 1, BYTE `79` = 0 경로). `5f2d4` 이후 발사 상태, `49fc6` C 소비 뒤, `28ae` 자식 `5f504`, `5f9ea` 이후, `5fca8` 이후는 실행되지 않는다. `5f4b0..5f760` 틈은 TB 0개다.
- [F] 기준(`4497217`)에서 seed 32 33은 frame 0 callback `dcf56`(N27 범위)에서 먼저 멈춘다. [I] N26만으로는 RNG·base 완주 수가 늘지 않는다(재범위 표의 N26 행 132/133 그대로). 검증은 실제 ROM 차분과 fixture가 맡는다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 168 block, routing 3 범위.** [F] 정적 디코드 시작 집합이 재범위 168과 같다. 재범위 `5f760..5fd04`는 WORD 표 `5fb06..5fb0e`(`ffff ffff ffff 003b`)를 품으므로 routing을 `5f760..5fb06`·`5fb0e..5fd04`로 나눈다(표 PC는 `unsupported animation machine PC`). 재범위 "3,907"은 누적 block 수다(바이트 아님; 코드 2,050바이트).
2. **`5f4b0..5f760` 틈과 고아 사슬.** [F] 위 요약대로 자료 84바이트 + 고아 `28ae` 자식 사슬 `5f504..5f760`(53 block, 전 바이트가 명령으로 디코드됨, 미도달 0)이다. 어느 단위도 소유하지 않는다. [U] 소유 단위 미정(N25 결정 2의 `5eed2..5efe6`과 같은 고아 설치 정리 단계 후보). 미연결 callee `4b6f4`를 부르므로 그 단계에서 함께 다뤄야 한다. 400 frame 안에 실행되지 않는다. 이번 탐침 이동에서 이 틈(`5f4c0` `5f4c2` `5f4c4` `5f500` `5f712`)도 RAM으로 옮겼다(결정 7).
3. **`ORI.B #1,CCR` 4 block = known Set.** [F] `5f3d6` `5f3fc` `5f426` `5f44c`는 `28ae` Set 뒤 `4970a` 복귀점의 `ORI.B #1,CCR` 단독 block이다. 뒤 block(`5f3da` `5f42a`: `MOVE.W #a,D0`가 C를 지움, `5f400 BRA`(FLOW) → `5f450 SUBQ`, `5f450 SUBQ`)이 모두 C를 다시 쓰므로 소비자는 없다. N07(`9c04c` `9c07a`)·N14(`a5d64` 외) 관례대로 실행부가 known Set을 둔다(N15 `76f50` `76f92`는 Unknown으로 둔 선례; 어느 쪽이든 관측 결과는 같다). 소비자가 없으므로 이 C에 대한 오류 문자열은 없다.
4. **자료 표(live bus).** [F] 점프 표가 아니므로 전사하지 않고 `am_read`로 읽는다. 색인 검사는 원본처럼 없다.
   - `5f4b0` WORD 6개(`0072 0074 0076 0078 0079 0000`, SHA256 `e9f89072…`)·`5f4bc` WORD 6개(`007a 007c 007e 0080 0081 0000`, SHA256 `2f55f78e…`): `5f314 MOVE.W (A0),D0`은 첫 WORD만 읽는다. `5f478`은 `D0` = 0, `D0.B` = BYTE `77`, `ADD.B D0,D0`(BYTE 덧셈: 색인 = (2·BYTE `77`) & `ff`, 0..254), `D0.W` = WORD(A0 + 색인)이다. 0이면 `5f488`.
   - `5fb06` WORD 4개(`ffff ffff ffff 003b`, SHA256 `64ce1d49…`): `5f7fc` 색인 2·BYTE `76`(`ADD.W`, 0..510).
   - `5fd04`(`ffff ffff ffff 0051`, SHA256 `b55848c3…`)·`5fd0c`(`ffff ffff ffff 0055`, SHA256 `f19522a2…`): `5fba0`/`5fbdc` 색인 2·BYTE `76`(`ADD.W`). `ffff`이면 BYTE `79` = 0.
   - `5fd14`(`0051 0052 0054 0000`, SHA256 `4ce864a0…`)·`5fd1c`(`0055 0056 0058 0000`, SHA256 `b8478a9a…`): `5fcd0` 색인 (2·BYTE `77`) & `ff`(`ADD.B`). 0이면 `5fce0`(BYTE `77` = 0, BYTE `79` = 0) 뒤 같은 `D0.W` = 0으로 `5fcea`.
   - 큰 색인은 범위 밖 ROM(다음 표·N27 코드 바이트)을 그대로 읽는다(원본과 같음).
5. **bank 읽기.** [F] `5f2ac` `5f7ac` `5f8a8` `5f908` `5f968` `5f9b8` `5fa3e` `5fa8c` `5fada` `5fb70 MOVE.L 200194.l,22(A6)`(id `18b`, banked LONG; 재범위 "bank 1" = 주소 1개). 이어서 LONG `22`를 기준으로 LONG을 읽는다: `ec`(`5f7ac` `5f9b8`), `f0`(`5f8a8`), `f8`(`5f908`), `100`(`5f968`), `f4`(`5fa3e`), `fc`(`5fa8c`), `104`(`5fada`), `120`(`5fc32`), `124`(`5fc4c`), 4·WORD 표 값(`5f314` `5f496` `5f81c` `5fbbc` `5fbf8` `5fcea`). 색인 LONG 읽기는 `(A1,Dn.W)`(16 bit 부호 확장)다. 모두 live bus(현재 PVC bank 모델)다.
6. **callee C 소비 7곳.** [F] 모두 callee가 RTS로 돌려준 C를 읽고, Unknown C면 `objects n26 caller requires known carry`(상태 보존)다.
   - `5f394` `5f876` `5fcb4 BCC`(interpreter `49fc6`): N20·N25 계약과 같은 interpreter 끝의 known C. Clear면 RTS(`5f4ae`) / `5f9ea` / RTS(`5fd02`).
   - `5f3c4` `5f3ea` `5f414` `5f43a BCC`(fade_card `28ae`): `2908 ORI` Set(자리 있음) → `4970a`로 자식 위치 지정 뒤 `ORI CCR`; `290e ANDI` Clear(자리 없음) → 건너뜀.
   - [F] 실제 생산자를 따라간 native 분기로 확인한다(검증 기록).
7. **무효화 탐침 — 다른 test 17개 수정.** [F] 기존 test가 "어느 단위에도 없는 미연결 PC"로 쓴 값 중 N26·N27 범위(`5f24a..60506`, `dcf56..dcf6a`, 사이의 `5f4b0..5f760` 틈과 `5fd04..5fd24` 표 포함) 안의 것을 RAM PC로 옮겼다(값과 그 값을 적은 주석만; 논리 변경 없음). `dcf56..dcf6a` 탐침은 없었다. 목록은 검증 기록에 적는다. [F] 남은 이 범위 값(`objects_n24` test의 `28ae` 자식 LONG `5f24a`~`6041e`, `objects_n25` test의 자기 범위·표 `5f202`~`5f248`, `objects_u04`·`u20`·`n24`·`n29` 등의 레지스터·자료 값 `5ffff` `60000`~`60302`, `buffer_cue` 등의 `60000`)은 탐침이 아니다. `tools/*.py`에는 이 범위 PC를 탐침으로 쓰는 곳이 없다(`60000`은 무작위 레지스터 후보값).
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n26.cpp`의 `animation_objects_n26_block`. 오류는 `unsupported animation objects n26 PC`(내부 PC), `objects n26 caller requires known carry`(소비 7 block).

## 원본 바이트 근거

[F] N26 코드 3 범위 2,050바이트(짝수 PC 1,025개, 시작 168, 내부 857). 연결 SHA256 `8e494fddf6bdbd754aedf5fefc7ed36b8627b4044caa7ea107445a7bc172de35`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `5f24a..5f4b0` | 614 | `fcd82c25c5fe99af786998e18cd77775ff44b5193da5ee83da6a8705ada2e5f9` | 61 |
| `5f760..5fb06` | 934 | `45bad26e3ac3dd7950605cb85a554c157ec643b75f0a5e392b3bc1bb7d1272e9` | 64 |
| `5fb0e..5fd04` | 502 | `a2a217bfbbb52a000c58eca135833980b0fce30ee27939770c96727ac2d6be9f` | 43 |

- [F] 범위 이웃(모두 routing 밖): `..5f24a`(N25 끝 표 `5f23a..5f24a`), `5f4b0..5f504`(자료 84바이트, SHA256 `d9907b24…`; 결정 2·4), `5f504..5f760`(고아 사슬 604바이트, SHA256 `34bbf431…`; 결정 2), `5fb06..5fb0e`(표, 결정 1), `5fd04..5fd24`(표 5개), `5fd24..`(N27 `28ae` 자식 `5fd24`).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "known Set 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(A6)·`(An,Dn.W)`는 부호 확장한다.

**`28ae` 자식 `5f24a`/`5f25c`(N24 `5dfa0`/`5dfb0`; BYTE `78` = 0/1, 초기화, bank LONG `200194`, 끝 `5f2be` 설치 `5f2c4` fall-through) 8**
- `5f24a`: `MOVE.B #0, 78(a6); MOVE.W #0, d0; MOVE.W #0, d1; BRA.W 5f26a`
- `5f25c`: `MOVE.B #1, 78(a6); MOVE.W #0, d0; MOVE.W #0, d1` (→`5f26a`)
- `5f26a`: `JSR 49290.l` — FLOW
- `5f270`: `JSR 491c4.l` — FLOW
- `5f276`: `MOVE.B #ff, 76(a6); MOVE.W #d5e, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5f28a`: `MOVE.W #d62, d0; JSR 4a496.l`
- `5f294`: `BSET.B #6, 15(a6); MOVE.W #804, 68(a6); MOVE.W #804, 1e(a6); JSR 16ef0.l`
- `5f2ac`: `MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); CLR.B 62(a6); MOVE.L #5f2c4, (a6)` (→`5f2c4`)

**설치 callback `5f2c4`(부모 BYTE `76` = 1·부모 BYTE `77` = 2 발사 상태, 표 `5f4b0`/`5f4bc`, 부모 BYTE `63` → 설치 `5e8b0`, `7e` 계수, `49fc6` C → `3af8`·`28ae` 자식 `5f504` 2개) 53**
- `5f2c4`: `MOVEA.L c(a6), a0; MOVE.B 76(a0), d0; CMPI.B #1, d0; BNE.W 5f33a` (→`5f2d4`)
- `5f2d4`: `CMPI.B #2, 77(a0); BNE.W 5f332` (→`5f2de`)
- `5f2de`: `TST.B 62(a6); BNE.W 5f32e` (→`5f2e6`)
- `5f2e6`: `ST.B 62(a6); ST.B 79(a6); MOVE.B #0, 77(a6); MOVE.W #6, 80(a6); MOVE.W #0, 7e(a6); TST.B 78(a6); BNE.W 5f310` (→`5f308`)
- `5f308`: `LEA.L 5f4b0(pc), a0; BRA.W 5f314` — FLOW
- `5f310`: `LEA.L 5f4bc(pc), a0` (→`5f314`) — FLOW
- `5f314`: `MOVE.W (a0), d0; LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5f32e`: `BRA.W 5f336` — FLOW
- `5f332`: `CLR.B 79(a6)` (→`5f336`)
- `5f336`: `BRA.W 5f33e` — FLOW
- `5f33a`: `CLR.B 79(a6)` (→`5f33e`)
- `5f33e`: `MOVEA.L c(a6), a0; TST.B 63(a0); BEQ.W 5f354` (→`5f34a`)
- `5f34a`: `CLR.B 79(a6); MOVE.L #5e8b0, (a6)` (→`5f354`)
- `5f354`: `JSR 43e34.l` — FLOW
- `5f35a`: `TST.W 7e(a6); BEQ.W 5f37e` (→`5f362`)
- `5f362`: `SUBQ.W #1, 7e(a6); BNE.W 5f37e` (→`5f36a`)
- `5f36a`: `MOVEA.L c(a6), a0; MOVE.B #1, 62(a0); MOVE.B #0, 77(a6); CLR.B 62(a6)` (→`5f37e`)
- `5f37e`: `TST.B 79(a6); BNE.W 5f388` (→`5f386`)
- `5f386`: `RTS` — FLOW
- `5f388`: `JSR 4a46c.l` — FLOW
- `5f38e`: `JSR 49fc6.l` — FLOW
- `5f394`: `BCC.W 5f4ae` (→`5f398`) — C 소비, FLOW
- `5f398`: `CMPI.B #2, 77(a6); BNE.W 5f460` (→`5f3a2`)
- `5f3a2`: `MOVE.W #1a9f, d0; JSR 3af8.l`
- `5f3ac`: `TST.B 78(a6); BNE.W 5f404` (→`5f3b4`)
- `5f3b4`: `MOVEA.L #5f504, a0; MOVE.W #a, d0; JSR 28ae.l`
- `5f3c4`: `BCC.W 5f3da` (→`5f3c8`) — C 소비, FLOW
- `5f3c8`: `MOVE.W #ffc0, d0; MOVE.W #ffea, d1; JSR 4970a.l`
- `5f3d6`: `ORI.B #1, ccr` (→`5f3da`) — known Set 생산
- `5f3da`: `MOVEA.L #5f504, a0; MOVE.W #a, d0; JSR 28ae.l`
- `5f3ea`: `BCC.W 5f400` (→`5f3ee`) — C 소비, FLOW
- `5f3ee`: `MOVE.W #ffc0, d0; MOVE.W #ffe0, d1; JSR 4970a.l`
- `5f3fc`: `ORI.B #1, ccr` (→`5f400`) — known Set 생산
- `5f400`: `BRA.W 5f450` — FLOW
- `5f404`: `MOVEA.L #5f504, a0; MOVE.W #a, d0; JSR 28ae.l`
- `5f414`: `BCC.W 5f42a` (→`5f418`) — C 소비, FLOW
- `5f418`: `MOVE.W #ffc0, d0; MOVE.W #30, d1; JSR 4970a.l`
- `5f426`: `ORI.B #1, ccr` (→`5f42a`) — known Set 생산
- `5f42a`: `MOVEA.L #5f504, a0; MOVE.W #a, d0; JSR 28ae.l`
- `5f43a`: `BCC.W 5f450` (→`5f43e`) — C 소비, FLOW
- `5f43e`: `MOVE.W #ffc0, d0; MOVE.W #3a, d1; JSR 4970a.l`
- `5f44c`: `ORI.B #1, ccr` (→`5f450`) — known Set 생산
- `5f450`: `SUBQ.W #1, 80(a6); BCC.W 5f45c` (→`5f458`)
- `5f458`: `ADDQ.B #1, 77(a6)` (→`5f45c`)
- `5f45c`: `BRA.W 5f464` — FLOW
- `5f460`: `ADDQ.B #1, 77(a6)` (→`5f464`)
- `5f464`: `TST.B 78(a6); BNE.W 5f474` (→`5f46c`)
- `5f46c`: `LEA.L 5f4b0(pc), a0; BRA.W 5f478` — FLOW
- `5f474`: `LEA.L 5f4bc(pc), a0` (→`5f478`) — FLOW
- `5f478`: `MOVEQ #0, d0; MOVE.B 77(a6), d0; ADD.B d0, d0; MOVE.W (a0, d0.w), d0; BNE.W 5f496` (→`5f488`)
- `5f488`: `CLR.B 79(a6); MOVE.W #78, 7e(a6); BRA.W 5f4ae`
- `5f496`: `LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5f4ae`: `RTS` — FLOW

**`28ae` 자식 `5f760`/`5f76c`(N24 `5dfc0`/`5dfd0`; `D1.W` = `a8`/0, 초기화, bank LONG `200194`, 끝 `5f7e6` 설치 `5f7ec` fall-through) 8**
- `5f760`: `MOVE.W #ffe0, d0; MOVE.W #a8, d1; BRA.W 5f774`
- `5f76c`: `MOVE.W #ffe0, d0; MOVE.W #0, d1` (→`5f774`)
- `5f774`: `JSR 49290.l` — FLOW
- `5f77a`: `JSR 491c4.l` — FLOW
- `5f780`: `MOVE.B #ff, 76(a6); MOVE.W #d4e, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5f794`: `BSET.B #6, 15(a6); MOVE.W #802, 68(a6); MOVE.W #802, 1e(a6); JSR 16ef0.l`
- `5f7ac`: `MOVE.W #3c, 7e(a6); MOVE.W #0, 80(a6); MOVE.B #0, 77(a6); LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L ec(a1), a1; JSR 49f8c.l`
- `5f7e6`: `MOVE.L #5f7ec, (a6)` (→`5f7ec`)

**설치 callback `5f7ec`(부모 BYTE `76` 추종, 표 `5fb06`, 부모 BYTE `63` → 설치 `5e8b0`, `49fc6` C → BYTE `77` 0~3 단계, 부모 BYTE `77` ≥ 2 → LONG `72` `4ae4a`, `7e` 계수 단계 전환) 56**
- `5f7ec`: `MOVEA.L c(a6), a0; MOVE.B 76(a0), d0; CMP.B 76(a6), d0; BEQ.W 5f84a` (→`5f7fc`)
- `5f7fc`: `MOVE.B d0, 76(a6); LEA.L 5fb06(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 5f838` (→`5f81c`)
- `5f81c`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5f838`: `MOVE.W #3c, 7e(a6); MOVE.W #0, 80(a6); MOVE.B #0, 77(a6)` (→`5f84a`)
- `5f84a`: `MOVEA.L c(a6), a0; TST.B 63(a0); BEQ.W 5f860` (→`5f856`)
- `5f856`: `CLR.B 79(a6); MOVE.L #5e8b0, (a6)` (→`5f860`)
- `5f860`: `JSR 43e34.l` — FLOW
- `5f866`: `TST.B 79(a6); BNE.W 5f870` (→`5f86e`)
- `5f86e`: `RTS` — FLOW
- `5f870`: `JSR 49fc6.l` — FLOW
- `5f876`: `BCC.W 5f9ea` (→`5f87a`) — C 소비, FLOW
- `5f87a`: `CMPI.B #0, 77(a6); BNE.W 5f8d0` (→`5f884`)
- `5f884`: `MOVE.W #1acb, d0; JSR 3af8.l`
- `5f88e`: `MOVE.W #1e, 7e(a6); JSR 8ff4.l`
- `5f89a`: `MOVE.W #d4e, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5f8a8`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L f0(a1), a1; JSR 49f8c.l`
- `5f8d0`: `CMPI.B #1, 77(a6); BNE.W 5f930` (→`5f8da`)
- `5f8da`: `MOVE.W #1acb, d0; JSR 3c44.l`
- `5f8e4`: `MOVE.W #1acc, d0; JSR 3af8.l`
- `5f8ee`: `MOVE.W #1e, 7e(a6); JSR 8ff4.l`
- `5f8fa`: `MOVE.W #d4e, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5f908`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L f8(a1), a1; JSR 49f8c.l`
- `5f930`: `CMPI.B #2, 77(a6); BNE.W 5f99a` (→`5f93a`)
- `5f93a`: `MOVE.W #1acc, d0; JSR 3c44.l`
- `5f944`: `MOVE.W #1acd, d0; JSR 3af8.l`
- `5f94e`: `MOVE.W #78, 7e(a6); JSR 8ff4.l`
- `5f95a`: `MOVE.W #d53, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5f968`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 100(a1), a1; JSR 49f8c.l`
- `5f990`: `MOVEA.L c(a6), a0; MOVE.B #1, 62(a0)` (→`5f99a`)
- `5f99a`: `CMPI.B #3, 77(a6); BNE.W 5f9ea` (→`5f9a4`)
- `5f9a4`: `JSR 8ff4.l` — FLOW
- `5f9aa`: `MOVE.W #d4e, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5f9b8`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L ec(a1), a1; JSR 49f8c.l`
- `5f9e0`: `MOVEA.L c(a6), a0; MOVE.B #1, 62(a0)` (→`5f9ea`)
- `5f9ea`: `MOVEA.L c(a6), a0; CMPI.B #2, 77(a0); BGE.W 5f9fa` (→`5f9f8`)
- `5f9f8`: `RTS` — FLOW
- `5f9fa`: `MOVE.L 72(a6), d0; BEQ.W 5fa0a` (→`5fa02`)
- `5fa02`: `MOVEA.L d0, a0; JSR 4ae4a.l` — FLOW
- `5fa0a`: `TST.W 7e(a6); BEQ.W 5fb04` (→`5fa12`)
- `5fa12`: `SUBQ.W #1, 7e(a6); BNE.W 5fb04` (→`5fa1a`)
- `5fa1a`: `CMPI.B #0, 77(a6); BNE.W 5fa68` (→`5fa24`)
- `5fa24`: `MOVE.B #1, 77(a6); JSR 8ff4.l`
- `5fa30`: `MOVE.W #d4e, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5fa3e`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L f4(a1), a1; JSR 49f8c.l`
- `5fa66`: `RTS` — FLOW
- `5fa68`: `CMPI.B #1, 77(a6); BNE.W 5fab6` (→`5fa72`)
- `5fa72`: `MOVE.B #2, 77(a6); JSR 8ff4.l`
- `5fa7e`: `MOVE.W #d52, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5fa8c`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L fc(a1), a1; JSR 49f8c.l`
- `5fab4`: `RTS` — FLOW
- `5fab6`: `CMPI.B #2, 77(a6); BNE.W 5fb04` (→`5fac0`)
- `5fac0`: `MOVE.B #3, 77(a6); JSR 8ff4.l`
- `5facc`: `MOVE.W #d54, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5fada`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 104(a1), a1; JSR 49f8c.l`
- `5fb02`: `RTS` — FLOW
- `5fb04`: `RTS` — FLOW

**`28ae` 자식 `5fb0e`/`5fb20`(N24 `5dfe0`/`5dff0`; BYTE `78` = 0/1, 초기화, bank LONG `200194`, 끝 `5fb7e` 설치 `5fb84` fall-through) 8**
- `5fb0e`: `MOVE.B #0, 78(a6); MOVE.W #0, d0; MOVE.W #0, d1; BRA.W 5fb2e`
- `5fb20`: `MOVE.B #1, 78(a6); MOVE.W #0, d0; MOVE.W #0, d1` (→`5fb2e`)
- `5fb2e`: `JSR 49290.l` — FLOW
- `5fb34`: `JSR 491c4.l` — FLOW
- `5fb3a`: `MOVE.B #ff, 76(a6); MOVE.W #d4b, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5fb4e`: `MOVE.W #d56, d0; JSR 4a496.l`
- `5fb58`: `BSET.B #6, 15(a6); MOVE.W #802, 68(a6); MOVE.W #802, 1e(a6); JSR 16ef0.l`
- `5fb70`: `MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.L #5fb84, (a6)` (→`5fb84`)

**설치 callback `5fb84`(부모 BYTE `76` 추종, 표 `5fd04`/`5fd0c`, 부모 BYTE `63`·BYTE `76` = 3 → 설치 `5e8b0`, 부모 WORD `46` 대 `180`, `49fc6` C → 표 `5fd14`/`5fd1c`) 35**
- `5fb84`: `MOVEA.L c(a6), a0; MOVE.B 76(a0), d0; CMP.B 76(a6), d0; BEQ.W 5fc14` (→`5fb94`)
- `5fb94`: `MOVE.B d0, 76(a6); TST.B 78(a6); BNE.W 5fbdc` (→`5fba0`)
- `5fba0`: `LEA.L 5fd04(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 5fbd8` (→`5fbbc`)
- `5fbbc`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5fbd8`: `BRA.W 5fc14` — FLOW
- `5fbdc`: `LEA.L 5fd0c(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 5fc14` (→`5fbf8`)
- `5fbf8`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5fc14`: `MOVEA.L c(a6), a0; TST.B 63(a0); BEQ.W 5fc70` (→`5fc20`)
- `5fc20`: `CMPI.B #3, 76(a6); BNE.W 5fc66` (→`5fc2a`)
- `5fc2a`: `TST.B 78(a6); BNE.W 5fc4c` (→`5fc32`)
- `5fc32`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 120(a1), a1; JSR 49f8c.l`
- `5fc48`: `BRA.W 5fc62` — FLOW
- `5fc4c`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 124(a1), a1; JSR 49f8c.l`
- `5fc62`: `BRA.W 5fc6a` — FLOW
- `5fc66`: `CLR.B 79(a6)` (→`5fc6a`)
- `5fc6a`: `MOVE.L #5e8b0, (a6)` (→`5fc70`)
- `5fc70`: `JSR 43e34.l` — FLOW
- `5fc76`: `MOVEA.L c(a6), a0; TST.B 78(a6); BNE.W 5fc92` (→`5fc82`)
- `5fc82`: `CMPI.W #180, 46(a0); BLE.W 5fc8e` (→`5fc8c`)
- `5fc8c`: `RTS` — FLOW
- `5fc8e`: `BRA.W 5fc9e` — FLOW
- `5fc92`: `CMPI.W #180, 46(a0); BGE.W 5fc9e` (→`5fc9c`)
- `5fc9c`: `RTS` — FLOW
- `5fc9e`: `TST.B 79(a6); BNE.W 5fca8` (→`5fca6`)
- `5fca6`: `RTS` — FLOW
- `5fca8`: `JSR 4a46c.l` — FLOW
- `5fcae`: `JSR 49fc6.l` — FLOW
- `5fcb4`: `BCC.W 5fd02` (→`5fcb8`) — C 소비, FLOW
- `5fcb8`: `ADDQ.B #1, 77(a6); TST.B 78(a6); BNE.W 5fccc` (→`5fcc4`)
- `5fcc4`: `LEA.L 5fd14(pc), a0; BRA.W 5fcd0` — FLOW
- `5fccc`: `LEA.L 5fd1c(pc), a0` (→`5fcd0`) — FLOW
- `5fcd0`: `MOVEQ #0, d0; MOVE.B 77(a6), d0; ADD.B d0, d0; MOVE.W (a0, d0.w), d0; BNE.W 5fcea` (→`5fce0`)
- `5fce0`: `MOVE.B #0, 77(a6); CLR.B 79(a6)` (→`5fcea`)
- `5fcea`: `LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5fd02`: `RTS` — FLOW

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다; WORD 산술은 16 bit 2의 보수, `.W`/`.B`는 나머지 bit 보존):
  - 애니메이션 인자(`MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c`): `D0.W` = `100`, A0 = A6 + `26`, A1 = LONG `22`, A1 = LONG(A1 + d), `JSR 49f8c`. 표 꼴(`LSL.W #2,D0; MOVEA.L 22(A6),A1; MOVEA.L (A1,D0.W),A1; …`): `D0.W` = (`D0.W` << 2) & `ffff`, A1 = LONG(LONG `22` + sext(`D0.W`)), 이어서 `D0.W` = `100`, A0 = A6 + `26`. bank 꼴(`5f7ac` `5f8a8` 등): A0 = A6 + `26`, `20.W` = `18b`, LONG `22` = banked LONG `200194`, 이어서 애니메이션 인자.
  - `5f24a`/`5f25c`(자식): BYTE `78` = 0/1, `D0.W` = `D1.W` = 0; `5f26a`: `JSR 49290`; `5f270`: `JSR 491c4`. `5f276`: BYTE `76` = `ff`, `8ebe`(`D0.W` = `d5e`, `D1.B` = 0). `5f28a`: `D0.W` = `d62`, `JSR 4a496`. `5f294`: BYTE `15` |= `40`(읽고 쓰기), `68.W` = `1e.W` = `804`, `JSR 16ef0`. `5f2ac`: `20.W` = `18b`, LONG `22` = banked LONG `200194`, BYTE `62` = 0, `(A6)` = `5f2c4`, fall-through.
  - `5f2c4`(설치): A0 = LONG `c(A6)`(부모), `D0.B` = BYTE `76(A0)`; `D0.B` ≠ 1이면 `5f33a`(BYTE `79` = 0). `5f2d4`: BYTE `77(A0)` ≠ 2이면 `5f332`(BYTE `79` = 0). `5f2de`: BYTE `62` ≠ 0이면 `5f32e`. `5f2e6`: BYTE `62` = `ff`, BYTE `79` = `ff`, BYTE `77` = 0, `80.W` = 6, `7e.W` = 0; BYTE `78` ≠ 0이면 A0 = `5f4bc`(`5f310`), 아니면 `5f4b0`(`5f308`). `5f314`: `D0.W` = WORD(A0)(첫 WORD), 표 꼴 애니메이션(복귀 `5f32e`). `5f32e`→`5f336`→`5f33e`.
  - `5f33e`: A0 = LONG `c`; BYTE `63(A0)` = 0이면 `5f354`. `5f34a`: BYTE `79` = 0, `(A6)` = `5e8b0`. `5f354`: `JSR 43e34`. `5f35a`: `7e.W` = 0이면 `5f37e`. `5f362`: `7e.W` −= 1(메모리 RMW); 결과 ≠ 0이면 `5f37e`. `5f36a`: A0 = LONG `c`, BYTE `62(A0)` = 1, BYTE `77` = 0, BYTE `62` = 0. `5f37e`: BYTE `79` = 0이면 `5f386 RTS`. `5f388`: `JSR 4a46c`. `5f38e`: `JSR 49fc6`. `5f394`: Clear면 `5f4ae RTS`.
  - `5f398`: BYTE `77` ≠ 2이면 `5f460`(BYTE `77` += 1, 메모리 RMW). `5f3a2`: `D0.W` = `1a9f`, `JSR 3af8`. `5f3ac`: BYTE `78` ≠ 0이면 `5f404`. `5f3b4` `5f3da` `5f404` `5f42a`: A0 = `5f504`, `D0.W` = `a`, `JSR 28ae`. 복귀 뒤 C Clear면 다음 `28ae`(`5f3da` `5f42a`) 또는 `5f450`(`5f3ea`→`5f400`, `5f43a`)로, Set이면 `D0.W`/`D1.W` = `ffc0`/`ffea`(`5f3c8`), `ffc0`/`ffe0`(`5f3ee`), `ffc0`/`30`(`5f418`), `ffc0`/`3a`(`5f43e`), `JSR 4970a`, 복귀점 `ORI.B #1,CCR`(known Set). `5f400`: `BRA 5f450`. `5f450`: `80.W` −= 1(메모리 RMW); 빌림(이전 값 0)이면 `5f458`(BYTE `77` += 1). `5f45c`: `BRA 5f464`.
  - `5f464`: BYTE `78` ≠ 0이면 A0 = `5f4bc`(`5f474`), 아니면 `5f4b0`(`5f46c`). `5f478`: `D0` = 0, `D0.B` = BYTE `77`, `D0.B` = (2·`D0.B`) & `ff`(결정 4), `D0.W` = WORD(A0 + `D0.W`); ≠ 0이면 `5f496`(표 꼴 애니메이션, 복귀 `5f4ae RTS`). = 0이면 `5f488`: BYTE `79` = 0, `7e.W` = `78`, `BRA 5f4ae`.
  - `5f760`/`5f76c`(자식): `D0.W` = `ffe0`, `D1.W` = `a8`/0(BYTE `78`은 쓰지 않음); `5f774`: `JSR 49290`; `5f77a`: `JSR 491c4`. `5f780`: BYTE `76` = `ff`, `8ebe`(`d4e`, 0). `5f794`: BYTE `15` |= `40`, `68.W` = `1e.W` = `802`, `JSR 16ef0`. `5f7ac`: `7e.W` = `3c`, `80.W` = 0, BYTE `77` = 0, bank 꼴 애니메이션 `ec`(복귀 `5f7e6`). `5f7e6`: `(A6)` = `5f7ec`, fall-through.
  - `5f7ec`(설치): A0 = LONG `c`, `D0.B` = BYTE `76(A0)`; = BYTE `76(A6)`이면 `5f84a`. `5f7fc`: BYTE `76(A6)` = `D0.B`, A0 = `5fb06`, `D0` = 0, `D0.B` = BYTE `76`, `D0.W` = 2·`D0.W`, `D0.W` = WORD(A0 + sext(`D0.W`)), BYTE `79` = 0, `ffff`이면 `5f838`. `5f81c`: BYTE `79` = `ff`, 표 꼴 애니메이션(복귀 `5f838`). `5f838`: `7e.W` = `3c`, `80.W` = 0, BYTE `77` = 0. `5f84a`: A0 = LONG `c`; BYTE `63(A0)` = 0이면 `5f860`. `5f856`: BYTE `79` = 0, `(A6)` = `5e8b0`. `5f860`: `JSR 43e34`. `5f866`: BYTE `79` = 0이면 `5f86e RTS`. `5f870`: `JSR 49fc6`. `5f876`: Clear면 `5f9ea`.
  - 단계(BYTE `77`은 이 사슬 안에서 바뀌지 않으므로 최대 한 단계만 실행): `5f87a` = 0 → `5f884`(`3af8`(`1acb`), `5f88e` `7e.W` = `1e` + `8ff4`, `5f89a` `8ebe`(`d4e`), `5f8a8` bank 꼴 `f0`, 복귀 `5f8d0`). `5f8d0` = 1 → `5f8da`(`3c44`(`1acb`), `5f8e4` `3af8`(`1acc`), `5f8ee` `7e.W` = `1e` + `8ff4`, `5f8fa` `8ebe`(`d4e`), `5f908` bank 꼴 `f8`, 복귀 `5f930`). `5f930` = 2 → `5f93a`(`3c44`(`1acc`), `5f944` `3af8`(`1acd`), `5f94e` `7e.W` = `78` + `8ff4`, `5f95a` `8ebe`(`d53`), `5f968` bank 꼴 `100`, 복귀 `5f990`: 부모 BYTE `62` = 1). `5f99a` = 3 → `5f9a4`(`8ff4`, `5f9aa` `8ebe`(`d4e`), `5f9b8` bank 꼴 `ec`, 복귀 `5f9e0`: 부모 BYTE `62` = 1).
  - `5f9ea`: A0 = LONG `c`; BYTE `77(A0)` < 2(부호 있는 BYTE)이면 `5f9f8 RTS`. `5f9fa`: `D0` = LONG `72`; 0이면 `5fa0a`. `5fa02`: A0 = `D0`, `JSR 4ae4a`(N08). `5fa0a`: `7e.W` = 0이면 `5fb04 RTS`. `5fa12`: `7e.W` −= 1; ≠ 0이면 `5fb04`. `5fa1a`: BYTE `77` = 0 → `5fa24`(BYTE `77` = 1, `8ff4`, `5fa30` `8ebe`(`d4e`), `5fa3e` bank 꼴 `f4`, `5fa66 RTS`). `5fa68`: = 1 → `5fa72`(= 2, `8ff4`, `5fa7e` `8ebe`(`d52`), `5fa8c` bank 꼴 `fc`, `5fab4 RTS`). `5fab6`: = 2 → `5fac0`(= 3, `8ff4`, `5facc` `8ebe`(`d54`), `5fada` bank 꼴 `104`, `5fb02 RTS`); 아니면 `5fb04 RTS`.
  - `5fb0e`/`5fb20`(자식): BYTE `78` = 0/1, `D0.W` = `D1.W` = 0; `5fb2e`: `JSR 49290`; `5fb34`: `JSR 491c4`. `5fb3a`: BYTE `76` = `ff`, `8ebe`(`d4b`, 0). `5fb4e`: `D0.W` = `d56`, `JSR 4a496`. `5fb58`: BYTE `15` |= `40`, `68.W` = `1e.W` = `802`, `JSR 16ef0`. `5fb70`: `20.W` = `18b`, LONG `22` = banked LONG `200194`, `(A6)` = `5fb84`, fall-through.
  - `5fb84`(설치): 부모 BYTE `76` 추종(`5f7ec`와 같은 꼴); 같으면 `5fc14`. `5fb94`: BYTE `76(A6)` = `D0.B`; BYTE `78` ≠ 0이면 `5fbdc`(표 `5fd0c`), 아니면 `5fba0`(표 `5fd04`): `5f7fc`와 같은 표 꼴(`ffff`이면 `5fbd8`/`5fc14`). `5fbbc`/`5fbf8`: BYTE `79` = `ff`, 표 꼴 애니메이션(복귀 `5fbd8 BRA 5fc14` / `5fc14`). `5fc14`: A0 = LONG `c`; BYTE `63(A0)` = 0이면 `5fc70`. `5fc20`: BYTE `76(A6)` ≠ 3이면 `5fc66`(BYTE `79` = 0). `5fc2a`: BYTE `78` ≠ 0이면 `5fc4c`(애니메이션 `124`), 아니면 `5fc32`(애니메이션 `120`, 복귀 `5fc48 BRA 5fc62`); `5fc62`: `BRA 5fc6a`. `5fc6a`: `(A6)` = `5e8b0`. `5fc70`: `JSR 43e34`. `5fc76`: A0 = LONG `c`; BYTE `78` ≠ 0이면 `5fc92`. `5fc82`: WORD `46(A0)` ≤ `180`(부호)이면 `5fc8e`(→`5fc9e`), 아니면 `5fc8c RTS`. `5fc92`: WORD `46(A0)` ≥ `180`(부호)이면 `5fc9e`, 아니면 `5fc9c RTS`. `5fc9e`: BYTE `79` = 0이면 `5fca6 RTS`. `5fca8`: `JSR 4a46c`. `5fcae`: `JSR 49fc6`. `5fcb4`: Clear면 `5fd02 RTS`. `5fcb8`: BYTE `77` += 1(메모리 RMW); BYTE `78` ≠ 0이면 A0 = `5fd1c`, 아니면 `5fd14`. `5fcd0`: `D0` = 0, `D0.B` = BYTE `77`, `D0.B` = (2·`D0.B`) & `ff`, `D0.W` = WORD(A0 + `D0.W`); ≠ 0이면 `5fcea`. `5fce0`: BYTE `77` = 0, BYTE `79` = 0(`D0.W` = 0 그대로). `5fcea`: 표 꼴 애니메이션(복귀 `5fd02 RTS`).

## carry

- [F] **소비 7 block**: `5f394` `5f876` `5fcb4 BCC`(interpreter `49fc6`의 C), `5f3c4` `5f3ea` `5f414` `5f43a BCC`(fade_card `28ae`의 C; 결정 6). Unknown C로 들어오면 `objects n26 caller requires known carry`(상태 보존)다.
- [F] **known 생산 4 block**: `5f3d6` `5f3fc` `5f426` `5f44c`(`ORI.B #1,CCR`, Set; 결정 3). 소비자는 없다(뒤 block이 C를 다시 쓴다). N26 안에는 `ANDI` CCR이 없고, RTS 12곳 앞 C를 읽는 ROM 소비자도 없다(callback의 복귀는 scheduler로 간다).
- [F] **FLOW_ONLY 49 block**(C 보존): JSR 하나뿐인 block(`5f26a` `5f270` `5f354` `5f388` `5f38e` `5f774` `5f77a` `5f860` `5f870` `5f9a4` `5fb2e` `5fb34` `5fc70` `5fca8` `5fcae`), `MOVEA`+JSR(`5fa02`), `LEA`(+`BRA`) block(`5f308` `5f310` `5f46c` `5f474` `5fcc4` `5fccc`), `BRA` block(`5f32e` `5f336` `5f400` `5f45c` `5fbd8` `5fc48` `5fc62` `5fc8e`), RTS(`5f386` `5f4ae` `5f86e` `5f9f8` `5fa66` `5fab4` `5fb02` `5fb04` `5fc8c` `5fc9c` `5fca6` `5fd02`), 소비 7.
- [F] **carry 보존 목록 49 PC** = FLOW_ONLY 49.
- [F] **Unknown 115 block**: 나머지(`MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`ADD`/`ADDQ`/`SUBQ`/`LSL`/`BSET`가 있는 block, 설치 block, 애니메이션 인자 block, `28ae` 자식 block). block 안에서 계산되는 C(`5f362` `5fa12` `SUBQ.W 7e`의 Z, `5f450 SUBQ.W 80`의 C)는 같은 block의 Bcc만 읽고 block 밖으로 나가지 않는다.
- [F] X를 쓰는 명령은 없다.

## 구현 범위와 규약

- routing 3 범위(`5f24a..5f4b0` `5f760..5fb06` `5fb0e..5fd04`). 짝수 PC 1,025개 중 block 시작 168, 내부 857. 내부 PC 직접 진입은 `unsupported animation objects n26 PC`다. 범위 이웃(`5f4b0..5f760` 자료·고아 사슬, `5fb06..5fb0e` 표, `5fd04..5fd24` 표)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다(`MOVEQ`·`MOVEA`·`LEA`·`MOVE.L`은 LONG 전체). 산술은 원래 폭의 2의 보수로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다. `SUBQ.W`의 빌림·0 결과, 부호 있는 비교(`BGE` BYTE, `BLE`/`BGE` WORD)는 폭별로 명시 계산한다. 결과 flag는 같은 block 안의 Bcc만 쓴다(결정 6 예외). 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다). 메모리 대상 RMW(`BSET.B` `SUBQ.W` `ADDQ.B`)는 읽은 뒤 쓴다.
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 49 PC를 넣는다. 생산 4 block은 실행부가 `AnimationCarrySet`을 둔다.
- 제어 이동: 모두 정적이다. 설치 값(`5f2c4` `5f7ec` `5fb84` `5e8b0`)과 `28ae` 자식 값 `5f504`는 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. `5f2be`→`5f2c4`, `5f7e6`→`5f7ec`, `5fb7e`→`5fb84`는 같은 실행으로 계속한다. `JSR 4ae4a`는 A0 = LONG `72(A6)`(임의 값)를 N08 실행부에 넘긴다.
- 스택: JSR 복귀 LONG push와 RTS pop만. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank): LONG `200194`(id `18b` → LONG `22`; 결정 5).
- [F] LONG `22` 기준 LONG 읽기(live bus; 대상이 bank window면 bank 읽기): 고정 변위 `ec` `f0` `f4` `f8` `fc` `100` `104` `120` `124`, 부호 확장 16 bit 색인 4·표 값. 결과 A1은 `49f8c`(interpreter) 인자다.
- [F] 고정 ROM 자료(live bus): `5f4b0` `5f4bc` `5fb06` `5fd04` `5fd0c` `5fd14` `5fd1c` WORD 표(결정 4). 주소만 넘기는 자료: `28ae` 자식 `5f504`(`D0.W` = `a`), `8ebe` 인자 WORD `d4b` `d4e` `d52` `d53` `d54` `d5e`(`D1.B` = 0), `4a496` 인자 `d56` `d62`, `49290` 인자 `D0.W`/`D1.W` = 0/0 또는 `ffe0`/`a8`·`ffe0`/0, `3af8` 인자 `1a9f` `1acb` `1acc` `1acd`, `3c44` 인자 `1acb` `1acc`, `4970a` 인자 `ffc0`/`ffea`·`ffe0`·`30`·`3a`.
- [F] work RAM 노드 A6: BYTE `15`(`BSET` RMW) `62` `76` `77`(RMW) `78` `79`; WORD `1e` `20` `68` `7e`(RMW) `80`(RMW); LONG `(A6)`(설치) `c`(부모) `22` `72`. 부모 노드(LONG `c`): BYTE `62`(쓰기) `63` `76` `77`, WORD `46`. A0 = A6 + `26`(`49f8c` 인자).
- [F] 상수 인자: `49f8c` `D0.W` = `100`; `28ae` `D0.W` = `a`.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256 앞 16자리): `engine/src/animation_machine_objects_n26.cpp` `d065629561341c18`, `engine/tests/animation_machine_objects_n26_test.cpp` `c3d071fd04391a9a`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나, carry 보존 case group 하나(49 PC); `2c38c9ca8db177eb`), `engine/src/animation_machine_internal.h`(선언 하나; `b4d35cf6dce9ff6a`), `Makefile`(source 목록·test target·실행 줄; `8851582821049c7c`), `tools/verify_animation_machine.py` SOURCES(`0741feb046f448ba`).
- [F] 결정 7 탐침 교체(17 test, 값과 그 값을 적은 주석만, 54줄; 각 test의 기존 `10fexx`(`10fe00`~`10fe2c` `10fe76` `10fe90`)와 겹치지 않게 `10fe40`부터 짝수로 배정; scratch `probe/migrate26.py`):
  - `frame_helpers` `5f800` `5f500`→`10fe40` `10fe42`; `motion_walk` `5f4c0`→`10fe40`; `node_delete` `5f810` `5f8b0` `5fe60`→`10fe40` `10fe42` `10fe44`(error fixture 2개의 `10f000:0005f810`→`0010fe40`, fixture 이름 `error-return-5f810`→`error-return-10fe40`, RTS 복귀 LONG 포함); `objects_u04` `5f4c2`→`10fe40`; `objects_u08` `5f802` `5fa10`→`10fe40` `10fe42`; `objects_u08b` `BOUNDARIES` `5ff40` `5fe14` `5fa14`→`10fe40` `10fe42` `10fe44`, outside `5ff44` `5fe18` `5fa18` `5fe1c`→`10fe46` `10fe48` `10fe4a` `10fe4c`.
  - `objects_u10`·`objects_u12` `5f712` `5f8a0` `5fe40`→`10fe40` `10fe42` `10fe44`(RTS 복귀 LONG `5f712`→`10fe40`); `objects_u11` `5f810` `5f8b0` `5fe60`→`10fe40` `10fe42` `10fe44`(복귀 LONG 포함); `objects_u13`·`objects_u14` `5fc10` `5fc20` `5fc30`→`10fe40` `10fe42` `10fe44`; `objects_u15` `5fd10` `5fd20` `5fd30`→`10fe40` `10fe42` `10fe44`; `objects_u15b` `5ff48` `5ff4c` `5ff50`→`10fe40` `10fe42` `10fe44`; `objects_u16` `5ff10` `5ff20` `5ff30`→`10fe40` `10fe42` `10fe44`; `scene_update` `5f4c4`→`10fe40`; `script_placement` `5f9f0`→`10fe40`; `stage_event` `5f9f2`→`10fe40`. U10~U16 test의 주석 "unrouted 5f6xx..5ffxx range"는 "work RAM 10fe00..10fefe"로 바꿨다.
  - [F] `dcf56..dcf6a` 탐침과 scheduler fixture 문자열의 이 범위 값은 없었다. [I] 이 중 N26 routing 안 값(`5f800` `5f802` `5f810` `5f8a0` `5f8b0` `5f9f0` `5f9f2` `5fa10` `5fa14` `5fa18` `5fc10`~`5fc30`)은 N26 routing 뒤 깨졌을 것이고, 틈(`5f4c0`~`5f712`)·N27 범위 값은 N27·고아 정리 단계를 위해 미리 옮겼다(교체 전 실패 재현은 하지 않았다).
- [F] 실행부 case 집합 = scratch `starts.txt`(168, SHA256 `18f414ce…`). 내부 PC 857개는 모두 `unsupported animation objects n26 PC`, 소비 7 block은 Unknown C에서 `objects n26 caller requires known carry`(상태 보존)다.
- [F] `make -j3 all test`(작업 지시의 동시 3 process 상한; brief의 `-j4` 대신): exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log`). N26 test 출력: `animation machine objects n26: 648 fixtures (25 checked errors, 25 kept C), 168 blocks, 2541 calls`. 탐침을 옮긴 17 test, N20~N25·N28·N29 test, `tools/tests` unittest 257개 통과.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N26 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만, scratch `gen/gen26.py` Unicorn 생성, 두 번 생성해 `tables_n26.inc` SHA256 `bff0887c136ac91d…` 같음): 648 fixture(성공 623, checked 오류 25), 168 시작 모두 Unicorn fixture로 덮음, block 표(168 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 7은 Unknown에서 거부, 생산 4는 Set), zero-step 168 × 3, 내부 PC 857 전수, 홀수 PC(범위마다 양끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`·RTS 복귀 `10fe40`(11 fixture), 범위 옆 자료 `5f248` `5f4b0` `5f4c6` `5f502` `5fb06` `5fb0c` `5fd04` `5fd22`(고아 사슬 코드 PC는 탐침으로 쓰지 않음), callee stop 15개(모두 다른 단위 진입). "real" 행은 fade_card `28ae`(자리 20/11 → `2908 ORI` Set → `4970a`, 10/0 → `290e ANDI` Clear → 다음 `28ae`/`5f450`)를 native로 따라가 실제 소비자 `5f3c4` `5f3ea` `5f414` `5f43a` 분기와 자식 LONG `5f504`를 비교했다. `49fc6` 소비 `5f394` `5f876` `5fcb4`는 typed C(실제 ROM 차분에서 확인). `ORI CCR` 4 block은 바로 뒤 PC를 선언 stop으로 둔 행에서 known Set을 확인했다. 합성 바이트: `5f4b0..5f4c8`(`0003 0005 2001 0007 3fff 0000 0009 000b 0000 000d 4000 0000`), `5fb06`(`0002 ffff 2001 0006`), `5fd04..5fd24`(16 WORD, `ffff`·0·`2002`/`8001`/`3ffe` 포함), bank `200000..200800`(LONG `200194` = `200400`). checked 오류 fixture 18개(홀수·ROM·장치 노드, 스택·RTS 장치, 부모 장치·ROM·홀수, 표 ROM(`5f478` BYTE `77` = `c`, `5fcd0` 4, `5f7fc` 4), 홀수 표 주소, 홀수·ROM LONG `22`, 적재 안 된 bank 바이트, 홀수 노드 LONG `72`) + 소비 7.
- [F] 돌연변이 검사(scratch `mut/mut26.py`, 실행부 한 줄씩 48개): 48/48을 test가 잡았다. 처음 실행에서 살아남은 `m34`(`5f9fa` LONG 0 판정 → WORD)는 LONG `72` = `100000` fixture를 더해 잡혔다. 잡힌 항목: 소비 분기 5곳 뒤바꿈, `ORI CCR` Set → Clear/Unknown, `ADD.B` → `ADD.W` 색인, BYTE/WORD 부호 없는 비교, `BLE`/`BGE` 경계, `SUBQ` 빌림/0 판정, 표 색인 배수·`LSL` 폭·색인 부호 확장, 초기값(`80` `7e` `3c` `1e` `78`), 부모 BYTE `77`/`76` 비교 폭, `4970a` 인자, 자식 값 `5f504`, 애니메이션 변위 `f0` `120`, `8ebe` id, `5f9ea` 문턱, 단계 값, 부모 `62` 쓰기, `CLR.B 62`, `5fce0` `77` = 0, `ADDQ.B` 폭, `5fc20` 3, `5fa02` A0, 자식 id 804, `D1.W` `a8`, `BSET` RMW, 표 선택(`5fd04`/`5fd0c`, `5fd14`/`5fd1c`), `5f314` 첫 WORD, 부모 추종 비교 폭, `5f838` `77` = 0, `5f2e6` `62` = `ff`.
- [F] 실제 ROM 차분(scratch `realrom/real26.py`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM, LONG `22` = 실제 banked 기록 또는 RAM 사본, 실제 ROM 표, LONG `26` = 0 또는 실제 기록의 애니메이션 목록, LONG `72` = 0 또는 RAM 노드, native는 STOP·`2a00`·`2a24`·C++ routing 밖 첫 PC·`49f8c`/`49f96`(선언 stop)에서 멈춤): 3 seed × 1,500 case 불일치 0/0/0, 시작 168/168(seed마다). 실제 생산자 뒤 소비자 native 분기 비교(seed 1/2/3): `5f3c4` 38/50/43, `5f3ea` 48/57/49, `5f414` 60/53/60, `5f43a` 69/58/69(fade_card `28ae`), `5f394` 16/15/16, `5f876` 15/14/9, `5fcb4` 10/15/10(interpreter `49fc6`). C++ stop C(Unknown/Clear/Set) seed 1 1,450/23/27. clean stop이 없는 native case는 건너뜀(315/285/351): 대부분 실제 interpreter `49fc6`·`4a46c`가 무작위 상태로 PC < `400`에 닿는 경우(`low`)와 무작위 A0로 직접 들어간 `5f478`, 초기화 사슬의 `8ebe` TRAP 경로(`none`)다. interpreter 따라가기(`FOLLOW_ANIM`) 2 × 1,000 case 불일치 0(건너뜀 273/258), 소비자 비교 `5f394` 18/8, `5f3c4` 32/26, `5f3ea` 39/36, `5f414` 36/41, `5f43a` 43/47, `5f876` 9/8, `5fcb4` 20/6.
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `4497217` 일치 pass 14,408·node 122,462, 불일치 0 → N26 뒤 같음(`diff_results.json` SHA256 `a6c41695…`, 기준과 바이트 동일).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 132·pass 52,800·node 396,091·불일치 0(`verification.json` SHA256 `762797c4…`) → N26 뒤 같은 값(`c55fc391…`; 차이는 `engine_source_sha256`의 `animation_machine.cpp`·`animation_machine_objects_n26.cpp`와 seed 32 33 116 117 기록의 `current_router_sha256`뿐). 새 완주 seed 0, 잃은 seed 0. seed 32 33은 그대로 frame 0 `dcf56`(N27)에서 멈춘다(재범위 예상과 같음).
- [U] 남은 미확인: seed 32 33의 자연 경로는 `dcf56`(N27)에서 먼저 멈춰 N26 범위의 frame pass 비교가 아직 없다(실제 ROM 차분·fixture로만 덮음). `5f2d4` 이후 발사 상태, `49fc6` C 소비 뒤 경로, `5f9ea` 이후, `5fca8` 이후, 자식 `5f504`는 자연 400 frame에서 실행되지 않는다. `5f504..5f760` 고아 사슬(미연결 callee `4b6f4` 포함)의 소유 단위는 미정이다(결정 2).
