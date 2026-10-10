# 카드 메뉴 YES 선택: 카드 저장 `bd26`(BIOS 경계 3회)과 결과 하위 메뉴 push 리뷰

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

계약 `docs/analysis/animation-machine-card-menu-save-contract.md`(SHA256 `d8d67ebb51671e4603cc8632268dedfb4e94bd0cb89fbd71354231f269b72a79`). `c1c4` 사건 3→`bd26`: `bbb8` 이름 복사, `bb74` checksum(`107f32`), BIOS `c00468` 두 번(명령 4·3)과 `c0046e`은 실행하지 않는 경계이며 선언 재개(PC=복귀, A7+=4, `10fdc6`)로 잇는다. `be0c` 결과 known C→`c1ea` 소비→`9f36`→`a71a`→`a0a0` 중첩 push(`a100` 추가)→효과음 `1adb`.

## 메인 리뷰

1. Core 29 case를 원본과 대조했다. 결함은 없었다. `bb76` ADD.W D0,D0의 WORD carry(bit15), `bbc0`의 옮긴 BYTE Z, `9f50` 부호확장 index, `-e4`/`-ce` 변위, `be1c` 결과 분기를 확인했다.
2. native checksum은 `0x8707`, 결과 프레임 `107eee` 바이트는 C++ 테스트 기대값과 같다.
3. 검증기의 native guard `guard-desc-flags-0001-9e94`는 관측 도구가 `9e94`를 범위 밖으로 둔 결과다. C++에서는 0237 닫기 실행부가 `9e94`를 실행하므로, 메인이 superseded로 판정했다(음성에 포함하지 않음).

## 검증 결과

- Native: 정상 66·guard 13 조건, split 3871, control 116. 체인은 frame 1, 커서 위, 선택→BIOS #1·#2·`c0046e`, 재개(SAVE OK)→`2ac2`, NO SAVE 갈래 포함. 관측 SHA `b0f9e26195f9a31181a6164f4ee15b93497515a7782dccc7f5a0e74ada142c0c`, 도구 SHA `eaf7d1a91e1f1f082ddcca0acce417076e3dcf78686738f0de1723391131934c`.
- C++ 비교(해당 단위 커밋 상태, detached worktree): 79조건, split 4038, continuous 116, BIOS 재개 71, 음성 95, zero-step 87, carry 탐침 7488. 보고서 SHA `8c403230fccdacb402c9888dc911dff9ee3739c5c1df517b99bcb082a33f5076`(두 번 같음), 검증기 SHA `b376944a17b915a12bf25e4c93c299be05cded3c6d08b76ec66f39d28a334d43`.
- core `05d4e6b864440b23c213ce0b4fe43712477ae756e18c8cfc0db49bcec647913e`, unit `3062813f2786620b1c12b3798d748716d4995a67d1d27e2da91db7c170416ab1`(799 API 호출).
- 이전 검증기의 경계 음성 이동과 전체 회귀는 0239 최종 상태의 정렬 커밋에 기록한다.

## 남은 제약

BIOS `c00468`/`c0046e` 내부와 카드 기록 결과, `10fdc2..10fdd0` BIOS 의미(재개 값은 선언 입력). 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다.
