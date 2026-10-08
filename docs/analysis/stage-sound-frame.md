# Stage sound frame 전체 실행

Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`의 고정 ROM CPU `0x2efa6..0x2efdb`를 재구성했다. CPU 주소와 파일 오프셋이 같다. 원본 명령 목록은 `artifacts/sound_frame_source.json`, 정적 계약은 `stage-sound-frame-contract.md`에 있다. 생산자는 전체 `0x3af8`, 취소는 전체 `0x3c44`, 두 helper의 byte 제출은 전체 `0x3ac8` API를 사용한다.

## 전이와 레지스터

신규 호출은 D1 하위 byte에 RAM `0x10d491`의 이전 값을 읽는다. RAM `0x10d490`이 비영이면 D0 하위 byte를 `0xff`, 아니면0으로 설정하고 이를 `0x10d491`에 게시한다. 두 byte 변경은 각 레지스터 상위24비트를 보존한다.

현재가 비영이고 이전이0이면 D0 하위 WORD를 `0x1d28`로 설정하고 생산자를 실행한다. 현재가0이고 이전이 비영이면 같은 WORD로 취소를 실행한다. 그 밖에는 helper를 호출하지 않고 반환한다. WORD 변경은 D0 상위16비트를 보존한다. helper에 진입한 뒤의 D0/D1/A0/A1 변화는 각 helper의 원본 동작을 따른다. 취소 경로는 첫 제출에서 D0 전체를 `0x14`로 바꾼다.

`0x10d491` 게시가 helper보다 먼저 일어난다. 따라서 생산자 gate가 명령을 거르더라도 게시한 현재 값은 유지하며, byte 제출 대기 중에도 이미 게시되어 있다. 오류에서는 게시까지 포함한 RAM/실행 상태/외부 읽기 횟수를 호출 전으로 보존한다.

## 대기 상태

`StageSoundFrameState`는 `byte`(전체 byte helper의 레지스터/waiting), `saved`(uint16), `kind`, `phase`를 가진다.

| kind | 의미 | 유효 phase | waiting | saved |
| --- | --- | --- | --- | --- |
| 0 | 신규 호출 | 0 | false | 성공 시0으로 정규화 |
| 1 | 생산자 재개 | 1..2 | true | 저장된 하위 byte,0..255 |
| 2 | 취소 재개 | 1..3 | true | 저장된 명령 WORD,0..65535 |

생산자의 첫/둘째 제출, 취소의 첫/둘째/셋째 제출은 독립적으로 대기할 수 있다. 재개에서는 선택한 helper의 캡처된 상태를 전달한다. `0x10d490/0x10d491`을 다시 읽거나 게시하지 않으며 D0를 다시 `0x1d28`로 설정하지 않는다. 스캔과 gate를 다시 실행하지 않고 이미 완료한 제출을 반복하지 않는다. 완료 시 kind/phase/saved는0, waiting은false다. 잘못된 조합은 오류다.

`external_status`는 생산자가 조건부로 읽는 `0xd00046`의 byte 입력이다. `external_reads`는 이번 호출의 읽기 횟수이며 취소·전이 없는 호출·대기 재개에서는0이다. 오류는 이 출력 인자의 기존 값도 보존한다. A5는 원본 `0x108000` 고정이고 A6는 CLI에서 보존한다. A7/반환 주소/CCR은 API 상태에 포함하지 않는다.

## 재현과 검증 범위

```
make build/step_stage_sound_frame build/stage_sound_frame_test
./build/stage_sound_frame_test
.venv/bin/python tools/verify_stage_sound_frame.py
```

CLI 계약은 다음과 같다.

```
build/step_stage_sound_frame D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 WAITING KIND PHASE SAVED EXTERNAL INPUT_RAM OUTPUT_RAM
```

레지스터는 unsigned32bit, WAITING은0..1, KIND는0..2, PHASE는0..3, SAVED는0..65535, EXTERNAL은0..255다. 숫자는 십진수 또는 `0x`16진수로 제공한다. kind별 phase/saved/waiting 제약도 함께 적용한다. 입력과 출력은 서로 다른65536byte RAM 파일이다. 출력 JSON의14개 레지스터와 waiting/kind/phase/saved 및 출력 RAM을 다음 재개 입력으로 사용하며 EXTERNAL은 매번 명시한다. `external_reads`는 관찰 결과다.

C++ 단위 검증은9가지 현재/이전 flag 조합과 레지스터 상위비트, 전체 helper 효과, 두 생산자 제출과 세 취소 제출의 hold/release를 포함한다. 대기 중 flag·gate·큐 변경 시 비재샘플, 조건부 외부 읽기, 게시 이후 스캔/byte 오류와 대기 해제 오류의 transaction도 확인한다. 원본과 실제 CLI 2441단계, 오류 시 입력·출력 보존112조건, 동일CPU 대기 체인19개를 확인했다. 상위3조건분기 양쪽과 다섯 대기 상태를 모두 비교했다. 고정 명령1d28에서 도달하지 않는 helper 분기는 보고서에 구분한다. 전체 빌드/테스트는 Python182개/C++131개, 경고0이다. 보고서 `artifacts/stage_sound_frame/verification.json` SHA256은 `5d1d8ecfa01264218f0f367221f25d9375717c2594f302da5a327c0fbe60f2df`다.

새 리소스는 필요하지 않다. 이 호출자는 사운드 명령 전이의 실행이며 오디오 재생 완료를 뜻하지 않는다. 원본의 실제 외부 장치, 전체 CCR/IRQ timing, `0x480bc` 통합과 자연 scheduler/직접 플레이는 남아 있다.
