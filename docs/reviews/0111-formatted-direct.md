# 직접 문자 렌더러3650 리뷰

대상 기준 커밋: `027d4ca`.

메인이3650..366e의byte/word shift와swap,비디오long쓰기·word8200쓰기 및cursor20증가를확인했다. 기존3a70파서를공유하며renderer주소를상태에저장한다. 3650분기는font/lookahead를읽지않고style의낮은4비트와bits8..11만타일값에쓴다. 지원renderer는3650/e84c8 두개로제한하고실패시RAM/포트를보존한다.

- `make all test`: Python73개및C++전체검사통과,경고없음. 로그 `artifacts/formatted_direct_build_test.log`.
- 추가C++검사는emptyfont,@/highbyte의한바이트처리,cursor순환,style절단,renderer상태,미지원renderer/늦은포맷오류롤백을확인했다. 별도실행도통과했다.
- `.venv/bin/python tools/verify_formatted_direct.py`:487조건/10,426포트/오류13조건통과. 실제d56/df0진단4조건포함. 전체RAM/포트비교,font읽기0,원본첫1MiB불변을검증했다.
- 메인리뷰에서합성fixture를고정ROM리소스범위밖120000에배치한문제를발견했다. API범위를늘리지않고workRAM108000에옮겼으며잘린포맷은RAM끝에두어실제오류를검증했다.
- `.venv/bin/python tools/verify_formatted_text.py`:기본renderer289조건회귀통과. 로그 `artifacts/formatted_direct_default_regression.log`.
- 새보고서SHA256 `172b71a08e5a0c40c557e18dd827ca13e54272c2229e1b8bc2e995bbd72e2b2e`.

진단리소스의d56..e49창에는e40..e49코드10바이트가함께있음을명시했다. 이번에ec4조건분기와최종scratch레지스터전달까지복원한것은아니다. 메인루프연결과전체게임실행은계속진행한다.
