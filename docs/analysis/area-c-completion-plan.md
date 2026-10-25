# 주 영역 C(플레이어)·E(캐릭터 선택) 완료 계획 — 현재 IO 관측 집합 기준

작성: 작업자 Claude Opus 5.5 / high(메인 지시, 2026-10-22). 기준 커밋 `92dbff7`(main, FR3~FR9 병합, 영역 D routing 완료), branch `claude/area-c-plan`. 전체 범위·완료 기준은 `docs/GOAL.md`를 따른다. 이 문서는 GOAL의 범위를 줄이지 않는다. 여기서 "C 완료"는 **현재 IO 관측 집합에서 실행된 C·E 코드**에 대한 중간 완료 정의다. 다른 입력·스테이지 진행으로만 실행되는 플레이어 코드는 남는다(§4.3, §7).

표기: [F] 원본 바이트·현재 소스·관측 기록에서 센 사실, [I] 추론·추정, [U] 미확인. 수치는 scratch `/Users/start/Workspce/ms5-scratch/c1/` 도구로 다시 만들 수 있다(§6). ROM `extracted/program/maincpu.decrypted.be.bin` SHA256 `29112a94…c860f`. 이 문서의 코드 주소는 모두 `<100000`이라 CPU 주소와 파일 오프셋이 같다. bank 창 읽기(`2001e4`)만 CPU 주소이고, 물리 오프셋은 `bank_base + (주소 − 200000)`이다.

메인 결정(Claude Opus 5.5, 2026-10-22):
- §2 관측 보정을 받아들인다. 원래 관측과 보정 관측의 native 기록이 18 run 모두 같다는 것을 메인이 `reobs_check.py`로 다시 확인했다.
  - 계획용 실행 집합은 scratch `ms5-scratch/c1/reobs/`를 쓴다. 공유 `artifacts/`는 고치지 않는다.
  - IO 비교의 기준은 native 기록이고, 그 기록이 같으므로 비교에 쓰는 관측은 바꾸지 않는다.
  - observer의 정확 bitmap 방식과 "단일 PC 실행부가 closure를 덮는다" 설명 수정은 C1 단위에서 코드·문서로 한다. 다시 관측한 결과를 `artifacts/`에 둘지는 사용자 승인 뒤에 정한다.
- §5 결정 2~11은 작업자 권고대로 한다.
  - 결정 7: 단위 이름은 C1~C13, E1로 둔다. 파일 접두어는 `player_c1`(C++), `pc1.py`(fixture spec)로 해서 controller 단위 C1~C3과 겹치지 않게 한다.
- 순서는 C1, E1, C2, C3, C4, C5, C6, C7, C8이다. C9~C13은 C8 뒤에, 입력을 늘린 관측이 생기면 다시 잰다.

## 1. 정의

- **관측 집합** [F]: D 계획 §1과 같다. native IO 관측 `artifacts/animation_machine_io_native`(`observation.json` SHA256 `66d30130d8a11a86…`)의 run 296개를 쓴다.
  - C·E 코드를 실행하는 run은 18개다: P1 12(case 68~71, 94, 95, 100, 101, 106, 107, 110, 111), P1b 2(68, 94), boot-title-start, boot-demo-0, fixture fx-c-input-read와 fx-n-input-read(`2622`만).
- **관측 보정** [F]: 역사 관측은 일부 실행 PC를 기록하지 않았다(§2).
  - 이 계획은 C·E run 18개를 정확한 routing bitmap으로 다시 관측한 기록 `ms5-scratch/c1/reobs/`로 실행 집합을 정한다. 원래 기록 대비 native 기록은 같다.
  - 메인이 이 보정을 받아들이는 방식은 §5 결정 1이다.
- **C 완료(이 관측 집합)**: 다음이 모두 참이다.
  1. 관측 집합의 어느 run이든 native가 실행한 routing 밖 PC 가운데 영역 C로 분류되는 것이 **모두 현재 dispatch 사슬로 routing**된다(C 남은 실행 PC = 0). 여기서 실행 PC는 보정 관측 기준이다(§2).
  2. IO 비교를 다시 돌렸을 때 어느 run의 첫 정지(첫 C++ 실패 PC)도 영역 C가 아니다. 불일치 0, 예상 밖 C++ 오류 0, 두 번 실행 결과 동일.
  3. 각 단위가 단위 검증(단위 시험, UBSan, 변이, 실제 ROM 차분, V1, frame 회귀, IO 비교)을 통과한다.
  - 영역 분류는 D 계획 §2(IO-1 `area_of` + 호출자 재분류)를 그대로 쓴다. D에서 C로 옮긴 helper 19개도 C다.
- **E와의 관계** [F]: E 캐릭터 선택(`de8bc`..`df2c0`, helper `18364`)은 C 첫 정지 run 15개에서 같은 순서로 끼어 실행된다.
  - 각 run의 첫 C·E frame을 기준(+0)으로 보면: `4e68e` 첫 frame(+0~+1) → E(+3~+62) → C 플레이어 생성(+64~+73) → E(+98~+134) → C 플레이어 본체(+186/+190~)(§3.3).
  - 그래서 IO 진척에는 C와 E가 모두 필요하다. C1만 연결하면 +45 frame, C1과 E1을 함께 연결하면 +3,430 frame이다(§4.2).
  - **E 단위는 이 계획에 넣는다(E1).** 이유: (1) C와 같은 run, 같은 frame 사슬에서 번갈아 첫 정지가 된다. (2) E 실행 PC 220개의 closure가 222 block으로 한 단위다. (3) E 주소 범위의 `4e68e` helper(`ca50` `ca3a` `b0c` `e6496`)는 C 단위에 둔다(§5 결정 6).
  - E 완료는 이 관측 집합에서 E 남은 실행 PC = 0, E 첫 정지 0이다. boot·데모·크레딧 등 다른 E 코드는 범위 밖이다.

## 2. 관측 보정: 역사 관측이 기록하지 않은 플레이어 코드

- [F] 관측기(`tools/observe_animation_machine_io.py` `native_setup`)는 TB마다 "routing bitmap 밖인 첫 명령"을 기록한다.
  - 이 bitmap(`routed2`)은 관측 당시 routing(`8ce8eb93`, git `ae4c486`)의 원자에 **단일 PC 원자의 함수 안 분기 closure를 더한 것**이다(코드 주석 "single-PC executors cover their intra-function closure [I]").
- [F] 단일 PC 원자 78개 가운데 `1dc84`의 closure가 C closure 안에서 1,894 명령을, `210ae`가 17 명령을 덮는다(둘을 합쳐 1,911 명령, 22 범위 `1d222..2156a`).
  - 현재 C++에서 `1dc84`/`1dc8a`/`210ae`/`210b4`는 interpreter 호출 stub다(`animation_machine_interpreter.cpp:160-164`: `JSR 49fc6` 뒤 C로 `1dccc`/`1dc8e`를 고르고 dispatcher로 돌아감). 따라서 그 closure를 덮지 않는다.
  - 결과: 그 범위에서 실행된 플레이어 코드는 역사 기록에 없다.
- [F] 증거:
  - 역사 기록에는 `20796`(BRA.W 표 칸)이 실행 PC로 있다. 그런데 그 `JMP 20792`와 이를 포함한 `20738..20792`는 어떤 TB의 첫 routing 밖 명령으로도 기록되지 않았다.
  - node callback 기록(frame 기록 `N.cbs`)에는 routing 밖이면서 기록되지 않은 callback 6개가 있다: `1edb0`(14 run, P1 94의 frame 193부터), `1ef0e`(14, frame 219), `20738`(9, frame 392), `1ebf6` `1f6da` `1fb02`(boot-demo).
  - P1 94: frame 192에 player node callback이 `1d1f4`로 다시 들어가고, 같은 frame에 `1d21c BCS 1d222`(가려진 코드)가 실행돼 `1edb0`을 설치한다(scratch `cbseq.py`).
- [F] **재관측**(scratch `reobs.py`): 관측기를 수정 없이 import한다.
  - pin 검사를 통과하도록 `ROUTING_FILE`만 scratch에 둔 관측 당시 사본(SHA256 `8ce8eb93…`)으로 바꾼다.
  - `routed2`는 현재 routing(`7233eefc…`, `hroute.routed`)이 routing하는 PC 정확히 그대로로 바꾼다.
  - C·E run 18개를 다시 돌렸다: 99초, 출력 `reobs/observation.json` SHA256 `02b87c20eca2164c…`, `compared_sha256` `9a0ee011f703c12f…`.
  - **native 기록은 원래와 같다**(scratch `reobs_check.py`): 18 run 모두 frame 수가 같고, 미실행 PC 필드(`unr_new` `unr_n` `unr_first`)를 뺀 모든 frame 기록 필드와 summary가 같다.
    - 역사 기록의 대표 run 재실행에만 있는 상세 TB 목록 `tbs`는 비교하지 않았다. TB 수·hash `tb`는 같다.
- [F] 새로 보인 PC(scratch `hidden2.py`, 숨긴 원자별):
  - `1dc84`/`1dc8a` 210개, `210ae`/`210b4` 4개, 두 쪽 모두에 걸린 것 1개: 모두 C이고, 그 run의 역사 첫 정지 뒤에만 실행된다. 이 **215개가 C에 더해진다**.
  - 나머지 원자(`8c16` `16ed2` `287e` `3d44` `47c5a` `4aa06` `e90ca` 등, D 29 + E 2)의 새 PC는 31개다. 그중 29개가 역사 첫 정지 앞 frame(IO 비교가 일치한 frame)에서 실행된다. 그러므로 그 원자의 C++ 단일 PC 실행부는 closure를 실제로 덮는다. 31개 모두 routing된 것으로 취급한다.
    - 예외: `46efe`(원자 `46ef4`)와 `46f0c`(`46ef4`/`46f08`, D 주소)는 정지 뒤에만 실행된다. 같은 원자의 `46ef6`은 정지 앞에서 실행되므로 덮인다고 보지만 [U]다.
- [I] 영향:
  - 역사 기록만 쓰면 C 실행 PC를 215개 적게 센다. 그러면 `1d222` 뒤의 플레이어 상태 코드(약 1,000 block)를 "미실행"으로 오판해, IO 단위를 잘못 자를 수 있다(이 작업에서 처음 그렇게 계산했다가 고쳤다).
  - IO 비교 자체(C++ 대 native frame)는 이 기록에 의존하지 않는다. 예측 모형과 단위 계획만 영향을 받는다.

## 3. 재측정(현재 routing `7233eefce1281ff3`)

### 3.1 기준선 재현과 보정값

| 측정 | C 실행 PC | E 실행 PC | D | root(C/E) | 실행 수(C/E) | 예측 일치 frame | 첫 정지 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 역사 관측(메인 기준선 재현) | 620 | 220 | 0 | 99 / 35 | 467,085 / 315,862 | 165,714 | C/E 15, C 1 |
| 보정 관측(§2, 이 계획) | **835** | 220 | 0 | 118 / 35 | 619,427 / 315,862 | 165,714 | C/E 15, C 1 |

- [F] 예측 일치 frame 165,714는 IO 비교 실측(165,714, 불일치 0, native 비교 frame 173,966)과 같다. 남은 8,252 frame을 C·E가 연다.
  - A 묶음 9 run(P1 8 + P1b 94) × 598 + B 묶음 5 run(P1 68~71 + P1b 68) × 378 + title-start 784 + demo 196(guard 전까지)이다.
- [F] 첫 정지: `4e68e` 15 run(P1 12, P1b 2, boot-title-start). 같은 frame에 E `ca50`도 처음 실행된다(C/E). boot-demo-0 1 run은 frame 381의 `1d1f4`다(C).
- [F] 실행 PC 계열(scratch `cfam.py`):

  | 계열 | 실행 PC | root | 실행 수 | run | 처음(상대 frame) |
  | --- | --- | --- | --- | --- | --- |
  | `4e68e` 슬롯 callback(root `4e4c0..4f3ff`) + 부르는 helper(`ca50` `ca3a` `b0c` `e6496` `371e` `3786` `1be3a` `1bf94` `1c052` `1c086` `1c0b4` `4da08` `4e0f6` `b7a28`) | 225 | 34 | 234,608 | 15 | +0 |
  | 플레이어 객체 `1d1f4`와 helper(`1b000..23fff`, `361e4` `48346` `48384` `49bca` `4d0a4` `4d106` `4d1ac` `4de7a` `4de9c` `cddee` `e8b5a` `ea626` …) | 624(역사 409) | 88(69) | 393,480(241,138) | 16 | +64 |
  | E 캐릭터 선택(`de8bc..df2c0`, `18364`) + boot `2622` | 206 | 31 | 307,201 | 17 | +3 |

### 3.2 정적 closure

- [F] 실행 C·E PC(보정 1,055개)의 FR 규칙 closure: 시작 **2,727 block**, 6,101 명령. 설치 값은 실행된 것만 따라간다.
  - TB 분할 PC 26개는 진입에서 뺐다: 연속 명령 TB 시작 `1cfe4..1d002` `1dfec..1e000` `24fe2..25000` `defe2..df002`, 묶인 조건 분기 둘째 `b26` `21c30` `21e5a` `e64b4`.
  - LONG `84(A6)`에 쓰는 값 19개는 block 시작으로 강제했다(§4.1).
- [F] 특이 명령:
  - TRAP: `4e69a` 하나.
  - DIVU 8, MULU/MULS 13, MOVEM 12(E 4 포함), ADDX 2, SUBX 1.
  - RAM 실행 TB 0, bank 실행 TB 0(재관측 summary `ram_exec_tbs` `banked_tbs`). 자기 수정 코드 관측 없음.
- [F] 간접 분기:
  - BRA.W 계산 점프 표 5개(§4.1 표): `2031c`(9칸, 실행 0) `20792`(4, 실행 칸 `20796`) `2094e`(28, `2095a`) `209d6`(28, 0) `25298`(9, `252a4`).
  - (handler LONG, key WORD) 목록 조회 `215e6` + `JMP (A1)` 15곳. A1은 ROM 목록 `21622` `21688` `216c8` `21aee` `21b0a` `21b26` `21b3c`의 LONG이다.
  - live `JMP (A1)` `1aa38`.
  - `201a6 JSR (A4)`: A4 = LONG `84(A6)`, 플레이어 node의 둘째 callback 칸.
  - `3772`/`37d8 JSR (A1)`: A1 = `LEA 3650(PC)`, 고정된 routing 대상. DIVU 표는 `377a`의 WORD 1·10·100·1000·10000.
- [F] D 계획의 추정(플레이어 1,521~1,775 block, `4e68e` 484 block)은 설치 값을 전부 따라간 값이다. 이 계획은 실행된 설치 값만 따라간다.
  - 미실행 설치 값은 70개다. 그중 63개는 다른 경로로 closure 안에 있어 block 시작이 되고, 7개는 쓰기만 하는 정지다.

### 3.3 어느 run·frame에서 무엇이 실행되나

- [F] run 묶음(첫 C·E frame):
  - A = P1 94, 95, 100, 101, 106, 107, 110, 111 + P1b 94: frame 2.
  - B = P1 68~71 + P1b 68: frame 222.
  - boot-title-start: frame 122.
  - boot-demo-0: frame 381. 이 run에는 `4e68e`·E가 없다. stage 코드 `47772`/`1bd9c`가 `1d1f4`를 설치한다.
  - 묶음 사이 순서는 같다(scratch `cseq.py`).
- [F] 상대 frame(A 기준, B는 +186 등으로 4 frame 이르다):
  - +0~+1: `4e68e`(node `1009a8`·`100a6c`, WORD `76` = 0/1) → `4e732` `4e7ec` `4f32e`(`28ae` 자식 `4f2e0`), E `ca50`.
  - +3~+62: E `de8ca` `de8ee` `de97e` `deba4` `defdc` → `de8bc` `dec10` `df06c` … `df15e`.
  - +64~+73: `4e83c` → `4e94e`. `4e94e`는 `4e91c LEA 1d1f4; JSR 2a28`로 LONG `78(A6)` = `100cb8`/`100da8` node에 플레이어 객체를 만든다. `1d1f4` → `1d20c`(대기: `1d21c BCS` 안 함).
  - +98~+134: E 끝(`18364` `dee28` `def32` `defc0`).
  - +190~+193: 플레이어 본체(198+22+3 PC). `1d1f4` 재진입, `1d222`, `1edb0`, `20128`(`201a6 JSR (A4)`), `21688`, `1cd98` ….
  - +216~+217: `4e94e` 본체, `1ef0e`, `371e`/`3786`.
  - 이어서 +241, +309, +344, +389~+391(`20738`), +424~+426, +455~+457(`4ebe2` `4ee04` `b0c` `e6496`).
- [F] P1b 68/94는 +130 뒤로 새 C PC가 없다(플레이어 본체 없음, C 75 PC). boot-demo-0은 frame 381부터 플레이어 본체를 실행하고, demo만의 코드(`248de` `1f418` `1f6da` `2285c` …)가 +135까지 이어진다.

## 4. 단위 계획

### 4.1 규칙

- 단위 = 그 단위에 속하는 **실행된** routing 밖 PC를 진입으로 한 FR closure. 실행된 설치 값만 따라가고, 앞 단위까지 routing된 상태에서 잰다(D 계획 §4와 같다).
- 단위 소속: 각 실행 PC의 키 = 각 run의 첫 C·E frame 기준 상대 frame의 최소값(demo만 실행하는 PC는 10000 + 상대 frame). 키 구간으로 나눈다. 같은 frame에 처음 실행되는 PC들은 같은 IO 단계에 속한다.
- 정지:
  - 뒤 단위에 속하는 실행된 block 시작에서 멈춘다(그 단위가 가짐).
  - 실행된 block 옆의 **미실행** 정적 subtree 중 크기 50 block 이상인 것의 입구 22곳(`1d3e0` `1de3c` `1e21c` `1e8de` `1efd6` `1f070` `1f48a` `1fb28` `1fc96` `1fd3c` `1fd50` `208fa` `21ca4` `21d0e` `21dd0` `21ea0` `21fa6` `2210c` `223a0` `223d6` `4eb6a` `4ef08`)에서 멈춘다. 그 뒤는 "나머지 단위"(C9~C13)로 미룬다(§5 결정 2).
  - [I] 22곳은 모두 미실행이다. 보정 관측에서 TB 시작으로 기록되지 않았다. 그중 4곳(`1d3e0` `1fb28` `208fa` `4eb6a`)은 조건 분기의 fall-through인데, 조건 분기는 TB를 끝내므로 실행됐다면 TB 시작으로 기록됐어야 한다.
- block 시작은 전체 closure 기준으로 한 번만 정한다. 다른 단위가 쓰는 설치 값이나 분기 대상도 시작이다.
  - `MOVE.L #v,$84(A6)`의 값 19개(`21602` `21610` `21c66` `21cd8` `21d2a` `21d92` `21e04` `21e6a` `21eb0` `21f70` `21fc6` `21ffc` `2210c` `22128` `221d2` `22240` `2228e` `22360` `2241c`)는 `201a6 JSR (A4)`의 대상이라 시작으로 강제한다.
  - 그중 `21610` `21c66` `21d92` `21e6a` `21f70`은 역사 기록에 TB 시작으로 있다. 다만 `201a2`가 역사에서는 가려져 있었으므로, node 쓰기 뒤 TB 분할인지 진짜 진입인지 기록만으로는 가를 수 없다 [U]. 둘 다 시작이면 맞다.
- 계산 점프 표: **실행된 칸만** 단위에 넣는다. 나머지 칸은 선언 정지로 둔다(FR4 결정과 같다, §5 결정 4).

| 계산 점프 | 표(CPU = 파일 오프셋) | 칸 | 대상 종류 | 실행 칸 → 대상 | 단위 | 전부 전사 시 추가 시작 |
| --- | --- | --- | --- | --- | --- | --- |
| `2031c JMP 20320(PC,D0.W)` | `20320..20344` | 9 | 6 | 없음 | C3 | +35 |
| `20792 JMP 20796(PC,D0.W)` | `20796..207a6` | 4 | 2 | `20796` → `208d2` | C5 | +15 |
| `2094e JMP 20952(PC,D0.W)` | `20952..209c2` | 28 | 8 | `2095a` → `212ce` | C5 | +90 |
| `209d6 JMP 209da(PC,D0.W)` | `209da..20a4a` | 28 | 2 | 없음 | C5 | +41 |
| `25298 JMP 2529c(PC,D0.W)` | `2529c..252c0` | 9 | 4 | `252a4` → `252c0` | C7 | +24 |

- [F] 다섯 표를 모두 전사하면 closure가 +204 시작 늘어난다. 새 계산 점프 3개(`20378` `203ac` `207ba`, `207ba`는 28칸)도 생긴다.

### 4.2 단위 표(보정 관측, scratch `plan/plan_final.json`)

예측 일치 frame은 D 계획 §1의 상한 모형이다(run마다 routing 밖 실행 PC가 처음 나온 frame까지, guard 전까지). 앞 단위 범위를 가상 routing(`hroute._EXTRA`)에 넣고 잰다. "남은 PC"는 그 단위 뒤의 C / E 실행 PC다.

| 단위 | root(대표) | block | 명령 | 실행 수 | run | 예측 일치 frame | 남은 C / E | 특이 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (기준) | | | | | | 165,714 | 835 / 220 | |
| **C1** | `4e68e` `4e732` `4e7ec` `4e83c` `4e94e`(앞) `4f2e0` `4f32e` `4e4da` `4e58a` `4e0f6` `b7a28` `ca50` `ca3a` + `1d1f4` `1d20c` `48346` `49bca` | 139 | 306 | 94,017 | 16 | 165,759 (+45) | 757 / 218 | TRAP `4e69a`, `28ae` 자식 `4f2e0`, bank 창 `2001e4`, callee의 C·Z 읽기 |
| **E1** | `de8bc`..`df2c0` 31 root, `18364`, `2622` | 222 | 609 | 307,201 | 17 | 169,144 (+3,385) | 757 / 12 | MOVEM 4, `28ae` 자식 `dedb6` `dee36` `defdc` |
| C2 | `1cd98` `1d20c`(`1d222..`) `1dfe6` `1d582` `1dde8` `1edb0`(앞) `1cab6` `1d0c2` `1d1d0` `1ed78` `1dbd8` `1d15a` `1a9e8` `1cb08` … | 196 | 468 | 78,634 | 14 | 169,144 (+0) | 659 / 12 | live `JMP (A1)` `1aa38` |
| C3 | `20128` `21688` `1edb0` `361e4` `4de9c` `4d0a4` `215e6` `206a4` `21556` `21610` `48350` `48384` `21602` `e8b5a` | 226 | 457 | 183,836 | 14 | 169,482 (+338) | 532 / 12 | `JSR (A4)` `201a6`, 표 `2031c`, `215e6` 목록 `JMP (A1)` `21620` `221de`, SUBX, MOVEM 2 |
| C4 | `4e94e`(본체) `1ef0e` `21688` `4f22c` `4e732`(뒤) `371e` `3786` `1be3a` `1c052` `1d09e` `4f13c` `4da08` `1cec2` `4eef4` `1bf94` `1c086` `1c0b4` `4e538` `4e564` … | 230 | 520 | 234,993 | 14 | 170,691 (+1,209) | 366 / 12 | 숫자 출력 `JSR (A1)`=`3650`, DIVU 6(표 `377a`), MULU, `JMP (A1)` `21c72` |
| C5 | `20738` `214d6` `2143c` `1c356` `211e6` `cddee` `1cc1a` `4d106` `1cb38` `1d182` `4de7a` `214c0` `206ec` `1c51c` | 203 | 493 | 22,436 | 14 | 172,297 (+1,606) | 265 / 12 | 표 `20792` `2094e` `209d6`, `JMP (A1)` `21f7c`, MULU 4, MOVEM 4, 자식 `1c4b0` `365fc` `cde42` |
| C6 | `1ebf6` `4ee04` `4ebe2` `e6496` `b0c` `1eb50` `1d63a` `1daee` `1d8cc` `21622` `1da60` `4e5b0` `4edc0` … | 214 | 457 | 10,972 | 10 | 173,820 (+1,523) | 196 / 0 | 자식 `1e67a` `e695a` |
| C7 | `248de` `1f6da` `1c9ce` `1f56a` `2285c` `1f2d4` `1f224` `226ca..22758`(demo만) | 217 | 542 | 1,437 | 1 | 173,877 (+57) | 93 / 0 | 표 `25298`, DIVU, MULS, 자식 `23c56` `253f4` |
| C8 | `1f418` `1cff8` `1fb02` `1cfde` `1fd12` `4d1ac` `1d066` `1f9da` `1f3e8` `ea626` `1fcce` …(demo만) | 99 | 205 | 1,763 | 1 | **173,966** (+89) | 0 / 0 | `JMP (A1)` `21d9e` `21e76`, MOVEM |
| C9 | 나머지 `ca5c..1dfe2` | 196 | 406 | 0 | 0 | 173,966 | 0 / 0 | 자식 `369ba` `3fe7a` `3fedc` |
| C10 | 나머지 `1dfe2..1e9a6` | 197 | 408 | 0 | 0 | 173,966 | 0 / 0 | MULS 4, MULU |
| C11 | 나머지 `1e9a6..1fede` | 196 | 363 | 0 | 0 | 173,966 | 0 / 0 | 자식 `36350` |
| C12 | 나머지 `1fede..222c8` | 196 | 391 | 0 | 0 | 173,966 | 0 / 0 | `JMP (A1)` 7곳(`215e6` 목록) |
| C13 | 나머지 `222c8..` | 196 | 476 | 0 | 0 | 173,966 | 0 / 0 | `JMP (A1)` `22378` `22428`, ADDX 2, MULU 2, DIVU, MOVEM |

- [F] 합계: IO 단위 C1~C8 + E1 = **1,746 block**, 나머지 C9~C13 = **981 block**, 전체 **2,727** = 전체 closure.
  - scratch `cplan3.py`가 확인한다: 단위 시작 합집합 = 전체 closure 시작, 단위 명령 합집합 = 전체 closure 명령, 겹침 0, 빠진 실행 PC 0.
- [F] 첫 정지(예측):
  - C1 뒤: E 15 run(frame +3, E `de8ca` 등), C 1 run(boot-demo frame 381, 정지 PC가 `1d1f4`에서 `1d222`로 바뀜).
  - E1 뒤: C 14 run(+186/+190). C2 뒤에도 C 14 run이다.
  - C5 뒤 C 10 run, C6~C7 뒤 C 1 run(demo), C8 뒤 0.
- [I] **IO 진척이 없는 단위:**
  - C2 단독은 +0이다. +190 frame에 실행 PC 198개가 처음 실행되고(이어서 +191 22, +193 3), 이 구간의 closure가 422 block이라 한 단위에 담을 수 없다. `1ee00`에서 둘로 나눴다(C2 196 / C3 226). C2와 C3을 한 묶음으로 IO 확인한다(FR2b~d의 `4e68e`와 같은 경우).
  - C1 단독은 +45뿐이다. E1까지 연결해야 +3,430이 된다.
  - C9~C13은 IO 관측에서 실행되지 않아 IO 진척이 없다.
- [F] 순수 FR 규칙(미실행 subtree를 미루지 않음, 같은 구간): C2 478, C3 488, C4 341, C5 277, C6 428, C7 217, C8 137 block(합 2,727).
  - +190 단계(169,482)에 C1·E1 뒤 966 block(약 5 단위)이 필요하고, 173,966에는 전체 2,727 block이 필요하다.
  - 미루는 규칙이면 1,746 block에서 173,966에 닿는다.
- [F] 역사 관측만으로 계획하면 C2 이후가 틀린다. `1d222` 뒤의 실행된 플레이어 코드(§2)를 미실행으로 보고 미루게 되기 때문이다. 이 표는 보정 관측으로 만들었다.

### 4.3 범위 밖

- [I] C9~C13(981 block)은 이 관측 집합에서 실행되지 않는 플레이어 코드다: 점프·수류탄·탈것·피격·사망 등 [I: 이름]. C 완료 정의(§1)의 조건 1에는 필요 없다(FR4b/FR4c와 같은 위치). GOAL 전체 완료에는 필요하다.
- [I] 계산 점프 표의 미실행 칸·handler(+204 시작과 새 계산 점프 3개)도 같은 위치다.

## 5. 결정 요청(메인)

1. **관측 보정(§2)을 받아들이는 방식.**
   - (a) 관측기에 정확한 routing bitmap 선택지를 더하고, C·E run 18개(또는 296개 전부)를 새 artifacts 디렉터리에 다시 관측해 보존한다. 문서의 `[I] single-PC executors cover their intra-function closure` 문장도 고친다(`1dc84`/`210ae`는 덮지 않음).
   - (b) scratch 재관측을 계획 입력으로만 쓴다.
   - **권고 (a)**: C 단위 계약마다 실행 집합이 필요하다. 관측기 본체는 다른 도구가 pin하지 않는지 먼저 확인해야 한다 [U].
2. **미실행 큰 subtree 미루기(§4.1, 22 입구, 문턱 50 block)** 대 순수 FR 규칙. **권고: 미루기.** IO 173,966에 1,746 block(9 단위)으로 닿는다. 순수 규칙이면 2,727 block 전부가 필요하다. 미룬 입구는 다른 단위 출구와 같은 선언 정지다.
3. **나머지 C9~C13(981 block)의 시기.**
   - **권고:** C1~C8 뒤에 IO 관측을 넓히고(점프·사격·수류탄 입력 스크립트, 스테이지 진행 seed), 그 관측으로 C9~C13을 다시 나눈다. IO 증거 없이 바로 구현할 수도 있다(FR7~FR9처럼 단위 시험·변이·실제 ROM·V1로 검증).
   - 주소 구간으로 자른 현재 분할은 임시값이다.
4. **계산 점프 표.** **권고: 실행된 칸만**(FR4 방식, 나머지는 선언 정지). 전부 전사하면 +204 시작이고 새 계산 점프 3개가 생긴다. 나머지 칸은 FR4b/FR4c처럼 "C 표" 단위로 미룬다.
5. **`4e68e` 계열의 분할.** 지금은 시간 순서로 C1(69 실행 시작), C4(118), C6(36)에 나뉘고, 함수 중간 block에서 끊긴다(C1 출구 `4e758` `4e962` `4e8e6` …). 함수 단위로 묶으면 약 480 block, 2~3 단위가 되고 IO 진척이 늦어진다. **권고: 시간 순서.**
6. **E 주소의 C helper와 공유 helper.**
   - `ca50`(C `4e7d4`/`4e7ec`/`4e83c`와 E `de8ee`가 부름), `ca3a`, `b0c`, `e6496`은 C 단위에 둔다.
   - `18364`(E `ded4a`만 부름)는 E1에 둔다.
   - `2622`(boot `9de`, fixture에서 guard frame에만 실행, 3 block)는 E1에 넣었다. boot E 단위로 미뤄도 IO에는 차이가 없다.
   - D와 공유하는 helper(`19a00` `1a988` `48210` `49c38`)는 이미 routing됐다.
   - **권고: 이대로.**
7. **이름 충돌.** 저장소에 controller 단위 C1~C3가 있다(`animation-machine-controller-c1-contract.md` 등, V1 `tools/unit_fixture_specs/c1.py` `c2.py` `c3b.py`). **권고:** 계획 이름은 C1…로 두고, 파일 이름은 `animation-machine-player-c1-contract.md`, `engine/src/animation_machine_player_c1.cpp`, spec `tools/unit_fixture_specs/pc1.py`처럼 접두를 붙여 구분한다.
8. **둘째 callback 칸 `84(A6)`의 값 19개를 block 시작으로 강제.** `215e6` 목록의 handler는 live `JMP (A1)` 대상으로 둔다(목록 자체는 자료). **권고: 이대로.**
9. **C2/C3 분할점 `1ee00`**(+190 단계를 둘로, IO는 둘 다 연결된 뒤 확인). 한 단위(422 block)로 하는 것도 가능하다. **권고: 둘로 나누고 C3 뒤에 IO를 확인한다.**
10. **FR4b/FR4c는 C 뒤로 계속 미룬다.** IO 관측에서 실행되지 않는다.
11. **FR7~FR9의 IO 확인.** C3~C6을 연결하면 C 뒤 D 경로가 IO 사슬에 닿는다. 단위마다 IO 재실행에서 D 첫 정지 0을 확인해 D 계획 §5의 [U]를 해소한다.

## 6. 진척 측정·재현

worktree(`/Users/start/Workspce/metalslug-c1`)에서 `.venv/bin/python /Users/start/Workspce/ms5-scratch/c1/tools/<도구>`로 실행한다. 도구는 scratch이고 납품물이 아니다. `extracted/`와 `artifacts/`는 읽기만 한다.

1. 기준선(역사 관측): `dleft.py` → `C 620, E 220, 예측 165714, C/E 15, C 1`.
2. 재관측: `MS5_SEED_DIR=artifacts/stage_entry_body .venv/bin/python …/reobs.py --config P1,P1b,boot-demo-0,boot-title-start,fx-c-input-read,fx-n-input-read --cases 68,69,70,71,94,95,100,101,106,107,110,111 --p1b-cases 68,94 --no-split --keep-all-states none --workers 3 --out <새 디렉터리>` → `reobs_check.py <디렉터리>/`는 `ALL NATIVE RECORDS EQUAL … True`가 나와야 한다.
3. 가려진 코드: `hidden.py`(`plan/hidden.json`: H, 가려진 callback), `hidden2.py`(`plan/hidden2.json`: 원자별 분류; 덮는 원자 판정의 입력).
4. 보정 기준선: `MS5_REOBS=…/reobs dleft.py` → `C 835, E 220, D 0, 예측 165714`. `dstate.py`가 `MS5_REOBS`를 보면 그 run의 기록으로 바꾸고, 덮는 원자의 PC는 뺀다.
5. 계획: `MS5_REOBS=… mkspec.py plan/plan_final.json 1ee00` → `MS5_REOBS=… cplan3.py plan/plan_final.json W` → `starts_C1.txt` … `starts_C13.txt`, `starts_E1.txt`, `plan/units.out.json`. 마지막 줄 검사는 `starts_equal true, insns_equal true, missing_exec []`여야 한다.
   - 비교용: 순수 규칙 `plan/plan_v0.json`(defer 없음).
6. 단위 상세: `MS5_REOBS=… udetail.py C1` → 출구 분류, 범위 SHA, `plan/C1.dis.txt`(`>` block 시작, `*` 실행 TB 시작).
7. 보조:
   - `cseq.py`(run별 상대 frame 순서), `cbseq.py CFG CASE`(node callback 변화), `cfront.py`(미실행 subtree 크기), `cfront2.py T`(미룰 입구).
   - `ctab.py`(BRA.W 표), `cind.py`(간접 분기), `cartef.py`(TB 분할 PC), `cfam.py`(계열), `cscan.py starts`(block 경계를 넘는 flag 읽기).
8. 단위마다(D 계획 §6과 같다):
   - IO 비교 재실행(`io_ab.sh`, 두 번 같음): 일치 frame과 위 표의 예측의 차이, 첫 정지 영역(C·E·D), 불일치 0.
   - `MS5_REOBS=… dleft.py`로 C·E 남은 실행 PC.
   - 단위 검증: `make -j3 all test`, UBSan, 변이, 실제 ROM 차분 7,500건, V1과 회귀 spec, frame 회귀(D1·controller game·IRQ 54,400, demo 45,684), legacy 검증기.

시작 목록 SHA256(첫 16자):

| 목록 | SHA256 | 목록 | SHA256 |
| --- | --- | --- | --- |
| C1 | `7d67c3729a79cc8c` | E1 | `befbbe32a6f0f859` |
| C2 | `c8e7313e2d71813c` | C3 | `6452d0d0f8a675c2` |
| C4 | `279a317b969ea012` | C5 | `88a6dbefd0665d5f` |
| C6 | `186ab793fac8d5db` | C7 | `18a35f40c2ab773d` |
| C8 | `646381e98a3bd723` | C9 | `69183e188891c35b` |
| C10 | `4439d36680027f1f` | C11 | `c27da5c895cea580` |
| C12 | `657d98291364a9fd` | C13 | `16212926277916c7` |

## 7. 미확인

- [U] `46efe` `46f0c`(원자 `46ef4`/`46f08`, D 주소)가 C++ 실행부에 덮이는지. 역사 첫 정지 뒤에만 실행된다. C 단위 IO 재실행에서 D 첫 정지로 나오면 보충한다.
- [U] 같은 frame에 처음 실행된 PC들의 순서. 첫 정지 PC는 IO 비교가 확정한다. C2만 연결했을 때의 IO 정지 PC는 예측하지 않았다.
- [I] 미룬 입구 22곳의 미실행 판정은 "조건 분기와 JSR/BRA는 TB를 끝낸다"는 Unicorn(QEMU) 동작과 정확한 bitmap 재관측에 기댄다.
- [U] 역사 기록에서 node 쓰기 뒤 바로 TB가 갈라지는 원인(`21610` `defe2..df002` 등). 해석에는 영향이 없다.
- [U] P1b 68/94에서 600 frame 안에 플레이어 본체가 시작하지 않는 이유.
- [I] 이름(슬롯 관리자, 플레이어 객체, 캐릭터 선택, 숫자 출력)은 동작에서 붙인 것이다. 원본 이름이 아니다.
- [U] C9~C13의 주소 구간 분할은 임시다. 착수 때(가능하면 관측을 넓힌 뒤) 다시 잰다.
- [U] 재관측은 C·E run 18개만 했다. 나머지 278 run은 IO 비교가 끝까지(또는 guard까지) 일치하므로, 그 run들에서 가려진 routing 밖 코드는 실행되지 않는다 [I].

## 8. C1 상세 명세

다음 Opus 작업자가 C1 계약과 실행부를 쓸 때의 입력이다. 수치는 scratch `plan/units.out.json`과 `udetail.py C1`이다.

### 8.1 범위

- [F] **139 block, 306 명령, 1,342 byte, 20 범위.** 시작 목록 `ms5-scratch/c1/starts_C1.txt`(SHA256 `7d67c3729a79cc8c81f4f231026ed70a6fb4eaefb3c047fc3b87e7d9bd67bd01`). 범위 byte를 이어 붙인 SHA256은 `73c889d9adf46c0a1fb00da0d5d99de9de0c90c02b16cff0e6d9ed6c9e583ed1`이다.

| 범위(CPU = 파일 오프셋) | byte | 시작 | 내용 [I] |
| --- | --- | --- | --- |
| `ca3a..ca42` | 8 | 1 | `MOVE.W -76a0(A5),-76a2(A5); RTS` |
| `ca50..ca56` | 6 | 1 | `TST.B -7699(A5); RTS`(Z를 돌려줌) |
| `1d1f4..1d222` | 46 | 7 | 플레이어 객체 진입 `1d1f4`, 대기 상태 `1d20c` |
| `48346..48350` `48368..4836e` | 10 + 6 | 2 | C를 돌려주는 helper의 Clear 쪽(`ANDI.B #fe,CCR`). Set 쪽 `48350..48368`은 C3 |
| `49bca..49be0` | 22 | 3 | WORD `4(5726/572c(A5))` 지우기 |
| `4e0f6..4e112` | 28 | 1 | WORD `5d22/5d26(A5)+2×(D0&1)` 지우기 |
| `4e4da..4e4e2` `4e536..4e538` | 8 + 2 | 2 | `TST.B 5d1f(A5)`: 0이면 `RTS`. 나머지 `4e4e2..`는 C4 |
| `4e58a..4e5b0` `4e5c2..4e5e8` | 38 + 38 | 7 | 비트 슬롯 할당·해제(BYTE 표 `4e4d2` `4e4d6`) |
| `4e68e..4e69a` `4e69c..4e758` | 12 + 188 | 13 | 슬롯 callback `4e68e`(WORD `76` 0/1/≥2 → TRAP), 초기화 → `4e732` |
| `4e7a2..4e8e6` | 324 | 42 | `4e732`/`4e7ec`/`4e83c` 상태, 입력 블록 `104ca8`/`104cae` |
| `4e8f0..4e8f8` `4e8fc..4e962` `4e97e..4e986` `4eb50..4eb58` | 8 + 102 + 8 + 8 | 12 | 플레이어 생성(`4e91c LEA 1d1f4; JSR 2a28`), `4e94e` 진입 |
| `4f2e0..4f4ba` | 474 | 47 | `28ae` 자식 `4f2e0` → `4f32e`/`4f396` 표시 객체 |
| `b7a28..b7a2e` | 6 | 1 | `TST.B D0; BNE b7a48` |

- [F] 진입(실행된 PC를 줄인 closure 진입): `ca50` `4e0f6` `4e4da` `4e58a` `4e68e` `4f2e0` `1d1f4` `4e8f0` `b7a28`.
  - 실행된 시작은 80개다(C 78, E 2). 실행되지 않은 시작은 59개다(`4e802..4e826` `4e888..4e8d4` `4f34a..4f4b8` 등 분기 쪽).
- [F] 범위 안 설치 값(dispatcher 진입이 되는 block 시작):
  - `4e68e`: `4e1cc`(controller C2 `4e1ee`/`4e204`)가 node `1009a8`/`100a6c`에 설치한다.
  - `4e732` `4e7ec` `4e83c` `4e94e` `4f32e` `4f396`(미실행) `1d20c`.
  - `1d1f4`: `4e91c`, `1bd9c`, `47772`가 설치한다.
  - `28ae` 자식 `4f2e0`: `4e7ba MOVEA.L #4f2e0,A0`.

### 8.2 출구와 경계

- [F] routing된 출구: `289e` `28ae` `2a00`(`4f33c`/`4f3a4 JMP 2a00`) `2a0a` `2a28` `3670` `8d34` `8ebe` `8ff4` `ca32` `ca42` `16ed2` `1bd2e` `48398` `49be0` `49f8c` `49fc6` `b7a2e` `b7a48` `e62ec`.
- [F] 뒤 단위 정지(실행되지만 뒤 단위가 가짐):
  - `1d222`(C2): `1d21c BCS`. demo frame 381과 A의 frame 192에 실행된다.
  - `48350`(C3): `48346`의 C Set 쪽.
  - `4e4e2` `4e538` `4e564` `4e758` `4e962` `4e986`(C4).
  - `4e8e6` `4e8f8` `4eb58`(C6).
- [F] TRAP `4e69a`(`TRAP #f`, WORD `76(A6)` ≥ 2). 경계로 둔다. 범위 `4e68e..4e69a`와 `4e69c..`가 그 PC를 뺀다.
- [F] 계산 점프·전사할 표는 없다. 읽는 자료:
  - BYTE 표 `4e4d2..4e4da`(`00 02 01 03 00 02 01 03`).
  - `4e81a LEA 4e34c(PC),A0`: ASCII HUD 문자열("PLEASE WAIT", "PRESS ST…"). C4의 `4e564`로 넘기는 포인터일 뿐이다.
  - `4e8c0 LEA e84c8.l,A1`: `3670`에 넘김.
  - `4f2f4 MOVEA.L #4f4ba,A1`: interpreter `49f8c`의 script 포인터.
  - bank 창 LONG 읽기 `4f2e6 MOVE.L 2001e4.l,22(A6)`: CPU 주소다. 물리 오프셋은 `bank_base + 1e4`.
- [F] block 경계를 넘는 flag(scratch `cscan.py`):
  - C 소비자:
    - `1d21c BCS`: `48346`의 C. `48368 ANDI.B #fe,CCR`이면 Clear, C3의 `48362 ORI.B #1,CCR`이면 Set.
    - `4e808 SCS`: routing된 `ca32 CMPI.B #aa,-769c(A5)`의 C.
    - `4e958 BCC.B`: routing된 `289e`의 C.
  - **Z 소비자** `4e7da` `4e7f2` `4e842 SNE`: `ca50 TST.B -7699(A5); RTS`의 Z를 읽는다.
    - [I] controller C1 `ac1_flag_zero`처럼 BYTE `A5 − 7699`를 다시 읽어 Z를 다시 계산하는 방식을 권한다. RTS는 그 byte를 바꾸지 않는다. A5 ≠ `108000`이면 오류로 두는 조건은 [U]이고, 계약에서 정한다.
  - C 생산자(호출자에게 돌려줌): `48368`(Clear). C 보존 목록에 넣는다(FR 관례).
  - `SEQ`/`SNE`/`SCS`는 `4e74c` `4e7da` `4e7f2` `4e808` `4e842`에 있다.

### 8.3 IO·seed

- [F] 실행하는 run 16개: P1 12, P1b 2, boot-title-start, boot-demo-0.
  - frame: A 2~3, 66~73 / B 222~223, 286~289 / title-start 122~123, 186~193 / demo 381(`1d1f4` `1d20c` `48346` `49bca`만).
  - node: `4e68e`은 `1009a8`(WORD `76` = 0, P1)과 `100a6c`(1, P2), LONG `78(A6)` := `100cb8`/`100da8`. `1d1f4`/`1d20c`는 LONG `100cb8`(관측 field `p1cb`) node.
- [F] IO 예측(C1만 연결): 165,714 → **165,759**(+45 = 15 run × 3 frame).
  - 15 run의 첫 정지는 frame +3의 E(`de8ca` `de8ee` `de97e` `deba4` `defdc`, E1)로 옮겨 간다.
  - boot-demo-0은 frame 381 그대로이고, 정지 PC가 `1d1f4`에서 `1d222`(C2)로 바뀐다 [I: 같은 frame의 실행 순서].
- [F] D1 자연 seed 137개(입력 없음)와 P0 run은 C·E 코드를 실행하지 않는다. 실제 생산자 사슬 seed는 IO 관측의 P1·boot 상태(`artifacts/animation_machine_io_native/states/…`, frame 2·66·72·222 등)다.

### 8.4 영향받는 기존 시험·검증기(이전 기대값을 기록하고 갱신)

- [F] `tools/verify_animation_machine_stage_event.py`와 `_stage_event_ops.py`의 `CPP_PINS`: `animation_machine.cpp`(`7233eefc…`)와 `animation_machine_internal.h`(`b870dcc5…`).
- [F] `tools/verify_animation_machine_stage_area.py`의 `UNROUTED_NEIGHBOURS`에 `4e68e` `b7a28` `b7a2a` `b7a2c`가 있다. C1 뒤 `4e68e` `b7a28`은 시작이 되고, `b7a2a` `b7a2c`는 block 안 PC가 된다. 오류 문구가 바뀌므로 `SUPERSEDED_NEIGHBOUR_ERRORS` 방식으로 옮긴다.
- [F] `tools/verify_animation_machine_area_clear.py`의 `unrouted_neighbour_00ca50`(`negatives`, 889행 근처): `ca50`이 시작이 된다.
- [F] `tools/verify_animation_machine_input.py` 861행 이웃 목록의 `49bca`(C1 시작).
- [F] `engine/tests/animation_machine_objects_u06_test.cpp`의 `rom_outside`에 `49bca` `49bde`가 있다(C1의 시작과 block 안 PC).
- [I] 경계가 맞닿은 범위: `engine/tests/animation_machine_input_test.cpp` RANGES `49ab4..49bca`, `animation_machine_controller_c1_test.cpp`·`unit_fixture_specs/c1.py`의 `ca32..ca3a`, `animation_machine_area_clear_test.cpp` RANGES `ca48..ca50`. 이웃 PC를 "routing 밖"으로 확인하는 행이 있으면 바뀐다. `make test`가 찾는다.
- [I] `4e68e`·`1d1f4` 값을 RAM에 쓰기만 하는 시험(`animation_machine_controller_c2_test.cpp`의 `2a28` 설치, `animation_machine_stage_area_test.cpp`)은 그 callback을 실행하지 않는 한 바뀌지 않는다.
- [F] IO 비교 기준: 첫 실패 전 일치 165,714 → 예측 165,759. frontier에서 `4e68e`가 사라지고 E `de8ca` 계열이 나와야 한다.

## 9. 완료 판정(2026-10-23, 메인)

- [F] C1~C8과 E1을 연결한 뒤 IO 비교: native 완료 frame 173,966 전부 일치, 불일치 0, 예상 밖 C++ 오류 0, 두 번 실행 동일, 수용 키 모두 true(`frontiers_confirmed` 포함). 첫 정지 run 0.
- [F] 보정 관측 기준 실행된 routing 밖 PC: C 0 / E 0 / D 0. 따라서 §1의 C 완료(이 관측 집합)와 D 계획 §5의 [U](C 뒤 D의 IO 확인)를 함께 닫는다.
- [F] 단위별 IO(예측 = 실측): C1 165,759 · E1 166,744 · C2 166,744 · C3 166,744 · C4 170,691 · C5 172,297 · C6 173,820 · C7 173,877 · C8 173,966.
  - E1~C3의 실측이 §4.2 예측보다 작았던 이유: 보정 관측도 TB의 첫 routing 밖 PC만 기록해 직선 연속 PC(`4e8e6` 등)가 숨었다. C3·C4가 숨은 block 6개를 넣었고, C4부터는 단위마다 정확한 bitmap으로 다시 관측해 예측했다.
- 남은 일(이 관측 집합 밖):
  - C9~C13(981 block)과 선언 정지로 둔 `1dccc` `1dc8e` `1e67a` `e695a` `1e918` `23c56` `1f3e8` `21e48`: 입력(점프·사격·폭탄 등)을 늘린 관측이 있어야 실행 근거가 생긴다.
  - 보정 관측을 `artifacts/`에 둘지와 observer의 정확 bitmap 방식 도입은 사용자 승인 뒤에 정한다.
  - FR4b/FR4c.

## 10. 입력 확장 관측과 남은 단위(2026-10-23, 작업자 Claude Opus 5.5 / high)

기준: `main` `b540438`(C1~C8, E1, D routing), routing `engine/src/animation_machine.cpp` SHA256 `2622b7a2374959c5…`(routing된 짝수 PC 127,936), branch `claude/io-observation-2`(커밋 안 함). 관측 결과는 scratch `ms5-scratch/obs2/`에만 두었다. 공유 `artifacts/`·ROM·`extracted/`는 읽기만 했다. 이 절은 BIOS 실행, 자연 scheduler, IRQ timing을 주장하지 않는다. 모든 입력 값과 host 쓰기는 선언이다.

### 10.1 원래 관측에서 C9~C13이 실행되지 않은 이유 [F]

- 플레이어 입력은 `1cd98`이 `JSR 49be0`(A0 = `5726(A5)`/`572c(A5)`)으로 읽는 WORD다. `1cdba MOVE.W (A0),D0` 뒤 bit 0(위)·1(아래)은 BYTE `61` bit 5·4로, bit 7(D)은 `ANDI.W #ff7f`로 지우고, 나머지(bit 2·3 방향, bit 4 A, bit 5 B, bit 6 C)를 상태 함수가 읽는다(C8 계약 `1f418`의 D0 bit 5 / 1 / 6 / 4).
- 그 WORD는 `49b3a`(P1)/`49b90`(P2)가 만든다. D0 = 현재 BYTE `104caa`, D1 = 새로 눌림 BYTE `104cab`이고, A4 = 버튼 mask 표다. **game mode(BYTE `100012` = 2)에서는 A4 = `10f01c`(P2 `10f020`), 그 밖에는 ROM `49ab0`(`10 20 40 80`)**이다(`49b48`/`49b52`). `49ab4..49ad4`는 버튼마다 `D0 & mask = mask`면 "누름"(D7), 그리고 `D1 & mask`도 참이면 "새로 눌림"(D6)으로 센다. `49bb4`가 D6을 `5726`, D7을 `5728`에 쓴다.
- stage seed와 boot RAM에서 `10f01c..10f023`은 0이다. mask가 0이면 네 버튼이 언제나 "누름"이고 "새로 눌림"은 없다. 실제로 P1 94의 frame 219부터 `5726/5728` = `0008`/`00f8`이다(오른쪽, 그리고 A·B·C·D 모두 누름). 그래서 walkfire의 A·B 입력은 사격·점프로 읽히지 않았다.
- `10f01c`/`10f020`을 채우는 곳은 게임의 기본 설정 경로뿐이다: `8fa JSR bcb4`(USER 초기화 경로, BYTE `10fd82` = 0) → `bd16`/`bd20 BSR bbfa` → `bc0a JSR bc1e`(`49ab0`의 네 BYTE를 `10f01c`와 `10f020`에 복사). `bbfa`는 이어서 BYTE `10f027` := 2, `10f026` := 3을 쓰고(`bc0e` `bc14`), `be3a`가 `10fd82` = 0이면 그 둘을 BYTE `10fd88`/`10fd8b`로 복사한다. BIOS 없는 boot는 `10fdae` = 2/3로 시작하므로 이 경로를 실행하지 않는다.
- 같은 이유로 목숨이 하나다. `4e8d6`이 플레이어 기록 BYTE `99` := BYTE `10fd88`이고, 0이면 1로 둔다(`4e8e0`). `10fd8b`는 game mode에서 `490cc`가 읽는다(그 밖은 3).
- [I] boot-demo-0는 BYTE `100012` = 1이라 ROM 표 `49ab0`를 쓰고, replay 입력이 정상으로 읽힌다. C7·C8의 demo에서만 실행된 코드가 이것으로 설명된다.

### 10.2 관측 설계

- **observer pin 처리: (a) 별도 script.** 새 도구 `tools/observe_animation_machine_io_ext.py`가 `tools/observe_animation_machine_io.py`를 수정 없이 import한다. 바꾸는 것은 셋이다.
  1. 입력 script·설정 파일을 `docs/analysis/data/io-input-scripts-ext.json`(같은 형식, version 1)으로 바꾼다. 기본 파일과 이름이 같은 항목(`none` `walkfire` `game-mode` `player-start-p1` `P0` `P1`)은 그대로 복사한 것이고, 도구가 실행 전에 같은지 검사한다.
  2. TB 기록 bitmap을 정확한 현재 routing으로 바꾼다(`verify_animation_machine_unit_fixtures.pc_routed`, 짝수 PC 전부, 선택 `--extra-routed`). 관측 시점 routing(`8ce8eb93`)의 pin 검사와 단일 PC closure 근사는 쓰지 않는다. 나머지 pin(도구 9개, ROM, seed)은 observer와 같다.
  3. 실행 조직: (설정, seed)마다 연속 run 하나이고, 모든 frame 시작 상태를 저장한다(IO 검증기가 요구). 대표 class·split run은 없다.
  - 그 밖의 native 기구, frame 규약, 선언, guard, 기록, state pack, `observation.json`/`platform.json`은 observer 그대로다. `observation.json`의 `pins.observer`는 고치지 않은 observer의 SHA이고, 새 `pins.extension`(도구·script 파일·기본 파일 SHA, case, 설정)을 더한 뒤 `compared_sha256`을 다시 계산한다.
  - 이유: observer 파일과 검증기를 그대로 두므로 기존 IO 비교가 바뀌지 않는다. scratch 사본(c)과 달리 저장소에서 재현할 수 있고, 같은 파일 안의 선택지(b)와 달리 pin된 파일을 건드리지 않는다. [F] 기존 IO 비교를 이 branch에서 다시 돌려 결과가 같음을 확인했다(§10.6).
- **선언 host 쓰기 `default-settings`**(frame 1, §10.1의 근거): LONG `10f01c` := `10204080`, LONG `10f020` := `10204080`, WORD `10f026` := `0302`, BYTE `10fd88` := 3, BYTE `10fd8b` := 2. 이것은 `bbfa`/`bc1e`/`be3a`의 효과를 선언한 것이다. 원래 경로를 native로 실행했다고 주장하지 않는다. `10f008..` 문자열과 checksum `10f028`은 초기화 검사 경로(`bcf8`)만 읽으므로 넣지 않았다.
- **입력 script**(P1 port `300000`, 낮을 때 누름. 모두 frame 20부터 주기 반복이라 플레이어 조작이 시작되는 frame과 관계없이 같은 동작이 나온다. start·select·coin bit는 없다):
  - `walkfire`(기존): 오른쪽 계속, A 8 frame마다 4 frame, B 64 frame마다 6 frame.
  - `jumpshoot`(주기 48): 오른쪽 계속, A 6 frame마다 2 frame, B 위상 0..3(점프), 아래 14..29(공중 아래 조준 뒤 웅크림), 위 34..43(위 조준).
  - `grenadeturn`(주기 96): 오른쪽 0..47 / 왼쪽 48..95(방향 바꿈), C 24 frame마다 2 frame(수류탄), A 10 frame마다 2 frame, 아래 60..83, B 30..33.
  - `mixed`(주기 160, 20 frame 창 여덟 개): A 누른 채 유지, B 유지 뒤 아래+A, 왼쪽+위+A, 입력 없음, 아래+C, 오른쪽+D+B, 위+B 뒤 A+C 동시, 왼쪽+아래+A.
  - [I] 첫 시험에서는 창 7에 왼쪽+오른쪽+아래를 함께 눌렀다. 그때 frame 310에서 N step-limit guard(6,000,000 명령)가 났다. 실제 stick으로는 불가능한 조합이라 뺐다.
- **설정**: `X1` = P1 입력(walkfire) + `default-settings`, `X2` = jumpshoot, `X3` = grenadeturn, `X4` = mixed(모두 game-mode + player-start-p1 + default-settings, 상한 2,000 frame). 대조군 `P0` `P1`(600 frame)도 같은 seed로 다시 관측한다. 검증기의 frontier 보고가 `P0` 기준선을 요구하고, 대조군 기록은 원래 관측과 비교하는 데 쓴다.
- **seed**: case 94와 68. [F] 원래 관측에서 플레이어가 나오는 P1 seed는 두 묶음뿐이다. A 묶음은 94 95 100 101 106 107 110 111이고 class signature가 같다(첫 C/E frame 2). B 묶음은 68~71이다(frame 222). 모두 mission 0이다.
- **frame 수**: X run은 모두 game over에서 끝난다. controller가 BIOS `c00444`로 가는 `system-return` guard이고, frame 1,181~1,929다. [F] 3,000 frame 시험에서는 run이 같은 frame에 끝났고 새 C PC가 없었다. 그래서 2,000을 상한으로 두었다. 합계 run 12개, 14,508 frame.
- 넣지 않은 것: boot 계열, P2 동시 입력(P1b), 다른 mission의 seed. [I] 남은 C(§10.5 C11~C14)의 큰 부분은 `1d388` 사슬의 등장 방식 코드 D7(1, 3…f)과 `1de28`/`1de30`의 `1aa3a` bit로 갈린다. 이 값은 입력이 아니라 stage가 정하는 것으로 보인다.

### 10.3 재현 명령·SHA·크기·결정성

- 명령(worktree에서): `MS5_SEED_DIR=artifacts/stage_entry_body .venv/bin/python tools/observe_animation_machine_io_ext.py --cases 94,68 --workers 4 --out <새 디렉터리>`(약 150초, bitmap 계산 27초 포함).
- [F] 결과 `ms5-scratch/obs2/final/`: `observation.json` SHA256 `9da40ac6dcbea3ebc6423319fc79755ebe87af3fc982bc7a70d596762125ffe6`, `compared_sha256` `b5d15d4fcd53555bce3f4773c8ee6113c6b79ee5aac113f6c1e59a87ddc57161`. 크기는 파일 24개 16,735,124 byte와 `observation.json` 235,696 byte다(`du` 16.6 MB, gzip run 기록과 모든 frame 상태 pack 포함).
- pin: 도구 `52b2eea30333d34d…`, script 파일 `0367bbcf769902a2…`, observer `facf49fa29b6cc0c…`(수정 없음), 기본 script 파일 `d8971c44441bca01…`.
- [F] **결정성**: 같은 명령을 두 번 돌렸다(`final`, `final_b`). `--compare` 결과는 `equal true, clean true`이고, `platform.json` 밖의 파일 25개가 모두 같다. 고치기 전 도구의 관측 두 벌(`obsA` `obsB`)도 서로 같았다. 그 run 기록·state pack의 SHA는 `final`과 같다.
- [F] **대조군**: `P0`/`P1` case 94·68의 frame 기록은 원래 관측(`artifacts/animation_machine_io_native`)과 같다. 600/600 frame에서 routing 밖 PC 필드(`unr_new` `unr_n` `unr_first`)와 대표 run 전용 `tbs`를 뺀 모든 필드가 같고, `digest_chain`도 같다.

| run | frame | 끝 | 플레이어 첫 frame / frame 수 | routing 밖 PC(관측) |
| --- | --- | --- | --- | --- |
| P0 68 / 94 | 600 / 600 | frame-limit | – | 25 / 18(덮는 원자·기준선) |
| P1 68 / 94 | 600 / 600 | frame-limit | 288 / 312, 72 / 385 | 29 / 31(같음) |
| X1 68 / 94 | 1,373 / 1,181 | system-return | 288 / 669, 72 / 693 | 418 / 482 |
| X2 68 / 94 | 1,403 / 1,211 | system-return | 288 / 701, 66 / 731 | 487 / 426 |
| X3 68 / 94 | 1,929 / 1,729 | system-return | 290 / 1,209, 70 / 1,237 | 789 / 603 |
| X4 68 / 94 | 1,721 / 1,561 | system-return | 290 / 975, 130 / 975 | 566 / 595 |

### 10.4 측정(현재 routing, scratch `ms5-scratch/obs2/tools/`)

- [F] 실행된 routing 밖 PC(P0 기준선, 덮는 단일 PC 원자의 closure 622 PC, 호출자 재분류를 뺀 수):
  - **C 228**(root 33, 실행 22,346)
  - **D 659**(root 100, 실행 79,913, 모두 C 뒤에 실행)
  - **E 108**(root 16, 실행 18,237)
  - 모두 X run 8개에서만 나온다. P0·P1에는 0이다.
  - 재분류: `3144` `e63fa` → E helper, `248de` → C helper.
- [F] 예측 일치 frame **5,095**(native 비교 frame 14,500 가운데). P0·P1 4 × 600에 X run의 첫 정지 frame을 더한 값이다. 첫 정지는 8 run 모두 C다(§10.6 실측과 같음):
  - `2210c` 4 run(X1 68 frame 440, X1 94 224, X2 68 438, X3 94 221)
  - `1f3e8` X2 94 216
  - `1f070` X3 68 436
  - `21e48` X4 68 440, X4 94 280
- [F] 원래 계획의 나머지 C9~C13에서 실행된 시작은 4 / 0 / 56 / 93 / 33이다(981 가운데 186). 그 밖에 C1~C8 계산 점프의 미실행 칸과 handler 42 PC가 실행된다. 예: C3 표 `2031c` 칸 `20324`/`20340` → `203a0`, C7 표 `25298` 칸 `252b4` → `252ce`, 목록 handler `21e48`.
- [F] 선언 정지 가운데 실행되는 것: `1dccc` `1dc8e`(interpreter stub 후속), `e695a`, `1f3e8` `1f3e0`(쓰기만 하던 callback), `21e48`. 여전히 실행되지 않는 것: `1e67a` `1e918` `23c56`, 그리고 자식 `36350` `371f8`.
- [F] C1 계획의 미룬 입구 22곳 가운데 11곳이 실행된다: `1efd6` `1f070` `1f48a` `1fb28` `208fa` `21ca4` `21d0e` `21dd0` `2210c` `223a0` `223d6`. 실행되지 않는 것은 `1d3e0` `1de3c` `1e21c` `1e8de` `1fc96` `1fd3c` `1fd50` `21ea0` `21fa6` `4eb6a` `4ef08`이다.
- [F] 새 closure(실행된 PC 995개, 설치 값은 실행된 것만 따라감)는 시작 1,499, 명령 3,603이다. 미실행 정적 subtree 가운데 50 block 이상인 것은 없다(최대 `c120c` 25). 그래서 미룰 입구는 0이다.
- 측정 명령: `MS5_OBS2=<관측> .venv/bin/python …/obs2/tools/dleft.py`, `runstops.py`(run별 첫 정지), `restcov.py`(원래 나머지·선언 정지 대조). `dstate.py`가 `MS5_OBS2`(이 관측의 모든 run, 덮는 원자 closure는 `covered.py`)와 `MS5_OBS2_MERGE`(아래 재관측의 첫 frame 병합)를 읽는다.

### 10.5 단위 계획

- 규칙(§4.1과 같음, scratch `xplan.py`):
  - 단위 = 실행된 routing 밖 PC를 진입으로 한 FR closure다. 설치 값은 실행된 것만 따라간다. 정지는 routing, 앞 단위, 다른 단위의 실행 leader다. block 시작은 전체 closure 기준으로 한 번 정한다(설치 값과 `84(A6)` 값 포함).
  - key = run마다 (그 PC의 첫 frame − 그 run의 첫 routing 밖 frame)의 최소값이다. 영역마다 key 순서로 220 block까지 모으고, 단위는 가장 작은 key 순서로 놓는다.
- **정확 bitmap 재관측으로 예측을 맞췄다**(C4~C8와 같은 방식):
  - 1차 계획(`xplan_obsA.json`)의 앞 k 단위를 `--extra-routed`로 가상 routing해 k = 1..8을 다시 관측했다. 그 결과 첫 단위만으로는 +40뿐이었다. 8 run 모두 C2 쪽 `22128`에서 멈췄는데, 이 PC는 `2210c`와 같은 TB의 직선 연속이라 X3 68 밖에서는 가려져 있었다.
  - 재관측의 첫 frame을 병합(`MS5_OBS2_MERGE`)하고 block 시작을 전체 기준으로 고쳐 2차 계획(`xplan_v2.json`)을 만들었다. 2차 계획을 다시 k = 1..8로 재관측한 결과는 아래 표의 예측과 모두 같다. 병합 뒤 다시 계획해도 단위 시작 SHA가 바뀌지 않는다(수렴).
  - 8 단위를 모두 routing한 재관측에서는 routing 밖 실행 PC가 0이다(숨은 PC 없음).
  - 재관측의 native 기록(`digest_chain`)은 모두 기준 관측과 같다.
- 단위 이름(제안, 결정 3): C 단위는 C9·C10, 영역 D 단위는 FR10~FR14, E 단위는 E2, 나머지 C는 C11~C14다.

| 순서 | 단위(계획 이름) | block | 명령 | byte | 실행 PC / 실행 | 재관측 예측 일치 frame | 다음 정지(재관측) | 특이 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (기준) | | | | | | 5,095 | C 8 run | |
| 1 | **C9**(C-1) | 220 | 454 | 1,996 | 126 / 18,815 | **5,839** (+744) | D 6(`6f1ca` `eaac0` `252b4` `71468`), C 2(`223fa`) | 목록 `JMP (A1)` 4(`21ce4` `21d36` `2224c` `22428`), `1f3e8` `21e48` `2210c` 포함, 자식 `36350` `371f8`(미실행) `eaac0` |
| 2 | FR10(D-1) | 214 | 516 | 2,314 | 149 / 43,952 | 6,267 (+428) | C 7(`1dccc` 4, `22148`, `223fa` 2), D 1 | MOVEM 2, 자식 `cde6e`; C7 표 칸 `252b4`→`252ce` 포함(결정 4) |
| 3 | C10(C-2) | 127 | 233 | 1,018 | 102 / 3,762 | 6,751 (+484) | D 8 | 새 계산 점프 `203ac`(표 `203b0`, 실행 칸 `203b0` `203c4` `203cc`→`20414`), C3 표 `2031c` 칸 `20324` `20340`→`203a0`, `JMP (A1)` `21e10` `2229a` `22378`, stub 후속 `1dccc` `1dc8e`, `1f3e0` |
| 4 | FR11(D-2) | 192 | 564 | 2,470 | 132 / 15,600 | 7,383 (+632) | D 8 | 계산 점프 `b42b4` `c54ae`, live `JMP (A0)` `b4034`, TRAP `b3e58`, MULS 4, MULU, MOVEM 3, 자식 `b3dbc` `b774a` `c5592` |
| 5 | FR12(D-3) | 212 | 611 | 2,664 | 126 / 3,717 | 7,977 (+594) | D 8 | MULS 6, MULU 3, MOVEM 3, 자식 `b3dbc` |
| 6 | FR13(D-4) | 207 | 478 | 2,290 | 161 / 5,004 | 10,374 (+2,397) | E 6(`3144`), D 2 | 계산 점프 `cc8da`(27칸), 자식 `bfd48` `d15c4` |
| 7 | E2(E-1) | 128 | 302 | 1,210 | 108 / 18,237 | 12,586 (+2,212) | D 3(`d177e` `3643e` `7177a`) | `e695a` 계열 [I: 마지막 목숨 뒤 화면], TRAP `e6d92` `e6dd0`, MOVEM 2 |
| 8 | FR14(D-5) | 199 | 445 | 2,000 | 91 / 11,664 | **14,500** (+1,914) | 없음 | MOVEM 2 |
| – | C11(R-1) `ca5c..1deea` | 171 | 350 | | 0 | 14,500 | | 자식 `369ba` `3fe7a` `3fedc` |
| – | C12(R-2) `1deea..1e5ec` | 171 | 367 | | 0 | | | MULS 4, MULU |
| – | C13(R-3) `1e5ec..21ea0` | 171 | 326 | | 0 | | | 자식 `1e67a` |
| – | C14(R-4) `21ea0..` | 170 | 422 | | 0 | | | `JMP (A1)` `21ebc` `21fd2`, ADDX 2, MULU 2, DIVU, MOVEM, 자식 `b3dfc` |

- [F] 검사: IO 단위 8개의 시작 합 1,499 = 전체 closure 시작, 명령 합집합 = 전체 closure 명령, 겹침 0, 빠진 실행 PC 0. 나머지 C11~C14는 683 block으로, C1 계획 나머지 981 가운데 IO 단위가 가진 298을 뺀 것이다. 이번 관측에서 실행되지 않는다.
- [F] 시작 목록(scratch `ms5-scratch/obs2/starts_<이름>.txt`) SHA256 앞 16자:
  - C9 `7297354e6f1ddb88`, FR10 `9b7c558e0a7fe4c9`, C10 `ec279a89d3ba30e8`, FR11 `0b9d751960bc3cc4`
  - FR12 `6565c7e2ab768e1d`, FR13 `e10ba8e15b814215`, E2 `3fd9ce2dd183641f`, FR14 `b885b234ad36b157`
  - C11 `bd40d783a32884e8`, C12 `8285f2efdb51168e`, C13 `d378a4957ff0245b`, C14 `20a92a5d244195af`
- [I] 순서 이유: D 코드는 모두 C 뒤에 실행된다. 그래서 C9를 먼저 하면 6 run의 첫 정지가 D로 바뀐다. C9와 C10을 합치면 347 block이라 한 단위에 넣을 수 없다. E2는 마지막 목숨 뒤에만 실행되므로 FR13 뒤에 둔다.

### 10.6 IO 비교 기준선(새 관측, 현재 `main` routing)

- 막는 것 [F]: `tools/verify_animation_machine_io.py`는 `--observation`을 받지만, 상수 `OBS_FILE_SHA_PREFIX = '66d30130d8a11a86'`과 `OBS_COMPARED_SHA = '4bb6b933…'`(1016~1023행)이 다른 관측을 거부한다.
  - observer SHA 검사(`pins.observer`)는 통과한다. observer 파일을 고치지 않았기 때문이다.
  - frontier 보고는 `aggregates.stage.baseline_p0_unrouted_pcs`를 쓰고, `P0`와 `P1`이 있어야 생긴다. 이 관측에는 둘 다 있다.
  - 음성 검사는 `P1` case 0이 없어 `negatives_ok` = null이다.
- 이번 실행: scratch `obs2/tools/verify_obs2.py`가 검증기를 수정 없이 import한다. 그리고 위 두 상수만 주어진 `observation.json`의 SHA와 저장된 `compared_sha256`으로 바꾼 뒤 `main`을 부른다. 다른 검사는 모두 그대로다.
- [F] 결과(`obs2/io_final`, 두 관측 벌 모두 같은 결과; `frontier.json` SHA256 `a39e85f6…`):
  - native 비교 frame 14,500 가운데 **일치 5,095**, 불일치 0(beyond 0), C++ 오류 0, chain divergence 0.
  - 수용 키는 `negatives_ok`(null)를 빼고 모두 true다. `frontiers_confirmed`도 true다.
  - 첫 정지는 확인된 C frontier 8 run이다: `2210c` 4, `21e48` 2, `1f3e8` 1, `1f070` 1. P0·P1 4 run은 끝까지 일치한다.
  - 예측 5,095와 같다. 이것을 다음 단위의 기준선으로 쓴다.
- [F] 기존 IO 비교(원래 관측, 이 branch, 검증기 기본 인자, scratch `obs2/io_historic`)는 바뀌지 않았다: 296 run, 일치 173,966 / 173,966, 불일치 0, C++ 오류 0, 수용 키 모두 true(`negatives_ok` 포함). §9와 같다.
- 최소 변경 제안(결정 2): 검증기에 알려진 관측 pin 표를 두는 것이다(`OBS_PINS = {'historic': (66d30130…, 4bb6b933…), 'io-ext': (9da40ac6…, b5d15d4f…)}`). `--observation`의 파일 SHA와 `compared_sha256`이 표의 한 쌍과 같아야 하고, 고른 이름을 `verification.json`의 `inputs.observation.pin`에 남긴다. 상수 두 개를 표 하나로 바꾸는 10행 안팎의 변경이고, 원래 관측의 결과는 바뀌지 않는다.

### 10.7 결정 요청(메인)

1. **관측 보관.** 관측은 지금 scratch에만 있다(`obs2/final`). **권고:** 사용자 승인 뒤 `artifacts/animation_machine_io_ext/`로 옮긴다(17 MB). 그 전까지는 위 명령으로 다시 만들 수 있다. 결정적이고 약 150초 걸린다.
2. **검증기 pin.** **권고:** §10.6의 pin 표. 대안은 scratch wrapper(`verify_obs2.py`)를 단위 runner에서 계속 쓰는 것이다. 다만 그러면 저장소만으로는 재현할 수 없다.
3. **단위 이름과 순서.** **권고:** C9, FR10, C10, FR11, FR12, FR13, E2, FR14(표 순서). 그 뒤 C11~C14는 IO 근거 없이 하거나(FR7~FR9처럼 단위 검증만), 다른 mission seed 관측을 기다린다(결정 6).
4. **주소 규칙과 실제 소유가 다른 PC.** C7 표 `25298`의 칸 `252b4` → `252ce`(root `25102`)는 주소 규칙으로 D가 되어 FR10에 들어갔다. **권고:** C10으로 옮긴다(2 block). C7 표 처리(실행 칸 `252a4`만 허용)를 고치는 일과 같은 단위에 두려는 것이다.
5. **앞 단위 표·목록의 갱신.** C3 표 `2031c`(실행 칸 `20324` `20340`)와 C7 표 `25298`(칸 `252b4`)은 지금 "미routing 칸 = 선언 정지"다. C10(과 결정 4)이 그 칸을 허용 목록에 더해야 한다. C9의 목록 `21aee`(`21602` `21d60` `21e48` `21e3a`)와 `216c8`(`21602`)의 handler는 C9 뒤 모두 routing된다.
6. **나머지 C11~C14(683 block).** [I] 대부분 등장 방식·탈것으로 보이는 stage 의존 경로다(`1d388` 사슬, `1de2c`/`1de34`). **권고:** 다른 mission의 stage seed(또는 stage 진행 seed)를 더한 관측을 만든 뒤 다시 잰다. 그 전에 구현하려면 C1 계획의 주소 분할을 쓴다.
7. **선언 정지 유지.** 아직 실행되지 않는 `1e67a` `1e918` `23c56` `36350` `371f8`은 계속 선언 정지로 둔다. **권고:** 이대로.
8. **`default-settings`의 범위.** 버튼 mask만 선언할 수도 있다. 그러면 목숨 1, 난이도 0이 되고 run이 일찍 끝난다(첫 시험 X1 94는 frame 712에서 끝남, C 110 PC). **권고:** 지금처럼 기본 설정 다섯 쓰기를 선언한다.

### 10.8 C9 상세 명세(§8과 같은 꼴)

다음 Opus 작업자가 C9 계약·실행부를 쓸 때의 입력이다. 수치는 scratch `obs2/plan/xplan_v2.json`과 `obs2/tools/xdetail.py obs2/plan/xplan_v2.json C-1`(출력 `obs2/plan/udetail_C9.txt`, 역어셈블 `obs2/plan/C-1.dis.txt`)이다.

#### 10.8.1 범위

- [F] **220 block, 454 명령, 1,996 byte, 20 범위.**
  - 시작 목록 `ms5-scratch/obs2/starts_C9.txt` SHA256 `7297354e6f1ddb88bbc0d2aed46990b57ee563eb244bdd6452d8b182c9017759`
  - 범위 byte를 이어 붙인 SHA256 `4b010840cf4b5a9405a971c7ff6404d69111ffc7217341c4f84807b27645fa24`
  - 실행된 시작 126, 실행되지 않은 시작 94.

| 범위(CPU = 파일 오프셋) | byte | 시작 | SHA256(앞 16자) | 내용 [I] |
| --- | --- | --- | --- | --- |
| `1d086..1d09e` | 24 | 4 | `62f0b738ca20a30c` | C8 `1d066` 뒤의 갈래 `1d086` `1d092` |
| `1ec74..1ed22` | 174 | 22 | `8bfeba981a7a9e00` | 설치 값 `1ec74` `1ecb8`(상태), `1b764` 기록 |
| `1f070..1f082` | 18 | 1 | `0bb1f2b54e1da9b6` | 미룬 입구 `1f070`(C4 `1ef0e` 상태의 갈래), `1b1ec` 기록 |
| `1f086..1f126` | 160 | 19 | `d4fab158b5ac5258` | 설치 값 `1f0ae`, 칸 `84` := `21602` |
| `1f3e8..1f3ec` | 4 | 1 | `921fb4b21e1a0f7b` | C7·C8가 쓰기만 하던 callback `1f3e8`: `LEA 1b26e(PC),A0` → C8 `1f3ec` |
| `1f48a..1f538` | 174 | 21 | `5a7ba80d97d35106` | 미룬 입구 `1f48a`, 설치 값 `1f4b6`, 칸 `84` := `21602` |
| `1fb28..1fb2e` | 6 | 1 | `a2b479890d32bf88` | 미룬 입구 `1fb28`(C8 `1fb02`의 BYTE `15` bit 7 쪽) |
| `20720..20738` | 24 | 1 | `a26a18a7b5e556b1` | C5 `20738` 앞 block |
| `208fa..2092c` | 50 | 8 | `36482efc41c1ea4a` | 미룬 입구 `208fa` |
| `20a4a..20bfe` | 436 | 41 | `271bc22a1dcc5680` | 설치 값 `20aec` `20b96`, 칸 `84` := `21602` 둘 |
| `20c00..20c30` | 48 | 7 | `cbfa73911c2cbc0d` | 설치 값 `20c30`은 쓰기만(실행 안 됨, 선언 정지) |
| `20cd8..20d72` | 154 | 11 | `32328cdf98533237` | 설치 값 `20d36`, 칸 `84` := `21602` |
| `21370..213da` | 106 | 6 | `1c0318ecfbfea2b1` | C5 표 `2094e`의 대상 `21370` 쪽, 칸 `84` := `21602` |
| `21ca4..21d60` | 188 | 28 | `008db994a1b0cad7` | 미룬 입구 `21ca4` `21d0e`. 칸 `84` := `21cd8`/`21d2a`(곧 실행), 목록 `21aee`/`216c8` + `JMP (A1)` `21ce4` `21d36` |
| `21e48..21e52` | 10 | 1 | `4babc8f180d852d0` | 목록 `21b0a`/`21aee`의 handler `21e48`: `LEA 1b9a8(PC),A0` → C8 `21e52` |
| `2210c..22148` | 60 | 3 | `e3d1b24d085289b6` | 둘째 칸 값 `2210c`와 직선 연속 `22128`(§10.5 재관측) |
| `22174..221ca` | 86 | 8 | `a1daf6e27bf7100c` | 기록 `22074` `220c0` `22028` |
| `22238..22286` | 78 | 13 | `5f005148b41735d3` | 칸 `84` := `22240`(곧 실행), 목록 `216c8` + `JMP (A1)` `2224c`, 칸 `84` := `22452` |
| `223a0..223fa` | 90 | 10 | `ccf4d235b2f650a9` | 미룬 입구 `223a0` `223d6`, 기록 `1b85e` `1b8ba` `1b8fe` `1b920` `1b964` |
| `22408..22472` | 106 | 14 | `76b29b8ad9e7d5ef` | 칸 `84` := `2241c`, 목록 `216c8` + `JMP (A1)` `22428`, 칸 `84` := `22452`, `22452` |

- [F] **진입**(실행 PC를 줄인 closure 진입): `1d092` `1f070` `1f3e8` `21e48` `2210c` `223a0` `21ca4` `22452` `1d086` `1f48a` `1fb28` `20720` `208fa` `223d6` `21d0e`.
- [F] **설치 값**(`MOVE.L #v,(A6)`): 범위 안 `1ec74` `1ecb8` `1f0ae` `1f3e8` `1f4b6` `20aec` `20b96` `20d36`, routing된 `1ed78` `1eeea` `21542`, 쓰기만 `20c30`.
- [F] **둘째 칸 `84(A6)` 값**: `21602`(routing, 6곳), `21cd8` `21d2a` `22240` `2241c` `22452`(범위 안, block 시작으로 강제).

#### 10.8.2 출구와 경계

- [F] **routing된 출구**: `28ae` `8ebe` `8ff4` `ce02` `1aa3a` `1cab6` `1cabe` `1cb08` `1cb38` `1cd98` `1cec2` `1cfbe` `1d0a4` `1eb98` `1eba0` `1eeea` `1f1d8` `1f2a4` `1f3ec` `1f538` `1f5d2` `1f5f2` `1f76e` `1f7a4` `1fa3c` `1fa68` `1fad2` `1fae8` `1fb2e` `201a2` `20738` `2092c` `20efc` `21430` `21520` `2156a` `215e6` `21602` `21baa` `21bc6` `21c1c` `21e52` `21ffc` `221ca` `43ea4` `49214` `49274` `4970a` `49fc6` `4bfc0` `ea680`.
- [F] **뒤 단위 정지**(실행되지만 C10이 가짐): `1f082` `20bfe` `22148` `22286` `223fa`.
- [F] **목록 `JMP (A1)` 4곳**(C3 `215e6` 목록 조회 뒤, C3·C4·C5·C8 결정과 같은 규칙):
  - `21ce4`: 목록 `21aee`([F] ROM: (`21602`, 0) (`21d60`, 2) (`21e48`, 3) (`21e3a`, 4), LONG 0). 대상 넷은 C9 뒤 모두 routing된다.
  - `21d36` `2224c` `22428`: 목록 `216c8`((`21602`, 0) 하나).
  - 그 밖의 A1은 checked jump-target 오류다.
- [F] **자식**(`MOVEA.L #v,A0` 뒤 `JSR 28ae`/`2986`): `36350` `371f8`(IO에서 실행 안 됨, 선언 정지), `eaac0`(FR10).
- [F] TRAP·DIVU·MULU/MULS·MOVEM·계산 점프 표는 없다. 고정 ROM 기록 포인터(`LEA d(PC)`)는 26곳이고 대부분 `1b1xx..1bcxx` 상태 기록이다. 넘기기만 하는 것이 대부분이다 [I].
- [F] **block 경계를 넘는 C**(block 첫 명령이 Bcc, scratch `cscan.py`; Z 쪽은 계약에서 확인):
  - 소비자 14곳: `1eca0` `1ed14` `1f118` `1f52a` `20900` `20a50` `20bd2` `21cae` `21cb6` `21cbe` `21ce0` `21d32` `22248` `22424`.
  - `21ce0` `22248` `22424`는 `215e6`의 C(목록 Set/Clear)를 읽는다. 나머지는 각 callee의 C이며, 계약에서 생산자를 정한다.
  - flag를 넘기는 곳: `22188`·`2226c`(다음 block으로 떨어짐), `22284`·`22450`(RTS로 돌려줌, C 생산자 후보).

#### 10.8.3 IO·seed

- [F] 실행 run 8개(X1~X4 × case 68·94). 각 run의 C9 PC 첫 frame(처음 ~ 마지막):

  | run | case 68 | case 94 |
  | --- | --- | --- |
  | X1 | 440..515 | 224..309 |
  | X2 | 438..650 | 216..311 |
  | X3 | 436..659 | 221..467 |
  | X4 | 440..1,108 | 280..948 |

  플레이어 node는 `100cb8`이다(관측 field `p1cb`).
- [F] IO 예측(C9만 연결, 재관측 `obs2/reobs/v2_u1`): 5,095 → **5,839**(+744).
  - 첫 정지는 D 6 run(`6f1ca` `eaac0` `252b4` `71468`, FR10)과 C 2 run(`223fa`, C10, X4)으로 옮겨 간다.
- [F] seed state: 새 관측의 state pack `obs2/final/states/X*/0{68,94}.pack.gz`(모든 frame). D1 자연 seed와 원래 IO 관측은 C9 코드를 실행하지 않는다.

#### 10.8.4 영향받는 기존 시험·spec

- [F] C9 시작을 정지 PC로 쓰는 시험·spec(정지 → 실행으로 기대값이 바뀜):
  - `engine/tests/animation_machine_player_c3_test.cpp`(`21e48` 773행 등, `2210c` `21ca4` `21d0e` `22452` `223a0` `223d6`)
  - `_c4_test.cpp`(`21e48` `2210c` `223a0` `223d6` `1f070`)
  - `_c5_test.cpp`(`21e48` `208fa` `2210c`)
  - `_c8_test.cpp`(`21e48` `1f48a` `2210c` `223d6` `223a0` `21d0e` `1fb28`)
  - `tools/unit_fixture_specs/pc3.py` `pc4.py` `pc5.py` `pc8.py`, `tools/generate_animation_machine_player_c5_test_table.py`
  - 앞 단위 계약의 방식대로 이전 기대값을 기록하고 갱신한다.
- [I] C8 `JMP (A1)` `21d9e`의 허용 대상 `21e48`(routing 밖 → 선언 정지)이 routing된 handler가 된다. C8 시험의 그 행이 바뀐다.
- [F] IO 기준: 원래 관측은 C9 코드를 실행하지 않는다. 일치 173,966은 그대로여야 한다. 새 관측의 기준은 5,095 → 예측 5,839다.

### 10.9 미확인

- [U] `default-settings`가 실제 기계의 상태와 같은지. 카드·backup 상태와 BIOS가 USER 초기화를 언제 부르는지는 모른다. 선언으로만 둔다.
- [U] 남은 C11~C14가 어떤 입력·stage 조건에서 실행되는지. `1d388`의 D7 출처, `1aa3a`의 bit, 탈것 여부.
- [U] 이름(사격·점프·수류탄·웅크림, 마지막 목숨 뒤 화면 `e695a` 계열, D 단위의 적·stage 코드)은 동작에서 붙인 것이다.
- [U] 주기 입력의 X3/X4가 X1/X2보다 오래 사는 이유(입력 탓인지 우연인지).
- [U] D 단위 FR10~FR14의 root 분류는 주소 규칙과 호출자 재분류에 따른다. 표 칸처럼 실제 소유가 다른 PC가 더 있는지는 단위 계약에서 확인한다(결정 4).
- [I] 재관측은 run 12개 전체를 했다. key와 예측은 이 두 seed 묶음, mission 0에만 해당한다.

### 10.x 메인 결정(2026-10-23)

- 확장 관측의 설계와 측정을 받아들인다. 기존 observer 파일은 바뀌지 않았다(SHA256 `facf49fa…`, `main`과 같음). 기존 IO 비교는 그대로 173,966/173,966이다.
- `default-settings` host 쓰기(버튼 mask `10f01c`/`10f020`, `10f026`, 목숨 `10fd88`, `10fd8b`)는 선언으로 받아들인다. 원래 설정 경로(`8fa → bcb4 → bbfa → bc1e`)를 실행했다는 주장이 아니다.
- 단위 이름과 순서는 C9, FR10, C10, FR11, FR12, FR13, E2, FR14로 한다(§10 표).
- C7 표 `25298`의 칸 `252b4 → 252ce`는 C10에 넣는다(주소 규칙으로 D가 된 것). C10은 C3 `2031c`와 C7 `25298`의 허용 칸을 늘린다.
- 미실행 선언 정지(`1e67a` `1e918` `23c56` `36350` `371f8`)는 그대로 둔다. C11~C14는 다른 mission seed 관측 뒤에 다시 잰다.
- 검증기의 관측 pin은 "알려진 관측 pin 표"(원래 관측 + 확장 관측)로 바꾼다. 원래 관측의 결과는 바뀌지 않아야 한다. 이 변경은 C9 단위에서 한다.
- 확장 관측을 `artifacts/`에 둘지는 사용자 결정이다. 그때까지 scratch `ms5-scratch/obs2/final/`을 쓰고, 단위 IO 확인은 scratch 경로로 한다.

### 10.y 확장 관측 완료(2026-10-24, 메인)

- [F] C9·FR10·C10·FR11·FR12·FR13·E2·FR14를 연결한 뒤 확장 관측 IO는 native frame 14,500 전부 일치한다. 불일치 0, 예상 밖 C++ 오류 0이고, 두 번 실행 결과가 같고, 수용 키도 모두 true다. 실행된 routing 밖 PC는 C 0 / D 0 / E 0이다. 원래 관측도 173,966/173,966 그대로다.
- [F] 단위별 확장 관측 IO(예측 = 실측):

  | 단위 | 일치 frame |
  | --- | --- |
  | 시작 | 5,095 |
  | C9 | 5,839 |
  | FR10 | 6,230 |
  | C10 | 6,751 |
  | FR11 | 7,383 |
  | FR12 | 7,977 |
  | FR13 | 10,374 |
  | E2 | 12,586 |
  | FR14 | 14,500 |

- 남은 일: 이 관측에서 실행되지 않는 C11~C14(683 block)과 선언 정지가 남았다. FR14 계약의 "확장 관측 완료 판정"에 목록이 있다. 다른 mission seed, P2 입력, game over 뒤 진행을 관측해야 다음 근거가 생긴다.
