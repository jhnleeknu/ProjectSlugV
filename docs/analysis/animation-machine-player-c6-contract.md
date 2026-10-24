# 영역 C 단위 C6(E helper `b0c`/`e6496`, 슬롯 상태 `4eb58` → `4ed3c` → `4edc0`/`4ee04`, 플레이어 본체 꼬리 `1d398` 형식 사슬·`1d90a`/`1d510`·`1dcd0` → `1e824` → `1e89e`, 입력 분기 `1eba0`/`1ebf6`, 212 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §4.2의 C6 행과 아래 "C6 상세 명세"(계획 §8과 같은 꼴, 이 계약에서 새로 씀)를 기준으로 삼고, 구조·공통 규칙은 C5 계약(`animation-machine-player-c5-contract.md`)·C4 계약·C3 계약·C2 계약·C1 계약을 따르며 다른 점만 적는다. 단위 이름은 C6, 파일 접두어는 `player_c6`(C++) / `pc6`(V1 spec)다(계획 메인 결정 7). 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기와 장치 쓰기는 없다(bank 창·장치는 callee가 읽고 쓴다). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `ad47a36`(branch `claude/c6-core`; C1 `ff2e284`, E1 `6308f75`·`1c17a3e`, C2 `5d686ac`, C3 `d31d04e`, C4 `749643e`, C5 `ad47a36` routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `beff46d62a342129120d107dba0848ca937dddf9301c16902d19a521d8da2f21`, `animation_machine_internal.h` `0dc447022c1b885d2fb7e112329823cb8373ee6369949b6811ae678a635939bd`.
- [F] 관측 입력: native IO 관측 `artifacts/animation_machine_io_native`(읽기 전용; state pack `states/P1/094.pack.gz` `106.pack.gz`, `boot-title-start/boot.pack.gz`, `boot-demo-0/boot.pack.gz`)와 계획의 보정 관측 `ms5-scratch/c1/reobs/`(읽기만), 그리고 이 단위의 정확 bitmap 재관측 두 벌(scratch `reobs_c6/obs_c5`, `reobs_c6/obs_c6a`; 결정 1).
- [F] 시작 목록: 계획 scratch `ms5-scratch/c6/starts_C6.txt`(214개, SHA256 `186ab793fac8d5dbd57d963859a4213a1e6dfe718016c6bebd67ccc529116437`, 계획 §6 표의 `186ab793fac8d5db`와 같음)에서 C4가 결정 1로 가져간 `4e57e` `4e8e6`을 뺀 **`ms5-scratch/c6/starts_C6_final.txt`(212개, SHA256 `7b910e5be798cbb680f3e0c004e787098cba436bdf85f584eaa2540db74963cb`)**. 재측정 목록 `remeasure/r6_C6.txt`와 같다. 실행부의 `case` label 212개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(작업자 확인).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/c6/`
  - `remeasure/`(재측정: `remeasure3.py` → `r6.json` `r6_C6.txt`), `work/udetail6.py` `work/udetail_C6_r6.txt` `work/C6_r6.dis.txt`(범위·출구·역어셈블, `>` = block 시작, `*` = IO 실행 TB 시작), `work/c6ranges_r6.txt`(범위), `work/intargets.py`(범위 안으로 들어오는 직접 분기), `work/callers_c6.py` `work/callers_c6_all.out`(호출자), `work/c6io.py` `work/c6io_obs_c5.txt`(IO run·frame), `work/natsig6.py` `work/natsig6.out`(IO 자연 node 선택), `work/newvis.py`(재관측 사이 새로 보인 PC), `work/predict_runs.py` `work/predict_runs.txt`(run별 예측), `work/firststops.py`(예측 첫 정지), `work/hexsearch6.py` `work/hexsearch6.out`(기존 파일의 C6 범위 상수 검색), `work/probe/probe.cpp`(C++ 실행 탐침), `work/probe_input.py` `work/probe_input2.py`(input 검증기 base row 탐침), `work/mw_oor.py`(motion-walk 계산 PC 검사), `work/pincheck.py`(CPP_PINS 대조), `work/v1_regs.sh`(V1 회귀), `reobs_c6/obs_c5` `reobs_c6/obs_c6a`(정확 bitmap 재관측), `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **재측정 전**(`MS5_REOBS=…/c1/reobs dleft.py`, routing `beff46d6…` = C1+E1+C2+C3+C4+C5): 실행된 routing 밖 PC C **261** / E **12** / D 0, 예측 일치 frame **172,297**, 첫 정지 영역 C 10(`dleft_before.log`). C5 계약의 C5 뒤 값과 같다.
- [F] **closure 재측정(C1~C5 routing 상태)**: C3~C5 작업자 방식 그대로 계획 spec `plan/plan_final.json`과 계획 당시 key(`remeasure/keys_old.json`)로 현재 routing에서 `cplan3`을 돌렸다(`remeasure/remeasure3.py`, `trial_logs/remeasure_r6.log`). **C6 = 212 block, 453 명령, 1,904 byte, 26 범위**(시작 목록 SHA `7b910e5be798cbb6…`), 예측 173,820(+1,523), 남은 C 194 / E 0, 첫 정지 C 1.
  - [F] 계획 목록(214)과의 차이는 `4e57e` `4e8e6` 둘뿐이다. 둘 다 C4 결정 1이 가져갔다(C4 `4e57e..4e58a`, `4e8e6..4e8f0`). C3 결정 10의 `1cde0` 계열과 `202a0`은 계획 C6 목록에 없었다.
- [F] **범위 밖에서 범위 안으로 들어오는 직접 분기**(`work/intargets.py`): 진짜 명령은 없다. 찾은 셋(`4edf0 → 4ee48`, `e1450 → e64c1`, `e1474 → e64e5`)은 `4edec JSR e6556.l`의 operand(`6556`)를 명령으로 읽은 것과 홀수 대상(자료)이다.
- [F] **정확 bitmap 재관측**(결정 1; scratch `tools/reobs.py`, 관측기 수정 없음; C·E run 18개, `--workers 2/3`):
  - C5 routing(`beff46d6…`) 그대로: `reobs_c6/obs_c5`(`observation.json` compared_sha256 `b40b583a5ce3b989…`), `reobs_check.py`: 18 run 모두 native 기록이 원래와 같다(`ALL NATIVE RECORDS EQUAL … True`). `dleft.py` → C 261 / E 12, 예측 **172,297**, 첫 정지 C 10(P1 94 계열 8 run frame 457·title frame 577의 `21564`, demo frame 381의 `1d398` …). C5 계약의 `obs_c5a`와 같다.
  - C6 범위를 가상 routing(`EXTRA_ROUTED`)에 넣은 bitmap: `reobs_c6/obs_c6a`(compared_sha256 `b4b556501ae25511…`, native 기록 18 run 모두 같음). `dleft.py` → C **194** / E **0**, 예측 **173,820**, 첫 정지 C 1: boot-demo-0 frame **431**의 C7 `1f2a4` `1f2ac` `1f2d8` …(demo 전용 코드). 나머지 17 run은 600 frame 끝(또는 guard)까지 정지가 없다.
  - [F] 두 관측 사이에 새로 보인 routing 밖 PC(TB 안에 가려진 직선 연속)는 **없다**(`work/newvis.py obs_c5 obs_c6a`: 18 run 모두 0). C6 연결로 사라진 실행 PC는 C6 범위의 PC뿐이다. 그래서 C3 결정 10·C4 결정 1과 같은 숨은 직선 block 추가는 필요 없다(C5 결정 1과 같은 결과).
- [F] **측정 결과**(`dleft.py`, 최종 routing `bd037aff…`): `MS5_REOBS=…/c1/reobs` → C 261 → **194**(−67), E 12 → **0**, 예측 일치 frame **173,820**(+1,523), 첫 정지 C 1(`dleft_after.log`). `MS5_REOBS=…/reobs_c6/obs_c6a`로도 같다(`dleft_after_obs_c6a.log`). [F] 계획 표(남은 C 196)와의 차이(−2)는 앞 단위의 범위 보정(C3 결정 10·C4 결정 1)이다. E는 계획 결정 6의 E helper `b0c`·`e6496`(실행 PC 12개: `b0c` `b26` `b2a` `b3c` `b56` `e6496` `e64a2` `e64ae` `e64b4` `e64b8` `e64c0` `e64cc`)이 C6에 들어와 0이 된다.
- [F] run별 예측(`work/predict_runs.txt`): P1 94 95 100 101 106 107 110 111이 frame 457 → 600(각 +143), boot-title-start가 577 → 906(guard, +329), boot-demo-0이 381 → 431(+50). 합 8 × 143 + 329 + 50 = **1,523**.

## C6 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **계획 214 block, 457 명령, 1,926 byte, 28 범위**(시작 목록 SHA256 `186ab793…`, 범위 이어 붙인 SHA256 `5d255cbcc07a682b96aa7eb023032d6f5b2f597d0c5922548e21cb098bfa14f4`) − C4 결정 1의 `4e57e..4e58a`(12 byte) `4e8e6..4e8f0`(10 byte) = **212 block, 453 명령, 1,904 byte, 26 범위**(시작 목록 SHA256 `7b910e5be798cbb680f3e0c004e787098cba436bdf85f584eaa2540db74963cb`, 범위 이어 붙인 SHA256 `1e5746c19ad9026943c7a3944a73d6e15fae9d9badc564ed444d2e6c32179f45`). 아래 표는 구현 범위다.

| 범위(CPU = 파일 오프셋) | byte | SHA256(앞 16자) | 시작 | 내용 [I] |
| --- | --- | --- | --- | --- |
| `b0c..b58` | 76 | `e333dd3dd3f44f0e` | 6 | E helper `b0c`(D0.W 플레이어, D1.B 요청): bit BYTE `10f007` 지우기·`10f006` 검사(bit D0 mod 8), BYTE 표 `b58 + 4 × D1.B + BYTE 10fdb6+D0.W`(ADD.B, 자리올림 버림), BYTE `10fdb6+D0.W` := D1.B, `10f007` bit 다시 세움 |
| `1d398..1d3e0` | 72 | `ccdc9e53aa3e69fd` | 9 | C2 `1d390`의 직선 연속: D7.W 형식 5/6/7/8/9/a/b/3/e → 각 처리(`1ddfc` `1ddc8` `1dce2` `1dd36` `1dd88` `1dda8` `1dc1a` `1daba`), 나머지 `1d3e0`(미룬 입구) |
| `1d510..1d582` | 114 | `097444b3e1da626c` | 13 | `1d510`: D1.W < 14 → `481b2`·`1aa3a`, LONG 표 `1d468 + 4 × D1.W` → 자식 `2986`·`49214`, C를 돌려줌 |
| `1d63a..1d664` | 42 | `777e4292ab247efb` | 4 | `49c38`의 C → WORD `42 − 53a2(A5)` := `ae`, `49c20`(입력 callback `1d664` 등록) |
| `1d698..1d6c2` | 42 | `23aa0bfa5bbcf533` | 4 | 같은 꼴, WORD `46 − 53a6(A5)`, callback `1d6c2` |
| `1d90a..1d940` | 54 | `2b468301e0b9c697` | 8 | `48210` → D1.W, BYTE 표 `1d8ce + D1.W`, `4c0ea`, `1d510`의 C |
| `1daba..1db0a` | 80 | `368b4712ea179e70` | 10 | 형식 e: WORD `78` ≠ 0이면 15 frame 상태 `1dace`(`49bca`, `ea626`, WORD `b0` 세기), 아니면 `1daee`(`1d63a`, `43e08`, `1d90a`로) |
| `1dbc6..1dbd8` | 18 | `1dfac551c5df4ae5` | 2 | `1d1d0`, BYTE `a7` bit 7, callback `1fcd4`(쓰기만) |
| `1dc1a..1dc84` | 106 | `59404cf9c1594e0d` | 14 | 형식 b/3: 상태 `1dc20`(`49bca` `ea626` `4836e`의 C → `43e34`, BYTE `81`/`82`, WORD `68`/`1e` := `e0ec`, `1cb08`(표 `1b1b0`)의 C, `1cab6`, 상태 `1dc70`, `1d182` `4bfc0` `ce02` → interpreter stub `1dc84`) |
| `1dcd0..1ddd0` | 256 | `4a6a05f8bac7b58f` | 31 | `1aa3a` D0 bit 6 → `1e824`; 형식 7/8(15 frame 상태 `1dcf6`/`1dd4a`, `1d63a`, `43e08`), 형식 9/a(`1d698`, `43e08`), `1dbd8` |
| `1e60a..1e638` | 46 | `d64b9e666b20a609` | 6 | D0 bit 0/1 → D1.W 280/80/180, `SUB.W 7c` / `ADDQ.W #3` / `ASR.W #2` / `ADD.W 7c` |
| `1e65c..1e67a` | 30 | `fa5d9f5de38c45b2` | 3 | WORD `42 − 4a − 53a2(A5) + 53aa(A5)` 부호 → BYTE `9c` := 9 / a |
| `1e824..1e8de` | 186 | `fda02ecbd58dcc0a` | 14 | `1d1d0`, 자식 `1e67a`(`28ae`), 칸 `84` 초기화, `43e08`, LONG `36`/`3a`, `1cb38`(`1bcce`), 상태 `1e89e`(`49bca` `1e60a` `43ea4` `ce02` `49fc6` `1e65c`, WORD `42` ≤ `ae` signed, callback `1e918` 쓰기만, `201a2`로) |
| `1eba0..1ec74` | 212 | `00fcabf5928a1ad2` | 23 | BYTE `9d` > 0(signed), BYTE `a7` bit 5, `1cb08`(표 `1b1ca`)의 C, `1cab6`, field 초기화·칸 `84`, 상태 `1ebf6`(`1cd98` 입력 D0 bit 5/1/7/c/50 분기: `1fae8` `1f7a4` `1fa68` `1fa3c` `1f2a4` `1f1d8` `1eeea` `1ed78`, `4bfc0` `ce02` `49fc6`의 C, `201a2`로) |
| `1efa4..1efb0` | 12 | `b361e35ea387cecf` | 2 | C4 `1ef9a`의 직선 연속: WORD `88` → `1ed78` / `1eba0` |
| `206cc..206d2` | 6 | `2a0dc1f76b0ff065` | 1 | C3 `206c6`의 직선 연속: BSET #0,`a7`(C3 `206d2`로) |
| `21564..2156a` | 6 | `2738adf81304c5fb` | 1 | C5 `214d6`/`2155a` 빌림 쪽, interpreter stub `210b4`의 Set 쪽: `JMP 2a00`(객체 제거) |
| `21662..21664` | 2 | `1ceeabf0c6a5a30b` | 1 | C3 `2161c BCC`의 Clear 쪽: RTS |
| `481b2..481de` | 44 | `c8beafc5ca46f6b6` | 3 | D0.W & 1 → 기록 `5694/569c(A5)`의 BYTE·WORD를 D1~D6에, `JMP 4d50e` |
| `4838c..48392` | 6 | `56ecae3be233dc03` | 1 | C3 `48384`의 Set 쪽: `ORI.B #1,CCR; RTS` |
| `4e572..4e57a` | 8 | `b1694dda2cc6ba7f` | 1 | C4 `4e564`의 WORD `76` = 0 쪽: `ADDI.W #20,D0; BRA 4e57e` |
| `4e5b0..4e5c2` | 18 | `c55a09eff13bf794` | 1 | BYTE 표 `4e4d2 + (D0.W & ff)` → `BCLR.B D0,5d1e(A5)` |
| `4e8f8..4e8fc` | 4 | `8a0d789be2f6e277` | 1 | C1 `4e8f0`의 BYTE `5d1f` ≠ 0 쪽: `JSR 4f22c`(C1 `4e8fc`로 돌아감) |
| `4eb58..4eb6a` | 18 | `b3384eb2f26efc34` | 2 | C1 `4e900 BEQ`: `4e5b0`, BYTE `10fd8a` = 0 → `4ed3c`, 아니면 `4eb6a`(미룬 입구) |
| `4ed3c..4ee7a` | 318 | `5a602ac4a31dcc0d` | 35 | 슬롯 `4ed3c`(`b0c` D1 = 3, `4e4da`, `e6496`(LONG `10de14`/`10de1c`) 순위 → 자식 `e695a`(`28ae`), 상태 `4edc0`(BYTE `62`, `2a0a`, `e6556`), 상태 `4ee04`(BYTE `7db6(A5)+WORD 76` 0/1 → `4e6f2`, `7d82`, `4a974`의 Z, WORD `96` 세기, `7004(A5)` bit, `b0c` D1 = 0, `5d1f` → `9a`, `4e564`) |
| `e6496..e6516` | 128 | `6ebb4fe0bdad55d2` | 16 | E helper `e6496`: LONG (A0)를 LONG 표 `10f02e`(10개, 간격 8)와 무부호 비교한 순위 D0/D1(없으면 −1), A0 = `10de14`/`10de1c`면 `5e13`/`5e12`와 LONG `5e1c`/`5e14(A5)`로 보정 |
| 합계 C6 | 1904 | 이어 붙인 바이트 `1e5746c1…` | **212** | 짝수 PC 952(내부 740) |

- [F] **진입(실행된 PC를 줄인 closure 진입, 재측정 `entries`)**: `21564` `b0c` `4e572` `4e5b0` `4e8f8` `4eb58` `1d398` `4838c` `206cc` `1eba0` `1efa4` `21662`.
- [F] **IO 실행**(`work/c6io_obs_c5.txt`; C5 routing 재관측): 실행된 C6 PC 79개(시작 77 + 묶인 둘째 Bcc `b26` `e64b4`), 실행 10,954회(계획 10,972), run 10개. 실행되지 않은 시작 135개.
- [F] **호출자**(ROM 전체 직접 분기 검색, `work/callers_c6_all.out`; 소속은 재측정 `r6.json`):
  - `b0c` ← C6 `4ed42` `4ee56`, C13(미실행) `4ebd0` `4ec5e` `4ec76`. `e6496` ← C6 `4ed64`, U02 `e50c4`(다음 `SUBQ.W`), 단위 밖 `e6a5c JSR e6496(PC)`.
  - `1d510` ← C6 `1d930`, C9 `1d70a`(다음 `BCS`) `1d8f6`(다음 `BCC`), C9 `1d50c BRA 1d514`. `1d63a` ← C6 `1daee` `1dd16` `1dd6a`, C9 `1d80a`. `1d698` ← C6 `1dd88` `1dda8`, C9 `1d812` `1db0a` `1db28`(다음 명령은 모두 C를 읽지 않음).
  - `1d90a` ← C6 `1db06`, C9 `1db24` `1db42`. `1dbc6` ← C6 `1d938`, C9 `1d70e` `1d8fe` `1d9ae` `1db9c`. `1dce2` ← C6 `1d3a8`, C9 `1d89a`. `1ddc8` ← C6, C9 `1da5c`.
  - `1e60a` ← C6 `1e8a8`, C10/C11 `1e946` `1e9a2` `1ea16`. `1e65c` ← C6 `1e8c4`, C10/C11 `1e954` `1e9b0` `1ea24` `1ea70`. `1eba0` ← C6 `1efac`, C11 `1eca0 BCC`. `1ebbe` ← C2 `1eee6 BRA`, C8 `1eb9c BRA`.
  - `21564` ← C5 `214da` `2155e`(BCS), interpreter stub `210b4`(Set), C11 `1fcbe`. `21662` ← C3 `2161c BCC`. `481b2` ← C6 `1d526`, C9 `1d982` `1d9e8`. `4eb58` ← C1 `4e900 BEQ`. `4ed3c` ← C6 `4eb66`, C13 `4eb6e` `4eba4` `4ebf0`.
  - 직선 연속으로만 들어오는 시작: `1d398`(C2 `1d390`), `1efa4`(C4 `1ef9a`), `206cc`(C3 `206c6`), `4838c`(C3 `48384`), `4e572`(C4 `4e564`), `4e8f8`(C1 `4e8f0`).
- [F] **설치 값**(`MOVE.L #v,(A6)`): 곧바로 들어감 `1dace`(`1dac2`) `1daee`(`1dae8`) `1dc20`(`1dc1a`) `1dc70`(`1dc6a`) `1dcf6`(`1dcea`) `1dd16`(`1dd10`) `1dd4a`(`1dd3e`) `1dd6a`(`1dd64`) `1e89e`(`1e892`) `1ebf6`(`1ebc2`) `4edc0`(`4edaa`) `4ee04`(`4edf2`). **쓰기만**: `1fcd4`(`1dbca`, C8), `1e918`(`1e8d4`, C10), `1ed78`(`1ec6a`, routing된 C2). 둘째 callback 칸 `84(A6)` := `21602`(`1e83e` `1ebc2`; C3 허용 목록 안).
- [F] **IO run의 node**(`work/natsig6.out`): P1 94 계열 frame 457에 플레이어 node `100cb8`의 C5 `214d6`이 빌림으로 `21564` → `JMP 2a00`(플레이어 객체 제거). frame 458에 슬롯 node `1009a8`의 C4 `4e94e`가 C1 `4e8f0`/`4e900`을 거쳐 `4eb58` → `4ed3c`(`b0c`, `e6496` 순위 음수 → `4edf2`) → 상태 `4ee04`, frame 459 이후 `4ee04`(WORD `96`을 1e에서 세어 내림). title은 frame 577/578/579/608/610에 같은 순서다. demo는 frame 381(C1 `1d1f4` → C2 `1d390` → `1d398` 형식 사슬 → `1daba`(WORD 78 = 0) → `1daee` → `1d63a` → `43e08` → `1d90a`), 407(C4 `1ef0e` → `1efa4`), 410/411(`1eba0` → 상태 `1ebf6`) [I: frame 381의 node는 그 frame에 생성되어 frame 시작 pack에 없다(`270e`), 그래서 재설치 world로 확인].

### 계산 점프와 표(결정 2)

- [F] **계산 점프는 없다.** 이 단위의 분기는 모두 직접 분기이고, `JMP`는 `21564 JMP 2a00.l` `481d8 JMP 4d50e.l`(고정 대상)뿐이다. `JSR (An)`/`JMP (An)`/`(PC,Dn)` 점프가 없어 FR4 방식의 칸 전사가 필요 없다.
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙):
  - BYTE 표 `b58 + sext(D7.W)`(`b2a` `b40`; ROM 16 byte `00 00 00 01 01 00 01 00 00 01 00 00 00 01 01 00`; 경로상 색인 = 4 × D1.B + BYTE `10fdb6+D0.W` 또는 4 + BYTE. D7.W는 최대 03ff로 부호 bit가 서지 않는다).
  - LONG 표 `1d468 + sext(4 × D1.W)`(`1d54c`; ROM 20 LONG, 0이 아닌 칸은 1 `2b7c6`, 4 `330a4`, 9 `3064a`, 11 `38b38`, 13 `3fd0e`; 경로상 D1.W < 14(`1d514`), 직접 진입은 D1.W 아무 값). 읽은 LONG은 `2986`에 넘기는 자식 callback(A0)일 뿐 이 단위가 실행하지 않는다.
  - BYTE 표 `1d8ce + sext(D1.W)`(`1d91a`; ROM 20 byte, D1.W는 `48210`의 결과).
  - BYTE 표 `4e4d2 + (D0.W & ff)`(`4e5b0`; ROM `00 02 01 03 00 02 01 03`, C1 `4e58a`와 같은 표).
  - 넘기기만 하는 포인터: `1d664` `1d6c2`(A0, `49c20`이 LONG `5734/5738(A5)`에 넣는 입력 callback; input 단위가 routing함), `1b1b0` `1b1ca`(A0, C2 `1cb08`의 기록 WORD 표), `1bcce`(A0, `1cb38`), `4e370`(A0, C4 `4e564`의 문자열), 자식 `1e67a` `e695a`(A0, `28ae`), `100bf4`(A1, `2986`), `10de18`/`10de20`(A1 → LONG `7a(자식)`).

### `28ae` 자식

- [F] `1e828 MOVEA.L #1e67a,A0; MOVE.W #0,D0; JSR 28ae.l`(돌아온 C를 읽지 않음: `1e83e`는 `MOVE.L`로 시작), `4ed70 MOVEA.L #e695a,A0; MOVE.W #0,D0; JSR 28ae.l`(`4ed8c BCC`가 C를 읽음). `1d558 JSR 2986.l`의 자식 callback은 LONG 표 `1d468`의 칸이다. [F] `1e67a` `e695a`는 routing되지 않았고 어느 계획 단위에도 없다(자식 callback은 closure가 따라가지 않는다). [U] 그 자식이 다음 frame에 실행되면 IO 비교의 새 첫 정지가 될 수 있다. 관측에서 `4ed70`·`1e828`은 실행되지 않았다.

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `28ae` `2986` `2a00` `2a0a` `ce02` `1aa3a` `1cab6` `1cb08` `1cb38` `1cd98` `1d182` `1d1d0` `1dbd8` `1ddd0` `1ddfc` `1de06` `1ed78` `1eeea` `1f1d8` `1f7a4` `1fa3c` `1fae8` `201a2` `206d2` `43e08` `43e34` `43ea4` `48210` `4836e` `49214` `49bca` `49c20` `49c38` `49fc6` `4a974` `4bfc0` `4c0ea` `4d50e` `4e4da` `4e564` `4e57e` `4e6f2` `4f22c` `e6556`. 복귀 PC로만 닿는 routing된 PC: `1dc84`(interpreter stub, `1dc7a JSR ce02`의 복귀), C1 `4e8fc`(`4e8f8 JSR 4f22c`의 복귀).
- [F] **뒤 단위 정지**(실행되거나 닿지만 뒤 단위가 가짐, routing 밖; V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS`):
  - 미룬 입구: `1d3e0`(`1d3d8`의 fall-through, C9), `4eb6a`(`4eb60`의 fall-through, C13).
  - 뒤 단위: `1f2a4`(`1ec2c BNE`, C7, demo frame 431의 IO 첫 정지), `1fa68`(`1ec1e BNE`, C8), `ea626`(`1dad8` `1dc2a` `1dd00` `1dd54`의 `JSR`, C8).
  - [F] **interpreter stub `1dc84`/`1dc8a`의 두 후속 `1dccc`(C Clear) `1dc8e`(C Set)**: `1dc7a JSR ce02`의 복귀가 stub `1dc84`(`JSR 49fc6` → C로 고름)라 C6 run은 이 둘에 닿는다. 둘 다 routing 밖이고 **어느 계획 단위에도 없다**(계획 closure는 routing된 stub에서 멈춘다; 재측정 `r6.json` 전 단위 시작에 없음). 선언 정지로 둔다(결정 6). [U] 이 둘(`1dc8e BSR 1d1d0` → `1dc92` …, `1dccc BRA 201a2`)을 어느 단위가 가질지는 메인 판단이다. IO 관측에서 `1dc7a`는 실행되지 않았다.
  - C6 run이 지나가는 C1~C5 block의 남은 정지(pc5 `EXIT_STOPS` 36개 가운데 C6가 routing한 10개와 위의 `1f2a4` `1fa68`을 뺀 24개; C1 TRAP `4e69a` 포함)도 pc6 `EXIT_STOPS`(모두 31개)에 넣었다.
  - [I] 직선 fall-through로 범위를 벗어나는 곳은 `1d3e0` `4eb6a`(조건 분기의 fall-through라 TB 시작으로 기록됨)와 routing된 `206d2`뿐이다. 재관측 `obs_c6a`에서 새로 보인 PC가 없어 가려진 연속은 없다.
- [F] TRAP 없음. ROM·RAM 실행 없음. 장치 쓰기 없음(`MOVE` 대상은 모두 node·work RAM).

### block 경계를 넘는 flag(결정 3·4)

C5 방식 그대로 `cscan`·호출자 검색과 실행부 검토로 정했다. X를 읽는 명령은 없다.

- [F] **C 소비 block 8개**(Clear 쪽 / Set 쪽; Unknown C면 `player c6 caller requires known carry`): `1d644 BCS 1d662`·`1d6a2 BCS 1d6c0`(`49c38`), `1d934 BCC 1d93c`(C6 `1d510`), `1dc36 BCC 1dc3c`(`4836e`), `1dc62 BCC 1dcd0`·`1ebba BCC 1ed78`(C2 `1cb08`; Set 쪽은 C5 `1cb32`), `1ec66 BCC 1ec70`(`49fc6`), `4ed8c BCC 4edd4`(`28ae`).
- [F] **C 생산 block**: Clear `1d546`(`ANDI.B #fe,CCR; RTS`) `1d54c`(`MOVE.L (A0,D1.W),D1`: `MOVE`는 C를 지움; 두 갈래 모두), Set `1d574` `4838c`(`ORI.B #1,CCR; RTS`).
- [F] **자료 C block 1개**(결정 4): `1d514 CMPI.W #14,D1; BCS 1d51e` — C = 무부호 D1.W < 14(빌림). fall-through `1d51c`는 Clear, 분기 `1d51e`는 Set이다. 실행부는 두 갈래에 그 값을 남긴다(C3 `21c06`·C2 `1e016`의 `DATA_SET`과 같은 처리).
- [F] **C 통과 block 2개**(`carry_preserving_pc`에 넣음): `1d51c RTS`(`1d514`의 Clear), `1d580 RTS`(`1d54c`의 Clear). `1d510`의 C를 읽는 쪽은 C6 `1d934`, C9 `1d70e`(BCS) `1d8fa`(BCC)다.
- [F] **돌려주지만 읽는 쪽이 없는 C**: `b56`(`b0c`의 RTS; 호출자 `4ed48` `4ee5c` 등은 C를 읽지 않음), `e64cc`/`e6514`(`e6496`; `4ed6a TST.W D0`), `1d662`/`1d6c0`(`1d63a`/`1d698`; 호출자의 다음 명령은 `MOVEA`/`MOVE`/`BRA`), `21662`(C3 `21610`의 RTS, `JSR (A4) 201a6`의 복귀 `201a8 JSR`), `4e5c0`, `1e636`, `1e678`. 통과 목록에 넣지 않는다(돌아간 뒤 Unknown).
- [F] **`4ee30 BEQ.W 4ee5c`의 Z**(결정 3): 유일한 선행은 `4ee26 MOVE.W 76(A6),D0; JSR 4a974.l`이다. `4a974`는 `TST.B (A0); RTS`(`4a9b0`/`4a9c6`)로 끝나고 RTS는 그 BYTE를 바꾸지 않는다. controller C1·C2, E1 `de938`, C4 `4e77a`와 같은 규칙: A0가 `4a974`가 가리킬 수 있는 work RAM BYTE 넷(`10fdb0` `10fdb1` `100004` `100005`) 가운데 하나일 때만 BYTE (A0)를 다시 읽어 Z = (BYTE = 0)로 정하고, 그 밖의 A0(32 bit 비교)는 checked `unsupported animation player c6 flag source`(rollback)다.
- [F] **같은 block 안의 묶인 Bcc**(결정 5): `b22 BNE b40; b26 BNE b40`(같은 `BTST`의 Z)와 `e64b0 BHI e64d2; e64b4 BCS e64c0`(같은 `CMP.L`)는 계획 closure가 한 block으로 둔다(`bundled_of`). 실행부는 한 `case`에서 두 조건을 함께 계산한다. [F] `b26 → b40`은 원본에서 일어날 수 없다(`b22`가 fall-through면 Z = 1이라 `b26`도 분기하지 않음). V1 spec은 그 결과를 `BRANCH_IMPOSSIBLE`로 둔다.
- [F] 나머지 `BEQ`/`BNE`/`BPL`/`BMI`/`BGT`/`BLE`/`BHI`/`BCC`/`BCS`/`BLE.B`는 모두 같은 block의 `TST`/`CMP`/`CMPI`/`CMPA`/`BTST`/`SUB`/`ADD`/`AND`/`MOVE`/`SUBQ` 뒤다.

### IO 실행 run과 frame

- [F] 보정 관측(C5 routing 재관측 `obs_c5`로 셈, `work/c6io.py`): C6 PC를 실행하는 run 10개(P1 8, boot-title-start, boot-demo-0), 실행된 C6 PC 79개(시작 77), 실행 10,954회.
  - P1 94 95 100 101 106 107 110 111: 처음 실행 frame **457, 458, 459**(각 1,064회, PC 34개). boot-title-start: **577, 578, 579, 608**(2,059회, PC 37개). boot-demo-0: **381, 407, 410, 411**(383회, PC 42개).
  - [I] frame 457(577): `214d6` 빌림 → `21564` → `JMP 2a00`. frame 458(578): 슬롯 `4e94e` → C1 `4e900 BEQ 4eb58` → `4e5b0` → `4ed3c` → `b0c`(D1 = 3) → `4e4da` → `e6496`(순위가 음수: `e64cc`) → `4edf2` → 상태 `4ee04` 설치·진입. frame 459(579) 이후: `4ee04`(`7db6(A5)+WORD 76`의 BYTE가 0/1이 아님 → `4ee1e` …, WORD `96` 세기, `4ee5c`). title frame 608: WORD `96`이 0 → `4ee44`(`7004(A5)` bit) → `b0c`(D1 = 0).
  - [I] demo frame 381: 플레이어 생성 frame에 C1 `1d1f4` → C2 `1d222` … `1d390` → `1d398` 형식 사슬 → `1daba`(WORD `78` = 0) → `1daee` → `1d63a`(`49c38`의 C; `1d648` `1d662` 모두 실행됨) → `43e08` → `1d90a`(`48210` D1.W = 0 → C2 `1ddd0`). frame 407: C4 `1ef0e` → `1ef9a` → `1efa4`(WORD `88`). frame 410/411: `1efa4` → `1efac` → `1eba0` → `1ebc2` → 상태 `1ebf6`(`1cd98` 입력 D0, `4bfc0` `ce02` `49fc6`). frame 431: `1ebf6`의 `1ec2c`(입력 D0 bit 1) → C7 `1f2a4`(IO 첫 정지 예측) [I].
- [F] **IO 예측(C1~C6 연결)**: 172,297 → **173,820**(+1,523 = P1 8 run × 143 + title 329 + demo 50). 예측 첫 정지: boot-demo-0 frame **431**(C7 `1f2a4` …)뿐. [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다(계획 §7 [U]).
- [F] D1 자연 seed 137개와 P0 run은 C6 코드를 실행하지 않는다.

## 공통 규칙·native 검증 계획

FR2..FR9, C1~C5 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_player_c6.cpp`, 함수 `animation_player_c6_block`. 오류 문자열은 `unsupported animation player c6 PC`(범위 안 내부 PC 직접 진입), `player c6 caller requires known carry`(C 소비 block에 Unknown C; 소비자 8개), `unsupported animation player c6 flag source`(결정 3의 Z 출처 guard) 세 개다. 계산 점프가 없어 jump-target 오류는 없다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(26 범위, C5 줄 뒤), `carry_preserving_pc`의 C5 묶음 뒤에 주석 달린 case 묶음 하나(소비자 8 + 통과 2), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 위 명세의 12개는 쓰고 곧바로 그 값으로 들어가고(`MOVE.L #v,(A6)` 다음 명령이 `v`), `1fcd4` `1e918` `1ed78`은 쓰기만 한다.
- **자료 읽기**(live bus): node field(A6: BYTE `15` `62` `98` `9a` `9c` `9d` `9e` `a7`, WORD `1e` `42` `46` `4a` `76` `78` `7c` `88` `96` `ae` `b0`), 자식 node(A0: WORD `76` `78`, LONG `7a`), A5 기준(WORD `53a2` `53a6` `53aa`, BYTE `5d1e` `5d1f` `7004` `7d82` `5e12` `5e13`, LONG `5e14` `5e1c`, 기록 `5694/569c`, BYTE 표 `7db6 + sext(WORD 76)`), 절대 RAM(BYTE `10f006` `10f007` `10fd8a` `10fdb6 + sext(D0.W)`, LONG 표 `10f02e`, LONG (A0) = `10de14`/`10de1c`), 스택(`1d51e`/`1d532`의 LONG A0·WORD D1, `1d91a`/`1d92e`의 WORD D1), 고정 ROM 표(위 "계산 점프와 표"). 단위 시험은 고정 ROM 자료 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): BYTE 표 `b58` = `00 01 01 00 01 00 00 01 00 00 01 01 01 01 00 00`, WORD 표 `1b1b0..1b1f0`(`1b1b0`: `10 0 12 0 14`, +10: `1 2 3`; `1b1ca`: `c e 0 10 0`, +c: `4 5 6`), LONG 표 `1d468` = 칸 k(4의 배수 0, 그 밖 `30000 + 1234k`), BYTE 표 `1d8ce` = k가 3 7 b f 13이면 1, 그 밖 0, BYTE 표 `4e4d2` = `03 01 02 00 07 05 06 04`. 음수 색인(`1d468 − 8000 = 15468`, `1d8ce − 10 = 1d8be`)과 단위 밖 색인(`b58 + 101`, `1d8ce + 103`)은 C++ 전용 규칙에서 합성 byte 하나를 더한 bus(`runs_to_extra`)로 확인한다. V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W/.B`, `ADD.W`, `SUB.W`, `ADDI.W`, `ADDQ.W`, `SUBQ.W`, `ANDI.W`, `AND.W`, `ASR.W`, `LSL.W`, `ADD.B`, `CLR.W`, `CLR.B`, `MOVE.B #imm`). `MOVEQ`·`MOVE.L`·`MOVEA.L`·`MOVEA.W #0`(부호 확장 LONG)·`LEA`·`CLR.L`·`ADDA.W`(부호 확장)는 LONG 전체. 색인 `(An,Dn.W)`·`ADDA.W`는 부호 확장 WORD. `ADD.B (A0,D0.W),D7`은 BYTE 덧셈이라 자리올림을 버리고 D7 bit 8..15를 그대로 둔다. `ASR.W #2`는 산술 WORD shift(bit 14..15에 부호). 비교: `CMPI.W #k,D7`(WORD 같음), `CMPI.W #14,D1` + `BCS`(무부호 WORD), `CMPI.W #9,D1`, `CMPI.W #a,D1` + `BEQ`, `CMPI.W #a,D1` + `BLE.B`(부호 WORD ≤ 10), `CMP.W ae(A6),D0` + `BLE`(부호 WORD), `TST.B 9d(A6)` + `BGT`(부호 BYTE > 0), `CMP.L D4,D3` + `BCC`/`BHI`/`BCS`(무부호 LONG), `CMP.L 5e1c/5e14(A5),D3` + `BCC`(무부호 LONG), `CMPA.L #10de14/#10de1c,A0`(32 bit 전체), `CMP.B 9a(A6),D0`·`CMPI.B #0/#1,D0`(BYTE), `SUB.W 7c` + `BMI`(WORD 결과 부호), `ADD.W 53aa` + `BPL`(WORD 결과 부호), `SUBQ.W #1,b0` + `BCS`(빌림 = 이전 WORD 0), `TST.W D0` + `BMI`(WORD 부호), `TST.W/.B field`. bit: `BTST/BSET/BCLR #n,d(An)`·`Dn,abs`·`Dn,d(A5)`(memory BYTE, bit mod 8), `BTST #n,Dn`(LONG bit n).
- **스택.** `1d51e`가 LONG A0, WORD D1 순서로 넣고(D1이 낮은 주소) `JSR 481b2`, `1d532`가 WORD D1(상위 유지), LONG A0 순서로 꺼낸다. `1d91a`가 WORD D1을 넣고 `1d92e`가 꺼낸다(상위 유지).

## carry와 Z(결정 3·4)

- [F] 소비자 8개·통과 2개·생산자·자료 C는 위 명세와 같다. dispatcher는 `carry_preserving_pc`에 없는 PC로 갈 때 C를 Unknown으로 만든다. 따라서 이 단위의 C 의미는 (1) 소비자 8개가 known C를 읽고 그대로 둔다, (2) 통과 block `1d51c` `1d580`이 들어온 C를 그대로 둔다, (3) 생산자 `1d546` `1d54c`(Clear) `1d574` `4838c`(Set)와 자료 C `1d514`가 자기 block에서 C를 정한다, (4) 나머지 block 뒤 C는 Unknown이다.
- [F] **`4ee30`의 Z**(결정 3): 위 명세. A0 ∉ {`10fdb0`, `10fdb1`, `100004`, `100005`}면 checked flag-source 오류(24 bit가 같아도 32 bit가 다르면 오류: `1100004`).

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1..FR9·C1~C5 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: 그 node(A6)에 선언 편집. ROM 쓰기 명령·호출자가 범위를 정한 값은 그 범위 안으로 둔다: WORD `76`/`78` 대부분 0/1, `b0c` 직접 진입의 D0.W 0/1과 D1.B 0..3, `1d510`~`1d54c`의 D1.W 대부분 < 14, `1d398`의 D7.W 형식, `e6496` 계열의 A0 = `10de14`/`10de1c`, BYTE `9e(A6)` 0..3, LONG `84(A6)` := C3 목록의 routing된 칸 값, BYTE `10fd82` := 0(`4a974`가 BIOS `c00450`을 부르지 않게), BYTE `10fdb6`/`10fdb7` 0..3, LONG 표 `10f02e`와 LONG `10de14`/`10de1c`/`5e14`/`5e1c(A5)`.
- **IO pack 자연 node 상태(family `natural`, 16개)**: P1 94 frame 457 458 459 490, P1 106 frame 458 459, boot-title-start frame 577 578 579 608 610, boot-demo-0 frame 407 411 492의 node pool에서 callback LONG이 C5 `214d6`, C4 `4e94e` `1ef0e` 또는 C6 설치 값인 node, 레지스터만 선언(A5 := `108000`, A6 := node, A7 := `10ef00`(복귀 LONG = sentinel), PC := callback).
- **재설치 world(family `reinstall`, 15개)**: demo frame 382 node `100cb8`에 C1 `1d1f4`(→ C2 → `1d398` 형식 사슬, C6 block 19개를 지나 sentinel까지), P1 94 frame 459 node `1009a8`에 `4ee04`(WORD `96` = 0 / 1, BYTE `9a`)·`4edc0`(BYTE `62` = 0 / 1), P1 94 frame 458 node `100cb8`에 `1e89e`(LONG `84` := `21602`; WORD `42`/`ae` = `7fff`/`8000`)·`1ebf6`, demo frame 411 node `100cb8`에 `1ebf6`(BYTE `15` = 0)·`1dace`(WORD `b0` = 0)·`1dcf6`(WORD `b0` = 3)·`1dc20`·`1daee`·`1dd6a`, title frame 608 node `1009a8`에 `4ee04`(WORD `76` = 1). [I] 이미 진행된 node를 다시 시작하는 world이며 native와 C++가 같은 상태를 받으므로 V1 비교는 유효하다. [F] P1 94 frame 458의 node `100cb8`은 frame 457에 `JMP 2a00`으로 제거된 node라 LONG `84`가 C3 허용 목록 밖이다. 그래서 `1e89e` 재설치 world는 LONG `84`를 선언한다(첫 시도 `v1_pc6_try1`의 실패 2개).
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다(`CHAINS` 8개 + Z 사슬 `4ee26` → `4a974` → `4ee30`): `1d63a`/`1d698`(`49c38`), `1d92e`(C6 `1d510`), `1dc30`(`4836e`), `1dc42`/`1ebb2`(C2 `1cb08`, 원본 ROM 표 `1b1b0`/`1b1ca`에서 BYTE `9f`와 LONG `22(A6)` 표를 맞춤), `1ec60`(`49fc6`), `4ed70`(`28ae`).
- node fixture: 설치 값 12개를 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다. callee fixture: helper `b0c` `e6496` `1d510` `1d63a` `1d698` `1e60a` `1e65c` `481b2` `4e5b0`와 꼬리 `1d398` `1d90a` `1daba` `1dbc6` `1dc1a` `1dcd0` `1dce2` `1dd36` `1dd88` `1dda8` `1e824` `1eba0` `1efa4` `206cc` `21564` `21662` `4838c` `4e572` `4e8f8` `4eb58` `4ed3c`를 subroutine으로 들어간다.
- 단위 시험(Unicorn 생성기, C5 꼴에 C3의 자료 C 처리; 장치 port 없음을 확인): 시작 212개(소비자 8개 제외; `4ee30`은 native SR Z를 다시 계산한 Z와 같게 두는 행 `single 5`) × 들어오는 C 3가지, zero-step, 내부 PC 740개 정확한 오류, 경계 stop(출구·뒤 단위 정지 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC. 손으로 계산한 규칙(`rules_a`..`rules_h`): `ADD.B` 자리올림 버림(`fc + 5 → 01`, `4 + fe → 02`), D7.W 색인 폭(`0101`), `(A0,D0.W)` 부호 확장(`1f8000 + sext(8000) = 1f0000`), 형식 사슬의 WORD 비교(`0106` 등), `CMPI.W #14`의 빌림과 C, LONG 표 음수 색인(`15468`), WORD push/pop과 상위 유지, `SUBQ.W` 빌림, `ASR.W #2`(`fffd → ffff`, `8000 → e000`, `8003 → e000`), WORD 합의 부호, 부호 `BLE`(`7fff`/`8000`), 부호 `BGT`(`80`), `AND.W` 마스크와 D0 변경, `ANDI.W #ff`(bit 7 유지), `TST.B`의 이웃 BYTE, `4ee30` 출처와 BYTE, `ADDA.W` 부호 확장(A5 = `f824a`, WORD 76 = `8000` → `f8000`), 무부호 LONG 비교(`80000000`/`7fffffff`), 부호 WORD 반복 한계(`7fff → 8000`, `fff0`), `CMPA.L` 32 bit(`1010de14`), ff node(쓴 field와 이웃 BYTE 유지).

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `beff46d62a342129120d107dba0848ca937dddf9301c16902d19a521d8da2f21` → `bd037aff436d5b102749b0c97562660c5b32423736393f679dede2d2dcecefd4`, `animation_machine_internal.h` `0dc447022c1b885d2fb7e112329823cb8373ee6369949b6811ae678a635939bd` → `5458ca6c08b35b69780549b938650f1c649eed535a4ce1760b828644efd6d9a5`(이 단위의 공유 수정; 옛 값은 `# player C6 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 작업 트리와 scratch clone root에서 확인했다(`work/pincheck.py`).
- [F] **U02 시험 `engine/tests/animation_machine_objects_u02_test.cpp` `boundaries()`**: 이전 = `e5086-p1` `e5086-p2`(`JSR e6496`)를 stop = `STOP`으로 다시 돌려 `unsupported animation machine PC`(e6496 미routing)를 기대. 새 = 그 둘을 목록에서 뺐다(`e6496`이 C6 시작이라 run이 지나감; 두 성공 fixture는 여전히 `e6496`에서 멈춤, stop-only). 같은 함수의 `48256`(FR2b) 선례와 같은 처리이며 주석에 이전 기대값을 적었다.
- [F] **C3 시험 생성기와 시험**(`tools/generate_animation_machine_player_c3_test_table.py`, `engine/tests/animation_machine_player_c3_test.cpp`): 오류 행 `error-21610-key-3`(목록 `21622`의 key 불일치 → C Clear → `21662`에서 `unsupported animation machine PC`) → `error-21610-key-3-then-10fe40`(`21662`가 C6 RTS라 복귀 LONG을 RAM `10fe40`으로 두고 그 PC에서 같은 오류). 생성기를 다시 돌려 이 행 하나만 바뀜을 확인했다. C3 시험 줄: 1,293 fixtures, 115,899 → 115,900 checks.
- [F] **C4 시험 생성기와 시험**: `error-4e564-then-4e572` → `error-4e564-then-10fe40`(`4e572` → `4e57e` → `JMP 3918`의 RTS가 RAM 복귀 LONG `10fe40`으로). 이 행 하나만 바뀜. C4 시험 줄: 1,372 fixtures, 135,877 → 135,878 checks.
- [F] **C5 시험 생성기와 시험**: `error-214d6-then-21564` → `error-214d6-then-2a00`(`21564` → `JMP 2a00` → `BSR.B 299c`를 홀수 A7에서; `program bus requires even WORD/LONG address`, 실패 PC `2a00`). [F] 짝수 A7로는 `2a00` 제거 뒤 dispatcher `2abe`가 LONG (0)을 읽어 `reached program vectors require exact128BYTE view`가 된다(scratch `work/probe`); 원래 뜻(앞 block을 실행한 뒤의 rollback)을 지키는 홀수 A7 행을 골랐다. 이 행 하나만 바뀜. C5 시험 줄: 1,184 fixtures, 162,967 checks(같음).
- [F] **V1 spec `ROUTED_LATER`**(선언 정지로 그대로 둠, C2~C5가 쓴 방식): pc1 += `4e8f8` `4eb58`; pc2 += `1d398` `1ebbe`; pc3 += `206cc` `21662` `4838c` `1d398` `1ebbe`; pc4 += `1efa4` `4e572` `1d398` `1ebbe` `206cc` `21662` `4838c` `4e8f8` `4eb58`; pc5(이전 빈 목록) := `21564` `1efa4` `4e572` `1d398` `1ebbe` `206cc` `21662` `4838c` `4e8f8` `4eb58`.
- [F] **V1 spec 오류 fixture**: pc4 `error-4e564-then-4e572`(`4e572`에서 unsupported) → `error-4e564-then-391a`(WORD 76 = 0, 홀수 A7: `4e572` → `4e57e` → `3918` → `391a BSR 386e`에서 `program bus requires even WORD/LONG address`). [F] C4 시험처럼 RAM 복귀 LONG `10fe40`을 쓰면 native 짝 행(`failpc`)이 work RAM PC에서 멈추지 못한다(`fetch-protected`, 첫 회귀 실행의 실패 1개). pc5 `error-214d6-then-21564` → `error-214d6-then-2a00`(홀수 A7, C5 시험과 같음).
- [F] **`tools/verify_animation_machine_input.py`**(옛 outside-PC 목록, 861행): `1d63a` `1d698` `1daba`가 C6 시작이 되었다. 이전 기대값 = 셋 모두 `unsupported animation machine PC`. 새: `SUPERSEDED_OUTSIDE`에 `1d63a` `1d698`(`area C C6 (player_c6)`; base row `natural-stage-frame-0000`, carry 2, stop `ff000`에서 정상 복귀 — 기존 API-only control 방식), 새 `SUPERSEDED_OUTSIDE_ERRORS`에 `1daba`(같은 base row에서 WORD 78 = 0 → `1daee` → `1d63a` → `43e08` → `1d90a` → `48210` → `1d914` → C2 `1ddd0` 뒤가 `unsupported program bus device address`로 rollback; 결과 행에 이전 기대값과 `superseded_by`를 남김). 관측: scratch `work/probe_input.py`·`probe_input2.py`(검증기를 import해 같은 harness·base row로 실행, `trial_logs/probe_input*.log`). 861행 번호는 바뀌지 않아 stage_area 검증기의 `BREAKING_EXPECTATIONS` 키는 그대로다.
- [F] 바뀌지 않음(확인): motion-walk 검증기의 계산 out-of-range PC 86개와 guard PC는 C6 범위에 없다(`work/mw_oor.py`). objects_g1 관측기의 `BOUNDARY`(U02의 `e6496`)는 stop으로만 쓰인다(stop은 routing보다 먼저 검사; FR2b가 routing한 `48256`도 같은 목록에 그대로 있음) [I]. stage_area 검증기·관측기의 `(48180, 481b2)` `(481de, 48210)`, input 시험의 `(1d61a,1d63a)` `(1d664,1d698)` `(1da60,1daba)` 범위는 C6와 맞닿을 뿐이다(`make test` 통과). 그 밖의 `hexsearch6.out` 적중은 stop으로만 쓰는 값, 주석, 다른 시험 자료 안의 우연한 값이다. 다른 단위 소스의 주석("`e6496` have no executor" 등)은 고치지 않았다(다른 검증기가 그 소스 SHA를 pin할 수 있음).
- [I] native 사슬이 이 단위의 PC를 첫 routing 밖 PC로 멈추던 V1 spec·검증기는 더 진행한다(정지는 routing에서 계산된다). pc1~pc5는 그 PC를 선언 정지로 두어 fixture 집합이 같다(V1 회귀 수는 아래 기록). 나머지는 메인 runner의 회귀·legacy 단계가 확인한다.

## 결정

1. **범위와 시작(scope correction): 계획 214 block에서 C4 결정 1의 `4e57e` `4e8e6`을 빼 212 block, 26 범위. 숨은 직선 block 추가 없음.**
   - [F] 재측정(212) = 계획 − {`4e57e`, `4e8e6`}. 범위 밖에서 범위 안 비시작 PC로 들어오는 직접 분기는 없다.
   - [F] **숨은 직선 연속 검사**: C5 routing과 C6 routing 각각으로 C·E run 18개를 정확한 bitmap으로 다시 관측했다(`reobs_c6/obs_c5`, `reobs_c6/obs_c6a`, native 기록은 18 run 모두 원래와 같음). 새로 보인 PC 0개, C6 routing 관측의 예측 첫 정지는 demo frame 431의 C7 `1f2a4` …뿐이고 나머지 17 run은 600 frame(또는 guard) 끝까지 간다. 예측 173,820은 계획 표와 같다.
   - [F] E helper `b0c`·`e6496`(계획 결정 6)이 이 단위에 있어 E 남은 실행 PC가 0이 된다.
2. **계산 점프 없음, 고정 ROM 표는 live bus.** `b58` `1d468` `1d8ce` `4e4d2`를 원본 그대로 읽고 상한을 검사하지 않는다(C3 결정 5와 같음). 단위 시험은 합성 byte로, V1·실제 ROM 차분은 원본으로 확인한다.
3. **RTS를 넘는 Z `4ee30`.** `4a974`의 `TST.B (A0)`를 A0가 그 BYTE 넷 가운데 하나일 때만 다시 읽는다(controller C1·C2, E1, C4 결정 3과 같은 규칙). 그 밖은 checked `unsupported animation player c6 flag source`(rollback).
4. **RTS를 넘는 C.** 소비자 8개는 known C를 읽거나 checked 오류. `1d514`의 `CMPI.W` 빌림은 자료 C로 두 갈래에 남기고(Clear → `1d51c`, Set → `1d51e`), `1d54c`의 `MOVE.L`은 Clear, `1d546` Clear, `1d574` `4838c` Set. 통과 block `1d51c` `1d580`만 `carry_preserving_pc`에 더한다(생산자는 자기 block에서 C를 정하므로 넣지 않음, FR 관례).
5. **묶인 Bcc.** `b22`/`b26`, `e64b0`/`e64b4`는 계획 closure대로 한 block. 원본에서 일어날 수 없는 `b26 → b40`은 V1 spec의 `BRANCH_IMPOSSIBLE`로 도달 못한 결과 목록에서 뺀다(새 spec 상수; 다른 spec은 바뀌지 않음).
6. **뒤 단위 정지와 앞 단위 spec.** C6 block이 닿는 뒤 단위 시작 3곳(`1f2a4` `1fa68` `ea626`)과 미룬 입구 2곳(`1d3e0` `4eb6a`), interpreter stub의 두 후속 `1dc8e` `1dccc`(어느 계획 단위에도 없음, [U] 소속은 메인 판단), C1~C5의 남은 정지 24곳을 V1 `first_unrouted`와 실제 ROM 차분의 선언 정지로 둔다. pc1~pc5의 `EXIT_STOPS` 가운데 C6가 routing한 PC는 `ROUTED_LATER`로 허용하고 선언 정지로 그대로 둔다(C2~C5가 쓴 방식).
7. **`2986` 실패 경로.** buffer_cue 결정 1(caller-X 한계는 의도된 checked 오류)을 그대로 둔다(B4 결정 4, C5 결정 8과 같음). `1d558 JSR 2986`이 `28ae` 실패(WORD `104ca0` 한도·free list 끝)를 만나면 C++는 `cue wrapper failure requires known caller X`로 멈춘다. [I] 원본은 더미 node `100e98`에 쓰고 이어 간다. 단위 시험 생성기의 `1d92e` 사슬 world는 free node를 두어 이 경로를 피한다. 실제 ROM 차분은 이 경우를 기존 문서화 분류로 센다(seed 1에서 2건). [F] IO 관측에서 `1d558`은 실행되지 않았다.
8. **실행부 파일·오류 문자열.** 위 "공통 규칙". 오류 문자열 3개.
9. **다음.** 계획 순서대로 C7(demo `1f2a4` … `248de` `1f6da` `2285c`, 표 `25298`). C6 연결로 IO +1,523(173,820)을 메인 runner가 확인한다. interpreter stub 후속 `1dc8e` `1dccc`와 자식 `1e67a` `e695a`, 쓰기만 하는 `1e918`(C10)·`1fcd4`(C8)의 소속을 C7 이후 계획에서 정해야 한다.

## 미확인

- [U] node field·전역 값의 의미(BYTE `62` `98` `9a` `9c` `9d` `a7`, WORD `76` `78` `7c` `88` `96` `ae` `b0`, A5 `53a2..53aa` `5d1e` `5d1f` `7004` `7d82` `7db6` `5e12..5e1c`, BYTE `10f006` `10f007` `10fd8a` `10fdb6`, LONG 표 `10f02e`, 표 `b58` `1d468` `1d8ce`). 이름(E helper, 순위, 슬롯 상태, 형식 사슬, 15 frame 상태, 입력 분기)은 동작에서 붙인 [I]이다.
- [U] IO 관측에서 실행되지 않은 이 단위의 block 135개(`b40` `b50`, `1d510`~`1d580`, `1d698`~`1d6c0`, `1d91a`~`1d93c`, `1dac2`~`1dae8`, `1dbc6` `1dbca`, `1dc1a`~`1ddcc` 대부분, `1e60a`~`1e8da`, `1ec0c`~`1ec28` `1ec6a`, `481b2`~`481c2`, `4ed5e`, `4ed70`~`4ede6`, `4ee50`, `e64aa` `e64d2`~`e6514`)는 closure로 들어왔다(V1 선언 상태·재설치 world·실제 ROM 차분으로만 확인).
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC). 예측은 demo frame 431의 C7 `1f2a4`다.
- [U] 재설치 world와 IO pack 자연 node 상태의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C5와 같음).
- [U] 결정 1의 정확 bitmap 재관측은 C·E run 18개만 했다(계획 §7과 같은 범위).
- [U] interpreter stub 후속 `1dc8e` `1dccc`와 자식 `1e67a` `e695a`의 소속(결정 6·9). IO 관측에서 이 경로는 실행되지 않았다.
- [U] `2986` 실패 경로(결정 7)가 IO 진행 중에 생기는지는 IO 비교가 확정한다.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_player_c6.cpp`(case label 212 = `starts_C6_final.txt`와 집합 일치; 공용 함수 `pc6_get` `pc6_put` `pc6_bit`(memory BYTE bit, 옛 bit) `pc6_word_zero` `pc6_carry` `pc6_return_carry` `pc6_field_call` `pc6_install` `pc6_counter_install` `pc6_count_down` `pc6_motion_call` `pc6_offset` `pc6_b58` `pc6_b0c_call` `pc6_rank_up`), `engine/tests/animation_machine_player_c6_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_h`), `tools/generate_animation_machine_player_c6_test_table.py`(생성기; C5 생성기에 C3의 자료 C(`data_carry`/`path_data`)를 더함; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 95초), `tools/unit_fixture_specs/pc6.py`(V1 spec; C5 spec의 공용 부분 그대로, 단위 부분 교체, `EXIT_STOPS`(31), `PASS_SET` `CLEAR_SET` `SET_SET` `DATA_SET`, `Z_READERS`, `BUNDLED`, `BRANCH_IMPOSSIBLE`, `OTHER_JUMP_PCS`, family `reinstall`). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `starts_C6_final.txt`(SHA256 `7b910e5be798cbb680f3e0c004e787098cba436bdf85f584eaa2540db74963cb`) = 계획 `starts_C6.txt`(214) − `4e57e` `4e8e6`(C4 결정 1).

- **`b0c..b58`(6)**: `b0c b2a b3c b40 b50 b56`
- **`1d398..1d940`(38)**: `1d398 1d3a0 1d3a8 1d3b0 1d3b8 1d3c0 1d3c8 1d3d0 1d3d8 1d510 1d514 1d51c 1d51e 1d52c 1d532 1d53e 1d546 1d54c 1d558 1d56a 1d574 1d580 1d63a 1d644 1d648 1d662 1d698 1d6a2 1d6a6 1d6c0 1d90a 1d914 1d91a 1d928 1d92e 1d934 1d938 1d93c`
- **`1daba..1ddd0`(57)**: `1daba 1dac2 1dace 1dad8 1dade 1dae6 1dae8 1daee 1daf2 1db06 1dbc6 1dbca 1dc1a 1dc20 1dc2a 1dc30 1dc36 1dc3a 1dc3c 1dc42 1dc62 1dc66 1dc6a 1dc70 1dc74 1dc7a 1dcd0 1dcd6 1dcde 1dce2 1dcea 1dcf6 1dd00 1dd06 1dd0e 1dd10 1dd16 1dd1a 1dd32 1dd36 1dd3e 1dd4a 1dd54 1dd5a 1dd62 1dd64 1dd6a 1dd6e 1dd84 1dd88 1dd8c 1dda4 1dda8 1ddac 1ddc4 1ddc8 1ddcc`
- **`1e60a..1e8de`(23)**: `1e60a 1e616 1e622 1e626 1e62e 1e630 1e65c 1e672 1e674 1e824 1e828 1e83e 1e87e 1e892 1e89e 1e8a8 1e8ae 1e8b4 1e8be 1e8c4 1e8c8 1e8d4 1e8da`
- **`1eba0..1efb0`(25)**: `1eba0 1eba8 1ebb2 1ebba 1ebbe 1ebc2 1ebf6 1ebfa 1ec04 1ec0c 1ec16 1ec1e 1ec28 1ec2c 1ec34 1ec3c 1ec46 1ec50 1ec56 1ec60 1ec66 1ec6a 1ec70 1efa4 1efac`
- **`206cc..21664`(3)**: `206cc 21564 21662`
- **`481b2..48392`(4)**: `481b2 481be 481c2 4838c`
- **`4e572..4ee7a`(40)**: `4e572 4e5b0 4e8f8 4eb58 4eb60 4ed3c 4ed48 4ed4c 4ed54 4ed5e 4ed64 4ed6a 4ed70 4ed8c 4ed90 4ed9a 4eda4 4edaa 4edc0 4edc8 4edca 4edce 4edd4 4eddc 4ede6 4edec 4edf2 4ee04 4ee16 4ee1e 4ee26 4ee30 4ee34 4ee3c 4ee44 4ee50 4ee5c 4ee68 4ee70 4ee78`
- **`e6496..e6516`(16)**: `e6496 e64a2 e64aa e64ae e64b8 e64c0 e64cc e64d2 e64de e64e6 e64f0 e64f4 e64fe e6506 e6510 e6514`

## 검증 수치

작업자 최종 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j3 all test`(최종 실행부·시험): 종료 0, 경고 0, Python 310 OK(`trial_logs/make_full1.log`). C6 시험 줄: `animation machine player pc6: 1248 fixtures (786 single-block, 8 Z reader, 350 path, 42 producer chain, 16 declared C, 46 checked error (12 with a later failing PC), 85 kept C), 212 blocks, 5319 calls, 180401 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 실제 사슬 두 C 값 6개(`1d63a` `1d698` `1dc30` `1dc42` `1ebb2` `4ed70`; `1d92e`는 Set 쪽 경로(`2986` `49214`)의 native run이 버려지고 [I: 선언 밖 ROM 읽기], `1ec60`(`49fc6`)은 bank·interpreter를 건드려 버려져 선언 C 행만), Z 사슬 두 결과 모두, 출구 중 stop이 아닌 것 0. 생성기를 다시 돌려 시험 파일이 바이트 단위로 같음을 확인했다(`trial_logs/gen_c6_repro.log`). 다른 player 시험 줄은 "영향받는" 절의 C3·C4 checks 변화 말고는 C5 기록과 같다.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, `work/ubsan.sh`, C6·C5·C4·C3 시험): 빌드 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_final.log`).
- [F] V1 pc6(작업자, `--workers 2`, scratch `work/v1_pc6`): fixture 1,856개(block 882, chain 18, node 27, natural 16, reinstall 15, callee 104, error 774, failpc 10, negative 10) failed 0, 방문 시작 212/212, 빠진 후속 0, 도달 못한 분기 결과 0(`b26 → b40`은 결정 5의 `BRANCH_IMPOSSIBLE`), 뒤 단위 gate 0, carry oracle Unknown/Clear/Set = 1008/42/22(`trial_logs/v1_pc6.log`). natural·reinstall 31개 가운데 22개가 sentinel까지 가고(C6 block 최대 34개), 2개는 `21564` → `2a00`, 2개는 `1e89e` → C3 `201a2`/`21602` 뒤 `21620 JMP (A1)`의 목록 대상 `21950`(routing 밖), 2개는 `1ebf6` → `1fafc`(앞 단위의 남은 선언 정지), 3개는 `ea626`(C8)에서 멈춘다. 첫 시도(`v1_pc6_try1`)의 실패 3개는 spec 결함이었다: `1dc70` node fixture가 interpreter stub 후속 `1dc8e`에 닿음(선언 정지 추가, 결정 6), `1e89e` 재설치 world 2개의 LONG `84`가 제거된 node의 값(선언 추가).
- [F] V1 회귀(작업자, `work/v1_regs.sh`): pc1 1,264/1,264, pc2 1,743/1,743, pc3 1,831/1,831, pc4 1,873/1,873, pc5 1,755/1,755, se1 2,102/2,102, fr1 1,631/1,631(모두 failed 0; 수는 C5 기록과 같음). 첫 회귀의 pc4 실패 1개(`failpc-4e564-then-10fe40`, native가 work RAM PC에서 멈추지 못함)는 오류 fixture를 `4e564-then-391a`로 바꿔 고쳤다("영향받는" 절). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·BSET/BCLR, WORD/BYTE → LONG, 복귀 PC, carry tag, mask·부호, 상수·설치 값, 부호 확장 제거, C6 helper 호출 꼴) + 손으로 고른 helper·block 변이(`ADD.B` 자리올림, 색인 폭과 부호 확장, `CMPI.W #14` 빌림과 C, 형식 사슬 WORD 비교, `ASR.W #2`, 부호/무부호 비교와 `BLE`/`BLT`, `CMPA.L` 24 bit, `4ee30` 출처 guard·BYTE, 15 frame 세기, push/pop 순서와 크기 등) + dispatcher carry 목록 10개·추가·범위 1개를 적용해 만든 것, 653개; `--workers 3`): 1회째 `killed 618 of 653`(`trial_logs/mut_first.log`). 생존 35개 중 24개는 시험 빈틈이었고 규칙 `rules_h`로 메웠다(`mut_gaps.log`, 그 뒤 남은 3개도 규칙을 고쳐 `killed 3 of 3`): 형식 사슬 8 block의 WORD 비교(`0106` 등), `b2a`의 D7.W 색인(`0101`, 합성 byte 하나 더한 bus)과 `(A0,D0.W)` 부호 확장(위쪽 RAM 거울 `1f8000 + sext(8000) = 1f0000`; 0 확장이면 `200000` bank), `b3c` 같은 확장, `1d91a` WORD push(`0103`), `1e672` `MOVEQ`(LONG), `4e5b0` `ANDI.W #ff`(bit 7), `4eb60` `4edc0` `4ee1e`의 `TST.B`(이웃 BYTE), `4ee30`의 BYTE 출처, `e64b8`의 WORD 비교, `e64c0`의 WORD 덧셈, `e64d2` `e64f4`의 `CMPA.L` 32 bit. 남은 11개는 동치다(`mut/equivalents.txt`: `ANDI`/`AND`/`MOVEQ` 뒤라 상위 BYTE가 0인 비교·색인 6, `MOVE.L`이 곧 덮는 D1의 `ADD.W` 2, `am_write`의 자체 mask 2, 부호 bit가 서지 않는 D7.W 색인 1 — 사례별 이유 기록). 64 KiB RAM 거울이 부호 확장 변이를 가리는 곳은 위쪽 RAM 거울 `1f8000`과 ROM 창(`15468`, `1d8be`, A5 = `f824a`의 `f8000`) 규칙으로 덮었다. 규칙을 더한 뒤 전체 2회째 `killed 642 of 653`(`trial_logs/mut_second.log`), 남은 11개가 동치 목록과 같다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`), `real_pc6.py`(C5 harness에 C6 world·소비자·통과·Z 진입·선언 정지; C5 계산 점프의 착지를 trace 전체에서 대조하는 분류 유지; `4ee30` 직접 진입의 출처를 native 레지스터에서 다시 계산해 분류)): 작업자 300건 × 3 — seed 1 `mismatches 0`(`covered starts 199 of 212`; 문서화된 분류 C3 jump-target 15건(무작위 slot-84 LONG의 `201a6`), 기존 `2986` caller-X 분류 2건(`1d54c` `1d92e` → `1d558 JSR 2986`, 결정 7)), seed 7 `FOLLOW_ANIM=1` `mismatches 0`(207/212; C3 jump-target 10건, caller-X 1건, native oracle abort 1건), seed 8 `FOLLOW_ANIM=1` `mismatches 0`(202/212; C3 jump-target 7건). 세 batch를 합치면 211/212 시작을 지났다(`1dd5a`만 빠짐; V1·단위 시험은 지남). [F] seed 7 `FOLLOW_ANIM=1`의 첫 실행은 native oracle(Unicorn 2.1.4 `tcg_gen_code_m68k` → `tcg_out_st`)이 프로세스를 abort시켜 결과 없이 끝났다(`trial_logs/real_n300_f7_unicorn_abort.log`, faulthandler C stack). C++ 쪽 문제가 아니다. 그래서 harness가 native를 case마다 fork한 자식에서 돌리게 했고(`native_safe`, `SAFE_NATIVE=1` 기본; 자식의 계수·trace를 돌려받음), 다시 돌린 seed 7에서 그 case(entry `1e89e`) 1건이 abort로 건너뛰어졌다 [U: abort 원인; 무작위 world의 코드 생성 한계로 보임 [I]]. seed 11 50건으로 fork 전후 결과가 같음을 확인했다. 정지하지 않은 native(약 10~17%; 주로 무작위 RAM의 긴 반복·interpreter)는 건너뜀. 로그 `trial_logs/real_n300_s1.log` `real_n300_f7.log` `real_n300_f8.log`.
- [F] `dleft.py`: 이전(routing `beff46d6…`) C 261 / E 12, 예측 172,297, 첫 정지 C 10(`dleft_before.log`; 재관측 `obs_c5`로도 같음). 이후(routing `bd037aff…`) C **194** / E **0**, 예측 **173,820**, 첫 정지 C 1(`dleft_after.log`; 재관측 `obs_c6a`로도 같음). 예측 첫 정지 PC(`work/firststops_after.txt`): boot-demo-0 frame 431의 C7 `1f2a4` `1f2ac` `1f2d8` `1f2e2` `1f30a` `1f312` `1f5f2` `1f614` …; 나머지 run은 정지 없음.
- [F] 기존 검증기 새 기대값은 scratch에서 관측했다: input 검증기는 그 모듈을 import해 같은 harness·base row로(`work/probe_input.py` `probe_input2.py`, `trial_logs/probe_input*.log`), C3·C4·C5 오류 행의 새 실패 PC는 C++ 탐침(`work/probe/probe.cpp`)으로. scratch clone root(`roots/probe`, `work/mkroot.py`: 작업 트리 clone + 변경 파일 복사 + 공유 자료 symlink)에서 stage_event / stage_event_ops `CPP_PINS`가 파일 SHA와 같음을 확인했다(4 / 9 pin, 불일치 0, `trial_logs/pincheck_root.log`).

## 메인 결정(2026-10-22)

- `1dc84`의 인계 목표 `1dccc`/`1dc8e`, `28ae` 자식 `1e67a` `e695a`, callback `1e918`은 이 관측 집합에서 실행되지 않는다(보정 관측에서 실행 PC 0). 지금은 선언 정지로 두고, 나머지 단위 C9~C13을 다시 잴 때 그 단위들에 넣는다.
- real-ROM harness의 `native_safe`(native 사례를 fork한 자식에서 실행, Unicorn 코드 생성기 abort를 그 사례만 건너뜀)를 이후 단위의 기본으로 쓴다.

## 검증 기록(검증 실행: 결정적 runner + 메인 검토)

- [F] `make -j4 all test`: 종료 0, 경고 0, Assert 0, Python 310 OK. C6 시험 `animation machine player pc6: 1248 fixtures (786 single-block, 8 Z reader, 350 path, 42 producer chain, 16 declared C, 46 checked error (12 with a later failing PC), 85 kept C), 212 blocks, 5319 calls, 180401 checks`.
- [F] `ubsan`: build/run 종료 0, runtime errors 0.
- [F] `mutation`: total 653, killed 642, equivalent 11.
  - 이 실행 전에 메운 시험 빈틈 24개.
  - 메모: 상위 RAM 미러와 ROM 창 음수 인덱스.
- [F] real-ROM: batches `f4`, `f5`, `s1`, `s2`, `s3` covered `212`, `211`, `212`, `211`, `212`; mismatches `0,0,0,0,0`(합집합 212/212).
  - 오라클: `native_safe`는 각 네이티브 케이스를 포크된 자식 프로세스에서 실행하며, Unicorn TCG abort가 발생하면 해당 케이스만 건너뛴다.
- [F] V1: A/B 각각 fixtures 1856, failed 0, runs 2, identical true(digest `9860d816609ecb5d`); regression specs 39개 모두 failed 0.
- [F] legacy verifiers: `stage_entry`, `area_clear`, `stage_event`, `stage_event_ops`, `frame_helpers`, `card_menu_close`, `input`, `scene_core`, `scheduler`, `objects_g1` 모두 종료 0. `objects_g1` 판정은 C1과 같다.
- [F] frames: `d1` 54400/54400, mismatches 0; `controller_game` 54400/54400, mismatches 0; `irq` 54400/54400, mismatches 0; `demo` 45684/45684, mismatches 0.
- [F] IO: matched_total 173820, baseline 172297, delta 1523, mismatches 0, cpp_errors 0, runs 2, identical true; per_config `P0` 81600, `P1` 81600, `P1b` 8400, `boot-demo-0` 431, `boot-title-idle` 600, `boot-title-start` 906, `fx-bios-call` 3, `fx-c-input-read` 3, `fx-n-input-read` 3, `fx-queue-short` 1, `fx-start-c79a` 273.
  - 예측 확인: 정확한 비트맵 재관측은 173820을 예측했고, 실측도 173820이다.
  - 수락 항목 중 실패한 항목은 `frontiers_confirmed`다. `boot-demo-0`만 여전히 프레임 431에서 TB 안에 숨은 C7 `1f2a4`에서 조기에 멈추므로 검증기가 이를 확인할 수 없다.
  - 범위: 숨은 직선형 블록은 없다. `4e57e`와 `4e8e6`은 이미 C4가 담당했고, E 헬퍼 `b0c` `e6496`이 라우팅되어 라우팅되지 않은 E 실행 PC는 0에 도달한다.
- [F] 남은 실행 PC: C 261 → 194, E 12 → 0.
- 검증 방법: 결정적 runner(LLM 없음). 이 기록 초안은 local Qwen이 썼고 메인이 검토·수정했다.

## 뒤 단위 변경 기록: select E2(2026-10-24, 작업자 Claude Opus 5.5 / high)

select E2 계약(`animation-machine-select-e2-contract.md`) 결정 1에 따른 기록이다. C6 실행부·시험은 바뀌지 않았다.

- [F] **선언 정지 `e695a`**(`4ed70`의 `28ae` 자식, 메인 결정으로 C9~C13 재측정 때까지 둔 것): 입력 확장 관측에서 실행되어(마지막 목숨 뒤 화면 [I]) E2 block이 되었다. C6 실행부는 `4ed70`에서 A0 := `e695a`를 `28ae`에 넘기기만 하므로 바뀌지 않는다.
- [F] 시험 `animation_machine_player_c6_test.cpp`의 `neighbours[]`(`e695a` 포함)는 C6 범위 밖인지만 확인하므로 그대로 참이다. `4ed70` 행들의 stop은 `28ae`라 그대로다. V1 spec `pc6.py`에는 `e695a`를 정지로 쓰는 곳이 없다(문서 주석뿐). V1 pc6 회귀는 fixture 1,856으로 같다.
- [F] 남은 선언 정지 `1e67a` `1e918` `23c56` `36350` `371f8`은 그대로다(확장 관측에서도 실행되지 않음).
