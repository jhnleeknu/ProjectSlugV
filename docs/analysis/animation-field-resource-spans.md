# Animation 필드 변경·상대 분기의 resource 범위

기준b5ded33, [확정계약](animation-field-full-contract.md)을따른다. `load_verified_program`으로canonical BE ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`와8,388,608바이트를확인했다. 아래fixed CPU주소는ROM파일offset과같다. 원본명령의padded decode와raw를대조했고기존extractor를메모리에서만호출했다. 초기조사단계에서는ROM/추출물쓰기·build를하지않았다. 후속으로허용된packer구현단계에서는원본을읽어ignoredruntime에새MS5A/manifest를생성했다. ROM원본은수정하지않았고공유build는수행하지않았다.

## 사실: 원본 접근과 resource 종류

| opcode | 원본raw 근거 | script에서실제로읽는것 | fixed MS5D/대상RAM |
| --- | --- | --- | --- |
|18 |4a27e1019,4a2803219,4a282d241,4a28a32321000,4a28e1d801000|valueBYTE,selectorWORD|4a76c+signed16((selector*2)&ffff)의WORD;object+signed16(offset)에BYTE쓰기|
|1c |4a2947000,4a2961019,4a298d040,4a2a030320000,4a2a43219,4a2a63d810000|selectorBYTE,valueWORD|4a76c+selector*2의WORD;object+signed16(offset)에WORD쓰기|
|20 |4a2ac7000,4a2ae1019,4a2b0d040,4a2b830320000,4a2bc2219,4a2be2d810000|selectorBYTE,valueLONG|같은BYTEselector WORD조회;object+signed16(offset)에LONG쓰기|
|24 |4a2c47000,4a2c61019,4a2c8d040,4a2d030320000,4a2d453360000|selectorBYTE|같은WORD조회;object+signed16(offset)의liveBYTE읽기/감소쓰기|
|34 |4a2f243e90001,4a2f67000,4a2f83d590070|skippedBYTE는읽지않고뒤WORD만읽음|table없음;object+70에WORD쓰기|
|38 |4a30043e90001,4a3043d590020|skippedBYTE는읽지않고뒤WORD만읽음|table없음;object+20에WORD쓰기|
|2c |4a3e01019,4a3ea30320000,4a3ee3419,4a3f010360000,4a3f4d040,4a3f6b042,4a3fcd2f10000,4a40043f12000|selectorBYTE,lengthWORD;조건통과시현재A1+signed16(index)의WORD|같은BYTEselector WORD조회;object+signed16(offset)의liveBYTE읽기|

모든명령의후속4a276 raw2c09와4a278 raw2086은D6=A1,LONG(A0)=D6를쓴다. 따라서target이statepointer나뒤liveRAMscript와alias되면쓰기순서를보존해야한다. fixedmetadata에추정field구조나logicaltable정의를추가할근거는없다.

18은fullWORDselector65536개가두배WORDwrap후32768개의signed-even주소를만든다. 전체WORDread의합집합은 **[4276c,5276c),65536바이트**이며selector와selector+8000은같은WORD주소다. 원본payload SHA256은 `00fd4b3f850678709eb4da84d61addd145491b9a6f0afc5637b8bd273ad32bd4`다. 1c/20/24/2c의BYTEselector0..255는0..1fe인덱스이므로 **[4a76c,4a96c),512바이트**다. payload SHA256은 `bee40eadfbd8d63117913312079cb3629c3d9c5e72a04f2d2dbb08d7f226cfbd`다. 34/38은fieldselector창을읽지않는다.

## 2c: script내 상대 WORD와 조건부 span

opcode주소를P라하면selector는P+1,lengthWORD는[P+2,P+4),그뒤A1=Q=P+4다. fieldtableWORD F와livefieldBYTE B로 `I=(((F&ff00)|B)*2)&ffff`를만든다. MOVE.B는offsethighBYTE를남기며ADD.W는WORDwrap이다. length L과I의비교는unsigned다.

I>=L이면선택WORD를읽지않고cursor=Q+signed16(L)이다. I<L이면 **WORD(Q+signed16(I))를script에서읽고** 그signed16값R을Q에더한뒤다시signed16(L)을더한다. 원본4a3fc의ADDA.W는선택WORD를읽어A1을갱신하는명령이며,absoluteLONGpointer조회나MS5Ddata조회가아니다. 기존reader구분대로fixed주소에서는MS5A scriptwindow,100000..10ffff에서는현재RAM이다. fieldoffsetWORD만MS5D다. 고정script 안에비실행WORD가있어도container종류를MS5D로바꿀근거는없다.

**도출:** index+2<=length검사는없다. L=1/I=0도선택WORD2바이트를읽는다. 큰unsigned I가비교를통과하면서signed주소는Q앞을가리킬수있다. L=0도fieldBYTE읽기는필요하다. 최종cursor는선택변위와length의두signed가산을순서대로검사하고4a276pointer쓰기후dispatch에서읽는다. 생략경로의선택WORD나최종cursor의script를미리요구하지않는다. 개별WORD의정렬/완전span과주소계산범위는실제도달시에검사해야한다. 모든index/length/tableWORD조합이유효script를만든다는주장은하지않는다.

## 사실: 기존 known script inventory

아래는호출자raw검사를내장한기존extractor/inspector가인식한명령만집계했다. operand/padding에서우연히동일BYTE를찾는검색은하지않았다.

| 검증된script범위 | 기존목록화함수 | 명령수/실제opcode |
| --- | --- | --- |
|[6f1e2,6f21a)|pack_animation.extract|11:04×5,00×5,08×1|
|[65f56,662c2)|pack_animation_branch.extract|34상위명령:0c/14/10/00각8,08×2;10내부항목은04|
|[48980,489c1)|inspect_activation_animation_scripts.inspect|9:04×8,28×1|
|[489c2,48a12)|같은inspector|11:04×9,00×1,08×1|

위기존4개knowninventory에는이번18/1c/20/24/34/38/2c가없다. 이는기존목록의사실이며전체ROM에없다는뜻이아니다. 후속caller검토로새로확인한18 script는아래별도절에기록한다. native검증작업자에게이결과와2c의scriptread분류를전달했다. 제어된syntheticliveRAMfixture의전체원본실행이후검증은자연게임도달성과구분해야한다.

## 재사용 가능 자원과 미확인

기존 `tools/pack_animation_control.py`의control_04276c.ms5d가18의wide창과다른4개의BYTEselector창을모두포함한다. container SHA256 `0e110324fa9a7d039c91f3c9a44b11a9ea60e0bbd7a73376166f91983beef0c2`,payload65536/container65568바이트다. 옛data_04a76c.ms5d의290바이트는fullBYTE512도fullWORD65536도충족하지않는다. wide창과옛중복창을함께공급하지않는다.

현재MS5A/MS5D는v1kind1의32바이트header,원본CPU=ROMfixed주소와length/CRC/reserved검사를유지한다. 실제read는단하나의완전window에서충족해야하며distinct파일의partial/overlap ambiguity를성공으로바꾸지않는다. 새format/state/CLI schema는필요하지않다. 아래caller-backedscript를기존MS5A로보존하는별도packer만추가했다. 2c의fixedscript가새로확인되면실제도달WORD·명령span을담는MS5A범위를caller와함께정해야한다. 그후속범위나C++소비완료를미리주장하지않는다.

## 후속 사실: caller-backed18 script3e808

기존 `animation-field-branch.md`와 `trace_animation_references.py`의후보를출발점으로원본caller와script를직접대조했다. caller `[3d2e2,3d2f2)` raw는 `227c0003e808303c01004eb900049f8c`다. A1=3e808,D0.low=0100뒤3d2ec에서49f8c를호출한다. 이는데이터연결근거이며상위루틴의자연게임도달성이나compositiongroup을확정하지않는다.

| 명령주소 | 구조 |
| --- | --- |
|3e808|0c desiredff/selector002f/target3e832|
|3e810/3e81e|18 value35/selector0034|
|3e814/3e822|04 draw operandID0001f800/00020000|
|3e81c/3e82a|00 duration1|
|3e82c|08 target3e810|
|3e832/3e840|18 value49/selector0034|
|3e836/3e844|04 draw operandID0001a800/0001b000|
|3e83e/3e84c|00 duration1|
|3e84e|08 target3e832|

selector002f의WORD는4a7ca raw00a0,selector0034는4a7d4 raw00b0다. 따라서초기0c는live object+a0,18은object+b0의BYTE에접근한다. `[3e808,3e854)`76바이트는15명령으로닫히며0c양쪽과08target은모두범위내명령시작이다.3e854는다음0cscript의시작으로이번에는제외한다. 후속2c후보를이76바이트의분석완료에포함하지않는다.

`tools/pack_animation_fields.py`는sourcehash/callerraw/command경계/opcode/branch·jumptarget/duration/18selector·value와payload/container독립pin을검증한다. 출력은 `extracted/runtime/animation_fields/animation_03e808.ms5a` 및manifest.json이다. payload76/container108바이트,CRC32 `1e1cfb2f`,payload SHA256 `cbc72554fb13051c10e05639ad8a898472f1e7fde919eeff51b617ae8b7893ad`,container SHA256 `806f465a3e2bdeb831fc356350ce3fa18c4b03da6e3dce8a0574d9cc6e0e5bc7`다. metadata는stablecommandID/CPU·ROM대응/caller/rawcommands/wideMS5D의존성을보존하고group/palette미확정을명시한다. source/tool변경을종료시에재확인하고stage에서container/manifest를검사한뒤공개한다. 실제I/O실패시복수file의원자교체는보장하지않는다.

합성bytes/mockedsourcepins를사용한 `tools.tests.test_animation_fields_resource` 의9test가통과했다. 실제packer를실행하고공개파일을재build와byte비교하여기존MS5A구조를확인했다. runtime은ignored이며원본을Git에추가하지않는다. 실제native/C++/loader소비는실행문서의최종보고에기록한다.

## 최종 실제 소비 확인

`artifacts/animation_field_execution/verification.json` SHA256 `d7f3685c55b9401359b84eff53d10e2e26d3ada6222c2d49e5b885ad2dab6592`의fixedscript12조건에서기존C++MS5Aloader가위108바이트container와wideMS5D를소비했다. 원본전체49fc6와RAM/15레지스터/carry/orderedPVC96건이일치했다. 고정trace의18value35는3회,value49는9회이며4a7ca/4a7d4의실제WORD조회도확인됐다. object+a0는0/1/80/ff,timer는0/0100/ffff이고group/object/queue는제어fixture다. 두루프의원본명령소비를확인한결과이며자연group binding·게임도달성의증거는아니다. source/runtime/packer는최종검증중변경하지않았다.
