# 480bc 구현 인터페이스 계약

기존 stage-frame-integration-contract.md의 순서와 오류/리소스 계약을 따른다. 확정 인터페이스:

```
struct StageFrameState {
    StageBufferFrameState buffer;
    unsigned int stage;
    SpriteSubmitStatus cue_status;
    unsigned int sound_kind, sound_phase;
    std::uint16_t sound_saved;
    // stage0, cue_status=SpriteAccepted, sound fields0; buffer default ctor
};
bool step_stage_frame(std::vector<std::uint8_t>& ram,
    const FixedDataResource& tables,
    const std::vector<FixedDataResource>& windows,
    StageFrameState& state, std::uint8_t external_status,
    std::uint8_t& external_reads, std::vector<VideoPortWrite>& ports,
    std::string& error);
```

레지스터의 단일 기준은 `buffer.registers`, A6는 `buffer.a6`, bank는 `buffer.bank`다. stage0은 신규480bc, stage1은4aa88 대기, stage2는e8a48 sprite 대기, stage3은2efa6 sound 대기다. 모든 stage에서 bank는2/3, `cue_status`는 `SpriteAccepted..SpriteWaiting`(0..3)만 허용한다. C++ API에 enum 범위 밖 값을 전달해도 오류다.

상태 조합은 실행 전에 검사하며 유효하지 않으면 정규화하거나 무시하지 않고 실패한다.

- stage1에서는 `buffer.phase`가1/2여야 한다. saved slot index0..15와 `saved_slot_a4 == 0x10daf8 + saved_slot_d7*8` 등 buffer pending metadata 검증은 buffer API에도 위임한다.
- stage0/2/3에서는 `buffer.phase`와 일곱 saved 필드 `saved_a6`, `saved_slot_a4`, `saved_slot_d7`, `saved_d0`, `saved_d1`, `saved_d7`, `saved_a0`가 **모두0**이어야 한다. 비활성 saved 필드에 남은 값을 무시하지 않는다.
- stage0/1/2에서는 `sound_kind`, `sound_phase`, `sound_saved`가 모두0이어야 한다.
- stage3에서는 kind1/phase1..2/saved0..255 또는 kind2/phase1..3/saved0..65535만 허용한다. 선택된 sound helper의 pending 검증도 유지한다.

신규실행:47642→scene1a73c(ports추가,bank2)→49b0c→4aa88→b4a2a→6f1c2(RTS)→4701e→e8a48→2efa6. 각단계별대기는그단계번호로반환하며그앞을재실행하지않는다. stage1후buffer의복원된A6/최종bank를후속에전달한다. stage2는cue waiting=true로재개. stage3는sound byte waiting=true로재개. 완료시stage0,sound fields0,buffer.phase와일곱buffer saved fields0이다. cue_status는cue API계약대로(해당submit미도달이면이전값보존) 유지한다.

성공시ports는이번호출의새port순서로교체하고external_reads는이번호출의sound읽기수다. 실패시RAM/state/ports/external_reads전부보존한다. 새frame진입때만scene tables/windows를필요할때검사하고, sound대기재개에이미지나scene입력을다시검증하지않는다.

CLI 이름 build/step_stage_frame. 인자 순서:

```
D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6
BANK STAGE BUFFER_PHASE SAVED_A6 SAVED_SLOT_A4 SAVED_SLOT_D7
SAVED_D0 SAVED_D1 SAVED_D7 SAVED_A0 CUE_STATUS
SOUND_KIND SOUND_PHASE SOUND_SAVED EXTERNAL
INPUT_RAM OUTPUT_RAM OUTPUT_PORTS TABLE_MS5D [WINDOW_MS5D_OR_DIRECTORY ...]
```

필수 argc34(실행명포함), 숫자인자29개. JSON은d0..d7,a0..a4,a6,bank,stage,buffer_phase,saved_a6,saved_slot_a4,saved_slot_d7,saved_d0,saved_d1,saved_d7,saved_a0,cue_status,sound_kind,sound_phase,sound_saved,external_reads. ports는기존9byte >BII binary. RAM65536byte. CLI는 입력 RAM과 두 출력, TABLE 사이의 canonical 경로/inode 충돌을 거부한다. 선택 window가 입력 RAM 또는 출력의 별칭이면 거부하며, TABLE 또는 이미 등록된 window와 같은 canonical 경로/inode이면 중복 로드를 생략한다. API 성공 후 두 출력 파일을 truncate 없이 예약/open하고 `fstat`으로 실제 device/inode가 서로 다른지 확인한다. 모든 입력/리소스의 `stat` identity와도 재비교한 뒤에만 `ftruncate`와 쓰기를 시작한다. 따라서 대소문자 비구분 파일시스템에서 아직 없는 두 출력 이름이 같은 파일을 가리키는 경우도 실제 inode로 검출한다. 예약/검사 실패 시 기존 파일은 보존하며 이번 호출에서 생성했고 현재 경로 identity가 일치하는 placeholder만 제거한다. RAM과 ports는 순차적으로 쓰고 close 결과를 검사한다. 쓰기/close 오류에는 이미 수행한 파일 변경의 rollback이나 두 출력의 원자적 교체를 보장하지 않는다. C++ API소유파일 engine/include/ms5/stage_frame.h, engine/src/stage_frame.cpp, engine/tests/stage_frame_test.cpp. CLI/Makefile와verify도구는별도담당한다.
