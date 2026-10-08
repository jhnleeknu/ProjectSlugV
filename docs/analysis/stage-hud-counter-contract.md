# 4e286 HUD 출력의 연결 계약 초안

canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 주소는 fixed CPU=ROM offset이다. 메인이4e286..4e330,8cda..8d32,35f0..3628의원본명령을읽었다. 다음구현을위한정적근거이며전체4e286 native/C++완료증거는아니다.

## 분기와 대기 재개

BYTE(A5+5d1f)=0이면호출자상태를그대로보존하고RTS한다. unsignedD0.low>99ff이면D0.low=7243,D1.low=c904,D2=4,D3=2로설정하여35f0으로tail jump한다. 이경로는8cda나sound를호출하지않는다.

그외D2=MOVEQ0. D0.low>=0a00이면BYTE(A5+5d20)=0을쓴뒤팔레트호출로간다. 미만이면해당byte를1감소시키며,이전0일때borrow가발생한다. 이경로는D0.low를stack에보관한뒤D0.low=1ac3으로3af8을호출한다. 사운드가대기하면저장한WORD와복귀phase를유지해야한다. 복귀후에만counterbyte=1f를쓰고D0.low를복원한다. D0의상위WORD나다른scratch레지스터가3af8에의해변한효과를지우면안된다.

낮은값경로는D0.byte를D2.byte로복사,LSL.B3,carry이면NOT.B,LSR.B3으로계수를구한다. D2는앞서0으로초기화되지만soundcall의전체레지스터효과를확인해야하며최종BYTE연산만으로상위24bit를임의초기화하지않는다. 높은값경로와낮은값경로모두D0.low저장→MOVEQ12 D0→D1.low=0a0d→8cda→D0.low복원을수행한다. 팔레트helper는A1/A2와D0/D2를변경하므로RAM전용API로대체하지않는다.

## nibble 조회와 리소스 범위

복원한D0.low를8bit우측이동한WORD를stack에보관한다. 다시4bit우측이동하고2배하여4e272의WORD표를읽는다. SWAP D0 뒤D0.low=7243,D2=D3=2로35f0을호출한다. 저장한WORD를D0.low로복원하고low nibble만남겨2배한offset으로다시같은표를읽는다. D0.low=7283,D2=D3=2로35f0 tail call한다.

4e272의명목상digit표는10 WORD(20byte) 뒤4e286 코드가시작한다. 그러나입력은일반WORD이고원본의검사는unsigned<=99ff뿐이다. 예를들어0x0a00..0x0f00은이경로를통과하여낮은자리index10..15로 **코드바이트를WORD데이터로읽는다**. 실제지원읽기창은[4e272,4e292)32byte이며이를명목표10개로축소하거나비BCD 입력을0으로정규화하면안된다.최대index15는4e290의WORD를읽는다. 이범위는논리적표의길이가아닌이루틴의관찰가능한rawlookup span이다. 기존MS5D v1kind1로원본바이트를보존하고C++loader가읽도록한다.

SWAP이D0상위WORD에첫자리index의2배를남긴다. 첫35f0후stackWORD복원과low nibble연산은상위WORD를보존하므로최종D0high를임의0으로만들면안된다. 두출력사이의상태와순서있는ports를유지하며8cda+첫출력+둘째출력중늦은실패는호출의상태전체를보존하는checked계약으로처리한다. 대기성공과실패의transaction정책은기존sound/frameAPI와맞춘다.

## 필요한 검증

참조flag0,99ff/9a00,09ff/0a00,모든nibble조합(비BCD포함),counterbyte0/1/ff,팔레트slot12 참조0/비영과target/weight/dirty분기,3af8 high/low 제출과실제대기재개를원본과비교한다. sound후저장WORD만복원되는동작과A5상대RAM alias도확인한다. 원본바이트·전체RAM·15register·ports·외부read·pending복귀를비교하기전완료로취급하지않는다.
