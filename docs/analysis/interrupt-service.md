# 인터럽트 처리 c8c 통합

원본 복호화 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
CPU `0xc8c..0xd54`는 고정 ROM의 같은 오프셋이다. 구현은 `engine/src/interrupt_service.cpp`, 공개 규격은 `engine/include/ms5/interrupt_service.h`다.

## 처리 순서

`begin_interrupt_service`는 RAM100019의 bit7을 검사·설정한다. 이미 설정되어 있으면 reentrant 상태로 즉시 반환한다. 아니면 RAM100016을 255에서 포화 증가시킨다. 증가 전 값이 255보다 작았을 때만 입력 D0.byte를 watchdog300001에 쓴다. 크레딧 요청 bbe는 그 뒤에 실행한다.

RAM10001b가 음수(byte bit7 설정)인 경우 다음 순서를 실행한다.

1. 72fa 팔레트 전송과 표시 bank 선택.
2. RAM10f001.bit4가 켜져 있으면 D0.byte를3a0011에 쓰기.
3. 1adf8의 네 구조체 열 제어와 PVC 전환.
4. 16cfa 스프라이트 갱신과 PVC/비디오 출력.
5. ce2 작업 프레임 복구. 작업이 있으면 본문 진입 경계에서 `InterruptServiceTask` 반환.

RAM10001b.bit7이 꺼져 있으면 렌더링뿐 아니라 작업 큐 조회도 건너뛴다. 작업이 없거나 이 분기를 건너뛰었으면 d36 후행 처리를 실행한다. f001.bit4에 따라 D0.byte를3a0001에 쓰고, 3cac 사운드 서비스를 실행한다. 사운드 생산자가 대기하면 `InterruptServiceSoundWait`를 반환한다. 사운드가 끝났을 때만 RAM100019 전체 byte를0으로 지우고 `InterruptServiceComplete`를 반환한다.

## 중단과 재개

`continue_interrupt_service`는 d2a로 진입한다. 호출자가 작업 본문 실행 결과 레지스터와 작업 RTS 이후 A7을 제공한다. A5를108000으로 되돌리고 현재 큐에서 다음 작업을 복구한다. 큐가 비면 d36 후행 처리를 실행한다. 크레딧, 카운터, 팔레트, 열 제어와 스프라이트 처리를 반복하지 않는다.

`resume_interrupt_service_sound`는 `InterruptServiceSoundWait` 결과의 pending 생산자를 이어간다. 타이머나 외부 상태를 다시 읽지 않으며, 3a0001 쓰기도 반복하지 않는다. 소비자에 도달했을 때 전달된 현재 sound_status를 사용한다. 완료 시 처리 중 byte를 전부 지운다. 대기 중 호스트가 바꾼 RAM은 재개 입력으로 반영된다.

## 표현 범위와 실패 계약

각 API는 RAM, 팔레트, 출력 상태와 포트를 후보 상태에서 계산한다. 지원하지 않는 하위 입력에서 실패하면 모든 가변 인자를 보존한다. 정상 대기와 작업 본문 진입은 실패가 아니며, 그 시점까지 진행한 상태와 출력이 유지된다.

`InterruptServiceResult.phase`는 complete0/reentrant1/task2/soundwait3이다. `task_registers`와 `task`는 task 상태에서만 유효하며 16개 레지스터와 외부 스택 두 쓰기를 나타낸다. 나머지 상태에서는 이 필드들을0으로 둔다. `sound`는 대기 생산자 상태, `sound_reads`는 이번 호출에서 소비자 상태를 읽은 횟수0/1이다. 포트 벡터는 이번 호출에서 발생한 모든 MMIO 쓰기를 실행 순서대로 담는다.

이 계층은 CPU 에뮬레이터가 아닌 게임 런타임 제어 흐름이다. 완료 시 CPU 임시 레지스터, CCR/SR, 하위 함수의 일시적 스택 쓰기는 출력 계약에 포함하지 않는다. 작업 진입의 레지스터와 프레임 스택 쓰기는 원본대로 제공한다. 입력 A5는 begin에서108000이어야 한다. task 재개는 임의의 A5를 허용한다.

실제 리소스는 기존 MS5C 바이너리와 C++ 로더를 그대로 사용한다. 각 하위 함수의 지원 범위(팔레트 counter0/2000, 일반 사각형 스프라이트 등)는 유지되며, 지원 밖 입력을 임의로 근사하지 않는다. 전체 IRQ prologue/epilogue, BIOS, 작업 본문, Z80와 장치 시간축은 별도 후속 작업이다.

## 검증 CLI

```sh
build/step_interrupt begin INPUT_RAM INPUT_BANKS INPUT_REGS OUTPUT_RAM OUTPUT_BANKS OUTPUT_PORTS EXTERNAL STATUS [MS5C ...]
build/step_interrupt task INPUT_RAM INPUT_BANKS INPUT_REGS OUTPUT_RAM OUTPUT_BANKS OUTPUT_PORTS EXTERNAL STATUS
build/step_interrupt sound INPUT_RAM INPUT_BANKS INPUT_REGS OUTPUT_RAM OUTPUT_BANKS OUTPUT_PORTS EXTERNAL STATUS KIND PHASE LOW CURSOR BYTE_COMMAND BYTE_TAIL BYTE_NEXT
```

RAM은64KiB, BANKS는두8192-byte bank, REGS는16개BE32다. OUTPUT_PORTS는size.byte/address.BE32/value.BE32의9-byte 진단 기록이다. CLI의 begin 초기 표시 bank는0이며 C++ API는 호출자가 제공한 상태를 사용한다. task/sound CLI는 표시 bank를 건드리지 않으므로 JSON display_bank는null(변경 없음)이다. task/sound에서도 bank 데이터는 그대로 출력한다. sound의 EXTERNAL과 REGS 입력은 공통 CLI 규격용이며 재개 동작에서 사용하지 않는다.

## 원본 비교 결과

`.venv/bin/python tools/verify_interrupt_service.py`에서 원본 명령을 바꾸지 않고 c8c/d2a/사운드 대기 경계부터 실행했다. 676조건(독립620, 연속8묶음)과 오류/별칭18조건이 통과했다. RAM64KiB, 두 팔레트 bank, 순서 있는 MMIO54,586개, 작업 경계16개 레지스터/실제 스택 쓰기, 사운드 pending 및 상태 읽기 횟수를 비교했다. 결과 상태는 complete500/reentrant128/task38/soundwait10이다.

모든256개 카운터와 guard byte, BCD 요청, 일반/특수 팔레트 전송, 네 열 구조체와 실제 MS5C002152/002952를 사용한 스프라이트 출력, 1/4/32개 작업 승계, high/low 사운드 대기와 실제 CPU 문맥 재개를 포함한다. 작업 본문 대신 명시적 호스트 레지스터 변화와 반환 스택 소비를 입력했다. 작업 반환에서 사운드 대기로 넘어가는 경로도 포함한다. 예상한 MMIO/RAM/외부 스택 밖의 원본 쓰기는 검증 오류로 처리한다.

보고서: `artifacts/interrupt_service/verification.json`, SHA256 `2d04e2c1b7d2c92c65327eae4de468d70206836e23ed0e80e99a97c73d588065`. 그래픽 원본 비교는 실제 두 MS5C가 가리키는 bank2 범위이며, 전체 뱅크·리소스·게임 시간축을 검증했다는 뜻은 아니다.
