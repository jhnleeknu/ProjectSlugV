# 오브젝트 목록 초기화 리뷰

기준 커밋: 88bc58d. 이 변경은 원본 0x2790 루틴의 지속 RAM 효과와 MS5I 리소스 소비를 추가한다.

메인 에이전트가 원본 명령 흐름과 C++ 구현을 비교했다. reset 이후 free 슬롯의 +4/+0xc/+0x10을 지우지 않는 점, boot 목록 연결 순서, sentinel 영역과 global 변수를 확인했다. 로더의 길이·CRC·주소 경계·겹침 검사와 실패 시 상태 보존을 확인했다. 검증 스크립트에 출력 길이 오류를 명시적으로 처리하도록 보완했다.

검증:
- make all test: Python 55개와 C++ 테스트 3종 통과.
- tools/pack_object_boot.py: 실제 원본 테이블에서 160바이트 MS5I 생성.
- tools/verify_object_lists.py: Unicorn 2.1.4 M68000에서 원본 진입점 0x2790 실행. 21개 패턴의 각 64KiB 전체가 C++ 출력과 일치.
- 결합 출력 SHA256: 55262174db19dbfa75f4db2aaa18a70d08fade4952bb2a0f40d0e041270ce4a4.
- 소스 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.

검증 범위는 지속 RAM 효과다. 비교 RAM 밖에 테스트 스택을 두었으며 레지스터·CCR·임시 스택 쓰기·Neo Geo 장치·전체 부팅은 검증하지 않는다. sanitizer 실행은 이 호스트에서 지연되어 확인되지 않았으며 일반 빌드 검증과 구분한다.
