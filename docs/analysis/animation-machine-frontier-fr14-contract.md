# frontier 단위 FR14(입력 확장 관측의 영역 D 마지막 단위: C5 `2986` 자식 `3643e`(표 `1cc04` 칸 1: `1aa3a` 결과 bit 3 → WORD 76 anim 표 `363ae` / `36522`·소리 표 `363be`, LONG 36 / 3a를 0 / `fff00000` / `fffc0000` 쪽으로 1/16씩 당김(`364aa` / `36588`, `ASR.L #4`), `BSET #3,61`, 기록 `363a6`의 `1ab80` 화면 시험; `3657c`는 routing 밖 `2986` 자식 `365fc`의 `BRA.W` 대상), FR12 / FR13 뒤 단위 짧은 fall-through `7177a`·`71786`·`71874`(`NEG.L D0`)·`d1632`(`NEG.W D0; NEG.L D1`), stage event op 08 자식 `b5c34`(`b5c60`..`b5d56`: `4c0ac`, `490ba`, bank anim 1b3, 설치 `b5cec`, helper `b6056` / `b6084` / `b60c4`, BYTE 8a의 LONG 표 `b6280`, `4b54e` / `b60da` / `1aa7e` C, 선수 시험 `b60da`(`49392` / `4941e`; `b6128` Clear, `b6146` Set)와 계수 `b7ae4` / `b7af0`(`MOVEM.L D0/A2-A3`)), FR1 종류 기록 처리기 `c0d68`(부호 있는 WORD 42, `c6a96`, bank anim 1eb, 설치 `c0dc8`: `b4958` / `b4ab0` / `b4334`), FR4 표 `cc7ac` 칸 3 `cc7b8`(→ `cd0fe`: BYTE 5f / BYTE 15 bit 0 부호 시험, BYTE 7a, WORD 8c anim 선택, `cdd2e` 쓰기만), FR13 뒤 단위 정지 `d177e`(`4ae4a`, `8ff4`, bank anim d2, 설치 `d17e0`), 200 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §10.5 표의 FR14 행(계획 이름 D-5)과 §10.x 메인 결정, FR12 계약 결정 1·FR13 계약 결정 1(FR12 / FR13이 남긴 짧은 fall-through `7177a` `71786` `71874` `d1632` `d177e`는 계획대로 FR14)을 기준으로 삼는다. 구조·공통 규칙은 FR13 계약(`animation-machine-frontier-fr13-contract.md`; 확장 관측 단위, 정확 bitmap 재관측, 뒤 단위 정지의 처리), E2 계약(`animation-machine-select-e2-contract.md`; 범위 밖 실제 분기 대상을 시작으로 더함, V1 reinstall family), FR12 계약(MOVEM·실행된 표 칸만 전사), C10 계약(범위 밖에서 들어오는 실제 분기 대상은 시작)을 따르며 다른 점만 적는다. 단위 이름은 FR14, 파일 접두어는 `objects_fr14`(C++) / `fr14`(V1 spec)다. 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다. BIOS 실행, 자연 scheduler, IRQ timing은 주장하지 않는다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 LONG(`200034` `2001a8` `2001c4` `20008c`)을 live bus로 읽는다(아래). 장치 쓰기는 없다(callee `49f8c`·`8ebe` 등이 장치에 쓴다; 그 실행부 몫). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 E2 커밋 `2309426`(branch `claude/fr14-core`; C1~C10, E1, E2, D, FR10~FR13 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `b376d62144aeacdbbfbb0a36b265669b896f9e2f63eaa1b363f77e664366eeed`, `animation_machine_internal.h` `4592d7ce786f860f34fbf253c234018e45329eccdd3ce5e83d2ee7f39dfd1b99`(E2 계약의 새 값과 같음).
- [F] 관측 입력(읽기 전용): 입력 확장 IO 관측 `artifacts/animation_machine_io_ext`(`observation.json` SHA256 `9da40ac6dcbea3eb…`, compared_sha256 `b5d15d4fcd53555b…`, 검증기 pin 이름 `io-ext`). V1 natural / reinstall family가 이 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT`)으로 읽는다(FR13 결정 5, E2 결정 6과 같은 방식).
- [F] 이 단위의 정확 bitmap 재관측 세 벌(scratch, 관측기 `tools/observe_animation_machine_io_ext.py` 수정 없음): `reobs/fr14base`(E2 routing 그대로), `reobs/fr14v1`(계획 FR14 16 범위를 `--extra-routed`로 가상 routing), `reobs/fr14final`(FR14를 실제로 routing한 작업 트리). 결정 1·"확장 관측 완료 판정".
- [F] 시작 목록: **`ms5-scratch/fr14/work/starts_fr14_final.txt`(200개, 줄마다 하나, SHA256 `d40487bede41770cc7535319f7f4652829b9899abd6b378320b1e90c2e5a3522`)**. 계획 목록 `ms5-scratch/fr14/starts_FR14.txt`(199개, 공백 구분, SHA256 `b885b234ad36b1579839deeffd4a9835a0067f374b21d2d25970f156a16676dc` = 계획 §10.5의 `b885b234ad36b157`)에 `3657c` 하나를 더한 것이다(결정 1). 실행부의 `case` label 200개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(V1 spec `build()`가 시작 200개와 범위 안 짝수 PC 1,000개가 모두 `animation_objects_fr14_block`로 routing됨을 확인, `make test`의 FR14 시험이 시작 200개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr14/`
  - `reobs/run.sh`(재관측 + `dleft.py` + `runstops.py`), `reobs/fr14base` `fr14v1` `fr14final`(+ `.dleft` `.stops` `.log`), `work/remeasure_ext.dleft` `.stops`(공유 관측 그대로 재측정, E2 routing), `work/remeasure_ext_after.dleft`(같은 공유 관측, FR14 routing), `work/udetail_FR14_plan.txt` `plan/D-5.dis.txt`(계획 `xplan_v2.json`의 D-5 상세·역어셈블; `tools/xdetail.py`, `MS5_OBS2=e2/reobs/e2v1`), `work/fr14ranges_plan.txt` = `work/fr14ranges_final.txt`(16 범위).
  - `tools/newvis_fr12.py`(`FR12_RANGES=work/fr14ranges_plan.txt`; 새로 보인 PC) → `work/newvis_fr14v1.txt`, `work/intargets.py` → `work/intargets_fr14_v1.out`(범위 안 비시작 PC로 오는 직접 분기), `tools/refs_fr13.py`(`STARTS=work/starts_fr14_plan.txt`) → `work/refs_fr14_v1.out`(ROM 전체 FR14 시작 참조), `tools/flagscan.py` → `work/flagscan_fr14_final.txt`, `tools/exitflags.py` → `work/exitflags_fr14.txt`(대상 `work/exitflags_targets_fr14.txt`), `tools/fr14exec.py` → `work/fr14exec_base.txt`(재관측의 FR14 실행 PC·run·frame), `tools/natscan_fr14.py` → `work/natscan_fr14_cand.out` `work/natural_fr14_cand.json`, `tools/fr14refs_repo.py` → `work/fr14refs_repo_v1.out`(저장소의 FR14 범위 literal), `work/v1_regs.sh`, `work/ubsan.sh`, `work/pincheck.py`, `work/mkroot.py`, `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위(결정 1)

- [F] **재측정(E2 routing, 공유 확장 관측 그대로)** `work/remeasure_ext.dleft`: 실행된 routing 밖 PC D 91(C 0 / E 0), 예측 일치 frame **12,586**, 첫 정지 D 3 run(X2 94 frame 874 `d177e`.., X3 68 1,120 `3643e`.., X3 94 958 `7177a` / `71786`). E2 계약의 IO 실측(12,586, frontier `d177e` `3643e` `7177a`)과 같다.
- [F] **정확 bitmap 재관측(E2 routing)** `reobs/fr14base`(routing `b376d621`): D 91, 예측 12,586, 첫 정지는 위와 run·frame이 같다(E2 계약의 가상 routing 재관측 `e2v1`과 `.stops`가 줄 단위로 같음).
- [F] **정확 bitmap 재관측(FR14 가상 routing, 계획 16 범위)** `reobs/fr14v1`: 예측 일치 frame **14,500**(계획 14,500과 같음, native 비교 frame 전부), 실행된 routing 밖 PC **C 0 / D 0 / E 0**, 첫 정지 없음. 12 run 모두 끝(P0 / P1 frame-limit, X run system-return guard)까지 routing 밖 PC가 없다.
  - [F] **숨은 직선 연속 검사**: `fr14base`에 없고 `fr14v1`에만 보이는 routing 밖 PC는 **없다**(`newvis_fr12.py`에 FR14 범위: 12 run 모두 0, `work/newvis_fr14v1.txt`). 반복은 한 번으로 수렴했다.
- [F] **범위 밖에서 범위 안 비시작 PC로 들어오는 직접 분기**(`work/intargets_fr14_v1.out`): 실제 코드는 **`36630 BRA.W 3657c` 하나**다. `365fc..36634`는 C5 `1cc88`(`MOVEA.L #365fc,A0; MOVE.W #1e,D0; MOVEA.L #100bf4,A1; JSR 2986`, `animation_machine_player_c5.cpp` 227행)이 만드는 `2986` 자식의 callback이다(bank anim `ca` / `200088`, anim `3819c`, 소리 `864`, LONG 36 / 3a := 0, `BRA.W 3657c`). `365fc`는 확장 관측에서 실행되지 않고(어느 계획 단위의 시작도 아님) routing 밖으로 남는다. 나머지 줄은 자료를 명령으로 읽은 것이다: `364a8` `36586` `b604a`는 FR14 `MOVE.L #v,(A6)`의 operand, `b5bfa`는 8 byte 기록 표 `b5b80..b5c30`(`0003 6000 044c 0000` …)의 바이트다(`b6048`은 명령 중간).
  - **범위 보정(결정 1)**: `36578`(`ADD.W D0,36(A6)`) block을 둘로 나눠 **`3657c`를 시작으로 더했다**(E2 `e695e`·C10 계약의 "범위 밖 실제 분기 대상은 시작" 규칙). 범위·명령·byte는 바뀌지 않는다(199 → 200 block). `36578`은 `3657c`로 떨어진다. 이렇게 해 두면 뒤 단위가 `365fc`를 routing할 때 그 `BRA.W`가 FR14 block 시작에 닿는다. 범위가 같으므로 정확 bitmap은 `fr14v1`과 같다(재관측 다시 하지 않음; `fr14final`이 실제 routing으로 확인).
- [F] **ROM 전체 참조**(`work/refs_fr14_v1.out`, 분기 operand 검색; LONG 검색은 scratch 즉석 스크립트): 범위 밖에서 FR14 시작을 가리키는 것은 다음뿐이다.
  - LONG 표: `1cc08`(C5 표 `1cc04` 칸 1 = `3643e`; 칸 2는 routing 밖 `363c6`), `e8efc`(stage event op 08 callback 표 `e8cc0`의 칸 `8f` = `b5c34`), `b36a6`(FR1 종류 기록 표 `b3484..b3894`(10 byte × 104)의 기록 `61`의 LONG 6 = `c0d68`).
  - 분기: `3643a BRA.W 3648c`(routing 밖 `3640e` callback의 꼬리; `3648c`는 시작), `b5da6` `b5de0` `b5e10` `b5e2c` `b5e98` `b5eac` `b5ed0` `b5f74` `b5f88` `b5ffc` `b6032` `b6034`(routing 밖 형제 callback `b5d5a..b6036`이 FR14 helper `b6056` `b6084` `b60c4` `b60da`와 꼬리 `b6038` / `b6082`로 감; 모두 시작), `b7ad4` `b7ae0 BRA.W b7af8`(routing 밖 형제 계수 진입; 시작), `c0e3a BPL.B c0dd2`(routing 밖 `c0e2a..`의 갈래; 시작), `cc83a`(FR4 표 `cc82e` 칸 3) `cc8ea`(FR13 표 `cc8de` 칸 3) `BRA.W cd0fe`(둘 다 routing 밖 칸, 실행 안 됨; `cd0fe`는 시작), `365d0 BRA.W 365da`(시작).
  - 그 밖의 LONG 검색 적중(`36500` × 7, `b6100` `cd16e` `cd1a8`)은 명령 operand가 우연히 같은 값이다(`1ca60 CMP.B 3(A4),D2` 등; scratch에서 역어셈블로 확인).
- [F] **계획 특이 항목 대조**(`plan/D-5.dis.txt`, ROM 바이트): MOVEM 2(`b7af8 MOVEM.L D0/A2-A3,-(A7)`, `b7b02 MOVEM.L (A7)+,D0/A2-A3`), 설치 값 `364aa` `36588` `b5cec` `c0dc8` `d17e0`(범위 안, 곧바로 들어감), 쓰기만 `b5d5a` `b5e46` `b5f00` `b604e`(routing 밖, 실행 안 됨)와 `cdd2e`(routing됨) — 계획과 같다. 계산 점프·`JSR (An)`·`JMP (An)`·TRAP·DIVU/MULU/MULS·ADDX/SUBX·`28ae`/`2986` 자식은 없다.
- [F] **실행되는 표 칸**: FR14가 routing하는 앞 단위 계산 착지는 FR4 `cc7a0`(`JMP cc7ac(PC,D0.W)`)의 칸 3 `cc7b8` 하나다. 같은 대상 `cd0fe`로 가는 FR4 표 `cc82e` 칸 3 `cc83a`와 FR13 표 `cc8de` 칸 3 `cc8ea`는 재관측(`fr14v1`, `fr14final`)에서 실행되지 않아 routing 밖 정지로 둔다(FR13 결정과 같은 규칙: 실행된 칸만 전사).
- [F] **IO 실행**(`reobs/fr14base`, `work/fr14exec_base.txt`): FR14 시작 가운데 기록된 것 91개, 실행 11,664회(계획 표의 91 / 11,664와 같음), run 3개. 처음 frame(처음 ~ 마지막): X2 94 874..883, X3 68 1,120..1,520, X3 94 958..1,300. 기록되지 않은 시작 109개(계획 108 + `3657c`): 같은 TB 안의 직선 연속(`3657c` 등)이거나 이 관측에서 실행되지 않는 분기 쪽이다(`36532` 계열 전부(1aa3a 결과 bit 3 = 1 쪽), `3649e` `364ba` `364ce` `364f0` `364fa` `36500`, `b5c68` `b5c84`(WORD 76 ≠ 0 쪽과 직선 연속), `b5d34` `b5d42` `b5d50` `b6046`(설치 쓰기), `b606a` `b6070` `b607a`, `b60a2` `b60b0` `b60c2` `b60d2`, `b60f0`..`b6146`(선수 2 / 4941e 쪽과 계수), `b7ae4`..`b7b2e` 전부, `c0d7a` `c0d88`, `cd0fe`의 WORD 8c ≠ 1 / BYTE 7a 쪽 대부분). [I] 계수 `b7ae4` / `b7af0`은 `b60da`가 C Set으로 끝나는 경로(선수 node가 상자 안)에서만 실행된다. 관측의 X run에서는 그 경로가 일어나지 않았다.

## FR14 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **200 block, 445 명령, 2,000 byte, 16 범위**(시작 목록 SHA256 `d40487be…`(줄 형식, 최종) / `b885b234…`(계획 형식, 199), 범위 byte를 이어 붙인 SHA256 `ae74fab10dfe4dab191c37595fb6989c570a58b0dd62399ac110a57bd419f1a2`). 짝수 PC 1,000(내부 800). 기존 routing과 겹침 0(V1 spec `build()`가 범위 안 짝수 PC 1,000개와 범위 양옆을 확인, 시험 `interior()`).

| 범위(CPU = 파일 오프셋) | byte | 시작 | SHA256(앞 16자) | 내용 [I] |
| --- | --- | --- | --- | --- |
| `3643e..36522` | 228 | 21 | `db843c09cb5ba722` | C5 `2986` 자식 `3643e`: WORD 20 := 22, LONG 22 := LONG `200034`, `JSR 1aa3a`; D0 bit 3 → `36532` / `3645a`: A1 := 표 `363ae`[WORD 76](anim), `49f8c`; 소리 표 `363be`[WORD 76], `8ebe`; WORD 3a += 4, BYTE 15 bit 0이면 WORD 36 −= 4 / += 4; 설치 `364aa`(곧바로): LONG 36 / 3a를 0 / `fff00000` 쪽으로(`SUB.L`, 양수면 `+f`, `ASR.L #4`), LONG 3a를 넣고 `4be34`, BYTE 15 bit 7이면 `BSET #3,61`(이미 1이면 `JMP 2a00`, 아니면 `NEG.L D0`), LONG 3a := D0, `49fc6`, 기록 `363a6`의 `1ab80` C → RTS / `JMP 2a00` |
| `36532..365d0` | 158 | 13 | `61bd48a41ccfb0d7` | `36452 BNE`의 대상: anim 표 `36522`, 소리 표 `363be`, WORD 3a / 36 ±4, `3657c`: BYTE 7f := 1e, 설치 `36588`(곧바로): LONG 36 / 3a를 0 / `fffc0000` 쪽으로, `SUBQ.B #1,7f; BCC` → `365da` / `BSET #3,61`(1이면 `JMP 2a00`) |
| `365d4..365fc` | 40 | 7 | `a11bb86cd55c081e` | BYTE 7f := 1e → `365da`: `4be34`, `49fc6`, 기록 `363a6`의 `1ab80` C → RTS / `JMP 2a00` |
| `7177a..7177c` | 2 | 1 | `335d5d3529f1169f` | FR12 `7176a`(BYTE 15 bit 0 = 0)의 fall-through: `NEG.L D0` → FR12 `7177c` |
| `71786..71788` | 2 | 1 | `335d5d3529f1169f` | FR12 `7177c`(D0 음수)의 fall-through: `NEG.L D0` → FR12 `71788` |
| `71874..71876` | 2 | 1 | `335d5d3529f1169f` | FR13 `71860`(BYTE 15 bit 0 = 0)의 fall-through: `NEG.L D0` → FR13 `71876` |
| `b5c34..b5c4c` | 24 | 2 | `8f5eea06bc39f768` | stage event op 08 자식(표 `e8cc0` 칸 8f): BYTE 8b := 0, 소리 `9b`, `BRA.W b5c60` |
| `b5c60..b5d5a` | 250 | 20 | `d70fa51c10eff75d` | WORD 76 → BYTE 15 bit 0 / LONG 64 := ±8000, LONG 80 := WORD 7c << 16, `4c0ac`, WORD 68 / 1e := 8820, `490ba`(A0 = `c8544`), WORD 86 := D0.W, bank anim 1b3 / `2001a8` / 94, 설치 `b5cec`(곧바로): `b6056`, `49fc6`, WORD 2a(A6) = 0이면 BYTE 8a := (8a + 1) & f, LONG 64 := 표 `b6280`[8a], `b6084`; `4b54e` C → `b5d5a` 쓰기, `b60da` C → `b5e46` 쓰기, LONG 80 = 0 → `b5f00` 쓰기, `BRA.W b6038` |
| `b6038..b604e` | 22 | 4 | `b5d06cbca3349d02` | 기록 `b6270`의 `1aa7e` C → `b604e` 쓰기, RTS |
| `b6056..b614c` | 246 | 36 | `6595e4ebe28fd30c` | `b6056`: BYTE 15 bit 7 → `4bfa4` / `4be2c` 뒤 bit 7이면 LONG 36 / 3a := 0; `b6084`: bit 7이면 `b60c4`(LONG 64 := ±LONG 64, BYTE 15 bit 0), `4bfa4`, LONG 80 −= \|LONG 64\|(음수면 0), LONG 64 / 36 / 3a := 0; `b60da`: BYTE 61 bit 0 → Set, 아니면 선수 0 / 1마다 `49392` C, 기록 `b6278`의 `4941e` C → Clear(`b6128`) / 선수 D0 := 0 / 1 → BYTE 8b로 계수 `b7af0` / `b7ae4` → Set(`b6146`) |
| `b7ae4..b7b30` | 76 | 11 | `7116f481e1dbfcd4` | 계수: A2 / A3 := A5 + `5ddf` / `5de7`(또는 `5dde` / `5de6`), `MOVEM.L D0/A2-A3`, `49392` C → 아니면 RTS; D0.B = 0이면 WORD `5ddc(A5)`, 아니면 WORD `5de4(A5)`와 A2 := A3; WORD += 1(무부호 64 이상이면 63), BYTE (A2) += 1 |
| `c0d68..c0e2a` | 194 | 17 | `962eb8631e533dfd` | FR1 종류 기록 `61` 처리기: LONG 64 := a000, WORD 42 ≥ a0(부호)이면 `BSET #0,15`, 아니면 `NEG.L 64`; `c6a96`(70 / 11 / 0), bank anim 1eb / `2001c4` / 44, 설치 `c0dc8`(곧바로): BYTE 15 bit 7 → `4bfa4` / `4be2c`, `b4958`, `b4ab0`, D0 bit 2 → `c1d2e` / `b4334` C → RTS / bank anim 다시 |
| `cc7b8..cc7bc` | 4 | 1 | `1e30ee71abc85561` | FR4 표 `cc7ac` 칸 3: `BRA.W cd0fe` |
| `cd0fe..cd370` | 626 | 53 | `b8a3f5c1f70cfd74` | D1.B := (BYTE 15 bit 0 ? ff : 0) ^ BYTE 5f(`SNE` / `EOR.B`), BMI → BYTE 7a 0 / 아님 → 세 anim 목록 가운데 하나에서 WORD 8c 0..4 / 그 밖(`ofr14_anim`: WORD 20 := WORD 8a, `49f8c`), LONG 3a := 20000, `cdd2e` 쓰기만, RTS |
| `d1632..d1636` | 4 | 1 | `8e2e5c0b1f8c07a4` | FR13 `d161a`(BYTE 15 bit 0 = 0)의 fall-through: `NEG.W D0; NEG.L D1` → FR13 `d1636` |
| `d177e..d17f8` | 122 | 11 | `105e7ac38a0b1bef` | FR13 `d177a BCC`의 Set 쪽 fall-through: A0 := `d1cba`, `4ae4a`(`MOVE.L A0,D0; BEQ`: 상수라 늘 실행), `8ff4`, WORD 68 / 1e := 1001, bank anim d2 / `20008c` / 10, 소리 `36b`, 설치 `d17e0`(곧바로): `43e34`, `49fc6` C → RTS / `JMP 2a00` |

- [F] **root·진입**(계획 xdetail의 "실행 PC를 줄인 closure 진입"): `d177e` `3643e` `7177a` `71786` `71874` `d1632` `cc7b8` `b5c34` `c0d68`. 설치 값(`MOVE.L #v,(A6)`): 곧바로 들어감 `364aa`(`364a4`) `36588`(`36582`) `b5cec`(`b5ce6`) `c0dc8`(`c0dc2`) `d17e0`(`d17da`); 쓰기만 `b5d5a`(`b5d34`) `b5e46`(`b5d42`) `b5f00`(`b5d50`) `b604e`(`b6046`)(모두 routing 밖, 이 관측에서 실행 안 됨)·`cdd2e`(`cd368`, routing됨: FR4). `MOVE.L #v,84(A6)`는 없다.
- [F] **진입**(현재 routing 기준 호출자):
  - 계산 착지(기존 실행부의 규칙 그대로, FR14는 그 칸·값을 routing할 뿐이다): C5 `1cc38`(`MOVEA.L 1cc04(PC,D1.W),A0; ...; JSR 2986`)의 칸 1 `3643e`(2986 자식: 다음 dispatch에서 A6 = 자식 node), stage event ops `e9558`(op 08: `MOVEA.L (A1,D0.W),A0`, 표 `e8cc0`; U7 `2986`)의 칸 `b5c34`, FR1 `b3f3a` / `b3fb2`(`MOVEA.L 6(A1/A0),A0; JMP (A0)`, 종류 기록 `b3484 + 10k`)의 기록 61 처리기 `c0d68`, FR4 `cc7a0`(`JMP cc7ac(PC,D0.W)`, FR4 결정 2: routing이 판정)의 칸 3 `cc7b8`.
  - 다른 실행부의 fall-through: `7177a` ← FR12 `7176a`, `71786` ← FR12 `7177c`, `71874` ← FR13 `71860`, `d1632` ← FR13 `d161a`, `d177e` ← FR13 `d177a`(C Set).
  - routing 밖에서 오는 분기(위 "ROM 전체 참조"): `3657c` ← `36630`(`365fc` 자식), `3648c` ← `3643a`, helper·꼬리 ← `b5d5a..b6036`, `b7af8` ← `b7ad4` `b7ae0`, `c0dd2` ← `c0e3a`, `cd0fe` ← `cc83a` `cc8ea`, `365da` ← `365d0`.
  - 범위 안 subroutine: `b6056`(`b5cec`) `b6084`(`b5d26`) `b60c4`(`b608e`) `b60da`(`b5d3a`) `b7af0`(`b6136`) `b7ae4`(`b6140`).
- [F] **`28ae` / `2986` 자식**: FR14는 자식을 만들지 않는다. FR14 자체가 C5 `1cc38`의 `2986` 자식(`3643e`)과 stage event op 08의 `2986` 자식(`b5c34`)을 가지며, routing 밖 C5 `2986` 자식 `365fc`의 분기 대상(`3657c`)을 가진다.

### 계산 점프와 표(결정 2)

- [F] **계산 점프·`JSR (An)`·`JMP (An)`은 없다.** 모든 분기 대상은 정적이다(`d177e`의 `BEQ.W d1792`는 상수 `d1cba` 시험이라 원본에서도 늘 `d178a`로 감; V1 `STATIC_IMPOSSIBLE`).
- [F] **FR14가 받는 계산 착지**(위 "진입"): C5 표 `1cc04` 칸 1, stage event 표 `e8cc0` 칸, FR1 종류 기록 처리기, FR4 표 `cc7ac` 칸 3. 각 실행부의 기존 규칙(routing이 판정)을 그대로 둔다. 표 `cc82e` 칸 3 `cc83a`와 `cc8de` 칸 3 `cc8ea`(같은 대상 `cd0fe`)는 실행되지 않아 routing 밖 정지다.
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5·E2 결정 2와 같은 규칙):
  - `363ae` anim LONG 표(4칸: `37f8a 37f8a 38008 38008`): `3645a MOVEA.L (A1,D0.W),A1`, D0.W = 4 × WORD 76(WORD 연산, **부호 확장** 색인). `36522`(4칸: `38104 38104 38150 38150`): `36532` 같은 꼴.
  - `363be` 소리 WORD 표(`0376 0377 0004 0005`): `36474` / `3654c MOVE.W (A0,D0.W),D0`, D0.W = 2 × WORD 76.
  - `b6280` LONG 표(16칸, BYTE 8a & f로 묶임): `b5d1a MOVE.L (A0,D0.W),D1`, D0.W = 4 × ((BYTE 8a + 1) & f).
  - bank 창 LONG `200034`(`3643e`: LONG 22에 넣기만), `2001a8`(+94), `2001c4`(+44), `20008c`(+10): FR13 `ofr13_bank_anim`과 같은 꼴(`ofr14_bank_anim`).
  - 넘기기만 하는 상수: 기록 `363a6`(`1ab80`) `b6270`(`1aa7e`) `b6278`(`4941e`) `c8544`(`490ba`) `d1cba`(`4ae4a`), anim 포인터 `ce48c` `cecde` `ced72` `cfde4` `cf636` `d05be` `d0d26` `cdf86` `ce7c4` `cf870` `cf126` `d00e0` `d07f8`(`cd0fe` 계열, `49f8c`로 넘김).
  - 이 표·창 값은 모두 anim 자료 포인터(A1)·소리 번호·속도 LONG이다. 코드 주소로 점프하지 않는다. [F] WORD 76은 원본 writer가 선수 번호로 쓰는 값으로 보이나 [I] FR14는 범위를 검사하지 않는다(원본도 검사 없음). 표 밖 색인은 원본도 표 앞뒤 byte를 읽는다.

### 정수 연산(결정 3)

- [F] **ASR.L #4**(`364c0` `364d4` `3659e` `365b2`): 부호 채움(`ofr14_asr4`; C++ 부호 shift를 쓰지 않음). 앞의 `SUB.L`은 mod 2^32이고 `BMI`는 그 LONG의 bit 31이다. 양수(bit 31 = 0)면 `ADDI.L #f`(mod 2^32: 7ffffff1 + f = 80000000이면 ASR 뒤 음수)를 먼저 한다 [I: 0 쪽으로 반올림한 1/16].
- [F] **부호 있는 WORD 비교**(`c0d68 CMPI.W #a0,42(A6); BGE`): `ofr14_signed_word`(bit 15를 빼서 int32로, 넘침 없음). **무부호 WORD**(`b7b1e CMPI.W #64,(A1); BCS`: ADDQ 뒤 새 WORD). **BYTE 부호**(`cd0fe EOR.B; BMI`: D1.B bit 7). **WORD 같음**(`cd132`..`cd328 CMPI.W #1..#4,D0`, `cd110 MOVE.W 8c; BNE`). **BYTE 0 시험**(`b612e TST.B 8b`, `cd1d4 TST.B 7a`, `b7b0a TST.B D0`). **LONG 0 / 부호**(`b5d48 TST.L 80`, `b6098 TST.L D0; BPL`, `b60a4 TST.L 80; BPL`, `d177e MOVE.L A0,D0; BEQ`).
- [F] **빌림**: `365b2 SUBQ.B #1,7f; BCC`(앞 BYTE ≠ 0이면 빌림 없음).
- [F] **WORD / BYTE 대상은 하위만 바꾼다**: `ADD.W D0,3a / 36(A6)`(메모리 WORD), `MOVE.W #4,D0`, `NEG.W D0`(`3649e` `36576` `d1632`), `ADD.W D0,D0`(표 색인), `MOVE.W (A0,D0.W),D0`, `MOVE.B #0,D1`, `MOVE.W #100 / #9b / #36b / #70 / #11,D0 / D1`, `MOVE.B #0,D2`, `CLR.W D0`, `MOVE.W #1,D0`, `MOVE.B 5f,D0`, `SNE.B D1`, `EOR.B D0,D1`, `MOVE.W 8c,D0`, `ADDQ.W #1,(A1)`, `ADDQ.B #1,(A2)`, `MOVE.W D0,86(A6)`. `MOVEQ`·`MOVE.L`·`CLR.L`·`NEG.L`·`SUB.L`·`ADD.L`·`ADDI.L`·`ASR.L`·`SWAP`(`b5c84`: `CLR.L D0; MOVE.W 7c,D0; SWAP` = WORD 7c << 16)·`MOVEA`·`LEA`·`MOVEM.L`은 LONG 전체.
- [F] **`BTST #n,D0`**(`36452` 3, `c0dee` 2): 데이터 레지스터 BTST는 LONG 모드지만 번호 < 8이라 하위 BYTE의 bit다. 메모리 BTST / BSET / BCLR은 BYTE, bit mod 8.
- [F] **`BSET #3,61(A6); BEQ`**(`364f0` `365c0`): Z는 바꾸기 전 bit가 0인지다(0이면 `36500` / `365d4`, 1이면 `JMP 2a00`).
- [F] **`MOVEM.L D0/A2-A3,-(A7)`**(`b7af8`): 높은 주소부터 A3, A2, D0 순으로 넣는다(가장 낮은 LONG = D0, 68000 순서). **`MOVEM.L (A7)+,D0/A2-A3`**(`b7b02`): 낮은 LONG부터 D0, A2, A3, A7 += 12. MOVEM은 flag를 바꾸지 않으므로 뒤의 `BCC`는 `49392`의 C를 읽는다(결정 4). 모두 `am_push`/`am_pop`(work RAM stack; 홀수 A7은 `program bus requires even WORD/LONG address`).
- [F] **`MOVE.L 3a(A6),-(A7)`**(`364da`) / **`MOVE.L (A7)+,D0`**(`364e4`): `4be34` 호출 앞뒤의 저장. 직접 진입한 `364e4`는 그 자리(원래 return LONG 위치)의 LONG을 D0로 꺼낸다(원본 그대로).
- [F] **`LEA d16(A5),An`**(`b7ae4` `b7af0` `b7b10` `b7b18`): 16 bit 변위는 부호 확장(`am_index`; 이 단위의 변위는 모두 양수).

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `2a00` `8ebe` `8ff4` `1aa3a` `1aa7e` `1ab80` `43e34` `490ba` `49392` `4941e` `49f8c` `49fc6` `4ae4a` `4b54e` `4be2c` `4be34` `4bfa4` `4c0ac` `b4334` `b4958` `b4ab0` `c1d2e` `c6a96`, 앞 단위 FR12 `7177c` `71788`, FR13 `71876` `d1636`, RTS 복귀(`36520` `365fa` `b604c` `b6082` `b60c2` `b60d4` `b6128` `b6146` `b7b2e` `c0e28` `cd360` `d17f6`).
- [F] **뒤 단위 정지 없음.** FR14 block이 직선·분기로 닿는 routing 밖 PC는 없다(분기 대상·fall-through는 모두 FR14 시작이거나 위 출구). 그래서 V1·실제 ROM 차분의 FR14 자신의 뒤 단위 정지(`UNIT_EXITS`)는 비어 있다. 앞 단위들의 남은 정지(C1~C9의 12개: `1fd3c` `21ea0` `1d3e0` `4eb6a` `4ef08` `1de3c` `1e21c` `1e8de` `1fc96` `1fd50` `21fa6` `4e69a`)는 V1 `EXIT_STOPS`에 그대로 둔다(FR14 run은 닿지 않음).
- [F] **FR12 / FR13의 뒤 단위 정지가 FR14 block이 됨**: FR12 `7177a` `71786`, FR13 `71874` `d1632` `d177e`. 앞 단위 시험·spec의 바뀐 기대값은 "영향받는" 절.
- [F] 직선 fall-through로 범위를 벗어나는 곳: `7177a` → FR12 `7177c`, `71786` → FR12 `71788`, `71874` → FR13 `71876`, `d1632` → FR13 `d1636`. 재관측에서 새로 보인 PC가 없어 가려진 연속은 없다(결정 1).

### block 경계·복귀를 넘는 flag(결정 4)

block 첫 명령부터 flag를 정하는 명령까지 훑었다(`work/flagscan_fr14_final.txt`). 그리고 FR14 출구 대상·object loop 복귀 PC(`work/exitflags_targets_fr14.txt`: 위 routing된 출구 23개, FR12 / FR13 fall-through 대상 4개, `2ac2`)에서 FR14가 남긴 flag를 읽는 곳을 따로 훑었다(`work/exitflags_fr14.txt`: 없음). X를 읽는 명령은 없다.

- [F] **C 소비 block 12개**(Clear 쪽 / Set 쪽; Unknown C면 `objects fr14 caller requires known carry`):
  - `36516 BCC 36520` `365f0 BCC 365fa`: routing된 `1ab80`(N05: `1aafc` Set / `1abd4` Clear)의 C.
  - `b5d30 BCC b5d3a`: `4b54e`(U01: `4b6be`에서 BYTE 5e = 0이면 Clear, 아니면 Set; LONG 56 ≠ 0 쪽은 `4b50c` C)의 C.
  - `b5d3e BCC b5d48`: FR14 `b60da`의 C(`b6128 ANDI.B #fe,CCR; RTS` Clear, `b6146 ORI.B #1,CCR; RTS` Set).
  - `b6042 BCC b604c`: `1aa7e`(U01, `1aafc` Set / Clear)의 C.
  - `b60ec BCC b6104` `b610e BCC b6128`: `49392`(frame helpers: `4939e` Clear, BYTE `568e(A5)` bit D0이면 `493b6` Set)의 C.
  - `b60fa BCS b6104` `b611c BCS b6128`: `4941e`(FR1c 상자 시험)의 C(Set 쪽이 분기).
  - `b7b02`(`MOVEM.L (A7)+,D0/A2-A3; BCC b7b2e`): `49392`의 C. MOVEM이 flag를 바꾸지 않으므로 block 안에서 C가 그대로다.
  - `c0dfc BCC c0e28`: `b4334`(FR2: `JSR 49fc6; RTS` — `b433a`가 C를 넘김)의 C.
  - `d17ec BCC d17f6`: `49fc6`의 C.
- [F] **C 생산 block 2개**: `b6128`(Clear) `b6146`(Set). 각자 C를 정하고 RTS로 `b5d3e`에 돌려준다. `b6146`은 `b60e0 BNE`(BYTE 61 bit 0)로도 바로 온다.
- [F] **dispatcher carry 보존 목록**: 소비자 12개만 더했다. 생산자 다음의 RTS 복귀 PC가 곧 소비자이므로 C가 그대로 전달된다. 그 밖의 FR14 block은 Unknown이다(dispatcher 기본).
- [F] **Z / N이 경계를 넘는 곳은 없다.** 복귀 뒤 첫 명령이 flag를 다시 정한다: `36452 BTST`(`1aa3a`의 D0), `c0dee BTST`(`b4ab0`의 D0), `364e4 MOVE.L`, `b7b0a TST.B`(`b7b02` 뒤; 같은 block의 `BCC`는 C만 읽음), `b5cf6 TST.W`, `b6098 MOVE.L` / `TST.L` 등. RTS로 돌려주는 flag(`36520` `365fa` `b604c` `b6082` `b60c2` `b60d4` `b7b2e` `c0e28` `cd360` `d17f6`)를 읽는 쪽은 없다(`b6128` / `b6146`의 C는 `b5d3e`가 읽음).

### IO 실행 run과 frame

- [F] 실행 run 3개(X2 94, X3 68, X3 94), 처음 frame은 위 "재확인과 범위". FR14 node는 pool `100800..104c00`의 여러 node다(`work/natscan_fr14_cand.out`): frame 시작 상태의 callback `3643e`(X3 68 1,120 `102590`) `364aa`(1,121..1,123) `d17e0`(X2 94 875..883 `102654`, X3 68 1,481..1,489 `10126c`) `b5cec` / `c0dc8`(X3 68 1,498..1,662 `102280` / `1020f8`, X3 94 1,278..1,462 `101330` / `101a14`). `b5c34`·`c0d68`·`cc7b8`·`d177e`·`7177a` 등은 다른 callback이 같은 frame에 들어가는 곳이라 frame 시작 상태에 남지 않는다(V1 reinstall family, 결정 6).
- [F] **IO 예측(FR14 연결)**: 12,586 → **14,500**(+1,914; 재관측 `reobs/fr14v1`, 계획과 같음). 첫 정지는 없다. [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다.
- [F] 원래 IO 관측은 FR14 코드를 실행하지 않는다(계획 §10.4: X run에서만 실행). 일치 173,966은 그대로여야 한다(작업자는 돌리지 않음; 메인 runner).

## block 의미(요약)

- **`3643e`**: WORD 20 := `22`, LONG 22 := LONG `200034`, `JSR 1aa3a`. **`36452`**: D0 bit 3 → `36532`(두째 anim 표) / `3645a`(A1 := `363ae`[4 × WORD 76], D0.W := 100, `JSR 49f8c`). **`36474`** / **`3654c`**: D0.W := `363be`[2 × WORD 76], D1.B := 0, `JSR 8ebe`. **`3648c`** / **`36564`**: D0.W := 4, WORD 3a += 4; BYTE 15 bit 0 = 1이면 D0.W := −4(`NEG.W`); WORD 36 += D0.W. **`364a0`**: 설치 `364aa`. **`3657c`**: BYTE 7f := 1e, 설치 `36588`.
- **`364aa`** / **`36588`**(callback): D2 := 0 − LONG 36(양수면 +f), ASR 4, LONG 36 += D2; D3 := `fff00000` / `fffc0000` − LONG 3a(양수면 +f), ASR 4, LONG 3a += D3. `364aa` 쪽: LONG 3a를 넣고 `JSR 4be34`, 꺼낸 값을 D0; BYTE 15 bit 7 = 1이면 `BSET #3,61`(이미 1이면 `JMP 2a00`, 아니면 `NEG.L D0`); LONG 3a := D0, `JSR 49fc6`, `363a6`의 `JSR 1ab80` → C Clear RTS / Set `JMP 2a00`. `36588` 쪽: BYTE 7f −= 1; 빌림(앞 0)이면 `BSET #3,61`(이미 1이면 `JMP 2a00`, 아니면 7f := 1e); `4be34`, `49fc6`, `1ab80` 같은 끝.
- **`b5c34`**(stage event 자식): BYTE 8b := 0, 소리 `9b`; **`b5c60`**: WORD 76 ≠ 0이면 BYTE 15 bit 0 := 1, LONG 64 := `ffff8000`, 아니면 bit 0 := 0, LONG 64 := `8000`; LONG 80 := WORD 7c << 16, `JSR 4c0ac`; **`b5c9a`**: WORD 68 / 1e := `8820`, `JSR 490ba`(A0 = `c8544`); **`b5cb2`**: WORD 86 := D0.W, LONG 64 := 0, BYTE 8a := 0, bank anim 1b3; 설치 `b5cec`.
- **`b5cec`**(callback): `JSR b6056`, `JSR 49fc6`; WORD 2a(A6) = 0이면 BYTE 8a := (8a + 1) & f, LONG 64 := `b6280`[8a], `JSR b6084`; `JSR 4b54e` → Set이면 `b5d5a` 쓰기; `JSR b60da` → Set이면 `b5e46` 쓰기; LONG 80 = 0이면 `b5f00` 쓰기; `BRA b6038`(`1aa7e` 상자 시험 → Set이면 `b604e` 쓰기; RTS).
- **`b6056`**: BYTE 15 bit 7 = 1 → `JSR 4bfa4`, 아니면 `JSR 4be2c` 뒤 bit 7 = 1이면 LONG 36 / 3a := 0; RTS. **`b6084`**: bit 7 = 0 → RTS; 1 → `JSR b60c4`, `JSR 4bfa4`, D0 := \|LONG 64\|, LONG 80 −= D0(음수면 0), D0 := 0, LONG 64 / 36 / 3a := 0; RTS. **`b60c4`**: D0 := LONG 64, BYTE 15 bit 0 = 1이면 `NEG.L`; LONG 64 := D0; RTS.
- **`b60da`**(C 결과): BYTE 61 bit 0 = 1 → Set; 아니면 선수 0(`CLR.W D0`): `49392` Clear → 선수 1로; Set → `4941e`(A1 = `b6278`) Clear → D0 := 0으로 계수, Set → 선수 1로; 선수 1(`MOVE.W #1,D0`): `49392` Clear → Clear(`b6128`), Set → `4941e` Set → Clear, Clear → D0 := 1로 계수; 계수(`b612e`): BYTE 8b = 0 → `JSR b7af0`, 아니면 `JSR b7ae4`; Set(`b6146`).
- **`b7ae4`** / **`b7af0`**: A2 / A3 := A5 + `5ddf` / `5de7`(`b7ae4`) 또는 `5dde` / `5de6`(`b7af0`); `MOVEM.L D0/A2-A3,-(A7)`, `JSR 49392`, `MOVEM.L (A7)+,D0/A2-A3`, C Clear → RTS; Set → D0.B = 0이면 A1 := A5 + `5ddc`, 아니면 A1 := A5 + `5de4`, A2 := A3; WORD (A1) += 1, 64 이상(무부호)이면 := 63; BYTE (A2) += 1; RTS.
- **`c0d68`**(FR1 종류 처리기): LONG 64 := `a000`; WORD 42 ≥ `a0`(부호)이면 BYTE 15 bit 0 := 1, 아니면 LONG 64 := −LONG 64; `c6a96`(D0.W 70, D1.W 11, D2.B 0); bank anim 1eb; 설치 `c0dc8`(callback): bit 7 → `4bfa4` / `4be2c`; `b4958`; `b4ab0`(D0.B := BYTE 96); D0 bit 2 = 1 → `c1d2e`(JMP 2a00); `b4334` → C Clear RTS / Set bank anim 1eb, RTS.
- **`cc7b8`** → **`cd0fe`**: D0.B := BYTE 5f, D1.B := (bit 0 of 15 ? ff : 0) ^ D0.B; D1.B bit 7 = 0 → 목록 A(WORD 8c 0..4 / 그 밖: `ce48c` `cecde` `cfde4` `cf636` `d05be` / `d0d26`); 1이고 BYTE 7a ≠ 0 → 목록 B(`ce48c` `ced72` `cfde4` `cf636` `d05be` / `d0d26`); 1이고 7a = 0 → 목록 C(`cdf86` `ce7c4` `cf870` `cf126` `d00e0` / `d07f8`); 그 anim으로 WORD 20 := WORD 8a, D0.W := 100, `JSR 49f8c`; LONG 3a := `20000`, (A6) := `cdd2e`(쓰기만), RTS.
- **`d177e`**: A0 := `d1cba`, D0 := A0(0이 아니라 늘) → A0 := D0, `JSR 4ae4a`; `JSR 8ff4`; WORD 68 / 1e := `1001`, bank anim d2; 소리 `36b`; 설치 `d17e0`(callback): `43e34`, `49fc6` → C Clear RTS / Set `JMP 2a00`.
- [I] 이름: WORD 76 = 선수 번호, 36 / 3a = 속도 LONG, 7f = 시간, 8a = 단계, 8b = 선수 계수 선택, 80 = 거리, A5 + `5ddc..5de7` = 선수별 계수(점수 / 획득 수로 보임). 원본 이름이 아니다. 어떤 적·item·효과인지는 정하지 않았다.

## 공통 규칙·native 검증 계획

FR2..FR13, C1~C10, E1, E2 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr14.cpp`, 함수 `animation_objects_fr14_block`. 오류 문자열은 `unsupported animation objects fr14 PC`(범위 안 내부 PC 직접 진입), `objects fr14 caller requires known carry`(C 소비 block 12개에 Unknown C) 두 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(16 범위, E2 줄 뒤; `)ok=animation_objects_fr14_block(c);`를 같은 줄에 둔다), `carry_preserving_pc`의 E2 묶음 뒤에 주석 달린 case 묶음 하나(소비자 12개), `animation_machine_internal.h`에 선언 하나(E2 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# objects FR14 refresh:` 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 곧바로 들어감 5개는 쓰고 그 값으로 들어가고, 쓰기만 하는 5개(`b5d5a` `b5e46` `b5f00` `b604e` `cdd2e`)는 쓰고 다음 block으로 간다.
- **자료 읽기**(live bus): node field(A6: BYTE `15` `5f` `61` `7a` `7f` `8a` `8b`, WORD `2a`(= 4(26(A6))) `36` `3a` `42` `76` `7c` `8a` `8c`, LONG `0`(설치) `22` `36` `3a` `64` `80`, 쓰기만 WORD `20` `68` `1e` `86`), A5 계수(WORD `5ddc` `5de4`, BYTE `5dde` `5ddf` `5de6` `5de7`), 스택(MOVEM, `364d4` / `364e4`), 고정 ROM·bank(위 "계산 점프와 표"). 단위 시험은 고정 ROM·bank 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): 기록 `363a6..363ae`(`1ab80`의 두 LONG `ffe8ff80 00300040`), anim 표 `363ae..363be`(`2b1000` + 40k), 소리 표 `363be..363c6`(`111 222 333 444`), anim 표 `36522..36532`(`2b2000` + 40k), 기록 `b6270..b6278`(`1aa7e`) `b6278..b6280`(`4941e`), LONG 표 `b6280..b62c0`(16 LONG), bank 창 LONG `200034` → `2a4000`, `2001a8` → `2a1000`(+94), `2001c4` → `2a2000`(+44), `20008c` → `2a3000`(+10). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** 위 "정수 연산(결정 3)". 색인 `(An,Dn.W)`는 An + sext(Dn.W).

## seed·fixture

- **V1(`tools/unit_fixture_specs/fr14.py`)**: FR13 spec의 공용 부분(routing 해석, `first_unrouted`, carry oracle, chain / node / natural / callee family)과 E2 spec의 reinstall family를 쓰고 단위 부분을 바꿨다. world: WORD 76 = 0..3 대부분(표 색인; 큰 색인은 다른 ROM을 anim 포인터로 읽어 native가 어디든 갈 수 있음), LONG 26 = 0 대부분(`49fc6` Set), LONG 56 = 0 대부분(`4b54e`가 contact 목록 없이 BYTE 5e만 봄), BYTE 1d < 4, BYTE `10fd82` = 0, WORD 90 = 4의 배수 < 18(FR2 `b4aca`), A1 / A2 RAM 포인터.
  - block: 시작 200개(소비자 12개 제외). hint(경계): 위 "정수 연산"의 부호·빌림·WORD / BYTE 경계, 접근 계산(LONG 36 / 3a의 부호·0·f·7fffffff·80000000), 표 색인, 계수 62 / 63 / 64 / ffff, mirror node.
  - chain 12개: `3650c`→`36516` `365e6`→`365f0`(`1ab80`), `b5d2a`→`b5d30`(`4b54e`), `b5d3a`→`b5d3e`(`b60da`), `b6038`→`b6042`(`1aa7e`), `b60e4`→`b60ec` `b6104`→`b610e` `b7af8`→`b7b02`(`49392`), `b60f0`→`b60fa` `b6112`→`b611c`(`4941e`), `c0df6`→`c0dfc`(`b4334`), `d17e6`→`d17ec`(`49fc6`).
  - node: `3643e` `364aa` `36588` `b5c34` `b5cec` `c0dc8` `d17e0`((A6) := 진입).
  - natural(결정 6): 확장 관측 pack frame 42개(scratch `natscan_fr14.py`: FR14 callback의 처음·4번째·12번째·20번째마다·마지막 frame, 그리고 FR14로 들어가는 routing된 callback(`NATURAL_ROUTED`: FR13 `d176e` `717e8` `d15c4`, FR12 `716ca`, `cc7b8`에 처음 닿는 frame의 `76984` `76d94` `cd8ee` `cdd2e`)의 처음 실행 frame). reinstall 14개: frame 시작 상태에 남지 않는 진입 `3643e` `3657c` `b5c34` `c0d68` `cc7b8`(BYTE 5f / 7a 셋) `d177e`를 그 다음 frame의 자연 node(callback `364aa` / `b5cec` / `c0dc8` / `cdd2e` / `d17e0`를 가진 node)에 callback LONG으로 쓴다. [I] 이미 초기화된 node를 다시 들어가는 world이며 native와 C++가 같은 상태를 받으므로 비교는 유효하다(E1·E2 결정과 같음).
  - callee: `7177a` `71786` `71874` `d1632` `d177e` `cc7b8` `cd0fe` `c0d68` `3657c` `b6056` `b6084` `b60c4` `b60da` `b7ae4` `b7af0` `b6038` `364aa` `36588` `b5c60` `3645a` `36532` `b5d02` `36502` `cd1d4` `cd2a0`.
  - error: 내부 PC 800, 홀수 PC, Unknown C 12, 홀수 node / A1 / stack(MOVEM 넣기·꺼내기, RTS, `364e4` 꺼내기), 고정 ROM 쓰기, 실행 뒤 실패(`cc7b8` → `cd110` 홀수 node, `b7ae4` → `b7af8` 홀수 stack, `36576` → `36578` ROM 쓰기).
  - negative: RAM bit, 레지스터, stop, queue 추가.
- **단위 시험(Unicorn 생성기, `tools/generate_animation_machine_objects_fr14_test_table.py`)**: FR13 생성기 꼴(flag reader 행 없음, 계산 점프 없음). 합성 physical byte는 위 "공통 규칙". 행: single(시작 188개 × 들어오는 C 3가지, 모든 분기 양쪽), path(188 진입), 사슬 10개(두 C 값; `c0df6`·`d17e6`은 `49fc6`이 bank 장치에 써서 native run이 버려져 선언 행만), 선언 C(소비자 12 × 2), error 43(실패 PC 4개 이동), zero-step, 내부 PC 800 정확 오류, rollback 탐침, 경계 stop(routing된 출구 27개 전부). 손 규칙(`rules_a`..`rules_d`): `3643e` 쓰기와 이웃 BYTE, `36452` bit 3, 표 색인의 WORD 산술·부호 확장(WORD 76 `ffff` → `363aa` / `363bc`, `4001` → 칸 1)과 표 밖 색인의 ROM 오류, `MOVE.W #100` / `MOVE.B #0,D1`의 상위 유지, `3648c` / `36564`의 WORD 3a / 36 덧셈(LONG의 다른 WORD 유지)·NEG.W, 접근 계산 9쌍(`asr4` 기준식과 대조)·`fffffff1` / `1` / `80000000` / `7fffffff`·ADDI 넘침(`7ffffff1`), `36588`의 BYTE 7f 빌림·`BSET` 이전 bit·JMP 2a00, `364e4`의 꺼낸 LONG·NEG.L·`BSET` 쓰기, 소비자의 선언 C 두 값과 Unknown C 오류, `3657c` 설치와 이웃 BYTE, NEG.L / NEG.W fall-through 넷의 폭, `b5c34`·`b5c60`의 BSET / BCLR·LONG 64·SWAP, `b5c9a` / `b5cb2`의 쓰기 폭(이웃 BYTE)·bank anim, `b5ce6` 설치와 `b6056` 갈래, `b6070` CLR.L 폭, `b5cf6` WORD 2a, `b5d02` BYTE 8a 8가지(ADDQ.B / ANDI.B, D0 = 4k), 설치 쓰기 셋과 LONG 80, `b6084` / `b60c4` NEG.L, `b6098` / `b60a4`의 부호·CLR(`80000000` − 1 = `7fffffff` 양수), `b60da`·`b60ec`·`b60fa`·`b610e`·`b611c`의 두 갈래와 CLR.W / MOVE.W의 상위 유지, MOVEM 순서(넣기: SP − 20..− 4, 꺼내기: D0 / A2 / A3), 계수 WORD `ffff` → 0 / `7fff` → `8000` → 63 / 62 → 63, BYTE 계수, `c0d68`의 부호 WORD 6가지·NEG.L·`c6a96` 인자 폭, bank anim 1eb / d2, `c0dee` bit 2, `cd0fe` 부호 시험 8가지(D0 / D1 상위 유지), 세 anim 목록 × WORD 8c 10가지와 그 뒤 `cd360`(LONG 3a, `cdd2e`, 이웃 BYTE), `cd132` / `cd264`의 WORD 비교, `d177e` / `d178a`, `d1798`·`d17cc`·`d17da`.

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `b376d62144aeacdbbfbb0a36b265669b896f9e2f63eaa1b363f77e664366eeed` → `1feb63c9de015b8ceb3ecc56ae51b31cba1bf0a17a726216db249697e718db2f`, `animation_machine_internal.h` `4592d7ce786f860f34fbf253c234018e45329eccdd3ce5e83d2ee7f39dfd1b99` → `1d4a08c30c9e9e9dbfeb4dd8b8fea3e5dad8b8f2640e1df430dd3b5310f0d3f3`(옛 값은 `# objects FR14 refresh:` 주석). 마지막 편집 뒤의 파일 SHA이고, 두 검증기의 pin 4 / 9개가 모두 파일 SHA와 같음을 작업 트리와 scratch clone root에서 확인했다(아래 "검증 수치").
- [F] `tools/verify_animation_machine.py` `SOURCES`에 `animation_machine_objects_fr14.cpp`.
- [F] **FR12 시험 생성기·시험**(`tools/generate_animation_machine_objects_fr12_test_table.py`, `engine/tests/animation_machine_objects_fr12_test.cpp`; 오류 행. 이전 = FR14 PC에서 `unsupported animation machine PC`. FR14가 그 PC를 routing해서 C++가 FR14 코드를 실행하므로 바뀜. FR13 선례대로 경로를 따라 실패 PC를 옮김. 고치기 전에는 `make test`가 `7176a: missing or ambiguous physical program bus ROM byte expected unsupported animation machine PC`로 실패했다(`trial_logs/make_full1.log`)):
  - `error-7176a-then-7177a` → `error-7176a-then-7177c-odd-node`: 홀수 node, FR14 `7177a` → FR12 `7177c`의 `MOVE.L D0,64(A6)`가 `invalid animation machine write size/alignment`.
  - `error-7177c-then-71786` → `error-7177c-then-717a4-odd-stack`: D0 = `80000000`, BYTE 15 = `80`, FR14 `71786` → FR12 `71788` → `7179a` → `717a4 JSR 4945e`의 push가 홀수 A7에서 `program bus requires even WORD/LONG address`(stop `4945e`).
  - 생성기를 다시 돌려 그 2행만 바뀜을 확인했다(`work/fr12_test_before_fr14.cpp` 대비 diff). fixture 수 1,127 그대로.
- [F] **FR13 시험 생성기·시험**(`tools/generate_animation_machine_objects_fr13_test_table.py`, `engine/tests/animation_machine_objects_fr13_test.cpp`; 같은 이유):
  - `error-71860-then-71874` → `error-71860-then-71876-odd-node`: 홀수 node, FR14 `71874` → FR13 `71876`의 `MOVE.L D0,64(A6)`가 alignment 오류.
  - `error-d161a-then-d1632` → `error-d161a-then-d1654-odd-stack`: FR14 `d1632` → FR13 `d1636` / `d1644` → `d1654`(`ofr13_ease`)의 `JSR 4be34` push가 홀수 A7에서 실패(stop `4be34`).
  - `error-d177a-then-d177e` → `error-d177a-then-d178a-odd-stack`: C Set, FR14 `d177e` → `d178a JSR 4ae4a`의 push가 홀수 A7에서 실패(stop `4ae4a`).
  - 생성기를 다시 돌려 그 3행만 바뀜을 확인했다(`work/fr13_test_before_fr14.cpp` 대비 diff). fixture 수 909 그대로.
- [F] **V1 spec**:
  - `fr12.py`: `ROUTED_LATER`에 `7177a` `71786`을 더했다(그 run은 그 PC에서 계속 멈춘다; `EXIT_STOPS`는 그대로). 오류 fixture `7176a-then-7177a` → `7176a-then-7177c-odd-node`, `7177c-then-71786` → `7177c-then-717a4-odd-stack`(위 생성기와 같은 뜻).
  - `fr13.py`: `ROUTED_LATER` `()` → (`71874` `d1632` `d177e` `7177a` `71786`). 오류 fixture `71860-then-71874` → `71860-then-71876-odd-node`, `d161a-then-d1632` → `d161a-then-d1654-odd-stack`.
  - `se2.py`: `ROUTED_LATER` `()` → (`71874` `d1632` `d177e` `7177a` `71786`)(E2 run의 선언 정지는 그대로).
- [F] **바뀌지 않음(확인)**: 저장소 engine 소스·시험·tools·spec·`docs/analysis/data`·`config`에서 FR14 범위 안 PC와 이웃(`365fc` `3657c` `cc7ac` `cc7b0` `cc83a` `cc8ea` `7177c` `71788` `71876` `d1636`)을 쓰는 4·5자리 hex literal을 전수 검색했다(`tools/fr14refs_repo.py` → `work/fr14refs_repo_v1.out`). 대소문자 무관 재검색(`verify_animation_machine_*.py`에 `b5c34` `c0d68` `3643e` `cd0fe` `d177e`)도 0건.
  - 정지 전용·값 전용 행(정지 검사가 dispatch보다 먼저라 routing이 바뀌어도 같음): FR12 시험·spec(정지 `7177a` `71786`이 single / path 행의 다음 PC), FR13 시험·spec(정지 `71874` `d1632` `d177e`, 표 `TABLE`의 `cc8ea`), FR4 시험·생성기·spec(`TARGETS`의 `cc7b8` `cc83a` 정지, `cc7a0-3` / `cc7a0-4`·`cc822-3` / `cc822-4` 행의 stop, RANGES 끝 `cc7ac`), FR8 시험·spec(RANGES 끝 `cc7b8`), FR11 시험·spec(`neighbours[]`의 `cc83a`, RANGES 끝 `cc836..cc83a`: `!in_ranges`만 확인), FR10 시험(`neighbours[]`의 `b7b2e`: `!in_ranges`만 확인; 주석의 "unrouted"는 FR10 시점의 설명), C5 시험·실행부(`1cc88`의 자식 값 `365fc`, stop `2986`), FR2b spec(`71876`은 FR13 기록 주석), FR12 / FR13 실행부(`7177a` `71786` / `71874` `d1632` `d177e`를 분기 대상으로 씀), FR4 실행부(표 시작 `cc7ac`), `docs/analysis/data/animation-machine-frame-head-leaders.json`(10진 숫자열의 우연한 적중).
  - 검증기(`tools/verify_animation_machine_*.py`)에는 FR14 PC를 이웃·탐침·"unsupported PC"·frontier 기대값으로 쓰는 literal이 없다. 그래서 바꾼 검증기는 `CPP_PINS`와 `SOURCES`뿐이다. [U] artifact에서 기대값을 읽는 검증기의 동적 경로는 메인의 통합 sweep이 확인한다.
  - V1 spec의 `ROUTED_LATER` / `EXIT_STOPS`: FR14 PC를 정지로 가진 spec은 fr12·fr13·se2뿐이다(위). 앞 단위 시험의 오류 행·V1 오류 fixture 가운데 FR14 PC를 대상으로 하는 것은 위 FR12 2 / FR13 3(시험), fr12 2 / fr13 2(V1)뿐이다.
  - `make -j4 all test`가 위(FR12·FR13 생성기 행) 말고 기존 시험이 모두 그대로 통과함을 확인했다. V1 회귀 pc1–pc10, se1, se2, fr9–fr13도 통과했다(아래).
- [F] 앞 단위 계약의 뒤 단위 변경 기록: FR12 계약(`7177a` `71786`), FR13 계약(`71874` `d1632` `d177e`), E2 계약(`ROUTED_LATER`), FR4 계약(표 `cc7ac` 칸 3), C5 계약(표 `1cc04` 칸 1 자식 `3643e`, `365fc`의 `BRA.W` 대상 `3657c`).
- [I] 원래 IO 관측과 frame 비교(d1·controller·irq·demo)는 FR14 코드를 실행하지 않으므로 결과가 같아야 한다. 메인 runner가 확인한다.

## 결정

1. **범위: 200 block, 16 범위(계획 199 + `3657c`).** 가상 routing 재관측에서 새로 보인 PC가 없고(숨은 직선 block 0), 범위 밖에서 범위 안 비시작 PC로 오는 실제 분기는 routing 밖 C5 `2986` 자식 `365fc`의 `BRA.W 3657c` 하나라 `3657c`를 시작으로 더했다(범위·명령 불변). 예측 14,500(+1,914), 첫 정지 없음.
2. **계산 점프·표.** FR14에는 계산 점프가 없다. 받는 계산 착지(`3643e` `b5c34` `c0d68` `cc7b8`)는 기존 실행부의 규칙 그대로다. 표 `cc82e` / `cc8de`의 같은 대상 칸 `cc83a` / `cc8ea`는 실행되지 않아 정지로 둔다. 고정 ROM 표(`363ae` `36522` `363be` `b6280`)와 bank 창은 live bus로 읽고 상한을 검사하지 않는다(원본과 같음). 색인은 부호 확장한다.
3. **정수 연산**: ASR.L #4는 부호 채움, 부호 / 무부호 비교는 정확히, WORD / BYTE 대상은 하위만, MOVEM은 68000 순서, `BSET`의 Z는 이전 bit.
4. **flag.** C 소비자 12개는 known C를 읽거나 checked 오류(`b7b02`는 MOVEM 뒤의 BCC). 생산자 2개(`b6128` Clear, `b6146` Set)는 block 안에서 C를 정한다. dispatcher carry 보존 목록에 소비자 12개만 더했다. Z / N 경계는 없다(RAM·고정 ROM에서 다시 계산할 것이 없음).
5. **앞 단위 spec·시험.** FR12 / FR13의 뒤 단위 정지 가운데 FR14 진입을 fr12·fr13·se2의 `ROUTED_LATER`에 두어 그 run은 계속 그 PC에서 멈춘다. 오류 fixture는 경로를 따라 실패 PC를 옮긴다(위).
6. **V1 natural / reinstall family.** 확장 관측 pack frame 42개(natural 94개) + reinstall 14개(frame 시작에 남지 않는 진입 6가지).
7. **입력 port.** FR14는 장치를 읽지 않는다(E1 결정 2(개정)의 queue 규칙과 충돌하지 않음).
8. **다음.** FR14 연결로 확장 관측 IO 14,500 / 14,500(+1,914)을 메인 runner가 확인한다. 확장 관측의 IO 단위 8개(C9, FR10, C10, FR11, FR12, FR13, E2, FR14)가 모두 끝났다(아래 "확장 관측 완료 판정").

## 확장 관측 완료 판정

- [F] **재측정(FR14 routing, 확장 관측)**:
  - 공유 관측 `artifacts/animation_machine_io_ext` 그대로(`work/remeasure_ext_after.dleft`, routing `1feb63c9`): 실행된 routing 밖 PC **C 0 / D 0 / E 0**, 예측 일치 frame 14,500, 첫 정지 없음.
  - 정확 bitmap 재관측 `reobs/fr14final`(실제 FR14 routing 작업 트리, 관측기 수정 없음): 실행된 routing 밖 PC **C 0 / D 0 / E 0**(12 run 모두 P0 기준선과 덮는 단일 PC 원자 closure 밖의 기록 0), 예측 14,500, 첫 정지 없음(`reobs/fr14final.dleft` `.stops`). native 기록(run별 `digest_chain`)은 `fr14base`·`fr14v1`·공유 관측과 12 run 모두 같다.
  - [F] **IO 비교**(작업자 1회, 아래 "검증 수치"): native 비교 frame 14,500 가운데 일치 **14,500**, 불일치 0, C++ 오류 0, 수용 키 모두 true, 첫 정지 run 0.
- [F] **예측 첫 정지: 없음.** 12 run 모두 끝(P0 / P1 600 frame-limit, X1~X4 system-return guard)까지 일치한다.
- [F] **계획했지만 실행되지 않은 것**(이 관측에서 실행 0; `fr14final`에 routing 밖 실행 PC가 없으므로 아래 어느 PC도 실행되지 않았다):
  - **C11~C14(683 block)**: C11 `ca5c..1deea` 171, C12 `1deea..1e5ec` 171, C13 `1e5ec..21ea0` 171, C14 `21ea0..` 170(계획 §10.5, scratch `starts_C11..C14.txt`). [I] 대부분 등장 방식·탈것으로 보이는 stage 의존 경로다: `1d388` 사슬의 등장 방식 코드 D7(1, 3…f), `1de28`/`1de30`의 `1aa3a` bit. 이 값은 입력이 아니라 stage가 정하는 것으로 보이고(§10.2), 이 관측은 mission 0의 두 seed 묶음(case 94 / 68)뿐이다.
  - **선언 정지**: `1e67a`(C6 `28ae` 자식), `1e918`(C6 callback), `23c56`, `36350` `371f8`(C9 `28ae` / `2986` 자식), C1 계획의 미룬 입구 11곳(`1d3e0` `1de3c` `1e21c` `1e8de` `1fc96` `1fd3c` `1fd50` `21ea0` `21fa6` `4eb6a` `4ef08`)과 `4e69a`(pc10 `EXIT_STOPS`), TRAP 경계(`b3e58` `b3eac` `e6d92` `e6dd0`; 선수 2 이상, 경계 밖 index).
  - **routing 밖 계산 착지·쓰기만 하는 값**: FR4 표 칸 45개(`cc7ac` / `cc82e`; `cc83a` 포함), FR13 표 `cc8de`의 26칸(`cc8ea` 포함), C3 `2031c` / C7 `2529c` / C10 `203b0` / FR11 `b42b8` `c54b2`의 남은 칸과 handler `b4036`, FR14의 쓰기만 설치 `b5d5a` `b5e46` `b5f00` `b604e`, routing 밖 형제 자식 `363c6` / `3640e`(C5 표 칸 2)·`365fc`(C5 `1cc88`)·`e6952`(FR2 `e693a`).
  - 남는 이유 [F]: 이 관측(입력 설정 X1~X4 + 대조 P0 / P1, mission 0, case 94·68)에서 그 코드에 닿는 상태가 생기지 않았다. 남은 PC는 정적 closure로만 알고, 실행 근거(관측 frame)가 없다. 계획 §10.x 메인 결정대로 다른 관측 뒤에 다시 잰다.
- **다음 관측 권고**(계획 §10.7 결정 6의 구체화, 사용자·메인 결정):
  1. 다른 mission의 stage seed(또는 stage 진행 seed). [I] C11~C14의 `1d388` 등장 방식(D7)과 `1aa3a` bit, 탈것 경로는 stage가 정한다. mission 0 밖의 mission(그리고 mission 0의 뒤 area)의 stage seed를 같은 입력 설정 X1~X4로 관측하면 C11~C14와 선언 정지의 큰 부분이 실행될 것으로 보인다 [I]. 그런 seed는 아직 없다: 원래 관측의 P1 seed는 mission 0의 두 묶음뿐이다(§10.2).
  2. P2 동시 입력(P1b): `b60da`의 선수 2 쪽(`b6104`..), E2 `e6dc2` / `e6e00`, FR14 계수 `b7ae4` / `b7af0`의 선수 1 쪽.
  3. 같은 seed에서 run을 game over 뒤 continue / 다음 area까지 이어 가는 입력(BIOS 없이 선언 host 쓰기로; §10.2의 `default-settings`와 같은 선언 방식).
  4. 관측 크기·시간: 이번 관측은 run 12개, 14,508 frame, 약 17 MB, 150초다. mission을 늘려도 run당 비용은 비슷하다.
  - 관측을 `artifacts/`에 둘지는 사용자 결정이다(이번 관측은 메인이 `artifacts/animation_machine_io_ext`로 옮긴 것을 읽기만 했다).

## 미확인

- [U] node field·전역 값의 의미(위 "block 의미"의 이름), A5 + `5ddc..5de7` 계수가 무엇을 세는지, `b6280` 표의 뜻, `cd0fe`의 세 anim 목록(BYTE 5f / 7a 조합)의 뜻. 이름은 동작에서 붙인 [I]이다. 어떤 적·item·효과인지는 정하지 않았다.
- [U] IO 관측에서 실행되지 않은 분기 쪽(위 "IO 실행"의 109개: 계수 `b7ae4..b7b2e` 전부, `36532` 계열 등)은 V1 선언 상태·reinstall·실제 ROM 차분·단위 시험으로만 확인했다.
- [U] `365fc`(C5 `1cc88`의 `2986` 자식)가 실행되는 조건(BYTE 9f / a0의 다른 값으로 보임 [I]). 이 단위는 그 분기 대상만 시작으로 둔다.
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC; 이번에는 첫 정지 없음).
- [U] natural / reinstall fixture의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C10, FR10~FR13, E1, E2와 같음).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr14.cpp`(case label 200 = `starts_fr14_final.txt`와 집합 일치; 공용 함수 `ofr14_get` `ofr14_put` `ofr14_bit` `ofr14_btst` `ofr14_bset` `ofr14_carry` `ofr14_install` `ofr14_asr4` `ofr14_signed_word` `ofr14_add_word` `ofr14_add_long` `ofr14_sub_long` `ofr14_bank_anim` `ofr14_anim` `ofr14_table_anim` `ofr14_table_sound` `ofr14_step`), `engine/tests/animation_machine_objects_fr14_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_d`), `tools/generate_animation_machine_objects_fr14_test_table.py`(생성기; FR13 생성기 꼴, V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 80초), `tools/unit_fixture_specs/fr14.py`(V1 spec; FR13 spec의 공용 부분, E2 spec의 reinstall, 단위 부분 교체, `CONSUMERS`(12), `CLEAR_SET`(`b6128`), `SET_SET`(`b6146`), `EXIT_STOPS`(C1~C9의 남은 12), `CHAINS`(12), `NODE_ENTRIES`(7), `NATURAL`(42 frame), `NATURAL_ROUTED`(8), `REINSTALL`(14), `STATIC_IMPOSSIBLE`(`d177e` → `d1792`)). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `work/starts_fr14_final.txt`(SHA256 `d40487be…`).

- **`3643e..36522`(21)**: `3643e 36452 3645a 36474 3648c 3649e 364a0 364aa 364ba 364c0 364ce 364d4 364e4 364f0 364fa 36500 36502 3650c 36516 3651a 36520`
- **`36532..365d0`(13)**: `36532 3654c 36564 36576 36578 3657c 36588 36598 3659e 365ac 365b2 365c0 365ca`
- **`365d4..365fc`(7)**: `365d4 365da 365e0 365e6 365f0 365f4 365fa`
- **`7177a..7177c`(1)**: `7177a`
- **`71786..71788`(1)**: `71786`
- **`71874..71876`(1)**: `71874`
- **`b5c34..b5c4c`(2)**: `b5c34 b5c48`
- **`b5c60..b5d5a`(20)**: `b5c60 b5c68 b5c78 b5c84 b5c9a b5cb2 b5ce6 b5cec b5cf0 b5cf6 b5d02 b5d2a b5d30 b5d34 b5d3a b5d3e b5d42 b5d48 b5d50 b5d56`
- **`b6038..b604e`(4)**: `b6038 b6042 b6046 b604c`
- **`b6056..b614c`(36)**: `b6056 b6060 b6066 b606a b6070 b607a b6082 b6084 b608e b6092 b6098 b60a2 b60a4 b60b0 b60b4 b60c2 b60c4 b60d2 b60d4 b60da b60e4 b60ec b60f0 b60fa b60fe b6104 b610e b6112 b611c b6120 b6128 b612e b6136 b613c b6140 b6146`
- **`b7ae4..b7b30`(11)**: `b7ae4 b7af0 b7af8 b7b02 b7b0a b7b10 b7b18 b7b1e b7b28 b7b2c b7b2e`
- **`c0d68..c0e2a`(17)**: `c0d68 c0d7a c0d82 c0d88 c0d9a c0dc2 c0dc8 c0dd2 c0dd8 c0ddc c0de2 c0de8 c0dee c0df6 c0dfc c0e00 c0e28`
- **`cc7b8..cc7bc`(1)**: `cc7b8`
- **`cd0fe..cd370`(53)**: `cd0fe cd110 cd118 cd12e cd132 cd13a cd150 cd154 cd15c cd172 cd176 cd17e cd194 cd198 cd1a0 cd1b6 cd1ba cd1d0 cd1d4 cd1dc cd1e4 cd1fa cd1fe cd206 cd21c cd220 cd228 cd23e cd242 cd24a cd260 cd264 cd26c cd282 cd286 cd29c cd2a0 cd2a8 cd2be cd2c2 cd2ca cd2e0 cd2e4 cd2ec cd302 cd306 cd30e cd324 cd328 cd330 cd346 cd34a cd360`
- **`d1632..d1636`(1)**: `d1632`
- **`d177e..d17f8`(11)**: `d177e d178a d1792 d1798 d17cc d17da d17e0 d17e6 d17ec d17f0 d17f6`

## 검증 수치

작업자 최종 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j4 all test`(최종 실행부·시험): 종료 0, 경고 0, Assert 0, Python 310 OK, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄(`trial_logs/make_final.log`). FR14 시험 줄: `animation machine objects fr14: 997 fixtures (584 single-block, 286 path, 60 producer chain, 24 declared C, 43 checked error (4 with a later failing PC), 92 kept C), 200 blocks, 4426 calls, 109529 checks`. 생성기 보고(`trial_logs/gen2.log`): 단일 행 없는 시작 0, 출구 중 stop이 아닌 것 0, 실제 사슬 10개(`3650c`→`36516` `365e6`→`365f0`(`1ab80`), `b5d2a`→`b5d30`(`4b54e`), `b5d3a`→`b5d3e`(`b60da`), `b6038`→`b6042`(`1aa7e`), `b60e4`→`b60ec` `b6104`→`b610e` `b7af8`→`b7b02`(`49392`), `b60f0`→`b60fa` `b6112`→`b611c`(`4941e`); 모두 두 C 값), 후속이 빠진 분기 block 1개(`d177e` → `d1792`: 상수 시험이라 원본에서도 불가능, V1 `STATIC_IMPOSSIBLE`). `c0df6`·`d17e6`의 `49fc6` 사슬은 `49fc6`이 bank 장치에 써서 native run이 버려져 선언 행만 있다(V1에서는 두 쪽 모두 나옴, 아래). 생성기를 다시 돌려 FR14 시험 파일이 바이트 단위로 같음을 확인했다(SHA256 `66cad35466adef0c…`, `trial_logs/gen_repro.log`). FR12 시험 줄은 fixture 1,127, FR13은 909 그대로(오류 행 2 / 3만 바뀜). 첫 실행(`trial_logs/make_full1.log`)은 FR12 시험의 옛 오류 행(`7176a`)에서 실패했고, 생성기 갱신 뒤 통과했다.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, `work/ubsan.sh`, FR14 시험): 빌드 경고 0, 실행 종료 0, runtime error 0(`trial_logs/ubsan_build.log` `ubsan_fr14.log`; 최종 시험으로 다시 실행).
- [F] V1 fr14(작업자, `--workers 3`, 1회): fixture 1,783개(match 944, error 829, mismatch 10; block 709, chain 24, node 16, natural 94 + reinstall 14, callee 84, failpc 3, negative 10) failed 0, `ok` true, 방문 시작 200/200, 빠진 후속 없음, 도달 못한 분기 결과 없음, carry oracle Unknown/Clear/Set = 900/15/29(`work/v1/v1_fr14_try1.log`, `work/v1/v1_fr14_try1/report.json`). 첫 시도에서 통과했다.
- [F] V1 회귀(작업자, `work/v1_regs.sh`, `--workers 2`; `work/v1/v1_regs.txt`): pc1 1,264, pc2 1,743, pc3 1,829, pc4 1,873, pc5 1,755, pc6 1,856, pc7 2,077, pc8 986, pc9 2,347, pc10 1,334, se1 2,102, fr9 1,415, fr10 2,170, fr11 2,170, fr12 2,302, fr13 2,122, se2 1,573(모두 failed 0, `ok` true). fr12 / se2는 E2 기록과 같은 수다(fr12는 바꾼 오류 fixture 2개와 그 failpc 2개만 이름이 다름). fr13은 2,126 → 2,122다: 바꾼 오류 fixture 2개(+ failpc) 말고, node / callee family가 고른 world 몇 개가 바뀌었다(이전 node `71884-2` `719f8-2` `71a62-2` `d176e-1` `d176e-2`, callee `720e0-8` `cc8c0-5..7` `d172e-3` → 이후 node `bfd88-1` `c557a-1`, callee `71fc2-8` `cc8d2-4` `d161a-4` `d1670-2`). [I] FR14가 `cc7b8`(FR4 `cc7a8` 표의 칸)을 routing해서 `first_unrouted`의 정지가 그 run에서 옮겨 가고, 고르는 key(정지, 지나간 FR13 block)와 난수 소비가 바뀐 결과다. 모든 fixture가 통과한다. 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1 / +2, 크기, bit 번호·op, WORD/BYTE → LONG, 복귀 PC·호출 대상, carry swap / tag, mask, 상수·설치 값, `ofr14_bank_anim` / `ofr14_anim` / `ofr14_table_anim` / `ofr14_table_sound` / `ofr14_step` / `ofr14_bset` 인자, A5 변위) + 손으로 고른 helper·block 변이(ASR 논리·채움·3 bit, 부호 WORD 비교의 무부호화, WORD / LONG 덧셈의 폭·뺄셈, SUB.L의 부호·순서·폭, bank anim의 창 폭·변위·A0·D0, anim의 WORD 20 폭, 표 색인의 부호 확장·LONG·× 2, 소리 D1 폭, `step` D0 폭, NEG 폭 넷, 접근 계산의 D2 초기화·D3 목표·+f / +10, `364d4` push 값, `364e4` WORD 꺼냄, BSET 이전 bit, `365b2` 새 값 시험, `b5c84` SWAP·상위 유지, `b5d02` MOVEQ·mask·× 2·A0, `b5cf6` A0, `b6098` bit 15, `b60a4` 덧셈·이전 값, `b60b4` D0, MOVEM 순서·WORD·A2 / A3, `b7b0a` WORD, `b7b18` A2, `b7b1e` 다시 읽기·부호·63 / 64, `c0d68` 무부호·엄격, `c0d88` D2 폭, `cd0fe` SNE 반전·D1 / D0 LONG·EOR 없음, `cd110` D0 LONG, `cd132` / `cd198` 폭, `cd1d4` WORD, `d177e` D0 WORD, `d178a` A0) + dispatcher carry 목록 12개·범위 29개를 적용해 만든 것, 597개; `--workers 3`): 1회째 `killed 583 of 597`(`trial_logs/mut_first.log`). 생존 14개 중 4개는 시험 빈틈이었고 규칙으로 메웠다(`cd154` / `cd176`의 `CMPI.W #2 / #3`를 BYTE로 읽는 변이: WORD 8c = 102 / 103을 세 목록에 더함; `cd1d4`의 `TST.B 7a`를 WORD로 읽는 변이 둘: BYTE 7a = 0, 7b = 80; 네 변이 다시 실행 `killed 4 of 4`, `trial_logs/mut_gaps.log`). 남은 10개는 동치다(`mut/equivalents.txt`, 사례별 이유: `ofr14_bank_anim`의 첫 `LEA 26(A6),A0`은 두째 LEA가 덮어써 죽은 값(둘), `am_word`가 하위 WORD만 남기는 `0x10000 − D0`(둘), `b5d02`에서 `MOVEQ #0` 직후라 BYTE / LONG 쓰기와 초기값 1이 같은 D0이 되는 셋과 D0 ≤ f의 WORD / LONG 덧셈, `am_write`가 size byte만 씀(둘), 이 단위의 `ofr14_get` / `ofr14_put` 변위는 모두 8000 미만 상수(부호 확장 없음과 같음)). 규칙을 더한 뒤 전체 2회째 `killed 587 of 597`(`trial_logs/mut_second.log`), 남은 10개가 동치 목록과 같다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`, 메인 runner용), `real_fr14.py`(E2 harness에 FR14 world(`fr14_world`: WORD 76 / 2a / 3a / 36 / 42 / 46 / 7c / 8a / 8c, BYTE 15 / 5e / 5f / 61 / 7a / 7f / 8a / 8b, LONG 36 / 3a / 64 / 80 / 56 / 26, A5 계수 `5ddc..5de7`, BYTE `568e(A5)`, 선수 기록 `100cb8` / `100da8`의 WORD 42 / 46)·소비자 12·선언 정지(E2 TRAP `e6d92` `e6dd0`, TRAP `b3e58` `b3eac`, C1~C9의 남은 정지 12, 앞 단위 계산 점프의 routing 밖 대상; FR12 / FR13의 뒤 단위 정지 5개는 FR14 block이라 뺐고 routing 밖 FR4 표 칸은 46 → 45)·`cb` 진입(callback 7, 처리기 `c0d68`, 표 칸 `cc7b8`, `3657c`, fall-through 5, subroutine 7, 생산자 호출 11, `364e4`(꺼낼 LONG) / `b7b02`(MOVEM 꺼낼 D0 / A2 / A3) / `b7b0a`..`b7b2c`(A5 계수 포인터) 직접 진입); 계산 점프 착지를 trace 전체에서 대조(앞 단위 표 그대로; FR14에는 계산 점프 없음); `native_safe` 기본 유지)): 작업자 300건 seed 1 `mismatches 0`(`covered starts 189 of 200`; 깨끗이 멈추지 않은 native 22건 건너뜀 [I: 3,000,000 명령 안에 멈추지 않는 routing된 후속 `c0d68` / `c0dc8` 쪽 등]; native oracle abort 0, 홀수 주소 0, 문서화된 분류 0건, `trial_logs/real_n300_s1.log`). 실행 중 FR14 소비자 12개가 실제 생산자 뒤에 native 분기와 비교되었다(`36516` 25, `365f0` 17, `b5d30` 11, `b5d3e` 12, `b6042` 18, `b60ec` 23, `b60fa` 16, `b610e` 34, `b611c` 28, `b7b02` 28, `c0dfc` 10, `d17ec` 10). 덮개를 보려고 seed 2 300건도 돌렸다: `mismatches 0`, 183 / 200(`trial_logs/real_n300_s2.log`); 두 seed 모두 빠진 시작은 `3649e` `b5ce6` `cd12e` `cd194` `cd330`(`49f8c` / `8ebe` 정지 뒤의 block이라 직접 진입으로만 닿음; 메인의 5 × 1,500에서 덮일 것으로 봄 [I]).
- [F] **IO, 입력 확장 관측**(FR14 연결 뒤, `--workers 3`, `MS5_SEED_DIR=artifacts/stage_entry_body`): run 12, native 비교 frame 14,500 가운데 일치 **14,500**(예측 14,500, 기준선 12,586 → +1,914), 불일치 0(beyond 0), C++ 오류 0, chain divergence 0, unrouted 0, 수용 키 모두 true(`negatives_ok` `frontiers_confirmed` 포함), 관측 pin `io-ext`(`trial_logs/io_ext_fr14.log`; `verification.json` SHA256 `0a13b61ce93e6a66…`, `frontier.json` `61caf880a4a0cdea…`, scratch `io_ext_fr14/`). run별 일치: P0 1,200, P1 1,200, X1 2,552, X2 2,612, X3 3,656, X4 3,280. 12 run 모두 끝(P0 / P1 frame-limit, X run system-return guard)까지 일치하고 첫 정지 run은 0이다 — 재관측 예측(`reobs/fr14v1.stops`, `fr14final.stops`)과 같다.
- [F] 원래 IO 관측·frame 비교·legacy 검증기는 작업자가 돌리지 않았다(메인 runner).
- [F] `CPP_PINS`: 작업 트리와 scratch clone root(`work/mkroot.py`; 확인 뒤 symlink를 먼저 지우고 삭제)에서 파일 SHA와 같다(4 / 9 pin, 불일치 0, `trial_logs/pincheck_tree.log` `pincheck_root.log`).
