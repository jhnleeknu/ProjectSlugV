# 리소스만 사용하는 C++ 문자 장면 실행

`render_text_scene`은 MS5X 원본 문자 스트림, MS5T 고정 타일, MS5P 팔레트를 읽어 복원한 해석기와 렌더러, RGB 변환을 실행한다. 런타임에는 ROM·Python·Unicorn·기록된 write trace·PNG가 필요하지 않다. 출력 PPM은 확인용 화면이며 게임 데이터로 다시 사용하지 않는다.

```
.venv/bin/python tools/pack_text_scene.py
make build/render_text_scene
./build/render_text_scene extracted/runtime/warning.ms5x extracted/runtime/fixed.ms5t extracted/runtime/palettes.ms5p artifacts/warning.ppm
.venv/bin/python tools/verify_text_scene.py
```

타일·팔레트는 기존 추출과 pack_tiles.py/pack_palettes.py 단계에서 생성한다. 입력 경로와 출력 경로를 실행 인자로 지정한다. 현재 실행은 단일 경고문 장면이며 조작·프레임 갱신·부팅을 포함하지 않는다.

## 검증 구조

verify_text_scene.py는 과거 캡처를 정답으로 읽지 않는다. 원본0x3ef2 초기화,0xcb64 문자 및 팔레트 등록,0x7196 색상 준비,0x72fa 전송을 새로 실행한다. 포트 쓰기에서 tilemap을 구성하고 raw fixed ROM을 MAME nibble 위치로 독립 해석한다. 색상은 pinned MAME 저항망 함수로 새로 계산한 lookup을 사용한다. C++ 실행의320×256×3 RGB바이트를 모두 비교한다.

비교 초기 조건은 zero VRAM/background, cartridge fixed tiles, normal screen이다. 실제 게임의 fixed source 선택과 화면 상태는 아직 미확인이다. 따라서 full-machine boot screenshot이나 원본 전체 게임과 동일하다는 주장은 하지 않는다. 런타임 입력에서 분석 trace를 제거하고 복원 코드가 리소스를 직접 소비하는 통합 단계다.
