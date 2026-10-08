# 전체 사운드 byte 제출과 대기 재개

원본 canonical BE 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 고정 ROM CPU 주소 `0x3ac8..0x3af7`은 같은 파일 오프셋에 대응한다. RAM 주소는 ROM 오프셋이 아니다.

## 원본 계약

`0x3ac8`은 D0의 하위 byte가 3이면 RAM `0x104d7b`에 ff를 쓰고 레지스터를 보존한 채 반환한다. 나머지는 WORD tail(`0x104d76`)을 부호 확장해 `0x104cf4`에 더한 주소를 A0에 저장하고 D1 하위 WORD에 `(tail+1)&127`을 기록한다. D1 상위 WORD는 보존한다.

`0x3aea`는 D1 하위 WORD와 live head(`0x104d74`)가 같으면 대기한다. 달라지면 D0 하위 byte를 A0에 쓰고 D1 하위 WORD를 tail에 기록한다. 이 순서는 목적지가 head/tail과 겹쳐도 유지한다. 대기 재개 때 tail이나 주소를 다시 계산하지 않는다.

`SoundByteExecutionState`는 D0..D7, A0..A4 및 waiting을 보존한다. A6는 사용되지 않으며 CLI가 그대로 전달한다. A5는 원본 비교에서 `0x108000`으로 고정한다. C++ API는 호출 스택을 추상화한다. 원본의 대기/반환 PC와 A7은 비교 도구가 별도로 확인한다.

논리적인 tail 0..127 제한을 추가하지 않는다. signed WORD 인덱싱으로 계산된 실제 쓰기 주소가 64KiB RAM에 속해야 한다. 쓰기 전 대기할 때에는 RAM 밖의 주소도 보존할 수 있다. 오류가 나면 RAM, 레지스터와 waiting을 모두 유지한다. 이 오류 정책은 RAM 밖 장치/ROM 동작을 재현한다는 뜻이 아니다.

## 실행 및 검증

```
make build/execute_sound_byte build/sound_byte_execution_test
./build/sound_byte_execution_test
.venv/bin/python tools/verify_sound_byte_execution.py
make test
```

CLI 인자는 `D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 WAITING INPUT_RAM OUTPUT_RAM`이다. RAM 파일은 65536바이트이며 입력과 출력은 서로 달라야 한다. 출력 JSON에 레지스터와 waiting이 반환된다. 재개에는 직전 출력 RAM 및 상태를 전달하며 외부 소비자의 head 변경을 적용한다.

pinned Musashi에서 수정하지 않은 원본과 실제 C++ CLI를 564단계 비교했다. 548회 신규 진입과 16회 재개이며, 9개 체인에서 같은 CPU를 유지했다. 7개는 대기 시작·tail 변경 후 대기 유지·head 변경 후 재개를, 2개는 head 상위 byte 변경만으로 재개되는 것을 확인했다. 전체 RAM, 14개 레지스터와 waiting이 일치한다. 두 조건 분기 각각 양쪽 경로를 확인하고 원본 RAM 쓰기 순서를 재생해 snapshot과 비교했다. 고정 ROM 불변과 입력 파일 보존도 확인한다.

모든 byte 명령, wrap, signed tail, head/tail alias를 포함한다. CLI의 RAM 밖 쓰기 4조건은 출력 파일을 보존하며 거부된다. 잘못된 주소의 원본 실행으로 ROM을 쓰는 fixture는 사용하지 않는다. API 단위 테스트는 지연된 주소 오류와 RAM 크기 오류의 원자성을 확인한다.

전체 빌드/테스트 기록 `artifacts/sound_byte_execution_build_test.log`: Python 182개, C++ 128개, 경고 0. 검증 결과 `artifacts/sound_byte_execution/verification.json` SHA256은 `90428c4bf9aacb97adb28b37b7d95aaf019427e1086bd3bca96e991aab041408`, CLI SHA256은 `9936913fae7569a3863a7c8f6569f28ace4724e829ab723936cef0ddb6826ee8`이다.

## 남은 범위

이 루틴은 RAM 큐에 명령을 제출한다. 새로운 런타임 리소스나 확인용 오디오를 생성하지 않는다. 전체 CCR, IRQ 타이밍, 실제 사운드 재생 및 자연 scheduler 실행은 이 검증에 포함하지 않는다. 상위 `0x3af8`, `0x3c44`, `0x2efa6`의 전체 레지스터·대기 연결과 전체 `0x480bc` 통합은 후속 작업이다. 기존 제한된 sound_word API의 검증과 이번 전체 byte 계약을 구분한다.
