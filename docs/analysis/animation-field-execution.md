# Animation 필드 변경과 상대 분기의 전체 상태 실행

## 현재 bank-state CLI schema

[실제 bank 상태 계약](animation-bank-state-contract.md)에 따라 공통 `SAVED_LIST_END` 바로 뒤 argv22에 unsigned32 `CURRENT_BANK_BASE`를 전달한다. 일반 CLI는22숫자/23JSON, RAM/output/ports argv23/24/25 및 resource26+이며, sound CLI는27숫자/28JSON, callback4개 argv23..26, EXTERNAL argv27, RAM/output/ports argv28/29/30 및 resource31+다. 두 출력 JSON은 숫자 `current_bank_base`를 항상 포함한다. 임의 uint32 bank 입력을 허용하며 saved_bank와 구분한다. 이전 schema 자동 추정이나 기본값 보충은 없다. 아래 원본 관측·검증 수치와 해시는 해당 단위 당시의 완료 기록이며, 이 schema 이행의 재검증 결과를 대신하지 않는다.


[확정계약](animation-field-full-contract.md)과 [resource 범위](animation-field-resource-spans.md)를따른다. baseline b5ded33,canonical BE ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. fixed CPU주소는ROM파일offset과같다. 이번범위는opcode18/1c/20/24/34/38/2c이며기존전체상태실행의확정효과를확장한다. 아래최종검증은이번7opcode의실제원본/C++비교기록이다. 지원은13opcode의전체상태효과와14의제한된callback경로이며전체17opcode완료를뜻하지않는다.

## 실행 범위와 상태

18은valueBYTE와WORDselector를읽고두배WORDwrap/signedtableindex로얻은fieldoffset에BYTE를쓴다. D0상위24bit와D1상위WORD를보존한다. 1c/20은MOVEQ0 D0뒤BYTEselector로offsetWORD를읽고각각WORD/LONG값을D1과objectfield에쓴다. 24는같은offset조회후liveRAMBYTE를1감소시켜wrap하며그BYTE를D0에로드하지않는다.

34는skippedBYTE를읽지않고뒤WORD를object+70에쓰며D0전체0,D1불변이다. 38은skippedBYTE뒤WORD를object+20에쓰고D0/D1은불변이다. 2c는fieldoffsethighBYTE를남긴liveBYTE와ADD.W2의wrap, unsignedlength비교,조건부scriptWORD읽기와선택WORD/length의두signed가산을순서대로수행한다. 선택값은absolutepointer가아니며table내선택WORD의resource종류는MS5A script또는현재RAM이다.

모든명령은4a276의D6=A1,LONG(A0)=D6뒤dispatch한다. statepointer/뒤RAMscript와target의alias순서를보존하고다음fetch는현재RAM을읽는다. 실제도달하는BYTE/WORD/LONG의정렬·span만검사하며선택을생략한WORD나skippedBYTE를미리읽지않는다. length8배수나index+2<=length같은추가제한은없다. 원본의후속00/28timer와최종carry를포함한whole49fc6가검증대상이다.

이번명령은새pending을만들지않는다. 기존phase0/1/2/3와saved_list_end/callbackmetadata,기존세APIoverload를유지한다. 현재 bank-state CLI는일반22숫자/23JSON·sound27숫자/28JSON이며공통argv22 CURRENT_BANK_BASE를추가한다. 당시field단위의21/26숫자schema검증기록과구분한다. 일반CLI의phase2/1f거절도유지한다. 에러는RAM·15레지스터·모든metadata·carry·ports및external-input호출형의external_reads를보존한다.

## Resource와 파일 보호

기존control_04276c.ms5d의65536바이트wide창은18의fullWORDselector와1c/20/24/2c의fullBYTEselector512바이트창을포함한다. 34/38에는이table이필요없다. 2c의선택WORD는scriptreader로읽으며MS5D를공급하는것만으로fixedscriptspan을대신할수없다. 기존knownfixedscript4범위에는이번7opcode가없지만후속caller검토로3e808..3e854의18script를확인하고기존MS5A로보존했다. 이추가script도자연게임도달성이나compositiongroup결합을입증하지않는다.

MS5A/MS5D형식·loader·strictnumericparser·RAM65536바이트·regularfile/FIFO검사·canonical/inodealias·두출력O_NONBLOCK예약후fstat검증과쓰기순서는변경하지않는다. suppliedresource는미사용경로에도검증한다. 기존파일은검사실패에서보존하며실제쓰기시작후두출력의원자교체/rollback은보장하지않는다. 새format은없으며caller-backed76바이트script용pack_animation_fields.py만추가한다.

## 재현과 검증 상태

현재존재하는resource/build명령은아래와같다. 문서작업자는공유build를중복실행하지않았다.

```sh
.venv/bin/python tools/pack_animation_control.py
.venv/bin/python tools/pack_animation_fields.py
.venv/bin/python -m unittest tools.tests.test_animation_fields_resource
make build/step_animation_execution build/step_animation_sound_execution build/animation_execution_test
./build/animation_execution_test
.venv/bin/python tools/observe_animation_field_execution.py
.venv/bin/python tools/verify_animation_field_execution.py
.venv/bin/python tools/verify_animation_execution.py
.venv/bin/python tools/verify_animation_control_execution.py
.venv/bin/python tools/verify_animation_sound_execution.py
.venv/bin/python tools/verify_animation_indexed_execution.py
make all test
```

원본관측 `artifacts/animation_field_native/observation.json` SHA256은 `8ce1f6051cd06310e7e3e321f8ad9bbb879714ceee4381e8662883b936f3e508`다. requested991조건중818조건을immutablewhole49fc6로실행하여PVC3272건과전체RAM/15레지스터/carry/read·write·PC·stacktrace를기록했다. opcode별수는18=36,1c=187,20=187,24=309,34=5,38=5,2c=89다. 제외173조건은실제WORD/LONG정렬,지원RAM밖최종cursor,제어terminal과header/선택WORD의겹침등을명시하며모두원본에서불가능한행동이라고뜻하지않는다. 후보를수정하여성공수로숨기지않았다.

최종 `artifacts/animation_field_execution/verification.json` SHA256은 `d7f3685c55b9401359b84eff53d10e2e26d3ada6222c2d49e5b885ad2dab6592`다. primary818건의원본을재실행한뒤실제CLI전체65536바이트RAM·15레지스터·metadata·carry·orderedPVC3272건을비교했다. 별도합법length1/index0조건은선택WORDlow00BYTE와최종00opcode가겹치는경로로PVC4건까지일치했다. primary제어fixture가제외한겹침을실제원본불가능으로일반화하지않는보충증거다.

actualfixedscript3e808..3e854의12조건도기존MS5Aloader와wideMS5D를소비해전체RAM/15R/carry/PVC96건이원본과일치했다. object+a0의0/1/80/ff와timer0/0100/ffff를조합했고고정trace의18value35가3회,value49가9회실행됐다. actualWORD4a7ca/4a7d4조회가있으며object+b0쓰기뒤draw/00의후속효과를포함한다. group/object/queue는제어된fixture이고상위게임도달성·palette/compositionbinding은미확인이다.

negative64건은잘못된metadata·누락/부분/중복/overlap MS5D·실제operand/field정렬과span·2c포인터공개후최종cursor·늦은field쓰기후다음fetch·파일alias/FIFO/예약실패등에서실패와파일보존을검사했다. 성공fixture·별도보충조건·checked오류수는합산하지않는다. 문서갱신시보고서의입력33개와artifact6644개entry를모두현재hash와대조했으며중복path를합치면6676개다.

코어독립리뷰는원본명령폭·순서,부분register보존,liveRAMalias,34/38의미읽기padding,2cscriptread와unsigned비교/두signed가산,기존candidate transaction을대조하여조치할문제를찾지못했다. 코어작업자의normal/UBSan unit은통과했다. 원본observer의독립리뷰도hook의expected주입이나SR조작없이실제whole49fc6를실행함을확인했다. 구현작업자는대표56조건의전체trace를메모리에서재실행했고문서작업자도7opcode대표7조건을메모리에서재실행하여기록과일치함을확인했다. native입력8개/단계파일3272개의현재hash도모두대조했다. 기존observer·보고서를덮어쓰지않았다.

기존4회귀보고서도현재코어에서통과했다. execution90조건/98단계+15추가/164오류,control178조건+2혼합/48오류,sound22조건/30단계/73오류,indexed846조건/854단계+fixed30+signed6+soundCLI12/60오류다. 아래는이전문서의역사해시와구분하는현재보고서해시이며이번7opcode통과수에합산하지않는다.

| 회귀 | 현재verification.json SHA256 | 고유참조수 |
| --- | --- | --- |
|animation_execution|27ed7bb20a9c5b77a39533156e240d8d24fa4cf403d2f85e7b557a902e06d93e|699|
|animation_control_execution|8993f94d2dc60984522e8ccdce3a782fa35fb28523b4cb66300fea3edc2b02a7|1484|
|animation_sound_execution|5dc8bd9f0d4538e1407b34e55dab7991683674526a0d339e9452c2d105f0a561|274|
|animation_indexed_execution|08ed36f540bfc3e81c655ecab0739102c608c718736e724bcda54b3d3f28b0aa|7206|

통합 `make all test`는exit0,Python234개(새packer합성test9개포함)/C++test실행145개/컴파일경고0건이다. packer의공개container/manifest는build(root)재생성bytes와일치했다. 재현명령에는추가audit-onlyflag를붙이지않는다. 이전회귀용원본관측artifact가없다면각verify도구가참조하는기존observer를먼저실행해야한다.

30sound/3ccallback/40bankedlookup와14의다른callback,bankedscript/data,전체CCR/A7stack/cycles,물리mirror/IRQ/scheduler,composition/palette binding,자연게임도달성과직접플레이는별도미완료이며전체GOAL에서제외하지않는다.
