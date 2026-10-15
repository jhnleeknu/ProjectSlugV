# F5 controller C3: boot `c52a`/`c560`·demo 도입·title 계약 초안

**상태: 구현 전 계약 초안 — 메인 결정 전.** 원본 바이트·scratch native 탐침 근거이며 구현·검증 기록이 아니다.

범위 근거는 F5 범위 문서(`animation-machine-frame-head-f5-scope.md`, SHA256 `973d4595…`)의 §4 C3 행(`c52a..c654` `c6da..c724` `4fb1a` `e62ec`, 48 block, fixture 전용, 위험 BIOS 요청·`107dea` 선언)과 결정 D10이다. C1 계약 결정 1의 재배치를 따라 `e62ec`(4)를 C2로 보내고 boot 전용 helper `8b64`/`8bb6`(3)을 C2에서 가져왔다. D9 권고(`animation-machine-controller-d9-decision.md`)는 **무선언 구성 (iii)에서 C3의 boot 머리 9 block이 자연 실행된다**는 탐침 결과에 근거해 D10("F5 자연 경로에서 제외, fixture 전용")의 일부 정정을 제안한다(결정 1).

작성자·기준·도구·표기는 C1 계약 머리와 같다(ROM SHA256 `29112a94…c886c860f`, HEAD `c49bcd2`, routing 원천 SHA256 `c7318132…caad2`, scratch `ana_c/`).

## 요약

- [F] **정적 leader 47개, 4 범위 508바이트(짝수 PC 254).** `c52a..c654` 32, `c6da..c724` 7, `4fb1a..4fb4a` 5, `8b64..8bbc` 3.
- [F] **자연 seed의 controller는 boot 진입 `c52a`다**(H 54,264개 모두 LONG `(1008e4)` = `c52a`에서 멈춤, D1 검증 기록). 탐침에서 선언 생략 대신 이것을 그대로 실행하면:
  - frame 1: `c52a`(`9056` → BYTE `107def` := `ff`; controller node `+76..+7e` WORD·`+80` `+81` `+83` BYTE := 0; `8b64` fill 카탈로그 selector 0 → PVC `2ffff2`/`2ffff0` 2쌍, palette helper `4718`(H3), WORD `107dea` := `2000`, WORD `100010` := 0) → callback `c560` 설치 → `c560`(`8bb6`: D0.W := WORD `107dea` = `2000` ≠ 0) → `c56c RTS`. block 9개, port 4건, RAM 변경 37바이트.
  - frame 2 이후: 매 frame `c560 8bb6 c566 c56c`(4 block, port 0, stack 2바이트만 변경).
  - [F] **WORD `107dea`를 줄이는 것은 IRQ `c8c`(F6)뿐이다**(`game-startup.md`의 rendering branch). D2 선언 모델은 IRQ를 실행하지 않으므로 `c560`은 끝나지 않는 안정 대기가 된다. 범위 문서 §2.4·D9 (iii)의 "첫 frame에 해체"는 `1008e4` := `c66a` 선언의 결과이고 기록 상태 그대로의 결과가 아니다(정정).
- [F] **`107dea` 대기가 풀린 뒤(fixture 전용):** `c56e`(`e7bf4` 고정 palette, `49a1a`(D0 = 0) RNG, BYTE `10f004` := 3, `47570` 게임 초기화) → `c58a` BIOS 요청 BYTE `10fdae`: 0·1이면 **`JMP c00444`**(종단), 3이면 title `c6da`, 그 밖(2 = demo [I])이면 `c5b4`(ROM WORD `000180` = 0) → `c5be` demo 도입(`ca7e`, `4fb1a` 자식 `4fb64`, `c5ce` 대기 → `ca76` + 자식 `de024` → `c5f4` 대기 → 150 frame 계수 `c608`) → `c610` 재시작(`49a1a` `c4cc` `caf0` `47570` `4823a` `3162`) → `c654`(C1)를 설치하고 RTS.
- [F] **경계:** 이미 routing된 callee `9056`(area_clear) `4718`(H3) `e7bf4`(palette_bind) `ca7e`(exit) `ca76`(stage_entry) `caf0`(screen) `28ae`(fade_card) `3902`(H2), C2 helper(`49a1a` `47570` `4823a` `3162` `c4cc`), C1(`36ba` `c724` `c73e` `c654` 설치), BIOS `JMP c00444` 2곳(`c598` `c5a6`), 자식 `4fb64` `de024` `de376`(미routing, 설치만).
- [F] **carry:** 소비 1(`4fb3c SCC.B 62(A6)`, `28ae`의 known C). **device:** PVC bank 쓰기(`8b64`/`8b98`, 기존 bank 모델), bank window 읽기 `200004`/`200008`(LONG).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **C3를 둘로 나눈다(제안).** [F] 무선언 구성에서 자연 실행되는 것은 boot 머리 9 block(`c52a` `c530` `c55a` `c560` `c566` `c56c` `8b64` `8b98` `8bb6`)뿐이고, 나머지 38개는 `107dea` 선언 해제가 있어야 닿는다.
   - **C3a(boot 대기, 9 block):** routing `c52a..c56e` `8b64..8bbc`. 의존: H3(`4718`)·area_clear(`9056`)뿐이다(C1·C2 불필요). frame 구동기 Execute 구성 (iii)(D9 문서)을 이것만으로 자연 136 seed × 400 frame에 적용할 수 있다.
   - **C3b(대기 뒤 boot·demo 도입·title, 38 block):** routing `c56e..c654` `c6da..c724` `4fb1a..4fb4a`. 의존: C1·C2. fixture 전용.
   - 대안: 범위 문서대로 C3 하나(47)를 C2 뒤에 둔다. 이 경우 구성 (iii)은 C2 뒤까지 미뤄진다.
2. **D10 정정.** [F] "boot는 F5 자연 경로에서 제외"는 구성 (iii)을 쓰지 않을 때만 맞다. 제안: D10을 "C3a는 자연(구성 (iii)), C3b는 typed fixture 전용(선언: WORD `107dea` := 0, BYTE `10fdae` ∈ {0,1,2,3,…})"으로 바꾼다.
3. **`107dea` 대기 해제는 선언 해제 어휘에 넣지 않는다(제안).** [F] `c560`은 Waiting block이 아니라 "값을 읽고 RTS하는 callback"이다(`8bb6`이 D0를 돌려주고 `c566 TST.W D0; BEQ`). 대기는 frame 단위 반복으로 표현되고 실행부에는 대기 PC가 없다. fixture는 frame 시작 전 host 쓰기 WORD `107dea` := 0으로 만든다(구동기 해제 어휘 변경 없음). [I] IRQ(F6) 구현 뒤에는 자연 감소가 이 경로를 연다.
4. **BIOS 요청 `10fdae` 분기와 종단.** `c598`/`c5a6 JMP c00444`는 C2 결정 3과 같은 종단(구동기 `animation frame controller system return`). `10fdae` = 3 → `c6da`(title), 그 밖 → `c5b4`. [F] 자연 seed의 `10fdae` = 0이다(종단 쪽). 값 2·3·4·`ff`는 fixture다.
5. **ROM WORD `000180`.** [F] `c5b4 TST.W 180.l; BNE.W c610`: canonical ROM 값 0이므로 `c5be`로 간다. 실행부는 live bus 읽기로 구현한다(쓰기 `c690`은 C2).
6. **`c608` 150 frame 계수.** [F] `c5fc`가 WORD `76(A6)` := `96`(150), `c608`이 매 frame `SUBQ.W #1`; 0이 되면 같은 호출에서 `c610`으로 간다. 계수 중에는 `c724`(C1)로 간다. fixture는 계수 1·2·150과 `0`(→ `ffff`, 65,535 frame) 진입을 덮는다.
7. **실행부 파일·오류 문자열.** `engine/src/animation_machine_controller_c3.cpp`의 `animation_controller_c3_block`(C3a·C3b가 같은 파일이면 routing `else if` 하나에 범위 둘을 둔다). 오류: `unsupported animation controller c3 PC`(내부 PC), `controller c3 caller requires known carry`(`4fb3c`에 Unknown C, 기존 어휘).
8. **무효화 탐침(C3a 뒤).** [F] 정적 검색:
   - `engine/tests/animation_machine_scheduler_test.cpp` 49행 `pass-controller`: pass가 controller node(callback `c52a`)에 닿아 `unsupported animation machine PC`를 기대한다. C3a 뒤에는 `c52a`가 실행되므로 기대가 바뀐다. 제안: 기대 문자열은 두고 controller callback LONG을 work RAM PC(`10fe4x`)로 바꾸는 값 교체(H1 결정 7 관례).
   - `tools/verify_animation_machine_scheduler.py` 783~791행(`pass-head-ring-unchecked-step-limit`): ring이 callback `c52a` node로 이어져 C++가 `unsupported`로 끝나는 것을 기대한다. 수정하지 않고 무효화 목록으로 보고한다.
   - stop PC로만 쓰는 곳은 유효하다: `animation_machine_frame_head_h1_test.cpp`(`d1-c52a` `d1-fbc-c52a`, stop `c52a`), `_h2_test.cpp`(stop `c52a`), `animation_machine_frame_test.cpp`(controller LONG `c52a`, 구동기 Skip 기본), `animation_machine_scheduler_test.cpp` `host()`(head callback `c52a` 거부, 실행 전 host 검사), `tools/verify_animation_machine_frame_head.py`(H stop `c52a`).
   - host 수준 API 시험(`game_startup_test.cpp` `c52a`/`c560`/`c584`, `tools/verify_game_startup.py` 등)은 실행부와 무관하다.

## 원본 바이트 근거

[F] 4 범위 508바이트, 연결 SHA256 `91179575518c99d6ec881308169ad30bd5cef59e4a2d79a21e3f6a53e052b973`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `8b64..8bbc` | 88 | `31b35171ed19425dd96809fc7a6b0bc6abffab716bb36153a2ac85eaf00b652d` | 3 |
| `c52a..c654` | 298 | `6f9f9fc8234ddd07157a251cff589c133347084808773305ad896ec3d615c018` | 32 |
| `c6da..c724` | 74 | `39ec07ccd9748dcaeb898b9b4d0060646effc1a1a820362a97964d1e236f8653` | 7 |
| `4fb1a..4fb4a` | 48 | `9fe69fb852c3984925a11a37a5d39c41ae6fac3b9bfcb3268096920bd31c21e3` | 5 |

- [F] 진입·참조(`xref.py`): `c52a`는 boot 초기 node 표 `268a`의 LONG(`269e`)뿐이다(scheduler `268e` 설치). `8b64`는 `c554`, `8bb6`은 `c560`, `4fb1a`는 `c5c2`에서만 불린다. 설치점: `c560`(`c55a`) `c5ce`(`c5c8`) `c5f4`(`c5ee`) `c608`(`c602`) `c654`(`c64c`, C1) `c6f4`(`c6ee`).
- [F] 범위 이웃: `8b62`(앞 함수) `8bbc`(cleanup 실행부 `8bbc..8bc0`), `c528`(C1 `c4f8` 함수의 RTS) `c654`(C1), `c6ce..c6da`(문자열 자료 `5c70005c6303 54494d45 0000` = `"\p\0\c\x03TIME\0\0"`, `c6f8 LEA`가 가리킴; 원본 정렬상 `c6d8`부터의 capstone 해석은 무의미하다) `c724`(C1), `4fb18`·`4fb4a..`(`4fb64` 자식 등, 미routing).
- [F] host 수준 기존 구현: `step_game_startup`(`c52a`/`c560` → `c584`, `game-startup.md`, 원본 IRQ 16회 비교 포함), `restart_game`(`c610..c652`), `game-continuation.md`(`c58a` 이후 정적 분기). 이 기록은 `8b64` D0 상위 WORD 규칙(`((D0 & ffff0000) << 5) | 2000`)·`c560` 반복 무해성 등 의미 근거로 쓴다.

## block 목록과 실행 의미

표기는 C1 계약과 같다. A5 = `108000`(`-216(A5)` = `107dea`, `-7ff0(A5)` = `100010`, `-25e(A5)` = `107da2`, `702a(A5)` = `10f02a`, `7dda(A5)` = `10fdda`, `7d82(A5)` = `10fd82`, `-7fff(A5)` = `100001`).

**C3a: boot fill `8b64`(`c554`) 2, counter 읽기 `8bb6`(`c560`) 1** — [F] `game-startup.md`.
- `8b64`: `MOVE.W #0, -7ff0(a5); MOVE.W #1000, 2ffff2.l; MOVE.W #0, 2ffff0.l … LEA.L (a0, d0.w), a0; BSR.W 4718 (10명령)` (→`8b98`) — PVC 쓰기 2(bank 변경), LONG `200004`/`200008` bank window 읽기, A4 := `107da2`, `ANDI.W #ffff,D0`(상위 WORD 유지), `LSL.L #5,D0`, A0 += sext(D0.W), H3 `4718` 호출
- `8b98`: `MOVE.W #2000, -216(a5); MOVE.W #0, -7ff0(a5); MOVE.W #1000, 2ffff2.l; MOVE.W #0, 2ffff0.l; RTS` — WORD `107dea` := `2000`, PVC 쓰기 2
- `8bb6`: `MOVE.W -216(a5), d0; RTS`

**C3a: boot 머리 `c52a`/`c560` 6**
- `c52a`: `JSR 9056.l` (→`c530`) — FLOW
- `c530`: `CLR.W 76(a6); CLR.W 78(a6); CLR.W 7a(a6) … MOVE.W #0, d0; JSR 8b64.l (10명령)` (→`c55a`) — `+76 +78 +7a +7c +7e` WORD, `+80 +81 +83` BYTE := 0(`+82` `+84` 보존), D0.W := 0
- `c55a`: `MOVE.L #c560, (a6)` (→`c560`) — 설치점
- `c560`: `JSR 8bb6.l` (→`c566`) — FLOW
- `c566`: `TST.W d0; BEQ.W c56e` (→`c56c`)
- `c56c`: `RTS` — FLOW. 자연 복귀 `2ac2`.

**C3b: 대기 뒤 boot `c56e` 12**
- `c56e`: `JSR e7bf4.l` (→`c574`) — FLOW
- `c574`: `MOVEQ #0, d0; JSR 49a1a.l` (→`c57c`)
- `c57c`: `MOVE.B #3, 10f004.l; JSR 47570.l` (→`c58a`)
- `c58a`: `MOVE.B 10fdae.l, d0; CMPI.B #0, d0; BNE.W c59e` (→`c598`)
- `c598`: `JMP c00444.l` — FLOW, BIOS 종단(결정 4)
- `c59e`: `CMPI.B #1, d0; BNE.W c5ac` (→`c5a6`)
- `c5a6`: `JMP c00444.l` — FLOW, BIOS 종단
- `c5ac`: `CMPI.B #3, d0; BEQ.W c6da` (→`c5b4`)
- `c5b4`: `TST.W 180.l; BNE.W c610` (→`c5be`) — ROM 읽기(결정 5)
- `c5be`: `JSR ca7e(pc)` (→`c5c2`) — FLOW
- `c5c2`: `JSR 4fb1a.l` (→`c5c8`) — FLOW
- `c5c8`: `MOVE.L #c5ce, (a6)` (→`c5ce`) — 설치점

**C3b: demo 도입 대기 `c5ce`/`c5f4`/`c608` 9, 재시작 `c610` 6**
- `c5ce`: `TST.B 62(a6); BEQ.W c73e` (→`c5d6`) — 대기(매 frame), `c73e`는 C1
- `c5d6`: `JSR ca76(pc)` (→`c5da`) — FLOW
- `c5da`: `MOVEA.L #de024, a0; MOVE.W #0, d0; JSR 28ae.l` (→`c5ea`) — 자식 `de024`(미routing)
- `c5ea`: `CLR.B 62(a6); MOVE.L #c5f4, (a6)` (→`c5f4`) — 설치점
- `c5f4`: `TST.B 62(a6); BEQ.W c724` (→`c5fc`) — 대기
- `c5fc`: `MOVE.W #96, 76(a6); MOVE.L #c608, (a6)` (→`c608`) — 설치점
- `c608`: `SUBQ.W #1, 76(a6); BNE.W c724` (→`c610`) — 결정 6
- `c610`: `MOVE.W #1, 702a(a5); MOVEQ #0, d0; JSR 49a1a.l` (→`c61e`)
- `c61e`: `BSR.W c4cc` (→`c622`) — FLOW
- `c622`: `BSR.W caf0` (→`c626`) — FLOW
- `c626`: `JSR 47570.l` (→`c62c`) — FLOW
- `c62c`: `MOVE.W 702a(a5), d0; ANDI.W #1, d0; MOVE.W d0, 702a(a5); ADDI.W #6, d0; JSR 4823a.l` (→`c642`)
- `c642`: `MOVE.W 702a(a5), d0; JSR 3162.l` (→`c64c`) — D0 ∈ {0,1} → replay mode
- `c64c`: `MOVE.L #c654, (a6); RTS` — C1 `c654` 설치

**C3b: title `c6da` 7** — BIOS 요청 3.
- `c6da`: `JSR ca76(pc)` (→`c6de`) — FLOW
- `c6de`: `MOVEA.L #de376, a0; MOVE.W #0, d0; JSR 28ae.l` (→`c6ee`) — 자식 `de376`(미routing)
- `c6ee`: `MOVE.L #c6f4, (a6)` (→`c6f4`) — 설치점
- `c6f4`: `MOVE.W #7257, d0; LEA.L c6ce(pc), a0; JSR 3902.l` (→`c702`) — "TIME" 문자열(H2 `3902`)
- `c702`: `MOVE.W #7278, d0; LEA.L 7dda(a5), a0; MOVE.W #3, d1; MOVEQ #0, d3; MOVEQ #2, d4; JSR 36ba.l` (→`c718`) — BCD 2자리(C1)
- `c718`: `TST.B 7dda(a5); BEQ.W c73e` (→`c720`)
- `c720`: `BRA.W c724` — FLOW

**C3b: demo 자식 할당 `4fb1a`(`c5c2`) 5**
- `4fb1a`: `TST.B 7d82(a5); BEQ.W 4fb42` (→`4fb22`)
- `4fb22`: `CMPI.B #1, -7fff(a5); BNE.W 4fb42` (→`4fb2c`)
- `4fb2c`: `MOVEA.L #4fb64, a0; MOVE.W #0, d0; JSR 28ae.l` (→`4fb3c`) — 자식 `4fb64`(미routing)
- `4fb3c`: `SCC.B 62(a6); RTS` — C 소비(`28ae`: 할당 성공 C = 1 → `62` := 0, 실패 C = 0 → `62` := `ff`)
- `4fb42`: `MOVE.B #ff, 62(a6); RTS`

## carry

- [F] **소비 1:** `4fb3c`(`28ae`의 `2908 ORI #1`/`290e ANDI #fe`가 남긴 known C). 들어오는 C가 Unknown이면 결정 7 오류.
- [F] **known 생산 0. FLOW 14**(위 태그). 나머지 Unknown. 같은 block flag: `c566`(`TST.W`→`BEQ`), `c58a`/`c59e`/`c5ac`(`CMPI.B`→`BNE`/`BEQ`), `c608`(`SUBQ`→`BNE`).
- [F] RTS 너머 C·Z 소비: `c56c`/`c64c`/`4fb3c`/`4fb42` 뒤 자연 복귀는 dispatcher `2ac2`(fade_card 실행부, flag를 읽지 않음) 또는 `c5c8`(`MOVE.L`).

## 경계·I/O·스택

- [F] **port:** `8b64`/`8b98`의 PVC `2ffff2`·`2ffff0` WORD 4건(기존 bank 모델 `pvc_bank_update`; 값 `1000`/`0` → bank 기준 `200000` [F] 탐침 port 4건). 그 밖은 callee(`caf0`, `47570` 뒤 sound, `e7bf4`)가 낸다.
- [F] **읽기:** bank window LONG `200004`/`200008`(bank 선택 뒤 `200000` 기준), ROM WORD `000180`, 문자열 `c6ce`, RAM 필드(`107dea` `10fdae` `10fd82` `100001` `10f02a` `10fdda`).
- [F] **쓰기:** controller node `+62` `+76..+7e` `+80` `+81` `+83`, `107dea` `100010` `10f004` `10f02a`, `107def`(`9056`), palette buffer(`4718` 경유, H3).
- [F] **대기:** 실행부 수준에는 없다(결정 3). `47570` 뒤 sound `3aea`는 C2·기존 실행부가 낸다(D6).

## 자연 실행(탐침)

[F] 구성 (iii)(무선언, 자연 seed): 아래 "탐침 집계". 구성 (i)·(ii)에서는 C3에 닿지 않는다(controller 선언이 `c66a`/`c7fc`).

## 구현 범위와 규약

- routing: C3a `c52a..c56e` `8b64..8bbc`, C3b `c56e..c654` `c6da..c724` `4fb1a..4fb4a`(결정 1). 내부 PC 직접 진입은 `unsupported animation controller c3 PC`.
- C3a는 C1·C2와 독립이라 **가장 먼저 구현할 수 있다**(D9 문서 §6 순서). C3b는 C1·C2 뒤.
- `8b64`의 `LEA.L (A0,D0.W),A0`는 D0.W 부호 확장, `LSL.L #5,D0`는 32 bit 이동(상위 WORD 보존 규칙은 `game-startup.md`). `4718`은 H3 실행부로 `am_call`.

## 시험·fixture 계획

- 단위 시험 `engine/tests/animation_machine_controller_c3_test.cpp`: 시작 47 × C 3가지 block 표, zero-step, 내부 PC 전수, 홀수, rollback 탐침.
  - C3a: `c52a`(D0 상위 WORD 0/`0001`/`07ff`/`0800`/`ffff` — `game-startup.md`의 경계와 같음, bank 시작 1/2, `107def` 이전 값), `c560`(`107dea` = 0/1/`2000`/`8000`/`ffff`).
  - C3b: `10fdae` 0/1/2/3/4/`ff`, `c5ce`/`c5f4` 대기 0/≠0, `c608` 계수 1/2/`96`/0, `c610`(`10f02a` 0/1/2/`ffff`), title(`10fdda` 0/≠0, BCD), `4fb1a`(`10fd82` 0/1 × `100001` 0/1/2 × 할당 성공·실패).
- 실제 ROM 차분: V1 fixture 검증기 spec.
  - C3a 자연: frame 구동기 Execute 구성 (iii)의 frame별 비교(D9 문서 §7) — 136 seed × 400 frame.
  - C3b: 자연 H stop 상태(`c52a`/`c560`)에 WORD `107dea` := 0과 `10fdae` 선언을 더한 상태에서 controller 진입부터 stop `2ac2` 또는 BIOS 경계까지(native는 `c00444` fetch에서 정지).

## 탐침 집계

[F] scratch `p4.py`(자연 137 seed × 400 frame; D9 문서 §3.1).

| 구성 | C3 leader 실행 | controller 경로 | 결과 |
| --- | --- | --- | --- |
| (iii) 기록(무선언) | 9/47(C3a 전부) | `c52a`→`c560` 136(frame 1), `c560`→`c560` 54,128 | 136/136 완주(case 141은 frame 0 `odd-pc`, 선언 생략과 같음) |
| (ii)·(i) | 0/47 | — | — |

- [F] (iii)의 controller port는 seed당 frame 1의 PVC 4건(`2ffff2/2` 2, `2ffff0/2` 2)뿐이다(합 544). controller 안 대기 0회, BIOS 0회, 미routing node 0개.
- [F] (iii)의 RAM 변경: frame 1은 37바이트(controller node 필드, `107def`, `107dea`, `100010`, stack 등; 바이트별 분해는 하지 않았다)다(표본 case 0). 이후 frame은 stack 2바이트(`c560`의 JSR 복귀 LONG)다.
- [F] 표본 6 seed(case 0·1·2·94·100·135)에서 node 순서는 400 frame 동안 선언 생략과 같고, RAM은 frame 1부터 다르다(scratch `p3.py`).

## 미확인

- [U] `10fdae`의 BIOS 의미(0/1 = BIOS 메뉴 복귀, 2 = demo, 3 = title [I]).
- [U] 자식 `4fb64` `de024` `de376`의 의미와 routing 단위.
- [U] 실제 boot에서 frame head·controller·IRQ의 순서(자연 boot 관측 없음).
