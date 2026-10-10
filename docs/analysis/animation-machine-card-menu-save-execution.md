# 카드 메뉴 YES 선택 카드 저장 실행부 검증: native 증거 대 C++ 공개 API

Baseline: 카드 메뉴 push/열림/입력/닫기/저장 C++ 실행부(커밋 2f96337). 검증기 `tools/verify_animation_machine_card_menu_save.py`, 보고서 `artifacts/animation_machine_card_menu_save_execution/verification.json`(Git 제외). 원본 ROM은 수정하지 않았고 ROM·추출 데이터는 Git에 추가하지 않았다. 계약 `docs/analysis/animation-machine-card-menu-save-contract.md` SHA256 `d8d67ebb51671e4603cc8632268dedfb4e94bd0cb89fbd71354231f269b72a79`, native 관측 SHA256 `b0f9e26195f9a31181a6164f4ee15b93497515a7782dccc7f5a0e74ada142c0c`, 관측 도구 SHA256 `eaf7d1a91e1f1f082ddcca0acce417076e3dcf78686738f0de1723391131934c`, ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(fixed CPU 주소=file offset).

## 방법(사실)

- 입력은 불변이다. 검증기는 관측기 main을 호출하지 않고 native 파일의 해시·trace 일관성(program read, split 대 continuous, 포트 순서)을 감사한다.
- 시작 상태는 native 레지스터가 아니라 C++ 실제 출력이다. fade/card 체인 BIOS 정지 출력(스텝 158)에서 시작해 open-native 체인 스텝 0..30(445 split, 카드 child a29c 스텝 24, push a370 스텝 25, 열림 프레임 스텝 30)을 C++로 다시 실행했고, 세 지점의 RAM SHA256이 save 관측의 교차 기록(`3e5d1fb0…`, `268b5550…`, `cb5ada60…`)과 같았다. 저장 체인 행은 스텝 31..36만 저장하며 445+4051=4496, 31+129=160이 관측 전체 합과 일치한다.
- 모든 split 스텝은 이전 C++ 출력과 native 기록의 선언 host 변경(pc, a7_add, ram)만으로 재개하고, 변경 종류·`pc_before`·`a7_before`를 기록과 대조한다. 각 스텝에서 64KiB RAM, 16 레지스터, PC, A7, PVC, bank, 순서 있는 포트, external read, status를 native 기록과 비교한다.
- 새 행(fresh/direct/answer/tail/nested/desc/bbb8/bb74/bd26/be0c)은 저장 체인의 해당 스텝 C++ 출력(RAM SHA256 일치) 위에 선언 준비만 더한다. 40개 행이 선언 레지스터 덮어쓰기를 가지며 보고서에 키 목록을 남겼다.
- 연속(continuous) 대조: 116개 스텝을 시작 상태에서 한 번에 실행해 split 마지막 출력과 같음을 확인했다.
- 체인 대 fresh: 6개 `compared_with_chain` 행의 823 phase가 체인 C++ 출력과 (carry 제외) 같고, `connected-input-f1-to-no-save`는 165 phase 일치 후 phase 165부터 분기(NO SAVE 경로)하여 관측의 부분 비교값 165와 같다.

## BIOS 경계(사실)

- `c00468` 두 번(bd5a, bd8a의 JSR 직후), `c0046e` 한 번(be16)은 실행하지 않는다. 정지 증거는 JSR 바이트(`4eb900c00468`/`4eb900c0046e`)와 이전 PC를 확인하고, C++ 출력 stack의 반환 LONG(`bd60`/`bd90`/`be1c`)과 그 위의 저장 A6를 직접 읽어 확인했다. 관측된 정지 지점 수 bd5a 19, bd8a 19, be16 18.
- 선언 재개 71회: 반환 LONG을 PC로, A7+=4, 필요 시 BYTE `10fdc6` 또는 다른 선언 RAM. PC는 stack의 LONG과 같음을 단언했고(bd60 21, bd90 14, be1c 36) A7 증가분은 4이다.
- stop을 BIOS가 아닌 값으로 주면 전체 rollback과 `unsupported animation machine PC`다(bd3c/bd60/be0c 세 시작 상태 × 4개 stop, 직접 BIOS 진입 × 3 stop).

## Carry(사실/추정 구분)

- 사실: 4038 split phase 모두 C++ carry가 native 실행 PC 위의 소스 opcode 분류(FLOW_ONLY 보존, ORI #1,CCR=Set, ANDI #fe,CCR=Clear, 그 밖 Unknown)와 같다. 분포 Unknown 3414, Clear 567, Set 57. native SR은 읽지 않았다.
- 알려진 C(1/2) 프로브 7488회(C를 읽는 분기가 쓰기 전에 실행되는 294 phase는 제외)가 소스 분류와 같고, 나머지 출력은 동일하다.
- 단일 block 단독 관측: 보존 block a100 a72a bb8c bbd0 bd90은 두 프로브 모두 보존, `be2e`는 Set·`be34`는 Clear를 항상 만든다. 소스에서 유도한 보존 목록이 계약/주석의 7개 `a100 a71a a72a bb8c bbd0 bd90 c1ea`와 같다. `a71a`와 `c1ea`는 단독 phase로는 관측되지 않았다(미확인: 직접 단독 관측 없음. `c1ea`는 known C 두 값에 대한 별도 제어로 확인).
- `c1ea`: known Clear→`c202`, known Set→`c1ee`이고 다른 상태는 그대로다. Unknown이면 `card menu caller requires known carry`와 전체 rollback.

## 부정 검증

- 내부 PC 52개(조건 분기 7개 포함)는 모두 정확히 `unsupported animation card menu save PC`이며 전체 상태가 보존된다. 범위 밖(9f34, 9f78, a72c, bb8e, bbd4, bd94, bd96, be3a)은 `unsupported animation machine PC`.
- 12개 native guard는 확인된 API 오류와 전체 보존으로 재현된다: 중첩 한계 2·BIOS other-stop 6은 `unsupported animation machine PC`, 홀수 `-ee`/descriptor 읽기와 홀수 A7 push는 `program bus requires even WORD/LONG address`, 홀수 A5의 WORD 쓰기는 `invalid animation machine write size/alignment`.
- 부정 검증 총 95건(83 + guard 12), zero-step 87건(block 시작 29 × carry 3)과 BIOS PC 두 곳의 zero-step이 입력 상태를 그대로 돌려준다.

## 미해결/주의(미확인 포함)

- `guard-desc-flags-0001-9e94`: native 관측기는 9e94를 매핑하지 않아 fetch 오류였지만, C++에는 닫기 실행부가 있어 같은 입력이 `2ac2`까지 오류 없이 실행된다. 이 guard는 대응 관계를 주장하지 않고 보고서의 `native_guards_superseded`에 결과만 기록했다. 닫기 경로의 native 대응은 닫기 단위 검증의 범위다.
- BIOS 내부(카드 쓰기, 레지스터 `10fdc2..10fdd0`, 응답 `10fdc6`)는 미모델·미확인이다. 선언 재개 값은 입력일 뿐 원본 측정이 아니다.
- carry는 소스 분류이며 native C 측정이 아니다. 자연 scheduler/IRQ/timing, 화면 의미, 이후 하위 메뉴 프레임은 범위 밖이다.
- 실패 시 보존은 API 출력 보존이며 원본 CPU fault rollback 동등성은 주장하지 않는다.

## 기존 검증기 부정 검증 중 경계 이동이 필요한 항목(보고만, 미적용)

현재 엔진으로 같은 상태(C++ 접두 스텝 24/25 출력, carry Set, stop `ff000`)에서 직접 진입한 관측값이 보고서 `older_verifier_negative_inputs_under_current_engine`에 있다.

| 구 검증기 | 부정 항목 | 구 기대 | 현재 |
| --- | --- | --- | --- |
| push(`verify_animation_machine_card_menu.py`) | `interior_direct_entry_00a100` | `unsupported animation card menu PC` | a100이 block 시작이 되어 BSR 9e1a로 진입, 이 상태에서는 `unsupported program bus device address` (이동 필요: 내부 PC 목록에서 a100 제외, block 시작·zero-step 목록에 추가) |
| open(`verify_animation_machine_card_menu_open.py`) | `boundary_direct_entry_00bd26` 및 `bd26_reached_via_callback-c1c4-d0-3-bd26_with_stop_*` | `unsupported animation machine PC` | 같은 문자열이지만 이유가 BIOS `c00468` 미실행으로 바뀜. 경계 PC를 `c00468`/`c0046e`로 옮기고 bd26은 실행 PC로 취급 |
| open | `boundary_direct_entry_009f36`, `…00a71a` | `unsupported animation machine PC` | 각각 `program bus requires even WORD/LONG address`, `unsupported program bus device address`(실행 시작 후 오류): 경계 목록에서 제거 |
| open | `interior_direct_entry_00c1ea`(open 범위 c1c4..c214의 내부 PC) | `unsupported animation card menu open PC` | c1ea는 block 시작(known C 소비)이 되어 `program bus requires even WORD/LONG address`(이 상태에서 Set→c1ee 경로): 내부 PC 목록에서 제외하고 `NEEDS_CARRY` 계열 소비자 목록에 추가 |
| open | `cpp_preserving_cases()` 파싱(`// Card menu open blocks`..`// BTST/BEQ`) | 68개 | 저장·닫기 보존 case가 같은 구간에 추가되어 목록이 달라짐: 구간 경계 또는 기대값 갱신 필요(저장 블록은 `// Card menu save blocks` 아래 7개) |

`STOP_BOUNDARIES`/`BOUNDARY_ROWS`의 `bd26` 행(`callback-c1c4-d0-3-bd26`)은 stop=bd26 양성 제어가 계속 성립하지만, 이후 BIOS 정지(`c00468`)를 새 경계로 삼는 확장이 필요하다.

## 실행 기록

- 검증기 2회 실행: 보고서 SHA256 동일(`8c403230fccdacb402c9888dc911dff9ee3739c5c1df517b99bcb082a33f5076`, 실행당 약 7분). 보고서에 시각 정보를 넣지 않았다.
- `make -j4 all test` 한 번 실행, 종료 코드 0.
- `git diff --check`: 추적 파일 변경 없음, 새 파일의 후행 공백 없음.
