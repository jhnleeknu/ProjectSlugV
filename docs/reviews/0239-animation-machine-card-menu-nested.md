# 카드 저장 결과 하위 메뉴 프레임과 중첩 복귀(`a698`/`a6da`)·부모 메뉴 닫기 리뷰

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

계약 `docs/analysis/animation-machine-card-menu-nested-contract.md`(SHA256 `1688616ba2f0ea744c0e37505c208bd2d9f0b8ba1ad066b21d1e65384fdbd27f`). 결과 메뉴 열림·입력(7e=1e 카운트다운)·닫기(기존 실행부), `a698` 중첩 복귀(부모 커서 callback D0=7, D0=0 효과음), `a6da` 재그리기, 부모 hook `bf2c` 80≠0→`a70a`→부모 닫기→`c2c8`→자식·부모 `2a00`.

## 메인 리뷰

1. Core 11 case를 원본과 대조했다. 결함은 없었다.
2. 원본 사실 기록: `a662`는 BYTE 4(A2)를 검사하므로 결과 메뉴는 WORD `00c0`에서 `a698`로 간다. 자연 체인의 `a6da`는 부모 프레임만 다시 그린다(`a67e`가 결과 프레임을 먼저 pop).

## 검증 결과

- Native: 정상 57·guard 5 조건, split 11605. 자연 체인 73프레임(SAVE OK, NO SAVE 각각)이며 C++ unit의 73프레임과 같다. 관측 SHA `7b40f4de2da0d11dba79fd098993b3dcc6f3a958be254d2642b456dd874c9959`, 도구 SHA `fb7524ab620f2fbc730844a92293518cdf9016e6340fedc3e38c9a7a417746c8`.
- C++ 비교(해당 단위 커밋 상태, detached worktree): 64 row, split 12293, continuous 272, 재개 12232, frame 검사 235, 음성 32, zero-step 33. 보고서 SHA `081d476cb4573d4b87136535b71afd841b4c310b568d97052d1433171783367f`(두 번 같음), 검증기 SHA `4f086c41f2d96c6a5d898a7d75c8805e9c73964d07a9daf23488c5b9e35bdafa`.
- core `97683a1582a0fa946b058c028cd9ab3b2459efd1a0965e869f9569b1f788179d`, unit `0932f6bf26a9fc9492da4686e70d9d31862250315e08070335a40827018ab320`(739 API 호출, 자연 73프레임).
- 이전 검증기의 경계 음성 이동과 전체 회귀는 0239 최종 상태의 정렬 커밋에 기록한다.

## 남은 제약

부모·자식 제거 뒤 다음 객체·장면, BIOS 카드 처리 내부, video port 화면 의미. 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다.
