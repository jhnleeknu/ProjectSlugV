# 메인 콜백 호출·복귀 스택 리뷰

대상 기준 커밋: `bb7bda7`.

메인이 f30..f52 원본 명령과 API/CLI/검증 diff를 직접 확인했다. f3c에서 A0를 다시 읽지 않고 현재 값을 사용하며, f44는 실제 스택의 A6만 복구한다. 다른 콜백 레지스터 변경을 유지하고 f46 직전 경계를 반환한다. 스택 주소의 뺄셈·덧셈은 범위 검사 뒤 수행한다.

- `make all test`: Python73개 및 C++ 전체 검사 통과, 경고 없음. 로그 `artifacts/main_callback_stack_build_test.log`.
- 추가 API 단위 검사를 작성한 뒤 `make build/irq_envelope_test && ./build/irq_envelope_test` 통과. 저장 A6 변조, 다른 레지스터 보존, 잘못된 범위·벡터 별칭과 결과/포트 롤백을 확인했다.
- `.venv/bin/python tools/verify_main_callback_stack.py`: 원본352조건 및 실패/별칭21조건 통과. 전체 RAM/스택/16레지스터와 시간순 스택 쓰기 비교, MMIO 없음.
- 실제 기본RTS16회와 호스트가 명시한 레지스터 변경을 연결했다. 원본 ROM 불변, code hook 경계 중단을 확인했다.
- 보고서 SHA256 `0af33d3f984a79ca47cb2ea1a562d43de1f2e8e72a3dbf6b03777c011efad4e9`.

팔레트 처리의 최종D1은 기존 API가 반환하지 않으므로 전체 콜백→팔레트→다음 입력 연결로 확대하지 않았다. f4c는 ef2와 다른 대기 조건임을 기록했다. 해당 후속 작업과 실제 콜백 본문·전체 부팅은 계속 남아 있으며 이번 두 스택 경계의 검증과 구분한다.
