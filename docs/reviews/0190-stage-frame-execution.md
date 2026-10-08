# 전체 stage frame 480bc 리뷰

Baseline `0552615c2e0b25f5b016bb90b1fd7ad27ba3fefa`, branch `codex/stage-frame-execution`. 대상은 C++11 상위 frame API/CLI, 단위 테스트, Makefile, 원본 비교 도구와 계약 문서다. ROM과 추출 데이터는 커밋하지 않는다.

Sol6.1/medium 세 작업자가 core/unit, CLI/문서, 원본 비교를 분담했다. 메인은 원본 호출 순서와 대기 stack 계약을 확정하고 실제 코드, CLI 인자 매핑, 검증 도구, 단위 테스트와 결과 provenance를 검토했다. 이후 완료된 작업자는 계약 문서 보완과 다음47a94 통합 계획으로 재배정했다.

원본480bc의9개 직접 호출을 순서대로 연결한다. 6f1c2는 실제 RTS다. 레지스터는 buffer 상태 한 곳에서 관리하며 scene 완료 후 bank2를 반영한다. buffer/cue/sound 대기 재개는 이전 단계를 반복하지 않는다. 성공한 대기는 이미 발생한 효과를 보존하고 호출별 ports/read count만 반환한다. 실패 시 전체 RAM/state/ports/read count를 보존한다.

Opus `claude-opus-5-5` / high 독립 읽기 전용 리뷰는 조합 로직 오류를 발견하지 않았지만 비활성 saved metadata 검증 누락과 대소문자 비구분 파일시스템의 새 출력 별칭 충돌을 지적했다. Sol이 비활성 buffer saved7개/enum 범위 검증과 회귀 테스트를 추가했다. CLI는 두 출력을 truncate 없이 예약하고 실제 device/inode와 모든 입력 리소스를 확인한 뒤 쓴다. 실패 시 새 placeholder만 identity 확인 후 제거한다. 리소스 canonical/inode 별칭도 중복 제거한다. 일반 쓰기/close 실패에 대한 두 파일 원자적 교체는 보장하지 않는다.

Opus 로그는 `artifacts/stage_frame_opus_review.json`이며 modelUsage는 요청 모델과 일치한다. effort는 CLI high 요청으로 확인하며 결과 자체의 별도 effort 필드는 없다. 실행240.514초, 보고 비용 $1.3691148, output23831 tokens(thinking17930), input32/cachecreation90805/cacheread829634. Opus는 테스트를 실행하지 않았으며 그 보고를 원본 동작 증거로 대체하지 않았다.

최종 `.venv/bin/python tools/verify_stage_frame.py`는 수정하지 않은 원본480bc 및 모든 callee와 실제 CLI96단계를 비교했다. 전체64KiB RAM/14레지스터/물리 bank/대기 상태/순서 있는264 ports/조건부 외부 read/정확한 JSON이 일치한다. buffer2상태, cue, sound5상태와 같은 CPU/stack/CCR을 유지한 재개를 검증한다. 재개 중 RAM 변경은 명시된 host 쓰기만 적용한다. 506개 MS5D를 canonical ROM에 대조하고 활성 spatial8개, region양쪽, cue allocation과 status0..3을 확인했다. CLI 오류148조건 및 실제 파일시스템에서 새 case alias 회귀1조건을 통과했다. 별도 CLI smoke6조건도 통과했다.

메인이 보고서의279개 입력 소스/바이너리 해시, 리소스 및 manifest 해시를 현재 파일과 다시 대조했다. report SHA256 `a6194a8280159525dde8266c1a54a214e0101f86b606c426fc13042946f53567`, CLI `2a3245bb932f3e8237f521e7740e7902c4c7e980b2cb3733387cb5c4ddcd1d88`. 최종 `make -j4 test`는 Python182/C++132/경고0/exit0이다. 빌드와 테스트 로그는 `artifacts/stage_frame_final_build.log`, `artifacts/stage_frame_final_test.log`에 보존했다.

이 단위의 통합을 수용한다. 제어된 fixture는 자연 scheduler/IRQ/플레이어 활성화, 전체 CCR/사이클 및 화면·오디오 동등성 증거가 아니다. 다음47a94 초기화 본문과480bc 연결의 정적 계약은 별도 후속 작업이며 아직 구현 완료가 아니다. 전체 게임 Goal은 미완료이며 active로 유지한다. 원격이 없어 로컬 커밋·리뷰로 통합한다.
