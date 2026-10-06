# 좌표 갱신 리뷰

기준f5ddef6. 메인 에이전트가 원본43e38/43ea8의 데이터 의존성과 ADDX.W carry 조합, 이전 result/stamp 읽기 시점을 추론하고 확정 사양 구현을 위임했다. C++ unsigned32 wrap과 부모self 참조를 검토했다. global stamp를 결과 쓰기 후 읽는 순서도 보존한다.

원본CPU와288개 ×64KiB 전체 일치. currentstamp1,2도 포함하도록 검증 범위를 보완했다. API의 parent RAM 범위 제한과 원본 CPU 예외/레지스터 동등성을 구분했다. make all test와 strict C++11 빌드 통과. 원본의 갱신 표시 toggle은 확인했으나 실제 게임 프레임당 호출 횟수는 미확인이다.
