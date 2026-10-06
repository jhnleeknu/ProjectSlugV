# 스테이지 그룹 콜백9802 리뷰

대상:`cc15e56` 이후 변경.

메인이9802/9f36/9f78/9fe4와 기존 query/formatter를 분석하고 콜백/dispatch 통합 및 실패검사를 구현했다. gpt-6.1-sol / medium 에이전트에는 원본prefix 추출, CLI/빌드 연결, 반복 비교를 분리 위임했다.

목록이 비었을 때 반환되는0 pointer를 빈문자열로 바꾸지 않았다. 원본vector prefix4바이트를 별도MS5D에 보존하고 `%s`의 최초0 출력 동작을 기존 포맷터로 실행한다. sourceCPU/ROM주소, 함수참조(4827e는 formatter가 아닌 name lookup), 바이너리형식/CRC와 기존출력 유지도 검토했다.

형식상 올바른 callback stack이라도 ROM/workRAM과 겹치면 readonly 인자 배열이 실제RAM 스택쓰기와 다를 수 있다. 이 구현은 명시적으로 외부 diagnostic stack만 허용하고, 포맷터에 남는 인자pointer/A2를 원본 진입A7로 계산한다. 이를 전체CPU stack 모델로 주장하지 않는다.

검증:
- 원본9b3e/9802를 수정 없이 실행한1,120조건: 전체RAM/ordered ports/A2/외부점프 일치.
- 기존parent 이벤트975조건 회귀, 전체55Python/C++검사 통과.
- missingcontext/font/prefix, 잘못된stack/row, 오류시RAM/A2/출력보존 단위검사.
- synthetic unit의 hex literal뒤+가 전처리 숫자토큰으로 합쳐지는 컴파일오류를 공백/unsignedsuffix로 수정 후 재빌드 통과.

전체행그리기/이동의 동적event5와9602는 아직 연결하지 않았다. 지원하지 않는 경로를 조용히 생략하지 않고 기존명시적 오류로 유지한다.
