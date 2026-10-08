# 47a94 진입 본문 실행 인터페이스

API는 D0..D7/A0..A6와 명시적인 frame 대기 상태를 다룬다. A7, call stack 쓰기, 전체 CCR, CPU cycle, 물리 RAM mirror는 이 계약에 포함하지 않는다. 원본 비교 harness는 게임 RAM64KiB 밖의 별도 stack을 사용하며 게임 RAM 비교에서 특정 byte를 마스킹하지 않는다. 이 조건의 전체 RAM 일치를 실제 기판 stack/mirror 동등성으로 확대하지 않는다.

RAM/TABLE 입력은 stream을 열기 전에 일반 파일인지 검사한다. 출력은 `O_NONBLOCK`으로 예약한 뒤 실제 descriptor의 일반 파일 여부와 inode를 확인하므로 FIFO 입력·출력으로 무한 대기하지 않는다. 개별 WINDOW의 FIFO도 거부한다. 두 CLI의 FIFO5종씩과 정상 실행·파일 별칭을 포함한16개 회귀 검사는 `artifacts/stage_entry_body_cli_review/smoke.json`에 기록했다.

원본 의미의 기준은 [본문 계약](stage-entry-body-contract.md)과 [연결 계획](stage-entry-body-integration-plan.md)이다. CLI 사용 규격과 검증 범위를 기록한다. 최종 수용 근거는 [리뷰0191](../reviews/0191-stage-entry-body.md)이다. canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 고정 CPU 주소 `0x047a94`는 같은 ROM 파일 오프셋 `0x047a94`다. banked 리소스는 MS5D의 CPU 주소와 ROM 오프셋을 구분한다.

## 빌드와 인자

```sh
make build/step_stage_entry_body
```

```text
build/step_stage_entry_body \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 \
  BANK STAGE BUFFER_PHASE SAVED_A6 SAVED_SLOT_A4 SAVED_SLOT_D7 \
  SAVED_D0 SAVED_D1 SAVED_D7 SAVED_A0 CUE_STATUS \
  SOUND_KIND SOUND_PHASE SOUND_SAVED EXTERNAL A5 BODY_PHASE \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS TABLE_MS5D [WINDOW_MS5D_OR_DIRECTORY ...]
```

기존 stage-frame의 숫자 29개 뒤에 A5와 BODY_PHASE를 추가한다. 숫자는 총31개, 필수 argc는 실행명을 포함해36이다. INPUT_RAM은 argv32, OUTPUT_RAM은33, OUTPUT_PORTS는34, TABLE_MS5D는35, 선택 windows는36부터다. 숫자는 부호 없는 10진수 또는 `0x`/`0X` 16진수이며 빈 숫자, 부호, 공백, 후행 문자와 범위 초과를 거부한다.

레지스터와 buffer saved 필드는32비트다. BANK는2/3, STAGE는0..3, BUFFER_PHASE는0..2, CUE_STATUS는0..3, SOUND_KIND는0..2, SOUND_PHASE는0..3, SOUND_SAVED는0..65535, EXTERNAL은0..255다. A5는 현재 `0x108000`만 지원하며 BODY_PHASE는0..2로 파싱한다. 개별 숫자 범위와 별도로 상태 조합의 유효성과 완료 상태 재호출 거부는 core API가 검사한다.

## 상태와 호출 순서

`StageEntryBodyState.frame`의 `buffer.registers`가 D0..D7/A0..A4의 단일 기준이고 `frame.buffer.a6`, `frame.buffer.bank`와 body의 `a5`를 함께 보존한다. BODY_PHASE0은 신규 본문이며 frame.stage0이 필요하다. BODY_PHASE1은 frame.stage1/2/3의 buffer/cue/sound 대기를 재개한다. BODY_PHASE2는 초기화와 최초 frame이 완료된 결과이며 이 CLI/API로 재호출하면 실패한다. 다음 `0x47af0` callback을 실행하는 상태가 아니다.

frame 상태 검증은 기존 [stage-frame API 계약](stage-frame-api-contract.md)을 따른다. 특히 stage1 밖의 buffer phase와 일곱 saved 필드는 모두0, stage3 밖의 sound fields는 모두0이어야 한다. cue enum0..3과 지원 bank2/3도 검사한다. 대기 재개에 반환 RAM과 모든 상태를 그대로 넘기며 EXTERNAL은 이번 호출의 sound 관측값을 지정한다.

신규 본문은 live record에서 scene 입력을 읽고 `1a5a4`를 실행한 뒤 record를 다시 읽어 `e8a1c` cue를 선택한다. flags bit1/3/5, `48398/30f4`의 기존 ROM8바이트 lookup 게시를 수행하고 record를 재독출하여 `e905c` events를 초기화한다. event API의15개 레지스터 결과를 반영하고 LONG(A6)에 `0x47af0`을 게시한 뒤 `480bc`로 연결한다. 초기화 ports와 frame ports를 원본 순서로 이어 붙인다. BODY_PHASE1 재개에서 초기화, lookup, flags, callback 게시를 반복하지 않는다.

C++ API 실패 시 RAM/state/ports/external_reads를 본문 호출 진입 시점 그대로 보존한다. 이는 원본 bus-fault 의미를 재현한다는 주장이 아니다. 초기화 자체는 external status를 읽지 않으므로 external_reads는 연결된 frame의 이번 호출 읽기 수다.

## 리소스와 파일 출력

RAM은 CPU `0x100000..0x10ffff`에 대응하는 정확히65536바이트다. TABLE_MS5D는 기존 버전1/kind1 fixed-data 로더로 읽고 windows에도 넣는다. 선택 windows는 개별 파일 또는 재귀 디렉터리이며 디렉터리의 `.ms5d` 파일을 정렬하여 읽는다. kind1 fixed/kind2 banked의 기존 헤더·매핑·길이·CRC 검사를 유지한다. 같은 TABLE/window의 canonical 경로 또는 inode 별칭은 중복 로드를 생략한다.

본문 wrapper가 직접 읽는 record와 indirection은 aligned live RAM 또는 고유한 fixed ROM window만 지원한다. banked record reader로 일반화하지 않는다. 구성 scene/frame helper의 기존 banked 리소스 지원과 본문 자체의 record reader 범위를 구분한다. 신규 본문의 실제 소비 경로에 맞는 scene, stage record, cue, event 및 후속 frame MS5D 묶음을 전달한다. lookup은 이미 존재하는 `extracted/runtime/stage_events/lookup_0030ec.ms5d`(CPU/ROM0x30ec, payload8)를 재사용한다. 로더가 인식하는 파일을 전달했다는 사실만으로 모든 의미상 resource bounds가 충족되는 것은 아니다. core는 실제 접근 단계에서 리소스를 검사한다. BODY_PHASE1 재개는 앞선 본문 초기화 리소스를 다시 소비하지 않지만 CLI에 제공한 파일 자체는 항상 기존 로더로 형식 검증하며 TABLE 인자는 계속 필요하다.

입력 RAM과 두 출력, TABLE은 서로 다른 canonical 경로/inode여야 한다. 선택 window가 입력 RAM 또는 출력의 별칭이면 거부한다. API 성공 후 두 출력은 truncate 없이 먼저 예약/open하고 `fstat` device/inode를 서로 비교하며 모든 입력/리소스의 `stat` identity와도 재검사한다. 검사 후에만 truncate와 쓰기를 시작하므로 아직 없는 두 출력의 대소문자 별칭도 실제 파일시스템의 inode로 검출한다. 예약/검사 실패 시 기존 파일을 보존하고 이번 호출에서 생성했으며 현재 identity가 같은 placeholder만 제거한다.

OUTPUT_RAM과 OUTPUT_PORTS는 순차적으로 쓰고 close 결과도 검사한다. 두 파일의 원자적인 교체나 쓰기/close 실패 후 rollback은 보장하지 않는다. OUTPUT_PORTS의 각 레코드는 기존9바이트 `>BII`(size1바이트, address/value big-endian32비트)이며 이번 호출에서 새로 발생한 write만 기록한다.

성공 stdout은 한 줄 JSON이다. 기존 frame 키 `d0..d7`, `a0..a4`, `a6`, `bank`, `stage`, `buffer_phase`, `saved_a6`, `saved_slot_a4`, `saved_slot_d7`, `saved_d0`, `saved_d1`, `saved_d7`, `saved_a0`, `cue_status`, `sound_kind`, `sound_phase`, `sound_saved`, `external_reads` 뒤에 `a5`, `body_phase`를 추가한다. 모든 값은 JSON 숫자다.

## 지원 범위와 검증

Makefile은 body 소스와 기존 STAGE_FRAME, SCENE_GENERAL_INITIALIZATION, STAGE_EVENT_INITIALIZATION의 sources/headers를 `sort` union으로 연결한다. `make build/stage_entry_body_test`와 `make test`에 body 단위 검증 대상도 등록한다. `make build/step_stage_entry_body`는 C++11, `-Wall -Wextra -pedantic` 설정으로 성공했고 진단은 없었다. 메인이 수행한 전체 빌드/test는 exit0이며 `artifacts/stage_entry_body_build_test.log`에서 서로 다른 `./build/*_test` 실행133개를 확인했다. 이 중 `stage_entry_body_test passed`가 포함된다. 133은 테스트 실행 파일 수이며 원본 fixture 수 또는 assertion 수가 아니다. FIFO 수정 후 최종 `make -j4 all test`도 exit0, Python182/C++133/경고0이며 로그는 `artifacts/stage_entry_body_final_build_test.log`다.

기존 helper의 미지원 input callback, RAM motion 제한과 traversal budget을 그대로 유지한다. BODY_PHASE2 이후 `47af0/72f0`의 scheduler·IRQ/carry 대기와 indexed dispatch는 이 wrapper의 범위 밖이다. 본문과 첫 frame 비교 통과만으로 자연적인 플레이어 활성화, 조작 가능한 게임, 화면/오디오 동등성 또는 전체 복원 완료를 주장하지 않는다.

## 최종 원본 비교

```sh
.venv/bin/python tools/observe_stage_entry_body.py
.venv/bin/python tools/verify_stage_entry_body.py
```

원본2790/3ef2를 실행한 pre-entry RAM에서 수정하지 않은47a94와모든callee를연속실행했다.142조건/152단계의전체RAM/15register/bank/pending/read/JSON과1,510,070 orderedports가실제CLI와일치한다.59actualrecords×2profiles,lookup8개와null/nonnull event,initialbank3,live record변경,5soundpending및동일CPU재개를포함한다.187오류조건(FIFO5종포함)과별도casealias1조건도통과했다.620MS5D는원본byte와일치함을확인했다.

결과 `artifacts/stage_entry_body/verification.json`의SHA256은 `6b0ad56cdf7300916f8274e55c78f613dca4dba3f92dbaa47cf3750671356454`다. native trace는schema1 gzip JSON이며모든PC/RAM쓰기/bank읽기를lossless로보존하고format/count/hash를검사한다. 초기화가cce0/cce8에서spritequeue를초기화하므로이noIRQ matrix는body에서시작한buffer/cue대기를증명하지않는다. 기존480bc검증의해당대기증거와구분한다.
