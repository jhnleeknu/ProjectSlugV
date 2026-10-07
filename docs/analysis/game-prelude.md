# 47570 접두부·47594 직접 진입과 사운드 대기

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 CPU 주소는 고정 ROM 파일 오프셋과 같다. 메인이47570..475a4와 호출 함수3af8/3d3a/3ac8을 직접 해석했다.

## 접두부 실행

47570은 RAMd683/d694/d69c byte를 지우고,100e로000e/089e word를 지운다.4755e는de14/de1c long을 지우며4823a는d680/d681 byte를0으로 한다. e8a1c는de26에원본포인터e89e4를 저장하고de2e=ff/de2f=0을 쓴다. 이 구간은 포인터를 역참조하지 않으므로 해당 데이터 자체를 추출한 것으로 취급하지 않는다.

이후 word명령0720을3af8에 전달한다. 중복·필터 처리는 기존 word producer를 따르며 링이 가득 차면 오래된 명령을 byte 큐로 보낸다. word 처리가 끝나면3d3a가RAM4d7e.byte를0으로 하고 byte명령08과20을 순서대로 보낸다. 후속475a4의RAMd686.word 지우기 전에서 현재 접두부 API가 끝난다.

3aea는 모든 byte producer 대기의 공통 PC다. 같은 PC만으로 재개할 위치를 판단할 수 없다. GamePreludeState는 phase1(word overflow),2(byte08),3(byte20)을 구분하며 word 내부 phase1/2는 high/low byte를 구분한다. phase0은47570 또는47594 최초 진입, phase4는475a4 완료 경계다. 완료 경계에서 이 API를 다시 호출하면 오류다.

47594 직접 진입은 위 prefix RAM 저장과 MOVEQ0을 건너뛰고 MOVE.W0720부터 시작한다. 따라서47570은 D0.highword=0으로 시작하지만47594는 입력 D0.highword를 보존한다. 이 보존은 word overflow와 두 byte 대기/재개 및475a4 완료 경계에도 이어진다. 직접 진입은 d683/d694/d69c,000e/089e,de14/de1c,d680/d681,de26/de2e/de2f를 초기화하지 않는다.47570에서 저장한e89e4 포인터가 직접 진입에서도 새로 기록된다고 주장하지 않는다.

D3는 그대로이며D1 상위word를 보존한다. 대기 및 최종 byte 전송에서D1.low는 captured next다. D0.lowword는 word 대기에서0700|command, byte08 대기에서0708, byte20 대기와완료에서0720이다. 전체 D0는 보존한 상위16bit와 이 lowword를 합친다. 이 규칙은 byte 대기의D0 전체가항상000007xx라는 이전47570 전용 관측을47594로 확장하지 않는다. 재개는 초기 필드 초기화와 conditional external read를 반복하지 않는다.

prefix에는 MMIO 쓰기가 없다.0720의필터는 RAM12==1,fd82!=0,fe80==0일 때만d00046 byte를 읽는다. API는값을인자로받고호출당 external_reads로 실제읽기여부를 반환한다. 실패하면RAM/state/read count를 보존한다.

## CLI

```
build/prepare_game --state PC D0 D1 D3 PHASE \
  [--word PHASE LOW CURSOR COMMAND TAIL NEXT] \
  [--byte COMMAND TAIL NEXT] EXTERNAL INPUT_RAM OUTPUT_RAM
```

JSON은next_pc/d0/d1/d3/phase/external_reads와word/byte pending을 담는다. RAM과pending,전체레지스터를 함께승계해야 한다. phase1은kind1의overflow pending을 사용하며 captured tail/next는live tail로대체하지 않는다. 잘못된PC·phase·pending·D0/D1 조합은외부출력변경없이거부한다.

## 후속 리셋 함수 묶음

`reset_game_subsystem`은 아래9개주소만지원하며 전체64KiB RAM과D0/D1/D3를변경한다. 고정필드동작을복원한것이며임의ROM주소실행기가아니다. 전체47570 통합은 [game-initialization.md](game-initialization.md)에 있으며 이 표는 선택한 개별 helper의 계약이다.

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

## 기존47570 검증 결과

`verify_game_prelude.py`: 원본171경계에서 전체RAM/D0D1D3와pending이 일치했다. word대기42회(high20/low22), byte08대기38회, byte20대기20회,475a4완료71회다. 원본 stack 반환주소3c00/4759e/3d4c/3d42로pending을독립적으로분류했다. 조건부external읽기16회와prefix MMIO쓰기0개도확인했다. 오류47조건은출력을보존한다.

12승계시퀀스는호스트가sound head를수정하지않고실제c8c IRQ37회로producer를재개했다. IRQ의순서있는포트68개가일치한다. IRQ rendering은비활성이며CPU context/stack 보존은호스트가한다. 별도2조건은실제game_startup CLI의RAM/레지스터를전달하고원본c584 JSR을실행하여47570으로진입한다. 저장된c58a 반환주소를검사하고, 한조건은완료·다른조건은가득찬byte링에서08대기에진입한다. 추가startup포트는4개다. suffix475a4는실행하지않는다. 보고서SHA256 `24e42600a631bc346165547a417fe3aa9c8dab9f2bc039697c952525c918af05`.

`verify_game_reset.py`:9개원본함수의전체RAM/D0D1D3를288회비교했다. 독립144조건과16개×9호출 실제CLI 상태승계가포함된다. 오류17조건과MMIO쓰기없음·원본불변도확인했다. 중간의다른47570호출은생략된선택함수검사이며전체초기화라고주장하지않는다. 보고서SHA256 `3188b37509467d265d390a56e74720662b928a890fe0904219cf19d3277f30d3`.

## 47594 확장 최종 검증

새 최종 `artifacts/game_prelude/verification.json` SHA256은 `7432265d5ecaabe8603866d176133cfe32a2f58b96aa49580971795e29e68896`이다. Session83344 exit0에서235조건=기존47570의171+직접47594의64, 오류50조건=기존47+추가3을 확인했다. 기존 실제IRQ37회/68포트는 유지되며 새47594 사례의 대기 해제는 별도로 표시한 host sound-head 변경이다. 전체 conditional read38회와 모든 재개 read0, 접두부 MMIO쓰기0을 확인했다.

직접47594 추가16개 시퀀스는 실제 CLI RAM/full D0/D1/D3/pending을 승계한다. 원본 네 하위 wait `(phase,wordphase)=(1,1),(1,2),(2,0),(3,0)`를 실제 관측하고 각각 A7 offset10/4/12/8 및 완료 stack endpoint를 검사했다. Native context/stack을 유지하며 명시적 RAM4d74.word 변경으로 대기를 해제한다. D0.high16과 prefix의세 clear byte d683/d694/d69c 보존이 일치했다. 이 host release를 기존 IRQ 해제 사례와 혼합하거나 자연 IRQ 일정이라고 주장하지 않는다.

시작·종료 prepare_game binary SHA256은 동일한 `adafa60a871b3aa59d9378dbd104e240a1bc84cf2050ba4bcbd40b3125620f93`다. 원본 fixed1MiB는 불변이며 전체 RAM/노출 register 계약만 비교했다. 전체 `make -j3 all test` 로그 `artifacts/first_area_sound_build_test.log`는 Python118검사·C++94 test executable·warning/error0이며 실행 담당자가 exit0을 보고했다. Shared suffix의 새 전체 함수 검증은 [game-initialization.md](game-initialization.md)에 별도로 기록한다. 자연479d0 caller 전체 및 stage body/scheduler 연결은 여전히 별도 범위다.
