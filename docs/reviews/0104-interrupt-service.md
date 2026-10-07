# c8c 서비스 통합 리뷰

대상 기준 커밋: `b282d52`.

메인이 원본 c8c..d54의 분기와 D0 의존성을 확인하고 기존 크레딧·팔레트·열 제어·스프라이트·작업 복구·사운드를 연결했다. 재진입, 작업 진입, 사운드 대기를 별도 상태로 표현하고 단계별 재개 API를 구현했다. 하위 오류는 전체 RAM/팔레트/출력을 보존하며 정상 대기는 진행한 상태를 유지한다.

- `make all test`: Python73개와 C++ 전체 검사 통과. 로그 `artifacts/interrupt_service_build_test.log`.
- `.venv/bin/python tools/verify_interrupt_service.py`: 원본676조건/54,586개 MMIO 및18개 오류·별칭 검사 통과. RAM/두 bank/작업 경계 레지스터/실제 스택 쓰기/pending/상태 읽기를 비교했다. 실제 MS5C 바이너리를 사용했다.
- 메인 리뷰에서 사운드 CLI의 불필요한 리소스 인자가 API 오류 검사를 가릴 수 있음을 발견해 검증 코드를 수정했다. 전체 dirty 팔레트 fixture가 pending 분기에 들어가지 않는 조합도 발견해 명시적 전송 조건을 추가했다.
- 예상 밖 비RAM/비스택 쓰기를 거부하도록 보강하고, 작업 반환→사운드 high/low 대기→완료 경로를 실제 원본 CPU 문맥으로 검증했다.
- task/sound CLI는 표시 bank를 새로 선택하지 않는다. 기존0 표시를null(변경 없음)로 수정하여 호출자에게 잘못된 bank 전환을 나타내지 않게 했다.
- 보고서 SHA256 `2d04e2c1b7d2c92c65327eae4de468d70206836e23ed0e80e99a97c73d588065`.

고정 ROM 호출 목록도 검토했다. c42는a08, c8c는23c에 직접 호출 후보가 있고 c64의 직접 JSR/BSR 후보는 없다. 이 사실만으로 미사용을 단정하지 않는다. 도구 `tools/analyze_task_queue_callers.py`, 보고서 SHA256 `54a77311fe489add556dfc29cd3a7dd99ed6035c10bb416e145edf7d8640ed9b`.

완료 시 CPU 임시 레지스터/CCR, IRQ prologue/epilogue·BIOS, 작업 본문과 자연 시간축은 이번 구현의 계약에 포함하지 않는다. 검증 범위와 실제 런타임 인터페이스를 문서에 명시했다. 전체 부팅/게임 완료로 취급하지 않는다.
