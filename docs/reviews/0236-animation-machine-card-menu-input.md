# 카드 메뉴 입력 프레임(`a406`)·자동 선택 타이머 hook(`bf2c`)·선택·닫기 시작 리뷰

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

계약 `docs/analysis/animation-machine-card-menu-input-contract.md`(SHA256 `78fe3d1a0c855e1e491d60c66afca710077585edaf8516076bb89386c72ca604`). `a406` 입력 프레임, descriptor hook `bf2c`(7e 감소, 0이면 사건 3, 80≠0이면 `a70a`), `10fdb6`/`10fdb7`→d(A2) mask(`9fc4`), 입력 edge `104cba`/`104cc0`의 bit 0,1,2,3,5,4 순서 처리, 사건 전달 루프 `a44e`/`a5aa`, `a70a` 효과음 `1a5b`→`a1ee` -e5=2. 입력·BIOS 영역 BYTE는 선언 fixture다.

## 메인 리뷰

1. Core 60 case를 원본과 대조했다. 결함은 없었다. 입력 group bit 순서와 분기 대상, BTST/SNE/ANDI.B/OR.B BYTE 한정, BCLR/BSET RMW, `bf34` SUBQ+MOVE.W+BNE의 Z, `10fdb6`/`10fdb7`의 1 또는 3 판정을 확인했다.
2. carry 보존 13 block이 모두 FLOW_ONLY임을 확인했다.
3. 미확인 기록: f bit0 재그리기는 `9e1a`를 남은 A1로 실행한다(원본 동작, 자연 도달 미확인).

## 검증 결과

- Native: 정상 92·guard 7 조건, split 35786, control 842. 300프레임 7e 카운트다운은 frame 300에서 사건 3→NO→`a1ee`, frame 301에서 `a662` stop이다. 관측 SHA `49c1ba52f7ec11dc1929022f7dc6b455b434681d472e9a39631c69ea98ce9b46`, 도구 SHA `cbd6fdf19fcc4c5ccec8126be1ab9f98501df5a393dd9805da3f1b7802e66104`.
- C++ 비교(해당 단위 커밋 상태, detached worktree): 99조건, split 35779, 재개 35682, 음성 128(native guard 7 + API 121), zero-step 180, carry 탐침 42672. 보고서 SHA `383e7d4f6b1dc0a558153e0e2be76163e64682cec4178ba1c082e3c6a56605d5`(두 번 같음), 검증기 SHA `3e9395dcecab9045d36a17c5f3fcb73f10f7f34b1c71c6baea71f5ae2a253ed0`.
- core `aaa1a4d2a663cb1212f7fbb4982f01c95de6b03f36b7cceafe3afa9405bed78d`, unit `bbc6ffb288da7b738d05350b06ce911933f874cebcc4f672bd48b2bfee90b74e`(1399 API 호출).
- 이전 검증기의 경계 음성 이동과 전체 회귀는 0239 최종 상태의 정렬 커밋에 기록한다.

## 남은 제약

`a662` 닫기, `bd26` BIOS 카드 저장, 원래 입력 루틴, `10fdb6`/`10fdb7`의 실제 BIOS 의미. 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다.
