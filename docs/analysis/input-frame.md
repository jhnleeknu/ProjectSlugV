# f12 입력 호출자 경계

원본 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
명령 주소는 고정 ROM CPU 주소와 복호화 프로그램 오프셋이 같다. RAM 오프셋은100000 기준이다.

`begin_input_frame`은 f12 진입부터 f54 또는 f3c 직전까지 구현한다. 먼저0016을001a로 복사하고0016과4ca2.word를 지운다.31d6 입력 샘플러와b68 후처리를 순서대로 실행한 뒤 오브젝트+76의long을 읽는다.0이면f54로, 그 외에는f3c로 진행한다. callback이 있을 때의 오브젝트+7a long도 후속 호출 준비 정보로 반환한다. 이는 원본 주소값이며 호스트 함수 포인터가 아니다.

오브젝트 필드는 입력 갱신 이후에 읽는다. RAM 갱신 영역과 오브젝트 필드가 겹치는 경우에도 이전 포인터를 미리 저장해서 사용하지 않는다. API는64KiB RAM과 완전한0x7e바이트의 짝수 오브젝트 주소 범위100000..10ff82를 요구한다. 전체 호출은 실패 시 RAM/result를 보존한다.

## D1.word 전달

기존 표시 함수의 style 입력은 D1.word다.31d6의 각 입력 블록 처리는 D1의 하위 바이트를 새 눌림 비트로 바꾼다. 마지막 P2 게임 블록 처리 후 D1.byte는 RAM4cb1과 같다. 모드0 또는2 이상의 처리에서는 D1의 상위 바이트를 보존한다.

모드1의352a는 이벤트를 토글할 때3580에서 D1.word에 생성 입력word를 읽고3586에서 비트를 바꾼다. 따라서 마지막 토글 직후의 생성 입력 상위 바이트가 반환 D1의 상위 바이트가 된다. 이벤트 없이 기다리거나 이미 종료된 커서로 진입한 경우에는 초기 D1 상위 바이트를 유지한다. 이후 반복 파싱의 D1.byte 변경은 이 상위 바이트를 덮지 않는다. 최종 생성 입력word만으로 D1 반환값을 재구성하면 이벤트 없는 경로에서 틀린다.

`sample_input`과`step_input`에 선택적인 입력/출력 style 포인터를 추가했다. 기존 호출 형식은 유지하며, 실패하면 style도 보존한다. b68은D1을 수정하지 않는다. D3는 이 경로에서 변경되지 않는다. 다른 CPU 레지스터·CCR 및 외부 스택은 이 API의 반환 계약이 아니다.

빌드: `make build/begin_input_frame`.
CLI: `build/begin_input_frame INPUT_RAM STREAMS_MS5D TABLE_MS5D OUTPUT_RAM OBJECT_ADDRESS STYLE SYSTEM P1_RAW P2_RAW P1_GAME P2_GAME`.
원본 비교: `.venv/bin/python tools/verify_input_frame.py`.

반환 결과는next_pc,callback,callback_context,style,read_count다. callback이0이면callback_context는0으로 반환한다. f3c 경계에서는 아직 A6를 스택에 저장하거나+7a로 바꾸지 않았으며 callback을 실행하지 않는다. f54 경계에서도 아직9136을 호출하지 않는다. 앞선ec4 대기·video counter 읽기 및 전체 interrupt/scheduler가 복원된 것으로 해석하지 않는다.

## 검증 결과와 다음 callback 근거

원본f12 실행437조건(독립237+승계200)에서 전체64KiB RAM, 정확한D1.word, 분기 경계·callback 정보·MMIO read count가 일치했다. 실제 재생 이벤트48조건과 비이벤트94조건을 구분해 관측했다. D3 전체, A6 오브젝트 주소와 A7 진입 스택은 두 경계에서 보존됐다. 오류·파일 별칭16조건은 출력을 보존했다. 원본ROM 불변을 확인했다.

보고서: `artifacts/input_frame/verification.json`.
SHA256: `d6febf3d169511624a0a354ee9740c5ce74c38f6dbdd6cc1fd2d391798951fc1`.

후속 정적 근거로e40은 A0를100896에, e44는 A6를10089a에 저장하고e48에서 반환한다(A5=108000). 이는 루트 오브젝트100820의+76/+7a다. 초기화e60은 현재 A6의+76을0으로 지운다. callback 설정 함수의 존재와 실제로 해당 함수가 실행되는 호출 경로는 구분해야 한다. 현재 callback 경계 지원은 임의 원본 주소의 실행 지원을 뜻하지 않는다.
