# 재개 가능한 c610 게임 초기화 통합 리뷰

Baseline `5f3d45e`. 원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인이c610..c652와3162/4823a의원본명령을해석했다. sol에core/CLI/unit/문서,전체원본검증,다음콜백목록화와독립검토를분담했다. 메인이최종코드·verifier·보고서를확인했다.

## 통합 계약

최초호출은f02a=1,seed49a1a,제거c4cc,화면caf0,전체47570을순서대로실행한다. 사운드대기에서는A6와nestedpending을유지하고재개시앞선seed/제거/화면을반복하지않는다. 47570반환후LIVEf02a.word&1을저장하고stage6/7및inputselector0/1을선택한다. 원본3162는ROM180.word=0인현재이미지에서D0.low=0,D1/D3보존이며이를기존RAM효과API와함께반영했다. 마지막에현재A6.callback=c654를설정하고RTSc652완료상태를반환한다.

outerphase0/1/2와innerphase를분리했다. 이미반환한상태,잘못된freshpending/대기PC를거부한다. innernext_pc475a4는마지막내부경계이고실제callerreturnPC가아니다. callbackc654는설정만하며본문실행은다음범위다. 실패는RAM/state/읽기수/포트전체를보존하고늦은inputresource오류도앞선변경을롤백한다.

## 리뷰에서 보완한 검증

초기wordwaitfixture는oldest를4d80에쓰고fd8d=0이어서word명령이필터돼byte대기만거쳤다. 메인과독립리뷰에서이를발견했다. 4d82=0455와fd8d=1로수정하고원본stack에서추출한phase/subphase를각label과대조하도록보완했다. 테스트이름만으로경로도달을주장하지않는다.

초기A6는sentinel100820만검사했다. 실제controller1008e4도fresh축에추가하고모든대기승계는1008e4로변경했다. fixture의실제28aechild할당부모도해당A6로맞췄다. core변경은필요하지않았다.

## 결과

최종native verifier session15698 exit0:144경계(48fresh+32개의3호출승계),오류38조건,순서있는포트166360개,외부읽기56회. 반환80경계와대기64경계를비교했다. 네종류wordhigh/wordlow/byte08/byte20은각16대기경계다. 실제2790/MS5I초기화와28ae추가노드,3ef2팔레트초기화를사용한다. 전체RAM/fullD0D1D3A6/pending/ports가일치하고원본은불변이다.

보고서SHA256 `eff31a72a6ac06645d6cb99f52b78a9103a10ff2a51810043073c468302fdd30`. 호스트는대기중head와f02a를명시적으로변경하며후자는0/1/2/ffff로LIVE선택을검증한다. 원본context/stack과실제CLI출력은승계한다. 재개포트0과앞선callee미재호출을검사한다.

전체 `make -j3 all test` session27682 exit0. Python88개와C++전체검사통과,경고없음. 로그 `artifacts/game_restart_build_test.log`. 이후수정은Python검증과문서이며C++변경없다. C++단위검사는fresh/resume의늦은inputresource오류시RAM/state/reads/ports보존과prefix재실행금지를확인한다.

## 남은 범위

이번대기해제는hostfixture이고IRQ·자연scheduler·물리시간·기타CPU레지스터/CCR/stack동등성은범위밖이다. 다음c654의정적오브젝트재시작및c66a의활성/replay판정,477e4스테이지콜백본문연결이남아있다. 다음후보목록은479b0에서끝나며전체콜백완료로취급하지않는다. 전체게임복원목표는계속진행중이다.
