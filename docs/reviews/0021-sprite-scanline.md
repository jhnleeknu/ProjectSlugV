# 줄별 스프라이트 선택 리뷰

대상:135b0b6 이후 변경. 이전 goal turn은 MS5C 통합과 검증·커밋으로 진척이 있었다. 이번 변경은 렌더링 하드웨어 계층의 실제 선택 로직을 추가한다.

메인 에이전트가 고정된 MAME parse_sprites/sprite_on_scanline을 읽어 규약을 확정하고, 서브에이전트의4개 C++ 파일을 리뷰했다. 원본 함수 본문을 수정하지 않은 별도 참조 프로그램으로 전체 VRAM을 비교했다.

- unsigned 차이와9bit 마스크가 원본 음수 차이의9bit wrap을 명시적으로 재현한다.
- rows0은 목록 생성에서 제외한다. 별도 sprite_on_scanline 함수의 rows0 처리와 혼동하지 않는다.
- 381개 sprite 검사,96개 제한, 추가 종료 엔트리와 반대 parity 보존을 확인했다.
- 입력 크기·범위 검증은 쓰기 전에 수행한다. CLI는 입력과 동일 inode 출력 및 정확하지 않은 파일 크기를 거부한다.
- `verify_sprite_scanline.py`:6가지 VRAM 상태×512줄=3072경우, 각69632바이트가 고정 MAME 참조와 일치했다.
- `make all test`: Python55개 및 C++ 테스트 통과.

검증 범위는 줄별 번호 선택이다. 원본 게임의 실제 frame timing, sprite rasterizer, zoom ROM 데이터, 전체 프레임 동일성을 주장하지 않는다. zoom 테이블 의존성을 분석 문서에 명시했다.
