# 동적 팔레트 소유권과 목록

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
원본 CPU/ROM 고정 주소: acquire8ebe..8ff2, release8ff4..9036, free helper8e4a..8e80. RAM 주소 아래는 CPU100000 기준 오프셋이다.

노드 영역4d92에는 256개의16바이트 슬롯이 있다. 노드+0/+2는 앞/뒤 연결, +4/+6은 같은16바이트 공간에 배치된 별개의 ID bucket sentinel, +8 참조word, +a/+c 원본 ID word, +e 별도 상태byte, +f flags이다. 링크는4d92 기준16비트 오프셋이다. ID 하위byte×16+4가 bucket sentinel이며 빈 슬롯 sentinel은1000이다.

acquire는 오브젝트+1d가4 이상이면 원본TRAP 경로다. flags bit0가0이면 해당 bucket의 다음 링크부터 같은 ID이며 node flags bit0가0인 첫 노드를 찾는다. 없거나 강제할당이면 free head를 사용하고 ID 두 필드와 flags|80을 쓴다. 참조는ffff가 아니면1 증가한다. 선택 노드는 bucket 맨 앞으로 이동한다. nodeoffset>>4인 slot을 obj+19+count와 obj+14에 쓰고 count를 증가시킨다.

빈 슬롯이 없으면 obj+14=ff, count와 목록은 그대로다. RAMf000 bit2가 켜진 경우 원본은 진단 표시 코드를 호출한다. 현재 C++ API는 그 UI를 구현하지 않고 오류로 반환한다. 원본 레지스터·CCR·스택 효과는 API 범위에 포함하지 않는다.

release는 obj 슬롯을 마지막부터 역순 처리한다. 참조0 또는ffff는 건너뛰며, 그 외에는1 감소한다. 0이 되면 bucket에서 빼고 free tail에 붙이며 ID 두 개를ffff, flags를2로 설정한다. node+e와 obj의 이전 slot/style byte는 지우지 않고 마지막에 count만0으로 만든다. 따라서 빈 슬롯 재사용 순서는 FIFO이고 한 오브젝트의 여러 슬롯 해제 순서는 역순이다. ffff는 여기에서 증가·감소하지 않는 고정 참조 상태다.

C++ `palette_allocator.h`는 RAM 작업본에 적용해 실패 시 원본RAM과 할당 상태 출력을 보존한다. 불량 링크·순환·4개 초과 획득·미지원 진단 UI는 오류로 처리한다. 이 입력 검사는 원본TRAP이나 메모리 손상을 흉내내지 않는다. `allocated`는 새 슬롯 생성 여부가 아니라 이번 acquire가 오브젝트에 슬롯 참조를 추가했는지 나타낸다.

검증 명령:

```
make all test
.venv/bin/python tools/verify_palette_allocator.py
```

원본과 전체64KiB RAM을 연속 연산마다 비교한다. ID 하위byte 충돌, 공유/강제할당, 여러 flags, bucket 앞 이동, 참조0/1/fffe/ffff,256슬롯 소진, 일반 실패, 역순 해제, FIFO 재사용을 포함한다. 별도 단위 검사는 손상 링크에서 참조 감소가 부분 적용되지 않는지와 오류 출력 보존을 확인한다.

이 모듈은 팔레트 소유권을 복원한다. MS5P 색 데이터의 동적 업로드·효과 처리와 전체 오브젝트 생명주기 연결은 별도 작업이다.

## 해제 경로의 D3

8ff4에서 참조 수가 1에서 0으로 줄면 8e4a가 노드를 해제 목록으로 옮긴다. 8e5c의 MOVE.W는 기존 노드를 목록에서 제거한 뒤의 free tail을 D3 하위 word에 읽고 상위 16비트를 유지한다. 여러 노드를 해제하면 마지막 이동의 값이 남는다. 참조 수가 0/ffff이거나 감소 후에도 0이 아니면 D3를 바꾸지 않는다. `release_palettes`의 선택적 D3 입출력이 이 동작을 반영하며 오류 시 후보 RAM과 함께 보존된다.

정적 오브젝트 재시작은 이 반환값을 연결 좌표 정리로 전달한다. 좌표가 활성 상태이면 이전 absolute Y 전체가 D3를 덮어쓴다. 최종 D1은 오브젝트 초기화 2730에서 ffffffff로 바뀐다. 다른 CPU 레지스터와 트랩 경로까지 모델링한 것은 아니다.

- `.venv/bin/python tools/verify_restart_registers.py`: 원본 506조건 및 오류 보존 5조건 통과. 보고서 SHA256 `05862a1870c440e1ab16e914f038db0dcfce6f1b52c83201f1b8172e15ad4dad`.
