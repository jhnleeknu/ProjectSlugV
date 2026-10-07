# Stage preparation 리소스와 구현 경계

## 고정 팔레트 등록 창

원본 canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 이 문서의 e7bda..e7bf4는 첫1MiB의 고정 ROM CPU 주소이며 같은 파일 오프셋이다. RAM/MMIO와 banked CPU 주소를 이 파일 오프셋에 대입하지 않는다. 아래 주소·필드 값은16진수이고 바이트·레코드 개수는10진수다.

`tools/pack_stage_palettes.py`는 `[e7bda,e7bf4)`의26바이트를 원시 순서 그대로 추출한다. 네 레코드는 각각6바이트의 `BE16 slot, BE16 source_id, byte flags, byte sixth_byte`다. 마지막 두 바이트는ffff terminator이며 마지막 레코드의 뒤에 있는 코드를 payload에 포함하지 않는다. Sixth byte는 값0이어도 보존하고 metadata에 기록한다.

| 레코드 CPU 주소/ROM 오프셋 | slot | source_id | flags | sixth_byte |
| --- | --- | --- | --- | --- |
| e7bda | b | 025f | 02 | 00 |
| e7be0 | c | 0065 | 02 | 00 |
| e7be6 | d | 0067 | 02 | 00 |
| e7bec | e | 006a | 02 | 00 |

Terminator CPU 주소와 파일 오프셋은e7bf2다. 이 표의 slot/source/flags는 메인이 확정한 등록 레코드 계약이며 특정 stage에서의 자연 도달성이나 후속 팔레트 적용 시점까지 입증하지 않는다.

## MS5D와 재생성

납품 리소스는 기존 MS5D v1 kind1으로 저장한다. 새로운 포맷이나 PNG를 사용하지 않는다. Header는 기존32바이트 `<4s7I>` 형식으로 magic MS5D, version1, kind1, source CPU, source ROM offset, payload length, CRC32, reserved0을 담는다. Payload26바이트를 더한 전체 파일은58바이트다. Stable ID는 `stage-palettes:000e7bda`다.

출력은 `extracted/runtime/stage_palettes.ms5d`와 `extracted/runtime/stage_palettes.manifest.json`이다. Manifest는 원본 전체 hash, source CPU/ROM 주소, exclusive end, 네 레코드 주소·필드·원시 바이트, terminator 주소와 payload/container hash를 제공한다. ROM 및 추출 게임 데이터는 Git에 추가하지 않는다.

Payload SHA256은 `55d47a0a681ab9b06490608b3fdb599297c26507093f8c6aa1e072774454e7bc`, container SHA256은 `de398dc6e5c917c83709a325dd72b557faa0b94a66b3a5d71b5c955fd7f3fdc6`다. Packer는 manifest를 통해 원본을 읽은 뒤 전체8MiB 길이와 pinned SHA를 다시 검사하고,26바이트 창의 필드·sixth byte·terminator·payload SHA를 확인한다. 기존 `engine/src/fixed_data_resource.cpp`의 `load_fixed_data_resource`가 사용하는 포맷이며 stage preparation API가 이 리소스를 직접 소비한다. 독립 stage native 동등성 결과는 아래 최종 보고서 범위에서 확인했다.

재생성 및 targeted 합성 검사는 다음 명령으로 수행했다.

```text
.venv/bin/python tools/pack_stage_palettes.py
.venv/bin/python -m unittest tools.tests.test_pack_stage_palettes tools.tests.test_main_startup -v
.venv/bin/python tools/pack_palettes.py
./build/check_palettes extracted/runtime/palettes.ms5p
```

실제 packer는 네 레코드·58바이트를 생성했고 `validate_container`로 header/CRC/payload를 다시 확인했다. 합성 테스트9개는 추출·container roundtrip, 잘린 program/payload, slot/source/flags/sixth/terminator 변경, 전체 program hash 변경, header schema, CRC 및 CRC를 다시 맞춘 payload 변경, 주변 byte가 창에 섞이지 않는 조건을 검사했다. 모든 테스트가 통과했으며 tracked 테스트 데이터에 ROM 원시 바이트를 넣지 않았다.

기존 `tools/pack_palettes.py`의 grounded binding table 목록에e7bda를 추가했고 위 pinned stage 창을 color 추출 전에 검사한다. 네 ID025f/0065/0067/006a가 기존 MS5P에 추가되어 전체 catalog는33개 ID·2276바이트가 됐다. MS5P schema는 유지하며 sparse/incomplete 상태다. 새 container SHA256은 `df097b579c1c544bb39f0eaa94b85767180f73acad33ace29b154da4a261a07c`다.

기존 `build/check_palettes` C++ loader가 새33개 ID를 모두 읽었고 네 ID의 hardware words 출력도 확인했다. 로그는 `artifacts/stage_palettes_loader_check.log`다. 합성 catalog 소비·잘못된 pinned table을 color read 전에 거부하는 두 조건과 기존 main startup/disabled binding 회귀를 포함한 targeted17검사가 통과했다. 이 loader 확인은 원본 palette 변환 native 동등성이나 stage preparation 전체 동등성 검사를 대신하지 않는다.

## Stage preparation API

실제 API는 `engine/include/ms5/main_startup.h`와 `engine/include/ms5/stage_preparation.h`에 있다. `StagePreparationState`는 전체 D0/D1/D3와 A6를 운반한다. Clear/body는 정확한64KiB RAM과 정렬된 완전한c4-byte A6 span을 요구한다. 다음 세 진입을 지원한다.

| 원본 진입/범위 | API | 완료 경계 |
| --- | --- | --- |
| e7c36 | `initialize_stage_palettes` | 팔레트 helper RTS에 대응하며 A6는 변경하지 않는다. |
| 477c2 | `clear_stage_objects` | 오브젝트 정리와 palette gate/IRQ callback reset의 RTS에 대응한다. |
| 479b0..479ba | `prepare_stage_body` | e7c36→477c2 순서 후479ba 본문 직전에서 끝난다. |

`initialize_main_palettes`는 기존 e7bf4에서 공유하는 검증된 helper다. 기존 고정 palette references를 해제·free-list로 relink한 뒤e7b58의17레코드를 순서대로 등록하고 slot6 blend를 설정한다. Final D0 전체는60, D1.lowword는1이며 highword를 보존한다. D3.lowword는 마지막 실제 relink의 old tail/head를 담고 highword를 보존한다. `initialize_main_frame`도 이 helper를 사용한 뒤 기존 e4a→e74 startup 필드를 갱신한다.

`initialize_stage_palettes`는 main helper를 먼저 실행한 뒤 네 e7bda 레코드를 원본 순서로 등록한다. 해당 노드가 이미 bucket head인 경우 불필요 relink를 수행하지 않으며 D3도 마지막 **실제** relink 값을 유지한다. Final D0 전체는0000ffff, D1.lowword는 마지막 source006a이며 caller highword를 보존한다. Stage resource 검사는 main helper 이후이므로 잘못된 stage 창이나 후속 ring 오류는 앞선 main palette 변경과 포트까지 모두 rollback한다.

e7c36의 순서 있는 watchdog 포트는300001.byte에 incoming D0.lowbyte,0,60을 기록하는 세 쓰기다. 이것은 palette helper의 MMIO 출력이며 실제 palette color 업로드·전체 stage VRAM 작업을 대신 실행한 것으로 표현하지 않는다. Bindings는 source CPU/ROM 주소·정확한 창 길이·terminator와 slot 범위를 host에서 검사한다. API shape 검사와 원본 pinned bytes 검증은 구분하며 canonical 값은 packer/manifest와 소비 검증에서 확인한다.

`clear_stage_objects`는 기존 `remove_objects`를 통해 현재 A6의2a0a descendant 정리, 이어 고정100bf4의2a84 제거를 수행한다. 실제 반환 A6/D1/D3를 유지하고 D0 전체는0으로 만든다. RAM107dec.byte=0, RAM104d91.bit4 clear, RAM100006/10000a.long=3dcc를 마지막에 기록한다. 제거의 watchdog 포트는 두 제거 순서대로 이어진다. 설치한 IRQ callback body나 자연 IRQ를 이 함수가 실행하지 않는다.

`prepare_stage_body`는 e7c36의 세 watchdog 뒤477c2 제거의 포트를 append한다. 전체 candidate RAM/state/ports에서 수행하고 모든 helper 성공 후에만 게시하므로 늦은 제거 오류도 팔레트 변경까지 보존한다. 노출 레지스터 이외 D2, 다른 주소 레지스터, CCR와 stack의 완전한 반환 계약을 주장하지 않는다.

## CLI와 검증 상태

CLI는 다음 형식을 사용한다.

```text
build/step_stage_preparation ENTRY D0 D1 D3 A6 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS MAIN_MS5D STAGE_MS5D
```

ENTRY는e7c36/477c2/479b0 중 하나다. JSON은 `d0/d1/d3/a6/writes`를 출력한다. 479b0 모드는479ba 직전에서 끝나지만 JSON에 가상 caller return PC를 만들지 않는다. 모든 모드는 두 MS5D를 실제 loader로 읽고 path/inode alias를 거부한다. Clear 진입에서 두 resource를 읽는 것은 CLI 입력 계약이며 원본477c2의 추가 ROM 읽기라고 표현하지 않는다.

공유 main palette helper refactor 뒤 기존 `.venv/bin/python tools/verify_main_startup.py` 회귀가 exit0으로 통과했다. 최종 `artifacts/main_startup/verification.json` SHA256은 `2bf5387682dae840040749fb882917080a43ecedb22a1dd13766ca123cccea7a`이며 원본209조건·오류32조건·포트418개와 준비 연결2조건을 포함한다. 기존 e4a 경로 회귀 결과를 새로운 e7c36/477c2/479b0 동등성 검사 수치로 합치지 않는다.

전체 `make -j3 all test` 로그 `artifacts/stage_preparation_build_test.log`에서 Python104검사·C++92 test executable 실행, warning/error0을 확인했다. 메인이 빌드 성공을 확인했다.

독립 stage 검증 session56721은 exit0으로 끝났다. 실제 `artifacts/stage_preparation/verification.json` SHA256은 `226820728af213cb3fc73808809723e951d4e8a00dbd39d644793f69d08a17ab`이다. 원본101조건·오류 보존37조건·API ordered 포트441개에서 전체64KiB RAM·전체 D0/D1/D3/A6가 일치했다. 외부 A7 stack endpoint도 일치했고 MMIO read0·원본 코드 변경0이다. 이 A7 관측을 stack 전체나 다른 레지스터/CCR 반환 계약으로 확대하지 않는다.

실제 CLI RAM/반환 레지스터를 운반하는 승계2시퀀스는 각각5호출이다. 원본2790/3ef2 fixture와 실제28ae child 및8ebe reference 준비를 사용했으며, 각 standalone entry의 CPU context 재설정은 명시적 host 입력이다. 자연 callback/scheduler의 전체 연속 실행으로 주장하지 않는다.

별도 resource 변환 관측에서 네 source025f/0065/0067/006a의 등록 slot hardware bytes가 MS5P 변환과 일치했다. 이 과정의 `resource_conversion_pvc_writes`는 `2ffff2.word=1000, 2ffff0.word=0` pair를 두 번 기록한 **네 쓰기**이며 API 포트441개와 구분한다. 관측된 bank는 고정 source2MiB이고 physical `[200000,2ffff0)` 즉200000..2fffef 데이터가 불변이었다.2ffff0 이후 PVC register overlay는 이 데이터 불변 비교에서 제외했다. 일반 PVC bank 장치·물리 timing 동등성은 미검증이다.

기존 `artifacts/palette_resources/verification.json` SHA256 `e7a7f4124229ccd54edcc5d4fb262d21588fab3ecd5194161cc89258019da32f`도 확인했다. 활성 binding34개의 palette bytes가 일치했고 disabled sourceffff binding4개는 색상 조회 주장에 포함하지 않았다. 이34개는 등록 참조 개수이며 MS5P의 unique ID33개와 구분한다. Disabled binding을 color IDffff로 조회하던 검증 오류는 수정됐고, disabled metadata는 계속 보존한다.

479b0 이후 본문의 호출 후보는 `artifacts/stage_body/inventory.asm`과 `report.json`에 있다. 자동 bounded 목록은 완전한 stage body 의미나 모든 분기 경로의 구현 완료 근거가 아니다.479ba 이후 일반 scene script·자연 callback/scheduler·stage gameplay는 아직 미완료다. 이 API는 준비 접두부의 반환과 transaction을 제공하며 전체479b0 body 완료를 주장하지 않는다.
