# 플레이어 상태 기록과 구역 재개 리뷰

Baseline `b4b94ab`. 원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 ROM CPU 주소는고정첫1MiB에서파일offset과같다. 메인은4d7a6/48180 및479ee/475ca의분기·레지스터폭·호출순서를해석했다. sol에원시조회창추출/구현/독립검증/문서를분담하고실제변경을검토했다.

## 읽기와 snapshot

4d7a6의D0.byte=0은RAMdcba/고정오브젝트100cb8,그외는dce6/100da8을선택한다. object callback270e 또는source첫word0이면기본값을반환한다. D0.low만0으로만들고D1/D2/D3/D4/D6전체0,D5전체ffffffff로한다. activecallback0도활성이다.

활성source의byte27이index이며0은원본TRAP이다. D0전체=index,D1.byte=source25,D2.byte=source26,D3.word=source1c,D5.word=source20,D6.byte=source2a로반환하고각명령이나머지bits를보존한다. D4는index×16 unsigned곱후ROM4cf64+index16+a의word를읽으므로최종상위word가0이다. 새leaf API는전체D0..D6를노출한다.

48180은D0.word&1로d694/d69c의8바이트destination을결정하고helper를호출한다. D0.byte,+3D1.byte,+2D2.byte,+4D3.word,+6D5.word,+1D6.byte순서로저장한다. 원본현재상태를저장하는동작이며복원이라고부르지않는다.

## 원시조회창

기존MS5D v1 kind1으로 `[4cf64,4df60)`4092바이트를보존한다. 모든byte index의+a word에대한주소가능창이며기존20개×16바이트논리레코드규격을확장하지않는다. 기존game_records320바이트와prefix가일치한다. 뒤의코드/데이터겹침과실제index사용여부는별도미확인이다. container4124바이트 SHA256 `aad55489c3ee994e32b0ca8301e97d546746d5735cea2f5181ec9f71d136ac45`. 이리소스는D4조회원본word를공급하며synthetic메타데이터로대체하지않는다.

## 구역의공통초기화

기존475a4초기화suffix에서475ca이후부분만내부area_suffix로분리했다. 기존진입은같은prefix후동일tail을호출한다. reset_stage_area는475ca부터47642 RTS까지수행한다. d682초기화,1bd12,callback설정과각subsystem reset순서를보존한다.

479ee..479fe는D0전체0으로첫player snapshot,전체1로두번째snapshot을호출한후475ca를수행한다. 외부계약은RAM/D0/D1/D3이며내부의다른레지스터를최종CPU값이라고노출하지않는다. snapshot에는원본에서새로쓴low값만사용되므로내부나머지레지스터초기값은최종RAM저장과이외부계약에영향을주지않는다. 모든API오류는앞서완료한첫snapshot까지rollback한다.

## 검증

메인은core와기존suffix분리를검토했다. 최종leaf원본3372조건과구역50조건,오류보존49조건이통과했다. 전체RAM과각계약의전체레지스터및A7종료위치를비교했고MMIO쓰기는0이었다. 실제CLI출력을승계한read→snapshot8시퀀스와앞선479ba player caller→원본479d0 BNE→479ee→479fe의연결2조건도통과했다. 후자는A5/A7/SR/반환stack을재초기화하지않았다. 노출하지않는D2/D4/D5/D6는native fixture임을기록했다. 보고서SHA256 `3be3c5e82d570c78096f49cdff1f34e6947a858efaf832a41af1c0c600cf97cd`.

전체make는Python118/C++94통과/경고0이다. 기존game initialization 원본회귀562조건/오류31조건/4승계시퀀스/외부읽기4회도통과했다. 보고서SHA256 `ba538ea67e01041c8b199c889d8f2a225f18b203bf55e6a281da5464af12a3b2`는이전결과와같다. 첫구역의47594사운드대기경로와479fe이후본문·일반scene script·자연scheduler는아직미완료다.
