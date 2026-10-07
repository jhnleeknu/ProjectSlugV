# 상태 소비와 팔레트 포트 연결 리뷰

대상: `c8a17fb` 이후 변경.

메인이f5a의분기·메모리순서및5728/7196의포트를분석하고 C++연결/단위검사를작성했다. gpt-6.1-sol / medium에CLI·빌드,원본반복비교,완전명령구간목록화를분리위임했다. 메인이실제소스/diff/보고서를리뷰했다.

상태소비는이전byte를먼저보관하고새D0 low byte를object+84에쓴다. 이전/새값의조합에따라video조회/설정,효과저장/설정·첫tick또는복구를실행한뒤ec4로가거나카운터를검사한다. 모든지원오류는후보RAM/포트만변경하므로전체출력을취소한다. 반면fee trap직전은원본의성공적인경계도달이므로그전에수행한상태/복구변경과포트를보존하여반환한다.

팔레트포트는단순변경boolean대신세old−new 상위byte차의OR값을watchdog에쓴다.578c..718b의완전구간은256개동일그룹이며D0가바뀌지않는다.7196의gate를통과하면준비전후각각2ffff2=1000,2ffff0=0을쓴다. helper4718/479e/4c40/504c에는추가MMIO가없다. optional vector는최대260항목을RAM변경전에예약하고성공시에만교체한다. 기존3인자API는동작을유지한다.

원본비교는호출자276조건(256독립+20승계)의전체RAM/경계와16,108포트,독립팔레트140조건의전체RAM과18,712포트를포함한다. 실제video query54/set108,효과저장/설정20,복구32,팔레트74/준비32,phase102,loop74/trap100을관찰했다. 고정ROM은불변이고팔레트뱅크는MMIO로사용한PVC tail밖이불변이다. MS5P전체를원본재추출결과와검증했다.

에이전트의최초오류fixture는pending gate가준비를건너뛰어미지원ID가사용되지않았다. 이를pending0으로고쳐실제늦은리소스실패가출력파일을보존함을2조건에서확인했다. C++동작을오류fixture에맞춰바꾸지않았다.

`make all test`는Python61개/C++전체통과했다. 단위검사는261개의video/watchdog/bank쓰기순서,restore후counter,trap시앞선변경확정,lateerror rollback,팔레트포트보존을확인한다. CLI숫자범위와모든입출력별칭검사통과. 로그: `artifacts/control_caller_build_test.log`. 보고서SHA256: `7e2cc2b35b657d8baf55358b3f3b0ff837742364e06d022584ef8bdd560e427a`.

f54의9136호출을포함한단일진입,ec4대기·실제입력/인터럽트,trap handler,CPU레지스터/flags와장치시간축은아직미완료다. 출력목록은순서있는장치쓰기이며RAM/포트사이의매cycle관측을모델링하지않는다. 전체목표는active다.
