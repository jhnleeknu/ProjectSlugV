# 원본 문자 리소스와 C++ 장면 통합 리뷰

기준24c280c. 메인 에이전트가 MS5X 규격·source ID·palette binding·원본 스트림 범위를 정하고 로더와 CLI 구현을 위임했다. 헤더/길이 상한/CRC, binding 중복과 누락, 원본 bytecode의 zero operand 보존, 실패 시 기존 resource 보존을 직접 검토했다. 실행 출력은 입력 inode와 달라야 한다.

C++ 프로그램이MS5X/MS5T/MS5P 세 파일만 소비하고 분석 trace를 읽지 않음을 확인했다. 원본CPU의 palette init→warning 실행→palette prepare→upload를 새로 실행한 참조로245760 RGB바이트 전체 일치를 확인했다. PPM SHA256 bc5aac61c7303ca7a56be15730cf4ec76390a987b471fb0cf93a9f17915bdeaa.

테스트: make all test; pack_text_scene.py; verify_text_scene.py. 원본 부팅 상태를 가정하지 않고 zero VRAM/background·normal screen·cartridge fixed source 조건을 명시했다. 단일 scene 통합이며 전체 게임/프레임 갱신/조작은 미완료다.
