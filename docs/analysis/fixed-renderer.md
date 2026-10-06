# 고정 레이어 렌더링과 확인용 색상

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
MAME 기준은 config/mame_sources.json의 고정 리비전·해시다.

## C++ 렌더러

`render_fixed_layer_words`는 MS5T fixed 타일에서 320×256 word framebuffer를 만든다. VRAM 입력은0x7000..0x74ff의1280word이며 `column*32+row` 순서다. 하위12bit 타일ID와 상위4bit palette slot을 사용한다. 픽셀0은 destination 배경을 보존하고, 나머지는 palette[slot*16+pixel] 하드웨어word를 쓴다. 이는 pinned neogeo_spr.cpp의 unbanked fixed-layer 주소 계산에 대응한다.

`render_fixed_words`는 검증용 드라이버다. 복원한 C++ 문자 해석기가 생성한 write stream을 적용하고 MS5T fixed 타일과 MS5P source0x897을 slot0으로 사용한다. slot0 대응은 원본0xcb64의 등록 테이블에 근거한다. 시작 VRAM과 배경은0으로 설정한 실험 조건이며, 원본 부팅 상태를 관찰한 것으로 표현하지 않는다. 다른 슬롯의 명령은 조용히 대체하지 않고 거부한다.

검증은 디코딩된 타일과 다른 경로로 수행한다. tools/verify_fixed_renderer.py는 raw fixed ROM의 MAME pair offset16,24,0,8 및 low/high nibble을 직접 읽는다. 경고문 frame의81920픽셀 전체가 C++ 출력과 일치했다. word frame SHA256 `2a98f171bbe4c97511e3d74a1438f3c93a63c5df10ba0179fb9a2dfc50eea13b`.

## 색상 조회표

neogeo_v.cpp와 resnet.cpp/h를 동일 MAME 리비전에서 확보하고 해시를 고정했다. tools/inspect_color_reference.py는 원본 create_rgb_lookups, compute_resistor_weights, combine_weights를 추출하여 독립 reference 바이너리로 실행한다. reference만 원본 문법 때문에 C++17로 컴파일하며 프로젝트 엔진은 C++11을 유지한다. 라이선스는 tools/licenses/mame-colors.txt다.

32단계 × normal/dark/shadow/dark_shadow 4개 열128바이트 조회표 SHA256 `1a35fd99068aba9ed9e05a97335f63ded453d32c8ddbb567c64a0d45da630ed4`. 단순 5bit 선형 확대가 아니라 MAME의 저항망 가중값을 사용한다. 원본 pulldown parameter는 int이므로 dark_shadow 저항의 실수→정수 변환도 원본 함수를 그대로 실행해 보존한다.

확인용 PNG는 normal screen(그림자 없음)을 가정하고 word bit15로 dark 열을 고른다. 채널 주소는 원본 paletteram_w의 bit 배치를 적용한다. 이 RGB 변환은 현재 확인용 Python에 있으며 C++ 하드웨어 계층의 완성으로 간주하지 않는다.

## 재현과 한계

```
make build/render_fixed_words
.venv/bin/python tools/verify_fixed_renderer.py
.venv/bin/python tools/inspect_color_reference.py
.venv/bin/python tools/preview_fixed_frame.py
```

선행 산출물: verify_fixed_text.py의 trace, fixed.ms5t, palettes.ms5p. 결과 artifacts/previews/warning-fixed.png를 직접 확인하여 원본 스트림의 경고문이 읽히는 것을 점검했다. PNG는 확인용이며 엔진 입력에 넣지 않는다.

이 결과는 선택한 cartridge fixed 타일로 그린 warning fixture다. 실제 fixed source 선택, BIOS 화면, crop·scanline timing, shadow 제어, 전체 게임 부팅 및 sprite 합성은 아직 검증하지 않았다. full-machine 화면 비교를 대신하지 않는다.
