# 스테이지 / 구역 선택 콜백9602

원본 프로그램 SHA256:`29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
코드와 데이터 CPU 주소는 고정 ROM 오프셋과 일치한다.

## 원본의 선택 상태

descriptor958a의0번 항목은 텍스트/callback0,1번은 구분선/callback0,2..9번은 callback9602다. 행번호에서2를 뺀 값이 그룹0..7이다. RAM107dfe는 현재 선택 그룹,107dff..107e06은 그룹별 구역byte다.

- event0: 현재 행-2를107dfe에 기록하고 화면을 다시 그린다.
- event1: 선택 그룹의 구역byte를1 감소한다. 이전값0이면 감소 후 값ff에 그룹의 구역수 하위byte를 더한다. 초기값을 미리 정상범위로 보정하지 않는다.
- event2: 구역byte를1 증가시킨 뒤 구역수 하위byte보다 작지 않으면0으로 만든다. ff의 증가도 byte 순환한다.
- event3:107dfa word=1,4823a로107dfe의 그룹을 선택한 뒤48250으로 그 그룹의 구역byte를 선택한다. mode=2, A2=head로 닫는다.
- event4: mode=2/A2=head만 설정하고 종료word는 그대로 둔다.
- event5: 선택 상태를 바꾸지 않고 다시 그린다.
- event6:107dfe+2를byte로 계산하여a280 지정 선택을 실행한다. 이전행/새행을 모두 다시 그린 뒤 event0을 대기시킨다. 선택 그룹byte 자체는 이event에서 바뀌지 않는다.
- 그 외 event는 상태/출력 변화가 없다.

좌우event가 변경하는 그룹은107dfe이고, 화면에 그리는 그룹은현재 행-2다. 이 두 값이 다를 때도 같은 값으로 합치지 않는다. C++ 좌우편집은 유효한 그룹0..7을 요구하며 다른값으로 메뉴슬롯을 훼손하는 경로는 명시적으로 거절한다.

## 출력 순서와 공유 리소스

96c8 이후는 행-2의 구역을 조회하고107e07=group+1,107e08=area+1을 각각byte로 기록한다. 이름 pointer는107e0a에 저장한다. 기존stage catalog의 원시레코드와MS5D 메뉴/폰트, null-name prefix를 사용한다.

1.9f36/9f78 좌표·스타일로956c의26공백과`\r`을 렌더링한다.
2.955e의`\c0%1x:%2x %s`를3a70 포맷터로 출력한다. 인자는107e07,107e08,이름pointer다. 실제 원본인자표 주소는 콜백entry stack-12다.
3.9f12의 메뉴 원점에서 word로x+3/y+1을 계산한다. 앞 단계9f36의byte 덧셈과 다르다.
4.포맷터가 남긴style로956c를 다시 출력하고, 같은 위치에서이름을3918/e84c8로 출력한다.

범위밖 구역의 이름pointer0도 처리한다. 위2의`%s`는ROM벡터prefix의최초0을glyph로 출력하지만, 위4의 일반3918문자열은최초0에서 즉시끝난다. 같은pointer라도 서로다른경로라서 하나의빈문자열처리로 치환하지 않는다.

## 중첩 이동과 다시 그리기

`dispatch_menu_event`의9602분기에 연결했고, `draw_menu_item`/`draw_menu_text`/`navigate_menu`에 stage context를 전달할 수 있도록 확장했다. 행그리기는일반항목텍스트 이후9602/9802의event5를 실행한다. context의stack값은 항상실제callback진입A7이다.

9602event6이a280으로직접점프할때진입stack은S다. 이전/새행을 그리는BSR이4바이트,9e0c의A1-A3저장이12바이트,9e10의BSR이4바이트를더사용하므로중첩9602entry는S-20이다. 임의의고정주소를쓰지않고이값으로복사한context를전달한다. rowhelper는A2를보존하므로event6결과A2는현재slot이다.

행/이동API에선택적인final_line출력을추가했다. 이전행과새행의D3를순서대로전달하며,숨겨진행은기존값유지,실패는호출자값보존이다. stage9802의native포맷은마지막literal공백뒤0이므로D3는포맷터RAM104cd8에서얻는다.

## 검증

```
make all test
.venv/bin/python tools/verify_stage_area_menu.py
.venv/bin/python tools/verify_stage_group_menu.py
.venv/bin/python tools/verify_menu_navigation.py
```

검증은원본9b3e에서실제9602,query/state helpers,3a70,글꼴,지정선택a280과행그리기9d3a까지실행한다. 명령/콜백을stub으로치환하지않는다. 전체64KiBRAM,ordered비디오포트,A2/외부점프를비교한다. 여러초기행/선택그룹의불일치,구역0/마지막/범위밖/ff,숨김/표시,head/current,좌표·줄·stack경계를포함한다. 수정된3,584조건이모두일치했고,이중보이는event6의768조건은실제로107..408개포트쓰기를발생시켰다.

C++단위검사는구역순환,확인/취소,중첩formatter의S-20 인자pointer,리소스부족/잘못된stack으로인한늦은실패시RAM/출력/줄/A2보존을포함한다.

## 남은 연결

구분선1번의그리기는아직미지원이다. event6의이전선택이구분선인경우와958a전체그리기는명시적오류로남는다. 기본이전선택0 또는실제선택행2..9의이동은검증범위다. 부모다시그리기/스택추가에context와호출깊이를전달하는작업,헤더9430/전체a370,실제스테이지실행도남았다. workRAM내CPU스택흔적,전체CPU레지스터/flags,픽셀및타이밍은동등성주장에포함하지않는다.

## 전체 D1/D3 전달

직접 9602 콜백은 선택적 전체 D1/D3를 입출력한다. 입력 D3 하위 word는 기존 line과 같아야 한다. event3의 4823a/48250 및 event4/7은 D1/D3를 유지한다. event0/1/2/5는 앞부분의 9f36/96de와 뒷부분의 9f12에서 D1 전체를 지우므로 최종 D1은 마지막 이름 스크립트의 style word다. 9738은 포맷터가 실제로 반환한 style을 저장하고 974c에서 복구한다.

D3는 첫 지우기 스크립트, 포맷터, 마지막 지우기와 이름 출력의 순서로 전달한다. 각 3918은 하위 word를 시작 좌표로 교체하고, 실행한 위치 제어는 상위 word도 지운다. event6은 a280 이동으로 진입하므로 두 행 다시그리기의 전체 D1/D3를 이어 준다. 내부 콜백 stack은 기존 진입값-20이다. 전체 상태와 레지스터는 성공 시에만 반영한다.

새 진단 CLI: `build/dispatch_stage_area_menu INPUT_RAM MENU_MS5D FONT_MS5D STAGES_DIRECTORY OUTPUT_RAM OUTPUT_PORTS EVENT D1 D3 CALLBACK_STACK`. 실제 MS5D 런타임 리소스를 읽고 A2/line/D1/D3 JSON을 출력한다.

- `.venv/bin/python tools/verify_stage_area_registers.py`: 원본 3,936조건, 순서 있는 포트 504,536개 및 출력 보존 오류 검사 31조건 통과. 보고서 SHA256 `a4e1cadf1bedbf87c1ec457bc5de298332a036f8231f85fb9dc3b89c9866fc52`.
