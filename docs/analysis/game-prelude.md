# 47570 접두부의 사운드 대기와 후속 리셋 함수

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 CPU 주소는 고정 ROM 파일 오프셋과 같다. 메인이47570..475a4와 호출 함수3af8/3d3a/3ac8을 직접 해석했다.

## 접두부 실행

47570은 RAMd683/d694/d69c byte를 지우고,100e로000e/089e word를 지운다.4755e는de14/de1c long을 지우며4823a는d680/d681 byte를0으로 한다. e8a1c는de26에원본포인터e89e4를 저장하고de2e=ff/de2f=0을 쓴다. 이 구간은 포인터를 역참조하지 않으므로 해당 데이터 자체를 추출한 것으로 취급하지 않는다.

이후 word명령0720을3af8에 전달한다. 중복·필터 처리는 기존 word producer를 따르며 링이 가득 차면 오래된 명령을 byte 큐로 보낸다. word 처리가 끝나면3d3a가RAM4d7e.byte를0으로 하고 byte명령08과20을 순서대로 보낸다. 후속475a4의RAMd686.word 지우기 전에서 현재 접두부 API가 끝난다.

3aea는 모든 byte producer 대기의 공통 PC다. 같은 PC만으로 재개할 위치를 판단할 수 없다. GamePreludeState는 phase1(word overflow),2(byte08),3(byte20)을 구분하며 word 내부 phase1/2는 high/low byte를 구분한다. phase0은47570 최초 진입, phase4는475a4 완료 경계다. 완료 경계에서 이 API를 다시 호출하면 오류다.

D3는 그대로이며D1 상위word를 보존한다. 대기 및 최종 byte 전송에서D1.low는 captured next다. 최초D0는MOVEQ 때문에00000720이 된다. 오래된 명령을 보낼 때도byte 명령만D0를 덮으므로 word 대기의D0는0700|command, byte08 대기는0708, byte20 대기와완료는0720이다. 재개는 초기 필드 초기화와 conditional external read를 반복하지 않는다.

prefix에는 MMIO 쓰기가 없다.0720의필터는 RAM12==1,fd82!=0,fe80==0일 때만d00046 byte를 읽는다. API는값을인자로받고호출당 external_reads로 실제읽기여부를 반환한다. 실패하면RAM/state/read count를 보존한다.

## CLI

```
build/prepare_game --state PC D0 D1 D3 PHASE \
  [--word PHASE LOW CURSOR COMMAND TAIL NEXT] \
  [--byte COMMAND TAIL NEXT] EXTERNAL INPUT_RAM OUTPUT_RAM
```

JSON은next_pc/d0/d1/d3/phase/external_reads와word/byte pending을 담는다. RAM과pending,전체레지스터를 함께승계해야 한다. phase1은kind1의overflow pending을 사용하며 captured tail/next는live tail로대체하지 않는다. 잘못된PC·phase·pending·D0/D1 조합은외부출력변경없이거부한다.

## 후속 리셋 함수 묶음

`reset_game_subsystem`은 아래9개주소만지원하며 전체64KiB RAM과D0/D1/D3를변경한다. 고정필드동작을복원한것이며임의ROM주소실행기가아니다. 다음47570전체호출로통합하는작업은별도로남아있다.

| 원본 진입 | 확인한 효과 | D0/D1/D3 |
| --- | --- | --- |
| b7a20 | dddc..dde2, dde4..ddea를0 | 보존 |
| 4d126 | dcba/dce6의명시적field reset, +26=4/+20=ffff | 보존 |
| 4d13c | 같은두구조체의word0/word6/long8/byte22만0 | 보존 |
| 49a8e | d726..d731 및d734..d73b를0, 중간word d732 보존 | 보존 |
| 4aa30 | daf8의128byte/db88의256byte와지정flag, d746/d918의d0byte와+1d0word를0, dc88=10db88 | 모두0 |
| b4a24 | dd5c부터10byte stride의12word를0 | D0=0 |
| 2ef90 | d487/d48f/d490/d491 byte를0 | D0=1 |
| 46f2e | d4e6의8개2cbyte구조체에서0..25를0,+26=ffff,+2a=0,+28보존 | D0=0 |
| 4ddb6 | dd12/dd18의6byte구조체를01 00 00 00 ff ff로설정 | 보존 |

CLI는 `build/reset_game_subsystem ENTRY D0 D1 D3 INPUT_RAM OUTPUT_RAM`이다. 알려지지 않은진입주소나RAM크기는변경전에거부한다. MMIO나새런타임리소스를필요로하지않는다. 나머지레지스터/CCR/stack은이API의반환계약이아니다.

## 검증 결과

`verify_game_prelude.py`: 원본171경계에서 전체RAM/D0D1D3와pending이 일치했다. word대기42회(high20/low22), byte08대기38회, byte20대기20회,475a4완료71회다. 원본 stack 반환주소3c00/4759e/3d4c/3d42로pending을독립적으로분류했다. 조건부external읽기16회와prefix MMIO쓰기0개도확인했다. 오류47조건은출력을보존한다.

12승계시퀀스는호스트가sound head를수정하지않고실제c8c IRQ37회로producer를재개했다. IRQ의순서있는포트68개가일치한다. IRQ rendering은비활성이며CPU context/stack 보존은호스트가한다. 별도2조건은실제game_startup CLI의RAM/레지스터를전달하고원본c584 JSR을실행하여47570으로진입한다. 저장된c58a 반환주소를검사하고, 한조건은완료·다른조건은가득찬byte링에서08대기에진입한다. 추가startup포트는4개다. suffix475a4는실행하지않는다. 보고서SHA256 `24e42600a631bc346165547a417fe3aa9c8dab9f2bc039697c952525c918af05`.

`verify_game_reset.py`:9개원본함수의전체RAM/D0D1D3를288회비교했다. 독립144조건과16개×9호출 실제CLI 상태승계가포함된다. 오류17조건과MMIO쓰기없음·원본불변도확인했다. 중간의다른47570호출은생략된선택함수검사이며전체초기화라고주장하지않는다. 보고서SHA256 `3188b37509467d265d390a56e74720662b928a890fe0904219cf19d3277f30d3`.
