# 작업 반환 반복 진입 리뷰

대상 기준 커밋: `74dd23f`.

메인이 원본 d2a의 세 명령을 확인하고 A5 복구 이후 기존 프레임 복구를 재사용하도록 구현했다. 입력 A7은 callback RTS 이후이며 중복 pop하지 않는다. 후보 레지스터로 처리하여 하위 복구 실패 시 원래 A5를 보존한다. CLI의 선택적 `--resume`은 기존 호출을 유지한다.

- `.venv/bin/python tools/verify_interrupt_task_resume.py`: 원본 312조건과 오류/별칭 24조건 통과. 전체 RAM, 16개 레지스터, 포트 순서와 실제 외부 스택 쓰기를 비교했다.
- 32개 작업과 마지막 빈 큐 경계를 연속 검증했다. 작업의 레지스터 변경과 RTS의 A7 +4는 명시적인 호스트 입력이며 실제 작업 본문 실행으로 주장하지 않는다.
- 복원 A5의 포인터 쓰기가 저장 A6/PC와 겹치는 조건 및 unsigned 빈 큐와 스택 경계를 포함한다.
- `make all test`: Python 73개 및 C++ 전체 검사 통과. 로그: `artifacts/interrupt_task_resume_build_test.log`.
- 보고서 SHA256: `3d1ff4b22cee4b4def59839de82ef68153d99066ca45d0da305673036d51d5ba` (`artifacts/interrupt_task_resume/verification.json`). 원본 ROM은 불변이다.

전체 c8c, 작업 본문, SR/CCR 및 자연 시간축은 후속 범위다. 메인 코드·검증 리뷰에서 통합 차단 문제는 발견되지 않았다.
