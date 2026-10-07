# 장면 좌표 갱신과 노드 레지스터 확장 리뷰

Baseline `77a976e`. 이전goal turn은motion 구간선택/평가와원본비교를통합한progress다. 이번메인원본분석은일반1a5a4가호출하는1a7a8의좌표갱신과그leaf의scratch register 승계에집중했다. 원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 원본코드는첫1MiB CPU=ROMoffset이다.

## 지원 경계

1a7a8..1a8ca직전의카메라+네노드좌표prefix를연결한다. 1a8ca의1afda및19e64네호출과마지막1a90e RTS는이API의실행범위밖이다. 원본검증도1a8ca에멈추며이를함수RTS나전체장면갱신과동일하다고주장하지않는다. 일반1a5a4 전체를이prefix로대체하지않는다.

## 원본과 코드 검토

Camera10d38e의delta는장면d3bc/d3c0와local좌표에서계산하며Y의01000000보정을포함한다. 43ea8뒤LIVEd404 WORD를worldY의상위word에더한다. 이후109156/10b1d6/10d256/10d2d6을순서대로처리한다. LIVE d40c 각두bit가X/Yscale호출을각각차단하지만1728c좌표갱신과후속scroll WORDadd는항상수행한다. Parent가앞서처리한node면scroll수정후world를읽는다.

SceneNodeState를D0..D7/A0/A1/A2/A4로확장했다. 기존5registerCLI는유지하고새12registerCLI를추가했다. 1724c/1726c는D7.low factor,D6의unsigned product→ASR32→carry보정,D5의SUBX.L결과0/ffffffff와signed두번째곱을노출한다. 양쪽곱의부호가다르며unsigned연산으로wrap/signfill을명시했다.

43e38 계열은advance local쓰기→oldworld D2/D3→parent/local읽기→D6lowcarry/D7flags→world쓰기→LIVEglobalstamp D5.byte/oldstamp D4.byte→history쓰기순서를보존한다. Self/overlap/globalstamp alias에서단순히최종RAM만다시읽어register를만들면틀릴수있어정확register경로를scene_node안에구현했다. 기존position_state RAM-only코어는수정하지않았다. Parent없는경로의D4/D5상위24비트와D6보존도검사한다.

메인이실제core/CLI/header/unit/Makefile/nativeverifier를읽고원본명령순서와대조했다. API는RAM/12register 전체transaction이며후반노드parent오류도전체입력을보존한다. 파일write 실패까지원자적출력을제공한다고주장하지않는다.

## 검증

신규native5248=leaf1132+prefix4116,negative135,MMIO0을통과했다. Prefix는256mask×8좌표/factor/fraction/parent/stamp profile×2highregister4096과4sequence×5 actualCLI carry20이다. Leaf10entries는실제node주소,부모/self/overlap/globalstampalias와곱/ASR/분수carry를검사한다. 전체RAM/12register/ROM불변및leaf A7=SP+4,prefix A7=SP를확인했다. Prefix 내부call사이context reset은없고호출간stack/SR reset은fixture다.

Report `artifacts/scene_coordinates/verification.json` SHA256 `f903e4444ad1f690bc8a4ae0aa016e20418479fa34ec5cc634189dbd6fd8bf0a`. LeafCLI SHA256 `2f20b2e4295e7cd2793850ea829ed6af2652651b0aea1bd9ace6c3b1e06d119a`,prefixCLI SHA256 `052b04e966b182a95228ca69f0dc05a12e7b9d207cd305fe9ecd430adbd651d2`. 메인이보고서/파일해시/실제counts를확인했다. Scope의미확정명칭columnrefresh는주소기반before1afda/four19e64로정정했다.

전체make exit0 Python139/C++102/경고0,로그 `artifacts/scene_coordinates_build_test.log`. 기존5registernode1904조건/오류94/8sequence48호출/MMIO0 회귀도통과했고보고서SHA256 `c900dfc01d94c31633856b8ffae34478ce9ad281366b9322e23ccebd85a0c1c6`은이전과동일하다. Scene command4535조건/오류104/1737175orderedports도통과했다. 최신report SHA256 `1a08295adfc94be432f14a46b013a760808ef0706679220b0f6355cb0d1b1019`,binary SHA256 `7fea703ec8fac8c64103f113fcab67d7a2b7fa787b62600703fbd09b7bda0c1e`. 각각session13922/88488 exit0를확인했으며메인이보고서파일을직접확인했다.

## 미완료

다음은1afda와19e64 path/display처리를원본근거로연결하는것이다. 여기에는추가표시자료와다른helper의검증이필요하며현재null/skip으로전체scene완료를주장하지않는다. 일반1a5a4,47a94이후stage진입,자연frame/IRQ,실제스테이지화면및전체목표는미완료다.
