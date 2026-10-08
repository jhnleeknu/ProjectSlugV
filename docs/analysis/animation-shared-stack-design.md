# Animation 실행 상태와 공유 RAM stack의 통합 설계

Baseline `68bd083`. 메인이 원본 명령, 기존 C++ 실행기와 stack 접근 목록·통합 감사를 검토해 정한 후속 구현 계약이다. 이 문서만으로 새 full49fc6 C++ 실행의 완성을 주장하지 않는다. Canonical 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며, 아래 고정 CPU 주소는 같은 ROM 파일 offset이다.

## 상태의 권위와 호출 경계

새 shared-stack 실행 경로는 명시적인 machine state를 사용한다. 필요한 값은 D0..D7/A0..A7, 현재 논리 PC, 실행·대기·호출 완료의 구분과 장치 상태다. 기존13register 구조에 A5/A6/A7을 함께 두어도 되지만 A7을 phase별 상수로 역산하지 않는다. PC는 적어도 진입·대기·복귀 dispatch를 구분할 수 있어야 한다.

처음 호출할 때 caller는 PC49fc6, 실제 A7과 이미 RAM에 있는 caller return LONG을 제공한다. 실행기가 임의 sentinel이나 초기 stack padding을 쓰지 않는다. 종료 경계의 caller PC는 호출자가 명시한다. RTS는 실제 LONG을 pop하고 PC를 바꾼 뒤 그 경계인지 확인한다. 내부 continuation으로 바뀐 return은 해당 지원 경로로 dispatch하며, 아직 지원하지 않는 주소는 명시적으로 보고한다. 예상 return을 RAM에 다시 쓰거나 원래 continuation으로 강제하지 않는다. 이 단계의 checked 미지원 주소는 전체 복원 목표의 최종 제외 범위가 아니다.

공유64KiB RAM이 saved A0/A1/bank/list end/low BYTE와 return LONG의 유일한 값 저장소다. 기존 metadata는 과거 scratch-stack 실행 증거를 재현하는 경로에 남길 수 있으나 새 경로의 복원값을 결정하지 않는다. 최종 엔진 소비 경로는 shared-stack 실행으로 전환한다. mode flag의 기본값이나 NULL stack context로 조용히 기존 동작을 선택하지 않는다.

구현은 원본 opcode를 범용 CPU로 해석하는 방식 대신, 의미가 확인된 함수·기본 블록의 C++11 로직으로 구성한다. 블록 사이 PC dispatch는 변경된 실제 return과 대기 재개 위치를 나타내기 위해 사용한다. 구조체·열거형·일반 함수와 명시적인 정수 타입을 사용한다.

## 공통 stack primitive

`push_program_stack`과 `pop_program_stack`은 program bus를 사용한다. BYTE/WORD는 A7을2, LONG은4만큼 바꾸며 uint32 연산으로 wrap한다. BYTE는1BYTE만 접근하고 padding은 건드리지 않는다. WORD/LONG 정렬·24bit bus 선택·16 RAM mirror·LONG의 두 WORD는 기존 bus 규칙을 따른다. Pop은 호출 시점의 live memory를 읽는다.

이 primitive는 한 접근의 실패 때 RAM/A7/출력값을 보존한다. 여러 push/pop과 queue/PVC 효과의 원자성은 상위 invocation transaction이 책임진다. 이 오류 계약은 실제 CPU bus fault의 부분 실행 효과를 모사한다는 뜻이 아니다. MOVEM의 레지스터 순서·sign extension과 JSR/RTS의 PC 변경은 caller 로직에서 구현한다.

## 순서가 의미를 바꾸는 지점

- direct04는4a104에서 return4a108을 먼저 push한 다음4a10c의 operand를 읽는다. Callback14/3c도 outer A0 push가 selector/operand fetch보다 앞선다. Stack과 script가 겹치면 나중 fetch가 바뀐 bytes를 보아야 한다.
- indexed10은4a23e에서 list end를 push한다. 선택 draw가 실행되는 경우 별도로 return4a270을 push하며,4a270은 live list end를 pop한다. 복귀는49ffe이고4a276 publication을 추가하지 않는다.
- callback과 draw의 bank 복귀는 **live bank pop→shadow 쓰기→D0/D7 WORD push→shadow 재읽기·PVC 쓰기→D0/D7 signed WORD pop→A0/A1 LONG pop**의 순서를 유지한다. 중간 WORD push가 shadow와 겹칠 수 있으므로 local 변수로 저장·복원한 것만으로 대체하지 않는다.
- direct30은 A0/A1 LONG과 return4a2ec를 사용한다. Callback bank frame이나 MOVEM.W sign extension을 추가하지 않는다.4a2ec는 두 live LONG을 읽고4a276이 복원된 A0에 script pointer를 쓴다.
- cd58의 defaultcd50 RTS callback과47672의ca70 호출도 실제 return LONG을 쓴다. 바로 pop해도 메모리에 남는 bytes를 지우지 않으며 후속40이 이를 읽을 수 있다.
- sound3bfa는 low BYTE를 stack에 저장하고3bfc는 return3c00을 push한다. High wait를 마친 뒤3c00은 live stack BYTE를 읽는다.3c02는 tailcall이므로 새 return을 push하지 않는다. Low wait 단계에서 이전 saved-low slot을 다시 읽지 않는다.
- nested47672의 inner A0와 interpreter의 outer A0는 서로 다른 live LONG이다. Inner pop 뒤 source를 다시 읽는 순서와 outer pop 뒤 script publication을 분리한다.

## 대기와 장치 상태

대기 상태에는 실제 PC/A7과 현재 레지스터를 보존한다. 같은 실행 인스턴스의 RAM·장치 상태에 명시적으로 적용된 외부 변화만 다음 호출 입력으로 허용한다. 이미 수행한 prefix/push/queue write를 재실행하지 않는다. Host가 wait 사이 stack BYTE/LONG을 바꾸었다면 다음 원본 pop 위치에서 그 변화를 소비한다. 이것은 원본 실행 도중 expected register를 주입하는 검증과 다르다.

일반 bus의 readonly PVC view만 연결하고 port 기록만 바꾸면 일관된 장치 상태가 되지 않는다. 새 invocation은 mutable PVC8192BYTE·current bank·ordered ports를 함께 처리해야 한다. Saved bank는 stack에서 읽는 RAM 값이며 current physical bank의 대체물이 아니다. Vector 선택과 기타 MMIO는 명시적인 장치 계약을 유지한다.

실행 전 candidate RAM·machine state·PVC를 만들고 그 candidate를 참조하는 bus view를 구성한다. 실패하면 caller의 RAM/상태/PVC/ports/외부 읽기 수를 모두 보존한다. 성공한 wait와 완료는 수행한 효과를 commit한다. Borrowed pointer가 swap 전 객체를 계속 가리키지 않도록 수명과 재바인딩을 명시한다.

## 구현·검증 순서와 남은 범위

1. 공통 stack primitive와 실제 synthetic M68000 push/pop의 SP·접근 BYTE·전체 RAM 대조를 완료한다. 이는 원본 whole-call 증거와 구분한다.
2. 원본49fc6를16개 RAM mirror와 실제 stack이 공유하는 backing에서 실행한다. Callback/direct sound/indexed skip/early draw 뒤40이 dead stack을 읽는 결과를 확보한다. 대기 중 live stack mutation도 같은 CPU에서 재개한다.
3. 새 machine 경로에 이미 분석한 animation 명령과 callee의 실제 frame을 연결한다. 초기 몇 개 fixture만 통과한 상태를 whole40 완료로 집계하지 않는다. 기존 callee의 canonical-only/A5 고정 제약을 목록화하고 bus/상태 전달로 해소한다.
4. 모든 지원 draw·callback·direct sound의 begin/hold/release, live stack 복원, script/queue/shadow alias, RTS dispatch와 장치 transaction을 원본과 비교한다. C++ 재개에는 직전 실제 출력과 기록된 외부 변경만 사용한다.

기존 scratch-stack 보고서를 shared RAM stack의 성공 근거로 재분류하지 않는다. 전체 RAM 차이를 mask하지 않고 모든16register/PC·실제 read/write 순서·PVC를 범위에 맞게 검증한다. 현재 backend의 host SR 관측만으로 일반 CCR을 검증했다고 주장하지 않는다. 자연 caller/script 도달성, scheduler/IRQ와 전체 게임의 나머지 로직은 별도 미완료 범위로 계속 유지한다.
