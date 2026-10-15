# D1 frame 구동기 리뷰

기준 커밋 `ae9e9fc`, 작업 브랜치 `claude/projectslugv-work-cycle-yout6u`, Claude 클라우드 세션(Linux, clang++, Python 3.13, Unicorn 2.1.4). ROM(`mslug5.zip` 13개 파일의 크기·CRC32·SHA1 일치)과 추출 데이터(프로그램 이미지 SHA256 `29112a94…` 일치)는 사용자가 제공했고 Git에 넣지 않았다.

## 역할
메인 Claude Opus 5.5가 다음을 맡았다.
- 단위 선정(F5 D1)
- 계약 확정: API, 선언 해제, card resume 방식, 플랫폼 rebase 판단
- diff 리뷰와 통합

작업자는 Agent 도구 서브에이전트이며, effort는 도구 기본값이다.

| 작업자 | 담당 |
| --- | --- |
| Sonnet | 구동기 구현·단위 시험, card resume 추가, 리뷰 반영 |
| Opus | 원본 산출물 연쇄 재생성 시도 |
| Opus | 원본 비교 검증기·하네스 작성 |
| Opus(별도) | 읽기 전용 독립 리뷰 |

## 경과와 판단
1. **역사 연쇄 재생성 불가.** 역사 native 산출물 연쇄(`stage_entry_body` → scheduler → rng → frame_head)는 Linux에서 바이트 재현이 불가능했다.
   - 원인: 보고서마다 Unicorn 라이브러리 경로와 SHA를 기록하는데, macOS `libunicorn.2.dylib`와 Linux `.so`가 다르다.
   - 판단: 역사 pin과 도구는 고치지 않았다. `d94a832`로 다시 만든 `stage_entry_body`(SHA `f74048bb…`)를 검증기 안에서만 선언 rebase로 사용한다.
   - 동등성 근거는 역사 집계 22개 일치뿐이다. 바이트 동등성은 [U]다.
2. **card resume 누락.** 첫 비교에서 54,270 frame이 일치했지만, 자연 130 seed가 BIOS card resume(F4부터 내려온 선언 단계)에서 멈췄다.
   - 핵심 실행부 `animation_machine.cpp/.h`는 다른 도구의 SHA pin 대상이라 수정하지 않았다.
   - 대신 구동기가 실패한 호출을 stop `c00468`로 다시 실행하는 선언 resume을 넣었다(`AnimationFrameOptions`). 독립 리뷰가 결정성 논거를 확인했다.
3. **독립 리뷰 지적 반영.**
   - 대기 상한을 64에서 원본과 같은 16으로 낮췄다.
   - N 종료 시 LONG `(100820)`=stop을 다시 확인한다.
   - H·N 종료에 A5=`108000`, A0=대상 확인을 추가했다.
   - 검증기: 원본 stop 종류와 C++ 오류 문구를 짝지었다. 부정 검사의 색인 오류를 막았다. 연쇄 seed 수를 400 frame 완주 136과 원본 정지 1로 나눠 표기했다. `--out` 옵션을 추가했다.
   - 더 엄격한 controller LONG 불변 확인은 유지했다. 위반해도 checked error일 뿐이다.

## 검증
- C++ 단위 시험 `animation_machine_frame_test` 58 checks. 리뷰 반영으로 추가한 경계 확인은 ROM 없는 fixture로 도달할 수 없어 실패 경로가 단위 시험에 없다. 원본 비교 전체 실행으로 회귀만 확인했다.
- 원본 비교 전체 결과(최종 코드 기준)는 아래 "최종 실행"에 적는다.
- 전체 `make test` 종료 0(구동기 첫 커밋 기준), Python 273개 통과.
  - 경고 10개는 모두 기존 파일(card_menu, cleanup, n09, scene)의 `-Wmisleading-indentation`이다. Linux clang 버전 차이로 나타난 것으로 보이며[I], 이번 변경 파일에는 경고가 없다.

## 남은 제약
- controller 본체, IRQ·BIOS는 실행하지 않는다.
- 외부 입력과 raster는 선언 값이다.
- 화면·사운드 동등성은 비교하지 않았다.
- 역사 macOS 실행과의 바이트 동등성은 [U]다.
- 검증기의 mode 2(H만 실행)는 하네스가 해제 규칙을 다시 적은 위치 확인용이라, 구동기 자체 검증은 아니다.

## 최종 실행
최종 코드(리뷰 반영 후 구동기와 검증기)로 `.venv/bin/python tools/verify_animation_machine_frame_driver.py --workers 4`를 실행했다. 256초, 종료 0, 보고서 SHA256 `76873c60983d4e842338b25153903f982be280bd187d62d1d435d91bf78d8836`(로컬 `artifacts/animation_machine_frame_driver/verification.json`).
- frame별 비교: 54,406 frame 중 정상 D1 frame 54,400개가 일치했고 불일치는 0이다. card frame 130개를 포함한다.
- 기대된 checked error 6개는 모두 상태를 보존했고, 원본 stop 종류와 오류 문구가 짝을 이룬다.
- C++ 단독 연쇄: 400 frame 완주 136 seed, 원본 정지 1 seed이며 어긋난 seed는 없다.
- 결정성, 부정 검사, 역사 집계 22개가 모두 통과했다.
