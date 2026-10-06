# 원본 양방향 애니메이션 루프 리소스

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 고정 ROM 주소는 CPU 주소와 파일 오프셋이 같다.

실제 초기화 `2bb06..2bb16`이 `65f56`을 애니메이션 상태에 설정한다. 이전 진입 조건은 `object+7f < 7`이다. `65f56..662c2`(끝 제외)의 876바이트는 각각 네 개의 duration1 프레임으로 이루어진 두 루프다. `object+7e`가 nonzero이면 앞 루프, zero이면 `6604c` 루프로 분기한다. 두 루프의 조건 분기는 반대 방향으로도 연결된다.

앞 루프는 callback14/1e와 indexed draw10/1e로 `object+7d`를 사용하며 프레임별 draw 항목이 5개다. 뒤 루프는 14/1d와 10/1d로 `object+7c`를 사용하며 항목이 17개다. callback1d 함수 포인터는 `4a574`의 `2b3e8`이며, index byte를 4배하여 operand table의 BE32를 읽고 `object+78`에 쓴다. `2b3e8..2b3f8`의 동작은 기존1e와 index 필드만 다르다.

`tools/pack_animation_branch.py`는 caller, 명령 경계, 조건/루프 대상, 콜백 선택자, 목록의 모든04 항목과 조회 범위를 확인한다. 출력은 다음과 같다.

- `animation_065f56.ms5a`: 원본 876바이트, 34개 상위 명령. 내부04 항목은 목록에 별도 기록.
- `branch_data_06431a.ms5d`: `6431a..6447a`, 352바이트. 각 목록에서 선택 가능한 인덱스가 참조하는 네 개 5-entry 창과 네 개 17-entry 창이다. 다른 인덱스가 게임에서 불가능하다는 주장은 아니다.
- `animation_branch.manifest.json`: 원본 주소, CRC 포함 바이너리의 해시, 명령과 목록 operand, 검증 범위.
- 기존 `data_04a76c.ms5d` 필드 테이블도 실행에 필요하다.

C++ `step_animation_resource INPUT_RAM INPUT_MS5A OUTPUT_RAM OUTPUT_STATUS OBJECT_OFFSET [INPUT_MS5D...]`가 네이티브 리소스를 읽고 실행한다. 기존 데이터 없는 호출도 유지한다. 출력이 추가 데이터 입력과 같은 파일/하드링크/정규화 경로이면 쓰기 전에 거부한다.

재생성 및 비교:

```
.venv/bin/python tools/pack_animation_data.py
.venv/bin/python tools/pack_animation_branch.py
make all test
.venv/bin/python tools/verify_animation_branch_resource.py
.venv/bin/python tools/verify_animation_pipeline.py --rom-script
```

원본 M68000과 C++의 68개 시퀀스×24회=1632회 전체 RAM·carry가 일치했다. 17개 후반 인덱스, 전반 인덱스 modulo5, 초기 timer0/ffff, speed128/256, 6회마다 외부 상태+7e를 바꾸는 양방향 전환을 포함한다. 대기 타이머와 callback 출력 및 producer queue가 비교 범위다. 기존 ROM 루프96회·192비디오 단계도 회귀 검증한다.

이 검증은 제어된 오브젝트 상태를 쓴다. 실제 게임의 오브젝트 생성부터 도달하는 경로, group 비트와 palette 연결은 아직 미확인이다. 목록의 identifier operand를 최종 MS5C ID로 오인해 추출하지 않았다. 따라서 이번 범위에는 이 스크립트의 화면 출력·자연 플레이 검증이 포함되지 않는다.
