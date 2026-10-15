# 고아 설치 사슬 `39366`·`28ae` 자식 `2d3ae`/`2d57a` 구현 계약 B2d

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안, 메인 확인 전.** 이 문서를 먼저 쓰고 그대로 구현한다. 아래 수치와 목록은 작업자가 정적 디코드로 독립 계산했다. 결정 항목(끝)은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB, mtime `1791291625`. 이 문서의 코드 주소는 모두 고정 영역(`<100000`)이라 CPU 주소와 파일 오프셋이 같다. banked 읽기(`2000xx`)는 live bus(bank base `200000`일 때 물리 오프셋 = CPU 주소)다. ROM·추출 데이터는 수정하지 않았다.
- [F] 저장소 기준 `e5bfb73`(= `origin/main`, B1a~B2b·C1~C3·F6 통합). routing 기준 `engine/src/animation_machine.cpp`(dispatch 규칙 109개). 이 파일의 dispatch 사슬을 Python 조건식으로 옮겨 "routing된 PC"를 판정했다(scratch `hroute.py`, N33 작업 도구와 같은 방식).
- [F] 정적 디코드: capstone 5.0.6 M68000. block 시작 규칙은 B1 계약 "기준 입력"과 같다(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `JMP d(PC,Dn)` 뒤 연속 `BRA.W` 표 entry와 그 대상, `MOVE.L #imm,(A6)` 설치, `MOVEA.L #imm,A0` + `JSR 28ae` 자식; routing된 PC에서 멈춤).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/b2d/`
  - `sdec.py`(디코더, N33 `n33.py` 파생), `unit_b2d.py`(단위 정의·분류), `refs_b2d.py`(LONG·PC 상대 참조 탐색), `disasm_b2d.py`, `hroute.py`.
  - `starts.txt`(block 시작 220개) SHA256 `6310bcda2cbd8b8381a5142cc55c03380370d1633ae715d85913862186354e4b`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인. "자연 400 frame"은 D1 구동기 기록(137 seed × 400 frame)을 말한다.

## 요약

- [F] **범위와 block 수**(정적, routing·다른 항목에서 멈춤):

| 항목 | block | routing 범위 | 바이트 | SHA256 | 진입을 만드는 곳(참조) |
| --- | --- | --- | --- | --- | --- |
| `39366` 상태 사슬 | 115 | `391e8..395dc` | 1012 | `7504a6f0b9b177d3bc8e0187e173d8c8e243502c590679f25969e76fe42c7884` | 설치: B2b `38dc2`, N32a `391de`(둘 다 routing됨), 범위 안 `3935c` `395d2`; 분기 `39272` |
| `3b044` 자식 | 18 | `3b044..3b118` | 212 | `f746a5a5855877f5d8f31d103b454615b2fb600832d794cab7225f5bcee5ebf7` | 범위 안 `39506`(`MOVEA.L #3b044,A0` + `JSR 28ae`) |
| `2d3ae`·`2d57a` 자식(+`2d6e6`) | 87 | `2d3ae..2d7be` | 1040 | `fd66195b1b671af8fca9bed24e4cd1f661d35ba685aedae08e59f136adfe88f8` | B2b `3a574`(`2d3ae`)·`3a560`(`2d57a`) `28ae` 자식(routing됨); routing 밖 `2b5b6`·`2b5a2`(아래 N28 범위 밖 사슬); `2d6e6`은 범위 안 `2d69c` |
| 합계 | **220** | 세 범위, 짝수 PC 1,132(내부 912) | 2,264 | 이어 붙인 바이트 `f38b8480b45ee626e03f032a8b56affc0099dfcfb87342118f3ecbe63960305a` | |

- [F] B2 계약 "새로 확인한 범위 밖 사슬"의 수(`39366` 133, `2d57a` 62, `2d3ae` 41)를 재현했다. `2d3ae`와 `2d57a`는 꼬리 16 block(`2d4c4..2d578`)을 공유하므로 합집합은 87이다(41 + 62 − 16). 총 220은 ~230 이하라 **나누지 않는다**(결정 1).
- [F] **현재 routing과의 관계**: 세 범위의 모든 짝수 PC는 현재 routing 밖이다(겹침 0). 경계 이웃: `391e6`(N32a)·`395dc`(N32a), `3b042`(routing 밖 자료 `3b03c..3b044`)·`3b118`(N33), `2d3ac`(routing 밖 자료 `..2d3ae`)·`2d7be`(routing 밖, 다른 자식 함수 `2d7be`).
- [F] **나가는 곳은 모두 routing됨**: callee `288c` `28ae` `3a4da` `3a5be` `3a5d2` `3af8` `3b288` `3b302` `3b334` `3b424` `43e08` `43e34` `43ea4` `443d2` `49214` `49a58` `49f8c` `49fc6` `4ae4a` `4be34` `8ebe`, 출구 `2a00` `3a350`(N31) `38dd4` `38ff4` `398be`(N32a) `39eb2`(N32b). 그래서 이 단위를 넣으면 세 사슬은 C++에서 끝까지 실행된다. 예외는 `3a5be`의 `JSR (A0)`(A0 = LONG `82(A6)`)가 routing 밖 `3a60a` 사슬(B2c 범위)로 가는 경우뿐이다.
- [F] **도달성**: 모든 진입이 정적 코드 참조를 가진다(`39366`은 routing된 B2b·N32a 설치, `2d3ae`/`2d57a`는 routing된 B2b `3a4da`의 `28ae` 자식). 즉 실행 가능한 기능이다. 자연 400 frame에서는 어느 seed도 실행하지 않는다([F] D1 구동기 기록: 자연 frame이 모두 일치하고 이 PC들은 routing 밖이었으므로 실행됐다면 C++ 오류로 불일치가 났다).
- [I] 의미: seed 116/117 객체 계열(N31~N33, "partner")의 지상 이동 상태기계(`39366`)와 그 먼지 효과 자식(`3b044`), `3a4da`가 만드는 발사체 자식 두 종류(`2d3ae` 감속 낙하형, `2d57a` 직선형 + 꼬리 입자 자식 `2d6e6`)다.

## 공통 규칙·native 검증 계획

B1 계약 "공통 규칙"(실행부·이름, routing, 경계, known C, 표, banked 읽기, `2986`, interpreter)과 "공통 native 검증 계획"(V1, `U.natural_cases()` = D1 `declared_rebase()` + `R.prepared(case)`, `U.seed_node_fixture` + `U.with_host_writes`, block 직접 진입·오류·표·음성·회귀), B2 계약 "자식(`28ae`) 진입 fixture"·"helper 진입 fixture"·"간접 `JSR (A0)`"을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_b2d.cpp`, 함수 `animation_objects_b2d_block`. 오류 문자열은 `unsupported animation objects b2d PC`(범위 안 내부 PC 직접 진입)와 `objects b2d caller requires known carry`(C 소비 block에 Unknown C)다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(세 범위), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나, `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES`, test 목록, 시험 target·실행 줄; Codex의 object 재사용 구조 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** 이 단위 밖으로 나가는 PC는 모두 다른 실행부가 있다. 단위 시험은 F4 관례대로 callee 진입 PC에서 stop만 확인한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다. 다른 단위(B2c 등)의 PC를 "미연결 탐침"으로 쓰지 않는다.
- **자료 읽기.** 고정 ROM 표 `3b03c..3b044`(WORD 4개, `3b0ac LEA 3b03c(PC),A1; ADDA.W D0,A1`), banked LONG `200094`(`3b04a` `2d6ec`), `2000b8`(`2d3b4` `2d580`), `20008c`(`2d52a`)는 live bus로 읽는다. 단위 시험은 이 주소에만 합성 typed physical byte를 둔다(ROM 자료가 아니다).
- **macOS seed.** 이 컴퓨터에는 `artifacts/linux_rebase/stage_entry_body`가 없고 역사 관측 `artifacts/stage_entry_body/observation.json`(SHA256 `1f65100f…` = D1 검증기의 `HISTORIC_SEED_SHA`)이 있다. 자연 seed가 필요한 V1·D1 실행은 scratch wrapper가 `D.SEED_DIR`만 이 역사 경로로 바꾼다(도구 파일은 고치지 않음). 선언 rebase의 출처는 보고서에 남는다.
- **V1 spec** `tools/unit_fixture_specs/b2d.py`: B2b spec과 같은 가족(block, coverage, chain, node, error, negative). 기반 world는 seed 116/117 frame 2의 자연 N pass node(N31 `38c36` 등)이고, 선언 편집으로 레지스터·node field·PC를 둔다.
  - block: 모든 block 시작(소비자 제외) 직접 진입, stop = 단위 밖 첫 PC.
  - coverage: 모든 조건분기의 양쪽과 두 표의 9 slot.
  - chain: 소비자 9개를 실제 생산자로 들어간다(`3a4da` → `3923c` `39330` `394a8`; `3b334` → `39358` `395ce`; `288c` → `3b0ec`; `49fc6` → `3b10c` `2d56e` `2d7b2`). native는 실제 flag로, C++는 known C로 분기한다.
  - node: 설치 값 13개와 자식 진입 4개를 node callback으로 들어가 dispatcher 복귀(또는 첫 경계)까지 실행한다. `3a5be`가 나오는 경로는 LONG `82(A6)` := `3a5d2`(N33, routing됨)로 선언하거나 `3a5be`에서 stop한다.
  - error: 내부 짝수 PC 전수, 홀수 PC, Unknown C 소비자 9개, `3a5be` → `3a60a`(routing 밖) stop 없음, RAM 탐침, 홀수 쓰기.
  - negative: RAM 1 bit, 레지스터, stop PC, queue.
- **단위 시험** `engine/tests/animation_machine_objects_b2d_test.cpp`: B1a 시험과 같은 꼴이다. `run_animation_machine`만 쓴다. FIXTURES 표는 scratch 생성기(Unicorn M68000, 원본 BE ROM 위에 같은 합성 byte를 겹침, 스택 work RAM, bank `200000`)의 native stop 상태(16 레지스터, RAM·레지스터·PC·bank·reads·status FNV-1a digest)다. 모든 시작 × 들어오는 C 3가지, zero-step(stop = 진입), 내부 PC 전수 정확한 오류, 경계 stop, RAM 탐침 rollback, Unknown C 소비자, 실패 시 보존을 확인한다.

## carry

- [F] **소비 block 9개**(callee가 돌려준 C를 읽음; 모두 FLOW):
  - `3923c` `39330` `394a8`: `MOVEM.L (A7)+,D0; BCS.W 39296` — `3a4da`(B2b)가 돌려준 C(`3a5b2` Set / `3a5b8` Clear). MOVEM은 flag를 바꾸지 않는다.
  - `39358` `395ce`: `BCC.W` — `3b334`(N33)가 돌려준 C(`3b392 LSR.B #1` 계산 C).
  - `3b0ec`: `BCS.W 3b0f6` — `288c`(readiness)의 C(부모 없음 Set, 부모 callback `270e`이면 Clear, 그 밖 Set).
  - `3b10c` `2d56e` `2d7b2`: `BCC.W` — `49fc6`(interpreter)의 C.
- [F] **known C 생산 0.** 이 단위에는 `ORI/ANDI CCR`이 없다. 다른 RTS의 C(`2d50e` CMPI 뒤, `2d5fe` `2d77c` MOVE 뒤 등)는 소비자가 없어 Unknown이다(B2b·N32a 관례).
- [F] **FLOW block 132개**(소비자 9 포함): 명령이 모두 C 불변(`JSR` `BSR` `JMP` `BRA` `RTS` `LEA` `MOVEA` `BTST` `BSET` `BCLR` `Scc` `MOVEM` `Bcc`)인 block이다. `carry_preserving_pc`에 넣어 들어온 C를 그대로 둔다(N32a·B1a 관례). 나머지 88 block은 진입 때 Unknown이 되고, block 안의 비교·분기는 같은 block에서 끝난다(N/Z/C 재계산 없음).
- FLOW 목록: `2d462 2d46c 2d476 2d490 2d494 2d498 2d49c 2d4a0 2d4a4 2d4a8 2d4ac 2d4b0 2d4b4 2d4be 2d4ca 2d50e 2d51a 2d562 2d568 2d56e 2d572 2d578 2d616 2d620 2d62a 2d644 2d648 2d64c 2d650 2d654 2d658 2d65c 2d660 2d664 2d668 2d672 2d67e 2d6e4 2d75e 2d76a 2d770 2d7ac 2d7b2 2d7b6 2d7bc 391e8 391f2 391f6 391fe 3920e 39218 39220 3923c 39244 3924c 39254 39276 3927a 3927e 39282 39292 392a6 392b0 392ba 392d8 392ea 392f2 39302 3930c 39314 39330 39338 39340 39350 39354 39358 39362 39366 39380 393c6 393d0 393d4 393de 39430 3943a 3943e 39454 3945e 39462 3946a 3947a 39484 3948c 394a8 394b0 394b8 394c2 394c6 394ce 394d8 394e2 394ea 394ee 3951a 39534 3953e 39542 3955a 39564 39568 39570 39580 3958a 39592 3959a 395a4 395a8 395b0 395ba 395be 395c6 395ca 395ce 395d8 3b08a 3b0e6 3b0ec 3b0f0 3b106 3b10c 3b110 3b116`.
- [F] X·DIVx·TRAP·I/O port 쓰기·bank 변경이 없다. `MULU.W #36,D0`(`2d444`) 하나, `ASR.L`/`ASR.W`/`LSL.B`/`NEG`/`EOR.B`/`SWAP`/`ADDA.W`가 있다. 부호 있는 shift는 부호 bit를 명시적으로 채워 구현한다(미정의 동작 없음).

## `39366` 상태 사슬(115 block, `391e8..395dc`)

- **진입**([F]): `39366`(설치 B2b `38dc2`, N32a `391de`, 범위 안 `3935c` `395d2`, 분기 `39272 BEQ`). 범위 안 설치 `39292` `392b0` `39380` `39454` `3951e` `3955a`.
- **의미**([F] 바이트, [I] 해석):
  - `39366`: 애니메이션 `3b8dc`(`3b302`), BYTE `95` := 2, LONG `64` := 0, 설치 `39380` → `BRA 391e8`.
  - 공통 입력 머리(`391e8`/`392b0`/`39454`/`3955a` 계열): BYTE `15` bit 7 = 0 → `398be`(N32a). `JSR 3b424`(B2b; partner 입력 bit → D0). D0 bit 7 → `39eb2`(N32b). bit 1 = 0이고 BYTE `9f` ≠ 0이고 `15` bit 7 → `38ff4`(N32a). bit 5 → `38dd4`(N32a).
  - BYTE `9d` bit 6 → `9d`/`9e` bit 6 지움, `MOVE.L D0,-(A7)`, `JSR 3a4da`(B2b, 자식 발사체 생성 시도), `MOVEM.L (A7)+,D0`, C Set → `39296`.
  - `391e8` 몸통: bit 2 → `3939c`, bit 3 → `39384`, 아니면 BYTE `94` bit 3 set, `JSR 3a5be`(A0 = LONG `82`), BYTE `97` = 0 → 애니메이션 `3b8e8` + 설치 `39292`(→`391e8`), = 4 → `39366`, 그 밖 → `3b288` `3b334` `BRA 3a350`.
  - `39296`: BYTE `98` := `ff`, 애니메이션 `3b97e`, `3a5d2`(N33), 설치 `392b0`. `392b0` 몸통: BYTE `98` ≠ 0 → D7 = 0 ± `2a000`(D0 bit 3 더함, bit 2 뺌) → LONG `64` → `39350`. 아니면 공통 입력, bit 3 → `393e8`, bit 2 → `39406`, 아니면 LONG `64` := 0. `39350`: `3b288`, `3b334` C Set → 설치 `39366`; `BRA 3a350`.
  - `39384`/`3939c`: BYTE `b0` := 5, LONG `64` := `2a000`/`fffd6000`, BYTE `94` bit 5 clear/set. `393b0`: (BYTE `94` bit 5 ≠ 0) XOR (BYTE `15` bit 0 ≠ 0)(`SNE.B D0/D1; EOR.B`)로 애니메이션 `3b8ee`/`3b8f4` → `39448`.
  - `393e2`/`39400`: BYTE `b0` := 3, 이어 `393e8`/`39406`: BYTE `95` := 2, LONG `64` := `2a000`/`fffd6000`, bit 5 clear/set, `3941a`: 같은 XOR로 `3b8fa`/`3b900` → `39448`.
  - `39448`: WORD `2c` := `100`, 설치 `39454`. `39454` 몸통: 공통 입력, bit 3 → (`94` bit 5 ≠ 0 → `393e2`, 아니면 `394e2`), bit 2 → (`94` bit 5 = 0 → `39400`, 아니면 `394e2`), 아니면 설치 `3951e`. `394e2`: `3a5be`(A0 = LONG `82`), `3b288`, `3b334`. `394f2`: D0 = BYTE `b0`(MOVEQ #0 뒤), 0이면 `3951a`; 아니면 `LSL.B #4,D0; SUB.B D0,af(A6)`, borrow 없으면 `3951a`, 있으면 BYTE `b0` −= 1, `28ae` 자식 `3b044`(D0.W = `1e`). `3951a`: `BRA 3a350`.
  - `3951e`: 같은 XOR로 애니메이션 `3b906`/`3b90c`, LONG `64` := 0, 설치 `3955a`. `3955a` 몸통: 공통 입력(BYTE `9d` 검사 없음), bit 3 → (`94` bit 5 = 0 → `393e8`, 아니면 `39384`), bit 2 → (`94` bit 5 ≠ 0 → `39406`, 아니면 `3939c`), 아니면 `3a5be` `3b288` `3b334` C Set → 설치 `39366`; `BRA 3a350`.
- **known C**: 소비 `3923c` `39330` `394a8`(`3a4da`), `39358` `395ce`(`3b334`). 생산 없음.
- **스택**: `MOVE.L D0,-(A7)`(`3922a` `3931e` `39496`)과 `MOVEM.L (A7)+,D0`(`3923c` `39330` `394a8`)이 `JSR 3a4da`를 감싼 짝이다.
- **경계**: 없음(모든 callee·출구가 routing됨). `3a5be`의 live target은 아래 결정 2.

## `3b044` 자식(18 block, `3b044..3b118`)

- **진입**([F]): `39506`의 `28ae` 자식(D0.W = `1e`). 범위 안 설치 `3b0e6`.
- **의미**([F]/[I]):
  - `3b044`: WORD `20` := `e2`, LONG `22` := banked LONG `200094`, A1 = `3d050`, D0.W = `100`, `49f8c`. `3b062`: 소리 `8ebe`(D0.W `204`, D1.B 0).
  - `3b070`: A0 = LONG `c(A6)`(부모). D0 = BYTE `af(A0)` + `100` → WORD `2c`. LONG `36(A0)` < 0 → BSET `15` bit 0(`3b08a`).
  - `3b090`: 부모 (BYTE `94` bit 5) XOR (BYTE `15` bit 0)이 참이면 D0.W = 4(`3b0a8`), 아니면 0(MOVEQ 뒤 `SNE`/`EOR` 결과).
  - `3b0ac`: A1 = `3b03c` + sext(D0.W)의 WORD 둘 → D0.W, D1.W([F] 표 `3b03c` = `fff0 0000`, `3b040` = `0010 0000`). 부모 `15` bit 0이면 `NEG.W D0`(`3b0c0`).
  - `3b0c2`: D0.W += WORD `42(A0)`, D1.W += WORD `46(A0)`, A1 = `538e(A5)`, D0.W −= WORD `14(A1)`, D1.W −= WORD `18(A1)`, A0 = `2e(A6)`, `43e08`. `3b0e0`: 설치 `3b0e6`.
  - `3b0e6`: `288c` C Clear(부모 callback `270e`) → `3b0f0 JMP 2a00`(삭제), Set → `3b0f6`: WORD `1e` := WORD `1e(A0)`(A0 = `288c`가 남긴 부모) + 1, `43e34`, `49fc6` C Set → `3b110 JMP 2a00`, Clear → `3b116 RTS`.
- **표**: `3b0ac`의 표는 앞 block이 D0.W ∈ {0, 4}로 묶는다([F] 2 entry, 8바이트 전부 위에 옮김). 직접 진입에서 다른 D0.W는 원본처럼 `3b03c` + sext(D0.W)를 live bus로 읽는다(F1 결정 3 관례: 상한 검사 없이 원본 산술).
- **known C**: 소비 `3b0ec`(`288c`), `3b10c`(`49fc6`).

## `2d3ae`·`2d57a` 자식(87 block, `2d3ae..2d7be`)

- **진입**([F]): `2d3ae`(B2b `3a574`, BYTE `ae` ≠ 5; routing 밖 `2b5b6`), `2d57a`(B2b `3a560`, BYTE `ae` = 5; routing 밖 `2b5a2`), 둘 다 `28ae` 자식(D0.W = `a`). 범위 안 설치 `2d420` `2d510` `2d562` `2d600` `2d77e`, 자식 `2d6e6`(`2d69c`, D0.W = `1e`).
- **공통 머리**(`2d3ae`/`2d57a` 같은 바이트, 다른 주소): WORD `20` := `12a`, LONG `22` := banked LONG `2000b8`, 소리 `3af8`(`1a55`), BSET `15` bit 4, WORD `68`/`1e` := `e000`, A1 = `2e26c`, D0.W = 0, `49f8c`, `8ebe`(`258`, 0), D0 = `160000`, D1.B = BYTE `76`, `443d2`(각도 → 속도 D0/D1, [I]).
- **`2d3ae`**:
  - `2d406`: A0 = LONG `c(A6)`, D0 += LONG `36(A0)`, D1 += LONG `3a(A0)`, LONG `36`/`3a` := D0/D1, 설치 `2d420`(fall).
  - `2d420`: LONG `36` += (0 − LONG `36`) ASR 3. D1 = (`ffe40000` − LONG `3a`) ASR 3. D0 = LONG `36`, 음수면 `NEG.L`(`2d440`). `2d442`: D0 = D0 ASR 8, `MULU.W #36,D0`, D1 += D0, LONG `3a` += D1. D0.B := BYTE `76`(D0.W 상위 byte는 앞 값 그대로), `ASR.W #3,D0`, `ANDI.B #1f`, BYTE `81` := D0.B. `4be34`.
  - `2d462`/`2d46c`: BYTE `15` bit 7 또는 BYTE `61` bit 0 → `2d4c4`. `2d476`: A0 = `2d354`, `4ae4a`. `2d480`: `CMPI.W #9,D0; BCC 2d4b4`. `2d488`: `ADD.W D0,D0` 두 번, `JMP 2d490(PC,D0.W)` — 9 slot 표(`2d494` `2d498` → `2d4c4`, 나머지 7개 → `2d4b4`).
  - `2d4b4`: BYTE `61` bit 1 → BSET `15` bit 1(`2d4be`) → `2d4c4` 설치 `2d510`. `2d4ca`: `49fc6`(C 버림). `2d4d0`: LONG `3a` < 0이면 WORD `76` −= (WORD `76` − `c000`) ASR.W 2(`2d4d8`).
  - `2d4e6`: WORD `2c` −= (WORD `2c` − `100`) ASR.W 3. 화면 판정: WORD `42` + `10` ≥ `160`(무부호) → `2d572 JMP 2a00`. `2d504`: WORD `46` − `100`의 bit 15(BMI) → `2a00`, 아니면 `2d50e RTS`.
  - `2d510`(설치): 소리 `1a63`, A0 = `2d372`, `4ae4a`, WORD `20` := `d2`, LONG `22` := banked LONG `20008c`, `8ebe`(`378`, 0), WORD `68`/`1e` := `1001`, A1 = `2ecaa`, D0.W = `100`, `49f8c`, 설치 `2d562`. `2d562`: `43e34`, `49fc6` C Set → `2a00`, Clear → `2d578 RTS`.
- **`2d57a`**:
  - `2d5d2`: A0 = LONG `c(A6)`(이후 쓰지 않음), LONG `36`/`3a` := D0/D1, LONG `78`/`7c` := D0/D1 ASR 4, BYTE `81` := ((D0.W 상위 | BYTE `76`) ASR.W 3) & `1f`, 설치 `2d600`, RTS.
  - `2d600`: LONG `36` += LONG `78`, LONG `3a` += LONG `7c`, `4be34`. `15` bit 7 / `61` bit 0 → `2d4c4`(공유 꼬리). A0 = `2d390`, `4ae4a`, `CMPI.W #9` → `2d668`, 표 `2d644`(`2d648` `2d64c` → `2d678`, 나머지 → `2d668`). `2d668`: `61` bit 1 → BSET `15` bit 1(`2d672`) → `2d678` 설치 `2d510`. `2d67e`: `49fc6`(C 버림).
  - `2d684`: WORD `2c` −= (WORD `2c` − `100`) ASR.W 3, BYTE `80` −= `c0`; borrow 없으면 `2d6ca`. 있으면 `28ae` 자식 `2d6e6`(D0.W = `1e`), `MOVE.L A0,-(A7)`, D0 = `fff80000`, D1.B = BYTE `76`, `443d2`, `SWAP D0`, `SWAP D1`, `MOVEA.L (A7)+,A0`, `49214`. `2d6ca`/`2d6da`: 같은 화면 판정 → `2a00` 또는 `2d6e4 RTS`.
  - `2d6e6`(자식): WORD `20` := `e2`, LONG `22` := banked LONG `200094`, `8ebe`(`204`, 0), WORD `68`/`1e` := `1001`, A1 = `2e206`, `49f8c`. `2d71e`: A0 = LONG `c(A6)`, LONG `36`/`3a` := 부모 `36`/`3a`, D0 = `18000`, D1.B = 부모 BYTE `76` + `80`, `443d2`. `2d746`: A0 = LONG `c(A6)`, LONG `78`/`7c` := D0/D1, `49a58`(난수). `2d758`: D0.W < 0 → BSET `15` bit 0, D0.B < 0 → BSET `15` bit 1. `2d770`: `43e34`. `2d776`: 설치 `2d77e`, RTS.
  - `2d77e`: A0 = LONG `4(A6)`([U] 이 field의 의미), LONG `36` += ((LONG `42(A0)` − LONG `42`) ASR 7) + LONG `78`, LONG `3a` += ((LONG `46(A0)` − LONG `46`) ASR 7) + LONG `7c`, `43ea4`, `49fc6` C Set → `2a00`, Clear → `2d7bc RTS`.
- **표**: `2d488`(base `2d490`)·`2d63c`(base `2d644`)는 앞 block의 `CMPI.W #9; BCC`로 index 0..8이 된다([F] 9 slot 전부 위에 옮김). 표 진입 block 직접 진입은 원본 산술 그대로 PC = base + sext((D0.W·4) & `ffff`)다(F1 결정 3·B2b `3a0e8` 관례). 명령 중간에 떨어지면 다음 block 조회에서 checked 오류가 된다.
- **known C**: 소비 `2d56e` `2d7b2`(`49fc6`). `2d4ca` `2d67e` 뒤의 `49fc6` C는 버린다.
- **스택**: `2d6ac MOVE.L A0,-(A7)` / `2d6be MOVEA.L (A7)+,A0`(같은 함수 안 짝).

## seed·fixture

- 자연 부모 seed 116/117(N31~N33 객체). 자연 400 frame에서 이 단위의 PC는 실행되지 않는다. 검증은 typed fixture(단위 시험)와 V1 선언 fixture(원본 ROM native 대 C++)로 한다.
- V1 기반 world: seed 116/117 frame 2의 자연 node(B2b spec과 같은 `NODE_INDEX`)에 선언 편집(레지스터, node field, 부모 `c(A6)`, `4(A6)`, `82(A6)`, PC).
- 자식 진입(`2d3ae` `2d57a` `2d6e6` `3b044`)은 빈 node 대신 자연 node에 `c(A6)` := 다른 자연 node(부모)를 선언한다. `28ae` 자식 생성 경로(`39506` `2d69c`)는 routing된 `28ae`가 실제로 할당하는 chain으로도 실행한다.

## 결정 4 대상: N28 범위 밖 설치 사슬 `2ba50`(구현하지 않음, 보고)

- [F] `2ba50`(N28 `2ba3e MOVE.L #2ba50,(A6)` 설치 값) 정적 closure: `2ba50..2c760` 연속 3,344바이트, 명령 756개, **block 시작 360개**(`BRA.W` 표 없음). routing 밖 callee `2b532` `2b608` `2b63e`(`2b532..2b668` 함수들)를 넣으면 385 block(명령 834), 그 밖 routing 밖 `8d34`(공용 helper), `1c114`, 출구 `2c96a`(`2c94c..` 함수)와 `28ae` 자식 `2d7be` `2d916` `2db06`이 더 있다.
- [F] `4c390`(B2b)의 호출자 `2c1f2` `2c2c2` `2c516` `2c754`와 `4c3cc`의 호출자 `2c728`은 모두 이 범위 안이다. `2b5a2`/`2b5b6`(`2b532..2b668`)는 이 단위의 `2d57a`/`2d3ae`를 자식으로 만든다.
- [F] 소유: 재범위 N28 행 밖(N28 계약 "범위 밖 설치 `2ba50`"), B1/B2 계약 어디에도 없다. 이 단위의 호출 그래프는 이 사슬로 가지 않는다(반대 방향만 있음). 크기가 ~230을 넘으므로 별도 단위 둘 이상이 필요하다([I] 권고: `2ba50..2c760` 360을 둘로 나누고 `2b532..2b668` 25를 앞쪽에 붙임).

## 영향받는 기존 시험·검증기

- [F] 저장소 시험·도구에서 세 범위의 PC를 미연결 탐침으로 쓰는 곳은 없다(16진 상수 전수 검색). 값으로만 나온다: B2b 실행부·시험(`39366` 설치 값, `2d3ae`/`2d57a` 자식 값), N32a 실행부·시험(`39366` 설치 값, 범위 끝 `391e8`), N32b 시험(stop `395dc`, N32a 시작), b1c·n04·n13 시험(우연히 같은 자료 값).
- [I] 자연 경로를 바꾸지 않으므로 D1 구동기(Skip), controller `Execute`(ii), 실제 IRQ 비교는 그대로여야 한다(회귀로 확인).

## 결정 필요 (MAIN DECISION NEEDED)

1. **범위.** 220 block(≤ ~230)이라 B2d 하나로 구현한다(작업자 권고·채택). 대안: `2d57a`/`2d6e6`(46)를 떼어 내면 174.
2. **`3a5be`의 live target.** B2b 결정대로 허용 목록 없이 LONG `82(A6)`로 간다. B2c가 `3a60a` 사슬을 routing하기 전에는 그 경로가 `unsupported animation machine PC`다. 시험은 `3a5be`에서 stop하거나 `82(A6)` := `3a5d2`(N33)로 둔다.
3. **FLOW carry 132개.** N32a·B1a처럼 C 불변 block 전부를 `carry_preserving_pc`에 넣는다(작업자 채택). 대안: 소비자 9개만 넣기(B2b 꼴).
4. **N28 범위 밖 사슬 `2ba50`**(360/385 block)은 이 단위에 넣지 않는다. 별도 단위로 계획할지 정한다.
5. **표 상한.** `3b0ac`·`2d488`·`2d63c` 직접 진입은 원본 산술 그대로(상한 검사 없음)다(F1 결정 3).

## 미확인

- [U] `2d77e`가 읽는 LONG `4(A6)`의 의미(node 연결 field로 추정).
- [U] `443d2`·`4be34`·`43ea4`·`43e08` 결과의 화면 의미, 각 애니메이션 자료의 내용.
- [U] 400 frame 밖·응답 `00`·controller 생략 해제 시의 자연 도달.
- [U] `2b532..2b668`·`2ba50` 사슬에서 `2d3ae`/`2d57a`가 만들어질 때 부모 field 값(이 단위 fixture는 `3a4da` 쪽 부모 꼴만 씀).

## block 목록

[F] scratch `starts.txt`(SHA256 `6310bcda2cbd8b8381a5142cc55c03380370d1633ae715d85913862186354e4b`)와 같다.

- **`2d3ae..2d7be`(87)**: `2d3ae 2d3c6 2d3e8 2d3f6 2d406 2d420 2d440 2d442 2d462 2d46c 2d476 2d480 2d488 2d490 2d494 2d498 2d49c 2d4a0 2d4a4 2d4a8 2d4ac 2d4b0 2d4b4 2d4be 2d4c4 2d4ca 2d4d0 2d4d8 2d4e6 2d504 2d50e 2d510 2d51a 2d524 2d540 2d55c 2d562 2d568 2d56e 2d572 2d578 2d57a 2d592 2d5b4 2d5c2 2d5d2 2d600 2d616 2d620 2d62a 2d634 2d63c 2d644 2d648 2d64c 2d650 2d654 2d658 2d65c 2d660 2d664 2d668 2d672 2d678 2d67e 2d684 2d69c 2d6ac 2d6be 2d6ca 2d6da 2d6e4 2d6e6 2d702 2d71e 2d746 2d758 2d75e 2d764 2d76a 2d770 2d776 2d77e 2d7ac 2d7b2 2d7b6 2d7bc`
- **`391e8..395dc`(115)**: `391e8 391f2 391f6 391fe 39206 3920e 39218 39220 3922a 3923c 39244 3924c 39254 39262 3926e 39276 3927a 3927e 39282 3928c 39292 39296 392a6 392aa 392b0 392ba 392be 392c6 392d6 392d8 392e0 392e2 392ea 392f2 392fa 39302 3930c 39314 3931e 39330 39338 39340 39348 39350 39354 39358 3935c 39362 39366 39370 39380 39384 3939c 393b0 393c6 393d0 393d4 393de 393e2 393e8 39400 39406 3941a 39430 3943a 3943e 39448 39454 3945e 39462 3946a 39472 3947a 39484 3948c 39496 394a8 394b0 394b8 394c2 394c6 394ce 394d8 394dc 394e2 394ea 394ee 394f2 394fc 39506 3951a 3951e 39534 3953e 39542 3954c 3955a 39564 39568 39570 39578 39580 3958a 39592 3959a 395a4 395a8 395b0 395ba 395be 395c6 395ca 395ce 395d2 395d8`
- **`3b044..3b118`(18)**: `3b044 3b062 3b070 3b08a 3b090 3b0a8 3b0ac 3b0c0 3b0c2 3b0e0 3b0e6 3b0ec 3b0f0 3b0f6 3b106 3b10c 3b110 3b116`
