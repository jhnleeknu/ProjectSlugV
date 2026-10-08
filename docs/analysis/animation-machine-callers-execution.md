# Animation initializer와 실제 stage caller 연결

현재 carry 확장은 `animation-machine-carry-execution.md`를 따른다. `ed42971` 이후 Unknown/Clear/Set 상태와 실제 BCC·BCS caller를 추가했다. 아래 이전 단위의 검증 수치·해시는 당시 기록이며, 최신 회귀 해시는 carry 문서에 별도로 기록한다.

Baseline은 `ff25485`다. Canonical BE 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 이 문서의 코드 주소는 fixed CPU 주소와 같은 파일 오프셋이다. 전체 stage callback의 자연 실행은 아직 확인하지 않았다.

## 구현 계약

기존 `run_animation_machine` API와 `AnimationMachineState`를 그대로 사용한다. 새 진입점은 아래와 같다. 실제 script/table은 기존 MS5D kind3와 program bus로 읽는다. 별도 리소스 규격이나 host continuation metadata를 추가하지 않는다.

| 진입 PC | 실행 내용 | 정상 경계 |
| --- | --- | --- |
| `49f8c` | 원본 initializer와 실제 RTS | RAM[A7]에서 읽은 return PC |
| `47cec` | object 좌표·속성 설정 뒤 아래 setup/calls | `47d20` |
| `47d0a` | A1=`489c2`, D0.low=`0100` 뒤 두 JSR | `47d20` |
| `47d10` | D0.low=`0100` 뒤 두 JSR | `47d20` |
| `47d14` | JSR `49f8c`, 복귀 후 JSR `49fc6` | `47d20` |
| `47d1a` | JSR `49fc6` | `47d20` |
| `47f04` | JSR `49fc6` | `47f0a` |

`47cec`의 순서는 WORD(A6+42)=00a0, WORD(A6+46)=0170, BYTE(A6+12)=ff, BYTE(A6+13)=ff, BYTE(A6+14)=04다. 그 뒤 `47d0a`가 A1을 설정하고 `47d10`이 D0의 하위 WORD만 바꾼다. 상위 WORD는 보존한다. 첫 JSR는 stack에 `47d1a`, 두 번째 JSR는 `47d20`을 실제로 쓴다. 정상 복귀 후 caller A7은 시작 값과 같지만 두 호출이 남긴 RAM bytes는 보존된다.

Initializer는 다음 순서를 지킨다.

1. A0=A6+26, BYTE(A6+18)=0.
2. WORD(A5−7ff0)=0, PVC `2ffff2=1000`, `2ffff0=0`.
3. **전체32bit A5**가 `108000`인지 비교. 다르면 원본 TRAP15 경로를 checked error로 보고한다.
4. LONG(A0)=A1, WORD(A0+4)=0, WORD(A0+6)=D0.low.
5. 공유 RAM의 live return LONG을 pop해 복귀한다.

A1은 initializer에서 단지 저장할 값이다. 0이나 ffffffff도 initializer 자체는 허용하며, 나중에 interpreter가 읽기 전부터 script resource를 요구하지 않는다. A6에는 canonical object 범위 검사를 덧붙이지 않는다. 실제로 도달한 bus 접근만 검증한다. RAM mirror에 쓰거나 bank shadow와 겹쳐도 원본 쓰기 순서를 유지하며, 뒤에서 shadow가 달라졌다는 이유로 PVC를 다시 갱신하지 않는다.

A0가 stack과 겹치면 pointer/timer/speed 쓰기가 return LONG을 바꿀 수 있다. 복귀 주소를 local 변수에 미리 저장하지 않는다. 성공한 대기·반환의 commit과 실패 시 모든 출력 보존은 기존 상위 transaction 계약을 따른다. 원본 TRAP·bus fault가 rollback한다는 의미는 아니다.

## Carry와 범위 경계

메인이 원본 명령을 확인했다. `47d20`은 `47d3e`로 BRA하고 `4847c`를 호출한다. `4847c`는 진입 MOVEQ로 기존 C를 지우고 끝에서 ORI/ANDI CCR로 반환 C를 결정한다. 따라서 `47d42` BCC는 애니메이션 C를 읽는 분기가 아니다. `47f0a` TST.W도 V/C를 지우므로 그 뒤 BEQ는 새 Z를 읽는다.

이 두 caller 연결에 일반 CCR을 허위로 추가하지 않았다. 다른 caller `1dc84 → 1dc8a BCC`는 애니메이션 C를 직접 읽는다. 후속 carry 단위에서 이 경로와 `210ae → 210b4 BCS`를 연결했으며, 일반 CCR 전체는 여전히 지원하지 않는다. 전체 raw caller 목록과 증거 수준은 `animation-machine-caller-inventory.md`를 따른다. Raw 후보1622개를 모두 분석·실행 완료한 caller로 세지 않는다.

`47cec`보다 앞선 `16ea4` 등의 callee와 `47d20`/`47f0a` 뒤 stage body는 이번 실행 경계 밖이다. 원본 명령 주소 전부가 공개 진입/stop 지점인 것은 아니다. 새 경로는 기존과 마찬가지로 확인된 semantic block 단위로 실행한다. 자연 scheduler/IRQ, 전체 stage callback, 직접 플레이 및 모든 animation callback의 구현 완료를 뜻하지 않는다.

## 단위 검사와 기존 회귀

`animation_machine_callers_test`의32개 API 조건은 일반 초기화, opaque A1, A6 mirror와 shadow overlap, 초기화 쓰기에 바뀐 live return, 지정 caller의 하위 WORD 보존과 JSR stack, 늦은 쓰기 실패·A5 TRAP·script 누락의 전체 rollback을 확인한다. 합성 one-command resource를 사용하는 unit은 실제 ROM script 증거와 구분한다. Normal/UBSan 모두 통과했다.

`make all test`는 Python257개/C++151개 실행, 경고0으로 통과했다. 기존 `verify_animation_machine.py`도 기본8조건+2단계와 확장85조건121단계,37재개/9오류를 다시 통과했다. 메인이1707개 고유 참조 파일 해시를 확인했다. 기존 회귀 report SHA256은 `6ebfb4ecb742bc4aa7b023a344e70e432eab9e284c099f194724cd021f622196`이다. 새 caller의 원본 대조는 별도로 기록한다.

## 새 원본 및 C++ 대조

`observe_animation_machine_callers.py`는 원본 코드를 변경하지 않고59조건/91단계를 각 fresh CPU에서 두 번 실행했다. Initializer18조건, 실제47cec setup6조건,47f04 caller35조건이다. 별도4조건은 noncanonical A5 때문에 원본 TRAP15 직전에 도달하는 것을 확인하고 중단했다. Guard를 정상 반환으로 집계하지 않는다.

`verify_animation_machine_callers.py`는 정상59조건/91단계와 guard4조건의 원본을 다시 실행하고 frozen payload와 대조했다. 실제 C++은 전체64KiB RAM,16register/PC, 상태, 독립 PVC 모델의 장치 bytes/bank, ordered ports806개가 일치했다. 외부 읽기는 이 관측군에서0회다.32회 재개는 직전 실제 C++ 출력에 기록된 host RAM 변경만 적용했다. Guard4조건과 caller 경계 밖 실행2조건은 checked API 오류 및 전체 출력 보존으로 검증했다.

두 initializer alias는 A1이 return LONG을 직접 덮거나 timer/speed가 return을00008000으로 바꾸는 경우다. 대기 연쇄에는 live indexed list-end106800, saved low BYTE77, direct sound의 saved outer A0를104900으로 바꾸는 조건을 넣었다. 실제 pop 위치에서 변경값을 읽고 새 A0에 pointer를 publish하는 것까지 관측했다. SR는 초기 설정 외 읽지 않으며, stack 차이를 mask하거나 실행 중 expected register를 주입하지 않는다.

Native 장치는 raw PVC 쓰기를 기록하고 실제 포트로 bank metadata를 계산한다. PVC read는 없고 bank ROM read는 folded bank2일 때만 허용한다. C++ 기대 PVC는 별도 pinned 모델로 포트를 접어 계산한다. 이 제한을 물리 기판 측정이나 모든 bank의 검증으로 확대하지 않는다.

독립 Sol은 정상 대표19조건+guard4조건/총43단계를 재실행하고 final native617참조 해시를 확인했다. 별도 Sol은 C++ diff와32개 unit을 독립 검토했다. 메인은 두 소스·실제 diff·검증 비교/재개 코드·단위 검사와 결과를 읽고, native617개 및 C++1233개 고유 파일 해시를 직접 확인했다.

재현 명령:

```sh
.venv/bin/python tools/observe_animation_machine_callers.py
.venv/bin/python tools/verify_animation_machine_callers.py
.venv/bin/python tools/verify_animation_machine.py
make all test
```

| 산출물 | SHA256 |
| --- | --- |
| caller native source | `20e4a8aec91053be7d21637e599c52ac3894aff22e17c11d0294ffe1dd8a52c7` |
| caller native report | `f735043941529a9e020020715735b45e60890ab8b2b94211aeb0e4fbe22e17d5` |
| caller verifier source | `1868bd074696f109460ebcb4b14a134f9225d3d096cabc37f267ed8ed97d5518` |
| caller verification report | `5b1ac7cc62ccbaba2982f83ac03ca43f61c3be69980a70ba7df55be61b49c9f5` |

이 관측은 지역적인 호출 순서의 증거이며 자연 stage 도달이나 전체 게임 완료의 증거는 아니다.
