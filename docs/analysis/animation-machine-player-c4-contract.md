# 영역 C 단위 C4(슬롯 callback `4e94e` 본체·숫자 출력·게이지, `4e758` 상태, 플레이어 상태 `1eeea`/`1ef0e`, 칸 상태 `21d60`/`21d92`, 232 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §4.2의 C4 행과 아래 "C4 상세 명세"(계획 §8과 같은 꼴, 이 계약에서 새로 씀)를 기준으로 삼고, 구조·공통 규칙은 C3 계약(`animation-machine-player-c3-contract.md`)·C2 계약·C1 계약을 따르며 다른 점만 적는다. 단위 이름은 C4, 파일 접두어는 `player_c4`(C++) / `pc4`(V1 spec)다(계획 메인 결정 7). 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기는 없다. 장치 쓰기는 video 주소/자료 port LONG `3c0000`(CPU 주소)뿐이다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `d31d04e`(branch `claude/c4-core`; C1 `ff2e284`, E1 `6308f75`, C2 `5d686ac`, C3 `d31d04e` routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `0a8379cacc854d593b262cbb4989dc68a17dfacb3e58b06e0d3e833d87474b26`, `animation_machine_internal.h` `dee2f94720c4f7abd38131660b83a741fa36ada560a56357fafd8cb3f2a0e112`.
- [F] 관측 입력: native IO 관측 `artifacts/animation_machine_io_native`(읽기 전용; state pack `states/P1/068.pack.gz` `094.pack.gz` `106.pack.gz` 등, `boot-title-start/boot.pack.gz`)와 계획의 보정 관측 `ms5-scratch/c1/reobs/`(실행 집합 측정용, 계획 메인 결정 1; 읽기만).
- [F] 시작 목록: 계획 scratch `ms5-scratch/c4/starts_C4.txt`(230개, SHA256 `279a317b969ea012f6ab68acc994fcf91b8896b509c79d49d8a7654831385180`, 계획 §6 표의 `279a317b969ea012`와 같음)에 결정 1의 2개(`4e57e` `4e8e6`)를 더한 **`ms5-scratch/c4/starts_C4_final.txt`(232개, SHA256 `ab2c1f99e768e8f6ca03a0deda7c67ec1d7a65e3ba708e6877e7c72f870d2bb0`)**. 실행부의 `case` label 232개, V1 spec `STARTS`와 집합이 같다(작업자 확인).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/c4/`
  - `remeasure/`(재측정: `remeasure2.py` → `r4.json` `r4_C4.txt`), `plan/udetail_C4.txt` `plan/C4.dis.txt`(범위·출구·역어셈블), `work/c4ranges_plan.txt` `work/c4ranges_final.txt`(범위), `work/callers_c4.py`(진입 호출자), `work/writers_c4.py`(field 쓰기 명령 검색), `work/straightline_c4.py`(IO 자연 frame의 직선 연속 추적), `work/straight_static.py`(정적 직선 연속 검사), `work/natsig.py`(자연 frame 선택), `work/c4io.py`(IO run·frame), `work/firststops.py`(예측 첫 정지 PC), `work/hexsearch.py`(기존 파일의 C4 범위 상수 검색), `reobs_c4/obs` `reobs_c4/obs2`(C4 routing의 정확 bitmap 재관측, 결정 1), `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **재측정 전**(`MS5_REOBS=…/c1/reobs dleft.py`, routing `0a8379ca…` = C1+E1+C2+C3): 실행된 routing 밖 PC C **529** / E **12** / D 0, 예측 일치 frame **169,482**, 첫 정지 영역 C 14(`dleft_before.log`). C3 계약의 C3 뒤 값과 같다.
- [F] **closure 재측정(C1+E1+C2+C3 routing 상태)**: C3 작업자 방식 그대로 계획 spec `plan/plan_final.json`과 계획 당시 key(`remeasure/keys_old.json`)로 현재 routing에서 `cplan3`을 돌렸다(`remeasure2.py`, `trial_logs/remeasure_r4.log`). **C4 = 229 block, 520 명령, 2,000 byte**(시작 목록 SHA `58eda6688d245a1e…`), 예측 170,691(+1,209), 남은 C 363 / E 12, 첫 정지 C 14.
  - [F] 계획 목록과의 차이는 `1ef08` 하나다(계획 230 = 재측정 229 + `1ef08`). `1ef08`(`MOVE.L #1ef0e,(A6)`)은 `1fb78 BCS.W 1ef08`(C11 미실행 block `1fb74`)의 분기 대상이다. C2가 routing되어 closure가 `1fb74`에 닿지 않으므로 재측정에서는 block 시작이 아니게 되었다. [I] 계획 §4.1("block 시작은 전체 closure 기준으로 한 번만 정한다")대로 `1ef08`을 시작으로 둔다. 시작으로 두지 않으면 C11이 `1fb78`을 routing할 때 C4 block 안으로 들어가는 분기가 된다.
  - [F] 같은 실행의 C5 `e444432f…`(201 block), C7 `f95f6bbd…`(214)는 계획 표(203 / 217)와 다르다. C3 결정 10의 `202a0` `1cde0` `1cdf0` `1cdfa`가 빠진 값이다. C9~C13 차이는 C3 계약에 적은 측정상의 차이와 같다.
- [F] **정적 범위(계획 230 block)**: 28 범위, 2,000 byte(이어 붙인 SHA256 `d9b324ffcd58480181156ce2e8b23f92b23f60457e95e923fb78e6acb0c30c9e`). **결정 1 반영 뒤(구현)**: **29 범위, 2,022 byte**(이어 붙인 SHA256 `77753d83155cf1c67226a64e8ae39887d1ea4090c648bcffefcc7edac0953948`), 524 명령, 짝수 PC 1,011(내부 779), 시작 232. 범위 안에 기존 routing된 PC는 없다(`make test`의 내부 PC 779개 검사가 모두 C4 오류로 거부됨).
- [F] **측정 결과**(`dleft.py`, `MS5_REOBS=…/c1/reobs`): C4 연결 뒤(최종 routing `9747100c…`) C 529 → **361**(−168: 실행된 C4 PC 168개, 모두 block 시작), E 12, 예측 일치 frame **170,691**(+1,209 = 13 run × 93 frame), 첫 정지 C 14. 계획 표의 366과 다른 5개는 C3 결정 10의 3개와 결정 1의 2개(`4e57e` `4e8e6`)다.
- [F] **C4 routing의 정확 bitmap 재관측**(결정 1, `reobs_c4/obs2`, 관측 때 routing `5a515747…` = 최종 routing과 같은 범위(dispatch 줄바꿈 전), `observation.json` compared_sha256 `704da9db94324e6f…`; `reobs_check.py`: 18 run 모두 native 기록이 원래와 같음): `MS5_REOBS=…/reobs_c4/obs2 dleft.py` → C 361 / E 12, 예측 **170,691**, 첫 정지 C 14. 예측 첫 정지(`work/firststops.py`): P1 94 계열 8 run frame **311**, P1 68 계열 4 run frame **527**, boot-title-start frame **431**에서 C5 `20240`(`20238 SUBQ.W #1,90(A6); BNE.W` 의 fall-through), boot-demo-0 frame **381**에서 C6 `1d398` …(C3 뒤와 같음).

## C4 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **계획 230 block, 520 명령, 2,000 byte, 28 범위**(시작 목록 SHA256 `279a317b…`, 범위 이어 붙인 SHA256 `d9b324ff…`) **+ 결정 1의 2 block = 232 block, 524 명령, 2,022 byte, 29 범위**(시작 목록 SHA256 `ab2c1f99e768e8f6ca03a0deda7c67ec1d7a65e3ba708e6877e7c72f870d2bb0`, 범위 이어 붙인 SHA256 `77753d83155cf1c67226a64e8ae39887d1ea4090c648bcffefcc7edac0953948`). 아래 표는 구현 범위다.

| 범위(CPU = 파일 오프셋) | byte | SHA256(앞 16자) | 시작 | 내용 [I] |
| --- | --- | --- | --- | --- |
| `371e..377a` | 92 | `f8f52c848a29c3f4` | 12 | 숫자 출력 `371e`(D4.W 자리, D7.W 값, D3.B 앞자리 표시): `DIVU` 표 `377a`, 문자 표 `370c`, `JSR (A1)` = `3650` |
| `3786..37e2` | 92 | `421ed3414f521ae9` | 12 | 숫자 출력 `3786`(앞 공백 생략, A0 보존) |
| `1be3a..1be6a` | 48 | `3eac731db3a635bd` | 7 | C helper: 플레이어 node(`A5−7348`/`−7258`) `289e` 판정과 BYTE `a8` bit 4 |
| `1bf94..1bfb4` | 32 | `4cf7d58e02c60840` | 4 | `289e` 뒤 D0.W/D2.W := `ffff` 또는 BYTE `9e`/WORD `76`(A0) |
| `1c052..1c072` | 32 | `29e40f407cac9188` | 6 | `4da08`의 C, WORD `545c`/`546c(A5)` |
| `1c086..1c0d2` | 76 | `dcdb497130f061d6` | 8 | `4d7a6`·`4d9a2` 뒤 D0/D1 := BYTE 쌍 |
| `1ceb0..1cec0` | 16 | `0c844003600e72bc` | 2 | BYTE `15` bit 0 → BYTE `a7` bit 3 설정(C2 RTS `1cec0`로) |
| `1cec2..1cef8` | 54 | `3078c22765ff39ce` | 6 | D1 := 0/1/2(BYTE `aa`, `a7` bit 3), BYTE `15` bit 0 반전 |
| `1cfbe..1cfce` | 16 | `307f9bb4f8b39c81` | 1 | A0 := LONG 표 `1cfce` + 4 × BYTE `9e` |
| `1d09e..1d0c2` | 36 | `be8e38d0058057fb` | 7 | LONG `64(A6)` := ±LONG (A0)(D0 bit 2·3) |
| `1eeea..1ef4c` | 98 | `66861124a232761d` | 9 | 상태 `1eeea`(`1cab6`, 설치 `1ef08` → `1ef0e`), callback `1ef0e`(BYTE `92` 포화 증가, `LSR.W 88`), `1cd98` |
| `1ef6c..1efa4` | 56 | `f53655ea4af1058a` | 7 | 입력 요약 bit 분기, `1cec2` |
| `1efb0..1efd6` | 38 | `c42e612c7ff4aceb` | 7 | `1ed34`의 C, `1d09e` `4bfc0` `ce02` `49fc6`, `201a2`로 |
| `21c72..21c74` | 2 | `96e3a4f65944fc97` | 1 | `JMP (A1)`(C3 `21c66`의 목록 `21aee`) |
| `21d60..21d9e` | 62 | `5aa9f77e3414ea99` | 9 | 목록 handler `21d60`: `21bc6` `21baa`, `1cabe`, 칸 `84` := `21d92`, 목록 `21b0a` 조회 |
| `21da0..21dd0` | 48 | `6ecfd37c03ee6aea` | 8 | `1cd98` bit 분기, `21be6`, `2156a`로 |
| `4d9a2..4d9ba` | 24 | `dcd2cf6618a2193d` | 4 | D7.B := BYTE `29(5cba/5ce6(A5))` |
| `4da08..4da2a` | 34 | `0e023abeb0eff1a9` | 5 | C helper: WORD `5cba/5ce6(A5)`, D7 := WORD `20` |
| `4e4e2..4e536` | 84 | `a25d5227cb83dbc8` | 3 | 숫자 3개(`35a2`): WORD `7c`/`82`/`80` |
| `4e538..4e572` | 58 | `be462f72748caed8` | 5 | `35a2` 문자열 출력 위치(WORD `76`) |
| `4e57a..4e58a` | 16 | `ca69bdfb90b5f337` | 2 | `4e564`의 `+80` 쪽, 결정 1: `4e57e LEA e84c8.l,A1; JMP 3918.l` |
| `4e758..4e7a2` | 74 | `a27d79a74d177550` | 12 | `4e732` 상태 뒷부분: `ca32`의 C(`SCS`), `4a974`의 Z, `4e564`/`4e538` |
| `4e8e6..4e8f0` | 10 | `2043316a7e499524` | 1 | 결정 1: C1 `4e8e0`의 직선 연속, `MOVE.W 76(A6),D0; JSR b7a28.l` |
| `4e962..4e97e` | 28 | `ef4793aa4ab8c13f` | 4 | `4e94e` 상태: `1be3a`의 C(`SCS`), BYTE `a1`/`9a` |
| `4e986..4eb50` | 458 | `1416170c60ac0fd1` | 46 | `4e94e` 본체: HUD 문자열(`3902`), 숫자(`3786`/`371e`), `4ee7a`, 표 `4e4a2`/`4e43e`, `36ba`, `1c052`, `1c086`, `4eef4` `4f22c` `4f13c` |
| `4ee7a..4eea2` | 40 | `79c8d6da63e6d74d` | 1 | WORD `88..94` 지우기, `4f08a`로 |
| `4eef4..4ef08` | 20 | `f7f6c101f25b4f39` | 3 | `4d7a6` D0.B |
| `4f118..4f184` | 108 | `13dceca15b2fcf77` | 13 | `DIVU.W 92(A6)`(C를 돌려줌), `MULU.W #2800` / `DIVU.W D6,D7` |
| `4f1ac..4f2ba` | 270 | `73f1564387cad3f3` | 27 | 게이지: video port LONG `3c0000` 쓰기 반복, 값 `10dddc`/`10dde4` |
| 합계 C4 | 2022 | 이어 붙인 바이트 `77753d83…` | **232** | 짝수 PC 1,011(내부 779) |

- [F] **진입(실행된 PC를 줄인 closure 진입, `udetail.py C4`)**: `371e` `3786` `1bf94` `1c052` `1c086` `1ceb0` `1cec2` `1cfbe` `1d09e` `1eeea` `21c72` `21d60` `4e4e2` `4e564` `4e758` `4e986` `1be3a` `4e962`. 실행된 시작 166개(계획), 실행되지 않은 시작 64개. 결정 1의 2개는 보정 관측에도 실행으로 기록되어 있다(`work/c4io.py`: C4 PC 168개, 모두 시작).
- [F] **호출자**(ROM 전체 직접 분기 검색, `work/callers_c4.py`): `371e` ← `4ead2` `4eb3e`(C4), `50118` `50130` `50148` `50160`(다른 단위); `3786` ← `4ea0e`; 내부 PC(`3722` … `37dc`)는 루프 안 분기만; `1be3a` ← `4e966`; `1bf94` ← `4ea1e`, `becaa` `bece0` `d617c` `d64fe`(뒤에서 D2/D0만 읽음); `1c052` ← `4ea70`; `1c086` ← `4eae0`; `1cec2` ← `1ef7c`와 뒤 단위 7곳(모두 D1을 읽음); `1cfbe` ← `1ef1c`·`1d09e`와 뒤 단위 6곳; `1d09e` ← `1efb8` `1f052` `1fb80`; `1d0a4` ← `1d08e` `1d09a`(BRA, 뒤 단위); `1eeea` ← `1ef8c`와 C2·뒤 단위 6곳(BNE/BEQ); `1ef08` ← `1fb78 BCS`(C11); `1efb0` ← `1efa0 BNE`만; `4d9a2` ← `1c09c`; `4da08` ← `1c052`; `4e538` ← `4e79e` `4e826`(C1); `4e564` ← `4e796`, C1 `4e81e`, `4e9a8`, `4ecd4` `4ee74`(뒤 단위); `4e8e6` ← C1 `4e8dc BNE`·`4e958 BCC.B`와 C1 `4e8e0`의 직선 연속; `4ee7a` ← `4ea14` `4ef1c` `4f14c`; `4eef4` ← `4eb44`; `4f118` ← `4f142`; `4f13c` ← `4eb4c`; `4f22c` ← `4eb48`, C1 `4e8f8`(C6 block). `4e4e2`는 C1 `4e4da`의 fall-through, `4e758`은 C1 `4e74c`의 다음, `4e962`/`4e986`은 C1 `4e94e`/`4e97e`의 다음, `21c72`는 C3 `21c6e`의 Set 쪽, `21d60`은 목록 handler(C3 `21620`·이 단위 `21c72`), `21d92`는 칸 `84` 값(C3 `201a6 JSR (A4)`).
- [F] **설치 값**: `1ef08 MOVE.L #1ef0e,(A6)`(곧바로 그 값으로 들어감; 노드 callback). 칸 `84`: `21d8a MOVE.L #21d92,84(A6)`(곧바로 들어감; C3 허용 목록 34개 안).
- [F] **IO run의 node**(`work/natsig.py`, `cbseq.py`): 슬롯 node `1009a8`(P1, callback C1 `4e94e`)이 frame 218부터 C4 `4e962`/`4e986` 본체를, `100a6c`(callback C1 `4e732`)이 `4e758` 상태를, 플레이어 node `100cb8`이 frame 219~391에 callback `1ef0e`을 실행한다(칸 `84` = `21d92`).

### 계산 점프와 표(결정 2)

- [F] **`3772 JSR (A1)` / `37d8 JSR (A1)`**(block `3766` / `37ca`): A1을 쓰는 명령은 함수 진입 `371e LEA 3650(PC),A1` / `3786 LEA 3650(PC),A1`뿐이다. 루프 안의 피호출 `3650`(routed, `animation_card_menu_open_block`: `SWAP D0` … `MOVE.L D0,3c0000.l` … `RTS`)은 A1을 바꾸지 않는다. 루프 머리 `3722`/`378a`와 그 안의 PC로 들어오는 분기는 루프 안의 `BNE.B`/`BNE.W`/`BCC.W`/`BEQ.W`/`BRA.W`뿐이다(`callers_c4.py`).
  - 허용 대상 = `3650` 하나. 그 밖의 A1(0, 홀수, 24 bit 밖 bit가 선 값, 다른 routed PC 포함)은 `unsupported animation player c4 jump target`(checked, rollback, 복귀 LONG을 넣기 전). [I] 68000은 주소 bit 24..31을 버리지만 C++는 32 bit로 비교한다(C3 결정 2와 같음).
- [F] **`21c72 JMP (A1)`**(block `21c72`, C3 `21c6e BCC`의 Set 쪽): A1 = C3 `215e6`이 목록 `21aee`(C3 `21c66 LEA 21aee(PC),A0`)에서 key WORD = BYTE `9c`로 찾은 handler LONG. 목록 `21aee..21b0a`([F] ROM 바이트): (`21602`, 0) (`21d60`, 2) (`21e48`, 3) (`21e3a`, 4), LONG 0.
  - 허용 대상 = 이 4개 handler. routing된 것은 `21602`(C3)·`21d60`(C4)이고 `21e48` `21e3a`는 뒤 단위 정지(다음 dispatch의 `unsupported animation machine PC`). 그 밖의 A1은 `unsupported animation player c4 jump target`.
- [F] `21d9e JMP (A1)`(목록 `21b0a`: (`21602`,0) (`21c22`,1) (`21e48`,3) (`21e3a`,4))은 C8 block이다(`21d9a BCC`의 Set 쪽 = 뒤 단위 정지).
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙):
  - DIVU WORD 표 `377a + sext(2 × D4.W)`(`373a`/`37a2`; [F] ROM 값 `0000 0001 000a 0064 03e8 2710`, 첫 칸 0). 경로상 D4.W ∈ 1..5(`CMPI.W #6`; `BCC`), 직접 진입은 `D5.W`의 아무 값.
  - 문자 BYTE 표 `370c + sext(D2.W)`(`3766`/`37ca`; "0123456789ABCDEF" 다음 `20` `00`). 경로상 D2.W ∈ 0..9 또는 `10`.
  - 기록 LONG 표 `1cfce + 4 × BYTE 9e`(`1cfbe`; [F] ROM 4칸 `1cf1e 1cf3e 1cf1e 1cf1e`, 그 뒤는 코드). [F] 플레이어 node의 BYTE `9e`를 쓰는 명령은 `1bd3a`(0)와 `1c1ec`(표 `1c1d8`)다.
  - LONG 표 `4e4a2 + sext(4 × D2.W)`(`4ea24`; D2 = `1bf94`가 돌려준 `ffff` 또는 WORD `76`(A0)) → A0(`362a`에 넘김). LONG 표 `4e43e + sext(4 × D1.W)`(`4eafc`; D1 = `1c086`이 돌려준 BYTE) → A0(`3902`에 넘김).
  - 넘기기만 하는 포인터: 문자열 `4e33a` `4e34c` `4e35e` `4e3aa` `4e3bc` `4e3ce` `4e3f1` `4e47a`(A0), 기록 표 `1b6e0`(`1cab6`) `1b7da`(`1cabe`), 목록 `21b0a`(C3 `215e6`), `e84c8`(A1, `3918`).

### DIVU·MULU(결정 4)

- [F] DIVU 6곳: `373e DIVU.W 377a(PC,D5.W),D2` `3748 DIVU.W #a,D2`(block `373a`), `37a6` `37b0`(block `37a2`, 같은 꼴), `4f130 DIVU.W 92(A6),D0`(block `4f130`), `4f172 DIVU.W D6,D7`(block `4f16e`). MULU 1곳: `4f16e MULU.W #2800,D7`.
- [F] 68000 의미(MC68000 사용자 설명서): `DIVU.W <ea>,Dn`은 LONG Dn을 무부호 WORD로 나눈다. 몫 ≤ `ffff`이면 Dn := 나머지 WORD << 16 | 몫 WORD. 몫 > `ffff`이면 overflow: V를 세우고 **Dn은 바뀌지 않는다**. 제수 0이면 zero-divide 예외(vector 5)다. `MULU.W #imm,Dn`은 Dn 하위 WORD × imm(무부호 16 × 16 → 32 bit)을 LONG Dn에 넣는다.
- [I] 경로상 overflow·0은 나오지 않는다: `373a`는 `MOVEQ #0,D2; MOVE.W D7,D2` 뒤 제수 1..`2710`; `4f130`은 `CLR.L D0; MOVE.W 94(A6),D0` 뒤(WORD `94` ≠ 0일 때만) 제수 WORD `92`(0이면 예외); `4f16e`는 `D6.W` ≠ 0, `D7.W` < `D6.W`일 때만이라 몫 < `2800`. 직접 진입(block 시작)은 아무 레지스터로 들어오므로 실행부는 일반 의미를 구현한다.
- 결정: `pc4_divu`가 위 의미를 그대로 구현한다(몫·나머지 무부호, overflow면 레지스터 그대로). **제수 0은 checked 오류 `unsupported animation player c4 divide by zero`**(rollback; 예외 처리·vector 5는 이 machine의 범위 밖이고, C++ 0 나눗셈 UB를 만들지 않는다). DIVU 뒤의 N/Z/V/C는 어느 block도 읽지 않는다(`3742 ANDI.L`, `374c SWAP` 뒤 `374e TST.W D2`가 다시 정함; `4f134 MOVE.W` 뒤 `ORI.B #1,CCR`; `4f174 TST.B`). 그래서 flag는 모델링하지 않는다. `4f130`은 DIVU 뒤 `ORI.B #1,CCR; RTS`라 C = Set(결정 5).

### video port(결정 6)

- [F] `4f1c4` `4f1e0` `4f1f4` `4f210` `4f220` `4f294` `4f2ac`가 `MOVE.L D0,3c0000.l`(LCD 주소/자료 port)을 쓴다. [F] 기존 실행부 규약(카드 메뉴 `animation_machine_card_menu_close.cpp` "one original LONG write is one observed video event", HUD `video`)과 같이 원본 LONG 쓰기 하나를 `VideoPortWrite{3c0000, 4, value}` 하나로 낸다. V1은 native의 WORD 쌍(`3c0000`/`3c0002`)을 LONG 하나와 같게 비교한다(`compare_ports`).
- [F] `ADDI.L #200000,D0`(`4f1c4` 등)와 `ADD.L D1,D0`(`4f294` `4f2ac`)은 32 bit, 올림 버림. `ASR.W #8,D7`(`4f1f4`)는 WORD 산술 shift, `ADD.B D7,D0`은 하위 BYTE만.

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `289e` `35a2` `362a` `36ba` `3650`(`JSR (A1)`) `3902` `3918` `8da2` `ca32` `ce02` `49fc6` `4a974` `4bfc0` `4d7a6` `4f08a` `b7a28`, 앞 단위 `1cab6` `1cabe` `1cd98` `1cec0` `1ed34` `1f1d8` `1fae8`(C2) `1f126` `201a2` `2156a` `215e6` `21baa` `21bc6` `21be6` `21f30` `21f40` `21ffc` `21602`(C3) `4e4da` `4e7a2` `4e8f0` `4e97e` `4eb50`(C1).
- [F] **뒤 단위 정지**(실행되지만 뒤 단위가 가짐, routing 밖; V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS`):
  - C5: `21f4c`(`21dc8 BCS`). C6: `1efa4`(`1ef9a` fall-through) `4e572`(`4e564` fall-through). C7: `1f2a4`(`1ef6c BNE`). C8: `1ef4c`(`1ef44` fall-through) `21d9e`(`21d9a` fall-through, `JMP (A1)`).
  - 미룬 입구(나머지 단위): `1efd6` `1f070`(C11) `21dd0` `2210c`(C12) `223a0` `223d6` `4ef08`(C13).
  - 계산 점프의 routing 밖 허용 대상: `21e48` `21e3a`.
  - C4 run이 지나가는 C1~C3 block의 남은 정지(pc1·pc2·pc3 `EXIT_STOPS` 가운데 아직 routing 밖인 32개; C1 TRAP `4e69a` 포함)도 pc4 `EXIT_STOPS`에 넣었다.
  - [I] fall-through(직선 다음 PC)는 `1ef4c` `1efa4` `4e572` `21d9e`다. 모두 조건 분기의 fall-through라 TB 시작으로 기록되므로 가려지지 않는다(결정 1의 직선 연속과 다름).
- [F] TRAP 없음(`4d7a6` 안의 `4d7f0 TRAP #f`는 다른 실행부의 경계). ROM·RAM 실행 없음. 특이 명령: DIVU 6, MULU 1, `ASR.W #8`, `LSR.W` 메모리(`1ef0e`), `SCS` 3(`4e75e` `4e96c` `1ef0e`), `BCHG`/`BCLR` 메모리 BYTE.

### block 경계를 넘는 flag(결정 3·5)

scratch `cscan.py starts_C4_final.txt`와 호출자 검색으로 정했다. block 경계 너머의 Z를 읽는 block은 `4e77a` 하나다(다른 `BEQ`/`BNE`/`BPL`/`BMI`/`BGT`는 같은 block의 `BTST`/`BCHG`/`BCLR`/`TST`/`CMP`/`CMPI`/`MOVE`/`AND`/`SUBQ`/`SUBI` 뒤). X를 읽는 명령은 없다.

- [F] **C 소비 block 11개**(Clear 쪽 / Set 쪽; Unknown C면 `player c4 caller requires known carry`):
  - `1be50 BCC`(`289e`), `1bf9a BCS`(`289e`), `1c058 BCC`(`4da08`), `21d6c BCS`(`21bc6`, C3), `21d74 BCS`(`21baa`, C3), `21d9a BCC`(`215e6`, C3), `21dc8 BCS`(`21be6`, C3), `4f144 BCS`(`4f118`), `1efb4 BCS 1f126`(`1ed34`, C2: 들어온 C를 돌려줌).
  - `SCS.B D0` 2개: `4e75e`(`ca32`, C1의 C 생산자 `CMPI.B #aa`), `4e96c`(`1be3a`). D0.B := C ? `ff` : `00`(D0 상위 유지) 뒤 같은 block의 `CMP.B`가 C를 다시 정한다. 그 C를 읽는 block은 없으므로(`4e768 MOVE.B`, `4e7a2 RTS`, `4e976`/`4e97a`) 두 block 뒤 C는 Unknown으로 둔다(결정 5; V1 carry oracle이 "소비자가 C를 그대로 둔다"는 처음 구현을 `chain-4e758-to-4e75e`에서 native C와 다르다고 잡았다).
- [F] **C 통과 block 1개**(`carry_preserving_pc`에 넣음): `1efb0`(`BSR 1ed34`는 CCR을 바꾸지 않음).
- [F] **C 생산 block**: Clear `1ef9a`(`AND.W D0,D1`; `1efb0` 쪽만 C가 살아남음) `1be64` `4f126`(`ANDI.B #fe,CCR; RTS`) `4da1c`(`MOVEQ #0,D7; RTS`: MOVEQ가 C를 지움), Set `1be5e` `4da20` `4f130`(`ORI.B #1,CCR; RTS`).
- [F] **앞 단위가 남긴 사항**: C1 `4e958 BCC.B`가 `289e`의 C를 읽는 것과 같은 방식이다. `1c05c RTS`는 `1c058`이 Set일 때 C를 그대로 돌려주지만 호출자 `4ea76`은 C를 읽지 않으므로 통과 목록에 넣지 않는다(돌아간 뒤 Unknown).
- [F] **`4e77a BEQ.W 4e786`의 Z**(결정 3): 유일한 선행은 `4e770 MOVE.W 76(A6),D0; JSR 4a974.l`이다. `4a974`(routed, controller C1)는 `4a9b0`/`4a9c6 TST.B (A0); RTS`로 끝나고 A0는 `10fdb0`/`10fdb1`(`7db0(A5)`, A5 = `108000`, + D0.W & 1) 또는 `100004`/`100005`다. RTS는 그 BYTE를 바꾸지 않는다.

### IO 실행 run과 frame

- [F] 보정 관측(계획 당시 routing으로 셈, `work/c4io.py`): C4 PC를 실행하는 run 14개(P1 12, boot-title-start, boot-demo-0), 실행된 C4 PC 168개(모두 시작), 실행 235,011회.
  - P1 94 95 100 101 106 107 110 111: 처음 실행 frame **218, 219, 243, 458**(각 19,223회, PC 165개). P1 68~71: **434, 435, 456**(각 15,036회, PC 163개). boot-title-start: **338, 339, 363, 578, 591**(19,230회, PC 167개). boot-demo-0: **383, 384**(1,853회, PC 48개; demo는 frame 381의 C6 정지가 앞이라 IO에 영향 없음).
  - [I] frame 218(434/338): 슬롯 node `1009a8`의 C1 `4e94e` → `289e` → C1 `4e95a`(BYTE `9a`) → C4 `4e962`(`1be3a`) → C1 `4e97e` → C4 `4e986` 본체(문자열 `3902`, 숫자 `3786`/`371e` → `3650` video port, `4ee7a`, `1bf94`, `362a`, `36ba`, `1c052`, `1c086`, `4eef4`, `4f22c` 게이지, `4f13c`). 같은 frame에 `100a6c`의 C1 `4e732` → C4 `4e758`(`ca32`, `4a974`) → `4e564` → 결정 1의 `4e57e`. frame 219부터 플레이어 node `100cb8`의 callback `1ef0e`(`1eeea`가 설치)과 칸 `84` = `21d92` 상태.
- [F] **IO 예측(C1+E1+C2+C3+C4 연결)**: 169,482 → **170,691**(+1,209 = A 8 run × 93 + B 4 run × 93 + title 93; demo 0). 예측 첫 정지: P1 94 계열 frame **311**, P1 68 계열 frame **527**, boot-title-start frame **431**(모두 C5 `20240`), boot-demo-0 frame **381**(C6 `1d398` …). [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다(계획 §7 [U]).
- [F] D1 자연 seed 137개와 P0 run은 C4 코드를 실행하지 않는다.

## 공통 규칙·native 검증 계획

FR2..FR9, C1~C3 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_player_c4.cpp`, 함수 `animation_player_c4_block`. 오류 문자열은 `unsupported animation player c4 PC`(범위 안 내부 PC 직접 진입), `player c4 caller requires known carry`(C 소비 block에 Unknown C; 소비자 11개), `unsupported animation player c4 flag source`(결정 3의 Z 출처 guard), `unsupported animation player c4 jump target`(결정 2의 계산 점프 대상 guard), `unsupported animation player c4 divide by zero`(결정 4) 다섯 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(29 범위, C3 줄 뒤), `carry_preserving_pc`의 C3 묶음 뒤에 주석 달린 case 묶음 하나(소비자 11 + 통과 1), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** `1ef08`(`MOVE.L #1ef0e,(A6)`)은 쓰고 곧바로 그 값으로 들어간다. `21d80`(`MOVE.L #21d92,84(A6)`)은 쓰고 곧바로 `21d92`로 들어간다.
- **자료 읽기**(live bus): node field(A6: BYTE `15` `6e` `7f` `92` `99` `9a` `9c` `9d` `9e` `9f` `a0` `a1` `a3` `a7` `aa`, WORD `76` `7c` `7e` `80` `82` `84` `86` `88` `8c` `8e` `92` `94`, LONG `64` `78`), A0 node(`289e` 뒤 `9e` `76` `a8`, `1c(A0)` `1e(A0)`, LONG (A0)), A4 기록(`5450`/`5460` BYTE 6·7, `5cba`/`5ce6` WORD 0·`20`·BYTE `29`), A5 기준 WORD `545c` `546c`, BYTE `5e14`/`5e1c`, 절대 RAM WORD `10dddc`/`10dde4`, `4e77a`의 BYTE (A0), 스택(`1c086`/`1c092`의 WORD, `4eae6`/`4eb18`의 WORD, `37ca`/`37da`의 LONG A0), 고정 ROM 표(위 "계산 점프와 표"). 단위 시험은 고정 ROM 자료 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): 문자 표 `370c..371e` = `41..50 2e 7e`, DIVU 표 `377a..3786` = `0000 0001 0007 0031 0300 2000`, LONG 표 `1cfce` = `10e900 10e940 10e980 10e9c0`, `4e43e` = `10e780..10e790`(5칸), `4e49e` = `10e7a0..10e7b0`(5칸), 음수 색인 자리 `4643e` = `10e700`, `464a2` = `10e740`, 목록 `21b0a` = (`21e3a`,1) (`21602`,2) (`21c22`,`104`) 0, BYTE 표 `21ba4..21baa` = `77 33 05 0a 80 01`. V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W/.B`, `ADDI.W`, `SUBI.W`, `ANDI.W`, `ANDI.B`, `AND.W`, `SUBQ.W`, `LSL.W`, `ASR.W`, `ADD.B`, `CLR.W`, `CLR.B`, `SCS.B`, `MOVE.B #imm`). `MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`·`CLR.L`·`ADDI.L`·`ADD.L`·`SUB.L`·`MULU`(결과)·`DIVU`(결과)는 LONG 전체. 색인 `(d,PC,Dn.W)`·`(A0,Dn.W)`는 부호 확장 WORD. 비교: `CMPI.W #1/#6,D4/D5` + `BNE`/`BCC`(무부호 WORD), `CMP.W D6,D7` + `BCS`(무부호 WORD), `CMPI.B #10,D7` + `BCS`(무부호 BYTE), `CMP.B 9a/a1/9f/9e/a0(A6),Dn` + `BEQ`/`BNE`(BYTE), `CMP.W 86(A6),D7`(WORD), `CMPI.W #ffff,D7`(WORD), `TST.B 9d` + `BGT`(부호 BYTE), `MOVE.B 99,D7` + `BPL`(BYTE 부호), `MOVE.W D7,86` + `BMI`(WORD 부호), `MOVE.W 8c,D1` + `BPL`, `SUBI.W #800,D1` + `BMI`(WORD 결과 부호), `SUBQ.W #1,Dn` + `BNE`/`BEQ`(WORD 결과). bit: `BTST/BSET/BCLR/BCHG #n,d(An)`(memory BYTE, n mod 8, 옛 bit로 분기), `BTST #n,D0`(LONG bit n). `1ef0e`: `ADDQ.B #1,92`의 carry → `SCS.B D0`(D0.B := `ff`/0) → `OR.B D0,92`(다시 읽어 `ff` 포화) → `LSR.W 88`(논리 shift).
- **스택.** `1c086`이 WORD D0을 넣고 `JSR 4d7a6`, `1c092`가 꺼낸다. `4eae6`이 WORD D0을 넣고 `4eb18`이 꺼낸다. `37ca`가 LONG A0을 넣고 `JSR (A1)`, `37da`가 꺼낸다.

## carry와 Z(결정 3·5)

- [F] 소비자 11개·통과 1개·생산자는 위 명세와 같다. dispatcher는 `carry_preserving_pc`에 없는 PC로 갈 때 C를 Unknown으로 만든다. 따라서 이 단위의 C 의미는 (1) BCC/BCS 소비자 9개가 known C를 읽고 그대로 두고, SCS 소비자 2개는 읽은 뒤 C를 Unknown으로 둔다(같은 block의 `CMP.B`), (2) 통과 block `1efb0`이 들어온 C를 그대로 둔다, (3) 생산자가 자기 block에서 C를 정한다, (4) 나머지 block 뒤 C는 Unknown이다.
- [F] **`4e77a`의 Z**(결정 3): A0가 `10fdb0` `10fdb1` `100004` `100005` 가운데 하나면 BYTE (A0)를 다시 읽어 0이면 `4e786`, 아니면 `4e77e`. 그 밖의 A0는 checked `unsupported animation player c4 flag source`(rollback). 이 규칙은 controller C1의 `ac1_flag_zero`(같은 `4a974`의 Z를 `4a9d0`/`4a9da`에서 다시 계산)와 같은 출처 목록을 쓴다.

## 경계·routing 밖 출구

- [F] 이 단위의 간접 분기는 `3772 JSR (A1)`, `37d8 JSR (A1)`, `21c72 JMP (A1)` 세 곳이다(결정 2). `RTS`로 끝나는 block 20개.
- [F] **native 정지 규칙**(V1): C3 spec의 `first_unrouted`에 C4 뒤 단위·미룬 입구 13곳과 C1~C3의 남은 정지 32곳(`EXIT_STOPS`)을 선언 정지로 더한다. 계산 점프 세 곳(`JUMP_PCS`) 직후 PC가 C4 시작도 routing된 허용 대상(`3650` `21602`)도 아니면 그 PC에서 멈춘다(`21e48` `21e3a`: C++는 다음 dispatch에서 정지/오류이므로 같은 stop에서 양쪽이 멈춘다). `3650`·`21602`는 routing되어 있어 native·C++가 이어서 실행한다(숫자 출력 run이 video port까지 비교된다). 실제 ROM 차분은 같은 정지를 `UNR`로 두고, 계산 점프 착지를 trace 전체에서 추적해 분류한다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1..FR9·C1~C3 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: 그 node(A6)에 선언 편집. ROM 쓰기 명령이 범위를 정한 값은 그 범위 안으로 둔다(결정 2): 숫자 루프 직접 진입의 A1 := `3650`, 직접 들어가는 `21c72`의 A1 := 목록 `21aee`의 handler, LONG `84(A6)` := C3 목록의 routing된 칸 값(`1efd2 → 201a2`가 C3의 `JSR (A4)`에 닿음), BYTE `a0` 0..8 / `a9` 0..5(C3 표). 루프 counter(D4, D2, D6/D7)와 BYTE `9e`는 대부분 작은 값(긴 루프는 native trace 상한에서 버려짐). BYTE `10fd82` := 0(`4a974`가 BIOS `c00450`을 부르지 않게; native에 BIOS가 없음).
- **IO pack 자연 node 상태(family `natural`)**: P1 94 frame 217 218 219 220 260 311, P1 68 frame 433 434 435, P1 106 frame 218 240, boot-title-start frame 337 338 339 400의 node pool에서 callback LONG이 C1 `4e94e`·`4e732` 또는 C4 `1ef0e`인 node, 레지스터만 선언(A5 := `108000`, A6 := node, A7 := `10ef00`(복귀 LONG = sentinel), PC := callback).
- **재설치 world(family `reinstall`, 13개)**: 플레이어 node `100cb8`에 callback `1ef0e`/`1edb0`과 칸 `84` := `21d92` / (`21c66` + BYTE `9c` = 2: `21c72` → `21d60`) / BYTE `9e` / BYTE `92` = `ff`·`6e` = 8(P1 94 260, P1 68 450, title 360), 슬롯 node `1009a8`에 `4e94e` + BYTE `9a` = 0 / `a1` = `ff` / WORD `94` = `40`·`92` = `10` / BYTE `99` = `85`, `100a6c`에 `4e732` + BYTE `9a` = `ff`. [I] 이미 진행된 node를 다시 시작하는 world이며 native와 C++가 같은 상태를 받으므로 V1 비교는 유효하다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다(`CHAINS` 12개 = 소비자 11 + Z 사슬 `4e770` → `4a974` → `4e77a`). 두 C가 다 나오는 것: `1be4a`(`289e`), `1bf94`(`289e`), `1c052`(`4da08`), `21d68`(`21bc6`), `21d70`(`21baa`), `21d92`(`215e6`), `4f13c`(`4f118`), `4e758`(`ca32`), `4e962`(`1be3a`). Clear만(뒤 단위 gate, `LATER_GATED`): `1ef9a`→`1efb4`(Set은 C5 `1cb1a` 경로), `21dc4`→`21dc8`(Set은 C5 `21c12`).
- node fixture: `1ef0e`를 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다. callee fixture: `371e` `3786` `1be3a` `1bf94` `1c052` `1c086` `1ceb0` `1cec2` `1cfbe` `1d09e` `1eeea` `21d60` `21d92` `4d9a2` `4da08` `4e4e2` `4e538` `4e564` `4e758` `4e8e6` `4e962` `4e986` `4ee7a` `4eef4` `4f118` `4f13c` `4f1ac` `4f22c`를 subroutine으로 들어간다.
- 단위 시험(Unicorn 생성기, C3 꼴 + video port 비교): 시작 232개(소비자 11개 제외; `4e77a`는 native SR Z를 다시 계산한 Z와 같게 두는 행 `single 5`) × 들어오는 C 3가지, zero-step, 내부 PC 779개 정확한 오류, 경계 stop(출구·뒤 단위 정지·계산 점프 대상 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC, 성공 행마다 video port 수와 FNV digest. 손으로 계산한 규칙(`rules_a`..`rules_d`): DIVU(몫·나머지 배치, 몫 = `ffff` 경계, overflow면 레지스터 그대로, 0 → checked, 표 색인 부호 확장 `ffc9` → `370c`), MULU 하위 WORD, 문자 표 색인, `JSR (A1)`/`JMP (A1)` 허용 목록(24 bit 밖 bit 거부), `4e77a` Z 출처 4개와 거부 6개(거울 `1ffdb0` 포함), SCS의 D0.B, `1ef0e` ADDQ/SCS/OR 포화·LSR.W, `1d0a4` SUB.L/ADD.L, `4ea24`/`4eafc`의 LSL.W와 음수 색인(`2000` → `8000`), `4f1f4` ASR.W·ADD.B, 게이지 video port 값 14개(ADD.L wrap), MOVEQ / WORD 쓰기 구분(`4ead2` `4eb2a` `4ea08` `1cec2`), ff node(쓴 field와 이웃 BYTE 유지).

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `0a8379cacc854d593b262cbb4989dc68a17dfacb3e58b06e0d3e833d87474b26` → `9747100c960fa54879c998635c250ae06e790155df4ae1c5a5a4e2ec2c03915d`, `animation_machine_internal.h` `dee2f94720c4f7abd38131660b83a741fa36ada560a56357fafd8cb3f2a0e112` → `6f22404a6c4422178f812a7ad193ee9e8a1b36bfde4f0da1c7740d2875923c0d`(이 단위의 공유 수정; 옛 값은 `# player C4 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 확인했다.
- [F] `tools/unit_fixture_specs/pc1.py`: `EXIT_STOPS`의 `4e4e2` `4e538` `4e564` `4e758` `4e962` `4e986`(C4 시작)과 `4e8e6`(결정 1)이 routing되어 `build()`의 "뒤 단위 정지는 routing 밖" 검사가 실패한다. 이전 `ROUTED_LATER = (0x1d222, 0x48350)` → 새 `(0x1d222, 0x48350, 0x4e4e2, 0x4e538, 0x4e564, 0x4e758, 0x4e962, 0x4e986, 0x4e8e6)`. 선언 정지로 그대로 둔다(C1 fixture 집합 불변: V1 pc1 1,264개, C3 기록과 같음).
- [F] `tools/unit_fixture_specs/pc2.py`: `EXIT_STOPS`의 `1ceb0` `1cec2` `1eeea`(C4 시작) → `ROUTED_LATER`에 더함(이전 `(0x1ee00, 0x201a2, 0x48384, 0xe8b5a, 0x1cde0, 0x1cdf0)`). V1 pc2 1,743개(같음).
- [F] `tools/unit_fixture_specs/pc3.py`:
  - `EXIT_STOPS`의 `21c72` `1ceb0` `1cec2` `1eeea`(C4 시작) → 새 `ROUTED_LATER = (0x21c72, 0x1ceb0, 0x1cec2, 0x1eeea)`, `build()`의 검사를 pc1·pc2와 같은 꼴(`unit_of(t) is None or t in ROUTED_LATER`)로 바꿈(이전: 모두 routing 밖이어야 함).
  - 계산 점프 대상 검사(`SLOT84` + `LIST_21622` + 표 칸은 C3 또는 routing 밖)가 `21d92`(SLOT84)·`21d60`(LIST_21622)에서 실패한다. 허용 실행부에 `animation_player_c4_block`를 더함.
  - 오류 fixture `error-21620-a1-listed-21d60`(목록 handler `21d60` → `unsupported animation machine PC`)과 `error-21610-then-21d60`(BYTE `9c` = 2 → `21d60`)은 대상이 C4 시작이 되어 C++가 C4 코드를 실행하므로 더 이상 그 오류가 아니다. 목록 `21622`의 아직 routing 밖 handler `21e48`로 옮겨 `error-21620-a1-listed-21e48`, `error-21610-then-21e48`(BYTE `9c` = 3)이 되었다. 확인 내용(C3 결정 2의 "routing 밖 허용 대상은 다음 dispatch 오류")은 같다. V1 pc3 1,831개(C3 기록과 같은 수).
- [F] `tools/generate_animation_machine_player_c3_test_table.py` 오류 행: `21620-listed-21d60` → `21620-listed-21e48`(같은 이유), `21610-key-1`(합성 목록 `21622`의 key 1 = `21d60`)은 실패 PC `21d60` → BYTE `9d` = 1을 더해 C4 `21d60`의 `BGT.W 21dd0`(C12, routing 밖) `21dd0`. 생성기를 다시 돌려 생성 구역에서 그 두 행만 바뀐 것을 확인했다(나머지 바이트 같음; `engine/tests/animation_machine_player_c3_test.cpp`).
- [F] `tools/verify_animation_machine_frame_helpers.py` "no executor" 탐침(`outside_range_entry_*`)의 `1c052` `4da08`: 이전 둘 다 `unsupported animation machine PC`. 새 `SUPERSEDED_OUTSIDE_C4`: 둘 다 `animation machine external read queue empty`(C4 시작에서 실행 → base 스택으로 복귀 → 선언 없는 입력 읽기; 분류 `area C C4 (player_c4) block start; continuation behind the RTS [U: not traced]`, `API_only_control`). 관측: scratch `work/fh_probe.py`(scratch clone root `roots/probe`, 검증기의 base `natural-seed0-bank2` 첫 단계, carry 2): `1c052` `4da08` → 위 값, 대조 `1c054` `4da0a` → `unsupported animation player c4 PC`, `10fe46` → `unsupported animation machine PC`(기존 기대값과 같음), U1 범위 `1c028` `4d9d6` → external read queue empty.
- [F] 검색(`work/hexsearch.py`: `tools/*.py`, `tools/unit_fixture_specs/*.py`, `engine/tests/*.cpp`, `engine/src/*.cpp`의 4~6자리 16진 상수 중 C4 범위 안의 값): 위 곳 말고는 경계가 맞닿은 범위(`frame_helpers` NEW_RANGES `1c028..1c052` `4d9d6..4da08`, `b2b` `4d98a..4d9a2` `4eea2..4eef4`, `b2c` `1bf80..1bf94`, `readiness` `1bdde..1be3a`), "자기 범위 밖"으로만 쓰는 값(`b2b`·`b2c` 시험의 `ends`), 주석, 다른 시험 자료 안의 우연한 값(레지스터·RAM 값의 `37xx` 등), controller C1 시험의 합성 glyph 표 `370c..3760`(그 시험 안의 physical 자료이고 C4 코드를 실행하지 않음)뿐이다. `make -j4 all test`가 통과했다(경고 0).
- [I] native 사슬이 이 단위의 PC를 첫 routing 밖 PC로 멈추던 V1 spec·검증기는 더 진행한다(정지는 routing에서 계산된다). pc1·pc2·pc3은 그 PC를 선언 정지로 두어 fixture 집합이 같다. 나머지는 메인 runner의 회귀·legacy 단계가 확인한다.

## 결정

1. **범위와 숨은 직선 연속(scope correction): 계획 230 block에 `4e57e` `4e8e6` 2 block을 더해 232 block, 29 범위.**
   - [F] 계획 목록 그대로(재측정 229 + `1ef08`, 위 "재확인과 범위").
   - [F] **`4e57e`**(`LEA e84c8.l,A1; JMP 3918.l`): C4 `4e57a ADDI.W #80,D0`의 직선 연속이다. 보정 관측은 TB의 첫 routing 밖 명령만 기록하므로 TB 시작 `4e57a` 뒤의 `4e57e`가 가려졌고, 계획은 이를 C6(+ 뒤 frame)에 두었다. native 추적(`work/straightline_c4.py`, IO pack frame-start 상태, 슬롯·플레이어 node 3개, frame 216~311 / 432~527 / 336~431)은 13 run 모두 frame 218(434, 338)에 node `100a6c`의 `4e732` → C1 → `4e758` → `4e796 JSR 4e564` → `4e57a` → **`4e57e`**에서 멈추었다(`trial_logs/straightline_iter1.log` `straightline_iter2.log`). 그 블록을 routing된 것으로 치고 다시 추적하면 모든 world가 sentinel 또는 C5 `20240`(frame 311/527/431, 예정된 다음 정지)까지 간다.
   - [F] **`4e8e6`**(`MOVE.W 76(A6),D0; JSR b7a28.l`, C1 `4e8f0`로 돌아감): C1 `4e8e0 MOVE.B #1,99(A6)`의 직선 연속이다. frame-start 추적은 이 경로를 만나지 않았다. 그래서 **C4까지 routing한 상태(4e57e 포함)로 C·E run 18개를 정확한 bitmap으로 다시 관측**했다(`reobs_c4/obs`, scratch `tools/reobs.py`, 관측기 수정 없음; native 기록은 원래와 같음). 그 관측에서 실행된 routing 밖 PC 가운데 예정 정지(C5 `20240` frame 311) 앞에 실행되는 것은 `4e8e6` 하나였고, frame **72**(P1 94 계열 8 run과 P1b 94), **288**(P1 68 계열 4 run과 P1b 68), **192**(boot-title-start)였다. 예측 일치 frame은 166,744(첫 정지 C 16, 모두 `4e8e6`)였다. [I] 이 PC는 C1 연결 때부터 IO를 막았을 것이다(E1 단위의 IO 기록 `ms5-scratch/e1/ioA.log`에서 boot-title-start가 frame 192에서 멈춘 것과 맞음; 계획 §8.2와 C1 계약은 `4e8e6`을 C6의 뒤 단위 정지로 두었다). [I] 그렇다면 C1~C3 연결 뒤의 실제 IO도 P1 계열 frame 72 / 288, title frame 192에서 멈춰 있을 것이다(메인 IO 확인 대상). `4e8e6`을 넣고 다시 관측(`reobs_c4/obs2`)하면 예정 정지 앞의 routing 밖 PC는 없고 예측 170,691, 첫 정지가 C5 `20240`·C6 `1d398`이다.
   - [I] 두 block의 flag는 block 안에서만 쓴다(`4e57e`는 `LEA`/`JMP`, `4e8e6`은 `MOVE.W`/`JSR`). C6의 시작 목록은 이 2개를 빼고 다시 재야 한다(메인 판단). [U] 같은 가림이 다른 IO 단계(C5 뒤)에도 있을 수 있다. 각 단위에서 정확 bitmap 재관측을 권한다.
2. **계산 점프 세 곳(허용 대상은 ROM 자료 쓰기에서 정함; C2·C3 결정 2의 선례).**
   - `3772`/`37d8 JSR (A1)`: 허용 = `3650`(A1을 쓰는 ROM 명령 `371e`/`3786 LEA 3650(PC),A1`). 목록 밖은 `unsupported animation player c4 jump target`(복귀 LONG을 넣기 전, rollback).
   - `21c72 JMP (A1)`: 허용 = 목록 `21aee`의 handler 4개(`21602` `21d60` `21e48` `21e3a`). routing 밖 값은 다음 dispatch의 `unsupported animation machine PC`(뒤 단위 정지). 목록 밖은 checked jump-target 오류.
3. **RTS를 넘는 Z(`4e77a`, C1 결정 3·controller C1 규약).** BYTE (A0)를 다시 읽는다. A0가 `4a974`가 가리킬 수 있는 BYTE 4개(`10fdb0` `10fdb1` `100004` `100005`)가 아니면 checked `unsupported animation player c4 flag source`(rollback). [I] 거울 주소(`1ffdb0` 등)는 `4a974`가 만들지 않으므로 거부한다.
4. **DIVU·MULU.** 몫·나머지는 68000 의미 그대로, overflow면 레지스터를 바꾸지 않는다. 제수 0은 checked `unsupported animation player c4 divide by zero`(rollback; zero-divide 예외는 모델링하지 않음). DIVU의 flag는 읽는 block이 없어 모델링하지 않는다. MULU는 하위 WORD 무부호 곱.
5. **carry 보존 목록과 SCS.** 소비자 11개와 통과 1개(`1efb0`)만 넣는다. 생산자는 자기 block에서 C를 정하므로 넣지 않는다(FR 관례). `1ef9a`는 `AND.W`의 Clear를 정하고 `1efb0`(통과) → C2 `1ed34`(통과) → `1efb4`가 읽는다. `4e77a`은 C를 읽지 않으므로 넣지 않는다. SCS 소비자 `4e75e` `4e96c`는 known C를 읽고(Unknown이면 checked 오류), 같은 block의 `CMP.B`가 C를 다시 정하는데 그 C를 읽는 block이 없어 Unknown으로 둔다(C3 `21be6`의 읽히지 않는 SUBX Z와 같은 처리).
6. **video port.** `MOVE.L D0,3c0000.l` 하나 = `VideoPortWrite{3c0000, 4, D0}` 하나(기존 규약).
7. **표 읽기.** 고정 ROM 표는 live bus로 읽고 상한을 검사하지 않는다(원본과 같음, C3 결정 5). 단위 시험은 합성 byte만 선언하므로 그 밖 색인은 `missing or ambiguous physical program bus ROM byte`로 확인하고, 원본 값은 V1·실제 ROM 차분이 비교한다.
8. **뒤 단위 정지와 앞 단위 spec.** C4 block이 닿는 뒤 단위 시작 6곳과 미룬 입구 7곳, C1~C3의 남은 정지 32곳을 V1 `first_unrouted`와 실제 ROM 차분의 선언 정지로 둔다. pc1·pc2·pc3의 `EXIT_STOPS` 가운데 C4가 routing한 PC는 `ROUTED_LATER`로 허용하고 선언 정지로 그대로 둔다(C2·C3가 쓴 방식).
9. **실행부 파일·오류 문자열.** 위 "공통 규칙". 오류 문자열 5개.
10. **다음.** 계획 순서대로 C5(`20738` `20240` …, 표 `20792` `2094e` `209d6`, `JMP (A1)` `21f7c`). C4 연결로 IO +1,209(170,691)를 메인 runner가 확인한다. C6의 시작 목록에서 `4e57e` `4e8e6`을 빼야 한다.

## 미확인

- [U] node field·전역 값의 의미(슬롯 node의 WORD `7c`..`86`(HUD 좌표 [I]), BYTE `99` `9a` `9d` `9e` `9f` `a0` `a1`, 플레이어 node의 BYTE `92`·WORD `88`, `5450/5460` 기록, `5cba/5ce6`, `5e14/5e1c`, `10dddc/10dde4`(게이지 값 [I])). 이름(숫자 출력, 게이지, HUD)은 동작에서 붙인 [I]이다.
- [U] IO 관측에서 실행되지 않은 이 단위의 block 64개(`1be46` `1be5e`, `1c09c`~`1c0c0`, `1cee0` `1cee4`, `1eeea`~`1ef30` 일부, `21d60`~`21d80` 일부, `4d9a2`~`4d9b4`, `4da12` `4da20`, `4e538`~`4e552`, `4e79e`, `4e9a4` `4e9ac`, `4ea92`~`4eaa0`, `4ead2`, `4f130`~`4f220` 대부분, `4f23a` `4f24a` `4f278` `4f294` 등)는 closure로 들어왔다(V1 선언 상태·실제 ROM 차분으로만 확인).
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC). 예측은 C5 `20240`(13 run)과 C6 `1d398`(demo)이다.
- [U] 재설치 world와 IO pack 자연 node 상태의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C3와 같음).
- [U] 결정 1의 정확 bitmap 재관측은 C·E run 18개만 했다(계획 §7과 같은 범위).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_player_c4.cpp`(case label 232 = `starts_C4_final.txt`와 집합 일치; 공용 함수 `pc4_get` `pc4_put` `pc4_bit`(BTST/BSET/BCLR/BCHG memory BYTE, 옛 bit) `pc4_byte_is` `pc4_word_zero` `pc4_carry` `pc4_scs` `pc4_return_carry` `pc4_divu`(결정 4) `pc4_video`(결정 6) `pc4_field_call` `pc4_digits` `pc4_digit_count` `pc4_digit_divide` `pc4_digit_put`(결정 2의 `3650`), 허용 목록 `PC4_LIST_21AEE`(4)), `engine/tests/animation_machine_player_c4_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_e`; 성공 행마다 video port 수·FNV digest 비교), `tools/generate_animation_machine_player_c4_test_table.py`(생성기; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native video port를 C++ 꼴(LONG 하나)로 맞춤; port 48개·trace 20,000 명령이 넘는 run은 버림; 약 95초; 다시 실행해 시험 파일 바이트 단위 같음), `tools/unit_fixture_specs/pc4.py`(V1 spec; C3 spec의 공용 부분 그대로, 단위 부분 교체, `EXIT_STOPS`(45), `PASS_SET`, `CLEAR_SET` `SET_SET`, `Z_READERS`, `LATER_GATED`, `JUMP_PCS` `JUMP_ROUTED` `LIST_21AEE`, family `reinstall`(추가 쓰기 포함)). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- [F] `make -j4 all test`(작업자, 최종): 종료 0, 경고 0, Python 310 OK. C4 시험 줄: `animation machine player pc4: 1372 fixtures (782 single-block, 12 Z reader, 423 path, 66 producer chain, 22 declared C, 67 checked error (12 with a later failing PC), 128 kept C, 108 with video ports), 232 blocks, 5520 calls, 135877 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block은 `4f210`의 자기 자신 쪽뿐(`BNE.B 4f210`: 단일 block 행은 entry에서 멈추는 zero-step이라 path 행이 덮음), 실제 사슬 두 C 값 9개(`1be4a` `1bf94` `1c052` `21d68` `21d70` `21d92` `4f13c` `4e758` `4e962`; SCS 둘은 `CHAINED`에서 빼고 D0.B로 확인), Clear만 2개와 Z 사슬(두 결과 모두). 기존 C1~C3 시험 줄은 C3 기록과 같다(pc3 114,880 checks: 오류 행 2개 교체로 +1).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, C4 시험): 빌드 경고 0, 실행 종료 0, runtime error 0.
- [F] V1 pc4(작업자 1회, `--workers 2`, scratch `work/v1_pc4`): fixture 1,873개(block 870, chain 22, node 3, natural 38, reinstall 13, callee 69, error 837, failpc 11, negative 10) failed 0, 방문 시작 232/232, 빠진 후속 0, 도달 못한 분기 결과 0, 뒤 단위 gate 2개(`1efb4`→`1f126`, `21dc8`→`21f4c`), carry oracle Unknown/Clear/Set = 932/59/35, native port 39,680개 비교. natural·reinstall 51개 가운데 50개가 sentinel까지(C4 block 최대 104개, C4를 지나는 world 45개) 가고, 나머지 1개(P1 94 frame 311의 `1ef0e`)는 예정된 C5 정지 `20240`에서 멈춘다.
- [F] V1 회귀(작업자): pc1 1,264/1,264, pc2 1,743/1,743, pc3 1,831/1,831, se1 2,102/2,102, fr1 1,631/1,631(모두 failed 0; 수는 C3 기록과 같음). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·BSET/BCLR/BCHG, WORD→LONG, 복귀 PC, carry tag·소비자 분기 교환, mask, 즉시값) + 손으로 고른 helper·block 변이(DIVU 0 허용·mask·overflow 경계(`>=ffff`)·overflow 제거·overflow 때 0·몫/나머지 교환·나머지 버림·상위 유지, 표 색인 부호 확장 제거(`377a` `370c` `4e4a2` `4e43e`)·표 기준 주소, `JSR (A1)`/`JMP (A1)` 허용 목록(값·개수·검사 제거·24 bit), `4e77a` 출처 목록(빠짐·거울·WORD 읽기·분기 교환), SCS 교환·WORD, video port 크기·주소·제거, MULU mask·상수, ASR→LSR, ADD.B→WORD, ADDI.L 상수, MOVEQ↔WORD, LSL 폭·횟수, 포화 OR 제거 등) + dispatcher carry 목록 12개·추가·범위 1개를 적용해 만든 것, 640개): 1회째 `killed 603 of 640`, 빈틈 21개를 규칙 `rules_e`와 합성 BYTE `370a`/`370b`(문자 표 음수 색인), 같은 값의 V1 hint로 메움(`killed 19 of 21`, 남은 2개(`3722-mask` `4e96c-mask`)는 건너뛴 block의 부작용까지 보는 규칙으로 고쳐 `killed 2 of 2`). 2회째(규칙·hint 보강 뒤 전체) `killed 624 of 640`, 남은 16개는 모두 동치다(`mut/equivalents.txt`; 최종 시험 표로 다시 돌려 `killed 0 of 16`: `ANDI.W #1` 뒤의 WORD/BYTE mask 4, `MOVEQ #0`·`CLR.L` 뒤 덮어쓰는 dead store와 BYTE 쓰기 6, BYTE 저장이 자르는 OR mask 1, `#c & D0.W` 뒤의 mask 1, 곧 덮어써지는 LEA 값 1, flag를 읽지 않는 `TST.B` field 1, SWAP 뒤 WORD 쓰기 1, bit 번호 mask 1). 64 KiB RAM 거울이 부호 확장 변이를 가리는 곳은 고정 ROM 합성 자료의 음수 색인(`377a` + sext(`ff92`) → `370c`, `4e4a2`/`4e43e` + sext(`8000`) → `464a2`/`4643e`, `370c` + sext(`fffe`/`ffff`) → `370a`/`370b`)과 `4e77a`의 거울 주소 `1ffdb0` 거부 규칙, `1be3a`의 A0 값(`100cb8` 대 `110cb8`) 규칙으로 덮었다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`), `real_pc4.py`(C3 harness에 C4 world·소비자·통과·Z 진입·선언 정지; C3·C4 계산 점프의 착지를 허용 목록과 trace 전체에서 대조해 분류; native zero-divide 예외를 DIVU 자리로 분류)): 작업자 300건 3회 — seed 1 `mismatches 0`(`covered starts 220 of 232`; 문서화된 분류 C4 jump-target 1건, divide-by-zero 9건), seed 7 `FOLLOW_ANIM=1` `mismatches 0`(223/232; jump-target 2, flag-source 1, divide-by-zero 7), seed 8 `FOLLOW_ANIM=1` `mismatches 0`(224/232; jump-target 4, flag-source 1, divide-by-zero 6). 정지하지 않은 native(약 17~21%; 주로 무작위 counter의 긴 숫자·게이지 루프가 명령 상한에 걸림)는 건너뜀. 처음 시도에서 `4f130`(block 첫 명령이 DIVU)의 native 예외 PC를 C++ stop으로 넘겨 C++가 그 자리에서 멈춘 harness 결함 4건을 고쳤다(예외 case의 C++ stop은 도달하지 않는 STOP). 로그 `trial_logs/real_n300_*.log`, `try_t60_s1.log`.
- [F] `dleft.py`(`MS5_REOBS=…/c1/reobs`): 이전(routing `0a8379ca…`) C 529 / E 12, 예측 169,482, 첫 정지 C 14(`dleft_before.log`). 이후(routing `9747100c…`) C **361** / E 12, 예측 **170,691**, 첫 정지 C 14(`dleft_after.log`). C4 routing의 정확 bitmap 재관측(`reobs_c4/obs2`, 결정 1)으로도 같다(`dleft_after_obs2.log`). 예측 첫 정지 PC(`work/firststops_after.txt`): P1 94 계열 8 run frame 311·P1 68 계열 4 run frame 527·boot-title-start frame 431에서 C5 `20240`, boot-demo-0 frame 381에서 C6 `1d398` … `1d63a`. 결정 1 앞(`4e8e6` 없음)의 정확 재관측(`reobs_c4/obs`)은 예측 166,744, 첫 정지 C 16(모두 `4e8e6`, `work/firststops_obs1.txt`)이었다.
- [F] 기존 검증기 새 기대값은 scratch clone root(`roots/probe`, `work/mkroot.py`: 작업 트리 clone + 변경 파일 복사 + 공유 자료 symlink, 출력 폴더만 실제)에서 관측했다(`fh_probe.py`). stage_event / stage_event_ops `CPP_PINS`가 파일 SHA와 같음을 확인했다(4 / 9 pin, 불일치 0).

## block 목록

[F] scratch `starts_C4_final.txt`(SHA256 `ab2c1f99e768e8f6ca03a0deda7c67ec1d7a65e3ba708e6877e7c72f870d2bb0`) = 계획 `starts_C4.txt`(230) + 결정 1의 `4e57e` `4e8e6`.

- **`371e..37e2`(24)**: `371e 3722 372a 372e 373a 374e 3754 375c 3762 3766 3774 3778 3786 378a 3792 3796 37a2 37b6 37bc 37c4 37ca 37da 37dc 37e0`
- **`1be3a..1c0d2`(25)**: `1be3a 1be46 1be4a 1be50 1be54 1be5e 1be64 1bf94 1bf9a 1bf9e 1bfa8 1c052 1c058 1c05c 1c05e 1c066 1c06c 1c086 1c092 1c09c 1c0a2 1c0aa 1c0b4 1c0c0 1c0c4`
- **`1ceb0..1d0c2`(16)**: `1ceb0 1ceba 1cec2 1cecc 1ced6 1cee0 1cee4 1cef4 1cfbe 1d09e 1d0a2 1d0a4 1d0b0 1d0b4 1d0bc 1d0c0`
- **`1eeea..1efd6`(23)**: `1eeea 1eef6 1ef08 1ef0e 1ef20 1ef30 1ef36 1ef3a 1ef44 1ef6c 1ef74 1ef7c 1ef80 1ef88 1ef90 1ef9a 1efb0 1efb4 1efb8 1efbc 1efc2 1efcc 1efd2`
- **`21c72..21dd0`(18)**: `21c72 21d60 21d68 21d6c 21d70 21d74 21d78 21d80 21d92 21d9a 21da0 21da4 21dac 21db4 21dbc 21dc4 21dc8 21dcc`
- **`4d9a2..4da2a`(9)**: `4d9a2 4d9a8 4d9b0 4d9b4 4da08 4da12 4da16 4da1c 4da20`
- **`4e4e2..4e7a2`(23)**: `4e4e2 4e4fe 4e51a 4e538 4e546 4e54e 4e552 4e564 4e57a 4e57e 4e758 4e75e 4e768 4e770 4e77a 4e77e 4e786 4e78a 4e792 4e796 4e79a 4e79e`, `4e8e6`
- **`4e962..4eb50`(50)**: `4e962 4e96c 4e976 4e97a 4e986 4e98e 4e998 4e99c 4e9a4 4e9ac 4e9b0 4e9bc 4e9c0 4e9ca 4e9d8 4e9ee 4e9f8 4e9fc 4ea04 4ea08 4ea14 4ea18 4ea24 4ea38 4ea40 4ea54 4ea5c 4ea6c 4ea76 4ea8a 4ea92 4ea9c 4eaa0 4eaa4 4eaae 4eab6 4eabe 4eace 4ead2 4eadc 4eae6 4eaf0 4eaf8 4eafc 4eb18 4eb22 4eb2a 4eb44 4eb48 4eb4c`
- **`4ee7a..4f2ba`(44)**: `4ee7a 4eef4 4eefe 4ef06 4f118 4f126 4f130 4f13c 4f144 4f148 4f150 4f152 4f158 4f160 4f166 4f16e 4f174 4f1ac 4f1c2 4f1c4 4f1d8 4f1e0 4f1f2 4f1f4 4f20c 4f210 4f220 4f22c 4f23a 4f240 4f24a 4f24c 4f254 4f25c 4f25e 4f26c 4f278 4f280 4f28c 4f294 4f2a0 4f2a4 4f2ac 4f2b8`
