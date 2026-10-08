# Stage frame480bc 후속 분석 계약

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 코드는 fixed 첫1MiB이므로 CPU 주소와 ROM offset이 같다. RAM offset은 CPU100000을 기준으로 구분한다. 메인이 원본을 읽은 후속 계약이며 이 문서만으로 C++ 구현·실행 비교 완료를 주장하지 않는다.

## 연결 순서와 남은 범위

480bc는47642,1a73c,49b0c,4aa88,b4a2a,6f1c2,4701e,e8a48,2efa6를 순서대로 호출하고480f0에서 반환한다. 1a73c 장면 프레임의 완료와 이 전체 caller 완료를 구분한다. 6f1c2의 현재 원본은 정확히 한 명령 `RTS`다. 그 뒤의 코드/자료를 이 함수에 포함하지 않는다.

47642의 d68e 생성은 scene-frame-control.md에 별도 계약이 있다. 49b0c는 입력 매핑과 동적 callback 경로를 가진다. 4aa88은 debug에 따른 추가 경로와 상태 buffer 갱신, b4a2a는49392/1c028/b481e를 호출한다. 4701e는 여덟 node에서43e38/46f52를 조건부 실행한다. e8a48의 할당/좌표/표 복사와 debug, 2efa6의 sound producer 대기도 남아 있다. 이 목록은 호출 관계의 분석 범위이며 미해석 callee를 비워 두어 전체 실행으로 포장하지 않는다.

## 입력 매핑49ab4

입력은 D0.byte/D1.byte와 A4의4-byte mask다. 기본 mask의 ROM49ab0..49ab4는 `10 20 40 80` **데이터**다. A4가 RAM10f01c 또는10f020인 경로도 있다.

D7=0, D7.byte=D0.byte&0f, D6.byte=D7.byte 순서다. Standalone helper의 D6 상위24비트는 보존한다. Caller49b0c가 그 전에 D6 전체를0으로 만드는 것과 구분한다. D2=4로 시작해 네 번 반복한다.

각 반복에서 D5.byte=(A4)+, D4.byte=D0.byte&D5.byte다. D4.byte와 mask가 같을 때 D7의 D2번 bit를 설정하고, D4.byte를 D1.byte와 AND한다. 그 결과가 비영일 때 D6의 같은 bit도 설정한다. 같은 mask가 아니면 D4에 D1을 AND하지 않는다. D2.byte를 증가시켜8이면 종료한다. D4/D5 상위24비트는 보존한다.

A4를4만큼 빼 원래 주소로 돌린 뒤 D2.byte=BYTE(A4+2)&BYTE(A4+1)로 만든다. 이 값이 비영이고 D6.bit6이 설정돼 있으면 D7/D6의 bit5를 모두 지운다. D0/D1은 변경하지 않는다. D2는 초기 MOVEQ 때문에 상위24비트가0이다. 원본 SUBQ.W의 대상이 A4인 경우는 주소 레지스터 전체 연산이며 WORD 절단으로 바꾸면 안 된다.

## 이전 값과 mask 적용

49afe는 D6.low=WORD(A1+2), D6.low&=fff0, D6.low^=D7.low, D6.low&=D7.low 순서다. D6 상위 WORD를 보존한다. Native EOR/AND를 전체LONG 연산으로 바꾸지 않는다.

49bb4는 D0.low=WORD(A1+4)를 읽은 뒤 그 RAM WORD를ffff로 쓴다. D7.low와 D6.low에 D0.low를 AND한 다음 WORD(A1+2)=D7.low, WORD(A1)=D6.low 순서로 쓴다. 입력·출력이 겹칠 수 있으므로 쓰기 전에 필요한 mask를 읽는 순서를 유지한다.

## 전체49b0c

첫 입력은 RAMd734 callback, 오브젝트100cb8, RAM4caa/4cab의 byte, 사용자 mask10f01c, 결과10d726이다. 둘째 입력은 RAMd738,100da8,4cb0/4cb1,10f020,10d72c다. 각 입력을 처리하기 전에 D7/D6 전체를0으로 만든다.

Callback이 null이면 D0.byte/D1.byte를 위 입력에서 읽고 BYTE RAM0012가2일 때 사용자 mask, 그 외 기본 ROM49ab0 mask로49ab4를 호출한다. D0/D1의 나머지 비트는 보존한다.

Callback이 비영이면 A0를 오브젝트 주소로 만들고289e로 callback marker270e를 검사한다. Marker가 일치하면 동적 호출을 생략한다. 일치하지 않으면 실제 `JSR(A1)` 뒤 결과 주소로 A1을 다시 설정하고49afe를 호출한다. 어느 경로든 결과 주소의49bb4를 실행한다. 첫 입력의49bb4는 BSR이고 둘째는 fall-through다. 동적 callback이 다른 register나 RAM을 바꿀 수 있으므로 미해석 callback을 임의의 D7 값으로 대체해서 전체49b0c 완료를 주장하면 안 된다.

49c20은 D0.low&=1, D0.low<<=2, A1=10d734+signed(D0.low), LONG(A1)=A0다. 49c32는 먼저 A0=0으로 만든 뒤49c20으로 분기한다. 49c66은 A0=49e34로 만든 뒤 같은 setter로 분기한다. 알려진 setter 호출과 실제 callback 대상의 근거를 추가 목록화한 뒤 callback 범위를 결정해야 한다. 후속 callback의 원본 계약은 아래에 추가했으며 실행 구현은 아직이다.

## 2efa6 sound 상태 전환

D1.byte=RAMd491을 보존한 뒤 RAMd490의0/비영을 D0.byte=00/ff로 바꿔 RAMd491에 쓴다. 비영으로 바뀐 최초 호출만 D0.low=1d28로3af8을 호출하고,0으로 바뀐 최초 호출만 D0.low=1d28로3c44를 호출한다. 그대로면 바로 반환한다.

3c44는 입력 D0.low를 stack에 보존하고 word queue에서 같은 command를0으로 바꾼 뒤 byte14, command 상위 byte, 하위 byte를 순서대로3ac8에 전달한다. 3ac8에는 이미 알려진 queue 대기가 있으므로 이 caller를 항상 즉시 성공하는 함수로 축약하지 않는다. Queue 인덱스의 정확한 지원 범위와 full register/pending 상태는 별도 분석·검증이 필요하다.

## 알려진 callback의 원본 계약 추가

아래는 메인이 원본 명령을 읽은 후속 계약이다. C++ 구현이나 실제 callback 실행 비교 완료를 뜻하지 않는다. Raw setter 참조 후보 목록은 `tools/inventory_stage_input_callbacks.py`로 재생성한다. Even offset의 인코딩 일치는 실제 코드 경계·도달성·A0 reaching definition의 증명이 아니다.

- 49e34: D7 전체를0으로 만들고 반환한다.
- 49d88: object42/4a LONG에서 camera d3a2/d3aa LONG을 빼고 각각 SWAP한다. Object78 WORD가0이면 target d73c, 그 외d73e다. 두 low WORD에서 target을 빼고 D3.low XOR D2.low의 N을 검사한다. N이면 D2.low와 A0를 stack에 보존하고49c32로 callback을 해제한 뒤 복원하고 NEG.W D2를 수행한다. D7=0 후 D2.low 음수는bit3, 양수는bit2,0은 그대로 반환한다.
- 49de6: D7=0, target 선택과 LONG 좌표 투영은 위와 같다. 현재 D2.low-target이0이거나 이전 D3.low-target과 XOR 결과의 N이1이면49c66으로 tail 진입해49e34를 설치한다. 그 외 D2의 부호에 따라 D7 bit3/2를 만든다.
- 49e38: LONG 투영이 아니라 object42/4a WORD에서 camera d3a2/d3aa WORD를 뺀다. Target 도달/교차 시 object15.bit7이 켜져 있으면 D7=0, A0=49f2c로49c20에 tail 진입한다. 그렇지 않으면 D2.low의 부호에 따라 D7 bit3/2 또는0을 반환한다.
- 49e9c: 49de6 이후 D0 LONG을 보존하고 D7.low&0c가0이면 D7=0 후bit5를 설정한다. D0 LONG을 복원한다.
- 49eba: CLR.B D0 뒤 `CMPA.L ($100cb8).L,A0`로 **메모리 LONG 값**과 비교한다. 즉시값 주소 비교가 아니다. 같으면 index0, 다르면1이다. RAMd732의 해당 bit가 이미 켜졌으면49de6만 실행한다. 꺼졌으면 bit를 켜고49de6을 실행한 뒤 D0 LONG을 보존하고 D0.low=D7.low, ORI.W20,D0를 수행하고 D0 LONG을 복원한다. 따라서 이 OR 결과는 버려지며 D7에bit5를 추가하지 않는다. 원본을 의도 추정으로 고치면 안 된다.
- 49ef0: 위와 같은 메모리 LONG 비교로 index를 만든다. RAMd732 bit가 켜졌으면 D0.low=object78,D7=0으로 반환한다. 꺼졌으면 D0 LONG을 stack에 저장하고49de6을 호출한 뒤 **D1 LONG으로** 복원한다. D2.low=D7.low&0c가0일 때 D1 번호의 bit를 RAMd732에 설정한다.
- 49f2c..49f66: D7=0, D1.byte는 object15.bit0의 SNE다. D0.low=object78이0이면 RAMd740, 그 외d741을 검사해 D2.byte를 SNE로 만든다. D1.byte XOR D2.byte가0이면 반환한다. 아니면 D2.byte가0일 때 D7.bit3, 비영일 때bit2를 설정한다.

49f66은 별도 함수다. D0=0 후 A0가 **즉시값**100cb8/100da8과 같을 때 각각 RAM4caa/4cb0 byte를 D0.byte로 읽고 A4=49ab0으로49ab4에 tail 진입한다. D1은 이 함수에서 초기화하지 않는다. 이 비교의 immediate 인코딩은49eba/49ef0의 absolute-memory 인코딩과 다르다. 알려진 callback만 지원하는 후속 API와 전체49b0c의 지원 범위는 별도로 정의해야 한다.

추가 직접 확인한 callback: 1bec0은 object15.bit7이1이고 objecta7.bit7이0이면 D7=0으로 반환한다. 그 외49f66을 호출한 뒤 D7.low&=000f를 수행한다. 1bee4의 setter는 A0=1bec0을 두 슬롯에 순서대로 설치한다. e73f2는 RAMde24 WORD를 D7.low에 읽고 반환하며 D7.high는 보존한다. 1d8cc는 RTS 한 명령이다.

1d5ac는4836e의 carry를 검사해 C0이면 object78 WORD로49c32를 호출하고, 어느 경로든 D7=0으로 반환한다. 4836e 계약은 추가 확인이 필요하다. 1d5e2는 object15.bit7이1이면1d628로 분기하며,0이면 D7=0 후 **A6+3a WORD**가 비음수일 때 D7.low=8을 만든다. 1d61a는 같은 flag가0이면 D7=0으로 반환하고1이면1d628로 간다. 따라서 전체 입력 callback API는 A6를 무조건 미사용으로 취급하면 안 된다.

1d628은 object78→D0.low,49c32 호출,49f66 호출 순서다. 49c32가 A0=0으로 만드는 효과를49f66 이전에 원래 object 주소로 복원하는 명령은 없다. 원본에 없는 복원을 넣으면 안 된다.

1d664는 D7=0, D1.low=object42-cameraXd3a2-objectae를 계산한다.0이면1d628, 음수면 D7.low에8, 양수면4를 OR한다. D2.low=object4a-cameraXd3a2-objectae를 계산하고 D1.low XOR D2.low의 N이1이면1d628로 간다. 1d6c2는 같은 형태에서 object46/4e와cameraYd3a6를 사용하고 음수1/양수2를 OR한다. 현재와 이전 좌표 모두 같은 camera WORD를 빼는 점을 보존한다. 이 callback들의 C++ 실행 비교는 아직이다.

4836e는 RAMd683.bit2가1일 때 carry0,0일 때carry1을 반환하며 일반 register/RAM은 바꾸지 않는다. 따라서1d5ac는 해당bit가 켜졌을 때 callback을 해제한다. 49c38은 A0=10d734,D0.low=(D0.low&1)<<2로 만든 뒤 해당 LONG이 비영이면carry1,0이면carry0이다. 49c56은 같은 주소 선택 후 LONG을 A0에 읽는다.

1da60은1d664와 같은 X 차분/부호 검사지만 현재차분0 또는 교차 시1da98로 간다. 여기서는 object78→D0.low로4d7a6을 호출하고 D0.byte 비영일 때 **반환된 A0**의78 WORD를 읽어49c32,49f66 순서로 호출한다. 4d7a6은 입력 D0.byte가0이면 A4=10dcba,A0=100cb8,비영이면 A4=10dce6,A0=100da8로 선택한다. 289e의 carry와 WORD(A4)가 조건을 만족하지 않으면 D0.low=0,D1..D4=0,D5=ffffffff,D6=0을 반환한다. 조건이 맞으면 record byte27과25/26/2a,WORD1c/20 및 ROM4cf64+index*16+10 조회가 있다. Byte27=0은TRAP15다. 후속 대조에서 기존 `player-record-capture.md`와 `read_player_record`가 D0..D6 및 조회/trap 계약을 이미 구현·검증했음을 확인했다. 기존 `player_record_lookup.ms5d`4092-byte 창을 재사용할 수 있다. 전체 callback 연결에는 추가 A0/A4 반환을 아래처럼 운반해야 한다.


4d7a6의 추가 주소 register 계약: 첫 D0.byte 선택에 따라 A0=100cb8/100da8,A4=10dcba/10dce6로 만든다. Inactive marker270e 또는 source 활성WORD0이면 그대로 반환한다. Active 비영index이면 반환 A4=4cf64+index*16이고 A0는 선택한 player 주소다. A1/A2/A3/A6/D7은 그대로다. 기존 read_player_record의 D0..D6 결과를 재사용하고 이 두 A register를 보완하면 원본 전체 일반 register를 운반할 수 있다.1da60에서 이 호출 뒤 D0.byte가0이면 D7은 이미 계산된 값을 유지한다. 비영이면 반환 A0의78 WORD를 읽어49c32→49f66을 실행한다. `game_records.ms5d`의20개 논리 record와4092-byte raw lookup 창은 서로 다른 규격이다.
