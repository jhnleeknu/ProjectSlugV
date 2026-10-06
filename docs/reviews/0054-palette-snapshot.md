# 임시 색 효과 저장·복구 리뷰

기준 be0b985 이후. 메인이8bc8/8be0 역어셈블과 실제 호출을 해석했다. gpt-6.1-sol medium에 확정된 C++ API/CLI 사양 구현을 위임하고 메인이 소스 검토, Makefile 통합 및 원본 검증을 수행했다.

- 저장 범위는20바이트로 counter 및 pending과 겹치지 않는다.
- 복구된 timer0일 때만 timer1과 복구 전 현재색 상위 byte를 유지한다. 낮은 byte는 저장된 값이다.
- RAM 크기는 쓰기 전에 검사한다. CLI가 입력/출력 같은 파일 및 symlink alias를 거부한다.
- 원본 전체RAM: 저장16, 복구512, 후속갱신8조건 일치. 저장→임시효과→4프레임→복구→갱신8단계도 일치했다.
- make all test 및 diff whitespace 검사 통과.
- pending gate를 사용하는 후속 검증은 화면 업로드를 검증하지 않는다. 상위 입력/게임 전체 흐름과 하드웨어 타이밍은 미완료다.
