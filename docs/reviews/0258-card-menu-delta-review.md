# Card-menu guard comparator의 제한된 변경 영향 리뷰

2026-10-14, 읽기 전용 독립 리뷰. 대상은 `verify_animation_machine_card_menu.compare_guards`의 기존 guard `guard-overflow-rts-unsupported-target`다. F5 H1이 원본 `0x1000 RTS`를 실행해 기존 stop `0xa370`에 도달하므로 이전 unsupported-PC 요구는 현재 구현을 나타내지 않는다. 이 문서는 guard의 원본 의미나 신규 positive native proof의 수용을 대신하지 않는다. 그 proof와 수정된 공식 card-menu main은 별도로 검증해야 한다.

## Baseline과 조사 방법

공식 35개 목록은 `docs/reviews/0256-regression-manifest.json.standard_reports`다. 각 도구와 recursive local import를 AST로 읽고 module alias·from-import alias·attribute access·callsite를 수집했다. `build/g3_acceptance/card-menu-dependency-review.json`은 35개 source SHA, module import graph, target module의 모든 top-level AST node와 함수별 AST SHA, 정확한 호출·참조 위치를 보존한다. baseline whole-file SHA는 `dc7b50331100f24d786d0ae6ac6f7483bcc5d0e4b51b1f880817e4dfab622f4c`다. review JSON SHA는 `bacf64e656c9361da3cd8e18a700136fb9d1c8f296046abb6783ef13b6895fc7`다. AST SHA는 줄 번호를 제외하지만 node의 실행 의미를 나타내는 구조·값·식은 포함한다. 파일 SHA는 별도로 보존한다.

[F] target `compare_guards`의 호출은 정확히 **1곳**, target module의 `main`(baseline line 627)이다. 다른 34개 공식 verifier 및 그 local import closure에는 이 함수를 호출·참조·alias하는 경로가 없다. target의 `main`은 마지막 `if __name__ == '__main__'` 아래에서만 실행되므로 module import가 이 guard 비교를 실행하지 않는다. 동적 getattr/eval/exec로 target 함수에 접근하는 경로도 발견하지 않았다.

| 다른 verifier가 실제 참조하는 target API | baseline callsite |
|---|---|
| `glyph_entry_prefix` | card_child:493, card_menu_input:678, card_menu_close:627, card_menu_open:494 |
| `audit_native`, `compare` | card_menu_open:638,639 |
| `start_of_row`, `apply_changes` | card_menu_open:294,308,312; card_menu_save:225,232,343,347 |
| 상수·설정 | card_menu_open의 `MENU_RANGES`, `OUT`, `CARRY_PROBES`, `A29C`, `CARD_CHILD_CHAIN_STEP`, `ODD_JSR` |

`compare`와 위 함수들에서 `compare_guards`를 호출하지 않는다. 각 card-menu-family verifier는 자기 module의 별도 `compare_guards`를 실행한다.

[F] 보수적인 recursive AST import graph에는 target 자신을 포함해 21개 공식 root가 target에 도달한다. 대부분 `card_child.negatives` 내부의 local import를 통해 포함된다. 이 개수는 import/provenance 가능성이고 실제로 guard 함수가 실행됐다는 뜻이 아니다. 실행 경로의 비영향 판단과 whole-file provenance 변경은 구분해야 한다.

## 최소 재검증 범위와 주장 범위

조건부로 허용되는 patch 범위는 **기존 `compare_guards` 함수 body와 여기서만 호출되는 새 helper 정의**다. 나머지 module top-level node, 기존 함수·class·상수, import, decorators와 default argument 평가를 그대로 유지해야 한다. 새 helper는 import 시 side effect가 없어야 하며 실행은 해당 guard 비교에서만 시작해야 한다. 적용 후 baseline AST와 실제 patch AST를 독립 비교해 이 조건을 확인한다.

이 조건이 증명되고 엔진·공유 comparator·다른 입력이 바뀌지 않으면, 행동 영향에 대한 최소 재검증은 수정된 **card-menu 공식 main의 전체 실행**과 해당 guard의 독립 native proof다. 다른 34개는 기존 실행 결과를 보존하고 source-delta 동등성 overlay로 연결할 수 있다. 이 리뷰만으로 새 guard가 통과했다고 주장하지 않는다.

기존 report·manifest의 SHA 또는 input pin을 새 값으로 덮어쓰지 않는다. target whole-file bytes가 달라지므로 이전 report가 pin한 파일과 현재 파일의 byte identity는 성립하지 않는다. overlay는 변경된 함수가 해당 검증 실행 경로에 쓰이지 않았다는 근거에 따른 **행동 동등성**이며, 기존 34개가 새 whole-file hash로 다시 실행됐다는 뜻이 아니다. `all_inputs_unchanged=true`라는 기존 실행의 사실은 기존 source freeze에만 적용한다. 35개 전부를 현재 파일 SHA로 실행했다고 표현하려면 35개 전부를 다시 실행해야 한다.

## 후속 확인

- patch 준비·적용 후 AST delta 및 신규 helper의 호출 위치를 확인한다.
- 35개 실행 완료 후 실제 `inputs`에 target tool pin이 들어간 report 목록을 별도로 기록한다(보수적인 import graph를 actual-loaded 증거로 대체하지 않는다).
- 수정된 card-menu main의 종료 코드·새 report SHA·native proof 및 delta overlay를 기록한다.

## 제안 patch 독립 확인

[F] 적용 전 scratch proposal `build/legacy_acceptance/card_menu_guard_repair.py` SHA256 `1dd4552147c45a34154bc6f48b2053d5a216f3bc065b6ad276ece0b51aa6dd37`를 baseline AST와 비교했다. 변경된 기존 정의는 `compare_guards` 하나, 추가 정의는 `overflow_guard_prefix` 하나다. 모든 다른 정의와 module의 비정의 top-level AST node는 동일하다. 새 helper의 유일한 호출은 `compare_guards` line 396이다. helper에는 decorator, default argument, annotation의 import-time 평가가 없다. 결과는 `build/g3_acceptance/card-menu-proposed-delta-review.json`에 보존했다. 이때 active tool의 bytes는 아직 baseline SHA와 같았다.

[F] helper를 읽어 확인한 검증 범위: 선언된 전체 guard의 `a0a0` 시작과 실제 직전 C++ 출력의 `a0c2` 시작을 각각 fresh native CPU에서 실행한다. 원본 고정 ROM의 offset/CPU address `1000` WORD가 `4e75 RTS`인지 확인하고, 실제 native trace에 `1000`이 포함되며 최종 stop이 `a370`인지 요구한다. C++ 결과의 전체 16 register·PC·RAM·PVC·bank·순서 있는 ports·external read 수(0)를 native 결과와 비교한다. `a0c2` 재실행 결과는 원래 `compare_guards`의 실제 API 결과 tuple과도 정확히 같아야 한다. native SR는 읽지 않으며 public carry 값만 기록한다. 이전 native fault와 rollback의 동등성을 주장하지 않는다.

[U] 이 검토는 proposed source의 delta 및 proof 검사 조건에 대한 독립 확인이다. 수정된 공식 main의 성공 보고서는 아직 수용하지 않았다. 적용 후 source SHA/AST 재확인, 공식 전체 card-menu 재실행과 report hash, actual-loaded pin 목록으로 후속 항목을 완료한다.

## Scene-core guard 상수의 추가 제한 변경

[F] frozen source `tools/verify_animation_machine_scene_core.py`의 baseline SHA256은 `040a0512d8ce3b094ba461e6219ece8a2cbf7e165bf18523d7856b8d9f5c8c5a`이며 최초 card-menu 조사 때의 source SHA와도 같다. baseline 모든 module AST node, `GUARD_ERRORS` 전체 key/value AST와 load 위치를 `build/g3_acceptance/scene-core-dependency-review.json`에 보존했다. 전체 35개 local import/call graph 재검사 결과는 `scene-core-callgraph-review.json`(SHA256 `e0da9262963909285f222f6a57d2a89dc6583fe9a69954579d8b59143afe1b8b`)이다.

변경 제안은 `GUARD_ERRORS['guard-cond-index-negative-8000']` 한 값만 `UNSUPPORTED_MACHINE`에서 `'unsupported animation frame head h4 PC'`로 바꾸는 것이다. 메인은 원본 target `0x122d4`가 H4 cell `0x120c0 + 532`의 내부(532 mod 18 = 10)이며 fresh archived-phase probe가 정확한 H4 오류와 전체 public rollback을 재현함을 확인했다. guard는 계속 checked rejection이며 positive로 분류하지 않는다. 이 리뷰는 원본 의미 판단을 대신하지 않고 상수 변경의 영향 범위를 확인한다.

[F] scene-core module에서 `GUARD_ERRORS`의 load는 두 곳뿐이고 모두 `compare_guards` 안이다: baseline line 757의 `GUARD_ERRORS[label]`, line 770의 `sorted(GUARD_ERRORS)`다. 별도 alias 생성이나 외부 module의 dictionary 참조는 없다. 새 값은 key set·sort 결과를 바꾸지 않는다. `compare_guards`의 호출은 own `run` line 941 한 곳이며 다른 공식 verifier는 이 함수나 `run/main`을 호출하지 않는다.

다른 직접 importer는 세 개(`verify_animation_machine_input`, `verify_animation_machine_scene_update`, `verify_animation_machine_script_placement`)다. 이들은 변경되지 않은 `classify_carry`, `merge_phases`, `check_result`, `build_pvc`, `pvc_page`, `apply_initial_writes`, `computed_carry`, `rebuild_scene_inputs`와 scene SHA·consumer 상수를 참조한다. `GUARD_ERRORS` 또는 그 해당 값을 참조·alias·전달하거나 동적으로 조회하지 않는다.

[F] scratch proposal patch `build/f5_acceptance/negative-audit/scene_core_h4_guard_repair.patch`의 효과를 baseline AST와 비교했다. 전체 module AST node 개수와 다른 node는 같고, 단 하나의 assignment에서 정확히 해당 key의 value만 바뀐다. dictionary key 및 모든 다른 value AST는 동일하다. 예상 whole-file SHA256은 `f5c18f3518d0deae8c41fedff5c783b3ff5ffa20c860476e91c348511d9f7cd1`다. 결과는 `scene-core-proposed-delta-review.json`에 보존했으며 active frozen source는 아직 baseline bytes 그대로였다.

두 제안을 합친 최소 행동 재검증 범위는 **card-menu와 scene-core 공식 main 전체 실행 2개**다. 두 변경의 AST 범위 및 다른 입력의 불변이 적용 후 다시 확인되면 나머지 **33개 기존 성공 report**는 원래 hash/pin을 그대로 유지하고 source-delta 동등성 overlay로 연결할 수 있다. 이 두 변경 모두 다른 33개가 호출하는 함수·사용하는 상수 값을 바꾸지 않는다. whole-file bytes와 provenance SHA는 바뀌므로 33개를 새 source SHA로 재실행했다고 표현하거나 과거 pin을 새 hash로 바꾸면 안 된다. 적용된 source·완료된 35개 실제 report pin 목록·신규 2개 공식 실행 결과는 후속 리뷰에서 확정한다.
