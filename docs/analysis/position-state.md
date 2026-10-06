# 부모 좌표와 이동 증분을 사용하는 좌표 상태

대상 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
주소는 고정 ROM CPU 주소이며 같은 파일 오프셋이다. 제목과 필드명은 분석 편의를 위해 붙인 것으로 원본 소스 이름을 복원한 것이 아니다.

## 자료 구조

오브젝트 A6+0x2e에서 시작하는0x26바이트 구조를 여러 helper가 사용한다. 0x43e04는 이 주소를 A0로 설정하고0x43e08로 이어진다. 0x43e08은 D0/D1 word를 SWAP 후 하위word를0으로 만들어 local 좌표 두 long에 저장한다. 이는16.16 형태의 좌표 표현을 뒷받침한다.

| 구조 상대 위치 | 확인한 동작과 해석 |
|---:|---|
| +0,+4 | local 좌표 두 long |
| +8,+0xc | advance 경로에서 local에 더하는 long 증분 |
| +0x10 | 부모 구조 주소 또는0 |
| +0x14,+0x18 | local+부모 결과 좌표 |
| +0x1c,+0x20 | 갱신 표시 조건에 따라 보존하는 이전 좌표 |
| +0x24 | 갱신 표시byte |
| +0x25 | 두 소수부 carry와 부모 flag를 OR한byte |

정확한 물리 단위, 축 방향, 업데이트 주기와 중력/가속도 적용 위치는 아직 확인하지 않았다. 증분을 초당 속도로 환산하지 않는다.

## 갱신 순서

0x43e38은 먼저 이전 result 좌표 두 개를 읽는다. parent가 있으면 parent result를 local에 32bit 덧셈한다. 이때 low16bit 덧셈에서 X carry를 따로 구하고 flags=`carryX | (carryY<<1) | parent.flags`로 만든다. null parent이면 flags0이며 결과는local이다. flags를 먼저 쓰고 결과 좌표 두 long을 저장한다.

그 후 CPU0x10d494의 갱신 표시byte와 구조+0x24를 읽는다. 저장된 표시가0이면 새 결과를 previous에도 복사한다. 표시가 current와 다르면 옛 result를 previous로 복사한다. 같으면 previous는 그대로 둔다. self parent의 경우 이전 result가 부모 result로 쓰인다. 재귀 parent 갱신은 하지 않는다.

0x43ea4는 오브젝트+0x2e를 A0로 설정한다.0x43ea8은 local에 두 증분을 더한 뒤0x43e38로 들어간다. C++ `update_position(..., advance)`는 이 두 진입점의 지속 RAM 효과를 구현한다. unsigned32로 wrap을 명시하고 signed overflow에 의존하지 않는다.

0x43dbc..0x43dc6에서 global byte를 `(old&1)+1`로 설정하므로1,2가 번갈아 나타나는 구조다. 이 함수의 실제 프레임당 호출 횟수는 추적이 필요하다. 따라서 변수를 실시간 프레임 카운터로 단정하지 않는다.

## 실행 비교

```
make build/update_position
.venv/bin/python tools/verify_position_state.py
```

288개 초기 상태에 대해 원본 M68000 루틴을 실행한64KiB RAM 전체가 C++와 일치했다. null/다른/self parent, 소수부 carry 조합, 32bit wrap, stamp0/같음/다름, current0/1/2/255, advance on/off를 포함한다. 비교 결합 출력 SHA256 `3cf693770c0eb3391880a556f91666096d099c7857dc8c2cc15dd30f4e74dc09`.

C++ API는 구조와 부모가64KiB RAM 안의 짝수 주소일 때를 지원한다. 다른 CPU 영역 parent는 명시적 실패이며 원본 address exception을 재현한 것이 아니다. 유효성 검사를 쓰기 전에 수행한다. CPU register/CCR, 임시 스택과 실제 프레임 시점은 비교 범위 밖이다. 아직 움직이는 오브젝트 렌더링과 연결하지 않았다.
