# 사운드 WORD 명령 전체 실행

Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`의 고정 ROM CPU `0x3af8..0x3c07`을 대상으로 한다. CPU 주소와 파일 오프셋이 같다. 원본 명령 목록은 `artifacts/sound_frame_source.json`, 해석 계약은 `docs/analysis/stage-sound-frame-contract.md`에 있다. 하위 `0x3ac8`은 기존 전체 byte 실행 API를 사용한다. 아래 실행 계약을 실제 CLI와 수정 없는 원본 실행으로 검증했다.

## 필터와 외부 입력

D0.low WORD가 unsigned `0x2000` 이상이거나 D0.byte가 `0x20` 미만이면 레지스터를 바꾸지 않고 반환한다. 통과하면 D1.low에 D0.low를 복사하고 D1.byte를 0으로 만든다. D1.low가 `0x0100`, `0x0300`, `0x0200`이면 반환한다. D1 상위 WORD는 보존한다.

RAM `0x100012`가 1이면 D1.low==0을 거른다. 그 외 명령에서는 RAM `0x10fd82`가 비영이고 `0x10fe80`이 0일 때만 외부 장치 `0xd00046`의 byte를 읽으며 비영이면 반환한다. 이어 `0x10fd8d`가 0이면 반환한다. RAM `0x100012`가 1이 아니면 이 추가 필터들을 건너뛴다. 별도 필터로 `0x104d7e`가 비영이고 D0.low가 unsigned `0x1000` 이상이면 반환하며, `0x10f001` bit5가 설정되고 D1.low==0이면 반환한다.

`external_status`는 이 조건부 장치 읽기에 제공하는 byte 입력이다. `external_reads`는 이번 호출의 읽기 횟수다. 외부 장치 전체나 IRQ timing을 구현한 것은 아니다. 대기 재개에서는 필터와 외부 입력을 다시 읽지 않는다.

## 큐와 overflow 제출

A0=`0x104d82`, D1.low=WORD head(`0x104d8a`)로 시작한다. 매 반복에서 live WORD tail(`0x104d8c`)과 비교한다. 다르면 A1=A0+signextend(D1.low)를 캡처하고 D1.low=(D1.low+2)&6으로 갱신한다. WORD(A1)이 입력 D0.low와 같으면 다음 인덱스를 live tail과 비교한다. 같으면 쓰기 없이 반환한다. 다르면 다음 WORD를 A1에 복사하고 D0.low를 다음 WORD에 쓰고 반환한다. 따라서 중복은 발견한 위치에서 다음 슬롯과 교환하며 끝까지 순회해 재배열하지 않는다. 불일치면 다음 반복으로 간다. 빈 큐는 A1을 보존한다.

tail에 도달하면 WORD(A0+signextend(D1.low))=D0.low, 다음 인덱스 계산, tail 게시 순서로 실행한다. 새 인덱스가 live head와 다르면 반환한다. 같으면 A0를 새 인덱스 주소로 바꾸고 다음 인덱스를 계산해 head에 게시한다. WORD(A0)가 0이면 반환한다. 비영이면 첫 byte를 D0.byte로 읽고 A0를 증가시킨다. 다음 byte는 저장하고 A0를 다시 증가시킨 뒤 첫 byte를 `0x3ac8`로 제출한다. 완료하면 저장한 byte를 D0.byte로 복원하여 `0x3ac8`로 tail call한다. 두 제출은 각각 대기할 수 있다. D0의 byte 변경은 상위 24비트를 보존하며, byte helper의 A0/D1 효과까지 결과에 포함한다.

`SoundWordExecutionState`는 byte helper 상태, `saved_low`, `phase`를 가진다. phase0은 신규 호출이며 byte.waiting=false, phase1/2는 각각 첫/둘째 byte 제출의 재개이며 byte.waiting=true를 요구한다. 재개에서는 큐 스캔·overflow·이미 완료한 제출을 반복하지 않는다. `saved_low`는 원본 스택의 저장 byte를 추상화한다. A5는 원본 `0x108000` 고정이고 A6는 CLI에서 그대로 보존한다. A7/반환 주소와 CCR은 이 API의 상태 출력에 포함하지 않는다.

WORD 접근은 실제 64KiB RAM 범위와 짝수 정렬을 요구한다. 초기 인덱스는 signed WORD로 해석하며 네 슬롯만 허용하는 제한을 두지 않는다. 잘못된 live tail 때문에 끝나지 않는 스캔은 오류로 구분하고 정상 반환으로 처리하지 않는다. 검증/API 오류는 RAM과 실행 상태를 보존해야 한다. 이는 장치 영역이나 CPU 주소 오류 예외를 에뮬레이트한다는 뜻은 아니다.

## 재현

```
make build/execute_sound_word build/sound_word_execution_test
./build/sound_word_execution_test
.venv/bin/python tools/verify_sound_word_execution.py
make -j3 all test
```

CLI는 다음 인자를 받는다.

```
build/execute_sound_word D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 WAITING PHASE SAVED_LOW EXTERNAL INPUT_RAM OUTPUT_RAM
```

레지스터는 unsigned32bit, WAITING은0..1, PHASE는0..2, SAVED_LOW와 EXTERNAL은0..255의 십진수 또는 `0x` 16진수다. 부호·공백·범위 밖 값은 오류다. 입력 RAM은 정확히65536byte여야 한다. 입력/출력은 경로 및 inode가 달라야 하며 동일 파일을 가리키는 symlink/hardlink도 거른다. 인자·입력·API 오류에서는 기존 출력파일을 열지 않아 보존한다.

JSON은 D0..D7, A0..A4, A6의14개 레지스터와 `waiting`, `phase`, `saved_low`, `external_reads`를 출력한다. 출력 RAM 및 레지스터/waiting/phase/saved_low를 다음 호출에 전달해 재개한다. EXTERNAL은 각 호출에 명시적으로 제공한다.

## 검증 기록

`artifacts/sound_word_execution/verification.json`에서 원본 Unicorn 실행과 실제 CLI의2560단계 전체64KiB RAM/14개 레지스터/대기 상태/조건부 외부 읽기를 비교했다. 그중12단계는 Musashi와도 일치했다. 22개 조건분기의 양쪽, 8개 동일CPU 대기 체인, signed 초기 주소·live alias·중복 이동·overflow·zero 및 byte 특수값을 포함한다. A5/A7와 원본 저장 스택을 확인했으며, ROM은 수정하지 않았다. 98개 오류 입력에서 입력과 기존 출력파일의 보존을 확인했다. 대기 해제는 합성 host 입력이며 자연 IRQ/scheduler 동작의 검증으로 확대하지 않는다.

보고서 SHA256 `e8d035a20eaf7a24500ded9945be71a97d8ae59c8e5507622cf0d24319eda0bd`; 검증 당시 CLI SHA256 `2117feccf6966a51fafbd086a95c9f3bd93c53f103251634780f8ec951db7a17`. `artifacts/sound_word_execution_build_test.log`의 전체 빌드·테스트는 Python182개/C++130개, 컴파일 경고0으로 통과했다.

새 리소스는 필요하지 않다. 이 단위는 RAM 사운드 명령 생산·byte 제출의 복원이며 오디오 재생 완료가 아니다. 전체 CCR/IRQ timing, 실제 외부 장치, `0x3c08` 배출 전체 상태, `0x2efa6` 호출자는 별도 [stage sound frame 문서](stage-sound-frame.md)에 기록했다. `0x480bc` 통합과 자연 scheduler/직접 플레이는 남아 있다.
