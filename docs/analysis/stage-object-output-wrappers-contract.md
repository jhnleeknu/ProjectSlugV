# 활성화 object 출력 wrapper 계약

canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 fixed CPU 주소=ROM 오프셋이다. 메인이16ea4..16ecc와47672..476ba의원본명령을직접읽었다. 기존cd58/3af8의전체register와pending API를재사용하되wrapper의진입부를대기마다반복하지않는다. 이문서는분석계약이며새wrapper의C++완료를뜻하지않는다.

## 16ea4 — object 좌표와 sprite 제출

1. A5=108000, D3=0(MOVEQ 전체32bit), D2.byte=BYTE(A6+53). D2의상위24bit는그대로다.
2. SWAP D0; D0.low+=WORD(A6+42) modulo65536; LSR.B1 D2의X를받아SUBX.W D3,D0. D3.low=0이므로원래object+53 bit0이1일때만D0.low를1더뺀다. ADD의carry를사용하는것이아니다.
3. 다시SWAP D0; D0.low+=WORD(A6+46) modulo65536; 두번째LSR.B1 D2의X로SUBX.W. 이번X는원래object+53 bit1이다. 완료후D2.byte는원래BYTE>>2이고상위24bit는보존된다.
4. D1=LONG(A6+12), D5.low=WORD(A6+1e)를읽어D5상위WORD를유지한다. D7은wrapper에서그대로다.
5. 원본은JSR이아닌JMP cd58이다. 기존full sprite submit의callback검사/clip/full/normal/deferred/pending을그대로이어받는다. 추가wrapper복귀stack을만들지않는다.

대기상태는기존13register/waiting에A5/A6를별도로보관한다. fresh에서만위전처리를실행한다. cd58에서captured cda4 wait가나오면A5=108000과동일상태를반환하고,재개는object+53/42/46/12/1e를다시읽거나A5를다시설정하지않고해당대기부터진행한다. 실제captured상태의A5=108000 제약을유지한다. caller가hold중object필드를변경했을때입력변환이반복되지않음을검증한다.

기존cd58은RAM9152 callback=cd50만지원한다. wrapper가clip될좌표여도실제callback은clip보다먼저호출되므로이제약을숨기거나생략하지않는다. 실제A6-relative BYTE/WORD/LONG접근과정렬만검사하며실패는전체RAM/상태/status를보존한다. 새ROM리소스를읽지않는wrapper다.

## 47672 — 상태 비교, sound 제출, raw WORD 조회

ca70이A0=A5−76a4로설정한다. D0.byte=BYTE(A0)를읽고BYTE(A6+7e)와비교한다. 다르면원본은A0 LONG을stack에저장하고D0.low=1ac0으로3af8을호출한뒤A0를복원한다. D0상위WORD/그밖scratch는sound의실제효과를유지한다. 같으면sound를호출하지않고saved A0도필요없다.

그뒤**live BYTE(A0)**를다시읽어BYTE(A6+7e)에쓴다. 이어**live WORD(A0)**를D1.low에읽는다. 이순서때문에A6+7e가A0또는A0+1과겹치면쓴결과를다음WORD읽기에반영한다. prefix에서읽은BYTE/WORD를cache하여재사용하면안된다.

D1.byte를ADD.B D1,D1로두배한다. signedBYTE overflow가나면D1.byte=80으로덮는다. 원래lowBYTE가40..bf이면overflow이고,그외에는2배의lowBYTE를유지한다. 이어D1.low&=00fe로상위BYTE를지운다. A0=4411e; WORD(A0+D1.W)를D1.low에읽고SUBQ.W1한다. 빌린자리carry1(원본WORD가0)이면MOVEQ0 D1으로전체32bit를지운다. 그외상위WORD는남는다. 마지막D1.byte를BYTE(A6+12)에쓴다.

raw index는모든짝수00..fe가가능하므로실제조회창은 `[4411e,4421e)`256byte이다. 이것을128개의논리적object/숫자표전체라고단정하지않는다. 후속packer는canonical hash·offset과이raw조회범위를pin한기존MS5D kind1/metadata를생성하고실제C++loader로읽게한다. 원본데이터는Git에넣지않는다.

사운드대기시기존SoundWordExecutionState와함께saved A0 및wrapper phase를유지한다. 재개는sound만이어가고완료후저장된A0를복원한뒤위live BYTE쓰기/WORD읽기로간다. object상태비교와sound제출을반복하지않는다. 현재full sound API의A5-relative주소제약에따라실제sound호출/재개는A5=108000이필요하다. sound를건너뛰는경로는actualcheckedA5-relative접근을허용한다. 이wrapper제약을임의A5 sound지원으로확대하지않는다.

두wrapper 모두같은nativeCPU를대기전/유지/해제에이어사용하고실제이전C++출력RAM/register/pending을다음호출에전달해검증한다. 원본callee를stub으로대체하거나원본자체를수정하지않는다. 자연IRQ/scheduler,임의callback,물리mirror/CCR전체는이helper연결의검증범위밖이다.
