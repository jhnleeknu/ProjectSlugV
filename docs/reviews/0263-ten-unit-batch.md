# 10개 주 작업 단위 묶음 리뷰 (2026-10-15)

기준 `cc88bde`(PR #1 병합) 이후 작업 브랜치 `claude/projectslugv-work-cycle-yout6u`. Linux 클라우드 세션(clang++, Python 3.13, Unicorn 2.1.4), 사용자 제공 ROM(13개 파일 해시 일치, 프로그램 이미지 `29112a94…`). ROM·추출 데이터·artifacts는 Git에 넣지 않았다.

## 역할
- 메인(Claude Opus 5.5): 단위 선정, 계약 검토와 결정 기록, 작업자 배정, 병합·충돌 해결, 병합 후 회귀, 문서.
- 계약 분석(Opus 3개): C1~C3·D9, IRQ F6, b-unit·고아 사슬. 결정은 각 계약 문서 끝 "메인 결정"에 남겼다.
- 구현(Sonnet high 또는 Opus): 작업자별 git worktree·브랜치에서 진행했고, 메인이 `--no-ff`로 병합했다.

## 단위와 결과

| # | 단위 | 내용 | 원본 비교 |
| --- | --- | --- | --- |
| 1 | M1 | 정적 코드 커버리지 기준선 `tools/measure_code_coverage.py`, `docs/analysis/code-coverage-baseline.md` | 결정적 재실행 |
| 2 | V1 | 단위 공용 native fixture 검증기 `tools/verify_animation_machine_unit_fixtures.py` + 하네스 | selftest 40/40 |
| 3 | C1 | controller gate·꼬리·helper 116 block | fixture 1,748/1,748, SBCD 512 입력 |
| 4 | C2 | 전환·해체·게임 mode + `b300` 메뉴 자식 164 block | fixture 1,607/1,607. (ii) 게임 모드 Execute에서 137 seed × 400 frame, 54,400/54,400 일치 |
| 5 | C3 | C3a 9 + C3b 38 block | C3a는 D9 검증에 포함. C3b fixture 457/457 |
| 6 | D9 | frame 구동기 controller `Execute` 모드, 기본은 `Skip` | (iii) 기록 상태 54,400/54,400. Skip은 D1 54,400/54,400 유지 |
| 7 | F6a | vblank IRQ shell 193 block + clear-run 진입점 381 | fixture 320/320 |
| 8 | F6b·F6c·F6-D | 팔레트 전송 522, IRQ writer 1,240 + Duff 256, 구동기 실제 IRQ 실행 | F6b 726/726, F6c 1,538/1,538. IRQ 모드 54,400/54,400, IRQ 108,528회 |
| 9 | B1 | b-unit: B1a 215, B1b 207, B1c 224 | 2,807 / 1,892 / 1,840 모두 통과 |
| 10 | B2 | 고아 사슬·`4d418`: B2a 180, B2b 209 | 1,386 / 1,419 모두 통과 |

모든 단위의 원본 비교 기준은 native Unicorn 원본 ROM 실행이다. 여기서 "자연"은 stage_entry_body seed(선언 rebase, `0262` 참고)에서 시작한 실행을 뜻한다. host 쓰기를 쓴 fixture는 "선언"으로 구분한다.

## 메인 결정과 편차(근거는 각 문서)
- **D9:** controller 실행은 옵션이다. RTS를 건너는 Z는 BYTE (A0)를 다시 읽어 계산하고, A0가 확인된 4바이트가 아니면 checked error다. 경계 확인은 작업자 제안대로 "controller 구간에서 LONG `(100820)` 불변"으로 바꿨다. H가 첫 frame에 `e4a`를 `e74`로 바꾸기 때문이다 [F].
- **F6 E6:** 공개 헤더 `animation_machine.h`가 감사 도구에 SHA로 pin돼 있어 바꾸지 않았다. 팔레트 RAM은 새 헤더 `animation_machine_irq.h`의 확장 진입점으로 붙였다.
- **block 수 편차:**
  - B1b는 207(계약 211). 3d8de 사슬의 실제 시작점이 9개다.
  - B2a는 180(계약 181). `60690`을 두 앞 block에 접었다(N04·N09 전례).
  - N22b 153 대 154는 [U]로 남는다.
- `4c3ba`는 정적 참조가 없어 미사용으로 기록했다(routing하지 않음).
- F6c family A의 fixture는 `108d3c` bit7을 host 쓰기로 켠 "선언" fixture다.

## 병합 중 발견·수정
- 양쪽 줄을 모두 남기는 방식의 충돌 해결이 Makefile `ANIMATION_MACHINE_SOURCES`에서 소스 두 개(b1b, c3)를 빠뜨렸다. 이전에 빌드된 바이너리 때문에 시험이 통과한 것처럼 보였다.
  - 깨끗한 재빌드로 이 문제를 찾아 수정했다(`abd2c2b`).
  - 이후 병합 스크립트에 누락 소스 자동 확인을 추가하고, 병합마다 깨끗한 재빌드로 검증했다.
- 이미 병합된 단위가 routing한 PC를 다른 단위의 시험이 "미연결 탐침"으로 쓰던 곳을 work RAM PC `10fe00`으로 옮겼다.
  - F6b 시험·spec의 `8b64`(C3a가 routing)
  - 작업자들이 고친 card_menu·stage_catalog 등 시험 탐침
- 예전 검증기 `tools/verify_animation_machine.py`의 `SOURCES`를 Makefile 목록과 동기화했다.

## 검증(최종 병합 트리 `cd9be14` + 아래 수정)
- C++ animation_machine 시험 바이너리 112개(깨끗한 재빌드)와 Python 단위 시험 310개가 모두 통과했다.
- V1 단위 원본 비교(C2가 들어간 상태): C3b 480/480, C2 1,607/1,607.
- D1 구동기(case 0, 32, 116 × 120 frame): 일치했다.
- controller Execute 모드, (ii) 게임 선언(case 0, 32, 116 × 400 frame): 1,200/1,200 일치했고, C++ 단독 연쇄 3개 seed가 모두 400 frame을 완주했다.
  - 처음 실행에서 고정 fixture `controller-c560-open-c3b-boundary` 하나가 실패했다.
  - 원인: C2·C3b 병합 뒤 boot가 `JMP c00444`까지 이어져, C++와 native가 모두 system return으로 끝난다(상태 보존). 기대값이 옛 "미연결 PC" 그대로였다.
  - 기대값을 새 결과로 고쳤고 재실행에서 `fixtures_ok` true.
- 단위 작업자 단계에서 이미 수행한 전체 실행(병합 전 각 브랜치):
  - D1 54,400/54,400
  - D9 Execute (iii) 54,400/54,400
  - C2 Execute (ii) 54,400/54,400
  - F6-D IRQ 모드 54,400/54,400

## 독립 리뷰
사용자의 크레딧 제약으로 이번 묶음에는 별도 독립 리뷰 작업자를 배정하지 않았다. 대신 다음으로 대신했다.
- 메인의 diff·결정 검토
- 단위별 native 비교와 부정 검사
- 병합 후 깨끗한 회귀

독립 리뷰는 다음 세션의 남은 항목이다.

## 남은 것·미확인
- **[U] 하드웨어 값:** 실제 vblank 시점, BIOS `c0044a`·`c00444`의 실제 효과, Z80 응답·video status 실제 값.
- **IRQ 전달 지점:** 자연 실행에서 IRQ가 전달된 곳은 `ef2`뿐이다. `16bd0`·`cda4`·`3aea`·gate 전달은 자연 비교가 없다.
- **demo 모드 (i):** 전환 뒤 자식 `e66aa`가 미연결이다.
- **기록되지 않은 시험 기대값:** `tools/verify_animation_machine_frame_controller.py`의 c3b 경계 행, fade_card 검증기의 `4c3a2` guard 등 pin된 예전 검증기의 기대값은 고치지 않았다. 해당 검증기는 이 환경에서 실행할 수 없다(역사 산출물 없음).
- **다음 후보:** B2c(`3a60a..3abde`), `44602`·`4b6f4`·`4db18`·`3b5a6`, 남은 큰 사슬(`3d526`, `cc8b4`, `78776` 그룹 등). 이후는 `remaining-work-plan.md` 순서를 따른다.
