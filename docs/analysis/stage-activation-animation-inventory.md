# Stage activation animation helper inventory

후속 공유 stack 통합은 `animation-machine-activation-execution.md`를 따른다. `6c90612` 이후16ea4/16ed2와47cae..47d20의 실제 호출·대기 경로를 연결했다. 아래 기존 API·미구현 분류와 검증 수치는 작성 당시 기록이며, 일반 stage 활성화 전체 완료를 뜻하지 않는다.

`47c6c` 활성화 경로에 필요한 `16ed2`, `16ea4`, `47672`, `49f8c`, `49fc6`의 기존 구현·검증 자료 목록이다. 전체 callback 구현 또는 자연 게임 진행 검증 결과가 아니다. canonical BE 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 아래 주소는 고정 CPU 주소이며 같은 값의 canonical ROM 파일 오프셋에 대응한다. 뱅크 데이터의 별도 대응은 아래에 명시한다.

기존 C++ API와 검증 문서의 사실을 먼저 기록하고, 새로 확인한 명령열은 **메인 의미 검토가 필요한 정적 근거**로 구분한다. 자동 역어셈블만으로 helper 분석 완료를 선언하지 않는다. 이번 작업에서는 원본·코드·리소스·검증 출력을 변경하지 않았고 기존 검증을 재실행하지 않았다.

## 구현 상태

| 원본 진입 | 현재 C++ 상태 | 재사용 가능한 부분 / 남은 계약 |
| --- | --- | --- |
| `16ed2` | 정확한 helper 공개 API 없음 | 두 RAM WORD 비교와 object bit 갱신의 전체 레지스터·정수 폭 계약 필요. 인접 `16ef0`은 다른 분기이므로 혼용 금지. |
| `16ea4` | 정확한 wrapper API 없음 | `execute_sprite_submit`은 `cd58` 전체 실행과 생산자 대기 재개를 제공한다. wrapper의 좌표 계산, A5 설정, A6 및 호출자 레지스터 보존·복귀 연결은 별도 필요. |
| `47672` | 정확한 helper API 없음 | `execute_sound_word`는 `3af8` 전체 실행과 high/low byte 대기 재개를 제공한다. `ca70`, 호출자 A0 보관, `4411e` 조회, sound 대기 이후 복귀점이 별도 필요. 기존 `47642..47672` 입력 루프 범위는 끝 주소 exclusive이며 이 helper를 포함하지 않는다. |
| `49f8c` | 정확한 전체 초기화 API 없음 | 기존 fixture는 상태 pointer/timer/speed를 직접 설정한다. 초기화의 A0·RAM 변경, 실제 PVC 쓰기, A5 검사와 TRAP 경로는 검증된 전체 API로 노출되지 않는다. |
| `49fc6` | 부분 구현 있음 | `step_animation` / `step_animation_with_data`는 RAM·carry 중심의 지원 opcode interpreter다. 전체 15개 레지스터, 실제 PVC 출력 및 sprite 대기 continuation을 반환하지 않는다. 따라서 full callback에 그대로 연결하는 것은 근거 부족이다. |

확인한 공개 헤더는 `engine/include/ms5/animation_step.h`, `animation_draw.h`, `animation_resource.h`, `sprite_submit_execution.h`, `sound_byte_execution.h`, `sound_word_execution.h`다. `SpriteSubmitExecutionState`와 sound 상태의 `registers`는 `SceneMapTransferState` (`D0..D7`, `A0..A4`)이며, 상위 wrapper가 A5/A6를 별도로 보존해야 한다.

## 원본 호출 및 상태 대응 — 정적 근거

`artifacts/stage_activation_static.json`과 `stage_activation_remaining_static.json`에 `47c6c` 부근 호출 명령이 남아 있다. 해당 경로의 한 갈래는 `47cc0 → 16ed2`, `47cc6 → 47672`, object+14 설정, object+7e에 따른 `48a12` LONG 조회, `47ce6 → 16ea4`, object 좌표·속성 설정, `A1=489c2`, `D0.low=0100`, `47d14 → 49f8c`, `47d1a → 49fc6` 순서다. 조건에 따라 이 갈래를 건너뛰므로 모든 호출이 매번 실행된다는 뜻은 아니다.

다음은 canonical 프로그램에서 `tools/disassemble_program.py`의 검증 로더와 명령 decoder로 읽은 범위다. 새 helper의 의미·지원 범위는 메인이 확정해야 한다.

* `16ed2..16ef0`: `WORD(A5+0d3e)`를 D0.low에 읽고 `WORD(A5+0d46)`와 비교한 뒤 BGE에 따라 object(A6)+15의 bit2를 clear/set한다. A5=`108000`이면 두 RAM 주소는 `108d3e`, `108d46`이다. D0 상위 WORD 보존과 signed 비교를 검토해야 하며, 필드에 게임 의미 이름을 부여하지 않았다.
* `16ea4..16ed2`: A5=`108000`, D3=0, D2.byte=object+53을 설정한다. D0의 SWAP/ADD.W와 D2의 LSR.B/SUBX.W를 이용하여 object+42/+46을 더하고, D1=LONG(object+12), D5.low=WORD(object+1e)를 읽어 `cd58`로 tail jump한다. D7은 호출자가 공급한다. 대기 재개 시 이 전처리를 다시 실행하지 않는 continuation이 필요하다.
* `47672..476bc`: `ca70` 뒤 `(A0).byte`와 object+7e를 비교한다. 다르면 A0를 stack에 보관하고 D0.low=`1ac0`으로 `3af8`을 호출한 뒤 A0를 복구한다. 이후 object+7e를 갱신하고 `(A0).word`의 low BYTE를 ADD.B/BVC와 `AND.W 00fe`로 처리해 `4411e`에서 WORD를 읽는다. SUBQ.W/BCC 후 D1.byte를 object+12에 저장한다. `ca70`의 짧은 명령열은 A0=`A5-76a4`; A5=`108000`이면 `10095c`다. sound 대기는 보관한 A0 및 복귀점을 유지해야 한다.
* `49f8c..49fc6`: A0=`A6+26`, object+18 BYTE=0, WORD(A5-7ff0)=0을 기록한다. 이어 `2ffff2`에 WORD `1000`, `2ffff0`에 WORD 0을 쓴다. A5가 `108000`이 아니면 TRAP15를 거친다. 정상 갈래는 A1을 state+0 LONG, 0을 state+4 WORD, D0.low를 state+6 WORD로 저장한다. RAM shadow만 쓰는 기존 API로 실제 PVC 효과를 대신했다고 주장할 수 없다.

`47c6c`의 다른 호출 `4e286`, `4843c`, `4e216`, `bee`, `4847c` 및 후속 분기도 full callback 계약의 별도 의존성이다. 위 다섯 helper를 해결하는 것만으로 callback 전체가 완성되지는 않는다.

## 기존 animation API의 실제 범위

`engine/src/animation_step.cpp`의 state는 object+26 LONG pointer, +2a WORD timer, +2c WORD 감소량이다. RAM은 CPU `100000..10ffff`의 정확히 64KiB다. pointer=0이면 RAM `100010` WORD를 0으로 만들고 carry=true로 반환하며 빈 script도 허용한다. active 경로는 shadow를 0으로, `10d742` BYTE를 0으로 만들고 object+17이 signed 양수일 때 감소시킨다.

기본 API는 `00/04/08/28`, data API는 여기에 `0c/10/14`를 추가한다. `14`는 selector `1d/1e`만 지원하며 object+7c/+7d BYTE index로 operand base+index*4의 LONG을 읽어 object+78에 저장한다. `10`과 `0c`는 fixed data window의 selector 조회를 사용한다. 개별 확장 필드는 별도로 범위를 검사한다. 일부 초기 분석 문서의 “미지원” 문장은 이후 구현보다 오래되었으므로 현재 헤더·소스를 우선해야 한다.

script fetch는 전달한 **단일 host vector**만 읽는다. fixture가 RAM 주소를 script_base로 주더라도 live RAM을 fetch하는 reader가 된 것은 아니다. `08` 분기 등도 이 vector 안에서 유효해야 한다. data windows는 CPU/ROM 주소가 같은 `100000` 미만의 비어 있지 않은 고정 ROM 범위이며 중첩을 거부한다. unsupported 명령, fetch 실패, 10000명령 제한, 생산자 대기는 RAM·carry를 보존하며 실패한다.

draw 경로는 `decode_animation_draw`의 `D0/D1/D5/D7` 결과를 기존 RAM API `submit_sprite`로 전달한다. `SpriteWaiting`이면 `animation sprite producer wait cannot resume in this API` 오류다. 최신 `execute_sprite_submit`의 captured `cda4` 대기 상태를 아직 사용하지 않는다. transform의 네 결과 레지스터 검증을 `49fc6` 전체 레지스터 검증으로 확대하면 안 된다.

## 리소스 및 기존 native fixture 근거

| 자료 / 도구 | 실제 제공 범위 | 활성화 경로에 대한 한계 |
| --- | --- | --- |
| `animation-wait.md`, `analyze_animation_wait.py --cpp` | 문서상 native/C++ 2000 RAM·carry 조건. wait 1920 + null/28 80. RTS 뒤 emulator SCS stub으로 carry를 포착하고 scratch를 복구한다. | 전체 레지스터/PVC/대기 재개 증거 아님. 원본 파일은 수정하지 않지만 emulator에는 검증 stub이 있다. |
| `animation-draw.md`, `analyze_animation_draw.py --cpp` | native transform 3072조건과 32 skip 조건; `verify_sprite_pipeline.py --blocks --flips --animation`은 124제출·32단계 RAM/video 비교를 기록한다. | `49fc6` 전체 호출자 레지스터·pending 상태 검증 아님. |
| `animation-rom-loop.md`, `pack_animation.py`, `verify_animation_pipeline.py --rom-script` | 실제 MS5A `6f1e2` script 및 MS5C 로더를 사용한 8시퀀스, 96 interpreter 호출·192 video 단계 비교를 기록한다. caller `1e6a6..1e6b6` 바이트도 검사한다. | script는 `489c2`가 아니다. fixture는 초기 animation state를 직접 설정하며 C++ `49f8c`를 실행하지 않는다. |
| `animation-callback-1e.md`, `analyze_animation_callback.py --cpp` | selector1e의 1536 RAM·carry 조건과 MS5D 로드 비교를 기록한다. | bounded 조회창 검증이며 자연 script 전체/논리적 table 범위 검증 아님. |
| `pack_animation_data.py` | MS5D v1 `4a76c` 290byte selector창, `6431a` 1024byte callback1e창. | `4411e`, `48a12`, `489c2`를 제공하지 않는다. |
| `pack_animation_branch.py`, `verify_animation_branch_resource.py` | 다른 caller `2bb06`과 script `65f56..662c2`의 `0c/14/10/00/08` 경로용 MS5A/MS5D 자료. | 지원 opcode가 겹친다고 `489c2` 전체 지원을 추정할 수 없다. |

MS5A v1 kind1은 fixed-ROM script bytes를 보존하며 CPU=ROM 주소와 CRC/길이를 C++ `load_animation_resource`에서 검증한다. `6f1e2` fixture의 composition IDs `528ca/530ca/538ca/540ca`는 CPU `284d7a/284d86/284d92/284d9e`, bank `400000`, ROM `484d7a/484d86/484d92/484d9e`에 대응한다. 이는 `489c2`에 필요한 composition 목록이라는 뜻이 아니다.

새 경로에서 확인할 resource 요구는 `47672`의 `4411e + D1.W` WORD read, `47cd0..47ce0`의 `48a12 + object[7e]*4` LONG read, 그리고 `489c2` script 및 그 명령이 참조하는 모든 데이터다. table의 논리적 전체 길이·script 종료 경계·composition 목록은 아직 확정하지 않았다. 주소만으로 임의 extent를 포장하지 않는다. `trace_animation_references.py`의 초기화 패턴 목록도 완전한 참조·자연 도달성 증거가 아니다.

## full callback까지의 최소 신뢰 경로

1. 메인이 위 짧은 helper 명령열의 정수 폭·부호·주소·TRAP 계약을 확정한다. `16ed2`와 `49f8c`는 독립 full-register/native 비교 대상으로 분리할 수 있다.
2. `47672`는 기존 sound-word 실행 상태에 호출자 A0와 반환 phase를 붙이는 계약, `16ea4`는 기존 sprite-submit 상태에 A5/A6 및 wrapper 반환을 붙이는 계약을 먼저 확정한다. 실제 대기 경로를 생략하지 않는다.
3. `4411e`, `48a12`, `489c2` 및 script 참조의 검토된 읽기 범위를 버전 리소스로 만들고 실제 C++ 로더 소비를 검증한다. 기존 packer의 다른 script 성공을 이 리소스의 증거로 대체하지 않는다.
4. full `49fc6`는 기존 opcode 의미를 재사용하되 전체 레지스터, 실제 PVC 쓰기, live/fixed fetch 정책, unsupported 명령 및 생산자 wait continuation을 명시해야 한다. 지원 script 경로를 먼저 원본과 비교하고 지원 범위를 기록한다.
5. 나머지 `47c6c` callees·분기를 포함한 연속 callback native/C++ 비교 이후에만 callback 지원을 주장한다. 제어 fixture 성공과 자연 게임 실행은 별도로 기록한다.

이 목록은 구현 우선순위와 남은 계약을 위한 근거다. 새 helper의 native 실행 보고나 full callback 통과 보고는 이번 작업에서 생성하지 않았다.
