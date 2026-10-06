# 일반 직사각형 스프라이트 합성 경로

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 코드 진입점0xce82. bank base0x400000에서 packed ID0x2152/0x2952를 시험했다.

## 확인한 단일 블록 형식

| 오프셋 | BE word | 확인한 용도 |
|---:|---|---|
| 0 | 0x0100 | 이 구현이 지원하는 단일 블록 header |
| 2 | dx | 좌표 상위word U에 더하는 가로 오프셋 |
| 4 | dy | 원본은 부호 반전하여 D6 상위word에 보관 |
| 6 | width<<8 \| height | 열 수와 열마다 타일 수 |
| 8 이후 | attribute,tile 순서의 word쌍 | column→row 순서 |

ID0x2152는 ROM0x4cce60에서22×16,1416바이트다. ID0x2952는 ROM0x4cd3e8에서39×27,4220바이트다. 후자의 범위도 실제consumer실행으로 확인했다. 두 데이터 외의 header나 일반복수블록은 아직 이 API가 지원하지 않는다.

## 명령 생성

C++ `emit_sprite_rectangle`은 원본consumer의 일반 단일 직사각형 경로에서 비디오 쓰기와 다음 슬롯 번호를 재구성한다. 슬롯 한계를 먼저 검사하고, 가로 좌표를64배로 표현한word에 열마다0x400을 더한다. `(xword+0x200)&0xffff >= 0x5000`이면 해당열을 건너뛰며 슬롯은 소비하지 않는다.

표시하는 열마다0x8401+slot에 가로 위치,0x8001+slot에0xffff 축소 값을 쓴다. 이어((slot+1)×64+row×2+1)에 속성,그 앞의짝수주소에타일word를쓴다. source attribute에style 상위byte를word 덧셈한뒤style 하위byte를XOR한다. 순서와16bit wrap을 보존한다.

pinned MAME neogeo_spr.cpp는 실제 tile ID를 `((attr<<12)&0xf0000)|tile_word`로 계산한다. palette는attr>>8이며bit0/1은뒤집기,bit2/3은자동animation에관여한다. 예컨대 source attr0x0040/tile0x275e는타일0x4275e를가리킨다. 이 하드웨어 해석은 아직 현재 출력에 rasterizer로 연결하지 않았다.

## 검증과 범위

```
make build/emit_composition
.venv/bin/python tools/verify_sprite_composition.py
```

두실제ID,5개U좌표,2개style,4개슬롯구간(빈구간·한칸·전체·마지막한칸)의80조합에서 원본0xce82 실행의 모든비디오쓰기 순서와다음슬롯이C++와일치했다. 첫ID의U=160,style0x1500,슬롯0..379에서는20열680쓰기다. 원본D6/A3도기록하여후속호출규약분석에보존한다.

이 진입점에서style하위bit를변경한검증은실제flip dispatch가맞다는증명이아니다. 원본은flip별별도진입점도가지며그경로는미검증이다. dy와레지스터부수효과,세로위치제어0x8200계열,전체큐소비,스프라이트화면합성은아직남아있다. 함수이름의rectangle은지원형식을한정하며전체원본consumer대체완료를뜻하지않는다.

raw합성파일과trace는artifacts/sprite_composition에분석용으로저장한다. 이후공통리소스규격·로더와연결해야하며현재raw시험파일을최종런타임카탈로그로취급하지않는다.

## 세로 제어와 슬롯 재사용: 0xf246

후속 분석에서 원본 0x16bba/0x16cfa의 큐 소비 경로를 찾았다. 두 경로는 RAM0x108d3c의 bit7과 슬롯 범위를 사용해 서로 다른 dispatch table을 선택한다.0x16d7c의 table0xf226 첫 entry는0xf246으로 연결된다. 실제 호출 시점과 전체 동시 처리 규약은 아직 미확인이다.

0xf246은 같은 packed ID와 합성 데이터를 읽지만, header의dy를 사용하여 `(((V-dy)*128)&0xffff)|height`의 세로 제어word를 만든다. V는producer D0 하위word에서 유래하며 queue record+8 상위word의bits7..15에 저장되어 있다.

이 경로의 A4+2는 슬롯limit, +4는다음slot, +6은이미준비된끝slot이다. 가로clip을통과한각열은0x8201+slot의Y제어를먼저쓴다. slot<cached_end이면가로위치·축소·타일쓰기를생략하고slot만증가한다. 그렇지않으면기존일반경로와같은X·zoom·attribute/tile쓰기를이어간다. 이것으로이전분석에서Y쓰기가없었던이유를설명할수있다.

C++ `emit_sprite_rectangle_refresh`에이경로를추가했다. 기존API와공통명령생성코드를공유하되기존API출력을보존한다. dy의부호·V범위는unsigned모듈러계산으로원본word연산을따른다.

```
make build/emit_composition_refresh build/emit_composition
.venv/bin/python tools/verify_sprite_refresh.py
.venv/bin/python tools/verify_sprite_composition.py
```

두ID,가로3종,세로4종(0,384,511,65535),cached_end3종,슬롯구간3종의216개조합에서원본0xf246의모든쓰기와다음slot이C++와일치했다. 이전일반경로80개도회귀통과했다. 결과는artifacts/sprite_refresh/verification.json에저장한다.

이로써일반단일직사각형의Y/X/tile제어가준비되었으나,실제큐스케줄링·flip·여러블록·화면래스터화는여전히별도작업이다. cached_end라는이름은비교조건에대한분석용명칭이다.

## C++ 리소스와 실제 팔레트 연결

원본0xde12c에서 A0=0xddf08,0xde130에서 등록 함수를 호출한다. 해당 테이블은 slot17..24에 source ID0xe8d..0xe94를 flags1로 등록하며 slot8/9/10/15/13/14에0xb03/0xb04/0xb05/0xb06/0xe96/0x9cf를 등록한다. 따라서0xde170의 style0x1500과0xde18e의 style0x1600은 각각 slot21/source0xe91,slot22/source0xe92에 연결된다.

이 테이블은 다른 장면 테이블과 독립된 초기 상태에서 검증한다. 서로 다른 장면의 slot 등록을 한 상태에 누적하면 실제 사용 문맥을 잃는다. 원본3ef2→8da2→7196→72fa 실행 결과와 확장된17개 MS5P 색상값이 일치했다.

MS5C 로더와 emit_sprite_resource를 추가했다. `verify_sprite_refresh.py --runtime-resources`는 MS5C를 실제 C++ 입력으로 사용하고 원본0xf246을 새로 실행한다. 두 ID 각각의 호출 style로216개 조건의 순서 있는 비디오 쓰기와 다음 슬롯이 일치했다. 이는 명령 생성 검증이며 완성 스프라이트 픽셀·전체 프레임 스케줄 검증은 아니다.

## 역방향 슬롯과 소비 호출부

준비 루틴0x16bba는 먼저0xce02에 태그0을 넘겨 지연 큐를 합치고0x166bc를 호출한 뒤0x108d36과0x108d34가 같아지기를 기다린다. 0x108d3c bit7이 설정되면 큐를 앞에서 순회해0xce62 분기표를 호출하고, 아니면 뒤에서 순회해0x11792 분기표를 호출한다. 마지막에는0x108d3a를0x108d36/38에 복사하고0x108d3d를0xff로 설정한다.

갱신 루틴0x16cfa는0x108d3d bit7을 지우며, 이전 값이0이면 바로 반환한다. 준비되어 있으면0x108d3c bit7을 반전시키고 이전 값이1일 때 앞방향0xf226 표,0일 때 역방향0x13b46 표를 선택한다. 따라서 방향은 준비된 큐를 소비할 때 교대하며 실제 호출 주기는 별도 확인이 필요하다.

레코드+6 style의 bit2로 A4=0x108d3e/0x108d46 슬롯 영역을 선택한 뒤 그 bit를 지운다. 레코드+4가0xffff가 아니면 분기표 인덱스에4를 더하고, style하위 bit0..1을 합쳐4배 하여8개 분기 중 하나를 고른다. 여기서 직접 검증한 일반 단일 직사각형은 각 표의 첫 번째 경로다. 다른 경로와0x166bc의 사전 처리는 아직 복원하지 않았다.

역방향 일반0x117b2는 A4+6을 현재 slot, A4+4를 하한으로 사용한다. 보이는 열마다 먼저 slot을1 감소시키고 X/zoom/타일을 쓴다. 열 데이터는 기존의 왼쪽→오른쪽 순서다. 이미지 flip과 구별한다. 역방향 refresh0x13b66은 A4+0을 하한으로 사용하고 감소된 slot에 Y를 먼저 쓰며 slot>=A4+4이면 이미 준비된 X/zoom/타일 쓰기를 생략한다. 다음 slot은 A4+6에 저장한다.

C++는 동일한 내부 계산을 공유하되 방향별 경계·감소시점을 명시한다. verify_sprite_reverse.py는 원본0x117b2/0x13b66과400조건을 비교한다. `--runtime-resources`는 refresh360조건에서 MS5C로더와 emit_sprite_resource의 reverse 옵션도 확인한다. 기존 정방향80+216조건은 회귀 비교한다. 전체 소비자 타이밍, 두 영역의 정리 명령, 종료 carry flag는 아직 C++ 스케줄러로 검증하지 않았다.
