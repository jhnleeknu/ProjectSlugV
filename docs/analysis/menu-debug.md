# 디버그 설정 메뉴와 lookup 글꼴

## 원본과 런타임 데이터

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
CPU 주소와 복호화 파일 오프셋은 모두 고정 ROM 범위에서 일치한다.

descriptor `99ee`의 15개 항목은 callback `9aa8`을 공유한다. 설정 word는 RAM CPU `10f000`이다. 원본 `9a98`의 항목별 bit 표는 다음 순서다.

```
15, 8, 9, 11, 12, 13, 14, 7, 2, 3, 1, 0, 6, 5, 10
```

`control_menu_tree.ms5d`를 `[937e,9aa8)`로 확장하여 이 표를 포함했다(1,866바이트). format/version은 기존 MS5D v1이다. `pack_menu_font.py`는 CPU `e80c8..e82c8`의 BE16 타일 word 256개를 `menu_font_6b.ms5d`(544바이트)에 보존한다. 실제 글리프 픽셀은 기존 fixed MS5T 타일에 있다. PNG나 글리프 이미지로 치환하지 않는다.

## callback 9aa8

- event 1/2/3은 현재 행의 매핑 bit를 반전하고 다시 표시한다. 좌/우의 값 증가·감소가 아니라 동일한 toggle이다.
- event 5는 값 변경 없이 표시한다.
- event 4는 mode=2로 닫기를 요청하고 A2=head를 남긴다. 종료 word7dfa를 바꾸지 않는다.
- 다른 event는 RAM/포트 변화가 없다.

표시는 `9f36`의 메뉴 좌표에서 x word에 18을 더한 위치다. 먼저 메뉴 x/y를 byte 연산으로 계산하고, 추가 18은 word 연산이므로 순서를 바꾸면 경계에서 다른 위치가 된다. ON/OFF 문자열은 resource의 `99e3`/`99e7`을 읽는다.

스타일은 `9f78`의 선택/부모 판정을 따른다. callback `9332`가 low style3을 6b로 바꾸며 palette 상위 nibble을 유지한다. 6b glyph는 표의 타일 word에 palette bits를 OR하고 long 포트 쓰기 한 번을 출력한다. 기본3650 렌더러의 후속 word8200 쓰기는 이 경로에 없다.

일반 항목 문자열이 가려져도 ON/OFF 콜백은 별도로 출력한다. callback 자체에는 보이는 높이 검사도 없다. 전체 메뉴 루프가 숨겨진 행의 callback 호출을 생략하는 것과 구분한다.

## 글꼴6b 스트림

`trace_table_fixed_text`는 기존 c/p/l/n/r 제어 해석기를 공유하고 원본 e84c8의 6b 경로를 구현한다.

- glyph 다음 byte DE/DF를 먼저 조사하여 지원되는 가나 조합을 하나의 글리프로 합친다.
- 이후 `@` 문법을 해석한다. `.`/`:`/`~`/`-` selector와 a/u/e/o 조합, backtick을 통한 다음 byte 소비, 미인식 byte의 그대로 출력 순서를 보존한다.
- operand로 소비한 0은 루프 terminator와 다르다. 경계 누락은 명시적 오류다.
- 각 글자는 표의 BE16 word를 읽고 커서를 32씩 word 순환시킨다. 출력과 D3 줄 위치는 성공 때만 반영한다.

다른 글꼴 코드를 6b로 대체하지 않는다. 미지원 style은 오류다. 메뉴에서 알려진 16-bit 설정 표 범위를 벗어나는 매핑도 거절한다.

## C++ 연결

`dispatch_menu_event`, `draw_menu_text`, `draw_menu_item`, `navigate_menu`, `push_menu`에 선택적 font 리소스를 전달한다. 기존 부모 메뉴 호출은 font 없이 유지된다. debug event-5는 일반 항목 문자 뒤에 붙고, 콜백이 남긴 줄 위치를 부모 다시 그리기/새 슬롯 측정에도 전달한다. 필요한 글꼴이 없을 때 RAM/기존 출력/결과는 보존된다.

## 검증

- `verify_menu_debug.py`: 원본 명령을 변경하지 않고 2,100조건의 전체 RAM/포트 순서·폭·값 일치. callback1,920(모든15행/event0..7/word패턴4종/head·선택상태), 전체 메뉴48, 이동·지정 선택120, debug 부모에서 메뉴 추가12조건이다. callback A2/외부 전환도 비교했다.
- `verify_table_text.py`: 원본3918/e84c8과 104스트림의 포트 및 D3 하위 word 일치. 모든255 nonzero glyph ×16palette, DE/DF 조합, @ 문법, 제어문자와 주소 순환을 포함한다.
- 부모 이벤트975 및 기존 전체 문자288조건 회귀 통과. `make all test` 통과.
- 단위 검사: 없는/잘린 글꼴, 잘린 @ operand, 잘못된 bit 표, 실패 시 전체 출력 보존, bit15 반전 및 동적 callback 이후 줄 위치.

```
.venv/bin/python tools/pack_control_menu_tree.py
.venv/bin/python tools/pack_menu_font.py
make all test
.venv/bin/python tools/verify_table_text.py
.venv/bin/python tools/verify_menu_debug.py
```

메뉴 CLI의 기존 인자 뒤에 `FONT_MS5D`를 추가하면 동적 표시를 사용할 수 있다. 별도 글꼴 진단 CLI는 다음과 같다.

```
build/trace_table_text INPUT_MS5D CPU_ADDRESS CURSOR STYLE OUTPUT_WRITES FONT_MS5D
```

다른 두 자식 콜백9602/9802, 헤더9430과 전체a370, 실제 픽셀·음향 출력은 아직 남아 있다. 전체 게임 완성이나 자연스러운 부팅 경로 검증으로 확대 해석하지 않는다.
