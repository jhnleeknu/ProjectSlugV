# 477a2/ddf9a/362a/35f0 stage block drawing 인터페이스

원본 의미는 [정적 계약](stage-block-draw-contract.md)을 따른다. canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 아래 고정 CPU 주소는 같은 ROM 파일 오프셋이다. 이 문서는 checked helper API/CLI의 지원 범위와 완료한 focused 원본 비교 결과를 설명한다. 전체 게임 실행 완료를 뜻하지 않는다.

## API와 CLI

```cpp
bool execute_stage_block_draw(std::vector<std::uint8_t>& ram,
    std::uint32_t entry, const std::vector<FixedDataResource>& windows,
    ObjectRestartState& state, std::vector<VideoPortWrite>& ports,
    std::string& error);
```

상태는 기존 `ObjectRestartState`의 D[8]/A[7]이며 전체15레지스터를 운반한다. RAM은 CPU `0x100000..0x10ffff`에 대응하는 정확히65536바이트다. helper는 RAM을 변경하지 않고 ordered video writes를 ports로 반환한다. 원본 resource 대신 PNG나 rendered pixels를 입력으로 사용하지 않는다.

```sh
make runtime-resources
make build/execute_stage_block_draw
```

`runtime-resources`는 기존 생성 단계와 함께 `tools/pack_stage_block_draw.py`를 실행한다. 새 별도 바이너리 형식 대신 기존 MS5D v1 kind1 fixed raw window를 사용한다.

```text
build/execute_stage_block_draw ENTRY \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS [FIXED_MS5D ...]
```

ENTRY를 포함해 숫자는16개, 최소 argc는 실행명을 포함해20이다. 부호 없는32비트 10진수 또는 `0x`/`0X` 16진수를 받으며 빈 숫자, 부호, 공백, 후행 문자와 범위 초과를 거부한다. 추가 인자는 개별 fixed MS5D 파일이며 디렉터리 인자가 아니다. direct35f0 또는 live RAM stream362a는 fixed windows를0개 전달해도 된다. 지원 entry는 `0x477a2`, `0xddf9a`, `0x362a`, `0x35f0`이며 core가 검사한다.

성공 stdout은 한 줄 JSON으로 정확히 `d0..d7`, `a0..a6` 숫자15개만 출력한다. ENTRY나 write count를 추가하지 않는다. OUTPUT_PORTS는 기존9바이트 `>BII`(size1바이트, address/value big-endian32비트)의 순서 있는 레코드다. 오류는 stderr에 쓰며 성공 JSON을 출력하지 않는다.

## 호출과 stream 범위

477a2는 D0.low를7162로 바꾸고 ddf9a로, ddf9a는 A0를ddfa4로 바꾸고362a로 이어진다. 362a는 A0의 stream을 읽으며 각 레코드는 offset WORD, tile WORD, width BYTE, height BYTE의6바이트다. offset WORD가ffff면 종료한다. 레코드 처리 전후 D0.low와 A0를 원본처럼 보존·복원하며 마지막 sentinel 읽기는 D1.low를ffff로 바꾸고 A0를2바이트 전진시킨다. 빈 stream은 rectangle을 실행하지 않으므로 관련 레지스터를 임의로 초기화하지 않는다.

canonical `0xddfa4..0xddfdc`는9레코드와 sentinel의56바이트이며477a2/ddf9a에는 해당 주소를 포함한 고유 fixed window가 필요하다. live RAM stream은 지원 RAM 안에서 각 read 전체가 유효해야 한다. fixed window는 CPU=ROM 오프셋, 비어 있지 않은 payload와 `0x100000` 미만 범위가 필요하다. 요청이 한 window 안에 완전히 포함되어야 하며 겹친 windows의 모호한 read나 partial-window read를 거부한다. WORD read는 짝수 정렬, BYTE read는 홀수 주소도 지원한다.24비트 read 범위와32비트 cursor 덧셈도 검사한다. banked stream은 지원하지 않는다.

각 fixed 파일은 기존 `load_fixed_data_resource`로 magic/version/kind/매핑/길이/CRC32를 검사한다. 동일 파일의 canonical 경로 또는 inode 별칭은 중복 로드를 생략한다. 서로 다른 파일의 겹치는 resource window는 core의 고유 read 검사 대상이며 임의로 합치지 않는다. 제공한 파일 자체는 실제 경로에서 쓰이지 않아도 로더로 검증한다.

## 35f0 효과와 checked 실패

35f0은 A4=3c0000으로 만들고 좌표·tile을 D7에 묶어 각 열의 행을 순서대로 그린다. 매 행은 LONG D7 write 후 D7 전체에10000을 더하고 D7 BYTE에10을 더한다. 마지막 BYTE 연산은 WORD/LONG으로 carry를 전파하지 않는다. 열마다 D1.byte에1, D0.low에20을 더하고 D2.low를 감소시킨다. 종료 시 WORD8200만3c0000에 쓴다.35a2와 달리 watchdog 또는3c0004 write를 추가하지 않는다.

direct35f0의 width/height는 D2.low/D3.low의 nonzero WORD(1..65535)다. stream 레코드는 BYTE로 읽어 D2/D3 전체를0으로 초기화하므로 width/height1..255가 지원된다. 어느 경로든0은 원본 SUBQ/BNE의 WORD wrap 반복이므로 임의 빈 rectangle로 취급하지 않고 명시적으로 지원 밖 오류를 반환한다. 정상 크기에 추가 낮은 dimension cap이나 별도 record/port budget을 두지 않는다.

각 tile을 쓰기 전 unsigned D7이 `0x75000000` 이상이면 원본 TRAP15 경로에 해당하는 checked 실패다. 시작점뿐 아니라 모든 행에서 검사한다. 따라서 nonzero 크기만으로 성공이 보장되지는 않는다. 잘못된 entry, RAM 크기, stream bounds/정렬/중복 window, zero dimension 또는 TRAP 경로에서 실패하면 RAM/state/기존 ports를 모두 보존한다. 성공 시 ports를 이번 호출의 새 결과로 교체한다. 원본 bus fault/TRAP 실행을 정상 완료로 재현한다고 주장하지 않는다.

D0/D1의 WORD/BYTE 연산과 D6.low 감소는 상위WORD를 보존한다. stream의 D2/D3는 MOVEQ0 효과를 포함한다. D4/D5/A1..A3/A5/A6는 보존한다. D7의 마지막 값과 A4를 포함해 전체15레지스터를 caller에 전달한다. canonical477a2의137ports를 포함한 정적 예상값은 실제 원본 관측과 CLI 비교에서 확인했다. 검증의 expected 결과는 정적 대체 알고리즘이 아니라 원본 CPU의 RAM·레지스터·포트 artifact다.

## 파일 보호와 I/O 한계

RAM과 모든 resource 입력은 stream/로더를 열기 전에 `stat`/`S_ISREG`로 일반 파일인지 확인하여 FIFO 등 특수 입력을 거부한다. 입력 RAM과 두 출력의 canonical 경로/inode 충돌을 거부하며 resource도 RAM/출력의 별칭이면 거부한다. 잘못된 입력/resource/core 결과가 있으면 출력 파일을 열지 않는다.

core 성공 뒤 두 출력을 truncate 없이 `O_WRONLY|O_NONBLOCK|O_CREAT|O_EXCL`로 예약하고 기존 파일은 `O_WRONLY|O_NONBLOCK`으로 연다. `fstat`으로 두 출력의 일반 파일 여부와 device/inode를 비교하며 입력 RAM뿐 아니라 **모든 등록한 resource**의 현재 `stat` identity와도 비교한 뒤에만 truncate/쓰기를 시작한다. 따라서 FIFO 출력과 실제 파일시스템의 case alias도 검사한다.

예약/검사 실패 시 기존 파일을 보존하고 이번 호출에서 생성했으며 현재 `lstat` identity가 예약한 inode와 같은 placeholder만 제거한다. RAM과 ports를 순차적으로 쓰고 close 결과도 검사한다. 실제 쓰기/close 실패에는 두 출력의 원자적 교체나 이미 수행한 변경의 rollback을 보장하지 않는다.

## 빌드와 검증 상태

core는 새 `stage_block_draw.cpp`, CLI의 MS5D 로더는 기존 `fixed_data_resource.cpp`를 사용한다. 공유 state/resource/port header 의존성을 포함하며 object restart 구현 전체를 링크하지 않는다. Makefile은 CLI를 all에, `stage_block_draw_test`를 test에 등록한다.

재현 순서는 packer, 빌드, 원본 관측, 실제 CLI 비교다.

```sh
.venv/bin/python tools/pack_stage_block_draw.py
make build/execute_stage_block_draw build/stage_block_draw_test
./build/stage_block_draw_test
.venv/bin/python tools/observe_stage_block_draw.py
.venv/bin/python tools/verify_stage_block_draw.py
```

`extracted/runtime/stage_block_draw/block_table.ms5d`는 실제 CLI에 전달되어 기존 C++ fixed-data 로더로 읽힌다. MS5D v1/kind1, CPU=ROM`0xddfa4`, payload56바이트, 전체 container88바이트이며 payload는 원본 `[0xddfa4,0xddfdc)`와 일치하고 CRC32도 확인했다. container SHA256은 `6148703a4160af0b0f8514084b222444a57479ba842d8cbed617b200affe034b`다. manifest와 container 모두 verifier의 불변성 감사 입력에 포함된다.

원본40조건과 실제 CLI의 전체RAM·15레지스터·2840개 ordered ports가 일치했다.477a2/ddf9a는 실제 MS5D 파일을 소비하고362a의 live RAM 및 direct35f0은 resource0개로 실행했다. 네 레지스터 profile, canonical table, empty stream, BYTE tile wrap과 WORD offset wrap, direct rectangle 경로를 포함한다. 원본 관측의 RAM/port/stack writes를 감사하고 원본·도구·실행 파일·resources의 불변성을 확인했다. 문서 갱신 시 verifier에 기록된 모든 현재 source/header/CLI/Makefile/resource 입력 hash가 실제 파일과 일치했다.

오류120조건에는 missing/incomplete/late-invalid stream, zero dimension, TRAP 입력, malformed 숫자/파일/리소스, 겹치는 window, 경로/hardlink/symlink 충돌, RAM/resource/두 출력 FIFO와 새 placeholder 정리가 포함된다. 실제 대소문자 비구분 파일시스템의 새 출력 case alias 및 기존 빈 출력 alias도 이 오류 조건에 포함된다. 입력·기존 출력의 보존을 확인했다. CLI의 동일 canonical 경로/inode resource 별칭 중복 제거와 **서로 다른 파일이 같은 payload/address를 공급하는 중복·partial overlap 오류**를 구분한다. 동일 내용의 파일 복사본은 같은 inode가 아니므로 제거하지 않으며, verifier의 distinct duplicate-table 및 partial-overlapping-window 부정 검증이 이 모호성을 확인했다.

검증 보고서는 `artifacts/stage_block_draw/verification.json`, 직접 계산한 SHA256은 `48cb285a61968ae0e55df6d5fdeeb5e90716a1e703e39b8bc9a746ee0f8a55ce`이다. 원본 관측 보고서 `artifacts/stage_block_draw/observation.json`의 SHA256은 `8d40c12dffce8101158a029de56342902e69424ac93f5e75ee63c5c4e2c20fc9`다. observation의 `Cpp_comparison_performed=false`와 verifier의 실제 CLI 비교 성공을 구분한다. 메인의 `make -j4 all test`는 exit0으로 완료했다. `artifacts/stage_block_draw_build_test.log`에서 Python189개 검사, 서로 다른 C++ 테스트 실행 파일136개, `stage_block_draw_test passed`와 warning 진단0개를 직접 확인했다. C++136은 실행 파일 수이며 native fixture 또는 assertion 수와 구분한다.

고립된 oracle stack을 사용하므로 A7/stack/CCR/cycles, 물리 RAM/video mirror, 실제 rendered pixels와 자연 stage scheduler/IRQ는 범위 밖이다. invalid stream·zero dimension·TRAP 입력의 transaction 실패는 원본의 정상 완료 결과라는 주장이 아니다. helper 비교만으로 조작 가능한 게임이나 전체 복원 완료를 주장하지 않는다.

독립 리뷰에서 raw window 시작주소와 WORD 읽기 정렬을 혼동한 검사를 발견하여 수정했다. 홀수 시작주소의 BYTE 조각도 C++ 로더를 통해 읽으며, 홀수 조각이 WORD 범위와 겹치면 ambiguity로 거부한다. 실제 원본 표를 5byte/1byte/나머지로 나눈 추가 CLI 실행도 원본 RAM·15레지스터·137ports와 일치했다. 수정 후 전체 테스트·원본 비교·UBSan 단위 검증을 통과했다. 저장소의 단위 테스트는 합성 레코드를 사용하며 원본 표는 Git에서 제외한 런타임 리소스로만 소비한다.
