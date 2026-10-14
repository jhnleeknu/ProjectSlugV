# D1 frame 구동기 (H → 선언 controller 생략 → N)

기준: F5 범위 문서 `animation-machine-frame-head-f5-scope.md`의 결정 D1(선택 A). 구현 `engine/include/ms5/animation_machine_frame.h`, `engine/src/animation_machine_frame.cpp`. 원본 비교 `tools/verify_animation_machine_frame_driver.py` + `engine/tools/frame_driver_acceptance.cpp`.

표기: [F] 원본 실행 비교로 확인한 사실, [I] 추론, [U] 미확인.

## API
- `run_animation_machine_pass`: seed에서 시작하는 frame 0용 N pass다.
  - 시작 조건: PC `2ac2`, A6 `1008e4`, A7 `1ff000`.
  - stop: 시작 시의 LONG `(100820)`. `e4a` 또는 `e74`만 허용한다.
  - 종료 조건: PC=stop, A6 `100820`, A7 `1feffc`, LONG `(1feffc)`=`2ac2`.
- `step_animation_machine_frame`: 한 frame을 세 구간으로 실행한다.
  1. H: frame head를 PC=LONG `(100820)`부터 controller 진입 PC=LONG `(1008e4)`까지 실행한다. 종료 시 A6 `1008e4`, A7 `1feffc`, 복귀 LONG `2ac2`를 확인하고, controller LONG이 바뀌지 않았는지도 확인한다.
  2. 선언 controller 생략: PC:=`2ac2`, A7+=4, C Unknown.
  3. N: `run_animation_machine_pass`와 같은 pass를 실행한다.
- 모든 구간은 C Unknown으로 시작한다. 실패하면 RAM·상태·device(PVC, bank, 외부 읽기 queue)·result를 전혀 바꾸지 않는다.
- 선언 해제(`AnimationFrameWait`로 순서대로 기록하고, 구간마다 최대 64회):

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
  - 원본에서 frame이 완료되지 않는 6개(guard-release seed 5개의 frame 0 `fetch-unmapped`, case 141 frame 0 `odd-pc` `47c05`)는 C++가 상태를 보존하는 checked error로 끝났다.
- **[F] C++ 단독 연쇄:** C++ 출력만 다음 frame으로 넘겨, 자연 seed 137개 모두 마지막 frame까지 원본과 일치했다. 54,400 frame이고 어긋난 frame은 없다. 같은 연쇄를 두 번 실행해도 결과가 같았다.
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
- 재현 명령: `.venv/bin/python tools/verify_animation_machine_frame_driver.py --workers 4`. 4코어에서 약 4분 24초 걸렸고, 보고서는 `artifacts/animation_machine_frame_driver/verification.json`(로컬, SHA256 `f96ce9b2…`)이다.

## 남은 것
- controller D9/C1~C3를 실행해 선언 생략을 없애야 한다.
- IRQ `c8c`(F6)·BIOS·실제 입력·raster 값은 아직 선언 값이다.
- 화면·사운드 출력 동등성은 비교하지 않았다. 이번 비교는 port 순서까지만이다.
- b-unit·고아 사슬은 남아 있다.
