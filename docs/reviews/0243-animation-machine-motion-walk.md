# `480bc` motion walk U3(`18c06`..`19768`) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 작성·보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측.
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. 해당 단위 커밋에 고정된 별도 detached worktree(`metalslug-vu3`)에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: U1~U7은 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 U7까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-motion-walk-u3-contract.md`(SHA256 `fe5db3bd8d160296e71a82e5ddace169b9dd61b6dd15c0e61fd0b96f0fc6793d`). U2 경계 `19812`/`19844`/`19910`에서 이어지는 motion walk. 메인 결정: (1) 처리 범위는 선택 F(36 type slot 전부, block 시작 370), (2) TST/AND의 known Clear, (3) 범위 밖 type은 U2 정책(계산 PC)이다.

## 메인 리뷰

1. Core 370 block을 원본과 대조했다. 결함은 없었다. 묶인 분기 14, 소비 block 9, 생산자(ORI Set 6 / ANDI Clear 1 / 계산 Clear 4)가 계약·관측기·C++ 표와 일치한다.
2. 계약 정정: 계약의 자연 도달 목록에 들어 있던 `18d32`/`18ece`는 type 80이 자연에서 실행되지 않아 잘못 포함된 항목이다(관측기 `contract_discrepancies` 1건). C++ 불일치가 아니라 계약 서술 문제이며 계약의 해당 문장을 바로잡는 것으로 처리한다.
3. Carry 규칙: 68000의 TST/AND는 항상 C=0이므로 `19710`/`1971c`의 TST.W와 `19372`/`1957a`의 AND.W는 C를 known Clear로 남긴다(메인 결정 2). 이 규칙은 소비 block으로 이어지는 생산 block에 한정하고, 해당 phase 176/224개에서 C++ 결과와 일치한다.
4. U2~U5 연결 후 `scene_frame` 1a73c→RTS 594 frame을 C++가 native 기록과 전부 맞게 실행했다(U5 검증기 기록).
5. 범위 밖 `19938..19978`(관측기가 선언한 4 row)은 C++가 라우팅하지 않는다. 비교에서 제외하고 정확한 오류와 보존만 확인했다.

## 검증 결과

- Native 일반 1333 + guard 30 조건(검증기 비교 1359), split 45408 phase. 관측 SHA `411f3444d365d487dc2e5e8fca861c2117dd9aa21733af7f8537e514e9708968`, 도구 SHA `c3112b04fbbeb54f76a77e8063099bdbe9231ce3cd2f2a95267368c922ae2d0b`.
- C++ 비교(detached worktree, 커밋 `a0b3df5`): 1359 case, split 45408(재개 44097), continuous 1304, Carry Unknown 41964 / Clear 1408 / Set 2036, probe 88876, zero-step 370 x 3 = 1110. 보고서 SHA `6ede75393848e017452f60dbedd596b01325de705cca7b2799ea2244c70167c2`(두 번 같음), 검증기 SHA `e6230dfffbd899d125fc13e328032d059c1a284a721e7abf76ff1a0f9a2ec901`, 실행 문서 SHA `fd49b3dcf7652b3893ba962ae672e5ae8265f05f6d68ed959c5e425f7fb253d4`.
- core `animation_machine_motion_walk.cpp` SHA `7f04d6b56287f97a265a1f7313c04c1dad8824035c072bb109685b8ca23a6b1b`, unit `animation_machine_motion_walk_test.cpp` SHA `16ddeaf9a98b45f174b6835e24e618a4968107ae05dbd8efd548ce483afbbc48`(3865 API 호출 PASS).
- 이전 검증기 `verify_animation_machine_scene_core.py`의 71~72·783~789·813~814행(`19812`/`19844`/`19910`을 미지원으로 가정)과 8·939행 문구는 최종 상태의 정렬 커밋에서 조정한다.

## 남은 제약

통제된 fixture 검증이며 자연 scheduler/IRQ 도달성이 아니다. 캡처·stage_entry 상태는 native 산출물 SHA 고정으로 재구성하지 못했다. 홀수 계산 PC의 dispatcher JMP 직후 부분 효과(D4.W)는 API로 관측할 수 없어 비교하지 않았다. native 오류 rollback과 C++ 검사 오류의 동등성은 주장하지 않는다. U4/U5 본문은 별도 단위다.
