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

ASCII MS5D + LE32 7개(version1,kind1,CPUbase,ROMoffset,payloadsize,CRC32,reserved0)의32byte 헤더다. CPUbase=ROMoffset<100000이고payload는1byte이상이며고정ROM끝을넘지않는다. byte는원본그대로보존하며파일길이는정확히32+payloadsize다. MS5A와주소표현을공유하며MS5D자체는불변ROM데이터창이다. 개별소비기가원시payload를표·레코드·장면명령스트림으로해석한다.

`pack_animation_data.py`는필드테이블후보범위4a76c..4a88e(290byte)와callback1e의byte인덱스조회창6431a..6471a(1024byte)를포장한다. 뒤의창이하나의논리테이블전체라는주장은하지않으며manifest에이차이를명시한다. 실행기는필요한BE16/BE32읽기가제공된한창안에완전히들어가야한다. 창의중첩은거부하고인접창을자동결합하지않는다.

### MS5P 특수 채우기 조회 프로필

바이너리 MS5P version1/68바이트 레코드를 그대로 사용하되 카탈로그 식별자를 `mslug5.palette-fill-selectors`, lookup_profile을 `fill_signed_word`로 분리한다. 파일은 `palette_fill.ms5p`다. 이 카탈로그의 ID는 일반 source palette ID가 아니라 원본8b64 입력의 하위11비트(0..2047)다. 안정적인 리소스 키는 `palette-fill:<선택값>`이며 일반 팔레트 카탈로그와 합치지 않는다.

원본 주소는 base+signed16((selector*32)&ffff)이며 각 레코드 manifest에 실제 ROM offset을 남긴다. 단일 색 변환은 기존4718 규칙과 같고 raw16워드와 hardware16워드를 모두 보존한다. converted word0은0이지만 setup API는 목적지 word0을 덮어쓰지 않는다.

`setup_palette_fill`은 전용 카탈로그의 완전한2048개 정렬ID 구성을 요구한다. 범위 전체를 추출했다는 사실이 모든 선택값의 실제 게임 사용을 뜻하지는 않는다. 카탈로그 프로필은 manifest/API 계약이며 MS5P 바이너리 magic 자체가 프로필을 구분하는 것은 아니다.

### MS5D 메뉴 descriptor 해석

기존 MS5D v1 데이터 창을 그대로 사용한다. 현재 `control_menu.ms5d`는 fixed ROM937e..942f의문자열과93e0 descriptor를보존한다. `menu:000093e0` ID와원본주소/해석필드는manifest에기록한다.

descriptor는BE필드의16byte헤더(title:u32,min_width:u8,min_height:u8,callback6:u32,callback10:u32,flags:u16)와10byte항목(title:u32,callback:u32,argument:u16)이다. title=ffffffff인4byte가종료하며0/fffffffe는항목으로보존한다. C++해석기는현재255개이내를지원한다. callback주소는논리코드참조이며호스트함수포인터가아니다. 문자데이터는원본386e스트림으로보존하고Unicode/PNG로대체하지않는다.

### MS5D 입력 재생 스트림

`input_streams.ms5d`는 fixed ROMf01fe..f1a0e의6160바이트를 보존한다. 안정 ID는 `input-streams:000f01fe`다. f0dfe의 BE32 두 포인터는 f01fe/f07fe, f1a06의 두 포인터는 f0e06/f1406을 가리킨다. 네 버퍼는 각각600바이트이며 테이블과 인접 바이트까지 같은 창에 유지한다. 마지막 이벤트의 다음 바이트 조회 때문에 버퍼 경계를 임의로 분리하거나 padding하지 않는다.

원본 selector180==0000을 추출 시 검증한다. 실제 `sample_input`은 이 이미지의352a 재생 분기를 사용하며 기록용 버퍼도 보존한다. 기간·버튼 토글 해석과 미지원 범위는 `docs/analysis/input-sampler.md`에 기록한다. PNG/재생 오디오가 아닌 C++ 직접 사용 MS5D 리소스다.

### MS5D 입력 상태 조회 창

`input_status.ms5d`는 고정 ROM b58..c58의256바이트를 보존한다. 안정 ID는 `input-status:00000b58`다. 원본b68이 `(4 + slot_byte) & 255`로 조회하므로 명령 바이트와 겹치는 부분도 같은 창에 유지한다. 범위 전체가 자연스럽게 쓰이는256개 의미 항목이라는 주장은 하지 않는다. 해석과 사용 API는 `docs/analysis/input-status.md`에 기록한다.

### MS5D 메인 초기화 팔레트 등록 표

`main_startup.ms5d`는 기존 MS5D v1 kind1으로 고정 ROM `e7b58..e7bc0`의104바이트를 그대로 보존한다. 안정 ID는 `main-startup:000e7b58`이다. payload는17개의6바이트 레코드와 마지막 BE16 `ffff` 종결자로 구성된다. 레코드는 `destination_slot:BE16`, `source_id:BE16`, `flags:u8`, `sixth_byte:u8`이며 여섯 번째 바이트도 원본 그대로 유지한다. 주소·해시·레코드별 메타데이터는 manifest에 기록한다.

목적 슬롯 `ffff`는 종결자다. source ID `ffff`는 해당 슬롯을 비활성화하는 값이며 실제 팔레트 데이터 ID로 추출하지 않는다. `pack_palettes.py`는 이 등록 근거를 기존 희소 MS5P 카탈로그에 추가하고, 비활성 레코드도 bindings 메타데이터에 `disabled:true`와 함께 보존한다. 이 표의 유효 고유 source ID는11종이다. 표와 카탈로그 추출은 전체 메인 초기화 실행이나 자연 도달성 검증을 뜻하지 않는다.

### MS5D 고정 게임 레코드 창

`pack_game_records.py`는 기존 MS5D v1 kind1으로 고정 ROM `4cf64..4d0a4`의320바이트를 `game_records.ms5d`에 보존한다. 안정 ID는 `game-records:0004cf64`다. payload는 ID0..19의16바이트 레코드20개이며, 소비하지 않는 바이트도 삭제·재배열하지 않는다. CPU주소와 canonical decrypted ROM파일 오프셋은 이 고정 영역에서 같다. manifest에는 전체 프로그램·payload·컨테이너 및 각 레코드의 SHA256, 원본 주소, 전체 raw bytes와 의미 이름을 붙이지 않은 필드를 기록한다.

원본 `4d81c..4d84e`는 D1.word를 unsigned20미만으로 검사한 뒤 `4cf64 + (D1 & ff)*16`을 조회한다. 범위를 벗어나면 TRAP #15로 간다. 읽는 필드는 상대 byte1/byte2와 BE16 word0a/word0c/word0e다. `481de..48210`은 이 조회기를 호출하고 선택한 RAM 구조체에 값을 기록한다. 추출기는 두 명령 창의 정확한 바이트와 고정 프로그램 해시를 검증한다. payload SHA256은 `9b1c4db78844053dff88ac7c863b15852c1ad1b9e500a831ed5a01fa9eff923c`이며32바이트 헤더를 포함한 파일 길이는352바이트다.

이 창은 기존 `FixedDataResource`가 직접 읽는 원본 BE데이터다. 레코드 필드의 게임 의미, 자연스러운 호출부 도달성, 전체 초기화 실행과 원본 TRAP 처리는 이 추출 규격의 검증 범위가 아니다.


### MS5D v1 kind2 — 뱅크 ROM 데이터 창

kind1의 고정 첫1MiB 계약은 유지한다. kind2는 같은32-byte header에서kind만2이며 CPUbase와ROMoffset을 따로 해석한다. Version1,CRC32,reserved0,정확한파일길이 규칙은kind1과같다. CPUbase는200000이상2ffff0미만이며payload는비영이고끝exclusive가2ffff0을넘지않는다. 이는 기존 v1 컨테이너의 상한이다. 실제 MS5 PVC cart RAM overlay는2fe000부터 시작하므로 소비기는2fe000..2fffff를 장치 상태로 읽어야 하며, 이 주소에 대응하는 raw ROM 리소스가 있다고 CPU ROM으로 읽어서는 안 된다.

매핑은 `position = CPUbase - 200000`, `bank_base = ROMoffset - position`이다. ROMoffset은position이상이고bank_base는100000이상700000이하의100000배수여야한다. ROMoffset+payloadsize는canonical8MiB를넘지않는다. 이는정렬된1MiB bank 창의주소표현이며모든PVC bank offset을지원한다는뜻이아니다. `load_fixed_data_resource`는kind1만, `load_banked_data_resource`는kind2만받는다. 공통FixedDataResource의source CPU/ROM필드로매핑을보존한다.

새 `program_bus`는 현재 선택된 bank로 physical offset을 계산한 뒤 kind2 리소스의 physical span을 조회한다. 추출 당시 CPUbase가 현재 CPU 주소와 같을 필요는 없다. WORD마다 유일한 완전한 창을 요구하고, LONG은 두 WORD 창을 각각 사용할 수 있다. 현재 PVC/vector 상태는 별도 명시적인 입력이다. 자세한 계약은 `analysis/animation-program-bus-contract.md`에 있다.

`extracted/runtime/animation_banked_reads/`는 원본 isolated40 관측에서 실제 읽힌 구간을 보존한 v1 리소스37개다. 각 stable ID는kind/CPU주소/physical주소를 포함하고 manifest는 원본 hash, 실제 읽기 PC/조건과 생성 도구를 연결한다. 이 추출기는 실제 overlay 아래2fe000까지만 ROM 구간으로 수집한다. 기존 v1 kind2가 각 physical1MiB 끝16BYTE를 표현하지 못하는 한계는 그대로이며, 아래kind3이 전체 physical ROM 표현을 추가한다. 기존 kind1/2 검증 범위는 변경하지 않는다.

Scene opcode04의palette root/lookup/binding은ROM bank200000을사용하므로이경우CPU와ROMoffset이수치상같다. 이를고정ROM으로잘못분류하지않으며manifest에도bank_base=200000을남긴다. 실제bank선택의word2ffff2=1000,word2ffff0=0은scene command의순서있는hardware writes로별도보존한다. Rawbinding은6-byte records와마지막BE16ffff이며구조는기존main startup팔레트등록표와같다. Palette색상자체의전송및후속frame표시는이데이터창규격에포함하지않는다.

### MS5D v1 kind3 — physical 프로그램 ROM 창

동일한32BYTE header에서version1/kind3,CPU필드ffffffff,physical ROM offset,payload size,CRC32,reserved0을 사용한다. CPU필드는 binding 없음의 sentinel이며 실제 CPU주소로 해석하지 않는다. Payload는1..100000BYTE, physical 시작은0..7fffff, 끝exclusive는800000 이하다. 정렬 제한이 없고 파일 길이는정확히32+payloadsize다. Payload는 canonical program bytes 그대로다.

별도 `PhysicalRomResource`와 `load_physical_rom_resource`가 이 의미를 보존한다. 기존 FixedDataResource/kind1·2 loader에 새 kind를 혼입하지 않는다. Loader는header·범위·CRC·정확길이를 검사하고 실패 시 기존 객체를 보존한다. 기존 loader는kind3을, 새 loader는kind1/2를 거절한다.

`pack_physical_program.py`는8MiB 전체를 `extracted/runtime/program_rom/program_rom_%06x.ms5d`의8개1MiB창으로 보존한다. Stable ID는 `physical-program:%08x`이며 숫자는physical시작offset이다. Manifest는 원본 전체hash,CPU binding 없음,각physical범위·CRC·payload/container hash와 exact coverage를 기록한다. 코드·데이터·미사용·미확인 bytes를 모두 보존하며 의미 분석 완료로 취급하지 않는다.

`ProgramBusState.physical_rom`은 해당 창 목록을 빌려 읽는다. Bus가 선택한fixed/banked ROM의physical주소를 조회하며vector/PVC/기타장치 매핑을 덮어쓰지 않는다. Kind3은byte별 유일한coverage를 요구하므로WORD가 인접한비중첩청크를 연결할 수 있다. 이는홀수physical bank base의 청크 경계에도 필요하다. 같은unit에legacy kind1/2와kind3이 겹치면 모호한입력으로 거절하며,legacy WORD의완전한창 요구는 그대로다. 상세계약은 `analysis/physical-program-resource-contract.md`에 기록한다.


### MS5D 장면 경로와 primary tilemap

`extracted/runtime/scene_maps/`는기존MS5D v1 header를그대로사용한다. `path_%06x.ms5d`는kind1의고정ROM명령span이며원본WORD opcode와operand,마지막negativeWORD를원시순서대로보존한다. Opcode00/1c는4operandbytes,04/08/0c/10/14는12,18은6이다. Conditional pointer는operand안의원본주소로남기며decoder가분기실행을대신하지않는다. Stable ID는 `scene-path:%08x`(고정CPU주소)다.

`primary_root.ms5d`는kind2 CPU200004/ROM300004의4bytes, `primary_lookup.ms5d`는CPU200008/ROM300008의308bytes다. `tilemap_%06x.ms5d`는bank3의개별map을담으며ROMoffset=CPUaddress+100000이다. Map payload는BE16 width,BE16 height,그뒤width×height개의4bytecell이다. 각cell은두BE16 word를그대로보존하고column-major offset은 `4+4*(column*height+row)`다. 파일payload는정확히그길이이며padding이나PNG변환물을포함하지않는다. Map ID는bank간충돌을피하도록 `scene-tilemap:%08x`(물리ROMoffset)다.

Typed C++ loader는kind1 path와kind2 map을구분한다. Map 소비기는양수width/height,bank3주소관계,정확payload길이를검사하고source CPU/ROM을반환한다. Rawheader와캐시dimension을대조하여원본byte를조회기준으로삼는다. 전체77개후보map을보존하되현재descriptor참조없는8개를미사용으로확정하지않는다. 이자료계약은실제183c6 clipping/VRAM쓰기또는19e64 handler의실행완료를뜻하지않으며secondary bank2자료는별도후속범위다.

### MS5D secondary 맵 읽기 창

`extracted/runtime/scene_secondary/secondary_%06x.ms5d`는기존v1kind2이며bank2 CPU주소=물리ROM offset이다. Stable ID는 `scene-secondary:%08x`(물리ROM시작)이다. 원본183c6의알려진비영secondary참조에서root4bytes,각lookup4bytes,descriptor width의두배개수인상대offset WORD들,각offset이참조하는height개의LONG cell 창을수집한다. Offset은각WORD자신의CPU주소를기준으로sign16하여더한다. Table시작기준으로변환하지않는다.

수집한창의겹침·인접구간만합쳐서각container로포장하며미관찰hole은채워넣지않는다. Manifest의coverage_origins는각descriptor/selector/column과원래읽기창을기록한다. 셀재배열·중복제거·PNG변환없이원본bytes와주소관계를보존한다. 이추출범위는source column/row0부터descriptor full width/height의읽기후보union이며전체논리자료의길이나모든동적접근의완전성·collision의미를주장하지않는다. Bank3 primary자료와CPU주소가겹쳐도물리ROM주소로구분한다.


### MS5D 장면 배치 스트림

`extracted/runtime/scene_placements/placement_%06x.ms5d`는기존v1kind1을사용하며고정CPU주소=ROMoffset이다. Stable ID는 `scene-placement:%08x`(rootCPU)다. Stream의BE16첫WORD가정확ffff이면2byte terminal이다. 그외record는16byteheader와BE16+2의inlinebytecount만큼의원시payload로구성된다. Header는+0gate,+2inlinecount,+4/+6좌표WORD,+8optionalbounds pointerLONG,+ccallback pointerLONG이다. 필드를재배열하거나pointer를호스트주소로바꾸지않는다.

Typed C++ decoder는aligned first1MiB window와정확한terminal/end를검사한다. Gate8000..fffe는일반record로보존한다. Inlinecount는even/<8000이어야하며odd복사loop와signedskip해석은지원밖오류다. 좌표word/포인터는원시값이며callback과bounds를자동실행·역참조하지않는다. Decoder결과는sourcebytes의소유복사와각record source/next CPU·ROM주소,inlinebytes,terminal주소를포함하며실패시기존결과를보존한다.

Canonical18streams의payload합계422bytes,일반record24개/terminal18개다. Optionalbounds는모두0이므로이번package에는bounds의추측자료를만들지않는다. 이구문형식과로드검증은1a414/1a470 실행,object할당,callback구현또는자연도달검증을대체하지않는다.

### MS5D 이벤트 초기화 자료

`extracted/runtime/stage_events`는기존v1kind1의fixed CPU=ROM 창을사용한다. `event_%06x.ms5d`의stable ID는 `stage-event-stream:%08x`이며47개window는header부터e905c gate-skip이읽는ff BYTE까지모든bytes를보존한다. 모든canonicalpayload는홀수길이다. MS5D는WORD개수가아닌byte길이를기록하므로padding을삽입하지않는다. 중간opcode/payload는해석여부와무관하게원본순서그대로남는다.

`pointer_%06x.ms5d`는47개의4byte간접포인터cell,ID는 `stage-event-indirect:%08x`다. `lookup_0030ec.ms5d`는8byte조회표,ID는 `stage-event-lookup:000030ec`다. 총95resources/48,881payloadbytes이며현재창끼리겹침은없다. Manifest는원본SHA256,CPU/ROM범위,CRC,container/payload SHA256,role,59catalog record와target 참조,header/gate주소,ff read boundary를기록한다.

Packer는기존stage catalog를검증하고inventory를메모리에서재생성한다. Canonicalstream의비음수header jump/양수gate jump를확인한뒤rawwindow를보존하며오래된cached inventory를추출근거로쓰지않는다. Runtime C++은부호있는jump와LIVE RAM도지원하므로packer의canonical목록조건을실행알고리즘제한으로혼동하지않는다. ff는이번read-window 경계이며전체event문법·미사용자료범위·callback실행완료를증명하지않는다.
