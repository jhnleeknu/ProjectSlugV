# 47a94 본문 연결 구현과 남은 검증 계획

이 문서는 `stage-entry-body-contract.md`에 따른 승인된 API 구현 결정과 남은 원본 검증 계획을 구분한다. 새 원본 의미를 확정하거나 47a94 전체 실행을 검증한 문서가 아니다. 원본 의미의 근거는 메인이 확인한 해당 계약이며, 아래 API 효과는 현재 C++ 소스와 검증 도구를 읽어 확인했다. canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 고정 CPU 주소는 동일 ROM 파일 오프셋이다. banked CPU 주소는 별도 ROM 오프셋으로 기록한다.

## 승인된 인터페이스와 구현 상태

다음 인터페이스는 메인이 승인하여 `engine/include/ms5/stage_entry_body.h`와 `engine/src/stage_entry_body.cpp`에 구현했다. 사용 인자는 [실행 인터페이스](stage-entry-body-execution.md)를 따른다.

```cpp
struct StageEntryBodyState {
    StageFrameState frame; // 유일한 D0..D7/A0..A4/A6/bank 기준
    std::uint32_t a5;      // 기본값 0x108000
    unsigned int phase;   // 0: 신규47a94, 1: frame 대기, 2: 본문 완료
    StageEntryBodyState() : a5(0x108000), phase(0) {}
};
bool step_stage_entry_body(std::vector<std::uint8_t>& ram,
    const FixedDataResource& tables,
    const std::vector<FixedDataResource>& windows,
    StageEntryBodyState& state, std::uint8_t external_status,
    std::uint8_t& external_reads, std::vector<VideoPortWrite>& ports,
    std::string& error);
```

`phase0`은 canonical inactive `StageFrameState`로 시작한다. `phase1`이면 `frame.stage`가1/2/3이어야 하며 frame API로 직접 재개한다. `phase2`는 47af0 callback이 게시되고 최초 frame이 완료된 경계다. 완료된 phase2로 다시 호출하면 실패하며 RAM/state/ports/external_reads를 보존한다. phase0의 inactive 조건은 frame.stage, buffer.phase와 일곱 saved 필드, sound_kind/phase/saved가 모두0인 것이다. cue enum0..3과 bank2/3은 모든 유효 진입에서 검사한다. 다음 callback 실행을 이 함수에 암묵적으로 넣지 않는다. frame의 stage0을 본문 신규 진입의 지표로 쓰면 완료 후 초기화를 반복하므로 별도의 phase가 필요하다.

A5는 상태 입력/출력으로 운반하되 지원 범위를 `0x108000`으로 제한하도록 승인하여 구현했다. event helper의 반환 A5도 검사한다. 기존 scene/frame 공통 API는 A5를 노출하지 않고 이 기반 주소를 사용하므로 event API 단독의 alternate A5 지원을 전체 본문 지원으로 확대하지 않는다. 일반 A5 지원은 현재 범위 밖이다.

본문 자체의 record/indirection read는 aligned live RAM 또는 고유 fixed ROM window만 허용하도록 구현했다. fixed window는 CPU/ROM 주소가 같고 겹치는 리소스가 하나여야 하며 요청 전체가 그 window 안에 있어야 한다. speculative banked record reader는 추가하지 않았다. scene/frame 구성 helper의 기존 banked payload 지원과 이 제한을 구분한다.

event 변환은 구현의 명시적인 복사 반복문으로 수행한다. D[0..7], A[0..4]를 임시 `ObjectRestartState`에 복사하고 events.a[5]=a5, events.a[6]=frame.buffer.a6로 둔다. 반환은 **15개 모두** authoritative body/frame 상태에 다시 반영한다. A3도 복사 대상이며 A5/A6를 추정 상수로 덮어쓰지 않는다. 임시 어댑터는 별도의 authoritative state가 아니다.

## 호출 연결과 상태 효과

| 단계 | 기존 API 또는 본문 동작 | 레지스터·bank·ports 계약 |
| --- | --- | --- |
| scene 입력 | live LONG(A6+0x76)→A4, LONG(A4+2)→A0, WORD(A4+0xe)→D0.low | 각 aligned checked read. D0 상위 WORD 보존 |
| scene 초기화 | `initialize_scene(ram,tables,windows,registers,a6,local_ports,error)` | D0..D7/A0..A4 반환 반영, A6 유지. 진입 PVC bank3, 종료 PVC bank2. local_ports를 누적하고 bank=2 게시 |
| cue 입력 | live LONG(A6+0x76)→A4 재독출, LONG(A4+6)→A0 | scene 이전 A4를 재사용하지 않음 |
| cue 선택 | `step_stage_cue_control(ram,0xe8a1c,windows,registers,a6,carry,error)` | null A0는0xe89e4가 됨. 10de26에 포인터, 10de2e=ff,10de2f=0. A6/bank/ports 영향 없음. 해당 entry는 carry를 읽거나 변경하지 않음 |
| flags 및48398 | 계약의 bit1/3/5 순서와30f4 lookup 적용 | D0.byte 읽기 후 D0.low &=7 후 fixed BYTE lookup. D0 상위 WORD와 다른 레지스터 보존. 10d67e/10d67f 게시. ports 없음 |
| event 입력 | live LONG(A6+0x76)→A4 재독출, LONG(A4+0xa)→A0; nonnull이면 LONG(A0)→A0; WORD(A4+0xe)→D0.low | 모든 read를 같은 candidate RAM에서 실행. 첫 단계의 target도 재사용하지 않음 |
| event 초기화 | `initialize_stage_events(ram,windows,events,local_ports,error)` | incoming A5+signed WORD0x8bf4로 object 선택. `restart_object_full`은 A5=108000, A0/A6 복원. 최종15레지스터 반영. watchdog와 nonnull-stream 종료 PVC를 순서대로 누적 |
| callback 및 frame | LONG(A6)=0x47af0 게시 후 `step_stage_frame` | 초기화 ports 뒤 frame ports를 이어 붙임. frame.stage1/2/3이면 body.phase1, 완료면 body.phase2. 재개 때 앞 단계·callback 게시 반복 금지 |

`initialize_stage_events`의 stream0 경로는 object restart 후 object+0x76=0을 기록하고 종료하여 마지막 PVC reset을 생략한다. scene이 이미 bank2로 끝났으므로 이 경로도 bank2를 유지한다. 현재 restart 소스에는 bank 전환이 없고 watchdog 0x300001만 추가된다. nonnull 경로는 RAM100010=0 및 PVC 1000/0을 내보내 bank2다. event ports가 비었다는 가정이나 모든 성공에 reset pair가 있다는 가정은 금지한다.

전체 body 호출은 RAM/state/ports/external_reads를 복제한 단일 transaction으로 감싼다. 구성 API의 성공 직후라도 나중에 실패하면 **이번 body 호출 진입 시점**으로 돌아가야 한다. 성공이면 ports를 이번 호출 누적 결과로 교체한다. initialization 부분은 external_status를 읽지 않으므로 external_reads는 frame의 이번 호출 읽기 수다. frame wait 재개는 앞선 resource/table/record를 다시 검사하지 않고 frame API가 실제 소비하는 입력만 요구한다.

## 기존 리소스 재사용

- `extracted/runtime/scene_debug.ms5d`: fixed CPU/ROM0x1af12, payload512. scene 초기화 API는 이 identity와 길이를 선검사한다.
- scene scripts/maps/secondary/placements와 node pointer windows: `observe_scene_general_initialization.resources()`의 검증된 MS5D 묶음. script와 motion은 실제 소비 지점에서 고유 fixed window를 요구하며 RAM motion은 현재 미지원이다. bank2 CPU0x200000 계열은 동일 ROM 오프셋, bank3은 ROM 오프셋에0x100000을 더한다. 디렉터리 전체 묶음을 합칠 때 동일 window를 중복 삽입하여 ambiguity를 만들지 않는다.
- `extracted/runtime/stages/stage_group_XX.ms5d`: 19개 stage list에59개 record가 보존되어 있고 opaque18-byte header 안에 +2/+6/+a/+e가 포함된다. wrapper가 record를 직접 읽으므로 이 group windows를 전달해야 한다. index lookup을 새로 실행하지 않으면 `stage_index.ms5d`는 body 자체에 필수라고 단정하지 않는다. live RAM record도 구현된 read 계약에 포함된다. 실제 원본 유효성과 관측된 record 경계는 별도 본문 fixture로 검증한다.
- `extracted/runtime/stage_events/lookup_0030ec.ms5d`: **이미 존재하는** MS5D v1 kind1, CPU/ROM0x30ec, payload8, 원본 bytes `60 70 80 90 90 90 90 90`. `pack_stage_events.py`가 생성하고 `verify_stage_event_initialization.resources()`가 source byte/hash/CRC를 검증한다. 새 형식·난수 대체·중복 lookup 리소스는 필요 없다.
- `extracted/runtime/stage_events`:47개 indirect pointer cell,47개 stream, 위 lookup 한 개로95 windows. +0xa nonnull 포인터의 정확한4-byte cell은 기존 packer가 이미 보존한다. stream ff 경계는 gate skip 검증 범위이며 전체 event opcode grammar의 완료 증거가 아니다.
- `extracted/runtime/stage_cue_control/default_cue.ms5d`: CPU/ROM0xe89e4,8byte. e8a1c 자체는 포인터만 저장하여 이 payload를 읽지 않는다. 후속 frame의 debug cue 좌표 경로가 소비하면 필요하다. default_stream0xe89ec14byte는 e8a1c만을 근거로 필수라 하지 않는다.
- frame 후속 입력은 `verify_stage_frame.py`의 audited resources union을 재사용한다. 기존458 scene windows 외 default input masks, cue 관련 windows, player_record_lookup/game_records 등을 source 검증하여 합친다. 기존 전체 window를 무차별로 중복 로드하지 않는다.

## 재사용 가능한 native fixture와 정지 경계

| 도구 | 기존 entry/stop | 재사용 범위와 주의 |
| --- | --- | --- |
| `observe_scene_general_initialization.py` | ENTRY0x1a5a4, RETURN0xff000; STACK0x1feffc | `fixture(program,case)`는 원본2790/3ef2를 entry 전에 실행해 RAM seed 생성. `build_cases`는 actual59 catalog script/target을 포함. Observer의 PVC bank2/3, source 불변성, ordered9byte ports 로직 재사용 가능. 현재 A5 결과는14-register 비교에 포함되지 않으므로 body에서는15개를 기록 |
| `observe_stage_event_initialization.py` | ENTRY0xe905c, RETURN0xff000; STACK0x1feffc | `fixture`는 palette/restart object 준비, actual59 record input 및47 streams/612 gate 경계, null/live RAM/alternate A5 사례 제공.15레지스터와 watchdog/PVC 로직 재사용 가능. 이 fixture를 scene fixture 위에 그대로 덮어쓰기하면 alias·수명 충돌 가능 |
| `observe_stage_cue_control.py` | entry0xe8a1c 등, RETURN0xff000; STACK0x1feffc | e8a1c null/opaque pointer fixture와 carry 보존 근거. Musashi oracle이며 다른 초기화 observer의 Unicorn context와 직접 섞지 않음 |
| `verify_stage_sound_initialization.py` | ENTRY0x47a1c, WAIT0x3aea, DONE0x47a94 | DONE 경계까지 원본 실행 후 전체 CPU context를 유지한 채 body로 이어가는 입력 후보. 기존 sound API는 일부 레지스터만 노출하므로 C++ body 초기 상태를 축약된 sound JSON으로만 복원하지 않음 |
| `verify_stage_frame.py` | ENTRY0x480bc, SPRITE_WAIT0xcda4, SOUND_WAIT0x3aea, RETURN0xff000 | 실제 CPU/stack/CCR를 보존한 wait 재개, stack에서 pending 추출, ordered ports/읽기 비교 재사용 가능. 본문 시작0x47a94에서는 helper 관찰 순서에 초기화 prefix가 추가됨 |

본문 oracle의 primary entry는0x47a94, tail-frame 진입 진단 경계는0x480bc다. 전체 완료는 caller sentinel0xff000이며 초기 STACK0x1feffc의 RTS 주소를 이어받는다. 0x47af0은 다음 object callback 값이지 이번 tail frame의 반환 정지점으로 대체할 주소가 아니다. 첫 검증은 실제 stage record별로 47a94→초기화→480bc를 **중간 stub/reset 없이** 연속 실행하고 RAM65536byte, D0..D7/A0..A6, bank, ordered ports와 pending을 비교한다.

새 body는 tail branch로480bc에 들어가므로 기존 frame 내부의 `STACK-4` helper 진입 기대는 tail branch 자체가 stack을 쓰지 않는 범위에서 재사용 가능하다. 이 예상은 실제 본문 oracle 관찰에서 A7와 return address를 확인할 항목이며 정적 tail-branch 해석만으로 동적 검증 완료로 처리하지 않는다. body helper 진입의 nested stack 깊이를 기존 frame 고정 assertion에 억지로 맞추지 않는다. 대기 정지는 기존처럼 실제 blocked spin 재방문을 확인하며 실행 중 SR를 읽지 않는다. resume는 동일 CPU context를 유지하고 명시적 host RAM 변화만 적용한다.

## 빌드 확인과 남은 원본 검증

메인이 실행한 전체 빌드/test는 exit0이며 로그는 `artifacts/stage_entry_body_build_test.log`다. 로그에서 실제 `./build/*_test` 실행 줄을 세면133개이고 모두 서로 다른 테스트 실행 파일이다. 이 안에 `./build/stage_entry_body_test`와 `stage_entry_body_test passed`가 포함된다. 이 수는 C++ 테스트 실행 파일 수이며 원본 본문 fixture 수나 개별 assertion 수가 아니다. 빌드·단위 검증 성공을 native 전체 본문 동등성의 증거로 대체하지 않는다.

아래는 원본 verifier 보고서와 메인 리뷰로 확인할 항목이다. 이 문서 갱신 시 최종 native 보고서의 통과 수와 범위를 수용한 상태가 아니므로 미완료로 유지한다.

1. 기존59 record별 group window 경계, +6 cue 포인터의 실제 fixed/banked/RAM 소비 경로와 helper 지원 여부를 전체 본문 관찰에서 기록한다. setter가 opaque pointer를 수용한다고 후속 frame 전체도 지원한다고 보지 않는다.
2. scene 초기화 뒤 record 또는 A6+0x76 alias가 바뀌는 fixture를 원본으로 구성하여 A4/target 재독출을 검증한다. helper fixture의 단순 결합만으로 유효 입력을 주장하지 않는다.
3. 기존 scene frame smoke는 이미 scene 초기화가 끝난 RAM이므로 body 초기 입력으로 무조건 재사용하지 않는다. body 전용 일관된 seed와 진입 전 host 변경 목록·hash를 원본 초기화 근거와 함께 기록한다.
4. lookup8개 index, D0 상위 WORD 보존, flags 게시 순서, null/nonnull event의 ports 차이, callback 게시 후 최초 frame의 buffer/cue/sound 대기와 동일 CPU 재개를 비교한다. 재개에서 lookup/flags/callback을 재게시하지 않는 조건도 포함한다.
5. 전체 body transaction, malformed record/window와 inactive/pending metadata 오류, 완료 재호출 거부를 native 비교와 host 부정 검증 범위에 맞게 구분한다. 새로운 CLI 숫자는 기존29개 뒤 A5/BODY_PHASE를 더한31개이며 필수 argc36으로 확정했다.
6. 기존 `StageSoundState` 완료와 body/frame pending을 연결하는 더 상위 state의 책임은 별도다. helper API의 임시1048576 traversal budget, RAM motion 미지원, 미지원 input callback 오류를 유지하며 이 제한을 원본 동작이나 분석 완료로 기록하지 않는다.
7. 47af0 이후72f0/carry/IRQ 및 indexed branch 의미는 이 wrapper 범위 밖 미완료다. 본문+첫 frame 비교 성공은 자연적 scheduler 진입·조작 가능한 게임·화면/오디오 동등성의 완료를 뜻하지 않는다.

## 후속 검증 수용

이 계획 이후 구현과 원본142조건/152단계 비교를 완료했다. actual59record,lookup8개,null/nonnull event,live RAM record alias,sound5pending의결과와잔여제약은 [리뷰0191](../reviews/0191-stage-entry-body.md)을 따른다. 위 검증 계획은 역사적 준비 기록이며, 완료된 항목을 다시 미확인으로 돌리지 않는다. A5=108000·phase2재호출거부는 확정 계약이다. noIRQ body에서buffer/cue대기 도달성,47af0 이후 callback·자연scheduler·직접플레이는 여전히 미완료다.
