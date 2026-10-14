# PVC 관측기 입력 경로 이식 리뷰

기준 커밋: `0caa22c` (`origin/main`과 같은 게시 체크포인트). 작업 브랜치: `claude/projectslugv-work-cycle-yout6u`. 대상은 `docs/WORKFLOW.md`가 남은 과제로 적은 PVC 관측기(`tools/observe_animation_machine_pvc_banks.py`)의 기계별 고정 입력 경로(`/Users/start/Workspce/metalslug-input`, `artifacts/reference`) 이식이다. Claude 클라우드 세션에는 ROM·추출 데이터·과거 artifacts가 없어서 ROM 없이 할 수 있는 이 단위를 골랐다.

## 역할 분담
- 메인(Claude Opus 5.5): 단위 선정, 작업 계약 확정, diff 리뷰, 통합, 문서화를 맡았다.
- 구현: Claude 서브에이전트(Sonnet)가 계약대로 구현과 테스트를 맡았다.
- 독립 리뷰: Claude 서브에이전트(Opus)가 읽기 전용으로 검토했다.
- effort는 세션의 Agent 도구가 정하며 별도로 지정하지 않았다. 외부 `claude` CLI를 실행하지 않아 `--effort` 지정이 적용되지 않았다.

## 경과
1. 1차 구현(`93261ed`): 관측기 본체에 `--input-tree`·`--reference-dir`를 직접 추가했다. 메인 리뷰와 테스트 271개는 통과했다.
2. 독립 리뷰가 HIGH 문제를 찾았다. 본체 파일의 SHA-256 `86ebf962…`를 세 도구가 assert로 pin한다.
   - `tools/observe_animation_machine_frame_head.py:56`, `:1155`
   - `tools/verify_animation_machine_objects_g2.py:56`
   - `tools/verify_animation_machine_stage_area.py:990`
   g1·rng_f4 등도 이 SHA를 보고서 입력으로 기록하므로, 본체를 수정하면 기존 인수 도구가 실패하거나 결과가 흔들린다. 메인이 SHA와 세 pin을 직접 확인했다.
3. 재설계: 본체를 `0caa22c`와 바이트 단위로 같게 되돌렸다(sha256 `86ebf962e3b83eef6882c1f96845c117edfa735c3137960b1cbda6623768d3a0`). 이식 기능은 새 wrapper `tools/run_animation_machine_pvc_banks.py`로 옮겼다.

## 최종 변경
- `tools/run_animation_machine_pvc_banks.py`(신규) 동작:
  - `--input-tree`와 `--reference-dir`를 받는다. 기본값은 과거 경로다.
  - 필요한 다섯 파일을 확인하고, 없으면 누락 경로 전체를 표시하고 출력·ROM 접근 전에 중단한다.
  - 성공하면 본체의 module 전역(`INPUT_TREE`, `INPUT_ROUTING`, `INPUT_BUS`, `REF_PVC`, `REF_NEOGEO`)과 `tool_pins`를 교체한다. 교체한 `tool_pins`는 키 이름과 순서가 원래와 같고, 참고 소스가 저장소 밖에 있어도 키는 `artifacts/reference/<name>`이다.
  - 본체는 `fork` context를 쓰므로 Pool 작업자가 교체된 전역을 이어받는다.
  - 실행 후 `<out>/input_locations.json`에 wrapper·본체 SHA, 입력 위치, `observation.json` SHA를 기록한다.
- `tools/tests/test_observe_pvc_banks_paths.py`(신규 7개) 항목:
  - 본체 SHA guard와 기본값
  - 인자 전달
  - 전역 설정 및 누락 시 전역 불변
  - 저장소 밖 임시 경로의 pin 키·해시
  - `Path.read_bytes`를 mock한 원래 `tool_pins`와의 dict·순서 동일성
  - 잘못된 경로가 출력 폴더 생성 전에 실패하는지
- `docs/WORKFLOW.md`: PVC 관측기 경로 안내를 wrapper 기준으로 갱신했다.

## 검증
- 저장소 고정 MAME 참고 소스(`tools/fetch_reference.py`)를 받은 뒤 기준선 `.venv/bin/python -m unittest discover -s tools/tests`: 266개 통과. 참고 소스가 없으면 `test_cmc_gfx` 1개가 오류다.
- 변경 후 같은 명령: 273개 통과. `py_compile`과 `--help` 확인.
- `sha256sum tools/observe_animation_machine_pvc_banks.py` = 위 pin 값.
- C++ 엔진은 바뀌지 않아 빌드를 다시 하지 않았다.

## 미확인·제약
- ROM·seed 관측(`artifacts/stage_entry_body/observation.json`)이 없어 wrapper로 본체 전체를 실행하지 못했다. 실제 관측 재현은 ROM과 병합 트리가 있는 컴퓨터에서 해야 한다.
- 상대 경로 입력은 resolve하지 않고 주어진 문자열 그대로 기록한다.
- 본체 내부 LIMITATIONS 문구의 `HEAD a4e9253`은 과거 기본 트리 기준이다. 다른 트리를 쓰면 실제 위치는 sidecar로 확인한다.
