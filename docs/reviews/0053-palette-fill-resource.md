# 채우기 설정 리소스 통합 리뷰

기준 a581ef2 이후. 메인이 원본 signed-word 사양과 리소스 계약을 정하고 gpt-6.1-sol medium 두 에이전트에 패커 및 C++ 구현을 각각 위임했다. 메인이 소스 리뷰, 전체 원본 비교 및 통합 검사를 수행했다.

- 기존 MS5P v1을 재사용한다. 별도 namespace와 manifest profile로 일반 팔레트 ID와 혼동하지 않도록 기록했다. 바이너리 magic만으로 profile을 판별할 수 없는 제약을 명시했다.
- 패커가 caller/setup/LEA 근거 bytes와 프로그램 해시를 검사한다. signed-word 주소 계산 및 기존 lookup 변환을 확인했다.
- C++는 크기와 전체 ID를 검사한 뒤 쓰므로 실패 시 RAM을 보존한다. word0과 나머지 상태 보존을 확인했다.
- CLI는 16비트 decimal/hex 입력 및 파일 alias를 검사한다.
- make all test 통과. 2,048 canonical selector와 3 aliases의 전체 RAM이 원본8b64와 일치했다. 특수전송32 및 후속 일반전송32 회귀 통과.
- 자연 게임 도달성 및 장치 타이밍은 미확인이다. 전체 게임 복원 완료를 의미하지 않는다.
