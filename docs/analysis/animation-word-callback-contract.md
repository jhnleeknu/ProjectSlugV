# Animation3c WORD callback 계약

Baseline `cc5750b`. canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 CPU4a30c..4a382는 같은 ROM 파일 오프셋이다. 메인이 원본 명령을 확인한 정적 계약이며, 실행 관측·구현 완료는 별도 검증해야 한다.

3c의4a30c는 outer A0 LONG을 저장하고 padding1 BYTE를 읽지 않고 건너뛴다. 4a312 WORD→D0.low는 기존 high16을 유지한다. ADD.W 두 번으로 wrap한 signed WORD 변위를4a500에 더해 LONG target→D7을 읽는다. 두 번째 WORD→D0.low, ADD.W 한 번,A0=4a76c로 설정한 뒤 A0+signedD0.low의WORD→D1.low를 읽는다(D1.high 유지). A2는 이 prefix에서 바뀌지 않는다. operand LONG→A0를 읽고 post-operand A1 LONG을 저장한다. A1=D7, D0=A0(전체LONG) 후 bank shadow WORD를 저장하고 bank0/PVC를 설정하여 실제 callback을 호출한다.

4a354..4a37e는 기존 callback14 복귀와 같은 효과다: saved bank WORD 복원, callee D0/D7 WORD를 임시보관, bank 재독출과 PVC 계산, MOVEM.W D0/D7의 signed16→32 복원, A1/A0 LONG 복원,4a276의D6/script pointer 저장. 이는 direct30의 복귀와 다르다.

## 구현 계약

- 기존 API/state/CLI 인자·JSON·리소스 규격을 재사용한다. 3c는새phase를만들지않는다. callback47672가sound대기하면기존phase2를사용한다. pending 이후 필요한정보는기존saved_a0/a1/bank 및callback metadata에모두있다.
- 초기 연결 대상은 이미 의미 복원한 실제target2b3e8/2b3fa/47672다. 3c는 WORD selector alias가 있으므로 실제 읽은 target으로 이 세 callee를 구분한다. selector 숫자1d/1e/1f만으로제한하지않는다. 다른target은 checked 미지원이며 완전한3c완료를주장하지않는다. 기존14의지원범위와오류거부는유지한다.
- 2b3e8/2b3fa는기존callee효과그대로사용하며D1을변경하지않아3c의두번째lookup결과가최종register에남는다. 47672는기존ObjectSoundLookupState를사용한다. 기존nonexternal API는47672를거부하며2b3e8/2b3fa는허용한다.
- 첫selector WORD의16bit 두배wrap/signedLONGlookup, 둘째WORD의16bit 두배wrap/signedWORDlookup을보존한다. 둘째lookup은callee가D1을덮어써도먼저실제읽고오류를처리한다. prefix의A0, D0와D1효과도callback진입상태에반영한다.
- whole-invocation RAM/state/carry/PVC/external_reads rollback과기존phase2hold의prefix미독출을유지한다. callee지원A5제약은기존정의를따른다.

## 리소스와 정적 범위

첫 WORD selector의고유16384 LONG slot은[42500,52500)이고각slot은4개selector가공유한다. 둘째 WORD lookup은[4276c,5276c). 기존control_04276c.ms5d는둘째전체와첫범위대부분을보존하지만[42500,4276c)의620BYTE가없다. 기존리소스를변경하지않고비중복prefix MS5D v1 kind1을추가하는방식을우선한다. 실제knowncallee경로의필요범위·전체alias는별도목록도구로검증한다. rawslot을호출가능한함수목록으로취급하지않는다.

## 다음 관측

원본whole49fc6의3c prefix/callee/복귀를수정없는ROM으로실행한다. 1d/1e 및WORD wrap aliases, 둘째lookup의WORD경계·부호·wrap, D1.high보존, operand liveRAM/fixed, callback1f high/low/high→low대기와poison을비교한다. 최초entry A7=S일때outer A0=S-4,A1=S-8,bankWORD=S-10,JSR return4a354=S-14. 47672 내부 A0 및3af8 return4768e 저장 후 highwait는S-28/lowwaitS-22가정이며실제스택관측으로검증한다. 자연게임도달성/나머지callback/40/전체Goal은미완료다.


## 실제 RTS callback 추가 근거

메인이 dispatch4a50c의 LONG=0003679e와 ROM03679e의4e75(RTS)를 확인했다. 따라서 실제target03679e도 지원한다(14의selector03 및3c의해당target aliases). 이는 다른 미지원 callback을 no-op으로 간주하는 것이 아니다. 이 callee는 레지스터를 그대로 반환하므로3c에서 준비한 D0=operand LONG과 D1 lookup 결과, wrapper의MOVEM.W sign확장을 직접 검증할 수 있다. 지원 여부는 원본2BYTE와 실제읽은target을 근거로 한다. 첫prefix 크기는0x26c=620BYTE이며 앞선624 계산을 정정했다.

## 경계 operand 리소스

독립 원본 fixture는1d/1e의 BYTE index 경계를 위해 operand0 및ffc00도 사용한다. 각각 전체 BYTE-domain LONG 범위[0,400),[ffc00,100000)를 기존 MS5D v1 kind1로 포장하고 원본 위치·해시·lookup 역할을 기록한다. 이들은 실제 게임의 논리적 표나 자연 script 참조가 확인됐다는 뜻이 아니다. [0,80)의 vector 선택은 현재 관측기가 canonical cartridge ROM view로 제공하며 BIOS/cart 선택 장치 상태를 검증하지 않는다. 이 한계를 C++ 비교에도 유지한다. 기존 operand6431a 범위는 기존 리소스를 재사용한다.
