# 초기화 콜백의 팔레트 대기·IRQ 해제 리뷰

Baseline `9d7c840`. 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인이c52a/c560 및8b64/4718의 전체D0 동작을 원본에서 확인했다. sol에 코어·CLI·단위 검사, 원본 및IRQ 비교, 다음 구간 목록화를 분담하고 메인이 결과 전체를 검토했다.

## 구현과 판단

GameStartupState는PC/object RAM offset/전체D0D1D3를 유지한다. c52a는 필드 초기화와fill 설정을 수행하고c560 대기는live counter를 읽기만 한다. counter0이면공유e7bf4 helper→D0=0 난수초기화→RAMf004=3을 실행하고c584에서 멈춘다. 다음47570의 미복원 동작을 성공 처리하거나 생략하지 않는다.

8b64의ANDI.Wffff는상위word를 지우지 않는다. LSL.L5와 이후word 명령의 차이를 반영했다. 기존 palette-fill 분석 문서의 부정확한 '16비트 마스크' 설명도 수정했다. 초기화와 대기는 동일 함수를 사용하되 초기화 포트를 반복하지 않는다. 전체 호출은후속helper 실패까지 RAM/state/포트를롤백한다. C++는 사용 시 리소스를검증하고 CLI는입력파일 두개를먼저로드한다.

initialize_main_palettes는기존private helper의행동을바꾸지않고public으로공개했다. 고정 팔레트 리소스와 난수 API를 실제후속호출에 연결한다. 추가runtime 형식은 만들지 않았다.

## 검증

`make -j3 all test` session67271 exit0. Python81개와C++전체통과,경고없음. 로그 `artifacts/game_startup_build_test.log`. 새단위검사는필드보존,재폴링무변경,전체D0shift,seed승계및latefailure rollback을확인한다.

원본 verifier session75275 exit0: 103경계(대기91/c584 12), 시작포트260개, 오류32조건. 여덟시퀀스는실제native/CLI IRQ16회를사이에실행하여포트16,456개와RAM/양bank/display를비교했다. 전체119호출/16,716포트다. 호스트는fixture뒤counter를쓰지않고render gate만명시적으로활성화한다. 비활성IRQ8회에서는대기가유지되고활성IRQ8회에서counter0이되어초기화가이어진다.

보고서 SHA256 `de8e6e4ca5ddd97c691e22d34e94c087fbfd950d635f62b203cd8cbd3c61a240`. 메인이최종보고서집계·해시를확인했다. 비교코드는원본과현재bank불변을검사한다. main context복원과재호출stack설정은호스트가하며자연IRQ/BIOS/SR/RTE/시간축을검증했다는뜻은아니다.

## 다음 작업 근거

`inventory_game_initialization.py`는47570..47642의210바이트에서직접호출23개/22대상을목록화했다. 비호출분기0개이지만대상내부의중단·반환은미해석일수있다. 보고서SHA256 `0a034a5f67e218ba7602192ccf0132f2d69416dd4e58164e9c098ea584aa288f`는이시점문서/코드참조snapshot이다. 메인이도구및원본명령을검토하고여러짧은helper와첫사운드호출을직접분석했다.

다음은47570접두부와word명령0720/byte명령08·20의큐대기연결이다. 그후의여러초기화helper,callback분기및전체게임은남아있다. 분석근거는 `docs/analysis/game-startup.md`에기록했다.
