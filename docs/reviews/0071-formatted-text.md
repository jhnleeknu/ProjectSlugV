# 메뉴 포맷터 복원 리뷰

대상:`9d90c3d` 이후 변경.

메인이37e2/383e/386e/3950/396e/3a70을 직접 해석하고 포맷터와 단위검사를 구현했다. gpt-6.1-sol / medium 에이전트에는 기존 glyph 코드의 기계적 분리, CLI/빌드 연결, 반복 원본 비교를 각각 맡겼다. 담당 파일을 분리하고 최종 diff/실행 결과를 메인이 확인했다.

원본이 `%s` 전 D3 low byte를 덮는 것, TST.B counter의256경계, 종료문자 시 state commit 생략, 현재인자 pointer의 초기보존, 홀수 hex폭의 하위nibble 시작을 확인했다. 일반 printf로 바꾸거나 정상화하지 않았다. formatter는 이미 parsed glyph0을 렌더링해야 하므로 기존 stream 종료조건과 단일glyph API를 구분했다.

검증:
- 원본3a70의 전체RAM/ordered ports289조건 일치,59실제이름 포함.
- 글꼴704스트림 회귀와 전체55Python/C++테스트 통과.
- 외부 stack인자 및 실패 rollback 단위검사.
- CLI의 RAM크기/숫자범위/입출력 경로·inode 별칭 거부, exact9-byte 포트출력 합성검사.

메모리 byte 조회에서 불필요하게 나머지영역 전체를 복사하던 것을 직접 조회로 바꾸고 포맷터289조건과 단위검사를 다시 통과시켰다. 전체 glyph refactor는 기존 trace의100000출력상한과 실패 시 보존을 유지한다.

실제 메뉴9602/9802와의 통합은 다음 단계다. 이번289조건은 재배치한 format/argument fixture를 원본3a70에 입력하며, 원본스테이지콜백/전체CPU레지스터/픽셀까지 검증한 것은 아니다.
