# 슬롯 설정·비활성 영역 리뷰

대상:f6e4cda 이후 변경. 이전 turn은 생성기 및 연속 pipeline 구현·원본 비교·커밋으로 진척이 있었다.

발견: 초기화가 만드는 all-ffff 슬롯 영역을 기존 dispatcher가 invalid로 거부했다. 원본0xcd1c와 실제0x44086 호출부를 추적하고 비활성 영역의 준비·갱신을 원본 CPU로 먼저 확인한 뒤 수정했다.

- setter는 unsigned16 비교와 비정상 인자에 대한 sentinel 변환까지 원본대로 보존한다. 지원할 수 없는 혼합 상태는 setter가 임의 수정하지 않고 dispatcher에서 거부한다.
- 정확히4word 모두ffff일 때만 비활성 예외를 허용한다.
- 비활성 레코드도 payload 검증은 유지하고 current에 emitter의 빈 영역 결과0을 저장하지 않는다. 정리 루프는 쓰기0회다.
- C++ source/diff/CLI와 테스트를 메인 에이전트가 리뷰했다.
- setter192조건, 비활성 준비96 및 후속 refresh96, 별도 refresh96조건의 원본RAM·비디오 일치.
- 활성/비활성 pipeline 각각124제출+32단계 원본 일치. 실험용 수동 pool word를 setter 호출로 대체했다.
- make test 통과.

실제 화면 모드의 전체 슬롯 배분, 대기 재개, IRQ/타이밍, 다른 표시 분기와 전체 게임 복원은 남아 있다.
