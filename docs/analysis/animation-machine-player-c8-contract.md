# 영역 C 단위 C8(데모 전용 플레이어 상태 `1f756` → `1f3d8` → `1f3ec`/`1f418`, `1fa68` → `1fafc`/`1fb02`(이동 helper `1cfde`/`1cff8`/`1d066`), `201bc` → `1fcce`/`1fcd4` → `1fd12`(`ea626`, 기록 helper `4d1ac`), C3 helper 꼬리 `4d0cc`, 입력 분기 `1ef4c`·`1eb98`·`1ce98`, 칸 `84` 상태 `21e3a` → `21e52` → `21e6a`와 `JMP (A1)` `21d9e`/`21e76`, 99 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §4.2의 C8 행과 아래 "C8 상세 명세"(계획 §8과 같은 꼴, 이 계약에서 새로 씀)를 기준으로 삼고, 구조·공통 규칙은 C7 계약(`animation-machine-player-c7-contract.md`)·C6 계약·C5 계약·C4 계약·C3 계약·C2 계약·C1 계약을 따르며 다른 점만 적는다. 단위 이름은 C8, 파일 접두어는 `player_c8`(C++) / `pc8`(V1 spec)다(계획 메인 결정 7). 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다. C8은 계획 순서의 마지막 IO 단위다. 이 계약 끝에 "C 완료 판정(이 관측 집합)"을 둔다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기와 장치 쓰기는 없다(장치·bank는 callee가 다룬다). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `2058960`(branch `claude/c8-core`; C1~C7, E1 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `1f4599a2480e6998abc34f8141e93cb790ea7cd5694852290bbe3dd7596ab97d`, `animation_machine_internal.h` `8ae7ae9276347fb2fb5349ed57e8c3d979da36c30042cbf4181da341ea8f0737`.
- [F] 관측 입력: native IO 관측 `artifacts/animation_machine_io_native`(읽기 전용; state pack `states/boot-demo-0/boot.pack.gz`), 계획의 보정 관측 `ms5-scratch/c1/reobs/`(읽기만), 그리고 이 단위의 정확 bitmap 재관측 두 벌(scratch `reobs_c8/obs_c7`, `reobs_c8/obs_c8a`; 결정 1).
- [F] 시작 목록: **`ms5-scratch/c8/starts_C8_final.txt`(99개, SHA256 `646381e98a3bd723e615a94f8e608059b34b2f869ecad4549a16ffd261f431d1`)**. 계획 scratch `ms5-scratch/c8/starts_C8.txt`(계획 §6 표의 `646381e98a3bd723`)와 같은 목록이다. 재측정 목록 `remeasure/r8_C8.txt`(98개, SHA256 `fb7b452a27a22a965a675244bbe735f4fb86bdd937421c3e9636c1e9672c916d`, C7 계약의 `r7_C8.txt`와 같음)에 `1fcd4`를 더한 것이다(결정 1). 실행부의 `case` label 99개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(작업자 확인: `make test`의 C8 시험이 시작 99개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/c8/`
  - `remeasure/remeasure8.py` → `r8.json` `r8_C8.txt`(재측정), `work/mkunits8.py` `work/units_r8.json`, `work/udetail8.py` → `work/udetail_C8_r8.txt` `work/C8_r8.dis.txt`(범위·출구·역어셈블, `>` = block 시작, `*` = IO 실행 TB 시작), `work/c8ranges_r8.txt`(범위), `work/callers_c8_all.out`(ROM 전체 직접 분기 호출자와 다음 명령), `work/intargets.py`(범위 안 비시작 PC로 오는 직접 분기), `work/c8io.py` `work/c8io_obs_c7.txt` `work/c8io_frames.txt`(IO run·frame), `work/natsig8.py` `work/natsig8.out` `work/natsig8_frames.out`(IO 자연 node), `work/newvis_c7_c8a.txt`(재관측 사이 새로 보인 PC), `work/firststops_before.txt` `work/firststops_c8a.txt` `work/firststops_after.txt`(예측 첫 정지), `work/pincheck.py`(CPP_PINS 대조), `work/mkpc8.py` + `work/pc8parts/`(V1 spec 조립: C7 spec의 공용 부분 + C8 부분), `work/mkc8test.py` `work/c8test_head.txt` `work/c8rules.cpp`(C8 시험 파일 조립: C7 시험의 공용 harness + C8 규칙), `work/v1_regs.sh`(V1 회귀), `work/ubsan.sh`, `reobs_c8/`(정확 bitmap 재관측, `run_reobs.sh`), `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **재측정 전**(`MS5_REOBS=…/c1/reobs dleft.py`, routing `1f4599a2…` = C1~C7 + E1): 실행된 routing 밖 PC C **93** / E 0 / D 0, 예측 일치 frame **173,877**, 첫 정지 C 1(`trial_logs/dleft_before.log`). C7 계약의 C7 뒤 값과 같다.
- [F] **closure 재측정(C1~C7 routing 상태)**: C7 작업자 방식 그대로 계획 spec `plan/plan_final.json`과 계획 당시 key(`remeasure/keys_old.json`)로 현재 routing에서 `cplan3`을 돌렸다(`remeasure/remeasure8.py`, `trial_logs/remeasure_r8.log`). **C8 = 98 block, 205 명령, 874 byte, 18 범위**(시작 목록 SHA `fb7b452a27a22a96…`), 예측 173,966(+89), 남은 C 0 / E 0, 첫 정지 없음. C7 작업자의 재측정(`r7_C8.txt`)과 같다. 계획 목록(99)과의 차이는 `1fcd4` 하나다(결정 1).
- [F] **범위 밖에서 범위 안 비시작 PC로 들어오는 직접 분기**: 없다(`work/intargets.py`). 찾은 하나(`19c1c dbls d0,1fd1e`)는 routing된 `19c1a MOVE.L D7,53c8(A5)`의 operand(`53c8`)를 명령으로 읽은 것이다.
- [F] **정확 bitmap 재관측**(결정 1; scratch `tools/reobs.py`, 관측기 수정 없음; C·E run 18개, `--workers 3`, `reobs_c8/run_reobs.sh`):
  - C7 routing(`1f4599a2…`, routing된 짝수 PC 127,499) 그대로: `reobs_c8/obs_c7`(`observation.json` compared_sha256 `7ab003a7b7bf397e…`), `reobs_check.py`: 18 run 모두 native 기록이 원래와 같다(`ALL NATIVE RECORDS EQUAL … True`, `trial_logs/reobs_check_obs_c7.log`). `dleft.py` → C 93 / E 0, 예측 **173,877**, 첫 정지 C 1: boot-demo-0 frame **488**의 `1f756`(`work/firststops_before.txt`; C7 계약의 `obs_c7a`와 같음).
  - C8 범위를 가상 routing(`EXTRA_ROUTED`, `work/c8ranges_r8.txt`)에 넣은 bitmap(짝수 PC 127,936): `reobs_c8/obs_c8a`(compared_sha256 `bbf2c2f46a9f892d…`, native 기록 18 run 모두 같음). `dleft.py` → C **0** / E **0** / D 0, 예측 **173,966**, 첫 정지 **없음**(`trial_logs/dleft_c8a_obs_c8a.log`, `work/firststops_c8a.txt` 빈 목록). 18 run 모두 600 frame 끝 또는 guard까지 정지가 없다.
  - [F] 두 관측 사이에 새로 보인 routing 밖 PC(TB 안에 가려진 직선 연속)는 **없다**(`work/newvis_c7_c8a.txt`: 18 run 모두 0; boot-demo-0의 routing 밖 PC 119 → 26, 나머지 26개는 덮는 원자의 PC로 C·E·D가 아님). 그래서 숨은 직선 block 추가는 필요 없다(C5~C7 결정 1과 같은 결과). 예측 첫 정지가 없으므로 반복을 한 번으로 멈췄다.
- [F] **측정 결과**(`dleft.py`, 최종 routing `2622b7a2…`): `MS5_REOBS=…/c1/reobs` → C 93 → **0**, E 0, D 0, 예측 일치 frame **173,877 → 173,966**(+89), 첫 정지 없음(`trial_logs/dleft_after.log`). `MS5_REOBS=…/reobs_c8/obs_c8a`로도 같다(`dleft_after_obs_c8a.log`, `work/firststops_after.txt` 빈 목록). 최종 routing의 짝수 PC 수 127,936은 `obs_c8a` bitmap과 같다.

## C8 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **99 block, 205 명령, 874 byte, 18 범위**(시작 목록 SHA256 `646381e98a3bd723…`, 범위 이어 붙인 SHA256 `0c4c549f20098ba60166ec822798b4ac9a70a87b47f92659a3de9cc7105b7afb`). 짝수 PC 437(내부 338). 아래 표는 구현 범위다.

| 범위(CPU = 파일 오프셋) | byte | SHA256(앞 16자) | 시작 | 내용 [I] |
| --- | --- | --- | --- | --- |
| `1ce98..1cea8` | 16 | `7950ddf99eb898ac` | 2 | C2 `1cd98` 입력 함수 안 갈래 `1ce98`(BYTE `15` bit 0이 0이면 `BSET #3,a7`), C2 `1cea8`로 떨어짐 |
| `1cfde..1d086` | 168 | `10df5d435f2e8360` | 20 | 이동 helper `1cfde`(BYTE `6e` ≠ 8이면 LONG `3a` := 0; `1cfbe`의 기록 A0: `3a += LONG 10(A0)`), `1cff8`(`3a += (LONG 18(A0) − 3a) ASR 5`; BYTE `61` bit 0이 0이면 D1 = LONG 14(A0); D0 bit 2 / 3으로 `D7 = ∓D1`, D2 = 2; `36 += (D7 − 36) ASR D2`; BYTE `a7` bit 3과 `D0 & 50`이면 BYTE `15` bit 0 반전·`a7` bit 3 지움), `1d066`(LONG `3a`를 스택에 두고 `4be82`, 꺼낸 LONG이 음수가 아니고 BYTE `61` bit 1이 0이면 `3a`에 다시 씀) |
| `1eb98..1eba0` | 8 | `94f58832842dc760` | 1 | `LEA 1b328(PC),A0; BRA.W 1ebbe`(C6) |
| `1ef4c..1ef6c` | 32 | `62f85773ae081eb1` | 4 | C4 상태 `1ef0e`의 입력 갈래(BYTE `9e`, D0 bit 1 → `1f7a4`, `D0 & c` → `1fa68`, 아니면 `1fa3c`) |
| `1f3d8..1f3e0` | 8 | `965f4514ca3685e9` | 1 | 설치 값 `1f3d8`: `LEA 1b2ae(PC),A0; BRA.W 1f3ec` |
| `1f3ec..1f48a` | 158 | `34e6e5536b52a157` | 18 | `1cab6`, 칸 부분(LONG `84` := `21602`, `9c` := 0, `aa` := 1, WORD `7a` := 0, `a9` := 2), LONG `64` := 0, 상태 `1f418`(`1cd98` 입력, BYTE `15` bit 7, D0 bit 5 / 1 / 6 / 4, BYTE `9e`, `AND.W #c` → `1fad2` `1f7a4` `1f76e` `1eb98` `1f5d2` `1f5f2` `1f48a`, `4bfc0` `ce02` `49fc6`의 C, `1f3e8` 쓰기만, `201a2`로) |
| `1f756..1f76a` | 20 | `e1d7449d23ba8206` | 2 | C7 `1f752 BCC`의 fall-through: `(A6)` := `1f3d8`, BYTE `88` ≠ 0이면 `(A6)` := `1f3e0`(쓰기만), C7 `1f76a`로 |
| `1fa68..1fa90` | 40 | `1071aa49ef8cbce5` | 5 | `1cb08`(표 `1b716`)의 C: Set → `1fa90`(C5); Clear → `1cab6`(표 `1b74a`), `1cfde`, `9c` := 4, `a9` := 1 → `1fafc` |
| `1fafc..1fb28` | 44 | `e77a7cd3b2a05bea` | 7 | `(A6)` := `1fb02`, 상태 `1fb02`(`1cd98`, `1cff8`, `1d066`, `ce02`, `49fc6`, BYTE `15` bit 7 → `1fb28`(미룸) / `1fb2e`) |
| `1fb2e..1fb32` | 4 | `846c1e17ddc18a0b` | 1 | `BRA.W 201a2` |
| `1fcce..1fd3c` | 110 | `035730c2d12b2169` | 8 | 설치 값 `1fcce`(WORD `90` := 8) → 설치 값 `1fcd4`(C6 `1dbca`가 씀; BYTE `61` bit 7 지움, `5e` := 0, `82` `81` := ff, LONG `56` := 0, 칸 부분(`a9` := 0), `(A6)` := `1fd12`) → 상태 `1fd12`(`ea626`, BYTE `a8` bit 3, `4de7a`(D0 = WORD `78`), `4d1ac`, `484b4`의 C: Clear → `1fd3c`(미룸), Set → `201a2`) |
| `201bc..201d0` | 20 | `93a5e53011c8e584` | 3 | C3 `201b8 BCC`의 Set 쪽: BYTE `a7` bit 7을 세우고 이전에 0이었으면 `(A6)` := `1fcce`, C3 `201da`로 |
| `21d9e..21da0` | 2 | `96e3a4f65944fc97` | 1 | C4 `21d9a BCC`의 Set 쪽: `JMP (A1)`(목록 `21b0a`, 결정 2) |
| `21e3a..21e48` | 14 | `cc604d26d1eaba72` | 1 | 목록 handler `21e3a`: `aa` := 1, `LEA 1b9c6(PC),A0; BRA.W 21e52` |
| `21e52..21ea0` | 78 | `4367d9c4d597b080` | 12 | `TST.B 9d(A6); BGT 21ea0; BLT 21d0e`(둘 다 미룸), `1cabe`, 칸 `84` := `21e6a`(곧바로 들어감), `215e6`(목록 `21b3c`)의 C: Set → `JMP (A1)` `21e76`(결정 2); Clear → `1cd98`, D0 bit 0 / 1 / 6 / 4 → `223a0` `223d6` `21ffc` `2210c`, 아니면 `2156a` |
| `4d0cc..4d100` | 52 | `3547bd4623177617` | 6 | C3 helper `4d0a4`의 `4d0ba BNE` 쪽: BYTE `22(A4)`, WORD `18(A4)`와 WORD `-7ff2(A5)` 비교, `484b4`의 C: Set → `22(A4)` := 0, Set으로 RTS; 그 밖 → WORD `(A4)` := 0, `22(A4)` := 1, C3 `4d100`(Clear, RTS)으로 |
| `4d1ac..4d208` | 92 | `bbc9f5da5c089f5d` | 6 | 기록 helper `4d1ac`(A4 = `5cba`/`5ce6(A5)` by WORD `78`; WORD `(A4)` ≠ 0이면 BYTE `15`의 bit 7·0을 BYTE `28(A4)`에서 가져오고 LONG `2e` `32` `36` `3a` `3e` := `(W2 << 16) + L10`, `(W4 << 16) + L14`, 0, 0, LONG `c(A4)`(`MOVEM.L D0-D3/A1,2e(A6)`), `43e34`) |
| `ea626..ea62e` | 8 | `5d2094677c815fda` | 1 | `MOVE.B #ff,5e50(A5); RTS` |
| 합계 C8 | 874 | 이어 붙인 바이트 `0c4c549f…` | **99** | 짝수 PC 437(내부 338) |

- [F] **진입(실행된 PC를 줄인 closure 진입, 재측정 `entries`)**: `1f756` `1cfde` `1cff8` `1d066` `1ef4c` `21d9e` `21e3a` `1ce98` `201bc` `4d0cc`.
- [F] **IO 실행**(`work/c8io_obs_c7.txt`; C7 routing 재관측): 실행된 C8 PC 93개(시작 87 + TB 분할 PC 6 `1cfe4` `1cff2` `1cff6` `1cffe` `1d002` `21e5a`), 실행 **1,763회**(계획 1,763), run 1개(boot-demo-0). 실행된 TB 시작이 아닌 시작 12개(`1d01c` `1d058` `1ef68` `1f42e` `1f438` `1f440` `1f480` `1f764` `1fcd4` `21e76` `4d0f6` `4d1bc`). `1d01c`와 `1fcd4`는 앞 block과 같은 TB 안에서 실행된다(`1d018`, `1fcce`의 직선 연속).
- [F] **호출자**(ROM 전체 직접 분기 검색 `work/callers_c8_all.out`, 다음 명령 포함):
  - `1cfde` ← C8 `1fa7c`, C2 `1fa4c` `1fac4`(다음 명령 `LEA` / `MOVE.L #`: flag를 읽지 않음). `1cff8` ← C8 `1fb06`, 뒤 단위 `1ff1e`(다음 `JSR 484b4`). `1d066` ← C8 `1fb0a`, 뒤 단위 `1dfa6 JSR (PC)` `1ff30`(다음 `MOVE.W`). `4d1ac` ← C8 `1fd28`(다음 `JSR 484b4`). `ea626` ← C8 `1fd12`, C6 `1dad8` `1dc2a` `1dd00` `1dd54`, 뒤 단위 `1d764` `1dc00` `1de4c`(다음 `JSR 4836e` / `SUBQ.W` / `BSET`: flag를 읽지 않음).
  - `1fa68` ← `BNE.W` 8곳: C6 `1ec24`, C2 `1edde`, C3 `1f194`, C7 `1f302`, C8 `1ef64`, 뒤 단위 `1ece6` `1f012` `1f0dc`. `1eb98` ← `BEQ.W` 5곳: C8 `1f448`, C7 `1f59a` `1f724`, 뒤 단위 `1f39e` `1f4e6`. `1fafc` ← C8 `1fa8c`, C2 `1fa64`. `1ce98` ← C2 `1ce94 BEQ`의 fall-through. `1ef4c` ← C4 `1ef48 BEQ`의 fall-through. `1f756` ← C7 `1f752 BCC`의 fall-through. `201bc` ← C3 `201b8 BCC`의 fall-through. `21d9e` ← C4 `21d9a BCC`의 fall-through. `4d0cc` ← C3 `4d0ba BNE`. `21e3a`는 `215e6` 목록 `21622` `21aee` `21b26` `21b0a`의 handler LONG이다(C3 `21620`, C4 `21c72`, C5 `21f7c`, C8 `21d9e`).
- [F] **설치 값**(`MOVE.L #v,(A6)`): 곧바로 들어감 `1f418`(`1f412`) `1fb02`(`1fafc`) `1fd12`(`1fd0c`). 다음 frame에 들어감 `1f3d8`(`1f756`) `1fcce`(`201c6`). **쓰기만**: `1f3e0`(`1f764`), `1f3e8`(`1f480`; C7 `1f334` `1f5c8`도 씀) — C8 범위 밖이고 IO에서 실행되지 않으며 routing 밖 선언 정지로 남는다(C6·C7 메인 결정과 같음). `1fcd4`는 C6 `1dbca`가 쓰기만 하는 값이지만 C8 block `1fcce`의 직선 연속이라 시작으로 둔다(결정 1). 둘째 callback 칸 `84(A6)` := `21602`(`1f3f0` `1fcee`; C3 허용 목록 안), `21e6a`(`21e62`; C3 허용 목록 안, 곧바로 들어감).
- [F] **IO run의 node**(`work/c8io_frames.txt`, `work/natsig8_frames.out`): boot-demo-0 player node `100cb8`. frame 488에 C7 `1f6da` → `1f752`(Set) → `1f756` → `1f76a` → `201a2`. frame 489에 `1f3d8` → `1f3ec` → `1f3f0` → `1f418` … `1f45c` → `1f466` → `1f476` → `1f47c`(`49fc6` Clear) → `1f486`. frame 490 `1f418`, 491 `1eb98`. frame 496에 C4 `1ef0e` 경로의 `1ef4c` → `1ef5e` → `1fa68` → `1fa70`(Clear) → `1fa74` → `1cfde` … `1fafc` → `1fb02` 사슬(`1cff8` `1d066`), 그리고 C3 `201a6 JSR (A4)`의 칸 `84` = `21d92`(C4) → `21d9e JMP (A1)` = `21e3a` → `21e52` → `21e5e` → `21e62` → `21e6a` → `21e72`(`215e6` Clear) → `21e78` … `21e9c`. frame 497 `1fb02` `21e6a`, 502 `1d03a`, 508 `1d084`, 510 `1ce98` `1cea2` `1d026` `1d04e`, 514 `201bc` `201c6` `4d0cc` … `4d0ea`(Set), 515 `1fcce` → `1fd12` … `4d1ac` … `1fd34`(`484b4` Set) → `1fd38`, 516 `1fd12`. [I: frame 516 뒤의 frame-start pack에서 node를 다시 돌리면 `201d0 BCLR` → `1fd50`(C11)으로 가지만, IO 기록에는 `1fd50`이 없다(`obs_c8a`의 routing 밖 PC 목록). frame-start 상태 재실행은 실제 dispatcher 진입과 다르다(C7 계약 IO node 항목과 같은 한계).]

### 계산 점프와 목록(결정 2)

- [F] **`JMP (A1)` 두 곳**. A1은 C3 `215e6`(목록 조회, C3 계약 결정 2)이 ROM 목록에서 `MOVEA.L (A0)+,A1`로 읽은 handler LONG이다. `215e6`은 key WORD = BYTE `9c(A6)`가 같은 칸을 찾으면 C Set, LONG 0(목록 끝)에서 C Clear로 돌아온다. `JMP`는 Set 쪽에서만 실행된다.
  - `21d9e JMP (A1)`(C4 `21d92 LEA 21b0a(PC),A0; BSR 215e6` → `21d9a BCC 21da0`의 Set 쪽). 목록 `21b0a`([F] ROM 바이트): (`21602`, 0) (`21c22`, 1) (`21e48`, 3) (`21e3a`, 4), LONG 0. **허용 대상 = `21602`(C3) `21c22`(C3) `21e48`(routing 밖) `21e3a`(C8)**.
  - `21e76 JMP (A1)`(C8 `21e6a LEA 21b3c(PC),A0; BSR 215e6` → `21e72 BCC 21e78`의 Set 쪽). 목록 `21b3c`: (`21602`, 0) (`21c22`, 1) (`21d60`, 2), LONG 0. **허용 대상 = `21602`(C3) `21c22`(C3) `21d60`(C4)**.
  - C3 `21620`·C4 `21c72`·C5 `21f7c`와 같은 규칙: A1이 그 목록의 handler면 PC := A1(routing 밖 `21e48`은 다음 dispatch의 `unsupported animation machine PC` = 선언 정지), 그 밖의 A1(직접 진입)은 checked `unsupported animation player c8 jump target`이다. 비교는 LONG 전체다(`121602`, `1021e3a`는 거부).
  - [I] ROM 자료 생산자(`215e6`와 그 목록)가 만드는 A1은 언제나 허용 목록 안이다. 목록 `21b0a`의 `21e48`(미실행 handler)은 뒤 단위(C12 계획 범위)로 미룬다.
- [F] PC 상대 BRA.W 표·DIVU·MULU/MULS는 없다.
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙): 이동 기록 A0의 LONG `10` / `14` / `18`(`1cfee` `1cffa` `1d018`; A0는 C4 `1cfbe`가 ROM 표 `1cfce + 4 × BYTE 9e`에서 읽은 기록 `1cf1e` / `1cf3e`). 직접 진입의 A0는 아무 값이다(RAM이면 RAM을 읽음).
- [F] 넘기기만 하는 포인터: `1b328`(→ C6 `1ebbe`), `1b2ae` `1b74a`(A0, C2 `1cab6`), `1b716`(A0, C2 `1cb08`), `1b9c6`(A0, C2 `1cabe`), `21b3c`(A0, C3 `215e6`).

### `MOVEM`·`ASR.L`(결정 4)

- [F] **`4d1fa MOVEM.L D0-D3/A1,2e(A6)`**(register → memory, 제어 주소 방식, mask `020f`): 낮은 주소부터 D0, D1, D2, D3, A1 순서로 LONG 다섯 개를 `2e` `32` `36` `3a` `3e(A6)`에 쓴다. flag는 바꾸지 않는다. 실행부는 같은 순서로 `pc8_put` 다섯 번을 한다(실패하면 run 전체가 되돌려짐). 그 앞의 D0 = `(WORD 2(A4) << 16) + LONG 10(A4)`, D1 = `(WORD 4(A4) << 16) + LONG 14(A4)`(`MOVEQ #0` → `MOVE.W` → `SWAP` → `ADD.L`, 모두 mod 2^32), D2 = D3 = 0, A1 = LONG `c(A4)`.
- [F] **`ASR.L D2,Dn`**(`1d006` `1d03e`): 68000 의미로 count = D2 mod 64(레지스터의 하위 6 bit), count ≥ 32면 부호 bit만 남는다(0 또는 ffffffff), count 0이면 값 그대로. `pc8_asr`는 부호 있는 shift 없이 무부호 LONG에서 `>> count`와 위쪽 채우기 `0xffffffff << (32 − count)`(count 1..31)로 계산한다(UB 없음). 경로상 D2는 `MOVE.W #5` / `#2` 뒤라 5 / 2이고, 직접 진입 `1d03a`의 D2는 아무 값이다(시험: 0 1 1e 1f 20 21 3f 40 45 `12340005`). ASR.L·ADD.L·SUB.L 뒤의 C·X는 아무도 읽지 않는다(`ADD.L`이 다시 정하고 `BTST`는 Z만 바꾸며, 다음 소비자 없음).

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `ce02` `1cab6` `1cabe` `1cb08` `1cd98` `1cea8` `1cfbe` `1ebbe` `1f5d2` `1f5f2` `1f76a` `1f76e` `1f7a4` `1fa3c` `1fa90` `1fad2` `201a2` `201da` `2156a` `215e6` `21ffc` `43e34` `484b4` `49fc6` `4be82` `4bfc0` `4d100` `4de7a`, 그리고 `JMP (A1)`의 routing된 handler `21602` `21c22` `21d60`.
- [F] **뒤 단위 정지**(미룬 입구, 계획 §4.1의 22곳 가운데 C8 block이 닿는 8곳; V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS`): `1f48a`(C11, `1f462 BNE`), `1fb28`(C11, `1fb24 BEQ`의 fall-through), `1fd3c`(C11, `1fd34 BCC`), `21ea0` `21d0e`(C12, `21e56 BGT` / `21e5a BLT`), `2210c`(C12, `21e98 BNE`), `223a0` `223d6`(C13, `21e80` `21e88 BNE`). 목록 handler `21e48`(routing 밖)은 계산 점프 정지다(결정 2). 쓰기만 하는 `1f3e0` `1f3e8`은 범위 밖 routing 밖이다.
  - C8 run이 지나가는 C1~C7 block의 남은 정지(pc7 `EXIT_STOPS` 32개 가운데 C8이 routing한 11개 `1eb98` `1f756` `1fa68` `ea626` `1ef4c` `21d9e` `1ce98` `1cfde` `1fafc` `201bc` `4d0cc`와 C8 정지와 겹치는 `2210c` `223a0` `223d6` `21d0e`를 뺀 17개: `1d3e0` `4eb6a` `1dc8e` `1dccc` `208fa` `1efd6` `1f070` `21dd0` `4ef08` `1de3c` `1e21c` `1e8de` `1fc96` `1fd50` `21ca4` `21fa6` `4e69a`)도 pc8 `EXIT_STOPS`(모두 25개)에 넣었다.
  - [I] 직선 fall-through로 범위를 벗어나는 곳은 `1fb28`(미룸)과 routing된 `1cea8`(C2) `1f76a`(C7) `4d100`(C3)뿐이다. 재관측 `obs_c8a`에서 새로 보인 PC가 없어 가려진 연속은 없다.
- [F] TRAP 없음. ROM·RAM 실행 없음. 장치 쓰기 없음(`MOVE` 대상은 node·A5 기록·work RAM).

### block 경계를 넘는 flag(결정 3)

C7 방식 그대로 호출자 검색(다음 명령)과 실행부 검토로 정했다. X를 읽는 명령은 없다.

- [F] **C 소비 block 5개**(Clear 쪽 / Set 쪽; Unknown C면 `player c8 caller requires known carry`): `1f47c BCC 1f486`(C2 `49fc6`), `1fa70 BCS 1fa90`(C2 `1cb08`; Set 쪽은 C5 `1cb32`), `1fd34 BCC 1fd3c`·`4d0e6 BCC 4d0f6`(C3 계열 `484b4`: `BTST #3,5683(A5)`의 bit로 Set / Clear), `21e72 BCC 21e78`(C3 `215e6`).
- [F] **C 생산 block**: Set `4d0ea`(`MOVE.B #0,22(A4); ORI.B #1,CCR; RTS`; C3 `201b8 BCC`가 읽음). `4d0f6`은 C3 `4d100`(`ANDI.B #fe,CCR; RTS`, C3의 Clear 생산자)으로 떨어진다.
- [F] **C 통과 block, 자료 C block**: 없다.
- [F] **돌려주지만 읽는 쪽이 없는 C**: `1cfee`(ADD.L) `1d064` `1d084` `4d206` `ea626`(MOVE.B: Clear)의 RTS. 호출자의 다음 명령(`work/callers_c8_all.out`)은 모두 flag를 다시 정하거나(`MOVE` `SUBQ` `BSET`) 다른 호출(`JSR` / `BSR`)이고, `LEA`(`1fa50`) 뒤의 명령도 `BSR`이다. 통과 목록에 넣지 않는다(돌아간 뒤 Unknown).
- [F] **Z가 경계를 넘는 곳은 없다.** `1d070 MOVE.L (A7)+,D0; BMI.W`은 같은 block의 `MOVE`가 정한 N(꺼낸 LONG의 bit 31)을 읽는다. 나머지 `BEQ`/`BNE`는 같은 block의 `TST`/`CMP`/`CMPI`/`BTST`/`BSET`/`AND` 뒤다.
- [F] 신호 있는 비교: `21e52 TST.B 9d(A6); BGT.W 21ea0; BLT.W 21d0e`(묶인 Bcc 둘, 둘째 `21e5a`는 같은 block): BYTE를 부호 있는 값으로 본다(01..7f → `21ea0`, 80..ff → `21d0e`, 0 → `21e5e`).

### IO 실행 run과 frame

- [F] 보정 관측(C7 routing 재관측 `obs_c7`, `work/c8io.py`): C8 PC를 실행하는 run 1개(boot-demo-0), 실행된 C8 PC 93개(시작 87), 실행 1,763회. 처음 실행 frame **488, 489, 490, 491, 496, 497, 502, 508, 510, 514, 515, 516**(`work/c8io_frames.txt`).
- [F] **IO 예측(C1~C8 연결)**: 173,877 → **173,966**(+89 = demo 488 → 577; frame 578은 그 run의 guard `invalid-memory-access`). 예측 첫 정지: **없음**. [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다(계획 §7 [U]).
- [F] D1 자연 seed 137개와 P0·P1·P1b·title run은 C8 코드를 실행하지 않는다.

## 공통 규칙·native 검증 계획

FR2..FR9, C1~C7 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_player_c8.cpp`, 함수 `animation_player_c8_block`. 오류 문자열은 `unsupported animation player c8 PC`(범위 안 내부 PC 직접 진입), `player c8 caller requires known carry`(C 소비 block에 Unknown C; 소비자 5개), `unsupported animation player c8 jump target`(결정 2의 목록 밖 A1) 세 개다. Z 출처 guard는 없다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(18 범위, C7 줄 뒤; `)ok=animation_player_c8_block(c);`를 같은 줄에 둔다 — `tools/verify_animation_machine_unit_fixtures.py`, scratch `hroute.py` 등이 `)ok=`를 붙여서 찾는다), `carry_preserving_pc`의 C7 묶음 뒤에 주석 달린 case 묶음 하나(소비자 5), `animation_machine_internal.h`에 선언 하나(C7 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# player C8 refresh:` 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 위 명세의 `1f418` `1fb02` `1fd12`는 쓰고 곧바로 그 값으로 들어가고, `1f3d8`(`1f756`)과 `1fcce`(`201c6`)은 쓰고 dispatcher로 돌아가며(다음 frame), `1f3e0` `1f3e8`은 쓰기만 한다.
- **자료 읽기**(live bus): node field(A6: BYTE `15` `61` `6e` `88` `9c` `9d` `9e` `a7` `a8`, WORD `1e` `78`, LONG `36` `3a`), 이동 기록 A0(LONG `10` `14` `18`), A4 기록(`4d0cc`: BYTE `22`, WORD `18`, WORD `(A4)`; `4d1c6`: BYTE `28`, WORD `2` `4`, LONG `c` `10` `14`), A5 WORD `-7ff2`(= `A5 + sext(800e)`), 스택(`1d070`의 LONG pop), 고정 ROM(이동 기록, 위 "계산 점프와 목록"). 단위 시험은 고정 ROM 자료 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): WORD 표 `1b716`(`10 0 12 0 14`, +10: `1 2 3`; C2 `1cb08` 사슬용), 목록 `21b3c` = (`21602`, 0) (`21c22`, 3) (`21d60`, 2), 0(handler는 ROM과 같고 key가 다름; C3 `215e6` 사슬용). 이동 기록은 RAM 기록(`10e900` …)으로 직접 들어가 시험한다(`1cfbe`의 ROM 표 읽기는 C4 범위라 생성기 행이 그 앞에서 멈춘다). `-7ff2(A5)`의 부호 확장은 A5 = `1f8000`(위쪽 RAM 거울: `1f000e` = `10000e`, 0 확장이면 bank 창 `20000e`)으로 확인한다. V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W #k`, `MOVE.W d(An)`, `AND.W`, `MOVE.B`, `AND.B` `NOT.B`(레지스터 BYTE), `AND.B`/`OR.B Dn,15(A6)`(memory BYTE)). `MOVEQ`·`MOVE.L`·`MOVEA.L`·`LEA`·`CLR.L`·`ADD.L`·`SUB.L`·`ASR.L`·`SWAP`은 LONG 전체(mod 2^32). 비교: `CMPI.B #8,6e(A6)`·`TST.B`·`CMPI.B #0`(BYTE), `CMP.W -7ff2(A5),D0`·`TST.W`(WORD), `MOVE.L` + `BMI`(LONG bit 31), `TST.B` + `BGT`/`BLT`(부호 BYTE). bit: `BTST/BSET/BCLR/BCHG #n,d(An)`(memory BYTE, bit mod 8), `BTST #n,D0`(LONG bit n).
- **스택.** `1d066`이 LONG `3a(A6)`를 넣고 `JSR 4be82`(복귀 `1d070` 위에 그 LONG), `1d070`이 LONG을 꺼낸다(callee가 그 칸을 바꿨으면 바뀐 값). 직접 진입 `1d070`의 A7은 그 LONG을 가리킨다.

## carry(결정 3)

- [F] 소비자 5개·생산자는 위 명세와 같다. dispatcher는 `carry_preserving_pc`에 없는 PC로 갈 때 C를 Unknown으로 만든다. 따라서 이 단위의 C 의미는 (1) 소비자 5개가 known C를 읽고 그대로 둔다, (2) 생산자 `4d0ea`(Set)가 자기 block에서 C를 정한다, (3) 나머지 block 뒤 C는 Unknown이다. `4d0f6`의 Clear는 C3 `4d100`이 정한다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1..FR9·C1~C7 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: 그 node(A6)에 선언 편집. ROM 쓰기 명령·호출자가 범위를 정한 값은 그 범위 안으로 둔다: WORD `78` 대부분 0/1, BYTE `9e(A6)` 0..3(C4 표 `1cfce`), BYTE `9c` 0..5(`215e6` key), 이동 기록 A0(직접 진입 `1cfee` `1cffa` `1d018`), A4 = `5cba`/`5ce6(A5)` 또는 선언 기록(`4d0cc` … `4d1c6`), `JMP (A1)` 직접 진입의 A1 = 그 목록의 handler(결정 2), `1d070` 직접 진입의 스택 LONG, LONG `84(A6)` := C3 목록의 routing된 칸 값(C8 `21e6a` 포함), LONG `26(A6)` := 0(대부분; `49fc6` Set, 무작위 script의 interpreter 회피), LONG `5434(A5)` := 0(C2 결정 2), BYTE `10fd82` := 0. native trace에서 `JMP (A1)`이 목록 밖으로 가면 그 world는 버린다(C++는 checked 오류).
- **IO pack 자연 node 상태(family `natural`, 10개)**: boot-demo-0 frame 488 489 490 497 503 508 511 515 516 520의 node pool에서 callback LONG이 C7 `1f6da` 또는 C8 설치 값(`1f3d8` `1f418` `1fb02` `1fcce` `1fcd4` `1fd12`)인 node, 레지스터만 선언(A5 := `108000`, A6 := node, A7 := `10ef00`(복귀 LONG = sentinel), PC := callback). frame 532의 pack은 쓰지 않는다(native oracle Unicorn이 그 상태에서 process abort; C6·C7의 [U]와 같음, `work/natsig8_frames.out`). pool 주소 `100d3c`(= `100cb8 + 84`, 칸 `84` LONG)는 node가 아니므로 `21e6a`를 자연 callback 목록에 넣지 않는다.
- **재설치 world(family `reinstall`, 9개)**: demo frame 489 node `100cb8`에 `1f3d8`(BYTE `9e` = 1), frame 490에 `1f418`(BYTE `9e` = 1)·`1ef4c`, frame 497에 `1fb02`(BYTE `a7` = 8 / BYTE `61` = 3)·`1fa68`, frame 515에 `1fcd4`·`1fcce`(WORD `78` = 1), frame 488에 `1f756`(BYTE `88` = 1). [I] 이미 진행된 node를 다시 시작하는 world이며 native와 C++가 같은 상태를 받으므로 V1 비교는 유효하다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다(`CHAINS` 5개): `1f476`(`49fc6`), `1fa68`(`1cb08`, 원본 ROM 표 `1b716`의 WORD c..10과 LONG `22(A6)` 표를 맞춤), `1fd2e` `4d0e0`(`484b4`, BYTE `5683(A5)`), `21e6a`(`215e6`, ROM 목록 `21b3c`의 key BYTE `9c`).
- node fixture: 설치 값 6개를 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다. callee fixture: helper `1cfde` `1cff8` `1d066` `4d1ac` `ea626`, C3 꼬리 `4d0cc`, 분기 대상 `1ce98` `1ef4c` `1eb98` `1f756` `1fa68` `201bc` `21e3a`, 칸 상태 `21e6a`, `JMP (A1)` `21d9e`, 안쪽 진입 `1cffa` `1d03a` `4d1c6`을 subroutine으로 들어간다.
- 단위 시험(Unicorn 생성기, C7 꼴; 장치 port 없음을 확인): 시작 99개(소비자 5개 제외) × 들어오는 C 3가지, zero-step, 내부 PC 338개 정확한 오류, 경계 stop(출구·뒤 단위 정지·목록 handler 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC. 손으로 계산한 규칙(`rules_a`..`rules_g`): 아래 "검증 수치".

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `1f4599a2480e6998abc34f8141e93cb790ea7cd5694852290bbe3dd7596ab97d` → `2622b7a2374959c551dea03156bc48ab1f7995118a1c1664e80e30ad36d443c5`, `animation_machine_internal.h` `8ae7ae9276347fb2fb5349ed57e8c3d979da36c30042cbf4181da341ea8f0737` → `57606da7148c24cc37efdec0560ea0f8a6ec6ce95932953f63cd8012c1499662`(이 단위의 공유 수정; 옛 값은 `# player C8 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 작업 트리와 scratch clone root에서 확인했다(`work/pincheck.py`, `trial_logs/pincheck_tree.log` `pincheck_root.log`).
- [F] **C4~C7 시험 생성기·시험**(오류 행; 이전 = 그 PC에서 `unsupported animation machine PC`, C8이 그 PC를 routing해서 C++가 C8 코드를 실행하므로 바뀜. 원래 뜻(실패 PC)을 지키는 C5~C7 선례 방식):
  - C4 `error-21c72-listed-21e3a`, C5 `error-21f7c-listed-21e3a`: A6 := 0 → C8 `21e3a`의 `MOVE.B #1,aa(A6)`가 고정 ROM에 써서 `unsupported animation machine write device`, 실패 PC `21e3a` 그대로. `-listed-21e48` 행은 그대로(`21e48`은 routing 밖).
  - C6 `error-1ec1e-then-1fa68`: A7 홀수 → C8 `1fa68`의 `BSR.W 1cb08`이 `program bus requires even WORD/LONG address`, 실패 PC `1fa68` 그대로. `error-1dad8-then-ea626`: A5 := 0 → C8 `ea626`의 `MOVE.B #ff,5e50(A5)`가 고정 ROM 쓰기, 실패 PC `ea626` 그대로.
  - C7 `error-1f2fc-then-1fa68`: A7 홀수, 실패 PC `1fa68` 그대로. `error-1f752-then-1f756`: A6 홀수 → `1f756`의 LONG 쓰기가 `invalid animation machine write size/alignment`, 실패 PC `1f756` 그대로. `error-1f596-then-1eb98`·`error-1f71a-then-1eb98`: `1eb98`(`LEA; BRA.W 1ebbe`)에는 접근이 없어 실패 PC를 지킬 수 없다. A7 홀수로 C6 `1ebbe`의 `BSR.W 1cab6`에서 실패하도록 바꿨다(실패 PC `1eb98` → `1ebbe`).
  - 생성기 네 개를 다시 돌려 그 행만 바뀜을 확인했다(`work/c4_test_before.cpp` … `c7_test_before.cpp` 대비 diff: C4 1줄, C5 1줄, C6 2줄, C7 4줄). 시험 줄의 fixture·check 수는 C7 기록과 같다(pc4 1,372, pc5 1,184, pc6 1,248, pc7 1,270 fixtures).
- [F] **V1 spec**: `ROUTED_LATER`(선언 정지로 그대로 둠, C2~C7이 쓴 방식): pc2 += `1ce98` `1cfde` `1fa68` `1fafc`; pc3 += `1fa68` `201bc` `4d0cc` `1ce98` `1cfde` `1fafc`; pc4 += `1ef4c` `21d9e` `1ce98` `1cfde` `1fa68` `1fafc` `201bc` `4d0cc`; pc5 += 같은 8개; pc6 += `1fa68` `ea626` `1ef4c` `21d9e` `1ce98` `1cfde` `1fafc` `201bc` `4d0cc`; pc7(이전 빈 목록) := `1eb98` `1f756` `1fa68` `ea626` `1ef4c` `21d9e` `1ce98` `1cfde` `1fafc` `201bc` `4d0cc`. `EXIT_STOPS`에 C8 PC가 있는 spec은 이 여섯뿐이다(전수 검색).
  - pc3: 계산 점프 대상 검사(`SLOT84`·`LIST_21622`·표 `2031c`)가 C3/C4 routing만 허용 → C8(`21e6a`, `21e3a`)도 허용. C3 run은 C3 시작이 아닌 대상에서 멈추므로 fixture는 같다.
  - pc4 / pc5: `LIST_21AEE` / `LIST_21B26` 대상 검사가 C8을 허용하고, `JUMP_ROUTED` 일치 검사에서 C8 `21e3a`를 뺀다(그 run에서 `21e3a`는 `ROUTED_LATER`처럼 선언 정지로 남음). 오류 fixture `21c72-a1-listed-21e3a` / `21f7c-a1-listed-21e3a`는 위 시험과 같은 방식(A6 := 0, 실패 PC `21e3a`, `unsupported animation machine write device`).
  - pc6 `1ec1e-then-1fa68`(A7 홀수, `program bus requires even WORD/LONG address`, 실패 PC `1fa68`)·`1dad8-then-ea626`(A5 := 0, `unsupported animation machine write device`, 실패 PC `ea626`); pc7 `1f2fc-then-1fa68`(A7 홀수, 실패 PC `1fa68`)·`1f596-then-1eb98` `1f71a-then-1eb98`(A7 홀수, 실패 PC `1eb98` → `1ebbe`).
  - V1 회귀는 모두 C7 기록과 같은 fixture 수로 통과했다(아래 "검증 수치").
- [F] **scene update 시험 `engine/tests/animation_machine_scene_update_test.cpp`** `path_policy`: 경로 opcode `7ffc` / `7ffe`(대상 `19e8a + op` = `21e86` / `21e88`)은 이제 C8 block `21e84`의 operand(내부 PC)라 `unsupported animation player c8 PC`가 된다. 이전 기대값(`unsupported animation machine PC`, "executor 밖")의 뜻을 지키도록 opcode를 `7fbe` / `7fc0`(대상 `21e48` = routing 밖 목록 handler / `21e4a`)으로 바꿨다(주석에 이전 값과 이유).
- [F] **scene update 검증기 `tools/verify_animation_machine_scene_update.py`** `GUARD_ERRORS['guard-path-index-7ffe-far']`: 고정된 native 관측의 guard(`7ffe` → `21e88`)라 opcode를 바꿀 수 없다. 기대 오류를 `UNSUPPORTED_MACHINE` → `'unsupported animation player c8 PC'`로 바꿨다(같은 줄 주석에 이전 값; 줄 수를 바꾸지 않아 stage_event 검증기 `scan_old_expectations`의 줄 번호 예외(718, 732)에 영향 없음). 관측기 `observe_animation_machine_scene_update.py`의 claim 문장("7ffe → 21e88 … stop at the first non-executable PC")은 그대로 참이고, 관측기는 `NATIVE_TOOL_SHA`로 pin되어 있어 고치지 않았다. [U] 이 검증기는 작업자가 돌리지 않았다(장시간 검증기는 메인 runner). C++ 쪽 동작은 scene update 시험의 같은 경로(`19e64` opcode 경로)로 확인했다.
- [F] 바뀌지 않음(확인): C2·C3 시험, objects u13 시험(`ea60c..ea626` 범위 끝 = C8 `ea626` 시작; `make test` 통과), n04 / n34 시험의 `4d1d8` `21e70`(레지스터 값). 저장소 tools·시험에서 C8 범위 안 PC를 쓰는 다른 곳은 위 항목과 앞 단위 생성기·spec의 stop 목록뿐이다(전수 검색, 5·6자리 16진 literal). 다른 단위 소스의 주석은 고치지 않았다(다른 검증기가 그 소스 SHA를 pin할 수 있음).
- [I] native 사슬이 이 단위의 PC를 첫 routing 밖 PC로 멈추던 V1 spec·검증기는 더 진행한다(정지는 routing에서 계산된다). pc2~pc7은 C8 PC를 선언 정지로 두어 fixture 집합이 같다(V1 회귀 수는 아래 기록). 나머지는 메인 runner의 회귀·legacy 단계가 확인한다.

## 결정

1. **범위와 시작(scope correction): 재측정 98 block에 `1fcd4`를 더해 99 block(계획 목록과 같음), 18 범위. 숨은 직선 block 추가 없음.**
   - [F] 재측정(98) = 계획 − {`1fcd4`}. `1fcd4`는 C6 `1dbca`가 `MOVE.L #1fcd4,(A6)`로 쓰는 callback 값이고(쓰기만, IO 미실행), C8 block `1fcce`(`MOVE.W #8,90(A6)`)의 직선 연속이다. 범위 밖의 쓰기 전용 값(`1f3e0` `1f3e8`, C6 `1e918`)은 routing 밖 선언 정지로 둘 수 있지만, `1fcd4`는 C8 범위 안이라 시작이 아니면 그 callback으로 들어오는 dispatch가 C8 내부 PC 오류가 된다. 그래서 시작으로 두었다(block `1fcce`가 둘로 나뉨; 범위·byte·명령 수는 같다). [F] IO에서 `1fcce` → `1fcd4`는 같은 TB로 실행된다.
   - [F] **숨은 직선 연속 검사**: C7 routing과 C8 가상 routing 각각으로 C·E run 18개를 정확한 bitmap으로 다시 관측했다(`reobs_c8/obs_c7`, `reobs_c8/obs_c8a`, native 기록은 18 run 모두 원래와 같음). 새로 보인 PC 0개, C8 routing 관측의 예측 첫 정지는 없고 C / E 실행 PC가 0으로 남는다. 예측 173,966은 계획 표와 같다.
2. **`JMP (A1)` `21d9e` / `21e76`: A1이 ROM 목록 `21b0a` / `21b3c`의 handler면 그 PC로(routing 밖 `21e48`은 선언 정지), 그 밖은 checked jump-target 오류.** C3 `21620`·C4 `21c72`·C5 `21f7c`와 같다. 목록 비교는 LONG 전체.
3. **RTS를 넘는 C.** 소비자 5개는 known C를 읽거나 checked 오류. `4d0ea` Set(자기 block). 통과 block과 자료 C는 없다. 읽는 쪽이 없는 RTS의 C(`1cfee` `1d064` `1d084` `4d206` `ea626`)는 Unknown으로 둔다. Z가 경계를 넘는 곳은 없다.
4. **MOVEM·ASR.L.** `MOVEM.L D0-D3/A1,2e(A6)`는 낮은 주소부터 레지스터 순서의 LONG 다섯 개. `ASR.L Dn`의 count는 Dn mod 64, 32 이상은 부호만 남는다. 둘 다 flag를 읽는 쪽이 없다.
5. **뒤 단위 정지와 앞 단위 spec.** C8 block이 닿는 미룬 입구 8곳과 목록 handler `21e48`, C1~C7의 남은 정지 17곳을 V1 `first_unrouted`와 실제 ROM 차분의 선언 정지로 둔다. pc2~pc7의 `EXIT_STOPS` 가운데 C8이 routing한 PC는 `ROUTED_LATER`로 허용하고 선언 정지로 그대로 둔다. pc3~pc5의 목록 대상 검사는 C8 routing을 허용한다(대상은 선언 정지로 남음).
6. **실행부 파일·오류 문자열.** 위 "공통 규칙". 오류 문자열 3개.
7. **다음.** C8 연결로 IO 173,966(+89, 모든 native 비교 frame)을 메인 runner가 확인한다. 이 관측 집합에서 C·E는 끝난다(아래 "C 완료 판정"). 나머지 C9~C13(미룬 입구 22곳의 subtree, 쓰기만 하는 `1f3e0` `1f3e8` `1e918`, 미실행 자식 `23c56`·표 자식, 목록 handler `21e48`, 계산 점프 표의 미실행 칸)은 입력을 늘린 관측으로 다시 잰 뒤 정한다(계획 결정 3).

## C 완료 판정(이 관측 집합)

계획 §1의 "C 완료(이 관측 집합)" 조건 1·2에 대한 작업자 측정이다. 조건 2(IO 비교 재실행: 불일치 0, 예상 밖 C++ 오류 0, 두 번 같음)와 조건 3의 장시간 단계는 메인 runner가 IO run으로 확정한다.

- [F] **재측정한 C / E 실행 PC(routing 밖)**: **C 0 / E 0**(D 0). 최종 routing `2622b7a2…`에서 `MS5_REOBS=…/c1/reobs dleft.py`(계획의 보정 관측)와 `MS5_REOBS=…/reobs_c8/obs_c8a dleft.py`(C8 정확 bitmap 재관측) 둘 다 `executed unrouted PCs by area {}`이다(`trial_logs/dleft_after.log` `dleft_after_obs_c8a.log`).
- [F] **예측 첫 정지(영역별)**: C 0, E 0, D 0 — 어느 run에도 예측 첫 정지가 없다(`work/firststops_after.txt` 빈 목록). 예측 일치 frame 173,966 = IO native 비교 frame 전체(계획 §3.1의 173,966). 남은 routing 밖 실행 PC는 덮는 원자(`hidden2.json`의 C++ 단일 PC 실행부가 덮는 closure, 계획 §2)의 PC와 P0 기준선 PC뿐이며 C·E·D 분류 밖이다(`obs_c8a` boot-demo-0 26개: `16eaa` `16ed6` … `8c1c` … `e90d0`).
- [F] **실행되었지만 routing되지 않은 C PC**: **없다**.
- [I] 계획 §7의 [U] `46efe` `46f0c`(원자 `46ef4`/`46f08`, D 주소)는 이 측정에서도 덮는 원자 PC로 분류된다(`obs_c8a` 목록에 `46ef6`이 있음). IO 비교에서 D 첫 정지로 나오는지는 메인 IO run이 확인한다.
- [I] 이 판정은 "현재 IO 관측 집합(run 296개, C·E run 18개)"에 대한 것이다. 다른 입력·스테이지로만 실행되는 플레이어 코드(C9~C13, 계획 §4.3)는 남는다. GOAL 전체 완료가 아니다.

## 미확인

- [U] node field·전역 값의 의미(BYTE `15` `61` `6e` `88` `9c` `9d` `9e` `a7` `a8` `a9` `aa` `5e` `81` `82`, WORD `1e` `78` `7a` `90`, LONG `36` `3a` `56` `64`, A5 기록 `5cba`/`5ce6`(BYTE `22` `28`, WORD `18`), WORD `-7ff2(A5)`, BYTE `5683(A5)`, BYTE `5e50(A5)`, 이동 기록 `1cf1e`/`1cf3e`, 표 `1b2ae` `1b328` `1b716` `1b74a` `1b9c6`). 이름(이동 helper, 기록 helper, 칸 상태)은 동작에서 붙인 [I]이다.
- [U] IO 관측에서 TB 시작으로 실행되지 않은 이 단위의 block 12개(`1d01c` `1d058` `1ef68` `1f42e` `1f438` `1f440` `1f480` `1f764` `1fcd4` `21e76` `4d0f6` `4d1bc`; `1d01c` `1fcd4`는 TB 안에서 실행)는 closure로 들어왔다(V1 선언 상태·재설치 world·실제 ROM 차분으로만 확인).
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC). 예측은 첫 정지 없음이다.
- [U] 재설치 world와 IO pack 자연 node 상태의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C7와 같음). frame 516 뒤의 자연 node 재실행이 `1fd50`(C11)으로 가는 것은 IO 기록과 다르다([I] frame-start 재실행의 한계).
- [U] 결정 1의 정확 bitmap 재관측은 C·E run 18개만 했다(계획 §7과 같은 범위).
- [U] Unicorn 2.1.4 native oracle abort(boot-demo-0 frame 532 pack 자연 node 재실행에서 process abort; C6·C7에서도 관측)의 원인.
- [U] scene update 검증기의 새 guard 기대값은 작업자가 그 검증기를 돌려 확인하지 않았다(메인 runner).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_player_c8.cpp`(case label 99 = `starts_C8_final.txt`와 집합 일치; 공용 함수 `pc8_get` `pc8_put` `pc8_bit`(memory BYTE bit; 0 시험, 1 세움, 2 지움, 3 바꿈) `pc8_field_bit` `pc8_input_bit` `pc8_byte_zero` `pc8_mask_c` `pc8_carry` `pc8_field_call` `pc8_install` `pc8_slot` `pc8_asr` `pc8_list_jump`, 목록 `PC8_LIST_21B0A` `PC8_LIST_21B3C`), `engine/tests/animation_machine_player_c8_test.cpp`(생성 구역 + 수작성 규칙), `tools/generate_animation_machine_player_c8_test_table.py`(생성기; C7 생성기 꼴, 계산 점프 착지 검사 `JUMP_ALLOWED` = 두 목록, V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀(`rec`/`regrec`: rec + 20 = A0 / A4 = `10ea00`); native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 45초), `tools/unit_fixture_specs/pc8.py`(V1 spec; C7 spec의 공용 부분 그대로(scratch `work/mkpc8.py`가 조립), 단위 부분 교체, `EXIT_STOPS`(25), `SET_SET` `CONSUMERS` `BUNDLED`(`21e5a`), `LIST_JUMPS`(trace가 목록 밖 착지를 버림), family `reinstall`). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `starts_C8_final.txt`(SHA256 `646381e98a3bd723e615a94f8e608059b34b2f869ecad4549a16ffd261f431d1`) = 재측정 `r8_C8.txt`(98) + `1fcd4`(결정 1) = 계획 `starts_C8.txt`.

- **`1ce98..1cea8`(2)**: `1ce98 1cea2`
- **`1cfde..1d086`(20)**: `1cfde 1cfe8 1cfec 1cfee 1cff8 1cffa 1d018 1d01c 1d026 1d02c 1d034 1d03a 1d04e 1d058 1d064 1d066 1d070 1d076 1d080 1d084`
- **`1eb98..1eba0`(1)**: `1eb98`
- **`1ef4c..1ef6c`(4)**: `1ef4c 1ef56 1ef5e 1ef68`
- **`1f3d8..1f48a`(19)**: `1f3d8 1f3ec 1f3f0 1f418 1f41c 1f426 1f42e 1f438 1f440 1f444 1f44c 1f454 1f45c 1f466 1f46c 1f476 1f47c 1f480 1f486`
- **`1f756..1f76a`(2)**: `1f756 1f764`
- **`1fa68..1fb32`(13)**: `1fa68 1fa70 1fa74 1fa7c 1fa80 1fafc 1fb02 1fb06 1fb0a 1fb0e 1fb18 1fb1e 1fb2e`
- **`1fcce..1fd3c`(8)**: `1fcce 1fcd4 1fd12 1fd18 1fd28 1fd2e 1fd34 1fd38`
- **`201bc..201d0`(3)**: `201bc 201c6 201cc`
- **`21d9e..21ea0`(14)**: `21d9e 21e3a 21e52 21e5e 21e62 21e6a 21e72 21e76 21e78 21e7c 21e84 21e8c 21e94 21e9c`
- **`4d0cc..4d208`(12)**: `4d0cc 4d0d4 4d0e0 4d0e6 4d0ea 4d0f6 4d1ac 4d1b4 4d1bc 4d1c0 4d1c6 4d206`
- **`ea626..ea62e`(1)**: `ea626`

## 검증 수치

작업자 최종 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j3 all test`(최종 실행부·시험): 종료 0, 경고 0, Python 310 OK(`trial_logs/make_final.log`). C8 시험 줄: `animation machine player pc8: 683 fixtures (438 single-block, 162 path, 24 producer chain, 10 declared C, 49 checked error (14 with a later failing PC), 37 kept C), 99 blocks, 2847 calls, 158942 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 실제 사슬 두 C 값 4개(`1fa68`→`1fa70`, `1fd2e`→`1fd34`, `4d0e0`→`4d0e6`, `21e6a`→`21e72`; `1f476`→`1f47c`(`49fc6`)은 `49fc6`이 bank 장치에 써서 native run이 버려져 선언 C 행만), 출구 중 stop이 아닌 것 0, `21d9e` / `21e76` 행이 목록 handler 다섯(`21602` `21c22` `21d60` `21e3a` `21e48`)에 모두 멈춤. 생성기를 다시 돌려 시험 파일이 바이트 단위로 같음을 확인했다(`trial_logs/gen_c8_repro.log`). 다른 player 시험 줄의 fixture 수는 C7 기록과 같다(pc4 1,372, pc5 1,184, pc6 1,248, pc7 1,270).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, `work/ubsan.sh`, C8·C7·C6·C5·C4·scene update 시험): 빌드 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_build.log` `ubsan_player_c8.log` … `ubsan_scene_update.log`).
- [F] V1 pc8(작업자, `--workers 3`, scratch `work/v1_pc8_try1`): fixture 986개(block 480, chain 10, node 18, natural 10, reinstall 9, callee 62, error 376, failpc 11, negative 10) failed 0, 방문 시작 99/99, 빠진 후속 없음, 도달 못한 분기 결과 없음, carry oracle Unknown/Clear/Set = 580/12/8(`trial_logs/v1_pc8_try1.log`). 첫 시도에서 통과했다.
- [F] V1 회귀(작업자, `work/v1_regs.sh`): pc1 1,264/1,264, pc2 1,743/1,743, pc3 1,831/1,831, pc4 1,873/1,873, pc5 1,755/1,755, pc6 1,856/1,856, pc7 2,077/2,077, se1 2,102/2,102, fr1 1,631/1,631(모두 failed 0; 수는 C7 기록과 같음, `work/v1_regs.txt`). 첫 실행에서 pc3~pc5는 spec의 계산 점프 대상 검사(`21e6a` / `21e3a`가 C8 routing)로 build 단계에서 멈췄고, "영향받는" 절의 수정 뒤 통과했다. 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·op, WORD/BYTE → LONG, 복귀 PC·호출 대상, carry tag, mask, 상수·설치 값, `pc8_*` helper 인자) + 손으로 고른 helper·block 변이(`ASR.L` count mask·채움·부호·32 경계, `JMP (A1)` 목록·비교 폭·guard, `ADD.L`/`SUB.L` 방향·순서·폭, `MOVE.W #k`가 남기는 상위 bit, `MOVEM.L` 순서·D2/D3·A1 폭, `SWAP`, BYTE `28` mask `81`·`NOT.B`·AND/OR, WORD 비교 `4d0d4`의 폭·부호 확장, `BGT`/`BLT` 부호, `BMI`의 bit, push/pop 폭 등) + dispatcher carry 목록 5개·추가·범위 2개를 적용해 만든 것, 409개; `--workers 3`): 1회째 `killed 397 of 409`(`trial_logs/mut_first.log.keep`). 생존 12개 중 1개는 시험 빈틈이었고 규칙 `rules_h`로 메웠다(`mut_gaps.log`: `killed 1 of 12`): `4d0cc-size`(`TST.B 22(A4)`를 WORD로 읽음: BYTE 22 = 0, BYTE 23 = 1, 같은 WORD, `484b4` Set이면 원본은 `4d0f6`, 변이는 `4d0ea`). 남은 11개는 동치다(`mut/equivalents.txt`, 사례별 이유: `AND.W #c` / `#50` 뒤 WORD와 BYTE 시험이 같음 2, `MOVEQ #0`이 덮는 D0/D1 상위 bit 5, BYTE 쓰기가 가리는 mask 1, `pc8_bit`의 상수 bit 0..7 1, `am_write`의 자체 mask 1, `ASR.L`의 채움 경계 bit가 원래 부호 bit 1). 규칙을 더한 뒤 전체 2회째 `killed 398 of 409`(`trial_logs/mut_second.log`), 남은 11개가 동치 목록과 같다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`, 메인 runner용), `real_pc8.py`(C7 harness에 C8 world(`pc8_world`)·소비자·선언 정지·목록 handler 정지; C8 `JMP (A1)`의 착지를 trace 전체에서 대조하는 분류 `JUMPTGT8` 추가; `native_safe` 기본 유지)): 작업자 300건 seed 1 `mismatches 0`(`covered starts 99 of 99`; 문서화된 분류 C3 jump-target 42건(무작위 slot-84 LONG의 `201a6`), C8 jump-target 2건(선언 Set으로 들어간 `21e72` → `21e76`의 무작위 A1); 정지하지 않은 native 39건 건너뜀; native oracle abort 0, `trial_logs/real_n300_s1.log`). 앞선 50건 seed 11 시험도 `mismatches 0`(`trial_logs/real_t50.log`).
- [F] `dleft.py`: 이전(routing `1f4599a2…`) C 93 / E 0, 예측 173,877, 첫 정지 C 1(`trial_logs/dleft_before.log`; 재관측 `obs_c7`로도 같음). 이후(routing `2622b7a2…`) C **0** / E **0** / D 0, 예측 **173,966**, 첫 정지 없음(`dleft_after.log`; 재관측 `obs_c8a`로도 같음).
- [F] 기존 검증기 새 기대값은 scratch에서 확인했다: C4~C7·scene update 시험은 `make test`로, scene update 검증기의 `7ffe` guard는 scene update 시험의 경로 opcode 행을 `7ffe` / `7ffc` → `unsupported animation player c8 PC`로 바꾼 scratch 사본을 빌드해 통과함을 확인했다(`work/probe_scene_update/`, `trial_logs/probe_scene_update_7ffe.log`; 검증기 자체는 돌리지 않음). CPP_PINS는 작업 트리와 scratch clone root(`roots/probe`, `work/mkroot.py`: 작업 트리 clone + 변경 파일 복사 + 공유 자료 symlink; 확인 뒤 symlink를 따라가지 않고 삭제)에서 파일 SHA와 같음을 확인했다(4 / 9 pin, 불일치 0, `trial_logs/pincheck_tree.log` `pincheck_root.log`).
