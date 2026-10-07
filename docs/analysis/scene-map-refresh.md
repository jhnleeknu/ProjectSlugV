# 장면 맵 갱신과 반복 경계 처리

Canonical decrypted source SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 코드의 CPU주소와ROM offset은같다. 메인이 `artifacts/scene_paths/disassembly.json`의16f0e..16f9a,1861a..1879c를원본bytes와함께읽었다. 아래는명령흐름의해석이며원본실행/C++대조결과는별도로기록한다.

## 16f0e 열 제어

A2=node+36 LONG,A1=node+2e LONG을처음한번읽는다. D6.low=D2.low-1로시작해DBRA로반복한다. 입력D2.low0은65536회이며각반복에서descriptor+4의width를LIVE조회한다. unsigned D0.low>=width면그열은쓰지않는다. 쓴다면A3=node+3a+2*(D4.low&31)이다.

- A2=0이면A3에WORD0021을쓴다.
- A2=ffffffff이면A3의상위byte만0으로쓰고A3+1은남긴다.
- 그외에는A2의timeWORD가0이아니고unsigned D0<time이면A2-=4로뒤로탐색한다. 다음record WORD가음수이거나D0보다크면앞으로탐색을끝낸다. 그렇지않으면A2+=4로진행한다.
- 선택record+3 byte를D7.byte로읽고A3+1에쓴다. 그뒤node+35 byte를D7.byte로읽고record+2 byte를빼고1을더해LSL.B3한다음A3에쓴다. WORD/상위register부분을임의로지우지않는다. A4는마지막다음record주소다.

각반복은D0/D4 WORD를1씩증가시키며DBRA가끝나면SUB.W D2로되돌린다. D6.low는ffff가되고highWORD는보존된다. 마지막A2는node+36에LONG으로게시한다. Data read와앞선RAMwrite가겹치면이순서를유지한다. 이코드는미리모든record를캐시해배열인덱스로치환하는해석과다르다.

Canonical72path의column pointer는모두0이다. Nonnull과ffffffff경로는코드에있지만canonical사용사실을주장하지않으며합성RAM record로별도검증한다. 확인되지않은column자료를임의추출하거나새리소스규격을만들지않는다.

## 18702 반복 맵 경계

Node+7a bit3은x,bit4는y처리를선택한다. 켜진축에서coordinate.low>=descriptor dimension의unsigned조건일때만AND.Lffff→DIVU.W dimension→SWAP을수행한다. 결과는highWORD=quotient,lowWORD=remainder다. 음수처럼보이는WORDffff도65535로계산하며signed modulo로바꾸지않는다. Divisor0의원본예외는API오류와구분해기록한다.

16f0e를호출한뒤D0..D5를MOVEM.W로저장하고183c6을호출한후sign-extended32bit로복원한다. Bit4가켜져있으면D1.low에서LIVE height를뺀추가전송을하고다시복원한다. Bit3이꺼졌으면복귀한다.

Bit3이켜져있으면D0.low에서LIVE width를빼고16f0e를다시호출한다. 저장→183c6→sign-extended복원을수행한후LIVE bit4가켜져있으면D1.low에서height를빼고마지막183c6을호출한다. **이마지막호출뒤에는D0..D5복원이없다.** Flag와dimension은helper뒤에다시읽는다. 전체는최대4개사각형이며작은맵을임의의추가반복으로채우지않는다. 각전송의port목록을원본순서대로이어야한다.

## 1861a 전체 창 갱신

A1=node+2e가0이면그대로복귀한다. D4.low=ASR.W4(ffa0-node14),D5.low=ASR.W4(027f-node18). D0.low=D4.low-node32,D1.low=-(D5.low-node34),D2.low=D3.low=32로만들고18702를호출한다. Word상수·wrap·산술오른쪽시프트가원본기준이며부동소수좌표로변환하지않는다.

## 18656 이동분 갱신

A1=node+2e가0이면복귀한다. LIVE node7a bit1이켜져있으면currentX=node14와oldX=node1c를각ASR.W4한차이를D2.low로계산한다. 차이0이면x전송을건너뛴다. 그외D4는MOVEQfa로전체fffffffa가된뒤oldTileX와delta를WORD로뺀다. Delta가음수면D4+=32,D4+=delta후delta를NEG.W한다. D5.low=0027-ASR.W4(node18),D3=MOVEQ32다. Node32/34를빼고y를NEG.W하여18702를호출한다.

그뒤LIVE bit2가켜져있으면currentY=node18,oldY=node20을ASR.W4한차이를D3.low로계산한다. 차이0이면복귀한다. D5=MOVEQ7에서oldTileY를빼고delta가음수면delta를NEG.W한뒤D5+=32,D5+=delta한다. D4.low=fffa-ASR.W4(node14),D2=MOVEQ32다. 같은origin변환후18702를호출한다. X전송의helper결과뒤에y관련RAM과flags를읽는다.

## 아직 남은 연결

이네helper는19e64 path handler에서사용되는맵표시의하위루틴이다. 전체1a7a8,일반1a5a4,47a94이후stage진입과자연frame·직접플레이가능화면의완료는별도이며현재미완료다.

## C++ 사용 계약

`scene_map_refresh.h`는기존13register SceneMapTransferState와MS5D창목록을사용하는4개API를제공한다: update_scene_columns,transfer_wrapped_scene_map,refresh_scene_map,refresh_moved_scene_map. 모두RAM/상태/orderedports를호출전체성공시에만게시한다. 내부183c6이여러번실행되면각port목록을순서대로붙이며뒤의실패는앞선RAM변경까지되돌린다. Column-only호출은ports가빈목록이다. Full CCR/stack의재현API는아니다.

진입bank2,A5=108000,정렬된A0 RAM주소와64KiB RAM을전제로한다. 실제읽기마다같은fixed/bank2/bank3 주소규칙과범위를검사한다. 18702의입력A1은초기DIVU검사에쓰이며16f0e호출후node2e에서재로드된다. 두descriptor가같다는가정을추가하지않는다. Descriptor NULL bypass는1861a/18656에만있다.

Column record탐색에는누적1048576번의임시이동한계가있고그밖의원본실행은API오류로처리한다. 하위183c6의각1048576cell한계도상속한다. 이한계의완전성은전체목표의해결항목이며임의축소한최종완료기준이아니다. Divisor0·없는resource·잘못된RAM접근도명시API오류다.

```text
make -j3 all test
.venv/bin/python tools/observe_scene_map_refresh.py
.venv/bin/python tools/observe_scene_map_refresh.py --extra
.venv/bin/python tools/verify_scene_map_refresh.py
build/refresh_scene_map ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS extracted/runtime/scene_maps extracted/runtime/scene_secondary
```

ENTRY는0x16f0e/0x18702/0x1861a/0x18656중하나다. 숫자는unsigned decimal또는0xhex다. CLI는sorted MS5D파일을미리읽고manifest를해석하지않는다. 출력은RAM65536bytes,기존9byte포트레코드,stdout JSON(entry/13regs/writes)이다. 입력·출력·리소스파일alias는거부하며이명령을스테이지화면실행명령으로취급하지않는다.

## 원본 대조 결과

1744조건(18702:1322,1861a:18,18656:282,16f0e:122)이원본RTS로복귀했고C++의전체RAM/13register/23636orderedports가일치했다. CLI오류35조건도입출력보존을통과했다. 기본1734조건에비power-of-two height DIVU4개와선행A1≠node2e6개를추가했다. 최종검증은전체1744조건을다시실행한결과이며검증결과재사용에의존하지않는다.

원본관찰 SHA256은 `867c7a7a892dc130c5fc37c91a407f75a85e307cf527e747e72abd3cdfa8073b`,C++비교는 `2ec30f6b5727a14a977d3d1d525a5a1c02d253580749d134790dc4bd7ba45944`,binary는 `4f12a22cb671a3925fab9e8f2877f70ae7676bfaa27bf937c2234a572ebf982e`다. Full make에서C++105/당시Python162/경고0을확인했다. 기존183c6 비교492조건도통과했다.

원본의각독립호출전에만baseline context를복원한다. Columns/wrapping/copy내부에서는재설정하지않는다. 모든값은명시fixture이고자연게임streaming이나연속CLI호출승계검증은아니다. Nonnull column은합성RAMrecords,secondary ffffffff는이번원본대조범위밖이다.

증분도구는이전자료를재사용하기전에동일binary/resources와nativeprefix전체해시·행수·case별결과를확인한다. Observer의--extra는기본fixture가정확히일치해야하며중복추가를거부한다. 재생성은위의기본관찰→extra관찰→전체C++비교명령을권장한다. 초기A1미설정fixture실패는 `artifacts/scene_map_refresh/invalid_a1_fixture_observation.json`에남겼으며최종결과와섞지않는다.

증분guard의재현가능한합성8개를추가한후전체Python170tests가통과했다. `.venv/bin/python -m unittest discover -s tools/tests`로실행한다. 이메타데이터검사를추가native실행조건으로계산하지않는다.
