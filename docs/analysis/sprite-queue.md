# 스프라이트 표시 큐와 합성 데이터 참조

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
이 단계는 원본 실행 관찰과 정적 해석이며 C++ 큐 구현 완료가 아니다.

## producer 0xcd58

A5=0x108000.0xccd6은 256개 offset 테이블(base0x108b34)을0,12,24,...로 초기화하고 queue 상태를 지운다. 각 레코드는0x107f34+offset에12바이트다. 0xcd58은 RAM0x109152 callback을 호출한다. 초기화 직후 callback은 RTS0xcd50이다.

D0를 상/하위word U,L로 두면 첫 범위 검사는 `(L-0x40)&0xffff < 0x280`, 두 번째는 `(U+0x160)&0xffff < 0x400`이다. 통과하면 next index를(old+2)&0x1fe로 계산한다. 큐가 찬 경우 반환 또는 상태 변화를 기다리는 분기가 있어 단일 스레드로 무조건 반복 실행하면 멈출 수 있다. 해당 분기는 아직 동작 환경 미해석이다.

D1 bit6이0이면 일반 순서 테이블,1이면0x108f4e 임시 offset 목록을 사용한다. 0xce02는 이 임시 목록을 레코드 첫 word로 비교하여 일반 순서에 넣는 경로다. sort 의미와 실제 호출 시점은 아직 확인해야 한다.

초기 큐의 첫 삽입은offset12, CPU0x107f40이다. 세 long은 다음과 같다(각 word wrap 적용).

- long0: highword=D5.lowword, lowword=U<<6.
- long1: D1의 상위24bit 보존, 하위byte는bit0..2만 보존.
- long2: highword=D7.highword OR (L<<7), lowword=D7.lowword.

`tools/analyze_sprite_queue.py`는 경계값·두 경로48개 조합에서 원본을 실행했고64KiB RAM 전체가 명령에서 도출한 효과와 일치했다. 이 중16개가 범위 검사에 통과했다. 검증은 빈 큐에 한 항목을 넣는 조건이며 큐 충만·동시 소비를 검증하지 않는다.

## consumer 0xce82와 원본 packed ID

0xce82는 A2+8 long을 읽고 bits0..2에서bank selector를 얻는다. PVC 쓰기 결과 bank base는 `(selector+2)*0x100000`이다. 다음 두 단계 pointer 조회를 수행한다.

1. group=(packed>>3)&0xff. CPU0x200004+group×4의long을 읽는다.
2. item=(packed>>11)&0xfff. 위 pointer+item×4의long을 읽어 합성 데이터 A3를 구한다.

producer가L<<7을D7 상위word에 OR하는 위치는bits23..31이다. 이 부분은 위ID 조회bit0..22와 겹치지 않는다. selector에 따라 ROM 끝을 벗어날 수 있으므로 모든23bit값을 유효ID로 간주하지 않는다.

원본0xde162는 D7=0x2152,0xde17c는D7=0x2952로 설정하고 각각0xde170/0xde18e에서producer를 호출한다. 이를 실제 ROM에 적용한 참조는 다음과 같다.

| packed ID | bank base | group | item | 합성 CPU 주소 | ROM 오프셋 |
|---:|---:|---:|---:|---:|---:|
| 0x2152 | 0x400000 | 42 | 4 | 0x2cce60 | 0x4cce60 |
| 0x2952 | 0x400000 | 42 | 5 | 0x2cd3e8 | 0x4cd3e8 |

공통 group table CPU주소는0x2cc3f8이다. 첫 데이터는 `0100 ff50 ff80 1610`으로 시작하고 그 뒤4바이트 쌍들이 이어진다. 소비 경로는 첫word-0x100으로 바깥 반복 수를 준비하고 뒤의 좌표/열 정보를 읽는다. 첫 항목 크기는 다음 항목까지0x588바이트이며 `8+22*16*4`와 일치한다.0x1610을22열·16타일 길이로 해석하는 근거지만 아직 모든형식/크기 검증을 마치지 않았다.

0xcf1a 이후는0x8401 계열 위치,0x8001 계열축소 정보와tile/attribute 쌍을비디오 포트에 쓰는 루프다.0xd220부터 source의첫word에D3를더하고D1.lowbyte를XOR한후쓰며 다음word도쓴다. flip·팔레트·확장tile bit의 전체 대응과consumer 진입규약을 다음 단계에서 실행으로 검증해야 한다.

현재는 합성 데이터의 소재와 ID경로를 확인했다. 아직 이 레코드를 최종 리소스로 패키징하거나 실제 오브젝트 외형을 완성했다고 주장하지 않는다.
