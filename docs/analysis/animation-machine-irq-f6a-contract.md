# F6a IRQ 껍질·서비스 `c8c`·credit·sound/Z80·열 제어·sprite flush 구동 계약 초안

**구현 전 계약 초안 — 메인 결정 전**

범위 근거는 F6 범위 문서(`animation-machine-irq-f6-scope.md`)의 4절 F6a 행이다. 결정 E1–E10이 이 계약을 구속한다(메인 결정 전). 단위 형식과 규약은 F5 H1 계약(`animation-machine-frame-head-h1-contract.md`)을 따른다.

Claude Opus 5.5 / high 읽기 전용 분석 작업자가 작성했다. canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`)을 capstone 5.0.6 M68000으로 디코드했다. F6a 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. 작업 트리 HEAD는 `3b63864`이다. F6a 범위의 짝수 PC는 기존 routing에 없다. [F]·[I]·[U] 표기는 범위 문서와 같다. block 목록은 scratch `units.py`(`units.json` F6a 191개 + push 복귀점 `d2a`와 그 분기 대상 `ce6`)에서 계산했다.

## 요약

- [F] **block 시작 193개**, 11 범위. 이 밖에 clear run의 계산 진입 381개가 있다(`1669e − 4n`, n = 0..380, 결정 3).
- [F] **진입:**
  - vector `64`/`6c` → `20c`, `68` → `29c`
  - raster callback 기본값 `3dcc`(`3dce`가 LONG `100006`/`10000a`에 설치; `23a JSR (A0)`·`2b4 JSR (A5)`의 대상)
  - `c8c`(`23c`)
  - task 복귀 `d2a`(`d18 MOVE.L #d2a,-(A7)`)
- [F] **경계(F6a가 실행하지 않음):**
  - F6b `72fa`(`cbe JSR`)
  - F6c writer 표 `16d80 JSR (A3,D7.W)`(A3=`f226`)·`16e3c`(A3=`13b46`)의 live 대상
  - 이미 routing된 `3af8`(sound, `48174 JSR`)
  - BIOS `c0044a`(`242 JSR`)·`c00438`(`21e JMP`)
  - raster callback이 `3dcc`가 아닌 값일 때의 대상(routing에 맡김)
  - task 본문(`d28 RTS`의 대상, 결정 E9)
- [F] **carry:**
  - 들어오는 C를 소비하는 block은 0개다.
  - known 생산은 5개다: `16e92` Set(`ORI #1,CCR`), `16e9e` Clear(`ANDI #fe,CCR`), RTE block `248` `2b6` `2ce`(꺼낸 SR bit0, 결정 E3).
  - FLOW_ONLY는 41개(`d2a`·`ce2` 포함), 나머지 147개는 Unknown이다(`ce6` 포함). 41 + 2(CCR) + 3(RTE) + 147 = 193이다.
  - `16cfa`의 known C는 `cdc` 뒤 `ce2`(`MOVEA`→`ce6 CMPA`)가 소비하지 않는다.
- [F] **I/O:**
  - port 쓰기: `3c000c` WORD(ack 6/2), `300001` BYTE(watchdog: `ca0` `cf0`), `3a0011`/`3a0001` BYTE(`10f001` bit4), `3c0004` WORD, `3c0000` WORD(`282` `2c4`)와 LONG(`187d8` 열 cell, clear run), PVC `2ffff2`/`2ffff0`(`26a` `1adf8` `1ae3e` `cf0` `16dc4` `16e7c`), `320000` BYTE(Z80 명령: `3ccc` `3cf0` `3d32`)
  - device 읽기: `3c0006` WORD(`288`), `320000` BYTE(`3cb2`)

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 193 block, routing 11 범위.** `20c..2d8` `3dcc..3dce` `a2c..b0c` `bbe..bee` `c8c..d56` `3cac..3d3a` `48156..48180` `1adf8..1ae56` `187d8..18be8` `16092..166bc` `16cfa..16ea4`.
   - `16092..166bc`는 clear run 본체 `160ae..1669e`를 포함한다.
   - `d54 RTS` 뒤 `d56..`은 자료다(routing 밖).
   - 범위 이웃은 범위 문서 4절을 본다.
2. **RTE(E3)와 IRQ 내부 SR.** 실행부는 `248`/`2b6`/`2ce` 끝에서 SR WORD·PC LONG을 pop하고 A7 += 6, carry := SR bit0으로 둔다. S=0 또는 T=1이면 `unsupported animation irq RTE status`다. IRQ 안의 interrupt mask는 표현하지 않는다(중첩 IRQ 없음).
3. **clear run 계산 점프는 live 대상으로 둔다(H4 결정 3과 같음).**
   - `16092`: `D1.W` := −`D1.W`, ×4, 목표 = `1669e` + sext(`D1.W`)다. `166a0`: `D1.W` ×4, 목표 = `1669e` + sext(`D1.W`)다.
   - 목표가 run 진입(`160ae..1669e`, 4바이트 간격, `MOVE.L D0,(A6)` 위치)이면 그 진입부터 실행한다.
   - 그 밖이면 다음 step의 routing에 맡긴다(F6c 범위면 F6c, routing 밖이면 `unsupported animation machine PC`).
   - [F] `16d9a`·`16db8`의 `D1` = WORD `2(A4)` − max(WORD `4(A4)`, WORD `6(A4)`)(부호 있는 `BGT`)이고, `16e56`·`16e72`의 `D1` = WORD `(A4)` − min(…)(`BLT`)이다. [U] 자연 범위(탐침 n = 0..70).
   - run 진입의 홀수 목표는 생기지 않는다(×4).
4. **raster callback 비기본값.** `224` block 끝 `JSR (A0)`(A0 = LONG `100006`)와 `2a4`의 `JSR (A5)`(A5 = LONG `10000a`)는 live 대상으로 둔다. `3dcc`는 F6a의 RTS block이고, 그 밖의 값은 routing에 맡긴다. 0이나 홀수는 기존 checked 오류다.
5. **task 복구(E9).** `cf0`은 실행한다. `d28 RTS`의 대상(task PC)은 routing에 맡긴다. 대안(checked 오류 `unsupported animation irq task`)은 범위 문서 E9에 있다.
6. **`320000` 읽기(E7).** `3cb2`의 BYTE `320000` 읽기는 external read queue(주소 `320000`, 크기 1)로 공급한다. 이를 위해 `external_queue_device`에 `320000`/1을 더한다(공개 의미 변경, 결정 필요). 빈 queue는 `animation machine external read queue empty`다.
7. **palette RAM(E6)은 F6a에 없다.** F6a는 `400000`을 쓰거나 읽지 않는다(F6b와 F6c는 쓰지 않음, H3 `4718`만 mirror 읽기). E6 b의 device 확장은 F6b에서 넣는다.
8. **실행부 파일·오류 문자열.**
   - 실행부는 `engine/src/animation_machine_irq_f6a.cpp`의 `animation_irq_f6a_block`이다.
   - 오류: `unsupported animation irq f6a PC`(내부 PC), `unsupported animation irq RTE status`(결정 2). 기존 장치·스택 오류는 그대로 쓴다.

## 원본 바이트 근거

[F] 범위별 SHA256:

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `20c..2d8` | 204 | `0b0c3ae8e1893520599f0f8085edc44e9c51fb9e7cfc9b239e4efa2d02c62a81` | 10 |
| `3dcc..3dce` | 2 | `1ceeabf0c6a5a30bad12cdac0e3ab015a7188a42e6aebb556aad00bb9cd693ad` | 1 |
| `a2c..b0c` | 224 | `c53964ab85ff5ddcdc2f856b425231c2915f0fd475df220faebe8fa5aaa86c4f` | 26 |
| `bbe..bee` | 48 | `66304b088406911b3b0556befebc6ec38ec01904afc57480e297b20a1c70dee8` | 6 |
| `c8c..d56` | 202 | `2d332577588480a7acf66e4845e7806c761343b64113f4f3fae0b4afbd5a9cb1` | 20 |
| `3cac..3d3a` | 142 | `40ebe88ca06644122a8fc044b8ce5cc6fa75cc1e76eec14582d2d145d4462c25` | 14 |
| `48156..48180` | 42 | `f0491c9ddba4b0517fca9dc48abd15ca7778805b9365c29d822b52f4a7f95417` | 6 |
| `1adf8..1ae56` | 94 | `45ef98c27ded1872818db05603798da9cc91e06ed5ae116afe7d2e56438e5108` | 5 |
| `187d8..18be8` | 1,040 | `e1b0e4e4a48585335ec1c4fa54a0a48588e5d0481f42190349e1deb99d432ba9` | 69 |
| `16092..166bc` | 1,578 | `48dbe20ae1a5c2050455a4d74e81c2a0227e198099ffa972ef7001c09421f01b` | 2 (+ run 381) |
| `16cfa..16ea4` | 426 | `a7e6b861a2c32c84ea82894b04faf0d10679176ab5382ef807d80d20d802397c` | 34 |

- 정적 leader 191개의 목록 SHA256은 `5660e6eda205bf8625101136ebc06480c3f8d573716b8b3d7305675e2229f77d`다(공백으로 구분한 소문자 hex, `units.json` 순서).
- [F] 자료와 RAM(A5 = `108000` 기준 자연 주소):
  - IRQ 신호: `100002` `100004..100005`(credit 계수) `100006` `10000a` `100010` `100014` `100016` `100019` `10001b`
  - task 큐: `10081c`와 frame `10001c..10081c`
  - VRAM 주소 사본 `104d8e`, sound ring `104cf4..104d73`(`-330c`), cursor `104d74`/`104d76`(`-328c`/`-328a`), 상태 `104d7a..104d7c`
  - sprite 큐: `107f34..`(`-cc`), `108b34..108d33`, `108d34` `108d36` `108d3c` `108d3d` `108d3e..108d4d`
  - 열 객체 `109156` `10b1d6` `10d256` `10d2d6`(+`26` `3a..79` `7a` `7c` `7e`)
  - sound timer `10d68c`(`568c`), `10f001` `10f003`(`7003`) `10f004` `10f006` `10f007`
  - BIOS 변수 `10fd80` `10fd82` `10fdaf` `10fdb4`

## block 목록과 실행 의미

표기는 H1과 같다. `(→x)`는 fall-through, "FLOW"는 C 보존, "RTE"는 결정 2, "경계"는 F6a 밖 대상이다. 태그가 없는 block은 Unknown이다. 반복 cell은 처음과 패턴만 적는다.

**vblank IRQ `20c` 10**
- `20c`: port `3c000c`/2 = 6; BYTE `10fd80` 검사; bit7=1(음수)이면 `224` (→`21e`)
- `21e`: `JMP c00438`(BIOS INT1 경계) — FLOW
- `224`: `MOVEM.L D0-D7/A0-A6,-(A7)`(A6..A0, D7..D0 순서 60바이트), A5 = `108000`, WORD push `-3272(A5)`(`104d8e`), WORD push `-7ff0(A5)`(`100010`), A0 = LONG `-7ffa(A5)`(`100006`), `JSR (A0)`(복귀 `23c`, 결정 4)
- `23c`: `JSR c8c` — FLOW
- `242`: `JSR c0044a`(BIOS 경계, E4 선언 resume는 driver가 한다) — FLOW
- `248`: port `3c0004`/2 = 0, A5 = `108000`, WORD `-7ff0(A5)` = WORD pop, `MOVEM.W D0/D7,-(A7)`(D7.W를 A7−2에, D0.W를 A7−4에 쓴다; 첫 쓰기가 방금 pop한 bank 자리를 덮는다), `D7.W` = WORD `-7ff0(A5)`, `D0.W` = `D7.W`, `D7.W` = ((`D7.W`+1) << 12) & `ffff`, PVC `2ffff2` = `D7.W`, `2ffff0` = 0, `MOVEM.W (A7)+,D0/D7`(부호 확장 LONG), `D0.W` = WORD pop, WORD `-3272(A5)` = `D0.W`, port `3c0000`/2 = `D0.W`, `D0.W` = 읽기 `3c0006`/2(E7), `D0.B` &= 8, BYTE `-7ffe(A5)`(`100002`) = (`D0.B`≠0 ? `ff` : 0), `MOVEM.L (A7)+,D0-D7/A0-A6`, `RTE` — RTE
- `29c`: BYTE `10fd80` 검사; bit7=0이면 `2ce` (→`2a4`)
- `2a4`: LONG push A5, A5 = `108000`, WORD push `-3272(A5)`, A5 = LONG `-7ff6(A5)`(`10000a`), `JSR (A5)`(복귀 `2b6`, 결정 4)
- `2b6`: port `3c000c`/2 = 2, WORD `104d8e` = WORD(A7), port `3c0000`/2 = WORD pop, A5 = LONG pop, `RTE` — RTE
- `2ce`: port `3c000c`/2 = 2, `RTE` — RTE

**기본 callback 1**
- `3dcc`: `RTS` — FLOW

**credit `a2c`/`a4e`/`a74` 26**
- `a2c`: A0 = `100004`, `D1` = 1, `D2.B` = BYTE(A0)+ (→`a36`)
- `a36`: `D0.B` >>= 1(논리, C = 나간 bit); C=0이면 `a46` (→`a3c`)
- `a3c`: `D2.B` −= 1; 빌림이면 `a46` (→`a42`)
- `a42`: `D0.B` |= 2 (→`a46`)
- `a46`: `D2.B` = BYTE(A0)+, `DBRA D1,a36` (→`a4c`)
- `a4c`: `RTS` — FLOW
- `a4e`: A0 = `100004`, `D1` = 1 (→`a56`)
- `a56`: `D0.W` >>= 1(논리); C=0이면 `a6c` (→`a5c`)
- `a5c`: `D7.B` = BYTE(A0); 0이면 `a6c` (→`a62`)
- `a62`: `D6.W` = 0(`SUB.W D6,D6`: X=0), `D6.B` = 1, `D7.B` = BCD(`D7.B` − `D6.B` − X)(`SBCD`), BYTE(A0) = `D7.B` (→`a6c`)
- `a6c`: A0 += 1, `DBRA D1,a56` (→`a72`)
- `a72`: `RTS` — FLOW
- `a74`: `D0.B` = BYTE `10fdaf`; = 1이면 `a92` (→`a82`)
- `a82`: `D0.B` = 2이면 `abc` (→`a8a`)
- `a8a`: BYTE `10fdb4` = 0, `RTS`
- `a92`: BYTE `10fd82` ≠ 0이면 `abc` (→`a9c`)
- `a9c`: `D0.B` = BYTE `10fdb4` & BYTE `10f004`; 0이면 `aba` (→`aac`)
- `aac`: BYTE `10fdb4` = 0, BYTE `10fdaf` = 2 (→`aba`)
- `aba`: `RTS` — FLOW
- `abc`: `D0.B` = BYTE `10fdb4`; BYTE `10fd82` ≠ 0이면 `ad0` (→`acc`)
- `acc`: `BSR a2c`(복귀 `ad0`) — FLOW
- `ad0`: `D0.B` &= BYTE `10f004`, `D1.B` = ~BYTE `10f006`, `D0.B` &= BYTE `10f007`, BYTE `10f006` |= `D0.B`, BYTE `10fdb4` = `D0.B`; 0이면 `afc` (→`af4`)
- `af4`: BYTE `10fdaf` = 2 (→`afc`)
- `afc`: BYTE `10fd82` ≠ 0이면 `b0a` (→`b06`)
- `b06`: `BSR a4e`(복귀 `b0a`) — FLOW
- `b0a`: `RTS` — FLOW

**credit 요청 `bbe` 6**
- `bbe`: BYTE `10fd82` = 0이면 `bca` (→`bc8`)
- `bc8`: `RTS` — FLOW
- `bca`: `D0.B` = BYTE `100014`; 0이면 `bec` (→`bd4`)
- `bd4`: BYTE `10fdb4` |= `D0.B`, `JSR a74`(복귀 `bde`)
- `bde`: `D0.B` = ~BYTE `10fdb4`, BYTE `100014` &= `D0.B` (→`bec`)
- `bec`: `RTS` — FLOW

**서비스 `c8c` 20**
- `c8c`: BYTE `-7fe7(A5)`(`100019`) bit7 검사·set; 원래 0이면 `c98` (→`c96`) — FLOW
- `c96`: `RTS`(재진입) — FLOW
- `c98`: BYTE `-7fea(A5)`(`100016`) += 1; carry(`ff`→0)이면 `caa` (→`ca0`)
- `ca0`: port `300001`/1 = `D0.B`, `BRA cb0`
- `caa`: BYTE `-7fea(A5)` = `ff` (→`cb0`)
- `cb0`: `JSR bbe`(복귀 `cb6`) — FLOW
- `cb6`: BYTE `-7fe5(A5)`(`10001b`) bit7 = 0이면 `d36` (→`cbe`)
- `cbe`: `JSR 72fa`(F6b 경계, 복귀 `cc4`) — FLOW
- `cc4`: BYTE `10f001` bit4 = 0이면 `cd6` (→`cd0`) — FLOW
- `cd0`: port `3a0011`/1 = `D0.B` (→`cd6`)
- `cd6`: `JSR 1adf8`(복귀 `cdc`) — FLOW
- `cdc`: `JSR 16cfa`(복귀 `ce2`) — FLOW
- `ce2`: A6 = LONG `-77e4(A5)`(`10081c`) (→`ce6`) — FLOW
- `ce6`: A6 ≥ `10081c`(부호 없는 32 bit)이면 `d36` (→`cf0`)
- `cf0`: port `300001`/1 = `D0.B`, WORD `-7ff0(A5)` = 0, PVC `2ffff2` = `1000`, `2ffff0` = 0, `MOVEM.L (A6)+,D0-D7/A0-A5`(14 LONG), A6 += 8, LONG `-77e4(A5)`(복원된 A5 기준) = A6, LONG push `d2a`, LONG push LONG(A6−4)(A6 −= 4), A6 = LONG(A6−4)(A6 −= 4 뒤 읽기), A5 = `108000`, `RTS`(task PC, 결정 5). 순서는 `interrupt-task.md`의 읽기·쓰기 순서와 같다.
- `d2a`: A5 = `108000`, A6 = LONG `-77e4(A5)`, `BRA ce6` — FLOW
- `d36`: BYTE `10f001` bit4 = 0이면 `d48` (→`d42`) — FLOW
- `d42`: port `3a0001`/1 = `D0.B` (→`d48`)
- `d48`: `JSR 3cac`(복귀 `d4e`) — FLOW
- `d4e`: BYTE `-7fe7(A5)` = 0, `RTS`

**sound/Z80 `3cac` 14**
- `3cac`: `JSR 48156`(복귀 `3cb2`) — FLOW
- `3cb2`: `D0.B` = 읽기 `320000`/1(결정 6), BYTE `-3284(A5)` = `D0.B`, BYTE `-3285(A5)` bit7 검사·clear; 원래 0이면 `3cd6` (→`3cc6`)
- `3cc6`: BYTE `-3286(A5)` = `ff`, port `320000`/1 = 3, `RTS`
- `3cd6`: `D0.B` ≠ 1이면 `3ce0` (→`3cde`)
- `3cde`: `RTS` — FLOW
- `3ce0`: BYTE `7003(A5)`(`10f003`) bit7 검사·clear; 원래 0이면 `3cfa` (→`3cea`) — FLOW
- `3cea`: BYTE `-3286(A5)` = `ff`, port `320000`/1 = `7f`, `RTS`
- `3cfa`: `D1.W` = WORD `-328c(A5)`; = WORD `-328a(A5)`이면 (→`3d06`), 아니면 `3d08`
- `3d06`: `RTS` — FLOW
- `3d08`: A0 = A5 − `330c`, `D0.B` = BYTE(A0 + sext(`D1.W`)), `D1.W` = (`D1.W`+1) & `7f` (→`3d16`)
- `3d16`: `D1.W` = WORD `-328a(A5)`이면 `3d2e` (→`3d1e`)
- `3d1e`: `D0.B` ≠ BYTE(A0 + sext(`D1.W`))이면 `3d2e` (→`3d26`)
- `3d26`: `D1.W` = (`D1.W`+1) & `7f`, `BRA 3d16`
- `3d2e`: WORD `-328c(A5)` = `D1.W`, port `320000`/1 = `D0.B`, `RTS`

**sound timer `48156` 6**
- `48156`: `D0.W` = WORD `568c(A5)`(`10d68c`); 0이면 `4817e` (→`4815e`)
- `4815e`: `D0.W` ≤ `f`(부호 있는)이면 `48170` (→`48166`)
- `48166`: `D0` = 0, WORD `568c(A5)` = 0, `BRA 48174`
- `48170`: WORD `568c(A5)` += 1 (→`48174`)
- `48174`: `D0.W` += `19c0`, `JSR 3af8`(routing된 sound, 복귀 `4817e`)
- `4817e`: `RTS` — FLOW

**열 제어 `1adf8` 5**
- `1adf8`: WORD `-7ff0(A5)` = 1, PVC `2ffff2` = `2000`, `2ffff0` = 0, A0 = `109156`, `JSR 187d8`
- `1ae1a`/`1ae26`/`1ae32`: A0 = `10b1d6`/`10d256`/`10d2d6`, `JSR 187d8` — FLOW
- `1ae3e`: WORD `-7ff0(A5)` = 0, PVC `2ffff2` = `1000`, `2ffff0` = 0, `RTS`

**열 갱신 `187d8` 69(머리 4 + cell 32×2 + RTS)**
- `187d8`: BYTE `7a(A0)` bit0 = 0이면 `18be6` (→`187e2`) — FLOW
- `187e2`: BYTE `7a(A0)` bit7 검사·clear; 원래 0이면 `18be6` (→`187ec`) — FLOW
- `187ec`: `D7.W` = WORD `26(A0)`; 음수이면 `18be6` (→`187f4`)
- `187f4`: 다음을 한 block으로 실행한 뒤, 조건 `D3.W` ≤ `D6.W`(부호 없는; `BLS`)이면 `18836`으로 가고, 아니면 (→`18834`)로 간다.
  - `D6.W` = `D7.W` + `8401`, `D7.W` += `8201`, `SWAP D7`, `SWAP D6`
  - `D6.W` = WORD `7c(A0)` << 7, `D0.W` = WORD `7e(A0)` << 7
  - A1 = A0 + `3a`, `D5` = `10000`, `D4.W` = `800`, `D3.W` = `a000`, A4 = `3c0000`
  - cell 0 앞부분: `D7.W` = `D0.W`, `D1.W` = WORD(A1)+, `D6.W` += `400`
- cell k(k = 0..31, `c` = `18834` + `1e`·k):
  - `c`: `D7.W` += `D1.W` (→`c+2`)
  - `c+2`: `D6.W` −= `400`, port `3c0000`/4 = `D6`, `D6` += `D5`, `D6.W` += `D4.W`, port `3c0000`/4 = `D7`, `D7` += `D5`. k < 31이면 다음 cell 앞부분(`D7.W` = `D0.W`, `D1.W` = WORD(A1)+, `D6.W` += `400`)을 실행하고, `BLS`이면 `c+1e+2`, 아니면 (→`c+1e`)로 간다. k = 31이면 `18be6`으로 간다.
- `18be6`: `RTS` — FLOW
- [F] cell 시작은 `18834 18836 18852 18854 … 18bd6 18bd8`(64개)이다.

**clear run `16092`/`166a0` 2 + 계산 진입 381**
- `16092`: `D0.W` += `8201`, `SWAP D0`, `D0.W` = `8000`, `D2` = `10000`, `D1.W` = −`D1.W`, `D1.W` ×4, A1 = `1669e`, `JMP (A1 + sext(D1.W))`(결정 3)
- `166a0`: `D0.W` += `8200`, `SWAP D0`, `D0.W` = `8000`, `D2` = `ffff0000`, `D1.W` ×4, A1 = `1669e`, `JMP (A1 + sext(D1.W))`(결정 3)
- run 진입 e = `1669e` − 4n(n = 0..380, `160ae..1669e`): n > 0이면 n회 { port `3c0000`/4 = `D0`; `D0` += `D2` }를 실행하고 `RTS`(`1669e`)로 간다. n = 0은 `RTS`뿐이다. 진입마다 block 하나다(parametric 실행부 허용, 시험은 381 진입 전부).

**sprite flush 구동 `16cfa` 34**
- `16cfa`: A5 = `108000`, BYTE `d3d(A5)` bit7 검사·clear; 원래 0이면 `16e9e` (→`16d0a`) — FLOW
- `16d0a`: `D0.W` = WORD `d34(A5)`, `D1.W` = WORD `d36(A5)`, A0 = A1 = A5 + `b34`, A0 += sext(`D0.W`), A1 += sext(`D1.W`), BYTE `d3c(A5)` bit7 검사·반전; 원래 0이면 `16dde` (→`16d26`)
- `16d26`: LONG push A6, A6 = `3c0000`, WORD `d42(A5)` = WORD `d3e(A5)`, WORD `d4a(A5)` = WORD `d46(A5)`(A4 = A5 + `d46`) (→`16d3e`)
- `16d3e`: A1 = A0(32 bit)이면 `16d86` (→`16d44`)
- `16d44`: A2 = A5 − `cc` + sext(WORD(A0)), A0 += 2; A0 ≠ `108d34`이면 `16d56` (→`16d52`)
- `16d52`: A0 = A5 + `b34` (→`16d56`) — FLOW
- `16d56`: `D1.W` = WORD `6(A2)`, A4 = A5 + `d3e`, `D1` bit2 검사·clear; 원래 0이면 `16d6a` (→`16d66`)
- `16d66`: A4 = A5 + `d46` (→`16d6a`) — FLOW
- `16d6a`: `D7.B` = (WORD `4(A2)` ≠ `ffff`) ? `ff` : 0, `D7.W` &= 4, `D7.B` |= `D1.B`, `D7.W` = (`D7.W` ×4) & `ffff`, A3 = `f226`, `JSR (A3 + sext(D7.W))`(F6c 경계·live 대상, 복귀 `16d84`)
- `16d84`: `BRA 16d3e` — FLOW
- `16d86`: A4 = A5 + `d3e`, `D0.W` = WORD `4(A4)`, `D1.W` = WORD `6(A4)`; `D0.W` > `D1.W`(부호 있는)이면 `16d9a` (→`16d98`)
- `16d98`: `D0.W` = `D1.W` (→`16d9a`)
- `16d9a`: `D1.W` = WORD `2(A4)` − `D0.W`, `BSR 16092`(복귀 `16da4`)
- `16da4`: A4 = A5 + `d46`, 같은 비교; >이면 `16db8` (→`16db6`)
- `16db6`: `D0.W` = `D1.W` (→`16db8`)
- `16db8`: `D1.W` = WORD `2(A4)` − `D0.W`, `BSR 16092`(복귀 `16dc2`)
- `16dc2`: A6 = LONG pop, WORD `-7ff0(A5)` = 0, PVC `2ffff2` = `1000`, `2ffff0` = 0, `BRA 16e92`
- `16dde`: LONG push A6, A6 = `3c0000`, WORD `d44(A5)` = WORD `d40(A5)`, WORD `d4c(A5)` = WORD `d48(A5)` (→`16dfa`)
- `16dfa`: A1 = A0이면 `16e42` (→`16e00`)
- `16e00`: A2 = A5 − `cc`; A1 ≠ `108b34`이면 `16e10` (→`16e0c`)
- `16e0c`: A1 = A5 + `d34` (→`16e10`) — FLOW
- `16e10`: A1 −= 2, A2 += sext(WORD(A1)), `D1.W` = WORD `6(A2)`, A4 = A5 + `d3e`, `D1` bit2 검사·clear; 원래 0이면 `16e26` (→`16e22`)
- `16e22`: A4 = A5 + `d46` (→`16e26`) — FLOW
- `16e26`: `16d6a`와 같고 A3 = `13b46`이다(F6c 경계, 복귀 `16e40`).
- `16e40`: `BRA 16dfa` — FLOW
- `16e42`: A4 = A5 + `d3e`, `D0.W` = WORD `4(A4)`, `D1.W` = WORD `6(A4)`; `D0.W` < `D1.W`(부호 있는)이면 `16e56` (→`16e54`)
- `16e54`: `D0.W` = `D1.W` (→`16e56`)
- `16e56`: `D1.W` = WORD `(A4)` − `D0.W`, `BSR 166a0`(복귀 `16e5e`)
- `16e5e`: A4 = A5 + `d46`, 같은 비교; <이면 `16e72` (→`16e70`)
- `16e70`: `D0.W` = `D1.W` (→`16e72`)
- `16e72`: `D1.W` = WORD `(A4)` − `D0.W`, `BSR 166a0`(복귀 `16e7a`)
- `16e7a`: A6 = LONG pop, WORD `-7ff0(A5)` = 0, PVC `2ffff2` = `1000`, `2ffff0` = 0 (→`16e92`)
- `16e92`: WORD `d34(A5)` = WORD `d36(A5)`, C := 1, `RTS` — known Set
- `16e9e`: C := 0, `RTS` — known Clear

- [F] 실행 의미 보충: `.W`/`.B`는 나머지 bit를 보존한다. 산술은 원래 폭의 2의 보수로 명시 계산한다. 메모리 RMW(`BSET` `BCLR` `BCHG` `ADDQ.B` `OR.B` `AND.B`)는 읽은 뒤 쓴다. `SBCD`(`a62`)는 X = 0(같은 block의 `SUB.W`)인 BCD 감산이며, 결과 BYTE만 의미가 있다(이후 flag 소비 없음). `MOVEM` 쓰기 순서와 `cf0`의 큐 포인터 쓰기·읽기 순서는 `irq-envelope.md`·`interrupt-task.md`의 [F] 기록과 같다.

## carry

- [F] 소비 0. 모든 Bcc·`DBRA`·`SBCD`는 같은 block에서 만든 flag나 X를 읽는다.
- [F] FLOW_ONLY 41개(scratch `flow.py`; 명령이 모두 `LEA` `MOVEA` `ADDA` `JSR` `BSR` `BRA` `JMP` `RTS` Bcc `BTST` `BSET` `BCLR` `BCHG` `DBcc` `MOVEM`인 block): `21e` `23c` `242` `a4c` `a72` `aba` `acc` `b06` `b0a` `bc8` `bec` `c8c` `c96` `cb0` `cbe` `cc4` `cd6` `cdc` `ce2` `d2a` `d36` `d48` `3cac` `3cde` `3ce0` `3d06` `3dcc` `16cfa` `16d52` `16d66` `16d84` `16e0c` `16e22` `16e40` `187d8` `187e2` `18be6` `1ae1a` `1ae26` `1ae32` `4817e`. carry 보존 목록(`carry_preserving_pc`)에 case group 하나로 넣는다. `ce6`(`CMPA`)은 Unknown이다.
- [F] known 생산 5개: `16e92`(Set), `16e9e`(Clear), `248` `2b6` `2ce`(꺼낸 SR bit0). 나머지 147개는 Unknown이다.
- [F] run 진입 381은 `MOVE.L`/`ADD.L`이므로 Unknown이다. n = 0(`1669e RTS`)은 FLOW다.

## 경계·Waiting·external read·port 모델

- [F] **Waiting 없음.** IRQ 안의 sound 생산자 `48174 → 3af8 → 3ac8`가 ring 가득에서 `3aea` Waiting을 내면, driver는 `animation irq internal wait` checked 오류로 처리한다(범위 문서 E10). 실행부 쪽 변경은 없다(`3aea`는 기존 sound 실행부다).
- [F] **external read:** `288` 안의 `3c0006`/2(기존 queue 장치), `3cb2`의 `320000`/1(결정 6).
- [F] **port:**
  - 쓰기 한 건이 `VideoPortWrite` 한 건이다. 크기는 원본 그대로다(`MOVE.L` `3c0000` = 크기 4 한 건; D1 관례).
  - PVC는 `am_write`(bank 갱신)로 쓴다. `cf0`·`16dc2`·`16e7a`·`1ae3e`의 세 쓰기는 기존 `am_zero_bank` 순서와 같다. `248`의 PVC 쓰기는 `((bank+1)<<12)` 값이다.
- [F] **스택:**
  - `224` MOVEM 60바이트와 WORD 2개, JSR/BSR 복귀 LONG
  - `248`의 MOVEM.W push/pop, MOVEM.L pop, RTE 6바이트
  - `2a4`/`2b6`의 LONG·WORD
  - `16d26`/`16dde` LONG push A6와 pop
  - `cf0`의 LONG push 2개
  - work RAM 밖 스택은 기존 checked 오류다.

## 시험 계획(fixture)

- 단위 시험 `engine/tests/animation_machine_irq_f6a_test.cpp`(`run_animation_machine`만)를 둔다. fixture는 Unicorn 생성(scratch)이고, 원본 ROM 외 합성 code는 없다. 시험 항목은 다음과 같다.
  - 시작 193 전부: 들어오는 C clear/set × native 후속 PC·digest·port 수·C 분류
  - zero-step: 193 × C 3
  - 내부 PC 전수(정확한 오류), 홀수 PC
- 분기별 fixture:
  - `10fd80` bit7 0/1(`21e` 경계 stop)
  - 재진입(`100019` bit7=1)
  - `100016` = `fe`/`ff`(포화)
  - `10001b` bit7 0/1
  - `10f001` bit4 0/1
  - task 큐 빈/1개/32개(frame PC = `3dcc` → `d2a` → `ce6` 연쇄; 결정 5)
  - credit: `10fd82` 0/≠0, `100014` 0/≠0, `10fdaf` 0/1/2/3, `10f004`·`10f006`·`10f007` 조합, `a62` SBCD 값 0/1/`10`/`99`/`a0`
  - Z80 응답 0/1/3/`7f`/`ff`, `104d7b` bit7, `10f003` bit7, ring 빈/중복 연속/wrap(`7f`)
  - `10d68c` 0/1/`f`/`10`/`ffff`
  - 열 객체 bit0·bit7·`26(A0)` 음수, cell 32개의 `BLS` 양쪽
  - sprite flush: `108d3d` bit7 0/1, `108d3c` bit7 0/1(두 방향), 큐 빈/1개/ring wrap(`108d34`, `108b34`), A4 선택 bit2, 표 대상 8종 stop(F6c 경계)과 표 밖 착지
  - clear run: n = 0, 1, 2, 40, 379, 380, 381(run 밖), 음수 `D1`, 두 방향
  - raster callback `3dcc`와 비기본값(stop)
  - RTE: SR `2000`/`2001`(C), S=0·T=1 오류
- driver 수준(F6-D) 시험은 범위 문서 E10을 따른다.

## 검증 계획

1. **실제 ROM 차분(F6a 경계까지).**
   - Unicorn과 C++ `run_animation_machine`(+ 8 `program_rom_*.ms5d`)을 무작위 work RAM + 구조 필드에서 비교한다.
   - native는 F6a routing 밖의 첫 PC(`72fa`, writer 표 대상, `c0044a`, `c00438`, task PC)에서 멈추고, `RTE` 직전에 선언 pop을 적용한다.
   - 비교 항목: RAM 64 KiB, 레지스터 16 + PC, PVC·bank, 순서 있는 port, external read 소비, C.
2. **host-level oracle 교차(E8).**
   - `begin_irq_envelope`/`finish_irq_envelope`/`begin_raster_irq`/`finish_raster_irq`: 스택·MMIO
   - `process_credit_request`: RAM·D0
   - `refresh_scene_columns`: RAM
   - `step_sound`: RAM·port
   - `restore_interrupt_task`: task 경계 레지스터·스택 쓰기
   - `refresh_sprite_queue`: 지원 입력의 RAM·VRAM port
   - 각 API 계약이 표현하는 항목만 비교한다.
3. **자연 도달성.** 범위 문서 5절 탐침 규약(E5 P1/P2 prep, E1 A)으로 seed frame에서 IRQ를 전달한다. F6a 경계까지 native와 C++를 비교하고, 처음 닿는 경계(F6b `72fa`, F6c 표 대상)의 분포를 보고한다.
4. **회귀.** `verify_animation_machine_frame_driver.py`(D1, `irq_execution` 꺼짐) 54,400 frame 무변화, base frame pass·RNG 400 무변화, 돌연변이 검사, UBSan.

## 미확인

- [U] BIOS `c0044a`의 실제 효과, `c00438` 이후 동작.
- [U] Z80 응답과 `3c0006` bit3의 실제 값, `320000` 쓰기 3/`7f`의 의미(reset·silence로 추정 [I]).
- [U] clear run `D1`의 자연 범위(탐침 n ≤ 70).
- [U] raster callback이 `3dcc`가 아닌 값을 갖는 게임 상황(`48cb0..48e72` 등의 `100006` 참조 표는 이번에 읽지 않았다).
