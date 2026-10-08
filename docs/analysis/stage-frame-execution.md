# stage frame 480bc 실행 인터페이스

상위 호출 순서와 pending 상태의 규격은 [연결 계약](stage-frame-integration-contract.md)과 [API 계약](stage-frame-api-contract.md)을 따른다. 원본 canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 여기의 고정 CPU 주소 `0x0480bc`는 canonical ROM 파일 오프셋 `0x0480bc`와 같다. 뱅크 리소스는 MS5D에 CPU 주소와 ROM 파일 오프셋을 별도로 보존한다.

## 빌드와 사용

```sh
make build/step_stage_frame
```

```text
build/step_stage_frame \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 \
  BANK STAGE BUFFER_PHASE SAVED_A6 SAVED_SLOT_A4 SAVED_SLOT_D7 \
  SAVED_D0 SAVED_D1 SAVED_D7 SAVED_A0 CUE_STATUS \
  SOUND_KIND SOUND_PHASE SOUND_SAVED EXTERNAL \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS TABLE_MS5D [WINDOW_MS5D_OR_DIRECTORY ...]
```

숫자는 정확히 29개이고 필수 인자를 포함한 argc는 34다. 부호 없는 10진수와 `0x`/`0X` 16진수를 받으며 부호, 공백, 빈 숫자, 뒤쪽 문자와 범위 초과를 거부한다. 레지스터와 buffer saved 필드는 32비트다. BANK는 2/3, STAGE는 0..3, BUFFER_PHASE는 0..2, CUE_STATUS는 0..3, SOUND_KIND는 0..2, SOUND_PHASE는 0..3, SOUND_SAVED는 0..65535, EXTERNAL은 0..255다. 개별 범위와 별개로 pending 필드 조합의 유효성은 C++ API에서 검사한다.

RAM 입력은 CPU `0x100000..0x10ffff`에 대응하는 정확히 65536바이트이며 출력도 같은 크기다. TABLE_MS5D는 기존 버전 1/kind 1 fixed-data 로더로 읽는다. 선택 window는 파일 또는 재귀 디렉터리로 받는다. 디렉터리는 `.ms5d` 파일만 수집하고 경로를 정렬하며 순환 디렉터리 참조를 방문한 canonical 경로로 차단한다. 개별 파일은 기존 kind 1 fixed/kind 2 banked 로더로 읽으므로 헤더, 매핑, 길이, CRC32 검사가 적용된다. 테이블도 windows에 포함한다.

입력 RAM, 두 출력, 테이블은 서로 다른 canonical 경로와 inode여야 한다. 선택 window가 입력 RAM 또는 출력의 별칭이면 거부한다. TABLE 또는 이미 등록한 window와 같은 canonical 경로/inode를 가리키는 리소스는 문자열이 달라도 중복 로드를 생략한다. 예를 들어 TABLE을 `./` 경로나 symlink로 다시 지정해도 같은 리소스로 처리한다.

C++ API 오류가 나면 출력 파일을 열지 않는다. API 성공 후에는 두 출력을 truncate 없이 먼저 예약/open한다. 새 파일은 `O_CREAT|O_EXCL`로 만들고 이미 있는 파일은 생성/truncate 없이 연다. 두 descriptor의 `fstat` device/inode가 서로 다르고 모든 입력/리소스의 `stat` identity와도 다름을 확인한 뒤에만 `ftruncate`와 쓰기를 수행한다. 아직 없는 출력 이름 두 개가 대소문자 비구분 파일시스템에서 같은 파일로 해석되는 경우도 실제 inode 비교로 거부한다. 이름을 소문자로 바꾸는 추정 규칙을 사용하지 않는다.

47a94 본문 CLI의 독립 리뷰에서 공통 FIFO 정지 문제를 발견하여 이 CLI도 수정했다. RAM/TABLE 입력은 stream을 열기 전에 `stat`/`S_ISREG`를 확인한다. 두 출력 예약에는 `O_NONBLOCK`을 적용하고 열린 descriptor를 일반 파일로 제한한다. 두 CLI의 FIFO 입력·테이블·두 출력·WINDOW 회귀10조건은5초 timeout 안에 오류 반환했고 기존 파일을 보존했다. 전체16조건 기록은 `artifacts/stage_entry_body_cli_review/smoke.json`이다.

예약/검사 실패 시 기존 파일을 보존하고, 이번 호출이 생성했으며 현재 `lstat` identity가 예약한 inode와 일치하는 placeholder만 제거한다. 검사가 끝난 뒤 RAM, ports를 순차적으로 쓰고 두 descriptor의 close 결과도 검사한다. 이 순차 I/O는 원자적인 두 파일 교체가 아니다. 쓰기 또는 close 단계의 실패에는 이미 truncate/기록한 출력의 rollback을 보장하지 않는다.

## 상태와 출력

STAGE 0은 신규 frame, 1은 buffer의 첫째/둘째 sprite 대기, 2는 cue sprite 대기, 3은 sound byte 대기다. 모든 stage에서 cue enum은0..3만 허용한다. STAGE1은 BUFFER_PHASE1/2가 필요하며 slot pending 검증은 buffer API도 수행한다. STAGE0/2/3에서는 BUFFER_PHASE와 `saved_a6`, `saved_slot_a4`, `saved_slot_d7`, `saved_d0`, `saved_d1`, `saved_d7`, `saved_a0`가 전부0이어야 한다. 비활성 saved 값도 오류로 검사한다. STAGE0/1/2의 sound 필드는 모두0이어야 하며 STAGE3은 kind1/phase1..2/saved0..255 또는 kind2/phase1..3/saved0..65535 조합만 허용한다. 완료 시 STAGE와 buffer phase/saved, sound 필드는0으로 돌아간다. 신규 frame의 순서는 `47642 → 1a73c → 49b0c → 4aa88 → b4a2a → 6f1c2(RTS) → 4701e → e8a48 → 2efa6`다. 재개는 저장된 단계부터 이어진다. 레지스터의 기준은 `state.buffer.registers`, A6와 bank의 기준은 `state.buffer.a6`와 `state.buffer.bank`다.

성공한 CLI의 stdout은 한 줄 JSON이다. 키는 `d0..d7`, `a0..a4`, `a6`, `bank`, `stage`, `buffer_phase`, `saved_a6`, `saved_slot_a4`, `saved_slot_d7`, `saved_d0`, `saved_d1`, `saved_d7`, `saved_a0`, `cue_status`, `sound_kind`, `sound_phase`, `sound_saved`, `external_reads`다. 재개에는 반환 RAM과 상태를 그대로 다음 입력으로 넘기며 EXTERNAL은 해당 호출의 관측값을 지정한다. cue status 숫자는 accepted=0, clipped=1, full=2, waiting=3이며 submit에 도달하지 않으면 이전 값이 보존된다.

OUTPUT_PORTS는 호출 중 새로 발생한 순서 있는 write만 기록한다. 각 레코드는 기존 9바이트 형식 `>BII`(size 1바이트, address와 value 각각 big-endian 32비트)다. pending 재개에서 이전 호출의 port를 다시 기록하지 않는다. `external_reads`는 이번 호출의 sound status 읽기 수이며 JSON에서 숫자로 출력한다.

scene/이미지의 의미상 요구사항은 신규 frame과 실제 접근 경로에서 API가 검사한다. sound 대기 재개는 이전 scene/이미지 요구사항을 재검사하지 않는다. CLI에서 제공한 파일 자체는 대기 재개에서도 기존 로더가 형식 검증하며, TABLE_MS5D 인자는 항상 필요하다. 따라서 sound 재개에 의미상 사용되지 않는 유효한 fixed MS5D 파일은 허용할 수 있지만 잘못된 헤더/CRC 파일을 허용한다는 뜻은 아니다.

C++ 호출 실패 시 RAM, state, ports와 external_reads를 모두 보존하는 transaction 규칙을 따른다. 이 규칙은 원본 CPU의 bus fault 동작에 대한 주장과 구분한다.

## 검증 범위

`make build/stage_frame_test`는 통합 API 단위 검증을 빌드하며 `make test`의 실행 대상에도 포함된다.

출력 보호와 alias 처리의 로컬 smoke 근거는 `artifacts/stage_frame_cli_review/smoke.py`와 `smoke.json`이다. 실제 대소문자 비구분 파일시스템에서 두 새 출력의 case alias 거부/placeholder 정리, 기존 alias 파일 보존, 두 번째 예약 실패 정리, 정상 seed의 원본 RAM/ports 일치, TABLE canonical/inode alias 중복 제거, resource/output 충돌 거부의 6개 검사를 통과했다. 보고서의 CLI source SHA256은 `e1ef614805c16a31a396a49e1e0379bcdf8c6072ab89044318c2472938c4b03f`이며 문서 갱신 시 실제 CLI 소스와 일치했다. 이 smoke 기록은 모든 통합 상태 조합의 최종 verifier 성공을 뜻하지 않는다.

최종 원본 비교는 `.venv/bin/python tools/verify_stage_frame.py`로 재현한다. 원본480bc와 실제 CLI96단계의 전체 RAM/14레지스터/bank/pending/순서 있는264 ports/외부 read/JSON이 일치했고 CLI 오류148조건과 실제 case alias 회귀1조건을 통과했다. 원본 실행에 사용하는 CPU의 stack/CCR을 대기 사이에 유지하며 명시된 host 쓰기만 반영한다. 결과는 `artifacts/stage_frame/verification.json`, SHA256 `a6194a8280159525dde8266c1a54a214e0101f86b606c426fc13042946f53567`이다. 메인 검토와 제한은 [리뷰0190](../reviews/0190-stage-frame-execution.md)에 기록했다. 최종 make test는 Python182/C++132/경고0이다.

제어된 fixture의 검증이며 자연적인 scheduler/IRQ/입력 기반 플레이 가능성이나 전체 게임 복원 완료를 주장하지 않는다. 전체 CCR/사이클 및 화면·오디오 동등성도 별도 검증이 필요하다.

FIFO 수정 후 동일 원본 verifier를 다시 실행하여96단계/오류148조건/casealias를 통과했다. 최신 보고서 SHA256은 `47645dd39e0df8241cb504cd637a99cdc751544b4ac47c9e1227d8d5705f53b5`이며 [리뷰0191](../reviews/0191-stage-entry-body.md)에 갱신된 CLI와 provenance 확인을 기록했다. 위 리뷰0190의 해시는 이전 커밋 당시의 기록이다.
