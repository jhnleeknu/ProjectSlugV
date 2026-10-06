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

인자는 입력·출력·U·V·style·첫 slot·상한·준비된 slot 끝이다. 출력은 검증용 명령 기록(BE32 다음 slot, BE16 주소/값 쌍)이며 이미지 리소스가 아니다. 엔진 코드는 CompositionResource와 emit_sprite_blocks를 직접 호출한다. 아직 sprite rasterizer 및 전체 게임 루프는 연결되지 않았다.

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

표시 준비 전 일반 링의 안정 정렬:

```sh
make build/radix_sprite_queue
.venv/bin/python tools/analyze_sprite_radix.py --cpp
```

`radix_sprite_queue INPUT OUTPUT`은64KiB RAM에서 준비 끝과 생산 끝 사이를 정렬한다. 지연 큐 정렬과는 다른 단계이며, 프로젝트에서는 `radix_sort_sprite_queue` API를 사용한다. 결과 순서뿐 아니라 원본 작업용 배열의 변경도 보존한다.

준비→갱신 연속 경로:

```sh
make build/prepare_sprite_queue build/refresh_sprite_queue
.venv/bin/python tools/analyze_sprite_prepare_queue.py --cpp
```

`prepare_sprite_queue INPUT_RAM OUTPUT_RAM OUTPUT_WRITES RESOURCE1.ms5c [RESOURCE2.ms5c ...]`는 MS5C를 읽어 지연 병합·정렬·명령 준비를 수행한다. 출력 명령은 BE16 주소/값 쌍이며 빈 결과는0바이트다. 이 출력 RAM을 `refresh_sprite_queue`에 전달할 수 있다. 준비 API는 읽기와 준비 cursor가 같을 때만 실행하며 소비 중이면 오류를 반환한다. 이 조건을 무시하고 busy wait를 대신 처리한 것으로 간주하지 않는다.

생성기와 연속 표시 경로:

```sh
make build/produce_sprite_queue build/prepare_sprite_queue build/refresh_sprite_queue
.venv/bin/python tools/verify_sprite_producer.py --cpp
.venv/bin/python tools/verify_sprite_pipeline.py
```

`produce_sprite_queue init INPUT OUTPUT`은64KiB RAM에 원본 큐 초기화를 적용한다. 슬롯 범위는0xffff로 초기화되므로 표시 전에 구성해야 한다. `produce_sprite_queue submit INPUT OUTPUT STATUS D0 D1 D5 D7`의 status는 BE32 Accepted0/Clipped1/Full2/Waiting3이다. 엔진은 initialize_sprite_queue와 submit_sprite API를 사용한다. Waiting은 재개 가능한 코루틴이나 실제 대기 구현이 아니며 원본 대기 조건의 관찰 결과다.

슬롯 영역 설정 및 비활성 영역 검증:

```sh
make build/configure_sprite_pool
.venv/bin/python tools/verify_sprite_pool.py
.venv/bin/python tools/verify_sprite_pipeline.py --disabled-pool
```

`configure_sprite_pool INPUT OUTPUT SELECT LOWER UPPER`는 원본 설정 함수의 메모리 효과를 적용한다. SELECT=0은 첫 영역이고 다른16bit값은 두 번째 영역이다. 초기화된 all-ffff 영역은 비활성이며 준비·갱신이 이를 보존한다. API는 `configure_sprite_pool`이다. 원본 setter는 혼합 sentinel도 만들 수 있으나 dispatcher는 유효 범위 또는 완전 비활성 상태만 지원한다.

### 직사각형 반전

MS5C 리소스를 읽는 emitter와 준비·갱신 큐에서 style bit0/1의 좌우·상하 반전을 지원한다. 큐 bit2는 슬롯 영역 선택이다. 고정 분기용 기존 API의 배치 의미는 유지한다.

```sh
.venv/bin/python tools/verify_sprite_flips.py --cpp
.venv/bin/python tools/verify_sprite_pipeline.py --flips
.venv/bin/python tools/verify_sprite_pipeline.py --flips --disabled-pool
```

원본 분기와 좌표 수식은 `docs/analysis/sprite-flips.md`에 기록했다. PNG 없이 동일한 MS5C 런타임 데이터를 사용한다.

### 여러 직사각형으로 구성된 리소스

MS5C kind2 로더와 emit_sprite_blocks가 개별 블록의 위치·반전·슬롯 배치를 처리한다. 기존 kind1도 같은 경로를 사용한다.

```sh
.venv/bin/python tools/pack_composition_blocks.py
make all test
.venv/bin/python tools/verify_sprite_blocks.py --cpp
.venv/bin/python tools/verify_sprite_pipeline.py --blocks --flips
.venv/bin/python tools/verify_sprite_pipeline.py --blocks --flips --disabled-pool
```

네 리소스의 팔레트 연결과 실제 게임 호출부는 미확인이며, 현재 검증은 RAM과 비디오 명령 단위다.

### 애니메이션 표시 인자 변환

`decode_animation_draw(ram, object_offset, operand, result, error)`가 opcode04 뒤7byte와 오브젝트 상태로 표시 인자를 만든다. `result.skipped`가false이면 `submit_sprite`에 d0/d1/d5/d7을 전달한다. RAM을 수정하지 않으며 명령 포인터 전진은 호출자가 처리한다. 실제 스크립트의 시간·분기 실행기는 아직 연결되지 않았다.

```sh
make all test
.venv/bin/python tools/analyze_animation_draw.py --cpp
.venv/bin/python tools/verify_sprite_pipeline.py --blocks --flips --animation
.venv/bin/python tools/verify_sprite_pipeline.py --blocks --flips --animation --disabled-pool
```

검증 CLI `decode_animation_draw INPUT_RAM INPUT_OPERAND OUTPUT OBJECT_OFFSET`의 OUTPUT은 skipped,d0,d1,d5,d7의BE32 다섯 word다. 이 출력은 검증 기록이며 별도 런타임 리소스 형식이 아니다.
