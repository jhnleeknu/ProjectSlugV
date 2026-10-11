# stage controller 완성 F1: 진입 본문·gate·활성화(F1a) 계약 초안

**상태: F1a 범위는 메인 리뷰를 거쳐 확정(아래 메인 결정), F1b·F1c는 개요. 구현·검증 기록이 아니다.** 범위 근거는 `animation-machine-frontier-after-480bc-scope.md`의 F1과 `animation-machine-480bc-scope.md`이며, 구조는 확정된 U2~U7 계약을 따른다.

Claude Opus 5.5 / high 분석 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, fixed CPU 주소=file offset)을 capstone M68000으로 디코드했다. banked window `200000+`는 bank `1000`이면 physical `200000`, `2000`이면 physical `300000`이다. 기존 관측 산출물은 Unicorn으로 읽기 전용 재생했고, 기존 실행부는 작업 트리 `/Users/start/Workspce/metalslug-input`(HEAD `57ec34a`, U1~U7 WIP 포함)의 `engine/src`를 읽기 전용으로 참조했다. [F]=원본 바이트 또는 기록 산출물·작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. 명령 단위 정답은 원본 바이트 자체다. block 수는 scratch 스크립트(`f1/lead.py`, `f1/cls.py`, `f1/clos.py`)가 원본 opcode에서 계산했다.

같은 루틴의 typed host 재구성(`engine/src/stage_entry_body*.cpp`, `stage_activation*.cpp`, `stage_catalog*.cpp`, `palette_transfer.cpp` 등)은 machine 실행부가 아니며 교차 확인 자료로만 쓴다.

메인 결정(Claude Opus 5.5, 원본 대조 리뷰 후): (1) F1a(block 시작 145+TRAP 경계 `e909c`)→F1b→F1c 순서로 나눈다. 이번 구현 범위는 F1a다. (2) `72f0` gate는 기존 `AnimationMachineWaiting`을 재사용한다. loop가 돌 상황(`47af6`의 C=0)이면 PC `47af0`(F1c에서는 `478de`)에서 Waiting으로 멈추고, host가 문서화한 IRQ palette 효과(bit7 해제 조건 포함, `107dea`≠0이면 원본 IRQ도 bit7을 남기므로 계속 대기)를 선언 변경으로 적용한 뒤 재개한다. 이는 자연 IRQ가 아니라 선언 fixture다. (3) `47b06`·`478a8` 표는 U2~U7의 계산 PC 정책을 따른다. (4) TRAP `e909c`(F1c: `478a6`, `4d824`)는 실행부 없는 stop 경계다. (5) PVC bank 쓰기는 기존 경로를 쓴다. (6) ROM 자료는 물리 `program_rom_000000.ms5d` window로만 읽고 `47aa6`는 stage record를 live로 다시 읽는다. (7) 새 실행부 파일 `engine/src/animation_machine_stage_entry.cpp`, `17292` unrolled clear는 한 block, `47af0`/`47b5c`/`47bfc`는 scheduler(F2) 전까지 선언 디스패처 재진입(A6=`100b30`, 복귀 `2ac2`), 무한 loop 가능성은 기존 block budget.

## 요약

- [F] F1 전체 정적 closure(기존 routing 27규칙에 이미 있는 PC에서 멈춤)는 **block 시작 약 406개**다. 범위 문서의 추정(~250)보다 크다. 주된 원인은 `477e4..47a94`가 부르는 `476dc`/`47594`/`475ca`가 `1bcfe..`, `2ef90..`, `46f2e..`, `49a58..`, `4aa30..`, `4d126..`, `4d81c..`, `4ddb6..`, `b4806..`, `b4a24..`, `b7a20..`로 퍼지기 때문이다.
- [I] 그래서 의존 순서대로 세 단위로 나누기를 권고한다. 이 문서는 F1a 전체 계약과 F1b·F1c 개요를 담는다.

| 단위 | 진입→끝 | block 시작 | 자연 seed | 주 위험 |
| --- | --- | --- | --- | --- |
| **F1a** 진입 본문·gate·표·활성화 | `47a94`/`47af0`/`47b5c`/`47bfc`/`47c04`→`480bc`/`47c6c`/`2ac2` | 145 + TRAP 경계 1(`e909c`) | stage_entry_body 152 phase, 그 출력에서 `47af0` 재진입 137, `47b5c` 연쇄 35, stage_activation_prefix 106 | `72f0` IRQ gate, `47b06` 범위 검사 없는 표, PVC bank, 4 KiB unrolled clear |
| F1b area clear | `47da4`(+callback 5)→`480bc`/`477ee` | 39 | 없음(transition 관측의 host-write 경계 1건뿐) | `28ae` 실패 무시, `SCC` carry 소비 |
| F1c catalog·area·transition | `477e4`/`477ee`(+callback 4)→`47a94` | 약 221(표 slot 6, TRAP `478a6`·`4d824` 포함) | 없음(transition 관측의 `477ee` 경계 4건뿐) | `478a8` 표(상한만 검사), `72f0` gate 재사용, helper 팬아웃 |

- [F] F1a만 구현하면 stage_entry_body 152 phase의 미연결 leader 84개(고유) 중 sentinel `ff000`을 뺀 83개가 모두 F1a 안에 든다. [I] 그러면 `47a94`부터 `480f0` RTS까지 한 frame 전체를 machine이 처음으로 끝까지 실행할 수 있다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

### 1. F1 분할

- 선택 A(**작업자 권고**): F1a(145)→F1b(39)→F1c(~221) 순서로 따로 구현한다. F1a는 자연 seed가 풍부해 통합 frame 검증이 바로 된다. F1b는 `477ee`를, F1c는 `47a94`를 경계 stop으로 둔다.
- 선택 B: F1c를 다시 c1(`477e4..47a94` 본문+작은 helper, 약 140)과 c2(`476dc`/`47594`/`475ca` 팬아웃, 약 80)로 나눈다.
- 선택 C: F1 전체(~406)를 한 번에 구현한다. [I] 비권고. F1b·F1c에는 자연 seed가 없어 host-write fixture로만 검증된다.

### 2. `72f0` palette IRQ gate 모델 (가장 중요)

**원본 동작**
- [F] `72f0` `MOVE.B -$213(A5),D0`(BYTE `107ded`, D0 상위 24bit 보존), `SUBI.B #$80,D0`, `RTS`. 따라서 C=1 ⇔ BYTE<`80`(bit7=0)이다. D0.B는 BYTE−`80`(mod 256)이 된다.
- [F] 호출자는 두 곳뿐이다: `47af0`(F1a), `478de`(F1c). fixed 1 MiB 원시 검색 `4eb9000072f0` 결과다. 둘 다 `JSR 72f0`; `BCC.B` 자기 자신으로 된 busy loop다(`47af6`, `478e4`). bit7이 1인 동안 RAM 외 아무것도 바뀌지 않는다.
- [F] bit7을 지우는 유일한 코드는 IRQ 경로 `cbe JSR 72fa`의 `7302 BCLR #7,107ded`다. 단 `72fa`는 WORD `107dea`≠0이면 `873a`(특수 bank 경로)로 가며, 그 경로는 bit7을 지우지 않는다. bit7은 `7232`/`72d0`에서 `MOVE.B 107dd5,107ded`로 설정된다(palette 준비 `718c..72ee`).
- [F] 기존 host 구현 `transfer_palette_frame`/`transfer_palette_banks`(`engine/include/ms5/palette_transfer.h`)가 `72fa`의 RAM 효과(bit7 해제, `105da2` WORD `&8000` mask, dirty header bit7 해제, palette bank 갱신)를 재현한다.
- [F] 자연 seed에서는 gate가 한 번도 막히지 않았다. stage_entry_body begin 출력 142개 모두 BYTE `107ded`=0이었고, `47af0` 재진입 137건 모두 `47af6`에서 C=1이었다.

**선택지**
- 선택 A(**작업자 권고**): 새 상태 값을 만들지 않는다. `47af6`(F1c에서는 `478e4`) block에서 C=Clear이면 PC=`47af0`(`478de`)로 두고 `c.waiting=true`로 `AnimationMachineWaiting`을 돌려준다. 이는 sound `3aea`·sprite `cda4` 대기와 같은 규약이다. 대기 상태는 A7이 callback 수준(복귀 LONG만 남음)이고, D0.B=BYTE−`80`, A7−4에 stale LONG `47af6`이 남은 상태다. 이 상태는 원본 spin의 어느 반복과도 RAM·레지스터가 같다. 재개는 host가 선언된 IRQ 효과(권고: `transfer_palette_banks`와 같은 RAM 효과, 최소안: BYTE `107ded` bit7 해제)를 적용한 뒤 같은 상태로 다시 호출한다. 효과 없이 재개하면 한 반복 뒤 같은 Waiting을 돌려준다(멱등). `107dea`≠0이면 원본 IRQ도 bit7을 남기므로 다시 Waiting이다. host는 상태 PC(`47af0`/`478de`)로 대기 종류를 구분한다(기존 관행).
- 선택 B: `AnimationMachineStatus`에 `AnimationMachineWaitingPalette` 같은 새 값을 추가한다. 공개 header를 바꾸며 기존 호출자 전체에 영향이 있다.
- 선택 C: bit7=1이면 checked 오류(`stage controller palette gate requires interrupt`)로 전체 rollback한다. 가장 단순하지만 bit7=1 상태로는 직접 진입할 수 없다.
- [U] 실제 IRQ는 spin 중 임의 명령 경계에서 들어오고 frame counter·sound·watchdog도 함께 바꾼다. 선택 A는 그중 palette RAM 효과만 선언된 host 변경으로 표현한다. 다른 IRQ 효과의 포함 여부는 메인 결정 사항이다.

### 3. 계산 PC 표 정책

- [F] `47b02` `JMP 47b06(PC,D0.W)`. D0=`MOVEQ #0`, `MOVE.B 1(A0)`이므로 index는 0..`ff`이고 **범위 검사가 없다**. 표는 8 slot(`47b06..47b22`, BRA.W)이다.
- 권고: U2~U7과 같이 원본 계산 PC `47b06+index`로 그대로 이동한다. 그 PC가 F1a block 시작이면 실행하고, 아니면 `unsupported animation machine PC`, 홀수면 기존 홀수 PC 오류로 전체 rollback한다.
  - [F] index≥`20` 짝수 중 block 시작에 닿는 값이 있다(예: `20`→`47b26`, `56`→`47b5c`, `fe`→`47c04`).
  - [I] `80`/`96`/`ce`→carry 소비 block `47b86`/`47b9c`/`47bd4`이다. machine은 MOVE.B의 C=0을 추적하지 않으므로 Unknown carry 오류가 된다. 원본은 C=0으로 분기한다. 이 차이는 오류로만 드러난다.
  - [F] 자연 seed 1건(`live-RAM-record-reread`, case 141의 출력)은 RAM record `10d420`의 +1 BYTE=`ff` 때문에 `47c05`로 점프한다. Unicorn은 주소 오류 예외를 냈다. machine은 홀수 PC 오류로 같은 결과(진행 불가)를 낸다.
- [F] F1c `478a8` `JMP 478ac(PC,D0.W)`는 `4789e CMPI.W #$18`/`BCS` 상한 검사가 있다. 상한 이상은 `478a6 TRAP #15`로 간다. 4의 배수 검사는 없다(예: 2→`478ae`, BRA.W의 displacement 중간). 같은 정책을 권고한다.

### 4. TRAP #15 경계

- [F] `e909c TRAP #15`: event lookup 항목의 첫 BYTE가 `ff`도 `00`도 아닐 때다. 권고: U1 `4939c`·U6 `4d7f0`처럼 실행부 없는 경계로 둔다. stop=`e909c`이면 그 직전 상태로 멈추고, 아니면 `unsupported animation machine PC`로 rollback한다. F1c의 `478a6`·`4d824`도 같다.

### 5. PVC bank 쓰기

- [F] `1a5a4`는 WORD 1→`100010`, `2000`→`2ffff2`, `0`→`2ffff0`(기존 `am_write` PVC 경로, U2 `1a73c`와 같은 쓰기)이다. 따라서 `1a5a4..1a724` 동안 banked window는 physical `300000`이다.
- [F] `1a724`와 `e90b2`가 `0`→`100010`, `1000`→`2ffff2`, `0`→`2ffff0`(`am_zero_bank`와 같은 세 쓰기)으로 되돌린다. `e9076`(event null) 경로는 되돌리지 않고 `1a724`의 결과를 그대로 둔다.
- 권고: 기존 PVC 쓰기 경로를 그대로 쓰고 새 장치는 두지 않는다. [F] 재생한 142 seed에서 F1a block 자신의 banked window 읽기는 0건이었다. banked 읽기는 U3~U5 callee 안에서만 일어났다.

### 6. ROM 자료 window

- 권고: U6 결정 5·U7 결정 4 선례대로 physical `extracted/runtime/program_rom/program_rom_000000.ms5d` window로만 읽는다. legacy kind 1/2 stage·event MS5D와 함께 싣지 않는다(program bus는 legacy/kind3 겹침을 ambiguous로 거부한다).
- [F] 재생 142 seed에서 F1a block이 읽은 fixed ROM은 다음과 같다.
  - catalog record: `47a98` LONG +2, `47a9c`/`47adc` WORD +14, `47aaa` LONG +6, `47ace` LONG +10. 주소는 `472c4..dd4bc`이다.
  - lookup 역참조 `47ada` LONG: `485d4..f1f40`.
  - event lookup 표 `e907e`/`e908a`/`e909e`/`e90a6`: `485d8..fbf7a`.
  - motion record `19964` WORD +8, `199e4` WORD +10: `48936..4fb08`.
  - placement WORD `1a422`: `d9c0c..f1a8c`.
- [F] 재생하지 않은 경로의 ROM 읽기는 다음과 같다.
  - `47afe` BYTE +1.
  - `47ba6` LONG +6과 그 cue(U7 `e8af4`).
  - `362a` 표 `ddfa4..ddfdc`(56바이트, 아래).
- [F] 한 seed(case 141)는 record가 RAM(`10d420`)이다. `47aa6`은 `1a5c2`가 바꾼 뒤의 record를 **다시 읽어야** 한다(관측: `e8a1c` 진입 A0=`00a00080`).

### 7. 그 밖의 결정

- (a) 새 실행부 파일 제안: `engine/src/animation_machine_stage_entry.cpp`(`animation_stage_entry_block`). routing 22 범위(아래)이며 `e909c`는 제외한다.
- (b) `17292` unrolled clear는 한 block으로 둔다. `A1=A0+80`, `D0=0`이고, 오름차순 LONG 쓰기 2048개(8 KiB)를 수행한다. 하나라도 쓰기에 실패하면 전체 rollback이다. 끝 상태는 `A1=A0+2080`, D0=0이다.
- (c) dispatcher 재진입 선언: F2(scheduler) 전이므로 `47af0`/`47b5c`/`47bfc` 진입은 A6=`100b30`, A5=`108000`, `(A7)`=복귀 LONG `2ac2`로 선언한 직접 진입으로 둔다. (F1a native 관측 보정) index `18` 경로(`47b1e`→`480b6`→`2a00`)의 `2a02 MOVEA.L -335c(A5),A7`가 dispatcher 기준 LONG `104ca4`를 읽으므로 재진입 선언에 `104ca4`=`1ff000`(직접 진입 A7 기준값)도 포함한다. 선언하지 않으면 frame이 A7=0으로 `2ac2`에 닿는다(관측 finding fixture).
- (d) 무한 루프 가능 지점(`1a65a..1a6aa`, `1a422..1a440`, `e908a..e90aa`, `362a..364e`)은 U5 결정 5처럼 원본대로 두고, 기존 block budget만 한계로 둔다.

## F1a 원본 바이트 근거

[F] 코드 22 범위 합계 5,608바이트, 2,428명령, 미해독 0이며 범위 안 빈틈은 없다. 아래 hex는 위 ROM에서 직접 추출했다.

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `47a94..47c5a` | `286e0076206c0002302c000e4eb90001a5a4286e0076206c00064eb9000e8a1c08ed0001568308ed0003568308ed00055683610008d0286e0076206c000ab0fc0000670000042050302c000e4eb9000e905c2cbc00047af0600005ce4eb9000072f064f8206e00767000102800014efb00026000001e600000326000005860000062600000746000008660000596600005764eb90000caf070007200740076004eb900008c16600000c870007200740076143d43007a4eb900008c164eb90000caf02cbc00047b5c536e007a6400055a6000009e70007200740076203d43007a60d4207c0004fcce303c00004eb9000028ae649e6000005a207c0004fd20303c00004eb9000028ae648860000044206e0076206800064eb9000e8af441ed538ed0680014d26800183b4056903b415692207c0004ff12303c00004eb9000028ae6400ff50316d56900076316d56920078422e006270007200740076004eb900008c162cbc00047bfc4a2e0062670004ba4a2d5684660000144eb9000090604eb90004e25408ed000456837001c02d5684670000066100fb787004c02d5684660000084eb90000ca764eb90000ca5608ed00025683102e007c0c000006640000084eb90000c3c0` |
| `72f0..72fa` | `102dfded040000804e75` |
| `1a5a4..1a73c` | `3b7c0001801033fc2000002ffff233fc0000002ffff03b40541c4ebafaba3b7c000054183b7c00a054263b7c00805428426d542a426d542c3b7c800054443b7c80005446426d5448426d544a3b7c7fff54423b7c7fff5440426d544c3b7cffff542e3b7cffff5430426d543242ad543442ad5438426d543c426d540c42390010d44e6100f1406100fc726100f5206100f7ba6100fd90307c00006100fdce41f9001091564eb90001729241f90010b1d64eb9000172926100fc0e6100f3743c2d541cbe46640000126100f37c640000063b47541c600000043e063c2d5416be46650000043e063b475418484742476100f2a42b4053bc2b4153c0610001083e2d5418be6d541c65ae41ed538e201022280004327c00004eb900043e2241ed1156201022280004327c00004eb900016fee41ed31d6201022280004327c00004eb900016fee41ed5256201022280004327c00004eb900016fee41ed52d6201022280004327c00004eb900016fee3e2d541ebe6d541c640000066100fb806100fcf23b7c0000801033fc1000002ffff233fc0000002ffff04e75` |
| `17292..1829a` | 4,104바이트, SHA256 `6da578d5498b326592a7acd6e146a6f95644adb0a0bc77843e8d0087f09f9259`. 구성: `43e80080` `7000` + `22c0`×2048(`17298..18298`, 확인함) + `4e75` |
| `19768..19772` | `227c0000000070007200` |
| `19938..19978` | `226d53b4b2fc00006600001470007200302d53b8322d53ba484048414e756100fdd22b4953b46100f67274003429000848426100f29a64000004d282d0824e75` |
| `199d4..19a00` | `226d53b4b2fc0000660000067e004e753e29000a4e75226d53b4b2fc000066000008003c00014e756000fd1e` |
| `19b50..19b96` | `422d53cc42ad53de42ad53e242ad53fc42ad5400426d53ee426d53f03b7c00a053d63b7c008053d8426d53da426d53dc2b7c0006000053e62b7c0006000053ea6100015c4e75` |
| `19dee..19e60` | `41f90010915643f90010d3564eba003441f90010b1d643f90010d3644eba002441f90010d25643f90010d3724eba001441f90010d2d643f90010d3804eba00044e7542914269000442690006426900084269000a137c0010000c4eb900016fac327c0000202d538e222d53924ef900016fee` |
| `1a07a..1a086` | `2b4854123b7c000054164e75` |
| `1a3c8..1a3d6` | `426d5404426d540642ad54084e75` |
| `1a414..1a442` | `206d540eb0fc0000660000044e753e100c47ffff660000044e75be6d5418630000044e75610000362b48540e60e0` |
| `e8a1c..e8a3a` | `b0fc00006600000641faffbe2b485e261b7c00ff5e2e1b7c00005e2f4e75` |
| `e905c..e90ca` | `2f083f0041ed8bf443fa00ea4eb900002a28301f2e1f66000008214700764e75224732194a406700002843f1100012110c0100ff6700001a0c010000670000044e4fb069000263000008d2e9000460de2e09214700763b7c0000801033fc1000002ffff233fc0000002ffff04e75` |
| `477a2..477ac` | `303c71624ef9000ddf9a` |
| `ddf9a..ddfa4` | `41fa00084ef90000362a` |
| `362a..3650` | `32180c41ffff660000044e753f00d041740076003218141816182f084ebaffa8205f301f60da` |
| `9060..9068` | `423900107def4e75` |
| `4e254..4e26c` | `1b7c00ff5d1f422d5d201b7c00008a421b7c00008b064e75` |
| `ca56..ca5c` | `422d89674e75` |
| `ca76..ca7e` | `1b7c00ff89654e75` |
| `c3c0..c3ce` | `b02dff316f0000061b40ff314e75` |

[F] 자료 `ddfa4..ddfdc`(SHA256 `14bba835b16c565a15364b794befbc8aca3c2575e28443654fbdae61ea36e30c`): `00008f80080801048fc8020401009f88020201869fec020201c09f8e02080140af8a04040184afcc02020102ffa802020144ffca0204ffff`. 이는 6바이트 record 9개(WORD offset, WORD D1, BYTE D2, BYTE D3)와 종료 WORD `ffff`다.

[F] 기존 routing 규칙과의 겹침은 없다. 모든 F1a 명령 주소에 대해 scratch `routing.py`(현재 27규칙 재현)가 미배정을 돌려줬다. 인접 경계는 다음과 같다.
- U2: `19978..199d4`, `19a40..19b50`, `19b96..19dee`, `1a3d6`, `1a442`, `1a526..1a5a4`, `1a73c`.
- U5: `19772`, `19e60`, `1a086`, `1a40e..1a414`.
- U4: `1724c..17292`.
- U3: `..19768`.
- 기타: sound `ca70..ca76`, exit `ca7e`/`47c5a`, hud `35f0..3628`, card_menu_open `3650`, transition `477ac`, fade_card `c364..c3be`, cleanup `c3dc`.

## F1a 실행 의미

[F] A5 상대 d16은 live A5로 계산한다. 아래 절대 주소는 A5=`108000` 기준이다(`53xx`/`54xx`→`10d3xx`/`10d4xx`, `5683`→`10d683`, `-7699`→`100967`, `-769b`→`100965`, `-75be`→`100a42`, `-74fa`→`100b06`, `-740c`→`100bf4`, `-213`→`107ded`, `-cf`→`107f31`, `-7ff0`→`100010`). 절대 LONG 주소를 쓰는 명령은 A5와 무관하다: `1a620` CLR.B `10d44e`, `9060` `107def`, `1a642`/`1a64e`/`19dee..19e24`의 LEA. 공통 폭 규칙은 U2와 같다. MOVE.W/MOVE.B Dn은 나머지 bit를 보존하고, MOVEQ·MOVEA.W(부호확장)는 LONG 전체를 쓴다. X 소비 명령은 F1a에 없다.

1. **진입 본문.**
   - `47a94`: A4=LONG `76(A6)`, A0=LONG `2(A4)`, D0.W=WORD `14(A4)`, JSR `1a5a4`(복귀 `47aa6`). [F] `47a94`는 F1c `47a8e JSR 3d44`의 복귀 PC이자 관측 진입점이다.
   - `47aa6`: A4=LONG `76(A6)`(재읽기), A0=LONG `6(A4)`, JSR `e8a1c`(복귀 `47ab4`).
   - `47ab4`: BSET #1, #3, #5를 BYTE `10d683`에 차례로 하고 BSR `48398`(exit, 복귀 `47aca`).
   - `47aca`: A4 재읽기, A0=LONG `10(A4)`; A0==0이면 `47adc`. `47ada`는 A0=LONG `(A0)`.
   - `47adc`: D0.W=WORD `14(A4)`, JSR `e905c`(복귀 `47ae6`).
   - `47ae6`: LONG `47af0`→`(A6)`, BRA `480bc`(U1).
2. **`1a5a4`(장면 초기화와 목표 phase까지 진행).**
   - 시작: WORD 1→`100010`, PVC `2000`/`0`, WORD D0→`10d41c`, JSR `1a07a`(복귀 `1a5c2`). `1a07a`는 LONG A0→`10d412`, WORD 0→`10d416`, RTS다.
   - `1a5c2` 쓰기 순서:
     - WORD `10d418`=0, `10d426`=`a0`, `10d428`=`80`.
     - CLR.W `10d42a`, `10d42c`.
     - `10d444`=`10d446`=`8000`.
     - CLR.W `10d448`, `10d44a`.
     - `10d442`=`10d440`=`7fff`.
     - CLR.W `10d44c`.
     - `10d42e`=`10d430`=`ffff`.
     - CLR.W `10d432`, CLR.L `10d434`, `10d438`, CLR.W `10d43c`, `10d40c`.
     - CLR.B 절대 `10d44e`.
     - BSR `19768`(복귀 `1a62a`).
   - `19768`: A1=0, D0=0, D1=0으로 두고 **U5 `19772`로 fall-through**한다(분기가 아님. block은 PC=`19772`로 끝난다).
   - 이어지는 BSR: `1a62a` BSR `1a29e`(U2) → `1a62e` BSR `19b50` → `1a632` BSR `19dee` → `1a636` BSR `1a3c8` → `1a63a` A0=0(MOVEA.W), BSR `1a40e`(U5) → `1a642`/`1a64e` A0=`109156`/`10b1d6`, JSR `17292`.
   - 루프 `1a65a`:
     - BSR `1a26a`(U2), BSR `199d4`.
     - `1a662`: D6.W=`10d41c`. D7.W≥D6이면(BCC) `1a67c` D7.W=D6이다. 아니면 `1a66c` BSR `199ea` 후 `1a670` BCC(carry 소비)이고, C=1이면 `1a674` WORD D7→`10d41c`이다. `1a678` BRA `1a67e`.
     - `1a67e`: D6.W=`10d416`. D7<D6(BCS)이면 유지, 아니면 `1a688` D7.W=D6.
     - `1a68a`: WORD D7→`10d418`, SWAP D7, CLR.W D7, BSR `19938`.
     - `1a696`: LONG D0→`10d3bc`, D1→`10d3c0`, BSR `1a7a8`(U4).
     - `1a6a2`: D7.W=`10d418`. `10d41c`보다 작으면(BCS) `1a65a`로 반복한다.
   - `1a6ac`: A0=`10d38e`, D0/D1=LONG (A0)/4(A0), A1=0, JSR `43e22`(cleanup).
   - `1a6c0`/`1a6d4`/`1a6e8`/`1a6fc`: A0=`109156`/`10b1d6`/`10d256`/`10d2d6`(A5 상대 `1156`/`31d6`/`5256`/`52d6`). 각각 D0/D1=(A0)/4(A0), A1=0, JSR `16fee`(U5).
   - `1a710`: `10d41e`≥`10d41c`이면(BCC) `1a720`, 아니면 `1a71c` BSR `1a29e`.
   - `1a720` BSR `1a414` 후 `1a724`에서 bank를 되돌리고 RTS.
3. **`19938`.** A1=LONG `10d3b4`.
   - null: `19944` D0=D1=0, D0.W=`10d3b8`, D1.W=`10d3ba`, 둘 다 SWAP, RTS.
   - 비null: `19956` BSR `1972a`(U3, 복귀 `1995a`) → `1995a` LONG A1→`10d3b4`, BSR `18fd2`(U3, 복귀 `19962`) → `19962` D2=WORD `8(A1)`<<16, BSR `18c06`(U3, 복귀 `1996e`) → `1996e` BCC `19974`(carry 소비). C=1이면 `19972` ADD.L D2,D1. `19974` ADD.L D2,D0, RTS.
4. **`199d4`.** A1=`10d3b4`; null이면 `199e0` MOVEQ 0,D7, 아니면 `199e4` D7.W=WORD `10(A1)`. RTS.
5. **`199ea`.** A1=`10d3b4`; null이면 `199f6` ORI CCR #1(known Set), RTS. 아니면 `199fc` BRA `1971c`(U3, 그 RTS가 known C를 `1a670`으로 돌려준다).
6. **`19b50`.**
   - CLR.B `10d3cc`; CLR.L `10d3de`, `10d3e2`, `10d3fc`, `10d400`; CLR.W `10d3ee`, `10d3f0`.
   - WORD `10d3d6`=`a0`, `10d3d8`=`80`; CLR.W `10d3da`, `10d3dc`.
   - LONG `10d3e6`=`10d3ea`=`60000`.
   - BSR `19cee`(U2, 복귀 `19b94`), `19b94` RTS.
7. **`19dee`.** 다음 네 쌍에 대해 JSR `19e30`을 부른다(PC 상대, 복귀 `19dfe`/`19e0e`/`19e1e`/`19e2e`). `19e2e`에서 RTS.
   - (A0, A1) = (`109156`, `10d356`), (`10b1d6`, `10d364`), (`10d256`, `10d372`), (`10d2d6`, `10d380`).
   - `19e30`: CLR.L (A1); CLR.W 4/6/8/10(A1); BYTE `10`→12(A1); JSR `16fac`(palette_bind, 복귀 `19e4e`).
   - `19e4e`: A1=0, D0=LONG `10d38e`, D1=LONG `10d392`, **JMP** `16fee`(U5 tail call; 그 RTS가 `19dee`의 호출 지점으로 돌아간다).
8. **`1a3c8`.** CLR.W `10d404`, `10d406`; CLR.L `10d408`; RTS.
9. **`1a414`(placement 따라잡기).**
   - A0=`10d40e`; null이면 `1a420` RTS.
   - `1a422`: D7.W=WORD (A0). `ffff`이면 `1a42c` RTS.
   - `1a42e`: D7≤`10d418`(BLS, unsigned)이면 `1a438` BSR `1a470`(U5, 복귀 `1a43c`). 아니면 `1a436` RTS.
   - `1a43c`: LONG A0→`10d40e`, BRA `1a422`.
10. **`17292`.** 앞의 결정 7(b)와 같다.
11. **`e8a1c`.** A0==0이면 `e8a24` A0=`e89e4`(PC 상대). `e8a28`: LONG A0→`10de26`, BYTE `ff`→`10de2e`, `0`→`10de2f`, RTS.
12. **`e905c`(stage event node 재설치와 lookup).**
    - 시작: push LONG A0, push WORD D0, A0=`100bf4`, A1=`e9150`, JSR `2a28`(cleanup, 복귀 `e906e`). `2a28`은 node `100bf4`를 정리하고 `(100bf4)`=`e9150`을 쓴다. 복귀 시 A0=`100bf4`다.
    - `e906e`: D0.W=pop WORD(상위 WORD는 callee 값 유지), D7=pop LONG. MOVE.L의 Z로 BNE.
    - D7==0: `e9076` LONG D7→`76(A0)`(=`100c6a`), RTS. bank 복원은 없다.
    - `e907c`: A1=D7, D1.W=(A1)+. D0.W==0이면 `e90ac`.
    - `e9086`: A1+=sext(D1.W).
    - 루프 `e908a`: D1.B=(A1). `ff`이면 `e90ac`. `00`이면 `e909e`, 그 밖은 `e909c` TRAP(경계). `e909e`: D0.W≤WORD `2(A1)`(BLS)이면 `e90ac`, 아니면 `e90a6` A1+=sext(WORD `4(A1)`), BRA `e908a`.
    - `e90ac`: D7=A1, LONG→`76(A0)`, 세 bank 복원 쓰기, RTS.
13. **gate·표(`47af0..47c04`).**
    - `47af0` JSR `72f0`(복귀 `47af6`). `47af6` BCC `47af0`(결정 2).
    - `47af8`: A0=LONG `76(A6)`, D0=0, D0.B=BYTE `1(A0)`, JMP `47b06+D0.W`. 표 slot은 `47b06`→`47b26`, `47b0a`→`47b3e`, `47b0e`→`47b68`, `47b12`→`47b76`, `47b16`→`47b8c`, `47b1a`→`47ba2`, `47b1e`→`480b6`(fade_card), `47b22`→`4809a`(fade_card)이다.
    - `47b26`: JSR `caf0`(screen, 복귀 `47b2c`). `47b2c`: D0..D3=0, JSR `8c16`(exit, 복귀 `47b3a`). `47b3a` BRA `47c04`.
    - `47b3e`: D0..D2=0, D3=`14`, WORD D3→`7a(A6)`. `47b4a` JSR `8c16`(복귀 `47b50`). `47b50` JSR `caf0`(복귀 `47b56`). `47b56` LONG `47b5c`→`(A6)`. `47b5c`(callback 진입 겸 fall-through): SUBQ.W #1,`7a(A6)`; borrow가 없으면(BCC) `480bc`. `47b64` BRA `47c04`.
    - `47b68`: D0..D2=0, D3=`20`, `7a(A6)`=`20`, BRA `47b4a`.
    - `47b76`/`47b8c`: A0=`4fcce`/`4fd20`, D0.W=0, JSR `28ae`(fade_card, known C, 복귀 `47b86`/`47b9c`). 다음 block에서 BCC `47b26`(실패), 성공이면 `47b88`/`47b9e` BRA `47be4`.
    - `47ba2`: A0=LONG `6(LONG 76(A6))`, JSR `e8af4`(U7, 복귀 `47bb0`). `47bb0`: D0.W+=WORD `10d3a2`, D1.W+=WORD `10d3a6`, →`10d690`/`10d692`, A0=`4ff12`, D0.W=0, JSR `28ae`(복귀 `47bd4`). `47bd4` BCC `47b26`. `47bd8`: WORD `10d690`→`76(A0)`, `10d692`→`78(A0)`(A0=새 객체).
    - `47be4`: CLR.B `62(A6)`, D0..D3=0, JSR `8c16`(복귀 `47bf6`). `47bf6` LONG `47bfc`→`(A6)`. `47bfc`(callback 진입 겸 fall-through): BYTE `62(A6)`==0이면 `480bc`, 아니면 `47c04`로 fall-through.
14. **활성화 `47c04`.**
    - BYTE `10d684`≠0이면 `47c1e`로 간다. 0이면 `47c0c` JSR `9060`(CLR.B `107def`), `47c12` JSR `4e254`, `47c18` BSET #4,`10d683`을 거친다.
    - `4e254`: BYTE `ff`→`10dd1f`, `0`→`10dd20`, `0`→`100a42`, `0`→`100b06`, RTS.
    - `47c1e`: `10d684`&1≠0이면 `47c28` BSR `477a2`(복귀 `47c2c`).
    - `47c2c`: `10d684`&4==0이면 `47c36` JSR `ca76`(BYTE `ff`→`100965`).
    - `47c3c` JSR `ca56`(CLR.B `100967`).
    - `47c42`: BSET #2,`10d683`; D0.B=BYTE `7c(A6)`. D0.B≥6(BCC, unsigned)이면 `47c5a`(exit) 직행, 아니면 `47c54` JSR `c3c0`(복귀 `47c5a`).
    - `c3c0`: CMP.B `107f31`,D0. D0.B≤BYTE(BLE, 부호)이면 `c3cc` RTS. 아니면 `c3c8` BYTE D0→`107f31`.
    - `477a2`: D0.W=`7162`, JMP `ddf9a`. `ddf9a`: A0=`ddfa4`, JMP `362a`.
    - `362a` 루프: D1.W=(A0)+. `ffff`이면 `3634` RTS(`47c2c`로 복귀). 아니면 `3636`:
      - push WORD D0, D0.W+=D1, D2=D3=0.
      - D1.W=(A0)+, D2.B=(A0)+, D3.B=(A0)+.
      - push LONG A0, JSR `35f0`(hud, 복귀 `364a`).
      - `364a`: A0=pop LONG, D0.W=pop WORD, BRA `362a`.
      - [F] 표는 record 9개이므로 `35f0`은 9번 불린다.

[F] port 쓰기는 `1a5aa`/`1a5b2`, `1a72a`/`1a732`, `e90b8`/`e90c0`(PVC)뿐이다. callee(`299c` watchdog `300001` 등)는 기존 실행부가 맡는다.

## 구현 범위와 규약(F1a)

- **routing 22 범위**:
  - `47a94..47c5a`, `72f0..72fa`, `1a5a4..1a73c`, `17292..1829a`, `19768..19772`, `19938..19978`, `199d4..19a00`, `19b50..19b96`, `19dee..19e60`, `1a07a..1a086`, `1a3c8..1a3d6`, `1a414..1a442`.
  - `e8a1c..e8a3a`, `e905c..e90ca`(`e909c` 제외), `477a2..477ac`, `ddf9a..ddfa4`, `362a..3650`, `9060..9068`, `4e254..4e26c`, `ca56..ca5c`, `ca76..ca7e`, `c3c0..c3ce`.
  - [F] 짝수 PC는 2,804개다. block 시작 145와 경계 `e909c`를 빼면 내부 PC는 2,658개다.
- **Block 시작 PC (145개)**: 루틴 진입, 분기 대상, 조건분기 fall-through, 호출 복귀, 호출 진입, 표 slot 8개, dispatcher callback 진입 `47af0`/`47b5c`/`47bfc`이다. 일반 규칙으로 144개(`e909c` 포함)를 계산했다. 여기에 `MOVE.L #imm,(A6)`로 설치되는 callback 진입 `47b5c`·`47bfc`를 더하고, TRAP 경계 `e909c`를 뺐다.

`362a` `3634` `3636` `364a` `72f0` `9060` `c3c0` `c3c8` `c3cc` `ca56` `ca76` `17292` `19768` `19938` `19944` `19956` `1995a` `19962` `1996e` `19972` `19974` `199d4` `199e0` `199e4` `199ea` `199f6` `199fc` `19b50` `19b94` `19dee` `19dfe` `19e0e` `19e1e` `19e2e` `19e30` `19e4e` `1a07a` `1a3c8` `1a414` `1a420` `1a422` `1a42c` `1a42e` `1a436` `1a438` `1a43c` `1a5a4` `1a5c2` `1a62a` `1a62e` `1a632` `1a636` `1a63a` `1a642` `1a64e` `1a65a` `1a65e` `1a662` `1a66c` `1a670` `1a674` `1a678` `1a67c` `1a67e` `1a688` `1a68a` `1a696` `1a6a2` `1a6ac` `1a6c0` `1a6d4` `1a6e8` `1a6fc` `1a710` `1a71c` `1a720` `1a724` `477a2` `47a94` `47aa6` `47ab4` `47aca` `47ada` `47adc` `47ae6` `47af0` `47af6` `47af8` `47b06` `47b0a` `47b0e` `47b12` `47b16` `47b1a` `47b1e` `47b22` `47b26` `47b2c` `47b3a` `47b3e` `47b4a` `47b50` `47b56` `47b5c` `47b64` `47b68` `47b76` `47b86` `47b88` `47b8c` `47b9c` `47b9e` `47ba2` `47bb0` `47bd4` `47bd8` `47be4` `47bf6` `47bfc` `47c04` `47c0c` `47c12` `47c18` `47c1e` `47c28` `47c2c` `47c36` `47c3c` `47c42` `47c54` `4e254` `ddf9a` `e8a1c` `e8a24` `e8a28` `e905c` `e906e` `e9076` `e907c` `e9086` `e908a` `e9094` `e909e` `e90a6` `e90ac`

- **묶인 조건분기 PC (25개, 직접 진입 거부)**: `3630` `c3c4` `19940` `199dc` `199f2` `1a41c` `1a428` `1a432` `1a668` `1a684` `1a6aa` `1a718` `47ad6` `47b60` `47c00` `47c08` `47c24` `47c32` `47c50` `e8a20` `e9072` `e9082` `e9090` `e9098` `e90a2`. [F] 모두 같은 block의 Z/N/C 생산자(CMP/CMPI/CMPA/TST/AND.B/SUBQ/MOVE.L) 뒤에 온다. 이전 block의 Z나 N을 소비하는 block 시작은 없다.
- **Carry 소비 block (6개)**: `47af6`(`72f0`), `47b86`·`47b9c`·`47bd4`(`28ae`), `1a670`(`199f6` 또는 U3 `1971c`), `1996e`(U3 `18c06`). 진입 C가 Unknown이면 checked 오류(제안 문자열 `stage controller caller requires known carry`)와 전체 rollback이다. `47af6`의 C=Clear는 결정 2를 따른다.
- **Known carry 생산 block**: `72f0`(SUBI.B 계산값, block 안 RTS), `199f6`(ORI, Set, block 안 RTS). [F] 나머지 생산자는 기존 실행부다(`28ae` 두 RTS, U3 `1971c`/`18c06`).
- **Carry 보존(FLOW_ONLY) block (63개)**: `3634` `c3cc` `19956` `1996e` `199fc` `19b94` `19dee` `19dfe` `19e0e` `19e1e` `19e2e` `1a420` `1a42c` `1a436` `1a438` `1a62a` `1a62e` `1a632` `1a636` `1a63a` `1a642` `1a64e` `1a65a` `1a65e` `1a66c` `1a670` `1a678` `1a71c` `1a720` `47aa6` `47ab4` `47ada` `47af0` `47af6` `47b06` `47b0a` `47b0e` `47b12` `47b16` `47b1a` `47b1e` `47b22` `47b26` `47b3a` `47b4a` `47b50` `47b64` `47b86` `47b88` `47b9c` `47b9e` `47ba2` `47bd4` `47c0c` `47c12` `47c18` `47c28` `47c36` `47c3c` `47c54` `ddf9a` `e8a24` `e9086`.
  - 기준은 U2와 같다. 전 명령이 LEA/MOVEA/JSR/JMP/BSR/BRA/RTS/BTST/BSET/BCLR/조건분기인 block만 넣었다.
  - [I] 정확성에 필요한 것은 `47af6`·`1a670`·`1996e`·`47b86`·`47b9c`·`47bd4`(소비 block 자신)뿐이다. 나머지는 규약상 목록이다.
- **경계(실행부 없음)**: TRAP `e909c`(결정 4).
- **기존 실행부로 나가는 지점(모두 기존 block 시작임을 확인)**:

| 대상 | 실행부 | 나가는 곳 → 복귀 |
| --- | --- | --- |
| `1972a` / `18fd2` / `18c06` | U3 | `19956`→`1995a` / `1995e`→`19962` / `1996a`→`1996e` |
| `1971c` | U3 | `199fc` BRA |
| `19cee` | U2 | →`19b94` |
| `1a29e` | U2 | →`1a62e`, `1a720` |
| `1a26a` | U2 | →`1a65e` |
| `16fac` | palette_bind | →`19e4e` |
| `16fee` | U5 | →`1a6d4`/`1a6e8`/`1a6fc`/`1a710`, `19e4e` JMP |
| `19772` | U5 | `19768` fall-through |
| `1a40e` | U5 | →`1a642` |
| `1a470` | U5 | →`1a43c` |
| `1a7a8` | U4 | →`1a6a2` |
| `43e22` | cleanup | →`1a6c0` |
| `2a28` | cleanup | →`e906e` |
| `48398` | exit | →`47aca` |
| `8c16` | exit | →`47b3a`/`47b50`/`47bf6` |
| `47c5a` | exit | `47c50` BCC, `c3c0` 복귀 |
| `caf0` | screen | →`47b2c`/`47b56` |
| `28ae` | fade_card | →`47b86`/`47b9c`/`47bd4` |
| `480b6` / `4809a` | fade_card | `47b1e` / `47b22` BRA |
| `e8af4` | U7 | →`47bb0` |
| `35f0` | hud | →`364a` |
| `480bc` | U1 | `47aec`/`47b60`/`47c00` |

- 폭·연산:
  - BSET/BCLR 메모리 bit 번호는 mod 8이다.
  - `SUBQ.W #1,7a(A6)`의 C는 borrow다(0→`ffff`이면 C=1이고 fall-through).
  - `SUBI.B`의 C는 borrow다.
  - `CMP.B`+BLE는 부호 비교, `BCC`/`BCS`/`BLS`는 무부호 비교다.
  - `LEA (A1,D1.W)`와 `ADDA.W`는 부호확장한다.
  - `MOVE.W (A7)+,D0`는 상위 WORD를 보존한다. `MOVE.L (A7)+,D7`의 Z로 분기한다.
  - live stack push/pop: `e905c`, `3636`/`364a`.
  - 홀수 주소 WORD/LONG 접근은 기존 checked 오류와 rollback이다. BYTE `1(A0)`·`(A1)`은 홀수도 허용한다.
- 루프: 결정 7(d)와 같다.
- 기존 회귀 탐침 갱신이 필요하다. [F] 아래 PC를 `unsupported animation machine PC` 탐침으로 쓰는 기존 test가 있다. block 시작은 실행되고, 내부 PC는 새 실행부 오류 문자열로 바뀐다. 탐침은 여전히 미연결인 PC(예: `19a3e`, `1a3a6`, `e8a3a`, `e8a46`)로 옮겨야 한다.
  - `animation_machine_buffer_cue_test.cpp:582`: `e8a1c`.
  - `animation_machine_scene_core_test.cpp:410`: `19768 19770 19938 19976 199d4 19b50 19b94 19dee 1a3d4 1a414 1a440 1a5a4 1a73a`.
  - `animation_machine_scene_update_test.cpp:798`: `17292 19e5e 1a07a`.
  - `animation_machine_script_placement_test.cpp:831`: `19770 19e5e 1a07a 1a084 1a414 1a43c 1a440`.
  - `animation_machine_motion_walk_test.cpp:761/772`: `19768 19938`. 761행의 "도달하지 않는 stop" 사례도 다시 확인해야 한다.

## 자연 시작 상태(읽기 전용 재생)

[F] scratch `f1/replay_entry.py`는 `tools/observe_stage_entry_body.py`의 `build_cases`/`prepare_case`/`Observer`를 그대로 import해 142 case의 begin 입력을 재구성했다. 같은 Unicorn에 읽기 hook만 더해 F1a block 경로를 기록했다. 산출물 SHA256은 `artifacts/stage_entry_body/observation.json` `1f65100f1fedc36b4999543c720814dc6f9eb4bf634f3af3439aa68d70e31207`, `artifacts/stage_activation_prefix/observation.json` `d27d39fa7129934db20f0a7735056822e2b27f30a54e474e0609bb3e347c51ce`이다.

**1. stage_entry_body begin 142(`47a94` 직접 진입)**
- [F] 조건: A6=`100b30`, A5=`108000`, profile 0/1 레지스터, bank 2(2건은 bank 3), 복귀 sentinel `ff000`.
- [F] 결과: 137은 `ff000`, 5(`wholebody-sound-wait`)는 U1 sound 대기 `3aea`에서 끝났다. hold/release 10 phase는 `3aea` 재개뿐이며 F1a를 지나지 않는다.
- [F] 경로:
  - `47ada`(lookup 비null) 118 / null 24.
  - `e8a24`(cue null→`e89e4`) 21.
  - `e9076`(event null) 24 / `e907c` 118. 그중 D0≠0 `e9086` 20, `e908a` 루프 20 seed(102회), `e90a6` 12.
  - `19944` motion null 22 / `19956` 120. `19972`(C=1) 114.
  - `199e0` 22 / `199e4` 120.
  - `1a66c`·`199fc` 6(모두 C=0 → `1a678`).
  - `1a688` 15.
  - `1a420` 73 / `1a422` 69(`1a42c` 63, `1a436` 6, `1a438` 63).
- [F] 미실행: `199f6` `1a674` `1a71c` `e909c`.
- [F] F1a block의 banked 읽기는 0건이고, ROM 읽기는 모두 fixed `<100000`이다(결정 6).

**2. dispatcher 재진입 `47af0`**
- [F] 조건: begin 출력 137건(poisoned `b30`=`deadbeef`인 release 5건 제외)을 그대로 쓴다. A6=`100b30`, `2abe`에서 `JSR (A0)`(복귀 `2ac2`)로 실행한다. scratch `f1/second.py`.
- [F] 결과:

| index(`+1` BYTE) | 건수 | 경로 | 끝 |
| --- | --- | --- | --- |
| `0c` | 89 | `47b12`→`47b76`→`28ae` 성공→`47be4`→`47bfc`(`62(A6)`=0) | `480bc`→`2ac2` |
| `04` | 35 | `47b0a`→`47b3e`→`47b5c`(20→19) | `480bc`→`2ac2` |
| `18` | 6 | `47b1e`→`480b6` | fade_card `2a00` 경로→`2ac2` |
| `00` | 4 | `47b26`→`47c04` | `47c6c` |
| `1c` | 2 | `47b22`→`4809a` | BIOS `c00468` |
| `ff` | 1 | case 141, RAM record | `47c05` 홀수 PC |

  - `47c04` 4건은 `47c0c`·`47c1e`→`47c2c`→`47c36`→`47c3c`→`47c54` 경로였다.
  - 모든 건에서 `72f0` C=1(gate 통과)이었다.
- [F] 미실행: `47b0e`/`47b68`, `47b16`/`47b8c`, `47b1a`/`47ba2`/`47bb0`/`47bd8`, `28ae` 실패 `47b86`→`47b26`, `47b64`, `47bfc`→`47c04`.

**3. `47b5c` 연쇄**
- [F] index `04` 35건은 host write 없이 같은 dispatcher 재진입을 반복했다. 매번 `480bc` 전체 frame을 지났고 sound/sprite 대기는 없었다. 21번째 호출(첫 `47af0` 포함)에서 `7a(A6)` 0→`ffff`로 `47b64`→`47c04`→`47c6c`에 도달했다. scratch `f1/chain.py`.

**4. stage_activation_prefix 106(`47c04` 직접 진입→`47c6c` 앞 stop)**
- [F] 조건: 104 case와 supplemental 2건이다. A6=`102000`, 고립 stack `1feffc`이다.
- [F] 경로 분포: BYTE `10d684`의 ≠0 여부·bit0·bit2와 `7c(A6)`<6의 조합 10종이다(건수 20/6/10/6/10/6/10/6/16/16). `477a2`→`ddf9a`→`362a` 9 record→`3634` 경로가 48건이다. `c3c0`는 106 trace 중 66건이며, 104 case의 branch coverage로는 `c3c4` BLE 41/23(합 64)이다.

**5. 기타**
- [F] 기존 stage_frame 96건은 F1a PC를 지나지 않는다.

## 검증 조건(최소)

**자연 경로(직접 진입)**
- stage_entry_body 142 begin을 `47a94`→sentinel stop(137) 또는 `3aea` Waiting(5)까지 실행하고, 이어서 hold/release 10 phase를 재개한다. 기존 기록 파일(`native_*.bin`·`.ports.bin`·결과 레지스터·bank)과 비교한다. split/continuous로 한다.
- [I] 이것이 `47a94`→`480f0` 첫 전체 frame 통합 검증이다.
- begin 출력 137건을 `47af0`으로 재진입하고 위 표의 끝 PC에서 stop하거나 오류를 확인한다. 비교 기준은 같은 seed의 Unicorn 재생이다(새 관측 산출물 필요).
- `47b5c` 연쇄 35건(21 호출)→`47c6c`.
- stage_activation_prefix 106건 `47c04`→`47c6c` stop.

**host-write 직접 진입**
- `107ded` bit7=1이면 `47af0` Waiting(결정 2 선택 A)이다.
  - 선언 IRQ 효과 적용 뒤 재개하면 통과해야 한다.
  - 효과 없이 재개하면 같은 Waiting이어야 한다(상태 동일).
  - `107dea`≠0 특수 경로에서는 Waiting이 유지되어야 한다.
- 표 index와 경로:
  - `08`(`47b68`), `10`(`47b8c`), `14`(`47ba2`/`47bb0`/`47bd8`, cue flags bit0/1).
  - `28ae` 실패(D0.W=0≥WORD `104ca0` 무부호, 즉 WORD `104ca0`=0; [F] `28ae`는 A0≠0이므로 그 밖의 실패 갈래가 없다)로 `47b86`/`47b9c`/`47bd4`→`47b26`.
  - `7a(A6)`=0에서 `47b5c`→`47b64`, `62(A6)`≠0에서 `47bfc`→`47c04`.
- 계산 PC:
  - index `20`/`56`/`fe`는 block 시작이므로 실행한다.
  - `80`은 Unknown carry 오류다.
  - `01`/`ff`는 홀수 PC 오류다.
  - `24` 등 내부 PC는 unsupported다.
- event·lookup:
  - event lookup 첫 BYTE가 `ff`/`00`이 아니면 `e909c` stop 또는 rollback이다.
  - `00` 항목에서 BLS 갈래 둘 다, D0=0 직행을 확인한다.
- `1a5a4` 내부 분기:
  - motion null에서 `199ea`→`199f6`→`1a674`.
  - `10d41e`<`10d41c`이면 `1a71c`.
  - `18c06` C=0/1(`19972` 생략/실행).
  - placement 루프 여러 번(`1a43c`).
- 진입 변형:
  - `e8a24`, `47ada` null, `e9076` null.
  - record를 RAM에 두고 재읽기(case 141과 같은 유형).
  - 초기 bank 3, `1a5a4` 중 banked 포인터(script/motion이 `200000+`, physical `300000` 읽기).
- 활성화 변형: `c3c0` BLE 양쪽, `10d684` 비트 조합, `7c(A6)`≥6.

**경계·오류**
- `e909c` stop과 비경계 stop rollback.
- Unknown carry로 소비 block 6개에 진입하면 오류.
- 묶인 분기 25개와 내부 PC 2,658개 거부.
- 홀수 A0/A1/A4/A6/A7 접근 오류.
- `17292` 쓰기가 RAM 밖으로 넘치면 rollback.
- zero-step.
- 위 회귀 탐침 갱신.

**비교 항목**
- 기존과 같다: 64KiB RAM 전체, 16R/PC/A7, carry 분류, PVC 장치와 bank, 순서 있는 port, external reads, status, 입력·산출물 SHA, ROM stat 불변.
- stack은 기존 machine 검증과 같은 RAM mirror 규약을 따른다. [U] 관측기의 고립 stack `1feffc`와 machine의 RAM 내 A7 사이 대응은 각 verify 도구의 기존 방식을 따른다.

## F1b 개요(area clear, 계약 미작성)

- [F] 범위:
  - `47da4..47eac`(`47da0`까지는 transition, `47eac`부터 exit), `4b6e4`, `4b6ec`, `1c5b0..1c5ea`, `1bee4..`(다시 `49c20`), `ca48`, `9056`.
  - block 시작 39개다(callback `47de4` `47e22` `47e62` `47e70` `47e92` 포함, `9060`은 F1a). 끝은 `47ea8 BRA 477ee`(F1c 경계)다.
- [F] 기존 실행부 호출: `289e`(`1c5b0`), `2a48`(stage event node `100bf4` 정리), `28ae`(`e4234`, `d72fe` 자식), `3af8`(sound `19db`), `8c16`(fade `e1/e1/e1/30`), `480bc`, `49c20`.
- [F] carry 소비:
  - `1c5bc`·`1c5d8`(`289e`).
  - `47e0a`(`SCC.B 62(A6)`+`BCC`: C를 메모리로 옮기는 소비).
  - `47e3a JSR 28ae` 뒤에는 C 검사가 없다. 실패 시 fallback A0=`100e98`에 `76(A0)`를 쓴다.
- [I] 의미(미확인 부분 있음):
  - 30 frame 대기 뒤 `10d68e`≠0이면 `9056`, 자식 `e4234`(`76`=area), 그 완료 대기(`62(A6)`), `9060`을 거친다.
  - 이어서 자식 `d72fe`(D0=`14`, `76`=area+1)를 만들고 sound `19db`를 낸다. 160 frame을 기다린 뒤 `10dd44`≠0까지 frame마다 poll한다.
  - fade 후 48 frame을 기다리고 `7c(A6)`+1→`10d680`, CLR `10d681`, `477ee`로 간다.
- [F] 시작 상태: 자연 seed는 없다. `artifacts/animation_machine_transition_native`(observation SHA `edf1f5e7248601d2a708cbc7ebfb8a89c62bfdb5dcef018cb94a2c5fa26aaba4`)에 `47da4` stop 1 phase가 있다(host-write fixture).

## F1c 개요(catalog·area·transition, 계약 미작성)

- [F] 범위는 `477e4..47a94`(`477ac`/`477bc`/`477c2..477e2`는 기존)와 helper `474e2`, `47540`, `4814e`, `3d58`/`3d64`(`3d3a..3d6e`), `ca8a`, `476dc`, `47594`, `475ca`, `4e666`, `48180`, `d760a`다. 정적 closure는 F1a·F1b와 겹치는 것을 빼고 block 시작 215개와 표 slot 6개(`478ac..478c0`)다.
- [F] 묶음:
  - TRAP `478a6`·`4d824`.
  - callback `478de`(`72f0` gate) `4790a` `4798e` `479b0`.
  - 죽은 코드 `47a54..47a64`(fixed ROM 안에 참조 없음)는 제외한다.
- [F] carry 소비: `478e4`(`72f0`), `47944`/`4795c`/`47974`(`28ae`), `47716`/`47732`/`4776c`, `1bd34`/`1bd96`(`289e` 계열 [U]).
- [F] 주요 흐름:
  - `477e4`: `1a5a4(A0=0,D0=0)` 후 `477ee`로 간다. `477ee`: `10d680`/`10d681`→`7c`/`7d(A6)`; `474e2`(stage 표 `474f4`, index<`13` 아니면 0)와 `47540`(area 목록 walk)으로 record를 `76(A6)`에 둔다. null이면 `7d` 0으로 재시도한다.
  - 정리 호출 `ca48`, `1c5b0`, `ca7e`, `4e24e`, `9056`, `10d683` bit 해제를 한다.
  - 음악 WORD `16(record)`와 `10d686`을 비교하고 `3d58`(`38`/`80`)과 `4814e`를 부른다. 이어서 `ca9e`.
  - 진입 효과 표 `478a8`(6 target) 뒤 `479b0`에서 다음을 한다:
    - `e7c36`, `477c2`, `10d681`=`ff`.
    - `476dc`(`5684`&3).
    - `7d`==0이면 `47594`+`4e666`, 아니면 `48180`×2+`475ca`.
    - `d760a`, `49c32`×2.
    - 음악 갱신(`3af8`/`3d44`), sound `1890..1892`, `3c84`, `3d44`.
    - 끝으로 `47a94`(F1a)로 간다.
- [F] 시작 상태: 자연 seed는 없다. transition 관측에 `477ee` stop 4 phase가 있다(host-write fixture).

## 미확인·범위 밖

1. 결정 2의 IRQ 효과 범위(palette RAM 효과만 둘지)와 실제 IRQ 시점. 자연 seed에서 gate가 한 번도 막히지 않아 원본 대기 상태 관측이 없다.
2. catalog record 필드(+1 진입 종류, +2 script, +6 cue, +10 event lookup, +14 목표 phase 겸 event index, +16 음악)의 게임 의미는 [I]이다.
3. `47b06` 표 index `08`/`10`/`14`/`1c`의 실제 stage 사용 여부와 `1c`→`4809a`→BIOS `c00468`의 의미.
4. `1a65a` 루프가 script 대기 `10d416`이 멈출 때 끝나지 않을 가능성(원본 그대로 budget에 맡김).
5. `e908a` event 표 walk의 종료 보장(`ff`/BLS 외 상한 없음)과 TRAP `e909c`의 의도.
6. `17292` 대상이 RAM 밖일 때 원본 동작(bus 오류 또는 무시)과 checked 오류의 차이.
7. `47bfc`/`47b5c`를 넘는 자연 다중 frame에서 다른 node(`100bf4` event `e9150`, 객체 pool)의 영향. F2·F3 범위다.
8. stack 고립(`1feffc`) 관측과 machine RAM 내 stack의 비교 방식(기존 도구 규약 확인 필요).
9. F1b·F1c의 정확한 block·묶음·carry 목록(개요 수치는 closure 추정), helper `476dc`/`47594`/`475ca`의 팬아웃 경계.

작업자 scratch: 세션 scratchpad `f1/`(`dis2.py`, `lead.py`, `cls.py`, `clos.py`, `split.py`, `cons.py`, `bytesf.py`, `agg2.py`, `replay_entry.py`, `second.py`, `chain.py`, `gate2.py`; 저장소 밖).
