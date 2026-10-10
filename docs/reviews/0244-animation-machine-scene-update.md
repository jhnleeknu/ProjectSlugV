# `480bc` 장면 갱신 U4(`1a7a8`) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 작성·보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측.
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. 해당 단위 커밋에 고정된 별도 detached worktree(`metalslug-vu4`)에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: U1~U7은 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 U7까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-scene-update-u4-contract.md`(SHA256 `68855b9567d285c4bcd6d3ae3e1024d304384ed03e4b1fc3401dfe0b5a1637dc`). `1a7a8` 장면 갱신(코드 1486바이트 405명령 + 디버그 표 200바이트, block 시작 118). 메인 결정: (1) 디버그 경로 `1b016..1b126`(`10f000` bit3/4)은 선택 D로 구현, (2) X flag는 block 안에서 지역 계산하고 노출하지 않음, (3) `43e08`/`43e22`는 U5로 이월, (4) path opcode index는 U2/U3와 같은 계산 PC 정책이다.

## 메인 리뷰

1. Core 118 block을 원본과 대조했다. 결함은 없었다. 묶인 분기 46, FLOW_ONLY 55, C 생산자·소비자 0이 원본 opcode 유도와 일치한다.
2. X flag: SUBX 생산자와 소비자(`17258` `17278` `1b058` `1b074`)가 같은 block 안에 있어 지역 계산으로 충분하다(SUBX의 Z 규칙 포함). 공용 machine 상태는 바꾸지 않았다.
3. `1724c`: `MULU.W`/`MULS.W`/`ASR.L #8`(산술)/`LSL.L #8`과 `ADD.B` 메모리 올림 + `SUBX.L`의 wrap을 원본 비트 폭대로 구현했음을 확인했다.
4. U2~U5 연결 후 `scene_frame` 1a73c→RTS 594 frame을 C++가 native 기록과 전부 맞게 실행했다(U5 검증기 기록).
5. `1a69e` BSR.W는 C++ 범위 밖이므로 검증기가 host 측 BSR로 대체하고 원본 phase와 독립 대조한 뒤 `1a7a8`부터 C++를 실행했다.

## 검증 결과

- Native 입력 674개. 관측 SHA `fdceb7710a9c73ca6ceb7459475ac6f6d05ebd26529510e7b516ab8cc1f9a063`, 도구 SHA `8ea6a0a9881bd48f262c15bff341822d10a9617d4f5b590ab8060a0132f9b981`.
- C++ 비교(detached worktree, 커밋 `b6b79ac`): 343 행(정상 325 + guard 18), split 12171(재개 11802), continuous 369, 탐침 24302회(불일치 0), Carry Unknown 11877 / Clear 109 / Set 165, zero-step 118 x 3 = 354, negative 671 = guard 18 + API 653. 보고서 SHA `db6f1aecb7175da82c9613679b24f58d053ace76d985bd15238a9c4f6989764d`, 검증기 SHA `4aab890a0d868f60e2f4d5c39c22c787a2b7068754f985be724dcc70c505787b`, 실행 문서 SHA `8d36f5c1bacacf1184aaebf16ccae2ba4980c8111c8c4400379e912b1e11b945`. 보고서 두 번 실행 동일 여부는 실행 문서에 기록되지 않아 [U].
- core `animation_machine_scene_update.cpp` SHA `8f5d43d2a9ba229abd29272d999c4709bad2a19aa49aaf94098f30aa9c899ccb`, unit `animation_machine_scene_update_test.cpp` SHA `483f706c62b6c8ae2bfe59f5df1ce85eacc7abe31ad5b4bbf1f476926583eca7`(1559 API 호출 PASS).
- 이전 검증기 `verify_animation_machine_scene_core.py`의 `1a7a8` 미지원 가정(BOUNDARY_PCS, outside 목록, `guard-bad-stop-1a7a8-on-19844-seed`, 한계 문구)은 최종 상태의 정렬 커밋에서 조정한다.

## 남은 제약

선언 상태 중 다른 행의 실제 C++ 연쇄 출력과 독립 재현된 것은 6개뿐이며 나머지 206은 원본 산출물 SHA 고정으로만 보증된다. 미관측 경로(조건 opcode 08/0c/10/14, 1c 등)는 선언 fixture의 host 쓰기로만 검증됐다. 실패는 API 출력 보존이지 원본 CPU 예외 롤백이 아니다. 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다.
