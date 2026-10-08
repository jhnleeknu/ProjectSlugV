# 활성화 경로의 작은 helper 인터페이스

원본 의미는 [확정 계약](stage-activation-small-helpers-contract.md)을 따른다. canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 fixed CPU 주소와 ROM 파일 오프셋은 같다. 지원 entry는 `4e216`, `bee`, `16ed2`, `49f8c`다. 각 helper의 실제 RAM·15레지스터와 지정된 carry/ordered PVC 쓰기를 운반하며 상위 callback나 전체 stage 활성화 완료를 뜻하지 않는다.

```cpp
bool execute_stage_activation_helper(std::vector<std::uint8_t>& ram,
    std::uint32_t entry, ObjectRestartState& state, bool& carry,
    std::vector<VideoPortWrite>& ports, std::string& error);
```

RAM은 CPU `100000..10ffff`의 정확히65536바이트, 상태는 `ObjectRestartState`의 D[8]/A[7]이다. `4e216`/`bee`는 반환 carry를 bool로 설정한다. `16ed2`/`49f8c`는 carry 입력 bool을 보존하며 그 entry의 CCR을 모델링하지 않는다. 오류는 RAM/state/carry/기존 ports를 보존하고 성공은 이번 호출의 ordered ports로 교체한다. 실제 도달하는 span과 WORD/LONG 정렬만 검사한다. 24bit mirror나 임의 주소 wrapping을 제공하지 않는다. 리소스와 대기 continuation은 없다.

## CLI

```text
build/execute_stage_activation_helper ENTRY \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS
```

숫자는 ENTRY를 포함해16개이며 실행명을 포함한 argc는 정확히20이다. RAM input/output/port 경로는 argv17/18/19다. 별도 carry 입력이나 resource 인자는 없다. 모든 숫자는 부호 없는32비트 10진수 또는 `0x`/`0X`16진수다. 빈 숫자, 부호, 공백, 후행 문자와 overflow를 거부하며 entry 지원 여부는 core가 검사한다.

성공 stdout은 정확히16개 key의 한 줄 JSON이다. `d0..d7`, `a0..a6` 숫자15개와 `carry`를 출력한다. `4e216`/`bee`의 carry는 boolean이며 **`16ed2`/`49f8c`에서는 null**이다. API의 보존된 bool을 이 두 entry의 원본 CCR 결과처럼 출력하지 않는다. ENTRY나 port count를 JSON에 추가하지 않는다. 오류는 stderr에 쓰며 성공 JSON을 출력하지 않는다.

OUTPUT_RAM은65536바이트다. OUTPUT_PORTS는 기존 ordered9바이트 `>BII`(size1바이트, address/value big-endian32비트)이며 `49f8c`의 두 WORD 쓰기 외 entry는 빈 파일이다.

## 각 helper의 실제 효과

`4e216`은 BYTE(A5-75bc)를 D0.byte에 읽고0/5일 때만 BYTE(A5-74f8)를 추가로 읽는다. 두 상태가 모두0/5일 때carry1이고 그 외carry0이다. D0에는 실제 마지막으로 읽은 BYTE가 남으며 상위24bit와 다른 레지스터/RAM은 보존한다. 두 번째 주소를 읽지 않는 조기반환은 그 주소의 유효성을 요구하지 않는다. BYTE 접근이므로 홀수 A5 자체를 거부하지 않는다.

`bee`는 absolute RAM10f004의 요청 BYTE를 D0.byte에 읽고 해당 BYTE를0으로 만든다. A0=10fdb6에서 첫 상태 BYTE를 D1.byte로 읽고 A0를 증가시킨다. 값1/2이면 요청을 복원하고carry1이다. 아니면 둘째 BYTE도 읽고 A0를 다시 증가시키며, 값1/2이면 복원/carry1, 아니면 요청을0으로 두고carry0이다. 최종 A0는 첫 성공이면10fdb7, 둘째를 읽으면10fdb8이다. D0/D1 상위24bit와 D2..D7/A1..A6는 보존한다. A5 값과 무관한 absolute RAM 연산이며 인접 BIOS/helper를 실행하지 않는다.

`16ed2`는 WORD(A5+d3e)를 D0.low에 읽어 상위WORD를 보존하고 WORD(A5+d46)와 signed16bit 비교한다. 미만이면 BYTE(A6+15)의 bit2를 세우고 이상이면 지운다. 다른 bits와 레지스터는 보존한다. 두 WORD 읽기가 flag 쓰기보다 먼저이므로 alias여도 순서를 유지한다. A6는 실제 flag BYTE 접근만 유효하면 홀수도 허용한다.

`49f8c`는 A0=A6+26, BYTE(A6+18)=0, WORD(A5-7ff0)=0, WORD1000→2ffff2, WORD0→2ffff0의 순서다. A5가108000이 아니면 원본 TRAP15 경로이므로 API는 transactional 오류를 반환한다. 정상 경로는 LONG(A0)=A1, WORD(A0+4)=0, WORD(A0+6)=D0.low를 순서대로 쓴다. A0만 변경되며 D0..D7/A1..A6는 보존된다. A1은 저장할 script pointer일 뿐 이번 helper가 dereference하지 않으므로 별도 script resource나 pointer 검증을 요구하지 않는다.

A6가 RAM object 시작주소여야 한다는 추가 제한은 없다. 예를 들어 A6=fffea이면 A0=100010으로 state와 bank shadow가 겹치며, 초기 clear 뒤 A1 LONG쓰기의 실제 순서를 유지한다. 최종 shadow를 다시0으로 만들거나 PVC 쓰기를 추가하지 않는다. 잘못된 span/정렬/TRAP의 checked 실패를 원본의 정상 완료와 같은 결과라고 주장하지 않는다. 후속 `49fc6` 실행과 sprite 대기는 별도 범위다.

## 파일 보호와 I/O 한계

INPUT_RAM은 열기 전에 `stat`/`S_ISREG`로 일반 파일임을 검사하여 FIFO 등 특수 입력을 거부한다. RAM/두 출력의 canonical 경로 또는 inode가 같으면 거부한다. 숫자·입력·core 실패 시 output을 열지 않는다.

core 성공 후 두 출력을 truncate 없이 nonblocking으로 예약한다. `fstat`으로 두 파일의 일반 파일 여부와 device/inode를 비교하고 input의 현재 inode와도 대조한 뒤에만 truncate/쓰기한다. 실제 case alias도 inode로 검사한다. 예약/검사 실패 시 기존 파일은 보존하며 이번 호출에서 새로 생성했고 현재 `lstat` identity가 예약 inode와 같은 placeholder만 제거한다. write/close를 검사하지만 실제 I/O 실패에는 두 출력의 원자적 교체나 rollback을 보장하지 않는다.

## 빌드와 검증 상태

Makefile은 CLI를 all에, `stage_activation_helpers_test`를 test에 등록한다. 새 `stage_activation_helpers.cpp` 하나와 관련 header, `object_restart_execution.h`, `video_port.h`를 의존성으로 갖는다. inline state 생성자를 사용하므로 object restart 구현 전체를 링크하지 않는다. 별도 runtime packer도 필요하지 않다.

```sh
make build/execute_stage_activation_helper build/stage_activation_helpers_test
./build/stage_activation_helpers_test
.venv/bin/python tools/observe_stage_activation_helpers.py
.venv/bin/python tools/verify_stage_activation_helpers.py
.venv/bin/python tools/verify_stage_activation_helpers.py --audit-only
make -j4 all test
```

원본 관측 `artifacts/stage_activation_helpers/observation.json`은441조건(`4e216`108, `bee`108, `16ed2`150, `49f8c`75)을 기록한다. SHA256은 `ed26b6cc85ec93c777f211d1fa1d184eeb965659cbaec281116ed7bb4a28b0cf`다. 관측 자체의 `Cpp_comparison_performed=false`와 별도로, 최종 `artifacts/stage_activation_helpers_execution/verification.json`은 이441조건을 원본에서 다시 실행하고 CLI 결과와 비교했다. 여기에 A5=1175bb에서 잘못된 두 번째 BYTE 주소를 읽지 않는 `4e216` 원본 조기반환2조건을 추가하여 총443조건의 전체64KiB RAM·15레지스터·지정된 carry와 ordered ports가 일치했다. ordered PVC 쓰기는150개이며, 정상 조건분기9개의 양쪽 결과를 관측했다. `49f8c`의 A5 TRAP guard는 정상 쪽만 native 비교했다. `bee`의 native A5 fixture는0과ffffffff다.

최종 보고서 SHA256은 `4600addebfe6aed363c07387ee9d5e13fa9f4c4ef241199931e33806718fa07a`이며155개 negative 검사가 입력·출력 보존을 확인했다. FIFO, parser/span/정렬/TRAP 오류, 기존·신규 출력 alias 및 새 placeholder 정리를 포함한다. 이 실행 환경의 case-insensitive 파일시스템에서 새 두 출력의 case alias 거부와 기존 zero-length alias 출력 보존도 확인했다. 보고서의 구현 입력9개, native 입력7개와 native artifact1774개의 현재 SHA256을 대조했으며 모두 일치했다. 비교 CLI 바이너리 SHA256은 `54b43378e2de704d16e7cc0d0c5370e7b08c4b3d88e816be965686c092ce5717`이다.

API 단위 회귀에는 `49f8c`의 A6=10ffd4가 포함된다. A0=10fffa의 LONG과 A0+4의 timer WORD까지 candidate에 기록한 뒤 마지막 A0+6=110000의 speed WORD span이 실패한다. incoming carry가 false/true인 두 경우 모두 전체 RAM·15레지스터·carry와 기존 ports가 보존됨을 검사한다. 이는 원본의 잘못된 접근 완료와의 동등성 주장이 아니라 API의 늦은 실패 rollback 증거다. `16ed2`/`49f8c`의 성공 carry 보존도 별도 API 단위 증거이며, CLI에서는 계속 null로 표시한다.

전체 `make -j4 all test`는 exit0으로 완료했다. `artifacts/stage_activation_helpers_build_test.log`에는 Python196 tests와 C++ 실행142개가 기록되어 있으며 경고는0개다. core의 별도 normal/UBSan 단위 실행도 통과했다.

A7/stack/CCR전체/cycles, 물리 RAM/PVC mirror, 자연 IRQ/scheduler, 직접 플레이와 전체 복원 완료는 이 작은 helper의 증거 범위 밖이다. 반환 carry만 지정한 두 entry와 CCR을 제공하지 않는 두 entry를 구분한다.
