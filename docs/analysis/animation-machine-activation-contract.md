# 상위 stage 활성화의 실제 stack 연결 계약

Baseline `6c90612`. 메인이 canonical BE 프로그램 `extracted/program/maincpu.decrypted.be.bin`의 원본 명령을 직접 읽었다. SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 fixed CPU 주소는 같은 파일 offset이다. 이 문서는 구현·검증에 앞서 확정한 계약이며 동작 대조 완료 기록은 별도 execution 문서에 남긴다.

## 실행 순서

| 진입 block | 실제 효과와 다음 PC |
| --- | --- |
| 47cae | WORD(A6+42)=00a0, WORD(A6+46)=0170, WORD(A6+1e)=ffff 순서대로 쓰고47cc0 |
| 47cc0 | JSR16ed2, 공유 stack return47cc6 |
| 47cc6 | PC-relative JSR47672, 공유 stack return47cca |
| 47cca | BYTE(A6+14)=0b 후 D0=0; live BYTE(A6+7e)를D0.byte에 읽고 WORD 두 번 더해4배; A0=48a12; LONG(A0+signextend(D0.low))를D7에 읽음; D0=0 후47ce6 |
| 47ce6 | JSR16ea4, 공유 stack return47cec |
| 47cec | 기존 좌표 설정→49f8c 초기화→49fc6 실행 후47d20 |

`47cc6` bytes는 `4ebaf9aa`이며 displacement 기준은 opcode 다음 WORD 주소47cc8이다. 새 stack은 RAM에 실제 return LONG을 쓰고 RTS는 그 시점 live RAM을 읽는다. Caller가 요구하는 순서를 callee 효과를 미리 계산해 합치는 방식으로 대체하지 않는다.

BYTE index는00..ff이고 두 번의 ADD.W 뒤0000..03fc이다. 따라서 raw LONG 조회 가능 span은 `[48a12,48e12)`이다. 이것은 논리적인256항목 table이라는 판정이 아니다. C++은 기존8MiB MS5D kind3 리소스를 실제 loader/bus로 읽으며 별도 합성 lookup을 만들지 않는다.

## 16ed2와16ea4

`16ed2`는 WORD(A5+0d3e)를D0.low에 읽고 live WORD(A5+0d46)와 **signed16** 비교한다. 작으면 BYTE(A6+15)의bit2를 세우고 그 외에는 지운다. D0.high와 다른 bit를 보존한다. BSET/BCLR 쓰기가 return LONG과 겹치면 실제 RTS가 변경된 return을 읽어야 한다. 일반 flag를 따로 저장하지 않고 해당 semantic block의 carry는 Unknown으로 둔다.

`16ea4`는 A5=108000, D3=0으로 만든 뒤 BYTE(A6+53)를D2.byte에 읽는다. D2의 상위24bit를 유지한다. SWAP D0→WORD(A6+42) 더하기→LSR.B D2→SUBX.W D3,D0을 실행한 뒤 다시 SWAP D0→WORD(A6+46) 더하기→LSR.B→SUBX.W 순서다. 각 subtraction의 X는 앞선 ADD가 아니라 **바로 앞 LSR에서 나온 원래 flag bit0/bit1**이다. 모든 WORD 연산은 modulo65536이고 signed C++ overflow에 의존하지 않는다.

그 뒤 LONG(A6+12)를D1에, WORD(A6+1e)를D5.low에 읽는다. D5.high와D7은 보존된다. 마지막 `16ecc:4ef90000cd58`은 JMP이므로 wrapper용 return을 추가로 push하지 않는다. cd58의 callback JSR는 기존과 같이 실제 stack을 사용한다. Clip에 걸려도 callback은 먼저 실행된다.

## 대기·실패·범위

16ea4의 사전 계산은 fresh block에서만 실행한다. 대기는 실제 cda4 또는3aea PC와16register/A7, live RAM을 다음 호출에 넘긴다. 대기 중 object 입력·callback·queue 값 또는 saved stack이 바뀌면 이후 실제 읽는 값에만 반영한다. 상위 활성화 block이나 이미 끝난 callee를 재실행하지 않는다.

세 새 JSR block은 입력 carry를 보존한다. 나머지 새 block은 보수적으로 Unknown이며, 이후 기존 initializer/animation writer만 알려진 C를 새로 결정한다. Zero-step과 실패의 전체 출력 보존은 현재 공개 machine 계약을 유지한다. 원본 TRAP/bus fault의 rollback을 뜻하지 않는다.

입력은 ROM을 바꾸지 않는 통제된 상태다. 이 갈래 앞의47c6c 조건문·HUD/BCD 및47d20 이후 readiness/frame은 별도 남은 작업이다. 전체 scheduler에서의 도달, 자연 IRQ/timing, 임의 callback와 전체 stage 실행을 이 계약으로 완료 처리하지 않는다.
