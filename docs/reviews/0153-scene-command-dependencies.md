# 장면 이동 초기화·간접 참조·경로 지정 리뷰

Baseline `e495c44`. 이전 goal turn은 scene handler 구현과 원본 검증을 커밋한 progress다. 이번 작업은 그 명령 실행 API에00/10/24를 연결한다. 메인이 원본 제어 흐름·레지스터 폭·리소스 계약을 확정하고, sol 세 작업에 구현/검증/추출·문서를 분담했다.

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 명시한 코드·table·path는 고정 첫1MiB의 CPU 주소=ROM offset이며 RAM pointer는 CPU 주소로 별도 구분한다. 원본 변경 없음.

## 원본 의미와 구현 검토

00은1a174에서 operand X/Y와 A2를 읽고19772→197da를 호출한다. 초기 word X/Y와16.16 long을 각각 보존한다. 비영 path의 첫 record+2 type을18c06의4-byte jump table로 판별한다. Type00..54는carry1,58..8c는carry0이다. 이에 따라 first+6 word를d3ba 또는d3b8 word에,first+8 word를d3c0 또는d3bc의 **상위word**에 더한다. LONG 전체 덧셈이나 소수부 덧셈으로 바꾸지 않았다. 모두16비트 wrap이다.

19772는 negated X와01000000-Y로 고정node10d38e에43e22를 호출한다.16fee가 아니므로 node2c를 지우지 않는다. 이전world X/Y와 D4/D5 scratch 및 D6 보존을 반영한다.197da는10바이트 stride로 record+2==ffff를 찾고 terminal 첫word-1을 D7.word에 둔다. Null은7fff이며 앞선 node helper가 D7 전체0을 만들었으므로 최종상위word도0이다. d41e/d420에 결과를 저장하고 A1은script다음명령으로 복구한다. A2는pathpointer를 반환한다.

10은1a10c에서 operand pointer가 가리키는4바이트를 읽어e89fa에 넘긴다. 값0은e89ec로 대체한 뒤RAMde2a에 저장한다.24는1a230에서 selector와A2를 읽고1a09e의고정table1a0a6에서목적RAM주소를선택한뒤19e60으로long을저장한다. A2 target을 dereference하거나 후속path를실행하지 않는다.

API는D0..D7/A0/A1/A2를 입력·출력한다. 기존optional dependency없는API호출은유지하며새vector는호출동안borrowed다. MS5D의정확한source주소/길이/끝과필요한RAMspan을검사한다. 오류는RAM/state/ports전체를보존한다. CLI는필요한dependency만기존fixedloader로읽고파일alias를검사한다.

## 추출 리뷰와 발견 사항

37 motion span,1간접word,1 path-node table을기존MS5D로추가했다. 합계39파일1248payloadbytes이며기존41script bytes는유지한다. Motion은108일반record와37개의4-byte terminalprefix1228바이트다. 경로의전체동작은아직미해석이다.

초기packer가첫word(time)을type으로검사한오류를메인리뷰에서발견했다. 원본18c06은2(A1)을읽으므로offset2로수정했다. 실제firsttype은14/64/80이다. time1/type14허용및time0/type90거부등회귀를추가해잘못된field가다시검증기준이되지않게했다. Raw resource bytes는변경없고metadata와검사가교정됐다.

최종manifest SHA256 `9b6dcb8156fdd8a6cd368b8afe79f86b2b6908d0efc85d3f0d53b1d79c6dafed`. Native verifier는39개리소스를canonical ROM과직접대조하며firsttype도원본+2에서읽는다.

## 검증

`tools/verify_scene_command.py`의 원본3945조건/오류83조건/18720순서있는ports가통과했다. Canonical지원698회×4profile=2792조건과CLI run 검사698회(이 중 길이2이상79개run의696회와singleton2회),기존slot260/video195조건을포함한다. 지원run79개에서실제CLI출력RAM과11레지스터를다음명령으로넘겼다. 고정ROM불변및A7반환도확인했다.

추가13개dependency오류검사는00/10/24각각directory생략·파일누락·malformed·CRC-valid주소불일치와dependency/output alias를포함한다. 임시복사파일만사용하며원본리소스를변경하지않았다. 잘못된입력이출력파일을보존하는지확인했다. 메인은검증스크립트와최종보고서를직접검토했다.

최종보고서 SHA256 `a69e2b5b136e4db0c14245b7602c36ec0ccd03b5868ed864b894eb5b3cc0f6fb`. Binary SHA256 `5c690cca7abc017ed999574b95d57caffe45c3f44a067e3938ee68a3563c6982`. 전체make는Python134/C++99/경고0/exit0이며로그는 `artifacts/scene_command_build_test.log`다. 전 단계verifier와같은report경로를현행결과로갱신했다.

지원은18종이며canonical에는17종698회가존재한다.4c는canonical occurrence가없다. 미지원04/08의75/41회=116회를건너뛰어완료된것처럼취급하지않고명시적인API오류를유지한다. Canonical operand만 원본비교하며null path/비영 firstoffset/4c와인위적alias등은C++합성unit범위다. RAM fixture와standalone call context,지원명령간CLI승계를전체게임의자연실행과구분한다. 미지원04/08과1a26a phase loop,맵/경로의후속실행·자연scheduler·스테이지화면은아직미완료다.
