# 제어 요청 비트와 비활성 상태 진입

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 ROM 주소는 고정영역 CPU/파일 주소가 같으며 RAM offset은 CPU100000 기준이다. 정확한 물리 버튼/게임 메뉴 의미는 미확인이다.

## 9086 요청 선택

RAM0012가2일 때 RAMfd82가0이면4cb5 전체byte를 읽는다. 다른 경우에는 f002가nonzero일 때4cb9/4cbf의bit7을 각각 결과bit1/bit3으로 옮기고4cb4 및0a와AND한다. 이후fdb6이0 또는3이면bit1을 지우고fdb7이0 또는3이면bit3을 지운다.

RAM0012가2가 아니면 f002가nonzero일 때만 두 bit7을 결과2/8로 옮긴다. 이 경로는4cb4와fdb6/fdb7을 검사하지 않는다. RAM을 변경하지 않으며 원본은 D0 전체를0으로 초기화하므로 결과 상위24비트도0이다.

`read_control_request` C++ API는 RAM65536바이트를 읽고1바이트결과를 반환한다. CLI `read_control_request INPUT_RAM OUTPUT_MASK`는 그 값을1바이트파일로 쓴다. 크기오류 시 API출력값을 보존하며 CLI는 입력/출력파일alias를 거부한다.

## 9136 비활성 상태 진입

7df0이0인 경로만 다음과 같이 원본실행으로 검증했다. 7df1이nonzero이면 이를7df0으로 옮기고7df1을0으로 만든다. pending요청이없으면 f000 bit1 또는7def==0 조건에서9086을 호출한다. 결과bit1이있으면7df0=1, 아니면bit3이있으면2로설정한다. 두bit가동시에있으면bit1이우선한다. 요청이없거나허용조건이없으면D0=1로반환한다.

활성화시7df6 long을0으로,4cd2 word를1002로설정한다(313c호출). 현재입력4caa/4cb0을7dfc/7dfd로보관한다. 공통92a8 꼬리에서 새로눌린bit를계산하지만 이진입에서는 방금같은값을저장했으므로 입력누적byte는불변이다. 7df3은0으로설정된뒤byte감소하여ff가되며D0=0으로반환한다.

비활성 진입은 activate_control로 구현했다. 이미 활성인7df0!=0은 이 API에서 명시적으로 거절한다. 활성 상태 전체 분기는 후속 분석 대상이며, 그 안의92ce 메뉴 진입과a370 메뉴 프레임은 별도 C++ API에 연결했다. 고정문자출력3902를 사용하는 활성 대기/반복 처리는 step_control_wait로 연결했다. 이미 열린 메뉴의 종료 뒤 간접callback은 아직 전체 컨트롤러로 통합하지 않았다.

## 효과 호출과 검증

f54는9136을호출하고 반환byte를object+84에기록한다. 이전값1에서반환0으로전환한경로는f94의효과저장과fa8의(-4,-4,-4,4)설정으로이어진다. 반환값/이전값에따른다른경로에는fd6의복구호출이있다. 자연게임입력으로이경로에진입했다는증거는아직없다.

```
make all test
.venv/bin/python tools/verify_control_request.py
.venv/bin/python tools/analyze_control_entry.py
```

9086의2,384조건에서원본D0·불변RAM·C++결과가일치했다. 직접입력256값,상태필터,모드별bit추출,비표준byte값을포함하며256종결과를모두관찰했다. 9136비활성진입은pending256값×32설정=8,192조건의원본전체RAM/반환값이모델과일치했다(활성화8,169/미진입23). 이검증은활성상태동작이나게임전체입력재현을의미하지않는다.

## C++ 비활성 요청 수락

```
build/activate_control INPUT_RAM OUTPUT_RAM
.venv/bin/python tools/verify_control_activation.py
```

출력 JSON `status`는 원본D0 low byte(수락0/비진입1)다. pending byte는1/2 이외에도 원본대로 복사한다. 수락한 경우313c의1002 word 설정, 입력 보관과92a8의 byte 감소를 포함한다. 현재 입력을 방금 저장했으므로 누적 입력byte는 변하지 않는다. 오류는 RAM과 출력status를 보존한다.

## 메뉴 진입92ce 연결

```
build/start_control_menu INPUT_RAM MENU_MS5D OUTPUT_RAM OUTPUT_PORTS LINE ENTRY_STACK
.venv/bin/python tools/verify_control_menu_start.py
```

이 API는 활성 컨트롤러에서 이미 메뉴 진입을 결정한92ce부터 실행한다. 입력 게이트를 다시 해석하지 않는다. 기존 C++ 게임용 MS5D에서 native93e0을 읽으며 새 리소스 형식을 추가하지 않는다.

원본ca9e는3c0000에773개의long을 쓴다. VRAM주소7500..77ff에0을 순서대로 쓰고,7500/7520/7540/7560에0200,7580에ff02를 쓴다. 이 단계에서 해당 데이터의 더 넓은 하드웨어 의미를 추정하지 않는다. 이어 RAM7dee를ff로 만들고 a29c로93e0을x4/y8에 초기화한다. a2b8의 효과로 전역renderer를9332로 설정하고 종료word7dfa를0으로 만든다.

첫a370 프레임까지 즉시 실행한다. 이 호출의 실제 진입A7은92ce 진입S−4다. 원본native메뉴의 표시 높이가0이므로 첫 프레임은 열기 단계를 수행하며 글꼴 리소스는 아직 읽지 않는다. 이후 컨트롤러 호출은 아래 step_control_menu에 기존 font/stage 리소스를 전달한다.

마지막92a8은 각 플레이어의 누적 입력에 `(현재 XOR 저장값) AND 현재`를OR하고7df3을byte 감소한다. 저장값7dfc/d는 이 경로에서 갱신하지 않는다. 비활성 요청 수락과 메뉴 진입의 입력 보관 시점을 합쳐 버리면 원본과 달라진다.

전체 진입은 하나의 C++ 트랜잭션이다. 773개 출력을 준비하고 메뉴 초기화까지 한 뒤 프레임 검증이 실패해도 RAM/result/ports를 모두 보존한다. 메뉴 초기화에도 선택적final_line을 연결하여 D3를 첫 프레임으로 전달한다.

원본92ce의432개 고립 조건과3개 열기 시퀀스의15호출을 비교했다. 전체 RAM, ordered ports, signedD0, D3 및 외부 전환 결과가 일치했다. helper 호출 순서는ca9e/a29c/a2b8/a370/92a8이며 앞의 네 진입은S−4, 꼬리는S임을 hook으로 확인했다. 초기화 후 첫 프레임의 소수 byte, 누적 입력과 countdown을 별도 검사했다. 연속 시퀀스는 실제9332 호출과 완전히 열린 상태 도달을 확인한다.

활성 대기와 메뉴 종료 연결은 아래 후속 절에서 다룬다. 실제 게임 입력 수집·스케줄링/부팅 및 픽셀/타이밍은 미완료이며, 분리된 진입과 프레임 검증을 전체 게임 완료로 취급하지 않는다.

비활성 진입의 C++ 비교는 원본9136의8,192조건 전체 RAM/반환byte가 일치했다(수락8,169/미진입23). 원본mapped1MiB 불변, 이미 활성인 입력·잘못된 RAM 크기·직접/하드링크/심볼릭링크 출력 충돌의 보존 검사를 포함한다. 전체 make all test(Python55개 및 C++전체) 통과.

## 활성 대기·반복과 점멸

```
.venv/bin/python tools/pack_control_pause.py
build/step_control_wait INPUT_RAM MENU_MS5D PAUSE_MS5D OUTPUT_RAM OUTPUT_PORTS STYLE LINE ENTRY_STACK
.venv/bin/python tools/verify_control_wait.py
```

입력 상태는7df0!=0,7dee==0이다. STYLE은 원본 진입D1 word, LINE은D3 word다. 이미 메뉴가 열린 경우는 이 API가 거절한다. 이 함수는 비활성 수락이나 메뉴 종료 콜백을 실행하지 않는다.

원본91c2는 플레이어별로 처리한다. enable bit0인1P에 대해 요청bit1, f002가 켜진 경우의4cb5 bit0,4cb4 bit0 순으로 검사하고, 아무 동작도 없을 때 enable bit1인2P의 요청bit3/4cb5 bit2/4cb4 bit2를 검사한다. 따라서1P의 새 진행·누름 유지가2P의 메뉴 요청보다 먼저 처리된다. 모든 메뉴 요청을 먼저 모아서 판정하면 달라진다.

새 진행925e는7df2를15로 설정하고 status low byte2를 반환한다. 누름 유지926c는7df2를byte 감소하고, 이전 값이0이면1로 다시 설정하여2를 반환한다. 그 외에는0이다.15에서 시작해 계속 유지하면15회0 후2/0/2가 반복된다. 여기서 한 프레임의 실제 게임 업데이트를 실행하는 것은 이 함수의 호출자 역할이다.

동작이 없으면 f001 bit6이 표시를 억제한다. 억제하지 않을 때7df3을 먼저byte 감소하고 그 결과&30이0이면9079의5공백, 아니면9068의PAUSE를3902로 출력한다. 공통92a8에서 다시 감소하므로 표시하는 대기는 총2회, 억제·진행·메뉴 진입은1회 감소한다. 입력 누적OR도 원본대로 유지한다.

9068..9086의30바이트를 기존MS5Dv1 `control_pause.ms5d`(파일62바이트)로 보존했다. 두 문자열의 제어 인자에 포함된0과9078의padding을 그대로 유지한다. 원본참조9238/924c를 검사하며 stable ID는 `control-pause:00009068`이다. PNG는 사용하지 않는다.

9086의 일부 selector 경로는D1 low byte를 변경한다. 이를 표시 전 스타일에 적용한다. PAUSE는palette0을 명시하지만 공백 문자열은 기존palette를 보존하므로 들어온D1을 무시하면 포트가 달라진다.

`result.status`는 **signed D0 전체**다. 표시 후9256은하위word만0으로 만들므로 상위word에3650이 마지막으로 그린tile이 남는다. 호출자가 사용하는 상태는 low byte0/2이며 `status==0`만으로 판정하면 안 된다. 원본비교에서 발견한 차이를 그대로 보존했다. `line`과포트 출력도 함께 반환한다.

원본9136/91c2의1,416조건에서 전체RAM,포트238,180회,signedD0,D3가 일치했다. 실측분기는대기776/새진행135/누름유지205/메뉴진입300이며,실제3902문자열은PAUSE484/공백144회다. 두플레이어의20회누름유지와표시억제유무별40회점멸시퀀스는출력RAM을이어갔다. 원본분기·script주소·counter/입력누적을별도assertion으로검사했다.

수정후전체make all test(Python61개/C++전체)가통과했다. 늦은텍스트오류시이미감소한counter와모든출력을복원하는검사,키우선순위,반복underflow,표시palette/줄위치를포함한다. 이미 열린 메뉴의 후속 처리와928e 출력은 다음 절에서 연결한다. 임의의 종료 간접 콜백과 실제 게임 메인 루프 통합은 남아 있다.


## 열린 메뉴의 프레임과 종료 연결

```
build/finish_control_menu INPUT_RAM PAUSE_MS5D OUTPUT_RAM OUTPUT_PORTS FRAME_D0 STYLE LINE
build/step_control_menu INPUT_RAM MENU_MS5D PAUSE_MS5D OUTPUT_RAM OUTPUT_PORTS STYLE LINE ENTRY_STACK [FONT [STAGES_DIR]]
.venv/bin/python tools/verify_control_finish.py
.venv/bin/python tools/verify_control_menu_frame.py
```

`finish_control_menu`는 원본9302부터의 처리다. 입력은 a370이 **반환한 뒤**의 D0 전체와 D1/D3 word다. D0 low byte가0이면932a는 하위 word만0으로 만든다. 그 외에는 메뉴 열림 byte7dee를0으로 만들고7df6의 콜백을 호출한 후, 종료 word7dfa가 정확히1이면928e로 간다. 현재 C++은 호출이 필요한 비영 콜백을 명시적으로 거절한다. low byte0인 경로에서는 콜백을 읽거나 실행하지 않으므로 비영 값도 허용한다.

928e는9079의 다섯 공백을 e84c8을 통해 그린다. 메뉴의9332 remapper를 거치지 않으며, 문자열이 선택한 font3은3650 직접 출력을 사용한다. 별도 폰트 테이블을 읽지 않고 기존 PAUSE MS5D의 제어 바이트를 사용한다. 들어온 D1의 palette를 보존한다. 마지막에7dee와7df0을0으로 만들고 D0=1로 설정한다. 종료 word가1이 아니면 활성 제어7df0과 D0를 유지한다. 모든 정상 반환은92a8의 입력 누적과 blink 감소를 수행한다.

`step_control_menu`는 이미 활성화되고 메뉴가 열린 상태(7df0/7dee가 모두 비영)에서92fc의 전체 호출을 연결한다. a370에는 컨트롤러 진입 A7보다4 작은 주소를 전달하여 stage callback의 스택 깊이도 보존한다. BIOS 전환이면 종료 꼬리를 실행하지 않는다. 모드0..2에서 프레임이 비영 D0를 반환하는 경로는 빈 스택 또는 높이0인 마지막 root를 pop하는 경우다. 두 경로는 D1을 바꾸지 않는다. 이 근거로 종료 지우기에 진입 STYLE을 전달하며, 실제9302 hook에서도 이 조건을 검사한다. 다른 모드는 이 연결 API의 지원 범위 밖이다.

두 API 모두 실패하면 RAM, 결과 구조체와 포트 목록을 보존한다. 특히 프레임이 마지막 root를 pop한 후 종료 콜백이나 문자열 검증에서 실패하는 경우도 전체 호출을 취소한다. 반환 status는 signed D0 전체이며, 호출자의 상태 판정은 하위 byte를 사용한다.

고정 ROM 첫1MiB에서7df6의 직접 참조는919a의0 초기화와930e의로드를 확인했다. 이 검색은 계산 주소나 다른 뱅크를 통한 비영 쓰기가 없다는 증거가 아니다. 임의의 간접 콜백 구현은 미완료다. 원본 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며, 이 절의 CPU 주소는 복호화 ROM 오프셋과 같다.

종료 꼬리 비교는880조건(독립760 + RAM 승계120), 실제3918 호출118회와 포트1,180회가 일치했다. 비영 콜백 거절48조건에서 기존 출력 보존과 새 출력 미생성을 확인했다. 전체 RAM, signed D0, D3 word 및 원본 매핑 불변을 검사했다.

연결 검증은1,027프레임(9136 진입36,92fc 진입991), 실제 stage callback697회와 포트165,533회가 일치했다.13개 연속 시퀀스는 초기화 후 child 열기·조작·취소/선택·parent 복귀·종료와 header 요청 종료를 포함한다. 비영 프레임 반환138회에서9302의 D1 word 보존을 확인했다. BIOS 전환 시 종료 꼬리를 건너뛰며 실제 watchdog3회도 비교한다. 종료 콜백·잘못된 PAUSE 범위·미지원 모드·비활성 상태의12개 CLI 거절 조건과 C++ 늦은 오류 트랜잭션 검사를 통과했다.

전체 `make all test`는 Python61개와 C++ 전체가 통과했다. 보고서는 `artifacts/control_finish/verification.json`(SHA256 `b9a16862228a1fb1b959aab7df3450362f2ac33ad37092501ff6459541b14afe`)과 `artifacts/control_menu_frame/verification.json`(SHA256 `a963f297ca0163bf489ad7a282c4554a925af55edca01733414cef66f981d6cd`)이다. 전체 CPU 레지스터/flags, 외부 진단 스택 메모리, 입력 수집·게임 업데이트 스케줄링, 픽셀·하드웨어 타이밍과 전체 게임 부팅을 검증한 것은 아니다.


## 통합9136 진입

```
build/step_control INPUT_RAM MENU_MS5D PAUSE_MS5D OUTPUT_RAM OUTPUT_PORTS STYLE LINE ENTRY_STACK [FONT [STAGES_DIR]]
.venv/bin/python tools/verify_control.py
```

`step_control`은7df0==0이면 비활성 수락, 그렇지 않고7dee==0이면 활성 대기, 그 외에는 열린 메뉴 프레임을 실행한다. 비활성 분기가 메뉴 byte보다 우선하므로 오래된7dee가 비영이어도 먼저 활성화를 처리한다. 사용하지 않는 분기의 리소스나 외부 진단 스택은 API에서 검사하지 않는다. CLI는 지정한 리소스 파일들을 로드한 뒤 호출한다.

비활성 수락은 MOVEQ로D0를0/1로 만들고 D3를 보존한다. 다른 분기의 signed D0 전체도 기존 API 그대로 반환한다. 호출자는 하위 byte로 판단해야 한다. BIOS 외부 전환은 별도 필드이며 실제 firmware 실행을 대신하지 않는다. 지원하는 메뉴 descriptor·모드·콜백 범위는 구성 API와 같다.

원본9136과835조건(독립576, RAM 승계258프레임, 오류 검증용 실제 메뉴 시작1회)에서 전체 RAM, signed D0, D3와 포트102,635회가 일치했다.4개 시퀀스는 활성화→누름 반복→메뉴 열기→debug/area/group 자식 조작→전체 종료→재활성화→두 번째 종료까지 이어진다. 재구성 측과 원본 측의 모든 출력 RAM을 비교하고 다음 입력 상태로 승계했다. 이 시퀀스의 입력 byte는 진단 호스트가 공급하며 실제 하드웨어 입력 수집을 검증한 것은 아니다.

실제 원본 hook에서919a 활성화97회,91c2 활성 분기731회,92ce 메뉴 시작97회,92fc/9302 메뉴 프레임255회,928e 종료8회,9602 area callback38회,9802 group callback18회를 확인했다. 미지원 종료 콜백의 늦은 실패2조건은 출력 파일을 보존했다. 전체 `make all test`(Python61개와 C++ 전체), API 분기 우선순위·오류 시 상태 보존과 CLI 숫자/별칭 검사가 통과했다.

보고서 `artifacts/control/verification.json` SHA256: `123e0774c0313c8fc741e753f3155004aeeb381c9f8ad06adddc3c60371b550e`. 실제 호출자의 효과·카운터 연결은 `control-caller.md`의 별도 분석이며,9136 통합만으로 게임 한 프레임이나 전체 부팅의 완료를 의미하지 않는다.

## 요청·비활성 진입의 D1/D3 반환

`read_control_request`와 `activate_control`은 선택적 `std::uint32_t* d1` 입출력을 받는다. 기존 호출은 그대로 유효하다. 원본9086은 RAM12==2, fd82!=0, f002!=0일 때만 D1.low byte를 `RAM4cb4 & 10`으로 바꾸고 상위24비트를 보존한다. 이후 상태 필터가 요청을 모두 지워도 D1 변경은 남는다. 다른 요청 경로는 전체 D1을 보존한다.

비활성9136은 pending7df1!=0이면 요청 판정을 건너뛴다. pending이0이어도 f000 bit1이0이고7def!=0이면 건너뛴다. 313c의word 저장과92a8의공통꼬리는 D1/D3를 변경하지 않는다. 따라서 이 API는 실제9086 호출에만 D1을 전달한다. 두 원본 경로 모두 D3는 그대로이며 별도 출력필드를 추가하지 않았다. 크기오류·활성상태거절은 선택적 D1도 보존한다.

```
build/read_control_request --d1 0xabcdab68 INPUT_RAM OUTPUT_MASK
build/activate_control --d1 0xabcdab68 INPUT_RAM OUTPUT_RAM
.venv/bin/python tools/verify_control_activation_registers.py
```

새CLI모드만 JSON `d1`을 추가하며 기존1바이트 mask 및RAM파일 형식은 유지한다. 이 변경은 활성 대기·열린메뉴의 최종 D1/D3를 아직 반환하지 않는다. 통합 `step_control`의 전체 레지스터 전달은 후속 작업이다.

## 메뉴 프레임 반환 이후9302의 전체 D1/D3

`finish_control_menu`의 선택적 D1/D3 입출력은 a370이 이미 반환한 시점부터 시작한다. 기존 frame_style/frame_line은 해당 레지스터의하위16비트와 일치해야 하며 불일치는 모든 출력을 보존하고 거절한다. CLI는 `--registers INPUT_D1 INPUT_D3`를 기존 인자 앞에 넣으면 반환JSON에 전체d1/d3를 추가한다.

D0.byte==0이면D0.lowword만0으로 만들고 D1/D3는보존한다. D0.byte!=0이고 종료word7dfa가1이 아니어도 D1/D3를보존한다. 종료word가1이면928e가3918을호출하여 원본9079문구를출력한다. 이문구의 `\c`는 D1.lowbyte를3으로 바꾸며 상위24비트를보존한다. 첫 `\l`은38ce에서MOVEQ0,D3을실행하므로 최종D3는 **상위16비트도0인0000725a**다. 공통92a8꼬리는이레지스터들을변경하지않는다.

공유 `trace_table_fixed_text`는 선택적으로 최종style 및 전체D3를반환한다. 파서가실제로위치제어문자를읽었는지기록하여 상위word초기화를판정한다. 위치제어가없으면3918의초기MOVE.W D0,D3과이후word연산대로상위word를보존한다. 종료직전제어문자도반환값에포함하며실패시모든선택적출력은불변이다.

a370 내부메뉴프레임, 활성대기91c2와메뉴시작92ce의전체레지스터반환은아직연결하지않았다. 이단계의입력레지스터는명시적경계입력이며 원본게임메뉴의전체실행을재현했다는의미가아니다.

## 활성 대기와 메뉴 시작의 전체 D1/D3

`step_control_wait`와 `start_control_menu`에도 선택적 전체D1/D3 입출력을 연결했다. CLI는 기존 인자 앞에 `--registers D1 D3`를 넣는다. wait의STYLE/LINE은입력레지스터의하위word와같아야하고 start는LINE만검사한다. 모든오류는레지스터/RAM/기존결과/포트를보존한다.

활성대기91c2는9086에서갱신된D1을분기전체에전달한다. 새step·held·문구억제는D3를그대로보존한다. idle의3902는D0.word를D3.word로옮긴뒤문구를파싱한다. 실제9068/9079의위치제어는D3전체를초기화한다. 직접텍스트추적에서종료style과전체D3를반환하게하여중복측정없이이결과를이어전달한다.

메뉴시작92ce의ca9e는cabc에서MOVEQ0,D1을실행한다.92e2는D1.word에8을넣고a29c로메뉴를초기화한다. a0a0의제목측정38e8은공유파서386e를사용하므로추출된제목의제어문자가D1/D3에남는다. `FixedTextMeasure.line_reset`으로전체D3초기화여부를알리고메뉴초기화는최종style과D3를반환한다.

첫a370호출에서는root의현재높이byte가0이고목표높이는양수다. 따라서a348→9b58의테두리출력은높이0으로즉시반환하고D1/D3를유지한다. RAM의높이fraction byte는원본대로보존되지만이조건을바꾸지않는다. native root가아닌목표높이0의변형리소스는이API의첫opening경로에해당하지않으므로거절한다. 이미열린메뉴a370의전체레지스터반환은후속작업이다.
