# 스테이지 이벤트 초기화 e905c

## 원본과 입력

Canonical program SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 코드와 아래 이벤트 자료는 fixed 첫1MiB이며 CPU주소=ROM파일오프셋이다. RAM `100000..10ffff`와 포트 주소는 ROM 오프셋이 아니다.

원본 `e905c..e90ca`는 A0 stream, D0.low 목표값을 받아 이벤트 오브젝트를 재시작하고 시작 cursor를 선택한다. `47aca` caller는 stage record+0a 포인터가 비영이면 LONG을 한번 역참조하여 A0에 전달하고 record+0e WORD를 D0.low로 전달한다. Callback e9150의 실제 실행은 초기화와 구분한다.

## 전체 레지스터 계약

먼저 A0 LONG과 D0 WORD를 스택에 저장한다. A0=입력A5-740c, A1=e9150으로 `2a28`을 호출한다. 일반 입력 A5=108000이면 오브젝트는100bf4다. A5를 먼저108000으로 강제하면 원본의 첫 주소 계산을 바꾸므로 입력 A5를 사용해야 한다. 호출 안의299c가A5를108000으로 바꾼다.

반환 후 D0.low만 저장값으로 복원하고 상위WORD는 callee 결과를 유지한다. D7은 저장한 입력 A0 LONG이다. D7=0이면 LONG(A0+76)=0을 쓰고 즉시 반환한다. 이 분기에서는 RAM bank shadow와2ffff2/2ffff0포트를 쓰지 않는다. 재시작의watchdog출력은 남는다.

D7이 비영이면 A1=D7, D1.low=WORD(A1), A1+=2다. D0.low=0이면 이 위치를 선택하며 header jump를 사용하지 않는다. 비영target이면 A1+=sign16(D1.low) 후 다음을 반복한다.

1. D1.byte=BYTE(A1)로 읽는다. 나머지 상위24비트는 보존한다.
2. BYTE가ff면 선택하고 종료한다. 0이 아니면 TRAP15다.
3. unsigned D0.low<=WORD(A1+2)이면 현재 위치를 선택한다.
4. 아니라면 A1+=sign16(WORD(A1+4)) 후 반복한다.

선택 후 D7=A1, LONG(A0+76)=D7, WORD(A5-7ff0)=0을 순서대로 쓴다. 이어2ffff2.WORD=1000,2ffff0.WORD=0을 출력하고RTS한다. WORD/LONG 접근은even이어야 하며 BYTE읽기는홀수위치도가능하다. RAM stream은재시작이쓴내용을LIVE로읽는다.

## 자료 보존 범위

59catalog record는52비영 stream 입력과7null을포함한다. 고유stream47개와간접포인터cell47개다. `e905c`의header/gate건너뛰기를따르면고유gate612개가있고47chain모두ff에서멈춘다. 모든canonicalheader jump는비음수이고gate jump는양수다.

추출window는각stream의header부터이ff BYTE를포함하는범위다. 총47window/48,685bytes이며중간명령과payload는해석여부와무관하게원본bytes를보존한다. 이는e905c가읽는범위와그사이자료의보존기준이지,전체이벤트문법이나미사용영역의완전한종료경계를증명하지않는다. Pointercell47개188bytes와30ec의8byte조회표도같은MS5D v1kind1으로보존한다. 총95개window이며PNG/오디오preview를runtime자료로쓰지않는다.

## 후속 이벤트 명령 근거

메인이e9176의dispatch와e9444..e97c8을읽었다. e9768은BYTE(A0+1)를unsigned길이로읽어A0를전진한다. 그러나모든명령을이길이만으로평탄하게순회하면안된다. Opcode09/e962a는+2WORD 상대위치로parentcursor를옮기고+1BYTE뒤위치를별도객체cursor로저장한다. Skip helper e9774에서도09/0b/0c는+2WORD로건너뛰고0a는BYTE길이를적용한뒤다음명령을재귀적으로건너뛴다. e96da에는후보를stack에모아난수로선택하는경로가있다.

이명령목록은후속해석의근거이며전체callback실행검증이아니다. 이번초기화의자료선택에명령길이만의추측을적용하지않고원본e905c의gate경로를사용한다.

## 검증 상태

C++ `initialize_stage_events`는전체64KiB RAM·ObjectRestartState15register·orderedports를transaction으로연결한다. Fixed자료는로드된MS5D창을빌려읽고RAM은LIVE로읽는다. 읽는주소는정확하나의완전한fixed창에포함되어야한다. 임시record한도는1,048,576회이며진행하지않는stream을임의로완료시키지않는다. Lateheader/gate실패도이미수행한재시작과watchdog를외부에게시하지않는다.

원본e905c부터2a28및하위callee를중단없이실행한2,443조건과C++결과의전체RAM·15register·7,275orderedports가일치했다. 원본코드patch/callee대체/intra-call contextreset은없다. RTS/A7+4·MMIO읽기0·ROM불변을확인했다. 가장긴호출은474명령,gatecursor방문최대39회다.

Corpus는47stream×5target×2profile470개,612gate각target-1/equal/+1의1,836개,실제59catalog쌍,null10개,palette/coordinate정리32개,입력A5변형16개,LIVE RAM alias3개,부호있는역방향RAM jump11개,실제CLI승계6호출이다. Gate612개모두실제원본방문union에포함됨을필수검사했다. 원본3ef2가palette를준비하고나머지는통제된fixture이며자연게임진행으로표현하지않는다.

특히stream100c5e는재시작의필드초기화로header가0002에서00ff로바뀐다. 비영target은이를LIVE로읽고홀수주소100d5f의ff BYTE를선택한다. Header/gate WORD의even조건과종료BYTE읽기를혼동하지않는다. 입력A5로오브젝트주소를먼저계산하고callee이후A5=108000을승계하는경계도검증했다.

2CLIsequence6호출중4호출은직전CLI출력을소비하며host는D0.low/A0/A5를다시제공한다. 오류120조건은입력/기존RAM출력/port출력을보존한다. Lateambiguousgate/marker/정렬/부호있는범위밖jump/좌표parent오류,zerojump및초기화로만들어진LIVE cycle의한도를포함한다.

메인은core/CLI/unit/observer/verifier/packer/Python테스트를읽었고2,443저장nativeRAM/ports및현재ROM/binary/95resource·metadata hash를대조했다. DirectoryCLI도별도로실행해전체RAM/15register/ports가원본과같음을확인했다. Python182/C++113/경고0이며새packer7합성테스트를포함한다. Packer는두번생성한96파일의byte동일성을확인했고메인재생성도같은manifest를만들었다.

- Native SHA256 `cae0353feda387d994ded125aa4585d633dc589e8dbc9a87d98c46a5244fdb88`.
- Verification SHA256 `27e2a119c5b7774f2f4f7f05d3b522c0ea50f22dd013a29b85198e3abfa89f6c`.
- CLI SHA256 `fc7dd39ac4d0a6c44c596e55f4605140dbd8585ecf8d62de57fb2e0f5d04813c`.
- Resource manifest SHA256 `cc1074eefb3698de5ae704e2aaed32240df3f3f4da9d41dc46c6c5d1666590db`.

```text
.venv/bin/python tools/pack_stage_catalog.py
.venv/bin/python tools/inventory_stage_event_contexts.py
.venv/bin/python tools/pack_stage_events.py
make -j3 all test
.venv/bin/python tools/observe_stage_event_initialization.py
.venv/bin/python tools/verify_stage_event_initialization.py
build/initialize_stage_events D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS extracted/runtime/stage_events
```

다음은47a94의e8a1c/48398/480bc연결이다. 480bc는47642,1a73c,49b0c,4aa88,b4a2a,6f1c2,4701e,e8a48,2efa6를호출한다. 이중1a73c는phase/script·motion·scene update·placement의frame경로여서일반초기화1a5a4와동일하다고가정할수없다. 전체goal,자연scheduler,전체stagecallback및직접플레이화면은미완료다.
