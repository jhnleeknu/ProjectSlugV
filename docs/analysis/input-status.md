# b68 입력 상태 후처리

원본 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
이 문서의 코드 주소는 고정 ROM CPU 주소이며 복호화 프로그램 파일 오프셋과 같다. RAM 오프셋의 기준 주소는100000이다.

원본 b68..bb4는 fdaf 바이트를0012로 복사하고 f007을 지운다. f006의 비트3부터0까지 차례로 지우며, 이전에 켜져 있던 비트에 대응하는 fdb6..fdb9 슬롯을1로 바꾼다. 각 슬롯은 D6.word=4에서 슬롯 값을 D6.byte에 더한 인덱스로 b58의 데이터를 읽는다. 읽은 값이0이 아니면 해당 비트를 결과에 켠다. 최종 결과를 f007에 저장한다. f006의 상위4비트는 남고, 슬롯은 해당 요청 비트가 없으면 이전 값을 유지한다.

ADD.B의 결과로 조회 인덱스는 `(4 + slot_byte) & 255`다. 251은255를,252는0을 조회한다. 앞의 작은 표만 추출하거나 슬롯을 clamp하면 원본과 달라진다. b58..c58 전체256바이트를 보존하며, 이 창은 b68 이후 명령 바이트와 겹친다. 모든 슬롯 값이 자연스러운 게임 상태에서 나타난다는 주장은 하지 않는다. 후처리에서 슬롯의 실제 의미를 충분히 추적하기 전까지 플레이어 상태 등의 이름을 단정하지 않는다.

`tools/pack_input_status.py`는 기존 MS5D v1 kind1 규격으로 `input_status.ms5d`를 생성한다. 전체 프로그램과 payload 해시를 고정하고 원본 주소를 manifest에 남긴다. 안정 ID는 `input-status:00000b58`다. C++은 추출 바이트를 직접 조회한다.

- payload256바이트 SHA256: `3a9b0abce59ff1b1b9f93b2d729519def993bd1e9ca3a3b0655c1d2fefc9b756`
- MS5D288바이트 SHA256: `14ea9e73e6089df26586b8b678f34d99c6b4bb7fdfaae0516ddc34fa76b31bd4`

`update_input_status`는64KiB RAM과 정확한 b58..c58 창을 요구한다. 검사가 끝난 후 RAM을 변경한다. `step_input`은 기존31d6 샘플러 뒤에 이 후처리를 호출하고, 어느 쪽이든 실패하면 RAM과 read_count를 모두 보존한다. CPU 레지스터·CCR 출력과 물리적 포트 시간축은 모델링하지 않는다.

재생성: `python3 tools/pack_input_status.py`.
빌드: `make build/update_input_status`.
독립 호출: `build/update_input_status INPUT_RAM TABLE_MS5D OUTPUT_RAM`.
통합 호출: `build/update_input_status --sample INPUT_RAM STREAMS_MS5D TABLE_MS5D OUTPUT_RAM SYSTEM P1_RAW P2_RAW P1_GAME P2_GAME`.
원본 비교: `.venv/bin/python tools/verify_input_status.py`.

통합 호출은31d6→b68 순서를 구현한다. ec4의 인터럽트 대기, f12 앞의 갱신 신호 초기화, 이후 오브젝트 callback과 컨트롤러까지 실행한 것은 아니다. 다음 연결에서는 CPU 반환 레지스터와 호출자 메모리 의존성도 별도로 확인해야 한다.

## 다음 호출 경계에서 확인한 의존성

f12는0016을001a로 복사한 뒤0016과4ca2.word를 지우고 f24에서31d6, f2a에서b68을 호출한다. 이어 오브젝트+76의 callback 주소가0이면f54 컨트롤러로 진행한다. callback이 있으면 A6를 오브젝트+7a로 바꾸어 호출하고 원래 A6를 복구한 뒤5728 팔레트 갱신,0016 비영 대기, f12 재진입 순서다.

c8c 인터럽트 처리의 일부만 카운터 증가 함수로 대체해서는 전체 호출을 복원했다고 볼 수 없다. c8c는0019.bit7 재진입 방지,0016의 포화 증가와 watchdog 이후bbe를 호출하며,001b와f001에 따라 추가 처리·작업 스택 복구를 수행한다. 마지막에는3cac 사운드 처리까지 호출하고0019를 지운다. 바깥20c handler에는 RAM0006의 간접 callback, BIOS c0044a, PVC/VRAM 주소 복구와3c0006 읽기도 있다. 이 의존성을 검증하기 전에는 입력 호출자 경계와 인터럽트 전체를 분리해 다룬다. 명령 주소와 호출 순서에 대한 정적 확인이며 실시간 interrupt 동작 검증은 아니다.

## 실행 검증

원본b68과 독립576조건,31d6→b68 승계160회에서 전체64KiB RAM과 CLI 결과가 일치했다. 모든 슬롯byte·pending byte·fdaf byte를 포함하고, 비트 강제 설정과 상위pending 보존, 인덱스wrap을 확인했다. 통합 시퀀스는 모드0/1/2와 재생종료1→2 각각40회다. 오류·파일 별칭12조건에서 기존 출력을 보존했다. 원본 고정ROM 불변도 확인했다.

보고서: `artifacts/input_status/verification.json`.
SHA256: `79b0545c0473095e2c9b3364d67d30990ee248cb06cbc2df422b6c7e4795f5c1`.
