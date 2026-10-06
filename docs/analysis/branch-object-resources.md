# 분기 오브젝트의 그래픽 그룹과 팔레트 초기화

대상 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 ROM 주소는 CPU 주소와 파일 오프셋이 같다.

## 그룹 연결

`2b6e6` 및 `2b7ce`의 `MOVE.W #00f2,20(A6)`가 그래픽 그룹을 설정한다. 두 경로는 각각 `2b7c6→2b6e6→2b8fc`, `2b8ae→2b7ce→2b8fc`로 이어진다. `2b8fc` 이후 `2b964`가 오브젝트의 다음 실행 주소에 `2baf4`를 기록한다. `2baf4`의 조건을 통과하면 `2bb10`에서 분석한 애니메이션 `65f56`을 초기화한다. 외부 호출 도달성과 중간 helper 전체 부작용까지 증명한 것은 아니며, 원본의 정적 초기화 연결 근거다.

애니메이션 목록의 ID operand에 그룹 F2를 OR하면 57개의 고유 composition ID가 된다. 모두 기존 원본 포인터 해석기로 유효한 다중 블록 payload에 대응했다. 추출 도구는 두 그룹 설정 명령의 정확한 바이트를 확인하고 MS5C kind2 및 주소·뱅크·블록 수·해시 manifest를 생성한다. 그룹의 하위3비트가2이므로 그래픽 데이터 뱅크는 ROM400000이며 CPU200000에 매핑한다.

## 팔레트 관찰

`tools/analyze_branch_object_setup.py`는 원본 팔레트 초기화3ef2 후 각 오브젝트 초기화 prefix를 실행하고 자식 생성 코드 전에 멈춘다.

| 초기화 범위(끝 제외) | 순서대로 요청하는 source ID |
|---|---|
| 2b6e6..2b726 | 03d3, 039d, 0203 |
| 2b7ce..2b80e | 087d, 039d, 087a |

원본8ebe 호출은 flags=1이다. 비어 있는 팔레트 상태에서는 slot0,1,2가 할당되어 오브젝트+19,+1a,+1b에 저장되고 +1d=3, 현재 style palette +14=2가 된다. 슬롯 번호는 초기 팔레트 할당 상태에 의존하며 고정 ID가 아니다. 팔레트 노드의 source ID와 전체RAM 해시를 검증 보고서에 남긴다. 이번 실행은 원본만 관찰한 것으로 C++ allocator 복원 동등성은 주장하지 않는다.

## 실행 검증과 범위

```
.venv/bin/python tools/pack_animation_branch.py
.venv/bin/python tools/analyze_branch_object_setup.py
.venv/bin/python tools/verify_animation_branch_resource.py --video
```

제어된 오브젝트의 group F2와 기존 MS5A/MS5D에 57개 MS5C를 공급한다. 68개 시퀀스, 각24회 애니메이션, 각 단계의 prepare/refresh를 원본과 비교한다. 비교 대상은 애니메이션 전체RAM·carry, 준비/갱신 전체RAM·비디오 register 쓰기 순서와 값이다. 방향은 index 홀짝에 따라 양방향을 포함한다. 실제 제출된 ID 집합이 manifest의 57개 전체와 일치해야 통과한다.

이 결과는 최종 픽셀 화면 검증이 아니다. palette 스타일은 제어한 값이고 자연 오브젝트 생성·팔레트 lifecycle·전체 게임 타이밍은 남았다. 원본의 외부 Y-zoom 데이터가 필요한 rasterizer 작업도 기존 미해결 사항이다. PNG는 이 실행 경로에 사용하지 않는다.
