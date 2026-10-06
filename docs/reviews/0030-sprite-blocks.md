# 다중 직사각형 리소스 리뷰

대상:b1dbc58 이후 변경. 이전 goal turn은 반전 분기 C++ 통합과 원본 검증을 완료한 progress다.

메인 에이전트가 헤더 개수와 블록 반복 제어를 추론하고 실제 네 리소스를 원본 CPU로 검증했다. 확정된 MS5C kind2 로더 및 로더 테스트는 gpt-6.1-sol/medium에 위임했고 메인이 실제 diff를 검토했다. 표시 wrapper, 포장 도구, 연속 pipeline 통합은 메인이 구현했다.

검토 사항:
- kind1 제약을 완화하지 않고 kind2를 명시적으로 추가했다. 원본 payload 바이트와 ID/위치 메타데이터를 유지한다.
- 크기 산술은 제한된 uint8 치수에서 수행한다. 각 블록 전 남은 길이를 확인해 subtraction/index underflow를 막고 exact consumption을 검사한다.
- wrapper는 블록마다 좌표를 새로 읽고 슬롯 상태만 전달한다. 실패 시 writes/next_slot 모두 보존한다. 슬롯 소진 후 손상된 블록도 검사하는 런타임 계약을 문서화했다.
- Makefile 테스트 의존성이 다른 test target에 잘못 붙은 것을 리뷰 중 발견하여 공통 test target으로 수정했다.
- 실제2880조건 원본 명령 일치, 다중 블록 활성/비활성 pipeline 각각124제출·32단계 일치, 기존 kind1 pipeline 회귀 통과.
- make all test와 git diff --check 통과.

미확인 게임 호출·팔레트는 manifest에 분리했다. 단순 포인터 탐색 결과로 전체 테이블 크기나 unused 판정을 하지 않았다. 다중 블록 소비기 검증은 픽셀·IRQ·전체 게임 검증을 대체하지 않는다.
