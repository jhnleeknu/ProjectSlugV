# 인터럽트 상태와 기본 콜백 초기화

원본 복호화 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 CPU 주소는 같은 ROM 오프셋을 가리킨다. `interrupt_init.h/.cpp`는 A5=108000에서의 c42/3dce를 별도 API로 제공한다.

`initialize_interrupt_state`는 c42..c62에 대응한다. RAM100016=0,100017=2,10001a=0,100019=0,10001b=0을 설정하고 RAM10081c.long에10081c를 쓴다. 프레임 신호는0, 임계값은2, 작업 큐는 빈 상태다. RAM100018과 저장 작업의 기존64-byte 프레임 내용은 지우지 않는다. IRQ 콜백 슬롯도 이 함수에서 바꾸지 않는다.

`initialize_irq_callbacks`는3dce..3de4에 대응한다. RAM104d91.bit4만 지우고 나머지 bit는 보존한다. A0=3dcc를 RAM100006.long과10000a.long에 저장한다. 이 값은 두 콜백의 기본값이며, 고정 원본3dcc는RTS다. A0를 결과로 반환한다. 임의의 런타임 콜백이 항상 기본값이라는 가정은 하지 않는다.

둘 다 정확히64KiB RAM을 요구하고 크기 오류에서 입력을 보존한다. API는 원본의 일반 RTS 스택 처리나 SR/CCR을 포함하지 않는다. 변경 주소가 서로 겹치지 않으므로 두 초기화의 순서에 따른 RAM 차이는 없지만, 이것을 전체 부팅 순서가 자유롭다는 의미로 확대하지 않는다.

## 기본 콜백 반환

`irq_envelope`의 `return_default_irq_callback`은 원본3dcc의RTS를 구현한다. 호출자가 현재 target이3dcc임을 확인한 경우에 사용한다. 명시적 외부 스택에서 반환long을 읽고 next_pc로 내보내며 A7을4 증가시킨다. 다른 레지스터·RAM·스택 바이트를 바꾸지 않고 MMIO/스택 쓰기도 없다.

외부 스택 규격은 기존 IRQ envelope와 같다. A7은110000..fffffa의 짝수이며 반환long 전체가 buffer에 있어야 한다. 실패하면 레지스터·결과·포트를 보존한다. 성공하면 이번 호출의 포트/스택 쓰기 결과는 빈 목록이다.3dcc 외의 콜백, BIOS, RTE의 구현으로 사용하지 않는다.

```sh
build/initialize_interrupt state INPUT_RAM OUTPUT_RAM A0
build/initialize_interrupt callbacks INPUT_RAM OUTPUT_RAM A0
build/step_irq_envelope callback INPUT_RAM INPUT_STACK INPUT_REGS OUTPUT_RAM OUTPUT_STACK OUTPUT_REGS OUTPUT_PORTS STACK_BASE
```

초기화 CLI는 JSON의a0를 반환한다. state 모드는 입력 A0를 보존하고 callbacks는3dcc를 반환한다. callback 모드는 기존 IRQ CLI의 파일 규격을 공유하며 next_pc와 갱신된 REGS를 반환한다. 입력·출력 파일의 별칭은 거부한다.

## 원본 비교

`.venv/bin/python tools/verify_interrupt_init.py`에서 초기화640조건(독립608), IRQ 진입/기본 콜백35조건, 첫 서비스 연결16조건 및 오류/별칭13조건이 통과했다. 모든256개 초기 byte·플래그, 반복 초기화의 멱등성, 두 초기화 순서, RAM100018 보존을 확인했다. 초기화 전후 전체 RAM/A0와 다른 레지스터 보존, MMIO 부재를 원본과 비교했다.

연결 검증은 초기화 결과에서 원본20c로 들어가 실제3dcc RTS를 실행하고23c의JSR c8c를 따라242(BIOS 호출 전)까지 진행한다. 같은 상태의 C++ 초기화/envelope/callback/service 결과와 RAM·레지스터·스택·포트를 각 API 계약에 맞춰 비교한다. 서비스 반환의 임시 레지스터/하위 스택은 그 API 계약 밖이다. 사운드 타이머·큐 등 두 초기화가 설정하지 않는 필드는 명시적으로 준비한 조건이며 전체 부팅 상태로 주장하지 않는다. 첫 서비스 후 카운터1/임계값2와busy0을 확인했다.

검증 도구는 캐시된 실행이 지정 경계를 넘지 않도록 명령 hook으로 경계 직전 중단을 보장한다. 원본 코드 패치는 없다. 보고서 SHA256 `c3b058b659bbb5e098b2b9229e1d41ba802a8914304b50005f96953d91dc0615` (`artifacts/interrupt_init/verification.json`). BIOS/RTE/자연 IRQ 시간축과 전체 부팅은 미완료다.
