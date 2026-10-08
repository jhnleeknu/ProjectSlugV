# 상위 stage 활성화의 API 목록 — 정적 조사, 통합 미완료

후속 공유 stack 통합은 `animation-machine-activation-execution.md`를 따른다. `6c90612` 이후16ea4/16ed2와47cae..47d20의 실제 호출·대기 경로를 연결했다. 아래 기존 API·미구현 분류와 검증 수치는 작성 당시 기록이며, 일반 stage 활성화 전체 완료를 뜻하지 않는다.

canonical decrypted BE source SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 이 문서의 코드·fixed data 주소는 첫1MiB CPU 주소이며 같은 ROM 파일 offset에 대응한다. RAM/MMIO 주소는 파일 offset이 아니다. `AGENTS.md`, `docs/GOAL.md`, `stage-post-entry-contract.md`, `stage-activation-prefix-contract.md` 및 현재 엔진의 공개 header/source를 읽었다.

`tools/disassemble_program.py`의 `load_verified_program`과 패딩·실길이 검사가 있는 `disassemble_range`로 `[47c04,480f2)`를 다시 읽었다. `[47c04,480bc)`에는 JSR/BSR 59개와 JMP 1개, 고유 직접 대상45개가 있다. 아래 표는 그60개 명령을 모두 포함한다. 조건부/무조건 BRA와 callback 주소 저장은 call 수에 포함하지 않는다. `480bc..480f2`의 기존 frame body는 별도 아래에 표시한다. 디코딩 목록과 현재 API 범위 조사이며 새 native 실행, C++ 동등성 또는 전체 활성화 완료를 주장하지 않는다.

## 분류와 직접 callee 전체 목록

**15R**은 `ObjectRestartState`의 D0..D7/A0..A6를 공개하는 실행 API다. **부분**은 해당 주소 API가 있으나 register subset/지원 명령/진입 범위에 제한이 있다. **내장**은 다른 caller 구현 안에 효과가 있으나 독립 진입 API가 없다. **없음**은 현재 동일 주소의 공개 실행 API를 찾지 못했다는 뜻이다. 내부 조합 후보를 동일 callee의 완전한 대체로 취급하지 않는다.

| 직접 대상 | callsite CPU/ROM | 분류와 현재 대응 |
|---|---|---|
| 9060 | 47c0c,47e2a | 없음. 원본 absolute107def BYTE clear. 9056과 반대 진입이며 control_activation9136 API가 대체하지 않는다. |
| 4e254 | 47c12 | 없음. prefix 계약에 네 BYTE write와 register 보존이 정리됨. |
| 477a2 | 47c28 | 15R: `stage_block_draw.h/.cpp::execute_stage_block_draw`, entry477a2. |
| ca76 | 47c36 | 내장: `stage_entry.cpp`/`game_ready.cpp` 계열에 RAM965 효과가 있으나 arbitrary A5의 독립 callee API 없음. |
| ca56 | 47c3c | 없음. prefix 계약의 BYTE(A5−7699) clear. |
| c3c0 | 47c54 | 없음. prefix 계약의 signed BYTE 비교/선택 write. |
| 4e286 | 47c7a | 없음. 사운드3af8 대기, palette8cda, fixed4e272 및 두35f0 출력까지 포함하므로 block API 한 번으로 대체 불가. |
| 4843c | 47c88 | 없음. 조건부 SBCD/borrow 처리가 필요; 유효 BCD 입력에 한정된 대체 금지. |
| ca70 | 47c8c | 없음. 독립 효과·전체 register 계약 필요. |
| 16ed2 | 47cc0,47eb2 | 없음. sprite node flag helper의 독립 API 필요. |
| 47672 | 47cc6 | 없음. 현재 stage_players476dc/47742와 다른 진입. |
| 16ea4 | 47ce6 | 없음. cd58 tail submission과 scratch register/대기 승계 필요. 기존 sprite producer 가족은 하위 조합 후보. |
| 49f8c | 47d14,47ee0 | 없음. animation 초기화의 독립 공개 API 없음. |
| 49fc6 | 47d1a,47f04 | 부분: `animation_step.h/.cpp::step_animation[_with_data]`; 제한 opcode, RAM/carry만 공개, producer wait는 오류. full scratch registers 및 일반 애니메이션 지원 아님. |
| 4e216 | 47d24 | 없음. 독립 효과와 register/port 계약 필요. |
| bee | 47d2e | 없음. BIOS/외부 경계 여부·실행 환경을 메인이 확인해야 함. |
| 4847c | 47d3e | 없음. 두1bdde 및 조건부4e166의 native carry가 caller 분기를 결정. |
| 477ac | 47d58 | 없음. 고정 D0..D3 준비 후35a2 tail call. screen reset의 고정 다섯 rectangle과 다른 rectangle이며 일반35a2 API 없음. |
| 3af8 | 47d92,47e50,47f4e,47f58,47f62,47f7c | 부분(13R): `sound_word_execution.h/.cpp::execute_sound_word`; captured byte wait/외부 d00046 read count 포함. A5/A6는 state 밖. |
| 4b6e4 | 47da4 | 없음. BYTE(A5+5b85)=ff의 짧은 진입. |
| 4b6ec | 47daa | 없음. BYTE(A5+5b87)=ff의 짧은 진입. |
| 2a48 | 47db4 | 없음. `remove_objects`의 지원 entry 목록에 없으며 `restart_object_full`은2a28 별도 진입. 단순 alias로 취급 불가. |
| 1c5b0 | 47dba | 내장: `stage_entry.cpp`에 두 player object 효과 구현; 공개 API는 부분 stage caller이며 callee 전체 register/carry는 없음. |
| 1bee4 | 47dc0 | 없음. 원본 A0=1bec0, D0=0/1로49c20 호출/꼬리호출. `stage_input::step_stage_input`49c20을 재사용할 후보는 있음. |
| ca48 | 47dd2 | 내장: `stage_entry.cpp` RAM967=ff. arbitrary A5 callee API 없음. |
| 9056 | 47df4 | 내장: `stage_entry.cpp`, `game_startup.cpp` 등에 absolute107def=ff. 독립 API 없음. |
| 28ae | 47e04,47e3a | 부분(4R+carry): `object_allocation.h/.cpp::allocate_object`. D0/A0/A1/A6만 state에 포함. |
| 8c16 | 47e80,47f96,47fb8,48058,4807e | 15R: `palette_effect_execution.h/.cpp::execute_palette_effect`. incoming A5를108000으로 교체. |
| 1c63c | 47ef8 | 없음. player 관련 상위 helper의 독립 효과·register 계약 필요. |
| 48398 | 47f42 | 내장: `stage_entry_body.cpp::initialize` private 경로에서30f4 lookup과567e/567f 게시. 독립 API 없음. |
| 3c84 | 47f68 | 내장: `stage_sound_initialization.cpp` 등에 RAM104d7e clear. 독립 전체 register API 없음. |
| 3d44 | 47f6e | 내장/부분: stage sound initialization에08/20 제출 순서가 있으나 독립 full-register3d44 API 없음. `enqueue_sound_pair`의 공개 entry는3d58/3d64뿐. |
| 4e24e | 47fbe | 내장: `stage_entry.cpp` RAMdd1f clear; arbitrary A5 callee API 없음. |
| ca7e | 47fc4 | 내장: `stage_entry.cpp` RAM965 clear; arbitrary A5 callee API 없음. |
| caf0 | 47fca,4809a | 15R: `game_screen_reset_execution.h`, `game_screen_reset.cpp::reset_game_screen_full`, entrycaf0. actual A5−769a BYTE destination checked; A5 preserved. |
| 477c2 | 47fe4 | 부분(4R): `stage_preparation.h/.cpp::clear_stage_objects`; D0/D1/D3/A6만 공개. |
| 43ffc | 47fec | 부분(12R): `scene_setup.h/.cpp::setup_scene_resources`; exact fixed descriptor 또는 null. A3/A5/A6는 state 밖. |
| e7c36 | 47ff2 | 부분(3R): `main_startup.h/.cpp::initialize_stage_palettes`; D0/D1/D3만 공개, A5=108000 implicit. |
| 8da2 | 4801e | 부분(9R): `main_startup.h/.cpp::bind_palette_resource`; D0..D4/A0/A1/A2/A4. |
| 16fac | 4802a | 부분(12R): `scene_node.h/.cpp::step_scene_node`, entry16fac. |
| 16ff8 | 4803c | 부분(13R): `scene_path_execution.h/.cpp::configure_scene_map_descriptor`. |
| 1861a | 48042 | 부분(13R): `scene_map_refresh.h/.cpp::refresh_scene_map`. |
| 17012 | 48048 | 없음. 원본 BYTE(A0+7a) OR81의 독립 entry API 없음. scene command1c의1701a slot clear와 다른 진입. |
| c364 | 480a0 | 없음. 원본 c00468 BIOS JSR 포함. 임의 fake return으로 연결 불가. |
| 2a00 | 480b6 JMP | 없음. `remove_objects`의 지원299c/2a0a/2a84/c4cc와 다른 tail 진입. |

모든 주소·상수는16진수다.

## 현재 사용 가능한 정확한 공개 signature

아래 표기의 `RAM`은 `std::vector<std::uint8_t>&`, `Windows`는 `const std::vector<FixedDataResource>&`, `Ports`는 `std::vector<VideoPortWrite>&`, `Error`는 `std::string&`다. 모든 함수는 `bool`을 반환한다. 요약 alias는 이 문서에서만 사용하며 C++ 타입을 새로 제안하는 것이 아니다.

```cpp
execute_stage_block_draw(RAM, std::uint32_t entry, Windows,
    ObjectRestartState&, Ports, Error);
execute_palette_effect(RAM, ObjectRestartState&, Error);
reset_game_screen_full(RAM, std::uint32_t entry, ObjectRestartState&, Ports, Error);
execute_sound_word(RAM, SoundWordExecutionState&, std::uint8_t external_status,
    std::uint8_t& external_reads, Error);
allocate_object(RAM, AllocationState&, Error);
clear_stage_objects(RAM, StagePreparationState&, Ports, Error);
setup_scene_resources(RAM, const FixedDataResource* descriptor,
    SceneCommandState&, Ports, Error);
initialize_stage_palettes(RAM, const FixedDataResource& main_bindings,
    const FixedDataResource& stage_bindings, std::uint32_t& d0,
    std::uint32_t& d1, std::uint32_t& d3, Ports, Error);
bind_palette_resource(RAM, const FixedDataResource& bindings,
    PaletteBindingState&, Ports, Error);
step_scene_node(RAM, std::uint32_t entry, SceneNodeState&, Error);
configure_scene_map_descriptor(RAM, Windows, SceneMapTransferState&, Ports, Error);
refresh_scene_map(RAM, Windows, SceneMapTransferState&, Ports, Error);
step_animation_with_data(RAM, std::size_t object_offset,
    const std::vector<std::uint8_t>& script, std::uint32_t script_base,
    Windows, bool& carry, Error);
step_stage_frame(RAM, const FixedDataResource& tables, Windows,
    StageFrameState&, std::uint8_t external_status, std::uint8_t& external_reads,
    Ports, Error);
```

`SceneMapTransferState`는 D[8]/A[5], `SceneCommandState`와 `SceneNodeState`는 D0..D7/A0/A1/A2/A4를 운반한다. 후자는 A3도 state 밖이다. `PaletteBindingState`는 D0..D4/A0/A1/A2/A4다. `SoundWordExecutionState.byte.registers`는13R이며 phase/saved_low/byte.waiting이 별도 대기 metadata다. `StageFrameState.buffer.registers`는13R, buffer.a6/bank가 별도 필드이며 A5는 포함하지 않는다.

## 480bc와외부 transfer

480bc부터의 JSR은47642,1a73c,49b0c,4aa88,b4a2a,6f1c2,4701e,e8a48,2efa6이며480f0이RTS다. 현재 `stage_frame.h/.cpp::step_stage_frame`이 그 순서와 buffer/cue/sound 재개를 구성한다. 상위 연결은 frame.stage1..3의 재개만 실행하고 선행activation이나 완료된 frame 부분을 재실행하지 않아야 한다. full15R 입력에서는 D/A0..4/A6 이동과 A5 별도 관리가 필요하며 A5 저장/고정 조건을 상위 계약으로 확인해야 한다.

범위 밖 branch는477ee(47d5c,47ea8)와480bc(여러callback)가 있다. `stage_entry::step_stage_entry`는477ee 입력을 지원하지만 D0/D1/D3/A6 부분state이며 catalog/debug resource와sound wait를 갖는다. full15R callback의 무손실adapter는 아직 없다. callback값을 쓴 것만으로 후속 실행 완료가 되지 않는다. 47eac 등은 조사 범위 내부 코드이며 별도callee로 세지 않는다.

## resource 의존과 부족

- 477a2: `FixedDataResource` MS5D v1 kind1의ddfa4..ddfdc raw56byte block stream. `tools/pack_stage_block_draw.py`와 기존C++ fixed loader가 대응한다. core의RAM stream지원이 caller477a2의원본table을synthetic data로 대체하는 근거는 아니다.
- 4e286: fixed4e272 WORD lookup과8cda full scratch대응이 부족하다. `palette_control.h/.cpp::set_palette_blend`는RAM만 공개하며 native D0/D1/D2/A1/A2 결과를 주지 않는다. 3af8 pending과 두35f0 사이의caller register저장이 필요하다.
- 47cda는fixed48a12 indexed LONG을D7로 읽는다. 47d0a/47ed6은animation A1=489c2/48980을 전달한다. raw fixed window와script extent/opcode실제지원 범위를 확인해야 한다. 기존MS5A loader와animation subset으로 두script전체가 실행되는지는 미확인이다.
- 48398: fixed30ec의8byte lookup은 `tools/pack_stage_events.py`가 `lookup_0030ec.ms5d`로 추출하며 stage_entry_body reader가 소비한다. 같은raw bytes를 재사용하고 난수계산으로 대체하지 않는다.
- 47fe8: descriptor A0=48108에서43ffc로 전달한다. 기존`tools/pack_scene_scripts.py`는stage-script opcode08이 참조하는15descriptor를 추출하지만 문서화된15개에48108은 없다. `descriptor_span` 재사용 후보이며48108이 이미 출력됐다고 가정하지 않는다.
- e7c36: main e7b58 binding과stage e7bda binding이 필요하다. 기존main/stage palette packer/loader를 재사용하되3R출력만으로 전체scratch를 채울 수 없다.
- 48012: PVC2ffff2=1000/2ffff0=0 직후CPU20000c의LONG→A0, 그A0+00f0의LONG→binding A0를live read하여8da2로 전달한다. bank2 pointer/index/binding raw window가 필요하다. `bind_palette_resource`는 선택된exact binding을 소비하며 앞선pointer lookup은 실행하지 않는다. 현재자산의pointer/selected binding수록 여부는 별도확인이 필요하다.
- 48030: fixed480f2→A1, A2=0,D0=0,D1=31로16ff8, 이어1861a를 호출한다. raw descriptor/전송window extent와기존scene packer수록 여부는 미확인이다. map helper는fixed/bank2/bank3 window reader계약을 사용한다.
- 480bc: debug tables와scene/script/motion/placement,buffer sprite,cue 등이 실제참조하는fixed/banked windows를기존frame계약에 따라 공급한다. 상위bank2 write이후상태와helper의bank변화를 일관되게 운반해야 한다.
- bee/c364: BIOS·외부메모리 구현경계와필요입력은 메인이 확인한다. E4234/D72FE등을28ae로전달하는 지점은callback값저장이며 그body resource를이call이읽었다고 주장하지 않는다.

## adapter 최소과제와독립검증 기준

전체register authority를15R하나로정하고 부분API의공개register를copy-in/out한다. 나머지register를보존한다고가정하려면 원본근거가필요하다. A5암묵108000인helper를arbitrary A5경로와자동으로동등하게취급하지않는다. 2a48/2a00,477c2,e7c36,49f8c/49fc6의전체scratch와caller가즉시읽는native carry가주요부족이다.

독립검증은미수정canonical ROM에비zero highwords와전체15R을주고 실제callee return/대기경계의RAM65536bytes·전체15R·ordered ports·필요carry/외부read수를수집해야한다. sound/sprite wait는native context를저장·재개하고callback PC만이동하거나callee를fake return으로대체하지않는다. late helper/resource실패의RAM/state/ports/read counter rollback과resume에서완료helper가재실행되지않음을별도로검사한다. BCD4843c는비BCD BYTE를포함한CPU SBCD경계를메인의확정계약과원본관측으로확인한다.

이번조사는source/header대조이며빌드·테스트·원본실행을새로수행하지않았다. 새파일은이문서하나이며ROM·추출데이터·공유core·Makefile·STATUS는변경하지않았다.
