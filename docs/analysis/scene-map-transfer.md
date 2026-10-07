# 장면 맵 사각형 전송 183c6 분석

원본 decrypted 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 코드 주소는 고정 첫1MiB CPU 주소=ROM offset이다. 근거는 `artifacts/scene_paths/disassembly.json`의183c6..185fa 창과 실제 원본 bytes다. 메인이 명령 순서를 직접 해석했다. 원본 실행 관찰 및 C++ 대조는 별도 결과로 기록한다.

## 입력과 clipping

A0는 RAM node, A1은12byte descriptor다. Descriptor +0/+2는 primary/secondary selector, +4/+6은 width/height이다. D0/D1은 source column/row, D2/D3은 전송 column/row count, D4/D5는 목적지 좌표의 WORD다. A5=108000을 전제로 bank shadow는 RAM100010이다. D0..D7와A2/A3/A4 scratch까지 결과를 보존해야 한다.

183c6..183f0은 x축,183f0..1841a는 y축을 자른다. 단순 signed rectangle 교집합으로 치환하지 않는다. 아래 연산은 WORD wrap이며 별도 설명 없으면 register 상위 WORD를 유지한다.

1. D7=descriptor dimension, count-=1, D7+=count, coordinate+=count.
2. unsigned coordinate>=D7이면185f4에서 CARRY만0으로 만들고 복귀한다. 앞에서 변경한 register는 남는다.
3. D7-=count; coordinate-=count. 두 번째 subtraction에 borrow가 있으면 x축은 destination-=coordinate, y축은 destination+=coordinate를 수행한다. 양쪽 모두 count+=coordinate 후 coordinate는 MOVEQ로 전체32bit0이 된다.
4. count+=1; D7-=coordinate; D7-=count. 마지막 subtraction에 borrow가 있으면 count+=D7.

통과하면 D4.low&=31, D5.low=(~D5.low)&31. D0..D5를 MOVEM.W로 저장하며18530에서 각각 sign-extended32bit로 복원한다. 특히 원래 high WORD 보존이 아니다. Early reject에는 이 복원이 없다. Count0과 비정상 dimension도 이 원본 연산 경로와 구분해야 한다.

## Primary 영상 쓰기

RAM100010=1, word port2ffff2=2000, word port2ffff0=0 순서로 bank3을 선택한다. 이때 CPU200000..2fffef=물리ROM300000..3fffef이며 PVC tail은 데이터로 읽지 않는다. CPU200004의 LONG root에서 `sign16((selector<<2)&ffff)` 변위의 LONG map pointer를 읽고4를 더한다. Map header는 이 루틴에서 읽지 않으며 descriptor의 height를 사용한다.

Node+26 WORD가 음수면 primary cell 읽기와 VRAM 쓰기만 건너뛴다. Root/lookup 읽기와 bank 전환은 이미 일어난다. 그렇지 않으면 첫 source cell은 map+4+4*(column*descriptorHeight+row)다. 다음 column으로는 `ADDA.W(height<<2)`를 사용하므로 이 변위는 WORD wrap 후 sign-extension이다.

영상 주소 구성에는 node+3a의64byte column control이 쓰인다. 목적지 column을2배하여 high control byte를 읽고 ASR.B3→ADD.B자기자신→ADD.B목적지row2배→AND.W003e를 수행한다. Slot은(node26+1)*2이며 slot과 목적지column2배를 더한 WORD를 LSL.W5하고 위 row offset을 더한다. 주소WORD를SWAP으로D7상위에 두고 각 source BE16을D7하위에 실어 LONG port3c0000으로 두 번 쓴다. 두 번째 쓰기 전 D7전체에10000을 더한다. Row 증가의 ADD.B/SUB.W 순서와 wrap도 유지한다.

184d2..1852e에는 별도 zero-write 코드가 있지만183c6 진입의 확인된 흐름은 이를 통과하지 않는다. 이 블록을 primary 음수 slot 처리로 잘못 연결하지 않는다. 다른 entry의 도달성은 별도 조사 대상이다.

## Secondary RAM 쓰기

18530 MOVEM.W 복원 후 RAM100010=0,2ffff2=1000,2ffff0=0으로 bank2를 선택한다. CPU와 물리ROM offset은200000..2fffef에서 수치상 같다. Descriptor+2가0이면 secondary 조회를 건너뛴다. 그렇지 않으면 CPU200010의root와같은signed WORD lookup 규칙으로 LONG pointer를 읽는다.

일반 pointer에서는 A2=pointer+sign16((sourceColumn<<2)&ffff). Source row offset은sign16((sourceRow<<2)&ffff)이다. 원래 clipped column count를WORD로2배하며 각 반복에서 다음을 수행한다.

- A4=offset entry 자체의 주소+sign16(BE16(entry))+signed row offset. A2는2bytes 전진한다. 상대 offset의 기준은 table 시작이 아니라 각 entry 주소다.
- Source A4부터 clipped row count개의 LONG을 순차로 읽어 node+80+column ring offset+(row offset&007e)에 쓴다. Row offset은4씩 증가한다.
- 목적지 column ring offset은 초기 D4<<8, 각 column 시작에&1f80, 각 종료에+80이다. Row offset 초기값은D5<<2다.
- Row loop 종료 시D6.low=0이며18598의 ADDA.W D6는0을 더한다. 따라서 원본1개 primary column은2개의 secondary offset entry를 소비한다.

Pointer ffffffff는 sentinel이다. 같은2배 column 수에 LONG0을 쓰지만 row mask는007c다. 일반 경로의007e와 같다고 가정하지 않는다. 이 경로의 존재와 canonical 참조에서 발견되는지는 별도로 기록한다.

마지막으로 bank2 shadow/port 쌍을 다시 쓰고 node+7a byte의bit7을 세운 뒤 CARRY=1로 복귀한다. Selector0이라도 마지막 bank2 port 쌍은 생략되지 않는다. Node/descriptor/column cache가 RAM에서 겹치면 앞선 쓰기 이후 LIVE 읽기 순서를 유지해야 한다.

## 리소스와 범위

Primary는 기존 scene_maps MS5D를 사용한다. Secondary는 알려진 descriptor의 full width/height,source column/row0을 기준으로 offset entry와각cell 읽기 창을 목록화한다. 동일 source span 공유와 overlap을 보존하고, 추출할 때 실제 읽기 창의 union만 기존MS5D kind2로 포장한다. 이 union은 전체 논리 자료의 길이나 전체 게임의 모든 동적 접근을 증명하지 않는다. Secondary 자료를 collision이라고 단정하지 않는다.

현재 전체1a7a8,19e64 handler,일반1a5a4와47a94 이후 자연 실행 연결 및 직접 조작 가능한 스테이지 화면은 미완료다.
