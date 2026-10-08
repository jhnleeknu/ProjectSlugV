# Animation 전체 상태 API의 첫 연결 계약

이 계약은원본49fc6과실제48980/489c2 scripts의00/04/08/28 경로를전체register/ports/pending으로먼저연결한다. 전체17opcode복원목표는유지하며다른opcode를완료로간주하지않는다. 기존RAM/carry API를삭제하거나기존지원범위를축소하지않고새API를추가한다. 원본주소와hash는animation-draw-full-contract.md를따른다.

## 상태와 외부 계약

`AnimationExecutionState`는기존 `SpriteSubmitExecutionState sprite`, 별도uint32 `a5/a6`, unsigned `phase`, uint32 `saved_a0/saved_a1`, uint16 `saved_bank`를갖는다. sprite.registers가D0..D7/A0..A4의유일한상태다. phase0은fresh/반환완료이며sprite.waiting=false,저장필드0이다. phase1은직접opcode04의cd58대기이며sprite.waiting=true이고저장필드는원본stack에서캡처한값이다. 향후indexed draw/sound/callback재개는명시적인상태확장이필요하다.

예정API는 `step_animation_execution(ram, scripts, state, carry, ports, error)`다. scripts는기존MS5A의 `vector<AnimationResource>`이며새파일형식을만들지않는다. 정확한64KiB RAM,도달한BYTE/정렬WORD/LONG주소를검사한다. 고정script읽기는CPU=ROM<100000인유일한완전한window에서읽고liveRAM주소는실제현재RAM에서읽는다. script가RAM주소일때별도hostvector를읽는이전API의방식을복사하지않는다. 미실행리소스를미리요구하지않는다.

새지원경로의모든RAM/register/pending/carry/ports는한transaction이다. 오류는모두보존하고,성공한대기는현재까지효과를commit한다. 대기에는반환CCR이없으므로carry bool입력을보존하고CLI에서는null로표시한다. RTS완료때만실제carry를제공한다. ports는이번호출의ordered writes로교체한다. 실행cap은checked오류로표현하며정상완료로바꾸지않는다.

## Fresh49fc6 및 반환

A0=A6+26. WORD(A5-7ff0)=0 후WORD1000→2ffff2,WORD0→2ffff0. D7=LONG(A0).0이면carry1로즉시완료하고더이상script/object+17을읽지않는다.0이아니면A1=D7, BYTE(A5+5742)=0. BYTE(A6+17)가signed양수일때만1을뺀다.

dispatch마다D7전체=0, D7.byte=BYTE(A1), A1++를수행한다. 지원opcode를실행하고다음dispatch또는아래epilogue로간다. epilogue는bankshadow0쓰기와PVC2WORD를다시 출력하고, ASR.W1 D7의이동전bit0을 carry로반환한다. D7상위WORD는보존되고하위WORD는산술오른쪽이동된다.

## 00 wait

D7전체=0. BYTE(A5+5742)를modulo256으로1증가. D1.byte=BYTE(A1++).

- duration0: D6.byte=BYTE(A0+4). 이BYTE가음수면WORD(A0+4)=0, D7=LONG(A0), A1=D7후dispatch. 음수가아니면바로epilogue. D6상위24bit를보존하고statepointer를갱신하지않는다.
- duration이 0이 아님: D6.low=WORD(A0+4). signedD6.low<=0이면BYTE(A0+4)에D1.byte를더한다. 여기서BYTE는timer의상위BYTE다.
- 그이전D6.low>=0이면D0.low=WORD(A0+6), WORD(A0+4)-=D0.low. 이읽기/쓰기와D0상위WORD보존을유지한다.
- live WORD(A0+4)>0이면D5=LONG(A0), A1=D5. 이후현재BYTE(A1)==28이면다시D5=LONG(A0), A1=D5, D7전체=ffffffff.
- 처음읽은D6.low<0이면dispatch로간다. 그외D6=A1전체32bit, LONG(A0)=D6후epilogue.

앞서저장한timer/pointer값으로live읽기를대체하지않는다. 원본alias순서가있으며BYTE증가와WORD감소의결합을밀리초나프레임duration같은추정의미로바꾸지않는다.

## 28 terminal / 08 jump

28: live WORD(A0+4)가음수면WORD를0으로, D7=LONG(A0), A1=D7후dispatch. 음수가아니면BYTE(A0+4)=0, D7전체=ffffffff후epilogue. opcode28뒤operand를읽지않는다.

08: A1을1증가시켜 skipped BYTE를건너뛴다. D7=LONG(A1), A1=D7. D6=A1, LONG(A0)=D6을저장하고dispatch한다. 분기대상과statepointer가겹칠때cache로live읽기순서를숨기지않는다.

## 04 draw와 캡처 상태 재개

animation-draw-full-contract.md의전체명령효과를구현한다. skip도operand7byte를읽고변경된register/A1을유지하여다음dispatch로돌아간다. submit에진입하는경우에만기존callee의제약으로A5=108000이필요하다. skip/null/wait/terminal에이제약을추가하지않는다.

A0/A1/bank저장, shadow0과PVC, cd58, bank복원과PVC, MOVEM.W로D0/D7부호확장, A0/A1복원을순서대로수행한다. phase1재개는cd58 pending만실행하고완료후이복귀열을거쳐다음dispatch로돌아간다. 대기중object가변해도현재draw전처리를반복하지않지만후속draw는새live값을읽을수있다.

초기지원밖opcode, 임의callback, banked script/data, 다른resume종류는checked실패로명시한다. 이들미구현을Goal에서제외하지않는다. 실제전체17opcode분류는animation-full-api-reuse.md에남긴다.
