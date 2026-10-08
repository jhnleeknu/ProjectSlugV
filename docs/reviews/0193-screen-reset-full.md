# ca9e/caf0 전체 레지스터 화면 초기화 리뷰

Baseline `b24c41f`, branch `codex/screen-reset-full`. Sol 6.1 / medium 작업자가 core/unit, CLI/문서, 원본 비교를 분담했고 메인이 원본 계약, 실제 diff 및 현재 검증 산출물 해시를 확인했다.

기존 부분 상태 API를 유지하면서 `reset_game_screen_full`을 추가했다. 두 API는 동일한 port 생성 함수를 사용한다. ca9e는 임의 A5를 허용하고 RAM을 변경하지 않는다. caf0는 실제 BYTE 목적지 A5−0x769a만 변경하며 지원 A5 양끝과 홀수 목적지를 허용한다. 범위 검사는 unsigned 뺄셈 전에 수행한다. 전체 15레지스터의 보존/변경과 D6/D7 상위 WORD 동작을 확인했다. 모든 할당과 검증 이후 RAM·상태·ports를 게시하므로 API 실패는 입력을 보존한다.

CLI는 ENTRY와 15레지스터, 세 파일 경로를 받는다. 정확한 15키 JSON과 기존 9byte `>BII` ports 형식을 사용한다. 일반 파일 검사, O_NONBLOCK 출력 예약, 실제 inode 별칭 검사와 identity를 확인한 새 placeholder 정리를 검토했다. 두 출력의 실제 write/close 실패를 원자적으로 되돌린다고 주장하지 않는다. Makefile은 새 target과 기존 소스의 모든 상위 header 의존성을 연결한다.

수정하지 않은 Unicorn 원본 관찰 32조건과 실제 CLI의 전체 RAM 64KiB·15레지스터·순서 있는 45,520개 ports가 일치했다. 4개 레지스터 프로필, ca9e 임의 A5, caf0 RAM 양끝·홀수 목적지를 포함한다. 잘못된 입력 134조건, FIFO와 실제 대소문자 비구분 파일 별칭도 출력 보존을 통과했다. 원본 RAM/stack/port 쓰기 재생, ROM 불변, SR 설정 순서를 확인하며 CPU 실행 중 SR을 읽지 않는다. 비교 stack은 게임 RAM 밖 oracle 영역이다.

검증 명령은 `.venv/bin/python tools/observe_screen_reset_full.py`, `.venv/bin/python tools/verify_screen_reset_full.py`, `make -j4 all test`다. 전체 테스트 Python182/C++135, 경고0. 기존 화면 초기화 API 회귀와 새 API 오류 원자성도 통과했다. 메인은 현재 소스/CLI 9개, native 입력 5개와 산출물 129개 해시를 보고서와 다시 대조했다.

- Native report SHA256: `26f2944f354460b3a9b48768e930003a323aa2491c36ae981b9ce0fcefc6b349`
- Verification SHA256: `eb27509b0fa14a529a230df257fa9aab600b535afead2fb8577c23606bf7a9bf`
- CLI SHA256: `e037c3844f188f4a2e793fd56bab850487f3b5608f3c08444cc23acd15f0e91e`
- Build/test log: `artifacts/screen_reset_full_build_test.log`

이 단위를 수용한다. CCR/cycle/A7·물리 mirror·실제 화면 동등성은 이 API 범위 밖이다. 이후 stage 활성화, 자연 scheduler/IRQ, 직접 플레이와 전체 게임 목표는 미완료다. 다음 477a2/ddf9a/362a/35f0의 정적 계약을 별도로 기록했으며 이를 C++ 구현 완료로 계산하지 않는다.
