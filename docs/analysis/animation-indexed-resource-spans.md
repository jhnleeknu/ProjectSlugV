# Opcode10 indexed draw의 원본 읽기 범위

## 기준과 조사 방법

기준commit은 `27cadc4`다. `load_verified_program`으로canonical BE ROM 8,388,608바이트와SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`를확인했다. 아래fixed CPU주소는ROM파일offset과같다. 원본handler는padded `disassemble_range`로명령경계를확인하고raw bytes를대조했다. 알려진script목록은기존 `tools/pack_animation_branch.py::extract(program)`을메모리에서호출한결과만사용했다. ROM/추출물쓰기·빌드는수행하지않았다. code영역의임의BYTE검색으로새script를발견했다고주장하지않는다.

## 사실: 원본 명령과 비트 폭

dispatch `4a032`의raw `600001f8`은handler4a22c로분기한다. handler진입A1은opcode뒤selector주소다.

| CPU/ROM | raw | 실제 연산 |
| --- | --- | --- |
| 4a22c | 7000 | MOVEQ0 D0, 전체32bit0 |
| 4a22e | 1019 | selector BYTE→D0.byte, A1+1 |
| 4a230 | d040 | ADD.W D0,D0: BYTE0..255를WORD0..1fe로변환 |
| 4a232 | 45f90004a76c | A2=4a76c |
| 4a238 | 30320000 | WORD(A2+signed16(D0.W))→D0.W |
| 4a23c | 3219 | list byte length WORD→D1.W, A1+2;D1.high16보존 |
| 4a23e | 48711000 | PEA(A1+signed16(D1.W)): list복귀주소저장 |
| 4a242 | 10360000 | BYTE(A6+signed16(D0.W))→D0.byte;D0.bits8..15보존 |
| 4a246 | e748 | LSL.W3 D0: WORD내shift/wrap,high16는0유지 |
| 4a248 | b041 | CMP.W D1,D0 |
| 4a24a | 64000024 | BCC4a270: unsigned D0.W>=D1.W이면draw생략 |
| 4a24e | 0c3100040000 | BYTE(A1+signed16(D0.W))가04인지검사 |
| 4a254 | 67000012 | 같으면4a268 |
| 4a258 | 4e4f | 다르면TRAP15;4a25a..267의문자열을실행명령으로해석하지않음 |
| 4a268 | 43f10001 | A1=list_base+signed16(D0.W)+1 |
| 4a26c | 6100fe9e | BSR4a10c: 기존draw body실행 |
| 4a270 | 225f | 저장된list복귀주소→A1 |
| 4a272 | 6000fd8a | BRA49ffe: 다음dispatch;4a276pointer저장경유안함 |

selector는BYTE×2이므로indexWORD는항상비음수이며fullBYTEdomain의raw WORD창은 **[4a76c,4a96c),512바이트**다. 이창의원본payload SHA256은 `bee40eadfbd8d63117913312079cb3629c3d9c5e72a04f2d2dbb08d7f226cfbd`다. 0c의fullWORD selector doubling/signedwrap과혼동하지않는다.

table에서읽은WORD를F,live field BYTE를B라하면field주소는A6+signed16(F)이고선택offset은 `O=(((F&ff00)|B)<<3)&ffff`다. `B*8`로단순화하면F.highBYTE가0이아닐때틀린다. D0.high16는처음MOVEQ0으로0이며D1.high16는length읽기후에도incoming값을유지한다. 모든WORD조합에서O는8배수이지만원본length L에는8배수검사가없다.

## 사실과 도출: 실제 span 요구

명령주소P에대해selector P+1,BE16 length [P+2,P+4),list_base Q=P+4다. 먼저selector/tableWORD/length를읽고복귀주소 `E=Q+signed16(L)`를계산하여stack에저장한뒤live fieldBYTE를읽는다. PEA는E가가리키는메모리를읽지않는다. draw생략이어도table/field조회는필요하다.

unsigned O<L일때만 `T=Q+signed16(O)`의opcodeBYTE를읽고04이면뒤7바이트를draw body가읽는다. 따라서선택항목은T의8바이트명령을제공할수있어야하며,draw내부의실제조건부읽기/쓰기·sprite재개요구는별도callee계약을따른다. O>=L이면선택항목을읽지않는다. draw성공/생략모두E로돌아가며E의다음opcode는그후dispatch에서도달했을때필요하다. length만큼전체list를미리읽는동작은없다.

**도출:** unsigned비교가통과해도signed pointer는음수가될수있다. 예를들어O=8000,L=8001이면선택T=Q−8000,복귀E=Q−7fff다. L=ffff의복귀는Q−1이다. O=fff8도큰unsigned length에서선택가능하다. L=1/O=0이면첫8바이트draw를실행하므로선택항목이선언length안에완전히들어간다는보장도없다. L=0은모든O에서생략한다. 이를일반적인「L/8개의유효항목배열」로바꾸거나모든범위를앞방향[Q,Q+L)로고정하면원본명령과달라진다. 32bit/24bit pointer wrap·정렬·지원RAM/fixed경계는앞으로의전체상태계약에서실제접근과분리하여확정해야한다.

## 사실: 알려진8개 list command

기존extractor는caller `[2bb06,2bb16)`의raw `227c00065f56303c01004eb900049f8c`와group설정2b6e6/2b7ce의 `3d7c00f20020`을검사한다. script `[65f56,662c2)`는876바이트/34개상위명령이다. 원본payload SHA256은 `63a1c8e3de2e5d196144c4ea51f1030bd67a06527871fd6fc44ce0e496029e9e`다. 아래목록은extractor가opcode10으로인식하고내부각8바이트의첫BYTE04를검사한8건이다.

| command P | raw header | list Q | 복귀 E | 내부04개수/마지막항목 |
| --- | --- | --- | --- | --- |
| 65f64 | 101e0028 | 65f68 | 65f90 | 5 /65f88 |
| 65fa0 | 101e0028 | 65fa4 | 65fcc | 5 /65fc4 |
| 65fdc | 101e0028 | 65fe0 | 66008 | 5 /66000 |
| 66018 | 101e0028 | 6601c | 66044 | 5 /6603c |
| 6605a | 101d0088 | 6605e | 660e6 | 17 /660de |
| 660f6 | 101d0088 | 660fa | 66182 | 17 /6617a |
| 66192 | 101d0088 | 66196 | 6621e | 17 /66216 |
| 6622e | 101d0088 | 66232 | 662ba | 17 /662b2 |

selector1e은WORD `[4a7a8,4a7aa)`의raw007d,1d는 `[4a7a6,4a7a8)`의raw007c다. 따라서이8건에서F.highBYTE=0이며각각live object+7d/+7c를사용한다. 길이28hex=40바이트/5항목,88hex=136바이트/17항목은**이알려진8건의구조**다. fullBYTE field의다른값은일부선택을생략하며자연index가0..4/0..16에제한된다는증거는아니다. 예를들어65f68과6605e의첫8바이트는둘다 `0440000000153000`이다. draw identifier는list BYTE에서읽은operand이며group결합은별도원본근거를따른다.

앞의callback14/1e·1d와뒤list10의selector일치는extractor가검사한다. 이는같은object index BYTE를사용한다는정적연결근거이며callback의fullBYTE operand읽기범위나자연도달성검증을대신하지않는다.

## 현재 resource 재사용과 구현 범위

| 기존 파일/도구 | 실제 보존 범위 | 이번 분석에서의 의미 |
| --- | --- | --- |
| pack_animation_control.py → control_04276c.ms5d | [4276c,5276c),65536payload | fullBYTE selector창512바이트를이미포함;새data추출불필요 |
| pack_animation_branch.py → animation_065f56.ms5a | [65f56,662c2),876payload | 알려진8list header/모든내부04/후속명령을이미보존 |
| pack_animation_control.py → operands_06431a.ms5d | [6431a,64836),1308payload | 앞선1d/1e의known8operandbase각fullBYTE raw조회합집합;10자체는이창을읽지않음 |
| pack_animation_data.py → data_04a76c.ms5d | [4a76c,4a88e),290payload | selector1d/1e에는충분하지만fullBYTE domain512바이트에는부족 |
| pack_animation_branch.py → branch_data_06431a.ms5d | [6431a,6447a),352payload | knownlist의bounded5/17 indices용;fullBYTE operand창이라고일반화불가 |

현재실제container를읽어header/magic/원본주소/길이를확인했다. animation_065f56.ms5a SHA256은 `afc40b7d711c425542b18458b1bbf93ed463745186a8bb9e57d1a9177c286b00`,control창은 `0e110324fa9a7d039c91f3c9a44b11a9ea60e0bbd7a73376166f91983beef0c2`,operand창은 `832681dcfe9f037a2e1fa069c8327b9c1d15a144e5132fbfced8ada668e773b2`다. MS5A/MS5D는v1kind1,32바이트header뒤payload다. 기존loaders와mixedCLI는두kind를지원하지만,wide창과옛field창을동시에공급하면겹친다. 독립resource가있다는사실과새10전체상태C++소비완료를구분한다.

기존 `engine/src/animation_step.cpp::step_animation_with_data`는10의RAM/carry동작과selected8바이트fetch를구현한다. `tools/analyze_animation_indexed_draw.py --cpp`와기존문서는selector30의256상태×3timer=768조건을기록하지만full15R/PVC/pending의새증거가아니다. 현재 `engine/src/animation_execution.cpp`의전체상태dispatch에는10이없다. MS5A script와MS5D창은재사용가능하나selecteddraw의PEA복귀주소·sprite wait캡처·재개후E복원과live후속fetch의새계약/원본검증은미완료다. 모든selector/length/offset조합,모든list유효성,bankedscript,자연게임도달성·전체GOAL완료를주장하지않는다.
