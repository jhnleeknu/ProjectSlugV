# 효과 진행과 조건부 팔레트 준비

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정ROM CPU/파일 entry5728, 갱신5728..5788,256회 펼친 dirty표시578c..718c, 준비게이트718c..7194, 준비7196.

RAM100000 기준 효과 상태:

| 오프셋 | 의미 |
|---|---|
| 7dc2,7dc4,7dc6 | 현재16비트 효과값. 준비 함수는 상위byte를 사용 |
| 7dc8,7dca,7dcc | 종료 시 대입할 목표word |
| 7dce,7dd0,7dd2 | 각 호출에서 더하는 step word |
| 7dd4 | 남은 호출 수 byte |
| 7ded bit7 | 준비를 건너뛰는 상태 gate |

타이머0이면 진행하지 않는다. nonzero이면 이전 상위byte들을 저장하고1 감소시킨다. 감소 후0이면 현재word를 목표word로 교체하고, 그 외에는step을16비트modulo 덧셈한다. 이전과 현재의 상위byte 중 하나라도 다르면256개 node의 flags에 dirty bit7을 설정한다. flags bit1(효과우회)이 있는 node는 건드리지 않는다. 하위byte만 변한 경우에는 dirty를 추가하지 않는다.

마지막에7ded bit7이 설정되어 있으면 그대로 반환하고, 아니면7196 준비 함수로 진행한다. 효과 갱신은 이 gate보다 먼저 발생하므로 준비대기 중에도 타이머와 현재값이 변할 수 있다. 원본 dirty표시 중 watchdog 쓰기는 C++ RAM API의 범위 밖이다.

`step_palette_frame`은 이 순서를 기존MS5P 준비 API와 연결한다. 준비 실패 시 타이머·효과·dirty표시까지 전체RAM을 rollback한다. 실제 프레임 호출 위치와 장치 동기화의 복원 완료를 의미하지는 않는다.

```
make all test
.venv/bin/python tools/verify_palette_frame.py
```

140조건은 타이머0/1/2/128/255 × 현재/step/목표7조합 × pending0/127/128/255다.256슬롯에 일반·우회·dirty flags와 실제MS5P 단일/혼합ID를 배치하여 원본5728부터 준비까지 전체RAM을 비교했고 모두 일치했다. 단위검사는 부분갱신 후 준비실패 rollback, 상위byte변화·하위byte만변화, 우회노드와 종료목표대입을 확인한다. 전체기존검사도 통과했다.

효과 상태를 설정하는 호출자, 오브젝트별 혼합계수 갱신과 실제 프레임의 업로드 순서·장치 타이밍은 후속 분석 대상이다.
