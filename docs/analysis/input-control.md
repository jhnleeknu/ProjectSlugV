# f12 입력부터 컨트롤러 반환 소비까지

원본 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
명령 주소는 고정 ROM CPU 주소이며 복호화 프로그램 오프셋과 같다.

`step_input_control`은 기존 `begin_input_frame`과 `step_control_caller`를 연결한다. f12의 신호 초기화,31d6 입력 처리와b68 상태 후처리 이후 callback 포인터가0이면f54의9136 호출과f5a 반환 소비까지 진행한다. 포인터가 비영이면f3c 직전 경계로 반환한다. 입력과 컨트롤러 사이에 원본에 없는 RAM·레지스터 재설정은 넣지 않는다.

D1.word는 입력 처리에서 얻은 style을 컨트롤러에 넘긴다. D3.word는 입력 경로에서 보존되므로 initial_line을 그대로 넘긴다. f54 도달 시 호출자 스택 깊이는f12 진입과 같으므로 entry_stack을 그대로 전달한다. f54 내부9136 호출의4바이트 깊이는 기존 API가 처리한다.

`InputFrameResult.style`은 입력 구간이 반환한D1.word이며 컨트롤러 종료 시의D1이 아니다. next_pc는f3c callback 경계,ec4 루프,fee trap 직전,c00444 BIOS 전환 또는0 정상 반환이다. callback 정보는 입력 구간에서 캡처한 원본 주소값이다. 컨트롤러의 BIOS·trap 경계는 성공 결과로 그 이전 변경을 확정하며, 지원 오류에서는 RAM/result/포트 출력 전체를 보존한다.

callback 경로는 컨트롤러 리소스·진단 스택을 사용하지 않으므로 API가 이들을 검증하지 않는다. CLI는 명시적으로 주어진 리소스 파일을 모두 로드한다. callback 함수 실행, 레지스터 전체와 외부 스택 모델, 실제 interrupt 대기,ec4의 video counter 읽기 및 전체 부팅은 별도 범위다.

빌드: `make build/step_input_control`.
CLI: `build/step_input_control INPUT_RAM STREAMS STATUS_TABLE MENU PAUSE PALETTES OUTPUT_RAM OUTPUT_PORTS OBJECT STYLE LINE STACK SYSTEM P1_RAW P2_RAW P1_GAME P2_GAME [FONT [STAGES_DIR]]`.
포트 출력은 기존 진단용9바이트 레코드(size8/addressBE32/valueBE32)다. 입력·메뉴·팔레트·폰트·스테이지 리소스는 기존 런타임 바이너리를 그대로 사용한다.

검증: `.venv/bin/python tools/verify_input_control.py`.

## 연속 실행 검증

원본f12부터 연속 실행한338조건(독립192+승계146)에서 전체64KiB RAM, 순서 있는 포트 쓰기69,521건과 모든 반환 정보가 일치했다. 두 승계 시퀀스는72/74회이며 raw 버튼의 누름·해제로 stage area/group 선택, 전체 닫기, 진행, 재활성화와 두 번째 닫기까지 수행한다.

b68 이후 A1=b58임을f54의314회와f3c의24회 진입에서 검사했다. 원본f54 직전 레지스터 재설정은 하지 않았다. 입력 구간의D3 전체 보존, f5a의 A6/스택 보존, stage callback 스택 깊이12/16/32바이트를 확인했다. callback24회와BIOS1회는 반환 소비를 우회한다. trap 직전 경계도 실행 관측했다.

늦은 팔레트 오류2조건에서는 RAM·포트 출력 파일이 새로 생기거나 변경되지 않았다. 원본 고정 ROM과 팔레트 bank의 PVC tail 이외 영역은 불변이다.

보고서: `artifacts/input_control/verification.json`.
SHA256: `385a3e87f68525fce6fd8709a89486658635234c085ce2e68f23efb59fd78338`.


## 입력·대기 경로의 전체 레지스터 (2026-10-07)

`step_input_control`, `poll_input_control`, `poll_callback_input_control`은 trailing optional D1/D3를 받는다. 제공된 값의 하위 word가 STYLE/LINE과 일치해야 한다. 입력 접두부의 전체 반환을 제어기에 전달하며, 최종 d1/d3는 제어기·팔레트 처리까지 수행한 값이다. `InputFrameResult.style`은 계속 입력 경계의 D1.word이므로 최종 d1.lowword와 다를 수 있다.

원본 ef2..f12 대기는 D0만 쓰고 D1/D3를 보존한다. f4c..f54의 callback 대기는 메모리 byte를 검사하며 D1/D3를 보존한다. 대기 성공은 RAM과 두 레지스터를 유지한다. 준비된 경우에만 입력으로 진행하고, 이후 오류 시 대기의 RAM18 갱신까지 후보 상태와 함께 버린다. CLI는 `--registers D1 D3`와 `--poll VIDEO` 또는 `--callback-poll`을 어느 순서로든 받는다.

`step_main_debug`도 optional full D3를 formatter에 전달한다. LINE도 제공하면 D3.lowword와 일치해야 한다. 비활성/zero-status bypass는 전체 D3를 보존하고, 실제 출력은 문자열 위치 제어의 전체 D3 변경을 따른다. 이 경로의 CLI는 `--d3 D3`를 지원한다. 물리적인 VBlank 시간, 임의 callback 본체, 다른 CPU 레지스터까지 복원됐다는 뜻은 아니다.


검증: `.venv/bin/python tools/verify_input_control_registers.py`는 810조건(prefix344/direct346/ef2대기60/f4c대기60), 포트81,005개 및 출력 보존69조건을 통과했다. 원본의 입력 읽기3,067회·video읽기37회와 접두부의 A1=b58/전체D3 보존을 관측했다. f54 직전에 원본 레지스터를 재설정하지 않는다. 9개 시퀀스354호출은 CLI RAM/D1/D3 반환을 승계했다. replay 이벤트74조건, 이벤트 없는 mode1 100조건 및 mode1→2 종료25조건을 실제 원본3588과 RAM 전이로 구분한다. 보고서 SHA256 `80703108ba7fb17e2be84f1dc583b3270db29e89f1c1a91ea2cfb29038a98174`. 신호16은 대기 시퀀스에서 호스트가 공급하며 IRQ 발생을 이번 검증으로 주장하지 않는다.


`.venv/bin/python tools/verify_main_debug_registers.py`는 ec4→ef2 806조건과 진단 포트62,382개, 출력 보존18조건을 통과했다. 추가 8회 input/controller 구간은 포트2,142개·입력읽기40회가 일치했다. 두 시퀀스는 최초 status1/pending-activation1에서 시작하여 debug→input/controller→ec4의 실제 CLI RAM/D1/D3를 4회씩 전달한다. 이후 object status0에 따른 debug bypass는 원본 동작이며, 뒤에 호스트 RAM을 주입하지 않는다. ef2 게이트는 이 시퀀스에서 실행하지 않고 f12로 진행하므로 IRQ/대기 시간 검증은 아니다. 보고서 SHA256 `c4ae8af3511d1392ea57bf397f7907fde2cc8e9787d3a1b6cc6082407ee16487`.
