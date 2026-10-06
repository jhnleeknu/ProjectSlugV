# 분기 오브젝트 리소스 연결 리뷰

기준37122c9 이후 변경. 메인이 초기화 흐름·그룹·팔레트 요청을 해석했다. 확정 group을 적용하는 composition 포장은 gpt-6.1-sol medium이 담당했고 메인이 diff와 원본 비교를 검토했다.

- 두 그룹 설정 명령을 추출 시 정확히 확인한다. sentinel을 제외하고 group OR 후 ID를 중복 제거한다.
- 원본 포인터 해석과 MS5C kind2를 재사용하며 새 리소스 형식을 만들지 않았다.
- 그룹에 맞는 ROM400000을 CPU200000에 매핑해 비디오 비교한다.
- 1632 animation steps / 3264 prepare-refresh stages의 전체RAM·carry·비디오 쓰기가 일치했다.
- 제출 ID 집합으로57개 의존리소스 전체의 실행 커버리지를 확인한다.
- palette 관찰은 원본 initializer prefix에 한정한다. 자연 도달성·동적 allocator C++ 동등성·최종픽셀 검증은 남아있다.
- ROM/추출리소스는 ignored 경로에 유지하고 소스·근거만 커밋한다.
