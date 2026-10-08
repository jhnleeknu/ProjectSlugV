# 4843c stage counter 인터페이스

원본 의미는 [확정 계약](stage-counter-contract.md)을 따른다. canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 fixed CPU `4843c..4847a`는 같은 ROM 파일 오프셋이다. 이 helper의 RAM·15레지스터 효과를 제공하며 `47c6c` callback 또는 자연 stage 실행 전체를 뜻하지 않는다.

```cpp
bool execute_stage_counter(std::vector<std::uint8_t>& ram,
    ObjectRestartState& state, std::string& error);
```

RAM은 CPU `100000..10ffff`의 정확히65536바이트이며 상태는 `ObjectRestartState`의 D[8]/A[7]이다. A5를108000으로 강제하지 않고 실제 도달하는 BYTE 접근만 검사한다. 홀수 A5도 해당 접근이 유효하면 허용한다. 24bit mirror나 임의 주소 wrapping을 구현하지 않는다. 실패 시 RAM/state를 보존한다. 외부 리소스나 MMIO/ports는 없다.

## CLI와 파일 보호

```text
build/execute_stage_counter \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  INPUT_RAM OUTPUT_RAM
```

숫자는15개, 실행명을 포함한 argc는 정확히18이다. ENTRY/resource/port 인자는 없다. 부호 없는32비트 10진수 또는 `0x`/`0X`16진수를 받으며 빈 숫자, 부호, 공백, 후행 문자와 overflow를 거부한다. 성공 stdout은 한 줄 JSON으로 정확히 `d0..d7`, `a0..a6` 숫자15개만 출력한다. OUTPUT_RAM은65536바이트다. 오류는 stderr에 쓰고 성공 JSON을 출력하지 않는다.

INPUT_RAM은 열기 전에 `stat`/`S_ISREG`로 일반 파일임을 검사하여 FIFO 등 특수 입력을 거부한다. input/output의 canonical 경로 또는 inode가 같으면 거부한다. 숫자·입력·core 실패 시 output을 열지 않는다.

core 성공 후 output을 truncate 없이 `O_WRONLY|O_NONBLOCK|O_CREAT|O_EXCL`로 예약하고 기존 파일은 `O_WRONLY|O_NONBLOCK`으로 연다. `fstat`으로 일반 파일 여부를 확인하며 처음 검사한 input inode와 쓰기 직전 input의 현재 inode를 모두 대조한 뒤에만 truncate/쓰기한다. hardlink/symlink/case alias도 실제 identity로 검사한다.

예약/검사 실패 시 기존 파일은 보존한다. 이번 호출에서 새로 생성했고 현재 `lstat` identity가 예약 inode와 같은 placeholder만 제거한다. write의 EINTR을 재시도하고 close 결과도 검사한다. 실제 truncate/write/close 실패에는 원자적 교체나 이미 수행한 출력 변경의 rollback을 보장하지 않는다.

## gate와 raw BYTE 연산

BYTE(A5+5683)의 bit4가0이면 RAM과 전체15레지스터를 그대로 보존한다. bit4가 켜져 있으면 두 status BYTE(A5+7db6/+7db7)를 각각1과 비교한 결과를 D0.byte/D1.byte에 ff/00으로 쓰고 OR.B D0,D1을 실행한다. 두 status를 모두 읽으며 short circuit하지 않는다. 둘 다1이 아니면 이 D0/D1 BYTE 변경만 남기고 반환한다. 두 레지스터의 상위24bit는 보존된다.

활성 경로는 D0.byte=RAM(A5+567f), D1.byte=RAM(A5+567e), D2=0으로 설정한다. D0.byte에서 binary2를 빼고 그 borrow/X를 source0의 SBCD.B D2,D1에 전달한다. incoming SR의 X는 SUBQ가 덮어쓰므로 별도 API 입력이 아니다. SBCD carry가1이면 D0/D1 **전체32비트**를0으로 지우고, carry0이면 상위24bit를 유지한다. D1.byte를 A5+567e에 먼저, D0.byte를 A5+567f에 다음으로 쓴다. D3..D7/A0..A6는 보존한다.

유효 BCD 입력만 가정하지 않는다. source0의 실제 BYTE/C/X 결과는 hardware-tested 외부 primary reference인 [Flamewing 68k BCD verifier revision39a01be](https://github.com/flamewing/68k-bcd-verifier/tree/39a01be528b0744302bf1dc9b3463fc22a3fc45f)의 검증 범위를 근거로 한다. README는 Model1 Sega Genesis와 Model3 VA2에서 모든 입력 조합의 hardware 통과를 보고한다. 이는 외부 저자의 hardware 검증이며 이번 저장소에서 직접 물리 CPU를 측정한 결과는 아니다.

다운로드한 고정 revision `39a01be528b0744302bf1dc9b3463fc22a3fc45f`의 `bcd-gen.cc`/`bcd-emul.cc`로 생성한 실제 `artifacts/dependencies/flamewing-bcd/data/bcd-table.bin`은1050624바이트이며 SHA256은 `8432868c9aa93c92574bae48bebd4efb2834e298340eb09530625365b80147e5`다. table 순서는 source→destination→X→Z, 각 항목은 flags BYTE 뒤 result BYTE다. source0 SBCD512조합의 BYTE/C/X를 원본 명령의 local cross-oracle 결과와 대조하면 Unicorn은512개 모두 일치하고 pinned Musashi는301개가 다르다. 두 incoming Z에서 BYTE/C/X는 동일하다. `tools/check_stage_counter_bcd.py`가 이 reference/probe 대조를 재현한다. 외부 GPL 소스는 분석 reference이며 engine에 구현을 복사하지 않는다.

확정된 source0 규칙은 X=0이면 dst BYTE 그대로이고 C=0이다. X=1이면 dst가0일 때 raw result99/C=1이며, 그 외에는 low nibble이0이면7, 아니면1을 빼서 BYTE로 자르고 C=0이다. 따라서 `4843c` caller의 관측 가능한 최종 결과는 X=1/dst0에서만 D0/D1 전체0이며 나머지는 상위24bit를 보존한다. 예를 들어 dst=a0/X0은a0/carry0, dst=a0/X1은99/carry0, dst=9f/X0은9f/carry0이다. dst0/X1을 단순 BYTE−7=f9로 계산하면 원본 SBCD 직후의 값이 틀리므로 post-correction raw99와 caller의 후속 clamp를 구분한다. 최종 CCR/N/V와 cycles 또는 물리68000의 모든 동작까지 동등하다고 주장하지 않는다.

## 빌드와 검증 상태

Makefile은 CLI를 all에, `stage_counter_test`를 test에 등록한다. source는 새 `stage_counter.cpp` 하나이며 header는 `stage_counter.h`, `object_restart_execution.h`, `video_port.h`다. `ObjectRestartState` 생성자는 inline이므로 object restart 구현 전체를 링크하지 않는다. runtime packer도 필요하지 않다.

```sh
make build/execute_stage_counter build/stage_counter_test
./build/stage_counter_test
.venv/bin/python tools/check_stage_counter_bcd.py
.venv/bin/python tools/observe_stage_counter.py --oracle unicorn
.venv/bin/python tools/verify_stage_counter.py
```

acceptance oracle은 hardware-tested source0 reference와 일치하는 pinned Unicorn이다. 최종 native 관측은 `artifacts/stage_counter/unicorn/observation.json`이며 직접 계산한 SHA256은 `aea00334404fbac5a894eedaa9049b639145e19f41f840bad29141900886f5b0`다. BCD 기준 대조 `artifacts/stage_counter_bcd/verification.json`의 최종 SHA256은 `bf692382e2f4905834e6cfc806944c4633d23d9989879a1b0adcf471c75d294e`다. 기존 Musashi 관측과 당시 입력 snapshot은 별도 진단으로 보존하며 acceptance로 사용하지 않는다. 기존 Musashi의 전체 WORD 출력/레지스터 차이39914개는 source0 raw BYTE/C/X 차이301개와 다른 집계다.

원본 counter WORD의 전체65536개를 실제 C++ API와 비교하여 전체64KiB RAM·15레지스터가 일치했다. verifier가 개발용 `engine/tests/stage_counter_sweep.cpp`를 별도 artifact 실행 파일로 빌드하여 batch API 비교를 수행한다. 이 harness는 원본 binary row의 출력BYTE와15레지스터를 expected로 읽으며 BCD 보정 수식을 중복 구현하지 않는다. 원본 CPU가 기록한 실제 두 BYTE 쓰기에서 expected RAM을 재생하고 hash와 쓰기 순서도 감사한다. native 전체65536개와 batch API 전체65536개를 합쳐 조건 수를 두 배로 세지 않는다.

실제 CLI621조건은 high BYTE256개 각각에 low0/2를 준512조건과 gate/status/비영 register high bits/odd·shifted A5/경계의109개 상세 조건이다. native109조건은별도로 전체 RAM·15레지스터·실제 단계·쓰기 근거를 기록했다. gate와 status 조기반환, SBCD 후 전체 D0/D1 clear의 각 조건 분기 양쪽 결과를 확인했다. runtime 리소스나 ports는 없다.

오류116조건에는 RAM 크기·15개 숫자 parse·missing/extra 인자·파일 종류/경로 충돌·hardlink/symlink·RAM input/output FIFO·도달한 A5 span과 late status/counter 접근·새 output 미생성·실제 대소문자 비구분 파일시스템의 input/output alias가 포함된다. 입력과 기존 출력 보존 및 실패 후 placeholder가 남지 않는 동작을 확인했다. 실제 truncate/write/close 실패의 rollback 한계는 그대로 남는다.

최종 실행 검증은 `artifacts/stage_counter/execution/verification.json`이며 직접 계산한 SHA256은 `2c9836dea6930615c4cd392af1f12fa880b38ace9fe57b96955c577df49368a4`다. 문서 갱신 시 `inputs`9개, `native_inputs`18개, `native_artifacts`453개, `reference_inputs`7개의 현재 hash가 보고서와 모두 일치했다. 이 확인에는 CLI/core/header/Makefile·batch harness와 binary·native 기록·고정 external reference가 포함된다.

메인의 `make -j4 all test`는 exit0으로 완료했다. `artifacts/stage_counter_build_test.log`에서 Python196개 검사, 서로 다른 C++ 테스트 실행 파일140개, warning 진단0개를 직접 확인했다. C++140은 실행 파일 수이며 native 조건이나 assertion 수가 아니다. core worker의 별도 격리 normal/UBSan 단위 실행도 통과했다. 이 검증은 자동 역어셈블이나 보정 수식만을 근거로 완료를 선언한 결과가 아니다.

A7/stack/CCR/cycles, 물리 RAM mirror, 상위 callback/IRQ/scheduler와 직접 플레이는 범위 밖이다. helper의 focused 비교만으로 전체 게임 복원 완료를 선언하지 않는다.
