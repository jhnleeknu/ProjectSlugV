# Animation draw 4a10c 전체 상태 계약 초안

Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 주소는 fixed CPU=ROM offset이다. 메인이 원본4a10c..4a22a를 직접 읽고 기존decode_animation_draw와 구분하여 정리했다. 새 전체register C++ 구현 완료나 전체49fc6의17opcode 검증을 뜻하지 않는다. 실행 관측으로 다음 계약을 대조한 뒤 구현한다.

## Operand 읽기와 조기반환

D0/D5/D6는 MOVEQ0으로 전체32bit를 초기화한다. A1에서 control BYTE→D5, X BYTE→D0, Y BYTE→D6, packed LONG→D7을 순서대로 읽고 각 읽기 뒤 A1을 증가시킨다. 총7byte다. operand는 opcode04의 다음 주소에서 시작한다.

D7=007ff800이면 즉시RTS한다. 이때 object필드를 읽거나후속register를0으로정리하지 않는다. 다음으로 object+20 WORD를 D7.low에 OR한다. timerBYTE(A0+4)가음수이면RTS한다. 이어 object+61 bit3이켜지고 BYTE(A5-7ff1)bit0도켜지면RTS한다. 앞선조건에서반환했으면 뒤조건의접근을요구하지않는다. 기존decode_animation_draw가skip에zero결과를주는것과원본의전체레지스터상태는다르다.

## 좌표와 flag 변환

D1=LONG(A6+12). EXT.W는D0/D6의BYTE를하위WORD에부호확장하지만상위WORD는0그대로다. control D5의두 LSR.B가각각 ADDX.W D6,D6 및 ADDX.W D0,D0의X를제공한다. WORD단위두배+bit는modulo65536이다.

D1 bit0이면 NEG.L D0, bit1이면 NEG.W D6다. 이폭의차이를단순한공통16bit부호반전으로치환하지않는다. 이어 object+42/+46 WORD를각각D0/D6.low에더한다. D3전체=0, D2.byte=object+53. D2상위24bit는보존하고두 LSR.B→SUBX.W로flag bit0/1을각좌표에서뺀다. 그뒤 SWAP D0와 MOVE.W D6,D0로packed좌표를구성한다.

D4.byte=D5.byte 후AND.B3, EOR.B D4,D1이원본flag결합이다. D4상위24bit를초기화하지않는다. D5는 LSR.W2 후값10이상이면10을빼고D1.byte bit2를뒤집는다. 다시5이상이면5를빼고palette선택으로간다.

5미만갈래는 WORD(A6+16)를D4.low로읽고 **ASR.B1 D4**를수행한다. 부호검사는결과BYTE이고carry는이동전bit0이다. 양수/0이고carry1이면 D1.byte를D4.byte에넣고 D4.low를D1.low에복사한다. 따라서object+16의상위BYTE와D1의flagBYTE가결합된다. 다른갈래에서는D5<4일때object+19+D5의BYTE를D1.byte에읽고LSL.W8한뒤저장한flagBYTE를복원한다. D5>=4이면그선택읽기를생략한다.

마지막D5.low=WORD(A6+1e). 여기까지의D0..D7/A0..A6전체가cd58진입상태의근거이며출력네register만비교해서는충분하지않다.

## Sprite 대기와 복귀

A0/A1 LONG과live bank shadow WORD(A5-7ff0)를stack에저장한다. shadow0쓰기와PVC WORD1000→2ffff2,0→2ffff0을실행한뒤cd58을호출한다. 기존fullspriteAPI의normal/deferred/clip/full/wait 상태를그대로사용한다.

대기시현재draw의operand/좌표/palette전처리와저장작업을반복하면안된다. saved A0/A1/bank와상위호출복귀위치를보존한다. cd58완료후bankshadow를복원하고PVC재설정후D0/D7을MOVEM.W로부호확장복원한다. A0/A1은LONG복원이다. 정확한instruction별근거는animation-full-register-boundaries.md에있다.

**현재draw 재개를반복하지않는것과이후draw가object를다시읽는것은다르다.** 실제48980/489c2는여러draw를연속실행한다. 대기중변경한object/callback값은그다음draw에서합법적으로읽힐수있다. 검증기는전체호출동안prefix주소가다시나오지않는다는잘못된조건을두지말고현재복귀4a200까지의경계를구분해야한다.

## 상위 interpreter에 남은 조건

기존MS5A의script배열과CPU주소를대응시키되liveRAM script fetch는별도정책이필요하다. 한hostvector를RAM에서온것처럼이름붙여도live읽기를재현한것이아니다. 처음에는실제fixed48980/489c2의읽기범위를관측하고source기반리소스로보존한다. 실제caller의composition group과packedID가확정되지않은것을임의로그래픽리소스에바인딩하지않는다.

49fc6의다른opcode·callback·bankedlookup·sound대기와원본전체범위는계속목표에포함된다. 이draw계약은그완료조건을대체하지않는다.
