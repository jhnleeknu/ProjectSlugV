# 사운드 취소 명령 전체 실행

Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`의 고정 ROM CPU `0x3c44..0x3c7b`를 재구성했다. CPU 주소와 파일 오프셋이 같다. 하위 `0x3ac8`은 기존 전체 byte 실행 API를 사용한다.

## 동작과 상태

D0 하위 WORD를 저장하고 WORD head(104d8a)에서 live WORD tail(104d8c)까지 큐를 순회한다. A1=104d82+signextend(index), 다음 index=(index+2)&6 순서이며, 명령과 같은 WORD를 지운다. 초기 signed 인덱스가 tail 자체를 가리키면 삭제가 다음 반복의 종료 조건을 바꿀 수 있다. 빈 큐는 A1을 보존한다. D1 상위 WORD를 유지한다.

스캔 후 D0 전체를14로 설정하여 byte 제출, 저장 명령의 상위 byte 제출, 저장 WORD를 D0.low로 복원해 하위 byte 제출을 수행한다. 각 제출은 독립적으로 대기할 수 있다. 상위/하위 byte가03이면 기존 byte 루틴의 우선 처리로 큐를 거치지 않는다.

`SoundCancelExecutionState`는 byte helper 상태, saved_word, phase를 가진다. phase0은 신규 호출이며 byte.waiting=false여야 한다. phase1/2/3은 각각 제출의 대기 재개이며 waiting=true여야 한다. 완료하면 phase와 saved_word는0이다. 재개는 스캔/저장/이미 완료한 byte 제출을 반복하지 않는다. 호출 스택은 상태로 추상화하며 원본 비교에서는 저장 WORD와 실제 반환 주소/A7을 별도로 확인한다.

WORD 읽기/삭제는 실제64KiB RAM 범위와 짝수 정렬을 요구한다. 논리적인 큐 인덱스만 허용하는 제한을 넣지 않는다. 반복 헤더의 (index,live tail) 재방문은 비종료 오류다. 초기 인덱스 이후 대상은 네 슬롯으로 제한되어 tail을 바꿀 수 없으므로 이 재방문 검출은 종료 가능한 스캔을 잘라내지 않는다. 모든 오류는 앞선 삭제를 포함한 전체 RAM/상태를 보존한다. RAM 밖 장치나 주소 오류 예외를 에뮬레이트한다는 뜻은 아니다.

## 재현

```
make build/execute_sound_cancel build/sound_cancel_execution_test
./build/sound_cancel_execution_test
.venv/bin/python tools/verify_sound_cancel_execution.py
make -j3 all test
```

CLI: `build/execute_sound_cancel D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 WAITING PHASE SAVED_WORD INPUT_RAM OUTPUT_RAM`. 입력/출력은 서로 다른65536byte 파일이다. JSON 결과 레지스터/waiting/phase/saved_word와 출력 RAM을 재개 입력으로 사용한다. A5는 원본108000고정, A6는 사용되지 않으며 CLI에서 보존한다.

원본 Musashi와 실제CLI의645단계 전체RAM/14register/대기 상태가 일치한다. 명령의 각 byte256값, 큐head/tail16조합, signed 초기 주소와 live tail alias, 10개 동일CPU 대기 체인을 포함한다. 9개 체인은 각 제출 위치에서 hold/release, 1개는 세 제출에 연속으로 대기한다. 정상 원본4조건분기의 양쪽을 확인했다. 원본 RAM쓰기 순서 재생, ROM 불변, A5/A7/저장 스택과 입력파일 보존을 확인한다. CLI 오류7조건은 기존 출력파일을 보존한다. API 단위 테스트에는 삭제 후 오류와 대기 해제 후 오류의 transaction이 포함된다.

검증 보고서 `artifacts/sound_cancel_execution/verification.json` SHA256 `ba58107375f806997f837dce4d302a761c39f2be427e7b9b74fe39f920a67919`; CLI `2508c7f6b0fef8184a1a2e5e058c7c1b4e522aea03ac5f5b08b58eded13d3b3b`. 전체 테스트 Python182/C++129/경고0.

새 리소스는 필요하지 않다. RAM 명령 제출이며 오디오 재생 완료가 아니다. 전체CCR/IRQ timing, 3af8전체 레지스터, 2efa6 및480bc 통합과 자연scheduler/직접플레이는 남아 있다.
