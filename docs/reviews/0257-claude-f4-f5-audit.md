# Claude F4/F5 진행 감사 — 2026-10-14

대상: `/Users/start/Workspce/metalslug-f4`, `codex/f4-continue`, `b8502bfaa8c6bebd6f02d79a9be46b16543cc289`.
사용자 요청은 진행 상태 검사다. 이번에는 구현·기존 검증기·ROM·공유 산출물을 수정하지 않고 문서만 추가한다. 전체 Goal은 재개하지 않는다. 메인이 공통 실행부와 실제 검증 결과를 검토했고, gpt-6.1-sol/medium 작업자 3개가 F4, F5, 산출물 출처를 독립 점검했다.

## 판정

계획된 주 단위의 구현·병합은 확인된다. 그러나 현재 최종 HEAD의 전체 원본 비교·회귀 인수는 완료되지 않았다. Claude가 밝힌 미완료 항목은 실제로 남아 있으며, “G2가 현재 코드에서 통과한다”는 요약은 확인된 증거보다 강하다. 기존 문서는 역사적 실행 커밋을 대체로 명시하고 있다.

## 확인된 구현과 관측

- F4 U17/U18/U19/U20a/U20b, N01/N03~N35 및 N32b에 소스·라우터·내부 선언·Makefile/시험 등록이 있다. N02는 U20b로 통합된 것이므로 파일 누락이 아니다. N33 201, N34 220, N35 26 case와 u08b `4bc58` 두 번째 진입점을 확인했다.
- N 이름의 본체가 병합됐다는 것은 해당 영역 전체가 끝났다는 뜻이 아니다. U19b/N16b/N19b/N22b/N29b/N30b와 고아 설치 사슬은 여전히 미구현이다. 설치되는 callback 값에 `b7100`, `776da`, `3d3f0`, `3323e`처럼 아직 실행부가 없는 값이 남는다. `4d418` 반환 C도 미확인이다.
- F5 H1/H2/H3/H4(H4~H7)/H8(H8~H11)와 외부읽기 queue API가 구현됐다. queue 주소/크기 일치, 값 폭 마스킹, 실패 전체 rollback, Waiting 후 소비 commit/재개 시험이 있다. 이번 검토에서 구체적인 새 엔진 결함은 발견하지 못했다.
- G3 native 관측은 공유본 및 scratch run1/run2가 동일 SHA256 `5bab5b216f7e3af4870544bf5f4467ec0507e836fe7def10bda1c957c816849f`다. 현재 계약/도구 pin도 일치하며 자연 node 30,632, typed fixture 2,459, 계약 차이 21건을 기록한다. 이 21건은 곧바로 C++ 오류 21건을 의미하지 않는다. C++ G3 검증기는 아직 없다.

## 완료 주장에 필요한 한정

### F4 RNG 136/137은 이전 커밋에서 확인한 결과

`/Users/start/Workspce/ms5-scratch/main-rng/h4800f35/verification.json`의 SHA256은 `57b2fe9527f6df03aaf34654fad98e336b14b04ce0917b10a1a143caa1757c8c`다. 자연 136완주, guard 종료 5, 자연 odd-PC 종료 1, 원본 동등 pass 54,400/node 412,067, 불일치 0을 실제 보고서에서 확인했다. answer00 변형 6개도 2,400pass/19,936node 일치다.

하지만 기록된 `animation_machine.cpp` SHA는 `032b04cc1d41199bc2a5235d65a2616495b72fe63697b0289d061ee7bcfed535`, 현재 값은 `c7318132fcdfd288c12a58ab7e51c03e2920b46d7e939103bd917d72ca8caad2`다. 그 뒤 H8의 carry 목록과 `ce62..f226` 라우팅이 추가됐다. 기록된 나머지 C++ 소스 해시는 일치한다. 따라서 당시 `4800f35` 결과로 인정하며 현재 HEAD의 새 전체 실행으로 취급하지 않는다.

seed141 원본은 frame0/node2/A6=100b30/callback47af0에서 홀수 PC `47c05`에 도달한다. C++ 보고서는 앞선 두 node의 일치와 같은 frame의 unaligned 오류·rollback을 확인한다. 실패 node의 최종 PC/전체 예외 상태까지 동등하다는 증거는 아니다(`verify_animation_machine_scheduler_rng_f4.py:321`). F2 pass만 실행하고 head/controller를 생략하는 선언 모델이라는 제한도 유지한다.

### G2 “현재 코드 PASS”의 근거는 부족

공유 보고서 `artifacts/animation_machine_objects_g2_execution/verification.json`은 `4f91481`의 역사 결과이며 SHA256 `f6773ae749a342085c559e5010435070d0e4705d9eecd58a860a1e2c2e71c082`다. `a22c318` 재실행도 존재한다(`/Users/start/Workspce/ms5-scratch/vg2/out/head_a22/verification.json`, SHA256 `8553779f25fee31dd8ea647a5497c946e902dcdcdfffdc6c85d072e6d6ecf15b`). 두 실행의 통과 기록과 현재 HEAD의 통과는 구분해야 한다. 현재 라우터 pin이 다르며 최종 HEAD 전체 실행은 이번 검사에서 확인되지 않았다.

### F5 4,975+976은 표본 비교이고 현재 소스 인수 보고서가 아님

`ms5-scratch/h2/realrom/nat_all.log`와 `nat_var.log`는 자연 4,975구간/136seed 및 변형 976구간/48seed, mismatch0, 관측 재현 mismatch0, stop `c52a`를 기록한다. `nat_h2.py:120`은 저장된 pass-end dump의 다음 H만 고른다. 자연 H 전체 54,264개나 최초 e4a frame 전부를 C++ 비교한 결과는 아니다.

비교 대상은 RAM FNV digest·16레지스터·PC·bank·순서 있는 ports·wait 횟수·외부읽기 소비 수·잔여 queue 길이다. 전체 PVC bytes, 최종 status, 잔여 queue 내용, C++ wait PC 순서는 이 scratch 출력에 없다. 비교기가 mismatch를 출력하지만 실패 exit/assert를 하지 않는 점도 자동 인수의 약점이다(`nat_h2.py:151`, `:155`, `:164`; `batch_h2.cpp:38`, `:52`). 당시 mismatch0 로그 자체는 확인된 사실이다.

이 scratch 비교에는 최종 소스/바이너리/리소스 SHA 인수 기록이 없다. H1~H4 소스 자체는 당시와 같지만 현재 router/u08b 등은 다르므로 최종 HEAD의 검증으로 확대하지 않는다. 관측기 자신의 SHA도 observation의 inputs에 포함되지 않는다.

H8은 자연 실행 0이다. `108d3c` bit7을 바꾼 선언 상태 4,975개 + fixture 2개(총 4,977)의 비교 기록은 있으나 stop은 `31d6`(H2 앞)이다. 이를 H8 포함 controller까지의 자연 실행 증거로 세지 않는다.

## 실제 재현한 실패 및 검증 정리 미완료

1. 현재 소스에서 새 common harness를 빌드하고 원본 base fixture로 공식 `negatives()`를 호출했다. 첫 `unsupported-PC`에서 기존 기대 `unsupported animation machine PC` 대신 `unsupported animation frame head h8 PC`가 나와 AssertionError가 발생했다. `deac`는 H8 범위 안의 interior PC이며 실행 가능한 block 시작으로 바뀐 것은 아니다. 전체 rollback은 유지됐다. 증거: `/tmp/ms5-oct14-main-audit/legacy-probe/result.json`, 재현 스크립트 `probe_legacy.py`.
2. `deac` 관련 이전 Python 검증기는 base/activation/cleanup/hud/exit/readiness/map_transfer/palette_bind/scene/screen/transition 11개다. card_menu의 `outside_range_entry_003902`도 H2 구현과 맞춰야 한다. 12개 전체를 재실행한 실패 수라고 주장하지 않는다.
3. stage_event/stage_event_ops의 고정 source pin이 현재 router/internal header와 다르다(`verify_animation_machine_stage_event.py:55,395`, `_ops.py:58,430`). 기대값만 맹목적으로 갱신할 것이 아니라 변경 검토 후 재검증해야 한다.
4. RNG 감사의 결과 수는 아직 134완주/2미연결, 53,600pass/403,677node다(`audit_animation_machine_scheduler_rng_f4_execution.py:69`). 기록된 136완주 결과조차 그대로 인수하지 못한다.
5. 기본 경로 `artifacts/animation_machine_objects_integration_execution/execution.json` 및 `artifacts/animation_machine_scheduler_rng_f4_execution/verification.json`이 없다. scratch override로 접근할 수 있는 역사 자료와 기본 실행 가능한 인수 패키지는 구분한다.

## 삭제 산출물 복구

문서에 지정한 네 역사 보고서는 모두 정확한 SHA로 복구돼 있다:

- stage_counter_bcd: `bf692382e2f4905834e6cfc806944c4633d23d9989879a1b0adcf471c75d294e`
- scene_general_initialization: `0a0e19dd0626d5f4880c983afe07cf8f2959ab4723803eebdaa859d71e95022a`
- stage_frame: `47645dd39e0df8241cb504cd637a99cdc751544b4ac47c9e1227d8d5705f53b5`
- scene_frame_execution: `bdbeea5e8caa803f045d574a2fd67d726dc7fed23c829a43dfc50ad1dfc56fad`

“약45개 변경”의 정확한 명단/이전·새 hash manifest는 확인되지 않았다. `docs_digest_scan.txt`의 full-hash 문자열 검색은 약식 SHA/원래 기록 없는 문서까지 섞으므로 이를 변경·손상 수로 대신할 수 없다. 별도 현재 입력 감사에서 58개 역사 보고서의 406개 pin 차이를 발견했지만 이것도 58개 실패나 손상을 뜻하지 않는다. 해당 기록 필드에서 참조 파일 누락은 0이다. 목록: `/tmp/ms5-oct14-provenance-audit/report-input-drift.json`.

## 이번 직접 실행 검증

`b8502bf`를 `git archive`로 `/tmp/ms5-oct14-main-audit/source`에 복사하여 공유 build/artifacts를 건드리지 않고 `make -j4 all test`를 실행했다. C++ 시험 실행 파일 249개 및 Python 시험 257개가 최종 통과했고 컴파일 경고는 0이다. 첫 make 실행은 격리 복사본의 `artifacts/reference/prot_cmc.cpp` 누락 때문에 Python 단계에서 종료 2였다. 그 앞 C++ 209개는 통과했다. 참조 파일을 동일 SHA로 복사한 뒤 Python 257개를 다시 실행해 종료 0, 뒤 C++ 40개도 각각 종료 0을 확인했다. Makefile의 시험 누락이나 제품 코드 오류가 아니다. 전체 `make all test`가 한 번에 종료 0이었다고 기록하지 않는다. 최종 메타데이터와 로그 해시는 `/tmp/ms5-oct14-main-audit/verification.json`에 있다. 원본과 격리 복사본의 tracked engine/tools/Makefile 바이트도 다시 비교해 차이 0을 확인했다. 오래 걸리는 RNG400/F5 native 전체 재관측이나 전체 Python 실행 검증기는 이번 감사에서 다시 돌리지 않았다. 보고서·소스·pin·원본 관측 증거를 대조했다.

## 남은 구현과 권장 순서

1. 기존 negative 및 source pin을 실제 새 동작과 맞추고 현재 HEAD의 회귀를 다시 인수한다. G2/RNG/F5 결과의 실행 소스와 비교 범위도 명시한다.
2. G3 C++ 검증기를 만들고 관측/계약 차이 21건을 정리한다.
3. D1 전체 선언 frame 구동기(H → controller 선언 생략 → N)를 구현·비교한다.
4. D9 결정을 확정하고 controller C1~C3를 진행한다.
5. 여섯 deferred b-unit, 고아 사슬과 `4d418` 반환 C를 정리한다.

이는 검사에서 정리한 다음 순서이며 이번 턴에서 구현을 시작한 것이 아니다. 전체 게임 완성률을 136/137이나 표본 통과율로 계산하지 않는다.
