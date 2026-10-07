# 메인 프레임 재개·IRQ·콜백 연결 리뷰

Baseline `1e0dad0`. 메인 에이전트가 API 설계·구현, 원본 분기와 CLI/단위 테스트/연속 비교 스크립트를 직접 검토했다.
프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. fixed CPU ec4/ef2/f12/f4c/c8c/f3c/f44/5728은 복호화 프로그램의 같은 파일 오프셋이다. 팔레트 진단 bank200000..2ffff0은 같은 source offset으로 매핑한다.

## 구현과 근거

새 MainFrameState는 PC/object/full D1/D3만 명시적으로 보관한다. ec4 debug 뒤 ef2로 전이하고, 대기 중에는 ef2만 재개한다. 입력·제어기 뒤 ec4를 반환하더라도 같은 호출에서 다음 프레임을 실행하지 않는다. f4c는 callback과 palette 이후 대기이므로 palette를 반복하지 않는다. 오류 시 후보 RAM·state·InputFrameResult·포트를 함께 버린다. 단위 검사에서 debug 출력 후 입력 오류의 롤백까지 확인했다.

CLI --main은 기존 --poll/--callback-poll과 배타적이며 --registers가 필요하다. debug 리소스와 출력 파일 별칭을 검사한다. 팔레트 CLI도 기존 API의 full D3를 노출하며 기존 기본/--d1 출력은 유지한다. C++11 기본 구조체와 일반 함수를 사용한다.

## 리뷰 발견·수정

메인 연속 검증의 첫 fixture에서 mode1 스트림 주소가 빠졌고, callback0 경로의 inactive/no-request가 정상 반환하는데 ec4를 기대했다. 원본 의미를 확인하여 초기 스트림 포인터와 pending activation을 수정했다. 런타임 구현을 바꿔 맞추지 않았다. debug 수행 횟수는 ec4 진입과 실제3a70 formatter 호출을 구분해서 검사하도록 했다. C++ D1/D3는 실제 반환을 native comparison context에도 명시적으로 전달한다.

## 검증

`make -j3 all test`: session87804 exit0, Python73개 및 C++ 전체(새 main_frame_test 포함) 통과, 경고 없음. 로그 `artifacts/main_frame_flow_build_test.log`.

`tools/verify_callback_register_flow.py`: 38경계, 출력 보존12조건. 15 main poll, 7 palette, 9 envelope, 7 c8c IRQ service를 비교한다. 세 연속 기본콜백 주기 및 네 팔레트 경로에서 실제 CLI RAM/full D1/D3를 승계한다. envelope만 전체16레지스터/stack을 비교·승계한다. 보고서 SHA256 `14e37384f2944dfbacc751546e571098431ffda56d81fa9ca28522329c290074`.

## 범위와 제약

IRQ service가 실제 signal16을 생성하지만 main CPU context 보존·복원은 호스트가 수행한다. BIOS/SR/RTE와 물리 타이밍을 구현한 것이 아니다. 입력/팔레트의 D1/D3 외 scratch register는 native fixture다. 기본3dcc 외 arbitrary callback은 외부 경계다. 모든 코드·리소스·stage 복원 완료를 의미하지 않는다.


`tools/verify_main_frame_flow.py`: 원본54경계(main37/IRQ17), 포트746개, 출력 보존14조건 통과. main 진입은 ec4 8/ef2 19/f12 8/f4c 2회다. video8/input73/sound16회 읽기를 확인하고, reentrant service1회는 sound를 읽지 않는다. 6개 승계 시퀀스에 controller→ec4의 세 프레임 주기가 포함된다. 8번 ec4 진입과 실제 debug formatter2회를 구분하며 waiting에서 재출력이 없다. 초기 fixture 이후 신호16은 실제 c8c만 바꾼다. 단 한 번 호스트가 재진입 guard19를 해제하는 조건은 별도 표시했다. 보고서 SHA256 `0a43c89908e4fcdb2b458fba4abadedc7173259c67f6933815ab59873fdfe3a1`.
