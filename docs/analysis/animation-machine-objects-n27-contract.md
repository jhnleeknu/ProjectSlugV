# 객체 callback F4 N27: N24 `28ae` 자식 5개(`5fd24` `5fd36` `60008` `6031e` `6041e`)와 설치 callback `5fd9a` `60086` `60396` `6048c`, BSR 부프로그램 `5ff90`, 노드 callback `dcf56` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N27 행(155 block, 누적 4,062, `5fd24..60506` `dcf56..dcf6a`, callback `5fd24` `5fd36` `5fd9a` `60008` `60086` `6031e` `60396` `6041e` `6048c` `dcf56`, 경계 callee `5ff90`, bank 1, 미실행 설치 1(+99), 새 seed 32 33 / 32 33, 누적 완주 134 / 135; 원 범위 U37 155)이다. 단위 형식과 규약은 N26 계약(`animation-machine-objects-n26-contract.md`, SHA256 `4afefc7a5512c6193c3ee0adfdc2b786ddff41952a618d754413cefaa47f7b1e`)과 N24·N25·N28 계약을 따른다. 메인 작업 지시:
- 범위 = N27 행. 수치(155 block, 4,062, 진입, bank, 경계 `5ff90`)를 정적 디코드로 다시 확인한다. 재범위의 수치 열에서 "4,062"는 누적 block, "1(+99)"는 미실행 설치(N26 계약의 해석)다.
- block 시작은 `MOVE.L #imm,(A6)` 설치 callback, DBRA 대상, JSR/BSR 복귀점을 포함한다. 자료 표는 routing하지 않고 routing 범위를 표 둘레로 나눈다(N25·N26 관례).
- N26 작업자가 `5fd10..5ff50`·`dcf56..dcf6a`의 옛 탐침을 RAM `10fe40`+로 옮겼다. engine/tests 탐침·fixture 문자열에 N27 범위 PC가 남았는지 다시 확인하고, 남았으면 RAM `10fe00..10fefe`(파일 안에서 겹치지 않게)로 옮긴다.
- 다른 단위 실행부의 두 번째 진입이 필요하면 고치지 않고 scratch patch + 결정으로 보고한다. interpreter callback은 live 대상으로 routing한다(허용 목록 없음).
- 기대: 기준에서 seed 32 33은 frame 0 `dcf56`에서 멈춘다. N27 뒤 RNG 400 frame 차분에서 완주할 수 있다(재범위 예측 134/135). 새 완주 seed를 정확히 보고하고, 여전히 멈추면 PC·frame·소유 단위를 보고한다.

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, BSR 대상, 범위 안 `MOVE.L #imm,(A6)` 설치·`MOVEA.L #imm,A0`+`JSR 28ae` 자식, 범위 밖에서 참조하는 범위 안 진입)로 정한다. Unicorn TB 분할은 시작이 아니다. 같은 flag를 쓰는 연속 Bcc는 한 block으로 묶는다(N27에는 연속 Bcc가 없다). DBRA는 없다.
- 결정 5(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N26 수용 관례: CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`BRA`/`JMP`/`RTS`/Bcc/`ST`)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. `MOVE`/`MOVEQ`/`CLR`/`CMP`/`CMPI`/`ADD`/`ADDQ`/`SUBQ`/`ANDI`/`LSL`/`TST`/`BSET` 등이 있는 block은 C를 바꾸며, 블록 밖 소비자가 없으므로 Unknown으로 둔다. `ORI.B #1,CCR` block은 known Set을 둔다(N07 `9c04c`·N14 `a5d64`·N26 `5f3d6` 관례). 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N27 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`200194`와 LONG `22(A6)`이 가리키는 표)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n27`(HEAD `77e5485` = N01~N26·N28(`30fa0` 두 번째 진입 포함)·N29a까지 통합, `engine/src/animation_machine.cpp` SHA256 `2c38c9ca8db177eb83bf0c6177f253c028f5b7d3fe84758ad99abf1db703637e`, routing 규칙 85개, `engine/src/animation_machine_interpreter.cpp` SHA256 `97abb2e1de42cf322e35fa3a66eea3ab633170143ea79e0d525e5ad4e317882f`)을 참조했다. N27 routing 범위의 짝수 PC는 기존 routing에 없다(범위 양끝 이웃 `5fd22` `5ffd8` `60006` `60316` `6031c` `60416` `6041c` `60506` `dcf54` `dcf6a`도 routing 밖). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n27/n27.py`(정적 디코드, `starts.txt` SHA256 `f753326883b47e1094d95fc86a25fb050a035b10a5c3c3d3d37c5b51e2664c7c`)와 `cls27.py`(분류)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N27 = 162 block**(routing 범위 5개 `5fd24..5ffd8` `60008..60316` `6031e..60416` `6041e..60506` `dcf56..dcf6a`, 코드 1,974바이트, 짝수 PC 987, 내부 825). 진입 6개(아래)와 범위 안 설치 4개에서 분기·fall-through·BSR을 끝까지 따라간 정적 closure이며, 범위 안 명령 436개를 모두 덮는다(미도달 0).
  - [F] 재범위 155와의 차이 7은 BSR 부프로그램 `5ff90`(`5ff90` `5ff98` `5ffa0` `5ffa4` `5ffb4` `5ffbe` `5ffd6`)이다. 재범위는 이 부프로그램을 별도 함수("경계 callee `5ff90`")로 세고 본문을 어느 행에도 넣지 않았다. 범위 `5fd24..60506` 안에 있고 다른 단위가 소유하지 않으므로 N27에 넣는다(결정 1). 155 + 7 = 162.
  - [F] 재범위 "4,062"는 누적 block 열(N26까지 3,907 + 155)이다. 재범위 `5fd24..60506` 안의 WORD 표 `5ffd8..60008`(4개, 48바이트), `60316..6031e`, `60416..6041e`는 코드가 아니라 routing에서 뺀다(결정 1). 끝 표 `60506..6050e`는 범위 밖이다.
- [F] 진입:
  - N24 `28ae` 자식 값(N24 `5e000` `5e010` `5e020` `5e030` `5e040`이 `MOVEA.L #x,A0; MOVE.W #0,D0; JSR 28ae`로 넘김): `5fd24` `5fd36` `60008` `6031e` `6041e`. 범위 밖 다른 실행 참조 없음(같은 값의 LONG은 좌표·자료 값이다).
  - 노드 callback `dcf56`: stage event 기술자 `dcf6a`(LONG `dd20c`가 가리킴)의 LONG `dcf76` = `dcf56`, 뒤 WORD `ffff`. N05 `dceca`(기술자 `dcf44`, LONG `dcf50`)와 같은 꼴이다. [I] 기술자 `+c` LONG이 node callback 진입이다(N05 계약과 같은 해석).
  - 범위 안 설치(fall-through): `5fd9a`(`5fd94`), `60086`(`60080`), `60396`(`60390`), `6048c`(`60486`).
  - 공유 callback `5e8b0`(N25) 설치: `5fe3a` `6012e` `603f2` `604e8 MOVE.L #5e8b0,(A6)`. 실행 PC가 아니라 노드 LONG 자료다.
- [F] **경계 callee 없음**(다른 단위 기준). 부르는 callee 16개(`8ebe` `8ff4` `16ef0` `28ae` `2a00`(`JMP`) `3af8` `3c44` `43e34` `491c4` `49290` `4970a` `49a58` `49f8c` `49fc6` `4a46c` `4a496`)가 모두 기존 실행부의 block 시작이다(scratch 검사: 해당 실행부 소스의 `case 0x…:`; 아래 "자료"). 재범위의 "경계 `5ff90`"은 N27 안 BSR 부프로그램이다(결정 1). 레지스터 간접 호출·TRAP·점프 표는 없다. 패치 파일은 없다.
- [F] **`28ae` 자식 `60516`**(결정 2): `6018e` `601b8 MOVEA.L #60516,A0; MOVE.W #a,D0; JSR 28ae`가 넘기는 자식이다. `60516..`은 범위 밖 고아 설치 사슬(진입 `JSR 49a58`, 설치 `605ae`, 미연결 callee `490ba`, `28ae` 자식 `d1cd8`(N05), `JMP 2a00` 여럿)이다. 재범위 N27 행의 "미실행 설치 1(+99)"가 이 자식이다. 두 기록(RNG 400·base) 어디서도 실행되지 않는다(아래 자연 도달). N27은 `60516`을 자료로만 넘긴다.
- [F] **carry**: 소비 3 block(`5ff7e BCC`: interpreter `49fc6`의 C; `6019e` `601c8 BCC`: fade_card `28ae`의 C), known 생산 2(`601b0` `601da ORI.B #1,CCR` Set, 소비자 없음; 결정 3), FLOW_ONLY 49(소비 3 포함), Unknown 111. 49 + 2 + 111 = 162.
- [F] N/Z 재계산 없음. X·DIVx/MULx·PC 상대 점프 표·레지스터 간접 점프·TRAP·I/O port 쓰기·bank 변경 없음. `SUBQ.W`(메모리 WORD)·`CMP`/`CMPI`/`TST`/`ANDI`의 flag는 같은 block의 Bcc만 읽는다.
- [F] 스택: JSR/BSR 복귀 LONG만(push/pop 없음). RTS 9곳(`5fe4e` `5ff8e` `5ffd6`(BSR 부프로그램 끝) `6013c` `60314` `60406` `60414` `604fc` `60504`). `dcf56`은 `JMP 2a00`(fade_card 실행부가 routing하는 `2a00`: `BSR 299c` 뒤 A7 복원, `2ac2`로)으로 끝난다(push 없음).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `seen27.py`): 두 기록 모두 seed 32 33만 N27 범위를 실행한다. callback 실행 수(seed별): `5fd24` `5fd36` `60008` `6031e` `6041e` `dcf56` 각 1, `5fd9a` 162, `60086` `60396` `6048c` 각 81. 실행된 범위 안 TB 시작은 57개(초기화 사슬 전부, `5fd9a` `5fdaa` `5fdb6` `5fdee` `5fdf2` `5fe2a` `5fe40` `5fe46` `5fe4e`, `60086` `60096` `600d6` `600dc` `600e2` `60134` `6013c`, `60396` `603a6` `603e2` `603f8` `603fe` `60406`, `6048c` `6049c` `604d8` `604ee` `604f4` `604fc`, `dcf56`)이다(표 값 `ffff`, 부모 BYTE `63` = 0, BYTE `79` = 0 경로). `5fe50` 이후 단계 상태기계, BSR `5ff90`, `600ee` 이후, `6013e` 이후(난수·`28ae` 자식 `60516`), `60408`, `604fe`는 실행되지 않는다. `60516..` 사슬은 TB 0개다.
- [F] 기준(`77e5485`)에서 seed 32 33은 frame 0 callback `dcf56`에서 먼저 멈춘다. [F] N27 뒤 두 seed는 RNG 400·base 120 모두 완주한다(재범위 134/135와 같음; 검증 기록).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 162 block, routing 5 범위.** [F] 정적 디코드 시작 집합은 재범위 155에 BSR 부프로그램 `5ff90`의 7 block을 더한 것이다(재범위는 `5ff90`을 "경계 callee"로 세고 본문을 어느 행에도 두지 않았다). `5ff90`은 N27 범위 안이고 `5fe68` `5feae` `5fece` `5fef8` `5ff1c` `5ff40 BSR.W`만 부르므로 N27에 넣는다. routing은 WORD 표 `5ffd8..60008`(`5ffd8` `5ffe0` `5ffe8` `5fff8`), `60316..6031e`, `60416..6041e`를 빼고 `5fd24..5ffd8` `60008..60316` `6031e..60416` `6041e..60506` `dcf56..dcf6a`로 나눈다(표 PC는 `unsupported animation machine PC`).
2. **`28ae` 자식 `60516` 고아 사슬.** [F] 범위 밖(`60506..60516` 자료 16바이트 뒤)이고 어느 단위도 소유하지 않는다. [U] 소유 단위 미정(N25 `5eed2`·N26 `5f504`와 같은 고아 설치 정리 단계 후보). 미연결 callee `490ba`(및 사슬 안 다른 미연결 callee)를 부르므로 그 단계에서 함께 다뤄야 한다. 400 frame 안에 실행되지 않는다.
3. **`ORI.B #1,CCR` 2 block = known Set.** [F] `601b0` `601da`는 `28ae` Set 뒤 `4970a` 복귀점의 `ORI.B #1,CCR` 단독 block이다. 뒤 block(`601b4 BRA`(FLOW) → `601de SUBQ.W`, `601de SUBQ.W`)이 C를 다시 쓰므로 소비자는 없다. N26 결정 3 관례대로 실행부가 known Set을 둔다. 소비자가 없으므로 이 C에 대한 오류 문자열은 없다.
4. **자료 표(live bus).** [F] 점프 표가 아니므로 전사하지 않고 `am_read`로 읽는다. 색인 검사는 원본처럼 없다.
   - `5ffd8`(`ffff ffff ffff 005a`, SHA256 앞 16자리 `86bc3a0f08934f06`)·`5ffe0`(`ffff ffff ffff 0061`, `aea8b5bca61050a8`): `5fdb6`/`5fdf2` 색인 2·BYTE `76`(`ADD.W`, 0..510). `ffff`이면 BYTE `79` = 0 그대로.
   - `5ffe8`(`005a 005b 005c 005d 005e 005f 0060 0000`, `39007e3d0d693bce`)·`5fff8`(`0061 … 0067 0000`, `21e58a7d0aa474fa`): `5ffa4` 색인 (2·BYTE `77`) & `ff`(`ADD.B`, 0..254). 0이면 `5ffb4`(BYTE `77` = 0, BYTE `79` = 0) 뒤 같은 `D0.W` = 0으로 `5ffbe`.
   - `60316`(`ffff ffff ffff 004d`, `647250c746c0e1a9`), `60416`(`ffff ffff ffff 0047`, `7fe6948992f43dc9`), `60506`(`ffff ffff ffff 0006`, `72e356562d55ab7c`): `60096`/`603a6`/`6049c` 색인 2·BYTE `76`(`ADD.W`).
   - 큰 색인은 범위 밖 ROM(다음 표·코드 바이트)을 그대로 읽는다(원본과 같음).
5. **bank 읽기.** [F] `5fd86` `60052` `6021a` `6026c` `602be` `60368` `6045e MOVE.L 200194.l,22(A6)`(id `18b`, banked LONG; 재범위 "bank 1" = 주소 1개). 이어서 LONG `22`를 기준으로 LONG을 읽는다: `134`(`60052` `6026c` `602be`), `138`(`6021a`), `13c`(`60110`), `11c`(`60368`), `18`(`6045e`), 4·WORD 표 값(`5fdd2` `5fe0e` `5ffbe` `600ba` `603c6` `604bc`). 색인 LONG 읽기는 `(A1,Dn.W)`(16 bit 부호 확장)다. 모두 live bus(현재 PVC bank 모델)다.
6. **callee C 소비 3곳.** [F] 모두 callee가 RTS로 돌려준 C를 읽고, Unknown C면 `objects n27 caller requires known carry`(상태 보존)다.
   - `5ff7e BCC`(interpreter `49fc6`): N20·N25·N26 계약과 같은 interpreter 끝의 known C. Clear면 `5ff8e RTS`, Set이면 `5ff82`(BYTE `62` = 0이면 `ST.B 62`).
   - `6019e` `601c8 BCC`(fade_card `28ae`): `2908 ORI` Set(자리 있음) → `4970a`로 자식 위치 지정 뒤 `ORI CCR`; `290e ANDI` Clear(자리 없음) → `601b4`(→`601de`) / `601de`.
   - [F] 실제 생산자를 따라간 native 분기로 확인한다(검증 기록).
7. **무효화 탐침 — 남은 것 없음.** [F] N26 작업자가 `5fd10..5ff50`의 옛 탐침을 옮긴 뒤 engine/tests·tools에 N27 범위(`5fd24..60506`, `dcf56..dcf6a`) PC를 fixture 진입·stop·rollback 탐침·RTS 복귀 LONG으로 쓰는 곳은 없다(scratch 검사: fixture 행 진입/stop, `addr:LONG` 문자열, `reject`/`outside`/`BOUNDARIES` 줄). 남은 이 범위 값은 자료다: `objects_n24` test의 `28ae` 자식 LONG `5fd24` `5fd36` `60008` `6031e` `6041e`(A0 출력)·`60080`(D0 출력)·`5ffff`/`60000`(노드 LONG `36`), `objects_u04` test 노드 LONG `60000`~`60302`, `objects_u20`의 `5fff0` `5fffc` `5ffff`, `objects_u18` `10e046:00060000`, `script_placement` `60077`(레지스터 출력), scene·stage test의 `60000`~`60022`(자료 주소). N26 test의 범위 옆 탐침 `5fd22`는 N27 범위 밖(N26 표 `5fd04..5fd24`)이라 그대로 routing 밖이다. 따라서 다른 test 파일은 고치지 않는다(전 test 통과로 확인).
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n27.cpp`의 `animation_objects_n27_block`. 오류는 `unsupported animation objects n27 PC`(내부 PC), `objects n27 caller requires known carry`(소비 3 block).

## 원본 바이트 근거

[F] N27 코드 5 범위 1,974바이트(짝수 PC 987개, 시작 162, 내부 825). 연결 SHA256 `90ae2879070a4a5e85a30ebc6bfa5df9e035624fd56be153325453acd4f2e288`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `5fd24..5ffd8` | 692 | `18d0384e7b81e3beadf4b6c2c7b5c171880fd78761d32fa935a044090a92bcbf` | 64 |
| `60008..60316` | 782 | `e82cc618da98613d96095fbbfbd59d5f6c4a4df176ed6f82e9b35a621a4e46d4` | 63 |
| `6031e..60416` | 248 | `cfa0f3f34f6be217902d6255a0245a43b6e4a00131a0253cc3a9c1e886083895` | 18 |
| `6041e..60506` | 232 | `4f4a491928150cc1005327f9564c5f88846d98e9fb720233197cd35cfe9f4041` | 16 |
| `dcf56..dcf6a` | 20 | `893b1e0bd5669c290389bef50519066cbf683e07cb1df67eb13bea135460432f` | 1 |

- [F] 범위 이웃(모두 routing 밖): `..5fd24`(N26 끝 표 `5fd04..5fd24`, SHA256 앞 16자리 `9c9c963ad5de2a60`), `5ffd8..60008`(표 4개 48바이트, `6664d9a27c3d5db0`; 결정 1·4), `60316..6031e`(표), `60416..6041e`(표), `60506..6050e`(표), `6050e..60516`(자료 `fff0 fff0 0020 0020`), `60516..`(고아 자식 사슬; 결정 2), `dcf3c..dcf56`(N05 `dceca` 끝 `JMP 2a00`·`RTS`·기술자 `dcf44`), `dcf6a..dcf7c`(기술자: 0 12바이트, LONG `dcf56`, `ffff`).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "known Set 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(A6)·`(An,Dn.W)`는 부호 확장한다.

**`28ae` 자식 `5fd24`/`5fd36`(N24 `5e002`/`5e012` LONG; BYTE `78` = 0/1, 초기화, bank LONG `200194`, 끝 `5fd94` 설치 `5fd9a` fall-through) 8**
- `5fd24`: `MOVE.B #0, 78(a6); MOVE.W #0, d0; MOVE.W #0, d1; BRA.W 5fd44`
- `5fd36`: `MOVE.B #1, 78(a6); MOVE.W #0, d0; MOVE.W #0, d1` (→`5fd44`)
- `5fd44`: `JSR 49290.l` — FLOW
- `5fd4a`: `JSR 491c4.l` — FLOW
- `5fd50`: `MOVE.B #ff, 76(a6); MOVE.W #d5d, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `5fd64`: `MOVE.W #d56, d0; JSR 4a496.l`
- `5fd6e`: `BSET.B #6, 15(a6); MOVE.W #804, 68(a6); MOVE.W #804, 1e(a6); JSR 16ef0.l`
- `5fd86`: `MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.L #5fd9a, (a6)` (→`5fd9a`)

**설치 callback `5fd9a`(부모 BYTE `76` 추종, 표 `5ffd8`/`5ffe0`, 부모 BYTE `63` → 설치 `5e8b0`, BYTE `77` 0~6 단계와 부모 BYTE `77`·LONG `3a`, BSR `5ff90`, `49fc6` C → BYTE `62`) 49**
- `5fd9a`: `MOVEA.L c(a6), a0; MOVE.B 76(a0), d0; CMP.B 76(a6), d0; BEQ.W 5fe2a` (→`5fdaa`)
- `5fdaa`: `MOVE.B d0, 76(a6); TST.B 78(a6); BNE.W 5fdf2` (→`5fdb6`)
- `5fdb6`: `LEA.L 5ffd8(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 5fdee` (→`5fdd2`)
- `5fdd2`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5fdee`: `BRA.W 5fe2a` — FLOW
- `5fdf2`: `LEA.L 5ffe0(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 5fe2a` (→`5fe0e`)
- `5fe0e`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5fe2a`: `MOVEA.L c(a6), a0; TST.B 63(a0); BEQ.W 5fe40` (→`5fe36`)
- `5fe36`: `CLR.B 79(a6); MOVE.L #5e8b0, (a6)` (→`5fe40`)
- `5fe40`: `JSR 43e34.l` — FLOW
- `5fe46`: `TST.B 79(a6); BNE.W 5fe50` (→`5fe4e`)
- `5fe4e`: `RTS` — FLOW
- `5fe50`: `CMPI.B #0, 77(a6); BNE.W 5fe7a` (→`5fe5a`)
- `5fe5a`: `MOVEA.L c(a6), a0; CMPI.B #2, 77(a0); BNE.W 5fe76` (→`5fe68`)
- `5fe68`: `CLR.B 62(a6); MOVE.B #1, 77(a6); BSR.W 5ff90`
- `5fe76`: `BRA.W 5ff72` — FLOW
- `5fe7a`: `CMPI.B #1, 77(a6); BNE.W 5feb6` (→`5fe84`)
- `5fe84`: `MOVEA.L c(a6), a0; CMPI.B #3, 77(a0); BNE.W 5feb2` (→`5fe92`)
- `5fe92`: `CLR.B 62(a6); TST.L 3a(a0); BMI.W 5fea8` (→`5fe9e`)
- `5fe9e`: `MOVE.B #2, 77(a6); BRA.W 5feae`
- `5fea8`: `MOVE.B #4, 77(a6)` (→`5feae`)
- `5feae`: `BSR.W 5ff90` — FLOW
- `5feb2`: `BRA.W 5ff72` — FLOW
- `5feb6`: `CMPI.B #2, 77(a6); BNE.W 5fee0` (→`5fec0`)
- `5fec0`: `MOVEA.L c(a6), a0; CMPI.B #4, 77(a0); BNE.W 5fedc` (→`5fece`)
- `5fece`: `CLR.B 62(a6); MOVE.B #3, 77(a6); BSR.W 5ff90`
- `5fedc`: `BRA.W 5ff72` — FLOW
- `5fee0`: `CMPI.B #4, 77(a6); BNE.W 5ff0a` (→`5feea`)
- `5feea`: `MOVEA.L c(a6), a0; CMPI.B #4, 77(a0); BNE.W 5ff06` (→`5fef8`)
- `5fef8`: `CLR.B 62(a6); MOVE.B #5, 77(a6); BSR.W 5ff90`
- `5ff06`: `BRA.W 5ff72` — FLOW
- `5ff0a`: `CMPI.B #3, 77(a6); BNE.W 5ff2e` (→`5ff14`)
- `5ff14`: `TST.B 62(a6); BEQ.W 5ff2a` (→`5ff1c`)
- `5ff1c`: `CLR.B 62(a6); MOVE.B #6, 77(a6); BSR.W 5ff90`
- `5ff2a`: `BRA.W 5ff72` — FLOW
- `5ff2e`: `CMPI.B #5, 77(a6); BNE.W 5ff52` (→`5ff38`)
- `5ff38`: `TST.B 62(a6); BEQ.W 5ff4e` (→`5ff40`)
- `5ff40`: `CLR.B 62(a6); MOVE.B #6, 77(a6); BSR.W 5ff90`
- `5ff4e`: `BRA.W 5ff72` — FLOW
- `5ff52`: `CMPI.B #6, 77(a6); BNE.W 5ff72` (→`5ff5c`)
- `5ff5c`: `TST.B 62(a6); BEQ.W 5ff6e` (→`5ff64`)
- `5ff64`: `CLR.B 62(a6); MOVE.B #0, 77(a6)` (→`5ff6e`)
- `5ff6e`: `BRA.W 5ff72` — FLOW
- `5ff72`: `JSR 4a46c.l` — FLOW
- `5ff78`: `JSR 49fc6.l` — FLOW
- `5ff7e`: `BCC.W 5ff8e` (→`5ff82`) — C 소비, FLOW
- `5ff82`: `TST.B 62(a6); BNE.W 5ff8e` (→`5ff8a`)
- `5ff8a`: `ST.B 62(a6)` (→`5ff8e`) — FLOW
- `5ff8e`: `RTS` — FLOW

**BSR 부프로그램 `5ff90`(재범위 "경계 callee"; 표 `5ffe8`/`5fff8` 단계 애니메이션) 7**
- `5ff90`: `TST.B 78(a6); BNE.W 5ffa0` (→`5ff98`)
- `5ff98`: `LEA.L 5ffe8(pc), a0; BRA.W 5ffa4` — FLOW
- `5ffa0`: `LEA.L 5fff8(pc), a0` (→`5ffa4`) — FLOW
- `5ffa4`: `MOVEQ #0, d0; MOVE.B 77(a6), d0; ADD.B d0, d0; MOVE.W (a0, d0.w), d0; BNE.W 5ffbe` (→`5ffb4`)
- `5ffb4`: `MOVE.B #0, 77(a6); CLR.B 79(a6)` (→`5ffbe`)
- `5ffbe`: `LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `5ffd6`: `RTS` — FLOW

**`28ae` 자식 `60008`(N24 `5e022`; 초기화, `82.W` = 2, bank 애니메이션 `134`, 끝 `60080` 설치 `60086` fall-through) 7**
- `60008`: `MOVE.B #ff, 76(a6); MOVE.W #0, d0; MOVE.W #0, d1; JSR 49290.l`
- `6001c`: `JSR 491c4.l` — FLOW
- `60022`: `MOVE.W #d5a, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `60030`: `MOVE.W #d63, d0; JSR 4a496.l`
- `6003a`: `BSET.B #6, 15(a6); MOVE.W #802, 68(a6); MOVE.W #802, 1e(a6); JSR 16ef0.l`
- `60052`: `MOVE.W #2, 82(a6); LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 134(a1), a1; JSR 49f8c.l`
- `60080`: `MOVE.L #60086, (a6)` (→`60086`)

**설치 callback `60086`(부모 BYTE `76` 추종, 표 `60316`, 부모 BYTE `63`·BYTE `76` = 3 → 애니메이션 `13c`·설치 `5e8b0`, BYTE `77` 0~4 단계, `49a58` 난수, `28ae` 자식 `60516` 2개(`28ae` C → `4970a`, ORI CCR), `82`·`80`·`7e` 계수) 56**
- `60086`: `MOVEA.L c(a6), a0; MOVE.B 76(a0), d0; CMP.B 76(a6), d0; BEQ.W 600dc` (→`60096`)
- `60096`: `MOVE.B d0, 76(a6); TST.B 78(a6); LEA.L 60316(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 600d6` (→`600ba`)
- `600ba`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `600d6`: `MOVE.B #0, 77(a6)` (→`600dc`)
- `600dc`: `JSR 43e34.l` — FLOW
- `600e2`: `MOVEA.L c(a6), a0; TST.B 63(a0); BEQ.W 60134` (→`600ee`)
- `600ee`: `CMPI.B #3, 76(a6); BNE.W 6012a` (→`600f8`)
- `600f8`: `ST.B 79(a6); JSR 8ff4.l` — FLOW
- `60102`: `MOVE.W #d5b, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `60110`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 13c(a1), a1; JSR 49f8c.l`
- `60126`: `BRA.W 6012e` — FLOW
- `6012a`: `CLR.B 79(a6)` (→`6012e`)
- `6012e`: `MOVE.L #5e8b0, (a6)` (→`60134`)
- `60134`: `TST.B 79(a6); BNE.W 6013e` (→`6013c`)
- `6013c`: `RTS` — FLOW
- `6013e`: `MOVE.B 77(a6), d0; BNE.W 6016a` (→`60146`)
- `60146`: `MOVEA.L c(a6), a0; CMPI.B #1, 77(a0); BNE.W 60166` (→`60154`)
- `60154`: `MOVE.B #1, 77(a6); MOVE.W #4, 7e(a6); MOVE.W #18, 80(a6)` (→`60166`)
- `60166`: `BRA.W 60308` — FLOW
- `6016a`: `CMPI.B #1, d0; BNE.W 60246` (→`60172`)
- `60172`: `SUBQ.W #1, 7e(a6); BCC.W 60242` (→`6017a`)
- `6017a`: `MOVE.W #4, 7e(a6); JSR 49a58.l`
- `60186`: `ANDI.W #1, d0; BNE.W 601b8` (→`6018e`)
- `6018e`: `MOVEA.L #60516, a0; MOVE.W #a, d0; JSR 28ae.l`
- `6019e`: `BCC.W 601b4` (→`601a2`) — C 소비, FLOW
- `601a2`: `MOVE.W #ffe0, d0; MOVE.W #12, d1; JSR 4970a.l`
- `601b0`: `ORI.B #1, ccr` (→`601b4`) — known Set 생산
- `601b4`: `BRA.W 601de` — FLOW
- `601b8`: `MOVEA.L #60516, a0; MOVE.W #a, d0; JSR 28ae.l`
- `601c8`: `BCC.W 601de` (→`601cc`) — C 소비, FLOW
- `601cc`: `MOVE.W #ffe0, d0; MOVE.W #24, d1; JSR 4970a.l`
- `601da`: `ORI.B #1, ccr` (→`601de`) — known Set 생산
- `601de`: `SUBQ.W #1, 82(a6); BCC.W 601f2` (→`601e6`)
- `601e6`: `MOVE.W #1a, 82(a6); MOVE.B #1, 8f(a0)` (→`601f2`)
- `601f2`: `SUBQ.W #1, 80(a6); BCC.W 60242` (→`601fa`)
- `601fa`: `JSR 49a58.l` — FLOW
- `60200`: `ANDI.B #1, d0; ADDQ.B #2, d0; MOVE.B d0, 77(a6); MOVE.W #78, 7e(a6); MOVE.W #1aca, d0; JSR 3af8.l`
- `6021a`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 138(a1), a1; JSR 49f8c.l`
- `60242`: `BRA.W 60308` — FLOW
- `60246`: `CMPI.B #2, d0; BNE.W 60298` (→`6024e`)
- `6024e`: `SUBQ.W #1, 7e(a6); BCC.W 60294` (→`60256`)
- `60256`: `MOVE.B #4, 77(a6); MOVE.W #1e, 7e(a6); MOVE.W #1aca, d0; JSR 3c44.l`
- `6026c`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 134(a1), a1; JSR 49f8c.l`
- `60294`: `BRA.W 60308` — FLOW
- `60298`: `CMPI.B #3, d0; BNE.W 602ea` (→`602a0`)
- `602a0`: `SUBQ.W #1, 7e(a6); BCC.W 602e6` (→`602a8`)
- `602a8`: `MOVE.B #4, 77(a6); MOVE.W #1e, 7e(a6); MOVE.W #1aca, d0; JSR 3c44.l`
- `602be`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 134(a1), a1; JSR 49f8c.l`
- `602e6`: `BRA.W 60308` — FLOW
- `602ea`: `CMPI.B #4, d0; BNE.W 60308` (→`602f2`)
- `602f2`: `SUBQ.W #1, 7e(a6); BCC.W 60304` (→`602fa`)
- `602fa`: `MOVEA.L c(a6), a0; MOVE.B #1, 62(a0)` (→`60304`)
- `60304`: `BRA.W 60308` — FLOW
- `60308`: `JSR 4a46c.l` — FLOW
- `6030e`: `JSR 49fc6.l` — FLOW
- `60314`: `RTS` — FLOW

**`28ae` 자식 `6031e`(N24 `5e032`; `D0.W`/`D1.W` = `ffe0`/0, 초기화, bank 애니메이션 `11c`, 끝 `60390` 설치 `60396` fall-through) 7**
- `6031e`: `MOVE.B #ff, 76(a6); MOVE.W #ffe0, d0; MOVE.W #0, d1; JSR 49290.l`
- `60332`: `JSR 491c4.l` — FLOW
- `60338`: `MOVE.W #d4a, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `60346`: `MOVE.W #d56, d0; JSR 4a496.l`
- `60350`: `BSET.B #6, 15(a6); MOVE.W #802, 68(a6); MOVE.W #802, 1e(a6); JSR 16ef0.l`
- `60368`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 11c(a1), a1; JSR 49f8c.l`
- `60390`: `MOVE.L #60396, (a6)` (→`60396`)

**설치 callback `60396`(부모 BYTE `76` 추종, 표 `60416`, 부모 BYTE `63` → 설치 `5e8b0`, BYTE `79` ≠ 0 → `4a46c`·`49fc6`) 11**
- `60396`: `MOVEA.L c(a6), a0; MOVE.B 76(a0), d0; CMP.B 76(a6), d0; BEQ.W 603e2` (→`603a6`)
- `603a6`: `MOVE.B d0, 76(a6); LEA.L 60416(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 603e2` (→`603c6`)
- `603c6`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `603e2`: `MOVEA.L c(a6), a0; TST.B 63(a0); BEQ.W 603f8` (→`603ee`)
- `603ee`: `CLR.B 79(a6); MOVE.L #5e8b0, (a6)` (→`603f8`)
- `603f8`: `JSR 43e34.l` — FLOW
- `603fe`: `TST.B 79(a6); BNE.W 60408` (→`60406`)
- `60406`: `RTS` — FLOW
- `60408`: `JSR 4a46c.l` — FLOW
- `6040e`: `JSR 49fc6.l` — FLOW
- `60414`: `RTS` — FLOW

**`28ae` 자식 `6041e`(N24 `5e042`; 초기화, bank 애니메이션 `18`, 끝 `60486` 설치 `6048c` fall-through) 6**
- `6041e`: `MOVE.B #ff, 76(a6); MOVE.W #0, d0; MOVE.W #0, d1; JSR 49290.l`
- `60432`: `JSR 491c4.l` — FLOW
- `60438`: `MOVE.W #d4c, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `60446`: `BSET.B #6, 15(a6); MOVE.W #802, 68(a6); MOVE.W #802, 1e(a6); JSR 16ef0.l`
- `6045e`: `LEA.L 26(a6), a0; MOVE.W #18b, 20(a6); MOVE.L 200194.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 18(a1), a1; JSR 49f8c.l`
- `60486`: `MOVE.L #6048c, (a6)` (→`6048c`)

**설치 callback `6048c`(부모 BYTE `76` 추종, 표 `60506`, 부모 BYTE `63` → 설치 `5e8b0`, BYTE `79` ≠ 0 → `49fc6`) 10**
- `6048c`: `MOVEA.L c(a6), a0; MOVE.B 76(a0), d0; CMP.B 76(a6), d0; BEQ.W 604d8` (→`6049c`)
- `6049c`: `MOVE.B d0, 76(a6); LEA.L 60506(pc), a0; MOVEQ #0, d0; MOVE.B 76(a6), d0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; CLR.B 79(a6); CMPI.W #ffff, d0; BEQ.W 604d8` (→`604bc`)
- `604bc`: `ST.B 79(a6); LSL.W #2, d0; MOVEA.L 22(a6), a1; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; LEA.L 26(a6), a0; JSR 49f8c.l`
- `604d8`: `MOVEA.L c(a6), a0; TST.B 63(a0); BEQ.W 604ee` (→`604e4`)
- `604e4`: `CLR.B 79(a6); MOVE.L #5e8b0, (a6)` (→`604ee`)
- `604ee`: `JSR 43e34.l` — FLOW
- `604f4`: `TST.B 79(a6); BNE.W 604fe` (→`604fc`)
- `604fc`: `RTS` — FLOW
- `604fe`: `JSR 49fc6.l` — FLOW
- `60504`: `RTS` — FLOW

**노드 callback `dcf56`(stage event 기록 `dcf6a`의 LONG `dcf76`; work RAM LONG `10b1de` = `fffe0000`, `JMP 2a00`) 1**
- `dcf56`: `LEA.L 10b1d6.l, a1; MOVE.L #fffe0000, 8(a1); JMP 2a00.l`


- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다; WORD 산술은 16 bit 2의 보수, `.W`/`.B`는 나머지 bit 보존):
  - 애니메이션 인자(`MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c`): `D0.W` = `100`, A0 = A6 + `26`, A1 = LONG `22`, A1 = LONG(A1 + d), `JSR 49f8c`. 표 꼴(`LSL.W #2,D0; MOVEA.L 22(A6),A1; MOVEA.L (A1,D0.W),A1; …`): `D0.W` = (`D0.W` << 2) & `ffff`, A1 = LONG(LONG `22` + sext(`D0.W`)), 이어서 `D0.W` = `100`, A0 = A6 + `26`. bank 꼴(`60052` `6021a` `6026c` `602be` `60368` `6045e`): A0 = A6 + `26`, `20.W` = `18b`, LONG `22` = banked LONG `200194`, 이어서 애니메이션 인자. 표 선택 꼴(`LEA t(PC),A0; MOVEQ #0,D0; MOVE.B 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; CLR.B 79(A6); CMPI.W #ffff,D0; BEQ`): A0 = t, `D0` = 0, `D0.B` = BYTE `76`, `D0.W` = 2·`D0.W`, `D0.W` = WORD(t + `D0.W`), BYTE `79` = 0, `ffff`이면 건너뜀; 아니면 다음 block에서 BYTE `79` = `ff` + 표 꼴 애니메이션. 부모 추종 꼴(`MOVEA.L c(A6),A0; MOVE.B 76(A0),D0; CMP.B 76(A6),D0; BEQ`): A0 = LONG `c`, `D0.B` = BYTE `76(A0)`, BYTE `76(A6)`과 같으면 건너뜀.
  - `5fd24`/`5fd36`(자식): BYTE `78` = 0/1, `D0.W` = `D1.W` = 0; `5fd44`: `JSR 49290`; `5fd4a`: `JSR 491c4`. `5fd50`: BYTE `76` = `ff`, `8ebe`(`D0.W` = `d5d`, `D1.B` = 0). `5fd64`: `D0.W` = `d56`, `JSR 4a496`. `5fd6e`: BYTE `15` |= `40`(읽고 쓰기), `68.W` = `1e.W` = `804`, `JSR 16ef0`. `5fd86`: `20.W` = `18b`, LONG `22` = banked LONG `200194`, `(A6)` = `5fd9a`, fall-through.
  - `5fd9a`(설치): 부모 추종(같으면 `5fe2a`). `5fdaa`: BYTE `76(A6)` = `D0.B`; BYTE `78` ≠ 0이면 `5fdf2`(표 `5ffe0`, `ffff`이면 `5fe2a`, 아니면 `5fe0e`), 아니면 `5fdb6`(표 `5ffd8`, `ffff`이면 `5fdee BRA 5fe2a`, 아니면 `5fdd2`). `5fdd2`/`5fe0e`: BYTE `79` = `ff`, 표 꼴 애니메이션(복귀 `5fdee`/`5fe2a`). `5fe2a`: A0 = LONG `c`; BYTE `63(A0)` = 0이면 `5fe40`. `5fe36`: BYTE `79` = 0, `(A6)` = `5e8b0`. `5fe40`: `JSR 43e34`. `5fe46`: BYTE `79` = 0이면 `5fe4e RTS`.
  - 단계 상태기계(BYTE `77`; 한 번 실행에 한 단계만): `5fe50` = 0 → `5fe5a`: A0 = LONG `c`, BYTE `77(A0)` = 2이면 `5fe68`(BYTE `62` = 0, BYTE `77` = 1, `BSR 5ff90` 복귀 `5fe76`). `5fe7a` = 1 → `5fe84`: A0 = LONG `c`, BYTE `77(A0)` = 3이면 `5fe92`(BYTE `62` = 0; LONG `3a(A0)` < 0(bit 31)이면 `5fea8` BYTE `77` = 4, 아니면 `5fe9e` BYTE `77` = 2 + `BRA 5feae`; `5feae`: `BSR 5ff90` 복귀 `5feb2`). `5feb6` = 2 → `5fec0`: BYTE `77(A0)` = 4이면 `5fece`(BYTE `62` = 0, BYTE `77` = 3, `BSR` 복귀 `5fedc`). `5fee0` = 4 → `5feea`: BYTE `77(A0)` = 4이면 `5fef8`(BYTE `62` = 0, BYTE `77` = 5, `BSR` 복귀 `5ff06`). `5ff0a` = 3 → `5ff14`: BYTE `62` ≠ 0이면 `5ff1c`(BYTE `62` = 0, BYTE `77` = 6, `BSR` 복귀 `5ff2a`). `5ff2e` = 5 → `5ff38`: BYTE `62` ≠ 0이면 `5ff40`(같음, 복귀 `5ff4e`). `5ff52` = 6 → `5ff5c`: BYTE `62` ≠ 0이면 `5ff64`(BYTE `62` = 0, BYTE `77` = 0). 그 밖의 값은 `5ff72`. `5fe76` `5feb2` `5fedc` `5ff06` `5ff2a` `5ff4e` `5ff6e`: `BRA 5ff72`.
  - `5ff72`: `JSR 4a46c`. `5ff78`: `JSR 49fc6`. `5ff7e`: Clear면 `5ff8e RTS`. `5ff82`: BYTE `62` ≠ 0이면 `5ff8e`. `5ff8a`: BYTE `62` = `ff`(`ST`).
  - `5ff90`(BSR 부프로그램): BYTE `78` ≠ 0이면 A0 = `5fff8`(`5ffa0`), 아니면 `5ffe8`(`5ff98`). `5ffa4`: `D0` = 0, `D0.B` = BYTE `77`, `D0.B` = (2·`D0.B`) & `ff`, `D0.W` = WORD(A0 + `D0.W`); ≠ 0이면 `5ffbe`. `5ffb4`: BYTE `77` = 0, BYTE `79` = 0(`D0.W` = 0 그대로). `5ffbe`: 표 꼴 애니메이션(복귀 `5ffd6 RTS`).
  - `60008`(자식): BYTE `76` = `ff`, `D0.W` = `D1.W` = 0, `JSR 49290`; `6001c`: `JSR 491c4`. `60022`: `8ebe`(`d5a`, 0). `60030`: `D0.W` = `d63`, `JSR 4a496`. `6003a`: BYTE `15` |= `40`, `68.W` = `1e.W` = `802`, `JSR 16ef0`. `60052`: `82.W` = 2, bank 꼴 애니메이션 `134`(복귀 `60080`). `60080`: `(A6)` = `60086`, fall-through.
  - `60086`(설치): 부모 추종(같으면 `600dc`). `60096`: BYTE `76(A6)` = `D0.B`, BYTE `78` 읽기(`TST.B`, 결과 미사용), 표 `60316`(`ffff`이면 `600d6`, 아니면 `600ba`: BYTE `79` = `ff`, 표 꼴 애니메이션, 복귀 `600d6`). `600d6`: BYTE `77` = 0. `600dc`: `JSR 43e34`. `600e2`: A0 = LONG `c`; BYTE `63(A0)` = 0이면 `60134`. `600ee`: BYTE `76` ≠ 3이면 `6012a`(BYTE `79` = 0). `600f8`: BYTE `79` = `ff`, `JSR 8ff4`; `60102`: `8ebe`(`d5b`, 0); `60110`: 애니메이션 `13c`(복귀 `60126 BRA 6012e`). `6012e`: `(A6)` = `5e8b0`. `60134`: BYTE `79` = 0이면 `6013c RTS`.
  - `6013e`: `D0.B` = BYTE `77`; 0이면 `60146`: A0 = LONG `c`, BYTE `77(A0)` = 1이면 `60154`(BYTE `77` = 1, `7e.W` = 4, `80.W` = `18`); `60166`: `BRA 60308`. `6016a`: `D0.B` = 1 → `60172`: `7e.W` −= 1(메모리 RMW); 빌림(이전 값 0)이 아니면 `60242`. `6017a`: `7e.W` = 4, `JSR 49a58`(난수). `60186`: `D0.W` &= 1; ≠ 0이면 `601b8`. `6018e`/`601b8`: A0 = `60516`, `D0.W` = `a`, `JSR 28ae`. `6019e`/`601c8`: Clear면 `601b4`(→`BRA 601de`)/`601de`, Set이면 `601a2`/`601cc`: `D0.W` = `ffe0`, `D1.W` = `12`/`24`, `JSR 4970a`, 복귀점 `601b0`/`601da ORI.B #1,CCR`(known Set). `601de`: `82.W` −= 1; 빌림이면 `601e6`(`82.W` = `1a`, BYTE `8f(A0)` = 1, A0는 그때의 레지스터 값). `601f2`: `80.W` −= 1; 빌림이 아니면 `60242`. `601fa`: `JSR 49a58`. `60200`: `D0.B` &= 1, `D0.B` += 2, BYTE `77` = `D0.B`, `7e.W` = `78`, `D0.W` = `1aca`, `JSR 3af8`. `6021a`: bank 꼴 애니메이션 `138`(복귀 `60242 BRA 60308`).
  - `60246`: `D0.B` = 2 → `6024e`: `7e.W` −= 1; 빌림이면 `60256`(BYTE `77` = 4, `7e.W` = `1e`, `D0.W` = `1aca`, `JSR 3c44`; `6026c` bank 꼴 `134`, 복귀 `60294`). `60298`: = 3 → `602a0`: 같은 꼴(`602a8`, `602be`, 복귀 `602e6`). `602ea`: = 4 → `602f2`: `7e.W` −= 1; 빌림이면 `602fa`(A0 = LONG `c`, BYTE `62(A0)` = 1). 그 밖은 `60308`. `60294` `602e6` `60304`: `BRA 60308`. `60308`: `JSR 4a46c`. `6030e`: `JSR 49fc6`. `60314`: `RTS`(C는 scheduler로; 소비자 없음).
  - `6031e`(자식): BYTE `76` = `ff`, `D0.W` = `ffe0`, `D1.W` = 0, `JSR 49290`; `60332`: `JSR 491c4`. `60338`: `8ebe`(`d4a`). `60346`: `D0.W` = `d56`, `JSR 4a496`. `60350`: BYTE `15` |= `40`, `68.W` = `1e.W` = `802`, `JSR 16ef0`. `60368`: bank 꼴 `11c`(복귀 `60390`). `60390`: `(A6)` = `60396`.
  - `60396`(설치): 부모 추종(같으면 `603e2`). `603a6`: BYTE `76(A6)` = `D0.B`, 표 `60416`(`ffff`이면 `603e2`, 아니면 `603c6`: BYTE `79` = `ff`, 표 꼴, 복귀 `603e2`). `603e2`: BYTE `63(A0)` = 0이면 `603f8`. `603ee`: BYTE `79` = 0, `(A6)` = `5e8b0`. `603f8`: `JSR 43e34`. `603fe`: BYTE `79` = 0이면 `60406 RTS`. `60408`: `JSR 4a46c`. `6040e`: `JSR 49fc6`. `60414`: `RTS`.
  - `6041e`(자식): BYTE `76` = `ff`, `D0.W` = `D1.W` = 0, `JSR 49290`; `60432`: `JSR 491c4`. `60438`: `8ebe`(`d4c`). `60446`: BYTE `15` |= `40`, `68.W` = `1e.W` = `802`, `JSR 16ef0`. `6045e`: bank 꼴 `18`(복귀 `60486`). `60486`: `(A6)` = `6048c`.
  - `6048c`(설치): 부모 추종(같으면 `604d8`). `6049c`: BYTE `76(A6)` = `D0.B`, 표 `60506`(`ffff`이면 `604d8`, 아니면 `604bc`: BYTE `79` = `ff`, 표 꼴, 복귀 `604d8`). `604d8`: BYTE `63(A0)` = 0이면 `604ee`. `604e4`: BYTE `79` = 0, `(A6)` = `5e8b0`. `604ee`: `JSR 43e34`. `604f4`: BYTE `79` = 0이면 `604fc RTS`. `604fe`: `JSR 49fc6`. `60504`: `RTS`.
  - `dcf56`: A1 = `10b1d6`, LONG `10b1de` = `fffe0000`, `JMP 2a00`(PC = `2a00`, 스택 변화 없음).

## carry

- [F] **소비 3 block**: `5ff7e BCC`(interpreter `49fc6`의 C), `6019e` `601c8 BCC`(fade_card `28ae`의 C; 결정 6). Unknown C로 들어오면 `objects n27 caller requires known carry`(상태 보존)다.
- [F] **known 생산 2 block**: `601b0` `601da`(`ORI.B #1,CCR`, Set; 결정 3). 소비자는 없다(뒤 block이 C를 다시 쓴다). N27 안에는 `ANDI` CCR이 없고, RTS 9곳 앞 C를 읽는 ROM 소비자도 없다(callback의 복귀는 scheduler로, BSR `5ff90`의 복귀점 `5fe76` 등은 `BRA`(FLOW) 뒤 `5ff72 JSR`로 간다).
- [F] **FLOW_ONLY 49 block**(C 보존): JSR 하나뿐인 block(`5fd44` `5fd4a` `5fe40` `5ff72` `5ff78` `6001c` `600dc` `601fa` `60308` `6030e` `60332` `603f8` `60408` `6040e` `60432` `604ee` `604fe`), `ST`+JSR(`600f8`), `ST`(`5ff8a`), `LEA`(+`BRA`) block(`5ff98` `5ffa0`), `BRA` block(`5fdee` `5fe76` `5feb2` `5fedc` `5ff06` `5ff2a` `5ff4e` `5ff6e` `60126` `60166` `601b4` `60242` `60294` `602e6` `60304`), BSR block(`5feae`), RTS(`5fe4e` `5ff8e` `5ffd6` `6013c` `60314` `60406` `60414` `604fc` `60504`), 소비 3.
- [F] **carry 보존 목록 49 PC** = FLOW_ONLY 49.
- [F] **Unknown 111 block**: 나머지(`MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`ADD`/`ADDQ`/`SUBQ`/`ANDI`/`LSL`/`BSET`가 있는 block, 설치 block, 애니메이션 인자 block, `28ae` 자식 block, `dcf56`(`MOVE.L`) 포함). block 안에서 계산되는 C(`SUBQ.W 7e`/`80`/`82`의 빌림)는 같은 block의 Bcc만 읽고 block 밖으로 나가지 않는다.
- [F] X를 쓰는 명령은 없다.

## 구현 범위와 규약

- routing 5 범위(`5fd24..5ffd8` `60008..60316` `6031e..60416` `6041e..60506` `dcf56..dcf6a`). 짝수 PC 987개 중 block 시작 162, 내부 825. 내부 PC 직접 진입은 `unsupported animation objects n27 PC`다. 범위 이웃(`5fd04..5fd24` 표, `5ffd8..60008` 표, `60316..6031e` 표, `60416..6041e` 표, `60506..60516` 표·자료, `dcf3c..dcf56`·`dcf6a..` 기술자)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다(`MOVEQ`·`MOVEA`·`LEA`·`MOVE.L`은 LONG 전체). 산술은 원래 폭의 2의 보수로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다. `SUBQ.W`의 빌림, `TST.L`의 부호(bit 31), `ANDI.W`/`ANDI.B` 결과 0 판정은 폭별로 명시 계산한다. 결과 flag는 같은 block 안의 Bcc만 쓴다(결정 6 예외). 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다; `60096 TST.B 78(A6)`의 읽기도 한다). 메모리 대상 RMW(`BSET.B` `SUBQ.W`)는 읽은 뒤 쓴다.
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 49 PC를 넣는다. 생산 2 block은 실행부가 `AnimationCarrySet`을 둔다.
- 제어 이동: 모두 정적이다. 설치 값(`5fd9a` `60086` `60396` `6048c` `5e8b0`)과 `28ae` 자식 값 `60516`은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. `5fd94`→`5fd9a`, `60080`→`60086`, `60390`→`60396`, `60486`→`6048c`는 같은 실행으로 계속한다. `BSR.W 5ff90`은 복귀 LONG(다음 PC)을 push하고 `5ff90`으로 간다. `JMP 2a00`은 push 없이 PC = `2a00`.
- 스택: JSR/BSR 복귀 LONG push와 RTS pop만. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank): LONG `200194`(id `18b` → LONG `22`; 결정 5).
- [F] LONG `22` 기준 LONG 읽기(live bus; 대상이 bank window면 bank 읽기): 고정 변위 `18` `11c` `134` `138` `13c`, 부호 확장 16 bit 색인 4·표 값. 결과 A1은 `49f8c`(interpreter) 인자다.
- [F] 고정 ROM 자료(live bus): `5ffd8` `5ffe0` `5ffe8` `5fff8` `60316` `60416` `60506` WORD 표(결정 4). 주소만 넘기는 자료: `28ae` 자식 `60516`(`D0.W` = `a`), `8ebe` 인자 WORD `d4a` `d4c` `d5a` `d5b` `d5d`(`D1.B` = 0), `4a496` 인자 `d56` `d63`, `49290` 인자 `D0.W`/`D1.W` = 0/0 또는 `ffe0`/0, `3af8` 인자 `1aca`, `3c44` 인자 `1aca`, `4970a` 인자 `ffe0`/`12`·`24`.
- [F] work RAM 노드 A6: BYTE `15`(`BSET` RMW) `62` `76` `77` `78` `79`; WORD `1e` `20` `68` `7e`(RMW) `80`(RMW) `82`(RMW); LONG `(A6)`(설치) `c`(부모) `22`. 부모 노드(LONG `c`): BYTE `62`(쓰기) `63` `76` `77`, LONG `3a`. `601e6`: BYTE `8f(A0)`(A0 = `28ae`/`4970a` 복귀 뒤 레지스터). `dcf56`: LONG `10b1de`. A0 = A6 + `26`(`49f8c` 인자).
- [F] 다른 실행부로 가는 callee(모두 기존 block 시작; scratch `rt27.py`): `8ebe`(U02), `8ff4` `43e34`(cleanup), `16ef0` `4a496`(U14), `28ae` `2a00`(fade_card), `3af8`(sound), `3c44`(frame_helpers), `491c4`(U17), `49290`(U08), `4970a`(N14), `49a58`(stage_area), `49f8c` `49fc6`(interpreter), `4a46c`(N04). 공유 설치 값 `5e8b0`은 N25 block 시작이다.
- [F] 상수 인자: `49f8c` `D0.W` = `100`; `28ae` `D0.W` = `a`.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256 앞 16자리): `engine/src/animation_machine_objects_n27.cpp` `1938fe0e46e61e51`, `engine/tests/animation_machine_objects_n27_test.cpp` `ceecf3476a1e8e5f`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나(5 범위), carry 보존 case group 하나(49 PC); `2f2ce6474a22d30c`), `engine/src/animation_machine_internal.h`(선언 하나; `00af711597edc08a`), `Makefile`(source 목록·test target·실행 줄; `3a824e13f6571588`), `tools/verify_animation_machine.py` SOURCES(`00b2c619136145fb`). 다른 test 파일은 고치지 않았다(결정 7: 남은 탐침 없음).
- [F] 실행부 case 집합 = scratch `starts.txt`(162, SHA256 `f7533268…`). 내부 PC 825개는 모두 `unsupported animation objects n27 PC`, 소비 3 block은 Unknown C에서 `objects n27 caller requires known carry`(상태 보존)다.
- [F] `make -j3 all test`(작업 지시의 동시 3 process 상한): exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log`). N27 test 출력: `animation machine objects n27: 690 fixtures (24 checked errors, 8 kept C), 162 blocks, 2525 calls`. N20~N26·N28·N29 test와 옛 U·N test 전부, `tools/tests` unittest 257개 통과(N27 routing으로 깨진 기존 test 없음 — 결정 7 확인).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N27 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만, scratch `gen/gen27.py` Unicorn 생성, 두 번 생성해 `tables_n27.inc` SHA256 `7a1cea855f191bfe…` 같음): 690 fixture(성공 666, checked 오류 24), 162 시작 모두 Unicorn fixture로 덮음, block 표(162 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 3은 Unknown에서 거부, 생산 2는 Set), zero-step 162 × 3, 내부 PC 825 전수, 홀수 PC(범위마다 양끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`·RTS 복귀 `10fe40`(13 fixture), 범위 옆 자료 `5fd22` `5ffd8` `5ffe6` `60006` `60316` `6031c` `60416` `6041c` `60506` `60514` `dcf54` `dcf6a`(고아 사슬 코드 `60516`은 탐침으로 쓰지 않음), callee stop 16개(모두 다른 단위 진입, `JMP 2a00` 포함). "real" 행은 fade_card `28ae`(자리 20/11 → `2908 ORI` Set → `4970a`, 10/0 → `290e ANDI` Clear → `601b4`/`601de` → `82`·`80` 계수, `601e6`의 BYTE `8f(A0)`는 `28ae`가 남긴 A0 = `100e98`)를 native로 따라가 실제 소비자 `6019e` `601c8` 분기와 자식 LONG `60516`을 비교했다. `49fc6` 소비 `5ff7e`는 typed C(실제 ROM 차분에서 확인). `ORI CCR` 2 block과 `BRA 601b4`는 바로 뒤 PC를 선언 stop으로 둔 행에서 known Set/보존을 확인했다. 합성 바이트: `5ffd8..60008`(24 WORD, `ffff`·0·`2001`/`3fff`/`3ffe`/`8001` 포함), `60316` `60416` `60506`(각 4 WORD), bank `200000..200800`(LONG `200194` = `200400`). checked 오류 fixture 21개(홀수·ROM·장치 노드, JSR·BSR 스택 장치, RTS 장치, 부모 장치·ROM·홀수(`TST.L 3a`), `601e6` ROM 쓰기, 표 ROM(`5ff90` BYTE `77` = 8, `5fdb6` BYTE `76` = `18`, `60096`·`6049c` BYTE `76` = 4), 홀수 표 주소, 홀수·ROM LONG `22`, 적재 안 된 bank 바이트) + 소비 3.
- [F] 돌연변이 검사(scratch `mut/mut27.py`, 실행부 한 줄씩 55개): 54/55를 test가 잡았다. 살아남은 `m22`(`60096`의 결과 미사용 `TST.B 78(A6)` 읽기 제거)는 관측 불가 동치다: 바로 앞 `MOVE.B D0,76(A6)` 쓰기와 바로 뒤 `MOVE.B 76(A6),D0` 읽기가 같은 장치에 닿으므로 읽기 성공·실패와 오류 문자열이 달라지지 않는다(외부 상태 읽기 `d00046`는 앞 쓰기가 먼저 실패). 원본 명령 순서를 따라 읽기는 남겼다. 잡힌 항목: 소비 분기 3곳 뒤바꿈, `ORI CCR` Set → Clear/Unknown, `ADD.B` → `ADD.W` 색인, 표 색인 배수·`LSL` 폭·색인 부호 확장, `SUBQ` 빌림 판정, `TST.L` bit 31, 단계 값(`5fe9e` 2, `5fef8` 5, `5ff64` 0, `600d6` 0), 부모 BYTE `77` 비교 값, `CLR.B 62`·`ST.B 62`, `5ffb4` BYTE `79`, 표 선택(`5ff98`, `5fdf2`), 부모 추종 비교 폭·`MOVE.B D0,76` 저장, `600ee` 3, 애니메이션 변위 `13c` `18`, `6013e`·`6016a` BYTE 판정 폭, `60154` `80`, `ANDI.W` 생략·LONG 폭, 자식 값 `60516`, `4970a` 인자, `601e6` `8f`·`1a`, `60200` `ANDI.B`/`ADDQ.B`/`7e`, `3c44` 단계 `7e`, `602fa` 부모 `62`, `60052` `82`, `dcf56` 값·변위, `BSET` RMW, id `804`, `8ebe` id, `6031e` `D0.W`, `5fd24` `78`, 설치 `5e8b0`·`5fd9a`, `5ff82`·`5ff14` 분기, BSR 복귀 PC, `601f2` 빌림 분기.
- [F] 실제 ROM 차분(scratch `realrom/real27.py`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM, LONG `22` = 실제 banked 기록 또는 RAM 사본, 실제 ROM 표, LONG `26` = 0 또는 실제 기록의 애니메이션 목록, native는 STOP·`2a00`·`2a24`·C++ routing 밖 첫 PC·`49f8c`/`49f96`(선언 stop)에서 멈춤): 3 seed × 1,500 case 불일치 0/0/0, 시작 162/162(seed마다). 실제 생산자 뒤 소비자 native 분기 비교(seed 1/2/3): `5ff7e` 96/88/82(interpreter `49fc6`), `6019e` 81/77/89, `601c8` 72/84/79(fade_card `28ae`). C++ stop C(Unknown/Clear/Set) seed 1 1,302/28/170. clean stop이 없는 native case는 건너뜀(1,134/1,038/1,158): 대부분 실제 `4a46c`(N04)·interpreter가 무작위 상태로 PC < `400`에 닿는 경우(`low`; 단계 상태기계 머리 `5fe7a`~`5ff72`, `6013e` 계열이 `4a46c`로 가는 경로)다. interpreter 따라가기(`FOLLOW_ANIM`) 2 × 1,000 case 불일치 0(건너뜀 1,101/1,176), 소비자 비교 `5ff7e` 96/110, `6019e` 68/59, `601c8` 57/62.
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `77e5485` 일치 pass 14,408·node 122,462·불일치 0(`diff_results.json` SHA256 `a6c41695…`) → N27 뒤 pass **14,648**·node **126,688**·불일치 0(`ad8c6c0a…`). 차이는 seed 32 33뿐(pass 0 → 120, native 120 frame 전부 일치). 첫 미연결 목록에서 `dcf56`이 사라졌다.
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 132·pass 52,800·node 396,091·불일치 0(`verification.json` SHA256 `67a1a03e…`) → N27 뒤 complete **134**·pass **53,600**·node **403,677**·불일치 0, chain 불일치 0, `other` 0(`30f8b214…`; 두 번 실행해 같은 SHA). **새 완주 seed 32 33**(각 400 frame, node 3 → 3,796), 잃은 seed 0, 다른 seed의 pass·node 변화 0. 재범위 예측 134/135와 같다. 남은 미완: 116 117(frame 0 callback `38ba0`, N31), guard 136~140(`deadbeef`), 141(native 끝 홀수 PC).
- [U] 남은 미확인: `5fe50` 단계 상태기계·BSR `5ff90`·`600ee` 이후·`6013e` 이후(난수·`28ae` 자식 `60516`)·`60408`·`604fe`는 자연 400 frame에서 실행되지 않는다(실제 ROM 차분·fixture로만 덮음). `60516..` 고아 사슬(미연결 callee `490ba` 포함)의 소유 단위는 미정이다(결정 2).
