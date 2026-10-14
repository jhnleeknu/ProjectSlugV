# 0258 — 신규 G3 verifier 독립 검토

대상은 `tools/verify_animation_machine_objects_g3.py`(검토 시작 SHA256 `4b0cc55608722889bd6eefb15270fb4e2396bd1cc47cd75ab980142d470eb7c1`)와 `docs/analysis/animation-machine-objects-g3-execution.md`다. G2 재사용 함수와 실제 failed/targeted 보고도 읽었다. 엔진·검증 소스·기존 보고를 수정하거나 전체 실행을 새로 수행하지 않았다.

## Concrete finding

### P2 — `--out`/`--scratch`의 `..`는 checkout 밖 출력 제한을 우회한다

`local_output()`(49–59행)은 `Path.absolute().is_relative_to(ROOT)`를 검사하지만 `absolute()`는 `..`를 제거하지 않고 `is_relative_to()`는 lexical 비교다. 따라서 user-controlled `ROOT / '../outside'`는 검사를 통과하고 모든 구성요소가 symlink가 아니어도 checkout 밖에서 `mkdir`/후속 출력을 실행할 수 있다. 문서의 로컬 checkout 출력 제한과 다르다.

순수 Path 계산으로 확인했다: `/…/metalslug/../outside`의 lexical under-ROOT는 True이고 normalized 경로는 ROOT 밖이다. 디렉터리나 파일을 실제로 만들지 않았다. `..` 구성요소를 거부하거나 symlink 검사 의미를 보존하는 방식으로 경로를 정규화해야 한다. 이 finding은 ROM 의미나 comparison을 바꾸는 요구가 아니다.

## 비교와 case 보존

실제 `failed-full`은 2,459 fixtures 및 30,632 natural nodes를 보존하고 `accepted=false`였다. `targeted`도 2,459개 row와 2,459 unique indices를 유지하며 through 실패 때문에 `accepted=false`였다. 초기 실패를 누락하거나 부분 요청을 전체 수용으로 바꾸지 않았다.

- `phase_groups()`는 native piece가 `71c98`에 끝나고 실행 PC 집합에 `71c86`이 있을 때 다음 piece만 합친다. 이로써 C++ N15 block 안의 TST/BNE를 분리된 stop으로 요구하지 않는다. targeted block probe는 두 Known 입력과 Unknown 입력의 `71ca0` 상태가 일치했다.
- EORI `792ac`/`7961e`는 register/RAM/PC만으로 dependency를 계산하는 G2의 한계를 좁게 보완한다. targeted Known runs는 C++ Clear/Set tag `2/1`과 native C `1/0`으로 모두 `cout_ok=true`였으며 Unknown은 정확한 consumer 오류였다. output carry를 무시한 equality로 바꾸지 않았다.
- `c637c` 예외는 carry-consumer fixture의 정확한 PC에만 적용한다. target 보고의 네 fixture에서 native stop `c6380`, full state/ports/reads, Unknown C 보존의 pass-through 검사가 통과했다. 다른 consumer는 기존 exact consumer 오류 검사를 유지한다.
- indices 1278/1281은 PC와 N-precondition 불일치를 다시 확인한 뒤 `excluded:contradictory-caller-N`과 `no_execution_equivalence`로 분류한다. targeted row의 원래 RAM/register diff는 `raw_comparison`에 남고 `regen_ok`와 carry/unknown 검사는 계속 적용된다. 동일 register/RAM의 유효 counterparts 1279/1280은 각각 `match`이며 전체 fixture 체크도 이를 요구한다.
- N19 `b1fdc`는 `units == [0]`, 기존 diagnostic 동일 오류/native 도달/production rollback 증거가 먼저 성립한 경우에만 새 prefix proof를 실행한다. 이전 실제 C++ phase 입력에서 `b1fdc` stop까지 full state/ports/reads를 원본 prefix와 비교하고 도달 시 C가 Unknown인지 확인한다. 이후 `phase_declared`를 사용하는 G2 chain 정책을 유지하며 whole-through equality로 승격하지 않는다.
- reviewed external 오류 `49ffe`/`cd58`은 정확한 diagnostic PC를 추가 요구한다. native 주소 마스크 차이는 bounded prefix와 checked rollback으로 분류하고 실제 fault 이후 PC 도달/equality를 주장하지 않는다.

## 입력 pin과 부정 검사

현재 provenance는 전체 C++ source/header와 Makefile, 원본 관찰의 계약·도구, G2/G3 verifier, N19 계약, MS5D·ROM·manifest, F3 계약, scheduler/RNG observation, 실제 stage-entry 142 seed RAM과 해당 observation을 포함한다. loaded module 파일, 실제 Python·Unicorn·Capstone library 및 compiler executable도 고정한다. 생산/진단 binaries와 생성한 C++ harness source는 별도로 전후 비교한다. 현재 G3 native oracle의 과거 library SHA가 원 관측에 없다는 한계를 명확히 유지한다.

부정 API 단계는 각 unit의 interior·odd·zero-step 목록과 unrouted RAM PC를 직접 생성하고 exact error 및 full rollback/zero-step 무출력을 요구한다. 비교기 mutation 검사도 실제 비교 함수에 RAM/register/PC/PVC/bank/ports/read/carry/wait 오염을 넣는다. targeted 보고에서 이 nine comparator 검사 모두 True였다. 이는 단순 wrapper 성공 여부만 확인하는 검사가 아니다.

검토 시점에 최종 전체 실행은 진행 중이었다. 현재 확인한 소스 비교/분류에서 추가 concrete false-accept 또는 case-drop finding은 발견하지 않았다. 최종 full run의 accepted 여부와 source/input pins, 출력 경로 finding의 수정 및 후속 검증은 메인 수용 기록에서 확인해야 한다.

## 전체 보고 후속 확인

검토 종료 직전 완료된 전체 보고 SHA256 `07c296a96ac33b2a71296d2aef7aae4fb6b6db289fd54cddf7a569f05e0540a7`에서 `accepted=true`, 35개 checks 모두 True, fixture 2,459개/unique indices 2,459개와 natural nodes 30,632개를 확인했다. 출력 경로 finding은 소스 수정 후 메인의 최종 재실행으로 처리할 예정이다. 추가 concrete comparison finding은 없다.

## 메인 최종 수용

출력 경로 finding은 `local_output()`이 `..`를 mkdir 전에 거부하고 기존 출력 파일까지 symlink를 사전 검사하도록 수정했다. 메인이 실제 수정 부분을 읽고 최종 전체 보고의 39개 checks, 전체 matrix, 770개 현재 입력, native 파일, 생산·진단 바이너리와 생성 C++ 소스의 SHA를 다시 대조했다. 전부 일치하며 보고 SHA256은 `2c2ac4ae6438eb86dc5286a351fea146832e73a4f1cfe4ffedc2b997a3c42419`이다. 경로 부정 검사 네 개도 전체 실행에 포함되어 통과했다. 비교 의미의 추가 변경이나 엔진 수정은 없다.
