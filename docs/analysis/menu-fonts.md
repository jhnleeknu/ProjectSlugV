# 스테이지 이름의 혼합 글꼴 출력

원본 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
아래 CPU 주소는 고정 ROM 파일 오프셋과 일치한다.

## 원본 분기와 구현

3918은 386e의 c/p/l/n/r 제어문자 파서를 거쳐 e84c8 렌더러를 호출한다. 글꼴 선택은 style 하위 byte다.

- 00..0f: e84c8에서 바로3650으로 이동한다. 결합문자와 @를 해석하지 않는다. glyph마다 long 주소/타일 쓰기와 word8200 쓰기를 3c0000에 순서대로 수행한다.
- 30: 공통 DE/DF 결합문자를 처리한 뒤 e8558에서 하위 style을3으로 바꾸어3650을 호출한다. @는 일반 문자다. 원본은 호출 뒤 style을 복원한다.
- 68: e868c가 e82c8의256개 BE16 타일표를 선택한다.
- 6b: e869c가 e80c8의256개 BE16 타일표를 선택한다.

68/6b는 결합문자 처리 이후 e86a0의 @ 문법을 공유한다. 기존6b 구현의 문자 결합·selector 동작을 그대로 사용하고 선택한 표에서 타일을 읽는다. palette bits는 타일 word에 OR한다. 각 lookup glyph는 long 포트 쓰기 한 번이고 커서는32씩16비트 순환한다. 다른 글꼴은 여전히 미지원 오류다.

`trace_table_fixed_text`는 스트림 안의 글꼴 전환을 처리한다. 해당 글리프가 사용하는 표 전체가 리소스에 있는지 검사하므로68 단독 리소스도 사용할 수 있다. 도중에 없는 표로 전환하거나 미지원 글꼴을 만나면 앞서 만든 출력과 줄 위치까지 반영하지 않는다. font 인자는 비어 있지 않은 정상 고정 ROM 리소스여야 한다.

## 프로젝트용 데이터

`pack_menu_font.py`는 기존 `menu_font_6b.ms5d`와 manifest를 byte 수준으로 유지하며, `menu_fonts.ms5d`와 manifest를 추가한다. 기존 MS5D v1이며 새 형식은 없다.

- CPU/ROM 범위: `[e80c8,e84c8)`.
- payload:1024바이트, 파일:1056바이트.
- font6b payload offset0, font68 offset512; 각256개 BE16 항목.
- 파일 SHA256:`73accc599f333d73809aac371f9f55153f458862bdb84d16707f12304a9f7c54`.
- 글리프 픽셀은 기존 fixed MS5T 리소스를 참조한다. PNG를 엔진 입력으로 사용하지 않는다.

## 검증과 재생성

```
.venv/bin/python tools/pack_menu_font.py
make all test
.venv/bin/python tools/verify_table_text.py
.venv/bin/python tools/verify_menu_debug.py
```

원본3918/e84c8/3650 명령을 수정하지 않고 Unicorn에서 실행하여 C++와704개 스트림의 모든 비디오 포트 쓰기 순서·주소·폭·값 및 최종D3 하위word를 비교했다. 전체255 nonzero glyph와16 palettes, 두 lookup 글꼴, 직접16스타일, font30, 결합문자, @ operand의0, 제어문자, 커서 순환과 혼합 전환을 포함한다. 원본474f4의19그룹에서 직접 찾은59개 이름도 초기style3으로 모두 비교했다. 결합 리소스 전체payload/header/CRC도 원본과 일치한다.

합성 C++ 검사는68 단독표, 도중에 없는 표로 전환할 때 출력 보존, direct와30의 결합문자 소비 차이, 미지원 글꼴, 커서 순환을 확인한다. 기존 debug메뉴 회귀는 별도로 수행한다. 최종 픽셀, 하드웨어 타이밍이나 다른 CPU 레지스터 전체의 동등성을 주장하지 않는다.

## 다음 연결에 필요한 확인 사항

스테이지 콜백9602가 사용하는955e 문자열은 `\c0%1x:%2x %s`, 9802의9781은 `FOR %s `이다. 3a70은104cd6의24바이트 상태를 사용하는3950/396e 포맷터 루프다. 이름을 일반 문자열로 렌더링한 이번 검증과 이 포맷터의 실행은 다르다.

3950은 cursor/line/style, format pointer, renderer pointer, arguments pointer와 반복counter를 기록한다. 396e는 `%`를 처리하고, `%s`가 읽는 대상의 제어문자가 style/line을 변경할 수 있다. 따라서 일반 printf 치환으로 대체하면 RAM 상태와 글리프 소비 순서를 잃는다. `%x`의37e2와 너비 파서383e, 빈 이름 포인터를 포함한 동작을 추가 분석하고 전체RAM과 포트로 검증해야 한다. 9602/9802 및 전체a370 연결은 아직 미완료다.
