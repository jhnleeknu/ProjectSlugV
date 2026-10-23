# frontier 단위 FR13(입력 확장 관측의 영역 D 넷째 단위: FR10 뒤 단위 정지 `70f60`(방향 시험 → BYTE 63)·`70fcc`·`70ff8`(`MOVE.L A0,(A6)`: 표 `70d72`의 LONG을 다음 callback으로 씀)·`71028`, FR12 뒤 단위 정지 `71682`·`717c2`, 표 `70d72` callback `71622`, 설치 값 `717e8`(`49a58` 두 번 → LONG 64 / 36)·`71884`·`719f8`·`71f2c`..`72114`(`705ca` C, `70302` 결과의 `71fe2 TST.B D0` / `71fe4 BEQ`, 부호 있는 LONG 제한 `7209c`..`720c0`, `EOR.W` 부호 시험 `720e0`)·`7224c`, FR11 뒤 단위 정지 `b6d90`(부호 있는 WORD 42 비교 → BYTE 15 bit 0)·`bfcfa`(`2986` 자식 `bfd48`), FR11 표 `c54b2` 칸 `c54ba`·`c54d6` → `c5520`, `c554c`, item 처리기 `b44ac`(RTS `b450c`가 `1c356`의 C를 FR2 `b46ac`로 넘김), FR4 표 `cc82e` 칸 `cc852`, animation 꼬리 `cc8b4`(계산 점프 `cc8da`: 27칸 `BRA.W` 표, 실행 칸 `cc8f6`만 전사 → `ccbc0`), interpreter callback `cca5a`·`d159e`(`2986` 자식 `d15c4` .. `d177a`), 207 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §10.5 표의 FR13 행(계획 이름 D-4)과 §10.x 메인 결정, FR11 계약의 메인 결정(실행되는 표 칸 `c54ba` `c54d6`(표 `c54b2`)은 FR13), FR12 계약 결정 1(FR12가 남긴 짧은 fall-through `71682` `717c2`는 계획대로 FR13)을 기준으로 삼는다. 구조·공통 규칙은 FR12 계약(`animation-machine-frontier-fr12-contract.md`; 확장 관측 단위, 정확 bitmap 재관측, 뒤 단위 정지의 처리), FR11 계약(`animation-machine-frontier-fr11-contract.md`; 계산 점프 규칙 — 표 `c54b2`의 guard 방식), FR10 계약(`animation-machine-frontier-fr10-contract.md`; 레지스터에서 다시 계산하는 Z 경계 `70ff4`), FR4 계약(`animation-machine-frontier-fr4-contract.md`; 근처의 27칸 표 `cc7a8`/`cc82a`)을 따르며 다른 점만 적는다. 단위 이름은 FR13, 파일 접두어는 `objects_fr13`(C++) / `fr13`(V1 spec)다. 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다. BIOS 실행, 자연 scheduler, IRQ timing은 주장하지 않는다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 LONG(`2000d0` `2000d4` `2001c0` `200080` `200090`)을 live bus로 읽는다(아래). 장치 쓰기는 없다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 FR12 커밋 `d632bb5`(branch `claude/fr13-core`; C1~C10, E1, D, FR10~FR12 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `49170da4b41a73e9cbb8d1684e0fa261fedc2ece6bab2e1e77a0b2dbe8e0c5f2`, `animation_machine_internal.h` `3a5dc9af01e57baf08320a0ec5ba744c82ea85679e150a5e912a7d1212ed8c84`(FR12 계약의 새 값과 같음).
- [F] 관측 입력(읽기 전용): 입력 확장 IO 관측 `artifacts/animation_machine_io_ext`(`observation.json` SHA256 `9da40ac6dcbea3eb…`, compared_sha256 `b5d15d4fcd53555b…`, 검증기 pin 이름 `io-ext`). V1 natural family가 이 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)으로 읽는다(C9 결정 6과 같은 방식).
- [F] 이 단위의 정확 bitmap 재관측 두 벌(scratch, 관측기 `tools/observe_animation_machine_io_ext.py` 수정 없음): `reobs/fr13base`(FR12 routing 그대로), `reobs/fr13v1`(계획 FR13 27 범위를 `--extra-routed`로 가상 routing). 결정 1.
- [F] 시작 목록: **`ms5-scratch/fr13/work/starts_fr13_final.txt`(207개, 줄마다 하나, SHA256 `7d9836ea0390e4c774b6e915aad94296e1ae0ac1331d6406fbc0700be9442860`)**. 계획 목록 `ms5-scratch/fr13/starts_FR13.txt`(207개, 공백 구분, SHA256 `e10ba8e15b814215321c5c1058d14d3213519bcfec6d06d9ca25909f8404ed72` = 계획 §10.5의 `e10ba8e15b814215`)와 집합이 같다(결정 1: 범위 보정 없음). 실행부의 `case` label 207개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(V1 spec `build()`가 시작 207개 모두 `animation_objects_fr13_block`로 routing됨을 확인, `make test`의 FR13 시험이 시작 207개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr13/`
  - `reobs/run.sh`(재관측 + `dleft.py` + `runstops.py`), `reobs/fr13base` `fr13v1`(+ `.dleft` `.stops` `.log`), `plan/udetail_FR13_plan.txt` `plan/D-4.dis.txt`(계획 `xplan_v2.json`의 D-4 상세·역어셈블; `tools/xdetail.py`, `MS5_OBS2=fr12/reobs/fr12v1`), `work/fr13ranges_plan.txt`(27 범위), `work/blocklist_fr13.md`.
  - `tools/newvis_fr12.py`(`FR12_RANGES=work/fr13ranges_plan.txt`로 FR13 범위를 줌; 새로 보인 PC), `work/intargets.py` → `work/intargets_fr13_v1.out`(범위 안 비시작 PC로 오는 직접 분기), `tools/refs_fr13.py` → `work/refs_fr13_v1.out`(ROM 전체 FR13 시작 참조), `tools/flagscan.py` → `work/flagscan_fr13_v1.txt`(block 경계를 넘는 flag), `tools/exitflags.py` → `work/exitflags_fr13.txt`(출구·복귀 대상이 앞 코드의 flag를 읽는지), `tools/fr13exec.py` → `work/fr13exec_base.txt`(재관측의 FR13 실행 PC·run·frame), `tools/natscan_fr13.py` → `work/natscan_fr13_cand.out` `work/natural_fr13_cand.json`(V1 natural frame), `tools/fr13refs_repo.py` → `work/fr13refs_repo_v1.out`(저장소의 FR13 범위 literal), `tools/dbg_callee.py`(V1 callee world 진단), `work/v1_regs.sh`, `work/pincheck.py`, `work/mkroot.py`, `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그). `tools/natfind_fr13.py`(callback마다 native trace로 FR13 도달을 찾는 시도)는 frame당 node 수 × fork 비용으로 끝내지 못해 중단했고, natural 후보는 정적 진입(아래)으로 정했다.
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위(결정 1)

- [F] **기준선**(FR12 routing, 입력 확장 관측): 예측 일치 frame **7,977**, 첫 정지 D 8 run이 모두 FR13이다. FR12 계약의 IO 실측(X1 68 frame 873 `70fcc`, X1 94 604 `c54ba`, X2 68 757 `71028`, X2 94 629 `70f60`, X3 68 760 `b44ac`, X3 94 588 `c54d6`, X4 68 773 `c554c`, X4 94 593 `71f2c`)과 같다.
- [F] **정확 bitmap 재관측(FR12 routing)** `reobs/fr13base`(routing `49170da4`): `dleft.py` 실행된 routing 밖 PC E 108 / D 252, 예측 7,977, 첫 정지 X1 68 873 `70fcc`, X1 94 604 `c54ba`/`c5520`/`c553a`, X2 68 757 `71028`, X2 94 629 `70f60`/`70f7e`, X3 68 760 `b44ac`/`b4506`/`b450c`/`bfcfa`.., X3 94 588 `c54d6`/`c5520`/`c5534`, X4 68 773 `c554c`.., X4 94 593 `71f2c`..(`reobs/fr13base.dleft` `.stops`; FR12 계약의 가상 routing 재관측 `fr12v1`과 줄 단위로 같음).
- [F] **정확 bitmap 재관측(FR13 가상 routing, 계획 27 범위)** `reobs/fr13v1`: 예측 일치 frame **10,374**(계획 10,374와 같음), 실행된 routing 밖 PC E 108 / D 91(D 91은 모두 FR14 D-5의 시작), 첫 정지는 E 6 run(`3144` → `e695a` ..: X1 68 frame 960, X1 94 768, X2 68 992, X2 94 800, X4 68 1,268, X4 94 1,108; E2)과 D 2 run(X3 68 1,120 `3643e`.., X3 94 958 `7177a`/`71786`; 둘 다 FR14)이다(`reobs/fr13v1.stops`; 단위 소속은 계획 `xplan_v2.json`).
  - [F] **숨은 직선 연속 검사**: `fr13base`에 없고 `fr13v1`에만 보이는 routing 밖 PC는 **없다**(`newvis_fr12.py`에 FR13 범위: 12 run 모두 0). 가상 routing 관측에서 실행된 FR13 범위 끝 PC `71874` `d1632` `d177e`(모두 FR14 D-5)는 기준 관측에서 이미 보였다. 반복은 한 번으로 수렴했다.
- [F] **범위 밖에서 범위 안 비시작 PC로 들어오는 직접 분기**: 없다(`work/intargets_fr13_v1.out` 2줄: `bfd80 → bfd18`은 범위 안 `bfd7c JSR c6a96.l`의 주소 하위 WORD `6a96`을 `BPL.B`로 읽은 것, `c55be → c5556`은 FR11 `c55ba JSR c6a96.l`의 같은 operand). ROM 전체 참조 검색(`work/refs_fr13_v1.out`)에서 범위 밖의 분기·설치는 모두 FR13 시작으로 온다(아래 "진입").
- [F] **계획 특이 항목 대조**(`plan/D-4.dis.txt`, ROM 바이트): 계산 점프 `cc8da JMP cc8de(PC,D0.W)`(27칸), `2986` 자식 `bfd48`(`bfcfa`) `d15c4`(`d159e`) — 계획과 같다. TRAP·DIVU·MULU/MULS·MOVEM·ADDX/SUBX는 없다.
- [F] **실행되는 표 칸**(재관측 기록의 routing 밖 PC): 표 `c54b2`(FR11 `c54ae`)에서는 `c54ba`(X1 94)와 `c54d6`(X3 68 / 94)뿐, 표 `cc8de`(FR13 `cc8da`)에서는 `cc8f6`(X3 68)뿐, FR4 표 `cc82e`(`cc82a`)에서는 `cc852`(X3 68 / 94, X4 68 / 94)다. FR13을 가상 routing한 `fr13v1`에서는 `cc8de` / `c54b2`의 다른 칸이 기록되지 않는다(남은 FR4 칸은 FR14 `cc7b8` 하나). 그래서 전사하는 칸은 이 셋(`c54ba` `c54d6` `cc8f6`)과 FR4 칸 `cc852`뿐이다(메인 결정·계획과 같음).
- [F] **뒤 단위 짧은 block**: 메인 결정대로 FR12가 남긴 `71682`(`MOVE.W 7a,78`; `7155e BRA`의 대상) `717c2`(`MOVE.L #717e8,(A6)`; `717ae BCC`의 fall-through)는 FR13 시작이다. 계획이 FR14(D-5)에 둔 `71874`(`NEG.L D0`, `71870 BNE`의 fall-through) `d1632`(`NEG.W D0`, `d162e BNE`의 fall-through) `d177e`(`d177a BCC`의 Set 쪽 fall-through)는 FR13 뒤 단위 정지로 둔다(FR12 결정 1과 같은 처리).
- [F] **`71fe2`/`71fe4`의 분할**: 계획의 block 시작은 실행된 TB 시작을 진입으로 넣어 정하므로(계획 §10.5 규칙) `71fe2 TST.B D0`와 `71fe4 BEQ.W 72000`이 각각 block이다 [I: 관측의 TB 경계가 이 사이에 있었다]. 시작 목록을 바꾸지 않고 FR10 `70ff0`/`70ff4`의 방식(Z를 레지스터에서 다시 계산)으로 처리한다(결정 4).
- [F] **IO 실행**(`reobs/fr13base`, `work/fr13exec_base.txt`): FR13 시작 가운데 기록된 것 161개, 실행 5,004회(계획 표의 161 / 5,004와 같음), run 8개. 처음 frame: X1 68 873, X1 94 604..724, X2 68 757, X2 94 629..870, X3 68 760..1,476, X3 94 588..1,076, X4 68 773..1,171, X4 94 593..1,011. 기록되지 않은 시작 46개는 closure로 들어왔다(같은 TB 안의 직선 연속이거나 이 관측에서 실행되지 않는 분기 쪽: `70f74`, bank anim의 `TST.W 9c` = 0 쪽(`7162a` `717f0` `71a00` `71f4a` `72048` `72254`)과 그 `BRA`, `716b0`, `718a8`, `71a72`, `71f34`/`71f3a`, `71fac`(설치 직후 곧바로), `71fe8`..`71ffa`, `72018` `72026` `72036`, `720b6` `720c0` `720e0` `720f2` `72106`, `b6d9c`, `cc94a`, `ccbc8`..`ccc6a`(WORD 8c ≠ 1의 anim 선택), `d16a6`, `d170e`).

## FR13 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **207 block, 478 명령, 2,290 byte, 27 범위**(시작 목록 SHA256 `7d9836ea…`(줄 형식) / `e10ba8e1…`(계획 형식), 범위 byte를 이어 붙인 SHA256 `a80b01e627ee858856b832044e9350df7f7fc6e52406f98dc9ece6bd14927096`). 짝수 PC 1,145(내부 938). 기존 routing과 겹침 0(V1 spec `build()`와 시험 `interior()`가 확인).

| 범위(CPU = 파일 오프셋) | byte | 시작 | SHA256(앞 16자) | 내용 [I] |
| --- | --- | --- | --- | --- |
| `70f60..70f84` | 36 | 3 | `624cca16ed3f3e22` | FR10 `70f4e`(`CMPI.W #3000; BCS`)의 fall-through: `SUBI.W #1800,D7; BTST #0,15; SEQ.B D0; EXT.W D0; EOR.W D7,D0; BMI` → BYTE 63 := 2 / 1 → FR10 `70f84` |
| `70fcc..70fd2` | 6 | 1 | `0e0e181975d18622` | FR10 `70fc2`(BYTE 82 bit 7)의 fall-through: `MOVE.L #71468,(A6)`(쓰기만) → FR10 `70fd2` |
| `70ff8..70ffa` | 2 | 1 | `bb5d2526bdf953e2` | FR10 `70ff4`(A0 ≠ 0)의 fall-through: `MOVE.L A0,(A6)`(표 `70d72`의 LONG을 쓰기만) → FR10 `70ffa` |
| `71028..7102e` | 6 | 1 | `724c9a2c1b6cc7dd` | FR10 `71020`(WORD 7c = 0)의 fall-through: `MOVE.L #72f8a,(A6)`(쓰기만) → FR10 `7102e` |
| `71622..716ca` | 168 | 15 | `f3f15605fffe762c` | 표 `70d72` 칸 4 callback: `TST.W 9c` → bank anim 3 / `2000d0` / 88 또는 b / `2000d4` / a4 → `71682`: WORD 78 := WORD 7a, LONG 64 := 0, 설치 `71696`(곧바로): `4be06`, BYTE 15 bit 7 → `4bfa4` / `4be2c`, `49fc6` C → `70c0c` 쓰기, `BRA.W 72dd2` |
| `717c2..717c8` | 6 | 1 | `9b7f138237027a2e` | FR12 `717ae BCC`의 fall-through: `MOVE.L #717e8,(A6)`(쓰기만) → FR12 `717c8` |
| `717e8..71874` | 140 | 7 | `911428064cd5d99d` | callback `717e8`: bank anim 3 / `2000d0` / 180 또는 b / `2000d4` / 1cc, LONG 36 := LONG 64, LONG 3a := 8a000, `49a58` 두 번(`MOVE.W D0,D1; ADD.W D1,D0; EXT.L; ADDI.L #28000`), BYTE 15 bit 0 → `71876` / `71874`(FR14) |
| `71876..718c8` | 82 | 10 | `5f09bf362f6aac09` | LONG 64 / 36 := D0, 설치 `71884`(곧바로): `702cc`, `49fc6`, `TST.W 3a; BPL` / `4ae4a`(A0 = `6fe78`) BYTE 6 → `718ec` 쓰기, BYTE 15 bit 7 → `BCLR #3,15`, `719f8` 쓰기, `BRA.W 72dd2` |
| `719f8..71a80` | 136 | 11 | `24de4f8b828c91e3` | callback `719f8`: bank anim 3 / `2000d0` / 188 또는 b / `2000d4` / 1d4, LONG 64 := 0, 설치 `71a62`(곧바로): `4bfa4` `49fc6` C → `70c0c` 쓰기, `703f6`, `BRA.W 72dd2` |
| `71f2c..72118` | 492 | 49 | `133dc72d3de4b725` | callback `71f2c`: `705ca` C → `49a58` & 1f를 WORD 88에 더함, bank anim 3 / `2000d0` / 104 또는 b / `2000d4` / 4, 설치 `71fac`(곧바로): BYTE 15 bit 7 → FR12 `722da` / `4bfa4` `49fc6`, \|WORD 8e − 42\| < 10 → `72040` 쓰기, `70302` → `71fe2`/`71fe4`(D0.B 0 / 1 / 그 밖: `721b8` / `7224c` 쓰기), WORD 88 감소(음수 → `7224c`), BYTE 82 bit 0 → `72118`, WORD 7c = 0 → `73192`, BYTE 6f ≠ 40 → `7224c`, `BRA.W 72d66`; callback `72040`: bank anim 3 / 64 또는 b / 4, D0 := (LONG 8e − LONG 42) ASR 5를 ±18000으로 제한 → LONG 64, WORD 8a := 18, 설치 `720d6`(곧바로): BYTE 82 bit 7 → `SNE`/`MOVE.B 64`/`EOR.W` 부호 → `NEG.L 64`, `4bfa4` `49fc6` C → `71f2c` 쓰기, WORD 8a 감소 = 0 → `71f2c` / `BRA.W 71fde` |
| `7224c..722da` | 142 | 11 | `6dba36a4d20be1c8` | callback `7224c`: bank anim 3 / `2000d0` / 68 또는 b / `2000d4` / 10, LONG 64 := 0, 설치 `722b6`(곧바로): BYTE 15 bit 7 → FR12 `722da` / `4bfa4` `49fc6` C → `70c0c` 쓰기, `BRA.W 72dd2` |
| `b44ac..b44b2` | 6 | 1 | `0f47953e028153c9` | item 기록 `b3894 + 12m`(m = 0, 10)의 처리기 LONG 4: `MOVEQ #5,D1; BRA.W b4506` |
| `b4506..b450e` | 8 | 2 | `5399bc514040e9d1` | `JSR 1c356.l`(C5); `RTS`(`b450c`: `1c356`의 C를 FR2 `b46ac`로 넘김) |
| `b6d90..b6dac` | 28 | 3 | `d51c09ba7b3965ba` | FR11 `b6d8c BCC`의 Set 쪽 fall-through: WORD 42(A6) ≤ WORD 42(A0)(부호)면 `BSET #0,15`, 아니면 `BCLR` → FR11 `b6dac` |
| `bfcfa..bfda0` | 166 | 16 | `6f958f29debf5f50` | FR11 `bfcee BNE`의 대상: `2986` 자식 `bfd48`(D0 = 1e), `4970a`(D0 = D1 = 0), BYTE 14 := BYTE 1a, WORD a4 := 2, 설치 `bfd2c`(곧바로): WORD a4 감소 음수 → `JMP 2a00` / `b4030` `b4334`; RTS. 자식 `bfd48`: bank anim 1e3 / `2001c0` / c, `c6a96`(D0 6f, D1 3, D2.B 0), 설치 `bfd88`(곧바로): `43e34` `49fc6` C → `JMP 2a00` / RTS |
| `c54ba..c54be` | 4 | 1 | `ca546638cbf4cd39` | FR11 표 `c54b2`의 칸 2: `BRA.W c5520` |
| `c54d6..c54da` | 4 | 1 | `518f0b1010d896f3` | FR11 표 `c54b2`의 칸 9: `BRA.W c5520` |
| `c5520..c5540` | 32 | 3 | `1ce6a741223ee321` | `CLR.B 5e; MOVE.L #c5432,(A6)`(쓰기만), BYTE 61 bit 7 → `MOVE.L #c554c,(A6)`(쓰기만); `CLR.B 5e; RTS` |
| `c554c..c5592` | 70 | 7 | `dd718959430e8925` | callback `c554c`: bank anim ba / `200080` / 148, 설치 `c557a`(곧바로): `4be06` `49fc6` C → `JMP 2a00` / RTS |
| `cc852..cc856` | 4 | 1 | `e2570600dea013b7` | FR4 표 `cc82e`(`cc82a JMP`)의 칸 9: `BRA.W cdc1c`(FR4) |
| `cc8b4..cc8de` | 42 | 4 | `812b255915007eac` | animation 꼬리 `cc8b4`(N15 `72d86`/`72dac`, B1a `78d3a`의 `JMP`): BYTE 5e = 0 → RTS `cc94a` / `JSR cca76`(FR4), BYTE 5e 다시 읽고 WORD 5e := 0, `CMPI.B #1b; BCC ccbc0` / `ANDI.W #ff; ADD.W` 둘; `JMP cc8de(PC,D0.W)`(결정 2) |
| `cc8f6..cc8fa` | 4 | 1 | `41e1637265308302` | 표 `cc8de`의 칸 6: `BRA.W ccbc0` |
| `cc94a..cc94c` | 2 | 1 | `1ceeabf0c6a5a30b` | `cc8b8 BEQ`의 대상: RTS |
| `cca5a..cca76` | 28 | 3 | `99c2dcee1896c2e5` | interpreter callback(script 표 `4a500` + 23c): `MOVEQ #0,D0; MOVE.W (A0),D0; SWAP`, BYTE 15 bit 0 clear → `NEG.L`, LONG 36 / 64 := D0; RTS |
| `ccbc0..ccc88` | 200 | 17 | `aa25534b18eb5d6b` | WORD 8c 0 / 1 / 2 / 3 / 4 / 그 밖 → anim 상수 `ce758` `ce7c4` `d0060` `cf126` `d00e0` `d07f8`(WORD 20 := WORD 8a, D0.W := 100, `JSR 49f8c`), `MOVE.L #cdd2e,(A6)`(쓰기만); RTS |
| `d159e..d1632` | 148 | 7 | `c15cc3fc04c30311` | interpreter callback(script 표 `4a500` + 19c): `2986` 자식 `d15c4`(D0 = 14), `49214`(D0 = D1 = 0), `JMP 491b6`. 자식 `d15c4`: `BSET #4,15`, WORD 68 / 1e := e0ef, bank anim da / `200090` / 8, 소리 `8ebe` 212 / 213, D0 := 18, WORD 32 += 18, D1 := 18000, BYTE 15 bit 0 → `d1636` / `d1632`(FR14) |
| `d1636..d177e` | 328 | 29 | `7b50a1aa8c78cc93` | WORD 2e += D0, LONG 36 := D1, 설치 `d1644`(곧바로): BYTE 15 bit 7 → `d16ae` 쓰기, LONG 3a += (fff00000 − 3a) ASR 5, `4be34` `49fc6`, `d1670`: WORD 10000e & 3, BYTE 14 / 19 / 1a 교대, `1ab80`(A0 = `d13a4`) C → `JMP 2a00` / RTS; callback `d16ae`: bank anim da / 4, LONG 36 / 3a / 64 := 0, WORD 76 := 78, 설치 `d16fa`(곧바로): BYTE 15 bit 7 → `4bfa4` / 3a += (fff40000 − 3a) ASR 5, `4be34`, `49fc6` C, WORD 76 감소(borrow → `d1740` 쓰기), `BRA.W d1670`; callback `d1740`: bank anim da / c, 설치 `d176e`(곧바로): `43e34` `49fc6` C → `d1670` / `d177e`(FR14) |

- [F] **진입**(현재 routing 기준 호출자, `work/refs_fr13_v1.out`, ROM 전체 LONG 검색):
  - 다른 실행부의 fall-through·분기: `70f60` ← FR10 `70f4e`(`BCS` 아님 쪽), `70fcc` ← FR10 `70fc2`(BYTE 82 bit 7 set), `70ff8` ← FR10 `70ff4`(A0 ≠ 0), `71028` ← FR10 `71020`(WORD 7c = 0), `71682` ← FR12 `7155e BRA`(routing 밖 `715be` `7161e`의 `BRA`도 이 PC로 옴), `717c2` ← FR12 `717ae`(BCC 아님 쪽), `b6d90` ← FR11 `b6d8c`(C Set; routing 밖 `b6ed4 BRA`), `bfcfa` ← FR11 `bfcea`/`bfcee BNE`.
  - 계산 착지(기존 실행부의 규칙 그대로, FR13은 그 칸을 routing할 뿐이다): FR11 `c54ae JMP c54b2(PC,D0.W)`의 칸 2 `c54ba` · 9 `c54d6`(FR11 결정 2: 색인 0..1a, routing이 판정), FR4 `cc82a JMP cc82e(PC,D0.W)`의 칸 9 `cc852`(FR4 결정 2), FR2 `b46aa JSR (A1)`의 item 기록 처리기 `b44ac`(기록 `b3894 + 12·0`의 LONG 4 = 파일 오프셋 `b38a4`, `+ 12·10` = `b3958`), interpreter `JSR (A1)`(`4a352` `4a43c`)의 script callback `cca5a`(표 `4a500` + 23c, LONG `4a73c`) `d159e`(표 + 19c, LONG `4a69c`), FR10 `70ff8 MOVE.L A0,(A6)`이 쓰는 표 `70d72` 칸 4의 `71622`(다음 dispatch; FR2b `70d22`·N15 `711e6`의 같은 쓰기).
  - 꼬리 `JMP cc8b4`: N15 `72d86`/`72dac`(`on15_death`), B1a `78d3a`, routing 밖 `6fdf8`.
  - 설치·callback: `717e8` ← FR13 `717c2`(쓰기만); `71884` ← FR13 `71876`(곧바로), FR2b `706f4`(쓰기만); `719f8` ← FR13 `718b8`(쓰기만), routing 밖 `719a4` `719ee`; `71f2c` ← FR12 `71f22`, FR13 `72106`(쓰기만)·`7210c BEQ`, routing 밖 `721ae` `72244`; `72040` ← FR13 `71fd8`(쓰기만), U13 `7093e`(쓰기만); `7224c` ← FR13 `71ffa` `72008` `72036`(쓰기만), routing 밖 `7211c BMI`; `c554c` ← FR13 `c5534`, FR3 `c542a` `c568e`(쓰기만), routing 밖 `c56f8` `c5750` `c5766` `c5796`; `d16ae` ← FR13 `d164e`; `d1740` ← FR13 `d1736`. 범위 안 곧바로 들어가는 설치 `71696`(`71690`) `71884`(`7187e`) `71a62`(`71a5c`) `71fac`(`71fa6`) `720d6`(`720d0`) `722b6`(`722b0`) `bfd2c`(`bfd26`) `bfd88`(`bfd82`) `c557a`(`c5574`) `d1644`(`d163e`) `d16fa`(`d16f4`) `d176e`(`d1768`).
  - `2986` 자식(A6 = 자식 node로 처음 dispatch): `bfd48` ← `bfcfa`, `d15c4` ← `d159e`.
- [F] **설치 값**(`MOVE.L #v,(A6)`): 곧바로 들어감 12개(위). **쓰기만**: `70c0c`(`716c0` `71a72` `722d0`, routing) `71468`(`70fcc`, routing) `72f8a`(`71028`, routing) `717e8`(`717c2`) `718ec`(`718a8`, routing 밖) `719f8`(`718b8`) `72040`(`71fd8`) `721b8`(`71ff0`, routing 밖) `7224c`(`71ffa` `72008` `72036`) `72118`(`72018`, routing 밖) `73192`(`72026`, routing 밖) `71f2c`(`72106`) `c5432`(`c5520`, routing) `c554c`(`c5534`) `cdd2e`(`ccc80`, routing) `d16ae`(`d164e`) `d1740`(`d1736`). **RAM 값 쓰기**: `70ff8 MOVE.L A0,(A6)`(점프가 아님; 다음 dispatch가 판정. A0 = FR10 `70fec`가 읽은 표 `70d72`의 LONG: 원본 `0 71502 71562 715c2 71622 716ca 716ca 716ca`, 0은 `70ff4`가 거름).
- [F] **2986 자식**(`MOVEA.L #v,A0; MOVE.W #n,D0; MOVEA.L #100bf4,A1; JSR 2986`): `bfcfa`(v = `bfd48`, n = 1e), `d159e`(v = `d15c4`, n = 14). 복귀 뒤의 C를 읽는 곳은 없다(`bfd10`·`d15b4`는 `MOVEQ`). `28ae` 자식은 없다. [F] 2986 안의 28ae 실패(`290e`)는 기존 2986 실행부가 caller X를 알 때만 계속하는 checked 오류다(C7 결정 6·7; 실제 ROM 차분의 문서화된 분류).

### 계산 점프와 표(결정 2)

- [F] **`cc8da JMP cc8de(PC,D0.W)`**(block `cc8d2`, `ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0` 뒤): 표 `cc8de..cc94a`(ROM 파일 오프셋 = CPU 주소), `BRA.W` 27칸. 원본 대상: 칸 3 → `cd0fe`, 4 → `cd50e`, 7 → `ccc88`, 10 → `ccf4e`, 11 → `ccd74`, 나머지 22칸 → `ccbc0`. 색인은 BYTE `5e(A6)`이고, 같은 block 앞의 `cc8c0`가 `MOVE.B 5e(A6),D0; MOVE.W #0,5e(A6); CMPI.B #1b,D0; BCC ccbc0`로 0..1a로 묶는다. BYTE 5e의 writer는 충돌 처리 등 여럿이므로(FR11 계약 `c5496`과 같은 상황) 범위는 writer가 아니라 이 guard가 정한다.
  - **규칙**(FR11 `c54ae`·FR4 `cc7a8`/`cc82a`·C10 `203ac`와 같은 꼴): 변위(D0.W = 4 × D0.B) ≤ 68이면 PC := `cc8de` + 변위(routing이 판정: 칸 6 `cc8f6`만 FR13 block, 나머지 26칸은 routing 밖 = 선언 정지), 넘으면(guard를 건너뛴 `cc8d2` 직접 진입) checked `unsupported animation objects fr13 jump target`. 관측에서 실행된 칸은 `cc8f6`뿐이다(위 "재확인").
  - [I] 실행되지 않은 칸의 대상 `cd0fe` `cd50e` `ccc88` `ccf4e` `ccd74`는 FR4 계약 결정 2의 처리기 무리(FR4b/FR4c 후보)와 겹친다. 이 단위는 그 대상을 routing하지 않는다.
- [F] **FR13이 받는 계산 착지**(위 "진입"): FR11 표 `c54b2`의 `c54ba` `c54d6`, FR4 표 `cc82e`의 `cc852`, FR2 item 처리기 `JSR (A1)`의 `b44ac`, interpreter `JSR (A1)`의 `cca5a` `d159e`. 각 실행부의 기존 규칙(routing이 판정)을 그대로 둔다.
- [F] **`70ff8 MOVE.L A0,(A6)`**: RAM LONG callback 자리에 레지스터 값을 쓰기만 하고 FR10 `70ffa`로 간다(점프가 아님). 다음 frame의 dispatch가 그 값을 routing으로 판정한다(C++는 값을 검사하지 않음; FR12 `c0966`과 같은 처리). 표 `70d72`의 값 가운데 FR13이 routing하는 것은 `71622`, FR12는 `71502` `716ca`이고 `71562` `715c2`는 routing 밖이다.
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙):
  - bank 창 LONG `2000d0`(+88 / 180 / 188 / 104 / 64 / 68), `2000d4`(+a4 / 1cc / 1d4 / 4 / 10), `2001c0`(+c), `200080`(+148), `200090`(+8 / 4 / c): FR4 `ofr4_bank_anim`·FR12 `ofr12_bank_anim`과 같은 꼴(`ofr13_bank_anim`).
  - `cca5a`의 WORD (A0): interpreter가 넘기는 script 자료 포인터(A0) 아래 WORD [I: callback의 인자]. live bus로 읽는다(RAM / 고정 ROM).
  - 넘기기만 하는 상수: anim 포인터 `ce758` `ce7c4` `d0060` `cf126` `d00e0` `d07f8`(`ccbc0`, `49f8c`로 넘김), `LEA 6fe78(PC),A0`(`71896` → `4ae4a`), `LEA d13a4(PC),A0`(`d1698` → `1ab80`: 그 두 LONG을 화면 상자로 읽음, N05 실행부).
  - 이 표·창 값은 모두 anim 자료 포인터(A1)·첨자·판정 WORD다. 코드 주소로 점프하지 않는다.

### 정수 연산(결정 3)

- [F] **ASR.L #5**(`7209c`, `d1654`, `d170e`): 부호 채움(`ofr13_asr`; C++ 부호 shift를 쓰지 않음). `d1654`/`d170e`는 `ofr13_ease`: D0 := (상수 − LONG 3a) ASR 5, LONG 3a += D0(mod 2^32).
- [F] **부호 있는 LONG 비교**(`7209c CMPI.L #18000; BLE`, `720b6 CMPI.L #fffe8000; BGE`): 두 LONG의 정확한 부호 비교(`ofr13_signed_long`: `int64`로 넘침 없이). 앞의 `SUB.L`은 mod 2^32(넘침도 원본대로: 예 7fffffff − ffffffff = 80000000 → 음수).
- [F] **부호 있는 WORD 비교**(`b6d90 CMP.W 42(A0),D0; BLE`): 두 WORD의 부호 비교(`ofr13_signed_word`). **무부호 WORD**(`71fd0 CMPI.W #10; BCS`), **무부호 BYTE**(`cc8c0 CMPI.B #1b; BCC`), BYTE 같음(`718a0 CMPI.B #6`, `71fe8 CMPI.B #1`, `7202c CMPI.B #40,6f`, `d167c CMP.B`), WORD 같음(`ccbe2`..`ccc48 CMPI.W #1..#4`).
- [F] **WORD / BYTE 대상은 하위만 바꾼다**: `SUBI.W #1800,D7`, `EXT.W D0`, `EOR.W D7,D0`(`70f60`), `MOVE.W D0,D1` `ADD.W D1,D0`(`71858`/`71860`), `ANDI.W #1f,D0` `ADD.W D0,88`(`71f3a`), `MOVE.W 8e,D0; SUB.W 42,D0` `NEG.W D0`(`71fc2`/`71fce`), `SUBQ.W #1`(`72000` 88, `7210c` 8a, `bfd2c` a4, `d172e` 76: 메모리 WORD), `MOVE.B 64,D1` `EOR.W D0,D1`(`720e0`), `SNE.B`/`SEQ.B`, `ANDI.W #ff` `ADD.W`(`cc8d2`), `MOVE.W #0,5e`(`cc8c0`: WORD 5e / 5f 둘 다 0), `ADDI.W #18,32` `ADD.W D0,2e`(`d161a`/`d1636`), `MOVE.W -7ff2(A5),D0; ANDI.W #3`(`d1670`: 음수 변위는 부호 확장). `MOVEQ`·`MOVE.L`·`EXT.L`·`ADDI.L`·`SUB.L`·`NEG.L`(레지스터 `cca6a`, 메모리 `720f2`)·`SWAP`·`ASR.L`은 LONG 전체.
- [F] **`720e0`의 부호 시험**: `BTST #0,15; SNE.B D0; MOVE.B 64(A6),D1; EOR.W D0,D1; BPL`. `SNE`와 `MOVE.B`는 하위 BYTE만 바꾸므로 `EOR.W` 결과의 bit 15는 D0 / D1의 앞 값 bit 15 둘의 XOR다(BYTE 64와 SNE 결과는 bit 0..7에만 들어감). C++는 원본대로 WORD로 XOR하고 bit 15를 본다(`rules_b`가 D0 / D1의 위 BYTE를 바꿔 확인) [I: 원본의 의도는 `EOR.B`였을 수 있다].
- [F] **`70f60`의 부호 시험**: `SEQ.B D0; EXT.W D0`가 D0.W를 0000 / ffff로 만들고 `EOR.W D7,D0`의 bit 15 = (BYTE 15 bit 0 clear) XOR (D7.W − 1800의 bit 15).
- [F] **`cca5a`**: `MOVEQ #0,D0; MOVE.W (A0),D0; SWAP D0` → D0 = WORD << 16, BYTE 15 bit 0 clear면 `NEG.L D0`.

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `2986` `2a00` `8ebe` `1ab80` `1c356` `43e34` `491b6` `49214` `4970a` `49a58` `49f8c` `49fc6` `4ae4a` `4be06` `4be2c` `4be34` `4bfa4` `702cc` `70302` `703f6` `705ca` `72d66` `72dd2` `b4334` `c6a96` `cca76` `cdc1c`, 앞 단위 FR10 `70f84` `70fd2` `70ffa` `7102e`, FR11 `b4030` `b6dac`, FR12 `717c8` `722da`, RTS 복귀(`b450c` `bfd40` `bfd9e` `c553a` `c5590` `cc94a` `cca6c` `ccc80` `d16ac`).
- [F] **뒤 단위 정지**(실행되지만 뒤 단위가 가짐; V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS` 앞 3개): FR14 `71874`(`71870 BNE`의 fall-through) `d1632`(`d162e BNE`의 fall-through) `d177e`(`d177a BCC`의 Set 쪽 fall-through).
  - FR13 run이 지나갈 수 있는 FR12의 남은 정지 `7177a` `71786`(FR14), C1~C9의 남은 정지 12개(pc10 `EXIT_STOPS[:12]`)도 fr13 `EXIT_STOPS`(모두 17개)에 넣었다. FR11·FR10의 뒤 단위 정지는 FR13이 모두 routing했다. TRAP `b3e58`(FR11) `b3eac`(FR1)는 FR13 run이 `bfd34 JSR b4030`으로 FR11 handler를 거칠 때를 위해 `TRAPS`에 둔다.
  - 계산 점프 `cc8da`의 routing 밖 칸 26개도 정지다(V1 `JUMP_PCS`, 실제 ROM 차분 `UNR_FR13TAB`).
- [F] 직선 fall-through로 범위를 벗어나는 곳: `70f7e`(→ FR10 `70f84`), `70fcc`(→ FR10 `70fd2`), `70ff8`(→ FR10 `70ffa`), `71028`(→ FR10 `7102e`), `717c2`(→ FR12 `717c8`), `b6da6`(→ FR11 `b6dac`), 그리고 위 뒤 단위 정지(`71860` `d161a` `d177a`의 fall-through 쪽). 재관측에서 새로 보인 PC가 없어 가려진 연속은 없다(결정 1).

### block 경계·복귀를 넘는 flag(결정 4)

FR12 방식대로 block 첫 명령부터 flag를 정하는 명령까지 훑었다(`work/flagscan_fr13_v1.txt`). 그리고 FR13 출구 대상·RTS 복귀 PC에서 FR13이 남긴 flag를 읽는 곳을 따로 훑었다(`work/exitflags_fr13.txt`; 대상 `work/exitflags_targets_fr13.txt`: 출구 전부와 RTS 복귀 PC `4a354` `4a43e`(interpreter) `b46ac`(FR2 item 처리기 호출자)). X를 읽는 명령은 없다.

- [F] **C 소비 block 10개**(Clear 쪽 / Set 쪽; Unknown C면 `objects fr13 caller requires known carry`): `716bc BCC 716c6` `71a6e BCC 71a78` `72102 BCC 7210c` `722cc BCC 722d6` `bfd94 BCC bfd9e` `c5586 BCC c5590` `d172a BCC d173c` `d177a BCC d1670`(모두 `49fc6`), `71f30 BCC 71f42`(`705ca`: N15 `705f8` Set / `705fe` Clear), `d16a2 BCC d16ac`(`1ab80`: N05 `1aafc` Set / `1abd4` Clear).
- [F] **C를 넘기는 block**: RTS `b450c`. `b44ac` / `b4506`이 부르는 C5 `1c356`의 C(C5 `1c4aa` Clear / `1c494` Set)를 FR2 `b46aa JSR (A1)`의 복귀 `b46ac`(`MOVEM.L (A7)+,D0/A0; BCS`: MOVEM은 flag를 바꾸지 않음)로 넘긴다. FR2 `b46ac`는 기존대로 known C를 읽거나 checked 오류다. dispatcher의 carry 보존 목록에 소비자 10개와 함께 넣었다(FR12 `4d86c`와 같은 방식).
- [F] **Z가 경계를 넘는 곳: `71fe4 BEQ.W 72000`**. Z는 `71fe2 TST.B D0`의 것이다(`71fde BSR 70302`의 복귀 PC가 `71fe2`라 그 block이 `TST.B` 하나뿐이고, 계획의 block 시작에서 `71fe4`가 따로 나뉨). `71fe4`로 오는 길은 `71fe2`의 fall-through 하나뿐이고(ROM 전체 참조 검색에 `71fe4`를 대상으로 하는 분기 없음) 사이에 명령이 없다. **`71fe4`는 Z = (D0.B = 0)으로 다시 계산한다**(FR10 `70ff4`와 같은 방식). 출처가 레지스터라 메모리 접근이 없고 flag-source 오류가 생길 수 없다. V1·단위 시험은 `71fe4`를 직접 들어가지 않고(`Z_READERS`, single 5 = native SR Z = (D0.B = 0)) `71fe2` 쪽 사슬로 확인한다.
- [F] RTS로 돌려주지만 읽는 쪽이 없는 flag: `bfd40` `bfd9e` `c553a` `c5590` `cc94a` `ccc80` `d16ac`(node callback의 RTS → object loop), `cca6c`(interpreter callback → `4a354`/`4a43e MOVE.W (A7)+,-7ff0(A5)`).
- [F] **그 밖의 Z / N은 block 안에서 정해진다**: `70f60 EOR.W`(BMI WORD), `71622`.. `TST.W 9c`(BNE), `7188e TST.W 3a`(BPL WORD), `71fc2 SUB.W`(BPL WORD), `72000 SUBQ.W`(BPL 새 WORD), `7210c SUBQ.W`(BEQ 새 WORD), `bfd2c SUBQ.W`(BMI 새 WORD), `d172e SUBQ.W; BCC`(borrow: 앞 WORD = 0), `d1670 ANDI.W #3`(BNE), `cc8b4`/`cc8c0 MOVE.B`(BEQ), `720e0 EOR.W`(BPL), `ccbc0 MOVE.W 8c`(BNE), BTST(Z만). 묶인 Bcc 쌍은 없다.
- [F] **flag 생산 block**: FR13 안에는 C를 정하는 block이 없다(`CLR` / `MOVE`류는 C를 지우지만 읽는 곳이 없음; 모델은 Unknown). 소비자 10개와 RTS `b450c`만 들어오는 C를 지킨다.

### IO 실행 run과 frame

- [F] 실행 run 8개(X1~X4 × case 68·94), 처음 frame은 위 "재확인과 범위". FR13 node는 pool `100800..104c00`의 여러 node다(`work/natscan_fr13_cand.out`: frame 시작 상태의 callback `71622` `71696` `717e8` `71884` `719f8` `71a62` `71f2c` `72040` `720d6` `7224c` `722b6` `bfd2c` `bfd48` `bfd88` `c554c` `c557a` `d15c4` `d1644` `d16ae` `d16fa` `d1740` `d176e`, 그리고 FR13으로 들어가는 routing된 callback `b3dbc`(item 자식) `70e2a` `70f3e` `71468` `713d8`(FR10) `c5470` `c5432` `b6d6a` `b6d82`(FR11) `716ca` `7179a`(FR12); `71fac`는 frame 시작 상태에 없다).
- [F] **IO 예측(FR13 연결)**: 7,977 → **10,374**(+2,397; 재관측 `reobs/fr13v1`, 계획과 같음). 첫 정지는 E 6 run(E2 `3144`)과 D 2 run(FR14 `3643e` / `7177a`)이다(위). [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다.
- [F] 원래 IO 관측은 FR13 코드를 실행하지 않는다(계획 §10.4: X run에서만 실행). 일치 173,966은 그대로여야 한다(작업자는 돌리지 않음; 메인 runner).

## 공통 규칙·native 검증 계획

FR2..FR12, C1~C10 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr13.cpp`, 함수 `animation_objects_fr13_block`. 오류 문자열은 `unsupported animation objects fr13 PC`(범위 안 내부 PC 직접 진입), `objects fr13 caller requires known carry`(C 소비 block 10개에 Unknown C), `unsupported animation objects fr13 jump target`(`cc8d2`의 색인 > 1a) 세 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(27 범위, FR12 줄 뒤; `)ok=animation_objects_fr13_block(c);`를 같은 줄에 둔다), `carry_preserving_pc`의 FR12 묶음 뒤에 주석 달린 case 묶음 하나(소비자 10 + RTS `b450c`), `animation_machine_internal.h`에 선언 하나(FR12 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# objects FR13 refresh:` 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 곧바로 들어감 12개는 쓰고 그 값으로 들어가고, 쓰기만 하는 17개는 쓰고 다음 block으로 간다. `70ff8`은 A0 LONG을 쓴다.
- **자료 읽기**(live bus): node field(A6: BYTE `14` `15` `19` `1a` `5e` `61` `6f` `82`, WORD `2e` `32` `3a` `42` `5e`(쓰기) `68`/`1e`(쓰기) `76` `7a` `7c` `78`(쓰기) `88` `8a` `8c` `8e` `9c` `a4` `20`(쓰기), LONG `0`(설치) `22` `36` `3a` `42` `64` `8e`), A0 record(WORD `42` — `b6d90`; WORD `0` — `cca5a`), A5(WORD `-7ff2` = `10000e` — `d1670`), 고정 ROM·bank(위 "계산 점프와 표"). 단위 시험은 고정 ROM·bank 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): 기록 `d13a4..d13ac`(`1ab80`의 두 LONG: `ffe8ff80 00300040`; FR1c 코드 `d13b4` 앞의 자료), bank 창 LONG `2000d0` → `2a1000`(+64 / 68 / 88 / 104 / 180 / 188) `2000d4` → `2a2000`(+4 / 10 / a4 / 1cc / 1d4) `2001c0` → `2a3000`(+c) `200080` → `2a4000`(+148) `200090` → `2a5000`(+4 / 8 / c). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** 위 "정수 연산(결정 3)". 표 첨자 `(PC,D0.W)`의 변위는 4 × BYTE(0..3fc)라 부호 확장이 필요 없다(guard가 0..68로 묶음).

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `49170da4b41a73e9cbb8d1684e0fa261fedc2ece6bab2e1e77a0b2dbe8e0c5f2` → `88e68c75bd863b4605891d5204e9adde48fa3168a320c1350662b70b840124e9`, `animation_machine_internal.h` `3a5dc9af01e57baf08320a0ec5ba744c82ea85679e150a5e912a7d1212ed8c84` → `00dfe0efd2b4192818b1b413cd19bf697776492da5fd42eb2670735f367dcca6`(옛 값은 `# objects FR13 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 작업 트리와 scratch clone root에서 확인했다(아래 "검증 수치").
- [F] **FR10 시험 생성기·시험**(`tools/generate_animation_machine_objects_fr10_test_table.py`, `engine/tests/animation_machine_objects_fr10_test.cpp`; 오류 행. 이전 = FR13 PC에서 `unsupported animation machine PC`. FR13이 그 PC를 routing해서 C++가 FR13 코드를 실행하므로 바뀜. FR11·FR12 선례대로 실패 PC를 지키거나 경로를 따라 옮김):
  - `error-70f4e-then-70f60` → `error-70f4e-then-70f84-odd-stack`: FR13 `70f60` → `70f7e` → FR10 `70f84 JSR 49fc6`의 push가 홀수 A7에서 `program bus requires even WORD/LONG address`(stop `49fc6`). 고치기 전에는 `make test`가 `70f4e: missing or ambiguous physical program bus ROM byte expected unsupported animation machine PC`로 실패했다(`49fc6` 쪽이 선언 밖 ROM을 읽음).
  - `error-70fc2-then-70fcc`: 홀수 node(A6 = `10e001`), FR13 `70fcc`의 `MOVE.L #71468,(A6)`가 `invalid animation machine write size/alignment`, 실패 PC `70fcc` 그대로.
  - `error-71020-then-71028` → `error-71020-then-72dd2-odd-stack`: FR13 `71028` → FR10 `7102e` → `72dd2 JSR 4b54e`의 push가 홀수 A7에서 실패(stop `4b54e`).
  - `error-70ff0-then-70ff8`, `error-70fe4-then-70ff8`: 홀수 node, FR13 `70ff8`의 `MOVE.L A0,(A6)`가 alignment 오류, 실패 PC 그대로.
  - `error-70f94-then-70fcc` → `error-70f94-then-70fd2-odd-stack`: FR11 `70fac` → FR10 `70fc2` → FR13 `70fcc` → FR10 `70fd2 BSR 7028e`의 push가 홀수 A7에서 실패(stop `7028e`).
  - 생성기를 다시 돌려 그 6행만 바뀜을 확인했다(`work/fr10_test_before_fr13.cpp` 대비 diff). fixture 수 1,074 그대로.
- [F] **FR11 시험 생성기·시험**(`tools/generate_animation_machine_objects_fr11_test_table.py`, `engine/tests/animation_machine_objects_fr11_test.cpp`; 같은 이유):
  - `error-b6d8c-then-b6d90`: 홀수 A0, FR13 `b6d90`의 `CMP.W 42(A0),D0`가 `program bus requires even WORD/LONG address`, 실패 PC 그대로(이전 `unsupported animation machine PC`).
  - `error-bfcea-then-bfcfa`: 홀수 A7, FR13 `bfcfa JSR 2986`의 push가 실패, 실패 PC 그대로(stop `2986`).
  - `error-c5496-then-c54ba` → `error-c5496-then-c5520`: 홀수 node, BYTE 5e = 2 → FR11 `c54a6` → FR13 `c54ba` → `c5520`의 `MOVE.L #c5432,(A6)`가 alignment 오류.
  - 생성기를 다시 돌려 그 3행만 바뀜을 확인했다(`work/fr11_test_before_fr13.cpp` 대비 diff). fixture 수 958 그대로.
- [F] **FR12 시험 생성기·시험**(`tools/generate_animation_machine_objects_fr12_test_table.py`, `engine/tests/animation_machine_objects_fr12_test.cpp`; 같은 이유):
  - `error-71532-then-71682`: 홀수 node, FR13 `71682`의 `MOVE.W 7a(A6)`가 `program bus requires even WORD/LONG address`, 실패 PC 그대로.
  - `error-717ae-then-717c2` → `error-717ae-then-717c8-odd-stack`: FR13 `717c2` → FR12 `717c8 JSR 4bfa4`의 push가 홀수 A7에서 실패(stop `4bfa4`).
  - 생성기를 다시 돌려 그 2행만 바뀜을 확인했다(`work/fr12_test_before_fr13.cpp` 대비 diff). fixture 수 1,127 그대로.
- [F] **V1 spec**:
  - `fr10.py`: `ROUTED_LATER`에 FR13 진입 `70f60` `70fcc` `70ff8` `71028`를 더했다(그 run은 그 PC에서 계속 멈춘다; `EXIT_STOPS`는 그대로). 오류 fixture `70f4e-then-70f60` → `70f4e-then-70f84-odd-stack`, `70fc2-then-70fcc`(홀수 node), `71020-then-71028` → `71020-then-72dd2-odd-stack`, `70ff0-then-70ff8` / `70fe4-then-70ff8`(홀수 node), `70f94-then-70fcc` → `70f94-then-70fd2-odd-stack`(위 생성기와 같은 뜻).
  - `fr11.py`: `ROUTED_LATER`에 `b6d90` `bfcfa` `70f60` `70fcc` `70ff8` `71028`, `JUMP_LATER`에 `c54ba` `c54d6`(FR11 run은 그 PC에서 계속 멈춤). 오류 fixture `b6d82-then-b6d90`(홀수 node: `b6d82`는 BYTE 9d만 읽고 `49392`가 A0를 플레이어 기록으로 바꾸므로 홀수 A0 대신 홀수 node로 `b6d90`의 `MOVE.W 42(A6)`에서 실패), `bfcea-then-bfcfa`(홀수 A7), `c5496-then-c54ba` → `c5496-then-c5520`(홀수 node).
  - `fr12.py`: `ROUTED_LATER` `()` → (`71682` `717c2` `b6d90` `bfcfa` `70f60` `70fcc` `70ff8` `71028`). 오류 fixture `71532-then-71682`(홀수 node), `717ae-then-717c2` → `717ae-then-717c8-odd-stack`.
  - `pc10.py`: `ROUTED_LATER`에 `70f60` `70fcc` `70ff8` `71028`(FR11 때와 같은 방식).
  - `fr2b.py`: `build()`의 "routing 밖이어야 하는 자료 / 정지 PC" 목록 (`702fa` `70d72` `76922` `71884`) → (`702fa` `70d72` `76922`). `71884`가 FR13 시작(`71876`의 설치 값, FR2b `706f4`가 쓰기만 하는 값)이 되었다. 남은 routing 밖 FR2b 정지 설치 값은 없다.
- [F] **바뀌지 않음(확인)**: 저장소 tools·시험·실행부에서 FR13 범위 안 PC(와 표 `cc8de`의 칸)를 쓰는 곳을 전수 검색 `tools/fr13refs_repo.py` → `work/fr13refs_repo_v1.out`으로 찾았다. 6 / 5자리 0x 표기와 tools·docs/analysis/data·config의 JSON까지 다시 훑었다(`docs/analysis/data/animation-machine-frame-head-leaders.json`의 걸린 값은 10진 숫자열이라 무관).
  - 정지 전용·값 전용 행(정지 검사가 dispatch보다 먼저라 routing이 바뀌어도 같음): FR10 시험·spec(정지 `70f60` `70fcc` `70ff8` `71028`, 표 `70d72` 값 `71622`, `cca5a` `ccbc0`의 범위 끝), FR11 시험·spec(정지 `b6d90` `bfcfa`, 표 칸 `c54ba` `c54d6` 정지와 `c5520` `c554c` 범위 끝), FR12 시험·spec(정지 `71682` `717c2`, 범위 끝 `717e8` `71f2c`), FR4 시험(`TARGETS`의 `cc852` 정지), N15 시험·실행부(`cc8b4` 경계 정지), B1a 시험·spec(`boundary-stop-78d3a-cc8b4` 정지 전용), FR1c 시험·spec(범위 끝 `d159e`), FR2b 실행부(설치 값 `71884` 쓰기만), U13 시험·실행부(설치 값 `72040` 쓰기만), FR3 실행부(`c554c` 쓰기만).
  - 검증기(`tools/verify_animation_machine_*.py`)에는 FR13 PC를 이웃·탐침·"unsupported PC" 기대값으로 쓰는 literal이 없다(stage_area의 `UNROUTED_NEIGHBOURS`, buffer_cue·scene_update의 outside 목록, motion_walk·objects_g2/g3 포함 전수). 그래서 이 단위에서 바꾼 검증기는 `CPP_PINS`와 `SOURCES`뿐이다. [U] artifact에서 기대값을 읽는 검증기의 동적 경로는 메인의 통합 sweep이 확인한다.
  - `make -j4 all test`가 위(FR10·FR11·FR12 생성기 행) 말고 기존 시험이 모두 그대로 통과함을 확인했다.
- [I] 원래 IO 관측과 frame 비교(d1·controller·irq·demo)는 FR13 코드를 실행하지 않으므로 결과가 같아야 한다. 메인 runner가 확인한다.

## 결정

1. **범위: 207 block, 27 범위(계획 그대로).** 가상 routing 재관측에서 새로 보인 PC가 없고(숨은 직선 block 0), 범위 밖에서 범위 안 비시작 PC로 오는 실제 분기도 없다. 실행 칸 `c54ba` `c54d6`(FR11 메인 결정)·`cc8f6`·FR4 칸 `cc852`만 전사한다. FR12가 남긴 `71682` `717c2`는 FR13(메인 결정). 뒤 단위의 짧은 fall-through `71874` `d1632` `d177e`(FR14)는 계획 배정대로 정지로 둔다. 예측 10,374(+2,397).
2. **계산 점프 `cc8da`.** 색인 ≤ 1a(같은 함수의 guard `cc8c0`)면 PC := `cc8de` + 4 × 색인이고 routing이 판정한다(`cc8f6`만 FR13 block). 넘으면 checked jump-target 오류. 받는 계산 착지(`c54ba` `c54d6` `cc852` `b44ac` `cca5a` `d159e` `71622`)는 기존 실행부의 규칙 그대로다. bank 창 LONG은 live bus로 읽고 상한을 검사하지 않는다.
3. **정수 연산**: ASR.L #5는 부호 채움, LONG / WORD 비교는 정확한 부호·무부호 비교, WORD / BYTE 대상은 하위만, `720e0`의 `EOR.W`와 `70f60`의 `EXT.W`/`EOR.W`는 원본 폭 그대로.
4. **flag.** C 소비자 10개는 known C를 읽거나 checked 오류. RTS `b450c`가 `1c356`의 C를 FR2 `b46ac`로 넘긴다. `71fe4`는 `71fe2 TST.B D0`의 Z를 D0.B에서 다시 계산한다(FR10 `70ff4` 방식). 그 밖의 Z / N 경계는 없다.
5. **V1 natural family.** 확장 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)이 읽는다. pool `100800..104c00`의 node가 FR13 callback(23개) 또는 FR13으로 들어가는 routing된 callback(`NATURAL_ROUTED` 12개)을 callback LONG으로 가진 frame 220개(`work/natural_fr13_cand.json`: run과 callback마다 처음·처음 여덟 가운데·마지막 frame). natural fixture는 300개다.
6. **앞 단위 spec·시험.** FR10·FR11·FR12의 뒤 단위 정지 가운데 FR13 진입을 fr10·fr11·fr12·pc10의 `ROUTED_LATER`(fr11은 `JUMP_LATER`도)에 두어 그 run은 계속 그 PC에서 멈춘다. 오류 fixture는 실패 PC를 지키거나 경로를 따라 옮긴다(위). fr2b의 unrouted 목록에서 `71884`를 뺀다.
7. **다음.** FR13 연결로 확장 관측 IO 10,374(+2,397)을 메인 runner가 확인한다. 다음 단위는 E2(`3144` / `e695a` 계열, 6 run)와 FR14(`3643e` `7177a` 등, 2 run)다. FR14는 계획 시작 목록에 FR13 뒤 단위 정지 `71874` `d1632` `d177e`와 FR12 정지 `7177a` `71786`, FR4 칸 `cc7b8`을 가진다.

## 미확인

- [U] node field·전역 값의 의미(BYTE `5e` `63` `6f` `82`, WORD `7a` `7c` `88` `8a` `8c` `9c` `a4` `76`, LONG `64` `8e` `42`, `10000e`). 이름(방향, 추적 속도 제한, 소리, 자식 생성, 화면 상자)은 동작에서 붙인 [I]이다. 어떤 적·탈것·item인지는 정하지 않았다.
- [U] `720e0`의 `EOR.W`가 원본의 의도인지(`EOR.B`였는지). 동작은 원본 바이트대로 재현한다.
- [U] 표 `cc8de`의 실행되지 않은 칸(`cd0fe` `cd50e` `ccc88` `ccf4e` `ccd74` 쪽)과 FR4 칸 무리(FR4b/FR4c)의 관계. 이 관측에서는 칸 6만 실행된다.
- [U] IO 관측에서 실행되지 않은 이 단위의 분기 쪽(위 "IO 실행"의 46개)은 V1 선언 상태·natural·실제 ROM 차분·단위 시험으로만 확인했다.
- [U] `bfcfa` / `d159e`의 2986 안의 28ae 실패는 기존 2986 실행부의 caller-X 한계로 C++에서 checked 오류다(실제 ROM 차분의 문서화된 분류).
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC).
- [U] natural fixture의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C10, FR10~FR12와 같음).
- [U] `71fe2`/`71fe4` 사이의 TB 경계가 왜 생겼는지(관측기의 TB 기록 방식) — 동작에는 영향이 없다.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr13.cpp`(case label 207 = `starts_fr13_final.txt`와 집합 일치; 공용 함수 `ofr13_get` `ofr13_put` `ofr13_bit` `ofr13_btst` `ofr13_test` `ofr13_carry` `ofr13_install` `ofr13_asr` `ofr13_signed_long` `ofr13_signed_word` `ofr13_bank_anim` `ofr13_anim` `ofr13_ease` `ofr13_spawn`), `engine/tests/animation_machine_objects_fr13_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_d`), `tools/generate_animation_machine_objects_fr13_test_table.py`(생성기; FR12 생성기 꼴 + FR10의 flag reader 행(single 5), 계산 점프가 표를 벗어난 native run을 버림, V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 100초), `tools/unit_fixture_specs/fr13.py`(V1 spec; FR12 spec의 공용 부분, 단위 부분 교체, `EXIT_STOPS`(17), `TRAPS`(`b3e58` `b3eac`), `CONSUMERS`(10), `PASS_SET`(`b450c`), `DATA_SET`(`71fe2`), `Z_READERS`(`71fe4`), `JUMP_TARGETS`(`cc8da`의 27칸), `NATURAL_ENTRIES`(23 + 12), natural family는 확장 관측 pack; world의 WORD `8e`는 0..7이 주(FR13 `b6d90`이 이어 들어가는 FR11 `b6dac`의 표 anim 첨자), d1xxx node의 LONG 76은 handler가 아닌 count). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `work/starts_fr13_final.txt`(SHA256 `7d9836ea…`).

- **`70f60..70f84`(3)**: `70f60 70f74 70f7e`
- **`70fcc..70fd2`(1)**: `70fcc`
- **`70ff8..70ffa`(1)**: `70ff8`
- **`71028..7102e`(1)**: `71028`
- **`71622..716ca`(15)**: `71622 7162a 71652 71656 7167e 71682 71696 7169c 716a6 716ac 716b0 716b6 716bc 716c0 716c6`
- **`717c2..717c8`(1)**: `717c2`
- **`717e8..71874`(7)**: `717e8 717f0 71818 7181c 71844 71858 71860`
- **`71876..718c8`(10)**: `71876 71884 71888 7188e 71896 718a0 718a8 718ae 718b8 718c4`
- **`719f8..71a80`(11)**: `719f8 71a00 71a28 71a2c 71a54 71a62 71a68 71a6e 71a72 71a78 71a7c`
- **`71f2c..72118`(49)**: `71f2c 71f30 71f34 71f3a 71f42 71f4a 71f72 71f76 71f9e 71fac 71fb6 71fbc 71fc2 71fce 71fd0 71fd8 71fde 71fe2 71fe4 71fe8 71ff0 71ffa 72000 72008 7200e 72018 7201e 72026 7202c 72036 7203c 72040 72048 72070 72074 7209c 720b0 720b6 720c0 720c6 720d6 720e0 720f2 720f6 720fc 72102 72106 7210c 72114`
- **`7224c..722da`(11)**: `7224c 72254 7227c 72280 722a8 722b6 722c0 722c6 722cc 722d0 722d6`
- **`b44ac..b44b2`(1)**: `b44ac`
- **`b4506..b450e`(2)**: `b4506 b450c`
- **`b6d90..b6dac`(3)**: `b6d90 b6d9c b6da6`
- **`bfcfa..bfda0`(16)**: `bfcfa bfd10 bfd1a bfd2c bfd34 bfd3a bfd40 bfd42 bfd48 bfd70 bfd82 bfd88 bfd8e bfd94 bfd98 bfd9e`
- **`c54ba..c54be`(1)**: `c54ba`
- **`c54d6..c54da`(1)**: `c54d6`
- **`c5520..c5540`(3)**: `c5520 c5534 c553a`
- **`c554c..c5592`(7)**: `c554c c5574 c557a c5580 c5586 c558a c5590`
- **`cc852..cc856`(1)**: `cc852`
- **`cc8b4..cc8de`(4)**: `cc8b4 cc8bc cc8c0 cc8d2`
- **`cc8f6..cc8fa`(1)**: `cc8f6`
- **`cc94a..cc94c`(1)**: `cc94a`
- **`cca5a..cca76`(3)**: `cca5a cca6a cca6c`
- **`ccbc0..ccc88`(17)**: `ccbc0 ccbc8 ccbde ccbe2 ccbea ccc00 ccc04 ccc0c ccc22 ccc26 ccc2e ccc44 ccc48 ccc50 ccc66 ccc6a ccc80`
- **`d159e..d1632`(7)**: `d159e d15b4 d15be d15c4 d15fe d160c d161a`
- **`d1636..d177e`(29)**: `d1636 d1644 d164e d1654 d166a d1670 d167c d1688 d1692 d1698 d16a2 d16a6 d16ac d16ae d16d6 d16fa d1704 d170a d170e d1724 d172a d172e d1736 d173c d1740 d1768 d176e d1774 d177a`

## 검증 수치

작업자 최종 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j4 all test`(최종 실행부·시험): 종료 0, 경고 0, Assert 0, Python 310 OK, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄(`trial_logs/make_final.log`). FR13 시험 줄: `animation machine objects fr13: 909 fixtures (536 single-block, 292 path, 18 producer chain, 20 declared C, 43 checked error (6 with a later failing PC), 33 kept C), 207 blocks, 4326 calls, 96027 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 출구 중 stop이 아닌 것 0, 실제 사슬 3개(`71f2c`→`71f30`(`705ca`), `d1698`→`d16a2`(`1ab80`), `71fe2`→`71fe4`(Z)), 표 `cc8de`에서 stop이 된 routing 밖 칸 5개(`cc8de` `cc8ee` `cc90a` `cc92e` `cc946`). `49fc6` 사슬 여덟은 `49fc6`이 bank 장치에 써서 native run이 버려졌고, `71fde`→`71fe4`(`70302`)는 선언 밖 ROM(`494c0`의 `702fa`)을 읽어 한쪽만 나와 선언 행만 있다(V1에서는 두 쪽 모두 나옴). 생성기를 다시 돌려 FR13 시험 파일이 바이트 단위로 같음을 확인했다(SHA256 `02fdb306686b6af5…`, `trial_logs/gen_repro.log`). FR10 시험 줄은 fixture 1,074, FR11은 958, FR12는 1,127 그대로(오류 행 6 / 3 / 2만 바뀜).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, `work/ubsan.sh`, FR13 시험): 빌드 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_build.log` `ubsan_fr13.log`).
- [F] V1 fr13(작업자, `--workers 3`): fixture 2,126개(match 1,150, error 966, mismatch 10; natural 300) failed 0, `ok` true, 방문 시작 207/207, 빠진 후속 없음, 도달 못한 분기 결과 없음, carry oracle Unknown/Clear/Set = 873/78/199(`trial_logs/v1_fr13_final.log`, `work/v1/fr13_try3/report.json`). 앞선 두 시도: try1은 callee `b6d90`의 world가 없었고(FR11 `b6dac`로 이어지는 표 anim이 WORD 8e로 ROM 표 밖을 읽어 random script의 TRAP; WORD 8e를 0..7 위주로 둠), try2는 node `bfd2c`의 hint가 LONG 76에 handler 아닌 값을 넣어 FR11 jump-target 오류(d1xxx node만 count 값을 씀)와 빠진 후속 둘(`705ca` Set 쪽: 지도 WORD `5b88(A5)` + 72 hint, `70302`의 D0 ≠ 0: BYTE 82 / 86 / 87 hint)이었다.
- [F] V1 회귀(작업자, `work/v1_regs.sh`, `--workers 3`; `work/v1/v1_regs.txt`): pc1 1,264, pc2 1,743, pc3 1,829, pc4 1,873, pc5 1,755, pc6 1,856, pc7 2,077, pc8 986, pc9 2,347, pc10 1,334, se1 2,102, fr9 1,415, fr10 2,170, fr11 2,170, fr12 2,302(모두 failed 0, `ok` true; FR12 기록과 같은 수). FR13 PC를 정지·값·범위 끝으로 가진 fr2b 1,761, fr4 1,629, b1a 2,801, fr1c 1,755, fr1 1,631도 돌렸다(`--workers 2`; 모두 failed 0, `ok` true). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·op, WORD/BYTE → LONG, 복귀 PC·호출 대상, carry tag, mask, 상수·설치 값, `ofr13_btst`/`ofr13_test`/`ofr13_bank_anim`/`ofr13_anim`/`ofr13_ease`/`ofr13_spawn` 인자) + 손으로 고른 helper·block 변이(ASR.L 논리·채움·0 쪽 반올림, 부호 LONG / WORD 비교의 무부호화, bank anim의 A0·D0 폭·LONG 22 생략, anim의 D0 폭·WORD 20 폭, ease의 순서·폭·저장, spawn의 D0 폭, `70f60`의 EXT 없음·SEQ 반전·D7 LONG·BYTE 부호, `71860`의 EXT 없음·LONG 덧셈·WORD ADDI, `71fc2`/`71fce`/`71fd0`의 부호·폭, `71fe4`/`71fe8`의 WORD / LONG 시험, `72000`/`7210c`/`bfd2c`/`d172e`의 결과 시험, `7209c`/`720b6`의 경계·폭·무부호·순서, `720e0`의 EOR.B·BYTE 부호·MOVE.L·SNE 반전, `720f2` WORD, `b6d90` 무부호·엄격·LONG, `cc8c0`의 BYTE 지움·부호 guard, `cc8d2`의 한계 6c / 64·guard 없음·AND 없음·× 2·LONG AND, `cca5a`의 SWAP 없음·MOVEQ 없음·NEG.W, `d1670`의 AND 없음·A5 양수 변위, `d161a`의 LONG 덧셈·MOVEQ WORD, `71858`·`b44ac`·`71f3a`의 폭, `bfd10`의 MOVEQ WORD) + dispatcher carry 목록 11개·범위 52개를 적용해 만든 것, 780개; `--workers 4`): 1회째 `killed 765 of 780`(`trial_logs/mut_first.log`). 생존 15개 중 5개는 시험 빈틈이었고 규칙으로 메웠다(`ccbc0`의 WORD 8c 선택 셋(`ccc04` `ccc26` `ccc48`의 `CMPI.W`를 BYTE로 읽는 변이: WORD 8c = 102 / 103 / 104), A5 음수 변위 둘(`ofr13_get`의 부호 확장 없음, `d1670`의 양수 변위: A5 = `1f8000`이면 `-7ff2(A5)` = `1f000e`(work RAM 거울)이고 양수면 `20000e`); 다섯 변이 다시 실행 `killed 5 of 5`, `trial_logs/mut_gaps.log`). 남은 10개는 동치다(`mut/equivalents.txt`, 사례별 이유: `70f60`의 EXT.W에서 ff00과 OR하는 위 BYTE와 SEQ 값이 00 / ff뿐인 bit 6 / 7, `71860`의 EXT.L이 하위 WORD만 읽는 LONG 덧셈 둘, `7209c`/`720b6`의 경계값에서 두 갈래가 같은 D0을 쓰는 BLE / BGE 셋, `7210c`의 16 bit 읽기, 8 미만 bit 번호, `am_write`의 자체 mask). 규칙을 더한 뒤 전체 2회째 `killed 770 of 780`(`trial_logs/mut_second.log`), 남은 10개가 동치 목록과 같다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`, 메인 runner용), `real_fr13.py`(FR12 harness에 FR13 world(`fr13_world`: BYTE 14 / 15 / 19 / 1a / 5e / 61 / 6f / 82, WORD 2e / 32 / 3a / 42 / 46 / 78 / 7a / 7c / 88 / 8a / 8c / 9c / a4, LONG 36 / 3a / 42 / 64 / 8e, WORD `10000e`, A0 record `FR13_REC`)·소비자 10·C pass `b450c`·Z reader `71fe4`(native SR Z = (D0.B = 0))·선언 정지(FR13의 뒤 단위 정지 3, FR12의 남은 정지 2, TRAP `b3e58` `b3eac`, C1~C9의 남은 정지, 계산 점프의 routing 밖 대상 `UNR_FR11TAB`·`UNR_FR13TAB`(26), routing 밖 FR4 표 칸 46)·`cb` 진입에 FR13으로 넘겨주는 FR10 `70f4e` `70fc2` `70ff0` `71020`, FR12 `7155e` `717ae`, FR11 `b6d8c` `bfcea` `c5496`, FR4 `cc822`, FR2 `b46a2`(item 기록 `b38a0` / `b3954`), N15 `72d86` `72dac`, B1a `78d3a`; 계산 점프 착지를 trace 전체에서 대조(`ALLOWED_FR13` = 표 `cc8de` 27칸, 앞 단위 표 그대로); 분류 `JUMPTGT13` 추가; `native_safe` 기본 유지)): 작업자 300건 seed 1 `mismatches 0`(`covered starts 193 of 207`; 문서화된 분류: 2986 실패 경로의 caller-X 5건(`b46a2` 2, `bfcea` `bfcfa` `d159e` 각 1), FR11 jump-target 1건(무작위 LONG 76의 `b4034`, `bfd2c` → `b4030` 경로); 깨끗이 멈추지 않은 native 197건 건너뜀(대부분 3,000,000 명령 안에 멈추지 않는 routing된 후속: `72dd2` `72d66`·interpreter 경로); native oracle abort 0, `trial_logs/real_n300_s1.log`). 앞선 30건 seed 11 시험도 `mismatches 0`(`trial_logs/real_t30.log`). 실행 중 FR13 소비자 10개와 `b450c`·FR2 `b46ac`·`71fe4`가 실제 생산자 뒤에 native 분기와 비교되었다.
- [F] **IO, 입력 확장 관측**(FR13 연결 뒤, `--workers 3`): run 12, native 비교 frame 14,500 가운데 일치 **10,374**(예측 10,374, 기준선 7,977 → +2,397), 불일치 0(beyond 0), C++ 오류 0, chain divergence 0, 수용 키 모두 true(`negatives_ok` 포함)(`trial_logs/io_ext_fr13.log`; `verification.json` SHA256 `a37f30eb782bcf1c…`, `frontier.json` `e3c6f44740fc132c…`, scratch `io_ext_fr13/`). run별 일치: P0 1,200, P1 1,200, X1 1,728, X2 1,792, X3 2,078, X4 2,376. 첫 정지 frame: X1 68 960, X1 94 768, X2 68 992, X2 94 800, X3 68 1,120, X3 94 958, X4 68 1,268, X4 94 1,108 — 재관측 예측(`reobs/fr13v1.stops`)과 run·frame이 모두 같다. 확인된 frontier PC는 `e695a`(E, 6 run; 재관측이 같은 frame에 적은 `3144`는 E helper 재분류이고 IO가 실행 순서로 `e695a`를 확정, [I] 같은 frame 안의 순서), `3643e`(D, 1 run), `7177a`(D, 1 run)로 E2와 FR14다.
- [F] 원래 IO 관측·frame 비교·legacy 검증기는 작업자가 돌리지 않았다(메인 runner).
- [F] `CPP_PINS`: 작업 트리와 scratch clone root(`work/mkroot.py`; 확인 뒤 symlink를 먼저 지우고 삭제)에서 파일 SHA와 같다(4 / 9 pin, 불일치 0, `trial_logs/pincheck_tree.log` `pincheck_root.log`).
