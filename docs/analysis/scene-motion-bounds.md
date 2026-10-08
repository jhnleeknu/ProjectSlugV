# 장면 경로의 폭·좌표 제한·가시 경계

## 근거와 목적

원본program SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래코드주소는fixed첫1MiB로CPU주소=ROM파일오프셋이다. RAM은100000..10ffff이며본문의d3xx/d4xx는RAMoffset이다.

Frame경로1a73c는1a2b4의조건에따른script실행,1a526 설정,19b96 좌표계산,19d08 경계계산,19802 phase조회,1a3d6 보정,전체1a7a8 update,1a442 단일배치를순서대로호출한다. 이경로의19b96/19d08이필요로하는198ee/19978/19d98/19d08을복원한다. 기존19938은record+8의bias를더하지만198ee는bias없이record+4의폭을반환하므로동일API로취급하면안된다.

## 198ee — 위치와 축별 폭

A1=RAMd3b4를읽는다. Null이면D0=WORDd3b8<<16,D1=WORDd3ba<<16,D2=D3=0으로반환한다. D4/D7등나머지레지스터는그대로다.

비영이면기존1972a selector를실행하고A1을RAMd3b4에저장한뒤18fd2의시간→위치계산을수행한다. 다음D2=D3=0,18c06의type조회로D4.low를갱신한다. Type<58이면D3=WORD(record+4)<<16,아니면D2=WORD(record+4)<<16이다. 상위WORD를추가부호확장하지않으며32bit상태에그대로옮긴다. 18c06의36entry분기표에서첫22개는carry1,나머지14개는carry0임을확인했다.

## 19978 — 제안 좌표 제한

198ee를호출한다. A1이null이면D0/D1을d3c4/d3c8에쓰고끝난다. 비영이면Y뒤X순서로계산한다.

```text
D3 += D1
if N(D3-D1): exchange entire D1,D3
D1 -= LIVE LONG(d3c8)
if not N(D1): LONG(d3c8) += D1
D3 -= LIVE LONG(d3c8)
if N(D3): LONG(d3c8) += D3
D2 += D0
if N(D2-D0): exchange entire D0,D2
D0 -= LIVE LONG(d3c4)
if not N(D0): LONG(d3c4) += D0
D2 -= LIVE LONG(d3c4)
if N(D2): LONG(d3c4) += D2
```

모든연산은32bitwrap이며N은결과bit31만본다. 원본BMI/BPL은N xor V를보는signed less/greater와다르다. 중간RAM쓰기뒤차이값을다시계산하는순서를보존한다.

## 19d98 — 한 시간의 경계 누적

SWAPD7,CLR.WD7로입력lowWORD를16.16시간으로옮긴뒤198ee를호출한다. D0-D3를각SWAP하고ADD.WD0,D2와ADD.WD1,D3로endpoint를만든다. signed16 D2.low<D0.low이면전체D0/D2를교환하고D3.low<D1.low이면전체D1/D3를교환한다.

D0.low가signed RAMd3f2보다작으면d3f2를갱신한다. D1은d3f6의최소,D2는d3f4의최대,D3는d3f8의최대를갱신한다. 이비교는원본BGE/BLE의N xor V규칙이며19978의N-only비교와구분한다. Exg는전체LONG이고RAM쓰기는WORD다.

## 19d08 — 현재 위치에서 두 시간의 가시 경계

초기WORD는d3f2/d3f6=7fff,d3f4/d3f8=8000이다. D0/D1=d3bc/d3c0의LONG으로19802를호출하고SWAPD7한다. D7.low를스택에WORD로보존한다.

D6.low=d418을읽고unsigned min(D6.low,d3ee)로제한한다. D7.low가D6.low보다작으면D6.low로올리고19d98을호출한다. 이어저장했던D7.low만복원한다. **현재D7.high는첫19d98/198ee의결과를보존한다.** D7.low를unsigned min(D7.low,d3f0)로제한하고19d98을다시호출한다.

마지막camera원점반영도WORD연산이다. D0.low=d3a2를d3f2에더한다. D0.low에140을더한후d3f4를더하며,**마지막ADD의signed overflow만**검사한다. Overflow면D0.low=7fff이고그값을d3f4에쓴다. 앞선+140의overflow를합쳐검사하지않는다. Y는D1.low=d3a6,d3f6에덧셈,+100,d3f8과마지막ADDoverflow검사로동일하게계산한다. 상위WORD는보존한다.

## 아직 연결되지 않은 frame 경로

전체1a73c 완료에는19832의두좌표간경로선택/192c4검사,19a40/19ac8의각축계산을포함하는19b96과1a2b4 조건판정등이추가로필요하다. 19ac8은53e2에계산결과를쓴직후같은값을빼는명령을포함하며이원본순서를추측으로수정하면안된다. 현재명시창목록은기계적해독근거이며그자체로해당frame동작분석완료를뜻하지않는다.

## 검증 상태

`step_scene_motion_bounds`는네진입을기존SceneCommandState12register와exactmotion MS5D로실행한다. 198ee와기존19938이공유하는bias전위치계산만private helper로묶었다. 기존19938의+8bias와19802의projection/selector는유지한다. 전체RAM/상태는성공시에만게시한다. Resource검증/선택한도는기존motion API와동일하며RAMmotion입력은아직runtime지원밖이다. Nullcursor는API에서resource를검사하지않는다.

원본명시10창548행/미해독0을보존했고37motion/108일반record를원본·manifest·container에대조했다. 모든현재record+4 WORD는0000이며등장type은11종이다. 이사실을전체ROM의미사용경로나다른자료까지폭0이라는주장으로확장하지않는다. Inventory SHA256 `3c1f66ceab858086ebb945049a71d6d13431377329aeb62c92ff269c488ccac8`.

신규원본3,606조건에서전체64KiBRAM·12register가C++와일치하고오류117조건에서입력/기존출력을보존했다. Canonicalresource조건880개,null조건206개,합성주소정규화조건2,504개,실제CLI승계16호출이다. 합성자료는원본CPU에서RAM106000에놓고C++에서는fixed MS5D60000으로읽는다. 두RAM에동일scratchbytes를유지하며비교시출력A1과RAMd3b4주소만정규화한다. ROM파일·에뮬레이터code는수정하지않으며이를canonical조건과합산해자연게임동작으로주장하지않는다.

모든네진입에서36type을실제로관찰했다. 40조건은CMP의signedoverflow가실제로발생하는register snapshot과분기PC를검사하여19978의N-only와19d98의signed비교를구분했다. 마지막ADD saturation은양수overflow/음수overflow/앞선ADD만overflow의6조건으로검사했다. 19d08의두198ee호출·19802호출과WORD스택복원뒤각시간선택도검사했고13조건에서두시간이서로다르다. 네bound min/max의갱신/비갱신분기를모두관찰했다.

4CLI승계sequence16호출중12호출이직전실제CLI RAM/12register를소비한다. Host는D7과phase를각호출에제공하고19d08앞에서는camera XY를설정한다. Native는호출경계에서만context/stack을설정하며callee중간reset/대체는없다. 정상RTS/A7+4와MMIO쓰기0,code불변을검사했다.

공유계산refactor후기존19938은12,170조건/오류69,19802는2,664조건/오류69를통과했다. 전체make Python182/C++114/경고0이다. 메인이core/CLI/unit/observer/verifier/inventory와신규3,606저장RAM/결과,37resource·현재report/ROM hash를확인했다.

- 신규native SHA256 `f32ba07b37962d31b86feb720d25c8c72754feef529eb7d9e82193a24077d528`.
- 신규verification SHA256 `d867cf922bba3631da01ee66a160ae9098e1d2af7677e521cf2209dd4acdc20f`.
- Bounds CLI SHA256 `41b1481bf18b1aa132601e8c8b07a6835f42140049d537b233396c0aa71bba4f`.
- 기존19938 verification SHA256 `8df14e6b25f3bdfca1e072ab8891693a240db05130685587c84bfe2ed3faa2e7`.
- 기존19802 verification SHA256 `6642a5916cfeed9c1a635f99bb633bd51579cb0bc46ec5825a123c877c1097bb`.

```text
make -j3 all test
.venv/bin/python tools/inventory_scene_frame.py
.venv/bin/python tools/observe_scene_motion_bounds.py
.venv/bin/python tools/verify_scene_motion_bounds.py
.venv/bin/python tools/verify_scene_motion.py
.venv/bin/python tools/verify_scene_motion_time.py
build/step_scene_motion_bounds ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A4 INPUT_RAM OUTPUT_RAM [MOTION_MS5D]
```

ENTRY는198ee/19978/19d98/19d08의원본주소이며CLI에서는0x접두부16진수나10진수를사용한다. 출력JSON은12register다. 전체frame/자연게임진행/직접플레이화면은미완료다.
