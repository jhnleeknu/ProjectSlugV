# 4847c stage readiness 인터페이스

후속 readiness의 공유 stack·실제 carry 분기 연결은 `animation-machine-readiness-execution.md`를 따른다. `93b5b40` 이후47d20→47d3e→4847c→47d42를 연결했다. 아래 수치와 지원 경계는 각 이전 단위의 기록이며 최신 구현 상태와 구분한다.

원본 의미는 [확정 계약](stage-readiness-contract.md)을 따른다. canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 아래 fixed CPU 주소와 ROM 파일 오프셋은 같다. 이 API는 `4847c`에서 실제 호출하는 `1bdde`/`289e`/`4dee2`/`4e166`을 연결한 전체15레지스터·반환 carry 효과를 제공한다. `47c6c` callback 또는 자연 stage 실행 전체를 뜻하지 않는다.

```cpp
bool execute_stage_readiness(const std::vector<std::uint8_t>& ram,
    ObjectRestartState& state, bool& carry, std::string& error);
```

RAM은 CPU `100000..10ffff`의 정확히65536바이트이며 읽기 전용이다. 상태는 `ObjectRestartState` D[8]/A[7]과 별도 bool carry다. 실패 시 state/carry를 보존하며 RAM은 변경하지 않는다. 실제 도달하는 RAM read의 span과 WORD/LONG 정렬만 검사하며 skipped 경로를 미리 검사하지 않는다. A5는108000으로 강제하지 않고 실제 접근이 지원 RAM에 맞으면 임의 값을 보존한다. 24bit mirror나 임의 wrapping은 제공하지 않는다. 외부 리소스·MMIO·ports는 없다.

## CLI와 파일 보호

```text
build/execute_stage_readiness \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  INPUT_RAM OUTPUT_RAM
```

숫자는15개이며 실행명을 포함한 argc는 정확히18이다. ENTRY/resource/port/carry 입력 인자는 없다. 부호 없는32비트 10진수 또는 `0x`/`0X`16진수를 받고 빈 숫자, 부호, 공백, 후행 문자와 overflow를 거부한다. 성공 stdout은 정확히16개 key의 한 줄 JSON으로 `d0..d7`, `a0..a6` 숫자15개와 `carry` boolean을 출력한다. OUTPUT_RAM은 입력과 동일한65536바이트이며 명시적인 fixture 출력을 제공한다. 오류는 stderr에 쓰고 성공 JSON을 출력하지 않는다.

INPUT_RAM은 열기 전에 `stat`/`S_ISREG`로 일반 파일임을 검사하여 FIFO 등 특수 입력을 거부한다. input/output의 canonical 경로나 inode가 같으면 거부한다. 숫자·입력·core 실패 시 output을 열지 않는다.

core 성공 후 output을 truncate 없이 `O_WRONLY|O_NONBLOCK|O_CREAT|O_EXCL`로 예약하고 기존 파일은 `O_WRONLY|O_NONBLOCK`으로 연다. `fstat`으로 일반 파일 여부를 확인하며 처음 검사한 input inode와 쓰기 직전 input의 현재 inode를 모두 대조한 뒤에만 truncate/쓰기한다. hardlink/symlink/case alias도 실제 identity로 검사한다.

예약/검사 실패 시 기존 파일을 보존하며 이번 호출에서 새로 생성했고 현재 `lstat` identity가 예약 inode와 같은 placeholder만 제거한다. write의 EINTR을 재시도하고 close 결과도 검사한다. 실제 truncate/write/close 실패에는 원자적 교체나 이미 수행한 출력 변경의 rollback을 보장하지 않는다.

## 호출 순서와 반환 상태

`4847c`는 D0 전체를0으로 설정하여 첫 `1bdde`를 호출한다. carry0이면 바로 최종carry0으로 반환한다. 통과하면 D0 전체를1로 설정하여 둘째 `1bdde`를 호출하고, 이 결과도carry0이면 최종carry0이다. 둘 다carry1이면 BYTE(A5+5684)를 읽어 비영일 때carry1,0일 때만 `4e166`의 mask를 구하고 D0.byte의 비영 여부를 반환한다.

`1bdde`는 D0.low&1로 A0=`A5-7348`/`A5-7258`을 선택하고 `289e`의 LONG marker270e 비교를 사용한다. marker가270e이거나 object+a8 bit4가 켜졌으면carry1이다. 그 외 object+61 bit7이 켜졌으면carry0이다. 남은 경로만 `4dee2`를 호출하며 그 carry0이면carry1, carry1일 때 D1.byte3/4/5이면carry0, 그 외에는carry1이다.

`4dee2`는 A4=`A5+5d12`/`A5+5d18`을 선택한다. WORD(A4+4)의 부호bit가 켜지면carry0, 그 외 BYTE(A4)가1/2일 때만 BYTE(A4+2)를 D1.byte에 읽고carry1이다. D1 상위24bit는 보존하며 나머지 type은 D1을 변경하지 않는다. 해당 WORD read의 실제 정렬과 complete span이 필요하다.

`4e166`은 D0 전체를0으로 만든 뒤 BYTE(A5-75bc)==2이면bit0, BYTE(A5-74f8)==2이면bit1을 세운다. 두 BYTE를 순서대로 모두 읽으며 D0 전체가0..3이 된다. 이 mask의 숫자 결과와 `4847c`의 최종carry를 구분한다. 조기반환에 따라 D0/D1/A0/A4의 최종값과 실제 접근이 달라지므로 bool 결과만 계산하고 scratch 레지스터를 무시하지 않는다.

## 빌드와 검증 상태

Makefile은 CLI를 all에, `stage_readiness_test`를 test에 등록한다. source는 새 `stage_readiness.cpp` 하나이며 header는 `stage_readiness.h`, `object_restart_execution.h`, `video_port.h`다. inline state 생성자만 사용하므로 object restart 구현 전체를 링크하지 않는다. runtime packer도 필요하지 않다.

```sh
make build/execute_stage_readiness build/stage_readiness_test
./build/stage_readiness_test
.venv/bin/python tools/observe_stage_readiness.py
.venv/bin/python tools/verify_stage_readiness.py
```

원본 관측 `artifacts/stage_readiness/observation.json`은214개 제어 조건,19개 조건 분기의 양쪽 결과,전체64KiB RAM·15레지스터·실제 RTS 이후 carry를 기록한다. 원본 helper를 stub으로 대체하거나 host carry로 덮어쓰지 않는다. SR은 A7보다 먼저 설정하고 hook에서 SR을 읽지 않는다. RAM 변경이 없고 실제 CPU writes는 격리된 guarded stack에만 있음을 감사했다. 두 skipped-invalid-address fixture와 shifted A5를 포함하며10조건은 pinned Musashi와도 RAM·15레지스터·carry를 교차 대조했다.

원본 관측의 SHA256은 `45ad59018ae534c4059d6348dc835e09d37d9d08dbc3554e2562c7cfe90a4844`다. 원본 관측 자체는 `Cpp_comparison_performed=false`이며, 별도 `tools/verify_stage_readiness.py`가214조건 모두를 실제 원본 CPU에서 다시 실행하고 실제 CLI와 전체64KiB RAM·15레지스터·반환 carry를 비교하여 일치를 확인했다. readiness 의미를 중복 구현한 host 알고리즘을 expected oracle로 사용하지 않는다. 성공 JSON도 정확히16개 key(15레지스터+carry)이며 count나 추가 상태를 출력하지 않는다.

반환 carry는 false128조건/true86조건이다. 조건 분기19개의 양쪽 결과와 native RAM operand read2170개, JSR/RTS stack write1121개의 순서를 감사했다. selected10조건의 pinned Musashi 교차 비교 근거도 보존한다. 실제 출력 RAM은 항상 입력과 같으며 새로운 output 파일 생성도 native 결과와 일치했다.

오류120조건에는 숫자·RAM 크기·파일 인자, 실제 도달하는 RAM span과 정렬, late helper 오류, input/output 경로·hardlink·symlink·실제 대소문자 비구분 alias, input/output FIFO 및 잘못된 입력 후 새 output 미생성 검사가 포함된다. 입력·기존 출력과 API state/carry 보존을 확인했다. odd A5는 첫 LONG read에서 이미 실패하므로 이 entry에서 독립적인 late odd WORD 경로를 실행했다고 주장하지 않는다. skipped-invalid-address 경로는 실제 읽지 않는 주소 때문에 거부하지 않는지 확인했다. 실제 I/O 실패의 원자적 rollback 한계는 그대로 남는다.

최종 보고서는 `artifacts/stage_readiness_execution/verification.json`이며 직접 계산한 SHA256은 `36dd7de01cbd422685c75b54ac4885ba88970ffe1581968c85b6dd54bbeacd5f`다. 문서 갱신 시 `inputs`9개, `native_inputs`9개, `native_artifacts`644개의 현재 hash가 보고서와 모두 일치했다. 이 확인에는 실제 CLI/core/header/Makefile·원본 명령·관측 RAM/trace·최신 계약이 포함된다.

메인의 `make -j4 all test`는 exit0으로 완료했다. `artifacts/stage_readiness_build_test.log`에서 Python196개 검사, 서로 다른 C++ 테스트 실행 파일141개, warning 진단0개를 직접 확인했다. C++141은 실행 파일 수이며 native 조건이나 assertion 수가 아니다. core worker의 별도 격리 normal/UBSan 단위 실행도 통과했다. 이 focused helper 검증은 상위 callback나 전체 stage/게임 실행 완료를 입증하지 않는다.

A7/stack은 oracle 실행 보조 상태이며 API의 동등성 출력이 아니다. 최종 CCR의 나머지 bits/cycles, 물리 RAM mirror, 자연 IRQ/scheduler, 직접 플레이와 전체 복원 완료는 범위 밖이다.
