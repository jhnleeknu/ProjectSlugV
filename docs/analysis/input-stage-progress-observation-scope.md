# 입력·스테이지 진행 관측 기반(단위 IO) 범위·설계

메인 결정(Claude Opus 5.5, 2026-10-18):
- 선택안 채택: S 계열(136 seed, game (ii) + BYTE `10f006` |= 1 선언 + 입력 스크립트, Execute + 실제 IRQ)과 B 계열(USER `852` BIOS 없는 boot snapshot)을 같은 protocol로 관측한다. (b) demo replay를 S seed에 선언하지 않는다.
- 결정 1: B 계열의 stack rebase(A7 `10f300` → `1ff000`)는 선언으로 둔다. 공개 헤더는 바꾸지 않는다.
- 결정 2: ROM 쓰기는 v1에서 checked 정지(guard `rom-write`)로 둔다. 실행부는 바꾸지 않는다.
- 구현 분할은 §8을 따른다. IO-2 관측 도구는 Sonnet/high, IO-3 C++ 비교·frontier는 Sonnet/medium이 맡는다.

**상태: 구현 전 범위·설계 문서(메인 결정 반영, 2026-10-18).** `remaining-work-plan.md` §3의 선행 기반을 구체화한다. 구현·검증 기록이 아니다.

- 작성: Claude Opus 5.5 / high 읽기 전용 분석 작업자. 작업 트리 `metalslug-io`(브랜치 `claude/input-observation`, HEAD `35a1eda`).
- ROM: `extracted/program/maincpu.decrypted.be.bin` SHA256 `29112a94…c886c860f`, mtime_ns `1791291625887190107`. 모든 탐침이 시작·끝에 SHA·mtime이 같음을 assert했다. 대상 코드는 모두 고정 영역 `<100000`이라 CPU 주소 = 파일 오프셋이다(뱅크 코드 실행은 탐침에서 0회).
- routing 기준: `engine/src/animation_machine.cpp` SHA256 `8ce8eb93…`(HEAD).
- seed: 역사 macOS `artifacts/stage_entry_body/observation.json`(SHA256 `1f65100f…`, `seed_kind historic`, `MS5_SEED_DIR`).
- 도구: Unicorn 2.1.4, capstone 5.0.6, macOS arm64.
- 표기: [F] 원본 바이트·탐침 실행에서 확인한 사실, [I] 추론, [U] 미확인.
- 모든 탐침은 선언 모델이다. BIOS 실행, 자연 IRQ 시점, 자연 scheduler를 주장하지 않는다. IRQ 전달은 F6-D와 같은 대기 지점 선언 전달이고, host 쓰기와 장치 응답은 모두 선언이다.
- 저장소 도구·엔진·ROM·추출 자료는 바꾸지 않았다. 탐침은 scratch `ms5-scratch/io1/`에 있으며 기존 관측기를 in-process로 import만 했다(§10).

## 1. 요약(권고)

- [F] **기존 137 seed에 입력만 넣으면 새 code가 거의 열리지 않는다.** 플레이어 node `100cb8`/`100da8`는 모든 seed에서 idle(`270e`)이다. BIOS 플레이어 상태 `10fdb6`/`10fdb7`(BIOS_PLAYER_MOD)도 0이다. 게임 mode(D9 (ii))에 입력 스크립트만 더하면 다음이 일어난다.
  - stage controller가 frame 241~245에 idle이 되고, controller가 `c79a` 대기로 간다(입력 없을 때와 같다).
  - start bit를 누르면 `c79a` menu를 거쳐 frame 274(seed 94는 34)에 BIOS `c00444`로 끝난다.
- [F] **"BIOS가 PLAYER_START를 처리한 결과"를 host 쓰기 1건으로 선언하면 C·D 영역 code가 실행된다.** 선언은 BYTE `10f006` |= 1이며, `a74`의 `OR.B D0,10f006` 효과와 같다. H의 `b68`이 이를 `10fdb6` := 1로 바꾼다.
  - 136 seed × 600 frame(IRQ 실행, 입력 스크립트)에서 새 미routing PC 1,864개가 실행됐다. 함수 root 328개(D 226, C 61, E 41 [I 분류]), 실행 1,282,870회.
  - 12 seed는 controller가 새 게임 시작(`c82e`→`c8e8`→`c90c`)으로 가서 캐릭터 선택(`4e732`)을 거쳐 플레이어 `1d1f4`를 만든다. 플레이어 frame은 합계 4,328이다.
- [F] **BIOS 없는 boot 선언(c)이 가장 자연스러운 seed 공급원이다.** 카트리지 USER 진입 `852`를 0 RAM에서 native로 실행했다. 선언 장치 응답 3개와 BIOS 호출 2개(RTS 선언), bank 창 쓰기 1건 무시만으로 scheduler dispatcher `2ab8`에 닿는다. 이때 node 목록은 `100820` = `e4a`, `1008e4` = `c52a`이고 나머지는 `270e`다. boot 상태에서 D1 frame(Execute + IRQ)을 이어 실행한 결과는 다음과 같다.
  - `10fdae` = 2(demo 요청): intro `c5f4`(228 frame) → `c608`(150 frame) → `c610`의 `3162`가 **replay 포인터 `104cc4` := `f07fe`, 입력 mode `104cd4` := 1**을 설치한다. mission 7 stage(`47c6c`)에서 플레이어가 ROM replay 입력으로 움직였다(replay cursor `0`→`29`, 197 frame). frame 577에는 원본이 ROM `aeaba`에 쓰는 지점에서 native 정지가 났다(§3.3).
  - `10fdae` = 3(title) + 선언 BYTE `10fdaf` := 2(frame 100, title에서 `a74`를 처음 부른 효과): 캐릭터 선택 → mission 1 → 플레이어 생성 → 사망 → `10fdb6` = 3(game over) → `c940` → frame 906에 BIOS `c00444`로 끝난다. boot부터 game over까지 이어진다.
- **결정(권고):** 단위 IO의 관측기는 seed 계열 두 개를 같은 protocol로 다룬다.
  - **S 계열:** 기존 136 seed + 게임 mode 선언 + 선언 player start + 입력 스크립트. C·D의 즉시 frontier다.
  - **B 계열:** BIOS 없는 boot snapshot. demo replay와 title → 게임 시작이며 E의 frontier이자 장기 주 공급원이다.
  - (b) demo replay는 S seed 위에 선언하지 않는다. B 계열의 demo 경로가 replay 포인터를 원본 code(`3162`)로 설치하기 때문이다.
- [F] 두 번 실행해 같다: S 9 seed × 600 frame의 frame별 전체 상태 digest가 같았다. B demo·title 실행 JSON도 시간 필드를 빼면 같았다.

## 2. 현재 기반 [F]

- **frame 구동기:** `step_animation_machine_frame`, `animation_machine_frame.h`. H → C(`AnimationFrameControllerExecute`) → N 순서이고, `irq_execution`이면 대기 지점에서 IRQ를 전달한다. C++ option에서 두 기능을 함께 켤 수 있다. 그러나 **Execute + IRQ 조합은 원본 비교가 없다**. 검증된 것은 controller 검증기(Execute, IRQ 없음)와 IRQ 검증기(Skip + IRQ)뿐이다. 이 조합의 비교가 단위 IO의 첫 C++ 비교다.
- **입력 queue:** `AnimationMachineDevice::reads`는 단일 순서 queue다. WORD `3c0006`와 BYTE `300000`/`340000`/`380000`만 소비한다.
  - mode 0의 H 한 번은 7건을 소비한다: `3c0006`(`eaa`), `3c0006`(`efc`), `380000`, `300000`, `340000`, `300000`, `340000`. 탐침에서 frame당 7건, 599 frame에 4,193건이었다.
  - IRQ 안의 읽기(`320000`, `3c0006`)는 queue가 아니라 option(`irq_z80_reply`, `irq_video_status`)에서 온다.
- **N 구간 장치 읽기:** 모든 탐침(S·B, IRQ 유무)에서 N 구간의 `300000`/`340000`/`380000` 직접 읽기는 0건이었다. 게임 logic은 H sampler가 RAM에 둔 입력만 읽는다.
  - 관측기 FH는 skip 뒤 장치 page를 0으로 정규화한다. 따라서 N에서 직접 읽기가 생기면 값 `00`(전부 눌림)을 읽게 된다. 이것은 guard로 막는다(§5.6).
- **입력 RAM:**
  - `104cb4`/`104cb5`: system, 곧 start/select와 그 edge.
  - `104cb6`/`104cbc`: P1/P2 6바이트 블록.
  - `104ca8`/`104cae`: gameplay 블록, mode 0에서는 두 번째 읽기 쌍으로 갱신.
  - `104cd4`: 입력 mode, 0 = 실시간, 1 = replay, 2 = 끝.
  - `104cc4`: replay 포인터.
  - 근거: `input-sampler.md`, H2 계약.

## 3. seed 공급원 평가

탐침 공통 조건:
- in-process native 실행. 클래스는 `verify_animation_machine_frame_controller.make_controller_class`(controller Execute)에 `verify_animation_machine_frame_irq.make_irq_class`의 IRQ 전달·palette RAM을 합성한 scratch 클래스 `ioprobe_lib.X`/`XF`다.
- 입력은 관측기 FH의 `script_queue`를 scratch에서 monkeypatch해 frame별 port 값을 그 frame의 모든 읽기에 공급했다. raster는 0이다.
- 미routing 판정은 실행된 TB 안의 명령 시작 PC를 routing bitmap으로 검사했다. bitmap은 `animation_machine.cpp`의 범위·단일 PC이고, 단일 PC 실행부는 함수 내부 분기 closure까지 포함하는 근사다 [I].
  - 기준선 P0(입력 없음, 136 seed × 600 frame)에서 이 판정이 낸 PC는 `3900` 1개뿐이다. D9에서 이미 알려진 실행부 끝 PC다.
  - 같은 PC 집합에 V1 검증기의 dispatch chain 평가기 `pc_routed`를 다시 적용하면 1,864개 모두 routing 밖이다.

### 3.1 (a) 기존 137 seed + 선언 입력

입력 스크립트 `walkfire`(scratch):
- frame 20부터 P1 오른쪽(`300000` bit 3).
- A(bit 4)는 4 frame마다 토글한다.
- B(bit 5)는 64 frame마다 6 frame 누른다.
- active-low이고, `340000`·`380000`은 `ff`다.
- `walkfire-start`는 여기에 P1 start(`380000` bit 0)를 frame 5~7, 60~62, 200~202에 더한다.

| 구성(5 seed: 0 30 94 120 135, 600 frame) | 결과 [F] |
| --- | --- |
| A: 게임 mode, 입력 없음 | 4 seed는 frame 245에 `c7fc`→`c79a` 대기로 가고, seed 94는 frame 1에 간다. 새 미routing 0 |
| B: A + `walkfire-start` | 5 seed 모두 BIOS `c00444`(C `system-return`)로 끝난다. frame 274(seed 94는 34)이고 `c79a` menu가 start를 받은 결과다 |
| C: A + `walkfire-start` + BYTE `10fdb6` := 1 | 600 frame 완주. stage controller가 `47c6c`에 머문다(`47c98`이 `7db6(A5)` = 1을 검사). seed 0·135는 새 PC 353개(적 `76xxx` `70xxx` `c53ec` …), seed 94는 1,272개(새 게임 시작, 플레이어 생성 frame 72) |
| D: C + IRQ 실행(F6-D 방식, P1 준비) | C와 미routing 수가 같다. IRQ는 frame당 2회 전달 |
| E: A + `walkfire-start` + BYTE `10f006` := 1(frame 6) | C와 사실상 같다(seed 94 1,268개). `b68`이 frame 6의 H에서 `10fdb6` := 1로 바꾼다 |

- [F] 원본 근거:
  - `a74`(PLAYER_START, 헤더 `128 JMP a74`): `10fdaf` = 2이면 `abc`로 가서 `D0 = 10fdb4 & f004 & f007`, `OR.B D0,10f006`, `10fdb4` := D0, D0 ≠ 0이면 `10fdaf` := 2.
  - `b68`(H): `10f006` bit를 지우면서(`BCLR`) 해당 `10fdb6+n` := 1로 둔다.
  - `47c98`: `10fdb6`/`10fdb7` = 1이 아니면 `47d24`(플레이어 없음 경로)로 간다.
  - 플레이어 생성 경로는 두 가지다. area 시작 `479ba`(`10d684 & 3` ≠ 0, seed는 모두 0)와 캐릭터 선택 객체 `4e94e`→`4e91c LEA 1d1f4`→`2a28`이다.
- [F] **136 seed 전체(구성 P1 = 게임 mode + BYTE `10f006` := 1 @frame 1 + `walkfire` + IRQ, 600 frame):**
  - 정지: 136 seed 모두 frame-limit. case 141은 frame 0 `odd-pc`로 D1과 같다.
  - 새 미routing PC 1,864개, 실행 1,282,870회, 함수 root 328개.
  - 미routing에 닿은 seed는 52개다. 첫 미routing frame은 최소 2, 중앙 100, 최대 327이다.
  - 플레이어를 만든 seed는 12개(4,328 frame)다.
  - controller 종료 callback: `c7fc` 128 seed, `c82e`/`c8e8`/`c90c` 12 seed.
- [F] **seed 동치류는 14개뿐이다.** 결과 서명(첫 미routing, 플레이어 frame, 미routing 수) 기준이다.

  | 동치류 | seed 수 | 서명 |
  | --- | --- | --- |
  | 새 code 없음 | 85 | 플레이어 없음. 카메라 정지(`10d3bc` 변화 0) |
  | `b3dbc` frame 99 | 11 | 343 PC. 카메라 자동 이동 `+0x3828000` |
  | `e5324` frame 100 | 11 | 78 PC |
  | `de660` frame 2 | 8 | 새 게임, 플레이어 385 frame, 1,126 PC |
  | `de660` frame 222 | 4 | 플레이어 312 frame, 894 PC |
  | 나머지 | 9쌍 × 2 seed | — |

  - 전체 상태 digest는 72종이다.
  - [I] 플레이어가 없으면 카메라가 움직이지 않아 다음 stage event가 열리지 않는다. 그래서 85 seed는 600 frame 안에 새 code가 없다.
- [F] 실패 양상:
  - start bit는 `c79a` menu에서 BIOS 종료를 일으킨다. 그래서 S 계열 기본 스크립트에는 start를 넣지 않는다.
  - 플레이어는 회피하지 않아 사망한다. 사망 뒤 `10fdb6` = 3이 되고 stage controller가 `47fa8`→`47fdc`→`4806a`로 간다.
  - 600 frame 안에 다른 mission으로는 가지 않았다(`10d680` 불변). seed 94류는 `10d681` := `ff`, `10d686` := `19d2`(새 mission 시작)다.

### 3.2 (b) demo replay(`104cd4` = 1, ROM stream `f01fe..`)

- [F] 필요한 상태는 `3162`(selector 0/1)가 쓰는 값 전부다.
  - `104cd4` := 1.
  - LONG `104cc4` := 표 `f0dfe`[selector](`f01fe`/`f07fe`), `104cc8` := 표 `f1a06`[selector].
  - WORD `104ccc`/`104cce`/`104cc2` := 0, BYTE `104cd0` := 0.
  - 이와 함께 demo mission이 처음부터 시작해야 한다.
- [F] 설치 code는 controller C3b 경로다. `c52a` → `c560`(`107dea` 대기, IRQ만 줄임) → `c56e`(`f004` := 3, `10fdae` 분기) → `10fdae` = 2이면 `c5b4` → intro(`ca7e` `4fb1a`, `c5ce`/`c5f4` flag 대기, `c608` 150 frame) → `c610`.
  - `c610`은 `702a` := 1, `c4cc`, `caf0`, `47570`, `4823a`(6 + (`702a`&1)), `3162`(`702a`)를 실행하고, `c654`로 `477e4`를 `100b30`에 설치한 뒤 `c66a`로 간다.
  - `c66a`는 매 frame `314c`(`104cd4` = 1이면 C=1)로 replay가 끝났는지 본다. 끝나면 `c69a` → `e66aa` → `c6c0` → `c00444`(demo 끝)다.
- [F] D9 (i)가 실패한 원인은 seed의 `104cc4` = 0이다(ROM 0부터 replay). 위 상태를 S seed에 host 쓰기로 선언할 수는 있다. 그러나 mission을 처음부터 시작하는 controller 경로(`c610` 이후)를 함께 선언해야 하고, seed 객체 상태와 맞지 않는다(§3.1의 `f004` = 0도 같은 문제).
- [F] B 계열 demo 실행(§3.3)은 이 상태 전체를 원본 code로 만든다. `3162`가 frame 379에 `104cc4` := `f07fe`, `104cd4` := 1을 쓴다. 이후 mission 7(`10d680` = 7)에서 플레이어(`1edb0`→`1ef0e`→`1ebf6`→`1f6da`→`1f3d8`→`1fb02`→`1fcce`→`1fd12`)가 replay 입력으로 움직인다.
- **판정:** (b)는 독립 seed 공급원으로 선언하지 않는다. B 계열의 demo 실행으로 얻는다.

### 3.3 (c) BIOS 없는 boot 선언(USER `852`/C3b → title/demo/게임)

[F] 탐침 `p3_boot.py`. 0 RAM, A7 = ROM LONG 0(`10f300`), SR `2700` [I: BIOS가 USER를 인터럽트 금지로 부른다는 가정], PC `852`에서 native로 실행한다. 아래 선언이 모두 필요했다.

| 선언 | 원본 근거 | 없을 때 |
| --- | --- | --- |
| BYTE `10fdae` := 2(demo) 또는 3(title) | `8a4` 분기(0 init, 1 eye-catch, 2 `950`, 3 `964`) | 0/1이면 `c00444` |
| 장치: BYTE `320000` 읽기 = 1(Z80 응답) | `10d6..10f4` handshake 루프(8000회) | `7cee` := `ff`, `11b4` "M1-ROM ERROR" 화면 |
| 장치: WORD `3c0002` 읽기 ≠ `8b55`(선언 0) | `1336`이 `7fff8b55`를 쓰고 `10c8`에서 다시 읽는다. `8b55`+`74ab` = 0이면 `7cef` = 0 | `1260` "WARNING THIS ROM CARTRIDGE IS FOR USE WITH ORIGINAL SNK…" 무한 루프 [I: 원본 하드웨어 확인] |
| BIOS `c0045c`(calendar, `1302`), `c004c2`(FIX_CLEAR, `1100`): RTS 선언(PC := (A7), A7 += 4, 출력 없음) | BIOS 호출 | fetch-unmapped |
| bank 창 WORD 쓰기 `25fff0` := `a`(`874`) 무시(기록) | `866..87c` | Unicorn write-protected |
| 장치 읽기 `3c0006`(`9a4`) = 0, `300000`(`2634`) = `ff`, `380000`(`1322`) = `ff` | 일반 읽기 | — |

- [F] 결과: 고유 TB 160개, 실행 TB 68,542개, port 35,069건 뒤 `2ab8`에 닿는다.
  - node: `100820` = `e4a`, `1008e4` = `c52a`, `100b30` = `100bf4` = `100cb8` = `100da8` = `270e`. 연결은 `100820`→`1008e4`→`1009a8`…
  - BYTE `10fd80` = `80`(`a1e`), `10fdaf` = 1, `10f007` = `ff`, `100017` = 2. LONG `104ca4` = `10f300`(자연 A7).
  - [F] F6-D의 P1 준비(`3dce`, `c42`, `10fd80` |= `80`)는 이 boot 경로(`974..a1e`)가 자연적으로 하는 일이다.
- [F] B 계열 frame 실행(`p4_bootframes.py`):
  - **frame 0 선언:** boot 상태 PC `2ab8`, A6 `100820`을 PC := `2ac2`, A6 := `1008e4`, A7 := `1ff000`, LONG `104ca4` := `1ff000`으로 바꾼다. 곧 D1의 SPd stack rebase다. N0은 idle node만 돌고, frame 1의 H가 첫 `e4a`, C가 `c52a`다.

  | 구성 | 결과 [F] |
  | --- | --- |
  | `10fdae` = 2, IRQ 없음 | 300 frame 동안 `c560` 대기(D9 (iii)와 같음) |
  | `10fdae` = 2, IRQ | frame 2 `c5f4`, 230 `c608`, 379 `c654`(replay 설치), 380 `c66a`. stage `478de`→`47af0`→`47bfc`→`47c6c`(406). frame 577에서 native 정지. IRQ 1,154회는 모두 `ef2`이고 모두 정상 복귀 |
  | `10fdae` = 3, IRQ, 입력 없음/`menu` | 1,500 frame `c6f4` title 대기(start bit만으로는 시작하지 않음. 시작은 BIOS PLAYER_START 몫) |
  | `10fdae` = 3, IRQ, `walkfire`, BYTE `10fdaf` := 2 @100 | `c6f4`→`c79a`(20)→`c82e`. 게임이 `10fdb6` := 1(frame 121)을 스스로 쓴다. 플레이어 192, mission 시작 `47c6c` 337, 사망·game over(`10fdb6` = 3) 578, `c940`, frame 906 `c00444` 종단. 새 PC 1,180개 |
  | 같은 구성 + BYTE `10f006` := 1 @100 | `c79a`를 거치지 않고 `c82e`(frame 100). frame 882 종단. 1,154 PC |

  - frame 577 정지 원인: `aea68 MOVE.W #2,82(A0)`에서 A0 = `aea38`(ROM)이라 ROM `aeaba`에 쓴다 [F]. 원본 하드웨어에서는 ROM 쓰기가 무시될 것으로 본다 [I]. 원본 bug인지, boot 선언의 차이 때문인지는 [U]다.
- [F] B 계열의 첫 미routing은 frame 2의 intro/title 객체다(demo `de024`, title `de376`). 따라서 C++가 일치하는 구간은 frame 0~1이다. intro·title·캐릭터 선택 객체(`de0xx`..`df2xx`, E 영역)를 routing해야 B 계열이 C·D까지 열린다.
- **판정:** (c)는 선언이 적고(장치 응답 3 + BIOS RTS 2 + 쓰기 무시 1 + 요청 1 + frame 0 rebase), 이후는 원본 code와 선언 IRQ뿐이다. 그래서 가장 자연스러운 공급원이다. boot snapshot 자체는 native 산출물로 쓰고, boot code(`852..a26`)의 C++ 이식은 E 영역 단위로 둔다.

## 4. 결정 항목(메인 결정 필요)

1. **seed 계열 두 개(S, B)를 같은 관측기·같은 기록 형식으로 둔다.** S는 즉시 C·D frontier, B는 E frontier이자 장기 주 공급원이다.
2. **player start 선언.**
   - S: BYTE `10f006` |= 1(P1) @frame 1. `a74`의 `OR.B` 효과다. 2인용은 bit 1로 option.
   - B(title): BYTE `10fdaf` := 2 @frame F. title 상태(`10fdaf` = 1, `10fd82` = 0, `f004` = 3)에서 `a74`를 처음 부른 효과이고, 그 뒤 원본이 `10fdb6` := 1을 쓴다.
   - 관측기는 같은 pre-state에서 `a74`를 native로 실행해(`10fdb4` := 1, RTS까지, 레지스터 버림) RAM 변화가 선언과 같은지 교차 확인한다(P1 준비의 `P1_EXPECT`와 같은 방식). 선언 기록에 이 결과를 남긴다.
3. **S 기본 입력 스크립트에는 start/coin bit를 넣지 않는다.** start는 `c79a`에서 BIOS 종단을 부른다(§3.1 B). start 스크립트는 guard 시험 구성으로만 둔다.
4. **frame 모델 = D1 + C Execute + IRQ 실행(F6-D) + palette RAM.** S는 게임 mode 선언(ii)과 P1 준비를 쓰고, B는 둘 다 쓰지 않는다(boot가 자연적으로 만든다).
5. **B의 stack rebase(A7 `10f300` → SPd `1ff000`)는 선언으로 둔다.** C++ 구동기는 SPd를 `1ff000`으로 고정해 검사하기 때문이다. 대안인 SPd 인자화는 public header 변경이라 메인 승인이 필요하다(§9).
6. **ROM 쓰기**(B demo frame 577)는 v1에서 checked native 정지 `rom-write`로 둔다. "무시 후 기록" 의미로 바꾸는 것은 C++ 실행부 결정이라 별도로 정한다.

## 5. 관측 protocol

### 5.1 frame 모델

- frame 0: N0. S는 seed 그대로이고, B는 §3.3의 frame 0 선언 상태다.
- frame k ≥ 1:
  1. host 쓰기(선언, 해당 frame만)
  2. H
  3. C(controller Execute, stop `2ac2` & A7 = SPd)
  4. N
- 대기 처리: H·C·N 모든 구간에서 `ef2`/`16bd0`/`cda4`/`3aea`/`47af0`/`478de` 대기에 IRQ를 1회 전달한다(F6-D 규약: `c0044a` 선언 resume, RTE 모사, 레지스터 복원 확인, 구간당 16회). card `c00468`(`c37c`/`c316`)는 선언 resume이다.
- IRQ 장치 값: BYTE `320000` = 0, WORD `3c0006` = 0(`irq_z80_reply`/`irq_video_status`). 실제 값은 [U]다.
- C++와 같은 구성: `AnimationFrameOptions{card_resume=true, card_answer=80, controller_mode=Execute, irq_execution=true}`와 palette RAM overload.

### 5.2 입력 선언 형식

- 버전 있는 JSON 파일 `docs/analysis/data/io-input-scripts.json`(`format "ms5-io-input-script"`, `version 1`).
- 이름마다 기본값 `{"380000":"ff","300000":"ff","340000":"ff","3c0006":"0000"}`과 구간 목록 `[{"from":F0,"to":F1,"port":"300000","value":"f7"}, …]`을 둔다. 주기 패턴은 `{"every":N,"phase":[a,b]}`로 적는다.
- 확장 결과(frame별 4값)의 SHA256을 기록에 남긴다.
- **의미:** frame k에 그 port를 몇 번 읽든 같은 값이다. pause 루프의 반복 읽기도 같다.
- **C++에 넘기는 것은 native 소비 기록이다.** native H·C·N의 장치 읽기 log를 소비 순서 그대로 `(address,size,value)` 목록으로 만든다. mode 0 정상 frame이면 7건이고, IRQ 안의 읽기는 빠진다.
- 관측기는 이 목록이 스크립트 값과 같고, 순서가 H2 계약 순서(`3c0006 3c0006 380000 300000 340000 300000 340000`, pause 반복 시 반복)인지 검사한다.
- mode 1(replay) frame은 H2 계약대로 입력 port 소비가 0건이어야 한다. mode ≥ 2이면 앞 3건이다. 관측기는 frame마다 `104cd4`와 소비 수를 짝지어 기록한다.

### 5.3 seed 집합과 구성

| 계열 | 구성 | seed | frame |
| --- | --- | --- | --- |
| S | `P0` 대조: 게임 mode, 입력 `ff` | 136 자연 seed(case 141은 frame 0 정지 기록) | 600 |
| S | `P1` 주 구성: 게임 mode + `10f006` \|= 1 @1 + `walkfire` | 136 | 600 |
| S | `P1b`: P1 + `10f006` \|= 2(P2) @1 | 동치류 대표 14(§3.1) | 600 |
| B | `boot-demo-0`: `10fdae` = 2, 입력 `ff` | 1 | 끝까지(최대 2,000; 탐침 577 정지) |
| B | `boot-title-start`: `10fdae` = 3, `10fdaf` := 2 @100, `walkfire` | 1 | 끝까지(최대 2,000; 탐침 906 종단) |
| B | `boot-title-idle`: `10fdae` = 3 | 1 | 600 |

- 비용 [F]: 탐침 S P1은 136 seed × 600 frame에 3 worker로 약 9분, B는 실행당 10~20초다.

### 5.4 반복·분할 검사

- 모든 구성을 continuous로 두 번 실행한다.
- 8 seed(동치류 대표)와 B 3개는 fresh-CPU split으로도 두 번 실행한다. split은 frame마다 기록된 frame 시작 상태에서 새 CPU로 실행한다.
- 네 결과의 frame별 digest가 같아야 한다.
- 두 전체 실행은 서로 다른 디렉터리에 쓴다. 비교 필드의 `observation.json` SHA가 같고 `diff -rq`가 깨끗해야 한다(플랫폼 필드 파일은 제외).

### 5.5 frame별 기록(비교 필드)

- **구간 경계 상태:** H·C·N 시작과 끝, IRQ 전후의 전체 상태 SHA256이다. 입력은 RAM 64 KiB, D0~D7, A0~A7, PC, bank base, PVC page 8 KiB, palette bank 2개와 선택, status byte.
- **frame 내용:**
  - 순서 있는 port(head, controller, node, irq)의 SHA와 개수
  - 대기 기록, IRQ 기록(구간, 대기 PC, 결과, 읽기 수, BIOS resume, RTE SR)
  - 외부 읽기 소비 목록(그대로)
  - host 쓰기
  - controller 진입·종료 callback, 정지 종류
- **진행 필드:**

  | 필드 | 주소 |
  | --- | --- |
  | stage controller callback | `100b30` |
  | 플레이어 callback | `100cb8`/`100da8` |
  | 카메라 | `10d3bc`/`10d3c0`/`10d3a2` |
  | mission/area | `10d680`/`10d681`/`10d686` |
  | BIOS 플레이어 상태 | `10fdb6`/`10fdb7` |
  | 입력 mode·replay cursor | `104cd4`/`104cce` |
  | 입력 블록 | `104ca8..104cbd` |

  pass별 node callback 목록도 기록한다.
- **실행 TB 목록:** frame별 고유 `(phase, addr, size)`와 횟수다. frontier 용이다.
- **전체 dump:** gzip blob으로 둔다. 대상은 frame 0·1·2, 첫 미routing frame과 그 직전 frame, 정지 frame, 구성별 마지막 frame, 각 seed의 player 생성 frame, B 계열 controller 전환 frame이다. C++ 비교는 frame 시작 상태가 필요하므로 **모든 frame 시작 상태**를 blob으로 둔다. 같은 RAM은 SHA로 중복을 제거하고 page 단위 delta를 쓴다.
  - 예상 크기 [I]: S 136 × 600 frame × (64 + 8 + 16 KiB)에 delta 압축을 하면 약 1~2 GB다. 상한 3 GB를 넘으면 동치류 대표만 전체를 남긴다.

### 5.6 guard(checked 정지, 상태 보존, 이유 기록)

- BIOS fetch: `c00444` → `system-return`(종단, 정상 종료로 집계). 선언 밖의 BIOS PC → `bios-boundary`.
- ROM 쓰기 → `rom-write`(§4.6).
- 그 밖: odd PC·odd data, unmapped, Unicorn 예외, 구간 step 한도(H/N `S.PASS_LIMIT`, C 2,000,000), `wait-not-released`(> 16), IRQ 실패(`bios-int1`, `internal-wait`, `regs-differ`, `undeclared-read`).
- 입력 관련: 외부 읽기 queue 비어 있음, **N·C 구간의 입력 port 직접 읽기**(`undeclared-device-read`; 탐침 0건), mode와 소비 수 불일치.
- head·menu callback guard(`f3c`, `931a`).
- B boot 단계의 선언 밖 장치 읽기와 BIOS 호출은 boot 실패다.

### 5.7 플랫폼 독립 기록

- `observation.json`에는 **비교 필드만** 둔다.
  - 입력 pin: ROM SHA, seed observation SHA, 입력 스크립트 확장 SHA, 이 문서 SHA, 관측기와 import한 저장소 도구 파일의 SHA, routing 파일 SHA.
  - 선언 목록, 구성, frame별 기록, 집계.
  - 최상위 `compared_sha256`은 위 필드의 정규 JSON(`sort_keys`, 공백 없음)에 대한 SHA다.
- `platform.json`(비교 제외): Unicorn·capstone 버전, 라이브러리 경로·SHA, Python 버전, OS/arch, worker 수, 경과 시간, 생성 시각.
- **역사적 실패의 원인을 피한다.** 그때는 보고서에 Unicorn 라이브러리 SHA가 들어가 다른 OS에서 바이트 재현이 되지 않았다. 그래서 다른 플랫폼 재생성은 `compared_sha256`이 같은지로 판정한다.
- 관측기는 저장소 도구를 수정하지 않고 import만 한다. 사용하는 기존 도구 파일의 SHA를 pin하고 assert한다.

## 6. C++ 비교와 frontier 보고

### 6.1 queue 공급과 frame 비교

- 각 native frame마다 C++ harness `frame_io_acceptance`에 다음을 넘긴다.
  - native frame 시작 상태(선언 host 쓰기를 적용한 뒤, controller 검증기 `start_override`와 같음)
  - queue = native H 소비 + C 소비 + N 소비(소비 순서)
  - IRQ option, palette
- 호출은 `step_animation_machine_frame`(Execute + IRQ)이고, frame 0은 `run_animation_machine_pass`다.
- 어긋난 위치를 찾기 위해 controller 구간 단독(mode 3)과 N 단독(mode 0)도 실행한다.
- **"일치"의 정의:** 다음이 모두 같고, C++가 queue를 남김없이 소비해야 한다.
  - RAM 64 KiB, 레지스터 16개, PC, bank base, PVC page
  - palette bank 2개와 선택
  - 구간별 순서 있는 port(MOVE.L `3c0000` 분할 어댑터는 D1과 같음)와 IRQ port
  - 대기 기록, IRQ 기록
  - 구간별 외부 읽기 수
  - head/controller/controller exit/pass stop PC
  - carry Unknown
- native에서 frame이 끝나지 않은 경우(guard)에는 C++가 대응하는 checked 오류를 내고 상태를 보존해야 한다. 대응표는 D1·controller·IRQ 검증기의 `NATIVE_END_ERROR`에 `rom-write`를 더한 것이고, 문자열은 구현 때 정한다.
- **C++ 단독 연쇄:** seed마다 C++ 출력만 이어 붙인다. 각 frame에는 선언 host 쓰기와 native 소비 queue만 더한다. 연쇄는 첫 C++ 실패 frame까지 가며, 두 번 실행해 같아야 한다.

### 6.2 frontier 위치 확정(V1 `check_fail_pc` 방식)

- frame F에서 native는 끝났는데 C++가 `unsupported animation machine PC`(또는 실행부 고유의 "unsupported … PC")로 실패하면 frontier를 찾는다.
- 후보 P: frame F native 실행 순서의 TB 안 명령 시작 PC 가운데 처음으로 `pc_routed(P)`가 거짓인 것. 평가기는 `verify_animation_machine_unit_fixtures.pc_routed`이며 import해서 쓴다.
- 확정 조건(V1 리뷰 0264 L-1과 같음): 같은 입력에서 C++를 stop = P로 실행하면 성공하고 정확히 P에서 끝나야 한다. 확정되지 않으면 다음 후보로 넘어간다. 함수 단위 실행부의 내부 PC가 이 단계에서 걸러진다.
- 기록: seed, 구성, frame F, 구간(H/C/N), P, P 진입 시 LONG(A7)(호출자 복귀), 현재 node A6과 그 callback.

### 6.3 frontier 보고

- **입력:** 위 확정 frontier와, frontier frame 이후 native 실행에서 처음 나타난 모든 미routing PC(실행 순서 무관, 횟수)다.
- **묶음:** P를 함수 root로 묶는다. root는 고정 ROM의 정적 call 대상과 code 포인터 대상 가운데 P 이하에서 가장 가까운 것(`0x1000` 이내)이다(근사 [I]).
- **root별 값:**
  - (a) frontier로 처음 걸린 seed·frame 수
  - (b) 실행 횟수, 고유 PC, seed 수
  - (c) 정적 closure: 분기 + JSR/BSR + fall-through이고 routing된 PC에서 멈춘다. leader·명령·바이트, 포인터 수, 미해결 간접 수.
  - (d) 영역 C/D/E [I]: 주소대로 C = `1b000..23fff`·`4e4c0..4f3ff`, E = `de000..df3ff`·`e6400..e6fff`·`c000..cbff`·`<1400`, 나머지 D. 단위 계약에서 다시 확인한다.
- **후보 단위:** 같은 영역에서 호출 관계로 이어진 root를 묶는다. 순위는 frontier seed 수, 그다음 실행 횟수다.
- **산출:** `frontier.json`과 문서 표.
- [F] 탐침 기준 상위 root(S P1, 기준선 제외):

  | root | 영역 [I] | 실행 | PC | seed | 직접 closure leader/명령/바이트 |
  | --- | --- | --- | --- | --- | --- |
  | `768b6` | D | 91,482 | 35 | 23 | 47 / 137 / 640 |
  | `b4958` | D | 78,991 | 15 | 23 | 108 / 298 / 1,064 |
  | `4e94e` | C | 70,928 | 45 | 12 | 502 / 1,226 / 4,654(캐릭터 선택 `4e732` 계열과 같은 closure) |
  | `1cd98` | C | 51,616 | 18 | 12 | 45 / 106 / 428 |
  | `c01a8` | D | 49,392 | 17 | 23 | 138 / 375 / 1,386 |
  | `de8bc` | E | 46,140 | 3 | 12 | 3 / 3 / 14 |
  | `7343a` | D | 28,160 | 18 | 11 | 74 / 190 / 748 |
  | `df15e` | E | 26,540 | 16 | 12 | 30 / 77 / 318 |
  | `730a6` | D | 8,745 | 15 | 11 | 115 / 310 / 1,292 |
  | `70c76` | D | 11,604 | 34 | 23 | 86 / 193 / 684 |

  - 영역 합계(root/실행/PC): D 226 / 742,798 / 1,211, C 61 / 350,392 / 395, E 41 / 189,680 / 258.
  - 첫 frontier PC(seed 수): `de660` 12, `b3dbc` 11, `e5324` 11, 그 밖 2개씩 9개.
  - 플레이어 root `1d1f4`의 직접 closure: leader 1,381, 명령 3,122, 13,244바이트. 포인터를 따라가면 3,695 leader다.

## 7. 단위 IO 성공 기준

1. **관측(IO-1):**
   - S 136 seed × 600 frame × {P0, P1}, S 대표 14 × P1b, B 3구성을 continuous로 두 번 관측해 `compared_sha256`이 같고 `diff -rq`가 깨끗하다.
   - 대표 8 seed와 B 3개는 split 두 번도 frame별 digest가 같다.
   - P0이 D9·IRQ의 기존 결과와 맞는다: 136 seed 완주, `c7fc`→`c79a`, 새 미routing 0(`3900` 제외).
   - P1에서 플레이어를 만든 seed ≥ 12, 새 미routing PC ≥ 1,500(탐침 1,864).
   - B demo는 `104cc4` = `f07fe`, `104cd4` = 1. B title-start는 `10fdb6` = 1, 플레이어 생성, `c00444` 종단.
   - 입력 소비 순서 검사 0 위반, ROM SHA·mtime 불변, 산출 크기 < 3 GB.
   - guard 종류별 typed fixture가 1개 이상 있다: start bit의 `c79a` 종단, N 입력 읽기 합성, queue 부족, ROM 쓰기(B demo frame 577), BIOS 밖 호출.
2. **C++ 비교(IO-2):**
   - 모든 seed·구성에서 frame 0부터 첫 frontier frame 직전까지 native 완료 frame이 C++와 전부 일치한다(불일치 0).
   - frontier frame에서는 C++가 checked 오류를 내고 상태를 보존하며, fail PC가 §6.2로 확정된다.
   - C++ 단독 연쇄가 같은 frame 수만큼 일치하고, 두 번 실행해 같다.
   - native guard frame은 대응하는 C++ checked 오류와 짝을 이룬다.
   - 부정 검사: RAM 1바이트, queue 값·순서·개수, host 쓰기 누락, IRQ option, 결과 위조를 모두 검출한다.
   - 검증기를 두 번 실행하면 JSON SHA가 같다. `make -j4 all test` 종료 코드 0.
   - 기존 frame 검증기(D1, controller game/demo, IRQ, head)와 0267 manifest 회귀가 그대로 PASS다.
3. **frontier 보고:** §6.3 표를 C·D·E 후보 단위(root 묶음, 정적 closure)로 정리한다. 다음 C·D·E 단위 범위 문서의 입력이 된다.

## 8. 구현 분할

| 하위 작업 | 작업자 | 담당 파일 | CLI | 산출 |
| --- | --- | --- | --- | --- |
| IO-1 관측기 | Sonnet / high | `tools/observe_animation_machine_io.py`, `docs/analysis/data/io-input-scripts.json`, `docs/analysis/animation-machine-io-observation.md` | `.venv/bin/python tools/observe_animation_machine_io.py --family stage\|boot\|all --config P0,P1,P1b,boot-demo-0,boot-title-start,boot-title-idle --frames 600 --workers 3 --out DIR [--seed-dir PATH] [--split-cases LIST]` | `DIR/observation.json`(비교 필드), `DIR/platform.json`, `DIR/blobs/`, `DIR/boot/`(boot snapshot과 boot 선언 기록). 기본 DIR `artifacts/animation_machine_io_native` |
| IO-2 C++ 비교 + frontier | Sonnet / medium | `tools/verify_animation_machine_io.py`, `engine/tools/frame_io_acceptance.cpp`, Makefile 항목(harness 빌드만), `docs/analysis/animation-machine-io-execution.md` | `.venv/bin/python tools/verify_animation_machine_io.py --observation DIR/observation.json --workers 3 --out DIR2 [--no-build]` | `DIR2/verification.json`, `DIR2/frontier.json`. 기본 DIR2 `artifacts/animation_machine_io_execution` |

- IO-1 구현 지침:
  - controller·IRQ 검증기의 native 클래스를 import해 합성한다. 탐침 `ioprobe_lib.X`가 원형이다.
  - `script_queue`는 monkeypatch하지 말고, 관측기 안의 하위 클래스에서 `run_head`의 queue를 만든다.
  - boot는 `p3_boot.py`의 선언을 그대로 정식화한다.
  - 선언 목록(`declared`)마다 이유와 원본 근거 주소를 둔다.
  - `engine/`·기존 `tools/` 파일은 고치지 않는다.
- IO-2 구현 지침:
  - harness는 `frame_controller_acceptance.cpp`와 `frame_irq_acceptance.cpp`를 합친 packet이다(Execute + IRQ + palette).
  - `engine/src` 실행부는 바꾸지 않는다. 결함을 찾으면 근거와 함께 보고한다.
- 순서: IO-1 → IO-2. IO-2는 IO-1 산출 형식이 확정되면 harness와 packet 작업을 먼저 시작할 수 있다.

## 9. 미확인·열린 질문

1. [U] 실제 BIOS의 PLAYER_START 호출 시점과 횟수. AES/MVS(`10fd82`)별로 다르다. title에서 `a74`를 처음 부르면 `10fdaf` := 2만 쓰고, 그 뒤 원본이 `10fdb6` := 1을 쓰는 것은 확인했다(§3.3). S에서 `10f006` 선언이 실제 두 번째 호출과 같은지는 추론이다.
2. [U] boot 장치 응답(`3c0002` 읽기 값, Z80 응답 시점, calendar 값)과 SR `2700` 진입 가정. BIOS가 boot 전에 RAM을 어떻게 초기화하는지도 모른다(탐침은 0 RAM).
3. 메인 결정 필요: B의 SPd rebase를 선언으로 할지(A7 `10f300` → `1ff000`이고 stack 바이트 위치가 다름), 아니면 구동기 SPd 인자화(public header 변경)로 할지.
4. 메인 결정 필요: ROM 쓰기(`aea68`, A0 = `aea38`)의 의미. 원본 bug인지, 선언 boot 차이인지 [U]. 무시 의미를 채택하면 C++ 실행부도 같이 바꿔야 한다.
5. [U] IRQ 장치 값(`320000` = 0, `3c0006` = 0)이 고정 상수다. raster·vblank 실제 값과 시점은 미확인이다.
6. [I] 미routing 판정 근사(단일 PC 실행부의 함수 내부 closure 포함)와 영역 C/D/E 주소 분류. IO-2는 `pc_routed`와 C++ stop 확정을 쓰므로 이 근사는 순위에만 영향을 준다.
7. [U] S 85 seed에서 600 frame 안에 새 code가 없는 원인. 플레이어가 없어 카메라가 멈춘다는 추론 [I]이다. P1b(2인)나 더 긴 frame으로 바뀌는지 확인하지 않았다.
8. [U] Execute + IRQ 조합의 C++ 동작은 원본 비교가 없다(IO-2가 처음 확인한다).

## 10. 탐침(scratch, 재현용; 저장소에 넣지 않음)

`/Users/start/Workspce/ms5-scratch/io1/`(SHA256 앞 16자리):

| 파일 | SHA256 앞 16자리 | 내용 |
| --- | --- | --- |
| `iocommon.py` | `bfdf8ecc6d946e93` | 공통 설정 |
| `ioprobe_lib.py` | `6c64c89df72c6756` | Execute + IRQ 합성 클래스, 스크립트, routing 근사, 정적 closure |
| `p0_seedfields.py` | `c0eaf6109b942091` | seed 필드 |
| `p1_input_probe.py` | `f9ace773f0c62c2b` | §3.1 구성 A~E |
| `p3_boot.py` | `b47e631581dfbc36` | BIOS 없는 boot |
| `p4_bootframes.py` | `6833f0be6c2b08dc` | B 계열 frame |
| `p5_allseeds.py` | `290eb1fdf82f3c2e` | 전 seed |
| `an5.py` | `ac27e6c185ad6631` | 집계 |
| `m68dis.py` | `8f0350d52f9ab974` | 디스어셈블 보조 |
| `xref.py` | `ae248672e918246a` | 교차 참조 |

출력:

| 파일 | SHA256 앞 16자리 |
| --- | --- |
| `out/r3/all_P0.json` | `17bc65cf01328ae4` |
| `out/r3/all_P1.json` | `68ffffd2780295bc` |
| `out/r3/all_P1rep.json` | `15737b3ad7a3f471` |
| `out/r2/boot_d2irq3k.json` | `b484e2e7c8609dfe` |
| `out/r2/boot_d3start.json` | `8856ce444f69774d` |
| `out/r2/boot_d3fdafonly.json` | `62b3054556bc02d2` |
| `out/r1/result_C.json` | `0c629f3e3675853f` |

재현 명령(작업 트리 루트, `MS5_SEED_DIR=artifacts/stage_entry_body`):

```sh
.venv/bin/python …/io1/p5_allseeds.py --frames 600 --script walkfire --declare game,10f006:1:1@1 --irq --workers 3 --out …/out/r3 --tag _P1
.venv/bin/python …/io1/p4_bootframes.py --fdae 3 --frames 1500 --irq --script walkfire --declare 10fdaf:1:2@100 --out …/out/r2 --tag _d3fdafonly
.venv/bin/python …/io1/an5.py …/out/r3/all_P1.json …/out/r3/all_P0.json 40
```
