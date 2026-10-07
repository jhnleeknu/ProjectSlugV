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

`pack_control_menu_tree.py`는 부모 `0x0093e0`과 위 세 메뉴, 참조 문자열을 기존 MS5D 규격으로 저장한다. 창은 `0x00937e..0x009aa8`(끝 제외), 파일 크기 1,866바이트다. 최초 추출 뒤 debug 비트 매핑 표까지 창을 확장했다. 사이에 있는 코드/미분류 바이트도 불투명 원본 데이터로 보존하며 C++ 로더가 이를 명령으로 실행하지 않는다. 콜백 주소 보존과 콜백 구현을 구분한다. debug9aa8의 동적 event-5 출력은 menu-debug 분석에서 연결했다. 스테이지 9602/9802도 stage-area-menu/stage-group-menu 분석에서 연결했다.

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

가득 찬 스택의 원본은 current를 스택에 저장한 후 복원 없이 조기 RTS하므로 정상적인 호출 반환 계약을 만족하지 않는다. C++는 이 조건을 오류로 거절한다. CPU의 잘못된 복귀나 trap 자체를 재현했다고 주장하지 않는다. 부모 출력은 현재 flags0/알려진 event-5 콜백 범위를 따른다. 전체 a370 프레임 및 실제 화면 픽셀/인터럽트 타이밍은 남아 있다.

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

## 스테이지 부모의 동적 출력 연결

`push_menu`는 선택적인 `StageGroupMenuContext`를 전체 부모 그리기에 전달한다. 런타임 입력은 기존 메뉴/글꼴 MS5D와 스테이지 카탈로그이며, PNG나 재생용 출력은 사용하지 않는다. 부모의 동적 출력과 새 자식 초기화를 같은 RAM/비디오 쓰기 트랜잭션 안에서 처리한다.

context의 `callback_stack`은 부모 event5 콜백에 실제 진입한 A7이다. 메뉴 추가 루틴 진입을 S로 두면, current 저장 4바이트와 D0/D1/A0 저장 12바이트, 전체 그리기 BSR 4바이트, 그 안의 행/콜백 호출 20바이트를 합쳐 **S−40**이다. C++가 다시 40을 빼지는 않는다. 다른 그리기 API와 같이 호출자가 실제 콜백 주소를 전달한다. 이 값은 포맷터 RAM의 인자 포인터를 원본과 맞추기 위한 것이며 호스트 스택 주소가 아니다.

CLI의 확장 형식:

```
build/push_menu INPUT_RAM MENU_MS5D OUTPUT_RAM OUTPUT_WRITES ADDRESS X Y LINE FONT_MS5D STAGES_DIRECTORY CALLBACK_STACK
.venv/bin/python tools/verify_stage_menu_push.py
```

기존 인자 형식과 빈 stdout은 유지한다. stage 디렉터리의 21개 입력 파일은 두 출력과 동일 경로·심볼릭 링크·하드 링크인지 검사한다. 숨겨져 실제 stage 콜백이 실행되지 않는 부모는 C++ API에서 context 없이 처리할 수 있다. 이 API로 stage 부모 아래 자식 메뉴를 추가하는 동작을 검증하는 것이며, 원본 사용자 입력만으로 모든 조합에 도달한다고 주장하지 않는다.

확장 검증 `verify_stage_menu_push.py`는 원본 a0a0의 코드를 수정하지 않고 6,192조건을 비교했다. native 조합 4,480, 좌표/줄/스택/current 432, 구역 마지막 유효값/255 경계 1,280이다. 전체 65,536바이트 RAM과 포트 순서·폭·값, 새 자식 슬롯, 소수 높이 및 current 복원이 일치했다. 실제 콜백이 실행된 4,032조건의 21,888회 진입은 모두 S−40이다. 보이는 폭2 구분선은 256회 쓰기를 확인했다. 전체 CPU 레지스터·외부 스택 메모리·자연 도달성·픽셀·하드웨어 타이밍은 이 비교 범위 밖이다.

기존 메뉴 추가 377조건/오류14, 이벤트 975조건/오류6 및 `make all test`가 통과했다. 단위검사는 stage 부모의 출력 후 자식 descriptor가 실패하는 경우와 context 누락의 RAM/출력 보존을 검사한다. CLI 입력 보호는 index/null-name × 두 출력 × 직접/하드링크/심볼릭링크 12조건과 숫자 오류 5조건을 별도 확인했다.

## 전체 D1/D3와 부모 출력

`push_menu`는 선택적 전체 D1/D3를 입출력한다. a0c8은 D0/D1/A0를 저장하고 부모의 9b58/9e1a를 실행한다. a104는 D1 전체를 원래 값으로 복구한 뒤 a110의 새 슬롯 구성으로 이어진다. 따라서 자식 측정은 원래 Y인 D1 하위 word로 시작하며 최종 D1 상위 word도 진입값이다. D3는 저장 대상이 아니므로 부모 테두리·텍스트의 반환값을 자식 제목 측정으로 이어 준다.

별도로 계산하던 테두리 종료 line을 제거하고 실제 `trace_menu_border`의 D3 출력을 사용한다. 부모 그리기와 자식 구성은 하나의 트랜잭션이며 실패 시 레지스터까지 보존한다. 옵션을 제공하면 Y=D1.low16, LINE=D3.low16을 요구한다.

```sh
build/push_menu --registers D1 D3 INPUT_RAM MENU_MS5D OUTPUT_RAM OUTPUT_PORTS ADDRESS X Y LINE FONT_MS5D STAGES_DIRECTORY CALLBACK_STACK
```

새 모드에서만 line/D1/D3 JSON을 출력한다. 원본 a0a0 진입과 정상 반환 경계를 비교하며 가득 찬 스택의 잘못된 복귀, 다른 레지스터·외부 스택 잔여 메모리·SR·물리적 타이밍은 포함하지 않는다.

- `.venv/bin/python tools/verify_menu_stack_registers.py`: 원본 544조건, 포트 135,264개, 출력 보존 오류 검사 27조건 통과. 보고서 SHA256 `cf1f98e6c894477560cb2936cef2a557d50252e07f96670e60238d5bd6690705`.
