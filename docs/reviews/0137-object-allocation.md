# 동적 오브젝트 할당과 실제 호출자 리뷰

Baseline `3a86a4c`. 원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인이28ae와4fb1a의원본명령을해석했고 sol에 C++/CLI/단위검사, 원본검증, 다음제거경로목록화를나눴다. 메인이 코어·CLI·단위시험·원본verifier·보고서와 문서를 검토했다.

## 구현 판단

CMP.W 이후BCC는unsigned request>=freecount 정상실패다. callback 검사는하위word만이아닌전체주소0검사다. 정상실패에서A0=100e98/carryfalse, RAM/D0/A1/A6보존을구현했다. 실패분기에서역참조하지않는포인터를강제로검증하지않는다.

성공은freehead pop/count감소/parent저장/depth계산/링크삽입/callback저장/inheritedbyte읽기를원본순서대로수행한다. 전역및오브젝트가겹쳐도live읽기를유지한다. 무조건필드를snapshot하면달라지는4개alias조건을원본과비교했다. signed연산과overflow미정의동작없이word wrap을구현한다. 사용포인터가RAM범위밖인원본동작은명시적으로지원하지않고오류로거부한다.

4fb1a는실제할당결과carry로parent+62를설정한다. 조건불충족의레지스터보존과fullCCR이아닌carry계약을구분한다. callback4fb64는저장만하며후속실행은별도다. 문서의불가능한'할당성공뒤parent범위오류'표현을고쳐, 정상할당실패뒤parent검증오류의transaction보존으로명확히했다.

## 검증

전체 `make -j3 all test` session3477 exit0. Python88개/C++전체통과,경고없음. 로그 `artifacts/object_allocation_build_test.log`.

최종 native verifier session71485 exit0. 전체RAM/fullD0A0A1A6/carry439조건과negative50조건통과. 원본SR.bit0과실제2908/2912분기를함께확인했으며wrapper우회는최종carryfalse를관측했다. 원본코드를패치하거나callee를우회하지않았고MMIO쓰기0/ROM불변을검사한다.

실제CLI출력RAM/레지스터를승계한3시퀀스를포함한다. 둘은3호출씩이며다른하나는원본2790 RAM과실제MS5I `init_objects` 결과를비교한뒤두번할당하여freecount80→79→78을확인했다. 다음callback/request는호스트가입력하며초기화의레지스터동등성을주장하지않는다.

보고서 SHA256 `9e6e6ad033a3683950fec1eeb40bdc66526b1b31f1c250e83b015c1c7e3abf6c`. 오류50조건에는원본의잘못된주소실행을포함하지않으며C++API/CLI거부와출력보존만검사한다.

## 다음 범위

299c/2a0a/2a84/c4cc의정적분석에서제거요청과실제free복귀가분리됨을확인했다. 비활성callback이더깊은다음노드를기다리고,마지막자식제거후이전비활성노드까지연쇄회수할수있다. 기존static restart를그대로linked삭제로쓸수없다. 근거와미확인범위는 `docs/analysis/object-removal.md`에기록했다. 이정적분석은동작검증이아니다. 자연부팅/스케줄러/후속callback/전체게임복원은진행중이다.
