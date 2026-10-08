# 맵 전송·반복 경계의 공유 스택 계약

Baseline `6212b39`. 메인이 원본 명령과 기존 부분 API를 대조해 아래 순서·폭·호출 의미를 확정했다. 구현/원본 동등성 완료 보고와 구분한다.
Canonical SHA29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f; fixedCPU=offset. Raw /tmp/ms5-map-main-raw.txt redecoded directlycanonical.

Whole boundary48042→4804e: actualJSR1861a return48048, thenJSR17012 return4804e (17012ORI.B81,node+7a→17018RTS). Do not yet claim timer/8c16 continuation.
Leaf16f0e columns then183c6 transfer plus18702wrapped/1861arefresh needed. Existing13R scene_map_transfer.cpp uses local6WORD saved[], requiresactual16R/A7 bus rewrite rather thanadapter. MOVEM.W predec D0-D5 pushesD5,D4,D3,D2,D1,D0, atfinalSPascendingD0..D5; pop signextends32bits. Mustreadliveafter helper writes. Nested18742 and18424 stackslots independentlyaliasnode/descriptors/secondary RAM.

16f0e A2=node36 thenA1=node2e (ordering);D6.W=D2.W-1. D2.low0 yields65536 loops.16f1aCMPWORDwidth/BCC skippedcolumn; widthliveeachloop.16f2eCMPA.W#0 means full32A2zero;16f3eCMPA.W#ffff meansfullffffffff.16f36WORD21 or16f46BYTE0;no entirecell prevalidation. Recordbacktrack16f4e readsD7.W, zero branches16f5e;unsignedD0>=D7 branchesforward;elseSUBQ.WA2 actually fulladdressA2-=4 (addressarithmetic noCCR),repeat.16f62recordnextWORD signnegative stops;elseD0<D7stops;elseA2=A4repeat.16f72BYTErecord+3 thenWRITEA3+1 beforeBYTE node35 andBYTErecord+2 rereads.16f88 incrementsD0/D4.W thenDBRA;16f90/92 subtractinputD2.W;16f94publishesactualA2LONGnode36,16f98RTS. GroupZ/N writerbranches unless implementingflags; do not expose16f50/64 directly. Carry-only actualCMP successor may support ifexplicitneeded, not byassumingregisters suffice.

183c6 clippedtransfer allboundary arithmeticWORDwrap; C fromCMP/sub consumedactualbranch. Reject185f4 ANDI CCRfe→185f8RTS knownClear; accepted185ee ORICCR1→185f2RTS knownSet. Need actualbranch oracle forC(nativeSRneverread), directknownwriter terminal can classify sourcewithoutclaimingmeasurednativeflags. Pointerwidthreads arelive.
18424MOVEM.W then bank3 writesA5-7ff0=1,2ffff2=2000,2ffff0=0; readWORD(A1),LONG200004;shiftindexWORD,signedlookupA2,A2+=4;readheightA1+6 before slotnode26. Negative slot branches18530 beforeprimary loops (stillrootlookupdone). Primarynestedloops18496;SUBQ.W/BNE mustgroup16bitwriter+branch. Secondarybank2 writes thenWORD A1+2;zero185d2skip;elseLONG200010 plus signedindexlookupD7.L. ffffffff clearpath185a6;normal18568, signed columnrelativeWORD fetched via(A2)+ thenA4 +=D1.W, RAMcopyreadLONG(A4)+ beforeWRITE(A3,D0.W). Afterinner D6.W0, ADDa.WD6,A2 actualnoextra stride. LiveRAMsource/read-afterwrites; no secondarypredecode.
184d2..1852e zerofill video block exists but normal183c6 shownpath branches18530 directly and184ceBRA18530. Do not inventfallthrough or includeunreachablecore asnormal evidence. Can defer block unless actualcaller/directscopeidentified.
185d2 restoresbank2 evenaftersecondary, BSET7 node7a beforeexplicitcarrySET. RealA5 fullvalue used forshadow not constant100010. Watchdog/video portwrites instructionunits notphysicalcycles.

18702bit3/4 flags reread perphase, dimensionreadCMP thenDIVU live; unsignedD0.low>=dimension triggers ANDI.Lffff/DIVU.W (zeroexception);SWAP resultquotienthigh/remainderlow. Need preserve instruction reread ifalias? nointerveningwrites but bus readsstillordered. 1873e BSR16f0e;18742MOVEM.W then183c6call;1874a signextendpop;bit4path18758pushbeforeSUB.Wliveheight;18764pop;bit3clear18772RTS. bit3setD0-=livewidth then16f0e;1877cpush→transfer→18784pop;bit4setD1-=liveheight,lasttransferwithoutregisterrestore. Return actualcurrentC fromcallee orlaterwriters, notblanketUnknown forRTS/MOVEM.

Upper currentnode10d256 header480f2 (3c,0,14,10) fixed;node32=0,34=1f,x/y14/18=0,flags6,columnpointer0,slotfromprevious43ffcscene. Current palette upper fixtures have node26=ffff, explicitly initialized by their source fixture; futureupperfixture mustactualscene-preparedslot ordeclaredcontrolledinitialvalue, not hide missingdependency. Mainprior native prep e7bf4 no scene. Existingkind3 all8MB already covermap bank3 data; verifyactualreads notjustpresence.


## 구현·검증 규약

C++11의 현재 AnimationMachineContext/am_read/am_write/am_push/am_pop/am_call/am_return을 사용한다. 새 실행부는 16f0e..16f98,183c6..184ce,18530..185f8,1861a..18654,18702..1879a 및48042/48048/17012/17018이다.184d2..1852e와185fa wrapper,18656 moved-refresh는 실제 별도 caller를 분석·검증할 후속 항목으로 남긴다. 새 라우팅은 기존 helper를 가리지 않는다.4804e가 다음 실행 전 경계이며 타이머/직접 플레이 완료로 해석하지 않는다.

중간 체크포인트는 실제 앞선 block에서 도달하는 PC만 노출한다. Z/N을 소비하는 분기는 실제 flag writer와 함께 묶는다. 임의 Z-only 진입을 D레지스터 값으로 흉내 내지 않는다. C 전용 분기는 known C를 명시적으로 전달할 때만 별도 지원하며 그렇지 않으면 writer와 묶는다. MOVEM.W는 actual memory에 여섯 WORD를 순서대로 쓰고 이후 실제 stack WORD를 sign-extend해 pop한다. 메모리 변경 뒤 host local saved array로 복구하지 않는다. 리소스 전체·ring·node를 미리 선검사하지 않고 각 actual 접근에서 bus 검사를 수행한다.

새 C 보존 block은 전체 block의 원본 명령을 기준으로 분류한다. BTST+분기는 C를 보존한다.185ee는 Set,185f4는 Clear를 확정한다.185e8 BSET도 C를 보존하지만 앞선 일반 MOVE는 Unknown으로 처리된다. source 분류와 native C 관측을 구분하고 초기화 후 native SR을 읽지 않는다. 전체 clear/restore/return 뒤 측정 가능한 원본 branch successor가 없으면 carry 미관측으로 남긴다.

DIVU의 unsigned dividend는 선행 ANDI.Lffff 때문에 quotient overflow가 발생하지 않는다. 1871a/18738 직접 진입을 제공할 경우 고위WORD가 있는 임의 dividend의 원본 overflow 의미를 구현해야 하므로 기본은 ANDI부터 DIVU/SWAP까지 묶는다. divisor는 원본처럼 다시 읽는다. zero divisor는 원본 예외와 checked API 오류를 별도로 기록한다. 음수 BYTE/WORD ASR은 unsigned mask와 명시적 sign bit 확장으로 구현한다. ADDQ/SUBQ address는 명령의 .W 표기와 무관하게 전체주소를 바꾸며 C를 보존한다.

실제 upper 일반 경로는480f2 header(3c,0,14,10)와 valid allocated slot으로 bank3 primary map을 전송해야 한다. 이전47fe8 scene 및47ff2 palette 준비를 원본에서 실행한 후 fresh fixture로 선언하거나, 가능한 경우 그 시작부터 연속 실행·split/control을 비교한다. 준비 단계와 실제 관측 구간을 구분하고 예상 register/RAM 주입으로 결과를 맞추지 않는다. null/negative slot은 별도 경계 조건이지 일반 drawing 대체가 아니다.

bank3 CPU200004=physical300004의LONG200008, CPU2000f8=physical3000f8의LONG2a4e10이며 map payload physical3a4e10..3a5314는20×16/1284byte다. 기존 kind3 chunk300000과fixed chunk0에 포함되고 실제 C++ loader/bus를 사용한다. Bank2 secondary도 실제 현재 bank를 계산해 source byte를 대조한다. video LONG은 관측된 instruction port write이며 물리bus cycle/최종VRAM화면과 구분한다.

검증은 full64KiB RAM/16R/PC/liveA7/devicePVC-bank/orderedports/readcount/status와 실제 이전 출력 재개, fresh split/continuous, currentinput+artifact hashes를 포함한다. nested stack alias·live dimensions/flags/record operands·secondary source overlap·late guards와 rollback, sign extension, WORDwrap/DBRA0은 실제 의미를 시험한다. 기존100000 block 한도는 실제65536회 DBRA의 최소 두 block 반복도 처리하지 못한다. 반복 PC에서 공개 stop API로 임의 중간 회차를 선택할 수 없으므로, 메인은 유한한 한도를1000000 block으로 늘리기로 결정했다. 무제한 내부 loop로 한도를 우회하지 않는다. 폭0의65536 skip loop 전체 완료와 유한 budget 실패/rollback을 함께 검증하고 기존 budget 회귀도 재실행한다. Native의 별도 instruction CAP은 실제 명령 수에 맞게 명시하며 두 한도를 동일 단위라고 부르지 않는다. 다른 거대·비정상 실행의 한계는 기록하되 전체 Goal 완료 기준을 줄이지 않는다.
