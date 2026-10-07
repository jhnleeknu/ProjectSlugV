# 메뉴 프레임의 헤더와 스택 다시 그리기

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 CPU 주소는 고정 ROM 범위이며 복호화 파일 오프셋과 같다. native93e0/958a/978a/99ee 메뉴의 a370 프레임을 C++에 연결했다. 전체 게임 루프/부팅을 복원했다는 뜻은 아니다.

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

## 전체 프레임에서 유지하는 순서

아래는 원본 명령에서 확인하고 step_menu_frame에 연결한 순서다. 알려지지 않은 descriptor/header 콜백은 명시적으로 거절한다.

- a370은 오래된 슬롯부터 descriptor+10 콜백을 호출한다. head보다 오래된 슬롯의 flag0과 현재 높이에 따라 닫기 단계를 수행하고 높이가0이 되면 a6da를 호출한다.
- 활성 경로a406은 높이가 목표보다 작으면 열기 한 단계 후 반환한다. 열린 경우 flag0을 지운 이전 값에 따라 전체 텍스트를 다시 그리고, 헤더+6을 호출한 뒤 pending을 비우고 입력을 처리한다. pending은 콜백 호출 전에ff로 바꾼다.
- 열기 완료a5ea는 callback이 있는 선택 행을 찾고 테두리/문자를 그린 후 event6, 이어 event0을 실행한다. 각각 current를 다시 읽는다. 콜백이 전혀 없는 메뉴의 원본 루프를 정상 메뉴로 간주하지 않는다.
- 닫기a662는 현재 높이가 양수면 닫기 단계 후 반환한다. 이미0이면9e94(줄 위치는 슬롯 좌표로 설정), head+=16, 비어 있으면−1 반환이다. 부모가 있으면 event7, head가 같을 때 event0, current를 다시 읽은 뒤a6da를 호출한다.
- 단계별 호출 깊이가 다르므로 stage context의 스택 주소를 모든 경로에 같은 값으로 넘기면 포맷터 RAM이 달라진다.

실제 픽셀, 하드웨어 타이밍, 자연 입력 도달성, 전체 게임 부팅/스테이지 실행은 이 단계의 검증 범위 밖이다.

## C++ 프레임 실행

```
build/step_menu_frame INPUT_RAM MENU_MS5D OUTPUT_RAM OUTPUT_PORTS LINE ENTRY_STACK [FONT_MS5D [STAGES_DIRECTORY]]
.venv/bin/python tools/verify_menu_frame.py
```

JSON 결과는 `status`(계속0/종료−1), `external_jump`, `line`이다. BIOS9532 분기의c00444는 실제 펌웨어를 실행하지 않고 외부 전환 주소를 반환한다. 이 경우 status0은 호스트 진단 표현이다. 실패하면 RAM, 결과 구조체와 포트 목록을 모두 보존한다. pending 처리의 무한 루프와 선택 가능한 callback 없는 메뉴도 오류로 거절한다.

이 API는 프레임 진입 A1이 전역 renderer107f16과 같다는 입력 계약을 사용한다. 지원하는 전역 renderer는3650과9332다. entry_stack은 실제 원본a370 진입의 외부 진단 A7이며, C++ 호스트 주소가 아니다. stage context의 callback_stack을 그대로 재사용하지 않고 각 호출 경로의 깊이로 계산한다.

| stage 콜백 경로 | a370 진입S에서 뺄 바이트 |
|---|---:|
| 열기 완료 전체 그리기/event6 내부 행 그리기 |24|
| 열기 완료 event6 및 event0 |4|
| 활성 flag 재출력 |28|
| 입력 이동의 행 그리기 |24|
| 대기 이벤트/입력 이벤트 |8|
| 대기 event6 안의 중첩 행 그리기 |28|
| 닫은 뒤 부모 event7 / event0 |8 / 4|
| 닫은 뒤 스택 다시 그리기 |32|
| 배경 메뉴 닫기 뒤 스택 다시 그리기 |36|

슬롯 설정, push, 이벤트 디스패처의 선택적 final_line으로 D3를 반환하여 프레임 내부 호출 사이에 전달한다. 원본과 같은 줄 위치를 다음 프레임에도 넘길 수 있다.

## 실제 메뉴 렌더러9332

92f0에서 a2b8로 설치하는9332는 D1 low byte가3이면6b로 바꾼 후 e84c8 표 렌더러로 간다. 3918은 D1을 복원하지 않으므로 스타일 변경은 다음 glyph에서도 유지된다. menu_text는 기존 MS5D 글꼴과 glyph 파서/렌더러를 공유하여 이 동작을 연결한다.

가림 wrapper a008은 a018의 판정 후 **전역107f16으로 tail-call**한다. 항상3650을 호출하는 것이 아니다. 따라서 clip 경로도 전역9332를 지원하며, 가려진 glyph는 스타일 변경·lookahead 소비·cursor 이동을 모두 생략한다. `@` operand가 다음 파서 입력에 남는 경우를 단위검사에 포함했다. 기존3650 API 기본값은 유지한다.

## 프레임 검증 범위

원본 a370을 수정하지 않은834프레임에서 전체65,536바이트 RAM, ordered video/watchdog writes, 반환 상태, 외부 전환 주소, 최종D3가 일치했다. 실제 stage콜백697회와 포트155,889회를 비교했다. 원본 a29c/C++ init_menu의 결과에서 시작해 RAM과D3를 계속 전달하는10개 시퀀스는 renderer3650/9332 각각에서 debug/area/group 취소와 area/group 확인을 수행한다. 자식 descriptor와 마지막 빈 stack을 별도로 확인한다.

고립된 프레임은 열기/완료, pending0..7, 두 입력의 우선순위/enable, 헤더 종료 뒤 pending와 실제 입력의 계속 실행, 닫기/pop/event7/event0/다시 그리기, 배경 메뉴 닫기, 빈 stack/잘못된 mode를 포함한다. 정적 재시작3조건은 원본allocator 초기값을 쓰고 palette/coordinate 연결이 없는 경우의 watchdog 쓰기까지 비교한다. 연결된 오브젝트의 재시작은 별도 menu-event 검증 범위이며 여기서 확대 검증했다고 주장하지 않는다.

원본 callback 주소/event/A7을 관찰한 결과 위 깊이와 일치했다. 원본 프로그램의 매핑된1MiB가 바뀌지 않았음도 확인했다. C++ 단위검사는 header가 RAM을 바꾼 뒤 pending callback 오류가 나는 경우, missing font, 빈 범위와 잘못된 stack의 모든 출력 보존을 검사한다. make all test(Python55개 및 C++ 전체)가 통과했다.

남은 범위는 실제 호출자92da/92fc의 프레임 진입 레지스터·입력 수집/스케줄링 통합, 다른 메뉴 descriptor/flags/콜백, BIOS 실행, 픽셀과 하드웨어 타이밍, 전체 게임 루프와 실제 스테이지 실행이다.

## 후속 레지스터 통합을 위한 원본 경계 관찰

9b3e는콜백을호출하기전에선택항목의+8word를D1.word에읽는다. 콜백전후D1의상위word를따로저장하지않는다.9d3a는보이지않는행에서도먼저D1.lowbyte를index+1로바꾼뒤반환한다. 보이는행은9d70에서D1을전체0으로만들고항목오프셋을계산한후9b3e를통해event5를보낸다. 따라서숨은행을단순히모든레지스터불변으로처리하면안된다. 이문단은명령관찰이며현재menu_text의전체D1/D3반환은아직구현되지않았다.

## 스택 다시그리기의 전체 레지스터

`redraw_menu_stack`은 a6da의 오래된 슬롯부터 마지막 슬롯까지, 각 9b58 테두리와 9e1a 텍스트의 전체 D1/D3를 순서대로 전달한다. 테두리 종료 line의 중복 계산을 제거하고 테두리 API 반환값을 사용한다. 빈 범위는 두 레지스터를 보존한다. 오류는 RAM·포트·line·D1/D3를 모두 보존하며 입력 LINE과 D3 하위 word가 다르면 거절한다.

CLI의 선행 `--registers D1 D3`는 기존 line JSON에 두 레지스터를 추가한다. 콜백 문맥은 기존과 같이 원본 a6da 진입 stack S의 S−28이다. 실제 슬롯별 그리기 순서와 동적 콜백 진입을 원본 실행에서 관찰한다. a370 전체 프레임의 레지스터 전달 완료를 뜻하지는 않는다.

- `.venv/bin/python tools/verify_menu_redraw_registers.py`: 원본 698조건, 포트 428,143개, 출력 보존 오류 검사 7조건 통과. 보고서 SHA256 `68711c1438609585d43f68612cb6300b3cba8c042a0e817d9ad1c05262de1159`.
