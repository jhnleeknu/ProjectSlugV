# ca9e/caf0 전체 레지스터 화면 초기화 인터페이스

원본 의미는 [전체 레지스터 계약](screen-reset-full-contract.md)을 따른다. canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 고정 CPU 주소 `0x00ca9e/0x00caf0`는 동일 ROM 파일 오프셋이다. 이 API는 화면 초기화 helper의 RAM·15레지스터·ordered ports를 제공한다. 실제 렌더링 화면이나 이후 stage callback 전체의 완료를 뜻하지 않는다.

## API와 CLI

```cpp
bool reset_game_screen_full(std::vector<std::uint8_t>& ram,
    std::uint32_t entry, ObjectRestartState& state,
    std::vector<VideoPortWrite>& ports, std::string& error);
```

선언은 `ms5/game_screen_reset_execution.h`, 구현은 기존 `engine/src/game_screen_reset.cpp`에 둔다. 별도의 새 core 소스를 추가하지 않는다. 기존 부분 레지스터 API `reset_game_screen`과 full API는 port 생성 코드를 공유하되 기존 API 계약을 유지한다. 상태는 `ObjectRestartState`의 D[8]/A[7]이며 object restart를 실행한다는 뜻은 아니다.

```sh
make build/reset_game_screen_full
```

```text
build/reset_game_screen_full ENTRY \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS
```

ENTRY를 포함한 숫자는16개, 필수 argc는 실행명을 포함해20이다. 추가 인자는 거부한다. 부호 없는32비트 10진수 또는 `0x`/`0X` 16진수를 받으며 부호, 공백, 빈 숫자, 후행 문자, 범위 초과를 거부한다. ENTRY는 core에서 `0xca9e` 또는 `0xcaf0`만 허용한다. 입력 RAM은 CPU `0x100000..0x10ffff`에 대응하는 정확히65536바이트다. 리소스/TABLE 인자는 없다.

성공 stdout은 한 줄 JSON이며 정확한 키는 `d0..d7`, `a0..a6`이고 값은 모두 숫자다. ENTRY, write count나 별도 상태 키를 추가하지 않는다. 반환 레지스터는 caller의 후속 상태로 그대로 전달한다. 실패 시 stderr에 진단을 쓰고 성공 JSON을 출력하지 않는다.

## 원본 효과와 A5 지원 범위

ca9e는773개의 video write를 반환하고 RAM을 변경하지 않는다. D0=`0x7580ff02`, D1=0, A4=`0x3c0000`, D7은 입력 상위WORD와 하위WORD`0xffff`가 된다. D2..D6/A0..A3/A5/A6를 보존한다. A5를 역참조하지 않으므로 ca9e의 incoming A5는 임의의32비트 값이 가능하다.

caf0는 ca9e 이후 원본35a2를 다섯 번 호출하는 고정 rectangle 효과를 연결한다. rectangle 순서는 `(7021,00ff,38,30)`, `(701f,7000,40,1)`, `(7000,7000,40,1)`, `(7000,7000,1,32)`, `(74e0,7000,1,32)`다. 각 rectangle은 watchdog BYTE, column-major video LONG writes, WORD`3c0004=0`, LONG`3c0000=82000000`을 기록한다. 전체2072개 ports의 순서를 보존한다. 임의 rectangle 입력이나35a2 TRAP 경로는 노출하지 않는다.

caf0 최종 레지스터는 D0=`0x75807500`, D1=`0x7000`, D2=0, D3=32, D6=입력 상위WORD|0, D7=`0x75007000`, A4=`0x3c0000`이다. D4/D5/A0..A3/A5/A6는 보존한다. 마지막 CLR.B의 목적지는 `A5-0x769a`이며 이1바이트가 지원 RAM 안에 있어야 한다. 따라서 caf0의 지원 A5 범위는 **`0x10769a..0x117699` 양끝 포함**이다. BYTE 목적지는 홀수 주소도 허용하며 WORD 정렬 조건을 적용하지 않는다. A5=`0x108000`이면 CPU`0x100966`에0을 기록한다. 범위 밖 caf0 A5를 임의 wrap 또는 고정966 쓰기로 정규화하지 않고 실패한다.

C++ API 실패 시 RAM,15레지스터와 기존 ports를 모두 보존한다. 성공 시 ports는 이번 호출의 새 writes로 교체한다. 원본 CCR/cycle/A7·stack·물리 mirror와 실제 픽셀 동등성은 이 인터페이스의 주장 범위 밖이다.

## ports와 파일 보호

OUTPUT_PORTS는 기존9바이트 `>BII` 레코드다. size1바이트 뒤 address/value가 각각 big-endian32비트로 이어진다. width·address·value·순서 전체를 보존하며 RAM 출력은65536바이트다.

입력은 stream을 열기 전에 `stat`/`S_ISREG`로 일반 파일인지 검사하여 FIFO 등 특수 입력을 거부한다. 입력 RAM과 두 출력의 canonical 경로 또는 inode가 같으면 거부한다. RAM 크기 검사와 core 실행 성공 전에는 출력 파일을 열지 않는다.

core 성공 후 두 출력을 `O_WRONLY|O_NONBLOCK|O_CREAT|O_EXCL`로 예약하고 기존 파일은 `O_WRONLY|O_NONBLOCK`으로 열며 truncate하지 않는다. 두 descriptor가 일반 파일인지 `fstat`으로 검사하고 실제 device/inode를 서로 비교하며 입력 RAM의 `stat` identity와도 비교한다. 검사 후에만 truncate와 쓰기를 수행하므로 아직 없는 두 출력 이름의 대소문자 별칭도 실제 파일시스템의 inode로 검출한다. FIFO 출력에도 대기하지 않는다.

예약/검사 실패 시 기존 파일을 보존하고 이번 호출에서 생성했으며 현재 `lstat` identity가 예약한 inode와 같은 placeholder만 제거한다. RAM과 ports는 순차적으로 쓰고 close 결과도 검사한다. 실제 쓰기/close 실패에는 두 출력의 원자적 교체나 이미 수행한 변경의 rollback을 보장하지 않는다.

## 빌드 연결과 검증 상태

Makefile은 새 CLI와 `game_screen_reset_execution_test`를 all/test에 등록한다. 기존 screen reset의 직접 target과 해당 소스를 컴파일하는 GAME_RESTART, GAME_READY, SCENE_INITIALIZATION, STAGE_TRANSITION, SCENE_UPDATE의 header 집합은 공통 `GAME_SCREEN_RESET_HEADERS`를 사용한다. 이 집합에 기존 header, 새 full API header, ObjectRestartState header와 VideoPortWrite header를 포함하므로 상위 source/header union에도 변경 의존성이 전달된다. 기존 API의 source와 테스트 의존성은 유지한다.

재현 명령은 다음과 같다. observation 생성은 원본 실행만 수행하고, verifier가 그 관측 artifact를 감사한 뒤 실제 full CLI와 비교한다.

```sh
make all test
.venv/bin/python tools/observe_screen_reset_full.py
.venv/bin/python tools/verify_screen_reset_full.py
```

전체 빌드/test 로그 `artifacts/screen_reset_full_build_test.log`에서 서로 다른 C++ 테스트 실행 파일135개의 실행과 `game_screen_reset_execution_test passed`를 확인했다. 이 수는 테스트 실행 파일 수이며 원본 fixture 수나 assertion 수가 아니다.

원본 관측32조건(ca9e/caf0 각각16개)과 실제 CLI의 RAM65536바이트·전체15레지스터·45520개 ordered watchdog/video ports가 일치했다. 네 레지스터 profile, ca9e의 임의 A5, caf0의 A5-relative BYTE 양끝 경계와 홀수 목적지를 포함한다. 원본 RAM/port/stack write artifact를 replay·감사하고 원본·native artifacts·실행 파일·검증 도구의 불변성을 확인했다. 보고서의 입력 hash는 문서 갱신 시 실제 CLI/core/header/Makefile과 모두 일치했다.

오류134조건은 잘못된 숫자/argc/RAM 크기·entry·caf0 A5 범위, 경로/hardlink/symlink 충돌, 입력/RAM 출력/port 출력 FIFO, 두 번째 예약 실패 시 새 placeholder만 정리하는 조건을 포함하며 입력과 기존 출력을 보존했다. 별도로 실제 대소문자 비구분 파일시스템에서 두 새 출력의 case alias 거부와 기존 빈 alias 출력 보존 회귀를 확인했다.

검증 보고서는 `artifacts/screen_reset_full/verification.json`, 직접 계산한 SHA256은 `eb27509b0fa14a529a230df257fa9aab600b535afead2fb8577c23606bf7a9bf`다. 원본 관측 보고서 `artifacts/screen_reset_full/observation.json`의 SHA256은 `26f2944f354460b3a9b48768e930003a323aa2491c36ae981b9ce0fcefc6b349`다. observation 자체의 `Cpp_comparison_performed=false`와 verifier의 실제 C++ 비교 성공을 구분한다.

이 검증은 고립된 oracle stack `0x1feffc`를 비교 RAM 밖에 둔다. stack writes는 감사했지만 A7/stack/CCR는 CLI 상태가 아니며 물리 RAM mirror·video mirroring·실제 렌더링 픽셀·cycle·scheduler 동등성을 주장하지 않는다. ca9e/caf0 helper 비교 통과만으로 `47af0` 이후 stage 활성화, 자연 IRQ/scheduler, 조작 가능한 게임, 화면·오디오 동등성 또는 전체 복원 완료를 주장하지 않는다.
