# 480bc 전체 호출 smoke fixture 계획과 원본 실행 근거

이 문서는 다음 통합 단계의 입력 계획이다. **확인 사실:** 아래 일관된 RAM 입력으로 수정하지 않은 원본 `0x480bc`가 모든 직접 호출을 실행하고 반환했다. **미확인:** 새 C++ 전체 frame wrapper와의 비교, 자연 scheduler/IRQ/플레이 입력에 의한 진입, 실제 게임 진행. 개별 helper 검증 결과나 이 smoke 실행을 전체 게임 완료로 취급하지 않는다.

원본 canonical BE SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 고정 ROM CPU 주소는 동일 파일 오프셋이며, RAM 주소는 파일 오프셋이 아니다. 뱅크 주소는 CPU `0x200000..0x2fffef` 창과 물리 ROM bank2/3 오프셋을 구분한다.

## 재현 입력

출발점은 기존 source-verified 원본 general initializer의 실제 출력 `artifacts/scene_general_initialization/native_0000.bin`이다. SHA256은 `5924838661acd15a85840db2c0d66627cf79c072f99ab0f6abfbf7cd5a13c0c2`. 해당 `observation.json`의 `results[0]`은 `script=0x488c4,target=0,profile=0,debug=0,available=true`이고, 입력 레지스터는 그 행의 `result`를 그대로 사용한다. 재생성 경로는 기존 `observe_scene_general_initialization.py`이며, 출발 fixture는 실제 원본 `0x2790/0x3ef2`를 실행한 후 `0x1a5a4`를 실행한 결과다.

아래 모든 값은 BE로 **진입 전에만** 쓴다. frame 중간이나 helper 경계에서는 RAM/레지스터를 재설정하지 않는다. 정확한 이전 바이트와 게시 바이트는 `artifacts/stage_frame_plan/probe.json`의 `changes`에 있다.

| RAM CPU 주소 | 크기 | 값 | 목적 |
|---|---:|---:|---|
| `0x100cb8`, `0x100da8` | 각각 LONG | `0x0000270e` | 두 player marker를 비활성으로 하여 실제 `47642`가 activity=0을 게시하도록 함 |
| `0x10d734`, `0x10d738` | 각각 LONG | 0 | 실제 `49b0c`의 null callback/default input 경로 |
| `0x10f001` | BYTE | 0 | buffer debug, cue debug, 사운드 bit5 gate 비활성 |
| `0x10dc88` | LONG | `0x0010db88` | normal buffer의 실제 16-WORD shift cursor |
| `0x10d61a - 0x2c*i + 0x26`, `i=0..7` | LONG | `0x80000000` | spatial node의 source 비활성 표식; 단순 null은 비활성을 뜻하지 않음 |
| `0x10d61a - 0x2c*i + 0x2a`, `i=0..7` | WORD | 0 | spatial node timer/parent 갱신 비활성 |
| `0x10de2e` | BYTE | 1 | cue manual mode: stream을 읽지 않음 |
| `0x10de2f` | BYTE | 0 | cue allocation 요청 비활성 |
| `0x10d490`, `0x10d491` | 각각 BYTE | 0 | 실제 `2efa6` 상태 게시를 실행하되 helper 호출 없는 전이 없음 경로 |

출발 레지스터는 D0..D7=`fff00000,00f00000,fff00000,00f00000,ffffff00,00000055,00000000,00000af0`, A0..A4=`00000000,00000000,00000000,0010ccd6,00223aee`, A6=`00100820`이다. 실행 harness는 SR=`0x2000`, A5=`0x108000`, A7=`0x1feffc`, `[A7].LONG=0x000ff000`, initial physical bank2를 설정한다. SR은 실행 전 설정만 하고 hook 안에서 읽지 않는다.

완성 입력 SHA256은 `d51aba17d6dba2ff67ce77774f44df8c175c12c3cc52203e8dc34a7c61e266ec`이며 `artifacts/stage_frame_plan/input.bin`에 있다. seed 자체의 scene control/camera/cache/node 필드를 유지한다. 무작위 helper fixture 전체를 덮어 합성하지 않는다.

## 실제 전체 원본 관찰

임시 재현 도구 `artifacts/stage_frame_plan/probe.py`는 기존 `observe_scene_frame_execution.Observer`를 사용한다. Python 관찰 시작 주소만 `0x480bc`로 바꾸었으며 ROM, callee, return address를 patch/stub하지 않았다. 호출 기록용 추가 hook은 PC/A7/A6만 읽는다. 실행 명령:

```sh
.venv/bin/python artifacts/stage_frame_plan/probe.py
```

호출 순서는 실제로 `480bc → 47642 → 1a73c → 49b0c → 4aa88 → b4a2a → 6f1c2 → 4701e → e8a48 → 2efa6 → 480f0 → ff000`이었다. 각 직접 callee 진입 A7은 `0x1feff8`, `480f0`의 A7은 `0x1feffc`, 최종 A7은 `0x1ff000`이다. A6=`0x100820`을 모든 경계에서 유지했다.

Unicorn M68000의 hook 관찰 횟수는 1,240회(반환 sentinel 관찰 포함), RAM write는 203회였다. 오류와 MMIO read는 없고 fixed ROM 및 마지막 bank payload 불변 assertion을 통과했다. 원본이 순서대로 게시한 port는 아래 네 개뿐이다.

| 순서 | 크기 | 주소 | 값 |
|---:|---:|---:|---:|
| 1 | WORD | `0x2ffff2` | `0x2000` (bank3) |
| 2 | WORD | `0x2ffff0` | 0 |
| 3 | WORD | `0x2ffff2` | `0x1000` (bank2) |
| 4 | WORD | `0x2ffff0` | 0 |

원본 출력 `artifacts/stage_frame_plan/native.bin`의 SHA256은 `8ff378d791dcc354e64b995b82c37979b248272793e21b5e7a069b375fdc8135`. 최종 D0..D7은 모두 0, A0..A4는 `0x10d4ba,0x10dd98,0x10dd98,0x10d746,0x10d918`, A6은 `0x100820`, bank는 2다. 이것은 전체 call chain 입력의 유효성 근거이며 C++ 동등성 판정은 아니다. probe/입출력은 분석 중간 데이터로 Git에 추가하지 않는다.

## 런타임 리소스 계획

scene 리소스는 `observe_scene_general_initialization.resources(root,program)`이 manifest와 원본 payload를 확인하여 반환하는 **기존 458개 MS5D**를 그대로 사용한다. 개별 helper fixture에서 쓰는 임의 8/9-byte slice로 대체하지 않는다.

- 전용 scene debug table: `extracted/runtime/scene_debug.ms5d` (`CPU=ROM 0x1af12`, payload 512 bytes).
- 일반 scene windows: `extracted/runtime/scene_scripts/manifest.json`, `scene_maps/manifest.json`, `scene_secondary/manifest.json`, `scene_placements/manifest.json`의 기존 builder가 반환하는 resource/dependency/node-pointer 항목. `scene_scripts/scene_0488c4.ms5d`와 후속 motion/path windows를 포함한다. directory glob보다 기존 builder의 검증·중복 제거 결과를 사용한다.
- 이 smoke의 추가 필수 input mask: `extracted/runtime/stage_input/default_masks.ms5d` (`CPU=ROM 0x49ab0`, payload `10 20 40 80`). `100012!=2`인 null callback 경로가 실제 읽는다. scene 458개에 이것을 더한 459개가 안전한 첫 전체 bundle 후보이며, debug table은 API의 전용 인자로도 구분한다.
- input 확장 후보: `extracted/runtime/player_record_lookup.ms5d` (`0x4cf64`, 4092-byte lookup), `extracted/runtime/game_records.ms5d`. smoke의 marker 비활성/null callback 경로는 이 둘에 의존하지 않는다.
- cue 확장 후보: `extracted/runtime/stage_cue_control/default_cue.ms5d`, `default_stream.ms5d`, `extracted/runtime/stage_cue_frame/indexed_lookup.ms5d`, 같은 directory의 manifest에 있는 canonical cue 42개. smoke는 allocation=0/manual=1/debug=0이므로 cue ROM windows를 읽지 않는다.
- buffer/region/spatial의 기존 fixed/banked probe windows는 이미 scene bundle에 있는 `scene_scripts/scene_0488c4.ms5d`, `scene_scripts/palette_bindings_200504.ms5d`, `scene_maps/primary_lookup.ms5d`다. 이 경로들을 다시 추가하여 같은 MS5D가 두 번 matching되지 않도록 한다. bank2와 bank3의 동일 CPU 주소는 물리 source ROM offset으로 구분한다.

추가 input/cue 48개와 scene 458개의 원본 ROM span을 직접 비교했으며 서로 겹치지 않았다. 따라서 이 추가 목록 전체를 쓰면 exact identity 중복 제거 후 506개 후보이다. 이는 파일 목록/주소 검사 결과이고 새 전체 C++ loader 실행 검증은 아직 아니다.

## fixture 간 충돌과 유지할 원칙

`47642`가 `d68e`를 다시 계산한다. region fixture처럼 activity만 0으로 써도 player marker/bit7가 활성이라면 앞 호출에서 바뀐다. 여기서는 player marker를 바꾸고 실제 activity 계산을 실행한다. scene condition 경로에도 같은 marker/activity가 보이므로 별도로 scene의 condition/camera 구조를 덮지 않는다.

`10f001`은 buffer bit7/bit0, cue bit1, sound bit5가 공유한다. 각 helper fixture의 debug 값을 순서 없이 합치면 후속 sprite/byte wait를 유발한다. 별도 scene debug BYTE `10f000`과 혼동하지 않는다.

`10dc88`은 buffer cursor이며 player records `10dcba/10dce6`는 그 뒤다. buffer는 `10db88..10dc87`의 ring을 실제 순환시키며 normal 경로가 `10d746`/`10d918` 계열 출력 block도 clear한다. input callback slots는 `10d734/10d738`이다. input fixture 전체를 복사하거나 buffer 출력 block을 region/player source로 재사용하지 않는다.

spatial fixture의 source `0x106000`/parent `0x102000`, cue fixture의 cue `0x106000`, stream `0x106200`, external A6=`0x106100`은 서로 다른 단위 시험에서 임의로 정한 주소들이다. 전체 fixture에 동시에 복사하지 않는다. 특히 spatial node `+0x26` source의 상위 WORD bit15가 비활성 조건이므로 pointer=0은 원본 ROM 0을 읽는 활성 경로가 된다. 여기서는 여덟 source를 명시적으로 `80000000`으로 만든다.

cue offset LONG `10d3a2/10d3a6`는 scene/input parent 좌표와 같다. cue fixture의 `1234/5678` fractional seed를 복사하면 앞선 scene 상태가 달라진다. cue phase `10d418`도 scene elapsed phase와 공유하므로 전체 chain의 앞선 출력이 authoritative하다. 이번 manual/no-debug 경로는 이 좌표를 다시 쓰지 않는다.

scene seed에 있는 node/cache/free-list/script/motion/path 필드는 실제 initializer 산출물이다. cue allocation이나 scene placement를 켤 때 공용 free-list `104c9c/104ca0`, object marker, A6 관련 원본 상대 주소를 따로 검토해야 한다. 개별 cue fixture의 allocator chain을 기존 scene seed 위에 무조건 덮지 않는다.

## 꺼진 동작과 다음 검증

모든 직접 callee는 실제 실행했다. 다만 player activity/region source 복사, known callback 호출, buffer debug sprite 제출, spatial active region/timer, cue stream/allocation/debug sprite, sound 상태 전이는 이 첫 fixture에서 꺼져 있다. scene은 초기화된 실제 motion/path/camera/node update를 실행하며 script wait는 원본 `ffff`를 유지했다. 이 frame에서는 새 canonical script command/placement/physical-bank data read는 발생하지 않았다.

다음 순서는 이 exact input을 전체 C++ wrapper와 full RAM·14regs·ordered ports·bank로 비교하고, 이전 실제 출력을 다음 frame 입력으로 운반하는 smoke chain을 추가하는 것이다. 그 후 공유 flag/queue를 한 번에 한 범주씩 켜서 buffer 첫/둘째 sprite wait, cue wait, sound high/low wait에서 **같은 원본 CPU/stack**를 보존하고 재개한다. 앞선 helper 재실행이 없는지 경계 횟수와 이미 게시한 port를 함께 검증해야 한다. 활성 spatial/region/callback/placement의 정상 범위와 오류 transaction도 이후 독립 coverage로 남아 있다.
