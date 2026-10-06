# 제어 요청 비트와 비활성 상태 진입

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 ROM 주소는 고정영역 CPU/파일 주소가 같으며 RAM offset은 CPU100000 기준이다. 정확한 물리 버튼/게임 메뉴 의미는 미확인이다.

## 9086 요청 선택

RAM0012가2일 때 RAMfd82가0이면4cb5 전체byte를 읽는다. 다른 경우에는 f002가nonzero일 때4cb9/4cbf의bit7을 각각 결과bit1/bit3으로 옮기고4cb4 및0a와AND한다. 이후fdb6이0 또는3이면bit1을 지우고fdb7이0 또는3이면bit3을 지운다.

RAM0012가2가 아니면 f002가nonzero일 때만 두 bit7을 결과2/8로 옮긴다. 이 경로는4cb4와fdb6/fdb7을 검사하지 않는다. RAM을 변경하지 않으며 원본은 D0 전체를0으로 초기화하므로 결과 상위24비트도0이다.

`read_control_request` C++ API는 RAM65536바이트를 읽고1바이트결과를 반환한다. CLI `read_control_request INPUT_RAM OUTPUT_MASK`는 그 값을1바이트파일로 쓴다. 크기오류 시 API출력값을 보존하며 CLI는 입력/출력파일alias를 거부한다.

## 9136 비활성 상태 진입

7df0이0인 경로만 다음과 같이 원본실행으로 검증했다. 7df1이nonzero이면 이를7df0으로 옮기고7df1을0으로 만든다. pending요청이없으면 f000 bit1 또는7def==0 조건에서9086을 호출한다. 결과bit1이있으면7df0=1, 아니면bit3이있으면2로설정한다. 두bit가동시에있으면bit1이우선한다. 요청이없거나허용조건이없으면D0=1로반환한다.

활성화시7df6 long을0으로,4cd2 word를1002로설정한다(313c호출). 현재입력4caa/4cb0을7dfc/7dfd로보관한다. 공통92a8 꼬리에서 새로눌린bit를계산하지만 이진입에서는 방금같은값을저장했으므로 입력누적byte는불변이다. 7df3은0으로설정된뒤byte감소하여ff가되며D0=0으로반환한다.

비활성 진입은 activate_control로 구현했다. 이미 활성인7df0!=0은 이 API에서 명시적으로 거절한다. 활성 상태 전체 분기는 후속 분석 대상이며, 그 안의92ce 메뉴 진입과a370 메뉴 프레임은 별도 C++ API에 연결했다. 고정문자출력3902를 사용하는 대기/반복 처리와 메뉴 종료 뒤 간접callback은 아직 전체 컨트롤러로 통합하지 않았다.

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

첫a370 프레임까지 즉시 실행한다. 이 호출의 실제 진입A7은92ce 진입S−4다. 원본native메뉴의 표시 높이가0이므로 첫 프레임은 열기 단계를 수행하며 글꼴 리소스는 아직 읽지 않는다. 이후 호출은 step_menu_frame에 기존font/stage리소스를 전달한다.

마지막92a8은 각 플레이어의 누적 입력에 `(현재 XOR 저장값) AND 현재`를OR하고7df3을byte 감소한다. 저장값7dfc/d는 이 경로에서 갱신하지 않는다. 비활성 요청 수락과 메뉴 진입의 입력 보관 시점을 합쳐 버리면 원본과 달라진다.

전체 진입은 하나의 C++ 트랜잭션이다. 773개 출력을 준비하고 메뉴 초기화까지 한 뒤 프레임 검증이 실패해도 RAM/result/ports를 모두 보존한다. 메뉴 초기화에도 선택적final_line을 연결하여 D3를 첫 프레임으로 전달한다.

원본92ce의432개 고립 조건과3개 열기 시퀀스의15호출을 비교했다. 전체 RAM, ordered ports, signedD0, D3 및 외부 전환 결과가 일치했다. helper 호출 순서는ca9e/a29c/a2b8/a370/92a8이며 앞의 네 진입은S−4, 꼬리는S임을 hook으로 확인했다. 초기화 후 첫 프레임의 소수 byte, 누적 입력과 countdown을 별도 검사했다. 연속 시퀀스는 실제9332 호출과 완전히 열린 상태 도달을 확인한다.

아직 미완료인 범위는9136 활성 대기/반복 전체 제어, 메뉴 종료 뒤 간접callback과928e 문자열 지우기, 실제 게임 입력 수집·스케줄링/부팅 및 픽셀/타이밍이다. 분리된 진입과 프레임 검증을 전체 컨트롤러/게임 완료로 취급하지 않는다.

비활성 진입의 C++ 비교는 원본9136의8,192조건 전체 RAM/반환byte가 일치했다(수락8,169/미진입23). 원본mapped1MiB 불변, 이미 활성인 입력·잘못된 RAM 크기·직접/하드링크/심볼릭링크 출력 충돌의 보존 검사를 포함한다. 전체 make all test(Python55개 및 C++전체) 통과.
