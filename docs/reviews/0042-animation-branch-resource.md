# 원본 양방향 애니메이션 리소스 검토

기준592987a 이후 변경. 메인이 ROM 흐름·callback1d를 해석하고 포장과 원본 비교를 수행했다. gpt-6.1-sol medium이 확정된1d 사양과 MS5A CLI의 MS5D 입력 연결을 구현했으며 메인이 diff를 검토했다.

- callback1d의7c,1e의7d와 각 RAM 경계 검사를 확인했다.
- MS5A/MS5D loader 및 기존 transactional API를 사용한다. 추가 데이터 입력을 출력으로 덮어쓰지 않는다.
- 루프 양방향 분기와 네 프레임의 경계는 원본으로 고정하고 추출 시 확인한다.
- make all test 통과. 실제ROM 리소스1632회 전체RAM/carry 일치.
- 기존 데이터 없는 MS5A CLI의 ROM루프96호출·192비디오 단계 회귀도 확인한다.
- composition group 미확인으로 최종 ID·렌더링을 임의 연결하지 않았다. 전체 복원 목표는 계속 진행 중이다.
