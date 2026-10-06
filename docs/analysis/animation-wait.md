# 애니메이션 대기·경계 명령 상태 전이

프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
주소는 고정 ROM 파일 오프셋=CPU 주소다. A6는 오브젝트, A0=A6+26이다.

## 상태와 진입

A0+0은 명령 포인터long, +4는16bit 타이머, +6은16bit 감소량이다.0x49fc6에서 bank shadow100010을0으로 설정한다. 포인터0이면 carry를 세우고 반환하며 아래 카운터를 건드리지 않는다.

활성 포인터이면0x49fee에서 global10d742 byte를0으로 지운다. 오브젝트+17 byte가signed 양수일 때만1감소한다. 그 뒤 opcode를 읽어 분기한다. 매 명령 재해석 시 이 두 초기화는 반복하지 않는다.

## opcode00 (0x4a066)

1. global10d742 byte를1증가하고 duration byte를 읽는다.
2. duration=0이면 타이머가signed 음수일 때 타이머 전체를0으로 지우고 저장된 포인터로 되돌아가 다시 해석한다. 비음수이면 포인터 저장 없이carry0으로 반환한다.
3. duration!=0이면 기존 타이머를 별도 old 값으로 잡는다. old가signed0이하일 때 타이머의**상위 byte에만** duration을byte wrap으로 더한다. 하위 byte는 유지한다.
4. old가비음수일 때만 감소량word를16bit wrap으로 뺀다. 이후 조건 판정에서도 갱신 후 타이머와 old를 구별한다.
5. 갱신 후 타이머가signed 양수이면 실행 포인터를 저장된 포인터로 되돌린다.
6. 다음 실행 포인터의byte가28이면 다시 저장 포인터로 되돌리고 반환carry 후보를1로 한다.
7. old가음수이면 현재 실행 포인터에서 같은 호출 내 해석을 계속한다. 이때 다음 명령 진입은 반환carry 후보를 다시 초기화한다.
8. old가비음수이면 실행 포인터를상태+0에 저장하고 반환한다.

따라서 단순한 정수 프레임 카운트가 아니다. signed 비교, 상위byte duration 덧셈, word 감소, 같은 호출 안의 반복이 함께 작동한다. duration을시간 단위로 정확히 해석하려면 실제 감소량 설정 호출부를 추가로 추적해야 한다.

## opcode28 (0x4a0e4)

타이머가음수이면 전체word를0으로 지우고 저장 포인터로 되돌아가 해석을 계속한다. 비음수이면 상위byte만0으로 만들고 carry1로 반환한다. 저장 포인터를null로 만들지 않는다. 따라서 이 명령을 오브젝트 소멸이나 애니메이션 영구 정지로 단정하지 않는다.

## 검증

`.venv/bin/python tools/analyze_animation_wait.py`

원본0x49fc6을 호출해 제어된RAM 스크립트를 실행했다. 대기1920조건과 직접28/포인터null80조건의총2000조건에서 전체64KiB RAM이 의미 모델과 일치했다. 타이머 signed 경계, duration0/1/2/127/128/255, 감소량0/1/256/ffff, 카운트다운signed 경계, 다음opcode00/28을 포함한다.

반환carry는 도구의SR 노출에 의존하지 않고 원본RTS 뒤 별도검증stub의SCS 명령이 테스트scratch105900에 기록한byte로 대조한다. 비교 전에 이 테스트전용byte를 원상복구하므로 원본RAM 변경과 혼동하지 않는다. 원본 파일은 수정하지 않고 emulator 메모리에만stub을 둔다.20000명령 한도 내 반환을 확인한다.

초기 실험에서 반환 주소를 이후 별도emu_start로 재실행하자 다음 호출의 종료점 관찰이 맞지 않았다. 검증stub을 원본반환 경로에 직접 넣고 하나의emu_start로 실행하도록 수정해 결과를 다시 확인했다.

현재 도구는 대기/경계 전용 의미 모델이다. C++ 시간 흐름 실행기, draw 혼합 스크립트, 다른opcode, 자연 게임 스크립트 및 실제 프레임 스케줄은 후속 작업이다.

## C++ 실행기 통합

`step_animation`은 원본 상태 포인터를 사용해 입력 script bytes와 CPU base 안에서00/04/28을 해석한다. 명령 fetch는 리소스 byte vector에서만 수행하고 RAM은 상태로 사용한다. 비활성 포인터에서는bank shadow만0으로 만들고carry1로 반환한다. 원본 명령 주소를 보존하지만 하드웨어 bank 전환을 수행하는 API는 아니다.

04는 `decode_animation_draw`와 `submit_sprite`에 연결했다. Accepted/Clipped/Full이면 해석을 계속하고, 동시 소비를 기다리는 Waiting은 명시적 오류로 되돌린다. 지원하지 않는 명령·잘린 operand·범위 밖 fetch·10000명령 초과도 오류이며 호출 전 RAM과carry를 보존한다. 이 실패 처리는 손상된 원본 명령 스트림의 CPU 동작을 흉내 내려는 계약이 아니다.

`analyze_animation_wait.py --cpp`의2000조건에서 원본·C++ 전체RAM과carry가 일치했다. `verify_animation_pipeline.py`는 두 draw 명령과 두 wait,28을 섞은제어스크립트로8개 연속 시퀀스를 비교한다. 타이머 초기0/ffff, 감소량128/256, 큐 초기방향0/128 조합에서12회씩 실행해총96 interpreter 호출과192 준비·갱신 단계의 전체RAM·carry·비디오 쓰기가 일치했다. 표시 리소스는 실제 추출된 MS5C 2152/2382a를 C++ 로더로 읽는다.

이 스크립트는 검증 fixture다. 원본 ROM에서 추출한 자연 애니메이션 리소스로 취급하지 않는다. 실제 스크립트의 경계·참조·시간 설정과 나머지opcode 연결은 다음 단계다.
