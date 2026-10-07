# 게임 초기화 접두부와 후속 리셋 묶음 리뷰

Baseline `a4b2dfd`. 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인이 원본47570 접두부와3af8/3d3a/3ac8, 그리고9개리셋함수의중첩호출까지직접해석했다. sol에접두부코어·CLI·단위검사, 원본/IRQ검증, 리셋묶음구현·검증을분담했다. 메인이전체코드와최종보고서를검토했다.

## 판단과 구현

공통wait PC3aea만으로는복귀할호출자를구분할수없다. word overflow와08/20 byte단계를명시하고word 내부high/low pending도유지한다. 실제D0는word0720의상위byte07을유지한채하위byte만바뀐다. D1.high/D3보존및captured byte next를반영했다. 단계가끝난뒤에만다음명령을enqueue하며재개는prefix를다시실행하지않는다.

conditionald00046 읽기는최초word enqueue에서만발생하고호출당external_reads로반환한다. 'MMIO 없음'이라는초기header표현은읽기를제외하지않도록'MMIO 쓰기 없음'으로고쳤다. RAM/state/read count는후속실패까지함께롤백한다. 원본포인터e89e4는저장만하며아직dereference하지않는다.

리셋API는확인된9개진입주소만받는다. 필드사이의gap을보존하고4aa30의전체register clear,2ef90의D0=1,그외보존을반영했다. 모든오류검사는변경전에끝나므로불필요한64KiB복사없이실패시보존한다.9개를전체47570과혼동하지않으며생략된호출은문서에명시했다.

## 검증

전체 `make -j3 all test` session58783 exit0. Python81개와C++전체통과,경고없음. 로그 `artifacts/game_prelude_reset_build_test.log`. 이후에는Python원본검증과문서만보완했으며C++변경은없다.

최종prefix verifier session16636 exit0.171경계(wordwait42/byte08wait38/byte20wait20/done71), conditional읽기16회, 오류47조건. 원본stack으로단계를독립적으로추출한다.12시퀀스는실제IRQ37회/포트68개로대기를풀고CLI RAM/전체레지스터/pending을승계한다. 호스트sound head수정은없다.

메인리뷰에서새경계의실제연결을요청하여game_startup→원본c584 JSR→47570 두조건을추가했다. 원본stack에c58a가저장되는것을확인하고실제CLI 반환을넘겼다. 한조건은완료,다른조건은가득찬byte링에서08대기다. 추가startup watchdog4포트도일치했다. 보고서SHA256 `24e42600a631bc346165547a417fe3aa9c8dab9f2bc039697c952525c918af05`.

리셋verifier288조건(독립144+16승계시퀀스144호출), 오류17조건통과. 전체RAM/fullD0D1D3, MMIO쓰기없음, 원본불변을검사한다. 보고서SHA256 `3188b37509467d265d390a56e74720662b928a890fe0904219cf19d3277f30d3`. 메인이두보고서의집계와해시를확인했다.

## 남은 범위

IRQ context복원은호스트가하며자연부팅/BIOS/SR/RTE/물리시간은미완료다. 다음은475a4 suffix의미복원1bcfe/1bd12 오브젝트경로와481de/4d81c 레코드처리및필요런타임리소스를복원한뒤확인된리셋함수들을원본순서로연결하는작업이다. 전체게임실행완료를주장하지않는다.
