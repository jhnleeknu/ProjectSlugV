# 첫 구역 사운드 진입 리뷰

Baseline `4d97459`. Canonical 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 CPU 주소는 고정 첫 1MiB의 ROM 오프셋과 같다. 메인은 원본 명령과 구현·검증 diff를 검토했고, sol 세 작업에 구현/회귀, 독립 원본 비교, 후속 목록/문서를 나누었다.

## 진입과 레지스터

479d8은47594를 호출한다.47594는 MOVE.W0720부터 시작하므로47570의 앞선 RAM 초기화와 MOVEQ0을 실행하지 않는다. 기존 GamePreludeState의 phase0에서 두 진입을 허용하고, prefix 쓰기는47570에만 적용했다.47594는 입력 D0 상위16비트를 보존한다.3bf8/3c00/3d44/3d4c는 모두 D0의 byte만 바꾸므로 대기 및475a4 완료에서도 상위word가 유지된다. 기존47570 결과는 그대로다.

공통 capture는 D0 상위word와0700|command를 합치며, continuation 검사는 lowword를 확인한다. 완료 전 같은 대기를 재호출해도 prefix 쓰기나 외부 상태 읽기를 반복하지 않는다. initialize_game은 기존 suffix 연결을 재사용하여47594부터47640 RTS까지 실행한다.475a4 경계까지 보존한 D0 상위word와 전체 초기화 후 D0/D1/D3=0을 구분한다. 메인 재확인에서 기존 헤더의 `47642 RTS` 주소 주석을 실제 `47640 RTS`로 바로잡았다.47642는 다음 함수다.

## 검증 근거

- 전체 `make -j3 all test`: Python118/C++94, 경고0. 로그 `artifacts/first_area_sound_build_test.log`.
- `verify_game_prelude.py`:235조건=기존171+47594 신규64, 오류 보존50. 기존 IRQ37회/포트68개를 유지하며 신규 실제 CLI 승계16개를 추가했다. 보고서 SHA256 `7432265d5ecaabe8603866d176133cfe32a2f58b96aa49580971795e29e68896`.
- `verify_game_initialization.py`:650조건=기존562+신규88, 오류 보존33. 승계20개=기존4+신규16. 보고서 SHA256 `9610a86247038cb92cf810dde218aa9764dacfe79950e5aa5f7e191f2b8fe876`.

두 검증 모두 word high/low, byte08/20의 네 대기를 실제로 관측한다. 전체 RAM과 D0/D1/D3, 스택 대기 깊이 및 완료/반환 A7을 확인하고 원본 고정 ROM과 실행 바이너리 불변을 검사한다. Native context를 승계할 때 SR/A7/stack을 재초기화하지 않는다. 신규47594 승계의 큐 head 변경은 명시적인 host 입력이며 자연 IRQ 일정의 증거가 아니다. 기존47570 IRQ 검증과 구분한다.

## 다음 범위

inventory_stage_area_body.py와 분석 문서는479d0..47af0의 호출21개/15대상 및16개 callee 창을 보존한다.558행은 명령 후보 수이며 분석 완료 수가 아니다.4e4d2의128바이트도 원시 근거 창으로만 취급한다.

이번 변경은47594 직접 진입을 복원했다.479d0의 양쪽 분기 통합,4e666의 selector 정리,479fe 이후 할당·사운드·일반 scene script와 자연 scheduler 및 전체 게임플레이는 여전히 다음 작업이다. 전체 목표는 미완료다.
