# 부모 메뉴 이벤트 디스패치

## 원본과 계약

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
CPU `0x009b3e`와 아래 콜백 주소는 고정 ROM의 복호화 파일 오프셋과 같다.

`dispatch_menu_event`는 current 슬롯+8의 항목에서 MS5D 콜백 주소를 읽는다. event는 D0 하위 word, initial_line은 D3 하위 word다. 슬롯+14의 대기 event를 지우는 일은 상위 프레임 루프의 책임이다. 이번 API는 호출 후 전체 RAM, 순서 있는 포트 쓰기, A2 및 외부 점프 대상을 반환한다. A2는 상위 메뉴 상태 머신이 콜백 뒤에 사용하는 값이므로 별도로 보존했다.

## 여섯 콜백의 실제 분기

| 콜백 | event 3 | event 4 | event 7 |
|---|---|---|---|
| 9488 | 현재 head 닫기 요청 | 종료 word=1, 닫기 | 변화 없음 |
| 94d6 | 99ee 메뉴 추가 | 종료 word=1, 닫기 | 변화 없음 |
| 949a | 958a 메뉴 추가 | 종료 word=1, 닫기 | 종료 word가 1이면 닫기 |
| 94b8 | 978a 메뉴 추가 | 종료 word=1, 닫기 | 종료 word가 1이면 닫기 |
| 950c | 고정 오브젝트 재시작, 종료 word=1, 닫기 | 종료 word를 바꾸지 않고 닫기 | 변화 없음 |
| 9532 | BIOS c00444로 점프 | 종료 word를 바꾸지 않고 닫기 | 변화 없음 |

다른 event는 이 여섯 콜백에서 RAM/포트 변화가 없다. callback 주소 0도 무효과다. 다른 callback 주소는 미구현 오류로 명시한다.

닫기 요청 `a1ee`는 RAM `0x107f1b=2`와 A2=head를 남긴다. current 포인터는 바꾸지 않는다. 종료 word는 `0x107dfa`의 BE16 값이다. event7의 조건은 word 전체가 정확히 1인 경우다.

하위 메뉴 위치 `9f36`은 x=`uint8(parent.x + ((flags&14)?1:3))`, y=`uint8(parent.y+1+row)`다. 이전에 구현한 `push_menu`를 호출하고 결과 A2는 새 head다. current 복원과 부모 출력은 push의 원본 동작을 따른다.

## 고정 오브젝트 재시작

`950c`는 A0=`0x1008e4`, A1=`0x00ca22`로 `2a28`을 호출한다. `restart_static_object`는 object+10 word가 0인 정적 오브젝트 경로를 복원한다.

1. `299c`의 watchdog 주소 `0x300001` byte 쓰기를 기록한다. 이 콜백에서는 값이 3이다.
2. `2782 -> 8ff4`로 보유 팔레트를 해제한다.
3. `46ef4`에서 object+6c의 연결 좌표 인덱스를 읽는다. bit7이 켜지면 해제할 좌표가 없다. 나머지는 0..7을 요구한다.
4. 좌표 CPU 주소 `0x10d4e6 + index*0x2c`의 +26 word를 ffff, +2a word를 2로 바꾸고 object+6c=ff로 둔다. 기존 `update_position`으로 `43e38` 좌표 갱신을 실행한다.
5. 원본 `271c`의 필드 초기화를 기존 `reset_object_fields`로 수행하고 최종 오브젝트 콜백을 ca22로 기록한다.

기존 팔레트 할당기/위치 갱신/오브젝트 초기화 구현을 재사용했다. object+10 word가 cleanup 뒤에도 0인지 확인하여 연쇄 리스트 제거 경로로 들어가는 입력을 무효과 성공으로 처리하지 않는다. 연결 리스트 오브젝트 재시작은 아직 별도 범위다.

## BIOS 경계

9532/event3은 `MenuEventResult.external_jump=0xc00444`를 반환한다. 호출자는 이 결과를 BIOS/호스트 계층으로 전달해야 한다. 원본 비교도 c00444 명령 실행 직전에 멈춘다. 빈 firmware를 실행하거나 BIOS 동작을 구현한 것으로 간주하지 않는다. 이 경로는 전체 게임 통합에 남아 있는 외부 전환 요구다.

## 검증

`verify_menu_event.py`: 975조건에서 원본 9b3e와 콜백/하위 helper 전체를 실행하여 64KiB RAM, 순서 있는 video/watchdog 쓰기, A2, BIOS 점프 결과가 C++와 일치했다.

- 기본 720조건: 항목6개 × event0..8/ffff × 종료 word0/1/ffff × 숨김/표시 × current=head/이전 슬롯.
- 하위 메뉴 위치 byte 순환 108조건.
- 8개 연결 좌표의 해제와 부모 유무/갱신 stamp 경계 144조건.
- 실제 원본 할당기로 1/2/4개 팔레트를 획득한 뒤 해제하는 3조건.

오류6조건은 출력 파일을 생성하지 않았다. 단위 검사에서는 잘못된 callback, 미포함 child resource, 오브젝트 trap 및 cleanup 중 실패에서도 전체 RAM/기존 출력/결과를 보존했다. `make all test` 통과.

```
make all test
.venv/bin/python tools/verify_menu_event.py
build/dispatch_menu_event INPUT_RAM INPUT_MS5D OUTPUT_RAM OUTPUT_WRITES EVENT LINE
```

포트 기록은 size byte + BE32 CPU 주소 + BE32 값의 기존 9-byte 진단 형식이다. stdout JSON은 a2/external_jump다. 리소스는 `control_menu_tree.ms5d`를 그대로 사용한다.

헤더 콜백9430의 프레임 입력 확인, 자식 메뉴9602/9802/9aa8의 동적 출력/선택, 전체a370 및 최종 화면·음향은 아직 남아 있다. 현재 검증을 전체 게임의 자연스러운 실행 경로 검증으로 해석하지 않는다.
