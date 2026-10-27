# D1 frame 구동기 (H → 선언 controller 생략 → N)

기준: F5 범위 문서 `animation-machine-frame-head-f5-scope.md`의 결정 D1(선택 A). 구현 `engine/include/ms5/animation_machine_frame.h`, `engine/src/animation_machine_frame.cpp`. 원본 비교 `tools/verify_animation_machine_frame_driver.py` + `engine/tools/frame_driver_acceptance.cpp`.

표기: [F] 원본 실행 비교로 확인한 사실, [I] 추론, [U] 미확인.

## API
- `run_animation_machine_pass`: seed에서 시작하는 frame 0용 N pass다.
  - 시작 조건: PC `2ac2`, A6 `1008e4`, A7 `1ff000`.
  - stop: 시작 시의 LONG `(100820)`. `e4a` 또는 `e74`만 허용한다.
  - 종료 조건: PC=stop, LONG `(100820)`=stop, A6 `100820`, A5 `108000`, A0=stop, A7 `1feffc`, LONG `(1feffc)`=`2ac2`.
- `step_animation_machine_frame`: 한 frame을 세 구간으로 실행한다.
  1. H: frame head를 PC=LONG `(100820)`부터 controller 진입 PC=LONG `(1008e4)`까지 실행한다. 종료 시 A6 `1008e4`, A5 `108000`, A0=controller, A7 `1feffc`, 복귀 LONG `2ac2`를 확인하고, controller LONG이 바뀌지 않았는지도 확인한다.
  2. 선언 controller 생략: PC:=`2ac2`, A7+=4, C Unknown.
  3. N: `run_animation_machine_pass`와 같은 pass를 실행한다.
- 모든 구간은 C Unknown으로 시작하고, 완료된 pass·frame은 C Unknown을 보고한다(아래 "개정: frame 끝 carry"). 실패하면 RAM·상태·device(PVC, bank, 외부 읽기 queue)·result를 전혀 바꾸지 않는다.
- 선언 해제(`AnimationFrameWait`로 순서대로 기록하고, 구간마다 최대 16회, 원본 `S.WAIT_LIMIT`와 같음):

  | PC | 해제 동작 | 의미 |
  | --- | --- | --- |
  | `ef2` | BYTE (A5−7fea) := BYTE (A5−7fe9) | vblank, D2 |
  | `16bd0` | WORD (A5+d34) := D0.W | sprite flush, D5 |
  | `3aea` | WORD `104d74` := ffff | sound ring, D6 |
  | `cda4` | WORD `108d34` := D4.W | sprite queue |
  | `47af0`/`478de` | WORD `107dea`=0일 때만 BYTE `107ded` &= 7f | gate |

  그 밖의 대기 PC는 checked error다.
- BIOS card 요청(`c376 JSR c00468`)은 `AnimationFrameOptions.card_resume`일 때만 선언 resume으로 처리한다.
  - 동작: PC:=`c37c`, A7+=4, BYTE `10fdc6`:=answer(기본 0x80), C Unknown. F4의 선언과 같다.
  - 구현 방식: 핵심 실행부(`animation_machine.cpp/.h`)는 다른 도구가 SHA로 pin하므로 바꾸지 않았다. 대신 실패한 호출을 같은 입력에서 stop `c00468`으로 다시 실행한다.
  - 정당성[I]: 실행은 결정적이고, 첫 실행은 원래 stop에 닿기 전에 실패했다. 따라서 재실행은 `c00468`에 먼저 닿거나 같은 지점에서 실패한다. 그 밖의 경우에는 원래 오류를 돌려준다.
- 실행하지 않는 것: controller 본체(`c52a`/`c66a`), BIOS 본체, IRQ `c8c`, 자연 scheduler. 이 API는 C1~C3·F6의 대체물이 아니다.

## 원본 비교 (2026-10-14, Linux, Unicorn 2.1.4)
- **원본 기준:** frame-head 관측기의 `HeadRun`(D1 protocol, continuous, 기본 입력 raster 0·입력 ff, card answer 0x80)을 저장소 도구 그대로 in-process로 실행했다.
- **선언 플랫폼 rebase:** seed는 Linux에서 다시 만든 `stage_entry_body` 관측(SHA256 `f74048bb…`, `d94a832`의 `observe_stage_entry_body.py`)이다.
  - 역사 pin `1f65100f…`과 다른 것은 보고서에 Unicorn 라이브러리 경로·SHA가 들어가기 때문으로 보인다[I].
  - 역사 pin과 도구 파일은 바꾸지 않았다. 검증기 안에서만 seed 경로와 SHA를 교체했고, 이 사실을 보고서에 기록했다.
- **[F] frame별 비교:** 각 frame을 원본 시작 상태에서 시작해 비교했다.
  - 대상: 142 seed × 최대 400 frame = 54,406 frame. 정상 D1 frame 54,400개가 모두 일치했고 불일치는 0이다.
  - 비교 항목: RAM 64KiB, 레지스터 16개·PC, PVC bank·page, 구간별 순서 있는 ports, 대기 해제 기록, 외부 읽기 수, head/controller/stop PC.
  - card frame 130개도 일치한다.
  - 원본에서 frame이 완료되지 않는 6개(guard-release seed 5개의 frame 0 `fetch-unmapped`, case 141 frame 0 `odd-pc` `47c05`)는 C++가 상태를 보존하는 checked error로 끝났고, 오류 문구가 원본 stop 종류와 짝을 이룬다(`fetch-unmapped` ↔ `animation fade card odd JSR target`, `odd-pc` ↔ `unaligned animation machine PC`).
- **[F] C++ 단독 연쇄:** C++ 출력만 다음 frame으로 넘겨, 자연 seed 136개가 400 frame을 완주하며 원본과 일치했고, case 141은 원본과 같은 frame 0 정지에서 checked error로 끝났다. 일치한 frame은 54,400개이고 어긋난 frame은 없다. 같은 연쇄를 두 번 실행해도 결과가 같았다.
- **[F] 역사 기록 대조:** 관측 문서의 역사 집계 22개가 모두 같다.
  - 자연 137 seed 중 136개가 400 frame을 완주했다.
  - H 54,264개가 모두 `c52a`에서 멈췄다.
  - `16bd0` 대기는 100 seed에서 합계 8,100회였다.
  - card resume은 130 seed에서 각 1회였다.
  - leader 577개를 덮었다.
  - 역사 seed RAM과의 바이트 동등성은 비교 자료가 없어 [U]다.
- **부정 검사:** 아래 변형을 모두 검출했다.
  - RAM 1바이트 변경
  - 입력 queue 순서·값·개수 변경
  - head PC 오류
  - card answer 오류
  - card_resume 끔
  - 결과 위조(RAM·레지스터·port·대기·읽기 수·carry)
- **비교 어댑터:** C++ `MOVE.L` `3c0000` 1건을 원본의 WORD 2건으로 나누는 변환을 썼다. 원본 node `4fcce`/`4fcda`의 port 구간 안에서만 적용한다(F4 검증기와 같은 규약).
- **외부 읽기 queue:** 원본 H가 실제 소비한 값과 순서를 그대로 C++에 공급했고, C++가 queue를 남김없이 소비했는지 확인했다.
- 재현 명령: `.venv/bin/python tools/verify_animation_machine_frame_driver.py --workers 4`. 4코어에서 약 4분 16초 걸렸고, 보고서는 `artifacts/animation_machine_frame_driver/verification.json`(로컬, SHA256 `76873c60…`, 최종 코드 기준)이다.

## 개정: frame 끝 carry (P2 carry, 2026-10-27)

- **옛 동작(`eeae7b0`).** pass는 마지막 node callback이 남긴 C를 그대로 보고했다. dispatcher block `2ac2`(`MOVEA.L 8(A6),A6`), `2ac6`(`BRA`), `2ab8`(`LEA`), `2abe`(`MOVEA.L (A6),A0`), `2ac0`(`JSR (A0)`)는 68000에서 CCR을 바꾸지 않으므로 C 보존이고, pass는 dispatcher가 head callback에 들어가는 `e4a`/`e74`에서 멈추기 때문이다.
- **원인 [F].** 셋째 IO 관측(io-ext2)의 D1 frame 295와 D2 frame 481에서 pass의 마지막 node는 P2 플레이어의 자식(A6 `101640` / `1010e4`)이고, 그 callback은 U18 `ea908` → `ea940` 상태다. segment 탐침(scratch `p2c/probe/carryprobe.py`, N 시작에서 block마다 stop PC 하나)의 C: `ea9ea` Unknown(U18 계약: 소비자 없는 `ANDI.B #fe,CCR`), `ea9f8` Unknown, `ea9fe` Clear(`ea9f8 JSR 49fc6`이 interpreter의 known C를 돌려줌), pass 끝 `e74` Clear. IO 검증기는 frame 끝 carry Unknown을 요구하므로(`animation-machine-io-execution.md` 3.1) D1 295~297, D2 481~483이 carry 불일치였고 연쇄는 첫 불일치에서 멈췄다.
- **실행부 분류는 맞다 [F].** `49fc6`의 known C는 실제 소비자가 쓴다(예: FR3 `ea8f6 JSR 49fc6` 뒤 `ea8fc`). `ea9f8`(JSR)·`ea9fe`(RTS)는 U18 계약에서 FLOW_ONLY이고 68000에서도 CCR을 보존한다. 다른 callback도 `49fc6`의 C를 dispatcher로 돌려준다(예: N28의 `PC := 49fc6` 꼬리). 따라서 결함은 특정 실행부가 아니라 frame 경계의 carry 규약에 있다.
- **새 동작.** `animation_machine_frame.cpp`의 `run_nodes`(`run_animation_machine_pass`·`step_animation_machine_frame` 공용)가 pass 경계 검사 뒤 C를 Unknown으로 둔다. 공개 header에 주석 한 줄을 더했다. `animation_machine.cpp`·`animation_machine_internal.h`는 바뀌지 않아 `CPP_PINS` 갱신은 없다. segment API(`run_animation_frame_segment`)의 stop 결과 carry는 그대로다.
- **native 의미와의 대응.** D1은 이미 모든 구간이 C Unknown으로 시작한다고 선언하므로 C++는 frame 끝 C를 소비하지 않는다. [F] native에서도 `e74`의 첫 명령은 `MOVE.W #0,3c0004`(MOVE는 C를 지운다)이고 H1 계약에 carry 소비자가 없으므로 frame 끝 C는 죽은 값이다. 소비자 없는 C를 Unknown으로 두는 것은 U18 `ea9ea`와 같은 규칙이다. [I] native `e74`의 실제 C는 검증된 interpreter 모델로 보아 Clear이다(관측은 SR을 기록하지 않는다).
- **선택하지 않은 안 [I].** (a) U18의 `ea9fe`나 `ea9f8`을 Unknown 생산으로 바꾸는 안: 68000 의미와 어긋나고, `49fc6`의 C를 돌려주는 다른 callback이 마지막 node가 되면 같은 불일치가 다시 난다. (b) IO 검증기의 carry 검사를 바꾸는 안: 금지 범위다. 검증기는 바꾸지 않았고 부정 검사 `result-carry`(위조 carry 1)는 그대로 검출된다.
- **시험(옛 → 새).** `engine/tests/animation_machine_frame_test.cpp`: `manual_pass`(harness식 수동 연쇄)가 N 구간 뒤 같은 선언 경계(C Unknown)를 적용한다(옛: 마지막 block의 C 그대로). 새 row는 node 7(`100d7c`) callback `2908`(`ORI #1,CCR`; `290c RTS` = Set)과 `290e`(`ANDI #fe,CCR`; `2916 RTS` = Clear)이다. 수동 `run_animation_machine`은 `e74`에 Set/Clear로 닿고, pass와 frame은 Unknown을 보고한다(옛 동작이면 Set/Clear). 새 줄을 지운 돌연변이는 새 row의 `same_as_manual`에서 실패한다. 시험 97 checks.
- **검증 [F].** `make -j6 all test` 종료 0, 경고 0. IO 전체 실행: historic 173,966 / 173,966 일치(변화 없음, acceptance 모두 true), io-ext 14,500 / 14,500(변화 없음), io-ext2 6,664 / 18,718 일치(옛 5,707, +957), 불일치 0(옛 2), C++ 오류 11(M1.5 `cue wrapper failure requires known caller X`, 별개의 알려진 한계), acceptance는 `no_unexpected_cpp_errors`만 false. io-ext2 첫 정지: D1 1,180(guard, `animation frame controller system return`), D2 553(routing 밖 `c13c0`), 나머지 run은 옛 값과 같다. V1 regression specs 20개(fr3, pc1~pc11, se1, se2, fr9~fr14; `MS5_SEED_DIR=artifacts/stage_entry_body`)는 frame 구동기를 거치지 않으며 fixtures 35,952개 모두 ok, failed 0이다.

## 남은 것
- controller D9/C1~C3를 실행해 선언 생략을 없애야 한다.
- IRQ `c8c`(F6)·BIOS·실제 입력·raster 값은 아직 선언 값이다.
- 화면·사운드 출력 동등성은 비교하지 않았다. 이번 비교는 port 순서까지만이다.
- b-unit·고아 사슬은 남아 있다.
