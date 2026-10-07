# ca9e/caf0 화면 초기화

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. ROM CPU 주소와 고정 파일 오프셋이 같다. A5=108000인 호출 조건이며 RAM offset966은CPU100966이다. 메인이 ca9e/caf0/35a2 명령을 해석하고 C++/검증 구현을 sol에 맡겼다.

## 동작

ca9e는CPU3c0000에32bit로VRAM주소/값을짝지어쓴다. 주소7500..77ff에0을쓴뒤7500/7520/7540/7560에0200,7580에ff02를쓴다. 총773포트이며RAM은변경하지않는다. 최종D0=7580ff02,D1=0,D3는입력을보존한다. SWAP과MOVE.W순서때문에최종D0상위word를단순0으로만들면안된다.

caf0는ca9e후35a2를다섯번호출한다. 각호출은watchdog300001에시작주소lowbyte를쓴뒤열마다VRAM주소를32증가시키며행마다1증가시키는고정값채우기를수행한다. 종료시3c0004.word=0,3c0000.long=82000000을쓴다.

| 시작VRAM주소 | 값 | 열 | 행 |
| --- | --- | ---: | ---: |
| 7021 | 00ff | 38 | 30 |
| 701f | 7000 | 40 | 1 |
| 7000 | 7000 | 40 | 1 |
| 7000 | 7000 | 1 | 32 |
| 74e0 | 7000 | 1 | 32 |

caf0전체는2072포트를출력하고RAM966.byte를0으로만든다. 최종D0=75807500,D1=00007000,D3=00000020이다. 다른RAM은보존한다. 임의의35a2입력은API로노출하지않으며고정영역은원본의75000000이상TRAP조건에걸리지않는다.

## API와 CLI

`reset_game_screen`은entry ca9e/caf0,정확64KiB RAM,전체D0/D1/D3와포트벡터를받는다. 성공시포트벡터를교체하고실패시RAM/레지스터/포트를모두보존한다. 실제포트순서를공통VideoPortWrite로제공하며픽셀을직접그렸다고주장하지않는다. 기존control_menu_start안의ca9e포트생성과같은원본동작이지만이번에는그경로를수정하지않았다.

```sh
make build/reset_game_screen build/game_screen_reset_test
build/reset_game_screen ENTRY D0 D1 D3 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS
.venv/bin/python tools/verify_game_screen_reset.py
```

포트파일은기존9byte(size1+BE32address+BE32value)형식이다. CLI숫자는unsigned32,입력/출력alias를거부한다. 검증오류는기존출력파일을보존한다.

## 검증 범위

원본ca9e/caf0를RTS까지실행하며실제35a2호출5회를확인한다. 전체RAM/fullD0D1D3와순서있는포트의폭·주소·값을비교한다. 일반35a2/TRAP/다른레지스터/CCR/stack동등성/렌더링픽셀/물리시간은검증범위밖이다. 이함수의호출자c610과의자연연결은다음작업이다.


최종 검증은104조건(각entry52회)/오류23조건이며전체147940포트가일치했다. 보고서 `artifacts/game_screen_reset/verification.json` SHA256 `328476653aa7648ceb08c18ea78a72b77425e09dc2591ef520c38d46e9a0227a`. 원본불변을확인했다. 전체빌드·Python88개·C++전체검사는제거묶음과함께통과했다.
