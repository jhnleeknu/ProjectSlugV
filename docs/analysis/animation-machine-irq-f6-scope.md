# F6 vblank IRQ `20c`/`c8c` 실행 범위와 단위 분할

**구현 전 계약 초안 — 메인 결정 전**

Claude Opus 5.5 / high 읽기 전용 분석 작업자가 작성했다(2026-10-15). 구현·검증 기록이 아니다. 단위 계약은 `animation-machine-irq-f6a-contract.md`, `animation-machine-irq-f6b-contract.md`, `animation-machine-irq-f6c-contract.md`에 있다.

기준:
- canonical BE ROM `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 문서의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. ROM은 읽기만 했다.
- 작업 트리 `/home/user/ProjectSlugV`, branch `claude/projectslugv-work-cycle-yout6u`, HEAD `3b63864`. routing은 `engine/src/animation_machine.cpp`의 dispatch 사슬(규칙 98개)을 scratch `route.py`로 해석했다.
- 정적 leader 규칙은 F4 rescope·F5와 같다. 분기 대상, 조건 분기 fall-through, JSR/BSR 복귀점, BRA.W 표 항목, 계산 점프(Duff·`JMP (A1,D1.W)`) 진입, push된 복귀 주소(`MOVE.L #d2a,-(A7)`)를 센다. 함수 걷기는 이미 routing된 PC에서 멈춘다.
- scratch(저장소 밖): `/tmp/claude-0/-home-user-ProjectSlugV/f54ebccc-3a36-5cdd-acbe-c0f66dd6e25d/scratchpad/ana_irq/`. `route.py`, `clos2.py`(closure), `units.py`(단위 leader, `units.json`), `flow.py`(C 분류), `cmpfam.py`(writer family 비교), `rte_test.py`, `probe_irq.py`(native 도달성 탐침), `summ.py`, `cov.py`.

표기: [F]는 원본 바이트, 기록 산출물 또는 scratch Unicorn 탐침에서 확인한 사실이다. [I]는 추론, [U]는 미확인이다. 탐침은 선언 모델을 Unicorn에서 돌린 것이다. BIOS 실행, 자연 IRQ 시간축, 자연 boot를 주장하지 않는다.

## 요약

- [F] **vector와 진입.** vector `64`(level 1) = `20c`, `68`(level 2) = `29c`, `6c`(level 3) = `20c`이다. pinned MAME `neogeo.cpp`에서 `m_vblank_level = 1`, `m_raster_level = 2`이므로 `20c`가 vblank IRQ, `29c`가 raster(timer) IRQ다.
- [F] **정적 closure(vector `64`/`68` + 기본 callback `3dcc`).** routing되지 않은 함수가 15개 있다(`20c` `29c` `c8c` `bbe` `a74` `a2c` `a4e` `72fa` `1adf8` `187d8` `16cfa` `16092` `166a0` `3cac` `48156`). 여기에 IRQ 전용 sprite writer family 2개(표 `f226` 8 routine, 표 `13b46` 8 routine)가 더해진다. 이미 routing된 callee는 `3af8`(sound) 하나다. BIOS 대상은 `c00438`(JMP), `c0044a`(JSR) 두 곳이다.
  - F5 범위 문서 2.5절의 "함수 15개, block 712개"는 writer 표를 따라가지 않은 수다. 이 문서의 수(아래 표)와 같은 규칙으로 세면 writer family를 뺀 부분이 F6a 191 + F6b 522 = 713이다(`d2a`/`ce6` 제외).
- [F] **단위 분할(아래 4절).**

  | 단위 | 내용 | 정적 block | 계산 진입(추가 block 시작) | 고유 코드 |
  | --- | --- | --- | --- | --- |
  | F6a | IRQ 껍질·서비스 `c8c`·credit·sound/Z80·열 제어·sprite flush 구동·clear run | 193 | clear run 381 | 약 130 |
  | F6b | palette 전송 `72fa`(일반 256 cell + 특수 채우기) | 522 | 0 | 10 + cell 1종 |
  | F6c | IRQ sprite writer family A(`f226..11792`)·B(`13b46..16092`) | 624 + 616 = 1,240 | Duff 128 + 128 | H8/H4 template + 편집 3종 |

- [F] **seed는 IRQ를 받을 수 없는 상태다.** `stage_entry_body` seed 142개 모두 BYTE `10fd80`=0, LONG `100006`=`10000a`=0, LONG `10081c`=0, BYTE `100017`=0, BYTE `10001b`=0이다.
  - 그대로 IRQ를 넣으면 `20c`가 `JMP c00438`(BIOS가 IRQ를 처리하는 mode)로 간다. bit7을 강제로 켜도 `JSR (0)`과 A6=0 task 복구(`ce2`)로 깨진다.
  - 원본 게임 초기화(`9e4 JSR 3dce`, `a08 JSR c42`, `a1e BSET #7,10fd80`, `a26 JMP 2aac`)가 이 값을 만든다. seed는 이 경로를 거치지 않은 host API 산출물이다.
- [F] **native 도달성 탐침**(`probe_irq.py`, D1 frame 규약에서 IRQ 효과를 가진 선언 해제를 실제 IRQ 실행으로 바꿈, 142 seed × 최대 400 frame, 아래 5절).
  - IRQ 실행 자체는 15,248회 전부 정상 복귀(RTE)했다. 레지스터 D0–D7/A0–A6, A7, SR이 IRQ 전과 같았다.
  - 그러나 자연 seed 137개 중 96개(P2) 또는 124개(P1)가 frame 21–33에서 H3 palette 준비 `4722`가 `42bcf4`를 읽어 멈췄다. 이 주소는 palette RAM mirror(`400000..7fffff`)다.
  - 원인 [F]: IRQ `72fa`가 `107ded` bit7을 지우면 head `718c` gate가 열린다. 그러면 palette 준비(`7196..722a`)가 매 frame 돈다. 그 과정에서 ID `ffff`, 참조 `ffff`인 slot 12를 처리한다(source = `22bd12 + ffff×32`).
  - 선언 모델(D1)에서는 gate가 거의 열리지 않아 이 경로가 숨어 있었다. [I] 실제 하드웨어에서는 palette RAM mirror를 읽는 무해한 경로다. 따라서 palette RAM을 device 기억으로 모델하는 결정(E6)이 자연 완주의 전제다.
  - [F] palette RAM mirror를 map한 재탐침(6절)에서는 P1·P2 모두 자연 136 seed가 400 frame을 완주했다. 이는 D1 기준선과 같다. IRQ 수는 P2 8,100(= D1의 `16bd0` 선언 해제 수), P1 108,528(frame당 2)이었다.
- [F] **Unicorn 2.1.4 M68K는 `RTE`를 실행하지 못한다.** `rte_test.py`에서 intr hook이 없으면 `UC_ERR_EXCEPTION`이 났고, hook이 있으면 intr 번호 256(EXCP_RTE)이 PC `RTE`에서 보고됐다. 두 경우 모두 SR·PC·A7이 바뀌지 않았다. native 검증은 RTE를 선언 단계로 에뮬레이트해야 한다(E3).
- [F] **기존 host-level API**(`irq_envelope` `interrupt_init` `interrupt_service` `interrupt_task` `credit_request` `column_control` `palette_transfer`/`palette_upload` `sound_service` `sprite_refresh_queue`)는 같은 원본 PC의 함수 단위 의미 구현이다. 그러나 block 실행부의 계약과 다르다. 이 API들은 CCR, task 본문, 지원 밖 입력을 거부하고 palette를 별도 bank vector로 다루며 스택 일부를 생략한다. 따라서 F6 실행부가 직접 부르지 않고 차등 검증 oracle로 쓴다(E8).

## 1. 원본 흐름

[F] `20c`(vblank, level 1):
1. `3c000c` := 6(IRQ ack)을 쓴다.
2. BYTE `10fd80` bit7이 0이면 `21e JMP c00438`(BIOS INT1; 종단)이다.
3. 그렇지 않으면 `224`가 D0–D7/A0–A6을 push하고(60바이트) A5 := `108000`으로 둔다. WORD `104d8e`(VRAM 주소 사본)와 WORD `100010`(bank 사본)을 push한다.
4. `JSR (LONG 100006)`로 raster callback을 부른다(기본 `3dcc RTS`).
5. `23c JSR c8c`, `242 JSR c0044a`(BIOS SYSTEM_IO)를 차례로 실행한다.
6. `248`은 다음을 하고 `29a RTE`로 끝난다.
   - `3c0004` := 0
   - bank 사본 복구, PVC bank 복구(`2ffff2` := (bank+1)<<12, `2ffff0` := 0)
   - VRAM 주소 복구(`104d8e`, `3c0000` WORD)
   - `3c0006` bit3 → BYTE `100002`(`SNE`)
   - 레지스터 pop

[F] `c8c`(서비스):
1. BYTE `100019` bit7을 test-and-set한다. 이미 1이면 `RTS`다(재진입).
2. BYTE `100016`을 255에서 포화 증가시킨다. 증가 전 값이 255 미만이면 watchdog `300001` := D0.B를 쓴다.
3. `JSR bbe`(credit)를 실행한다.
4. BYTE `10001b` bit7이 1일 때만 다음을 한다.
   - `JSR 72fa`(palette 전송)
   - `10f001` bit4가 1이면 `3a0011` := D0.B
   - `JSR 1adf8`(배경 열 제어 4개)
   - `JSR 16cfa`(sprite flush)
   - `ce2` task 큐 복구: LONG `10081c` < `10081c`이면 frame 복구 뒤 `RTS`로 task 본문에 들어간다. 복귀점은 `d2a`이고, `d2a`는 다시 `ce6`으로 간다.
5. `d36`: `10f001` bit4가 1이면 `3a0001` := D0.B, `JSR 3cac`(sound/Z80), BYTE `100019` := 0, `RTS`.

[F] `29c`(raster, level 2): BYTE `10fd80` bit7이 0이면 `3c000c` := 2, `RTE`. 1이면 A5를 push하고 VRAM 주소를 push한 뒤 `JSR (LONG 10000a)`를 부른다. 그다음 `3c000c` := 2, VRAM 주소 복구, A5 pop, `RTE`. 자연 frame 모델에서 이 IRQ를 넣을 시점은 없다([I]; timer 설정 근거 없음). fixture 전용이다.

## 2. head·N과 IRQ의 접점(선언 해제 지점)

[F] 현재 D1 driver의 선언 해제 6종 중 5종은 IRQ 효과의 대용이다. 각 대기 block은 flag를 먼저 만드는 명령으로 시작하므로 들어오는 C를 소비하지 않는다(`ef2 MOVE.B/CMP.B`, `16bd0 CMP.W`, `3aea CMP.W`, `cda4 CMP.W`, `47af0`/`478de JSR 72f0`의 `SUBI.B`).

| 대기 PC | 조건 | 현재 선언 해제 | 실제 IRQ 효과(원본) |
| --- | --- | --- | --- |
| `ef2`(H) | BYTE `100016` < BYTE `100017` | `100016` := `100017` | `c98` 포화 +1(IRQ 1회당 1) |
| `16bd0`(H) | WORD `108d34` ≠ `D0.W` | `108d34` := D0 | `16cfa`(`10001b` bit7·`108d3d` bit7 필요)가 `16e92`에서 `108d34` := `108d36` |
| `cda4`(N) | WORD `108d34` ≠ `D4.W` | `108d34` := D4 | 같음 |
| `3aea`(N, sound ring 가득) | WORD `104d74` = 다음 쓰기 cursor | `104d74` := `ffff` | `3cac`가 Z80 응답 조건이 맞으면 read cursor `104d74`를 전진(중복 byte 건너뜀) |
| `47af0`/`478de`(N, gate) | `107ded` bit7 = 1 | `107dea`=0이면 bit7 clear | `72fa`: `107dea`≠0이면 특수 채우기(`107dea` −= `2000`), 0이면 bit7 clear 뒤 전송 |
| `c00468`(카드 BIOS) | — | 선언 resume | IRQ와 무관(유지) |

## 3. 결정 필요 항목(MAIN DECISION NEEDED)

### E1. IRQ 전달 시점(schedule)

- 선택 A(**권고**): **대기 해제 대체.** 위 표의 IRQ 효과 대기 5종(`ef2` `16bd0` `cda4` `3aea` `47af0`/`478de`)에서 Waiting이 나올 때마다 다음을 한다.
  1. IRQ를 한 번 실행하고(E2–E5), 같은 대기 block을 다시 실행한다.
  2. 대기가 풀릴 때까지 반복한다. 구간당 전달 상한은 기존 `MAX_WAITS` 16과 공유한다.
  3. IRQ가 대기 조건을 바꾸지 못하면 상한에서 `animation irq wait not released` checked 오류다(예: `10001b` bit7=0이라 `16cfa`가 돌지 않는 경우).
  - 장점: 기존 D1 구간 구조와 Waiting 어휘를 그대로 쓰고, IRQ가 원본이 실제로 기다리는 지점에서만 들어간다.
  - [F] 탐침 P2에서는 `16bd0`에서만 2,386회 전달됐고 매번 1회로 풀렸다. P1(`100017`=2)에서는 `ef2`에서 frame당 2회, 15,248회였고 `16bd0` 대기는 0회였다.
- 선택 B: A + **vblank tick.** H가 `ef2`에 도착할 때마다(대기 여부와 무관, pause 루프 반복 포함) IRQ 1회를 먼저 넣는다. frame당 vblank 1회 이상을 보장한다. [F] 탐침 P2V는 7,624회였다.
- 선택 C: frame 경계(H 시작 전)에 고정 횟수를 넣는다. 원본이 기다리지 않는 지점이라 비권고다.
- [I] 어느 선택도 자연 시간축이 아니다. 실제 IRQ는 N pass 중간에도 들어온다. 선언 schedule임을 기록에 남긴다.

### E2. 전달 시 CPU 상태(예외 frame)

- **권고:** 68000 group 1/2 예외 frame을 실제 스택에 만든다.
  1. A7 −= 4, LONG(A7) := 대기 PC를 쓴다.
  2. A7 −= 2, WORD(A7) := 선언 SR `2000`을 쓴다(S=1, mask 0, CCR 0).
  3. PC := LONG ROM[`64`] = `20c`, carry Unknown으로 둔다.
  4. IRQ 안의 SR(mask 1)은 실행부가 표현하지 않는다. IRQ 안에 SR을 읽는 명령은 없다([F] closure 안의 CCR 명령은 `16e98 ORI #1,CCR`·`16e9e ANDI #fe,CCR`뿐이다).
- 대안: push SR에 현재 known C를 넣는다(`2000|C`). 대기 block은 C를 소비하지 않으므로 이득이 없고, native 비교에서 실제 CCR을 정규화해야 한다. 비권고다.
- native harness는 전달 직전에 SR := `2000`으로 정규화한다. FH 관측기의 controller skip 정규화와 같은 방식이며 선언 단계로 기록한다.
- 스택은 main 스택 그대로다(supervisor 단일 스택). [F] 탐침에서 IRQ가 쓰는 깊이는 frame 6 + 레지스터 60 + 4 + callee 수십 바이트다. 모두 work RAM `10exxx`(A7 `1fexxx`의 mirror) 안이다.

### E3. RTE

- **권고:** 실행부 block `248`·`2b6`·`2ce`의 끝 `RTE`는 다음을 한다.
  - SR := WORD(A7), PC := LONG(A7+2), A7 += 6을 실행한다.
  - carry := 꺼낸 SR bit0이다(known C; 선언 `2000`이면 Clear).
  - 꺼낸 SR의 S bit(13)가 0이거나 trace bit(15)가 1이면 `unsupported animation irq RTE status` checked 오류다. 실행부는 user 스택을 표현하지 않는다.
- driver는 IRQ 구간을 stop PC = 대기 PC로 실행한다. `RTE` 뒤 PC = 대기 PC에서 Returned가 된다.
- driver는 IRQ 전후로 D0–D7/A0–A6·A7이 같은지 확인한다. 다르면 `animation irq register restore mismatch` checked 오류다(무결성 검사; [F] 탐침 15,248/15,248 같음).
- native는 `29a`/`2cc`/`2d6`의 `RTE` 직전에 멈추고 같은 선언 RTE(pop SR WORD, PC LONG, A7 += 6)를 적용한다. [F] Unicorn이 RTE를 실행하지 못하기 때문이다(요약). 그래서 RTE block의 native 근거는 "직전 상태 + 선언 pop"이다.

### E4. BIOS

- `242 JSR c0044a`(SYSTEM_IO, **권고**): 선언 resume으로 둔다. driver는 IRQ 구간을 stop `c0044a`로 한 번 실행하고, PC := LONG(A7)(= `248`), A7 += 4, C Unknown으로 둔 뒤 기록하고 stop = 대기 PC로 이어간다. RAM 효과는 없다고 선언한다.
  - [U] 실제 BIOS는 입력·`10fdxx` BIOS 변수를 갱신한다. BIOS ROM은 제공되지 않았다(`irq-envelope.md`: mslug5.zip 13항목에 BIOS 없음).
  - 카드 BIOS(`c00468`)와 같은 driver 방식이다. 핵심 실행부를 바꾸지 않는다.
- `21e JMP c00438`(BYTE `10fd80` bit7 = 0): 종단 경계다. `c00438`이 routing 밖이라 기존 `unsupported animation machine PC`(상태 보존)다. driver가 이 오류를 `animation irq bios int1 boundary`로 바꿔 보고하는 것은 선택이다.
- 대안: BIOS 효과를 선언 queue로 넣는다(입력 변수). 근거 ROM이 없어 비권고다.

### E5. seed의 IRQ 초기 상태(가장 중요)

- 선택 P0: seed 그대로 둔다. 자연 IRQ 실행이 불가능하다(`c00438`). F6은 fixture로만 검증한다.
- 선택 P2(**회귀 연결용 권고**): 선언 prep = BYTE `10fd80` |= `80`, LONG `100006` = LONG `10000a` = `3dcc`, LONG `10081c` = `10081c`. 원본 `a1e` BSET, `3dce`의 두 LONG 쓰기, `c58`과 같은 값이다. `100017`=0은 그대로 둔다.
  - IRQ는 `16bd0` 등 실제 대기에서만 들어간다. D1 기준선과 가장 가깝다(frame 1까지 같다).
- 선택 P1(**자연 초기화 대응 권고**): 원본 `3dce`·`c42`를 seed RAM에서 native로 실행하고 `a1e` BSET을 선언 쓰기로 둔다. RNG prep(`49a1a`)과 같은 방식이다.
  - 결과는 P2 + `100016`=0, `100017`=2, `10001a`=`100019`=`10001b`=0, `104d91` bit4 clear다.
  - head가 `ef2`에서 frame당 2회 대기하고, A에서는 IRQ 2회가 된다.
- 권고: 관측·인수 기준선은 P1(원본 초기화 경로와 같은 값)으로 하고, P2를 D1 회귀 연결 변종으로 함께 둔다. 어느 쪽이든 prep을 `declared` 목록에 남기고 seed 파일은 바꾸지 않는다.

### E6. palette RAM `400000..7fffff`

- 선택 a: port 기록으로만 둔다. MOVEM.L 1회 = LONG 8건이고, 원본 bus 순서는 MOVEM이 정한다.
  - IRQ 1회의 palette 쓰기가 dirty block 수 × 8 LONG(특수 채우기는 2,048 LONG)이다. [F] 탐침 P2 평균은 IRQ당 16.5 LONG이다.
  - 읽기(`42bcf4`)는 표현할 수 없다. 자연 완주가 막힌다.
- 선택 b(**권고**): device 기억으로 둔다. `AnimationMachineDevice`에 palette RAM 2 bank × 8 KiB와 선택 bank를 더한다(공개 header additive 변경).
  - `3a000f` 쓰기는 bank 0을, `3a001f` 쓰기는 bank 1을 선택한다(`palette-fill.md` 해석, MAME `set_palette_bank`).
  - `400000..7fffff`는 선택 bank의 `& 1fff` mirror다(MAME `map(0x400000, 0x401fff).mirror(0x3fe000)`). 읽기·쓰기 모두 이 mirror를 쓴다.
  - palette 쓰기는 port 목록에 넣지 않는다. 비교는 bank 내용과 선택 bank로 한다. `3a00xx` 쓰기는 port로 남긴다.
  - [U] 하드웨어의 palette RAM 쓰기 폭·대기 시간은 모델하지 않는다.
- 선택 c: b + palette 쓰기 개수만 port 요약으로 남긴다(진단용).

### E7. IRQ 안의 장치 읽기

- [F] IRQ 1회(비재진입·게임 mode)마다 읽기가 2건 있다.
  - `3cb2 MOVE.B 320000`: Z80 응답이다. MAME MVS map에서 `320000`은 `AUDIO_COIN`이다.
  - `288 MOVE.W 3c0006`: video 상태 bit3 → BYTE `100002`이다.
  - 순서는 `320000` 먼저, `3c0006` 다음이다.
- 선택 a: 기존 단일 queue에 넣는다(`external_queue_device`에 `320000`/1 추가). 호출자가 H·N·IRQ 읽기를 실행 순서대로 공급한다.
- 선택 b(**권고**): driver가 IRQ마다 `AnimationFrameOptions.irq_z80_reply`(기본 0)와 `irq_video_status`(기본 0)로 두 항목을 queue 앞에 넣는다.
  - IRQ가 끝나면 남은 IRQ 항목을 제거하고, 소비 수를 IRQ 기록에 남긴다. 재진입 경로는 두 읽기가 모두 없다.
  - `320000`/1은 a처럼 queue 장치에 추가한다(공개 의미 변경: 그동안 `unsupported program bus device address`였던 BYTE `320000` 읽기가 queue를 쓴다).
  - fixture는 값 표(응답 0, 1, 3, `7f`, `ff`; 상태 bit3 0/1)로 분기를 덮는다.
- [U] 실제 Z80 응답 값의 시간 변화. [F] 탐침은 응답 0을 썼고, `320000` 쓰기는 2,386 IRQ 중 266회(P2)였다.

### E8. 기존 host-level API와의 관계

- **권고:** F6 실행부는 block 실행부(원본 PC·block 단위·Waiting·checked 오류)로 새로 구현한다. 기존 API는 같은 입력에서의 차등 oracle로 쓴다. 관계는 다음과 같다.

  | 원본 범위 | 기존 API | F6 단위 | 재사용 방식 |
  | --- | --- | --- | --- |
  | `20c..23a`, `248..29a` | `begin_irq_envelope`/`finish_irq_envelope` | F6a | 스택 frame·MMIO 순서 교차 비교(`finish`는 RTE 직전까지) |
  | `29c..2d6`, `3dcc` | `begin_raster_irq`/`finish_raster_irq`, `return_default_irq_callback` | F6a | 같음 |
  | `c42`, `3dce` | `initialize_interrupt_state`/`initialize_irq_callbacks` | E5 prep | P1 prep 결과 교차 확인 |
  | `c8c..d54` | `begin_interrupt_service`/`continue_interrupt_service` | F6a(+F6b, F6c) | 완료 phase의 RAM·port(palette 제외) 비교. 지원 밖(특수 sprite 등)은 비교 제외 |
  | `ce2..d28`, `d2a` | `restore_interrupt_task`/`resume_interrupt_tasks` | F6a | fixture의 task 경계 비교 |
  | `bbe`(`a74` `a2c` `a4e`) | `process_credit_request` | F6a | RAM·D0 비교 |
  | `1adf8`/`187d8` | `refresh_scene_columns`/`refresh_column_controls` | F6a | RAM 비교(port는 F6a가 추가) |
  | `3cac`(`48156`) | `step_sound`/`resume_sound` | F6a | RAM·port 비교 |
  | `16cfa` | `refresh_sprite_queue`(일반 사각형) | F6a+F6c | 지원 입력에서 RAM·VRAM port 비교 |
  | `72fa`, `7320..871a`, `873a` | `transfer_palette_banks`, `upload_dirty_palette_blocks` | F6b | E6 b의 bank 내용 비교 |

- 직접 호출하지 않는 이유 [F]: 이 API들은 CCR을 계약에서 빼고, task 본문·sound 대기를 별도 phase로 끊는다. 또 지원 밖 입력(특수 counter, 비정렬 sprite X 등)을 거부하고, 하위 함수의 임시 스택 쓰기를 생략한다. block 실행부는 같은 RAM 전체·스택 바이트를 원본과 맞춰야 한다.

### E9. task 큐(`ce2..d28`)

- [F] `c64`(등록)의 직접 호출은 고정 ROM에 없다(`interrupt-task.md`). seed는 LONG `10081c`=0이다. 이 값에서 `ce2`는 `CMPA.L #10081c` 결과가 C=1이라 A6=0 task 복구를 한다(prep 없이는 깨진다).
- **권고:** `cf0`(task 복구 block)은 실행하되, `d28 RTS`가 task 본문 PC로 가면 그 PC의 routing에 맡긴다. task 본문을 따로 구현하지 않는다.
  - 자연 prep(P1/P2)에서는 큐가 비어(`10081c`) `cf0`에 닿지 않는다. [F] 탐침 0회였다.
  - fixture에서 queue frame의 PC를 routing된 PC(예: `3dcc` RTS → `d2a`)로 두어 `cf0`·`d2a`·`ce6` 연쇄를 시험한다.
- 대안: `cf0` 진입을 `unsupported animation irq task` checked 오류로 막는다. 더 보수적이지만 `d2a`·`ce6`이 시험되지 않는다.

### E10. frame driver 통합

- **권고:** `AnimationFrameOptions`에 다음 필드를 더한다(공개 header additive).
  - `irq_execution`(기본 false = 현재 선언 해제)
  - `irq_vblank_tick`(E1 B, 기본 false)
  - `irq_z80_reply`, `irq_video_status`(E7)
- `irq_execution`이 참이면 `release_wait`가 IRQ 효과 대기 5종에서 선언 쓰기 대신 `deliver_irq`를 실행한다. 순서는 다음과 같다.
  1. 예외 frame push(E2)
  2. 구간 1 실행: stop `c0044a`
  3. BIOS resume(E4)
  4. 구간 2 실행: stop = 대기 PC
  5. 무결성 검사(E3)
  6. 같은 대기 block을 다시 실행
- 카드 BIOS는 그대로다. IRQ 안에서 나온 Waiting은 checked 오류 `animation irq internal wait`다. 예: sound ring이 가득 찬 `3aea` — 생산자 `48156`과 소비자 `3cac`가 같은 IRQ 안에 있어 실제 하드웨어에서도 풀리지 않는다.
- 결과 기록: `AnimationFrameResult`에 `std::vector<AnimationFrameIrq> irqs`를 더한다. 필드는 segment, 대기 PC, 전달 순번, ports 범위, 외부 읽기 수, BIOS resume 수, RTE의 SR이다. IRQ port는 `irq_ports`로 분리한다(H·N port와 섞지 않는다).
- `irq_execution`이 거짓일 때 동작·출력은 지금과 바이트 단위로 같아야 한다(기존 D1 인수 54,400 frame 회귀).

## 4. 단위 분할과 순서

| 단위 | routing 범위 | block | 자연 탐침 도달(P1∪P2∪P2V) | 의존 | 위험 |
| --- | --- | --- | --- | --- | --- |
| F6a | `20c..2d8` `3dcc..3dce` `a2c..b0c` `bbe..bee` `c8c..d56` `3cac..3d3a` `48156..48180` `1adf8..1ae56` `187d8..18be8` `16092..166bc` `16cfa..16ea4` | 193 + clear run 381 | 145/193, run 진입 0..70 | E1–E5, E7, E9 | RTE·BIOS resume, `SBCD`, 계산 점프 범위, MOVE.L VRAM port |
| F6b | `72fa..8b64` | 522 | 302/522(특수 채우기 `873a` `8b5c` `8b60` `8732` 미도달) | E6 | MOVEM 순서, 8 KiB 채우기, bank 선택 |
| F6c | `f226..11792` `13b46..16092` | 1,240 + Duff 256 | A 65/624, B 60/616 | H4·H8 template | `MULS`/`MULU`, 정방향·역방향 편집, 표 밖 착지 |
| F6-D | `animation_machine_frame.cpp`(driver 옵션) | 0 | — | F6a–F6c, E10 | 공개 header, 회귀 |

- 이미 routing된 범위와 겹치지 않는다([F] 모든 짝수 PC가 routing 밖이다). 이웃은 다음과 같다.
  - `3dcc` 앞은 H1 `3db2..3dcc`, 뒤는 cleanup `3dce`다.
  - `bbe..bee` 뒤는 transition `bee`다.
  - `187d8..18be8` 앞은 H1, 뒤는 U08 `18be8`이다.
  - `1adf8..1ae56` 뒤는 H1 `1ae56`이다.
  - `16092..166bc` 뒤는 H1 `166bc`다.
  - `16cfa..16ea4` 앞은 H1 `16cfa` 직전, 뒤는 sprite `16ea4`다.
  - `72fa..8b64` 앞은 stage_entry `72f0..72fa`다.
  - `f226..11792`는 H8 `ce62..f226`와 H4 `11792..` 사이다.
  - `13b46..16092`는 H4 뒤다.
- 순서 권고:
  1. F6a(fixture 전부, 자연은 `10001b` bit7=0 경로와 F6b·F6c 경계 stop)
  2. F6b
  3. F6c
  4. F6-D(driver 옵션 + native 인수)
- [I] F6a만으로는 자연 IRQ가 render 분기에서 `72fa`(F6b)나 writer 표(F6c)에 닿아 rollback된다. 자연 완주 인수는 F6-D에서 한다.
- 무효화 탐침: 기존 엔진 시험·Python 검증기가 이 범위의 PC를 "routing 밖" 탐침으로 쓰는지 각 단위 작업에서 검색하고, H1 결정 7 관례(work RAM PC `10fe00..10fefe`로 값만 교체, Python 검증기는 무효화 목록으로 보고)를 따른다. [U] 이번 분석에서는 검색하지 않았다.

## 5. native 도달성 탐침(scratch `probe_irq.py`)

[F] 방법:
- `tools/verify_animation_machine_frame_driver.py`의 `setup_native()`(선언 rebase, Linux seed `f74048bb…`)와 `FH.prepared`(RNG prep)를 in-process로 쓴다. 저장소 도구는 수정하지 않았다.
- seed RAM에 E5 prep을 적용하고, `FH.HeadRun`을 subclass해 `release_wait`를 IRQ 실행으로 바꿨다.
  - IRQ 실행: 예외 frame(SR `2000`, 대기 PC) push, SR `2100`, PC = ROM[`64`]
  - `c0044a` unmapped fetch → 선언 resume
  - `RTE` intr 256 → 선언 pop
  - Z80 응답 0, palette RAM `400000` 8 KiB 1 bank
- 대기 해제 기준: 대기 주소의 값이 바뀌었는지 본다.

| 설정 | IRQ 수(전달 지점) | 정상 복귀 | 400 frame 완주(자연 137) | 주된 정지 |
| --- | --- | --- | --- | --- |
| P2(A) | 2,386(`16bd0`) | 2,386 | 40 | `4722` 읽기 `42bcf4` 96(frame 21–33) |
| P1(A) | 15,248(`ef2` frame당 2) | 15,248 | 12 | 같은 정지 124 |
| P2 + tick(B) | 7,624(`ef2` tick) | 7,624 | 12 | 같은 정지 124 |

- 모든 설정에서 guard seed 5개는 `fetch-unmapped`, case 141은 `odd-pc`로 D1과 같은 곳에서 멈췄다.
- IRQ port 합계(P2): 다음 표와 같다.

  | port | 건수 |
  | --- | --- |
  | `3c0000` LONG | 149,554 |
  | palette LONG | 39,328 |
  | PVC `2ffff2`/`2ffff0` | 각 22,870 |
  | `300001` | 4,772 |
  | `3a000f` | 3,021 |
  | `3c000c`/`3c0004`/`3c0000` WORD | 각 2,386 |
  | `320000` | 266 |

  `3a0011`/`3a0001`은 0건이다(`10f001` bit4=0).
- 자연 IRQ가 도달한 leader는 다음과 같다(TB 범위 기준, 세 설정 합).
  - F6a: 145/193. 미도달은 `21e` `29c..2ce`(raster), credit `a2c..b0c` `bc8` `bd4` `bde`, `c96`(재진입), `caa`(포화), `cd0` `d42`(`10f001` bit4), `cf0` `d2a`(task), `3cc6` `3cde` `3cea` `3d26`(Z80 응답·중복), `48156` 이후(`10d68c`≠0)다.
  - F6b: 302/522(mirror 재탐침 포함 308). 미도달은 특수 채우기 `873a` `8b5c` `8b60`, `8732`(`107dec`≠0)와 dirty가 아닌 cell이다.
  - F6c: A 65/624, B 60/616. Duff 진입은 0/256이다.
  - clear run: 진입 381개 중 n=0..40 41개다.
- 결론 [I]:
  - IRQ 실행 자체는 seed에서 안정적이다.
  - 자연 완주는 E6 b(palette RAM mirror 읽기)가 있어야 한다. palette mirror를 넣은 재탐침에서는 P1·P2 모두 자연 136 seed가 400 frame을 완주했다(6절).
  - writer family의 자연 커버리지가 낮다. F6c는 H4/H8처럼 fixture 위주로 검증해야 한다.

## 6. palette mirror 재탐침

[F] E6 b를 Unicorn에서 근사했다. `400000..7fffff`를 8 KiB 한 기억의 512겹 mirror로 map했다. `3a000f`/`3a001f`의 bank 전환은 근사하지 않았다([I] 단일 bank 근사). 나머지 규약은 5절과 같다. 산출은 scratch `probe_P2_mir.json`, `probe_P1_mir.json`이다.

| 설정 | IRQ 수(전달 지점) | 정상 복귀 | 400 frame 완주(자연 137) | palette mirror 읽기(H) |
| --- | --- | --- | --- | --- |
| P2(A) + mirror | 8,100(`16bd0`) | 8,100 | 136 | 1,440 |
| P1(A) + mirror | 108,528(`ef2`, H 54,264 × 2) | 108,528 | 136 | 1,860 |

- 두 설정 모두 정지는 D1 기준선과 같다. 자연 136 seed가 400 frame을 완주했고, case 141은 frame 0 `odd-pc`, guard 5개는 `fetch-unmapped`다. 카드 resume도 130회로 D1과 같다.
- P2의 IRQ 수 분포는 D1 관측의 `16bd0` 선언 해제 분포와 정확히 같다(seed당 85회 61개, 81회 25개, 0회 37개(case 141 포함), 그 밖 소수; 합계 8,100). 매 대기가 IRQ 1회로 풀렸다.
- IRQ 실행의 내부 정지(BIOS INT1, task, 내부 대기, 레지스터 불일치)는 0건이다.
- 자연 도달 leader(다섯 탐침 합)는 다음과 같다.
  - F6a 145/193
  - F6b 308/522
  - F6c A 65/624, B 60/616, Duff 0
  - clear run 진입 n = 0..70(71개)
- [I] 결론:
  - E1 A + E5(P1 또는 P2) + E6 b가 갖춰지면 F6-D native 인수는 D1과 같은 seed·frame 범위(54,400 frame)에서 실행할 수 있다.
  - P1은 frame당 IRQ 2회이고, palette 전송·sprite flush·sound 서비스가 매 frame 실제로 돈다.

## 7. 미확인

1. 실제 vblank 시간축(N pass 중간 IRQ), `100017`의 게임 중 값, frame당 IRQ 수.
2. BIOS `c0044a`/`c00438`의 실제 효과(BIOS ROM 없음).
3. Z80 응답 `320000`의 시간 변화, video 상태 `3c0006` bit3의 실제 값.
4. palette slot 12(ID `ffff`, 참조 `ffff`, flag bit7)가 실제 게임에서 생기는지(seed 산출 경로의 부산물인지).
5. writer family A/B의 정확한 template 증명(F6c 단위에서 한다), Duff `D7.B` 범위(H4·H8과 같은 `SUBQ.B #1; ANDI.B #1f; ADD.B` 패턴을 routine 4에서 확인; 나머지 routine은 단위에서 확인).
6. clear run(`16092`/`166a0`)의 `D1` 범위(열 수 차이, 부호 있는 WORD). 범위 밖 착지는 live 대상으로 둔다(F6a 결정 3).

## 메인 결정 (Claude Opus 5.5, 2026-10-15)

- E1 채택(선택 A): IRQ 효과를 내는 선언 해제 다섯 가지(`ef2`, `16bd0`, `cda4`, `3aea`, gate `47af0`/`478de`) 대신, 그 대기 block에서 실제 IRQ 한 번을 실행하고 대기 block을 다시 실행한다. 구간당 최대 16회. IRQ 전달 지점이 대기 block이라는 것은 선언이며 실제 vblank 시점은 [U]다.
- E2·E3 채택. native 쪽에서도 RTE를 선언 단계로 모사한다(Unicorn 2.1.4에서 RTE 실행 불가 [F]).
- E4 채택: `c0044a`는 선언 resume(PC:=`248`, A7+=4), `c00438`은 종단 경계.
- E5 채택: P1(원본 `3dce`/`c42` native 실행 + `10fd80`.7 BSET)을 인수 기준으로, P2를 D1 회귀 연결로 쓴다.
- E6 수정 채택: 팔레트 RAM은 device 메모리로 모델링한다(2 × 8KiB bank, `3a000f`/`3a001f`로 선택, `400000..7fffff` 미러). 다만 공개 헤더 `engine/include/ms5/animation_machine.h`는 감사 도구가 SHA로 pin하므로 바꾸지 않는다.
  - 새 헤더 `engine/include/ms5/animation_machine_irq.h`에 `AnimationMachinePaletteRam`과 확장 진입점(`run_animation_machine_with_palette` 등)을 둔다.
  - 기존 `run_animation_machine`은 팔레트 RAM이 없는 것으로 동작하며, 지금과 같다(팔레트 접근은 기존 checked error).
- E7·E8·E9·E10 채택. `irq_execution`이 꺼져 있으면 D1과 바이트 단위로 같아야 한다.
- 단위 배정: 이번 10개 묶음의 7번 = F6a, 8번 = F6b + F6c + F6-D(구동기 통합과 native 인수). F6c는 H4/H8 계열과 같이 parametric 실행부로 구현해도 되며, 모든 진입 PC가 routing돼야 한다.

## F6-D 결과 (구현 작업자 Claude Opus 5.5, 2026-10-15)

구현:
- [F] `AnimationFrameOptions`에 `irq_execution`(기본 false), `irq_z80_reply`, `irq_video_status`를 더했다. `AnimationFrameResult`에 `irqs`(`AnimationFrameIrq`: segment, 대기 PC, 순번, `irq_ports` 범위, 외부 읽기 수, BIOS resume 수, RTE가 꺼낸 SR)와 `irq_ports`를 더했다(`engine/include/ms5/animation_machine_frame.h`).
- [F] palette RAM은 `run_animation_machine_pass`/`step_animation_machine_frame`의 새 overload(`AnimationMachinePaletteRam&` 인자)로 붙인다. 기존 함수와 호출자는 바뀌지 않았다. palette는 transaction의 일부다(성공 시 commit, 실패 시 보존).
- [F] `irq_execution`이 참이면 대기 6 PC(`ef2` `16bd0` `cda4` `3aea` `47af0` `478de`)에서 E1–E4·E7대로 IRQ 1회를 전달하고 대기 block을 다시 실행한다. 구간당 16회 상한은 선언 해제와 공유한다. checked 오류는 `animation irq wait not released`, `... bios int1 boundary`, `... internal wait`, `... bios return mismatch`, `... register restore mismatch`, `... external read overrun`, `... vector unavailable`, `... stack invalid`이다. IRQ 안의 실행부 오류는 그대로 반환한다. 카드 BIOS resume은 그대로다.
- [F] 내부 `run_animation_frame_segment`에 palette·IRQ 출력 overload를 더했다. 기존 signature는 wrapper로 남겼다(IRQ 기록은 버린다).

검증:
- [F] native 인수 `tools/verify_animation_machine_frame_irq.py`(harness `engine/tools/frame_irq_acceptance.cpp`)를 142 seed × 400 frame으로 실행했다. 조건은 P1 prep(원본 `3dce`·`c42` native 실행 + `10fd80`.7), Z80 응답 0, video 상태 0, 2 bank palette mirror다.
  - 자연 137 seed 중 136이 400 frame을 완주했다. complete frame 54,400/54,400이 일치했다(step과 N 단독 pass 둘 다).
  - 비완주 6건(guard 5 `fetch-unmapped`, case 141 frame 0 `odd-pc`)은 D1과 같은 checked 오류로 상태를 보존했다.
  - IRQ는 108,528회 전달됐다. 모두 `ef2`(frame당 2회)였고 정상 복귀했다. BIOS resume도 108,528회였다. 탐침 6절 P1 수와 같다. palette bank 전환(`3a001f`)은 0회였다.
  - 일치한 frame에서 비교한 IRQ port는 2,130,063건이다. H palette mirror 읽기가 있는 seed는 124개다. 카드 resume seed는 130개다.
  - C++ 단독 chain은 54,400 frame이 일치했고 기대 실패는 1건, 발산은 0이었다. 첫 4 자연 seed에서 결정성을 확인했다.
  - 기준 일치와 negative 검사 18종을 모두 검출했다(IRQ 끔, Z80·video 값, palette 미부착, `10fd80`.7=0 → int1 오류, queue, 결과 변조 등). 비영 값(`--z80 0x37 --video 8`, 1 seed 4 frame)도 일치했다.
- [F] `irq_execution`=false의 D1 회귀(`tools/verify_animation_machine_frame_driver.py` 전체, workers 3): 54,400/54,400 frame 일치, 비완주 6건 checked 보존, chain 54,400, 결정성·negative 통과, historic 비교 전부 같음.
- [F] `engine/tests/animation_machine_frame_test.cpp`는 ROM 없이 IRQ 행을 더했다(85 checks). 내용은 다음과 같다.
  - `ef2` 2회 IRQ를 수동 harness 연쇄와 비교했다.
  - Z80 응답 → `104d7c`, video bit3 → `100002`를 확인했다.
  - 끔 모드에서 palette overload와 기존 함수가 같은 결과를 냈다.
  - checked 오류와 상태 보존을 확인했다. 대상은 int1, vector 없음, 16회 초과, 미routing raster callback, 잘못된 palette, `10001b`.7=0의 `cda4`다.

한계·미확인:
- [I] 자연 P1에서는 `ef2`만 IRQ 전달 지점이었다. `16bd0`·`cda4`·`3aea`·gate의 IRQ 전달은 단위 시험(`cda4` 미해제)으로만 확인했고 자연 native 비교는 없다.
- [U] 실제 vblank 시점, BIOS `c0044a` 효과, Z80 응답·video 상태의 실제 값은 미확인이다(7절과 같다).
