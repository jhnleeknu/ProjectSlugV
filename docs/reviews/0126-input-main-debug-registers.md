# 입력·대기·메인 debug 레지스터 리뷰

Baseline `6c39a04`. 메인 에이전트가 원본 명령, 모든 구현/CLI/test diff 및 두 검증 스크립트의 비교·승계 방식을 직접 검토했다.
프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 fixed CPU 주소는 복호화 프로그램의 파일 오프셋과 같다. 팔레트 진단 bank200000..2ffff0도 같은 파일 오프셋으로 매핑한다.

## 근거와 구현

31d6..349a는 D1.byte를 갱신하고 mode1의352a..35a0은 D1 byte/word만 쓴다. 3580 MOVE.W/3586 BCHG는 상위16비트를 보존한다. ROM000180 selector0을 사용하는 기존 지원 범위를 유지한다. b68..bb4와 입력 접두부는 D3를 변경하지 않는다. 검증된 style word와 입력 D1 상위16비트를 합성하고, 전체 D3를 전달한다.

`step_input_control`은 입력의 전체 반환을 f54 제어기에 전달하고 최종값을 반환한다. 기존 result.style은 input boundary word여서 최종 D1과 다를 수 있다. ef2..f12는 D0만 사용하고 f4c 대기도 D1/D3를 보존한다. 각 wrapper는 후보 RAM/포트/레지스터로 오류 시 출력을 보존한다. main debug는 formatter의 전체 D3와 연결하며 LINE/D3 일치 검사는 bypass에서도 적용한다.

## 발견 및 수정

진단→입력 연속 검증의 최초 inactive/no-request 상태는 원본 f54에서 정상 RTS를 반환했다. ec4 복귀를 기대한 fixture가 잘못된 것이므로 pending activation1을 설정했다. 이후 object status0으로 debug가 생략되는 원본 동작을 유지했다. 런타임 의미를 테스트 기대에 맞춰 바꾸지 않았다.

CLI의 옵션 중복/순서, 입력 word 일치, 파일 별칭, 늦은 오류 rollback을 검토했다. 이미지/재생 음원을 런타임 리소스로 대체하지 않았으며 MS5D/MS5P 원본 데이터 로더를 사용한다.

## 검증 결과

`make -j3 all test`: session3519 exit0, Python73개 및 C++ 전체 통과, 경고 없음. 로그 `artifacts/input_control_registers_build_test.log`.

`tools/verify_input_control_registers.py`: 810조건(prefix344/direct346/poll60/callback-poll60), 포트81,005개, 입력읽기3,067회/video읽기37회, 오류 보존69조건. 실제3588 event74조건/no-event100조건/mode1→2 25조건. 9시퀀스354호출은 CLI RAM/full D1/D3를 승계한다. 원본 f54 직전 재설정 없이 A1=b58, D3 보존과 callback stack을 관측한다. ROM 불변 확인. 보고서 SHA256 `80703108ba7fb17e2be84f1dc583b3270db29e89f1c1a91ea2cfb29038a98174`.

`tools/verify_main_debug_registers.py`: debug806조건, 포트62,382개, 오류18조건. 추가 input/controller8회에서 포트2,142개/입력읽기40회와 RAM/전체D1/D3가 일치한다. 실제 CLI 반환으로 2×4회 debug→input/controller→ec4 연결. 보고서 SHA256 `c4ae8af3511d1392ea57bf397f7907fde2cc8e9787d3a1b6cc6082407ee16487`.

## 제약과 다음 작업

입력 대기 시퀀스의 신호16은 호스트 fixture다. debug 연속 검증은 ef2 게이트를 건너뛰고 f12로 진입하며 IRQ/물리 타이밍을 증명하지 않는다. 외부 callback/BIOS/TRAP 및 다른 CPU 레지스터/CCR·픽셀·사운드 전체는 미검증이다. 다음은 IRQ 신호와 callback/팔레트 경로를 포함한 메인 루프 통합이다. 전체 목표 완료는 아니다.
