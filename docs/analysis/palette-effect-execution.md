# 8c16 palette effect 전체 레지스터 실행 인터페이스

원본 범위는 [첫 프레임 이후 stage callback 계약](stage-post-entry-contract.md)의 palette helper `0x008c16`이다. canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 이 고정 CPU 주소는 동일 ROM 파일 오프셋 `0x008c16`과 같다. 이 문서는 helper CLI 사용과 지원 범위를 설명하며 다음 stage callback 전체의 구현·검증 완료를 뜻하지 않는다.

## API와 CLI

```cpp
bool execute_palette_effect(std::vector<std::uint8_t>& ram,
    ObjectRestartState& state, std::string& error);
```

`ObjectRestartState`의 `d[8]`, `a[7]`로 D0..D7/A0..A6 총15개 레지스터를 운반한다. 기존 구조체 형식을 공유하며 object restart를 실행한다는 뜻은 아니다. 이 helper는 외부 runtime resource나 ports 인자를 사용하지 않는다.

```sh
make build/execute_palette_effect
```

```text
build/execute_palette_effect \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  INPUT_RAM OUTPUT_RAM
```

숫자는15개이며 필수 argc는 실행명을 포함하여18이다. 추가 인자도 거부한다. 부호 없는32비트 10진수 또는 `0x`/`0X` 16진수를 받는다. 빈 숫자, 부호, 공백, 후행 문자와 범위 초과를 거부한다. INPUT_RAM은 CPU `0x100000..0x10ffff`에 대응하는 정확히65536바이트다.

성공 stdout은 한 줄 JSON이며 정확한 키는 `d0..d7`, `a0..a6`이고 값은 모두 숫자다. 별도 port 파일이나 리소스 인자는 없다. 전체 반환 레지스터를 다음 caller 상태로 그대로 이어야 한다. 실패 시 진단은 stderr에 쓰고 성공 JSON을 출력하지 않는다.

## 원본 효과와 지원 범위

원본은 진입 A5 값과 관계없이 A5를 `0x108000`으로 설정한다. 따라서 다른 incoming A5를 단순히 오류로 거부하지 않는다. D0..D2의 signed WORD를 -31..31로 clamp하여 WORD8비트 이동한 target을 만들고 현재값과 WORD 차이를 계산한다. clamp 분기의 MOVEQ는 레지스터 전체를 바꾸고 범위 안의 값에 대한 WORD 연산은 상위WORD를 보존하므로 입력 high bits를 임의로 정규화하지 않는다. D3.low는 ANDff 후 duration0을1로 바꾼다. delta OR가0이면 D3.low와 timer를0으로 만들며, 그렇지 않으면 D3 전체를 정규화한 duration1..255로 만들고 DIVS 결과의 remainder 상위WORD와 quotient 하위WORD를 D0..D2에 유지한다. D4..D7/A0..A4/A6는 보존한다. 기존 RAM 전용 `set_palette_effect`만 호출해 레지스터 효과까지 복원했다고 주장하지 않는다.

RAM target은 CPU `0x107dc8/ca/cc`, step은 `0x107dce/d0/d2`, timer는 `0x107dd4`다. current WORD와 다른 RAM의 보존 및 전체15레지스터 반환을 원본 비교에서 확인했다. CLI는 원본 CCR·cycle·stack을 노출하지 않으며 전체 helper의 레지스터/RAM 계약을 caller 연결에 제공한다. 원본 CPU의 WORD 폭과 DIVS 의미를 C++의 signed overflow나 음수 shift에 의존하여 구현하지 않는다.

## 파일 보호와 오류

입력은 `stat`으로 일반 파일임을 확인한 뒤 stream을 열므로 FIFO 등 특수 입력을 받지 않는다. 입력과 출력의 canonical 경로 또는 inode가 같으면 거부한다. RAM 크기 검사와 core 실행이 성공하기 전에는 출력을 열지 않는다.

출력은 `O_WRONLY|O_NONBLOCK|O_CREAT|O_EXCL`로 예약하고 이미 있는 파일은 `O_NONBLOCK|O_WRONLY`로 열며 truncate하지 않는다. `fstat`으로 일반 파일인지 확인하고 읽었던 입력 identity 및 현재 입력의 `stat` device/inode와 비교한 후에만 truncate와 쓰기를 시작한다. FIFO 출력에도 대기하지 않는다. 예약/검사 실패 시 기존 파일은 보존하며 이번 호출에서 생성했고 현재 `lstat` identity가 예약한 inode와 일치하는 placeholder만 제거한다.

쓰기와 close 결과를 검사한다. 실제 I/O 단계의 실패에는 이미 truncate/기록한 출력의 rollback이나 원자적인 파일 교체를 보장하지 않는다. C++ core의 오류 시 RAM/레지스터 보존과 파일 I/O 실패 처리를 구분한다.

## 빌드 연결과 검증 기록

CLI는 self-contained `palette_effect_execution.cpp`만 링크하고 `ObjectRestartState` 정의를 위해 object restart header를 읽는다. object restart 구현이나 다른 helper 전체를 링크하지 않는다. core 담당과 합의한 단위 테스트 target만 기존 RAM 효과와 교차검증하기 위해 `palette_control.cpp`를 추가한다. `all`에 CLI, `test`에 `palette_effect_execution_test`를 등록한다.

최종 core/unit/native 비교를 메인 리뷰에서 수용했다. 실제 명령과 통과 수는 아래 최종 검증 기록을 따른다. helper 비교가 통과해도 `47af0` 이후 gate/dispatch, 다음 callback, 자연 IRQ/scheduler, 조작 가능한 게임, 화면·오디오 동등성의 완료를 주장하지 않는다.

## 최종 검증

`.venv/bin/python tools/verify_palette_effect_execution.py`로원본Musashi8c16과실제CLI883조건을비교했다. 전체RAM/15register/JSON일치,오류104조건(FIFO2종포함),도달가능8조건분기양쪽을통과했다. allzero324/nonzero559조건과모든duration256값을포함한다.8cac의duration0분기는앞선정규화로도달불가이며coverage누락을숨기지않는다.

보고서 `artifacts/palette_effect_execution/verification.json` SHA256은 `4db8fcbafa31fd053b35afb3d2a8beef86183d018a9234f7aab4e74397aaadac`다. 최종make all test는Python182/C++134/경고0,단위UBSan도통과했다. [메인리뷰0192](../reviews/0192-palette-effect-execution.md)에원본근거와한계를기록했다. 후속47af0콜백전체와직접플레이완료를뜻하지않는다.
