# C++ 하드웨어 색상 변환

`ms5::hardware_color_to_rgb(word, shadow)`는 Neo Geo 색상 word와 화면 shadow 상태를 RGB8로 변환한다. 32×4 정수 조회표를 사용하며 엔진 실행 때 부동소수 저항망 계산이 필요하지 않다. 엔진 C++11 규칙을 유지한다.

조회표는 고정 MAME 리비전 `df09546b783c419889a2386bec9402883574b881`의 neogeo_v.cpp와 resnet.cpp/h로 생성한다. 소스 SHA256은 config/mame_sources.json에 기록했다. 라이선스는 tools/licenses/mame-colors.txt다. 이 조회표는 게임 ROM 데이터가 아니라 하드웨어 모델에서 계산한 값이므로 engine/src/color_lookup.inc에 보관한다.

```
.venv/bin/python tools/generate_color_lookup.py
make build/convert_color_words
.venv/bin/python tools/verify_hardware_color.py
```

원본 MAME create_rgb_lookups와 paletteram_w를 그대로 독립 reference 빌드에서 실행했다. set_pen_color의 출력만 간단한 sink에 저장한다. 65536개 word 모두에서 normal/shadow RGB를 수집하고 두 팔레트 bank에서도 확인했다. C++11 API의393216 RGB바이트가 모두 일치했다. 출력 SHA256 `b3991a9e36e676849b2a92740fa9e470607f66dc86d7b20527b2c5eff4380cd2`.

bit15는 dark column을 선택한다. red는 bit14와 bits8..11, green은 bit13과 bits4..7, blue는 bit12와 bits0..3에서5bit 입력을 구성한다. shadow는 조회표 열에2를 더한다. 임의 gamma나 선형5bit 확장을 추가하지 않는다.

`convert_color_words INPUT OUTPUT normal|shadow`는 BEword 입력을 RGB 순서의3byte 출력으로 바꾼다. preview_fixed_frame.py도 이제 이 C++ CLI를 사용하며 Python은 PNG 포장만 수행한다. 출력 RGB나 PNG는 진단용이고 런타임 리소스에는 원래 word를 유지한다.

검증 범위는 정적 색상 모델 전체다. 실제 CRT 아날로그 발색, 장치 bank 전환 시점, 화면 shadow 상태를 정하는 게임 로직, frame timing 및 full-machine 영상 비교는 별도다.
