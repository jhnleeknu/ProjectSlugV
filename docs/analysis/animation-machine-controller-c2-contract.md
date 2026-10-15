# F5 controller C2: 전환·해체·게임 mode 분기와 `c00444`/`c00468` 경계 계약 초안

**상태: 구현 전 계약 초안 — 메인 결정 전.** 원본 바이트·scratch native 탐침 근거이며 구현·검증 기록이 아니다.

범위 근거는 F5 범위 문서(`animation-machine-frame-head-f5-scope.md`, SHA256 `973d4595…`)의 §4 C2 행(`c686..c6ce` `c724..c988` `3162` `4755e` `47570` `4823a` `49a1a` `4e1cc` `bbd4` `c2fa..c364` `8b64` `8bb6`, 127 block, 위험 자식 미routing·`caf0` port 2,072)과 결정 D9/D10이다. C1 계약(`animation-machine-controller-c1-contract.md`) 결정 1의 재배치를 따르고, D9 권고(`animation-machine-controller-d9-decision.md`)의 게임 mode 구성에서 전환 뒤 연속을 위해 자식 `b300`(11 block)과 그 menu 항목 handler(25 block)를 더한다(결정 2).

작성자·기준·도구·표기는 C1 계약 머리와 같다(ROM SHA256 `29112a94…c886c860f`, HEAD `c49bcd2`, routing 원천 SHA256 `c7318132…caad2`, scratch `ana_c/leaders.py` `units.py` `cprobe.py` `p2.py` `p4.py` `p5.py`).

## 요약

- [F] **정적 leader 128개(controller closure) + 자식 `b300` 11개 + menu 항목 handler 25개 = 164.** controller closure 13 범위 1,192바이트(짝수 PC 596), `b300..b362` 98바이트, handler `a75a..a770` 22바이트·`a856..a8d0` 122바이트.
  - 범위 문서 C2(127)에서 `c724..c74c`(6)·`c7fc..c80e`(3)를 C1로, `8b64`/`8bb6`(3)을 C3로 보냈고, `c4cc`(7)·`100e`(1)·`101c`(1)를 C1에서 가져왔다. `3162`는 dbra 대상 `31ce`가 leader라 6개다.
- [F] **C2는 controller가 상태를 바꾸는 frame이다.** 전환 뒤 새 대기 상태(`c6c0` `c79a` `c82e` `c89c` `c8e8` `c940`)의 매 frame 경로도 C2 안에 있다(대기 상태는 C1 꼬리 `c988`로 이어진다).
- [F] **탐침의 자연 전환 두 가지**(stage controller node `100b30`이 idle `270e`이 되는 frame, 자연 seed에서 frame 1/221/241/245):
  - 게임 mode(D9 (ii)): `c7fc` → `c80a` → **`c76a`**: `3162`(D0 = −1 → replay 끔, BYTE `104cd4` := 0) → `c4cc`(controller 뒤 모든 node 해체) → `ca76` → `caf0`(화면 초기화, port 2,072) → BYTE `62(A6)` := 0, 자식 `b300` 할당(D0 = `14`) → callback `c79a` 설치 → `c79a`(BYTE `10fdb6`/`10fdb7` = 1이면 `c80e`, BYTE `62(A6)` = 2면 `c7c6` 재시작, 0이면 꼬리, 그 밖이면 BIOS `c00444`). 이후 매 frame `c79a c7a4 c7ae c7ba` → C1 꼬리.
  - demo mode(D9 (i)): `c66a` → `c686` → `c69a`: `c4cc` → `caf0` → `ca76` → 자식 `e66aa` 할당 → `c6c0` 설치 → `c6c0`(BYTE `62(A6)` = 0이면 `c73e` → 꼬리). 자식 `e66aa`가 `62(A6)`을 세우면(탐침: 106 frame 뒤) **`c6c8 JMP c00444`**(종단).
- [F] **경계:** 이미 routing된 callee 13개(`289e` `28ae` `2a28` `2a0a` `2a84` `3dce` `8bbc` `9060` `bb74` `bbb8` `ca48` `ca76` `caf0` `e7bf4` `e8a1c`, 자식 `b300`의 `3d3a` `de424` `a29c` `a2b8` `ddf9a` `8c16` `a370` `2a00`), C1 진입(`c988` `c73e` `c724` `c7fc` 설치), BIOS `JMP c00444` 3곳(`c6c8` `c7c0` `c982`, 종단), `JSR c00468` 1곳(`c310`, 카드, 선언 resume), ROM 쓰기 `c690 CLR.W 180.l`(canonical ROM에서 도달 불가).
- [F] **자식 node(설치만 하고 실행하지 않음):** `b300`(게임 mode stage 종료 전환; [I] menu 표 `a810`의 문자열 `"GAME START"` `"OPTION"` `"HOW TO PLAY"` `"EXIT"`(`a7e2..a80e`)로 보아 AES(BYTE `10fd82` = 0) 주 menu, 결정 2에서 routing 제안), `e66aa`(demo 끝, 72 leader, TRAP 2·간접 JSR 1 — 미routing 유지), `de660`(`c8ce`, 68 leader), `c250`(카드, `c332`, 기존 card_child 실행부). 미routing 자식은 **같은 frame의 N pass**가 그 node에 닿을 때 `unsupported animation machine PC`(frame 전체 rollback)다.
- [F] **carry·flag:** C 소비 2(`c87e` `c916`, `289e`), RTS 너머 Z 소비 2(`c964` `c97a`, C1 결정 3과 같은 규약), 같은 block `CMPI`/`BCS`(`3162` `4823a`). `MULU.W`(`49a44`, RNG 표 생성) 1.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 128(+36).** routing: `100e..1022` `3162..31d6` `bbd4..bbfa` `c2fa..c364` `c4cc..c4f8` `c686..c6ce` `c74c..c7fc` `c80e..c988` `4755e..47594` `4823a..48250` `49a1a..49a58` `4e1cc..4e216` `e62ec..e630a`(+ 결정 2 `b300..b362` `a75a..a770` `a856..a8d0`).
   - [F] 범위 이웃: `1002..100e`(H1 밖, 별도) `31d6`(H2) `bbb8..bbd2`(card_menu_save, 앞) `bbfa..`(다른 함수) `c2f8`(card_menu_close 끝 `c2c8..c2f8`) `c364`(fade_card `c364..c3be`) `c6ce..c6da`(문자열 자료 `"\p\0\c\x03TIME\0\0"`, C3 `c6f4`가 읽음) `47540..4755e`(stage_catalog) `47594`(stage_area) `49a58`(stage_area) `4e186..4e1cc`(objects u07) `4e216`(transition) `b2fe`·`b362`(`b362`는 `ca2c JMP`만 참조하는 다른 함수, 범위 밖)는 다른 실행부 또는 routing 밖이다.
   - `c690 CLR.W 180.l; BRA.W c610`(`c686`에서 WORD ROM `000180` ≠ 0일 때): [F] canonical ROM의 `000180` = `0000`이라 도달하지 않는다. block 시작으로 routing하되 실행하면 ROM 주소 쓰기이므로 `am_write`의 기존 ROM 쓰기 오류(checked, rollback)다. `c610`(C3)은 그 뒤다. host 수준 `game_ready`와 같은 "ROM180 = 0만 지원" 규약이다.
2. **자식 `b300`과 menu 항목 handler를 C2에 넣는다(제안, +36 block).** [F] `c77e`가 `b300`을 node로 할당하고 같은 frame의 N pass가 그 node(callback `b300`, 다음 frame부터 `b344`)를 실행한다.
   - `b300..b362`는 leader 11개이고 callee가 모두 이미 routing돼 있다(`3d3a` stage_area, `de424` card_child, `a29c`·`a2b8` card_menu, `ddf9a` stage_entry, `8c16` exit, `a370` card_menu_open, `2a00` fade_card self delete).
   - `b30c`가 `a29c`에 넘기는 menu 표 `a810`은 (문자열, handler) LONG 쌍이다: (`a7e2`, `a856`) (`a7f4`, `a876`) (`a7ed`, `a896`) (`a80a`, `a8bc`). card menu 실행부가 매 frame 선택 항목의 handler를 live 대상으로 부른다. [F] 탐침(`p5.py`)에서 전환 4 frame 뒤부터 136 seed 모두 `a856`(및 `a876` `a896` `a8bc`)를 실행했다.
   - handler closure는 leader 25개(`a856` `a876` `a896` `a8bc` 각 함수 + 공통 `a75a`)이고 callee는 모두 routing돼 있다(`a73e` card_menu_open, `a71a`·`9f36` card_menu_save, `38e8` card_menu). `a8c8 JMP c00444`(EXIT 선택)는 BIOS 종단이다(N에서 닿으면 기존 `unsupported animation machine PC` rollback; 구동기 종단 처리는 C segment만, D9 문서 §5.3).
   - [F] 탐침에서 전환 뒤 N pass의 새 routing 밖 실행 code는 `b300..b360`과 이 handler뿐이다. 선언 생략(S) 구성에서 실행되던 routing 밖 PC(실행부 내부 PC) 53개를 빼고, controller closure를 뺀 결과다(아래 "탐침 집계"). 이것을 넣지 않으면 D9 (ii) 구성의 C++ 연쇄는 전환 frame(자연 1/221/241/245)에서 끝난다.
   - [I] `b344`는 `a370`이 0이 아닌 값을 돌려주면 부모(controller) `62` := 3을 쓰고 self delete한다. 이때 controller `c79a`는 `c7c0 JMP c00444`로 간다.
   - 대안: `b300`+handler를 별도 단위(C2b, 36 block)로 둔다.
3. **BIOS `JMP c00444`(SYSTEM_RETURN) 종단.** [F] C2의 `c6c8` `c7c0` `c982`(C3의 `c598` `c5a6`)는 PC := `c00444`. 실행부는 `JMP`까지 실행하고(PC 설정) 다음 step에서 `c00444`가 routing 밖이라 `unsupported animation machine PC`(rollback)다. **frame 구동기가 같은 입력에서 stop `c00444`로 다시 실행해 닿으면 `animation frame controller system return`(checked, 상태 보존)으로 바꾼다**(D9 문서 §5.3). resume은 없다. [F] 탐침 demo 구성: 136 seed 중 `c6c8` 도달은 아래 집계.
4. **카드 BIOS `c310 JSR c00468` 선언 resume.** [F] `c2fe`: A6 LONG push, BYTE `10fdc4` := 1, WORD `10fdce` := `268`, `JSR c00468`(복귀 `c316`). `c316`: A6 pop, A5 := `108000`, BYTE `10fdc6`(`7dc6(A5)`) 검사. 기존 card resume(`c376` → `c37c`)과 같은 BIOS 함수·같은 응답 바이트다. 제안: frame 구동기의 card resume이 복귀 LONG `c37c` **또는 `c316`**을 받아들이게 넓힌다(PC := 복귀 LONG, A7 += 4, BYTE `10fdc6` := `card_answer`, C Unknown, `AnimationFrameWait` pc `c00468`). [F] 자연 경로에서는 `c890`(`c882` 경로, `c82e`/`c874` 뒤)에서만 닿고 탐침 구성에서는 닿지 않았다.
5. **RTS 너머 Z 소비 `c964` `c97a`.** C1 결정 3의 규약(복귀 block에서 BYTE (A0) 재읽기)을 같이 쓴다. [F] 두 곳 모두 `JSR 4a974.l` 복귀점이다.
6. **`c4cc` 해체 반복과 A6.** [F] `c4cc`: `3dce`(cleanup) → `2a0a`(cleanup) → A0 := LONG `8(A6)` → `100820`(frame head node)에 닿을 때까지 `2a84`(node 제거)를 반복한다. A6(controller node `1008e4`)는 바꾸지 않는다. 반복 수는 node 수만큼이고 기존 `run_animation_machine` block 예산 안이다. [F] 탐침: 전환 frame에서 반복 6~7회.
7. **`49a1a` RNG 재초기화.** [F] D0 ≠ 0이면 WORD `10f02c` += 1 뒤 그 값으로, D0 = 0이면 0으로 55개 WORD 표 `1056b4..` 를 `MULU.W` 점화식으로 채우고 LONG `105722` := 끝 포인터. F4 결정 1의 seed 준비가 native로 실행한 함수이고 routing은 처음이다. `MULU.W D1,D1`(16×16→32 무부호)을 정확히 구현한다.
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_controller_c2.cpp`의 `animation_controller_c2_block`(+ 결정 2면 같은 파일에 `b300` 범위). 오류: `unsupported animation controller c2 PC`(내부 PC), `controller c2 caller requires known carry`(C 소비 block에 Unknown C, 기존 어휘), C1과 공유하는 `unsupported animation controller flag source`.
9. **무효화 탐침.** [F] 정적 검색에서 C2 PC를 "routing 밖" 탐침으로 쓰는 엔진 시험은 없다(`c4cc` `c6c0` `c686` `47570` `49a1a` `3162` `4823a`는 host 수준 API 시험·도구 `game_ready` `game_restart` `object_removal` `game_initialization` `random_state` `input_initializer`의 진입 PC이고 실행부와 무관하다). `animation_machine_card_menu*_test.cpp`의 `c2fa`·`bbd4`는 [U](구현 뒤 `make all test`로 확인; 다른 단위의 경계 stop으로 쓰였다면 유효).

## 원본 바이트 근거

[F] controller closure 13 범위 1,192바이트, 연결 SHA256 `a96f2920142addbce8cbd7c56e58e2311628cc2e61bef21e3834935162f4fc1a`. 자식 `b300..b362` 98바이트 SHA256 `bc5f46ec384f82ea56979fb48ad1a093a155ddd14169b90c68b33909314e5d81`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `100e..1022` | 20 | `13363083d1e3e42a1c6dd86a0363646eb9f8a2f47937d45a4c034d43fd514377` | 2 |
| `3162..31d6` | 116 | `45f12864fe11bbf13dddf5d3fc082fde94b7d7e58e237a236d7f040e1ad78d16` | 6 |
| `bbd4..bbfa` | 38 | `4f0c8121b99d1ede8db01fa7e6c8289b76e2f41a0998dd583d07b02334148acb` | 3 |
| `c2fa..c364` | 106 | `aa60c0ce83c981a74323b4524a79917423dcdac91ce1df6c103318a196cf523a` | 7 |
| `c4cc..c4f8` | 44 | `2836ee67098e34cad17d3544fa600b94882a95879e3f4e14372f9c04a30df14b` | 7 |
| `c686..c6ce` | 72 | `4f8b8311cd27a8de6aaf93283354ede5a96a1e8862e5de21ca7aa580693be21f` | 9 |
| `c74c..c7fc` | 176 | `ea10f344a9c64a28e7404c7119d858154a5c3732d76712dab520d2da3e678e6d` | 22 |
| `c80e..c988` | 378 | `ff24273eae945ba4b2f1189eabd8856e4090e69fe77dafd5d379cd354e9bf53f` | 50 |
| `4755e..47594` | 54 | `0164abb50b429ce276453e294cb78c997ebe2383a1f268fb88fd64627dede27e` | 7 |
| `4823a..48250` | 22 | `2550c7eeb3e744897fe3667d744e75ad09a02da1cf28f082137779b5b6324549` | 3 |
| `49a1a..49a58` | 62 | `467831a76fa05626db92dbd68cd15497cf4f29ddf4e82d37e273516cc7b10ecb` | 5 |
| `4e1cc..4e216` | 74 | `da04e1182a1054029546c83c9b87c720c23fe029e2622c2585035b3aff22d0e8` | 3 |
| `e62ec..e630a` | 30 | `fffe307225577c4057cf88b83631ff94b2d9cf3ef11be287b12baa9fa6c56ecc` | 4 |
| `b300..b362`(결정 2) | 98 | `bc5f46ec384f82ea56979fb48ad1a093a155ddd14169b90c68b33909314e5d81` | 11 |
| `a75a..a770`(결정 2) | 22 | `fba6ba202d4a9285d11d535bfcb44a09c8d41c95de0c2c13d61c37c4d8a9d8f7` | 3 |
| `a856..a8d0`(결정 2) | 122 | `37be8dcc20396cbc48276aadd046a2ad0fe567aaa2b6f43864f60b192d4aa596` | 22 |

- [F] 자료: replay 표 `f0dfe`·`f1a06`(`3192`/`319e`, LONG, 색인 D0 × 4; D0 < 2일 때만), `bb8e`(`bbda LEA`, card_menu_save 실행부가 읽음), `a810`(`b30c`, card_menu가 읽음), `4e68e`(`4e1ee`/`4e204`의 callback 값, `2a28`이 설치), ROM WORD `000180`(`3358`·`31bc`·`c686`, 값 0).
- [F] host 수준 기존 구현(독립 참조, block 실행부가 아님): `restart_game`(`c610..c652`, `game-restart.md`), `step_game_ready`(`c654`/`c66a`/`c686`/`c6c0`, `game-ready.md`), `initialize_game`/`prepare_game_prelude`(`47570`, `game-initialization.md`·`game-prelude.md`), `remove_objects`(`c4cc`, `object-removal.md`), `seed_random`(`49a1a`). 이들의 원본 비교 기록은 이 단위의 의미 근거로 쓸 수 있으나, 실행부는 block 계약을 따로 지켜야 한다.

## block 목록과 실행 의미

표기는 C1 계약과 같다. A5 = `108000`(`7d82(A5)` = `10fd82`, `7d8e(A5)` = `10fd8e`, `7db6(A5)`/`7db7(A5)` = `10fdb6`/`10fdb7`, `7dc6(A5)` = `10fdc6`, `7dd0(A5)` = `10fdd0`, `702a(A5)` = `10f02a`, `-334b(A5)` = `104cb5`, `-7fe9(A5)` = `100017`, `-7ff2(A5)` = `10000e`, `-7762(A5)` = `10089e`, `-332c(A5)` = `104cd4`).

**frame 계수 초기화 `100e`(`4757c`) 1, IRQ 요구 수 `101c`(`c758` + 범위 밖 `de37a` `eb988` `eb99a`) 1**
- `100e`: `MOVE.W #0, -7ff2(a5); MOVE.W #0, -7762(a5); RTS` — WORD `10000e`(frame counter)·`10089e`(head `+7e`) := 0
- `101c`: `MOVE.B d0, -7fe9(a5); RTS` — BYTE `100017` := D0.B(D2 vblank 대기 기준값)

**입력 mode 선택 `3162`(`c646` `c76c` `c814`, 범위 밖 `310c`) 6** — D0.W < 2이면 replay(BYTE `104cd4` := 1, replay/recorder 포인터 `104cc4`/`104cc8` := 표 `f0dfe`/`f1a06`[D0], 계수 0), 아니면 실시간(`104cd4` := 0).
- `3162`: `LEA.L 108000.l, a5; LEA.L -3358(a5), a0; CLR.L (a0)+ … CMPI.W #2, d0; BCS.W 3188 (9명령)` (→`3180`)
- `3180`: `MOVE.B #0, -332c(a5); RTS`
- `3188`: `MOVE.B #1, -332c(a5); ADD.W d0, d0; ADD.W d0, d0 … MOVE.W 180.w, d0; BEQ.W 31d4 (14명령)` (→`31c4`)
- `31c4`: `MOVEA.L -3338(a5), a0; MOVEQ #ff, d1; MOVE.W #5ff, d7` (→`31ce`) — ROM180 ≠ 0일 때만(도달 불가, [F] ROM `000180` = 0)
- `31ce`: `MOVE.B d1, (a0)+; DBRA d7, 31ce` (→`31d4`) — 도달 불가(위와 같음; recorder 버퍼 `ff` 채우기)
- `31d4`: `RTS` — FLOW

**카드 menu 표 준비 `bbd4`(`c2fa` + 범위 밖 `bcaa`) 3**
- `bbd4`: `LEA.L 107f1c.l, a0; LEA.L bb8e(pc), a1; MOVE.W #18, d7; BSR.B bbb8` (→`bbe4`)
- `bbe4`: `LEA.L -e4(a5), a0; MOVE.B #ff, -cf(a5); MOVE.W #16, d7; BSR.B bb74` (→`bbf4`)
- `bbf4`: `MOVE.W d0, -ce(a5); RTS`

**카드 BIOS 요청 `c2fa`(`c890`) 7**
- `c2fa`: `BSR.W bbd4` (→`c2fe`) — FLOW
- `c2fe`: `MOVE.L a6, -(a7); MOVE.B #1, 10fdc4.l; MOVE.W #268, 10fdce.l; JSR c00468.l` (→`c316`) — BIOS 경계(결정 4)
- `c316`: `MOVEA.L (a7)+, a6; LEA.L 108000.l, a5; TST.B 7dc6(a5); BNE.W c35c` (→`c326`)
- `c326`: `MOVE.W 7dd0(a5), d0; BTST.B #0, d0; BEQ.W c35c` (→`c332`)
- `c332`: `CLR.B 62(a6); MOVEA.L #c250, a0; MOVE.W #0, d0; JSR 28ae.l` (→`c346`) — 자식 `c250`(기존 card_child 실행부)
- `c346`: `MOVE.L #bef0, 76(a0); MOVE.W #4, 7a(a0); MOVE.W #4, 7c(a0); RTS` — A0 = 할당 결과(실패 시 `28ae`의 `290e`가 A0 := A5 + sext(`8e98`) = `100e98`로 둔 주소에 쓴다; 원본도 C를 보지 않는다)
- `c35c`: `MOVE.B #ff, 62(a6); RTS`

**전체 node 해체 `c4cc`(9곳) 7** — 결정 6.
- `c4cc`: `JSR 3dce.l` (→`c4d2`) — FLOW
- `c4d2`: `JSR 2a0a.l` (→`c4d8`) — FLOW
- `c4d8`: `MOVEA.L 8(a6), a0` (→`c4dc`) — FLOW
- `c4dc`: `CMPA.L #100820, a0; BEQ.W c4f6` (→`c4e6`)
- `c4e6`: `MOVE.L a0, -(a7); JSR 2a84.l` (→`c4ee`)
- `c4ee`: `MOVEA.L (a7)+, a0; MOVEA.L 8(a0), a0; BRA.B c4dc` — FLOW
- `c4f6`: `RTS` — FLOW

**demo 끝 해체 `c686`(C1 `c674`/`c67e`) 9** — host 수준 `step_game_ready`와 같은 경로.
- `c686`: `TST.W 180.l; BEQ.W c69a` (→`c690`) — ROM WORD 읽기(live bus)
- `c690`: `CLR.W 180.l; BRA.W c610` — 도달 불가·ROM 쓰기(결정 1)
- `c69a`: `BSR.W c4cc` (→`c69e`) — FLOW
- `c69e`: `BSR.W caf0` (→`c6a2`) — FLOW
- `c6a2`: `BSR.W ca76` (→`c6a6`) — FLOW
- `c6a6`: `MOVEA.L #e66aa, a0; MOVE.W #0, d0; JSR 28ae.l` (→`c6b6`) — 자식 `e66aa`(미routing)
- `c6b6`: `CLR.B 62(a6); MOVE.L #c6c0, (a6)` (→`c6c0`) — 설치점
- `c6c0`: `TST.B 62(a6); BEQ.W c73e` (→`c6c8`) — 대기 상태(매 frame)
- `c6c8`: `JMP c00444.l` — FLOW, BIOS 종단(결정 3)

**게임 시작 `c74c`(C1 `c724`/`c73e`, BYTE `100012` = 2) 4, stage 종료 전환 `c76a`(C1 `c80a`, `c7fc`/… 실패 경로) 6, 대기 `c79a` 5, 재시작 `c7c6` 7**
- `c74c`: `MOVEQ #0, d0; JSR 8bbc.l` (→`c754`)
- `c754`: `MOVE.B #2, d0; JSR 101c.l` (→`c75e`) — BYTE `100017` := 2
- `c75e`: `TST.B 7d82(a5); BEQ.W c76a` (→`c766`)
- `c766`: `BRA.W c80e` — FLOW
- `c76a`: `MOVEQ #ff, d0; JSR 3162.l` (→`c772`)
- `c772`: `BSR.W c4cc` (→`c776`) — FLOW
- `c776`: `JSR ca76(pc)` (→`c77a`) — FLOW
- `c77a`: `JSR caf0(pc)` (→`c77e`) — FLOW
- `c77e`: `MOVE.B #0, 62(a6); MOVEA.L #b300, a0; MOVE.W #14, d0; JSR 28ae.l` (→`c794`) — 자식 `b300`(결정 2)
- `c794`: `MOVE.L #c79a, (a6)` (→`c79a`) — 설치점
- `c79a`: `CMPI.B #1, 7db6(a5); BEQ.W c80e` (→`c7a4`) — 대기 상태(매 frame)
- `c7a4`: `CMPI.B #1, 7db7(a5); BEQ.W c80e` (→`c7ae`)
- `c7ae`: `MOVE.B 62(a6), d0; CMPI.B #2, d0; BEQ.W c7c6` (→`c7ba`)
- `c7ba`: `TST.B d0; BEQ.W c988` (→`c7c0`)
- `c7c0`: `JMP c00444.l` — FLOW, BIOS 종단(결정 3)
- `c7c6`: `MOVEQ #ff, d0; JSR 49a1a.l` (→`c7ce`)
- `c7ce`: `BSR.W c4cc` (→`c7d2`) — FLOW
- `c7d2`: `BSR.W caf0` (→`c7d6`) — FLOW
- `c7d6`: `JSR 47570.l` (→`c7dc`) — FLOW
- `c7dc`: `MOVE.W #8, d0; JSR 4823a.l` (→`c7e6`)
- `c7e6`: `LEA.L -74d0(a5), a0; LEA.L 477e4.l, a1; JSR 2a28.l` (→`c7f6`) — FLOW
- `c7f6`: `MOVE.L #c7fc, (a6)` (→`c7fc`) — 설치점, C1

**이어하기 경로 `c80e`(`c766` `c79a` `c7a4`) 5, 대기 `c82e` 9, `c874` 2, 카드 `c882` 5, 대기 `c89c` 2, 다음 단계 `c8aa` 9, 대기 `c8e8` 4, `c90c` 2, 끝 해체 `c91a` 6, 대기 `c940` 12** — [I] continue·카드 저장·랭킹 계열. 의미 이름은 [U].
- `c80e`: `CLR.W 702a(a5); MOVEQ #ff, d0; JSR 3162.l` (→`c81a`)
- `c81a`: `BSR.W c4cc` (→`c81e`) — FLOW
- `c81e`: `MOVEQ #ff, d0; JSR 49a1a.l` (→`c826`)
- `c826`: `MOVE.L #c82e, (a6); RTS` — 설치점
- `c82e`: `TST.B 7d82(a5); BEQ.W c882` (→`c836`)
- `c836`: `TST.B 7d8e(a5); BEQ.W c882` (→`c83e`)
- `c83e`: `MOVEQ #ff, d0; JSR 49a1a.l` (→`c846`)
- `c846`: `BSR.W c4cc` (→`c84a`) — FLOW
- `c84a`: `BSR.W caf0` (→`c84e`) — FLOW
- `c84e`: `JSR 47570.l` (→`c854`) — FLOW
- `c854`: `MOVE.W #8, d0; JSR 4823a.l` (→`c85e`)
- `c85e`: `LEA.L -74d0(a5), a0; LEA.L 477e4.l, a1; JSR 2a28.l` (→`c86e`) — FLOW
- `c86e`: `MOVE.L #c874, (a6)` (→`c874`) — 설치점
- `c874`: `LEA.L -74d0(a5), a0; JSR 289e.l` (→`c87e`) — FLOW
- `c87e`: `BCS.W c988` (→`c882`) — FLOW, C 소비(`289e`)
- `c882`: `BSR.W c4cc` (→`c886`) — FLOW
- `c886`: `BSR.W caf0` (→`c88a`) — FLOW
- `c88a`: `JSR 47570.l` (→`c890`) — FLOW
- `c890`: `JSR c2fa.l` (→`c896`) — FLOW
- `c896`: `MOVE.L #c89c, (a6)` (→`c89c`) — 설치점
- `c89c`: `TST.B 62(a6); BEQ.W c988` (→`c8a4`)
- `c8a4`: `MOVE.L #c8aa, (a6)` (→`c8aa`) — 설치점
- `c8aa`: `JSR 9060.l` (→`c8b0`) — FLOW
- `c8b0`: `BSR.W c4cc` (→`c8b4`) — FLOW
- `c8b4`: `BSR.W caf0` (→`c8b8`) — FLOW
- `c8b8`: `MOVE.W #30ff, 7c(a6); JSR e7bf4.l` (→`c8c4`)
- `c8c4`: `JSR 4e1cc.l` (→`c8ca`) — FLOW
- `c8ca`: `BSR.W ca48` (→`c8ce`) — FLOW
- `c8ce`: `CLR.B 62(a6); MOVEA.L #de660, a0; MOVE.W #0, d0; JSR 28ae.l` (→`c8e2`) — 자식 `de660`(미routing)
- `c8e2`: `MOVE.L #c8e8, (a6)` (→`c8e8`) — 설치점
- `c8e8`: `TST.B 62(a6); BEQ.W c988` (→`c8f0`)
- `c8f0`: `MOVE.W #9ff, 7c(a6); LEA.L -74d0(a5), a0; LEA.L 477e4.l, a1; JSR 2a28.l` (→`c906`)
- `c906`: `MOVE.L #c90c, (a6)` (→`c90c`) — 설치점
- `c90c`: `LEA.L -74d0(a5), a0; JSR 289e.l` (→`c916`) — FLOW
- `c916`: `BCS.W c988` (→`c91a`) — FLOW, C 소비(`289e`)
- `c91a`: `BSR.W c4cc` (→`c91e`) — FLOW
- `c91e`: `BSR.W caf0` (→`c922`) — FLOW
- `c922`: `BSR.W ca76` (→`c926`) — FLOW
- `c926`: `MOVEA.L #e66aa, a0; MOVE.W #0, d0; JSR 28ae.l` (→`c936`) — 자식 `e66aa`(미routing)
- `c936`: `CLR.B 62(a6); MOVE.L #c940, (a6)` (→`c940`) — 설치점
- `c940`: `TST.B 62(a6); BNE.W c982` (→`c948`)
- `c948`: `TST.B 10fd82.l; BEQ.W c97e` (→`c952`)
- `c952`: `BTST.B #0, -334b(a5); BEQ.W c968` (→`c95c`) — FLOW
- `c95c`: `MOVEQ #0, d0; JSR 4a974.l` (→`c964`)
- `c964`: `BNE.W c982` (→`c968`) — FLOW, Z 소비(결정 5)
- `c968`: `BTST.B #2, -334b(a5); BEQ.W c97e` (→`c972`) — FLOW
- `c972`: `MOVEQ #1, d0; JSR 4a974.l` (→`c97a`)
- `c97a`: `BNE.W c982` (→`c97e`) — FLOW, Z 소비(결정 5)
- `c97e`: `BRA.W c988` — FLOW
- `c982`: `JMP c00444.l` — FLOW, BIOS 종단(결정 3)

**게임 초기화 `47570`(`c7d6` `c84e` `c88a`, C3 `c584` `c626`, 범위 밖 `e676e`) 4, `4755e` 3, `e62ec` 4, `4823a` 3, RNG `49a1a` 5, `4e1cc` 3**
- `4755e`: `MOVEQ #0, d0; JSR e62ec.l` (→`47566`)
- `47566`: `MOVEQ #1, d0; JSR e62ec.l` (→`4756e`)
- `4756e`: `RTS` — FLOW
- `47570`: `CLR.B 5683(a5); CLR.B 5694(a5); CLR.B 569c(a5); JSR 100e.l` (→`47582`)
- `47582`: `BSR.B 4755e` (→`47584`) — FLOW
- `47584`: `MOVEQ #0, d0; JSR 4823a(pc)` (→`4758a`)
- `4758a`: `MOVEA.W #0, a0; JSR e8a1c.l` (→`47594`) — FLOW. 복귀점 `47594`는 stage_area 실행부(기존)이고 거기서 sound 대기 `3aea`가 날 수 있다(D6 선언 해제).
- `4823a`: `CMPI.W #13, d0; BCS.W 48244` (→`48242`)
- `48242`: `MOVEQ #0, d0` (→`48244`)
- `48244`: `MOVE.B d0, 5680(a5); MOVE.B #0, 5681(a5); RTS`
- `49a1a`: `LEA.L 108000.l, a5; TST.W d0; BEQ.W 49a34` (→`49a26`)
- `49a26`: `MOVE.W 10f02c.l, d0; ADDQ.W #1, d0; MOVE.W d0, 10f02c.l` (→`49a34`)
- `49a34`: `LEA.L 56b4(a5), a0; MOVE.W #36, d7; MOVE.W d0, d1` (→`49a3e`)
- `49a3e`: `ADDI.W #7925, d1; ADD.W d0, d1; MULU.W d1, d1; LSR.L #8, d1; EXG.L d1, d0; MOVE.W d0, (a0)+; DBRA d7, 49a3e` (→`49a50`) — 결정 7(55회)
- `49a50`: `SUBQ.W #2, a0; MOVE.L a0, 5722(a5); RTS`
- `4e1cc`: `CLR.B 5d1e(a5); CLR.B 5d1f(a5); CLR.B 5d20(a5) … LEA.L 4e68e(pc), a1; JSR 2a28.l (9명령)` (→`4e1f8`)
- `4e1f8`: `MOVE.W #0, 76(a0); LEA.L 100a6c.l, a0; LEA.L 4e68e(pc), a1; JSR 2a28.l` (→`4e20e`)
- `4e20e`: `MOVE.W #1, 76(a0); RTS`
- `e62ec`: `TST.B d0; BNE.W e62fc` (→`e62f2`)
- `e62f2`: `LEA.L 10de14.l, a0; BRA.W e6302` — FLOW
- `e62fc`: `LEA.L 10de1c.l, a0` (→`e6302`) — FLOW
- `e6302`: `MOVE.L #0, (a0); RTS`

**자식 `b300`(결정 2) 11**
- `b300`: `JSR 3d3a.l` (→`b306`) — FLOW
- `b306`: `JSR de424.l` (→`b30c`) — FLOW
- `b30c`: `LEA.L a810(pc), a0; MOVEQ #3, d0; MOVEQ #4, d1; JSR a29c.l` (→`b31a`)
- `b31a`: `LEA.L e84c8.l, a0; JSR a2b8.l` (→`b326`) — FLOW
- `b326`: `MOVE.W #7095, d0; JSR ddf9a.l` (→`b330`)
- `b330`: `MOVEQ #0, d0; MOVEQ #0, d1; MOVEQ #0, d2; MOVEQ #0, d3; JSR 8c16.l` (→`b33e`)
- `b33e`: `MOVE.L #b344, (a6)` (→`b344`) — 설치점
- `b344`: `JSR a370.l` (→`b34a`) — FLOW
- `b34a`: `TST.B d0; BEQ.W b360` (→`b350`)
- `b350`: `MOVEA.L c(a6), a0; MOVE.B #3, 62(a0); JMP 2a00.l` — 부모 BYTE `62` := 3, self delete(`2a00`은 A7 := LONG `104ca4` 뒤 `2ac2`)
- `b360`: `RTS` — FLOW

**menu 항목 handler(결정 2) 25** — [F] 범위 이웃: `a758`까지 card_menu_open(`a73e..a758`), `a770..`(다른 함수, 미routing), `a8d0..`(다른 menu의 handler, LONG `a920`/`a97a`가 가리킴, 미routing).
- `a75a`: `JSR 9f36.l` (→`a760`) — FLOW
- `a760`: `MOVE.W d1, -(a7); MOVE.W d0, -(a7); JSR 38e8.l` (→`a76a`)
- `a76a`: `ADD.W (a7)+, d0; MOVE.W (a7)+, d1; RTS`
- `a856`: `BSR.W a73e` (→`a85a`) — FLOW
- `a85a`: `CMPI.W #3, d0; BEQ.B a868` (→`a860`)
- `a860`: `CMPI.W #2, d0; BNE.W a874` (→`a868`)
- `a868`: `BSR.W a75a` (→`a86c`) — FLOW
- `a86c`: `LEA.L a8f8(pc), a0; JMP a71a(pc)` — FLOW
- `a874`: `RTS` — FLOW
- `a876`: `BSR.W a73e` (→`a87a`) — FLOW
- `a87a`: `CMPI.W #3, d0; BEQ.B a888` (→`a880`)
- `a880`: `CMPI.W #2, d0; BNE.W a894` (→`a888`)
- `a888`: `BSR.W a75a` (→`a88c`) — FLOW
- `a88c`: `LEA.L a952(pc), a0; JSR a71a(pc)` (→`a894`) — FLOW
- `a894`: `RTS` — FLOW
- `a896`: `BSR.W a73e` (→`a89a`) — FLOW
- `a89a`: `CMPI.W #3, d0; BEQ.B a8a8` (→`a8a0`)
- `a8a0`: `CMPI.W #2, d0; BNE.W a8ba` (→`a8a8`)
- `a8a8`: `JSR 9f36.l` (→`a8ae`) — FLOW
- `a8ae`: `ADDQ.B #4, d0; SUBQ.B #2, d1; LEA.L aa24(pc), a0; JMP a71a(pc)`
- `a8ba`: `RTS` — FLOW
- `a8bc`: `BSR.W a73e` (→`a8c0`) — FLOW
- `a8c0`: `CMPI.W #3, d0; BNE.W a8ce` (→`a8c8`)
- `a8c8`: `JMP c00444.l` — FLOW, BIOS 종단
- `a8ce`: `RTS` — FLOW

## carry

- [F] **소비 2 + Z 소비 2:** `c87e` `c916`(`289e` known C), `c964` `c97a`(C1 결정 3). 들어오는 C가 Unknown이면 결정 8 오류.
- [F] **known 생산 0.** `c346`(할당 실패 여부)는 C를 읽지 않는다. 같은 block 안: `3162`(`CMPI.W #2` → `BCS`), `4823a`(`CMPI.W #13` → `BCS`).
- [F] **FLOW 52**(위 목록 태그, 자식 제외) + `b300` 쪽 FLOW 5(`b300` `b306` `b31a` `b344` `b360`) + handler 쪽 FLOW 15. 나머지 Unknown. handler의 flag는 모두 같은 block의 `CMPI`가 만든다(C 소비 0).
- [F] RTS block 뒤 호출자가 C를 읽는 곳: `4fb3c SCC`(C3, `28ae` 반환 C)뿐이고 C2 함수의 반환 C를 읽는 호출자는 없다([F] `xref.py` 호출자의 복귀 명령: `3162` → `MOVE.L`(`c64c`)/`BSR`(`c772` `c81a` `3110`), `47570` → `MOVE.B`(`c58a`)/`MOVE.W`(`c62c` `c7dc` `c854`)/`JSR`(`c890`), `49a1a` → `MOVE.B`(`c57c`)/`BSR`(`c61e` `c7ce` `c846`)/`MOVE.L`(`c826`), `c4cc` → `BSR`/`JSR`/`MOVEQ`(`c81e`)/`JMP`(`ca2c`), 범위 밖 `e676e` → `MOVEQ`(`e6774`)).

## 경계·I/O·스택

- [F] **port:** C2 자체는 없다. callee `caf0`(2,072건: `3c0000` LONG, watchdog `300001`, `3c0004`), `c4cc`의 `3dce`/`2a84` 계열(watchdog), `47570` 뒤 `47594` sound 큐(`3ac8` 계열)가 낸다. [F] 탐침 전환 frame의 controller port = `300001/1` 11, `3c0000/4` 2,062, `3c0004/2` 5.
- [F] **BIOS:** 결정 3·4. **대기:** callee 안 sound `3aea`(D6 선언 해제)만 가능하다([F] 탐침 전환 frame에서는 0회).
- [F] **쓰기:** controller node `62` `76`(C3 쪽) `7c`, `10f02a` `10f02c`, RNG 표 `1056b4..10571f`·`105722`, `104cc2..104cd4`, `10de14`/`10de1c`, `105680`/`105681`/`105683`/`105694`/`10569c`, `10000e`/`10089e`, `100017`, `10fdc4`/`10fdce`, `105d1e..105d2b`, 자식 node(`28ae` 실행부), stack.

## 자연 실행(탐침)

[F] 아래 "탐침 집계" 절의 수치. 자연 seed에 선언 없이(D9 (iii)) C2에 닿는 경로는 없다(controller가 `c560`에서 대기). D9 (ii)·(i) 구성에서 각각 `c76a…c79a`·`c686…c6c0`(+ `c6c8` 종단)과 `c4cc` `3162`가 자연 실행된다. 나머지(`c74c` `c7c6` `c80e..c982` `c2fa` `47570` `4823a` `49a1a` `4e1cc` `bbd4`)는 fixture 전용이다.

## 구현 범위와 규약

- routing: 결정 1(+2)의 범위(controller 13 + 자식·handler 3 = 16 범위). 내부 PC 직접 진입은 `unsupported animation controller c2 PC`다. `c690`은 block 시작이다(결정 1).
- executor는 C1과 같은 helper만 쓴다. `JMP c00444`는 PC 설정만 한다(결정 3). `JSR c00468`은 복귀 LONG push + PC 설정만 한다(결정 4).
- C2는 C1 뒤에 구현한다(C1 꼬리 `c988`, C1의 `4a974`·Z 규약을 쓴다). C3의 boot 경로는 C2 helper(`47570` `49a1a` `4823a` `3162` `c4cc`)를 쓴다.

## 시험·fixture 계획

- 단위 시험 `engine/tests/animation_machine_controller_c2_test.cpp`: 시작 128(+36) × C 3가지 block 표, zero-step, 내부 PC 전수, 홀수 PC, rollback 탐침 `10fexx`.
  - 전환 fixture: `c76a`(node 0·1·여러 개, 할당 성공·실패(free count 0)), `c686`(ROM180 = 0), `c79a` 4분기(`10fdb6`/`10fdb7` = 1, `62` = 0/2/3), `c7c6` 재시작(sound 대기 해제 포함), `c80e`→`c82e`(`10fd82`·`10fd8e` 조합)→`c874`/`c882`, `c890` 카드(BIOS 경계 정지), `c89c`/`c8e8`/`c940` 대기 0/≠0, `c948..c97e`(`10fd82` = 0 경로; ≠0은 C1 결정 5의 `c00450` 경계).
  - `3162`(D0 0/1/2/ffff), `4823a`(D0 `12`/`13`/`ffff`), `49a1a`(D0 0/≠0, `10f02c` `ffff` 넘침), `e62ec`(D0.B 0/≠0), `4e1cc`.
  - 종단 `c00444`(3곳): 실행부 수준에서는 `unsupported animation machine PC` rollback, 구동기 수준(D9 문서)에서 `animation frame controller system return`.
- 실제 ROM 차분: V1 fixture 검증기(`tools/verify_animation_machine_unit_fixtures.py`) spec. 입력은 (a) D9 (ii) 구성의 자연 전환 frame controller 진입 상태(136 seed 중 전환이 있는 seed 전부), (b) 같은 상태의 `c79a` 대기 frame, (c) 위 typed fixture. stop `2ac2`. 카드 resume(결정 4)은 V1 검증기의 `card` 해제가 `c37c`만 받으므로 `c316` 추가가 필요하다(V1 확장, 검증기 담당 작업).
- `b300`·handler(결정 2): (ii) 구성 전환 frame 다음 N pass의 node 진입 상태(callback `b300`/`b344`)에서 node 하나 차분(`seed_node_fixture`). handler는 card menu 실행부가 부르는 live 대상이므로 `b344` node 차분이 덮는다. 항목 선택 분기(D0 = 2/3)는 typed fixture(입력 queue로 menu 조작)로 덮는다.

## 탐침 집계

[F] scratch `p4.py`(자연 137 seed × 400 frame; D9 문서 §3.1).

| 구성 | C2 leader 실행 | 전환 | 전환 뒤 | 미routing node callback(N) |
| --- | --- | --- | --- | --- |
| (iii) 기록 | 0/128 | 없음 | | 없음 |
| (ii) 게임 | 19/128 | `c7fc`→`c79a` 136(frame 1: 8, 221: 4, 241: 35, 245: 89) | `c79a` 대기 23,132 frame, 136/136 완주 | `b300` 136, `b344` 23,132 |
| (i) demo | 15/128 | `c66a`→`c6c0` 136(같은 frame) | `c6c0` 대기 14,416 frame 뒤 `c6c8` → BIOS `c00444` 136 | `e66aa` 136, `e66ee` 4,624, `e673e` 9,792, `e6932` 12,376, `e6916` 2,040, `e68c6` 136 |

- [F] (ii) 실행 leader: `3162 3180 c4cc c4d2 c4d8 c4dc c4e6 c4ee c4f6 c76a c772 c776 c77a c77e c794 c79a c7a4 c7ae c7ba`. (i): `c4cc..c4f6` 7 + `c686 c69a c69e c6a2 c6a6 c6b6 c6c0 c6c8`. 합집합 27/128.
- [F] 전환 frame의 controller port(seed당): `3c0000/4` 2,062, `300001/1` 11, `3c0004/2` 5. controller 안 대기 0회. N의 card resume 130회는 선언 생략과 같다.
- [F] `c4cc` 반복(`c4dc`→`c4e6`→`c4ee`)은 전환 frame마다 6~7회였다(표본 case 0·94).
- [F] routing 밖 실행 code(`p5.py`, 실행된 모든 TB 범위의 각 짝수 PC를 현재 routing bitmap으로 검사):
  - 선언 생략(S) 기준 136 seed에서 routing 밖 PC는 53개다. 모두 기존 실행부 block 안의 내부 PC로, D1 C++ 검증이 덮는다.
  - (ii)에서 이 53개와 controller closure를 뺀 새 PC는 18개다. `a856..a8ce` 15개(handler, 첫 frame = 전환 + 4)와 `3900`·`e7c32`·`e84d2` 3개다. 뒤의 3개는 기존 실행부 block `38fe`·`e7c30`·`e84d0`의 명령 내부·끝 PC다(실행부가 덮음).
  - (iii)에서는 새 PC가 0개다.
  - 두 구성 모두 controller 복귀 시 A6 = `1008e4`, A7 = SPd였다(관측기 `skip_bad` 0).


## 미확인

- [U] 자식 `e66aa`(demo 끝, 72 leader, TRAP 2·간접 JSR 1)·`de660`(68)·`de024`·`de376`·`4fb64`의 의미와 routing 단위.
- [U] `b344`의 `a370`이 0이 아닌 값을 돌려주는 조건(입력·시간). 탐침 400 frame 안에서는 일어나지 않았다.
- [U] `10fdb6`/`10fdb7`(BIOS player start 상태 [I]), `10fd8e`, `104cb5` bit 0·2의 의미.
- [U] 자연 boot에서 `c76a`·`c80e` 이후 실제 흐름(IRQ·BIOS·입력이 있어야 한다).
