# 0258 — main verifier 변경 독립 검토

대상: `b8502bf` 기반 작업 트리의 `verify_animation_machine_objects_g1.py`, `verify_animation_machine_objects_g2.py`, `verify_animation_machine_scheduler_rng_f4.py`와 두 `audit_*f4_execution.py` 변경. 범위는 새 provenance 기록과 비교, G2 guard tightening, 현재 matrix cardinality 및 audit receipt와의 상호작용이다. 엔진·도구·보고 파일은 수정하지 않았으며 대규모 실행을 새로 수행하지 않았다. 별도 요청으로 신규 `acceptance_provenance.py`를 구현했고 그 구현은 메인이 검토했다.

## 확인한 실행 증거

검토 시작 시 실제 보고:

- G1 `execution.json` SHA256 `b3f264599bb94c0f54f7a62d9864220083067c5f9befef56b85a24da72190ab1`: 전체 4,747 rows, equality 4,683 / checked boundary 55 / native step limit 8 / invalid declared flag 1. 당시 source/header input hash는 현재 파일과 일치했다.
- G2 `verification.json` SHA256 `6f73a5f6e6ab71156fe0bc86abfe4600d1db6d05348f05590733f7173d8d103f`: full requested matrix. 새 guard 비교는 `expected_error_ok()`와 preserved 상태를 함께 요구하며 기존 blanket `UNSUPPORTED_MACHINE` fallback을 제거했다.
- RNG `verification.json` SHA256 `13b409a9432f628605027d58f0bf965b7b8793f90c187dba131ae57154b5e8f9`: 136 complete + 5 odd-JSR native-end + 1 unaligned native-end; 일반 54,400 passes / 412,067 nodes, answer-00 2,400 / 19,936. audit의 현재 수치와 일치한다.

이 SHA들은 helper 통합 전 보고의 식별자다. helper 통합 후 affected full run은 메인이 다시 수행하고 있으며 최종 수용 기록은 그 재실행 보고를 사용해야 한다.

## 발견 및 조치

### P2 — 현재 equality 수치와 역사적 baseline 필드 구분

objects audit는 equality 4,683을 검증하면서 receipt의 `original_execution_equal_rows`에는 4,657을 기록했다. 실제 당시 `acceptance.json`에서도 두 수치가 함께 확인되어 현재 수치로 읽을 수 있는 모호함이 있었다. 메인이 `historical_baseline_execution_equal_rows=4657`로 이름을 분명히 하고 `execution_equal_rows=expected['execution-equal']`을 추가했다. 변경된 소스에서 확인했다. 이는 실제 equality row를 늘린 수정이 아니다.

### P2 — 새 전체 provenance claim에 빠진 활성 dependency

G1의 새 명시 목록에는 실제 Env ROM loader인 `disassemble_program.py`, program manifest 및 native Unicorn 구현이 빠져 있었다. G2의 새 pin에는 같은 loader/manifest/oracle과 실제로 읽는 여섯 unit contract, F3 contract, stage-entry seed tree, scheduler/RNG observation이 빠져 있었다. 특히 `contracts`는 `G2.UNITS[u]['sha']` 상수를 돌려주어 자체적으로 마지막 시점의 contract byte를 다시 읽지 않았다. compiler는 version 문자열만 확인했다. 현재 보고의 실행 결과가 틀렸다는 증거는 없지만 `all_inputs_unchanged`의 범위를 실제 읽은 입력으로 충분히 뒷받침하지 못했다.

메인이 요청한 신규 helper는 명시 entry에서 AST-local imports를 재귀적으로 추적하고 자기 소스, program manifest, interpreter/compiler executable SHA와 version, Unicorn/Capstone Python wrapper 및 native library를 포함한다. 명시 data file/tree는 실제 byte hash와 tree membership을 반환한다. G1은 실행 전후 helper snapshot을 비교하고, G2는 `pins()`의 dependencies에 실제 외부 데이터를 포함한다. RNG는 F3 contract와 manifest를 추가한다. 두 post-audit도 기록된 dependencies를 fresh snapshot과 비교한다. 실제 갱신된 callsite와 최종 비교 소스를 읽어 확인했다.

G2 외부 data 목록은 다음과 같다:

- `G2.contract_path(u)` — 17, 18, 19, 20, 21, 22의 여섯 contract
- `S.F3_CONTRACT`
- `S.SEED_DIR` 전체 tree — stage-entry 원본 seed
- `G2.SCHED_DIR/observation.json`
- `G2.RNG_DIR/observation.json`

원래 G2 `NATIVE_DIR` full tree는 별도 pin을 유지한다. scheduler/RNG의 전체 seed tree는 현재 `make_run()` 입력이 아니다. `load_records()`는 해당 observation만 읽고 시작 RAM은 stage-entry seed에서 얻으므로 그 두 전체 tree를 불필요하게 추가하지 않았다.

G1의 `Env()`가 먼저 읽는 01..07 contract는 `parse_contract()`에서 byte SHA가 고정 `CONTRACT_SHA[u]`와 같은지 검사한다. 이 observer 소스 및 상수는 helper 초기 snapshot에 들어가고, 뒤이어 기존 flat input pins가 모든 contract를 execution 전에 고정한다. 나머지 contract coverage는 이 flat pin 이후 계산한다. 기존 guard를 확인했으며 이 읽기 순서에 별도의 미해결 finding을 남기지 않는다.

## 작은 검증과 남은 범위

helper의 반복 snapshot 동일성, local sibling/address_map import 추적, helper 자체 및 두 native library 포함을 확인했다. data file 추가/제거, imported sibling 변경은 snapshot을 바꾸고 명시 missing data는 예외로 거부했다. 실제 G2 경로 목록으로 snapshot을 읽어 loader/manifest/F3·six contracts와 stage-entry tree 포함을 확인했다(542 file pins). 이 검증은 임시 파일과 read-only snapshot을 사용했으며 ROM·native 관찰·기존 보고를 수정하지 않았다.

header provenance의 새 audit는 전체 공개 header와 현재 내부 header 집합을 execution report에서 얻어 실제 SHA 및 집합을 비교한다. 과거 sanitizer anchor를 필수 입력에서 제거해도 현재 실행의 header 증거가 유지된다. 이미 존재하는 output/acceptance 경로를 덮어쓰지 않는 정책은 이번 변경의 회귀로 분류하지 않았다.

현재 소스 변경에서 위 concrete provenance/receipt 문제의 조치는 확인했다. helper를 포함한 새 full run 및 post-audit 결과 확인은 메인이 담당한다. 기존 G2 black-box/guard 모델의 한계, declared pass-only RNG 모델과 native-end exception 상태의 범위는 그대로 별도 한계이며 이 검토로 성공 실행으로 승격하지 않는다.
