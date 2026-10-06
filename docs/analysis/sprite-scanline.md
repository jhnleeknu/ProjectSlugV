# 화면 줄별 스프라이트 선택

기준은 config/mame_sources.json으로 SHA256을 고정한 MAME neogeo_spr.cpp다. 이는 게임의 68000 루틴과 구별되는 하드웨어 계층이다. 원본 게임 명령 생성 검증은 sprite-composition.md를 따른다.

## 확인된 동작

parse_sprites는 sprite0..380을 번호순으로 검사한다. Y 제어 word는 VRAM[0x8200|번호]이며 bit6이0이면 Y=512-(word>>7), 높이=word&63으로 상태를 새로 설정한다. bit6이1이면 이전 스프라이트의 Y·높이를 상속한다. 높이0은 제외하고 높이32 이상은 모든 줄에 포함한다. 나머지는 ((scanline-Y)&511)<높이×16 조건으로 선택한다.

최대96개를 선택하며 홀수 줄은0x8680, 짝수 줄은0x8600부터 번호를 쓴다. 선택하지 않은 나머지와 추가 종료 entry96을0으로 채운다. 선택된 목록의97word 외에는 변경하지 않는다. sprite0은 유효한 번호이므로0을 단순한 영구 종료 표식으로 해석해서는 안 된다. draw_sprites의 목록 소비는 별도 분석 대상이다.

C++ parse_sprite_scanline은0x8800word VRAM과0..511 줄 번호를 받는다. 크기나 범위를 벗어나면 원본 벡터를 보존하고 오류를 반환한다. 실제 화면의 가시 영역·타이머 호출 순서를 이 API의 입력 범위로 추정하지 않는다.

## 원본 참조 비교

verify_sprite_scanline.py는 고정된 MAME의 sprite_on_scanline과 parse_sprites 함수 본문을 수정하지 않고 별도 참조 프로그램으로 컴파일한다. 빈 목록·96개 초과·연결 좌표 상속·무작위 제어 및 실제 MS5C 두 리소스에서 생성한 명령을 VRAM에 적용한 상태를 각각512줄에 걸쳐 비교한다. 매회0x11000바이트 전체를 비교하므로 반대쪽 목록과 다른 VRAM의 보존도 검사한다. 참조 소스 라이선스는 tools/licenses/mame-sprites.txt다.

## 픽셀 렌더링에 남은 의존성

고정된 MAME의 draw_sprites는 ((zoom_y<<8)|zoom_line)로 외부 Y 확대축소 ROM을 조회한다. neogeo.cpp의 ROM_Y_ZOOM은 000-lo.lo, 크기0x20000, CRC5a86cff2, SHA1 5992277debadeb64d1c1c64b0a92d9293eaf7e4a를 지정한다. 이 테이블은 현재 제공된 카트리지의 그래픽 리소스와 별개이며 작업 디렉터리에서 발견되지 않았다. 줌0xff도 조회 경로를 통과하므로 검증하지 않은 선형 표로 대체하지 않는다.

향후 rasterizer는 명시적인 테이블 입력과 타일·팔레트 리소스를 사용해야 한다. 줄별 sprite 선택은 테이블 없이 검증 가능하지만 픽셀 표시·전체 화면·하드웨어 타이밍 검증을 대신하지 않는다. 아직 sprite rasterizer, 자동 애니메이션 상태, 실제 게임의 프레임 스케줄은 연결되지 않았다.
