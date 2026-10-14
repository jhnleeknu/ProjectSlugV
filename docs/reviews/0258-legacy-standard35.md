# F4/F5 병합 뒤 기존 35개 검증기 재인수

대상 실행부는 `b8502bfaa8c6bebd6f02d79a9be46b16543cc289`의 C++ 소스다. 이 기록은 기존 검증기의 기대 오류·pin을 현재 추가 라우팅/API 계약과 대조하고 현재 소스에서 재실행하는 작업이며 새 controller/b-unit 구현은 아니다. 전체 게임 완료를 주장하지 않는다.

## 변경 근거

- base/activation/cleanup/hud/exit/readiness/map_transfer/palette_bind/scene/screen/transition의 `deac` 입력 또는 live 반환은 여전히 유효 block 시작이 아니다. H8 라우팅 범위에 들어가는 interior PC이므로 오류는 `unsupported animation frame head h8 PC`다. 기존 전체 public 출력 rollback 검사는 유지했다.
- HUD의 synthetic A5와 map_transfer의 synthetic A0가 만드는 비물리 read 주소는 F5의 외부 read queue 경로를 탄다. legacy harness의 queue가 비었으므로 정확한 오류는 `animation machine external read queue empty`다. 이를 원본 장치 동작의 증거로 세지 않는다.
- card_menu의 기존 `outside_range_entry_003902`는 이제 H2의 유효 진입점이다. 원본 CPU 주소 `003902`, canonical 프로그램 파일 오프셋 `003902`의 바이트 `3600` (`MOVE.W D0,D3`)를 readonly 원본에서 fresh Unicorn M68000으로 실행했다. 16R/PC와 C++의 전체 RAM/PVC/bank/ports를 확인한다. public carry는 소스 분류 `Unknown`(0)이고 native SR은 읽지 않는다.
- 같은 frozen legacy 상태로 원본 string/glyph/menu 경로를 계속 실행하고 `002ac0`의 `4e90` (`JSR (A0)`) 직전에 멈춘다. C++도 같은 stop으로 성공하며 16R/PC/RAM/PVC/bank와 순서 있는 ports가 같다. live A0는 `92bdcb15`로 홀수다. full public 호출은 정확히 `animation fade card odd JSR target`로 실패하고 모든 public 출력을 보존한다. 이는 원본 CPU 예외 rollback 동등성 주장이 아니다. 이 새 prefix 근거는 `negatives_superseded_by_later_card_menu_cores.h2_string_entry_prefix`에 포함한다.
- stage_event/stage_event_ops의 `0c89a1f` 대비 `b8502bf` router/internal-header diff는 N33/N34/N35와 H2/H3/H4/H8의 라우팅·carry-preserving PC 목록·private 선언 추가다. 기존 pinned unit 실행 소스 바이트는 그대로다. 두 검증기의 해당 router/header pin을 이 검토 후 갱신했다.

원본 canonical 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. CPU 주소와 파일 오프셋은 위 항목에서 따로 명시했다. 원본 ROM·immutable native 관측·runtime resource를 수정하지 않는다.

## 검증 경로와 실행 범위

`build/legacy_acceptance/targeted_preflight.py`는 immutable native report의 RAM/PVC/초기 레지스터를 hash 확인하여 기존 negative 함수만 실행한다. activation trace의 `pcs/events`를 별도 trace.json에서 읽고, card_menu source의 instruction 키는 `cpu_address`를 사용한다. PVC 제외용 digest 함수는 입력 크기를 줄이므로 public API 입력에 사용하지 않는다. targeted 결과는 API-only이며 full native 비교를 주장하지 않는다.

35개 공식 main은 `docs/reviews/0256-regression-manifest.json.standard_reports`의 도구 목록을 사용한다. `build/legacy_acceptance/run_standard35.py`는 readonly native/runtime 링크를 입력으로 두고 각 verifier의 실제 main을 실행한다. 실행 출력은 이 worktree의 real `artifacts/*_execution`/`*_verify` 디렉터리다. 공유 보고서를 덮어쓰지 않는다. heavy open/close는 한 worker에서 순차 실행하고 나머지는 다른 worker에서 순차 실행한다.

시작 전에 engine C++/header와 35개 검증기의 AST-recursive local import Python 파일을 freeze하고 각 도구 종료 및 전체 종료 때 비교한다. source commit, source/변경 diff SHA, report SHA, 로그 SHA, 종료 코드, 실행 시간, free storage를 local manifest에 기록한다. audit 도구와 진행 문서는 실행 source freeze에 포함하지 않는다. 출력은 기본적으로 모두 보존한다. 역사 출력 크기 합은 약 16.14 GB이며 시작 시 free storage는 약 35 GiB다.

원 frozen 35개 main은 모두 실행됐다. `build/legacy_acceptance/standard35-manifest.json`은 31 pass와 아래 네 stale expectation 실패, 517개 source pin의 실행 전/후 동일성을 기록한다. driver의 마지막 all35 assertion 실패는 이 네 실패 때문에 발생했고 예상 밖 실패는 없었다. 이후 정확히 네 검증기 수정만 적용하여 네 공식 main을 모두 재실행했다. 최종 수용은 31개 역사 실행과 네 replacement 실행을 명시적인 source delta overlay로 연결한다.

## full run에서 확인한 추가 legacy guard 변경

frozen 35개 실행 중 `verify_animation_machine_card_menu.py`는 원본/CPP positive matrix 비교를 완료한 뒤 `guard-overflow-rts-unsupported-target`의 옛 실패 기대에서 종료 1이었다. 실제 public 출력은 stop `a370` 성공이다. 원본 H1의 CPU 주소 `001000`, 파일 오프셋 `001000`에 있는 `4e75` (`RTS`)가 현재 실행된다. 옛 native observer는 이 주소에서 `unsupported_code_target` guard로 멈췄다.

소스를 변경하지 않고 전체 guard 10 label을 probe했다. 이 label만 새 positive가 됐고 나머지 negative와 기존 superseded positive는 현재 분류와 같았다. 새 원본 prefix는 두 fresh readonly Unicorn M68000에서 각각 선언 whole 입력 `a0a0` 및 저장된 guard phase 입력 `a0c2`로 시작해 `1000` RTS → `c2a8` → `a2b8` → `c2ba` → `a370`을 실행했다. C++와 16R/PC/RAM/PVC/bank 및 순서 있는 ports가 같다. native SR은 읽지 않았다. `build/legacy_acceptance/card_guard_probe/verification.json`과 `helper_validation/verification.json`에 두 시작점의 근거가 있다.

적용한 수정 patch는 `build/legacy_acceptance/card_menu_guard_repair.patch`다. 변경은 `compare_guards()`의 한 special case와 순수 helper `overflow_guard_prefix()`뿐이다. import·constant·module 부작용이나 기존 positive comparison 함수는 바꾸지 않는다. 전역 freeze를 유지한 채 35개 원 실행을 끝냈고, 독립 AST 검토 뒤 아래 네 patch만 적용하여 해당 네 verifier 전체를 새로 실행했다. 성공한 다른 31개 원 report는 원래 source/pin으로 보존한다. 이전 whole-file pin이 새 card_menu 소스와 같다고 주장하지 않는다. 독립 delta acceptance가 실제 호출 경로의 영향과 provenance 한정을 명시한다.


추가 frozen 실행에서는 scene_core, script_placement, stage_area의 과거 negative 기대도 현재 additive 실행 범위와 달랐다. source freeze가 끝나기 전에는 수정하지 않았고, 실패한 원 출력·로그·receipt를 보존했다.

- scene_core의 `guard-cond-index-negative-8000`는 target `0122d4`에서 정확히 `unsupported animation frame head h4 PC`로 실패하고 전체 public rollback을 유지한다. H4 시작 `0120c0` 대비 offset 532, stride 18의 residue 10인 interior다. 수정은 `GUARD_ERRORS` 한 값뿐이다.
- script_placement의 outside 입력 `003db2`는 현재 H1의 leaf 진입점이다. readonly 원본에서 fresh 실행한 `MOVEQ/BTST`와 `RTS` 이후 저장 반환 `01a296`부터 최종 stop `ff000`까지 C++와 16R/PC/RAM/bank/순서 있는 ports/외부 read 수를 비교한다. 시작 PVC 8192바이트는 정확히 같게 초기화한다. 반환 뒤 원본 경로의 14개 PVC WORD write를 기존 독립 `fold_device` 모델에 적용한 전체 PVC/bank가 C++와 같다. raw native PVC의 `ff8/ff9`는 장치 모델 표현이 다를 수 있으므로 raw 8192바이트 동일성을 주장하지 않는다. 나머지 주소는 folded image와 같다. `003db4`는 정확한 H1 interior 오류와 전체 rollback을 확인한다. 다른 10개 outside 입력 분류는 그대로다. 수정은 `negatives()`와 새 순수 helper이며, 새 local Python 의존성·Unicorn wrapper·native library의 import 전/실행 후 hash를 helper에 기록한다.
- stage_area의 이웃 입력 `b481e/b4a2a/46f52/1bdde`는 현재 H1 경로에서 정확히 `animation machine external read queue empty`로 실패한다. 전체 public rollback과 별도로 fresh 원본/CPP prefix `EA4`의 404개 ordered ports 및 `EAA`의 첫 `3c0006` WORD read를 확인한다. 수정은 `reject_one()`과 새 순수 helper다. native hook count에는 stopped PC도 포함됨을 metadata에 명시한다.

script_placement scratch 검증은 659개 호출(357 negative, 264 zero 포함), stage_area scratch 검증은 719 negative/10 consumer/462 zero 및 기존 RNG/F3b API 확인을 통과했다. 이 scratch 검증은 공식 full main 대체가 아니다. 뒤의 post-freeze 네 full rerun 통과가 최종 수용 근거다. 독립 AST 검토는 네 변경의 범위와 다른 31개 도구가 해당 변경 함수/값을 호출하지 않는다는 사실을 확인했다. 역사 whole-file source pin을 현재 수정 소스와 같다고 주장하지 않고 명시적인 delta overlay로 연결한다.

네 failed 실행 폴더는 원본을 바꾸지 않고 `build/legacy_acceptance/original-failures/`에 복사했다. 각 inventory는 원본 복사 전/후와 보존본의 모든 파일 SHA256·크기가 같음을 확인한다. card_menu 48,903개 파일(1.123 GiB), scene_core 3개, script_placement 3개, stage_area 6개를 보존했고 symlink는 없었다. 원래 `.result.json`과 로그도 그대로 유지한다.

post-freeze 실행 도구 `build/legacy_acceptance/run_replacements.py`는 original35가 정확히 31 pass + 위 네 failed tool이며 source hash가 전부 유지됐는지 gate했다. 네 공식 CLI main을 기본 output 경로·조건으로 두 worker에서 실행했고 `reruns/<tool>.result.json`에 실행 명령·시간·return code·log/report SHA와 source/runtime input의 실행 전/후 hash를 기록했다. 완성 report 복사본 `reruns/<tool>.verification.json`은 기본 report와 hash가 같음을 확인했다. immutable native 입력은 원본 report의 선언된 입력과 verifier 내부 manifest 확인을 함께 사용한다. 역사 own generated outputs는 runtime input으로 오인하여 pin하지 않고 앞의 별도 보존 inventory로 기록한다.


## 최종 결과

최종 verifier source cut은 `668e142`다. 네 수정 파일은 `delta-applied.json`의 독립 검토 candidate SHA와 정확히 같으며, 나머지 frozen source는 그대로다. ROM canonical SHA는 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`로 유지됐다. 엔진은 이 작업에서 수정하지 않았다.

| 공식 replacement main | 종료 | 시간(초) | full 비교 범위 | 실행 전/후 input pin |
|---|---:|---:|---|---:|
| card_menu | 0 | 878.992 | 95 cases, 2,405 split, 4,612 carry probes, 111 controls | 30,994 동일 |
| scene_core | 0 | 765.857 | 410 cases, 19,011 split, 36,944 carry probes, 393 controls | 1,165 동일 |
| script_placement | 0 | 287.419 | 658 cases, 5,475 split, 10,890 carry probes, 663 controls | 1,132 동일 |
| stage_area | 0 | 183.292 | 3,695 frames, 63,538 split phases, 80,756 carry probes | 555 동일 |

네 receipt는 `build/legacy_acceptance/reruns/verify_animation_machine_<name>.py.result.json`이며 명령·return code·실행 시간·source identity·input before/after map·log/report hash를 포함한다. 네 report 복사본과 기본 output report는 hash가 같다. 원 35개 로그와 성공한 원 31개 report의 hash를 마지막에 다시 확인했다. main 통합 manifest는 이 31개 중 24개 exact current와 7개 영향 없는 source delta 적용 기록을 구분하고 네 replacement를 더해 35개 수용을 기록한다. 35개 전부를 최종 whole-file source epoch에서 새로 실행했다고 주장하지 않는다.

card_menu의 두 overflow fresh native prefix와 H2 prefix가 최종 report에 포함됐다. 보존한 preexisting 출력 48,903개 파일은 rerun 뒤에도 모두 SHA256가 같고 missing/changed가 없다 (`reruns/card_menu-preexisting-output-comparison.json`). scene_core의 수정 guard는 phase와 whole-step 모두 정확한 H4 오류 및 전체 rollback을 확인했다. script_placement의 `3db2`는 API-only=False이고 full PVC fold와 before/after helper provenance가 모두 통과했다. stage_area 네 수정 negative는 exact queue error·전체 rollback·404-port prefix를 모두 통과했다. native CPU exception rollback이나 native CCR 동일성은 주장하지 않는다.

`build/legacy_acceptance/post-rerun-validation.json`은 최종 report/log/source pin와 위 native 증거 필드를 재확인한 기록이다. 최종 free storage는 약 17.27 GiB였다. 이 기록은 기존 35개 legacy 검증기의 현재 추가 라우팅 인수 완료를 뜻하며 전체 게임 목표 완료를 뜻하지 않는다.
