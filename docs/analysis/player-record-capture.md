# Player record capture 원시 lookup 리소스

## 원본 범위와 lookup 근거

Canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 source CPU 주소는 첫1MiB의 고정 ROM 주소이며 canonical 파일 오프셋과 같다. RAM/MMIO와 banked 주소는 분리한다. 주소·필드 값은16진수, 바이트·레코드·반복 개수는10진수다.

메인이 확정한4d7a6 active 경로는 player object100cb8/100da8과 RAM10dcba/10dce6 record를 사용한다. Record 활성word가 비영이면 record+27.byte를 index로 사용한다. Index0은 원본TRAP 경로이며 정상 lookup 계약이 아니다. 비영 byte1..255에 대해4d806..4d81a의 명령은 D4.word를00ff로 mask하고 unsigned16 곱셈16배, base4cf64에 더한 뒤+a.word를 읽는다.

`load_verified_program`과 `disassemble_range`로 실제4d806..4d81a 창을 확인했다. 이20바이트는 `MOVE.W D0,D4; ANDI.W00ff,D4; MULU.W0010,D4; LEA4cf64(PC),A4; ADDA.W D4,A4; MOVE.W0a(A4),D4`다. Packer는 이 명령 raw evidence를 pin하고 manifest에 각 주소·바이트·operand를 기록한다. Bounded 명령 확인을 전체4d7a6의 callback/제어 흐름 분석 완료로 취급하지 않는다.

조회 주소는 `4cf64 + unsigned byte index*16 +0a`다. Index255의 마지막word는4df5e..4df60(exclusive)에 있으므로 보존 창은 `[4cf64,4df60)`의4092바이트다. **원본 논리 record table이4092바이트라는 주장은 하지 않는다.** 기존 `game_records.ms5d`의20×16=320바이트 크기와 계약을 변경하지 않는다. 이 새 창은 기존320바이트 prefix 뒤의 code/미분류 바이트를 포함할 수 있으며 가능한 byte lookup에 필요한 원시 바이트를 삭제하지 않는다. 각 index의 자연 사용이나 word의 게임 의미는 별도 분석 대상이다.

## MS5D와 재생성

`tools/pack_player_record_lookup.py`는 기존 MS5D v1 kind1 형식을 그대로 사용한다. Stable ID는 `player-record-lookup:0004cf64`이며 출력은 `extracted/runtime/player_record_lookup.ms5d`와 `player_record_lookup.manifest.json`이다. Header32바이트와 payload4092바이트를 합친 전체 파일은4124바이트다. Manifest에는 source CPU/ROM offset·exclusive end·hash, lookup expression·정상 active index 범위·0 TRAP 제한, 기존320바이트 prefix와 lookup instruction evidence를 기록한다.

Payload SHA256은 `a6ff769be292399534dc547ca3c43af55f33f5c047758ab44487d23cf0f6f899`, container SHA256은 `aad55489c3ee994e32b0ca8301e97d546746d5735cea2f5181ec9f71d136ac45`다. 첫320바이트 SHA256 `9b1c4db78844053dff88ac7c863b15852c1ad1b9e500a831ed5a01fa9eff923c`는 기존 game records payload와 같고 실제 기존 resource의 prefix bytes도 비교했다. C++는 기존 `FixedDataResource`/`load_fixed_data_resource` 포맷을 사용할 수 있으며 새 schema를 만들지 않는다. Capture API가 이 lookup 리소스를 직접 소비하며 독립 native 결과는 아래 대기 범위다.

재생성과 합성 검사는 다음 명령으로 실행했다.

```text
.venv/bin/python tools/pack_player_record_lookup.py
.venv/bin/python -m unittest tools.tests.test_player_record_lookup_resource -v
```

실제 packer는 전체8MiB 길이·canonical SHA·lookup evidence·prefix/payload SHA를 확인하고 container header/CRC/payload roundtrip을 검사했다. 합성 테스트7개는256개 byte index의 word 주소와 최대 end, 추출/container roundtrip, source/payload truncation, prefix와 후속 byte 변경, instruction/source hash pin, header schema·길이·CRC 및 CRC를 다시 맞춘 raw 변경을 확인했다. 모두 통과했으며 tracked 테스트에는 전체 ROM 창을 넣지 않았다. Raw index0 주소 테스트는 보존된 byte 범위를 검증할 뿐 원본TRAP 경로 지원을 뜻하지 않는다.

## Capture API와 현재 상태 snapshot

생성된 `engine/include/ms5/player_record_capture.h`, `engine/src/player_record_capture.cpp`와 공유 `game_initialization.h/.cpp`를 읽어 다음 지원 진입을 대조했다. 이는 이전 record를 player에게 복원하는 restore 경로가 아니다. 현재 RAM의 player record 상태를 읽어 작은 snapshot에 저장한 뒤 공통 stage-area reset을 수행하는 순서다.

| 원본 진입/범위 | API | 노출 반환 |
| --- | --- | --- |
| 4d7a6 | `read_player_record` | 전체 D0/D1/D2/D3/D4/D5/D6, RAM read-only |
| 48180 | `capture_player_record` | 전체 D0..D6와 snapshot RAM 변경 |
| 475ca..47642 | `reset_stage_area` | 전체 D0/D1/D3, 공통 reset RTS |
| 479ee..479fe | `resume_stage_area` | 두 snapshot→475ca 순서, 전체 D0/D1/D3,479fe 본문 직전 |

모두 정확한64KiB RAM을 요구한다. Leaf는 `PlayerRecordState`의 전체 D0..D6를 운반하며 오류 시 state를 보존한다. Capture/resume/reset은 candidate RAM/registers에서 수행하고 성공 시에만 게시하므로 두 번째 snapshot이나 후속 reset 실패도 앞선 변경까지 rollback한다. 이 지원 범위는 hardware write를 발생시키지 않는다. 상위 reset/resume의 계약을 leaf처럼 D2/D4/D5/D6 반환으로 확대하지 않는다. 다른 CPU register·CCR·stack·자연 scheduler도 별도 범위다.

### 4d7a6 read 폭과 조건부 lookup

D0.lowbyte가0이면 object100cb8/source10dcba, 그 외에는100da8/10dce6를 선택한다. Object callback=270e 또는 source 활성word=0이면 lookup을 읽지 않는다. 이 경로는 D0.lowword0/highword 보존, D1/D2/D3/D4/D6 전체0, D5 전체ffffffff로 반환한다. Callback0을 inactive270e와 같다고 취급하지 않는다.

Active 경로는 source+27.byte의 비영 index를 D0 전체에 넣는다. D1/D2/D6는 각각 source+25/+26/+2a.byte를 lowbyte에 읽고 이전 상위24bit를 보존한다. D3/D5는 source+1c/+20.word를 lowword에 읽고 상위16bit를 보존한다. D4 전체는 위 원시 ROM lookup word 값이다. Index0은 native TRAP에 대한 API 오류이며 잘못된 resource shape와 별도로 구분한다.

Lookup resource는 active/source-nonzero 경로에서만 source CPU/ROM4cf64와4092바이트 크기를 검사한다. Inactive/sourceword0 경로는 미사용 lookup을 검증하지 않는다. 이 조건부 host 검증을 원본의 미사용 ROM 읽기나 추가 fault로 표현하지 않는다. Resource 전체가256개의 논리 record라는 뜻은 아니며 기존20-record prefix 계약을 그대로 유지한다.

### 48180 snapshot 선택과 저장 순서

Snapshot은 호출 입력 D0.word를1로 AND하여 player parity를 정하고 **read 전에** destination을 선택한다.0이면 RAM10d694,1이면10d69c다. 이후 leaf read는 이 정리된 D0.lowbyte를 사용한다. 따라서48180의 parity 선택과 직접4d7a6의 nonzero-byte 선택을 같은 입력 판정으로 합치지 않는다.

Destination에서 원본 순서는 byte+0=D0, byte+3=D1, byte+2=D2, word+4=D3, word+6=D5, byte+1=D6다. D4 lookup 결과는 leaf 반환에 포함되지만 snapshot에 저장하지 않는다. 이것은 현재 source의 byte/word snapshot이며 player callback이나 source 상태를 복원하는 작업이 아니다.

### 공통 reset과 area resume

`reset_stage_area`는 기존 게임 초기화 suffix의475ca..47642를 공유한다. d682 clear→1bd12 game object reset→de2a=e89ec→default IRQ callback 설치→기존 subsystem resets 순서를 유지하고, 마지막 좌표·timer word/byte를 원본대로 설정한다. 이 helper를 호출하는 초기 게임 준비와 area resume이 같은 원본 부분을 중복 구현하지 않는다. Final exposed D0/D1/D3는 모두0이며 IRQ callback body를 실행하지 않는다.

`resume_stage_area`는 MOVEQ0에 대응하는 첫48180 snapshot, MOVEQ1에 대응하는 둘째 snapshot,475ca 공통 reset을 순서대로 실행한다. Leaf scratch 레지스터들은 내부에서 사용하며 상위 API는 D0/D1/D3만 반환한다. Snapshot을 reset 뒤에 만들거나 앞의 반환 레지스터를 다시 caller fixture로 초기화하지 않는다.479fe 이후 본문은 실행하지 않는다.

## CLI와 native 검증

실제 CLI는 다음 두 형식이다.

```text
build/step_player_record_capture ENTRY D0 D1 D2 D3 D4 D5 D6 INPUT_RAM OUTPUT_RAM LOOKUP_MS5D
build/step_stage_area_resume ENTRY D0 D1 D3 INPUT_RAM OUTPUT_RAM LOOKUP_MS5D
```

첫 ENTRY는4d7a6/48180, 둘째는475ca/479ee다. 첫 JSON은 `d0..d6`, 둘째는 `d0/d1/d3`를 출력한다. 가상 caller return PC나 hardware port 목록을 만들지 않는다. CLI는 모든 경로에서 실제 MS5D loader와 path/inode alias 검사를 수행한다. Inactive leaf나475ca처럼 API가 lookup을 쓰지 않아도 CLI loader는 입력 형식상 실행하며, 이를 native 추가 읽기나 API upfront resource requirement로 혼동하지 않는다.

독립 native 최종 `artifacts/player_record_capture/verification.json`을 읽고 SHA256 `3be3c5e82d570c78096f49cdff1f34e6947a858efaf832a41af1c0c600cf97cd`을 확인했다. Leaf3372조건과 area50조건, 합계3422조건·오류 보존49조건이 통과했다. Leaf는 전체64KiB RAM과 전체 D0..D6, area는 전체 RAM과 전체 D0/D1/D3를 비교했다. MMIO 쓰기0·원본 code 변경0이며 RTS stack endpoint도 일치했다. 이 endpoint를 stack 전체나 다른 CPU register/CCR 계약으로 확대하지 않는다.

모든 active byte index1..255가 실제 원본 read instruction을 통해 원시4092-byte resource를 조회했다. 이 coverage는 논리256-record table이나 index의 자연 게임 사용을 입증하지 않는다. Index0은 원본TRAP 실행 동등성에서 제외하고 API transactional error로 검사했다. Source record/callback 변경은 통제된 fixture다.

실제 CLI RAM/전체 D0..D6 출력을 운반하는 read→snapshot 승계8시퀀스는 각각4호출이다. Read 뒤 D0.word snapshot selector 지정은 명시적 host 입력이며 나머지 반환 bits/RAM은 실제 output을 운반한다. 실제479ba CLI→원본479d0 BNE→479ee→479fe 연결2조건은 A5/A7/SR나 return stack을 재초기화하지 않고 native context를 유지했다. 이 상위 경로가 C++에서 반환하는 data register는 D0/D1/D3뿐이다. D2/D4/D5/D6는 native fixture context이며 C++ 결과라고 주장하지 않는다.

최종 leaf 실행 파일 SHA256은 `a0de0720adf74ea53f26477e0da67b7e97e4e84bf978e07bf6bb869bb585ba58`, area 실행 파일은 `a34533d774b2de9dcb7526b78fd43a6b853aa8ae214ecbeca45cba902925edf4`다. 전체 `make -j3 all test`가 exit0으로 완료됐다. `artifacts/player_record_capture_build_test.log`에서 Python118검사·C++94 test executable 실행과 warning/error0을 확인했다.

공통 area suffix 분리 뒤 기존 `.venv/bin/python tools/verify_game_initialization.py` 회귀 session85298도 exit0으로 끝났다. 실제 `artifacts/game_initialization/verification.json` SHA256 `ba538ea67e01041c8b199c889d8f2a225f18b203bf55e6a281da5464af12a3b2`과 `artifacts/player_record_capture_game_initialization_regression.log`를 확인했다. 원본562조건·오류 보존31조건·승계4시퀀스·외부 읽기4회가 통과했다. 회귀의 sound head 변경은 명시적 host fixture이며 자연 IRQ/scheduler 동등성으로 확대하지 않는다. 이 기존47570 회귀 수치는 새 leaf/area3422조건과 구분한다.

Callback body 실행, 자연 record 사용·scheduler와 전체 player/stage/gameplay 완료는 아직 미완료다.
