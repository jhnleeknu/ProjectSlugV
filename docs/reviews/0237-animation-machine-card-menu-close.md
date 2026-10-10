# 카드 메뉴 닫기(`a662`/`a2be`/`9e94`)와 카드 자식·부모 종료(`c2c8`→`2a00`) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 작성·보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: C++ core·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측.
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. 해당 단위 커밋에 고정된 별도 detached worktree에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: 0236~0239는 각 단위 커밋 상태에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 0239까지 적용한 최종 상태에서 한 번에 수행했고, 그 결과는 정렬 커밋(별도)에 기록한다. 따라서 중간 커밋 각각에서 전체 회귀를 재실행하지는 않았다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-card-menu-close-contract.md`(SHA256 `925c44c1fb66b9489be24073f598b83132d02936a5f0ab46e417fcb145274c38`). `a662` 닫기 프레임, `a2be` 높이 축소(6(A2)<<6)와 행 지우기(`a018` known C 소비 `a324`), `9e94`, `a67e` stack pop, `c2c8` 페이드·7e=14 타이머, `c2e8`의 부모 62=ff와 `2a00` 자식 제거, 부모 재진입 `480ac`→`2a00`.

## 메인 리뷰

1. 메인의 계약 오류를 core 작업자가 원본으로 찾았다. 감소량은 c(A2)가 아니라 6(A2)(항목 수)<<6이다. `c188`에서는 `0600`→…→`0000`, 6프레임이다. 메인이 원본(`a2be` `7000 102a0006 ed48`)으로 확인해 계약을 보정했다(SHA 갱신, 실행 중인 관측 작업자에게 재pin 전달).
2. Core 31 case를 원본과 대조했다. 결함은 없었다. `a2d0` borrow, `9e94` port 배치(위치<<16|00ff, ADDI.L #200000), `a67e` LONG RMW를 확인했다.
3. `a344`(ADDQ.W #2,A7; RTS)는 실제 68000에서 C를 보존하지만 기존 source 분류(FLOW_ONLY에 addq 없음)와 일치시키기 위해 메인이 carry 보존 목록에서 빼 Unknown으로 두었다(ADDA/SUBA 규약과 같음).
4. 사실 기록: `2a00` cleanup의 원본 TRAP #15 회피에는 선언 fixture(`1d`=0, `6c`=ff, `104ca4`)가 필요하다. pool slot이 초기화되지 않은 값이기 때문이며, fade_card cleanup fixture 규약과 같다.

## 검증 결과

- Native: 정상 71·guard 11 조건, 27단계 닫기 체인(높이 `0600`→`0000` 6프레임, 높이 0 프레임, 타이머 18프레임, 자식·부모 `2a00`). 관측 SHA `b5bd2164ab5badd5067b469d9d6c7d79b3cedeae2efca07d89ff18d4882a39dd`, 도구 SHA `f38219e8734f45e1dc0389e222c64bb005b3d7493f5ecee29a006108fa554de8`.
- C++ 비교(해당 단위 커밋 상태, detached worktree): 82조건, split 7886, control 246, 음성 98(guard 11 포함), zero-step 93, carry 탐침 14102. 보고서 SHA `8f4255c509d063f46a6f26829556b5cbcb253aa86fe9bb6badc4834e3d157da9`(두 번 같음), 검증기 SHA `01869cb82d23c9d91f9515207c3f4d727b7043c240d5826ee291c40e7a847974`. 검증기는 기존 cleanup core의 CMP.W known carry(`2886`/`2a12`)를 native 분기 경로로 대조하는 규칙을 추가했다.
- core `edb2f0ac3ad300f877eb800235781d2cb9f99717271a48a690bf11d37d8b9dad`(a344 carry 목록 제외는 `engine/src/animation_machine.cpp`에서 메인 수정), unit 911 API 호출.
- 이전 검증기의 경계 음성 이동과 전체 회귀는 0239 최종 상태의 정렬 커밋에 기록한다.

## 남은 제약

`a698` 중첩 복귀(0239), `bd26`(0238), 부모·자식 제거 뒤 다음 장면, video port 화면 의미. 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다.
