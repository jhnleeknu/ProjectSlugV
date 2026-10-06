# 팔레트 상태 초기화 리뷰

기준 커밋 ae8ecad. 메인 에이전트가 원본 0x3ef2..0x3f96의 루프 종료, 16비트 상대 링크, sentinel, staging 첫 word만 초기화하는 동작 및 전역 변수 쓰기를 해석한 후 구현 사양을 위임했다. C++ 구현을 직접 읽고 원본 M68000 실행과 20개 × 64KiB 전체를 비교하여 일치를 확인했다.

추가로 원본0x8ebe/0x8ff4에서 동일 ID 공유, bit0 새 할당, 같은 bucket 다른 ID 구분, 역순 참조 해제를 관찰했다. 이 결과를 할당/해제 C++ 구현 완료로 표현하지 않는다. pool 소진과 trap 경로는 미검증이다.

검증: make all test, tools/verify_palette_state.py. API는 size/null 검사 후에만 쓰며 CLI는 동일 입력/출력 inode와 잘못된 길이를 거부한다. 일반 C++11 컴파일과 차등 검증을 완료했다. ROM에서 파생된 fixture는 Git 제외 상태다.
