# Stage spatial frame 4701e 후속 원본 분석 초안

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 명령은 fixed 첫1MiB CPU=ROM offset. RAM CPU100000..10ffff,A5=108000. 메인이4701e..4706c와46f52..4701e를 직접 읽었다. 아직 구현/실행 검증 완료가 아니다. spatial은 편의 이름이며 모든 소비자의 의미를 확정하지 않았다.

## 4701e

A0=10d646,D0=0. LONG(A0)+를9회0으로 써 d646..d669를 지운다. WORDd67c=7;A0=10d61a. 각 반복에서 D0.low=WORD(A0+2a); 비영이면 lowWORD에서1빼고 같은위치에쓴후43e38을호출한다(기존 step_scene_node 재사용 후보, A3 보존 필요). 이후 WORD(A0+26)의 부호bit가0일때46f52를호출한다. A0-=2c; WORDd67c를1줄이고 borrow가없으면반복한다. 정상 고정루프는8개node이며 마지막카운터ffff. 함수진입A6와A3는직접바꾸지않는다. Helper의alias로loop RAM카운터가바뀌는경로지원범위는후속결정한다.

## 46f52

A1=LONG(A0+26); D0.low=WORD(A0+1c),D1.low=WORD(A0+20),D2.low=WORD(A0+14),D3.low=WORD(A0+18). signed D0.low>D2.low이면 EXG LONG D0/D2, signed D1.low>D3.low이면 EXG LONG D1/D3. 상위WORD까지교환한다.

MOVEM.W(A1)+,D4-D7은4WORD를 각각32bit signextend하고A1을8증가시킨다. D7.low+=1; D4..7 lowWORD를각각3bit왼쪽shift. D6.low+=D4.low,D7.low+=D5.low. D0.low+=D4.low,D1.low+=D5.low,D2.low+=D6.low,D3.low+=D7.low.

D7.low=WORDd67c; D6 LONG=0; D6.byte=BYTE(A1); ROL.B D6,2;D6.byte&=3; D6.low-=3. borrow없으면category쓰기를skip. borrow있으면NOT.W D6; A1=10d669;BSET.B D7,-(A1); DBRA D6 반복. 입력byte상위2bit가0/1/2/3이면 각각3/2/1/0byte(d668부터역방향)에bit(D7&7)를설정한다. NativeD6의highWORD는0이며최종low값도비교해야한다.

D4.low=ffa0(-96),D5.low=1ff(511). signed D0.low>511이면반환. D2.low-=D4.low 뒤 BLT면반환. D0.low-=D4.low 뒤 BGE가아니면D0 LONG=0. **46fcc는D2가아닌D1과D5를비교**하고signedD1.low>511이면D1.low=D5.low로쓴다. 원본의이피연산자를임의수정하지않는다.

D4.low=80(128),D5.low=1ff. signedD1.low>511이면반환. D3.low-=D4.low 뒤BLT면반환. D1.low-=D4.low 뒤BGE가아니면D1 LONG=0. signedD3.low>511이면D3.low=D5.low.

SUB뒤BLT/BGE는N xor V에따른조건이다. 단순히wrap된결과의부호만검사하면overflow경계에서틀린다. 입력signedoperand비교로조건을재현하되결과WORD는wrap해서남긴다.

D0.low>>=5;D2.low>>=5;D2.low-=D0.low. D1.low>>=5;D3.low>>=5;D3.low-=D1.low. A1=10d646+signextend(D0.low); BSET.B D7,(A1)+; DBRA D2 반복. A1=10d656+signextend(D1.low); BSET.B D7,(A1)+; DBRA D3 반복. DBRA는lowWORD감소/ffff종료이고highWORD보존. 연산순서와실제read/write범위를유지할필요가있다. 임의손상source가유발하는큰범위·loop에대한API지원한계는아직확정하지않았다.

## 후속 확인

- 43e38 전체 반환register adapter와A0보존 확인.
- 실제 source MS5D 분포/읽기 범위, bank2/3 mapping 선택과 필요한 rawprefix 규격 확인.
- 전체4701e의8개노드 및 직접46f52 경계/overflow/비트필드/DBRA상태를 whole-original로비교.
- 범위검사나 데이터분류를추정으로엔진에추가하지않는다. 현재초안은자연스테이지의콜리전완료증거가아니다.
