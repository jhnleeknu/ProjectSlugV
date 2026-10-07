# 장면 경로와 맵 참조 조사 리뷰

Baseline `0be8b81`. 이전goal turn은좌표prefix와12register node코어·회귀를통합한progress다. 이번에는뒤의19e64 및호출되는16ff8/1861a/18656/18702/16f0e/183c6의원본을메인이직접읽어경로명령과외부맵참조를분리했다. Canonical SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.

## 원본 근거와 범위

19e7e는WORD opcode를D7.low에읽고negative면RTS,그외8entry jump table로분기한다. Payload 길이는00/1c=4,04=12,08/0c/10/14=12,18=6bytes다. 조건명령의successor는sequential과opcode+10의LONGpointer이며양쪽을CFG후보로보존한다. 자연도달이나branch조건이참이라는증거는아니다.

실제scene opcode24의72참조는72고유root로이어지고218고유구문행(00:72,04:72,18:2,terminal:72)이있다. 오류·overlap·cycle은0이다. 72descriptor는primary69고유선택자,secondary nonzero40,column pointer모두0을포함한다. Canonical에없는다른명령을제외해최종엔진범위를줄이지않는다.

183c6은bank3를선택해CPU200004 root에서맵pointer를조회하고+4부터4byte셀을column-major로읽는다. Descriptor의width/height와각맵header BE16 두값이일치한다. 1854a이후에는bank2 CPU200010 root의secondary selector를읽는다. 이별도자료를현재collision으로단정하지않으며node80buffer복사라는확정효과만기록했다. 명령실행·타일갱신C++구현은이번범위가아니다.

## 목록 도구 리뷰 수정

메인이walk의recursive DFS에서4096 guard보다Python recursion한도가먼저올수있음을발견했다. Iterative DFS로수정하고1500명령경로를검사했다. 고정ROM경계뿐아니라짧은program길이도검사해truncation을명시진단한다. 합성7tests는모든conditional successor/cycle/operandoverlap/길이/unknown/odd/bounds를다룬다. ROMpatch실행과구분한다.

Tilemap도구는원시descriptorbytes와source일치를확인하고field도raw >4HI에서다시읽어metadata와대조하도록수정했다. 구조불일치는명시status와nonzero exit로보고한다. 테이블범위는root200008부터첫pointer20013c까지77entry라는구조후보이며이것만으로전체ROM맵의완전성이나사용여부를단정하지않는다.

77pointer가순서대로bank3에있고각header가양수이며4+4×width×height span이모든다음pointer와정확히맞는다. 중간gap/overlap0,총763136bytes/190707cells,마지막CPU2ba63c=ROM3ba63c다. 남은bank bytes는별도미분석으로둔다. 알려진72descriptor 모두치수가맞고69selector를참조한다. 나머지8selector(decimal21,49,59,60,65,66,71,73)는현재참조없음이지미사용확정이아니다.

## 검증과 재현

원본dispatch654조건은218주소×D7high3이다. Handler진입직전또는negativeRTS까지D7/A2/D/Aregs·전체RAM/stack/ROM불변과A7를검사했다. 실제실행된양수opcode는00/04/18이며다른5target은원시BRA주소대조뿐이다. Handler효과/C++동등성검증이라고주장하지않는다. 원본reference/root/rawclosure도독립재계산했다.

Path inventory SHA256 `0bb2ed9b1c73335e983b72290187eed473e1229f0b3db47df5402d81ebc91a07`,dispatch report `f50925f4e467cf4fda90309e3cf2cab58bf9ba07cb746fdc273fea5795204e11`,tilemap inventory `4249e94dcb069c477494b40ec91a312cde0ee076ec9ac978d35db9daf1a50262`. 메인이도구diff·실제JSON수치/해시·검증코드를확인했다. 전체Python146tests exit0,로그 `artifacts/scene_paths/python_tests.log`. C++변경없음으로동일C++전체회귀를반복하지않았다.

## 다음 연결

조사한경로/맵을기존버전있는MS5D로보존하고C++로더와map/secondarydata 접근을연결해야한다. 이번JSONinventory를최종게임리소스형식으로대체하지않는다. 19e64의8명령,표시helper,1afda register승계,일반1a5a4와전체stage/gameplay는남아있다. 전체목표는미완료다.
