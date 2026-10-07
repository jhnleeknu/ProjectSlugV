# Stage dispatch 접두부와 callback 경계

## 범위와 근거

원본 canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 명령 주소는 첫1MiB의 고정 ROM CPU 주소이며 파일 오프셋과 같다. RAM100000..10ffff와 MMIO 주소는 ROM 파일 오프셋과 구분한다. 별도 표기가 없는 주소·상수는16진수이며 바이트·반복·포트 개수는10진수다.

`artifacts/stage_dispatch/inventory.asm`은478c4..47b00의 명시적 전체 창을 보존한다. 명령/분기 후보 목록이며 원본 실행 trace나 전체 본문 분석 완료를 뜻하지 않는다. 마지막47afe의 원시1028은 지정 범위 안에서 두 바이트뿐이므로 `dc.w`로 남겼다. 바깥 명령을 완전하게 해석한 것으로 취급하지 않는다. 직접 호출 및 기존 API 후보는 `artifacts/stage_dispatch/report.json`에 있다.

`engine/include/ms5/stage_transition.h`의 `StageTransitionState`는 next_pc, 전체32bit D0/D1/D2/D3, A6를 운반한다. `step_stage_transition`은 아래 여섯 dispatch 진입과 세 callback 진입을 지원하며 정확한64KiB RAM, 정렬된 완전한c4-byte A6 span을 요구한다. 오류 시 RAM·전체 state·순서 있는 `VideoPortWrite`를 보존한다. 내부 작업은 candidate RAM/state/ports에서 수행한 뒤 성공 시 게시한다. 다른 주소 레지스터·CCR·stack·자연 scheduler와 물리 시점은 노출 계약 밖이다.

## 여섯 dispatch 진입

| 진입 CPU/ROM 주소 | 원본 명령과 구현 경계 |
| --- | --- |
| 478c4 | MOVEQ로 D0/D1/D2=-31, D3.word=0을 설정하고8c16 호출. A6.callback=478de를 저장한 뒤480bc 본문 직전에 끝낸다. |
| 478f0 | D0/D1/D2=-31, D3.word=0x10 및 A6+7a.word=0x10 설정,8c16 호출, callback4790a 설정 후 같은 호출의 countdown까지 실행한다. |
| 4791c | caf0 화면 reset 후 A6+7a.word=0x3c, D0/D1/D2=31, D3.word=0x1e를 설정한다.478fe로 합류해8c16→callback4790a→countdown을 실행한다. |
| 47934 | callback4fcb8, D0.word=0으로28ae 할당을 호출한다. 성공 시 flag 대기 callback4798e, 실패 시478c4의 fade 설정으로 합류한다. |
| 4794c | callback4fd0a로 같은 할당·성공/실패 경로를 수행한다. |
| 47964 | callback4ff4c로 할당하고 성공 시 새 child+76/+78.word에 LIVE RAM10d690/10d692를 원본 순서로 복사한다. 이후 같은 flag 대기 경로다. |

각 할당은 기존 `allocate_object`를 사용한다. A6+62.byte를0으로 만들고 A6.callback=4798e를 저장하는 성공 경로는 설치만 수행하며4fcb8/4fd0a/4ff4c body를 실행하지 않는다. child 좌표 word 복사는 source/destination alias 가능성을 고려해 순서대로 읽고 쓴다. 할당 실패의 carry 분기는 내부 선택 근거이며 전체 CCR 반환을 제공하는 계약이 아니다. 잘못된 live pointer는 API 오류이며 정상 할당 실패와 구분한다.

4791c의 caf0은 기존 `reset_game_screen`의2072개 ordered watchdog/video 쓰기를 사용한다. 이 호출 뒤 fade 설정과 countdown도 같은 API 호출에서 계속 실행한다. caf0 화면 reset과 ca8a의 후속 clear를 동일 동작으로 축약하지 않는다.

## 8c16의 전체 레지스터 결과

C++는 기존 `set_palette_effect`의 RAM 갱신과 원본 DIVS의 전체 D0/D1/D2 결과를 함께 연결한다. 세 입력은 MOVEQ -31 또는31이므로 각 목표word는e100 또는1f00이다. 목표에서 현재 RAM107dc2/4/6.word를 뺀 하위16bit 차이를 signed 확장해 나눗셈에 사용한다. quotient는0 방향 절단이며 전체 레지스터는 signed remainder의 하위word를 상위16bit에, quotient의 하위word를 하위16bit에 둔다.

세 차이가 모두0이면 각 D0/D1/D2는 입력 highword를 유지하고 lowword0으로 끝난다. 따라서 dark 경로는ffff0000, bright 경로는0이다. D3도 caller의 highword를 보존하고 lowword0으로 끝난다. 하나라도 달라지면 duration의 하위byte가0인 경우1, 그 외 값이 전체 D3로 반환되어 이전 highword를 대체한다. dark 즉시 설정은1, dark timed 설정은0x10, bright 설정은0x1e다. RAM targets/steps/timer의 원본 정수 폭은 기존 palette-control 계약을 따른다.

이 레지스터 결과를 색상 RAM만 맞추거나 D0/D1/D2의 lowword만 보존하는 구현으로 대체하지 않는다. 반대로 전체 DIVS 레지스터 결과를 다른 helper나 다른 레지스터의 보편적인 계약으로 확대하지 않는다.

## 세 callback 진입과 종료 경계

478de는72f0의 RAM107ded.byte 판정을 한 번 수행한다. D0.lowbyte는 이전 byte−0x80의 byte wrap 결과이며 나머지 D0 bits를 보존한다. 이전 값이0x80 이상이면 원본의 BCC busy loop를 한 번 관측하는 경계로 next_pc=478de를 반환한다. Host가 자연 palette/IRQ 진행을 대신 완료했다고 주장하지 않는다. 이전 값이0x80 미만이면 ca8a clear를 실행해479b0 본문 직전에 끝난다.

4790a는 A6+7a.word를 항상1 감소시킨다. **이전 값이0일 때의 underflow만** ca8a로 진행한다. 이전 값이ffff처럼 signed 음수여도 underflow 조건이 아니므로480bc 경계로 끝난다.478f0 계열 timed 시작에서 첫 감소도 같은 호출에 포함된다. counter 저장은 이후의 alias-sensitive 읽기보다 먼저 수행한다.

4798e는 LIVE A6+62.byte를 검사한다.0이면480bc 경계에서 끝난다. 비영이면 dark 즉시8c16 설정을 실행하고 A6.callback=479b0을 기록한 뒤480bc 경계로 끝난다. 이 API가479b0 body를 대신 실행하거나 callback 변경만으로 자연 재호출을 보장하지 않는다.

ca8a clear는1283개 ordered 포트를 기록한다. 먼저 watchdog300001.byte=0, 다음40열×32행의1280개3c0000.long 쓰기, 마지막3c0004.word=0과3c0000.long=82000000이다. 각 clear 값은 highword `7000+column*32+row`, lowword7000이며 column0..39 바깥 루프, row0..31 안쪽 루프 순서다. 완료 D0.lowword=7500, D1.lowword=7000, D2.lowword=0은 각각 highword를 보존하고 D3 전체는20이다. next_pc=479b0은 후속 body **직전** 경계다.

## 연결 한계와 검증 상태

원본 stage entry는 별도 API에서 selector를 조회하고 이 여섯 dispatch 주소를 반환한다. 그 API는 D0/D1/D3와 A6를 노출하지만 D2를 반환하지 않는다. 따라서 stage entry→transition 사이 D2를 host fixture로 전달하는 검증은 명시해야 하며, 현재 인터페이스만으로 완전한 원본 register chain이 복원됐다고 주장하지 않는다.479b0과480bc는 이 API의 출력 경계이고 입력 진입으로 지원하지 않는다.

독립 검증 `.venv/bin/python tools/verify_stage_transition.py`의 최종 `artifacts/stage_transition/verification.json`을 읽고 SHA256 `fa20a6699046a1429b21094909462a5f7cd9be89688f6016ae195ff7756f97d3`을 확인했다. 원본1249조건, 오류 보존49조건, 순서 있는 포트618179개가 통과했다. 전체64KiB RAM·전체 D0/D1/D2/D3/A6·포트 순서가 일치했고 MMIO read0·원본 코드 변경0이다. 검증 시작·종료 binary는 동일 SHA256 `e0f78097c4db6e2b60b9ed9d4effb9561bcee1ba27ab0fb0a221a19057dbd7af`다.

모든256개 palette transfer status의 한 번 helper 실행·loopback, allocation 성공/실패와 live parent/depth, countdown underflow, no-change highword와 signed DIVS remainder를 비교했다. A6+7a counter와 palette current의 LIVE alias36조건 및 child 첫 word 쓰기가 두 번째 source와 겹치는1조건을 포함한다. 각 alias는 명시적 fixture이며 일반 포인터가 안전하다는 주장으로 확대하지 않는다.

실제 CLI RAM/full register 출력을 운반하는 callback 승계6시퀀스(각3/17/61/2/2/2호출)는 native CPU context도 유지했다. callback 호출 순서는 host가 명시적으로 선택했고 gate/child flag 변경도 host fixture다.480bc scheduler나 외부 callback body를 실행하지 않았으므로 자연 scheduler/IRQ/timing 동등성 결과가 아니다.

전체 `make -j3 all test`의 `artifacts/stage_transition_build_test.log`에서 Python95검사·C++91 test executable 실행과 warning/error0을 확인했다. 빌드 실행 담당 에이전트가 exit0을 보고했고 메인은 로그와 변경을 검토했다. 일반479b0 stage body,480bc 메인 연결, callback allocator의 하위 body와 자연 scheduler·전체 stage gameplay는 미완료다.
