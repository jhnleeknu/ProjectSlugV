# 사운드 타이머·생산·소비 통합

원본 복호화 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 CPU 주소3cac와 ROM 오프셋3cac는 같다. `step_sound`는3cac의48156 호출과 이어지는3cb2 소비를 연결한다. word/byte 생산자의 기존 대기 상태를 그대로 사용한다.

## 실행 순서

RAMd68c의 timer word가0이면 생산자를 건너뛴다. 나머지는 signed 비교로15 이하이면 RAM word를1 증가시키고, 양수16..32767이면0으로 만든다. 명령은 증가 전 값에19c0을 더한 word이며 초기화 경로는19c0이다. 이 명령을3af8 규칙으로 전달한다. 타이머를 갱신했어도 명령 필터에서 거를 수 있다.

생산자가 가득 찬 byte 큐에서 기다리면 해당 호출은 pending을 반환한다. 이때까지 수행한 timer/word 큐 변경은 남지만3cb2 소비는 아직 실행되지 않는다. 반환 read_count는0이고 포트 출력은 비어 있다. 같은 호출의 소비자를 먼저 실행해 대기를 임의로 해소하지 않는다.

생산이 끝나면3cb2를 실행한다. supplied sound_status를 한 번 소비하여 read_count=1을 반환하고, 우선 명령 또는 일반 큐에 따라0개나1개의320000 byte 쓰기를 낸다. read_count는320000 상태 읽기 수이며 조건부d00046 입력 읽기 수를 포함하지 않는다.

`resume_sound`는 kind1의 보류된 overflow 생산자만 받는다. 기존 byte/word 재개부터 이어가므로 timer와 external_status를 다시 취득하지 않는다. 소비자에 도달할 때의 sound_status를 전달해야 하며 원래 대기 시작 시점의 상태를 저장해 사용하지 않는다. 계속 기다리면 read_count=0이다. 완료 시 pending은 전부0으로 초기화된다.

오류는 해당 API 호출 전체의 RAM/pending/read_count/ports 변경을 취소한다. 따라서 생산은 성공했지만 뒤의 소비기가 잘못된 인덱스를 발견한 경우 timer 증가와 word 추가도 취소된다. 오류가 아닌 정상 대기는 원본의 부분 진행 상태를 보존한다. 새 step 호출은 새 실행을 시작하므로 호출자는 보관한 pending을 resume에 전달해야 한다.

```sh
build/step_sound step INPUT_RAM OUTPUT_RAM OUTPUT_PORTS EXTERNAL STATUS
build/step_sound resume INPUT_RAM OUTPUT_RAM OUTPUT_PORTS STATUS KIND PHASE LOW CURSOR COMMAND TAIL NEXT
.venv/bin/python tools/verify_sound_service.py
```

포트 파일의9바이트 기록(size byte, address BE32, value BE32)은 검증용 실행 기록이다. 런타임 리소스는 기존 C++ 바이너리 규격을 유지한다.

## 검증 범위와 남은 연결

검증기는 원본3cac부터48156/3af8/3ac8/3cb2를 연속 실행한다. 대기 재개는 원본 CPU 문맥과 스택을 보존한다. 호스트에서 명시적으로 head/tail/timer를 바꾸는 실험은 캡처 상태와 재개 순서를 검증하며 자연적인 IRQ 스케줄링을 주장하지 않는다.

사운드 서비스의 CPU 레지스터/플래그 전체 출력, c8c/20c의 인터럽트 저장·복구, Z80 실행과 실제 오디오 시간축은 남아 있다. 다음 연결은 c8c의 credit/busy 분기 및 작업·렌더링 의존성과 사운드 서비스를 통합하는 것이다.

원본718조건의 전체64KiB RAM, pending/read_count와 포트 쓰기가 일치했다.672개 독립 조건과40회 연속 tick, 원본 문맥을 보존한 두 high-wait→low-wait→완료 시퀀스를 포함한다. 모든 status byte와 timer wrap에 따른 명령 필터를 확인했다.16개 오류/파일 별칭 조건은 기존 출력을 보존했다. 원본 ROM은 수정하지 않았다.

보고서: `artifacts/sound_service/verification.json`, SHA256 `a810b518f387d35e639579fb058a9ee657f77fb8036fd6d9d93449c872ef0f69`.
