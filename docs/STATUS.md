# 진행 상태

## 2026-10-06 — ROM 기반 검증 완료
- 작업 브랜치: analysis/rom-foundation.
- mslug5.zip의 게임 ROM 13개가 고정 MAME 정의와 크기·CRC32·SHA1 모두 일치한다.
- 누락·추가·중복 파일 없음. ROM 원본은 변경하지 않았다.
- 검사 도구: tools/inspect_rom.py. 결과: artifacts/rom_inventory.json.
- config/mslug5_mame.json에 기준 해시를, config/mame_sources.json에 참고 소스 리비전·SHA256을 기록했다.
- tools/fetch_reference.py로 고정된 참고 소스를 확보할 수 있다.
- 합성 데이터 테스트 9개와 실제 ROM 검증 통과. 메인 에이전트 코드 리뷰 완료.
- docs/analysis/rom-layout.md에 데이터 영역과 복호화 순서·한계를 정리했다.
- 로컬 Git 구성 완료. 원격은 없어 실제 PR은 생성하지 않았다.

## 2026-10-06 — 영역 조립 및 68000 복호화
- 네 암호화 영역 P/C/M/V를 검증된 ROM으로 조립하고 파일 대응·해시를 저장했다.
- MAME ROM 로더와 endianness 헤더로 P 영역 바이트 순서를 확인했다.
- PVC 복호화 Python 구현을 메인 에이전트가 리뷰했다.
- 실제 ROM 및 합성 입력 각각 8MiB 전체가 원본 MAME C++ 함수 출력과 일치했다. BE/LE 대응도 일치한다.
- canonical BE 프로그램 이미지: extracted/program/maincpu.decrypted.be.bin.
- 합성 단위 테스트 총 20개 통과.
- 근거·재생성 명령·검증 범위: docs/analysis/pvc-program.md.

## 2026-10-06 — 그래픽·사운드 복호화
- CMC50 C/M1, PCM2 V 및 고정 문자 타일 추출 구현 완료.
- 실제 출력 5개가 원본 MAME C++ 함수 결과와 전체 바이트 일치한다.
- M1 512KiB, Z80 실행 영역 576KiB, ADPCM 16MiB, C 64MiB, 고정 타일 128KiB.
- 산출물·해시: extracted/media/manifest.json. 구현은 tools/extract_media.py로 재실행한다.
- 단위 테스트 총 31개 통과. 메인 에이전트가 구현 및 원본 대응을 리뷰했다.
- docs/analysis/media-decryption.md에 검증 범위·명령·출력 해시를 기록했다.

## 2026-10-06 — 런타임 타일 리소스
- 사용자 지침 반영: PNG·재생용 오디오는 확인용이며 최종 사용 데이터는 C++ 런타임 형식이다.
- 서브에이전트 사용자 상한 5개를 기록했다. 현재 도구 상한 때문에 동시에 최대 3개를 사용한다.
- C 타일 524288개와 S 타일 4096개를 indexed8 중간 데이터로 디코딩했다.
- C 픽셀 134217728바이트가 pinned MAME optimize_helper C++ 결과와 전체 일치, S 262144픽셀도 렌더러 nibble 매핑과 전체 일치했다.
- MS5T v1 바이너리 런타임 규격과 C++11 로더를 구현했다. 규격: docs/resource-format.md.
- extracted/runtime/sprites.ms5t 및 fixed.ms5t를 실제 C++ check_tiles로 읽었다.
- Python 테스트 총 41개와 C++ 로더 테스트 통과. 메인 에이전트 코드 리뷰 완료.
- 원본 팔레트는 미해석이다. 타일 인덱스는 보존되며 임의 색상을 런타임에 넣지 않았다.

## 2026-10-06 — 첫 68000 코드 분석
- Capstone 5.0.6을 로컬 .venv에 고정하고 명시적 범위 역어셈블 도구를 만들었다.
- 잘린 명령에서 가짜 피연산자를 만드는 디코더 경계 문제를 발견·회귀 테스트로 차단했다.
- 벡터 상태·고정 ROM·PVC overlay·뱅크 기준값을 구분하는 주소 resolver를 구현했다.
- 초기 오브젝트 테이블 8개, stride 0xc4의 80개 추가 슬롯, 순환 디스패치 루프 0x2aac를 정적으로 해석했다.
- 콜백이 자체 함수 포인터를 바꾸는 두 전이를 확인했다. 실제 게임 실행 비교는 아직이다.
- RAM으로 복사하면서 ROR16 3비트 변환하는 코드 경로(0x1026..0x1095)를 발견했다.
- 근거: docs/analysis/object-dispatch.md, address-map.md. 재생성: tools/analyze_object_boot.py.
- Python 테스트 55개 통과. 전체 빌드 테스트는 make test로 실행한다.

## 2026-10-06 — 첫 C++ 게임 로직의 원본 실행 비교
- 원본 0x271c와 호출 helper를 분석하여 ms5::reset_object_fields로 메모리 효과를 구현했다.
- Unicorn 2.1.4에서 M68000 모델을 명시하고 실제 ROM 루틴을 실행했다.
- 261가지 입력 × 196바이트 전체가 C++ 결과와 일치했다. 경계 guard, 원본 반환 PC/A0도 확인했다.
- 변환 ROM [0x1342,0x2518)의 4566바이트를 ROR16 3비트로 복원했고 원본 0x1046 루프 실행 결과와 전체 일치했다.
- 변환된 RAM 코드 자체의 동작은 아직 미분석/미실행이다.
- 재현: tools/verify_object_reset.py, tools/extract_ram_code.py. 근거: object-reset.md, ram-code.md.
- 전체 BIOS/장치 부팅 비교를 위해 보유 neogeo.zip 경로를 사용자에게 질문했다. 답변 없이도 독립 분석을 계속할 수 있다.

## 2026-10-06 — 오브젝트 목록 초기화 재구성
- 원본 0x2790의 8개 순환 목록, 80개 free 슬롯, sentinel 및 제어 변수 초기화를 C++11로 구현했다.
- MS5I v1 리소스와 C++ 로더를 연결했다. 원본 테이블은 런타임 바이너리에 보존한다.
- 21가지 초기 RAM × 65536바이트 전체가 원본 M68000 루틴 실행과 일치했다.
- Python 55개 및 C++ 테스트 3종 통과. 메인 리뷰·통합 완료.
- CPU 레지스터/플래그, 콜백 실행, 전체 부팅은 이 검증에 포함하지 않는다.

## 2026-10-06 — 팔레트 전송과 원본 데이터 참조
- 0x7320..0x871a의 256개 dirty 블록 전송을 C++11로 구현했다.
- 259가지 입력의 staging+destination 각 16KiB 전체가 원본 M68000 실행과 일치했다.
- 팔레트 source 0x22bd12와 lookup 0x25cb52 참조 경로를 확인했다. bank base=0x200000 조건이다.
- 원본 0x4718 helper의 signed16 조회 변환을 16개 probe에서 확인했다.
- 전체 팔레트 범위·게임 사용 ID·혼합 경로·RGB 변환·wrapper는 미완료. 분석: docs/analysis/palette-flow.md.

## 2026-10-06 — 팔레트 슬롯 관리 추적
- 0x3ef2 초기화를 C++로 구현하고 20개 패턴 × 64KiB RAM 전체 원본 일치를 확인했다.
- 256개 destination 슬롯과 source palette ID가 별개임을 확인했다.
- 원본0x8ebe에서 ID 공유·새 할당 플래그·동일 bucket의 ID 구분을 실행 관찰했다.
- 원본0x8ff4의 보유 슬롯 참조 해제를 실행 관찰했다. 할당/해제 C++ 구현은 아직이다.
- 상세 주소·필드·검증 범위: docs/analysis/palette-flow.md.

## 2026-10-06 — 첫 원본 ID 팔레트 런타임 리소스
- 고정 등록 테이블 두 개에서 source ID 0x897,0xb01,0xb02를 확인했다.
- 원본word·일반 조회 변환word를 함께 저장하는 MS5P v1과 C++ 로더를 구현했다.
- 원본 초기화→등록→준비→전송 실행 결과96바이트가 패키징한 색상값과 일치했다.
- 전체 카탈로그가 아닌 incomplete_sparse 상태를 manifest와 규격에 명시했다.
- 실제 RGB 렌더링과 원본 장면 대응은 아직 남아 있다.

## 2026-10-06 — 원본 문자에서 타일 배치로 연결
- 경고문 원본 [0xcb80,0xccd5), palette source0x897→slot0, font61 참조를 추적했다.
- ASCII/font61 제어 해석을 C++로 복원했다. 미지원 글꼴은 오류로 구분한다.
- 실제 원본 경고문560개 포트 쓰기 순서 전체와 추가127개 ASCII 스트림이 C++ 결과와 일치했다.
- 실제 화면·fixed source 선택·RGB 변환·공통 스트림 리소스 연결은 남아 있다.
- 분석과 재현: docs/analysis/fixed-text.md, tools/verify_fixed_text.py.

## 2026-10-06 — 추출 타일·팔레트를 소비하는 고정 레이어
- C++ fixed renderer를 구현하여 MS5T와 MS5P를 실제로 사용했다.
- 원본CPU와 일치한 문자 write trace에서 320×256 frame을 생성했다.
- raw fixed ROM을 독립 해석한81920픽셀 전체가 C++ 하드웨어word frame과 일치했다.
- pinned MAME 저항망 원본 함수로32×4 색상 조회표를 생성했다.
- 확인용 PNG를 열어 경고문 배치를 점검했다. PNG는 런타임 입력이 아니다.
- 실제 부팅 화면·fixed source 선택·sprite 합성·C++ RGB 계층은 아직 남아 있다.

## 2026-10-06 — C++ 하드웨어 RGB 변환
- MAME 저항망에서 생성한32×4 lookup을 C++11 하드웨어 계층에 연결했다.
- 모든65536 색상word × normal/shadow 두 모드393216 RGB바이트가 원본 MAME 함수 출력과 일치했다.
- 두 reference bank에서도 동등성을 확인했다. 확인용 PNG도 이제 C++ 변환을 사용한다.
- 화면 상태 제어·CRT·전체 화면 타이밍 검증은 아직 별도다.

## 2026-10-06 — 리소스만 사용하는 C++ 단일 장면 통합
- MS5X로 원본 문자 스트림과 palette source ID→slot 연결을 패키징했다.
- render_text_scene은 MS5X/MS5T/MS5P만 읽어 해석→tilemap→하드웨어word→RGB를 실행한다.
- 분석 trace나 완성 PNG를 실행 입력으로 사용하지 않는다.
- 원본CPU를 새로 실행한 참조와245760 RGB바이트 전체가 일치했다.
- 단일 경고문 통합이며 조작·프레임 갱신·전체 부팅은 아직 아니다. engine/README.md에 실행 방법을 추가했다.

## 2026-10-06 — 부모 좌표와 이동 증분 갱신
- 오브젝트+0x2e 좌표 구조와 원본43e38/43ea8 갱신을 C++로 복원했다.
- 부모 합산, 소수부 carry, 32bit wrap, 이전 좌표 보존 조건을 확인했다.
- 288개 초기 상태 ×64KiB RAM 전체가 원본CPU 실행과 일치했다.
- global 갱신 표시는1/2 toggle이다. 실제 프레임 호출 순서·축 단위·sprite 연결은 아직이다.
- 분석: docs/analysis/position-state.md. 검증: tools/verify_position_state.py.

## 2026-10-06 — 스프라이트 합성 데이터 참조 발견
- 원본0xcd58의12바이트 표시 큐 레코드와 일반/별도정렬 경로를 해석했다.
- 경계값48개에서 원본CPU의64KiB 메모리 효과를 확인했다. C++ 구현은 아직이다.
- consumer0xce82의packed ID bank/group/item 참조를 확인했다.
- 실제 호출부ID0x2152/0x2952를 ROM0x4cce60/0x4cd3e8의합성데이터에 연결했다.
- 다음은consumer 진입규약과비디오쓰기를실행검증하고타일배치형식을확정하는작업이다.

## 2026-10-06 — 원본 합성 데이터에서 스프라이트 명령 생성
- 단일 직사각형 블록의 열·타일 수와 attribute/tile 쌍 순서를 확인했다.
- ID0x2152의22×16,ID0x2952의39×27 데이터로일반명령생성을C++에구현했다.
- 좌표·style·슬롯경계80조합에서원본CPU의모든비디오쓰기와다음slot이일치했다.
- dy/세로위치제어·flip다른경로·rasterizer·공통합성리소스로더는아직남아있다.
- 분석: docs/analysis/sprite-composition.md. 검증: tools/verify_sprite_composition.py.

## 2026-10-06 — 스프라이트 세로 제어와 슬롯 재사용
- 큐 소비 호출부와 원본0xf246의 일반 refresh 경로를 확인했다.
- Y 제어를 먼저 쓰고 이미 준비된 슬롯의 X/zoom/tile 쓰기를 생략하는 경로를 C++에 추가했다.
- 세로값·좌표·캐시·슬롯경계216조합의 모든 쓰기가 원본과 일치했다. 이전 일반경로80조합도 통과했다.
- 전체 스케줄링·다중블록·flip·화면 rasterizer는 아직 남아 있다.

## 2026-10-06 — C++ 스프라이트 리소스 통합
- MS5C 리소스2개와 C++ 로더를 추가하고 원본 refresh 경로216조건에서 모든 명령·다음 슬롯 일치를 확인했다.
- 실제 호출부 팔레트 연결을 확인하여 MS5P 카탈로그를17개 ID로 확장했다. 등록 테이블은 장면별로 독립 검증한다.
- C++ 런타임 입력은 바이너리 리소스이며 PNG/분석 trace를 입력으로 사용하지 않는다.
- 전체 테스트와 기존 문자 장면 회귀 검증을 통과했다. 전체 sprite rasterizer·게임 루프·사운드 복원은 남아 있다.

## 2026-10-06 — 하드웨어 줄별 스프라이트 선택
- C++ parse_sprite_scanline에 줄당96개 제한, 번호순 선택, 연결된 Y/높이 상속, 홀짝 목록 갱신을 구현했다.
- 고정 MAME 함수 본문을 참조로 실행해3072조건×0x11000바이트 VRAM 전체가 일치했다. 실제 MS5C2개 명령 출력도 포함했다.
- 세로 zoom은 외부000-lo.lo 테이블을 조회함을 확인했다. 현재 카트리지 파일만으로 그 테이블을 검증할 수 없어 픽셀 rasterizer는 아직 연결하지 않았다.
- 원본 함수 비교·계층 구분·남은 의존성은 docs/analysis/sprite-scanline.md에 기록했다.

## 2026-10-06 — 지연 표시 큐 정렬 복원
- 원본0xce02의 unsigned16 키 비교, 목록 내부 교환, 이전 태그 덮어쓰기, 링 wrap을 해석하고 C++로 구현했다.
- 원본 생성기로0..255개 지연 레코드를 준비한80조건에서 C++와 원본의64KiB RAM 전체가 일치했다.
- 큐가 찼을 때 생성기의 소비자 대기 분기도 확인했다. 동시 소비·실제 프레임 스케줄은 아직 분석 중이다.
- 분석: docs/analysis/sprite-sort.md. 원본 비교: tools/analyze_sprite_sort.py --cpp.

## 2026-10-06 — 역방향 슬롯 할당과 재사용
- 소비자0x16bba/0x16cfa의 방향 선택을 추적하고0x117b2/0x13b66을 C++로 복원했다.
- 타일 열 순서는 유지하면서 보이는 열에 대해서만 slot을 먼저 감소시킨다. refresh는 Y를 쓰고 캐시 시작 이상인 slot의 나머지 쓰기를 생략한다.
- 역방향400조건과 기존 정방향296조건에서 원본 비디오 쓰기·다음 slot이 일치했다. MS5C 직접 로드 경로도 연결했다.
- ready bit·두 슬롯 영역·프레임 준비/소비의 관계를 분석 문서에 기록했다. 전체 스케줄러의 실행 통합은 아직이다.

## 2026-10-06 — 큐 단위 스프라이트 갱신 통합
- 원본0x16cfa의 ready 처리, 방향 전환, 두 슬롯 영역, 큐 순회, 개별 refresh, 남은 Y 지우기와 read-index 갱신을 C++로 연결했다.
- C++는 MS5C 로더의 리소스를 사용한다. 원본96조건에서64KiB RAM과 순서 있는 비디오 쓰기 전체가 일치했다.
- 20개 레코드로 슬롯 소진을 검사했고 잘못된 두 번째 레코드가 호출자 상태를 부분 변경하지 않는지도 테스트했다.
- 리뷰에서 X하위6bit의 묵시적 절삭 가능성을 찾아 원본 생성기 정렬 조건을 명시적으로 검증하게 수정했다.
- 일반 단일 직사각형 분기만 통합했다. 준비/사전정렬·다른 분기·실제 타이밍은 미완료다.

## 2026-10-06 — 표시 준비 전 안정 정렬
- 원본0x166bc를 unsigned16 두 바이트 안정 정렬로 해석하고 C++로 구현했다.
- histogram·누적합·임시 배열·ring 수정까지 원본72조건의64KiB RAM 전체와 일치했다. 중복 레코드, 같은 키, wrap,255개 경계를 포함한다.
- 독립 정렬/빈도 oracle로 C++ scratch 결과와 입력 오류 시 상태 보존을 검사했다.
- 지연 정렬이 키를 태그로 바꾸고 사전 정렬이 전체 미준비 큐를 다시 정렬하는 연결을 확인했다. 전체 준비 dispatcher 통합이 다음이다.

## 2026-10-06 — 준비·갱신 연속 경로 통합
- 원본0x16bba의 지연 병합→안정 정렬→방향별 일반 명령 준비→ready 게시를 C++로 연결했다.
- 일반+지연 혼합, 두 영역, 양방향, wrap, 슬롯 제한의96조건에서 원본RAM·비디오 명령이 일치했다.
- 이어서0x16cfa/refresh_sprite_queue를 실행한96개 상태 전달도 원본과 일치했다. 실제 런타임 입력은 MS5C 리소스다.
- 현재 동기 API는 소비 중인 큐를 명시적 오류로 반환하고 상태를 보존한다. 원본 대기/IRQ/실시간 스케줄링과 다른 분기는 미완료다.
- 분석·실행 명령: docs/analysis/sprite-prepare-queue.md 및 engine/README.md.

## 2026-10-06 — 생성기와 연속 표시 경로
- 원본0xccd6 초기화와 기본 RTS 콜백의0xcd58 생성기를 C++로 구현했다.
- 초기 RAM8개와 생성기192조건에서64KiB RAM 전체가 일치했다. 화면 경계·일반/지연·wrap·Full/Waiting 진입을 포함한다.
- 초기 방향/링 위치4조합에서4회씩 상태를 유지하며 생성→준비→갱신을 실행했다.124개 제출과32개 준비/갱신 단계가 원본RAM·비디오 명령과 일치했다.
- Waiting은 원본 대기 진입만 나타낸다. 재개 타깃 캡처·IRQ·실시간 scheduling, 사용자 콜백, 다른 표시 분기는 미완료다.

## 2026-10-07 — 원본 슬롯 설정과 비활성 영역 지원
- 원본0xcd1c 설정 함수를 C++로 복원했고192조건의64KiB RAM 전체가 일치했다.
- 초기화의 all-ffff pool이 비활성 상태임을 원본 준비/갱신으로 확인했다. 이를 거부하던 두 dispatcher를 수정했다.
- 비활성 영역 포함 준비96+갱신96조건과 연속124제출/32단계가 원본과 일치했다. 활성 두 영역 연속 처리도 회귀 통과했다.
- 연속 검증의 pool 수동 word 설정을 원본/C++ setter 호출로 대체했다. 실제 화면 모드의 모든 설정값·호출 주기까지 검증한 것은 아니다.

## 2026-10-07 — 직사각형 좌우·상하 반전 통합
- 원본16개 분기에서 H/V 좌표 계산과 목적지 타일 순서를 해석하고 C++ variant API로 구현했다.
- MS5C 로더·준비·갱신 dispatcher에 연결했으며 기존 고정 분기 API 동작은 유지했다.
- 두 원본 리소스의1440조건에서 순서 있는 비디오 쓰기와 다음 슬롯이 일치했다.
- 반전을 섞은 연속 생성→준비→갱신은 활성/비활성 영역 각각124제출·32단계의 전체RAM·출력이 일치했다.
- 일반 표시80, 갱신216, 역방향400조건 회귀 검증과 make all test 통과. 전체 게임 복원은 계속 진행 중이다.
- 원본 주소·수식·검증 범위: docs/analysis/sprite-flips.md.

## 2026-10-07 — 다중 직사각형 리소스와 런타임 연결
- 원본 payload의 블록 수와 반복을 해석하고 MS5C kind2 및 C++ 로더/표시 경로를 추가했다. kind1 호환성을 유지한다.
- 실제 네 리소스를 추출했고2880조건의 원본 비디오 쓰기·다음 슬롯이 일치했다.
- 반전 포함 생성→준비→갱신은 활성/비활성 각각124제출·32단계의 전체RAM·출력이 일치했다. kind1 pipeline 회귀와 make all test도 통과했다.
- 이번 네 리소스의 게임 내 호출·팔레트·사용 여부는 미확인으로 기록했다. low header flags의 의미도 미해결이다.
- 분석 근거와 재현: docs/analysis/sprite-blocks.md, docs/resource-format.md.

## 2026-10-07 — 헤더 비영 하위 byte 지원
- 원본 소비기의 header 처리와 dispatcher 분기 선택을 추적했다. 하위 byte는 표시 출력에 영향이 없으며 다른 코드에서의 의미는 미확인이다.
- 단일/3블록 payload의0..255 byte sweep8192조건에서 원본 비디오 쓰기·다음 슬롯이 일치했다.
- kind2의 불필요한 zero 제한을 제거하고 실제0101/0103 두 리소스를 추가했다. kind1 규격은 유지했다.
- 실제 여섯 리소스4320조건과 활성/비활성 pipeline 각각124제출·32단계가 원본과 일치했다. make all test 통과.
- 분석 및 재현: docs/analysis/sprite-header.md. 전체 게임 복원은 계속 진행 중이다.

## 2026-10-07 — 애니메이션 표시 명령 연결 분석
- 이전 turn의 헤더 확장은 원본 대조·구현·커밋을 완료한 progress다.
- 원본 애니메이션 명령 해석기49fc6과 opcode04 표시 handler4a10c→생성기cd58 경로를 확인했다.
- 좌표 확장·반전 순서·부모 carry·팔레트 우선순위·리소스 ID 합성의3072조건에서 생성기 직전 인자와 A1 전진이 원본과 일치했다.
- 재현 도구 tools/analyze_animation_draw.py 및 근거 docs/analysis/animation-draw.md를 추가했다. 아직 C++ 변환기·애니메이션 시간 흐름은 미구현이다.

## 2026-10-07 — 애니메이션 표시 변환 C++ 통합
- 이전 turn은 원본 명령 연결과3072조건 실행 근거를 추가한 progress다.
- C++ decode_animation_draw와 검증 CLI를 추가했다. 원본3072개 인자 조합 및32개 생략 조건과 일치했다.
- 원본4a10c를 생성기·bank복원까지 실행한 경로와 C++ decode→submit→prepare→refresh를 연결했다. 활성/비활성 각각124제출·32단계 전체RAM·출력이 일치했다.
- make all test 통과. 인자 검증·실패 시 출력 보존·최대object offset도 검사했다.
- 프레임 대기·분기 명령 해석기와 실제 스크립트 추출은 다음 단계다.

## 2026-10-07 — 애니메이션 대기·경계 명령 분석
- 이전 turn의 C++ 표시 변환·연속 검증은 progress다.
- 원본49fc6의진입 상태와 opcode00/28의타이머·포인터·반환carry를 해석했다.
- 상위byte duration 덧셈과16bit 감소, 음수 상태의같은 호출 내 재해석을2000조건의전체RAM·carry로 검증했다.
- 재현 도구 tools/analyze_animation_wait.py와 docs/analysis/animation-wait.md를 추가했다. 실제 시간단위·자연 스크립트·C++ 실행기는 아직 미완료다.

## 2026-10-07 — 애니메이션 상태 실행기 통합
- 이전 turn은 대기/경계 명령의2000조건 근거를 추가한 progress다.
- C++ step_animation이00/04/28을 해석하고 표시 변환→큐 생성기로 연결한다. RAM·carry 오류 원자성, 범위 검사, 실행한도를 추가했다.
- 대기/경계2000조건의원본·C++ 전체RAM·carry가 일치했다. 두 표시·대기 혼합script8시퀀스의96호출·192비디오 단계도 일치했다.
- make all test와추가 Waiting/명령한도 실패 테스트를 통과했다. 실제MS5C 리소스를 사용하지만 명령script는검증fixture다.
- 자연ROM 스크립트 추출과다른opcode 복원이 다음 단계다.

## 2026-10-07 — 원본 애니메이션 리소스 연결
- 이전 turn은 C++ 상태 실행기와혼합fixture 검증을완료한progress다.
- 원본호출1e6b0의6f1e2 루프,그룹ca,감소량100과자기점프경계를확인했다.
- MS5A 로더·포장도구·실행CLI와opcode08을추가하고56byte스크립트 및MS5C 의존4개를추출했다.
- 원본ROM 직접실행과C++ MS5A로드 경로가96호출·192비디오단계의RAM·carry·출력에서일치했다. make all test 통과.
- 자연게임도달성·팔레트연결·외부스크립트분기·나머지opcode는미완료다. 근거:docs/analysis/animation-rom-loop.md.

## 2026-10-07 — 애니메이션 조건 분기 분석
- 이전 turn은 실제ROM 루프추출과C++ 실행검증을완료한progress다.
- opcode0c의조건byte·선택자word·대상주소형식과원본필드테이블4a76c를확인했다.
- 확인한32선택자prefix에서1536조건의분기포인터·전체RAM·반환carry가일치했다. 조건은byte동등성이아닌zero/nonzero 동등성이다.
- C++ 통합과테이블전체경계·실제참조는미완료다. 근거 docs/analysis/animation-field-branch.md 및 tools/analyze_animation_branch.py.

## 2026-10-07 — 실제 조건 분기 참조와 필드 범위 확장
- 이전 turn의조건분기1536조건분석은progress다.
- 실제초기화2bb10→스크립트65f56→selector31을연결했다. 조건분기참조후보32개를재생성가능한도구로목록화했다.
- 테이블뒤4a88e가별도호출되는코드임을확인해145word 후보범위를확보하고6960조건의원본RAM·carry일치를검증했다.
- 실제분기후속14는함수테이블호출명령이다. 이를무시하지않고다음복원대상으로기록했다. selector47 후보의후속18도미지원이다.
- 필드런타임리소스·C++0c 및후속명령통합은아직남아있다.

## 2026-10-07 — 조건 분기 후속 함수1e 분석
- 이전 turn의실제분기참조·145필드 검증확장은progress다.
- 함수테이블4a500의선택1e→2b3fa를해석했다. 오브젝트+7d로operand table의long을골라+78에복사한다.
- 원본14 handler를포함해1536조건의전체RAM·반환carry를검증했다. 실제스크립트65f5e의테이블주소6431a와연결했다.
- 데이터의후속용도·논리테이블경계·자연사용인덱스·C++14통합은남아있다. docs/analysis/animation-callback-1e.md에범위를기록했다.

## 2026-10-07 — 조건 분기·조회 명령의 C++ 리소스 통합
- 이전 turn은callback1e의1536조건실행근거를추가한progress다.
- MS5D 로더/포장도구와step_animation_with_data를추가해0c 조건분기·14/1e 조회복사를지원한다. 원본테이블byte는런타임리소스로읽는다.
- 원본/C++ 조건분기6960조건 및callback1536조건의전체RAM·carry가일치했다.
- make all test와추가범위·중첩·누락·rollback검사가통과했다. 데이터창의논리테이블범위/자연사용여부는manifest에서구분한다.
- 실제분기스크립트의후속10/18등명령통합과전체카탈로그확장은남아있다.

## 2026-10-07 — 상태 선택 표시 명령 C++ 통합
- opcode10은 필드 테이블로 선택한 상태 바이트에 따라 draw04 항목 하나를 실행한다. 범위를 벗어나면 표시를 생략한다.
- 실제65f64의selector30/길이40과 원본4a22c를 연결했다. 테이블은 MS5D로 공급한다.
- 256인덱스×3타이머=768조건의 선택주소·전체RAM·carry가 원본과 C++에서 일치했다.
- make all test, 추가 오류/rollback 검사, 기존ROM루프96호출·192비디오단계 회귀가 통과했다.
- 전체 실제분기스크립트·자연도달성과 나머지 명령은 미완료다. docs/analysis/animation-indexed-draw.md 참고.

## 2026-10-07 — 원본 양방향 루프의 네이티브 리소스 실행
- 이전 turn은 opcode10 원본비교·C++ 통합을 끝낸 progress다.
- 실제65f56..662c2의 두 4프레임 루프를 MS5A로 추출했다. 1d callback은+7c를 조회하며 1e는+7d다.
- MS5A CLI에 MS5D 입력을 연결하고 352바이트 callback 창을 별도 리소스로 제공했다.
- 강제 양방향 상태전환 포함68시퀀스1632호출에서 원본/C++ 전체RAM·carry 일치. make all test 통과.
- 이 경로의 composition group·팔레트·자연생성 경로 연결은 남았다. docs/analysis/animation-branch-resource.md 참고.

## 2026-10-07 — 분기 오브젝트의 composition 연결
- 이전 turn은 실제양방향루프의1632회 리소스실행을 검증한 progress다.
- 두 initializer에서 groupF2 설정을 확인하고57개 MS5C 의존리소스를 추출했다.
- 원본 initializer prefix 두 종류를 실행해 palette source ID 3종씩과 slot 할당을 기록했다. C++ allocator 전체복원은 아직 아니다.
- 원본/C++ animation1632회 및 prepare/refresh3264단계 RAM·비디오 쓰기 비교를 확장했다. 자연생성·palette lifecycle·픽셀화면은 미완료다.
- 상세근거 docs/analysis/branch-object-resources.md.

## 2026-10-07 — 동적 팔레트 할당·해제 C++ 복원
- 이전 turn은57개 composition 연결과3264비디오단계 원본비교를 완료한 progress다.
- 원본8ebe/8ff4/8e4a의 bucket·free목록과 참조 관리를 해석하고 C++로 구현했다.
- 공유/강제할당·참조특수값·256슬롯소진·역순해제·FIFO재사용 포함409연산의 전체RAM이 원본과 일치했다.
- make all test 및 실패rollback 검사 통과. MS5P 동적업로드·효과·전체오브젝트 생명주기 연결은 남았다.
- 근거 docs/analysis/palette-allocator.md.

## 2026-10-07 — MS5P 동적 팔레트 준비 연결
- 이전 turn은 allocator409연산의 원본비교를 완료한 progress다.
- 실제initializer 요청5ID를 추가해 MS5P22종을 제공한다. 기존17개 고정레코드는 보존했다.
- 준비7196의 일반조회/효과우회 경로를 C++로 복원하고 기존업로드와 연결했다.
- 256슬롯×dirty/clean512조건에서 전체준비RAM과업로드bytes가 원본과 일치했다. 전체검사·고정팔레트 회귀 통과.
- 혼합과활성효과 경로는 명시적미지원이며 전체게임호출 연결은 남았다. docs/analysis/palette-prepare.md 참고.

## 2026-10-07 — 원본 팔레트 혼합 복원
- 이전 turn은 MS5P22종과 준비/업로드512조건 검증을 완료한 progress다.
- 원본4c40 혼합표1890값과 signed주소 색변환32768값을 확인했다. 원본helper2112조건의 전체RAM이 모델과 일치했다.
- 일반 혼합을 C++ MS5P 준비에 연결해 실제팔레트20쌍660조건이 원본7196과 일치했다.
- 전체검사 통과. 활성효과·효과혼합504c 및 전체게임계수갱신은 남았다. docs/analysis/palette-blend.md 참고.

## 2026-10-07 — 활성 색 효과와 혼합 효과 복원
- 이전 turn은 일반혼합 계산과660조건 실제리소스 검증을 완료한 progress다.
- 479e/504c의 8비트덧셈·부호검사·상한처리를 해석하고 원본helper9248조건을 검증했다.
- C++ MS5P 준비에 효과를 연결해 실제리소스825조건의 전체RAM이 원본과 일치했다.
- 전체검사와 일반혼합660조건 회귀 통과. 실제게임의 효과word·혼합계수 갱신 흐름과 전체프레임 연결은 남았다.
- docs/analysis/palette-effect.md 참고.

## 2026-10-07 — 효과 진행과 준비 게이트 연결
- 이전 turn은479e/504c 효과계산과 실제MS5P825조건 검증을 완료한 progress다.
- 원본5728의 타이머·현재/목표/step word·dirty표시·준비게이트를 해석하고 step_palette_frame으로 연결했다.
- 경계140조건의 전체RAM이 원본과 일치했다. 전체검사 및 준비실패rollback 통과.
- 효과설정 호출자, 오브젝트 혼합계수 진행과 실제전체프레임 동기화는 남았다. docs/analysis/palette-frame.md 참고.

## 2026-10-07 — 효과·혼합 설정 진입점 복원
- 이전turn은 효과진행·준비게이트140조건을 완료한progress다.
- 8c16 효과목표/기간/증분 설정과8cda 슬롯별혼합설정을 C++로복원했다.
- 원본937조건의전체RAM이일치했고 전체기존검사가통과했다.
- 실제fa8설정→fae갱신직접호출의바이트를확인했다. 전체프레임동기화와상위게임호출은남았다.
- docs/analysis/palette-control.md 참고.

## 2026-10-07 — 일반 팔레트 전송과 연속 실행 연결
- 이전turn은 효과/혼합설정937조건 및 설정→갱신호출근거를 확보한progress다.
- 72fa 일반전송의pending해제·slot0특별처리·최종표시뱅크를 C++로연결했다.
- 54회전송과24회연속효과프레임에서 원본RAM·팔레트·뱅크가일치했다. 전체기존검사통과.
- 특수채우기873a,bank1내용과실제IRQ/장치타이밍은남았다. docs/analysis/palette-transfer.md 참고.

## 2026-10-07 — 특수 팔레트 채우기 분석
- 이전turn은 일반전송54회와연속효과24프레임을검증한progress다.
- 873a의bank1 전체채우기를32조건,8b64설정의전체RAM을9조건으로검증했다.
- 설정주소가일반ID×32와달리signed16 offset임을확인했다. 일반MS5P ID를그대로사용하면잘못된리소스가될수있다.
- C++두뱅크API와별도주소근거에맞는리소스연결은다음작업이다. docs/analysis/palette-fill.md 참고.

## 2026-10-07 — 두뱅크 팔레트 전송 통합
- 이전turn은 특수채우기/설정41조건과signed주소차이를확인한progress다.
- 두뱅크API가일반counter0과설정함수의특수counter2000을처리한다.
- 특수32조건과후속일반32조건의전체RAM·두bank·표시선택이원본과일치했다. 전체검사통과.
- 직접c554호출은ID0을전달한다. setup리소스연결,다른counter/장치타이밍은남아있다.

## 2026-10-07 — 채우기 설정과 게임용 바이너리 리소스 연결
- signed-word 주소의 2,048개 선택값을 별도 카탈로그의 MS5P v1으로 추출했다. 일반 팔레트 카탈로그와 ID 의미를 구별한다.
- C++11 setup_palette_fill이 이 리소스를 직접 읽는 CLI와 연결됐다. 패턴 첫 word를 보존하며 counter와 bank shadow를 원본대로 설정한다.
- 원본 대비 전체 RAM 2,051조건, 특수전송32조건 및 후속 일반전송32조건이 일치했다. make all test 통과.
- 자연 호출 도달성, 실제 장치 타이밍과 화면 검증은 남았다. docs/analysis/palette-fill.md 참고.

## 2026-10-07 — 임시 색 효과 저장과 복구
- 이전 turn은 채우기 설정 MS5P 연결과2,051조건 원본검증을 완료한 progress다.
- 8bc8/8be0의20바이트 상태 저장/복구 및 timer0 특수처리를 해석해 C++로 구현했다.
- f94 저장, fa8 임시효과 설정, fd6 복구의 실제 호출 근거를 확인했다. c560의 채우기 완료 대기도 정적 코드로 확인했다.
- 저장16/복구512/후속갱신8조건과 연속8단계 전체RAM 비교 및 make all test가 통과했다. 결과는 docs/analysis/palette-snapshot.md와 artifacts/palette_snapshot/verification.json에 기록한다.
- 자연 입력 도달성, 전체 루프 연결과 표시화면은 남았다.

## 2026-10-07 — 입력 요청 비트와 제어 진입 근거
- 이전 turn은 임시 색 효과 저장/복구를 C++로 연결하고 원본검증한 progress다.
- 원본9086의 모드별 요청비트 선택을 C++로 복원했다. 2,384조건에서 원본 D0/불변RAM/C++ 결과가 일치했다.
- 9136 비활성 상태 진입은 원본8,192조건에서 전체RAM/반환값이 모델과 일치했다. 이 상태기계의 C++ 구현과 활성상태 메뉴 의존성은 남았다.
- 실제 f54→9136 및 저장/복구 전환 분기를 확인했다. 물리입력과 자연게임 도달성은 아직 미확인이다.
- make all test 통과. docs/analysis/control-request.md 참고.

## 2026-10-07 — 제어 메뉴 리소스 추출과 C++ 해석
- 이전 turn은 입력 요청 C++ 및 비활성 진입 원본검증을 완료한 progress다.
- 93e0 메뉴의16byte헤더/10byte항목/종료표시를해석했다. 6항목과7문자열을기존MS5D로보존하고C++파서를연결했다.
- 원본6선택주소/24callback진입/7문자열소비범위와전체필드가일치했다. 경계및기존전체검사가통과했다.
- 메뉴초기화/프레임/항목callback의C++동작과화면검증은남았다. docs/analysis/control-menu.md 참고.

## 2026-10-07 — 원본 문자열 측정과 공통 해석기
- 이전 turn은6항목메뉴의MS5D추출/C++파서를원본으로검증한progress다.
- 38e8문자측정을C++로복원하고기존trace와제어명령해석을공유했다. MS5D메뉴문자열을직접사용한다.
- 원본388조건의count/style/line/종료주소가일치했다. 16비트countwrap과비ASCII byte도검증했다. 잘린입력/trap조건거부와출력보존검사통과.
- 메뉴초기화/표시와다른글꼴렌더링은남았다. docs/analysis/fixed-text.md 참고.

## 2026-10-07 — 메뉴 초기화와 네이티브 리소스 연결
- 이전 turn은 문자열측정388조건과표시회귀를완료한progress다.
- a29c reset/첫메뉴할당을C++로연결했다. MS5D descriptor와원본문자측정으로폭/높이및RAM상태를설정한다.
- 실제리소스및경계378조건의전체RAM이원본과일치했다. 8/16비트wrap,slot+5/current pointer보존,문자열간line전달을확인했다.
- 중첩a0a0 push와a370 프레임/표시는남았다. docs/analysis/control-menu.md 참고.

## 2026-10-07 — 메뉴 테두리와 중첩 가림 복원
- 이전 turn은메뉴초기화378조건을완료한progress다.
- 9b58테두리/9e94지우기/a018가림을C++로연결했다. MS5D descriptor flags와RAM슬롯에서매번출력명령을계산한다.
- 원본237조건의비디오포트전체쓰기순서/값이일치하고RAM은불변이었다. 가림시주소증가도생략하는동작을보존했다.
- 전체검사통과. 열기/닫기진행,a370전체프레임,문자와실제픽셀표시는남았다. docs/analysis/menu-border.md 참고.

## 2026-10-07 — 메뉴 열기·닫기 진행 연결
- 이전 turn은테두리/지우기/가림237조건을검증한progress다.
- a348/a2be의8.8높이갱신과표시순서를C++로연결했다. 닫힌행지우기는가림시에도주소를증가시키는차이를보존했다.
- 경계560단계와실제리소스초기화후연속16단계의전체RAM/포트쓰기가원본과일치했다. 전체검사및오류보존검사통과.
- a370전체상태전환,문자,선택callback과최종화면은남았다. docs/analysis/menu-motion.md 참고.

## 2026-10-07 — 메뉴 기본 문자 출력과 비디오 쓰기폭 복원
- 이전 turn은메뉴열기/닫기576단계를원본과검증한progress다.
- 기본3650문자callback을C++로연결했다. MS5D문자열과공통제어해석을사용하고각글자의long타일쓰기/word주소reset을모두보존한다.
- 실제메뉴문자열을포함한291스트림과65,280glyph/style조합에서원본포트주소/쓰기폭/값/순서가일치했다. 전체검사통과.
- 메뉴배치·선택callback·최종팔레트및픽셀화면은남았다. docs/analysis/fixed-text.md 참고.

## 2026-10-07 — 전체 메뉴 문자 배치와 실제 콜백 분석
- 이전 turn은기본문자C++출력291스트림을원본으로검증한progress다.
- 원본9e1a/9d3a의signed제목정렬,선택표시,항목스타일,가림및event5처리를해석했다.
- 실제6callback을건너뛰지않은288조건에서전체RAM/포트쓰기/callback대상·인자가독립모델과일치했다.
- 다음은이전체배치를C++에연결하는작업이다. 다른메뉴flags/callback및픽셀화면은미검증이다. docs/analysis/menu-text-layout.md 참고.

## 2026-10-07 — 메뉴 문자 배치 C++ 통합
- 이전 turn은전체메뉴원본문자배치288조건의분석모델을검증한progress다.
- glyph별가림을공통문자해석기에연결하고제목/선택화살표/항목스타일/event5 no-op경로를C++로통합했다. MS5D를직접읽는다.
- 원본288조건의전체RAM및포트쓰기폭/주소/값/순서가C++와일치했다. 미지원callback/flags에서상태보존을확인했다.
- a370전체상태전환/선택입력/다른callback/최종픽셀표시는남았다. docs/analysis/menu-text-layout.md 참고.

## 2026-10-07 — 메뉴 입력 판정의 전체 바이트 조합 검증
- 이전 turn은메뉴문자배치C++288조건을검증한progress다.
- a472의두플레이어입력마스크/우선순위/출처기록을C++로복원했다.
- 327,680조건에서원본분기결과와출처byte가일치했고다른RAM보존을확인했다. 전체검사통과.
- 이전/다음항목검색a216과event callback실행을전체프레임에연결하는작업은남았다. docs/analysis/menu-input.md 참고.

## 2026-10-07 — 메뉴 이동 및 지정 선택 연결
- 직전 응답은 설정/진행 상태 재확인으로 새 구현이 없었다. 현재 작업 트리와 원본을 재확인하고 a216/a280 복원을 진행했다.
- 선택 불가능 항목 건너뛰기, byte 순환/지정 인덱스 보정, 이전/새 행 그리기와 event0 대기를 C++/MS5D에 연결했다.
- 원본 명령과 콜백을 실행한 1,986조건에서 전체 RAM 및 비디오 포트 순서/폭/값이 일치했다. 오류12조건과 상태보존, 기존 메뉴288조건 회귀 및 전체 테스트 통과.
- 보이는 다른 flags/콜백, 구분선 출력과 전체a370 프레임은 남았다. 다음 연결은 event 디스패치와 열기/활성/닫기 상태전환이다. docs/analysis/menu-navigation.md 참고.

## 2026-10-07 — 하위 메뉴 리소스와 스택 추가
- 이전 turn은 메뉴 이동/지정 선택을 원본1,986조건과 검증한 progress다.
- 부모93e0과 자식958a/978a/99ee를 같은 MS5D 창으로 추출하고 C++ 로더의4descriptor 일치를 확인했다.
- a0a0의 부모 비활성 다시 그리기, 새 슬롯 설정, current 복원과 문자 줄 위치 전달을 연결했다. 초기화 크기 계산을 공유한다.
- 원본377조건의 전체RAM/포트 일치, 오류14조건 및 롤백 통과. 기존초기화378/문자288조건 회귀와 전체검사 통과.
- 다음은 event 디스패치와 자식별 콜백, a370 전체프레임이다. docs/analysis/menu-stack.md 참고.

## 2026-10-07 — 부모 메뉴 이벤트와 정적 오브젝트 재시작
- 이전 turn은 하위 메뉴 추가377조건을 원본과 검증한 progress다.
- 9b3e와 부모6콜백의 하위 메뉴 열기/닫기/event7전파/재시작을 연결했다. BIOS c00444는 명시적 외부 전환으로 반환한다.
- 2a28 재시작에 실제 팔레트 해제·연결 좌표 갱신·필드 초기화를 재사용하고 watchdog 쓰기를 보존했다.
- 원본975조건의 전체RAM/포트/A2/외부 점프 일치, 오류6조건 및 트랜잭션 검사/전체테스트 통과.
- 헤더9430, 자식9602/9802/9aa8, 전체a370 및 BIOS호스트 전환은 남았다. docs/analysis/menu-event.md 참고.

## 2026-10-07 — 디버그 메뉴 toggle과 동적 글꼴 표시
- 이전 turn은 부모6콜백975조건과 정적 오브젝트 재시작을 검증한 progress다.
- debug9aa8의15bit 매핑을 MS5D로 보존하고 event1/2/3 toggle과 ON/OFF 출력, event4 닫기를 연결했다.
- font6b lookup표256개를 별도MS5D로 추출하고 결합문자/@문법을 구현했다. 이동·전체그리기·부모다시그리기도 동적event5를 실행한다.
- 원본debug2,100조건과 글꼴104스트림 일치. 부모975/기존문자288 회귀 및 전체테스트 통과.
- 자식9602/9802, 헤더9430, 전체a370 및 최종픽셀/음향은 남았다. docs/analysis/menu-debug.md 참고.

## 2026-10-07 — 스테이지 선택 목록과 상태 helper
- 이전 turn은 debug메뉴2,100조건 및 font6b104스트림을 검증한 progress다.
- 474f4의19그룹·59레코드를 MS5D창과 manifest로 추출했다. 원시header18바이트·이름/제어문자/padding을 보존한다.
- C++카탈로그와 count/record/name 조회450조건, 선택 상태helper272조건 전체RAM이 원본과 일치했다. 구조오류/출력보존 및 전체검사 통과.
- 9602/9802의 동적 포맷팅/표시와 전체frame, 레코드 참조대상 및 실제스테이지 실행은 남았다. docs/analysis/stage-catalog.md 참고.

## 2026-10-07 — 스테이지 이름 혼합 글꼴
- 이전 turn은19그룹·59레코드 추출과 조회450/상태272조건을 검증한 progress다.
- font68/6b 표를 기존MS5D로 함께 보존하고, C++에 스트림 내 글꼴 전환 및 direct00..0f/font30 경로를 연결했다.
- 실제59이름을 포함한704스트림에서 원본의 포트 순서·폭·값과 최종줄 위치 일치. 리소스1024바이트 원본일치, 전체테스트와 debug2,100조건 회귀 통과.
- 3a70은 RAM 상태가 있는 포맷터이므로 단순 printf로 대체하지 않는다. 9602/9802, 전체frame 및 최종픽셀/음향 연결은 남았다. docs/analysis/menu-fonts.md 참고.

## 2026-10-07 — RAM 상태를 보존하는 문자열 포맷터
- 이전 turn은 혼합글꼴과 실제59이름을704스트림에서 검증한 progress다.
- 3a70/3950/396e의 상태형 포맷터와 %s/%x/%%, 폭·패딩·인자소비를 C++에 복원했다. 기존 MS5D와 RAM/스택 인자를 사용한다.
- 원본289조건에서 전체64KiB RAM/ordered ports 일치. 빈문자열, D3 lowbyte 변경,256/512 인자 경계와 폭순환 포함. 전체테스트 및 glyph704스트림 회귀 통과.
- 9602/9802의 실제 콜백 통합과 구분선/전체frame, 최종픽셀·음향은 남았다. docs/analysis/formatted-text.md 참고.

## 2026-10-07 — 스테이지 그룹9..18 메뉴 이벤트
- 이전 turn은 상태형포맷터289조건과 glyph704스트림을 검증한 progress다.
- native978a/9802의 그룹선택·닫기·FOR/name 출력을 이벤트디스패처와 기존카탈로그/포맷터에 연결했다.
- 비어있는그룹의 이름pointer0은 원본vector prefix를 MS5D로 보존해 처리한다. 진입stack주소가 포맷터RAM/A2에 남는 효과도 유지한다.
- 원본1,120조건 전체RAM/ports/A2 일치. parent975조건 회귀와 전체테스트 통과.
- 9602와 전체행그리기/이동/부모다시그리기의 stage event5 연결, 전체frame/실제stage실행은 남았다. docs/analysis/stage-group-menu.md 참고.

## 2026-10-07 — 구역 선택과 중첩 행 갱신
- 이전 turn은 그룹9802의1,120조건과 parent975조건을 검증한 progress다.
- 9602의 구역 감소/증가·확인/취소·표시·초기 선택event6을 C++에 연결했다. 일반 행그리기와 이동에 stage context 및 줄 위치를 전달한다.
- 원본3,584조건에서 전체RAM/ordered ports/A2가 일치했다. fixture의 표시높이 입력 오류를 메인 리뷰에서 수정한 후 전부 다시 검증했으며, 보이는event6의768조건은 실제107..408개 포트 쓰기를 비교했다.
- stage9802 1,120 / 기존이동1,986 / debug2,100조건 회귀와 전체테스트 통과.
- 구분선, 부모다시그리기/스택추가의context, 헤더9430/전체frame 및 실제스테이지실행은 남았다. docs/analysis/stage-area-menu.md 참고.

## 2026-10-07 — 구분선과 스테이지 메뉴 전체 출력
- 이전 turn은 구역9602와 중첩 행 갱신3,584조건을 검증한 progress다.
- 9cd4 구분선을 일반 행그리기에 연결했다. 폭2의256칸 출력과 가려진 칸의 주소 정지를 원본대로 보존한다.
- native958a/978a 전체그리기5,040조건에서 전체RAM·ordered ports·최종D3가 일치했다. 콜백 진입stack은 전체그리기 진입보다20바이트 낮음을 관찰했다.
- 구분선에서 이동하는 경우까지2,526조건/오류12를 검증했다. 가림fixture를 수정한 후 실제 구분선 타일 개수도 별도 확인했다. 전체테스트 통과.
- 다음은 push_menu의 stage context/부모다시그리기 연결, 헤더9430 및 전체a370이다. docs/analysis/menu-separator.md 참고.


## 2026-10-07 — 스테이지 부모 다시 그리기와 메뉴 추가
- 이전 turn은 구분선과 전체 메뉴 출력 5,040조건을 검증한 progress다.
- push_menu가 기존 C++ 런타임 리소스와 stage context를 사용해 부모를 다시 그리고 새 자식을 초기화하도록 연결했다. 실제 event5 진입 스택을 전달하며 이중 보정하지 않는다.
- 원본 a0a0과 6,192조건의 전체 RAM·ordered ports·새 자식 슬롯이 일치했다. 실제 콜백 21,888회 모두 진입 A7=S−40을 확인했다.
- 기존 메뉴 추가 377조건/오류14, 이벤트 975조건/오류6, 전체 Python55개/C++검사 통과. 늦은 자식 초기화 오류와 context 누락 시 상태 보존도 확인했다.
- 다음은 헤더9430과 전체a370의 상태/호출 깊이 연결이다. 픽셀·타이밍·실제 스테이지 실행과 전체 게임 복원은 미완료다. docs/analysis/menu-stack.md 참고.

## 2026-10-07 — 메뉴 헤더와 스택 전체 다시 그리기
- 이전 turn은 스테이지 부모 메뉴 추가6,192조건을 검증한 progress다.
- native9430 종료 입력 처리를 기존9086 요청 선택기에 연결했다. 원본960조건에서 전체 RAM/A2 일치, 종료264/보존696조건이다.
- a6da의 오래된 순서 테두리/문자 다시 그리기와 마지막 current 보존을 구현했다. 원본692조건에서 전체 RAM·ordered ports·D3가 일치했다. mixed height/부분 범위/가림 flag를 포함하며 stage콜백3,305회 모두 진입S−28이다.
- 전체 Python55개/C++검사와 새 빈 범위/늦은 오류 rollback 검사 통과. docs/analysis/menu-frame.md에 전체 프레임 연결 시 호출/이벤트 순서를 기록했다.
- 다음은 a370의 활성/열기/닫기 경로를 한 프레임으로 연결하는 작업이다. 헤더 종료 요청 뒤에도 입력 처리가 계속되는 원본 순서와 경로별 콜백 스택을 보존해야 한다. 전체 게임 복원은 계속 미완료다.

## 2026-10-07 — 전체 메뉴 프레임과 실제 글꼴 렌더러
- 이전 turn은 헤더960/다시 그리기692조건을 검증한 progress다.
- a370 활성/열기/닫기, pending·입력·부모복귀를 하나의 C++ 프레임으로 연결했다. 호출 깊이에 맞는 stage context와 D3 전달을 유지한다.
- 원본92f0이 설치하는9332 및 a008의 전역renderer tail-call을 연결했다. covered glyph의 스타일/lookahead/cursor 보존도 검사했다.
- 원본834프레임 전체 RAM/ordered video·watchdog/status/external_jump/D3 일치. renderer3650/9332에서 시작해 자식 확인·취소·부모복귀를 수행하는10연속시퀀스 포함, stage콜백697회/포트155,889회다.
- 전체 Python55개/C++테스트 및 late-failure rollback 통과. docs/analysis/menu-frame.md와 reviews/0077 참고.
- 입력 A1=전역renderer 계약이며 실제 호출자92da/92fc의 레지스터·입력 수집/스케줄링 연결, 다른 descriptor/flags, 최종 픽셀/타이밍·실제 게임 실행은 남았다. 전체 목표는 active다.

## 2026-10-07 — 제어 요청 수락과 실제 메뉴 진입
- 이전 turn은 a370 프레임834조건과10연속시퀀스를 검증한 progress다.
- 9136의 비활성 요청 수락을 C++로 구현했다. 원본8,192조건 전체 RAM/반환byte 일치(수락8,169/미진입23), 활성 상태는 이 API에서 명시적으로 거절한다.
- 실제92ce의 ca9e773비디오쓰기→a29c→renderer9332→첫a370→92a8입력누적/감소를 연결했다. 고립432조건과3열기시퀀스15호출의 전체 RAM/ports/D0/D3 일치, 실제9332 렌더링까지 확인했다.
- 전체 Python55개/C++테스트와 늦은 진입 실패 rollback 통과. docs/analysis/control-request.md, reviews/0078 참고.
- 활성 컨트롤러의 대기/반복, 메뉴 종료 뒤 간접콜백/928e 출력과 실제 입력 수집·스케줄링, 픽셀·타이밍 및 전체게임실행은 남았다. 전체 목표는 active다.

## 2026-10-07 — 활성 대기·반복과 PAUSE 런타임 리소스
- 이전 turn은 비활성 요청수락8,192조건 및 실제메뉴진입432조건/열기시퀀스를 검증한 progress다.
- active7df0!=0/7dee==0 경로의 플레이어별 우선순위, 새 진행/누름 유지, 점멸 표시/억제, 메뉴 진입과 입력누적을 연결했다.
- PAUSE/공백30원본바이트를 기존MS5D(62바이트)로 추출하고 C++에서 사용한다. 원본제어문자/패딩을보존한다.
- 원본1,416조건의 전체RAM/238,180ports/signedD0/D3 일치. 대기표시 뒤D0상위word가남는차이를 원본비교에서발견해수정했다. 반환status의lowbyte가호출자상태다.
- 두플레이어의누름유지와점멸4시퀀스120회,실제분기/script주소검증및전체Python61개/C++테스트통과. docs/analysis/control-request.md,reviews/0079참고.
- 다음은이미열린메뉴의종료간접callback/928e지우기와9136전체제어통합이다. 전체게임실행/최종픽셀/타이밍은남아있으며전체목표는active다.

## 다음 작업
1. 실제 ROM 애니메이션 스크립트의 참조·경계를 확인하고 런타임 리소스로 추출한다. 분기 등 나머지opcode를 해석해 상태 실행기에 연결한다.
2. 팔레트·애니메이션·맵 참조 경로를 오브젝트 코드와 연결한다.
3. 원본에 근거한 대표 오브젝트 표시·애니메이션·이동을 런타임에 연결한다.
4. RAM 변환 코드의 실제 역할과 Z80 사운드 시퀀스를 분석한다.

## 미해결
- 복호화된 데이터의 리소스 해석, 코드 분석, 엔진 재구성은 아직 미완료.
- 원본 비교 실행을 위한 에뮬레이터 환경·BIOS는 확인되지 않았다.
- 원격 저장소와 공개 범위 미정.

기존 실제ROM 루프의96호출·192비디오단계 회귀도 원본과 일치했다.


## 2026-10-07 — 열린 제어 메뉴의 프레임·종료 연결

- `finish_control_menu`로9302의 byte 상태 판정, word 종료 플래그,928e의 원본 공백 출력과 제어 해제를 복원했다. C++에서 기존 PAUSE MS5D를 직접 읽는다.
- `step_control_menu`는 이미 열린 메뉴의 a370 호출과 종료 꼬리를 연결한다. 실제 콜백 스택 깊이를 보존하고 BIOS 전환은 별도로 반환한다.
- 종료 꼬리880조건, 연결1,027프레임의 전체 RAM/signed D0/D3/포트 비교가 통과했다. 연결 검증에는13개 연속 시퀀스, stage callback697회, 포트165,533회와 실제9136 진입36회가 포함된다.
- 메뉴 종료138회에서 원본9302의 D1 보존을 확인했다. 마지막 root pop 후 콜백·문자열 오류가 발생해도 API의 RAM/result/ports를 모두 보존한다.
- Python61개 및 C++ 전체 테스트 통과. 분석: docs/analysis/control-request.md. 리뷰: docs/reviews/0080-control-menu-finish.md.
- 비영 종료 콜백은 호출이 필요할 때 명시적으로 거절한다. 고정 ROM에서 직접 비영 쓰기를 찾지 못했다는 사실을 콜백이 불가능하다는 결론으로 바꾸지 않았다.
- 다음 작업은 비활성 수락·활성 대기·열린 메뉴 분기를 하나의 컨트롤러 진입으로 통합하고, 실제 호출자의 상태 byte 처리·게임 갱신 스케줄링을 연결하는 것이다. 전체 게임 복원 목표는 active다.


## 2026-10-07 — 통합9136 컨트롤러와 호출자 실행 분석

- `step_control`로 비활성 수락·활성 대기·열린 메뉴 분기를 하나의 C++ 진입 API/CLI에 연결했다. 기존 바이너리 리소스를 그대로 사용하며 모든 실패 출력 보존 계약을 유지한다.
- 원본9136과835조건, 포트102,635회, 전체 RAM/signed D0/D3가 일치했다.4개 연속 시퀀스는 활성화·자식 메뉴 조작·전체 종료·재활성화·두 번째 종료를 포함한다.
- `analyze_control_caller.py`는 실제f5a 이후512조건에서 helper 호출 순서, video word/포트, 효과 저장/복구, 카운터 wrap/trap 경계와 좌표 단계byte를 확인했다. 전체RAM 비교가 아닌 관측·명시적 조건 검사임을 구분했다.
- `make all test`: Python61개와 C++ 전체 통과. 리뷰: docs/reviews/0081-control-dispatch.md. 분석: docs/analysis/control-request.md 및 control-caller.md.
- 다음은3d7e/3db2의 video 제어와43dbc 단계byte 갱신을 구현하고,9136의 반환값 소비·팔레트 효과 API를 f54 호출자 순서로 연결하는 것이다. ec4의 동기화·입력 수집과 실제 게임 갱신은 아직 미완료다. 전체 목표는 active다.


## 2026-10-07 — 호출자의 비디오 제어 word 복원

- 3db2 조회와3d7e 설정을 `query_video_control`/`set_video_control`로 구현했다. RAM shadow4d90/91과3c0006의word쓰기를 보존한다. 입력257 이상을 clamp하지 않고 원본 byte 저장을 따른다.
- 모든16비트 입력65,536개, 모든shadow65,536개 경계 설정 배치와 별도 조회65,536개가 원본과 일치했다. CLI194조건에서 전체64KiB RAM/조회값/포트를 비교했다.
- 전체 `make all test`(Python61개/C++ 전체),CLI 숫자·별칭·배치 framing 오류 검사 통과. 리뷰: docs/reviews/0082-video-control.md.
- ec4의100016/100017 대기 및3c0006 **읽기** 경로도 명령 근거로 문서화했다. 쓰기shadow가 읽기결과를 대신한다고 가정하지 않는다.
- 다음은43dbc의 단계byte와 호출자 카운터,기존 팔레트 효과 API를 f54/f5a 순서로 연결하는 것이다. 인터럽트·실제 입력·타이밍·전체 부팅은 미완료이며 전체 목표는 active다.


## 2026-10-07 — 진행 카운터 검사와 좌표 단계 전환

- `advance_control_counter`로fe2..1000의word비교·16비트wrap·43dbc 단계byte갱신을구현했다. 불일치는RAM을보존하고trap명령직전경계로반환한다.
- 원본과1,734조건전체RAM/경계일치. 실제trap경계863회,phasehelper871회,모든256phase와메모리중첩순서를확인했다. CLI오류/별칭25조건도출력을보존했다.
- `make all test`(Python61개/C++전체)통과. 리뷰: docs/reviews/0083-control-counter.md. 보고서: artifacts/control_counter/verification.json.
- 비디오제어와진행카운터의연결준비가끝났다. 다음은기존팔레트효과API까지포함하여f5a호출자순서를통합하고,효과갱신의watchdog·뱅크쓰기출력범위를확인하는것이다. 전체목표는active다.


## 2026-10-07 — 컨트롤러 반환값 소비와 팔레트 하드웨어 출력 연결

- `consume_control_result`로f5a의상태전환·비디오조회/복구·팔레트저장/설정/갱신/복구·카운터처리를원본순서로연결했다. ec4루프,fee trap직전,정상rts를구분한다.
- `step_palette_frame`에watchdog256회와준비전후PVC bank word4회의선택적출력을추가했다. 기존RAM전용호출은유지한다.
- 원본호출자276조건의전체RAM·경계·포트16,108회와독립팔레트140조건의전체RAM·포트18,712회가일치했다. 미지원palette ID의늦은실패는앞선변경과출력을취소한다. 원본trap경계는앞선복구변경을확정한다.
- 실제MS5P파일을원본에서재추출한전체내용과비교했다. 고정ROM/팔레트뱅크의불변부분도확인했다.
- `make all test`(Python61개/C++전체),CLI범위·별칭검사통과. 리뷰: docs/reviews/0084-control-caller.md. 보고서: artifacts/control_caller/verification.json.
- 다음은f54의9136호출부터이후소비까지단일진입으로연결하고,ec4의입력·인터럽트대기를추적하는것이다. 전체CPU상태·장치타이밍·게임부팅은미완료이며전체목표는active다.


## 2026-10-07 — f54 컨트롤러 호출과 반환 소비 통합

- `step_control_caller`로9136호출부터비디오/팔레트/카운터처리까지한API로연결했다. 원본JSR의4byte스택깊이와BIOS우회를보존한다.
- 원본f54의410조건/104,487포트/전체RAM/경계가일치했다.2개연속시퀀스129프레임은전체종료·재활성화까지이어갔다.
- 실제f5a409회에서A6와호출자A7보존확인. 정적재시작과BIOS전환,stage callback깊이12/16/32byte,늦은palette오류rollback을검증했다.
- `make all test`(Python61개/C++전체)와CLI숫자·별칭검사통과. 리뷰: docs/reviews/0085-control-caller-step.md.
- 다음은31d6의실제포트입력/반복byte와b68을구현하고,vector64→20c→c8c의대기신호생산경로를ec4루프에연결하는것이다. 시간축·전체CPU상태·게임부팅은미완료이며전체목표는active다.

## 2026-10-07 — 입력 포트·반복 타이머·원본 재생 스트림 복원

- `sample_input`으로31d6의 모드별 입력 처리와352a 재생을 구현했다. 같은 포트의 두 번 읽기, byte 반복 타이머, 비트15 토글, 종료 호출의 입력 유지와 커서 저장 순서를 보존한다.
- 네600바이트 버퍼와 두 포인터 테이블을 기존 MS5D 바이너리로 추출했다. 미사용 기록 대상까지 보존하며 C++이 원본 바이트를 직접 읽는다. 확인용 변환 파일에 의존하지 않는다.
- 원본과 전체 RAM4,301조건, 연속 재생 상태689,769회 및 최종 전체 RAM이 일치했다. 추출 창 밖의 실제 읽기 등9개 실패 조건은 출력을 보존했다. 원본 ROM 불변·MMIO 읽기 순서도 확인했다.
- `make all test`: Python67개와 C++ 전체 통과. 리뷰: docs/reviews/0086-input-sampler.md. 보고서: artifacts/input_sampler/verification.json.
- 다음은3162 초기화와b68의 상태 입력 후처리, 인터럽트 신호를 ec4 루프에 연결하는 것이다. b68의 lookup은 ADD.B 때문에 최대256바이트 창이 필요함을 명령으로 확인했다. CPU 레지스터 전파·실제 타이밍·전체 부팅은 미완료이며 전체 목표는 active다.

## 2026-10-07 — 입력 초기화와 샘플러 연결

- `initialize_input`으로 원본3162 초기화를 구현했다. 기존 MS5D 포인터 테이블에서 두 재생 선택값을 시작하며, 선택값2 이상에서 재생 상태를 남기는 원본 분기를 보존한다.
- 원본 초기화121조건과 이어지는 입력 갱신120회에서 전체64KiB RAM이 일치했다. CLI 오류·파일 별칭17조건에서 입력과 기존 출력 보존을 확인했다.
- `make all test`: Python67개 및 C++ 전체 통과. 리뷰: docs/reviews/0087-input-initializer.md. 보고서: artifacts/input_initializer/verification.json.
- 다음은b68 상태 후처리와 인터럽트 신호 생산을ec4 루프에 연결하는 것이다. 전체CPU 레지스터·장치 시간축·전체 부팅은 미완료이며 전체 목표는 active다.

## 2026-10-07 — 입력 상태 후처리와 샘플링 통합

- `update_input_status`로b68의 상태 복사·pending 비트 소모·슬롯 조회를 복원하고, `step_input`으로31d6→b68을 연결했다. 후처리 실패 시 입력 갱신까지 취소한다.
- 조회 인덱스의 byte wrap을 보존하도록b58..c58 전체256바이트를 MS5D로 추출했다. 명령과 겹치는 원본 바이트도 유지한다.
- 원본 전체RAM 비교576조건과 승계160회 갱신, 오류·파일 별칭12조건 통과. Python73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0088-input-status.md.
- 다음은f12 입력 호출자의 신호 초기화와 callback 분기, CPU 반환 레지스터 의존성 및 인터럽트 연결이다. c8c가 사운드·작업 복구까지 호출함을 정적으로 확인했다. 전체 게임 부팅과 시간축은 미완료이며 목표는 active다.

## 2026-10-07 — f12 입력 호출자와 스타일 전달

- `begin_input_frame`으로 갱신 신호 복사·초기화,31d6→b68과 오브젝트 callback 분기까지 연결했다. f54 또는f3c 직전 경계를 반환하며 callback은 실행하지 않는다.
- 입력 샘플러에 선택적인D1.word 전달을 추가했다. 재생 이벤트가 있을 때와 대기할 때의 상위 바이트 차이를 보존하며, 실패 시 style도 취소한다.
- 원본437조건(승계200회 포함)의 전체RAM/정확한D1/경계 정보가 일치했다. 토글48·비토글94조건, A6/A7/D3 보존과 오류·별칭16조건을 확인했다. Python73개와 C++ 전체 검사 통과. 리뷰: docs/reviews/0089-input-frame.md.
- 루트 오브젝트100820의+76/+7a 설정 함수e40/e44를 확인했다. 자연 호출 경로는 미확인이다. 다음은f54 컨트롤러와 입력 호출자 연결, callback/인터럽트 의존성 추적이다. 전체 부팅·시간축은 미완료이며 목표는 active다.

## 2026-10-07 — 입력에서 컨트롤러 반환 소비까지 통합

- `step_input_control`로f12 입력 신호 초기화·샘플링·후처리에서f54 컨트롤러와f5a 반환 소비까지 연결했다. 실제 입력D1을 넘기며 callback은f3c 경계로 반환한다.
- 원본338조건의 전체RAM과69,521 포트 쓰기가 일치했다. 두 raw 버튼 시퀀스146회에서 stage 선택·전체 종료·진행·재활성화·재종료를 확인했다.
- f54 직전 레지스터 보정 없이 A1=b58 상태로 검증했다. D3/A6/스택 보존과 자식callback 깊이, BIOS·trap·callback 경계를 확인했다. 늦은 팔레트 오류2조건은 출력을 보존한다.
- Python73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0090-input-control.md. 보고서: artifacts/input_control/verification.json.
- 다음은ec4의 대기 신호와 video counter 취득을 입력 진입에 연결하고, 인터럽트·외부callback 의존성을 복원하는 것이다. 전체 게임 부팅과 실제 시간축은 미완료이며 목표는 active다.

## 2026-10-07 — 대기 신호와 비디오 읽기 연결

- `poll_frame_gate`로ef2의 unsigned 대기 조건과 조건부3c0006 word 읽기·0018 저장을 복원했다. `poll_input_control`은 준비된 경우에만 기존 입력/컨트롤러를 실행한다.
- 모든 signal/threshold 조합과 video word 총131,072조건에서 원본과 일치했다. 대기32,640건은 비디오 읽기가 없었고 준비98,432건은 정확히1회였다.
- C++ 전체RAM48조건, 통합14조건과 늦은 오류2조건 통과. 호스트 신호를 명시적으로 바꾸는8회 승계로 대기/준비 재진입을 확인했다. Python73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0091-frame-gate.md.
- 다음은ec4의 선택적 디버그 출력과 인터럽트 신호 생산을 연결하는 것이다. 현재 호스트 신호 fixture는 실제 interrupt 구현이 아니다. BIOS·사운드·작업 복구·장치 시간축·전체 부팅은 남아 있으며 목표는 active다.

## 2026-10-07 — 인터럽트 실행 근거와 사운드 큐 소비

- c8c 원본5,632개 진입 조건과864개 제한된 전체 반환 조건을 실행해 재진입·신호 포화·watchdog·플래그 종료 순서를 확인했다. 사운드 생산/렌더링/credit 관련 실제 의존 경계4개를 기록했다.
- `service_sound_queue`로3cb2의 status 읽기, 우선 명령과128바이트 큐의 연속 중복 합치기를 복원했다. 원본2,575조건의 전체RAM과 사운드 포트2,394건이 일치했다.14개 실패 조건은 출력 보존을 확인했다.
- Python73개와 C++ 전체 검사 통과. 리뷰: docs/reviews/0092-sound-queue-interrupt-flow.md. 분석: docs/analysis/interrupt-flow.md 및 sound-queue.md.
- 다음은48156/3af8의 사운드 생산과3ac8 byte 큐의 대기 관계를 복원하여3cac 호출을 완성하는 것이다. 전체 interrupt·BIOS·작업 복구·사운드CPU·오디오 시간축은 아직 미완료이며 목표는 active다.


## 2026-10-07 — 사운드 byte 생산과 캡처 상태 재개

- `enqueue_sound_byte`와 `resume_sound_byte`로3ac8/3aea를 복원했다. 가득 찬 큐는 pending 상태를 반환하고 원본이 캡처한 쓰기 위치로 재개한다.
- 원본523조건의 전체RAM/pending이 일치했다. 모든 command/tail,260회 대기와 실제 소비자를 끼운 두 문맥 보존 시퀀스,16개 오류/별칭 검사를 통과했다.
- Python73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0093-sound-byte.md. 분석: docs/analysis/sound-byte.md.
- 다음은48156/3af8의 word 명령 생산과3c08 배출을 연결하는 것이다. 자연적인 대기 재개 스케줄링, 전체 interrupt·Z80·오디오 시간축과 게임 부팅은 미완료이며 전체 목표는 active다.


## 2026-10-07 — 상위 사운드 명령 큐와 배출 복원

- `enqueue_sound_word`, `drain_sound_words`, `resume_sound_word`로3af8/3c08을 복원했다. 필터와 한 슬롯 중복 교환, overflow의 선행 head 갱신, 배출의 지연 head 저장과 상·하위 byte 대기를 보존한다.
- 원본2,241조건의 전체RAM/pending이 일치했다. 필터2,048조합, 실제 CPU 문맥 재개22회와25개 실패/별칭 보존 검사를 통과했다. 메인 리뷰에서 필터에 걸려 큐를 검증하지 못하던 fixture를 수정하고 실제 경로 도달 assertion을 추가했다.
- 별도48156 원본65,536조건에서 signed 타이머, 명령과 전체D0/전체RAM/분기 경계를 확인했다. 생산자는 첫 명령 전에 중단했으며 C++ 타이머 검증은 아니다.
- Python73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0094-sound-word.md. 분석: docs/analysis/sound-word.md 및 sound-timer.md.
- 다음은48156 타이머를 상위 생산자에 연결하고3cac의 생산→소비 및 대기 재개를 구성하는 것이다. 전체 interrupt·자연 스케줄링·Z80·오디오 시간축과 전체 부팅은 미완료이며 목표는 active다.


## 2026-10-07 — 사운드 타이머에서 생산·소비까지 연결

- `step_sound`로3cac의48156→3af8→3cb2를 연결하고 `resume_sound`로 생산자 대기 이후를 이어간다. 정상 대기 시 timer/word 상태를 보존하고 소비자는 생산 완료 후에만 실행한다.
- 원본718조건의 전체RAM/포트/pending/read_count가 일치했다.40회 연속 tick, 실제 원본 문맥의 high/low 대기 재개, 모든status byte와 timer wrap 필터를 확인했다.16개 실패/별칭 조건은 출력 보존을 확인했다.
- Python73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0095-sound-service.md. 분석: docs/analysis/sound-service.md.
- 다음은c8c의 credit/busy 분기, 렌더링·작업 복구 의존성과 사운드 서비스를 연결하는 것이다. 전체 인터럽트·BIOS·자연 스케줄링·Z80·오디오 시간축과 전체 부팅은 미완료이며 목표는 active다.


## 2026-10-07 — 인터럽트 선행 크레딧 요청 처리

- `process_credit_request`로bbe→a74/a2c/a4e를 복원했다. 두 크레딧의 BCD 차감, 요청/상태 마스크와 전체D0의 byte/word 이동을 보존한다. 이 경로에 BIOS 호출은 없다.
- 원본1,326조건의 전체RAM/전체D0가 일치했다. 모든256개 크레딧/요청 byte와32회 승계를 포함하며7개 크기/별칭 오류에서 출력 보존을 확인했다.
- Python73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0096-credit-request.md. 분석: docs/analysis/credit-request.md.
- 다음은c8c 호출자와 요청 처리·사운드 서비스를 연결하고 렌더링/작업 복구 의존성을 복원하는 것이다. 전체IRQ 레지스터/CCR·BIOS·자연 시간축·Z80와 전체 부팅은 미완료이며 목표는 active다.


## 2026-10-07 — 인터럽트 열 위치 제어와 네 구조체 호출자

- `refresh_column_controls`와 `refresh_scene_columns`로187d8/1adf8을 복원했다.32개 열의 위치/보정, 요청bit 제거, 주소·좌표word 순환과 네 구조체/PVC 쓰기 순서를 보존한다.
- 원본1,441조건의 전체RAM/D0와78,272개 포트 기록이 일치했다.전체256flags·각축512유효좌표·16활성 조합과11개 오류/별칭 보존 검사를 통과했다.
- Python73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0097-column-control.md. 분석: docs/analysis/column-control.md.
- 다음은c8c에 기존팔레트·열제어·일반스프라이트·사운드를 연결하기 위한 레지스터 전달과 작업 복구를 복원하는 것이다. 전체IRQ·상위맵자료·장치시간축·Z80와 전체 부팅은 미완료이며 목표는 active다.


## 2026-10-07 — 팔레트 전송의 D0와 포트 순서 보완

- `transfer_palette_banks_traced`로 기존두bank전송에 원본D0와bank/palette/watchdog포트기록을 추가했다. 일반전송과역순전체채우기의차이를보존한다.
- 원본680조건의전체RAM/두bank/표시bank/D0와190,792포트가일치했다.36개전체채우기와이어지는전송,14개오류/별칭보존을확인했다.
- Python73개및C++전체검사통과. 리뷰: docs/reviews/0098-palette-transfer-trace.md. 분석: docs/analysis/palette-transfer-trace.md.
- 다음은일반스프라이트의반환레지스터의존성과작업복구를확인하고c8c호출자에기존함수들을연결하는것이다. 전체IRQ/장치시간축/Z80/상위맵자료와전체부팅은미완료이며목표는active다.


## 2026-10-07 — 스프라이트 갱신 D0 반환 보완

- `refresh_sprite_queue`에선택적D0전달을추가했다. 준비되지않은큐는입력을보존하고준비된큐는두번째pool정리의원본반환값을낸다. 비디오출력이0개여도정리함수의D0변경을보존한다.
- 원본584조건의전체RAM/D0와370,740비디오쓰기가일치했다.8개오류/별칭에서출력보존을확인했다. 네이티브PVC4,208쓰기는다음통합용관찰이며현재C++과비교한전체포트결과가아니다.
- Python73개및C++전체검사통과. 리뷰: docs/reviews/0099-sprite-refresh-d0.md. 분석: docs/analysis/sprite-refresh-queue.md.
- 다음은스프라이트PVC쓰기를비디오쓰기사이에정확히연결하고작업복구/c8c호출자를복원하는것이다. 전체IRQ/장치시간축/Z80/상위맵자료와전체부팅은미완료이며목표는active다.


## 2026-10-07 — 스프라이트 뱅크 전환과 비디오 순서 통합

- `refresh_sprite_queue`의선택적ports출력으로매레코드PVC전환·비디오·후행정리·기본bank복구를연결했다. 비활성pool에서도원본뱅크전환을보존한다.
- 원본608조건의전체RAM/D0와378,428포트(PVC4,448/비디오373,980)가일치했다. 네flip/양방향/0레코드/승계8회및8개실패/별칭을확인했다. 실제리소스는bank2범위다.
- Python73개및C++전체검사통과. 리뷰: docs/reviews/0100-sprite-refresh-ports.md. 분석: docs/analysis/sprite-refresh-queue.md.
- 다음은c8c의기존하위함수연결과대기작업복구를복원하는것이다. 전체IRQ/장치시간축/Z80/상위맵자료와전체부팅은미완료이며목표는active다.


## 2026-10-07 — 인터럽트 저장 작업 프레임 복구

- `restore_interrupt_task`로ce2부터d28 RTS의작업진입경계까지복원했다. D0..D7/A0..A7,복원A5기준포인터쓰기,후속PC/A6읽기와외부스택쓰기를보존한다.
- 원본279조건의전체RAM/16레지스터/포트/실제스택쓰기가일치했다.32개정규프레임·alias·경계와25개실패/별칭보존을확인했다.
- Python73개및C++전체검사통과. 리뷰: docs/reviews/0101-interrupt-task.md. 분석: docs/analysis/interrupt-task.md.
- 다음은c64등록과작업복귀d2a반복및c8c전체호출자연결이다. 작업본문실행·SR/CCR·장치시간축/Z80/상위맵자료와전체부팅은미완료이며목표는active다.


## 2026-10-07 — 인터럽트 작업 등록과 역순 복구 연결

- `queue_interrupt_task`로 c64 등록을 복원했다. 두 복귀 주소, 레지스터 저장 순서와 큐가 가득 찼을 때의 스택 정리를 보존한다.
- 원본 등록/건너뛰기 176조건과 동일 RAM의 32개 작업 역순 복구에서 전체 RAM·16개 레지스터·스택 쓰기가 일치했다. 오류/별칭 19조건도 통과했다.
- Python 73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0102-interrupt-task-queue.md. 분석: docs/analysis/interrupt-task.md.
- 다음은 작업 복귀 d2a 반복 및 c8c 호출자 연결이다. 작업 본문 실행·SR/CCR·장치 시간축/Z80/상위 맵 자료와 전체 부팅은 미완료이며 목표는 active다.


## 2026-10-07 — 작업 반환 뒤 다음 작업으로 전환

- `resume_interrupt_tasks`로 d2a에서 A5를 복구하고 현재 큐를 다시 읽는 반복 진입을 연결했다. 입력 스택은 callback RTS 이후이며 추가 pop하지 않는다.
- 원본 312조건, 오류/별칭 24조건 통과. 32개 연속 작업과 마지막 빈 큐에서 전체 RAM·레지스터·포트·스택 쓰기가 일치했다. 작업 본문은 실행하지 않았으며 호스트 입력 변화를 명시했다.
- Python 73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0103-interrupt-task-resume.md.
- 다음은 c8c의 busy/credit/렌더링/작업/사운드 경계를 연결하는 것이다. 전체 IRQ·작업 본문·SR/CCR·장치 시간축/Z80 및 전체 부팅은 미완료이며 목표는 active다.


## 2026-10-07 — c8c 렌더링·작업·사운드 서비스 통합

- `begin_interrupt_service`, `continue_interrupt_service`, `resume_interrupt_service_sound`로 busy/카운터/크레딧/팔레트/열 제어/실제 MS5C 스프라이트/작업/사운드 흐름을 연결했다. 중단 시 busy를 유지하며 정상 완료에만 전체 byte를 지운다.
- 원본676조건과54,586개 장치 쓰기, 오류/별칭18조건을 통과했다. 두 bank/전체 RAM 및 작업 경계 레지스터·스택, 사운드 문맥 재개를 비교했다. Python73개 및 C++ 전체 검사 통과.
- 메인 리뷰에서 검증 CLI 인자와 전체 dirty fixture 도달성을 수정하고 예상 밖 장치 쓰기 및 작업→사운드 대기 경로를 보강했다. 리뷰: docs/reviews/0104-interrupt-service.md. 분석: docs/analysis/interrupt-service.md.
- 고정 첫1MiB에서 c64 직접 JSR/BSR 후보가 발견되지 않았다. 간접/뱅크 코드와 자연 사용 여부는 미확인이며 큐의 기능 검증과 구분한다.
- 다음은20c IRQ의 외부 callback/BIOS 경계와 bank·VRAM 복구, 초기화 c42 및 메인 루프와의 연결이다. 전체 IRQ·작업 본문·SR/CCR·장치 시간축/Z80 및 전체 부팅은 미완료이며 목표는 active다.


## 2026-10-07 — IRQ 외부 스택 저장과 복구

- `begin_irq_envelope`와 `finish_irq_envelope`로20c 진입→callback/BIOS 경계,248→RTE 직전 경계를 복원했다. 실제 스택 bytes 및 쓰기 순서, bank/VRAM/비디오 상태와15개 저장 레지스터를 다룬다.
- 원본1,342조건·오류/별칭20조건에서 전체 RAM/스택/16레지스터/포트가 일치했다.16개 진입/종료 쌍을 포함한다. Python73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0105-irq-envelope.md.
- 정적 슬롯 조사와 메인 원본 확인에서3dce가100006/10000a에3dcc RTS를 설정한다. 초기화 호출 후보를 기록했으며 자연 도달성은 별도다.
- 입력mslug5.zip의13항목은게임P/C/M/V이며 BIOS가 없다. BIOS 내부 실행 검증은 미완료이나 다른 게임 코드 작업은 계속 가능하다.
- 다음은c42/3dce 초기화 및 기본 콜백 연결, IRQ/메인 루프의 경계 연결이다. RTE·SR/CCR·BIOS·장치 시간축/Z80 및 전체 부팅은 미완료이며 목표는 active다.


## 2026-10-07 — 인터럽트 초기화와 기본 콜백에서 첫 서비스까지

- `initialize_interrupt_state`와 `initialize_irq_callbacks`로 c42/3dce를 복원하고 `return_default_irq_callback`으로3dcc의 실제 스택 반환을 연결했다. 기존 작업 프레임과 RAM18 등 초기화 대상 밖의 bytes는 보존한다.
- 초기화640조건, envelope/콜백35조건, 초기화→20c→실제3dcc→23c의JSR c8c→242 연결16조건 및 오류/별칭13조건 통과. Python73개 및 C++ 전체 검사 통과.
- 검증 도구의 캐시된 실행이 중단 경계를 넘는 문제를 code hook 중단으로 수정했다. 원본 ROM은 변경하지 않았다. 리뷰: docs/reviews/0106-interrupt-init.md. 분석: docs/analysis/interrupt-init.md.
- 다음은 IRQ 서비스의 메인 루프 입력/프레임 대기 연결 및 남은 raster IRQ29c/비디오 제어 경계다. BIOS/RTE/SR/CCR·장치 시간축/Z80 및 전체 부팅은 미완료이며 목표는 active다.


## 2026-10-07 — 실제 IRQ 신호로 프레임 대기 해제 및29c 복구

- 실제 c8c 서비스가 만든 신호를 공유 RAM의 메인 ef2 poll에 연결해573조건(IRQ279/poll294), 포트1,070개를 비교했다. 호스트가 RAM16을 직접 변경하지 않고0→255를 서비스255회로 생성했다. 메인 문맥 복구와 다음 프레임 진입은 명시적 호스트 조건이다.
- `begin_raster_irq`/`finish_raster_irq`로29c의 활성·비활성 분기, 기본 콜백과VRAM/A5 복구를 구현했다. 원본386조건, 포트314개/스택 쓰기441개 및 오류23조건 통과.
- CLI 모드 검사/분기 누락을 메인이 수정하고 재검증했다. Python73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0107-interrupt-frame-raster.md.
- 다음은ec4 앞부분과f3c 콜백 재개를 연결하여 명시적인 다음 poll 진입을 실제 메인 흐름으로 대체하는 것이다. SR/RTE/BIOS·장치 시간축/Z80 및 전체 부팅은 미완료이며 목표는 active다.


## 2026-10-07 — 메인 콜백의 실제 호출 스택과 오브젝트 복구

- `enter_main_callback`/`restore_main_callback`으로 f3c 호출과 f44 복귀를 복원했다. 이미 읽은 A0와 실제 스택의 저장 A6를 사용하고 콜백의 다른 레지스터 변경을 보존한다. f46 팔레트 호출 직전까지다.
- 원본352조건, 실패/별칭21조건 및 실제 기본RTS16회 연결 검증 통과. 전체 RAM·스택·16레지스터·스택 쓰기가 일치했다. Python73개/C++ 전체 검사와 추가 API 단위 검사 통과.
- 리뷰: docs/reviews/0108-main-callback-stack.md. 분석: docs/analysis/main-callback-stack.md.
- 다음은5728 팔레트 처리의 최종D1을 복원하고 f4c 대기를 연결하는 것이다. f4c는 RAM16!=0만 검사하므로 ef2 임계값·비디오 읽기를 재사용하면 안 된다. ec4 앞부분, 실제 콜백 본문, SR/RTE/BIOS·장치 시간축/Z80 및 전체 부팅은 미완료이며 목표는active다.


## 2026-10-07 — 팔레트 처리의 최종 D1 복원

- `step_palette_frame`/`prepare_palettes`에 선택적 D1 입출력을 추가했다. 타이머 byte 계산, 마지막 색 보정·혼합 결과와 단순복사 시 이전 D1 보존을 반영했다. 실제 MS5P 바이너리 리소스를 사용한다.
- 원본566조건과 MMIO43,684개, 오류14조건 통과. 전체RAM/32비트D1/시간순 포트를 비교했다. Python73개 및 C++ 전체 검사 통과.
- 리뷰: docs/reviews/0109-palette-d1.md. 분석: docs/analysis/palette-d1.md.
- 다음은 복구된D1을 f46 팔레트 호출→f4c 대기→f12 입력에 연결하는 것이다. ec4 앞부분, 실제 콜백 본문, SR/RTE/BIOS·장치 시간축/Z80 및 전체 부팅은 미완료이며 목표는active다.


## 2026-10-07 — 콜백·팔레트·IRQ 신호에서 다음 입력까지 연결

- `poll_callback_input_control`로 f4c의 신호!=0 대기를 연결했다. RAM17 임계값을 무시하고 비디오를 읽지 않으며 RAM18을 유지한다. 대기 시 팔레트 타이머를 재실행하지 않는다.
- 원본537조건, 포트286개 및 오류5조건 통과. 네 가지 팔레트D1 전달과 실제3dcc 콜백→팔레트→대기→IRQ신호→다음입력 주기를 비교했다. 인터럽트 사이의 CPU 문맥 복구는 명시적 호스트 동작이다.
- Python73개 및 C++ 전체 검사 통과. 리뷰: docs/reviews/0110-callback-frame-flow.md. 분석: docs/analysis/callback-frame-flow.md.
- 다음은 ec4 앞부분의 진단 텍스트 출력과 ef2 대기를 연결하는 것이다. 이 경로는 renderer3650을 사용하며 기존 포맷터는e84c8 전용이므로 렌더러 차이를 먼저 반영해야 한다. 실제 게임 콜백 본문, SR/RTE/BIOS·장치 시간축/Z80 및 전체 부팅은 미완료이며 목표는active다.


## 2026-10-07 — 진단 텍스트의 직접 문자 렌더러3650

- 기존3a70포맷터에3650선택을추가했다. 실제renderer주소를RAM에저장하며font/lookahead없이한바이트타일을출력한다. 기본e84c8호출은유지한다.
- 원본487조건과포트10,426개,오류13조건통과. 실제d56/df0진단4조건포함. 기존289조건회귀와Python73개/C++전체검사도통과했다.
- 리뷰: docs/reviews/0111-formatted-direct.md. 분석: docs/analysis/formatted-text.md.
- 다음은진단format/인자표의정규MS5D추출과ec4조건분기·최종D1전달을연결하는것이다. 실제게임콜백본문,SR/RTE/BIOS·장치시간축/Z80및전체부팅은미완료이며목표는active다.


## 2026-10-07 — 메인 진단 리소스와 조건부 출력

- d56..e3f의format/20포인터를정규main_debug.ms5d와manifest로추출했다. step_main_debug로ec4→ef2직전의조건부출력과최종D1을복원했다. 종료제어문자style은RAM상태와별도로반환한다.
- 원본790조건,포트61,272개,오류11조건통과. Python73개및C++전체검사통과.
- 리뷰: docs/reviews/0112-main-debug.md. 분석: docs/analysis/main-debug.md.
- 다음은ec4진단→ef2대기→f12입력을연결하고D3줄위치등필요문맥을확인하는것이다. 실제게임콜백본문,SR/RTE/BIOS·장치시간축/Z80및전체부팅은미완료이며목표는active다.


## 2026-10-07 — 진단 줄 위치에서 다음 입력으로 전달

- 포맷터와진단API에종료D3.word출력을추가했다. 종료줄바꿈이RAM에저장되지않는동작을반영하고CLI의D1/line을ef2 poll에전달했다.
- 실제진단5·IRQ10·poll14총29경계/469포트와오류6조건통과. Python73개및C++전체검사통과.
- 리뷰: docs/reviews/0113-debug-input-flow.md. 두번째프레임의컨트롤러최종D1/D3는원본에서얻은외부입력조건임을명시했다.
- 다음은컨트롤러종료의D1/D3문맥을복원하여연속메인루프의원본레지스터주입을줄이는것이다. 실제게임콜백본문,SR/RTE/BIOS·장치시간축/Z80및전체부팅은미완료이며목표는active다.


## 2026-10-07 — 컨트롤러 반환 뒤 D1/D3 복원

- consume_control_result에f5a이후32비트D1/D3입출력을추가했다. 상태byte·효과시작DIVS·복구전색읽기·팔레트혼합최종D3를반영했다.
- 원본322조건/27,858포트/오류14조건통과. Python73개/C++전체검사및추가롤백단위검사통과.
- 리뷰: docs/reviews/0114-control-caller-registers.md. 분석: docs/analysis/control-caller.md.
- 다음은9136컨트롤러본체의반환D1/D3를복원하여이번tail과연결하는것이다. 실제게임콜백본문,SR/RTE/BIOS·장치시간축/Z80및전체부팅은미완료이며목표는active다.


## 2026-10-07 — 요청·비활성 컨트롤러 D1 연결

- 요청 판정과 비활성 진입 API에 선택적 전체D1을 추가했다. 요청필터 후0에도 남는 byte변경과 pending/게이트 우회 시 보존을 반영했다. 원본D3는 불변이다.
- 원본3,141조건, 오류25조건, 활성화→f5a 연속5조건/포트1,305개 통과. Python73개 및 C++전체 검사 통과.
- 리뷰: docs/reviews/0115-control-activation-registers.md. 분석: docs/analysis/control-request.md.
- 다음은 활성대기91c2와 메뉴92fc의 반환D1/D3를 복원하고 step_control 및 호출자에 연결하는 것이다. 이번 변경은 비활성경로만 포함한다. 실제게임콜백본문, SR/RTE/BIOS·장치시간축/Z80 및 전체부팅은 미완료이며 목표는active다.


## 2026-10-07 — 메뉴 반환 꼬리의 전체 D1/D3

- finish_control_menu에 전체D1/D3반환을추가했다.9079의위치제어가D3상위word까지지우는동작과종료style을공유텍스트파서에서반영했다.
- 원본880조건/포트1,180개/오류63조건통과.3개40회연속꼬리호출은이전C++출력D1/D3를다음입력으로사용한다.Python73개및C++전체검사통과.
- 리뷰: docs/reviews/0116-control-finish-registers.md. 분석: docs/analysis/control-request.md.
- 다음은활성대기91c2·메뉴시작92ce·a370본체의전체레지스터반환이다.위치제어가D3상위를지우므로단순히기존line출력을상위word와합치면안된다.실제게임콜백본문,SR/RTE/BIOS·장치시간축/Z80및전체부팅은미완료이며목표는active다.


## 2026-10-07 — 활성 대기·메뉴 시작 D1/D3

- step_control_wait/start_control_menu에전체D1/D3전달을추가했다. selector변경,직접문구의위치제어,ca9e의D1초기화와메뉴제목측정의최종style을반영했다.
- 원본1,470조건/포트279,922개/오류36조건통과. 네개반복호출흐름은이전C++RAM/D1/D3를이어입력한다.Python73개및C++전체검사와추가메뉴초기화단위검사통과.
- 리뷰: docs/reviews/0117-control-wait-registers.md. 분석: docs/analysis/control-request.md.
- 다음은이미열린a370메뉴프레임의전체D1/D3반환을복원하고step_control→호출자에통합하는것이다.현재비활성/활성대기/메뉴시작/종료꼬리의개별API는전체값을반환하지만통합API의전체반환은아직미완료다.실제게임콜백본문,SR/RTE/BIOS·장치시간축/Z80및전체부팅도남아있으며목표는active다.


## 2026-10-07 — 메뉴 개폐·테두리의 D1/D3

- open_menu_step/close_menu_step과 테두리 출력에 전체 레지스터 반환을 추가했다. 닫기에서 지울 행 수가 D1.word에 남고 마지막 테두리 줄 증가가 D3에 남는 동작을 반영했다.
- 원본408조건/출력256,136개/오류34조건과 8개16단계 개폐 흐름 통과. 실제 가림39,416회도 확인했다. Python73개 및 C++ 전체 검사 통과.
- 리뷰: docs/reviews/0118-menu-motion-registers.md. 분석: docs/analysis/menu-motion.md.
- a370 통합을 위해 개폐 경로의 의존 기능을 복원한 단계다. 입력 판정은 a474에서 전체D1을0으로 만들고 활성P2입력byte를 읽는다. 다음은 입력 판정과 텍스트·콜백의 반환값을 연결하여 이미 열린 메뉴의 전체D1/D3를 완성하는 것이다. 전체 프레임·실제 게임 콜백·부팅은 아직 미완료이며 목표는active다.


## 2026-10-07 — 메뉴 입력·헤더·디버그 콜백의 레지스터 반환

- select_menu_input/update_menu_header에D1, dispatch_debug_menu에전체D1/D3입출력을추가했다. 입력의전체D1초기화, 헤더의selector변경, 디버그좌표계산의D1초기화와그리지않는이벤트의보존을구분했다.
- 원본3,988조건/포트2,952개/오류44조건과6개C++출력연속전달흐름통과. Python73개및C++전체검사통과.
- 리뷰: docs/reviews/0119-menu-input-debug-registers.md. menu-input.md/menu-debug.md/menu-frame.md에근거와경계를기록했다.
- 다음은stage group/area동적콜백및menu_text의전체D1/D3를완성하는것이다.9d3a는숨은행에서도D1.lowbyte를바꾸고,보이는행은D1전체를초기화한뒤9b3e에서항목argument word를읽는다.이를반영한뒤a370→step_control→호출자를통합해야한다.전체게임콜백/부팅/장치시간축은미완료이며목표는active다.

## 2026-10-07 — 포맷터·스테이지 그룹 콜백 전체 D1/D3
- 포맷터의 위치 제어에 따른 D3 상위 word 초기화와 최종 style/line을 연결했다. 스테이지 그룹 콜백은 이벤트별 전체 D1/D3를 반환한다. 오류 시 상태와 레지스터를 보존한다.
- C++11 API, MS5D를 읽는 새 CLI 및 기본 문법 구현을 유지한다.
- `.venv/bin/python tools/verify_formatted_registers.py`: 914조건, 포트 5,392개, 출력 보존 오류 검사 18조건 통과. 보고서 SHA256 `8ccc6d16fd27b94fc32b2717d14c47b5ab96bd57a335270b8b2026158608f673`.
- `.venv/bin/python tools/verify_stage_group_registers.py`: 1,208조건, 포트 12,588개, 출력 보존 오류 검사 31조건 통과. 보고서 SHA256 `062aff35044fe73111a4ef14a3224a939ec95d57d75dcfdb070a5aee22828d2b`.
- 전체 빌드/테스트 통과: Python 73개와 C++ 전체 검사. 메인 리뷰 `docs/reviews/0120-formatted-stage-group-registers.md`.
- 원본 문자열 줄바꿈 TRAP #15 경계는 정상 반환 검증에서 제외하고 C++ 오류 보존을 확인했다. 실제 예외 핸들러와 임의의 문자열 후속 메모리 실행은 미검증이다.
- 다음: 9602 구역 메뉴와 메뉴 텍스트의 전체 레지스터를 연결한 뒤 a370/제어기/메인 프레임으로 통합한다. 전체 목표는 미완료다.

## 2026-10-07 — 구역 메뉴·텍스트·이동 전체 레지스터
- 직접 9602 구역 콜백과 9d3a/9e1a 텍스트, a216/a280 이동의 전체 D1/D3 전달을 구현했다. 숨은 행의 D1 byte 변화, 보이는 행의 초기화/argument, 문자열 위치 제어 및 두 행의 순차 전달을 반영한다.
- 구역 초기 선택 event6의 재귀 이동·행 출력도 같은 경로로 연결했다. 실제 MS5D 런타임 리소스를 읽는 새 CLI와 기존 CLI의 선택적 레지스터 모드를 제공한다.
- `.venv/bin/python tools/verify_menu_text_registers.py`: 원본 1,946조건, 순서 있는 포트 18,922개 및 출력 보존 오류 검사 12조건 통과. 보고서 SHA256 `226ce366dd34fa448a6ef0ee0d1eae11a53bb38dee8d9c5d63bdacfb8cebf294`.
- `.venv/bin/python tools/verify_stage_area_registers.py`: 원본 3,936조건, 순서 있는 포트 504,536개 및 출력 보존 오류 검사 31조건 통과. 보고서 SHA256 `a4e1cadf1bedbf87c1ec457bc5de298332a036f8231f85fb9dc3b89c9866fc52`.
- Python 73개와 C++ 전체 검사 통과, 경고 없음. 메인 코드/원본/검증 리뷰 완료: `docs/reviews/0121-stage-area-menu-text-registers.md`.
- 다음: 상위 이벤트 디스패처와 스택 다시그리기/메뉴 열기에 레지스터를 전달한 뒤 a370과 제어기/메인 루프를 통합한다. 다른 CPU 상태·예외 핸들러·실제 타이밍과 전체 게임 복원은 계속 진행 중이다.

## 2026-10-07 — 메뉴 추가·스택 다시그리기 레지스터
- a0a0의 부모 출력 전후 D1 전체 복구와 D3 연속 전달, a6da의 슬롯별 테두리/텍스트 전달을 구현했다. 테두리 line 중복 계산을 제거했다.
- CLI에 선택적 레지스터 모드를 추가하고 입력 lowword 일치 및 오류 출력 보존을 검증했다. 실제 MS5D 런타임 리소스를 사용한다.
- `.venv/bin/python tools/verify_menu_stack_registers.py`: 원본 544조건, 포트 135,264개, 출력 보존 오류 검사 27조건 통과. 보고서 SHA256 `cf1f98e6c894477560cb2936cef2a557d50252e07f96670e60238d5bd6690705`.
- `.venv/bin/python tools/verify_menu_redraw_registers.py`: 원본 698조건, 포트 428,143개, 출력 보존 오류 검사 7조건 통과. 보고서 SHA256 `68711c1438609585d43f68612cb6300b3cba8c042a0e817d9ad1c05262de1159`.
- 전체 빌드·Python 73개·C++ 전체 검사 통과. 메인 리뷰: `docs/reviews/0122-menu-stack-redraw-registers.md`.
- 다음은 9b3e 상위 이벤트 디스패처에서 항목 argument와 콜백별 레지스터를 연결하고, a370/제어기/메인 루프로 이어 가는 작업이다. 전체 목표는 진행 중이다.

## 2026-10-07 — 상위 메뉴 이벤트·정적 재시작 전체 레지스터
- 9b3e 항목 argument와 모든 지원 콜백의 전체 D1/D3를 연결했다. 하위 메뉴 열기의 D1 초기화와 BIOS 외부 점프 경계를 반영한다.
- 2a28 정적 재시작에서 팔레트 해제 후 D3, 연결 좌표의 이전 absolute Y, 최종 D1=ffffffff를 복원했다. 오류 시 전체 후보 출력은 보존한다.
- `.venv/bin/python tools/verify_menu_event_registers.py`: 원본 5,551조건 및 오류 보존 28조건 통과. 보고서 SHA256 `5504bf49e774fc5e4bdf51cddc8fadc36471860d23495784550510bf86eeab81`.
- `.venv/bin/python tools/verify_restart_registers.py`: 원본 506조건 및 오류 보존 5조건 통과. 보고서 SHA256 `05862a1870c440e1ab16e914f038db0dcfce6f1b52c83201f1b8172e15ad4dad`.
- 전체 빌드·Python 73개·C++ 검사 통과. 메인 리뷰: `docs/reviews/0123-menu-event-restart-registers.md`.
- 다음은 a370 전체 메뉴 프레임의 분기와 호출 사이 레지스터 전달, 이후 제어기/메인 루프 통합이다. 전체 게임 복원 목표는 진행 중이다.

## 2026-10-07 — a370 전체 메뉴 프레임 레지스터
- 배경 닫기/다시그리기부터 텍스트·헤더·이벤트·입력·이동까지 전체 D1/D3를 전달한다. 높이0 닫기의 D3 하위 word와 빈 스택의 보존을 반영했다. 오류 시 기존 출력은 모두 보존한다.
- `.venv/bin/python tools/verify_menu_frame_registers.py`: 834프레임, 순서 있는 포트 155,889개 통과. 보고서 SHA256 `bb9f90db18860eb32323838f4934aafedc762967f639b6de294fc91246ca3a45`.
- `.venv/bin/python tools/verify_menu_frame_register_sequences.py`: 116프레임, 순서 있는 포트 9,584개 통과. 보고서 SHA256 `46a1403dee75aaad5b9824b22bb7d33b600b4427f592c61b6e9d895014ff0263`.
- 총 950프레임 중 414프레임은 초기화된 메뉴에서 실제 CLI RAM/전체 레지스터 반환을 연속 전달했다. 재시작·BIOS 경계·닫기 후 빈 프레임도 포함한다.
- 전체 빌드, Python 73개 및 C++ 전체 검사 통과. 메인 리뷰 `docs/reviews/0124-menu-frame-registers.md`.
- 다음은 step_control_menu/step_control/step_control_caller와 입력·메인 루프로 레지스터를 전달하는 통합이다. A1 진입 계약과 다른 CPU 상태·타이밍/픽셀/사운드의 미복원 범위는 유지하며 전체 목표는 진행 중이다.


## 2026-10-07 — 상위 제어기와 호출자 전체 레지스터
- 92fc 메뉴 제어기, 9136 분기 및 f54 호출자에 전체 D1/D3를 연결했다. 메뉴의 실제 반환 스타일로 종료를 처리하고, f5a의 byte 덮어쓰기·팔레트 효과/복구까지 전달한다.
- 선택적 CLI `--registers D1 D3`와 입력 lowword 일치/실패 트랜잭션 검사를 제공한다. 기존 기본 JSON은 유지한다.
- `.venv/bin/python tools/verify_control_registers.py`: 원본 1,207조건, 포트 208,678개 및 오류 보존 65조건 통과. 10개 시퀀스 445호출은 실제 CLI RAM/전체 레지스터 반환을 승계한다.
- 보고서 SHA256 `fd6a4249b3831c84cd6bd5da3e5006a7cda88a4a52c5dbff7d99f05a6b5b6431`. 전체 빌드·Python 73개·C++ 검사 통과. 메인 리뷰 `docs/reviews/0125-control-registers.md`.
- 다음은 입력 접두부/대기 게이트/메인 콜백과 debug 경로에 전체 레지스터를 연결하는 작업이다. fixture 입력·A1 계약 및 BIOS/TRAP/루프 외부 경계는 남아 있으며 전체 게임 복원 목표는 진행 중이다.


## 2026-10-07 — 입력·대기·메인 진단 출력 전체 레지스터
- 입력 접두부와 직접/ef2대기/f4c대기 경로에 전체 D1/D3를 연결했다. 입력의 D1 상위16비트와 D3 보존을 원본31d6/352a/b68에서 확인하고 제어기 최종 반환을 전달한다.
- 메인 debug의 전체 D3를 formatter와 연결했다. 기존 style/line 계약을 유지하며 선택적 CLI 레지스터 모드를 제공한다.
- `verify_input_control_registers.py`: 원본810조건, 포트81,005개, 오류 보존69조건 통과. 9개 시퀀스354호출은 실제 CLI RAM/D1/D3 반환을 승계한다. SHA256 `80703108ba7fb17e2be84f1dc583b3270db29e89f1c1a91ea2cfb29038a98174`.
- `verify_main_debug_registers.py`: 원본 debug806조건/포트62,382개/오류18조건 및 실제 debug→input/controller→ec4 승계8회 통과. SHA256 `c4ae8af3511d1392ea57bf397f7907fde2cc8e9787d3a1b6cc6082407ee16487`.
- 전체 빌드·Python73개·C++ 검사 통과. 메인 리뷰 `docs/reviews/0126-input-main-debug-registers.md`.
- 다음은 IRQ가 생성하는 프레임 신호와 callback/팔레트 경로를 포함한 메인 루프의 연속 실행 통합이다. 현재 호스트 신호 fixture와 선택한 경계만 검증했으며 다른 CPU 상태·물리 타이밍·전체 게임 복원은 진행 중이다.


## 2026-10-07 — 재개 가능한 메인 프레임과 IRQ·콜백 연결
- `MainFrameState`/`step_main_frame`을 추가했다. ec4 debug→ef2대기→입력·제어기 한 프레임을 실행하고 다음 PC와 전체 D1/D3를 반환한다. ef2 재개에서는 debug를 다시 실행하지 않으며 f4c 재개는 팔레트를 반복하지 않는다.
- CLI `--main PC DEBUG_MS5D VIDEO`를 추가하고 팔레트 CLI에도 전체 레지스터 모드를 연결했다. 실제 MS5D/MS5P를 사용하며 오류 시 RAM/state/result/포트는 모두 보존한다.
- `verify_main_frame_flow.py`: 원본54경계(main37/IRQ17), 포트746개, 오류14조건 통과. SHA256 `0a43c89908e4fcdb2b458fba4abadedc7173259c67f6933815ab59873fdfe3a1`.
- `verify_callback_register_flow.py`: 원본38경계, 오류12조건 통과. 기본 callback3dcc→stack복귀→팔레트→대기→IRQ→입력의 세 주기를 실제 CLI 출력으로 승계했다. SHA256 `14e37384f2944dfbacc751546e571098431ffda56d81fa9ca28522329c290074`.
- 전체 빌드·Python73개·C++ 전체 검사(새 main_frame_test 포함) 통과. 메인 리뷰 `docs/reviews/0127-main-frame-flow.md`.
- 실제 c8c 서비스가 신호를 생성하지만 IRQ 전후 main context 복원은 호스트가 수행한다. BIOS/SR/RTE/물리 타이밍과 D1/D3 외 scratch register는 미완료다. 다음은 기본 RTS 이외의 메인 콜백과 IRQ 작업 본문 분석·실행 연결이다. 전체 목표는 진행 중이다.


## 2026-10-07 — 메인 callback 후보 조사와 배경 좌표 준비
- fixed1MiB의 A6+76 참조1,101후보와 그 이후7MiB의 c64 등록 후보를 목록화했다. 후자는 절대 JSR/JMP0개, 원시값일치8개다. 데이터·다른 오브젝트 필드가 섞이므로 실제 callback/미사용기능으로 단정하지 않았다. 근거 `docs/analysis/main-callback-references.md`.
- 메인 e74에서 직접 호출하는1ae56/1879c를 복원했다. 네 배경 구조체의 좌표word/flag subtraction, cache변경과 dirtybit7, bank전환을 구현했다.
- `verify_column_prepare.py`: 준비1,482조건, 준비→기존화면갱신4조건, 포트1,312개와 오류29조건 통과. 실제 CLI RAM/full D0/D1/D3 승계도 검증했다. 보고서 SHA256 `1ee49b44a787cf2b279b99252ec8639b9183b2139b37450386bce9a8b38d6069`.
- 전체 빌드·Python73개·C++전체 통과. 메인 리뷰 `docs/reviews/0128-column-prepare-callback-inventory.md`.
- 다음은 메인 e74의 사운드 큐 비우기3c08, 일반 sprite 준비16bba, 배경 좌표 준비1ae56, 팔레트5728을 원본 순서로 잇는 작업이다. callback/IRQ 작업의 자연 실행 대상과 전체 게임 복원은 미완료다.


## 2026-10-07 — sprite 준비의 정렬 후 대기·재개
- `begin_sprite_queue`/`resume_sprite_queue`와 pending cursor를 추가했다. 원본16bba는 병합·정렬 후16bd0에서 소비자를 기다린다. 재개는 정렬을 반복하지 않고 현재 방향과 슬롯 경계를 읽는다. 기존 동기 API의 오류 시 출력 보존은 유지한다.
- CLI `--begin`/`--resume CURSOR`는 실제 MS5C 런타임 리소스를 사용한다. 대기 시에는 리소스가 없어도 RAM을 보존하고 빈 쓰기 목록을 반환한다.
- `verify_sprite_prepare_wait.py`: 원본1,297경계(begin329/wait640/release328), 실제 CLI 상태 승계328시퀀스, VRAM459,520개, 오류 보존27조건 통과. 보고서 SHA256 `fc59d6fc5b1e296a18f20e4195a67f0557bd793734119c425d2027ee1fd2c0d4`.
- 전체 빌드·Python73개·C++전체 검사 및 기존 동기 준비96조건→갱신96조건 통과. 메인 리뷰 `docs/reviews/0129-sprite-prepare-wait.md`.
- 다음은 emitter의 D1 상위word와 PVC 포트 전달, sound3c08 대기/재개를 포함한 e74→ec4 연결이다. sprite emitter의 SWAP이 D1 상위word를 바꾸므로 단순 보존/0 가정은 금한다. 실제 IRQ 소비·물리 시간·전체 게임 복원은 미완료이며 목표는 진행 중이다.


## 2026-10-07 — sprite 준비 전체 D1/D3와 PVC·VRAM 순서
- 스프라이트 begin/resume/동기 준비에 전체 D1/D3를 연결했다. 비어 있지 않은 radix의 반환값, emitter의 마지막 attribute 주소 상위word, 빈 큐/클리핑/disabled 보존을 반영한다.
- 실제 MS5C 사용을 유지하면서 레코드별 PVC 선택→VRAM 쓰기→마지막 PVC 복구를 선택적으로 출력한다. CLI `--registers D1 D3`/`--ports OUTPUT_PORTS`를 제공하며 실패 시 기존 출력을 보존한다.
- `verify_sprite_prepare_registers.py`: 원본1,873경계, 470승계시퀀스, 전체 포트688,064개(VRAM681,860개), 오류42조건 통과. 실제2/3/2블록 리소스도 포함한다. sprite 반환 RAM/D1/D3→scene좌표 준비4조건/포트16개도 통과했다.
- 보고서 SHA256 `5fc87b656fd8679312163060e7c58a0557511148f4081f7f0a574296ac77a04b`. 전체 빌드·Python73개·C++전체 검사 통과. 메인 리뷰 `docs/reviews/0130-sprite-prepare-registers.md`.
- 다음은 sound3c08 대기·재개 및 e74→ec4 순서 연결이다. 원본 D0/기타scratch/CCR, 자연 IRQ와 물리 시간·전체 게임 복원은 남아 있으며 전체 목표는 진행 중이다.


## 2026-10-07 — e74 메인 준비와 두 소비 대기 연결
- `prepare_main_frame`을 추가하고 상위`step_main_frame`에 연결했다. 초기 화면 명령→sound3c08→sprite16bba→scene1ae56→palette5728→영상delta를 실행한다. sound3aea/sprite16bd0 대기는 pending을 승계하며 앞선 작업을 반복하지 않는다.
- 실제 MS5P/MS5C를 사용하는 전용CLI와 JSON상태를 제공한다. 준비 완료는ec4이며 기존 main debug/gate/input과도 이어진다. 후속 실패는 앞선 준비의 변경까지 롤백한다.
- `verify_main_prelude.py`: 원본182경계, 포트58,136개, 영상읽기134회, 오류33조건 통과. 10승계시퀀스와 대기 중 word명령 추가6조건, 준비→기존main연결4조건(후속읽기12회)을 확인했다. SHA256 `9356a45524c67501dfdec3da7746796895fdf83df3922473a19f4f2256e6c6a5`.
- 전체 빌드·Python73개·C++전체 검사와 기존 main/IRQ54경계 회귀 검사 통과. 메인 리뷰 `docs/reviews/0131-main-prelude.md`.
- 다음은 실제 IRQ 소비 서비스의 sound head/sprite cursor 진행으로 새 준비 대기를 해제하는 통합이다. 현재 해제는 호스트fixture이며 e4a초기화/자연callback·task/BIOS·물리시간/전체게임 복원은 미완료다. 전체 목표는 진행 중이다.


## 2026-10-07 — 실제 IRQ 소비로 메인 준비 대기 해제
- 기존 준비/IRQ C++ API를 공유 RAM으로 연결했다. 초기 fixture 이후 sound head와 sprite read cursor를 호스트가 수정하지 않아도 IRQ 소비로 main이 재개된다. 실제 MS5P/MS5C와 두 팔레트 bank를 사용한다.
- `verify_main_prelude_irq.py`: 82시퀀스, main292경계 및 완료 IRQ187회, 순서 있는 포트124,884개 통과. 영상 읽기82회/sound status 읽기187회도 일치한다. IRQ timer16이 word명령19c0을 실제 추가하고 main이 소비하는2시퀀스를 포함한다.
- 보고서 SHA256 `6d930aea7824a4dc5ba7bebc5b1a451c903da8aadaaf9fe3584c5b83ca054ad4`. 전체 빌드·Python73개·C++전체 검사 통과. 메인 리뷰 `docs/reviews/0132-main-prelude-irq.md`.
- 다음 e4a 초기화의 고정 팔레트 등록17레코드와 직접 호출을 `docs/analysis/main-startup.md`에 분석했다. 구현은 아직 남아 있다. IRQ context 복원은 호스트가 수행하며 자연 task/callback·BIOS/SR/RTE·물리 시간과 전체 게임 복원 목표는 진행 중이다.


## 2026-10-07 — 메인 초기화와 난수 상태 복원
- e4a→e74 초기화를 C++로 연결했다. 고정 팔레트 해제·head 등록·slot6 blend·오브젝트/제어 상태 초기화를 수행하고 기존 준비 코드로 상태를 넘긴다. MS5D로17레코드를 보존하고 disabledffff는 제외하여 MS5P가29 ID로 확장됐다.
- `verify_main_startup.py`: 원본209조건/포트418개/오류32조건 통과. 다섯3호출 상태 승계 및 준비 연결2조건(추가24포트/영상2읽기)도 일치했다. SHA256 `2bf5387682dae840040749fb882917080a43ecedb22a1dd13766ca123cccea7a`.
- 난수 seed49a1a/next49a58/scale49a84를 복원했다. `verify_random_state.py`: 전체RAM/fullD0D1 1,690조건과 오류26조건 통과. 480호출 상태 승계와 고정limit의220호출/네wrap 포함. SHA256 `886e457b96b4ea5c9655c432d208eeca198e840a42c29a6a119d92d6c57308ff`.
- 전체 빌드·Python81개·C++전체 검사 통과. 메인 리뷰 `docs/reviews/0133-main-startup-random.md`. sol에 구현·검증·추출을 큰 단위로 분담하고 메인이 의미 해석·리뷰·통합을 수행했다.
- 다음은 초기 노드c52a/c560의 fill 대기를 IRQ와 연결하고c56e 이후 초기화 경로를 복원하는 작업이다. 자연 부팅·게임플레이 전체 연결은 미완료이며 목표는 진행 중이다.


## 2026-10-07 — 후속 초기화의 fill 대기와 IRQ 연결
- c52a/c560 콜백을 C++로 복원했다. 별도 MS5P fill 설정→반복 대기→공유 고정 팔레트 등록·난수 초기화로 이어지고c584의 미복원47570 호출 전에 반환한다. 기존 대기를 다시 호출해도 초기화·포트를 반복하지 않는다.
- `verify_game_startup.py`: 시작103경계와실제IRQ16회, 총포트16,716개 및오류32조건통과. 8시퀀스에서호스트counter수정없이실제IRQ출력만으로대기를해제했다. 전체D0상위word shift와RAM/D1/D3·양팔레트bank/display를비교했다.
- 보고서SHA256 `de8e6e4ca5ddd97c691e22d34e94c087fbfd950d635f62b203cd8cbd3c61a240`. 전체빌드·Python81개·C++전체통과. 메인리뷰 `docs/reviews/0134-game-startup-fill.md`.
- 47570의직접호출23개/22대상을목록화하고접두부와사운드명령0720/08/20의대기를다음구현대상으로확인했다. 자연부팅/전체callback·전투·스테이지·사운드실행은미완료이며전체목표는진행중이다.
