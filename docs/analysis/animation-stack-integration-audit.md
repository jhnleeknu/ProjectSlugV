# Animation shared stack 통합 API 감사

기준 `68bd083`, branch의 현재 `animation_execution`, `sprite_submit_execution`, `object_sound_lookup`, `sound_word_execution`, `sound_byte_execution`을 읽었다. canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8,388,608 bytes, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 아래 고정 CPU 주소는 같은 ROM 파일 offset이다. ROM·기존 관측·구현을 수정하거나 빌드하지 않았다.

이 문서는 [stack 접근 목록](animation-stack-access-inventory.md)의 후속 API 감사다. **원본 명령과 현재 코드의 차이는 사실, 새 API와 통합 순서는 제안**이다. 새 의미/API의 최종 결정은 메인이 한다. 기존 원본 관측은 RAM과 분리된 scratch stack을 사용한 증거이며 shared RAM stack alias의 검증으로 확대하지 않는다.

## 현재 상태가 보존하는 것과 보존하지 않는 것

`AnimationExecutionState`는 `sprite.registers`의 D0..D7/A0..A4, 별도 A5/A6와 phase0..4를 가진다. `saved_a0/a1/bank`, `saved_list_end`, `callback_saved_a0`, `callback_sound_phase/saved_low/waiting`은 stack frame의 일부 값을 host metadata로 대체한다. A7, 원본 return LONG, 현재 PC, stack BYTE padding은 상태에 없다. `current_bank_base`는 실제 PVC 장치 상태이며 saved bank WORD의 대체물이 아니다.

`SpriteSubmitExecutionState`, `SoundByteExecutionState`도 13레지스터와 waiting만 가진다. `SoundWordExecutionState`는 여기에 phase/saved_low를 붙이고 `ObjectSoundLookupState`는 A5/A6와 phase/saved_a0를 붙인다. 이 API들은 68000 호출 frame을 쓰거나 pop하지 않는다. 따라서 기존 metadata 값을 RAM에 한 번 복사하는 것만으로 shared stack 실행을 구현할 수 없다.

원본 명령 순서를 실제 bytes와 대조한 핵심 지점은 다음과 같다. 완전한 목록과 PC witness 범위는 앞 문서를 따른다.

| 원본 CPU / offset | 메모리 동작 | 현재 대체 위치 | shared stack에서 필요한 차이 |
|---|---|---|---|
| `4a104`, `4a26c` BSR | return LONG push | `draw()` 직접 호출 | draw operand를 읽기 전 원본 위치에서 push; return 시 실제 LONG 소비 |
| `4a1dc/1e0`, `4a200/226` | A0/A1 LONG·bank WORD push/pop | `animation_execution.cpp:96..106,149..154` | 저장·복원 모두 live stack bus 사용 |
| `4a204/222` | D0/D7 WORD push/pop, signed16→32 | `draw_return()` local low WORD | 중간 RAM 쓰기와 live 재읽기, signed restore 모두 필요 |
| `4a23e`, `4a270` | list end PEA/pop A1 | `indexed_draw()`, phase3 `saved_list_end` | draw의 saved A1과 다른 live LONG; 복귀 후4a276 publication 없이49ffe로 진행 |
| `4a2e2/2e6/2ec` | A0/A1 LONG·return4a2ec push/pop | `direct_sound():243..257` | bank/MOVEM.W를 추가하지 않고 원래 LONG frame만 소비 |
| `4a30c/332/338/352`, `4a354..37c` | 3c outer frame·return4a354·WORD 임시 frame | `callback()`, `callback_return()` | push 시점부터 실제 메모리 효과; 복귀 bank/A1/A0 live 읽기 |
| `4a408/41e/422/43c`, `4a43e..466` | 14 outer frame·return4a43e·WORD 임시 frame | 같은 callback 경로 | 3c와 복귀 PC 차이를 유지 |
| `cd5c`, `cd50`, `ce00` | callback returncd5e push/pop, draw return pop | `execute_sprite_submit()` default callback 검사·함수 return | default RTS여도 실제 stack write/read와 dead bytes를 생략하지 않음 |
| `47672/ca74`, `47682/688/68e` | 임시 return47678, inner A0·return4768e, A0 pop | `object_sound_lookup.cpp:run`, `saved_a0` | 임시 슬롯 재사용까지 원래 순서; source A0를 live pop한 뒤 source 재읽기 |
| `3bfa/3bfc/3c00/3c02` | low BYTE push, return3c00, BYTE pop, tailcall3ac8 | `sound_word_execution.cpp:submit/run`, `saved_low` | A7 BYTE stride2, padding 보존, pop 시 live BYTE 소비; tailcall은 return 추가 없음 |

## Frame 위치와 반환의 구분

S는 whole49fc6 진입의 A7이며 `[S,S+4)`의 caller return LONG은 호출자가 제공한다. 아래는 원본 push 폭으로 정해지는 정상 제어 흐름의 슬롯이다. 이전 관측에서 같은 깊이를 확인했어도 **실제 RAM mirror의 해당 bytes가 다른 게임 데이터와 겹치는 실행까지 검증한 것은 아니다**.

| 경로 | 장기 보존 슬롯 | wait의 A7 / top return |
|---|---|---|
| direct04 | S−4 draw return4a108; S−12 A0; S−8 A1; S−14 bank | S−18 /4a200 |
| indexed10 | S−4 list end; S−8 draw return4a270; S−16 A0; S−12 A1; S−18 bank | S−22 /4a200 |
| direct30 | S−8 A0; S−4 A1; S−12 sound return4a2ec | high S−18 /3c00, saved low BYTE S−14; low S−12 /4a2ec |
| callback14/3c→47672 | S−4 outer A0; S−8 outer A1; S−10 bank; S−14 outer return4a43e/4a354; S−18 inner A0; S−22 sound return4768e | high S−28 /3c00, saved low BYTE S−24; low S−22 /4768e |

`cd5c JSR(A0)`은 direct04의 S−22/indexed10의 S−26에 임시 returncd5e를 쓴다. defaultcd50 RTS 뒤 A7은 돌아오지만 bytes는 지우지 않는다. `47672 JSRca70`의 return47678은 callback frame의 S−18을 먼저 쓰고, sound branch가 같은 위치를 inner saved A0로 덮는다. 이런 dead stack bytes도 후속 opcode40의 RAM mirror 읽기에 관측될 수 있다.

`4a222/4a376/4a460 MOVEM.W`는 D0/D7을 각각 signed WORD로 full32 확장한다. callback/ordinary draw에서 이 규칙이 필요하지만 direct30의 `4a2ec MOVEM.L`에는 적용하지 않는다. 원본 `4a270` list-end pop과 direct30의 A0/A1 pop도 서로 바꾸지 않는다.

`RTS`는 host의 고정 함수 복귀가 아니라 live LONG→PC와 A7+4다. 현재 phase는 올바른 미변경 frame의 정상 복귀 위치를 암묵적으로 선택한다. shared stack에서 return LONG이 바뀌면 현재 metadata만으로 같은 PC 흐름을 정할 수 없다. known continuation과 caller 완료를 구분하는 return dispatch, 실제 PC 상태 또는 동등한 제어 표현이 필요하다. 불일치 return을 조용히 원래 PC로 고치는 것은 허용할 수 없다. 미지원 target을 checked 실패로 처리할지 더 일반적인 실행으로 확장할지는 메인의 지원 계약 결정이며, 이를 전체 게임의 최종 완료 범위 축소로 삼으면 안 된다.

## Live restore가 달라지는 구체적 지점

1. **저장 이전 push부터 alias가 작동한다.** `4a104`의 return push는 draw operand fetch보다 앞이고 callback14는 `4a408`에서 A0를 저장한 뒤 selector/operand를 읽는다. stack이 script와 겹치면 parser가 읽는 bytes 자체가 달라질 수 있다. 이미 파싱한 metadata를 나중에 stack에 쓰는 방식은 원래 순서가 아니다.
2. **bank pop 뒤 임시 MOVEM.W가 shadow를 다시 바꿀 수 있다.** `4a200`은 pop한 bank를 live A5−7ff0에 쓰고 `4a204`가 D0/D7 WORD를 stack에 쓴 뒤 `4a208`이 shadow를 다시 읽는다. 현재 `draw_return()`은 bank 쓰기와 shadow 재읽기를 구현하지만 중간 stack 쓰기를 생략한다. shadow가 임시 슬롯과 겹치면 장치 bank 계산과 뒤 signed restore가 모두 달라질 수 있다. 예를 들어 direct04 S=100020이면 임시 D0 WORD의 주소 S−16=100010이 canonical A5−7ff0와 같다. 이는 정적 alias 후보이며 이 문서에서 whole original 실행 성공을 주장하는 새 fixture는 아니다.
3. **outer와 inner A0가 다르다.** callback47672의 `4768e`는 inner source pointer를 pop한 뒤 `47690` source BYTE를 object+7e에 쓰고, 이어 live source WORD/lookup을 읽는다. 현재 inner `saved_a0`는 source의 live 데이터 변화는 허용하지만 stack 슬롯이 새 pointer로 바뀌는 것은 표현하지 않는다. outer saved A0는 이후 interpreter pointer publication에 쓰인다. 두 값을 하나로 합칠 수 없다.
4. **captured low의 capture 장소가 달라진다.** 현재 `saved_low`는 low BYTE를 host에 보존하고 high 완료 후 D0.byte에 대입한다. 원본은 source에서 읽은 low를 `3bfa` stack BYTE에 저장하고, high 완료 뒤 `3c00`에서 그 당시의 stack BYTE를 읽는다. high wait 중 source/command를 바꿔도 원래 stack BYTE가 유지되면 low는 유지된다. 반대로 stack BYTE를 바꾸면 low가 달라질 수 있다. current capture 방식이 잘못됐다는 일반 주장이 아니라 scratch-stack fixture에서 증명한 범위를 넘는 새 요구다.
5. **BYTE padding은 값이 아니다.** A7 predecrement BYTE는2를 빼고 한 BYTE만 쓴다. S−13/S−23 padding을 zero로 만들거나 두 BYTE를 모두 low 값으로 채우지 않는다. pop도 한 BYTE만 읽고2를 더한다. padding은 기존 RAM bytes로 남아 후속 일반 읽기에 보일 수 있다.
6. **low wait에는 saved low pop이 이미 끝났다.** high→low 변환 뒤 low는 현재 D0.byte이고, top return은 outer sound return이다. 계속 low 대기하는 동안 옛 high saved-low 슬롯을 다시 읽거나3bfa를 재실행하면 안 된다. high hold도 아직 실행되지 않은 pop/RTS를 미리 소비하면 안 된다.
7. **queue/stack 교차는 prefix와 poll을 바꾼다.** high low BYTE/return push 또는 sprite callback JSR가 queue head/tail/source와 겹칠 수 있다. queue 쓰기는 다시 pending return/source slot을 바꿀 수 있다. 기존 byte wait의 live head poll과 register-captured destination은 유지하되, 원래 stack 동작을 둘러싼 메모리 순서가 추가되어야 한다.

## 기존 callee의 RAM·주소 제약

| 경로 | 현재 제약 | shared bus 통합 시 검토 대상 |
|---|---|---|
| animation read/write/script/data | `ram_span`: int64(base)+displacement, canonical `[100000,110000)`의 complete span; RAM script도 canonical뿐 | 32-bit wrapping address 계산과24-bit bus 선택,16RAM mirrors, LONG의 두 WORD 경계. 기존 fixed MS5A 명령 의미는 유지 |
| spritecd58 | queue/callback pointer absolute canonical 주소; A5 input 없음; callbackcd50만 허용; reached animation call/resume A5=108000 | A5-relative 원본 접근을 fullmode의 A5로 전달, mirror 대응; defaultcallback push/pop도 실제 수행. 다른callback은 별도 분석 필요 |
| sound3ac8 | hardcoded104cf4/104d74/76, canonical destination BYTE; A5 input 없음 | 원본 A5-relative queue를 fullmode에 전달. waiting captured A0는 raw32 register이며 실제 쓰기는 bus 선택 |
| sound3af8 | hardcoded gates/queue104d82..8c, canonical aligned WORD; phase/saved_low | 새 stackctx와 A5, live low BYTE pop, source/write mirror 지원. externalD00046는 실제 도달 시에만 입력/카운트 |
| object47672 | 일반 A5/A6는 reached canonical span 검사, sound이면 A5=108000; RAM/fixed lookup canonical | live inner stack restore와 source의 bus 읽기; lookup window/physical resource 경로는 새 공통 reader와 조정 |

따라서 animation에 A7만 추가하고 기존 callee를 그대로 호출하면, stack frame을 관측 가능하게 쓰더라도 A5/mirror 및 내부 live restore는 여전히 미구현이다. 반대로 공통 program bus를 stack에만 사용하는 것도 기존 script/object/source reader의 mirror 제약을 자동 해소하지 않는다. read-only program bus와 RAM writer는 재사용 후보지만 stack RAM 밖의 MMIO write, physical fault·timing을 이미 지원한다고 주장하지 않는다.

## 상태·API에 필요한 정보 — 제안

최소 기능 목록은 다음과 같다. 이름과 struct 분리는 메인 결정 사항이다.

- caller 소유의 전체15register+A7와 원래 논리32-bit PC 또는 동등한 resume 위치. A7은 phase에서 역산하는 상수가 아니라 push/pop마다 변하는 실제 값이다.
- shared64KiB RAM에 실제 stack writes/reads. rawSP는32-bit wrap 후 bus24로 해석하고 RAMmirror는 같은 storage를 사용한다. WORD/LONG의 정렬·각 WORD의 reached span을 검사한다. BYTE push/pop stride2는 stack helper의 별도 규칙이다.
- 실제 current bank와 필요한 explicit vector/PVC views·kind3 physical storage를 가진 bus context. saved bank는 RAM 슬롯에서 복원하며 current bank와 독립이다. PVC 장치 writes/ports는 원래 순서로 반영한다.
- sprite wait와 sound high/low wait의 제어 위치. waiting snapshot의 live registers는 그대로 필요하지만 saved A0/A1/list-end/low를 metadata에서 권위 있게 복원하지 않는다. 별도 diagnostic capture를 남겨도 live slot을 capture와 다르다는 이유만으로 거부하지 않는다.
- caller return 처리와 known internal return dispatch. phase만으로 암묵적 RTS를 건너뛰지 않는다. 지원하지 않는 return target/장치 접근은 실행 전 checked 실패와 명시적 scope로 관리한다.
- 원래 요구한 성공 wait의 효과 commit, 완료/실패의 상태·RAM·ports·external count·carry 보존. 기존 각 API의 copy/swap transaction을 바깥 shared context까지 포함한다. borrowed context의 원본 RAM/PVC를 candidate 실행 중 직접 변경하지 않도록 수명을 설계한다.

공개 fullmode는 최소16register, resume/완료 상태와 current device bank를 반환해야 native stack pointer를 대조할 수 있다. caller가 이미 RAM에 return LONG을 제공하는 방식과 API가 caller sentinel을 push하는 방식은 서로 다른 entry 계약이므로 하나를 명시해야 한다. 기존 원본 fixture의 synthetic sentinel을 자연 caller frame으로 부르지 않는다. entry A7과 final A7 모두 검증 대상이며 종료 때 dead bytes를 지우지 않는다.

## API 전환 선택지

| 선택 | 장점 | 필수 주의점 |
|---|---|---|
| 별도 full state/API, legacy metadata API 유지 | 과거 scratch-stack 대조·CLI schema의 의미를 보존하고 sharedstack 계약을 명확히 구분 | fullmode를 임시 축소판으로 고정하지 않음. supported animation+callee의 실제 frame/alias 지원을 완료하고, 기존 API를 fullmode로 호출하는 adapter는 실제 entrySP/frame 없이 정확한 동등성을 주장하지 않음 |
| 기존 state/API를 A7/PC/bus 기반으로 전환 | 최종 엔진의 상태 권위를 하나로 통일 | 모든 CLI·verifier·save metadata와 transaction 계약을 명시적으로 migration. 과거 reports는 역사적 scope로 유지; capturemetadata와 liveRAM 중 어느 쪽이 권위인지 혼합하지 않음 |
| 기존 함수 안에 선택적 fullmode flag 추가 | 호출 표면 변화가 작음 | 같은 필드가 mode별로 다른 의미를 가지므로 검증·serialization이 복잡해짐. 기본값이나NULL stackctx로 조용히 legacy fallback하는 방식은 피함 |

감사자의 제안은 **명시적 full state/API를 먼저 분리하고 구현·원본 sharedRAM 검증이 완료되면 엔진 소비 경로를 전환**하는 것이다. legacy 지원은 기존 증거의 재현을 위한 수단이며 전체 목표에서 alias·변경된 live return·A5/mirror 지원을 제외하는 근거가 아니다. 새 opcode별 CLI를 늘리는 결정까지 이 문서가 요구하지는 않는다.

## 새 원본 증거와 검증에 필요한 목록

현재 scratch-stack whole49fc6 자료와 isolated banked handler의 실제 RAMmirror 자료를 합쳐 sharedstack 일치를 주장하지 않는다. 다음은 새 통합 검증의 요구 목록이며 완료 수치가 아니다.

1. 동일한 RAM backing에16mirror와 실제 stack을 두고 original instructions를 그대로 실행한다. stack이 routine/object/script/queue와 겹치지 않는 baseline부터 모든 지원 경로의 fullRAM16R/PC/read/write/PVC 순서를 확인한다. 기존 sentinel·source해시·backend 한계 유지.
2. direct04/indexed10/direct30/callback14·3c의 각 wait/hold/release 및 high→low를 같은CPU로 이어 실행한다. C++ resume는 직전 실제 출력+기록된 host mutation만 받는다.
3. 실제 stack low BYTE, inner source A0, outer A0/A1/list end/bank slot의 개별 mutation과 queue·shadow·script alias를 원본에서 실행한다. 단순 mutation이 original return target까지 바꾸는 경우는 결과PC를 먼저 분류한다. 예상metadata를 원본 CPU에 주입하지 않는다.
4. padding 불변, 임시 JSR/BSR/MOVEM의 write order 및 dead bytes를 대조한다. 원본 복귀 후 opcode40이 dead stack bytes를 읽는 경우는 별도의 wholecall 결과로 검증한다.
5. logicalSP highbits/32wrap/24mask, RAMmirror 내부 경계와 mirror→bank write 실패, late restore/source failure를 검사한다. synthetic CPU alias 모델과 물리 측정은 구분한다.
6. fullmode가 기존 legacy snapshot과 다른 RAM bytes를 내는 것을 masking projection으로 숨기지 않는다. 새로운 지원 계약의 전체 RAM과 실제 후속 읽기 결과를 비교한다. CCR 전체를 현재 backend hostSR만으로 검증했다고 하지 않는다.

## 메인에게 남기는 결정 질문

- 실제 entry/완료 계약은 caller가 frame을 공급하는 full49fc6 call인가, 별도 caller wrapper인가? A7/PC를 새 state에 어떻게 노출할 것인가?
- live RTS target이 원래 continuation과 다를 때 어디까지 원본 코드를 실행하고 어떤 미지원 상태를 checked 보고할 것인가? 지원 완료 목표와 당장 구현 경계를 별개로 기록해야 한다.
- A5-relative sprite/sound와 canonical-only object/script reader를 함께 전환할 것인가, 단계적으로 fullmode callee를 분리할 것인가? A7만 추가하는 통합으로는 충분하지 않다.
- shared PVC view와 current bank·ordered ports의 권위/transaction 소유권을 어떻게 합칠 것인가? stack bank restore는 capture값보다 liveRAM이 우선이다.

이 문서는 새 C++ 동작이나 sharedstack native 성공을 선언하지 않는다. 원본 의미와 API 설계 결정을 위한 영향 목록이다.
