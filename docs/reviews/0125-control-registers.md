# 상위 제어기 전체 레지스터 리뷰

대상 baseline: `fe407cf`. 메인 에이전트가 원본 명령, 구현 diff, CLI/테스트와 검증 스크립트를 직접 검토했다.
프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. CPU 92fc/9136/f54는 복호화 프로그램 파일 오프셋과 같다. 팔레트 검증의 CPU200000..2ffff0은 같은 파일 오프셋의 진단 매핑이다.

## 변경과 원본 근거

92fc JSR a370 이후 9302는 D0 byte를 검사하며 D1/D3 복구 명령이 없다. a370 반환 레지스터를 종료 처리에 전달한다. BIOS 외부 점프는 종료 처리를 건너뛴다. 9136의 비활성/대기/메뉴 분기를 각 하위 API와 연결했다. f54 JSR9136 이후 f5a MOVE.B object+84,D1은 상위24비트를 보존하므로 제어기의 전체 반환이 필요하다. 이후 기존 팔레트 API의 전체 scratch 값을 최종 반환한다.

후보 RAM/포트/레지스터를 사용하여 늦은 오류도 출력에 반영하지 않는다. 비활성 분기는 하위 activate_control 성공 뒤 실패 가능한 연산이 없음을 확인했다. C++11 기본 문법을 유지하며 바이너리 리소스 규격은 바꾸지 않았다.

## 발견·수정

- 기존 진입 STYLE을 그대로 종료 처리에 사용하던 가정을 제거했다.
- 새 caller 단위 검사에서 효과 시작/첫 tick을 빠뜨린 레지스터 예상값을 수정했다. 동일 fixture를 원본 f54에서 직접 실행하여 ec4의 D1=0000ff01, D3=4를 확인했다. 효과 나눗셈 뒤 첫 tick의 중간 채널 byte 차이가 D1.lowbyte를1로 바꾼다. 런타임 구현은 원본과 일치했다.
- 연속 검증의 메뉴 슬롯 합성 초기값과 시작 후 renderer 변경을 보고서에 명시했다. 실제 시작으로 검증된 모든 CPU 상태라고 과장하지 않는다.

## 검증

`make -j3 all test` 최종 session36359 exit0. 로그 `artifacts/control_registers_build_test.log`: Python73 및 C++ 전체 통과, 컴파일 경고 없음. 앞선 두 실행의 실패는 위 단위 기대값 오류이며 수정 후 재검증했다.

`.venv/bin/python tools/verify_control_registers.py`: 1,207조건(menu260/control503/caller444), 순서 있는 포트208,678개, 실제 stage callback233회, 오류 보존65조건. 전체64KiB RAM/반환 경계/전체 D1/D3를 비교한다. 10개 시퀀스445호출은 C++ CLI 반환 RAM/레지스터를 다음 native/C++ 호출의 입력으로 전달한다. ROM fixed 영역과 팔레트 bank 불변도 검사한다.
보고서 SHA256 `fd6a4249b3831c84cd6bd5da3e5006a7cda88a4a52c5dbff7d99f05a6b5b6431`.

## 남은 범위

A1은 매 진입 시 전역 renderer라는 외부 계약이다. 호스트가 입력 byte를 공급하고 일부 renderer를 변경한다. 초기 메뉴 슬롯은 합성 fixture다. 다른 CPU 레지스터/CCR, 외부 스택 메모리, 물리 타이밍, BIOS/TRAP 실행, ec4 이후 메인 루프와 전체 게임 동작 완료를 증명하지 않는다. 다음은 입력·메인 계층의 레지스터 연결이다.
