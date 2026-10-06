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
