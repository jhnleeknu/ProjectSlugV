# F6b IRQ palette 전송 `72fa`(일반 256 cell·특수 채우기) 계약 초안

**구현 전 계약 초안 — 메인 결정 전**

범위 근거는 F6 범위 문서(`animation-machine-irq-f6-scope.md`)의 4절 F6b 행과 결정 E6(palette RAM 모델)이다. 형식은 F5 H3 계약(반복 cell family, `animation-machine-frame-head-h3-contract.md`)을 따른다. 원본 의미의 기존 기록은 `palette-flow.md`(일반 전송 커널 `7320..871a`)와 `palette-fill.md`(특수 채우기 `873a`)다.

Claude Opus 5.5 / high 읽기 전용 분석 작업자가 작성했다. canonical BE ROM SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 범위 `72fa..8b64`는 fixed이므로 CPU 주소와 file offset이 같다. 6,250바이트, SHA256 `cd963079dbfed39ae46a67a99d9956b8f3354ec4b7a7e619891f49e1801d55a7`. 짝수 PC는 기존 routing에 없다. 앞 이웃 `72f0..72fa`(gate 술어)는 stage_entry 실행부, 뒤 `8b64`(특수 채우기 설정)는 routing 밖이고 IRQ closure 밖이다.

## 요약

- [F] **block 시작 522개.** 고유 10개 + cell 512개(256 cell × 2)다. leader 목록 SHA256은 `c34cb0b83d3971ba464484eb726095594ca111ff63871f32fe068b911bc65210`이다.
  - 고유 시작: `72fa` `7302` `730c` `7326`(cell 0 복사) `871a` `8720` `8728` `8732` `8738` `873a` `8b5c` `8b60`. 이 가운데 `7326`과 `871a`는 cell 규칙으로 센다.
  - cell 시작: k = 1..255에서 `732e + 14·(k−1)`(`BCLR #7,d16(A0)` + `BEQ`)와 그 +8(`MOVEM` 복사 쌍)이다. 마지막 cell 뒤 `871a`가 이어진다.
- [F] **진입은 `cbe JSR 72fa` 하나다**(F6a). 다른 호출자는 [U](고정 ROM 정적 탐색 미실시). `8720`은 `8b60 BRA` 대상이다.
- [F] **carry:** 소비 0, known 생산 0. FLOW 514(`BCLR`+`BEQ` cell, `MOVEM` 쌍, `7302` `8738` `8b60`), Unknown 8(`72fa` `730c` `871a` `8720` `8728` `8732` `873a` `8b5c`).
- [F] **I/O:**
  - palette RAM 쓰기 `400000..401fff`: 일반 전송은 `MOVEM.L D0-D7,d16(A1)`이고, 특수 채우기는 `MOVEM.L D0-D7,-(A0)` 256회 + `8b5c` WORD 1회다.
  - system latch 쓰기: `3a000f`(bank 0 선택; `730c` `8728`)와 `3a001f`(bank 1 선택; `8732` `873a`).
  - watchdog `300001`(`871a`).
  - device 읽기는 없다.
- [F] **자연 도달(범위 문서 5절, P1∪P2∪P2V):** 302/522다. 일반 전송의 dirty cell과 `8720` `8728` `8738`에 닿았다. 특수 채우기 `873a` `8b5c` `8b60`과 `8732`(`107dec`≠0)는 0이다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **palette RAM 표현(E6).** 권고는 E6 b다.
   - `AnimationMachineDevice`에 `std::vector<std::uint8_t> palette`(16,384바이트: bank 0 `0..1fff`, bank 1 `2000..3fff`)와 `std::uint8_t palette_bank`(0/1)를 더한다. 기본 생성은 0으로 채운 2 bank, bank 0이다.
   - `am_write`: `3a000f`·`3a001f` BYTE 쓰기(값 무관, 주소가 선택)가 `palette_bank`를 바꾸고 port 1건을 남긴다. `400000..7fffff` 쓰기는 `palette[bank*2000 + (address & 1fff)]`이고 port를 남기지 않는다.
   - `am_read`: `400000..7fffff` 읽기는 같은 mirror다(H3 `4718` 경로가 쓴다; 범위 문서 요약).
   - 크기 검사: `device.palette.size()`가 16,384가 아니면 `invalid animation machine RAM/PVC/stop PC`와 같은 입력 오류다(문구는 결정).
   - 대안 a(port만)는 범위 문서 E6에 있다.
2. **MOVEM 쓰기 순서(E6 a를 택할 경우에만 중요).** 일반 전송 `MOVEM.L D0-D7,(A1)`·`d16(A1)`은 D0..D7을 오름차순 주소로 쓴다. 특수 채우기 `MOVEM.L D0-D7,-(A0)`는 D7부터 내림차순 주소로 쓴다.
   - 68000 실기의 predecrement LONG 쓰기는 하위 WORD를 먼저 쓴다. [U] Unicorn은 LONG 단위 hook로 보고한다.
   - E6 b에서는 최종 기억 내용만 비교하므로 순서 결정이 필요 없다.
3. **반복 cell은 PC parametric 실행부를 허용한다(F5 D 관례).** cell k의 두 block은 변위 `20·k`만 다르다. 시험은 512 진입 전부를 덮는다.
4. **실행부 파일·오류 문자열.** `engine/src/animation_machine_irq_f6b.cpp`의 `animation_irq_f6b_block`. 내부 PC 진입은 `unsupported animation irq f6b PC`다(예: `873a` 블록 안 `874e..8b52`의 MOVEM PC).

## block 목록과 실행 의미

표기는 H1과 같다. 주소·변위·간격은 모두 16진이다. A5 = `108000`(호출자 `c8c` 기준; 실행부는 A5 상대로 계산한다).

**머리 3**
- `72fa`: WORD `-216(A5)`(`107dea`) ≠ 0이면 `873a` (→`7302`)
- `7302`: BYTE `-213(A5)`(`107ded`) bit7 검사·clear; 원래 0이면 `871a` (→`730c`) — FLOW
- `730c`: port `3a000f`/1 = `D0.B`(E6 b: bank 0 선택), A0 = A5 − `225e`(`105da2`), WORD(A0) &= `8000`, A1 = `400000`(직선으로 cell 0 `7320 BCLR #7,(A0)`; 원래 0이면 `732e`, 아니면 (→`7326`))
  - [F] `7320..7324`는 `730c` block에 속한다(분기 대상이 아님). cell 0의 검사는 이 block 끝이다.

**cell 512**
- `7326`(cell 0 복사): `MOVEM.L (A0),D0-D7`; `MOVEM.L D0-D7,(A1)` (→`732e`) — FLOW
- cell k(k = 1..255, s = `732e + 14·(k−1)`, d = `20·k`):
  - `s`: BYTE(A0 + d) bit7 검사·clear; 원래 0이면 `s + 14` (→`s + 8`) — FLOW
  - `s + 8`: `MOVEM.L d(A0),D0-D7`; `MOVEM.L D0-D7,d(A1)` (→`s + 14`) — FLOW
  - [F] k = 255: s = `8706`, s + 8 = `870e`, s + 14 = `871a`.
- [F] 의미: staging block k의 첫 BYTE bit7을 먼저 지우고, 원래 1이었으면 지운 뒤의 32바이트를 palette `400000 + 20·k`(선택 bank)에 복사한다. 표시 bit는 palette로 가지 않는다(`palette-flow.md`와 같음).

**꼬리 5**
- `871a`: port `300001`/1 = `D0.B` (→`8720`)
  - `D0`의 값은 마지막 MOVEM으로 바뀐 값일 수 있다(원본 그대로). `MOVE.B`는 flag를 바꾸므로 Unknown이다.
- `8720`: BYTE `-214(A5)`(`107dec`) ≠ 0이면 `8732` (→`8728`)
  - [F] `8720`은 `8b60 BRA`의 대상이라 `871a`와 따로 시작한다.
- `8728`: port `3a000f`/1 = `D0.B`, `BRA 8738`
- `8732`: port `3a001f`/1 = `D0.B` (→`8738`)
- `8738`: `RTS` — FLOW

**특수 채우기 3**
- `873a`: 다음을 차례로 한다.
  1. port `3a001f`/1 = `D0.B`(bank 1 선택)
  2. A0 = `400000` + sext(WORD `-216(A5)`)
  3. A1 = A5 − `25e`(`107da2`), `MOVEM.L (A1),D0-D7`
  4. 256회 `MOVEM.L D0-D7,-(A0)`(A0 −= 32씩; 쓰기 8 LONG, D7이 가장 높은 주소)
  5. WORD `-216(A5)` −= `2000`; 결과 ≠ 0이면 `8b60` (→`8b5c`)
  - [F] palette 주소는 `400000 + sext(counter) − 32·(i+1)`다. counter `2000`이면 bank 전체 `400000..401fff`다. 그 밖의 counter는 `400000` 아래(`3fexxx`, palette 밖)나 mirror로 간다. 이 경우 E6 b에서는 `400000..7fffff` 밖 쓰기가 기존 `unsupported animation machine write device` checked 오류다([I] 원본 하드웨어에서는 다른 장치에 쓴다). [F] `palette-fill.md`는 counter `2000`만 확인했다.
- `8b5c`: WORD(A0) = 0 (→`8b60`)
- `8b60`: `BRA 8720` — FLOW

## carry

- [F] 소비 0. 모든 `BEQ`/`BNE`는 같은 block의 `BCLR`/`TST`/`SUBI`가 만든 flag를 읽는다.
- [F] FLOW 514: `7302`, `7326`, cell k의 `s`/`s + 8`(510), `8738`, `8b60`. carry 보존 목록에 범위식(`7326` ≤ pc < `871a` 짝수, `7302`, `8738`, `8b60`)으로 넣는다.
  - [F] `7326..871a` 안의 짝수 PC 가운데 block 시작이 아닌 PC는 내부 PC이고 보존 목록 판정과 무관하다.
- [F] Unknown 8: `72fa` `730c` `871a` `8720` `8728` `8732` `873a` `8b5c`.

## 경계·port·자료

- [F] 경계: 없음. F6b는 RTS로 `cc4`(F6a)에 돌아간다.
- [F] port:
  - `3a000f`/`3a001f`/`300001`은 BYTE 1건씩이다.
  - palette 쓰기는 E6 b에서 port가 아니다. E6 a를 택하면 MOVEM LONG 8건/cell이고, 특수 채우기는 2,048 LONG + WORD 1건이다.
- [F] RAM:
  - `105da2..107da1`(staging 256×32, `-225e`)
  - `107da2..107dc1`(채우기 pattern, `-25e`)
  - `107dea`(counter, `-216`), `107dec`(표시 bank, `-214`), `107ded`(pending, `-213`)
- [F] 다른 단위와의 관계: H3(`5728` palette frame)가 staging·pending을 만들고, F5 gate(`47af0`/`478de` → `72f0`)가 pending을 기다린다. 이 IRQ 경로가 그 대기의 실제 해제다(범위 문서 2절).

## 시험 계획(fixture)

- 단위 시험 `engine/tests/animation_machine_irq_f6b_test.cpp`(`run_animation_machine`만).
- 시작 522 전부(들어오는 C clear/set × 후속 PC·digest·C 분류), zero-step, 내부 PC 전수(`873a` 블록 내부 254개 MOVEM PC 포함), 홀수 PC를 시험한다.
- 분기 fixture:
  - `107dea` 0/`2000`/`4000`(bank 1 채우기 1회와 2회 연속, `8b5c` 유무)
  - `107ded` bit7 0/1
  - dirty 패턴: 단독 256종, 전부, 교대, 없음(기존 `verify_palette_upload.py`의 259 패턴 재사용)
  - `107dec` 0/≠0
  - palette bank 초기 0/1
- E6 b 장치 시험(`animation_machine_device_test.cpp` 확장):
  - mirror 주소(`400000` `401fff` `402000` `7fffe0`), bank 선택 순서, 읽기 mirror
  - palette 크기 오류
  - 실패 시 palette·bank rollback
- counter가 `2000`의 배수가 아닌 값(예: `1000`, `ffe0`): `400000` 아래 쓰기에서 checked 오류와 상태 보존.

## 검증 계획

1. **실제 ROM 차분.** Unicorn(palette RAM `400000..7fffff`를 8 KiB 두 bank mirror로 map, `3a000f`/`3a001f` 쓰기 hook로 bank 전환)과 C++를 비교한다. 비교 항목은 RAM, palette 16 KiB, bank, port, 레지스터다. 입력은 무작위 staging·counter·pending 조합이다.
2. **host-level oracle(E8).** 같은 입력에서 `transfer_palette_banks`(counter 0/`2000`)의 RAM·bank 0/1·표시 bank 결과와 비교한다. 기존 API의 `palette0`/`palette1`과 E6 b의 bank 0/1을 대응시킨다.
3. **자연 도달.** 범위 문서 5절 탐침 규약으로 IRQ를 전달하고 F6b 구간(`cbe` → `cc4`)을 native와 비교한다. 특수 채우기는 자연 0이므로 fixture로만 덮는다.
4. 회귀·돌연변이·UBSan은 F6a와 같다.

## 미확인

- [U] `72fa`의 다른 호출자(IRQ 밖) 여부.
- [U] counter가 `2000`/`4000` 외 값일 때의 원본 의도(`8b64` 설정은 `2000`만 만든다; `palette-fill.md`).
- [U] palette RAM 쓰기의 실제 bus 순서·대기(E6 b에서는 비교하지 않는다).
- [U] `3a000f`/`3a001f`가 표시 bank인지 CPU 접근 bank인지의 구분. MAME `set_palette_bank`는 하나의 bank 선택으로 둘 다를 바꾼다([I] 단일 선택으로 모델).
