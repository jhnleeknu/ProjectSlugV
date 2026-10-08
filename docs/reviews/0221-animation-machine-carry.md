# 0221 — Animation 반환 carry와 실제 BCC·BCS caller

Baseline `ed42971`, branch `codex/animation-machine-carry`. 기존 전체 목표·완료 기준·진행을 승계한다.

## 변경과 리뷰 결론

공개 machine state에 uint32 기반 `AnimationCarryUnknown/Clear/Set`을 추가했다. 세 writer는 실제 원본 `49fe6 ORI CCR`, `4a0e0 ASR.W`, initializer의 마지막 `49fc0 MOVE.W`다. 확인한 55개 semantic block은 C를 보존하고 나머지는 실행 전에 Unknown으로 만든다. 유효한 zero-step은 입력 C를 보존하나 잘못된 enum은 zero-step에서도 거부한다. RTS 주소만으로 앞선 writer의 실행을 가정하지 않는다.

실제 `1dc84 → 1dc8a BCC`, `210ae → 210b4 BCS`를 추가했다. Unknown 소비는 checked 오류다. 분기 후 body는 지원 범위 밖이고 관측된 successor에서 멈춘다. 원본 fixed CPU 주소는 canonical BE 프로그램의 같은 파일 offset이다. 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다.

메인은 실제 core diff·native observer·비교기·검사 소스와 결과를 읽고 원본 branch bytes/targets 및 C 보존 block을 검토했다. 독립 Sol도 55개 첫 명령과 복합 block suffix, 세 writer, transaction·zero-step·enum 경계를 검토했고 core 결함을 발견하지 못했다. C 보존은 bus/stack helper의 읽기·쓰기 여부로 추론하지 않는다. MOVEM/JSR와 MOVE는 flag 동작이 다르다.

## 검증

- 신규 unit 196회 API 호출 및 기존 machine/caller unit 일반·UBSan 통과. `make all test` exit0, Python257개/C++ 실행152개, warning0.
- 원본 60조건: split160단계와 fresh continuous control100단계. 각 모드를 두 번 실행해240 CPU/520단계를 기록했다. SR 읽기·ROM patch·중간 register 주입 없이 실제 BCC/BCS successor로 C를 관측한다. 분기 앞 stop/resume이 없는 control도 동일하다.
- C++60조건/160단계, 실제 이전 출력100회 재개, wait40/return60/branch60. 전체64KiB RAM,16R/PC, C, 상태, PVC 모델/bank,632포트와 외부 읽기0회 일치. Wait의 Unknown은 native flag 관측이 아닌 API 계약이다.
- 오류10조건과 valid zero-step3조건 통과. Unknown 분기2, invalid enum2, branch 뒤 미지원 PC4, 앞선 실제 caller 쓰기 후 늦은 실패2가 모든 API 출력을 보존한다. Native fault rollback을 주장하지 않는다.
- 기존 machine 기본8조건+chain2단계 및 확장85조건121단계,37재개/9오류 통과. 기존 caller59조건91단계,32재개/6오류 통과. 기존 immutable native는 C를 관측하지 않았으므로 실제 C 전달 및 rollback 검사와 원본 C 대조를 구분한다.
- 독립 Sol이 대표25조건을 fresh CPU50개에서 split82/continuous57단계 재실행했다. 전체 RAM/16R/PC/PVC/trace/ports가 일치했고 native1968개 해시와 phase참조1920개도 확인했다. Guard 방어 코드는 검토했으나 별도 오류 유발 matrix 실행은 이 감사 범위 밖이다.
- 메인이 native1968, 기존 machine1707, caller1233, 새 carry3042 고유 파일의 해시를 각각 확인했다(합집합5834). 별도 Sol도 세 C++ 보고서 전수 해시를 확인했다.

## 검토 중 보강

Unknown 오류의 예상 문구를 실제 `requires known carry`와 맞췄다. Branch에서 시작하는 오류 검사에 더해 caller 진입부터 RAM/PVC 쓰기를 수행한 뒤 실패하는 두 조건을 추가했다. 비교기 JSON은 22개 strict key이고 invalid enum은 정확한 입력값의 실패 반환에만 허용한다. 독립 parser 검사6개도 통과했다.

## 산출물과 한계

| 보고서 | SHA256 |
| --- | --- |
| carry native | `759ea9af0fd9e9fa58ba44b87be2b48a8b7b6b257aba6b164438f7c3df586d70` |
| carry C++ | `7ec1ea7d43529bb29a430b22fe696e18588f63f7d58338ef9e9e780d0c6f7d6d` |
| machine 회귀 | `c1771f496f754859aeee314064a68e252e624b0783e97a3cf9fb1e875d466496` |
| caller 회귀 | `1b2de20742f09904952f76f7cdf72e25de84c99ef2824b9fea6ede5918c6eee8` |

정확한 재현 명령·API·원본 근거는 `docs/analysis/animation-machine-carry-execution.md`를 따른다. 리소스 규격은 변경하지 않았고 MS5D kind3 실제 C++ 로더를 계속 사용한다. 코드·도구·문서만 커밋하고 ROM/추출물/artifacts는 제외한다. 원격이 없어 로컬 리뷰·커밋으로 진행한다.

일반 CCR/XNZV·IRQ/timing·자연 scheduler 도달·분기 후 상위 body·직접 플레이·전체 스테이지/적/보스·미사용 자료 전체 의미는 미완료다. PVC는 원본 포트를 pinned 모델로 접은 비교이며 물리 기판 실측이 아니다. 애니메이션17명령 중14종+14/3c 일부의 집계와 전체게임복원율 미산정, Goal active를 유지한다.
