# Animation opcode30 직접 sound 실행

## 현재 bank-state CLI schema

[실제 bank 상태 계약](animation-bank-state-contract.md)에 따라 공통 `SAVED_LIST_END` 바로 뒤 argv22에 unsigned32 `CURRENT_BANK_BASE`를 전달한다. 일반 CLI는22숫자/23JSON, RAM/output/ports argv23/24/25 및 resource26+이며, sound CLI는27숫자/28JSON, callback4개 argv23..26, EXTERNAL argv27, RAM/output/ports argv28/29/30 및 resource31+다. 두 출력 JSON은 숫자 `current_bank_base`를 항상 포함한다. 임의 uint32 bank 입력을 허용하며 saved_bank와 구분한다. 이전 schema 자동 추정이나 기본값 보충은 없다. 아래 원본 관측·검증 수치와 해시는 해당 단위 당시의 완료 기록이며, 이 schema 이행의 재검증 결과를 대신하지 않는다.


계약은 `animation-direct-sound-contract.md`를 따른다. 기준 `51bdf61`, canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 CPU 주소는 ROM 파일 offset과 같다(고정 영역). 구현은 C++11이다. 원본 관측과 C++ 비교의 검증 범위는 아래에 구분한다.

## 구현된 의미 (소스: `engine/src/animation_execution.cpp`)

- opcode30(4a2da..): A1+1(padding 미독출, 32비트 overflow checked) → D0 전체 0 → WORD(A1)+를 D0.low로 → A0/A1 LONG 저장(`saved_a0/saved_a1`) → 기존 `execute_sound_word`(3af8)를 callee로 호출한다.
- 정상 복귀(4a2ec)는 A0/A1 LONG만 복원한다. D0/D7 WORD 부호확장, `saved_bank`, PVC 쓰기는 하지 않는다. 이후 D6=A1, LONG(A0)=D6를 쓰고(4a276 경로) 다음 명령으로 진행한다.
- 대기(high/low byte wait)는 `phase=4`로 보존한다. `callback_sound_phase`(1/2), `callback_saved_low`, `callback_waiting`은 phase2와 공유하는 sound metadata다. phase4에서 `saved_bank`, `saved_list_end`, `callback_saved_a0`는 0이어야 하며(`valid`) 아니면 checked 거부한다. `sprite.waiting=false`.
- phase4 재개는 현재 canonical 레지스터/phase/saved_low/waiting으로 `SoundWordExecutionState`를 구성해 callee만 실행한다. 대기 유지 시 RAM/state/carry를 바꾸지 않고 `external_reads=0`, 포트 없음. 대기 중 A6, script, 원래 command는 다시 검사하지 않는다. high→low 전환 후 계속 대기할 수 있다.
- 완료 시 모든 direct sound metadata와 `saved_a0/a1`을 0으로 clear한다.
- `external_reads`는 호출 내 모든 30/1f callee의 uint8 읽기를 합산한다. 오류 시 RAM/state/carry/ports/읽기 횟수 모두 rollback(transaction).
- 지원 범위: 외부 입력 overload만. 기존 두 overload는 30/phase4를 checked 거부한다. 실제 call/resume에서 A5=0x108000 필요(현재 지원 제한).

## CLI

직접sound 추가 당시 `step_animation_sound_execution`은26숫자/27JSON을 유지하고 PHASE 최대값만4로 확장했다. 현재 bank-state schema는27숫자/28JSON이며 argv22 CURRENT_BANK_BASE를 추가한다. `callback_waiting`은 phase2/4, `waiting`은 phase1/3, carry는 phase!=0에서 null이다. 일반 `step_animation_execution` CLI는 변경하지 않았다(phase0/1/3만).

## 단위 시험 (`engine/tests/animation_execution_test.cpp`)

`direct_sound_calls`(6개 command, padding 미독출/MOVEM.W 부호확장 부재, 다중 읽기 합산·rollback), `direct_sound_waits`(high/low 대기, 입력 carry 보존, poisoning, 유지 중 미사용 A6, 비정상 saved A0/A1·A5 거부, 완료 시 clear), `direct_sound_metadata`(잘못된 metadata 거부, 잘린 script, 구 API 거부). 결과는 보고서 참고.

## 원본 관측과 검증 현황

`tools/observe_animation_direct_sound.py`는 수정하지 않은 원본49fc6에서207조건/255단계를 실행한다. 18대기 연쇄(high6, low6, high→low4, 순차명령2), 외부입력 읽기17회와 PVC828개를 관찰했다. 전체64KiB RAM,15레지스터,명령/읽기/쓰기 trace,스택과 복귀 carry를 기록한다. observation SHA256 `4ef6c7dd0ea871f98dacf1145e1a57fabdffb3ef587cfe3ec8cf55c7871c9386`.

high wait A7=S-18, low tailcall A7=S-12와 캡처한 low BYTE 재사용을 실제 스택·읽기 trace로 확인했다. 대기 중 원래 명령·게이트·WORD큐·오브젝트 pointer·bank를 바꾸어도 prefix를 다시 실행하지 않는다. 재개 이후 실제로 사용하는 BYTE큐 head/tail은 live 상태로 읽는다. 직접 sound 복귀에는 bank/PVC 쓰기와 D0/D7 WORD 부호확장이 없다. 관측 스크립트의 종료00,00 때문에 최종 carry는 모두 false이며, 양쪽 carry 보존과28 종료는 합성 단위 검사에서 구분해 확인한다.

메인이 별도 임시 비교 스크립트로207조건/255단계의 실제 soundCLI 전체RAM/15레지스터/metadata/carry/PVC/외부읽기 일치를 확인했다. 재개 입력은 직전 C++ 결과에 기록된 host 변경만 적용했다. 이후 공식 `tools/verify_animation_direct_sound.py`도 모든 원본 단계를 재실행하고 같은 비교를 통과했다. 48회 재개는 직전 실제 C++ 출력만 사용하며, 오류·파일 보존41조건도 통과했다. 최종 verification SHA256 `72669c031841d8c019df09addc9469848aeb3b390286ad3fdf8004a69c92851f`. 메인이 입력30개/산출물2049항목의 고유2077개 참조 해시를 확인했다. 파일 별칭 오류 검사에 복사해 사용하는 리소스도 provenance에 포함했다. `make all test`는 exit0(Python234/C++145), 독립 Sol의 UBSan 단위 검사도 통과했다.

## 남은 제약

- Sol 독립 감사에서도 원본207조건/255단계와1028개 참조 해시, guard control2개가 일치했다. 동일 Unicorn 기반 재현성 감사이며 다른 CPU 구현과의 교차 검증은 아니다. 메인 최종 리뷰는 `docs/reviews/0212-animation-direct-sound.md`에 기록한다.
- 원본 입력은 canonical A5/A6의 합성 liveRAM script다. 실제 게임에서의 도달성이나 모든 sound gate 조합을 증명하지 않는다.
- 홀수 WORD큐 주소, 실제 IRQ/Z80 소비, 사이클 타이밍, 전체 CCR은 이 관측 범위 밖이다.
- 실제 사운드 재생·자연 IRQ 소비, 3c/40 및 다른14 callback, 전체 Goal은 미완료다.


## 재현과 회귀

```sh
make all test
.venv/bin/python tools/observe_animation_direct_sound.py
.venv/bin/python tools/verify_animation_direct_sound.py
```

기존 `verify_animation_execution.py`, `verify_animation_control_execution.py`, `verify_animation_sound_execution.py`, `verify_animation_indexed_execution.py`, `verify_animation_field_execution.py`도 모두 통과했다. 현재 보고서 해시는 STATUS와 리뷰0212를 따른다. 실제 런타임은 기존 C++ binary loader와 liveRAM/MS5A 규격을 유지하며 PNG·재생용 오디오를 실행 데이터로 사용하지 않는다. 이번 원본 비교 입력은 합성 liveRAM 스크립트이고, 분리된 MS5A에서 padding 바이트 없이 실제 WORD만 읽는 경우는 C++ 단위 검사로 검증했다.
