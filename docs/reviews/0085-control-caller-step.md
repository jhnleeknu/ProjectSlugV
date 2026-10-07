# f54 단일 제어 진입 리뷰

대상: `cba98a5` 이후 변경.

메인이9136과f5a의연결,스택깊이·A6보존계약과트랜잭션범위를설계하고C++ API/단위검사를구현했다. gpt-6.1-sol / medium에CLI/Makefile,원본비교와후속입력경로목록화를분리위임했다. 메인이diff와verifier를리뷰했다.

9136에는entry_stack−4를전달한다. 반환된RAM과signed D0를uint32로보존하여소비API에넘긴다. BIOS전환이면f5a를실행하지않는다. 원본trap경계는정상적인경계결과로앞선변경을확정하고,지원오류는호출전RAM/result/ports를모두보존한다. 원본이호출자A6를유지하는지실제f5a hook에서검사했다.

원본f54의410조건(281독립+129승계)은전체64KiB RAM,104,487orderedports와next_pc가일치했다. f5a409회에서A6/A7보존확인. root950c정적재시작도A6가100f5c로보존됐다. root9532 BIOS경로는f5a가없었다. stagecallback깊이12/16/32는바깥반환주소를포함한다.2개연속시퀀스는area/group조작과전체종료·진행·재활성화를포함한다. 늦은palette실패2조건의출력보존도확인했다.

단위검사는9136활성화뒤실패해도전체변경을취소하는지,누름진행이효과복구/카운터로연결되는지,trap경계가앞선countdown변경을유지하는지확인한다. `make all test`는Python61개/C++전체통과. CLI숫자범위/별칭검사와 `git diff --check`도통과. 로그: `artifacts/control_caller_step_build_test.log`.

보고서SHA256: `dde81aaccb38533008098a252dcc09c0a9ba1db25306169004b6df691c509c24`.

입력byte는진단호스트가공급하며ec4대기루프를실행한것이아니다. 후속31d6/b68입력과c8c신호생산,외부CPU스택/전체레지스터/flags,장치시간축·예외handler·전체부팅은남아있다. 전체목표는active다.
