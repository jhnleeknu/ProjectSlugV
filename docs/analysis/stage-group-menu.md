# 그룹9..18 선택 메뉴 콜백

프로그램 SHA256:`29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
이 문서의 코드/문자열 CPU 주소는 고정 ROM 파일 오프셋과 같다.

## 978a/9802의 동작

descriptor978a는10개 항목으로 구성되며 모두 title976a, callback9802, argument0이다. 그룹 번호는 스테이지 목록의 원본 인덱스이고 실제 플레이 순서나 자연스러운 도달 가능성을 뜻하지 않는다.

- event3: 종료 word107dfa=1, 그룹=row+9를4823a로 선택하여10d680에 기록하고10d681의 구역을0으로 초기화한다. 닫기 mode107f1b=2, A2=head.
- event4: 닫기 mode만 설정하며 종료 word는 유지한다. A2=head.
- event5: FOR/name 문자열을 렌더링한다. 슬롯의 보이는 높이와 관계없이 콜백 자체는 실행된다. A2는 콜백 진입 당시 A7 값으로 남는다.
- 나머지 event는 RAM/포트에 영향을 주지 않는다.

그리기는9f36의 byte 좌표계산과9f78의 팔레트 선택을 따른다. x는 padding(원본flags0이면3)을 더해 byte 순환하고 y도1+row를 더해 byte 순환한다. 이후x<<5와 ADD.B y, ADD.W7000으로 VRAM주소를 만든다. 이를 word 덧셈으로 단순화하지 않는다.

RAM107e07에는row+1,107e0a에는4827e가 조회한 이름 pointer를 기록한다. 그룹row+9의 구역0을 선택한 뒤9781의 `FOR %s `를 기존3a70 C++ 포맷터로 출력한다. 다른 메뉴 뒤에 가려진 비선택 행은style603, 그 외 nativeflags0 경로는style3이다.

## 이름 pointer0의 실제 읽기

원본 그룹9..15는 비어 있어 이름pointer0을 돌려준다. `%s`는 최초0도 glyph0으로 출력하므로, 현재 검증의 카트리지 ROM vector mapping에서는 `00 10 f3`를 출력하고 다음0에서 끝난다. 의도된 이름이나 빈문자열이라고 정정하지 않는다.

`pack_stage_catalog.py`가 기존 출력은 유지하며 `stage_null_name.ms5d`/manifest를 추가한다. 기존MS5D v1, CPU/ROM0, payload4바이트 `0010f300`, 파일36바이트다. 이는 이름 조회 실패 후 소비되는 원본 벡터 prefix다. BIOS 벡터 매핑을 바꾼 실행까지 동일하다고 주장하지 않는다. 그룹16..18은 기존 카탈로그 레코드의 실제 이름을 사용한다.

## C++ 연결 및 스택 주소

`dispatch_stage_group_menu`를 `dispatch_menu_event`의9802 분기에 연결했다. 기존 parent/debug 호출은 추가 인자 없이 유지된다. 그림을 그릴 때만 font와 `StageGroupMenuContext`의 catalog/null_name/콜백 진입stack주소가 필요하다. RAM과 A2/포트 결과는 전체 작업이 성공할 때만 반영한다.

원본9874가 이름pointer를 stack에 push하므로 포맷터의 초기 인자주소는 `callback_stack-4`다. 인자를 소비한 후104ce4의 다음pointer와 A2는 `callback_stack`이 된다. 포맷터는 이미 지원하는 외부 인자 byte 배열을 사용한다. 하드코딩한 가짜 인자주소로 RAM 결과를 덮지 않는다.

현재 context는 고정 ROM/64KiB work RAM보다 높은 짝수 diagnostic stack만 지원한다. 원본CPU가 work RAM 안에 쌓는 모든 스택 흔적을 모델링한 API가 아니다. 원본과 비교하는 stack 자체는 work RAM 밖에 두며, 그 주소가 포맷터 상태/A2에 남는 효과를 비교한다. 자연스러운 전체프레임 연결 시 호출 깊이와 CPU스택 취급을 별도로 다뤄야 한다.

## 검증과 사용

```
.venv/bin/python tools/pack_stage_catalog.py
make all test
.venv/bin/python tools/verify_stage_group_menu.py
.venv/bin/python tools/verify_menu_event.py
```

원본9b3e에서 실제9802와4827e/4823a,3a70,9f36/9f78,닫기 경로를 변경 없이 실행했다. 1,120조건에서 전체64KiB RAM, 비디오 포트 순서·주소·폭·값, A2/외부점프 결과가 C++와 일치했다.

- native10행×event0..7×head/current×선택상태:320조건.
- byte좌표/줄/폭/진입stack 변화:720조건.
- 확인·취소의 종료word1/ffff 보존/변경:80조건.

카탈로그/메뉴/글꼴/벡터prefix도 원본과 비교했다. 단위검사는 없는리소스, 잘못된stack·행과 실패 후 RAM/A2/출력보존, 실제prefix의3glyph출력, 그룹18선택과취소word보존을 확인한다. 부모이벤트975조건 회귀와 전체테스트도 통과했다.

기존 CLI 뒤에 카탈로그 경로와 콜백 진입stack주소를 추가한다.

```
build/dispatch_menu_event INPUT_RAM MENU_MS5D OUTPUT_RAM OUTPUT_PORTS EVENT LINE FONT_MS5D STAGES_DIRECTORY CALLBACK_STACK
```

인자형식 예: 메뉴 `extracted/runtime/control_menu_tree.ms5d`, 글꼴 `extracted/runtime/menu_fonts.ms5d`, stage경로 `extracted/runtime/stages`, stack `0x1feffc`. RAM은 별도로 준비한 실제 메뉴 슬롯 상태다. 입력과 겹치는 출력 경로/inode를 거부한다.

## 남은 작업

다른 스테이지/구역 콜백9602,9802 event5를 전체행그리기/이동/부모다시그리기에 연결하는 작업, 구분선 및 헤더9430/전체a370이 남았다. 이번 작업은 이벤트 디스패처의9802 분기를 완성한 것이며 실제 스테이지 로딩·플레이 또는 전체화면 픽셀 검증은 아니다.
