# 0220 — Animation 초기화와 stage caller의 공유 스택 연결

Baseline `ff25485`, branch `codex/animation-machine-caller`. 이전 machine 통합은 progress로 승계했다. 전체 목표와 완료 기준은 변경하지 않았다.

## 결론과 실제 변경

`49f8c` initializer와 `47cec/47d0a/47d10/47d14/47d1a/47f04` 진입점을 기존 machine에 연결했다. 원본 initializer의 쓰기 순서·opaque A1·전체32bit A5 검사와 실제 RTS를 보존하며, caller의 두 JSR가 각각 `47d1a/47d20`을 공유 RAM에 쓴다. `47f04`는 return `47f0a`를 쓴다. 기존 header/API·리소스 규격·실행 경로는 유지한다.

메인은 원본 bytes와 실제 C++ diff, 두 새 Python 소스, unit, native/C++ 보고서를 읽고 수용했다. 별도 Sol의 C++ 독립 리뷰에서도 결함은 발견되지 않았다. 신규 unit32조건은 opaque pointer, mirror/shadow alias, 초기화로 바뀐 live return, exact JSR return, D0.high 보존과 늦은 실패의 모든 출력 보존을 확인했다. Normal/UBSan 및 독립 normal 실행 통과.

초기 계획의 carry 선행 조건은 원본 확인으로 수정했다. `47d20 → 47d3e` 뒤 `4847c`가 C를 새로 결정하며, `47f0a` TST.W는 C를 덮어쓴다. 따라서 이 두 caller의 연결은 일반 CCR을 요구하지 않는다. 반면 `1dc84 → 1dc8a BCC`는 animation C를 직접 읽는다. 이 반례와1622개 raw caller 후보를 inventory에 남겨 일반 carry 과제가 사라진 것처럼 기록하지 않았다. 메인이 원본 전체의 candidate 목록과 문서 목록 일치도 재검사했다.

## 원본·C++ 검증

- Native 정상59조건/91단계, 별도 TRAP 직전 guard4조건을 각각 fresh CPU2회 실행했다. Initializer18,47cec setup6,47f04 caller35조건이다. 전체16register/PC/RAM/stack event를 유지하고 SR 읽기·ROM patch·중간 register 주입·stack mask는 없다.
- 공식 verifier가 모든 원본을 다시 실행한 뒤 실제 C++59조건/91단계를 비교했다. 이전 실제 C++ 출력32회 재개와 PVC806포트, 전체 RAM/16R/PC/PVC 모델/bank/status가 일치했다. 이 군의 외부 읽기는0회다. Guard4건과 caller 경계 밖 실행2건의 API rollback도 통과했다. Native TRAP 실행이나 native fault rollback을 검증했다고 주장하지 않는다.
- 독립 Sol은 최종 정상19조건+guard4건/43단계를 다시 실행했다. Indexed PEA106800, saved low BYTE77 및 direct sound의 saved outer A0 변경을 포함한다. 실제 `4a2ec`가 RAM `1feff0`에서104900을 읽고 `4a278`이104900에106004를 publish하는 근거를 확인했다.
- 메인과 작업자가 native617참조와 C++1233개 고유 파일 해시를 확인했다. C++ 보고서의45input+1212artifact 문자열 항목을 절대 경로로 정규화하면1233개다.
- 기존 machine 회귀도 기본8조건+2단계와 확장85조건121단계,37재개/9오류를 통과했다. 메인이1707고유파일 해시를 확인했다. `make all test`는 Python257/C++151개 실행, 경고0, exit0이다.

## 리뷰 중 보강

새 native main의 시작에서 이전 성공 보고서를 삭제하도록 보강했다. 독립 감사의 임시폴더·의도적인 source 검증 실패 시험에서 삭제가 확인됐다. Initializer return alias fixture의 stack metadata도 실제 override 뒤 return 값과 일치시켰다.

새 verifier는 native replay 전에 자기 소스·공통 도구·core/header·compiler·Python·unit 입력 해시를 저장하고 마지막에 재검사하도록 했다. 예상한 negative 원인도 `initializer TRAP15` 문구로 검사한다. 실제 C++ 동작 수정이 필요했던 결함은 발견되지 않았다.

## 최종 식별 및 남은 범위

| 보고서 | SHA256 |
| --- | --- |
| caller native | `f735043941529a9e020020715735b45e60890ab8b2b94211aeb0e4fbe22e17d5` |
| caller C++ verification | `5b1ac7cc62ccbaba2982f83ac03ca43f61c3be69980a70ba7df55be61b49c9f5` |
| 기존 machine 회귀 | `6ebfb4ecb742bc4aa7b023a344e70e432eab9e284c099f194724cd021f622196` |

재현 명령과 exact API 경계는 `docs/analysis/animation-machine-callers-execution.md`를 따른다. 코드·도구·문서만 Git에 추가하고 ROM/추출 데이터/artifacts는 제외한다. 원격이 없어 로컬 리뷰·커밋으로 진행한다.

원본 관측은 bank2와 PVC read 없는 통제 입력 범위다. 다른 bank·general CCR/carry·모든 alias·자연 scheduler/IRQ·상위47c6c 전체·직접플레이·전체스테이지/적/보스 및 전체미사용자료 의미는 미완료다. 이번 caller 성공으로 애니메이션17명령 중14종+14/3c 일부의 기존 집계를 변경하지 않으며 전체게임복원율은 미산정, Goal은 active다.
