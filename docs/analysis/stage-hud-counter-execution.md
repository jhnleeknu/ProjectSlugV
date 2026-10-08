# 4e286 HUD counter 인터페이스

원본 의미는 [연결 계약](stage-hud-counter-contract.md)을 따른다. canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 아래 fixed CPU 주소와 ROM 파일 오프셋은 같다. 이 API는 `4e286` 전체 helper 및 sound 대기의 checked continuation을 대상으로 한다. 상위 `47c6c` callback이나 자연 stage 실행 전체를 뜻하지 않는다.

## API와 상태

```cpp
struct StageHudCounterState {
    SoundWordExecutionState sound;
    std::uint32_t a5, a6;
    unsigned int phase;
    std::uint16_t saved_d0;
};
bool step_stage_hud_counter(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, StageHudCounterState& state,
    std::uint8_t external_status, std::uint8_t& external_reads,
    std::vector<VideoPortWrite>& ports, std::string& error);
```

RAM은 CPU `100000..10ffff`의 정확히65536바이트다. D0..D7/A0..A4의 유일한 저장 위치는 `sound.byte.registers`이며 A5/A6는 별도 필드다. 중복 caller register snapshot을 갖지 않는다. phase0은 fresh/완료 상태이며 saved_d0=0, sound.phase=0, sound.saved_low=0, waiting=false가 필요하다. phase1은 실제 sound 대기의 복귀 상태이며 sound.phase1/2와 waiting=true를 함께 보존해야 한다. 단순히 phase만 바꾸어 재개할 수 없다.

phase1은 저장한 sound 작업만 재개하고 flag/counter 감소 prefix를 다시 실행하지 않는다. 원본 sound 호출이 끝난 후에만 counter를1f로 쓰고 저장한 D0.low를 복원한다. D0 상위WORD 및 다른 sound scratch 레지스터 효과는 원본대로 유지한다. 완료 후 HUD/sound continuation 필드를 fresh 상태로 정리한다. 성공한 wait는 실제 효과를 commit하며, 오류는 RAM/state/external_reads/기존 ports를 보존한다. 성공 ports는 이번 호출의 ordered writes로 교체된다.

현재 sound-word/byte callee는 A5=`108000`에 대응하는 queue 주소를 지원하므로 **실제로 sound 호출 또는 그 재개에 도달하면 A5=108000이 필요**하다. 비정규 A5를 그 경로에서 transactional 오류로 거부한다. sound를 실행하지 않는 경로는 실제 A5-relative RAM 접근이 유효한 범위에서 임의 A5를 허용한다. 이 조건부 callee 제약을 전체 helper의 무조건 고정 A5 제한이나 임의 A5 sound 지원으로 확대하지 않는다.

## CLI

```text
build/step_stage_hud_counter \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  HUD_PHASE HUD_SAVED_WORD SOUND_PHASE SOUND_SAVED_BYTE SOUND_WAITING EXTERNAL_STATUS \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS [FIXED_MS5D ...]
```

숫자는21개이며 최소 argc는 실행명을 포함해25다. INPUT_RAM/OUTPUT_RAM/OUTPUT_PORTS는 argv22/23/24, optional resources는 argv25부터다. ENTRY 숫자는 없다. 모든 숫자는 부호 없는10진수 또는 `0x`/`0X`16진수이며 빈 숫자, 부호, 공백, 후행 문자와 overflow를 거부한다. register는32비트, HUD_PHASE0..1, HUD_SAVED_WORD0..65535, SOUND_PHASE0..2, SOUND_SAVED_BYTE0..255, SOUND_WAITING0..1, EXTERNAL_STATUS0..255다. 범위 외에도 state 조합의 유효성은 core가 검사한다.

성공 stdout은 정확히21개 key의 한 줄 JSON이다. `d0..d7`, `a0..a6`에 더해 `phase`, `saved_d0`, `sound_phase`, `sound_saved_low`, `waiting`, `external_reads`를 출력한다. waiting은 JSON boolean이고 나머지는 unsigned 숫자다. 외부 status 입력 자체를 JSON에 추가하지 않는다. OUTPUT_RAM은65536바이트, OUTPUT_PORTS는 ordered9바이트 `>BII`(size1바이트, address/value big-endian32비트)다. 오류는 stderr에 쓰며 성공 JSON을 출력하지 않는다.

외부 status는 원본 `d00046`의 조건부 읽기에 공급하며 external_reads가 이번 호출의 실제 읽기 수다. captured sound 재개는 이 status를 다시 읽는 호출로 바꾸지 않는다. 대기 여부는 phase/JSON과 반환 RAM을 함께 보존하여 다음 호출로 전달해야 한다.

## helper 효과와 raw lookup 리소스

BYTE(A5+5d1f)=0이면 레지스터를 그대로 보존하고 출력 없이 완료한다. D0.low가 unsigned99ff를 넘으면35f0의4×2 표시로 tail call하며 sound/palette/lookup을 실행하지 않는다. 그 외에는 A5+5d20 counter 처리와 조건부 sound1ac3, full `8cda` palette blend, 두 차례35f0 출력을 원본 순서로 연결한다. late lookup/draw 실패도 호출 전체를 보존하는 checked 실패다. 각 부분의 정수 폭·SWAP·레지스터 효과는 연결 계약과 [palette-blend](palette-blend-execution.md), [block-draw](stage-block-draw-execution.md) 범위를 따른다.

숫자 조회는 원본 WORD를 BCD로 정규화하지 않는다. `4e272..4e286`의 명목상10 WORD 뒤에는 코드가 있지만 허용된 입력은 index10..15의 코드바이트도 WORD 데이터로 읽을 수 있다. packer는 따라서 **raw lookup read span `[4e272,4e292)`32바이트**를 그대로 보존한다. 이를 논리적16개 digit table 또는 주변 데이터 전체의 경계라고 주장하지 않는다.

`tools/pack_stage_hud_counter.py`는 기존 MS5D v1 kind1 container `extracted/runtime/stage_hud_counter/lookup.ms5d`와 `manifest.json`을 생성한다. CPU=ROM=`4e272`, payload32바이트, container64바이트, payload CRC32=`07354387`이다. payload SHA256은 `095633d24bf3730eff7bc16f1f39975b01599421b749480b2ad6b8e30859bdda`, container SHA256은 `97e2e029a44238156c22f96c85ea53c66cfebe8f7d3289ed5e8669ba585a8bb6`이다.

stable resource ID는 `stage-hud-counter-raw-lookup`, WORD read IDs는 `stage-hud-counter-lookup-word:00`부터`:15`다. metadata는 각 read의 CPU/ROM 주소·payload offset·WORD값과 명목digit entry 여부, provenance와 scope를 기록한다. 원본 hash와 정확한 payload/container를 검사하고 source를 다시 읽어 변경이 없음을 확인한다. 임시 staging에 두 파일을 쓴 뒤 container를 검증하고 목적지로 publish하며 게시 결과도 대조한다. 각 파일 replace는 순차적이므로 디렉터리 전체의 원자적 교체를 보장하지 않는다. 추출 원본 데이터와 runtime 파일은 Git에 추가하지 않는다.

CLI는 supplied MS5D마다 기존 C++ fixed-data loader를 호출한다. 동일 canonical 경로/inode 별칭은 중복 로드를 생략하지만 서로 다른 파일의 중첩 읽기는 core가 모호성/partial read로 거부한다. resource0개도 받되 실제 fixed lookup 경로를 실행하면 해당 read 전체를 덮는 고유 window가 필요하다. helper가 소비하지 않는 supplied 파일도 로더 검증은 수행한다. banked lookup은 지원한다고 주장하지 않는다.

## 파일 보호와 I/O 한계

RAM과 모든 resource는 열기 전에 `stat`/`S_ISREG`로 일반 파일임을 검사하여 FIFO 등 특수 입력을 거부한다. RAM/두 출력의 canonical 경로·inode 충돌과 resource의 RAM/출력 별칭을 거부한다. 숫자·입력·resource·core 실패 시 출력은 열지 않는다.

core 성공 후 두 출력을 truncate 없이 nonblocking으로 예약한다. `fstat`으로 두 파일의 일반 파일 여부와 실제 device/inode를 비교하고, 모든 등록한 입력/resource의 현재 inode와도 대조한 뒤에만 truncate/쓰기한다. 실제 case alias도 inode로 검사한다. 예약/검사 실패에는 기존 파일을 보존하고, 이번 호출에서 새로 생성했으며 현재 identity가 예약 inode와 같은 placeholder만 제거한다. 순차 write와 close를 검사하지만 실제 I/O 실패에는 두 출력의 원자적 교체나 rollback을 보장하지 않는다.

## 빌드와 검증 상태

Makefile의 source/header union은 새 HUD core와 기존 sound-word/byte 실행, palette-blend/palette-control, block-draw 및 fixed-data loader 의존성을 포함한다. all/test에 CLI/단위 target, runtime-resources에 packer를 등록한다. 별도 리소스 형식이나 object restart 구현 전체는 필요하지 않다.

```sh
.venv/bin/python -m unittest tools.tests.test_stage_hud_counter_resource
.venv/bin/python tools/pack_stage_hud_counter.py
make build/step_stage_hud_counter build/stage_hud_counter_test
./build/stage_hud_counter_test
.venv/bin/python tools/observe_stage_hud_counter.py
.venv/bin/python tools/verify_stage_hud_counter.py
```

packer의 합성 데이터/mocked hash 단위7개는 통과했다. 실제 canonical32바이트를 추출하여 payload SHA/CRC,64바이트 MS5D container hash와 재생성한 metadata를 확인했다. verifier는 이 `lookup.ms5d`를 실제 CLI에 전달하여 C++ fixed-data 로더를 거친 조회 결과와 비교했다. index10..15의 코드바이트도 raw WORD로 읽으며 명목상10개 digit으로 정규화하지 않는다.

원본 관측은 `artifacts/stage_hud_counter/observation.json`이며 SHA256은 `b87af2a6a5a5e2506072e241b8c003aa9ff889cd6acd430880a23c06d17d95d5`다. 이 보고서는 decimal slot12의 실제 RAM node `4d92 + 12*16 = 4e52`에 palette fixture를 설정한 수정본이다. 원본128조건에 별도168조건을 더한296회 실제 CLI 비교에서 전체64KiB RAM·15레지스터·HUD/sound pending 상태·ordered ports2732개가 일치했다. 원본 실행의 RAM/port 쓰기 replay, lookup read, sound 외부 read, saved WORD와 sound phase의 stack 근거를 감사했다. 원본 observer 자체와 실제 C++ 비교 verifier의 역할을 구분한다.

추가168조건은 다음을 포함한다.

- sound wait9단계: high/low 각각 시작·유지·해제6단계와 high→low 연속 대기의3단계다. 같은 원본 CPU의 stack/CCR을 유지한 채 재개하며, host consumer release와 prefix 필드 poisoning을 명시하여 counter 감소/flag prefix가 반복되지 않는지 확인했다. captured 재개의 external_reads는0이다.
- 조건부 external status0/1/255의3조건은 실제 외부 읽기1회와 후속 결과를 비교한다.
- unsigned 허용 upper BYTE00..99의154조건 sweep은 비BCD nibble을 포함한 fixed lookup을 비교한다.
- A5=`ff140`/`ff141`의2조건은 A5-relative counter BYTE와 palette slot 필드의 live alias를 비교한다. 이들은 sound를 실행하지 않는 경로이며 임의 A5 sound 지원의 증거가 아니다.

오류187조건에는 숫자·RAM·continuation 조합, 실제 sound 호출/재개의 비정규 A5, missing/partial/ambiguous resource, late lookup 오류, 경로/hardlink/symlink 충돌, RAM/resource/두 출력 FIFO, 새 placeholder 정리와 실제 대소문자 비구분 파일시스템의 새/기존 빈 출력 alias가 포함된다. 입력·리소스·기존 출력 및 pending transaction 보존을 확인했다. 이 checked 실패를 원본 invalid 입력의 정상 실행과 같은 결과라고 주장하지 않는다.

최종 보고서는 `artifacts/stage_hud_counter_execution/verification.json`이며 직접 계산한 SHA256은 `f6bc9947607e214476a861926f22b8ba1308bb893a92bfc86e4020360e076abf`다. 문서 갱신 시 `inputs`24개, `native_inputs`7개, `native_artifacts`1185개의 현재 파일 hash가 보고서와 모두 일치했다. 이 확인에는 CLI binary·core/callees/header·Makefile·실제 lookup container/manifest 및 원본 관측 결과가 포함된다.

메인의 `make -j4 all test`는 exit0으로 완료했다. `artifacts/stage_hud_counter_execution_build_test.log`에서 Python196개 검사, 서로 다른 C++ 테스트 실행 파일139개, warning 진단0개를 직접 확인했다. Python196에는 새 packer7개가 포함된다. C++139는 실행 파일 수이며 native 조건이나 assertion 수가 아니다. 독립 Opus5.5/high 리뷰에서는 조치가 필요한 버그가 보고되지 않았다. 이 helper의 focused 검증이나 리뷰가 전체 복원 목표의 완료를 뜻하지 않는다.

A7/stack/CCR/cycles, 물리 RAM/video mirror, rendered pixels, 상위 callback와 자연 scheduler/IRQ는 이 checked helper의 범위 밖이다. 명시된 sound A5 제한이나 오류 transaction을 원본의 모든 입력에 대한 정상 실행 동등성으로 확대하지 않는다.
