# F5 controller C1: 매 frame gate(`c66a`·`c7fc`)·공통 꼬리 `c988`·표시 helper 계약 초안

**상태: 구현 전 계약 초안 — 메인 결정 전.** 원본 바이트·scratch native 탐침 근거이며 구현·검증 기록이 아니다.

범위 근거는 F5 범위 문서(`animation-machine-frame-head-f5-scope.md`, SHA256 `973d45957731ff17ccf49537024307cf7fd20fe9270c9d9bb44a2bc553280fb0`)의 §4 C1 행(`c654..c686` `c988..ca22` `c49c..c52a` `ca32` `30bc` `30d4` `314c` `100e` `101c` `4a88e..4a9e0` `36ba`/`3706`, 116 block, 위험 `SBCD`·`JSR (A1)`)과 결정 D9/D10이다. D9 권고와 frame 구동기 변경은 `animation-machine-controller-d9-decision.md`가 정한다. 이 문서는 그 권고(선택 B(ii) 게임 mode 선언 + 기록 상태 무선언 구성)를 전제로 단위 경계를 다시 나눴다(결정 1).

Claude Opus 5.5 / high 읽기 전용 분석 작업자가 작성했다.
- canonical BE ROM `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, mtime `1791291625`(작업 전후 같음). C1 코드는 모두 fixed `<100000`이라 CPU 주소 = file offset이다.
- 작업 트리 `/home/user/ProjectSlugV`, branch `claude/projectslugv-work-cycle-yout6u`, HEAD `c49bcd2`(작업 중 `3b63864`에서 다른 작업자의 M1·V1 커밋이 더해짐; engine 파일은 바뀌지 않음). routing 원천 `engine/src/animation_machine.cpp` SHA256 `c7318132fcdfd288c12a58ab7e51c03e2920b46d7e939103bd917d72ca8caad2`(H1·H2·H3·H4·H8 포함). C1 범위의 짝수 PC는 기존 routing에 없다.
- 정적 leader는 scratch `ana_c/leaders.py`(capstone 5.0.6, F4 rescope와 같은 규칙: 진입, 분기 대상, 조건 분기 fall-through, `DBcc` 대상·fall-through, BSR/JSR 복귀점, `MOVE.L #imm,(A6)` 설치점; 이미 routing된 PC에서 걷기를 멈춤)로 `c52a`부터 controller closure 291개를 계산하고(범위 문서 298에서 H2 `3902` 6·H3 `4718` 1을 뺀 값과 같다), 범위로 C1/C2/C3에 나눴다(`units.py`).
- native 탐침은 scratch `ana_c/cprobe.py`다. 저장소 관측기 `observe_animation_machine_frame_head.HeadRun`을 in-process로 상속해 D1 protocol(H → controller → N)을 돌리되, H가 controller LONG `(1008e4)` 진입에서 멈추면 선언 생략 대신 controller를 Unicorn으로 실행해 PC `2ac2`·A7 = SPd(`1ff000`) 복귀에서 멈춘다. seed는 `verify_animation_machine_frame_driver.declared_rebase()`의 Linux 재생성 `stage_entry_body`(observation SHA256 `f74048bb…`)와 `R.prepared(case)`의 RNG 준비 상태다. 저장소 도구는 고치지 않았다.
- 표기: [F]=원본 바이트·기록 산출물·scratch 탐침에서 확인한 사실, [I]=추론, [U]=미확인. 탐침은 선언 모델이다. BIOS·자연 IRQ·자연 scheduler를 주장하지 않는다.

## 요약

- [F] **정적 leader 116개, 12 범위 858바이트(짝수 PC 429개).** 범위 문서 C1 행과 수는 같지만 구성이 다르다(결정 1): `c4cc`(7, 전체 node 해체), `100e`(1), `101c`(1)을 C2로 보내고, 매 frame 경로가 지나는 `c724..c74c`(6, mode 검사)와 게임 mode gate `c7fc..c80e`(3)를 C2에서 가져왔다.
- [F] **C1은 "controller가 매 frame 하는 일"이다.** 탐침에서 controller가 상태를 바꾸지 않는 frame의 경로는 모두 C1 안에서 끝난다.
  - 게임 mode(D9 (ii), `1008e4` = `c7fc`): `c7fc`(`289e`로 `100b30` callback ≠ `270e` 확인) → `c806 BCS` → 꼬리 `c988..ca20` → RTS. block 14~23개, RAM 변경 3바이트(controller 필드·stack), port 0.
  - demo mode(D9 (i), `c66a` + `104cd4` = 1): `c66a` → `314c`(BYTE `104cd4` = 1) → `c724` → (BYTE `81(A6)` ≠ 0이면 `c49c` credit 표시) → 꼬리. block 21~46개, 표시 frame은 `3c0000` port 40건.
  - controller 전환(`c686`, `c76a`)·`c74c`(게임 시작)는 C2, boot·title은 C3이다.
- [F] **경계(C1이 실행하지 않는 곳):** 이미 routing된 callee `289e`(readiness) `2a28`(cleanup) `3918`(card_menu_open, `c4c4 JMP` 꼬리 호출) `3902`(H2) `35f0`(hud) `3650`(card_menu_open, `JSR (A1)` 대상), C2 진입 `c686`(`c674`/`c67e`) `c74c`(`c724`/`c73e`, BYTE `100012` = 2) `c76a`(`c80a JMP`), BIOS `JSR c00450`(`4a98c`, BYTE `10fd82` ≠ 0일 때만).
- [F] **carry·flag 소비가 있다(H 단위와 다름).** C 소비 block 6개(`c4a0` `c674` `c67e` `c806` `c996` `c9ba`)는 callee RTS의 known C(`ca32` CMPI, `289e`, `314c`, `30bc`, `30d4`)를 읽는다. **RTS를 넘는 Z 소비 2곳**(`4a9d0` `4a9da`, C2에 2곳 더: `c964` `c97a`)은 기존 carry 상태 모델로 표현되지 않는다(결정 3).
- [F] **특수 연산:** `ca06 SBCD.B D2,D1`(X는 같은 block `SUBQ.B #8,D0`), `c50e MOVE.B …,-(A7)`(A7 −2, byte push), `JSR (A1)` 2곳(`36b0` `36fa`, A1 = `3650`).
- [F] **device:** 쓰기 없음(VRAM은 callee `3650`/`35f0`/`3918`이 쓴다). 읽기 `d00034`(MVS backup RAM, `4a89e`/`4a954`, BYTE `10fd82` ≠ 0이고 BYTE `10fe80` = 0일 때)뿐이며 자연 seed에서는 닿지 않는다(결정 5).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **단위 경계 재배치(116 = 116).** [F] 범위 문서의 C1/C2 경계는 주소 범위 기준이었다. D9 권고(게임 mode `c7fc` 매 frame)에서는 `c7fc..c80e`가 매 frame 경로이고 `c4cc`는 전환에서만 실행된다. 제안: C1 = 아래 12 범위. `c80a JMP c76a`(전환)와 `c724`/`c73e`의 `BEQ c74c`, `c674`/`c67e`의 `BCC c686`은 C2 진입 경계다(C2 전에는 `unsupported animation machine PC`, rollback).
   - routing: `30bc..30ec` `314c..3162` `3670..370c` `c49c..c4cc` `c4f8..c52a` `c654..c686` `c724..c74c` `c7fc..c80e` `c988..ca22` `ca32..ca3a` `4a88e..4a8f8` `4a944..4a9e2`.
   - 범위 밖 이웃: `30ec..30f4`(`BRA.B`+표 자료, 다른 함수) `3144..314c`(`MOVE.W D0,104cd2`, 참조 별도) `366e`까지 card_menu_open(`3650..366e`) `370c..`(숫자 글꼴 표 자료) `4a8f8..4a90e`(문자열 `"CREDITS  "` 등 자료) `4a90e..4a944`(다른 함수, controller에서 부르지 않음) `ca22..ca32`(다른 함수 `ca22 JSR 9056; JSR c4cc; JMP b362`, 참조 없음 [F] `xref.py`) `ca3a..`(다른 함수).
2. **진입 PC와 live 진입.** [F] callback 설치점: `c654`(C3 `c64c`가 설치), `c66a`(`c664`), `c7fc`(C2 `c7f6`). 함수 진입: `30bc`(`c990`) `30d4`(`c9b4`) `314c`(`c678`) `36ba`(23곳: `8f54` `c712` `4a8f2 JMP` `498d4`… [F] `xref.py`) `3706`(`ab14` `c520`) `c49c`(`c736`) `c4f8`(`c9be`) `ca32`(`c49c` + 범위 밖 `4e758` `4e802`) `4a88e`(`c9a6`) `4a944`(`c9c8`) `4a974`(`c95e` `c974` `4a9ce` `4a9d8` + 범위 밖 `4e774` `4eb7e` `4ee2a` `de932`) `4a9ca`(`c4a4` + `4eb88`). C1 routing 뒤에는 범위 밖 호출자(아직 미routing 단위)도 이 실행부로 들어온다. 공유 helper(`36ba` `4a974` `ca32`)의 반환 C·Z 규약(결정 3)은 그 호출자에게도 같게 적용한다.
3. **RTS를 넘는 Z 소비(새 규약).** [F] `4a974`는 `4a9b0`/`4a9c6`(`TST.B (A0); RTS`)로 끝나고, 호출자 복귀 block `4a9d0` `4a9da`(C1)·`c964` `c97a`(C2)는 첫 명령 `BEQ`/`BNE`로 그 Z를 읽는다. 범위 밖 호출자 4곳도 같은 형태다([F] 복귀 명령 `4e77a BEQ` `4eb84 BNE` `4ee30 BEQ` `de938 BEQ`). `ca32`의 범위 밖 호출자 `4e758`/`4e802`는 복귀점에서 `SCS.B D0`로 C를 읽고, `4a9ca`의 `4eb88`은 `TST.B D7`(flag 생산)이다. `AnimationMachineState`는 C만 운반한다.
   - 제안 A(**작업자 권고**, public header 변경 없음): 복귀 block이 Z를 **BYTE (A0) 재읽기**로 다시 계산한다(Z = (BYTE(A0) = 0)). [F] 근거: `4a974`의 A0는 `LEA 7db0(A5)`(= `10fdb0`) 또는 `LEA 100004`에 `ADDA.W D0`(D0 ∈ {0,1}, `ANDI.W #1`)만 더한 값이라 work RAM `10fdb0`/`10fdb1`/`100004`/`100005` 중 하나다. `RTS`는 stack(`1fefxx` = RAM `10efxx` 미러)만 읽으므로 그 사이 쓰기가 없다. 재읽기는 RAM 읽기라 효과가 없다. guard: 복귀 block 진입 시 A0가 RAM(`100000..1fffff`)이 아니면 `unsupported animation controller flag source`(checked, rollback). 직접 진입 시험은 A0를 RAM으로 둔다.
   - 제안 B: `4a9b0`/`4a9c6`을 복귀 block과 "융합"(callee RTS 뒤 복귀 PC의 첫 Bcc까지 한 block). 호출자가 여럿이라 실행부 사이 결합이 생기므로 비권고.
   - 제안 C: `AnimationMachineState`에 Z 상태를 더하는 public header 변경. 기존 실행부 전부의 Z 규약을 정해야 하므로 비권고.
4. **`JSR (A1)` live 대상.** [F] `36a2`/`36ec`의 `JSR (A1)`에서 A1은 `36ba`/`3706`의 `LEA 3650(PC),A1`로만 정해진다(정적, 함수 진입 경로 2개). 직접 진입(`3670`/`36c0`, 범위 밖 `JMP 36ba` 경로 포함)에서 A1은 live 값이다. H1 결정 5와 같이 live 대상으로 둔다: 복귀 LONG push(`36b2`/`36fc`) 뒤 PC := A1, routing에 맡긴다(홀수면 `unaligned animation machine PC`, 미routing이면 `unsupported animation machine PC`). 자연 대상 `3650`은 card_menu_open 실행부다.
5. **BIOS·backup RAM 경계.**
   - `4a982 JSR c00450`(CREDIT_CHECK [I]): 실행부는 `MOVE.L #01010000,10fdb0`, WORD push D0, JSR(복귀 LONG `4a992` push, PC := `c00450`)까지 하고, PC `c00450`은 routing 밖이라 `unsupported animation machine PC`로 끝난다. **선언 resume은 frame 구동기가 한다**(D9 문서 §5.3, card resume과 같은 재실행 방식): stop `c00450`에 닿고 LONG(A7) = `4a992`이면 선언 응답 LONG `10fdb0` := `credit_answer`(기본: 현재 값 유지 = `01010000`), PC := `4a992`, A7 += 4, C Unknown. [F] 자연 seed는 BYTE `10fd82` = 0이라 닿지 않는다.
   - `d00034` 읽기(`4a89e`/`4a954` → `4a8b0`/`4a966`의 `(A1)` 읽기, BYTE `10fd82` ≠ 0 그리고 BYTE `10fe80` = 0): 제안은 checked 오류 `unsupported animation controller backup RAM read`(상태 보존)다. 대안은 external read queue 확장(`d00034`/1, `d00034`/2)인데 MVS backup RAM 모델이 없으므로 비권고. [F] 자연 seed는 닿지 않는다.
6. **byte push `-(A7)`.** [F] `c50e MOVE.B 10fd8b.l,-(A7)`은 68000 규칙대로 A7을 2 줄이고 BYTE를 (A7)(상위 바이트)에 쓴다. `ADDQ.B #1,(A0)`(A0 = A7)는 그 BYTE만 바꾸고, `c526 MOVE.B (A7)+,D0`는 A7을 2 늘린다. 실행부는 A7 홀수·device 범위를 기존 stack helper 오류로 처리한다.
7. **`SBCD` 정밀 의미.** [F] `ca06`: D0.W := WORD `7a(A6)`; D1.B := BYTE `7a(A6)`; D2 := 0; `SUBQ.B #8,D0`(X = C = 빌림); `SBCD.B D2,D1`(D1.B := D1.B − 0 − X, BCD); C(=X)가 0이면 `ca18`, 1이면 `ca14`(D0 := D1 := 0). 68000의 SBCD는 BCD가 아닌 입력(nibble ≥ A)에도 정해진 결과를 낸다. 실행부는 Musashi `m68k_op_sbcd_8_rr` 규칙(저 nibble 보정 `−6`, 고 nibble 보정 `−0x60`, C = 결과가 `0x99`를 넘는 빌림)을 그대로 따르고 N/Z/V는 쓰지 않는다(소비자 없음). 시험은 D1.B 256값 × X 2값 전수(결정 9).
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_controller_c1.cpp`의 `animation_controller_c1_block`. 오류: `unsupported animation controller c1 PC`(범위 안 내부 PC), `unsupported animation controller flag source`(결정 3 guard), `unsupported animation controller backup RAM read`(결정 5). carry 소비 block은 들어오는 C가 Unknown이면 `controller c1 caller requires known carry`(checked, rollback; 기존 `readiness caller requires known carry`·`objects n12 caller requires known carry` 등과 같은 어휘).
9. **무효화 탐침.** [F] 정적 검색(scratch, `engine/tests/*.cpp` `engine/tools/*.cpp` `tools/verify_*.py`): C1 PC를 "routing 밖" 탐침으로 쓰는 시험은 없다. `c66a`는 `animation_machine_frame_head_h1_test.cpp`(`d1-c66a`, stop)와 `animation_machine_frame_test.cpp`(선언 생략 기대, 결정 D9의 기본 Skip에서 유효)에서 stop/선언 controller 값으로만 쓰인다. `game_ready_test.cpp`·`tools/verify_game_ready.py`는 host 수준 API(`step_game_ready`)의 진입 PC로 쓰므로 영향이 없다. 구현 뒤 `make all test`로 다시 확인한다.

## 원본 바이트 근거

[F] C1 코드 12 범위 858바이트. 연결 SHA256 `50af8fd097fadeba206afa036e8acd18bd312166aa92992b1e9f58439cdd9761`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `30bc..30ec` | 48 | `c757d0ca5eefe53e2c11fb5f0627f39a98f15280ae94815ca3fb251f883a3f2d` | 6 |
| `314c..3162` | 22 | `bc0b6cf69e5112c7941bba638f0155c571dff928197598928f03e526520d4b58` | 3 |
| `3670..370c` | 156 | `2ea6ab37683936b2e269cded1d79522ea461edd87b4a5a255883f01d5a63e4fc` | 25 |
| `c49c..c4cc` | 48 | `c2b953387685f7c28ed200e095b570cf8e5bbfbea17e46afd17b6bc5d5a75162` | 6 |
| `c4f8..c52a` | 50 | `c1b4aebb0ba612cc97e0a6e6bb4acbc025155321a1cacc414fc68b41cd53f488` | 3 |
| `c654..c686` | 50 | `f334e2d9f68ecae08368156c9b16821c138e864c9179afe6a27a49b88421b514` | 7 |
| `c724..c74c` | 40 | `1ccb8d90f6092751632e2b37a5a4355e68f584681c14e2205049e21d5bb51d2f` | 6 |
| `c7fc..c80e` | 18 | `a2fcd9f3da16bf09e1b41526eda4496f01dc5da7a5611c036ae3b64e090b98fd` | 3 |
| `c988..ca22` | 154 | `a70632de3910f86f34cb15336455ec118e6df9d9c432c602fbd97c90d481bd2b` | 21 |
| `ca32..ca3a` | 8 | `d4c383e676181011dd14459f939a5d0bdad0c70ca3e25d4b22086bad783f1a68` | 1 |
| `4a88e..4a8f8` | 106 | `a0063b17e2bc9e8a06a26d3062efcd33113a448e6df77fa641f6a1fa50738f7b` | 12 |
| `4a944..4a9e2` | 158 | `6d0b6c0eb40894792dfa4dcf91d2769eedc3124587b70b9b0529375653c3284e` | 23 |

- [F] 자료: `c46e`(`c4b6 LEA`의 문자열 A0), `c48c..c49c`(LONG 표 4항목, `c4ae MOVEA.L c48c(PC,D7.W)`; D7 = `4a9ca`가 만든 bit 0..1 × 4 → 0..12), `370c..`(숫자→글자 BYTE 표, `36a4`/`36ee`의 `(A0,D2.W)`, D2.W ∈ 0..16), `4a8f8`·`4a903`(문자열). 표 읽기는 live bus(ROM)다.
- [F] `c4ba..c4c4`: D0.W := `7157`(fix layer 주소 [I]), A1 := `e84c8`(card_menu_open 실행부 범위 `e84c8..e84d0`의 글꼴 callback [I]), `JMP 3918`(꼬리 호출; 복귀는 `c736 BSR`의 `c73a`).

## block 목록과 실행 의미

표기는 H1 계약과 같다: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "FLOW"(CCR 보존 명령과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`만, C 보존), "C:=1/0 반환"(`ORI`/`ANDI` CCR 뒤 RTS, known C 생산), "C 소비(x)"·"Z 소비"(결정 3). 태그 없는 block은 Unknown이다. d16(An)·`(An,Dn.W)`는 부호 확장한다. A5 = `108000`(`-74d0(A5)` = `100b30`, `-7fee(A5)` = `100012`, `-7ffc(A5)` = `100004`, `-7ffd(A5)` = `100003`, `7d82(A5)` = `10fd82`, `7e80(A5)` = `10fe80`, `7e00(A5)` = `10fe00`, `7db0(A5)` = `10fdb0`, `-769c(A5)` = `100964`, `-332c(A5)` = `104cd4`).

**BIOS soft-dip bit 검사 `30bc`/`30d4`(`c990`/`c9b4`) 6** — [I] BYTE `10fd8f`는 BIOS game soft-dip 영역(`10fd84..10fd93`)이다.
- `30bc`: `BTST.B #1, 10fd8f.l; BEQ.W 30ce` (→`30c8`) — FLOW
- `30c8`: `ORI.B #1, ccr; RTS` — C:=1 반환
- `30ce`: `ANDI.B #fe, ccr; RTS` — C:=0 반환
- `30d4`: `BTST.B #0, 10fd8f.l; BEQ.W 30e6` (→`30e0`) — FLOW
- `30e0`: `ORI.B #1, ccr; RTS` — C:=1 반환
- `30e6`: `ANDI.B #fe, ccr; RTS` — C:=0 반환

**입력 replay mode 검사 `314c`(`c678`) 3**
- `314c`: `CMPI.B #1, -332c(a5); BNE.W 315c` (→`3156`) — C는 `ORI`/`ANDI`가 덮으므로 CMPI의 C는 쓰지 않는다.
- `3156`: `ORI.B #1, ccr; RTS` — C:=1 반환
- `315c`: `ANDI.B #fe, ccr; RTS` — C:=0 반환

**BCD 숫자 표시 `36ba`/`3706`(공유 25)** — D4 = 자릿수, A0 = BCD 바이트열, D2 = 글자 색인, `JSR (A1)`(A1 = `3650`)이 한 글자를 그린다. `36ba`는 앞자리 0도 그리고(`D3` 초기값 유지), `3706`은 앞자리 0을 건너뛴다(`36c0 CLR.B D3`).
- `3670`: `MOVE.B (a0), d2; BTST.B #0, d4; BNE.W 3680` (→`367a`)
- `367a`: `LSR.B #4, d2; BRA.W 3682`
- `3680`: `ADDQ.W #1, a0` (→`3682`) — FLOW
- `3682`: `ANDI.W #f, d2; BNE.B 3690` (→`3688`)
- `3688`: `CMPI.W #1, d4; BNE.W 3698` (→`3690`)
- `3690`: `MOVE.B #ff, d3; BRA.W 36a2`
- `3698`: `TST.B d3; BNE.W 36a2` (→`369e`)
- `369e`: `MOVE.B #10, d2` (→`36a2`)
- `36a2`: `MOVE.L a0, -(a7); LEA.L 370c(pc), a0; MOVE.B (a0, d2.w), d2; LEA.L 3650(pc), a0; JSR (a1)` (→`36b2`) — 결정 4
- `36b2`: `MOVEA.L (a7)+, a0; SUBQ.W #1, d4; BNE.B 3670` (→`36b8`)
- `36b8`: `RTS` — FLOW
- `36ba`: `LEA.L 3650(pc), a1; BRA.B 3670` — FLOW
- `36c0`: `CLR.B d3` (→`36c2`)
- `36c2`: `MOVE.B (a0), d2; BTST.B #0, d4; BNE.W 36d2` (→`36cc`)
- `36cc`: `LSR.B #4, d2; BRA.W 36d4`
- `36d2`: `ADDQ.W #1, a0` (→`36d4`) — FLOW
- `36d4`: `ANDI.W #f, d2; BNE.B 36e2` (→`36da`)
- `36da`: `CMPI.W #1, d4; BNE.W 36e6` (→`36e2`)
- `36e2`: `MOVE.B #ff, d3` (→`36e6`)
- `36e6`: `TST.B d3; BEQ.W 36fe` (→`36ec`)
- `36ec`: `MOVE.L a0, -(a7); LEA.L 370c(pc), a0; MOVE.B (a0, d2.w), d2; LEA.L 3650(pc), a0; JSR (a1)` (→`36fc`) — 결정 4
- `36fc`: `MOVEA.L (a7)+, a0` (→`36fe`) — FLOW
- `36fe`: `SUBQ.W #1, d4; BNE.B 36c2` (→`3702`)
- `3702`: `SWAP d0; RTS`
- `3706`: `LEA.L 3650(pc), a1; BRA.B 36c0` — FLOW

**credit 문구 표시 `c49c`(`c736`) 6, credit 수 표시 `c4f8`(`c9be`) 3, 표시 조건 `ca32` 1**
- `c49c`: `JSR ca32(pc)` (→`c4a0`) — FLOW
- `c4a0`: `BCC.W c4b6` (→`c4a4`) — FLOW, C 소비(`ca32` CMPI: BYTE `100964` < `aa`(무부호)이면 C = 1)
- `c4a4`: `JSR 4a9ca.l` (→`c4aa`) — FLOW
- `c4aa`: `ADD.W d7, d7; ADD.W d7, d7; MOVEA.L c48c(pc, d7.w), a0; BRA.W c4ba`
- `c4b6`: `LEA.L c46e(pc), a0` (→`c4ba`) — FLOW
- `c4ba`: `MOVE.W #7157, d0; LEA.L e84c8.l, a1; JMP 3918.l` — 꼬리 호출, 복귀는 호출자의 복귀점
- `c4f8`: `MOVE.W #723d, d0; MOVE.W #b5a, d1; MOVE.W #5, d2; MOVE.W #1, d3; JSR 35f0.l` (→`c50e`)
- `c50e`: `MOVE.W #3, d1; MOVE.B 10fd8b.l, -(a7); MOVEA.L a7, a0; ADDQ.B #1, (a0); MOVE.W #1, d4; JSR 3706.l` (→`c526`) — 결정 6
- `c526`: `MOVE.B (a7)+, d0; RTS` — 결정 6
- `ca32`: `CMPI.B #aa, -769c(a5); RTS` — C 계산 반환(CMPI)

**demo gate `c654`/`c66a` 7** — [I] attract demo 감시(`input-sampler.md`: `104cd4` 1 = replay).
- `c654`: `LEA.L -74d0(a5), a0; LEA.L 477e4.l, a1; JSR 2a28.l` (→`c664`) — FLOW. `100b30`을 callback `477e4`로 정적 재시작(cleanup 실행부).
- `c664`: `MOVE.L #c66a, (a6)` (→`c66a`) — 설치점
- `c66a`: `LEA.L -74d0(a5), a0; JSR 289e.l` (→`c674`) — FLOW
- `c674`: `BCC.W c686` (→`c678`) — FLOW, C 소비(`289e`: callback ≠ `270e`이면 C = 1). `c686`은 C2 경계.
- `c678`: `JSR 314c.l` (→`c67e`) — FLOW
- `c67e`: `BCC.W c686` (→`c682`) — FLOW, C 소비(`314c`)
- `c682`: `BRA.W c724` — FLOW

**mode 검사 `c724`/`c73e` 6** — BYTE `100012`(`b68`이 매 frame BIOS `10fdaf`를 복사) = 2(게임)이면 C2 `c74c`(게임 시작).
- `c724`: `CMPI.B #2, -7fee(a5); BEQ.W c74c` (→`c72e`)
- `c72e`: `TST.B 81(a6); BEQ.W c988` (→`c736`)
- `c736`: `BSR.W c49c` (→`c73a`) — FLOW
- `c73a`: `BRA.W c988` — FLOW
- `c73e`: `CMPI.B #2, -7fee(a5); BEQ.W c74c` (→`c748`)
- `c748`: `BRA.W c988` — FLOW

**게임 mode gate `c7fc` 3** — [I] stage 진행 중 매 frame 상태.
- `c7fc`: `LEA.L -74d0(a5), a0; JSR 289e.l` (→`c806`) — FLOW
- `c806`: `BCS.W c988` (→`c80a`) — FLOW, C 소비(`289e`)
- `c80a`: `JMP c76a(pc)` — FLOW. `c76a`는 C2 경계(stage 종료 전환).

**매 frame 꼬리 `c988..ca20` 21** — controller node 필드: `+78` WORD 감소 계수기, `+7a..+7b` BCD 타이머(초·frame [I]), `+7e` 직전 credit 값, `+80` 깜박임 계수기, `+81` credit 표시 flag, `+82` 직전 `+81`, `+83` 타이머 정지 flag.
- `c988`: `TST.B 81(a6); BEQ.W c9c2` (→`c990`)
- `c990`: `JSR 30bc.l` (→`c996`) — FLOW
- `c996`: `BCC.W c9ac` (→`c99a`) — FLOW, C 소비(`30bc`)
- `c99a`: `MOVE.W #709d, d0; MOVE.W #737d, d2; MOVE.W #3, d1; JSR 4a88e.l` (→`c9ac`)
- `c9ac`: `TST.B 82(a6); BNE.W c9c2` (→`c9b4`)
- `c9b4`: `JSR 30d4.l` (→`c9ba`) — FLOW
- `c9ba`: `BCC.W c9c2` (→`c9be`) — FLOW, C 소비(`30d4`)
- `c9be`: `BSR.W c4f8` (→`c9c2`) — FLOW
- `c9c2`: `MOVE.B 81(a6), 82(a6); JSR 4a944.l` (→`c9ce`)
- `c9ce`: `CMP.W 7e(a6), d0; BEQ.W c9de` (→`c9d6`)
- `c9d6`: `MOVE.W d0, 7e(a6); CLR.B 80(a6)` (→`c9de`)
- `c9de`: `ADDQ.B #6, 80(a6); MOVE.W 78(a6), d0; BEQ.W c9f6` (→`c9ea`)
- `c9ea`: `SUBQ.W #4, d0; BCC.W c9f2` (→`c9f0`) — C는 같은 block의 `SUBQ`
- `c9f0`: `MOVEQ #0, d0` (→`c9f2`)
- `c9f2`: `MOVE.W d0, 78(a6)` (→`c9f6`)
- `c9f6`: `TST.B 83(a6); BNE.W ca20` (→`c9fe`)
- `c9fe`: `MOVE.W 7a(a6), d0; BEQ.W ca20` (→`ca06`)
- `ca06`: `MOVE.B 7a(a6), d1; MOVEQ #0, d2; SUBQ.B #8, d0; SBCD.B d2, d1; BCC.W ca18` (→`ca14`) — 결정 7
- `ca14`: `MOVEQ #0, d0; MOVEQ #0, d1` (→`ca18`)
- `ca18`: `MOVE.B d0, 7b(a6); MOVE.B d1, 7a(a6)` (→`ca20`)
- `ca20`: `RTS` — FLOW. 자연 복귀는 dispatcher `2ac2`(controller segment stop).

**credit 표시 `4a88e`(`c9a6`) 12** — D0 = fix 주소, D2 = 둘째 주소, A1 = credit 바이트(`100004`, MVS면 `d00034`/`10fe00`).
- `4a88e`: `TST.B 7d82(a5); BNE.W 4a89e` (→`4a896`)
- `4a896`: `LEA.L -7ffc(a5), a1; BRA.W 4a8b0` — FLOW
- `4a89e`: `LEA.L d00034.l, a1; TST.B 7e80(a5); BEQ.W 4a8b0` (→`4a8ac`)
- `4a8ac`: `LEA.L 7e00(a5), a1` (→`4a8b0`) — FLOW
- `4a8b0`: `TST.B 100003.l; BEQ.W 4a8cc` (→`4a8ba`)
- `4a8ba`: `MOVE.W d2, -(a7); MOVE.L a1, -(a7); BSR.W 4a8ce` (→`4a8c2`)
- `4a8c2`: `MOVEA.L (a7)+, a1; MOVE.W (a7)+, d0; ADDQ.W #1, a1; BRA.W 4a8ce`
- `4a8cc`: `MOVE.W d2, d0` (→`4a8ce`)
- `4a8ce`: `LEA.L 4a903(pc), a0; CMPI.B #2, (a1); BCC.W 4a8de` (→`4a8da`) — `(A1)` 읽기(결정 5 guard 대상)
- `4a8da`: `LEA.L 4a8f8(pc), a0` (→`4a8de`) — FLOW
- `4a8de`: `MOVE.L a1, -(a7); JSR 3902.l` (→`4a8e6`)
- `4a8e6`: `SUBI.W #40, d0; MOVEA.L (a7)+, a0; MOVEQ #ff, d3; MOVE.W #2, d4; JMP 36ba.l` — 꼬리 호출

**credit 값 `4a944`(`c9c8`) 7, credit 확인 `4a974` 9, 두 player bit `4a9ca` 7**
- `4a944`: `TST.B 7d82(a5); BNE.W 4a954` (→`4a94c`)
- `4a94c`: `LEA.L -7ffc(a5), a1; BRA.W 4a966` — FLOW
- `4a954`: `LEA.L d00034.l, a1; TST.B 7e80(a5); BEQ.W 4a966` (→`4a962`)
- `4a962`: `LEA.L 7e00(a5), a1` (→`4a966`) — FLOW
- `4a966`: `MOVE.W (a1), d0; TST.B -7ffd(a5); BNE.W 4a972` (→`4a970`) — `(A1)` 읽기(결정 5)
- `4a970`: `MOVE.B (a1), d0` (→`4a972`)
- `4a972`: `RTS` — FLOW
- `4a974`: `ANDI.W #1, d0; TST.B 10fd82.l; BEQ.W 4a9b4` (→`4a982`)
- `4a982`: `MOVE.L #1010000, 7db0(a5); MOVE.W d0, -(a7); JSR c00450.l` (→`4a992`) — BIOS 경계(결정 5)
- `4a992`: `MOVE.W (a7)+, d0; LEA.L 108000.l, a5; LEA.L 7db0(a5), a0; TST.B -7ffd(a5); BNE.B 4a9ae` (→`4a9a4`)
- `4a9a4`: `CMPI.B #2, -7fee(a5); BEQ.W 4a9b0` (→`4a9ae`)
- `4a9ae`: `ADDA.W d0, a0` (→`4a9b0`) — FLOW
- `4a9b0`: `TST.B (a0); RTS` — Z 생산(결정 3)
- `4a9b4`: `LEA.L 100004.l, a0; TST.B 100003.l; BEQ.W 4a9c6` (→`4a9c4`)
- `4a9c4`: `ADDA.W d0, a0` (→`4a9c6`) — FLOW
- `4a9c6`: `TST.B (a0); RTS` — Z 생산(결정 3)
- `4a9ca`: `MOVEQ #0, d7; MOVEQ #0, d0; BSR.B 4a974` (→`4a9d0`)
- `4a9d0`: `BEQ.W 4a9d6` (→`4a9d4`) — FLOW, Z 소비(결정 3)
- `4a9d4`: `BSET.B d0, d7` (→`4a9d6`) — FLOW
- `4a9d6`: `MOVEQ #1, d0; BSR.B 4a974` (→`4a9da`)
- `4a9da`: `BEQ.W 4a9e0` (→`4a9de`) — FLOW, Z 소비(결정 3)
- `4a9de`: `BSET.B d0, d7` (→`4a9e0`) — FLOW
- `4a9e0`: `RTS` — FLOW

## carry

- [F] **소비 6 + Z 소비 2.** `c4a0`(`ca32`), `c674`(`289e`), `c67e`(`314c`), `c806`(`289e`), `c996`(`30bc`), `c9ba`(`30d4`). 모두 들어오는 C가 known이어야 한다. 자연 경로에서는 바로 앞 callee RTS가 known C를 남긴다: `289e`는 readiness 실행부가 `return_carry`(같음 = Clear, 다름 = Set)로, `ca32`·`30bc`·`30d4`·`314c`는 이 단위가 known으로 반환한다. 들어오는 C가 Unknown이면 결정 8 오류다.
- [F] **known 생산 7.** `30c8` `30e0` `3156`(Set), `30ce` `30e6` `315c`(Clear), `ca32`(CMPI.B `#aa`의 빌림: BYTE `100964` < `aa`).
- [F] **같은 block 안에서 만들고 쓰는 C:** `c9ea`(`SUBQ`), `ca06`(`SUBQ`의 X → `SBCD`의 C), `4a8ce`(`CMPI`). 그 밖의 Bcc는 Z/N만 읽는다.
- [F] **FLOW 43**(C 보존): 위 목록의 FLOW 태그. 나머지 Unknown. 이 단위의 RTS block(`36b8` `ca20` `4a972` `4a9e0`) 뒤 범위 안 호출자는 C를 읽지 않는다. `ca32`는 범위 밖 `4e758`/`4e802`의 `SCS`가 C를 읽으므로 known C 반환이 필수다.

## 경계·I/O·스택

- [F] **callee(실행하지 않음):** `289e`(readiness) `2a28`(cleanup, `c654`) `3902`(H2, `4a8e0`) `3918`(card_menu_open, `c4c4 JMP`) `35f0`(hud, `c508`) `3650`(card_menu_open, `JSR (A1)`). BIOS `c00450`(결정 5).
- [F] **다른 단위로 가는 분기:** `c686`(C2, `c674`/`c67e`), `c74c`(C2, `c724`/`c73e`), `c76a`(C2, `c80a`). `c724`·`c73e`·`c988`은 C2·C3에서도 들어온다(`c5f4` `c608` `c718` `c6c4` `c7bc` 등).
- [F] **읽기:** RAM 필드(`100b30` callback, `104cd4`, `100012`, `100964`, `10fd82`, `10fd8b`, `10fd8f`, `10fe80`, `100003`, `100004..5`, `10fdb0..1`, controller node `+78..+83`), ROM 표(`c48c` `370c`), device `d00034`(결정 5).
- [F] **쓰기:** controller node `+78` `+7a` `+7b` `+7e` `+80` `+82`, `10fdb0` LONG(`4a982`, BIOS 경로), stack(JSR 복귀, WORD/LONG push, byte push).
- [F] **port:** C1 자체는 없다. 표시 callee(`3650` `35f0` `3918`)가 `3c0000` LONG/WORD를 쓴다(탐침: demo 표시 frame 40건 = `3c0000/4` 20 + `3c0000/2` 20).
- [F] **대기:** 없다. TRAP 없다.

## 자연 실행(탐침)

[F] scratch `p2.py`/`p4.py`(natural seed, 400 frame, continuous). 아래 "선언"은 frame 1의 H 시작 전 host 쓰기다.

| 구성 | 매 frame 경로(C1) | 비고 |
| --- | --- | --- |
| (ii) 게임: LONG `1008e4` := `c7fc`, BYTE `10fdaf` := 2 | `c7fc c806 c988 c9c2 4a944 4a94c 4a966 4a970 4a972 c9ce c9de c9f6 c9fe ca20`(14), `81(A6)` ≠ 0 frame은 `c990 30bc 30ce c996 c9ac c9b4 30d4 30e6 c9ba`가 더해짐 | 전환 frame에서 `c80a` → C2 |
| (i) demo: LONG `1008e4` := `c66a`, BYTE `104cd4` := 1 | `c66a c674 c678 314c 3156 c67e c682 c724 c72e …`(21), `81(A6)` ≠ 0이면 `c736 c49c ca32 c4a0 c4a4 4a9ca 4a974 4a9b4 4a9c6 4a9d0 …`(46) | 전환 frame에서 `c674` → C2 `c686` |
| (iii) 기록(무선언, `c52a`) | 없음(C3 `c560` 대기만) | |

- [F] 자연 137 seed 집계에서 C1 leader가 실행된 수: (ii) 24, (i) 49, 합집합 52/116(아래 "탐침 집계").
- [F] 자연 seed의 BYTE `10fd82` = 0이므로 `4a89e` `4a8ac` `4a954` `4a962` `4a982` `4a992` `4a9a4` `4a9ae` `4a9b0`과 BIOS `c00450`은 fixture 전용이다. BYTE `100003` = 0이라 `4a8ba` `4a8c2` `4a9c4` 쪽도 fixture 전용이다.

## 구현 범위와 규약

- routing: 결정 1의 12 범위(짝수 PC 429, 시작 116, 내부 313). 내부 PC 직접 진입은 `unsupported animation controller c1 PC`다.
- executor: block 하나 = 위 목록 한 줄. 기존 helper(`am_read`/`am_write`/`am_call`/`am_return`/`return_carry`/stack push·pop)만 쓴다. `JSR (A1)`·`JMP 3918`·`JMP 36ba`는 기존 `am_call`/PC 설정이다.
- 공유 최소 수정: `animation_machine.cpp` routing `else if` 하나(마지막 `else return am_error` 앞)와 carry 보존 case group 하나(FLOW 43 PC), `animation_machine_internal.h` 선언 하나, `Makefile`(source·test target), `tools/verify_animation_machine.py` SOURCES. public header는 바꾸지 않는다(결정 3 제안 A).
- C1은 **frame 구동기 변경(D9 문서 §5)과 함께** 자연 frame에서 의미가 있다. C1 단독(구동기 Skip)에서는 기존 결과가 바뀌지 않는다: controller는 H stop 뒤 선언 생략이므로 C1 PC에 닿지 않는다 [I, 구현 뒤 base frame pass·RNG 400·D1 검증기 무변화로 확인].

## 시험·fixture 계획

- 단위 시험 `engine/tests/animation_machine_controller_c1_test.cpp`(`run_animation_machine`만): 시작 116개 × 들어오는 C(clear/set/unknown) block 표, zero-step(stop = 시작), 내부 PC 313개 전수 오류, 범위 양끝 홀수, rollback 탐침 work RAM `10fe00..10fefe`.
  - 경로 fixture: 게임 gate(`100b30` callback `270e`/`47bfc`/0, `c80a` 착지 = C2 경계 오류), demo gate(`104cd4` 0/1/2), mode 검사(`100012` 0/1/2/3), 꼬리의 모든 분기(`81` 0/≠0 × `10fd8f` bit0·1 × `82`, credit 변화·불변, `78` 0/1..3/4/ffff, `83`, `7a` 0/BCD 경계 `00 08`/`01 07`/`10 00`/`99 ff`).
  - `SBCD` 전수: D1.B 256 × (D0.B 하위 < 8, ≥ 8) → 512 fixture(비 BCD 포함), 결정 7.
  - 표시: `36ba`/`3706` 자릿수 1..4 × 앞자리 0 유무 × nibble 0..f(`370c` 표 전 항목), `c49c`(BYTE `100964` = `a9`/`aa`/`ab`, `4a9ca` d7 0..3), `c4f8`(byte push, `10fd8b` = `ff` 넘침 포함), `4a88e`(`100003` 0/1, `(A1)` 0/1/2/ff).
  - credit: `4a944`·`4a974`(`10fd82` 0; `100003` 0/1; D0 0/1/ffff), Z 규약(결정 3): `4a9ca`에서 두 bit 4조합, 복귀 block 직접 진입(A0 RAM 값 0/≠0, A0 = ROM·device → guard 오류).
  - BIOS·device(결정 5): `10fd82` ≠ 0 → `4a982`에서 PC `c00450` 정지(unsupported, rollback), `d00034` 읽기 guard 오류. 구동기 선언 resume은 D9 문서 시험에서.
  - live 대상(결정 4): A1 = `3650`(자연), work RAM PC(unsupported, rollback), 홀수 A1.
- 실제 ROM 차분(Unicorn vs C++ + 8 `program_rom_*.ms5d`): `tools/verify_animation_machine_unit_fixtures.py`(V1 fixture 검증기, HEAD `c49bcd2`)의 spec 하나로 작성한다. 입력 상태:
  1. 자연 F5 관측의 controller 진입 상태(H stop, PC = `c52a`)에 D9 (ii)/(i) 선언을 적용한 상태(controller LONG과 PC를 `c7fc`/`c66a`로, 136 seed × 전 frame 중 표본), stop `2ac2`(controller 복귀). 전환 frame은 C2 경계 오류 기대.
  2. 같은 상태에서 C1 각 시작으로 직접 진입하는 강제 case(n번째 leader snapshot, 필드 교란).
  - 비교: RAM 64 KiB, D0–D7/A0–A7, PC, bank, PVC, 순서 있는 port, 대기, external read(없음). carry는 tag만.
- frame 단위 native 비교는 D9 문서 §7(구동기 Execute 구성)에서 한다.

## 탐침 집계

[F] scratch `p4.py`(자연 137 seed × 400 frame, continuous; D9 문서 §3.1).

| 구성 | C1 leader 실행 | C1 매 frame 경로 frame 수 | 비고 |
| --- | --- | --- | --- |
| (iii) 기록 | 0/116 | 0 | controller는 C3a `c560` 대기 |
| (ii) 게임 | 24/116 | `c7fc`→`c7fc` 30,996, 전환 뒤 `c79a` 대기(C2)의 꼬리 23,132 | 136/136 완주 |
| (i) demo | 49/116 | `c66a`→`c66a` 30,996, `c6c0` 대기(C2)의 꼬리 14,416 | 136 seed가 BIOS 종단 |
| 합집합 | 52/116 | | |

- [F] (ii) 실행 leader: `30bc 30ce 30d4 30e6 c7fc c806 c80a c988 c990 c996 c9ac c9b4 c9ba c9c2 c9ce c9de c9f6 c9fe ca20 4a944 4a94c 4a966 4a970 4a972`.
- [F] (i)이 더하는 leader: `314c 3156 c49c c4a0 c4a4 c4aa c4b6 c4ba c66a c674 c678 c67e c682 c724 c72e c736 c73a c73e c748 ca32 4a974 4a9b4 4a9c6 4a9ca 4a9d0 4a9d6 4a9da 4a9e0`(결정 3의 Z 소비 `4a9d0`·`4a9da`가 자연에서 실행된다).
- [F] 자연 미실행 64개: 숫자 표시 `3670..3706` 25(`c4f8`·`4a88e` 경로가 자연에서 닫혀 있음: `30bc`/`30d4`가 C = 0), `c4f8` 3, `c654`/`c664`, `c99a`, `c9be`, `c9d6`, `c9ea..c9f2`, `ca06..ca18`(타이머 `7a` = 0), `4a88e` 12, BIOS·MVS 쪽 등. fixture로 덮는다.

## 미확인

- [U] `36ba`의 범위 밖 호출자 23곳의 복귀 flag 소비 형태(`4a974`·`ca32`·`4a9ca` 호출자는 결정 3에서 확인).
- [U] `10fd8f` bit 0·1, `10fd8b`, `100964`(`aa` 비교)의 게임상 의미(soft-dip·credit 표시 [I]).
- [U] BIOS `c00450`의 실제 응답 형식(`10fdb0..10fdb3`).
- [U] `+7a..+7b` 타이머를 누가 세우는가(자연 seed에서 0이면 `c9fe`에서 끝남).
