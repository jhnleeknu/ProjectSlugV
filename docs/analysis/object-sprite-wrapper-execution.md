# Object sprite wrapper 실행 인터페이스

후속 공유 stack 통합은 `animation-machine-activation-execution.md`를 따른다. `6c90612` 이후16ea4/16ed2와47cae..47d20의 실제 호출·대기 경로를 연결했다. 아래 기존 API·미구현 분류와 검증 수치는 작성 당시 기록이며, 일반 stage 활성화 전체 완료를 뜻하지 않는다.

[원본 계약](stage-object-output-wrappers-contract.md)의 fixed CPU `16ea4..16ecc`와 tail-call `cd58`을 연결한다. canonical BE ROM SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 이 fixed CPU 주소는 ROM 파일 오프셋과 같다. 원본 ROM을 변경하거나 callee를 stub으로 대체하지 않는다. 이 범위는 object sprite 제출 wrapper이며 전체 object callback나 stage 활성화 완료를 뜻하지 않는다.

```cpp
struct ObjectSpriteWrapperState {
    SpriteSubmitExecutionState sprite;
    std::uint32_t a5, a6;
};
bool execute_object_sprite_wrapper(std::vector<std::uint8_t>& ram,
    ObjectSpriteWrapperState& state, SpriteSubmitStatus& status,
    std::string& error);
```

RAM은 CPU `100000..10ffff`의 정확히65536바이트다. `sprite.registers`의 D[8]/A[5]가 D0..D7/A0..A4의 유일한 상태이며 별도 A5/A6와 waiting을 합쳐 전달한다. 오류는 전체 RAM, 15레지스터, waiting과 status를 보존한다. 성공 status는0 Accepted,1 Clipped,2 Full,3 Waiting이다. 리소스나 port 출력은 없다.

## CLI

```text
build/execute_object_sprite_wrapper \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  WAITING INPUT_RAM OUTPUT_RAM
```

숫자는16개이며 argc는 정확히19다. WAITING은 argv16의0/1, input/output 경로는 argv17/18이다. ENTRY나 STATUS 입력은 없다. 레지스터는 부호 없는32bit 10진수 또는 `0x`/`0X`16진수다. 빈 문자열, 부호, 공백, 후행 문자, overflow와 범위 밖 waiting을 거부한다.

성공 stdout은 정확히17개 key의 한 줄 JSON이다. `d0..d7`, `a0..a6` 숫자15개와 `waiting` boolean, `status` 숫자를 출력한다. OUTPUT_RAM은65536바이트다. 오류는 stderr와 실패 종료 코드로 보고하며 성공 JSON을 출력하지 않는다. API status는 CLI 내부에서 초기화하며 이전 status를 continuation 입력으로 요구하지 않는다.

## fresh와 captured wait

fresh 호출은 A5=108000, D3=0으로 설정한다. BYTE(A6+53)를 D2.byte에 읽어 상위24bit를 보존한다. SWAP D0 뒤 WORD(A6+42)를 modulo65536으로 더하고 원래 flag bit0을 받아1을 뺀다. 다시 SWAP 뒤 WORD(A6+46)를 더하고 원래 flag bit1에 따라1을 뺀다. 두 SUBX의 입력 X는 각각 LSR.B에서 나오며 앞 ADD carry를 사용하지 않는다. D2.byte에는 원래 BYTE>>2가 남는다.

LONG(A6+12)를 D1에, WORD(A6+1e)를 D5.low에 읽고 D5 상위WORD를 보존한다. 이후 원본 JMP처럼 기존 full sprite-submit API로 이어진다. clip/full/normal/deferred/waiting의 실제 register·RAM 효과는 callee를 따른다. wrapper가 별도의 복귀 stack을 만들지 않는다. A6는 보존된다.

captured wait는 A5=108000을 요구하며 cd58의 captured cda4 비교부터 재개한다. object+53/+42/+46/+12/+1e를 다시 읽거나 좌표 변환과 A5 초기화를 반복하지 않는다. 따라서 다음 호출은 직전 실제 출력 RAM·15레지스터·waiting을 전달해야 한다. 대기 중 object 필드를 변경한 경우에도 fresh 전처리를 반복하지 않는다.

기존 callee는 RAM9152 callback=cd50만 지원한다. callback 검사가 clip보다 먼저 실행되므로 clip될 좌표도 임의 callback을 허용하지 않는다. fresh의 실제 object BYTE/WORD/LONG span과 정렬, 이후 callee의 실제 접근만 검사한다. A6 자체에 임의 object-pool 범위를 추가하지 않으며 주소 wrapping이나 물리 RAM mirror를 제공하지 않는다.

## 파일 보호와 I/O 한계

INPUT_RAM은 ifstream으로 열기 전에 stat/S_ISREG로 일반 파일임을 확인하여 FIFO 등 특수 입력을 거부한다. input/output의 canonical 경로나 device/inode가 같으면 거부한다. 숫자·입력·core 오류 시 output을 열지 않는다.

core 성공 후 output을 truncate 없이 O_NONBLOCK으로 예약하고 fstat으로 일반 파일임을 확인한다. 저장한 input identity 및 현재 input inode와 비교한 뒤에만 truncate/쓰기한다. 실제 case alias도 inode로 검사한다. 예약·검사 실패 시 기존 output은 보존하며 새로 생성한 placeholder는 현재 lstat identity가 예약 inode와 같은 경우에만 제거한다. write/close를 검사하지만 실제 I/O 실패 시 output의 원자적 교체나 rollback을 보장하지 않는다.

## 재현과 검증 상태

Makefile의 all/test는 CLI와 `object_sprite_wrapper_test`를 등록한다. 구현은 `object_sprite_wrapper.cpp`와 기존 `sprite_submit_execution.cpp`를 링크하며 기존 sprite-submit header 의존성을 재사용한다. ROM resource loader나 별도 packer는 필요하지 않다.

```sh
make build/execute_object_sprite_wrapper build/object_sprite_wrapper_test
./build/object_sprite_wrapper_test
.venv/bin/python tools/observe_object_sprite_wrapper.py
.venv/bin/python tools/verify_object_sprite_wrapper.py
.venv/bin/python tools/verify_object_sprite_wrapper.py --audit-only
make -j4 all test
```

최종 `artifacts/object_sprite_wrapper_execution/verification.json` SHA256은 `41f926ba31a51a813b5e9c965767e94c1b1e8d2f6a58e758689d9aab5d9b97a5`다. 원본 관측 `artifacts/object_sprite_wrapper/observation.json`의 SHA256은 `49b4e745f9243d6c6b044e81327c7cbaa5122c2d051d8bdfe9734793ea95c525`다. 고정한 Musashi M68000 revision `313ebf1bd9f4d0d93341eb5ce21fd8a119e9dbdd`에서 원본96조건·112phase를 다시 실행하고, 각 phase의 전체64KiB RAM·15레지스터·waiting/status 및 원본 trace/쓰기 기록을 대조했다. 여덟 same-CPU 대기 chain의16개 resume는 직전 실제 C++ 출력 RAM·15레지스터·waiting과 명시된 외부 RAM 변경만을 다음 CLI 입력으로 전달했다.

112phase의 status는 Accepted34, Clipped54, Full8, Waiting16이며 callee 조건분기6개에서 양쪽 결과를 확인했다. 원본 RAM 쓰기는204개다. 대기 중 object 필드·callback·prepared/producer cursor를 변경해도 wrapper 전처리나 callback을 반복하지 않았다. 별도 public captured snapshot 검증4phase는 A6를0/ffffffff로 외부 변경한 hold/ready의 원본·C++ 비교다. 이것은 변경하지 않은 primary96/112 이력에 합치지 않으며, resume에서 사용하지 않는 A6를 읽지 않음을 추가로 확인한다. captured A5=108000 제한은 유지한다.

139개 negative 검사는 malformed 숫자·waiting, RAM 크기/접근/정렬, 늦은 callee 실패, 잘못된 captured A5 및 FIFO/alias에서 input과 기존 output 보존을 확인했다. 이 환경의 case-insensitive input/output alias 거부와 새 output 생성도 확인했다. checked 오류와 합성한 잘못된 resume를 원본의 정상 완료 이력이라고 취급하지 않는다. 보고서의 구현 입력13개, native 입력5개와 native/C++ artifact238개의 현재 SHA256도 모두 일치했다. 비교 CLI 바이너리 SHA256은 `4f1f25f01dd46f2b624f1f0c40f68fbae5b033ec79301e635f32ae89a1152906`이다.

전체 `make -j4 all test`는 exit0으로 완료했다. `artifacts/object_sprite_wrapper_build_test.log`에는 Python196 tests, C++ 실행143개와 경고0개가 기록되어 있다. core의 별도 normal/UBSan 단위 실행도 통과했다.

A7/stack·CCR전체·cycles, 임의 callback, 자연IRQ/scheduler, 물리mirror, 화면 전체·직접 플레이와 전체 재구성 완료는 이 wrapper의 증거 범위 밖이다. 대기 반환은 자연 scheduler나 장치 시점의 복원 완료를 뜻하지 않는다.
