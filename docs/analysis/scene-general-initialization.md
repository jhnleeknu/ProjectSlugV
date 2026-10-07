# 일반 장면 초기화 1a5a4의 연결 계약

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 CPU 주소는 ROM 파일 오프셋과 같고 A5=108000이다. 메인이 원본 1a5a4..1a73c와 아래 callee를 직접 대조한 후속 구현용 분석이다. 현재 `initialize_stage_scene`은 null-script 호출자477e4에 특화되어 있으므로 이 일반 계약의 구현 완료 근거로 사용할 수 없다.

## 초기 상태와 보존할 값

입력 A0는 script, D0.low는 목표 phase다. RAM10.word=1을 쓰고2ffff2.word=2000,2ffff0.word=0을 순서대로 출력한다. D0.low를d41c에 저장하고1a07a가 A0를d412에 저장하며d416.word=0으로 만든다. 이 일반 진입에서 D0 전체를 먼저0으로 바꾸면 안 된다.

1a5c2..1a620의 기본값은 원본 폭 그대로 적용한다. 특히d40c는WORD clear, d44e는BYTE clear다. 이어19768,1a29e,19b50,19dee,1a3c8 순서로 호출한다. A0=0으로1a40e를 호출해d40e=0을 저장한 뒤 node109156과10b1d6에17292를 각각 호출한다. Scene node와 script 실행에서 레지스터 결과를 계속 승계한다.

19768 자체는 A1=0,D0=D1=0을 설정하므로19796의비영motion 분기는 이 진입에서는 실행되지 않는다. Base/cursor/evaluated좌표를0으로 저장하고 D0=0,D1=01000000,A0=10d38e,A1=0으로43e22에 tail call한다.

1a29e는d422.LONG=0,197da 실행,d41e/d420 WORD=D7.low,d43e.word=0이다. 197da는A1=d3b4, null이면D7.low=7fff(상위WORD보존). 비영이면10byte씩 이동하여 type WORD가 정확ffff인record의startWORD-1을D7.low에 담는다. Terminalcursor는A1에남는다.

19b50는d3cc.byte=0, d3de/d3e2/d3fc/d400.LONG=0, d3ee/d3f0.word=0, d3d6.word=a0,d3d8.word=80,d3da/d3dc.word=0,d3e6/d3ea.LONG=60000으로놓는다. 19cee는d3ce/d3d0.word=7fff,d3d2/d3d4.word=8000이다. 이 함수는placement bounds인d3f2..d3f8을 초기화하지 않는다.

19dee는 네 node109156/10b1d6/10d256/10d2d6와metadata10d356/10d364/10d372/10d380에19e30을 순서대로 호출한다. Metadata+0.LONG과+4/+6/+8/+a.WORD를0으로 쓰고+c.BYTE=10을 쓴다. +d byte는보존한다. Node16fac 초기화 뒤 A1=0, D0/D1=camera local0/4로16fee에 tail call한다. 마지막 node까지 전체 공개 레지스터를 승계해야 한다.

1a3c8은d404/d406.WORD와d408.LONG을0으로 쓴다.

## 준비 phase 반복

1a65a에서1a26a script를 실행한다. 이어199d4는A1=d3b4, null이면D7=MOVEQ0, 비영이면D7.low=WORD(A1+a)를 읽는다.

D6.low=d41c로 놓고 unsigned D7.low와 비교한다. D7이 작으면199ea로마지막구간을검사한다. Nullcursor일 때 carry=1, 비영은1971c의 다음type WORD 음수여부다. Carry=1이면d41c.word=D7.low로 목표를 낮춘다. D7이 목표 이상이면D7.low=D6.low로 제한한다.

D6.low=d416을 읽고 unsigned D7.low>=D6.low이면D7.low=D6.low로 제한한다. D7.low를d418에 저장한 뒤 SWAP/CLR.W로16.16 시간으로 만들어19938을 호출한다. 결과D0/D1을d3bc/d3c0에저장하고 전체1a7a8을 호출한다. 전체update의debug와네path도 같은호출중연속실행한다.

업데이트 후 D7.low=d418로 다시읽는다. Unsigned d418<d41c이면1a65a로반복한다. 원본이진행하지않는입력에대해서는완료값을조작하지않고명시적실행한도오류가필요하다.

## 마지막 위치 정리와 배치

Camera10d38e의local0/4를D0/D1로읽고A1=0으로43e22를호출한다. 네node도각local0/4를읽어A1=0으로16fee를호출한다. 각node는직전호출의레지스터를승계한다.

D7.low=d41e를읽고 unsigned d41e<d41c이면1a29e를호출한다. 이어1a414 전체배치를실행한다. Script opcode0c가d40e를설정했을수있으므로초기값0을근거로배치를생략하면안된다.

마지막에RAM10.word=0,2ffff2.word=1000,2ffff0.word=0을순서대로쓰고1a73a RTS한다. Port목록은각callee의출력을호출순서대로연결해야한다. Native stack/CCR 전체노출과자연frame scheduling은별도계약이며, 현재조각들의시험통과만으로이일반호출완료를주장하지않는다.
