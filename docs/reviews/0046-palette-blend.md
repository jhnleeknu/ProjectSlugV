# 팔레트 혼합 검토

기준7bc7cee 이후. 메인이 원본4c40의 MOVE.B 잔여비트와 signed lookup을 모델링하고 전체 차이표 및15비트 색변환을 검증했다. 확정된 식의 C++ 반영은 gpt-6.1-sol medium이 담당하고 메인이 diff를 검토했다.

- float/반올림 대신 원본에 맞는 signed 정수 나눗셈을 사용한다.
- 계수0/31이상은 한쪽 리소스만 요구하며 equal-ID는 혼합하지 않는다.
- 원본helper2112조건과 실제MS5P20쌍660조건 일치.
- make all test, 누락·bit15·끝점·rollback 검사 통과.
- bit15가 있는 중간 혼합색, 활성효과 및 효과혼합504c는 미지원으로 남았다.
