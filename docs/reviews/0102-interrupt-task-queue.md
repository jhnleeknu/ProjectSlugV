# 작업 큐 등록 리뷰

대상 기준 커밋: `6eb63f7`.

메인이 원본 c64…c8a의 스택 이동과 저장 순서를 해석하고 C++ 구현 및 검증 코드를 리뷰했다. 즉시 복귀 주소와 지연 작업 주소를 구분하며, 큐가 가득 찬 경우에도 외부 스택 두 쓰기와 A7 +8을 보존한다. A6와 나머지 레지스터는 유지한다.

- `queue_interrupt_task`는 64KiB RAM, 외부 스택 범위 및 사용 프레임을 검증하고 성공한 경우만 상태를 반영한다.
- CLI는 RAM과 16개 big-endian 레지스터를 읽고, 모든 입력·출력 경로 사이의 별칭을 거부한다.
- `.venv/bin/python tools/verify_interrupt_task_queue.py`: 원본 등록/건너뛰기 176조건, 동일 RAM에서 역순 복구 32회, 오류/별칭 19조건 통과. 전체 RAM, 16개 레지스터와 실제 스택 쓰기/메모리를 비교했다. 원본 ROM은 변경하지 않았다.
- `make all test`: Python 73개 및 C++ 전체 검사 통과. 로그: `artifacts/interrupt_task_queue_build_test.log`.
- 보고서: `artifacts/interrupt_task_queue/verification.json`, SHA256 `3d8d0f8a716339ed91318ebecc751c574793c5a96ed45400b311b444d6f46320`.

작업 본문, d2a 반복, SR/CCR, 전체 인터럽트와 실제 시간축은 이번 검증에 포함되지 않는다. 지원 범위 밖의 RAM/스택 주소는 API 오류로 처리한다. 발견된 통합 차단 문제는 없다.
