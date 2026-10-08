# 전체 stage frame 480bc 연결 계약 초안

정적 원본과 기존 API를 대조한 후속 설계이며, 아직 전체 frame 실행 비교를 완료한 문서가 아니다. 원본 canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 CPU 주소는 같은 ROM 파일 오프셋이다.

## 원본 호출 순서

480bc:47642 → 480c0:1a73c → 480c6:49b0c → 480cc:4aa88 → 480d2:b4a2a → 480d8:6f1c2 → 480de:4701e → 480e4:e8a48 → 480ea:2efa6 → 480f0:RTS. 6f1c2는 실제 원본 RTS 한 명령이며 생략 가능한 무효 호출이다. 나머지는 호출 전후 RAM과 레지스터를 그대로 이어야 한다.

- 47642/49b0c: step_stage_input_loop. 기존 지원 callback 범위를 유지하고 미지원 실제 callback 도달 시 오류를 반환한다. 오류를 정상 빈 동작으로 바꾸지 않는다.
- 1a73c: step_scene_frame. scene tables와 고정/뱅크별 원본 리소스를 사용한다. 진입 PVC writes는 bank3, 반환 writes는 bank2다. 다음4aa88에 bank2를 전달해야 한다. ports를 순서대로 누적한다.
- 4aa88: step_stage_buffer_frame. 첫/둘째 sprite 제출에서 대기할 수 있다. 현재bank, 외부A6, slot 상태 및 임시 보존 레지스터를 모두 유지한다. 재개는 4aa88의 captured phase부터 수행하며 이전47642/scene/input loop를 재실행하지 않는다.
- b4a2a: step_stage_region_frame. 49392의 activity_carry는 내부 계약에 필요하지만480bc 자체는 반환flags를 읽지 않는다. 기존 API의 오류 및 data bounds를 유지한다.
- 4701e: step_stage_spatial_frame. bank별 리소스와 live RAM을 전달한다. 카운터는 원본처럼 live 갱신하며8회로 제한하지 않는다.
- e8a48: step_stage_cue_frame. sprite 대기일 때 wrapper는 이 단계와 해당 레지스터를 보존한다. 재개 시 앞선 spatial/region/buffer를 반복하지 않는다. debug status는 helper 계약대로 보존한다.
- 2efa6: 사운드 상태전환 wrapper를 연결한다. 3af8/3c44의 byte 대기면 선택된 helper를 재개한다. 상태 게시를 반복하지 않는다.

## 상태와 오류 처리

외부 상태에는 상위 실행 단계, D0..D7/A0..A4/A6, 현재 bank, 해당 단계의 pending metadata가 필요하다. 상태를 복제할 경우 어느 필드가 레지스터의 기준인지 명확히 하고, 재개 시 서로 다른 사본을 혼용하지 않는다. 종료 시 pending은 초기 상태로 정규화한다.

성공한 호출의 ports는 그 호출에서 발생한 순서대로 반환한다. 대기 시 이미 수행한 RAM/port 효과를 유지하고 다음 호출은 이어서 새 효과만 생성한다. 검증된 API와 동일하게 실패는 해당 C++ 호출의 시작 RAM/상태/ports를 보존한다. 이 transaction 정책을 원본의 bus-fault 실행으로 혼동하지 않는다.

## 원본 비교에 필요한 근거

먼저 상위480bc를 수정·stub 없이 실행할 수 있는 일관된 RAM fixture와 기존 MS5D 묶음을 구성해야 한다. 개별 helper fixture들을 단순히 합쳐도 유효하다고 가정하지 않는다. 앞선 helper가 바꾼 live RAM과 레지스터가 후속 helper 입력이 되기 때문이다.

원본 전체 호출의 RAM/레지스터/순서 있는 MMIO와 bank/pending을 비교하고, 동일CPU의 실제 wait와 재개를 포함한다. 특히4aa88/cue/sound 대기 후 이전 단계가 다시 실행되지 않는 조건을 만들어야 한다. 여러 frame의 이전 출력을 다음 입력에 넘기되 host 조작을 명시한다. 이 검증과 실제 scheduler/IRQ/입력에 따른 자연적인 스테이지 실행은 별개의 단계다. 전체frame 일부 fixture 통과를 직접 플레이 가능으로 발표하지 않는다.
