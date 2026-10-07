# 메인 준비 구간과 사운드·sprite 대기 연결 리뷰

Baseline `f921d6b`. 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. e74..ec4/3ac8..3af6/3c08..3c40의 CPU주소는 고정 ROM 파일 오프셋과 같다. 메인이 이 구간의 명령·레지스터·실행 순서를 추론하고 코어와 상위 main 연결을 구현했다.

## 구현과 리뷰

MainFrameState에 sound/sprite pending을 추가했다. prepare_main_frame은 초기 화면 명령→sound drain→sprite 병합/정렬/출력→scene 좌표→palette→영상 delta를 원본 순서로 실행한다. 3aea와16bd0에서 반환해 앞선 단계를 재실행하지 않는다. sound의 D1.high/D3는 보존하며, 대기 D1.low는 captured byte next, 완료 D1.low는 restored word head다. e98/ea4의 rendering flag와 eaa..ec0의 unsigned word clamp/byte subtraction을 반영했다.

RAM과 pending/포트는 후보 상태로 실행한다. 후속 sprite 또는 palette 오류가 발생하면 초기 포트/사운드 변경도 외부에 반영하지 않는다. 상위 step_main_frame은 준비 완료 뒤 기존 debug/gate/input으로 계속 진행하고, 후속 debug 실패 역시 전체 호출을 롤백한다. 기존 ec4 반복을 e74로 바꾸지 않았다. 기본 상태의 next_pc=ec4 및 기존 CLI의 허용 PC도 유지한다.

새 CLI/Makefile/단위 검사를 서브에이전트에 위임하고 메인이 diff를 검토했다. 신규 테스트를 무관한 tile_resource_test에 간접 의존시킨 Makefile 변경은 직접 test prerequisite로 수정했다. CLI는 pending 옵션의 범위, 전체 입력·출력 경로와 inode 별칭, 실제 MS5P/MS5C를 검사하고 결과 JSON으로 다음 호출 상태를 전달한다. C++에는 compositions 인자를 제공하며 NULL은 빈 목록이다.

## 원본 비교와 검증 개선

혼합 실행에서 sprite가4MiB bank, palette가2MiB bank를 읽으므로 verifier는 PVC2ffff2 쓰기에 맞춰 실제 원본 bank window를 바꾼다. 단일 bank를 고정한 채 통합을 검증하지 않는다. 사운드 대기 시 원본 stack의3c2c/3c32 반환주소에서 high/low phase와 저장 word cursor를 추출해 pending을 독립적으로 비교한다. 같은 CPU context와 stack을 유지하고 실제 CLI RAM/D1/D3/pending을 승계한다.

초기166조건은 session86710 exit0이었다. 메인 리뷰에서 word-tail을 현재cursor+2로 다시 쓰는 것만으로는 새 명령 추가를 검증하지 못함을 발견했다. 실제4d84에0355를 추가하고 tail4로 변경하는6시퀀스로 보완했다. 기존 상태를 다시 초기화하지 않고 추가 명령을 소모한 뒤 sprite 대기와 완료까지 확인했다. ec4 이후 main 연결4조건과 pending/alias 오류도 추가하여 최종 검증을 실행했다.

최종 `.venv/bin/python tools/verify_main_prelude.py`: session36330 exit0. 182경계(sound대기28/sprite대기20/ec4완료134), 순서 있는 포트58,136개, 영상 읽기134회, 오류 보존33조건 통과. 10시퀀스 중6개는 대기 중 word 명령을 실제 추가한다. 실제 단일/다중 MS5C와 MS5P를 원본과 대조하고 사용하며 palette4718/479e/4c40/504c 네 경로도 실행 관측했다. 코드/현재 bank 원본 불변을 확인했다.

준비 반환에서 A5/A6/A7이 보존됨을 확인하고, 전체 RAM/D1/D3를 기존 main CLI에 넘긴4조건(ef2대기2/f3c callback경계2)이 원본과 일치했다. 후속 읽기는 총12회이며 callback 자체는 실행하지 않는다. 보고서 SHA256 `9356a45524c67501dfdec3da7746796895fdf83df3922473a19f4f2256e6c6a5`. 메인이 검증 코드와 실제 보고서 집계/해시를 확인했다.

`make -j3 all test`: session8022 exit0, Python73개/C++전체 통과, 경고 없음. 신규 main_prelude_test와 상위main의 e74→ef2/late-debug rollback 검사 포함. 로그 `artifacts/main_prelude_build_test.log`.

변경된 상위 main 경로의 회귀 검사 `tools/verify_main_frame_flow.py`: session49016 exit0, 기존54경계(main37/IRQ17), 포트746개/오류14조건 재확인. 보고서 해시도 이전 `0a43c89908e4fcdb2b458fba4abadedc7173259c67f6933815ab59873fdfe3a1`과 같다.

## 남은 범위

대기 해제는 명시적인 호스트 fixture다. 다음 단계는 실제 IRQ 소비 서비스가 생성하는 sound head/sprite cursor 진행을 새 준비 상태와 연결하는 것이다. 메인 시작 e4a의 전체 초기화, 자연 callback/IRQ task 본문, D1/D3 외 scratch/CCR, BIOS/SR/RTE/물리 시간과 전체 게임 복원은 남아 있다. 현재 VIDEO 인자는 같은 호출 안의 각 읽기에 같은 값을 제공한다.
