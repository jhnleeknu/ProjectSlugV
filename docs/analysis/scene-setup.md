# Scene opcode08의 장면 표시 설정과 descriptor

## Source와 목록 범위

Baseline은 `c96d141`이며 canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. Script·descriptor CPU 주소는 first1MiB 고정 ROM이며 같은 파일 offset이다. Descriptor payload의 node pointer는 CPU RAM 주소로 분리한다. 주소·상수는16진수,개수는10진수다.

`tools/inventory_scene_setup.py`는 canonical stage catalog가 참조하는41 script에서 opcode08의 operand BE32를 수집한다. 총41참조와15개의 고유 descriptor를 확인했다. 원본43ffc helper 의미는 메인이 분석 중이므로 이 목록을 실행·allocation·scene 초기화 완료로 취급하지 않는다. 원시 목록 뒤 아래 MS5D descriptor 추출까지 확장했다. C++ core는 별도 담당자가 구현 중이며 이 문서의 원본 관찰과 추출 결과는 C++ 동등성 검증과 구분한다.

## 원시 record 문법

메인이 확인한 문법은 첫word signed stride,offset2 word type다. Prefix에서type1/2는 signed stride만큼 다음 record로 진행한다. Prefix type0은 같은 stride로 한 번 진행한 뒤 suffix 단계로 바뀐다. Prefix type3은 즉시 끝난다. Suffix에서는type1/2를 따라 진행하고type3에서 끝나며type0은 이번 확정문법의 미지원이다.

| Type | 기록하는 최소 필드 |
| --- | --- |
| 0/3 | 첫 signed stride word와type word,4바이트 |
| 1 | 위4바이트와offset4 requestslots BE16,6바이트 |
| 2 | 위4바이트와offset4 node RAM pointer BE32,8바이트 |

최소 필드 길이는 논리 record 전체 크기의 증명이 아니다. Record마다 phase/CPU·ROM주소/stride raw와signed값/type/raw최소필드/next주소를 보존한다. Request word와type·stride를 혼동하지 않으며 node pointer의 구조나 field role은 추측하지 않는다.

Scan은 start+65536바이트 및fixed1MiB 범위를 제한하고 visited address로loop를 검사한다. 음수 stride·unknown type·suffix type0·unaligned/범위/truncation을unsupported 상태로 남긴다. 현재canonical에서는이상값이나음수stride가없어메인에게해석질문을만들지않았다. 일반음수stride가원본에서절대불가능하다는주장은하지않는다.

## 실제 descriptor 목록 결과

15개 고유 descriptor를 각 한 번 따라갔을 때84개의 record 후보를 보존했고 전부type3 terminal에서 끝났다. Prefix/suffix phase counts는 다음과 같다. 이 수치는41참조에 따른 가중 사용빈도가 아니라 고유 descriptor별 목록의 합이다.

| Phase/type | Record 수 |
| --- | ---: |
| prefix1 | 12 |
| prefix2 | 13 |
| prefix0 | 15 |
| suffix1 | 2 |
| suffix2 | 27 |
| suffix3 | 15 |

Stride값은0:15,4:15,6:14,8:40이다.0은모두type3 terminal에서진행하지않는값이다. Type1의requestslots word는0040이13개,003c가1개다. Type2의node RAM pointer는109156/10b1d6/10d256 세값이다. 이 값은raw참조이며slot allocation·node clearing·VRAM효과나RAM효과계약으로일반화하지않는다.

Descriptor 주소는048944/0da392/0da3b8/0db994/0db9ba/0dc4b2/0dc4fe/0dd238/0ddc46/0ddc6c/0ddc92/0e4f96/0e6208/0e6eac/0f1a8e이다. 구조별raw순서와41script참조는report에기록한다.0e4f96은prefix0→suffix3의2개record만있고,나머지descriptor의request/node순서는추측없이목록에남긴다.

## 재생성과 근거

```text
.venv/bin/python tools/inventory_scene_setup.py
```

실행exit0으로41참조/15고유 descriptor/84record/type3 terminal15개를 확인했다. 합성 직접검사는prefix0이stride후suffix로전환하는조건,0stride type1 visitedloop와음수stride unsupported 정지를 확인했다. 원본code/data를수정하지않았고 source전체SHA를검사한다.

`artifacts/scene_setup/report.json` SHA256은 `6063646f4c19288c3548007ea3ea932cb123a5e03f97210b81f64910f124f2b1`, `inventory.asm` SHA256은 `bbee01ae20072b19d704ddaf92faf4acdbc875f59a618cdc38e57f484c21f777`이다. `.asm`은명령역어셈블이아니라descriptorrawfield 목록이다. 자동목록은nativetrace·전체helper분석완료가아니다.

## MS5D runtime 추출

`tools/pack_scene_scripts.py`의 `descriptor_span`은15개 descriptor를 기존MS5D v1 kind1 `descriptor_%06x.ms5d`로 만든다. Stable ID는 `scene-setup:%08x`다. Payload는최초주소부터type3terminal의4바이트까지의연속창이며record field 사이stride gap을그대로보존한다. 일반stride는비음수짝수이고최소type1:6/type2:8/type0:4를포함해야한다. Type3은4바이트를보존하고첫word임의16비트를허용한다. Terminal의첫word는주소전진에사용하지않으며음수/홀수값을거부하지않는다. 후속MOVEM.W의D0signextend에영향을줄수있으므로raw그대로남긴다. Suffix0·unknown type·음수/홀수/부족stride·loop/bound/truncation은오류다. 이오류처리는원본trap/addresserror를정상실행으로위장하지않는다.

Canonical15파일/41참조/총524payload바이트를생성했다. 전체manifest는기존184dependencies에15개를더해199파일/9000payload바이트이며최종manifestSHA256은 `9bf33a996fedc298a189fd456eddaa0e9f64f90aa3358277f8f9007ec20f09d8`다. Metadata는CPU/ROM offset·end·kind/version/container/payload hash/reference와prefix/suffix record목록을기록한다. 기존script·기존dependency binary내용은유지한다.

```text
.venv/bin/python tools/pack_scene_scripts.py
.venv/bin/python -m unittest tools.tests.test_scene_script_pack -v
```

Packer exit0,합성시험14개가통과했다. 신규descriptor2시험은prefix→suffix전환과gap보존·terminal4byte만포함·firsttype3의firstword0/1/ffff/8000허용,미지원type/nonterminalstride/suffix0·truncation·주소오류거부를확인한다. 실제15container는headerkind1·CRC·canonical raw bytes·SHA가일치했다. 추출데이터/ROM은Git에추가하지않는다.

## Standalone 원본 관찰

`artifacts/scene_setup/native_observation.json` SHA256은 `f1f2d26f9b315f96929619e4d7001162de8be4f6ea44afdf349241419b06a673`이다. 별도관찰도구는41canonical opcode08×4fixture,총164개를수정없는원본dispatcher와callee로RTS까지실행했다.164개모두완료했고A7/다음A1과bank2→3→2경계를관찰했다. 총1,372,384 ordered MMIO는case별binary/count/hash/대표trace로보존한다. FullRAMhash·fullregisters·직접callee counts도report에있다.

Fixture는randomRAM/highregisters,A5=108000,A3/A6=0,외부stack1feffc의standalone조건이다. PVC word1000/2000에한해physical200000..2fffef를ROM2MiB/3MiB source로모델링했다. Registeroverlay tail은immutableROM검사에서제외하며fixedROM과physicalbankpayload는불변이다. 이것은원본관찰이며C++ equivalence·자연scene실행·임의PVCbankmapping·scheduler/audio/video timing을증명하지않는다.

## 장면 표시 설정 API

`scene_setup.h/.cpp`의 `setup_scene_resources(ram,descriptor,state,ports,error)`는원본43ffc의sprite queue/node초기화·영상slot양방향할당/clear와pool설정을연결한다. 맵데이터전체초기화완료나실제map tile/frameupdate를의미하지않는다. RAM64KiB와 `SceneCommandState` fullD0..D7/A0/A1/A2/A4를입력·출력하며descriptor는호출중borrowedpointer다. 입력A0가0이면descriptor를사용하지않고reset/pool설정을진행한다. 비영A0는그주소와같은CPU=ROMfixedwindow·짝수·exactterminalspan을요구한다.

먼저sprite queue를초기화하고RAM0010.word=1,orderedPVCword2000/0으로bank3MiB를선택한다.4개고정node109156/10b1d6/10d256/10d2d6에slotffff로초기화해node+26.word를ffff로만들고node+7a.bit0를지우며node+3a..+79를0으로만든다. RAM0010.word=0과PVCword1000/0으로bank2MiB에복귀한뒤380slot의3개VRAMlong과각watchdog를순서대로발행한다. RAMd496=0,d498=017c로slot가용범위를설정한다. 이bank전환순서와영상port는ordered결과이며단순최종값으로축약하지않는다.

Descriptor prefix는앞방향원시순서로읽으면서RAMd49a=ff인상위끝할당을사용한다. Type1의request word는pool할당을,Type2는32slot할당뒤지정RAMnode의slot설정과영상clear를수행한다. Type0을만나면stride후주소로가서RAMd49a=0/D7=0으로suffix를수집한다. Suffix는원시앞방향으로주소를stack목록처럼모은뒤역순으로처리한다. Type3에서종료하며suffix0은APIerror다. 일반record처리의MOVEM.W효과는stride/type을fullregister에signextend하므로word상위bits보존으로일반화하지않는다.

Slot할당은LIVE d496/d498의아래·위경계를사용한다. 남은request가0이아니면원본unsupportedtrap조건을APIerror로거부한다. Type2 node는짝수RAM CPU주소와전체7b바이트span을요구한다. 비음수slot에서는1024회×2VRAMlong과watchdog,그후32회×2영상slotlong과watchdog를발행한다. 음수slot은해당영상writes를건너뛰지만RAMslot/flag/historyclear는수행한다. Pool설정은기존sprite poolcore를사용하며descriptor종료뒤남은범위도마지막pool에등록한다.

성공은RAM/fullstate/orderedports를교체한다. Resource/stride/type/node/slotcapacity/pool오류는앞선reset·PVC·영상writes를포함해candidate전체를취소한다. Helper는caller를실행하지않는다. Genericnulldescriptor·terminalword·alias/오류범위의C++시험과canonical원본비교를분리해기록한다.

## Opcode08과 현행 CLI

`execute_scene_command`는20개opcodehandler를지원하며08의operandlong을A0로읽어setuphelper를호출한다. 비영pointer의dependencyfilename은descriptor_%06x.ms5d다. Helper에서변한A1은원본wrapper의savedscriptcursor복구를따라command.next_cpu_address로반환한다. 공개register는기존12개이고A3/A5/A6/CCR·CPUstack은API밖이다. Nullpointer08는API에서descriptor없이지원하지만canonical41reference에는null이없다.

```text
build/step_scene_command D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A4 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS SCRIPT_MS5D NODE_POINTERS_MS5D [DEPENDENCIES_DIR]
```

CLI는실제A1 command의비영08pointer를찾아DEPENDENCIES_DIR의descriptor를기존fixedloader로읽는다. Node/script파일의기존항상loading과selecteddependency의alias/header/CRC조건은유지한다. JSON은12fullregister+writecount,port파일은기존9byteorderedrecords다. Null08는dependencydir를사용하지않는다.

## 현행 최종 C++ 원본 비교

최종 `artifacts/scene_command/verification.json` SHA256은 `a7941afc795daf3895485ed76c1afd493f3b3b6b3941d36c43aeaf5010522ee8`이다. Session57582은exit0으로4,535 native/104negative/1,737,175 ordered ports를통과했다. 전체RAM/full12registers/orderedports와A7RTSendpoint가일치했다. Binary SHA256 `f20d9a1830f449b4089f8d49a89711a52f4e3c3870240a2ab8ba0253304779a6`와fixedROM은시작·끝에같았다. PVC1000/2000에따라physical200000..2fffef가실제ROM2MiB/3MiB source로동적전환하며각bankpayload는불변이다. PVCregistertail은ROMimmutable검사에서제외한다.

08 subset은205조건/1,715,480ports다. C++의9-byteport파일과원본의전체portbytes를비교하고각trace의count/SHA/prefix를report에남겼다. 이205조건의C++equivalence와앞의164case native-only관찰은서로다른matrix이며합산하지않는다. Canonicaloperand41개는patch하지않고randomRAM/highregisters와원본3ef2초기화는명시된fixture다. Native-only관찰의A3/A6=0등조건과전체matrixfixture조건도서로구분한다.

기존184개와descriptor15개,총199dependencies가canonical rawbytes와CPU/ROM/CRC에일치했다. 새08 missing/malformed descriptor·CRC-valid wrongwindow·outputalias는temporary복사파일에서검사하고출력을보존했다. 원본resource와ROM은수정하지않았다. Genericnulldescriptor·합성stride/type/terminalword·alias조건은C++시험으로구분하며canonicalnative효과를그범위로확대하지않는다.

Canonical41script의814command는모두지원하며미지원occurrence는0이다. API지원20opcode중4c는canonicaloccurrence0이므로C++합성unit만확인했고native도달을주장하지않는다. 실제CLIcarry43구간/824호출은41script의814helpercall과별도2palette재등록구간10call이다. 각script의원시command를순차적으로단일helper에전달했으며 **원본1a26a phasegate를실행하지않는다.** 따라서모든command개별동등성과실제출력carry를확인해도전체interpreter·script의자연진행·scheduler가완료된것은아니다. Callcontext재설정과negative terminator경계도report scope에남긴다.

전체`make -j3 all test`는exit0,Python139/C++99/warning0으로통과했다. 로그는 `artifacts/scene_command_build_test.log`다. 현재완료는원시descriptor리소스와장면표시설정·단일20handler검증이다. 실제maptile/frameupdate·scenephasegate와전체interpreter·자연게임도달·hardwaretiming은미완료다.
