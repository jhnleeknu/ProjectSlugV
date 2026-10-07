# 호출자 카운터·단계 전환 리뷰

대상: `afc49ad` 이후 변경.

메인이fe2..1000과43dbc의명령·메모리순서를근거로API/단위검사를작성했다. gpt-6.1-sol / medium에CLI·Makefile와반복원본비교를파일별로위임하고실제diff/검증코드를메인이검토했다.

비교불일치는호스트오류가아닌원본trap15경계다. API는true를반환하되trap15=true이며RAM은불변이다. 정상경로는global word,object word,phase byte순으로쓴다. 메인이counter/phase가겹치는10d416주소의순서문제를확인하여별도검사에포함했다.00ff→0100저장후phase에의해objectword가0200으로바뀌는효과와다음호출의불일치를유지했다. 지원주소는짝수이며0x80byte범위가64KiB내에완전히있어야한다.

원본fe2부터실제43dbc까지또는fee명령직전까지1,734조건을비교했다. 독립1,716조건과3개의6호출RAM승계시퀀스다. 전체RAM일치,실제phase호출871회/trap경계863회,포트출력없음,원본mapped1MiB불변을확인했다. 모든256phase값,카운터경계와최저/최고object주소를포함한다. 잘못된주소·RAM크기·입출력별칭25조건에서출력을보존했다.

보고서SHA256: `7deacddda16f7717b17b375b421d65bd346239381bdd4b768d5f0d5f3e92dbf5`. `make all test`는Python61개와C++전체통과. 로그: `artifacts/control_counter_build_test.log`. `git diff --check`통과.

임의fixture주소의실제게임도달성을주장하지않는다. CPU레지스터/flags,외부스택,trap handler와메인루프동기화는범위밖이다. f5a상태소비/팔레트/비디오/카운터의최종호출순서통합은다음작업이며전체목표는active다.
