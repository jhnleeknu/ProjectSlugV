# `2986` 자식 표 `227fc..2282c`의 child callback 일곱과 공용 helper 구현 계약 B4(= B4a)

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. 후보는 B3c 계약 결정 5(자식 표의 child callback 8개 `22ad4 22b04 22d94 22dbc 2308e 23058 235ca 23a3e`)와 demo 조사 문서의 U06 옆 script 처리기 `e74f8`(점프 표 `e7504`, `28ae` 자식 `2b7be` / `e7996`)다. 두 후보의 정적 closure를 프로젝트 leader 규칙으로 다시 쟀고(아래 "크기 판정"), 합이 약 220 block을 넘으므로 이 단위(B4 = B4a)는 자연 경계에서 218 block만 구현하고 나머지(B4b)는 끝 절에 정확히 명세한다. 결정 항목(끝)은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 코드와 고정 표는 모두 `<100000`이라 CPU 주소와 파일 오프셋이 같다. bank 창 읽기 `20006c..200098`은 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다(아래 "자료 표"). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `52bad15`(branch `claude/b-final` = PR #4 head). routing 기준 `engine/src/animation_machine.cpp` SHA256 `1e7625c722bca323152a57d6cd81f2237a5fdff51c13a1563b6e430c26ccbf76`. dispatch 사슬을 Python 조건식으로 옮겨 "routing된 PC"를 판정했다(scratch `hroute.py`, B3c 도구와 같은 방식, 경로만 이 작업 트리).
- [F] 정적 디코드: capstone M68000. block 시작 규칙은 B1 계약 "기준 입력"과 같다(분기 대상·fall-through, JSR/BSR 복귀 PC, `MOVE.L #imm,(A6)` 설치 값). 설치 값은 변위 없는 `(A6)`만 센다: `MOVE.L #22a02,8c(A6)`·`MOVE.L #235b6,80(A6)`은 자료 목록 포인터라 시작이 아니다(B3c 도구의 정규식이 변위 붙은 `d(A6)`까지 세던 것을 고쳤다; 이 수정으로 B3c 결과는 바뀌지 않는다 — B3c 범위에는 그런 쓰기가 없다). `28ae`/`2986` 자식 값(`MOVEA.L #값,A0` 뒤 `JSR 28ae`/`2986`)은 closure에 넣지 않고 자식 후보로 적는다(B3c 결정 5와 같은 관례). routing된 PC에서 멈춘다.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/b4/`
  - `sdec.py` `hroute.py` `closure2.py` `b3adis.py` `refs.py`(B3c scratch 복사, 경로와 설치 정규식만 바꿈), `unit_b4.py`(단위 정의·분류), `combos.py` `sizes.py` `sizes2.py`(크기 판정), `xref.py` `lrefs.py`(ROM 전체의 직접 참조·LONG 상수 검색), `probe_scan.py`(기존 시험의 범위 안 상수 검색), `data.py`(자료 표 전사), `blkdis.py`(block 표시 역어셈블 `b4a_dis.txt`).
  - `starts.txt`(시작 218개) SHA256 `cf02258d78b56e305866e777be61a2d0549d6cd74b48906aa178d5b828d40472`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 크기 판정

[F] 진입별 정적 closure(routing된 PC는 제외, 자식 값은 따라가지 않음; scratch `combos.py` `sizes.py` `sizes2.py`):

| 후보 | 진입 | block | 비고 |
| --- | --- | --- | --- |
| (a) G1 | `22ad4` `22b04` | 78 | 공용 helper 포함 |
| (a) G2 | `22d94` `22dbc` | 70 | |
| (a) G3 | `2308e` `23058` | 86 | |
| (a) G4 | `235ca` | 50 | |
| (a) G5 | `23a3e` | 62 | helper `49636..496a6` |
| (a) 합 | 8개 | **266** | 공용 35 block(`1c9b8..` 8, `22a10..` 8, `22c82` `22c86`, `4bb52..` 17) |
| (b) | `e74f8`, 점프 표 항목 `e7504` `e7508`, `28ae` 자식 `2b7be` `e7996` | **35** | 간접 `JSR e7504(PC,D0.W)` 1곳(2 항목 표) |
| (a)+(b) | | **299** | 약 220 초과 |

- [F] 자연 경계: 자식 표는 플레이어 BYTE `9e`(B3c `1c14c`의 index)로 고른다 — `227fc`(9e = 0: `22b04` `23058` `22dbc`), `2280c`(9e = 1: `22ad4` `2308e` `22d94`), `2281c`(9e = 2: `235ca` ×3), `2282c`(9e = 3: `23a3e` ×3). G1 + G2 + G3 + G4 = **218 block**이 표 `227fc` `2280c` `2281c`의 자식 전부(BYTE `9e` = 0, 1, 2)이고 공용 helper를 모두 담는다. 나머지는 표 `2282c`의 `23a3e`(새 block 48)와 (b)(35)다.
- [F] **이 단위 B4(= B4a)는 218 block을 구현한다.** B4b 이하는 끝 절 "후속 단위 명세"에 정확히 적는다.

## 요약

- [F] **범위·block 수**(8 범위, 합 218):

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `1c9b8..1c9ec` | 52 | `4bfe4e8d90bb1b90b38e50a74bfe7bca77d6228c47649a4ba0a364229526bf3e` | 8 | 26 |
| `22a10..22a8a` | 122 | `234718ca0556311246ffb9d3983de0687f6315744a5ba6a3acb126e90e55d813` | 8 | 61 |
| `22ad4..22c8c` | 440 | `2037545a1a9765b3858a07ffc163503f68b33b673d58daba0239a8be9163edb4` | 25 | 220 |
| `22c8e..22d64` | 214 | `8c624c964449ebee65f53341fb767a7898d662e24f365709d9b2ad653e82bb42` | 20 | 107 |
| `22d94..22f7a` | 486 | `0049e55ce4741e33faa3aaec05390d2bad4c60c6835c57521e39e2c19ed5d490` | 35 | 243 |
| `23058..2334c` | 756 | `420f3f0b4e3a9d6761d0f4aa11937976019d9db006642366c3e028e17a989e9d` | 69 | 378 |
| `235ca..23774` | 426 | `f74d9567f53e9265e9fdc6a9b16a65ea26ba8f22b37b034ae54a3ed8d145943f` | 36 | 213 |
| `4bb52..4bc04` | 178 | `d80ec18a10deb7d29a9e02ce280f953e21b3bd31b4a873c888c5004f0c2df485` | 17 | 89 |
| 합계 B4 | 2674 | 이어 붙인 바이트 `81483ad1200c2c9c6e33f4d62c4fa6b7c361108bdfe3d79709d8099071a9e0aa` | **218** | 1337(내부 1119) |

- [F] 명령 592개, 정적 closure가 여덟 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 연속 Bcc 묶음 없음, 간접 분기 없음(계산 jump 표 없음), TRAP·I/O port·bank 변경·X 소비(ADDX/SUBX/ROX)·DIV 없음.
- [F] **현재 routing과의 관계**: 여덟 범위의 짝수 PC는 모두 routing 밖이다(겹침 0). 경계 이웃: `1c9b6`(routing 밖, `1c9b4 JMP 1c1f4(PC)`의 중간)·`1c9ec`(routing 밖 다른 함수), `22a0e`(routing 밖 RTS; 앞 `22a02..22a0e`는 자료 목록)·`22a8a`(routing 밖 자료 `22a8a..22a9e`, 이어 다른 함수 `22a9e`), `22ad2`(`22ad0 BRA.W 22b30`의 중간; 함수 `22a9e`는 B3c 이웃 `2298c`의 자식)·`22c8c`(도달하지 않는 `RTS`, 결정 2)·`22d64`(자료 `22d64..22d94`), `22f7a`(routing 밖 `2986` 자식 코드), `23056`(자료 `22fe0..23058`)·`2334c`(routing 밖 `28ae` 자식 코드), `235c8`(자료 `2355c..235ca`)·`23774`(routing 밖 `2986` 자식 코드), `4bb50`(routing된 U08b `RTS`)·`4bc04`(routing된 N04 block).
- [F] **나가는 곳은 모두 routing돼 있다**: callee `1ab80` `287e` `28ae` `2986` `3af8` `43e34` `443d2` `491b6` `49214` `4970a` `49f8c` `49fc6` `4ae4a` `4be06` `4be34` `8cda` `8ebe` `8ff4` `ea5e0`, 출구 `JMP 2a00`(삭제) 6곳. routing 밖 값은 자료와 자식 callback 값뿐이다(아래).
- [F] **새 자식 값**(실행은 이후 pass, 이 단위 밖): `2986` 자식 `22f7a`(`22e88` `22f0c`)·`23774`(`235ee`), `28ae` 자식 `2334c`(`231ce` `23274` `232ae`)·`d206a`(`23180`).
- [F] **참조**(ROM 전체 직접 분기·LONG 상수 검색, scratch `xref.py` `lrefs.py`): 진입 7개는 자식 표 LONG뿐이다(`22b04` = `22800`, `23058` = `22804`, `22dbc` = `22808`, `22ad4` = `22810`, `2308e` = `22814`, `22d94` = `22818`, `235ca` = `2281e..2282c`의 셋). 범위 밖에서 들어오는 분기: `22ad0 BRA.W 22b30`(함수 `22a9e`), `23558 BRA.W 231bc`(`2334c` 자식 코드), `2390c BCS.W 22c82`·`23bbe BCC.W 22c82`(B4b 후보), `23912`·`23be4 BSR.W 22a4c`(B4b 후보), `23834`·`23a84 JSR 1c9b8`(B4b 후보와 그 이웃), `4bb52`의 JSR 15곳(`25158` `27efe` `281a0` `291ca` `294a4` `29cf8` `86cde` `86cea` `86cf6` `d199e`, routing된 N04 `72d14` `72d20` `72d2c`, 이 단위 `22bc6` `22ee2`) + `4ad32 BSR.W`. 모두 block 시작으로 들어온다(내부 PC 착지 0). LONG 상수 `23228`이 `d119e` `e9726`에도 있으나 명령 바이트(`3028 0002 3228`)의 우연이다.
- [I] 의미: 일곱 진입은 플레이어 무기(`1c114`가 `2986`으로 만드는 탄)의 callback이다. `22ad4`/`22b04`(설치 `22b96`)는 `443d2`로 속도를 정하고 `4be34`가 주는 각도 BYTE `82`로 sin/cos 표(`4411e`/`4419e`)를 써서 휘는 궤도(유도)를 그리고, 맞으면(`4ae4a` D0 ≠ 0) `22cb0`(설치 `22d06`)의 폭발 목록으로 바뀐다. `22d94`/`22dbc`(설치 `22e48`)는 반사(`NEG.L 36`)와 분열(`2986` 자식 `22f7a`)을 하는 탄, `23058`/`2308e`(설치 `230fa`)는 맞으면 `28ae` 자식(`d206a`, 이어 `2334c` 넷)을 뿌리는 탄, `235ca`(설치 `23664`)는 `2986` 자식 `23774`와 짝을 이루는 탄이다. `1c9b8`/`1c9ce`는 플레이어 기록(`5450(A5)`/`5460(A5)`, D0 bit 0으로 고름) BYTE `1`의 탄 수 증감, `22a4c`는 그 감소를 한 번만 하는 표시(WORD `76` bit 15), `22a62`는 화면 위쪽 고정점으로의 감쇠 이동, `4bb52`는 work RAM `5b88(A5)`의 8 × 16 WORD 격자에 중심 `100`·상하좌우 `c0`·대각 `80`을 더하는 영향도 기록이다. 이름은 확정하지 않는다.

## 공통 규칙·native 검증 계획

B1 계약 "공통 규칙"과 "공통 native 검증 계획", B2 계약 "자식(`28ae`) 진입 fixture", B2c~B3c 계약의 공유 파일·macOS seed 관례를 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_b4.cpp`, 함수 `animation_objects_b4_block`. 오류 문자열은 `unsupported animation objects b4 PC`(범위 안 내부 PC 직접 진입)와 `objects b4 caller requires known carry`(C 소비 block에 Unknown C; 소비자 8개가 있으므로 둔다)다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(여덟 범위), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 8개), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, test 목록 실행 줄, 시험 target; Codex의 object 재사용 구조 유지, SOURCES·HEADERS 줄은 각각 하나), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** 이 단위에서 routing 밖으로 나가는 실행 PC는 없다. 다른 단위 시험·spec이 stop으로 확인하던 `4bb52`(N04 `72d08` `72d1a` `72d26`)는 그대로 통과해야 한다(stop 판정은 routing보다 먼저). U08b 시험 `rom_outside[]`의 `4bb52`는 U08b 범위 밖인지만 본다(그대로 참). rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다(F4 관례).
- **오류 fixture의 실패 PC**(리뷰 0264 L-1). 기대 오류 fixture마다 실패 PC를 적는다. 실패 PC가 진입 PC와 다르면 같은 상태를 stop = 실패 PC로 실행해 정확히 그 PC에서 멈추는지(성공) 함께 확인한다.
- **자료 읽기**(live bus, F1 결정 3): 모든 표 읽기는 원본 주소 계산 그대로 live bus로 읽는다. 상한 검사는 원본에 없으므로 두지 않는다. 대상: LONG `20006c` `200070` `200078` `20008c` `200094`(bank 창), WORD `4411e + sext(D4.W)`·`4419e + sext(D4.W)`(sin/cos), WORD `22d82 + sext(2·(D0 & ff))`, LONG `(LONG 8c(A6))`·`(LONG 80(A6))` 목록(`22a02`·`235b6` 또는 RAM). 단위 시험은 이 고정 ROM·bank 주소에 합성 typed physical byte를 둔다(ROM 자료가 아니다). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `4bb52 MOVEM.L D0-D1/A0,-(A7)`는 A0, D1, D0 순으로 LONG 3개를 넣고(낮은 주소에 D0) `4bbfe MOVEM.L (A7)+,D0-D1/A0`가 D0, D1, A0 순으로 꺼낸다(flag 불변). `2360a MOVEM.L 2e(A6),D0-D3/A1`·`MOVEM.L D0-D3/A1,2e(A0)`는 LONG 5개(`2e` `32` `36` `3a` `3e` → D0 D1 D2 D3 A1)를 오름차순으로 옮긴다.
- **정수 연산.** `MULS.W`(부호 16 × 16 → 32, `(An,D4.W)` WORD 표 원소), `ASR.L #8/#4/#3/#1`·`ASR.W #5/#1`(부호 bit 채움; `.W`는 하위 WORD만), `LSL.W #3`·`LSR.W #4/#1`(WORD), `NEG.L` 레지스터·메모리, `SUB.L`/`ADD.L`(32 bit wrap), `ADD.W`/`SUB.W` 메모리(WORD wrap), `ADDI.W`/`SUBI.W`/`ANDI.W`/`ORI.W`(WORD), `ADDQ.B`/`SUBQ.B`/`SUBQ.W`/`ADDQ.W`/`ADDQ.L`/`ADDI.L`, `CLR.W Dn`(하위 WORD만)·`CLR.B`/`CLR.W`/`CLR.L` 메모리, `MOVEQ`(LONG), `MOVE.B`/`MOVE.W` → Dn(상위 유지), `ADDA.W`·`(An,Dn.W)` index(부호 확장), `LEA d16(A5)`(부호 확장 변위: `5450` `5460` `5b88`)를 68000 폭 그대로 명시 구현한다. 비교: `CMPI.W`/`CMPI.B` + `BCC`/`BCS`(무부호), `CMPI.W #2` + `BLE`·`CMPI.W #0` + `BGT`·`CMPI.B #4` + `BLT`·`TST.B` + `BLE`(부호), `TST.B`/`TST.L`/`CMPI.L #0` + `BEQ`/`BNE`, `MOVE.W`/`MOVE.L`/`SUB.L` + `BMI`/`BPL`(bit 15/31), `SUBQ.W #1` + `BCS`/`BCC`(이전 값 0이면 C), `SUBI.W #140` + `BCC`(이전 값 ≥ 140이면 C 없음). 모두 같은 block 안에서 만들고 소비한다.
- **macOS seed.** 자연 seed가 필요한 V1·D1 실행은 B3a~B3c와 같은 scratch wrapper가 `D.SEED_DIR`만 역사 관측 `artifacts/stage_entry_body`(SHA256 `1f65100f…`)로 바꾼다(도구 파일은 고치지 않음).

## carry

- [F] **소비 block 8개**(callee가 돌려준 C를 읽음; 각 block은 Bcc 하나):
  - `22d2c BCC.W 22d36` / `23768 BCC.W 23772`: `49fc6`(interpreter known C). Clear → 분기 대상, Set → `JMP 2a00` block(`22d30` `2376c`).
  - `23190 BCC.W 231a2` / `231de BCC.W 231f0` / `23284 BCC.W 23296` / `232be BCC.W 232d0`: `28ae`(성공 `2908 ORI` Set, 실패 `2912 ANDI` Clear, A0 = 더미 `100e98`). Clear → 분기 대상, Set → `23194` `231e2` `23288` `232c2`(`CLR.W D0; CLR.W D1; JSR 4970a`).
  - `23336 BCC.W 23348`: `287e`(`CMP.W 10(A0),D0`, LONG `8(A6)` → A0, WORD `10(A6)`; C = 무부호 미만). Clear → `23348`, Set → `2333a`.
  - `236be BCS.W 22c82`: `1ab80`(N05 화면 범위 검사; 밖이면 `1aafc` Set, 안이면 `1abd4 ANDI` Clear). Set → `22c82`, Clear → `236c2`.
- [F] 8개만 `carry_preserving_pc`에 넣는다(B2c~B3c 꼴). Unknown C로 들어오면 checked 오류다.
- [F] **known C 생산**: `2319e` `231ec` `23292` `232cc`(`ORI.B #1,CCR`, 각 block의 유일한 명령)는 C Set을 만들고 다음 block(`231a2` `231f0` `23296` `232d0`)으로 이어진다. 다음 block은 소비자가 아니고 첫 명령이 `MOVE`(C를 지움)라 아무도 이 C를 읽지 않는다. 실행부는 원본과 같게 이 넷에서 C Set을 남긴다(B3a `2b5fc` 관례; 정확하고 해가 없음). 그 밖의 모든 block은 진입 때 Unknown이 되고 Unknown으로 끝난다(block 안의 비교 C를 밖으로 내보내지 않는다).
- [F] 공용 helper의 반환 C를 읽는 호출자는 없다: `1c9b8`(복귀 `22b90` `22e32` `230e8` `235e2`, 범위 밖 `2383a BSET` `23a8a MOVE`), `1c9ce`(`22a5a ORI.W`), `22a10`(`22bde` `22efa` MOVE), `22a4c`(`22c86 JMP` `22c98 MOVEQ` `22eb8` `22ee2` `236c8`, 범위 밖 `23916 MOVE` `23be8 LEA`), `22a62`(`22c46` `22f56` `2311e`), `4bb52`(`22bcc MOVEQ` `22ee8 MOVE`, N04 `72d1a SUBI` `72d26 ADDI` `72d32 SUBI`). 그래서 소비자 없는 carry 보존은 만들지 않는다.
- [F] block 경계를 건너 다시 계산하는 flag는 없다(모든 Bcc는 같은 block 안의 비교·TST·MOVE나 callee C를 읽는다). `22f32 SUBQ.W #1,7c(A6); BNE.W 22f3a`는 두 쪽이 모두 `22f3a`다.

## 공용 helper `1c9b8..1c9ec`(8)

- **`1c9b8`**: A4 := A5 + `5450`, D0.W &= 1(WORD), 결과 0 → `1c9c8`, 아니면 `1c9c4`(A4 := A5 + `5460`). **`1c9c8`**: BYTE `1(A4)` += 1(BYTE wrap), `RTS`.
- **`1c9ce`**: 같은 선택(`1c9da`: A4 := A5 + `5460`). **`1c9de`**: BYTE `1(A4)` = 0 → `1c9ea RTS`, 아니면 `1c9e6`: BYTE `1(A4)` −= 1, `1c9ea RTS`.

## 공용 helper `22a10..22a8a`(8)

- **`22a10`**(회전, `RTS`로 끝나는 한 block): A0 := `4411e`, A1 := `4419e`, D2 := D0, D3 := D1, D4.W := 2·D4.W(WORD), D2 := ASR.L 8, D3 := ASR.L 8, D2 := sext(D2.W) × W(A0 + sext(D4.W)), D3 := sext(D3.W) × W(A1 + sext(D4.W)), D2 −= D3, D2 := ASR.L 8, D3 := D2, D2 := sext(D2.W) × W(A0 + …), D3 := sext(D3.W) × W(A1 + …), D3 := −D3, D0 −= D2, D1 −= D3, D0 := −D0, D1 := −D1, D0 += D2, D1 += D3, `RTS`. 표 WORD 읽기는 네 번(같은 두 주소를 두 번씩), 순서는 A0 표, A1 표, A0 표, A1 표.
- **`22a4c`**: D0.W := WORD `76`, bit 15 = 1 → `22a60`, 아니면 `22a54`: `JSR 1c9ce`(복귀 `22a5a`). **`22a5a`**: WORD `76` |= `8000`. **`22a60`**: `RTS`.
- **`22a62`**: D0 := `fff05398` − LONG `3a`, D0 := ASR.L 4, LONG `3a` += D0, D0 := 0 − LONG `36`, bit 31 = 1 → `22a82`, 아니면 `22a7c`: D0 += `f`(LONG). **`22a82`**: D0 := ASR.L 4, LONG `36` += D0, `RTS`.

## child `22ad4`/`22b04` `22ad4..22c8c`(25) + `22c8e..22d64`(20)

- **`22ad4`**: WORD `20` := `92`, LONG `22` := LONG `20006c`(bank 창), D0.W := `204`, D1.B := 0, `JSR 8ebe`(복귀 `22af0`). **`22af0`**: A1 := `23e02`, D0.W := `100`, `JSR 49f8c`(복귀 `22b00`). **`22b00`**: `BRA.W 22b30`.
- **`22b04`**: 같은 꼴(D0.W := `27c`, 복귀 `22b20`). **`22b20`**: A1 := `23cfa`, D0.W := `100`, `JSR 49f8c`(복귀 `22b30`).
- **`22b30`**: D0 := `bc897`, D1.B := BYTE `78`, `JSR 443d2`(복귀 `22b40`).
- **`22b40`**: LONG `36` += D0, LONG `3a` := D1, D2.W := `280`, BYTE `15` bit 0 = 0 → `22b58`, 아니면 `22b56`: D2.W := −D2.W.
- **`22b58`**: WORD `80` := D2.W, WORD `7e` := 0, WORD `68` := `e000`, WORD `1e` := `e000`, BYTE `15` bit 4 := 1, bit 0 := 0, WORD `7c` := 1, `JSR ea5e0`(복귀 `22b86`).
- **`22b86`**: D0.W := WORD `76`, `JSR 1c9b8`(복귀 `22b90`). **`22b90`**: 설치 `22b96`.
- **`22b96`**(설치 값): A0 := `229a8`, `JSR 4ae4a`(복귀 `22ba0`). **`22ba0`**: D0.B ≠ 0 → `22c8e`, 아니면 `22ba6`.
- **`22ba6`**: LONG `84` := LONG `36`, LONG `88` := LONG `3a`, `JSR 4be34`(복귀 `22bb8`). **`22bb8`**: WORD `82` := D4.W, BYTE `15` bit 7 = 0 → `22c42`, 아니면 `22bc6`: `JSR 4bb52`(복귀 `22bcc`).
- **`22bcc`**: D4 := BYTE `82`(MOVEQ 뒤, 상위 0), D0 := LONG `84`, D1 := LONG `88`, `BSR.W 22a10`(복귀 `22bde`).
- **`22bde`**: LONG `36` := D0, LONG `3a` := D1, A0 := `4411e`, A1 := `4419e`, D4 := BYTE `82`, D4.W := 2·D4.W, D0 := D2, D1 := D3, D0 := ASR.L 8, D1 := ASR.L 8, D0 := sext(D0.W) × W(A0 + sext(D4.W)), D1 := sext(D1.W) × W(A1 + …), D0 −= D1, D0 := ASR.L 8, D0 := ASR.L 3, D1.W := WORD `80`, D0.W −= D1.W, D0.W := ASR.W 1, WORD `80` += D0.W, D1.W := D1.W << 3, D0.W := D1.W, D0 := sext(D0.W) × W(A0 + …), D1 := sext(D1.W) × W(A1 + …), D1 := −D1, D0 −= D2, D1 −= D3, D0 := ASR.L 1, D1 := ASR.L 1, LONG `36` += D0, LONG `3a` += D1, WORD `7c` −= 1; 이전 WORD = 0(빌림) → `22c94`, 아니면 `22c42`.
- **`22c42`**: `BSR.W 22a62`(복귀 `22c46`).
- **`22c46`**: D0.W := WORD `80`, D1.W := D0.W, D1.W := ASR.W 5, WORD `80` −= D1.W, D0.W += WORD `7e`, D0.W &= `1fff`, WORD `7e` := D0.W, `JSR 49fc6`(복귀 `22c64`).
- **`22c64`**: D0.W := WORD `42`, 무부호 D0.W ≥ `140` → `22c82`, 아니면 `22c70`: D0.W := WORD `46` − `100`, 무부호 ≥ `140` → `22c82`, 아니면 `22c80 RTS`.
- **`22c82`**: `BSR.W 22a4c`(복귀 `22c86`). **`22c86`**: `JMP 2a00`.
- **`22c8e`**: `JSR 4be06`(복귀 `22c94`). **`22c94`**: `BSR.W 22a4c`(복귀 `22c98`).
- **`22c98`**: D0 := 0, LONG `36` := 0, LONG `3a` := 0, LONG `(A6)` := `22cb0`(설치만), `JSR 49fc6`(복귀 `22cae`). **`22cae`**: `RTS`.
- **`22cb0`**(설치 값): WORD `20` := `d2`, LONG `22` := LONG `20008c`, D0.W := `1a26`, `JSR 3af8`(복귀 `22cc8`). **`22cc8`**: `JSR 8ff4`(복귀 `22cce`). **`22cce`**: D0.W := `378`, D1.B := 0, `JSR 8ebe`(복귀 `22cdc`).
- **`22cdc`**: WORD `68` := `1001`, WORD `1e` := `1001`, A1 := `23f22`, D0.W := `100`, `JSR 49f8c`(복귀 `22cf8`). **`22cf8`**: LONG `8c` := `22a02`, 설치 `22d06`(fall-through).
- **`22d06`**(설치 값): A4 := LONG `8c`, LONG `(A4)` = 0 → `22d20`, 아니면 `22d14`: A0 := LONG `(A4)`, A4 += 4, LONG `8c` := A4, `JSR 4ae4a`(복귀 `22d20`).
- **`22d20`**: `JSR 43e34`(복귀 `22d26`). **`22d26`**: `JSR 49fc6`(복귀 `22d2c`). **`22d2c`**(소비자): Clear → `22d36`, Set → `22d30 JMP 2a00`.
- **`22d36`**: D0.W := WORD `42` + `20`, 무부호 < `180` → `22d4c`, 아니면 `22d46 JMP 2a00`. **`22d4c`**: D0.W := WORD `46` − `100`, 무부호 < `140` → `22d62 RTS`, 아니면 `22d5c JMP 2a00`.

## child `22d94`/`22dbc` `22d94..22f7a`(35)

- **`22d94`**: WORD `20` := `e2`, LONG `22` := LONG `200094`, BYTE `8a` := `ff`, A1 := `240ca`, D0.W := `100`, `JSR 49f8c`(복귀 `22db8`). **`22db8`**: `BRA.W 22de4`.
- **`22dbc`**: 같은 꼴(BYTE `8a` := 0, A1 := `23ffa`, 복귀 `22de0`). **`22de0`**: `BRA.W 22de4`.
- **`22de4`**: D0.W := `20a`, D1.B := 0, `JSR 8ebe`(복귀 `22df2`). **`22df2`**: D0 := `bc897`, D1.B := BYTE `78`, `JSR 443d2`(복귀 `22e02`).
- **`22e02`**: LONG `36` += D0, LONG `3a` := D1, WORD `68` := `e000`, WORD `1e` := `e000`, BYTE `15` bit 0 := 0, WORD `7c` := 3, `JSR ea5e0`(복귀 `22e28`).
- **`22e28`**: D0.W := WORD `76`, `JSR 1c9b8`(복귀 `22e32`). **`22e32`**: BYTE `15` bit 4 := 1, BYTE `8b` := 0, WORD `80` := `1e`, 설치 `22e48`.
- **`22e48`**(설치 값): BYTE `61` bit 3 ≠ 0 → `22eb8`, 아니면 `22e52`: A0 := `22d64`, `JSR 4ae4a`(복귀 `22e5c`). **`22e5c`**: D0.B = 0 → `22eb8`, 아니면 `22e62`.
- **`22e62`**: A0 := `22d82`, D0.W &= `ff`, D0.W *= 2, D0.W := WORD `(22d82 + sext(D0.W))`, `JSR 3af8`(복귀 `22e76`).
- **`22e76`**: LONG `36` := −LONG `36`, D0 := LONG `3a`, bit 31 = 0 → `22e88`, 아니면 `22e82`: D0 := −D0, LONG `3a` := D0.
- **`22e88`**: A0 := `22f7a`, D0.W := `1e`, A1 := `100bf4`, `JSR 2986`(복귀 `22e9e`). **`22e9e`**: BYTE `8a(A0)` := BYTE `8a(A6)`, D0 := 0, D1 := 0, `JSR 49214`(복귀 `22eae`).
- **`22eae`**: BYTE `61` bit 3 := 1, `BSR.W 22a4c`(복귀 `22eb8`).
- **`22eb8`**: LONG `82` := LONG `36`, LONG `86` := LONG `3a`, `JSR 4be34`(복귀 `22eca`). **`22eca`**: WORD `7e` := D4.W, BYTE `15` bit 7 = 0 → `22f3a`, 아니면 `22ed8`: BYTE `61` bit 3 := 1, `BSR.W 22a4c`(복귀 `22ee2`).
- **`22ee2`**: `JSR 4bb52`(복귀 `22ee8`). **`22ee8`**: D0 := LONG `82`, D1 := LONG `86`, D4 := BYTE `7e`(MOVEQ 뒤), `JSR 22a10(PC)`(복귀 `22efa`).
- **`22efa`**: LONG `36` := D0, LONG `3a` := D1, 부호 WORD `3a` ≤ 2 → `22f32`, 아니면 `22f0c`(`22e88`과 같은 꼴, 복귀 `22f22`). **`22f22`**: `22e9e`와 같은 꼴(복귀 `22f32`).
- **`22f32`**: WORD `7c` −= 1, → `22f3a`(BNE의 두 쪽 모두).
- **`22f3a`**: BYTE `61` bit 3 = 0 → `22f52`, 아니면 `22f44`: WORD `80` −= 1, 이전 WORD ≠ 0 → `22f52`, 아니면 `22f4c JMP 2a00`.
- **`22f52`**: `BSR.W 22a62`(복귀 `22f56`). **`22f56`**: `JSR 49fc6`(복귀 `22f5c`).
- **`22f5c`**: D0.W := WORD `42`, 무부호 ≥ `140` → `22c82`, 아니면 `22f68`: D0.W := WORD `46` − `100`, 무부호 ≥ `140` → `22c82`, 아니면 `22f78 RTS`.

## child `23058`/`2308e` `23058..2334c`(69)

- **`23058`**: WORD `20` := `9a`, LONG `22` := LONG `200070`, D0.W := `203`, D1.B := 0, `JSR 8ebe`(복귀 `23074`). **`23074`**: A1 := `2419a`, D0.W := `100`, `JSR 49f8c`(복귀 `23084`). **`23084`**: BYTE `84` := 0, `BRA.W 230c0`.
- **`2308e`**: 같은 꼴(D0.W := `872`, 복귀 `230aa`). **`230aa`**: A1 := `24240`, `JSR 49f8c`(복귀 `230ba`). **`230ba`**: BYTE `84` := 1.
- **`230c0`**: D0 := `a4f84`, D1.B := BYTE `78`, `JSR 443d2`(복귀 `230d0`).
- **`230d0`**: LONG `36` += D0, LONG `3a` := D1, BYTE `15` bit 4 := 1, D0.W := WORD `76`, `JSR 1c9b8`(복귀 `230e8`).
- **`230e8`**: WORD `68` := `e000`, WORD `1e` := `e000`, 설치 `230fa`.
- **`230fa`**(설치 값): A0 := `22fe0`, `JSR 4ae4a`(복귀 `23104`). **`23104`**: D0.B = 2 → `2315e`, 아니면 `2310c`: D0.B = 1 → `2315e`, 아니면 `23114`.
- **`23114`**: `JSR 4be34`(복귀 `2311a`). **`2311a`**: `BSR.W 22a62`(복귀 `2311e`). **`2311e`**: `JSR 49fc6`(복귀 `23124`).
- **`23124`**: BYTE `15` bit 7 = 0 → `23134`, 아니면 `2312e`: LONG `(A6)` := `231bc`(설치만, `23134`로 이어짐).
- **`23134`**: D0.W := WORD `42`, 무부호 < `140` → `23146`, 아니면 `23140`: LONG `(A6)` := `23348`(설치만). **`23146`**: D0.W := WORD `46` − `100`, 무부호 < `140` → `2315c RTS`, 아니면 `23156`: LONG `(A6)` := `23348`(설치만), `2315c RTS`.
- **`2315e`**: BYTE `84` = 1 → `23176`, 아니면 `23168`: D0.W := `1a26`, `JSR 3af8`(복귀 `23172`). **`23172`**: `BRA.W 23180`. **`23176`**: D0.W := `1a24`, `JSR 3af8`(복귀 `23180`).
- **`23180`**: A0 := `d206a`, D0.W := `14`, `JSR 28ae`(복귀 `23190`). **`23190`**(소비자): Clear → `231a2`, Set → `23194`.
- **`23194`**·**`231e2`**·**`23288`**·**`232c2`**: D0.W := 0, D1.W := 0(`CLR.W`, 상위 유지), `JSR 4970a`(복귀 각각 `2319e` `231ec` `23292` `232cc`). **`2319e`**·**`231ec`**·**`23292`**·**`232cc`**: `ORI.B #1,CCR`(C Set).
- **`231a2`**: WORD `68(A0)` := `1001`, WORD `1e(A0)` := `1001`, A0 := `22ffe`, `JSR 4ae4a`(복귀 `231b8`). **`231b8`**: `BRA.W 23348`.
- **`231bc`**(설치 값): BYTE `82` := 0, LONG `64` := 0, WORD `32` += 4, `JSR 43e34`(복귀 `231ce`). **`231ce`**: A0 := `2334c`, D0.W := `a`, `JSR 28ae`(복귀 `231de`). **`231de`**(소비자): Clear → `231f0`, Set → `231e2`.
- **`231f0`**: BYTE `60(A0)` := BYTE `60(A6)`, BYTE `84(A0)` := BYTE `84(A6)`, LONG `64` := `100000`, BYTE `84` ≠ 1 → `23228`, 아니면 `2320e`.
- **`2320e`**: WORD `80` := 4, BYTE `83` := `18`, D0.W := `1a99`, `JSR 3af8`(복귀 `23224`). **`23224`**: `BRA.W 2323c`. **`23228`**: WORD `80` := 0, BYTE `83` := 0, D0.W := `1a64`, `JSR 3af8`(복귀 `2323c`).
- **`2323c`**: 설치 `23242`. **`23242`**(설치 값): `JSR 4be06`(복귀 `23248`).
- **`23248`**: WORD `80` −= 1, 부호 WORD `80` > 0 → `232fc`, 아니면 `23256`: BYTE `84` = 1 → `2326a`(WORD `80` := 3), 아니면 `23260`(WORD `80` := 2, `BRA.W 23270`).
- **`23270`**: BYTE `82` += 1, A0 := `2334c`, D0.W := `14`, `JSR 28ae`(복귀 `23284`). **`23284`**(소비자): Clear → `23296`, Set → `23288`.
- **`23296`**: BYTE `60(A0)` := BYTE `60`, LONG `64(A0)` := LONG `64`, BYTE `82(A0)` := BYTE `82`, BYTE `84(A0)` := BYTE `84`, A0 := `2334c`, D0.W := `14`, `JSR 28ae`(복귀 `232be`). **`232be`**(소비자): Clear → `232d0`, Set → `232c2`.
- **`232d0`**: BYTE `60(A0)` := BYTE `60`, D0 := −LONG `64`, LONG `64(A0)` := D0, BYTE `82(A0)` := BYTE `82`, BYTE `84(A0)` := BYTE `84`, 부호 BYTE `82` < 4 → `232fc`, 아니면 `232f6`: LONG `(A6)` := `23328`(설치만).
- **`232fc`**: D0.W := WORD `42`, 무부호 < `140` → `2330e`, 아니면 `23308`: LONG `(A6)` := `23328`(설치만). **`2330e`**: D0.W := WORD `46` − `100`, 무부호 < `140` → `23324`, 아니면 `2331e`: LONG `(A6)` := `23328`(설치만). **`23324`**: `BRA.W 2333a`.
- **`23328`**(설치 값): 부호 BYTE `83` ≤ 0 → `23348`, 아니면 `23330`: `JSR 287e`(복귀 `23336`). **`23336`**(소비자): Clear → `23348`, Set → `2333a`.
- **`2333a`**: 부호 BYTE `83` ≤ 0 → `23346 RTS`, 아니면 `23342`: BYTE `83` −= 1, `23346 RTS`.
- **`23348`**(설치 값이기도 함): `BRA.W 22c82`.

## child `235ca` `235ca..23774`(36)

- **`235ca`**: WORD `20` := `aa`, LONG `22` := LONG `200078`, D0.W := WORD `76`, `JSR 1c9b8`(복귀 `235e2`). **`235e2`**: BYTE `15` bit 4 := 1, `JSR 43e34`(복귀 `235ee`).
- **`235ee`**: A0 := `23774`, D0.W := `1e`, A1 := `100bf4`, `JSR 2986`(복귀 `23604`). **`23604`**: `JSR 491b6`(복귀 `2360a`).
- **`2360a`**: D0 D1 D2 D3 A1 := LONG `2e` `32` `36` `3a` `3e`(A6), LONG `2e..42(A0)` := 그 다섯, WORD `68` := `e000`, WORD `1e` := `e000`, D0.W := `8ba`, D1.B := 1, `JSR 8ebe`(복귀 `23630`).
- **`23630`**: A1 := `2457c`, D0.W := `100`, `JSR 49f8c`(복귀 `23640`). **`23640`**: D0 := `180000`, D1.B := BYTE `78`, `JSR 443d2`(복귀 `23650`).
- **`23650`**: LONG `36` += D0, LONG `3a` := D1, WORD `7e` := `19`, 설치 `23664`.
- **`23664`**(설치 값): A0 := `2355c`, `JSR 4ae4a`(복귀 `2366e`). **`2366e`**: D0.B ≠ 0 → `236c4`, 아니면 `23674`: `JSR 4be34`(복귀 `2367a`).
- **`2367a`**: BYTE `15` bit 7 ≠ 0 → `236c4`, 아니면 `23684`: WORD `7e` −= 1, 이전 WORD = 0 → `236c4`, 아니면 `2368c`.
- **`2368c`**: D0 := `fff00000` − LONG `3a`, D0 := ASR.L 3, LONG `3a` += D0, D0 := 0 − LONG `36`, bit 31 = 1 → `236a8`, 아니면 `236a6`: D0 += 7. **`236a8`**: D0 := ASR.L 3, LONG `36` += D0, `JSR 49fc6`(복귀 `236b4`).
- **`236b4`**: A0 := `235c2`, `JSR 1ab80`(복귀 `236be`). **`236be`**(소비자): Set → `22c82`, Clear → `236c2 RTS`.
- **`236c4`**: `BSR.W 22a4c`(복귀 `236c8`). **`236c8`**: LONG `(A6)` := `236d0`, `RTS`.
- **`236d0`**(설치 값): D0.W := `1a24`, `JSR 3af8`(복귀 `236da`). **`236da`**: WORD `68` := `1001`, WORD `1e` := `1001`, `JSR 8ff4`(복귀 `236ec`). **`236ec`**: D0.W := `80c`, D1.B := 1, `JSR 8ebe`(복귀 `236fa`).
- **`236fa`**: BYTE `7c` := `20`, A1 := `6f536`, D0.W := `100`, `JSR 49f8c`(복귀 `23710`). **`23710`**: LONG `80` := `235b6`, LONG `36` := 0, LONG `3a` := 0, 설치 `23726`.
- **`23726`**(설치 값): A4 := LONG `80`, LONG `(A4)` = 0 → `2373c`, 아니면 `23730`: A0 := LONG `(A4)`, A4 += 4, LONG `80` := A4, `JSR 4ae4a`(복귀 `2373c`).
- **`2373c`**: D0.B := BYTE `14`, D1.W := `80b`, D2.B := BYTE `7c`, `JSR 8cda`(복귀 `2374e`).
- **`2374e`**: WORD `7c` −= `140`, 이전 WORD ≥ `140`(무부호) → `2375c`, 아니면 `23758`: WORD `7c` := 0. **`2375c`**: `JSR 4be34`(복귀 `23762`). **`23762`**: `JSR 49fc6`(복귀 `23768`).
- **`23768`**(소비자): Clear → `23772 RTS`, Set → `2376c JMP 2a00`.

## 공용 leaf `4bb52..4bc04`(17)

- **`4bb52`**: `MOVEM.L D0-D1/A0,-(A7)`, D0.W := WORD `46` − `100`, 무부호 ≥ `100` → `4bbfe`, 아니면 `4bb66`.
- **`4bb66`**: D0.W := (D0.W >> 4) & `e`, D1.W := WORD `42` − `20`, 무부호 ≥ `200` → `4bbfe`, 아니면 `4bb7c`.
- **`4bb7c`**: D1.W := (D1.W >> 1) & `f0`, A0 := A5 + `5b88` + sext(D0.W) + sext(D1.W), WORD `(A0)` += `100`, 무부호 D0.W < 2 → `4bbb8`, 아니면 `4bb96`.
- **`4bb96`**: WORD `−2(A0)` += `c0`, 무부호 D1.W < `10` → `4bbaa`, 아니면 `4bba4`: WORD `−12(A0)` += `80`. **`4bbaa`**: 무부호 D1.W ≥ `f0` → `4bbb8`, 아니면 `4bbb2`: WORD `e(A0)` += `80`.
- **`4bbb8`**: 무부호 D1.W < `10` → `4bbc6`, 아니면 `4bbc0`: WORD `−10(A0)` += `c0`. **`4bbc6`**: 무부호 D1.W ≥ `f0` → `4bbd4`, 아니면 `4bbce`: WORD `10(A0)` += `c0`.
- **`4bbd4`**: 무부호 D0.W ≥ `e` → `4bbfe`, 아니면 `4bbdc`: WORD `2(A0)` += `c0`, 무부호 D1.W < `10` → `4bbf0`, 아니면 `4bbea`: WORD `−e(A0)` += `80`. **`4bbf0`**: 무부호 D1.W ≥ `f0` → `4bbfe`, 아니면 `4bbf8`: WORD `12(A0)` += `80`.
- **`4bbfe`**: `MOVEM.L (A7)+,D0-D1/A0`, `RTS`.

## 자료 표(전사, routing 밖으로 둠)

[F] 원본 바이트 그대로다(scratch `data.py`). index 범위는 원본에 상한 검사가 없어 [I]로 적는다. 실행부는 표 내용을 코드에 넣지 않고 live bus로 읽는다.

| 표 | 범위 | 바이트·SHA256 | 읽는 곳 | 내용 |
| --- | --- | --- | --- | --- |
| bank LONG | CPU `20006c..200098`(bank 창) | 44; bank_base = 물리 `200000`일 때 `98daab9bf17d8c3978e5b309e8dd6355ed676dc22c0b27529f55f919b13f99b0` | `22ad4` `22b04`(`20006c`), `23058` `2308e`(`200070`), `235ca`(`200078`), `22cb0`(`20008c`), `22d94` `22dbc`(`200094`) | 물리 `200000` bank: `20006c` = `00294282`, `200070` = `002945b4`, `200078` = `00294724`, `20008c` = `002977dc`, `200094` = `002996ec`. 물리 `300000` bank: `0024f52c` `00251240` `002540c8` `0025e42c` `00267dc4` |
| sin/cos(WORD) | `4411e..4439e` | 640, `398e75bfcd95d3a2b4dc255a0f93006fbc9368eb5869caaf578c8e649a6fdf83` | `22a10` `22bde`(index 2·BYTE `82`/`7e`, [I] 0..255; sin = `4411e + 2k`, cos = `4419e + 2k`) | 아래 전사 |
| 소리(WORD) | `22d82..22d94` | 18, `0ce48eff4a754266928e2c2a80f15f8bbff4c51f359b345e8c3b4eb30975f12d` | `22e62`(index `4ae4a`의 D0.B, [I] 0..8) | `1a69` `1a9a` `1a9a` `1a69` `1a69` `1a69` `1a69` `1a69` `1a9a` |
| 목록(LONG) | `22a02..22a0e` | 12, `77c8ed890104cc68f935c4f7d9207b3304121418312e876904f0aa6748aea6c8` | `22d06` `22d14`(LONG `8c(A6)`) | `000229c6` `000229e4` `00000000`(끝) |
| 목록(LONG) | `235b6..235c2` | 12, `dbc18c80cde1d5b998a1229521fc76cd4d75ccb3a9e255e3a2c2ca7f63885b38` | `23726` `23730`(LONG `80(A6)`) | `0002357a` `00023598` `00000000`(끝) |

sin/cos `4411e..4439e`(WORD 320개, 한 줄 16개):

```
4411e: 0000 0006 000d 0013 0019 001f 0026 002c 0032 0038 003e 0044 004a 0050 0056 005c
4413e: 0062 0068 006d 0073 0079 007e 0084 0089 008e 0093 0098 009d 00a2 00a7 00ac 00b1
4415e: 00b5 00b9 00be 00c2 00c6 00ca 00ce 00d1 00d5 00d8 00dc 00df 00e2 00e5 00e7 00ea
4417e: 00ed 00ef 00f1 00f3 00f5 00f7 00f8 00fa 00fb 00fc 00fd 00fe 00ff 00ff 0100 0100
4419e: 0100 0100 0100 00ff 00ff 00fe 00fd 00fc 00fb 00fa 00f8 00f7 00f5 00f3 00f1 00ef
441be: 00ed 00ea 00e7 00e5 00e2 00df 00dc 00d8 00d5 00d1 00ce 00ca 00c6 00c2 00be 00b9
441de: 00b5 00b1 00ac 00a7 00a2 009d 0098 0093 008e 0089 0084 007e 0079 0073 006d 0068
441fe: 0062 005c 0056 0050 004a 0044 003e 0038 0032 002c 0026 001f 0019 0013 000d 0006
4421e: 0000 fffa fff3 ffed ffe7 ffe1 ffda ffd4 ffce ffc8 ffc2 ffbc ffb6 ffb0 ffaa ffa4
4423e: ff9e ff98 ff93 ff8d ff87 ff82 ff7c ff77 ff72 ff6d ff68 ff63 ff5e ff59 ff54 ff4f
4425e: ff4b ff47 ff42 ff3e ff3a ff36 ff32 ff2f ff2b ff28 ff24 ff21 ff1e ff1b ff19 ff16
4427e: ff13 ff11 ff0f ff0d ff0b ff09 ff08 ff06 ff05 ff04 ff03 ff02 ff01 ff01 ff00 ff00
4429e: ff00 ff00 ff00 ff01 ff01 ff02 ff03 ff04 ff05 ff06 ff08 ff09 ff0b ff0d ff0f ff11
442be: ff13 ff16 ff19 ff1b ff1e ff21 ff24 ff28 ff2b ff2f ff32 ff36 ff3a ff3e ff42 ff47
442de: ff4b ff4f ff54 ff59 ff5e ff63 ff68 ff6d ff72 ff77 ff7c ff82 ff87 ff8d ff93 ff98
442fe: ff9e ffa4 ffaa ffb0 ffb6 ffbc ffc2 ffc8 ffce ffd4 ffda ffe1 ffe7 ffed fff3 fffa
4431e: 0000 0006 000d 0013 0019 001f 0026 002c 0032 0038 003e 0044 004a 0050 0056 005c
4433e: 0062 0068 006d 0073 0079 007e 0084 0089 008e 0093 0098 009d 00a2 00a7 00ac 00b1
4435e: 00b5 00b9 00be 00c2 00c6 00ca 00ce 00d1 00d5 00d8 00dc 00df 00e2 00e5 00e7 00ea
4437e: 00ed 00ef 00f1 00f3 00f5 00f7 00f8 00fa 00fb 00fc 00fd 00fe 00ff 00ff 0100 0100
```

- [F] `4439e`부터는 다른 코드다(B4b 이하 후보 `4439e..443b8`). sin index 255는 `4431c`, cos index 255는 `4439c`에서 끝난다.
- [F] **callee에게 넘기기만 하는 자료**(이 단위는 읽지 않음): `4ae4a`의 A0 = `229a8`(`22b96`) `22d64`(`22e52`) `22fe0`(`230fa`) `22ffe`(`231a2`) `2355c`(`23664`)와 목록 원소 `229c6` `229e4` `2357a` `23598`; `1ab80`의 A0 = `235c2`(`235c2..235ca` = `fff0 ffd0 0020 0040`); `49f8c`의 애니메이션 목록 A1 = `23e02` `23cfa` `23f22` `240ca` `23ffa` `2419a` `24240` `2457c` `6f536`; `443d2`의 D0 = `bc897` `a4f84` `180000`; `8ebe`의 소리 `204` `27c` `378` `20a` `203` `872` `8ba` `80c`; `3af8`의 D0 = `1a26` `1a24` `1a99` `1a64`(와 `22d82` 표 값).
- [I] index가 [I] 범위 밖이면 원본은 다음 코드·표 바이트를 자료로 읽는다. C++도 같은 주소를 live bus로 읽는다(단위 시험에서는 합성 바이트 밖이라 bus checked 오류).

## 경계·routing 밖 출구

- [F] routing 밖 실행 PC: 없음. routing 밖 값은 위 자료와 새 자식 값(`22f7a` `23774` `2334c` `d206a`)뿐이다.
- [F] routing된 출구·callee: 위 "요약"의 19개와 `JMP 2a00`. 반환은 `RTS` 14곳(`1c9c8` `1c9ea` `22a10` `22a60` `22a82`의 helper 끝, `22c80` `22cae` `22d62` `22f78` `2315c` `23346` `236c2` `236c8` `23772`; `4bbfe`의 helper 끝을 더해 15).
- [F] 공유 진입: `22b30`은 함수 `22a9e`(routing 밖, `22ad0 BRA.W`)가, `231bc`는 `2334c` 자식 코드(`23558 BRA.W`)가, `22c82`·`22a4c`·`1c9b8`은 B4b 후보 코드가, `4bb52`는 15곳이 쓴다. 이후 그 코드를 넣는 단위는 이 단위의 block 시작으로 끝나야 한다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, B3a~B3c spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, 목록 포인터 LONG `8c`/`80` := ROM 목록 또는 자연 node, A0 := 자연 node(자식 기록), A5 기준 플레이어 기록 `10d450`/`10d460`의 BYTE `1`, 격자 `10db88..`, PC).
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다(`28ae` → `23190`(`23180` 진입) `231de`(`231ce`) `23284`(`23270`) `232be`(`23296`), `287e` → `23336`(`23330`), `1ab80` → `236be`(`236b4`), `49fc6` → `22d2c`(`22d26`) `23768`(`23762`); `49fc6`는 단위 시험에서 선언 C, V1·실제 ROM 차분에서 실제 사슬).
- node fixture: 자식 진입 7개와 설치 값(`22b96` `22cb0` `22d06` `22e48` `230fa` `231bc` `23242` `23328` `23348` `23664` `236d0` `23726`)을 node callback으로 들어가 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다. `2986` 실패 경로는 결정 4의 기대 오류다.
- callee fixture: `1c9b8` `1c9ce` `22a10` `22a4c` `22a62` `4bb52`를 subroutine으로(복귀 LONG = sentinel) 들어간다.
- 단위 시험(Unicorn 생성기, B3c 꼴): 시작 218개 × 들어오는 C 3가지, zero-step, 내부 PC 1119개 정확한 오류, 경계 stop, rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC.

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `probe_scan.py`: 여덟 범위 안 값, `engine/tests` `tools/unit_fixture_specs` `tools/*.py`): N04 시험의 `4bb52` stop(행 `72d04-c2` `72d1a` `72d26`, 표 826~828행, `boundaries()` `want[]`; stop 판정이 routing보다 먼저라 그대로 통과), U08b 시험 `RANGES`의 끝 `4bb52`(배타)와 `rom_outside[]`의 `4bb52`(U08b 범위 밖인지만 검사), U11 시험의 자료 값 `2320f`(PC가 아님)뿐이다. "routing 밖" rollback 기대로 이 범위 PC를 쓰는 곳은 없다.
- [I] 계산 PC로 이 범위에 착지하는 숨은 탐침(예: N04 RTS 사슬이 `4bb52`를 지나 rollback을 기대하는 행)은 구현 뒤 `make test`로 찾는다. 찾으면 결정 6대로 옮기고 이 절에 더한다.
- [I] `4bb52`는 routing된 N04(`72d14` `72d20` `72d2c`)가 부른다. 자연 frame에서 N04가 그 경로를 지나면 지금까지 `4bb52`에서 `unsupported animation machine PC`로 끝나던 실행이 더 간다. frame 회귀(D1·controller·IRQ)로 확인한다(다음 작업자).

## 결정

1. **범위.** (a)+(b) = 299 block이라 한 단위로 하지 않는다. 표 `227fc` `2280c` `2281c`의 자식 7개와 공용 helper(218 block)를 B4(= B4a)로 구현하고, `23a3e`·(b)·새 자식은 B4b로 미룬다(끝 절; 작업자 권고).
2. **도달하지 않는 `22c8c RTS`.** 정적 참조가 없으므로 넣지 않고 routing 밖으로 둔다(B3c 결정 1과 같은 꼴). 범위는 `22ad4..22c8c`와 `22c8e..22d64`로 나뉜다.
3. **자료.** 표·bank 읽기는 live bus, 상한 검사 없음(F1 결정 3). 표 바이트(`22a02..22a10` `22d64..22d94` `22fe0..23058` `2355c..235ca` `4411e..4439e`)는 routing하지 않는다.
4. **`2986` 실패 경로.** buffer_cue 결정 1(caller-X 한계는 의도된 checked 오류)을 그대로 둔다. `22e88` `22f0c` `235ee`의 `JSR 2986`이 `28ae` 실패(WORD 한도·free list 끝)를 만나면 C++는 `298e`에서 `cue wrapper failure requires known caller X`로 멈춘다. [I] 원본은 더미 node `100e98`에 쓰고 이어 간다.
5. **carry 보존 목록.** 소비자 8개만 넣는다. `ORI.B #1,CCR` block 넷은 자기 block 안에서 known C Set을 남긴다.
6. **숨은 탐침 이전.** 기존 시험이 계산 PC로 이 범위에 착지하면 B3a 결정 5와 같이 RAM `10fexx` 탐침으로 옮기고, 옮길 수 없으면 기대 문자열만 이 단위 오류로 바꾸고 실패 PC를 stop으로 확인한다. 옮긴 곳은 이 절과 "구현·검증 기록"에 대응을 적는다.

## 미확인

- [U] BYTE `15` bit 4·7, BYTE `61` bit 3, BYTE `82` `83` `84` `8a` `8b`, WORD `7c` `7e` `80`, LONG `64` `84` `88`의 의미; `4be34`가 돌려주는 D4.W(각도 [I])와 `4ae4a`의 D0.B(충돌 종류 [I])의 정확한 의미.
- [U] 일곱 진입의 화면상 무기 이름, sin index와 `22d82` index의 실제 범위.
- [U] `5450(A5)`/`5460(A5)` 기록 BYTE `1`(탄 수 [I])과 `5b88(A5)` 격자(영향도 [I])의 사용처.
- [U] 자연 400 frame에서 이 단위 범위(특히 `4bb52`)의 도달.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_b4.cpp`(case label 218 = scratch `starts.txt`와 집합 일치), `engine/tests/animation_machine_objects_b4_test.cpp`(생성 구역 + 수작성 규칙: `4bb52` MOVEM.L 저장·복원 순서, `2360a` MOVEM.L 복사 순서, 자료·도달하지 않는 PC 20개의 dispatcher 오류), `tools/generate_animation_machine_objects_b4_test_table.py`(생성기; 두 번 실행해 시험 파일 바이트 단위 같음, SHA256 `7292f28625ed581d…`), `tools/unit_fixture_specs/b4.py`(V1 spec; 정적 검사만 함 — `load_routing` 뒤 시작 218개가 모두 `animation_objects_b4_block`, `static_next` 전부 정의됨, 내부 1119). 공유 수정은 "공통 규칙"의 다섯 곳뿐이다.
- [F] 단위 시험 world: A7 = `10ef00`, `4bb52` 안쪽 진입(`4bb66..4bbfe`)은 A7 = `10ef00 − 12`(MOVEM.L LONG 셋이 스택에 있음). 합성 typed physical byte: bank `20006c..200098`, sin/cos `4411e..4439e`, `22d82..22d94`, 목록 `22a02..22a0e`·`235b6..235ca`(뒤 8바이트는 `1ab80` 사각형).
- [F] `make -j3 all test`(작업자): 종료 0, 경고 0, Assert 줄 0, 시험 실행 269개, Python 310개 통과. B3a·B3b·B3c·N04 줄은 변경 전과 같다. B4 시험 줄: `751 fixtures (543 single-block, 136 path, 30 producer chain, 16 declared C, 26 checked error (6 with a later failing PC), 50 kept C), 218 blocks, 4209 calls, 38393 checks`. 내부 PC 1119개 정확한 오류, 실제 생산자 사슬: `28ae` 넷·`287e`·`1ab80` 각각 C Clear/Set 둘 다.
- [F] 무효가 된 기존 탐침: 없음(전체 시험 통과; N04의 `4bb52` stop 행·U08b `rom_outside[]`는 그대로 성립). 결정 6의 이전 대응 없음.
- [F] 작업자가 손으로 만든 확인용 변이 2개(`ASR.L` 부호 채움 제거, `22a10`의 sin/cos 표 맞바꿈)는 시험이 모두 잡았다. 전체 변이(65개)·UBSan·실제 ROM 차분·V1·frame 회귀는 검증 작업자 몫이다(scratch `HANDOFF.md`).
- [U] 미확인은 위 "미확인" 절 그대로다.

### 검증 기록(검증 작업자 Sonnet 5.5 / medium; seed `MS5_SEED_DIR=artifacts/stage_entry_body`)

- [F] `make -j3 all test`: 종료 0, 경고 0, Assert 0, Python 310개 통과, `ANIMATION_MACHINE_SOURCES` / `_HEADERS` 각 1줄. B4 줄은 위와 같고 호출·검사 수만 `4213 calls, 38397 checks`(아래 22e62 규칙 추가분). 생성기 재실행: 시험 파일 바이트 단위 동일.
- [F] UBSan(`-O1 -fsanitize=undefined -fno-sanitize-recover=undefined`): 종료 0, `runtime error` 0, B4 줄 동일(22e62 규칙 추가 전 빌드).
- [F] 변이 65개: 64개 사망. 생존 둘: `22e62-and7f`(시험 틈, 아래 수정으로 사망)과 `2374e-bhi`. `2374e-bhi`는 **동치**: `SUBI.W #140,7c(A6)`의 옛 값이 정확히 `140`일 때 BCC가 `2375c`로 가든(원본) `23758`(`CLR.W 7c(A6)`, 이미 0)을 거쳐 `2375c`로 가든 레지스터·RAM·C가 같다. 수정 후 재실행: `killed 64 of 65`, 남은 하나는 위 동치.
- [F] 실제 ROM 차분(Unicorn 대 C++, 8 `program_rom_*.ms5d`, 1,500 case × 5 seed = 7,500): 불일치 0, 시작 218/218 도달. 첫 실행에서 harness 수정 없음. 실제 생산자 뒤 소비자 분기 비교(5 배치 합): `22d2c` 112, `23190` 324, `231de` 243, `23284` 378, `232be` 653, `23336` 316, `236be` 322, `23768` 140. 문서화된 차이 "2986 실패 경로는 호출자 X 필요": 10 + 16 + 9 + 17 + 18 = 70(`235ca` 33, `235ee` 9, `22f0c` 4, 그 밖 `22e5c..22ee8`·`235e2`·`22eca`·`22e62`·`22e82`·`22e88`·`22ed8`·`22ee2`·`22ee8`). 다른 부류(홀수 주소 레지스터, Unknown C 진입, interpreter 계산 분기) 0.
- [F] V1 native 고정: `b4: carry oracle ok, final tags Unknown/Clear/Set = 669/8/8`, 1,830 fixture 전부 ok(error 1135 / match 685 / mismatch 10 = 부정 시험 기대), `visited 218/218`, 누락 후속·도달 불가 결과 없음. 두 번 실행 `[(name,digest)]` 동일. 계열: error 1135, block 608, node 43, chain 16, callee 15, negative 10, failpc 3. node 행에서 `2986` 안의 `28ae` 실패가 `298e`로 돌아오는 실행은 0(예상한 `-to-298e` 쌍 없음).
- [F] V1 회귀: b3a 1468/1468, b3b 1360/1360, b3c 625/625 모두 ok. N04·U08b용 spec은 없다.
- [F] frame: D1 / controller `--declare game` / IRQ 각 54,400/54,400 완료, 자연 불일치 0, 결정성·negative ok; controller `--declare demo` 45,684/45,684(자연 불일치 0, 137 seed). B3c 기록과 같고 `4bb52`로 인한 frame 변화 없음(자연 frame이 `4bb52` 너머로 더 가지 않았다).
- [F] 검증 중 수정(B4 파일만):
  1. `tools/unit_fixture_specs/b4.py` `first_unrouted`: Unicorn이 code hook에 주는 `size`가 M68000 명령 길이가 아니라(`287e MOVEA.L 8(A6),A0` 다음 `2882`를 점프로 오판) `23330 -> 287e` 사슬이 `no chain world`로 실패했다. 직전 명령 길이를 capstone으로 디코드하도록 고쳤다(`b3c.py`는 수정하지 않음).
  2. `engine/tests/animation_machine_objects_b4_test.cpp` `rules()`: `22e62`의 `ANDI.W #ff,D0`가 8비트 전부를 쓰는지(D0.B 7f / 80 / ff, 상위 WORD 보존) 별도 합성 ROM(`22d82` 256 WORD)으로 확인하는 규칙 추가. 생성 구역은 그대로. 변이 `22e62-and7f`를 죽인다.

## 후속 단위 명세(B4b)

[F] B4 routing을 뺀 정적 closure(scratch `sizes2.py`; 같은 규칙):

| 후보 | 진입 | 새 block | 명령 | 범위 |
| --- | --- | --- | --- | --- |
| B4b-1: 표 `2282c` 자식 | `23a3e` | 48 | — | `23a3e..23c56` `49636..496a6` |
| B4b-2: U06 옆 처리기 | `e74f8`, 표 항목 `e7504` `e7508`, `28ae` 자식 `2b7be`(형제 stage event callback `2b7b8` 포함) `e7996` | 36 | — | `2b6e6..2b7c6` `e74f8..e7546` `e7996..e7a44` |
| B4b-1 + B4b-2 | | **84** | 250 | 위 다섯 |
| B4b-3: 새 자식 | `2986` 자식 `22f7a` `23774`, `28ae` 자식 `2334c` `d206a` `281ea`(`23a3e`가 만듦) | **114** | 338 | `22f7a..22fe0` `2334c..233bc` `233be..2347e` `23480..2353c` `23774..237ca` `281ea..2822a` `2825c..28490` `4439e..443b8` `d206a..d20b0` |
| 합 | | **198** | 588 | |

- [F] 합 198 ≤ 약 220이므로 **B4b 한 단위(198 block)**를 권고한다. 나누면 B4b-1 + B4b-2(84)를 먼저 하고 B4b-3(114)을 뒤에 한다(B4b-3의 `2334c` 등은 B4 출구라 B4 시험의 stop만 바뀐다).
- [F] B4b의 출구(모두 routing됨): `288c` `28ae` `2a00` `3af8` `8ebe` `8ff4` `2b8b6` `43e34` `43ea4` `43eb8` `443d2` `44602` `496c2` `4970a` `49f8c` `49fc6` `4ae4a` `4be06` `4be34` `4bfa4` `4c0ac` `c6a96` `d239c`. 더 나오는 `28ae` 자식 `41fe6`(`2b736` `2b778`)·`d1d08`(`e7996` 쪽)은 이미 routing돼 있다.
- [F] 간접 분기 1곳: `e74fc JSR e7504(PC,D0.W)`(D0.W := WORD `(A0)+`, script 명령 인자). 표는 `e7504 BRA.W e750c`·`e7508 BRA.W e7534` 두 항목으로 정적으로 닫힌다(U06 계약 결정 3의 `e74ac`처럼 live 대상은 routing에 맡긴다: `e7504 + sext(D0.W)`가 `e7504`/`e7508`이면 그 block, `e7506`/`e750a`는 B4b 내부 PC 오류, 홀수면 `unaligned animation machine PC`, 그 밖은 그 PC의 routing). F1 결정 3대로 표 밖 착지는 checked 오류다.
- [F] B4b-2의 `2b6e6..2b7b8`은 N28 계약 "범위 이웃"의 형제 설정 함수, `2b7b8`(`BSET.B #0,15(A6)` 뒤 `2b7be`로 fall-through)·`2b7be`는 stage event 표 `e8cc0..e8cdc`의 값이다(N28·N29 계약). `2b746` `2b788 BCC.W`는 `28ae` C 소비자, `2b770` `2b7b2 ORI.B #1,CCR`은 같은 block 안의 known C 생산(→ `2b7b6 RTS`; `2b7be BSR.W 2b6e6` 뒤 `2b7c2 BRA.W 2b8b6`이 C를 읽는지 B4b에서 확인).
- [F] B4b-3의 `281ea..28490`은 `23a3e`의 `28ae` 자식(B4b-1이 만듦)이다. `4439e..443b8`은 sin/cos 표 바로 뒤의 코드다.
- [U] B4b 각 범위의 경계 이웃·자료 표·carry 소비자는 B4b 계약에서 이 문서와 같은 방법으로 전수 확인한다.

## block 목록

[F] scratch `starts.txt`(SHA256 `cf02258d78b56e305866e777be61a2d0549d6cd74b48906aa178d5b828d40472`)와 같다.

- **`1c9b8..1c9ec`(8)**: `1c9b8 1c9c4 1c9c8 1c9ce 1c9da 1c9de 1c9e6 1c9ea`
- **`22a10..22a8a`(8)**: `22a10 22a4c 22a54 22a5a 22a60 22a62 22a7c 22a82`
- **`22ad4..22c8c`(25)**: `22ad4 22af0 22b00 22b04 22b20 22b30 22b40 22b56 22b58 22b86 22b90 22b96 22ba0 22ba6 22bb8 22bc6 22bcc 22bde 22c42 22c46 22c64 22c70 22c80 22c82 22c86`
- **`22c8e..22d64`(20)**: `22c8e 22c94 22c98 22cae 22cb0 22cc8 22cce 22cdc 22cf8 22d06 22d14 22d20 22d26 22d2c 22d30 22d36 22d46 22d4c 22d5c 22d62`
- **`22d94..22f7a`(35)**: `22d94 22db8 22dbc 22de0 22de4 22df2 22e02 22e28 22e32 22e48 22e52 22e5c 22e62 22e76 22e82 22e88 22e9e 22eae 22eb8 22eca 22ed8 22ee2 22ee8 22efa 22f0c 22f22 22f32 22f3a 22f44 22f4c 22f52 22f56 22f5c 22f68 22f78`
- **`23058..2334c`(69)**: `23058 23074 23084 2308e 230aa 230ba 230c0 230d0 230e8 230fa 23104 2310c 23114 2311a 2311e 23124 2312e 23134 23140 23146 23156 2315c 2315e 23168 23172 23176 23180 23190 23194 2319e 231a2 231b8 231bc 231ce 231de 231e2 231ec 231f0 2320e 23224 23228 2323c 23242 23248 23256 23260 2326a 23270 23284 23288 23292 23296 232be 232c2 232cc 232d0 232f6 232fc 23308 2330e 2331e 23324 23328 23330 23336 2333a 23342 23346 23348`
- **`235ca..23774`(36)**: `235ca 235e2 235ee 23604 2360a 23630 23640 23650 23664 2366e 23674 2367a 23684 2368c 236a6 236a8 236b4 236be 236c2 236c4 236c8 236d0 236da 236ec 236fa 23710 23726 23730 2373c 2374e 23758 2375c 23762 23768 2376c 23772`
- **`4bb52..4bc04`(17)**: `4bb52 4bb66 4bb7c 4bb96 4bba4 4bbaa 4bbb2 4bbb8 4bbc0 4bbc6 4bbce 4bbd4 4bbdc 4bbea 4bbf0 4bbf8 4bbfe`
