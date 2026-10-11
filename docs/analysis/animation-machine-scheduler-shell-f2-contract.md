# scheduler shell F2: 노드 디스패처·프레임 패스 계약 초안

**상태: 메인 결정 반영 계약. 구현·검증 기록이 아니다.**

메인 결정(Claude Opus 5.5):
1. 범위는 새 block 4개(`2aac` `270e` `2716` `271a`)와 stage controller fade 자식 `4fcce`(13 block)를 함께 둔다. 파일 `engine/src/animation_machine_scheduler.cpp`.
2. 프레임 패스는 권고대로: PC=`2ac2`, A6=`1008e4`에서 시작해 실제 node 목록(자식 삽입·삭제 포함)을 따르고 frame head callback LONG `(100820)`(`e4a`/`e74`)에서 stop한다. 실행부 없는 node는 패스 전체 rollback. F1 직접 재진입은 패스의 `100b30` 구간과 같으므로 F1a~F1c 검증은 유효하다.
3. frame head `e74`·controller `c66a`는 선언 효과 없이 건너뛴다(생략 목록은 본문). 
4. SPd는 기존 F1a 결정 7(c)·stage_frame 규약과 같은 `1ff000`(work RAM `10f000`의 64KiB mirror이며 같은 물리 RAM)으로 선언하고 첫 패스 전에 LONG `104ca4`=SPd를 선언 쓰기한다. 권고값 `10f000`은 같은 RAM이지만 기존 산출물과 A7 값을 맞추기 위해 mirror 값을 쓴다.
5. 순서는 F3a → F2(+`4fcce`) → F3b(F1c2 뒤). 
6. 관측 도구 `tools/observe_animation_machine_scheduler.py`를 새로 두고 F3 node 단위 seed도 여기서 만든다. 범위 근거는 `animation-machine-frontier-after-480bc-scope.md`의 F2이며, 구조와 규약(block 시작, 묶인 분기, carry 보존 목록, 경계, 선언 host 쓰기)은 확정된 F1a(`animation-machine-stage-controller-f1-contract.md`)·F1b·F1c·U7 계약을 따른다.

Claude Opus 5.5 / high 읽기 전용 분석 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, fixed CPU 주소=file offset)을 capstone M68000으로 디코드했다. F2의 코드·자료는 모두 fixed `<100000`이다. 기존 실행부와 routing은 작업 트리 `/Users/start/Workspce/metalslug-input`(HEAD `543a3a4`, U1~U7·F1a 포함, F1b `animation_machine_area_clear.cpp`는 커밋 전 WIP)의 `engine/src`를 읽기 전용으로 참조했다. 관측 산출물은 Unicorn으로 읽기 전용 재생했다. [F]=원본 바이트, 기록 산출물 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. 이 문서의 "자연"은 게임 자연 실행이 아니라 아래 결정 2의 선언 프레임 경계 모델을 Unicorn에서 돌린 결과다. BIOS 실행·자연 IRQ·자연 scheduler 진행을 주장하지 않는다.

## 요약

- [F] **범위 정정.** 디스패처 루프 `2ab8..2ac6`(block `2ab8` `2abe` `2ac0` `2ac2` `2ac6`)과 객체 자기 삭제 `2a00..2a06`(block `2a00` `2a02` `2a06`)은 이미 fade_card 실행부(`animation_machine_fade_card.cpp`)에 있고, node 설치 `2a28`(+`2a48` `2a6c` `2a90`)은 cleanup 실행부에 있다. 범위 문서의 "F2 ~10 block", "F3 = `e9150`+`2a28`"은 이 점을 반영하지 않은 값이다.
- [F] F2에서 새로 필요한 원본 block은 **4개**다: boot 진입 `2aac`(LEA+`MOVE.L A7,104ca4`, `2ab2`는 참조 없는 내부 PC)와 idle node callback `270e` `2716` `271a`. 선택 사항으로 stage controller의 fade 자식 `4fcce`(13 block, 결정 1)가 있다.
- [F] F2의 실질은 코드보다 **실행 규약**이다. 현재 F1a~F1c는 node 하나를 "선언 직접 재진입(A6=`100b30`, A5=`108000`, `(A7)`=`2ac2`)"으로 돌리고 `2ac2`에서 멈춘다. 이를 원본 디스패처가 node list를 따라가는 **프레임 패스**(`2ac2`, A6=`1008e4`에서 시작해 frame head callback 진입에서 stop)로 바꾸는 것이 결정 2다.
- [F] frame head(`100820`: `e4a`→`e74`)와 controller(`1008e4`: `c52a`→`c66a`)는 기록된 어떤 산출물에서도 실행된 적이 없다(아래 "자연 시작 상태"). 두 node는 F5 범위이며 F2에서는 프레임 경계의 **선언 skip**으로 둔다(결정 3).
- [F] Unicorn 프레임 패스 탐침(stage_entry_body begin 출력 142 seed, 120 frame): 134 seed가 120 frame을 완주했다. F1a·F1b·F1c·F3a·F2가 모두 구현됐다고 가정할 때 패스 전체가 실행부 안에 드는 seed는 8개(120 frame 전부), `4fcce` 자식까지 넣으면 22개다. 나머지 112개는 frame 0부터 객체 long tail callback(`d6d22` `d7828` `b4d7e` `dbdb6` 등)이 list에 있어 패스 전체 실행은 불가능하다(node 단위 실행만 가능).

| 항목 | 값 |
| --- | --- |
| 새 block 시작 | 4(`2aac` `270e` `2716` `271a`) + 선택 `4fcce` 13 |
| 묶인 조건분기 | 1(`2712`) + 선택 `4fcce` 5 |
| carry 소비 block | 0 |
| carry 보존(FLOW_ONLY) | 1(`271a`) |
| 기존 실행부로 나가는 지점 | `2ab8`(fade_card, `2aac` fall-through), `2a00`(fade_card, `4fcce` 끝) |
| 경계(실행부 없음) | frame head callback `e4a`/`e74`(프레임 패스 stop), controller callback `c52a`/`c66a`(선언 skip) |

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

### 1. 실행부 파일과 범위

- 선택 A(**작업자 권고**): 새 실행부 `engine/src/animation_machine_scheduler.cpp`(`bool animation_scheduler_block(AnimationMachineContext&)`), routing 2 범위 `2aac..2ab8`, `270e..271c`. 기존 `2ab8..2ac6`·`2a00..2a06`은 fade_card에 그대로 둔다(파일 이동 없음). 오류 문자열은 단위 관례대로 `unsupported animation scheduler PC`.
- 선택 B: 같은 파일에 stage controller fade 자식 `4fcce..4fd0a`·`4fd58..4fda6`(13 block)을 더한다. [F] 이 자식은 `47b76`(`47b06` 표 index `0c`, begin 재진입 137 중 89건)이 `28ae`로 만든다. 넣으면 프레임 패스 전체 검증 seed가 8→22개로 는다. 자식은 `3c0000`에 `MOVEM.W D3-D4,(A4)`로 VRAM 주소·자료를 쓴다(기존 map_transfer 관례대로 port `3c0000` size 4 한 건으로 기록 권고). 형제 변형 `4fd0a`/`4fd20`(callback `4fd16`/`4fd2c`, 7 block 추가: `4fd0a` `4fd16` `4fd20` `4fd2c` `4fd32` `4fd40` `4fd50`, `47b8c` index `10` 경로)은 자연 seed가 없다.
- 선택 C: F2를 따로 두지 않고 4 block을 cleanup 실행부(`299c`/`2a0a`가 이미 `270e`를 비교·설치)에 넣는다. 파일 소유 충돌 위험이 있어 비권고.

### 2. 프레임 패스 모델 (가장 중요)

**원본 동작**
- [F] boot `a26 JMP 2aac` → `2aac LEA 100820,A6` → `2ab2 MOVE.L A7,104ca4` → `2ab8 LEA 108000,A5` → `2abe MOVEA.L (A6),A0` → `2ac0 JSR (A0)`(복귀 `2ac2`) → `2ac2 MOVEA.L 8(A6),A6` → `2ac6 BRA 2ab8`. 탈출 경로는 없다. fixed 1 MiB 전 짝수 offset 디코드에서 이 shell로 들어오는 제어 이동은 `a26 JMP 2aac`, `2a06 BRA 2ac2`, `2ac6 BRA 2ab8`, `2712 BEQ 271a`뿐이다. `e4a`·`e74`로 가는 분기·호출은 없다(`e74`는 `e6e MOVE.L #e74,(A6)`로만 설치되고 `e4a`는 `e74`로 fall-through).
- [F] 프레임 동기화는 frame head callback `e74`의 `ef2..efa`(BYTE `108016` < BYTE `108017`이면 spin, IRQ `c8c`가 올림)뿐이다. 즉 원본의 "한 frame"은 frame head 실행 사이의 list 한 바퀴다.
- [F] node list는 원형 이중 연결이다(아래 "node 구조"). seed RAM의 순서: `100820`(e4a) → `1008e4`(c52a) → `1009a8`(270e) → `100a6c`(270e) → `100b30`(stage controller) → [자식] → `100bf4`(stage event) → [자식] → `100cb8`(270e) → `100da8`(270e) → `100820`.
- [F] `28ae`는 자식을 부모 바로 뒤에 넣는다(`28fc`). 그래서 같은 패스 안에서 막 만든 자식도 곧바로 실행된다. Unicorn 탐침에서 같은 frame에 slot `1013f4`가 `d7828`로 실행된 뒤 해제·재할당되어 `bb188`로 다시 실행된 사례가 있다.
- [F] `2a00`(자기 삭제)은 `299c`로 node를 해제한 뒤 `2a02 MOVEA.L 104ca4,A7`, `BRA 2ac2`로 **디스패처 수준 A7을 LONG `104ca4`에서 복원**한다. 기록된 모든 seed RAM에서 LONG `104ca4`=0이다(boot `2ab2`가 실행되지 않은 host 구성 RAM).

**선택지**
- 선택 A(**작업자 권고**, 프레임 패스):
  - 입력: PC=`2ac2`, A6=`1008e4`(controller callback이 막 돌아온 상태), A7=SPd(디스패처 수준), LONG `104ca4`=SPd(결정 4), carry Unknown. stop PC=LONG `(100820)`. 이 값이 `e4a`나 `e74`가 아니면 host가 실행 전에 거부한다.
  - 실행: `2ac2`가 `8(1008e4)`를 읽어 다음 node로 가고, controller 자식 → `100b30` → 그 자식 → `100bf4` → … → `100da8`을 원본 순서대로 돌린 뒤 `2ac0 JSR (A0)`이 frame head callback으로 들어가는 순간 PC=stop으로 멈춘다.
  - 출력(stop 시점): PC=A0=`e4a`(또는 `e74`), A6=`100820`, A5=`108000`, A7=SPd−4, LONG `(SPd−4)`=`2ac2`.
  - 다음 frame: 결정 3의 선언 경계 적용 뒤 같은 입력 형태(PC=`2ac2`, A6=`1008e4`, A7=SPd)로 다시 시작한다. stack LONG `(SPd−4)`=`2ac2`는 원본 JSR이 남긴 stale 값이며 그대로 둔다.
  - 한 node라도 실행부가 없으면 `unsupported animation machine PC`로 **패스 전체 rollback**이다. Waiting(sound `3aea`, sprite `cda4`, gate `47af0`/`478de`)은 패스 중간에서 돌려주며, 같은 stop으로 재개하면 패스를 이어 간다.
  - [I] F1 선언 재진입과의 관계: 패스 안의 `100b30` 구간(`2abe`→callback→`2ac2`)은 F1a 결정 7(c)의 선언 재진입 한 번과 같은 상태 변화다. 따라서 F1a~F1c 검증은 패스의 부분 구간 검증으로 그대로 유효하다.
- 선택 B(현행 유지): host가 list를 직접 걷고 node마다 PC=`2ab8`, A6=node, stop `2ac2`로 돌린다(card child test가 쓰는 방식). 실행부가 없는 node를 건너뛸 수 있지만, 디스패처가 `8(A6)`를 따라가는 원본 순서·삽입·삭제를 host가 흉내 낸다. node 단위 검증(F3 등)의 보조 모드로만 권고한다.
- 선택 C: PC=`2ab8`, A6=`100b30`에서 시작한다. controller(`1008e4`)의 자식을 건너뛰므로 비권고.
- 선택 D: frame head `e74`·controller `c66a`까지 실행한다. F5(~850+~280 block, IRQ poll·raster read·BIOS) 선행이 필요하다.

### 3. 프레임 경계의 선언 skip과 생략되는 원본 효과

- 선택 A(**작업자 권고**): 경계에서 원본 코드를 실행하지 않고 A7=SPd, A6=`1008e4`, PC=`2ac2`로만 되돌린다. 효과는 선언하지 않는다. 단, F1 결정 2의 palette gate 대기 해제와 F1b·F1c의 선언 host 쓰기(`62(A6)`, `10dd44` 등)는 기존 규약대로 이 경계에서만 적용한다.
- [F] 생략되는 원본 효과(전부 F5 범위):
  - `e4a`(첫 frame만): `e7bf4`, WORD `10800e`=0, `7e`/`84`/`76(A6)`, `903a`, callback→`e74`.
  - `e74`:
    - port 쓰기 `3c0004`=0, `3c0000`=`82000000`, `3c0006` raster 읽기.
    - `3c08` `16bba` `1ae56` `5728`, BYTE `10801b` bit7.
    - IRQ 대기 `ef2`, BYTE `108018`/`10801a`/`108016` 갱신, `CLR.W 104ca2`(`f1e`), `31d6`, `b68`, `76(A6)` 보조 callback, `9136` 등.
  - `c66a`: `289e`(`100b30` 활성), `314c`(BYTE `104cd4`=1)를 확인한다. 정상 frame이면 `c724`→`c988` 매 frame 처리, 비활성이면 `c69a` 종료 경로(`c4cc` `caf0` `ca76` 자식 `e66aa` BIOS `c00444`)다.
  - `c52a`(controller가 한 번도 안 돌았을 때): `9056`, `8b64`, `c560` 대기와 그 이후 boot 흐름, `c654`의 `477e4` 설치. [F] 모든 seed RAM에서 `1008e4`=`c52a`다.
- [F] `104ca2`(zombie node 방문 수, `2716`이 증가)는 `e74 f1e`와 `2848`만 지운다. fixed ROM 안에 A5 상대·절대 주소로 읽는 명령은 없다. 선언 skip에서는 패스마다 누적된다. [U] 다른 포인터 경로로 읽히는지.
- 선택 B: `CLR.W 104ca2` 하나만 선언 효과로 넣는다. 원본 frame 끝 값과 더 가까워지지만 Unicorn 기준 산출물도 같은 선언을 따라야 한다.

### 4. 디스패처 수준 A7(SPd)과 LONG `104ca4`

- [F] 게임 코드는 A7을 직접 설정하지 않는다(boot `960..a26`과 `400..3000`에 A7 대상 LEA/MOVEA/MOVE는 `2a02` 하나뿐이다). boot 시 A7은 BIOS가 넘긴 값이고 `2ab2`가 이를 `104ca4`에 저장한다. [U] 자연 값.
- 권고: SPd=`10f000`으로 선언하고 첫 패스 전에 LONG `104ca4`=SPd를 선언 host 쓰기로 둔다. 기존 F1a·F1b test의 SP=`10effc`, LONG `10effc`=`2ac2`(디스패처 수준 `10f000`)와 같다. [F] `104ca4`≠SPd이면 `2a00`을 지나는 패스가 A7을 엉뚱한 값으로 바꾼다. [I] 예를 들어 0이면 다음 JSR push 주소가 `fffffc`(RAM 밖)가 되어 checked 오류로 rollback된다. 이 음성 사례를 test로 둔다.

### 5. 순서

- 권고: **F3a → F2(+`4fcce`) → F3b**. [F] 프레임 패스 전체 검증 seed 22개는 F1a·F3a·`270e`(+`4fcce`)만 지난다. 그 seed들은 F1b·F1c·F3b block을 한 번도 지나지 않았다(탐침: F3b leader 접촉 0). F2만 먼저 구현하면 모든 자연 패스가 `100bf4`의 `e9150`/`e9176`에서 rollback되므로 합성 list test만 가능하다.

### 6. 새 관측 산출물

- 권고: `tools/observe_animation_machine_scheduler.py`가 `artifacts/animation_machine_scheduler_native`를 만든다. 입력은 stage_entry_body begin 출력 142건, 선언 SPd·`104ca4`, 결정 3의 경계 모델이다.
  - frame 상한: 22 패스 가능 seed는 끝까지(6 seed×≥400 frame 상한 400, 2 seed×240, 14 seed×244는 BIOS `c00468` 경계까지), 나머지는 120 frame이다.
  - 기록: 패스마다 전체 상태 SHA(64 KiB RAM·16R·PC·A7·bank·PVC·순서 있는 port), node 방문 순서(A6, callback), 패스 전체 가능 여부를 남긴다.
  - 전체 dump: 패스 가능 seed의 frame 0, 1, 20, 21, 마지막, 그리고 처음 나타나는 node 구성마다 남긴다.
  - F3 node 실행 seed(F3 계약)도 같은 도구가 만든다.

## 원본 바이트 근거

[F] 아래 hex는 위 ROM에서 직접 추출했다.

| CPU 범위 | 원본 바이트 | 디코드 |
| --- | --- | --- |
| `2aac..2ab8` | `4df90010082023cf00104ca4` | `LEA 100820,A6`; `MOVE.L A7,104ca4` |
| `2ab8..2ac8`(기존 fade_card) | `4bf90010800020564e902c6e000860f0` | `LEA 108000,A5`; `MOVEA.L (A6),A0`; `JSR (A0)`; `MOVEA.L 8(A6),A6`; `BRA.B 2ab8` |
| `270e..271c` | `4a6e001067000006526dcca24e75` | `TST.W 10(A6)`; `BEQ.W 271a`; `ADDQ.W #1,-335e(A5)`; `RTS` |
| `2a00..2a0a`(기존 fade_card) | `619a2e6dcca4600000ba` | `BSR 299c`; `MOVEA.L -335c(A5),A7`; `BRA.W 2ac2` |
| `4fcce..4fd0a`(선택) | `3d7cffe2007a2cbc0004fcda207c00050074322e007a56410c4100286d000012206e000c117c000100624ef900002a003d41007a343c000160000050` | |
| `4fd58..4fda6`(선택) | `4a416e00000e44415241d241d0c1323c000149f9003c00003a0238180c4100276400002a0c44ffff670000220c42001f640000143601eb4bd6420643700048940018524260e65241340560ce4e75` | |
| 자료 `268a..270e`(static node 초기화 표) | `00100820 00000e4a 0000×4` 다음 16바이트 record(node, callback, WORD×4) 7개(`1008e4`/`c52a`, `1009a8` `100a6c` `100b30` `100bf4` `100cb8` `100da8`/`270e`), 끝 LONG 0 | `2790`이 읽는다 |

[F] 기존 routing 규칙과 겹침이 없다(`2aac` `2ab2` `270e` `2712` `2716` `271a`, `4fcce..4fda6` 모두 미배정. 작업자 scratch `routing.py`는 현재 worktree의 routing을 재현한다).

## node 구조(실행 의미의 근거)

[F] `271c`(node 초기화), `2790`(static list 구성), `2800..287c`(pool 구성), `28ae`(자식 할당, 기존 fade_card 실행부), `299c`(해제, 기존 cleanup)에서 확인했다.

| offset | 폭 | 의미 |
| --- | --- | --- |
| `+0` | LONG | callback PC(디스패처가 `JSR`) |
| `+4` / `+8` | LONG | prev / next(원형 이중 연결) |
| `+c` | LONG | parent(static은 0) |
| `+10` | WORD | 깊이(static 0, 자식은 부모+1, `28ae`) |
| `+12` `+13` | BYTE | `ff`로 초기화 |
| `+15` `+61` `+62` `+63` | BYTE | 0으로 초기화(`+62`는 자식 완료 flag로 쓰인다) |
| `+1e` | WORD | `ffff`로 초기화 |
| `+6a` | BYTE | 부모에서 복사(`28ae`) |
| `+76..+c4` | LONG×19+WORD | 0으로 초기화되는 callback 지역 변수 |

- [F] node 크기는 `c4`(196)이다. static node는 8개(`100820`부터 `c4` 간격, 마지막 `100da8`)다. 그 뒤 `100e98..100f5c`는 sentinel node다(callback `270e`, prev/next/parent=자기 자신, `28ae` 실패 시 A0 fallback).
- [F] pool은 `100f5c`부터 `c4` 간격 80개이며 끝은 `104c9c`다. `2834`가 개수 `50`을 검사하고 아니면 TRAP한다.
  - 전역: LONG `104c9c` free list head, WORD `104ca0` free 개수(`28ae` 실패 조건), WORD `104ca2` zombie 방문 수, LONG `104ca4` 디스패처 수준 A7.
- [F] `270e`는 빈 callback이다. 깊이 0(static idle)이면 아무것도 쓰지 않고 RTS한다. 깊이≠0이면 `299c`가 자식이 남아 해제를 미룬 zombie node이며 WORD `104ca2`를 1 늘린다(WORD wrap). [F] 탐침 120 frame 동안 `270e` 실행 70,154회 중 static 69,638회, pool zombie(깊이≠0) 516회였다.

## 구현 범위와 규약(권고 A)

- **routing 2 범위**: `2aac..2ab8`, `270e..271c`(선택 B: `4fcce..4fd0a`, `4fd58..4fda6`).
- **Block 시작 4개**: `2aac` `270e` `2716` `271a`. [F] `2ab2`는 분기 대상도 참조도 없어 `2aac` block 내부 PC다.
  - `2aac`: A6=`100820`, LONG A7→`104ca4`(A7은 바꾸지 않는다), PC=`2ab8`(fall-through, 기존 fade_card block).
  - `270e`: WORD `10(A6)`가 0이면 PC=`271a`, 아니면 `2716`.
  - `2716`: WORD `-335e(A5)`(A5=`108000`이면 `104ca2`) +1, PC=`271a`.
  - `271a`: RTS.
- **묶인 조건분기 1개**: `2712`(같은 block `TST.W` 뒤). 직접 진입은 거부한다.
- **carry**: 소비 block은 없다. FLOW_ONLY는 `271a`. `2aac`(`MOVE.L` C=0)와 `270e`/`2716`(TST/ADDQ)은 carry를 Unknown으로 둔다(소비자가 없다).
- **내부 PC**: `2ab2` `2712` `2714` `2718` `2710` 등 범위 안 짝수 PC 중 block 시작이 아닌 것은 `unsupported animation scheduler PC`.
- **선택 B `4fcce` 13 block**: `4fcce` `4fcda`(callback, `MOVE.L #imm,(A6)` 설치) `4fcee` `4fcfe` `4fd58` `4fd5e` `4fd6a` `4fd72` `4fd7c` `4fd84` `4fd8c` `4fd9e` `4fda4`.
  - 묶인 분기 5개: `4fcea` `4fd5a` `4fd78` `4fd80` `4fd88`(모두 같은 block의 CMPI/TST 뒤). carry 소비 block은 없다.
  - 끝은 `4fcf8 JMP 2a00`(부모 `62`=1 설정 뒤 자기 삭제)이다.
  - ROM 자료 `50074..`(WORD 열, `ffff` 종료)은 physical window로만 읽는다.
  - 무한 루프는 없다(`d1`<`27`, `d2`<`1f` 상한).
- **새 Waiting·상태 값 없음.** 프레임 패스는 기존 `run_animation_machine`의 stop PC 하나로 표현한다.
- **block budget**: [F] 탐침의 패스당 최대 Unicorn TB 수는 191,890(long tail 포함 seed), 패스 가능 22 seed는 5,510 이하다. 기존 1,000,000 block 한도로 충분하다.

## 자연 시작 상태(읽기 전용 재생)

[F] scratch `f23/sched*.py`가 `artifacts/stage_entry_body/observation.json`(SHA256 `1f65100f1fedc36b4999543c720814dc6f9eb4bf634f3af3439aa68d70e31207`)의 begin(또는 `release-poisoned-prefix`) 출력 중 final PC `ff000`인 142건을 썼다. 레지스터와 bank는 기록된 값이고, 선언 SPd=`10f000`과 LONG `104ca4`=SPd를 썼다. 결정 2 A와 결정 3 A(경계 효과 없음, `100820`·`1008e4`는 `2abe`에서 PC=`2ac2`로 skip)를 Unicorn으로 재생했다.

- [F] 기록 산출물 24,302개 RAM의 node list 조사(scratch `frontier/scan_nodes.py`): 정상 구성 1,833개 모두에서 `100820`=`e4a`, `1008e4`=`c52a`였다. frame head와 controller는 한 번도 실행되지 않은 상태다. `100bf4`=`e9150`인 상태가 303개 있고 `e9176`(실행 후 callback)인 상태는 0개다.
- [F] 120 frame 결과:
  - 134 seed 완주.
  - 5 seed(`wholebody-sound-wait`, release 출력)는 `100b30`=`deadbeef`로 frame 0에서 홀수 JSR이다. machine에서는 `animation fade card odd JSR target`이 된다.
  - 2 seed는 BIOS `c00468`(fade_card `c376` 경계, `47b22`→`4809a` 경로)이다.
  - 1 seed(case 141)는 F1a와 같은 `47c05` 홀수 PC 예외다.
  - 디스패처 진입 시 A7≠SPd는 0건, Waiting 정지는 0건, 선언 host 쓰기는 0건이었다.
- [F] 패스 전체가 실행부 안에 드는 seed(F1a·F1b·F1c·F3·`270e` 가정):
  - 8개(case 50, 51, 100, 101, 106, 107, 110, 111)는 모든 frame이 그렇다. 100·101·106·107·110·111은 `47b1e`→`480b6`으로 stage controller가 frame 0에 스스로 삭제되고 event node만 400 frame 이상 남는다. 50·51은 `47b5c` 연쇄→`47c6c` 뒤 240 frame에서 BIOS `c00468`에 닿는다.
  - `4fcce` 자식을 더하면 14개(case 4, 5, 10, 11, 48, 49, 64~67, 78, 79, 86, 87)가 늘어 22개다. 이들은 244 frame에서 BIOS `c00468`에 닿는다.
  - [F] 이 22개는 400 frame 상한 안에서 F1b·F1c·F3b block을 한 번도 지나지 않았다(scratch `sched6.py` block hook).
- [F] frame 0에 실행부가 없는 callback(seed 수): `4fcce` 89, `d6d22` 22, `d7828`·`d73de`·`d72f2` 17, `b4d7e`·`7090a` 14, `bafe6`·`bb188`·`bb536`·`babb4`·`dbdb6` 13 등.

## 검증 조건(최소)

**단위(host-write)**
- `270e`: 깊이 0이면 RAM 불변, 깊이≠0이면 WORD `104ca2`+1(`ffff`→0 wrap 포함). A5≠`108000`이면 A5 상대 주소를 따른다.
- `2aac` 진입: PC=`2aac`, A7=X, stop `e4a`(list가 static 8 node, 나머지 `270e`)이면 LONG `104ca4`=X, A6=`100820`, A0=`e4a`, A7=X−4, LONG `(X−4)`=`2ac2`, A5=`108000`이다.
- 묶인 `2712`·내부 PC `2ab2` 직접 진입 거부, 홀수 A6 읽기 오류, zero-step.

**프레임 패스(합성 list)**
- static 8 node만 있을 때 한 패스가 `1009a8`…`100da8` `270e` 6회 후 `e4a`에서 stop. 출력 레지스터·stack은 결정 2 A와 같아야 한다.
- 패스 중 `28ae` 자식 생성(같은 패스에서 실행), `2a00` 자기 삭제(A7=`104ca4` 복원 후 다음 node 계속), zombie 해제 루프(`299c` `29c0..29fc`).
- 실행부 없는 callback이 섞이면 패스 전체 rollback(RAM·port 불변).
- `104ca4`≠SPd 음성 사례, stop 값이 `e4a`/`e74`가 아닌 list는 host 거부.
- 패스 중간 Waiting(sound `3aea`, sprite `cda4`, `47af0` gate)과 재개 후 같은 stop까지 완주.

**자연(결정 6 산출물)**
- 패스 가능 22 seed를 C++가 직전 C++ 출력에서 frame마다 이어 실행하고, 모든 패스의 상태 SHA를 Unicorn과 비교한다. dump frame은 바이트 비교한다. split/continuous 두 방식으로 한다.
- 같은 seed의 `100b30` 구간을 F1a 선언 재진입 결과와 교차 비교한다(결정 2 [I] 등가성).
- 나머지 seed는 패스 전체가 rollback되는지(오류 문자열·상태 불변)만 확인한다.

**비교 항목**: 기존과 같다(64 KiB RAM, 16R/PC/A7, carry 분류, PVC·bank, 순서 있는 port, external reads, status, 입력·산출물 SHA, ROM stat 불변).

## 미확인·범위 밖

1. 자연 SPd·`104ca4` 값(BIOS가 넘긴 A7)과 boot 직후 첫 frame 상태. 기록 산출물에 boot 이후 frame head가 돈 상태가 없다.
2. 선언 skip이 생략하는 `e74`·`c66a` 효과가 F1~F3 경로에 주는 영향의 크기. 특히 frame counter, sound handshake, `c988` 이후 매 frame 처리.
3. frame head(`100820`)의 자식이 있을 때. 패스 시작이 `1008e4`이므로 그 자식은 건너뛴다. 기록된 list에는 없다.
4. `104ca2`의 소비자(포인터 경유 읽기 여부).
5. `4fd0a`/`4fd20` fade-out 변형의 실제 사용 경로(`47b8c`, index `10`).

작업자 scratch: 세션 scratchpad `f23/`(`clos3.py`, `sched.py`, `sched2.py`~`sched5.py`, `ana.py`, `s2.pkl`, `s3.pkl`, `s5.pkl`; 저장소 밖).
