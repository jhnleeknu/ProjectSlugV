# stage controller 완성 F1c: catalog·area·transition 계약 초안

**상태: 메인 결정 반영 계약. 구현·검증 기록이 아니다.**

메인 결정(Claude Opus 5.5 메인 리뷰; `3d3a..3d7c`·`478d0..478f0` capstone 재디코드로 BYTE push(`MOVE.B D0,-(A7)`: A7-2, 상위 BYTE만 씀)와 `478de` gate 근거 확인): 아래 MAIN DECISION NEEDED 1~12를 작업자 권고대로 모두 채택한다. 요점은 다음과 같다.
- F1c1(67 block, TRAP `478a6`, `479b0`에서 자름)·F1c2(153 block, TRAP `4d824`) 2단계이며 순서는 F1a→F1b→F1c1→F1c2.
- `478de` gate는 F1 결정 2와 같은 Waiting. `478a8` 표는 F1 결정 3의 계산 PC 정책. 두 TRAP은 stop 경계.
- 한 frame=한 실행, `2ac2` stop과 선언 재진입. 자식 완료 `62(A6)`는 선언 host 쓰기.
- 빈 group loop는 원본대로 block budget rollback. `3d58`/`3d6e`의 BYTE push/pop은 A7±2와 BYTE 하나만 쓴다(WORD `am_push` 금지).
- `49a58`의 A5 덮어쓰기는 원본대로, RNG 포인터가 RAM 밖이면 checked 오류. ROM 자료는 physical window만.
- 파일 `animation_machine_stage_catalog.cpp`(F1c1)·`animation_machine_stage_area.cpp`(F1c2). 오류 문자열은 단위 관례대로 `unsupported animation stage catalog PC`/`stage catalog caller requires known carry`, `unsupported animation stage area PC`/`stage area caller requires known carry`.
- 연쇄 seed는 137 begin 출력만 쓴다. 5 release(poisoned prefix) 출력은 WORD `104d8a`=`8001`로 U1 `3c60 CMP.W (A1),D0`가 홀수 주소 `fcd83`의 WORD를 읽어 실제 68000에서는 address error다(F1b core 확인; Unicorn은 이를 모델링하지 않음). 이 5건은 guard row로만 쓴다. 범위 근거는 `animation-machine-stage-controller-f1-contract.md`(이하 F1 계약)의 "F1c 개요"와 메인 결정 (2)~(7)이다. 구조는 F1a 계약과 U6·U7 계약을 따른다.

Claude Opus 5.5 / high 분석 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, fixed CPU 주소=file offset)을 capstone M68000으로 디코드했다. F1c의 모든 코드와 자료는 fixed `<100000`에 있으므로 CPU 주소와 file offset이 같다. 기존 실행부와 routing은 작업 트리 `/Users/start/Workspce/metalslug-input`(HEAD `543a3a4`, U1~U7과 F1a `animation_machine_stage_entry.cpp` 포함)의 `engine/src`를 읽기 전용으로 참조했다. 관측 산출물은 Unicorn 2.1.4로 읽기 전용 재생했다. [F]=원본 바이트, 기록 산출물 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. 명령 단위 정답은 원본 바이트 자체다. block 수는 scratch 스크립트(`f1c/c_lose.py`, `f1c/blk.py`, `f1c/fin.py`)가 원본 opcode에서 계산했다.

같은 루틴의 typed host 재구성(`engine/src/stage_entry.cpp`, `stage_transition.cpp`, `stage_area_initialization.cpp`, `stage_players.cpp`, `stage_preparation.cpp`, `stage_sound_initialization.cpp`, `stage_catalog.cpp` 등)과 그 검증 도구(`tools/verify_stage_initialization.py` 등)는 machine 실행부가 아니며 교차 확인 자료와 fixture 생성 방식의 출처로만 쓴다.

## 요약

- [F] F1c 정적 closure(현재 routing 28규칙에 이미 있는 PC와 F1b block에서 멈춤)는 **block 시작 220개 + TRAP 경계 2개(`478a6`, `4d824`)**다. 30개 코드 범위, 2,144바이트, 523명령, 짝수 PC 1,072개, 내부 PC 850개이며 미해독은 없다.
  - 220에는 `478a8` 표 slot 6개, dispatcher callback 진입 4개(`478de` `4790a` `4798e` `479b0`), node callback 진입 `477e4`, DBRA 대상 `4aa6e`가 들어 있다.
  - [F] F1 계약의 "215+표 slot 6"은 TRAP 2개를 block 수에 넣고, closure 스크립트가 `DBRA D7,4aa6e`의 대상을 읽지 못해 `4aa6e`를 빠뜨린 값이다. 정정: 215−2+6+1=220.
- [F] 기존 routing·F1a·F1b와 겹치는 PC는 없다. F1c가 부르는 `ca48`, `1c5b0..1c5ea`, `9056`은 F1b block이다(결정 2).
- [I] 진입 경로(dispatcher callback `479b0`)에서 자르면 의존 방향이 한쪽인 두 단위로 나뉜다. 작업자 권고는 아래 F1c1→F1c2 순서다(결정 1).

| 단위 | 진입→끝 | block 시작 | 경계 | 시작 상태 | 주 위험 |
| --- | --- | --- | --- | --- | --- |
| **F1c1** catalog·음악·진입 효과 | `477e4`/`477ee`, callback `478de` `4790a` `4798e`→`480bc`(callback `479b0` 설치) | 67(표 slot 6 포함) | TRAP `478a6` | F1b 연쇄 142, runtime fixture 236, transition 4 | `478a8` 계산 PC, `72f0` gate, 빈 group 무한 loop |
| **F1c2** area·player 초기화·음악 갱신 | callback `479b0`→`47a94`(F1a) | 153 | TRAP `4d824` | F1c1 출력(같은 seed 계열) | helper 팬아웃 24 범위, `49a58` A5 덮어쓰기, A7 BYTE push, RNG 포인터 |

- [F] 시작 상태: 자연 게임 흐름 관측은 없다. 대신 (1) F1a seed→F1b 연쇄 142건이 선언 host write 2종으로 `477ee`에 닿고, (2) typed host 검증 도구들과 같은 runtime fixture(원본 `2790`→`3ef2`→`49a1a` 실행 RAM)에 59개 catalog record를 넣은 236건이 모두 `47a94`까지 원본대로 간다(작업자 scratch 재생). 모두 host-write fixture이며 자연 IRQ·scheduler 주장은 하지 않는다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

### 1. F1c 분할

- 선택 A: F1c 전체(220+TRAP 2)를 한 실행부로 구현한다.
- 선택 B(**작업자 권고**): callback 진입 `479b0`에서 나눈다.
  - F1c1(67+`478a6`): `477e4..479b0`, `474e2`, `47540`, `3d58`/`3d6a`/`3d6e`, `ca8a`, `4814e`. 끝은 `480bc` 또는 `479b0` stop이다.
  - F1c2(153+`4d824`): `479b0..47a94`와 helper 전부. 진입은 F1c1 출력의 callback `479b0` 재진입이다.
  - [F] 두 집합은 서로소이고 합이 220이다. F1c1에서 F1c2로 가는 길은 `478ec`/`47918` BRA `479b0`과 `479a6` callback 설치뿐이다. F1c2에서 F1c1로 돌아오는 길은 없다.
  - [I] 이 경계는 기존 typed host 도구의 분할(`verify_stage_initialization`·`verify_stage_transition` 대 `verify_stage_preparation`·`verify_stage_area_initialization`·`verify_stage_players`·`verify_stage_sound_initialization`)과 같다. F1c1만 구현해도 모든 seed가 `479b0` stop까지 원본 비교된다.
- 선택 C: F1c2를 다시 area 초기화(`47594`/`475ca` closure 84)와 나머지(69)로 나눈다. [I] 비권고. 모든 catalog 경로가 `47594`나 `475ca`를 부르고 player 경로(`47782 JSR 1bd2e`)도 area 쪽 block을 공유하므로, 나머지 69만으로는 `47a94`까지 갈 수 없다.

### 2. F1b와의 순서 의존

- [F] F1c1 `47824`/`4782a`/`4783c`가 JSR하는 `ca48`, `1c5b0`(+`1c5bc` `1c5c0` `1c5cc` `1c5d8` `1c5dc` `1c5e8`), `9056`의 9개 block은 F1b 계약의 block 목록에 있다. F1c1의 모든 경로가 이 셋을 지난다.
- 권고: F1 순서(F1a→F1b→F1c)를 유지하고 F1c는 이 9개를 기존(F1b) 실행부 출구로 취급한다. F1c를 먼저 구현해야 한다면 이 9개를 F1c1로 옮기고 F1b가 그것을 참조해야 한다. 두 계약에 같은 block이 동시에 들어가면 안 된다.

### 3. `72f0` gate(`478de`/`478e4`)

- [F] `478d4 MOVE.L #478de,(A6)`; `BRA 480bc`이므로 gate는 항상 다음 dispatcher 재진입에서 처음 검사된다. `478de JSR 72f0`; `478e4 BCC 478de`는 F1a `47af0`/`47af6`과 같은 busy loop다.
- 권고: F1 메인 결정 2를 그대로 쓴다. `478e4`에서 C=Clear이면 PC=`478de`, `c.waiting=true`로 `AnimationMachineWaiting`을 돌려준다. 재개 조건, 멱등성, `107dea`≠0 유지는 F1a와 같다. Unknown carry는 checked 오류다.
- [F] scratch 재생에서 `478de` gate를 지난 158회(F1b 연쇄 142건, runtime fixture의 index `00` 경로 16건)는 모두 첫 검사에서 통과했다. BYTE `107ded`=`80`을 host write한 typed fixture에서는 Unicorn이 `478de`↔`478e4`를 끝없이 돈다.

### 4. `478a8` 계산 PC 표

- [F] `47896`: A0=LONG `76(A6)`, MOVEQ #0,D0, D0.B=BYTE `(A0)`(record +0). `4789e CMPI.W #18,D0`; `BCS 478a8`. 아니면 `478a6 TRAP #15`. `478a8 JMP 478ac(PC,D0.W)`. 4의 배수 검사는 없다.
- 권고: F1 메인 결정 3대로 PC=`478ac`+D0.W로 옮긴다. 결과는 index별로 다음과 같다.
  - `00`/`04`/`08`/`0c`/`10`/`14`: slot `478ac`~`478c0`(BRA.W)이며 실행한다.
  - `02`/`06`/`0a`/`0e`/`12`/`16`: BRA.W displacement WORD 위치(내부 PC)이므로 `unsupported` 오류와 전체 rollback이다.
  - 홀수: 기존 홀수 PC 오류다.
  - `18`~`ff`: `478a6` TRAP 경계다(결정 5).
- [F] catalog 59 record의 +0 값은 `00`(4개), `04`(10), `0c`(42), `14`(3)뿐이다. `08`(`478b4`→`4791c`)과 `10`(`478bc`→`4794c`)은 RAM record typed fixture로만 갈 수 있다.

### 5. TRAP 경계 `478a6`, `4d824`

- [F] `478a6`: record +0≥`18`. `4d824`: `4d81c`의 `CMPI.W #14,D1`·`BCS` 실패, 즉 D1.W≥`14`(무부호). F1c 경로의 `481de` 호출은 모두 D1=0(`475bc`/`475c4` MOVEQ)이므로 catalog 경로로는 닿지 않는다. 다른 호출자(`2b8e4` 등 fixed ROM 9곳)는 F1c 밖이다.
- 권고: F1 메인 결정 4를 따른다. 실행부 없는 경계로 두고, stop이 그 PC이면 직전 상태로 멈춘다. 아니면 `unsupported animation machine PC`로 rollback한다.

### 6. dispatcher 재진입과 자식 완료 선언

- 권고: F1 메인 결정 7(c)·F1b 결정 2와 같이 한 frame을 한 `run_animation_machine` 호출로 둔다. 각 frame은 `480f0 RTS`→`2ac2` stop으로 끝난다. 다음 frame은 A6=`100b30`, A5=`108000`, `(A7)`=`2ac2`, PC=LONG `(A6)`로 직접 진입한다. `477e4`도 같은 node callback이다. [F] `c654`/`c7ea`/`c862`/`c8fa`가 `LEA 477e4,A1`+`JSR 2a28`로 node `100b30`(`-74d0(A5)`)에 설치한다.
- [F] `4798e TST.B 62(A6)`; `BEQ 480bc`는 자식(`47934`/`4794c`/`47964`가 `28ae`로 만든 `4fcb8`/`4fd0a`/`4ff4c` callback 객체)의 완료 표시를 기다린다. 그 자식 코드는 F1c 밖이다(F2/F3).
- 권고: frame 사이 BYTE `62(A6)`≠0을 선언 host RAM write로 둔다(F1b `47e22`와 같은 방식). 자연 완료는 주장하지 않는다.

### 7. 무한 loop

- [F] 빈 group(stage `09`~`0f`): `47540`이 area 0에서도 null을 돌려준다. 그래서 `4781a CLR.B 7d(A6)`; `BRA 477fa`가 바뀌는 상태 없이 영원히 돈다. 기존 typed 검증(`artifacts/stage_initialization/verification.json` `empty_group_native_observations`)도 bounded 관측만 했다.
- [F] 그 밖의 loop는 모두 상한이 있다: `47544` 목록 walk(크기 0 WORD에서 끝남), `46f32` 8회, `4aa50` 16회, `4aa6e` 256회, `4790a` 17 frame, `4791c` 경로 61 frame.
- 권고: F1 메인 결정 7(d)대로 원본대로 두고 기존 block budget(1,000,000)만 한계로 둔다. budget 초과는 rollback이다.

### 8. A7 BYTE push/pop (`3d58`, `3d6e`)

- [F] `3d58 MOVE.B D0,-(A7)`과 `3d6e MOVE.B (A7)+,D0`는 M68000 규칙상 A7을 2만큼 옮긴다. push는 A7−2 위치(짝수 주소)에 BYTE 하나만 쓰고 A7−1은 건드리지 않는다.
- 권고: 기존 `am_push(c,2,…)`(WORD 쓰기)를 쓰지 않는다. A7−=2 후 BYTE 쓰기, pop은 BYTE 읽기 후 A7+=2로 구현한다. RAM 안 stack 전체 비교에서 A7+1 BYTE가 원본과 같아야 한다.

### 9. `49a58` RNG의 A5·포인터

- [F] `49a58 LEA 108000.L,A5`는 live A5를 상수로 덮어쓴다. 이후 `5722(A5)` 등과 F1c2의 나머지 d16(A5)는 새 A5를 쓴다.
- [F] RNG 고리는 `49a1a`가 초기화한다. WORD 55개(`10d6b4..10d722`)이고 포인터 LONG `10d722`의 초기값은 `10d720`이다. `49a58`은 포인터에서 WORD를 읽어 D0으로 돌려준다. 포인터를 2 진행하고 끝이면 −`6e`로 되돌린다. 그 뒤 +`2e`(같은 wrap) 위치 WORD에서 D0을 뺀다. [I] Knuth식 55/24 감산 생성기다.
- [F] `49a1a` 없이 `2790`/`3ef2`만 실행한 RAM(기존 `verify_stage_initialization`/`transition` fixture)에서는 포인터가 0이다. 그 상태에서 player 경로를 실행하면 Unicorn은 ROM `0`을 읽고 ROM `30`에 `SUB.W`를 쓴다(작업자 재생에서 확인).
- 권고:
  - A5 쓰기는 원본대로 구현하고 fixture는 A5=`108000`만 쓴다.
  - 포인터가 RAM 밖이면 쓰기 단계의 기존 checked 오류와 rollback으로 둔다. [U] 실제 하드웨어의 ROM 쓰기 결과는 미확인이다.
  - fixture 기반 RAM에는 반드시 `49a1a(D0=0)`을 포함한다(`verify_stage_players.py`와 같다).

### 10. ROM 자료 window

- 권고: F1 메인 결정 6과 같이 physical `program_rom_000000.ms5d` window로만 읽는다. [F] runtime fixture 236건(선언 재진입 포함 1,252 frame) 재생에서 F1c block 자신의 banked window 읽기는 0건이다. 읽는 fixed ROM은 아래 "입출력"에 정리했다.

### 11. 실행부 파일·오류 문자열(권고)

- F1c1: `engine/src/animation_machine_stage_catalog.cpp`의 `animation_stage_catalog_block`. 오류는 `unsupported animation stage catalog PC`, `stage catalog caller requires known carry`.
- F1c2: `engine/src/animation_machine_stage_area.cpp`의 `animation_stage_area_block`. 오류는 `unsupported animation stage area PC`, `stage area caller requires known carry`.
- 선택 A면 첫 파일 하나로 합친다.
- routing 규칙은 단위마다 하나씩 추가하고 TRAP PC는 `next.pc!=`로 제외한다(F1a `e909c` 방식).

### 12. 새 관측 도구

- [F] F1c PC를 지나는 기존 machine 관측 산출물은 transition 4 phase(아래)뿐이다.
- 권고: F1a observer(`tools/observe_animation_machine_stage_entry.py`, 주 작업 트리 미추적)의 Observer·선언 host change 어휘(RAM write / PC redirect / A7 delta)를 import로 재사용한다. 새 도구 `tools/observe_animation_machine_stage_catalog.py`가 아래 세 seed 계열을 split/continuous로 관측한다. stack은 RAM 안(F1b 연쇄와 같은 `10eff8`)에 둔다.

## F1c 원본 바이트 근거

[F] 코드 30 범위(F1c1 7개 564바이트, F1c2 24개 1,580바이트; `477e4..47a54`는 `479b0`에서 둘로 갈린다) 합계 2,144바이트이며 미해독은 0이다. 이어 붙인 SHA256은 F1c1 `40c8dfbe9abc0fad2f65abae38cabb7670caa53f125b079b9fdeb8d06d7d25ef`, F1c2 `29e15c153b9b84ec7a16597761d7a181d367fa51893e466d76f577c4e7a2efae`다.

**F1c1**

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `3d58..3d62` | `1f00103c000a6000000a` |
| `3d6a..3d7c` | `6100fd5c101f0600002055c180416000fd4e` |
| `ca8a..ca9e` | `303c7000343c00287620323c70004ef9000035a2` |
| `474e2..474f4` | `0c400013650000047000e548207b00044e75` |
| `47540..4755e` | `41e80002301866000008307c00004e755341640000044e7541f0000060e6` |
| `477e4..479b0` | `700020404eb90001a5a41d6d5680007c1d6d5681007d7000102e007c6100fce01b5056847200122e007d6100fd30b0fc000066000008422e007d60da2d4800764eb90000ca484eb90001c5b04eb90000ca7e4eb90004e24e4eb90000905608ad0000568308ad0004568308ad0002568308ad0001568308ad00055683206e007630280010322d5686b240670000200c4019c16600000a303c003860000006303c00804eb900003d584eba08c04eb90000ca9e206e0076700010100c400018650000044e4f4efb0002600000166000003e600000666000007a6000008e600000a270e172e174e1363c00004eb900008c162cbc000478de600007e04eb9000072f064f84eb90000ca8a600000c270e172e174e1363c00103d43007a4eb900008c162cbc0004790a536e007a640007ac4eb90000ca8a600000964eb90000caf03d7c003c007a701f721f741f363c001e60ca207c0004fcb8303c00004eb9000028ae6400ff7e6000003a207c0004fd0a303c00004eb9000028ae6400ff6660000022207c0004ff4c303c00004eb9000028ae6400ff4e316d56900076316d56920078422e00622cbc0004798e4a2e00626700072870e172e174e1363c00004eb900008c162cbc000479b06000070e` |
| `4814e..48156` | `3b7c0001568c4e75` |

**F1c2**

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `3d3a..3d44` | `6100ff48610000044e75` |
| `1bcfe..1bdde` | `41f900100cb86100002841f900100da86100001e426d547842ad547441f900100cb86100006e41f900100da8600000644eb90000289e650000044e75117c0000009e117c000000a0117c0000009f422800a149ed5450302800786700000649ed5460214c008c197c00010006197c000a0007197c00000004197c00000005397cffff000c197c00ff00034eba00fa426c00084eb90000289e650000044e7520bc0001d1f4422800154228006108e80007006108e8000400a8117c00000081117c00000082302800784eb90002efdc2868008c422c0002422c0001426c000a4e75` |
| `1be84..1be98` | `49ed5450024000016700000649ed546042144e75` |
| `2ef90..2efa6` | `70004eba004870014eba0042422d5490422d54914e75` |
| `2efdc..2eff4` | `43f90010d4804a406700000843f90010d488422900074e75` |
| `46f2e..46f52` | `41ed54e6317cffff0026317c0000002a4eb900043dda41e8002cb1fc0010d64665e24e75` |
| `47594..47642` | `303c07204eb900003af84eb900003d3a426d56864eb9000b7a204eb90004d1264eb90001bcfe700072004eba0c1e700172004eba0c16422d56824eb90001bd12207c000000004eb9000e89fa4eb900003d424eb900003dce4eb900049a8e4eb90004aa304eb9000b4a244eb90002ef904eb90006f1c24eb900046f2e4eb90004d13c4eb90004ddb6422d5c8c422d5c8d3b7c00a056903b7c01805692422d568e426d5688426d568a426d568c4e75` |
| `476dc..477a2` | `7000102e007c5d400c400003650000047000d040d04041faffdc207000007000102e007dd040d04043f00000321941f9001009a84eb90000289e6500000c2f09700061000022225f321941f900100a6c4eb90000289e6500000c2f09700161000006225f4e7541f900100cb84a406700000841f900100da84a416a00000c4eb900002a486000003e3f014eb90000289e6500001a3f0043f90001d1f44eb900002a28315f00784eb90001bd2e301f0c4000046500000c4eb900049a5802400003314000764e75` |
| `479b0..47a54` | `4eb9000e7c366100fe0a1b7c00ff5681103c0003c02d5684670000066100fd0e4a2e007d660000186100fbba4a2d5684660000084eb90004e6666000001270006100078e7001610007886100fbce4a2d5684660000084eb9000d760a70004eb900049c3270014eb900049c32206e007630280010322d56863b405686b2406700003a0c4010fe670000320c4019c16700002a0c4019c06700001c4eb900003af860000018` |
| `47a64..47a94` | `4eb900003d44303c18904eb900003af8303c18914eb900003af8303c18924eb900003af84eb900003c844eb900003d44` |
| `48180..481b2` | `41ed5694024000016700000641ed569c2f084eb90004d7a6205f108011410003114200023143000431450006114600014e75` |
| `481de..48210` | `41ed5694024000016700000641ed569c2f084eb90004d81c205f108011410003114200023143000431450006114600014e75` |
| `49a58..49a84` | `4bf90010800049ed57222654301bb7cc6500000696fc006e288bd6fc002eb7cc6500000696fc006e91534e75` |
| `49a8e..49ab0` | `426d5726426d5728426d572a42ad5734426d572c426d572e426d573042ad57384e75` |
| `4aa30..4aa86` | `1b7c00005b841b7c00005b851b7c00005b861b7c00005b877e0049f90010daf828872947000449ec0008b9fc0010db7865ee3e3c00ff41ed5b882b485c8810fc000051cffffa49ed57466100010c49ed591860000104` |
| `4d126..4d196` | `49f90010dcba6100002449f90010dce66100001a4e7549f90010dcba6100003849f90010dce66100002e4e75197c00000025197c00040026197c00000027397c0000001c397c0000001a397cffff0020197c0000002a38bc0000197c00000022397c00000006297c0000000000084e75` |
| `4d81c..4d84e` | `0c410014650000044e4f3001024100ffc2fc001041faf732d0c13228000c142800013628000a38033a28000e1c2800024e75` |
| `4ddb6..4ddde` | `41ed5d126100000641ed5d1810bc0001317cffff0004117c00000001117c00000002422800034e75` |
| `4e666..4e68e` | `41ed5d2a6100000641ed5d2b103c000010106b00001243fafe541031000001ad5d1e10bc00ff4e75` |
| `b4806..b481e` | `43ed5d5c45ed5d984eba002e43ed5d9845ed5dd44efa0022` |
| `b4a24..b4a2a` | `4ebafde04e75` |
| `b7a20..b7a28` | `4eba000c60000022` |
| `b7a2e..b7a62` | `426d5ddc422d5dde422d5ddf422d5de0422d5de1422d5de24e75426d5de4422d5de6422d5de7422d5de8422d5de9422d5dea4e75` |
| `d760a..d764a` | `41f90010ddec30bc0001317c01080002317c01a000045c4830bc0000317c01080002317c01a000043b7c00965df8207c000d764a303c00004eb9000028ae4e75` |

- [F] 제외한 인접 코드:
  - 죽은 코드 `47a54..47a64`(`70404eb900003d584eba06f060000008`, SHA256 `5a0b27bd…f242f171`)는 참조가 없다. `47a64`는 `47a46 BEQ`의 대상이라 살아 있다.
  - `3d44..3d58`은 exit 실행부(`3d44`/`3d48`/`3d4c`) 영역이다. `3d62 RTS`는 도달할 수 없고 `3d64`(별도 진입)는 F1c에서 부르지 않는다.
  - `49a84`(별도 진입)와 `b7a28`(`TST.B D0`; `BNE`)도 F1c에서 도달하지 않는다.
- [F] 겹침 확인: scratch `f1c/rng2.py`가 현재 routing 28규칙(F1a 포함)을 재현해 F1c의 짝수 PC 1,072개 모두 미배정임을 확인했다. F1b 범위(`47da4..47eac`, `1c5b0..1c5ea`, `ca48`, `9056`, `4b6e4`, `4b6ec`, `1bee4..`)와도 겹치지 않는다.
- [F] 인접 경계:
  - cleanup `477c2..477e2`, transition `477ac`/`477bc`/`35a2..35ee`, F1a `477a2..477ac`·`47a94..`, frame_helpers `47642..47670`·`46f52..`·`2efa6..2efda`·`b481e..b484e`·`b4a2a..`.
  - readiness `1bdde..1be3a`, input `1bec0..1bee4`·`4d7a6..4d81c`·`49ab4..`, buffer_cue `4aa88..`, exit `3d44`/`3c84`, screen `ca9e..`.

## F1c 실행 의미

[F] A5 상대 d16은 live A5로 계산한다(`49a58` 이후 A5=`108000`, 결정 9). 아래 절대 주소는 A5=`108000` 기준이다(`5680`→`10d680`, `-74d0`→`100b30`, `-7699`→`100967`, `-3285`→`104d7b`, `-328a`/`-328c`→`104d76`/`104d74`). 절대 LONG 주소를 쓰는 명령은 A5와 무관하다(`1009a8` `100a6c` `100cb8` `100da8` `10d480` `10d488` `10daf8` `10dcba` `10dce6` `10ddec` `108000` LEA/CMPA). 폭 규칙은 F1a와 같다.
- MOVE.B/MOVE.W Dn은 나머지 bit를 보존한다. MOVEQ, MOVEA.W(부호확장), ADDQ/SUBA to An(LONG)은 LONG 전체를 쓴다.
- index 주소 `(An,Dn.W)`와 ADDA.W는 부호확장한다.
- X 소비 명령은 없다. `3d74 SCS`는 같은 block `ADDI.B`의 C를 소비한다.

### F1c1

1. **진입.**
   - `477e4`: MOVEQ #0,D0; MOVEA.L D0,A0; JSR `1a5a4`(F1a, script null·목표 phase 0, 복귀 `477ee`).
   - `477ee`: BYTE `10d680`→`7c(A6)`, `10d681`→`7d(A6)`.
2. **group·record 선택.**
   - `477fa`: MOVEQ #0,D0; D0.B=`7c(A6)`; BSR `474e2`.
   - `474e2`: CMPI.W #13,D0; BCS `474ec`; `474ea` MOVEQ #0,D0. `474ec`: LSL.W #2,D0; A0=LONG `474f4+D0.W`; RTS.
   - `47804`: BYTE `(A0)`(group flags)→`10d684`; MOVEQ #0,D1; D1.B=`7d(A6)`; BSR `47540`.
   - `47540`: A0+=2.
   - `47544` 반복: D0.W=`(A0)+`. 0이면 `4754a`에서 A0=0(MOVEA.W)으로 RTS.
   - `47550`: SUBQ.W #1,D1. borrow면(D1이 0이었으면) `47556` RTS로 A0=record(크기 WORD 바로 뒤)다. 아니면 `47558` A0+=sext(D0.W), BRA `47544`.
   - `47812`: CMPA.W #0,A0(LONG 전체 비교); 0이 아니면 `47820`. `4781a`: CLR.B `7d(A6)`; BRA `477fa`(결정 7).
3. **정리.**
   - `47820`: LONG A0→`76(A6)`; JSR `ca48`(F1b, 복귀 `4782a`).
   - `4782a` JSR `1c5b0`(F1b) → `47830` JSR `ca7e`(exit) → `47836` JSR `4e24e`(exit) → `4783c` JSR `9056`(F1b) → `47842`.
   - `47842`: BCLR #0,#4,#2,#1,#5 BYTE `10d683`(이 순서).
4. **음악 비교.** `47842`에 이어: A0=`76(A6)`; D0.W=WORD `10(A0)`; D1.W=WORD `10d686`; CMP.W D0,D1; 같으면 `47890`.
   - `47872`: D0.W==`19c1`이면 `4787a` D0.W=`38`, BRA `47886`. 아니면 `47882` D0.W=`80`.
   - `47886` JSR `3d58`(복귀 `4788c`). `4788c` JSR `4814e`(복귀 `47890`). `4814e`: WORD 1→`10d68c`, RTS.
   - `3d58`: MOVE.B D0,-(A7)(결정 8); D0.B=`0a`; BRA `3d6a`. `3d6a`: BSR `3ac8`(sound, 복귀 `3d6e`).
   - `3d6e`: MOVE.B (A7)+,D0; ADDI.B #20,D0; SCS.B D1; OR.W D1,D0(D1 상위 BYTE 포함); BRA `3ac8`. 그 RTS가 `4788c`로 돌아간다.
5. **진입 효과 표.**
   - `47890`: JSR `ca9e`(screen, 복귀 `47896`).
   - `47896`: 결정 4의 `478a8` 표로 간다.
6. **표 대상.**
   - `478c4`(index `00`): D0=D1=D2=MOVEQ #`e1`(`ffffffe1`); D3.W=0; JSR `8c16`(복귀 `478d4`). `478d4`: LONG `478de`→`(A6)`; BRA `480bc`.
   - `478de`/`478e4`: gate(결정 3). `478e6`: JSR `ca8a`(복귀 `478ec`). `478ec`: BRA `479b0`.
   - `ca8a`: D0.W=`7000`, D2.W=`28`, D3=MOVEQ #`20`, D1.W=`7000`; JMP `35a2`(transition). 그 RTS가 `ca8a`의 호출 지점으로 돌아간다.
   - `478f0`(index `04`): D0..D2=`ffffffe1`; D3.W=`10`; WORD D3→`7a(A6)`. `478fe` JSR `8c16`(복귀 `47904`). `47904`: LONG `4790a`→`(A6)` 후 fall-through.
   - `4790a`(callback): SUBQ.W #1,`7a(A6)`; borrow가 없으면 `480bc`. `47912` JSR `ca8a`(복귀 `47918`); `47918` BRA `479b0`.
   - `4791c`(index `08`): JSR `caf0`(screen, 복귀 `47922`). `47922`: WORD `3c`→`7a(A6)`; D0..D2=MOVEQ #`1f`; D3.W=`1e`; BRA `478fe`. `478fa`의 `MOVE.W D3,7a(A6)`는 건너뛴다.
   - `47934`/`4794c`/`47964`(index `0c`/`10`/`14`): A0=`4fcb8`/`4fd0a`/`4ff4c`; D0.W=0; JSR `28ae`(fade_card, known C, 복귀 `47944`/`4795c`/`47974`). 다음 block에서 BCC `478c4`(C=0 실패면 index `00` 경로)다.
     - 성공(C=1): `47948`/`47960` BRA `47984`. `47978`: WORD `10d690`→`76(A0)`, `10d692`→`78(A0)`(A0=새 객체).
   - `47984`: CLR.B `62(A6)`; LONG `4798e`→`(A6)` 후 fall-through.
   - `4798e`(callback): TST.B `62(A6)`; 0이면 `480bc`(결정 6).
   - `47996`: D0..D2=`ffffffe1`; D3.W=0; JSR `8c16`(복귀 `479a6`). `479a6`: LONG `479b0`→`(A6)`; BRA `480bc`.

### F1c2

7. **area 시작(`479b0`).**
   - `479b0` JSR `e7c36`(palette_bind, 복귀 `479b6`). `479b6` BSR `477c2`(cleanup, 복귀 `479ba`).
   - `479ba`: BYTE `ff`→`10d681`; D0.B=3(MOVE.B, 상위 보존); AND.B `10d684`,D0. 0이 아니면 `479cc` BSR `476dc`.
   - `479d0`: TST.B `7d(A6)`; 0이 아니면 `479ee`.
     - 0이면 `479d8` BSR `47594`. `479dc`: TST.B `10d684`. 0이면 `479e4` JSR `4e666`. `479ea` BRA `479fe`.
     - `479ee`: MOVEQ #0,D0; BSR `48180` → `479f4` MOVEQ #1,D0; BSR `48180` → `479fa` BSR `475ca`.
   - `479fe`: TST.B `10d684`. 0이면 `47a06` JSR `d760a`.
   - `47a0c` MOVEQ #0,D0; JSR `49c32`(U6) → `47a14` MOVEQ #1,D0; JSR `49c32` → `47a1c`.
   - `47a1c`: A0=`76(A6)`; D0.W=WORD `10(A0)`; D1.W=WORD `10d686`; WORD D0→`10d686`(비교 전에 씀). D0==D1, `10fe`, `19c1`이면 `47a6a`. `19c0`이면 `47a64` JSR `3d44`(exit). 그 밖이면 `47a4a` JSR `3af8`(sound) 후 `47a50` BRA `47a6a`.
   - `47a6a`/`47a74`/`47a7e`: D0.W=`1890`/`1891`/`1892`; JSR `3af8`. `47a88` JSR `3c84`(exit). `47a8e` JSR `3d44`. 복귀 `47a94`는 F1a 진입 본문이다.
8. **player 배치(`476dc`, `10d684`&3≠0).**
   - `476dc`: MOVEQ #0,D0; D0.B=`7c(A6)`; SUBQ.W #6,D0; CMPI.W #3,D0; BCS `476ee`. `476ec` MOVEQ #0,D0.
   - `476ee`: D0.W×4; A0=LONG `476d0+D0.W`(표 `476bc`/`476c4`/`476cc`); MOVEQ #0,D0; D0.B=`7d(A6)`; ×4; A1=A0+D0.W.
   - 이어서 D1.W=`(A1)+`; A0=`1009a8`; JSR `289e`(복귀 `47716`).
   - `47716` BCS `47724`. `4771a`: push LONG A1; MOVEQ #0,D0; BSR `47742`. `47722`: pop A1.
   - `47724`: D1.W=`(A1)+`; A0=`100a6c`; JSR `289e`. `47732` BCS `47740`. `47736`: push A1; MOVEQ #1,D0; BSR `47742`. `4773e`: pop A1. `47740` RTS.
   - `47742`: A0=`100cb8`; D0.W≠0이면 `4774e` A0=`100da8`. `47754`: TST.W D1; 음수면 `4775a` JSR `2a48`(cleanup) 후 `47760` BRA `477a0` RTS.
   - `47764`: push WORD D1; JSR `289e`(복귀 `4776c`). `4776c`: BCS `47788`.
   - `47770`: push WORD D0; A1=`1d1f4`; JSR `2a28`(cleanup). `4777e`: pop WORD→`78(A0)`; JSR `1bd2e`.
   - `47788`: D0.W=pop WORD(=D1, 상위 보존); D0.W<4(무부호)이면 `4779c`. 아니면 `47792` JSR `49a58`, `47798` ANDI.W #3,D0.
   - `4779c`: WORD D0→`76(A0)`; RTS. [F] C=1 경로는 WORD 하나, C=0 경로는 둘을 push하고 같은 수만큼 pop한다.
9. **area 초기화(`47594`, 첫 area).**
   - `47594`: D0.W=`720`; JSR `3af8` → `4759e` JSR `3d3a` → `475a4` CLR.W `10d686`; JSR `b7a20` → `475ae` JSR `4d126` → `475b4` JSR `1bcfe`.
   - `475ba`: D0=0, D1=0, JSR `481de` → `475c2`: D0=1, D1=0, JSR `481de`. 이어서 `475ca`로 fall-through한다.
   - `475ca`(다른 area의 진입점이기도 함): CLR.B `10d682`; JSR `1bd12` → `475d4` A0=0; JSR `e89fa`(U5) → `475e0` JSR `3d42`(RTS뿐) → `475e6` JSR `3dce`(cleanup).
   - 이어지는 호출: `475ec` `49a8e` → `475f2` `4aa30` → `475f8` `b4a24` → `475fe` `2ef90` → `47604` `6f1c2`(U1, RTS뿐) → `4760a` `46f2e` → `47610` `4d13c` → `47616` `4ddb6`.
   - `4761c`: CLR.B `10dc8c`, `10dc8d`; WORD `a0`→`10d690`, `180`→`10d692`; CLR.B `10d68e`; CLR.W `10d688`, `10d68a`, `10d68c`; RTS.
10. **helper(쓰기 순서는 원본 바이트 순서 그대로).**
    - `3d3a`: BSR `3c84` → `3d3e` BSR `3d44` → `3d42` RTS.
    - `b7a20`: JSR `b7a2e`(PC) → `b7a24` BRA `b7a48`.
      - `b7a2e`: CLR.W `10dddc`; CLR.B `10ddde`..`10dde2`; RTS.
      - `b7a48`: CLR.W `10dde4`; CLR.B `10dde6`..`10ddea`; RTS.
    - `4d126`/`4d13c`: A4=`10dcba`, BSR `4d152`/`4d17c`; A4=`10dce6`, 같은 BSR; RTS.
      - `4d152`: BYTE `25`=0, `26`=4, `27`=0; WORD `1c`=0, `1a`=0, `20`=`ffff`; BYTE `2a`=0. 이어서 `4d17c`로 fall-through한다.
      - `4d17c`: WORD `(A4)`=0; BYTE `22`=0; WORD `6`=0; LONG `8`=0; RTS.
    - `1bcfe`: A0=`100cb8` BSR `1bd2e` → `1bd08` A0=`100da8` BSR `1bd2e` → `1bd12`.
      - `1bd12`: CLR.W `10d478`; CLR.L `10d474`; A0=`100cb8` BSR `1bd90` → `1bd24` A0=`100da8` BRA `1bd90`.
    - `1bd2e` JSR `289e` → `1bd34` BCS `1bd3a`, 아니면 `1bd38` RTS.
      - `1bd3a`: BYTE 0→`9e`/`a0`/`9f(A0)`; CLR.B `a1(A0)`; A4=`10d450`; D0.W=WORD `78(A0)`. 0이 아니면 `1bd5c` A4=`10d460`.
      - `1bd60`: LONG A4→`8c(A0)`; BYTE `6(A4)`=1, `7`=`a`, `4`=0, `5`=0; WORD `c(A4)`=`ffff`; BYTE `3(A4)`=`ff`; JSR `1be84`(PC).
      - `1be84`: A4=`10d450`; ANDI.W #1,D0. 0이 아니면 `1be90` A4=`10d460`. `1be94`: CLR.B `(A4)`; RTS. 따라서 이후 A4는 D0&1로 다시 정해진다.
      - `1bd8c`: CLR.W `8(A4)` 후 fall-through.
    - `1bd90` JSR `289e` → `1bd96` BCS `1bd9c`, 아니면 `1bd9a` RTS.
      - `1bd9c`: LONG `1d1f4`→`(A0)`; CLR.B `15`, `61(A0)`; BSET #7,`61(A0)`; BSET #4,`a8(A0)`; BYTE 0→`81`/`82(A0)`; D0.W=`78(A0)`; JSR `2efdc`.
      - `1bdcc`: A4=LONG `8c(A0)`; CLR.B `2(A4)`, `1(A4)`; CLR.W `a(A4)`; RTS.
    - `2ef90`: D0=0 JSR `2efdc` → `2ef96` D0=1 JSR `2efdc` → `2ef9c` CLR.B `10d490`, `10d491`; RTS.
      - `2efdc`: A1=`10d480`. D0.W≠0이면 `2efe8` A1=`10d488`. `2efee` CLR.B `7(A1)`; RTS.
    - `46f2e`: A0=`10d4e6`.
      - `46f32` 반복: WORD `ffff`→`26(A0)`, 0→`2a(A0)`; JSR `43dda`(cleanup).
      - `46f44`: A0+=`2c`; A0<`10d646`(CMPA.L, 무부호)이면 반복한다. 8회 뒤 `46f50` RTS.
    - `481de`/`48180`:
      - A0=`10d694`; D0&=1(ANDI.W). 0이 아니면 A0=`10d69c`.
      - push A0; JSR `4d81c`/`4d7a6`(U6).
      - pop A0; BYTE D0→`(A0)`, D1.B→`3`, D2.B→`2`; WORD D3→`4`, D5→`6`; BYTE D6→`1`; RTS.
    - `4d81c`: D1.W≥`14`이면 TRAP(결정 5).
      - `4d826`: D0.W=D1.W; D1&=`ff`; MULU.W #10,D1(LONG 결과); A0=`4cf64`+sext(D1.W).
      - 이어서 D1.W=WORD `c(A0)`, D2.B=`1(A0)`, D3.W=`a(A0)`, D4.W=D3.W, D5.W=`e(A0)`, D6.B=`2(A0)`; RTS.
    - `49a58`: 결정 9. `49a70`·`49a80`이 두 wrap 지점이다(CMPA.L A4,A3; BCS).
    - `49a8e`: CLR.W `10d726`, `728`, `72a`; CLR.L `10d734`; CLR.W `10d72c`, `72e`, `730`; CLR.L `10d738`; RTS.
    - `4aa30`:
      - BYTE 0→`10db84`..`10db87`; D7=0; A4=`10daf8`.
      - `4aa50` 반복: LONG D7→`(A4)`, `4(A4)`; A4+=8; A4<`10db78`이면 반복한다(16회).
      - `4aa62`: D7.W=`ff`; A0=`10db88`; LONG A0→`10dc88`.
      - `4aa6e`: BYTE 0→`(A0)+`; DBRA D7(256회, 끝 D7.W=`ffff`).
      - `4aa76`: A4=`10d746` BSR `4ab88`(U7) → `4aa7e` A4=`10d918` BRA `4ab88`.
    - `b4a24`: JSR `b4806` → `b4a28` RTS.
      - `b4806`: A1=`10dd5c`, A2=`10dd98` JSR `b483e`(U1) → `b4812` A1=`10dd98`, A2=`10ddd4` JMP `b483e`.
    - `4ddb6`: A0=`10dd12` BSR `4ddc2` → `4ddbe` A0=`10dd18` 후 fall-through.
      - `4ddc2`: BYTE 1→`(A0)`; WORD `ffff`→`4(A0)`; BYTE 0→`1`, `2`; CLR.B `3(A0)`; RTS.
    - `4e666`: A0=`10dd2a` BSR `4e672` → `4e66e` A0=`10dd2b` 후 fall-through.
      - `4e672`: MOVE.B #0,D0(하위 BYTE만); D0.B=`(A0)`. 음수면 `4e68c` RTS.
      - `4e67c`: D0.B=BYTE `4e4d2+sext(D0.W)`. [F] D0.W 상위 BYTE는 호출자의 값이 남는다. BCLR D0,`10dd1e`(bit mod 8); BYTE `ff`→`(A0)`; RTS.
    - `d760a`:
      - A0=`10ddec`; WORD 1→`(A0)`, `108`→`2`, `1a0`→`4`; ADDQ.W #6,A0.
      - WORD 0→`(A0)`, `108`→`2`, `1a0`→`4`; WORD `96`→`10ddf8`.
      - A0=`d764a`; D0.W=0; JSR `28ae`. `d7648` RTS(C는 소비되지 않는다).

[F] F1c block 자신의 port 쓰기는 없다(runtime fixture 236건 재생에서 F1c 명령의 `>=200000` 쓰기 0건). 관측된 `3c0000`/`3c0004`(video), `300001`(watchdog), `2ffff0`/`2ffff2`(PVC, `477e4`→`1a5a4`)는 모두 기존 callee 실행부가 낸다.

## 구현 범위와 규약

- **routing 범위(끝 미포함)**
  - F1c1 7개: `3d58..3d62`, `3d6a..3d7c`, `ca8a..ca9e`, `474e2..474f4`, `47540..4755e`, `477e4..479b0`(`478a6` 제외), `4814e..48156`. 짝수 PC 282개이고, block 67과 TRAP 1을 빼면 내부 PC는 214개다.
  - F1c2 24개: `3d3a..3d44`, `1bcfe..1bdde`, `1be84..1be98`, `2ef90..2efa6`, `2efdc..2eff4`, `46f2e..46f52`, `47594..47642`, `476dc..477a2`, `479b0..47a54`, `47a64..47a94`, `48180..481b2`, `481de..48210`, `49a58..49a84`, `49a8e..49ab0`, `4aa30..4aa86`, `4d126..4d196`, `4d81c..4d84e`(`4d824` 제외), `4ddb6..4ddde`, `4e666..4e68e`, `b4806..b481e`, `b4a24..b4a2a`, `b7a20..b7a28`, `b7a2e..b7a62`, `d760a..d764a`. 짝수 PC 790개이고, block 153과 TRAP 1을 빼면 내부 PC는 636개다.
- **Block 시작 PC.** 루틴 진입, 분기 대상, 조건분기 fall-through, 호출 복귀, 호출 진입, 표 slot, `MOVE.L #imm,(A6)`로 설치되는 callback 진입, DBRA 대상이다.
  - F1c1(67): `3d58` `3d6a` `3d6e` `ca8a` `474e2` `474ea` `474ec` `47540` `47544` `4754a` `47550` `47556` `47558` `477e4` `477ee` `477fa` `47804` `47812` `4781a` `47820` `4782a` `47830` `47836` `4783c` `47842` `47872` `47882` `4787a` `47886` `4788c` `47890` `47896` `478a8` `478ac` `478b0` `478b4` `478b8` `478bc` `478c0` `478c4` `478d4` `478de` `478e4` `478e6` `478ec` `478f0` `478fe` `47904` `4790a` `47912` `47918` `4791c` `47922` `47934` `47944` `47948` `4794c` `4795c` `47960` `47964` `47974` `47978` `47984` `4798e` `47996` `479a6` `4814e`
  - F1c2(153): `3d3a` `3d3e` `3d42` `1bcfe` `1bd08` `1bd12` `1bd24` `1bd2e` `1bd34` `1bd38` `1bd3a` `1bd5c` `1bd60` `1bd8c` `1bd90` `1bd96` `1bd9a` `1bd9c` `1bdcc` `1be84` `1be90` `1be94` `2ef90` `2ef96` `2ef9c` `2efdc` `2efe8` `2efee` `46f2e` `46f32` `46f44` `46f50` `47594` `4759e` `475a4` `475ae` `475b4` `475ba` `475c2` `475ca` `475d4` `475e0` `475e6` `475ec` `475f2` `475f8` `475fe` `47604` `4760a` `47610` `47616` `4761c` `476dc` `476ec` `476ee` `47716` `4771a` `47722` `47724` `47732` `47736` `4773e` `47740` `47742` `4774e` `47754` `4775a` `47760` `47764` `4776c` `47770` `4777e` `47788` `47792` `47798` `4779c` `477a0` `479b0` `479b6` `479ba` `479cc` `479d0` `479d8` `479dc` `479e4` `479ea` `479ee` `479f4` `479fa` `479fe` `47a06` `47a0c` `47a14` `47a1c` `47a32` `47a3a` `47a42` `47a4a` `47a50` `47a64` `47a6a` `47a74` `47a7e` `47a88` `47a8e` `48180` `4818c` `48190` `48198` `481de` `481ea` `481ee` `481f6` `49a58` `49a6c` `49a70` `49a7c` `49a80` `49a8e` `4aa30` `4aa50` `4aa62` `4aa6e` `4aa76` `4aa7e` `4d126` `4d130` `4d13a` `4d13c` `4d146` `4d150` `4d152` `4d17c` `4d81c` `4d826` `4ddb6` `4ddbe` `4ddc2` `4e666` `4e66e` `4e672` `4e67c` `4e68c` `b4806` `b4812` `b4a24` `b4a28` `b7a20` `b7a24` `b7a2e` `b7a48` `d760a` `d7648`
- **묶인 조건분기 PC(직접 진입 거부).** [F] 모두 같은 block의 Z/N/C 생산자(CMP/CMPI/CMPA/TST/MOVE/AND/ANDI/SUBQ) 뒤에 온다. 이전 block의 Z나 N을 소비하는 block 시작은 없다.
  - F1c1(9): `474e6` `47546` `47552` `47816` `4786e` `47876` `478a2` `4790e` `47992`
  - F1c2(23+DBRA 1): `1bd58` `1be8c` `2efe4` `46f4e` `476e8` `4774a` `47756` `4778e` `479c8` `479d4` `479e0` `47a02` `47a2e` `47a36` `47a3e` `47a46` `48188` `481e6` `49a68` `49a78` `4aa60` `4d820` `4e678`, DBRA `4aa72`
- **Carry 소비 block(9개, 모두 callee 복귀 PC이며 block 첫 명령이 Bcc).** 진입 C가 Unknown이면 checked 오류와 전체 rollback이다.
  - F1c1: `478e4`(`72f0`, C=Clear는 결정 3), `47944`·`4795c`·`47974`(`28ae`; C=0 실패→`478c4`).
  - F1c2: `47716`·`47732`·`4776c`·`1bd34`·`1bd96`(`289e`; LONG `(A0)`≠`270e`이면 C=1).
- **Known carry 생산 block.** F1c 안에는 없다. 생산자는 모두 기존 실행부다(F1a `72f0`, fade_card `28ae`, readiness `289e`). `47556 RTS`의 borrow C와 `d7648`의 `28ae` C는 소비자가 없다.
- **Carry 보존(FLOW_ONLY) block.** 기준은 U2·F1a와 같다. 전 명령이 LEA/MOVEA/JSR/JMP/BSR/BRA/RTS/BTST/BSET/BCLR/Bcc인 block만 넣는다.
  - F1c1(32): `3d6a` `47540` `4754a` `47556` `47558` `4782a` `47830` `47836` `4783c` `47886` `4788c` `47890` `478a8` `478ac` `478b0` `478b4` `478b8` `478bc` `478c0` `478de` `478e4` `478e6` `478ec` `478fe` `47912` `47918` `4791c` `47944` `47948` `4795c` `47960` `47974`
  - F1c2(77): `3d3a` `3d3e` `3d42` `1bcfe` `1bd08` `1bd24` `1bd2e` `1bd34` `1bd38` `1bd5c` `1bd90` `1bd96` `1bd9a` `1be90` `2efe8` `46f2e` `46f50` `4759e` `475ae` `475b4` `475d4` `475e0` `475e6` `475ec` `475f2` `475f8` `475fe` `47604` `4760a` `47610` `47616` `47716` `47722` `47732` `4773e` `47740` `4774e` `4775a` `47760` `4776c` `47792` `477a0` `479b0` `479b6` `479cc` `479d8` `479e4` `479ea` `479fa` `47a06` `47a4a` `47a50` `47a64` `47a88` `47a8e` `4818c` `481ea` `4aa76` `4aa7e` `4d126` `4d130` `4d13a` `4d13c` `4d146` `4d150` `4ddb6` `4ddbe` `4e666` `4e66e` `4e68c` `b4806` `b4812` `b4a24` `b4a28` `b7a20` `b7a24` `d7648`
  - [I] 정확성에 필요한 것은 소비 block 9개뿐이다. 나머지는 규약상 목록이다.
- **경계(실행부 없음):** TRAP `478a6`, `4d824`(결정 5).
- **기존 실행부로 나가는 지점.** 모두 해당 실행부의 block 시작임을 `engine/src`의 `case`에서 확인했다.

| 대상 | 실행부 | 나가는 곳 → 복귀 |
| --- | --- | --- |
| `1a5a4` | F1a | `477e8`→`477ee` |
| `ca48` / `1c5b0` / `9056` | F1b | →`4782a` / →`47830` / →`47842` |
| `ca7e` / `4e24e` | exit | →`47836` / →`4783c` |
| `3ac8` | sound | `3d6a`→`3d6e`, `3d78` BRA(꼬리) |
| `ca9e` | screen | →`47896` |
| `caf0` | screen | →`47922` |
| `8c16` | exit | →`478d4` / `47904` / `479a6` |
| `480bc` | U1 | `478da` / `4790e` / `47992` / `479ac` |
| `72f0` | F1a | →`478e4` |
| `35a2` | transition | `ca98` JMP(꼬리, →`478ec`/`47918`) |
| `28ae` | fade_card | →`47944` / `4795c` / `47974` / `d7648` |
| `e7c36` | palette_bind | →`479b6` |
| `477c2` / `2a48` / `2a28` / `3dce` / `43dda` | cleanup | →`479ba` / `47760` / `4777e` / `475ec` / `46f44` |
| `289e` | readiness | →`47716` / `47732` / `4776c` / `1bd34` / `1bd96` |
| `3af8` | sound | →`4759e` / `47a50` / `47a74` / `47a7e` / `47a88` |
| `3c84` / `3d44` | exit | →`3d3e`, `47a8e` / →`3d42`, `47a6a`, `47a94` |
| `e89fa` | U5 | →`475e0` |
| `6f1c2` / `b483e` | U1 | →`4760a` / →`b4812`, `b481a` JMP |
| `4ab88` | U7 | →`4aa7e`, `4aa82` BRA |
| `4d7a6` / `49c32` | U6 | →`48198` / →`47a14`, `47a1c` |
| `47a94` | F1a | `47a8e` 복귀 |

- **폭·연산**
  - BSET/BCLR 메모리 bit 번호는 mod 8이다(`4e684 BCLR D0` 포함). `SUBQ.W #1,7a(A6)`와 `SUBQ.W #1,D1`의 C는 borrow다.
  - `CMPI.W`+`BCS`, `CMPA.L`+`BCS`는 무부호 비교다. `TST.W D1`+`BPL`은 bit15로 판정한다.
  - `MULU.W #10,D1`은 LONG을 쓴다. `ADDQ.W #6,A0`는 LONG을 더한다. `SUBA.W #6e`/`ADDA.W #2e`/`ADDA.W D1`은 부호확장한다.
  - live stack:
    - push/pop LONG: `4771a`/`47722`, `47736`/`4773e`, `48190`/`48198`, `481ee`/`481f6`.
    - push/pop WORD: `47764`·`47770`/`4777e`·`47788`. `4777e`는 메모리로 pop한다.
    - BYTE: `3d58`/`3d6e`(결정 8).
  - 홀수 주소 WORD/LONG 접근은 기존 checked 오류와 rollback이다(record +`10`, `76(A6)`, A0/A1/A4/A7 포함). BYTE 접근은 홀수도 허용한다.
- **루프:** 결정 7과 같다.
- **기존 회귀 탐침 갱신.** [F] 아래 PC가 지금 `unsupported animation machine PC` 탐침으로 쓰인다. 구현 뒤 block 시작은 실행되고, 내부 PC는 새 실행부의 오류 문자열을 낸다. 그대로 미연결로 남는 PC(예: 죽은 코드 `47a54`, `3d64`, `49a84`, `b7a28`, `4755e`)로 옮긴다.
  - `engine/tests/animation_machine_frame_helpers_test.cpp:297-298`의 `outside[]`:
    - block 시작: `2efdc` `b4a28` `46f50`.
    - 내부 PC: `47640` `2efa4` `b481c`.
  - `engine/tests/animation_machine_input_test.cpp:887`의 `outside[]`: `4d81c` `49a8e`(둘 다 block 시작).
  - `engine/tests/animation_machine_motion_walk_test.cpp:773`의 `outside[]`: `477ee`(block 시작), `47800`(내부). F1b 계약도 같은 줄을 F1c PC로 옮기라고 권고하므로 F1b 쪽 대체값과 충돌하지 않게 조정해야 한다.
  - `engine/tests/animation_machine_stage_entry_test.cpp:719`의 `outside[]`: `477a0`(block 시작), `47a92`(내부).
  - `animation_machine_transition_test.cpp:41/71`의 `477ee`는 stop·점프 대상 검사이므로 그대로 유효하다.

## 입출력

- **A6 node 필드(stage controller node, 자연 A6=`100b30`):**
  - LONG `(A6)` callback: `478de`/`4790a`/`4798e`/`479b0`.
  - LONG `76`: record. WORD `7a`: frame 수. BYTE `62`: 자식 완료. BYTE `7c`/`7d`: stage/area 사본.
- **RAM(A5=`108000`).**
  - `10d680` BYTE stage(읽음), `10d681` BYTE area(읽음; `479ba`에서 `ff`).
  - `10d682` CLR, `10d683` bit 0/1/2/4/5 해제, `10d684` BYTE group flags(`47804`가 씀; `479c4`/`479dc`/`479fe`가 읽음).
  - `10d686` WORD 현재 음악: `47868` 읽음, `475a4` CLR, `47a28` 씀.
  - `10d688`/`10d68a`/`10d68c`(`4814e`=1, `4763c` CLR), `10d68e`, `10d690`/`10d692`(`47978` 읽음, `47624`/`4762a` 씀).
  - `10d474..10d479`, `10d450`/`10d460` player 보조 block, `10d480`/`10d488` `+7`, `10d490`/`10d491`.
  - `10d4e6..10d646` 8 node×`2c`, `10d694..10d6a3`, RNG `10d6b4..10d725`, `10d726..10d73b`(`10d734`/`10d738` LONG 포함).
  - `10d746`/`10d918`(U7 인자), `10daf8..10db77`, `10db84..10dc8b`(`10dc88` LONG), `10dc8c`/`10dc8d`.
  - `10dcba`/`10dce6` block, `10dd12`/`10dd18`, `10dd1e`(bit), `10dd2a`/`10dd2b`, `10dd5c..10ddd3`(U1 `b483e`).
  - `10dddc..10ddea`, `10ddec..10ddf7`, `10ddf8`.
- **객체 필드.**
  - player node `100cb8`/`100da8`:
    - LONG `(A0)`=`1d1f4`. WORD `76`(종류: 표 값 또는 RNG&3), WORD `78`(player 0/1).
    - LONG `8c`(A4). BYTE `9e` `9f` `a0` `a1` `15` `61`(bit7) `a8`(bit4) `81` `82`.
  - 검사만 하는 node: `1009a8`, `100a6c`.
  - 새 자식 객체(`47978`): WORD `76`/`78`.
- **음악·sound 호출.**
  - `3d58`: sound BYTE `0a` 다음에 (D0+`20`), 즉 `58`(음악 `19c1`) 또는 `a0`이다. 둘 다 `3ac8` ring이다.
  - `4814e`: `10d68c`=1.
  - `3af8`: `720`(`47594`), 새 음악 WORD(`47a4a`), `1890`/`1891`/`1892`.
  - `3d3a`=`3c84`+`3d44`, `47a64`/`47a8e` `3d44`, `47a88` `3c84`.
  - [F] 모든 `3ac8`/`3af8` 호출은 U1 `3aea` ring-full 대기(Waiting)가 날 수 있다. 재개는 U1 규약(선언 head release)이다.
- **ROM 자료 window(모두 fixed, physical window로 읽음).**
  - `474f4..47540`: stage group 표 LONG 19개, SHA256 `f404ca58a5bb5d1a3a19b7bd571847076bf72225c2d97a6d6f794124d9765b94`. `474e2`가 index<`13`으로 제한한다.
  - group 자료:
    - group 0~4: `d99e2..dd4be` 영역. group 5~18: `472be..474e0`.
    - group +0 BYTE flags, +2부터 (WORD 크기, record) 목록이고 크기 0 WORD에서 끝난다.
    - [F] record 수는 group별 11/6/14/5/9/3/3/3/2/0×7/1/1/1, 합 59다. 0인 7개가 group 9~15이며 결정 7의 빈 group이다.
    - F1c가 읽는 record 필드는 +0 BYTE(진입 효과 index)와 +`10` WORD(음악)다. F1a는 +1, +2, +6, +`a`, +`e`를 읽는다.
    - group flags: group 5=`04`, 6=`01`, 7=`01`, 8=`02`, 그 밖은 `00`이다.
  - `476bc..476dc`(SHA256 `d23c1271c0306bf466f4f017a15076076c76ee8f11e31821a626eace146ad7b7`): WORD 쌍 표와 그 뒤 LONG 포인터 3개(`476d0`=`476bc`, `476c4`, `476cc`)다.
    - [F] stage 8 area 1은 `476d0`을 읽어 D1=`0004`, `76bc`가 된다. 즉 포인터 표 바이트를 player 값으로 읽는다(재생에서 `47724`가 `476d2`를 읽음 확인).
  - `4cf64..4d0a4`(SHA256 `9b1c4db78844053dff88ac7c863b15852c1ad1b9e500a831ed5a01fa9eff923c`): 16바이트 record `14`개(`4d81c`).
  - `4e4d2..4e552`(SHA256 `aab36d4692c572b94b43fb395e58d13c8b39e8ed0448a91b8a06e52a919cbf86`): 128바이트 lookup(`4e67c`).
  - 상수 포인터(읽지 않음): `4fcb8`/`4fd0a`/`4ff4c`/`d764a`(`28ae` 자식 callback), `1d1f4`(player callback).
- **MMIO:** F1c block 자신은 없다(위 실행 의미 끝 참고).

## 시작 상태(읽기 전용 재생)

[F] scratch `f1c/rep*.py`·`chainc.py`가 Unicorn에 읽기 hook만 더해 F1c block 경로를 기록했다. 원본 프로그램은 바꾸지 않았다. 입력 산출물 SHA256은 `artifacts/stage_entry_body/observation.json` `1f65100f1fedc36b4999543c720814dc6f9eb4bf634f3af3439aa68d70e31207`, `artifacts/animation_machine_transition_native/observation.json` `edf1f5e7248601d2a708cbc7ebfb8a89c62bfdb5dcef018cb94a2c5fa26aaba4`다.

**1. F1b 연쇄 142건(F1c1·F1c2 통합 seed, F1b 구현 필요)**
- [F] 조건:
  - stage_entry_body begin(또는 release-poisoned-prefix) 출력 중 `ff000`으로 끝난 142건을 쓴다.
  - `47da4` 직접 진입, A6=`100b30`, A7=`10eff4`(`(A7)`=`2ac2`)로 시작한다.
  - frame마다 선언 재진입을 하고, 선언 host write는 `47e22`에서 `62(A6)`=1, `47e70`에서 `10dd44`=`ff`다.
  - 이 방식은 F1b scratch `f1b/replay_b.py`와 같다. [U] F1b 계약 본문은 137건이라고 적었다. 같은 선택 규칙의 재생 로그는 142행이므로 메인 확인이 필요하다.
  - 모두 237 frame에서 `477ee`에 닿았다. 상태는 `10d680`=1, `10d681`=0, `10d684`=0, `10d686`=0, `107ded`=0이다.
- [F] F1c 결과(142건 동일 경로, 2 frame):
  - frame 1: record `dcd18`(+0=`00`, 음악 `19c0`). 음악≠0이라 `3d58`(D0=`80`)를 지나 `478c4`→`8c16`→`480bc`로 끝난다.
  - frame 2: `478de` gate 통과, `ca8a`, `479b0`. 7d=0이라 `47594`, `10d684`=0이라 `4e666`과 `d760a`를 지난다. `47a1c`에서 `10d686`이 0(`475a4` CLR)과 `19c0`이므로 `47a64` `3d44`를 거쳐 `47a94` stop.
  - 방문 block 139개, 선언 host write 없음. [I] 이것이 F1a→F1b→F1c→F1a로 이어지는 첫 연쇄 검증이다.

**2. runtime fixture 236건(typed host 검증 도구와 같은 기반)**
- [F] 조건:
  - 0 RAM에서 원본 `2790`→`3ef2`→`49a1a`(D0=0)를 실행한다.
  - host write: `10d680`=group, `10d681`=area, `10d683`=`ff`, `10d686`=record 음악(같음) 또는 그 보수(다름), `104d74`=`104d76`=0.
  - 레지스터는 A5=`108000`, A6=`100b30`, A7=`1feffc`(복귀 `ff000`)이다.
  - 진입은 `477ee`와 `477e4`이다. 대상은 59 record×음악 2×진입 2다.
  - frame 사이 선언 재진입과 `4798e`의 `62(A6)`=`ff`를 쓴다.
- [F] 결과: 236건 모두 `47a94`에 닿았다. 선언 재진입 수는 index `0c`/`14`가 3 segment(180건), `04`가 17 segment(40건, `4790a` 16회), `00`이 2 segment(16건)다. `3aea` 대기와 ROM 쓰기는 0건이다.
- [F] 방문 block 208/220이다(`4aa6e`는 실행되나 hook 집합 밖). 미방문 12개는 `474ea` `4754a` `4781a` `476ec` `478b4` `478bc` `4791c` `47922` `4794c` `4795c` `47960` `49a7c`다.
- [F] 한쪽만 나온 조건분기는 다음과 같다(typed fixture로 보완).
  - `474e2`(stage<`13`만), `47544`(크기≠0만), `47812`(비null만), `476dc`(7c−6<3만).
  - `47716`/`47732`/`4776c`(C=0만), `47896`(<`18`만), `478e4`(통과만), `47944`/`47974`(성공만).
  - `47a32`(`10fe` 없음), `49a70`(두 번째 wrap 없음), `4d81c`(<`14`만), `4e672`(BMI 없음).
  - `1bd34`·`1bd96`은 양쪽이 모두 나왔다.
- [F] typed 변형 재생 결과:
  - stage=`21`이면 `474ea`. area=`7f`이면 `4754a`→`4781a` 재시도. WORD `104ca0`=0이면 `28ae` 실패로 `47944`→`478c4`. 모두 `47a94`에 닿는다.
  - BYTE `107ded`=`80`이면 `478de`에서 끝없이 돈다.
- [F] `49a1a`를 빼면 RNG 포인터 0 때문에 Unicorn이 ROM `30`에 쓴다(결정 9). 기존 `verify_stage_initialization.py`/`verify_stage_transition.py` fixture는 `49a1a`를 부르지 않는다. 그래서 F1c2에는 `verify_stage_players.py`처럼 `49a1a`를 포함한 기반을 써야 한다.

**3. transition native 4 phase(F1c1 앞부분 seed)**
- [F] case 66~69(`signed-00/7f-fill0/1`)는 `47d46` 진입 후 `477ee` stop으로 끝났다.
  - 레지스터는 A6=`102000`이고, RAM은 fill 패턴이다(`10d680`=`21`, `10d681`=0/`7f`, `10d686`=0, 객체 pool `104c9c`가 garbage).
  - Unicorn 재생은 `474ea`, area `7f`의 `4754a`/`4781a`, `3d58`, `4814e`, `ca9e`를 지나 `478a8`→`478b8`→`47934`에 닿는다. 이어 `28ae`가 garbage pool을 따라가다 `28cc`에서 unmapped read로 끝난다.
- 권고: stop=`47934`인 F1c1 앞부분 비교 seed(F1b block 포함)로 쓴다. `47934`를 넘는 실행은 음성 사례(machine checked 오류와 rollback)로 둔다.

**4. 기타**
- [F] `artifacts/stage_initialization`(526 case)·`stage_transition`(1,249)·`stage_area_initialization`(453)·`stage_players`·`stage_preparation`·`stage_sound_initialization`은 같은 루틴의 typed host 차분 검증이다. machine 비교 기준으로 쓰지 않고 fixture 구성 방식만 참고한다.
- [I] `game_ready` 흐름(`c654`가 `477e4`를 `100b30`에 설치)은 `477e4` 진입의 자연 전단계 후보다. 그러나 machine 관측은 없다[U].

## 검증 조건(최소)

**seed 경로(선언 재진입·선언 host write만)**
- F1b 연쇄 142건: `477ee`→2 frame→`47a94`를 split/continuous로 실행한다. 이어서 F1a로 `47a94`→`2ac2`까지 간다. 비교 기준은 같은 seed의 Unicorn 재생(새 관측 산출물)이다.
- runtime fixture 236건: `477ee`/`477e4`에서 시작해 frame별 `2ac2` stop과 마지막 `47a94` stop을 확인한다. F1c1만 구현했을 때는 `479b0` stop으로 확인한다.
- transition 4 phase: `477ee`→stop `47934`. 넘기면 rollback(음성)이다.

**host-write 직접 진입**
- gate:
  - `107ded` bit7=1이면 `478de` Waiting이다.
  - 선언 IRQ 효과 뒤 재개하면 통과한다. 효과 없이 재개하면 같은 Waiting이다. `107dea`≠0이면 Waiting이 유지된다.
- 표 index:
  - `47896` 직접 진입, `76(A6)`=RAM record로 `08`(`4791c`/`47922`, 61 frame)과 `10`(`4794c`/`4795c`/`47960`)을 실행한다.
  - `02`/`06`/`0a`/`0e`/`12`/`16`은 unsupported, 홀수는 unaligned다. `18` 이상은 `478a6` stop 또는 rollback이다.
- `28ae` 실패: WORD `104ca0`=0에서 `47944`/`4795c`/`47974`→`478c4`.
- catalog 변형:
  - stage≥`13`, area 범위 밖(null→재시도).
  - 빈 group(stage `09`): budget 초과 rollback.
  - 음악 같음/`19c1`/그 밖(`47872`).
  - `47a1c`의 `10fe`/`19c1`/`19c0`/같음/그 밖. `10fe`는 `479b0` 직접 진입과 RAM record로 만든다.
- area·player:
  - `10d684`=0/≠0, &3≠0(`476dc`), `7d`=0/≠0을 조합한다. `476ec`는 `479b0` 직접 진입, 7c∉6..8, `10d684`&3≠0으로 만든다.
  - `289e` C=0/1: `1009a8`/`100a6c`/`100cb8`/`100da8` LONG을 `270e`로 두거나 다른 값으로 둔다.
  - D1 음수(`2a48`), D1≥4(RNG), RNG 두 wrap(`10d722` 위치 조정).
  - `4e672` BMI(`10dd2a`/`2b` bit7), `4e67c` D0.W 상위 BYTE≠0(원본대로 부호확장 index).
- `4d81c` D1≥`14`: `481de` 직접 진입에서 `4d824` stop 또는 rollback.
- 대기: sound ring full(`104d74`=(`104d76`+1)&`7f`)이면 `3d6a`/`3d78`/`3af8`/`3d44` 경로에서 `3aea` Waiting이고, 선언 head release로 재개한다.
- 폭: `3d58`/`3d6e`에서 A7−1·A7+1 BYTE가 보존되고 A7이 복원된다. `49a58` 이후 A5=`108000`이다(A5=`108000` fixture에서만 검사).

**경계·오류**
- TRAP `478a6`/`4d824` stop과 비경계 stop rollback.
- Unknown carry로 소비 block 9개에 진입하면 오류.
- 묶인 분기 33개(DBRA 포함)와 내부 PC 850개(F1c1 214, F1c2 636) 거부.
- 홀수 A0/A1/A4/A6/A7 WORD·LONG 접근, 홀수 record 오류.
- RNG 포인터가 RAM 밖이면 쓰기 오류와 rollback.
- zero-step, 위 회귀 탐침 갱신.

**비교 항목**
- F1a와 같다: 64KiB RAM 전체, 16R/PC/A7, carry 분류, PVC 장치와 bank, 순서 있는 port, external reads, status, 입력·산출물 SHA, ROM stat 불변.

## F1 계약 "F1c 개요" 정정

1. block 수: "215개와 표 slot 6개"는 220 block 시작(표 slot 6, DBRA 대상 `4aa6e` 포함)+TRAP 경계 2로 바로잡는다. closure 스크립트(`f1/clos.py`)는 `DBRA Dn,target`의 대상을 해석하지 못한다.
2. "자연 seed는 없다(transition 관측의 `477ee` 경계 4건뿐)": 자연 게임 흐름 seed는 여전히 없다. 그러나 F1b 연쇄 142건과 runtime fixture 236건이 `47a94`까지 원본대로 간다. transition 4건은 garbage RAM이라 `47934`(`28ae`)에서 막힌다.
3. "`3d58`/`3d64`(`3d3a..3d6e`)": F1c가 쓰는 것은 `3d3a..3d44`, `3d58..3d62`, `3d6a..3d7c`다. `3d64`는 부르지 않고 `3d44`/`3d48`/`3d4c`는 exit 실행부다.
4. "`4e666`(`7d`==0 경로)": `4e666`과 `d760a`는 `10d684`==0일 때만 부른다(`479dc`·`479fe`).
5. "`1bd34`/`1bd96`(`289e` 계열 [U])": [F]로 확정한다. `1bd2e`/`1bd90 JSR 289e`의 복귀 PC다.
6. "음악 갱신(`3af8`/`3d44`)":
   - `10d686`을 먼저 새 값으로 쓴 뒤 비교한다. 같음·`10fe`·`19c1`이면 생략, `19c0`이면 `3d44`, 그 밖이면 `3af8`이다.
   - 첫 area 경로는 `47594`가 `10d686`을 지우므로 항상 다르다.
7. `ca48`/`1c5b0`/`9056`은 F1b block이다(결정 2). F1c helper 목록의 `47594` 팬아웃에는 TRAP `4d824`(`481de`→`4d81c`)와 A5를 덮어쓰는 `49a58`이 들어 있다.

## 미확인·범위 밖

1. 진입 효과 index의 게임 의미([I]: `00` 즉시 fade·gate, `04` 16 frame, `08` 60 frame, `0c`/`10`/`14` 자식 연출)와 catalog가 쓰지 않는 `08`/`10`의 용도.
2. `62(A6)`를 세우는 자식(`4fcb8`/`4fd0a`/`4ff4c` callback)의 동작과 자연 완료 시점(F2/F3).
3. 자연 상태에서 `478de` gate가 막히는 빈도와 실제 IRQ 시점(F1 미확인 1과 같음).
4. `10d684` flags 각 bit, `476bc` 표, `1009a8`/`100a6c` node, `270e` handler의 게임 의미. stage 8 area 1이 포인터 표 바이트를 읽는 것이 의도인지 여부.
5. 빈 group 9~15에 자연 진입할 수 있는지, `10fe` 음악 비교가 무엇을 뜻하는지.
6. RNG 포인터 미초기화 시 실제 하드웨어 결과(ROM 쓰기 무시 여부).
7. sound 명령(`0a`/`58`/`a0`, `720`, `1890..1892`)의 의미.
8. `4e67c` index의 D0.W 상위 BYTE가 자연 경로에서 항상 0인지(호출자 `475ca` 연쇄의 마지막 D0 생산자에 따름).
9. F1b 계약의 연쇄 seed 수(137)와 이 문서의 재생 수(142)의 차이.
10. 고립 stack(`1feffc`) fixture와 machine의 RAM 내 stack 대응(F1 미확인 8과 같음). 새 관측은 RAM 내 stack(`10eff8`)을 권고한다.

작업자 scratch: 세션 scratchpad `f1c/`(`c_lose.py`, `rng.py`, `rng2.py`, `blk.py`, `sub.py`, `sub2.py`, `fin.py`, `rep.py`, `rep_all.py`, `rep2.py`, `rep3.py`, `rep3b.py`, `rep_tr.py`, `chainc.py`, `grepb.py`; 저장소 밖).
