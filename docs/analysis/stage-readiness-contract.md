# 4847c stage readiness carry 계약

canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. fixed CPU 주소=ROM 오프셋. 메인이4847c..484b2,1bdde..1be38,289e..28ac,4dee2..4df18,4e166..4e184를 immutable 원본에서 읽었다. 이 이름은 분석 편의상 붙인 것이다. 이 문서는 의미 계약이며 현재 구현·검증 결과는 stage-readiness-execution.md와 검증 보고서를 따른다.

## 4847c 상위 순서

- D0=0(MOVEQ 전체32bit) 후1bdde를 호출한다. carry0이면 바로 최종carry0으로 반환한다.
- D0=1(MOVEQ 전체32bit) 후1bdde를 호출한다. carry0이면 바로 최종carry0으로 반환한다.
- 두 호출이 carry1이면 BYTE(A5+5684)를 읽는다. 비영이면 최종carry1이다.
- flag0이면4e166을 호출하고 D0.byte가 비영이면carry1,0이면carry0으로 반환한다.

조기 종료에 따라 D0/D1/A0/A4 최종값과 실제 도달하는 주소가 다르다. 반환 carry를 caller 분기용 bool로 별도 보존하며 다른 CCR bits/cycles까지 반환한다고 주장하지 않는다. RAM 변경은 없으며 JSR/RTS stack 효과는 oracle 영역에서 검증한다. 실행하지 않는 뒤쪽 주소를 미리 검증해 정상 조기반환을 거부하지 않는다.

## 1bdde

A0=A5−7348으로설정하고 D0.low&=1을 수행한다(상위WORD 보존). 결과비영이면A0=A5−7258로바꾼다.289e의LONG(A0)==270e이면carry0,다르면carry1이다.1bdde는289e carry0이면 자신의carry1로반환한다. 활성object인경우BYTE(A0+a8)의bit4가1이어도carry1이다. 그 외BYTE(A0+61)의bit7이1이면carry0이다.

남은 경로만4dee2를호출한다. 이callee의carry0이면1bdde는carry1이다. carry1이면D1.byte가3,4,5중하나일때carry0,그외carry1이다. D0.low/A0는모든경로에서갱신되며A4/D1은4dee2의실제효과만갱신된다.

## 4dee2

A4=A5+5d12, D0.low&=1을수행하고비영이면A4=A5+5d18로바꾼다. WORD(A4+4)의bit15가1이면carry0으로반환한다. 나머지는BYTE(A4)가1또는2일때만BYTE(A4+2)를D1.byte에읽고carry1을반환하며,다른값은D1을보존하고carry0이다. D1상위24bit는항상보존한다. 실제WORD주소의짝수정렬과2byte범위를검사해야한다.

## 4e166

D0=0으로초기화한다. BYTE(A5−75bc)==2이면D0.low|=1, BYTE(A5−74f8)==2이면D0.low|=2다. 두BYTE를항상순서대로읽는다. 결과D0전체는0..3이고나머지레지스터/RAM은보존된다.

## 검증 경계

full15레지스터/RAM/carry를미수정원본4847c로검증한다. marker270e/다른값,두objectflag,recordWORD부호/유형BYTE/상태BYTE,첫player조기반환/두번째조기반환/양쪽통과,flag5684및4e166mask0..3을조합한다. carry는원본RTS후hook밖에서읽으며carry를host계산값으로대체하지않는다. A5를임의로108000에고정하지않고실제도달한RAM span과정렬만검사한다. 출력메모리효과가없으므로새리소스는필요없다.

이 단위는47c6c 전체 복원 완료를 뜻하지 않는다.
