# 영역 C 단위 C7(데모 전용 플레이어 입력 상태 `1f2a4` → `1f2d4`/`1f538` → `1f56a`/`1f5d2`/`1f5f2` → `1f6aa` → `1f6da`, C helper `1c9ec`/`1ca4c`, interpreter script callback `22480`/`22656`/`2285c`, 2986 자식 `24fb0` → `25102`(BRA.W 표 `2529c`)·`253f4` → `25448`, 214 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §4.2의 C7 행과 아래 "C7 상세 명세"(계획 §8과 같은 꼴, 이 계약에서 새로 씀)를 기준으로 삼고, 구조·공통 규칙은 C6 계약(`animation-machine-player-c6-contract.md`)·C5 계약·C4 계약·C3 계약·C2 계약·C1 계약을 따르며 다른 점만 적는다. 단위 이름은 C7, 파일 접두어는 `player_c7`(C++) / `pc7`(V1 spec)다(계획 메인 결정 7). 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 `<100000`이라 CPU 주소 = 파일 오프셋이다. 예외는 bank 창 LONG 읽기 둘(`24fb6 MOVE.L 2000b8.l,22(A6)`, `251c8 MOVE.L 200094.l,22(A6)`)이다. CPU 주소이고 물리 오프셋은 `bank_base + b8` / `bank_base + 94`다. 장치 쓰기는 없다(장치·bank는 callee가 다룬다). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `5185666`(branch `claude/c7-core`; C1~C6, E1 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `bd037aff436d5b102749b0c97562660c5b32423736393f679dede2d2dcecefd4`, `animation_machine_internal.h` `5458ca6c08b35b69780549b938650f1c649eed535a4ce1760b828644efd6d9a5`.
- [F] 관측 입력: native IO 관측 `artifacts/animation_machine_io_native`(읽기 전용; state pack `states/boot-demo-0/boot.pack.gz`), 계획의 보정 관측 `ms5-scratch/c1/reobs/`(읽기만), 그리고 이 단위의 정확 bitmap 재관측 두 벌(scratch `reobs_c7/obs_c6`, `reobs_c7/obs_c7a`; 결정 1).
- [F] 시작 목록: 계획 scratch `ms5-scratch/c7/starts_C7.txt`(217개, SHA256 `18a35f40c2ab773df41f174863c42a3312feeade8d919011c00e74c36f0c29c1`, 계획 §6 표의 `18a35f40c2ab773d`와 같음)에서 C3 결정 10이 가져간 `1cde0` `1cdf0` `1cdfa`를 뺀 **`ms5-scratch/c7/starts_C7_final.txt`(214개, SHA256 `f95f6bbd592ed620e1ce6352b5bcacbca2843d3449a7dd28b695813db35684d5`)**. 재측정 목록 `remeasure/r7_C7.txt`와 같다. 실행부의 `case` label 214개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(작업자 확인: `make test`의 C7 시험이 시작 214개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/c7/`
  - `remeasure/remeasure7.py` → `r7.json` `r7_C7.txt` `r7_C8.txt`(재측정), `work/mkunits7.py` `work/units_r7.json`, `work/udetail7.py` → `work/udetail_C7_r7.txt` `work/C7_r7.dis.txt`(범위·출구·역어셈블, `>` = block 시작, `*` = IO 실행 TB 시작), `work/c7ranges_r7.txt`(범위), `work/callers_c7_all.out`(ROM 전체 직접 분기 호출자), `work/c7io.py` `work/c7io_obs_c6.txt`(IO run·frame), `work/natsig7.py` `work/natsig7.out` `work/natdbg.py`(IO 자연 node), `work/newvis_c6_c7a.txt`(재관측 사이 새로 보인 PC), `work/firststops_before.txt` `work/firststops_c7a.txt` `work/firststops_after.txt`(예측 첫 정지), `work/mw_oor7.py`(motion-walk 계산 PC 검사), `work/pincheck.py`(CPP_PINS 대조), `work/mkpc7.py` + `work/pc7parts/`(V1 spec 조립: C6 spec의 공용 부분 + C7 부분), `work/v1_regs.sh`(V1 회귀), `work/ubsan.sh`, `reobs_c7/`(정확 bitmap 재관측), `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **재측정 전**(`MS5_REOBS=…/c1/reobs dleft.py`, routing `bd037aff…` = C1~C6 + E1): 실행된 routing 밖 PC C **194** / E 0 / D 0, 예측 일치 frame **173,820**, 첫 정지 C 1(`trial_logs/dleft_before.log`). C6 계약의 C6 뒤 값과 같다.
- [F] **closure 재측정(C1~C6 routing 상태)**: C6 작업자 방식 그대로 계획 spec `plan/plan_final.json`과 계획 당시 key(`remeasure/keys_old.json`)로 현재 routing에서 `cplan3`을 돌렸다(`remeasure/remeasure7.py`, `trial_logs/remeasure_r7.log`). **C7 = 214 block, 537 명령, 2,270 byte, 13 범위**(시작 목록 SHA `f95f6bbd592ed620…`), 예측 173,877(+57), 남은 C 93 / E 0, 첫 정지 C 1. C8 = 98 block(시작 목록 SHA256 `fb7b452a27a22a965a675244bbe735f4fb86bdd937421c3e9636c1e9672c916d`, 계획 99 − `1fcd4`), 예측 173,966.
  - [F] 계획 목록(217)과의 차이는 `1cde0` `1cdf0` `1cdfa` 셋뿐이다. 셋 다 C3 결정 10이 가져갔다(C3 `1cde0..1cdea` `1cdf0..1cdfe`).
  - [F] C8의 계획과의 차이 `1fcd4`: C6 `1dbca`가 쓰기만 하는 callback 값(C6 계약 "설치 값")이다. 재측정 closure는 실행되지 않은 쓰기 전용 값을 시작으로 두지 않는다 [I: 계획 당시에는 C6가 routing되지 않아 다른 경로로 시작이 됐다]. C8 착수 때 다시 정한다.
  - [F] **C7 + C8 병합 검토**: 재측정 합계 214 + 98 = 312 block으로 약 230을 넘는다. 병합을 제안하지 않는다.
- [F] **범위 밖에서 범위 안 비시작 PC로 들어오는 직접 분기**: 없다(`work/callers_c7_all.out`: 범위 안으로 오는 분기 대상은 모두 시작이다). `2520a bsr.b 25284`는 `2520c BRA.W`의 operand(`6000`)를 명령으로 읽은 것이다.
- [F] **정확 bitmap 재관측**(결정 1; scratch `tools/reobs.py`, 관측기 수정 없음; C·E run 18개, `--workers 3`):
  - C6 routing(`bd037aff…`) 그대로: `reobs_c7/obs_c6`(`observation.json` compared_sha256 `d8a163c9f87e242e…`), `reobs_check.py`: 18 run 모두 native 기록이 원래와 같다(`ALL NATIVE RECORDS EQUAL … True`). `dleft.py` → C 194 / E 0, 예측 **173,820**, 첫 정지 C 1: boot-demo-0 frame **431**의 `1f2a4` `1f2ac` `1f2d8` …(C6 계약의 `obs_c6a`와 같음; 두 관측 사이 새로 보인 PC 0).
  - C7 범위를 가상 routing(`EXTRA_ROUTED`)에 넣은 bitmap: `reobs_c7/obs_c7a`(compared_sha256 `65047e6224d8d988…`, native 기록 18 run 모두 같음). `dleft.py` → C **93** / E 0, 예측 **173,877**, 첫 정지 C 1: boot-demo-0 frame **488**의 C8 `1f756`(`1f752 BCC`의 fall-through)뿐이다. 나머지 17 run은 600 frame 끝(또는 guard)까지 정지가 없다.
  - [F] 두 관측 사이에 새로 보인 routing 밖 PC(TB 안에 가려진 직선 연속)는 **없다**(`work/newvis_c6_c7a.txt`: 18 run 모두 0). C7 연결로 사라진 실행 PC는 C7 범위의 PC뿐이다(demo 220 → 119). 그래서 C3 결정 10·C4 결정 1과 같은 숨은 직선 block 추가는 필요 없다(C5·C6 결정 1과 같은 결과). 예측 첫 정지가 C8뿐이므로 반복을 멈췄다.
- [F] **측정 결과**(`dleft.py`, 최종 routing `1f4599a2…`): `MS5_REOBS=…/c1/reobs` → C 194 → **93**(−101: 실행된 C7 PC 101개 = 시작 96 + TB 분할 PC 5 `24fe2` `24fe6` `24ff0` `24ff4` `25000`), E 0, 예측 일치 frame **173,877**(+57), 첫 정지 C 1(`trial_logs/dleft_after.log`). `MS5_REOBS=…/reobs_c7/obs_c7a`로도 같다(`dleft_after_obs_c7a.log`). 계획 표(남은 C 93)와 같다.
- [F] run별 예측(`work/firststops_before.txt` → `firststops_after.txt`): boot-demo-0만 frame 431 → 488(+57). 나머지 17 run은 바뀌지 않는다.

## C7 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **계획 217 block, 542 명령**(시작 목록 SHA256 `18a35f40…`) − C3 결정 10의 `1cde0` `1cdf0` `1cdfa` = **214 block, 537 명령, 2,270 byte, 13 범위**(시작 목록 SHA256 `f95f6bbd592ed620e1ce6352b5bcacbca2843d3449a7dd28b695813db35684d5`, 범위 이어 붙인 SHA256 `8fbb2dfa9988ed640503294ee33226db4de4788eb2e3fe1da0c8fbd5a66c1c38`). 짝수 PC 1,135(내부 921). 아래 표는 구현 범위다.

| 범위(CPU = 파일 오프셋) | byte | SHA256(앞 16자) | 시작 | 내용 [I] |
| --- | --- | --- | --- | --- |
| `1c9ec..1ca74` | 136 | `237719e3c7b72db1` | 20 | C helper `1c9ec`(D0.W & 1 → BYTE 기록 `5450`/`5460(A5)` = A4, D1.B 열쇠 `CMP.B 4(A4)`): 다르면 Clear; 같으면 `1ca4c`(BYTE 3 = ff → Set; BYTE 2 < 3 → `ADDQ.B #1,2(A4)`, Set; 아니면 Clear)의 C, Set이면 `10f001` bit 3 / WORD `c(A4)` 세기(ffff 고정, 0에서 멈춤) 뒤 Set, WORD 0이면 Clear |
| `1f2a4..1f33e` | 154 | `08da2e71b0274a0b` | 17 | 입력 상태 `1f2a4`(C6 `1ec2c`가 분기): `1cab6`(표 `1b24c`), field 초기화·칸 `84` := `21602`, 상태 `1f2d4`(`1cd98` 입력 D0 bit 5/1/6/4, BYTE `15` bit 7, BYTE `9e`, `AND.W #c` → `1fae8` `1f7a4` `1fa68` `1fa3c` `1f5d2` `1f5f2`, `4bfc0` `ce02` `49fc6`의 C, `201a2`로) |
| `1f538..1f65e` | 294 | `358e08c6db81eb1c` | 26 | `1f538`(`BCHG #0,15`, `1cab6` 표 `1b2ee`, 상태 `1f56a`: 같은 꼴, `1fad2` `1f76e` `1eb98`), `1f5d2`(BYTE `a5`/`a6` bit 6 지움, `88` := 0, 표 `1b482`), `1f5f2`(bit 4 지움, `88` := 1, BYTE `a7` bit 0/1, `6e` = 5 → 표 `1b6a8`/`1b68a`, 아니면 `1b632`/`1b610`, `1cb08`의 C), `1f648`(LONG 표 `1f65e + 4 × BYTE 4(A4)`) |
| `1f6aa..1f756` | 172 | `4ee7f63fef88734b` | 18 | `1f6aa`(`1cab6`, field 초기화, BYTE `7e` 지움) → 상태 `1f6da`(`1cd98`, `1cec2`의 D1.B = 1 → `1f538`, BYTE `7e`/`a5` 분기, `49fc6`의 C) |
| `1f76a..1f7a4` | 58 | `693301d8d6fbc952` | 6 | `1f76a BRA 201a2`, `1f76e`(`1cb08` 표 `1b310`의 C → `1fa3c` / `1cab6` → `1faa0`) |
| `22480..22502` | 130 | `1224025bc6f61bf4` | 14 | script callback `22480`(WORD `42`/`46`을 스택에 두고 BYTE `7a`/`7b` EXT.W만큼 빼고 `4ae4a`(A0 = LONG (A0)), 되돌림; D0.B 6/8과 WORD (A0) 2/8로 소리 `3af8`(`1a6b` `18d1` `1a69` `1a4b`)) |
| `22656..22788` | 306 | `a099a9d356b39c30` | 25 | script callback `22656`(BYTE 표 `22642 + BYTE 4(A4)`, 아니면 `1c9ec`의 C; LONG 표 `225f6`의 자식 → `2986`(D0 := 1e), WORD 3개(A0 = script) 반전, `49214` `491b6`; LONG 표 `225e6 + 4 × BYTE 9e`의 부표 + 4 × BYTE 4(A4) 자식 → `2986`(D0 := a)의 C, BYTE `a1` 세기, 자식 field, `2291a`; BYTE 4 = 5 / a와 BYTE `9e` = 1이면 `DIVU.W #3` / `MULS.W D7,D0`로 BYTE `76(자식)` 보정) |
| `2285c..2291a` | 190 | `1c7928dd79fc55e8` | 15 | script callback `2285c`(`BCLR #5,a8`·WORD `a(A4)` → 자식 `23c56`; LONG 표 `2284c + 4 × BYTE 9e`의 목록 + 4 × BYTE 6(A4)(< 4, 아니면 0) 자식 → `2986`, BYTE `7(A4)` 세기, 자식 field, WORD 3개 반전, routing된 `2291a`로 떨어짐) |
| `24fb0..25082` | 210 | `f5dac9200ae04e23` | 11 | 2986 자식 `24fb0`(WORD `20` := 12a, LONG `22` := bank 창 `2000b8`, `3af8`, 칸 `84` := script `6f364`, LONG `7a` := 100000, script `255ba` → `49f8c`, `8ebe`, field, `443d2` → LONG `36`/`3a`, BYTE `76`의 bit 5 반올림으로 BYTE `77`/`78`/`79`, 상태 `25102`) |
| `25102..2529c` | 410 | `91478bea9b1989de` | 41 | 상태 `25102`(`4be34`, LONG 표 `25082`/`250c2 + 4 × (BYTE 77 & f)` → `4ae4a` D0.B: 0 → `ea69c`의 C를 `SCS.B 83`, BYTE `15` bit 5/7, `4bb52`, `JMP 2a00`; `49fc6`, WORD `42`/`46` 경계 → `JMP 2a00`, BYTE `8a`/`8b`/`89` 세기; `251c2` 착지 상태(bank 창 `200094`, `49a58` 흔들기 → script `26178`/`26112`, `8ebe`, callback `25448` 쓰기만)); D0.W ≠ 0 → `2528c`(`CMPI.W #9` → 표 `JMP 2529c(PC,D0.W)`) |
| `252a4..252a8` | 4 | `c35b1e40f0bb0352` | 1 | 표 칸 2(실행된 칸): `BRA.W 252c0` |
| `252c0..252ce` | 14 | `69ddef0e595f9e19` | 2 | 소리 `1a5d` → `253c8` |
| `253c8..25488` | 192 | `1c98b0905841e0bd` | 18 | 자식 `253f4` 만들기(`2986`, 칸 `84` 복사, `49214`, `JMP 2a00`), 자식 `253f4`(`8ebe`, `16ed2`, script = LONG `84` → `49f8c`, `49a58` 흔들기 → 상태 `25448`: `43e34`, `49fc6`의 C, WORD `42`/`46` 경계) |
| 합계 C7 | 2270 | 이어 붙인 바이트 `8fbb2dfa…` | **214** | 짝수 PC 1,135(내부 921) |

- [F] **진입(실행된 PC를 줄인 closure 진입, 재측정 `entries`)**: `1f2a4` `22480` `1c9ec` `22656` `24fb0` `252a4` `253f4` `2285c`.
- [F] **IO 실행**(`work/c7io_obs_c6.txt`; C6 routing 재관측): 실행된 C7 PC 101개(시작 96 + TB 분할 PC 5), 실행 1,317회(계획 1,437), run 1개(boot-demo-0). 실행되지 않은 시작 118개.
- [F] **호출자**(ROM 전체 직접 분기 검색 `work/callers_c7_all.out`, LONG 값 검색):
  - `1c9ec` ← C7 `22670`(다음 `BCS`), 단위 밖 `227ba`(다음 `BCS`). `1ca4c` ← C7 `1ca0a`(다음 `BCS`), `1ca88 BEQ.B`(단위 밖 자료/코드).
  - `1f2a4` ← C6 `1ec30`, 뒤 단위 `1ecf2` `1edea` `1ef70` `1f01e` `1f0e8`(모두 `BNE.W`). `1f538` ← C7 `1f70e`, 뒤 단위 `1f4f2`. `1f5d2` ← C7 `1f30e` `1f5a2` `1f72e`, 뒤 단위 `1f3a6` `1f450` `1f504`. `1f5f2` ← C7 `1f316` `1f5aa` `1f738`, 뒤 단위 `1f458` `1f50c`. `1f76e` ← C7 `1f592` `1f702`, 뒤 단위 `1f396` `1f440` `1f4de` `1f872` `1f962` `1f9b2`.
  - script callback: `22656` `2285c` `22480`은 interpreter callback 표 `4a500`의 LONG(칸 0, 2, 7)이다(`animation_machine_interpreter.cpp` `callback`: `JSR (A1)`, A0 = script의 LONG). `22656`은 단위 밖 `6f2a2 JMP` `6f2e4 JMP`, `2285c`는 단위 밖 `1e10c BSR` `1e654 BSR`(다음 명령은 flag를 읽지 않음)도 부른다.
  - 2986 자식: `24fb0` = LONG 표 `22502` 칸 0·16·17, `2254e`는 다른 값(`24d46` …). `253f4` ← `253c8 MOVEA.L #253f4,A0`.
  - 뒤 단위 코드에서 들어오는 시작: `24ffa`(뒤 단위 `24bf0` … `24fac` `BRA.W` 11곳), `25132`(`24d08` `253a4` `253c4`), `2528c`(`24d04`), `253c8`(`252b0` `252e2` `252f4`), `252c0`(표 칸 `2529c` `252ac` `252b8` `252bc`), `228e8`(`229a4`).
- [F] **설치 값**(`MOVE.L #v,(A6)`): 곧바로 들어감 `1f2d4`(`1f2ce`) `1f56a`(`1f564`) `1f6da`(`1f6d4`) `25102`(`25078` 뒤 `BRA`) `25448`(`25442`). **쓰기만**: `1f3e8`(`1f334` `1f5c8`, C8), `25448`(`25284`; C7 시작이지만 `25284`는 쓰고 RTS). 둘째 callback 칸 `84(A6)` := `21602`(`1f2b0` `1f546` `1f6b2` `1f788`; C3 허용 목록 안). `24fc8`의 `84(A6)` := `6f364`는 script 포인터다(`253de`가 자식에 복사, `25414`가 `49f8c`에 넘김). 이 node(`24fb0` 자식)는 player node가 아니라서 C3 `201a6 JSR (A4)`에 닿지 않는다 [I: 이 계열은 `201a2`로 가지 않음].
- [F] **IO run의 node**(`work/natsig7.out`, 재관측 `unr_new`): demo frame 431에 player node `100cb8`의 C6 `1ebf6` → `1ec2c` → `1f2a4` → `1f2d4` → `1f5f2` → `1f634`/`1f63e`/`1f640`(`1cb08` Set) → `1f6aa` → 상태 `1f6da` → `1f706`/`1f712`/`1f73c` … `1f752`(`49fc6` Clear) → `1f76a`. frame 432에 `1f6da`와 interpreter callback `22480`(→ `224c2` → `224ca` 소리). frame 440에 `1f648` `1f71a` `1f728` `1f732`, callback `22656` → `1c9ec`/`1ca4c`(Set) → `2267a` → `226ca` → `226f0`(`2986` Set) → `2270a` … `2273c` → `22758`. frame 441에 2986 자식 node(`101640`)의 `24fb0` → `25102` → `2528c` → `25294` → 칸 `252a4` → `252c0` → `253c8`(자식 `253f4`) → `JMP 2a00`. frame 442/443에 자식 `253f4` → `25448` …, frame 453에 `25458`(`JMP 2a00`). frame 465에 `1f5d2`와 callback `2285c` → `22894` → `228ae` → `228b8` → `228cc`(`2986`) → `228e6` → `22912` → routing된 `2291a`. [I: frame 431의 자연 node는 frame 시작 pack의 입력이 이전 frame 값이라 `1ebf6`에서 `1f2a4`로 가지 않는다(`work/natdbg.py`). 그래서 V1은 `1f2a4`·`1f5d2`·`1f5f2`·`1f538`·`1f76e`·`1f6da` 재설치 world로 확인한다.]

### 계산 점프와 표(결정 2)

- [F] **계산 점프 하나: `25298 JMP 2529c(PC,D0.W)`**(BRA.W 표, ROM 파일 오프셋 = CPU `2529c..252c0`, 9칸). 앞의 `2528c CMPI.W #9,D0; BCC.W 252c0`이 D0.W를 0..8로 묶고 `25294 ADD.W D0,D0` 두 번으로 변위 0..20(4의 배수)을 만든다. D0는 `25122 JSR 4ae4a`가 돌려준 값이다(`2512c TST.B D0` ≠ 0). 표 칸(ROM `6000 xxxx`): 0 `2529c → 252c0`, 1 `252a0 → 252e6`, **2 `252a4 → 252c0`(IO에서 실행된 유일한 칸)**, 3 `252a8 → 252ce`, 4 `252ac → 252c0`, 5 `252b0 → 253c8`, 6 `252b4 → 252ce`, 7 `252b8 → 252c0`, 8 `252bc → 252c0`.
  - FR4 결정·C5 결정 2와 같은 규칙: **실행된 칸 `252a4`만 단위 block**이다. 변위 0..20은 PC를 그 칸으로 옮긴다(routing되지 않은 칸은 다음 dispatch의 `unsupported animation machine PC` = 선언 정지). 그 밖의 D0.W(`25294` 직접 진입; 두 번 더한 WORD가 20을 넘거나 음수)는 checked `unsupported animation player c7 jump target`이다. [F] 변위는 WORD 덧셈 결과다(`4002` → `0008` → 칸 2, `8008` → `0020` → 칸 8).
  - [I] ROM의 자료 생산자(`4ae4a`)가 무엇을 돌려주든 `2528c` 경로는 칸 0..8만 만든다. 표의 나머지 칸과 그 대상(`252e6` `252ce` 등, 약 +24 시작)은 계획 결정 4대로 뒤("C 표" 단위)로 미룬다.
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙):
  - LONG 표 `1f65e + sext(4 × BYTE 4(A4))`(`1f648`; ROM 19칸 `1b3dc` `1b3fa` … `1b466`, `1cab6`에 넘기는 표 포인터). D7은 `MOVEQ #0`/`MOVE.B` 뒤라 3fc 이하다.
  - BYTE 표 `22642 + BYTE 4(A4)`(`22656`; ROM 20 byte, 칸 16·17만 1), LONG 표 `225f6 + sext(4 × BYTE 4(A4))`(`2267a`; ROM 19칸, 0이 아니면 `6f1c4`), LONG 표 `225e6 + 4 × BYTE 9e`(`226ca`; ROM `22502 2254e 22502 22502`)와 그 부표 `+ sext(4 × D0.W)`(D0.W = `4 × BYTE 9e`의 bit 8..15 + `MOVE.B 4(A4)`; ROM `22502`/`2254e` 각 19칸 자식 callback).
  - LONG 표 `2284c + 4 × BYTE 9e`(`22894`; ROM `227fc 2280c 2281c 2282c`)와 그 목록 `+ 4 × BYTE 6(A4)`(< 4, 아니면 0; ROM 각 4칸, **칸 0은 0**, 나머지 B4/B4b의 자식 `22b04` `23058` `22dbc` `22ad4` `2308e` `22d94` `235ca` `23a3e`).
  - LONG 표 `25082`/`250c2 + 4 × (BYTE 77 & f)`(`25122`; ROM 각 16칸, `4ae4a`의 A0).
  - bank 창 LONG `2000b8`(`24fb6`), `200094`(`251c8`): CPU 주소(물리 `bank_base + b8` / `+ 94`), `22(A6)`에 저장만 한다.
  - 넘기기만 하는 포인터: `1b24c` `1b2ee` `1b482` `1b632` `1b610` `1b6a8` `1b68a`(A0, C2 `1cab6`/`1cb08`의 표), `1b310`(A0, `1cb08`), script `255ba` `26112` `26178` `6f364`(A1 / LONG `84`, `49f8c`), 자식 `23c56` `253f4`·표의 LONG(A0, `2986`), `100bf4`(A1, `2986`).

### DIVU·MULS(결정 4)

- [F] `22778 DIVU.W #3,D0`(block `22772`): `MOVEQ #0,D0; MOVE.B a1(A6),D0` 뒤라 피제수는 0..ff다. 68000 의미(C4 결정 4): LONG D0를 무부호 WORD로 나눠 몫 ≤ ffff면 D0 := 나머지 WORD << 16 | 몫 WORD, 넘치면 V이고 D0는 그대로, 제수 0이면 zero-divide 예외. **제수는 즉시값 3이라 0 나눗셈이 없고, 피제수 ≤ ff라 몫 ≤ 55로 overflow도 없다** [F]. 실행부 `pc7_divu3`는 overflow 규칙(레지스터 그대로)을 그대로 두지만 도달할 수 없다(변이 동치로 기록). DIVU 뒤의 flag는 아무도 읽지 않는다(`SWAP`·`SUBQ.W`·`MULS`·`ADD.B`가 다시 정하고, `22786 RTS` 뒤 호출자는 interpreter다).
- [F] `22780 MULS.W D7,D0`: 하위 WORD 둘의 부호 곱을 LONG D0에 넣는다(16 × 16 → 32 bit, |곱| ≤ 2^30이라 넘침 없음). `pc7_muls`는 두 WORD를 `std::int32_t`로 부호 확장해 곱하고 `static_cast<std::uint32_t>`로 돌린다(UB 없음). D0.W는 `SUBQ.W #1`로 ffff(나머지 0) / 0 / 1, D7은 `MOVEQ #2`/`#3` 뒤 `ADDQ.W #1` 가능이라 경로상 곱은 −4..4다. 직접 진입 `22772`의 D7은 아무 값이다(시험: `D7.W` ffff·8000·7fff·12348000).
- [F] 결과는 `ADD.B D0,76(A0)`로 자식 BYTE에 더한다(자리올림 버림).

### `28ae`/`2986` 자식

- [F] C7은 `2986`(buffer_cue, 내부 `28ae`)을 다섯 곳에서 부른다: `2268a`(LONG 표 `225f6`의 값, D0 := 1e), `226f0`(부표 값, D0 := a; `22704 BCC`가 C를 읽음), `22872`(`23c56`, D0 := a), `228cc`(목록 값, D0 := a), `253c8`(`253f4`, D0 := 1e). `22704` 말고는 돌아온 C를 읽지 않는다.
- [F] 자식 callback은 이 단위가 실행하지 않는다. `24fb0` `253f4`는 IO에서 실행되어 C7 시작이다. `23c56`(`22878`)은 routing되지 않았고 IO에서 실행되지 않았다 [U: 소속]. 표 자식 `6f1c4`(`JMP 2a00`; 미routing) `2624c` `27a9c` `26aa0` `24ecc` `263ae` `24d46` 등은 미실행·미routing이다. 목록 자식 `22b04` 등은 B4/B4b가 routing했다.
- [F] **`28ae` 실패**(`D0.W ≥ WORD 104ca0` 또는 A0 = 0): buffer_cue 결정 1의 caller-X 한계로 C++는 `cue wrapper failure requires known caller X`로 멈춘다(C6 결정 7과 같음, 결정 6). [F] `228cc`의 목록 칸 0과 `228bc`의 BYTE 6 ≥ 4 경로는 ROM에서 A0 = 0을 만든다. 그 경로는 원본에서 실패 쪽(더미 node `100e98`)으로 이어 가지만 C++는 이 한계로 멈춘다 [I]. [F] IO demo frame 465의 `228cc`는 BYTE 6 = 1(`22b04`), WORD 104ca0 = 44라 성공 쪽이다(`work` 탐침: pack frame 464~488). `22704`의 Clear 쪽(`22786`)은 그래서 V1에서 도달하지 못한 결과로 남는다(단위 시험은 선언 C 행으로 확인).

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `2986` `2a00` `3af8` `8ebe` `ce02` `16ed2` `1cab6` `1cb08` `1cd98` `1cec2` `1f7a4` `1fa3c` `1faa0` `1fad2` `1fae8` `201a2` `2291a`(B3c; `22912`의 직선 연속, `22738 BSR`) `43e34` `443d2` `491b6` `49214` `49a58` `49f8c` `49fc6` `4ae4a` `4bb52` `4be34` `4bfc0` `ea69c`.
- [F] **뒤 단위 정지**(실행되거나 닿지만 뒤 단위가 가짐, routing 밖; V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS`): `1eb98`(`1f59a` `1f724 BEQ`, C8), `1f756`(`1f752 BCC`의 fall-through, C8, demo frame 488의 예측 IO 첫 정지), `1fa68`(`1f302 BNE`, C8). 표 `2529c`의 미routing 칸 8개(`2529c` `252a0` `252a8` `252ac` `252b0` `252b4` `252b8` `252bc`)는 계산 점프 정지다(결정 2).
  - C7 run이 지나가는 C1~C6 block의 남은 정지(pc6 `EXIT_STOPS` 31개 가운데 C7이 routing한 `1f2a4`를 뺀 30개, 그중 `1fa68`은 위 C7 정지와 같음; C1 TRAP `4e69a`, C6의 interpreter stub 후속 `1dc8e` `1dccc` 포함)도 pc7 `EXIT_STOPS`(모두 32개)에 넣었다.
  - [I] 직선 fall-through로 범위를 벗어나는 곳은 `1f756`(조건 분기의 fall-through라 TB 시작으로 기록됨)과 routing된 `2291a`뿐이다. 재관측 `obs_c7a`에서 새로 보인 PC가 없어 가려진 연속은 없다.
- [F] TRAP 없음. ROM·RAM 실행 없음. 장치 쓰기 없음(`MOVE` 대상은 모두 node·work RAM).

### block 경계를 넘는 flag(결정 3)

C6 방식 그대로 `cscan`·호출자 검색과 실행부 검토로 정했다. X를 읽는 명령은 없다.

- [F] **C 소비 block 10개**(Clear 쪽 / Set 쪽; Unknown C면 `player c7 caller requires known carry`): `1ca0e BCS 1ca14`(C7 `1ca4c`), `1f330 BCC 1f33a`·`1f5c4 BCC 1f5ce`·`1f752 BCC 1f76a`·`25454 BCC 2545e`(`49fc6`), `1f644 BCS 1f6aa`·`1f776 BCS 1f77e`(C2 `1cb08`; Set 쪽은 C5 `1cb32`), `22674 BCS 2267a`(C7 `1c9ec`), `22704 MOVEA.L (A7)+,A1; BCC 22786`(`2986`; `MOVEA`는 flag를 바꾸지 않음), `25140 SCS.B 83(A6)`(`ea69c`; Set → ff, Clear → 00).
- [F] **C 생산 block**: Clear `1ca04` `1ca28`(`ANDI.B #fe,CCR; RTS`), Set `1ca46` `1ca56` `1ca6a`(`ORI.B #1,CCR; RTS`).
- [F] **자료 C block 1개**: `1ca5c MOVE.B 2(A4),D2; CMP.B 3(A4),D2; BCS 1ca6a` — C = 무부호 BYTE 2 < BYTE 3(빌림). fall-through `1ca68`은 Clear, 분기 `1ca6a`는 Set(그 block이 다시 Set)이다. 실행부는 두 갈래에 그 값을 남긴다(C6 `1d514`와 같은 처리).
- [F] **C 통과 block 2개**(`carry_preserving_pc`에 넣음): `1ca12 RTS`(`1ca0e`가 읽은 Clear를 `1c9ec` 호출자에게), `1ca68 RTS`(`1ca5c`의 Clear를 `1ca0e`에게). `1c9ec`의 C를 읽는 쪽은 C7 `22674`, 단위 밖 `227be`(BCS)다.
- [F] **돌려주지만 읽는 쪽이 없는 C**: `22678` `22758` `22786` `224c0` `224d4` `224e8` `224f4` `22500` `228b6`(interpreter callback의 RTS: 복귀 `4a354`/`4a43e`; `2285c`·`22656`의 다른 호출자 `1e110 MOVE.W` `6f2a2 JMP`), `251c0` `25486` `25284`(node callback의 RTS). 통과 목록에 넣지 않는다(돌아간 뒤 Unknown).
- [F] **Z가 경계를 넘는 곳은 없다.** 모든 `BEQ`/`BNE`/`BMI`/`BGT`/`BCC`/`BCS`는 같은 block의 `TST`/`CMP`/`CMPI`/`BTST`/`BCLR`/`BCHG`/`AND`/`MOVE`/`SUBQ` 뒤다(`1f70a CMPI.B #1,D1`, `2512c TST.B D0`, `224a6 CMPI.B #6,D0`은 callee 결과를 같은 block에서 비교).
- [F] 신호 있는 비교: `2519a SUBQ.B #1,8b(A6); BGT.W 251c0` — BGT = (Z = 0 ∧ N = V): BYTE b에서 b − 1 > 0을 정확한 정수로 판정한다(b = 80이면 V로 거짓). 실행부: `b ∈ [2, 7f]`. `251c2 CMPI.B #40,76(A6); BMI.W 251e0` — BYTE 차의 N(bit 7)이다(무부호 비교가 아님: c0 → 80 → N).

### IO 실행 run과 frame

- [F] 보정 관측(C6 routing 재관측 `obs_c6`, `work/c7io.py`): C7 PC를 실행하는 run 1개(boot-demo-0), 실행된 C7 PC 101개(시작 96), 실행 1,317회. 처음 실행 frame **431, 432, 440, 441, 442, 443, 453, 465**.
- [F] **IO 예측(C1~C7 연결)**: 173,820 → **173,877**(+57 = demo 431 → 488). 예측 첫 정지: boot-demo-0 frame **488**(C8 `1f756`)뿐. [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다(계획 §7 [U]).
- [F] D1 자연 seed 137개와 P0·P1·P1b·title run은 C7 코드를 실행하지 않는다.

## 공통 규칙·native 검증 계획

FR2..FR9, C1~C6 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_player_c7.cpp`, 함수 `animation_player_c7_block`. 오류 문자열은 `unsupported animation player c7 PC`(범위 안 내부 PC 직접 진입), `player c7 caller requires known carry`(C 소비 block에 Unknown C; 소비자 10개), `unsupported animation player c7 jump target`(결정 2의 표 밖 변위) 세 개다. Z 출처 guard는 없다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(13 범위, C6 줄 뒤), `carry_preserving_pc`의 C6 묶음 뒤에 주석 달린 case 묶음 하나(소비자 10 + 통과 2), `animation_machine_internal.h`에 선언 하나(C6 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# player C7 refresh:` 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 위 명세의 `1f2d4` `1f56a` `1f6da` `25102` `25448`(`25442`)은 쓰고 곧바로 그 값으로 들어가고, `1f3e8`(`1f334` `1f5c8`)과 `25448`(`25284`)은 쓰기만 한다.
- **자료 읽기**(live bus): node field(A6: BYTE `15` `60` `61` `6e` `6f` `76` `77` `7a` `7b` `7e` `83` `88` `89` `8a` `8b` `9e` `a1` `a5` `a6` `a7` `a8` `aa`, WORD `1e` `2e` `32` `42` `46` `78`, LONG `7a` `84` `8c`), 기록 A4(= LONG `8c(A6)` 또는 `5450`/`5460(A5)`: BYTE 2 3 4 6 7, WORD a c), script(A0: LONG (A0) → WORD; A1 = A0의 WORD 셋), 자식(A0: BYTE `76`, WORD `78`), 절대 RAM(BYTE `10f001`), 스택(`22480`/`224a6`의 WORD 둘·LONG A0, `2269e`의 LONG (A7), `22704` `2288e` `228e6` `226c8`의 LONG pop), 고정 ROM 표(위 "계산 점프와 표"), bank 창 LONG 둘. 단위 시험은 고정 ROM 자료 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): WORD 표 `1b310`(`10 0 12 0 14`, +10: `1 2 3`), LONG 표 `1f65e` = `31000 + 40k`, `22502`(38칸) = k가 3의 배수면 0, 그 밖 `32000 + 10k`, `225e6` = `22502 2254e 2254e 22502`, `225f6` = k ≡ 1 (mod 4)이면 0, 그 밖 `33000 + 10k`, BYTE 표 `22642` = k가 2 5 10이면 1, `227fc`(16칸) = `34000 + 10k`, `2284c` = `2280c 227fc 2282c 2281c`, `25082`(32칸) = `35000 + 20k`, bank 창 `2000b8` = `0012abcd`, `200094` = `00345678`. 음수 색인(`225f6 − 8000 = 1a5f6`)과 단위 밖 색인(`225e6 + 100`)은 C++ 전용 규칙에서 합성 byte를 더한 bus(`runs_to_extra`)로 확인한다. V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W/.B`, `ADD.W`, `SUB.W`, `SUBI.W`, `SUBQ.W/.B`, `ADDQ.W/.B`, `ADDI.B`, `ANDI.W/.B`, `AND.W`, `LSR.W`, `LSL.W`, `NEG.B/.W`, `EXT.W`, `CLR.W/.B`, `MOVE.B #imm`). `MOVEQ`·`MOVE.L`·`MOVEA.L`·`LEA`·`CLR.L`은 LONG 전체. 색인 `(An,Dn.W)`·`(PC,Dn.W)`는 부호 확장 WORD. `MOVE.B 4(A4),D0`(`226ca` `2273c`)는 D0 bit 8..15를 그대로 둔다(`226ca`에서는 `4 × BYTE 9e`의 bit 8..9가 남아 부표 색인에 들어감). `LSR.W #n`은 WORD 논리 shift(bit 8..15의 이전 값이 함께 내려옴), 뒤의 `ANDI`가 가린다(`25056`의 `ANDI.B #1f`는 bit 8..15를 남김). `ADDI.B #f`/`ADDQ.B #7`/`#3`/`ADDQ.B #1`/`#3`·`SUBQ.B #1`·`ADD.B`는 BYTE(자리올림 버림). `NEG.B; ADDI.B #80; NEG.W`(`226b0` `2271e` `2290a`)는 BYTE·WORD 반전. 비교: `CMP.B 4(A4),D1`(BYTE), `CMPI.W #ffff,D2`(WORD), `SUBQ.W #1,D2; BCC`(빌림 = 이전 WORD 0), `CMP.B 3(A4),D2; BCS`(무부호 BYTE), `CMPI.B #ff/#0/#1/#5/#6/#8/#a/#40,…`(BYTE), `CMPI.W #2/#8,(A0)`(WORD), `CMPI.W #140,D0` + `BCS`·`SUBI.W #100; CMPI.W #100` + `BCS`(무부호 WORD), `CMPI.B #4,D0` + `BCS`·`CMPI.B #5,89(A6)` + `BCC`(무부호 BYTE), `CMPI.W #9,D0` + `BCC`(무부호 WORD), `SUBQ.B` + `BGT`(부호 BYTE), `CMPI.B #40` + `BMI`(BYTE 차의 N), `TST.W/.B`, `MOVE.L` + `BEQ`(LONG 0). bit: `BTST/BSET/BCLR/BCHG #n,d(An)`·`#n,abs`(memory BYTE, bit mod 8), `BTST #n,D0`(LONG bit n).
- **스택.** `22480`이 WORD `42`, WORD `46`, LONG A0 순서로 넣고 `JSR 4ae4a`, `224a6`이 LONG A0, WORD → `46`, WORD → `42` 순서로 꺼낸다. `2268a` `226f0` `22872` `228cc`(`pc7_child`)가 LONG A0를 넣고 `JSR 2986`; `2269e`는 LONG (A7)를 꺼내지 않고 읽고(A1), `226c8`이 A0로, `22704` `2288e` `228e6`이 A1로 꺼낸다.

## carry(결정 3)

- [F] 소비자 10개·통과 2개·생산자·자료 C는 위 명세와 같다. dispatcher는 `carry_preserving_pc`에 없는 PC로 갈 때 C를 Unknown으로 만든다. 따라서 이 단위의 C 의미는 (1) 소비자 10개가 known C를 읽고 그대로 둔다(`25140`은 그 C를 BYTE로 저장), (2) 통과 block `1ca12` `1ca68`이 들어온 C를 그대로 둔다, (3) 생산자 `1ca04` `1ca28`(Clear) `1ca46` `1ca56` `1ca6a`(Set)와 자료 C `1ca5c`가 자기 block에서 C를 정한다, (4) 나머지 block 뒤 C는 Unknown이다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1..FR9·C1~C6 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: 그 node(A6)에 선언 편집. ROM 쓰기 명령·호출자가 범위를 정한 값은 그 범위 안으로 둔다: WORD `76`/`78` 대부분 0/1, BYTE `9e(A6)` 0..3, LONG `8c(A6)` := 선언 기록(BYTE 4 대부분 0..12, BYTE 6 대부분 1..3), A0 = script 기록(LONG → WORD 셋), `25294` 직접 진입의 D0.W 0..8(`4002` 등 WORD 넘침 포함), LONG `84(A6)` := C3 목록의 routing된 칸 값(`253f4` node는 script `6f364`), LONG `26(A6)` := 0(`49fc6` Set, 무작위 script의 interpreter 회피), WORD `104ca0` := 100(`28ae` 한도), BYTE `10fd82` := 0. `28ae` 실패 경로(PC `290e`)를 지난 native run은 fixture에서 뺀다(결정 6).
- **IO pack 자연 node 상태(family `natural`, 25개)**: boot-demo-0 frame 432 440 441 442 443 447 448 453 459 465 480의 node pool에서 callback LONG이 C6 `1ebf6` 또는 C7 설치 값·자식(`1f2d4` `1f56a` `1f6da` `25102` `25448` `24fb0` `253f4`)인 node, 레지스터만 선언(A5 := `108000`, A6 := node, A7 := `10ef00`(복귀 LONG = sentinel), PC := callback).
- **재설치 world(family `reinstall`, 9개)**: demo frame 431 node `100cb8`에 `1f2a4`(그리고 frame 441에 BYTE `9e` = 1), frame 465에 `1f5d2` `1f76e`, frame 440에 `1f5f2`(BYTE `a7` = 0 / 1)·`1f538`, frame 443에 `1f6da`(BYTE `7e` = 1), frame 432에 `1f6da`(BYTE `15` = 0). [I] 이미 진행된 node를 다시 시작하는 world이며 native와 C++가 같은 상태를 받으므로 V1 비교는 유효하다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다(`CHAINS` 10개): `1ca0a`(`1ca4c`), `1f32a` `1f5be` `1f74c` `2544e`(`49fc6`), `1f640` `1f76e`(`1cb08`, 원본 ROM 표 `1b310`/`1b632`…의 WORD와 LONG `22(A6)` 표를 맞춤), `22670`(`1c9ec`, A5 기록), `226f0`(`2986`, Set만: Clear는 결정 6의 checked 한계), `2513a`(`ea69c`).
- node fixture: 설치 값·자식 7개를 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다. callee fixture: helper `1c9ec` `1ca4c`, script callback `22480` `22656` `2285c`, 꼬리 `1f2a4` `1f538` `1f5d2` `1f5f2` `1f648` `1f76e` `226ca` `22894` `2273c` `2528c` `252c0` `25132` `251c2` `25172`를 subroutine으로 들어간다.
- 단위 시험(Unicorn 생성기, C6 꼴; 장치 port 없음을 확인): 시작 214개(소비자 10개 제외) × 들어오는 C 3가지, zero-step, 내부 PC 921개 정확한 오류, 경계 stop(출구·뒤 단위 정지·표 칸 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC. 손으로 계산한 규칙(`rules_a`..`rules_g` + 변이 빈틈 규칙): 아래 "검증 수치".

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `bd037aff436d5b102749b0c97562660c5b32423736393f679dede2d2dcecefd4` → `1f4599a2480e6998abc34f8141e93cb790ea7cd5694852290bbe3dd7596ab97d`, `animation_machine_internal.h` `5458ca6c08b35b69780549b938650f1c649eed535a4ce1760b828644efd6d9a5` → `8ae7ae9276347fb2fb5349ed57e8c3d979da36c30042cbf4181da341ea8f0737`(이 단위의 공유 수정; 옛 값은 `# player C7 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 작업 트리에서 확인했다(`work/pincheck.py`, `trial_logs/pincheck_tree.log`).
- [F] **B4 시험 `engine/tests/animation_machine_objects_b4_test.cpp`**: 이전 = 자료 PC 목록 `data[]`의 `1c9ec`를 `unsupported animation machine PC`로 거부(공용 helper 범위 `1c9b8..1c9ec`의 끝). 새 = `1c9ec`를 목록에서 빼고 "player C7 시작: B4 범위 밖, stop-only" 확인 하나로 바꿨다(주석에 이전 기대값). [F] 이전 기대값으로 두면 `1c9ec`가 C7으로 실행되어 A5 = 0의 ROM 읽기 오류가 난다(첫 `make test` 실패, `trial_logs/make_try1.log`).
- [F] **C6 시험 생성기·V1 spec·시험**(`tools/generate_animation_machine_player_c6_test_table.py`, `tools/unit_fixture_specs/pc6.py`, `engine/tests/animation_machine_player_c6_test.cpp`): 오류 행 `error-1ec2c-then-1f2a4`(이전 = `1f2a4`에서 `unsupported animation machine PC`) → 같은 이름, A7 홀수, `program bus requires even WORD/LONG address`, 실패 PC `1f2a4`(C7 `1f2a4`의 `BSR.W 1cab6`이 홀수 A7에 push). 원래 뜻(실패 PC `1f2a4`)을 지키는 C5·C6 선례의 홀수 A7 방식이다. 생성기를 다시 돌려 이 행 하나만 바뀜을 확인했다(`work/c6_test_before.cpp` 대비 diff 1줄). C6 시험 줄: 1,248 fixtures, 180,401 checks(같음).
- [F] **V1 spec `ROUTED_LATER`**(선언 정지로 그대로 둠, C2~C6가 쓴 방식): pc2 += `1f2a4`; pc3 += `1f2a4`; pc4 += `1f2a4`; pc5 += `1f2a4`; pc6(이전 빈 목록) := `1f2a4`. `EXIT_STOPS`에 `1f2a4`가 있는 spec은 이 다섯뿐이다.
- [F] 바뀌지 않음(확인): motion-walk 검증기의 계산 out-of-range PC 86개와 guard PC는 C7 범위에 없다(`work/mw_oor7.py`, `trial_logs/mw_oor7.log`). C2·C4 시험의 `1f2a4`·C2/C3/C6의 `1fa68`은 stop으로만 쓰인다(stop은 dispatch보다 먼저 검사). 저장소 tools·시험에서 C7 범위 안 PC를 쓰는 다른 곳은 자료 값(n33/n34/fr3/motion-walk 시험의 레지스터 값)과 주석(`observe_animation_bank_state.py`의 `22656`, B3c 생성기의 `2285c`)뿐이다(전수 검색). 다른 단위 소스의 주석은 고치지 않았다(다른 검증기가 그 소스 SHA를 pin할 수 있음).
- [I] native 사슬이 이 단위의 PC를 첫 routing 밖 PC로 멈추던 V1 spec·검증기는 더 진행한다(정지는 routing에서 계산된다). pc2~pc6은 `1f2a4`를 선언 정지로 두어 fixture 집합이 같다(V1 회귀 수는 아래 기록). 나머지는 메인 runner의 회귀·legacy 단계가 확인한다.

## 결정

1. **범위와 시작(scope correction): 계획 217 block에서 C3 결정 10의 `1cde0` `1cdf0` `1cdfa`를 빼 214 block, 13 범위. 숨은 직선 block 추가 없음. C8과 병합하지 않음.**
   - [F] 재측정(214) = 계획 − {`1cde0`, `1cdf0`, `1cdfa`}. 범위 밖에서 범위 안 비시작 PC로 들어오는 직접 분기는 없다.
   - [F] **숨은 직선 연속 검사**: C6 routing과 C7 가상 routing 각각으로 C·E run 18개를 정확한 bitmap으로 다시 관측했다(`reobs_c7/obs_c6`, `reobs_c7/obs_c7a`, native 기록은 18 run 모두 원래와 같음). 새로 보인 PC 0개, C7 routing 관측의 예측 첫 정지는 demo frame 488의 C8 `1f756`뿐이다. 예측 173,877은 계획 표와 같다.
   - [F] C7 + C8 = 214 + 98 = 312 block(약 230 초과)이라 병합을 제안하지 않는다.
2. **계산 점프 `25298`: 실행된 칸 `252a4`만 전사, 변위 0..20은 표 칸(미routing 칸은 선언 정지), 그 밖은 checked jump-target 오류.** 고정 ROM 표·bank 창은 live bus로 읽고 상한을 검사하지 않는다(C3 결정 5와 같음).
3. **RTS를 넘는 C.** 소비자 10개는 known C를 읽거나 checked 오류. `1ca5c`의 `CMP.B` 빌림은 자료 C로 두 갈래에 남기고, `1ca04` `1ca28` Clear, `1ca46` `1ca56` `1ca6a` Set. 통과 block `1ca12` `1ca68`만 `carry_preserving_pc`에 더한다(생산자는 자기 block에서 C를 정하므로 넣지 않음, FR 관례). Z가 경계를 넘는 곳은 없다.
4. **DIVU·MULS.** `DIVU.W #3`은 C4 결정 4의 의미(overflow면 레지스터 그대로, 제수 0은 checked 오류)를 따르되 이 단위에서는 둘 다 도달할 수 없다(즉시값 3, 피제수 ≤ ff). zero-divide 오류 문자열은 두지 않는다(제수가 상수라 C++ 0 나눗셈이 생기지 않음). `MULS.W`는 부호 WORD 곱의 LONG.
5. **뒤 단위 정지와 앞 단위 spec.** C7 block이 닿는 뒤 단위 시작 3곳(`1eb98` `1f756` `1fa68`)과 표의 미routing 칸 8곳, C1~C6의 남은 정지 29곳을 V1 `first_unrouted`와 실제 ROM 차분의 선언 정지로 둔다. pc2~pc6의 `EXIT_STOPS` 가운데 C7이 routing한 `1f2a4`는 `ROUTED_LATER`로 허용하고 선언 정지로 그대로 둔다.
6. **`2986`/`28ae` 실패 경로.** buffer_cue 결정 1(caller-X 한계는 의도된 checked 오류)을 그대로 둔다(B4 결정 4, C5 결정 8, C6 결정 7과 같음). C7에서는 `228bc`의 BYTE 6 = 0 또는 ≥ 4가 ROM 목록 칸 0(LONG 0)을 골라 A0 = 0이 되므로, 무작위 world에서 이 경로가 흔하다. V1 spec은 `28ae` 실패 PC `290e`를 지난 native run을 fixture로 쓰지 않고, 실제 ROM 차분은 기존 문서화 분류로 센다. [F] IO demo에서 C7의 `2986` 호출 넷(frame 440 `226f0`, 441 `253c8`, 465 `228cc`, 그리고 자식 생성)은 모두 성공 쪽이다.
7. **interpreter script callback.** `22480` `22656` `2285c`는 interpreter callback 표 `4a500`의 칸 값이다. A0(script의 LONG)와 interpreter의 스택은 interpreter 실행부가 정한다. C7은 callback 몸체만 routing한다. 표의 다른 칸(`3679e` `36b2c` `6f282` `6f2d8` 등)은 routing 밖으로 남는다.
8. **실행부 파일·오류 문자열.** 위 "공통 규칙". 오류 문자열 3개.
9. **다음.** 계획 순서대로 C8(demo frame 488의 `1f756` …, 재측정 98 block). C7 연결로 IO +57(173,877)을 메인 runner가 확인한다. 자식 `23c56`·표의 미실행 자식, 쓰기만 하는 `1f3e8`(C8)·`1fcd4`의 소속은 C8 이후 계획에서 정한다.

## 미확인

- [U] node field·전역 값의 의미(BYTE `15` `61` `6e` `6f` `7e` `83` `88` `89` `8a` `8b` `9e` `a1` `a5` `a6` `a7` `a8` `aa`, WORD `2e` `32` `42` `46` `7a`, A5 기록 `5450`/`5460`, BYTE `10f001`, 표 `1f65e` `22642` `225f6` `225e6` `2284c` `25082` `250c2`, script `255ba` `26112` `26178` `6f364`). 이름(입력 상태, script callback, 자식, 흔들기)은 동작에서 붙인 [I]이다.
- [U] IO 관측에서 실행되지 않은 이 단위의 block 118개(`1c9f8` `1ca04` `1ca12` `1ca28` `1ca3a`~`1ca42` `1ca5c`~`1ca6a`, `1f2d4` `1f2ea`~`1f306` `1f31a`~`1f33a`, `1f538`~`1f5ce` 대부분, `1f62c` `1f640`, `1f6f0`~`1f702`, `1f76e`~`1f782`, `224b8`~`22500` 대부분, `22678`~`226c8`, `2271e`, `2275a`~`22786`, `2286a`~`2288e`, `228b6` `228bc` `228ca` `228e8` `2290a`, `2503a` `25054` `2506c`, `2511e`~`25284` 대부분, `2546a` `25480`)는 closure로 들어왔다(V1 선언 상태·재설치 world·실제 ROM 차분으로만 확인).
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC). 예측은 demo frame 488의 C8 `1f756`이다.
- [U] 재설치 world와 IO pack 자연 node 상태의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C6와 같음).
- [U] 결정 1의 정확 bitmap 재관측은 C·E run 18개만 했다(계획 §7과 같은 범위).
- [U] 자식 `23c56`과 표 자식들의 소속(결정 9). IO 관측에서 실행되지 않았다.
- [U] `1f5c4`의 Clear 쪽(`1f5ce`)은 V1에서 도달하지 못했다(V1 world는 LONG `26(A6)` = 0으로 `49fc6`의 interpreter를 피함). 단위 시험의 선언 C 행과 실제 ROM 차분이 확인한다.
- [U] Unicorn 2.1.4 native oracle abort(실제 ROM 차분, C6에서도 관측)의 원인.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_player_c7.cpp`(case label 214 = `starts_C7_final.txt`와 집합 일치; 공용 함수 `pc7_get` `pc7_put` `pc7_bit`(memory BYTE bit; 0 시험, 1 세움, 2 지움, 3 바꿈) `pc7_field_bit` `pc7_input_bit` `pc7_byte_zero` `pc7_carry` `pc7_return_carry` `pc7_field_call` `pc7_word_call` `pc7_8ebe_call` `pc7_install` `pc7_slot` `pc7_slot_state` `pc7_jitter` `pc7_x_bound` `pc7_y_bound` `pc7_triple` `pc7_mirror` `pc7_child` `pc7_times4` `pc7_divu3` `pc7_muls` `pc7_ext` `pc7_table_jump`), `engine/tests/animation_machine_player_c7_test.cpp`(생성 구역 + 수작성 규칙), `tools/generate_animation_machine_player_c7_test_table.py`(생성기; C6 생성기 꼴, 자료 C `data_carry`는 출력 RAM의 BYTE 3(A4)와 D2.B, 계산 점프 착지 검사 `JUMP_ALLOWED`, `25140 SCS`의 C는 BYTE `83`; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 100초), `tools/unit_fixture_specs/pc7.py`(V1 spec; C6 spec의 공용 부분 그대로(scratch `work/mkpc7.py`가 조립), 단위 부분 교체, `EXIT_STOPS`(32), `PASS_SET` `CLEAR_SET` `SET_SET` `DATA_SET`, `JUMP_PCS` `TABLE_2529C`, family `reinstall`, `290e` 필터). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `starts_C7_final.txt`(SHA256 `f95f6bbd592ed620e1ce6352b5bcacbca2843d3449a7dd28b695813db35684d5`) = 계획 `starts_C7.txt`(217) − `1cde0` `1cdf0` `1cdfa`(C3 결정 10).

- **`1c9ec..1ca74`(20)**: `1c9ec 1c9f8 1c9fc 1ca04 1ca0a 1ca0e 1ca12 1ca14 1ca20 1ca28 1ca2e 1ca3a 1ca40 1ca42 1ca46 1ca4c 1ca56 1ca5c 1ca68 1ca6a`
- **`1f2a4..1f7a4`(67)**: `1f2a4 1f2ac 1f2d4 1f2d8 1f2e2 1f2ea 1f2f4 1f2fc 1f306 1f30a 1f312 1f31a 1f320 1f32a 1f330 1f334 1f33a 1f538 1f546 1f56a 1f56e 1f578 1f580 1f58a 1f592 1f596 1f59e 1f5a6 1f5ae 1f5b4 1f5be 1f5c4 1f5c8 1f5ce 1f5d2 1f5f2 1f614 1f62c 1f634 1f63e 1f640 1f644 1f648 1f6aa 1f6ae 1f6da 1f6de 1f6e8 1f6f0 1f6fa 1f702 1f706 1f70a 1f712 1f71a 1f728 1f732 1f73c 1f742 1f74c 1f752 1f76a 1f76e 1f776 1f77a 1f77e 1f782`
- **`22480..22502`(14)**: `22480 224a6 224b8 224c0 224c2 224ca 224d4 224d6 224de 224e8 224ea 224f4 224f6 22500`
- **`22656..22788`(25)**: `22656 22670 22674 22678 2267a 2268a 2269e 226b0 226b8 226c2 226c8 226ca 226f0 22704 2270a 2271e 22726 2273c 2274e 22758 2275a 22764 22766 22772 22786`
- **`2285c..2291a`(15)**: `2285c 2286a 22872 2288e 22894 228ae 228b6 228b8 228bc 228ca 228cc 228e6 228e8 2290a 22912`
- **`24fb0..25082`(11)**: `24fb0 24fc8 24fec 24ffa 25026 2503a 2503e 25054 25056 2506c 2506e`
- **`25102..25488`(62)**: `25102 25108 2511e 25122 2512c 25132 2513a 25140 25144 2514e 25158 2515e 25166 2516c 25172 2517e 25184 25194 2519a 251ac 251b6 251ba 251c0 251c2 251da 251e0 251f6 251fc 25210 2521a 25220 2523a 25240 25254 2525a 25264 2526a 25276 25284 2528c 25294 252a4 252c0 252ca 253c8 253de 253ee 253f4 25402 25414 25422 25428 25438 25448 2544e 25454 25458 2545e 2546a 25470 25480 25486`

## 검증 수치

작업자 최종 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j3 all test`(최종 실행부·시험): 종료 0, 경고 0, Python 310 OK(`trial_logs/make_final.log`). C7 시험 줄: `animation machine player pc7: 1270 fixtures (831 single-block, 342 path, 24 producer chain, 20 declared C, 53 checked error (17 with a later failing PC), 108 kept C), 214 blocks, 5593 calls, 198167 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 실제 사슬 두 C 값 4개(`1ca0a`→`1ca0e`, `1f640`→`1f644`, `1f76e`→`1f776`, `22670`→`22674`; `49fc6` 사슬 넷은 interpreter가 선언 밖 ROM을 읽어 native run이 버려지고, `226f0`은 Set만(결정 6), `2513a`(`ea69c`)는 Clear만 나와 선언 C 행만), 출구 중 stop이 아닌 것 0, `25294` 행이 표 칸 9개 모두에 멈춤. 생성기를 다시 돌려 시험 파일이 바이트 단위로 같음을 확인했다(`trial_logs/gen_c7_repro2.log`). 다른 player 시험 줄은 C6 기록과 같다(C6 1,248 fixtures / 180,401 checks; B4 751 fixtures).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, `work/ubsan.sh`, C7·C6·B4 시험): 빌드 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_build.log` `ubsan_player_c7.log` `ubsan_player_c6.log` `ubsan_objects_b4.log`).
- [F] V1 pc7(작업자, `--workers 3`, scratch `work/v1_pc7_try6`): fixture 2,077개(block 950, chain 14, node 17, natural 25, reinstall 9, callee 66, error 968, failpc 18, negative 10) failed 0, 방문 시작 214/214, carry oracle Unknown/Clear/Set = 969/53/77(`trial_logs/v1_pc7_try6.log`). 도달 못한 분기 결과 2개: `1f5c4 → 1f5ce`(`49fc6` Clear; V1 world는 LONG `26(A6)` = 0), `22706 → 22786`(`2986` Clear = `28ae` 실패, 결정 6). 앞선 시도의 실패는 모두 spec 결함이었다: try1 BYTE hint 값 105, try2 `253f4` node의 LONG `84`(script `6f364`가 아니면 interpreter가 code를 script로 읽음), try3~try5 `2986`의 `28ae` 실패(caller-X)와 무작위 script의 interpreter dispatch 한계 → V1 world에 WORD `104ca0` := 100, BYTE 6(A4) 1..3, LONG `26(A6)` := 0을 두고 PC `290e`를 지난 run을 뺐다(결정 6).
- [F] V1 회귀(작업자, `work/v1_regs.sh`): pc1 1,264/1,264, pc2 1,743/1,743, pc3 1,831/1,831, pc4 1,873/1,873, pc5 1,755/1,755, pc6 1,856/1,856, se1 2,102/2,102, fr1 1,631/1,631(모두 failed 0; 수는 C6 기록과 같음, `work/v1_regs.txt`). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·op, WORD/BYTE → LONG, 복귀 PC·호출 대상, carry tag, mask, 상수·설치 값·자식 값, 부호 확장 제거, `pc7_*` helper 인자) + 손으로 고른 helper·block 변이(`DIVU.W #3` 몫·나머지·overflow, `MULS.W` 부호·크기·피연산자, `EXT.W`, 표 점프 guard·base·폭, `BGT` 부호, `BMI`, `LSR.W` 폭, `ANDI.W/.B`, `ADDI.B` 자리올림, `CMP.B` 빌림, MOVE.B가 남기는 bit 8..15, push/pop 순서, slot 초기화 등) + dispatcher carry 목록 12개·추가·범위 1개를 적용해 만든 것, 868개; `--workers 2/3`): 1회째 `killed 832 of 868`(`trial_logs/mut_first.log`). 생존 36개 중 9개는 시험 빈틈이었고 규칙 `rules_h`로 메웠다(`mut_gaps.log`: `killed 9 of 36`): `1f614`의 BYTE `aa` 크기, 색인 WORD의 bit 8..15(`1f648` BYTE 4 = 40 → `1f75e`, `22894` BYTE 9e = 40 → `2294c`, `228cc` D0 = 40, `25122` D0 = 100, 모두 합성 byte를 더한 bus), 부호 확장(`228cc` D0 = 2000을 위쪽 RAM 거울 `1fec00`에서 `1f6c00` = `106c00`; 0 확장이면 bank 창 `206c00`, `25122` D0 = 8000을 ROM 창 `1d082`), `2528c`의 WORD 비교(`0100`), `25294`의 표 변위 `0108`. 남은 27개는 동치다(`mut/equivalents.txt`, 사례별 이유 기록: 값의 범위로 보이지 않는 mask·폭 9(`NEG.B`의 하위 BYTE, BYTE 인자, `ANDI.W #1`/`AND.W #c` 뒤, 0..ff 색인, `ANDI`가 가리는 `LSR.W` 상위), `MOVEQ #0` 뒤 BYTE라 상위가 0인 쓰기·두 배 8, 색인 범위로 bit 15가 서지 않는 부호 확장 4, `pc7_bit`의 상수 bit·`am_write`의 자체 mask 2, `DIVU`의 몫이 `SWAP`·`MULS`로 보이지 않음·overflow 불가능 3과 `SUBQ.W`의 LONG 빌림을 `MULS`가 덮음 1). 규칙을 더하고 생성 표를 다시 만든 뒤 전체 2회째 `killed 841 of 868`(`trial_logs/mut_second.log`), 남은 27개가 동치 목록과 같다. `DIVU`/`MULS` 변이는 `divu-rem2` `divu-swapped` `divu-norem` `muls-unsigned` `muls-xunsigned` `muls-yunsigned` `muls-word` `22772-mulsd7d0` `22772-noswap` 모두 검출, `divu-2` `divu-noovf` `divu-ovf-ge` `22772-sublong`만 동치다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`, 메인 runner용), `real_pc7.py`(C6 harness에 C7 world(`pc7_world`)·소비자·통과·선언 정지·표 칸 정지; C7 계산 점프의 착지를 trace 전체에서 대조하는 분류 `JUMPTGT7` 추가; `native_safe` 기본 유지)): 작업자 300건 seed 1 `mismatches 0`(`covered starts 198 of 214`; 문서화된 분류 `2986` caller-X 21건(결정 6), C3 jump-target 13건(무작위 slot-84 LONG의 `201a6`), C7 jump-target 0건; 정지하지 않은 native 62건 건너뜀; native oracle abort 0, `trial_logs/real_n300_s1.log`). 앞선 50건 seed 11 시험은 `mismatches 0`, native oracle abort 1건(entry `25294`, fork한 자식이라 그 사례만 건너뜀; `trial_logs/real_t50.log`).
- [F] `dleft.py`: 이전(routing `bd037aff…`) C 194 / E 0, 예측 173,820, 첫 정지 C 1(`trial_logs/dleft_before.log`; 재관측 `obs_c6a`·`obs_c6`로도 같음). 이후(routing `1f4599a2…`) C **93** / E 0, 예측 **173,877**, 첫 정지 C 1(`dleft_after.log`; 재관측 `obs_c7a`로도 같음). 예측 첫 정지 PC(`work/firststops_after.txt`): boot-demo-0 frame 488의 C8 `1f756`뿐; 나머지 run은 정지 없음.
- [F] 기존 검증기 새 기대값은 scratch에서 확인했다: B4·C6 시험은 `make test`로, CPP_PINS는 작업 트리와 scratch clone root(`roots/probe`, `work/mkroot.py`: 작업 트리 clone + 변경 파일 복사 + 공유 자료 symlink)에서 파일 SHA와 같음을 확인했다(4 / 9 pin, 불일치 0, `trial_logs/pincheck_tree.log` `pincheck_root.log`).

## 메인 결정(2026-10-23)

- 실행되지 않은 자식 `23c56`, 다른 미실행 표 자식, 쓰기만 하는 callback `1f3e8`은 선언 정지로 두고 나머지 단위 C9~C13을 다시 잴 때 넣는다(C6 메인 결정과 같다).

## 검증 기록(검증 실행: 결정적 runner + 메인 검토)

- [F] `make -j3 all test`: 종료 0, 경고 0, Assert 0, Python 310 OK. C7 시험 `animation machine player pc7: 1270 fixtures (831 single-block, 342 path, 24 producer chain, 20 declared C, 53 checked error (17 with a later failing PC), 108 kept C), 214 blocks, 5593 calls, 198167 checks`.
- [F] `ubsan`: build/run 종료 0, runtime errors 0.
- [F] `mutation`: total 868, killed 841, equivalent 27.
  - 이 실행 전에 메운 시험 빈틈 9개.
  - 메모: 테이블이 256 바이트를 넘거나 음수 인덱스로 읽히는 경우, 상위 RAM 미러 `1fec00`과 ROM 창 `1d082`가 부호 확장 누락을 드러낸다. 결과를 바꾸는 DIVU/MULS 경계 변이는 제거된다.
- [F] real-ROM: batches `f4`, `f5`, `s1`, `s2`, `s3` covered `213`, `214`, `214`, `214`, `213`; mismatches `0,0,0,0,0`(합집합 214/214).
  - 오라클: `native_safe` 켬.
- [F] V1: A/B 각각 fixtures 2077, failed 0, runs 2, identical true(digest `d794d500fa4d4857`); regression specs 40개 모두 failed 0.
- [F] legacy verifiers: `stage_entry`, `area_clear`, `stage_event`, `stage_event_ops`, `frame_helpers`, `card_menu_close`, `input`, `scene_core`, `scheduler`, `objects_g1` 모두 종료 0. `objects_g1` 판정은 C1과 같다.
- [F] frames: `d1` 54400/54400, mismatches 0; `controller_game` 54400/54400, mismatches 0; `irq` 54400/54400, mismatches 0; `demo` 45684/45684, mismatches 0.
- [F] IO: matched_total 173877, baseline 173820, delta 57, mismatches 0, cpp_errors 0, runs 2, identical true; per_config `P0` 81600, `P1` 81600, `P1b` 8400, `boot-demo-0` 488, `boot-title-idle` 600, `boot-title-start` 906, `fx-bios-call` 3, `fx-c-input-read` 3, `fx-n-input-read` 3, `fx-queue-short` 1, `fx-start-c79a` 273.
  - 예측 확인: 정확한 비트맵 재관측은 173877을 예측했고, 실측도 173877이다.
  - 수락 항목 중 실패한 항목은 `frontiers_confirmed`다. `boot-demo-0`만 여전히 frame 488에서 TB 안에 숨은 C8 `1f756`에서 일찍 멈추므로 검증기가 이를 확인할 수 없다.
  - 범위: 214블록은 계획 217에서 `1cde0`, `1cdf0`, `1cdfa`(C3이 담당)를 뺀 값이고, 숨은 직선형 블록은 없다.
- [F] 남은 실행 PC: C 194 → 93, E 0.
- 검증 방법: 결정적 runner(LLM 없음). 이 기록 초안은 local Qwen이 썼고 메인이 검토·수정했다.

## 뒤 단위 변경 기록: player C10(2026-10-24, 작업자 Claude Opus 5.5 / high)

C10 계약(`animation-machine-player-c10-contract.md`) 결정 2·4와 계획 §10.x 메인 결정 4에 따른 기록이다. C7 실행부의 동작은 바뀌지 않았다(주석만 고침).

- [F] **표 `25298`의 전사 칸**: 이전 = 실행된 칸 `252a4`만 C7 block(위 결정 2). 새 = `252a4`(C7)와 `252b4`(→ `BRA.W 252ce`, C10 block; 이어지는 `252ce` `252d8` `252e2`도 C10)가 routing된 칸이다. 칸 선택 규칙(변위 0..`20`은 칸, 그 밖은 checked jump-target 오류)은 그대로다. [F] 정확 bitmap 재관측에서 실행된 칸은 `252a4`와 `252b4`뿐이다(`252a8` → `252ce`는 실행되지 않음). 나머지 7칸은 계속 뒤 단위 정지다.
- [F] 실행부 `animation_machine_player_c7.cpp`의 `pc7_table_jump` 주석, 생성기 `JUMP_TARGETS` 주석, V1 spec 주석을 고쳤다. C7 단위 시험은 `252b4`를 정지로만 쓰므로 바뀌지 않는다(정지 검사가 dispatch보다 먼저).
- [F] V1 spec `pc7.py`: 표 칸 검사 `{252a4}` → `{252a4, 252b4}`(소유자 C7 또는 C10). 오류 fixture `25294-d0-6-entry`(이전: `252b4`에서 `unsupported animation machine PC`) → `25294-d0-6-then-252d8`(`252b4` → `252ce`(BYTE `61(A2)` bit 7 clear) → `252d8 JSR 3af8`가 홀수 A7에서 실패; `25294`와 `252b4`/`252ce`는 스택을 쓰지 않음). `EXIT_STOPS`·`ROUTED_LATER`에 C10 진입 14개를 더했다. V1 pc7 2,077 그대로.
