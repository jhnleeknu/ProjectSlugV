# 재개 가능한 메인 프레임

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 여기의 fixed CPU 주소는 복호화 프로그램 파일 오프셋과 같다. 실제 런타임 리소스는 기존 MS5D/MS5P/MS5C를 사용한다.

`MainFrameState`는 다음 실행 경계, 오브젝트 주소, 전체 D1/D3와 사운드·sprite 대기 상태를 보관한다. `step_main_frame`은 한 번에 입력·제어기 한 프레임까지만 실행한다. ec4를 반환하면 다음 호출에서 다음 프레임을 시작한다.

| 진입 PC | 처리 |
| --- | --- |
| e74 | 초기 화면 명령, 사운드 비우기, sprite·배경·팔레트 준비 후 ec4 |
| 3aea | 저장된 사운드 byte enqueue 대기에서 준비 재개 |
| 16bd0 | 정렬된 sprite 소비 대기에서 준비 재개 |
| ec4 | 조건부 main debug 출력 후 ef2 대기/입력 |
| ef2 | 프레임 신호와 임계값 비교 후 준비된 경우에만 입력 |
| f12 | 입력 접두부와 제어기/호출자 |
| f4c | 콜백·팔레트 처리 뒤 신호 비영 대기 후 입력 |

원본 ec4..ef2는 debug 출력, ef2..f12는 신호 비교와 video read, f12..f3c/f54는 입력과 콜백 선택이다. f54의 제어기 결과는 ec4 루프, fee TRAP 경계 또는 정상 반환으로 이어진다. f4c는 callback 경로의 별도 대기다. 대기 시 state.next_pc가 해당 대기 경계로 남으므로 재호출이 debug 출력이나 팔레트 처리를 반복하지 않는다.

상태·RAM·포트·InputFrameResult는 모두 성공한 뒤 함께 반영한다. debug가 성공한 뒤 입력 리소스 오류가 나더라도 앞선 debug 변경과 포트도 보존된 원래 출력으로 되돌린다. 콜백 f3c, BIOS c00444, TRAP fee, 정상 반환0은 외부 경계이며 이 API에서 재개하지 않는다. f4c 진입은 호출자가 앞선 callback과 팔레트를 처리했음을 전제로 한다. 알 수 없는 콜백을 기본 RTS로 대체하지 않는다.

기존 진단 CLI의 --main 허용 PC는 ec4/ef2/f12/f4c로 유지한다. 준비 구간은 아래의 전용 CLI를 사용한다. C++ step_main_frame은 세 준비 PC도 받아 완료 후 debug/입력으로 같은 호출에서 이어 간다.

진단 CLI `step_input_control --registers D1 D3 --main PC DEBUG_MS5D VIDEO` 뒤에 기존 positional 인자를 붙인다. STYLE/LINE은 진입 D1/D3 lowword와 같아야 하며 JSON d1/d3는 최종 전체 값이다. `result.style`은 입력 접두부의 값이며, 대기한 경우에는 대기 진입의 D1.word다. --main은 --poll/--callback-poll과 함께 사용할 수 없다. DEBUG_MS5D는 `extracted/runtime/main_debug.ms5d`다.

`step_palette_frame --registers D1 D3`는 기존 팔레트 API의 전체 D3 전달을 CLI에도 노출한다. 기존 --d1과 기본 모드는 유지한다. 기본 callback3dcc의 실제 RTS와 f3c/f44 스택 처리는 기존 irq_envelope API로 검증한다.

## 검증 범위

프레임 신호를 생성하는 c8c 서비스와 main frame 사이에는 실제 CLI RAM 출력을 전달한다. D1/D3도 C++ 반환값을 승계한다. 그러나 c8c는 scratch register를 완전히 반환하는 API가 아니므로 인터럽트 전후 나머지 main CPU context는 진단 호스트가 보존·복원한다. BIOS와 SR/RTE, 실제 VBlank 시간축을 구현하거나 검증했다는 뜻은 아니다. 입력/팔레트 경로의 나머지 CPU register도 원본 context fixture로 남아 있다. default callback의 명시적 stack API 구간만 전체16레지스터와 stack을 반환한다.


`tools/verify_callback_register_flow.py`: 원본38경계(main poll15/palette7/envelope9/IRQ7), 출력 보존12조건 통과. 네 가지 팔레트 처리 경로와 기본 callback3dcc의 세 연속 주기를 확인했다. 7개 poll은 새 main f4c 재개 API를 사용하고, 나머지8개는 기존 callback-poll을 사용한다. 포트27개와 입력읽기40회, 전체 RAM 및 전체 D1/D3가 일치한다. envelope 구간은 전체 stack/16개 레지스터도 비교한다. 보고서 SHA256 `14e37384f2944dfbacc751546e571098431ffda56d81fa9ca28522329c290074`.


`tools/verify_main_frame_flow.py`: 원본54경계(main37/IRQ17), 포트746개, 출력 보존14조건 통과. main 진입은 ec4 8/ef2 19/f12 8/f4c 2회다. video8/input73/sound16회 읽기를 확인하고, reentrant service1회는 sound를 읽지 않는다. 6개 승계 시퀀스에 controller→ec4의 세 프레임 주기가 포함된다. 8번 ec4 진입과 실제 debug formatter2회를 구분하며 waiting에서 재출력이 없다. 초기 fixture 이후 신호16은 실제 c8c만 바꾼다. 단 한 번 호스트가 재진입 guard19를 해제하는 조건은 별도 표시했다. 보고서 SHA256 `0a43c89908e4fcdb2b458fba4abadedc7173259c67f6933815ab59873fdfe3a1`.


## e74 준비 구간과 중단 상태

`prepare_main_frame`은 e74의 word3c0004=0과 long3c0000=82000000을 한 번 출력한 뒤3c08을 실행한다. 사운드 대기에서는 word cursor와 아직 보내지 않은 low byte, byte queue의 captured tail/next를 상태로 유지한다. 이 시점 D1.low는 byte queue의 next다. 비우기가 끝나면3c32가 복원한 word cursor가 live tail에 도달하므로 D1.low는 공개된4d8a와 같다. D1.high와 D3는 보존한다.

사운드가 끝나야 sprite의 병합/정렬을 시작한다. 16bd0 대기는 앞서 준비한 링과 cursor를 그대로 재사용한다. 소비가 끝나면1ae56의 네 배경 좌표를 준비하고 RAM1b.bit7을 지운 상태에서5728 팔레트 프레임을 실행한 뒤 다시 bit7을 설정한다. 마지막 eaa에서 video word를 읽어 `(video>>7)-256`을 음수이면0으로 제한하고, 이전 RAM18 byte를 빼서 하위byte를 저장한다. 이 준비 API는 완료 시ec4로 반환하며, 완료 상태로 재호출하면 오류다. 기존 ec4 반복을 임의로 e74 재진입으로 바꾸지 않는다.

대기 중에는 후속 단계나 영상 카운터 읽기를 실행하지 않는다. 호출별 포트 목록은 그 호출에서 실제 실행한 단계만 담는다. 실패는 RAM/pending/전체D1D3/포트를 모두 보존한다. step_main_frame의 후속 debug나 입력에서 오류가 나도 해당 호출에서 실행한 준비 결과까지 함께 되돌린다. D0는 helper 내부 scratch로 사용하며 외부 반환 계약이 아니다.

전용 진단 CLI:

```
build/prepare_main_frame --state PC D1 D3 \
  [--sound PHASE LOW CURSOR COMMAND TAIL NEXT] [--sprite CURSOR] \
  VIDEO INPUT_RAM OUTPUT_RAM OUTPUT_PORTS PALETTES.ms5p [RESOURCE.ms5c ...]
```

출력 JSON은 next_pc/d1/d3/writes와 sound/sprite 상태를 담는다. 시작 PC는e74이고 초기 pending은비활성이다. 3aea 재개는 sound 객체의6필드를,16bd0 재개는 sprite.cursor를 옵션으로 전달한다. sound.kind는2, byte.waiting은true로 복원한다. 실제 RAM 및 전체 레지스터 반환을 같이 전달해야 하며, 잘못된 pending/PC 조합은 오류다. OUTPUT_PORTS는 기존9바이트 size/address/value 형식이다. 이 진단 상태는 게임 리소스가 아니며 실제 데이터는 기존 MS5P/MS5C 로더를 사용한다.

C++ step_main_frame의 compositions 인자는 NULL이면 빈 리소스 목록으로 취급한다. nonempty sprite 큐는 해당 MS5C를 제공해야 한다. 준비와 기존 gate에서 각각 영상 값을 읽는 경우 현재 API는 같은 VIDEO 표본을 사용하며, 개별 물리 시각을 계산하는 API가 아니다.

`tools/verify_main_prelude.py`: 182준비경계(sound대기28/sprite대기20/ec4완료134), 전체RAM/fullD1D3/pending 및 순서 있는 포트58,136개, 영상 읽기134회, 오류 보존33조건 통과. 원본 PVC에 따라2/3/4MiB bank window를 전환한다. 10승계시퀀스 중6개는 sound 대기 중 새 word 명령을 추가하여 live tail까지 비운다. 반환 A5/A6/A7 보존을 확인한 뒤 실제 CLI 상태로 main ef2대기2조건/f3c진입2조건을 잇는 검사도 통과했다. 후속 영상·입력 읽기는12회다. 보고서 SHA256 `9356a45524c67501dfdec3da7746796895fdf83df3922473a19f4f2256e6c6a5`. 실제 소비 IRQ와 물리 시간은 후속 통합 대상으로 남는다.


## 실제 IRQ 소비와 준비 재개

`tools/verify_main_prelude_irq.py`는 초기 fixture 이후 sound head/sprite read cursor를 직접 쓰지 않는다. 준비 API가3aea 또는16bd0에서 대기하면 원본 c8c 및 C++ IRQ 서비스를 실행하고, 그 RAM 반환으로 준비를 재개한다. sprite는 이전 준비 구간과 새 정렬 구간을 분리한다. IRQ가 이전 구간을 소비하여 read cursor를 옮기고 방향을 뒤집으면 main은 새 방향으로 준비를 마친다. 다음 IRQ는 새로 준비한 구간을 소비한다.

82시퀀스에서 main292경계(sound82/sprite128/ec4완료82), IRQ187완료 및 순서 있는 포트124,884개가 일치했다. 실제 MS5P/MS5C, 전체 RAM/fullD1D3/pending, 두 palette bank와 display를 비교한다. IRQ timer16의 word명령19c0 추가2조건도 포함한다. 보고서 SHA256 `6d930aea7824a4dc5ba7bebc5b1a451c903da8aadaaf9fe3584c5b83ca054ad4`.

main CPU context는 호스트가 IRQ 전후에 보존·복원하며 IRQ 진입 scratch register는 fixture다. 빈 task queue를 사용하고 IRQ 완료 후에만 main을 재개한다. BIOS/SR/RTE와 자연 시간축을 구현했다는 뜻은 아니다. e74 이전의 미구현 초기화는 [main-startup.md](main-startup.md)에 정리했다.
