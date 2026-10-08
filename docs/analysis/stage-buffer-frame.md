# Stage buffer frame 4aa88 후속 분석 계약

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소는 fixed 첫1MiB이므로 CPU=ROM offset이다. RAM은CPU100000..10ffff, A5=108000이다. 메인이 원본4aa88..4abc0 및4b784..4b82e를 직접 읽은 계약이다. 구현·실행 비교가 완료됐다는 뜻은 아니다.

## 4aa88 정상 처리

Debug 검사 이후4aafe에서D7=0,A0=LONG RAMdc88을읽는다.16개의WORD에대해각각LSR.W (A0)+를실행한다. 최종A0가unsigned10dc88이상이면A0=10db88로설정하고LONGdc88=A0를쓴다. 주소범위를논리ring내로강제하지말고실제16개의순차read/write와그뒤비교순서를구분한다.

BYTEdb85를db84로복사하고db85=0; BYTEdb87을db86으로복사하고db87=0. BYTEf001.bit0이켜져있고(BYTE4cab|BYTE4cb1)&80이비영이면db84=ff다. 이때D0.byte의중간변화는뒤의MOVEQ로덮인다.

A4=10d746,A3=10d918을설정하고BYTEd744.bit7을토글한다. **이전bit가0일때** A3/A4를교환한다. D1=ffffffff를설정한후WORD(A4+1d0)=0. 그후D0..D7을각각0으로만들고A4+=d0(hex208). MOVEM.L D0-D7,-(A4)를6회, D0-D3,-(A4)를1회실행해총208byte를뒤에서앞으로지운다. 최종A4는선택한버퍼시작이고A3는다른버퍼시작이다. A0는ring진행후주소, A1/A2는debug가없으면보존한다. A6는정상처리에서바뀌지않는다.

## 앞선 debug16-slot 처리

BYTE10f001.bit7이켜지면원래A6를stack에보존한다. A4=10daf8,D7=0으로시작해각8byte slot의LONG(A4)를A6, LONG(A4+4)를A0로읽는다. A6/A0중하나가0이면skip. 비영이면D6.byte=BYTE(A6+6d)&0f이며D7.byte와같을때만호출한다.

호출전A4 LONG/D7 WORD를보존하고A0+=4,D7=0000122b로4b784를호출한다. 반환후D7는**하위WORD만복원**하고A4를복원한다. WORD RAM0010=0, WORD port2ffff2=1000, WORD port2ffff0=0을순서대로쓴다. D7.low+=1,A4+=8 후unsignedA4<10db78이면반복한다.16slot종료후원래A6를복원하고4aafe로간다. Debug내에서발생한A1/A2반환효과는정상경로가덮지않는한남는다.

## 4b784 두 sprite 제출

D1=ffff0000. BYTE(A6+15).bit2가켜지면D1.low=4. LONG(A0)+를D0로읽는다. 같은flag.bit0이켜지면D0상위WORD를NEG하고D1.bit0설정, bit1이켜지면D0하위WORD를NEG하고D1.bit1설정한다. SWAP/ADD.W(A6+42)/SWAP/ADD.W(A6+46)으로좌표를더한다.

D0/D1/D7/A0의LONG을stack에보존하고D5=ffffffff,cd58을호출한다. 반환후A0/D7/D1/D0를역순복원한다. 이어WORD(A0)+를D2.low,다음WORD(A0)+를D3.low로읽는다. D1.low ^=3. Objectflag.bit0이면D2.low NEG,bit1이면D3.low NEG. D0상위WORD에D2.low,하위WORD에D3.low를더한다.

이번에는A0 LONG만보존하고D5=ffffffff,cd58을두번째호출한다. A0를복원한뒤WORD RAM0010=0, WORD port2ffff2=1000, WORD port2ffff0=0을쓰고RTS한다. 다른register는두번째sprite제출결과대로남는다. D1.bit6은이구성에서켜지지않는다.

둘중어느sprite에서도대기할수있으므로각호출지점의stack보존값과상위slotloop복귀상태를유지해야한다. 첫대기재개뒤두번째좌표WORD를읽는것은live읽기이며미리캐시하면원본과달라질수있다. 기존sprite실행API를재사용하되단계별저장상태가필요하다. MMIO가있으므로원본검증은기존port지원oracle방식을검토해야한다. 아직이unit의fixture·리소스주소범위·banked지원계약은확정하지않았다.
