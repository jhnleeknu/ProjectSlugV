# 0265 — 10개 단위 묶음 독립 리뷰 후속과 B영역 단위(B2c-a·B2d·B2e·B3a·B3b) 작업 주기

- 대상: `e5bfb73`(origin/main, PR #2) → 작업 브랜치 `claude/next-work-cycle`.
  - 병합 커밋: `fa30f5d` `04d5c2f` `b6bc035` `52ac400` `97aaa54` `57c4f7f` `2c7e5a4` `c919eed` `6503470` `53ee58d` `de0e5be`.
  - pin 재정렬 커밋은 이 문서 뒤에 이어진다.
- 실행 환경: macOS(arm64), 원래 공유 `artifacts/`가 있는 컴퓨터. ROM SHA256 `29112a94…`은 작업 전후로 같았다.
- 역할:
  - 메인: Claude Opus 5.5. 분해·결정·리뷰·병합.
  - 작업자: Claude Opus 5.5/high는 계약·실행부, Claude Sonnet 5.5/medium·high는 검증 실행·정렬·탐침 이전.
  - 운영 방식은 주기 중에 바뀌었다. 사용자 지시로 처음에는 Opus 동시 1개로 줄였고, 이어서 단위를 Opus/Sonnet 하위 작업으로 나눠 서브에이전트를 한 번에 하나씩 실행했다.

## 1. 독립 리뷰(0264)와 후속

- 리뷰 문서는 `docs/reviews/0264-ten-unit-batch-independent-review.md`다.
- [F] 실행부가 원본과 다르게 동작하는 결함은 찾지 못했다. 발견 사항 처리는 다음과 같다.

| 항목 | 처리 | 근거 |
| --- | --- | --- |
| M-1 예전 검증기 기대값 | 대체한 단위와 이전 기대값을 행에 기록하고, work RAM 대조군을 더했다 | `0264-legacy-regression-mac.md` |
| M-2 Linux 전용 seed 경로 | `--seed-dir`/`MS5_SEED_DIR`를 추가했다. Linux 또는 역사 SHA만 허용하고, 보고서에 `seed_kind`를 기록한다 | 같은 문서, `docs/WORKFLOW.md` |
| M-3 다음 단위 ROM PC를 쓴 탐침 | 새 V1 spec 12개와 C++ 시험 16개, 예전 시험 55개 파일의 탐침 427개를 `10fe00..10fefe`로 옮겼다. 범위 끝은 정적 `!in_ranges` 검사로 남겼다 | `0264-review-followup.md` |
| L-1 실패 PC 미확인 | V1 `check_fail_pc()`를 추가했다. d9 행은 `c00444` 실패로 정정했다 | 같은 문서 |
| L-2 검증기 예외 frame | acceptance 실패로 센다 | `0264-legacy-regression-mac.md` |
| L-3 Makefile 헤더 중복 | `b6bc035`로 고쳤다. 출처는 C2 병합 `cd9be14`이고, `b6bc035` 메시지의 "B1a 병합"은 틀렸다 | 리뷰 L-3 |
| L-4 U06 fixture 삭제 | `16ea4` sprite 경계 기준으로 복원했다. native digest와 같다 | `0264-review-followup.md` |

## 2. 병합한 단위

| 단위 | block | 범위 요약 | 계약 |
| --- | --- | --- | --- |
| B2d | 220 | `39366` 상태 사슬 `391e8..395dc`, 자식 `3b044..3b118`, `2d3ae`/`2d57a` 자식 `2d3ae..2d7be` | `animation-machine-deferred-b2d-contract.md` |
| B2c-a | 218 | `82(A6)` 부상태 사슬 `3a60a..3abde`(175, B2 계약의 75는 설치·표 항목 누락), 자식 `3af86` `3ae84`, leaf `3b48c` `3b5a6` `1bf80` `1d198` | `…-b2c-contract.md` |
| B2e | 109 | B2c-b script callback `3abee` `3b458` `3b62a` `3b648` `3b656`(callback 표 `4a500` 0x23..0x27), leaf `44602` `4db18` `e89da`, demo 랭킹 자식 `e66aa` | `…-b2e-contract.md` |
| B3a | 216 | N28 범위 밖 사슬 `2ba50..2baf4` `2c0fc..2c760`, helper `2b532..2b668`, leaf `8d34..8da2` | `…-b3a-contract.md` |
| B3b | 206 | `2baf4..2c0fc` `2c96a..2ca68`. `2bd58` BMI는 앞 block 둘이라 각 앞 block으로 접었다(N04 `ab1a6` 선례) | `…-b3b-contract.md` |

- 합계 969 block이다.
- [F] 단위마다 다음 검증을 통과했다.
  - 단위 시험(`run_animation_machine`만 사용)
  - UBSan
  - 변이 시험(모두 검출. 살아남은 것은 동등 변이로 증명)
  - 실제 ROM 차분(8개 `program_rom_*.ms5d`, 단위마다 7,500건, 불일치 0)
  - V1 native fixture
  - D1·controller(`--declare game`)·IRQ frame 비교
- [F] B2e로 demo 모드 frame 일치가 31,128/45,684에서 45,680/45,684로 늘었다. 135 seed가 원본과 같은 BIOS system return으로 끝난다.

## 3. 최종 병합 트리 회귀(`de0e5be`, `MS5_SEED_DIR=artifacts/stage_entry_body`, seed_kind historic)

| 검사 | 결과 |
| --- | --- |
| `make -j4 all test` | 종료 0, 경고 0, Assert 없음 |
| D1 frame 구동기 | 54,400/54,400 일치, 불일치 0, deterministic·negative_ok. 보고서 SHA `66278618…` |
| controller Execute `--declare game` | 54,400/54,400, fixtures_ok. 보고서 `27ad731a…` |
| IRQ | 54,400 frame 완료, IRQ 108,528회, guard 불일치 0. 보고서 `63672385…` |
| V1 spec 18개 | 모두 통과. b1a 2,807, b1b 1,892, b1c 1,842, b2a 1,386, b2b 1,419, b2c 1,707, b2d 1,489, b2e 1,054, b3a 1,468, b3b 1,360, c1 1,741, c2 1,607, c3b 480, d9 26, f6a 320, f6b 726, f6c 1,538, selftest 40 |

- 출력 위치는 `build/final_regression/`이며 Git에서 제외된다.
- [F] 표준 회귀 35개도 `de0e5be`에서 모두 통과했다. stage_event·stage_event_ops의 `animation_machine.cpp`/`internal.h` pin만 `aba5bec0…`/`706f6a5b…`로 갱신했다(`0264-legacy-regression-mac.md` 추가 절). 병합 후 `751bd47`에서 `make -j4 all test` 종료 0, Python 310개 OK.

## 4. 병합 중 발견한 문제

- [F] 병합 해결 스크립트는 충돌 줄을 합집합으로 남긴다. 그래서 Makefile의 한 줄짜리 `ANIMATION_MACHINE_SOURCES`·`_HEADERS`가 두 벌 남았다(B2e·B3a 병합 시).
  - 도구들은 첫 SOURCES 줄을 읽으므로 새 단위가 링크 목록에서 빠질 수 있었다.
  - `57c4f7f`와 B3a 병합에서 바로잡았다. 이후 병합마다 두 줄인지 확인한다.
- [F] 이 컴퓨터에는 `artifacts/linux_rebase`가 없다. frame 검증은 역사 seed(`1f65100f…`)로 수행했다.

## 5. 남은 것·미확인

- [U] legacy 정렬의 일부 [I]/[U] 귀속은 아직 추적하지 않았다.
  - `buffer_cue` `e8a1c` `4b82e`
  - `frame_helpers` `47672` `2efdc` `493bc`, 자연 480bc stop
  - 위 경우가 "external read queue empty"로 끝나게 된 routing 경로가 미추적이다.
- [U] demo seed 108·109는 frame 22(demo 전환 전)에서 C++ `unsupported animation machine PC`로 2 frame씩 불일치한다. `04d5c2f`에도 같은 결과가 있어 B2e 이전부터 있던 문제다.
- 다음 B 후보:
  - B3c 약 71 block(자식 `2d7be` `2d916` `2db06`, callee `1c114`)
  - 미사용 후보 `3b4e0` `4c3ba` 판정 기록
  - `4b6f4`(B2 결정 4)
- `docs/reviews/0258-regression-manifest.json`은 갱신하지 않았다.
- 하드웨어 실제 값, 자연 scheduler·IRQ timing, BIOS 실행은 주장하지 않는다. 전체 Goal 범위·완료 기준은 바꾸지 않았다.
