# 메뉴 테두리와 중첩 가림 처리

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정CPU/파일9b58은테두리,9e94는사각영역지우기,a018은가림판정이다. RAMoffset은CPU100000기준이다.

## 원본 동작

9b58은current pointer7f12의슬롯+4 visible height가0이면descriptor를읽지않고반환한다. descriptor flags bit0이있으면9e94로분기하여width×height영역에타일word00ff를쓴다. 이지우기경로는가림을검사하지않는다.

일반테두리는current==head7f0e일때0b00,아니면6b00을기본값으로쓴다. 위행의타일하위byte는f4/f0/f5,중간행f2/60/f3,아래행f6/f1/f7이다. width가0/1이어도좌우2칸을시도하며height1이어도위아래2행을시도한다. 초기VRAM word주소는7000+(x<<5)의상위byte+((x<<5)+y)의하위byte다. ADD.B의carry는버린다.

a018은현재슬롯앞에서head까지16바이트간격으로검사한다. 슬롯+f bit0이면가림에서제외한다. 좌표는주소-7000의word값에서column=(delta>>5)의하위byte,row=delta&31로계산한다. 다른슬롯과의차이도byte로wrap하고폭/visible height보다작으면가려진다.

**가려진칸은쓰기뿐아니라주소+20도건너뛴다.** 따라서같은행에서그뒤반복은동일가림좌표에머물수있다. 이원본동작을일반사각형클리핑으로고치지않았다. 다음행은별도row start를1증가시켜시작한다.

## C++ 및 검증

`trace_menu_border(ram,resource,writes,error)`는기존MS5D descriptor를읽고기존FixedWrite(address,value)목록을생성한다. RAM은불변이고오류시이전목록을보존한다. head/current를107e0e..107efe의정렬된슬롯으로검사한다. 잘못된pointer에서원본이임의메모리를읽는동작은지원하지않는다.

```
make all test
build/trace_menu_border INPUT_RAM INPUT_MS5D OUTPUT_WRITES
.venv/bin/python tools/verify_menu_border.py
```

OUTPUT_WRITES는비교도구용BE16주소+BE16값의연속이다. 게임API는매번상태와리소스에서그리기동작을계산한다. 저장된화면명령재생으로엔진을대체하지않는다.

실제93e0리소스1조건,크기/좌표/flags/중첩108조건,중첩가림128조건의총237조건에서원본3c0000포트쓰기의전체순서와값이일치했다. RAM불변도확인했다. 255×255지우기65,025쓰기,0/1크기,좌표byte경계및중첩색상도포함한다. 전체검사와오류출력보존unit검사통과.

아직메뉴문자열렌더링,열기/닫기진행값업데이트,a370의전체프레임,실제팔레트연결과최종화면은검증하지않았다. 237조건은픽셀/장치타이밍비교가아니다.
