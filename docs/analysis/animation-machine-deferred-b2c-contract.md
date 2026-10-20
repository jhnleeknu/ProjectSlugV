# `82(A6)` partner 부상태 사슬·주변 작은 사슬 구현 계약 B2c

**구현 전 계약 — 메인 결정 전.** 구현·검증 기록이 아니다. 아래 수치와 목록은 구현 작업자(Claude Opus 5.5 / high)가 정적 디코드로 만든 것이다. 실행부·시험은 이 계약을 그대로 따른다. 범위 밖 판단은 "결정 필요"에 남긴다.

## 기준 입력

- [F] ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 코드 주소는 모두 고정 영역(`<100000`)이라 CPU 주소와 파일 오프셋이 같다. banked 주소(`2000xx`)는 live bus로 읽는다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `e5bfb73`(`origin/main`). routing 기준 `engine/src/animation_machine.cpp` SHA256 `7e76e64bad3037cc22c6597b3c8746b05f7540dee4703c4dc18853179cf951a6`(dispatch 규칙 109개).
- [F] 정적 디코드: capstone M68000. block 시작 규칙은 B1 계약 "기준 입력"과 같다(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `MOVE.L #imm,(A6)` 설치, 연속 Bcc 묶음, routing된 PC에서 멈춤). 이 사슬에 필요한 규칙 셋을 더했다.
  - `MOVE.L #imm,82(A6)`(부상태 설치) 값은 진입이다. `3a5be`의 `JSR (A0)`이 A0 = LONG `82(A6)`로 실행한다(B2 계약 `3a5be`).
  - `LEA x(PC),A0` 바로 뒤 `BRA.W 3ab3e`/`BRA.W 3aba4`의 x는 진입이다(`JMP (A0)` 복귀 대상). `3aba4`로 가는 경우 x부터 4바이트 간격 7개의 `BRA.W` slot이 `JMP (A0,D1.W)` 대상이다.
  - `3ab7a MOVEA.L 3ab80(PC,D0.W),A0`의 LONG 표 6개 entry(`3a62e` `3a774` `3a8ba` `3a8f8` `3aae8` `3ab0c`)는 진입이다.
- scratch(저장소 밖, 재현용) `/Users/start/Workspce/ms5-scratch/b2c/`: `route.py`(routing 해석, SHA256 `bcb2a44d…`), `closure.py`(정적 closure·block 시작, `b1ae306d…`), `refs.py`(LONG·PC 상대 참조, `e8e0f53a…`), `blocks.py`(block별 명령, `3dc8e26e…`), `b2cdis.py`(선형 디코드, `fd93827d…`), `starts_a.txt`(B2c 218 block 시작, `72238f6a87716944fb30a7aef485f3a70d46839e3526fd29c258cea9ebd3fea4`).
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 요약

- [F] **B2 계약 수 75와의 차이.** 같은 진입 `3a60a`의 정적 closure는 **175 block**(사슬 170 + 공용 helper `3b48c` 5)이다. B2 계약의 75는 `82(A6)` 설치 값 27개, `LEA` 복귀 대상 8개, 7 slot `BRA.W` 표 3개(21 slot), LONG 표 6 entry를 block 시작으로 세지 않은 수로 본다([I]). 이 계약은 위 규칙을 따른 175를 쓴다.
- [F] **현재 routing과의 관계**: 아래 B2c의 모든 block 시작·내부 짝수 PC는 현재 routing 밖이다(겹침 0). 범위 끝 바로 옆은 이미 routing돼 있다: `3a5d2..3a60a`(N33), `3b424..3b458`(B2b), `3b542..3b5a6`(N33), `3acd6`(B2b).
- [F] **도달성**: 모든 진입이 이미 routing된 코드에서 정적으로 참조된다(아래 표). 자연 400 frame(D1 54,400/54,400, 136 seed 완주)은 어느 진입도 실행하지 않는다. 실행했다면 미연결 PC 오류가 났을 것이기 때문이다. 검증은 typed fixture와 실제 ROM 차분으로 한다.
- [F] 후보 전체 합은 269 block이다(아래 "B2c-b"). 상한 약 220을 넘어 **두 부분으로 나눈다**(결정 1). 이 계약이 구현하는 것은 **B2c(= B2c-a) 218 block**이다.

| 항목 | block | 짝수 PC | 내부 PC | routing 범위 | 진입을 만드는 곳(참조) |
| --- | --- | --- | --- | --- | --- |
| `82(A6)` 부상태 사슬 | 170 | 728 | 558 | `3a60a..3ab80` `3aba4..3abde` | N33 `3a5d2 MOVE.L #3a60a,82(A6)`; 실행은 `3a5be JSR (A0)`(B2b), 호출자 N31·N32·N32b·N33 11곳 + 범위 밖 6곳 |
| `3b48c`(위치 보정 helper) | 5 | 24 | 19 | `3b48c..3b4bc` | `3ab30` `3ac86 BSR`, `3ac44` `3b50c JSR (PC)` |
| `3b5a6` | 5 | 66 | 61 | `3b5a6..3b62a` | B2b `38d5c JSR (PC)`, 범위 밖 `38b8e` |
| `3af86`(`28ae` 자식) | 14 | 91 | 77 | `3af86..3b03c` | B2b `38d60 MOVEA.L #3af86,A0; JSR 28ae` |
| `3ae84`(`28ae` 자식) | 20 | 116 | 96 | `3ae84..3af6c` | B2b `3a50e MOVEA.L #3ae84,A0; JSR 28ae` |
| `1bf80`(leaf) | 3 | 10 | 7 | `1bf80..1bf94` | `3af9c`, 범위 밖 `2d92c` `314ce` |
| `1d198`(leaf) | 1 | 12 | 11 | `1d198..1d1b0` | `3af8e`, 범위 밖 `2d91e` `314aa` `36682` `36824` `1d226` |
| 합계 B2c | **218** | 1,047 | 829 | | |

## 공통 규칙

B1 계약 "공통 규칙"을 그대로 따른다. 다른 점과 이 단위 값만 적는다.

1. **실행부·이름.** `engine/src/animation_machine_objects_b2c.cpp`, 함수 `animation_objects_b2c_block`. 오류 문자열은 `unsupported animation objects b2c PC`(내부 PC 직접 진입)와 `objects b2c caller requires known carry`(C 소비 block에 Unknown C)다.
2. **routing.** 위 표의 8개 범위를 dispatch 사슬의 마지막 `else if` 하나로 더한다. 기존 범위와 겹치지 않는다.
3. **경계.** 범위 밖 callee는 경계다(stop만 확인). 범위 밖 미연결 callee: 없음(아래 "경계"의 callee는 모두 routing돼 있다). 자식·자료 값은 실행 PC가 아니다. 단위 시험의 rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다.
4. **known C.** C 소비 block은 셋뿐이다: `3af12` `3af60` `3b026`(모두 `BCC.W`, `JSR 49fc6`가 돌려준 C). 이 셋은 carry 보존 목록에 넣고 Unknown C면 checked 오류다. 같은 block 안에서 만들고 소비하는 flag(`3aeca ADDQ.B`/`BCS`, `3b48c CMPI.B`/`BLS`, `3aea0 CMPI.B`/`BCC`, `3a97c CMPI.B`/`BCC`, BTST/TST/CMPI + Bcc)는 block 안에서 계산한다. 이 단위에는 다른 block이 소비하는 known C 생산자가 없다. 그래서 그 밖의 모든 block은 끝에서 Unknown이다.
5. **간접 분기**(원본에 거르기가 없음, live target; F4 결정·B2 `3a5c8`과 같다):
   - `3ab7e JMP (A0)`: PC := A0. A0는 `LEA` 복귀 대상 또는 LONG 표에서 읽은 값이다.
   - `3abda JMP (A0,D1.W)`: PC := A0 + sext(D1.W). A0는 `3aba4`가 스택에 넣었던 LONG을 `MOVEA.L (A7)+,A0`로 다시 읽은 값이다.
   - 대상이 routing 밖이면 `unsupported animation machine PC`, 홀수면 `unaligned animation machine PC`다(dispatcher가 판정).
6. **계산 표**(F1 결정 3: 상한 검사 없이 live bus로 읽는다. 자료 읽기라 범위를 넘으면 원본처럼 뒤의 바이트를 읽는다):
   - `3ab72`: `ANDI.W #ff,D0`, ×4, `MOVEA.L 3ab80(PC,D0.W),A0`. 이 block에 올 때 D0.B는 `0..7f`라(`3ab6c TST.B`/`BMI`) 읽는 주소는 `3ab80..3ad7c`다. 6 entry 밖은 뒤 자료·코드 바이트를 LONG으로 읽는다.
   - `3ab5a`: `ADD.W D1,D1`, `MOVE.W 3ab98(A1,D1.W),D2`(D1.B = BYTE `96` ∈ `0..fe`), `BTST.L D0,D2`. **bit 번호는 D0 & 31이고 D2는 LONG 전체다**(상위 WORD는 진입 때의 D2 값). 6 entry 밖은 뒤 바이트를 읽는다.
   - `3abc0`: `ANDI.W #f,D1`, `MOVE.B 3abde(PC,D1.W),D1`(16 entry, 정적으로 한정), ×4.
   - `3b4a0`/`3b4b4`: D1 ≤ `11`(`CMPI.B #11`/`BLS` clamp), BYTE 쌍 `3b4bc+2·D1`, `3b4bd+2·D1`(정적으로 한정).
   - `3afa2`: WORD `3af74+2·(D0 & ff)`, 이어서 LONG `(22(A6)) + sext(4·WORD)`. `3afcc`: WORD `3af6c + sext(2·WORD 88(c(A6)))`. `1d198`: `1d1b0 + sext(8·D0.W)`에서 LONG 2개.
7. **banked 읽기.** `3ae8a MOVE.L 20009c.l,22(A6)`, `1d1a4 MOVE.L (A1),22(A6)`(A1은 표의 LONG, 원본 값은 `2000xx`), `3afc2 MOVEA.L (A1,D7.W),A1`은 live bus 관례로 읽는다.
8. **정수 연산.** `3aed6 MULS.W 3a(A6),D0`(16×16 부호 곱, 32비트 결과), `ASR.L #8`, `3af1c SUBI.W #ff,D0`/`ASR.W #3`, `3ab5a BTST.L`, `3abaa SNE.B`, `3abc0 LSL.B #2`, `EXT.W`, `NEG.W`는 68000 폭 그대로 명시 구현한다. X·DIV는 없다.
9. **`3a5be`와의 관계.** `3a5be`(B2b)가 `ST.B 97(A6)`, BYTE `99` := BYTE `9a`, `JSR (A0)`(복귀 `3a5ca`)를 한다. 부상태 진입은 RTS(`3ab3c`)로 `3a5ca`에 돌아간다. 이 단위는 `3a5be`·`3a5ca`를 바꾸지 않는다.

## 공통 native 검증 계획

B1 계약 "공통 native 검증 계획"과 B2 계약의 자식·helper·간접 fixture 규칙을 따른다. V1 `tools/verify_animation_machine_unit_fixtures.py`에 새 spec `tools/unit_fixture_specs/b2c.py`를 둔다.

- **seed.** `U.seed_node_fixture(case, 2, node)`로 D1 seed 116/117(frame 2)의 자연 node 상태(N31 `38c36`, N33 `3b166`, N28 `2b99c`, N30a `331d8`, N29 `30de4`, N22 `3d32c`; A5·bank·RAM 자연)를 얻는다(D1 `declared_rebase()` + `R.prepared(case)` 경로). 그 위에 `U.with_host_writes`로 선언 편집을 더한다.
- **block 직접 진입.** 모든 block 시작을 직접 진입 fixture로 덮는다. D0-D7·A0-A4와 도달 block이 읽는 node field를 선언 편집하고 PC := block 시작, 복귀 LONG = sentinel이다. stop은 첫 범위 밖 PC다.
- **사슬(chain) fixture.**
  - `3a5be` 경유: A0 := 설치 값(27개 + `3a60a`)으로 `3a5be`에 진입한다. 부상태가 실행되고 RTS로 `3a5ca`에 돌아와 sentinel까지 간다(routed callee 전부 통과).
  - N33 `3a1e0`(A0 = LONG `82(A6)` 읽기 + `JSR 3a5be`)에서 `82(A6)` := 설치 값으로 진입한다.
  - `3a5d2`(N33) → `3a60a`: B2b `38d56` → `3b5a6` → N33 `3b22a` → `3a5d2` → … 으로 이어지는 사슬 fixture.
  - helper: `3b48c`는 복귀 LONG = 실제 소비 위치 `3ab34`, `1bf80`은 `3afa2`, `1d198`은 `3af94`로 둔다.
  - C 소비: `3aefc`·`3af5a`·`3b020`(`JSR 49fc6`, routed interpreter)에서 진입해 `3af12`·`3af60`·`3b026`의 native 분기와 C++ 분기를 비교한다.
- **분기·표 경계값.** BYTE `95` ∈ {`0..5`, `6`, `7f`, `80`, `fe`, `ff`}, BYTE `96` ∈ {`0..5`, `ff`}(mask bit 경계, `BTST.L` bit ≥ 16), BYTE `9a` ∈ `0..3`과 `3b446`의 D0 bit 0/1 조합 16개, BYTE `9f` ∈ {`10` `11` `12` `ff`}, BYTE `13` = `ff`(ADDQ 자리올림), BYTE `15` bit 0/7, BYTE `94` bit 0/4, `97` 부호, `a3` = 0/≠0, `9d` bit 4.
- **오류 fixture.** 내부 짝수 PC 전수(829) → `unsupported animation objects b2c PC`. 소비 block Unknown C(3) → `objects b2c caller requires known carry`. 범위 밖 이웃(`3ab80` `3abde` `3af6c` `3b03c` `3b4bc` `1bf94` `1d1b0` `3b62a` `3abee`) → `unsupported animation machine PC`. 홀수 PC. 간접 분기 대상이 routing 밖(work RAM `10fe00`)·홀수인 경우. 상태 보존 확인.
- **음성 검사.** C++ 입력 RAM 1 bit·레지스터 1 bit·queue 차이가 검출되는지 본다.
- **회귀.** D1 driver 400 frame(54,400/54,400), controller Execute (ii) 게임 모드, IRQ 모드 비교는 출력만 scratch로 옮겨 그대로 돌린다. 새 routing은 자연 경로에 없는 PC만 더하므로 바뀌지 않아야 한다([I]).

## `82(A6)` 부상태 사슬(170)

- **진입**([F]):
  - N33 `3a5d2`: `MOVE.L #3a60a,82(A6)`, BYTE `96` `95` := `ff`, `99` `9a` := 0, A1 = 0, `JSR 3b398`. 호출자는 N31 `38bd2` `38cac` `38d0a` `38de8` `38e40`, N32 `39086`, `39746` `39834` 등 15곳과 이 단위의 `3b5e4`다.
  - `3a5be`(B2b) `JSR (A0)`. 호출자는 `MOVEA.L 82(A6),A0; JSR 3a5be(PC)`이다(N31 `38cc6`, N33 `3a1e0` 등 17곳, 11곳 routing됨).
  - 사슬 안 `MOVE.L #imm,82(A6)` 27개: `3a60a`(`3aad6`) `3a622` `3a670` `3a69c` `3a6b8` `3a6d4` `3a6fc` `3a724` `3a740` `3a7b6` `3a7e2` `3a7fe` `3a81a` `3a842` `3a86a` `3a886` `3a8d2` `3a910` `3a9aa` `3a9d6` `3a9f2` `3aa08` `3aa2a` `3aa52` `3aa6e` `3ab00` `3ab24`.
- **의미**([F] 바이트, [I] 해석): partner 객체(116/117의 N31/N33 계열)의 애니메이션 부상태 기계다.
  - 각 상태 진입은 `MOVEA.L #script,A1; JSR 3b398`(N33: `a9` `aa` := 0, BYTE `94` bit 0 clear, A0 = A6+`8c`, D0 = `100`, `JMP 49f96` 스크립트 시작)로 스크립트를 고르고, BYTE `97`(2/3/4/0) 또는 `96`(0~5)을 쓰고, `82(A6)`에 다음 frame의 재진입 PC를 설치한다. 스크립트 표 13개: `3c88c` `3c8ca` `3c956` `3caee` `3cb2c` `3ca68` `3c9dc` `3cb6a` `3ccce` `3cbf0` `3c904` `3c990` `3cc3a` `3cc84` `3caa2` `3ca16`(자료, 실행 PC 아님).
  - `3ab3e`(요청 dispatcher): BYTE `95`(요청 상태, `ff` = 없음)가 `ff`면 `JMP (A0)`(복귀 대상). BYTE `96`(현재 상태)가 `ff`가 아니고 mask WORD `3ab98[96]`의 bit `95`가 서 있으면 요청을 막는다(D0 := `ff`). 아니면 LONG 표 `3ab80[95]`의 상태 진입으로 `JMP`한다.
  - `3aba4`(입력 dispatcher): A0(7 slot 표)를 스택에 넣고 `BSR 3b446`(B2b, partner 입력 D0). 입력 class D1 = bit 1이면 3, 아니면 bit 0이면 1, 아니면 0. BYTE `99` := class. slot = BYTE 표 `3abde[((9a << 2) | class) & f]`, `JMP (A0, 4·slot)`.
  - `3ab30`: `BSR 3b48c`(BYTE `9f`로 고른 위치 보정 D0/D1, BYTE `15` bit 0이면 D0 부호 반전), BYTE `a9` := D0, `aa` := D1, RTS(N33 `3b3b4`가 `42`/`46`에 더한다).
  - `3a744`/`3a88a`/`3a8d2`/`3a910`: BYTE `9d` bit 4면 `9d`/`9e` bit 4를 지우고 `3a936`(BYTE `a6` := 5, `a3` := 6, `a8` := 0, 세 번째 상태 무리)로 간다.
  - `3aa7a..3aae4`: BYTE `94` bit 0(스크립트 끝)이면 다시 `3a952`, bit 4·`97` 부호로 `97` 정리, `a3` = 0이면 `9d`/`9e` bit 6·4를 지우고 `95` := (`95` ≠ `ff`면 `95`, 아니면 `96`), `96` := `ff`, `82` := `3a60a`, `97` := 4.
- **표 3개와 slot**([F]): `3a63c`(`3a62e`), `3a782`(`3a774`), `3a960`(`3a952`) 각 7 slot `BRA.W`. LONG 표 `3ab80`: `3a62e 3a774 3a8ba 3a8f8 3aae8 3ab0c`. mask 표 `3ab98`: `0001 0002 0004 0008 007f 007f`. BYTE 표 `3abde`: `00 01 00 06 02 03 00 02 00 00 00 00 05 05 00 04`.
- **known C**: 생산·소비 없음(모든 flag는 block 안에서 소비).
- **경계(routing됨)**: N33 `3b398`, B2b `3b446`. 그 밖 callee 없음.

## `3b48c`(5)

- [F] `MOVEQ #0,D0; MOVEQ #0,D1; MOVE.B 9f(A6),D1; CMPI.B #11,D1; BLS.W 3b4a0` / `MOVE.B #11,D1`; `ADD.W D1,D1; MOVE.B 3b4bc(PC,D1.W),D0; EXT.W D0; BTST.B #0,15(A6); BEQ` / `NEG.W D0`; `MOVE.B 3b4bd(PC,D1.W),D1; EXT.W D1; RTS`.
- RTS의 C는 MOVE/EXT 뒤라 Clear지만 소비자가 없다(호출자 `3ab34` `3ac8a` `3b510`). 이 단위는 Unknown으로 둔다.
- 범위 밖 호출자 `3ac44` `3ac86`(`3abee`, B2c-b)와 `3b50c`(`3b4e0`, 미사용 후보)는 이 helper를 그대로 쓴다.

## `3b5a6`(5)

- [F] `JSR 3b22a`(N33), BYTE `14` := BYTE `1b`, LONG `64` `7e` := 0, WORD `8a` := 0, BYTE `9f` := `11`, `99` `9a` `ab` `b2` := 0, `JSR 3a5d2`(N33, 부상태 초기화), LONG `56` := `3b882`(자료), A0 := 0(`LEA 0.w`), `JSR 4b82e`(N03), BYTE `61` bit 7 clear, `5e` := 0, WORD `68` `1e` := `8811`, `9d` `9e` := 0, D0 = WORD `86`, D7.B := 1, `JSR 4d98a`(B2b), RTS.
- [I] partner 객체의 초기화 helper다(B2b `38d56` 설치 경로와 범위 밖 `38b8e`).
- RTS C: `4d98a`가 MOVE 뒤 Clear를 돌려주지만 소비자가 없다(`38d60`, `38b92` 모두 MOVE/MOVEA). Unknown으로 둔다.

## `3af86`(14, `28ae` 자식)

- [F] A0 = `c(A6)`(부모), D0 = 부모 WORD `88`, `JSR 1d198`(BYTE 22 LONG 설정). D0 = WORD `86`, `JSR 1bf80`(player 객체 `8cb8`/`8da8`의 BYTE `9f`). `3afa2`: 위 "계산 표" 경로로 A1을 고르고 A0 = A6+`26`, D0 = `100`, `JSR 49f8c`. `3afcc`: 소리 WORD `3af6c[부모 88]`, `JSR 8ebe`. `49290`(D0 = D1 = 0), `491c4`, 설치 `3affe`.
- `3affe`(재진입): D0 = ±5(BYTE `15` bit 0), D1 = `23`, WORD `2e` `32`, `JSR 43e34`, `JSR 49fc6` → `3b026 BCC`: Clear면 RTS(`3b03a`), Set이면 부모 BYTE `62` := `ff`, `JMP 2a00`.
- **known C**: 소비 `3b026`(`49fc6`).
- 경계: leaf `1d198` `1bf80`은 이 단위에 넣는다(결정 3). 나머지 callee는 routing됨.

## `3ae84`(20, `28ae` 자식)

- [F] WORD `20` := `f2`, LONG `22` := banked `20009c`, 소리 `208`(`8ebe`). 부모(`c(A6)`) BYTE `9f` < `11`이면 `3aeae`(스크립트 `3d0f2`, 설치 `3aec4`), 아니면 `3af2e`(WORD `36` `3a`를 `2e` `32`에 더함, 스크립트 `3d198`, 설치 `3af54`).
- `3aec4`(재진입): `JSR 43e34`. D0 = BYTE `13` + 1(BYTE 자리올림이면 `3aee4`로 건너뜀), `MULS.W 3a(A6),D0`, `ASR.L #8`, `SUB.W 3a(A6),D0`, WORD `46` -= D0. `3aee4`: D0/D1 = EXT BYTE `8e`/`8f`, BYTE `15` bit 0이면 `NEG.W D0`, D0 -= WORD `36`, D1 -= WORD `3a`, WORD `42` -= D0, `46` -= D1, `JSR 49fc6` → `3af12 BCC`: Set이면 `JMP 2a00`; Clear면 `3af1c`: D0 = (BYTE `13` − `ff`) `ASR.W #3`, BYTE `13` -= D0.B, RTS.
- `3af54`(재진입): `JSR 43e34`, `JSR 49fc6` → `3af60 BCC`: Set이면 `JMP 2a00`, Clear면 RTS.
- **known C**: 소비 `3af12` `3af60`(`49fc6`).

## `1bf80`(3)·`1d198`(1) leaf

- [F] `1bf80`: A0 = A5−`7348`(`8cb8`), D0.B ≠ 0이면 A5−`7258`(`8da8`), D0.B := BYTE `9f(A0)`, RTS.
- [F] `1d198`: D0.W ×8, A0 = `1d1b0` + sext(D0.W), A1 = LONG `(A0)+`, LONG `22(A6)` := LONG `(A1)`(banked), D0 := LONG `(A0)`, WORD `20(A6)` := D0.W, RTS.
- RTS C는 소비자가 없다(MOVE 뒤 Clear). Unknown으로 둔다.
- [F] 두 helper는 player 영역(`2d9xx` `314xx` `366xx`)도 부른다. 병렬 단위 B2d(`39366` `2d57a` `2d3ae`)의 정적 closure는 이 둘을 부르지 않는다(겹침 0).

## B2c-b(이 계약 밖, 다음 단위 후보) = 55

| 항목 | block | routing 범위 | 진입 |
| --- | --- | --- | --- |
| `3abee` | 19 | `3abee..3acd6` | 애니메이션 스크립트 callback 표 `4a500`의 index `23`(LONG `4a58c`). interpreter `4a352`/`4a43c` `JSR (A1)` live target |
| `3b458` + `44602` | 2 + 6 | `3b458..3b48c` `44602..4464a` | 표 index `25`(LONG `4a594`); `44602`는 공용 leaf(호출 44곳) |
| `3b62a` `3b648` `3b656` | 4 + 1 + 5 | `3b62a..3b68a` | 표 index `27` `26` `24` |
| `4db18` | 18 | `4db18..4db42` `4dbdc..4dc66` | N28 `2c826`, N29b `30c36`, N30a `33796`, B2b `3a1b2`, 범위 밖 `3da60`. `28ae` 자식 `4dbdc`에 `JSR (A1)`(LONG `7a`, live) |

- [F] `3abec..3acd6`(B2 "범위 밖 사슬" 마지막 줄): `3abde..3abee`는 `3aba4`의 BYTE 표(16바이트)이고, 코드는 `3abee`에서 시작한다. `3abee`는 `82(A6)` 사슬의 closure에 들지 않는다. 진입은 스크립트 callback 표뿐이다. 그래서 같은 partner 영역의 스크립트 callback 무리(B2c-b)로 둔다. `3b48c`를 함께 쓴다.
- [F] **`3b4e0`(8 block: `3b4e0 3b500 3b508 3b510 3b51a 3b530 3b536 3b538`)는 정적 참조가 없다.** 8 MiB LONG `0003b4e0` 0건, ±32 KiB PC 상대 분기·호출 0건, `4a500` 표에도 없다. [I] 미사용 후보다. routing하지 않는다(B2 결정 3 `4c3ba` 관례).
- [F] `4b6f4`: 이 영역의 helper가 아니다(호출은 B2a `5ef66` `5f5e0` `5f73e`와 `51ce4`~`ef974` 20곳). routing하면 pin된 `tools/verify_animation_machine_area_clear.py` 883행 기대를 바꿔야 한다(B2 결정 4). 이 단위에 넣지 않는다.

## 영향받는 기존 시험·검증기

[F] 새 routing 대상 PC를 "미연결" 기대로 쓰는 곳:

- `engine/tests/animation_machine_objects_b2b_test.cpp`
  - 560행 `3a5be` A0 = `3a60a` → `unsupported animation machine PC` 기대. → A0 = `10fe00`(work RAM 탐침)으로 바꾼다.
  - 589행 `38d56`을 stop 없이 실행해 `3b5a6`에서 오류 기대. → stop만 확인하는 588행은 그대로 두고, 589행은 work RAM 탐침 `10fe02`의 rollback 확인으로 바꾼다.
  - 620행 미연결 목록의 `3b5a6`. → `10fe04`로 바꾼다.
- `tools/unit_fixture_specs/b2b.py`: `UNROUTED_NEIGHBOURS`의 `3b5a6`, `error-3a5be-unrouted-3a60a`, `error-boundary-3b5a6`. → 각각 work RAM 탐침(`10fe04`, A0 = `10fe00`, `3a5be` A0 = `10fe02`)으로 바꾼다. 문서 문자열도 같이 고친다.
- stop만 확인하는 곳(그대로 통과): b2b 시험 95행(`38d56` → `3b5a6` stop), 588행.
- 데이터 값으로만 나오는 곳(무관): `motion_walk` 279행 `3b5c6`, `b1c` 423행 `3af3a`, `n04` 86행 `3ab48`, `u20` `3a6fb`, `n33` 671행 범위 끝 `3a60a`(배타 끝).

## 결정 필요 (MAIN DECISION NEEDED)

1. **B2c 분할.** 후보 269 block을 B2c(= B2c-a, 218: `82(A6)` 사슬 + `3b48c` + `3b5a6` + `3af86` + `3ae84` + leaf `1bf80` `1d198`)와 B2c-b(55: 스크립트 callback `3abee` `3b458` `3b62a` `3b648` `3b656` + `44602` + `4db18`)로 나눈다. 이 작업자는 B2c-a만 구현한다.
2. **`3b4e0` 미사용 후보.** routing하지 않고 [I] 미사용으로 기록하는 안을 권고한다(`4c3ba` 관례).
3. **player 영역 leaf `1bf80` `1d198`.** `3af86`이 첫 block에서 부르는 4 block leaf다. 넣으면 `3af86`을 끝까지 실행할 수 있다. 다른 호출자(player 영역)의 미래 단위와 겹치지 않도록 이 단위가 routing한다. 대안은 경계(stop만)로 두는 것이다.
4. **B2 계약 수 정정.** `82(A6)` 사슬 75 → 175(같은 진입, 설치·복귀 대상·slot을 block 시작으로 센 수).
5. **`4b6f4`·`44602`·`4db18`.** `44602`·`4db18`은 B2c-b로, `4b6f4`는 B2 결정 4 그대로(이 단위 밖) 둔다.

## 미확인

- [U] 스크립트 표(`3c88c` 등)의 내용과 각 부상태의 화면상 동작 이름.
- [U] `95` 요청을 쓰는 곳(범위 밖 사슬 `39366`·N32·N33 `3b2xx`)과 실제 상태 전이 순서.
- [U] 400 frame 밖·응답 `00`·controller 생략 해제 시의 자연 도달.
- [U] LONG 표 `3ab80` index 6 이상(BYTE `95` ∈ `6..7f`)이 실제로 생기는지. 생기면 원본은 뒤 바이트를 주소로 읽어 jump한다(이 계약은 그대로 옮긴다).

## block 목록

[F] scratch `starts_a.txt`(SHA256 `72238f6a87716944fb30a7aef485f3a70d46839e3526fd29c258cea9ebd3fea4`)와 같다.

- **`82(A6)` 사슬(170)**: `3a60a 3a614 3a622 3a62a 3a62e 3a63c 3a640 3a644 3a648 3a64c 3a650 3a654 3a658 3a662 3a670 3a674 3a67a 3a680 3a684 3a68e 3a69c 3a6a0 3a6aa 3a6b8 3a6bc 3a6c6 3a6d4 3a6d8 3a6e0 3a6e4 3a6ee 3a6fc 3a700 3a708 3a70c 3a716 3a724 3a728 3a732 3a740 3a744 3a74e 3a75e 3a766 3a770 3a774 3a782 3a786 3a78a 3a78e 3a792 3a796 3a79a 3a79e 3a7a8 3a7b6 3a7ba 3a7c0 3a7c6 3a7ca 3a7d4 3a7e2 3a7e6 3a7f0 3a7fe 3a802 3a80c 3a81a 3a81e 3a826 3a82a 3a834 3a842 3a846 3a84e 3a852 3a85c 3a86a 3a86e 3a878 3a886 3a88a 3a894 3a8a4 3a8ac 3a8b6 3a8ba 3a8c4 3a8d2 3a8dc 3a8ec 3a8f4 3a8f8 3a902 3a910 3a91a 3a92a 3a932 3a936 3a952 3a960 3a964 3a968 3a96c 3a970 3a974 3a978 3a97c 3a986 3a990 3a994 3a99e 3a9a2 3a9aa 3a9ae 3a9b4 3a9ba 3a9be 3a9c8 3a9d6 3a9da 3a9e4 3a9f2 3a9f6 3aa00 3aa08 3aa0c 3aa14 3aa18 3aa22 3aa2a 3aa2e 3aa36 3aa3a 3aa44 3aa52 3aa56 3aa60 3aa6e 3aa72 3aa7a 3aa84 3aa8e 3aa96 3aa9c 3aaa4 3aac8 3aacc 3aae4 3aae8 3aaf2 3ab00 3ab08 3ab0c 3ab16 3ab24 3ab2c 3ab30 3ab34 3ab3e 3ab4c 3ab5a 3ab6a 3ab6c 3ab72 3ab7e 3aba4 3abaa 3abbc 3abc0`
- **`3b48c`(5)**: `3b48c 3b49c 3b4a0 3b4b2 3b4b4`
- **`3b5a6`(5)**: `3b5a6 3b5aa 3b5e8 3b5fa 3b628`
- **`3af86`(14)**: `3af86 3af94 3afa2 3afcc 3afe8 3aff2 3aff8 3affe 3b010 3b012 3b020 3b026 3b02a 3b03a`
- **`3ae84`(20)**: `3ae84 3aea0 3aeae 3aebe 3aec4 3aeca 3aed6 3aee4 3aefa 3aefc 3af12 3af16 3af1c 3af2e 3af4e 3af54 3af5a 3af60 3af64 3af6a`
- **leaf(4)**: `1bf80 1bf8a 1bf8e 1d198`
- **B2c-b(55, 참고)**: `3abee 3abf6 3ac00 3ac12 3ac1a 3ac1c 3ac2c 3ac44 3ac48 3ac56 3ac58 3ac76 3ac7c 3ac8a 3ac98 3aca0 3acb2 3acc6 3acd4` / `3b458 3b46c 44602 4461c 44620 44626 4462a 4463c` / `3b62a 3b638 3b63a 3b642 3b648 3b656 3b666 3b66a 3b678 3b67c` / `4db18 4db34 4dbdc 4dbfa 4dc08 4dc22 4dc28 4dc2e 4dc34 4dc38 4dc40 4dc46 4dc4a 4dc50 4dc54 4dc58 4dc5e 4dc60`

## 구현·검증 기록(작업자, 메인 리뷰 전)

- 실행부 `engine/src/animation_machine_objects_b2c.cpp`(case 218 = block 시작 218). routing `else if` 1개, carry 보존 목록에 `3af12 3af60 3b026`, 선언 1줄, Makefile(SOURCES·시험 target·실행 줄), `tools/verify_animation_machine.py` SOURCES.
- 단위 시험 `engine/tests/animation_machine_objects_b2c_test.cpp`(run_animation_machine만 사용): 생성 행 360개(`tools/generate_animation_machine_objects_b2c_test_table.py`, native Unicorn + 합성 표 바이트, 재생성 결과 바이트 동일), 비소비 block × C 3종, 소비 block × C 2종, zero-step 218 × 3, 내부 짝수 PC 829개 정확한 오류, 범위 양끝 홀수 PC, work RAM `10fe00..10fefe` rollback 탐침, 간접 분기 RAM·홀수 대상, 저장 뒤 실패 rollback, 소비 block Unknown C.
- V1 `tools/unit_fixture_specs/b2c.py`: 1,707 fixture 전부 통과(match 835, error 862, mismatch 10). 두 번 실행한 행 digest 동일. carry oracle 통과. 218 시작 모두 실행, 자연 seed 상태에서 출발한 `28ae` 자식(spawn, 부모 PC 선언) fixture 24개가 31 시작을 덮는다.
- 실제 ROM에서 확인한 사실: BYTE `95` = 6이면 `3ab72`가 mask 표를 LONG `00010002`로 읽어 F6c 내부 PC로 간다(C++: 그 단위의 checked 오류, fixture `error-3ab72-index-6`).
- 회귀(scratch 출력): D1 54,400/54,400, controller Execute (ii) 54,400/54,400, IRQ 54,400/54,400(IRQ 108,528회), B2b V1 1,419/1,419. 결정 필요 항목은 위 "결정 필요"와 같다.
