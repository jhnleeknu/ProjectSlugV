# 제어 메뉴 전체 문자 배치 분석

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정CPU/파일9e1a는제목과항목전체,9d3a는한항목,9f7c는항목style선택이다. 이번범위는실제93e0메뉴의flags0·6항목이다. 다른메뉴와separator항목의일반지원으로확대하지않는다.

## 제목과 항목 위치

current slot의visible height(+4)가0이면9e1a는반환한다. 제목길이를38e8로측정한다음`width-count`를byte로잘라signed ASR.B #1로2로나눈다(음수는아래쪽으로반올림). x를ADD.B한뒤x<<5, y를ADD.B하고7000을더해제목주소를만든다. 단순host unsigned 가운데정렬과다르다.

제목의초기style은current==head일때0103,다른경우0603이다. 원본문자열의c/p명령이이후font/page와palette를바꾼다. 메뉴에는비ASCII문자도있으며원본byte를그대로그린다.

항목은slot+8에index를기록하고9d3a를호출한다. `uint8(index+1) >= visible height`이면아무것도그리지않고callback도호출하지않는다. 숨겨진항목도+8갱신에는포함되므로현재메뉴6항목의반복종료시+8은5다. height0조기반환에서는기존값을유지한다.

항목주소는기준x/y위치에word20을더하고index+1을ADD.B한다. flags0에서는선택표시2칸을배치한다. 선택항목의word는0313/0314,그외는00ff/00ff다. 각화살표는a018가림을검사하지만가려져도다음칸으로word20증가한다. 그뒤문자열을그린다.

## 스타일·가림·콜백

항목이현재head메뉴이면기본style0003이다. 오래된메뉴에서선택되지않은항목은0603이고선택항목은0003이다. flags&0e==2의다른색경로는원본에있지만이번실제카탈로그flags0검증범위에는포함하지않았다.

호출자가A1=3650을지정하면글자마다직접타일long쓰기와8200 word주소reset을수행한다. A1=a008이면가림검사후RAM7f16의renderer로간다. 가려진글자는renderer를호출하지않으므로cursor도진행하지않는다. 따라서직접trace후일괄삭제하는방식으로가림을구현하면원본과달라질수있다. 제어명령은가려진상태에서도해석된다.

보이는항목은마지막에9b3e를통해event5로처리함수를호출한다. 실제6주소9488/94d6/949a/94b8/950c/9532는event5일때추가RAM/포트변경없이반환한다. event3/4/7에는종료·중첩메뉴·외부루틴등다른동작이있으며이결과로no-op처리해서는안된다.

## 검증과 다음 구현 계약

```
.venv/bin/python tools/analyze_menu_text.py
```

전체원본9e1a를실행하면서9d3a·3650/a008·실제항목callback까지생략없이실행했다. 288조건의전체RAM,모든비디오포트쓰기폭/주소/값/순서,callback대상/event/인자가독립모델과일치했다. visible height0/1/2/4/8/255,선택0/3/5/255,폭0/16/255,직접/가림renderer,단일/중첩상태를포함한다.

모델은카탈로그에관찰한c/p명령만허용하며다른명령이생기면실패한다. 원본함수본문을모델로치환하거나callback을건너뛰지않았다. 출력은artifacts/menu_text/analysis.json이다.

다음C++연결은기존문자해석기에glyph단위가림을연결하고,배치·선택표시·style및event5 dispatcher를원본순서대로수행해야한다. 초기분석후아래지원범위의C++배치를추가했다. 이분석은자연게임입력도달성이나팔레트/픽셀화면검증이아니다.

## C++ 배치 통합

`draw_menu_text(ram,resource,clip,initial_line,writes,error)`가공통MS5D descriptor/문자측정/직접문자출력/가림판정을사용한다. 현재지원범위는flags0,nonnull제목및일반항목,descriptor와일치하는항목수,callback0또는확인한6개event5 no-op함수다. 지원밖의flags/separator/callback은명시적으로거부한다. 오류시RAM과출력목록을모두보존한다. height0에서는리소스를읽지않고빈목록으로반환한다.

직접문자해석기에`FixedTextVisibility`함수포인터를추가해glyph마다출력여부를판정한다. invisible이면두포트쓰기와cursor증가를함께생략한다. 제어명령은계속해석한다. 기존직접출력API는null callback으로같은구현을사용한다. clip모드는RAM7f16의3650 renderer를검사한다.

```
make all test
build/draw_menu_text INPUT_RAM INPUT_MS5D OUTPUT_RAM OUTPUT_WRITES CLIP LINE
.venv/bin/python tools/analyze_menu_text.py --cpp
```

CLIP은0/1,LINE은제목길이측정시원본D3의word초기값이다. 출력포트파일은기존9byte진단레코드(size/address/value)다. 실제게임용입력은원본MS5D이며출력기록재생으로배치로직을대체하지않는다.

원본288조건과C++의전체RAM및쓰기폭/주소/값/순서가일치했다. 지원밖callback/flags에서상태보존,높이0의리소스생략과glyph가림시cursor보존unit검사도통과했다. a370의상태전환과선택입력,다른event callback,메뉴픽셀/팔레트연결은계속남아있다.
