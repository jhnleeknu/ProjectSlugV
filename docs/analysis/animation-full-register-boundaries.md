# Animation 49fc6 전체 실행 연결의 후속 경계

Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 고정 CPU 주소는 ROM 파일 오프셋과 같다. 기존 animation RAM/carry API를 전체 register API로 확대하기 전에 메인이 원본 명령을 직접 읽고 확인한 주의점이다. 전체49fc6 구현·검증 완료를 뜻하지 않는다.

## Sprite 호출 전후에 보존할 상태

4a10c의 draw 변환은4a1dc에서 A0/A1 LONG을 stack에 저장하고4a1e0에서 현재 bank shadow WORD를 저장한다. 이후 shadow를0으로 만들고2ffff2에1000,2ffff0에0을 쓴 뒤4a1fa에서 실제cd58을 호출한다. 따라서 sprite 대기 중에는 interpreter의 A0/A1과 저장된 bank WORD, 복귀 위치가 필요하다. 재개 때 draw operand나 object 변환을 다시 읽으면 안 된다.

cd58이 반환한 뒤4a200이 저장된 WORD를 **live A5-7ff0**에 복원한다. 4a204가 당시 D0/D7의 하위 WORD를 저장하고, 복원된 bank shadow로 ((WORD+1)<<12)의 하위 WORD를 계산해 PVC 두 WORD를 출력한다. 4a222에서 저장한 두 WORD를 복원한 뒤 A0/A1 LONG을 복원한다. 재개 상태의 A5, 저장된 shadow, callee의 D0/D7 scratch와 실제 출력 순서를 별도로 보존해야 한다.

## MOVEM.W는 상위 WORD 보존이 아니다

`MOVEM.W (A7)+,D0/D7`은 두 WORD를 각각 signed16에서32bit로 확장한다. 일반 MOVE.W처럼 기존 상위 WORD를 보존하는 helper로 구현하면 틀린다. 같은 형태가 draw 복귀4a222, callback 복귀4a376/4a460에도 있다. 메인은 원본의 세 instruction을 그대로 실행하여 각기25개 조합(0000/0001/7fff/8000/ffff의 두 register 조합), 총75조건을 확인했다.

재현: `.venv/bin/python tools/observe_animation_word_restore.py`. 보고서 `artifacts/animation_word_restore/observation.json` SHA256 `f562ac986b13474b7886bf84c4bf5a8fee998239d432a44aa800a2dda12dd8ef`. 합성 stack과 서로 다른 상위 register 값으로 진입했고 전체15register, A7+4, CPU 쓰기0, stack guard와 원본 코드 불변을 확인했다. 이 관측은 **원본 단일 instruction의 복원 의미**에 대한 증거이며 전체 callback 또는 자연 도달성의 증거가 아니다.

## 아직 연결하지 않은 경로

- 49fc6 entry와4a0ca 반환은 실제 bank shadow 및 PVC 출력을 가진다. pointer0의 조기반환은 entry 출력만 발생하며 carry1이다. active 상태에서는object+17의 signedBYTE 양수만 감소시킨다.
- 4a2da의 sound opcode는 A0/A1 LONG을 저장하고3af8을 호출한다. sound high/low 대기 상태와 interpreter 복귀 상태를 함께 보존해야 한다.
- 4a30c와4a408의 callback은 원본 테이블4a500을 통해 간접 호출한다. callback 효과를 일반 no-op으로 처리하지 않는다. bank 복원과 위 MOVEM.W 의미도 유지한다.
- 4a382의200004 기반 조회는 현재 bank 매핑이 필요하다. fixed ROM MS5D window만으로 해당 뱅크 자료를 대체하지 않는다.
- 17개의 명령 entry는4a022의4byte 분기표에 있다. 단순히 opcode<44만 만족한다고 모든 BYTE 값이 의미 있는 명령은 아니다. 잘못된 중간 entry/TRAP의 정상 종료를 가정하지 않는다.

다음 단계는 실제489c2 등의 script 경로와 참조 범위를 확인하고, 전체 register/ports/pending 상태를 원본에 대조하는 것이다. 기존 RAM/carry 검증의 범위를 확대해 주장하지 않는다.
