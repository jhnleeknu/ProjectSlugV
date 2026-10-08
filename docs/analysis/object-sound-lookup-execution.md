# Object sound lookup 실행 인터페이스

[원본 계약](stage-object-output-wrappers-contract.md)의 fixed CPU `47672..476ba`, `ca70`과 실제 `3af8` sound continuation을 연결한다. canonical BE ROM SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 fixed CPU 주소는 ROM 파일 오프셋과 같다. 이 wrapper의 검증을 전체 object callback나 stage 활성화 완료로 확대하지 않는다.

```cpp
struct ObjectSoundLookupState {
    SoundWordExecutionState sound;
    std::uint32_t a5, a6;
    unsigned int phase;
    std::uint32_t saved_a0;
};
bool execute_object_sound_lookup(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,
    ObjectSoundLookupState& state, std::uint8_t external_status,
    std::uint8_t& external_reads, std::string& error);
```

RAM은 CPU `100000..10ffff`의 정확히65536바이트다. `sound.byte.registers`의 D[8]/A[5]가 D0..D7/A0..A4의 유일한 상태이며 별도 A5/A6를 함께 전달한다. 오류는 전체 RAM·15레지스터·continuation metadata·external_reads를 보존한다. phase0은 idle이며 saved_a0/sound.phase/saved_low가0이고 waiting=false여야 한다. phase1은 saved A0와 sound phase1/2의 captured wait를 보관하며 waiting=true여야 한다. core가 상태 조합을 검사한다.

## CLI

```text
build/execute_object_sound_lookup \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  PHASE SAVED_A0 SOUND_PHASE SAVED_LOW WAITING EXTERNAL \
  INPUT_RAM OUTPUT_RAM [FIXED_MS5D ...]
```

숫자는21개이며 argc는 최소24다. INPUT_RAM은 argv22, OUTPUT_RAM은 argv23, resource는 argv24 이후다. ENTRY나 port 경로는 없다. register와 SAVED_A0는 unsigned32bit, PHASE0..1, SOUND_PHASE0..2, SAVED_LOW/EXTERNAL0..255, WAITING0..1을 받는다. 숫자는 10진수 또는 `0x`/`0X`16진수이며 부호·공백·빈 숫자·후행 문자·overflow를 거부한다.

성공 stdout은 정확히21개 key의 한 줄 JSON이다. 숫자 `d0..d7`, `a0..a6`, `phase`, `saved_a0`, `sound_phase`, `saved_low`, `external_reads`와 boolean `waiting`을 출력한다. OUTPUT_RAM은65536바이트다. 오류는 stderr와 실패 종료 코드로 보고하며 성공 JSON을 출력하지 않는다.

## 실행 순서와 continuation

fresh에서 ca70의 A0=A5−76a4를 계산하여 BYTE(A0)를 D0.byte에 읽고 BYTE(A6+7e)와 비교한다. 다르면 A0를 보관하고 D0.low=1ac0으로 기존 full sound-word API를 호출한다. 실제 sound 호출/재개는 기존 callee의 A5-relative queue 지원 한계에 따라 A5=108000을 요구한다. sound를 건너뛰는 경로는 실제 reached RAM span을 검사한 arbitrary A5/A6를 허용한다.

sound 대기 시 phase1과 saved A0를 유지한다. 다음 호출은 직전 실제 출력 RAM·15레지스터·metadata를 전달한다. resume는 sound만 이어가며 앞 상태 비교/명령 제출을 반복하지 않는다. 대기가 유지되면 lookup resource를 소비하지 않으므로 resource0개가 허용된다. sound가 완료되면 saved A0를 복원하고 phase/saved_a0를0으로 되돌린 뒤 lookup을 실행한다. EXTERNAL은 callee의 조건부 `d00046` 읽기에만 전달되며 external_reads는 이번 호출의 실제 읽기 수다.

완료부는 live BYTE(A0)를 BYTE(A6+7e)에 쓴 뒤 live WORD(A0)를 D1.low에 읽는다. destination이 A0/A0+1과 겹칠 때도 쓰기 후 WORD 값을 사용한다. D1.byte의 ADD.B 자기 덧셈에서 signed overflow가 나는 원래 BYTE40..bf는80으로 덮고, 그 외는 modulo256 두 배를 유지한다. D1.low&=00fe 뒤 A0=4411e, WORD(A0+D1.W)를 읽어 WORD1을 뺀다. 원본 WORD0이면 borrow에 따라 D1 전체를0으로 만들고, 그 외 D1 상위WORD를 보존한다. 마지막 D1.byte를 BYTE(A6+12)에 쓴다. 실제 BYTE/WORD span과 WORD 정렬만 검사하며 임의 object-pool 제한을 추가하지 않는다.

## 런타임 resource

`tools/pack_object_sound_lookup.py`는 원본 `[4411e,4421e)`256바이트를 기존 MS5D v1 kind1 fixed-window container와 metadata로 제공한다. 모든 짝수 index00..fe의128 WORD 조회를 보존하며128개의 논리적 object나 숫자 테이블이라고 단정하지 않는다. raw ROM이나 추출 resource는 Git에 넣지 않는다.

CLI는 공급한 모든 resource를 기존 `load_fixed_data_resource`로 읽어 형식/범위/CRC를 검증한다. 대기 중 resource가 필요하지 않아도 공급한 잘못된 파일을 무시하지 않는다. resource 간 같은 canonical 경로/inode는 한 번만 로드하며, 서로 다른 파일의 겹치는 WORD 창은 해당 접근이 실제로 도달할 때 core의 missing/partial/ambiguous 검사를 따른다. 종료 lookup이 도달하면 그 WORD 전체를 제공하는 유일한 유효 fixed window가 필요하다. 새 ROM resource format이나 banked reader를 추가하지 않는다.

실제로 로드한 `extracted/runtime/object_sound_lookup/lookup.ms5d`는 payload256바이트/container288바이트다. payload SHA256은 `eea1eddb352dfc10643395459d1afbd26ad22d1c5d3aa5c0fdf312052e458649`, CRC32는 `7344c719`, container SHA256은 `b8fb48ea03880f2285abf550e43cae731889b3545e1241b48074dcc05a3e6b7e`다. 현재 파일을 manifest와 직접 대조했다.

## 파일 보호와 I/O 한계

RAM과 모든 resource는 열기 전에 stat/S_ISREG로 일반 파일임을 검사하여 FIFO 등 특수 입력을 거부한다. output은 RAM/resource와 canonical 경로나 inode가 같으면 거부한다. parser·입력·loader·core 실패 시 output을 열지 않는다.

core 성공 후 output을 truncate 없이 O_NONBLOCK으로 예약하고 fstat으로 일반 파일임을 확인한다. 예약 inode를 모든 입력의 저장된 identity 및 현재 inode와 비교한 뒤에만 truncate/쓰기한다. 실제 case alias도 inode로 확인한다. 예약/검사 실패 시 기존 파일을 보존하며 새 placeholder는 현재 lstat identity가 예약 inode와 같은 경우에만 제거한다. write/close를 검사하지만 실제 I/O 실패 시 output의 원자적 교체나 rollback을 보장하지 않는다.

## 재현과 검증 상태

Makefile all/test는 CLI와 `object_sound_lookup_test`를 등록한다. core source는 `object_sound_lookup.cpp`와 기존 `sound_word_execution.cpp`/`sound_byte_execution.cpp`이며 CLI에 `fixed_data_resource.cpp`를 추가한다. 관련 sound/fixed header 의존성을 재사용한다. runtime-resources는 새 packer를 호출한다.

```sh
.venv/bin/python tools/pack_object_sound_lookup.py
make build/execute_object_sound_lookup build/object_sound_lookup_test
./build/object_sound_lookup_test
.venv/bin/python tools/observe_object_sound_lookup.py
.venv/bin/python tools/verify_object_sound_lookup.py
make -j4 all test
```

원본 관측 `artifacts/object_sound_lookup/observation.json` SHA256은 `42f093ee7d31dbd3e70b986dd7d7edd7fc409eeb543892ff5c3c6d4494e99f5d`다. 최종 비교는 수정하지 않은47672/ca70/3af8을 다시 실행하여277조건·291phase의 전체64KiB RAM·15레지스터·continuation/external_reads를 실제 CLI와 대조했다. 같은 native CPU를 유지한6개 chain의14개 resume는 직전 실제 C++ 출력과 명시된 host RAM 변경, EXTERNAL255만을 다음 호출에 전달했다.14개 waiting phase는 resource 없이 실행했다. 실제 raw lookup의128개 짝수 WORD 주소 모두를 관측했으며 lookup 읽기는277회다.

163개 negative 검사는 parser/continuation, RAM span/정렬, missing/corrupted resource, FIFO·alias와 늦은 실패의 입력·기존 출력 보존을 확인했다. 수정된 late WORD fixture는 A5=108001/1176a3에서 먼저 object 비교 BYTE를 source와 같게 만들어 sound를 건너뛴 뒤, live BYTE 쓰기 이후 WORD의 홀수 정렬/끝 경계를 실패시킨다. A6=fffa0도 비교 BYTE가 같도록 준비하여 마지막 output BYTE가 RAM 아래로 벗어나는 늦은 실패를 실제로 도달한다. 초기 비교 실패나 지원하지 않는 A5 sound 오류를 late WORD 검증으로 오인하지 않는다. 별도 API 단위 검사는 duplicate/partial/overlap window의 거부를 확인하며, 이를163개 CLI negative 검사에 포함된 것으로 기록하지 않는다.

최종 `artifacts/object_sound_lookup_execution/verification.json` SHA256은 `785bc6249e24f89fc96fa69fabe5365d1cbe2871948a33b07f5e9d58eec2d0b5`다. corrected late WORD fixture와 간접 header 입력을 포함한 현재 보고서를 기준으로 하며 이전 `e5d110...` 보고서는 대체되었다. 구현·도구·resource 입력18개와 native/C++ artifact1172개의 현재 SHA256 총1190개를 대조했으며 모두 일치했다.

전체 `make -j4 all test`는 exit0으로 완료했다. `artifacts/object_sound_lookup_build_test.log`에는 Python205 tests, C++ 실행144개와 경고0개가 기록되어 있다. 새 packer의 synthetic 검사는9개이며 core의 별도 normal/UBSan 단위 실행도 통과했다. sound gate 전체 분기를 이 wrapper 관측만으로 검증했다고 주장하지 않는다.

A7/stack·CCR전체·cycles, banked reader·임의 A5 sound, 자연IRQ/scheduler, 물리mirror, 직접 플레이와 전체 재구성 완료는 이 wrapper의 증거 범위 밖이다. checked 오류는 원본의 잘못된 접근 완료 동등성을 뜻하지 않는다.
