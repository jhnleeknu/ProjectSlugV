# 콜백 후 프레임 대기 연결 리뷰

대상 기준 커밋: `43c8a8e`.

메인이 f46..f52의 원본 명령과 API/CLI diff를 확인했다. f4c의 조건은 신호 byte가0이 아닌지이며 ef2의 임계값·비디오 처리를 재사용하지 않는다. waiting 경로는 리소스나 오브젝트를 사용하지 않고 결과를 초기화하며 ready 경로는 기존 트랜잭션 API로 전달한다. 팔레트 tick은 대기 전에 한 번 실행하고 반복 poll에서 다시 실행하지 않는다.

- `make all test`: Python73개 및 C++ 전체 검사 통과, 경고 없음. 로그 `artifacts/callback_frame_flow_build_test.log`.
- 단위 검사에서 threshold0/signal0 대기, threshold255/signal1 진입, RAM18 보존과 실패 시 RAM·결과·포트 보존을 확인했다.

- `.venv/bin/python tools/verify_callback_frame_flow.py`:537조건, 포트286개 및 오류5조건 통과. 전체RAM/입력읽기/결과/포트를 비교하고 스택단계는 전체스택/16레지스터도 비교했다.
- 네 가지 팔레트 경로의D1 전달 및 기본콜백의 실제RTS부터 다음IRQ신호 소비까지 연결했다. 팔레트 전후 A5/A6/A7 보존을 메인 리뷰에서 보강했다.
- 일반 controller가5728을 호출할 수 있으므로 palette_calls=0 검사를 대기/콜백 경계에 한정했다. 초기행렬 신호와 실제IRQ생성 신호를 보고서에서 구분했다.
- 보고서 SHA256 `cc6c268073de463fd30f29c40171d8d021268274622735763c9333994950852d`.

전체 CPU/SR/RTE/BIOS·장치 시간축과 임의 콜백 본문 실행은 이 API의 검증으로 완료를 주장하지 않는다.
