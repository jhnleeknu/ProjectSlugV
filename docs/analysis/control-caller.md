# 컨트롤러 반환값을 사용하는 호출자

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 CPU 주소는 복호화 프로그램의 파일 오프셋과 같다. 진입f54는9136을 호출하고, f5a부터 반환값을 소비한다. 아래 분석은 원본 코드 실행과 명령 근거다. 후속 C++ 구현은f5a 이후를 연결하며, f54의9136 호출부터 포함한 통합과ec4 루프 실행은 아직 분리되어 있다.

## 상태 전환과 표시 효과

f5a는 object(A6)+84의 이전 상태 byte를D1로 읽고, f5e는 반환D0의 하위 byte를+84에 저장한다. 상위24비트는 분기 판단에 영향을 주지 않는다.

| 새 상태 byte | 이전 상태 byte | 실제 처리 |
| --- | --- | --- |
| 0 | 0 | 5728 효과 갱신 후ec4로 이동 |
| 0 | 1 | 3db2 조회 결과를object+82에 저장,3d7e(0),효과 저장,(-4,-4,-4,4) 설정,5728 갱신 후ec4 |
| 0 | 그 외 비영 | 조회 결과 저장,3d7e(0),5728 갱신 후ec4 |
| 비영 | 0 | object+82를3d7e로 복구;object+80이 비영이면 효과 복구 후+80=0;카운터 검사 |
| 비영 | 비영 | 카운터 검사 |

효과 저장 경로는8bbc(0)으로7dec를0으로 만들고8bc8로7dc2..7dd5의20바이트를7dd6..7de9에 복사한다. object+80을ff로 설정하고8c16(-4,-4,-4,4)를 호출한다. 이어5728을 즉시 호출하므로 일반적인 이 입력에서는 타이머4를 설정한 같은 호출 안에서3으로 감소한다. 효과 저장/복구와 설정·갱신을 기존 C++ API로 복원했고, 아래 consume_control_result에서 이 호출자의 순서로 연결했다.

3db2는4d91 bit3이 켜져 있으면0, 꺼져 있으면4d90 byte+1을 반환한다. byte255는 word256이 된다.3d7e는 입력word에서1을 빼고 borrow 여부로 분기한다. 입력0이면4d90=0 및4d91 bit3 설정, 그 외에는 감소 결과의 하위byte를4d90에 쓰고bit3을 지운다. 이어4d90/91 word를 포트3c0006에 쓴다. 이 문서는 명령 수준의 shadow/포트 동작을 기록하며 장치 타이밍까지 구현한 것으로 취급하지 않는다.

## 진행 카운터와 좌표 갱신 단계

비영 반환 경로의fe2는 object+7e word와RAM10000e word를 비교한다. 불일치하면fee의trap15로 간다. 같으면16비트로1을 더해 두 위치에 저장한다. ffa에서43dbc를 호출한다. 이 helper는RAM10d494 byte를 `(old & 1) + 1`로 바꾸므로 결과1/2가 번갈아 나온다. 기존 좌표 갱신 API가 이 byte를 읽는다. 반환0인 경로는 이 카운터 검사와 단계 갱신을 건너뛰고ec4로 간다. 따라서 컨트롤러 한 호출을 무조건 게임 진행 한 번으로 세면 원본 순서와 달라진다.

주변f30..f52에는object+76의 간접콜백을 object+7a를A6로 하여 실행하는 별도 분기가 있다. 이 분기는5728 호출 후f12로 돌아간다. 이 경로와ec4 루프의 자연 진입·장치 동기화는 다음 분석 범위다.

## 원본 실행 근거와 한계

```
.venv/bin/python tools/analyze_control_caller.py
```

원본f5a부터512조건을 실행했다. 새 상태0/1/2/ff, 이전 상태0/1/2/ff, 복구 플래그0/ff, video bit3, 카운터0/ffff와 불일치 여부, 저장 효과 타이머0/4를 조합했다. D0 상위24비트는비영으로 두었다. 실제 helper를 그대로 실행하고ec4 또는trap15 명령 직전에 멈추거나 정상rts까지 진행했다. 결과는ec4 루프128조건, trap 경계192조건, 정상 반환192조건이다.

실제 helper 호출 순서, 상태 byte, video shadow/포트, 효과 저장/복구와 목표/첫 tick, 카운터 비교·wrap, 단계byte를 명시적으로 검사했다. 원본mapped1MiB 불변도 확인했다. 팔레트 준비는7ded bit7의 원본 gate로 연기했다. RAM 전체 해시는 관측 기록이며 독립적인 전체RAM 모델 비교가 아니다. 모든 CPU 상태,trap handler,ec4 이후 루프,실제 입력/부팅/하드웨어 타이밍은 미검증이다.

보고서 `artifacts/control_caller/analysis.json` SHA256: `33eb12994474a8dd3ea8ab035be5e35dc83bbb5c6400e1585b18471509a1d120`.


## C++ 비디오 제어 shadow와 포트

```
build/video_control INPUT_RAM OUTPUT_RAM OUTPUT_PORTS VALUE
.venv/bin/python tools/verify_video_control.py
```

`query_video_control`과 `set_video_control`을3db2/3d7e에 대응하여 추가했다. 조회는 RAM shadow를 읽으며 하드웨어 포트를 읽지 않는다. 설정 입력은 임의의16비트 word다. 예를 들어256을 설정하면 조회값256,257을 설정하면 조회값1,ffff를 설정하면 조회값255다. 입력을256으로 제한하거나 clamp하면 원본과 달라진다. 입력0은bit3을 설정하고 나머지 입력은bit3을 지운다. 다른low-byte bit는 보존한다.

설정은3c0006에word쓰기 한 번을 출력한다. API는 새 포트 목록의 메모리를 확보한 다음 RAM 두 byte와 출력을 함께 확정한다. 잘못된 RAM 크기나 할당 실패는 RAM과 포트 목록을 보존한다. 출력 포트를 실제 하드웨어나 렌더링 호스트에 적용하는 것은 별도 계층의 역할이다.

`--batch`는 대량 비교용 진단 형식이다. stdin의4바이트 record는BE16 초기shadow와BE16 설정값이며, stdout의15바이트 record는BE16 조회전/조회후/최종shadow 및9바이트 포트 기록이다. 게임 리소스 규격을 추가한 것이 아니다. 정상 CLI는 전체64KiB 입력/출력 RAM과 기존9바이트 포트 형식을 사용한다.

## ec4 대기 루프의 후속 분석 경계

원본ec4는10f000 bit0과object+84에 따라3a70의 진단 텍스트 출력을 거친다. ef2..efa는RAM100016 byte가100017 byte 이상이 될 때까지 unsigned 비교로 기다린다. efc는3c0006을word 읽고7비트 shift 후100을 뺀다. borrow가 있으면0으로 만든 뒤하위byte를100018에 쓴다. 이 포트의 읽기 결과를 위의 쓰기 shadow와 같은 값으로 간주하면 안 된다.

f12는100016을10001a에 복사하고100016과104ca2 word를0으로 만든 뒤31d6과b68을 호출한다. 이후object+76이0이면f54의 컨트롤러로 간다. 비영이면 간접콜백·5728 실행 후100016의 비영 값을 기다리고f12로 돌아간다. 현재 이 루프의 동기화 신호를 생산하는 인터럽트와 실제 입력 수집을 연결하지 않았으므로 호스트 쪽 대기를 임의로 제거하거나 한 번의 호출을 한 프레임으로 취급하지 않는다.


비디오 제어 검증은 모든16비트 설정 입력65,536개와, 모든shadow65,536개에 경계 설정값을 순환 적용한 배치131,072건이 통과했다. 이는 모든 입력×shadow의 Cartesian 조합을 검사했다는 뜻은 아니다. 별도 원본 조회 sweep65,536건에서 D0 전체 결과와 RAM/포트 불변을 확인했다. C++ 배치는 조회전/조회후 값, 최종shadow와 단일 포트를 비교하고, 별도 CLI194조건은 서로 다른 초기64KiB RAM 전체와 포트를 비교했다. 원본setter 입력D0의 상위word도 비영으로 두었다. setter가 반환하는 기타 레지스터/flags는 API 범위 밖이다.

원본mapped1MiB 불변과 전체 `make all test`(Python61개/C++ 전체)가 통과했다. 단위 검사는 조회256,설정257/ffff의 하위byte wrap,다른RAM 보존과잘못된 크기에서 출력 보존을 포함한다. 보고서 `artifacts/video_control/verification.json` SHA256: `10f00ea2352dd0b6354521e436b79b386c58b279e14415dfdd3ec99b5989654c`.


## C++ 진행 카운터와 단계 전환

```
build/advance_control_counter INPUT_RAM OUTPUT_RAM OBJECT_ADDRESS
.venv/bin/python tools/verify_control_counter.py
```

`advance_control_counter`는fe2에서1000까지의 RAM 효과와trap 경계를 구현한다. object+7e word와RAM000e가 다르면 `trap15=true`로 성공 반환하며 RAM을 바꾸지 않는다. 이 결과는 지원하지 않는 입력 오류와 구분하며, 원본fee의trap 명령을 실행한 것으로 간주하지 않는다. 값이 같으면 global word, object word 순서로16비트 증가값을 쓰고,43dbc의RAMd494 갱신을 마지막에 수행한다.

OBJECT_ADDRESS는100000..10ff80 사이의짝수CPU주소이며끝의0x80바이트span이RAM에포함되어야한다. 검증에서 사용한 임의 주소가 실제 게임에서 객체로 도달한다는 주장은 하지 않는다. 특히10d416이면object+7e가d494를가리킨다.00ff를증가시켜0100을쓴후phase연산으로상위byte가02가되어object counter는0200,global counter는0100이된다. 이를정규화하지않으며다음호출의trap도원본대로관찰했다.

1,734조건(독립1,716 및RAM승계18회)에서전체64KiB RAM과종료경계가일치했다. 실제fee 경계863회와43dbc 호출871회를hook으로확인했다. 모든256개초기phase,word0/1/7fff/8000/ffff,최저·최고object주소와phase중첩을포함한다. 오류주소·RAM크기·입출력직접/하드링크/심볼릭링크별칭25조건은출력을보존했다. 영상/watchdog포트출력이없고원본mapped1MiB가불변임을확인했다.

전체 `make all test`(Python61개/C++전체)통과. 보고서 `artifacts/control_counter/verification.json` SHA256: `7deacddda16f7717b17b375b421d65bd346239381bdd4b768d5f0d5f3e92dbf5`. 다른CPU레지스터/flags,trap handler와실제게임동기화는API범위밖이다. 다음연결작업은f5a의상태소비와팔레트효과·비디오제어·이카운터API를원본순서로호출하는것이다.


## 반환값 소비·비디오·팔레트·카운터의 C++ 연결

```
build/consume_control INPUT_RAM PALETTES_MS5P OUTPUT_RAM OUTPUT_PORTS OBJECT_ADDRESS CONTROL_D0
.venv/bin/python tools/verify_control_caller.py
```

`consume_control_result`는9136이반환한뒤의f5a부터실행한다. RAM과입력CONTROL_D0는반환직후상태다. 상태의하위byte를object+84에기록한뒤이전byte와조합하여video조회/설정,효과저장·설정·갱신또는복구,카운터검사를원본순서대로호출한다. 팔레트준비는실제MS5P를사용한다. OBJECT_ADDRESS는짝수100000..10ff7a이며0x85byte전체가RAM안에있어야한다.

결과 `next_pc`는0xec4(대기루프경계),0xfee(trap15명령직전),0(정상rts)이다. 경계뒤코드는실행하지않는다. trap은원본에서실제로도달한성공결과이므로그전에변경한상태byte·비디오/효과복구와포트를유지한다. 지원하지않는팔레트ID같은호스트오류는그이전변경까지전체트랜잭션으로취소한다. 두경우를같은실패처리로묶지않는다.

팔레트프레임 API에선택적포트출력을추가했다. 색상상위byte가변한경우 `(old_red-new_red) OR (old_green-new_green) OR (old_blue-new_blue)`의각차를byte로계산한값을watchdog300001에256회쓴다. 이값은단순boolean이아니다. 준비를실행하면2ffff2에1000,2ffff0에0을쓴뒤팔레트준비를하고같은쌍을다시쓴다. 출력목록은watchdog→두쌍의bank word순서이며준비gate가켜져있으면bank쓰기는없다. RAM갱신도기존과같이보존한다. 장치의시간축과RAM/포트간세부관측타이밍은모델밖이다.

원본f5a의276조건(독립256 및RAM승계20)에서전체64KiB RAM,루프/return/trap경계와16,108개의순서있는video/watchdog/PVC쓰기가일치했다. 실제도달수는video query54/set108,효과저장/설정20,효과복구32,팔레트프레임74/준비32,카운터phase102,ec4루프74와fee경계100이다. 별도5728의140조건도전체RAM과18,712개의포트가일치했다. timer/gate,일반/혼합palette,효과우회와word경계를포함한다.

잘못된palette ID로인한늦은실패2조건은출력파일을보존했다. 단위검사는video조회후효과저장·첫tick·포트순서,복구후진행,trap시앞선변경확정,지원오류시모든출력rollback을검사한다. 원본고정ROM과PVC영역을제외한팔레트ROM뱅크불변을확인했다. 보고서 `artifacts/control_caller/verification.json` SHA256: `7e2cc2b35b657d8baf55358b3f3b0ff837742364e06d022584ef8bdd560e427a`.

남은연결은f54의실제9136호출과이소비API를단일실행으로묶는것이다. 이때9136진입스택은f54진입보다4작다. ec4의입력·인터럽트대기,trap handler,전체CPU레지스터/flags,픽셀·사운드·게임부팅은여전히미완료다.


## f54 단일 진입 통합

```
build/step_control_caller INPUT_RAM MENU_MS5D PAUSE_MS5D PALETTES_MS5P OUTPUT_RAM OUTPUT_PORTS OBJECT_ADDRESS STYLE LINE ENTRY_STACK [FONT [STAGES_DIR]]
.venv/bin/python tools/verify_control_caller_step.py
```

`step_control_caller`는 원본f54부터 실행하는 C++ API다.9136에는 진입 스택보다4 작은 주소를 전달하고, 반환 후의 RAM과D0를 f5a 소비 함수에 연결한다. 메뉴와 팔레트는 기존MS5D/MS5P를 직접 읽는다. BIOS 외부 전환이면 소비 함수를 실행하지 않는다. `next_pc`는 정상반환0,ec4 루프,fee trap직전,c00444 BIOS 경계 중 하나다. 모든 지원 오류는9136이 수행한 변경까지 취소한다.

OBJECT_ADDRESS는 기존 소비 API 범위이며, ENTRY_STACK은짝수110108..fffffc다. STYLE/LINE은f54진입D1/D3 word이며, 이미 열린 메뉴에 들어갈 때A1은전역renderer와같다는기존계약을유지한다. 이 API는 모든 CPU레지스터의 반환상태를 제공하지 않는다.

원본f54와410조건(독립281 + 출력RAM승계129)에서전체64KiB RAM,모든순서있는하드웨어쓰기104,487회와경계가일치했다. 두연속시퀀스는활성화·누름반복·메뉴/area/group조작·전체종료·진행·재활성화·두번째종료까지수행한다. 호스트가입력byte를공급하며ec4의실제입력수집루프는실행하지않는다.

실제f5a도달409회에서A6가진입호출자객체주소이고A7이진입스택으로복구됨을확인했다. rootrow4의950c 정적재시작도포함한다. row5의9532 BIOS전환은f5a를건너뛴다. stage callback의실제스택깊이12/16/32byte는f54의바깥JSR4byte를포함한다. 늦은팔레트실패2조건은이미메뉴가초기화된뒤발생하며모든출력파일을보존한다.

전체 `make all test`(Python61개/C++전체),CLI숫자·별칭검사가통과했다. 보고서 `artifacts/control_caller_step/verification.json` SHA256: `dde81aaccb38533008098a252dcc09c0a9ba1db25306169004b6df691c509c24`. 전체게임부팅·입력/인터럽트시간축·예외handler·외부스택메모리와모든CPU레지스터/flags는미완료다.

## 입력 수집과 대기 신호의 다음 연결 근거

31d6은380000을byte읽고반전한하위4bit를RAM4cb4에저장한다. 기존값과의XOR/AND로새로눌린bit를4cb5에쓴다.31f2는300000,3242는340000,32a4는300000을읽는다. 입력처리는349a까지의분기와349c/352a helper를포함하므로처음의포트읽기만으로완료라하지않는다. b68은10fdaf를100012에복사하고fdb6부터의값과b58테이블을이용해f006/f007을갱신한다.

ROMvector64의값은20c이며,그진입의조건부경로에서23c가c8c를호출한다. c8c는100019 bit7로재진입을검사하고100016을byte증가한다. overflow는ff로되돌려포화시키며,overflow가없을때300001 watchdog쓰기가있다. d4e는100019를0으로만든다. 메인이vector/call바이트와c8c의완전명령을재확인했다. 이연결은인터럽트호출경로근거이며실제발생주기·게임의자연도달성은아직미검증이다.

## f5a 종료의 D1/D3 문맥

`consume_control_result`에선택적32비트D1/D3입출력을추가했다. 입력은9136에서돌아온직후의레지스터이며이전프레임의입력style/line과동일하다고가정하지않는다. 성공시에만갱신하고실패시RAM/포트/경계와함께보존한다.

f5a는이전object+84.byte를D1.lowbyte에읽는다. status0이면서이전상태1이면MOVEQ로D1=-4,D3=4를설정하고8c16을실행한다. 세current색word와fc00target의차이를word로계산하며,모두0이면D1=ffff0000,D3=0이다. 하나라도다르면signed middle delta를4로나누어D1.highword에signed나머지,D1.lowword에몫을남기고D3=4가된다. C++의signed division/remainder와명시적16비트변환으로이형식을재현한다.

그뒤5728은타이머와팔레트변환에따라D1/D3를추가로바꾼다. 기존D1반환에D3반환을더했다. 직접복사와효과만적용하는helper는D3를유지한다. 혼합4c40/504c는마지막색15의최종low채널0..31을D3.lowword에남기며상위word는유지한다. 효과와혼합이모두있으면효과적용후채널이다.

status!=0/이전상태0에서효과복구8be0을실행하면복구전RAM107dc4.byte를D1.lowbyte에읽는다. 타이머복구가0이든아니든이레지스터읽기는발생한다. 나머지비디오조회/설정·counter경로는D1/D3를더바꾸지않는다.

```sh
build/consume_control --registers D1 D3 INPUT_RAM PALETTES_MS5P OUTPUT_RAM OUTPUT_PORTS OBJECT_ADDRESS CONTROL_D0
```

옵션이있으면JSON에d1/d3를추가하고기존호출의JSON은유지한다. 이계약은f5a이후tail이며9136자체의최종레지스터복원은후속작업이다.

`.venv/bin/python tools/verify_control_caller_registers.py`는원본322조건,시간순포트27,858개,출력보존오류14조건을통과했다.
전체RAM/32비트D1/D3를비교했고네가지팔레트helper진입을관찰했다. DIVS의음수나머지및all-fc00변화없음사례,실제MS5P,원본코드불변과주소alias순서를포함한다. 연속사례는RAM을이어받지만D1/D3입력은독립fixture임을명시했다.

보고서: `artifacts/control_caller_registers/verification.json`.
SHA256: `8b636bf7b93621d7b7787618b630ad6c4fd8b189961da7ed9d26a31209511960`.
