# 메뉴 프레임의 헤더와 스택 다시 그리기

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 CPU 주소는 고정 ROM 범위이며 복호화 파일 오프셋과 같다. 전체 a370 프레임은 아직 연결 중이다.

## 헤더9430

native93e0의 descriptor+6 콜백9430은 먼저9086을 호출한다. `read_control_request`가 반환한 byte의 bit1과 RAM107df0의 bit0, 또는 반환 bit3과 RAM107df0의 bit1이 함께 켜져 있으면 종료한다. 종료는 RAM107dfa의 word를1, mode107f1b를2로 쓰고 A2를 head107f0e의 long으로 바꾼다. 조건이 거짓이면 RAM과 A2를 보존한다. 원본은 head를 여기서 역참조하지 않으므로 C++도 임의의 head 값을 거절하지 않는다.

`update_menu_header`는 기존 요청 선택기를 사용한다. 헤더가 종료를 요청하더라도 a440의 호출자는 저장했던 A2를 복원한 뒤 pending 이벤트와 입력 처리로 계속 간다. 전체 프레임을 연결할 때 mode 변경을 근거로 조기 반환하면 원본과 달라진다.

```
build/update_menu_header INPUT_RAM OUTPUT_RAM A2
.venv/bin/python tools/verify_menu_header.py
```

원본9430과 실제9086, C++ 사이 960조건의 전체 RAM/A2가 일치했다. 종료264조건과 보존696조건, 모드·마스크·플레이어 상태·입력 enable의 불일치 및 임의 head/current/초기 종료 word를 포함한다. 단위검사는 크기 오류와 입력 출력 보존을 검사한다.

## 스택 다시 그리기a6da

이 함수는 입력 A2를 저장하고107efe부터16바이트씩 감소시키며 입력 슬롯까지 포함해 처리한다. 매 슬롯마다 current107f12를 쓰고9b58 테두리 다음9e1a 전체 문자를 호출한다. 마지막에 A2만 복원하므로 current는 마지막으로 그린 슬롯에 남는다. A2=107f0e이면 빈 범위이며 RAM과 포트 출력은 변하지 않는다.

`redraw_menu_stack`는 head 이후의 할당된 슬롯 또는 빈 범위를 받고 전체 작업을 하나의 트랜잭션으로 처리한다. newer head가 다시 그리는 범위 밖에 있어도 그 슬롯의 가림 판정을 사용한다. 보이는 메뉴는 기존 flags0/알려진 콜백 범위다. 실패하면 RAM, 비디오 출력, optional final_line을 보존한다. 원본의 임의 RAM 주소를 슬롯으로 읽는 동작은 지원하지 않는다.

줄 위치D3는 각 테두리와 텍스트 실행 이후 다음 슬롯으로 이어진다. 높이0인 슬롯은 줄 위치를 바꾸지 않는다. context는 실제 stage event5 진입 A7이며 a6da 진입 S에 대해 S−28이다(A2 저장4 + 전체 문자 BSR4 + 행/콜백20). 이전 push_menu의 S−40과 다르다. C++ context에 실제 콜백 진입 주소를 주며 함수 안에서 다시 보정하지 않는다.

```
build/redraw_menu_stack INPUT_RAM MENU_MS5D OUTPUT_RAM OUTPUT_PORTS LAST_SLOT LINE [FONT_MS5D [STAGES_DIRECTORY CALLBACK_STACK]]
.venv/bin/python tools/verify_menu_redraw.py
```

입력은 기존 C++ 게임용 MS5D 메뉴/글꼴/스테이지 리소스다. CLI의 9바이트 포트 레코드는 검증용이며 PNG로 바꿔 읽지 않는다.

원본a6da 검증은 692조건(기본432, 좌표/구역 경계128, 부분24, 빈 범위12, 높이 혼합/가림 flag96)에서 전체 RAM·ordered ports·최종D3가 일치했다. 실제 테두리/문자 호출 순서와 callback 수를 원본 실행 hook으로 검사했다. stage 콜백3,305회 모두 S−28이며 원본A2 보존도 확인했다. 부분 범위 밖의 최신 메뉴가 가리는 경우와 마지막 슬롯 높이가0인 줄 위치 전달을 포함한다. 전체 `make all test`와 새 단위검사 통과.

## 전체 프레임 연결 시 유지할 순서

아래는 원본 명령에서 확인한 후속 구현 제약이며 전체 프레임 완료 주장이 아니다.

- a370은 오래된 슬롯부터 descriptor+10 콜백을 호출한다. head보다 오래된 슬롯의 flag0과 현재 높이에 따라 닫기 단계를 수행하고 높이가0이 되면 a6da를 호출한다.
- 활성 경로a406은 높이가 목표보다 작으면 열기 한 단계 후 반환한다. 열린 경우 flag0을 지운 이전 값에 따라 전체 텍스트를 다시 그리고, 헤더+6을 호출한 뒤 pending을 비우고 입력을 처리한다. pending은 콜백 호출 전에ff로 바꾼다.
- 열기 완료a5ea는 callback이 있는 선택 행을 찾고 테두리/문자를 그린 후 event6, 이어 event0을 실행한다. 각각 current를 다시 읽는다. 콜백이 전혀 없는 메뉴의 원본 루프를 정상 메뉴로 간주하지 않는다.
- 닫기a662는 현재 높이가 양수면 닫기 단계 후 반환한다. 이미0이면9e94(줄 위치는 슬롯 좌표로 설정), head+=16, 비어 있으면−1 반환이다. 부모가 있으면 event7, head가 같을 때 event0, current를 다시 읽은 뒤a6da를 호출한다.
- 단계별 호출 깊이가 다르므로 stage context의 스택 주소를 모든 경로에 같은 값으로 넘기면 포맷터 RAM이 달라진다.

실제 픽셀, 하드웨어 타이밍, 자연 입력 도달성, 전체 게임 부팅/스테이지 실행은 이 단계의 검증 범위 밖이다.
