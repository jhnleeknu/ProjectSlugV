# MS5C 런타임 연결 및 팔레트 확장 리뷰

대상: bba4d8e 이후 변경. 메인 에이전트가 서브에이전트의 로더·CLI·테스트를 읽고 추출기·빌드·원본 비교를 통합했다.

- 헤더는32바이트, payload는 원본 BE 배열이며 정확한 크기·CRC·상한을 검사한다. 입력 실패는 기존 결과를 변경하지 않는다.
- CLI는 숫자와 리소스를 검증한 후 출력을 열며 같은 inode 덮어쓰기를 거부한다.
- 원본 대응은 고정 SHA 프로그램의 bank/group/item 포인터로 추출기가 확인한다. 로더의 offset은 provenance이며 의미적 원본 대응을 단독 보증하지 않는다.
- 팔레트 테이블은 장면별 독립 상태로 비교하도록 수정했다. 다른 장면 등록을 누적하지 않는다.
- `make all test`: Python55개 및 C++ 리소스/로직 테스트 통과.
- `verify_sprite_refresh.py --runtime-resources`:216조건에서 원본0xf246 명령·다음 슬롯 일치.
- `verify_palette_resources.py`:17개 팔레트 원본 준비·업로드 체인 일치.
- `verify_text_scene.py`: 기존 문자 장면 RGB 회귀 일치.

범위: 정상 단일 직사각형2개만 리소스화했다. flip·다중블록·전체 카탈로그·sprite 픽셀 렌더링·전체 프레임 스케줄은 미완료다. ROM과 추출 데이터는 Git에 포함하지 않는다.
