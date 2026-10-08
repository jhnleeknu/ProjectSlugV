# Animation machine: shared RAM stack 실행 API와 검증 범위

기준 통합 commit `e526370` 이후 새 machine 구현의 현재 파일과 검증 보고서를 읽어 작성했다. Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8,388,608 bytes, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 아래 고정 CPU 주소는 같은 ROM 파일 offset이며, banked CPU 주소와 physical ROM offset은 별개다. 원본 ROM을 수정하지 않았고 ROM·추출 데이터는 Git 대상이 아니다.

이 문서는 확정된 shared-stack 실행 경로와 현재 대조 범위를 기록한다. 일반 68000 CPU, 전체 animation의 자연 도달성 또는 게임 완료를 선언하지 않는다. 설계 근거는 `animation-shared-stack-design.md`, 기계적 명령 목록은 `animation-stack-access-inventory.md`를 따른다.

## Public API와 caller 입력

`engine/include/ms5/animation_machine.h`:

```cpp
bool run_animation_machine(
    std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources,
    AnimationMachineState& state,
    AnimationMachineDevice& device,
    std::uint32_t stop_pc,
    std::uint8_t external_status,
    std::uint32_t& external_reads,
    AnimationMachineStatus& status,
    std::vector<VideoPortWrite>& ports,
    std::string& error);
```

`AnimationMachineState`의 `d[8]`, `a[8]`, `pc`가 D0..D7/A0..A7와 현재 logical PC의 유일한 권위다. 생성자는 모든 register를0, PC를`49fc6`으로 설정한다. 이 기본값이 유효한 caller frame을 만들지는 않는다. Caller는 실제 A7과 그 주소에서 읽을 return LONG을 **입력 RAM에 이미 제공**하고 별도의 `stop_pc`를 전달해야 한다. 구현이 sentinel·return 값·padding을 만들어 넣지 않는다.

`AnimationMachineDevice`는 mutable `pvc`8192BYTE와 `bank_base`를 가진다. 생성자 기본값은8192개의0BYTE와`200000`이다. Caller는 필요한 장치 입력 상태를 선언한다. `resources.pvc`와 `resources.bank_base`는 invocation candidate의 `device` view로 대체되며, 별도의 과거 bank metadata가 복원값을 결정하지 않는다. `resources.vectors`와 `resources.physical_rom` 등 borrowed view의 소유자는 호출 동안 살아 있어야 한다.

RAM은 정확히65536BYTE, PVC는 정확히8192BYTE여야 하며 `stop_pc`는 even이어야 한다. A5/A6/A7에 canonical 주소를 일괄 강제하지 않는다. 실제로 도달하는 bus 접근과 지원 PC를 검사한다. RTS는 현재 stack에서 live LONG을 pop해 PC로 사용한다. 그 PC가 `stop_pc`이면 완료하며, 지원하는 내부 PC이면 계속 dispatch하고, 미지원 PC이면 실패한다. 처음부터 PC가 stop과 같으면 block 실행 없이 완료한다.

## Runtime program 리소스와 bus

새 API는 `AnimationResource`와 예전 continuation metadata 대신 program bus를 통해 script·table·stack·source를 읽는다. 일반 RAM은 CPU`100000..1fffff`의16개 mirror가 같은64KiB를 참조한다. Logical32bit 덧셈은 wrap하고 접근 시24bit bus 주소를 선택한다. WORD/LONG은 even이어야 하며 LONG은 독립된 두 WORD 단위다.

검증 harness는 `extracted/runtime/program_rom/`의8개 MS5D v1 **kind3** resource를 typed `load_physical_rom_resource`로 읽어 `resources.physical_rom`에 연결한다. Kind3는 CPU binding이 없는 physical ROM 저장소다. 각32BYTE LE header의 CPU field는`ffffffff`, payload는 최대1MiB이며8개 payload가 canonical8MiB를 빠짐없이 보존한다. Kind3를 기존 `FixedDataResource` kind1/2에 섞지 않는다. 새 reader는 인접 kind3 chunk 경계의 physical WORD를 byte별 unique coverage로 조립하지만 중복·gap 또는 legacy/physical overlap을 거부한다. 기존 kind1/2의 loader·overlap 규칙은 유지한다.

Fixed bus`80..fffff`와 bank bus`200000..2fdfff`는 각각 계산된 physical offset을 선택한다. Bank physical offset은 현재 `device.bank_base`와 CPU bank-window offset으로 계산한다. Vector`0..7f`는 caller가 선언한 정확히128BYTE view이고, PVC`2fe000..2fffff`는 mutable 장치 view다. 이 장치 overlay는 ROM보다 우선하며 kind3 ROM fallback을 하지 않는다. 검증 harness의 vector view는 cart ROM 첫128BYTE이며 BIOS 선택을 검증한 것은 아니다.

## 실행·대기·재개와 transaction

구현은 알려진 원본 basic block을 C++11 함수로 옮겼다. 원본 opcode bytes를 범용 decode하는 CPU emulator가 아니다. Interpreter는 현재 지원한17개 command `00/04/08/0c/10/14/18/1c/20/24/28/2c/30/34/38/3c/40`와 callback target`3679e/2b3e8/2b3fa/47672`를 처리한다. Sprite 경로는 실제 default callback`cd50`을 호출하며 정상·deferred·clip·full·wait 동작을 포함한다. Sound 경로는 실제`3af8/3ac8`, nested`47672/ca70`의 확인된 block을 사용한다.

JSR/BSR는 return LONG을 실제 공유 RAM stack에 push하고, RTS는 실제 pop한다. MOVEM의 predecrement 순서, WORD restore의 sign extension, BYTE stack stride2와 untouched padding을 유지한다. Saved A0/A1/bank/list end/low BYTE는 host continuation field로 복원하지 않는다. 따라서 host 또는 실행 중 RAM write가 저장 slot을 바꾸면 다음 원본 pop이 그 live 값을 소비한다. Original bank 복귀의 `bank pop → shadow write → D0/D7 WORD push → shadow 재읽기/PVC → signed WORD pop → A0/A1 LONG pop` 순서도 유지한다.

성공한 호출은 `AnimationMachineReturned` 또는 `AnimationMachineWaiting`을 반환한다. Waiting은 실제 PC`cda4`(sprite) 또는`3aea`(sound)와 A7·register·RAM·PVC를 그대로 남긴다. 재개 입력은 **직전 실제 출력 전체**이며, 그 사이 필요한 외부 RAM/device 변화만 명시적으로 적용한다. 별도 phase 번호나 capture register를 주입하지 않는다. 이미 지나간 prefix와 stack push는 재실행하지 않는다.

외부 status는 해당 invocation에서 byte bus read`d00046`을 실제로 수행할 때 소비하는 입력이다. `external_reads`는 이번 invocation의 실제 읽기 수로 교체한다. `ports`도 이번 invocation의 ordered PVC writes로 교체하며 호출 간 자동 append하지 않는다. PVC write는 mutable view와 pinned PVC 장치 식에 따른 bank/색상 부작용을 함께 갱신한다.

상위 invocation은 RAM·state·device의 candidate와 새 ports/read count를 사용한다. 성공한 wait와 return만 commit하며 오류 시 RAM, 모든 register/PC, PVC/bank, read count, status, ports를 전부 보존한다. `error`는 실패 사유로 바뀌고 성공 시 비운다. 이는 native bus fault의 부분 실행 효과를 모사한다는 뜻이 아니다. 실행 cap은100000개의 C++ block이며 초과 시 같은 transaction 실패다.

## 원본 대조 결과

`tools/verify_animation_machine.py`는 immutable original을 다시 실행한 뒤 실제 public C++ API harness 결과와 비교한다. 기대 register/RAM을 C++에서 생성하거나 native CPU에 결과를 주입하지 않는다. 재개에는 직전 **실제 C++ 출력**과 기록된 host RAM 변경만 사용하며 native incoming 상태와도 대조한다. Generated harness는 검증 plumbing이며 production CLI나 파일 보호 구현이 아니다.

| 관측군 | fixture | phase | 실제 C++ 출력에서 재개 |
|---|---:|---:|---:|
| 기본 residual stack/40 nonwait | 8 | 8 | 0 |
| 기본 highwait/live stack mutation chain | 1 | 2 | 1 |
| 확장 draw/callback/field/sound | 85 | 121 | 36 |
| 합계 | **94** | **131** | **37** |

각 비교는 D0..D7/A0..A7와 PC, **전체64KiB RAM**, ordered ports, 독립적으로 접은 PVC/bank 상태를 포함한다. Stack 영역 차이를 mask하지 않는다. 원본 관측은 각 fixture/chain을 fresh CPU에서 두 번 재현했고 검증기는 frozen payload와 현재 원본 재실행을 다시 대조했다. 별도9개 API negative는 미지원 PC/live return, 누락 ROM, odd stack/stop, short RAM/PVC, 늦은 fetch/publication 오류에서 전체 출력 보존을 확인했다. 이9건은 위94개 원본 fixture 수에 포함하지 않는다.

기본8건은14 actual RTS, direct30 early sound, indexed skip, direct04 sentinel 뒤40이 실제 dead stack bytes를 읽는 조건이다. 기본 chain은 saved low BYTE`55→77`과 saved outer A0`104900`을 host가 RAM에서 바꾼 뒤 같은 native CPU에서 재개해 실제 pop·queue enqueue·대체 publication을 관측했다.

확장85건은 direct17/indexed9/control15/sound9/WORD callback8/field21/direct sound6이다. 실제 fixed script`48980/489c2`의 accepted/deferred/clip-X/clip-Y/full/flash, indexed selected draw와 sentinel, callback4종, unsigned/signed selector·field 경로와7field command를 포함한다. 총15개 same-CPU chain 중 indexed2건은 live PEA list end를`106800`으로 바꾸어 실제`4a270` pop을 확인한다. Callback/direct sound hold는 소비한 prefix를 poison하고 callback source WORD를 live 변경한다. High→low5phase chain은3건이다. 확장군은 실제 opcode fetch`00..3c`16종, conditional branch edge72개, 외부 read4회, PVC writes940개를 기록했다. Opcode40은 기본군에서 별도로 검증했다.

## 재현 명령과 식별 해시

Canonical 프로그램과 Python `.venv`/pinned Unicorn 환경이 준비된 repository root에서:

```sh
.venv/bin/python tools/pack_physical_program.py
.venv/bin/python tools/observe_animation_shared_stack.py
.venv/bin/python tools/observe_animation_machine_extended.py
.venv/bin/python tools/verify_animation_machine.py
make build/animation_machine_test build/animation_machine_device_test build/program_stack_test
./build/animation_machine_test
./build/animation_machine_device_test
./build/program_stack_test
```

메인은 현재 `make all test`에서 Python257개와 C++150개 실행의 exit0·warning0을 확인했다고 통합 보고했다. 이 문서 작성 중 위 명령을 재실행하지 않았다. 아래 현재 frozen source/report와 기존 실행 결과를 읽고 기록했다. Python 명령은 지정 extracted/artifact 출력을 재생성하므로 실행 후 새 해시를 확인해야 한다.

| 대상 | SHA256 |
|---|---|
| public `animation_machine.h` | `d291ceb34dc12fff843e6619846d6a1856f57718d3e80158a5b4ecea9abd00f8` |
| `animation_machine.cpp` | `caaab5b639be0d1698b92a78e1d4613513bbc37142d4a20bbb4ce4703754bed1` |
| interpreter | `f9d3a2d5fc408d611f28972b3c64166d26c9acc7ed3078330c0819c732683f30` |
| sprite | `cffe05b043a3d3fa0d45a70cd54ed8c24d2cb255c945e15d96ec6e659ae87154` |
| sound | `3a7b894dc2ef03326c3d76af4dd16a02c03f96ff04e4c75a58bbb06f53cb180a` |
| verifier tool | `3b63ef82f54a4e3a308e1c501140256e17145bddd06ffb97fe14fcbbeaa70c9b` |
| `artifacts/animation_machine_execution/verification.json` | `5462fac8893d9c614888e52476eaffdfaa2afbcd785b2591266bd87b519cb0e2` |
| basic native observation | `43a6627828fa9047ba1b3a89becc0731c1f19e38aa2f1f2dd8f4f9e098cb94cc` |
| extended native observation | `5ca26b65cb413860fab9fb5b488023665f2a5ec7dd27a729d6e71734c7262029` |

메인의 최종 해시 감사는1717개 문자열 경로 key를 정규화하여1707개의 distinct file을 확인했다(절대·상대 경로 표기가 같은 파일을 중복 참조할 수 있다). 이 수를1717개의 고유 파일로 집계하지 않는다. 각 원본 관측의 source bytes·backend·imported fixture·pinned reference provenance와 생성 harness/core/resource 입력은 이 보고서에서 추적한다.

## 현재 제약과 미확인

- 일반 CCR/SR, carry 출력, IRQ, timing 및 arbitrary opcode 실행을 state에 표현하지 않는다. 분기에 필요한 확인된 직전 연산은 각 block 안에서 명시적으로 계산한다. Native observer는 초기 SR 설정 외 SR를 읽지 않는다.
- 알려진 block PC와 callback만 지원한다. 범위 안의 모든 명령 주소가 진입점인 것은 아니며 변경된 live RTS target이 미지원 PC를 가리키면 checked error다. 이 제한을 실제 원본 도달 불가능으로 해석하지 않는다.
- 원본 관측은 fixed bank2 매핑을 사용한다. Native PVC writes를 독립적으로 접고 bank ROM read 때 실제 folded bank2임을 확인하며 PVC read는 없는 fixture다. C++의 다른 bank/PVC read·색상 부작용 경로가 이94개 fixture로 모두 native 검증됐다고 주장하지 않는다.
- 실제 stack과 script/source/object의 일부 live alias를 관측했지만 모든 A7 위치·mirror/device 경계·return 변조·callback alias를 열거한 것은 아니다. 전체 transaction 실패 계약도 native fault의 rollback 규칙과 구분한다.
- Fixture의 script·register·object·queue는 제어된 입력이다. Natural caller, scheduler, script 도달성, 전체 animation 명령의 모든 path 및 전체 게임 완료는 별도 미완료 범위다.
