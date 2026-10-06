# C++ 런타임 기반

현재 구현은 MS5T 타일 카탈로그 로더와 원본 오브젝트 필드 초기화 함수다. 플레이 가능한 게임이나 애니메이션 엔진은 아직 아니다.
C++11 기본 문법으로 작성하며, 리소스 규격은 ../docs/resource-format.md를 따른다.

저장소 루트에서:

```sh
make setup-tools
python3 tools/decode_tiles.py
python3 tools/verify_tiles_reference.py
python3 tools/pack_tiles.py
make
./build/check_tiles extracted/runtime/sprites.ms5t extracted/runtime/fixed.ms5t
make test
```

사전 입력은 검증된 extracted/media/ 데이터다. 이 입력을 만드는 단계는 docs/analysis/media-decryption.md에 있다.
런타임은 PNG 미리보기가 아닌 .ms5t 파일을 읽는다. 팔레트와 오브젝트 조합은 후속 작업이다.
check_tiles는 현재 파일 검증 CLI이며 렌더링 화면을 제공하지 않는다.
테스트 실행은 macOS/Linux POSIX 임시 파일 API를 사용하고 로더 자체는 표준 C++11이다.

오브젝트 초기화 원본 CPU 비교: `.venv/bin/python tools/verify_object_reset.py` (`make all` 후 실행). 이 함수는 메모리 효과를 검증했으며 전체 게임 루프는 아직 아니다.

## 리소스로 단일 문자 장면 실행

```
make build/render_text_scene
./build/render_text_scene extracted/runtime/warning.ms5x extracted/runtime/fixed.ms5t extracted/runtime/palettes.ms5p artifacts/warning.ppm
```

`warning.ms5x`는 `.venv/bin/python tools/pack_text_scene.py`로 생성한다. 타일·팔레트 런타임 패키지는 기존 추출 단계에서 생성해야 한다. 이 실행 파일은 세 런타임 패키지만 읽어 원본 문자 명령을 해석하고 화면을 만든다. 분석 trace, PNG, Python이나 원본 ROM을 실행 중에 읽지 않는다.

현재는 조작 없는 경고문 단일 장면이며 전체 게임 실행은 미완료다. 출력 PPM은 확인용이다. full pipeline 검증은 `.venv/bin/python tools/verify_text_scene.py`로 수행한다.

스프라이트 합성 리소스를 직접 읽는 C++ 경로:

```sh
.venv/bin/python tools/pack_compositions.py
make build/emit_sprite_resource
build/emit_sprite_resource extracted/runtime/composition_002152.ms5c artifacts/sprite-writes.bin 160 384 0x1500 0 380 0
.venv/bin/python tools/verify_sprite_refresh.py --runtime-resources
```

인자는 입력·출력·U·V·style·첫 slot·상한·준비된 slot 끝이다. 출력은 검증용 명령 기록(BE32 다음 slot, BE16 주소/값 쌍)이며 이미지 리소스가 아니다. 엔진 코드는 CompositionResource와 emit_sprite_rectangle_refresh를 직접 호출한다. 아직 sprite rasterizer 및 전체 게임 루프는 연결되지 않았다.

줄별 하드웨어 스프라이트 선택:

```sh
make build/parse_sprite_scanline
.venv/bin/python tools/verify_sprite_scanline.py
```

`parse_sprite_scanline INPUT OUTPUT SCANLINE`은 BE VRAM0x11000바이트를 읽어 홀짝에 맞는97word 목록만 갱신한다. 엔진에서는 같은 이름의 벡터 API를 직접 호출한다. 검증은 실제 MS5C 두 개의 명령을 포함해512줄씩 비교한다. 화면 픽셀 변환과 비디오 타이머는 아직 별도 미구현 단계다.

지연 표시 큐 정렬과 태그 갱신:

```sh
make build/sort_sprite_queue
.venv/bin/python tools/analyze_sprite_sort.py --cpp
```

`sort_sprite_queue INPUT OUTPUT TAG`는 CPU0x100000에 대응하는64KiB RAM에서 지연 목록을 일반 링에 합치며 새 태그를 저장한다. 실제 런타임에서는 `sort_deferred_sprites` API를 사용한다. 전체 큐 생성·소비 스케줄은 아직 연결하지 않았다.

MS5C로 역방향 슬롯을 채우려면 마지막 인자에 `reverse`를 추가한다. 이때 FIRST는 높은 시작 경계, LIMIT은 낮은 경계, CACHED는 준비된 슬롯의 시작이다. 기존 인자를 생략한 동작은 forward다.

```sh
build/emit_sprite_resource extracted/runtime/composition_002152.ms5c artifacts/reverse-writes.bin 160 384 0x1500 380 0 380 reverse
.venv/bin/python tools/verify_sprite_reverse.py --runtime-resources
```

역방향은 하드웨어 슬롯 번호의 배정 방향이다. 타일 열의 순서를 뒤집지 않는다.

큐 단위 갱신 통합 검증:

```sh
make build/refresh_sprite_queue
.venv/bin/python tools/analyze_sprite_refresh_queue.py --cpp
```

`refresh_sprite_queue INPUT_RAM OUTPUT_RAM OUTPUT_WRITES RESOURCE1.ms5c [RESOURCE2.ms5c ...]`는 전체 큐를 처리한다. 비디오 출력은 BE32 처리 여부0/1 다음 BE16 주소/값 쌍이다. 게임 프로젝트는 같은 이름의 API에 로드된 리소스를 전달하면 된다. 아직 일반 단일 직사각형만 지원하며 다른 분기는 명시적으로 거부한다. 상세 계약은 docs/analysis/sprite-refresh-queue.md를 따른다.
