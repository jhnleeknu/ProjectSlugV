# 상태·요청 분기와 화면 채우기의 실제 스택 계약

Baseline `915a4c3`. Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소는 fixed CPU 주소이자 같은 ROM 파일 offset이다. 메인은 원본 `bee..c36`, `4e216..4e24e`, `47d24..47da4`, `477ac..477c2`, `35a2..35f0`의 완전한 명령 bytes를 읽고 기존 작은 helper와 화면 초기화 계약을 대조했다. 이는 구현 계약이며 실행 검증은 별도 execution 문서에 기록한다.

## 두 helper와 실제 carry 소비

4e216은 D0.byte=BYTE(A5-75bc)를 읽고0/5일 때만 D0.byte=BYTE(A5-74f8)를 추가로 읽는다. 둘 다0/5이면4e248의 ORI CCR1로 Set, 그 외4e242의 ANDI CCRfe로 Clear를 만든다. D0 상위24bit를 보존하며 실제 마지막 읽은 BYTE가 남는다. 접근하지 않는 두 번째 주소를 미리 검사하지 않는다. 끝에서는 live RTS를 실행한다.

bee는 absolute BYTE10f004를 D0.byte에 읽고 같은 주소를0으로 쓴다. A0=10fdb6에서 첫 BYTE를 D1.byte로 읽고 A0를1증가시킨다. 값1/2이면 c2a에서 D0.byte를10f004에 복원하고 c30 ORI로 Set을 만든다. 그 외 두 번째 BYTE도 postincrement로 읽고 같은 조건을 검사한다. 둘 다 다르면 c24 ANDI에서 Clear로 반환하며 요청 BYTE는0으로 남는다. 두 register의 상위24bit는 유지한다. A5에 의존하지 않으며 BIOS 호출이나 외부 상태 읽기는 없다. 직접 writer/RTS 진입은 선행 read/write가 실행됐다고 추측하지 않는다.

47d24 JSR4e216은 return47d2a를 실제 RAM에 push한다.47d2a BCC는 Clear이면 기존47d3e, Set이면47d2e로 간다.47d2e JSRbee의 return은47d34이며, 그 BCS는 Set이면47d3e, Clear이면47d38이다.47d38은 CLR.L D0 후47f4a로 BRA한다. Unknown C를 분기에서 false로 간주하지 않고 checked 오류로 거부한다.

통제 alias의 하나는 A5-75bc가 incoming A7-4인47d24다. 초기 status가2여도 실제 JSR return00047d2a의 쓰기가 첫 BYTE를0으로 바꾼다. 두 번째 status5를 읽고 Set으로 반환할 수 있다. 이는 스택 쓰기 없는 helper 값 계산과 다른 결과이며 원본 관측으로 검증해야 한다.

다른 alias는 direct bee의 A7=10f002, return00047d34다. 요청 BYTE10f004는 return의7d와 같다. 복원 경로는 원래 return을 유지하지만 소비 경로는 실제 RTS 값을00040034로 바꾼다. 성공 경로와 지원 밖 target guard를 구분하고 차이를 가리지 않는다.

## 준비 상태 이후 선택과 사운드

47d46은 BYTE(A5+5681)의 sign을 검사한다. 비음수이면 D0=1 후 AND.B BYTE(A5+5684), 즉 bit0(mask1)을 검사한다.0이면47d5c, 비영이면47d58 BSR477ac(return47d5c)을 실행한다.47d5c는477ee로 BRA한다.

음수이면47d60에서 BYTE(A5+568e)를 읽는다.0이면47d72, 그 외 BYTE(A5+5683)의 bit0이1이면47da4,0이면47d72다.47da4 body는 이번 실행 전 경계다.

47d72는 WORD(A5+5688)를 D0.low에 읽는다.0이면47da0으로 간다. 비영일 때 timer WORD(A5+568a)가 비영이면 그 WORD를1감소시킨 뒤47da0으로 간다. timer가0이면 WORD(A5+5686)와 비교해 같을 때47d98, 다르면 D0.low를5686에 쓰고5688을0으로 쓴 후47d92 JSR3af8(return47d98)을 실행한다.47d98 BRA47da0,47da0 BRA480bc다. 사운드가 대기한 뒤에는 기존 실제 PC/A7에서 재개하며 이전 비교·쓰기·호출을 반복하지 않는다. 변수의 게임 내 의도를 주소 이상의 확정 이름으로 확대하지 않는다.

## 477ac와 35a2 화면 채우기

477ac은 D0.low=7162, D1.low=00ff, D2.low=0012, D3.low=0008을 순서대로 쓴 뒤35a2로 tail JMP한다. 각 register의 상위 WORD를 보존하며 추가 return을 push하지 않는다.

35a2는 BYTE300001에 D0.byte를 쓰고 A4=3c0000을 설정한다. D2.low가0이면 바로 종료 출력으로 간다. 그 외 D7=(D0.low<<16)|D1.low, D6.low=D3.low로 설정한다. D6.low가0이면 셀 출력을 생략한다. 각 셀은 unsigned D7>=75000000이면 원본 TRAP15 경계에서 checked 오류로 거부한다. 그 외 LONG D7을 live(A4)에 쓰고 D7+=10000, D6.low--를 수행한다.35f0과 달리 D7의 tile BYTE를 별도로 증가시키지 않는다.

열 끝에 D0.low+=20, D2.low--를 수행해 다시 폭을 검사한다. 종료 시 absolute WORD3c0004=0, LONG(A4)=82000000을 순서대로 쓰고 실제 RTS한다. 폭·높이0은 원본의 명시적 skip이며35f0의 감소 후 wrap과 다르다. 반복은 machine block 예산을 적용한다.

35bc 자체는 TST가 아니라 BEQ이며 직전 MOVE.W 또는 SUBQ.W가 설정한 Z를 소비한다. 현재 공개 상태에는 Z가 없으므로 임의35bc 진입을 D6 값만 보고 실행하면 원본과 다른 결과를 만들 수 있다. 이 진입은 checked unsupported로 거부한다. 정상 경로에서는35b4의 MOVE.W와35c0 block의 SUBQ.W에 해당 BEQ를 함께 처리하여 방금 계산한 실제 Z 의미를 사용한다.35ae는 실제 TST.W를 포함하므로 그 진입에서 D2.low를 검사할 수 있다.

출력은 기존 화면 초기화의 `VideoPortWrite` 규격을 사용한다.300001 BYTE,3c0004 WORD,3c0000 LONG/WORD를 명령 접근 단위로 순서대로 기록한다. 이는 watchdog/video 포트 trace이며 watchdog reset 시간이나 VRAM 장치 전체를 모델링했다는 뜻은 아니다. live A4가 이 제한된 출력 주소와 다르면 기존 RAM/PVC 쓰기 또는 checked unsupported 경계를 따른다. 일반 am_write의 장치 지원 범위를 넓히지 않는다. PVC는 기존 독립 모델과 WORD trace를 유지한다.

## 검증과 한계

JSR/BSR/BRA/BCC/BCS와 독립 RTS/LEA-only의 확인된 block만 C를 보존한다.4e216/bee의 실제 ANDI/ORI는 known C를 만든다. 나머지 새 block은 보수적으로 Unknown이다. TST·AND·SUB 등 내부 분기는 해당 실제 연산의 폭으로 계산하지만 일반 CCR/XNZV를 지원했다고 주장하지 않는다.

원본 C는 실제47d2a BCC/47d34 BCS와 기존47d42 BCC의 바로 뒤 경로에서 확인한다. Standalone helper return을 이 분기 PC로 놓는 경우는 통제 adapter라고 기록한다. 분할 실행과 fresh continuous 실행을 대조하고 SR 읽기·ROM patch·중간 register 주입·stack mask 없이 full64KiB RAM/16R/PC, ordered ports와 대기를 관측한다. C++ 재개는 직전 실제 출력과 명시된 RAM 변경만 입력으로 사용한다.

기존8개 MS5D kind3와 C++ loader/bus를 사용하며 리소스 형식을 바꾸지 않는다. API 실패의 전체 출력 보존은 원본 CPU fault rollback과 별개다.477ee/47f4a/47da4/480bc의 후속 body,47eac, 자연 scheduler·IRQ/timing·직접 플레이·전체 게임 복원은 미완료 범위다.
