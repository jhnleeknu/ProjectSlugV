# 표시 생성기 및 연속 흐름 리뷰

대상:8229d2b 이후 변경. 이전 turn은 준비→갱신 연속 구현·원본 검증·커밋으로 진척이 있었다.

메인 에이전트가 기존48개 단일 제출 근거를 확장해 초기화8개, 생성192개를 원본 CPU로 검증한 뒤 구현을 위임했다. C++ source/header/CLI/tests를 읽고 통제된4개 연속 시퀀스를 원본과 비교했다.

- 초기화는 방향 byte와 레코드를 보존하며 pools를0xffff로 둔다. 준비 완료 구성으로 오해하지 않는다.
- callback이 원본에서 clip보다 앞서 호출되므로 기본 RTS 주소인지 먼저 검증한다. 다른 callback을 무시하지 않고 거부한다.
- 좌표 packing의 uint32 shift/OR 및 하위16bit wrap을 보존한다.
- full 검사 뒤에만 선택된 record/deferred 공간을 검증하고, malformed 상태로 실제 쓰기 전에 실패한다.
- Waiting은 원본0xcda4 첫 진입에서 확인했다. 스핀 재개/시간 동일성을 주장하지 않는다.
- `verify_sprite_producer.py --cpp`: 초기화8개+제출192개64KiB RAM 전체 및 상태 일치.
- `verify_sprite_pipeline.py`:4시퀀스×4회 연속 처리,124제출+32준비/갱신 단계 전체 RAM·비디오 일치.
- make test 및 입력 오류 시 상태 보존·별칭 출력 거부 검사 통과.

남은 항목: 기본 콜백 이외 변환, 대기 타깃 캡처·재개, 실제 IRQ/frame timing, flip/다중블록, 픽셀·전체 게임·사운드다. 합성 fixture의 deferred 저장 상한256개 검사는 실제 소비 없는 생산 한도255개와 구별한다.
