# 애니메이션 표시 변환 C++ 리뷰

대상7216e10 이후 변경. 메인은 검증된 사양을 gpt-6.1-sol/medium에 위임하고 API/core/CLI diff를 검토했다. 원본 검증과 큐·MS5C 연속 통합, 범위/원자성 테스트는 메인이 작성했다.

- int32 좌표 중간값은 signed8의2배와16bit base를 처리하는 범위 안에 있다. low16은 명시적uint16 변환으로 보존한다.
- 상대 좌표 반전 후 style XOR, 팔레트 우선순위와 원본high16 보존을 확인했다.
- RAM exact size, object_offset의덧셈 전 범위 검사, operand exact7byte를 검증한다. 실패는 결과를 보존한다.
- skipped의zero register는 인터페이스 표현이다. 원본 반환 register 동일성을 주장하지 않는다. 원본 A1의7byte 전진을 따로 확인했다.
- CLI는 입력 alias에 출력하지 않고 모든 검사 뒤에 출력을 연다. 에이전트의 별도 대량 smoke는 완료 결과가 확보되지 않아 근거로 사용하지 않았다.
- 메인 실행의 원본/C++3072조건 및32생략 조건, 활성/비활성 pipeline 각각124제출·32단계가 모두 일치했다.
- make all test, git diff --check 통과.

현재 연결은 실제 handler와 큐 사이의 계약을 복원한다. 명령 스트림 실행기·자연 스크립트 추출·프레임 타이밍·전체 게임 완료로 확대하지 않는다.
