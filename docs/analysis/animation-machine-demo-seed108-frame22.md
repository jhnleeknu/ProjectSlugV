# controller demo 선언 seed 108·109 불일치(frame 22·60): U06 경계 callee `e7562`

**상태: 원인 분석과 단위 제안(구현 전). engine/ 변경 없음.** 구현은 다음 하위 작업이다.

[F]=원본 바이트 또는 이 작업의 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인.

- ROM: canonical BE program(`extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB). 관련 코드는 모두 `<100000`에 있어 **file offset = CPU 주소**다(bank 무관).
- 기준 트리: `claude/b-followups` `6134dd1`, `engine/src/animation_machine.cpp` SHA256 `aba5bec0b6450b00b0259478ccdbe6c0fa133ec9e481145117b3a2631aa68cc9`. U06 계약 `animation-machine-objects-u06-contract.md` SHA256 `6d628d0fa1e907e75f06d2906433fb5afbf2d215320be6beee8ebeb6bebd7e63`.
- seed: `--seed-dir artifacts/stage_entry_body`(historic pin `1f65100f…`). 선언: `--declare demo`(frame 1에 LONG `1008e4` := `c66a`, BYTE `104cd4` := 1).
- scratch: `/Users/start/Workspce/ms5-scratch/demo108/`(분리 worktree `wt`, `6134dd1` detached, 커밋 없음).

## 요약

1. [F] **실패 PC는 `e7562`다.** frame 22(seed 108·109 공통)의 N pass에서 C++는 U06 block `e7462`(`BSR.W e7562`)까지 실행하고, routing에 `e7562`가 없어 `unsupported animation machine PC`로 끝난다. 이때 `A6 = 100f5c`(script 객체 `e73f8` 노드, callback LONG `(100f5c)` = `e7426`), `A5 = 108000`, `A7 = 1feff8`, `D7 = 10`, `D0 = ffffffff`.
2. [F] **두 번째 불일치 frame은 23이 아니라 60이다.** 400 frame 실행에서 불일치는 seed마다 frame 22와 60뿐이며, 둘 다 같은 `e7562` 오류다(STATUS/0265의 "2 frame씩"은 이 두 frame을 말한다). frame 23..59는 frame마다 native 상태에서 다시 시작하는 비교라 일치한다. full chain은 frame 22에서 갈라진다.
3. [F] **native는 `e7562 → 48250 → e756c → e7466`을 실행한다.** `48250`이 BYTE `10d681`(`5681(A5)`)에 1을 쓴다. 그 뒤로는 routing된 code만 실행한다.
4. [F] **소유자 없음.** `e7562`는 U06 계약이 "경계 callee(실행부 없음)"로 둔 함수이고, `48250`은 C2 범위(`4823a..48250`) 바로 다음 함수다. F4 범위·재범위 문서, B2·B2c·B2d·B2e 표, D9 결정 문서 어디에도 실행부 담당으로 올라 있지 않다. 새로 만들어야 하는 아주 작은 code다.
5. **닫힘:** block 시작 3개(`e7562` `e756c` `48250`), 범위 2개(`e7562..e7570` 14바이트, `48250..48256` 6바이트), 표·간접 분기·bank·port 없음, C 소비자 없음, 경계 callee 없음.
6. **제안:** 새 단위 **U06b**(U08b·U15b와 같은 후속 단위 꼴). scratch patch로 확인한 결과 seed 108·109의 demo 비교가 348/348 complete frame 일치, full chain 348 frame이 native 종단(frame 348 BIOS `c00444` system return)까지 이어진다(기준 346/348).

## 재현

[F] 명령(scratch worktree `wt`, 원인 탐지용 임시 계측: `am_error`가 stderr에 PC·레지스터·직전 64 dispatch PC를 찍게 함; 동작은 바꾸지 않음. 계측본은 `animation_machine.instrumented.cpp`):

```
.venv/bin/python tools/verify_animation_machine_frame_controller.py --cases 108,109 --frames 400 --workers 2 \
    --declare demo --seed-dir artifacts/stage_entry_body --out /Users/start/Workspce/ms5-scratch/demo108/run400
```

| 항목 | 108 | 109 |
| --- | --- | --- |
| frame / complete / 일치 | 349 / 348 / 346 | 349 / 348 / 346 |
| 불일치 frame | 22, 60 | 22, 60 |
| 불일치 내용(pass·step 둘 다) | `cpp-error` `unsupported animation machine PC`, preserved | 같음 |
| native 종단 | frame 348 `C:system-return`(`c00444`) | 같음 |

[F] C++ 오류 기록(계측 stderr, 20회 모두 같은 값): `pc=0e7562`, 직전 dispatch 경로 `… e77e2 2ac2 2ac6 2ab8 2abe 2ac0 e7426 4836e 48378 e742c e7430 e7440 e744a e744e e7456 e745a e7462 → e7562`. 그 밖의 오류(`c00444` `c00468`, 외부 read queue)는 검증기의 negative/fixture 검사가 일부러 만드는 것이다.

## native 근거

[F] scratch `native_n22.py`(Unicorn, frame 22·60의 N 시작 상태부터 N 끝 PC `e74`까지):

- frame 22·60 경로: `e742c e7430 e7432 e7436 e7440 e7442 e7446 e744a e744e e7452 e7456 e745a e745e e7462 e7562 e7564 e7566 48250 48254 e756c e756e e7466 e746a …`, `A6 = 100f5c`.
- `48250 MOVE.B D0,5681(A5)`가 `10d681` := `01`(frame 22 시작 값 `00`; frame 60은 이미 `01`).
- 읽기: `e744a OR.B -3355(A5),D7`이 `104cab` = `10`, `e7456`이 `104cb1` = `00`. 그래서 `D7 AND 30` ≠ 0이 되어 `e7462`가 실행된다.
- frame 21에는 `104cab` = `00`이라 `e7462`를 건너뛴다.
- N pass에서 routing 밖으로 들어간 곳은 `e7562` `e7564` `e7566` `48250` `48254` `e756c` `e756e`뿐이다(`16eaa..`·`47fe0`은 이미 routing된 block 안의 명령이다).

[I] `104cab`는 H2 `92a8..92b4`(`MOVE.B -3356(A5),D6; MOVE.B -204(A5),D7; EOR; AND; OR.B D7,-3355(A5)`)가 만드는 "새로 눌림" bit다. 이 선언에서 하드웨어 port(`300000` `340000` `380000`)는 모두 `ff`(입력 없음)이므로, bit 4는 demo 입력(`104cd4` = 1)에서 온다. D9 결정 문서 결정 4("seed의 replay 포인터가 0이라 replay 입력이 ROM 벡터 영역이다")와 맞는다. 그러므로 frame 22·60의 `e7562` 도달은 선언 (i) demo 구성에서 생긴 값 때문이다. 자연 상태에서 실제 버튼을 누를 때와 같은 경로인지는 [U]다.

## 정적 디코드

[F] 바이트(file offset = CPU 주소):

| 범위 | 바이트 | SHA256 |
| --- | --- | --- |
| `e7562..e7570` | `2f08 7001 4eb9 0004 8250 205f 4e75` | `dde6af8e405d225c4247e4e1bb9a53a8186875bb320e211e04da9602c34443c0` |
| `48250..48256` | `1b40 5681 4e75` | `4059f5ad05a638d48bf5c7c73732b66068f04b1ebfa55e29b4287548408b76ec` |

- `e7562`: `MOVE.L A0,-(A7); MOVEQ #1,D0; JSR 48250.L` → 복귀 `e756c`
- `e756c`: `MOVEA.L (A7)+,A0; RTS`
- `48250`: `MOVE.B D0,5681(A5); RTS`

[F] 진입 종류:
- `e7562`: U06 callback `e7426` 본문의 `BSR.W` 3곳(`e7462`: 입력 bit `30`; `e7478`: BYTE `7db6(A5)` = 1; `e7486`: BYTE `7db7(A5)` = 1). script 끝 항목 `e774e`(`ffff fe10`: 지속 `ffff`, 처리기 `e7752 + sext(fe10)` = `e7562`)도 `e74ac JSR (A0,D0.W)`로 들어온다. 설치 callback, `28ae` 자식, interpreter callback 표, PC 상대 점프 표 진입은 아니다.
- `48250`: 절대 `JSR 48250.L` 6곳: `965a`(메뉴 `9602`), `308c0`, `d64b2`, `d6b3c`, `d6c98`, `e7566`. 앞의 다섯 호출자는 모두 routing 밖이다. 그래서 이 단위가 처음 실행하는 공용 leaf다(B2c 결정 3, B2e 결정 3 `44602`·`e89da` 관례).
- [F] `48250`의 의미는 비-machine 계층에 이미 복원되어 있다(`engine/src/stage_state.cpp` `SelectStageArea`: `ram[d681]` := 입력 하위 byte, `docs/analysis/stage-catalog.md`). machine 실행부는 아직 없다.

[F] carry·flag: 소비자가 없다. `48250`의 `MOVE.B`는 native에서 C를 지우지만, 호출자 `e7466`(`TST.B`)과 `e74b0`(`MOVE.L`)이 곧 flag를 다시 정한다. U01/U05 관례("`MOVE.x`는 소비자가 있을 때만 known 생산")대로 known 생산으로 두지 않는다. `e756c`(`MOVEA.L (A7)+,A0; RTS`)는 U06 `e74d6`·`e755e`처럼 C 보존 목록에 넣는다. 결과는 같다.

[F] stack: `e7562`의 `MOVE.L A0,-(A7)`와 `JSR` 복귀 LONG, `e756c`의 pop과 `RTS`. 홀수 A7이나 work RAM 밖 접근은 기존 checked 오류다.

## 소유 판정

- [F] U06 계약 §요약·결정 3: `e7562`는 "경계 callee(실행부 없음)"이고, U06 routing은 `e7546..e7562`에서 끝난다. U06 범위 밖 이웃 표에도 `e7562..e7570`(경계 `e7562`)이 따로 적혀 있다.
- [F] C2 계약: routing `4823a..48250`(배타 끝)이고 `48250`은 범위 밖이다.
- [F] `e7562`·`48250`·`e756c`는 F4 범위(`animation-machine-object-callbacks-f4-scope.md`)의 단위 행, 재범위 문서, B2/B2c/B2d/B2e 계약, D9 결정 문서 어디에도 담당 단위로 올라 있지 않다. F4 범위 문서 U06 행의 개략 범위 `e73f8..e7944`는 이 함수를 지나지만, U06 계약은 이를 경계로 뺐다.
- 판정: 이미 있는 실행부 안의 "시작 누락"이나 "두 번째 진입"이 아니다. U06 범위 바로 옆의 **실행부 없는 경계 함수 1개 + 공용 leaf 1개**다.

## 닫힘 크기(프로젝트 leader 규칙)

| 항목 | 값 |
| --- | --- |
| block 시작 | 3: `e7562` `e756c`(JSR 복귀점) `48250` |
| routing 범위 | 2: `e7562..e7570`, `48250..48256` |
| 짝수 PC / 내부 PC | 10 / 7(`e7564 e7566 e7568 e756a e756e`, `48252 48254`) |
| 표·간접·bank·port·TRAP | 없음 |
| 경계 callee | 없음(`48250`이 닫힘 안에 있음) |
| C 소비 / known 생산 | 0 / 0 |
| 쓰기 | BYTE `5681(A5)`(work RAM) 1, stack LONG |

[F] 이웃 미routing 처리기 `e74f8`(script 처리기, `JSR e7504(PC,D0.W)` 2-entry 점프 표 → `e750c` `28ae` 자식 `2b7be` / `e7534` `28ae` 자식 `e7996`)는 이 문제와 상관없다. script 디코드(scratch `script108.py`)로 보면 `e74f8` 항목은 script 시작에서 대략 frame 580·787·1001에 있다. seed 108·109는 demo에서 frame 348에 끝나므로 닿지 않는다. 기본(무선언) 400 frame에도 [I] 닿지 않는다. 담당은 [U]이며 U06b에 넣지 않는다.

## 단위 제안: U06b

- 이름: **Objects F4 U06b**(U06 경계 callee `e7562` + 공용 leaf `48250`).
- 실행부: `engine/src/animation_machine_objects_u06b.cpp`, `animation_objects_u06b_block`, 오류 문자열 `unsupported animation objects u06b PC`.
- routing: `(next.pc>=0xe7562 && next.pc<0xe7570) || (next.pc>=0x48250 && next.pc<0x48256)`(U06 줄 바로 뒤).
- C 보존 목록: `e756c`.
- 연결: Makefile `ANIMATION_MACHINE_SOURCES`, `tools/verify_animation_machine.py` SOURCES, 새 시험 target과 실행 줄.
- 대안: U06에 `e7562`/`e756c`를, C2에 `48250`을 넣는다(두 실행부와 두 시험의 범위 표가 바뀐다). 권고는 새 단위다. 기존 U06·C2 시험의 `RANGES` 표를 건드리지 않는다.

### scratch patch와 확인

[F] patch: `/Users/start/Workspce/ms5-scratch/demo108/u06b.patch`(SHA256 `3c61691a259e1d2e1241cf02b986074f97cd4b10aa8642502503ee2b5463863c`). 5 파일: Makefile, `animation_machine.cpp`, `animation_machine_internal.h`, 새 `animation_machine_objects_u06b.cpp`, `tools/verify_animation_machine.py`. 단위 시험은 들어 있지 않다.

[F] patch를 넣은 scratch worktree의 controller demo 비교(`--cases 108,109 --frames 400 --declare demo`, 출력 `fix400/`):

| 항목 | 기준(`6134dd1`) | patch 뒤 |
| --- | --- | --- |
| complete 일치(108 / 109) | 346/348 / 346/348 | 348/348 / 348/348 |
| 불일치 | 4(frame 22·60 × 2) | 0 |
| full chain | frame 22에서 갈라짐 | 348 frame 일치, frame 348 기대 실패(native system return) |
| chain 결정성 | — | 두 번 같음, digest `d9b19288…` |

[I] 전체 demo 실행(142 case)의 기준 불일치 4는 모두 이 두 seed의 것이었다(B2e 기록 `natural_mismatches` 4). 그래서 patch 뒤 demo 전체는 불일치 0이 될 것으로 본다. D1·게임 mode·IRQ·무선언 controller는 [I] 바뀌지 않는다. 새 routing은 지금까지 `unsupported animation machine PC`로 끝나던 PC만 받기 때문이고, 그 검증기들에는 `e7562`/`48250` 오류가 없었다. 구현 하위 작업에서 다시 실행해 확인한다.

### 바꿔야 하는 기존 시험

[F] scratch worktree에서 patch를 넣고 `make -j3 all test`(4분 32초)를 실행하면 실패는 **하나**다. `animation_machine_objects_u06_test` `boundaries()`(395행 `reject`): `unexpected success e742c stop ff000`. 이 함수는 fixture `e742c-clear-key1` `e7462` `script-end`를 stop 없이 실행하면 `e7562`에서 `unsupported animation machine PC`로 rollback된다고 기대한다. patch 뒤에는 `e7562 → 48250`을 지나 fixture STOP(`ff000`)까지 성공한다. 이 세 행만 scratch에서 뺀 시험 변경(`u06_test_scratch.patch`, SHA256 `0c8227f96cc61447ddb940edcc1cb0cb97b48f78ed91400111891b1bdecf5c1c`, 확인용)을 넣고 다시 `make -j3 test`를 돌리면 rc=0이다(로그 `make_t2.log`).

구현 때 바꿀 곳(삭제하지 말고 다시 겨냥한다):

| 파일 | 위치 | 지금 | 바꾸는 값 |
| --- | --- | --- | --- |
| `engine/tests/animation_machine_objects_u06_test.cpp` | `boundaries()` `names[]`/`pcs[]`의 `e742c-clear-key1`·`e7462`·`script-end`(`pcs` = `e7562`) | stop 없이 rollback 기대 | 세 행을 boundary 목록에서 뺀다. 대신 "stop 없이 실행하면 `e7562`·`48250`을 지나 STOP까지 성공하고 BYTE `10d681` = 1"을 native digest로 확인하는 행을 둔다(U06b 시험 생성기에서 함께 만든다). |
| 같은 파일 | 21행·496행 주석 "boundary (… e7562 …)" | 경계 | U06b 실행부로 고친다. |
| `engine/src/animation_machine_objects_u06.cpp` | 74·75행 주석 "e7562 … no executor" | 경계 | U06b로 고친다. |

- 그대로 통과하는 곳: U06 시험의 stop = `e7562` 행(46~59·68·172·211~216행, stop을 먼저 검사함), `rom_outside[]`의 `0xe7562`(U06 `RANGES` 밖인지만 검사), C2 시험(`48250`은 이미 work RAM 탐침 `10fe1x`로 바뀜), stage catalog 시험 799행(`48250`은 이미 `10fe24`).
- 상관없는 곳: `tools/observe_animation_machine_objects_g1.py` `BOUNDARY`(native 관측기), `tools/observe_animation_machine_pvc_banks.py` `U06_RANGES`(U06 범위 표).

### 구현 하위 작업의 검증 기준

- 새 시험 `engine/tests/animation_machine_objects_u06b_test.cpp`(run_animation_machine만): 3 block 각각 native 생성 행(`e7562`를 `e7462`·`e7478`·`e7486`·`e74ac` 진입으로, `48250`을 D0.B 0/1/ff로) × C 3종, zero-step 3 × 3 carry, 내부 짝수 PC 7개는 `unsupported animation objects u06b PC`, 범위 양끝 홀수 PC, 홀수 A7(push 실패 rollback), work RAM 탐침 rollback(`10fe00..`).
- frame 검증기 4종(D1, controller 무선언·game·demo, IRQ)을 다시 실행하고 기준과 비교한다. demo 108·109는 348/348이어야 한다.
- `make -j4 all test` 종료 코드.

## 미확인

- [U] `5681(A5)` := 1의 게임 의미. 비-machine 계층에서는 구역 선택 byte(`SelectStageArea`)다. script 객체 `e73f8`(U06 계약 [I] 연출 객체)이 입력으로 이를 1로 정하는 화면상 의미는 확인하지 않았다.
- [U] 자연 상태(선언 없이 boot부터)에서 `e7426`이 입력 bit `30`을 보는 경로. 이 문서의 도달은 선언 (i) demo 입력 때문이다.
- [U] `e74f8` 처리기와 그 자식(`2b7be` `e7996`)의 담당 단위.
- [U] H pass에서 `104caa` bit 4를 만드는 replay 읽기 위치는 직접 추적하지 않았다(H는 `16bd0` 대기에서 선언 재진입이 필요하다).
