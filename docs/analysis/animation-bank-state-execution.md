# Animation 실제 ROM bank의 저장과 대기 재개

Baseline `35aa5d5`, branch `codex/animation-banked-lookup`. canonical BE program SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 아래 고정 CPU 주소는 같은 ROM 파일 오프셋이다. `current_bank_base`는 물리 ROM byte offset이며 RAM 주소·CPU bank-window 주소·saved_bank WORD와 다르다.

## 구현한 동작

`AnimationExecutionState.current_bank_base`의 기본값은 `0x200000`이다. 실제 animation PVC 쌍을 발행할 때 이 상태를 갱신한다. RAM shadow만 바뀌거나 sound/draw가 대기하면 값을 보존한다. 기존 candidate transaction에 포함하므로 뒤늦은 오류에도 caller 상태를 바꾸지 않는다. 사용하지 않는 입력 bank는 임의 uint32를 허용한다. 실제 ROM 읽기 가능 여부와는 별개다.

첫 `2ffff2←value` 쓰기 뒤 PVC 모델은 저장 ff9의 bit15를 지운다. 이어지는 `2ffff0←0` 쓰기까지 끝난 bank는 `100000+((value&7fff)<<8)`이다. raw port WORD는 수정하지 않는다. 초기 설계의 `&ffff` 식은 첫 쓰기의 부수효과를 빠뜨렸으므로 수정했다. 이는 animation의 완전한 두-WORD 쓰기 패턴에 대한 구현이며 일반 PVC 장치 전체를 뜻하지 않는다.

기존 두 CLI 모두 `SAVED_LIST_END` 바로 뒤에 `CURRENT_BANK_BASE`를 요구한다. 일반 CLI는 숫자22개/JSON23키, sound CLI는 숫자27개/JSON28키다. 구 positional schema를 암묵적으로 추정하지 않는다. API overload와 MS5A/MS5D 버전은 유지했다. 현재 리소스 소비 검증에는 기존 실제 `animation_control/control_04276c.ms5d`를 사용한다.

## 원본 실행 근거

`observe_animation_bank_state.py`는 수정하지 않은 원본 `49fc6`을 실행한다. A6를 `100010`으로 두면 원본 field WORD `[4a76e]=0`을 사용하는 `1c 01`이 bank shadow를 쓴다. `14 03`은 원본 LONG `[4a50c]=3679e`를 읽고 실제 `4e75` RTS를 호출한다. 이어지는 `30` sound 대기와 `28` 종료를 관측한다. 비교군은 `14`를 생략하여 RAM shadow 변경만으로 bank가 바뀌지 않음을 확인한다.

- 92조건, 276단계, 대기68연쇄, PVC560쓰기, guard3개.
- high/low/high→low 대기를 포함하며 host가 consumed script, object, shadow를 바꾸는 조작은 단계 사이에 명시적으로 기록한다.
- hold는 queue head만 읽는다. 재개는 script prefix나 shadow를 다시 읽지 않는다.
- `value=8000`은 첫 쓰기 직후 bank900000, 쌍 완료 후100000이다. `value=f000`은 각각1000000과800000이다. 읽기 없는 대기에서는 ROM 밖 bank 선택값도 보존하며 ROM 크기로 wrap하지 않는다.
- 원본 관측의 bank 값은 CPU register나 물리 기판 측정값이 아니다. 실제 ordered ports를 pinned PVC 모델에 순서대로 적용해 도출했다. 관측기 포트 메모리를 완전한 PVC 장치로 취급하지 않는다.

메인은 전체 관측을 재실행했고, 별도 Sol도 92조건/276단계/1104산출물과 guard3개를 메모리에서 재실행했다. 독립 검사는 별도 `address_map.pvc_bank_update`로 560개 쓰기를 대조했다. 메인 리뷰에서 제한 설명 두 문장을 정정했으며 실행 로직이나 산출물 bytes는 바뀌지 않았다.

최종 observer SHA256: `4fc007dca23ba6aebb2886c072329c777a65cbbaf4dd9d981a457af378bb4359`.
최종 native observation SHA256: `28060b3d2ea2edcd9048929b34855e8698c13504314c81421bde9764aa7fe777`.

## C++ 대조와 재현

```sh
make all test
.venv/bin/python tools/observe_animation_bank_state.py
.venv/bin/python tools/verify_animation_bank_state.py
```

새 verifier는 원본 전체 단계와 guard를 다시 실행한 뒤 실제 sound CLI의 전체64KiB RAM, 15레지스터, pending metadata, carry, ordered ports, 외부 읽기 횟수와 bank를 대조한다. 276단계 모두 일치했고, 184회 재개는 직전 실제 C++ 출력과 기록된 host 변경만 사용했다. begin에는 실제 MS5D를 주고 이후 모든 재개는 리소스 없이 수행한다. 기대 bank는 원본 ports에서 독립적으로 계산한다. 추가 오류5조건은 거부와 파일 보존을 확인하며, 내부 rollback 자체는 C++ unit으로 검증한다.

최종 verifier SHA256: `404b12b683d7910a56b3e2e3b29a59b3bb1e81c2ccbd527e3c94d081f904e763`.
최종 verification SHA256: `efc034849e741abbaedfc92478a0cafc85dad370f3b632fce1da2c24b0d6ad67`.
메인은 입력43개/산출물2220참조의 고유2256개 해시를 확인했다.

기존 일곱 animation verifier도 새 schema로 모두 통과했다. 각 보고서의 현재 SHA는 리뷰0214에 기록했다. 전체 고유24461참조를 메인과 독립 Sol이 확인했다. `make all test`는 C++ 실행145개, Python243개, 경고0으로 통과했고 별도 core normal/UBSan도 통과했다.

## 범위와 다음 작업

새 원본 fixture는 합성 live-RAM script와 제어된 queue를 사용한다. 자연 scheduler/IRQ/Z80 진행이나 전체 게임 도달성은 증명하지 않는다. banked ROM 데이터 읽기, opcode40, 다른 callback 전체 지원은 이번 결과에 포함하지 않는다. animation 전체17명령 중 완료14종과14/3c 일부 지원이라는 기존 집계는 그대로다.

후속40 설계에는 current bank에 따른 MS5D kind2 선택뿐 아니라 RAM mirror, LONG의 영역 경계, PVC 데이터 읽기 및 24-bit bus 의미가 필요하다. `animation-banked-lookup-design.md`에 근거와 기존 bounded observer의 scratch stack 한계를 기록했다.

## 추가 원본 모델 확인

기존 pinned revision `df09546b783c419889a2386bec9402883574b881`의 헤더도 메인이 확인했다. cartridge wrapper는 선택 인자를 사용하지 않고 PVC 장치의 `get_bank_base()`를 호출하며, cart RAM은 uint16_t 배열이다. 이는 native 보고서의 발췌에 없던 선언을 보완하는 정적 근거다. [pvc.h](https://raw.githubusercontent.com/mamedev/mame/df09546b783c419889a2386bec9402883574b881/src/devices/bus/neogeo/pvc.h), [prot_pvc.h](https://raw.githubusercontent.com/mamedev/mame/df09546b783c419889a2386bec9402883574b881/src/devices/bus/neogeo/prot_pvc.h).
