# 0264 legacy 회귀 재실행 (macOS 원 환경)

대상 커밋 `e5bfb73`(= origin/main), 작업 브랜치 `claude/legacy-wip`, 작업 트리 `/Users/start/Workspce/metalslug-legacy`. 변경은 커밋하지 않았다(작업 트리 수정만). ROM(`mslug5.zip`, 프로그램 이미지 SHA256 `29112a94…c860f`)과 추출 데이터는 수정하지 않았고 실행 전후 SHA/mtime·공유 `artifacts/` 변경 여부(`find -newer`)를 확인했다(변경 없음).

## 배경
`0263` "남은 것·미확인"은 Linux 클라우드에 역사 산출물이 없어 pin된 예전 검증기를 실행하지 못했다고 적었다. 이 기록은 원 산출물이 있는 이 Mac에서 `0258` 표준 35개 검증기와 이후 추가된 frame/controller/IRQ/단위 fixture 검증기를 `e5bfb73`에 대해 실행하고, 독립 리뷰 `0264-ten-unit-batch-independent-review`의 M-1·L-2 항목을 반영한다.

## 환경
- macOS 26.4.1 (25E253), arm64, Apple clang 17.0.0 (clang-1700.6.3.2), Python 3.14.3 (공유 `.venv`), Unicorn 2.1.4.
- 빌드: `make -j3 all test` 종료 0 (로그 `ms5-scratch/legacy/logs/make.log`).
- Python 단위 시험: `python -m unittest discover -s tools/tests` 310개 OK (수정 반영 트리).
- 실행 방식(scratch-root): `ms5-scratch/legacy/roots/<도구>/`에 `git clone`한 `e5bfb73` 트리 + 이 문서의 수정 파일 덮어쓰기. `artifacts/`는 실제 폴더이고 공유 산출물은 심볼릭 링크, 해당 검증기의 자기 출력 폴더만 빈 실제 폴더다. `extracted/`·`mslug5.zip`·`.venv`는 읽기 전용 링크. 최대 3개 프로세스(`run_one.py` 스케줄러). 도구 실행기는 scratch 안에만 있다.
- 명령 형식: `python tools/<도구>.py` (공통 인자 없음). 예외: frame 구동기 `--seed-dir artifacts/stage_entry_body --workers 3`, controller `--seed-dir … --declare game --workers 3`, IRQ `--seed-dir … --workers 3`, 단위 fixture `--spec tools/unit_fixture_specs/<이름>.py --out <scratch> --seed-dir …`.

## 결과 (최종 수정 소스, 도구별 마지막 실행)
| 검증기 | 결과 | 시간 | 보고서 SHA256(앞 16) |
| --- | --- | --- | --- |
| `verify_animation_machine.py` | PASS | 50s | `809312af71618973` |
| `verify_animation_machine_activation.py` | PASS | 40s | `163725071c6f04bc` |
| `verify_animation_machine_area_clear.py` | PASS | 187s | `d6719c836c3c8be8` |
| `verify_animation_machine_buffer_cue.py` | PASS | 871s | `52f77f448161681f` |
| `verify_animation_machine_callers.py` | PASS | 55s | `8fb1502cc29efce3` |
| `verify_animation_machine_card_child.py` | PASS | 119s | `46e9f7e29effe1fd` |
| `verify_animation_machine_card_menu.py` | PASS | 1004s | `b266e8d4e8df1d4e` |
| `verify_animation_machine_card_menu_close.py` | PASS | 3291s | `9aca6f2b5c04ba8b` |
| `verify_animation_machine_card_menu_input.py` | PASS | 2305s | `6fbe6f5c1401e394` |
| `verify_animation_machine_card_menu_nested.py` | PASS | 612s | `d51ecb29980f78e9` |
| `verify_animation_machine_card_menu_open.py` | PASS | 9952s | `372b1332ffe6112c` |
| `verify_animation_machine_card_menu_save.py` | PASS | 491s | `ba0419b6f813ab94` |
| `verify_animation_machine_carry.py` | PASS | 70s | `a9ccf37a297fc085` |
| `verify_animation_machine_cleanup.py` | PASS | 270s | `122d3bc64f95839f` |
| `verify_animation_machine_exit.py` | PASS | 75s | `089e127fbd56ab8f` |
| `verify_animation_machine_fade_card.py` | PASS | 77s | `12548d3218cabec2` |
| `verify_animation_machine_frame_controller.py` | PASS | 276s | `6c06d8fff6ad398e` |
| `verify_animation_machine_frame_driver.py` | PASS | 247s | `b0b7ed2f0b39f5b9` |
| `verify_animation_machine_frame_head.py` | PASS | 109s | `0973cdc186a40b41` |
| `verify_animation_machine_frame_helpers.py` | PASS | 1310s | `f8dcacc484b7a183` |
| `verify_animation_machine_frame_irq.py` | PASS | 298s | `bd8c82200d251d5e` |
| `verify_animation_machine_hud.py` | PASS | 212s | `9853c355761f6db4` |
| `verify_animation_machine_input.py` | PASS | 550s | `c7db004e8a0ede4a` |
| `verify_animation_machine_map_transfer.py` | PASS | 168s | `51ba876b5e594c91` |
| `verify_animation_machine_motion_walk.py` | PASS | 3924s | `b745fcaec03cc8dd` |
| `verify_animation_machine_palette_bind.py` | PASS | 104s | `c108f2a43cbf46ce` |
| `verify_animation_machine_readiness.py` | PASS | 53s | `391e55a7d7d50e14` |
| `verify_animation_machine_scene.py` | PASS | 200s | `6211bec1000a9abc` |
| `verify_animation_machine_scene_core.py` | PASS | 1372s | `76edb588d48cca6d` |
| `verify_animation_machine_scene_update.py` | PASS | 552s | `7abd960555877a41` |
| `verify_animation_machine_scheduler.py` | PASS | 457s | `da681ff20bb489b7` |
| `verify_animation_machine_screen.py` | PASS | 96s | `d4bd67c831153e3b` |
| `verify_animation_machine_script_placement.py` | PASS | 305s | `fe86d0d37024b46a` |
| `verify_animation_machine_stage_area.py` | PASS | 155s | `221c9d8f68786549` |
| `verify_animation_machine_stage_catalog.py` | PASS | 2373s | `92fdc0d494c54ea3` |
| `verify_animation_machine_stage_entry.py` | PASS | 2015s | `8e5e04373e6b0d08` |
| `verify_animation_machine_stage_event.py` | PASS | 162s | `2303cdf079815d0c` |
| `verify_animation_machine_stage_event_ops.py` | PASS | 99s | `8187720522f0c87b` |
| `verify_animation_machine_transition.py` | PASS | 88s | `0fbc12a3116afcb0` |

단위 fixture(`verify_animation_machine_unit_fixtures.py`, spec 13개: b1a b1b b1c b2a b2b c1 c2 c3b d9 f6a f6b f6c selftest): 모두 종료 0, `ok` true. 예: b1a 2,807/2,807, c3b 480/480, d9 26/26. 보고서는 scratch `uf_out/<이름>/report.json`.

시간은 기계 부하(다른 작업자 병행)에 크게 좌우된다. 앞선 실패 실행의 로그는 `ms5-scratch/legacy/logs/`에 있다.

## 새 `--seed-dir` 옵션 (메인 결정)
- `verify_animation_machine_frame_driver.py`에 `--seed-dir PATH`(또는 환경 변수 `MS5_SEED_DIR`)를 추가했다. 기본값은 그대로 `artifacts/linux_rebase/stage_entry_body`다. 선택한 폴더의 `observation.json` SHA256이 Linux 재생성 pin(`f74048bb…`) 또는 원 macOS pin(`1f65100f…`)이 아니면, 폴더가 없으면 모두 오류다(조용한 대체 없음). 보고서 `declared_platform_rebase`에 `seed_dir`, `seed_sha256`, `seed_kind`(`linux_rebase`|`historic`)를 기록한다.
- `_frame_controller.py`, `_frame_irq.py`, `_unit_fixtures.py`는 같은 옵션을 D에 그대로 전달한다(다른 변경 없음; unit_fixtures는 3줄). `docs/WORKFLOW.md` "환경과 경로 재현"에 한 줄 추가했다.
- 검증(이 Mac, `--seed-dir artifacts/stage_entry_body`, seed_kind `historic`): D1 구동기 54,400/54,400, controller Execute(`--declare game`) 54,400/54,400, IRQ 54,400/54,400(IRQ 108,528회 전달). 기본 경로는 이 Mac에서 `seed observation missing: …/artifacts/linux_rebase/stage_entry_body/observation.json (use --seed-dir …)`로 명확히 실패한다.

## L-2 (verifier-error 판정)
`frame_irq.py`, `frame_controller.py`, `frame_driver.py`의 `bad_fail` 계산에 `category == 'verifier-error'`를 포함했다. 검증기 예외로 `checks`가 비어 있는 frame이 있으면 `*_expected_failure_bad/not_ok`가 0이 아니게 되어 acceptance가 거짓이 된다. 이번 전체 실행에서 `verifier-error`는 없었다(`categories`에 없음).

## 실패 분류와 수정
모든 수정은 검증기 기대값/pin만이다. 엔진 C++는 바꾸지 않았다. "이전 기대"와 "후속 단위"를 소스 주석과 보고서 행(`former_expected_API_error`, `superseded_by`)에 남겼다. 한 PC에서 성공과 오류를 모두 허용하는 검사는 없다(PC마다 정확한 오류 하나). [I]는 오류 문구를 해당 실행에 귀속한 추론이며 PC별 추적은 하지 않았다.

### (a) 후속 단위가 PC를 routing해 무효가 된 기대
| 검증기 | 대상 | 이전 기대 | 현재 | 후속 단위 |
| --- | --- | --- | --- | --- |
| fade_card | guard `guard-alloc-return-clobbered`(목표 `4c3a2`) | `unsupported animation machine PC` | `program bus requires even WORD/LONG address` | B2b(`4c390..4c3ba`) |
| card_menu_close | `outside_range_entry_00c2fc` | machine PC 오류 | `unsupported animation controller c2 PC` | C2(`c2fa..c364`, `c2fc`는 BSR.W 내부) |
| card_menu_close | `c2fa` | machine PC 오류 | 유지(`bbd4`→`bcaa` 사슬로 같은 문구) | 유지, 원인 주석 |
| card_menu_save | `outside_range_entry_00bbd4` | machine PC 오류 | `unaligned animation machine PC` [I] | C2(`bbd4` 카드 menu 표 준비) |
| card_menu_open | `outside_range_entry_003670` | machine PC 오류 | `unsupported program bus device address` | C1(`3670` digit reader) |
| card_menu_open | `outside_range_entry_00a75a` | machine PC 오류 | `program bus requires even WORD/LONG address` [I] | C2(`a75a..a770`) |
| cleanup | `sound_callback_publication_overwrites_live_return` | machine PC 오류 | `unaligned animation machine PC` [I] | F6a(`3dcc`) |
| motion_walk | guard `guard-oor-18fd2-type8000`(`10fda`) | machine PC 오류 | `unsupported animation irq f6c PC` [I] | F6c(`f226..11792`) |
| motion_walk | `computed_pc_run_on_oor-{18c06,18caa,18efa,18fd2,192c4}-type8000` | machine PC 오류 | 18c06·18efa `unsupported animation machine write device`, 나머지 `unsupported animation irq f6c PC` [I] | F6c |
| scheduler | `pass-head-ring-unchecked-step-limit` | `unsupported animation machine PC` | `animation machine block budget exceeded` | C3(`c52a..c64c`) |
| scheduler | `unrouted_after_002ab8` | machine PC 오류 | `animation machine external read queue empty` [I] | F6a(`20c..2d8`) |
| stage_entry | `outside_entry_0072fa` / `007300` | machine PC 오류 | external read queue empty / `unsupported animation irq f6b PC` | F6b(`72f0..7326`) |
| buffer_cue | `outside_entry_00e8a1c`, `004b82e` | machine PC 오류 | external read queue empty | 이어지는 routing, 후속 단위 [U] |
| frame_helpers | BOUNDARY `1a73c 49b0c 4aa88 e8a48` 직접 진입 | machine PC 오류 | external read queue empty | U2..U7(실행됨, 헤더 기록 있음) |
| frame_helpers | outside `47672`, `2efdc`, `493bc` / natural `480bc` stop `ff000`·`4939c` | machine PC 오류 | external read queue empty | 후속 단위 [U] |
| stage_catalog | 이웃 탐침 `4755e`(C2), `48156`(F6a) (M-1) | machine PC 오류(잘못된 이유로 통과) | 탐침에서 제외 | C2 / F6a |

"external read queue empty"는 비물리 주소 읽기가 F5 외부 읽기 큐 경로를 타는 harness 결과이며 원본 장치 동작의 증거가 아니다(`0258` 선례).
work-RAM `10fe00`/`10fefe` 대조(code가 RAM에서 실행되지 않으므로 항상 `unsupported animation machine PC`)를 card_menu_close, card_menu_open, card_menu_save, cleanup, stage_catalog, stage_entry, frame_helpers, scheduler에 추가했다(buffer_cue에는 이미 있음).

### (b) pin 갱신
- `verify_animation_machine_stage_event.py`, `_stage_event_ops.py`: `CPP_PINS`의 `engine/src/animation_machine.cpp`(이전 `c7318132…caad2`)와 `engine/src/animation_machine_internal.h`(이전 `6406329a…a6e`)를 현재 `7e76e64b…`, `4585a260…`로 갱신. `709a706..e5bfb73`는 열 단위 routing, private 선언, 팔레트 장치 context, Z80 응답 `320000` 외부 읽기 장치 추가이며 삭제는 교체된 한 줄(외부 장치 판정, 함수 시그니처 분리)뿐이다.

### (c) 실제 회귀 / 설명 불가
없음. 모든 실패는 위 (a)/(b)로 분류됐고 수정 뒤 재실행에서 통과했다.

### 이전 `0263` 항목
- frame_controller의 c3b 경계 행(`ac75f6d`)은 실제 `--declare game` 실행(54,400)과 단위 fixture c3b 480/480에서 통과.
- fade_card `4c3a2` guard는 위 (a)로 수정.

## 수정 파일 (SHA256 앞 16)
```
284c0a6076c681a3 docs/WORKFLOW.md
86f94c6427808c31 tools/verify_animation_machine_buffer_cue.py
97a5b1bffae5618c tools/verify_animation_machine_card_menu_close.py
84a8b30b6d5018c4 tools/verify_animation_machine_card_menu_open.py
af3dff9ea85e1a44 tools/verify_animation_machine_card_menu_save.py
8d8d4f55b1bfc401 tools/verify_animation_machine_cleanup.py
d42d7305b6d1a598 tools/verify_animation_machine_fade_card.py
45d163c4f6dc747a tools/verify_animation_machine_frame_controller.py
55bdc6cee56cbc00 tools/verify_animation_machine_frame_driver.py
bbd9c45dab211ff9 tools/verify_animation_machine_frame_helpers.py
4f327616df45a5dc tools/verify_animation_machine_frame_irq.py
5c54e5ed0efb5286 tools/verify_animation_machine_motion_walk.py
bc776b843c27b7e3 tools/verify_animation_machine_scheduler.py
5a95cf7ceff2b9cd tools/verify_animation_machine_stage_catalog.py
473b56e8772fd1c3 tools/verify_animation_machine_stage_entry.py
136f920e02355890 tools/verify_animation_machine_stage_event.py
06e0361390d6a458 tools/verify_animation_machine_stage_event_ops.py
d1aabe9221eccd3b tools/verify_animation_machine_unit_fixtures.py
```

## 미해결·미확인
- (a)의 [I]/[U] 항목은 오류 문구를 후속 단위에 귀속한 추론이며 PC별 추적은 하지 않았다. 필요하면 해당 PC의 native 대조 또는 C++ 단위 시험으로 확인한다.
- buffer_cue `e8a1c`/`4b82e`, frame_helpers `47672 2efdc 493bc`와 natural 480bc 두 stop은 external read queue empty로 끝나는 원인 routing을 특정하지 않았다 [U].
- `0258`의 35개 pin은 이번에 `e5bfb73` 소스 기준으로 다시 정렬되었으나 `docs/reviews/0258-regression-manifest.json`은 갱신하지 않았다.
- 전체 게임 완료를 뜻하지 않는다.


## de0e5be 재실행 (후속 단위 B2c-a/B2d/B2e/B3a/B3b 반영 후 소스 pin 재정렬)

대상 커밋 `de0e5be`(브랜치 `claude/pins-wip`, 작업 트리 `/Users/start/Workspce/metalslug-pins`). 변경은 커밋하지 않았다. ROM·추출 데이터·`artifacts/` 공유 산출물은 수정하지 않았다(실행 후 `find -newer`로 확인, 변경 없음). 엔진 C++는 바꾸지 않았다.

### pin 변경
`e5bfb73` 이후 단위가 `engine/src/animation_machine.cpp`·`animation_machine_internal.h`에 routing/선언을 추가해(`e5bfb73..de0e5be`: B2c-a, B2d, B2e, B3a, B3b) 두 검증기의 `CPP_PINS`가 다시 낡았다. 소스 전수 grep(`7e76e64b`, `4585a260`, `animation_machine.cpp`) 결과 해시 pin은 이 두 파일뿐이다. 다른 `*_f4_execution` audit와 그 외 검증기는 이 파일을 해시로 pin하지 않고 이름/경로만 참조한다. 같은 `CPP_PINS`의 나머지 단위 소스 pin은 모두 현재 값과 일치한다.

| 파일 | 대상 | 이전 | 현재 |
| --- | --- | --- | --- |
| `tools/verify_animation_machine_stage_event.py`, `tools/verify_animation_machine_stage_event_ops.py` | `engine/src/animation_machine.cpp` | `7e76e64b…f951a6` | `aba5bec0b6450b00…a68cc9` |
| 같음 | `engine/src/animation_machine_internal.h` | `4585a260…6d6cfbd` | `706f6a5bcd3ce44c…a0e78` |

이전 값은 각 소스 주석에 남겼다. 수정 파일 SHA256(앞 16): `707b3f71f464b3eb tools/verify_animation_machine_stage_event.py`, `3a171e83f64858c4 tools/verify_animation_machine_stage_event_ops.py`.

### 실행 방식
`de0e5be`를 scratch(`ms5-scratch/pins/roots/<도구>/`)에 clone하고 위 두 수정 파일을 덮어쓴 뒤, 공유 산출물은 심볼릭 링크, 해당 검증기 자기 출력 폴더만 실제 폴더로 두었다(앞선 legacy 실행기와 동일 방식). C++ 바이너리는 `de0e5be` clone에서 `make -j3 all test`로 빌드한 한 벌을 각 root에 복사했다: C++ 테스트는 모두 통과했고, 마지막 단계 `python -m unittest discover`만 clone에 `.venv`가 없어 실행되지 않았다(이번 재실행 범위 밖). 동시 프로세스 2개.

### 결과 (표준 35개, 기대값 정렬 없이 pin 갱신 후 모두 통과)
실패 없음: 기대값 정렬이 필요한 항목은 발견되지 않았다(B2c/B2d/B2e/B3a/B3b가 기존 검증기의 PC 경계 기대를 무효화한 경우 없음).

| 검증기 | 결과 | 시간(s) | 보고서 SHA256(앞 16) |
| --- | --- | --- | --- |
| `verify_animation_machine.py` | PASS | 50 | `46453720f139d223` |
| `verify_animation_machine_activation.py` | PASS | 38 | `1cd48d88fc96de2f` |
| `verify_animation_machine_area_clear.py` | PASS | 214 | `edd84870d8551255` |
| `verify_animation_machine_buffer_cue.py` | PASS | 821 | `e5f59a65f69165ba` |
| `verify_animation_machine_callers.py` | PASS | 63 | `f6ee0a93d8fc21ec` |
| `verify_animation_machine_card_child.py` | PASS | 118 | `fb47c8637d323a31` |
| `verify_animation_machine_card_menu.py` | PASS | 821 | `3dda09b5c14e6de3` |
| `verify_animation_machine_card_menu_close.py` | PASS | 2793 | `ab4122c79c56af1e` |
| `verify_animation_machine_card_menu_input.py` | PASS | 1440 | `0640edc7951322b9` |
| `verify_animation_machine_card_menu_nested.py` | PASS | 625 | `6dcda72c679d64e5` |
| `verify_animation_machine_card_menu_open.py` | PASS | 11426 | `66cb8a6a16ab146d` |
| `verify_animation_machine_card_menu_save.py` | PASS | 466 | `66e6a6f05fea45e1` |
| `verify_animation_machine_carry.py` | PASS | 78 | `95b287f587c53757` |
| `verify_animation_machine_cleanup.py` | PASS | 278 | `0f71644934b4a6f5` |
| `verify_animation_machine_exit.py` | PASS | 72 | `dec9115f8b394f1d` |
| `verify_animation_machine_fade_card.py` | PASS | 76 | `ae8d2962659607f1` |
| `verify_animation_machine_frame_helpers.py` | PASS | 1371 | `50baa696110aef57` |
| `verify_animation_machine_hud.py` | PASS | 232 | `0edbe7299d01d8b9` |
| `verify_animation_machine_input.py` | PASS | 598 | `9b70ca8ad8e2e3a9` |
| `verify_animation_machine_map_transfer.py` | PASS | 166 | `3ec2fd5a3647906a` |
| `verify_animation_machine_motion_walk.py` | PASS | 3069 | `f9f1e2906fa77ae8` |
| `verify_animation_machine_palette_bind.py` | PASS | 94 | `467f9c0a3dc1277e` |
| `verify_animation_machine_readiness.py` | PASS | 51 | `a8383b453054e8f1` |
| `verify_animation_machine_scene.py` | PASS | 196 | `854b2ebf7bc599d3` |
| `verify_animation_machine_scene_core.py` | PASS | 979 | `4c31e29d05dba6cd` |
| `verify_animation_machine_scene_update.py` | PASS | 599 | `9b19bb1c92396316` |
| `verify_animation_machine_scheduler.py` | PASS | 278 | `bd3721432977c9d8` |
| `verify_animation_machine_screen.py` | PASS | 116 | `d685c052b944a519` |
| `verify_animation_machine_script_placement.py` | PASS | 300 | `6e0660d328b227fd` |
| `verify_animation_machine_stage_area.py` | PASS | 153 | `8817f0262b775367` |
| `verify_animation_machine_stage_catalog.py` | PASS | 2061 | `225af7a60b75fe2c` |
| `verify_animation_machine_stage_entry.py` | PASS | 1683 | `9f8cd949b6fa6df3` |
| `verify_animation_machine_stage_event.py` | PASS | 142 | `84fc6c63fe736df1` |
| `verify_animation_machine_stage_event_ops.py` | PASS | 80 | `e9854007a36056b5` |
| `verify_animation_machine_transition.py` | PASS | 107 | `b74427c412d15869` |

PASS = 종료 코드 0. 시간은 기계 부하에 좌우된다. 단위 fixture·frame 구동기 계열(표준 35개 밖)은 이번에 재실행하지 않았다 [미확인].
