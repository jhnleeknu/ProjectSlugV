# Animation 필드 변경과 상대 분기 전체 상태 계약

Baseline `b5ded33`. canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 fixed CPU 주소는 ROM 파일 offset과 같다. 메인이 원본4a276..2d8,4a2f2..308,4a3de..404를 명령 경계로 읽고 실제bytes를 대조했다. 다음7개명령의 구현 계약이며 검증 완료 보고가 아니다.

모든명령은4a276에서D6=A1,LONG(A0)=D6를쓴후49ffe로dispatch한다. 새pending/state/CLI는필요없다. 원본순서의실제읽기/쓰기만검사하고전체invocation RAM/regs/metadata/carry/ports/external_reads rollback을유지한다. table과script는현재MS5D/MS5A및liveRAM을소비한다.

| opcode/handler | 원본 효과 |
| --- | --- |
|18 /4a27e | BYTE(A1)+→D0.byte(상위24보존);WORD(A1)+→D1.low(상위16보존);ADD.W D1,D1 wrap;A2=4a76c;WORD(A2+signed16(D1.low))→D1.low;BYTE D0→(A6+signed16(D1.low)) |
|1c /4a294 | D0=0;selectorBYTE(A1)+→D0.byte;ADD.W D0,D0;A2=4a76c;WORD(A2+signed16(D0.low))→D0.low;WORD(A1)+→D1.low(상위16보존);WORD D1→(A6+signed16(D0.low)) |
|20 /4a2ac | 1c와같은selector/table읽기뒤LONG(A1)+→D1전체;LONG D1→(A6+signed16(D0.low)) |
|24 /4a2c4 | 1c와같은selector/table읽기뒤SUBQ.B1 (A6+signed16(D0.low));RAM BYTE만wrap해서감소,그BYTE를D0에로드하지않음 |
|34 /4a2f2 | A1+=1(읽지않음);D0=0;WORD(A1)+를직접object+70에씀.D1은불변 |
|38 /4a300 | A1+=1(읽지않음);WORD(A1)+를직접object+20에씀.D0/D1은불변 |
|2c /4a3de | D0=0;selectorBYTE(A1)+→D0;ADD.W D0,D0;A2=4a76c;tableWORD→D0.low;lengthWORD(A1)+→D2.low(상위16보존);liveBYTE(A6+signed16(D0.low))→D0.byte(WORD상위BYTE보존);ADD.W D0,D0;unsignedD0.low>=D2.low이면선택읽기생략;작으면WORD(A1+signed16(D0.low))를읽고signed16(그WORD)를A1에더함;그결과A1에signed16(D2.low)를다시더함 |

18은WORD selector를두배하여wrap한signedWORD를table주소에더하므로실제raw창은[4276c,5276c)65536BYTE다. 나머지selector는BYTE이며[4a76c,4a96c)512BYTE다. 기존widecontrolMS5D에모두포함된다. 어떤rawWORD도논리적필드정의라고단정하지않는다. targetRAM의정렬/범위를실제도달시검사한다.

2c의선택값은일반absolute jump pointer가아니며두signed加算을순서대로한다. length0도livefield를읽는다. index+2<=length 제한은원본에없다. 선언length1/index0은WORD를읽을수있다. 큰unsigned index도signed주소에서는뒤로갈수있다. length역시비교는unsigned,최종변위는signed다. 단계별주소계산은넓은signed타입으로검사하고overflow는checked실패로한다. 생략경로는선택WORD를읽지않으며계산된최종cursor는4a276의pointer쓰기후실제dispatch시fetch한다.

쓰기가statepointer나다음script와alias할수있다. 예컨대object+26의임시write는곧4a276으로덮일수있지만원본쓰기순서대로수행해야한다. live다음script가바뀌면변경후bytes를읽어야한다.34/38은사실상paddingBYTE를건너뛰며읽는것처럼구현하지않는다. command후00/28의실제timer효과와원본carry를포함한whole49fc6로검증한다.

지원되지않은30 sound/3c callback/40 bankedlookup 및14의기타callback은이번단위로완료되지않는다. 원본관측·C++대조·리소스소비·회귀·리뷰결과는후속실행문서에기록한다. 자연게임도달성·전체Goal은미완료다.

## 후속 구현 상태

이 계약의7명령은후속C++구현과원본비교를통과했다. 정확한조건수·실제MS5A소비·오류검사·검증한계는 `animation-field-execution.md`와리뷰0211을따른다. 이계약자체를전체Goal완료근거로사용하지않는다.
