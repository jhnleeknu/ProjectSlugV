# 일반 장면 초기화 1a5a4의 연결 계약

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 CPU 주소는 ROM 파일 오프셋과 같고 A5=108000이다. 메인이 원본 1a5a4..1a73c와 아래 callee를 직접 대조하고 별도 `initialize_scene` API로 연결했다. 기존 `initialize_stage_scene`은 null-script 호출자477e4에 특화된 계약을 유지한다. 일반 호출의 검증 결과는 아래에 기록한다.

## 초기 상태와 보존할 값

입력 A0는 script, D0.low는 목표 phase다. RAM10.word=1을 쓰고2ffff2.word=2000,2ffff0.word=0을 순서대로 출력한다. D0.low를d41c에 저장하고1a07a가 A0를d412에 저장하며d416.word=0으로 만든다. 이 일반 진입에서 D0 전체를 먼저0으로 바꾸면 안 된다.

1a5c2..1a620의 기본값은 원본 폭 그대로 적용한다. 특히d40c는WORD clear, d44e는BYTE clear다. 이어19768,1a29e,19b50,19dee,1a3c8 순서로 호출한다. A0=0으로1a40e를 호출해d40e=0을 저장한 뒤 node109156과10b1d6에17292를 각각 호출한다. Scene node와 script 실행에서 레지스터 결과를 계속 승계한다.

19768 자체는 A1=0,D0=D1=0을 설정하므로19796의비영motion 분기는 이 진입에서는 실행되지 않는다. Base/cursor/evaluated좌표를0으로 저장하고 D0=0,D1=01000000,A0=10d38e,A1=0으로43e22에 tail call한다.

1a29e는d422.LONG=0,197da 실행,d41e/d420 WORD=D7.low,d43e.word=0이다. 197da는A1=d3b4, null이면D7.low=7fff(상위WORD보존). 비영이면10byte씩 이동하여 type WORD가 정확ffff인record의startWORD-1을D7.low에 담는다. Terminalcursor는A1에남는다.

19b50는d3cc.byte=0, d3de/d3e2/d3fc/d400.LONG=0, d3ee/d3f0.word=0, d3d6.word=a0,d3d8.word=80,d3da/d3dc.word=0,d3e6/d3ea.LONG=60000으로놓는다. 19cee는d3ce/d3d0.word=7fff,d3d2/d3d4.word=8000이다. 이 함수는placement bounds인d3f2..d3f8을 초기화하지 않는다.

19dee는 네 node109156/10b1d6/10d256/10d2d6와metadata10d356/10d364/10d372/10d380에19e30을 순서대로 호출한다. Metadata+0.LONG과+4/+6/+8/+a.WORD를0으로 쓰고+c.BYTE=10을 쓴다. +d byte는보존한다. Node16fac 초기화 뒤 A1=0, D0/D1=camera local0/4로16fee에 tail call한다. 마지막 node까지 전체 공개 레지스터를 승계해야 한다.

1a3c8은d404/d406.WORD와d408.LONG을0으로 쓴다.

## 준비 phase 반복

1a65a에서1a26a script를 실행한다. 이어199d4는A1=d3b4, null이면D7=MOVEQ0, 비영이면D7.low=WORD(A1+a)를 읽는다.

D6.low=d41c로 놓고 unsigned D7.low와 비교한다. D7이 작으면199ea로마지막구간을검사한다. Nullcursor일 때 carry=1, 비영은1971c의 다음type WORD 음수여부다. Carry=1이면d41c.word=D7.low로 목표를 낮춘다. D7이 목표 이상이면D7.low=D6.low로 제한한다.

D6.low=d416을 읽고 unsigned D7.low>=D6.low이면D7.low=D6.low로 제한한다. D7.low를d418에 저장한 뒤 SWAP/CLR.W로16.16 시간으로 만들어19938을 호출한다. 결과D0/D1을d3bc/d3c0에저장하고 전체1a7a8을 호출한다. 전체update의debug와네path도 같은호출중연속실행한다.

업데이트 후 D7.low=d418로 다시읽는다. Unsigned d418<d41c이면1a65a로반복한다. 원본이진행하지않는입력에대해서는완료값을조작하지않고명시적실행한도오류가필요하다.

## 마지막 위치 정리와 배치

Camera10d38e의local0/4를D0/D1로읽고A1=0으로43e22를호출한다. 네node도각local0/4를읽어A1=0으로16fee를호출한다. 각node는직전호출의레지스터를승계한다.

D7.low=d41e를읽고 unsigned d41e<d41c이면1a29e를호출한다. 이어1a414 전체배치를실행한다. Script opcode0c가d40e를설정했을수있으므로초기값0을근거로배치를생략하면안된다.

마지막에RAM10.word=0,2ffff2.word=1000,2ffff0.word=0을순서대로쓰고1a73a RTS한다. Port목록은각callee의출력을호출순서대로연결해야한다. Native stack/CCR 전체노출과자연frame scheduling은별도계약이며, 현재조각들의시험통과만으로이일반호출완료를주장하지않는다.

## C++ API 및 재생성

`initialize_scene`은 위 일반 호출을 `SceneMapTransferState`의13개 레지스터(D0-D7/A0-A4)와 별도 A6 입력으로 연결한다. A6는 변하지 않는다. 기존12register helper를 연결할 때 A3를 보존하고, 전체 장면 갱신은13register 결과를 승계한다. 기존 null-script 특화 API를 이 함수로 임의 대체하지 않았다.

Script/motion은 사용 시 유일한 fixed MS5D 창을 선택한다. Palette/map은 기존 banked 리소스와 helper 계약을 따른다. Debug table은1af12의512byte 창이다. 각 helper가 반환한 포트 목록을 순서대로 이어붙이며 전체 초기화에 성공한 경우에만 RAM·레지스터·포트 결과를 게시한다. 후반 배치에서 실패해도 앞선 script/map 출력은 외부에 게시되지 않는다.

임시 phase 반복 한도는1,048,576회다. Duration scan에도같은record한도를두며자료읽기가먼저지원창을벗어나면오류다. RAMmotion과각하위helper의지원범위밖동작은명시적으로미지원이다. Callback주소저장과callback실행을구분한다.

```text
make -j3 all test
.venv/bin/python tools/inventory_scene_general_initialization.py
.venv/bin/python tools/observe_scene_general_initialization.py
.venv/bin/python tools/verify_scene_general_initialization.py
build/initialize_scene D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS RESOURCE_FILE_OR_DIR...
```

리소스입력은scene_scripts/scene_maps/scene_secondary/scene_placements의MS5D와scene_debug.ms5d다. CLI는파일또는directory를읽고fixed/banked loader를선택한다. Header/CRC검증은loader가담당한다. Resource와RAM·port출력의경로/symlink/hardlink alias를거부한다. 포트파일은기존size8/addressBE32/valueBE32의9byte record다.

## 실제 caller 입력 목록

원본47a94는A4=LONG(A6+76), A0=LONG(A4+2), D0.low=WORD(A4+0e) 뒤47aa0에서1a5a4를호출한다. Catalog59record는41개비영script와4개null record를포함한다. Target은0×49,60×1,80×3,130×1,220×1,500×1,580×2,830×1이다(값은16진수). Raw catalog값과자연도달가능성은구분한다.

명시한10개원본창은211행이며미해독0이다. Disassembly SHA256 `26cb5b0aa51a69e3cd457dbbd82a26df28c3ca988fce3346e3814dd3c50c688c`,contexts SHA256 `dae6f294d18510d56d1a795b70460dbfdc1a74816818267ae51851048b8f2ed0`. Stage catalog manifest SHA256 `8df755304fc28f981c0eb3c6f400be40ff06014e78f074d5a661b91fe3401ffd`. 자동역어셈블과literal목록만으로실행동등성을판정하지않는다.

## 다음 caller 연결의 경계

1a5a4 반환 뒤47aa6은A6+76의record를LIVE로다시읽고+6 포인터를e8a1c에전달한다. e8a1c는null일때e89e4를선택하여de26.LONG에쓰고de2e.byte=ff/de2f.byte=0으로놓는다. 다음47ab4..47ac0은d683의bit1/3/5를설정한다.

48398은30f4의byte lookup 뒤d67e.byte=D0.byte,d67f.byte=ff로쓴다. 30f4는fd8c.byte를D0.byte로읽고ANDI.W7을적용한후30ec의8byte table을조회한다. D0상위WORD는보존된다. 이표의리소스추출과호출연결은별도남은작업이다.

47aca는record를다시읽고+0a 포인터가비영이면그포인터의LONG을한번역참조한다. D0.low=record+0e로e905c를호출한다. e905c는정적객체100bf4/callbacke9150으로2a28을호출한뒤입력포인터와target에따라후속stream cursor를선택한다. 기존restart_static_object는D1/D3만선택적으로반환하므로전체register caller연결을그대로대체하지못한다. e905c의stream자료와2a28 전체register계약도추가확인이필요하다. e905c 완료후47ae6은A6callback을47af0으로설정하고480bc로분기한다. 여기서관찰한명령만으로47a94전체실행완료를주장하지않는다.

## 전체 호출 검증 결과

221조건에서원본1a5a4부터RTS까지전체64KiB RAM·14register·순서있는3,176,113포트명령이C++와일치했다. 각포트는size/address/value9byte record를그대로비교한다. 원본코드patch나callee대체는없으며호출중contextreset도없다. 입력fixture는원본2790/3ef2로준비한후debugflag/bounds/allocation조건을명시적으로설정했다. 이준비는실제게임boot/scheduler관찰이아니다.

Corpus는41script target0,59catalog실제script/target쌍,41script의추가debug/할당조건82개,null target경계10개,선택한3script의7fff/8000/ffff target9개,비영target의debug8/16·할당조건12개,실제CLI승계8호출이다. 59catalog쌍을단독함수입력으로실행한것이며각stage의모든callback실행·자연도달·직접플레이를의미하지않는다.

실제phase루프332회(호출당최대13회),map전송진입904회중185f2성공856회,배치/43e08각102회,allocator거절23회를관찰했다. Debug8/16분기의lookup호출은각38,400회다. 메인검토후추가한guard는multi-loop,실제map전송과ports,placement,debug두분기,할당거절후100ec6쓰기를요구한다.

4CLIsequence의8호출중4호출은직전CLI RAM/register출력을사용한다. Host는D0.low target,A0 script,A6 parent를다시제공한다. 나머지상태의승계를전체게임프레임진행으로표현하지않는다. 오류111조건에서입력과기존RAM/port출력을보존했다. Lateallocation실패,script/map/placement/secondary자료누락,숫자범위와파일alias를포함한다.

- Native observation SHA256 `7cf8f965dd1b774eafff1ad73400eab54dca1a8373f8a75ce6cb14557ddffa6e`.
- Verification SHA256 `950e3dd90209d2efd6a6629bf1568996396fb6005bede6e79df0f2ae290316eb`.
- CLI SHA256 `ec40eaeb8e7f0d379c841c331629552fc38a47851a84385cafc5d1ce2c13c163`.

458resource·5manifest·contextinventory·binary의전후불변을확인했고메인도현재hash와각native/report행을대조했다. 전체make Python175/C++111/경고0. 메인은실제directory인자경로로canonical첫조건을추가실행해RAM/orderedports일치도확인했다. 물리bank는CPU주소와ROM주소를모두사용해구분한다. Nativefixture instruction cap은2,000,000이며이는C++ API의phase한도와별개다.

## 후속 이벤트 입력 목록

`inventory_stage_event_contexts.py`는 원본 및 기존 stage catalog를 대조해59record의+0a 간접 포인터와+0e target을 목록화한다. 비영 stream 입력52개, null7개이며 고유 간접 포인터와 stream은 각각47개다. 비영 stream의 첫 WORD를 부호 있는 상대 오프셋으로 읽고, header 직후를 기준으로 첫 gate를 찾는다. Gate는 첫 BYTE가0이고+2 WORD가target 비교값,+4 WORD가다음 gate의 부호 있는 상대 오프셋이다. ff BYTE에서 이 건너뛰기 과정이 멈춘다.

47개 stream의 gate chain에서고유612개 gate를확인했고모두ff에종료한다. 실제catalog target으로선택하면42개는target0의header직후,10개는gate,7개는null이다. Target0은첫WORD jump를적용하지않는다. 보고서SHA256은 `42dd9abc3b757545521fca62a14dab435b51b236c7f97434d515d6b383394372`다.

이목록은원본e905c의선택알고리즘을기계적으로적용한결과이며native실행검증은아니다. 건너뛴내용은opaque로남기며ff를전체event resource의끝으로단정하지않는다. 이벤트opcode전체문법·runtime리소스추출·e905c실행연결은다음작업이다. 재시작2a28의전체레지스터계약은별도 `object-restart-full.md`에서관리한다.
