# 고아 설치 사슬·공용 helper·`4d418` 반환 C 구현 계약 B2

**구현 전 계약 초안 — 메인 결정 전.** 구현·검증 기록이 아니다. 아래 수치와 목록은 읽기 전용 분석 작업자(Claude Opus 5.5)가 정적 디코드로 만든 것이다. 메인 결정 전에는 routing·실행부·시험을 바꾸지 않는다.

## 기준 입력

- [F] ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(고정 영역, CPU 주소 = 파일 오프셋). 저장소 HEAD `c49bcd2`. `engine/src/animation_machine.cpp` SHA256 `c7318132fcdfd288c12a58ab7e51c03e2920b46d7e939103bd917d72ca8caad2`(dispatch 규칙 98개).
- 디코드 규칙·보정·scratch 위치·표기는 B1 계약(`animation-machine-deferred-b1-contract.md`) "기준 입력"과 같다. 디코더는 N16b·U19b·N19b·N30b 계약 목록을 재현한다.
- [F] **참조 탐색**(scratch `refs.py`): 두 가지를 찾았다.
  - LONG 참조: 8 MiB 이미지 전체에서 대상 주소의 4바이트 BE 값을 찾고, 앞 명령을 디코드한다(`MOVE.L #imm,(A6)` 설치, `MOVEA.L #imm,A0` + `JSR 28ae` 자식, `JSR/JMP abs.L`).
  - PC 상대 참조: 대상 ±`8000`바이트의 모든 짝수 주소에서 PC 상대 분기·`JSR (PC)`·`LEA (PC)`를 디코드했다.
  - 참조 위치가 routing된 PC인지도 표시했다.

## 요약

- [F] **현재 routing과의 관계**: 목록의 고아 사슬 11개와 `4d418..4d508`의 모든 block 시작·내부 짝수 PC는 현재 routing 밖이다(겹침 0). 후속 단위가 routing한 것은 없다.
  - 사슬 경계 바로 옆은 이미 routing돼 있다: `3a1e0`(N33), `3a5d2`(N33), `3a24c`(N33), `33958`(N30a).
  - 따라서 STATUS의 범위 표기(`39f9c..3a1e0` 등)는 끝이 정확하다.
- [F] **block 수**(정적, routing·다른 항목에서 멈춤):

| 항목 | block | 짝수 PC | routing 범위 | 진입을 만드는 곳(참조) |
| --- | --- | --- | --- | --- |
| `5eed2` | 28 | 138 | `5eed2..5efe6` | N25 `5ee20` `5ee4e` `28ae` 자식 |
| `5f504` | 53 | 302 | `5f504..5f760` | N26 `5f3b4` `5f3da` `5f404` `5f42a` `28ae` 자식 |
| `60516` | 100 | 530 | `60516..6093a` | N27 `6018e` `601b8` `28ae` 자식 |
| `3383c` | 15 | 106 | `3383c..338f8` `33940..33958` | N30a `33832` 설치 |
| `3a4a4` | 29 | 149 | `3a4a4..3a4d6` `3a4da..3a5d2` | JSR: N31 `38c5a` `3a380`, N33 `3a212`(`3a4a4`), N32b·N33(`3a4be`), N32·N32b(`3a4da`), N31·N32·N32b·N33 17곳(`3a5be`) |
| `3b424` | 6 | 26 | `3b424..3b458` | JSR: N32 14곳, N32b 2곳, N33 `3a1fe`(`3b424`); 범위 밖 `3a670..3aba6` 10곳(`3b446`) |
| `4bfc0` | 10 | 48 | `4bfc0..4c020` | JMP: N30a `33c34`, N33 `3b292`; JSR: player 계열 `1dc74`~`21490` 24곳, `409aa`(routing 밖) |
| `38d56` | 18 | 63 | `38d56..38dd4` | N31 `38c80` 설치 |
| `39f9c` | 54 | 216 | `39f9c..3a048` `3a0dc..3a1e0` | N32b `39ea8` 설치·표 slot `39e7e` `39e82`; `3a0dc`는 N31 `3a412` 설치 |
| `3acd6` | 12 | 57 | `3acd6..3ad48` | N32b `39d8e` `28ae` 자식 |
| `4c390` | 6(+2) | 39 | `4c390..4c3ba` `4c3cc..4c3de`(+`4c3ba..4c3cc`) | N28 `2c79a JSR 4c3a2`; 범위 밖 N28 계열 `2c1f2` `2c2c2` `2c516` `2c754`(`4c390`), `2c728`(`4c3cc`); `4c3ba` 참조 없음 |
| `4d418` | 21 | 120 | `4d418..4d508` | `4d418`: JSR N29a `319fe`·N30a `3320c` `337d4`, JMP `3a4b8`(위)·`3dcd4`(N22b) 등 10곳. `4d4b4`: JSR N28 `2c894` `2ca8a`, N32 `38e62`, JMP N29a `31a24` 등 17곳 |
| 합계 | **352**(`4c3ba` 2 포함 354) | | | |

- [F] **도달성**: `4c3ba` 하나를 빼고 모든 진입이 정적 코드 참조를 가진다. 대부분 참조 위치가 이미 routing된 코드다.
  - 즉 "실행 가능한 기능"이고, 자연 400 frame에서 어느 seed도 실행하지 않았을 뿐이다(각 단위 계약의 자연 도달 기록).
  - `4c390`/`4c3cc`는 routing 밖 N28 계열 상태기계(`2bf1e..2c6f4` 설치 사슬, N28 계약의 범위 밖 설치 `2ba50`)에서만 부른다([I] 도달 가능, 사슬은 이 계약 밖).
  - `3b446`은 routing 밖 `82(A6)` 부상태 사슬(아래 "새로 확인한 범위 밖 사슬")에서만 부른다.
- [F] **`4c3ba`(2 block: `4c3ba` `4c3c2`)는 정적 참조가 없다.** 8 MiB 전체 LONG 값 `0004c3ba`가 0건이고, ±32 KiB PC 상대 분기·호출도 0건이다. 모양은 같은 꼴의 진입 조각 넷(`4c390` `4c3a2` `4c3ba` `4c3cc`: `MOVE.L A0,5c8e(A5)`, `JSR 4bce0`/`4bc44`, BYTE `5cb4` := 0/`ff`, `BRA 4c810`) 중 하나다. [I] 미사용 진입 조각이다. 결정 3에서 다룬다.
- [F] **`4d418` 반환 C(STATUS "미확인")를 정적으로 정했다.** 아래 B2b `4d418` 절을 본다. `4d418`은 두 RTS 모두 known C이고, `4d4b4`는 한 경로만 CMP 계산 C다.
- [F] B2 목록 합 352는 ~220을 넘는다. 그래서 **B2를 두 단위로 나눈다**(결정 1):
  - **B2a** = `5eed2` + `5f504` + `60516` = 181. 작은 leaf helper `44602`(6)·`4b6f4`(3)를 넣으면 **190**이다.
  - **B2b** = 나머지 9 항목 171(`4c3ba` 제외). B1·기존 N28~N33이 함께 쓰는 C 생산 leaf helper 38을 넣으면 **209**다.

## 공통 규칙·native 검증 계획

B1 계약의 "공통 규칙"(실행부·이름, routing, 경계, known C, 표, banked 읽기, `2986`, interpreter)과 "공통 native 검증 계획"(V1 `tools/verify_animation_machine_unit_fixtures.py`, `U.natural_cases()` = D1 `declared_rebase()` + `R.prepared(case)`, `U.seed_node_fixture` + `U.with_host_writes`, block 직접 진입·오류·표·음성·회귀)을 그대로 따른다. 다른 점만 적는다.

- **자식(`28ae`) 진입 fixture.**
  - 부모 node에서 자식 생성 분기 조건을 선언 편집한다. routing된 `28ae`가 실제로 자식 node를 할당하게 하고, `U.advance_native`로 다음 pass의 그 자식 node 진입까지 진행한다(chain fixture).
  - 직접 진입은 빈 node slot에 `(A6)` := 자식 진입, 부모 포인터 `c(A6)` 등 `28ae`가 쓰는 field를 선언한다(`28ae` 실행부의 기록 field와 같게).
- **helper 진입 fixture.** 복귀 LONG을 실제 ROM 소비자 주소로 둔다. 그래서 native 분기가 C·D0를 확인한다(N19·N22·N29 "RTS 앞 생산" 선례).
- **간접 `JSR (A0)`**(`3a5c8`): 원본에 거르기가 없으므로 interpreter `JSR (A1)`처럼 live target으로 옮긴다(F4 결정: 허용 목록 없음). 대상은 routing된 PC(예: N33 `3a5d2`)와 routing 밖 PC(`3a60a` → `unsupported animation machine PC`) 둘 다 fixture로 둔다.
- **I/O port**: helper `4eea2`의 BSR `4f08a`가 `MOVE.L D0,3c0000`을 7회 한다(`4f094` `4f0a8`×5 `4f0bc`). 기존 card_menu 실행부 관례대로 LONG 쓰기 하나를 `VideoPortWrite`(address `3c0000`, size 4) 하나로 기록한다. V1은 ordered ports를 비교한다.

## B2a = `5eed2`(28) + `5f504`(53) + `60516`(100) [+ `44602` 6, `4b6f4` 3] = 190

세 항목 모두 seed 32 33 객체 계열(N24~N27)의 `28ae` 자식 callback이다. N25/N26/N27 계약은 이들을 "자료로만 넘김"으로 두었다.

### `5eed2`(N25 자식)

- **진입**: N25 `5ee1c BCC`(`49fc6` C) 뒤 `5ee20`, 그리고 `5ee4e`. 둘 다 `MOVEA.L #5eed2,A0; MOVE.W #a,D0; JSR 28ae`이며 자식 2개를 만든다.
- **의미**([I]): 파편·발사체 자식이다.
  - 난수 `443d2`, 소리 `8ebe` 3회, 애니메이션 `49f8c`(bank `200194` 읽기 `5ef1e` `5ef96`).
  - 설치 `5ef42` `5ef8c` `5efba`.
  - `1ab02` 화면 판정(C 소비 `5ef80` `5efda`), `4b6f4` C(소비 `5ef6c`), `4ae4a`.
  - 화면 밖이면 `JMP 2a00`(`5ef8a` `5efe4`, 삭제).
- **known C**: 생산 없음. 소비 `5ef6c`(`4b6f4`), `5ef80` `5efda`(`1ab02`), `5efc6`(`49fc6`).
- **경계**: `4b6f4`(결정 4).

### `5f504`(N26 자식)

- **진입**: N26 `5f3b0 BNE`(BYTE `78`) 뒤 `5f3b4`와 `5f3da` `5f404` `5f42a`(4곳).
- **의미**([I]): 발사체 자식이다.
  - 난수 `49a58`, `4b702`, 소리 `8ebe`, 애니메이션 `49f8c`(bank `200090`).
  - 설치 `5f57c` `5f5f2` `5f66a`, 정리 `8ff4`, `4b54e`, `4ae4a`.
  - `28ae` 자식 `d22e6`(N05), `4970a` 뒤 `ORI.B #1,CCR`(`5f714`), `JMP 2a00`.
  - 자료 포인터 즉값 `5f4e6`(LONG `56`; N26 계약의 84바이트 자료)과 `90000`(d(A6))은 실행 PC가 아니다.
- **known C**: 소비 `5f5e6` `5f744`(`4b6f4`), `5f6c2`(`4b54e`), `5f702`(`28ae`).
- **경계**: `4b6f4`.

### `60516`(N27 자식)

- **진입**: N27 `6018a BNE`(`ANDI.W #1,D0` 난수) 앞뒤 `6018e` `601b8`.
- **의미**([F]/[I]):
  - 초기화: 난수 `49a58` → BYTE `8e`, LONG `90` = `30000`, `490ba`(표 `60c54`), `4b702`, 소리 `d64`/`d59`(BYTE `8f`), 애니메이션 bank `200194`, 설치 `605ae`.
  - `605ae`: 부모(`c(A6)`) BYTE `77`의 값 1/2/그 밖에 따라 갈린다.
    - 1: 흔들림 BYTE `8e`, LONG `90` 가속.
    - 2: 타이머 `7e`와 `28ae` 자식 `d1cd8`(N05) 5곳 + `4970a` 뒤 `ORI` Set 7곳.
    - 그 밖: `2986` 자식 `b3dbc` 2곳(`60812` `608b6`), `49214`, `4b54e`, `4ae4a`, helper `44602`.
- **known C**: 생산 `ORI` 7곳(`60640` `60706` `60790` `6084a` `60870` `608ee` `60914`, 모두 뒤에 `4970a`). 소비 `6062e` `606f4` `6077e` `6085e` `60902`(`28ae`), `60880`(`4b54e`).
- **경계**: `44602`(선택 leaf), `2986` 자식 값 `b3dbc`(31 block, B1 결정 5).

### 선택 leaf helper

- `44602`(6): `4461c` `44620` `44626` `4462a` `4463c`. RTS 앞 `ADD.B`(계산 C, 소비처는 [U]).
- `4b6f4`(3): `TST.B 5b86(A5); BEQ 4b700; ORI.B #1,CCR; RTS` → BYTE ≠ 0이면 Set, 0이면 Clear. 시작 `4b6f4 4b6fc 4b700`.
  - 주의: `tools/verify_animation_machine_area_clear.py` 883행이 `unrouted_neighbour_04b6f4`를 `unsupported animation machine PC`로 기대한다(F1b 범위 `4b6e4..4b6f4`의 이웃). routing하면 이 pin된 검증기의 `SUPERSEDED_NEIGHBOUR_ERRORS`를 고쳐야 한다(결정 4).

### seed·fixture

- 자연 부모 seed 32 33. N25 `5e940`(81회), N26 `5f2c4`(162회), N27 `5fd9a`(162회)·`60086`(81회) node가 있다. 자식 생성 분기는 자연 400 frame에서 실행되지 않는다.
- 부모 node에서 다음을 선언 편집해 `28ae` 자식 생성 경로를 연다.
  - `5ee1c`: `49fc6` C가 Clear가 되게 interpreter 상태를 둔다.
  - `5f3b0`: BYTE `78` := 0.
  - `6018a`: 난수 결과 대신 `D0` 편집은 불가(난수 호출 뒤 같은 block)이므로 RNG 상태 RAM을 편집한다([I]).
- 각 자식은 직접 진입 fixture로도 덮는다.
- `60516`의 부모 BYTE `77` = 0/1/2/3 네 갈래를 덮는다.

## B2b = 171 + C 생산 leaf helper 38 = 209

### `4d418..4d508`(21) — `4d418` 반환 C

- [F] **`4d418`**(진입 D0.B = 선택(0 → 표 `5cba(A5)`/`8cb8(A5)`, ≠0 → `5ce6(A5)`/`8da8(A5)`), D2/D3 = 오프셋, A6 = 객체):
  - `JSR 289e`(readiness, 대상 객체 A0 가능 여부)의 C를 `4d438 BCC`가 소비한다.
  - 다음 중 하나면 `4d4ac` Clear로 간다: 대상 BYTE `61` bit 7 set, slot WORD `(A4)`가 0도 자신(A6 하위 WORD)도 아님, BYTE `22(A4)` ≠ 0.
  - 아니면 slot을 채운다. `2(A4)` = D2, `4(A4)` = D3, LONG `c/10/14` = A6의 `3e/2e/32`, `(A4)` = A6, BYTE `22` = `ff`, WORD `18` = `-7ff2(A5)`, BYTE `24` = BYTE `5e`(≠0일 때), BYTE `60(A6)` = 대상 `60`, BYTE `23` = 1, BYTE `28` = BYTE `15`, D0 = 대상 WORD `76`.
  - **RTS C**:
    - `4d4a6 ORI.B #1,CCR; RTS` → **Set**. 앞 `MOVE.W 76(A0),D0`이 C를 지운 뒤 ORI가 세운다.
    - `4d4ac ANDI.B #fe,CCR; MOVEQ #0,D0; RTS` → **Clear**, D0 = 0.
  - 소비자([F]):
    - 직접: N29a `31a04 BCC`, N30a `33212 BCC`, N30b `33a08 BCS`, 범위 밖 `330c0` `37dc8` `40b6e`. N30a `337da`는 `BRA`라 소비하지 않는다.
    - 꼬리 JMP 경유: `3a4a4` → N31 `38c5e BCC`·`3a384 BCS`, 범위 밖 `38b4e`; `3dcac`(N22b) → N22a `3d358 BCC`·N22b `3dbca BCS`; `2b5xx` 계열 `2b662 JMP` → [U].
- [F] **`4d4b4`**(D0.B = 선택, D1 = 값, A6 = 객체):
  - `MOVE.B 15(A6),D2`, `MOVEM.L D0-D1`, `JSR 4eea2`(D0 = 선택; RAM `1009a8`/`100a6c` 블록의 WORD 6개를 지우고 `4f08a`로 `3c0000`에 LONG 7개를 쓴다).
  - 그 뒤 slot `(A4)`가 자신이면 `(A4)` = 0, BYTE `22` = 2, `23` = D1, `28` = D2, `24` = BYTE `5e`(≠0)이다.
  - **RTS C**(`4d506`):
    - `4d4e4 BNE` 경로는 `CMP.W (A4),D7`의 borrow(계산 C).
    - `4d4fe BEQ` 경로와 fall-through 경로는 Clear(`MOVE`).
  - [I] 확인한 호출자 중 이 C를 소비하는 곳은 없다(`2c89a BSR`, `2ca90 MOVEQ`, `38e68 MOVE.L`, `3d508 MOVE.L`, `33940`/`3a4be`/`3dcda`의 꼬리). 그래도 계산 C를 그대로 구현할 것을 권고한다(결정 5).
- **경계**: `4eea2`(leaf, 아래). `289e`는 readiness 실행부다.
- **fixture**:
  - 116/117 객체 node(N30a `331d8`, N29a `31a12`/`319f6` 계열)에서 `JSR 4d418` 직전 상태로 진입한다. slot 표 `5cba`/`5ce6`, 대상 `8cb8`/`8da8`의 BYTE `61`·`22`·WORD `(A4)`를 선언 편집해 Set/Clear 각 경로를 낸다.
  - 복귀 LONG은 실제 소비자(`31a04` `33212` `33a08` `38c5e` `3a384` `3d358` `3dbca`)로 둔다.

### `3383c`(15, N30a 설치)

- [F] `LEA 349ee(PC),A0` → `4ae4a`, helper `33940`(BYTE push, `4d8d8`, D0 ≥ 0이면 `JMP 4d4b4`, 아니면 RTS Clear), `4ff96`, `d3d7c` 4회(파편 4개의 속도 LONG `36`/`3a`·WORD `54`), `2986` 자식 `338f8`(A1 = `100bf4`), `49214`, 소리 `18de`, `JMP 2a00`.
- [I] N30 객체의 파괴 처리다. N29b `30cb8`과 같은 꼴이다.
- 경계: `2986` 자식 값 `338f8`(B1 결정 5).
- fixture: 116/117 N30 node에서 `(A6)` := `3383c`. `33940`은 복귀 LONG = `3384e`·N30a `337c8` 다음으로 둔다.

### `3a4a4` 계열(29: `3a4a4` `3a4be` `3a4da` `3a5be`)

- [F] `3a4a4`: D0 = WORD `86`, D2 = ±2(BYTE `15` bit 0), D3 = `1e`, `JMP 4d418`(C는 `4d418`의 것).
- [F] `3a4be`: `33940`과 같은 꼴(`4d8d8`, `JMP 4d4b4` 또는 RTS Clear).
- [F] `3a4da`: BYTE `b2` ≠ 0이면 Clear 반환이다. 아니면 다음과 같다.
  - `4d6b4`(C 소비 `3a4ec BCC`), BYTE `9f` < `11`에 따라 오프셋 쌍 `3a4d6`/`3a4d8`(자료 2바이트×2, routing 밖)를 고른다.
  - BYTE `b2` := `18`, `28ae` 자식 `3ae84`(범위 밖 사슬), `49214`, `491b6`, 자식 위치·`1e` 설정.
  - BYTE `ae` = 5이면 `28ae` 자식 `2d57a`, 아니면 `2d3ae`(둘 다 범위 밖 사슬). WORD `76`, `4c2fa`.
  - `3a5b2 ORI` → **Set** RTS / `3a5b8 ANDI` → **Clear** RTS.
  - 소비: N32 `39128` `396ca`, N32b `39c30` 이후(`MOVEM.L (A7)+,D0`는 C를 바꾸지 않음).
- [F] `3a5be`: `ST.B 97(A6)`, BYTE `99` := BYTE `9a`, **`JSR (A0)`**(`3a5c8`, live target), BYTE `9a` := BYTE `99`, RTS(MOVE 뒤라 C = 0).
  - 호출자는 A0 = LONG `82(A6)`(부상태 포인터)를 넘긴다. N33 `3a5d2`가 `82(A6)` := `3a60a`를 설정한다.
  - 그 대상 사슬 `3a60a..3abde`는 routing 밖이다(아래 "새로 확인한 범위 밖 사슬").
- 경계: `4c2fa`·`4d6b4`(leaf, 아래). 자식 값 `3ae84`(20 block), `2d57a`(62), `2d3ae`(41)는 범위 밖 사슬이다.
- fixture:
  - 116/117 N31 `38c36` node 상태에서 `38c5a` 직전으로 진입한다(BYTE `15`, `86` 편집).
  - `3a4da`의 BYTE `b2`/`9f`/`ae` 조합.
  - `3a5be`는 A0 = `3a5d2`(N33, routing됨)와 `3a60a`(routing 밖 → checked 오류)로 둔다.

### `3b424`(6: `3b424` `3b446`)

- [F] `3b424`: D0 = WORD `86`, `JSR 49be0`(A0 = 입력 LONG 포인터). D0 = 입력 LONG 상위·하위 WORD AND, `AND.B 9e(A6)`, `OR.B D0,9d(A6)`, RTS(C = 0).
- [F] `3b446`: `BSR 3b424`. BYTE `15` bit 7 set이면 `ANDI.W #fdfd,D0`. RTS(C = 0, `BTST`는 C를 바꾸지 않음).
- [I] 상대 객체(partner) 입력 bit를 D0로 돌려주는 helper다. 호출자는 D0 bit를 `BTST`한다(N32 `3902c`, N33 `3a202`).
- fixture: 116/117 N31/N33 node에서 `49be0` 입력 RAM을 선언 편집하고, 복귀 LONG = `3902c`/`3a202`로 둔다.

### `4bfc0`(10)

- [F] `BSR 4bce0`(N33), `BSR 4c020`(U17), `JSR 4b8e8`(N33 진입), `ADD.B D7,D7; BCC 4bf0a`(U08b; ADD의 C를 같은 block에서 소비하므로 묶음).
- [F] 이어서 `JSR 469d8`(U09)를 하고, 위치 D2/D3를 LONG `36`/`3a`에서 `3e(A6)`·A0의 `14/18/1c/20` 보정으로 계산한다. `MOVEM.L D0-D3/A0,2e(A6)` 뒤 `BRA 4bf16`(U08b)이다.
- [I] `4bfb4`(N33)의 쌍 진입이다. player 계열(`1dc74`~`21490`, 24곳 JSR)이 많이 부르므로 player 단위(원 범위 결정 8의 `1d1f4`)의 선행 helper다.
- fixture: 116/117 N33 `4bfb4` 관련 node에서 `(A6)` 대신 PC := `4bfc0`, 복귀 LONG = N30a `33c3a`/N33 `3b298`.

### `38d56`(18, N31 설치)

- [F] BYTE `b5` := `ff`, `JSR 3b5a6`(범위 밖 9 block, `4d98a` 호출), `28ae` 자식 `3af86`(범위 밖 18 block), `SCC.B 62(A6)`(`28ae` C 소비), `4972c`, 설치 `38d80`.
- [F] BYTE `62`에 따라 갈린다.
  - 0이면: N33 `3b288` `3b334` `3b2ee`, `BRA 3a350`(N31).
  - 아니면: 소리 `1a60`, `3b302`(A0 = `3b8a6`), 설치 `38db6`(`3b288`, `3b334` C 소비 `38dbe BCC` → 설치 `39366`(범위 밖 133 block 사슬)), `3b2ee`, `BRA 3a350`.
- 경계: `3b5a6`(결정 2에서 leaf로 넣을지), 설치 값 `39366`, 자식 `3af86`.
- fixture: 116/117 N31 `38c36` node에서 `(A6)` := `38d56`. BYTE `62` = 0/`ff`, `3b334` C 두 갈래.

### `39f9c`(54: `39f9c` `3a0dc`)

- [F] `39f9c`: 소리 `1ac8`(`3c44`), `4ae4a`(`3b7ce`), `4ff96`, `d3d7c` 4회(파편), `28ae` 자식 `3a2fa`(N31), `49214`.
- [F] `3a0dc`: BYTE `5e` < `1b`이면 27 slot BRA.W 표 `3a0f0`(slot `3a0f4..3a15c`), 상한 이상은 `3a160`이다.
  - 이어서 `4d8d8`, `4db18`(경계), `3b302` 3회, `3a5d2`(N33), `496c2`, 소리, 설치 `3a1e0`(N33).
  - 출구: N33 `3a24c`, N31 `3a2f4`.
- [F] 두 범위 사이 `3a048..3a0dc`는 다른 함수다. `3a0d2 MOVE.L #38e86,(A6)`을 포함하며 이 항목의 closure에 들지 않는다([U]).
- 경계: `4db18`(결정 2), `4ff96`·`d3d7c`(leaf).
- fixture:
  - 116/117 N31/N32b node에서 `(A6)` := `39f9c`/`3a0dc`.
  - `3a0f0` slot 27개 + BYTE `5e` = `1b`/`ff`.

### `3acd6`(12, N32b 자식)

- [F] 애니메이션 bank `2000b4`, `49f8c`, 소리 `8ebe`, `49274`(U08), 설치 `3ad20`.
- [F] `288c`(C 소비 `3ad26 BCS`), `43e34`, `49fc6`(C 소비 `3ad3c BCC`), `JMP 2a00`.
- [I] 짧은 효과 자식이다.
- fixture: 빈 node slot에 `(A6)` := `3acd6`, 부모 포인터 선언. 또는 N32b `39d8a` 경로(BYTE `ac` 편집) chain fixture.

### `4c390`(6; `4c3ba` 2 제외)

- [F] 네 조각의 공통 꼴: `MOVE.L A0,5c8e(A5)`, `JSR 4bce0`(N33) 또는 `4bc44`(U08b), BYTE `549f`·`5cb4` 설정, `BRA 4c810`(N34).
- 진입은 `4c390`, `4c3a2`(N28 `2c79a`; routing된 호출자), `4c3cc`다.
- fixture: 116/117 N28 node에서 `2c79a` 직전 상태(A0 선언)로 진입하고, 복귀 LONG = `2c7a0`.
- 주의: `tools/observe_animation_machine_fade_card.py` 376행과 `verify_animation_machine_fade_card.py` 154행이 `4c3a2`를 native guard 대상(실행 전 거부)으로 선언한다. C++ routing을 더해도 이 native guard 선언은 바뀌지 않는다고 본다([I]). 병합 때 확인한다.

### C 생산 leaf helper(38)

| helper | block | 내용 | RTS C | 부르는 곳 |
| --- | --- | --- | --- | --- |
| `4c2fa` | 5 | `4c2fa..4c340` | `ANDI.W` 뒤(Clear) | `3a5ac`, N23 경계 |
| `4d6b4` | 8 | `4d6b4..4d6f2` | `4d6c4`·`4d6ea` Set, `4d6f0` Clear | `3a4e6`(소비 `3a4ec`), `33e48` 사슬 |
| `4d734` | 6 | `4d734..4d766` | MOVE 뒤(Clear) | N22b, N30b, N29a `30f70`, N31 |
| `4d98a` | 4 | `4d98a..4d9a2` | MOVE 뒤(Clear) | N22b `3e0a6`, N30b, `3b5a6` |
| `4d9ba` | 3 | `4d9ba..4d9d6` | MOVE 뒤(Clear) | N30b, N29a `30f7e`, N31 |
| `4eea2` | 8 | `4eea2..4eef4` `4f08a..4f0c4` | Clear(`4f0bc MOVE.L` 뒤 RTS, MOVEM은 flag 불변) | `4d4b4` |
| `4ff96` | 2 | `4ff96..4ffba` | `MOVE.W (A7)+` 뒤(Clear) | N22b `3d8de`, N29b, N30b, `3383c`, `39f9c`, N28·N29a·N33 경계 |
| `d3d7c` | 2 | `d3d7c..d3d9c` | RTS 없음: `2986`(A0 = 자식 값 `d3d9c`, A1 = `100bf4`) 뒤 `JMP 49214`. `2986` caller-X 제한 적용 | 위와 같음 |

- 시작: `4c2fa 4c2fe 4c308 4c30a 4c32a 4d6b4 4d6c0 4d6c6 4d6cc 4d6d4 4d6d8 4d6e0 4d6ec 4d734 4d73a 4d742 4d746 4d750 4d75e 4d98a 4d990 4d998 4d99c 4d9ba 4d9c6 4d9ca 4eea2 4eeac 4eeb6 4eebc 4eeea 4f08a 4f0a8 4f0b8 4ff96 4ffb0 d3d7c d3d92`.
- [F] 이 helper들은 이미 routing된 N28·N29a·N30a·N31·N32·N33 계약의 "경계(실행부 없음)" 목록에 있다. B2b 병합으로 그 단위들의 fixture 경계도 줄어든다.
- 선택: `4db18`(18 block: `4db18..4db42` `4dbdc..4dc66`). 넣으면 B2b 227이다(결정 2).

## 새로 확인한 범위 밖 사슬(이 계약 밖, 참고)

| 사슬 | 진입·참조 | 정적 block | 비고 |
| --- | --- | --- | --- |
| `82(A6)` 부상태 `3a60a..3abde` | N33 `3a5d2` `MOVE.L #3a60a,82(A6)`. 사슬 안에서 `82(A6)` 즉값 27개(`3a60a` `3a622` `3a670` … `3ab24`). `3a5be JSR (A0)`로 실행 | 75 | 간접 `JSR (A?)` 2곳(`3ab7e` `3abda`), `3b398`(N33)·`3b446` 호출. [I] 38ba0 계열의 partner 동작 script |
| `b3dbc` | `60516` `2986` 자식 | 31 | B1 결정 5 |
| `3ae84` `2d57a` `2d3ae` | `3a4da` `28ae` 자식 | 20/62/41 | |
| `39366` | `38d56` 설치 | 133 | `391e8..395dc` `3b044..3b118` |
| `3af86` `3b5a6` | `38d56` | 18/9 | |
| `2ba50`/`2bf1e..2c6f4` | N28 범위 밖 설치 | [U] | `4c390` `4c3cc`의 호출자 |
| `3abec..3acd6` | 참조 [U] | [U] | `3acd6` 앞 영역 |

- [F] 재범위 §3의 고아 설치 38곳(사슬 2,328 block)과 단위별 "미실행 설치"(1단계 2,304 block) 가운데 B1/B2에 들지 않은 것은 여전히 남는다. B1/B2는 STATUS가 이름을 든 사슬만 다룬다.

## 영향받는 기존 시험·검증기

[F] 아래 파일이 새 routing 대상 PC를 쓴다. 단위 시험은 F4 관례상 stop 확인이라 통과할 것으로 본다([I]). 각 사용처의 기대를 병합 전에 확인한다.

- 단위 시험 사용처:
  - `animation_machine_objects_n25_test.cpp`(`5eed2`), `n26`(`5f504`), `n27`(`60516`), `n30`(`3383c` `4bfc0` `4d418` `4db18` `33940`).
  - `n31`(`3a4a4` `38d56` `3a5be` `4d734` `4d9ba`), `n32`(`3a4da` `3a5be` `3b424` `4d4b4`), `n32b`(`39f9c` `3acd6` `3a4be` `3a4da` `3a5be` `3b424`).
  - `n33`(`3a4a4` `3a4be` `3a5be` `3b424` `4bfc0` `4c390` `4ff96` `d3d7c`), `n28`(`4c3a2` `4d4b4` `4ff96` `d3d7c` `4db18`), `n29`(`4d418` `4d4b4` `4d734` `4d9ba` `4ff96` `d3d7c`), `n23`(`4d418`).
- pin된 검증기: `tools/verify_animation_machine_area_clear.py` 883행 `4b6f4`(B2a 선택 helper; 결정 4). fade_card 관측·검증기의 `4c3a2` guard(위).

## 결정 필요 (MAIN DECISION NEEDED)

1. **B2 재분할.** B2a(190)·B2b(209) 두 단위안을 채택할지 정한다.
2. **B2b 범위.** C 생산 leaf helper 38을 넣을지 정한다. 권고는 넣는 것이다. B1 b 단위와 이미 routing된 N28~N33의 공용 경계라 효과가 크다. `4db18`(18)·`3b5a6`(9)까지 넣으면 236으로 상한을 넘는다.
3. **`4c3ba` 미사용 진입.** 정적 참조가 0이다(전체 이미지 LONG 0건, ±32 KiB PC 상대 0건). 권고는 routing하지 않고 "미사용 후보, [I]"로 기록하는 것이다. GOAL §2 "미사용 데이터의 존재와 실제 실행 가능한 기능을 구분"에 따른다.
   - 근거·바이트 SHA를 남기고, 시험에서 `4c3ba`가 `unsupported animation machine PC`로 남는지 확인한다.
   - 대안: 완전성을 위해 2 block을 routing하고 fixture로 검증한다. 다만 그렇게 하면 "실행 가능 기능"으로 잘못 읽힐 수 있다.
4. **`4b6f4` routing.** pin된 area_clear 검증기의 이웃 기대를 바꿔야 한다(`SUPERSEDED_NEIGHBOUR_ERRORS`에 추가, 검증기 SHA 변경). 대안: `4b6f4`를 경계로 남기고 `5eed2`/`5f504` fixture를 거기서 stop한다.
5. **`4d4b4`의 계산 C.** 소비자가 없는 CMP borrow C를 계산해 둘지(권고), Unknown으로 둘지 정한다.
6. **순서.** B2b를 B1보다 먼저 하는 안(B1 결정 4와 같음)과, `82(A6)` 부상태 사슬(75)을 B2b 다음 단위(B2c 후보)로 둘지 정한다.
7. **`2986` 자식 값**(`338f8`, `b3dbc`, `d3d7c`가 넘기는 `d3d9c`). B1 결정 5와 함께 정한다.

## 미확인

- [U] `2b5xx`(`2b662 JMP 4d418`) 쪽 소비자, `44602` RTS C의 소비자.
- [U] `4c390`/`4c3cc` 호출 사슬(N28 범위 밖 `2ba50` 계열)의 자연 도달.
- [U] `3a048..3a0dc` 함수와 `3abec..3acd6` 영역의 진입.
- [U] 400 frame 밖·응답 `00`·controller 생략 해제 시의 자연 도달.

## block 목록

[F] scratch `lists.txt`(SHA256 `6e5cbd1388d8cd528c21ac641aa3f35777d4fc27ecc96d6d3fb860dd5e6c2d8a`)와 같다.

- **`5eed2`(28)**: `5eed2 5eee2 5eef8 5ef06 5ef14 5ef3c 5ef42 5ef48 5ef4e 5ef58 5ef60 5ef66 5ef6c 5ef70 5ef76 5ef80 5ef84 5ef8a 5ef8c 5efb4 5efba 5efc0 5efc6 5efca 5efd0 5efda 5efde 5efe4`
- **`5f504`(53)**: `5f504 5f50a 5f520 5f54e 5f576 5f57c 5f584 5f596 5f59e 5f5a2 5f5ba 5f5c8 5f5ce 5f5da 5f5e0 5f5e6 5f5ea 5f5f0 5f5f2 5f602 5f62e 5f63c 5f664 5f66a 5f67c 5f684 5f688 5f694 5f69a 5f6a8 5f6b6 5f6bc 5f6c2 5f6c6 5f6ca 5f6d4 5f6da 5f6e2 5f6ea 5f6f2 5f702 5f706 5f714 5f718 5f71e 5f728 5f738 5f73e 5f744 5f748 5f74e 5f758 5f75e`
- **`60516`(100)**: `60516 6051c 6053c 60546 60554 60568 6056c 6057a 605a2 605ae 605be 605c6 605d4 605dc 605e0 605ee 605f4 605f8 60600 6060a 60616 6061e 6062e 60632 60640 60644 6064a 60670 60684 6068c 60690 60694 6069a 6069c 606b2 606ba 606be 606c6 606d0 606dc 606e4 606f4 606f8 60706 6070a 60710 60718 60720 60724 60728 60730 60734 60742 6074a 6074e 60756 60760 60766 6076e 6077e 60782 60790 60794 6079a 607a8 607b0 607b4 607c2 607d0 607d6 607de 607e6 607ee 607f6 60828 60830 6084a 6084e 6085e 60862 60870 60874 6087a 60880 60884 60888 60892 6089a 608cc 608d4 608ee 608f2 60902 60906 60914 60918 6091e 60926 60932 60938`
- **B2a leaf(9)**: `44602 4461c 44620 44626 4462a 4463c 4b6f4 4b6fc 4b700`
- **`3383c`(15)**: `3383c 33846 3384e 33858 3385e 3387a 33896 338b2 338de 338e8 338f2 33940 33948 33950 33952`
- **`3a4a4`(29)**: `3a4a4 3a4b6 3a4b8 3a4be 3a4c6 3a4ce 3a4d0 3a4da 3a4e2 3a4ec 3a4f0 3a4fa 3a502 3a506 3a51e 3a528 3a52e 3a542 3a544 3a560 3a570 3a574 3a584 3a5a0 3a5a6 3a5b2 3a5b8 3a5be 3a5ca`
- **`3b424`(6)**: `3b424 3b42e 3b446 3b448 3b452 3b456`
- **`4bfc0`(10)**: `4bfc0 4bfc4 4bfc8 4bfce 4bfd4 4bfda 4bfee 4bffe 4c006 4c016`
- **`38d56`(18)**: `38d56 38d60 38d70 38d7a 38d80 38d88 38d8c 38d90 38d98 38d9c 38da6 38db0 38db6 38dba 38dbe 38dc2 38dc8 38dd0`
- **`39f9c`(54)**: `39f9c 39fa6 39fb0 39fba 39fc0 39fdc 39ff8 3a014 3a03a 3a044 3a0dc 3a0e8 3a0f4 3a0f8 3a0fc 3a100 3a104 3a108 3a10c 3a110 3a114 3a118 3a11c 3a120 3a124 3a128 3a12c 3a130 3a134 3a138 3a13c 3a140 3a144 3a148 3a14c 3a150 3a154 3a158 3a15c 3a160 3a166 3a16c 3a176 3a180 3a188 3a192 3a196 3a1a0 3a1aa 3a1ae 3a1b2 3a1b8 3a1c6 3a1da`
- **`3acd6`(12)**: `3acd6 3ad06 3ad14 3ad1a 3ad20 3ad26 3ad2a 3ad30 3ad36 3ad3c 3ad40 3ad46`
- **`4c390`(6, `4c3ba` `4c3c2` 제외)**: `4c390 4c398 4c3a2 4c3aa 4c3cc 4c3d4`
- **`4d418`(21)**: `4d418 4d41e 4d42a 4d432 4d438 4d43c 4d446 4d44e 4d454 4d476 4d48c 4d490 4d4ac 4d4b4 4d4c2 4d4cc 4d4d8 4d4e0 4d4e8 4d502 4d506`
- **B2b leaf(38)**: 위 "C 생산 leaf helper" 절.
