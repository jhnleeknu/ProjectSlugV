# 영역 E 단위 E2(마지막 목숨 뒤 화면 [I]: 이름 입력 `e695a` 계열 — C6 `28ae` 자식 `e695a`와 그 진입 `e695e`(routing 밖 `28ae` 자식 `e6952`의 `BRA.W` 대상), callback `e69c0`(입력 → 결정 `e6c26` / 지우기 `e6c96` / 다음·이전 글자 `e6cea` / `e6d2e`, 시간 초과), 다시 그리기 `e6a4c`(순위 글자 표 `e637a`, 이름, 커서 `MOVEM.L`, 끝 표시 `e6e25` / `35a2` 상자), 끝 `e6b24`(금지 이름 목록 `e6e32` → `e63fa` 비교 → `e6e2c` 바꿈, `7f` → 공백 `e6416`, 설치 `e6ba0` / `e6bea`, 부모 BYTE 62, `JMP 2a00`), 선수 선택 `e6d8a` / `e6dc8`(D0.W > 1: TRAP #15 `e6d92` / `e6dd0` 경계), WORD 쓰기 `3144`, 129 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §10.5 표의 E2 행(계획 이름 E-1)과 §10.x 메인 결정을 기준으로 삼는다. 구조·공통 규칙은 select E1 계약(`animation-machine-select-e1-contract.md`; 영역 E의 관례, 결정 2 개정: 외부 읽기 queue는 phase H만 읽고 C·N의 queue 장치 읽기는 checked 오류), FR13 / FR12 계약(확장 관측 단위, 정확 bitmap 재관측, V1 natural family = `IO_EXT` pack), C10 계약(실행된 표 칸만 전사, 범위 밖에서 들어오는 실제 분기 대상은 시작), FR5 계약 결정 2(TRAP 자리는 단위 밖 경계)를 따르며 다른 점만 적는다. 단위 이름은 E2, 파일 접두어는 `select_e2`(C++) / `se2`(V1 spec)다. 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다. BIOS 실행, 자연 scheduler, IRQ timing은 주장하지 않는다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창·장치 읽기는 없다. 장치 쓰기도 없다(callee `35a2`·`e84c8`이 장치에 쓴다; 그 실행부 몫). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 FR13 커밋 `7f92b79`(branch `claude/e2-core`; C1~C10, E1, D, FR10~FR13 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `88e68c75bd863b4605891d5204e9adde48fa3168a320c1350662b70b840124e9`, `animation_machine_internal.h` `00dfe0efd2b4192818b1b413cd19bf697776492da5fd42eb2670735f367dcca6`(FR13 계약의 새 값과 같음).
- [F] 관측 입력(읽기 전용): 입력 확장 IO 관측 `artifacts/animation_machine_io_ext`(`observation.json` SHA256 `9da40ac6dcbea3eb…`, compared_sha256 `b5d15d4fcd53555b…`, 검증기 pin 이름 `io-ext`). V1 natural family가 이 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)으로 읽는다(C9 결정 6, FR13 결정 5와 같은 방식).
- [F] 이 단위의 정확 bitmap 재관측 두 벌(scratch, 관측기 `tools/observe_animation_machine_io_ext.py` 수정 없음): `reobs/e2base`(FR13 routing 그대로), `reobs/e2v1`(계획 E2 5 범위를 `--extra-routed`로 가상 routing). 결정 1.
- [F] 시작 목록: **`ms5-scratch/e2/work/starts_e2_final.txt`(129개, 줄마다 하나, SHA256 `41efc72dcc404d449193cdba02842387a5e74251f1ade2338d87bc6a1f00e8aa`)**. 계획 목록 `ms5-scratch/e2/starts_E2.txt`(128개, 공백 구분, SHA256 `3fd9ce2dd183641f48c8ae60093ce193f543352076b8586c27e438b6aba8d91d` = 계획 §10.5의 `3fd9ce2dd183641f`)에 `e695e` 하나를 더한 것이다(결정 1). 실행부의 `case` label 129개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(V1 spec `build()`가 시작 129개와 범위 안 짝수 PC 605개가 모두 `animation_select_e2_block`로 routing됨을 확인, `make test`의 E2 시험이 시작 129개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/e2/`
  - `reobs/run.sh`(재관측 + `dleft.py` + `runstops.py`), `reobs/e2base` `e2v1`(+ `.dleft` `.stops` `.log`), `work/remeasure_ext.dleft` `.stops`(공유 관측 그대로 재측정), `work/udetail_E2_plan.txt` `plan/E-1.dis.txt`(계획 `xplan_v2.json`의 E-1 상세·역어셈블; `tools/xdetail.py`, `MS5_OBS2=fr13/reobs/fr13v1`), `work/e2ranges_plan.txt`(5 범위).
  - `tools/newvis_fr12.py`(`FR12_RANGES=work/e2ranges_plan.txt`; 새로 보인 PC) → `work/newvis_e2v1.txt`, `work/intargets.py` → `work/intargets_e2_v1.out`(범위 안 비시작 PC로 오는 직접 분기), `tools/refs_fr13.py`(`STARTS=work/starts_e2_plan.txt`) → `work/refs_e2_v1.out`(ROM 전체 E2 시작 참조), `tools/flagscan.py` → `work/flagscan_e2_final.txt`, `tools/exitflags.py` → `work/exitflags_e2.txt`, `tools/e2exec.py` → `work/e2exec_base.txt`(재관측의 E2 실행 PC·run·frame), `tools/natscan_e2.py` → `work/natscan_e2_cand.out` `work/natural_e2_cand.json` `work/reinstall_e2_cand.json`, `tools/e2refs_repo.py` → `work/e2refs_repo_v1.out`(저장소의 E2 범위 literal), `work/fxsummary.py`(V1 fixture 요약), `work/v1_regs.sh`, `work/pincheck.py`, `work/mkroot.py`, `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위(결정 1)

- [F] **재측정(FR13 routing, 공유 확장 관측 그대로)** `work/remeasure_ext.dleft`: 실행된 routing 밖 PC E 108 / D 91, 예측 일치 frame **10,374**, 첫 정지 E 6 run(`3144` `e695a` ..: X1 68 frame 960, X1 94 768, X2 68 992, X2 94 800, X4 68 1,268, X4 94 1,108)과 D 2 run(X3 68 1,120 `3643e`, X3 94 958 `7177a`). FR13 계약의 IO 실측(10,374, frontier `e695a` 6 run, `3643e` `7177a`)과 같다.
- [F] **정확 bitmap 재관측(FR13 routing)** `reobs/e2base`(routing `88e68c75`): E 108 / D 91, 예측 10,374, 첫 정지는 위와 run·frame이 같다(FR13 계약의 가상 routing 재관측 `fr13v1`과 줄 단위로 같음).
- [F] **정확 bitmap 재관측(E2 가상 routing, 계획 5 범위)** `reobs/e2v1`: 예측 일치 frame **12,586**(계획 12,586과 같음), 실행된 routing 밖 PC E 0 / D 91(모두 FR14 D-5의 시작), 첫 정지는 D 3 run이다: X2 94 frame 874 `d177e`(FR13 뒤 단위 정지), X3 68 1,120 `3643e`, X3 94 958 `7177a`(모두 FR14). E2만 가졌던 run 5개(X1 68 / 94, X2 68, X4 68 / 94)는 끝(system-return guard)까지 routing 밖 PC가 없다.
  - [F] **숨은 직선 연속 검사**: `e2base`에 없고 `e2v1`에만 보이는 routing 밖 PC는 **없다**(`newvis_fr12.py`에 E2 범위: 12 run 모두 0, `work/newvis_e2v1.txt`). 반복은 한 번으로 수렴했다.
- [F] **범위 밖에서 범위 안 비시작 PC로 들어오는 직접 분기**(`work/intargets_e2_v1.out`): 실제 코드는 **`e6956 BRA.W e695e` 하나**다. `e6952 ST.B 8c(A6); BRA.W e695e`는 FR2 `e693a`(routing됨, `animation_machine_objects_fr2.cpp` 487–488행: `MOVEA.L #e6952,A0; MOVE.W #14,D0; JSR 28ae`, 복귀 `e694c MOVE.W (A7)+,7e(A0)`)가 만드는 `28ae` 자식의 callback이다. `e6952`는 확장 관측에서 실행되지 않고(어느 계획 단위의 시작도 아님) routing 밖으로 남는다. 나머지 줄은 자료를 명령으로 읽은 것이다: `e13ac`..`e1990`은 ASCII 이름 표(바이트 `50 68 61 65 64 72 61 00 …`), `e6930` `e6940`은 `e6928`/`e693c`의 operand, `e69be` `e6b9e` `e6be8`은 E2 명령의 operand, `e6d94` `e6da2`는 TRAP 뒤 자료다.
  - **범위 보정(결정 1)**: `e695a`(`CLR.B 8c(A6)`) block을 둘로 나눠 **`e695e`를 시작으로 더했다**(C10 계약의 "범위 밖 실제 분기 대상은 시작" 규칙). 범위·명령·byte는 바뀌지 않는다(128 → 129 block). `e695a`는 `e695e`로 떨어진다. 이렇게 해 두면 뒤 단위가 `e6952`를 routing할 때 그 `BRA.W`가 E2 block 시작에 닿는다.
- [F] **ROM 전체 참조**(`work/refs_e2_v1.out`, LONG·분기 operand 검색): 범위 밖에서 E2 시작을 가리키는 실제 코드는 `4ed7c MOVEA.L #e695a,A0`(C6, `28ae` 자식)와 `e6956 BRA.W e695e`(위)뿐이다. `3144`를 부르는 곳은 E2 `e69a4 JSR 3144.l`과 routing 밖 `b4b50 JSR 3144.l`이다(`ori.w #$3144,$7a.w` 줄 26개는 자료를 명령으로 읽은 것).
- [F] **계획 특이 항목 대조**(`plan/E-1.dis.txt`, ROM 바이트): TRAP #15 `e6d92` `e6dd0`(`e6d8a`/`e6dc8 CMPI.W #1,D0; BLE`의 fall-through), MOVEM 2(`e6acc MOVEM.L D0-D1/D7/A0,-(A7)`, `e6adc MOVEM.L (A7)+,D0-D1/D7/A0`), 설치 값 `e69c0` `e6ba0` `e6bea`(모두 범위 안, 곧바로 들어감) — 계획과 같다. 계산 점프·`JSR (An)`·DIVU/MULU/MULS·ADDX/SUBX·`28ae`/`2986` 자식은 없다.
- [F] **IO 실행**(`reobs/e2base`, `work/e2exec_base.txt`): E2 시작 가운데 기록된 것 108개, 실행 18,237회(계획 표의 108 / 18,237과 같음), run 8개. 처음 frame(처음 ~ 마지막): X1 68 960..1,043, X1 94 768..851, X2 68 992..1,073, X2 94 800..881, X3 68 1,502..1,599, X3 94 1,310..1,399, X4 68 1,268..1,391, X4 94 1,108..1,231. 기록되지 않은 시작 21개(계획 20 + `e695e`): 같은 TB 안의 직선 연속(`e695e` `e6974` `e6c10`)이거나 이 관측에서 실행되지 않는 분기 쪽(`e6422` `e643a` `e697e` `e69ca` `e6a66` `e6c1a` `e6c44` `e6c8c` `e6cbc` `e6cc4` `e6ce2` `e6cf6` `e6d18` `e6d1e` `e6d38` `e6d48` `e6dc2` `e6e00`). [I] 관측의 X run은 모두 선수 1(WORD 76 = 0)이고, 다음 글자 입력(`e6cf6`)·끝 표시 선택(`e6c44`)·`4836e` Set 쪽(`e69ca`)은 일어나지 않았다.

## E2 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **129 block, 302 명령, 1,210 byte, 5 범위**(시작 목록 SHA256 `41efc72d…`(줄 형식, 최종) / `3fd9ce2d…`(계획 형식, 128), 범위 byte를 이어 붙인 SHA256 `20f150acde3101c8139b7be3ae2b4f6bcd7dd9fba20924322d067e14d94e7ed3`). 짝수 PC 605(내부 476). 기존 routing과 겹침 0(V1 spec `build()`가 범위 안 짝수 PC 605개와 범위 양옆을 확인, 시험 `interior()`).

| 범위(CPU = 파일 오프셋) | byte | 시작 | SHA256(앞 16자) | 내용 [I] |
| --- | --- | --- | --- | --- |
| `3144..314c` | 8 | 1 | `b381d1fdc0c7f64c` | `MOVE.W D0,104cd2.l; RTS`(`e69a4`가 D0 = `2004`로 부름) |
| `e63fa..e6448` | 78 | 13 | `87eb8b3d6749516a` | `e63fa`: D0.W BYTE 비교(`SUBQ.W #1,D0; BCS` → 같음 / `CMPM.B (A0)+,(A1)+; BNE` + `DBRA`; 같으면 `ORI.B #1,CCR`, 다르면 `ANDI.B #fe,CCR`), `e6416`: (A0)의 3 BYTE `7f` → `20`(`DBRA D7`), `e6432`: BYTE 8d = 0이면 `e63ec`로 이름 := `e6e2c`(3 BYTE) |
| `e695a..e6d92` | 1,080 | 108 | `130068e467fd9157` | 시작 `e695a`/`e695e`, callback `e69c0`, 다시 그리기 `e6a4c`, 끝 `e6b24`..`e6c24`, 결정 `e6c26`, 지우기 `e6c96`, 다음 / 이전 글자 `e6cea` / `e6d2e`, 커서 찾기 `e6d66`, 선수 선택 `e6d8a`(`e6d92` TRAP 앞까지) |
| `e6db6..e6dd0` | 26 | 4 | `158e26492973bfad` | 새로 눌림 BYTE `-3354` / `-334e(A5)`(선수 0 / 1), 선수 선택 `e6dc8`(`e6dd0` TRAP 앞까지) |
| `e6df4..e6e06` | 18 | 3 | `bbd79e58e501ed2f` | 입력 기록 `LEA -3358` / `-3352(A5),A0`(선수 0 / 1) |

- [F] **root·진입**(계획 xdetail의 "실행 PC를 줄인 closure 진입"): `3144`, `e695a`. root(`cfam`): `3144` `e63fa` `e695a`(나머지는 `e695a` 함수 안). 설치 값(`MOVE.L #v,(A6)`): `e69c0`(`e69ba`) `e6ba0`(`e6b9a`) `e6bea`(`e6be4`) — 모두 범위 안이고 설치 바로 다음 PC라 곧바로 들어간다. 그 밖의 설치·`MOVE.L #v,84(A6)`는 없다.
- [F] **진입**(현재 routing 기준 호출자):
  - `e695a` ← C6 `4ed70`(`MOVEA.L #e695a,A0; MOVE.W #0,D0; JSR 28ae.l`; `4ed90..4edb6`이 자식 WORD 76 := 부모 WORD 76(선수), WORD 78 := 부모 WORD 7c + 40, LONG 7a := `10de18` / `10de20`). 자식 callback(28ae가 node에 넣음, 다음 dispatch에서 실행).
  - `e695e` ← routing 밖 `e6952`(`e6956 BRA.W`; FR2 `e693a`의 `28ae` 자식, 실행 안 됨). `e695a`의 fall-through.
  - `e69c0` `e6ba0` `e6bea`: 설치 값(위), 다음 frame들의 callback.
  - `3144` ← `e69a4`(E2), routing 밖 `b4b50`.
  - 범위 안 subroutine: `e63fa`(`e6b60`) `e6416`(`e6b80`) `e6432`(`e6b42`) `e6a4c`(`e6be0 JSR`, `e6bca BRA`) `e6c26`(`e69e4`) `e6c96`(`e6a02`) `e6cea`(`e6a1a`) `e6d2e`(`e6a2a`) `e6d66`(`e6996` `e6c8c`, `e6ce6 BRA`) `e6d8a`(`e6a0e`) `e6dc8`(`e69d0`).
- [F] **`28ae` 자식**: E2는 자식을 만들지 않는다. E2 자체가 C6 `4ed70`의 자식(`e695a`)이고, routing 밖 FR2 자식 `e6952`의 분기 대상(`e695e`)을 가진다.

### 계산 점프와 표(결정 2)

- [F] **계산 점프·`JSR (An)`·`JMP (An)`은 없다.** 모든 분기 대상은 정적이다.
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5·E1 결정 5와 같은 규칙):
  - `e6e06` 글자 표(`" ABCDEFGHIJKLMNOPQRSTUVWXYZ.?!&"` 32글자, 칸 1f = 끝 표시 `7f`, 칸 20 = `00`): `e6c26 CMPI.B #7f,(A4,D7.W)`, `e6c44 MOVE.B (A4),(A3,D5.W)`, `e6cac` / `e6cc4 MOVE.B (A4) / 1(A4)`, `e6cf6 MOVE.B (A4,D7.W),D6`, `e6d1e` / `e6d4e MOVE.B (A4,D7.W),(A3,D5.W)`, `e6d78 CMP.B (A4,D6.W),D7`. 색인은 WORD 82(A6) 또는 D6.W이고 **부호 확장**된다(`(An,Dn.W)`). WORD 82는 쓰는 곳(`e6c44` `e6cf6` `e6d18` `e6d3a` `e6d48` `e6d84`)이 0..1f(20 → 0으로 감음, 0 − 1 → 1f)로 묶는다. 표 밖 색인은 원본도 표 앞뒤 byte를 읽는다(검사 없음).
  - `e6e25`(끝 표시 1 BYTE `7f`, `e6afa`), `e6e28`(기본 이름 `"A  "`, `e6982` → `e63ec`), `e6e2c`(바꿀 이름 `"SNK"`, `e643a` / `e6b68` → `e63ec`), `e6e30`(커서 글자 `15`, `e6acc`).
  - `e637a` 순위 글자 LONG 표(11칸 → `e63a6` + 4k: `"1ST."` … `"11TH"`): `e6a6a MOVEA.L (A4,D0.W),A0`, D0.W = 4 × (`e6496` − 1) 또는 4 × WORD 7e(BYTE 8c ≠ 0). [F] `e6496`(C6 routing)은 순위 1..11 또는 −1(`MOVEQ #ff`)을 돌려준다. −1이면 색인 = `fff8`(부호 확장) → `e6372`(기본 순위 표 `e6322..e637a`의 마지막 기록: LONG `99999999` "APE")를 LONG으로 읽는다. 원본 그대로 재현한다(검사 없음).
  - `e6e32` 금지 이름 LONG 목록(10칸 + 0: `"SEX" "SM " "S M" " SM" "   " "AAA" "ASS" "GAY" "FAG" "\x7f  "`; `e6b4c MOVEA.L (A4,D7.W),A0; CMPA.L #0`). D7은 0부터 4씩(`e6b78 ADDQ.W #4`), 끝은 LONG 0.
  - 이 표·글자 값은 모두 자료(글자·포인터)다. 코드 주소로 점프하지 않는다.

### TRAP(결정 3)

- [F] **`TRAP #15` `e6d92` / `e6dd0`**: `e6d8a` / `e6dc8 CMPI.W #1,D0; BLE.W e6db6 / e6df4`의 fall-through다(D0.W > 1, 부호 있는 WORD: 선수 번호가 2 이상). FR5 결정 2와 같이 **단위에 넣지 않는다**(범위 `e695a..e6d92`, `e6db6..e6dd0`가 그 PC를 뺌): `e6d8a`/`e6dc8`이 PC := `e6d92`/`e6dd0`로 끝나고 다음 dispatch가 `unsupported animation machine PC`(전체 rollback)를 낸다. 시험은 `e6d92` `e6dd0`을 정지로만 확인한다(정지 판정이 routing보다 먼저). `TRAP` 뒤 `e6d94..e6db6` `e6dd2..e6df4`는 자료다(역어셈블이 깨짐).
- [F] 그 밖의 TRAP·ROM·RAM 실행은 없다.

### 정수 연산(결정 4)

- [F] **부호 있는 WORD 비교**(`se2_signed_word`: bit 15를 빼서 int32로, 넘침 없음): `e6ac2 CMPI.W #7,84; BGT`, `e6b1a ADDQ.W #1,D7; CMPI.W #3,D7; BLE`(7fff → 8000은 음수라 계속), `e6ba0 SUBQ.W #1,86; CMPI.W #24,86; BLE`, `e6bae ADDQ.W #1,84; CMPI.W #6; BLT`, `e6bc0 CMPI.W #4; BGE`, `e6c5a ADDQ.W #1,80; CMPI.W #3; BLE`, `e6d8a` / `e6dc8 CMPI.W #1,D0; BLE`.
- [F] **WORD 같음**: `e6ab8 CMP.W 80(A6),D7`(D7.W만), `e6ae8 CMPI.W #3,D7`, `e6af0` `e6c6e` `e6c96` `e6cea` `e6d2e CMPI.W #3,80(A6)`. **BYTE 같음**: `e641a CMPI.B #7f,(A0)`, `e6c26 CMPI.B #7f,(A4,D7.W)`, `e6d78 CMP.B (A4,D6.W),D7`(D7.B만), `e6400 CMPM.B`. **LONG 같음**: `e695e`/`e6974`/`e6bf2`/`e6c10 CMPA.L #10de14 / #10de1c,A0`(A0 = LONG 7a − 4, `SUBA.W #4`는 부호 확장한 4를 LONG에서 뺌), `e6b4c CMPA.L #0,A0`.
- [F] **빌림·0 시험**: `e63fa SUBQ.W #1,D0; BCS`(앞 WORD = 0), `e6bea` `e6cbc` `e6d3a SUBQ.W #1,…; BCC`(앞 WORD ≠ 0), `e6a2e SUBQ.W; BNE`, `e6a3c` `e6a44 SUBQ.W; BEQ`(새 WORD), `DBRA`(`e6406` `e6426`: D0.W / D7.W 감소, `ffff`면 끝; 상위 WORD 유지).
- [F] **WORD / BYTE 대상은 하위만 바꾼다**: `SUBQ.W #1,D0`(`e63fa` `e6a60`), `MOVE.W #2,D7`(`e6416`), `MOVE.W 76/78/7e/80/82(A6),Dn`, `ADD.W D0,D0` 두 번(`e6a6a`), `MOVE.W #441/#3/#ff,D1`, `ADDI.W #1/#a0/#40/#a2,D0`, `MOVE.B (A0)+,D2`, `MOVE.B 3(A0),D0`(`e69d4`), `MOVE.B -3354(A5),D0`, `ADDQ.W #1,D7` / `#4,D7` / `#1,D6`, `SUBQ.W #1,D5`(`e6c80`), `MOVE.B (A3,D5.W),D7`, `MOVE.B (A4,D7.W),D6`. `MOVEQ`(`e6aa6` D7 := 0, `e6b46`, `e6b5a` D0 := 3, `e6b0a`/`e6b0c`/`e6b90`/`e6b92`/`e6bd6`/`e6bd8` D2 / D3, `e6d18` D7 := 0, `e6d76` D6 := 0)·`MOVEA`·`LEA`·`ADDA.L`·`MOVEM.L`은 LONG 전체.
- [F] **`BTST #n,D0`**(`e69d8` 4, `e69fa` 5, `e6a12` 3, `e6a22` 2): 데이터 레지스터 BTST는 LONG 모드지만 번호 < 8이라 하위 BYTE의 bit다.
- [F] **`MOVEM.L D0-D1/D7/A0,-(A7)`**(`e6acc`): 높은 주소부터 A0, D7, D1, D0 순으로 넣는다(가장 낮은 LONG = D0, 68000 순서). **`MOVEM.L (A7)+,D0-D1/D7/A0`**(`e6adc`): 낮은 LONG부터 D0, D1, D7, A0, A7 += 16. 모두 `am_push`/`am_pop`(work RAM stack; 홀수 A7은 `program bus requires even WORD/LONG address`).
- [F] **`CMPM.B (A0)+,(A1)+`**(`e6400`): (A0)과 (A1)의 BYTE를 읽고 둘 다 1 증가(A7이 아니므로 1). **`MOVE.B (A3,D5.W),1(A3,D5.W)`**(`e6c80`): 원본 주소 A3 + sext(D5.W), 대상 + 1.
- [F] **`LEA d16(A5),A0`**(`e6dfa` `e6e00`)와 `-3354/-334e(A5)` 읽기·`5e12/5e13(A5)` 쓰기: 16 bit 변위는 부호 확장(`am_index`).

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `2a00`(`e6c1e JMP`) `35a2`(`e6b0e` `e6b94 JSR`, `e6bda JMP`) `3af8`(`e69f0` `e6b28`) `4836e`(`e69c0`) `e63ec`(`e643a` `e6982` `e6b68`, FR2) `e6496`(`e6a54`, C6) `e84c8`(`e6a80` `e6a90` `e6a98` `e6aa0` `e6ad6` `e6b14 JSR`, `e6afa JMP`), RTS 복귀(`3144` `e640a` `e6410` `e6430` `e6446` `e69ca` `e6b22` `e6c24` `e6c44` `e6c68` `e6c90` `e6cf4` `e6d1e` `e6d38` `e6d4e` `e6d84` `e6dbc` `e6dc2` `e6dfa` `e6e00`).
- [F] **뒤 단위 정지 없음.** E2 block이 직선·분기로 닿는 routing 밖 PC는 TRAP `e6d92` `e6dd0`뿐이다. 그래서 V1·실제 ROM 차분의 E2 자신의 뒤 단위 정지(`UNIT_EXITS`)는 비어 있다. 앞 단위들의 남은 정지(FR14 `71874` `d1632` `d177e` `7177a` `71786`, C1~C9의 12개)는 V1 `EXIT_STOPS`에 그대로 둔다(E2 run은 닿지 않음).
- [F] **C6의 선언 정지 `e695a`**(C6 계약 결정 6·"메인 결정", 계획 §9): E2 block이 되었다. 저장소의 시험·검증기·spec에는 이것을 정지로 쓰는 literal이 없다(`animation_machine_player_c6_test.cpp`의 `neighbours[]`는 C6 범위 밖인지만 본다: 그대로 참). 그래서 바뀐 기대값은 없다. C6 계약에 뒤 단위 변경 기록을 더했다.
- [F] 직선 fall-through로 범위를 벗어나는 곳: `e6d8a` → `e6d92`, `e6dc8` → `e6dd0`(TRAP 경계). 재관측에서 새로 보인 PC가 없어 가려진 연속은 없다(결정 1).

### block 경계·복귀를 넘는 flag(결정 5)

block 첫 명령부터 flag를 정하는 명령까지 훑었다(`work/flagscan_e2_final.txt`). 그리고 E2 출구 대상·object loop 복귀 PC(`2a00` `35a2` `3af8` `4836e` `e63ec` `e6496` `e84c8` `2ac2`)에서 E2가 남긴 flag를 읽는 곳을 따로 훑었다(`work/exitflags_e2.txt`: 없음). X를 읽는 명령은 없다.

- [F] **C 소비 block 3개**(Clear 쪽 / Set 쪽; Unknown C면 `select e2 caller requires known carry`):
  - `e69c6 BCC.W e69cc / e69ca`: routing된 `4836e`(C2 계약의 C 생산자: `BTST #2,5683(A5)`가 1이면 `ANDI.B #fe,CCR` Clear, 0이면 `ORI.B #1,CCR` Set)의 C.
  - `e69e8 BCS.W e6b24 / e69ec`: E2 `e6c26`의 C(`e6c44` `e6c68 ORI.B #1,CCR; RTS` Set, `e6c90 ANDI.B #fe,CCR; RTS` Clear).
  - `e6b64 BCC.W e6b78 / e6b68`: E2 `e63fa`의 C(`e640a ORI.B #1,CCR; RTS` Set = 같음, `e6410 ANDI.B #fe,CCR; RTS` Clear = 다름).
- [F] **C 생산 block 5개**(실행부가 그 block 안에서 C를 정함): Set `e640a` `e6c44` `e6c68`, Clear `e6410` `e6c90`. `e6c90`의 `ANDI.B #fe,CCR`은 C만 지우고 앞 `e6d66`의 N / Z / V는 남기지만 `e69e8 BCS`는 C만 읽는다.
- [F] **dispatcher carry 보존 목록**: 소비자 3개(`e69c6` `e69e8` `e6b64`)만 더했다. 생산자 다음의 RTS 복귀 PC가 곧 소비자이므로 C가 그대로 전달된다. 그 밖의 E2 block은 Unknown이다(dispatcher 기본).
- [F] **Z / N이 경계를 넘는 곳은 없다.** 복귀 뒤 첫 명령이 flag를 다시 정한다: `e69d4 MOVE.B`, `e6a12 BTST`(D0은 `e6d8a`가 `MOVE.B`로 줌), `e699a MOVE.W`, `e6b84 MOVE.W`, `e6a86` `e6a96` `e6a9e` `e6aa6` `e6b1a`(`e84c8` 뒤), `e6b46 LEA`/`MOVEQ`, `e6be4 MOVE.L`, `e6a60 SUBQ`. RTS로 돌려주는 flag(`e6430` `e6446` `e6b22` `e6c24` `e6cf4` `e6d1e` `e6d38` `e6d4e` `e6d84` `e6dbc` `e6dc2` `e6dfa` `e6e00` `3144`)를 읽는 쪽은 없다.

### IO 실행 run과 frame

- [F] 실행 run 8개(X1~X4 × case 68·94), 처음 frame은 위 "재확인과 범위". E2 node는 pool `100800..104c00`의 자식 node 하나다(run마다 `101330` `101eac` `1014b8` `1014b8` `102344` `1017c8` `101d24` `101950`; `work/natscan_e2_cand.out`). frame 시작 상태의 callback은 `e69c0`(run당 22~64 frame) → `e6ba0`(23) → `e6bea`(36)이고, `e695a`는 생성 frame 안에서 곧바로 실행돼 frame 시작 상태에 남지 않는다. 부모 C6 node `1009a8`은 그동안 `4edc0`(BYTE 62 대기), 끝난 뒤 `4ee04`다.
- [F] **IO 예측(E2 연결)**: 10,374 → **12,586**(+2,212; 재관측 `reobs/e2v1`, 계획과 같음). 첫 정지는 D 3 run(X2 94 874 `d177e`, X3 68 1,120 `3643e`, X3 94 958 `7177a`; 모두 FR14)이다. [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다.
- [F] 원래 IO 관측은 E2 코드를 실행하지 않는다(계획 §10.4: X run에서만 실행). 일치 173,966은 그대로여야 한다(작업자는 돌리지 않음; 메인 runner).

## block 의미(요약)

- **`3144`**: WORD `104cd2` := D0.W, `RTS`.
- **`e63fa`**(D0.W BYTE 비교, A0 = 금지 이름, A1 = 이름): D0.W −= 1, 빌림(0) → `e640a`(Set); `e6400`: BYTE (A1) ≠ (A0) → `e6410`(Clear), 둘 다 + 1; `e6406`: `DBRA D0,e6400` → 끝나면 `e640a`.
- **`e6416`**: D7.W := 2; `e641a`: BYTE (A0) = `7f` → `e6422`(:= `20`); `e6426`: A0 += 1, `DBRA D7` → `e6430 RTS`.
- **`e6432`**: BYTE 8d ≠ 0 → `e6446 RTS`, 아니면 `e643a`: A0 := `e6e2c`, D0.W := 3, `JSR e63ec`(이름 := `"SNK"`).
- **`e695a`**: BYTE 8c := 0 → `e695e`: A0 := LONG 7a − 4; = `10de14` → `e6970`(BYTE `5e12(A5)` := ff); `e6974`: = `10de1c` → `e697e`(BYTE `5e13(A5)` := ff); `e6982`: WORD 80 := 0, A1 := LONG 7a, A0 := `e6e28`, D0.W := 3, `JSR e63ec`(기본 이름); `e6996`: `JSR e6d66`; `e699a`: WORD 84 := f, D0.W := `2004`, `JSR 3144`; `e69aa`: WORD 88 := `258`, 8a := `12c`, BYTE 8d := 0, (A6) := `e69c0`(들어감).
- **`e69c0`**(callback): `JSR 4836e`; `e69c6`(C): Set → `e69ca RTS`; Clear → `e69cc`: D0.W := WORD 76, `JSR e6dc8`(A0 := 선수 입력 기록); `e69d4`: D0.B := BYTE 3(A0), bit 4 → `e69e0`(BYTE 8d := ff, `JSR e6c26` → `e69e8`(C): Set → `e6b24`(끝), Clear → `e69ec`(소리 `1a6c`, `JSR 3af8`) → `e6a2e`); bit 5 → `e6a02`(`JSR e6c96`) → `e6a2e`; 아니면 `e6a0a`: D0.W := WORD 76, `JSR e6d8a`(D0.B := 새로 눌림 BYTE); `e6a12`: bit 3 → `JSR e6cea`, 아니면 `e6a22`: bit 2 → `JSR e6d2e`; `e6a2e`: WORD 84 −= 1, 0이면 := f; `e6a3c`: WORD 88 −= 1 = 0 → `e6b24`; `e6a44`: WORD 8a −= 1 = 0 → `e6b24`; `e6a4c`(다시 그리기).
- **`e6a4c`**: BYTE 8c ≠ 0 → `e6a66`(D0.W := WORD 7e), 아니면 `e6a54`(A0 := LONG 7a − 4, `JSR e6496`) → `e6a60`(D0.W −= 1); `e6a6a`: D0.W ×= 4, A4 := `e637a`, A0 := LONG (A4 + sext D0.W), D0.W := WORD 78, D1.W := `441`, 글자 3개(`e6a86`: D1.W := 3, D0.W += 1)를 `e84c8`로 그림; `e6aa6`: D0.W := WORD 78 + `a0`, D1.W := `441`, A0 := LONG 7a, D7 := 0; `e6ab8`: D2.B := (A0)+, D7.W = WORD 80이고 WORD 84 ≤ 7(부호)이면 `e6acc`(MOVEM 저장, 커서 글자 `e6e30`, `e6adc` MOVEM 복원, D0.W += 40 → `e6b1a`); 아니면 `e6ae8`: D7.W = 3이고 WORD 80 = 3이면 `e6afa`(끝 표시 `e6e25`를 `JMP e84c8`), D7.W = 3이고 80 ≠ 3이면 `e6b06`(`35a2` 상자 D2 = 2, D3 = 2), 그 뒤 `e6b14 JSR e84c8`; `e6b1a`: D7.W += 1, ≤ 3(부호) → `e6ab8`, 아니면 `e6b22 RTS`.
- **`e6b24`**(끝): 소리 `1a6d`; `e6b2e`: WORD 80 := ffff, 84 := 0, 86 := `3c`, A1 := LONG 7a, `JSR e6432`; `e6b46`: A4 := `e6e32`, D7 := 0; `e6b4c`: A0 := LONG (A4 + sext D7.W), 0 → `e6b7c`; `e6b5a`: A1 := LONG 7a, D0 := 3, `JSR e63fa` → `e6b64`(C): Set → `e6b68`(이름 := `"SNK"`) → `e6b78`: D7.W += 4 → `e6b4c`; `e6b7c`: A0 := LONG 7a, `JSR e6416`; `e6b84`: `35a2` 상자(D0.W := WORD 78 + `a2`, D2 = 8); `e6b9a`: (A6) := `e6ba0`(들어감).
- **`e6ba0`**(깜박임): WORD 86 −= 1, ≤ 24(부호) → `e6be0`(`JSR e6a4c`, (A6) := `e6bea`, 들어감); 아니면 `e6bae`: WORD 84 += 1, ≥ 6(부호)이면 := 0; `e6bc0`: 84 ≥ 4(부호) → `e6bce`(`35a2` 상자 D2 = b, `JMP`), 아니면 `e6bca BRA e6a4c`.
- **`e6bea`**(대기): WORD 86 −= 1, 앞 값 ≠ 0 → `e6c24 RTS`; 0 → `e6bf2`: 부모 LONG c(A6)의 BYTE 62 := ff, A0 := LONG 7a − 4; `10de14` → BYTE `5e12(A5)` := 0, `10de1c` → BYTE `5e13(A5)` := 0; `e6c1e JMP 2a00`(node 제거).
- **`e6c26`**(결정): WORD 84 := f, 8a := `12c`, D7.W := WORD 82, A4 := `e6e06`; 표[D7.W] = `7f` → `e6c44`(WORD 82 := 0, 이름[80] := 표[0], Set); 아니면 `e6c5a`: WORD 80 += 1, > 3(부호) → `e6c68`(Set); `e6c6e`: 80 = 3 → `e6c90`(Clear); `e6c78`: D5.W := 80, 0 → `e6c8c`; `e6c80`: 이름[80] := 이름[80 − 1]; `e6c8c`: `JSR e6d66`; `e6c90` Clear.
- **`e6c96`**(지우기): 84 := f, 8a := `12c`, 80 ≠ 3이면 `e6cac`: 이름[80] := 표[0]; `e6cbc`: WORD 80 −= 1, 빌림 → `e6cc4`(80 := 0, 이름[0] := 표[1]); `e6cda`: 80 = 0 → `e6ce2`(BYTE 8d := 0); `e6ce6 BRA e6d66`.
- **`e6cea`**(다음 글자): 80 = 3 → `RTS`; `e6cf6`: 84 := f, 8a := `12c`, WORD 82 += 1, D7.W := 82, D6.B := 표[D7.W], 0이면 `e6d18`(82 := 0, D7 := 0); `e6d1e`: 이름[80] := 표[D7.W], `RTS`. **`e6d2e`**(이전 글자): 80 = 3 → `RTS`; `e6d3a`: 8a := `12c`, WORD 82 −= 1, 빌림 → `e6d48`(82 := 1f); `e6d4e`: D7.W := 82, A4 := `e6e06`, 이름[80] := 표[D7.W], `RTS`.
- **`e6d66`**(커서 글자 찾기): A3 := LONG 7a, D5.W := 80, D7.B := 이름[80], A4 := `e6e06`, D6 := 0; `e6d78`: 표[D6.W] = D7.B → `e6d84`(WORD 82 := D6.W, `RTS`); `e6d80`: D6.W += 1 → `e6d78`.
- **`e6d8a`** / **`e6dc8`**: D0.W ≤ 1(부호) → `e6db6` / `e6df4`, 아니면 TRAP 경계. `e6db6`: D0.W ≠ 0 → `e6dc2`(D0.B := BYTE `-334e(A5)`), 아니면 `e6dbc`(BYTE `-3354(A5)`); `RTS`. `e6df4`: D0.W ≠ 0 → `e6e00`(A0 := A5 − `3352`), 아니면 `e6dfa`(A5 − `3358`); `RTS`.
- [I] 이름: 7a = 이름 버퍼(그 앞 LONG = 점수), 76 = 선수, 78 = 화면 위치, 7e = 순위(FR2 자식), 80 = 커서 칸(0..2, 3 = 끝 칸), 82 = 글자 색인, 84 = 깜박임, 86 = 끝 뒤 대기, 88 / 8a = 시간 초과, 8c = 순위를 7e에서 읽음(FR2 자식 `e6952`), 8d = 입력 있음. 원본 이름이 아니다.

## 공통 규칙·native 검증 계획

select E1, FR2..FR13, C1~C10 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_select_e2.cpp`, 함수 `animation_select_e2_block`. 오류 문자열은 `unsupported animation select e2 PC`(범위 안 내부 PC 직접 진입), `select e2 caller requires known carry`(C 소비 block 3개에 Unknown C) 두 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다(TRAP 경계 다음 dispatch의 `unsupported animation machine PC` 포함).
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(5 범위, FR13 줄 뒤; `)ok=animation_select_e2_block(c);`를 같은 줄에 둔다), `carry_preserving_pc`의 FR13 묶음 뒤에 주석 달린 case 묶음 하나(소비자 3개), `animation_machine_internal.h`에 선언 하나(FR13 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# select E2 refresh:` 주석).
- **설치 값.** 3개 모두 쓰고 그 값으로 곧바로 들어간다(`se2_install(c,v,v)`).
- **자료 읽기**(live bus): node field(A6: LONG `0`(설치) `c`(부모) `7a`(이름 버퍼), WORD `76` `78` `7e` `80` `82` `84` `86` `88` `8a`, BYTE `8c` `8d`), 부모 BYTE `62`(쓰기), 이름 버퍼 BYTE(A3 / A0 / A1, 그 앞 LONG은 `e6496`이 읽음), A5 BYTE `5e12` `5e13`(쓰기) `-3354` `-334e`, 선수 입력 기록 BYTE `3(-3358 / -3352(A5))`, WORD `104cd2`(쓰기), 스택(MOVEM), 고정 ROM(위 "계산 점프와 표"). 단위 시험은 고정 ROM 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): 기본 순위 표 자리 `e6322..e637a`(음수 색인으로만 읽힘), 순위 글자 표 `e637a..e63d2`, 글자 표·글자·금지 이름 목록 `e6e06..e6e86`. V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** 위 "정수 연산(결정 4)". 색인 `(An,Dn.W)`는 An + sext(Dn.W)(+ d8).

## seed·fixture

- **V1(`tools/unit_fixture_specs/se2.py`)**: FR13 spec의 공용 부분(routing 해석, `first_unrouted`, carry oracle, chain / node / natural / callee family)을 그대로 쓰고 단위 부분을 바꿨다. world: LONG 7a = 이름 버퍼(`10de18` / `10de20` 대부분, 아니면 선언 기록)와 그 3 글자(표 글자 대부분, 금지 이름 25%)·점수 LONG, LONG c = 부모, WORD 76 = 0 / 1 대부분(2 / ffff / 8000: TRAP 경계·음수), WORD 80 = 0..3 대부분, 82 = 0..20 대부분, 7e = 0..a, BYTE 8c = 0 대부분, BYTE `10d683`(4836e bit 2), 입력 BYTE `104cab` `104cac` `104cb1` `104cb2`.
  - block: 시작 129개(소비자 3개 제외). hint(경계): 위 "정수 연산"의 부호·빌림·WORD / BYTE 경계, 점수 기록 `10de14` / `10de1c`, 입력 bit, 금지 이름, 표 끝 / 감음, mirror node.
  - chain: `e69c0` → `e69c6`(`4836e`), `e69e0` → `e69e8`(`e6c26`), `e6b5a` → `e6b64`(`e63fa`). 세 사슬 모두 두 C 값이 실제 생산자로 나온다.
  - node: `e695a` `e695e` `e69c0` `e6ba0` `e6bea`((A6) := 진입).
  - natural: 확장 관측 pack frame 352개(run마다 `e69c0`의 모든 frame, `e6ba0` / `e6bea`의 처음·4번째·12번째·마지막 frame; scratch `natscan_e2.py`). reinstall 16개: run마다 첫 `e69c0` frame의 자연 node에 callback LONG `e695a`를 쓰거나, `e695e` + BYTE 8c := ff + WORD 7e(순위 1..a; FR2 `e693a`가 자식 `e6952`에 주는 값)를 쓴다. [I] 이미 초기화된 node를 다시 초기화하는 world이며 native와 C++가 같은 상태를 받으므로 비교는 유효하다(E1 결정과 같음).
  - callee: `3144` `e63fa` `e6416` `e6432` `e6a4c` `e6c26` `e6c96` `e6cea` `e6d2e` `e6d66` `e6d8a` `e6dc8` `e6ab8` `e6b24` `e6a2e` `e6a0a` `e69cc`.
  - error: 내부 PC 476, 홀수 PC, Unknown C 3, TRAP 경계 4(`e6d8a`/`e6dc8` 직접, `e6a0a`/`e69cc`를 거쳐), 홀수 node / stack(MOVEM 넣기·꺼내기, RTS) / 표 색인, 실행 뒤 실패(`e695a` → `e695e` 홀수 node, `e6ae8` → `e6b06` 홀수 stack).
  - negative: RAM bit, 레지스터, stop, queue 추가.
- **단위 시험(Unicorn 생성기, `tools/generate_animation_machine_select_e2_test_table.py`)**: FR13 생성기 꼴. 합성 physical byte(원본 자료 아님, 자료 영역만): `e6322..e63d2`(기본 순위 표 자리 11 기록을 순위 글자 포인터 + 4 BYTE로, 순위 글자 표 11 LONG(칸 k → 글자 (3k) mod 11), 글자 11개), `e6e06..e6e86`(글자 표: 칸 0 `-`, 1..1a `Z`..`A`, 1b..1e `#$%+`, 1f `7f`, 20 `00`; 기본 이름 `"Q? "`, 바꿀 이름 `"XYZ"`, 커서 `5f`, 금지 이름 목록 4칸 + 0과 그 이름 `"QWE" "RTY" "\x7f\x7f\x7f" "UIO"`). 행: single(시작 126개 × 들어오는 C 3가지, 모든 분기 양쪽), path(125 진입), 사슬 3개(두 C 값), 선언 C(소비자 3 × 2), error 31(실패 PC 8개 이동), zero-step, 내부 PC 476 정확 오류, rollback 탐침, 경계 stop(routing된 출구 7개와 TRAP 2개 전부). 손 규칙(`rules_a`..`rules_d`): `3144` WORD 쓰기, `e63fa` 빌림·CMPM 증가·DBRA·Set / Clear, `e6416` `7f` → 공백·D7 상위 유지, 선수 선택의 부호 WORD 비교(ffff / 8000 / 10001 / 2 / 7fff)·TRAP 경계·하위 WORD 시험, A5 음수 변위(A5 = `1f8000` mirror), 점수 기록 `10de14` / `10de1c` / LONG A0, 입력 bit 4 / 5 / 3 / 2, 시간 초과 count, 순위 색인(부호 확장 `fffe` → `e6372`, WORD ×4의 상위 유지, 표 밖 색인의 ROM 오류), `CMP.W 80,D7`의 하위 WORD, `CMPI.W #7,84`의 부호, MOVEM 순서와 복원, `ADDI.W #40` 상위 유지, `e6ae8`/`e6af0`, 끝 표시, `35a2` 상자 D1.W / D2 / D3, `e6b1a` 부호 BLE(7fff → 8000), 글자 표 색인의 부호 확장(WORD 82 `f51c` → `e6322`)과 표 밖 색인(`100`)의 ROM 오류, `e6c44` 끝 표시 저장·Set, `e6c5a` 부호 BLE, `e6c80` 앞 글자 복사(D5.W 0 → ffff), 지우기 빌림, 다음 글자 감음(MOVEQ #0,D7 LONG), 이전 글자 빌림 → 1f, 대상 `(A3,D5.W)`의 부호 확장(mirror `1f0010` − 10), 커서 찾기(D7.B만, 색인 부호 확장, ADDQ.W), 금지 이름 목록의 부호 확장·LONG `10000`·목록 끝, 소비자의 선언 C 두 값과 Unknown C 오류, 깜박임·대기의 부호 비교와 빌림, 끝(부모 BYTE 62, `5e12` / `5e13` 지우기, `JMP 2a00`), 설치 두 곳.

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `88e68c75bd863b4605891d5204e9adde48fa3168a320c1350662b70b840124e9` → `b376d62144aeacdbbfbb0a36b265669b896f9e2f63eaa1b363f77e664366eeed`, `animation_machine_internal.h` `00dfe0efd2b4192818b1b413cd19bf697776492da5fd42eb2670735f367dcca6` → `4592d7ce786f860f34fbf253c234018e45329eccdd3ce5e83d2ee7f39dfd1b99`(옛 값은 `# select E2 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 작업 트리와 scratch clone root에서 확인했다(아래 "검증 수치").
- [F] `tools/verify_animation_machine.py` `SOURCES`에 `animation_machine_select_e2.cpp`.
- [F] **바뀌지 않음(확인)**: 저장소 engine 소스·시험·tools·spec·`docs/analysis/data`·`config`에서 E2 범위 안 PC와 이웃(`e6d92` `e6dd0` `e6952`)을 쓰는 4·5자리 hex literal을 전수 검색했다(`tools/e2refs_repo.py` → `work/e2refs_repo_v1.out`).
  - 범위 끝·값으로만 쓰는 곳: H2 시험 RANGES `{0x313c,0x3144}`(범위 끝), FR2 시험·spec RANGES `e63ec..e63fa` `e693a..e6952`(범위 끝)과 `e693a` 행의 자식 값 `e6952`(stop은 `28ae`), C6 시험의 `4ed70` 행(자식 값 `e695a`, stop `28ae`)과 `neighbours[]`(`!in_ranges`만 확인), FR2 실행부 `e693a`의 A0 값, C6 실행부 `4ed70`의 A0 값, `verify_animation_machine_io.py`의 영역 경계 `0xe6400 <= r < 0xe7000`(영역 E 정의, PC 기대값 아님).
  - 검증기(`tools/verify_animation_machine_*.py`)에는 E2 PC를 이웃·탐침·"unsupported PC"·frontier 기대값으로 쓰는 literal이 없다. 그래서 바꾼 검증기는 `CPP_PINS`와 `SOURCES`뿐이다. [U] artifact에서 기대값을 읽는 검증기의 동적 경로는 메인의 통합 sweep이 확인한다.
  - V1 spec의 `ROUTED_LATER` / `EXIT_STOPS`: E2 PC를 정지로 가진 spec은 없다(C6의 선언 정지 `e695a`는 문서에만 있었다). 앞 단위 시험의 오류 행·V1 오류 fixture 가운데 E2 PC를 대상으로 하는 것도 없다.
  - `make -j4 all test`가 E2 시험 말고 기존 시험이 모두 그대로 통과함을 확인했다(아래). V1 회귀 pc1–pc10, se1, fr9–fr13도 통과했다(아래).
- [F] 앞 단위 계약의 뒤 단위 변경 기록: C6 계약(`e695a`가 E2 block), FR2 계약(자식 `e6952`의 분기 대상 `e695e`가 E2 시작, `e6952`는 routing 밖 그대로).
- [I] 원래 IO 관측과 frame 비교(d1·controller·irq·demo)는 E2 코드를 실행하지 않으므로 결과가 같아야 한다. 메인 runner가 확인한다.

## 결정

1. **범위: 129 block, 5 범위(계획 128 + `e695e`).** 가상 routing 재관측에서 새로 보인 PC가 없고(숨은 직선 block 0), 범위 밖에서 범위 안 비시작 PC로 오는 실제 분기는 routing 밖 `28ae` 자식 `e6952`의 `BRA.W e695e` 하나라 `e695e`를 시작으로 더했다(범위·명령 불변). 예측 12,586(+2,212), 첫 정지 D 3(FR14).
2. **계산 점프·표.** 계산 점프는 없다. 표(`e637a` `e6e06` `e6e32`)는 live bus로 읽고 상한을 검사하지 않는다(원본과 같음). 색인은 부호 확장한다.
3. **TRAP #15 `e6d92` / `e6dd0`**: 단위 밖 경계(FR5 결정 2). `e6d8a`/`e6dc8`이 PC := TRAP PC로 끝나고 다음 dispatch가 전체 rollback.
4. **정수 연산**: 부호 있는 WORD 비교는 정확한 부호 비교, WORD / BYTE 대상은 하위만, MOVEM은 68000 순서, CMPM은 두 포인터 모두 + 1.
5. **flag.** C 소비자 3개는 known C를 읽거나 checked 오류. 생산자 5개(Set `e640a` `e6c44` `e6c68`, Clear `e6410` `e6c90`)는 block 안에서 C를 정한다. dispatcher carry 보존 목록에 소비자 3개만 더했다. Z / N 경계는 없다(RAM·고정 ROM에서 다시 계산할 것이 없음).
6. **V1 natural family.** 확장 관측 pack의 E2 callback frame 352개 + reinstall 16개(`e695a`, `e695e`).
7. **입력 port.** E2는 장치를 읽지 않는다(입력은 이미 RAM에 있는 기록 BYTE). E1 결정 2(개정)의 queue 규칙과 충돌하지 않는다.
8. **다음.** E2 연결로 확장 관측 IO 12,586(+2,212)을 메인 runner가 확인한다. 다음 단위는 FR14(`3643e` `7177a` `d177e` 등, 3 run). E2 뒤 E 영역의 실행된 routing 밖 PC는 0이다(재관측 `e2v1`).

## 미확인

- [U] node field·전역 값의 의미(위 "block 의미"의 이름), `3144`의 WORD `104cd2`(`2004`)가 무엇을 바꾸는지, `4836e`의 BYTE `5683(A5)` bit 2, 입력 기록 BYTE의 의미(새로 눌림 / 반복). 이름(이름 입력, 순위, 금지 이름, 깜박임)은 동작과 ROM 글자에서 붙인 [I]이다.
- [U] 선수 2(WORD 76 = 1) 쪽(`e6dc2` `e6e00`)과 다음 글자(`e6cf6` `e6d18` `e6d1e`)·끝 표시 선택(`e6c44`)·`4836e` Set(`e69ca`)은 IO 관측에서 실행되지 않았다. V1 선언 상태·reinstall·실제 ROM 차분·단위 시험으로만 확인했다.
- [U] `e6496`이 −1을 돌려주는 경우(순위 밖)의 `e6372` 읽기는 원본 그대로 재현하지만, 실제 게임에서 그 경로가 나오는지(`4ed6a TST.W D0; BMI.W 4edf2`가 자식을 만들지 않게 막는 것으로 보임 [I])는 확인하지 않았다.
- [U] `e6952`(FR2 `e693a`의 자식)가 실행되는 조건(순위 표 화면의 다른 경로로 보임 [I]). 이 단위는 그 분기 대상만 시작으로 둔다.
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC).
- [U] natural / reinstall fixture의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C10, FR10~FR13, E1과 같음).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_select_e2.cpp`(case label 129 = `starts_e2_final.txt`와 집합 일치; 공용 함수 `se2_get` `se2_put` `se2_signed_word` `se2_word` `se2_decrement` `se2_carry` `se2_install` `se2_record` `se2_cursor` `se2_store_char` `se2_text` `se2_box`), `engine/tests/animation_machine_select_e2_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_d`), `tools/generate_animation_machine_select_e2_test_table.py`(생성기; FR13 생성기 꼴, V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 50초), `tools/unit_fixture_specs/se2.py`(V1 spec; FR13 spec의 공용 부분, 단위 부분 교체, `CONSUMERS`(3), `CLEAR_SET`(`e6410` `e6c90`), `SET_SET`(`e640a` `e6c44` `e6c68`), `TRAPS`(`e6d92` `e6dd0`), `EXIT_STOPS`(앞 단위의 남은 17), `CHAINS`(3), `NODE_ENTRIES`(5), `NATURAL`(352 frame), `REINSTALL`(16)). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `work/starts_e2_final.txt`(SHA256 `41efc72d…`).

- **`3144..314c`(1)**: `3144`
- **`e63fa..e6448`(13)**: `e63fa e6400 e6406 e640a e6410 e6416 e641a e6422 e6426 e6430 e6432 e643a e6446`
- **`e695a..e6d92`(108)**: `e695a e695e e6970 e6974 e697e e6982 e6996 e699a e69aa e69c0 e69c6 e69ca e69cc e69d4 e69e0 e69e8 e69ec e69f6 e69fa e6a02 e6a06 e6a0a e6a12 e6a1a e6a1e e6a22 e6a2a e6a2e e6a36 e6a3c e6a44 e6a4c e6a54 e6a60 e6a66 e6a6a e6a86 e6a96 e6a9e e6aa6 e6ab8 e6ac2 e6acc e6adc e6ae8 e6af0 e6afa e6b06 e6b14 e6b1a e6b22 e6b24 e6b2e e6b46 e6b4c e6b5a e6b64 e6b68 e6b78 e6b7c e6b84 e6b9a e6ba0 e6bae e6bbc e6bc0 e6bca e6bce e6be0 e6be4 e6bea e6bf2 e6c0c e6c10 e6c1a e6c1e e6c24 e6c26 e6c44 e6c5a e6c68 e6c6e e6c78 e6c80 e6c8c e6c90 e6c96 e6cac e6cbc e6cc4 e6cda e6ce2 e6ce6 e6cea e6cf4 e6cf6 e6d18 e6d1e e6d2e e6d38 e6d3a e6d48 e6d4e e6d66 e6d78 e6d80 e6d84 e6d8a`
- **`e6db6..e6dd0`(4)**: `e6db6 e6dbc e6dc2 e6dc8`
- **`e6df4..e6e06`(3)**: `e6df4 e6dfa e6e00`

## 검증 수치

작업자 최종 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j4 all test`(최종 실행부·시험): 종료 0, 경고 0, Assert 0, Python 310 OK, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄(`trial_logs/make_final.log`). E2 시험 줄: `animation machine select e2: 844 fixtures (526 single-block, 263 path, 18 producer chain, 6 declared C, 31 checked error (8 with a later failing PC), 76 kept C), 129 blocks, 3483 calls, 105067 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 출구 중 stop이 아닌 것 0, 실제 사슬 3개(`e69c0`→`e69c6`(`4836e`), `e69e0`→`e69e8`(`e6c26`), `e6b5a`→`e6b64`(`e63fa`); 모두 두 C 값). 생성기를 다시 돌려 E2 시험 파일이 바이트 단위로 같음을 확인했다(SHA256 `8c95dfdd66d42335…`, `trial_logs/gen_repro.log`). 기존 시험은 하나도 바뀌지 않았다(모두 그대로 통과).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, E2 시험): 빌드 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_build.log` `ubsan_se2.log`).
- [F] V1 se2(작업자, `--workers 3`): fixture 1,573개(match 1,069, error 494, mismatch 10; natural 352 + reinstall 16) failed 0, `ok` true, 방문 시작 129/129, 빠진 후속 없음, 도달 못한 분기 결과 없음, carry oracle Unknown/Clear/Set = 967/72/30(`work/v1/v1_se2.log`, `work/v1/v1_se2/report.json`). 첫 시도(`se2_try1`)는 빠진 후속 둘(`e6974` → `e697e`, `e6c10` → `e6c1a`: 직접 진입 block의 A0 = `10de1c`)뿐이어서 A0 hint를 더했다(`se2_try2` 이후 빠진 것 없음).
- [F] V1 회귀(작업자, `work/v1_regs.sh`, `--workers 3`; `work/v1/v1_regs.txt`): pc1 1,264, pc2 1,743, pc3 1,829, pc4 1,873, pc5 1,755, pc6 1,856, pc7 2,077, pc8 986, pc9 2,347, pc10 1,334, se1 2,102, fr9 1,415, fr10 2,170, fr11 2,170, fr12 2,302, fr13 2,126(모두 failed 0, `ok` true; FR13 기록과 같은 수). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1/+2, 크기, WORD/BYTE → LONG, 복귀 PC·호출 대상, carry swap·tag, mask, 상수·설치 값, 상자·글자 인자, 점수 기록·A5 변위) + 손으로 고른 helper·block 변이(부호 WORD 비교의 무부호화, 감소 mask, 점수 기록 −2 / WORD, 커서 D5 LONG, 글자 저장의 부호 확장 없음·d8 없음, text 증가 없음·D2 LONG, 상자 D1/D2/D3, `3144` LONG, `e63fa` BYTE 시험, CMPM 증가, DBRA 0 / LONG, MOVEM 순서·D1/D7·WORD, 순위 색인 부호 확장 없음·LONG, 끝 표시 A0, `e6b1a`/`e6ba0`/`e6bae`/`e6bc0`/`e6c5a`/`e6ac2`/`e6d8a` 무부호·엄격·새 값, 금지 목록 부호 확장·WORD 시험, 대상 +1 없음, 빌림 시험의 새 값, 감음 D7 WORD, 커서 찾기 WORD·부호 확장, 하위 WORD 시험의 LONG) + dispatcher carry 목록 3개·범위 9개를 적용해 만든 것, 563개; `--workers 4`): 1회째 `killed 534 of 563`(`trial_logs/mut_first.log`). 생존 29개 중 27개는 시험 빈틈이었고 규칙(`rules_a`..`rules_d`)과 합성 기본 순위 표(`e6322..e637a`: 음수 색인 `fffe` → `e6372`, WORD 82 `f51c` → `e6322`의 부호 확장을 확인하려고)로 메웠다(`trial_logs/mut_gaps.log`: `killed 26 of 29`, 그 뒤 `e6ae8-mask`는 `35a2` 상자 경로가 같은 정지에 닿아 살았으므로 port·D1·A7까지 보는 규칙으로 바꿔 `killed 1 of 1`). 남은 2개는 동치다(`mut/equivalents.txt`: `put-nomask` — `am_write`가 size byte만 씀, `dec-nomask` — 감소 값 `now`의 위 bit를 읽는 곳이 없음(WORD 저장, 0 비교, `se2_signed_word`)). 규칙을 더한 뒤 전체 2회째 `killed 561 of 563`(`trial_logs/mut_second.log`), 남은 2개가 동치 목록과 같다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`, 메인 runner용), `real_se2.py`(FR13 harness에 E2 world(`se2_world`: LONG 7a 이름 버퍼와 글자·점수, WORD 76 / 78 / 7e / 80 / 82 / 84 / 86 / 88 / 8a, BYTE 8c / 8d, BYTE `10de12` / `10de13`, 입력 기록 `104ca8..104cb3`)·소비자 3·선언 정지(TRAP `e6d92` `e6dd0`, FR13 / FR12의 남은 정지, TRAP `b3e58` `b3eac`, C1~C9의 남은 정지, 앞 단위 계산 점프의 routing 밖 대상)·`cb` 진입(callback 5, subroutine 12, 생산자 호출 3, 끝·다시 그리기 진입); 계산 점프 착지를 trace 전체에서 대조(앞 단위 표 그대로; E2에는 계산 점프 없음); `native_safe` 기본 유지)): 작업자 300건 seed 1 `mismatches 0`(`covered starts 129 of 129`; 깨끗이 멈추지 않은 native 25건 건너뜀 [I: 무작위 RAM 목록·검색 반복이 3,000,000 명령 안에 끝나지 않음]; native oracle abort 0, 홀수 주소·계산 점프 분류 0, `trial_logs/real_n300_s1.log`). 실행 중 E2 소비자 3개가 실제 생산자 뒤에 native 분기와 비교되었다(`e69c6` 40, `e69e8` 18, `e6b64` 281). 앞선 30건 seed 11 시험도 `mismatches 0`(`trial_logs/real_t30.log`).
- [F] **IO, 입력 확장 관측**(E2 연결 뒤, `--workers 3`, `MS5_SEED_DIR=artifacts/stage_entry_body`): run 12, native 비교 frame 14,500 가운데 일치 **12,586**(예측 12,586, 기준선 10,374 → +2,212), 불일치 0(beyond 0), C++ 오류 0, chain divergence 0, 수용 키 모두 true(`negatives_ok` 포함), 관측 pin `io-ext`(`trial_logs/io_ext_e2.log`; `verification.json` SHA256 `b31b0b6cd39e704d…`, `frontier.json` `7de4279cecbb892a…`, scratch `io_ext_e2/`). run별 일치: P0 1,200, P1 1,200, X1 2,552, X2 2,276, X3 2,078, X4 3,280. X1 68 / 94, X2 68, X4 68 / 94는 guard frame(system-return)까지 모두 일치한다. 첫 정지 frame: X2 94 874, X3 68 1,120, X3 94 958 — 재관측 예측(`reobs/e2v1.stops`)과 run·frame이 모두 같다. 확인된 frontier PC는 `d177e` `3643e` `7177a`(D, 각 1 run)로 모두 FR14다.
- [F] 원래 IO 관측·frame 비교·legacy 검증기는 작업자가 돌리지 않았다(메인 runner).
- [F] `CPP_PINS`: 작업 트리와 scratch clone root(`work/mkroot.py`; 확인 뒤 symlink를 먼저 지우고 삭제)에서 파일 SHA와 같다(4 / 9 pin, 불일치 0, `trial_logs/pincheck_tree.log` `pincheck_root.log`).

## 검증 기록(검증 실행: 결정적 runner + 메인 검토)

- [F] `make -j4 all test`: 종료 0, 경고 0, Assert 0, Python 310 OK.
- [F] `ubsan`: 빌드/실행 종료 0, 런타임 오류 0.
- [F] `mutation`: 변이 563, 제거 561, 등가 2.
  - 이 실행 전에 메운 시험 빈틈 27개.
- [F] real-ROM: 배치 `f4`, `f5`, `s1`, `s2`, `s3` 커버 `129`, `129`, `129`, `129`, `129`; mismatches `0,0,0,0,0`.
  - 오라클: `native_safe` 켬.
- [F] V1: A/B 각각 fixtures 1573, failed 0, identical true(digest `8f2b0def0ea3f284`); regression specs 48개 모두 failed 0.
- [F] legacy verifiers: `stage_entry`, `area_clear`, `stage_event`, `stage_event_ops`, `frame_helpers`, `card_menu_close`, `input`, `scene_core`, `scheduler`, `objects_g1` 모두 종료 0. `objects_g1` 판정은 C1과 같다.
- [F] frames: `d1` 완료 54400, mismatches 0; `controller_game` 완료 54400, mismatches 0; `irq` 완료 54400, mismatches 0; `demo` 완료 45684, mismatches 0.
- [F] IO(원래 관측): 일치 합계 173966, 기준 173966, 차이 0, mismatches 0, C++ 오류 0, 실행 2, identical true; 설정별 `P0` 81600, `P1` 81600, `P1b` 8400, `boot-demo-0` 577, `boot-title-idle` 600, `boot-title-start` 906, `fx-bios-call` 3, `fx-c-input-read` 3, `fx-n-input-read` 3, `fx-queue-short` 1, `fx-start-c79a` 273.
  - 수락 실패 항목은 없고, native frame 173966 전부 일치한다.
- [F] IO(확장 입력 관측, 14500 native frames): 일치 합계 12586, 기준 10374, 차이 2212, mismatches 0, C++ 오류 0, 실행 2, identical true; 설정별 `P0` 1200, `P1` 1200, `X1` 2552, `X2` 2276, `X3` 2078, `X4` 3280.
  - 예측 확인: 정확한 비트맵 재관측은 12586을 예측했고, 실측도 12586이다.
  - 수락 실패 항목은 없고, native 완료 frame 14500 중 12586이 일치한다.
  - 첫 정지: `d177e 3643e 7177a`(모두 FR14).
  - 범위: 계획 128개에 `e695e`(`28ae`의 라우팅되지 않은 자식 `e6952`에서 오는 `BRA.W`)를 추가했다. `TRAP` `e6d92`와 `e6dd0`은 단위 밖에 있다(FR5 관례). E에서 실행된 라우팅되지 않은 PC는 0에 도달한다.
- 검증 방법: 결정적 runner(LLM 없음). 이 기록 초안은 local Qwen이 썼고 메인이 검토·수정했다.

## 뒤 단위 변경 기록: objects FR14(2026-10-24, 작업자 Claude Opus 5.5 / high)

FR14 계약(`animation-machine-frontier-fr14-contract.md`) 결정 5에 따른 기록이다. E2 실행부와 E2 시험은 바뀌지 않았다.

- [F] V1 spec `se2.py`의 `EXIT_STOPS` 앞 5개(`71874` `d1632` `d177e` `7177a` `71786`)가 FR14 block이 되어 `ROUTED_LATER` `()` → (`71874` `d1632` `d177e` `7177a` `71786`)로 두었다(E2 run의 선언 정지는 그대로).
