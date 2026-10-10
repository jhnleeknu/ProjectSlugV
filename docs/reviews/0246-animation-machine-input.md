# `480bc` 입력 U6(`49b0c`·입력 callback) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 작성·보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측.
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. 해당 단위 커밋에 고정된 별도 detached worktree(`metalslug-vu6`)에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: U1~U7은 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 U7까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-input-u6-contract.md`(SHA256 `99ba39b26d652b48189f1ab55251c6a099bad4faa21abb2d5a387522636c98dc`). `49b0c` 입력 루틴과 입력 callback(U6a·U6b·U6c, block 시작 151 중 실행 150, `4d7f0` TRAP은 stop 경계). 메인 결정: (1) U6a·U6b·U6c 전체를 하나의 core로 구현, (2) `JSR (A1)` 대상은 계산 PC 정책이며 상위 BYTE가 0이 아니면 24bit로 접지 않고 checked 오류, (3) `4d7f0` TRAP #15는 실행부 없는 경계, (4) `49dd4`·`49e8a`는 앞 block에 접고 `49f4a`는 두 선행 block에 복제하며 직접 진입은 거부, (5) ROM 자료는 물리 `program_rom_000000.ms5d` window로만 읽는다.

## 메인 리뷰

1. Core 150 block과 `carry_preserving_pc` 표(계약 66개와 정확히 같음)를 원본과 대조했다. 결함은 없었다.
2. 표 index 132..138과 167..169는 코드를 읽는다(자료가 아니라 명령 바이트). 이 항목은 메인 결정 기록이며 core 반영은 U6 검증기의 직접 진입·callback 대조로 확인했다.
3. `JSR (A1)` 대상의 상위 BYTE가 0이 아니면 checked 오류다. 실제 24비트 주소 하드웨어는 상위 BYTE를 접어 `049e34`를 실행하므로 이것이 실제 하드웨어와 다를 수 있는 유일한 지점이다. 잘못된 결과 대신 오류를 낸다(의도된 차이).
4. 내부 `49e36`(block 중간 RTS)는 거부한다. native는 실행하는 변종 2행이 있으며 이 역시 의도된 차이다.
5. 계약 정정: 계약 범위 표의 "명령 수" 열이 4개 행에서 디코드 결과와 다르다(`49de6..49e34` 22/23, `49f66..49f8c` 8/9, `49d88..49de6` 31/29, `49e38..49f66` 83/85). 합은 366 대 368이며 바이트와 단위 합계는 맞는다. 문서 오타이므로 표를 고친다.
6. 이전 단계(U1)의 `49b0c` 경계가 이제 U6 block 시작이므로 U1 단위 테스트의 `49b0c`→`480cc` 기대값이 이미 갱신되었음을 확인했다.

## 검증 결과

- Native 저장 658 + guard 27, 정상 census 7527. 관측 SHA `311fb438bae1ff7aa013bf4e175302a7ba249cff5ef78eb45caa258308ec78b4`, 도구 SHA `de302e9213e6946a2157fe7146d48561c053aed51eb9b4984a464e2a1f7f240a`. 관측 파일 121001개를 전부 읽어 해시를 확인했다.
- C++ 비교(detached worktree, 커밋 `2f65d65`): split 11408, continuous 656(변종 2행 제외), 재개 10750, 정상 end-to-end 7527(자연 206 저장 행, 나머지 7321은 고정 관측기 함수로 재구성해 Unicorn으로 재실행: native 쪽이 저장 데이터가 아니라 재실행 값), 불일치 0, 제로 스텝 150 x 3 = 450 + 경계 5곳 x 3, 직접 진입 거부(명령 중간 217, 피연산자 WORD 276, 범위 밖 21, 홀수 7). 보고서 SHA `f74a5d8ee46aeb38bc90f3f40973f523f473d4a01be2dd110a4779a98a9486a9`(두 번 같음), 검증기 SHA `509dd1d0455969f7137816e4bc5ba08ac972328e1302900452fdb08765dc4acf`, 실행 문서 SHA `71336467313171ce694d2aa3f7c2fa6bba40c9632cb1332d14406efa2696988d`.
- core `animation_machine_input.cpp` SHA `ca5b990786de072951f89e724d2aba69c40df525441c3e18039eeef80acb4e8b`, unit `animation_machine_input_test.cpp` SHA `0323e98d390c56e38c695514f0d640cf71cec629a1d3dc2268e09a3ae01e0723`(1771 API 호출 PASS).
- 이전 검증기 `verify_animation_machine_frame_helpers.py` 36·548·554·687·9행의 `natural_480bc_with_stop_49b0c` 등 `49b0c` 미지원 가정은 최종 상태의 정렬 커밋에서 조정한다(`49b0c`가 이제 U6 block 시작).

## 남은 제약

비저장 6,869건의 native 쪽 최종 상태는 저장 기록이 아니라 재실행값이다. U6c callback 6종은 ROM 설치 경로가 없어 선언 slot 값으로만 관측한다([I]). TRAP #15 처리기와 필드 의미, slot 상위 BYTE 비영 값의 자연 발생 여부는 미확인이다. 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 미완료다.
