# Animation machine의 제한된 carry와 실제 caller 분기

`codex/animation-machine-carry` 단위는 기존 `run_animation_machine`에 알려진 원본 C 상태를 추가하고, 실제 caller의 BCC/BCS를 실행한다. 다른 CCR bit·CPU timing·IRQ·자연 gameplay 전체를 구현하거나 검증했다는 뜻은 아니다. canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8,388,608바이트, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 원본 명령은 모두 fixed CPU 주소<100000이며 같은 ROM 파일 offset에 대응한다. 뱅크 CPU 주소와 물리 ROM offset을 같은 값으로 일반화하지 않는다. 원본과 기존 native 자료는 수정하지 않았다.

## API와 carry가 알려지는 경계

`AnimationMachineState`는 기존 `d[8]`, `a[8]`, `pc`에 다음 필드를 더한다. public 함수 signature와 RAM/PVC/stack/bus 계약은 유지한다.

```cpp
enum AnimationCarryState : std::uint32_t {
    AnimationCarryUnknown=0,
    AnimationCarryClear=1,
    AnimationCarrySet=2
};
// AnimationMachineState::carry의 기본값은 AnimationCarryUnknown.
```

Unknown은 C=0이 아니다. 해당 실행 블록에서 C를 보장하지 않는다는 뜻이다. domain 밖 입력은 public API가 실행 전에 checked error로 거부한다. `pc==stop_pc`인 zero-step 성공은 입력 carry를 그대로 보존하며, 성공 출력 ports/read count는 기존 계약대로 해당 invocation의 빈 효과로 교체한다. 실패는 RAM·전체 state(carry 포함)·device PVC/bank·ports·external_reads·status를 보존한다.

현재 C를 확정하는 writer는 세 실행 블록이다. 이는 일반 CCR emulator가 아니라 원본 반환 경계에 필요한 확정된 효과다.

| 실행 블록 | 실제 원본 근거 CPU=ROM | 확정 C |
| --- | --- | --- |
| initializer49f8c | 마지막49fc0 `31400006` MOVE.W D0,6(A0), 뒤49fc4 `4e75` RTS | Clear |
| null-state49fc6 갈래 | 49fe6 `003c0001` ORI.B #1,CCR,49fea `4e75` | Set |
| 공통반환4a0ca 블록 | 4a0e0 `e247` ASR.W #1,D7,4a0e2 `4e75` | shift 전 D7.low의 bit0 |

`animation_machine.cpp::carry_preserving_pc`의55개 PC 블록은 실제 블록 전체가 C를 보존하는 경우에만 기존 enum을 전달한다. JSR/RTS/PEA/MOVEM과 bus read/write helper의 사용 자체를 MOVE flags와 혼동하지 않는다. 그 밖의 블록은 실행 전에 Unknown으로 전환하고, 위 writer가 도달하면 다시 알려진 C를 만든다. 직접 RTS 진입49fea/4a0e2도 Unknown을 포함한 입력 enum을 그대로 보존하며 새로운 writer로 취급하지 않는다. sound/sprite polling 대기는 이 API에서 Unknown이다. 원본 대기 단계의 실제 C를 관측했다고 주장하지 않는다.

## 실제 caller의 원본 명령

| caller/분기 CPU=ROM | raw bytes | 실행 경계 |
| --- | --- | --- |
| 1dc84 | `4eb900049fc6` | JSR49fc6; live A7에 return1dc8a push |
| 1dc8a | `64000040` | BCC: Clear→1dccc, Set→1dc8e |
| 210ae | `4eb900049fc6` | JSR49fc6; live A7에 return210b4 push |
| 210b4 | `650004ae` | BCS: Set→21564, Clear→210b8 |

두 분기는 Unknown 입력을 `animation caller requires known carry`로 거부한다. 각 successor에 도착한 직후 stop하며 successor 명령은 실행하지 않는다. 이후 caller 전체 행동은 이 단위의 검증 범위가 아니다. 앞선 stage caller47d1a/47f04의 carry 비소비와 달리 여기서는 실제 반환 C를 소비한다. 지역 caller 명령을 확인한 사실과 자연 scheduler에서의 도달성은 구분한다.

## 원본 oracle와 실제 C++ 비교

`tools/observe_animation_machine_carry.py`는 수정하지 않은 원본 caller JSR→49fc6/실제 callee→RTS→BCC/BCS를 실행한다. 모든 실행은16개의 coherent64KiB RAM mirror와 live A7/공유 stack을 사용한다. fixed ROM은 원본 그대로이며, hook에서 예상 register나 CCR을 주입하지 않는다. SR은 어느 phase에서도 읽지 않는다. C는 **원본 BCC/BCS가 실제 선택한 successor**에서만 도출한다.

60조건의 split 실행은160단계다. 대기40단계의 carry는 native JSON에서 null이며, return 경계60개는 같은 CPU에서 뒤이어 실행한 실제 branch 방향으로 소급 태그한다. branch-result60개도 실제 successor로 판정한다. 별도 fresh CPU continuous control100단계는 return 경계에서 멈추지 않고 분기까지 실행한다. split과 continuous의 전체 RAM/PVC/16레지스터/PC/events 및 return 직전 snapshot이 일치했다. split/control 각각 두 번 실행하여 fresh CPU240회, 총 phase 실행520회를 기록했다. BCC와 BCS 각각 Clear18조건·Set12조건을 포함한다. initializer 두 조건의 return은 fixture가 해당 원본 branch 주소로 명시한 제어 조건이며 자연 initializer caller binding의 증거가 아니다.

`tools/verify_animation_machine_carry.py`는 split160단계와 continuous100단계의 원본을 모두 메모리에서 다시 실행하고 frozen payload·trace와 대조했다. verifier는 원본 branch opcode/displacement와 caller JSR bytes도 확인하며, observer의 carry 태그나 C++ 출력값을 기대값으로 복사하지 않고 실제 branch successor에서 Clear/Set을 독립 계산한다.

실제 C++은60조건·160단계에서 전체64KiB RAM,16레지스터/A7,PC,status,632개 ordered PVC writes,external_reads0회가 원본과 일치했다. return60개와 branch-result60개의 carry가 실제 원본 분기로 도출한 값과 일치했다. wait40개는 API의 Unknown 계약을 검사했다. 재개100회는 직전 **실제 C++ RAM/state/carry/PVC/bank**에 기록된 host RAM 변경만 적용한다. native incoming은 비교용 assertion이며 C++ 재개 state를 만드는 데 사용하지 않는다. device PVC/bank는 actual native ordered writes를 pinned PVC model로 독립 fold하여 비교한다. raw native PVC fixture의 side effect 부재와 device model 결과를 혼동하지 않는다.

생성 harness는 검증용 plumbing이며 production CLI가 아니다. 공통 harness는 carry를 pc 직후의 numeric argv18로 받고, bank19/stop20/external21, input/output paths22..26, MS5D resources27+를 사용한다. stdout은 정확히22개 key(16R,pc,carry,bank_base,external_reads,status,ok)다. carry의 정상 domain0..2와 정수형을 검사하며 JSON bool·중복/누락/추가 key를 거부한다. invalid-enum API failure 검사만 입력과 정확히 같은 domain 밖 값의 보존을 허용한다. 성공 출력에는 이 예외가 없다.

runtime 입력은 기존 physical program의8개 MS5D kind3 resource이며 실제 C++ loader/bus로 읽는다. 별도 carry 리소스 규격이나 ROM patch를 추가하지 않는다.

## 오류·회귀와 근거 해시

새 negative10조건은 Unknown BCC/BCS2개, invalid enum3/ffffffff2개, branch에서 시작한 unsupported successor4개, 전체 caller→animation의 RAM/PVC 쓰기 뒤 unsupported successor2개다. 모두 원하는 checked error 원인과 전체 API 출력 보존을 확인했다. 별도 zero-step3조건은 Unknown/Clear/Set 입력 보존을 확인했다. 이는 checked API transaction 검증이며 원본 CPU fault rollback·파일 쓰기의 atomicity를 뜻하지 않는다. 기존 caller 자료의 noncanonical A5 native TRAP guard4개와 C++ checked rollback도 별도 계약으로 유지했다.

기존 두 verifier도 새22-key harness로 전체 재실행했다. 기존 native 관측기의 소스·보고서·16R/PC schema와 pins는 변경하지 않았다. 기존 native 비교는 carry를 관측하지 않았으므로 hardware state projection을 비교하고, 새 enum은 실제 C++ 재개 전달·waitUnknown·failure 보존을 별도로 검사한다.

| 현재 보고서 | 실제 결과 | SHA256 |
| --- | --- | --- |
| `artifacts/animation_machine_execution/verification.json` | 기본8+2단계,확장85조건121단계,negative9 | `c1771f496f754859aeee314064a68e252e624b0783e97a3cf9fb1e875d466496` |
| `artifacts/animation_machine_callers_execution/verification.json` | 59조건91단계,32실제출력재개,PVC806,negative6 | `1b2de20742f09904952f76f7cdf72e25de84c99ef2824b9fea6ede5918c6eee8` |
| `artifacts/animation_machine_carry_native/observation.json` | 60조건,split160/control100,원본각2회 | `759ea9af0fd9e9fa58ba44b87be2b48a8b7b6b257aba6b164438f7c3df586d70` |
| `artifacts/animation_machine_carry_execution/verification.json` | C++60조건160단계,100재개,PVC632,negative10,zero-step3 | `7ec1ea7d43529bb29a430b22fe696e18588f63f7d58338ef9e9e780d0c6f7d6d` |

새 verifier는48개 inputs와3019개 artifact 참조를 기록했다. 합3067개 문자열 참조는 absolute/relative aliases를 정규화하면3042개 고유 경로다. 모든 해시와 원본 SHA/stat를 실행 전후 대조했다. 기존 두 보고서는 각각1707/1233개 고유 경로이며, 세 보고서의 합집합5834개 경로도 해시가 일치했다. 원본 관측 자체는47개 입력/1921개 artifacts를 기록한다. 코어 작업자의 기존 machine/caller 두 unit과 새 carry unit normal/UBSan이 통과했고, 새unit은196개 API invocation을 검사한다. `make all test`는 Python257개/C++152개, 경고0으로 통과했다. 세 verifier의 generated C++11 harness는 경고 없이 컴파일됐다. 독립 source/parser/해시 감사도 조치할 결함 없이 통과했다. 별도 원본 독립 재실행은25조건의split82단계와continuous57단계를 대조했으며, 원본 입력/artifact1968개 해시를 확인했다. 이 기록은 전체게임 또는 전체CCR의 완료 선언이 아니다.

| 입력 소스 | SHA256 |
| --- | --- |
| `engine/include/ms5/animation_machine.h` | `16092fb9479f1f72f883816e0c9f3e25914d1d56a071208ba800d0ed5b732734` |
| `engine/src/animation_machine.cpp` | `8d8be7814df37b2f517dbc3839ded066b2c06f4fd366559499415f1236beede3` |
| `engine/src/animation_machine_interpreter.cpp` | `c4e1179fcf51b1104ca98094c25d7b39872933a0cf9056b1fddb4b5d01a2096d` |
| `engine/tests/animation_machine_carry_test.cpp` | `ecd24c78b4454c113ff16fad03a0791e833608a51935596016a133393ddce3eb` |
| `tools/observe_animation_machine_carry.py` | `1f133fb8a6d8645f7cf837c18d78c56e9294550a67722e50bac5eb5d3ce06633` |
| `tools/verify_animation_machine.py` | `bcb08250630b40075114342ddf73e704c3f47ec13b15d35fc45f21e273d62732` |
| `tools/verify_animation_machine_callers.py` | `da720272d50305e6637fd8953641632eba82cc021f177eea51a2a052f8b6dd38` |
| `tools/verify_animation_machine_carry.py` | `ac68f5d531fde0c2ffbe0e9c7310cb9061d47e42b39d71f464622d5b1cc02274` |

## 재현

저장소 루트에서 실행한다. Packer/observer는 ignored runtime/native 산출물을 재생성하며 verifier는 각자 ignored harness와 비교 산출물을 만든다. 기존 frozen 보고서의 historical hash는 해당 시점 결과로 유지한다.

```sh
.venv/bin/python tools/pack_physical_program.py
make build/animation_machine_test build/animation_machine_device_test build/animation_machine_callers_test build/animation_machine_carry_test
./build/animation_machine_test
./build/animation_machine_device_test
./build/animation_machine_callers_test
./build/animation_machine_carry_test
.venv/bin/python tools/observe_animation_machine_carry.py
.venv/bin/python tools/verify_animation_machine.py
.venv/bin/python tools/verify_animation_machine_callers.py
.venv/bin/python tools/verify_animation_machine_carry.py
make all test
```

일반 CCR 지원, 원본 caller successor 이후의 실행, 자연 gameplay 도달성, 다른 장치·뱅크·IRQ·timing은 이 carry 단위에서 검증하지 않았다. Unknown을 false로 강제하거나 원본 branch 대신 host가 원하는 방향으로 이동하는 방식으로 이 경계를 숨기지 않는다.
