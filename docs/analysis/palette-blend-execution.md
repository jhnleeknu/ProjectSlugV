# 8cda palette blend 전체 레지스터 인터페이스

원본 의미는 [전체 레지스터 계약](stage-activation-prefix-contract.md#8cda의-전체-레지스터-연결-계약)을 따른다. canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 고정 CPU `8cda..8d32`는 같은 ROM 파일 오프셋이다. 이 API는 `8cda` 진입부터 원본 RTS까지의 RAM·15레지스터 효과를 제공한다. 전체 stage callback 실행이나 실제 화면 출력 완료를 뜻하지 않는다.

```cpp
bool execute_palette_blend(std::vector<std::uint8_t>& ram,
    ObjectRestartState& state, std::string& error);
```

RAM은 CPU `100000..10ffff`의 정확히65536바이트이며, 상태는 `ObjectRestartState`의 D[8]/A[7]이다. 기존 `set_palette_blend`는 RAM 효과 API이므로 호출자의 레지스터 연결에는 이 full adapter를 사용한다. helper는 외부 리소스나 MMIO를 읽지 않고 ports를 생성하지 않는다.

## CLI

```text
build/execute_palette_blend \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  INPUT_RAM OUTPUT_RAM
```

숫자는15개이며 실행명을 포함한 argc는 정확히18이다. ENTRY/resource/port 인자는 없다. 부호 없는32비트 10진수 또는 `0x`/`0X` 16진수를 받고 빈 숫자, 부호, 공백, 후행 문자와 범위 초과를 거부한다. 성공 stdout은 한 줄 JSON으로 정확히 `d0..d7`, `a0..a6` 숫자15개만 출력한다. OUTPUT_RAM은65536바이트다. 오류는 stderr에 쓰며 성공 JSON을 출력하지 않는다.

## RAM 및 레지스터 효과

입력 D0.byte가 slot0..255를 선택한다. D0.low는 `(incoming D0.low & 00ff) << 4`로 바뀌고 상위WORD는 보존된다. A1=`104d92`, A2=`104d92 + slot*16`이다. 고정 slot 읽기는 임의 A5/A6를 주소 base로 사용하지 않는다.

A2+8의 참조WORD가0이면 주소·D0 변화만 남기고 반환하며 RAM과 D2는 변경하지 않는다. 참조가 비영일 때만 weight D2.byte를 처리한다. BYTE가32 이상이면 원본 MOVEQ32처럼 **D2 전체**를32로 바꾸며,32 미만이면 D2 전체 입력값을 보존한다.

D1.low가 slot+0c의 현재 target WORD와 다르면 target WORD와 slot+0e의 weight BYTE를 쓰고 slot+0f bit7을 세운다. target이 같고 weight만 다르면 weight BYTE를 쓰며, D1.low가 slot+0a WORD와 다를 때만 bit7을 세운다. target과 weight가 모두 같으면 해당 필드를 변경하지 않는다. 다른 flag bit와 node/list 필드는 보존한다.

D1/D3..D7/A0/A3..A6는 보존한다. 특히 **A5는 임의 입력값 그대로 유지**하며, A5를108000으로 설정하는 `8c16` palette-effect helper와 다르다. A7/stack/CCR/cycles, 물리 mirror, 실제 palette 전송과 rendered pixels, 상위 callback/IRQ/scheduler 및 자연 게임 도달성은 이 API의 동등성 범위 밖이다. 실패 시 RAM/state를 보존한다.

## 파일 보호와 I/O 한계

INPUT_RAM은 stream을 열기 전에 `stat`/`S_ISREG`로 일반 파일인지 검사하여 FIFO 등 특수 입력을 거부한다. input/output의 canonical 경로나 inode가 같으면 거부한다. 숫자·입력·core 실패 시 output을 열지 않는다.

core 성공 뒤 output을 truncate 없이 `O_WRONLY|O_NONBLOCK|O_CREAT|O_EXCL`로 예약하고 기존 파일은 `O_WRONLY|O_NONBLOCK`으로 연다. `fstat`으로 일반 파일 여부를 확인하고 처음 검사한 input inode 및 쓰기 직전 input의 현재 inode와 비교한 뒤에만 truncate/쓰기를 시작한다. path 표기와 다른 hardlink/symlink/case alias도 실제 identity로 검사한다.

예약/검사 실패에는 기존 파일을 보존하며, 새로 생성했고 현재 `lstat` identity가 예약 inode와 같은 placeholder만 제거한다. write의 EINTR을 재시도하고 close 결과도 검사한다. 실제 truncate/write/close 실패에는 원자적 교체나 이미 수행한 출력 변경의 rollback을 보장하지 않는다.

## 빌드와 검증 상태

Makefile의 CLI 및 단위 target은 `palette_blend_execution.cpp`, `palette_control.cpp`와 두 API header, `object_restart_execution.h`, `video_port.h`를 의존성으로 갖는다. CLI는 all에, `palette_blend_execution_test`는 test에 등록한다. object restart 구현 전체나 리소스 packer는 필요하지 않다.

```sh
make build/execute_palette_blend build/palette_blend_execution_test
./build/palette_blend_execution_test
.venv/bin/python tools/observe_palette_blend_full.py
.venv/bin/python tools/verify_palette_blend_execution.py
```

원본 준비 도구 `observe_palette_blend_full.py`는 pinned Musashi에서 프로그램 patch/stub 없이 `8cda`를 RTS까지 실행한다. 참조WORD0/1/ffff, slot0/1/12/255, weight BYTE0/31/32/33/255, 비영 register high bits, target/weight/base ID의 같음·다름과 임의 incoming A5를 포함하는480조건이다. SR은 A7보다 먼저 설정하며 hook에서 SR을 읽지 않는다. 전체64KiB RAM·15레지스터·ordered CPU writes와 sentinel stack/원본 불변성을 감사한다. RAM expected 결과는 원본 CPU에서 얻으며 host 의미 모델로 생성하지 않는다.

원본 관측 보고서 `artifacts/palette_blend_full/observation.json`의 SHA256은 `aaddf6efc6fd19e61d5d2af783db3f3a5cc159a6a7cb339ac886e15dbe298222`다. 원본 observer 자체는 `Cpp_comparison_performed=false`다. 별도 verifier `tools/verify_palette_blend_execution.py`가 그 고정 원본 결과와 실제 CLI를 비교하여480조건의 전체64KiB RAM·15레지스터 일치를 확인했다. 원본 CPU의 ordered RAM 쓰기600개를 replay하고 조건 분기5개의 양쪽 결과를 모두 감사했다. 참조0 bypass160조건, 비영 참조320조건, D2 전체 MOVEQ32 적용192조건과 D2 보존288조건을 포함한다. 초기 dirty/clean flag는 각각240조건으로 검사한다.

core는 기존 RAM setter `set_palette_blend`를 재사용하고 caller 레지스터 효과를 추가한다. 특히 참조WORD를 확인한 뒤에만 D2의 전체 MOVEQ32 효과를 적용한다. 참조0이면 incoming D2.byte가32 이상이어도 전체 D2를 그대로 유지하는 native 결과와 일치했다. 기존 setter를 전체 레지스터 API의 검증 없이 대체 사용했다는 뜻은 아니다.

오류107조건에는 RAM 크기,15개 register parse, missing/extra 인자, missing/directory 파일·output parent, 동일 경로/hardlink/symlink, RAM input/output FIFO, 잘못된 RAM/register에 새 output을 남기지 않는 검사와 실제 대소문자 비구분 파일시스템의 input/output alias가 포함된다. 입력·기존 출력을 보존하는 실패 동작과 새 output 생성의 native 결과 일치를 확인했다. 실제 쓰기/close 실패에 대한 원자적 rollback 한계는 그대로 남는다.

최종 검증 보고서는 `artifacts/palette_blend_execution/verification.json`이며 직접 계산한 SHA256은 `63125a881e5dac28dbb7562f8adbb9678ba138af48783fe13b2932c0e1eff07f`다. 검증한 CLI binary SHA256은 `729c4defc5ecaf5f66f79aa0d4668a3391af96a4b1117167021a149c33aae255`다. 문서 갱신 시 보고서의 `inputs`10개, `native_inputs`6개, `native_artifacts`961개 해시가 현재 파일과 모두 일치했다. 이 확인에는 실제 실행 파일·core·RAM setter·관련 header·CLI·Makefile 및 원본 관측 RAM이 포함된다.

메인의 `make -j4 all test`는 exit0으로 완료했다. `artifacts/palette_blend_execution_build_test.log`에서 Python189개 검사, 서로 다른 C++ 테스트 실행 파일138개, `palette_blend_execution_test: passed`, warning 진단0개를 직접 확인했다. C++138은 실행 파일 수이며 native fixture나 assertion 수가 아니다. 이 focused helper 비교는 상위 `4e286`/`47c6c` callback, 자연 stage 실행, palette 전송·화면/오디오 또는 전체 복원 완료를 검증한 결과가 아니다.
