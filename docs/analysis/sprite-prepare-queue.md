# 표시 준비 루틴 통합

원본 프로그램 SHA256:29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f. 고정 ROM CPU 주소/파일 오프셋0x16bba..0x16cf8을 대상으로 한다.

## 확인된 순서

1. 0xce02에 새 태그0을 넘겨 지연 목록을 일반 링에 합친다. 선택된 지연 레코드의 첫word는 이전 태그로 바뀐다.
2. 0x166bc로 준비 끝0x108d36부터 생산 끝0x108d3a 사이를 안정 정렬한다.
3. 읽기0x108d34가 기존 준비 끝에 도달하기를 기다린다.
4. 방향 byte0x108d3c bit7이1이면 순방향,0이면 역방향으로 일반 링을 순회한다. 이 함수는 방향을 반전하지 않는다.
5. 두 슬롯 영역 각각에서 현재 방향의 cursor를 물리 경계로 초기화한다. 순방향은+4=하한, 역방향은+6=상한이다. 일반 emitter의 제한은 반대편 cached cursor(+6 또는+4)다. 실제 영역의 물리 상한/하한으로 무조건 채우는 것이 아니다.
6. X/zoom/타일 명령을 생성한다. Y 제어와 남는 영역 정리는 이어지는 갱신 함수0x16cfa가 담당한다.
7. bank shadow RAM0x100010을0으로 하고, 생산 끝을 준비 끝과 일반 쓰기 끝0x108d38에 복사한다. ready byte0x108d3d는0xff로 설정한다. 읽기 인덱스는 변경하지 않는다.

## C++ 계약

prepare_sprite_queue는64KiB RAM과 로드된 MS5C 리소스로 위 흐름을 실행한다. 일반 직사각형 레코드 분기를 지원한다. 레코드 marker0xffff, style low byte0..7, 생성기에 맞춘 X word 하위6bit=0을 요구한다. 두 슬롯 영역과 링의 짝수 인덱스·참조 범위를 검사한다.

기존 `prepare_sprite_queue`는 동기 호출이다. 읽기와 준비 끝이 다르면 consumer-not-synchronized 오류로 입력을 보존한다.

`begin_sprite_queue`는 원본16bba..16bcc를 실행한 메모리 상태를 공개한다. 지연 병합과 정렬을 한 번 수행하고, D0.word에 잡히는 준비 끝을 `SpritePreparePending.cursor`에 저장한다. 읽기 cursor가 이미 일치하더라도 waiting=true인 경계로 반환한다. 활성 pending에 begin을 다시 호출하면 오류다.

`resume_sprite_queue`는 원본16bd0의 비교를 수행한다. 읽기 cursor가 저장된 값과 다르면 RAM/pending을 보존하고 빈 출력으로 성공한다. 일치하면 현재 방향·풀 경계·링을 읽어 출력을 만들고 pending을 초기화한다. 이때 병합/정렬을 반복하지 않는다. 원본은 비교에는 저장한 D0.word를 사용하지만 이후 순회에는 RAM8d36/8d3a를 다시 읽는다. 대기 중 소비 서비스가 바꾼 방향이나 cached 슬롯은 재개에 반영된다. 실제 IRQ 스케줄링과 CPU 시간은 이 API 밖에 있다.

CLI는 기존 인자 앞에 `--begin` 또는 `--resume CURSOR`를 받는다. 새 모드는 리소스 0개도 허용하며 JSON waiting/cursor를 출력한다. begin에는 리소스가 필요 없고 resume의 비어 있지 않은 출력 경로에는 실제 MS5C가 필요하다. RAM 파일과 pending cursor를 다음 호출로 전달한다.

일반 미준비 개수와 지연 개수의 합은255 이하이고 이들을 합친 끝이 생산 끝과 같아야 한다. 입력 RAM의 인덱스만 맞추고 아직 채우지 않은 레코드를 순회하지 않도록 검사한다. 오류는 정렬·emission이 일부 진행된 뒤 발견되어도 호출자의 RAM·비디오 출력을 변경하지 않는다. 모든 임시 상태에서 성공한 경우에만 결과를 반영한다.

## 원본 실행 검증

analyze_sprite_prepare_queue.py는 먼저 검증된 정렬 모델과 C++ 개별 emitter를 조합하고 원본0x16bba를 실행한다. `--cpp`는 MS5C 로더를 사용하는 C++ 준비 dispatcher까지 비교한다. 양방향×개수0/1/4/20×일반만/일반+지연×링 시작0/510×cached 경계3개=96조건이다. 매번64KiB RAM 및 모든 비디오 명령을 비교한다.

추가로 같은 원본 CPU 상태에서0x16cfa를 실행하고 C++ 준비 출력 RAM을 refresh_sprite_queue에 넘겨 후속 상태·명령을 비교한다. 이96개 연속 실행도 일치했다. 따라서 단일 emitter 입력과 별개로 준비→갱신의 상태 전달을 검증했다.

비디오 이벤트는0x3c0000 포트 쓰기를 말한다. 리소스 직접 로딩은 원본 bank 장치 쓰기를 대체하며 bank shadow만 RAM 계약에 포함된다. 이 초기 검증의 범위는 일반 단일 직사각형이다. 현재 dispatcher는 emit_sprite_blocks를 사용하여 flip/다중블록도 지원하지만, CPU registers/flags, 실제 IRQ 스케줄링·타이밍, 전체 게임 루프·픽셀·사운드 검증은 여전히 미완료다.

## 메인 준비 구간 연결 시 레지스터 주의

메인 e74→ec4를 연결하려면 이 API의 RAM/VRAM 계약 외에 레지스터 전달을 추가해야 한다. 166d0/16734 등의 radix 경로는 MOVEQ로 D1 전체를 지우지만, emitter cf54..cf5a와 역방향11884..1188a는 SWAP→MOVE.W→ADDQ.W→SWAP으로 D1 상위word를 다시 쓴다. 따라서 sprite 준비 뒤 D1 상위word를 무조건 0 또는 입력값으로 처리하면 안 된다. 이후 배경 준비1879c는 D1 하위word만 덮어쓰므로 이 차이는 메인 debug/입력까지 전달될 수 있다. 현 단계는 이 레지스터 경로를 구현·검증했다고 주장하지 않는다. 정확한 emitter별 최종 D1 및 PVC 쓰기 순서를 추가 추적한 뒤 main prelude와 통합한다.

## 대기 경계 원본 비교

`.venv/bin/python tools/verify_sprite_prepare_wait.py`: session59056 exit0. 정렬 직후329경계, 반복 대기640경계, 완료328경계로 총1,297경계를 비교했다. 328개 시퀀스는 실제 CLI의 RAM/pending cursor와 같은 원본 CPU context를 이어 사용한다. 순서 있는 VRAM 쓰기459,520개, 출력 보존 오류27조건이 통과했다. 양방향·ring wrap·지연 병합·빈 큐·flip·disabled pool·cached 경계와, 대기 중 방향/경계/key 변경을 포함한다. 변경과 읽기 cursor 해제는 명시적인 호스트 fixture이며 자연 IRQ 실행으로 주장하지 않는다. main은 검증 코드와 생성 보고서의 집계/해시를 확인했다. 보고서 SHA256 `fc59d6fc5b1e296a18f20e4195a67f0557bd793734119c425d2027ee1fd2c0d4`.
