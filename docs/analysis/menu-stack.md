# 메뉴 스택 추가와 부모 다시 그리기

## 원본과 데이터

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
아래 CPU 주소는 고정 ROM 범위의 복호화 파일 오프셋과 같다.

`0x00a0a0..0x00a1e0`은 메뉴 스택 추가다. 부모 메뉴 콜백의 event 3 분기에서 `0x009f36`으로 위치를 구하고 이 루틴으로 이동한다. 실제 하위 참조는 다음과 같다.

| 참조 명령 | descriptor | 항목 수 |
|---|---|---|
| `0x0094aa` | `0x00958a` | 10 |
| `0x0094c8` | `0x00978a` | 10 |
| `0x0094e4` | `0x0099ee` | 15 |

`pack_control_menu_tree.py`는 부모 `0x0093e0`과 위 세 메뉴, 참조 문자열을 기존 MS5D 규격으로 저장한다. 창은 `0x00937e..0x009aa8`(끝 제외), 파일 크기 1,866바이트다. 최초 추출 뒤 debug 비트 매핑 표까지 창을 확장했다. 사이에 있는 코드/미분류 바이트도 불투명 원본 데이터로 보존하며 C++ 로더가 이를 명령으로 실행하지 않는다. 콜백 주소 보존과 콜백 구현을 구분한다. debug9aa8의 동적 event-5 출력은 menu-debug 분석에서 연결했다. 다른 자식 콜백은 아직 별도 구현 대상이다.

## 스택 추가 순서

1. 기존 current를 저장한다. head에서 16바이트를 빼 새 슬롯을 잡는다. 빈 스택의 head는 `0x107f0e`, 슬롯은 `0x107e0e..0x107efe`다.
2. 새 head를 기록한다. 새 슬롯 x/y를 255, width/target-height를 0으로 두어 부모 다시 그리기 중 새 슬롯의 가림이 발생하지 않게 한다.
3. 이전 head가 실제 슬롯이면 부모의 테두리와 전체 문자를 그린다. 이때 parent != head이므로 비활성 스타일이다. 부모 슬롯+8은 전체 그리기의 마지막 항목 인덱스로 바뀐다.
4. 새 슬롯을 설정한다. descriptor, 위치, 항목 수/크기, 기본 플래그를 기록하고 높이의 정수 byte만 0으로 만든다. 기존 슬롯+5의 소수 byte는 보존한다.
5. mode를 1(열기)로 설정하고 저장한 current를 복원한다. renderer와 입력 출처 byte는 초기화하지 않는다.

C++ `push_menu`는 위 순서의 전체 RAM 및 포트 쓰기를 구성한다. 첫 메뉴 초기화와 스택 추가는 `configure_menu_slot`의 측정/크기 계산을 공유한다. 기존 `initialize_menu`의 renderer/input 초기화는 그대로 별도로 유지한다.

## 문자 줄 위치 전달

원본 D3의 하위 word는 문자 제어 스트림의 줄 위치다. 테두리 flags0 경로는 base + max(height,2)를 남긴다. 이어 제목과 보이는 항목은 각각 `3918`에서 자신의 시작 위치로 D3를 재설정하고 `l/n` 제어에서 갱신한다. 숨겨진 행은 줄 위치를 바꾸지 않는다. 최종 줄 위치가 새 메뉴의 제목/항목 측정에 전달된다.

`draw_menu_text`의 선택적 `final_line` 출력으로 이 상태를 보존했다. 공통 문자 해석기로 계산하며 실패 시 호출자의 출력값도 보존한다. 부모 높이가 0이거나 빈 스택이면 초기 line이 유지된다. 이는 새 문자열에 개행 등이 있을 때 trap 판정에도 영향을 준다.

## 검증과 제약

`verify_menu_stack.py`는 원본 a0a0 명령과 부모의 실제 콜백을 실행하여 전체 64KiB RAM 및 포트 주소/폭/값/순서를 C++와 비교한다. 377조건 일치: 실제 부모/자식 256, 빈 스택 48, 합성 문자 줄 전달 72, 빈 스택에서 미구현 콜백 주소 보존 1. 최하단 슬롯 할당, current의 임의 저장값, x/y 상위 word, 소수 높이와 renderer/input 보존을 포함한다. 잘못된 요청 14조건은 출력 파일을 생성하지 않았다. C++ 단위 검사로 부모 출력을 준비한 뒤 새 descriptor가 실패해도 전체 RAM/출력을 보존함을 확인했다.

기존 첫 메뉴 초기화 378조건 및 전체 메뉴 문자 288조건 회귀, `make all test` 통과.

가득 찬 스택의 원본은 current를 스택에 저장한 후 복원 없이 조기 RTS하므로 정상적인 호출 반환 계약을 만족하지 않는다. C++는 이 조건을 오류로 거절한다. CPU의 잘못된 복귀나 trap 자체를 재현했다고 주장하지 않는다. 부모 출력은 현재 flags0/알려진 event-5 콜백 범위를 따른다. 하위 메뉴 콜백, 전체 이벤트 디스패치, a370 프레임 및 실제 화면 픽셀/인터럽트 타이밍은 남아 있다.

## 재현

```
.venv/bin/python tools/pack_control_menu_tree.py
make all test
.venv/bin/python tools/verify_menu_stack.py
.venv/bin/python tools/verify_menu_init.py
.venv/bin/python tools/analyze_menu_text.py --cpp
build/push_menu INPUT_RAM INPUT_MS5D OUTPUT_RAM OUTPUT_WRITES ADDRESS X Y LINE
```

리소스는 C++가 읽는 MS5D다. OUTPUT_WRITES는 기존 9-byte 비디오 포트 진단 레코드이며 PNG 변환은 필요하지 않다.
