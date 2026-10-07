# 스프라이트 준비 대기·재개 리뷰

Baseline `cd2a841`. 메인 에이전트가 원본16bba..16cf8의 명령 순서, 핵심 C++ API, CLI와 단위 검사 diff를 검토했다. 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`; 이 구간의 CPU 주소는 고정 ROM 파일 오프셋과 같다.

## 의미와 구현

원본은 ce02 병합과166bc 정렬 뒤16bcc에서 준비 끝을 D0.word에 저장한다. 16bd0..16bd4는 이 저장값과 live 읽기 cursor를 비교한다. 16bd6 이후는 RAM8d36/8d3a, 방향과 슬롯 경계를 다시 읽는다.

`begin_sprite_queue`는 정렬 결과와 저장 cursor를 공개하고 `resume_sprite_queue`는 비교만 반복한다. 대기 중 리소스가 없어도 RAM은 그대로 유지되며 출력은 비운다. 소비가 끝나면 재정렬 없이 live 방향/풀을 사용해 출력한다. 실패는 후보 RAM과 임시 출력만 폐기하여 pending/RAM/기존 출력을 보존한다. 기존 동기 API는 후보 상태에서 이 두 단계를 호출하므로 소비 중 오류의 기존 트랜잭션 계약을 유지한다.

CLI는 uint16 cursor를 오버플로 없이 파싱하고 코어에서 짝수0..510을 검사한다. 기존 경로 별칭/동일 inode 검사와 출력 전 검증을 유지한다. 단위 검사는 정렬 후 key 변경, 반복 대기, 실패 후 정상 재개를 통해 재정렬과 상태 손실을 탐지한다. 메인 리뷰 후 새 검사 코드의 압축된 공백을 기존 스타일로 정리했다.

## 검증

`make -j3 all test`: session29146 exit0. Python73개 및 C++전체 검사 통과, 컴파일 경고 없음. 로그 `artifacts/sprite_prepare_wait_build_test.log`.

`.venv/bin/python tools/analyze_sprite_prepare_queue.py --cpp`: session26880 exit0. 기존 동기 준비96조건과 같은 원본 CPU 상태에서 후속 갱신96조건의64KiB RAM/순서 있는 VRAM 쓰기가 일치했다. 로그 `artifacts/sprite_prepare_wait_legacy.log`.

`.venv/bin/python tools/verify_sprite_prepare_wait.py`: session59056 exit0. 정렬 직후329경계, 반복 대기640경계, 완료328경계로 총1,297경계를 비교했다. 328개 시퀀스는 실제 CLI의 RAM/pending cursor와 같은 원본 CPU context를 이어 사용한다. 순서 있는 VRAM 쓰기459,520개, 출력 보존 오류27조건이 통과했다. 양방향·ring wrap·지연 병합·빈 큐·flip·disabled pool·cached 경계와, 대기 중 방향/경계/key 변경을 포함한다. 변경과 읽기 cursor 해제는 명시적인 호스트 fixture이며 자연 IRQ 실행으로 주장하지 않는다. main은 검증 코드와 생성 보고서의 집계/해시를 확인했다. 보고서 SHA256 `fc59d6fc5b1e296a18f20e4195a67f0557bd793734119c425d2027ee1fd2c0d4`.

## 남은 범위

이번 상태 모델은 실제 IRQ 실행기와 아직 연결하지 않았다. CPU scratch registers, CCR, PVC 포트와 물리 시간은 기존 준비 API와 마찬가지로 범위 밖이다. 특히 D1 상위word가 emitter의 SWAP 시퀀스로 바뀌는 것을 확인했으므로 메인 e74→ec4 통합에는 그 전달을 추가해야 한다. 비직사각형 레코드와 전체 게임 복원도 남아 있다.
