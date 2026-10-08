# Stage activation helper 리뷰

Baseline `730c943`, branch `codex/stage-activation-helpers`. Sol6.1/medium 세 작업자가 core/unit, CLI/Make/문서, 원본 비교를 분담했다. 메인이 원본 계약, 실제 core·단위·CLI·검증기와 Makefile 변경을 읽고 현재 보고서의 입력과 산출물 해시 1,790개 참조를 확인했다.

4e216/bee의 BYTE 읽기 순서, 상위 register 보존, 조건부 반환 carry를 연결했다. 16ed2는 두 signed WORD를 먼저 읽은 뒤 alias 가능한 flag BYTE를 변경한다. 49f8c는 object clear, bank shadow clear, PVC 두 WORD, A5 guard, animation pointer/timer/speed 쓰기의 원본 순서를 유지한다. A1은 이 구간에서 읽지 않는 불투명 값이다. A6=fffea/fffe8의 bank shadow와 pointer 중첩도 임의 후처리 없이 보존한다.

실제 도달한 span만 검사하고 WORD/LONG에는 2byte 정렬을 요구한다. 각 helper의 전체 RAM/state/carry/ports는 임시 결과가 성공한 뒤 교체된다. 16ed2/49f8c는 입력 bool을 보존하지만 원본 CCR을 제공하지 않으므로 CLI carry는 null이다. A5 TRAP와 잘못된 접근은 checked 실패이며 원본 정상 반환으로 취급하지 않는다.

CLI는 숫자·RAM·core 오류 이후에만 출력 예약을 시작한다. 두 파일을 truncate 없이 예약하고 일반 파일과 inode를 검사한다. 신규 case alias와 FIFO를 포함한 예약 실패에서 기존 파일을 보존하고 새 placeholder만 제거한다. 실제 write/close 실패의 두 파일 원자적 rollback은 보장하지 않는다.

- 실제 CLI 443조건 = 저장된 원본441조건 전체 재실행 + A5=1175bb의 미실행 두 번째 BYTE 주소를 허용하는 원본2조건. 전체64KiB RAM/15레지스터/지정 carry/ordered PVC150개 일치.
- 정상 조건분기9개 양쪽, A5 TRAP guard 정상 쪽만 원본 관측. bee의 관측 A5는0/ffffffff다.
- 오류·파일 보존155조건 통과. API 단위는 RAM/state/carry/ports 전체 보존을 별도로 확인한다.
- 독립 Sol 리뷰가 최종 WORD 실패의 직접 API 검사를 보강하도록 제안했다. A6=10ffd4에서 LONG10fffa와 WORD10fffe까지 성공한 뒤 WORD110000이 실패한다. false/true 입력 carry 모두의 rollback 회귀를 추가했다.
- 전체 `make -j4 all test`: exit0, Python196/C++142/경고0. 최종 단위 보강 뒤 메인이 normal/UBSan을 따로 재실행했고 모두 exit0으로 통과했다. 로그 `artifacts/stage_activation_helpers_build_test.log`.
- Native SHA256 `ed26b6cc85ec93c777f211d1fa1d184eeb965659cbaec281116ed7bb4a28b0cf`.
- Verification SHA256 `4600addebfe6aed363c07387ee9d5e13fa9f4c4ef241199931e33806718fa07a`.
- CLI SHA256 `54b43378e2de704d16e7cc0d0c5370e7b08c4b3d88e816be965686c092ce5717`.

새 ROM 리소스가 필요 없는 RAM helper 단위다. 후속49fc6 animation, 전체 stage callback, 자연 scheduler/IRQ, 직접 플레이와 전체 게임 복원은 미완료다. 기존 목표와 완료 기준을 유지한다.

## 후속 object 출력 분석

16ea4의 SWAP/WORD 덧셈/LSR→SUBX와 cd58 tail 호출, 47672의 sound 대기와 live alias WORD lookup 계약을 기록했다. 메인은 새 native observer를 읽고 원본 프로그램 불변 검사, 전체15register 경계 capture, RAM write replay와 같은 CPU의 wait/hold/release를 확인했다. native 관측을 C++ wrapper 완료로 취급하지 않는다. 새 wrapper 구현·비교는 다음 단위다.

별도 Sol의 읽기 전용 감사는96조건/112단계/8같은CPU 연쇄, RAM쓰기204회와112개 RAM파일 및 입력/oracle 해시를 확인했다. 대표9조건(연속대기4연쇄 포함)을 메모리에서 재실행해 전체 상태가 일치했다. 모든6개 callee 분기의 양쪽 경로를 관찰했다. source.json은 원본 bytes와 직접 대조했지만 native 보고서 입력 목록에 해시가 없으므로 후속 C++ verifier에서 별도 해시를 기록한다. Native SHA256 `49b4e745f9243d6c6b044e81327c7cbaa5122c2d051d8bdfe9734793ea95c525`.
