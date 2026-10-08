# 47c04 stage activation prefix 인터페이스

원본 의미는 [정적 계약](stage-activation-prefix-contract.md)을 따른다. canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 아래 고정 CPU 주소와 ROM 파일 오프셋은 같다. 이 API의 경계는 `47c04` 진입부터 **`47c6c` 명령 실행 직전**까지다. 원본은 그 지점으로 fall-through하므로 이 결과를 원본 RTS, 전체 callback 실행 또는 stage 활성화 완료라고 부르지 않는다.

## API와 CLI

```cpp
bool initialize_stage_activation_prefix(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,
    ObjectRestartState& state, std::vector<VideoPortWrite>& ports,
    std::string& error);
```

RAM은 CPU `100000..10ffff`에 대응하는 정확히65536바이트다. 상태는 기존 `ObjectRestartState`의 D[8]/A[7]이며 전체15레지스터를 운반한다. A5를 임의로 `108000`으로 바꾸거나 그 값만 허용하지 않는다. 실제로 실행하는 RAM 접근의 span과 WORD/LONG 정렬을 core가 검사한다. A5/A6 필드가 서로 겹치는 경우에도 실제 읽기·쓰기 순서를 보존해야 한다.

```text
build/initialize_stage_activation_prefix \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS [FIXED_MS5D ...]
```

숫자는15개이며 실행명을 포함한 최소 argc는19다. ENTRY 숫자는 받지 않으며 진입은 고정 `47c04`다. 부호 없는32비트 10진수 또는 `0x`/`0X` 16진수를 받는다. 빈 숫자, 부호, 공백, 후행 문자와 범위 초과는 거부한다. 성공 stdout은 한 줄 JSON으로 정확히 `d0..d7`, `a0..a6` 숫자15개만 출력한다. stop PC나 port count를 JSON에 추가하지 않는다. 오류는 stderr에 쓰고 성공 JSON을 출력하지 않는다.

OUTPUT_RAM은65536바이트다. OUTPUT_PORTS는 ordered9바이트 `>BII` 레코드(size1바이트, address/value big-endian32비트)다. 이번 구간에서 출력이 없으면 port 파일은 빈 파일이다.

## 실행 범위와 리소스

core는 `47c04`의 live flag 읽기, 조건부 `9060`/`4e254` RAM 변경, 조건부 `477a2` block 출력, `ca76`/`ca56`, signed BYTE 비교 `c3c0`, object 필드 및 callback 주소 게시를 순서대로 실행한다. 최종 LONG(A6)는 `00047c6c`지만 그 callback의 첫 명령은 실행하지 않는다. 블록 출력이 없는 경로는 해당 helper에 필요한 리소스를 요구하지 않는다.

추가 인자는 각각 기존 MS5D v1 kind1 fixed window 파일이다. 디렉터리 인자가 아니며0개도 전달할 수 있다. 다만 실제 `477a2`가 호출되면 canonical `ddfa4..ddfdc`의9개 레코드와 sentinel을 포함하는 고유 읽기 범위가 필요하다. 기존 `tools/pack_stage_block_draw.py`가 생성하는 `extracted/runtime/stage_block_draw/block_table.ms5d`를 재사용하며 새 리소스 형식이나 packer를 추가하지 않는다.

모든 supplied resource는 실제 경로에서 쓰이는지와 관계없이 C++ `load_fixed_data_resource`로 magic/version/kind/매핑/길이/CRC32를 검사한다. 동일 canonical 경로나 inode를 가리키는 resource 별칭은 중복 로드를 생략한다. 서로 다른 파일의 같은 주소·내용을 임의로 중복 제거하지 않는다. core의 fixed reader는 고유한 complete read를 요구하며 distinct windows의 모호한 중첩과 partial read를 거부한다. fixed CPU=ROM 매핑과 범위, stream 정렬, nonzero dimensions 및 TRAP 검사는 [block-draw 인터페이스](stage-block-draw-execution.md)의 checked helper 범위를 따른다.

실패하면 RAM/state/기존 ports를 보존하며 성공하면 이번 구간의 ports로 교체하는 계약이다. 잘못된 주소·정렬·resource나 원본 TRAP 경로를 정상 완료로 바꾸지 않는다. stack/CCR/cycles, 물리 mirror, rendered pixels, 이후 `47c6c`의 분기·사운드 대기·애니메이션·IRQ 및 자연 게임 도달성은 이 prefix의 범위 밖이다.

## 파일 보호와 I/O 한계

RAM과 모든 resource는 stream/로더를 열기 전에 `stat`/`S_ISREG`로 일반 파일인지 검사하여 FIFO 등 특수 입력을 거부한다. RAM/두 출력의 canonical 경로와 inode 충돌을 거부하며 resource도 RAM 또는 출력의 별칭이면 거부한다. 숫자·입력·resource·core 실패 시 출력 파일을 열지 않는다.

core 성공 후 두 출력을 truncate 없이 `O_WRONLY|O_NONBLOCK|O_CREAT|O_EXCL`로 예약하고 기존 파일은 `O_WRONLY|O_NONBLOCK`으로 연다. 두 descriptor에 `fstat`을 적용하여 일반 파일 여부와 device/inode를 비교하고, 등록한 RAM 및 **모든 resource**의 현재 inode와도 비교한 후에만 truncate/쓰기를 시작한다. 실제 파일시스템에서 발생하는 case alias도 이 비교로 검사하며 파일명 소문자 변환으로 추정하지 않는다.

예약/검사 실패 시 기존 파일은 보존한다. 새로 생성했고 현재 `lstat` identity가 예약한 inode와 같은 placeholder만 제거한다. 두 출력을 순서대로 쓰고 close 결과도 검사한다. 실제 쓰기/close 실패에는 원자적 pair 교체나 이미 쓴 파일의 rollback을 보장하지 않는다.

## 빌드와 검증 상태

Makefile은 CLI를 all에, `stage_activation_prefix_test`를 test에 등록한다. source는 새 `stage_activation_prefix.cpp`와 기존 `stage_block_draw.cpp`, `fixed_data_resource.cpp`다. 관련 header 의존성은 기존 block-draw 목록과 새 prefix header의 sort union으로 관리한다. 공유 state 타입을 얻기 위해 object restart 구현 전체를 링크하지 않는다.

```sh
.venv/bin/python tools/pack_stage_block_draw.py
make build/initialize_stage_activation_prefix build/stage_activation_prefix_test
./build/stage_activation_prefix_test
.venv/bin/python tools/observe_stage_activation_prefix.py
.venv/bin/python tools/verify_stage_activation_prefix.py
```

`tools/observe_stage_activation_prefix.py`는 원본 `47c04`를 patch 없이 실행하고 `47c6c` 실행 전에 멈추는104개 제어 조건을 기록한다. flags, parent BYTE, signed 비교 경계, register profiles와 RAM alias 조건을 포함한다. 실제 CLI와 비교한 primary104조건에서 전체64KiB RAM·15레지스터·ordered ports가 일치했다. verifier는 A5=`108001`/`108002`인 별도 원본 실행2조건도 기록하고 CLI와 비교했다. 기존 primary 중 블록 경로를 타지 않는5조건은 resource0개로 추가 호출하여 원본 결과와 비교했다. 따라서 성공한 CLI 호출은104+2+5=111회이며, 서로 다른 원본 fixture 수와 구분한다. 비교한 ordered ports 총수는6576개다.

원본 전체 RAM 변경은 실제 CPU write replay로 대조했고, parent/helper alias로 인해 나중에 읽는 값이 바뀌는 read trace도 감사했다. canonical block 출력은 실제 `block_table.ms5d`를 CLI에 전달하여 C++ fixed-data 로더를 거쳤다. 동일 canonical 경로/inode resource 별칭은 중복 제거하지만 서로 다른 파일의 중복·partial overlap은 core의 고유 read 검사로 거부한다. A5 shifted 조건의 성공은 고정108000 제한이 없음을 보여 주며, 모든 임의 A5가 유효하다는 뜻은 아니다. 각 실행 경로의 실제 접근이 checked RAM에 맞아야 한다.

오류149조건에는 RAM 크기·숫자 parse·주소/정렬·리소스 오류, missing/directory 입력·출력, 경로/hardlink/symlink 충돌, RAM/resource/두 출력 FIFO, 새 placeholder 정리 및 실제 대소문자 비구분 파일시스템에서의 새 출력 alias와 기존 빈 출력 alias가 포함된다. 실패 시 입력·리소스·기존 출력 보존을 확인했다. 이 실패 검증은 원본 invalid 주소나 TRAP을 정상 실행 결과로 재현했다는 주장이 아니다.

최종 보고서는 `artifacts/stage_activation_prefix/verification.json`이며 직접 계산한 SHA256은 `8d201ba3822457b69673b5ebab5ea663fadeb81889c5aa59d1ff5730617e56ae`다. 원본 관측 `observation.json`의 SHA256은 `d27d39fa7129934db20f0a7735056822e2b27f30a54e474e0609bb3e347c51ce`다. 문서 갱신 시 verifier의 `inputs`15개, `native_inputs`7개, `native_artifacts`425개의 현재 파일 해시가 모두 보고서와 일치했다. 이 확인에는 실행 파일·core/header/CLI·Makefile·실제 MS5D 및 manifest가 포함된다.

메인의 `make -j4 all test`는 exit0으로 완료했다. `artifacts/stage_activation_prefix_build_test.log`에서 Python189개 검사, 서로 다른 C++ 테스트 실행 파일137개, `stage_activation_prefix_test: passed`, warning 진단0개를 직접 확인했다. C++137은 실행 파일 수이며 native fixture 또는 assertion 수가 아니다.

성공 결과는 모두 **STOP before47c6c**의 상태다. 원본 callback은 RTS하지 않았고 `47c6c`의 첫 명령이나 이후 stage frame을 실행한 결과가 아니다. A7/stack은 oracle의 격리된 실행 보조 상태이며 full callback 반환·CCR/cycle·물리 RAM mirror·scheduler/IRQ·rendered pixels·자연 게임 도달성 또는 전체 복원 완료를 입증하지 않는다. 두 출력의 순차 I/O 비원자성 한계도 그대로 남는다.
