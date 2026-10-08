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


## 2026-10-07 — 게임 초기화 사운드 접두부와9개 리셋 함수
- 47570→475a4 접두부를복원했다. word0720과byte08/20의모든3aea대기를구분해재개하고초기화·external읽기를반복하지않는다. 전체D0D1D3와pending을CLI/C++에유지한다.
- `verify_game_prelude.py`:171경계, 조건부읽기16회, 오류47조건통과.12시퀀스의실제IRQ37회/포트68개로head수정없이재개했다. 기존startup CLI→원본c584 JSR→접두부연결2조건도통과했다. SHA256 `24e42600a631bc346165547a417fe3aa9c8dab9f2bc039697c952525c918af05`.
- 후속초기화의리셋함수9개를묶어구현했다. `verify_game_reset.py`:288조건/오류17조건통과,16승계시퀀스포함. SHA256 `3188b37509467d265d390a56e74720662b928a890fe0904219cf19d3277f30d3`.
- 전체빌드·Python81개·C++전체통과. 메인리뷰 `docs/reviews/0135-game-prelude-resets.md`. 다음은475a4 suffix의오브젝트·레코드처리및리셋함수순서연결이다. 자연부팅과전체게임복원은미완료이며목표는진행중이다.


## 2026-10-07 — 전체47570 초기화와 네이티브 리소스 연결
- 475a4 suffix의 오브젝트1bcfe/1bd12, 레코드481de/4d81c와 기존 리셋 함수를 원본 순서로 연결했다. `initialize_game`은 사운드 대기를 승계하고47570의RTS까지 실행한다. returned와 마지막 내부PC를 구분하며 후속 실패는 접두부 변경까지 롤백한다.
- 20×16byte 레코드 전체를MS5D로 추출하고 C++에서 읽는다. selector의zero/nonzero와parity 선택 차이, live pointer, 정수폭과 fallthrough를 보존했다. PNG/오디오 진단 출력에 의존하지 않는다.
- 원본 비교: 오브젝트149조건/오류24, 레코드168조건/오류32, 전체초기화562조건/오류31 통과. 전체 RAM과 계약된 레지스터 및 pending을 비교했다. 전체초기화 보고서SHA256 `ba538ea67e01041c8b199c889d8f2a225f18b203bf55e6a281da5464af12a3b2`. 실제CLI JSON 상태 승계로 재검증했고 결과가 같다.
- 전체빌드·Python88개·C++전체 통과. 메인리뷰 `docs/reviews/0136-game-initialization.md`, 상세 `docs/analysis/game-initialization.md`. whole-function 대기 해제4시퀀스는 호스트sound head 수정이며 IRQ/스케줄러 동등성으로 확대하지 않는다.
- 다음c58a 경로94명령후보/22직접호출/23분기·JMP를 목록화하고 메인이 분기/콜백 fallthrough를 분석했다. `docs/analysis/game-continuation.md`. BIOS c00444 경계와 하위호출4fb1a/28ae/c4cc/caf0 연결이 다음 대상이다. 자연부팅·전투·모든스테이지와 전체게임 복원은 미완료이며 목표는 진행 중이다.


## 2026-10-07 — 동적 오브젝트 할당과 실제 풀 연결
- 28ae의 free-list 할당과4fb1a 조건부요청을C++로복원했다. unsigned reserve threshold,전체callback0검사,depth word wrap,live링크/상속byte순서와carry를유지한다. 정상실패와잘못된포인터API오류를구분한다.
- `verify_object_allocation.py`: 원본439조건과오류50조건통과. 실제CLI승계3시퀀스중하나는원본2790과MS5I초기화RAM을비교하고freepool80→79→78을확인했다. MMIO쓰기0,원본ROM불변. 보고서SHA256 `9e6e6ad033a3683950fec1eeb40bdc66526b1b31f1c250e83b015c1c7e3abf6c`.
- 전체빌드·Python88개·C++전체통과. 메인리뷰 `docs/reviews/0137-object-allocation.md`. 실제callback4fb64 실행과자연스케줄러는아직범위밖이다.
- 제거경로5개진입59명령후보/22제어참조를목록화하고메인이정적분석했다. `docs/analysis/object-removal.md`. 자식이남은비활성노드의지연제거와연쇄회수를다음구현에서원본검증해야한다. BIOS전환과전체게임복원목표는계속진행중이다.


## 2026-10-07 — 지연 제거·연쇄 회수와 화면 초기화
- 299c/2a0a/2a84/c4cc를복원했다. 자식이남으면inactive노드를유지하고마지막자식제거후이전inactive노드를연쇄회수한다. palette/coordinate정리와live순회,전체D0D1D3/A6 및watchdog순서를연결했다. 팔레트해제optionalD1을추가했다.
- 제거원본343조건/오류50조건,watchdog382개통과. 메인리뷰로reset전반환값이노출되는deferred150조건을추가했다. SHA256 `4422458b5cfcf56ddb232cc46c1a5f21b2a92df94f16c0eb7b49d01f33fcca3f`. 기존staticrestart506조건/오류5조건회귀도통과했다.
- ca9e/caf0화면초기화는104조건/오류23조건,147940순서있는포트를비교했다. SHA256 `328476653aa7648ceb08c18ea78a72b77425e09dc2591ef520c38d46e9a0227a`. 실제5회35a2호출을포함하며픽셀렌더링완료를주장하지않는다.
- 전체빌드·Python88개·C++전체통과. 메인리뷰 `docs/reviews/0138-object-removal-screen.md`. 다음은실제c610호출자에서난수→제거→화면→47570대기/재개→stage/input초기화를연결하는작업이다. 자연부팅/전체게임플레이목표는계속진행중이다.


## 2026-10-07 — c610 실제 호출자와 초기화 대기·재개 연결
- 난수→오브젝트제거→화면초기화→47570→stage/input선택을하나의재개가능C++API로연결했다. 대기시앞선단계를반복하지않고완료시A6.callback=c654를설정한다. 실제MS5D게임레코드와입력stream을사용하며늦은오류도전체transaction으로보존한다.
- 최종원본144경계/오류38조건,166360포트/외부읽기56회통과. 실제controller1008e4의32승계시퀀스,네사운드대기분류및LIVEf02a선택을확인했다. SHA256 `eff31a72a6ac06645d6cb99f52b78a9103a10ff2a51810043073c468302fdd30`. head해제는명시적hostfixture이며자연IRQ동등성은미검증이다.
- 전체빌드·Python88개·C++전체통과. 메인리뷰 `docs/reviews/0139-game-restart.md`, 상세 `docs/analysis/game-restart.md`. 원본wordwait조건과실제A6범위를리뷰에서보완했다.
- 다음c654/c66a및477e4콜백후보144명령/21호출을목록화하고메인이활성/replay판정을정적분석했다. callback본문과자연scheduler,전체스테이지게임플레이는미완료이며목표는계속진행중이다.


## 2026-10-07 — c654 ready gate와 후속 준비 경계
- c654/c66a/c686/c6c0을 재개 가능한 진입 경계로 복원했다. 고정100b30의 정적 restart→활성/replay gate, 오브젝트 제거→화면 reset→동적 할당 및 현재 callback/flag 설정을 원본 순서로 연결했다. 종료는 실제c724/c73e/BIOS c00444 경계이며 body나 가상RTS를 실행하지 않는다. ROM180.word=0만 지원하고 ROM 변경 경로는 제외한다.
- `verify_game_ready.py`: 원본246조건/오류39조건, 순서 있는 포트274484개 및4승계시퀀스를 통과했다. 전체 RAM/D0/D1/D3/A6가 일치하며 실제 restart CLI→원본c610 반환→c654 연결은 두caller에서 확인했다. 재진입의+62 flag 변경은 명시적hostfixture다. 보고서 SHA256 `4f09a7ef5db74efe5b5ab29bf8a4646cf9cb49145dc5c05a2508e0dcffc1fe17`.
- 전체 `make -j3 all test` 통과: Python88검사·C++86 test executable, 경고·오류0. 로그 `artifacts/game_ready_build_test.log`. 상세 `docs/analysis/game-ready.md`, 메인리뷰 `docs/reviews/0140-game-ready.md`.
- stage startup을5개 명시진입/111명령후보/23직접호출/17helper후보 및14 API family 후보로 목록화했다. `artifacts/stage_startup/report.json` SHA256 `6664908c593cd78cb6b8b8763b6df4e4541d093b84eae917e81a08c769330928`. Capstone5.0.6의 bounded 디코딩이며 원본 실행은 관측하지 않았다. 후보분류·기존API 참조를 의미확정이나 동등성 근거로 취급하지 않는다.
- 다음은477e4가 호출하는1a5a4의 복잡한 초기화와 후속 stage 연결 분석이다. 이번에 callbacks477e4/e66aa는 설치만 확인하고 실행하지 않았으며 BIOS c00444도 경계에서 멈췄다. 자연scheduler·전체스테이지게임플레이와 전체복원 목표는 계속 진행 중이다.


## 2026-10-07 — stage 원본 관측과 scene-node 기반 함수

- `inventory_stage_startup.py`가 일곱 전체 지정 창의248개 명령 후보/undecoded word를 추가하고17292의 prefix·22c0×2048·RTS를 assert한다. first-RTS 목록과 구분하며1b128..1b160은 데이터 가능성이 있는 미확정 구간이다. 보고서 SHA256 `3ce6dd670d4cf77310bc08135a6986133e2db51907f6ddd41606806b15a0fe19`.
- 원본1a5a4 probe는 입력 A0=0/D0=0의16개 조건 모두 RTS에 도달했다. flag0은4 PVC, f000 bits8/16/24는4 PVC+1280 VRAM 쓰기였고 외부 read0/D0=0/D1=D3=01000000이다. 보고서 SHA256 `18c241850f4c7e0adf715963cbe3bb98f653590cacb97e12715e9afd458c4e05`. 이는 제한된 원본 관측이며 일반 script/실제 PVC 전환이나 C++1a5a4 동등성 검사가 아니다. 짧은 hook 바이트 디코딩 오류는24바이트 창과 canonical raw 검증으로 수정한 최종 결과만 수용했다.
- `scene_node`는43dda/16fac 초기화,43e22/16fee parent 설정,43e38/43ea8/1728c 갱신,1724c/1726c 정수 폭·잔여 carry 계산과17292의8192바이트 clear를 연결했다. 전체 RAM/D0/D1/D3/A0/A1 transaction을 보장하며 다른 레지스터/CCR는 계약 밖이다.
- 독립 원본 비교1904조건·오류94조건·8승계시퀀스가 통과했다. 승계의48호출은1904조건에 포함되며 실제 CLI RAM/레지스터 출력을 운반한다. set의 parent/위치는 명시적hostfixture다. MMIO0, 원본코드변경0. 보고서 SHA256 `c900dfc01d94c31633856b8ffae34478ce9ad281366b9322e23ccebd85a0c1c6`.
- 전체 `make -j3 all test` exit0: Python88검사·C++87 test executable, warning/error0. 로그 `artifacts/scene_node_build_test.log`, 메인 리뷰 `docs/reviews/0141-scene-node.md`, 상세 `docs/analysis/scene-node.md`와 `docs/analysis/stage-startup.md`.
- 다음은1a5a4 전체 호출자와 리소스 연결이다.1afda debug 표시의1280회 VRAM 쓰기와1af12/1afd2 표의 실제MS5D 계약을 생략하지 않는다. 일반 nonzero script, 전체477e4/scheduler·스테이지게임플레이와 전체복원은 미완료이며 목표는 계속 진행 중이다.


## 2026-10-07 — null-script 장면 초기화와 원본 debug 표시

- 원본1afda debug 갱신과477e4의 D0=0/A0=0 준비→1a5a4→477ee 경계를 C++로 연결했다. 첫 노드를 반복 읽는 원본 history 판정, sticky SUBX Z, word high 보존, descending1280 VRAM 쓰기와 네 PVC 쓰기를 유지한다. 메인 리뷰에서 scale의 BTST.B/BNE 조건 방향을 수정하고 네 노드의 X/Y helper 호출을 실제 순서로 보존했다.
- `[1af12,1b112)`의512바이트를 기존 MS5D v1 kind1 리소스로 보존하고 C++ fixed-data loader로 소비한다. byte index 전체의 addressable window이며 논리 table extent로 단정하지 않는다. flag/code 겹침도 보존한다. container SHA256 `ca28489b53c66df310f32a2afca6312f56714f2e5af3fb65a2da17e3c2c4581f`.
- `verify_scene_initialization.py`: 원본576조건(debug524/initializer52), 오류 보존24조건, 순서 있는 포트672744개 및 실제 CLI 승계7시퀀스 통과. 전체 RAM/D0/D1/D3가 일치했고256 index×4 upper flag의1024조합을 실제 lookup에서 관측했다. MMIO read0·원본 코드 변경0이며 시작/종료 binary hash가 동일하다. 보고서 SHA256 `451015b835b3a4e741bddf61b43e21cf5c8d72d1d4dc30ff4c4c5107f7554bb4`.
- 전체 `make -j3 all test` exit0: Python95검사·C++88 test executable, warning/error0. 로그 `artifacts/scene_initialization_build_test.log`, 메인 리뷰 `docs/reviews/0142-scene-initialization.md`, 상세 `docs/analysis/scene-initialization.md`. 이전 원본1a5a4 probe16조건과 이번 C++ 동등성576조건을 구분한다.
- 다음은477ee stage catalog 연결과3d58의 two-byte queue 대기/재개다.4814e의d68c.word=1,3d58의0a 전송→원래D0.byte 복구·ADD.B20/SCS.B/OR.W→두 번째3ac8 호출을 메인이 확인했으며 wrapper 구현은 아직 남아 있다. 일반 nonzero script·전체477e4·자연 scheduler/물리 timing·전체 스테이지 게임플레이와 복원 목표는 계속 진행 중이다.

## 2026-10-07 — 스테이지 진입과 두 바이트 사운드 연결
- sound pair3d58/3d64를 C++11로 복원했다. carry 입력의 suffixff와 두 대기의 캡처된 queue 상태를 보존한다. 원본2180/오류67조건,40승계시퀀스 통과. 이 중8시퀀스는 실제c8c IRQ28회로 해제했다.
- stage entry477e4/477ee부터 catalog 선택·flag 갱신·sound 대기/재개·ca9e 화면 초기화·LIVE 레코드 재조회 및 여섯 분기 목적지까지 연결했다. 분기 본문은 아직 실행하지 않는다.
- 원본19그룹59레코드를 모두 검증했다. 7빈그룹의 원본 반복은 API bounded 오류로 구분한다. canonical selector는0/4/c/14이고8/10은 독립 분기 매핑 검증이다.
- stage 원본526/오류81조건,401942 ordered ports,8실제CLI 승계 통과. 이 stage 승계의 queue 해제는 host 입력이다. 보고서 artifacts/stage_initialization/verification.json, SHA256 6ba246a33c26b91b841443ed3f26a023eb5abd150dd4f16e2b7626d775bd31fa.
- 전체 make -j3 all test: Python95/C++90 통과, 경고0. 문서 docs/analysis/sound-pair.md 및 stage-entry.md, 메인 리뷰 docs/reviews/0143-stage-entry.md.
- 다음 구간478c4..47b00 목록화 완료:134행/35직접호출/23대상. 마지막 잘린 명령은 미완료로 보존했다. 다음은 팔레트 효과·대기 callback·오브젝트 할당 분기와 이후 스테이지 본문 연결이다.
- 전체 리소스/게임플레이 복원 목표는 진행 중이다. 전체 진행률25~30%는 범위 기반 추정이며 측정된 코드 커버리지가 아니다.

## 2026-10-07 — 스테이지 전환 분기 검증
- C++11 stage_transition은 여섯 dispatch와 세 callback을 연결한다. 팔레트 DIVS의 전체 반환값, timer underflow, allocation 실패 fallback 및 LIVE child 좌표 복사 순서를 보존한다.
- 480bc/479b0 본문 직전 또는478de busy-loop 한 회 관찰 뒤 반환한다. 자연 scheduler와 전체 stage body는 미완료다.
- 전체 make -j3 all test: Python95/C++91 통과, 경고0. 독립 원본1249/오류49조건,618179포트,실제CLI 승계6시퀀스 통과. callback 호출과 flag 변경은 host fixture다. 보고서 artifacts/stage_transition/verification.json SHA256 fa20a6699046a1429b21094909462a5f7cd9be89688f6016ae195ff7756f97d3.
- 다음 본문 호출18대상/582행 목록화와 API 재사용 후보를 artifacts/stage_body에 보존했다. code/data 경계 및 실행 도달 여부는 자동 목록으로 확정하지 않는다.
- 다음 분석은 e7c36 추가 팔레트 등록e7bda(26bytes),477c2의 제거/팔레트/사운드 연결 및479b0 본문이다. docs/reviews/0144-stage-transition.md에 메인 해석을 기록했다.

## 2026-10-07 — 스테이지 팔레트·오브젝트 준비 연결
- e7bda의4등록 레코드를 기존MS5D v1로 추출했다.26payload/58container, stage_palettes.ms5d SHA256 de398dc6e5c917c83709a325dd72b557faa0b94a66b3a5d71b5c955fd7f3fdc6. 실제색4IDs도MS5P에추가해33IDs/2276bytes다.
- e7c36은 기존main팔레트 초기화 뒤 새테이블을 실제소비한다.477c2는 자손과고정100bf4제거,팔레트gate와사운드callback초기화를 원본순서로 연결했다.479b0 준비API는두호출후479ba직전에멈춘다.
- 원본101/오류37조건/441orderedports/2CLI승계 통과. 신규4슬롯의원본등록→색변환→전송도MS5P와일치했다. 보고서 artifacts/stage_preparation/verification.json SHA256 226820728af213cb3fc73808809723e951d4e8a00dbd39d644793f69d08a17ab.
- shared등록loop 변경후 기존main회귀209/32조건 및준비연결2조건통과. 전체make104Python/92C++통과/경고0. runtime-resources에두등록테이블packer추가.
- 기존palette resource검증에서ffff 비활성등록을실제색ID로조회하던오류수정. 활성34bindings변환검증과비활성4개제외목록을분리했다.
- 메인리뷰 docs/reviews/0145-stage-preparation.md,규격·명령·한계 docs/analysis/stage-preparation.md. 다음은479ba이후플레이어설정/레코드복구및일반scene script로확장한다. 476dc/47742와pointertable의초기근거를리뷰에남겼고아직동작완료가아니다.

## 2026-10-07 — 스테이지 플레이어 선택·재시작 연결
- 47742의 signed선택값 제거/정적재시작/1bd2e초기화/49a58난수선택을 기존 C++ 기능으로연결했다. callback0도활성이며D1을stack에서D0로복원하는정수폭을보존한다.
- 476dc의두gate와stage/area선택을 MS5D stage_players.ms5d에연결했다.1040바이트주소가능창이며선두5pairs/3pointers/원본code겹침을구분한다. container1072bytes SHA2569248616256431f9e81b27ab938bf2d6cc8e108006b7f032929babfa8c1c604e9.
- 479ba caller를479d0직전까지연결해앞선stage preparation 출력에서실제로이어간다. d681쓰기후LIVE area조회및조건부API검증을보존한다.
- 원본1899/오류42조건/380ports/6CLI RNG승계/2prep→caller연결통과. 최종보고서 artifacts/stage_players/verification.json SHA2567d82d2427746eff1edea0e1f3659807d1f84db2e6a6327210dae4ef4e7235e77. 모든stage256및area256×3읽기검증은helpers gated; 선두조합80/overlap160실행을자연사용증거와구분했다.
- 전체make111Python/93C++/경고0,기존game_objects원본회귀149/오류24통과. 메인review0146,분석docs/analysis/stage-players.md.
- 다음은479d0의area0/비영분기,48180레코드복구와475ca설정,이후scene script연결이다. 플레이어callback전체게임플레이·자연scheduler는미완료다.

## 2026-10-07 — 플레이어 상태 기록과 구역 재개
- 4d7a6의byte selector·활성조건·레지스터폭과48180의8-byte RAM snapshot을복원했다. 현재상태저장이며복원이아니다. leaf는D0..D6전체를검증한다.
- player_record_lookup.ms5d는4cf64..4df60의4092바이트원시주소창이다. 기존20records/320bytes규격은그대로고prefix일치. container4124bytes SHA256 aad55489c3ee994e32b0ca8301e97d546746d5735cea2f5181ec9f71d136ac45.
- 475ca공통tail을기존초기화에서분리하고479ee..479fe의두snapshot→tail을연결했다. 원본3372leaf+50area조건/49오류조건/MMIO0/8CLI승계/2실제playercaller→원본분기연결통과. report artifacts/player_record_capture/verification.json SHA256 3be3c5e82d570c78096f49cdff1f34e6947a858efaf832a41af1c0c600cf97cd.
- 전체make118Python/94C++/경고0. 기존game initialization 회귀562/오류31통과. 메인review0147,분석docs/analysis/player-record-capture.md.
- 첫구역47594사운드대기경로와4e666, 479fe이후d760a/49c32및scene script 연결은다음범위다. 전체stage/gameplay와자연scheduler는미완료다.

## 2026-10-07 — 첫 구역 사운드 직접 진입

- GamePreludeState phase0의47594 진입을 지원한다.47570 앞부분의 RAM 초기화를 건너뛰고 MOVE.W0720부터 실행하며 D0 상위16비트를 모든 사운드 대기와475a4 완료까지 보존한다. 기존 initialize_game을 통해 전체 suffix와47640 RTS도 연결했다.
- 원본 비교는 prelude235조건(신규64)/오류50, initialization650조건(신규88)/오류33을 통과했다. 각 신규 CLI 승계16개에서 word high/low·byte08/20 대기, 재개 외부 읽기0과 A7 위치를 확인했다. 신규 승계의 큐 해제는 명시적인 host 입력이다.
- 보고서 SHA256: prelude `7432265d5ecaabe8603866d176133cfe32a2f58b96aa49580971795e29e68896`, initialization `9610a86247038cb92cf810dde218aa9764dacfe79950e5aa5f7e191f2b8fe876`. 전체make Python118/C++94/경고0. 메인 리뷰 `docs/reviews/0148-first-area-sound.md`.
- 후속 본문 호출21개/15대상과16개 명시 창을558행으로 목록화했다. 원시 selector lookup128바이트는 논리 테이블 크기나 동작 검증으로 주장하지 않는다. 상세 `docs/analysis/stage-area-body.md`.
- 다음은479d0 양쪽 분기를 같은 진입으로 연결하고4e666, d760a/49c32와 후속 일반 scene script를 복원하는 것이다. 전체 게임플레이·자연scheduler 및 전체 목표는 계속 미완료다.

## 2026-10-07 — 구역 진입 양분기와 후속 할당 통합

- stage_area_initialization으로479d0부터47a1c까지 연결했다. 첫 구역47594 초기화/사운드 대기와 다른 구역의 두 snapshot/475ca를 구분하며, 재개 시 분기를 반복하지 않는다. 이후LIVE d684 gate,4e666 selector 정리,d760a 할당,두49c32 저장을 원본 순서로 실행한다.
- 원시 selector lookup128바이트를 기존MS5D128payload/160container로 보존하고 C++에서 소비한다. Container SHA256 `59541b176a2819fd0f7aefbaa481d309c9e06e1fb4b722df52fe28e3285d6046`. 논리 테이블 전체 크기나 standalone signed-index 범위를 주장하지 않는다.
- 원본453조건/오류47조건/실제CLI승계16개/이전player caller 연결2개를 통과했다. 네 사운드 대기,128 lookup주소,대기중LIVE gate 변경과분기유지,할당실패/alias쓰기순서를 확인했다. MMIO쓰기0,ROM·binary불변. 보고서 SHA256 `76e22c1c64acba38eecb095c5d2e989b17079dd58be3685a4e5d0bf6b4712778`.
- 전체make Python125/C++95/경고0. 상세 `docs/analysis/stage-area-initialization.md`,메인리뷰 `docs/reviews/0149-stage-area-initialization.md`.
- 후속 장면 포인터42개(59레코드,41비영/4개레코드의null)를 목록화했다.41개 스크립트의855구문행이 종료점까지 읽혔고9개inline block은원시보존했다. 구문보고서 SHA256 `21b526531039763241fb8a01bc240df657ce0a357e240d21fab50ec8a42dd1a6`;실행검증은아니다.
- 다음은47a1c 이후 사운드 선택/대기 묶음과47a94 일반 scene interpreter다. 설치한d764a callback 실행·자연scheduler·전체게임플레이를 포함한 전체 목표는 미완료다.

## 2026-10-07 — 스테이지 사운드 설정 연결

- 공유sound_word 큐에원본D0/D1 결과와conditional read count를 추가하고47a1c..47a94의선택명령→1890/91/92→08/20을 연결했다. 대기 중record를다시읽지않으며새명령의외부읽기는구분한다. 기존StageCatalog MS5D를직접소비한다.
- Primitive2525/오류34와기존큐회귀2241/25통과. Caller556/오류50,59canonical레코드/12대기하위단계/CLI승계8/앞선구역출력연결2통과. Caller보고서SHA256 `74d5eda9bdc667ff3590807b5ef1dd8e63a389abddec62a34b205335f9aa2b80`.
- 전체make Python125/C++97/경고0. 공유코어prelude235/50회귀도통과했으며최신SHA256 `f9f3a9cc50175db1ca4c5c5111b7f954dafb8abb17eb811e0a52bcc13fabbe5e`. 메인리뷰0150과stage-sound-initialization.md에범위/한계를기록했다.
- sol 두 작업이workspace credits오류로종료되어메인이남은보고서확인·회귀·문서를완료했다. 다음은47a94 일반scene script와후속엔진연결이다. 자연scheduler/IRQ/오디오시간축·전체게임플레이를포함한전체목표는미완료다.

## 2026-10-07 — 장면 스크립트 리소스의 실제 C++ 소비

- stage record59개가참조하는비영script41개를기존MS5D로추출했다. 합계5486payload bytes,814일반명령+41terminator,9opaque inline block을보존한다. Null과외부map/path참조를별도구분하며이미지/오디오변환물은사용하지않는다.
- C++ SceneScript loader/decoder와inspect_scene_script CLI를추가했다. 명령주소/opcode/operand/inline/다음주소및원본bytes를보존하며종료뒤추가bytes와지원밖구문은오류로처리한다. 실제interpreter handler실행은아직아니다.
- 실제41개파일의C++출력을재조합해원본전체bytes와대조했고814개원본dispatch에서목적주소/A1/D7를확인했다. Handler실행직전정지이며효과동등성검증은아니다. 부정CLI10조건통과. 보고서SHA256 `624fdd85a3d34445a37421e5df4413b0a70d84dd94f027a90715ff6f907ec560`.
- 전체make Python131/C++98/경고0. 메인리뷰0151,분석scene-script-resources.md,빌드로그artifacts/scene_script_resources_build_test.log. 이번sol 재시도는실행되었다. 다음은handler와외부map/path리소스및일반scene초기화실행연결이며전체목표는계속미완료다.


## 2026-10-07 — 장면 명령의 RAM·레지스터·영상 쓰기 연결

- 추출한41개 MS5D script를 직접 사용하는 scene_command API/CLI에15종 handler를 연결했다. 고정 node table1a08e의16바이트도 같은 MS5D 규격으로 보존했다. A1 명령 경계는 raw source 재디코딩으로 검사하며 미지원5종은 오류로 처리한다.
- 원본 실행 비교에서 발견한1c의 watchdog/64 VRAM long 쓰기와14의 scratch register 결과를 수정했다. 최종 API는 D0..D7/A0/A1을 승계하며 WORD·BYTE 보존폭과32비트 wrap, 노드 history/global stamp alias 순서를 반영한다.
- 원본3385조건/부정65조건/18720순서 있는 ports/118지원명령 CLI승계 run 통과. Canonical814명령 중 지원586회(14종), 미지원228회(5종)다.15번째4c는 canonical occurrence가 없어 합성 unit 범위로 명시한다. 보고서 SHA256 `ea129b9adc8158c195cd1bd92ee4488d24aae78ca87e6327a3a0dad5ffe9e65d`.
- 전체빌드 Python131/C++99/경고0. 메인리뷰0152와분석scene-command.md에검증·제약을기록했다. 이전 사용자 상태응답은 소스 변경 없는 상태 확인이었으며 이번에는 실제 누락수정·확장검증을 완료했다.
- 미지원00/04/08/10/24는각39/75/41/1/72회다. 다음은 외부map/path/palette 의존성 및1a26a phase loop를 연결하는 작업이다. 현재도 직접 조작 가능한 스테이지 화면, 자연scheduler와전체게임플레이는미완료이며 전체목표는계속진행중이다.


## 2026-10-07 — 장면 이동 초기화와 경로 리소스 연결

- 장면명령00/10/24를추가해18종을지원한다. 기존MS5D로37 motion span·간접word1·path-node table1(총1248payloadbytes)을보존하고C++에서직접소비한다. A2를포함한11레지스터를승계하며00의좌표WORD변경과43e22 초기화/종결시간조회,10의간접pointer fallback,24의경로pointer저장을원본순서대로연결했다.
- 메인리뷰에서packer의time/type field혼동을발견해offset2 type검사로수정했다. 회귀3개를추가했으며실제firsttype은14/64/80이다. 후속운동명령의의미해석완료를주장하지않는다.
- 원본3945조건/오류83조건/18720orderedports/79 CLI승계run 통과. 지원698 canonical명령,미지원116명령(04:75,08:41),4c는합성unit만이다. 추가dependency오류13조건은임시파일로검사했으며원본리소스와고정ROM은보존했다. 최종보고서 SHA256 `a69e2b5b136e4db0c14245b7602c36ec0ccd03b5868ed864b894eb5b3cc0f6fb`.
- 전체빌드 Python134/C++99/경고0. 메인리뷰0153 및scene-command-dependencies.md에재생성/CLI/검증범위를기록했다. 다음은04의bank/palette 등록과08의map 초기화,이후1a26a phase loop 연결이다. 전체목표와직접실행가능한스테이지화면은미완료다.


## 2026-10-07 — 장면 팔레트 명령과 뱅크 데이터 로더

- opcode04를기존palette binding공통코어에연결했다. RAMbank shadow→PVC선택쓰기→root/lookup→등록순서를보존하고12레지스터(D0..D7/A0/A1/A2/A4)를승계한다. 지원19종,canonical773회이며미지원08은41회다.4c는canonical에없어합성unit범위다.
- MS5D v1kind2 bankedwindow와별도bankedloader를추가했다. kind1고정첫1MiB제약은유지한다. Palette root1/lookup72/binding72의145리소스7228payloadbytes를추출했으며CPU/ROM/bank주소및PVCoverlay경계를명시한다. 전체dependencies184개8476payloadbytes,manifest SHA256 `c9df39f855b267c0b547e2392be4a334a4e698ea48d6a1593e571e72018b4dc1`.
- 원본4330조건/오류99조건/19875ports/길이2이상carry42구간781호출통과. Palette상태는원본3ef2로준비하며전체자연부팅으로간주하지않는다. 최종보고서 SHA256 `308312679576dba7914c1bf16662b0443fb6136ce415346d789f700e327e4b51`.
- 공유코어mainstartup209/32회귀는기존SHA와동일하며stageprep101/37회귀도통과했다. 전체make Python137/C++99/경고0. 메인리뷰0154,분석scene-palette-command.md,공통resource-format.md에규격·한계·검증을기록했다.
- 다음은08의43ffc 맵/스프라이트초기화와외부데이터연결,이후1a26a실행루프다. 팔레트등록을색상전송·전체스테이지화면완료로취급하지않으며전체목표는계속미완료다.


## 2026-10-07 — 장면 표시 초기화 명령 연결

- 마지막opcode08을scene_setup API에연결했다. Sprite queue와네node초기화,bank3MiB/2MiB선택,380slot영상clear,상한prefix/하한suffix역순할당,잔여sprite pool설정을원본순서로재구성했다. MOVEM.W sign-extension과역순loop D7상위word,마지막A0를보존한다. 기존sprite RAM API는재사용하고수정하지않았다.
- Canonical41참조의15고유descriptor524bytes를기존MS5Dkind1으로추출했다. 전체dependencies199개9000bytes이다. Type3 terminalword는주소전진에쓰이지않아odd/negative값도보존하도록초기검사제약을수정했다. 비정상record/원본TRAP조건은transactional API오류로구분한다.
- 독립원본관찰164조건/1372384MMIO를보존했고,통합C++원본비교4535조건/오류104조건/1737175ports가통과했다. 전체814canonical명령이포함되며43carry구간824호출을검사했다.08 subset205조건1715480포트는case별binarytrace/fullbyte비교로검증했다. 최종보고서 SHA256 `a7941afc795daf3895485ed76c1afd493f3b3b6b3941d36c43aeaf5010522ee8`.
- 전체make Python139/C++99/경고0. 메인리뷰0155,scene-setup.md,inventory/observation도구에근거·재생성·제약을저장했다. 지원20종중4c는canonical에없어합성unit만이며전체게임복원완료율로환산하지않는다.
- 다음은1a26a phase gate와일반scene 초기화/후속frame을연결하는작업이다. 현재검증은standalone명령과순차helper승계이며원본시간축의전체script실행·실제맵tile/frame업데이트·플레이가능스테이지화면은아직미완료다.


## 2026-10-07 — 장면 스크립트 조건부 실행 루프 통합

- 원본1a26a의 A1 최초 load, LIVE unsigned phase gate,20종 handler 반복, cursor publication과 음수 종료를 C++ run_scene_script API/CLI로 연결했다. 종료 후 cursor를 유지하며 다음 호출도 phase 조건을 다시 적용한다. Raw MS5D를 직접 소비하고 호출 전체 RAM/12register/result/ports를 transaction으로 처리한다.
- 원본2211조건/오류70조건/7657120 orderedports/26170 handler 실행 비교 통과. 41script의 phase/threshold/register 조합1230, 모든814 command cursor 시작, 실제 CLI carry164, 별도 null/wait/terminal3을 포함한다. 호출 내부 context reset은 없으며 호출간 phase 변경은 명시 host fixture다.
- Preload 오류를 late API 오류로 잘못 표시한 검증 설명을 수정하고 실제 선행48 이후08 descriptor identity 오류를 추가 검사했다. 최종 report SHA256 `e9cc49c1c4fead4cdb7454f9af6adac3cf9d9c3ff3205b1fcf8936430acc5113`. 전체 make Python139/C++100/경고0. 메인 리뷰0156과 scene-script-run.md에 계약·검증·재현 방법을 기록했다.
- CLI는 초기 gate 통과시 전체 script dependencies를 미리 로드한다. API의 실행시 접근과 구분한다. 현재도 자연 frame/IRQ 시간축과 일반1a5a4·후속 장면 갱신·직접 조작 가능한 스테이지 화면은 미완료다. 다음은 motion 경로 이동/평가와 일반 scene 초기화를 연결하는 작업이다.


## 2026-10-07 — 장면 이동 경로 평가 연결

- 기존MS5D motion37경로/108구간을직접소비하는evaluate_scene_motion API/CLI를추가했다. 원본19938의구간전후이동·기준좌표word누적·36type16.16좌표계산·종료clamp와최종offset을연결했다. N-only분기,NEG-before-ASR,word/longwrap과register보존폭을명시적으로재현한다.
- 원본12,170조건/오류69조건/MMIO0통과. Strict주소5,466(canonical경계5,168+74양방향CLIcarry290+null8),RAMrelocation합성6,704(36type6,480+N-only경계224)이다. 전체RAM/12register/RTS/A7/ROM불변을비교했고미복귀0이다. 합성은원본RAM경로106000과C++fixed60000간A1/d3b4만정규화하며실제게임데이터와구분한다.
- 보고서 SHA256 `a9926535334bf76d820277ac25b3da2448e8346599d11f372c4f7fa8755522a9`. 전체make Python139/C++101/경고0. 메인리뷰0157,scene-motion-evaluation.md,inventory/disassembly/dispatch재생성도구에근거와제약을저장했다.
- 다음은1a7a8 node갱신과일반1a5a4의동일호출연결이다. 기존nullscript초기화만으로일반진입을대체하지않는다. 자연frame/IRQ시간축·직접조작가능한스테이지화면·전체게임복원은미완료다.


## 2026-10-07 — 카메라·네 노드 좌표 갱신 연결

- SceneNodeState를D0..D7/A0/A1/A2/A4로확장하고기존5registerCLI를유지했다. 곱셈/ASR/분수carry scratch와부모좌표·history/globalstamp alias의읽기순서를원본대로반환한다. 기존position_state RAM-only코어는수정하지않았다.
- 1a7a8부터1a8ca직전까지카메라와네노드의좌표prefix를연결했다. LIVE mask로축별scale을선택하고worldY상위word에scroll을적용한다. 1afda및네19e64 tail은포함하지않으며전체1a7a8완료로취급하지않는다.
- 신규원본5248조건(leaf1132/prefix4116)/오류135/MMIO0/CLIcarry20호출통과. Prefix는1a8ca직전A7초기값,leaf는RTS후A7+4를검사하며호출내contextreset은없다. 보고서SHA256 `f903e4444ad1f690bc8a4ae0aa016e20418479fa34ec5cc634189dbd6fd8bf0a`.
- 기존node1904/94회귀는동일SHA c900dfc01d94c31633856b8ffae34478ce9ad281366b9322e23ccebd85a0c1c6이며scene command4535/104/1737175ports도통과했다(최신reportSHA256 `1a08295adfc94be432f14a46b013a760808ef0706679220b0f6355cb0d1b1019`). 전체make Python139/C++102/경고0. 메인리뷰0158과scene-coordinates.md에범위·검증·재생성을기록했다.
- 다음은미연결1afda와19e64 path/display처리및추가리소스다. 일반1a5a4와47a94이후전체진입·자연시간축·실제스테이지화면및전체게임복원은미완료다.


## 2026-10-07 — 장면 경로와 맵 데이터 참조 조사

- 후속19e64의8종구문과descriptor참조를원본에서확인했다. Scene opcode24의72고유root를218행으로목록화했다(00/04각72,18두개,terminal72). CFG양쪽조건edge를보존하되canonical에는조건명령이없어자연도달검증으로간주하지않는다.
- 원본dispatch654조건은handler진입직전/terminalRTS까지만통과했으며RAM·stack쓰기0/ROM불변이다. Handler본문이나C++실행완료가아니다. ReportSHA256 `f50925f4e467cf4fda90309e3cf2cab58bf9ba07cb746fdc273fea5795204e11`.
- Bank3 primary map 후보77개는모든header/범위가유효하고gap/overlap0,합계763136bytes/190707cells다. 참조72descriptor의69selector치수가모두일치한다. 나머지8selector는현재알려진참조없음으로기록하며미사용확정하지않는다. TilemapreportSHA256 `4249e94dcb069c477494b40ec91a312cde0ee076ec9ac978d35db9daf1a50262`. Bank2 secondary자료는별도참조로확인했고collision의미는미확정이다.
- 메인리뷰에서재귀한도와descriptor metadata대조를보완했다. 합성구문7개포함전체Python146tests통과. 리뷰0159와scene-paths.md/scene-tilemaps.md에원본창·재생성·사실/후보범위를기록했다. 이번에는C++/MS5D규격을바꾸지않았다.
- 다음은경로/맵MS5D추출과C++실제소비,19e64/표시helper연결이다. JSON조사를최종게임리소스로대체하지않으며일반scene/스테이지화면/전체게임목표는계속미완료다.


## 2026-10-07 — 장면 경로·맵 바이너리 리소스와 C++ 로더 통합

- 기존 MS5D v1으로 path72개, primary root/lookup2개, bank3 map77개를 추출했다. 총151파일/765048 payload bytes이며 C++ path decoder와 column-major cell 조회 API가 원본 바이너리를 직접 소비한다. PNG 변환물은 사용하지 않는다.
- 메인 리뷰에서 빈 payload, 중복 root/파일/ID, raw selector/pointer와 reference metadata 검사를 보강했다. 보강 후 manifest SHA256 `8312156694a7cf20a6782ad6834285965734c579cb532e09d82f40839080411e`와151개 container는 동일하다.
- Typed C++149파일(path72/map77)의218행과190707셀 전체를 재조합해 원본과 대조했다. Root/lookup2파일의77map 연결은 별도 검사했다. 오류39조건 통과. Report SHA256 `7d799705deddddfc37482d63fdc9aa8ee4b903594f8064bf89d048e3df3ed6ec`.
- 전체 빌드 C++103/경고0, 최종 Python154 tests 통과. 메인 리뷰0160과 scene-map-resources.md에 계약·재생성·근거를 저장했다. Read-only 리소스 검사이며 handler 효과/VRAM 실행 검증은 아니다.
- 다음은183c6의 맵 clipping/VRAM/cache 전송과 bank2 secondary 자료,19e64 handler 및 일반 scene 진입 연결이다. 직접 조작 가능한 스테이지 화면·자연시간축·전체 게임 복원은 미완료이며 전체 목표는 계속 active다.


## 2026-10-07 — Secondary 맵 접근 창 추출

- 원본183c6의clipping/VRAM/bank2 secondary흐름을메인이분석하고scene-map-transfer.md에명령폭·순서·미확정범위를기록했다. 각secondary offset은WORD자신의주소기준이며primary column당2개의offset을소비한다.
- 비영descriptor40개/selector37개에서8642column 후보를목록화했다. Root/lookup/offset/cell 읽기창8723개의union만기존MS5Dkind2 47파일/164960bytes로추출했다. 겹침·인접merge후hole을추가하지않는다. 전체논리자료extent나collision으로단정하지않는다.
- Header/CRC/원본전체bytes/metadata및독립endpoint sweep union비교통과. ReportSHA256 `79f4678387ed1d40a8c1257dc992e0b7c622fc6e414ad65e4098f33bf75e597b`. 합성8개포함전체Python162tests통과,리뷰0161완료.
- 이번resource검증은Python-only다.183c6 C++전송루틴과원본관찰은별도작업중이며아직동등성완료로기록하지않는다. 일반scene실행연결·직접조작가능스테이지화면·전체목표는미완료다.


## 2026-10-07 — 맵 사각형의 영상·보조 캐시 전송 연결

- 183c6 clipping→bank3 primary VRAM쓰기→bank2 secondary RAMring쓰기→flag/carry를C++ API와CLI로연결했다. 앞서추출한scene_maps/scene_secondary MS5D를직접소비하며D0..D7/A0..A4 13register를보존한다. MOVEM.W sign-extension,ADD.B폭과LIVE descriptor읽기를반영했다.
- 원본492조건/CLI오류29조건/ordered16620ports 비교통과. 전체RAM·13register·copied가일치하며복사420/거부72,RAMdescriptor-bankshadowalias4조건을포함한다. ReportSHA256 `ba687e364602ab08a4074d3aa09f5b17ae8396576132a30c75d5ae99f611acef`.
- 전체make Python162/C++104/경고0,메인리뷰0162완료. Sentinel secondary는canonical원본관찰에없어합성unit범위이며다회호출승계/자연streaming은아직검증하지않았다. 임시primary/secondary각1048576cell실행한계초과는명시API오류다.
- 다음은18702 wrapping/16f0e columncontrol/1861a·18656 refresh와19e64 handler를연결하는작업이다. 영상메모리쓰기복원은실제스테이지화면완료가아니다. 일반scene진입·자연시간축·직접플레이·전체게임복원목표는계속미완료다.


## 2026-10-07 — 맵 열 제어·반복 경계·스크롤 갱신 연결

- 16f0e column control,18702 wrapping,1861a 전체32x32갱신,18656 이동strip갱신을기존183c6과연결했다. DBRA0의65536회,relative columncursor, unsignedDIVU/SWAP, MOVEM.W sign-extension과마지막미복원호출,helper후LIVE flags/dimensions를보존한다. 기존MS5D리소스를직접소비한다.
- 원본1744조건/오류35조건/ordered23636ports에서전체RAM·13register가일치했다. 72canonicaldescriptor와경계/이동/null/합성RAMcolumn경로,비power-height와초기A1≠node2e10조건을포함한다. 최종전체비교SHA256 `2ec30f6b5727a14a977d3d1d525a5a1c02d253580749d134790dc4bd7ba45944`.
- 메인리뷰에서LIVEwidth unit의변별력을수정하고증분검증의자료재사용검사를보강했다. 최종결과는자료재사용없이1744조건전체를재대조했다. 합성guard8개포함Python170/C++105/경고0,기존183c6 회귀492/29/16620ports통과. 리뷰0163과scene-map-refresh.md에근거·한계·재생성을저장했다.
- 다음은19e64 path handler와16ff8 descriptor설정,1afda 전체register승계,전체1a7a8/일반1a5a4/47a94진입연결이다. 임시탐색/전송예산한계,자연frame/다회호출승계·직접플레이화면과전체게임복원은미완료이며goal은active다.


## 2026-10-07 — 장면 경로 실행과 맵 교체 통합

- 19e64의8종명령과16ff8 descriptor설정을C++ API/CLI로연결했다. 기존MS5D path/map/secondary bytes를직접소비하고initial moved refresh,descriptor 교체,조건분기와cursor게시를원본순서로실행한다. 전체호출RAM/13register/ports는실패시보존한다.
- 원본2,958조건/오류36조건/130,388 orderedports의전체RAM·13register 비교통과. 72canonical경로와218cursor,합성RAM분기,메인리뷰에서추가한256 highflag×oldmap유무512조건을포함한다. 조건opcode의canonical사용이나자연도달을주장하지않는다.
- 전체비교 SHA256 `9f4d41d3bd8c55215a56f060f138603e0e972f8c59293715e4db85dd8a8ff687`. 전체make Python170/C++106/경고0,기존refresh회귀1,744/35/23,636ports 통과. 메인이최종binary/resource/report hash와추가분기범위를확인했다. 리뷰0164와scene-path-execution.md에계약·재생성·제약을기록했다.
- 다음은기존1afda debug의전체register승계확장과1a7a8 좌표prefix→debug→네path의동일호출통합이다. 이어일반1a5a4 및47a94 진입을연결해야한다. 임시명령/탐색/전송예산,자연frame/직접조작가능한스테이지화면및전체게임목표는미완료이며goal은active다.


## 2026-10-08 — 전체 장면 갱신 연결 작업 중

- 직전goal turn은path통합70dc096으로progress였다. 이번에는메인이1afda/lookup/reset의전체register변화와1a7a8 tail호출순서를확인하고,sol이13register debug API·좌표prefix→debug→네path composite와CLI를구현했다. 기존3register debug API는wrapper로유지한다.
- 현재fullmake Python170/C++107/경고0. 신규unit은A3보존,네RAMpath순서,debug1280ports 후네번째path실패의전체rollback을포함한다. Main core/CLI/unit 리뷰에서현재까지추가수정사항은없다. step_scene_update SHA256 `062b79fd12f7d16098ac7d845e07c0b7605bb28aa3d2a0a6a9c13de8e478e5c7`.
- 기존scene_initialization 회귀576/오류24/672744ports/7승계sequence통과. Report SHA256 `bfa2403632a17fe814710ae03897243fab189646848ed6e7e5c61d2d7bbd2566`. 이회귀는기존D0/D1/D3만비교하므로신규13register 전체update검증을대체하지않는다.
- 신규독립원본observer/verifier는담당agent control_finish_verify가작업중이다. 최종전체RAM/13register/ports 비교,메인harness리뷰,리뷰0165와로컬commit은아직남았다. 원본창5개336행과분석계약은inventory_scene_update.py 및scene-update.md에보존했다. 직접플레이화면·일반1a5a4·전체goal은계속미완료다.


## 2026-10-08 — 전체 장면 갱신 원본 비교·통합 완료

- 위작업중항목의1afda 전체13register와1a7a8 좌표→debug→네path 연결을검증했다. 원본1,417조건/오류44조건/1,403,936orderedports의전체RAM·13register가일치한다. Actual CLI RAM/regs승계20호출/11sequence도통과했다.
- 메인리뷰에서native포트allowlist의3c0004누락과slot0이지만전부clip되는mapfixture를발견해보완했다. 기존극단좌표를보존하고추가visible72에서원본전송성공/3c0000쓰기를필수검사했다. 이72조건에실제96,616ports가있다. 최종native와C++를전체재실행했으며재사용positive는없다.
- Report SHA256 `b9a0e96aa5e041411a578da4756e71cd716e8f96eb1452f5fe253ff1b87b58c5`. Native SHA256 `a04fd624e808e1f58f3c22d1ba5ead5fbdb4cb411bde008b20e4c2c14157e030`. 전체make Python170/C++107/경고0과기존초기화회귀576/24를확인했고리뷰0165·scene-update.md에원본계약/재생성/한계를확정했다.
- 다음은일반1a5a4 초기화와phase반복연결이다. 종료후1a414가소비하는opcode0c pointed자료18개는현재41script/199dependency에포함되지않는것을원본명령과manifest로확인했다. 해당배치자료추출·1a470/object할당·position·inlinepayload까지연결해야한다. 현재전체update검증을일반초기화나자연frame·직접플레이화면완료로취급하지않으며전체goal은active다.


## 2026-10-08 — 장면 배치 스트림 바이너리·C++ 로더

- Scene command0c가참조하는18root를원본1a414/1a470의경계로분석했다. 일반record24개/정확ffff terminal18개,총422bytes이며inline길이0/2,bounds모두0,callback24개는rawpointer로보존한다. 미실행callback을복원완료로취급하지않는다.
- 기존MS5D v1kind1으로18resources를생성하고C++ typedloader/검사CLI를추가했다. Highgate8000..fffe와opaque pointer를보존하며odd/8000이상inlinecount는명시지원밖오류다. Native의copy loop와signedskip차이를근거로제약을기록했다.
- 18container의C++JSON을재조립한422bytes가원본과전수일치했다. CLI오류26/합성raw양성1/Python합성5 포함전체Python175/C++108/경고0. Report SHA256 `5e4c65d7bbdd46daa77a773f0ee0ba0328603174cdf56db92cb64529b9cb0e92`,manifest SHA256 `d958cd6ad42dfa84c6675f20c1e1a3251dab95ea71c184d70c4e2efe4fea3306`.
- 메인이packer root범위검사와Makefile선행inventory생성을보완하고리뷰0166·scene-placements.md·공통resource-format.md를확정했다. 관련세재생성명령의hash동일성을확인했다. 이번검증은구문/데이터읽기이며placement 실행검증이아니다.
- 다음은19802 inverse motion의구간선택과1a470 bounds/object allocation/position/inlinecopy,1a414 phase gate를연결하고일반1a5a4로통합하는작업이다. 자연frame·직접플레이스테이지화면·전체게임복원은계속미완료이며goal은active다.


## 2026-10-08 — 좌표에서 경로 시간 조회 통합

- 원본19802/18efa의네축·방향투영과1972a 구간선택을C++ API/CLI로연결했다. 기존37개MS5D motion리소스를직접사용한다. Fraction borrow, D0/D1 LONG보존, backward의조기cursor게시와forward뒤재투영차이를보존했다.
- 신규원본2,664조건/오류69조건에서전체64KiB RAM·12register가일치했다. Canonical/null1,584와주소정규화합성1,080을구분한다. 74sequence/290호출중216호출이직전CLI출력을승계하며XY변경은명시host입력이다. 자연프레임진행검증은아니다.
- 신규report SHA256 `1759ae535202062c79b78cfa9e760d09449dfd14ed3505fdc8e07a679eceebb6`. 메인은원본비대칭·공유selector·CLI/unit·독립observer/verifier를리뷰했고resource37개/manifest/native/binary의현재hash를확인했다. 입력RAM불변과resource전후hash검사를보강한뒤C++전체를재비교했다.
- 전체make Python175/C++109/경고0. 기존19938 회귀12,170조건/오류69조건/MMIO0/미복귀0도통과했다. Report SHA256 `ab2460c368136e41266e0cf982f99628c3a5d64b46a83818c22588b22942a2f9`,binary SHA256 `8e2a9567a004d4c48f0e2aff092478e8af40dfc1d542a3de5cc325bb93694c35`. 리뷰0167과scene-motion-time.md에계약·재생성·임시반복한계를기록했다.
- 다음은1a470의bounds/object할당/43e08position/inlinecopy와1a414 gate를연결하고일반1a5a4로통합하는작업이다. 직접조작가능한스테이지화면과전체게임복원은미완료이며goal은active다.


## 2026-10-08 — 배치용 WORD 좌표 초기화

- 원본43e08의lowWORD→16.16변환과parent/local/stamp초기화를기존position경로에연결했다. 43e22의LONG입력과구분하며전체RAM/12register transaction을유지한다. 메인이원본·core/unit·독립verifier를리뷰했다.
- 원본2,020조건/오류72조건/MMIO0통과. Parent/self/overlap/stamp aliases와유효RAM경계,할당거절후에도원본이쓰는100ec6주소를포함한다. 실제CLI승계4sequence/20호출중16이직전출력을소비한다. 신규report SHA256 `69cc9998a64b73427ac99aa46579e4c6032dbce91862391f6accd33b588598b6`.
- 기존좌표회귀5,248/오류135/MMIO0,전체make Python175/C++109/경고0. 회귀report SHA256 `ca8a3b769e504965d2c2e2ad0f2d531433576cef5861bced5212be35d2ac7066`. 리뷰0168과scene-placement-execution.md에근거·재현·한계를기록했다.
- 다음작업의1a414/1a470전체원본순서를분석했다. X bounds도d3a6을읽는점,allocation실패시에도position쓰기,WORD inlinecopy와signedskip차이를보존해야한다. 이전체배치실행·일반1a5a4·자연frame·플레이화면·전체게임goal은아직미완료다.


## 2026-10-08 — 장면 배치 실행 통합

- 1a414 phase gate와1a470 시간조회/bounds/할당/좌표/WORD payload복사를단일C++ API·CLI로연결했다. 기존18placement/37motion MS5D를직접읽고RAMalias는LIVE읽기순서로처리한다. 할당거절후에도100ec6에위치쓰기,inlinecount의후반재조회,stream중phase재조회를보존한다.
- 원본1,625조건/오류113조건에서전체64KiB RAM·13register가일치했다. 18root/24record/37motion과네bounds제외분기,겹치는WORD복사,같은호출중phase변경뒤두번째record실행을포함한다. 18CLIsequence90호출중72는직전출력을소비하되phase/A0/A6는명시host입력이다.
- Verification SHA256 `341085cfa6992a09e44fefc3d23cfe18b3f409c88e5d1d65abf6102ae994996b`. Native SHA256 `716b54add2b2733cbd04b7274e6d6fe852e7762cc8558f32056720da457b2820`. 전체make Python175/C++110/경고0. 메인이core/CLI/unit/observer/verifier를읽고검증fixture의bounds우회·잘못된복사겹침·RAM끝계산을보강했다. 최종전체재실행과현재hash를확인했다.
- 리뷰0169와scene-placement-execution.md에재생성·지원제약을기록했다. RAMmotion과odd/8000이상inline길이,임시record한도밖은지원밖오류다. Callback은저장만하며실행하지않는다.
- 다음은일반1a5a4 초기화의script/phase반복/전체update/배치연결이다. 메인이원본을대조해scene-general-initialization.md에후속계약을저장했다. 자연frame·직접플레이화면·전체게임복원은미완료이며goal은active다.


## 2026-10-08 — 일반 장면 초기화 통합

- 일반1a5a4의script실행→phase선택/반복→motion→전체scene update→좌표정리→placement를C++ API/CLI로연결했다. 초기D0.low target/A0script를보존하고14register와orderedports를승계한다. 기존null-script특화API는변경하지않았다.
- 221조건/오류111조건에서전체64KiB RAM·14register·3,176,113orderedports가원본과일치했다. 모든41script와59catalog실제입력쌍,큰target경계,debug8/16,할당성공/거절을포함한다. Phase최대13회,map성공856회,placement102회,allocator거절23회를관찰했다. 4CLI승계sequence8호출중4는직전출력을소비하되D0.low/A0/A6는host가명시한다.
- Verification SHA256 `950e3dd90209d2efd6a6629bf1568996396fb6005bede6e79df0f2ae290316eb`. Native SHA256 `7cf8f965dd1b774eafff1ad73400eab54dca1a8373f8a75ce6cb14557ddffa6e`. 전체make Python175/C++111/경고0. 메인이core/CLI/unit/observer/verifier와현재458resource/binary/report hash를확인했다. DirectoryCLI도별도canonical조건에서RAM/ports일치했다.
- 리뷰0170·scene-general-initialization.md에재생성·입력fixture·지원제약·한계를확정했다. engine/README.md의오래된현재상태설명을갱신하고CLI사용법을추가했다. 현재결과는직접플레이화면이나전체stagecallback실행을뜻하지않는다.
- 다음은47a94 caller의e8a1c/48398/e905c및480bc연결이다. e905c의stream자료와2a28전체register계약은추가복원이필요하다. 메인이후속원본을직접확인해분석문서에저장했다. 자연frame·전체게임복원은미완료이며goal은active다.

## 2026-10-08 — 전체 레지스터 오브젝트 재시작

- 원본2a28의palette해제·좌표연결해제·초기화·callback저장을새C++ API/CLI로구현했다. D0-D7/A0-A6전체15register를승계하고기존부분API는보존했다. 메인이callee와LIVE alias를직접해석했고구현/원본비교/목록화는sol3개에분담했다.
- 597조건에서전체64KiB RAM·15register·597orderedwatchdog출력이원본과일치했다. 팔레트rawcount255,부호있는link,coordinate부모/self/overlap,종류변경뒤연속연결정리와이전static종료를포함한다. 4실제CLIsequence12호출중8호출은이전출력을소비한다. 오류136조건에서입력/기존출력을보존했으며self-cycle65,536회한도도검사했다.
- Verification SHA256 `6a196fae937d7d558b8d885ec5c237a02236bc216683a0740e820dc4037483d6`. Native SHA256 `ac50d120ef409636185808d039c4a1c0425d20f526f6f74fd83afb3aa86b670c`. 전체make Python175/C++112/경고0. 메인이core/CLI/unit/observer/verifier·597저장결과와현재hash를확인했다. 리뷰0171·object-restart-full.md에계약/재생성/제약을기록했다.
- 후속e905c의실제입력도목록화했다. Catalog59record중비영stream52/null7,고유stream47/gate612다. 이는선택알고리즘의raw목록이며전체event문법·runtime자료추출·callback실행완료는아니다. Report SHA256 `42dd9abc3b757545521fca62a14dab435b51b236c7f97434d515d6b383394372`.
- 다음은event리소스추출과e905c실행,47a94후반e8a1c/48398/480bc연결이다. 자연frame·직접플레이화면·전체게임복원은미완료이며goal은active다.

## 2026-10-08 — 이벤트 바이너리 자료와 초기화 연결

- e905c의전체15register계약을복원하고C++ API/CLI에서full2a28→target별stream cursor선택→조건부bankreset을연결했다. 입력A5의주소계산순서,lowWORD/byte상위보존,signedjump,unsignedgate비교,LIVE RAM헤더와홀수ff주소를보존한다.
- 47stream/47pointercell/조회표1개의95MS5D를추출했다. 48,881payloadbytes,overlap0. 기존v1kind1을사용하고중간미해석명령도원본그대로보존한다. Manifest SHA256 `cc1074eefb3698de5ae704e2aaed32240df3f3f4da9d41dc46c6c5d1666590db`. 전체event문법과미사용영역종료를증명한것은아니다.
- 원본2,443조건/orderedports7,275개에서전체RAM·15register가C++와일치했다. 모든612gate의실제native방문을확인했다. 오류120조건에서입력/기존출력보존,2CLIsequence6호출중4의출력승계를확인했다. Verification SHA256 `27e2a119c5b7774f2f4f7f05d3b522c0ea50f22dd013a29b85198e3abfa89f6c`,native `cae0353feda387d994ded125aa4585d633dc589e8dbc9a87d98c46a5244fdb88`.
- 전체make Python182/C++113/경고0. 메인이core/CLI/unit/packer/observer/verifier전체와현재95resources·2443저장결과를검토했다. Cachedinventory근거검사를재생성동일검사로보강했고directoryCLI도별도로원본과대조했다. 리뷰0172·stage-event-initialization.md·공통규격/README에재현과한계를기록했다.
- 다음은47a94후반e8a1c/48398및480bc연결이다. 480bc는1a73c frame경로등다수callee를실행하므로추가분석이필요하다. e9150 callback실행,자연frame·직접플레이·전체goal은미완료이며goal은active다.

## 2026-10-08 — 장면 경로 폭·좌표 제한·가시 경계

- Frame1a73c가필요로하는198ee/19978/19d98/19d08을C++ API/CLI로복원했다. 기존37motion MS5D를사용하고bias전위치계산만기존19938과공유한다. 메인이N-only LONG비교와signed WORD비교,전체EXG,WORD스택복원,마지막ADD만의포화를분석·리뷰했다.
- 원본3,606조건/오류117조건이통과했다. Canonical880/null206/합성주소정규화2,504/실제CLI승계16호출을구분한다. 네진입모두36type을실제로관찰하고CMPoverflow40조건·포화6조건에는branch/register근거를검사했다. 4승계sequence의12호출은직전CLI출력을소비한다.
- Verification SHA256 `d867cf922bba3631da01ee66a160ae9098e1d2af7677e521cf2209dd4acdc20f`,native `f32ba07b37962d31b86feb720d25c8c72754feef529eb7d9e82193a24077d528`. 메인이전체core/CLI/unit/observer/verifier와3,606저장RAM/결과·37resources/원본hash를확인했다. 리뷰0173·scene-motion-bounds.md에재생성/합성자료/지원한계를기록했다.
- 기존19938 12,170/오류69,19802 2,664/오류69 회귀와전체make Python182/C++114/경고0을확인했다. 최종build의세CLI hash도각report와동일하다. Frame10창548행목록과37motion108record+4WORD가모두0인사실을기록했다. 이목록밖미사용자료의값이나도달성을추론하지않는다.
- 다음은19832/192c4의두좌표경로선택,19a40/19ac8/19b96의좌표진행,1a2b4조건등을연결하여전체1a73c frame을복원하는작업이다. 자연frame·직접플레이화면·전체게임goal은아직미완료이며active다.


## 2026-10-08 — 두 좌표 경로 검사·선택과 독립 CPU 검증

- 원본 192c4/19832를 C++11 API·CLI로 복원했다. 기존 37개 motion MS5D를 직접 사용하며 두 좌표 변환, 구간 이동·되돌림, 시작/끝 제한을 연결한다. 원본의 비대칭 D0 재사용 열 명령과 N-only 분기를 보존한다. 전체 RAM·12레지스터·carry는 성공 시에만 게시한다.
- 4,232조건에서 Musashi로 실행한 원본의 전체 RAM·12레지스터·반환 carry가 C++와 일치했다. Canonical 2,376 / 합성 주소 정규화 1,846 / null 10이다. 모든 108개 canonical record와 합성 36type을 포함한다. 오류 107조건에서 입력/기존 출력을 보존했다. 8개 CLI sequence의 24호출 중 16호출은 직전 출력을 소비한다. XY 갱신은 명시 host 입력이며 자연 프레임 검증은 아니다.
- 메인이 Unicorn 2.1.4의 실행 중 SR-read hook이 분기를 바꾸는 문제를 36개 별도 합성 조건으로 재현했다. 최종 secondary는 실행 중 SR을 읽지 않으며 모든 RAM·레지스터가 Musashi와 일치했다. 반환 후 raw SR.C의 1,326개 불일치는 진단값으로 남긴다. 원본 ROM이나 CPU 플래그를 보정하지 않았다.
- 고정 revision의 공식 Musashi를 ignored artifact에서 빌드하는 도구·C bridge·Python wrapper를 추가했다. 메인이 코드와 callback/메모리/budget 계약을 리뷰하고 CCR·관찰 기능 무간섭·예외 거절 검사를 직접 확인했다. 버전·archive·191 vendor 파일·빌드 옵션·라이선스·현재 library/source hash를 결과에 결합한다. 게임 엔진에 에뮬레이터를 넣은 것은 아니며 사이클/MMIO 재현은 이 검증 도구의 범위 밖이다.
- Verification SHA256 `5cb8f44eff5d7552bba9eed5e146bb3c6b984d1180e1622df5ef4f13c3917853`, primary native `e9aaaf121cdddf157aa8d756d29ee2659a18611ee62f5b6fd426ea17d4ae9408`. 메인이 최종 4,232개 결과·저장 RAM·모든 원본/리소스/oracle/CLI/probe hash를 직접 대조했다. 리뷰0174와 scene-motion-pair.md에 재현·제약을 기록했다.
- 전체 make Python182/C++115/경고0, 기존 19938의 12,170/오류69, 19802의 2,664/오류69, bounds의 3,606/오류117 회귀를 통과했다. 별도 oracle 빌드의 macOS linker alignment 경고 1개는 metadata에 남겼다. C++ 방어적 반복 cap은 현재 공개 입력으로 도달하지 않아 소진 검증을 주장하지 않는다.
- 다음은 19a40/19ac8/19b96의 좌표 진행이다. 메인이 Y 선행 저장, X/Y 후진 검사 비대칭, unsigned 제한과 N-only/signed 분기를 분석해 scene-camera-progress.md에 계약을 남겼다. 이후 조건·배치 단일 실행과 전체 1a73c를 연결한다. 자연 frame·직접 플레이·전체 goal은 계속 미완료이며 active다.


## 2026-10-08 — 카메라 좌표 진행

- 원본19a40/19ac8의 축별 요청과 전체19b96을 새 C++11 API·CLI로 연결했다. 기존19802/19832/19978과37motion MS5D를 사용한다. Y 선행 저장, X/Y 후진 검사 비대칭, N-only와 signed/unsigned 비교, 강제 속도 zero-extension을 보존한다. 메인이 원본·core/CLI/unit을 리뷰하고 마지막 경계 초기화 쓰기 순서를 원본대로 정리했다.
- 원본2,773조건/오류102조건을 통과했다. 축별1,152/canonical1,080/합성 주소 정규화465/null 전체진행76이다. 모든108 canonical record와36type을 관찰했다. X385/Y382 ADD V1 분기와 unsigned 제한의 다섯 분기 양쪽 목적지를 검증했다. 축별335조건은 실행 중 SR을 읽지 않는 Unicorn과도 전체RAM·12레지스터가 일치했다.
- 강제 속도를 더한 LONG이 감싸더라도 전진 제한으로 가는 원본 경로를 확인했다. 이동 거절457회 중128회는 이전에 바뀐 cursor와 제안 XY를 유지하면서 현재 XY를 보존했다. CLI8sequence/24호출 중16이 직전 출력을 소비한다. Host가 제어 필드와 old velocity 등을 매번 설정하므로 자연 frame/velocity 연속성 검증으로 표현하지 않는다.
- Verification SHA256 `6e98c13f63080f3859d99446d618990d615e2e1c2fb756a818be46b74f0b86c2`, native `94e5b900cb10941cccca10dbf08392218beefb4fda498b6ad8ba72eb61736e65`. 메인이 모든 native 저장 RAM·report 행·현재 원본/리소스/oracle/CLI hash와 분기 근거를 대조했다. 전체make Python182/C++116/경고0과 수정 후 대상unit 재검증이 통과했다. 기존 motion core/binary는 그대로다.
- Camera 두 코드 창193행과 literal 비대칭 명령6개를 보존했다. 후속 조건 데이터는41script/814명령 중9개 opcode2c의 inline98bytes이며 기존 MS5D 안에 있다. Selector4는8개,8은1개이고 정의된 길이와 정확히 맞는다. 메인이 source/container/catalog 참조 대조 도구와현재hash를 확인했다. 미사용 전체 범위나 조건 실행 완료로 확대하지 않는다.
- 리뷰0175와 scene-camera-progress.md에 구현·재현·한계를 정리했다. 다음1a2b4 조건,1a526 설정,1a3d6 흔들림,1a442 단일 배치와전체1a73c 계약은 scene-frame-control.md에 저장했다. 전체frame·직접플레이·전체goal은 계속미완료이며 active다.

## 2026-10-08 — 장면 조건·설정·흔들림과 단일 배치

- 1a2b4 진행 조건,1a34c 사각형,1a29e raw 기간,1a526 설정,1a3d6 흔들림을 C++11 API/CLI로 복원했다. 기존 script/motion MS5D와 live RAM을 읽고 전체 RAM·12register·carry를 성공 시에만 게시한다. Packed LONG 덧셈·단락 평가·signed/unsigned 경계·WORD 상위 보존·ASR/NEG wrap을 유지한다.
- 2,235조건/오류133조건에서 Musashi 원본의 전체 RAM·12register·실제 C와 일치했다. Canonical9 조건/108 motion cursor를 포함한다. 선택299조건은 SR-read hook 없는 Unicorn과도 RAM/register가 일치했다. 네 CLI sequence42호출 중38회는 이전 실제 출력을 재작성 없이 소비하며 두16-shake 연속 호출을 포함한다.
- 메인이 구현·unit·검증 도구를 읽고 packed rectangle unit 기대값과 설정 fixture 주소 오류를 발견했다. 잘못된0444 대신d444 등에 입력하도록 수정하고 실제 분기 양쪽·입력 필드 assertion을 추가한 후 전체 원본/C++ 비교를 재실행했다. 양축 fallback 각각100회, signed rectangle 네 분기 모두 양쪽 경로를 확인했다.
- 기존 placement API에1a442를 추가했다. 원본814조건/오류19조건에서 RAM·12register/A6가 일치한다.18root/24record/18terminal/37motion 입력 집합을 대조했고744조건은 한 번,70조건은0번 record를 실행했다. 실제 unmapped 다음 페이지를 읽지 않으며 같은 두 eligible 입력의 loop/single 차이도 확인했다. 세 CLI 호출 중 두 후속 호출은 RAM/register를 그대로 승계한다.
- 기존 placement1,625/오류113과 일반 초기화221/오류111/3,176,113 ordered ports 회귀가 통과했다. 전체make Python182/C++117/경고0. 메인이 최종 저장 RAM·결과 행·현재 원본/리소스/oracle/core/CLI hash를 확인하고 리뷰0176을 수용했다. 원격/PR 없이 로컬 branch/commit으로 관리한다.
- Frame verification SHA256 `fbe67ae4b00712c0579f6cb991dfdfcfbfaca3d46c6fea22ba3192312f61c2b2`, native `8bff6c9466994aff28d0c338acfd5ed7630349cc6e2cb583b0e586aae3eb810f`. Single verification `e09fa63f51a0a804fa299889b0304d53e0df6e95c1c4e6c9213fbe3843fed633`. 재생성 명령·전체 hash·지원 한계는 scene-frame-control.md와 리뷰0176에 기록했다.
- 다음은 전체1a73c의 조건→script→설정→camera→bounds→phase→shake→update→단일 배치 연결이다. 리소스는 현재 cursor를 각 호출 직전에 다시 조회하고13register/보존A6/ordered ports를 승계해야 한다. 외부47642의 d68e 생성 원본도 분석 계약에 추가했다. 전체frame·stage callback·직접플레이·전체게임 goal은 계속 미완료이며 active다.

## 2026-10-08 — 장면 프레임 전체 연결

- 원본1a73c의 조건→script→설정→camera→bounds→phase→shake→update→단일 placement와 bank 출력 envelope를 C++11 API/CLI로 연결했다. 각 호출 직전 live cursor에서 기존458개 MS5D 리소스를 선택하며 A3/A6와 포트 순서를 보존한다.
- 원본594프레임에서 전체64KiB RAM·14register·ordered ports621,663건이 일치했다. 오류149조건과 directory 로더 비교도 통과했다. 여섯 연속 sequence360호출 중354회는 직전 실제 CLI 출력을 호스트 재작성 없이 소비한다. Wait16 이후 canonical 명령, 경로 구간 변화, 한 프레임당 한 배치, 실제 빈 풀 대체 슬롯 쓰기를 확인했다.
- Setup replay와 debug8/16은 명시된 초기 host 입력으로 구분한다. 조건 false/phase 유지/camera 거절도 관찰했다. 실행 중 SR을 읽지 않는 Unicorn 원본 실행이며 CCR·IRQ·scheduler·상위callback 완료를 주장하지 않는다.
- 메인이 core/CLI/unit/관측·검증·목록 도구를 리뷰하고 전체 저장RAM·ports·register/입력승계·현재 provenance를 직접 확인했다. 초기 coverage 오해와 negative resource 목록 비교를 수정했다. 전체make Python182/C++118/경고0. 리뷰0177과 scene-frame-execution.md에 재현·해시·한계를 기록했다.
- Native SHA256 `fc060d8c4d74b43d8bdb424f07d99478da6534f86db1426d4d7e3bd93ddac9f2`, verification `bdbeea5e8caa803f045d574a2fd67d726dc7fed23c829a43dfc50ad1dfc56fad`. 다음은480bc 상위 루프의 입력·오브젝트·사운드 연결이다. 입력 callback 원본 계약은 stage-frame-followup.md에 저장했다. 직접 플레이 화면과 전체게임 goal은 계속 미완료이며 active다.

## 2026-10-08 — 입력 매핑·게시·callback 주소 설정

- 49ab4/49afe/49bb4/49c20/49c32/49c66 여섯 보조 함수를 C++11 API/CLI로 복원했다. BYTE/WORD 상위 보존, 겹치는 버튼 mask 처리, mask 읽기·소모·게시 순서, callback 슬롯 선택을 유지한다. 전체13register/RAM은 성공 시에만 게시한다.
- 기본4-byte mask는 새 MS5D v1 kind1 파일로 추출하고 실제 C++ 로더로 검증했다. 원본/metadata/CRC/정확한주소를 검증하며 기본값을 엔진에 하드코딩하지 않는다. 생성 파일·ROM은 Git에 포함하지 않는다.
- Musashi 원본2,694조건과 실제CLI의64KiB RAM·13register가 일치했다. 오류42조건에서 입력과 기존 출력을 보존했다. 두 sequence12호출 중10은 호스트 재작성 없이 직전 출력을 소비한다. 전체 재실행에서도 보고서 SHA가 같았다.
- 메인이 전체source/검증도구/packer를 리뷰하고 저장RAM2,694개·입력승계·원본 쓰기 순서·현재 source/resource/oracle/CLI hash를 대조했다. 복사된CLI오류문구를 수정했다. 전체make Python182/C++119/경고0, scene frame CLI도 이전 hash 유지. 리뷰0178과 stage-input.md에 근거·재현·한계를 기록했다.
- Native SHA256 `987ac8dca989d70198c636e1d0f1713d2a8f84d112b686e5a488125efc089ac2`, verification `6b8e948dbef5e6eed8ff8cdc35f94179c664cc58382dab4e4e0864a424c9b7b6`. 다음은 알려진 입력 callback 실행과 전체49b0c,47642 및상위480bc 연결이다. 현재 callback 주소 설치는 callback 실행 완료를 뜻하지 않는다. 직접플레이와 전체게임 goal은 계속 active다.


## 2026-10-08 — 입력 callback 실행

- 알려진18 callback을 C++11 API/CLI로 연결했다. 좌표차분·목표교차·callback교체/해제·flag/latch·기본입력매핑을 원본순서대로 실행한다.49eba/49ef0의 absolute-memory CMPA,버려지는OR20,D0→D1복원과1d628 A0zero 유지도 보존한다.
- 원본2,943조건에서 전체64KiB RAM·14register가 일치하고 오류160조건이 통과했다. 실제18entry 집합과38조건분기의 양쪽을 확인했다. 네 sequence32호출 중28회는 호스트 재작성 없이 이전 실제 CLI 출력을 소비한다.16 unused-mask 생략과 directory loader도 확인했다.
- 메인이 원본계약·core/header/CLI/unit·관측/검증/목록도구를 리뷰하고2,943개 저장RAM/fixture/register/branch와현재 provenance를 직접 대조했다. 전체make Python182/C++120/경고0. 원격 없는 로컬 검증·리뷰0179·stage-input-callbacks.md에 재현/한계를 기록했다.
- Native SHA256 `2bb75aa89ee636ee8a6afee4df7662def786b02f7a8ee9e3d1b850ff8a41cd0c`, verification `ef931982b559b333ef52a6bd9b9020c78c782568ff874cd9a01a3ef21c97c398`. 다음은49b0c두player loop/47642활동mask와1da60/4d7a6연결이다. 기존플레이어조회resource를 재사용하고A0/A4계약을 보완한다. 직접플레이 및 전체게임goal은 계속 active다.

## 2026-10-08 — 두 플레이어 입력 루프·활동 mask

- 49b0c 두 플레이어 입력,47642활동mask,4d7a6전체주소register반환,1da60교차callback을 C++ API/CLI로 연결했다. 기존19knowncallback과4092-byte lookup/defaultmask MS5D를 사용한다. 첫 player가 바꾼 두 번째 slot을 같은호출에서live로읽으며 unknowncallback은실제로필요할때만오류다.
- 원본3,229조건에서64KiB RAM·14register가일치했다. 두player각255lookup index와3BYTE선택profile,두JSR(A1)각19target을실제로확인했다.48오류조건/3resource생략조건과세sequence12호출중9회이전출력승계도통과했다.17조건분기중TRAP하나를제외한16개는양쪽목적지를관찰했다.
- 메인이 전체source/unit/CLI/목록·관측·검증도구를리뷰했다. Fixture WORD주소+1e를원본의+20으로수정하고모든원본/CLI비교를다시실행했다. 최종3229저장RAM·입력승계·branch·dynamic19target집합·현재provenance를직접대조했다. 전체make Python182/C++121/경고0. 리뷰0180과stage-input-loop.md에재현/한계를기록했다.
- Native SHA256 `0b1b93471c22c27a0cd7623c62cfe9976f62478416e32a5a3b8ad35579e2dd2e`, verification `184414fd1ae985ad9eae7bc2b60580acfa8fea1452bc1fd003e33cd0542be7d6`. 다음은상위480bc의4aa88/b4a2a/4701e/e8a48/2efa6연결이다. 알려진입력경로를넘어전체unknowncallback/자연scheduler/직접플레이가완료됐다는뜻은아니다. 전체goal은active다.
