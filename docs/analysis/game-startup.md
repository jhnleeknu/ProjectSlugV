# 두 번째 초기 노드의 팔레트 대기와 후속 초기화

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 CPU 주소는 고정 ROM 파일 오프셋과 같다. 초기 오브젝트 테이블268a의 두 번째 노드1008e4는 callback c52a를 가진다. 이 테이블 근거와 자연 부팅의 실행 관측은 구분한다.

## c52a와 c560

c52a는9056으로 RAM7def.byte=ff를 쓴다. object+76/78/7a/7c/7e의word와80/81/83의byte를0으로 한다. +82와+84는 보존한다. D0.low=0 뒤8b64로 별도 fill 카탈로그의selector0을 설정한다. PVC2ffff2=1000/2ffff0=0을 앞뒤로 출력하며 RAM7dea.word=2000과RAM10.word=0을 만든다. object의callback을c560으로 바꾼다.

8b64의 ANDI.W #ffff는 상위word를 지우지 않는다. LSL.L #5 뒤4718은D0의 하위word만 바꾸므로 c560의 counter 조회까지 실행한 D0는 `((incoming_D0 & ffff0000) << 5) | 2000`이다. D1과D3는 초기 fill 설정에서 보존된다.

c560은 live RAM7dea.word를D0.low로 읽는다. nonzero면RTS로 돌아가며, 다음 호출에서도c560을 실행한다. 초기 필드 지우기나 fill 설정은 반복하지 않는다.0이면c56e에서 기존e7bf4의 고정 팔레트 해제·등록·혼합을 실행하고, D0=0으로49a1a 난수 초기화를 호출한다. RAMf004.byte=3을 쓴 다음c584에서47570 호출 직전에 현재 API가 반환한다. c584를 완료된 게임 초기화로 취급하지 않는다.

## C++와 실행 계약

`step_game_startup`은 next_pc/object_offset/전체D0D1D3를 GameStartupState로 받는다. PC는c52a 또는c560이며 출력은 대기c560 또는 후속 경계c584다. object는짝수 RAM offset이며0x84바이트가 필요하다. A5=108000을 전제한다. 실패는 RAM/state/포트 전체를 보존한다. 대기 자체는 리소스를 읽지 않으며 C++는 사용되는 단계에서만 리소스를 검증한다.

```
build/step_game_startup PC OBJECT_RAM_OFFSET D0 D1 D3 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS FILL.ms5p BINDINGS.ms5d
```

CLI는 두 파일을 먼저 로드한다. FILL은 `extracted/runtime/palette_fill.ms5p`, BINDINGS는 `extracted/runtime/main_startup.ms5d`다. 일반 팔레트 카탈로그를 fill 파일로 대신하지 않는다. JSON은 next_pc/d0/d1/d3/writes이며 포트 파일은 기존9바이트 size/address/value 형식이다. 공유 `initialize_main_palettes`는 이번에 public API로 공개했다. 이 helper의 최종D0는60이고D1.low는1이며 상위word를 보존한다. main startup wrapper는 그 뒤D0를0으로 바꾼다.

## 실제 IRQ 대기 해제

c8c의 rendering branch는 기존 특수 팔레트 전송으로 bank1 전체를 채우고counter를0으로 만든다. rendering이 비활성이면counter는2000으로 남는다. 검증은 초기 fixture 이후 counter를 호스트가 변경하지 않고, 실제 IRQ의 RAM/bank 반환을c560에 넘긴다. 비활성 서비스와 재대기 뒤render1b.bit7만 호스트가 켜는 조건을 명시한다. IRQ 앞뒤 context 복원과 callback 재호출 stack 설정은 호스트 책임이며 BIOS/SR/RTE·시간축 구현을 주장하지 않는다.

## 다음 경계47570

`tools/inventory_game_initialization.py`는47570부터47640 RTS까지210바이트를 원본 그대로 디코딩한다. 이 주 구간은23직접호출/22대상이며 비호출 분기가 없다. 호출 대상 내부의 분기·대기·다른 반환까지 해결됐다는 뜻은 아니다. 보고서는 각 대상의 최대64바이트 후보 디코딩과 문서·코드 주소 참조를 보존한다. 텍스트 참조를 구현 완료로 세지 않는다.

메인이 추가 확인한 다음 작업의 근거:

- 4757c의100e는RAM000e/089e word를0으로 한다.4755e는D0=0,1로e62ec를 각각 호출하여RAMde14/de1c long을0으로 한다.
- 4823a는D0.word가19이상이면D0=0으로 만들고RAMd680.byte에 넣으며d681.byte=0으로 한다. 이 호출자는D0=0이다.
- e8a1c는A0=0이면원본e89e4 포인터를 선택해RAMde26에 쓰고de2e=ff/de2f=0을 쓴다. 이 포인터가 가리키는 데이터는 별도 분석 대상이다.
- 47598의3af8은word명령0720을 enqueue하고,4759e의3d3a는RAM4d7e.byte를0으로 한 뒤byte명령08,20을 enqueue한다. 각각 사운드 큐의 소비 대기로 중단될 수 있으므로 일괄 성공으로 가정할 수 없다.
- 후속481de는4d81c를 통해4cf64의16바이트 레코드를 조회한다.4d81c의D1.word<20 조건 및 각 반환 레지스터의 폭을 보존해야 한다. 현재 호출자는D1=0이다. 레코드의 게임상 이름은 아직 확정하지 않았다.

47570 전체 구현, callback 이후 분기, 스테이지·전투 로직은 남아 있다.

## 검증 결과

`tools/verify_game_startup.py`는103경계(대기91/ready c584 12), 시작 포트260개 및 오류32조건을 통과했다. 명시적인 D0 상위word 경계0001/07ff/0800에서 각각00202000/ffe02000/00002000을 확인했다. 일반 참조·기존 고정 등록·object 경계 및 live counter0/1/2000/8000/ffff를 비교했다.

8승계시퀀스의 실제 IRQ16회는 포트16,456개, RAM/양쪽palette bank/display와 일치한다. 비활성8회는counter2000을 보존하고 활성8회는bank1을 채우며counter0으로 만든다. 전체119호출/16,716포트다. 원본코드·현재ROM bank 불변을 확인했으며47570은 실행하지 않았다. 보고서 SHA256 `de8e6e4ca5ddd97c691e22d34e94c087fbfd950d635f62b203cd8cbd3c61a240`.
