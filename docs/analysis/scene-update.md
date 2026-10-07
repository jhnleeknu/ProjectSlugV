# 전체 장면 갱신과 디버그 표시

원본 decrypted SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 코드 주소는 고정 첫1MiB CPU주소=ROM offset이다. 전체1a7a8은 기존좌표prefix(1a8ca직전)에1afda와네19e64를연결하고1a90e의RTS까지진행한다. 자연frame scheduler나일반scene초기화1a5a4와구분한다.

## 원본 호출 순서

1a8ca에서debug1afda를호출한다. 이후(A0 node,A1 metadata)는차례로(109156,10d356),(10b1d6,10d364),(10d256,10d372),(10d2d6,10d380)이며각각19e64를호출한다. 각helper의scratch와RAM변경은다음helper에승계된다. 이전12register좌표API에는A3가없으므로통합시A3를그대로보존해야한다.

## Debug1afda의 register 계약

진입시D7/D6을MOVEQ0으로지운다. RAM10f000 bit3 또는4가켜지면D7=ffffffff다. 둘다꺼졌으면D6.byte=이전RAM10d44e,10d44e=0이며이전값이0이면1b014 RTS한다. 비영이면caf0로tail jump한다. 기존reset API가반환하는RAM/ports/D0/D1/D3에추가해caf0와35a2의최종D2=0,D6=0,D7=75007000,A4=3c0000을승계한다. 다른address register는그대로다.

활성경로는D6=fff80000으로6world long을mask한다. 그후D6.byte에이전d44e를읽고d44e=ff를쓴다. 따라서no-draw경로의D6은fff800xx이다. 이전flag0이면즉시draw한다. 비영이면A0=109156, D0/D1=currentX/Y, D2=oldX-currentX, D3=oldY-currentY-borrow를계산한다. SUBX의stickyZ에따라D2와D3가모두0일때만다음검사로간다. 두번째LEA는A1=10b1d6으로바꾸지만뒤의좌표읽기는A0를그대로사용한다. 이것은원본명령상확인된중복검사다. 두번째node만움직인것으로draw를강제하지않는다.

Draw는D2.low39,D3.low31로시작한다. 매cell D4.low=(D2.low<<5)+D3.low+7000,SWAP D4,D4.low320,A1=1af12,A2=1afd2다. LIVE bit3이면A0=109156으로lookup하고D4.low!=320이면두번째lookup을생략한다. 320이며LIVE bit4이면A0=10b1d6으로lookup한다. D4 LONG을3c0000에쓴다. DBRA D2뒤각row마다D2.low39로재설정하며마지막row도예외가아니다. 최종D3.lowffff,D2.low39이고총40×32회다. D5/A3/A4는활성경로에서변경하지않는다.

## Lookup1b0e0

D0.low=((column*8-node14)&1f8)<<4, D1.low=((row*8+node18)&1f8)>>2, D0.low+=D1.low+80이다. Node+D0.word의cache WORD를D7.low에읽고ADDI.B58로lowbyte만변경한다. D6=MOVEQ0,D6.byte=D7.byte,ADD.W D6,D6으로lookup byteoffset을얻는다. D4.low=WORD(A1+D6.word). 320이면여기서복귀한다. 다르면D7.low&=c000후ROL.W3하여0/2/4/6을만들고WORD(A2+D7.word)를D4.low에OR한다. MOVE.W/B가보존하는상위부분을별도로유지해야한다.

추출리소스는기존MS5D512byte창1af12..1b112이다. 이창은주소가능lookup의보존범위이며일부코드와겹친다. 논리table의끝이나자연도달가능index를새로확정한것이아니다.

## 일반 초기화와 남은 경계

일반1a5a4는최초bank3선택뒤script/좌표/default를설정하고,1a26a→199d4/199ea→19938→전체1a7a8을phase목표까지반복한다. 전체update의연결만으로일반초기화루프나47a94이후stage진입을완료했다고간주하지않는다. 이후camera와네node의position 재초기화,조건부1a29e,1a414와bank2복귀까지별도통합이필요하다.

원본창 재생성: `.venv/bin/python tools/inventory_scene_update.py`. 명시한5개창336행을보존하며보고서 SHA256은 `22da103f76af8f7b0ee36e5cb19787cd86d952a90a08523fb891d54ddec24844`다. 모든행이decode되었다는사실만으로호출의의미나자연실행완료를판정하지않는다.

Canonical path72참조의metadata selector는0:11개,4:40개,8:21개이며현재목록에c는없다. 40개scene script에속한다. 전체update 검증에서path를임의의node에배치한fixture와원래selector/4에배치한fixture를구분해야한다. 특히세번째/네번째node는0x80간격이므로secondary cache를가진다른node의path를잘못대입하면다른node/metadata와겹칠수있다.

## C++ API와 재현

`update_scene_debug_registers`는기존SceneMapTransferState13register를반환하고기존3register `update_scene_debug`는wrapper로남는다. `update_scene`는명시debug table과borrowed raw MS5D windows를받아전체1a7a8을실행한다. 64KiB RAM·register·orderedports는모든helper가성공한뒤게시한다. 기존path/column/transfer의임시실행한계와resource범위오류는그대로적용된다.

```text
make -j3 all test
.venv/bin/python tools/inventory_scene_update.py
.venv/bin/python tools/observe_scene_update.py
.venv/bin/python tools/verify_scene_update.py
build/step_scene_update ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS extracted/runtime/scene_maps extracted/runtime/scene_secondary extracted/runtime/scene_debug.ms5d
```

ENTRY는1afda 또는1a7a8이며unsigned decimal/0xhex 형식이다. RAM은정확65536bytes,port는기존9byte big-endian레코드,stdout은entry/13regs/writes JSON이다. CLI는MS5D파일또는디렉터리를미리읽고정확1af12/512byte창한개를선택한다. Input/output/resource의path/inode alias를거부한다. 두출력파일의filesystem-wide atomicity를주장하지않는다.

## 원본 관찰 범위

원본1,417조건(1afda263,1a7a8 1,154)이모두RTS/A7+4로복귀했다. 총1,403,936 ports,호출내context reset없음,ROM/bank bytes불변이다. Native SHA256 `a04fd624e808e1f58f3c22d1ba5ead5fbdb4cb411bde008b20e4c2c14157e030`.

Debugflags/history216,table320fallback18,256mask×2profile512,추가parent/factor/debug128,원래selector에놓은72paths×4조건288,slot활성이나geometry-clipped72,visiblegeometry72,script별40group×2profile80,carrysequence구성31호출이다. 이중20호출은직전출력상태를승계한다. Host가history snapshot/debug bits를명시변경하며SR/stack은standalone호출진입마다설정한다. 자연시간축으로간주하지않는다.

Visible72는원본초기00좌표에서signed12bit metaX/Y를얻어worldX=-96-16*metaX,worldY=639-16*metaY의정수부로배치했다. Maskff,scroll0,parent0,velocity0,slot0/debugoff를사용한다. 원본실행중자료를보정하지않았고각case에서185f2성공과3c0000쓰기를확인했다. 이family에96,616ports가있다. 나머지극단좌표path조건에서맵이clip되는사실도보존한다.

최종C++전체1,417조건의RAM·13register·1,403,936 orderedports가원본과일치했다. CLI오류44조건은기존입력/출력파일을보존했고11sequence중20호출은실제직전CLI출력을승계했다. Report SHA256 `b9a0e96aa5e041411a578da4756e71cd716e8f96eb1452f5fe253ff1b87b58c5`, binary SHA256 `062b79fd12f7d16098ac7d845e07c0b7605bb28aa3d2a0a6a9c13de8e478e5c7`.

Verifier는smoke자료를거부하고현재build_cases의전체개수·순서·각fixture와native의RTS/A7+4를확인한다. 원본opcode24의72command rawbytes/selector/pointer도고정ROM과대조한다. 최종비교는이전positive결과를재사용하지않았다. 전체make Python170/C++107/경고0,기존초기화회귀576/오류24/672744ports/7sequence도통과했다. 전체CCR/자연frame/입력/스테이지화면은별도미완료범위다.


## 다음 일반 초기화에 필요한 배치 데이터

기존scene-script목록의opcode0c는18회이며18개비영포인터가모두고유하다. 메인이원본command WORD/operandLONG과현재manifest의41script+199dependency 범위를대조했으며18포인터의첫byte도이리소스들에포함되지않았다. 명령이RAMd40e에포인터를저장하는구현만으로그자료의실행까지완료한것이아니다.

원본1a414는d40e를A0에읽고null/ffff terminator/phase gate를검사한뒤1a470을호출하고새A0를게시한다. 1a470의뒤쪽1a4da..1a51a는28ae object할당,43e08 position설정,record+2의길이만큼inline WORD복사를포함한다. 첫pointer에서자료의전체extent를아직확정하지않았으며추출·정수폭·호출승계·실행비교가다음분석범위다.
