# 애니메이션 상태 선택 표시 opcode10

프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
아래 주소는 고정 ROM의 CPU 주소이며 파일 오프셋과 같다.

원본 handler `4a22c..4a272`는 opcode 뒤 selector byte, 목록 길이 BE16을 읽는다. `4a76c + selector*2`의 BE16을 signed 필드 오프셋으로 해석하고 A6 오브젝트의 해당 바이트를 읽는다. MOVE.B는 레지스터 워드의 상위 바이트를 유지하므로 `index_word=(field_offset&ff00)|field_byte`이다. 워드를 3비트 좌측 이동한 결과를 16비트로 잘라 offset을 얻는다.

`offset >= length`의 unsigned 비교가 참이면 표시를 생략한다. 아니면 `list_base + signed16(offset)`의 opcode가 04인지 확인하고 뒤 7바이트를 기존 draw handler `4a10c`에 전달한다. 다른 opcode는 원본에서 TRAP #15이며 C++에서는 오류와 rollback으로 처리한다. 두 경로 모두 `list_base + signed16(length)`에서 계속한다. 이 명령 자체는 오브젝트의 저장된 스크립트 포인터를 갱신하지 않는다. 길이의 8배수 여부를 강제하지 않는다.

실제 스크립트 `65f64`의 prefix는 `10 1e 00 28`이다. selector30은 오브젝트+7d이며 40바이트 목록의 5개 draw 중 하나를 선택한다. 앞선 callback14/1e도 +7d를 읽는다. 이 대응은 동일 상태를 사용하는 근거이며 아직 전체 스크립트의 자연 게임 실행 검증은 아니다.

C++는 `step_animation_with_data`에서 필드 테이블을 MS5D로 읽는다. 선택한 항목과 후속 명령은 제공한 스크립트 범위 내에서 읽는다. 누락된 데이터, 범위 초과, 잘못된 선택 opcode, producer 대기는 RAM과 carry를 보존하며 실패한다. 그래픽 변환본 PNG를 실행 입력으로 사용하지 않는다.

검증:

- `.venv/bin/python tools/analyze_animation_indexed_draw.py --cpp`: 제어된 5개 항목, 256 상태×3 타이머=768조건. 원본 draw 진입의 A1 주소, 저장 포인터, 전체 RAM, carry 비교 성공.
- `make all test`: Python55 및 C++ 검사 통과. 추가 indexed draw의 범위 생략, 잘못된 선택 opcode, 잘린 데이터 rollback, 상위 바이트 유지 단위 검사 통과.
- `.venv/bin/python tools/verify_animation_pipeline.py --rom-script`: 기존 ROM 루프96호출·192비디오단계 일치.

768조건은 실제 selector30을 사용한다. 모든 signed 길이·필드 오프셋 조합, 다른 selector의 자연 사용, 실제65f56 전체 경로와 전체 게임은 검증하지 않았다. 원본 높은 오프셋 비트 유지 규칙은 명령 의미에서 도출했으며 별도 C++ 단위 검사로 고정했다.
