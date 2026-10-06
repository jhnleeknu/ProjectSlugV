# C++ 런타임 리소스 규격 v1

PNG·WAV 등은 사람이 확인하는 출력이다. C++ 게임은 런타임 패키지를 읽는다. 원본 팔레트나 시퀀스가 미해석이면 그 사실을 유지하고 확인용 색상·음원을 게임 리소스로 대체하지 않는다.

## 단계와 경로
- 원본: mslug5.zip (수정하지 않음).
- 복호화 데이터: extracted/program, extracted/media.
- 분석 중간 데이터: extracted/tiles의 indexed8 배열·JSON.
- C++ 런타임 리소스: extracted/runtime의 타입별 바이너리 및 manifest JSON.
- 확인용 출력: artifacts/previews. 게임 의존성에 포함하지 않는다.

## 타일 카탈로그 MS5T
헤더는 32바이트다. 구조체 메모리를 그대로 파일로 쓰지 않는다. magic 뒤의 정수는 모두 uint32 little-endian이다.

| 바이트 오프셋 | 필드 | 값 |
|---:|---|---|
| 0 | magic | ASCII MS5T |
| 4 | version | 1 |
| 8 | kind | 1=스프라이트, 2=고정 문자 |
| 12 | width | kind 1:16, kind 2:8 |
| 16 | height | kind 1:16, kind 2:8 |
| 20 | count | kind 1:524288, kind 2:4096 |
| 24 | payload_size | width × height × count |
| 28 | crc32 | payload의 표준 ZIP CRC32 |

payload는 tile → row → column 순서의 1바이트 색상 인덱스다. 값 범위는 0..15이고 0은 투명하다. 압축하지 않는다. 파일 길이는 32 + payload_size와 정확히 같아야 한다.

리소스 ID는 mslug5.sprite_tiles / mslug5.fixed_tiles다. 타일 ID는 원본 카탈로그 인덱스를 유지한다. 디코딩된 소스 오프셋은 sprite ID × 128, fixed ID × 32다. 이 주소는 복호화 영역 오프셋이며 CPU 주소나 원래 암호화 파일 오프셋이 아니다.

manifest.json에는 런타임 파일 크기·SHA256, source 파일·SHA256, palette_status=unresolved를 기록한다. 런타임 로더는 MS5T 헤더·파일 크기·CRC32·픽셀 범위를 검사한다. JSON은 생성 이력과 빌드 도구용 메타데이터이며 타일 payload에 중복 삽입하지 않는다.

## 이후 확장
팔레트·애니메이션·맵·오브젝트·사운드에 별도 타입과 버전 있는 구조를 정의하고 C++ 로더를 함께 구현한다. 현재 타일 카탈로그만으로 원본 캐릭터나 음악이 완성되었다고 취급하지 않는다. 사운드는 코드·명령·시퀀스 분석 뒤 재현 방식에 맞춰 런타임 규격을 확정한다.

## 초기 오브젝트 테이블 MS5I
리소스 ID는 `mslug5.object_boot`다. `object_boot.ms5i`는 160바이트이며 헤더 32바이트와 원본 BE 레코드 128바이트로 구성한다. magic 이후 헤더 정수는 uint32 little-endian이다.

| 오프셋 | 필드 | 값 |
|---:|---|---|
| 0 | magic | ASCII MS5I |
| 4 | version | 1 |
| 8 | count | 8 |
| 12 | record_size | 16 |
| 16 | source_rom_offset | 0x268a |
| 20 | payload_size | 128 |
| 24 | crc32 | payload의 ZIP CRC32 |
| 28 | reserved | 0 |

각 레코드는 BE uint32 RAM 주소, BE uint32 콜백 주소, BE uint16 네 개다. 네 word는 오브젝트 +0x76부터 복사한다. 콜백 주소는 원본 CPU 함수 식별자이며 호스트 함수 포인터로 캐스팅하지 않는다. 원본 주소와 C++ 구현을 연결하는 디스패치는 별도로 구현해야 한다.

C++ 로더는 헤더·CRC·정확한 파일 길이·주소 정렬·범위·오브젝트 간 겹침을 검사한다. 실패하면 기존 테이블을 보존한다. `tools/pack_object_boot.py`는 검증된 프로그램에서 생성하고 `object_boot.manifest.json`에 SHA256과 원본 위치를 기록한다.

## 원본 ID 기반 팔레트 MS5P

리소스 ID `mslug5.palettes`, 파일 `palettes.ms5p`, 이력 `palettes.manifest.json`이다. 현재 카탈로그는 확인된 고정 등록 테이블 두 개의 source ID 0x897,0xb01,0xb02만 담는 **미완성 sparse 카탈로그**다. source ID는 destination 슬롯 번호와 다르다. 이후 확인한 ID를 기존 번호 그대로 추가한다.

헤더 32바이트: ASCII MS5P 이후 uint32 little-endian 7개다.

| 오프셋 | 필드 | 값 |
|---:|---|---|
| 4 | version | 1 |
| 8 | count | 1..65536 |
| 12 | record_size | 68 |
| 16 | payload_size | count×68 |
| 20 | crc32 | payload ZIP CRC32 |
| 24 | reserved | 0 |
| 28 | reserved | 0 |

각 레코드: LE uint32 원본 source ID(0..65535), 원본 BE uint16 색상값16개, 일반 조회 변환 후 BE uint16 하드웨어 색상값16개. source ID 오름차순이며 중복을 허용하지 않는다. 변환 후 첫 word는0이다. 원본 첫 word는 별도로 보존한다. 나머지15개는 원본0x4718의 signed16 lookup 계산을 적용한 결과다. 이 값은 RGB가 아니며 혼합·명암 분기 결과를 미리 대체하지 않는다.

C++ 로더는 정확한 길이, 헤더, 상한, CRC, ID 정렬·중복, 첫 변환 word를 검증한다. 실패하면 기존 레코드를 보존한다. manifest에는 각 ID의 원본 위치, 15개 lookup 위치, 이 ID를 참조하는 등록 테이블·레코드·destination slot·flags를 저장한다. `catalog_status=incomplete_sparse`를 유지한다.

## 원본 고정 문자 스트림 MS5X

고정 문자 스트림과 palette source ID→slot 연결을 함께 담는다. 현재 리소스 ID `mslug5.fixed_text.00cb80`, 파일 `warning.ms5x`, 이력 `warning.manifest.json`이다. 기록된 타일 쓰기나 완성 이미지가 아니라 원본 제어 byte를 C++가 해석한다.

32바이트 헤더: magic ASCII MS5X, 이후 uint32 LE 7개다.

| 오프셋 | 필드 | 값 |
|---:|---|---|
| 4 | version | 1 |
| 8 | kind | 1=원본 fixed text stream |
| 12 | id | 원본 프로그램 오프셋, 0..0x7fffff |
| 16 | binding_count | 1..16 |
| 20 | payload_size | binding_count×8 + script bytes |
| 24 | crc32 | payload ZIP CRC32 |
| 28 | reserved | 0 |

payload 앞에는 LE uint32 slot(0..15), LE uint32 source palette ID(0..65535)의8바이트 레코드를 binding_count개 둔다. slot은 중복 불가다. 뒤에는1..1048576바이트의 원본 명령 스트림을 그대로 둔다. 제어 operand로0이 포함될 수 있으므로 raw NUL 위치만으로 끝을 추정하지 않는다. 파일 길이는32+payload_size와 같아야 한다.

로더는 형식·길이·CRC·binding 범위/중복을 검사한다. bytecode 해석 가능 여부는 decoder가 검사한다. kind1의 현재 C++ decoder는 ASCII/font61만 지원하며 나머지를 오류로 보고한다. 리소스는 palette catalog의 source ID를 참조하며 실행 프로그램은 누락된 ID를 거부한다.

현재 단일 장면 실행은 initial cursor/style0, zero VRAM/background, normal screen, cartridge fixed tiles를 사용한다. 이 실험 조건은 manifest와 실행 문서에 명시하며 원본 부팅에서 관찰한 상태로 취급하지 않는다.

## 스프라이트 합성 리소스 MS5C

`pack_compositions.py`가 확인된 ID 0x2152/0x2952를 `composition_002152.ms5c`, `composition_002952.ms5c`로 저장한다. manifest는 원본 해시, bank/group/item, CPU 주소와 ROM 오프셋, 실제 호출부의 style·팔레트 연결을 기록한다. 카탈로그는 아직 incomplete_sparse다.

32바이트 헤더: ASCII MS5C 다음 LE uint32 7개는 version=1, kind=1(일반 단일 직사각형), packed ID, source ROM offset, payload size, payload ZIP CRC32, reserved=0 순서다. ID는 23bit이며 bank selector(ID&7)는0..5다. 원본 위치와 payload 범위는8MiB 안에 있어야 한다. ID와 원본 위치의 실제 대응은 추출기가 고정 해시 ROM의 포인터를 따라 확인한다.

payload는 원본 BE 데이터를 보존한다: uint16 0x0100, dx, dy, 폭/높이 각 uint8, 이후 열 우선 순서의 attribute/tile uint16 쌍이다. 폭1..255, 높이1..32이며 크기는8+폭×높이×4다. C++ 로더는 길이·CRC·종류·범위를 검사하고 실패 시 기존 리소스를 보존한다. 런타임 명령 생성은 ROM이나 PNG를 읽지 않고 이 payload를 직접 사용한다.

팔레트 MS5P는 테이블0xddf08 추가로 현재17개 source ID를 포함한다. 이 테이블의 slot21/22는 source ID0xe91/0xe92다. 팔레트 선택은 호출부 상태이므로 합성 리소스 자체의 고정 속성으로 취급하지 않는다.

### MS5C v1 kind 2 — counted rectangles

kind=2는 원본 BE16 헤더의 상위 byte를 블록 수(1..255), 하위 byte를 원본 그대로 보존한다(표시 소비기에는 영향 없음). 그 뒤 블록 수만큼 `dx BE16, dy BE16, width uint8, height uint8, attribute/tile BE16 pairs`가 반복된다. 블록에는 별도0100 헤더가 없다. 각 블록 폭1..255·높이1..32, 열 우선 순서를 유지한다. 길이는 `2 + sum(6 + width*height*4)`이며 정확히 일치해야 한다. kind1의 기존 길이·개수 제한은 유지한다.

`pack_composition_blocks.py`가 ID02382a/02402a/02482a/000122/029802/070002 여섯 리소스를 저장하고 별도 `composition_blocks.manifest.json`에 원본 위치와 블록 치수를 기록한다. 이들의 소비 동작은 원본 CPU 직접 호출로 검증했지만 자연스러운 게임 실행에서의 사용 여부와 호출부 팔레트는 아직 미확인이다.

런타임 `emit_sprite_blocks`는 kind1과kind2의 raw payload를 읽고 각 블록의 상대좌표와 현재 슬롯을 적용한다. 실패 시 출력은 보존하며 슬롯이 소진되어도 나머지 payload의 형식 오류를 검사한다. 따라서 손상된 리소스에 대한 동작은 원본 CPU의 메모리 접근을 재현하는 계약이 아니다.

kind2 하위 header byte의 비영 값은 표시 소비기에서 출력에 영향을 주지 않는다. 실제0101/0103 리소스 및 단일/3블록의0..255 byte sweep8192조건으로 확인했다. 다른 호출자에서 이 byte를 이용하는지는 미확인이다. kind1의0100 제한은 이전 규격 그대로 유지한다.

## 애니메이션 리소스 MS5A

32byte 헤더: ASCII MS5A와LE32 7개(version1,kind1,source CPU address,source ROM offset,payload size,payload CRC32,reserved0). kind1은 고정 프로그램 영역이라 CPU주소=ROMoffset이고 둘 다100000미만이다. payload는1byte이상이며 고정 영역 끝을 넘지 않는다. 원본 명령 byte와절대분기주소를그대로보존한다.

로더는 헤더·범위·파일정확길이·CRC를검사하며 명령지원여부는 실행기가검사한다. 실패시기존리소스는보존한다. `pack_animation.py`는 확인된호출부와자기루프끝을검사해6f1e2..6f21a의56byte를포장하고 참조하는 MS5C 네개도함께생성한다. 명령·호출부·그룹·감소량·원본해시는 `animations.manifest.json`에기록한다. 현재카탈로그는대표루프하나이며전체추출이아니다.

## 고정 ROM 데이터 창 MS5D

ASCII MS5D + LE32 7개(version1,kind1,CPUbase,ROMoffset,payloadsize,CRC32,reserved0)의32byte 헤더다. CPUbase=ROMoffset<100000이고payload는1byte이상이며고정ROM끝을넘지않는다. byte는원본그대로보존하며파일길이는정확히32+payloadsize다. MS5A와주소표현을공유하되MS5D는명령스트림이아닌불변데이터창이다.

`pack_animation_data.py`는필드테이블후보범위4a76c..4a88e(290byte)와callback1e의byte인덱스조회창6431a..6471a(1024byte)를포장한다. 뒤의창이하나의논리테이블전체라는주장은하지않으며manifest에이차이를명시한다. 실행기는필요한BE16/BE32읽기가제공된한창안에완전히들어가야한다. 창의중첩은거부하고인접창을자동결합하지않는다.
