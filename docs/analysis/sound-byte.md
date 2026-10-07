# 사운드 byte 생산과 대기 재개

원본 복호화 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 매핑 CPU 주소와 ROM 오프셋은 같다. 대상은 `3ac8..3af8`이며 재개 지점은 `3aea`다.

`enqueue_sound_byte`는 D0의 하위 byte를 명령으로 받는다. 명령3이면 RAM4d7b를ff로 설정하고 인덱스를 읽지 않는다. 나머지는 RAM4d76의 tail을 읽어 쓰기 주소4cf4+tail을 A0에, 다음 인덱스 `(tail+1)&127`을 D1.word에 잡는다. 다음 인덱스가 RAM4d74의 head와 같으면3aea에서 기다린다. 공간이 생기면 캡처한 주소에 명령을 쓰고 다음 인덱스를 tail로 저장한다. 하드웨어 포트 쓰기는 없다.

C++은 호스트를 무한 대기시키지 않고 `SoundBytePending`에 waiting/command/tail/next를 반환한다. `resume_sound_byte`는 이 상태를 받아 live head만 다시 확인한다. 대기 중 RAM tail이 바뀌어도 원본 A0/D1처럼 캡처한 쓰기 위치를 유지한다. 완료 시에도 캡처 필드를 유지하고 waiting만 false가 된다. 명령3의 출력은 waiting=false, command=3, tail=next=0이다.

지원 범위는 정확히64KiB RAM과 사용되는 인덱스0..127이다. 일반 진입은 head/tail을 검사하고 재개는 캡처 상태와 live head를 검사한다. 사용하지 않는 live tail은 재개 시 검사하지 않는다. 명령3은 인덱스 검사를 우회한다. 잘못된 상태는 오류이며 RAM과 pending을 보존한다. 새 진입은 새 작업의 출력 상태를 만든다. 호출자는 대기 중인 작업의 상태를 보관하고 재개 API로 이어야 한다.

CLI:

```sh
build/enqueue_sound_byte INPUT_RAM OUTPUT_RAM COMMAND
build/enqueue_sound_byte --resume INPUT_RAM OUTPUT_RAM COMMAND TAIL NEXT
.venv/bin/python tools/verify_sound_byte.py
```

전체 RAM과 pending을 원본523조건에서 비교했다. 모든256개 command와128개 tail 위치, 준비/대기/랩어라운드, 명령3의 인덱스 우회를 포함한다. 대기 결과는260건이다. 두 시퀀스는 원본 생산자 CPU 문맥을 저장하고 같은 RAM에서 실제3cb2 소비자를 실행한 뒤 문맥을 복구하여 생산자를 재개했다. 소비자의 RAM과 포트도 C++과 비교했다. 별도 호스트 tail 변경 실험은 캡처 위치 보존을 검증한다. 이것이 자연적인 동시 실행이나 실제 인터럽트 스케줄링의 증거는 아니다.

실패/파일 별칭16조건의 출력 보존과 원본 ROM 불변을 확인했다. 보고서: `artifacts/sound_byte/verification.json`, SHA256 `82b65cd0bb99ff12816f0d936a12bf5bcca594c381176ab945e28c8d441a374d`.

48156/3af8/3c08의 상위 생산자, 자연 호출자의 재개 순서, 전체 CPU 레지스터/플래그, Z80 명령 실행과 오디오 시간축은 미완료다. 특히3cac는48156 생산자를 먼저 호출하므로 같은 호출 안의 소비자가 자동으로 모든 대기를 해소한다고 가정하지 않는다.
