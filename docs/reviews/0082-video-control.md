# 비디오 제어 조회·설정 리뷰

대상: `475ed76` 이후 변경.

메인이 원본3d7e/3db2의 word 감소,borrow 분기와byte 저장을 분석하고 C++ API 및 오류/경계 검사를 구현했다. gpt-6.1-sol / medium에 CLI·빌드 연결과 원본 대량 비교를 별도로 위임했다. 메인이 실제 diff,배치 framing과 verifier의 비교 범위를 검토했다.

조회는bit3이 켜지면0이며 그 외에는상위byte+1을word로 반환한다. 설정값0만byte0/bit3설정 경로이고 나머지는값−1의하위byte를저장한다. 따라서설정257의조회값은1이며ffff의조회값은255다. 다른low-byte bit를보존하고3c0006에word한개를쓴다. 메모리할당을RAM변경보다먼저수행하므로할당실패도출력을보존한다.

검증은원본코드를변경하지않고설정입력65,536개,shadow65,536개에경계값을순환적용한배치총131,072건을비교했다. 독립query sweep65,536건도실행했다. 원본전체RAM보존은모든경우확인하고,C++배치에서는조회전/후값·shadow·단일포트를비교한다. 배치가zeroRAM을사용하므로별도CLI194조건에서서로다른64KiB전체를비교했다. 모든입력과shadow의Cartesian전조합을검사했다는주장은하지않는다.

보고서SHA256: `10f00ea2352dd0b6354521e436b79b386c58b279e14415dfdd3ec99b5989654c`. 배치출력SHA256: `206ddb37ded7dca3367c45d8fa0aae8f92dc7da6a9db37b261485598178c3af1`.

`make all test`는Python61개와C++전체통과했다. CLI는uint16범위·출력별칭·정상64KiB/9byte출력·배치15byte framing과잘린입력거부를확인했다. API단위검사는bytewrap과RAM/result/포트보존을검사한다. 로그: `artifacts/video_control_build_test.log`.

원본setter의반환레지스터/flags,포트실제장치타이밍,화면scanline과전체게임실행은범위밖이다. ec4대기루프가같은3c0006을읽는다는사실은쓰기shadow를읽기결과로사용할근거가아니다. 호출자전체C++통합은다음단계이며전체목표는active다.
