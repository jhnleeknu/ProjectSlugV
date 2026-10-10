# `480bc` 프레임 helper 묶음 U1: C++ 실행 검증 기록

대상 커밋 77b8dbe(카드 메뉴 core + `480bc` U1 frame helper core, detached worktree). 구현·원본 동등성 완료 보고가 아니라 통제된 fixture에서의 native 대조 기록이다. 원본 ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(고정 CPU 주소 = 파일 오프셋). 계약 `animation-machine-frame-helpers-u1-contract.md` SHA256 `785c3fba8bf05bd405ad8c0898738504367ed0c3195ffb9aa80a0a3774c861e0`.

## 입력과 도구

| 항목 | SHA256 |
| --- | --- |
| native 관찰 `artifacts/animation_machine_frame_helpers_native/observation.json` | `bf7525b04f9735da44958b24fdf9be2f7d67b7f80fd7b53015b0c7645a949916` |
| 관찰 도구 `tools/observe_animation_machine_frame_helpers.py` | `7c6c65e09a2ffea2fc436086a441d7aa158b267df4c1f429a432161acc4a31d2` |
| 검증 도구 `tools/verify_animation_machine_frame_helpers.py` | `b48acb94ef27170cd9475b489e92178456e380065697f6dcb70819e1902ddce5` |
| 보고서 `artifacts/animation_machine_frame_helpers_execution/verification.json` | `737f1c0d9f33002545285d4ac15afb45b2405bc9e06b8d8c354b55d19dc60a8b` |

검증 도구는 관찰 도구를 실행하지 않는다(고정 입력). C++ 소스·테스트·관찰 도구는 수정하지 않았다.

## 방법(card menu verifier와 같은 비교 방식)

- 시작 상태: 관찰이 선언한 stage-frame seed 11개(`verify_stage_frame.smoke()` 7개 + `artifacts/stage_frame` 기록 출력 4개)를 이 검증 도구가 직접 재구성한다. 각 seed의 입력 RAM SHA, 레지스터, 반환 LONG `2ac2`(A7=`1feffc`), PVC 페이지, bank 상태가 관찰의 fixture(`initial_RAM_sha256`, `initial_PVC_sha256`, `seed` provenance)와 정확히 한 seed로 일치함을 assert한다. 행별 레지스터·A7 차이(30행)는 fixture에 기록된 선언 값으로만 허용하고 보고서에 키 목록을 남긴다. A5=`108000`.
- 분할 실행: native split 단계마다 C++를 같은 stop으로 실행하고 64KiB RAM 전체, D0-D7/A0-A7, PC, PVC, bank, 순서 있는 port 바이트, 외부 읽기 횟수, status를 native 출력과 비교한다. 두 번째 이후 단계는 직전 실제 C++ 출력에서만 재개하고, 선언된 host 변경(PC 재지정, 반환 LONG, RAM fixture; 첫 단계에만 존재)만 얹는다. native 입력 레지스터는 assert로만 쓰인다.
- 연속 대조: 단계 시작 상태에서 한 번에 끝 stop까지 C++를 실행해 분할 결과 및 native 연속 대조와 같음을 확인한다(182회).
- 정답이 `28ac`/`28a8`에서 멈추는 native 분할(기존 `289e` executor는 입구 block에서 C를 정해 곧바로 복귀하므로 C++에는 그 PC의 block이 없다)은 다음 phase와 합쳐 비교한다(53회, 이벤트·ram_after는 합산·마지막 값). 이는 비교 단위만 바꾼다.
- status: native는 대기(`waiting`)를 한 번도 기록하지 않았다(3952 phase 모두 False). `3aea` stop은 split 체크포인트일 뿐이므로 공용 `check_result`의 `3aea ⇒ status 1` 가정 대신 native `waiting` 값 기준으로 status 0을 요구했다.
- C 비교: native SR은 읽지 않는다. 실행 PC 열을 원본 opcode로 훑는 분류(ORI/ANDI CCR 알려진 값, `493a2` ANDI.W #1,D0 = Clear, `289e`에서 CMPI.L 뒤 BEQ가 `28ac`로 갈 때 Clear/ORI 경로 Set, FLOW_ONLY만이면 보존, 그 외 Unknown)과 C++ carry를 매 단계 비교했다. `493a2` 외의 ANDI.W는 보수적으로 Unknown이다(`b481e`의 ANDI.W가 Unknown으로 나옴을 확인).
- carry probe: consumer가 아닌 모든 단계를 알려진 입력 C=1, C=2로 다시 실행해 출력(carry 제외)이 같고 carry가 분류와 같음을 확인했다(7040회). `4765c`/`b4a38`/`b4a6c` consumer 단계(163회)는 입력 C를 뒤집으면 반대 분기 PC로 가고 RAM·PVC가 변하지 않음을 확인했다.
- 외부 입력: native 행 1개만 external=1. 외부 읽기 합계 2회(native와 일치).
- 원본 프로그램 읽기 감사: 고정 영역 117회, bank 읽기 18회를 현재 bank로 재구성해 ROM 바이트와 대조(PVC 쓰기 0).

## 결과(두 번 실행 결과가 같아야 함)

| 항목 | 값 |
| --- | --- |
| native 행 | 199(정상 182 + guard 17) |
| 분할 단계(C++ 비교) | 3683 = native 3753 − 합친 53 − guard 단계 17; 재개(직전 C++ 출력 사용) 3492 |
| 연속 대조 | 182 |
| carry | Unknown 2979 / Clear 370 / Set 334, probe 7040, consumer flip 163 |
| 선언 host 변경 | RAM 2122, PC 163 |
| block start | 신규 범위 106, `animation_frame_helpers_block`의 `case` 레이블과 정확히 일치(차이 0), native 관찰 106과도 일치 |
| 원본 opcode 재유도 leader | 관찰 106과 차이 0 |
| carry 보존 block | 38(원본 opcode 전부 FLOW_ONLY인 block; 단일 block 단계의 C++ carry 보존 여부와 일치) |
| zero-step | 106 × carry 0/1/2 = 318, 모두 입력 상태·RAM·PVC 보존 |
| 경계 zero-step(stop == 진입 PC) | `1a73c` `49b0c` `4aa88` `e8a48` `4939c` 모두 ok(관찰된 동작, 계약 요구 아님) |
| 내부 PC 거부 | 137개 모두 정확히 `unsupported animation frame helper PC` |
| 경계 직접 진입(다른 stop) | 5개 모두 `unsupported animation machine PC` |
| 범위 밖 진입 | 12개(`480ba` `480f2` `47672` `6f1c4` `2efdc` `3c7c` `b4ab0` `493bc` `1c052` `4da08` `b4850` `4706c`) `unsupported animation machine PC` |
| Unknown carry consumer 진입 | `4765c` `b4a38` `b4a6c` 모두 `frame helper caller requires known carry`, 전체 보존 |
| 경계 도달 negative | 자연 `480bc` + stop `ff000`/`49b0c`/`4aa88`/`4939c`, `6f1c2` + stop `ff000`, A5≠`108000`(`49392`, `b4a2a` 경유) + stop `ff000`: 모두 `unsupported animation machine PC` + rollback |
| negative 합계 | 164 + guard 17 = 181 |

### guard 17개(C++ 오류 + 전체 보존)

native guard는 각 행의 마지막 phase에서 발생했다. C++는 같은 phase 시작 상태와 단계 전체(단계 시작 상태, 단계 stop) 두 방식으로 실행해 정확한 오류와 RAM/16R/PC/carry/PVC/bank/port marker/외부 읽기 marker/status 보존을 확인했다.

| 오류 문자열 | 행 |
| --- | --- |
| `unsupported program bus device address` | `guard-hazard-x-bin-overflow-x1-06a0/1000/4000/7fff` |
| `program bus requires even WORD/LONG address` | `guard-odd-A0-46f52`, `guard-odd-A1-movem`, `guard-odd-A1-4d9d6-route`, `guard-odd-A4-4d9d6`, `guard-odd-A7-6f1c2-rts`, `guard-odd-A7-3c44-push`, `guard-odd-A7-jsr-push` |
| `unsupported animation machine write device` | `guard-rom-write-b4a2a-a5-0`, `guard-rom-write-4701e-a5-0`, `guard-rom-write-b481e-a5-8000` |
| `invalid animation machine write size/alignment` | `guard-odd-A5-b4a2a` |
| `unsupported animation machine PC` | `guard-stop-not-boundary-2ac2`, `guard-ret-1a73c-boundary-via-direct` |

## 사실 / 추론 / 미확인

사실(이번 실행으로 확인):
- 위 표의 모든 비교가 통과했다. C++와 native가 일치하지 않은 정상 조건은 없다. C++ 코드 불일치는 발견하지 못했다.
- X bin 겹침: native에서 큰 rect의 X bin 루프는 Y 배열과 여분 바이트를 넘어 `10d665` 뒤로 쓴다(`x1=06a0`에서 `10d67c`에 도달, 슬롯 카운터 WORD를 망가뜨려 슬롯 루프가 테이블을 넘어간 뒤 `46f76`에서 주소 `800000` WORD 접근으로 fault). 이 4개(`x1=06a0/1000/4000/7fff`)는 native fault인 guard이며, 정상 행은 native와 같은 쓰기를 C++가 재현한다. C++는 guard 4개 모두 `unsupported program bus device address` 오류와 전체 롤백을 낸다(원본 CPU의 fault 시점 부분 쓰기와 같다고 주장하지 않는다).
- `49b0c` `4aa88` `e8a48`로 가는 shell 반환 블록 `480c6` `480cc` `480d2` `480ea`는 native에서 실행되지 않았다(1a73c에서 정지). 이 4개는 zero-step과 아래 API-only 제어만 있다.

추론:
- carry 분류는 원본 opcode 해석이다(native SR 미사용). `ANDI.W`가 항상 C를 지운다는 사실에 기반해 `493a2`만 Clear로 분류했고, 다른 위치의 ANDI.W는 C++가 Unknown으로 두는 것을 규약으로 확인했다.
- `289e` 분할 stop `28a8`/`28ac`의 병합은 기존 executor 구조(입구 block이 C를 정하고 복귀) 때문이며 native 의미가 같다고 추론한다(병합된 phase의 출력 비교가 통과).

API-only(native 대응 없음): 경계 stop 제어 `480c6→49b0c`, `480cc→4aa88`, `480e4→e8a48`, `480d2→b4a2a`, `480ea→2efa6`는 해당 PC에서 stop하고 아무것도 실행하지 않는다(5개 ok). 내부/경계 직접 진입과 범위 밖 진입의 거부는 native guard가 없다.

미확인·범위 밖: `1a73c` `49b0c` `4aa88` `e8a48` 본문, `4939c` TRAP의 의도, 자연 scheduler·IRQ·gameplay 도달성, 원본 CPU fault 롤백 동등성, X bin 겹침이 원본 버그인지 여부(관찰된 동작만 기록).

## 이전 verifier/테스트에서 480bc 등을 미지원 경계로 쓰는 negative (수정하지 않음, 보고만)

- `tools/verify_animation_machine_fade_card.py:452` `reject('frame_helper_480bc_unsupported', {'pc': 0x480bc}, ('unsupported animation machine PC',))`: 이제 `480bc`는 실행부가 있으므로 이름과 의미가 낡았다. 결과(오류 문자열)가 그대로일지는 이 검증에서 실행하지 않아 미확인이다(`480bc`에서 `47642` `289e`를 거쳐 `1a73c` 경계에 stop `ff000`으로 도달하면 `unsupported animation machine PC` 롤백이 되는 경로가 맞다면 문자열은 유지되지만, 그 fade-card 시작 RAM에서 `47642`/`289e`가 먼저 다른 오류를 낼 수 있다). 해당 verifier를 돌려 확인하고 이름·근거를 "경계 도달" 의미로 바꿔야 한다.
- `tools/verify_animation_machine_fade_card.py:154` `declared_targets = {0x4806b, 0x480bc, 0x4c3a2}`: native fade-card 관찰에서 실행되지 않는 guard 목표라는 주석은 native 쪽에서는 유효하나 C++ 의미는 달라졌다.
- 영향 없음(480bc를 stop 또는 zero-step으로만 사용): `verify_animation_machine_screen.py:269`, `verify_animation_machine_transition.py:322`의 zero-step 목록, `engine/tests/animation_machine_{transition,exit,screen}_test.cpp`의 stop `0x480bc`. `engine/tests/animation_machine_fade_card_test.cpp:135`의 `outside[]`(`0x1a73c`)와 `animation_machine_screen_test.cpp:69`의 `1a73c` 거부는 여전히 실행부가 없는 경계이므로 유효하다.
- `47642` `b4a2a` `4701e` `2efa6` `3c44` `6f1c2` `46f52` `49392` `1c028` `4d9d6` `b481e`를 미지원 경계로 쓰는 다른 `verify_animation_machine*.py`나 C++ 테스트는 없었다(주소 상수 전수 검색).

## 검증 명령

- `make -j4 all test`(worktree): 종료 코드 0, `animation_machine_frame_helpers_test PASS 1063 API invocations`.
- `.venv/bin/python tools/verify_animation_machine_frame_helpers.py` 두 번 실행, 보고서 SHA256 동일: `737f1c0d9f33002545285d4ac15afb45b2405bc9e06b8d8c354b55d19dc60a8b`. 출력 폴더는 실행 시작 시 이 검증 도구가 비운다(`artifacts/animation_machine_frame_helpers_execution/`만).
- 소요: 한 번에 약 20분(10k회 이상 C++ harness 호출).
- `git diff --check` 깨끗함(신규 파일은 공백 끝 검사 별도 수행).
