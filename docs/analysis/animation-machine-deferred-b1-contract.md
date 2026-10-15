# 미룬 F4 b 단위(N16b·N19b·U19b·N22b·N29b·N30b) 구현 계약 B1

**구현 전 계약 초안 — 메인 결정 전.** 구현·검증 기록이 아니다. 아래 수치와 목록은 읽기 전용 분석 작업자(Claude Opus 5.5)가 정적 디코드로 만든 것이다. 메인 결정 전에는 routing·실행부·시험을 바꾸지 않는다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 코드 주소는 모두 고정 영역(`<100000`)이라 CPU 주소와 파일 오프셋이 같다. ROM·추출 데이터는 수정하지 않았다.
- [F] 저장소 HEAD `c49bcd2`(V1 native fixture 검증기 포함). routing 기준 `engine/src/animation_machine.cpp` SHA256 `c7318132fcdfd288c12a58ab7e51c03e2920b46d7e939103bd917d72ca8caad2`. 이 파일의 dispatch 사슬(`if ((next.pc>=0x3ac8` … `else return am_error(c,"unsupported animation machine PC")`, 규칙 98개)을 그대로 Python 조건식으로 옮겨 "routing된 PC"를 판정했다. `stage_event_ops_trap` 8곳도 반영했다.
- [F] 정적 디코드: capstone 5.0.6 M68000. block 시작 규칙은 F4 재범위(`animation-machine-object-callbacks-f4-rescope.md` "측정 방법")와 같다.
  - 진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `JMP/JSR d(PC,Dn)` 뒤 연속 `BRA.W` 표 entry가 시작이다.
  - 연속 Bcc(앞 Bcc 바로 뒤가 또 Bcc)는 묶는다. 앞 Bcc의 fall-through는 시작이 아니다.
  - `MOVE.L #imm,(A6)` 설치와 `MOVEA.L/LEA #imm,A0` + `JSR 28ae` 자식은 별도 진입이다. 단위 범위 안이면 따라가고, 밖이면 경계다.
  - routing된 PC에서 멈춘다. TRAP은 경계이며 block 수에 넣지 않는다.
  - 범위 제한은 원 단위 계약의 b 범위를 쓴다.
- [F] 보정: 같은 디코더로 N16b 107 block이 N16 계약 "N16b" 절 목록과 **집합까지 일치**, U19b 86·N30b 160이 각 계약 수와 일치, N19b는 계약 31 + TRAP `b1c90`(경계)로 일치했다. N22b는 154로 N22 계약의 153보다 1 많다(짝수 PC 736은 계약과 같음; 차이 1 block의 출처는 [U]). N29b는 64로 N29 계약 "54 + α(약 10)"와 맞는다.
- 작업자 scratch(저장소 밖, 재현용): `/tmp/claude-0/-home-user-ProjectSlugV/f54ebccc-3a36-5cdd-acbe-c0f66dd6e25d/scratchpad/ana_b/`
  - `route.py`(routing 해석, SHA256 `5fbcd5c4…`), `sdec.py`(디코더, `b8ebd7c5…`), `agg.py`(항목 정의, `667297b9…`), `refs.py`(LONG·PC 상대 참조 탐색), `sem.py` `bnd.py` `grpb.py`, `lists.txt`(block 목록, `6e5cbd13…`).
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인. "자연 400 frame"은 RNG 초기화 400 frame 자연 seed(136 완주, case 141 원본 `odd-pc`) 기록을 말한다.

## 요약

- [F] **현재 routing과의 관계**: 6개 b 단위의 모든 block 시작과 내부 짝수 PC는 현재 routing 밖이다(겹침 0). 후속 단위(N23~N35, H1~H8)가 일부를 이미 routing한 경우는 없다.
- [F] **block 수**: N16b 107, N19b 31, U19b 86, N22b 154, N29b 64, N30b 160. 합계 **602 block**이라 단위 상한(~220)을 크게 넘는다. 그래서 **B1을 세 단위로 다시 나눈다**(결정 1):
  - **B1a** = N16b + U19b = 193, 작은 leaf helper 22를 넣으면 215.
  - **B1b** = N22b + N19b = 185, `3d8de`·`3e250` 사슬 26을 넣으면 211.
  - **B1c** = N29b + N30b = **224**(상한 약간 초과, 결정 2). helper는 모두 경계로 둔다.
- [F] **도달성**: 모든 b 단위 진입은 현재 routing된 코드가 정적으로 설치·분기·호출한다(N19b 제외, 아래). 즉 "실제 실행 가능한 기능"이고 미사용 코드가 아니다. 자연 400 frame에서는 어느 seed도 실행하지 않으므로 **검증은 typed fixture와 실제 ROM 차분만으로** 한다.
  - N19b `b1656`/`b16d6`만 예외다. stage event callback 표 LONG(`e8ec8`/`e8ed0`)에서만 참조되고, 어느 stage stream이 그 index를 고르는지는 [U]다(event 문법 미완, `artifacts/linux_rebase/stage_event_contexts.json`의 scope 문구). `b1d8c`는 routing 밖 N19 경계 helper `b1f4e`의 `JSR (PC)`만 부른다([I] 도달 가능).
- [F] **경계 의존**: N22b·N29b·N30b는 아직 routing 밖인 공용 helper(`4d418` `4d4b4` `4d734` `4d98a` `4d9ba` `4ff96` `d3d7c` `4db18`)를 부른다. 이 helper들은 B2 계약(B2b)에 있다. **B2b를 먼저 병합하면** B1b·B1c fixture가 경계에서 덜 멈춘다(결정 4).
- [F] 자연 400 frame 결과(136/137, D1 54,400 frame 일치)는 바뀌지 않아야 한다. 새 routing은 자연 경로에 없는 PC만 더하기 때문이다([I], 단위마다 회귀로 확인).

| 단위 | 하위 | block | 짝수 PC | 내부 PC | routing 범위 |
| --- | --- | --- | --- | --- | --- |
| B1a | N16b | 107 | 456 | 349 | `783ea..78660` `78cc4..78d5a` `7919a..791c0` `79222..79256` `7962a..79654` |
| B1a | U19b | 86 | 722 | 636 | `b7100..b76a4` |
| B1a | (선택) leaf helper | 22 | - | - | `7930a..79320` `796e6..79746` `b7d2e..b7d4a` |
| B1b | N22b | 154 | 736 | 582 | `3d3f0..3d526` `3d7e8..3d8de` `3da72..3db62` `3db68..3dbba` `3dbbe..3dc24` `3dcac..3dcf2` `3dd0e..3dd42` `3dde4..3de06` `3de54..3def2` `3defa..3df1a` `3df1e..3df44` `3e03e..3e0aa` |
| B1b | N19b | 31 | 143 | 112 | `b1656..b16ea` `b1c82..b1c90` `b1c9e..b1cf8` `b1d8c..b1dae`(TRAP `b1c90`·문자열 `b1c92..b1c9e` 제외) |
| B1b | (선택) `3d8de` `3e250` | 26 | - | - | `3d8de..3d982` `3e250..3e302` |
| B1c | N29b | 64 | 256 | 192 | `30b6c..30d6c` |
| B1c | N30b | 160 | 736 | 576 | `3323e..336d2` `3395c..33a88` |

## 공통 규칙(B1a~B1c)

1. **실행부·이름.** 단위마다 실행부 파일 하나를 둔다. 권고 이름은 `animation_machine_objects_b1a.cpp`처럼 묶음 이름이다. 오류 문자열은 `unsupported animation objects b1a PC`(내부 PC 직접 진입)와 `objects b1a caller requires known carry`(C 소비 block에 Unknown C)다. 하위 단위 이름(`n16b` 등)을 쓸지는 결정 3이다.
2. **routing.** 위 표의 범위를 dispatch 사슬에 규칙 하나로 더한다. 기존 범위와 겹치지 않아(겹침 0) 규칙 위치는 결과에 영향이 없다. 범위 밖 PC는 지금처럼 `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
3. **경계.** 범위 밖 미연결 callee·설치값·자식 값은 경계다. 단위 시험은 그 PC에서 stop만 확인한다(F4 시험 관례). rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다.
4. **known C.** RTS 앞 `ORI.B #1,CCR`은 Set, `ANDI.B #fe,CCR`·`MOVEQ`·`MOVE`·`TST` 뒤 RTS는 Clear다. CMP 결과를 그대로 돌려주면 계산 C다. 소비 block(BCC/BCS/SCC)은 Unknown C로 들어오면 checked 오류다. typed fixture는 실제 ROM 소비자를 복귀 LONG으로 두고 native 분기로 C를 확인한다(N19·N22·N29 선례).
5. **표.** `JMP d(PC,D0.W)` 표 entry는 모두 block 시작이다. F1 메인 결정 3(N18 `86298`, N29 `30a72`, N30 `336de` 선례)대로 표 진입 block은 상한 검사 없이 PC = 표 base + sext((4·(`D0.W` & `ff`)) & `ffff`)로 옮긴다.
6. **banked 자료 읽기.** `2000xx` operand는 live bus 읽기 관례를 따른다.
7. **`2986` 호출.** `2986` caller-X 제한(buffer_cue 결정 1)은 그대로다. 이 단위의 호출자가 `2986` 실패 경로에 들어가면 기존 checked 오류다.
8. **interpreter 호출**(`49f8c` `49f96` `49fc6`)은 기존 interpreter 실행부를 쓴다. `49fc6`의 C는 기존 known C 규칙을 따른다.

## 공통 native 검증 계획

V1 검증기 `tools/verify_animation_machine_unit_fixtures.py`(HEAD `c49bcd2`)를 그대로 쓴다. 단위마다 spec 모듈(`tools/unit_fixture_specs/b1a.py` 등)을 둔다.

- **seed 준비.** `U.natural_cases()`가 D1 검증기의 `declared_rebase()`(Linux 재생성 `artifacts/linux_rebase/stage_entry_body` seed, in-process 선언 rebase)와 RNG 준비 `R.prepared(case)`를 거친다. 이 경로를 그대로 쓴다.
- **부모 node fixture.** `U.seed_node_fixture(case, frame, node)`로 부모 callback을 가진 자연 node 상태를 얻는다. 그 상태에 `U.with_host_writes(...)`로 선언 편집을 더한다.
  - 분기 조건 field 편집: 부모가 자연 경로 대신 b 진입으로 가게 한다.
  - 또는 `(A6)` LONG := b 진입, PC := b 진입.
  - stop은 node의 RTS 대상(dispatcher 복귀)이나 첫 경계 PC다.
- **block 직접 진입.** 모든 block 시작을 한 번 이상 직접 진입 fixture로 덮는다. 상태는 부모 node 상태를 `U.advance_native`로 그 PC까지 진행한 것을 우선 쓰고, 닿지 않으면 같은 node 상태에 field를 선언해 쓴다.
- **오류 fixture.**
  - 내부 PC 전수 → `('error','unsupported animation objects <unit> PC')`.
  - C 소비 block Unknown C → `('error','caller requires known carry')`.
  - 범위 밖 경계 PC(stop 없이) → `('error','unsupported animation machine PC')`, 상태 보존.
  - 홀수 PC(범위 양끝) → unaligned 오류.
- **표.** 모든 slot과 상한 이상 index(`D0.B` ≥ 상한)를 표 진입 block에서 확인한다.
- **음성 검사.** V1 self-test처럼 C++ 입력 RAM·레지스터를 1 bit 바꿔 차이가 검출되는지 본다.
- **회귀.**
  - RNG 초기화 400 frame: 136/137 완주, 불일치 0.
  - 기본 120 frame, D1 driver 54,400 frame 일치.
  - G1~G3 검증기, 기존 단위 시험(아래 "영향받는 기존 시험").

## B1a = N16b(107) + U19b(86) [+ leaf helper 22]

### N16b

- **진입과 참조**([F]):
  - `783ea`: N16 `783ce BNE.W`(`TST.W 88(A6)` ≠ 0).
  - `785f2`: N16 `783e2 BNE.W`(`BTST.B #2,9b(A6)`). 범위 안 설치 `785e8` `786e4`(뒤는 범위 밖)도 이 값을 쓴다.
  - 범위 안 설치 `7840c` `78444` `78462` `78496` `784bc` `784fa` `7855a` `785b4` `785f2` `78628`, 꼬리 `78cc4`(설치 `78d0a` `78d3a`), helper `7919a` `79222` `7962a`.
- **의미**([F] 바이트, [I] 해석): 같은 객체 상태기계(`7839a` 계열)의 두 번째·세 번째 상태 갈래다. `88(A6)` 타이머 갈래와 `9b` bit 2 갈래가 상태 callback을 차례로 설치하며 움직인다.
  - 애니메이션 자료: bank `2000d4` 읽기 6곳.
  - interpreter `49f8c` `49fc6`, 공용 `4be06` `4be34` `4bfa4`, `1ab02` 화면 판정, `28ae` 자식 생성.
- **known C**([F]):
  - 생산: `79222`(Set `79246`/RTS `7924a`, Clear `79250`/`79254`), `7962a`(Set `79648`/`7964c`, Clear `7964e`/`79652`), `78d2a ORI`.
  - 소비 14곳(복귀점 BCC/BCS): `78408` `78454` `784ae` `7854c` `78652`(N16 `791fa`), `7853e`(`79222`), `784a0` `785dc`(`49fc6`), `78636`(`7962a`), `78644`(`7930a`, 경계), `78cfe`(`1ab02`), `78d1a`(`28ae`), `79630`(`4945e`), `79638`(`79722`, 경계).
- **경계**([F]):
  - 범위 밖 설치 `78660` `78716`, 분기 `78776`, 자식 `78e0e`, 꼬리 `cc8b4`(>`4000` 거리 tail).
  - helper `7930a` `796e6` `7970e` `79722`.
  - `78660`/`78716`/`78776` 사슬은 정적 76/31/155 block, `cc8b4`는 323 block이다(아래 "범위 밖 사슬").
- **자연 부모 seed**: 76 77 98 99 104 105. 각 seed에서 `7839a` callback이 1회 실행된다(N16 계약).
- **fixture**:
  - 부모 `7839a` node에서 `88.W` := 1 → `783ea` 갈래.
  - `88.W` := 0, BYTE `9b` bit 5 := 0, bit 2 := 1 → `785f2` 갈래.
  - 각 설치 값은 `(A6)` := 값으로 직접 진입한다.

### U19b

- **진입과 참조**([F]): U19 `b6a0c MOVE.L #b7100,(A6)`, `b6a1a MOVE.L #b749c,(A6)`(U19 범위 `b68ba..b6ba0`, `6f1c2` 결과 D1 bit 0/1에 따라).
  - 범위 안 설치: `b718c` `b71ae` `b723c` `b72f2` `b7386` `b73a0` `b7444` `b7474` `b7528` `b754e` `b75dc` `b7618`.
  - routing된 대상: `b68be`(U19, `b724c` `b7492`), `b6a2a`(U19, `b75fe`), `b76a4`(U18, `b769e` 설치·fall-through), `b76bc`(U18 분기).
- **의미**([I]): U19 계약 미확인 1의 지상 상태 뒤 두 상태 사슬(`b7100`/`b749c`)이다. 애니메이션은 bank 표 `2001a8`/`2001ac`(32곳 읽기)를 쓴다. interpreter `49f8c` 16곳, `6f1c2` 지형 판정 4곳, `49fc6` C 5곳을 쓴다.
- **known C**([F]): 생산 없음. 소비 5곳은 `b71a0` `b726a` `b7392` `b7538` `b75ee`(모두 `49fc6`)다.
- **경계**([F]): `b7d2e`, `b7d3c`(둘 다 `JSR 43e34` 뒤 RTS 2 block helper; 선택 leaf). 자료 포인터 즉값 `15500`(`b722e`), `4cccc`(`b7426`)는 `d(A6)` LONG 쓰기라 실행 PC가 아니다.
- **자연 부모 seed**: U19 `b6362`/`b68ba` 계열 seed 8 9 80 81(U19 계약). 그 seed에서 `b68ba` 상태까지 가는지는 [U]다.
- **fixture**: U19 객체 node 상태에서 `(A6)` := `b7100`/`b749c`로 직접 진입한다. `6f1c2` 입력(지형 RAM)을 선언 편집해 `b6a0c`/`b6a1a` 설치 경로도 1개 이상 덮는다.

### 선택 leaf helper(22 block)

- `7930a`(4; `78644`의 C 생산 `7931e ANDI`), `796e6`(7), `7970e`(3), `79722`(4; Clear `7973e`/Set `79744`), `b7d2e` `b7d3c`(각 2).
- 시작: `7930a 79314 79318 7931a 796e6 796f4 796fa 796fc 79700 79706 79708 7970e 7971e 79720 79722 79732 7973a 79740 b7d2e b7d3a b7d3c b7d48`.

## B1b = N22b(154) + N19b(31) [+ `3d8de`·`3e250` 26]

### N22b

- **진입과 참조**([F]):
  - `3d3f0`: N22a `3d37a` 설치.
  - `3dcac`: N22a `3d354 JSR`, N22b `3dbc6`.
  - `3defa`: N22a `3dc76 JSR`.
  - `3d7e8`·`3da72`: 범위 밖 설치 `3d7e2`·`3da6c`. 각각 N22b가 설치하는 범위 밖 사슬 `3d526..3d7e8`·`3d8de..3da72` 안에 있다.
  - N22a 계약의 미실행 내부 callee `3dcda` `3dd0e` `3dd30` `3dde4` `3de54` `3df30` `3e03e` `3e0a8`.
- **의미**([I], N22 계약 결정 1의 해석): N22 객체의 공격·파괴 상태 사슬이다.
  - 9 slot BRA.W 표 `3d8a4`(slot `3d8a8..3d8c8`).
  - `28ae` 자식 `3db68`(범위 안), `3e250`(범위 밖).
  - interpreter `49f8c` `49f96`, 소리 `3af8`.
- **known C**([F]):
  - 생산: `3dcac` → `JMP 4d418`(C는 `4d418` RTS의 것; B2b), `3dcda` → `JMP 4d4b4` 또는 `TST` 뒤 RTS(Clear).
  - 소비: `3d40a SCC`(`28ae`), `3d478 BCC`(`3dcf2`, N22a known C), `3dbae BCC`(`49fc6`), `3dbca BCS`(`3dcac` → `4d418`).
- **경계**([F]):
  - B2b helper: `4d418`(분기) `4d4b4` `4d734` `4d98a` `4ff96` `d3d7c`.
  - 범위 밖 설치 `3d526`(사슬 190 block), `3d8de`(분기·설치).
  - 자식 `3e250`, `19a00`(scene 계열 helper, 11 block), `8d34`(H 계열 근처, 8 block; `3d8de` 사슬 안 JMP).
- **자연 부모 seed**: 38 39 116 117. `3d32c` callback이 seed마다 80~84회 실행된다. 그러나 `3d340 JSR 4d2d4` Set·`3d350`·`3d35c` 조건이 자연 경로에서 맞지 않아 `3d37a` 설치는 실행되지 않는다(N22 계약).
- **fixture**:
  - `3d32c` node에서 `(A6)` := `3d3f0`.
  - `3d7e8`/`3da72`는 `(A6)` 직접 진입.
  - `3d8a4` 표 slot 9개 전부와 D0 상한 이상.
  - `3dcac`는 복귀 LONG = `3d358`(N22a)·`3dbca`(N22b)로 두고 `4d418` 경로를 native로 따라간다. B2b 병합 전이면 `4d418`에서 stop이다.

### N19b

- **진입과 참조**([F]):
  - `b1656`, `b16d6`: stage event callback 표 LONG `e8ec8`/`e8ed0`. 같은 표의 이웃 `e8ecc`가 N19 자연 진입이다.
  - `b1d8c`: routing 밖 `b1f4e JSR (PC)`.
  - 범위 안 설치 `b16b0`, `28ae` 자식 `b1660`.
- **의미**: N19 계약 "N19b로 넘기는 block" 절 그대로다. `b1c82`는 `78(A6)` − 1 ≤ 5를 확인하고 아니면 `TRAP #f`(`TK205A ERR`)다.
- **known C**([F]): 생산 `b1cc2 ORI`(Set). 소비 `b16c2 BCS`(N19 `b15e0`: `61` bit 7), `b1cb4 BCC`(`28ae`).
- **경계**: TRAP `b1c90`(결정 6 관례: checked 경계). 다른 출구는 모두 routing된 N19 진입(`b186a` `b19b2` `b1b76` `b1c0e` `b1cf8` `b1dfa` `b15e0` `b160a`)이다.
- **자연 부모 seed**: 12 13(N19 객체). 표 index 경로는 [U].
- **fixture**:
  - seed 12/13 N19 node에서 `(A6)` := `b1656`/`b16d6`. `78.W` ∈ {1..6, 0, 7}로 TRAP 경계 쪽도 확인한다.
  - `b1d8c`는 복귀 LONG을 선언해 직접 진입한다.
  - `49a84` 난수 bit 선택 반복(`b1cdc..b1cf6`)은 D2 & `1f` 경계값을 포함해 확인한다.

### 선택 `3d8de`(13)·`3e250`(13)

- `3d8de`: N22b `3d8d4` 설치·표 slot `3d8ac` `3d8b0` 분기 대상. 끝에서 `4ff96`·`d3d7c`(B2b)를 부른다.
- `3e250`: N22b `3d3fa`의 `28ae` 자식.
- 시작:
  - `3d8de 3d8ea 3d8f4 3d8fa 3d916 3d932 3d94e 3d974 3d97e`(+`3d982` 설치 값은 범위 밖).
  - `3e250 3e268 3e280 3e29a 3e2b6 3e2d0 3e2d6 3e2dc 3e2e0 3e2e6 3e2ec 3e2f0 3e2f2`.

## B1c = N29b(64) + N30b(160) = 224

### N29b

- **진입과 참조**([F]):
  - `30b6c`: N28 `30f96` 설치. N28 계약 범위 밖 설치 값이다.
  - `30cb8`: 범위 안 `30cae` 설치.
  - 범위 안 설치 `30c4c`.
  - 출구: N28 `30fa0`(`30cb4 BRA.W`, N28 결정 9의 두 번째 진입), `2a00`.
- **의미**([F]): `30b6c`는 BYTE `5e`(무부호 < `1b`)로 27 slot BRA.W 표 `30b80`(slot `30b84..30bec`, 각 4바이트)을 고른다. 상한 이상은 `30bf0`이다.
  - `30c4c` 계열은 `317b8`·`4d8d8`·N29 helper(`3166c` `31a12` `319f6` `31696` `316ac` `3165e`)로 착지 상태를 갱신한다.
  - `30cb8` 계열은 `4ae4a`, `4ff96`, `d3d7c`(파편 4개 생성)과 `2986` 자식 `30d6c`(A1 = `100bf4`)로 파괴 처리한다.
- **known C**([F]): 생산 없음. 소비 `30c7c BCS`(N29 `319f6` known C).
- **경계**([F]): `317b8`(13 block helper), `4db18` `4ff96` `d3d7c`(B2b). `2986` 자식 값 `30d6c`(9 block)는 실행 PC가 아니다(N28 `2cb30` 관례, 결정 5).
- **자연 부모 seed**: 116 117. N28 `30f96` 설치는 자연 400 frame에서 실행되지 않는다(N28 계약).
- **fixture**:
  - 116/117의 N28/N29 객체 node에서 `(A6)` := `30b6c`, BYTE `5e` = 0..26, `1b`, `ff`.
  - `(A6)` := `30cb8`. `30cae`로 가는 BYTE `98` = 0 경로도 덮는다.

### N30b

- **진입과 참조**([F]):
  - `3323e`: N30a `33234` 설치. 조건은 `331f6 JSR 4d2d4` Set, `33204 JSR 4d418` Set이다.
  - `3395c`: N30b 안 `BRA.W` 6곳(`33298` `33332` `333ee` `3347e` `334d8` `33536`).
  - 범위 안 설치 `33280` `3329c` `332d6` `33364` `333f2` `3341a` `3349e` `33500` `3353a` `3359c`.
  - `33336`은 N30b block이며, 범위 밖 함수 `330a4`의 `33104`도 이 값을 설치한다.
  - 출구 `33132`(설치 `33a0c`, `33546 BRA`), `33a88` `33aa4`(N30a 공유 꼬리).
- **의미**([F]/[I]): N30 객체의 이동·공격 상태기계(`33250`)다. `4ae4a`가 고른 9 slot 표 `335fa`(`CMPI.W #9,D0; BCC`; slot `335fe..3361e`)가 있다. 파괴는 `3363a`(`2986` 자식 `338f8`)다. 꼬리 `3395c..33a88`는 `4d418` C → 설치 `33132`다.
- **known C**([F]): 생산 없음. 소비 `3328e` `3352c BCC`(`49fc6`), `33390 BCC` `335b4 BCS`(`4c2c4`, 경계), `33a08 BCS`(`4d418`, B2b).
- **경계**([F]):
  - 범위 밖 helper: `33940`(B2b `3383c` 항목), `33c78` `33d2c` `33dce` `33e48` `343e0` `34470` `34490` `3453a` `4c2c4`.
  - B2b helper: `4d418` `4d734` `4d98a` `4d9ba` `4ff96` `d3d7c`.
  - 앞의 10개는 어느 계약에도 없는 helper다(합 약 190 block; "범위 밖 사슬").
- **자연 부모 seed**: 116 117. `331d8`이 80회 실행되지만 `4d2d4` Clear로 설치까지 가지 않는다(N30 계약).
- **fixture**:
  - `331d8` node에서 `(A6)` := `3323e`.
  - 상태 설치 값 10개 각각 `(A6)` 직접 진입.
  - `335fa` slot 9개 + `D0.W` ≥ 9.
  - `33a02 JSR 4d418` → `33a08`은 B2b 병합 뒤 native C로 확인하고, 병합 전이면 stop이다.

## 범위 밖 사슬(B1이 경계로 두는 것, 참고)

[F] 범위 제한 없이 따라간 정적 closure(routing된 PC와 B1/B2 항목에서 멈춤)다. 어느 계약에도 없다.

| 대상 | 참조 | closure block | 비고 |
| --- | --- | --- | --- |
| `3d526` | N22b `3d486` `3d80c` 설치 | 190 | `3d526..3d7e8` `3e302..3e6bc` 등 24 진입 |
| `78776`/`78660`/`78716` | N16b 분기·설치 | 155/76/31(겹침) | `78776..78a16` `78dee..79054` `7975a..79884` `ea69c..ea712` |
| `cc8b4` | N16b `78c9a` 거리 tail | 323 | 공용 animation 루틴 `cc778` 계열(재범위 "경계 함수") |
| `33e48` | N30b | 75 | `1c0b4..1c1ba` `34256..3437a` `4d6b4` |
| `33c78` `33d2c` `33dce` `343e0` `34470` `34490` `3453a` `4c2c4` | N30b | 19/23/7/23/2/2/11/6 | |
| `317b8` | N29b | 13 | |
| `19a00` `8d34` | N22b | 11/8 | |

## 영향받는 기존 시험·검증기

[F] 아래 파일이 새 routing 대상 PC를 경계로 쓴다. 대부분 F4 관례(경계는 stop만 확인)라 그대로 통과할 것으로 본다([I]). 병합 전에 각 사용처가 stop인지 rollback 기대인지 확인한다.

- `engine/tests/animation_machine_objects_n16_test.cpp`(`783ea` `785f2` `7930a` `79722`).
- `animation_machine_objects_n19_test.cpp`(`b1656` `b1d8c`).
- `animation_machine_objects_n22_test.cpp`(`3d3f0` `3dcac` `3defa`).
- `animation_machine_objects_n29_test.cpp`(`30b6c` `317b8`).
- `animation_machine_objects_n30_test.cpp`(`3323e` `3395c` `33940`).
- `animation_machine_objects_u18_test.cpp`(`b7d2e`).
- `tools/observe_animation_machine_objects_g2.py` 86행(U19 `written=(0xb7100,0xb749c,…)`). pin된 관측기이며 "쓰기만 함" 선언이라 실행 결과는 바뀌지 않는다([I]).

## 결정 필요 (MAIN DECISION NEEDED)

1. **B1 재분할.** 602 block은 ~220 상한의 약 2.7배다. B1a(193/215), B1b(185/211), B1c(224)의 세 단위로 나누는 안을 채택할지 결정한다. 대안은 b 단위 6개를 각각 따로 하는 것(31~160 block; 단위 수는 늘지만 원 단위 계약과 1:1).
2. **B1c 224.** 상한을 4 block 넘는다. 다른 묶음으로 옮길 자리는 없다(B1b에 N29b를 더하면 249 이상). 그래서 B1c 224를 허용하거나, N29b(64, `317b8` 13을 넣으면 77)를 단독 단위로 떼고 N30b(160)만 B1c로 둔다.
3. **이름.** 묶음 이름(`objects-b1a`)으로 할지, 하위 이름(`objects-n16b`·`objects-u19b` 등; 원 계약의 "N22b = objects-n22b 예정" 관례)으로 할지 정한다. 하위 이름이면 실행부 파일이 6개다.
4. **순서.** B2b(공용 helper `4d418` 계열)를 B1b·B1c보다 먼저 병합할지 정한다. 권고는 B2b → B1c → B1b → B1a → B2a다. B2b가 이미 routing된 N28~N33의 경계까지 줄인다.
5. **`2986` 자식 값**(`30d6c`, `338f8`, B2의 `b3dbc`). N28 관례(`2cb30`, "실행 PC가 아님")를 유지할지 정한다. 바이트로는 코드다([F], `30d6c MOVE.W #…; JSR 8ebe` 등). [I] `2986`이 A1 = `100bf4` list에 넣는 cue callback이라 다른 처리기가 실행할 가능성이 있다. 실행 경로는 [U]다.
6. **N19b 표 index 도달성.** stage event 문법이 미완이라 `e8ec8`/`e8ed0`을 고르는 stream이 있는지 [U]다. 구현은 하되(정적 코드 포인터가 있으므로) 도달성은 [U]로 기록하는 안을 권고한다.

## 미확인

- [U] N22b 계약 153과 이번 154의 차이 1 block.
- [U] U19 seed에서 `b68ba` 지상 상태 도달 여부. N19b 표 index·`b1f4e` 경로의 실제 도달.
- [U] `2986` 자식 값의 실행 주체.
- [U] 400 frame 밖, 응답 `00`, controller 생략 해제 시의 자연 도달(재범위 §3과 같음).

## block 목록

[F] scratch `lists.txt`(SHA256 `6e5cbd1388d8cd528c21ac641aa3f35777d4fc27ecc96d6d3fb860dd5e6c2d8a`)와 같다.

- **N16b(107)**: `783ea 783f2 783fe 78404 78408 7840c 7843e 78444 7844a 78450 78454 78458 7845e 78462 78468 78490 78496 7849a 784a0 784a4 784aa 784ae 784b2 784b8 784bc 784c0 784cc 784f4 784fa 784fe 78504 78510 7851a 78522 78528 7852c 78534 7853a 7853e 78542 78548 7854c 78550 78556 7855a 78564 7856e 785ae 785b4 785ba 785c4 785d0 785d6 785dc 785e0 785e8 785ee 785f2 78622 78628 7862c 78632 78636 7863a 78640 78644 78648 7864e 78652 78656 7865c 78cc4 78cc8 78cd0 78cd6 78cdc 78ce6 78cf0 78cf4 78cfe 78d02 78d08 78d0a 78d1a 78d1e 78d2a 78d2e 78d3a 7919a 791a0 791aa 791b0 791b8 791be 79222 7922c 79240 7924c 79250 7962a 79630 79634 79638 7963c 79640 79648 7964e`
- **U19b(86)**: `b7100 b7106 b7112 b714a b714e b7186 b718c b719a b71a0 b71a4 b71aa b71ae b71ba b71f2 b71f6 b722e b723c b7246 b724c b7256 b725e b7264 b726a b726e b727a b72b2 b72b6 b72ee b72f2 b72f8 b7304 b733c b7340 b7378 b7380 b7386 b738c b7392 b7396 b739c b73a0 b73b2 b73ea b73ee b7426 b7444 b744c b745c b746a b7474 b7482 b7488 b7492 b7498 b749c b74a2 b74ae b74e6 b74ea b7522 b7528 b7532 b7538 b753c b7544 b754a b754e b755a b7592 b7596 b75ce b75dc b75e6 b75ee b75f2 b75f8 b75fe b7604 b760e b7614 b7618 b761e b762a b7662 b7666 b769e`
- **N22b(154)**: `3d3f0 3d3fa 3d40a 3d414 3d41a 3d422 3d426 3d42a 3d432 3d436 3d44a 3d45a 3d46a 3d470 3d474 3d478 3d47c 3d486 3d48c 3d494 3d498 3d4a8 3d4c2 3d4d2 3d4e2 3d4e6 3d4ea 3d4f4 3d508 3d51a 3d7e8 3d7ec 3d7f4 3d7fc 3d804 3d80c 3d812 3d816 3d81a 3d81e 3d828 3d836 3d856 3d866 3d87a 3d880 3d884 3d888 3d88c 3d898 3d8a0 3d8a8 3d8ac 3d8b0 3d8b4 3d8b8 3d8bc 3d8c0 3d8c4 3d8c8 3d8cc 3d8d4 3d8da 3da72 3da78 3da7e 3da82 3da8a 3da98 3da9c 3daa0 3daa4 3daae 3dab2 3dab6 3dabe 3dac2 3dac6 3dacc 3dad0 3dadc 3dae4 3daee 3daf4 3db10 3db2c 3db52 3db5c 3db68 3db72 3db80 3db9c 3dba2 3dba8 3dbae 3dbb2 3dbb8 3dbbe 3dbc2 3dbc6 3dbca 3dbce 3dbd8 3dbe2 3dbea 3dbf2 3dbfc 3dc04 3dc0e 3dc16 3dc20 3dcac 3dcbc 3dcc4 3dcc8 3dcd2 3dcd4 3dcda 3dce2 3dcea 3dcec 3dd0e 3dd18 3dd1e 3dd28 3dd2e 3dd30 3dde4 3ddee 3de54 3de64 3de8c 3de8e 3de94 3de9a 3dea8 3deaa 3deb0 3deb4 3ded4 3dee2 3def0 3defa 3df04 3df0e 3df1e 3df22 3df30 3e03e 3e042 3e06e 3e078 3e0a6 3e0a8`
- **N19b(31)**: `b1656 b165a b1660 b1670 b1686 b1690 b16a4 b16aa b16b0 b16c2 b16c6 b16cc b16d0 b16d4 b16d6 b16e6 b1c82 b1c9e b1ca0 b1cb4 b1cb8 b1cc2 b1cc6 b1cca b1cce b1cdc b1cec b1cf6 b1d8c b1d92 b1da4`
- **N29b(64)**: `30b6c 30b78 30b84 30b88 30b8c 30b90 30b94 30b98 30b9c 30ba0 30ba4 30ba8 30bac 30bb0 30bb4 30bb8 30bbc 30bc0 30bc4 30bc8 30bcc 30bd0 30bd4 30bd8 30bdc 30be0 30be4 30be8 30bec 30bf0 30c00 30c06 30c0c 30c16 30c1c 30c3c 30c46 30c4c 30c52 30c5e 30c64 30c68 30c70 30c78 30c7c 30c80 30c86 30c8a 30c8e 30c92 30c96 30ca4 30cae 30cb4 30cb8 30cc4 30ccc 30cd6 30cdc 30cf8 30d14 30d30 30d5c 30d66`
- **N30b(160)**: `3323e 33248 3324c 33250 33264 33274 3327a 33280 33284 33288 3328e 33292 33298 3329c 332a6 332bc 332d0 332d6 332da 332ea 332f0 332f8 332fe 33320 33324 33328 3332c 33332 33336 33358 33364 33368 33370 3337a 3337e 33386 33390 33394 333aa 333ac 333b4 333b8 333bc 333c0 333c4 333ce 333d4 333dc 333e2 333e8 333f2 33408 33414 3341a 3341e 33428 33430 33434 3346a 3346e 33472 33478 33482 33498 3349e 334a8 334ac 334b4 334bc 334c0 334c4 334c8 334cc 334d2 334dc 334ea 334fa 33500 33504 3350c 33516 3351a 3351e 33522 33526 3352c 33530 33536 3353a 33546 3354a 33550 3355a 33562 33580 33584 33588 3358e 3359c 335b4 335b8 335c4 335cc 335d0 335d4 335d8 335de 335ee 335f6 335fe 33602 33606 3360a 3360e 33612 33616 3361a 3361e 33622 3362c 33636 3363a 33644 3364e 33654 33670 3368c 336b8 336c2 336cc 3395c 33964 33968 33970 33974 33980 33990 33994 339a4 339aa 339b0 339bc 339c6 339d2 339dc 339e0 339ec 339f6 339fa 33a08 33a0c 33a16 33a20 33a28 33a30 33a3a 33a48 33a50 33a5a 33a76`
