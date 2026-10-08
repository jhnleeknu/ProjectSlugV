# Stage block drawing 477a2/ddf9a/362a 정적 계약

canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소는 고정 CPU 주소와 동일 ROM 오프셋이다. 메인이477a2,ddf9a,362a..364e,35f0..3628을원본명령으로읽었다. 이는후속구현계약이며C++동등성완료증거가아니다.

477a2는D0.low=7162 후ddf9a로tail jump한다. ddf9a는A0=ddfa4를설정하고362a로tail jump한다.362a는반복해서WORD(A0)+를D1.low에읽으며ffff면그대로RTS한다. 아니면D0.low를stack에보존하고offset WORD를D0.low에더한다. D2/D3전체를0으로만들고다음WORD를D1.low,다음BYTE를D2.byte(width),다음BYTE를D3.byte(height)에읽는다. A0를stack에보존하고35f0을호출한뒤A0,D0.low를복원하고다음레코드로진행한다.

레코드는offset WORD,tile WORD,width BYTE,height BYTE의6byte이며ffff WORD가끝이다. 실제ddfa4..ddfdc는9레코드와sentinel,총56byte다. `artifacts/stage_activation_block_table.json`에원본필드/위치를보존했다. 새리소스는기존MS5D v1 kind1 raw window를사용하면되며PNG나렌더링결과를입력으로대체하지않는다.

35f0은A4=3c0000, D7.low=D0.low→SWAP D7→D7.low=D1.low로좌표/타일을묶는다. D6.low=D3.low로행수를설정하고각행에서unsigned D7<75000000인지확인한다. 이상이면TRAP15다. 정상시LONG D7을3c0000에쓰고D7전체에10000을더한뒤D7의BYTE에10을더한다. 마지막BYTE더하기는WORD/LONGcarry를전파하지않는다. D6.low를1빼서0일때까지반복한다. 열이끝나면D1.byte에1,D0.low에20을더하고D2.low를1빼서다음열을수행한다. 끝에WORD8200을3c0000에쓰고RTS한다.35a2처럼3c0004나watchdog쓰기와동일시하지않는다.

D0상위WORD와D1상위WORD는이경로에서보존된다. D6상위WORD도유지된다. 각레코드의D2/D3는MOVEQ0으로초기화되므로D2최종0,D3는마지막height다. D7은마지막열의마지막행후상태이고A4=3c0000이다. 마지막ffff읽기는D1.low를ffff로바꾸고A0를sentinel뒤로옮긴다. D4/D5/A1..A3/A5/A6는보존한다. 빈stream은35f0을실행하지않으므로관련레지스터를임의초기화하지않는다.

실제477a2와ddfa4표의정적예상은137ports(128tile LONG+9WORDflush),A0=ddfdc,D0.low=7162,D1.low=ffff,D2=0,D3=4,D6.low=0,D7=72caff0b,A4=3c0000이다. 이숫자는원본CPU관찰로확인해야하며expected oracle을만드는대체알고리즘으로쓰지않는다.

잘못된width/height0은DBRA가아니라SUBQ/BNE의WORDwrap반복이며임의빈rectangle로처리하면안된다. 범위초과tile주소는원본TRAP15다. 새로운checkedAPI는지원밖TRAP/불완전stream/주소오류를transaction보존실패로처리하고그것을정상원본실행이라고주장하지않는다. 고유fixed window와live RAM의WORD정렬/범위를확인하며banked stream을근거없이일반화하지않는다.
