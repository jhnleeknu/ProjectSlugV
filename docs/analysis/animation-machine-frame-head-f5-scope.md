# F5 frame head `e4a`/`e74`·controller `c52a`/`c66a` 구현 범위 분석(구현 전 계획)


메인 결정(Claude Opus 5.5, 2026-10-13):
- D1 채택: frame = H(e74 실행, LONG `(1008e4)` stop) → 선언 controller 생략(PC:=2ac2, A7+=4) → N(기존 F2 pass). 기존 F1~F4 검증은 N 구간으로 유효하다.
- D2 채택(`ef2` vblank Waiting, `100016:=100017` 선언 해제; IRQ `c8c`는 F6). D3/D4 채택(raster·입력은 선언 external-read queue, 기본 raster 0·입력 ff, 빈 queue는 checked 오류). D5 채택(`16bd0` sprite-flush Waiting, `108d34:=108d36` 선언 해제). D6/D7/D8/D10 채택.
- D9: F5a에서는 controller를 계속 선언 생략한다. C1/C2의 선언 상태(demo `c66a`+`104cd4`=1 대 game `c7fc`+`10fdaf`=2)는 H 단위가 끝난 뒤 별도로 정한다.
- 반복 family(5728 palette cell, sprite writer 16종, Duff 진입)는 PC를 매개변수로 받는 executor 하나로 구현해도 된다. 단위 상한은 고유 코드 기준으로 세되, 시험은 모든 진입 PC를 덮어야 한다.
- 주소 정정: IRQ 신호 필드는 `100016`/`100017`/`10000e`다(frontier·F2 문서의 `108016`/`108017`/`10800e`는 오기).
- 순서: native 관측 도구(D1 protocol) → H1 → H2 → H3 → H4~H7 → (C 결정) → H8~H11·C3.
**상태: 읽기 전용 분석 작업자 초안. 구현·검증 기록이 아니며 메인 결정 전이다.**

Claude Opus 5.5 / high 읽기 전용 분석 작업자가 작성했다. 기준:
- canonical BE ROM `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. fixed 영역은 CPU 주소=file offset이다. 작업 전후 SHA·mtime이 같았다.
- 작업 트리 `metalslug-f4`, HEAD `10b3c2d`(F4 N21까지).
  - routing 원천 `engine/src/animation_machine.cpp`(SHA256 `36cb03c8e257208e0685cdb93a071867920bba256320f2dc2e1612c8ee506da0`, 규칙 78개)를 파싱했다.
- native 입력 `artifacts/animation_machine_scheduler_rng_native/observation.json`(SHA256 `413052978cbf85fa1eedbaaa0ca93bc20b9996c131bba032a6e8db22bc27d6d7`)과 seed 기록·blob을 읽기 전용으로 썼다.
  - 관측 도구 SHA: `observe_animation_machine_scheduler.py` `62bb23ff…`, `_scheduler_rng.py` `659f8636…`, `_pvc_banks.py` `86ebf962…`. 이 도구들은 in-process import만 하고 수정하지 않았다.

표기: [F]=원본 바이트, 기록 산출물 또는 작업자 scratch Unicorn 탐침에서 확인한 사실. [I]=추론. [U]=미확인.
- 탐침은 선언 모델을 Unicorn에서 돌린 것이다. BIOS 실행, 자연 IRQ, 자연 scheduler를 주장하지 않는다.
- block 시작 수는 기존 F4 rescope와 같은 capstone 정적 leader 규칙으로 셌다(분기 대상, 조건 분기 fall-through, flag 공유 Bcc 묶음, JSR 복귀점, BRA.W 표 항목, `MOVE.L #imm,(A6)` 설치점). 함수 걷기는 이미 routing된 PC에서 멈춘다.
- scratch는 `/Users/start/Workspce/ms5-scratch/f5scope/`(`f5route.py` `f5sdec.py` `f5clos.py` `f5full.py` `f5groups.py` `f5probe.py` `f5expA*.py` `f5expC.py` `f5expD.py` `f5expE.py` `f5irq.py` `f5deleted.py` `f5fields.py`)이며 저장소 밖이다.

## 요약

- [F] **정적 closure가 frontier 추정보다 크다.** frontier 문서의 "`e74` ~850 block"은 sprite writer 간접 표를 빼고 센 값이다.
  - frame head(`e4a`부터): 함수 58개, block 시작 2,038개, 명령 11,356개다. 여기에 sprite writer의 계산 점프(Duff 진입) 256개를 더하면 2,294개다.
  - 이 가운데 반복 구조가 1,984개다. 하나는 `5728` palette 표시 루프(26바이트 동일 cell 256개 × block 2 = 512)다. 다른 하나는 sprite writer 16개(정방향 8, 역방향 8, 각 ~75 block, 표 항목 16 포함 1,216)와 Duff 진입 256이다.
  - 반복이 아닌 고유 block은 310개다.
- [F] controller(`c52a` `c560` `c56e` `c66a`와 그 callback 상태 19개): 함수 49개, block 시작 298개, 명령 672개다. `c66a` 이후 매 frame 경로만 보면 257개다.
- [F] **현재 native 관측은 frame head·controller를 실행하지 않는다.**
  - 관측기는 `e4a`/`e74` 첫 명령에서 멈춘다(`HEAD_STOPS`).
  - 다음 pass를 PC `2ac2`, A6 `1008e4`, A7 `1ff000`으로 다시 시작한다. 모든 pass 기록이 `ctrl_skipped=True`다.
  - 자연 seed의 seed-start·pass-end dump 5,155개 전부에서 `100820`=`e4a`, `1008e4`=`c52a`다.
  - 따라서 "130/137 seed 일치"는 선언 모델과의 일치이고 full-frame 일치가 아니다.
- [F] **skip이 숨기는 것(정량).**
  - frame head 한 번(자연 pass-end 상태 5,017개에서 native 실행): RAM 쓰기 1,000~4,209바이트다.
  - port는 14~6,372건이고 표본 436개 평균은 286건이다. `3c0000` LONG, watchdog `300001`, PVC `2ffff0/2`, `3c0004`가 여기에 든다.
  - device 읽기는 7회다(`3c0006`×2, `300000`×2, `340000`×2, `380000`×1).
  - 이 값들이 다음 pass의 routing된 code로 들어간다. frame counter `10000e`, BIOS mode 사본 `100012`, 입력 `104caa..104cb1`, sound 큐 cursor, palette slot 표, sprite 큐, 배경 좌표 snapshot, frame parity `10d494` 등이다.
  - head를 매 frame 넣은 연쇄 실험(full dump seed 7개 × 400 frame)을 했다. node 순서는 7개 모두 같았다.
  - 그러나 head가 쓰지 않은 RAM도 frame 1부터 갈라졌다. 1~2,287바이트다.
- [F] **controller를 seed 상태에서 실행하면 첫 frame에 게임이 해체된다.** seed RAM은 `104cd4`(입력 mode)=0, `100012`=0, `10fdae`=`10fdaf`=0, `1008e4`=`c52a`다.
  - `1008e4`=`c66a`를 선언하고 실행하면 표본 272개 전부 `c686`→`c69a` 해체 경로로 간다(`c4cc` 전체 node 제거, `caf0` 화면 초기화, 자식 `e66aa`).
  - `c52a`부터 실행하면 `107dea` palette 대기를 지난 뒤 `10fdae`=0이라 BIOS `c00444`로 간다.
- [F] **자연 137 seed 중 136개에서 stage controller node `100b30`이 idle(`270e`)이 된다.** frame 1에 8개, 221·241·245 frame에 128개다.
  - full-frame 모델이라면 이 시점에 controller가 stage를 떠나는 전환을 한다(`c686`/`c76a`).
  - 지금의 400 frame 기록 중 약 23,268 pass(43%)는 controller skip 때문에만 이어지는 연속이다.
- [F] **주소 정정.** frame head의 IRQ 신호는 A5 상대 `-7fea(a5)`이다. 따라서 `100016`/`100017`이 맞다.
  - frontier·F2 계약 문서의 "`108016`/`108017`/`108018`/`10801a`/`10801b`, WORD `10800e`"는 각각 `100016`/`100017`/`100018`/`10001a`/`10001b`, `10000e`의 오기다. `main-frame.md`와 `interrupt-frame-flow.md`는 `100016`으로 맞게 적었다.

| 항목 | frame head | controller |
| --- | --- | --- |
| 정적 함수 / block 시작 / 명령 | 58 / 2,038(+Duff 256) / 11,356 | 49 / 298 / 672 |
| 반복 family | `5728` cell 256×2, sprite writer 16×~75, Duff 8×32 | 없음 |
| 이미 routing된 callee | 15(`3650` `386e` `3918` `3a70` `3ac8` `3d7e` `8bbc` `8c16` `9056` `a29c` `a2b8` `a370` `ca9e` `ce02` `e7bf4`) | 22(`289e` `28ae` `2a0a` `2a28` `2a84` `35f0` `3650` `386e` `3918` `3dce` `47594` `8bbc` `9056` `9060` `bb74` `bbb8` `ca48` `ca76` `ca7e` `caf0` `e7bf4` `e8a1c`) |
| 간접 제어 | `f42 JSR (A0)`(aux callback `100896`), `931a JSR (A0)`(menu callback `107df6`), `16c48`/`16cc8 JSR (A3,D7.W)`(sprite 표 `ce62`/`11792`, 각 8항목), BRA.W 표 16개(각 32항목), Duff `JMP d(PC,D3.W)` 8개 | `36b0`/`36fa JSR (A1)`(숫자 표시 helper `36ba`/`3706`, `4a88e`/`4a8ce` 경유) |
| TRAP | `fee TRAP #15`(head `+7e` ≠ WORD `10000e`) | 없음 |
| BIOS | 없음 | `JMP c00444` 5곳(`c598` `c5a6` `c6c8` `c7c0` `c982`), `JSR c00468`(`c310`, 카드), `JSR c00450`(`4a98c`, `10fd82`≠0일 때만) |
| I/O | 쓰기 `3c0004` `3c0000`, watchdog `300001`, PVC `2ffff0/2`. 읽기 raster `3c0006`, 입력 `300000` `340000` `380000`. 배너 window `200004`/`200008` | `d00034`(backup RAM 읽기, `4a954`), `3c0000`(표시 helper) |
| 특수 연산 | `MULS.W` 8곳(sprite writer), `SUBX.W` 2곳(`187ac` `187b0`, X는 같은 block의 `LSR`) | `SBCD.B`(`ca0e`, X는 같은 block의 `SUBQ`), `MULU.W`(`49a44`). DIV 없음 |

## 1. 정적 closure(현재 routing 기준)

### 1.1 frame head `e4a`/`e74`

[F] 원본 흐름:
1. `e4a`(첫 frame만): `JSR e7bf4`. WORD `10000e`=0, `+7e`=0, `+84`=1, `+76`=0으로 둔다. `JSR 903a`.
2. `e6e`: callback LONG을 `e74`로 설치하고 `e74`로 fall-through한다.
3. `e74`: `3c0004`=0, `3c0000`=`82000000`, `3c08` sound word 큐 flush, `16bba` sprite flush를 차례로 한다.
4. `1ae56` 배경 좌표 snapshot을 실행한다.
5. BYTE `10001b` bit7 clear, `5728` palette frame, bit7 set 순서로 실행한다.
6. `eaa` raster 읽기: `(3c0006>>7)−256`을 계산하고 음수이면 0으로 둔다. 그 값에서 `100018`을 빼서 저장한다.
7. `ec4`: `10f000` bit0과 `+84`가 모두 참이면 debug 출력 `3a70`.
8. `ef2` **IRQ 대기**: BYTE `100016` < BYTE `100017`이면 spin한다.
9. `efc` raster 두 번째 읽기.
10. `f12`: 신호를 `10001a`로 옮기고 `100016`=0, WORD `104ca2`=0으로 둔다. `31d6` 입력, `b68` BIOS mode·player mod를 실행한다.
11. `f30`: aux callback `+76`이 0이 아니면 `f3c` 경로로 간다. `JSR (A0)` 뒤 `5728`, `f4c` 신호 대기, `BRA f12` 순서로 head 안에서 반복한다.
12. `f54`: `JSR 9136`(pause/menu 요청). 결과에 따라 다음 중 하나로 간다.
    - `+84`=1→0 전환이면 `8bbc`/`8bc8`/`8c16`/`5728` 뒤 `BRA ec4`다. **dispatcher로 돌아가지 않는 head 내부 루프**이며 [I] pause다.
    - 그렇지 않으면 `fe2`로 간다. `+7e` ≠ `10000e`이면 TRAP이고, 같으면 +1, `43dbc` parity 순서로 `1000 RTS`한다.

[F] 묶음별 정적 block 시작. 묶음 합은 2,038이며 중복이 없다. 자연 열은 아래 2절 탐침(자연 pass-end 상태 5,017개)에서 실행된 leader 수다.

| 묶음 | 범위 | block | 명령 | 자연 실행 |
| --- | --- | --- | --- | --- |
| head 본문 | `e4a..1000` | 44 | 99 | 23 |
| BIOS mode·player mod | `b68..bb4` | 7 | 18 | 6 |
| 입력 sampler | `31d6..349a` `349c..3528` `352a..35a0` | 70 | 246 | 14 |
| sound word flush | `3c08..3c40` | 8 | 19 | 8 |
| palette frame | `5728..72ee`. 색 helper `4718` `479e` `4c40` `504c`(`4718..5726`, 직선 unrolled) | 551 | 3,191 | 318 |
| sprite flush core | `16bba..16cf8`, 정렬 `166bc..16bb8` | 33 | 675 | 23 |
| sprite writer | 표 `ce62..ce82`, 정방향 `ce82..f224` 8개. 표 `11792..117b2`, 역방향 `117b2..13b44` 8개 | 1,216 | 6,864 | 149(정방향 0) |
| 배경 snapshot | `1ae56..1aeb2` `1879c..187d6` | 10 | 32 | 10 |
| pause/menu 요청 | `9136..932e` `9086..9134` `313c` `3902..3916` | 81 | 167 | 5 |
| 기타 | `903a` `9546` `8bc8` `8bd4` `8be0` `3db2` `43dbc` | 18 | 45 | 7 |
| **계** |  | **2,038** | 11,356 | 563 |

- [F] Duff 진입: `e1ba` `e6ce` `ebea` `f10a` `12ae2` `12ff4` `1350e` `13a2c`에 `JMP d(PC,D3.W)`가 있다. 여기서 D3 = D7.B×4이고, D7.B는 앞의 `ANDI.B #1f` 뒤 `ADD.B D7,D7`로 0..62 사이 짝수다.
  - 각 진입점은 `MOVE.L D4,(A6)`/`ADD.L D2,D4`/`MOVE.L D0,(A6)`/`ADD.L D2,D0` 반복 run 안에 있다. 진입점은 8바이트 간격이고 run 끝까지 32개다. 총 256개다.
  - 이 진입점은 위 정적 leader에 하나도 없다(자연에서 4개만 진입). 기존 block 시작 규약대로라면 256개의 추가 block 시작이다.
- [F] `5728`의 `578c..718c`는 26바이트 cell 256개다(`MOVE.B D0,300001`; `BTST #1,f(A2)`; `BNE`; `BSET #7,f(A2)`; `LEA 10(A2),A2`). cell마다 leader가 2개(`+10`, `+16`)다. palette slot 표 `104d92+16k`의 dirty bit를 세우면서 watchdog을 cell마다 친다.
- [F] sprite writer 16개는 `sprite-flips.md`의 "정방향/역방향 준비" 4종과 갱신 4종(BRA 표 `ce62+4k`/`11792+4k`, k=0..7)이다. 각 routine은 32항목 BRA.W 표 하나를 가지고, k=4..7 routine은 Duff 진입 하나를 더 가진다.
  - VRAM 쓰기는 `A6=3c0000`에 대한 `MOVE.L Dn,(A6)`(주소 word + 자료 word)다.
  - 방향은 BYTE `108d3c` bit7이 고른다(bpl→`11792` 역방향). 이 bit를 바꾸는 것은 IRQ 쪽 `16cfa`의 `BCHG`뿐이다. 그래서 IRQ를 실행하지 않는 선언 모델에서는 정방향 8개가 자연 실행되지 않는다([F] 자연 0/608).
- [F] 간접 callback 2개는 사실상 쓰이지 않는다.
  - `+76`(`100896`)은 `e4a`가 0으로 쓰고, 그 밖의 정적 writer는 `e40 MOVE.L A0,100896`뿐이다. 그런데 fixed ROM 전체에 `e40`으로 가는 JSR/JMP/BSR나 짝수 정렬 포인터가 없다.
  - menu callback LONG `107df6`의 writer는 `919a MOVE.L #0`뿐이다. [I] 둘 다 dead 또는 BIOS·디버그 전용이다.
- [F] 모두 새 code다. 이미 routing된 PC는 위 표의 callee 15개뿐이다(card menu 계열 `3650` `386e` `3918` `a29c` `a2b8` `a370` `ca9e`는 `9136` pause menu 경로).

### 1.2 controller `c52a`·`c66a`

[F] callback 상태(설치점): `c52a`→`c560`(palette 대기 WORD `107dea`)→`c56e` 순서로 boot가 진행된다. 이후는 BIOS 요청 `10fdae`에 따라 갈린다.
- 0 또는 1: BIOS `c00444`.
- 3: `c6da` title(자식 `de376`, `c6f4` 대기).
- 2(그 밖): demo로 간다. `c5ce`(자식 `4fb64`)→`c5f4`(자식 `de024`)→`c608`(150 frame) 다음 `c610`이 `49a1a` RNG, `c4cc`, `caf0`, `47570`, `4823a`, `3162` replay 선택을 실행하고 `c654`로 간다.
- `c654`가 `100b30`에 `477e4`를 설치하고 `c66a`로 넘어간다.

[F] `c66a`(매 frame): `289e`(`100b30` callback≠`270e`)와 `314c`(BYTE `104cd4`==1, 입력 replay mode)가 모두 참이면 `c724`로 간다. 그렇지 않으면 `c686`→`c69a` 해체(`c4cc` `caf0` `ca76`, 자식 `e66aa`, `c6c0`)로 가고 끝에 BIOS `c00444`에 이른다.
- [I] 따라서 `c66a`는 attract demo의 감시자다(`input-sampler.md`: `104cd4` 0=실시간, 1=replay, 2=replay 끝).
- [F] 게임 mode(BYTE `100012`==2, `b68`이 BIOS `10fdaf`를 매 frame 복사)에서는 `c724`/`c73e`가 `c74c`로 간다. 여기서 `101c`(BYTE `100017`:=2), 자식 `b300` 등 게임 흐름 상태 `c79a` `c7fc` `c82e` `c874` `c89c` `c8aa` `c8e8` `c90c` `c940`이 이어진다.
  - [I] 게임 진행 중 매 frame 상태는 `c7fc`다(`289e`가 참이면 `c988`, 거짓이면 `c76a` 해체 뒤 재시작).
- 공통 꼬리 `c988..ca20`: `+80..+83` 계수기, BCD 타이머(`SBCD`), `30bc`/`4a88e`/`30d4`/`c4f8` 표시 helper가 있다.

| 영역 | 범위 | block |
| --- | --- | --- |
| boot·demo 도입 | `c52a..c654` | 32 |
| gate | `c654..c686` | 7 |
| 해체 | `c686..c6ce` | 9 |
| title | `c6ce..c724`(`c6ce..c6d9` 문자열 자료 `"\\p\\cTIME"` 포함, [F] `c6da`부터 code) | 7 |
| 게임 mode 분기 | `c724..c988` | 81 |
| 매 frame 꼬리 | `c988..ca22` | 21 |
| 지역 helper | `c49c..c52a` | 16 |
| 기타 지역 | `ca32` 1, `c2fa..c364`(카드 BIOS) 7 |  |
| 공유 helper | `100e` `101c` `30bc` `30d4` `314c` `3162` `36ba` `3706` `3902` `4718` `8b64` `8bb6` `bbd4` `4755e` `47570` `4823a` `49a1a` `4a88e` `4a8ce` `4a944` `4a974` `4a9ca` `4e1cc` `4fb1a` `e62ec` | 117 |
| **계** |  | **298** |

- [F] 자식 callback 7개(`4fb64` `b300` `c250` `de024` `de376` `de660` `e66aa`)는 이 closure에 넣지 않았다. 모두 미routing이며 F5 범위 밖의 새 node다.
- [F] frame head와 공유하는 leader는 7개(`3902` 6, `4718` 1)다.
- [F] F4 scope·rescope 단위 범위와 겹치는 PC는 없다(`49a1a`는 F4 결정 1의 seed 준비에서 native 실행만 했고 routing되지 않았다).

## 2. "선언 효과 없는 skip"이 숨기는 것

### 2.1 native 관측기는 head·controller를 실행하지 않는다

- [F] 기록 관측의 선언 모델은 `observe_animation_machine_scheduler.py`와 `_rng.py`다.
  - stop은 `e4a`/`e74` 첫 명령의 code hook이다. 다음 frame은 PC `2ac2`, A6 `1008e4`, A7 `1ff000`, SR `2000`으로 레지스터만 다시 쓴다.
  - `declared_model.skipped`=`['frame head e4a/e74 (everything)','controller c52a/c66a (everything)']`이고 pass 기록은 모두 `ctrl_skipped=True`다.
- [F] `seed_boot_state`에서 142 seed 모두 `100820`=`e4a`, `1008e4`=`c52a`, `10fdae`=0, `10f004`=0이다. 자연 seed의 seed-start·pass-end dump 5,155개에서도 다음 값이 변하지 않았다.
  - `100012` `10fdaf` `10fdae` `10fd82` `104cd4` `100016` `100017` `100018` `10001a` `10001b` WORD `10000e`, head `+7e` `+84` `+76`, `10f000`, `107dea` `107ded` `107df0` `107df1` `108d34` `108d36`이 모두 0이다.
  - [I] seed RAM은 boot·BIOS를 거치지 않은 host API 산출물이다.
- [F] 따라서 F4 `verify_animation_machine_scheduler_rng_f4`의 130/137 완주(작업 지시 기준)는 "head·controller를 뺀 node pass"의 일치다.

### 2.2 head 1회의 효과(실험 A, `f5expA*.py`)

[F] 자연 seed의 기록 pass-end 상태(PC `e4a`/`e74`, A6 `100820`, A7 SPd−4=`1feffc`) 5,017개에서 head를 native로 RTS(`2ac2`)까지 실행했다. 선언 입력은 `300000`/`340000`/`380000`=`ff`(누름 없음, active-low), raster `3c0006`=0이다.
- 결과: 전부 `2ac2`로 돌아왔다. IRQ 대기(`100017`=0이므로 spin 없음), sound 대기, aux·menu callback, TRAP은 0건이다.
- RAM 쓰기는 상태당 1,000~4,209바이트다.

| 쓰기 영역 | writer |
| --- | --- |
| `10000e` `100010` `100012` `100016` `100018` `10001a..1b` | `e4a`/`e74` 본문, `b68`, bank 선택 |
| head node `100820` `100896` `10089e` `1008a4`, WORD `104ca2` | 본문 |
| 입력 블록 `104ca8..104cc1`, `10f006..7` | `31d6`, `b68` |
| sound ring `104cf4..` `104d76`, word 큐 cursor `104d8a` | `3c08`→`3ac8` |
| palette slot 표 `104d92..105d92`(16바이트×256) | `5728` cell, routing된 `e7bf4` 계열 `8dxx` |
| palette buffer `105da2..107da2` | `4718` `479e` `4c40` `504c` |
| `107dc2..` `107dd4` `107ded..107df1` `107dfe..107e06` | `8bc8` `903a` `9546` `5728` |
| sprite 큐 `107f40..`, `108b34..108d31` `108d36..` `108d4c..10914b` `10914e..` | `166bc` `ce02`(u04) `16bba` writer |
| 배경 snapshot `1091d0` `10b250` `10d2d0` `10d350` | `1879c` |
| parity `10d494` | `43dbc` |
| stack `10efe4..10effb` |  |

- port(표본 436): `3c0000` LONG 79,294, `300001` BYTE 36,712, `2ffff0`/`2ffff2` 각 4,198, `3c0004` 436. 상태당 14~6,372건이다.
- device 읽기(표본 436): `3c0006`×872, `300000`×872, `340000`×872, `380000`×436이다. mode 0(`104cd4`=0)에서 frame당 입력 읽기는 5회다.
- [F] 정적 leader 2,038 중 자연 실행은 563개, Duff 진입은 256 중 4개다(묶음별 값은 1.1 표).

### 2.3 head 결과가 다음 pass로 흘러가는가(실험 C·D)

- [F] 실험 C(`f5expC.py`): full dump seed 7개(case 0 1 2 100 106 111 135)를 seed-start부터 400 frame 이어 실행했다.
  - (a) 선언 모델 재현: 매 frame RAM이 기록 pass-end blob과 바이트 단위로 같았다(7×400, 차이 0, node 순서 일치). 하네스가 기록 모델을 정확히 재현함을 보인다.
  - (b) head 포함: 각 frame 경계에서 head를 native로 실행하고 controller는 계속 skip했다.
  - (b)의 결과: node 순서(A6, callback)는 7 seed 400 frame 모두 기록과 같았다. head가 한 번이라도 쓴 바이트를 빼고도 RAM이 frame 1부터 달랐다. 최대 차이는 case 100·106·111이 1바이트(`100c46`, event node 필드), case 2가 24바이트, case 0·1·135가 2,287바이트(pool 객체 `1011f3..`, `108b41..`, `10d273..` 등)였다.
  - (b)에서 선언 sprite 소비 해제(`16bd0`)가 seed 0·1·2·135에서 85회 일어났다(아래 결정 D5).
- [F] 실험 D(`f5expD.py`): head가 마지막으로 쓴 바이트를 다음 pass의 routing된 code가 읽은 PC를 셌다.
  - case 0, 120 frame에서 424바이트를 읽었다.

| 소비 code(소유 실행부) | 읽은 head 산출 |
| --- | --- |
| `b481e`(frame_helpers) | WORD `10000e` frame counter |
| `49b3a` `49b3e` `49b48` `49b90` `49b94` `49b9e`(input) | 입력 `104caa..104cb1`, `100012` |
| `3b2a` `3b9c` `3bda` `3adc`(sound) | `100012`, `104d8a`, `104d76` |
| `8e96` `8e4a` `9010` `8dd6` `8dec` `8f14` `8fb4` `8cea` `8d24`(palette_bind·cleanup·u02·hud) | palette slot 표 `104d92..`, buffer `1050f8..` |
| `cdb6` `cdd4` `ce02` `ce0a`(sprite·u04) | sprite 큐 `108d38` `10914e` `109150` |
| `186b2` `18702` `18720` `185e8` `1701a`(scene_update·map_transfer·scene) | 배경 snapshot `1091d0` `10b250` `10d2d0` `10d350` |
| `43e7a`(cleanup) | parity `10d494` |
| `2abe`(dispatcher) | `100820`(`e4a`→`e74`) |

  - 미routing 소비자 `8e4c` `8e5c` `8c8a..8c92`도 있다.
  - case 2(120 frame)는 90바이트, case 100(60 frame)은 2바이트(`100820` `10d494`)였다.
- [I] 결론: head는 독립 장치가 아니라 입력·sound·palette·sprite·배경·시간축을 매 frame 갱신하는 producer다. 현재 선언 모델은 이 값들을 seed 값에 고정한다. node 순서가 같아도 객체 상태는 frame 1부터 다르다.

### 2.4 controller 효과(실험 E, 자연 seed 표본 272 상태 × 변형 3)

| 선언 | 경로 | 결과 |
| --- | --- | --- |
| `1008e4`:=`c66a`, 나머지 기록 그대로 | `c686`→`c69a`→`c6c0`→`c73e`→`c988`→`ca20` | 272/272 해체(전체 node 제거·`caf0`·자식 `e66aa`) |
| 위 + `104cd4`:=1 | stage 활성 128: `c724`→`c988`→`ca20`. 쓰기는 `100964` `100966` 등 controller 필드와 stack뿐이고 port는 `3c0000` 160건이다 | 정상 frame |
|  | stage 비활성 144: 해체 경로 |  |
| 위 + `100012`:=2 | `c724`→`c74c`(`101c`가 `100017`:=2) 또는 해체 | 게임 mode 분기 |

- [F] stage controller 비활성화 시점(`f5deleted.py`): 자연 137 seed 중 136개에서 `100b30`이 idle(`270e`)이 된다. 첫 frame 분포는 1(8 seed: 94 95 100 101 106 107 110 111), 221(4), 241(35), 245(89)다. case 141만 그렇지 않다(frame 0 홀수 PC 정지).
  - 이후 frame은 기록 400 frame 중 약 23,268 pass다. 그 사이 controller는 해체(demo) 또는 `c76a`/`c79a`(게임) 전환을 했어야 한다. [I] 이 구간은 선언 모델에서만 있는 연속이다.

### 2.5 IRQ 쪽(참고, F5 범위 밖)

- [F] vector `64`→`20c`(level 1), `68`→`29c`. `20c`는 `3c000c`=6(IRQ ack)을 쓴 뒤 `10fd80` bit7을 본다. 비게임 mode면 BIOS `c00438`로 가고, 게임 mode면 다음을 차례로 실행한 뒤 RTE한다.
  - `JSR (108006)`(raster callback)
  - `JSR c8c`
  - `JSR c0044a`(BIOS SYSTEM_IO, [I] 입력 갱신)
  - `3c0004` 쓰기, `3c0006` bit3 읽기
- [F] 정적 closure는 함수 15개, block 712개, BIOS 2개다. palette RAM `400000`, Z80 `320000`, system latch `3a00xx`를 쓴다.
- [F] `c8c` 탐침(272 상태, head 실행 뒤)에서 RAM 쓰기는 다음과 같았다.
  - `100016`(+1), `100019`
  - palette buffer 표시 word `105da2+20k`, `107ded`(pending bit 해제)
  - `108d34`(sprite 소비, `16exx`), `108d3c..` `108d44` `108d4c`, `1091d0` 등
  - port는 palette RAM 쓰기 28,448, `3c0000` LONG 23,024, PVC, watchdog, `3a000f`였다.
  - `ce2..d28`의 task 문맥 전환은 탐침 stack 구성 때문에 끝까지 가지 못했다([U]).

## 3. 장치·BIOS 경계 결정(MAIN DECISION NEEDED)

기존 관례를 따랐다: BIOS는 실행하지 않는다. JSR형 BIOS는 fade_card `c00468`처럼 선언 resume(PC=복귀, A7+=4, 응답 바이트 선언)으로, JMP형은 종단 경계로 둔다. IRQ 효과는 Waiting 해제 어휘(sound `104d74`:=`ffff`, sprite `108d34`:=D4, gate `107ded` bit7)로만 넣는다.

### D1. frame 경계와 pass 규약(가장 중요)

- 선택 A(**작업자 권고**, F5a): stop은 지금처럼 frame head callback 진입 LONG `(100820)`(`e4a`/`e74`)로 둔다. pass 입력은 직전 pass 출력 그대로다(PC=`e74`, A6=`100820`, A5=`108000`, A7=SPd−4, LONG(SPd−4)=`2ac2`). 한 frame은 다음 세 segment다.
  1. **H**: head `e74`(첫 frame `e4a`)부터 RTS `2ac2`, dispatcher가 `1008e4`의 `JSR (A0)`로 들어가는 순간까지 실행한다. stop=LONG `(1008e4)`.
  2. **선언 controller skip**: PC:=`2ac2`, A7+=4(RTS 대체), carry Unknown. 이때 A6는 이미 `1008e4`다. 이것이 현재 F2 경계 재설정(A6:=`1008e4`, PC:=`2ac2`, A7:=SPd)과 정확히 같은 상태다.
  3. **N**: 기존 F2 pass(stop LONG `(100820)`).
  - [I] N은 기존 F1~F4 검증과 같은 의미다. 바뀌는 것은 H 추가와 경계 레지스터 재설정의 제거다. pass 0은 지금처럼 seed 상태(PC `2ac2`, A6 `1008e4`)에서 N부터 시작한다.
  - controller를 구현하면(F5c) 2를 없애고 H+C+N을 stop LONG `(100820)` 한 번으로 실행한다.
- 선택 B: 자연 vblank 지점 `ef2`를 stop으로 둔다. 한 run은 `ef2`→…→`ef2`이다.
  - 장점: pause 루프(`fb4 BRA ec4`)의 각 반복도 run 하나다.
  - 단점: 현재 API는 시작 PC가 stop과 같으면 0 step으로 끝난다. 그래서 "첫 block은 stop 검사 전에 실행" 같은 API 변경이 필요하다. 또 기존 기록(`e74` 정지)과 frame 정렬이 어긋난다.
- 선택 C: head를 별도 API(host-level `step_main_frame` 재사용)로 돌린다. block 실행부 목표와 맞지 않아 비권고다.

### D2. IRQ 대기 `ef2`(vblank)

- 권고: 새 Waiting 종류 `vblank`를 둔다. `ef2` block이 BYTE `100016` < BYTE `100017`일 때만 PC=`ef2`로 Waiting한다. 선언 해제는 BYTE `100016` := BYTE `100017`(대기를 통과하는 최소 IRQ 수)이고, IRQ의 나머지 효과는 넣지 않는다.
- [F] 자연 seed는 `100017`=0이라 Waiting이 0건이다. [F] 자연 boot라면 `c46`이 2를 쓰고 게임 mode `c758`이 2를 쓴다. [U] 실제 값과 frame당 vblank 수.
- seed `100017` 보정은 하지 않는다(무단 수정 금지). 대신 typed fixture(1, 2)로 Waiting과 해제를 검증한다.
- 선택: IRQ `c8c`를 block 단위로 실행(712 block + BIOS `c0044a`)한다. 별도 F6 단위로 미룬다.

### D3. raster `3c0006`

- 권고: external read로 기록한다. 값은 frame마다 선언된 순서로 공급한다(H당 2회, `eaa`와 `efc`). 기본은 0이다(`(v>>7)−256`<0이므로 0으로 clamp).
- fixture는 v≥`8000`(clamp되지 않는 분기)과 두 읽기 값이 서로 다른 경우를 포함한다. [I] 실제 LSPC 줄 계수 값은 [U]다.

### D4. 입력 `300000`/`340000`/`380000`

- 권고: external read 선언 큐(frame당 3회 또는 5회, 순서 `380000` `300000` `340000` [`300000` `340000`])를 둔다. 기본값은 `ff`(누름 없음)이다. 큐가 비면 checked error로 처리한다.
- `104cd4`=1(replay) 경로는 ROM replay stream(`f01fe..`)을 읽으므로 기존 MS5D 근거(`input-sampler.md`)와 같다.

### D5. sprite flush 대기 `16bd0`

- 권고: 새 Waiting 종류 `sprite-flush`(PC `16bd0`, WORD `108d36`≠WORD `108d34`)를 둔다. 선언 해제는 WORD `108d34` := WORD `108d36`이다.
- [F] 근거: IRQ `16cfa` 계열이 `108d34`를 쓴다(c8c 탐침). 실험 C에서 85회 일어났다.
- 기존 `cda4`(`108d34`:=D4)와 같은 어휘다.

### D6. sound flush

- `3c08`→`3ac8`(routing됨)의 ring full 대기는 기존 sound Waiting `3aea`를 그대로 쓴다. 새 결정은 없다.

### D7. video port·watchdog·PVC

- 권고: 기존 관례를 따른다.
  - `3c0000` `MOVE.L`은 size 4 port 1건(map_transfer·`4fd8c` 관례)이다.
  - `3c0004` WORD, watchdog `300001` BYTE는 port다. 의미 해석은 하지 않는다.
  - PVC `2ffff0`/`2ffff2`는 기존 bank 모델을 쓴다.
- frame당 최대 약 6,400건이므로 port 목록은 digest와 dump frame에서만 전부 비교한다.

### D8. dead·guard 경로

- `f3c` aux callback(`100896`≠0), `931a` menu callback(`107df6`≠0): checked error로 둔다. 예: `unsupported animation frame head aux callback`, `unsupported animation frame head menu callback`.
- `fee TRAP #15`(`+7e`≠`10000e`): F3 TRAP과 같은 checked error 경계다.
- `ec4` debug 출력(`10f000` bit0, `3a70` u02 routing)은 일반 경로로 구현하고 fixture로 검증한다.

### D9. controller 상태

- 선택 A(**작업자 권고**, F5a): controller skip을 유지한다(D1 segment 2). head만 넣는다.
- 선택 B(F5c): 일관된 controller 상태를 선언하고 실행한다. 아래 셋 중 메인이 고른다.
  - (i) demo: `1008e4`:=`c66a`, `104cd4`:=1. replay 입력이며 `c724`→`c988`.
  - (ii) 게임: `1008e4`:=`c7fc`, `10fdaf`:=2. `b68`이 매 frame `100012`:=2로 복사한다.
  - (iii) 기록 그대로: 첫 frame에 해체. 비권고.
  - [I] (ii)가 stage play에 가장 가깝다. 그러나 seed가 어느 mode의 상태인지는 [U]다.
  - stage controller 비활성 frame(1/221/241/245)의 전환(`c76a`/`c686`)에서 생기는 자식(`b300` `e66aa` 등)은 미routing 경계다. 그곳에서 pass 전체 rollback이 된다.
- `JMP c00444`(SYSTEM_RETURN, 5곳): **종단** BIOS 경계다. 실행부는 PC=`c00444`에서 checked stop을 하고 resume이 없다.
- `JSR c00468`(`c310`): 기존 카드 BIOS 선언 resume과 같다.
- `JSR c00450`(`4a98c`, `10fd82`≠0일 때만): 선언 resume으로 둔다(PC=`4a992`, A7+=4, 응답 LONG `10fdb0..10fdb3`). [I] BIOS credit 확인. 자연 seed는 `10fd82`=0이라 닿지 않는다.

### D10. boot `c52a`/`c560`/`c56e`

- 권고: F5의 자연 경로에서 제외하고 typed fixture로만 검증한다.
- 선언이 필요한 값: BIOS 요청 `10fdae`(2=demo, 3=title), palette 대기 WORD `107dea`의 IRQ 감소. `c56e`는 `49a1a`로 RNG를 다시 초기화하므로 F4 seed 준비와 겹친다.

## 4. 단위 계획(≤ ~220 block)

[I] 반복 family(`5728` cell, sprite writer, Duff)는 C++에서 PC 산술 parametric 실행부로 구현하면 코드 양이 크게 준다. 이 경우에도 block 시작 규약(모든 진입 PC가 routing되고 split 가능)은 지킨다. 아래 수는 원본 block 시작 수다.

| 단위 | 내용 | 범위 | block | 자연 실행 | 의존 | 위험 |
| --- | --- | --- | --- | --- | --- | --- |
| H1 | head 본문 + flush/배경/기타 + D1 규약·D2 Waiting·D5 Waiting·D8 guard | `e4a..1000` `b68..bb4` `3c08..3c40` `16bba..16cf8` `166bc..16bb8` `1ae56..1aeb2` `1879c..187d6` `903a..9054` `9546..955c` `8bc8..8bde` `8be0..8c14` `3db2..3dca` `43dbc..43dca` | 120 | 77 | F2 | pause 루프, TRAP, raster clamp, `SUBX` |
| H2 | 입력 sampler + pause/menu | `31d6..35a0` `9086..932e` `313c` `3902..3916` | 151 | 19 | H1 | external read 큐, replay stream, card menu callee |
| H3 | palette frame | `5728..72ee` `4718..5726` | 551(고유 39 + cell 256×2) | 318 | H1 | unrolled 2,381명령 색 blend, watchdog 256회, PVC |
| H4 | 역방향 writer A | 표 `11792..117b2`, `117b2..11b7e` `11b7e..11f4c` | 157 | 자연 | H1 | `MULS`, VRAM LONG |
| H5 | 역방향 writer B | `11f4c..1231c` `1231c..126ee` | 149 | 자연 | H4 |  |
| H6 | 역방향 writer C | `126ee..12bfc` `12bfc..1310e` + Duff `12ae2` `12ff4` 64 | 215 | 자연 | H4 | Duff 진입 |
| H7 | 역방향 writer D | `1310e..13628` `13628..13b44` + Duff `1350e` `13a2c` 64 | 215 | 자연 | H4 | Duff 진입 |
| H8 | 정방향 writer A | 표 `ce62..ce82`, `ce82..d250` `d250..d620` | 157 | 0 | H4 | fixture 전용(`108d3c` bit7) |
| H9 | 정방향 writer B | `d620..d9f2` `d9f2..ddc6` | 149 | 0 | H8 |  |
| H10 | 정방향 writer C | `ddc6..e2d6` `e2d6..e7ea` + Duff 64 | 215 | 0 | H8 |  |
| H11 | 정방향 writer D | `e7ea..ed06` `ed06..f224` + Duff 64 | 215 | 0 | H8 |  |
| C1 | controller gate·매 frame 꼬리·표시 helper + `c00450` resume | `c654..c686` `c988..ca22` `c49c..c52a` `ca32` `30bc` `30d4` `314c` `100e` `101c` `4a88e..4a9e0` `36ba`/`3706`(`3670..370a`) | 116 | 선언 상태 필요 | H1, D9 | `SBCD`, `JSR (A1)` |
| C2 | 전환·해체·게임 mode 분기 + `c00444` 종단·`c00468` | `c686..c6ce` `c724..c988` `3162` `4755e` `47570` `4823a` `49a1a` `4e1cc` `bbd4` `c2fa..c364` `8b64` `8bb6` | 127 | 전환 frame | C1 | 자식 미routing, `caf0` port 2,072 |
| C3 | boot·demo 도입·title | `c52a..c654` `c6da..c724` `4fb1a` `e62ec` | 48 | fixture 전용 | C2 | BIOS 요청·`107dea` 선언 |

- 합계는 head 2,294(Duff 포함), controller 298(공유 7 제외 291)이다.
- 권고 순서:
  1. H1→H2→H3→H4~H7로 F5a 자연 완주를 시도한다.
  2. 그다음 C1→C2(D9 선택 B 결정 뒤)를 진행한다.
  3. H8~H11·C3은 fixture 전용이라 마지막에 둔다.
- [I] H1만으로는 `16bba`가 writer 표로 들어가는 순간 rollback된다. 그래서 자연 pass 완주는 H4~H7까지 필요하다.
- 무효화되는 기존 시험(수정하지 말고 단위 작업에서 정리):
  - `engine/tests/animation_machine_scheduler_test.cpp` `pass-controller`(`c52a` 미routing을 기대). C1/C3 뒤 무효가 된다.
  - `tools/verify_animation_machine_scheduler.py`의 `pass-head-ring-unchecked`(controller에서 `unsupported animation machine PC`). C1/C3 뒤 무효가 된다.
  - 경계 탐침으로 `e74`/`c52a` 계열 PC를 쓰는 시험은 H1/C1 뒤에 다시 확인해야 한다(새 탐침은 work RAM PC `10fe00..10fefe` 관례).

## 5. native 관측 계획

- 새 도구 `tools/observe_animation_machine_frame_head.py`, 산출 `artifacts/animation_machine_frame_head_native/`. scheduler·rng·pvc_banks 관측기는 in-process import만 하고 수정하지 않는다. 계약 SHA를 고정한다.
- seed: RNG 준비된 자연 137(+guard 5)이다. 규약은 D1 A(H+선언 skip+N), 400 frame이다. 선언 입력 기본값은 입력 `ff`/`ff`/`ff`, raster 0이다. 선언 vblank·sprite-flush·sound·gate·카드 BIOS 해제는 모두 `declared` 목록에 남긴다.
  - [F] 탐침 기준으로 H의 Waiting은 `16bd0` 해제(seed 0·1·2·135, 85회) 외에는 없다. 정방향 writer·pause·menu·aux·TRAP은 0회다.
- 기록 항목:
  - frame마다 H/N 각각의 시작·끝 전체 상태 SHA(64 KiB RAM, 16R, PC, A7, bank, PVC)
  - 순서 있는 port digest(H는 6,000건 이상일 수 있다), external read 열(주소, 크기, 선언 값)
  - node 방문 순서, H의 leader hit
- 기존 rng 관측과 교차 비교: N의 시작 상태가 "기록 pass-end + H 효과"와 같은지 확인한다. 실험 C가 같은 하네스로 기존 기록을 바이트 단위로 재현함을 이미 보였다.
- 변형:
  1. 입력 스크립트(P1 방향·버튼, start, `380000` 비트)로 `31d6`/`9136` 분기를 넓힌다. seed 몇 개만 쓴다.
  2. raster ≥`8000`, 두 읽기 값을 다르게 둔다.
  3. `100017`=1·2(vblank Waiting).
  4. D9 B(i)/(ii) controller 상태(C1·C2용). 전환 frame(1/221/241/245)을 포함한다.
- typed fixture(자연 미도달 leader 1,475 + Duff 252):
  - 정방향 writer 8개(`108d3c` bit7=1), 각 Duff 진입 32개(sprite 높이 0..31)
  - `5728` 타이머 경로(`107dd4`≠0)와 cell 분기 양쪽, blend helper 4종
  - pause/menu(`107df0`/`107df1`/`107def`/`10f000` bit1, `9086` mode)와 `fb4` 루프
  - `e4a` 첫 frame, `fee` TRAP, aux·menu callback guard, `ec4` debug
  - controller boot(`10fdae`=2/3, `107dea`)와 `c00450`/`c00468`/`c00444`
- 관측 규칙(공통): 조건마다 fresh-CPU split과 continuous를 각 두 번 실행해 비교한다. 전이 명령 직후에만 멈춘다. dump는 8 seed와 경계 frame에서 남긴다.
  - 단위 block의 독립 Python 모델은 반복 family를 cell 단위 parametric 모델로 만들고 매 segment 비교한다. 기존 `S.Model` 68k 해석기를 재사용할 수 있다.
  - 두 번 실행해 `observation.json` SHA가 같은지 보고 `diff -rq`로 확인한다.
- 크기 추정: 기존 rng 관측 204 MB에 H의 dump와 port digest가 더해진다. [I] 1 GB 미만(port 전체 목록은 dump frame만 남김).

## 6. frame 규약 변화 요약(D1 A 기준)

| 항목 | 현재(F2~F4) | F5a | F5c |
| --- | --- | --- | --- |
| stop | LONG `(100820)` 진입 | 같음 | 같음 |
| 경계 host 쓰기 | A6:=`1008e4`, PC:=`2ac2`, A7:=SPd(매 frame) | 없음(직전 출력 그대로) | 없음 |
| head | skip | 실행(H) | 실행 |
| controller | skip | H stop LONG `(1008e4)` 뒤 선언 RTS(PC `2ac2`, A7+=4) | 실행(선언 controller 상태 1회) |
| IRQ | 없음 | `ef2` Waiting `vblank`(`100016`:=`100017`), `16bd0` Waiting `sprite-flush` | 같음 |
| external read | node 내부만 | + raster 2, 입력 3~5 | 같음 |
| BIOS | `c00468` resume | 같음 | + `c00450` resume, `c00444` 종단 |

## 7. 미확인

1. 자연 `100017`·frame당 vblank 수, `3c0006` 실제 값, seed가 demo/게임 중 어느 상태인지.
2. IRQ `c8c` 문맥 전환(`ce2..d28`, `10081c` task stack)의 의미와 head 대기와의 상호작용.
3. `e40`(aux 설정)·`107df6`(menu callback)의 실제 사용 여부(BIOS·디버그 경유 가능성).
4. Duff 진입 D7.B 범위가 모든 8곳에서 `ANDI #1f`/`ADD.B`로 제한되는지. 첫 routine 형태로 추론했고 각 routine의 정확한 선행 경로는 단위 계약에서 확인한다.
5. controller 자식 7개와 게임 mode 상태(`c79a` 이후)의 매 frame 의미.
