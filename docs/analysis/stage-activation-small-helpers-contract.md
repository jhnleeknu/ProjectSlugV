# 활성화 경로의 작은 helper 계약

canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 fixed CPU 주소와 ROM 오프셋은 같다. 메인이 원본 명령을 직접 읽었다. 아직 각 helper의 새 C++ 연결/원본 비교 완료를 뜻하지 않는다.

## 4e216 — 두 상태의 종료 조건

D0.byte=BYTE(A5−75bc)를 읽는다.0 또는5이면 D0.byte=BYTE(A5−74f8)를 읽고, 이 두 번째 값이0 또는5일 때만carry1로반환한다. 첫 번째 값이0/5가 아니면 두 번째 주소를 읽지 않고carry0으로반환한다. 다른레지스터와RAM은그대로이며D0상위24bit도보존된다. 실제로 읽은 마지막 상태BYTE가D0에남는다. BYTE검사이므로A5의홀수자체를거부하지않는다. 접근하지않는주소의유효성을미리요구하지않는다.

## bee — 요청 BYTE 보존/소비 판정

D0.byte=absolute BYTE(10f004)를읽고같은RAM BYTE를0으로쓴다. A0=10fdb6; BYTE(A0)를D1.byte로읽으며A0를1증가시킨다. 이값이1또는2이면 저장했던D0.byte를10f004에다시쓰고carry1로반환한다. 첫값이다르면 다음BYTE도D1.byte로읽고A0를1증가시킨다. 둘째값1/2도같이복원/carry1이며그외에는10f004=0을유지하고carry0이다.

따라서최종A0는첫째성공이면10fdb7,둘째를읽었으면10fdb8이다. D0/D1의상위24bit는보존된다. D2..D7/A1..A6는보존되며A5값과무관한absoluteRAM접근이다. 이정확한bee..c34 범위에는BIOS/외부장치호출이없다. 인접한c64의다른기능을이helper에섞지않는다. 별도의callback/리소스도필요하지않다.

## 16ed2 — signed WORD에 따른 object bit

D0.low=WORD(A5+d3e)를읽어상위WORD를보존한다. 이를WORD(A5+d46)와signed16bit로비교하여미만이면BYTE(A6+15)의bit2를세우고,이상이면bit2를지운다. 그밖의flag bits와레지스터는보존한다. unsigned 비교로대체하지않으며−32768/32767경계를확인한다. 두WORD를읽은뒤flag BYTE를변경하므로그BYTE가비교피연산자와겹치더라도원본읽기·쓰기순서를보존한다. 실제WORD주소만짝수정렬이필요하며A6 자체가홀수여도flag BYTE가유효하면허용한다.

## 49f8c — animation state 초기화

원본순서는 A0=A6+26, BYTE(A6+18)=0, WORD(A5−7ff0)=0, WORD1000→2ffff2, WORD0→2ffff0, A5==108000 검사다. 같지않으면TRAP15이다. 정상경로는 LONG(A0)=A1, WORD(A0+4)=0, WORD(A0+6)=D0.low를순서대로기록한뒤RTS한다. A0만변경되며D0..D7/A1..A6는그대로다.

API에서성공은정상반환만뜻하고TRAP/잘못된RAM span은checked실패로표현한다. 실패의RAM/레지스터/기존ports는보존한다. 정상출력은기존VideoPortWrite의두WORD쓰기를순서대로제공한다. 해당범위는banked script를읽지않으므로포인터A1의유효성이나리소스를미리요구하지않는다. 실제PVC전환과RAM100010 shadow의연결은상위기존bank처리규칙을따른다. 오직RAM shadow만바꾸고원본포트쓰기를생략하지않는다.

A6 자체가RAM object 시작주소여야한다는추가제약을만들지않는다. 도달하는BYTE/WORD/LONG각span과WORD/LONG짝수정렬을검사한다. 예를들어A6=fffea이면A0=100010으로bank shadow와state pointer가겹치므로초기clear뒤A1 LONG쓰기의실제순서를보존해야한다. 이때최종RAM shadow는A1값으로덮일수있지만실제출력포트는여전히앞서기록한두WORD뿐이다. shadow를다시0으로강제하거나추가PVC쓰기효과를만들지않는다. 이초기화에는대기없으며후속49fc6의sprite대기는별도상태다.

## 공통 검증

전체64KiB RAM/15레지스터, 앞두helper의반환carry,49f8c의orderedPVC쓰기를원본에서관찰한다. checked오류는원본TRAP의완료동등성으로주장하지않는다. 원본ROM을바꾸거나helper를host stub으로대체하지않는다. A7/CCR전체/cycles/물리mirror/자연scheduler/직접플레이는이작은helper의증거로완료선언하지않는다.
